"""Wishlume's shape: the paper globe, its ribs' lines, the paddle arms, the face's places (wishlume_ultra.py).

Measured on chatgpt/monsters/14-wishlume/2-turnaround.png (1672 x 941): 1 px = 1.38 mm, the ground line at y 783, the
front view's axis at x 332 (side 842, back 1340). The globe is 382 px wide, 368 px deep and 370 px tall (paper top
y 178, the bottom ring y 548), its widest at y 363; the upper half is an ellipsoid, the lower half fuller (a
superellipse, n 2.7) cut off by the opening at the ring (radius 97 px). Ten ribs (the front view shows the centre one
and two each side at 0.59 and 0.95 of the radius: 36 degrees apart); the front rib stops between the eyes (y 382).
The crown and its loop rise to y 113 (0.93 m); the tassel hangs to just above the ground.

Metres; the monster faces -Y, Z is up, +X is its left. Everything here is pure numpy / mathutils (no scene access).
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Vector

from lib.mesh import Part
from lib.surface import smooth, v3

PX = 0.00138                         # metres per turnaround pixel

# ----------------------------------------------------------------------------- the globe
C0 = (0.0, 0.0, 0.58)                # the globe's centre: the hover point
A_X, A_Y = 0.2636, 0.2538            # half width, half depth
B_TOP, B_BOT, N_BOT = 0.255, 0.257, 2.7
Z_OPEN = 0.339                       # the bottom opening (the ring) ...
R_OPEN = 0.134                       # ... and its radius (across x; y is A_Y / A_X of it)
DISH_D = 0.062                       # how far the inside of the lantern rises above the opening (the flame's dome)
TOP_Z = C0[2] + B_TOP                # 0.835: the paper's top (restHeight)
RIBS = 10
RIB_STEP = 360.0 / RIBS
RIB_R = 0.0072                       # a rib's radius (polish: 1.5x, so the ribs read at 64 px)
RIB_TOP_R = 0.074                    # the ribs run under the crown's rim from here
FRONT_RIB_END = 0.655                # round 3: the front rib stops at the brow line (3-faces; lower, it read as a nose)
PILLOW = 0.0034                      # the paper bulges between the ribs ...
GROOVE = 0.0011                      # ... and dips under each rib


def rho_unit(u: np.ndarray) -> np.ndarray:
    """Distance from C0 to the bare globe along unit directions u (n x 3)."""
    q2 = (u[:, 0] / A_X) ** 2 + (u[:, 1] / A_Y) ** 2
    top = 1.0 / np.sqrt(q2 + (u[:, 2] / B_TOP) ** 2)
    q = np.sqrt(q2)
    bot = (q ** N_BOT + (np.abs(u[:, 2]) / B_BOT) ** N_BOT) ** (-1.0 / N_BOT)
    return np.where(u[:, 2] >= 0, top, bot)


def theta_deg(p: np.ndarray) -> np.ndarray:
    """The angle round the axis: 0 at the front (-Y), +90 at the monster's left (+X)."""
    return np.degrees(np.arctan2(p[:, 0], -p[:, 1]))


def rib_angles() -> list[float]:
    return [RIB_STEP * k for k in range(RIBS)]


def pillow(p: np.ndarray) -> np.ndarray:
    """The paper's offset along the globe's radius: a soft bulge in the middle of each panel, a small dip at each rib,
    fading where the ribs converge (the top) and at the opening; below the front rib's end the two front panels merge."""
    th = theta_deg(p)
    z = p[:, 2]
    rxy = np.sqrt(p[:, 0] ** 2 + p[:, 1] ** 2)
    phi = (th + RIB_STEP / 2) % RIB_STEP - RIB_STEP / 2           # degrees to the nearest rib
    u = np.abs(phi) / (RIB_STEP / 2)                               # 0 on a rib, 1 mid-panel
    narrow = PILLOW * 0.5 * (1 - np.cos(np.pi * u)) - GROOVE * np.exp(-((np.radians(phi) * rxy) / 0.004) ** 2)
    wide = PILLOW * 0.5 * (1 - np.cos(np.pi * np.clip(1 - np.abs(th) / RIB_STEP, 0, 1)))
    front = (np.abs(th) < RIB_STEP) * smooth(FRONT_RIB_END + 0.01, FRONT_RIB_END - 0.035, z)
    off = narrow * (1 - front) + wide * front
    fade = smooth(TOP_Z - 0.012, TOP_Z - 0.075, z) * smooth(Z_OPEN + 0.004, Z_OPEN + 0.045, z)
    return off * fade


def globe_point(p: np.ndarray) -> np.ndarray:
    """Each point moved onto the paper along the globe's radius (the bulges included)."""
    c = v3(C0)
    d = p - c
    r = np.maximum(np.linalg.norm(d, axis=1), 1e-9)
    u = d / r[:, None]
    q = c + u * rho_unit(u)[:, None]
    return c + u * (rho_unit(u) + pillow(q))[:, None]


def outside(p: np.ndarray) -> np.ndarray:
    """How far each point lies outside the bare globe (negative inside)."""
    c = v3(C0)
    d = p - c
    r = np.linalg.norm(d, axis=1)
    u = d / np.maximum(r, 1e-9)[:, None]
    return r - rho_unit(u)


def ellip_r(p: np.ndarray) -> np.ndarray:
    """The radius round the axis, measured across x (y stretched by A_X / A_Y): R_OPEN on the opening's rim."""
    return np.sqrt(p[:, 0] ** 2 + (p[:, 1] * A_X / A_Y) ** 2)


def dish_z(s: np.ndarray) -> np.ndarray:
    """The inside of the lantern seen through the opening: a dome rising DISH_D above the rim (s = ellip_r / R_OPEN)."""
    return Z_OPEN + DISH_D * np.sqrt(np.clip(1 - np.clip(s, 0, 1) ** 2, 0, 1))


def surface_at(x: float, z: float, front: bool = True) -> Vector:
    """The paper's point at (x, z) on the front (or back) half: bisection along y."""
    sgn = -1.0 if front else 1.0
    lo, hi = 0.0, 0.32
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        p = np.array([[x, sgn * mid, z]])
        if outside(p)[0] - pillow(globe_point(p))[0] > 0:
            hi = mid
        else:
            lo = mid
    return Vector((x, sgn * 0.5 * (lo + hi), z))


def surface_dir(theta: float, z: float) -> Vector:
    """The paper's point at angle theta (degrees, 0 front, +90 left) and height z."""
    t = math.radians(theta)
    lo, hi = 0.0, 0.32
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        p = np.array([[mid * math.sin(t), -mid * math.cos(t), z]])
        if outside(p)[0] - pillow(globe_point(p))[0] > 0:
            hi = mid
        else:
            lo = mid
    r = 0.5 * (lo + hi)
    return Vector((r * math.sin(t), -r * math.cos(t), z))


def normal_at(p: Vector) -> Vector:
    """The bare globe's outward normal (the gradient of its implicit form) at a point on or near it."""
    d = p - Vector(C0)
    if d.z >= 0:
        n = Vector((d.x / A_X ** 2, d.y / A_Y ** 2, d.z / B_TOP ** 2))
    else:
        q = math.sqrt((d.x / A_X) ** 2 + (d.y / A_Y) ** 2)
        k = N_BOT * q ** (N_BOT - 2)
        n = Vector((k * d.x / A_X ** 2, k * d.y / A_Y ** 2, -N_BOT * (abs(d.z) / B_BOT) ** (N_BOT - 1) / B_BOT))
    return n.normalized()


def tangent_frame(p: Vector, angle_deg: float = 0.0) -> tuple[Vector, Vector, Vector]:
    """(n, t, b) at p: the normal, a direction on the surface `angle_deg` from straight up (+ toward +theta, i.e.
    round toward the monster's left on the front) and the third axis."""
    n = normal_at(p)
    up = Vector((0, 0, 1)) - n * n.z
    if up.length < 1e-6:
        up = Vector((0, -1, 0)) - n * (-n.y)
    up.normalize()
    east = n.cross(up).normalized() * -1.0          # toward +theta
    a = math.radians(angle_deg)
    t = (up * math.cos(a) + east * math.sin(a)).normalized()
    return n, t, n.cross(t).normalized()


# ----------------------------------------------------------------------------- the arms: plump paper paddles
# (front view: the root 0.124 m tall at the globe's side, a slight waist, a round bulb 0.11 m tall reaching x 0.395,
# drooping about 27 degrees; the broad face turned a little out from the front)
ARM_DROOP, ARM_TURN = 25.0, 22.0     # degrees down, and back: round 2 turns the broad face further out, so the side view
                                     # shows a flat paddle with its leaves rather than the end of a tube
ARM_HALF = (0.064, 0.135, 0.042)     # half height, half length, half thickness (polish: 30% longer, plumper, thickest out at the bulb)
ARM_TAPER = 0.3                      # the root end narrower (lib.mesh 'paddle')
ARM_AXIS0 = Vector((0.2, -0.03, 0.52))


def _arm_matrix():
    """Local paddle axes (x height, y along, z thickness) to world, for the left paddle."""
    from mathutils import Euler, Matrix
    perm = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0)))
    return Euler((0.0, math.radians(ARM_DROOP), math.radians(ARM_TURN)), 'XYZ').to_matrix() @ perm


ARM_M = _arm_matrix()
ARM_ROT = tuple(math.degrees(a) for a in ARM_M.to_euler('XYZ'))
ARM_DIR = ARM_M @ Vector((0, 1, 0))
ARM_C = ARM_AXIS0 + ARM_DIR * (0.008 + ARM_HALF[1])          # the paddle's centre (its root end sunk in the globe)
ARM_BULB = ARM_AXIS0 + ARM_DIR * 0.2                           # its widest part
ARM_FLARE = (ARM_AXIS0 + ARM_DIR * 0.048, (0.074, 0.052, 0.04))   # where it grows out of the globe
ARM = {'shoulder': tuple(ARM_AXIS0 + ARM_DIR * 0.07), 'elbow': tuple(ARM_AXIS0 + ARM_DIR * 0.15),
       'hand': tuple(ARM_AXIS0 + ARM_DIR * 0.276)}


def arm_axes(s: int) -> tuple[Vector, Vector, Vector]:
    """The left (s 1) or right paddle's (along, broad-face normal toward the front, up) axes."""
    along, up, thick = ARM_M @ Vector((0, 1, 0)), ARM_M @ Vector((1, 0, 0)), ARM_M @ Vector((0, 0, 1))
    face = -thick if thick.y > 0 else thick
    if s < 0:
        along, face, up = Vector((-along.x, along.y, along.z)), Vector((-face.x, face.y, face.z)), Vector((-up.x, up.y, up.z))
    return along, face, up


def mirror(p, s: int) -> tuple[float, float, float]:
    return (p[0] * s, p[1], p[2])


def arm_e(p: np.ndarray) -> np.ndarray:
    """The paddles' field: < 1 inside a paddle or its root flare (either side), about 1 on its skin."""
    R = np.array(ARM_M)
    q = np.stack([np.abs(p[:, 0]), p[:, 1], p[:, 2]], axis=1)
    sx, sy, sz = ARM_HALF
    loc = (q - v3(ARM_C[:])) @ R
    k = np.clip((loc[:, 1] / sy + 1) / 2, 0, 1)
    w = (1 - ARM_TAPER) + ARM_TAPER * np.sin(np.minimum(1.0, k * 1.15) * np.pi / 2)
    e = np.sqrt((loc[:, 0] / (sx * w)) ** 2 + (loc[:, 1] / sy) ** 2 + (loc[:, 2] / sz) ** 2)
    loc2 = ((q - v3(ARM_FLARE[0][:])) @ R) / v3(ARM_FLARE[1])
    return np.minimum(e, np.linalg.norm(loc2, axis=1))


def arm_k(p: np.ndarray) -> np.ndarray:
    """0..1: how much a point belongs to a paddle (its skin outside the globe; the root's fillet half and half)."""
    return smooth(1.32, 1.1, arm_e(p)) * smooth(-0.002, 0.006, outside(p)) * (np.abs(p[:, 0]) > 0.15)


def arm_local(p: np.ndarray, s: int) -> np.ndarray:
    """Points in the s paddle's frame: (along from the bulb's widest part, across the face toward the front, up)."""
    al, fa, up = (v3(a) for a in arm_axes(s))
    c = v3(mirror(ARM_BULB, s))
    d = p - c
    return np.stack([d @ al, d @ fa, d @ up], axis=1)


def all_parts() -> list[Part]:
    ps = [Part('globe', 'sphere', loc=C0, radius=1.0, scale=(A_X, A_Y, B_TOP)),
          # the fuller lower half (the snap in carve() then lays the paper on the exact profile)
          Part('skirt', 'sphere', loc=(0.0, 0.0, 0.47), radius=1.0, scale=(0.245, 0.236, 0.16))]
    ps.append(Part('arm', 'paddle', loc=tuple(ARM_C), radius=1.0, scale=ARM_HALF, rot=ARM_ROT, taper=ARM_TAPER, mirror=True))
    ps.append(Part('arm_root', 'sphere', loc=tuple(ARM_FLARE[0]), radius=1.0, scale=ARM_FLARE[1], rot=ARM_ROT, mirror=True))
    return ps


# ----------------------------------------------------------------------------- the face (front-view measurements)
EYE_X, EYE_Z = 0.104, 0.574          # polish: wider apart with the bigger eyes (the gap stays about 21% of the body)
EYE_R = 0.0515                       # polish: 10% bigger (0.18 of the body's width). Round 3: the lens is a patch laid on the paper (it was a dome that sank on the nose side
                                     # and stood proud on the other); it shows to 0.93 of this: 0.087 m, 16.5% of the body
EYE_SHAPE = (1.0, 1.1)               # near-round, a little taller than wide
EYE_DOME, EYE_SINK = 0.0024, 0.0002  # the patch's bulge over the paper at its centre, and how far its rim sits under it
BROW_X, BROW_Z = 0.0945, 0.664       # each brow's centre; it spans 0.06 m and arches 7 mm
MOUTH_Z, MOUTH_W, MOUTH_SAG = 0.518, 0.033, 0.0085
BLUSH_X, BLUSH_Z, BLUSH_R = 0.122, 0.507, (0.027, 0.015)   # round 3: a clear soft oval, about the iris's width


def eye_centre(s: int) -> Vector:
    return surface_at(EYE_X * s, EYE_Z)


EYE_C = {s: eye_centre(s) for s in (1, -1)}


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye: the look wraps the globe's curve, mostly ahead."""
    c = EYE_C[s]
    look = (normal_at(c) * 0.62 + Vector((0, -1, 0)) * 0.38).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_local(p: np.ndarray, s: int) -> np.ndarray:
    """Points in an eye's frame, in units of EYE_R (x across, y up, z out)."""
    c, xa, ya, lk = eye_frame(s)
    d = p - v3(c)
    return np.stack([d @ v3(xa) / (EYE_R * EYE_SHAPE[0]), d @ v3(ya) / (EYE_R * EYE_SHAPE[1]), d @ v3(lk) / EYE_R], axis=1)


def eye_dist(p: np.ndarray) -> np.ndarray:
    return np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))


# ----------------------------------------------------------------------------- zones
def zones(p: np.ndarray, n=None) -> dict:
    p = np.asarray(p, np.float64)
    ak = arm_k(p)
    ed = eye_dist(p)
    th = theta_deg(p)
    z = p[:, 2]
    face = (np.abs(th) < 48) & (z > 0.47) & (z < 0.71) & (ak < 0.5)
    dish = (z < Z_OPEN + DISH_D + 0.002) & (ellip_r(p) < R_OPEN * 1.002) & (z < 0.41)
    return {'face': face, 'eye_d': ed, 'arm': ak, 'dish': dish, 'muzzle': np.zeros(len(p), bool)}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(z['face'] * 0.85 + (z['eye_d'] < 0.06) * 1.0 + z['arm'] * 0.35, 0, 1)
