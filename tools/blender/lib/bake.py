"""High → low baking for Art 2.1 (docs/ART_2_DETAIL.md §3.1, §3.3): the atlas layout with its strip of tuft-lock and
fur-card tiles, Cycles selected → active bakes with only the sources visible, ORM packing, a share of the AO in the
colour, variant colour maps on the same UVs, and the cards' root colours.

Generalised from the detail spike (tools/blender/spikes/detail_spike.py). A caller supplies the bake plan (each low
mesh with its sources and its occluders) and a `paint(pass)` callback that puts the right emission materials on the
sources for the 'base' and 'rough' passes (and any extra colour passes, e.g. a variant). Pinned to Blender 5.2.
"""
from __future__ import annotations

import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

from . import common as C
from . import mesh as M
from . import surface as S
from .nodes import NB, new_image, new_mat

# ----------------------------------------------------------------------------- atlas layout
STRIP = 0.125          # bottom share of the body atlas kept for the strip
CELLS = 8              # strip cells: 0–1 tuft-lock tiles, 2–7 fur-card tiles
LOCK_CELLS = (0, 1)
CARD_CELLS = (2, 3, 4, 5, 6, 7)
CARD_STYLES = ('fur', 'wool', 'hair')


def card_cell_styles(style) -> dict[int, str]:
    """{card cell: style} for a CARD_STYLE (one style on every cell) or per-layer styles (a tuple: the distinct styles,
    in order, share the six cells: two styles three cells each, three styles two each)."""
    styles = (style,) if isinstance(style, str) else tuple(style)
    distinct = list(dict.fromkeys(styles))
    for st in distinct:
        if st not in CARD_STYLES:
            raise ValueError(f'card style {st!r}: one of {CARD_STYLES}')
    if len(distinct) > 3:
        raise ValueError(f'card styles {distinct}: at most three different styles share the six card cells')
    per = len(CARD_CELLS) // len(distinct)
    return {c: distinct[min(i // per, len(distinct) - 1)] for i, c in enumerate(CARD_CELLS)}


def layer_cells(style, layers: int) -> dict[int, tuple[int, ...]]:
    """{card layer: its style's cells} (CARD_LAYER_STYLES; a single style gives every layer all six cells)."""
    cs = card_cell_styles(style)
    styles = (style,) * layers if isinstance(style, str) else tuple(style)
    if len(styles) < layers:
        raise ValueError(f'card styles {styles}: one per card layer ({layers})')
    return {i: tuple(c for c in CARD_CELLS if cs[c] == styles[i]) for i in range(layers)}
BASE_AO = 0.38         # share of the baked AO multiplied into the base colour (crevices stay dark on any renderer)


def _uv_arrays(objs, uv_name: str) -> list[np.ndarray]:
    out = []
    for o in objs:
        uv = o.data.uv_layers[uv_name].data
        arr = np.empty(len(uv) * 2, np.float32)
        uv.foreach_get('uv', arr)
        out.append(arr.reshape(-1, 2))
    return out


def _set_uvs(objs, uv_name: str, arrays: list[np.ndarray]) -> None:
    for o, arr in zip(objs, arrays):
        o.data.uv_layers[uv_name].data.foreach_set('uv', np.ascontiguousarray(arr, np.float32).ravel())


def uv_overlap_faces(ob: bpy.types.Object, uv_name: str = 'UVMap', size: int = 2048) -> tuple[int, set[int]]:
    """(texels claimed by two different triangles on a size x size grid over UV 0..1, the polygons involved). Adjacent
    triangles of one island never share a texel centre, so any count is a real overlap: both faces would bake into the
    same pixels. Object mode. (tools/art/ultra-uv.ts counts the same on an exported .glb.)"""
    me = ob.data
    if uv_name not in me.uv_layers or not len(me.polygons):
        return 0, set()
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    tl = np.empty(n * 3, np.int32)
    me.loop_triangles.foreach_get('loops', tl)
    tp = np.empty(n, np.int32)
    me.loop_triangles.foreach_get('polygon_index', tp)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[uv_name].data.foreach_get('uv', uv)
    tri = uv.reshape(-1, 2)[tl].reshape(n, 3, 2).astype(np.float64) * size
    owner = np.full(size * size, -1, np.int64)
    hit = np.zeros(size * size, bool)
    bad: set[int] = set()
    lo = np.clip(np.floor(tri.min(axis=1)).astype(np.int64), 0, size - 1)
    hi = np.clip(np.ceil(tri.max(axis=1)).astype(np.int64), 0, size - 1)
    for t in range(n):
        (x0, y0), (x1, y1), (x2, y2) = tri[t]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            continue
        sgn = 1.0 if area > 0 else -1.0
        xs = np.arange(lo[t, 0], hi[t, 0] + 1) + 0.5
        ys = np.arange(lo[t, 1], hi[t, 1] + 1) + 0.5
        px, py = np.meshgrid(xs, ys)
        w0 = sgn * ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py))
        w1 = sgn * ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py))
        w2 = sgn * ((x0 - px) * (y1 - py) - (x1 - px) * (y0 - py))
        inside = (w0 > 0) & (w1 > 0) & (w2 > 0)
        if not inside.any():
            continue
        k = (py[inside] - 0.5).astype(np.int64) * size + (px[inside] - 0.5).astype(np.int64)
        prev = owner[k]
        clash = (prev >= 0) & (prev != t)
        if clash.any():
            hit[k[clash]] = True
            bad.add(int(tp[t]))
            bad.update(int(tp[q]) for q in np.unique(prev[clash]))
        owner[k] = t
    return int(hit.sum()), bad


def _uv_face_areas(ob: bpy.types.Object, uv_name: str) -> tuple[np.ndarray, np.ndarray]:
    """(each polygon's UV area, its area in the scene), object mode."""
    me = ob.data
    starts = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_start', starts)
    totals = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_total', totals)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[uv_name].data.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2).astype(np.float64)
    nxt = np.arange(len(me.loops)) + 1
    ends = starts + totals
    nxt[ends - 1] = starts                                         # each polygon's last corner wraps to its first
    cross = uv[:, 0] * uv[nxt, 1] - uv[nxt, 0] * uv[:, 1]
    uva = np.abs(np.add.reduceat(cross, starts)) * 0.5 if len(starts) else np.zeros(0)
    area = np.empty(len(me.polygons), np.float32)
    me.polygons.foreach_get('area', area)
    return uva, area.astype(np.float64)


def _repair_overlaps(objs: list[bpy.types.Object], uv_name: str, angle_deg: float, island_margin: float, pack_margin: float) -> None:
    """After a pack the islands are apart, so any overlap left is an island lying over itself (smart-project put a fold
    and the skin under it, both facing its way, in one island: Tumblefox's belly over a front sock, Puddlepup's cheek
    under its ear). Those faces are projected again on their own (at the pack's angle, then at a third of it, then
    each face flat on its own), scaled to their object's texel density and packed with the rest. A pack without
    overlaps is left exactly as it was."""
    import bmesh
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    for attempt in range(3):
        bad = {o.name: uv_overlap_faces(o, uv_name)[1] for o in objs}
        if not any(bad.values()):
            return
        C.log(f"atlas pack: overlapping UVs, projecting {sum(len(v) for v in bad.values())} faces again "
              f"({', '.join(f'{k} {len(v)}' for k, v in bad.items() if v)}; pass {attempt + 1})")
        dens = {}
        for o in objs:
            uva, area = _uv_face_areas(o, uv_name)
            good = np.ones(len(area), bool)
            good[list(bad[o.name])] = False
            dens[o.name] = float(uva[good].sum() / max(area[good].sum(), 1e-12)) if good.any() else None
        known = [d for d in dens.values() if d]
        fallback = float(np.median(known)) if known else 1.0
        if attempt < 2:
            angle = angle_deg if attempt == 0 else angle_deg / 3.0
            with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_objects=objs, selected_editable_objects=objs):
                bpy.ops.object.mode_set(mode='EDIT')
                for o in objs:
                    bm = bmesh.from_edit_mesh(o.data)
                    for f in bm.faces:
                        f.select = f.index in bad[o.name]
                    bmesh.update_edit_mesh(o.data)
                bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=island_margin, correct_aspect=True, scale_to_bounds=False)
                bpy.ops.object.mode_set(mode='OBJECT')
        else:
            # each face flat on its own plane, its own island (far apart until the pack): cannot lie over itself
            for o in objs:
                if not bad[o.name]:
                    continue
                me = o.data
                uvl = me.uv_layers[uv_name].data
                co = np.empty(len(me.vertices) * 3, np.float32)
                me.vertices.foreach_get('co', co)
                co = co.reshape(-1, 3).astype(np.float64)
                for j, fi in enumerate(sorted(bad[o.name])):
                    poly = me.polygons[fi]
                    nrm = np.array(poly.normal, np.float64)
                    ref = np.array([0.0, 0.0, 1.0]) if abs(nrm[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
                    a1 = ref - nrm * float(ref @ nrm)
                    a1 /= max(float(np.linalg.norm(a1)), 1e-12)
                    a2 = np.cross(nrm, a1)
                    q = co[[me.loops[li].vertex_index for li in poly.loop_indices]]
                    xy = np.stack([q @ a1, q @ a2], axis=1)
                    nxt = np.roll(xy, -1, axis=0) - xy
                    turns = nxt[:, 0] * np.roll(nxt, -1, axis=0)[:, 1] - nxt[:, 1] * np.roll(nxt, -1, axis=0)[:, 0]
                    if len(xy) > 3 and not ((turns > 0).all() or (turns < 0).all()):
                        # a folded or twisted face lies over itself whichever way it is flattened: its corners go
                        # round a circle of the same area instead (a few hidden faces, a fold in a prop or a coat)
                        k = len(xy)
                        rad = math.sqrt(max(poly.area, 1e-12) / (0.5 * k * math.sin(2 * math.pi / k)))
                        ang = 2 * math.pi * np.arange(k) / k
                        xy = np.stack([rad * np.cos(ang), rad * np.sin(ang)], axis=1)
                    for li, (x, y) in zip(poly.loop_indices, xy):
                        uvl[li].uv = (float(x) + 10.0 * j, float(y))
        # the new islands at their object's texel density (they came back at the projector's own scale)
        for o in objs:
            if not bad[o.name]:
                continue
            uva, area = _uv_face_areas(o, uv_name)
            sel = np.zeros(len(area), bool)
            sel[list(bad[o.name])] = True
            now = float(uva[sel].sum() / max(area[sel].sum(), 1e-12))
            k = math.sqrt((dens[o.name] or fallback) / max(now, 1e-12))
            me = o.data
            starts = np.empty(len(me.polygons), np.int32)
            me.polygons.foreach_get('loop_start', starts)
            totals = np.empty(len(me.polygons), np.int32)
            me.polygons.foreach_get('loop_total', totals)
            lsel = np.repeat(sel, totals)
            uv = np.empty(len(me.loops) * 2, np.float32)
            me.uv_layers[uv_name].data.foreach_get('uv', uv)
            uv = uv.reshape(-1, 2)
            uv[lsel] *= k
            me.uv_layers[uv_name].data.foreach_set('uv', uv.ravel())
        with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_objects=objs, selected_editable_objects=objs):
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.pack_islands(rotate=True, margin=pack_margin)
            bpy.ops.object.mode_set(mode='OBJECT')


# texel_k is grouped in steps of this before projecting (each group unwrapped on its own)
TEXEL_K_STEP = 0.1


def _face_texel_k(o: bpy.types.Object) -> np.ndarray | None:
    """The object's FACE float attribute texel_k (missing, zero or negative values count as 1), or None."""
    a = o.data.attributes.get('texel_k')
    if a is None or a.domain != 'FACE' or a.data_type != 'FLOAT':
        return None
    k = np.empty(len(o.data.polygons), np.float32)
    a.data.foreach_get('value', k)
    return np.where(k > 0.0, k, 1.0).astype(np.float64)


def _texel_groups(objs, keep_faces: str | None) -> dict:
    """{object: per-face group id (k rounded to TEXEL_K_STEP; -1 for own-UV faces)} when any object has texel_k
    other than 1; else {} (the pack runs as it always did)."""
    ks = {o.name: _face_texel_k(o) for o in objs}
    if all(k is None or np.allclose(k, 1.0) for k in ks.values()):
        return {}
    out = {}
    for o in objs:
        k = ks[o.name] if ks[o.name] is not None else np.ones(len(o.data.polygons))
        g = np.round(k / TEXEL_K_STEP).astype(np.int64)
        if keep_faces and keep_faces in o.data.attributes:
            kf = np.empty(len(o.data.polygons), np.float32)
            o.data.attributes[keep_faces].data.foreach_get('value', kf)
            g = np.where(kf > 0.5, -1, g)
        out[o.name] = g
    return out


def _apply_texel_k(objs, uv_name: str, keep_faces: str | None) -> None:
    """Scale each face's UVs by its texel_k group (islands never straddle groups); own-UV faces by their object's
    mean k over them (an own unwrap is one island per part)."""
    for o in objs:
        k = _face_texel_k(o)
        if k is None:
            continue
        me = o.data
        g = np.round(k / TEXEL_K_STEP) * TEXEL_K_STEP
        if keep_faces and keep_faces in me.attributes:
            kf = np.empty(len(me.polygons), np.float32)
            me.attributes[keep_faces].data.foreach_get('value', kf)
            own = kf > 0.5
            if own.any():
                g = np.where(own, float(k[own].mean()), g)
        totals = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get('loop_total', totals)
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers[uv_name].data.foreach_get('uv', uv)
        uv = uv.reshape(-1, 2) * np.repeat(g, totals)[:, None].astype(np.float32)
        me.uv_layers[uv_name].data.foreach_set('uv', uv.ravel())
    C.log(f"atlas pack: texel_k applied ({', '.join(f'{o.name} {np.unique(np.round(_face_texel_k(o) / TEXEL_K_STEP) * TEXEL_K_STEP).round(2).tolist()}' for o in objs if _face_texel_k(o) is not None)})")


def pack_atlas(objs: list[bpy.types.Object], uv_name: str, strip: float, angle_deg: float = 62.0,
               island_margin: float = 0.005, pack_margin: float = 0.003, density: dict | None = None, keep_faces: str | None = None) -> None:
    """Smart-project the objects together into `uv_name` at an even texel density, leaving the bottom `strip`.
    `density` {object name: k} scales an object's texel density by k (e.g. eyes up, smooth membranes down).
    `keep_faces` names a FACE float attribute: faces where it is > 0.5 keep the UVs already in `uv_name` (a recipe's own
    unwrap: a horn or a rope unrolled as one strip, where smart-project cuts many small islands); they are only scaled
    to the common texel density and packed with the rest.
    A FACE float attribute `texel_k` on any object (default 1) scales those faces' texel density by k (the head 1.6, the
    belly 0.7): the faces are grouped by k in steps of TEXEL_K_STEP and each group is projected on its own, so no
    island straddles two densities; an own-UV island takes its faces' mean k. Faces that end up sharing texels (an island lying over
    itself) are projected again on their own (_repair_overlaps); build_ultra fails in words if any are left.

    The islands fill the whole 1 × (1 − strip) rectangle (P1.2; P1.1 packed into a square and used ~80% of the width):
    a first pack chooses each island's rotation; then the UVs are stretched by 1 / (1 − strip) in v, packed again into
    the unit square without rotating (only moved and scaled together), and squashed back, so every island keeps its shape."""
    for o in objs:
        if uv_name not in o.data.uv_layers:
            o.data.uv_layers.new(name=uv_name)
        o.data.uv_layers.active = o.data.uv_layers[uv_name]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    def edit(fn) -> None:
        with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_objects=objs, selected_editable_objects=objs):
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            fn()
            bpy.ops.object.mode_set(mode='OBJECT')

    groups = _texel_groups(objs, keep_faces)

    def project() -> None:
        if groups:
            # one projection per density group (faces of other groups, and own-UV faces, unselected meanwhile)
            import bmesh
            for g in sorted({g for gs in groups.values() for g in gs.tolist() if g >= 0}):
                for o in objs:
                    bm = bmesh.from_edit_mesh(o.data)
                    bm.faces.ensure_lookup_table()
                    sel = groups[o.name] == g
                    for f in bm.faces:
                        f.select = bool(sel[f.index])
                    bmesh.update_edit_mesh(o.data)
                bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg), island_margin=island_margin, correct_aspect=True, scale_to_bounds=False)
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.average_islands_scale()
            return
        if keep_faces:
            # the recipe's own unwraps stay out of the projection (unselected), then join the rest for the scaling
            import bmesh
            for o in objs:
                bm = bmesh.from_edit_mesh(o.data)
                lay = bm.faces.layers.float.get(keep_faces)
                if lay is not None:
                    for f in bm.faces:
                        if f[lay] > 0.5:
                            f.select = False
                    bmesh.update_edit_mesh(o.data)
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg), island_margin=island_margin, correct_aspect=True, scale_to_bounds=False)
        if keep_faces:
            bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.average_islands_scale()
    edit(project)
    if density:
        arrs = _uv_arrays(objs, uv_name)
        _set_uvs(objs, uv_name, [a * float(density.get(o.name, 1.0)) for o, a in zip(objs, arrs)])
    if groups:
        _apply_texel_k(objs, uv_name, keep_faces)
    edit(lambda: bpy.ops.uv.pack_islands(rotate=True, margin=pack_margin))
    _repair_overlaps(objs, uv_name, angle_deg, island_margin, pack_margin)
    keep = 1.0 - strip
    if strip > 0:
        _set_uvs(objs, uv_name, [a * np.array([1.0, 1.0 / keep], np.float32) for a in _uv_arrays(objs, uv_name)])
        edit(lambda: bpy.ops.uv.pack_islands(rotate=False, margin=pack_margin))
    arrs = _uv_arrays(objs, uv_name)
    lo = np.min([a.min(0) for a in arrs], axis=0)
    hi = np.max([a.max(0) for a in arrs], axis=0)
    C.log(f'atlas pack: islands span u {lo[0]:.3f}..{hi[0]:.3f}, v {lo[1]:.3f}..{hi[1]:.3f} (of the unit square before the strip)')
    out = []
    for a in arrs:
        a = a.copy()
        if strip > 0:
            a[:, 1] = a[:, 1] * keep + strip
        out.append(a)
    _set_uvs(objs, uv_name, out)
    for o in objs:
        if 'UVMap' in o.data.uv_layers:
            o.data.uv_layers.active = o.data.uv_layers['UVMap']


def strip_uvs(ob: bpy.types.Object, cells: tuple[int, ...], uv_name: str = 'UVMap', by_layer: dict | None = None) -> None:
    """Each element maps into one strip cell (across → u, along → v), picked by its random number; `by_layer`
    {layer: cells} picks from its layer's cells instead (per-layer card styles: the element attribute 'layer')."""
    me = ob.data
    if uv_name not in me.uv_layers:
        me.uv_layers.new(name=uv_name)
    across = S.attr_array(ob, 'across')
    tpos = S.attr_array(ob, 'tpos')
    lrand = S.attr_array(ob, 'lrand')
    if by_layer:
        layer = np.round(S.attr_array(ob, 'layer')).astype(int)
        cell = np.zeros(len(lrand), np.int64)
        for li, cs in by_layer.items():
            m = layer == li
            pick = np.minimum((lrand[m] * len(cs)).astype(int), len(cs) - 1)
            cell[m] = np.array(cs)[pick]
    else:
        pick = np.minimum((lrand * len(cells)).astype(int), len(cells) - 1)
        cell = np.array(cells)[pick]
    pad = 0.012
    u = (cell + pad + (np.clip(across, -1, 1) + 1) * 0.5 * (1 - 2 * pad)) / CELLS
    v = (pad + tpos * (1 - 2 * pad)) * STRIP
    loops_v = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', loops_v)
    me.uv_layers[uv_name].data.foreach_set('uv', np.stack([u[loops_v], v[loops_v]], axis=1).astype(np.float32).ravel())


# ----------------------------------------------------------------------------- Cycles
def use_gpu(with_cpu: bool = False) -> str:
    """Cycles on the GPU (OptiX, else CUDA); `with_cpu` adds the processor too (when another job holds the GPU)."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = kind
            prefs.refresh_devices()
            if [d for d in prefs.devices if d.type == kind]:
                for d in prefs.devices:
                    d.use = d.type == kind or (with_cpu and d.type == 'CPU')
                sc.cycles.device = 'GPU'
                return kind
        except Exception:  # noqa: BLE001
            pass
    sc.cycles.device = 'CPU'
    return 'CPU'


def use_cpu() -> str:
    """Cycles on the processor only: on a shared PC, faster than a GPU another job saturates."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    return 'CPU'


def bake_world(ao_distance: float = 0.05) -> None:
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new('BakeWorld')
    sc.world.light_settings.distance = ao_distance


def set_material(objs, mat) -> None:
    for o in objs:
        o.data.materials.clear()
        o.data.materials.append(mat)


def bake_target_material(name: str, image: bpy.types.Image) -> bpy.types.Material:
    m, nb = new_mat(name)
    t = nb.new('ShaderNodeTexImage', image=image)
    t.select = True
    nb.t.nodes.active = t
    bsdf = nb.new('ShaderNodeBsdfPrincipled')
    nb.output(bsdf.outputs[0])
    return m


def bake(kind: str, low: bpy.types.Object, highs: list[bpy.types.Object], image: bpy.types.Image, samples: int,
         clear: bool, cage: float = 0.02, dist: float = 0.05, uv_layer: str = 'UVMap', margin: int = 6) -> None:
    """One selected → active bake. Only the sources may shadow it: everything else is hidden from render and the low
    mesh is invisible to rays (the game's own cards, tuft and low meshes stand above the fur and turned the AO black)."""
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    prev_mats = list(low.data.materials)
    set_material([low], bake_target_material(f'target_{low.name}', image))
    scene_obs = [o for o in bpy.context.scene.objects if o is not None]
    hidden = {o.name: o.hide_render for o in scene_obs}
    ray_flags = ('visible_diffuse', 'visible_glossy', 'visible_shadow', 'visible_transmission', 'visible_volume_scatter')
    low_rays = {f: getattr(low, f) for f in ray_flags}
    keep = {o.name for o in highs} | {low.name}
    for o in scene_obs:
        o.select_set(False)
        o.hide_render = o.name not in keep
    for f in ray_flags:
        setattr(low, f, False)
    for o in highs:
        o.hide_set(False)
        o.select_set(True)
    low.hide_set(False)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    try:
        with C.Timer(f'bake {kind} {low.name} → {image.name}'):
            with bpy.context.temp_override(active_object=low, object=low, selected_objects=highs + [low], selected_editable_objects=highs + [low]):
                bpy.ops.object.bake(type=kind, use_selected_to_active=True, cage_extrusion=cage, max_ray_distance=dist,
                                    margin=margin, margin_type='EXTEND', use_clear=clear, normal_space='TANGENT', target='IMAGE_TEXTURES',
                                    uv_layer=uv_layer)
    finally:
        for o in bpy.context.scene.objects:
            if o is not None and o.name in hidden:
                o.hide_render = hidden[o.name]
        for f, v in low_rays.items():
            setattr(low, f, v)
        low.data.materials.clear()
        for m in prev_mats:
            low.data.materials.append(m)


def save_png(image: bpy.types.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(path)
    image.file_format = 'PNG'
    image.save()
    C.log(f'saved {C.rel(path)}')


def image_array(image: bpy.types.Image) -> np.ndarray:
    w, h = image.size
    a = np.empty(w * h * 4, np.float32)
    image.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def image_from_array(name: str, arr: np.ndarray, srgb: bool, alpha: bool) -> bpy.types.Image:
    h, w = arr.shape[:2]
    img = new_image(name, w, alpha=alpha, srgb=srgb)
    img.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    return img


# ----------------------------------------------------------------------------- source paint materials
def _attr(nb: NB, name: str, out: str = 'Fac'):
    return nb.attribute(name).outputs[out]


def emission_attr_material(name: str, attr: str) -> bpy.types.Material:
    """Emission straight from a colour attribute (numpy-painted sources)."""
    m, nb = new_mat(name)
    em = nb.new('ShaderNodeEmission')
    nb.link(_attr(nb, attr, 'Color'), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def strip_paint_material(name: str, rough_pass: bool = False, alpha_pass: bool = False) -> bpy.types.Material:
    """The strip's tiles: a neutral gradient (vertex colours tint it), damp-fur roughness, and for fur cards an alpha
    that fades the lock tips softly."""
    m, nb = new_mat(name)
    tpos = _attr(nb, 'tpos')
    em = nb.new('ShaderNodeEmission')
    if alpha_pass:
        tip = nb.smooth(tpos, 0.98, 0.62)
        root = nb.smooth(tpos, 0.0, 0.1)
        a = nb.math('MULTIPLY', tip, root)
        nb.link(nb.comb(a, a, a), em.inputs['Color'])
    elif rough_pass:
        rough = nb.math('ADD', 0.44, nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', tpos, 0.45)), 0.25))
        nb.link(nb.comb(1.0, rough, 0.16), em.inputs['Color'])
    else:
        g = nb.math('ADD', 0.88, nb.math('MULTIPLY', tpos, 0.12))
        nb.link(nb.comb(g, g, g), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def hair_tile(px: int, seed: int) -> dict:
    """One 'hair' card tile, px x px, rows bottom-up (row 0 the card's root, tpos 0): 8-14 thin strands with alpha-0
    gaps between them, each 10-20 px wide at 256 px, tapering over its top 40-60% to a fine point with a soft 2-3 px
    falloff along the sides. The shading is in the tile (roots about 0.6x, lighter tips, a thin highlight line and a
    darker edge per strand, a little brightness jitter between strands) and the normal rounds across each strand.
    Painted in numpy (no strip geometry): 'value' (grey, the cards' vertex colour tints it), 'alpha', 'normal' (0..1),
    'ao', 'rough'. (Starhowl's mane: the fur tiles' 2-3 broad, near-opaque, unshaded lobes read as cut-paper blades.)"""
    rng = np.random.default_rng(seed)
    k = px / 256.0
    X, Y = np.meshgrid(np.arange(px) + 0.5, (np.arange(px) + 0.5) / px)
    value = np.full((px, px), 0.94)
    alpha = np.zeros((px, px))
    nx = np.zeros((px, px))
    ao = np.ones((px, px))
    rough = np.full((px, px), 0.5)
    n = int(rng.integers(8, 15))
    widths = rng.uniform(10, 20, n) * k
    gaps = rng.dirichlet(np.ones(n + 1) * 3.0) * max(px * 0.94 - widths.sum(), n * 2.0 * k)
    left = px * 0.03 + np.cumsum(np.concatenate([[0.0], widths[:-1]])) + np.cumsum(gaps[:-1])
    for i in range(n):
        w = widths[i]
        length = rng.uniform(0.72, 0.98)
        taper0 = length * (1.0 - rng.uniform(0.4, 0.6))
        bend = rng.normal(0.0, 0.025) * px
        wave = rng.uniform(0.0, 0.008) * px
        phase = rng.uniform(0, 2 * math.pi)
        jitter = rng.uniform(0.9, 1.08)
        t = Y / length
        cx = left[i] + w / 2 + bend * t ** 2 + wave * np.sin(t * math.pi * 2.0 + phase)
        hw = 0.5 * w * (1.0 - S.smooth(taper0 / length, 1.0, t) * 0.92)
        d = np.abs(X - cx)
        a = np.clip((hw - d) / (2.5 * k) + 0.5, 0.0, 1.0) * (t <= 1.0) * S.smooth(1.0, 0.97, t) * S.smooth(0.0, 0.04, Y)
        u = np.clip((X - cx) / np.maximum(hw, 1e-6), -1.0, 1.0)
        tc = np.clip(t, 0, 1)
        shade = (0.6 + 0.42 * tc ** 0.7) * jitter
        shade = shade * (1.0 - 0.16 * S.smooth(0.55, 1.0, np.abs(u))) + 0.14 * np.exp(-((u + 0.28) / 0.16) ** 2) * S.smooth(0.05, 0.25, t)
        take = (a > 0.0) & (a >= alpha)
        value = np.where(take, np.clip(shade, 0.0, 1.0), value)
        alpha = np.maximum(alpha, a)
        nx = np.where(take, u * 0.55, nx)
        ao = np.where(take, 0.82 + 0.18 * tc, ao)
        rough = np.where(take, 0.44 + 0.12 * np.abs(u), rough)
    nz = np.sqrt(np.clip(1.0 - nx * nx, 0.0, 1.0))
    normal = np.stack([nx * 0.5 + 0.5, np.full_like(nx, 0.5), nz * 0.5 + 0.5], axis=-1)
    return {'value': value, 'alpha': alpha, 'normal': normal, 'ao': ao, 'rough': rough}


def paint_hair_cells(imgs: dict, alpha: np.ndarray, cells: list[int]) -> None:
    """Write 'hair' tiles into the baked strip's card cells (colour, normal, AO, roughness and the alpha array)."""
    if not cells:
        return
    size = imgs['base'].size[0]
    rows = int(round(size * STRIP))
    cw = size // CELLS
    arrs = {k: image_array(imgs[k]) for k in ('base', 'normal', 'ao', 'rc')}
    for c in cells:
        t = hair_tile(min(rows, cw), 100 + c)
        r = slice(0, t['alpha'].shape[0])
        x = slice(c * cw, c * cw + t['alpha'].shape[1])
        arrs['base'][r, x, :3] = t['value'][..., None]
        arrs['normal'][r, x, :3] = t['normal']
        arrs['ao'][r, x, :3] = t['ao'][..., None]
        arrs['rc'][r, x, 1] = t['rough']
        arrs['rc'][r, x, 2] = 0.16
        alpha[r, x] = t['alpha']
    for k, a in arrs.items():
        imgs[k].pixels.foreach_set(np.ascontiguousarray(a, dtype=np.float32).ravel())
    C.log(f"strip: 'hair' tiles painted in card cells {cells}")


def strip_scene(card_style='fur'):
    """The strip's high detail: per lock cell one tuft lock laid flat; per card cell a cluster of soft locks with
    rounded tips at different lengths (card_style 'wool': short crimped ringlets in a fluffy clump instead). The low is
    a plane whose UVs are the strip."""
    rng = np.random.default_rng(5)
    cs = card_cell_styles(card_style) if not isinstance(card_style, dict) else card_style
    parts = []
    for c in LOCK_CELLS:
        tpl = S.lock_template(28, 28, 3, strand=0.18)
        v = tpl[0]
        verts = np.stack([c + 0.5 + v[:, 0] * 0.5, 0.012 + v[:, 1] * 0.976, v[:, 2] * 0.14], axis=1)[None]
        parts.append(S.elements_object(f'strip_lock_{c}', verts, tpl, np.zeros((1, 3)), S.KIND_TUFT, rng))
    for c in [c for c in CARD_CELLS if cs[c] == 'fur']:
        k = 3 + (c % 2)
        for i in range(k):
            tpl = S.lock_template(16, 22, 3, strand=0.16)
            v = tpl[0]
            w = (0.92 / k) * (0.9 + 0.2 * rng.random())
            cx = c + (i + 0.5) / k + rng.normal(0, 0.015)
            ln = 0.7 + 0.26 * rng.random()
            ang = math.radians(rng.normal(0, 6))
            # narrow at the root so each card's locks stand apart all the way down (no solid strip at the base)
            x = v[:, 0] * w * 0.5 * (0.6 + 0.4 * S.smooth(0.0, 0.3, v[:, 1]))
            y = v[:, 1] * ln
            xr, yr = x * math.cos(ang) - y * math.sin(ang), x * math.sin(ang) + y * math.cos(ang)
            verts = np.stack([cx + xr, 0.01 + yr, v[:, 2] * 0.07 + 0.002 * i], axis=1)[None]
            parts.append(S.elements_object(f'strip_card_{c}_{i}', verts, tpl, np.zeros((1, 3)), S.KIND_CARD, rng))
    for c in [c for c in CARD_CELLS if cs[c] == 'wool']:
        # wool: five to seven short ringlets per tile, crimped side to side, wide and round-tipped, overlapping in a clump
        k = 5 + (c % 3)
        for i in range(k):
            tpl = S.lock_template(14, 26, 2, strand=0.1)
            v = tpl[0]
            w = (1.25 / k) * (0.9 + 0.25 * rng.random())
            cx = c + (i + 0.5) / k + rng.normal(0, 0.03)
            ln = 0.45 + 0.4 * rng.random()
            crimp = (0.05 + 0.04 * rng.random()) * np.sin(v[:, 1] * np.pi * (3.0 + 2.0 * rng.random()) + rng.uniform(0, np.pi))
            x = v[:, 0] * w * 0.5 * (0.75 + 0.25 * S.smooth(0.0, 0.25, v[:, 1])) + crimp * S.smooth(0.05, 0.3, v[:, 1])
            y = v[:, 1] * ln
            verts = np.stack([cx + x, 0.01 + y, v[:, 2] * 0.11 + 0.003 * i], axis=1)[None]
            parts.append(S.elements_object(f'strip_wool_{c}_{i}', verts, tpl, np.zeros((1, 3)), S.KIND_CARD, rng))
    hi = S.join_elements(parts, 'strip_hi', attrs=('tpos', 'kind', 'lrand', 'root', 'mouth', 'dots', 'across'))
    me = bpy.data.meshes.new('strip_lo')
    nx, ny = CELLS * 8, 16
    vco = [(i / nx * CELLS, j / ny, -0.003) for j in range(ny + 1) for i in range(nx + 1)]
    faces = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(ny) for i in range(nx)]
    me.from_pydata(vco, [], faces)
    me.update()
    uvl = me.uv_layers.new(name='UVMap')
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    c = np.array(vco)
    uvl.data.foreach_set('uv', np.stack([c[lv, 0] / CELLS, c[lv, 1] * STRIP], axis=1).astype(np.float32).ravel())
    lo = bpy.data.objects.new('strip_lo', me)
    C.link_obj(lo)
    return lo, hi


# ----------------------------------------------------------------------------- one texture set
def _blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """A separable Gaussian blur of a 2-D array (zeros beyond the edges)."""
    r = max(1, int(math.ceil(3.0 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    for axis in (0, 1):
        p = np.pad(a, [(r, r) if ax == axis else (0, 0) for ax in (0, 1)])
        n = a.shape[axis]
        a = sum(float(k[j]) * (p[j:j + n] if axis == 0 else p[:, j:j + n]) for j in range(2 * r + 1))
    return a


def treat_ao(ao: np.ndarray, written: np.ndarray, floor: float = 0.0, soften: float = 0.0) -> tuple[np.ndarray, int]:
    """The recipe's AO_SOFTEN (a Gaussian blur of that many texels, only among the texels a bake wrote, so the empty
    space between islands never darkens them) and AO_FLOOR (no written texel darker than it): narrow slots between
    crossing clumps, crowded lock roots and deep wool seams otherwise bake near black, and the baked AO multiplies into
    the base colour. `ao` is one channel; returns it and how many texels the floor raised."""
    out = ao.astype(np.float64)
    m = written.astype(np.float64)
    if soften > 0:
        num = _blur(out * m, soften)
        den = _blur(m, soften)
        out = np.where(written, num / np.maximum(den, 1e-6), out)
    raised = 0
    if floor > 0:
        low = written & (out < floor)
        raised = int(low.sum())
        out = np.where(low, floor, out)
    return out.astype(np.float32), raised


def bake_set(prefix: str, size: int, out_dir: Path, plan, uv: str, with_strip: bool, paint, samples,
             extra_colours: tuple[str, ...] = (), base_ao: float = BASE_AO, card_style='fur',
             ao_floor: float = 0.0, ao_soften: float = 0.0) -> dict:
    """Bake one texture set for `plan` = [(low, sources, occluders)]: tangent normals, AO, base colour and roughness /
    coat (and optionally the strip), pack ORM (R AO, G roughness, B clearcoat mask), multiply `base_ao` of the AO into
    the colour, and save <prefix>_base.png (RGBA), _normal.png, _orm.png. `paint(pass)` assigns the sources' emission
    materials for 'base', 'rough' and each name in `extra_colours`; every extra colour pass is saved as
    <prefix>_<name>.png on the same UVs with the base's strip copied in (its tiles are neutral). `ao_floor` /
    `ao_soften` (the recipe's AO_FLOOR / AO_SOFTEN; 0 = off) treat the islands' AO before it is packed (treat_ao)."""
    s_n, s_ao, s_e = samples
    imgs = {k: new_image(f'{prefix}_{k}', size, alpha=False, color=(0.5, 0.5, 1.0, 1.0) if k == 'normal' else (0.0, 0.0, 0.0, 1.0),
                         srgb=k == 'base') for k in ('base', 'normal', 'ao', 'rc')}
    for k, (low, src, _) in enumerate(plan):
        bake('NORMAL', low, src, imgs['normal'], s_n, clear=k == 0, uv_layer=uv)
    for k, (low, _, occ) in enumerate(plan):
        bake('AO', low, occ, imgs['ao'], s_ao, clear=k == 0, uv_layer=uv)
    paint('base')
    for k, (low, src, _) in enumerate(plan):
        bake('EMIT', low, src, imgs['base'], s_e, clear=k == 0, uv_layer=uv)
    for name in extra_colours:
        imgs[name] = new_image(f'{prefix}_{name}', size, alpha=False, color=(0.0, 0.0, 0.0, 1.0), srgb=True)
        paint(name)
        for k, (low, src, _) in enumerate(plan):
            bake('EMIT', low, src, imgs[name], s_e, clear=k == 0, uv_layer=uv)
    paint('rough')
    for k, (low, src, _) in enumerate(plan):
        bake('EMIT', low, src, imgs['rc'], s_e, clear=k == 0, uv_layer=uv)
    alpha = None
    if with_strip:
        s_lo, s_hi = strip_scene(card_style)
        bake('NORMAL', s_lo, [s_hi], imgs['normal'], s_n, clear=False, cage=0.2, dist=0.3)
        bake('AO', s_lo, [s_hi], imgs['ao'], s_ao, clear=False, cage=0.2, dist=0.3)
        set_material([s_hi], strip_paint_material('strip_paint'))
        bake('EMIT', s_lo, [s_hi], imgs['base'], s_e, clear=False, cage=0.2, dist=0.3)
        set_material([s_hi], strip_paint_material('strip_rough', rough_pass=True))
        bake('EMIT', s_lo, [s_hi], imgs['rc'], s_e, clear=False, cage=0.2, dist=0.3)
        a_img = new_image(f'{prefix}_alpha', size, alpha=False, color=(0.0, 0.0, 0.0, 1.0), srgb=False)
        set_material([s_hi], strip_paint_material('strip_alpha', alpha_pass=True))
        bake('EMIT', s_lo, [s_hi], a_img, max(s_e, 8), clear=True, cage=0.2, dist=0.3)
        alpha = image_array(a_img)[..., 0]
        bpy.data.objects.remove(s_lo, do_unlink=True)
        bpy.data.objects.remove(s_hi, do_unlink=True)
        paint_hair_cells(imgs, alpha, [c for c, st in card_cell_styles(card_style).items() if st == 'hair'])
    ao = image_array(imgs['ao'])
    if ao_floor > 0 or ao_soften > 0:
        # the islands only (the strip's tiles are shared): the texels a bake wrote, by colour or AO
        rows = int(round(ao.shape[0] * STRIP)) if with_strip else 0
        isl = ao[rows:, :, 0]
        written = (image_array(imgs['base'])[rows:, :, :3].max(axis=-1) > 0.002) | (isl > 0.002)
        treated, raised = treat_ao(isl, written, ao_floor, ao_soften)
        ao[rows:, :, :3] = treated[..., None]
        imgs['ao'].pixels.foreach_set(np.ascontiguousarray(ao, dtype=np.float32).ravel())
        C.log(f'{prefix}: AO softened {ao_soften:g} texels, floor {ao_floor:g} ({raised} texels raised to it)')
    rc = image_array(imgs['rc'])
    orm = np.ones_like(ao)
    orm[..., 0] = ao[..., 0]
    orm[..., 1] = rc[..., 1]
    orm[..., 2] = rc[..., 2]
    imgs['orm'] = image_from_array(f'{prefix}_orm', orm, srgb=False, alpha=False)
    h, w = ao.shape[:2]
    strip_rows = int(round(h * STRIP))

    def compose(colour: np.ndarray, strip_from: np.ndarray | None) -> np.ndarray:
        rgba = colour.copy()
        rgba[..., :3] *= (1.0 - base_ao * (1.0 - ao[..., :1]))
        rgba[..., 3] = 1.0
        if strip_from is not None:
            rgba[:strip_rows] = strip_from[:strip_rows]
        elif alpha is not None:
            # alpha only inside the card cells of the strip; everything else is opaque
            xs = np.arange(w) * CELLS // w
            card_cols = np.isin(xs, CARD_CELLS)
            region = rgba[:strip_rows, card_cols]
            a = alpha[:strip_rows, card_cols]
            # transparent texels carry the tile's own grey, so mipmaps never pull a dark fringe into the lock edges
            region[..., :3] = np.where(a[..., None] < 0.02, 0.94, region[..., :3])
            region[..., 3] = a
            rgba[:strip_rows, card_cols] = region
        return rgba

    base_rgba = compose(image_array(imgs['base']), None)
    imgs['base_rgba'] = image_from_array(f'{prefix}_base_rgba', base_rgba, srgb=True, alpha=True)
    for name in extra_colours:
        rgba = compose(image_array(imgs[name]), base_rgba if with_strip else None)
        imgs[f'{name}_rgba'] = image_from_array(f'{prefix}_{name}_rgba', rgba, srgb=True, alpha=True)
    save_png(imgs['base_rgba'], out_dir / f'{prefix}_base.png')
    save_png(imgs['normal'], out_dir / f'{prefix}_normal.png')
    save_png(imgs['orm'], out_dir / f'{prefix}_orm.png')
    for name in extra_colours:
        save_png(imgs[f'{name}_rgba'], out_dir / f'{prefix}_{name}.png')
    # over the texels a bake wrote (any colour or AO), not the empty space between the islands
    covered = (image_array(imgs['base'])[strip_rows:, :, :3].max(axis=-1) > 0.002) | (ao[strip_rows:, :, 0] > 0.002)
    q = np.percentile(ao[strip_rows:, :, 0][covered] if covered.any() else ao[strip_rows:, :, 0], [5, 50, 95])
    C.log(f'{prefix}: AO percentiles 5/50/95 = {q[0]:.2f} / {q[1]:.2f} / {q[2]:.2f} (healthy median ≈ 0.9)')
    return imgs


# ----------------------------------------------------------------------------- cards' colours
def sample_vertex_colours(elems: bpy.types.Object, body: bpy.types.Object, base: np.ndarray, layer: str = 'Col',
                          active: bool = True, uv: str = 'UVMap', scale: float = 1.0) -> np.ndarray:
    """Each card or lock takes the baked colour at its root on the body (linear), so the markings carry on across it."""
    h, w = base.shape[:2]
    roots = S.attr_array(elems, 'root')
    me = body.data
    me.calc_loop_triangles()
    uvd = me.uv_layers[uv].data
    uvs = np.empty(len(uvd) * 2, np.float32)
    uvd.foreach_get('uv', uvs)
    uvs = uvs.reshape(-1, 2)
    tri_of_poly: dict[int, list] = {}
    for lt in me.loop_triangles:
        tri_of_poly.setdefault(lt.polygon_index, []).append(lt)
    cache: dict[tuple, tuple] = {}
    cols = np.ones((len(roots), 3), np.float32)
    for i, r in enumerate(roots):
        key = (round(float(r[0]), 5), round(float(r[1]), 5), round(float(r[2]), 5))
        if key not in cache:
            ok, loc, _nrm, fi = body.closest_point_on_mesh(Vector(r))
            col = (1.0, 1.0, 1.0)
            if ok:
                best = None
                for lt in tri_of_poly.get(fi, []):
                    a, b, c = (me.vertices[vi].co for vi in lt.vertices)
                    bc = S.barycentric(loc, a, b, c)
                    if best is None or min(bc) > min(best[0]):
                        best = (bc, lt)
                if best is not None:
                    bc, lt = best
                    bc = np.clip(np.array(bc), 0, 1)
                    bc = bc / max(bc.sum(), 1e-9)
                    u, v = (uvs[lt.loops[0]] * bc[0] + uvs[lt.loops[1]] * bc[1] + uvs[lt.loops[2]] * bc[2])
                    px, py = min(w - 1, max(0, int(u * w))), min(h - 1, max(0, int(v * h)))
                    col = tuple(float(x) for x in base[py, px, :3])
            cache[key] = col
        cols[i] = cache[key]
    # image.pixels of an 8-bit sRGB image are sRGB-encoded; a colour attribute (glTF COLOR_n) is linear
    srgb = np.clip(cols * scale, 0, 1)
    lin = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    S.set_colour_attr(elems, layer, lin, active=active)
    return lin
