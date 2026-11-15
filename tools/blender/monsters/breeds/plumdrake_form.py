"""Plumdrake's shape (shared by plumdrake_ultra.py, plumdrake_horns.py and plumdrake_wings.py): the body's rounded parts,
the face's landmarks, the limbs' joints, the tail's points, the fluffy clumps (the ruff, the tail puff, the crest) and the
zone tests the paint, the weights and the scales read.

Measured on chatgpt/monsters/32-plumdrake/2-turnaround.png (front, side, back and wings-spread on one ground line): 543 px
from the ground to the crest's tip = 1.775 m (HEIGHT_UNITS 270: 1.8 x Puddlepup), so 3.27 mm a pixel; the side view's
y = 0 is the legs' axis (its x = 535), the front view's centre its x = 211. The hero (1-hero.png) wins where the views
disagree: the long tail lies on the ground and sweeps round toward the monster's left, its puff standing up beside the
left foot (the turnaround's modelling pose laid it straight back).

Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib.mesh import Part
from lib.surface import norm, smooth, v3
from monsters.breeds import hearthwing_parts as HP

# ============================================================================= the head
HEAD_C = (0.0, -0.11, 1.465)
HEAD_R = (0.2, 0.185, 0.17)            # the cranium's half axes (across, depth, height)
FACE = ((0.0, -0.165, 1.46), (0.17, 0.135, 0.135))      # the face's front under the brows (the eyes sit on it)
# round 2 (review: a pig-nose disc): a long, wide, rounded dragon snout (4-details panel 1), its top sloping gently from
# the brow to a soft nose at the tip, two small nostrils on top; the mouth runs along its sides up into the cheeks
# round 3: one broad, smooth, rounded snout (round 2 read as three stacked bulges: a nose bulb, a sausage upper lip and a
# chin lobe): a bigger snout that takes in the lip, a subtle nose, the lower jaw flowing into it
SNOUT = ((0.0, -0.32, 1.39), (0.118, 0.16, 0.074))
BRIDGE = ((0.0, -0.28, 1.43), (0.075, 0.12, 0.045))
NOSE = ((0.0, -0.43, 1.425), (0.068, 0.045, 0.032))
NOSE_C = (0.0, -0.452, 1.452)
NOSTRIL_DX, NOSTRIL_DZ, NOSTRIL_R = 0.03, 0.0, 0.0072
JOWL = ((0.085, -0.28, 1.372), (0.05, 0.11, 0.05))      # the upper lip along the snout's sides (mirrored; inside the snout)
CHIN = ((0.0, -0.3, 1.33), (0.105, 0.13, 0.055))       # the lower jaw under the smile (flowing into the snout)
JAWSIDE = ((0.1, -0.22, 1.33), (0.068, 0.1, 0.055))    # the jaw's sides back to the corners (mirrored)
CHEEK = ((0.145, -0.17, 1.43), (0.072, 0.072, 0.064))   # soft cheeks below the eyes (mirrored)
BROW = ((0.105, -0.212, 1.592), (0.06, 0.03, 0.017))    # soft brow ridges over the eyes (mirrored)
EAR = {'base': (0.182, -0.06, 1.485), 'dir': (0.85, 0.32, -0.02), 'len': 0.085, 'w': 0.07, 'th': 0.03}   # small pointed ears under the horns
EYE_X, EYE_Z = 0.1, 1.487
EYE_R = 0.054                          # the lens' half width (the front view: 35 px across the white, bigger: big, kind eyes)
EYE_SHAPE = (1.0, 1.06)
EYE_DEPTH = (0.5, 0.14)               # the dome's depth and how far it sits sunk, in EYE_R
BROW_Z = 1.565
# the smile (2-turnaround front and 3-faces neutral): a wide curve from corner to corner, (x, z) on the snout's front
SMILE_W = 0.178                        # the corners' half width
SMILE_Z0 = 1.343                       # the lip line's height at the snout's front
CORNER_Y = -0.19                       # the mouth's corners, under the eyes (round 3: a closed smile curling up into the cheeks)
JAW_HINGE = (0.0, -0.14, 1.37)
JAW_TIP = (0.0, -0.42, 1.3)
FANG_X = 0.074                         # the two little rounded fangs hang from the upper lip here

# ============================================================================= the body (a heavy pear)
CHEST = ((0.0, -0.02, 0.93), (0.31, 0.29, 0.3))
SHOULDER_M = ((0.26, -0.02, 0.96), (0.13, 0.13, 0.13))
BELLY = ((0.0, -0.07, 0.56), (0.35, 0.32, 0.37))
LOWER = ((0.0, 0.02, 0.5), (0.41, 0.35, 0.34))
BACK = ((0.0, 0.07, 0.78), (0.34, 0.28, 0.36))
RUMP = ((0.0, 0.16, 0.39), (0.33, 0.24, 0.22))
NECK = ((0.0, -0.05, 1.06), (0.0, -0.11, 1.38), 0.15)

# the left leg (mirrored): short, thick and sturdy; the crotch at about 0.22 m
LEG_HIP = (0.2, 0.0, 0.42)
KNEE = (0.235, -0.06, 0.25)
ANKLE = (0.245, 0.0, 0.1)
TOE = (0.25, -0.2, 0.035)
FOOT_C = (0.248, -0.04, 0.055)
FOOT_YAW = 8.0                         # the toes turn out a little (the front view)
TOE_DX = (-0.095, 0.0, 0.095)          # three broad toes a foot (the card)
TOE_Y, TOE_Z = -0.14, 0.058
TOE_R = (0.068, 0.085, 0.06)             # round 2: three chunky toes (they read as a pancake with spikes)

# the left arm: short and strong, an A-pose about 40 degrees out (2-turnaround front), the elbow a little bent
SHOULDER = (0.29, -0.03, 0.97)
ELBOW = (0.4, 0.0, 0.83)
WRIST = (0.48, -0.06, 0.72)
HAND = (0.535, -0.13, 0.64)            # the fingertips

# the tail (six bones): from the rump down to the ground, back along it and round toward the monster's left, the tip
# curling up into the puff (1-hero; 2-turnaround side: lying on the ground, about 0.9 m long)
TAIL_PTS = [(0.0, 0.3, 0.37), (0.0, 0.47, 0.2), (0.03, 0.63, 0.118), (0.11, 0.77, 0.097), (0.23, 0.86, 0.1),
            (0.35, 0.9, 0.16), (0.42, 0.9, 0.29)]
TAIL_RAD = [0.2, 0.152, 0.117, 0.096, 0.082, 0.07, 0.062]
PUFF_LEN = 0.2                         # the puff bone, past the tail's tip
PUFF_R = 0.2                           # the puff's core (round 3: its 14 big swirled locks reach about 0.35 m out)


def mirror(p, s: int) -> tuple[float, float, float]:
    return (float(p[0]) * s, float(p[1]), float(p[2]))


def basis_euler(xax, zax) -> tuple[float, float, float]:
    """XYZ Euler degrees turning a part's +X onto `xax` and (as near as it can) its +Z onto `zax`."""
    x = Vector(xax).normalized()
    z = Vector(zax)
    z = (z - x * z.dot(x)).normalized()
    y = z.cross(x)
    e = Matrix((x, y, z)).transposed().to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def puff_axis() -> tuple[np.ndarray, np.ndarray]:
    """(the tail's tip, the puff's direction)."""
    a, b = v3(TAIL_PTS[-2]), v3(TAIL_PTS[-1])
    return b, HP.unit(b - a)


def puff_centre() -> np.ndarray:
    b, d = puff_axis()
    return b + d * 0.05 + v3((0.0, 0.0, 0.07))


# ============================================================================= the eyes
def _front_y(c, r, x: float, z: float) -> float:
    k = 1.0 - (x / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
    return c[1] - r[1] * math.sqrt(k) if k > 0 else 9.0


def head_normal(c) -> Vector:
    c = Vector(c)
    h = Vector(HEAD_C)
    r = HEAD_R
    return Vector(((c.x - h.x) / r[0] ** 2, (c.y - h.y) / r[1] ** 2, (c.z - h.z) / r[2] ** 2)).normalized()


def _eye_centre(s: int) -> Vector:
    y = min(_front_y(HEAD_C, HEAD_R, EYE_X, EYE_Z), _front_y(*FACE, EYE_X, EYE_Z))
    return Vector((EYE_X * s, y - 0.002, EYE_Z))


EYE_C = {s: _eye_centre(s) for s in (1, -1)}


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye: it looks forward and a little out, wrapping the head's curve (the
    reviewers' ask on every breed: the eyes and their highlights read in profile too)."""
    c = EYE_C[s]
    look = (head_normal(c) * 0.52 + Vector((0, -1, 0)) * 0.48).normalized()
    look = (look + Vector((0, 0, 0.04))).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


# ============================================================================= hands and feet
def hand_frame(s: int):
    """The left (s = 1) or right hand: wrist, the hand's direction, across (toward the front) and the palm's normal."""
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
    """(base, tip, radius) of the three fingers and the thumb (four-fingered hands, the card)."""
    w, h, across, palm = hand_frame(s)
    out = []
    base = w + h * 0.065
    for a, ln in ((-26.0, 0.056), (0.0, 0.062), (26.0, 0.056)):      # round 2: bigger fingers (they read as dots)
        r = math.radians(a)
        d = (h * math.cos(r) + across * math.sin(r)).normalized()
        d = (d + palm * 0.3).normalized()            # curled a little toward the palm
        b = base + across * (0.04 * math.sin(r) / 0.44)
        out.append((b, b + d * ln, 0.031))
    tb = w + h * 0.035 + across * 0.05
    td = (across * 0.75 + h * 0.5 + palm * 0.35).normalized()
    out.append((tb, tb + td * 0.046, 0.03))
    return out


def toe_centres(s: int) -> list[Vector]:
    fc = Vector(mirror(FOOT_C, s))
    a = math.radians(FOOT_YAW * s)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for dx in TOE_DX:
        lx, ly = dx * s, (TOE_Y - FOOT_C[1]) + abs(dx) * 0.35
        out.append(Vector((fc.x + lx * ca - ly * sa, fc.y + lx * sa + ly * ca, TOE_Z)))
    return out


def toe_dir(s: int, dx: float) -> Vector:
    a = math.radians(FOOT_YAW * s)
    d = Vector((dx * 0.9 * s, -1.0, 0.0))
    d = Vector((d.x * math.cos(a) - d.y * math.sin(a), d.x * math.sin(a) + d.y * math.cos(a), 0.0)).normalized()
    return d


# ============================================================================= the parts
def _ell(name: str, e, mirror_: bool = False, rot=(0.0, 0.0, 0.0)) -> Part:
    return Part(name, 'sphere', loc=tuple(e[0]), radius=1.0, scale=tuple(e[1]), rot=rot, mirror=mirror_)


def head_parts() -> list[Part]:
    return [
        _ell('cranium', (HEAD_C, HEAD_R)),
        _ell('face', FACE),
        _ell('snout', SNOUT),
        _ell('bridge', BRIDGE),
        _ell('nose', NOSE),
        _ell('jowl', JOWL, True),
        _ell('chin', CHIN),
        _ell('jawside', JAWSIDE, True),
        _ell('cheek', CHEEK, True),
        _ell('brow', BROW, True),
        Part('neck', 'capsule', loc=NECK[0], to=NECK[1], radius=NECK[2]),
    ]


def torso_parts() -> list[Part]:
    return [_ell('chest', CHEST), _ell('shoulder', SHOULDER_M, True), _ell('belly', BELLY), _ell('lower', LOWER),
            _ell('back', BACK), _ell('rump', RUMP)]


def limb_parts() -> list[Part]:
    ps: list[Part] = []
    for s, tag in ((1, ''), (-1, '.R')):
        m = lambda p, s=s: mirror(p, s)
        ps += [
            Part(f'upperarm{tag}', 'tube', loc=m(SHOULDER), to=m(ELBOW), radius=0.094, r2=0.082),
            Part(f'elbow{tag}', 'sphere', loc=m(ELBOW), radius=0.08),
            Part(f'forearm{tag}', 'tube', loc=m(ELBOW), to=m(WRIST), radius=0.079, r2=0.066),
        ]
        w, h, across, palm = hand_frame(s)
        ps.append(Part(f'palm{tag}', 'sphere', loc=tuple(w + h * 0.045), radius=1.0, scale=(0.046, 0.075, 0.07),
                       rot=basis_euler(palm, h)))
        for k, (b, t, r) in enumerate(finger_tips(s)):
            ps.append(Part(f'finger{k}{tag}', 'capsule', loc=tuple(b), to=tuple(t), radius=r))
        ps += [
            Part(f'thigh{tag}', 'sphere', loc=m((0.24, -0.02, 0.32)), radius=1.0, scale=(0.17, 0.18, 0.16)),
            Part(f'shin{tag}', 'tube', loc=m((0.245, -0.04, 0.27)), to=m((0.245, -0.01, 0.12)), radius=0.14, r2=0.135),
            # round 2: the ankle flows into the foot (a ring seam read as a boot)
            Part(f'ankle{tag}', 'sphere', loc=m((0.246, -0.03, 0.105)), radius=1.0, scale=(0.15, 0.165, 0.095)),
            Part(f'heel{tag}', 'sphere', loc=m((0.245, 0.06, 0.07)), radius=1.0, scale=(0.11, 0.105, 0.072)),
            Part(f'foot{tag}', 'sphere', loc=m(FOOT_C), radius=1.0, scale=(0.165, 0.17, 0.065), rot=(0.0, 0.0, FOOT_YAW * s)),
        ]
        for k, t in enumerate(toe_centres(s)):
            ps.append(Part(f'toe{k}{tag}', 'sphere', loc=tuple(t), radius=1.0, scale=TOE_R, rot=(0.0, 0.0, FOOT_YAW * s + TOE_DX[k] * 90 * s)))
    return ps


def tail_parts() -> list[Part]:
    out = []
    for i in range(len(TAIL_PTS) - 1):
        out.append(Part(f'tail{i}', 'tube', loc=TAIL_PTS[i], to=TAIL_PTS[i + 1], radius=TAIL_RAD[i], r2=TAIL_RAD[i + 1]))
    out.append(Part('puffcore', 'sphere', loc=tuple(puff_centre()), radius=PUFF_R))
    return out


# the ruff's core: a soft collar round the neck and over the shoulders (the clumps grow out of it)
RUFF_CORE = [
    ((0.0, -0.24, 1.06), (0.24, 0.15, 0.16)),
    ((0.0, -0.29, 0.96), (0.14, 0.1, 0.09)),
    ((0.2, -0.1, 1.13), (0.14, 0.16, 0.15)),
    ((-0.2, -0.1, 1.13), (0.14, 0.16, 0.15)),
    ((0.0, 0.14, 1.19), (0.26, 0.16, 0.17)),
    ((0.0, 0.2, 1.06), (0.16, 0.1, 0.1)),
    ((0.185, -0.15, 1.31), (0.075, 0.08, 0.085)),
    ((-0.185, -0.15, 1.31), (0.075, 0.08, 0.085)),
]


def ruff_parts() -> list[Part]:
    return [_ell(f'ruffcore{i}', e) for i, e in enumerate(RUFF_CORE)]


def all_parts() -> list[Part]:
    return head_parts() + torso_parts() + limb_parts() + tail_parts() + ruff_parts()


# ============================================================================= signed distances to the parts (approximate)
def _sd_ell(q: np.ndarray, c, r, rot=None) -> np.ndarray:
    q = q - v3(c)
    if rot is not None:
        q = q @ rot
    rr = v3(r)
    k = np.linalg.norm(q / rr, axis=1)
    return (k - 1.0) * float(rr.min())


def _sd_tube(p: np.ndarray, a, b, r1: float, r2: float) -> np.ndarray:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1) - (r1 + (r2 - r1) * t)


def sd_parts(p: np.ndarray, parts: list[Part]) -> np.ndarray:
    """The approximate signed distance (metres, negative inside) to the union of the parts (the mirrored twin is tested
    by mirroring the point, as hearthwing_parts.inside does)."""
    from mathutils import Euler
    d = np.full(len(p), 9.0)
    for pt in parts:
        rot = None
        if pt.kind == 'sphere' and any(abs(a) > 1e-9 for a in pt.rot):
            rot = np.array(Euler([math.radians(a) for a in pt.rot], 'XYZ').to_matrix())
        for side in ((1, -1) if pt.mirror else (1,)):
            q = p if side > 0 else p * v3((-1.0, 1.0, 1.0))
            if pt.kind == 'sphere':
                d = np.minimum(d, _sd_ell(q, pt.loc, tuple(pt.radius * s_ for s_ in pt.scale), rot))
            elif pt.kind in ('capsule', 'tube'):
                r2 = pt.r2 if (pt.kind == 'tube' and pt.r2 is not None) else pt.radius
                d = np.minimum(d, _sd_tube(q, pt.loc, pt.to, pt.radius, r2))
    return d


# ============================================================================= the fluffy clumps (body extras)
def clump_axis(spec: dict, rings: int = 11):
    """A lock of fluff: from `base` (buried `bury` of its length) along `dir`, bending toward `bend_dir` (curl x length
    at the tip) and waving sideways (`wave`), wide along `side` and thin across; returns (centres, X, Y, rx, ry, t)."""
    b = v3(spec['base'])
    d = HP.unit(spec['dir'])
    L = float(spec['len'])
    side = HP.unit(v3(spec.get('side', (1.0, 0.0, 0.0))) - d * (v3(spec.get('side', (1.0, 0.0, 0.0))) @ d))
    bend = HP.unit(v3(spec.get('bend_dir', (0.0, 0.0, -1.0))) - d * (v3(spec.get('bend_dir', (0.0, 0.0, -1.0))) @ d))
    bury = float(spec.get('bury', 0.3))
    t = np.linspace(-bury, 1.0, rings)
    tt = np.clip(t, 0.0, 1.0)
    c = (b[None] + d[None] * (L * t)[:, None] + bend[None] * (spec.get('curl', 0.25) * L * tt ** 2)[:, None]
         + side[None] * (spec.get('wave', 0.0) * L * np.sin(np.pi * tt) * tt)[:, None])
    T, X, Y = HP.side_frames(c, side)
    # a soft lock: full from the root to about half way, then rounding into a short soft point
    pp, qq = spec.get('tip', (1.7, 0.72))
    prof = np.where(t < 0, 1.0, np.clip(1.0 - tt ** pp, 0.0, 1.0) ** qq * (0.86 + 0.14 * np.sin(np.pi * np.clip(tt * 1.6, 0, 1))))
    w, th = float(spec['w']), float(spec['th'])
    return c, X, Y, 0.5 * w * prof, 0.5 * th * np.maximum(prof, 0.0) ** 0.75, t


def clump_object(name: str, spec: dict, rings: int = 11, seg: int = 10) -> bpy.types.Object:
    c, X, Y, rx, ry, _t = clump_axis(spec, rings)
    return HP.loft(name, c[:-1], X[:-1], Y[:-1], np.maximum(rx[:-1], 2e-4), np.maximum(ry[:-1], 2e-4), seg, True, True, c[-1])


def clump_sd(p: np.ndarray, specs: list[dict], rings: int = 11, with_t: bool = False):
    """Approximate signed distance to the union of clumps (each a chain of elliptic sections); with `with_t`, also the
    nearest clump's position 0 (root) .. 1 (tip) along it and that clump's index (-1: none near)."""
    d = np.full(len(p), 9.0)
    tt = np.zeros(len(p))
    which = np.full(len(p), -1, np.int64)
    for k, sp in enumerate(specs):
        c, X, Y, rx, ry, tc = clump_axis(sp, rings)
        lo = c.min(axis=0) - rx.max() - 0.03
        hi = c.max(axis=0) + rx.max() + 0.03
        near = np.all((p > lo) & (p < hi), axis=1)
        if not near.any():
            continue
        q = p[near]
        best = np.full(len(q), 9.0)
        bt = np.zeros(len(q))
        for i in range(len(c) - 1):
            ab = c[i + 1] - c[i]
            u = np.clip(((q - c[i]) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
            m = c[i] + u[:, None] * ab
            r_x = rx[i] + (rx[i + 1] - rx[i]) * u
            r_y = ry[i] + (ry[i + 1] - ry[i]) * u
            dq = q - m
            ex = (dq @ X[i]) / np.maximum(r_x, 1e-4)
            ey = (dq @ Y[i]) / np.maximum(r_y, 1e-4)
            e = np.sqrt(ex * ex + ey * ey)
            dd = (e - 1.0) * np.minimum(r_x, r_y).clip(0.004)
            better = dd < best
            best = np.where(better, dd, best)
            bt = np.where(better, tc[i] + (tc[i + 1] - tc[i]) * u, bt)
        sub = np.nonzero(near)[0]
        win = best < d[sub]
        d[sub[win]] = best[win]
        tt[sub[win]] = bt[win]
        which[sub[win]] = k
    if with_t:
        return d, np.clip(tt, 0.0, 1.0), which
    return d


# The fluff's layouts (the ruff, the tail puff, the crest, the ears): plumdrake_fluff.py.


# ============================================================================= zone helpers
def tail_param(p: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(t 0..1 along the tail, distance to its axis, the tail's radius there)."""
    pts = np.array(TAIL_PTS)
    rad = np.array(TAIL_RAD)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    best_d = np.full(len(p), 9.0)
    best_t = np.zeros(len(p))
    best_r = np.zeros(len(p))
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        u = np.clip(((p - a) @ ab) / float(ab @ ab), 0, 1)
        d = np.linalg.norm(p - (a + u[:, None] * ab), axis=1)
        better = d < best_d
        best_d = np.where(better, d, best_d)
        best_t = np.where(better, cum[i] + u * (cum[i + 1] - cum[i]), best_t)
        best_r = np.where(better, rad[i] + u * (rad[i + 1] - rad[i]), best_r)
    return best_t, best_d, best_r


def seg_dist(p: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / float(ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def core_parts() -> list[Part]:
    """Everything but the ruff's core and the puff's core: the fluff counts as fluff only outside these."""
    return [pt for pt in all_parts() if not pt.name.startswith('ruffcore') and pt.name != 'puffcore']
