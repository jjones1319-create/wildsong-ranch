"""Nibblegrub's form (Art 2.1 Ultra; chatgpt/monsters/27-nibblegrub): the proportions measured on 2-turnaround (1.985 mm
a pixel: 0.80 m from the ground to the antenna balls' tops, HEIGHT_UNITS 120; 1.14 m from the cheeks to the tail's
end), the body's parts and the masks every other helper reads. No Blender imports beyond lib.mesh.Part: pure numpy.

A chubby larva: a big round head (the face, the cheeks sunk into it up to the eyes, a small muzzle over a puffy 'w'
lip and a little open, chewing mouth, the antenna nubs on short curved stalks) sitting on the front of its plump body,
then four bulging segments pinched deep between them, ending in a round dome; one smooth cream underside; six stubby
straight-down legs (three pairs) under the front, each with three round peach toe beans.
Metres; the monster faces −Y, Z is up, +X is its left.

The trunk is a loft: thin elliptic discs every 4 mm along Y (each 6 cm long), voxel-united, so the creases between the
segments are soft valleys of a chosen depth (a union of whole ellipsoids met in sharp V slits that baked black); a
second, continuous run of flatter discs makes the belly (round 1: the belly's discs followed the creases and read as
slab pads with hard cuts).
"""
from __future__ import annotations

import math

import numpy as np

from lib.mesh import Part

# ----------------------------------------------------------------------------- the rig's points
# round 2: three bones in front of the pivot and three behind it (two each curled 72 degrees a joint into a ball and the
# fat body folded into itself; three spread the curl)
HIP = (0.0, 0.18, 0.25)                 # the pivot: the crease between the second and third segments
F1 = (0.0, 0.03, 0.265)
F1B = (0.0, -0.13, 0.285)
F2 = (0.0, -0.28, 0.31)                 # the head's pivot, low in the jowl (the front legs ride front.2, not the head)
R1 = (0.0, 0.3, 0.24)
R1B = (0.0, 0.43, 0.225)
R2 = (0.0, 0.555, 0.2)                  # the tail end
FRONT = [HIP, F1, F1B, F2]
REAR = [HIP, R1, R1B, R2]
HEAD_C = (0.0, -0.27, 0.462)
HEAD_R = 0.25
HEAD_TIP = (0.0, -0.468, 0.49)          # on the face, between the eyes, above the muzzle
HEAD_REACH = 0.36                       # the cheeks reach this far from HEAD_C (the plan's ground guard)
JAW = {'head': (0.0, -0.3, 0.42), 'tail': (0.0, -0.5, 0.33)}     # hinged behind the cheeks, so a chew moves them

# the head: the cranium over the jowl (the first segment's front, cream underneath), the muzzle pad, the lip's two
# puffs (the 'w'), the cheeks
HEAD = ((0.0, -0.27, 0.462), (0.245, 0.2, 0.252))
JOWL = ((0.0, -0.24, 0.25), (0.285, 0.25, 0.235))
MUZZLE = ((0.0, -0.468, 0.433), (0.054, 0.036, 0.033))
LIP = ((0.021, -0.482, 0.401), (0.027, 0.024, 0.02))             # left puff; mirrored
LOWER_LIP = ((0.0, -0.462, 0.347), (0.03, 0.022, 0.014))         # round 2: the mouth opens between the lips
# round 2: sunk about a quarter into the face and raised, so their tops reach the eyes' lower rims (3-faces)
CHEEK = ((0.165, -0.352, 0.38), (0.118, 0.112, 0.116))           # left; mirrored; round 3: a little deeper
CHEEK_FILL = ((0.15, -0.375, 0.31), (0.085, 0.07, 0.05))        # round 3: fills the crease under each cheek
# the mouth: a little open smile under the lip's puffs (the upper edge follows the 'w', the lower one smiles); the
# chew opens it wider (the jaw)
MOUTH = (0.0, -0.475, 0.37)
MOUTH_W = 0.031                         # half width
MOUTH_DEPTH = 0.022
# the antenna nubs: round 2: a thicker stalk, half as long again out of the crown, curving outward, and a round ball;
# a soft flare at the root (the crease there baked a dark blot)
# round 3: longer out of the crown, curving outward
ANTENNA = [(0.075, -0.262, 0.67), (0.112, -0.27, 0.735), (0.19, -0.28, 0.762)]
ANT_R = (0.025, 0.021)
BALL_R = 0.041
ROOT_FLARE = ((0.09, -0.264, 0.69), (0.046, 0.044, 0.03))
# the eyes: big glossy lenses on the face (4-details panel 2), seated in sockets under a soft lid ring
EYE_AT = (0.123, 0.5)                   # x, z of the left eye's centre on the cranium
EYE_R, EYE_DEPTH, EYE_SINK = 0.061, 0.18, 0.006       # round 3: a flatter lens (its edge read in profile)
EYE_TURN = 0.55                         # the lens looks between the surface's normal (1) and straight ahead (0)

# the legs (left; mirrored), front to back: round 2: short fat stumps straight down under the body's sides
LEG_Y = (-0.32, -0.12, 0.07)
LEG_R = (0.06, 0.057)


def leg(i: int) -> dict:
    y = LEG_Y[i]
    return {'hip': (0.185, y, 0.16), 'knee': (0.194, y, 0.085), 'foot': (0.197, y - 0.004, 0.032)}


LEGS = [{**leg(i), 'parent': ('front.2', 'front.1', 'chest')[i]} for i in range(3)]
FOOT_R = (0.062, 0.064, 0.044)               # round 3: a round foot (a flat disc showed when it lifted)
TOE_R = 0.019
TOE_DX = (-0.025, 0.0, 0.025)

# the trunk's segments, round 3: four plump rolls, each rounded front and back (a parabola over its length, top and
# sides), their soft union making a shallow pinch between them (round 2's narrow deep creases read as coin slots):
# (centre y, top, half width)
SEGS = [(-0.105, 0.535, 0.272), (0.08, 0.522, 0.266), (0.265, 0.49, 0.255), (0.44, 0.45, 0.236)]
ROLL_TOP, ROLL_SIDE = 3.4, 2.8          # each roll's fall-off (metres a metre squared): about 3 cm down at a pinch
ROLL_K = 200.0                          # the soft union's sharpness (1/m): rounds each pinch over about a centimetre
BOTTOM = 0.006                          # the trunk's underside
TRUNK_Y = (-0.24, 0.44)                 # the discs' run; the tail dome closes the end
TAIL_CAP = ((0.0, 0.44, 0.228), (0.236, 0.152, 0.222))           # the fourth roll's round back end (a full dome)
DISC_STEP, DISC_LEN = 0.004, 0.03
BELLY_RZ = 0.12


def _pinches() -> tuple:
    """Where each pair of neighbouring rolls' tops meet (the pinches, where the bands lie)."""
    out = []
    for (y0, t0, _w0), (y1, t1, _w1) in zip(SEGS[:-1], SEGS[1:]):
        # t0 − c(y − y0)² = t1 − c(y − y1)²  →  linear in y
        out.append(round(((t0 - t1) / ROLL_TOP + y1 * y1 - y0 * y0) / (2.0 * (y1 - y0)), 4))
    return tuple(out)


BAND_Y = _pinches()


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


def v3(a) -> np.ndarray:
    return np.asarray(a, np.float64)


def smooth(a: float, b: float, x):
    """0 at a, 1 at b (either order), smoothstep between."""
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def ell_q(p: np.ndarray, spec) -> np.ndarray:
    """((p − c) / r)² summed: < 1 inside the ellipsoid."""
    c, r = v3(spec[0]), v3(spec[1])
    return (((p - c) / r) ** 2).sum(axis=-1)


def ell_sdf(p: np.ndarray, spec) -> np.ndarray:
    """An approximate signed distance to the ellipsoid (metres; < 0 inside)."""
    c, r = v3(spec[0]), v3(spec[1])
    q = (p - c) / r
    k = np.linalg.norm(q, axis=-1)
    return (k - 1.0) * float(np.min(r))


# ----------------------------------------------------------------------------- the trunk's profile
def _softmax(vals: list, k: float) -> np.ndarray:
    v = np.stack(vals)
    m = v.max(axis=0)
    return m + np.log(np.exp(k * (v - m)).sum(axis=0)) / k - np.log(len(vals)) / k * 0.0


def envelope(y) -> tuple[np.ndarray, np.ndarray]:
    """(top, half width) of the trunk at y: the rolls' soft union."""
    y = np.atleast_1d(np.asarray(y, np.float64))
    tops = [t - ROLL_TOP * (y - yc) ** 2 for yc, t, _w in SEGS]
    wids = [w - ROLL_SIDE * (y - yc) ** 2 for yc, _t, w in SEGS]
    return _softmax(tops, ROLL_K), _softmax(wids, ROLL_K)


def profile(y) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(centre z, half height, half width) of the trunk's cross-section at y (the underside on the floor)."""
    top, wid = envelope(y)
    bot = np.full_like(top, BOTTOM)
    return 0.5 * (top + bot), 0.5 * (top - bot), wid


def trunk_parts() -> list[Part]:
    """The loft: an elliptic disc every 4 mm, and under each a flatter, fuller one with the same pinches (the belly is
    part of each roll, round 2's separate cream tube with cut ends is gone), tapering into the jowl and the dome."""
    out = []
    n = int(round((TRUNK_Y[1] - TRUNK_Y[0]) / DISC_STEP)) + 1
    ys = np.linspace(TRUNK_Y[0], TRUNK_Y[1], n)
    cz, rz, rx = profile(ys)
    taper = smooth(-0.26, -0.13, ys) * (0.55 + 0.45 * smooth(0.46, 0.37, ys))
    for k, y in enumerate(ys):
        out.append(Part(f'disc{k}', 'sphere', loc=(0.0, float(y), float(cz[k])), radius=1.0,
                        scale=(float(rx[k]), DISC_LEN, float(rz[k]))))
        if taper[k] > 0.05:
            out.append(Part(f'belly{k}', 'sphere', loc=(0.0, float(y), BOTTOM + BELLY_RZ + 0.001), radius=1.0,
                            scale=(float(rx[k]) * 0.92 * float(taper[k]), DISC_LEN, BELLY_RZ)))
    out.append(Part('tailcap', 'sphere', loc=TAIL_CAP[0], radius=1.0, scale=TAIL_CAP[1]))
    return out


# ----------------------------------------------------------------------------- the eyes
def head_surface_y(x: float, z: float) -> float:
    c, r = HEAD[0], HEAD[1]
    return c[1] - r[1] * math.sqrt(max(0.0, 1.0 - (x / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2))


def eye_frame(s: int):
    """(centre on the cranium's surface, x across toward the monster's left, y up, look)."""
    x, z = EYE_AT[0] * s, EYE_AT[1]
    c = v3((x, head_surface_y(x, z), z))
    n = unit((c - v3(HEAD[0])) / v3(HEAD[1]) ** 2)
    look = unit(EYE_TURN * n + (1.0 - EYE_TURN) * v3((0.0, -1.0, 0.0)))
    xax = unit(np.cross(v3((0.0, 0.0, 1.0)), look))
    yax = unit(np.cross(look, xax))
    return c, xax, yax, look


def head_w(u, v, s: int) -> np.ndarray:
    """(polish) The cranium's surface along the eye's look, above the lens's base plane, at in-plane lens coordinates
    (u, v) in lens radii: metres."""
    c, xax, yax, look = eye_frame(s)
    u, v = np.asarray(u, np.float64), np.asarray(v, np.float64)
    p0 = (c - look * EYE_SINK)[None] + (u.reshape(-1)[:, None] * xax[None] + v.reshape(-1)[:, None] * yax[None]) * EYE_R
    C0, rr = v3(HEAD[0]), v3(HEAD[1])
    A = float(((look / rr) ** 2).sum())
    d = (p0 - C0[None]) / rr[None]
    B = 2.0 * (d * (look / rr)[None]).sum(axis=1)
    Cc = (d ** 2).sum(axis=1) - 1.0
    t = (-B + np.sqrt(np.maximum(B * B - 4 * A * Cc, 0.0))) / (2 * A)
    return t.reshape(np.shape(u))


EYE_DOME = (0.0045, 0.0012)                 # (polish) the lens: the head's own curve, 1.2 mm proud at its edge, 5.7 mm at its middle


def lens_w(u, v, s: int) -> np.ndarray:
    rho2 = np.clip(np.asarray(u) ** 2 + np.asarray(v) ** 2, 0.0, 1.0)
    return head_w(u, v, s) + EYE_DOME[0] * (1.0 - rho2) + EYE_DOME[1]


def eye_local(co: np.ndarray, s: int) -> np.ndarray:
    """Points in eye s's frame, in lens radii: (across, up, along the look from the lens's base)."""
    c, xax, yax, look = eye_frame(s)
    q = co - (c - look * EYE_SINK)[None]
    return np.stack([q @ xax, q @ yax, q @ look], axis=1) / EYE_R


# ----------------------------------------------------------------------------- the mouth
def mouth_edges(x) -> tuple[np.ndarray, np.ndarray]:
    """(upper, lower) z of the mouth's opening at x: the upper edge under the lip's two puffs, the lower a smile."""
    ax = np.abs(np.asarray(x, np.float64))
    top = MOUTH[2] + 0.0135 - 0.0035 * np.clip(1.0 - ((ax - 0.016) / 0.016) ** 2, 0.0, 1.0)
    bot = MOUTH[2] - 0.0125 + 0.019 * np.clip(ax / MOUTH_W, 0.0, 1.0) ** 2
    return top, bot


def mouth_inside(co: np.ndarray) -> np.ndarray:
    """0..1: how far inside the opening (in its own height) a point on the face lies; 0 outside."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    top, bot = mouth_edges(x)
    half = np.maximum(0.5 * (top - bot), 1e-4)
    mid = 0.5 * (top + bot)
    e = 1.0 - np.abs(z - mid) / half
    e = np.minimum(e, (MOUTH_W - np.abs(x)) / 0.008)
    return np.clip(e, 0.0, 1.0) * (y < MOUTH[1] + 0.06)


# ----------------------------------------------------------------------------- the parts
def _ell(name: str, spec, s: int = 1) -> Part:
    c, r = spec
    return Part(name, 'sphere', loc=_m(c, s), radius=1.0, scale=tuple(r))


def antenna_points(s: int) -> list[tuple]:
    return [_m(p, s) for p in ANTENNA]


def toe_centres(s: int, i: int) -> list[tuple]:
    lg = leg(i)
    fx, fy = lg['foot'][0] * s, lg['foot'][1] - 0.004
    out = []
    for dx in TOE_DX:
        back = 0.004 * abs(dx) / 0.026
        out.append((fx + dx * s, fy - FOOT_R[1] * 0.7 + back, TOE_R * 1.02))
    return out


def leg_parts(tag: str, s: int, i: int) -> list[Part]:
    lg = leg(i)
    hip, knee, foot = _m(lg['hip'], s), _m(lg['knee'], s), _m(lg['foot'], s)
    ps = [Part(f'leg{i}{tag}', 'tube', loc=hip, to=knee, radius=LEG_R[0], r2=LEG_R[1]),
          Part(f'shin{i}{tag}', 'tube', loc=knee, to=(foot[0], foot[1], foot[2] + 0.026), radius=LEG_R[1], r2=LEG_R[1] * 0.97)]
    fc = (foot[0], foot[1] - 0.004, FOOT_R[2] + 0.001)
    ps.append(Part(f'foot{i}{tag}', 'sphere', loc=fc, radius=1.0, scale=FOOT_R))
    for j, c in enumerate(toe_centres(s, i)):
        ps.append(Part(f'toe{i}{tag}{j}', 'sphere', loc=c, radius=1.0, scale=(TOE_R, TOE_R, TOE_R * 0.95)))
    return ps


def all_parts() -> list[Part]:
    ps = trunk_parts()
    ps += [_ell('head', HEAD), _ell('jowl', JOWL), _ell('muzzle', MUZZLE)]
    for tag, s in (('L', 1), ('R', -1)):
        ps.append(_ell(f'cheek{tag}', CHEEK, s))
        ps.append(_ell(f'cheekfill{tag}', CHEEK_FILL, s))
        ps.append(_ell(f'lip{tag}', LIP, s))
        if s > 0:
            ps.append(_ell('lowerlip', LOWER_LIP))
        a = antenna_points(s)
        ps.append(Part(f'ant{tag}0', 'tube', loc=a[0], to=a[1], radius=ANT_R[0], r2=ANT_R[1]))
        ps.append(Part(f'ant{tag}1', 'tube', loc=a[1], to=a[2], radius=ANT_R[1], r2=ANT_R[1]))
        ps.append(Part(f'ball{tag}', 'sphere', loc=a[2], radius=BALL_R))
        ps.append(_ell(f'flare{tag}', ROOT_FLARE, s))
        for i in range(3):
            ps += leg_parts(tag, s, i)
            # (polish) a soft fillet where each leg meets the belly (a bright sliver and a dark ring showed in the crevice)
            lg = leg(i)
            ps.append(Part(f'legroot{i}{tag}', 'sphere', loc=(lg['hip'][0] * s, lg['hip'][1], 0.112), radius=1.0,
                           scale=(0.068, 0.072, 0.042)))
    return ps


# ----------------------------------------------------------------------------- masks (pure numpy)
def seg_dist(p: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a[None] + t[:, None] * ab[None]), axis=1), t


def cheek_q(co: np.ndarray) -> np.ndarray:
    """The nearer cheek's ellipsoid measure (1 on its surface)."""
    return np.minimum(ell_q(co, (_m(CHEEK[0], 1), CHEEK[1])), ell_q(co, (_m(CHEEK[0], -1), CHEEK[1])))


def antenna_dist(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(distance to the nearer antenna's stalk axis, distance to the nearer ball's centre)."""
    ds = np.full(len(co), np.inf)
    db = np.full(len(co), np.inf)
    for s in (1, -1):
        a = antenna_points(s)
        for k in range(2):
            ds = np.minimum(ds, seg_dist(co, a[k], a[k + 1])[0])
        db = np.minimum(db, np.linalg.norm(co - v3(a[2])[None], axis=1))
    return ds, db


def leg_dist(co: np.ndarray) -> np.ndarray:
    """Distance to the nearest leg's axis (hip → knee → foot)."""
    d = np.full(len(co), np.inf)
    for s in (1, -1):
        for i in range(3):
            lg = leg(i)
            d = np.minimum(d, seg_dist(co, _m(lg['hip'], s), _m(lg['knee'], s))[0])
            d = np.minimum(d, seg_dist(co, _m(lg['knee'], s), _m(lg['foot'], s))[0])
    return d


def toe_dist(co: np.ndarray) -> np.ndarray:
    d = np.full(len(co), np.inf)
    for s in (1, -1):
        for i in range(3):
            for c in toe_centres(s, i):
                d = np.minimum(d, np.linalg.norm(co - v3(c)[None], axis=1))
    return d


def head_zone(co: np.ndarray) -> np.ndarray:
    """1 on the head (the cranium, the face, the cheeks, the antennae), 0 on the trunk; soft at the nape."""
    q = np.minimum(ell_q(co, HEAD), cheek_q(co))
    ds, db = antenna_dist(co)
    out = smooth(1.35, 1.05, q)
    out = np.maximum(out, (np.minimum(ds, db) < 0.08).astype(float))
    return out


def belly_border(co: np.ndarray) -> np.ndarray:
    """The height of the cream border at each point: low along the trunk's sides, under the cheeks on the jowl, up to
    the chin between the cheeks, and low under the round tail end (yellow from behind: 2-turnaround back)."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    side = 0.15 + 0.05 * smooth(0.0, -0.3, y) - 0.08 * smooth(0.36, 0.52, y)
    chin = smooth(-0.36, -0.44, y) * smooth(0.15, 0.08, np.abs(x))
    return side + (0.31 - side) * chin
