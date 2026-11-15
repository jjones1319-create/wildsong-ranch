"""Grumblestone at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9; RECIPE.md, "Biped plan"): the recipe for
`tools/blender/monsters/build_ultra.py`.

A hulking, hunched boulder giant on two short, thick legs; grumpy, slow and utterly dependable
(chatgpt/monsters/11-grumblestone: the card decides the parts, 1-hero the shapes, 2-turnaround the measurements,
CONTENT §2.2 #22 the colours):
  - one huge egg-shaped granite shell from the hood over the face to the rump, cracked into big flat chiselled plates
    (a Voronoi of seeds laid on the body's own surface: flat faces, bevelled edges, narrow cracks), the biggest on the
    back (~30 cm, the turtle-shell back of 2-turnaround), smaller on the hood, the shoulders, the arms and the legs;
  - violet crystals glowing in the cracks like the inside of a geode: the crack floors glow (the glow map), small
    faceted crystals sit at crack junctions, and geode clusters poke out of both shoulders and the top of the hood;
  - lighter stone on the face and the chest: a smooth pitted face panel set into the hood (no plates) and a chest of
    big flat plastron plates with thin seams;
  - the face: two heavy granite brow blocks (baked; there is no brow bone) overhanging small yellow eyes with big black
    pupils, a wide closed smile curling up into the cheeks, no neck (the face sits low and forward in the hood);
  - long pillar arms reaching near the ground, ending in big blocky fists: four stone fingers, each with a faceted
    violet gem set in its knuckle, and a curled fingertip block under it;
  - short thick legs on big flat feet with four toe blocks.
No fur, no cards, no tuft: the detail is carved, baked and painted; the crystals are rigid glowing props.

Size: about 1.8 × Puddlepup (PROMPTS.md): HEIGHT_UNITS 270, so the stone body stands about 1.77 m tall to the top of
the hood; the crystals reach a little higher. Metres; the monster faces −Y, Z is up, +X is its left. Palette: CONTENT
§2.2 #22 (#7A7068 granite / #9C938A lighter stone / #9B5DE5 crystals / #F5E663 eyes); no secret variant.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import new_mat
from lib.surface import in_ellipsoid, norm, smooth, v3
from monsters.breeds import grumblestone_stone as K

ID = 'grumblestone'
LOOK = 'grumblestone-ultra'
PLAN = 'biped'
HEIGHT_UNITS = 270

PALETTE = {'body': '#7A7068', 'belly': '#9C938A', 'accent': '#9B5DE5', 'eye': '#F5E663'}
VARIANTS: dict = {}

# colours CONTENT has no hex for, each derived from the palette (the pictures show where they go)
PUPIL_HEX = '#16121A'
LASH_HEX = '#2A2522'

# no fur: no locks, cards or tuft, so the body atlas needs no strip (RECIPE.md "Coats without fur")
ATLAS_STRIP = 0
NORMAL_SCALE = 1.15              # the chiselled facets, chips and pits want about full strength (Cobblemaw 1.1)
BODY_TRIS = 60000                # the plates' bevels reach the silhouette
VOXELS = {'lo': 0.009}           # a big body: the heat solve fails on fine proxies (Cobblemaw's lesson)
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_props': 1.1}
UV_SMOOTH = 40                   # the plated shell unwraps into fewer, larger islands
GLOW = {'strength': 1.6, 'tint': None}       # round 3: saturated, not washed toward white
BODY_SHEEN = 0                   # stone: the film's fur sheen would read as felt with a halo (Cobblemaw's lesson)
LITE_PROPS_TRIS = 3200           # the crystals are the signature: keep them in the Lite copy
FACE_NOTE = ('Baked face: two heavy granite brow blocks (no brow bone), small yellow lenses with big black pupils that '
             'squash and sink to blink, a wide closed smile. The cracks and the crystals glow violet (ORM alpha).')

# ============================================================================= proportions (2-turnaround, 309 px/m)
# the shell: an egg from the rump to the hood; the hood over the face makes the head's top (no neck)
SHELL = ((0.0, -0.01, 1.0), (0.45, 0.48, 0.58))
HOOD = ((0.0, -0.18, 1.38), (0.40, 0.40, 0.36))
# round 2: the upper back fills behind the hood, so the hood and the shell read as one hunched hump (the head juts
# forward from under it), and the upper chest fills under the chin (no step from the chin to the chest)
UPPERBACK = ((0.0, -0.02, 1.36), (0.42, 0.40, 0.34))
CHESTTOP = ((0.0, -0.38, 1.05), (0.30, 0.22, 0.14))
PLASTRON = ((0.0, -0.24, 0.82), (0.36, 0.31, 0.38))
RUMP = ((0.0, 0.04, 0.58), (0.33, 0.22, 0.19))
PELVIS = ((0.0, -0.02, 0.56), (0.36, 0.28, 0.16))
SHOULDER = ((0.47, -0.02, 1.17), (0.25, 0.30, 0.29))     # round 2: the tops at eye level
# the face (lighter stone, set into the hood): a broad, flat-fronted panel (1-hero, 3-faces), wide cheeks, the eyes
# tucked under the brows, a hanging chin; no snout
# one tall, flat-fronted shield from the brows (z 1.42) to the chin (1.03), widest across the cheeks and narrower at
# the bottom (2-turnaround front: a rounded hexagon), its front near vertical in profile; the eyes sit in sockets
# cut into it under the brows, the smile across its upper half, a big chin below
FACE = {'c': (0.0, -0.48, 1.235), 'half': (0.30, 0.20, 0.205), 'rot': (5.0, 0.0, 0.0), 'm': (0.62, 0.6, 0.45), 'taper': 0.34}
# round 3: granite blocks flanking the face hide the shield's flat sides (no boxy slab behind the cheek)
CHEEKGUARD = ((0.31, -0.46, 1.30), (0.10, 0.16, 0.19))
CHEEK = ((0.17, -0.635, 1.31), (0.075, 0.05, 0.065))       # soft fullness above the mouth's corners
# the brows: a thick granite block over each eye (2-turnaround side: its front-bottom edge is the most forward point
# of the head, the front face leaning back), the inner end lower (grumpy), the outer end turned back with the face
BROW = {'c': (0.145, -0.607, 1.50), 'half': (0.11, 0.085, 0.062), 'rot': (5.0, -18.0, 8.0)}   # wedges, inner end low (grumpy)
# arms (the left; mirrored): a big shoulder, a pillar upper arm and forearm, a big round fist
ARM_PTS = [(0.53, -0.01, 1.0), (0.70, -0.08, 0.71), (0.745, -0.22, 0.48)]
ARM_R = (0.185, 0.21, 0.21)
FIST = ((0.77, -0.31, 0.32), (0.235, 0.215, 0.225))     # clear of the foot (2.5 cm+)                # the fist's mass
PALM = {'c': (0.77, -0.24, 0.38), 'half': (0.19, 0.14, 0.15), 'rot': (0.0, 0.0, 0.0)}
# the knuckles wrap the fist's front-outer corner (2-turnaround: two or three gems show from the front AND the side)
KNUCKLE_ANG = (-26.0, 6.0, 38.0, 70.0)                           # degrees from straight ahead toward the outside
KNUCKLE_R = 0.19                                                # from the fist's centre, in plan
FINGER_UP = {'dz': 0.06, 'half': (0.062, 0.088, 0.105), 'pitch': -6.0}        # chiselled rounded blocks
FINGER_LO = {'dz': -0.12, 'back': 0.03, 'half': (0.058, 0.082, 0.078), 'pitch': 12.0}
THUMB = {'ang': -62.0, 'r': 0.19, 'dz': 0.01, 'half': (0.06, 0.095, 0.09)}
# legs (the left): short thick columns on big flat feet with four rounded toe blocks
LEG_PTS = [(0.25, 0.0, 0.56), (0.27, -0.04, 0.34), (0.29, -0.01, 0.16)]
LEG_R = (0.13, 0.13, 0.14)
FOOT = {'c': (0.32, -0.07, 0.04), 'half': (0.18, 0.17, 0.04), 'rot': (0.0, 0.0, 0.0)}
INSTEP = ((0.31, -0.05, 0.10), (0.20, 0.21, 0.10))
TOE_X = (-0.15, -0.05, 0.05, 0.15)
TOE = {'y': -0.29, 'z': 0.06, 'half': (0.052, 0.078, 0.062)}       # chiselled rounded blocks

# the rig (plans/biped.py): the left limbs, mirrored
HIP = (0.0, 0.0, 0.60)
CHEST = (0.0, 0.0, 1.22)
HEAD_BASE = (0.0, -0.30, 1.30)           # in front of the chest: the neck is a short forward stub (no visible neck)
HEAD_C = Vector((0.0, -0.50, 1.40))
HEAD_R = 0.27
LEGS = {'hip': (0.25, 0.0, 0.58), 'knee': (0.27, -0.05, 0.34), 'ankle': (0.30, -0.01, 0.15), 'toe': (0.32, -0.32, 0.05)}
ARMS = {'shoulder': (0.50, 0.0, 1.08), 'elbow': (0.70, -0.08, 0.72), 'wrist': (0.76, -0.24, 0.48), 'hand': (0.78, -0.44, 0.27)}


# the big fists in front of the deep belly and the broad face: the hands' goals are kept out of these (rest pose,
# carried by their bones; margin = about the fist's half thickness; pushed straight forward, so the hulk's low guard
# stays low) and 0.2 m apart from the mid-line (plans/biped.py
# hand_clear, hand_gap); the slam's fists rise high and wide overhead, then land well in front of the toes (5-poses
# attack), not on the feet
HAND_CLEAR = [
    {'bone': 'spine', 'c': (0.0, -0.10, 0.84), 'r': (0.40, 0.46, 0.44), 'margin': 0.13, 'push': (0.0, -1.0, 0.0)},
    {'bone': 'head', 'c': (0.0, -0.50, 1.27), 'r': (0.30, 0.17, 0.22), 'margin': 0.10, 'push': (0.0, -1.0, 0.0)},
    # round 2: overhead fists (win, celebrate, cast) are pushed forward out of the hump, in front of the head
    {'bone': 'chest', 'c': (0.0, 0.1, 1.6), 'r': (1.0, 0.45, 0.4), 'margin': 0.05, 'push': (0.0, -1.0, 0.0)},
]
# round 2: the impact leans in less with the face kept up (it hid the face), the fists land nearer the middle
SLAM = {'over': (0.55, -0.30, 1.95), 'ground': (0.32, -0.92, 0.07), 'lean': 18.0, 'gaze': 0.6,
        'hand_up': (60.0, 0.0, 0.0), 'hand_down': (-30.0, 0.0, 0.0),       # overhead the knuckle gems face forward
        'yaw': 45.0}                                                       # polish: the chest and face to the camera's side
# round 3: win raises both fists high and out to the sides, the knuckle gems toward the camera (plans/biped.py `win`)
WIN = {'over': (0.85, -0.38, 1.82), 'hand': (60.0, 0.0, 0.0)}


# no neck: the face is set in the hood, so the plan's head turns (up to ~30-34 degrees in hit, hit_heavy, look_around)
# would slide it across the shell; the head and the neck stub keep half their keyed rotation in every clip
CLIP_CALM = {'*': {'head': 0.5}, 'strike': {'head': 1.0}, 'ko': {'head': 1.0, 'torso': 0.35},
             'hit_heavy': {'head': 0.3, 'torso': 0.5}}     # no face crushed or thrown out of view


def calm_group(bone: str) -> str | None:
    if bone in ('head', 'neck'):
        return 'head'
    return 'torso' if bone in ('spine', 'chest') else None


def rig_p() -> dict:
    return {'hip': HIP, 'chest': CHEST, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R, 'head_base': HEAD_BASE,
            'legs': LEGS, 'arms': ARMS, 'hulk': 1.0, 'strike_style': 'slam', 'arm_relax': 15.0,
            'arm_radius': 0.3, 'leg_radius': 0.22, 'hand_clear': HAND_CLEAR, 'hand_gap': 0.2, 'slam': SLAM, 'win': WIN}


# ============================================================================= the body
def _ell(name: str, spec, mirror: bool = False, rot=(0, 0, 0)) -> Part:
    c, r = spec
    return Part(name, 'sphere', loc=tuple(c), radius=1.0, scale=tuple(r), mirror=mirror, rot=rot)


def _box(name: str, c, half, rot=(0, 0, 0), mirror: bool = False) -> Part:
    return Part(name, 'box', loc=tuple(c), radius=1.0, scale=tuple(half), rot=tuple(rot), mirror=mirror)


def knuckles(s: int) -> list[dict]:
    """One fist's four knuckles on an arc round its front-outer corner (s = +1 left, −1 right): per finger its
    facing direction `d` (in plan), the upper block's centre `c` and its yaw (degrees, the block's front along d), and
    `k` (the outer, little finger smaller)."""
    F = v3(FIST[0]) * v3((s, 1, 1))
    out = []
    for i, a in enumerate(KNUCKLE_ANG):
        r = math.radians(a)
        d = v3((math.sin(r) * s, -math.cos(r), 0.0))
        k = 0.84 if i == 3 else 1.0
        c = F + d * KNUCKLE_R + v3((0.0, 0.0, FINGER_UP['dz'] - (0.012 if i == 3 else 0.0)))
        out.append({'d': d, 'c': c, 'yaw': a * s, 'k': k})
    return out


def finger_boxes(s: int) -> list[tuple[str, tuple, tuple, tuple]]:
    """(name, centre, half extents, rotation) of one fist's finger blocks (s = +1 left, −1 right), already mirrored:
    an upper block per knuckle (its gem set in the front) and a curled fingertip block under it, and the thumb."""
    out = []
    for i, kn in enumerate(knuckles(s)):
        k, d = kn['k'], kn['d']
        out.append((f'fingerU{i}', tuple(kn['c']), tuple(h * k for h in FINGER_UP['half']), (FINGER_UP['pitch'], 0.0, kn['yaw'])))
        lo = kn['c'] - d * FINGER_LO['back'] + v3((0.0, 0.0, FINGER_LO['dz'] - FINGER_UP['dz'] + (0.012 if i == 3 else 0.0)))
        out.append((f'fingerL{i}', tuple(lo), tuple(h * k for h in FINGER_LO['half']), (FINGER_LO['pitch'], 0.0, kn['yaw'])))
    F = v3(FIST[0]) * v3((s, 1, 1))
    r = math.radians(THUMB['ang'])
    d = v3((math.sin(r) * s, -math.cos(r), 0.0))
    out.append(('thumb', tuple(F + d * THUMB['r'] + v3((0.0, 0.0, THUMB['dz']))), THUMB['half'], (0.0, 0.0, THUMB['ang'] * s)))
    return out


def toe_boxes(s: int) -> list[tuple[str, tuple, tuple, tuple]]:
    fx = FOOT['c'][0] * s
    return [(f'toe{i}', (fx + dx * s, TOE['y'] + (0.014 if i in (0, 3) else 0.0), TOE['z']),
             tuple(h * (0.9 if i in (0, 3) else 1.0) for h in TOE['half']), (0.0, 0.0, -7.0 * (i - 1.5) * s))
            for i, dx in enumerate(TOE_X)]


def all_parts() -> list[Part]:
    ps = [
        _ell('shell', SHELL), _ell('hood', HOOD), _ell('plastron', PLASTRON), _ell('rump', RUMP), _ell('pelvis', PELVIS),
        _ell('shoulder', SHOULDER, mirror=True), _ell('upperback', UPPERBACK), _ell('cheekguard', CHEEKGUARD, mirror=True),
        _ell('cheek', CHEEK, mirror=True),
    ]
    for s, tag in ((1, 'L'), (-1, 'R')):
        m = lambda p, s=s: (p[0] * s, p[1], p[2])  # noqa: E731
        a = [m(p) for p in ARM_PTS]
        ps += [
            Part(f'upperarm{tag}', 'tube', loc=a[0], to=a[1], radius=ARM_R[0], r2=ARM_R[1]),
            Part(f'forearm{tag}', 'tube', loc=a[1], to=a[2], radius=ARM_R[1], r2=ARM_R[2]),
            Part(f'elbow{tag}', 'sphere', loc=a[1], radius=0.2),
            _ell(f'fist{tag}', (m(FIST[0]), FIST[1])),
            _box(f'palm{tag}', m(PALM['c']), PALM['half'], PALM['rot']),
        ]
        g = [m(p) for p in LEG_PTS]
        ps += [
            Part(f'thigh{tag}', 'tube', loc=g[0], to=g[1], radius=LEG_R[0], r2=LEG_R[1]),
            Part(f'shin{tag}', 'tube', loc=g[1], to=g[2], radius=LEG_R[1], r2=LEG_R[2]),
            _box(f'foot{tag}', m(FOOT['c']), FOOT['half'], FOOT['rot']),
            _ell(f'instep{tag}', (m(INSTEP[0]), INSTEP[1])),
        ]
    return ps


def body_extras() -> list[bpy.types.Object]:
    """The chiselled blocks, voxel-united into the body: the brows, each fist's finger blocks and thumb, each foot's
    four toes (rounded boxes; the rig skins a proxy without them and copies its weights)."""
    out = [K.rounded_block('face', FACE['c'], FACE['half'], FACE['rot'], m=FACE['m'], seg=48, taper=FACE['taper'])]
    for s in (1, -1):
        c = v3(BROW['c']) * v3((s, 1, 1))
        r = (BROW['rot'][0], BROW['rot'][1] * s, BROW['rot'][2] * s)
        out.append(K.rounded_block(f'brow{s}', c, BROW['half'], r, m=0.32))
        for n, c, h, r in finger_boxes(s) + toe_boxes(s):
            out.append(K.rounded_block(f'{n}{s}', c, h, r, m=0.45))
    return out


# ============================================================================= zones
def _seg_dist(p: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / float(ab @ ab), 0.0, 1.0)
    return np.linalg.norm(p - (a[None] + t[:, None] * ab[None]), axis=1), t


def arm_dist(p: np.ndarray) -> np.ndarray:
    """Metres from the nearer arm's axis (shoulder → elbow → wrist)."""
    d = np.full(len(p), 9.0)
    for s in (1, -1):
        pts = [v3(q) * v3((s, 1, 1)) for q in ARM_PTS]
        for a, b in zip(pts[:-1], pts[1:]):
            d = np.minimum(d, _seg_dist(p, a, b)[0])
    return d


def leg_dist(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), 9.0)
    for s in (1, -1):
        pts = [v3(q) * v3((s, 1, 1)) for q in LEG_PTS]
        for a, b in zip(pts[:-1], pts[1:]):
            d = np.minimum(d, _seg_dist(p, a, b)[0])
    return d


def finger_sdf(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), np.inf)
    for s in (1, -1):
        for _n, c, h, r in finger_boxes(s):
            d = np.minimum(d, K.box_sdf(p, c, h, r))
    return d


def toe_sdf(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), np.inf)
    for s in (1, -1):
        for _n, c, h, r in toe_boxes(s):
            d = np.minimum(d, K.box_sdf(p, c, h, r))
    return d


def brow_sdf(p: np.ndarray) -> np.ndarray:
    return K.box_sdf(p, BROW['c'], BROW['half'], BROW['rot'], mirror=True)


def face_sdf(p: np.ndarray) -> np.ndarray:
    """< 0 on the lighter face panel: inside the face's shield and cheeks (a little grown), in front, under the brows."""
    d = K.box_sdf(p, FACE['c'], v3(FACE['half']) + v3((-0.025, 0.012, 0.012)), FACE['rot']) - 0.012
    for s in (1, -1):
        d = np.minimum(d, K.ell_sdf(p, (CHEEK[0][0] * s, CHEEK[0][1], CHEEK[0][2]), v3(CHEEK[1]) * 1.08))
    # under the brow line (it rises toward the middle, over the nose bridge) and in front of the hood
    top = 1.432 + 0.03 * smooth(0.06, 0.0, np.abs(p[:, 0]))
    d = np.maximum(d, p[:, 2] - top)
    d = np.maximum(d, p[:, 1] + 0.40)
    return d


def fist_mask(p: np.ndarray) -> np.ndarray:
    m = np.zeros(len(p), bool)
    for s in (1, -1):
        m |= K.ell_sdf(p, (FIST[0][0] * s, FIST[0][1], FIST[0][2]), v3(FIST[1]) + 0.07) < 0
    return m


def chest_mask(p: np.ndarray) -> np.ndarray:
    """The lighter plastron's area seen from the front (its seeds lay the light plates; the cracks bound the colour)."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    r = (np.abs(x) / 0.36) ** 2.2 + (np.abs(z - 0.80) / 0.37) ** 2.2
    return (r < 1.0) & (y < -0.28) & (z < 1.15)


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    fs = face_sdf(p)
    face = fs < 0
    brow = brow_sdf(p) < 0.012
    fing = finger_sdf(p) < 0.008
    toes = toe_sdf(p) < 0.008
    fist = fist_mask(p)
    arm = ((arm_dist(p) < 0.3) & (ax > 0.42) & (z < 1.12)) | fist
    leg = (leg_dist(p) < 0.22) & (z < 0.5) & (ax < 0.5) & ~fist
    foot = (z < 0.16) & (ax < 0.56) & ~fist
    sole = z < 0.006
    if n is not None:
        sole = sole | ((n[:, 2] < -0.6) & (z < 0.05))
        sole = sole | ((n[:, 2] < -0.55) & (z < 0.42) & (fist | fing | toes | ((z < 0.16) & (ax < 0.56))))
    chest = chest_mask(p) & ~face & ~arm
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    th = mouth_theta(p)
    mz = mouth_z(th)
    return {'face': face, 'face_sdf': fs, 'brow': brow, 'fingers': fing, 'toes': fing | toes, 'toe': toes, 'fist': fist,
            'paw': fist, 'arm': arm, 'leg': leg, 'foot': foot, 'sole': sole, 'chest': chest, 'belly': chest, 'eye_d': eye_d,
            'muzzle': face & (z < 1.4), 'theta': th, 'mouth_z': mz}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The face's shield and the brows move with the head bone only (the weight proxy has no face block, so its heat
    weights there come from the hood behind); the hood keeps its heat weights, so the shell flexes softly round it."""
    core = (face_sdf(co) < -0.004) | (brow_sdf(co) < 0.004)
    return [U.rigid(core, 'head')]


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """Protect the face (eyes and smile most), the brows and the finger and toe blocks from the decimation; the plates'
    edges keep themselves (the collapse keeps sharp creases)."""
    z = zones(co)
    k = 0.55 * z['face'] + 0.45 * (z['eye_d'] < 0.09) + 0.4 * z['brow'] + 0.3 * z['toes']
    return np.clip(k, 0.0, 1.0)


# ============================================================================= the cracked shell
SEED = 2207
_PLATES: dict = {}


def plate_spacing(p: np.ndarray, n: np.ndarray, z: dict) -> np.ndarray:
    """Seed spacing per point (metres; NaN = no plates: the face, the brows, the finger and toe blocks, the soles):
    the biggest plates on the back (2-turnaround back), smaller up the hood, on the shoulders, arms and legs."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    # round 3: big irregular boulders (about 10 on the back, 5-7 per arm segment), sizes varying about 2x
    sp = np.full(len(p), 0.38)
    sp = sp - 0.13 * smooth(1.3, 1.6, zz) * smooth(0.15, -0.15, y)          # the hood's top and front (~0.25 m cobbles)
    sp = sp - 0.08 * smooth(0.3, 0.5, ax) * smooth(0.8, 1.1, zz)             # the shoulders
    sp = sp - 0.10 * smooth(-0.2, -0.45, y) * smooth(1.05, 1.25, zz)         # around the face
    sp = np.where(z['chest'], 0.22, sp)
    sp = np.where(z['arm'], 0.27, sp)
    sp = np.where(z['fist'], 0.17, sp)
    sp = np.where(z['leg'], 0.19, sp)
    sp = np.where(z['foot'], 0.13, sp)
    sp = np.where((zz < 0.62) & ~z['leg'] & ~z['arm'] & ~z['chest'], np.minimum(sp, 0.24), sp)     # the rump's underside
    vary = 0.65 + 0.7 * K.value_noise(p, 1 / 0.45, 59)
    sp = np.where(z['chest'], sp, sp * vary)
    no =z['face'] | (z['face_sdf'] < 0.03) | (z['brow']) | z['toes'] | z['sole']
    return np.where(no, np.nan, sp)


def seed_params(c: np.ndarray, n: np.ndarray) -> dict:
    """Per seed: kind (0 granite, 1 the lighter chest), proud height H, crack half width w, crack depth cd, the
    flatness kf, the bevel slope sb, the top's tilt g and its spacing sp."""
    z = zones(c, n)
    k = len(c)
    chest = z['chest']
    limb = z['arm'] | z['leg'] | z['foot']
    H = np.where(chest, 0.010, np.where(limb, 0.022, 0.030))
    H = np.where(z['fist'] | z['foot'], 0.018, H)
    w = np.where(chest, 0.0035, np.where(limb, 0.0055, 0.0075))
    cd = np.where(chest, 0.004, np.where(limb, 0.008, 0.012))
    curved = (c[:, 2] > 1.3) | limb | (np.abs(c[:, 0]) > 0.4)
    kf = np.where(chest, 0.45, np.where(curved, 0.55, 0.82))
    sb = np.where(chest, 1.8, 3.0)
    rnd = np.stack([K.hash1(np.arange(k), SEED + j) for j in range(6)], axis=1)
    H = H * (0.62 + 0.76 * rnd[:, 0])                     # some boulders stand proud of their neighbours
    g = rnd[:, 1:4] - 0.5
    g = g - n * (g * n).sum(1, keepdims=True)
    g = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9) * np.where(chest, 0.04, np.where(curved, 0.09, 0.15))[:, None] * rnd[:, 4:5]
    sp = plate_spacing(c, n, z)
    ax_ = np.abs(c[:, 0])
    armpit = smooth(0.30, 0.38, ax_) * smooth(0.58, 0.50, ax_) * smooth(0.62, 0.72, c[:, 2]) * smooth(1.15, 1.05, c[:, 2])
    elbow = np.minimum(np.linalg.norm(c - v3(ARM_PTS[1]), axis=1), np.linalg.norm(c - v3(ARM_PTS[1]) * v3((-1, 1, 1)), axis=1))
    H = H * (1.0 - 0.5 * armpit) * (0.5 + 0.5 * smooth(0.1, 0.22, elbow)) * (0.45 + 0.55 * smooth(0.03, 0.15, z['face_sdf']))
    return {'kind': chest.astype(np.float64), 'H': H, 'w': w, 'cd': cd, 'kf': kf, 'sb': sb, 'g': g,
            'sp': np.where(np.isfinite(sp), sp, 0.15)}


def make_plates(co: np.ndarray, vn: np.ndarray) -> dict:
    """The seeds (cached: the high source's layout is reused for the low body): a Poisson set on the surface with the
    spacing above, each with its own height, tilt and bevels."""
    if 'plates' in _PLATES:
        return _PLATES['plates']
    z = zones(co, vn)
    sp = plate_spacing(co, vn, z)
    lay = U.plate_layout(co, vn, sp, 0.1, 0.02, SEED, wobble=0.0)
    c, n = lay['c'], lay['n']
    plates = {'c': c, 'n': n, **seed_params(c, n)}
    C.log(f'plates: {len(c)} seeds ({int(plates["kind"].sum())} on the chest)')
    _PLATES['plates'] = plates
    return plates


def plate_field(co: np.ndarray, vn: np.ndarray, plates: dict, z: dict, scale: float = 1.0) -> dict:
    """The plates as heights along the normals: a flat, tilted, chiselled top on each plate, bevelled down to a narrow
    crack at the cell walls (the bisector to the 2nd nearest seed), and to the edge of every plain area (the face, the
    brows, the finger and toe blocks). Returns h, the wall distance dw, the crack's half width w, the junction distance
    dj (to the 3rd seed's wall), the plate id, its kind (chest) and the 'top' (0..1 toward the plate's middle)."""
    c, n = plates['c'], plates['n']
    idx, dist = K.nearest_seeds(co, vn, c, n, k=3)
    i1, i2, i3 = idx[:, 0], idx[:, 1], idx[:, 2]
    dw = K.wall_distance(co, c[i1], c[i2])
    dj = K.wall_distance(co, c[i1], c[i3])
    # the plain areas bound the plates too (a crack round the face, the brows, the fingers and the toes)
    plain = np.minimum(np.minimum(np.maximum(z['face_sdf'], -1.0), brow_sdf(co) - 0.012),
                       np.minimum(finger_sdf(co) - 0.008, toe_sdf(co) - 0.008))
    plain = np.where(plain < 0, 0.0, plain)
    dw = np.minimum(dw, plain)
    on = ~(z['face'] | z['brow'] | z['toes'] | z['sole'])
    q = co - c[i1]
    n1 = n[i1]
    H, w, cd, kf, sb, g, sp = (plates[k][i1] for k in ('H', 'w', 'cd', 'kf', 'sb', 'g', 'sp'))
    # a flat top: the plate's own plane (its tangent plane at the seed, lifted H and tilted by g), so on the curved
    # shell each plate reads as a flat chiselled face and the outline as a polygon (not a smooth dome)
    top = H + kf * np.maximum(0.0, -(q * n1).sum(1)) + (q * g).sum(1)
    # chisel cuts: four planes per plate cut its shoulder into extra facets (granite only)
    gran = plates['kind'][i1] < 0.5
    for j in range(4):
        phi = 2 * np.pi * j / 4 + 1.4 * K.hash1(i1, SEED + 20 + j)
        t1 = np.cross(n1, np.array([0.0, 0.0, 1.0]))
        bad = np.linalg.norm(t1, axis=1) < 1e-3
        t1[bad] = np.array([1.0, 0.0, 0.0])
        t1 = t1 / np.linalg.norm(t1, axis=1, keepdims=True)
        t2 = np.cross(n1, t1)
        dirv = t1 * np.cos(phi)[:, None] + t2 * np.sin(phi)[:, None]
        u = (q * dirv).sum(1) / (0.5 * sp)
        u0 = 0.45 + 0.35 * K.hash1(i1, SEED + 30 + j)
        gk = 0.35 + 0.5 * K.hash1(i1, SEED + 40 + j)
        top = np.where(gran, np.minimum(top, top - H * gk * np.maximum(0.0, u - u0) * 2.0), top)
    edge = -cd + sb * (dw - w)
    h = np.maximum(np.minimum(top, edge), -cd)
    h = np.where(on, h, 0.0) * scale
    crack = np.where(on, smooth(w * 1.3, w * 0.5, dw), 0.0)          # the glowing core, deep in the crack
    gap = np.where(on, smooth(w * 2.2, w * 1.0, dw), 0.0)             # the dark crack walls round it
    topm = np.where(on, smooth(0.0, 0.35, dw / np.maximum(sp, 1e-3)), 0.0)
    return {'h': h, 'dw': dw, 'dj': dj, 'w': w, 'pid': np.where(on, i1, -1), 'kind': np.where(on, plates['kind'][i1], -1.0),
            'crack': crack, 'gap': gap, 'top': topm}


# ============================================================================= the face
EYE_C = {s: Vector((0.125 * s, -0.665, 1.38)) for s in (1, -1)}
EYE_R = 0.055
EYE_DEPTH = (0.45, 0.30)
EYE_SHAPE = (1.0, 0.96)
MOUTH_AXIS_Y = -0.40
MOUTH_TH = [0.0, 12.0, 24.0, 33.0, 40.0, 45.0, 48.0]
MOUTH_Z = [1.29, 1.293, 1.302, 1.315, 1.33, 1.347, 1.362]          # a wide smile, the corners curling up into the cheeks


def mouth_theta(p: np.ndarray) -> np.ndarray:
    """Degrees round a vertical axis behind the face (0 straight ahead, + toward the monster's left)."""
    return np.degrees(np.arctan2(p[:, 0], -(p[:, 1] - MOUTH_AXIS_Y)))


def mouth_z(th: np.ndarray) -> np.ndarray:
    return np.interp(np.abs(th), MOUTH_TH, MOUTH_Z)


def eye_frame(s: int):
    c = EYE_C[s]
    look = Vector((0.24 * s, -1.0, 0.03)).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


LID_LASH, LID_DROP, LID_W = 0.06, 0.14, 0.94
BLINK_CLOSED = (0.74, 0.04, 0.2)


def blink_pivot(s: int):
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens, the closed lid (a soft bulge) and its lash line; hidden until a blink sinks the lens."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax_, ay_ = EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1]
        r2 = (xe / ax_) ** 2 + (ye / ay_) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax_ * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * EYE_R
        th = 0.0024 + 0.0016 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def eye_socket(co: np.ndarray, vn: np.ndarray | None = None) -> np.ndarray:
    """Metres to move each vertex near an eye along its normal: inside the lens's outline the face becomes a dome 3 mm
    behind the lens (the closed lid: hidden while the eye is open, a smooth curved lid flush with the face when a blink
    sinks the lens), easing out into the cheek and the brow by 1.45 radii (never pulling them forward)."""
    out = np.zeros(len(co))
    off_brow = smooth(-0.004, 0.006, brow_sdf(co))      # never the brow blocks above (a spike rose through them)
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        r = np.sqrt((xe / (EYE_R * EYE_SHAPE[0])) ** 2 + (ye / (EYE_R * EYE_SHAPE[1])) ** 2)
        lens = (np.sqrt(np.clip(1.0 - r * r, 0.0, 1.0)) * EYE_DEPTH[0] - EYE_DEPTH[1]) * EYE_R - 0.004
        blend = smooth(1.12, 0.98, r) * (ze > -0.06) * (ze < 0.10)
        # only ever pushed back (a forward pull overshot over the lens where the face tilts): the closed lid is this
        # smooth dome 1 cm behind the lens
        delta = (lens - ze) * blend * off_brow
        if vn is not None:      # the move is along each vertex's normal: scale it to land on the target along the eye's axis
            delta = delta / np.clip(vn @ v3(look), 0.6, 1.0)
        delta = np.clip(delta, -0.05, 0.006)
        out = np.where(blend > 0, delta, out)
    return out


def face_marks(co: np.ndarray, z: dict) -> dict:
    """The smile's groove, the creases curling up from its corners into the cheeks, and the nose's soft bridge line."""
    x, y, zz = co[:, 0], co[:, 1], co[:, 2]
    th = z['theta']
    front = z['face'] & (np.abs(th) < 60)
    groove = np.exp(-((zz - z['mouth_z']) / 0.0065) ** 2) * front * smooth(47.5, 43.5, np.abs(th))
    curl = np.zeros(len(co))
    for s in (1, -1):
        # a short crease from the corner up and out along the cheek (the smile lines of 3-faces neutral)
        a = v3((0.215 * s, -0.625, 1.352))
        b = v3((0.245 * s, -0.595, 1.40))
        d, t = _seg_dist(co, a, b)
        curl = np.maximum(curl, np.exp(-(d / 0.007) ** 2) * (1.0 - 0.6 * t) * smooth(0.0, 0.25, t))
    return {'groove': groove, 'curl': curl * z['face']}


# ============================================================================= carving (the high source)
_LAST: dict = {}


def _region_smooth(ob: bpy.types.Object, mask: np.ndarray, iterations: int, factor: float = 0.6) -> None:
    """Blender's Smooth modifier on the masked vertices only (a vertex group in four weight steps)."""
    if len(mask) == 0 or float(mask.max()) <= 0.0:
        return
    vg = ob.vertex_groups.new(name='ws_region_smooth')
    for lo_, hi_ in ((0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.01)):
        idx = np.nonzero((mask > lo_) & (mask <= hi_))[0]
        if len(idx):
            vg.add(idx.tolist(), float(min(1.0, hi_)), 'REPLACE')
    sm = ob.modifiers.new('ws_region_smooth', 'SMOOTH')
    sm.factor = factor
    sm.iterations = int(iterations)
    sm.vertex_group = vg.name
    C.apply_modifiers(ob)
    left = ob.vertex_groups.get('ws_region_smooth')
    if left is not None:
        ob.vertex_groups.remove(left)


def foot_sdf(p: np.ndarray) -> np.ndarray:
    return K.box_sdf(p, FOOT['c'], FOOT['half'], FOOT['rot'], mirror=True)


def soften(ob: bpy.types.Object) -> None:
    """Round the stone blocks (the brows, the fingers, the toes, the foot's slab: chiselled blocks, not bricks) and
    melt the creases between the face's parts into one soft face (not the eyes' surroundings or the brows). The reach
    is the same at every voxel size (about 2 cm for the blocks, 3 cm for the face), so the high and low bodies agree."""
    co, _vn = S.mesh_arrays(ob)
    edge = math.sqrt(max(S.mesh_area(ob), 1e-9) / max(len(co), 1))
    eyes = np.minimum(np.linalg.norm(co - v3(EYE_C[1]), axis=1), np.linalg.norm(co - v3(EYE_C[-1]), axis=1))
    m = smooth(0.03, -0.01, face_sdf(co)) * smooth(0.05, 0.08, eyes) * smooth(0.0, 0.02, brow_sdf(co))
    _region_smooth(ob, m, int(np.clip((0.03 / edge) ** 2, 6, 300)), 0.55)
    co, _vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    chin = smooth(0.9, 1.0, z) * smooth(1.2, 1.1, z) * smooth(-0.3, -0.42, y) * smooth(0.34, 0.24, np.abs(x))
    _region_smooth(ob, chin, int(np.clip((0.05 / edge) ** 2, 8, 400)), 0.6)


def sole_grooves(co: np.ndarray) -> np.ndarray:
    """0..1 along the grooves between the sole's pads (4-details: a plated pad under each foot)."""
    q = co.copy()
    q[:, 2] = 0.0
    f1, f2, _ = K.voronoi(q, 0.08, 41)
    return smooth(0.008, 0.002, f2 - f1)


def carve(ob: bpy.types.Object) -> None:
    """The high source: the cracked shell (plates, bevels, cracks), granite pits and chips, the faceted brows, fingers
    and toes, the face's pits, smile and closed lids, the eye sockets."""
    soften(ob)
    co, vn = S.mesh_arrays(ob)
    z = zones(co, vn)
    plates = make_plates(co, vn)
    f = plate_field(co, vn, plates, z, 1.0)
    gran = (f['kind'] < 0.5) & (f['pid'] >= 0)
    light = np.clip((f['kind'] > 0.5) * 1.0 + z['face'] * 1.0, 0.0, 1.0)
    blocks = z['brow'] | z['toes']
    # chips: flat chipped cuts near the plates' edges and over the blocks (4-details panels 5, 6: chipped facets)
    chips = K.facets(co, 0.026, 73) * (smooth(0.07, 0.012, f['dw']) * gran + 0.6 * blocks)
    flats = K.facets(co, 0.075, 77) * gran * 1.0 + K.facets(co, 0.06, 78) * blocks * 2.2
    pits = np.clip(K.fbm(co, 1 / 0.006, 79, 1) - 0.15, 0.0, 1.0)
    pf1, _pf2, _ = K.voronoi(co, 0.012, 87)
    dimples = smooth(0.0035, 0.0013, pf1) * smooth(-0.3, 0.25, K.fbm(co, 1 / 0.05, 88, 2))
    gr = K.grain(co)
    d_stone = (0.0015 * gr - 0.013 * chips - 0.009 * flats - 0.0016 * pits - 0.0015 * dimples) * (1.0 - 0.6 * light)
    # round 3: the lighter stone's pits coarser and sparser (fine ones read as felt at grazing angles)
    pl1, _pl2, _ = K.voronoi(co, 0.022, 89)
    lpits = smooth(0.0055, 0.0022, pl1) * smooth(-0.25, 0.3, K.fbm(co, 1 / 0.07, 90, 2))
    d_light = (0.0004 * gr - 0.003 * lpits) * light
    hair = 0.35 * K.cracks(co, 0.16, 0.0018, 61, warp=0.05) * smooth(0.2, 0.5, K.fbm(co, 1 / 0.3, 62, 2)) * (gran | z['face'])   # polish: faint (they read as tears)
    hair = hair * smooth(0.02, 0.05, f['dw']) * (1.0 - smooth(0.12, 0.06, z['eye_d']))
    fm = face_marks(co, z)
    d_face = -0.007 * fm['groove'] - 0.0025 * fm['curl']
    bulge, lash = closed_lid(co)
    d_lid = -0.0015 * lash                       # the lid itself is the dome eye_socket leaves behind the lens
    sole_g = sole_grooves(co) * z['sole']
    hair = np.maximum(hair, sole_g)
    disp = f['h'] + d_stone + d_light - 0.0025 * hair + d_face + d_lid + eye_socket(co, vn)
    disp = np.where(z['sole'], -0.007 * sole_g, disp)
    new = co + vn * disp[:, None]
    new[:, 2] = np.maximum(new[:, 2], 0.0)
    S.set_positions(ob, new)
    S.base_attrs(ob, co, {'mouth': fm['groove']})
    for name, val in (('plate_id', f['pid'].astype(np.float64)), ('plate_kind', f['kind']), ('crack', f['crack']),
                      ('plate_top', f['top']), ('chips', chips), ('hairline', hair), ('lash', lash), ('lid', bulge),
                      ('light', light), ('dw', f['dw']), ('curl', fm['curl']), ('gap', f['gap']), ('pits', lpits * light)):
        S.add_attr(ob, name, np.asarray(val, np.float64))
    _LAST.clear()
    _LAST.update({'n': len(co), 'co': new.copy(), 'vn': vn.copy(), 'base': co.copy(), 'pid': f['pid'], 'kind': f['kind'],
                  'crack': f['crack'], 'top': f['top'], 'light': light, 'dw': f['dw'], 'dj': f['dj'], 'w': f['w'],
                  'chips': chips, 'groove': fm['groove'], 'curl': fm['curl'], 'lash': lash, 'gap': f['gap'], 'pits': lpits * light})
    C.log(f'carve: {len(plates["c"])} plates; {int((f["crack"] > 0.5).sum())} of {len(co)} vertices in a crack; '
          f'height {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm')


def carve_low(ob: bpy.types.Object) -> None:
    """The low body takes the same plates (no fine detail), so the plates' flat faces and bevels reach the silhouette
    and the bake's cage (2 cm out, 5 cm in) finds the cracks."""
    soften(ob)
    co, vn = S.mesh_arrays(ob)
    z = zones(co, vn)
    plates = make_plates(co, vn)
    f = plate_field(co, vn, plates, z, 0.9)
    disp = f['h'] + eye_socket(co, vn)
    disp = np.where(z['sole'], 0.0, disp)
    new = co + vn * disp[:, None]
    new[:, 2] = np.maximum(new[:, 2], 0.0)
    S.set_positions(ob, new)
    C.log(f'carve_low: height {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm')


# ============================================================================= eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * EYE_SHAPE[0], v.co.y * EYE_R * EYE_SHAPE[1], v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1], EYE_R * EYE_DEPTH[0])))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """Small grumpy yellow eyes (4-details panel 2, 3-faces neutral): a yellow iris filling the lens round a big black
    pupil, a deeper gold ring and a dark rim, two crisp catchlights toward the key light, and the heavy upper lid in
    the face's stone crossing the top (lower toward the nose: the grumpy look). The rough pass keeps the lid matte."""
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    inner = nb.smooth(nb.math('MULTIPLY', nb.math('MULTIPLY', rx, side), -1.0), 0.0, 0.9)
    edge = nb.math('ADD', nb.math('ADD', 0.72, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', rx, rx)), 0.08)),
                   nb.math('MULTIPLY', inner, -0.04))
    upper = nb.smooth(nb.math('SUBTRACT', ry, edge), -0.015, 0.015)
    low_edge = nb.math('ADD', -0.80, nb.math('MULTIPLY', nb.math('MULTIPLY', rx, rx), 0.14))
    lower = nb.smooth(nb.math('SUBTRACT', low_edge, ry), -0.02, 0.02)
    lid = nb.math('MAXIMUM', upper, lower)
    if rough_pass:
        # glossy lens (the runtime floors roughness at 0.3), the pupil a touch matter with a low coat, matte lids
        ri0 = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.03)), 0.98),
                                         nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.02), 0.98), 0.0))
        pupil = nb.smooth(ri0, 0.5, 0.42)
        rr = nb.math('ADD', nb.math('ADD', 0.3, nb.math('MULTIPLY', pupil, 0.1)), nb.math('MULTIPLY', lid, 0.5))
        cc = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, lid), nb.math('SUBTRACT', 0.6, nb.math('MULTIPLY', pupil, 0.3)))
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, rr, cc), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    yel = PALETTE['eye']
    ix = nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.03))
    iy = nb.math('SUBTRACT', ry, 0.02)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.98), nb.math('DIVIDE', iy, 0.98), 0.0))
    deep = C.mix_hex(yel, '#C98A1E', 0.45)
    iris = nb.ramp(ri, [(0.0, C.lin(PUPIL_HEX)), (0.44, C.lin(PUPIL_HEX)), (0.49, C.lin(C.shade_hex(deep, 0.7))),
                        (0.5, C.lin(deep)), (0.55, C.lin(yel)), (0.88, C.lin(C.mix_hex(yel, '#FFF8D0', 0.3))),
                        (0.93, C.lin(C.mix_hex(yel, '#8A6410', 0.5))), (1.0, C.lin('#3A2A10'))])
    ang = nb.math('ARCTAN2', iy, ix)
    streak = nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 21.0)), 0.5)
    streak = nb.math('MULTIPLY', nb.math('ADD', streak, 0.5), nb.math('MULTIPLY', nb.smooth(ri, 0.5, 0.6), nb.smooth(ri, 0.95, 0.85)))
    c = nb.mix(nb.math('MULTIPLY', streak, 0.2), iris, nb.rgb(C.lin(C.mix_hex(yel, '#FFF4C8', 0.5))))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.2), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.18), 1.15), 0.0)), 0.21, 0.16)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.22), nb.math('ADD', ry, 0.26), 0.0)), 0.06, 0.045)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    sh = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ry, edge), -0.32, 0.0), 0.22)
    c = nb.mix(sh, c, nb.rgb(C.lin('#2A2420')), blend='MULTIPLY')
    lid_col = C.shade_hex(PALETTE['belly'], 0.86, cool=0.01)
    c = nb.mix(upper, c, nb.rgb(C.lin(lid_col)))
    c = nb.mix(lower, c, nb.rgb(C.lin(C.shade_hex(PALETTE['belly'], 0.94))))
    lash = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ry, edge), -0.07, -0.01), nb.smooth(nb.math('SUBTRACT', ry, edge), 0.06, 0.01))
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= the crystals (rigid, glowing props)
# round 2: a near-symmetric crest of big faceted crystals across both shoulder tops and down the spine (1-hero,
# 2-turnaround back), the tallest about half the head's height; never one big crystal on the head itself. Smaller ones
# sit in the seams beside the face and down the outside of each arm; the small crack crystals are added below.
CLUSTERS = [
    {'at': (0.38, 0.03, 1.50), 'count': 7, 'len': (0.10, 0.36), 'spread': 0.45, 'up': 0.45, 'lean': (0.6, 0.1, 0.0), 'jit': 0.10, 'seed': 11},
    {'at': (-0.38, 0.03, 1.50), 'count': 7, 'len': (0.10, 0.35), 'spread': 0.45, 'up': 0.45, 'lean': (-0.6, 0.1, 0.0), 'jit': 0.10, 'seed': 12},
    {'at': (0.0, 0.14, 1.66), 'count': 4, 'len': (0.11, 0.32), 'spread': 0.4, 'up': 0.8, 'lean': (0.0, 0.35, 0.0), 'jit': 0.08, 'seed': 13},
    {'at': (0.0, 0.30, 1.52), 'count': 4, 'len': (0.10, 0.22), 'spread': 0.42, 'up': 0.6, 'lean': (0.0, 0.3, 0.0), 'jit': 0.08, 'seed': 14},
    {'at': (0.0, 0.42, 1.32), 'count': 3, 'len': (0.08, 0.17), 'spread': 0.42, 'up': 0.4, 'lean': (0.0, 0.35, 0.0), 'jit': 0.06, 'seed': 15},
    {'at': (0.88, -0.05, 0.88), 'count': 3, 'len': (0.05, 0.10), 'spread': 0.45, 'up': 0.1, 'lean': (0.3, 0.0, 0.0), 'jit': 0.05, 'seed': 21},
    {'at': (-0.88, -0.05, 0.88), 'count': 3, 'len': (0.05, 0.10), 'spread': 0.45, 'up': 0.1, 'lean': (-0.3, 0.0, 0.0), 'jit': 0.05, 'seed': 23},
    {'at': (0.87, -0.04, 0.62), 'count': 2, 'len': (0.04, 0.08), 'spread': 0.45, 'up': 0.0, 'lean': (0.3, 0.0, 0.0), 'jit': 0.04, 'seed': 22},
    {'at': (-0.87, -0.04, 0.62), 'count': 2, 'len': (0.04, 0.08), 'spread': 0.45, 'up': 0.0, 'lean': (-0.3, 0.0, 0.0), 'jit': 0.04, 'seed': 24},
]
_XTAL: dict = {}


def crystal_specs() -> list[dict]:
    """Every crystal (cached, so the high and the low props match): the clusters, the knuckle gems and the small ones
    in the cracks' junctions, each seated on the carved high body."""
    if 'specs' in _XTAL:
        return _XTAL['specs']
    if not _LAST:
        raise SystemExit('grumblestone: build_props needs carve(hi_body) first (the crystals sit on the carved surface)')
    co, vn = _LAST['co'], _LAST['vn']
    specs: list[dict] = []
    for cl in CLUSTERS:
        p, nrm = K.surface_point(co, vn, cl['at'])
        for sp_ in K.cluster(p - nrm * 0.012, nrm, cl['count'], cl['len'], cl['spread'], cl['seed'], up=cl['up'], lean=cl['lean'],
                             jitter=cl['jit'], radius_k=0.34):
            q, nq = K.surface_point(co, vn, sp_['base'])
            nq = nq / np.linalg.norm(nq)
            ax = sp_['axis'] / np.linalg.norm(sp_['axis'])
            if ax @ nq < 0.45:
                ax = ax + nq * (0.45 - ax @ nq) * 1.6
                ax = ax / np.linalg.norm(ax)
            sp_['base'] = q - nq * 0.015
            for _try in range(2):
                tip_ = sp_['base'] + ax * sp_['length']
                ti, tn = K.surface_point(co, vn, tip_)
                clear = float((tip_ - ti) @ (tn / np.linalg.norm(tn)))
                if clear >= 0.55 * sp_['length']:
                    break
                ax = nq + 0.25 * ax
                ax = ax / np.linalg.norm(ax)
            sp_['axis'] = ax
            if clear >= 0.4 * sp_['length']:
                specs.append(sp_)
            else:
                C.log(f"crystals: dropped one at {np.round(sp_['base'], 3)} (only {clear * 100:.1f} cm clear of the body)")
    # the knuckle gems (4-details panel 3): a big faceted gem set in the front of each finger's upper block, facing the
    # knuckle's own way round the fist's corner
    for s in (1, -1):
        for i, kn in enumerate(knuckles(s)):
            k, d = kn['k'], kn['d']
            ax = d + v3((0.0, 0.0, 0.1))
            base = kn['c'] + d * (FINGER_UP['half'][1] * k - 0.004) + v3((0.0, 0.0, 0.01))
            specs.append({'base': base, 'axis': ax / np.linalg.norm(ax), 'length': 0.062 * k, 'radius': 0.054 * k,
                          'sides': 8, 'kind': 'gem', 'bury': 0.5, 'aspect': 1.25, 'seed': 500 + i + (0 if s > 0 else 10), 'anchor': base})
    # small crystals growing in the cracks (shoulders, arms, the back and the hood; few on the legs, none on the chest)
    w = _LAST['w']
    zz = zones(co, vn)
    up = co[:, 2] > 0.55
    ok = (_LAST['kind'] == 0) & (_LAST['pid'] >= 0) & up & ~zz['fist'] & (co[:, 1] > -0.42) & (zz['face_sdf'] > 0.1)
    ok &= (_LAST['dw'] < 0.8 * w) & (_LAST['dj'] < 2.0 * w + 0.004)
    spots = K.crack_spots(co, _LAST['dw'], _LAST['dj'], ok, 0.16, w, SEED + 5, 24)
    rng = np.random.default_rng(SEED + 6)
    for j, i in enumerate(spots):
        nrm = vn[i] / np.linalg.norm(vn[i])
        L = rng.uniform(0.05, 0.09)
        for m in range(1 + int(rng.random() < 0.5)):
            ax = K.tilt(nrm, 0.25, rng)
            b = co[i] - nrm * 0.03 + rng.normal(0, 0.003, 3)
            specs.append({'base': b, 'axis': ax, 'length': L * (1.0 if m == 0 else 0.7), 'radius': L * 0.3,
                          'seed': 900 + 3 * j + m, 'anchor': co[i], 'bury': 0.45})
    C.log(f'crystals: {len(specs)} ({len(spots)} crack spots)')
    _XTAL['specs'] = specs
    return specs


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    ob = K.crystals_object(f'{tag}_crystals', crystal_specs())
    return [ob]


def preview_prop_colour(name: str) -> str:
    return C.mix_hex(PALETTE['accent'], '#FFFFFF', 0.15)


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """Each crystal rides the skin it sits on, rigidly: every vertex of a crystal copies lo_body's weights at its
    anchor (the nearest body vertex), so a gem moves with its fist and a cluster with its shoulder."""
    from mathutils.kdtree import KDTree
    body = bpy.data.objects.get('lo_body')
    anchor = attr('anchor')
    if body is None:
        return [(np.ones(len(co), bool), {'chest': np.ones(len(co))})]
    bn, W = S.body_weights(body)
    bco, _ = S.mesh_arrays(body)
    kd = KDTree(len(bco))
    for i, p in enumerate(bco):
        kd.insert(Vector(p), i)
    kd.balance()
    uniq, inv = np.unique(np.round(anchor, 5), axis=0, return_inverse=True)
    rows = np.zeros((len(uniq), len(bn)))
    for u, p in enumerate(uniq):
        near = kd.find_n(Vector(p), 6)
        rows[u] = np.mean([W[j] for _c, j, _d in near], axis=0)
    out: dict[str, np.ndarray] = {}
    for j, nm in enumerate(bn):
        if nm in names and rows[:, j].max() > 1e-4:
            out[nm] = rows[inv.ravel(), j]
    return [(np.ones(len(co), bool), out)]


# ============================================================================= paint
def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def colours(pal: dict) -> dict:
    """Every derived colour (CONTENT has no hex for them): granite flecks and the crack's geode violets, all made from
    the palette."""
    body, light, cry = pal['body'], pal['belly'], pal['accent']
    return {
        'granite': body,
        'granite_dark': C.shade_hex(body, 0.62, cool=0.01),
        'granite_warm': C.mix_hex(body, C.mix_hex(body, '#8A5A3A', 0.6), 0.5),        # the rusty brown grains
        'granite_top': C.mix_hex(body, light, 0.3),
        'fleck_dark': C.shade_hex(body, 0.32),
        'fleck_pale': C.mix_hex(light, '#FFFFFF', 0.35),
        'light': light,
        'light_dark': C.shade_hex(light, 0.8, cool=0.01),
        'crack': cry,
        'crack_gap': C.mix_hex(C.shade_hex(body, 0.35), cry, 0.12),
        'crack_glow': cry,
        'crystal': cry,
        'crystal_deep': C.shade_hex(cry, 0.62, cool=0.02),
        'crystal_pale': C.mix_hex(cry, '#FFFFFF', 0.5),
    }


def _body_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(paint linear RGB, rough (1, roughness, coat), glow) per vertex of a body source."""
    col = colours(pal)
    k = len(I['co'])
    pid = I['pid'].astype(np.int64)
    ph = U.plate_hash(pid, 5)
    ph2 = U.plate_hash(pid, 9)
    mott = K.fbm(I['co'], 1 / 0.12, 81, 3)
    granite = lin(col['granite'])[None] * (1.04 + 0.16 * ph + 0.06 * mott)[:, None] * np.array([[1.04, 1.0, 0.94]])
    warm = (smooth(0.25, 1.0, ph2) * 0.45)[:, None]
    granite = granite * (1 - warm) + lin(col['granite_warm'])[None] * (1.04 + 0.1 * ph[:, None]) * warm
    lt = I['light'][:, None]
    light = lin(col['light'])[None] * (1.06 + 0.06 * ph[:, None] + 0.04 * mott[:, None])
    light = light * (1.0 - 0.35 * np.asarray(I.get('pits', np.zeros(k)))[:, None])      # its pits a little darker
    rgb = granite * (1 - lt) + light * lt
    # the plates' bevelled shoulders a little darker, the chips paler (fresh broken stone)
    rimk = (smooth(0.05, 0.01, I['dw']) * 0.14 * (1 - lt[:, 0]))[:, None]
    rgb = rgb * (1 - rimk)
    chip = (I['chips'] * 0.0)[:, None]          # round 3: no per-vertex chip paint (it streaked down the bevels)
    rgb = rgb * (1 - chip) + lin(col['granite_top'])[None] * chip
    # the cracks: deep violet at the floor (it glows), dark where the bevels meet it
    gk = (np.asarray(I.get('gap', I['crack'])) * 0.6)[:, None]
    rgb = rgb * (1 - gk) + lin(col['crack_gap'])[None] * gk
    ck = I['crack'][:, None]
    chestk = (I['kind'] > 0.5)[:, None]
    crack_col = np.where(chestk, lin(col['light_dark'])[None] * 0.5, lin(col['crack'])[None])
    rgb = rgb * (1 - ck) + crack_col * ck
    lsh = (np.clip(np.asarray(I.get('lash', np.zeros(k))), 0.0, 1.0) * 0.8)[:, None]       # the closed lid's line
    rgb = rgb * (1 - lsh) + lin(LASH_HEX)[None] * lsh
    mo = (np.clip(I.get('mouth', np.zeros(k)) * 1.2, 0.0, 1.0) * 0.75)[:, None]
    rgb = rgb * (1 - mo) + lin(col['light_dark'])[None] * 0.45 * mo
    hl = (I['hairline'] * 0.5)[:, None]
    rgb = rgb * (1 - hl) + lin(col['granite_dark'])[None] * 0.7 * hl
    rough = np.stack([np.ones(k), 0.82 - 0.1 * I['light'] - 0.3 * I['crack'], 0.05 + 0.3 * I['crack']], axis=1)
    chest_seam = (I['kind'] > 0.5) * I['crack']
    glow = np.clip(I['crack'] * (I['kind'] < 0.5), 0.0, 1.0)
    glow = glow + 0.0 * chest_seam
    return rgb, rough, glow


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        get = lambda nm, d=0.0, ob=ob: S.attr_array(ob, nm).astype(np.float64) if nm in ob.data.attributes else np.full(len(ob.data.vertices), d)  # noqa: E731
        co = S.attr_array(ob, 'root').astype(np.float64) if 'root' in ob.data.attributes else S.mesh_arrays(ob)[0]
        I = {'co': co, 'pid': get('plate_id', -1.0), 'kind': get('plate_kind', -1.0), 'crack': get('crack'), 'dw': get('dw', 1.0),
             'light': get('light'), 'chips': get('chips'), 'hairline': get('hairline'), 'mouth': get('mouth') + get('curl'),
             'gap': get('gap'), 'pits': get('pits'), 'lash': get('lash')}
        rgb, rough, glow = _body_paint(I, PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.add_attr(ob, 'glow', glow)
    for ob in props:
        a = S.attr_array(ob, 'xtal').astype(np.float64)
        t, fs, gem = a[:, 0], a[:, 1], a[:, 2]
        col = colours(PALETTE)
        base = lin(col['crystal_deep'])[None] * (1 - t[:, None]) + lin(col['crystal'])[None] * t[:, None]
        tip = (smooth(0.8, 1.0, t) * 0.5 * (1.0 - gem))[:, None]
        base = base * (1 - tip) + lin(col['crystal_pale'])[None] * tip
        base = base * (1.0 + 0.25 * fs)[:, None]           # a shade per facet: bright and deep faces side by side
        S.set_colour_attr(ob, 'paint', np.clip(base, 0.0, 1.0))
        n = len(t)
        S.set_colour_attr(ob, 'rough', np.stack([np.ones(n), np.full(n, 0.3), np.full(n, 0.8)], axis=1))
        S.add_attr(ob, 'glow', np.clip((0.3 + 0.45 * smooth(0.35, 1.0, t) + 0.08 * fs) * (1.0 - gem) + (0.55 + 0.1 * fs) * gem, 0.0, 1.0))


def body_material(name: str, attr: str, pal: dict, marks):
    """The body's colour pass: the painted attribute plus granite flecks per pixel (black, pale and rust grains of a
    few millimetres; 4-details panel 6), fewer and finer on the lighter stone."""
    m, nb = new_mat(name)
    base = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    light = nb.attribute('light').outputs['Fac']
    crack = nb.attribute('crack').outputs['Fac']
    col = colours(pal)
    stone = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, crack), nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', light, 0.55)))
    warp = nb.vmath('ADD', pos, nb.vmath('SCALE', nb.comb(nb.noise(pos, 40.0, 1.0, 0.5), nb.noise(nb.vmath('ADD', pos, nb.comb(1.7, 0.3, 2.9)), 40.0, 1.0, 0.5), 0.0), scale=0.004))
    dark = nb.math('MULTIPLY', nb.smooth(nb.voronoi(warp, 170.0, 'F1'), 0.24, 0.16), stone)
    c = nb.mix(nb.math('MULTIPLY', dark, 0.8), base, nb.rgb(C.lin(col['fleck_dark'])))
    rust = nb.math('MULTIPLY', nb.smooth(nb.voronoi(nb.vmath('ADD', warp, nb.comb(-5.3, 2.9, 4.1)), 110.0, 'F1'), 0.26, 0.18), stone)
    rust = nb.math('MULTIPLY', rust, nb.smooth(nb.noise(nb.vmath('ADD', pos, nb.comb(2.2, 5.1, 0.4)), 18.0, 1.0, 0.5), 0.45, 0.6))
    c = nb.mix(nb.math('MULTIPLY', rust, 0.65), c, nb.rgb(C.lin(col['granite_warm'])))
    pale = nb.math('MULTIPLY', nb.smooth(nb.voronoi(nb.vmath('ADD', warp, nb.comb(3.1, 7.7, 1.3)), 240.0, 'F1'), 0.18, 0.11), stone)
    c = nb.mix(nb.math('MULTIPLY', pale, 0.55), c, nb.rgb(C.lin(col['fleck_pale'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """The shape preview: granite with a tone per plate, the lighter face and chest, violet cracks."""
    if _LAST and _LAST.get('n') == len(co):
        I = {'co': _LAST['base'], 'pid': _LAST['pid'].astype(np.float64), 'kind': _LAST['kind'], 'crack': _LAST['crack'],
             'dw': _LAST['dw'], 'light': _LAST['light'], 'chips': _LAST['chips'], 'hairline': np.zeros(len(co)),
             'mouth': _LAST['groove'] + _LAST['curl'], 'gap': _LAST['gap'], 'pits': _LAST['pits'], 'lash': _LAST['lash']}
        rgb, _r, glow = _body_paint(I, PALETTE)
        g = glow[:, None]
        return rgb * (1 - g) + lin(PALETTE['accent'])[None] * 1.4 * g
    z = zones(co, vn)
    light = (z['face'] | z['chest'])[:, None]
    return np.where(light, lin(PALETTE['belly'])[None], lin(PALETTE['body'])[None])


REVIEW = {'centre': (0.0, -0.05, 0.92), 'size': 2.35, 'head': ((0.0, -0.55, 1.42), 0.85)}
