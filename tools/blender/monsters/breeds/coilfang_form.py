"""Coilfang at Art 2.1 Ultra: the form (chatgpt/monsters/23-coilfang; CONTENT entry 9; RECIPE.md "Serpent plan").

The centre line from the back of the head to the tail's tip (a near-vertical neck rising from the front of a loose S
laid on the ground, the tail's tip curling up; 2-turnaround side, top and front, 1-hero), the body's thickness along
it, the head's volumes, the eyes' frames and the tube coordinates every other module reads: s (metres along the centre
line from the back of the head), phi (radians round it: 0 on the spine's top, +pi/2 on the monster's left flank,
+-pi on the belly) and the distance from the axis.

Metres; the monster faces -Y, Z is up, +X is its left. Size: HEIGHT_UNITS 150 (coiled, 1 x Puddlepup's height): 0.986 m
to the crest's top; about 3.3 m from the snout to the tail's tip along the body (the card: 3.5 x Puddlepup's length;
the turnaround's path agrees).
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

from lib.mesh import Part
from lib.surface import smooth, v3

RMAX = 0.135                # the body's radius at its thickest (the coil-sit's spacing and the ground guard)
BELLY_K = 0.88              # the belly's flattening: the bottom sits this share of the radius below the axis
SIDE_K = 1.05               # the flanks a little wider than tall
STEP = 0.003                # the dense centre line's spacing (metres)

# the centre line's control points, head -> tail tip; z None = lying on the ground (the axis at BELLY_K x the radius)
# (the neck leans a little forward all the way up, so every neck bone's heading is the same: a vertical bone's heading
# is undefined and flipped between neighbours, which twisted the neck in the coil-sit)
# (polish: the neck turns into the body over a radius wider than the body is thick; the tighter turn folded the tube
# coordinates on the bend's inside and stretched its scales into streaks)
CTRL = [(0.0, -0.648, 0.555), (0.0, -0.64, 0.45), (0.0, -0.622, 0.35), (0.0, -0.585, 0.262), (-0.015, -0.525, 0.195),
        (-0.06, -0.45, None), (-0.13, -0.37, None), (-0.25, -0.27, None), (-0.33, -0.07, None), (-0.31, 0.14, None), (-0.17, 0.31, None),
        (0.05, 0.4, None), (0.27, 0.5, None), (0.42, 0.67, None), (0.44, 0.86, None), (0.33, 1.0, None),
        (0.2, 1.06, None), (0.07, 1.085, 0.055), (-0.04, 1.075, 0.11), (-0.1, 1.03, 0.17)]

# the radius along the body (share of the length from the back of the head -> metres)
# (round 2: the neck flares wide into the chest at its base; the last 30% tapers smoothly to a fine point, one tube)
R_TAB = [(0.0, 0.09), (0.06, 0.093), (0.12, 0.112), (0.17, 0.136), (0.22, 0.146), (0.32, 0.14), (0.5, 0.134), (0.6, 0.122),
         (0.66, 0.106), (0.72, 0.086), (0.78, 0.064), (0.84, 0.045), (0.89, 0.031), (0.935, 0.02), (0.97, 0.012), (1.0, 0.004)]

# the rig's spine: the 4 neck bones' lengths (from the back of the head down), the hips bone, then the tail's bones
NECK_LENGTHS = (0.135, 0.14, 0.145, 0.15)
HIPS_LENGTH = 0.16
TAIL_BONES = 15


# ============================================================================= small maths
def catmull(pts, n_per: int = 40) -> np.ndarray:
    P = [v3(p) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n_per):
            t = k / n_per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def catmull1(xs, ys, x: np.ndarray) -> np.ndarray:
    """A smooth 1-D curve through (xs, ys) (Catmull-Rom on uneven knots, clamped ends)."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    x = np.clip(np.asarray(x, float), xs[0], xs[-1])
    i = np.clip(np.searchsorted(xs, x, side='right') - 1, 0, len(xs) - 2)
    x0, x1 = xs[i], xs[i + 1]
    y0, y1 = ys[i], ys[i + 1]
    m = np.gradient(ys, xs)
    t = (x - x0) / np.maximum(x1 - x0, 1e-9)
    h = x1 - x0
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * h * m[i + 1]


def arc(c: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])


def resample(c: np.ndarray, step: float) -> np.ndarray:
    s = arc(c)
    n = max(2, int(round(s[-1] / step)) + 1)
    t = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(t, s, c[:, k]) for k in range(3)], axis=1)


def unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def ell_sdf(p: np.ndarray, c, r) -> np.ndarray:
    """An ellipsoid's approximate signed distance (metres; < 0 inside)."""
    c, r = v3(c), v3(r)
    q = (p - c) / r
    k = np.linalg.norm(q, axis=1)
    return (k - 1.0) * float(np.min(r))


# ============================================================================= the centre line
def radius_at_share(u) -> np.ndarray:
    xs, ys = zip(*R_TAB)
    return catmull1(xs, ys, u)


def _build_curve():
    pts = [list(p) for p in CTRL]
    for p in pts:
        if p[2] is None:
            p[2] = 0.1
    for _ in range(4):
        c = resample(catmull(pts), STEP)
        s = arc(c)
        tot = s[-1]
        for k, q in enumerate(CTRL):
            if q[2] is None:
                i = int(np.argmin(np.linalg.norm(c[:, :2] - np.array(q[:2]), axis=1)))
                pts[k][2] = float(BELLY_K * radius_at_share(s[i] / tot)) + 0.001
    c = resample(catmull(pts), STEP)
    return c, arc(c)


CURVE, CUM = _build_curve()
S_TOT = float(CUM[-1])
TAN = np.gradient(CURVE, axis=0)
TAN /= np.linalg.norm(TAN, axis=1, keepdims=True)


def radius(s) -> np.ndarray:
    return radius_at_share(np.asarray(s, float) / S_TOT)


def _frames():
    """Dorsal directions by parallel transport from the body's middle (lying flat there: straight up) both ways, so the
    spine's top runs up the back of the neck and along the top of the S; left = T x D (T toward the tail)."""
    n = len(CURVE)
    D = np.zeros((n, 3))
    k0 = int(np.argmin(np.abs(CUM - 0.5 * S_TOT)))
    up = np.array((0.0, 0.0, 1.0))
    D[k0] = unit(up - TAN[k0] * (up @ TAN[k0]))
    for k in range(k0 + 1, n):
        d = D[k - 1] - TAN[k] * (D[k - 1] @ TAN[k])
        D[k] = d / np.linalg.norm(d)
    for k in range(k0 - 1, -1, -1):
        d = D[k + 1] - TAN[k] * (D[k + 1] @ TAN[k])
        D[k] = d / np.linalg.norm(d)
    L = np.cross(TAN, D)
    return D, L


DORSAL, LEFT = _frames()
_KD = KDTree(len(CURVE))
for _i, _p in enumerate(CURVE):
    _KD.insert(Vector(_p), _i)
_KD.balance()


def point_at(s) -> np.ndarray:
    s = np.clip(np.atleast_1d(np.asarray(s, float)), 0.0, S_TOT)
    return np.stack([np.interp(s, CUM, CURVE[:, k]) for k in range(3)], axis=1)


def tube_coords(co: np.ndarray) -> dict:
    """Each point against the centre line: s (metres from the back of the head; may run below 0 in front of the curve's
    start), phi (0 the spine's top, + toward the monster's left, +-pi the belly), rho (the distance from the axis), the
    unit radial direction, and the frame there (T toward the tail, D dorsal, L left)."""
    co = np.asarray(co, float)
    idx = np.fromiter((_KD.find(Vector(p))[1] for p in co), dtype=np.int64, count=len(co))
    T, D, L = TAN[idx], DORSAL[idx], LEFT[idx]
    d = co - CURVE[idx]
    along = (d * T).sum(axis=1)
    s = CUM[idx] + along
    perp = d - T * along[:, None]
    rho = np.linalg.norm(perp, axis=1)
    radial = perp / np.maximum(rho, 1e-9)[:, None]
    phi = np.arctan2((perp * L).sum(axis=1), (perp * D).sum(axis=1))
    return {'s': s, 'phi': phi, 'rho': rho, 'radial': radial, 'T': T, 'D': D, 'L': L, 'idx': idx}


# ============================================================================= the rig's spine
def spine_lengths() -> list[float]:
    rest = S_TOT - sum(NECK_LENGTHS) - HIPS_LENGTH
    w = np.linspace(1.0, 0.5, TAIL_BONES)
    return list(NECK_LENGTHS) + [HIPS_LENGTH] + list(w / w.sum() * rest)


def spine_points() -> list[tuple[float, float, float]]:
    s = np.concatenate([[0.0], np.cumsum(spine_lengths())])
    s[-1] = S_TOT
    return [tuple(float(v) for v in p) for p in point_at(s)]


SPINE = spine_points()
ANCHOR = len(NECK_LENGTHS) + 1            # Q5: the hips bone starts here (on the ground, the body's first curve)
SPINE_S = np.concatenate([[0.0], np.cumsum(spine_lengths())])


# ============================================================================= the head
HEAD_C = (0.0, -0.76, 0.64)
HEAD_R = 0.16
HEAD_TIP = (0.0, -0.945, 0.6)

# round 3: the head is a long smooth viper wedge, about 1.5 times as long as tall (4-details panel 1, 2-turnaround side):
# the back narrows into the neck with no step or ring (the variant's back view), the cheeks are widest below and behind
# the eyes, the skull's top is flat between and behind the eyes, the snout long and rounded. Profiles along y (back ->
# snout): the half width, the top and the underside of the upper head; the lower jaw tucked under it, blending into the
# throat at the back.
_HY = [-0.6, -0.64, -0.68, -0.72, -0.76, -0.8, -0.84, -0.87, -0.89]
_HW = [0.096, 0.13, 0.155, 0.162, 0.152, 0.13, 0.104, 0.08, 0.062]
_HT = [0.69, 0.728, 0.748, 0.752, 0.75, 0.735, 0.704, 0.676, 0.655]
_HB = [0.485, 0.49, 0.495, 0.5, 0.506, 0.513, 0.521, 0.53, 0.542]
_JY = [-0.64, -0.7, -0.76, -0.81, -0.85, -0.87]
_JW = [0.075, 0.08, 0.074, 0.062, 0.05, 0.04]
_JZ = [0.492, 0.5, 0.507, 0.512, 0.516, 0.52]
_JR = [0.048, 0.04, 0.033, 0.028, 0.024, 0.02]


def _wedge(y: float) -> tuple:
    yy = -np.asarray(y)
    return (float(np.interp(yy, [-v for v in _HY], _HW)), float(np.interp(yy, [-v for v in _HY], _HT)),
            float(np.interp(yy, [-v for v in _HY], _HB)))


HEAD_SECTIONS = []
for _y in np.linspace(_HY[0], _HY[-1], 48):
    _w, _top, _bot = _wedge(_y)
    HEAD_SECTIONS.append(((0.0, float(_y), float(0.5 * (_top + _bot))), (_w, 0.055, float(0.5 * (_top - _bot)))))
JAW_SECTIONS = []
for _y in np.linspace(_JY[0], _JY[-1], 28):
    yy = -_y
    JAW_SECTIONS.append(((0.0, float(_y), float(np.interp(yy, [-v for v in _JY], _JZ))),
                         (float(np.interp(yy, [-v for v in _JY], _JW)), 0.05, float(np.interp(yy, [-v for v in _JY], _JR)))))
THROAT = ((0.0, -0.665, 0.47), (0.118, 0.1, 0.09))     # round 3: the neck flares up into the jaw
HEAD_PARTS = tuple(HEAD_SECTIONS) + tuple(JAW_SECTIONS) + (THROAT,)
CRANIUM = HEAD_SECTIONS[12]

# the eyes: big glossy lenses on the front of the head's sides, looking forward and out (3-faces neutral)
EYE_X, EYE_Z = 0.1, 0.703          # round 2-3: big and high on the head, on its front
EYE_R = 0.049                       # the lens's half width (about 0.1 m across: 2-turnaround front)
EYE_SHAPE = (1.0, 1.1)
EYE_DEPTH = (0.48, 0.16)            # the dome's depth and how far its base sits behind the centre (x EYE_R)
EYE_OUT = 0.5                       # how far the look turns out (x across per 1 forward)


def head_sdf(co: np.ndarray) -> np.ndarray:
    return np.min(np.stack([ell_sdf(co, c, r) for c, r in HEAD_PARTS], axis=1), axis=1)


def _front_y(c, r, x: float, z: float) -> float:
    k = 1.0 - ((x - c[0]) / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
    return c[1] - r[1] * math.sqrt(k) if k > 0 else 9.0


def _eye_centre(s: int) -> np.ndarray:
    y = min(_front_y(c, r, EYE_X, EYE_Z) for c, r in HEAD_SECTIONS)
    return np.array((EYE_X * s, y - 0.004, EYE_Z))


EYE_C = {s: _eye_centre(s) for s in (1, -1)}


def _head_normal(p) -> np.ndarray:
    p = v3(p)
    e = 0.002
    g = [float(head_sdf(np.array([p + d]))[0] - head_sdf(np.array([p - d]))[0]) for d in np.eye(3) * e]
    return unit(g)


def eye_frame(s: int):
    """The eye looks half along the head's own surface (the wedge's side) and half forward, a little up, so the lens
    sits on the skin evenly all round."""
    c = EYE_C[s]
    look = unit(0.3 * _head_normal(c) + 0.7 * unit((EYE_OUT * s, -1.0, 0.0)) + np.array((0.0, 0.0, 0.14)))
    xax = unit(np.cross(np.array((0.0, 0.0, 1.0)), look))
    yax = unit(np.cross(look, xax))
    return c, xax, yax, look


def eye_coords(co: np.ndarray, s: int):
    """(rx, ry) in lens units and ze metres along the look from the lens's base."""
    c, xax, yax, look = eye_frame(s)
    q = co - (c - look * (EYE_R * EYE_DEPTH[1]))
    return (q @ xax) / (EYE_R * EYE_SHAPE[0]), (q @ yax) / (EYE_R * EYE_SHAPE[1]), q @ look


def eye_d(co: np.ndarray) -> np.ndarray:
    return np.minimum(np.linalg.norm(co - EYE_C[1], axis=1), np.linalg.norm(co - EYE_C[-1], axis=1))


def _euler_xyz(m: np.ndarray) -> tuple[float, float, float]:
    sy = -m[2, 0]
    y = math.asin(max(-1.0, min(1.0, sy)))
    x = math.atan2(m[2, 1], m[2, 2])
    z = math.atan2(m[1, 0], m[0, 0])
    return (math.degrees(x), math.degrees(y), math.degrees(z))


def eye_parts() -> list[Part]:
    """Each eyeball under its lens: a shallow dome only 3 mm proud of the face (round 2: the closed lid a blink shows lies
    nearly flush, never a goggle)."""
    out = []
    for tag, s in (('L', 1), ('R', -1)):
        c, xax, yax, look = eye_frame(s)
        e = _euler_xyz(np.stack([xax, yax, look], axis=1))
        c0 = c - look * (EYE_R * EYE_DEPTH[1])
        out.append(Part(f'eyeball{tag}', 'sphere', loc=tuple(c0), radius=1.0, rot=e,
                        scale=(EYE_R * EYE_SHAPE[0] - 0.003, EYE_R * EYE_SHAPE[1] - 0.003, EYE_R * 0.22)))
    return out


# ============================================================================= the parts
PART_STEP = 0.024


def body_parts() -> list[Part]:
    """The body as short tapered tubes along the centre line (the voxel union smooths them into one skin)."""
    n = max(2, int(math.ceil(S_TOT / PART_STEP)))
    s = np.linspace(0.0, S_TOT, n + 1)
    p = point_at(s)
    r = radius(s)
    return [Part(f'seg{i}', 'tube', loc=tuple(p[i]), to=tuple(p[i + 1]), radius=float(r[i]), r2=float(r[i + 1])) for i in range(n)]


def head_parts() -> list[Part]:
    ps = [Part(f'head{k}', 'sphere', loc=c, radius=1.0, scale=r) for k, (c, r) in enumerate(HEAD_PARTS)]
    return ps + eye_parts()


def all_parts() -> list[Part]:
    return body_parts() + head_parts()


# ============================================================================= the head's and the body's masks
def head_w(co: np.ndarray, tc: dict | None = None) -> np.ndarray:
    """0..1: the head (its volumes, softly) against the tube: 1 well inside the head's volumes' reach."""
    return smooth(0.03, -0.004, head_sdf(co))


def tube_w(co: np.ndarray, tc: dict) -> np.ndarray:
    """0..1: where the tube coordinates hold (the body and the neck), fading out into the head."""
    return (1.0 - head_w(co)) * smooth(0.02, 0.07, tc['s'])


def reshape(co: np.ndarray, tc: dict, w: np.ndarray) -> np.ndarray:
    """The body's section: the belly flattened (its bottom BELLY_K x the radius below the axis) and the flanks widened
    (SIDE_K), by moving each point in its section; `w` (0..1) fades it out into the head."""
    perp = tc['radial'] * tc['rho'][:, None]
    dD = (perp * tc['D']).sum(axis=1)
    dL = (perp * tc['L']).sum(axis=1)
    r = np.maximum(radius(np.clip(tc['s'], 0.0, S_TOT)), 1e-3)
    down = smooth(0.0, -1.0, dD / r)
    nD = dD * (1.0 - (1.0 - BELLY_K) * down ** 1.5)
    nL = dL * (1.0 + (SIDE_K - 1.0) * (1.0 - np.abs(np.clip(dD / r, -1, 1))))
    new = co + (tc['D'] * (nD - dD)[:, None] + tc['L'] * (nL - dL)[:, None]) * w[:, None]
    return new
