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
BASE_AO = 0.38         # share of the baked AO multiplied into the base colour (crevices stay dark on any renderer)


def pack_atlas(objs: list[bpy.types.Object], uv_name: str, strip: float, angle_deg: float = 62.0,
               island_margin: float = 0.005, pack_margin: float = 0.003) -> None:
    """Smart-project the objects together into `uv_name` at an even texel density, leaving the bottom `strip`."""
    for o in objs:
        if uv_name not in o.data.uv_layers:
            o.data.uv_layers.new(name=uv_name)
        o.data.uv_layers.active = o.data.uv_layers[uv_name]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg), island_margin=island_margin, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(rotate=True, margin=pack_margin)
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        uv = o.data.uv_layers[uv_name].data
        arr = np.empty(len(uv) * 2, np.float32)
        uv.foreach_get('uv', arr)
        arr = arr.reshape(-1, 2)
        if strip > 0:
            arr = arr * (1.0 - strip)
            arr[:, 1] += strip
        uv.foreach_set('uv', arr.ravel())
        if 'UVMap' in o.data.uv_layers:
            o.data.uv_layers.active = o.data.uv_layers['UVMap']


def strip_uvs(ob: bpy.types.Object, cells: tuple[int, ...], uv_name: str = 'UVMap') -> None:
    """Each element maps into one strip cell (across → u, along → v), picked by its random number."""
    me = ob.data
    if uv_name not in me.uv_layers:
        me.uv_layers.new(name=uv_name)
    across = S.attr_array(ob, 'across')
    tpos = S.attr_array(ob, 'tpos')
    lrand = S.attr_array(ob, 'lrand')
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


def strip_scene():
    """The strip's high detail: per lock cell one tuft lock laid flat; per card cell a cluster of soft locks with
    rounded tips at different lengths. The low is a plane whose UVs are the strip."""
    rng = np.random.default_rng(5)
    parts = []
    for c in LOCK_CELLS:
        tpl = S.lock_template(28, 28, 3, strand=0.18)
        v = tpl[0]
        verts = np.stack([c + 0.5 + v[:, 0] * 0.5, 0.012 + v[:, 1] * 0.976, v[:, 2] * 0.14], axis=1)[None]
        parts.append(S.elements_object(f'strip_lock_{c}', verts, tpl, np.zeros((1, 3)), S.KIND_TUFT, rng))
    for c in CARD_CELLS:
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
def bake_set(prefix: str, size: int, out_dir: Path, plan, uv: str, with_strip: bool, paint, samples,
             extra_colours: tuple[str, ...] = (), base_ao: float = BASE_AO) -> dict:
    """Bake one texture set for `plan` = [(low, sources, occluders)]: tangent normals, AO, base colour and roughness /
    coat (and optionally the strip), pack ORM (R AO, G roughness, B clearcoat mask), multiply `base_ao` of the AO into
    the colour, and save <prefix>_base.png (RGBA), _normal.png, _orm.png. `paint(pass)` assigns the sources' emission
    materials for 'base', 'rough' and each name in `extra_colours`; every extra colour pass is saved as
    <prefix>_<name>.png on the same UVs with the base's strip copied in (its tiles are neutral)."""
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
        s_lo, s_hi = strip_scene()
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
    ao = image_array(imgs['ao'])
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
    q = np.percentile(ao[strip_rows:, :, 0], [5, 50, 95])
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
