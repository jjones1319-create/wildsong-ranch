"""Aurelwyrm's props (Art 2.1 Ultra), all in lo_props (always worn):
  - the antlers: two small branching velvet antlers (a beam rising up, out and back with a front tine and a top fork,
    the tips blunt and soft; a gold scaled collar at each base), one voxel-smoothed skin each, rigid on `head`
    (4-details panel 5, 2-turnaround, 3-faces);
  - the whiskers: two long, fine whiskers from the muzzle's sides, sweeping out, hanging and curling at their tips, on
    the mirrored chains whiskerL / whiskerR (1-hero, 2-turnaround front and side);
  - the golden mane: pointed gold feather-locks round the back of the face (the cheek ruff) and in rows down both sides
    of the neck beside the cream throat (2-turnaround front, 4-details panels 1 and 4); the crimson flame locks behind
    them are membranes (aurelwyrm_fins.py);
  - the mouth's pocket behind the lips (aurelwyrm_mouth.py).

Every prop object carries the same attributes (zero where they don't apply), so the joined mesh keeps them: the antlers'
ant, ant_t, collar; the whiskers' wh, wh_u, wh_side; the mane's mn, mn_u, mn_v, mn_id, mn_s; the pocket's bag, bag_d,
bag_floor, bag_a, bag_b, bag_t.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.mesh import Part
from lib.surface import smooth, v3
from monsters.breeds import aurelwyrm_form as F
from monsters.breeds import aurelwyrm_mouth as MO

ATTRS = ('ant', 'ant_t', 'collar', 'wh', 'wh_u', 'wh_side', 'mn', 'mn_u', 'mn_v', 'mn_id', 'mn_s', 'mn_cream',
         'bag', 'bag_d', 'bag_floor', 'bag_a', 'bag_b', 'bag_t')


def _complete(ob) -> bpy.types.Object:
    n = len(ob.data.vertices)
    for k in ATTRS:
        if k not in ob.data.attributes:
            S.add_attr(ob, k, np.zeros(n))
    return ob


def loft(c: np.ndarray, X: np.ndarray, Y: np.ndarray, rx: np.ndarray, ry: np.ndarray, seg: int,
         tip: bool = True) -> tuple[np.ndarray, list]:
    """A closed tube of elliptic rings round the centres (X x Y along the line: the faces wind outward), a fan cap at the
    start and a fan to a point past the end (or a flat cap)."""
    n = len(c)
    a = np.linspace(0.0, 2 * math.pi, seg, endpoint=False)
    ring = c[:, None] + X[:, None] * (rx[:, None] * np.cos(a)[None])[..., None] + Y[:, None] * (ry[:, None] * np.sin(a)[None])[..., None]
    verts = list(ring.reshape(-1, 3))
    faces = []
    for i in range(n - 1):
        for j in range(seg):
            jn = (j + 1) % seg
            faces.append((i * seg + j, i * seg + jn, (i + 1) * seg + jn, (i + 1) * seg + j))
    c0 = len(verts)
    verts.append(c[0])
    for j in range(seg):
        faces.append((c0, (j + 1) % seg, j))
    c1 = len(verts)
    d = c[-1] - c[-2]
    verts.append(c[-1] + (d / max(np.linalg.norm(d), 1e-9) * 0.6 * max(rx[-1], ry[-1]) if tip else 0.0))
    for j in range(seg):
        faces.append((c1, (n - 1) * seg + j, (n - 1) * seg + (j + 1) % seg))
    return np.array(verts), faces


def frames(c: np.ndarray, up) -> tuple[np.ndarray, np.ndarray]:
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    Y = np.broadcast_to(v3(up), c.shape) - T * (T @ v3(up))[:, None]
    Y /= np.linalg.norm(Y, axis=1, keepdims=True)
    X = np.cross(Y, T)
    return X, Y


def mesh(name: str, verts: np.ndarray, faces: list) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.asarray(verts).tolist(), [], faces)
    me.update()
    me.validate(verbose=False)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def smooth_curve(pts, n: int) -> np.ndarray:
    """n points evenly along a Catmull-Rom curve through pts."""
    c = F.catmull(pts, 24)
    s = F.arc(c)
    t = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(t, s, c[:, k]) for k in range(3)], axis=1)


# ============================================================================= the antlers
# the left antler (+X); the right mirrors it. The beam rises from the crown behind the brow, up, out and back, its tip
# turning up; a front tine leaves its lower third, a top tine its upper part (4-details panel 5: three soft points)
# (shape 2: small, as the card says: thicker, about 0.2 m above the skull, the tines short, soft and curving up)
# (round 2: a thick tapering beam rising up, out and back; the tines branch off its back and curve up and forward, its
# own tip too: three parallel tines read as a fork or a hand from the front)
# (round 3: the main beam curves back, then up at its end; two shorter tines splay apart at different lengths, the
# front one up and forward, the middle one up and out: three equal parallel tines read as a fork or a rake)
_A = [(0.056, -1.062, 1.395), (0.07, -1.032, 1.44), (0.096, -0.975, 1.47), (0.126, -0.905, 1.49), (0.152, -0.845, 1.515),
      (0.168, -0.806, 1.556), (0.174, -0.795, 1.6), (0.172, -0.805, 1.628)]
_T = [
    [(0.08, -1.02, 1.455), (0.077, -1.05, 1.492), (0.078, -1.085, 1.516), (0.083, -1.112, 1.526)],    # the front tine: forward
    [(0.124, -0.91, 1.49), (0.138, -0.925, 1.535), (0.15, -0.948, 1.568), (0.158, -0.968, 1.585)],    # the middle tine: up, out
]
ANT_BEAM = [(p[0], p[1], p[2] + F.HDZ) for p in _A]
ANT_BASE = ANT_BEAM[0]
ANT_TINES = [[(p[0], p[1], p[2] + F.HDZ) for p in t] for t in _T]
ANT_R = (0.036, 0.016)              # the beam's radius at its base and its tip
TINE_R = (0.02, 0.0125)
COLLAR = (0.034, 0.03)              # the gold collar's radius and height at the base


def antler_parts(s: int) -> list[Part]:
    ps = []

    def chain(pts, r0, r1, n, tag):
        c = smooth_curve([F.v3((p[0] * s, p[1], p[2])) for p in pts], n)
        r = np.linspace(r0, r1, n)
        for i in range(n - 1):
            ps.append(Part(f'{tag}{i}', 'tube', loc=tuple(c[i]), to=tuple(c[i + 1]), radius=float(r[i]), r2=float(r[i + 1])))
    chain(ANT_BEAM, ANT_R[0], ANT_R[1], 22, 'beam')
    for k, t in enumerate(ANT_TINES):
        chain(t, TINE_R[0], TINE_R[1], 10, f'tine{k}')
    b = F.v3((ANT_BASE[0] * s, ANT_BASE[1], ANT_BASE[2]))
    d = F.unit(F.v3(ANT_BEAM[1]) * np.array((s, 1, 1)) - b)
    ps.append(Part('collar', 'tube', loc=tuple(b - d * 0.02), to=tuple(b + d * COLLAR[1]), radius=COLLAR[0], r2=COLLAR[0] * 0.86))
    return ps


def antlers(high: bool) -> list[bpy.types.Object]:
    out = []
    for s in (1, -1):
        tag = 'hi' if high else 'lo'
        ob = S.build_body(f'{tag}_antler{"L" if s > 0 else "R"}', antler_parts(s), 0.0022 if high else 0.0035, 3, segments=20,
                          coll='AntlerParts')
        if not high:
            S.decimate_to(ob, 1300, smooth_after=0.0)
        co, vn = S.mesh_arrays(ob)
        b = F.v3((ANT_BASE[0] * s, ANT_BASE[1], ANT_BASE[2]))
        d = F.unit(F.v3(ANT_BEAM[1]) * np.array((s, 1, 1)) - b)
        h = (co - b) @ d
        if high:
            # the velvet: a fine soft fuzz
            from monsters.breeds import bloatoad_noise as N
            fz = N.fbm(co, 1 / 0.0012, 91 + s, 2)
            S.set_positions(ob, co + vn * (0.0005 * fz * smooth(0.03, 0.05, h))[:, None])
        top = max(float(np.linalg.norm(F.v3(p) - F.v3(ANT_BASE))) for p in ANT_BEAM + [q for t in ANT_TINES for q in t])
        S.add_attr(ob, 'ant', np.ones(len(co)))
        S.add_attr(ob, 'ant_t', np.clip(np.linalg.norm(co - b, axis=1) / top, 0.0, 1.0))
        S.add_attr(ob, 'collar', smooth(COLLAR[1] + 0.006, COLLAR[1] - 0.004, h))
        ob['prop'] = 'antlers'
        out.append(_complete(ob))
    return out


def antler_top() -> float:
    return float(max(p[2] for p in ANT_BEAM + [q for t in ANT_TINES for q in t]) + ANT_R[1])


# ============================================================================= the whiskers
# from the muzzle's side just behind the nose: sweeping out and a little down, then curling up and back into an open
# spiral with a pale feathered end (round 2: even rods hanging straight down; 1-hero, 3-faces). The chain's points are
# the first part; the curl rides the last bone.
# (round 3: rooted on the upper lip behind the nose, not in the nostrils; the outer third curls down into an open
# loop that shows in the head shots; the outer half keeps a minimum thickness so it never beads at clip size)
# (polish: rooted on the upper lip just below and behind the nose pad, running out in front of the face: from the
# side they read as dowels from the muzzle's side through the cheek)
WHISKER = [(p[0], p[1], p[2] + F.HDZ) for p in ((0.018, -1.292, 1.214), (0.09, -1.33, 1.205), (0.17, -1.335, 1.18), (0.24, -1.31, 1.145))]
WHISKER_CURL = [(p[0], p[1], p[2] + F.HDZ) for p in ((0.275, -1.28, 1.108), (0.285, -1.255, 1.07), (0.27, -1.24, 1.045),
                                                     (0.245, -1.245, 1.046), (0.235, -1.257, 1.07), (0.245, -1.268, 1.09))]
WHISKER_R = (0.0062, 0.0024)
FEATHER = 0.032         # the fine filaments splaying from each tip


def whisker_points(s: int) -> list[tuple]:
    return [(p[0] * s, p[1], p[2]) for p in WHISKER]


def whiskers(high: bool) -> list[bpy.types.Object]:
    out = []
    for s in (1, -1):
        pts = [F.v3((p[0] * s, p[1], p[2])) for p in WHISKER + WHISKER_CURL]
        n = 90 if high else 34
        c = smooth_curve(pts, n)
        X, Y = frames(c, (0, -1, 0))
        u = F.arc(c) / F.arc(c)[-1]
        r = np.maximum(WHISKER_R[0] + (WHISKER_R[1] - WHISKER_R[0]) * u ** 0.9, WHISKER_R[1])   # a clear taper, never thinner
        v, f = loft(c, X, Y, r, r, 10 if high else 6)
        # the feathered end (polish: a three-prong twig read as a stick): a soft, short, flat fan of three pale-gold
        # vanes in one plane
        d = F.unit(c[-1] - c[-3])
        for k in range(3):
            a = (k - 1) * 0.42
            dd = F.unit(d * np.cos(a) + X[-1] * np.sin(a))
            tf = {'root': c[-1] - d * 0.004, 'dir': dd, 'across': X[-1], 'L': FEATHER * (1.0 - 0.15 * abs(k - 1)),
                  'W': FEATHER * 0.32, 'bend': np.zeros(3), 's': 0.0, 'seed': 0}
            v2, f2, _a = blade(tf, 0, high)
            f += [tuple(q + len(v) for q in face) for face in f2]
            v = np.vstack([v, v2])
        ob = mesh(f'{"hi" if high else "lo"}_whisker{"L" if s > 0 else "R"}', v, f)
        co, _ = S.mesh_arrays(ob)
        from lib import ultra as U
        uu, _L = U.polyline_param(co, c)
        S.add_attr(ob, 'wh', np.ones(len(co)))
        S.add_attr(ob, 'wh_u', np.clip(uu, 0.0, 1.0))
        S.add_attr(ob, 'wh_side', np.full(len(co), float(s)))
        ob['prop'] = 'whiskers'
        out.append(_complete(ob))
    return out


# ============================================================================= the golden mane
def _mane_spec() -> list[dict]:
    """Every gold lock: root, direction, the across direction of its vane, length, half width, bend, its place along the
    body (mn_s: < 0 on the head) for the weights, and whether it is cream cheek fluff.
    Round 3 (the reviewer: about 12 broad gold leaves read as a sunflower or artichoke collar, a row of tabs ran down
    the neck): three layers of narrow pointed locks round the back of the face, streaming back like flame and tipping to
    orange; a few more on the neck's upper half only; pointed cream fluff on each cheek sweeping back to the ears."""
    rng = np.random.default_rng(31)
    out = []
    hc = np.array((0.0, -1.03, 1.25 + F.HDZ))

    def add(root, d, across, L, W, bend, s_=-0.05, cream=0.0):
        out.append({'root': root, 'dir': F.unit(d), 'across': F.unit(across), 'L': L, 'W': W, 'bend': bend, 's': s_,
                    'cream': cream, 'seed': int(rng.integers(1 << 30))})
    for layer, (rr, dy, n, L0) in enumerate(((0.112, 0.0, 15, 0.11), (0.126, 0.026, 16, 0.14), (0.138, 0.052, 15, 0.17))):
        for a in np.linspace(-128.0, 128.0, n) + (6.0 if layer == 1 else 0.0):
            if abs(a) < 12.0:
                continue
            ar = math.radians(a + rng.uniform(-4, 4))
            rad = np.array((math.sin(ar), 0.0, math.cos(ar)))
            root = hc + rad * np.array((rr, 0.0, rr * 0.96)) + np.array((0.0, dy + 0.012 * rng.uniform(-1, 1), 0.0))
            low = smooth(40.0, 120.0, abs(a))
            d = rad * 0.75 + np.array((0.0, 0.75 + 0.15 * layer, 0.0)) + np.array((0.0, 0.0, -0.3 * low))
            # (build 9) narrower, the vane turned 40 degrees toward the body's line: leaf faces read as bananas head-on
            across = F.unit(np.cross(F.unit(d), np.array((0.0, 1.0, 0.0))) + np.array((0.0, 0.8, 0.0)))
            L = (L0 + 0.04 * low) * (1.0 + 0.15 * rng.uniform(-1, 1))
            add(root, d, across, L, L * 0.085, np.array((0.0, 0.14, 0.0)) + rad * 0.04)
    # the neck's upper half: a few locks streaming down its sides, merged into the ruff (they stop well above the chest)
    for s_ in np.linspace(0.06, F.S_NECK * 0.42, 3):
        p, T, D, Lft = F.frame_at(float(s_))
        r = float(F.radius(s_))
        for side in (1, -1):
            for phi in (1.1, 1.55):
                ph = side * (phi + rng.uniform(-0.1, 0.1))
                rad = D * math.cos(ph) + Lft * math.sin(ph)
                d = T * 0.9 + rad * 0.3
                across = np.cross(F.unit(d), rad)
                L = (0.15 - 0.04 * s_ / F.S_NECK) * (1.0 + 0.12 * rng.uniform(-1, 1))
                add(p + rad * (r * 0.9), d, across, L, L * 0.13, rad * 0.06, s_=float(s_))
    # (polish: the cream cheek tufts are gone: shaded under the ruff they read as grey-silver cards and specks)
    return out


def blade(f: dict, fid: int, high: bool) -> tuple[np.ndarray, list, dict]:
    """A pointed gold lock: a lens-section blade, widest a third along, a fine curved point (as a feather's vane, without
    barbs: 4-details panel 4's gold locks)."""
    nu, nv = (26, 4) if high else (9, 2)                 # (polish: 7 x 1 showed facets)
    u = np.linspace(-0.08, 0.97, nu)
    v = np.linspace(-1.0, 1.0, 2 * nv + 1)
    uu = np.clip(u, 0.0, None)
    c = f['root'][None] + f['dir'][None] * (f['L'] * u)[:, None] + f['bend'][None] * (f['L'] * uu ** 2)[:, None]
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    X = f['across'][None] - T * (T @ f['across'])[:, None]
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    N = np.cross(T, X)
    # (round 2) a soft feather: widest near its middle, a rounded point
    w = (0.45 + 0.55 * smooth(0.0, 0.35, u)) * np.sqrt(np.clip(1.0 - smooth(0.45, 1.0, u) ** 1.8, 0.0, 1.0))
    halfw = np.maximum(f['W'] * w, 0.0015)
    thick = 0.0018 * (1.0 - 0.6 * smooth(0.3, 1.0, u)) + 0.0004
    rings = []
    for i in range(len(u)):
        base = c[i][None] + X[i][None] * (v * halfw[i])[:, None]
        t = thick[i] * np.sqrt(np.clip(1.0 - v ** 2, 0.0, 1.0))
        top = base + N[i][None] * t[:, None]
        bot = base - N[i][None] * (t * 0.8)[:, None]
        rings.append(np.vstack([top, bot[-2:0:-1]]))
    m = len(rings[0])
    verts = np.vstack(rings)
    faces = []
    for i in range(len(rings) - 1):
        for j in range(m):
            j1 = (j + 1) % m
            faces.append((i * m + j, (i + 1) * m + j, (i + 1) * m + j1, i * m + j1))
    c0 = len(verts)
    tipp = f['root'] + f['dir'] * f['L'] + f['bend'] * f['L']
    verts = np.vstack([verts, c[0][None], tipp[None]])
    last = (len(rings) - 1) * m
    for j in range(m):
        faces.append((c0, j, (j + 1) % m))
        faces.append((c0 + 1, last + (j + 1) % m, last + j))
    vv = np.concatenate([v, v[-2:0:-1]])
    n = len(verts)
    attrs = {'mn': np.ones(n), 'mn_u': np.clip(np.concatenate([np.repeat(u, m), [0.0, 1.0]]), 0, 1),
             'mn_v': np.concatenate([np.tile(vv, len(u)), [0.0, 0.0]]), 'mn_id': np.full(n, (fid * 0.618) % 1.0),
             'mn_s': np.full(n, f['s']), 'mn_cream': np.full(n, f.get('cream', 0.0))}
    return verts, faces, attrs


def mane(high: bool) -> bpy.types.Object:
    vs, fs, at = [], [], {}
    off = 0
    spec = _mane_spec()
    for i, f in enumerate(spec):
        v, fc, a = blade(f, i, high)
        vs.append(v)
        fs += [tuple(q + off for q in face) for face in fc]
        for k, val in a.items():
            at.setdefault(k, []).append(val)
        off += len(v)
    ob = mesh(f'{"hi" if high else "lo"}_mane', np.vstack(vs), fs)
    for k, val in at.items():
        S.add_attr(ob, k, np.concatenate(val).astype(np.float64))
    ob['prop'] = 'mane'
    C.log(f'{ob.name}: {len(fs)} faces in {len(spec)} gold locks')
    return _complete(ob)


# ============================================================================= all of them
def build(high: bool, quick: bool) -> list[bpy.types.Object]:
    out = antlers(high) + whiskers(high) + [mane(high)]
    lo = bpy.data.objects.get('lo_body')
    if lo is not None:
        if 'jside' not in lo.data.attributes:
            # the game mesh is final here (after its decimation): cut its mouth, then grow the pocket from the cut
            MO.cut_mouth(lo)
        out.append(_complete(MO.pocket(high)))
    return out
