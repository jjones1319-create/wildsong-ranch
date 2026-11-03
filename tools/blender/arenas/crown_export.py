"""The Crown Amphitheatre's export stage: the baked groups → the game meshes (one per atlas = one draw call), Full
and Lite (Lite = the faces flagged `lite` plus the Lite-only bowl, with the half-size atlases), the sky domes, the
shadow catcher, the anchors → crown_raw.glb, crown_lite_raw.glb and crown_build.json (anchors, fly-in, sun, seats,
the painted crowd's rows, triangles, sources, the fly-in's clearance).
"""
from __future__ import annotations

import json
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from lib import common as C
from lib.nodes import new_mat
import kit as K
import guild_bake as GB
import crown as CR
import crown_bake as CB
import crown_bowl as BW
import crown_gates as GT
import crown_layout as L

SHADOW_R = 14.0


def finalise(ob: bpy.types.Object, group: str, lite: bool) -> None:
    """One material named for its atlas, only the bake UVs (as UVMap), no paint attributes."""
    me = ob.data
    for layer in [x for x in me.uv_layers if x.name != 'BakeUV']:
        me.uv_layers.remove(layer)
    me.uv_layers['BakeUV'].name = 'UVMap'
    for a in ('lite', 'near', 'crowd', 'riser', 'v0', 'hgt', 'row', 'wedge', 'fan', 'path', 'tint', 'aspect'):
        if a in me.attributes:
            me.attributes.remove(me.attributes[a])
    for a in [a.name for a in me.color_attributes]:
        me.color_attributes.remove(me.color_attributes[a])
    tex = f'{group}_lite' if lite else group
    mat = bpy.data.materials.get(f'crown_{tex}')
    if mat is None:
        img = bpy.data.images.load(str(CB.TEX / f'{tex}.png'), check_existing=True)
        mat = K.emission_image_mat(f'crown_{tex}', img, 'UVMap')
        mat['atlas'] = group
        mat['doubleSided'] = CR.GROUPS.get(group, (0, False))[1]
    me.materials.clear()
    me.materials.append(mat)


def to_gltf(v) -> list[float]:
    return GB.to_gltf(v)


def seats() -> list[dict]:
    out = []
    for s in BW.live_seats() + GT.patron_seats():
        x, y, z = s['p']
        dx, dy = math.cos(s['face']), math.sin(s['face'])
        out.append({'p': to_gltf((x, y, z)), 'yaw': round(math.atan2(dx, -dy), 4), 'row': s['row'], 'section': s['section'],
                    'kind': s['kind'], 'lite': s['lite']})
    return out


def painted_count() -> int:
    """About how many spectators the bowl's texture paints (rows that are not live, less aisles and cut-outs)."""
    from crown_geo import perimeter
    n = 0.0
    for r in L.rows():
        if r['tier'] == 0 and r['k'] == 0:
            continue
        P = perimeter(r['off0'] + 0.4)
        aisles = L.TIERS[r['tier']]['aisles'] * L.AISLE_W * (1 + (r['off0'] - L.tier_bounds()[r['tier']]['off0']) / 40)
        cut = (4 * L.GATE_HALF + 2 * L.BOX_HALF) * 1.4 if r['tier'] == 0 else 0.0
        frac = 0.5 if (r['tier'] == 0 and r['k'] == 1) else 1.0
        n += (P - aisles - cut) / 0.52 * 0.9 * frac
    return int(round(n, -2))


def catmull(keys: list, per: int = 80) -> np.ndarray:
    """Centripetal Catmull–Rom through the fly-in eyes (as three.js's CatmullRomCurve3 'centripetal' draws it)."""
    P = [np.asarray(k, np.float64) for k in keys]
    P = [2 * P[0] - P[1]] + P + [2 * P[-1] - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + max(1e-4, np.linalg.norm(p1 - p0) ** 0.5)
        t2 = t1 + max(1e-4, np.linalg.norm(p2 - p1) ** 0.5)
        t3 = t2 + max(1e-4, np.linalg.norm(p3 - p2) ** 0.5)
        for t in np.linspace(t1, t2, per, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-2])
    return np.asarray(out)


def clearance(meshes: list[bpy.types.Object]) -> dict:
    """The fly-in path's closest approach to any shipped surface (the sky domes and the catcher excepted)."""
    dg = bpy.context.evaluated_depsgraph_get()
    trees = []
    for o in meshes:
        if o.name.startswith(('sky', 'shadow')):
            continue
        bm = bmesh.new()
        bm.from_object(o, dg)
        bm.transform(o.matrix_world)
        trees.append((o.name, BVHTree.FromBMesh(bm)))
        bm.free()
    path = catmull([e for e, _, _, _ in CR.FLY])
    last = 80 * (len(CR.FLY) - 2)          # where the final segment (into the runtime's face-off) begins
    best, early = (1e9, None, None), 1e9
    per_key = []
    for i, p in enumerate(path):
        for name, tr in trees:
            hit = tr.find_nearest(Vector(p))
            if hit[0] is not None and hit[3] < best[0]:
                best = (hit[3], name, [round(float(x), 2) for x in p])
            if hit[0] is not None and i < last:
                early = min(early, hit[3])
        if i % 80 == 0:
            per_key.append(round(min((tr.find_nearest(Vector(p))[3] or 1e9) for _, tr in trees), 2))
    return {'minMetres': round(best[0], 2), 'nearest': best[1], 'at': best[2], 'atKeys': per_key,
            'minBeforeFaceOffMetres': round(early, 2),
            'note': 'closest approach of the eye path (centripetal Catmull–Rom through the cam_fly eyes) to any arena surface; the last key is the runtime face-off'}


def shadow_catcher() -> bpy.types.Object:
    segs = 72
    verts = [(0.0, 0.0, 0.004)] + [(SHADOW_R * math.cos(2 * math.pi * i / segs), SHADOW_R * math.sin(2 * math.pi * i / segs), 0.004) for i in range(segs)]
    ob = K.obj_from_arrays('shadow_catcher', verts, [(0, 1 + i, 1 + (i + 1) % segs) for i in range(segs)], C.collection('SKY'))
    ob.data.uv_layers.new(name='UVMap')
    m, nb = new_mat('crown_shadow_catcher')
    K.principled(nb, (0, 0, 0, 1), 1.0)
    ob.data.materials.append(m)
    ob.hide_render = True
    return ob


def stage_export() -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(CR.OUT / 'crown_baked.blend'))
    O = bpy.data.objects
    full, lite, tris_full, tris_lite = [], [], {}, {}
    for g, (_, _, _, lite_only) in CR.GROUPS.items():
        ob = O[f'arena_{g}']
        if lite_only:
            ob.name = ob.data.name = f'lite_{g}'
            finalise(ob, g, True)
            lite.append(ob)
            tris_lite[ob.name] = K.tri_count(ob)
            continue
        keep = GB.face_attr(ob, 'lite').astype(bool)
        if keep.any():
            lp = GB.subset(ob, keep, f'lite_{g}')
            finalise(lp, g, True)
            lite.append(lp)
            tris_lite[lp.name] = K.tri_count(lp)
        finalise(ob, g, False)
        full.append(ob)
        tris_full[ob.name] = K.tri_count(ob)
    for half in ('front', 'back'):
        for prefix, dst, tri in (('sky', full, tris_full), ('sky_lite', lite, tris_lite)):
            ob = O[f'{prefix}_{half}']
            ob.hide_render = False
            img = bpy.data.images.load(str(CB.TEX / f'{prefix}_{half}.png'), check_existing=True)
            mname = f'crown_{prefix}_{half}'
            mat = bpy.data.materials.get(mname) or K.emission_image_mat(mname, img, 'UVMap')
            mat['atlas'] = f'{prefix}_{half}'
            mat['doubleSided'] = True
            ob.data.uv_layers['BakeUV'].name = 'UVMap'
            ob.data.materials.clear()
            ob.data.materials.append(mat)
            dst.append(ob)
            tri[ob.name] = K.tri_count(ob)
    catcher = shadow_catcher()
    full.append(catcher)
    lite.append(catcher)
    with C.Timer('fly-in clearance'):
        clear = clearance([o for o in full if o.type == 'MESH'])
    C.log(f'fly-in clearance: {clear}')
    anchors = [o for o in O if o.type == 'EMPTY' and any(c.name == 'ANCHORS' for c in o.users_collection)]
    for o in anchors:                       # an anchor must keep its exact name (the game looks it up by name)
        base = o.name.split('.')[0]
        if base != o.name:
            other = O.get(base)
            if other is not None:
                other.name = base + '_mesh'
            o.name = base
    from lib import export as EX
    before = dict(EX.EXPORT_OPTIONS)
    EX.EXPORT_OPTIONS.update(export_normals=False, export_tangents=False, export_animations=False, export_skins=False,
                             export_image_format='NONE', export_materials='EXPORT', export_vertex_color='NONE',
                             export_all_vertex_colors=False, export_extras=True, export_apply=True)
    try:
        EX.export_glb(CR.OUT / 'crown_raw.glb', full + anchors)
        EX.export_glb(CR.OUT / 'crown_lite_raw.glb', lite + anchors)
    finally:
        EX.EXPORT_OPTIONS.clear()
        EX.EXPORT_OPTIONS.update(before)
    man = json.loads((K.CACHE / 'crown_manifest.json').read_text(encoding='utf-8'))
    st = seats()

    def fwd(o):
        return to_gltf((o.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()) if o.name.startswith(('spawn', 'gate', 'tunnel')) else None
    info = {
        'units': 'metres, glTF Y-up; the sand at y = 0 centred on the origin; the duel ring\'s curb starts at ringRadius',
        'ringRadius': L.RING_R,
        'cameraRadius': L.CAMERA_R,
        'anchors': {o.name: {'position': to_gltf(o.location), 'forward': fwd(o),
                             **({'target': to_gltf(o['target']), 'fovDeg': o['fovDeg']} if 'target' in o else {}),
                             **({'t': o['t']} if 't' in o else {})} for o in sorted(anchors, key=lambda o: o.name)},
        'flyIn': [{'node': f'cam_fly_{i}', 'eye': to_gltf(e), 'target': to_gltf(t), 't': tt, 'fovDeg': f} for i, (e, t, tt, f) in enumerate(CR.FLY)],
        'flyInClearance': clear,
        'sun': {'direction': to_gltf(CR.SUN_DIR), 'color': [1.0, 0.94, 0.84]},
        'seats': st,
        'crowd': {
            'liveSeats': len(st), 'liveSeatsLite': sum(1 for s in st if s['lite']),
            'liveRows': 'row 0 (the front marble row) all round; row 1 too on the long sides (sections north and south); the Patrons\' box (section patrons, 2 rows)',
            'paintedRows': 'every other seat row is baked with a painted crowd: rows 1-13 of the lowest tier (row 1 only at the gate ends), all 14 of the middle tier and all 10 of the top tier',
            'paintedSpectators': painted_count(),
            'bakedInto': {'full': ['low_n', 'low_s', 'mid', 'top'], 'lite': ['lbowl_low', 'lbowl_high']},
        },
        'trianglesFull': tris_full, 'trianglesLite': tris_lite,
        'sources': [{'id': a, **{k: man[a][k] for k in ('type', 'name', 'authors', 'url', 'license')}} for a in man],
    }
    (CR.OUT / 'crown_build.json').write_text(json.dumps(info, indent=1), encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(CR.OUT / 'crown_export.blend'), compress=False)
    C.log(f'export: full {sum(tris_full.values())} tris in {len(full)} meshes; lite {sum(tris_lite.values())} in {len(lite)}')
    return info
