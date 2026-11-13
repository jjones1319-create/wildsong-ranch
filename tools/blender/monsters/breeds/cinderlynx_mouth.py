"""Cinderlynx Ultra's mouth (Nov 12, "do all of the upgrade"): a real opening for the swipe, the cast and the smiles.

The low body is cut along the lip line, the crease under the whisker pads from one mouth corner round the front to the
other (`cut`, from the recipe's `carve_low`, before the decimation). The two lips part by a hairline (`GAP`), so the
weight hook can tell the lower lip from the upper by position, and at rest the slit shows the dark mouth behind it. The
lower jaw's skin rides the `jaw` bone (`jaw_weight`); the corners stay joined and stretch.

Behind the lips, the mouth is an inner skin (`mouth_mesh`, a prop): a copy of the low body's muzzle and lower jaw, sunk a
little inward away from the cut and turned inside out, so it only ever shows from inside the mouth (from outside every
face of it looks away and is culled). It takes the skin's own weights (head or jaw, the same blend), so it follows the
lips exactly. A throat cap closes it at the back, and two small fangs hang from the upper jaw, hidden behind the lower
lip while the mouth is shut. Every vertex gets `mouth_part`: 1 the palate (upper), -1 the floor and tongue (lower),
2 the throat, 3 the fangs.

All shapes are head-local (the recipe's H / Hinv map them to model space): pass `to_local` / `to_world`.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib.surface import smooth, v3

CORNER_Y = -0.47            # the mouth's corners (head-local y); the cut runs from here forward round the front
HINGE_L = (0.0, -0.425, 0.762)
CHIN_L = (0.0, -0.537, 0.738)
GAP = 0.0008                # the lips' parting at rest (m, model space; Nov 13: a hairline, the seam showed pink)
INSET = 0.0022              # how far the inner skin sinks inward, away from the cut (m)
BACK_Y = -0.432             # the inner skin's back edge and the throat cap (head-local y)
FANG_L = [(s * 0.018, -0.53) for s in (1, -1)]        # (x, y) head-local, at the lip line


def lip_z(hx: np.ndarray, hy: np.ndarray) -> np.ndarray:
    """The lip line's height (head-local): the crease between the whisker pads and the chin, rising a little toward the
    corners (a cat's mouth line turns up at the back)."""
    ax = np.abs(hx)
    return 0.7515 - 0.0035 * smooth(0.0, 0.03, ax) + 0.012 * smooth(-0.515, -0.47, hy)


def lip_f(hl: np.ndarray) -> np.ndarray:
    """Signed height above the lip line (head-local): > 0 the upper jaw, < 0 the lower."""
    return hl[:, 2] - lip_z(hl[:, 0], hl[:, 1])


def cut_region(hl: np.ndarray) -> np.ndarray:
    return (hl[:, 1] < CORNER_Y) & (np.abs(hl[:, 0]) < 0.085) & (hl[:, 2] > 0.7) & (hl[:, 2] < 0.81)


def cut(ob: bpy.types.Object, to_local, k: float) -> dict:
    """Cut `ob` (the low voxel body, before the decimation) along the lip line and part the lips by GAP. `k` = the
    head's scale (head-local → model). Returns counts for the log."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    co = np.array([v.co[:] for v in bm.verts], np.float64)
    hl = to_local(co)
    f = lip_f(hl)
    f = np.where(np.abs(f) < 1e-7, 1e-7, f)
    reg = cut_region(hl)
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
    joined, odd = 0, 0
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
    moved_up = moved_dn = 0
    touched = {v for e in res['edges'] for v in e.verts}
    up = np.array((0.0, 0.0, 1.0))
    for v in touched:
        if len(v.link_faces) == 0:
            continue
        cen = np.array([fc.calc_center_median()[:] for fc in v.link_faces], np.float64)
        sf = float(np.mean(lip_f(to_local(cen))))
        # the corners (shared by both lips: faces on both sides) stay put
        sides = np.sign(lip_f(to_local(cen)))
        if sides.min() < 0 < sides.max():
            continue
        d = up * (GAP * 0.5) * (1.0 if sf > 0 else -1.0)
        v.co = tuple(np.asarray(v.co[:]) + d)
        if sf > 0:
            moved_up += 1
        else:
            moved_dn += 1
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    info = {'crossings': len(cross), 'joined': joined, 'odd_faces': odd, 'chain_edges': len(chain), 'upper': moved_up, 'lower': moved_dn}
    C.log(f'mouth cut: {info}')
    return info


def jaw_weight(hl: np.ndarray) -> np.ndarray:
    """0..1: how much a point of the skin (head-local) rides the jaw: the lower jaw in front of the corners fully,
    fading back to the hinge (the corners stretch) and down into the throat."""
    f = lip_f(hl)
    return (smooth(HINGE_L[1], CORNER_Y, hl[:, 1]) * smooth(0.0003, -0.0004, f) * smooth(0.695, 0.722, hl[:, 2])
            * smooth(0.1, 0.08, np.abs(hl[:, 0])))


ROOF_F = 0.012               # the palate's roof: this far above the lip line (head-local)
FLOOR_F = -0.016            # the floor (and the tongue): this far below


def _section(co: np.ndarray, hl: np.ndarray, me, lvl: float, to_local) -> np.ndarray | None:
    """The body's cross-section where lip_f = lvl, in front of BACK_Y (head-local points, sorted counter-clockwise
    round their centre seen from above), closed across the back by the sort."""
    f = lip_f(hl) - lvl
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)
    fa, fb = f[ev[:, 0]], f[ev[:, 1]]
    m = (fa * fb < 0) & (hl[ev[:, 0], 1] < BACK_Y + 0.004) & (np.abs(hl[ev[:, 0], 0]) < 0.12)
    if m.sum() < 6:
        return None
    t = (fa[m] / (fa[m] - fb[m]))[:, None]
    p = hl[ev[m, 0]] * (1 - t) + hl[ev[m, 1]] * t
    p = p[p[:, 1] < BACK_Y]
    if len(p) < 6:
        return None
    # the back's closing edge: points along hy = BACK_Y between the two ends
    xs = p[np.argsort(p[:, 1])[-6:], 0]
    lo_x, hi_x = float(xs.min()), float(xs.max())
    zb = float(np.median(p[:, 2]))
    back = np.array([(x, BACK_Y, zb) for x in np.linspace(lo_x, hi_x, 7)[1:-1]])
    p = np.vstack([p, back]) if len(back) else p
    c = p.mean(axis=0)
    ang = np.arctan2(p[:, 1] - c[1], p[:, 0] - c[0])
    return p[np.argsort(ang)]


def _ellipse_cap(cy: float, cz: float, rx: float, rz: float, n: int):
    pts = [(rx * math.cos(2 * math.pi * k / n), cy, cz + rz * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return [(0.0, cy, cz)] + pts


def mouth_mesh(name: str, lo: bpy.types.Object, to_local, to_world, k: float, inside=None, target: int = 0) -> bpy.types.Object:
    """The inner skin, the throat cap and the fangs, as one prop (see the module's notes). `lo` = the cut low body;
    `inside(points)` (optional) → bool per model-space point, to shrink the throat cap inside the head."""
    me = lo.data
    nv = len(me.vertices)
    co = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).astype(np.float64)
    vn = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get('normal', vn)
    vn = vn.reshape(-1, 3).astype(np.float64)
    hl = to_local(co)
    f = lip_f(hl)
    polys = [list(p.vertices) for p in me.polygons]
    cen = np.array([hl[p].mean(axis=0) for p in polys])
    pf = lip_f(cen)
    # the inner walls: narrow bands of the skin along the lips (exact copies, sunk inward away from the cut)
    take = (cen[:, 1] < BACK_Y) & (np.abs(cen[:, 0]) < 0.09) & (pf > FLOOR_F - 0.002) & (pf < ROOF_F + 0.002)
    sel = [p for p, t in zip(polys, take) if t]
    used = sorted({i for p in sel for i in p})
    remap = {i: j for j, i in enumerate(used)}
    sink = INSET * smooth(0.0, 0.006 / k, np.abs(f[used]))
    pts = co[used] - vn[used] * sink[:, None]
    part = np.where(f[used] > 0, 1.0, -1.0)
    verts = [tuple(p) for p in pts]
    faces = [tuple(remap[i] for i in reversed(p)) for p in sel]        # turned inside out
    parts = list(part)
    # the palate's roof (head) and the floor (jaw): the muzzle's own cross-section at those heights, a little inside it
    for lvl, sign in ((ROOF_F, 1.0), (FLOOR_F, -1.0)):
        ring = _section(co, hl, me, lvl, to_local)
        if ring is None:
            C.log(f'{name}: no cross-section at f={lvl}')
            continue
        c0 = ring.mean(axis=0)
        ring = c0 + (ring - c0) * 0.94
        b0 = len(verts)
        verts += [tuple(p) for p in to_world(np.vstack([c0[None], ring]))]
        parts += [sign] * (len(ring) + 1)
        m = len(ring)
        for j in range(m):
            a_, b_ = b0 + 1 + j, b0 + 1 + (j + 1) % m
            # sorted counter-clockwise seen from above: (c, a, b) faces up (the floor), (c, b, a) down (the roof)
            faces.append((b0, a_, b_) if sign < 0 else (b0, b_, a_))
    # the throat cap at the back, facing forward into the mouth (a fan, inside the head)
    zc = float(lip_z(np.zeros(1), np.full(1, BACK_Y))[0])
    rx, rz = 0.072, 0.042
    for _try in range(6):
        cap = _ellipse_cap(BACK_Y, zc - 0.006, rx, rz, 24)
        cw = to_world(np.array(cap, np.float64))
        if inside is None or bool(np.all(inside(cw[1:]))):
            break
        rx, rz = rx * 0.88, rz * 0.88
    base = len(verts)
    verts += [tuple(p) for p in cw]
    parts += [2.0] * len(cw)
    n = len(cw) - 1
    for j in range(n):
        # facing -y (forward, toward the lips)
        faces.append((base, base + 1 + j, base + 1 + (j + 1) % n))
    # the fangs: small cones from the upper lip line, pointing down
    for fx, fy in FANG_L:
        z0 = float(lip_z(np.array([fx]), np.array([fy]))[0]) + 0.0012
        # Nov 13: bigger, so they read at game size
        tip = to_world(np.array([[fx, fy - 0.0015, z0 - 0.0085]]))[0]
        ring = []
        for j in range(8):
            a = 2 * math.pi * j / 8
            ring.append((fx + 0.0026 * math.cos(a), fy + 0.0021 * math.sin(a), z0))
        rw = to_world(np.array(ring, np.float64))
        b0 = len(verts)
        verts += [tuple(p) for p in rw] + [tuple(tip)]
        parts += [3.0] * 9
        for j in range(8):
            faces.append((b0 + (j + 1) % 8, b0 + j, b0 + 8))      # outward
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=False)
    mesh.update()
    mesh.shade_smooth()
    ob = bpy.data.objects.new(name, mesh)
    C.link_obj(ob)
    nsel = len(sel)
    if target and len(mesh.polygons) > target:
        # fewer faces away from the lips: the inner skin's edge along the cut, the cap and the fangs keep every vertex
        pv = np.asarray(parts)
        cw_ = np.empty(len(mesh.vertices) * 3, np.float32)
        mesh.vertices.foreach_get('co', cw_)
        fl = np.abs(lip_f(to_local(cw_.reshape(-1, 3).astype(np.float64))))
        free = np.where((np.abs(pv) < 1.5) & (fl > 0.006), 1.0, 0.0)
        vg = ob.vertex_groups.new(name='free')
        idx = np.nonzero(free > 0.5)[0]
        if len(idx):
            vg.add(idx.tolist(), 1.0, 'REPLACE')
        dm = ob.modifiers.new('decimate', 'DECIMATE')
        dm.decimate_type = 'COLLAPSE'
        dm.ratio = max(0.02, target / len(mesh.polygons))
        dm.use_collapse_triangulate = True
        dm.vertex_group = 'free'
        dm.vertex_group_factor = 1.0
        # the modifier keeps attributes; apply it
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_apply(modifier=dm.name)
        ob.vertex_groups.clear()
    ob['prop'] = 'mouth'
    from lib import surface as S
    if len(ob.data.vertices) != len(parts):
        # the decimation dropped vertices: take each one's part from the nearest original
        from mathutils.kdtree import KDTree
        kd = KDTree(len(verts))
        for i, p in enumerate(verts):
            kd.insert(p, i)
        kd.balance()
        parts = [parts[kd.find(v.co)[1]] for v in ob.data.vertices]
    S.add_attr(ob, 'mouth_part', np.asarray(parts, np.float64))
    # the attributes every prop shares (the props are joined keeping only the common ones)
    for a in ('whisker', 'flame_u', 'flame_part'):
        S.add_attr(ob, a, np.zeros(len(parts)))
    C.log(f'{name}: inner skin {nsel} faces, throat cap {rx:.3f} x {rz:.3f}, {len(ob.data.polygons)} faces in all')
    return ob
