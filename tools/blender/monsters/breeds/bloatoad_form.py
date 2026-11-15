"""Bloatoad's form (Art 2.1 Ultra; chatgpt/monsters/21-bloatoad): the proportions measured on 2-turnaround (2.586 mm a
pixel: 1.20 m from the ground to the crown bump's top, HEIGHT_UNITS 180), the body's parts and the masks every other
helper reads (the peach underside, the face, the feet). No Blender imports beyond lib.mesh.Part: pure numpy.

A huge squat toad: a wide pear sitting low (1.33 m across the hind feet, 1.28 m nose to rump), the head the front of
its top with the big half-lidded eyes up on it, a wide smiling mouth, a peach throat and belly, four short bent legs
on big four-toed webbed feet (the hind legs folded into round haunches), three crown bumps (and two little ones).
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from lib.mesh import Part

# ----------------------------------------------------------------------------- the rig's points
HIP = (0.0, 0.02, 0.5)                  # the body's centre (bone `body`)
TOP = (0.0, -0.2, 1.12)                 # the crown: the top of the squash chain
BASE = (0.0, 0.04, 0.02)                # its bottom, on the ground
HEAD_SPLIT = 0.6                        # the face (eyes 0.97 m, mouth 0.83 m) sits above the split (0.68 m)
# polish: the rig's squash chain stands straight up through the old head split (0, -0.104, 0.68), so the head turns
# about the same point; BASE → TOP above stays the skin's axis (bloatoad_skin.trunk_t: the weights' bands unchanged).
# A clip keys a scale in world axes mapped through the bone's rest axes by their absolute values (lib/anim.py
# ClipBuilder.scale), which turns a scale of 1 on a bone tilted 12° into 1.19 along two axes: every clip stood the
# body 19% taller and deeper than its rest (the sidestep's bowling pin, the hit 7% over battle idle)
RIG_BASE = (0.0, -0.104, 0.02)
RIG_TOP = (0.0, -0.104, 1.12)
HEAD_C = (0.0, -0.44, 0.9)
HEAD_R = 0.3
JAW = {'head': (0.0, -0.38, 0.85), 'tail': (0.0, -0.62, 0.81)}      # hinged at the mouth's corners
# round 2: the sac bone sits at the ballooned bubble's centre, so its weights push the throat onto a sphere round it
# round 3: lower, so the full bubble's sphere passes just under the lower lip (no rim, no bucket)
# polish: level (tilted 8°, its every scale came out 1.13 times wider up and down and front to back than asked)
SAC = {'head': (0.0, -0.43, 0.5), 'tail': (0.0, -0.72, 0.5), 'parent': 'head', 'max': 2.4}
SAC_R = 0.38                            # the full bubble's radius round SAC['head']
# round 2: lower, rooted behind the lower lip (the mouth's line is at 0.826 m): it leaves through the opened mouth
# polish: 5 mm higher (a thicker tongue: its belly sits in the pocket's floor, its tip clear of the chin's skin)
TONGUE = [(0.0, -0.32, 0.8), (0.0, -0.4, 0.8), (0.0, -0.48, 0.797), (0.0, -0.545, 0.793)]
# the legs (left; mirrored): a toad's arm (shoulder, elbow out and back, the wrist under it, the hand forward) and a
# folded frog leg (the thigh forward to the knee at the haunch's front, the shin back to the heel, the foot forward)
# round 2: both pairs splayed further out and the base widened about 10% (the review: a low pear, flaring at the base)
LEG_F = {'hip': (0.27, -0.28, 0.52), 'knee': (0.41, -0.37, 0.3), 'ankle': (0.36, -0.45, 0.09), 'toe': (0.37, -0.62, 0.025)}
LEG_B = {'hip': (0.38, 0.34, 0.42), 'knee': (0.59, 0.12, 0.32), 'ankle': (0.58, 0.5, 0.1), 'toe': (0.63, 0.12, 0.025)}
LEGS = [LEG_F, LEG_B]

# ----------------------------------------------------------------------------- the body's volumes (centre, radii)
BELLY = ((0.0, -0.02, 0.4), (0.6, 0.56, 0.4))
BACK = ((0.0, 0.08, 0.5), (0.56, 0.5, 0.47))
NAPE = ((0.0, -0.05, 0.85), (0.36, 0.3, 0.22))
RUMP = ((0.0, 0.2, 0.4), (0.56, 0.42, 0.36))
HEAD = ((0.0, -0.24, 0.84), (0.37, 0.38, 0.29))
# round 3: one volume for the throat and the jowls (two stacked ones met in deep even grooves under the chin)
FRONT = ((0.0, -0.3, 0.6), (0.5, 0.32, 0.37))
SNOUT = ((0.0, -0.47, 0.885), (0.2, 0.16, 0.115))
HAUNCH = ((0.5, 0.31, 0.35), (0.28, 0.3, 0.27))         # left; mirrored
# the crown: one big bump between two smaller, and a little one before and behind (2-turnaround, 4-details panel 5)
CROWN = [((0.0, -0.17, 1.14), 0.058), ((0.115, -0.22, 1.105), 0.035), ((-0.115, -0.22, 1.105), 0.035),
         ((0.0, -0.31, 1.112), 0.027), ((0.0, -0.05, 1.108), 0.027)]

# ----------------------------------------------------------------------------- the eyes (lenses on raised sockets)
EYE_C = {s: np.array((0.22 * s, -0.5, 0.99)) for s in (1, -1)}
EYE_R = 0.075
EYE_SHAPE = (1.0, 0.9)
EYE_DEPTH = (0.6, 0.3)                  # the lens's dome depth and how far its base sits behind the centre (× EYE_R)
EYE_LOOK = (0.45, -1.0, 0.22)
LID = (0.6, -0.05, 1.15, 0.85, 0.72)    # the upper lid's egg in the lens's frame (× EYE_R): centre up, out; radii
LID_EDGE = (0.2, 0.022, 0.0)           # where it crosses the lens: ry = a + b (1 − rx²) + c·rx·s (lens units; top 40% covered)
CLOSED_LASH = -0.62                     # the closed lid's lash line (ry), where a blink squeezes the lens to

# ----------------------------------------------------------------------------- the feet: four webbed toes each
# round 2: broad, flat webbed paddles (about a quarter of the body's width each), fat round pads
TOES_F = {'palm': (0.37, -0.48, 0.035), 'angles': (-70.0, -25.0, 20.0, 64.0), 'len': (0.19, 0.21, 0.21, 0.19), 'yaw': 8.0}
TOES_B = {'palm': (0.6, 0.28, 0.035), 'angles': (-64.0, -26.0, 12.0, 50.0), 'len': (0.19, 0.22, 0.22, 0.19), 'yaw': 14.0}
TOE_R = (0.045, 0.03)                   # round 3: thick at the root, tapering                  # the toe's radius at the palm and at the pad
PAD_R = 0.044                           # the round toe pads


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


def v3(a) -> np.ndarray:
    return np.asarray(a, np.float64)


def smooth(a: float, b: float, x):
    """Smoothstep from a to b (either order), clamped."""
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ell_sdf(p: np.ndarray, centre, radii) -> np.ndarray:
    """An ellipsoid's approximate signed distance (metres; exact on the axes)."""
    r = v3(radii)
    return (np.linalg.norm((p - v3(centre)) / r[None], axis=1) - 1.0) * float(r.min())


def seg_dist(p: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def poly_dist(p: np.ndarray, pts) -> np.ndarray:
    d = np.full(len(p), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        d = np.minimum(d, seg_dist(p, a, b)[0])
    return d


# ----------------------------------------------------------------------------- the feet
def toe_lines(foot: dict, s: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """(palm end, pad centre) of each toe, fanned forward and out from the palm."""
    palm = v3(_m(foot['palm'], s))
    out = []
    for ang, ln in zip(foot['angles'], foot['len']):
        a = math.radians(ang + foot['yaw'])
        d = np.array((math.sin(a) * s, -math.cos(a), 0.0))
        p0 = palm + d * 0.035 + np.array((0.0, 0.0, 0.004))
        pad = palm + d * ln
        pad[2] = PAD_R * 0.78
        out.append((p0, pad))
    return out


def foot_parts(tag: str, s: int, foot: dict) -> list[Part]:
    palm = _m(foot['palm'], s)
    ps = [Part(f'palm{tag}', 'sphere', loc=palm, radius=1.0, scale=(0.12, 0.11, 0.036))]
    lines = toe_lines(foot, s)
    for j, (p0, pad) in enumerate(lines):
        ps.append(Part(f'toe{tag}{j}', 'tube', loc=tuple(p0), to=tuple(pad), radius=TOE_R[0], r2=TOE_R[1]))
        ps.append(Part(f'pad{tag}{j}', 'sphere', loc=tuple(pad), radius=1.0, scale=(PAD_R, PAD_R, PAD_R * 0.8)))
    # the webs: a thin slab between each pair of toes, short of the pads (scalloped between them)
    for j in range(len(lines) - 1):
        a0, a1 = lines[j]
        b0, b1 = lines[j + 1]
        da, db = a1 - a0, b1 - b0
        bis = (da / np.linalg.norm(da) + db / np.linalg.norm(db))
        bis /= np.linalg.norm(bis)
        ln = 0.5 * (np.linalg.norm(da) + np.linalg.norm(db))
        gap = np.linalg.norm(a1 - b1)
        # round 3: the web stretched almost to the pads and level with the toes (seen from above: a fan, not a disc)
        c = (a0 + b0) * 0.5 + bis * ln * 0.52
        c[2] = 0.022
        yaw = math.degrees(math.atan2(-bis[0], bis[1])) + 180.0
        ps.append(Part(f'web{tag}{j}', 'sphere', loc=tuple(c), radius=1.0, scale=(gap * 0.56, ln * 0.6, 0.016), rot=(0.0, 0.0, yaw)))
    return ps


def toe_dist(co: np.ndarray) -> np.ndarray:
    """Distance (metres) to the nearest toe pad's surface (< 0 inside)."""
    d = np.full(len(co), np.inf)
    for s in (1, -1):
        for foot in (TOES_F, TOES_B):
            for _p0, pad in toe_lines(foot, s):
                d = np.minimum(d, ell_sdf(co, pad, (PAD_R, PAD_R, PAD_R * 0.8)))
    return d


def toe_line_dist(co: np.ndarray) -> np.ndarray:
    d = np.full(len(co), np.inf)
    for s in (1, -1):
        for foot in (TOES_F, TOES_B):
            for p0, pad in toe_lines(foot, s):
                d = np.minimum(d, seg_dist(co, p0, pad)[0])
    return d


def leg_dist(co: np.ndarray) -> np.ndarray:
    """Distance to the nearest leg's bone line (hip, knee, ankle)."""
    d = np.full(len(co), np.inf)
    for s in (1, -1):
        for lg in LEGS:
            d = np.minimum(d, poly_dist(co, [_m(lg['hip'], s), _m(lg['knee'], s), _m(lg['ankle'], s)]))
    return d


def arm_dist(co: np.ndarray) -> np.ndarray:
    d = np.full(len(co), np.inf)
    for s in (1, -1):
        lg = LEG_F
        d = np.minimum(d, poly_dist(co, [_m(lg['hip'], s), _m(lg['knee'], s), _m(lg['ankle'], s)]))
    return d


def foot_mask(co: np.ndarray) -> np.ndarray:
    """0..1 on the feet: the palms, the toes and the webs (low and near a palm)."""
    m = np.zeros(len(co))
    for s in (1, -1):
        for foot in (TOES_F, TOES_B):
            palm = v3(_m(foot['palm'], s))
            r = np.linalg.norm((co - palm)[:, :2], axis=1)
            m = np.maximum(m, smooth(max(foot['len']) + 0.05, max(foot['len']) + 0.01, r) * smooth(0.075, 0.05, co[:, 2]))
    return m


# ----------------------------------------------------------------------------- the eyes' frame
def eye_frame(s: int):
    c = EYE_C[s]
    look = np.array((EYE_LOOK[0] * s, EYE_LOOK[1], EYE_LOOK[2]))
    look /= np.linalg.norm(look)
    xax = np.cross(np.array((0.0, 0.0, 1.0)), look)
    xax /= np.linalg.norm(xax)
    yax = np.cross(look, xax)
    yax /= np.linalg.norm(yax)
    return c, xax, yax, look


def lid_edge(rx: np.ndarray, s: int) -> np.ndarray:
    r = np.clip(rx, -1.2, 1.2)
    return LID_EDGE[0] + LID_EDGE[1] * (1.0 - r * r) + LID_EDGE[2] * r * s


def eye_coords(co: np.ndarray, s: int):
    """Each point in the lens's frame: (rx, ry) in lens units, ze metres along the look from the lens's base."""
    c, xax, yax, look = eye_frame(s)
    c0 = c - look * (EYE_R * EYE_DEPTH[1])
    q = co - c0
    return (q @ xax) / (EYE_R * EYE_SHAPE[0]), (q @ yax) / (EYE_R * EYE_SHAPE[1]), q @ look


def lens_ze(rx: np.ndarray, ry: np.ndarray) -> np.ndarray:
    """The lens's front surface (metres along the look from its base) over (rx, ry)."""
    return EYE_DEPTH[0] * EYE_R * np.sqrt(np.clip(1.0 - rx * rx - ry * ry, 0.0, 1.0))


def eye_parts() -> list[Part]:
    """Each eye: the eyeball under the lens (the lens's own shape, 3 mm smaller: the closed lid a blink shows), and the
    heavy upper lid, an egg over its top (LID, in the lens's frame) whose front stands 1-1.5 cm proud of the lens and
    whose lower surface crosses the lens at the lash line (LID_EDGE fits that crossing)."""
    ps = []
    for tag, s in (('L', 1), ('R', -1)):
        c, xax, yax, look = eye_frame(s)
        m = np.stack([xax, yax, look], axis=1)
        e = _euler_xyz(m)
        c0 = c - look * (EYE_R * EYE_DEPTH[1])
        ps.append(Part(f'eyeball{tag}', 'sphere', loc=tuple(c0), radius=1.0, rot=e,
                       scale=(EYE_R * EYE_SHAPE[0] - 0.003, EYE_R * EYE_SHAPE[1] - 0.003, EYE_R * EYE_DEPTH[0] - 0.003)))
        yc, zc, ax, ay, az = LID
        ps.append(Part(f'lid{tag}', 'sphere', loc=tuple(c0 + yax * (EYE_R * yc) + look * (EYE_R * zc)), radius=1.0, rot=e,
                       scale=(EYE_R * ax, EYE_R * ay, EYE_R * az)))
    return ps


def _euler_xyz(m: np.ndarray) -> tuple[float, float, float]:
    """XYZ Euler degrees of a rotation matrix (columns = the rotated x, y, z axes)."""
    sy = -m[2, 0]
    y = math.asin(max(-1.0, min(1.0, sy)))
    x = math.atan2(m[2, 1], m[2, 2])
    z = math.atan2(m[1, 0], m[0, 0])
    return (math.degrees(x), math.degrees(y), math.degrees(z))


# ----------------------------------------------------------------------------- all the parts
def _ell(name: str, spec, mirror: bool = False, rot=(0.0, 0.0, 0.0)) -> Part:
    c, r = spec
    return Part(name, 'sphere', loc=c, radius=1.0, scale=r, mirror=mirror, rot=rot)


def all_parts() -> list[Part]:
    ps = [_ell('belly', BELLY), _ell('back', BACK), _ell('rump', RUMP), _ell('head', HEAD), _ell('nape', NAPE), _ell('front', FRONT),
          _ell('snout', SNOUT), _ell('haunch', HAUNCH, mirror=True)]
    ps += [Part(f'crown{k}', 'sphere', loc=c, radius=1.0, scale=(r, r, r * 0.95)) for k, (c, r) in enumerate(CROWN)]
    ps += eye_parts()
    for tag, s in (('L', 1), ('R', -1)):
        f = LEG_F
        ps.append(Part(f'arm{tag}', 'tube', loc=_m(f['hip'], s), to=_m(f['knee'], s), radius=0.13, r2=0.115))
        ps.append(Part(f'fore{tag}', 'tube', loc=_m(f['knee'], s), to=_m(f['ankle'], s), radius=0.115, r2=0.092))
        b = LEG_B
        ps.append(Part(f'thigh{tag}', 'tube', loc=_m(b['hip'], s), to=_m(b['knee'], s), radius=0.13, r2=0.11))
        ps.append(Part(f'shin{tag}', 'tube', loc=_m(b['knee'], s), to=_m(b['ankle'], s), radius=0.1, r2=0.075))
        ps.append(Part(f'heel{tag}', 'tube', loc=_m(b['ankle'], s), to=_m(TOES_B['palm'], s), radius=0.065, r2=0.05))
        ps.append(Part(f'wrist{tag}', 'tube', loc=_m(f['ankle'], s), to=_m(TOES_F['palm'], s), radius=0.075, r2=0.06))
        ps += foot_parts(f'F{tag}', s, TOES_F) + foot_parts(f'B{tag}', s, TOES_B)
    return ps
