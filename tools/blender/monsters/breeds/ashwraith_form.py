"""Ashwraith's shape (ashwraith_ultra.py): the hood and the dark face inside it, the hood's tip, the dark core under the
cloth, the little arms, the eyes' places. The cloth itself (the cape, the front panels, the wisp chains) is in
ashwraith_drape.py. Pure numpy / mathutils (no scene access).

Measured on chatgpt/monsters/15-ashwraith/2-turnaround.png (1672 x 941): 1 px = 1.6 mm (the hood tip's top at y 122,
the ground line at y 810: 688 px = 1.10 m, HEIGHT_UNITS 165), the front view's axis at x 337, the side view's at x 790.
- The hood: a soft cowl 0.53 m wide at the eyes, its crown at z ~1.0, overhanging the face; its tip rises to the
  monster's right and (round 2 of the review, so it reads from the game's three-quarter camera) flops forward and
  curls over into a fat, frayed wisp (front view: the curl at x -0.24..-0.30, z 0.96-1.06).
- The face: a dark egg filling the hood's wide opening (0.38 m across, z 0.60 to 0.89), two ember crescents at z
  0.69, 0.16 m apart (hero, 2-turnaround, 4-details 2).
- Inside the cloth there is no body (the card): a slim dark core, seen only through the tears and under the hems.
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Vector

from lib.surface import smooth, v3

PX = 0.0016                          # metres per turnaround pixel


def _unit(a: np.ndarray) -> np.ndarray:
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-12)


def theta_of(p: np.ndarray, yc: np.ndarray | float = 0.0) -> np.ndarray:
    """The angle round the vertical axis (radians): 0 at the front (-Y), +pi/2 at the monster's left (+X)."""
    return np.arctan2(p[:, 0], -(p[:, 1] - yc))


def mirror(p, s: int) -> tuple[float, float, float]:
    return (p[0] * s, p[1], p[2])


# ============================================================================ the hood and the face
H0 = np.array([0.0, 0.03, 0.74])     # the hood's centre (its radial functions start here)
# round 2 (review): a bigger, softer cowl that overhangs the face (its front read as a straight visor from the side)
HOOD_R = {'x': 0.265, 'front': 0.258, 'back': 0.182, 'top': 0.246, 'bottom': 0.2}
HOOD_P = (2.35, 3.0)                 # superellipse powers: a fuller, rounder dome above (no straight visor line), and
                                     # sides that stay upright below its widest part (the cape carries on with no crease)
PEAK_DIR = _unit(np.array([-0.3, -0.1, 0.95]))     # the cowl rises into a soft point up and to its right
PEAK = (0.045, math.radians(34.0), 0.045, math.radians(16.0))   # a broad rise and a sharper point (metres, spread)
# round 3: the face egg set back and reaching lower (the rim overhangs it in profile; the void a full oval, eyes at mid)
F0 = np.array([0.0, 0.008, 0.718])   # the dark face inside: an egg filling the opening
FACE_R = np.array([0.19, 0.18, 0.185])
OPEN_AXIS = _unit(np.array([0.0, -1.0, 0.08]))
OPEN_HALF = {'side': math.radians(46.0), 'top': math.radians(24.0), 'bottom': math.radians(50.0)}
OPEN_W = 0.05                        # the rim's band in units of the opening's angle (the inner wall's steepness)
BRIM = (0.018, math.radians(55.0))   # the brim's extra reach over the face's top, and how far up the dome it fades
COWL = (0.026, math.radians(30.0))   # round 3: the whole rim reaches forward this much (fading over this far), so the cowl
                                     # overhangs the face all round (the face bulged past the rim like a visor)


def _open_frame():
    f = OPEN_AXIS
    ex = np.array([1.0, 0.0, 0.0])
    ez = np.cross(f, ex)
    ez = ez / np.linalg.norm(ez)
    if ez[2] < 0:
        ez = -ez
    return f, ex, ez


def open_coords(d: np.ndarray):
    """(alpha, beta, a_n) per unit direction from H0: the angle from the opening's axis, the angle round it (0 toward
    the monster's left, +pi/2 up) and alpha over the opening's half-angle that way (1 on the rim)."""
    f, ex, ez = _open_frame()
    a = np.arccos(np.clip(d @ f, -1.0, 1.0))
    b = np.arctan2(d @ ez, d @ ex)
    sb, cb = np.sin(b), np.cos(b)
    vert = np.where(sb >= 0, OPEN_HALF['top'], OPEN_HALF['bottom'])
    half = 1.0 / np.sqrt((cb / OPEN_HALF['side']) ** 2 + (sb / vert) ** 2)
    # a torn rim: tatters and notches round the opening (round 2: bolder; hero, 2-turnaround: the brim's frayed edge)
    # (round 3: no fine ripple; it corrugated the deep inner wall into radial ridges, a fur ruff round the face)
    rag = (1.0 + 0.035 * np.sin(7.0 * b + 0.6) + 0.01 * np.sin(17.0 * b + 2.1)
           + 0.05 * np.clip(np.sin(5.0 * b + 1.3), 0, 1) ** 6)
    return a, b, a / (half * rag)


def hood_outer_r(d: np.ndarray) -> np.ndarray:
    """The hood's outer surface along unit directions from H0: a soft egg (fuller in front), the brim reaching over
    the face's top, a point rising toward the tip."""
    rx, rz = HOOD_R['x'], np.where(d[:, 2] >= 0, HOOD_R['top'], HOOD_R['bottom'])
    ry = np.where(d[:, 1] <= 0, HOOD_R['front'], HOOD_R['back'])
    pw = np.where(d[:, 2] >= 0, HOOD_P[0], HOOD_P[1])
    q = np.sqrt((d[:, 0] / rx) ** 2 + (d[:, 1] / ry) ** 2)
    r = 1.0 / (q ** pw + np.abs(d[:, 2] / rz) ** pw) ** (1.0 / pw)
    a, b, an = open_coords(d)
    up = np.clip(np.sin(b), 0.0, 1.0)
    excess = a - a / np.maximum(an, 1e-6)                  # radians outside the rim
    fall = 0.5 + 0.5 * np.cos(np.pi * np.clip(excess / BRIM[1], 0.0, 1.0))
    k = up ** 1.2 * smooth(-0.03, 0.04, excess) * fall
    cowl = COWL[0] * smooth(-0.03, 0.04, excess) * (0.5 + 0.5 * np.cos(np.pi * np.clip(excess / COWL[1], 0.0, 1.0)))
    pk = np.arccos(np.clip(d @ PEAK_DIR, -1.0, 1.0))
    peak = PEAK[0] * np.exp(-(pk / PEAK[1]) ** 2) + PEAK[2] * np.exp(-(pk / PEAK[3]) ** 2)
    return hood_drape(d, r + BRIM[0] * k + cowl + peak)


def drape_z(phi) -> np.ndarray:
    """How low the hood's back hangs over the cape, round the body (phi 0 front): torn into uneven tatters, lowest at
    the back, none at the front (the face and the panels)."""
    a = np.abs(np.angle(np.exp(1j * np.asarray(phi, np.float64))))
    # round 3: long and pointed at the back (down to z ~0.5), short at the sides: no seam running all round
    base = 0.69 - 0.19 * smooth(1.8, math.pi, a) ** 1.4     # a point at the centre back over the cape layers
    tat = (0.04 * np.clip(np.sin(7.0 * phi + 0.8), 0, 1) ** 2 + 0.025 * np.clip(np.sin(13.0 * phi + 2.2), 0, 1) ** 2
           + 0.012 * np.abs(np.sin(29.0 * phi)) ** 3)
    return base - tat


def hood_drape(d: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Round 2 (the hood read as a cap on a lampshade from behind): below its widest part the hood's back and sides
    hang just outside the cape (ashwraith_drape's shroud) down to a torn line, then tuck in under it, so the boundary
    is a ragged hood edge lying on the cape rather than a ring."""
    from monsters.breeds import ashwraith_drape as D
    below = d[:, 2] < 0.0
    if not below.any():
        return r
    p = H0 + d * r[:, None]
    z = p[:, 2]
    phi = np.arctan2(p[:, 0], -(p[:, 1] - D.sh_abyc(z)[2]))
    a = np.abs(np.angle(np.exp(1j * phi)))
    # round 3: lower down it lies over both cape layers (the middle one at +0.016) and follows their folds, or their
    # fold crests poked through it and the boundary read as one level seam where the capes came out
    q = D.shroud_point(phi, z, 0.006 + 0.03 * smooth(0.72, 0.62, z), smooth(0.72, 0.64, z))
    rho_s = np.hypot(q[:, 0], q[:, 1] - H0[1])
    cos_el = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)
    want = np.minimum(rho_s / cos_el, r + 0.12)              # never far out (near the bottom pole cos_el -> 0)
    k = smooth(-0.025, 0.004, z - drape_z(phi)) * smooth(1.05, 1.35, a) * smooth(0.0, -0.16, d[:, 2]) * smooth(0.25, 0.45, cos_el)
    return np.maximum(r, r + (want - r) * k)


def face_r(d: np.ndarray, origin: np.ndarray = H0) -> np.ndarray:
    """Distance from `origin` (inside the face egg) to the face egg's surface along unit directions d."""
    o = (origin - F0) / FACE_R
    u = d / FACE_R
    A = (u * u).sum(1)
    B = 2.0 * (u * o).sum(1)
    Cc = float(o @ o) - 1.0
    return (-B + np.sqrt(np.maximum(B * B - 4 * A * Cc, 0.0))) / (2 * A)


def face_point(p: np.ndarray) -> np.ndarray:
    """Each point moved onto the face egg along the egg's own radius (from F0)."""
    d = _unit(p - F0)
    return F0 + d * face_r(d, F0)[:, None]


def face_normal(p: np.ndarray) -> np.ndarray:
    return _unit((p - F0) / FACE_R ** 2)


def hood_r(d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The closed hood's radius along unit directions from H0, and the 'inside' share (0 on the outer cloth, 1 on the
    face; between: the rim's rolled, torn lip and the inner wall)."""
    ro = hood_outer_r(d)
    rf = face_r(d)
    a, b, an = open_coords(d)
    k = smooth(1.0 + OPEN_W, 1.0 - OPEN_W, an)
    lip = 0.019 * np.exp(-((an - (1.0 + 0.7 * OPEN_W)) / (1.0 * OPEN_W)) ** 2)
    r = ro * (1 - k) + np.minimum(rf, ro) * k + lip * (1 - k)
    return r, k


# ============================================================================ the hood's tip
# from inside the point it rises to its top (x -0.2, z 1.07), then flops forward and to the monster's right and curls
# over and down into a fat wisp (round 2: it curled back like a thin tail, a peg from the three-quarter camera)
HOOD_TIP = [(-0.095, -0.005, 1.025), (-0.145, -0.03, 1.058), (-0.2, -0.065, 1.07), (-0.265, -0.14, 1.0)]
TIP_W = _unit(np.array([-0.55, -0.83, 0.0]))                # the curl's outward direction (its right and forward)
TIP_R = (0.075, 0.026)                                       # the curl's radius at its start and its end
TIP_PHI = (math.radians(135.0), math.radians(135.0 - 370.0))  # the curl's angles in its plane (0 = outward, 90 = up): round
                                                              # 3, a broad cloth tip curling into a spiral (1-hero, 3-faces)
TIP_C = np.array(HOOD_TIP[2]) - TIP_R[0] * (math.cos(TIP_PHI[0]) * TIP_W + math.sin(TIP_PHI[0]) * np.array([0, 0, 1.0]))


# ============================================================================ the dark core (no body: seen through tears)
CORE_Z = np.array([0.30, 0.40, 0.50, 0.60, 0.70])
CORE_A = np.array([0.2, 0.212, 0.2, 0.178, 0.158])
CORE_B = np.array([0.19, 0.2, 0.19, 0.17, 0.155])
CORE_YC = np.array([0.04, 0.032, 0.02, 0.008, 0.0])
CORE_BOTTOM = 0.245                  # its rounded underside's lowest point


def core_abyc(z):
    z = np.asarray(z, np.float64)
    return np.interp(z, CORE_Z, CORE_A), np.interp(z, CORE_Z, CORE_B), np.interp(z, CORE_Z, CORE_YC)


def core_point(th: np.ndarray, z: np.ndarray) -> np.ndarray:
    a, b, yc = core_abyc(z)
    return np.stack([a * np.sin(th), yc - b * np.cos(th), np.broadcast_to(z, np.shape(th))], axis=-1)


def core_outside(p: np.ndarray) -> np.ndarray:
    a, b, yc = core_abyc(np.maximum(p[:, 2], CORE_Z[0]))
    r = np.sqrt((p[:, 0] / a) ** 2 + ((p[:, 1] - yc) / b) ** 2)
    return (r - 1.0) * 0.5 * (a + b)


# ============================================================================ the rig's points
HIP = (0.0, 0.03, 0.56)              # the hover point
CHEST = (0.0, 0.01, 0.985)           # the hood's crown: the top of the squash chain
BASE = (0.0, 0.05, 0.16)             # the hems: its bottom
HEAD_C = (0.0, -0.1, 0.72)
HEAD_R = 0.21
# the little arms: from a shoulder under the collar, down and forward to the mitten clutching the cloak (a pitch up
# lifts the hand up and forward in front of the robe: `arm_pitch`)
ARM = {'shoulder': (0.075, -0.135, 0.6), 'elbow': (0.06, -0.19, 0.545), 'hand': (0.042, -0.234, 0.5)}    # half tucked in the folds

# ============================================================================ the face's places
EYE_X, EYE_Z = 0.08, 0.7
EYE_R = 0.052                        # the patch's reach (the crescent and its halo margin lie inside it)
# the ember crescent (round 2: about 30% thicker, so it survives 64 px): its spine an arc of radius CRES_R whose centre
# sits CRES_DROP below the eye's centre, spanning +-CRES_PHI; CRES_T thick at the middle, tapering to the horns
# polish (round-3 review: filled half-discs read bored): a wider arc, about 20% bigger, 35% as thick as wide, pointed
CRES_R, CRES_DROP, CRES_PHI = 0.05, 0.025, math.radians(64.0)
CRES_T, CRES_TMIN, CRES_MARGIN = 0.031, 0.003, 0.012     # the halo is the patch's margin
EYE_DOME, EYE_SINK = 0.0028, 0.0006


def face_y(x: float, z: float) -> float:
    q = 1.0 - (x / FACE_R[0]) ** 2 - ((z - F0[2]) / FACE_R[2]) ** 2
    return float(F0[1] - FACE_R[1] * math.sqrt(max(q, 0.0)))


def eye_centre(s: int) -> Vector:
    return Vector((EYE_X * s, face_y(EYE_X * s, EYE_Z), EYE_Z))


EYE_C = {s: eye_centre(s) for s in (1, -1)}


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye: the look wraps the egg's curve, mostly ahead."""
    c = EYE_C[s]
    n = Vector(face_normal(np.array([c[:]]))[0])
    look = (n * 0.6 + Vector((0, -1, 0)) * 0.4).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def cres_spine(phi: np.ndarray) -> np.ndarray:
    """The crescent's spine in the eye's plane (x across, y up, metres)."""
    return np.stack([CRES_R * np.sin(phi), -CRES_DROP + CRES_R * np.cos(phi)], axis=-1)


def cres_thick(phi: np.ndarray) -> np.ndarray:
    return CRES_TMIN + (CRES_T - CRES_TMIN) * np.cos(np.clip(phi / CRES_PHI, -1, 1) * np.pi / 2) ** 0.85


def eye_dist(p: np.ndarray) -> np.ndarray:
    return np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
