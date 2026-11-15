"""Gloomgrin's shape (shared by gloomgrin_ultra.py and its helpers): the body's rounded parts, the ear slabs, the face's
landmarks, the limbs' joints, the tail's curl, the wings, and the masks the carving, the paint and the weights share.

Measured on chatgpt/monsters/13-gloomgrin/2-turnaround.png (front, side, back on one ground line, y 778): 590 px from the
ground to the crest = 0.986 m (HEIGHT_UNITS 150: 1 × Puddlepup standing), so 1.67 mm per pixel; the front view's
mid-line is its x = 300, the side view's body axis its x = 815. The hero (1-hero.png) wins where the views disagree: the
tail curls out toward the monster's LEFT and up into its arrowhead (the back view's modelling pose curled it right).

A squat gargoyle imp: a big round head (about 40% of the height) with wide jowls and a wide grin, big bat ears out to the
sides, stubby horns, round shoulders, long arms with big clawed hands, short thick legs on big three-toed feet.

Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib.mesh import Part
from lib.surface import smooth, v3

# ----------------------------------------------------------------------------- the head
CRANIUM = ((0.0, -0.045, 0.795), (0.18, 0.165, 0.17))          # top 0.965 (front view y 207, with its plates)
FACE = ((0.0, -0.08, 0.672), (0.205, 0.125, 0.112))           # the wide jowls of the grin, pulled back (rounds 2-3)
MUZZLE = ((0.0, -0.19, 0.672), (0.112, 0.088, 0.07))          # round 3: a thick rounded pug muzzle
BRIDGE = ((0.0, -0.212, 0.742), (0.034, 0.042, 0.036))        # round 3: the snout's top runs up between the eyes (no flat bill)
CHIN = ((0.0, -0.18, 0.616), (0.112, 0.096, 0.05))             # round 3: the lower lip as far forward as the teeth (they sit behind it)
NOSE = ((0.0, -0.268, 0.708), (0.034, 0.025, 0.025))          # a round nose at the snout's tip (side view y −0.289)
NOSE_BLOCK = {'c': (0.0, -0.272, 0.712), 'half': (0.033, 0.022, 0.024), 'taper': 0.55}   # polish: a rounded triangle
CHEEK = ((0.172, -0.072, 0.70), (0.055, 0.055, 0.05))         # rounds 2-3: back, so the whole eye shows in profile
OCCIPUT = ((0.0, 0.035, 0.785), (0.165, 0.11, 0.15))          # the back of the skull (side view x 880: y +0.11)
BROW = {'c': (0.106, -0.18, 0.818), 'half': (0.06, 0.026, 0.021), 'rot': (8.0, -14.0, 16.0)}
# round 3 (cheeky): the left brow raised and tilted more than the right (one flat bar read as manic)
BROW_SIDE = {1: {'dz': 0.016, 'tilt': -34.0}, -1: {'dz': 0.0, 'tilt': -26.0}}   # round 2: higher, less overhang   # inner end low (cheeky)

EYE_X, EYE_Z = 0.103, 0.742                                    # front view (245 / 357, 340); polish: 20% bigger eyes
EYE_R = 0.055
EYE_SHAPE = (1.0, 1.0)
EYE_DEPTH = (0.62, 0.12)                                        # the lens dome's depth and how far it sits sunk (EYE_R)

# the grin: an angle round a vertical axis behind the face (0 straight ahead, + toward the monster's left)
MOUTH_AXIS_Y = -0.05
MOUTH_TH = [0.0, 12.0, 24.0, 33.0, 41.0, 47.0, 53.0]
MOUTH_Z = [0.646, 0.649, 0.658, 0.671, 0.688, 0.708, 0.732]    # polish: a wider crescent, the corners curled up ~30 degrees
MOUTH_OPEN = [0.046, 0.045, 0.041, 0.033, 0.022, 0.01, 0.0]  # the grin's gap (upper lip to lower lip) per angle
MOUTH_UP = 0.7                                                 # share of the gap above the mouth line
UPPER_TEETH = (5.0, 15.0, 25.0)                                # round 2: six big square upper teeth (mirrored), degrees
LOWER_TEETH = ()
TOOTH_STEP = 10.0
FANG_TH = 34.5                                                 # an upper fang at each end of the row, pointing down
MOUTH_DEPTH = 0.022                                            # how deep the grin's gap is carved (the teeth sit in it)

# ----------------------------------------------------------------------------- the ears (bat ears, every picture)
# round 3: tilted up about 30 degrees and cupped deeper, a thick rim (clear of the wings at 64 px)
EAR = {'root': (0.158, -0.012, 0.81), 'tip': (0.318, 0.012, 0.985), 'normal': (0.55, -0.8, 0.2),
       'half_width': 0.085, 'thick': (0.022, 0.012), 'cup': 0.03, 'skew': -0.26, 'curl': 0.016}

# ----------------------------------------------------------------------------- the body
NECK = ((0.0, 0.015, 0.50), (0.0, -0.025, 0.64), 0.112)
CHEST = ((0.0, -0.005, 0.44), (0.15, 0.135, 0.135))
HUMP = ((0.0, 0.045, 0.50), (0.165, 0.105, 0.10))              # round-shouldered: the upper back
BELLY = ((0.0, -0.02, 0.31), (0.135, 0.125, 0.125))
PELVIS = ((0.0, 0.02, 0.22), (0.145, 0.12, 0.09))               # the crotch at 0.13 (front view y 700)
RUMP = ((0.0, 0.075, 0.25), (0.12, 0.08, 0.085))
SHOULDER = ((0.185, -0.015, 0.505), 0.072)                       # the round shoulder caps (front view ±0.25)

# the left arm (mirrored): an A-pose about 35° out and 25° forward (2-turnaround front and side), elbows a little bent
ARM = {'shoulder': (0.185, -0.015, 0.515), 'elbow': (0.29, -0.085, 0.40), 'wrist': (0.337, -0.143, 0.326),
       'hand': (0.372, -0.214, 0.238)}           # round 2: forearm and hand about 12% shorter (to the hips)
ARM_R = (0.058, 0.052, 0.064, 0.056)                               # upper arm (root, elbow), forearm (elbow, wrist)
FINGER_SPREAD = (-24.0, 0.0, 24.0)                               # three fingers and a thumb (4-details 3)
FINGER_LEN = (0.055, 0.062, 0.055)
FINGER_R = (0.024, 0.019)

# the left leg: short and thick, on a big three-toed foot turned a little out (2-turnaround front and side)
LEG = {'hip': (0.11, 0.02, 0.24), 'knee': (0.165, -0.04, 0.14), 'ankle': (0.19, 0.02, 0.075), 'toe': (0.205, -0.165, 0.022)}
THIGH = ((0.155, 0.015, 0.215), (0.082, 0.094, 0.09))
SHIN_R = (0.052, 0.047)
FOOT = ((0.19, -0.035, 0.043), (0.07, 0.105, 0.043))
HEEL = ((0.19, 0.055, 0.05), 0.047)
FOOT_YAW = 12.0
TOE_DX = (-0.045, 0.0, 0.045)
TOE = {'y0': -0.065, 'y1': -0.142, 'z0': 0.036, 'z1': 0.029, 'r': (0.031, 0.026), 'splay': 1.25}

# the tail: down from the rump, back along the ground, round toward the monster's left and up into the arrowhead
TAIL = [(0.0, 0.10, 0.26), (0.018, 0.19, 0.19), (0.06, 0.262, 0.128), (0.135, 0.31, 0.1), (0.215, 0.33, 0.112),
        (0.278, 0.33, 0.158), (0.302, 0.318, 0.215)]
TAIL_R = [0.062, 0.052, 0.044, 0.038, 0.033, 0.029, 0.026]
ARROW = {'up': (0.08, -0.03, 1.0), 'face': (0.6, -0.8, 0.0), 'len': 0.175, 'width': 0.14, 'thick': 0.062, 'sides': 12}

# the wings: small bat wings folded half open behind the shoulders (the rest pose: 2-turnaround, 1-hero), two fingers
# round 2: mounted higher (the wrist near ear height, 4-details panel 4: three fingers, a scallop between each pair)
WINGS = {'parent': 'chest', 'name': 'wing', 'scallop': 0.24,
         'shoulder': (0.085, 0.06, 0.635), 'elbow': (0.165, 0.14, 0.745), 'wrist': (0.29, 0.18, 0.86),
         'fingers': [(0.53, 0.22, 0.69), (0.45, 0.24, 0.53), (0.33, 0.245, 0.48)], 'attach': (0.12, 0.08, 0.47),
         'spread': {'elbow': (0.3, 0.07, 0.8), 'wrist': (0.52, 0.09, 0.92),
                    'fingers': [(0.95, 0.13, 0.78), (0.82, 0.17, 0.5), (0.62, 0.19, 0.38)]}}
WING_R = {'arm': (0.034, 0.028, 0.024), 'finger': (0.017, 0.0075)}

# ----------------------------------------------------------------------------- the rig
HIP = (0.0, 0.02, 0.24)
CHEST_PT = (0.0, 0.0, 0.565)
HEAD_BASE = (0.0, -0.025, 0.625)
RIG_HEAD_C = (0.0, -0.07, 0.775)
RIG_HEAD_R = 0.19


def mirror(p, s: int) -> tuple[float, float, float]:
    return (float(p[0]) * s, float(p[1]), float(p[2]))


def unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def basis_euler(xax, zax) -> tuple[float, float, float]:
    """XYZ Euler degrees of the rotation that turns a part's +X onto `xax` and (as near as it can) its +Z onto `zax`."""
    x = Vector(xax).normalized()
    z = Vector(zax)
    z = (z - x * z.dot(x)).normalized()
    y = z.cross(x)
    e = Matrix((x, y, z)).transposed().to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def ell_sdf(p: np.ndarray, centre, radii) -> np.ndarray:
    r = v3(radii)
    return (np.linalg.norm((p - v3(centre)) / r[None], axis=1) - 1.0) * float(r.min())


def seg_dist(p: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a[None] + t[:, None] * ab[None]), axis=1), t


# ----------------------------------------------------------------------------- the hands and feet
def hand_frame(s: int):
    """The left (s = 1) or right hand: wrist, the hand's direction, across (the fingers' spread: forward and in) and
    the palm's normal (toward the body)."""
    w = v3(mirror(ARM['wrist'], s))
    h = unit(v3(mirror(ARM['hand'], s)) - w)
    across = np.cross(h, (0.0, 0.0, 1.0))
    if across[1] > 0:
        across = -across
    across = unit(across)
    palm = unit(np.cross(across, h))
    if palm[0] * s > 0:
        palm = -palm
    return w, h, across, palm


def fingers(s: int) -> list[tuple[np.ndarray, np.ndarray, float, float]]:
    """(knuckle, tip, root radius, tip radius) of the three fingers and the thumb, curled a little toward the palm."""
    w, h, across, palm = hand_frame(s)
    L = float(np.linalg.norm(v3(mirror(ARM['hand'], s)) - w))
    out = []
    base = w + h * (0.42 * L)
    for a, ln in zip(FINGER_SPREAD, FINGER_LEN):
        r = math.radians(a)
        d = unit(h * math.cos(r) + across * math.sin(r) + palm * 0.28)
        b = base + across * (0.026 * math.sin(r) / math.sin(math.radians(24.0)))
        out.append((b, b + d * ln, FINGER_R[0], FINGER_R[1]))
    tb = w + h * (0.18 * L) + across * 0.03 + palm * 0.012
    td = unit(across * 0.75 + h * 0.6 + palm * 0.35)
    out.append((tb, tb + td * 0.042, 0.021, 0.0175))
    return out


def palm_part(s: int) -> Part:
    w, h, across, palm = hand_frame(s)
    L = float(np.linalg.norm(v3(mirror(ARM['hand'], s)) - w))
    c = w + h * (0.3 * L)
    rot = basis_euler(Vector(h), Vector(palm))
    return Part(f'palm{s}', 'sphere', loc=tuple(map(float, c)), radius=1.0, scale=(0.056, 0.05, 0.033), rot=rot)


def foot_rot(p: np.ndarray, s: int) -> np.ndarray:
    """A point in the left foot's own plan (x, y about the foot's centre) turned out by FOOT_YAW and mirrored."""
    a = math.radians(FOOT_YAW)
    ca, sa = math.cos(a), math.sin(a)
    x, y = p[0], p[1]
    xr, yr = x * ca - y * sa, x * sa + y * ca
    fc = FOOT[0]
    return v3(((fc[0] + xr) * s, fc[1] + yr, p[2]))


def toes(s: int) -> list[tuple[np.ndarray, np.ndarray, float, float]]:
    """(root, tip, root radius, tip radius) of the three toes, splayed, in the foot's turned-out frame."""
    out = []
    for dx in TOE_DX:
        a = foot_rot((dx, TOE['y0'] - FOOT[0][1], TOE['z0']), s)
        b = foot_rot((dx * TOE['splay'], TOE['y1'] - FOOT[0][1] - 0.012 * (dx == 0.0), TOE['z1']), s)
        out.append((a, b, TOE['r'][0], TOE['r'][1]))
    return out


# ----------------------------------------------------------------------------- the ear slabs
def ear_frame(s: int):
    """root, tip, along A (root → tip), across B (toward the upper edge), the lining's normal N (forward and out)."""
    root, tip = v3(mirror(EAR['root'], s)), v3(mirror(EAR['tip'], s))
    A = unit(tip - root)
    n0 = v3(mirror(EAR['normal'], s))
    N = unit(n0 - A * float(n0 @ A))
    B = np.cross(N, A)
    if B[2] < 0:
        B = -B
    return root, tip, A, B, N


def ear_width(u: np.ndarray) -> np.ndarray:
    """The ear's half width along it (0 at the buried root … 1 at the tip), as a share of half_width."""
    u = np.clip(u, 0.0, 1.0)
    return np.clip(u / 0.1, 0.0, 1.0) ** 0.5 * (1.0 - u) ** 0.85 * (0.85 + 0.35 * np.sin(np.pi * np.clip(u * 1.4, 0, 1)))


def ear_point(s: int, u, cphi, sphi) -> np.ndarray:
    """The slab's surface at (u along, the cross-section's angle as cos/sin) for side s: a leaf with a rounded rim,
    cupped (the lining concave), the lower edge curving more than the upper, the tip bent back a little."""
    root, tip, A, B, N = ear_frame(s)
    L = float(np.linalg.norm(tip - root))
    u = np.asarray(u, np.float64)
    W = EAR['half_width'] * ear_width(u)
    T = EAR['thick'][0] * (1 - u) + EAR['thick'][1] * u
    across = W * (cphi + EAR['skew'] * np.sin(np.pi * u) * (1.0 - 0.0 * u))
    thick = sphi * T
    cup = -EAR['cup'] * (1.0 - cphi ** 2) * np.sin(np.pi * np.clip(u, 0, 1)) ** 0.7
    curl = -EAR['curl'] * u ** 3
    return (root[None] + A[None] * (u * L)[:, None] + B[None] * across[:, None] + N[None] * (thick + cup + curl)[:, None])


def ear_slab(name: str, s: int, seg: int = 64) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    co = np.array([v.co[:] for v in bm.verts])
    # the sphere's x is the ear's length (−1 the root, +1 the tip); (y, z) round the ring is the cross-section's angle
    x = co[:, 0]
    rr = np.sqrt(np.maximum(1.0 - x * x, 1e-12))
    cphi = np.clip(co[:, 1] / rr, -1, 1)
    sphi = np.clip(co[:, 2] / rr, -1, 1)
    pole = rr < 1e-4
    cphi[pole] = 0.0
    sphi[pole] = 0.0
    p = ear_point(s, (x + 1.0) * 0.5, cphi, sphi)
    for v, q in zip(bm.verts, p):
        v.co = Vector(tuple(map(float, q)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def ear_coords(p: np.ndarray, s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(u along, across in half widths, the offset along the lining's normal in metres) of points against side s's ear."""
    root, tip, A, B, N = ear_frame(s)
    L = float(np.linalg.norm(tip - root))
    q = p - root[None]
    u = (q @ A) / L
    W = EAR['half_width'] * np.maximum(ear_width(u), 1e-3)
    acr = (q @ B) / W - EAR['skew'] * np.sin(np.pi * np.clip(u, 0, 1))
    off = q @ N + EAR['cup'] * (1.0 - np.clip(acr, -1, 1) ** 2) * np.sin(np.pi * np.clip(u, 0, 1)) ** 0.7 + EAR['curl'] * np.clip(u, 0, 1) ** 3
    return u, acr, off


def ear_mask(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(on an ear slab, beyond the head; which side) per point."""
    on = np.zeros(len(p), bool)
    side = np.zeros(len(p))
    for s in (1, -1):
        u, acr, off = ear_coords(p, s)
        m = (u > 0.12) & (u < 1.06) & (np.abs(acr) < 1.25) & (np.abs(off) < 0.03) & (np.sign(p[:, 0]) == s)
        m &= head_sdf(p) > -0.004
        on |= m
        side = np.where(m, s, side)
    return on, side


# ----------------------------------------------------------------------------- shared masks
def head_sdf(p: np.ndarray) -> np.ndarray:
    """< 0 inside the head's rounded parts (the cranium, the face, the muzzle, the chin, the cheeks, the occiput)."""
    d = ell_sdf(p, *CRANIUM)
    for spec in (FACE, MUZZLE, CHIN, OCCIPUT, BRIDGE, NOSE):
        d = np.minimum(d, ell_sdf(p, *spec))
    for s in (1, -1):
        d = np.minimum(d, ell_sdf(p, mirror(CHEEK[0], s), CHEEK[1]))
    return d


def mouth_theta(p: np.ndarray) -> np.ndarray:
    return np.degrees(np.arctan2(p[:, 0], -(p[:, 1] - MOUTH_AXIS_Y)))


def mouth_z(th: np.ndarray) -> np.ndarray:
    return np.interp(np.abs(th), MOUTH_TH, MOUTH_Z)


def mouth_gap(th: np.ndarray) -> np.ndarray:
    return np.interp(np.abs(th), MOUTH_TH, MOUTH_OPEN)


def light_face_sdf(p: np.ndarray) -> np.ndarray:
    """< 0 on the lighter stone of the face: the muzzle, the lower cheeks round the grin and the chin (2-turnaround
    front: the forehead, the brows and the outer cheeks are charcoal plates)."""
    d = ell_sdf(p, (0.0, -0.21, 0.648), (0.188, 0.14, 0.098))
    d = np.maximum(d, p[:, 1] + 0.135)
    return d


def finger_dist(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), 9.0)
    for s in (1, -1):
        for a, b, r0, r1 in fingers(s):
            dd, t = seg_dist(p, a, b)
            d = np.minimum(d, dd - (r0 + (r1 - r0) * t))
    return d


def toe_dist(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), 9.0)
    for s in (1, -1):
        for a, b, r0, r1 in toes(s):
            dd, t = seg_dist(p, a, b)
            d = np.minimum(d, dd - (r0 + (r1 - r0) * t))
    return d


def arm_dist(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), 9.0)
    for s in (1, -1):
        a = [v3(mirror(ARM[k], s)) for k in ('shoulder', 'elbow', 'wrist', 'hand')]
        for x, y in zip(a[:-1], a[1:]):
            d = np.minimum(d, seg_dist(p, x, y)[0])
    return d


def leg_dist(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), 9.0)
    for s in (1, -1):
        a = [v3(mirror(LEG[k], s)) for k in ('hip', 'knee', 'ankle')]
        for x, y in zip(a[:-1], a[1:]):
            d = np.minimum(d, seg_dist(p, x, y)[0])
    return d


def tail_param(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(t along the tail 0 root … 1 tip, distance to its axis minus its radius) per point."""
    pts = np.array(TAIL, np.float64)
    seg = pts[1:] - pts[:-1]
    lens = np.linalg.norm(seg, axis=1)
    start = np.concatenate([[0.0], np.cumsum(lens)[:-1]]) / lens.sum()
    best = np.full(len(p), np.inf)
    bt = np.zeros(len(p))
    for i in range(len(seg)):
        u = np.clip(((p - pts[i]) @ seg[i]) / (lens[i] ** 2), 0.0, 1.0)
        q = pts[i] + u[:, None] * seg[i]
        r = TAIL_R[i] + (TAIL_R[i + 1] - TAIL_R[i]) * u
        d = np.linalg.norm(p - q, axis=1) - r
        better = d < best
        best = np.where(better, d, best)
        bt = np.where(better, start[i] + u * lens[i] / lens.sum(), bt)
    return bt, best


def belly_sdf(p: np.ndarray) -> np.ndarray:
    """< 0 on the lighter chevron plates down the chest and belly (2-turnaround front), seen from the front."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    zc = 0.33
    hw = 0.108 - 0.03 * smooth(0.25, 0.14, z) - 0.025 * smooth(0.42, 0.53, z)
    r = (np.abs(x) / np.maximum(hw, 1e-3)) ** 2.4 + (np.abs(z - zc) / 0.205) ** 2.4
    d = (r ** (1 / 2.4) - 1.0) * 0.1
    return np.where(y < -0.02, d, 0.05)


def sole_mask(p: np.ndarray, n: np.ndarray | None = None) -> np.ndarray:
    m = p[:, 2] < 0.006
    if n is not None:
        m |= (n[:, 2] < -0.6) & (p[:, 2] < 0.03)
    return m


# ----------------------------------------------------------------------------- the parts
def head_parts() -> list[Part]:
    return [
        Part('cranium', 'sphere', loc=CRANIUM[0], radius=1.0, scale=CRANIUM[1]),
        Part('face', 'sphere', loc=FACE[0], radius=1.0, scale=FACE[1]),
        Part('muzzle', 'sphere', loc=MUZZLE[0], radius=1.0, scale=MUZZLE[1]),
        Part('chin', 'sphere', loc=CHIN[0], radius=1.0, scale=CHIN[1]),
        Part('bridge', 'sphere', loc=BRIDGE[0], radius=1.0, scale=BRIDGE[1]),
        Part('occiput', 'sphere', loc=OCCIPUT[0], radius=1.0, scale=OCCIPUT[1]),
        Part('cheek', 'sphere', loc=CHEEK[0], radius=1.0, scale=CHEEK[1], mirror=True),
    ]


def torso_parts() -> list[Part]:
    return [
        Part('neck', 'capsule', loc=NECK[0], to=NECK[1], radius=NECK[2]),
        Part('chest', 'sphere', loc=CHEST[0], radius=1.0, scale=CHEST[1]),
        Part('hump', 'sphere', loc=HUMP[0], radius=1.0, scale=HUMP[1]),
        Part('belly', 'sphere', loc=BELLY[0], radius=1.0, scale=BELLY[1]),
        Part('pelvis', 'sphere', loc=PELVIS[0], radius=1.0, scale=PELVIS[1]),
        Part('rump', 'sphere', loc=RUMP[0], radius=1.0, scale=RUMP[1]),
        Part('shoulder', 'sphere', loc=SHOULDER[0], radius=SHOULDER[1], mirror=True),
    ]


def limb_parts() -> list[Part]:
    ps: list[Part] = []
    for s, tag in ((1, 'L'), (-1, 'R')):
        a = {k: mirror(v, s) for k, v in ARM.items()}
        ps += [
            Part(f'upperarm{tag}', 'tube', loc=a['shoulder'], to=a['elbow'], radius=ARM_R[0], r2=ARM_R[1]),
            Part(f'forearm{tag}', 'tube', loc=a['elbow'], to=a['wrist'], radius=ARM_R[2], r2=ARM_R[3]),
            palm_part(s),
        ]
        for i, (b, t, r0, r1) in enumerate(fingers(s)):
            ps.append(Part(f'finger{tag}{i}', 'tube', loc=tuple(map(float, b)), to=tuple(map(float, t)), radius=r0, r2=r1))
        g = {k: mirror(v, s) for k, v in LEG.items()}
        fc = mirror(FOOT[0], s)
        ps += [
            Part(f'thigh{tag}', 'sphere', loc=mirror(THIGH[0], s), radius=1.0, scale=THIGH[1]),
            Part(f'shin{tag}', 'tube', loc=g['knee'], to=g['ankle'], radius=SHIN_R[0], r2=SHIN_R[1]),
            Part(f'foot{tag}', 'sphere', loc=fc, radius=1.0, scale=FOOT[1], rot=(0.0, 0.0, FOOT_YAW * s)),
            Part(f'heel{tag}', 'sphere', loc=mirror(HEEL[0], s), radius=HEEL[1], scale=(1.0, 1.0, 0.95)),
        ]
        for i, (b, t, r0, r1) in enumerate(toes(s)):
            ps.append(Part(f'toe{tag}{i}', 'tube', loc=tuple(map(float, b)), to=tuple(map(float, t)), radius=r0, r2=r1))
    return ps


def tail_parts() -> list[Part]:
    return [Part(f'tail{i}', 'tube', loc=TAIL[i], to=TAIL[i + 1], radius=TAIL_R[i], r2=TAIL_R[i + 1]) for i in range(len(TAIL) - 1)]


def all_parts() -> list[Part]:
    return head_parts() + torso_parts() + limb_parts() + tail_parts()
