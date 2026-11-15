"""Zipwisp's shape (zipwisp_ultra.py): the ball of static, its swirl, the flame licks of its fuzzy outline, the crown
flames and the curl, the face's places, the wings' and the tail's outlines and frames.

Measured on chatgpt/monsters/16-zipwisp/2-turnaround.png (1672 x 941): the ground line at y 703, the tuft's top at y
229 (0.6 m: 1 px = 1.263 mm); the front view's axis at x 324, the side view's centre at x 796, the back view's 1346.
The ball is about 320 px wide and 314 deep with its fuzz (0.40 m), its fuzz from y 286 to 671 (a little taller than
wide, flames rising off the crown), its lowest point about 32 px over the ground; the eye line y 443 (0.328 m), the
eyes about 64 x 68 px (0.08 x 0.086 m) at x +-65 px; the white core round the mouth (y 505) and a white star on the
back (y 504); the spark wings' tips at x +-281 px, y 332 (0.47 m), swept back (the side view shows them behind the
middle); the zigzag tail leaves the lower back on the monster's right and runs back and out to (-0.33, 0.34, 0.17);
the curl on the crown leans to the monster's right (front view x 213-263).

Metres; the monster faces -Y, Z is up, +X is its left. Pure numpy / mathutils (no scene access).
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Vector

from lib.mesh import Part
from lib.surface import smooth, v3

PX = 0.001263                        # metres per turnaround pixel

# ----------------------------------------------------------------------------- the ball
C0 = (0.0, 0.0, 0.27)                # the ball's centre: the hover point
A_X, A_Y, B_Z = 0.19, 0.182, 0.205   # half width, half depth, half height (the bare ball, under its flame licks)
TOP_Z = C0[2] + B_Z                  # 0.475
BOT_Z = C0[2] - B_Z                  # 0.065
Q = (0.0, 0.0, 0.255)                # the swirl's axis runs front to back through here (the core and the back star)
SPIN = -1.0                          # the swirl turns clockwise seen from behind (2-turnaround back view)
SPIRAL = (0.6, 0.8)                  # sin, cos of the spiral's angle off the circles round the axis (36.9 degrees)


def rho_unit(u: np.ndarray) -> np.ndarray:
    """Distance from C0 to the bare ball along unit directions u (n x 3)."""
    return 1.0 / np.sqrt((u[:, 0] / A_X) ** 2 + (u[:, 1] / A_Y) ** 2 + (u[:, 2] / B_Z) ** 2)


def ball_point(p: np.ndarray) -> np.ndarray:
    """Each point moved onto the bare ball along its radius from C0."""
    c = v3(C0)
    d = np.asarray(p, np.float64) - c
    r = np.maximum(np.linalg.norm(d, axis=1), 1e-9)
    u = d / r[:, None]
    return c + u * rho_unit(u)[:, None]


def outside(p: np.ndarray) -> np.ndarray:
    """How far each point lies outside the bare ball, along its radius (negative inside)."""
    c = v3(C0)
    d = np.asarray(p, np.float64) - c
    r = np.linalg.norm(d, axis=1)
    u = d / np.maximum(r, 1e-9)[:, None]
    return r - rho_unit(u)


def normal_of(p: np.ndarray) -> np.ndarray:
    """The bare ball's outward normal at points on or near it (the gradient of its implicit form)."""
    d = np.asarray(p, np.float64) - v3(C0)
    g = d / np.array([A_X ** 2, A_Y ** 2, B_Z ** 2])
    return g / np.maximum(np.linalg.norm(g, axis=1), 1e-12)[:, None]


def surface_dir(u) -> Vector:
    """The bare ball's point in direction u (from C0)."""
    u = v3(u) / np.linalg.norm(v3(u))
    return Vector((v3(C0) + u * rho_unit(u[None])[0]).tolist())


def front_point(x: float, z: float) -> Vector:
    """The bare ball's front point at (x, z)."""
    dx, dz = x / A_X, (z - C0[2]) / B_Z
    y = -A_Y * math.sqrt(max(0.0, 1.0 - dx * dx - dz * dz))
    return Vector((x, y, z))


# ----------------------------------------------------------------------------- the swirl (static strands, licks)
def swirl_frame(p: np.ndarray):
    """Per point: (alpha, phi, circ, merid): the angle from the back pole (+Y) of the swirl's axis, the angle round it,
    and the unit tangents of the circulation (SPIN) and of the meridian away from the back pole."""
    d = np.asarray(p, np.float64) - v3(Q)
    r = np.maximum(np.linalg.norm(d, axis=1), 1e-9)
    c = np.clip(d[:, 1] / r, -1.0, 1.0)
    alpha = np.arccos(c)
    phi = np.arctan2(d[:, 2], d[:, 0])
    n = normal_of(p)
    a = np.array([0.0, 1.0, 0.0])
    circ = SPIN * np.cross(np.broadcast_to(a, n.shape), n)
    circ /= np.maximum(np.linalg.norm(circ, axis=1), 1e-9)[:, None]
    merid = -(a[None] - n * n[:, 1:2])               # away from the back pole, along the surface
    merid /= np.maximum(np.linalg.norm(merid, axis=1), 1e-9)[:, None]
    return alpha, phi, circ, merid


def flow(p: np.ndarray) -> np.ndarray:
    """The swirl's unit direction on the surface: round the axis, spiralling out of the back star toward the front."""
    _a, _p, circ, merid = swirl_frame(p)
    t = SPIRAL[1] * circ + SPIRAL[0] * merid
    return t / np.maximum(np.linalg.norm(t, axis=1), 1e-9)[:, None]


def swirl_coords(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(psi, chi): the loxodrome coordinates of the swirl (conformal: L = ln tan(alpha/2), phi). psi is constant along
    a strand, chi runs along it. psi jumps by 2 pi SIN at the seam, so N * SIN must be whole for a seamless sin(N psi)."""
    alpha, phi, _c, _m = swirl_frame(p)
    c = np.cos(alpha)
    L = 0.5 * np.log(np.clip((1.0 - c) / np.maximum(1.0 + c, 1e-9), 1e-9, 1e9))
    s, k = SPIRAL
    # the flow in (L, phi) is (s, -SPIN k) (phi falls as the ball turns about +Y): psi is level along it, chi rises
    psi = L * k + SPIN * phi * s
    chi = L * s - SPIN * phi * k
    return psi, chi


# ----------------------------------------------------------------------------- the face
FACE_DIR = Vector((0.0, -1.0, 0.18)).normalized()
EYE_X, EYE_Z = 0.086, 0.32
EYE_R = 0.039                        # the eye's half width
EYE_SHAPE = (1.0, 1.32)              # review 2: a taller oval still (4-details 2), 0.078 x 0.103 m
EYE_DOME, EYE_SINK = 0.0062, 0.0004  # the lens bulges over the ball at its centre; its rim tucks under it
MOUTH_Z, MOUTH_W, MOUTH_H = 0.249, 0.027, 0.024    # a small open smile (1-hero): half width, height
CORE_FRONT = (0.0, -1.0, -0.03)      # the white core: a spot just above the mouth, fading before the eyes' outer edges (review 3) ...
CORE_BACK = (0.0, 1.0, -0.09)        # ... and as a star on the back


def eye_centre(s: int) -> Vector:
    return front_point(EYE_X * s, EYE_Z)


EYE_C = {s: eye_centre(s) for s in (1, -1)}


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye: the look follows the ball's curve, a little toward the front."""
    c = EYE_C[s]
    n = Vector(normal_of(np.array([c[:]]))[0].tolist())
    look = (n * 0.7 + Vector((0, -1, 0)) * 0.3).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_dist(p: np.ndarray) -> np.ndarray:
    return np.minimum(np.linalg.norm(p - v3(EYE_C[1][:]), axis=1), np.linalg.norm(p - v3(EYE_C[-1][:]), axis=1))


def face_angle(p: np.ndarray) -> np.ndarray:
    """Degrees between a point's direction from C0 and the face's direction."""
    d = np.asarray(p, np.float64) - v3(C0)
    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]
    return np.degrees(np.arccos(np.clip(d @ v3(FACE_DIR[:]), -1, 1)))


def dir_angle(p: np.ndarray, u) -> np.ndarray:
    d = np.asarray(p, np.float64) - v3(C0)
    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]
    u = v3(u) / np.linalg.norm(v3(u))
    return np.degrees(np.arccos(np.clip(d @ u, -1, 1)))


# ----------------------------------------------------------------------------- licks: the fuzzy, flaming outline
def _fib(n: int) -> np.ndarray:
    k = np.arange(n) + 0.5
    z = 1 - 2 * k / n
    a = math.pi * (3 - math.sqrt(5)) * k
    r = np.sqrt(1 - z * z)
    return np.stack([r * np.cos(a), r * np.sin(a), z], axis=1)


_LICKS: list = []


def licks() -> list[dict]:
    """The flame licks over the ball (1-hero, 2-turnaround: a ragged outline of flame tongues swirling round), each a
    broad tongue lying along the swirl: it starts sunk in the ball, follows the ball's curve with the flow and lifts
    off it toward its rounded tip, curling a little to one side: {'pts' (4), 'r' (4)}. None on the face, short round
    it and round the back star, longer and lifting more on the crown. A fixed seed."""
    if _LICKS:
        return _LICKS
    rng = np.random.default_rng(16)
    U = _fib(390)
    U += rng.normal(0, 0.035, U.shape)
    U /= np.linalg.norm(U, axis=1)[:, None]
    P = v3(C0) + U * rho_unit(U)[:, None]
    fa = face_angle(P)
    back = dir_angle(P, CORE_BACK)
    for p, f, b in zip(P, fa, back):
        if f < 46:
            continue                                  # the face gets its own low wisps (face_wisps)
        n = normal_of(p[None])[0]
        near = 1.0 - smooth(46, 64, f)                # licks round the face are short
        crown = smooth(0.5, 0.85, n[2])
        k = (0.6 + 0.4 * smooth(10, 32, b)) * (1.0 - 0.5 * near)
        L = float(rng.uniform(0.05, 0.08)) * k * (1 + 0.2 * crown)
        lift = float(rng.uniform(0.016, 0.026)) * k * (1 + 0.25 * crown)   # review 2: the crest read as crystal spikes
        lift *= 0.65 + 0.35 * smooth(-0.6, 0.0, n[2])  # review 3: flatter underneath (lifted tips left see-through loops)
        r0 = float(rng.uniform(0.0105, 0.015)) * (0.75 + 0.25 * k)      # round 1: finer tongues (they read as scales)
        curl = float(rng.uniform(-14, 14))            # degrees the tongue turns about the normal per step
        hook = 30.0 if curl >= 0 else -30.0           # review 2: the tip curls over with the swirl to a finer point
        hs = (-0.008, 0.2 * lift, 0.6 * lift, 0.92 * lift, lift)   # review 3: the tip never dips back (no closed loops)
        q, t = p - flow(p[None])[0] * L * 0.35, None
        q = ball_point(q[None])[0]
        pts = []
        for i in range(5):
            nn = normal_of(q[None])[0]
            t = flow(q[None])[0] if t is None else t - nn * float(t @ nn)
            t /= np.linalg.norm(t)
            pts.append(tuple(q + nn * hs[i]))
            ang = np.radians(curl + (hook if i == 3 else 0.0))
            side = np.cross(nn, t)
            t = t * np.cos(ang) + side * np.sin(ang)
            t = t + nn * (0.12 + 0.2 * crown) * (1 <= i <= 2)
            q = ball_point((q + t / np.linalg.norm(t) * (L / (3.4 if i < 3 else 6.0)))[None])[0]
        rr = (r0, 0.75 * r0, 0.5 * r0, 0.0046, 0.0033)
        _LICKS.append({'pts': pts, 'r': rr})
    _LICKS.extend(face_wisps())
    return _LICKS


def _face_clear(q: np.ndarray) -> bool:
    """Clean skin stays round the eyes and the mouth (the lenses sit flush, the smile reads)."""
    mc = front_point(0.0, MOUTH_Z - 0.4 * MOUTH_H)
    e = eye_dist(q[None])[0]
    return e > EYE_R * 1.75 and float(np.linalg.norm(q - np.array(mc[:]))) > 0.05


def face_wisps() -> list[dict]:
    """Review 1: short, low wisps over the face's edge and the cheeks (the smooth face read as a bald disk with a hard
    edge), smallest toward the middle, none round the eyes and the mouth."""
    rng = np.random.default_rng(61)
    U = _fib(1400)
    U += rng.normal(0, 0.01, U.shape)
    U /= np.linalg.norm(U, axis=1)[:, None]
    P = v3(C0) + U * rho_unit(U)[:, None]
    fa = face_angle(P)
    out = []
    for p, f in zip(P, fa):
        if f < 16 or f >= 46 or not _face_clear(p):
            continue
        k = 0.35 + 0.45 * smooth(16, 46, f)
        L = float(rng.uniform(0.03, 0.05)) * k / 0.8
        lift = float(rng.uniform(0.005, 0.01)) * k / 0.8
        r0 = float(rng.uniform(0.0065, 0.009))
        hs = (-0.005, 0.3 * lift, 0.7 * lift, lift)
        q, t = ball_point((p - flow(p[None])[0] * L * 0.4)[None])[0], None
        pts, ok = [], True
        for i in range(4):
            nn = normal_of(q[None])[0]
            t = flow(q[None])[0] if t is None else t - nn * float(t @ nn)
            t /= np.linalg.norm(t)
            if not _face_clear(q):
                ok = False
            pts.append(tuple(q + nn * hs[i]))
            q = ball_point((q + t * (L / 3))[None])[0]
        if ok:
            out.append({'pts': pts, 'r': (r0, 0.75 * r0, 0.55 * r0, 0.0041)})
    return out


# the crown's flames (1-hero, 3-faces: tongues rising off the top, leaning with the swirl toward the monster's right) and
# the big curl (2-turnaround: on the crown's right, curling over toward the right and down)
# review 2: soft flame wisps that bend over with the swirl and curl at the tip (2-turnaround side), not straight spikes
CROWN = [
    [(0.02, 0.05, 0.43), (0.02, 0.05, 0.49), (0.008, 0.052, 0.53), (-0.018, 0.056, 0.548), (-0.04, 0.06, 0.54)],
    [(0.075, -0.035, 0.42), (0.082, -0.04, 0.47), (0.072, -0.046, 0.505), (0.05, -0.05, 0.522), (0.032, -0.052, 0.515)],
    [(0.1, 0.055, 0.4), (0.114, 0.06, 0.45), (0.11, 0.068, 0.486), (0.092, 0.076, 0.505), (0.074, 0.08, 0.5)],
    [(0.005, -0.075, 0.425), (0.0, -0.086, 0.47), (-0.016, -0.094, 0.5), (-0.04, -0.098, 0.512), (-0.06, -0.098, 0.502)],
    [(-0.03, 0.105, 0.415), (-0.036, 0.116, 0.46), (-0.054, 0.124, 0.49), (-0.08, 0.128, 0.5), (-0.098, 0.128, 0.49)],
    [(0.05, 0.125, 0.395), (0.057, 0.14, 0.44), (0.046, 0.152, 0.47), (0.025, 0.158, 0.484), (0.008, 0.16, 0.478)],
    [(-0.04, -0.012, 0.455), (-0.032, -0.03, 0.5), (-0.016, -0.038, 0.528), (0.006, -0.04, 0.54), (0.022, -0.04, 0.532)],
    [(-0.07, 0.025, 0.45), (-0.09, 0.034, 0.494), (-0.112, 0.038, 0.516), (-0.134, 0.038, 0.52), (-0.148, 0.036, 0.508)],
]
CROWN_R = (0.022, 0.017, 0.012, 0.0075, 0.004)
CURL = [(-0.045, 0.0, 0.43), (-0.056, 0.0, 0.49), (-0.066, -0.003, 0.535), (-0.084, -0.005, 0.566), (-0.106, -0.005, 0.578),
        (-0.126, -0.004, 0.57), (-0.135, -0.003, 0.553), (-0.132, -0.002, 0.54)]
CURL_R = (0.032, 0.026, 0.02, 0.015, 0.011, 0.008, 0.006, 0.0042)


def all_parts() -> list[Part]:
    ps = [Part('ball', 'sphere', loc=C0, radius=1.0, scale=(A_X, A_Y, B_Z))]
    for i, lk in enumerate(licks()):
        pts, r = lk['pts'], lk['r']
        for j in range(len(pts) - 1):
            ps.append(Part(f'lick{i}_{j}', 'tube', loc=pts[j], to=pts[j + 1], radius=r[j], r2=r[j + 1]))
    for i, fl in enumerate(CROWN):
        for j in range(len(fl) - 1):
            ps.append(Part(f'crown{i}_{j}', 'tube', loc=fl[j], to=fl[j + 1], radius=CROWN_R[j], r2=CROWN_R[j + 1]))
    for j in range(len(CURL) - 1):
        ps.append(Part(f'curl{j}', 'tube', loc=CURL[j], to=CURL[j + 1], radius=CURL_R[j], r2=CURL_R[j + 1]))
    return ps


TUFT = [CURL[1], CURL[3], CURL[-1]]   # the curl's two bones: the rise, then the curl over


def tuft_k(p: np.ndarray) -> np.ndarray:
    """0..1: how much a point belongs to the curl (outside the ball, near its centre line)."""
    pts = np.asarray(CURL, np.float64)
    d = np.full(len(p), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        ab = b - a
        u = np.clip(((p - a) @ ab) / float(ab @ ab), 0, 1)
        d = np.minimum(d, np.linalg.norm(p - (a + u[:, None] * ab), axis=1))
    return smooth(0.034, 0.024, d) * smooth(0.0, 0.012, outside(p)) * (p[:, 0] < 0.0)


# ----------------------------------------------------------------------------- the spark wings and the bolt tail
WING_ROOT = (0.168, 0.02, 0.362)
WING_SWEEP, WING_RAISE = 18.0, 8.0   # degrees back and up (review 2: at 38 the far wing went edge-on, a horn, in the 3/4 view)
WING_CANT = 28.0                     # review 2: each wing's face turned up this much round its span (both faces show from above)
WING_K = 1.22                        # review 1: bigger (the span about 1.7x the body, 2-turnaround)
# the left wing's outline (u out along the wing, v up), from the root's top: the long upper point, then the zigzag edge
# back to the root (1-hero, 2-turnaround front, 4-details 3: three points)
WING_OUTLINE = [(-0.035, 0.05), (0.03 * WING_K, 0.068 * WING_K), (0.188 * WING_K, 0.106 * WING_K), (0.112 * WING_K, 0.046 * WING_K),
                (0.166 * WING_K, 0.01 * WING_K), (0.094 * WING_K, -0.021 * WING_K), (0.118 * WING_K, -0.077 * WING_K),
                (0.03 * WING_K, -0.042 * WING_K), (-0.035, -0.045)]
WING_T = (0.03, 0.012)              # the slab's thickness at the root and at the points (review 1: thicker)


def wing_axes(s: int) -> tuple[Vector, Vector, Vector, Vector]:
    """Origin, u (out along the wing), v (up in its plane) and its front face's normal, for the left (s 1) or right."""
    sw, ra = math.radians(WING_SWEEP), math.radians(WING_RAISE)
    u = Vector((math.cos(sw) * math.cos(ra) * s, math.sin(sw) * math.cos(ra), math.sin(ra))).normalized()
    v = (Vector((0, 0, 1)) - u * u.z).normalized()
    n = u.cross(v).normalized()
    if n.y > 0:
        n = -n
    # the cant: the wing's top edge leans back, so its front face looks up and forward
    c = math.radians(WING_CANT)
    v = (v * math.cos(c) - n * math.sin(c)).normalized()
    n = u.cross(v).normalized()
    if n.y > 0:
        n = -n
    o = Vector((WING_ROOT[0] * s, WING_ROOT[1], WING_ROOT[2]))
    return o, u, v, n


def wing_bone_points(s: int) -> list[tuple]:
    """The wing chain's 3 points: the root (in the ball), the middle, the upper point's tip."""
    o, u, v, _n = wing_axes(s)
    k = WING_K
    return [tuple(o + u * -0.01 + v * 0.01), tuple(o + u * (0.085 * k) + v * (0.03 * k)), tuple(o + u * (0.188 * k) + v * (0.106 * k))]


TAIL_ROOT_DIR = (-0.78, 0.2, -0.45)   # review 2/3: on the lower right side (about 8 o'clock from the front)
TAIL_TIP = (-0.44, 0.15, 0.2)       # review 3: swung 40 degrees out to its right and a little down, its face toward the
                                     # front three-quarter, so it shows in the front and 3/4 views (pointing back, it hid)      # a little more to the side than the side view shows, so the front view shows the W
# the bolt's centre line in its own plane (s along from root to tip, w up), as shares of the root-to-tip length, with its
# half widths: a W ending in a sharp point (4-details 4)
TAIL_LINE = [(-0.1, 0.0), (0.0, 0.0), (0.25, -0.052), (0.48, 0.042), (0.7, -0.046), (1.0, 0.05)]   # (share of length, metres)
TAIL_HALF = [0.023, 0.022, 0.0195, 0.017, 0.0145, 0.0]
TAIL_T = (0.026, 0.013)             # review 3: a little more wedge (edge-on it read as a white sliver)


def tail_axes() -> tuple[Vector, Vector, Vector, Vector, float]:
    """Origin (where it leaves the ball), s (toward the tip), w (up in its plane), the plane's normal, and the length."""
    o = surface_dir(TAIL_ROOT_DIR)
    o = o - (o - Vector(C0)).normalized() * 0.004
    tip = Vector(TAIL_TIP)
    s = (tip - o)
    length = s.length
    s.normalize()
    w = (Vector((0, 0, 1)) - s * s.z).normalized()
    n = s.cross(w).normalized()
    return o, s, w, n, length


def tail_points() -> list[tuple]:
    """The bolt's corners in model space (root inside the ball, then each corner, the tip)."""
    o, s, w, _n, L = tail_axes()
    return [tuple(o + s * (a * L) + w * b) for a, b in TAIL_LINE]


TAIL_BONES = tail_points()[1:]        # 4 bones, one per stroke of the W


# ----------------------------------------------------------------------------- zones
def zones(p: np.ndarray, n=None) -> dict:
    p = np.asarray(p, np.float64)
    fa = face_angle(p)
    face = (fa < 44) & (outside(p) < 0.01)
    return {'face': face, 'eye_d': eye_dist(p), 'muzzle': np.zeros(len(p), bool), 'tuft': tuft_k(p)}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    lick = smooth(0.004, 0.014, outside(co))
    return np.clip(z['face'] * 0.85 + (z['eye_d'] < 0.06) * 1.0 + 0.3 * lick + 0.4 * z['tuft'], 0, 1)
