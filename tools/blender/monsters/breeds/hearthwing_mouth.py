"""Hearthwing Ultra's mouth (Nov 13): a real opening for the fire breath (cast, fly_cast), the strike's snap and the smiles.

The approach is Cinderlynx's (cinderlynx_mouth.py), parametrised for both forms by a spec from hearthwing_form.Form:
- the low body is cut along the lip line before its decimation (`cut`), the two lips parting by a hairline (GAP), so at
  rest the slit shows the dark mouth behind it and the weight hook can tell the lower lip from the upper by position;
- the lower jaw's skin rides the `jaw` bone (`jaw_weight`, crisp at the cut); the corners stay joined and stretch;
- behind the lips an inner skin (`mouth_mesh`, a prop): copies of the skin along the lips sunk inward and turned inside
  out (seen only from inside the mouth), a palate roof and a tongue floor (the muzzle's own cross-sections), a throat cap
  at the back and two small fangs. Every vertex gets a part (the prop's `pg`): 1 the palate, -1 the floor and tongue, 2
  the throat, 3 the fangs.

Model space throughout (the monster faces -Y, Z is up). The spec:
  lip(x, y) -> z          the lip line's height
  corner_y                the mouth's corners (the cut runs from here forward round the front)
  x_max, z_band           the cut region's half width and half height about the lip
  back_y                  the inner skin's back edge and the throat cap (a little behind the corners)
  hinge_y, jaw_z0         the jaw's hinge (y) and the lowest skin it moves (z below the lip)
  k                       the face's scale (1 = the young form)
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth

GAP = 0.0016
INSET = 0.0022
ROOF_F = 0.012
FLOOR_F = -0.016


def lip_f(spec: dict, p: np.ndarray) -> np.ndarray:
    """Signed height above the lip line: > 0 the upper jaw, < 0 the lower."""
    return p[:, 2] - spec['lip'](p[:, 0], p[:, 1])


def cut_region(spec: dict, p: np.ndarray) -> np.ndarray:
    k = spec['k']
    return (p[:, 1] < spec['corner_y']) & (np.abs(p[:, 0]) < spec['x_max']) & (np.abs(lip_f(spec, p)) < spec['z_band'] * k)


def cut(ob: bpy.types.Object, spec: dict) -> dict:
    """Cut `ob` (the low voxel body, before its decimation) along the lip line and part the lips by GAP."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    co = np.array([v.co[:] for v in bm.verts], np.float64)
    f = lip_f(spec, co)
    f = np.where(np.abs(f) < 1e-7, 1e-7, f)
    reg = cut_region(spec, co)
    fv = {v: float(f[i]) for i, v in enumerate(bm.verts)}
    rv = {v: bool(reg[i]) for i, v in enumerate(bm.verts)}
    cross = [e for e in bm.edges if rv[e.verts[0]] and rv[e.verts[1]] and fv[e.verts[0]] * fv[e.verts[1]] < 0.0]
    new: set = set()
    for e in cross:
        a, b = e.verts
        t = fv[a] / (fv[a] - fv[b])
        _ne, nv = bmesh.utils.edge_split(e, a, min(max(t, 0.02), 0.98))
        new.add(nv)
    faces = {fc for v in new for fc in v.link_faces}
    joined = odd = 0
    for fc in faces:
        vs = [v for v in fc.verts if v in new]
        if len(vs) == 2:
            if not any(e.other_vert(vs[0]) is vs[1] for e in vs[0].link_edges):
                bmesh.ops.connect_verts(bm, verts=vs)
                joined += 1
        elif len(vs) > 2:
            odd += 1
    chain = [e for e in bm.edges if e.verts[0] in new and e.verts[1] in new]
    res = bmesh.ops.split_edges(bm, edges=chain)
    up_n = dn_n = 0
    touched = {v for e in res['edges'] for v in e.verts}
    for v in touched:
        if not v.link_faces:
            continue
        cen = np.array([fc.calc_center_median()[:] for fc in v.link_faces], np.float64)
        sides = np.sign(lip_f(spec, cen))
        if sides.min() < 0 < sides.max():
            continue                    # a corner, shared by both lips: stays put
        sf = float(np.mean(lip_f(spec, cen)))
        v.co = (v.co[0], v.co[1], v.co[2] + GAP * 0.5 * (1.0 if sf > 0 else -1.0))
        if sf > 0:
            up_n += 1
        else:
            dn_n += 1
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    info = {'crossings': len(cross), 'joined': joined, 'odd_faces': odd, 'chain_edges': len(chain), 'upper': up_n, 'lower': dn_n}
    C.log(f'mouth cut: {info}')
    return info


def jaw_weight(spec: dict, p: np.ndarray) -> np.ndarray:
    """0..1: the lower jaw in front of the corners fully (crisp at the cut), fading back to the hinge and down the throat."""
    f = lip_f(spec, p)
    k = spec['k']
    return (smooth(spec['hinge_y'], spec['corner_y'], p[:, 1]) * smooth(0.0003, -0.0004, f)
            * smooth(-spec['jaw_z0'] * k, -0.6 * spec['jaw_z0'] * k, f) * smooth(spec['x_max'] * 1.25, spec['x_max'], np.abs(p[:, 0])))


def _section(spec: dict, co: np.ndarray, me, lvl: float) -> np.ndarray | None:
    f = lip_f(spec, co) - lvl
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)
    fa, fb = f[ev[:, 0]], f[ev[:, 1]]
    m = (fa * fb < 0) & (co[ev[:, 0], 1] < spec['back_y'] + 0.004 * spec['k']) & (np.abs(co[ev[:, 0], 0]) < spec['x_max'] * 1.4)
    if m.sum() < 6:
        return None
    t = (fa[m] / (fa[m] - fb[m]))[:, None]
    p = co[ev[m, 0]] * (1 - t) + co[ev[m, 1]] * t
    p = p[p[:, 1] < spec['back_y']]
    if len(p) < 6:
        return None
    xs = p[np.argsort(p[:, 1])[-6:], 0]
    zb = float(np.median(p[:, 2]))
    back = np.array([(x, spec['back_y'], zb) for x in np.linspace(float(xs.min()), float(xs.max()), 7)[1:-1]])
    p = np.vstack([p, back]) if len(back) else p
    c = p.mean(axis=0)
    ang = np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0])
    return p[np.argsort(ang)]


def mouth_mesh(name: str, lo: bpy.types.Object, spec: dict, target: int = 0) -> bpy.types.Object:
    """The inner skin, the palate, the floor, the throat cap and the fangs, as one mesh; `pg` = its part."""
    k = spec['k']
    me = lo.data
    nv = len(me.vertices)
    co = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).astype(np.float64)
    vn = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get('normal', vn)
    vn = vn.reshape(-1, 3).astype(np.float64)
    f = lip_f(spec, co)
    polys = [list(p.vertices) for p in me.polygons]
    cen = np.array([co[p].mean(axis=0) for p in polys])
    pf = lip_f(spec, cen)
    take = (cen[:, 1] < spec['back_y']) & (np.abs(cen[:, 0]) < spec['x_max'] * 1.1) & (pf > FLOOR_F * k - 0.002) & (pf < ROOF_F * k + 0.002)
    sel = [p for p, t in zip(polys, take) if t]
    used = sorted({i for p in sel for i in p})
    remap = {i: j for j, i in enumerate(used)}
    sink = INSET * k * smooth(0.0, 0.006 * k, np.abs(f[used]))
    pts = co[used] - vn[used] * sink[:, None]
    verts = [tuple(p) for p in pts]
    faces = [tuple(remap[i] for i in reversed(p)) for p in sel]
    parts = list(np.where(f[used] > 0, 1.0, -1.0))
    for lvl, sign in ((ROOF_F * k, 1.0), (FLOOR_F * k, -1.0)):
        ring = _section(spec, co, me, lvl)
        if ring is None:
            C.log(f'{name}: no cross-section at f={lvl:.3f}')
            continue
        c0 = ring.mean(axis=0)
        ring = c0 + (ring - c0) * 0.94
        b0 = len(verts)
        verts += [tuple(p) for p in np.vstack([c0[None], ring])]
        parts += [sign] * (len(ring) + 1)
        m = len(ring)
        for j in range(m):
            a_, b_ = b0 + 1 + j, b0 + 1 + (j + 1) % m
            faces.append((b0, a_, b_) if sign < 0 else (b0, b_, a_))
    # the throat cap at the back, facing forward into the mouth
    zc = float(spec['lip'](np.zeros(1), np.full(1, spec['back_y']))[0]) - 0.006 * k
    rx, rz = spec['x_max'] * 0.8, 0.036 * k
    base = len(verts)
    verts.append((0.0, spec['back_y'], zc))
    for j in range(24):
        a = 2 * math.pi * j / 24
        verts.append((rx * math.cos(a), spec['back_y'], zc + rz * math.sin(a)))
    parts += [2.0] * 25
    for j in range(24):
        faces.append((base, base + 1 + j, base + 1 + (j + 1) % 24))
    # two small fangs from the upper lip line near the front, pointing down
    for fx in (0.02 * k, -0.02 * k):
        fy = spec['fang_y']
        z0 = float(spec['lip'](np.array([fx]), np.array([fy]))[0]) + 0.0012 * k
        b0 = len(verts)
        for j in range(8):
            a = 2 * math.pi * j / 8
            verts.append((fx + 0.0019 * k * math.cos(a), fy + 0.0016 * k * math.sin(a), z0))
        verts.append((fx, fy - 0.001 * k, z0 - 0.0062 * k))
        parts += [3.0] * 9
        for j in range(8):
            faces.append((b0 + (j + 1) % 8, b0 + j, b0 + 8))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    mesh.shade_smooth()
    ob = bpy.data.objects.new(name, mesh)
    C.link_obj(ob)
    nsel = len(sel)
    if target and len(mesh.polygons) > target:
        pv = np.asarray(parts)
        cw = np.empty(len(mesh.vertices) * 3, np.float32)
        mesh.vertices.foreach_get('co', cw)
        fl = np.abs(lip_f(spec, cw.reshape(-1, 3).astype(np.float64)))
        idx = np.nonzero((np.abs(pv) < 1.5) & (fl > 0.006 * k))[0]
        vg = ob.vertex_groups.new(name='free')
        if len(idx):
            vg.add(idx.tolist(), 1.0, 'REPLACE')
        dm = ob.modifiers.new('decimate', 'DECIMATE')
        dm.decimate_type = 'COLLAPSE'
        dm.ratio = max(0.02, target / len(mesh.polygons))
        dm.use_collapse_triangulate = True
        dm.vertex_group = 'free'
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_apply(modifier=dm.name)
        ob.vertex_groups.clear()
    if len(ob.data.vertices) != len(parts):
        from mathutils.kdtree import KDTree
        kd = KDTree(len(verts))
        for i, p in enumerate(verts):
            kd.insert(p, i)
        kd.balance()
        parts = [parts[kd.find(v.co)[1]] for v in ob.data.vertices]
    S.add_attr(ob, 'mouth_part_tmp', np.asarray(parts, np.float64))
    C.log(f'{name}: inner skin {nsel} faces, {len(ob.data.polygons)} faces in all')
    return ob


MOUTH_COLS = {'palate': '#5E2630', 'gum': '#6A2A34', 'tongue': '#C9606E', 'throat': '#2A0C12', 'fang': '#F2ECE2', 'lip': '#2A181C'}


def mouth_colours(spec: dict, co: np.ndarray, mp: np.ndarray, lin) -> np.ndarray:
    """A dark rose palate and gums, a pink tongue down the middle of the floor, a deep throat, ivory fangs, dark rims."""
    k = spec['k']
    f = lip_f(spec, co)
    rgb = np.tile(lin(MOUTH_COLS['palate']), (len(co), 1))
    tongue = smooth(0.03 * k, 0.018 * k, np.abs(co[:, 0])) * smooth(-0.0015 * k, -0.005 * k, f)
    floor = lin(MOUTH_COLS['gum'])[None] * (1 - tongue[:, None]) + lin(MOUTH_COLS['tongue'])[None] * tongue[:, None]
    rgb = np.where((mp < -0.5)[:, None], floor, rgb)
    rgb = np.where((np.abs(mp - 2) < 0.5)[:, None], lin(MOUTH_COLS['throat'])[None], rgb)
    rgb = np.where((np.abs(mp - 3) < 0.5)[:, None], lin(MOUTH_COLS['fang'])[None], rgb)
    rim = smooth(0.004 * k, 0.0012 * k, np.abs(f)) * (np.abs(mp) < 1.5)
    return rgb * (1 - rim[:, None]) + lin(MOUTH_COLS['lip'])[None] * rim[:, None]
