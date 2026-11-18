"""Coilfang's mouth (Art 2.1 Ultra): a small snake smile that opens wide (the Fang Snap lunge, the Venom Mist hiss, a
yawn), with a closed, dark mouth behind the lips at every opening (Bloatoad's lesson, ART_2_DETAIL §9.9).

The line: a smile round a vertical axis at MOUTH_Y (theta 0 at the snout's front, +- toward the corners under the front
of each eye), its height MOUTH_Z(theta) (the corners curl up a little: 3-faces neutral). The game mesh is cut along it
after its decimation (each edge crossing the line split on it, so each lip ends in one smooth curve); the cut's two
edges are the lips. A pocket grows from the cut's own edges inward and up into the roof (behind the upper lip) and down
into the floor (behind the lower lip, the tongue's bed), closed by a back wall; each pocket vertex follows its two lip
vertices' weights, so no pose opens a gap (bloatoad_props.py, ported).
"""
from __future__ import annotations

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth
from monsters.breeds import coilfang_form as F

# round 2: a real smile (3-faces neutral, 1-hero): the line runs back to under the eye and curls up at the corners
MOUTH_Y = -0.71
MOUTH_TH = [0.0, 19.0, 35.0, 48.0, 57.0, 63.0, 67.0]
MOUTH_Z = [0.536, 0.537, 0.541, 0.548, 0.558, 0.571, 0.586]
MOUTH_END = 67.5
CUT_END = MOUTH_END - 2.5
CUT_SNAP = 0.22
JAW_HINGE = (0.0, -0.745, 0.565)
JAW_TIP = (0.0, -0.905, 0.52)


def mouth_theta(co: np.ndarray) -> np.ndarray:
    return np.degrees(np.arctan2(co[:, 0], -(co[:, 1] - MOUTH_Y)))


def mouth_z(th: np.ndarray) -> np.ndarray:
    return np.interp(np.abs(th), MOUTH_TH, MOUTH_Z)


def face_front(co: np.ndarray) -> np.ndarray:
    """The front of the head round the mouth (the lips, the snout's and the chin's fronts)."""
    return (F.ell_sdf(co, (0.0, -0.81, 0.56), (0.2, 0.2, 0.1)) < 0.02) & (co[:, 1] < -0.66)


def mouth_field(co: np.ndarray, vn: np.ndarray | None = None) -> dict:
    """The lips: a shallow crease along the line (the cut makes the opening, the paint the one dark line), a soft roll
    on each lip, a little tuck at each corner; dz = height above the line (the paint's per-pixel line)."""
    th = mouth_theta(co)
    dz = co[:, 2] - mouth_z(th)
    ff = face_front(co)
    span = smooth(MOUTH_END + 1.0, MOUTH_END - 4.0, np.abs(th)) * ff
    groove = np.exp(-(dz / 0.0022) ** 2) * span
    upper = np.exp(-((dz - 0.008) / 0.007) ** 2) * span
    lower = np.exp(-((dz + 0.009) / 0.008) ** 2) * span
    corner = np.exp(-((np.abs(th) - MOUTH_END) / 2.5) ** 2 - (dz / 0.009) ** 2) * ff
    disp = -0.0016 * groove + 0.0012 * upper + 0.0010 * lower - 0.003 * corner
    return {'disp': disp, 'mouth': np.clip(groove + 0.6 * corner, 0, 1), 'lip': np.clip(upper + lower, 0, 1), 'span': span,
            'corner': corner, 'dz': dz}


def jaw_weight(co: np.ndarray) -> np.ndarray:
    """0..1: the lower jaw (below the line, in front of the corners): rigid on `jaw`, fading into the throat."""
    th = mouth_theta(co)
    dz = mouth_z(th) - co[:, 2]
    w = smooth(-0.002, 0.002, dz) * smooth(0.075, 0.03, dz) * smooth(MOUTH_END + 1.0, MOUTH_END - 9.0, np.abs(th))
    return np.clip(w * face_front(co) * (co[:, 1] < -0.69), 0.0, 1.0)


# ============================================================================= the cut (on the decimated game mesh)
def cut_mouth(ob) -> int:
    """Cut lo_body along the line (Bloatoad's polish method): split every edge crossing it where it crosses (or move
    its near end onto it), split each face there, then cut the edges along the line. The corners stay joined. Stores
    `jside` (1 the jaw's side, 0 the head's, 0.5 both: the cut's ends, -1 away from it)."""
    import bmesh
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    lay = bm.verts.layers.float.new('mf')

    def field(v) -> float:
        c = np.array([v.co[:]])
        return float(mouth_z(mouth_theta(c))[0] - c[0, 2])

    def inside(v) -> bool:
        c = np.array([v.co[:]])
        return bool((np.abs(mouth_theta(c)) < CUT_END + 2.0)[0] and face_front(c)[0] and c[0, 1] < -0.7)

    zone = set()
    for v in bm.verts:
        f = field(v)
        v[lay] = f
        if abs(f) < 0.03 and inside(v):
            zone.add(v)

    def on_line(v) -> None:
        c = np.array([v.co[:]])
        v.co.z = float(mouth_z(mouth_theta(c))[0])
        v[lay] = 0.0

    for e in list(bm.edges):
        a, b = e.verts
        if a not in zone or b not in zone:
            continue
        fa, fb = a[lay], b[lay]
        if fa == 0.0 or fb == 0.0 or (fa > 0) == (fb > 0):
            continue
        t = fa / (fa - fb)
        if t < CUT_SNAP:
            on_line(a)
        elif t > 1.0 - CUT_SNAP:
            on_line(b)
    for e in list(bm.edges):
        a, b = e.verts
        if a not in zone or b not in zone:
            continue
        fa, fb = a[lay], b[lay]
        if fa == 0.0 or fb == 0.0 or (fa > 0) == (fb > 0):
            continue
        _ne, nv = bmesh.utils.edge_split(e, a, fa / (fa - fb))
        on_line(nv)
        zone.add(nv)
    for fc in list(bm.faces):
        vs = list(fc.verts)
        if not any(v in zone for v in vs):
            continue
        ons = [v for v in vs if v[lay] == 0.0 and v in zone]
        if len(ons) != 2:
            continue
        if not (any(v[lay] > 0 for v in vs) and any(v[lay] < 0 for v in vs)):
            continue
        if any(set(e.verts) == set(ons) for e in fc.edges):
            continue
        try:
            bmesh.utils.face_split(fc, ons[0], ons[1])
        except ValueError:
            pass
    big = [fc for fc in bm.faces if len(fc.verts) > 3]
    if big:
        bmesh.ops.triangulate(bm, faces=big)

    def side(fc) -> int:
        f = [v[lay] for v in fc.verts if v[lay] != 0.0]
        return 0 if not f else (1 if sum(f) > 0 else -1)

    cut = []
    for e in bm.edges:
        a, b = e.verts
        if a[lay] != 0.0 or b[lay] != 0.0 or a not in zone or b not in zone or len(e.link_faces) != 2:
            continue
        mid = np.array([[(a.co.x + b.co.x) / 2, (a.co.y + b.co.y) / 2, (a.co.z + b.co.z) / 2]])
        if abs(mouth_theta(mid)[0]) >= CUT_END:
            continue
        if side(e.link_faces[0]) * side(e.link_faces[1]) < 0:
            cut.append(e)
    if cut:
        bmesh.ops.split_edges(bm, edges=cut)
    bm.verts.ensure_lookup_table()
    js = np.full(len(bm.verts), -1.0)
    for v in bm.verts:
        if v not in zone and abs(v[lay]) >= 0.03:
            continue
        sides = {side(fc) for fc in v.link_faces} - {0}
        if not sides or not inside(v):
            continue
        js[v.index] = 1.0 if sides == {1} else (0.0 if sides == {-1} else 0.5)
    bm.verts.layers.float.remove(lay)
    bm.to_mesh(me)
    bm.free()
    me.update()
    if me.validate(verbose=False):
        C.log('mouth: validate() fixed invalid geometry after the cut')
    S.add_attr(ob, 'jside', js)
    C.log(f'mouth: cut {len(cut)} edges along the line; {int((js == 1).sum())} jaw-side, {int((js == 0).sum())} head-side vertices')
    return len(cut)


def jside(n: int):
    """lo_body's `jside` (set by cut_mouth) when the rig asks for the game mesh's weights, else None."""
    try:
        ob = bpy.data.objects.get('lo_body')
        if ob is None or len(ob.data.vertices) != n or 'jside' not in ob.data.attributes:
            return None
        return S.attr_array(ob, 'jside').astype(np.float64)
    except Exception:
        return None


# ============================================================================= the pocket behind the lips
POCKET_S = (0.0, 0.08, 0.25, 0.5, 0.78, 1.0)
POCKET_G = (0.0, 0.45, 0.85, 1.0, 0.92, 0.75)
POCKET_M = 64
POCKET_BACK = 0.035
POCKET_V = (0.032, 0.03)            # the roof's rise and the floor's drop (metres) at the front
POCKET_GAP = 0.003


def _lip_loop(lo) -> tuple[list[int], np.ndarray, np.ndarray]:
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
        raise SystemExit('coilfang mouth pocket: the game mesh has no cut (coilfang_mouth.cut_mouth)')
    loop = max(loops, key=len)
    if len(loops) > 1:
        C.log(f'mouth pocket: {len(loops)} open edges on the game mesh; the lips are the longest ({len(loop)} vertices)')
    js = S.attr_array(lo, 'jside').astype(np.float64)[loop]
    pos = co[loop]
    th = mouth_theta(pos)
    ends = [i for i in range(len(loop)) if 0.25 < js[i] < 0.75]
    if len(ends) != 2:
        C.log(f'mouth pocket: {len(ends)} corner vertices on the lips (2 expected); taking the widest on each side')
        ends = [int(np.argmax(np.where(pos[:, 0] > 0, np.abs(th), -1.0))), int(np.argmax(np.where(pos[:, 0] <= 0, np.abs(th), -1.0)))]
        js[ends] = 0.5
    r = ends[0]
    return loop[r:] + loop[:r], np.roll(pos, -r, axis=0), np.roll(js, -r)


def pocket(high: bool) -> bpy.types.Object:
    """The mouth's inside: a pocket grown from the lips' cut edges inward and closed by a back wall, its faces toward its
    inside. Attributes: bag 1, bag_d (0 at the lips -> 1 at the back wall), bag_floor (1 on the floor: the tongue's
    bed), bag_a, bag_b, bag_t (the two lo_body lip vertices each vertex follows and how far between them; -1 on the
    back wall's middle)."""
    from mathutils.bvhtree import BVHTree
    lo = bpy.data.objects['lo_body']
    loop, P0, js = _lip_loop(lo)
    n0 = len(loop)
    seg = np.linalg.norm(np.diff(np.vstack([P0, P0[:1]]), axis=0), axis=1)
    t0 = np.concatenate([[0.0], np.cumsum(seg)[:-1]]) / seg.sum()
    sg0 = np.clip((0.5 - js) * 2.0, -1.0, 1.0)            # +1 the upper lip, -1 the lower, 0 a corner
    other = [i for i in range(1, n0) if 0.25 < js[i] < 0.75]
    tc = t0[other[0]] if other else 0.5
    half = POCKET_M // 2
    tau = np.concatenate([np.linspace(0.0, tc, half, endpoint=False), np.linspace(tc, 1.0, POCKET_M - half, endpoint=False)])
    ia = np.clip(np.searchsorted(t0, tau, side='right') - 1, 0, n0 - 1)
    ib = (ia + 1) % n0
    span = np.where(ib == 0, 1.0 - t0[ia], t0[ib] - t0[ia])
    ft = np.clip((tau - t0[ia]) / np.maximum(span, 1e-9), 0.0, 1.0)
    p_lip = P0[ia] * (1 - ft)[:, None] + P0[ib] * ft[:, None]
    sg = sg0[ia] * (1 - ft) + sg0[ib] * ft
    th = mouth_theta(p_lip)
    c = np.clip(np.cos(np.radians(th)), 0.0, 1.0)
    hz = np.stack([-p_lip[:, 0], MOUTH_Y - p_lip[:, 1]], axis=1)
    rad = np.linalg.norm(hz, axis=1)
    u_in = hz / np.maximum(rad, 1e-6)[:, None]
    depth = np.maximum(rad - POCKET_BACK, 0.02)
    rise = np.where(sg > 0, POCKET_V[0], POCKET_V[1]) * (0.3 + 0.7 * c) * sg
    verts = [P0]
    for s_, g in zip(POCKET_S[1:], POCKET_G[1:]):
        r = p_lip.copy()
        r[:, :2] += u_in * (s_ * depth)[:, None]
        r[:, 2] += g * rise
        verts.append(r)
    V = np.vstack(verts + [verts[-1].mean(axis=0)[None]])
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
    i = j = 0
    A_, B_ = ring[0], ring[1]
    while i < n0 or j < POCKET_M:
        ta = t0[i + 1] if i + 1 < n0 else 1.0
        tb = tau[j + 1] if j + 1 < POCKET_M else 1.0
        if i < n0 and (j >= POCKET_M or ta <= tb):
            faces.append((A_[i], A_[(i + 1) % n0], B_[j % POCKET_M]))
            i += 1
        else:
            faces.append((A_[i % n0], B_[(j + 1) % POCKET_M], B_[j % POCKET_M]))
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
    # the first band twice, the copy facing the other way (a simplified Lite lip shows this band's dark back, never
    # the background)
    src = np.arange(n0 + POCKET_M)
    off = len(V)
    V = np.vstack([V, V[src]])
    faces += [tuple(off + q for q in reversed(f)) for f in faces[:nz]]
    name = f'{"hi" if high else "lo"}_mouthbag'
    me = bpy.data.meshes.new(name)
    me.from_pydata(V.tolist(), [], faces)
    me.update()
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
    d = ext(np.concatenate([np.zeros(n0)] + [np.full(POCKET_M, s_) for s_ in POCKET_S[1:]] + [[1.0]]))
    sgv = ext(np.concatenate([sg0] + [sg] * (len(POCKET_S) - 1) + [[0.0]]))
    S.add_attr(ob, 'bag', np.ones(n))
    S.add_attr(ob, 'bag_d', d)
    S.add_attr(ob, 'bag_floor', (sgv < -0.5) * smooth(0.03, 0.2, d))
    lip = np.asarray(loop, np.float64)
    S.add_attr(ob, 'bag_a', ext(np.concatenate([lip] + [lip[ia]] * (len(POCKET_S) - 1) + [[-1.0]])))
    S.add_attr(ob, 'bag_b', ext(np.concatenate([lip] + [lip[ib]] * (len(POCKET_S) - 1) + [[-1.0]])))
    S.add_attr(ob, 'bag_t', ext(np.concatenate([np.zeros(n0)] + [ft] * (len(POCKET_S) - 1) + [[0.0]])))
    ob['prop'] = 'mouthbag'
    C.log(f'mouth pocket: {n0} lip vertices, {len(POCKET_S) - 1} rings of {POCKET_M}, {len(me.polygons)} faces, '
          f'{moved} vertices kept inside the skin')
    return ob
