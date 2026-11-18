"""Aurelwyrm at Art 2.1 Ultra: the form (chatgpt/monsters/24-aurelwyrm; CONTENT entry 20; RECIPE.md "Serpent plan").

The centre line from the back of the head to the tail's tip (a floating dragon: the head raised on a neck that comes
down and back into a deep chest, then the body in a gentle S in both views, a low chest, a hump two thirds back and a
low dip before the tail, which lifts a little at its tip; 2-turnaround side, top and front, 1-hero), the body's
thickness along it, the head's volumes (a domed skull, round cheeks, a short soft muzzle, small pointed ears), the eyes'
frames and the tube coordinates every other module reads: s (metres along the centre line from the back of the head),
phi (radians round it: 0 on the spine's top, +pi/2 on the monster's left flank, +-pi on the belly) and the distance
from the axis.

Metres; the monster faces -Y, Z is up, +X is its left. Size: HEIGHT_UNITS 225 (the card: its raised head floats about
1.5 x Puddlepup's height above the ground) -> 1.479 m to the top of the skull; about 4.3 m from the snout to the tail's
tip along the body (the card: 4.5 x Puddlepup's length). It floats at rest: nothing touches the ground.
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

from lib.mesh import Part
from lib.surface import smooth, v3

RMAX = 0.17                 # the body's radius at its thickest (the chest)
BELLY_K = 0.93              # the belly a touch flatter: its bottom sits this share of the radius below the axis
SIDE_K = 1.04               # the flanks a little wider than tall
STEP = 0.003                # the dense centre line's spacing (metres)

# the centre line's control points, the back of the head -> the tail's tip (the neck leans forward all the way up, so
# no neck bone is vertical; the chest is the anchor, CTRL[ANCHOR_CTRL])
HDZ = 0.037                 # the head (and everything on it) raised this much over its first layout: the size rule
CTRL = [(0.0, -0.95, 1.17 + HDZ), (0.0, -0.865, 1.035 + 0.75 * HDZ), (0.0, -0.785, 0.9 + 0.5 * HDZ),
        (0.0, -0.71, 0.765 + 0.25 * HDZ), (0.004, -0.635, 0.64),
        (0.012, -0.555, 0.53),
        (0.04, -0.456, 0.445), (0.12, -0.298, 0.4), (0.25, -0.11, 0.43), (0.33, 0.098, 0.53), (0.31, 0.305, 0.68),
        (0.17, 0.503, 0.82), (-0.04, 0.7, 0.88), (-0.22, 0.872, 0.82), (-0.3, 1.034, 0.66), (-0.25, 1.178, 0.48),
        (-0.1, 1.34, 0.34), (0.07, 1.52, 0.27), (0.17, 1.708, 0.28), (0.2, 1.87, 0.34)]
ANCHOR_CTRL = 5

# the radius along the body (share of the length from the back of the head -> metres): the neck slimmer under the head,
# the deep chest, the body tapering from its middle to a fine tail
R_TAB = [(0.0, 0.1), (0.05, 0.11), (0.11, 0.124), (0.17, 0.155), (0.21, 0.17), (0.27, 0.166), (0.4, 0.156),
         (0.52, 0.146), (0.62, 0.134), (0.71, 0.118), (0.79, 0.1), (0.86, 0.082), (0.91, 0.065), (0.95, 0.048),
         (0.98, 0.032), (1.0, 0.012)]

NECK_BONES = 4
HIPS_LENGTH = 0.2
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
    """A smooth 1-D curve through (xs, ys) (cubic Hermite on uneven knots, clamped ends)."""
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


def smin(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


# ============================================================================= the centre line
def radius_at_share(u) -> np.ndarray:
    xs, ys = zip(*R_TAB)
    return catmull1(xs, ys, u)


CURVE = resample(catmull(CTRL), STEP)
CUM = arc(CURVE)
S_TOT = float(CUM[-1])
TAN = np.gradient(CURVE, axis=0)
TAN /= np.linalg.norm(TAN, axis=1, keepdims=True)


def radius(s) -> np.ndarray:
    return radius_at_share(np.asarray(s, float) / S_TOT)


def _frames():
    """Dorsal directions: straight up, square to the centre line, all along it (the back of the neck, the top of the S);
    left = T x D (T toward the tail). Build 2 transported them along the line instead, which turned through the S's
    side-to-side bends, so the cream belly crept onto the tail's top. The line is never near vertical (the neck leans
    30 degrees), so up always projects cleanly."""
    up = np.array((0.0, 0.0, 1.0))
    D = up[None] - TAN * (TAN @ up)[:, None]
    D /= np.linalg.norm(D, axis=1, keepdims=True)
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


def frame_at(s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(point, T toward the tail, D dorsal, L left) at s."""
    i = int(np.clip(np.searchsorted(CUM, s), 0, len(CUM) - 1))
    return point_at(s)[0], TAN[i], DORSAL[i], LEFT[i]


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
S_NECK = float(CUM[int(np.argmin(np.linalg.norm(CURVE - v3(CTRL[ANCHOR_CTRL]), axis=1)))])
NECK_LENGTHS = tuple([S_NECK / NECK_BONES] * NECK_BONES)


def spine_lengths() -> list[float]:
    rest = S_TOT - sum(NECK_LENGTHS) - HIPS_LENGTH
    w = np.linspace(1.0, 0.55, TAIL_BONES)
    return list(NECK_LENGTHS) + [HIPS_LENGTH] + list(w / w.sum() * rest)


def spine_points() -> list[tuple[float, float, float]]:
    s = np.concatenate([[0.0], np.cumsum(spine_lengths())])
    s[-1] = S_TOT
    return [tuple(float(v) for v in p) for p in point_at(s)]


SPINE = spine_points()
ANCHOR = NECK_BONES + 1                   # the hips bone starts here (the chest's base, the body's first curve)
SPINE_S = np.concatenate([[0.0], np.cumsum(spine_lengths())])


# ============================================================================= the head
# a kind, regal face (1-hero, 3-faces, 4-details panel 1): a domed skull, slim cheeks, a longer fox-like muzzle with a
# small nose pad, a small chin; the back of the skull flows into the neck under the mane (round 2: the puffed cheeks and
# the short round muzzle read as a pup)
HEAD_C = (0.0, -1.1, 1.28)
HEAD_R = 0.15
HEAD_TIP = (0.0, -1.33, 1.24)
HEAD_PARTS = (
    ((0.0, -1.06, 1.3), (0.122, 0.135, 0.122)),          # the cranium's dome
    ((0.0, -1.135, 1.325), (0.098, 0.088, 0.088)),       # the brow
    # (round 3: slimmer cheeks, a muzzle 15% shorter tapering to a small, slightly upturned tip, a smaller chin)
    ((0.05, -1.085, 1.242), (0.058, 0.085, 0.062)),      # the left cheek
    ((-0.05, -1.085, 1.242), (0.058, 0.085, 0.062)),     # the right cheek
    ((0.0, -1.22, 1.224), (0.054, 0.1, 0.052)),          # the muzzle
    ((0.0, -1.22, 1.262), (0.038, 0.1, 0.038)),          # the bridge of the nose
    ((0.0, -1.3, 1.248), (0.022, 0.024, 0.022)),         # the nose's tip, a little up
    ((0.0, -1.185, 1.172), (0.046, 0.095, 0.032)),       # the chin and the lower jaw
    ((0.0, -0.99, 1.22), (0.1, 0.09, 0.11)),             # the back of the head
    ((0.0, -0.995, 1.13), (0.075, 0.08, 0.06)),          # the throat under the jaw (round 3: no second bulge)
)
HEAD_PARTS = tuple(((c[0], c[1], c[2] + HDZ), r) for c, r in HEAD_PARTS)
HEAD_C = (HEAD_C[0], HEAD_C[1], HEAD_C[2] + HDZ)
HEAD_TIP = (HEAD_TIP[0], HEAD_TIP[1], HEAD_TIP[2] + HDZ)
HEAD_SECTIONS = HEAD_PARTS[:8]

# the ears: small pointed leaves rising out and back from behind the eyes (every picture; the card doesn't name them:
# kept small, as the pictures show them)
EAR_ROOT = (0.094, -1.028, 1.37 + HDZ)            # (polish: the root sunk into the skull)
EAR_DIR = (0.6, 0.38, 0.7)
EAR_LEN, EAR_W, EAR_T = 0.11, 0.042, 0.018          # round 2: longer and pointed

# the eyes: big glossy lenses high on the face's front, looking forward and a little out (3-faces neutral)
EYE_X, EYE_Z = 0.07, 1.318 + HDZ
# round 2: almond eyes set into the face (round bulging orbs read as a surprised pup): wider than tall, a flatter dome
EYE_R = 0.036                       # x EYE_SHAPE: about 8 cm wide, 5.6 cm tall (3-faces neutral, 4-details panel 2)
EYE_SHAPE = (1.1, 0.86)              # round 3: wider open (kind, not sleepy)
EYE_DEPTH = (0.36, 0.2)             # the dome's depth and how far its base sits behind the centre (x EYE_R)
EYE_ALMOND = 0.22                   # the lens narrows toward its corners by this share (an almond outline)
EYE_TILT = 0.12                     # its outer corner lifted (x the lens's half height)
EYE_OUT = 0.42                      # how far the look turns out (x across per 1 forward)


def head_sdf(co: np.ndarray) -> np.ndarray:
    return np.min(np.stack([ell_sdf(co, c, r) for c, r in HEAD_PARTS], axis=1), axis=1)


def _front_y(c, r, x: float, z: float) -> float:
    k = 1.0 - ((x - c[0]) / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
    return c[1] - r[1] * math.sqrt(k) if k > 0 else 9.0


def _eye_centre(s: int) -> np.ndarray:
    y = min(_front_y(c, r, EYE_X * s, EYE_Z) for c, r in HEAD_SECTIONS)
    return np.array((EYE_X * s, y - 0.003, EYE_Z))


EYE_C = {s: _eye_centre(s) for s in (1, -1)}


def _head_normal(p) -> np.ndarray:
    p = v3(p)
    e = 0.002
    g = [float(head_sdf(np.array([p + d]))[0] - head_sdf(np.array([p - d]))[0]) for d in np.eye(3) * e]
    return unit(g)


def eye_frame(s: int):
    """The eye looks half along the head's own surface and half forward, a little up, so the lens sits on the skin
    evenly all round."""
    c = EYE_C[s]
    look = unit(0.35 * _head_normal(c) + 0.65 * unit((EYE_OUT * s, -1.0, 0.0)) + np.array((0.0, 0.0, 0.1)))
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
    """Each eyeball under its lens: a shallow dome only 3 mm proud of the face (the closed lid a blink shows lies nearly
    flush)."""
    out = []
    for tag, s in (('L', 1), ('R', -1)):
        c, xax, yax, look = eye_frame(s)
        e = _euler_xyz(np.stack([xax, yax, look], axis=1))
        c0 = c - look * (EYE_R * EYE_DEPTH[1])
        out.append(Part(f'eyeball{tag}', 'sphere', loc=tuple(c0), radius=1.0, rot=e,
                        scale=(EYE_R * EYE_SHAPE[0] - 0.004, EYE_R * EYE_SHAPE[1] * 0.8 - 0.003, EYE_R * 0.18)))
    return out


def ear_frame(s: int):
    """(root, along, across, normal) of the ear on side s: it rises out and back, its open face toward the front."""
    root = np.array((EAR_ROOT[0] * s, EAR_ROOT[1], EAR_ROOT[2]))
    d = unit((EAR_DIR[0] * s, EAR_DIR[1], EAR_DIR[2]))
    nrm = unit(np.array((0.35 * s, -1.0, 0.1)) - d * float(d @ unit((0.35 * s, -1.0, 0.1))))
    across = unit(np.cross(nrm, d))
    return root, d, across, nrm


def ear_parts() -> list[Part]:
    out = []
    for tag, s in (('L', 1), ('R', -1)):
        root, d, across, nrm = ear_frame(s)
        e = _euler_xyz(np.stack([across, d, nrm], axis=1))
        # (polish) the slab starts 2 cm inside the skull: its thin base met the skin in a pinch that baked two dark specks
        c = root + d * (0.5 * EAR_LEN - 0.01)
        out.append(Part(f'ear{tag}', 'fin', loc=tuple(c), radius=1.0, rot=e, scale=(EAR_W, (EAR_LEN + 0.02) * 0.5, EAR_T), taper=1.0))
    return out


def ear_w(co: np.ndarray) -> np.ndarray:
    """0..1: on an ear (its inner, front face is the pink lining)."""
    out = np.zeros(len(co))
    for s in (1, -1):
        root, d, across, nrm = ear_frame(s)
        q = co - root
        u = q @ d
        out = np.maximum(out, smooth(-0.01, 0.012, u) * smooth(EAR_LEN + 0.02, EAR_LEN - 0.01, u)
                         * smooth(0.03, 0.02, np.abs(q @ nrm)) * smooth(EAR_W + 0.012, EAR_W, np.abs(q @ across)))
    return out


def ear_inner(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """0..1: the ear's front face (the pink lining), away from its rim."""
    out = np.zeros(len(co))
    for s in (1, -1):
        root, d, across, nrm = ear_frame(s)
        q = co - root
        u = np.clip((q @ d) / EAR_LEN, 0.0, 1.0)
        half = EAR_W * (1.0 - 0.92 * u ** 1.6)
        rim = smooth(0.95, 0.6, np.abs(q @ across) / np.maximum(half, 1e-4))
        front = smooth(0.2, 0.6, vn @ nrm)
        out = np.maximum(out, rim * front * smooth(0.08, 0.2, u) * smooth(0.95, 0.75, u))
    return out * ear_w(co)


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
    return ps + ear_parts() + eye_parts()


def all_parts() -> list[Part]:
    return body_parts() + head_parts()


# ============================================================================= the head's and the body's masks
def head_w(co: np.ndarray, tc: dict | None = None) -> np.ndarray:
    """0..1: the head (its volumes and the ears, softly) against the tube: 1 well inside the head's volumes' reach."""
    return np.maximum(smooth(0.03, -0.004, head_sdf(co)), ear_w(co))


def tube_w(co: np.ndarray, tc: dict) -> np.ndarray:
    """0..1: where the tube coordinates hold (the body and the neck), fading out into the head."""
    return (1.0 - head_w(co)) * smooth(-0.06, 0.0, tc['s'])


def reshape(co: np.ndarray, tc: dict, w: np.ndarray) -> np.ndarray:
    """The body's section: the belly a touch flattened and the flanks a touch wider, by moving each point in its section;
    `w` (0..1) fades it out into the head."""
    perp = tc['radial'] * tc['rho'][:, None]
    dD = (perp * tc['D']).sum(axis=1)
    dL = (perp * tc['L']).sum(axis=1)
    r = np.maximum(radius(np.clip(tc['s'], 0.0, S_TOT)), 1e-3)
    down = smooth(0.0, -1.0, dD / r)
    nD = dD * (1.0 - (1.0 - BELLY_K) * down ** 1.5)
    nL = dL * (1.0 + (SIDE_K - 1.0) * (1.0 - np.abs(np.clip(dD / r, -1, 1))))
    return co + (tc['D'] * (nD - dD)[:, None] + tc['L'] * (nL - dL)[:, None]) * w[:, None]
