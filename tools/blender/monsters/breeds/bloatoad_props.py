"""Bloatoad's tongue (Art 2.1 Ultra): a long, soft, flattened tongue lying in the mouth (hidden inside the head at
rest), widening to a round, slightly thicker tip (5-poses, attack). It rides the jaw's three-bone chain `tongue.1..3`
(RECIPE.md, Blob plan): the bones after the first slide out as it lashes, stretching it between them.

Attributes: tg_u (0 at the root → 1 at the tip), tg_v (−1..1 across: 0 along the top's middle), tg_top (1 on top).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from monsters.breeds import bloatoad_form as F
from monsters.breeds import bloatoad_skin as SK

TIP_EXTRA = 0.02          # the round tip reaches this far past the last point


def _axis() -> np.ndarray:
    pts = np.array(F.TONGUE, np.float64)
    d = pts[-1] - pts[-2]
    return np.vstack([pts, pts[-1] + d / np.linalg.norm(d) * TIP_EXTRA])


def _section(u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Half-width and half-thickness (metres) along the tongue: a narrow root, a long blade, a round spoon at the tip
    (closing over its last 12%)."""
    # round 2: thick at the root, tapering along the shaft, a fat round tip about 1.5 times the shaft (5-poses attack)
    # round 3: thicker toward the root
    # polish: a third of the mouth's width at the root (15 cm), tapering to the shaft, a fat round tip twice the
    # shaft's width (the reviewer still saw an even straw)
    w = 0.075 - 0.03 * F.smooth(0.05, 0.6, u) + 0.045 * F.smooth(0.64, 0.86, u)
    t = 0.04 - 0.012 * F.smooth(0.05, 0.6, u) + 0.012 * F.smooth(0.64, 0.86, u)
    close = np.sqrt(np.clip(1.0 - ((u - 0.88) / 0.12) ** 2, 0.0, 1.0))
    close = np.where(u < 0.88, 1.0, close)
    start = np.sqrt(np.clip(1.0 - ((0.06 - u) / 0.06) ** 2, 0.0, 1.0))
    start = np.where(u > 0.06, 1.0, start)
    k = np.maximum(close * start, 0.0)
    return w * k, t * k


def _polyline(pts: np.ndarray, u: np.ndarray) -> np.ndarray:
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    return np.stack([np.interp(u, cum, pts[:, k]) for k in range(3)], axis=1)


# polish: the mouth's inside is a pocket grown from the lips' own cut edges (the game mesh is cut along the mouth,
# bloatoad_carve.cut_mouth): ring 0 is the lip's edge itself (no gap anywhere, at any opening: a cup behind the lips
# left grey wedges at the corners and a band in ko), each deeper ring a step further in and, behind the upper lip, up
# into the roof, behind the lower lip down into the floor (the tongue's bed); the last ring closed by a back wall
POCKET_S = (0.0, 0.07, 0.25, 0.55, 0.85, 1.0)       # each ring's depth (a share of the depth to the back wall)
POCKET_G = (0.0, 0.45, 0.85, 1.0, 0.9, 0.7)         # its roof's rise and floor's drop (a share of POCKET_V)
POCKET_M = 72                                       # vertices in each inner ring (half under the roof, half the floor)
POCKET_BACK = 0.08                                  # the back wall: this far from the mouth's axis (bloatoad_skin.MOUTH_Y)
POCKET_V = (0.05, 0.075)                            # the roof's rise and the floor's drop at the front (metres)
POCKET_GAP = 0.003                                  # the inner rings kept this far inside the skin


def build(high: bool, quick: bool) -> list[bpy.types.Object]:
    lo = bpy.data.objects.get('lo_body')
    if lo is not None and 'jside' not in lo.data.attributes:
        # the game mesh is final here (after its decimation): cut its mouth, then grow the pocket from the cut
        from monsters.breeds import bloatoad_carve as CV
        CV.cut_mouth(lo)
    return [_tongue(high), _bag(high)]


def _lip_loop(lo) -> tuple[list[int], np.ndarray, np.ndarray]:
    """The cut's edge on the game mesh as one closed loop (the upper lip's edge one way, the lower's back), starting at
    one corner: lo_body vertex indices, their positions and their `jside` (0 the upper lip, 1 the lower, 0.5 a corner)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(lo.data)
    bm.verts.ensure_lookup_table()
    nb: dict[int, list[int]] = {}
    for e in bm.edges:
        if e.is_boundary:
            a, b = e.verts[0].index, e.verts[1].index
            nb.setdefault(a, []).append(b)
            nb.setdefault(b, []).append(a)
    co = np.array([v.co[:] for v in bm.verts])
    bm.free()
    loops, seen = [], set()
    for start in nb:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [w for w in nb[cur] if w != prev and w not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)
    if not loops:
        raise SystemExit('bloatoad mouth pocket: the game mesh has no cut (bloatoad_carve.cut_mouth)')
    loop = max(loops, key=len)
    if len(loops) > 1:
        C.log(f'mouth pocket: {len(loops)} open edges on the game mesh; the lips are the longest ({len(loop)} vertices)')
    js = S.attr_array(lo, 'jside').astype(np.float64)[loop]
    pos = co[loop]
    th = SK.mouth_theta(pos)
    # start at a corner: the two vertices shared by both lips (else the widest on each side)
    ends = [i for i in range(len(loop)) if 0.25 < js[i] < 0.75]
    if len(ends) != 2:
        C.log(f'mouth pocket: {len(ends)} corner vertices on the lips (2 expected); taking the widest on each side')
        ends = [int(np.argmax(np.where(pos[:, 0] > 0, np.abs(th), -1.0))), int(np.argmax(np.where(pos[:, 0] <= 0, np.abs(th), -1.0)))]
        js[ends] = 0.5
    r = ends[0]
    return loop[r:] + loop[:r], np.roll(pos, -r, axis=0), np.roll(js, -r)


def _bag(high: bool) -> bpy.types.Object:
    """The mouth's inside (polish): a pocket grown from the lips' cut edges inward and closed by a back wall, its faces
    toward its inside; the same mesh for the high source and the game. Attributes: bag 1, bag_d (0 at the lips → 1 at
    the back wall), bag_floor (1 on the floor behind the lower lip: the tongue's bed); bag_a, bag_b, bag_t (the two lip
    vertices of lo_body each vertex follows and how far between them: the rig copies their weights; −1 on the back
    wall's middle); the tongue's tg_* are 0 here."""
    from mathutils.bvhtree import BVHTree
    lo = bpy.data.objects['lo_body']
    loop, P0, js = _lip_loop(lo)
    n0 = len(loop)
    seg = np.linalg.norm(np.diff(np.vstack([P0, P0[:1]]), axis=0), axis=1)
    t0 = np.concatenate([[0.0], np.cumsum(seg)[:-1]]) / seg.sum()
    sg0 = np.clip((0.5 - js) * 2.0, -1.0, 1.0)            # +1 the upper lip, −1 the lower, 0 a corner
    other = [i for i in range(1, n0) if 0.25 < js[i] < 0.75]
    tc = t0[other[0]] if other else 0.5
    half = POCKET_M // 2
    tau = np.concatenate([np.linspace(0.0, tc, half, endpoint=False), np.linspace(tc, 1.0, POCKET_M - half, endpoint=False)])
    # each sample's place on the lip loop: the two lip vertices round it and how far between
    ia = np.clip(np.searchsorted(t0, tau, side='right') - 1, 0, n0 - 1)
    ib = (ia + 1) % n0
    span = np.where(ib == 0, 1.0 - t0[ia], t0[ib] - t0[ia])
    ft = np.clip((tau - t0[ia]) / np.maximum(span, 1e-9), 0.0, 1.0)
    p_lip = P0[ia] * (1 - ft)[:, None] + P0[ib] * ft[:, None]
    sg = sg0[ia] * (1 - ft) + sg0[ib] * ft
    th = SK.mouth_theta(p_lip)
    c = np.clip(np.cos(np.radians(th)), 0.0, 1.0)
    hz = np.stack([-p_lip[:, 0], SK.MOUTH_Y - p_lip[:, 1]], axis=1)
    rad = np.linalg.norm(hz, axis=1)
    u_in = hz / np.maximum(rad, 1e-6)[:, None]
    depth = np.maximum(rad - POCKET_BACK, 0.03)
    rise = np.where(sg > 0, POCKET_V[0], POCKET_V[1]) * (0.3 + 0.7 * c) * sg
    verts = [P0]
    for s, g in zip(POCKET_S[1:], POCKET_G[1:]):
        r = p_lip.copy()
        r[:, :2] += u_in * (s * depth)[:, None]
        r[:, 2] += g * rise
        verts.append(r)
    V = np.vstack(verts + [verts[-1].mean(axis=0)[None]])
    # the inner rings kept inside the skin (POCKET_GAP), never through it
    bvh = BVHTree.FromObject(lo, bpy.context.evaluated_depsgraph_get())
    moved = 0
    for i in range(n0, len(V)):
        hit = bvh.find_nearest(V[i].tolist())
        if hit[0] is None:
            continue
        loc, nor = np.array(hit[0][:]), np.array(hit[1][:])
        if float(np.dot(V[i] - loc, nor)) > -POCKET_GAP:
            V[i] = loc - nor * POCKET_GAP
            moved += 1
    ring = [list(range(n0))] + [list(range(n0 + k * POCKET_M, n0 + (k + 1) * POCKET_M)) for k in range(len(POCKET_S) - 1)]
    faces = []
    # the lips' edge to the first ring, zipped by their places along the loop
    i = j = 0
    A, B = ring[0], ring[1]
    while i < n0 or j < POCKET_M:
        ta = t0[i + 1] if i + 1 < n0 else 1.0
        tb = tau[j + 1] if j + 1 < POCKET_M else 1.0
        if i < n0 and (j >= POCKET_M or ta <= tb):
            faces.append((A[i], A[(i + 1) % n0], B[j % POCKET_M]))
            i += 1
        else:
            faces.append((A[i % n0], B[(j + 1) % POCKET_M], B[j % POCKET_M]))
            j += 1
    nz = len(faces)
    for k in range(1, len(ring) - 1):
        a_, b_ = ring[k], ring[k + 1]
        for j in range(POCKET_M):
            j1 = (j + 1) % POCKET_M
            faces.append((a_[j], a_[j1], b_[j1], b_[j]))
    ci = len(V) - 1
    for j in range(POCKET_M):
        faces.append((ring[-1][j], ring[-1][(j + 1) % POCKET_M], ci))
    nq = (len(ring) - 2) * POCKET_M
    # the first band (lip to ring 1) twice, the copy facing the other way on its own vertices: the Lite copy simplifies
    # each lip's edge on its own, and a sliver between them then shows this band's dark back, never the background
    src = np.arange(n0 + POCKET_M)
    off = len(V)
    V = np.vstack([V, V[src]])
    faces += [tuple(off + q for q in reversed(f)) for f in faces[:nz]]
    name = f'{"hi" if high else "lo"}_mouthbag'
    me = bpy.data.meshes.new(name)
    me.from_pydata(V.tolist(), [], faces)
    me.update()
    # its faces toward its inside: the roof's look down
    nrm = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get('normal', nrm)
    nrm = nrm.reshape(-1, 3)
    roof = [nz + q for q in range(nq) if sg[q % POCKET_M] > 0.5]
    if roof and float(nrm[roof, 2].mean()) > 0.0:
        me.flip_normals()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    n = len(V)

    def ext(a: np.ndarray) -> np.ndarray:
        return np.concatenate([a, a[src]])
    d = ext(np.concatenate([np.zeros(n0)] + [np.full(POCKET_M, s) for s in POCKET_S[1:]] + [[1.0]]))
    sgv = ext(np.concatenate([sg0] + [sg] * (len(POCKET_S) - 1) + [[0.0]]))
    S.add_attr(ob, 'bag', np.ones(n))
    S.add_attr(ob, 'bag_d', d)
    S.add_attr(ob, 'bag_floor', (sgv < -0.5) * F.smooth(0.03, 0.2, d))
    lip = np.asarray(loop, np.float64)
    S.add_attr(ob, 'bag_a', ext(np.concatenate([lip] + [lip[ia]] * (len(POCKET_S) - 1) + [[-1.0]])))
    S.add_attr(ob, 'bag_b', ext(np.concatenate([lip] + [lip[ib]] * (len(POCKET_S) - 1) + [[-1.0]])))
    S.add_attr(ob, 'bag_t', ext(np.concatenate([np.zeros(n0)] + [ft] * (len(POCKET_S) - 1) + [[0.0]])))
    for k in ('tg_u', 'tg_v', 'tg_top'):
        S.add_attr(ob, k, np.zeros(n))
    ob['prop'] = 'mouthbag'
    C.log(f'mouth pocket: {n0} lip vertices, {len(POCKET_S) - 1} rings of {POCKET_M}, {len(me.polygons)} faces, '
          f'{moved} vertices kept inside the skin')
    return ob


def _tongue(high: bool) -> bpy.types.Object:
    nu, nv = (64, 40) if high else (22, 14)
    pts = _axis()
    u = np.linspace(0.0, 1.0, nu + 1)
    cen = _polyline(pts, u)
    fwd = np.gradient(cen, axis=0)
    fwd /= np.linalg.norm(fwd, axis=1, keepdims=True)
    up = np.array((0.0, 0.0, 1.0))
    side = np.cross(fwd, up)
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    upv = np.cross(side, fwd)
    w, t = _section(u)
    a = np.linspace(0.0, 2.0 * math.pi, nv, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    # a flattened, slightly squarish section (a soft blade), its top a touch fuller than its belly
    sx = np.sign(ca) * np.abs(ca) ** 0.8
    sy = np.sign(sa) * np.abs(sa) ** 0.9 * np.where(sa > 0, 1.0, 0.85)
    V = (cen[:, None] + side[:, None] * (w[:, None, None] * sx[None, :, None])
         + upv[:, None] * (t[:, None, None] * sy[None, :, None]))
    if high:
        # a soft groove down the top's middle, flattening out at the tip
        groove = np.exp(-((a - math.pi / 2) / 0.35) ** 2)[None, :] * (1.0 - F.smooth(0.7, 0.95, u))[:, None]
        V = V - upv[:, None] * (0.0035 * groove)[..., None]
    verts = V.reshape(-1, 3)
    faces = []
    for i in range(nu):
        for j in range(nv):
            j1 = (j + 1) % nv
            faces.append((i * nv + j, i * nv + j1, (i + 1) * nv + j1, (i + 1) * nv + j))
    me = bpy.data.meshes.new(f'{"hi" if high else "lo"}_tongue')
    me.from_pydata(verts.tolist(), [], faces)
    me.update()
    me.shade_smooth()
    name = f'{"hi" if high else "lo"}_tongue'
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    # the closed ends are rings of zero radius: weld them
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me)
    bm.free()
    co, _vn = S.mesh_arrays(ob)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    # u by projection on the axis
    d = co[:, None, :] - pts[None, :-1, :]
    ab = (pts[1:] - pts[:-1])
    tt = np.clip((d * ab[None]).sum(axis=2) / (ab * ab).sum(axis=1)[None], 0.0, 1.0)
    proj = pts[None, :-1] + tt[..., None] * ab[None]
    dist = np.linalg.norm(co[:, None] - proj, axis=2)
    k = np.argmin(dist, axis=1)
    uu = (cum[k] + tt[np.arange(len(co)), k] * seg[k]) / cum[-1]
    c2 = _polyline(pts, uu)
    rel = co - c2
    across = rel[:, 0]
    S.add_attr(ob, 'tg_u', uu)
    S.add_attr(ob, 'tg_v', np.clip(across / 0.04, -1.0, 1.0))
    S.add_attr(ob, 'tg_top', F.smooth(-0.002, 0.004, rel[:, 2]))
    S.orient_away(ob, lambda fc: _polyline(pts, np.clip(_project_u(fc, pts, cum, seg), 0.0, 1.0)))
    if not high:
        S.tube_uvs(ob, [tuple(p) for p in pts])
    n = len(ob.data.vertices)
    for k in ('bag', 'bag_d', 'bag_floor', 'bag_a', 'bag_b', 'bag_t'):
        S.add_attr(ob, k, np.zeros(n))
    ob['prop'] = 'tongue'
    return ob


def _project_u(co: np.ndarray, pts: np.ndarray, cum: np.ndarray, seg: np.ndarray) -> np.ndarray:
    d = co[:, None, :] - pts[None, :-1, :]
    ab = (pts[1:] - pts[:-1])
    tt = np.clip((d * ab[None]).sum(axis=2) / (ab * ab).sum(axis=1)[None], 0.0, 1.0)
    proj = pts[None, :-1] + tt[..., None] * ab[None]
    dist = np.linalg.norm(co[:, None] - proj, axis=2)
    k = np.argmin(dist, axis=1)
    return (cum[k] + tt[np.arange(len(co)), k] * seg[k]) / cum[-1]
