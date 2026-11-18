"""Galeheron's props (Art 2.1 Ultra), all always worn, in lo_props:
  - the wings: rigid feather blades on the wing bones (plans/avian.py wings, two fingers a wing): the secondaries hang
    from the arm, the primaries from the hand, three rows of coverts over them and the primary coverts; folded (the rest
    pose) they lie down the flank as the hero's cloak and hug the body; spread, the bones swing them out to the side,
    hanging and fanned as the turnaround's 'wings' view;
  - the crest: leaf-wide streaming plumes round the crown on three chains (crestm, crestL, crestR), twisted along
    their length, the tips rounded and curling (2-turnaround, 3-faces, 4-details panel 5);
  - the tail: long plumes hanging back and down from the rump on three chains (tail, tailsL, tailsR);
  - the dagger beak: the upper mandible rigid on `head`, the lower on `jaw`, flat where they meet (the mouth's inside).

Every blade is a closed lens-section vane (never a single sheet: no edge-on needles), at least 40% of its width at 90%
of its length, with a rounded tip. Every prop object carries the same attributes (zero where they don't apply):
  pk     1 wing feather, 2 crest plume, 3 tail plume, 4 upper mandible, 5 lower mandible
  fk     the wing row: 0 secondary, 1 primary, 2 greater covert, 3 median covert, 4 lesser covert, 5 primary covert
  fu fv  along the blade (0 root .. 1 tip) and across it (-1 .. 1); ftop +1 on the outer face, -1 the inner
  fid    a random number per blade; side +1 left / -1 right
  rx ry rz  the blade's root (the wing feathers ride their root's bone weights rigidly); fbone 1 + t on the hand
         (t 0 = the inner finger f3 .. 1 = the leading f1, blended between the three)
  cid cu the chain (0 crestm, 1 crestL, 2 crestR, 3 tail, 4 tailsL, 5 tailsR) and the blade's share along it
  bk_in  1 on a mandible's flat inner face (the mouth), bk_u along the beak (0 base .. 1 tip)

Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import galeheron_form as F
from monsters.breeds.galeheron_form import smooth, unit

ATTRS = ('pk', 'fk', 'fu', 'fv', 'ftop', 'fid', 'side', 'rx', 'ry', 'rz', 'fbone', 'cid', 'cu', 'bk_in', 'bk_u')

# ----------------------------------------------------------------------------- the wing (left, folded = rest)
WING = {'name': 'wing', 'parent': 'chest',
        # the arm runs back nearly level along the top of the folded wing (the elbow a little high), so the secondaries
        # hanging from it are near its normal and hang straight down from the spread arm
        # (build 2) nearer the spine, so the folded wings drape over the back as in the back view
        # (round 2) along the leaning back, the hand and its long primaries reaching back over the tail
        'shoulder': (0.095, -0.13, 1.075), 'elbow': (0.115, -0.005, 1.085), 'wrist': (0.12, 0.125, 1.045),
        'fingers': [(0.13, 0.43, 0.72), (0.125, 0.4, 0.69), (0.12, 0.36, 0.66)],
        'attach': (0.13, 0.12, 0.85),
        # spread (2-turnaround 'wings', 5-poses attack): the arm out and a little up, the three fingers fanned from
        # level (the leading primaries) to 60 degrees down (the inner ones), so the primaries overlap in a broad fan
        'spread': {'elbow': (0.4, -0.12, 1.11), 'wrist': (0.7, -0.11, 1.09),
                   'fingers': [(1.0, -0.09, 1.06), (0.97, -0.06, 0.92), (0.87, -0.04, 0.82)]}}
CHAIN_NAMES = ('crestm', 'crestL', 'crestR', 'tail', 'tailsL', 'tailsR')


def chains() -> list[dict]:
    """The rig's chains (plans/avian.py `chains`): the crest on `head`, the tail plumes on `hips`."""
    return [{'name': 'crestm', 'kind': 'crest', 'parent': 'head',
             'points': [(0.0, -0.17, 1.55), (0.0, -0.05, 1.62), (0.0, 0.11, 1.6), (0.0, 0.27, 1.5)]},
            {'name': 'crest', 'kind': 'crest', 'parent': 'head', 'mirror': True,
             'points': [(0.035, -0.15, 1.53), (0.11, -0.05, 1.54), (0.2, 0.07, 1.49), (0.26, 0.19, 1.41)]},
            {'name': 'tail', 'kind': 'plume', 'parent': 'hips',
             'points': [(0.0, 0.3, 0.72), (0.0, 0.42, 0.56), (0.0, 0.51, 0.4), (0.0, 0.57, 0.24)]},
            {'name': 'tails', 'kind': 'plume', 'parent': 'hips', 'mirror': True,
             'points': [(0.05, 0.29, 0.72), (0.11, 0.4, 0.57), (0.16, 0.48, 0.43), (0.19, 0.54, 0.29)]}]


# ----------------------------------------------------------------------------- one blade
def blade(c: np.ndarray, X: np.ndarray, hw: np.ndarray, th: np.ndarray, u: np.ndarray, nv: int, cup: float = 0.12,
          rachis: float = 0.0) -> tuple[np.ndarray, list, dict]:
    """A closed vane round the centre line c (n x 3) with unit across directions X (n x 3, normal to the line's
    tangent): half widths hw, half thicknesses th, cupped by `cup` (its edges turned toward -N), a raised rachis on
    the outer face. The faces wind outward (N = T x X is the outer face)."""
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.cross(T, X)
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    v = np.linspace(-1.0, 1.0, 2 * nv + 1)
    e = np.sqrt(np.clip(1.0 - v ** 2, 0.0, 1.0))
    rings, vv, top = [], None, None
    for i in range(len(c)):
        base = c[i][None] + X[i][None] * (v * hw[i])[:, None] - N[i][None] * (cup * hw[i] * v ** 2)[:, None]
        up = th[i] * e + rachis * th[i] * np.exp(-(v / 0.14) ** 2)
        t_ = base + N[i][None] * up[:, None]
        b_ = base - N[i][None] * (0.8 * th[i] * e)[:, None]
        rings.append(np.vstack([t_, b_[-2:0:-1]]))
    m = len(rings[0])
    vv = np.concatenate([v, v[-2:0:-1]])
    top = np.concatenate([np.ones(len(v)), -np.ones(len(v) - 2)])
    verts = np.vstack(rings)
    faces = []
    for i in range(len(rings) - 1):
        for j in range(m):
            j1 = (j + 1) % m
            faces.append((i * m + j, (i + 1) * m + j, (i + 1) * m + j1, i * m + j1))
    c0 = len(verts)
    tipp = c[-1] + T[-1] * max(0.35 * float(hw[-1]), 0.0015)
    verts = np.vstack([verts, (c[0] - T[0] * 0.002)[None], tipp[None]])
    last = (len(rings) - 1) * m
    for j in range(m):
        faces.append((c0, j, (j + 1) % m))
        faces.append((c0 + 1, last + (j + 1) % m, last + j))
    n = len(verts)
    attrs = {'fu': np.concatenate([np.repeat(u, m), [u[0], 1.0]]),
             'fv': np.concatenate([np.tile(vv, len(u)), [0.0, 0.0]]),
             'ftop': np.concatenate([np.tile(top, len(u)), [0.0, 0.0]])}
    return verts, faces, attrs


def u_samples(n: int) -> np.ndarray:
    """Along a blade, denser toward the rounded tip."""
    s = np.linspace(0.0, 1.0, n)
    return np.clip(0.985 * (1.0 - (1.0 - s) ** 1.35), 0.0, 0.985)


def vane_width(u: np.ndarray, root: float = 0.35, peak: float = 0.5, tip0: float = 0.6) -> np.ndarray:
    """0..1: narrow at the quill, full from `peak`, a rounded end after tip0 (about 0.65 at u 0.9)."""
    w = root + (1.0 - root) * smooth(0.0, peak, u)
    r = np.clip((u - tip0) / (1.0 - tip0), 0.0, 1.0)
    return w * np.sqrt(np.clip(1.0 - r ** 2, 0.0, 1.0)) ** 0.8


def frames_across(c: np.ndarray, out: np.ndarray, twist_deg: float = 0.0) -> np.ndarray:
    """Across directions normal to the line: perpendicular to `out` (the outer face's direction, n x 3 or 3), twisted
    linearly along the blade."""
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    o = np.broadcast_to(np.asarray(out, np.float64), c.shape)
    X = np.cross(o, T)
    X /= np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)
    if twist_deg:
        a = np.radians(twist_deg) * np.linspace(0.0, 1.0, len(c))
        N = np.cross(T, X)
        X = X * np.cos(a)[:, None] + N * np.sin(a)[:, None]
    return X


def _relax(c: np.ndarray, it: int = 6) -> np.ndarray:
    c = c.copy()
    for _ in range(it):
        c[1:-1] = 0.25 * c[:-2] + 0.5 * c[1:-1] + 0.25 * c[2:]
    return c


class Bag:
    """Blades gathered into one object, every attribute kept."""

    def __init__(self):
        self.v, self.f, self.a, self.off = [], [], {k: [] for k in ATTRS}, 0

    def add(self, verts, faces, attrs: dict, **const) -> None:
        n = len(verts)
        self.v.append(np.asarray(verts, np.float64))
        self.f += [tuple(q + self.off for q in fc) for fc in faces]
        for k in ATTRS:
            if k in attrs:
                self.a[k].append(np.asarray(attrs[k], np.float64))
            else:
                self.a[k].append(np.full(n, float(const.get(k, 0.0))))
        self.off += n

    def object(self, name: str, prop: str) -> bpy.types.Object:
        me = bpy.data.meshes.new(name)
        me.from_pydata(np.vstack(self.v).tolist(), [], self.f)
        me.update()
        me.validate(verbose=False)
        me.shade_smooth()
        ob = bpy.data.objects.new(name, me)
        C.link_obj(ob)
        for k in ATTRS:
            S.add_attr(ob, k, np.concatenate(self.a[k]))
        if name.startswith('lo_'):
            # (polish) texel density per face: the folded wing's covert and secondary rows (the swirls) the most, so
            # the Lite's 1024 px copy keeps them crisp; the bib and the plumes a little less
            pk = np.concatenate(self.a['pk'])
            fk = np.concatenate(self.a['fk'])
            first = np.array([fc[0] for fc in self.f])
            pkf, fkf = np.round(pk[first]), np.round(fk[first])
            kf = np.where((pkf == 1) & (fkf != 1), 1.7, np.where(pkf == 1, 1.2, np.where(pkf == 7, 0.8, np.where((pkf == 2) | (pkf == 3), 0.9, 1.0))))
            me.attributes.new('texel_k', 'FLOAT', 'FACE').data.foreach_set('value', kf.astype(np.float32))
        ob['prop'] = prop
        C.log(f'{name}: {len(self.f)} faces')
        return ob


# ----------------------------------------------------------------------------- the wing feathers
ROWS = {  # kind: (count, root offset down the feather's line (share of its length), length range, half width, layer)
    0: (12, 0.0, (0.4, 0.44), 0.037, 0),        # secondaries, along the arm
    1: (10, 0.0, (0.34, 0.48), 0.034, -1),      # primaries, along the hand, long over the tail (round 2)
    2: (12, 0.06, (0.17, 0.19), 0.03, 1),       # greater coverts
    3: (13, 0.02, (0.11, 0.12), 0.026, 2),      # median coverts
    4: (14, -0.08, (0.08, 0.085), 0.024, 3),    # lesser coverts, tucked up under the scapulars (round 3: a dark seam)
    5: (7, 0.02, (0.12, 0.15), 0.026, 1),       # primary coverts, along the hand
}


def _arm(s: int, u: np.ndarray) -> np.ndarray:
    q = U.wing_points(WING, s)
    pts = np.array([q['shoulder'], q['elbow'], q['wrist']], np.float64)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    acc = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    return np.stack([np.interp(u, acc, pts[:, k]) for k in range(3)], axis=1)


def wing_feathers(s: int) -> list[dict]:
    """One wing's feathers at rest (folded): root, direction, length, half width, layer, finger, row."""
    q = U.wing_points(WING, s)
    W = np.array(q['wrist'], np.float64)
    f1, f2, f3 = (np.array(t, np.float64) for t in q['fingers'])
    rng = np.random.default_rng(23)
    out = []
    for kind, (n, back, (L0, L1), hw, layer) in ROWS.items():
        for i in range(n):
            t = (i + 0.5) / n
            jit = rng.uniform(-1, 1, 3)
            if kind in (1, 5):
                # along the hand, from the wrist toward the fingers' tips; the outer ones on f1 (the leading finger),
                # the inner on f3, blended between
                tip = (f3 + (f2 - f3) * (2 * t)) if t < 0.5 else (f2 + (f1 - f2) * (2 * t - 1))
                root = W + (tip - W) * (0.08 + 0.72 * t if kind == 1 else 0.05 + 0.45 * t)
                d = unit(tip - W + np.array((-0.05 * s, 0.05 * t, -0.04)))      # converging over the tail
                fb = 1.0 + t
            else:
                root = _arm(s, np.array([0.04 + 0.94 * t]))[0]
                # down and back over the flank, a little more back toward the wrist
                d = unit(np.array((0.0, 0.16 + 0.24 * t, -1.0)))
                fb = 0
            L = (L0 + (L1 - L0) * t) * (1.0 + 0.03 * jit[0])
            root = root + d * L * back
            out.append({'root': root, 'd': d, 'L': L, 'hw': hw * (1.0 + 0.05 * jit[1]), 'layer': layer, 'fbone': fb, 'kind': kind,
                        'order': i / max(1, n - 1), 'seed': float(rng.uniform())})
    return out


def wing_blade(f: dict, s: int, high: bool) -> tuple[np.ndarray, list, dict]:
    nu, nv = (22, 4) if high else (9, 2)
    u = u_samples(nu)
    c = f['root'][None] + f['d'][None] * (f['L'] * u)[:, None]
    # hug the flank: never closer to the body than its layer's clearance (the folded cloak), relaxed smooth
    clear = 0.012 + 0.0068 * (f['layer'] + 1) + 0.0016 * f['order']
    xs = F.outside_x(c[:, 1], c[:, 2], head=False)
    want = np.where(xs > 0, xs + clear, 0.0)
    cx = np.maximum(s * c[:, 0], want)
    c[:, 0] = s * cx
    c = _relax(c, 4)
    c[:, 0] = s * np.maximum(s * c[:, 0], want * smooth(0.0, 0.15, u))
    out = np.array((float(s), 0.0, 0.0))
    X = frames_across(c, out, 6.0 * (f['seed'] - 0.5))
    hw = f['hw'] * vane_width(u, 0.4 if f['kind'] in (0, 1) else 0.55, 0.35, 0.62 if f['kind'] in (0, 1) else 0.5)
    hw = np.maximum(hw, 0.0016)
    th = (0.0024 - 0.0012 * u) * (1.0 if high else 1.1)
    # (round 3) flatter and without a ridged shaft: the ridges cut the swirls into dashes and read as vertical grooves
    return blade(c, X, hw, th, u, nv, cup=0.03, rachis=0.0)


def wings(high: bool) -> bpy.types.Object:
    bag = Bag()
    for s in (1, -1):
        for f in wing_feathers(s):
            v, fc, a = wing_blade(f, s, high)
            bag.add(v, fc, a, pk=1, fk=f['kind'], fid=f['seed'], side=s, rx=f['root'][0], ry=f['root'][1], rz=f['root'][2],
                    fbone=f['fbone'])
        for f in scapulars(s):
            v, fc, a = scapular_blade(f, high)
            bag.add(v, fc, a, pk=6, fid=f['seed'], side=s, rx=f['root'][0], ry=f['root'][1], rz=f['root'][2])
    return bag.object(f'{"hi" if high else "lo"}_wings', 'wings')


# ----------------------------------------------------------------------------- the scapulars (on the body)
def hug(c: np.ndarray, clear) -> np.ndarray:
    """Push points out along the body's field until they are `clear` off it (per point or one number)."""
    c = c.copy()
    clear = np.broadcast_to(np.asarray(clear, np.float64), (len(c),))
    for _ in range(5):
        d = F.body_sd(c)
        n = F.sd_normal(F.body_sd, c)
        c = c + n * np.maximum(0.0, clear - d)[:, None]
    return c


def scapulars(s: int) -> list[dict]:
    """Two rows of broad feathers over the back between the folded wings (2-turnaround back view: the wings' cloak
    meets at the spine), lying back and a little out; they ride the body (chest / hips), not the wings."""
    rng = np.random.default_rng(31)
    out = []
    # (round 2) three rows from the shoulders back over the rump (turn_back showed a bare rump between the wings)
    for row, (x0, n, L, hw) in enumerate(((0.025, 9, 0.2, 0.034), (0.06, 8, 0.18, 0.032), (0.035, 5, 0.22, 0.036))):
        for i in range(n):
            t = (i + 0.5) / n
            y = (-0.12 + 0.5 * t + 0.02 * row) if row < 2 else (0.22 + 0.22 * t)
            zc = 0.84 - 0.62 * (y - 0.03)
            x = s * (x0 + 0.01 * rng.uniform(-1, 1))
            root = F.surface_hit(F.body_sd, np.array((x, y, zc - 0.02)), np.array([[0.0, 0.0, 1.0]]), 0.5)[0]
            d = unit(np.array((s * (0.18 + 0.12 * (row == 1)), 0.85, -0.6 - 0.15 * t)))
            out.append({'root': root - np.array((0.0, 0.0, 0.006)), 'd': d, 'L': L * (1.0 + 0.05 * rng.uniform(-1, 1)), 'hw': hw,
                        'layer': row, 'seed': float(rng.uniform()), 's': s})
    return out


def scapular_blade(f: dict, high: bool) -> tuple[np.ndarray, list, dict]:
    nu, nv = (18, 4) if high else (8, 2)
    u = u_samples(nu)
    c = f['root'][None] + f['d'][None] * (f['L'] * u)[:, None]
    c = _relax(hug(c, 0.006 + 0.005 * f['layer'] + 0.004 * u), 3)
    n = F.sd_normal(F.body_sd, c)
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    X = np.cross(n, T)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    hw = np.maximum(f['hw'] * vane_width(u, 0.5, 0.35, 0.55), 0.0016)
    return blade(c, X, hw, 0.0022 - 0.001 * u, u, nv, cup=0.06, rachis=0.6 if high else 0.0)


# ----------------------------------------------------------------------------- plumes on chains
def catmull(pts, n: int = 200) -> np.ndarray:
    """n points evenly along a Catmull-Rom curve through pts (ends extrapolated)."""
    P = np.asarray(pts, np.float64)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t = np.linspace(0.0, 1.0, 40, endpoint=False)[:, None]
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2][None])
    c = np.vstack(out)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])
    t = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(t, s, c[:, k]) for k in range(3)], axis=1)


def resample(c: np.ndarray, us: np.ndarray) -> np.ndarray:
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])
    return np.stack([np.interp(us * s[-1], s, c[:, k]) for k in range(3)], axis=1)


def rmf_across(c: np.ndarray, out, twist_deg: float) -> np.ndarray:
    """Across directions by a rotation-minimising frame from the root (the outer face toward `out` there), twisted
    linearly along the line: never degenerate, however the line curls."""
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    o = np.asarray(out, np.float64) - T[0] * float(np.dot(out, T[0]))
    if np.linalg.norm(o) < 1e-3:
        o = np.array((1.0, 0.0, 0.0)) - T[0] * T[0][0]
    X = np.zeros_like(c)
    X[0] = unit(np.cross(unit(o), T[0]))
    for i in range(1, len(c)):
        x = X[i - 1] - T[i] * float(np.dot(T[i], X[i - 1]))
        X[i] = x / max(float(np.linalg.norm(x)), 1e-9)
    a = np.radians(twist_deg) * np.linspace(0.0, 1.0, len(c))
    N = np.cross(T, X)
    return X * np.cos(a)[:, None] + N * np.sin(a)[:, None]


def _root(az: float, back: float) -> np.ndarray:
    """A point on the skull round the head's long axis: azimuth 0 = the crown, +90 = the left side; `back` tilts the
    ray toward the nape (+) or the brow (-)."""
    a = math.radians(az)
    hc = np.array(F.HEAD_C)
    root = F.surface_hit(F.head_sd, hc, unit(np.array((math.sin(a), back, math.cos(a))))[None], 0.2)[0]
    return root - F.sd_normal(F.head_sd, root[None])[0] * 0.007


def crest_specs() -> list[dict]:
    """(round 3) The crest as a swept-back V (1-hero, 2-turnaround side and front, 4-details panels 1 and 5): every plume
    rooted over the crown and the back of the skull, sweeping back and climbing out to its own side at about 40 degrees
    from upright, so from the front the plumes form a V behind the head (not a ring); nothing rises at the brow. Four
    long plumes trail well behind the head in a gentle S, their tips lifting. Each: control points, the outer face's
    direction at the root, half width, twist, chain."""
    rng = np.random.default_rng(5)
    out = []

    def add(az, pts, face, hw, cid, tw=12.0, root_w=0.3):              # (polish) less twist: the tips turned into flags
        sgn = (1 if az >= 0 else -1) * (1 if len(out) % 2 else -1)
        out.append({'pts': pts, 'out': unit(face), 'hw': hw * (1.0 + 0.06 * rng.uniform(-1, 1)), 'twist': (tw + 10.0 * rng.uniform()) * sgn,
                    'cid': cid, 'seed': float(rng.uniform()), 'az': az, 'root_w': root_w})

    def walk(p0, L, steps):
        pts = [p0]
        for d, k in steps:
            pts.append(pts[-1] + unit(np.array(d)) * L * k)
        return pts
    for s in (1, -1):
        cid = 1 if s > 0 else 2
        # the long ones: from the top and the back of the crown, out to their side a little, a gentle S
        for az, back, L0, out_ in ((10.0, 0.05, 0.72, 0.28), (26.0, 0.3, 0.64, 0.42)):
            L = L0 * (1.0 + 0.04 * rng.uniform(-1, 1))
            # (polish) the third stretch level and the tip lifting: a dipping stretch hung the outer tips down like flags
        add(s * az, walk(_root(s * az, back), L, [((s * out_, 0.85, 0.5), 0.2), ((s * out_, 1.0, 0.06), 0.32),
                                                      ((s * out_ * 0.7, 0.95, -0.04), 0.28), ((s * out_ * 0.4, 0.8, 0.45), 0.2)]),
                (s * 0.5, 0.0, 1.0), 0.03, cid)
        # the shorter ones: back and up-and-out along the V's arm (the front view's lines at about 40 degrees)
        for k, (az, back, L0) in enumerate(((16.0, -0.15, 0.3), (32.0, -0.02, 0.36), (46.0, 0.12, 0.34), (58.0, 0.28, 0.3),
                                            (22.0, 0.2, 0.4), (40.0, 0.36, 0.32))):
            L = L0 * (1.0 + 0.08 * rng.uniform(-1, 1))
            rise = 0.55 + 0.1 * (k % 2)
            add(s * az, walk(_root(s * az, back), L, [((s * 0.62, 0.75, rise), 0.42), ((s * 0.62, 1.0, 0.3 * rise), 0.38),
                                                      ((s * 0.4, 0.9, 0.38), 0.2)]),
                (s * 0.7, 0.0, 0.7), 0.026, cid)
    return out


def tail_specs() -> list[dict]:
    """(round 3) The tail: seven long plumes cascading from under the wings' tips in a fan in the side plane (1-hero,
    2-turnaround side), from back-and-down to nearly straight down, to about knee height; their faces turned half
    out and half back, so the side and the back both see vanes (from behind they thinned to wire strands)."""
    rng = np.random.default_rng(9)
    out = []
    for i, k in enumerate(np.linspace(0.0, 1.0, 7)):
        x = (-1.0) ** i * (0.3 + 0.7 * k)
        ang = math.radians(28.0 + 50.0 * k)                       # below level
        p0 = np.array((0.035 * x, 0.33 - 0.05 * k, 0.665 - 0.03 * k))
        L = (0.6 - 0.08 * k) * (1.0 + 0.04 * rng.uniform(-1, 1))
        d1 = np.array((0.12 * x, math.cos(ang), -math.sin(ang)))
        a2 = ang + math.radians(12.0)
        d2 = np.array((0.16 * x, math.cos(a2), -math.sin(a2)))
        a3 = ang - math.radians(22.0)
        d3 = np.array((0.1 * x, math.cos(a3), -math.sin(a3)))
        pts = [p0]
        for d, f in ((d1, 0.42), (d2, 0.38), (d3, 0.2)):
            pts.append(pts[-1] + unit(d) * L * f)
        cid = 3 if i == 0 else (4 if x > 0 else 5)
        out.append({'pts': pts, 'out': unit(np.array((0.75 * np.sign(x), 0.65, 0.2))), 'hw': 0.052 - 0.006 * k, 'cid': cid,
                    'twist': 10.0 * np.sign(x) + 6.0 * rng.uniform(-1, 1), 'seed': float(rng.uniform()), 'az': x, 'root_w': 0.3})
    return out


def plume_width(u: np.ndarray, root_w: float, seed: float, high: bool) -> np.ndarray:
    """(round 3) A vane: narrow at the quill, widest at about 60% of its length, then tapering to a soft point (about
    45% of its width left at 90%), a few barb notches on its edges past its middle. (Round 2's near-even width with a
    rounded end read as noodles.)"""
    w = root_w + (1.0 - root_w) * np.sin(0.5 * np.pi * np.clip(u / 0.6, 0.0, 1.0)) ** 1.2
    w = w * (1.0 - 0.55 * smooth(0.6, 0.9, u))
    tip = np.clip((u - 0.9) / 0.1, 0.0, 1.0)
    w = w * (1.0 - tip ** 1.6) ** 0.55             # (polish) a soft, rounded point (a sharp one read as a stray spike edge-on)
    ph = np.mod(u * 7.0 + seed * 3.0, 1.0)
    notch = (ph ** 4) * smooth(0.45, 0.55, u) * (1.0 - smooth(0.74, 0.82, u))      # (polish) no ragged tips
    return w * (1.0 - 0.15 * notch)


def plume_blade(f: dict, high: bool, tail: bool) -> tuple[np.ndarray, list, dict]:
    nu, nv = (44, 4) if high else (22, 2)
    u = u_samples(nu)
    c = resample(catmull(f['pts']), u / 0.985)
    X = rmf_across(c, f['out'], f['twist'])
    hw = np.maximum(f['hw'] * plume_width(u, f.get('root_w', 0.3), f['seed'], high), 0.0012)
    th = 0.0022 - 0.0012 * u
    return blade(c, X, hw, th, u, nv, cup=0.08, rachis=0.0)


# ----------------------------------------------------------------------------- the bib and the trousers (round 3)
def bib_specs() -> list[dict]:
    """A shaggy bib of long, soft white feathers over the breast and the belly, shingled (each row's tips over the next
    row's roots), the lowest rows hanging over the legs' tops (1-hero); a few up the neck's front; and the trousers:
    feathers round each drumstick's top. They replace round 2's sculpted lobes, which read as thistle spikes."""
    rng = np.random.default_rng(17)
    out = []
    o = np.array((0.0, -0.11, 0.87))
    # (polish) two more rows over the upper breast and the shoulders' fronts (they read as smooth grey skin in 3/4)
    rows = [(68.0, 5, 0.11, 0.028), (57.0, 7, 0.12, 0.03), (46.0, 6, 0.13, 0.03), (32.0, 7, 0.14, 0.032), (18.0, 8, 0.15, 0.033), (4.0, 8, 0.155, 0.034), (-10.0, 9, 0.16, 0.034),
            (-24.0, 9, 0.165, 0.034), (-38.0, 9, 0.17, 0.033), (-52.0, 8, 0.17, 0.032)]
    nr = len(rows)
    for r, (el, n, L, hw) in enumerate(rows):
        span = (80.0 if el > 50 else 62.0) + 3.0 * r
        for az in np.linspace(-span, span, n) + (4.0 if r % 2 else -4.0):
            a, e = math.radians(az + rng.uniform(-3, 3)), math.radians(el + rng.uniform(-2, 2))
            d = np.array((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
            root = F.surface_hit(F.body_sd, o, d[None])[0]
            if abs(root[0]) > 0.115 and root[2] > 0.74:
                continue                                  # under the folded wing
            out.append({'root': root, 'down': np.array((0.0, 0.15, -1.0)), 'L': L * (1.0 + 0.1 * rng.uniform(-1, 1)), 'hw': hw,
                        'clear': 0.004 + 0.0035 * (nr - r), 'seed': float(rng.uniform())})
    # the neck's front, low: three short rows
    for j, u in enumerate((0.15, 0.3, 0.45)):
        k = int(u * (len(F.NECK) - 1))
        f = u * (len(F.NECK) - 1) - k
        c = np.array(F.NECK[k]) * (1 - f) + np.array(F.NECK[k + 1]) * f
        for az in ((-30.0, 0.0, 30.0) if j % 2 else (-45.0, -15.0, 15.0, 45.0)):
            a = math.radians(az)
            root = F.surface_hit(F.body_sd, c, unit(np.array((math.sin(a), -math.cos(a), -0.1)))[None], 0.2)[0]
            out.append({'root': root, 'down': np.array((0.0, 0.1, -1.0)), 'L': 0.1, 'hw': 0.024, 'clear': 0.004 + 0.003 * (3 - j),
                        'seed': float(rng.uniform())})
    for xg in (-0.09, -0.03, 0.03, 0.09):                 # (polish) the belly behind the legs (bare grey under the wing)
        for yg in (0.1, 0.2, 0.29):
            p0 = np.array((xg, yg, 0.84 - 0.62 * (yg - 0.03)))
            root = F.surface_hit(F.body_sd, p0, unit(np.array((0.3 * np.sign(xg), 0.15, -1.0)))[None], 0.4)[0]
            out.append({'root': root, 'down': np.array((0.25 * np.sign(xg), 0.6, -1.0)), 'L': 0.13, 'hw': 0.03, 'clear': 0.005,
                        'seed': float(rng.uniform())})
    for s in (1, -1):                                     # the trousers
        c = np.array((0.075 * s, -0.02, 0.8))
        for ang in np.linspace(0.0, 360.0, 11, endpoint=False) + 16.0:
            a = math.radians(ang)
            d = unit(np.array((0.55 * math.cos(a), 0.55 * math.sin(a), -1.0)))
            root = F.surface_hit(F.body_sd, c, d[None])[0]
            # (build 13) short and splayed: at 15 cm they wrapped each drumstick in a white sleeve with a hard hem
            out.append({'root': root, 'down': np.array((math.cos(a) * 0.3, math.sin(a) * 0.3, -1.0)), 'L': 0.12 + 0.02 * rng.uniform(-1, 1), 'hw': 0.028,
                        'clear': 0.006, 'seed': float(rng.uniform())})
    return out


def bib_blade(f: dict, high: bool) -> tuple[np.ndarray, list, dict]:
    nu, nv = (20, 4) if high else (10, 2)
    u = u_samples(nu)
    g = f['down']
    n0 = F.sd_normal(F.body_sd, f['root'][None])[0]
    d = unit(g - n0 * float(np.dot(g, n0)))
    c = f['root'][None] + d[None] * (f['L'] * u)[:, None]
    # hug the body (each row's clearance a little more than the row below it: shingles), the tip lifting a little
    c = _relax(hug(c, f['clear'] + 0.006 * u ** 2), 3)
    n = F.sd_normal(F.body_sd, c)
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    X = np.cross(n, T)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    hw = np.maximum(f['hw'] * plume_width(u, 0.4, f['seed'], high), 0.0012)
    return blade(c, X, hw, 0.0022 - 0.0011 * u, u, nv, cup=0.05, rachis=0.0)


def bib(high: bool) -> bpy.types.Object:
    bag = Bag()
    for f in bib_specs():
        v, fc, a = bib_blade(f, high)
        bag.add(v, fc, a, pk=7, fid=f['seed'], rx=f['root'][0], ry=f['root'][1], rz=f['root'][2])
    return bag.object(f'{"hi" if high else "lo"}_bib', 'bib')


def plumes(high: bool) -> bpy.types.Object:
    bag = Bag()
    for tail, specs in ((False, crest_specs()), (True, tail_specs())):
        for f in specs:
            v, fc, a = plume_blade(f, high, tail)
            bag.add(v, fc, {**a, 'cu': a['fu']}, pk=3 if tail else 2, fid=f['seed'], cid=f['cid'],
                    side=float(np.sign(f['az'])) if f['az'] else 0.0, rx=f['pts'][0][0], ry=f['pts'][0][1], rz=f['pts'][0][2])
    return bag.object(f'{"hi" if high else "lo"}_plumes', 'plumes')


# ----------------------------------------------------------------------------- the beak
def beak_axis():
    """The gape line from the corner to the tip, the beak's up direction and its length."""
    g, t = np.array(F.GAPE), np.array(F.BEAK_TIP)
    ax = unit(t - g)
    up = unit(np.array((0.0, 0.0, 1.0)) - ax * ax[2])
    return g, ax, up, float(np.linalg.norm(t - g))


def mandible(high: bool, upper: bool) -> tuple[np.ndarray, list, dict]:
    """One half of the dagger beak: a lofted half-lens above (or below) the gape line from 4 cm inside the face to the
    tip; flat where the halves meet. The upper is 4.4 cm deep at the face, the lower 2.6 cm; both taper to a point."""
    g, ax, up, L = beak_axis()
    side = np.cross(ax, up)                                  # +X for this beak (it points -Y)
    nu, na = (40, 18) if high else (16, 8)
    s0 = -0.045
    s = np.linspace(s0, L * (1.0 if upper else 0.965), nu)
    us = (s - s0) / (L - s0)
    k = np.clip(s / L, 0.0, 1.0)
    depth = (0.044 if upper else 0.026) * (1.0 - k) ** (0.95 if upper else 1.05) + 0.0012
    width = 0.024 * (1.0 - k) ** 0.85 + 0.0012
    # the culmen curves down a little near the tip (a dagger, not a hook)
    drop = -0.006 * smooth(0.6, 1.0, k)
    ang = np.linspace(0.0, math.pi, na)
    rings, ins = [], []
    sg = 1.0 if upper else -1.0
    for i in range(nu):
        c = g + ax * s[i] + up * drop[i]
        a = ang if upper else ang[::-1]
        # the half lens: x = width cos a, h = depth sin a (squared sides: a flatter, blade-like section)
        h = depth[i] * np.sin(a) ** 0.8
        x = width[i] * np.sign(np.cos(a)) * np.abs(np.cos(a)) ** 0.9
        arc = c[None] + side[None] * x[:, None] + up[None] * (sg * h)[:, None]
        # the flat inner face back across (a few points, so the mouth's inside bakes)
        fl = np.linspace(1.0, -1.0, 5)[1:-1] * (-width[i] if upper else width[i])
        flat = c[None] + side[None] * fl[:, None] + up[None] * (sg * 0.0004)
        rings.append(np.vstack([arc, flat]))
        ins.append(np.concatenate([np.zeros(na), np.ones(len(fl))]))
    m = len(rings[0])
    verts = np.vstack(rings)
    faces = []
    for i in range(nu - 1):
        for j in range(m):
            j1 = (j + 1) % m
            faces.append((i * m + j, (i + 1) * m + j, (i + 1) * m + j1, i * m + j1))
    c0, c1 = len(verts), len(verts) + 1
    verts = np.vstack([verts, (g + ax * s[0])[None], (g + ax * (s[-1] + 0.0015) + up * drop[-1])[None]])
    last = (nu - 1) * m
    for j in range(m):
        j1 = (j + 1) % m
        faces.append((c0, j, j1))
        faces.append((c1, last + j1, last + j))
    n = len(verts)
    attrs = {'bk_in': np.concatenate([np.tile(ins[0], nu), [0.0, 0.0]]),
             'bk_u': np.concatenate([np.repeat(us, m), [0.0, 1.0]]),
             'fv': np.concatenate([np.tile(np.concatenate([np.cos(ang), np.zeros(m - na)]), nu), [0.0, 0.0]])}
    return verts, faces, attrs


def beak(high: bool) -> list[bpy.types.Object]:
    out = []
    for upper in (True, False):
        bag = Bag()
        v, fc, a = mandible(high, upper)
        bag.add(v, fc, a, pk=4 if upper else 5)
        ob = bag.object(f'{"hi" if high else "lo"}_beak{"" if upper else "_lower"}', 'beak')
        out.append(ob)
    return out


def build(high: bool, quick: bool) -> list[bpy.types.Object]:
    return [wings(high), plumes(high), bib(high)] + beak(high)


# ----------------------------------------------------------------------------- weights
def chain_u_weights(u: np.ndarray, bones: list[str], parent: str) -> dict[str, np.ndarray]:
    """Weights along a plume by its own share u (0 root .. 1 tip) over the chain's bones: the root on the parent, then
    each bone's centre fully its own, blended linearly between."""
    n = len(bones)
    cen = (np.arange(n) + 0.5) / n
    w = {b: np.zeros(len(u)) for b in bones}
    w[parent] = np.zeros(len(u))
    xs = np.concatenate([[0.0], cen])
    names = [parent] + bones
    uu = np.clip(u, 0.0, 1.0)
    for i in range(len(names)):
        col = np.zeros(len(names))
        col[i] = 1.0
        w[names[i]] = w[names[i]] + np.interp(uu, xs, col)
    return w


def weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    pk = np.round(attr('pk')).astype(int)
    regs = []
    # the beak: rigid
    regs.append(U.rigid(pk == 4, 'head'))
    regs.append(U.rigid(pk == 5, 'jaw'))
    # the wing feathers: each rides its root's bone weights (rigid per blade); the primaries their finger
    side = attr('side')
    fb = attr('fbone')
    root = np.stack([attr('rx'), attr('ry'), attr('rz')], axis=1)
    for s in (1, -1):
        nm = U.wing_bone_names(WING, s)
        q = U.wing_points(WING, s)
        m = (pk == 1) & (np.sign(side) == s) & (fb < 0.5)
        if m.any():
            segs = [(nm[0], q['shoulder'], q['elbow']), (nm[1], q['elbow'], q['wrist'])]
            regs.append((m, U.segment_weights(root[m], segs, power=8.0)))
        mh = (pk == 1) & (np.sign(side) == s) & (fb > 0.5)
        if mh.any():
            t = np.clip(fb[mh] - 1.0, 0.0, 1.0)
            regs.append((mh, {nm[2]: np.clip(2 * t - 1, 0, 1), nm[3]: 1.0 - np.abs(2 * t - 1), nm[4]: np.clip(1 - 2 * t, 0, 1)}))
    # the bib and the trousers (round 3): rigid per blade on the neck, the chest or the hips at their root
    m7 = pk == 7
    if m7.any():
        hip, ch = np.array(F.HIP), np.array(F.CHEST)
        mid = 0.5 * (hip + ch)
        nk = [np.array(p) for p in F.NECK]
        regs.append((m7, U.segment_weights(root[m7], [('neck.1', nk[0], nk[1]), ('neck.2', nk[1], nk[2]), ('chest', mid, ch),
                                                      ('hips', hip, mid)], power=8.0)))
    # the scapulars: rigid per blade on the body's chest / hips at their root
    m6 = pk == 6
    if m6.any():
        hip, ch = np.array(F.HIP), np.array(F.CHEST)
        mid = 0.5 * (hip + ch)
        regs.append((m6, U.segment_weights(root[m6], [('chest', mid, ch), ('hips', hip, mid)], power=8.0)))
    # the plumes: along their own length over their chain's bones
    cid = np.round(attr('cid')).astype(int)
    cu = attr('cu')
    for i, nm in enumerate(CHAIN_NAMES):
        m = (pk >= 2) & (pk <= 3) & (cid == i)
        if m.any():
            bones = [f'{nm}.{k + 1}' for k in range(3)]
            regs.append((m, chain_u_weights(cu[m], bones, 'head' if i < 3 else 'hips')))
    return regs
