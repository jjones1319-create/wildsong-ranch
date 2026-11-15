"""Mirrorkin's shape (mirrorkin_ultra.py): measured on chatgpt/monsters/17-mirrorkin/2-turnaround.png (front and side
views at 1.67 mm a pixel: the crest's tip at 1.18 m, the handle's tip 4.4 cm off the ground).

- The mirror: one closed solid (body_extras): the convex glass dome, the gilded frame's moulding (an inner lip, a bead,
  a cove, the main bead and the outer roll) and the domed gold back. Every point of it is given by its angle round the
  oval (phi: 0 at its left side, +X; pi/2 at the top) and its place along the profile.
- The handle: a lathe with an oval cross-section below the frame (narrow neck, a teardrop bulb).
- The gloves: rounded parts (all_parts), voxel-united into the body as two islands, skinned rigid to hand.L / hand.R.
Pure numpy (and mathutils for the parts' frames). Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Matrix, Vector

from lib.mesh import Part
from lib.surface import smooth

# ----------------------------------------------------------------------------- the oval
ZC = 0.78                     # the oval's centre height
GA, GB = 0.19, 0.246          # the glass's half width and half height (inside the frame's lip)
BAND_SIDE = 0.045             # the frame's width at the sides; top and bottom 0.7 of it (2-turnaround front)
YG0 = -0.026                  # the glass's edge, set back behind the lip
DOME = 0.088                  # the glass bulges this far in front of its edge (the side view's face profile)
DOME_P = 0.6
YB0 = 0.045                   # the back's edge
BACK_DOME = 0.006             # round 1: a near-flat plate (it bulged like a dome) ...
BACK_RIM = (0.93, 0.03, 0.009)   # ... inside a raised rim moulding: (rho, half width, height)
# the moulding: (offset out from the glass's edge, depth y); the offset scales with band_k(phi)
PROFILE = [
    (0.000, -0.026), (0.0006, -0.036), (0.002, -0.0445), (0.005, -0.0495), (0.009, -0.0505), (0.012, -0.0475),
    (0.0145, -0.0435), (0.018, -0.0465), (0.023, -0.0525), (0.029, -0.0545), (0.035, -0.0515), (0.039, -0.0445),
    (0.0425, -0.032), (0.0445, -0.016), (0.045, 0.000), (0.0437, 0.015), (0.040, 0.026), (0.034, 0.034),
    (0.025, 0.0395), (0.012, 0.043), (0.000, 0.045),
]
# where each moulding feature lies along the profile (index ranges, for the paint): the lip and inner bead, the cove,
# the main bead, the outer roll, the back edge
P_LIP = (1, 5)
P_COVE = (6, 7)
P_BEAD = (7, 12)
P_ROLL = (12, 17)


def band_k(phi):
    """The frame's width at angle phi as a share of BAND_SIDE (sides 1, top and bottom 0.7)."""
    return 1.0 - 0.3 * np.sin(phi) ** 2


def oval_xz(phi, d):
    """A point on the oval offset d (scaled by band_k) out from the glass's edge, at angle phi: (x, z)."""
    dd = d * band_k(phi)
    return (GA + dd) * np.cos(phi), ZC + (GB + dd) * np.sin(phi)


def glass_rho(x, z):
    """The elliptic radius of (x, z) in the glass's oval (1 at the glass's edge)."""
    return np.sqrt((np.asarray(x) / GA) ** 2 + ((np.asarray(z) - ZC) / GB) ** 2)


def glass_y(x, z):
    """The glass's front surface at (x, z) (inside the oval)."""
    r2 = np.clip(glass_rho(x, z) ** 2, 0.0, 1.0)
    return YG0 - DOME * (1.0 - r2) ** DOME_P


def glass_normal(x, z) -> np.ndarray:
    """The glass's outward normal at (x, z)."""
    x, z = np.asarray(x, np.float64), np.asarray(z, np.float64)
    e = 1e-4
    gx = (glass_y(x + e, z) - glass_y(x - e, z)) / (2 * e)
    gz = (glass_y(x, z + e) - glass_y(x, z - e)) / (2 * e)
    n = np.stack([gx, -np.ones_like(gx), gz], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def ring_offset(x, z) -> tuple[np.ndarray, np.ndarray]:
    """(phi, d) of each point: its angle round the oval and its offset out from the glass's edge (in metres, before
    band_k: d / band_k is the profile's coordinate), solved by a few Newton steps."""
    x, z = np.asarray(x, np.float64), np.asarray(z, np.float64)
    phi = np.arctan2((z - ZC) / GB, x / GA)
    d = np.zeros_like(x)
    for _ in range(6):
        k = band_k(phi)
        a, b = GA + d * k, GB + d * k
        f = (x / a) ** 2 + ((z - ZC) / b) ** 2 - 1.0
        df = -2 * k * (x ** 2 / a ** 3 + (z - ZC) ** 2 / b ** 3)
        d = d - f / np.where(np.abs(df) < 1e-9, -1e-9, df)
        phi = np.arctan2((z - ZC) / b, x / a)
    return phi, d


# ----------------------------------------------------------------------------- the mirror solid
def profile_poly() -> list[tuple[float, float, float]]:
    """The whole closed profile from the glass's apex to the back's centre, as (kind, a, y): kind 0 = the glass (a =
    rho 0..1), 1 = the moulding (a = offset), 2 = the back (a = rho 1..0)."""
    out = []
    for r in np.linspace(0.0, 1.0, 34)[1:-1] ** 0.75:
        out.append((0, float(r), float(YG0 - DOME * (1.0 - r * r) ** DOME_P)))
    for d, y in PROFILE:
        out.append((1, d, y))
    for r in np.linspace(1.0, 0.0, 34)[1:-1] ** 0.8:
        out.append((2, float(r), float(back_y(r))))
    return out


def back_y(rho) -> np.ndarray:
    """The back plate's depth at elliptic radius rho: near flat, a raised rim moulding just inside the edge."""
    r = np.asarray(rho, np.float64)
    rc, rw, rh = BACK_RIM
    return YB0 + 0.004 * smooth(1.0, 0.86, r) + BACK_DOME * (1.0 - np.clip(r, 0, 1) ** 2) + rh * np.exp(-((r - rc) / rw) ** 2)


def mirror_rings(m: int = 192) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    """Rings of the closed mirror solid (each m points round the oval) and its two poles (the glass's apex, the back's
    centre)."""
    phi = np.linspace(0.0, 2 * np.pi, m, endpoint=False)
    rings = []
    for kind, a, y in profile_poly():
        if kind == 1:
            x, z = oval_xz(phi, a)
        else:
            x, z = a * GA * np.cos(phi), ZC + a * GB * np.sin(phi)
        rings.append(np.stack([x, np.full(m, y), z], axis=1))
    front = np.array([0.0, YG0 - DOME, ZC])
    back = np.array([0.0, float(back_y(0.0)), ZC])
    return rings, front, back


# ----------------------------------------------------------------------------- the handle
HANDLE_Y = -0.004
# (z, half width, half depth): the neck narrowest at 0.353, the teardrop bulb widest at 0.16 (2-turnaround front, side)
HANDLE = [(0.535, 0.036, 0.03), (0.50, 0.036, 0.03), (0.46, 0.034, 0.029), (0.42, 0.029, 0.026), (0.385, 0.024, 0.022),
          (0.353, 0.022, 0.021), (0.32, 0.027, 0.025), (0.287, 0.038, 0.031), (0.25, 0.055, 0.04), (0.22, 0.068, 0.047),
          (0.19, 0.077, 0.052), (0.161, 0.081, 0.054), (0.13, 0.077, 0.052), (0.103, 0.063, 0.044), (0.085, 0.047, 0.035),
          (0.072, 0.032, 0.027), (0.063, 0.021, 0.019), (0.058, 0.012, 0.012)]
HANDLE_TIP = 0.044            # the finial's tip (a prop)


def handle_rx(z):
    zz = np.asarray(z, np.float64)
    H = np.array(HANDLE[::-1])
    return np.interp(zz, H[:, 0], H[:, 1]), np.interp(zz, H[:, 0], H[:, 2])


def handle_rings(m: int = 64) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    th = np.linspace(0.0, 2 * np.pi, m, endpoint=False)
    zs = np.concatenate([np.linspace(0.535, 0.30, 24), np.linspace(0.29, 0.058, 30)])
    rings = []
    for z in zs:
        rx, ry = handle_rx(z)
        rings.append(np.stack([rx * np.cos(th), HANDLE_Y + ry * np.sin(th), np.full(m, z)], axis=1))
    return rings, np.array([0.0, HANDLE_Y, 0.545]), np.array([0.0, HANDLE_Y, 0.052])


def handle_surface_y(z: float, front: bool = True) -> float:
    """The handle's front (or back) surface depth at height z, on its centre line."""
    _rx, ry = handle_rx(z)
    return float(HANDLE_Y - ry) if front else float(HANDLE_Y + ry)


# ----------------------------------------------------------------------------- the gloves
# the left glove (+X; the right mirrors it): palm up, the fingers pointing out and forward (2-turnaround front and side)
WRIST = Vector((0.318, -0.026, 0.535))
GS = 1.28                     # the gloves' size (the pictures' big cartoon gloves)
HAND_DIR = Vector((0.66, -0.74, 0.12)).normalized()
PALM_UP = Vector((0.0, 0.0, 1.0))
GLOVE_LEN = 0.205 * GS


def hand_frame(s: int = 1) -> tuple[Vector, Vector, Vector, Vector]:
    """(wrist, along, up, thumb side) of the left (s=+1) or right (s=-1) glove."""
    w = Vector((WRIST.x * s, WRIST.y, WRIST.z))
    f = Vector((HAND_DIR.x * s, HAND_DIR.y, HAND_DIR.z))
    up = (PALM_UP - f * PALM_UP.dot(f)).normalized()
    # the thumb: on the left hand, palm up, it lies to the left of the fingers (up x along); mirrored on the right
    th = up.cross(f).normalized() * s
    return w, f, up, th


def mirror(p, s: int) -> tuple[float, float, float]:
    return (p[0] * s, p[1], p[2])


def _euler_deg(f: Vector, up: Vector) -> tuple[float, float, float]:
    """XYZ Euler degrees of a part frame whose local +Y runs along f and local +Z along up."""
    y = f.normalized()
    z = (up - y * up.dot(y)).normalized()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed()
    e = m.to_euler('XYZ')
    return tuple(math.degrees(a) for a in e)


FINGERS = [   # (offset across the knuckles toward the thumb side, length, radius, curl degrees), before GS
    # round 1: spread wider and a little slimmer, so the voxel union leaves real gaps between them
    (0.0255, 0.064, 0.0098, 12.0), (0.0085, 0.071, 0.0101, 9.0), (-0.0085, 0.066, 0.0098, 11.0), (-0.0255, 0.054, 0.0092, 16.0)]


def glove_points(s: int = 1) -> dict:
    """Key points of a glove: the cuff, the palm's centre and size, each finger as two segments, the thumb."""
    w, f, up, th = hand_frame(s)
    g = GS
    palm_c = w + f * (0.062 * g) + up * 0.002
    knuck = w + f * (0.1 * g)
    fingers = []
    for off, ln, r, curl in FINGERS:
        off, ln, r = off * g, ln * g, r * g
        a = knuck + th * off + up * 0.002
        fa = (f + th * off * 4.5 / g).normalized()
        c = math.radians(curl)
        b = a + fa * (ln * 0.5)
        fb = (fa * math.cos(c) + up * math.sin(c)).normalized()
        e = b + fb * (ln * 0.5)
        fingers.append((a, b, e, r))
    t0 = w + f * (0.055 * g) + th * (0.026 * g) + up * 0.004
    tdir = (f * 0.8 + th * 0.45 + up * 0.38).normalized()
    t1 = t0 + tdir * (0.028 * g)
    t2 = t1 + (tdir + f * 0.2).normalized() * (0.024 * g)
    return {'wrist': w, 'along': f, 'up': up, 'thumb_side': th, 'palm': palm_c, 'fingers': fingers, 'thumb': (t0, t1, t2),
            'cuff': (w - f * (0.016 * g), w + f * 0.008)}


def glove_parts(s: int, tag: str) -> list[Part]:
    g = glove_points(s)
    f, up = g['along'], g['up']
    rot = _euler_deg(f, up)
    k = GS
    ps = [Part(f'palm{tag}', 'sphere', loc=tuple(g['palm']), radius=0.05 * k, scale=(0.72, 1.06, 0.4), rot=rot),
          # review round 1: no separate wrist puff (it stuck out past the bracelet like a marshmallow): the heel of the
          # hand ends just behind the bracelet
          Part(f'heel{tag}', 'sphere', loc=tuple(g['wrist'] + f * (0.009 * k)), radius=0.031 * k, scale=(0.95, 1.0, 0.84), rot=rot)]
    for k, (a, b, e, r) in enumerate(g['fingers']):
        ps.append(Part(f'fing{tag}{k}a', 'capsule', loc=tuple(a), to=tuple(b), radius=r))
        ps.append(Part(f'fing{tag}{k}b', 'capsule', loc=tuple(b), to=tuple(e), radius=r * 0.94))
    t0, t1, t2 = g['thumb']
    ps.append(Part(f'thumb{tag}a', 'capsule', loc=tuple(t0), to=tuple(t1), radius=0.0104 * k))
    ps.append(Part(f'thumb{tag}b', 'capsule', loc=tuple(t1), to=tuple(t2), radius=0.0098 * k))
    return ps


def glove_axis(s: int) -> tuple[np.ndarray, np.ndarray]:
    w, f, _up, _th = hand_frame(s)
    return np.array(w - f * (0.04 * GS)), np.array(w + f * (GLOVE_LEN - 0.02))


def glove_mask(co: np.ndarray, s: int, r: float = 0.075 * GS) -> np.ndarray:
    a, b = glove_axis(s)
    ab = b - a
    t = np.clip(((co - a) @ ab) / float(ab @ ab), 0, 1)
    return np.linalg.norm(co - (a + t[:, None] * ab), axis=1) < r


def glove_k(co: np.ndarray) -> np.ndarray:
    """+1 on the left glove, -1 on the right, 0 elsewhere (body points): everything of the body beyond 0.25 m out at the
    gloves' height is glove (the frame's edge is 0.23 m out at most there). Round 1: a radius round the glove's axis
    missed the thumb tips and the cuff's end, which were painted gold."""
    on = (np.abs(co[:, 0]) > 0.25) & (co[:, 2] > 0.36) & (co[:, 2] < 0.72)
    return np.where(on, np.sign(co[:, 0]), 0.0)


def glove_local(co: np.ndarray, s: int) -> np.ndarray:
    """Points in the glove's frame: (along from the wrist, up off the palm, toward the thumb)."""
    w, f, up, th = hand_frame(s)
    d = co - np.array(w)
    return np.stack([d @ np.array(f), d @ np.array(up), d @ np.array(th)], axis=1)


# ----------------------------------------------------------------------------- the parts
def all_parts() -> list[Part]:
    """The gloves, and stand-ins for the mirror and the handle inside the exact solids (body_extras): the weight proxy
    (built from these alone) then has the mirror's mass for the heat solve."""
    ps = [Part('core', 'sphere', loc=(0.0, 0.004, ZC), radius=1.0, scale=(0.17, 0.035, 0.22)),
          Part('stem', 'capsule', loc=(0.0, HANDLE_Y, 0.5), to=(0.0, HANDLE_Y, 0.3), radius=0.016),
          Part('bulb', 'sphere', loc=(0.0, HANDLE_Y, 0.165), radius=1.0, scale=(0.055, 0.035, 0.07))]
    for s, tag in ((1, 'L'), (-1, 'R')):
        ps += glove_parts(s, tag)
    return ps


# ----------------------------------------------------------------------------- the face
EYE_X, EYE_Z = 0.094, 0.814    # the eyes' centres on the glass (2-turnaround front: 57 px apart from the middle)
EYE_A, EYE_B = 0.047, 0.0435   # their half width and half height on the glass
EYE_DOME, EYE_SINK = 0.0028, 0.0018
BROW_X, BROW_Z = 0.104, 0.902
NOSE = (0.0, 0.774)
MOUTH_Z, MOUTH_W, MOUTH_SAG = 0.748, 0.058, 0.011
BLUSH_X, BLUSH_Z = 0.132, 0.764


def surface_at(x: float, z: float, out: float = 0.0) -> np.ndarray:
    """The glass's front surface at (x, z), `out` metres along its normal."""
    y = float(glass_y(x, z))
    n = glass_normal(np.array([x]), np.array([z]))[0]
    return np.array([x, y, z]) + n * out


def eye_frame(s: int):
    """(centre, across, up, out) Vectors of the eye on side s (+1 left): the tangent plane of the glass there."""
    c = surface_at(EYE_X * s, EYE_Z)
    n = Vector(glass_normal(np.array([EYE_X * s]), np.array([EYE_Z]))[0])
    up = (Vector((0.0, 0.0, 1.0)) - n * n.z).normalized()
    xa = up.cross(n).normalized()          # toward +X for the monster (it faces -Y: up x out = +X)
    if xa.x < 0:
        xa = -xa
    return Vector(c), xa, up, n


def eye_dist(co: np.ndarray) -> np.ndarray:
    """The distance (in eye radii) from the nearer eye's centre in its tangent plane."""
    out = np.full(len(co), 9.0)
    for s in (1, -1):
        c, xa, ya, _n = eye_frame(s)
        d = co - np.array(c)
        u = d @ np.array(xa) / EYE_A
        v = d @ np.array(ya) / EYE_B
        out = np.minimum(out, np.sqrt(u * u + v * v))
    return out


# ----------------------------------------------------------------------------- zones
def glass_mask(co: np.ndarray, margin: float = 0.0) -> np.ndarray:
    """The glass: inside the lip's oval and in front of the frame's middle."""
    return (glass_rho(co[:, 0], co[:, 2]) < 1.0 - margin) & (co[:, 1] < -0.02)


def handle_mask(co: np.ndarray) -> np.ndarray:
    ring_bottom = ZC - GB - BAND_SIDE * 0.7
    return (co[:, 2] < ring_bottom + 0.012) & (np.abs(co[:, 0]) < 0.09) & (glove_k(co) == 0)


def zones(co: np.ndarray, n=None) -> dict:
    gk = glove_k(co)
    glass = glass_mask(co) & (gk == 0)
    return {'face': glass & (eye_dist(co) < 2.6), 'glass': glass, 'glove': gk != 0, 'handle': handle_mask(co),
            'eye_d': np.clip((eye_dist(co) - 1.0) * 0.1, 0, 1)}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """Protect the face (the eyes' rims sit flush on the glass), the gloves' fingers and the frame's sharp moulding a
    little; the big smooth glass and the back can go."""
    z = zones(co)
    keep = np.zeros(len(co))
    keep = np.maximum(keep, smooth(2.2, 1.0, eye_dist(co)) * z['glass'])
    keep = np.maximum(keep, 0.55 * z['glove'])
    # polish: the whole glass a little, so the dome keeps even triangles (long slivers left a faint shading line down
    # the forehead)
    keep = np.maximum(keep, 0.45 * (z['glass'] & (glass_rho(co[:, 0], co[:, 2]) < 0.96)))
    phi, d = ring_offset(co[:, 0], co[:, 2])
    lip = (d > -0.002) & (d < 0.05) & (co[:, 1] < 0.0) & ~z['glove'] & ~z['handle']
    keep = np.maximum(keep, 0.35 * lip)
    _ = phi
    return keep
