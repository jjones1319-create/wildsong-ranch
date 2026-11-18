"""Velvesper's props (Art 2.1 Ultra): the four moth wings and the two feathery antennae, with their skin weights.

The wings (1-hero, 2-turnaround, 4-details panels 4-6): each a soft, slightly cupped paddle with a rounded bead along its
rim, so seen edge-on it is a curved band with a visible edge, never a hairline. Built on a polar grid round a centre
inside the wing: the top and the bottom skins meet at the rim ring (a half-round edge 12 mm thick, the middle 7 mm).
Each wing lies in its own plane: upright, swept back 30 degrees from the frontal plane (the three-quarter hero shows the
near wing face-on), the hindwing 4 cm behind the forewing and on the same beat axis, so the pair beats as one surface
and never cuts through itself. Own UVs: each skin is one flat island (the front and the back are separate islands).
Attributes for the paint: `pk` (1 forewing, 2 hindwing, 3 antenna shaft, 4 antenna vane), `wu`, `wv` (the wing's own
plane, metres from its root), `ws` (0 at the polar centre .. 1 at the rim), `wd` (metres to the rim), `wface` (+1 front,
-1 back), `side`.

The antennae (4-details panel 3): a cream shaft arching up and out from the crown, and a broad feathery vane hanging
under the arch: two comb-like rows of barbs in a shallow V (so the plume reads broad from the front and from the side),
each row one sheet whose inner web is solid and whose outer edge is cut into tapering teeth, all leaning toward the tip.
Attributes `au` (0 root .. 1 tip), `aw` (0 shaft .. 1 barb tip), `tooth` (0..1 per tooth).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import velvesper_form as F

SWEEP = 24.0                                  # degrees back from the frontal plane (the turnaround's ~30; less so the far wing shows in three-quarter)
WING_ROOT = (0.07, 0.05)                      # the beat axis's (x, y) for both pairs (left side)
# outlines in the wing's own plane: (u along the wing, outward and back; v up), metres from the root
WINGS = {
    'fore': {'z': 0.69, 'offset': 0.0, 'centre': (0.5, 0.19), 'cup': 0.045,
             'outline': [(0.0, 0.0), (0.05, 0.06), (0.15, 0.16), (0.29, 0.28), (0.45, 0.37), (0.61, 0.425), (0.75, 0.43), (0.86, 0.39),
                         (0.935, 0.31), (0.965, 0.21), (0.94, 0.11), (0.86, 0.035), (0.71, -0.015), (0.52, -0.04), (0.32, -0.05),
                         (0.15, -0.05), (0.04, -0.035)],
             'bones': [(0.0, 0.0), (0.58, 0.25), (0.93, 0.3)]},
    'hind': {'z': 0.6, 'offset': -0.04, 'centre': (0.34, -0.16), 'cup': 0.035,
             'outline': [(0.0, 0.02), (0.11, 0.09), (0.28, 0.13), (0.45, 0.105), (0.58, 0.035), (0.655, -0.07), (0.66, -0.19),
                         (0.6, -0.3), (0.49, -0.385), (0.36, -0.42), (0.23, -0.385), (0.12, -0.28), (0.045, -0.15), (0.005, -0.05)],
             'bones': [(0.0, 0.0), (0.38, -0.17), (0.6, -0.29)]},
}
# the markings, in the same (u, v) (2-turnaround front view, 1-hero)
CRESCENT = {'c': (0.53, 0.225), 'r': 0.062, 'bite': (-0.56, 0.42), 'bite_r': 0.84}     # the bite toward the body and up
EYESPOT = {'c': (0.335, -0.185), 'r': (0.058, 0.077, 0.112)}                          # orange disc, cream ring, scallops
# (round 2) a slimmer rim (the 12 mm bead read as a glossy rolled plastic edge); the margin gently scalloped
BEAD, CORE = 0.0035, 0.003                    # the rim's half-round radius and the middle's half thickness
SCALLOP = (30, 0.009)                         # the margin's scallops: lobes round the wing, depth (metres)


def frame(s: int, offset: float = 0.0):
    """(origin, e_u, e_v, n) of a wing plane: e_u along the wing (outward, swept back), e_v up, n its front."""
    a = math.radians(SWEEP)
    eu = np.array((math.cos(a) * s, math.sin(a), 0.0))
    ev = np.array((0.0, 0.0, 1.0))
    n = np.array((math.sin(a) * s, -math.cos(a), 0.0))
    return eu, ev, n


def wing_world(name: str, s: int, u, v, w) -> np.ndarray:
    spec = WINGS[name]
    eu, ev, n = frame(s)
    o = np.array((WING_ROOT[0] * s, WING_ROOT[1], spec['z'])) + n * spec['offset']
    u, v, w = (np.asarray(x, np.float64) for x in (u, v, w))
    return o[None] + u[..., None] * eu[None] + v[..., None] * ev[None] + w[..., None] * n[None]


def wing_bone_points(name: str, s: int) -> list[tuple[float, float, float]]:
    """The wing's bone points (root, mid, tip): the root on the shared beat axis, the rest in the wing's plane."""
    spec = WINGS[name]
    pts = []
    for k, (u, v) in enumerate(spec['bones']):
        p = wing_world(name, s, u, v, 0.0)
        if k == 0:
            p = np.array((WING_ROOT[0] * s, WING_ROOT[1], spec['z'] + v))
        pts.append(tuple(float(x) for x in np.asarray(p).reshape(3)))
    return pts


def _outline_dense(pts, n: int = 720) -> np.ndarray:
    """A closed Catmull-Rom spline through the outline's points, sampled densely."""
    P = np.asarray(pts, np.float64)
    m = len(P)
    out = []
    per = max(2, n // m)
    for i in range(m):
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        for t in np.linspace(0.0, 1.0, per, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


def _ray_radius(poly: np.ndarray, c: np.ndarray, th: np.ndarray) -> np.ndarray:
    """The distance from c along each angle to the closed polyline (the farthest crossing; the outline is star-shaped
    about c)."""
    a, b = poly, np.roll(poly, -1, axis=0)
    out = np.zeros(len(th))
    for j, t in enumerate(th):
        d = np.array((math.cos(t), math.sin(t)))
        e = b - a
        den = d[0] * e[:, 1] - d[1] * e[:, 0]
        ok = np.abs(den) > 1e-12
        ac = a - c
        r = np.where(ok, (ac[:, 0] * e[:, 1] - ac[:, 1] * e[:, 0]) / np.where(ok, den, 1.0), -1.0)
        q = np.where(ok, (ac[:, 0] * d[1] - ac[:, 1] * d[0]) / np.where(ok, den, 1.0), -1.0)
        hit = ok & (r > 0) & (q >= 0) & (q <= 1)
        out[j] = r[hit].max() if hit.any() else 0.0
    return out


def thickness(d: np.ndarray) -> np.ndarray:
    """Half the wing's thickness at distance d from its rim: a half-round bead of radius BEAD, then the thinner middle."""
    d = np.asarray(d, np.float64)
    bead = np.sqrt(np.clip(BEAD * BEAD - (BEAD - np.minimum(d, BEAD)) ** 2, 0.0, None))
    return np.where(d <= BEAD, bead, CORE + (BEAD - CORE) * np.exp(-((d - BEAD) / 0.006) ** 2))


def _vnoise(x: np.ndarray, y: np.ndarray, cell: float, seed: int) -> np.ndarray:
    """Smooth value noise in -1..1 on a square lattice of `cell` metres (hashed corners, smoothstep blend)."""
    gx, gy = x / cell, y / cell
    ix, iy = np.floor(gx).astype(np.int64), np.floor(gy).astype(np.int64)
    fx, fy = gx - ix, gy - iy

    def h(a, b):
        v = (a * 374761393 + b * 668265263 + seed * 2654435761) & 0xFFFFFFFF
        v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
        return (v & 0xFFFF) / 32767.5 - 1.0

    sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = h(ix, iy) * (1 - sx) + h(ix + 1, iy) * sx
    b = h(ix, iy + 1) * (1 - sx) + h(ix + 1, iy + 1) * sx
    return a * (1 - sy) + b * sy


DUST = 0.0008                                 # the scale dust's relief on the source wings, metres (round 2: it didn't show)


def wing_object(obname: str, name: str, s: int, high: bool) -> bpy.types.Object:
    """One wing (vectorised; round 1): the rim ring shared by both skins, each further ring twice (front, back), a pole
    each; on the high source a fine scale-dust relief over both skins (baked into the normal map: 4-details panel 6)."""
    spec = WINGS[name]
    poly = _outline_dense(spec['outline'])
    c = np.array(spec['centre'])
    nth = 560 if high else 44
    th = np.linspace(0.0, 2 * math.pi, nth, endpoint=False)
    R = _ray_radius(poly, c, th)
    R = R - SCALLOP[1] * (1.0 - np.abs(np.cos(th * SCALLOP[0] * 0.5)) ** 0.6)
    rim = [0.0, 0.0006, 0.0015, 0.0026, 0.0038, 0.006, 0.0095, 0.015] if high else [0.0, 0.002, 0.0045, 0.01]
    inner = 110 if high else 5
    rhos, ds = [], []
    for d in rim:
        rhos.append(R - d)
        ds.append(np.full(nth, d))
    last = R - rim[-1]
    for q in np.linspace(1.0, 0.0, inner + 1)[1:-1] ** 1.15:
        rhos.append(last * q)
        ds.append(R - last * q)
    rho, dd = np.array(rhos), np.array(ds)                      # (rings, nth)
    nr = len(rho)
    um = max(p[0] for p in spec['outline'])
    U = c[0] + rho * np.cos(th)[None]
    V = c[1] + rho * np.sin(th)[None]
    W0 = -spec['cup'] * (np.maximum(U, 0.0) / um) ** 2 - 0.008 * (1.0 - np.minimum(1.0, np.hypot(U - c[0], V - c[1]) / 0.45)) ** 2
    T = thickness(dd)
    WS = rho / np.maximum(R[None], 1e-9)
    if high:
        # fine scale dust: two octaves of value noise, outward on both skins, fading out over the rim's bead
        dn = 0.65 * _vnoise(U, V, 0.0055, 3 + (name == 'hind')) + 0.35 * _vnoise(U, V, 0.0028, 11 + (name == 'hind'))
        T = T + DUST * (0.5 + 0.5 * dn) * F.smooth(BEAD, 0.016, dd)
    # vertices: ring 0 shared, then the front skin's rings 1.., the back skin's rings 1.., the two poles
    def flat(a):
        return a.reshape(-1)
    uu = np.concatenate([U[0], flat(U[1:]), flat(U[1:]), [c[0], c[0]]])
    vv = np.concatenate([V[0], flat(V[1:]), flat(V[1:]), [c[1], c[1]]])
    tc = float(thickness(np.array([R.mean()]))[0])
    w0p = float(-spec['cup'] * (max(c[0], 0.0) / um) ** 2 - 0.008)
    ww = np.concatenate([W0[0], flat(W0[1:] + T[1:]), flat(W0[1:] - T[1:]), [w0p + tc, w0p - tc]])
    wd = np.concatenate([dd[0], flat(dd[1:]), flat(dd[1:]), [R.min(), R.min()]])
    wf = np.concatenate([np.zeros(nth), np.ones((nr - 1) * nth), -np.ones((nr - 1) * nth), [1.0, -1.0]])
    wsv = np.concatenate([WS[0], flat(WS[1:]), flat(WS[1:]), [0.0, 0.0]])
    Vt = wing_world(name, s, uu, vv, ww)
    n1 = (nr - 1) * nth

    def top(k, j):
        return np.where(k == 0, j, nth + (k - 1) * nth + j)

    def bot(k, j):
        return np.where(k == 0, j, nth + n1 + (k - 1) * nth + j)

    k, j = np.meshgrid(np.arange(nr - 1), np.arange(nth), indexing='ij')
    k, j = k.ravel(), j.ravel()
    j2 = (j + 1) % nth
    ft = np.stack([top(k, j), top(k + 1, j), top(k + 1, j2), top(k, j2)], axis=1)
    fb = np.stack([bot(k, j), bot(k, j2), bot(k + 1, j2), bot(k + 1, j)], axis=1)
    pt, pb = nth + 2 * n1, nth + 2 * n1 + 1
    jj = np.arange(nth)
    tt = np.stack([top(np.full(nth, nr - 1), jj), np.full(nth, pt), top(np.full(nth, nr - 1), (jj + 1) % nth)], axis=1)
    tb = np.stack([bot(np.full(nth, nr - 1), jj), bot(np.full(nth, nr - 1), (jj + 1) % nth), np.full(nth, pb)], axis=1)
    faces = [tuple(f) for f in ft.tolist()] + [tuple(f) for f in fb.tolist()] + [tuple(f) for f in tt.tolist()] + [tuple(f) for f in tb.tolist()]
    me = bpy.data.meshes.new(obname)
    me.from_pydata(Vt.tolist(), [], faces)
    me.update()
    ob = bpy.data.objects.new(obname, me)
    C.link_obj(ob)
    eu, ev, n = frame(s)
    _orient(ob, n, wf)
    me.shade_smooth()
    nv = len(Vt)
    for key, a in (('wu', uu), ('wv', vv), ('ws', wsv), ('wd', wd), ('wface', wf)):
        S.add_attr(ob, key, np.asarray(a, np.float64))
    S.add_attr(ob, 'pk', np.full(nv, 1.0 if name == 'fore' else 2.0))
    S.add_attr(ob, 'side', np.full(nv, float(s)))
    S.add_attr(ob, 'au', np.zeros(nv))
    S.add_attr(ob, 'aw', np.zeros(nv))
    S.add_attr(ob, 'tooth', np.zeros(nv))
    if not high:
        _wing_uvs(ob, um)
        a = me.attributes.new('texel_k', 'FLOAT', 'FACE')
        # (round 1) more of the atlas for the wings: their bands stair-stepped up close (head_front, head_34)
        a.data.foreach_set('value', np.full(len(me.polygons), 1.4, np.float32))
    return ob


def _orient(ob, n: np.ndarray, wface: np.ndarray) -> None:
    """Turn each face so the top skin faces +n and the bottom -n (the rim faces by their side's skin)."""
    me = ob.data
    nf = len(me.polygons)
    nn = np.empty(nf * 3, np.float32)
    me.polygons.foreach_get('normal', nn)
    nn = nn.reshape(-1, 3)
    flip = []
    for p in me.polygons:
        f = wface[list(p.vertices)]
        side = 1.0 if f.sum() > 0 else -1.0
        if float(nn[p.index] @ n) * side < 0:
            flip.append(p.index)
    if flip:
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in flip])
        bm.to_mesh(me)
        bm.free()
        me.update()


def _wing_uvs(ob, um: float) -> None:
    """Each skin one flat island in the wing's own plane (the back mirrored beside the front)."""
    me = ob.data
    uvl = me.uv_layers.new(name='UVMap')
    wu = S.attr_array(ob, 'wu').astype(np.float64)
    wv = S.attr_array(ob, 'wv').astype(np.float64)
    wf = S.attr_array(ob, 'wface').astype(np.float64)
    uv = np.zeros((len(me.loops), 2), np.float32)
    for p in me.polygons:
        vs = list(p.vertices)
        side = 1.0 if wf[vs].sum() > 0 else -1.0
        for li, vi in zip(p.loop_indices, vs):
            uv[li] = (wu[vi], wv[vi]) if side > 0 else (2.0 * um + 0.1 - wu[vi], wv[vi])
    uvl.data.foreach_set('uv', uv.ravel())
    ob['own_uv'] = True


# ----------------------------------------------------------------------------- antennae
def antenna_ctrl(s: int) -> np.ndarray:
    """The shaft's cubic Bezier (left, mirrored): up from the crown's front, arching out and a little forward, the tip
    hanging down (2-turnaround front: up to 1.31 m, out to 0.45 m)."""
    # (build 5) the arch 7 cm lower: with the plume the tops stood at 1.41 m (2-turnaround: 1.31 m)
    # (round 2) the arch turned forward too (from the side the plumes went edge-on into a thin V)
    # (polish) turned forward only half as far: the far antenna's plane went edge-on in three-quarter views
    P = np.array(((0.06, -0.1, 1.045), (0.12, -0.15, 1.22), (0.31, -0.25, 1.31), (0.43, -0.29, 1.1)))
    P[:, 0] *= s
    return P


def bez(P: np.ndarray, t) -> np.ndarray:
    t = np.asarray(t, np.float64)[..., None]
    return ((1 - t) ** 3) * P[0] + 3 * ((1 - t) ** 2) * t * P[1] + 3 * (1 - t) * t * t * P[2] + (t ** 3) * P[3]


def bez_d(P: np.ndarray, t) -> np.ndarray:
    t = np.asarray(t, np.float64)[..., None]
    return 3 * ((1 - t) ** 2) * (P[1] - P[0]) + 6 * (1 - t) * t * (P[2] - P[1]) + 3 * t * t * (P[3] - P[2])


def bez_dd(P: np.ndarray, t) -> np.ndarray:
    t = np.asarray(t, np.float64)[..., None]
    return 6 * (1 - t) * (P[2] - 2 * P[1] + P[0]) + 6 * t * (P[3] - 2 * P[2] + P[1])


def antenna_points(s: int) -> list[tuple[float, float, float]]:
    """The chain's three points on the shaft (the rig's two antenna bones)."""
    P = antenna_ctrl(s)
    return [tuple(float(x) for x in bez(P, t)) for t in (0.0, 0.42, 1.0)]


def _frames(P: np.ndarray, t: np.ndarray):
    """(T, N, B) along the shaft. (polish) N lies in the curve's own plane, toward the arch's inside, with one sign
    for the whole curve: the principal normal flipped where the turned-forward arch straightens, and the vane twisted
    half a turn into a tent there."""
    T = bez_d(P, t)
    T = T / np.linalg.norm(T, axis=1, keepdims=True)
    C_ = bez(P, np.linspace(0.0, 1.0, 48))
    c0 = C_.mean(axis=0)
    npl = np.linalg.svd(C_ - c0)[2][2]
    N = np.cross(npl[None], T)
    N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    Ns = np.cross(npl[None], bez_d(P, np.linspace(0.0, 1.0, 48)))
    if float((Ns * (c0[None] - C_)).sum()) < 0.0:
        N = -N
    B = np.cross(T, N)
    return T, N, B


SHAFT_R = (0.0052, 0.0024)                    # (build 1) thinner: a thick gold stick under sparse barbs
# (build 1) a lush plume: longer, denser barbs and a fuller web (they read as a wire with a sparse comb)
# (round 1) slimmer, denser barbs, closer together toward the tip, each one curved (a stiff comb of needles before)
# (round 2) the V opened wider (the plumes read broad from the side too); the vane starts clear of the crown
VANE = {'teeth': 56, 'L': 0.165, 'web': 0.3, 'spread': 52.0, 'lean': 1.0, 'u0': 0.12, 'u1': 0.985, 'bow': 0.2}
# the rows: (name, side of the arch: -1 the convex (the plume: 1-hero, 4-details panel 3), +1 the concave (a short
# fringe under the arch), the row's turn about the shaft (+-1 opens the plume's V, 0 straight), its length)
# (polish) one flat fan in the arch's own plane (4-details panel 3): the two rows of the V read as a tent or a cat's
# ear from three-quarter views; the arch turned forward still shows the fan's face from the side
ROWS = (('a', -1.0, 0.0, 1.0),)


def barb_len(u: np.ndarray) -> np.ndarray:
    """The vane's half-width along the shaft: short at the root, fullest past the middle, tapering to the tip."""
    x = np.clip((u - VANE['u0']) / (VANE['u1'] - VANE['u0']), 0.0, 1.0)
    return VANE['L'] * np.sin(math.pi * x ** 0.75) * (0.12 + 0.88 * F.smooth(0.08, 0.45, x)) + 0.012


def shaft_object(obname: str, s: int, high: bool) -> bpy.types.Object:
    P = antenna_ctrl(s)
    nseg = 14 if high else 8
    nring = 70 if high else 18
    t = np.linspace(0.0, 1.0, nring)
    C_ = bez(P, t)
    T, N, B = _frames(P, t)
    r = SHAFT_R[0] + (SHAFT_R[1] - SHAFT_R[0]) * t
    verts, au = [], []
    for i in range(nring):
        for k in range(nseg):
            a = 2 * math.pi * k / nseg
            verts.append(C_[i] + r[i] * (math.cos(a) * N[i] + math.sin(a) * B[i]))
            au.append(t[i])
    tip = C_[-1] + T[-1] * r[-1]
    verts.append(tip)
    au.append(1.0)
    verts.append(C_[0] - T[0] * r[0])                                         # the root's cap centre (inside the head)
    au.append(0.0)
    faces = []
    for i in range(nring - 1):
        for k in range(nseg):
            k2 = (k + 1) % nseg
            faces.append((i * nseg + k, i * nseg + k2, (i + 1) * nseg + k2, (i + 1) * nseg + k))
    ti, ci = len(verts) - 2, len(verts) - 1
    for k in range(nseg):
        faces.append(((nring - 1) * nseg + k, (nring - 1) * nseg + (k + 1) % nseg, ti))
        faces.append(((k + 1) % nseg, k, ci))                                   # triangles only (the export's tangents)
    ob = S.sheet_object(obname, np.array(verts), faces)
    nv = len(ob.data.vertices)
    S.orient_away(ob, lambda c: bez(P, np.clip(_nearest_t(P, c), 0.0, 1.0)))
    for k, a in (('pk', np.full(nv, 3.0)), ('au', np.array(au)), ('aw', np.zeros(nv)), ('tooth', np.zeros(nv)), ('side', np.full(nv, float(s))),
                 ('wu', np.zeros(nv)), ('wv', np.zeros(nv)), ('ws', np.zeros(nv)), ('wd', np.zeros(nv)), ('wface', np.zeros(nv))):
        S.add_attr(ob, k, a)
    return ob


def _nearest_t(P: np.ndarray, c: np.ndarray) -> np.ndarray:
    ts = np.linspace(0.0, 1.0, 200)
    pts = bez(P, ts)
    d = np.linalg.norm(np.asarray(c)[:, None, :] - pts[None], axis=2)
    return ts[np.argmin(d, axis=1)]


def vane_object(obname: str, s: int, arch: float, row: float, scale: float, high: bool) -> bpy.types.Object:
    """One comb row of barbs (on the arch's convex side, `arch` -1, turned `row` about the shaft; or the concave
    fringe): a solid web along the shaft, then tapering teeth leaning toward the tip; solidified to 2.2 mm so no view
    sees it as a single sheet."""
    P = antenna_ctrl(s)
    nt = VANE['teeth'] if scale > 0.5 else VANE['teeth'] // 2
    ne = 2 * nt + 1                                    # the web's outer edge: two points per tooth plus one
    ue = VANE['u0'] + (VANE['u1'] - VANE['u0']) * np.linspace(0.0, 1.0, ne) ** 0.85
    T, N, B = _frames(P, ue)
    a = math.radians(VANE['spread'])
    D = math.cos(a) * arch * N + row * math.sin(a) * B * s + VANE['lean'] * T
    D = D / np.linalg.norm(D, axis=1, keepdims=True)
    L = barb_len(ue) * scale
    base = bez(P, ue)
    web_rows = 3 if high else 1
    J = 6 if high else 3
    verts, au, aw, tooth = [], [], [], []
    grid = np.zeros((web_rows + 1, ne), np.int64)
    for r_ in range(web_rows + 1):
        f = VANE['web'] * r_ / web_rows
        for i in range(ne):
            grid[r_, i] = len(verts)
            verts.append(base[i] + D[i] * L[i] * f)
            au.append(ue[i])
            aw.append(f)
            tooth.append(0.0)
    faces = []
    for r_ in range(web_rows):
        for i in range(ne - 1):
            faces.append((grid[r_, i], grid[r_, i + 1], grid[r_ + 1, i + 1], grid[r_ + 1, i]))
    edge = grid[web_rows]
    rng = np.random.default_rng(7 + int(3 * row + 3) + (11 if arch > 0 else 0) + (2 if s > 0 else 0))
    for k in range(nt):
        i0, i1, i2 = 2 * k, 2 * k + 1, 2 * k + 2
        tk = float(rng.uniform(0.0, 1.0))
        # the tooth's tip: from its middle base out along the barb direction, leaning a little further toward the tip
        tipu = min(VANE['u1'], ue[i1] + 0.012)
        tb = bez(P, np.array([tipu]))[0]
        Tt, Nt, Bt = _frames(P, np.array([tipu]))
        Dt = math.cos(a) * arch * Nt[0] + row * math.sin(a) * Bt[0] * s + VANE['lean'] * Tt[0]
        Dt = Dt / np.linalg.norm(Dt)
        tip = tb + Dt * barb_len(np.array([tipu]))[0] * scale * (0.96 + 0.08 * tk)
        rows = [[edge[i0], edge[i1], edge[i2]]]
        for j in range(1, J):
            fj = j / J
            row_ids = []
            for ii in (i0, i1, i2):
                p0 = np.array(verts[edge[ii]])
                q = p0 + (tip - p0) * fj - Tt[0] * (VANE['bow'] * np.linalg.norm(tip - p0) * math.sin(math.pi * fj))
                # the tooth's sides bow out a little (a soft barb, not a dart)
                if ii != i1:
                    m0 = np.array(verts[edge[i1]])
                    mid = m0 + (tip - m0) * fj - Tt[0] * (VANE['bow'] * np.linalg.norm(tip - m0) * math.sin(math.pi * fj))
                    q = q + (q - mid) * 0.25 * math.sin(math.pi * fj)
                row_ids.append(len(verts))
                verts.append(q)
                au.append(ue[i1])
                aw.append(VANE['web'] + (1 - VANE['web']) * fj)
                tooth.append(tk)
            rows.append(row_ids)
        ti = len(verts)
        verts.append(tip)
        au.append(ue[i1])
        aw.append(1.0)
        tooth.append(tk)
        for j in range(len(rows) - 1):
            a_, b_ = rows[j], rows[j + 1]
            faces.append((a_[0], a_[1], b_[1], b_[0]))
            faces.append((a_[1], a_[2], b_[2], b_[1]))
        last = rows[-1]
        faces.append((last[0], last[1], ti))
        faces.append((last[1], last[2], ti))
    V = np.array(verts)
    me = bpy.data.meshes.new(obname + '_sheet')
    me.from_pydata([tuple(map(float, p)) for p in V], [], [tuple(int(i) for i in f) for f in faces])
    me.update()
    sh = bpy.data.objects.new(obname, me)
    C.link_obj(sh)
    for k, arr in (('au', au), ('aw', aw), ('tooth', tooth)):
        S.add_attr(sh, k, np.asarray(arr, np.float64))
    sol = sh.modifiers.new('solid', 'SOLIDIFY')
    sol.thickness = 0.0022
    sol.offset = 0.0
    sol.use_rim = True
    sol.use_even_offset = True
    C.apply_modifiers(sh)
    sh.data.shade_smooth()
    nv = len(sh.data.vertices)
    for k, arr in (('pk', np.full(nv, 4.0 if arch < 0 else 5.0)), ('side', np.full(nv, float(s))), ('wu', np.zeros(nv)), ('wv', np.zeros(nv)),
                   ('ws', np.zeros(nv)), ('wd', np.zeros(nv)), ('wface', np.zeros(nv))):
        S.add_attr(sh, k, arr)
    return sh


# ----------------------------------------------------------------------------- build and weights
def build(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for s, t in ((1, 'L'), (-1, 'R')):
        for name in ('fore', 'hind'):
            out.append(wing_object(f'{tag}_{name}{t}', name, s, high))
        out.append(shaft_object(f'{tag}_shaft{t}', s, high))
        for nm, arch, row, scale in ROWS:
            out.append(vane_object(f'{tag}_vane{t}{nm}', s, arch, row, scale, high))
    return out


def weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    pk, side = attr('pk'), attr('side')
    regs = []
    for s, t in ((1, 'L'), (-1, 'R')):
        for name, bone, kind in (('fore', 'wing', 1.0), ('hind', 'hind', 2.0)):
            m = (np.abs(pk - kind) < 0.5) & (side * s > 0)
            if m.any():
                pts = wing_bone_points(name, s)
                segs = [(f'{bone}{t}.1', pts[0], pts[1]), (f'{bone}{t}.2', pts[1], pts[2])]
                regs.append((m, U.segment_weights(co[m], segs, power=4.0)))
        m = (pk > 2.5) & (side * s > 0)
        if m.any():
            pts = antenna_points(s)
            regs.append((m, U.chain_weights(co[m], pts, [f'antenna{t}.1', f'antenna{t}.2'], 'head')))
    return regs
