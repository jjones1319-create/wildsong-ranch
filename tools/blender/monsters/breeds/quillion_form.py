"""Quillion's shape (shared by quillion_ultra.py, quillion_quills.py and quillion_cape.py): the body's rounded parts, the
face's landmarks, the limbs' joints, the tail's points and the quill zone.

Measured on chatgpt/monsters/10-quillion/2-turnaround.png (front, side and back on one ground line): 676 px from the
ground to the top quill = 0.887 m (HEIGHT_UNITS 135: 0.9 × Puddlepup), so 1.31 mm per pixel; the side view's body
centre line (y = 0) is its x = 780. The hero (1-hero.png) wins where the views disagree: the tail leaves the rump and
its silver blade curves up behind the body to about 0.7 of the height (the back view's modelling pose stood it
straight up the spine to the very top).

Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Matrix, Vector

from lib.mesh import Part
from lib.surface import norm, smooth, v3

# ----------------------------------------------------------------------------- the head (a chibi head, ~35% of the height)
HEAD_C = (0.0, -0.01, 0.655)
HEAD_R = (0.148, 0.142, 0.15)          # half-axes (across, depth, height) of the skull
EYE_R = 0.0355                         # the lens' half-width (front view: 55 px across)
EYE_SHAPE = (1.0, 0.97)
EYE_DEPTH = (0.46, 0.16)               # the dome's depth and how far it sits sunk, in EYE_R
EYE_Z = 0.607                          # the eye line (front view y 330)
EYE_X = 0.084
NOSE_C = (0.0, -0.2, 0.574)
NOSE_R = (0.0185, 0.014, 0.0135)
MUZZLE = ((0.0, -0.148, 0.562), (0.052, 0.058, 0.04))
CHIN = ((0.0, -0.124, 0.52), (0.036, 0.032, 0.024))
# the smile (front view: about ±6 cm at the corners, the middle under the nose): (x, z) on the muzzle's front
SMILE_W = 0.052
JAW_HINGE = (0.0, -0.085, 0.552)
JAW_TIP = (0.0, -0.172, 0.515)
# the small round ears on the upper sides of the head, in front of the quills (side view: y +0.02, z 0.70)
EAR_C = (0.152, 0.008, 0.706)
EAR_N = (0.5, -0.84, 0.2)              # where the ear's cup opens: forward and out (the pink lining shows from the front)
EAR_UP = (0.58, 0.12, 0.8)             # the ear's long axis, standing out of the head
EAR_SIZE = (0.0125, 0.034, 0.038)      # half thickness, half width, half height
BROW_Z = 0.684

# ----------------------------------------------------------------------------- the body
HIP = (0.0, 0.012, 0.2)
CHEST = (0.0, 0.0, 0.43)
# the left arm (mirrored): an A-pose about 40° out (2-turnaround front), elbows a little bent
SHOULDER = (0.12, -0.012, 0.392)
ELBOW = (0.196, 0.004, 0.314)
WRIST = (0.246, -0.02, 0.25)
HAND = (0.273, -0.047, 0.206)          # the fingertips
# the left leg: short and sturdy (the crotch at 0.10 m), the knee a little bent
LEG_HIP = (0.088, 0.012, 0.2)
KNEE = (0.1, -0.03, 0.113)
ANKLE = (0.103, 0.004, 0.052)
TOE = (0.12, -0.098, 0.016)
FOOT_C = (0.107, -0.028, 0.026)
FOOT_YAW = 10.0                        # the toes turn out a little (front view)
TOE_DX = (-0.025, -0.0085, 0.0085, 0.025)   # four toes a foot (4-details 3)

# the tail: from the rump back and a little up to the blade's root, in its ruff of quills; tail.3 is the blade
# the hero: the tail leaves the rump toward the monster's left and the blade rises beside the body (the three-quarter
# view sees it beside the quills, not hidden behind them)
TAIL_POINTS = [(0.0, 0.1, 0.205), (0.055, 0.195, 0.245), (0.125, 0.275, 0.295), (0.26, 0.37, 0.665)]
TAIL_TUBE = ((0.0, 0.07, 0.195), (0.12, 0.27, 0.295), 0.05, 0.03)
# the blade-quill: a scimitar-curved quill in the body's mid-plane (a quadratic Bezier in y, z), from inside the tail's
# end up behind the body; the hero's tip stands at about 0.7 of the height
BLADE_BEZ = ((0.112, 0.255, 0.287), (0.2, 0.4, 0.43), (0.26, 0.37, 0.665))

# the quill mantle: the hedgehog's raised spine-bed over the back of the head and the upper back, so the quills stand
# out from a rounded mass (2-turnaround side: their tips at y ≈ +0.33, the body's back at ≈ +0.15)
MANTLE = ((0.0, 0.075, 0.562), (0.198, 0.18, 0.25))
SRC = (0.0, -0.32, 0.57)               # the quills sweep away from a point in front of the face


def mirror(p, s: int) -> tuple[float, float, float]:
    return (float(p[0]) * s, float(p[1]), float(p[2]))


def basis_euler(xax, zax) -> tuple[float, float, float]:
    """XYZ Euler degrees of the rotation that turns a part's +X onto `xax` and (as near as it can) its +Z onto `zax`."""
    x = Vector(xax).normalized()
    z = Vector(zax)
    z = (z - x * z.dot(x)).normalized()
    y = z.cross(x)
    m = Matrix((x, y, z)).transposed()
    e = m.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


# ----------------------------------------------------------------------------- the eyes
def head_normal(c) -> Vector:
    c = Vector(c)
    h = Vector(HEAD_C)
    r = HEAD_R
    return Vector(((c.x - h.x) / r[0] ** 2, (c.y - h.y) / r[1] ** 2, (c.z - h.z) / r[2] ** 2)).normalized()


FACE = ((0.0, -0.05, 0.596), (0.122, 0.104, 0.1))     # the face's front under the forehead (the eyes sit on it)


def _front_y(c, r, x: float, z: float) -> float:
    k = 1.0 - (x / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
    return c[1] - r[1] * math.sqrt(k) if k > 0 else 9.0


def _eye_centre(s: int) -> Vector:
    """On the face's surface (the frontmost of the skull and the face), so the lens dome stands out of it."""
    y = min(_front_y(HEAD_C, HEAD_R, EYE_X, EYE_Z), _front_y(*FACE, EYE_X, EYE_Z))
    return Vector((EYE_X * s, y - 0.002, EYE_Z))


EYE_C = {s: _eye_centre(s) for s in (1, -1)}


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye (+Z of its dome looks out: forward, a little out and up)."""
    c = EYE_C[s]
    look = (head_normal(c) * 0.55 + Vector((0, -1, 0)) * 0.45).normalized()
    look = (look + Vector((0, 0, 0.03))).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


# ----------------------------------------------------------------------------- the hands and feet
def hand_frame(s: int):
    """The left (s = 1) or right hand: wrist, the hand's direction, across (the fingers' spread, toward the front)
    and the palm's normal."""
    w = Vector(mirror(WRIST, s))
    h = (Vector(mirror(HAND, s)) - w).normalized()
    across = h.cross(Vector((0, 0, 1)))
    if across.y > 0:
        across = -across
    across.normalize()
    palm = across.cross(h).normalized()
    if palm.x * s > 0:
        palm = -palm
    return w, h, across, palm


def finger_tips(s: int) -> list[tuple[Vector, Vector, float]]:
    """(base, tip, radius) of the three fingers and the thumb."""
    w, h, across, palm = hand_frame(s)
    out = []
    base = w + h * 0.04
    for a, ln in ((-20.0, 0.029), (0.0, 0.032), (20.0, 0.029)):
        r = math.radians(a)
        d = (h * math.cos(r) + across * math.sin(r)).normalized()
        d = (d + palm * 0.25).normalized()            # curled a little toward the palm
        b = base + across * (0.015 * math.sin(r) / 0.34)
        out.append((b, b + d * ln, 0.0118))
    tb = w + h * 0.02 + across * 0.023
    td = (across * 0.8 + h * 0.55 + palm * 0.25).normalized()
    out.append((tb, tb + td * 0.024, 0.0115))
    return out


def toe_centres(s: int) -> list[Vector]:
    fc = Vector(mirror(FOOT_C, s))
    a = math.radians(FOOT_YAW * s)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for dx in TOE_DX:
        lx, ly = dx * 1.12 * s, -0.078 + abs(dx) * 0.4
        out.append(Vector((fc.x + lx * ca - ly * sa, fc.y + lx * sa + ly * ca, 0.016)))
    return out


# ----------------------------------------------------------------------------- the parts
def head_parts() -> list[Part]:
    ear_rot = basis_euler(EAR_N, EAR_UP)
    return [
        Part('cranium', 'sphere', loc=HEAD_C, radius=1.0, scale=HEAD_R),
        # the face's front: a broad, gently rounded face under the forehead, the eyes set on it (2-turnaround front)
        Part('face', 'sphere', loc=FACE[0], radius=1.0, scale=FACE[1]),
        # soft full cheeks below the eyes (their fluff is fur cards), not pouches
        Part('cheek', 'sphere', loc=(0.082, -0.07, 0.548), radius=1.0, scale=(0.06, 0.056, 0.048), mirror=True),
        # a short pointed snout: a tapered tube from the face to the nose, its underside the muzzle (2-turnaround side)
        Part('snout', 'tube', loc=(0.0, -0.105, 0.574), to=(0.0, -0.188, 0.568), radius=0.046, r2=0.02),
        Part('muzzle', 'sphere', loc=MUZZLE[0], radius=1.0, scale=MUZZLE[1]),
        Part('nose', 'sphere', loc=NOSE_C, radius=1.0, scale=NOSE_R),
        Part('chin', 'sphere', loc=CHIN[0], radius=1.0, scale=CHIN[1]),
        Part('ear', 'sphere', loc=EAR_C, radius=1.0, scale=EAR_SIZE, rot=ear_rot, mirror=True),
    ]


def torso_parts() -> list[Part]:
    return [
        Part('neck', 'capsule', loc=(0.0, 0.0, 0.42), to=(0.0, -0.01, 0.56), radius=0.086),
        Part('chest', 'sphere', loc=(0.0, -0.008, 0.39), radius=0.125, scale=(1.12, 0.95, 0.86)),
        # the round belly (2-turnaround side: it bulges to y −0.17)
        Part('belly', 'sphere', loc=(0.0, -0.04, 0.255), radius=0.15, scale=(1.0, 0.97, 1.02)),
        Part('pelvis', 'sphere', loc=(0.0, 0.015, 0.185), radius=0.13, scale=(1.04, 0.92, 0.72)),
        Part('rump', 'sphere', loc=(0.0, 0.06, 0.22), radius=0.1, scale=(1.1, 0.9, 0.9)),
        Part('mantle', 'sphere', loc=MANTLE[0], radius=1.0, scale=MANTLE[1]),
        Part('nape', 'sphere', loc=(0.0, 0.05, 0.47), radius=1.0, scale=(0.14, 0.12, 0.1)),
        Part('shoulder', 'sphere', loc=(0.106, -0.006, 0.386), radius=0.06, mirror=True),
    ]


def limb_parts() -> list[Part]:
    ps: list[Part] = []
    for s, tag in ((1, ''), (-1, '.R')):
        m = lambda p, s=s: mirror(p, s)
        ps += [
            Part(f'upperarm{tag}', 'tube', loc=m(SHOULDER), to=m(ELBOW), radius=0.049, r2=0.04),
            Part(f'elbow{tag}', 'sphere', loc=m(ELBOW), radius=0.04),
            Part(f'forearm{tag}', 'tube', loc=m(ELBOW), to=m(WRIST), radius=0.039, r2=0.031),
        ]
        w, h, across, palm = hand_frame(s)
        pc = w + h * 0.02
        ps.append(Part(f'palm{tag}', 'sphere', loc=tuple(pc), radius=1.0, scale=(0.016, 0.031, 0.029),
                       rot=basis_euler(palm, h)))
        for k, (b, t, r) in enumerate(finger_tips(s)):
            ps.append(Part(f'finger{k}{tag}', 'capsule', loc=tuple(b), to=tuple(t), radius=r))
        ps += [
            Part(f'thigh{tag}', 'tube', loc=m(LEG_HIP), to=m(KNEE), radius=0.068, r2=0.052),
            Part(f'knee{tag}', 'sphere', loc=m(KNEE), radius=0.05),
            Part(f'shin{tag}', 'tube', loc=m(KNEE), to=m(ANKLE), radius=0.048, r2=0.039),
            Part(f'heel{tag}', 'sphere', loc=m((0.103, 0.024, 0.032)), radius=0.034),
            Part(f'foot{tag}', 'sphere', loc=m(FOOT_C), radius=1.0, scale=(0.044, 0.08, 0.03), rot=(0.0, 0.0, FOOT_YAW * s)),
        ]
        for k, t in enumerate(toe_centres(s)):
            ps.append(Part(f'toe{k}{tag}', 'sphere', loc=tuple(t), radius=1.0, scale=(0.014, 0.017, 0.015)))
    return ps


def tail_parts() -> list[Part]:
    a, b, r1, r2 = TAIL_TUBE
    return [Part('tail', 'tube', loc=a, to=b, radius=r1, r2=r2)]


def all_parts() -> list[Part]:
    return head_parts() + torso_parts() + limb_parts() + tail_parts()


# ----------------------------------------------------------------------------- the quill zone
# the hairline in the side view: the quills start on the forehead just above the brows' crest, run back over the ears
# (the ears stand in front of them) and down behind the cheeks, the shoulders and the upper back
HAIR_Z = (0.28, 0.33, 0.4, 0.48, 0.56, 0.62, 0.66, 0.685, 0.705, 0.74, 0.95)
HAIR_Y = (0.13, 0.1, 0.07, 0.055, 0.055, 0.04, 0.0, -0.085, -0.15, -0.2, -0.3)


def hairline_y(z: np.ndarray) -> np.ndarray:
    return np.interp(z, HAIR_Z, HAIR_Y)


def ear_dist(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), 9.0)
    for s in (1, -1):
        d = np.minimum(d, np.linalg.norm(p - v3(mirror(EAR_C, s)), axis=1))
    return d


def shoulder_dist(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), 9.0)
    for s in (1, -1):
        d = np.minimum(d, np.linalg.norm(p - v3(mirror(SHOULDER, s)), axis=1))
    return d


def tail_param(p: np.ndarray):
    """(0..1 along the tail tube, distance to its axis)."""
    a, b, _r1, _r2 = TAIL_TUBE
    a, b = v3(a), v3(b)
    ab = b - a
    t = ((p - a) @ ab) / float(ab @ ab)
    tc = np.clip(t, 0, 1)
    d = np.linalg.norm(p - (a + tc[:, None] * ab), axis=1)
    return t, d


def quill_zone(p: np.ndarray, soft: float = 0.012) -> np.ndarray:
    """0..1 where the quill mantle grows (the quills' roots and the chestnut spine-bed under them): behind the hairline,
    above the lower back, off the ears and the shoulders' joints."""
    y, z = p[:, 1], p[:, 2]
    k = smooth(-soft, soft, y - hairline_y(z))
    k = k * smooth(0.27, 0.31, z)
    k = k * smooth(0.055, 0.07, ear_dist(p))
    k = k * smooth(0.075, 0.095, shoulder_dist(p))
    tt, td = tail_param(p)
    k = k * (1.0 - smooth(0.065, 0.05, td) * smooth(-0.05, 0.05, tt))
    return np.clip(k, 0.0, 1.0)


def quill_flow(p: np.ndarray, n: np.ndarray) -> np.ndarray:
    """The tangent the quills sweep along: on the face's side of the head, away from a point in front of the face (up
    and back over the crown, back past the ears); behind it, fanning out from the back's middle as in the back view
    (up and out at the top, out at the sides, down and out low); drooping on the lower back."""
    k = len(p)
    r = norm(p - v3(SRC))
    fan = np.stack([p[:, 0], np.full(k, 0.0), p[:, 2] - 0.74], axis=1)
    small = np.linalg.norm(fan, axis=1) < 1e-4
    fan[small] = np.array([0.0, 0.0, 1.0])
    fan = norm(fan) + v3((0.0, 0.95, 0.0))[None]
    wb = smooth(-0.02, 0.1, p[:, 1])[:, None]
    f = norm(r * (1 - wb) + norm(fan) * wb)
    g = norm(np.tile(v3((0.0, 0.35, -1.0)), (k, 1)))
    wg = (smooth(0.5, 0.33, p[:, 2]) * 0.8)[:, None]
    f = norm(f + g * wg)
    t = f - n * (f * n).sum(1, keepdims=True)
    bad = np.linalg.norm(t, axis=1) < 1e-6
    t[bad] = np.array([0.0, 1.0, 0.0])
    return norm(t)
