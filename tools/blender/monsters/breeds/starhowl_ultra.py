"""Starhowl at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9): the recipe for `tools/blender/monsters/build_ultra.py`
(contract: breeds/RECIPE.md).

A sleek, noble wolf of the night sky (CONTENT §2.2 #25; chatgpt/monsters/06-starhowl): an athletic wolf with long legs
and a proud head with a narrow muzzle; tall pointed ears with a pink hollow (`starhowl_ears`); midnight-indigo fur in
thick layered clumps, lighter indigo on the belly, the inside of the legs and the lower legs, a pale lavender muzzle,
cheeks and brows; tiny twinkling stars all over, constellations (star points joined by faint lines) on the shoulders,
flanks, haunches and legs, and a star cluster on the brow; glowing pale eyes; a long aurora mane of silky locks round
the neck and shoulders, teal shading to rose (`starhowl_mane`, spring chains); a bushy tail whose lower plume shades to
teal and rose, tipped with a small glowing star.

Size: CARD 1.3 × Puddlepup → HEIGHT_UNITS 195, modelled 1.28 m to the ear tips (RECIPE: HEIGHT_UNITS / 150 m, Puddlepup
0.986 m at 150). Measurements from 2-turnaround.png at 502 px / m.
Metres; the monster faces −Y, Z is up, +X is its left. Palette: CONTENT §2.2 #25 (#2B2F6B / #4C5199 / #6EE7C8, rose
#F49AC1 / #E8F1FF). No secret variant.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3
from monsters.breeds import starhowl_ears as E
from monsters.breeds import starhowl_locks as LK
from monsters.breeds import starhowl_mane as M

ID = 'starhowl'
LOOK = 'starhowl-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 195

PALETTE = {'body': '#2B2F6B', 'belly': '#4C5199', 'accent': '#6EE7C8', 'eye': '#E8F1FF', 'rose': '#F49AC1'}
VARIANTS: dict = {}

NOSE_HEX = '#15161E'
MOUTH_HEX = '#261A33'      # round 8: darker (it is what shows when the jaws open)
LINER_HEX = '#0E0F22'
BROW_HEX = '#15173C'       # the dark brow strokes (round 7)


def colours(pal: dict) -> dict:
    """Every derived colour of a palette."""
    indigo, light, teal = pal['body'], pal['belly'], pal['accent']
    rose = pal.get('rose', '#F49AC1')
    return {
        'indigo': indigo, 'light': light, 'teal': teal, 'rose': rose,
        # the pale lavender of the muzzle, cheeks, chin and brows (the pictures: a soft lilac grey, never white)
        'pale': C.mix_hex(light, '#ECEAF8', 0.66),
        'brow': C.mix_hex(light, '#E9EBFA', 0.62),
        # the ears' hollow: a dusty rose (the pictures), from the mane's rose toward a warm shade
        'inner_ear': C.mix_hex(rose, '#B86F82', 0.45),
        'ear_fluff': C.mix_hex(light, '#D8DAF0', 0.55),
        'pad': C.mix_hex(indigo, '#2A2833', 0.55),
        'claw': '#24242E',
        'aurora_root': C.mix_hex(indigo, teal, 0.45),
        'mane_mid': '#C9F6E8',      # the pale mint between the mane's teal and its rose (round 8)
        'mane_root': C.mix_hex(indigo, light, 0.22),        # the mane's indigo roots (round 7), a touch lifted so they read as fur
        'teal_deep': C.mix_hex(teal, '#2B7FA6', 0.5),
        'teal_pale': C.mix_hex(teal, '#C8F6FF', 0.38),
        'star_white': '#DCEBFF',
        'star_gold': '#FFE3A0',
        'line': '#FFF0D2',
        'tail_star': '#FFF2B0',
        'lid': C.mix_hex(indigo, light, 0.45),
    }


# ----------------------------------------------------------------------------- the head
# round 6 (review: the head sunk into the collar): the head carried 3 cm higher (the ears' tips, which set the height,
# stay where they are), the collar starting behind the cheeks
HEAD_C = Vector((0.0, -0.435, 1.05))
HEAD_R = (0.112, 0.122, 0.112)
# round 7 (the owner: the eyes are a bit wide and round; they want the hero's shape and expression). Measured on
# 3-faces neutral and 1-hero: each eye is about 0.24 of the skull's width (ours were 0.34) and about 1.5 times as wide
# as it is tall; the upper lid is a round arc that follows the iris, the lower lid is flatter; the saturated iris fills
# the opening's height (white only at the two sides), under a heavy dark upper lash line with a flick.
EYE_C = {s: Vector((0.058 * s, -0.546, 1.064)) for s in (1, -1)}
EYE_R = 0.032
EYE_W, EYE_H = 0.9, 0.64           # half-width and upper half-height (× EYE_R); nearly all of it shows (see EYE_DEPTH)
EYE_LOW = 0.84                     # the lower half's height as a share of the upper (a flatter lower lid): 42 mm tall in all
IRIS_R = 0.56                      # the iris's radius (× EYE_R = 18 mm): both lids cut it, a little white at the sides
IRIS_DY = -0.03                    # the iris's centre below the eye's axis (× EYE_R)
# round 5 (review: round, bulging, startled eyes): a flatter dome whose rim sits well inside the skin (0.28 high, set
# 0.3 in: the apex is flush with the face), pinched toward the corners (`EYE_PINCH`: the lens is an almond, not an
# oval), the outer corner raised 11°
EYE_DEPTH = (0.24, 0.16)             # round 8: the rim 5 mm under the skin (it was 8: only the lens's round middle showed)
EYE_PINCH = 0.42                      # the lens's height at the corners is (1 − PINCH) of its height in the middle
EYE_TILT = math.radians(22)           # round 7: the outer corner well above the inner (3-faces: the eyes slant up into the wing)
IRIS_OUT = 0.0                        # the iris sits this much (× EYE_R) toward the outer corner
# round 2: a long, narrow wedge muzzle about 0.8 × the cranium, flowing from the brow, and a small rounded-triangle nose
# round 5: a touch lower (a clear stop), the nose smaller; round 6: a little longer and tapered (a boxy snout from the front)
NOSE_C = Vector((0.0, -0.702, 0.98))
MUZZLE = ((0.0, -0.625, 0.97), (0.05, 0.105, 0.05))
CHEEK = (0.06, -0.47, 0.974, 0.044)        # round 8: smaller (white cheek balls made the front view a puffy snout)
BROW_STAR = Vector((0.0, -0.554, 1.138))
BROW_PATCH = ((0.0, -0.53, 1.165), (0.055, 0.05, 0.075))     # the cluster's patch of short, flat fur


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye (+Z of its dome looks out, more forward than the head's normal: a
    wolf's eyes face ahead)."""
    c = EYE_C[s]
    surf_n = Vector(((c.x - HEAD_C.x) / HEAD_R[0] ** 2, (c.y - HEAD_C.y) / HEAD_R[1] ** 2, (c.z - HEAD_C.z) / HEAD_R[2] ** 2)).normalized()
    look = (surf_n * 0.5 + Vector((0, -1, 0)) * 0.5).normalized()
    look = (look + Vector((0, 0, 0.04))).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    # tilt: rotate the across and up axes about the look axis so the outer corner rises
    a = EYE_TILT * s
    x2 = xax * math.cos(a) + yax * math.sin(a)
    y2 = yax * math.cos(a) - xax * math.sin(a)
    return c, x2, y2, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


LID_LASH, LID_DROP, LID_W = 0.12, 0.14, 0.94


def blink_pivot(s: int) -> tuple[Vector, Vector, Vector]:
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * EYE_H * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.74, 0.04, 0.2)
ATLAS_DENSITY = {'lo_eyes': 2.2, 'lo_fins': 0.3}       # round 7: the lenses are about half their old area; they keep their texels
BODY_TRIS = 58000      # round 7: the sculpted locks of the mane and the plume are the body's own triangles (was 40000)

# ----------------------------------------------------------------------------- the body's layout (2-turnaround.png)
LEGS = {'FL': (0.1, -0.3), 'FR': (-0.1, -0.3), 'BL': (0.11, 0.41), 'BR': (-0.11, 0.41)}
PAW_Y = {'F': -0.35, 'B': 0.405}
TOE_DX = (-0.048, -0.016, 0.016, 0.048)        # round 8: toes a little apart (mittens)
TAIL_PTS = [(0.0, 0.47, 0.67), (0.0, 0.63, 0.74), (0.0, 0.8, 0.8), (0.0, 0.97, 0.86), (0.0, 1.12, 0.93)]  # round 4b: 1.2x longer
STAR_C = (0.0, 1.27, 1.06)      # round 8: a bold star standing clear of the plume's tip (it was small and buried)


def paw_centre(leg: str) -> Vector:
    x, _y = LEGS[leg]
    return Vector((x, PAW_Y[leg[0]], 0.04))


def toe_centres(leg: str) -> list[Vector]:
    pc = paw_centre(leg)
    k = 1.0 if leg[0] == 'F' else 0.95
    return [Vector((pc.x + dx * k, pc.y - (0.056 - 0.45 * abs(dx)) * k, 0.031)) for dx in TOE_DX]


def claw_centres(leg: str) -> list[Vector]:
    return [t + Vector((0.0, -0.029, -0.011)) for t in toe_centres(leg)]


def pad_centre(leg: str) -> tuple[Vector, tuple[float, float, float]]:
    pc = paw_centre(leg)
    return Vector((pc.x, pc.y + 0.006, 0.006)), (0.034, 0.03, 0.014)


def head_parts() -> list[Part]:
    return [
        Part('head', 'sphere', loc=tuple(HEAD_C), radius=1.0, scale=HEAD_R),
        # round 5 (review: a smooth tube muzzle that reads as a beak in profile, a bulging skull): a flatter forehead,
        # a brow shelf over the eyes (the stop under it; the lids hooded from the side), a fuller lower jaw with chin
        # fur under the muzzle so the head is deep at the stop and tapers to the nose (4-details panel 1)
        Part('forehead', 'sphere', loc=(0.0, -0.465, 1.102), radius=0.07, scale=(1.25, 0.9, 0.72)),
        # round 6: no brow ridges (they read as heavy, grumpy brows); the brows are paint only
        Part('cheek', 'sphere', loc=CHEEK[:3], radius=CHEEK[3], scale=(0.95, 1.3, 0.8), mirror=True),
        Part('jaw', 'sphere', loc=(0.0, -0.495, 0.952), radius=0.065, scale=(0.88, 1.1, 0.66)),
        # the upper muzzle: a tapered wedge from inside the brow to the nose
        # round 4: a soft wedge, wide at the stop and flatter on top, narrowing to a rounded tip (not a round tube)
        # round 6: tapered more from the stop to the tip (from the front it was a short boxy snout)
        Part('muzzleBase', 'sphere', loc=(0.0, -0.545, 0.98), radius=1.0, scale=(0.044, 0.05, 0.047)),      # round 8: a slimmer wedge from the front
        Part('muzzle', 'sphere', loc=(0.0, -0.61, 0.977), radius=1.0, scale=(0.031, 0.09, 0.037)),
        Part('muzzleTip', 'sphere', loc=(0.0, -0.672, 0.975), radius=1.0, scale=(0.02, 0.032, 0.029)),
        Part('bridge', 'sphere', loc=(0.0, -0.62, 0.996), radius=1.0, scale=(0.024, 0.085, 0.02), rot=(5.0, 0.0, 0.0)),
        # the lower jaw, narrower, under it (the smile runs along the seam)
        Part('lowerjaw', 'tube', loc=(0.0, -0.5, 0.942), to=(0.0, -0.662, 0.952), radius=0.04, r2=0.02),
        Part('chinFur', 'sphere', loc=(0.0, -0.565, 0.927), radius=1.0, scale=(0.036, 0.062, 0.03)),
        Part('nose', 'sphere', loc=tuple(NOSE_C), radius=0.0135, scale=(1.12, 1.0, 0.8)),
        # round 3: a thicker neck and a full throat under the jaw (the chin sits on the ruff, no bare stalk)
        Part('neck', 'capsule', loc=(0.0, -0.28, 0.72), to=(0.0, -0.415, 0.98), radius=0.118),

    ]


def leg_parts(leg: str) -> list[Part]:
    """Round 2 (review: thin stilts, no hock, mitten paws): fuller forearms, a clear angled hock on the hind legs, paws
    with four separate toes and dark claws."""
    x, y = LEGS[leg]
    s = 1 if x > 0 else -1
    pc = paw_centre(leg)
    if leg[0] == 'F':
        ps = [
            Part(f'arm{leg}', 'capsule', loc=(x + 0.005 * s, y + 0.02, 0.54), to=(x, y + 0.035, 0.36), radius=0.078),
            Part(f'fore{leg}', 'tube', loc=(x, y + 0.03, 0.37), to=(x, y + 0.012, 0.11), radius=0.064, r2=0.048),
            Part(f'pastern{leg}', 'tube', loc=(x, y + 0.012, 0.12), to=(x, pc.y + 0.02, 0.05), radius=0.048, r2=0.052),
        ]
    else:
        ps = [
            Part(f'thigh{leg}', 'capsule', loc=(x, y - 0.03, 0.56), to=(x + 0.005 * s, y - 0.12, 0.38), radius=0.094),
            Part(f'gaskin{leg}', 'tube', loc=(x + 0.005 * s, y - 0.11, 0.39), to=(x, y + 0.1, 0.2), radius=0.07, r2=0.046),
            Part(f'hock{leg}', 'sphere', loc=(x, y + 0.105, 0.2), radius=0.045, scale=(0.9, 1.0, 1.1)),
            Part(f'meta{leg}', 'tube', loc=(x, y + 0.1, 0.2), to=(x, pc.y + 0.03, 0.06), radius=0.044, r2=0.05),
        ]
    k = 1.0 if leg[0] == 'F' else 0.95
    ps.append(Part(f'paw{leg}', 'sphere', loc=tuple(pc), radius=0.064 * k, scale=(1.05, 1.22, 0.7)))
    for i, (t, c) in enumerate(zip(toe_centres(leg), claw_centres(leg))):
        ps.append(Part(f'toe{leg}{i}', 'sphere', loc=tuple(t), radius=0.028 * k, scale=(0.9, 1.3, 1.0)))
        ps.append(Part(f'claw{leg}{i}', 'sphere', loc=tuple(c), radius=0.0125, scale=(0.75, 2.4, 0.75), rot=(-28.0, 0.0, 0.0)))
    return ps


def torso_parts() -> list[Part]:
    ps = [
        Part('chest', 'sphere', loc=(0.0, -0.33, 0.59), radius=0.16, scale=(0.84, 1.05, 1.27)),      # round 9: deep (to z 0.39)
        Part('ribs', 'tube', loc=(0.0, -0.24, 0.6), to=(0.0, 0.12, 0.628), radius=0.15, r2=0.118),      # round 9: the belly tucks up
        Part('loin', 'tube', loc=(0.0, 0.1, 0.628), to=(0.0, 0.36, 0.64), radius=0.118, r2=0.108),
        Part('haunch', 'sphere', loc=(0.095, 0.39, 0.56), radius=0.12, scale=(0.85, 1.12, 1.3), mirror=True),
        Part('rump', 'sphere', loc=(0.0, 0.43, 0.625), radius=0.11, scale=(1.25, 1.0, 0.9)),
        Part('shoulder', 'sphere', loc=(0.1, -0.3, 0.575), radius=0.1, scale=(0.72, 1.0, 1.45), mirror=True),
        Part('tailroot', 'tube', loc=TAIL_PTS[0], to=TAIL_PTS[1], radius=0.078, r2=0.09),
        # the plume hangs below the tail's spine (a big bushy brush, star at the top of its tip)
        # round 4b: about 1.6x deeper (it hangs well below the spine, the 2-turnaround side) and 1.2x longer; a little
        # wider (the back view's fan); blends between the lobes keep one soft brush (no beads)
        # round 5: a little narrower side to side (from behind the core showed as a smooth pink paddle)
        # round 7 (the owner: the plume is thin from behind and wants volume; 2-turnaround back: an egg about as wide as
        # the body): the core wider again (about ±0.12 m at its fullest), under sculpted pointed clumps (starhowl_locks)
        # that break the smooth paddle rounds 4–6 showed from behind
        Part('plume1', 'sphere', loc=(0.0, 0.62, 0.665), radius=0.13, scale=(0.66, 1.2, 1.08)),
        Part('plume12', 'sphere', loc=(0.0, 0.71, 0.635), radius=0.165, scale=(0.64, 1.15, 1.08)),
        Part('plume2', 'sphere', loc=(0.0, 0.81, 0.625), radius=0.2, scale=(0.6, 1.1, 1.04)),
        Part('plume23', 'sphere', loc=(0.0, 0.92, 0.665), radius=0.185, scale=(0.6, 1.08, 1.02)),
        Part('plume3', 'sphere', loc=(0.0, 1.0, 0.725), radius=0.155, scale=(0.6, 1.08, 1.0)),
        Part('plume34', 'sphere', loc=(0.0, 1.06, 0.8), radius=0.12, scale=(0.62, 1.08, 1.0)),
        Part('plume4', 'sphere', loc=(0.0, 1.1, 0.87), radius=0.088, scale=(0.68, 1.08, 1.0)),
        Part('plume45', 'sphere', loc=(0.0, 1.125, 0.92), radius=0.064, scale=(0.75, 1.08, 1.0)),
        Part('plume5', 'sphere', loc=(0.0, 1.14, 0.955), radius=0.048),
    ]
    for leg in LEGS:
        ps.extend(leg_parts(leg))
    return ps


def all_parts() -> list[Part]:
    return head_parts() + torso_parts() + MANE_PARTS + RUFF_PARTS


# Round 4: the mane is a sculpted volume (the silhouette holds by itself) under long lying locks and three layers of long
# fur cards, painted teal over rose with glowing lock tips.
# Round 5 (review: two separate lobes hanging behind the ears read as earmuffs or a stole, a bare neck between them, no
# mane on the crown): ONE continuous lion-like collar (1-hero, 2-turnaround front). Two rings of ellipsoids round the
# neck axis: the first frames the face (a crest behind the skull up to the ears' roots, wide flares at cheek height,
# closed under the chin), the second lies over the withers and shoulders and crosses the chest; lower lobes hang to
# the elbows, and a tuft stands between the ears. The lavender bib (`RUFF_PARTS`) sits inside the collar's front.
def _skirt_ring(name: str, z: float, x_half: float, y_front: float, y_back: float, n: int, r, back_from: float = 1.0,
                stagger: float = 0.0) -> list[Part]:
    """One horizontal slice of the mane: `n` ellipsoids of half-sizes `r` round an ellipse at height `z`, so their
    union fills the section |x| < x_half, y_front < y < y_back. Sectors behind `back_from` (|θ| / π) are left out;
    `stagger` (0..1 of a step) turns the ring so neighbouring slices' bumps don't line up in columns."""
    rx, ry, rz = r
    cy = 0.5 * (y_front + y_back)
    ax, ay = max(x_half - rx, 0.0), max(0.5 * (y_back - y_front) - ry, 0.0)
    parts = []
    for i in range(n):
        th = -math.pi + 2.0 * math.pi * (i + 0.5 + stagger) / n      # θ = 0 the back, ±π the front (the throat)
        th = (th + math.pi) % (2.0 * math.pi) - math.pi
        if abs(th) / math.pi < 1.0 - back_from:
            continue
        parts.append(Part(f'{name}{i}', 'sphere', loc=(ax * math.sin(th), cy + ay * math.cos(th), z), radius=1.0, scale=(rx, ry, rz)))
    return parts


# the collar's profile down the body (1-hero, 2-turnaround front and side): a halo behind the skull, widest at cheek
# and chin height, over the withers at the top of the chest, tapering to a rounded point between the forelegs. Keyed
# by height: half-width, front, back, how much of the ring (from the front) and the ellipsoids' half-sizes.
COLLAR_KEYS = [
    # round 9 (review: a bell, the head low inside it, sleeves at the elbows): slim round the neck, no wider than the
    # shoulders, ending above the elbows; the ribbons (starhowl_locks) are the mane's mass
    (1.03, 0.115, -0.39, -0.27, 1.0, (0.045, 0.05, 0.04)),
    (0.95, 0.15, -0.44, -0.235, 1.0, (0.06, 0.065, 0.06)),
    (0.89, 0.175, -0.48, -0.2, 1.0, (0.068, 0.072, 0.066)),
    (0.82, 0.19, -0.5, -0.17, 1.0, (0.072, 0.076, 0.07)),
    (0.74, 0.185, -0.5, -0.15, 1.0, (0.072, 0.076, 0.066)),
    (0.67, 0.16, -0.49, -0.2, 0.75, (0.068, 0.07, 0.064)),
    (0.61, 0.12, -0.47, -0.3, 0.6, (0.06, 0.06, 0.06)),
]


def _collar_parts(step: float = 0.04) -> list[Part]:
    """Slices every `step` metres, interpolated between COLLAR_KEYS, staggered half a step in turn (their vertical
    overlap is deep, so the union has no waists: round 4's stacked rings)."""
    zs = [k[0] for k in COLLAR_KEYS]
    cols = list(zip(*COLLAR_KEYS))
    parts = []
    z = zs[0]
    i = 0
    while z >= zs[-1] - 1e-6:
        f = lambda c: float(np.interp(z, zs[::-1], c[::-1]))
        r = tuple(f([k[5][j] for k in COLLAR_KEYS]) for j in range(3))
        n = max(8, int(round(2.0 * math.pi * f(cols[1]) / (0.8 * r[0]))))
        parts += _skirt_ring(f'collar{i}', z, f(cols[1]), f(cols[2]), f(cols[3]), n, r, back_from=f(cols[4]), stagger=0.5 * (i % 2))
        z -= step
        i += 1
    return parts


MANE_PARTS = _collar_parts() + [
    # the teal tuft between the ears, swept back
    Part('crownTuft', 'sphere', loc=(0.0, -0.36, 1.125), radius=1.0, scale=(0.03, 0.045, 0.022), rot=(30.0, 0.0, 0.0)),
]
# the lavender bib: one smooth volume from under the chin down the throat to the chest (no stacked rings), flush
# with the collar's front
RUFF_PARTS = [
    Part('bib', 'sphere', loc=(0.0, -0.475, 0.775), radius=1.0, scale=(0.085, 0.058, 0.165)),      # round 9: thinner over the chest
]


def _part_norm(p: np.ndarray, part: Part) -> np.ndarray:
    """Normalised radius of points in a (rotated, scaled, maybe mirrored) sphere Part: < 1 inside; the nearer twin."""
    from mathutils import Euler
    R = np.array(Euler([math.radians(a) for a in part.rot], 'XYZ').to_matrix(), float)
    r = np.array(part.scale, float) * part.radius
    out = np.full(len(p), 9.0)
    for side in ((1, -1) if part.mirror else (1,)):
        loc = np.array(part.loc, float)
        Rs = R
        if side < 0:
            loc[0] = -loc[0]
            Mi = np.diag([-1.0, 1.0, 1.0])
            Rs = Mi @ R @ Mi
        q = (p - loc) @ Rs
        out = np.minimum(out, np.linalg.norm(q / r, axis=1))
    return out


def mane_norm(p: np.ndarray) -> np.ndarray:
    """Normalised radius of points in the collar: < 1 inside the section COLLAR_KEYS describes at the point's height
    (analytic, not per slice: `zones` runs on millions of points), plus the crown tuft."""
    zs = np.array([k[0] for k in COLLAR_KEYS])[::-1]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    zc = np.clip(z, zs[0], zs[-1])
    col = lambda i: np.interp(zc, zs, np.array([k[i] for k in COLLAR_KEYS])[::-1])
    xh, yf, yb, back_from = col(1), col(2), col(3), col(4)
    rz = np.interp(zc, zs, np.array([k[5][2] for k in COLLAR_KEYS])[::-1])
    cy, ay = 0.5 * (yf + yb), 0.5 * (yb - yf)
    sec = np.sqrt((x / xh) ** 2 + ((y - cy) / ay) ** 2 + ((z - zc) / rz) ** 2)
    # the slices that leave out the back sectors: the section ends at the angle back_from
    th = np.abs(np.arctan2(x / xh, (y - cy) / ay)) / math.pi
    sec = np.where(th < 1.0 - back_from, np.maximum(sec, 1.0 + (1.0 - back_from - th) * 4.0), sec)
    tuft = _part_norm(p, MANE_PARTS[-1])
    return np.minimum(sec, tuft)


def ruff_norm(p: np.ndarray) -> np.ndarray:
    return np.min(np.stack([_part_norm(p, q) for q in RUFF_PARTS]), axis=0)


def body_extras() -> list[bpy.types.Object]:
    """The two ears' shells, and (round 7) the sculpted locks of the mane and the plume, voxel-united into the body so
    the coat grows on them."""
    return [E.slab(s) for s in (1, -1)] + [LK.lock_mesh(n) for n in LK.SETS]


# the plume's own centre line, through its lobes (the sculpted clumps root round it)
PLUME_AXIS = [(0.0, 0.56, 0.67), (0.0, 0.62, 0.665), (0.0, 0.71, 0.635), (0.0, 0.81, 0.625), (0.0, 0.92, 0.665), (0.0, 1.0, 0.725),
              (0.0, 1.06, 0.8), (0.0, 1.1, 0.87), (0.0, 1.14, 0.955)]

M.configure(all_parts())
M.configure_tail(TAIL_PTS, STAR_C)
# round 8: a fluffy cuff round each lower leg above the paw (starhowl_locks 'cuff'): the ring's centre on the leg
CUFFS = [(LEGS[lg][0], LEGS[lg][1] + (0.017 if lg[0] == 'F' else 0.084), 0.185 if lg[0] == 'F' else 0.17) for lg in LEGS]
LK.configure(COLLAR_KEYS, PLUME_AXIS, CUFFS)
EAR_ROOT = {s: E.root(s) for s in (1, -1)}


# ----------------------------------------------------------------------------- the tail's own coordinates
def tail_coords(p: np.ndarray):
    """(t along the spine 0..1 (may run past), height above the spine in the tail's sagittal plane, distance from the
    spine)."""
    pts = np.array(TAIL_PTS)
    t, _L = U.polyline_param(p, pts)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    acc = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()
    tc = np.clip(t, 0, 1)
    c = np.stack([np.interp(tc, acc, pts[:, i]) for i in range(3)], axis=1)
    d = p - c
    # the spine's tangent there
    tg = np.stack([np.interp(np.clip(tc + 0.01, 0, 1), acc, pts[:, i]) - np.interp(np.clip(tc - 0.01, 0, 1), acc, pts[:, i]) for i in range(3)], axis=1)
    tg = norm(tg)
    up = norm(np.tile(v3((0, 0, 1)), (len(p), 1)) - tg * tg[:, 2:3])
    return t, (d * up).sum(1), np.linalg.norm(d, axis=1)


# ----------------------------------------------------------------------------- carving (the high source only)
SMILE_SIDE = [(-0.702, 0.959), (-0.678, 0.953), (-0.645, 0.949), (-0.61, 0.949), (-0.586, 0.955), (-0.571, 0.965), (-0.563, 0.976), (-0.561, 0.984)]   # (y, z)
SMILE_FRONT = [(-0.017, 0.928), (-0.009, 0.93), (0.0, 0.932), (0.009, 0.93), (0.017, 0.928)]                       # (x, z)


def mouth_mask(co: np.ndarray) -> np.ndarray:
    """Round 2 (review: a flat mouth): the corners of the mouth turn up into a small confident smile. The lip line
    runs back along each side of the muzzle (the seam over the lower jaw) and curls up below the cheek; a short
    philtrum drops from the nose to the front lip."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    ax = np.abs(x)
    # round 5 (review: a small boxy mouth with tooth marks): one thin lip line along each side, curling up at the
    # corner; no front lip line and only a hair of a philtrum (3-faces neutral: a closed smile)
    side = S.polyline_dist(y, z, SMILE_SIDE)
    g = np.exp(-(side / 0.0021) ** 2) * (ax > 0.006) * (ax < 0.06) * (y < -0.558) * smooth(-0.7, -0.676, y)
    phil = 0.5 * np.exp(-(ax / 0.0009) ** 2) * (z < NOSE_C.z - 0.012) * (z > 0.963) * (y < NOSE_C.y + 0.02)
    # round 9 (review: the jaws read shut in the strike): the lower lip is dark for 5 mm under the line, where the
    # skin stretches when the jaw opens
    below = np.interp(y, np.array([q[0] for q in SMILE_SIDE]), np.array([q[1] for q in SMILE_SIDE])) - z
    g = np.maximum(g, 0.75 * smooth(0.0065, 0.003, below) * smooth(-0.002, 0.0, below) * (ax < 0.05) * smooth(-0.555, -0.58, y)
                   * smooth(-0.7, -0.68, y))
    return np.clip(np.maximum(g, phil), 0, 1)


def eye_local(co: np.ndarray, s: int):
    c, xax, yax, look = eye_frame(s)
    q = co - v3(c)
    return q @ v3(xax), q @ v3(yax), q @ v3(look)


def pinched_r(xe: np.ndarray, ye: np.ndarray) -> np.ndarray:
    """The normalised radius of skin points in the almond lens's outline (1 = its rim, pinched toward the corners)."""
    ax, ay = EYE_R * EYE_W, EYE_R * EYE_H
    xn = np.clip(xe / ax, -1, 1)
    hy = ay * (1.0 - EYE_PINCH * xn * xn) * np.where(ye < 0, EYE_LOW, 1.0)
    return np.sqrt((xe / ax) ** 2 + (ye / hy) ** 2)


def eye_world(euv: np.ndarray) -> np.ndarray:
    """A lens's unit coordinates → its real position across and up, in units of EYE_R (round shapes are painted in
    these; the lids follow the unit coordinates)."""
    xu, yu = euv[:, 0], euv[:, 1]
    pinch = 1.0 - EYE_PINCH * np.minimum(1.0, xu * xu)
    return np.stack([xu * EYE_W, yu * EYE_H * pinch * np.where(yu < 0, EYE_LOW, 1.0), np.zeros(len(euv))], axis=1)


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens: the soft closed lid (a bulge) and its lash line, shown only while a blink sinks the lens."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        xe, ye, ze = eye_local(co, s)
        ax, ay = EYE_R * EYE_W, EYE_R * EYE_H
        r2 = pinched_r(xe, ye) ** 2        # round 7: the lens's own outline (the old ellipse left a dark lid rim round it)
        front = ze > -0.025
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * ay
        th = 0.0016 + 0.0013 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 0.9) & (r2 < 0.8)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(0.9, 0.75, np.abs(xn)))
    return bulge, lash


def liner(co: np.ndarray) -> np.ndarray:
    """The dark eye-liner round the open eye on the skin: thin below, bold over the top, with a short wing flicking out
    and up at the outer corner (3-faces.png, 4-details.png panel 2)."""
    out = np.zeros(len(co))
    for s in (1, -1):
        xe, ye, ze = eye_local(co, s)
        ax, ay = EYE_R * EYE_W, EYE_R * EYE_H
        r = pinched_r(xe, ye)
        front = ze > -0.03
        top = smooth(-0.35, 0.35, ye / ay)
        # round 5: a bold liner along the almond's upper rim (the lash line continues onto the skin), thin below
        w = 0.06 + 0.13 * top + 0.05 * smooth(0.3, 0.95, xe * s / ax)
        # round 7: the lower lid's line shows too (3-faces: a fine dark line under the eye)
        ring = np.exp(-((r - 1.04) / w) ** 2) * front * (0.5 + 0.5 * top) * (0.6 + 0.4 * smooth(-0.6, 0.6, xe * s / ax))
        # the wing: a tapered stroke beyond the outer corner, flicked up (4-details panel 2); round 6: longer and bolder
        a = v3((0.93 * s, 0.16, 0.0))
        b = v3((1.55 * s, 0.66, 0.0))
        pq = np.stack([xe / ax, ye / ay, np.zeros(len(co))], axis=1)
        ab = b - a
        t = np.clip(((pq - a) @ ab) / (ab @ ab), 0, 1)
        d = np.linalg.norm(pq - (a + t[:, None] * ab), axis=1)
        wing = np.exp(-(d / (0.14 * (1 - 0.7 * t))) ** 2) * front
        out = np.maximum(out, np.maximum(ring, wing))
    return np.clip(out, 0, 1)


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    groove = mouth_mask(co)
    nos = np.zeros_like(x)
    for s in (1, -1):
        dd = np.sqrt(((x - 0.007 * s) / 1.5) ** 2 + (z - (NOSE_C.z - 0.003)) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.0034) ** 2))
    nos *= smooth(NOSE_C.y + 0.01, NOSE_C.y + 0.002, y)
    # the toes stand apart: a groove between neighbours; the big pad and the toe beans are set in
    # round 5 (review: mittens with faint grooves): deeper, wider grooves that reach the paw's top
    gap = np.zeros(len(co))
    for leg in LEGS:
        ts = toe_centres(leg)
        for a, b in zip(ts[:-1], ts[1:]):
            m = 0.5 * (a + b)
            d = np.sqrt(((x - m.x) / 0.0042) ** 2 + ((y - m.y) / 0.036) ** 2 + ((z - 0.034) / 0.05) ** 2)
            gap = np.maximum(gap, np.exp(-d ** 2))
    bulge, lash = closed_lid(co)
    sock = np.zeros(len(co))
    for s_ in (1, -1):
        xe, ye, ze = eye_local(co, s_)
        r_ = pinched_r(xe, ye)
        sock = np.maximum(sock, smooth(0.88, 1.04, r_) * smooth(1.5, 1.1, r_) * (ze > -0.03) * (ze < 0.05))
    # round 5: a shallow socket (the deep ring round the lens made it a ball in a cup)
    disp = -0.002 * sock - 0.0012 * groove - 0.0035 * nos - 0.011 * gap - 0.0006 * lash        # round 8: no lid bulge (goggles)
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)
    S.add_attr(ob, 'liner', liner(co))
    # the stars are placed now, on the carved high body, so the fur cards can keep clear of them (round 2: cards rooted
    # on a star took its colour: gold and cream smears behind the mane)
    _MARKS['v'] = make_marks(ob)


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    uv = []
    for v in bm.verts:
        uv.append((v.co.x, v.co.y, v.co.z))
        # round 5: the almond: the lens's height shrinks toward the corners (the paint keeps the unpinched coordinates)
        # round 7: the lower half is flatter than the upper (EYE_LOW)
        pinch = 1.0 - EYE_PINCH * min(1.0, v.co.x * v.co.x)
        low = EYE_LOW if v.co.y < 0 else 1.0
        v.co = Vector((v.co.x * EYE_R * EYE_W, v.co.y * EYE_R * EYE_H * pinch * low, v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    euv = np.array(uv)
    S.add_attr(ob, 'eyeuv', euv)
    S.add_attr(ob, 'eyexy', eye_world(euv))
    S.add_attr(ob, 'glow', eye_glow(euv, s))
    S.add_attr(ob, 'eye_side', np.full(len(euv), float(s)))
    return ob


def eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """Round 7 (1-hero, 3-faces neutral, 4-details panel 2): a big saturated sky-blue iris that fills the opening's
    height (deep blue at its rim, a pale cyan glow in its lower half, a dark limbal ring), a large dark pupil, two crisp
    catchlights, a little white at the two sides only, a heavy dark lash band along the upper rim that thickens toward
    the outer corner, a soft lid shadow under it and a fine lower lid line. (The pale outer iris of rounds 1–6 read as
    white all round a small iris: a stare.)"""
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']          # the lens's unit coordinates: the rim at radius 1
    w = nb.attribute('eyexy').outputs['Vector']          # real proportions, in units of EYE_R (round shapes)
    side = nb.attribute('eye_side').outputs['Fac']
    xu, yu, _zu = nb.sep(e)
    xw, yw, _zw = nb.sep(w)
    ru = nb.vmath('LENGTH', nb.comb(xu, yu, 0.0))
    top = nb.smooth(yu, -0.2, 0.25)
    outer_k = nb.smooth(nb.math('MULTIPLY', xu, side), 0.0, 0.95)
    lash_in = nb.math('SUBTRACT', 0.75, nb.math('MULTIPLY', outer_k, 0.08))        # round 8: the upper lid's dark band on the lens itself
    lash = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ru, lash_in), -0.03, 0.03), top)
    lower = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(ru, 0.92, 0.96), nb.math('SUBTRACT', 1.0, top)), 0.75)
    if rough_pass:
        lid_ = nb.math('MAXIMUM', lash, lower)
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, nb.math('ADD', 0.04, nb.math('MULTIPLY', lid_, 0.7)), nb.math('SUBTRACT', 1.0, lid_)), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    xi = nb.math('SUBTRACT', xw, nb.math('MULTIPLY', side, IRIS_OUT))
    yi = nb.math('SUBTRACT', yw, IRIS_DY)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(xi, yi, 0.0)), IRIS_R)
    # round 8 (CONTENT: glowing pale eyes, #E8F1FF): a pale ice-blue iris with a light blue ring and a dark rim
    stops = [(0.0, '#070B1E'), (0.28, '#070B1E'), (0.33, '#DCE9FF'), (0.48, '#E8F1FF'), (0.64, '#A9CEFA'), (0.84, '#6FA6EC'),
             (0.97, '#3A6EC2'), (1.0, '#15255A'), (1.03, '#F4F6FC'), (1.6, '#E4E9F4')]
    c = nb.ramp(nb.math('DIVIDE', ri, 1.6), [(p / 1.6, C.lin(h)) for p, h in stops])
    # the pale cyan glow in the iris's lower half (the pictures' "glowing" eyes)
    glow_k = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(nb.math('DIVIDE', yi, IRIS_R), 0.15, -0.55), nb.smooth(ri, 0.27, 0.4)),
                     nb.smooth(ri, 0.98, 0.84))
    c = nb.mix(nb.math('MULTIPLY', glow_k, 0.12), c, nb.rgb(C.lin('#8FDCFF')))
    # the fine streaks of the iris (4-details panel 2)
    ang = nb.math('ARCTAN2', yi, xi)
    streak = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 26.0)), 0.5),
                     nb.math('MULTIPLY', nb.smooth(ri, 0.5, 0.62), nb.smooth(ri, 0.95, 0.85)))
    c = nb.mix(nb.math('MULTIPLY', nb.math('ABSOLUTE', streak), 0.22), c, nb.rgb(C.lin('#B8DCFF')))
    # the upper lid's shadow across the top of the eye
    sh = nb.math('MULTIPLY', nb.smooth(yu, 0.15, 0.8), 0.5)
    c = nb.mix(sh, c, nb.rgb(C.lin('#3A4280')), blend='MULTIPLY')
    # the catchlights (both eyes on the same side: one light)
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', xi, 0.2), nb.math('SUBTRACT', yi, 0.2), 0.0)), 0.185, 0.155)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', xi, 0.2), nb.math('ADD', yi, 0.25), 0.0)), 0.07, 0.05)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    c = nb.mix(lash, c, nb.rgb(C.lin(LINER_HEX)))
    c = nb.mix(nb.math('MULTIPLY', lower, 0.8), c, nb.rgb(C.lin(LINER_HEX)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def apply_transform(ob: bpy.types.Object) -> None:
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)


# ----------------------------------------------------------------------------- zones
NECK_SEG = (v3((0.0, -0.41, 0.97)), v3((0.0, -0.25, 0.7)))


def neck_dist(p: np.ndarray) -> np.ndarray:
    a, b = NECK_SEG
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def leg_masks(p: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    out = {}
    for leg, (lx, ly) in LEGS.items():
        top = 0.42 if leg[0] == 'F' else 0.36
        pc = paw_centre(leg)
        paw = (np.hypot(x - lx, (y - pc.y) * 0.75) < 0.1) & (z < 0.13)
        if leg[0] == 'F':
            r = np.hypot(x - lx, (y - ly) * 0.9)
            out[leg] = ((r < 0.11) & (z < top + 0.03 * np.sign(x * lx))) | paw
        else:
            # the hind leg slants back to the hock: follow it
            yc = ly + np.interp(z, [0.0, 0.06, 0.2, 0.39], [-0.01, 0.0, 0.1, -0.11])
            r = np.hypot(x - lx, (y - yc) * 0.9)
            out[leg] = ((r < 0.11) & (z < top)) | paw
    return out


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    ear, ear_u, ear_inner, ear_rim, ear_l = E.zone(p)
    head = ((in_ellipsoid(p, (0.0, -0.475, 1.03), (0.2, 0.26, 0.17)) < 1.0) & (z > 0.89)) | ear
    muzzle = in_ellipsoid(p, *MUZZLE) < 1.0
    nose = np.linalg.norm(p - v3(NOSE_C), axis=1) < 0.034
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = head & (y < -0.505) & (z > 0.91) & (z < 1.13) & (ax < 0.12) & ~ear
    crown = head & (z > 1.11) & ~ear
    cheek = head & (ax > 0.08) & (z < 1.03) & (y < -0.385) & ~ear & ~muzzle
    chin = head & (z < 0.955) & (y < -0.505)
    ear_root = E.root_dist(p) < 0.03
    legs = leg_masks(p)
    leg = np.zeros(len(p), bool)
    for m in legs.values():
        leg |= m
    leg &= ~head
    paw = leg & (z < 0.085)
    toes = np.zeros(len(p), bool)
    for lg in LEGS:
        pc = paw_centre(lg)
        toes |= legs[lg] & (y < pc.y - 0.02) & (z < 0.07)
    sole = z < 0.014
    tt, th, tr = tail_coords(p)
    # round 7: the sculpted locks (starhowl_locks) belong to the mane and to the tail wherever they reach
    lm_in, lm_u, lm_t = LK.lookup(p, 'mane')
    lt_in, _lt_u, lt_t = LK.lookup(p, 'tail')
    lb_in, lb_u, _lb_t = LK.lookup(p, 'bib')            # round 8: the throat ruff's sculpted clumps
    lm_raw = lm_in & ~ear & (eye_d > 0.045)
    hidden = lm_raw & (face | muzzle | (eye_d <= 0.07) | (head & (y < -0.47) & (z < 1.11)))
    if hidden.any():
        # round 9b: a lock that hangs beside the face is still mane (it was painted the head's indigo); only the
        # head's own skin under a lock keeps the head's colours
        on = np.flatnonzero(hidden)
        hidden[on[M.sdf(p[on]) > 0.006]] = False
    lm_in = lm_raw & ~hidden
    lc_in, lc_u, lc_t = LK.lookup(p, 'crown')           # round 8d: the crown's sculpted tuft
    lc_in = lc_in & ~ear & ~face & ~muzzle & (eye_d > 0.07) & ~lm_in
    if lc_in.any():
        # only the locks themselves (outside the analytic body), not the skull's skin beside their roots
        on = np.flatnonzero(lc_in)
        lc_in[on[M.sdf(p[on]) < 0.004]] = False
    lm_u = np.where(lc_in, lc_u, lm_u)
    lm_t = np.where(lc_in[:, None], lc_t, lm_t)
    lm_in = lm_in | lc_in
    lm_v = np.where(lc_in, 0.0, LK.lookup_v(p, 'mane'))
    lt_in = lt_in & ~head & (y > 0.45)
    leg = leg & ~lm_in & ~lt_in
    paw = paw & leg
    toes = toes & leg
    tail = ((~head) & (~leg) & (tt > 0.04) & (y > 0.48) & ((z > 0.45) | ((y > 0.56) & (z > 0.28)))) | lt_in
    plume = tail & (tt > 0.15)
    torso = ~head & ~leg & ~tail
    # the mane's skin: round the neck, from under the skull to the withers (the locks cover it)
    nd = neck_dist(p)
    mn = mane_norm(p)
    rn = ruff_norm(p)
    # round 5: the bib is a zone inside the collar's front (the same volume, painted lavender); the mane is the rest
    ruff = ((~ear & (rn < 1.1) & (y < -0.42) & ~chin & ~muzzle & ~face & (z < 0.95) & ~lm_in)
            | (lb_in & ~lm_in & ~face & ~muzzle & ~chin & ~ear))
    mane = (~ear & (mn < 1.12) & ~ruff & ~face & ~muzzle & (eye_d > 0.07) & ~(head & (y < -0.47) & (z < 1.11))) | lm_in
    # the lighter underside: the belly line falls from the chest's front to the tucked loin
    # round 6: higher (the belly and the inner legs lacked the periwinkle)
    zb = np.interp(y, [-0.5, -0.36, -0.15, 0.1, 0.3, 0.45], [0.62, 0.53, 0.525, 0.53, 0.56, 0.58])
    belly = torso & (z < zb) & (z > 0.3)
    chest = torso & (y < -0.38) & (z < 0.72) & (z > 0.3)
    back = torso & (z > 0.68)
    return {'ear': ear, 'ear_u': ear_u, 'ear_v': ear_l['v'], 'ear_inner': ear_inner, 'ear_rim': ear_rim, 'ear_up': ear_l['up'],
            'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face, 'crown': crown, 'cheek': cheek,
            'chin': chin, 'ear_root': ear_root, 'leg': leg, 'paw': paw, 'toes': toes, 'sole': sole, 'tail': tail,
            'plume': plume, 'tail_t': tt, 'tail_h': th, 'tail_r': tr, 'torso': torso, 'mane': mane, 'ruff': ruff, 'mane_n': mn,
            'neck_d': nd, 'belly': belly, 'bib_u': np.where(lb_in, lb_u, 0.0), 'lock_in': lm_in, 'lock_u': lm_u, 'lock_t': lm_t, 'tlock_in': lt_in, 'tlock_t': lt_t, 'crown_in': lc_in, 'lock_v': lm_v,
            'chest': chest, 'back': back, 'legs': legs}


# round 7: the sculpted locks of the mane and the plume would unwrap into thousands of slivers; they are unwrapped at
# smoothed positions instead (RECIPE.md: far fewer, larger islands). The face, the ears and the paws keep their own.
UV_SMOOTH = 90


def uv_smooth_mask(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    m = np.where(z['mane'] | z['ruff'] | z['tail'], 1.0, 0.25)
    return np.where((z['head'] & ~z['mane']) | z['ear'] | z['paw'], 0.0, m)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(z['face'] * 1.0 + z['muzzle'] * 1.0 + (z['eye_d'] < 0.07) * 1.0 + z['toes'] * 0.75 + z['paw'] * 0.25 + z['mane'] * 0.3 + z['chin'] * 1.0 + z['crown_in'] * 1.0
                   + z['ear'] * 0.5, 0, 1)


# ----------------------------------------------------------------------------- colours by region (at the roots)
def tone_masks(p: np.ndarray, z: dict) -> dict[str, np.ndarray]:
    """0..1 weights of the coat's tones at points: `light` (#4C5199: belly, inner and lower legs, chest ruff, eye
    halo), `pale` (lavender: muzzle, cheeks, chin, under the eyes), `inner_ear`, `aurora` (the tail's teal → rose) and
    `rose` (how far the aurora has turned rose). The rest is indigo."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    # --- the face: a husky-like mask. Pale on the muzzle's sides and underside, the cheeks below the eyes and the chin;
    # a dark indigo stripe down the bridge to the nose and the forehead above the brows.
    pale = np.zeros(len(p))
    pale = np.maximum(pale, ell_soft(p, (0.0, -0.61, 0.945), (0.06, 0.13, 0.045), 0.25))
    for s in (1, -1):
        pale = np.maximum(pale, ell_soft(p, (0.072 * s, -0.495, 0.98), (0.07, 0.08, 0.05), 0.3))
        pale = np.maximum(pale, ell_soft(p, (0.038 * s, -0.61, 0.97), (0.032, 0.11, 0.032), 0.3))
    bridge = smooth(0.022, 0.012, ax) * smooth(0.982, 0.997, zz) * (y < -0.53) * smooth(-0.70, -0.675, y)
    pale = pale * (1 - bridge)
    pale = np.where(z['head'] & (zz > 1.03), 0.0, pale)
    pale *= ~z['ear']
    # --- the lighter fur
    light = np.zeros(len(p))
    # the halo round each eye and the brow area, soft
    for s in (1, -1):
        light = np.maximum(light, ell_soft(p, tuple(EYE_C[s] + Vector((0.004 * s, 0.01, -0.004))), (0.052, 0.055, 0.046), 0.4))
        pale = np.maximum(pale, 0.5 * ell_soft(p, tuple(EYE_C[s] + Vector((0.004 * s, 0.012, -0.016))), (0.05, 0.055, 0.04), 0.45)
                          * (np.abs(x) > 0.022))
        # round 7: the lavender upper lid between the eye and the dark brow stroke (1-hero, 3-faces)
        light = np.maximum(light, 0.95 * ell_soft(p, tuple(EYE_C[s] + Vector((0.003 * s, 0.006, 0.03))), (0.044, 0.05, 0.03), 0.5)
                           * (np.abs(x) > 0.02))
    # the throat ruff under the chin and the chest
    light = np.maximum(light, ell_soft(p, (0.0, -0.48, 0.84), (0.13, 0.12, 0.1), 0.3) * ~z['head'])
    light = np.maximum(light, ell_soft(p, (0.0, -0.47, 0.66), (0.11, 0.1, 0.2), 0.35) * ~z['head'])
    # the chin and throat ruff: pale under the chin, blending into the lighter fur down the throat
    pale = np.maximum(pale, ell_soft(p, (0.0, -0.505, 0.905), (0.085, 0.09, 0.05), 0.45) * 0.85)
    light = np.maximum(light, (z['chin'] | (z['head'] & (zz < 0.93) & (y < -0.4))) * 1.0)
    # the underside (round 6: higher, a clear periwinkle belly; 2-turnaround side)
    zb = np.interp(y, [-0.5, -0.36, -0.15, 0.1, 0.3, 0.45], [0.64, 0.55, 0.54, 0.55, 0.58, 0.6])
    light = np.maximum(light, z['torso'] * smooth(zb + 0.03, zb - 0.03, zz))
    # the legs: the inside all the way up, every leg lighter from the wrist / hock down (the paws darken again)
    for lg, (lx, _ly) in LEGS.items():
        m = z['legs'][lg]
        inner = smooth(0.0, -0.03, (x - lx) * np.sign(lx)) * smooth(0.62, 0.52, zz)
        # round 8 (review: smooth indigo tubes): the lower legs are clearly periwinkle from below the elbow / the hock
        lower = (smooth(0.42, 0.3, zz) if lg[0] == 'F' else smooth(0.36, 0.26, zz)) * smooth(0.075, 0.105, zz)
        light = np.maximum(light, m * np.maximum(inner, lower))
    leg_any = np.zeros(len(p), bool)
    for m in z['legs'].values():
        leg_any |= m
    # round 2: the lower legs grade lighter toward the paws (periwinkle, then a little paler)
    # round 5 (review: a pale scratchy fringe on the leg outlines): much less of the pale there (the cards take it)
    pale = np.maximum(pale, leg_any * smooth(0.24, 0.1, zz) * smooth(0.075, 0.105, zz) * 0.26)
    light = np.clip(light - pale, 0, 1)
    # --- the ears' hollow
    # round 8: the hollow's pink starts above the ear's root (it bled onto the skull behind the eye)
    inner_ear = z['ear_inner'] * smooth(0.1, 0.2, z['ear_u']) * smooth(0.97, 0.85, z['ear_u'])
    ear_fluff = z['ear_inner'] * smooth(0.35, 0.1, z['ear_u']) * (smooth(0.3, 0.05, z['ear_v']) + 0.6 * smooth(0.7, 0.95, z['ear_v']))
    # --- the tail's aurora: the plume's underside and its far end
    tt, th = z['tail_t'], z['tail_h']
    # round 4: indigo at the base (and along the top until the middle), teal through the middle, rose at the end and
    # underneath (2-turnaround side and back, 4-details panel 4)
    # round 4b: the indigo ridge runs along the top to near the tip; the hanging plume below it is the aurora
    aur = z['tail'] * smooth(0.05, 0.5, tt) * np.maximum(smooth(0.03, -0.07, th), smooth(0.5, 0.85, tt))      # round 9: a long blend
    # round 7 (2-turnaround back: a pink centre and underside, teal sides, an indigo rim): rose at the very end and
    # along the middle of the underside only; the plume's flanks stay teal
    rose = np.clip(smooth(0.5, 0.94, tt) + smooth(-0.1, -0.24, th) * smooth(0.3, 0.55, tt) * smooth(0.085, 0.035, ax), 0, 1)
    # round 4: the mane mass: teal on its upper part, rose over the lower third (2-turnaround front and side), deeper aqua
    # in toward the neck; the throat ruff lavender (the light fur, paler toward its tips)
    mane = np.where(z['lock_in'], 1.0, smooth(1.25, 1.0, z['mane_n'])) * z['mane'] * ~z['ruff']
    # round 6 (review: rose was a thin dusty band along the bottom): a clear rose over the collar's lower 40% (the
    # cards take their colour from this skin), blending from z 0.86 down; full rose below 0.66
    # round 7: the sculpted locks' tips turn rose too (below the cheeks; 1-hero: pink curled tips flaring at the sides)
    lock_tip = z['lock_in'] * smooth(0.76, 0.87, z['lock_u']) * ~z['crown_in']
    # (the first sculpted preview was pink over its lower two thirds: the z blend sits lower now, and the rose comes
    # mostly from the locks' own tips)
    # round 8: each lock turns rose over its own lower third or more (below the cheeks), and every lock is rose low
    # down; the collar under the locks is never rose (it showed as a mauve patch on the Lite copy's chest)
    mane_rose = z['lock_in'] * smooth(0.46, 0.72, z['lock_u']) * ~z['crown_in']        # round 9: each ribbon's own lower third
    mane_deep = smooth(0.14, 0.06, z['neck_d']) * 0.5
    # round 7 (1-hero, 3-faces, 2-turnaround back): the mane is rooted in indigo: a ring of indigo fur right behind the
    # cheeks and the ears, and a dark stripe down the crest to the withers, before the teal begins
    d_head = np.linalg.norm(p - v3(HEAD_C), axis=1)
    mane_ind = np.maximum(smooth(0.27, 0.19, d_head), 0.9 * smooth(0.085, 0.035, ax) * (y > -0.36) * smooth(0.6, 0.7, zz))
    mane_ind = np.zeros(len(p))          # round 9 (review: the face sat in an indigo hood): the teal starts at the cheeks and the ears
    # a ribbon of strands: darker toward its edges, fine lines along it
    v_ = z['lock_v']
    lock_shade = np.where(z['lock_in'] & ~z['crown_in'], (1.0 - 0.28 * smooth(0.45, 1.0, np.abs(v_))) * (1.0 + 0.1 * np.sin(v_ * 9.0)), 1.0)
    light = np.where(z['ruff'], 1.0, light)
    # round 9: the ruff's paleness fades out toward its lower edge (pale strokes over the chest read as icicles)
    pale = np.where(z['ruff'], np.maximum(pale, (0.3 + 0.45 * z['bib_u']) * smooth(0.63, 0.75, zz)), pale)
    # round 9 (review: closed lids are pale domes): the skin under each lens is the surrounding indigo
    sock = smooth(0.034, 0.026, z['eye_d'])
    light, pale = light * (1.0 - sock), pale * (1.0 - sock)
    return {'pale': np.clip(pale, 0, 1), 'light': np.clip(light, 0, 1), 'inner_ear': np.clip(inner_ear, 0, 1),
            'ear_fluff': np.clip(ear_fluff, 0, 1), 'aurora': np.clip(aur, 0, 1), 'rose': np.clip(rose, 0, 1),
            'mane': np.clip(mane, 0, 1), 'mane_rose': np.clip(mane_rose, 0, 1), 'mane_deep': np.clip(mane_deep, 0, 1),
            'mane_ind': np.clip(mane_ind, 0, 1), 'mane_base': (z['mane'] & ~z['lock_in'] & ~z['ruff']) * 1.0, 'lock_tip': np.clip(lock_tip, 0, 1), 'lock_shade': lock_shade}


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


MANE_GAIN = 1.1


def tone_rgb(t: dict, col: dict) -> np.ndarray:
    k = len(t['pale'])
    rgb = np.tile(lin(col['indigo']), (k, 1))
    rgb = rgb * (1 - t['light'][:, None]) + lin(col['light'])[None] * t['light'][:, None]
    rgb = rgb * (1 - t['pale'][:, None]) + lin(col['pale'])[None] * t['pale'][:, None]
    # (round 9: through the pale mint, like the mane: a straight teal-to-rose mix is a muddy mauve half way)
    ra_, rb_ = np.clip(t['rose'][:, None] * 2.0, 0, 1), np.clip(t['rose'][:, None] * 2.0 - 1.0, 0, 1)
    aur = lin(col['teal'])[None] * (1 - 0.45 * ra_) + lin(col['mane_mid'])[None] * (0.45 * ra_)
    aur = aur * (1 - rb_) + lin(col['rose'])[None] * rb_
    # the aurora skin is a touch deeper than the locks over it (they glow; it doesn't)
    rgb = rgb * (1 - t['aurora'][:, None]) + aur * t['aurora'][:, None]
    teal = lin(col['teal'])[None] * (1 - t['mane_deep'][:, None]) + lin(col['teal_deep'])[None] * t['mane_deep'][:, None]
    # round 8: teal turns to rose through a pale mint, as in 1-hero (a straight teal-to-rose mix passes through a
    # muddy grey-mauve: the review's dusty tips)
    r_ = t['mane_rose'][:, None]
    a_, b_ = np.clip(r_ * 2.0, 0, 1), np.clip(r_ * 2.0 - 1.0, 0, 1)
    mane_col = teal * (1 - 0.45 * a_) + lin(col['mane_mid'])[None] * (0.45 * a_)
    mane_col = mane_col * (1 - b_) + lin(col['rose'])[None] * b_
    # round 7b: the aurora is luminous (1-hero: mint and pale rose); the first sculpted build baked it dark green
    # in the creases between the locks, so its paint is lifted (MANE_GAIN) before the bake's shading
    mane_col = np.clip(mane_col * MANE_GAIN, 0, 1) * t['lock_shade'][:, None]
    mane_col = mane_col * (1 - t['mane_ind'][:, None]) + lin(col['mane_root'])[None] * t['mane_ind'][:, None]
    # the collar under the locks: a deep teal shadow (it shows only between them)
    base_ = 0.6 * t['mane_base'][:, None] * (1 - t['mane_ind'][:, None])
    mane_col = mane_col * (1 - base_) + lin(col['teal'])[None] * 0.75 * base_
    rgb = rgb * (1 - t['mane'][:, None]) + mane_col * t['mane'][:, None]
    rgb = rgb * (1 - t['inner_ear'][:, None]) + lin(col['inner_ear'])[None] * t['inner_ear'][:, None]
    rgb = rgb * (1 - t['ear_fluff'][:, None]) + lin(col['ear_fluff'])[None] * t['ear_fluff'][:, None]
    return rgb


# ----------------------------------------------------------------------------- how the fur lies
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    k = len(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    # head: combed back from the nose, turning down over the cheeks
    g = norm(p - v3((NOSE_C.x, NOSE_C.y - 0.03, NOSE_C.z)))
    wd = smooth(1.01, 0.93, zz)[:, None]
    g_head = norm(g * (1 - wd) + norm(v3((0, 0.6, -1)) + np.stack([x * 3, np.zeros(k), np.zeros(k)], axis=1)) * wd)
    # between the eyes: comb up and a little out (no starburst on the brow)
    face_up = norm(np.stack([x * 3.0, np.full(k, 0.3), np.ones(k)], axis=1))
    wf = (smooth(-0.495, -0.545, y) * smooth(1.06, 1.09, zz) * smooth(0.08, 0.03, np.abs(x)))[:, None]
    g_head = norm(g_head * (1 - wf) + face_up * wf)
    # the ears' backs: up toward the tip
    g_head = np.where(z['ear'][:, None], z['ear_up'], g_head)
    side = np.clip(np.abs(n[:, 0]) * 1.3, 0, 1)[:, None]
    g_torso = norm(v3((0.0, 1.0, -0.15)) * (1 - side) + v3((0.0, 0.5, -1.0)) * side)
    g = np.where(z['torso'][:, None], g_torso, g_head)
    g = np.where(z['belly'][:, None], np.tile(v3((0.0, 0.5, -0.8)), (k, 1)), g)
    g = np.where(z['chest'][:, None], np.tile(v3((0.0, -0.1, -1.0)), (k, 1)), g)
    g = np.where(z['leg'][:, None], np.tile(v3((0.0, 0.15, -1.0)), (k, 1)), g)
    g = np.where((z['leg'] & (zz < 0.22))[:, None], np.tile(v3((0.0, 0.9, -0.55)), (k, 1)), g)
    g = np.where((z['paw'] & (zz > 0.05))[:, None], np.tile(v3((0.0, -0.8, -0.6)), (k, 1)), g)
    # the tail: along the spine toward the tip, sweeping out and down off the plume like feathers
    pts = np.array(TAIL_PTS)
    tt = np.clip(z['tail_t'], 0, 1)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    acc = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()
    tg = norm(np.stack([np.interp(np.clip(tt + 0.02, 0, 1), acc, pts[:, i]) - np.interp(np.clip(tt - 0.02, 0, 1), acc, pts[:, i]) for i in range(3)], axis=1))
    # round 5 (review: from behind the plume is a smooth pink paddle): toward the tip the fur fans out from the spine,
    # so the back view sees the clumps broadside instead of end-on
    fan_k = (0.25 + 1.0 * smooth(0.45, 0.9, tt))[:, None]
    g_tail = norm(tg * (1.0 - 0.8 * smooth(0.6, 0.95, tt))[:, None] + n * fan_k + v3((0, 0, -0.25)) * smooth(0.0, -0.08, z['tail_h'])[:, None])
    g = np.where(z['tail'][:, None], g_tail, g)
    g = np.where((z['head'] & ~z['chest'])[:, None], g_head, g)
    # round 4: the mane falls back and out from the neck in an S-sweep (the locks wave sideways as they fall); the
    # throat ruff falls down the chest; the plume's fur combs toward the tip and out from the spine
    ax_, up_, side_ = M.neck_frame()
    rel = p - M.NECK_A
    th_ = np.arctan2(rel @ side_, rel @ up_)
    fall = (np.tile(v3((0.0, 0.95, -0.3)), (k, 1)) * np.maximum(np.cos(th_), 0)[:, None] ** 1.5
            + np.stack([np.sign(np.sin(th_)) * 0.35, np.full(k, 0.8), np.full(k, -0.65)], axis=1) * np.abs(np.sin(th_))[:, None]
            + np.tile(v3((0.0, -0.1, -1.0)), (k, 1)) * np.maximum(-np.cos(th_), 0)[:, None] ** 1.5)
    across = norm(np.cross(norm(fall), n))
    wave = np.sin(zz * 24.0 + th_ * 2.0)[:, None] * 0.55
    g_mane = norm(norm(fall) + across * wave)
    g = np.where(z['mane'][:, None], g_mane, g)
    # round 7: on a sculpted lock the fur runs along the lock (the mane's and the plume's)
    g = np.where(z['lock_in'][:, None], z['lock_t'], g)
    g = np.where((z['tlock_in'] & (np.linalg.norm(z['tlock_t'], axis=1) > 0.5))[:, None], z['tlock_t'], g)
    g = np.where(z['ruff'][:, None], np.tile(v3((0.0, -0.15, -1.0)), (k, 1)), g)
    # round 2: the cheek fur sweeps back and out into points
    g_cheek = norm(np.stack([np.sign(x) * 0.55, np.ones(k), np.full(k, -0.3)], axis=1))
    g = np.where((z['cheek'] & ~z['ear'])[:, None], g_cheek, g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


def head_lock_params(p, n):
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.052)
    W = np.full(k, 0.0105)
    lift = np.full(k, _rad(3.0))
    L = np.where(z['face'], 0.034, L)
    W = np.where(z['face'], 0.0075, W)
    L = np.where(z['crown'], 0.06, L)
    L = np.where(z['cheek'], 0.07, L)
    W = np.where(z['cheek'], 0.012, W)
    lift = np.where(z['cheek'], _rad(6), lift)
    L = np.where(z['chin'], 0.05, L)
    L = np.where(z['ear'], 0.04, L)
    W = np.where(z['ear'], 0.009, W)
    near_eye = smooth(EYE_R * 1.25, EYE_R * 2.2, z['eye_d'])
    L = L * (0.45 + 0.55 * near_eye)
    W = W * (0.6 + 0.4 * near_eye)
    brow = in_ellipsoid(p, *BROW_PATCH) < 1.0
    L = np.where(brow, 0.022, L)
    W = np.where(brow, 0.0065, W)
    lift = np.where(brow, _rad(0.5), lift)
    snout = z['muzzle'] | z['chin'] | ((p[:, 1] < -0.56) & (p[:, 2] < 1.0))
    L = np.where(snout, 0.022, L)
    W = np.where(snout, 0.0062, W)
    lift = np.where(snout, _rad(1.0), lift)
    skip = (~z['head'] | z['mane'] | z['ruff'] | z['nose'] | (z['eye_d'] < EYE_R * 1.2)
            | (mouth_mask(p) > 0.05) | (p[:, 1] < NOSE_C.y + 0.008)
            | (z['ear_inner'] & (z['ear_u'] > 0.32)))
    return np.where(skip, np.nan, W * 0.55), L, W, lift, z


def body_lock_params(p, n):
    """Thick fur in layered clumps (the pictures): longer, wider locks than Puddlepup's, lifting more at their tips."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.125)
    W = np.full(k, 0.024)
    lift = np.full(k, _rad(8))
    L = np.where(z['belly'], 0.1, L)
    L = np.where(z['chest'], 0.11, L)
    W = np.where(z['chest'], 0.02, W)
    upper = z['leg'] & (p[:, 2] > 0.3)
    L = np.where(z['leg'], np.where(upper, 0.08, 0.055), L)
    W = np.where(z['leg'], np.where(upper, 0.016, 0.012), W)
    L = np.where(z['paw'], 0.032, L)
    W = np.where(z['paw'], 0.009, W)
    L = np.where(z['tail'], 0.11, L)
    W = np.where(z['tail'], 0.02, W)
    lift = np.where(z['tail'], _rad(9), lift)
    # round 8c: broad, flat strands along each sculpted lock (fine ones made the bare locks a busy, mottled feather texture)
    L = np.where(z['mane'], 0.055, L)
    W = np.where(z['mane'], 0.016, W)
    lift = np.where(z['mane'], _rad(3), lift)
    L = np.where(z['ruff'], 0.06, L)
    W = np.where(z['ruff'], 0.014, W)
    lift = np.where(z['ruff'], _rad(7), lift)
    L = np.where(z['plume'], 0.17, L)
    W = np.where(z['plume'], 0.028, W)
    # round 5: the plume's clumps lift more toward the tip, so the back view sees ridges instead of a smooth core
    lift = np.where(z['plume'], _rad(8) + _rad(4) * smooth(0.45, 0.9, z['tail_t']), lift)
    skip = (z['head'] & ~z['chest'] & ~z['mane'] & ~z['ruff']) | z['toes'] | z['sole'] | (z['paw'] & (p[:, 2] < 0.03))
    # round 8d: none on the crown's sculpted tuft (20 cm strokes from it ran across the ear and the temple)
    return np.where(skip, np.nan, W * 0.6), L, W, lift, z


LOCK_TEMPLATES = {'head': (7, 11, 3, 0.22), 'body': (5, 11, 3, 0.26)}
CARD_LAYERS = 1            # round 8d: the coat only (the hair layers on the legs and the crown read as combs and dashes)
# round 6 (RECIPE.md, Nov 8): layer 0 is the coat (fur tiles); layers 1 and 2 are the mane's and the plume's long
# cards, drawn with the thin tapered, shaded 'hair' strands (the fur tiles' broad lobes read as cut-paper blades);
# the game fades the cards' edges later, so long mane cards show more face-on
CARD_LAYER_STYLES = ('fur',)
CARD_COLOUR_FROM = 'skin'    # the bare skin's bake at each card's root (round 9b: the paint path washed the cards grey-white; near_marks keeps cards off the stars)
CARD_SHADE = 1.0
AO_FLOOR = 0.56            # round 4: the dense locks' narrow slots no longer bake near black
AO_SOFTEN = 2.0


def _near_locks(p: np.ndarray, r: float = 0.04) -> np.ndarray:
    """Points within about `r` of a sculpted mane or tail lock."""
    out = np.zeros(len(p), bool)
    for name in ('mane', 'tail'):
        for d in ((r, 0, 0), (-r, 0, 0), (0, r, 0), (0, -r, 0), (0, 0, r), (0, 0, -r)):
            out |= LK.lookup(p + np.array(d, float), name)[0]
    return out


def card_params(p, n, layer: int):
    """Soft fur cards for the outline. 0: the whole coat; 1: the fringes (cheek ruff, throat, belly, elbows, the backs
    of the thighs, the ears' edges, the plume's edges); 2: the long feathering of the tail plume and the britches.
    None under the mane (its locks are the outline there) or on the face, the ears' hollows, the toes."""
    z = zones(p, n)
    k = len(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    head = z['head']
    t = tone_masks(p, z)
    paw_tuft = z['paw'] & (zz > 0.058) & (zz < 0.09)
    if layer == 0:
        L = np.where(head, 0.05, 0.085)
        W = np.where(head, 0.032, 0.05)
        lift = np.where(head, _rad(4), _rad(7))
        L = np.where(z['ear'], 0.032, L)
        W = np.where(z['ear'], 0.026, W)
        # round 5: the leg cards lie flatter and shorter (they drew a pale scratchy fringe round the leg outlines)
        L = np.where(z['leg'], 0.042, L)
        W = np.where(z['leg'], 0.05, W)
        lift = np.where(z['leg'], _rad(3), lift)
        L = np.where(z['paw'], 0.036, L)
        L = np.where(z['leg'] & (zz < 0.2), 0.03, L)
        L = np.where(paw_tuft, 0.028, L)
        W = np.where(paw_tuft, 0.032, W)
        L = np.where(z['tail'], 0.12, L)
        W = np.where(z['tail'], 0.05, W)
        # round 5: the plume's cards lift more toward the tip (the back view sees fur, not the core)
        lift = np.where(z['tail'], _rad(8) + _rad(6) * smooth(0.5, 0.95, z['tail_t']), lift)       # round 7b: the clumps are the shape
        # round 6 (review: short, wide, flat mint blades): many narrower, longer cards with lift, in three dense layers
        # (how Tumblefox's tail and Puddlepup's coat get their softness)
        L = np.where(z['mane'], 0.11, L)
        W = np.where(z['mane'], 0.022, W)
        lift = np.where(z['mane'], _rad(6), lift)
        L = np.where(z['ruff'], 0.055, L)
        W = np.where(z['ruff'], 0.045, W)
        lift = np.where(z['ruff'], _rad(5), lift)
        sp = np.where(head, 0.018, 0.024)
        sp = np.where(z['leg'], 0.025, sp)
        sp = np.where(z['plume'], 0.034, sp)        # round 7: sparser fur tiles over the sculpted clumps (they are the mass now)
        sp = np.where(z['mane'], 0.034, sp)
        sp = np.where(z['ruff'], 0.02, sp)
        skip = (z['face'] | z['muzzle'] | z['nose'] | (z['eye_d'] < 0.075) | z['ear_root'] | z['ear_inner'] | z['toes'] | z['sole']
                | (z['chin'] & (y < -0.55)) | (z['ear'] & ((z['ear_u'] > 0.7) | z['ear_rim'])) | ((zz < 0.08) & ~paw_tuft)
                | (in_ellipsoid(p, *BROW_PATCH) < 1.3)
                # round 6: no cards on the lower legs (they drew a pale scratchy fringe round the outlines; the lying
                # locks are the fur there)
                | (z['leg'] & (zz < 0.46))            # round 8d: the whole leg (comb teeth from the front and the back)
                | (zz < 0.3) | z['belly'] | (t['pale'] > 0.3)        # … the cuffs, the paws and the pale underside
                | _near_locks(p)
                # round 7: no fur-tile cards on the teal and rose mane (the sculpted locks are its mass; its cards are
                # the hair layers); the indigo ring behind the cheeks keeps them
                | z['mane'] | z['ruff'] | z['plume']
                # round 7c: none on the cheeks either (pale blades stood out as a comb against the indigo ring; the
                # cheek fluff is the lying locks)
                | z['cheek']
                | (head & (y < -0.42) & ~z['ear'] & ~z['cheek'] & ~z['mane'] & ~z['ruff']))
    elif layer == 1:
        L = np.full(k, 0.1)
        W = np.full(k, 0.05)
        lift = np.full(k, _rad(10))
        sp = np.full(k, 0.033)
        cheek_ruff = z['cheek'] & (y > -0.5) & (zz < 0.99)
        throat = ~head & (y < -0.4) & (zz > 0.46) & (zz < 0.88) & (np.abs(x) < 0.13)
        belly = z['belly'] & (zz < 0.5)
        leg_back = np.zeros(k, bool)
        for lg, (lx, ly) in LEGS.items():
            if lg[0] == 'F':
                leg_back |= z['legs'][lg] & (y > ly + 0.02) & (zz > 0.2) & (zz < 0.45)
            else:
                leg_back |= z['legs'][lg] & (y > ly - 0.04) & (zz > 0.15)
        ear_edge = z['ear'] & z['ear_rim'] & (z['ear_u'] > 0.15)
        plume_edge = z['plume'] & (z['tail_h'] < 0.0)
        L = np.where(cheek_ruff, 0.05, L)
        W = np.where(cheek_ruff, 0.042, W)
        sp = np.where(cheek_ruff, 0.02, sp)
        lift = np.where(cheek_ruff, _rad(5), lift)
        L = np.where(throat, 0.065, L)
        W = np.where(throat, 0.04, W)
        lift = np.where(throat, _rad(5), lift)
        sp = np.where(throat, 0.024, sp)
        L = np.where(belly, 0.07, L)
        W = np.where(belly, 0.06, W)
        L = np.where(leg_back, 0.06, L)
        W = np.where(leg_back, 0.055, W)
        L = np.where(ear_edge, 0.035, L)
        W = np.where(ear_edge, 0.022, W)
        sp = np.where(ear_edge, 0.016, sp)
        lift = np.where(ear_edge, _rad(14), lift)
        L = np.where(plume_edge, 0.14, L)
        W = np.where(plume_edge, 0.055, W)
        lift = np.where(plume_edge, _rad(8) + _rad(4) * smooth(0.5, 0.95, z['tail_t']), lift)
        sp = np.where(plume_edge, 0.036, sp)
        mane1 = z['mane'] & (zz < 0.95)
        plume1 = z['plume']
        # round 7b: the hair lies along the sculpted locks (6–8° of lift; at 13–16° it stood out in a ragged halo) and
        # is a little wider and sparser, so the locks' own shapes show through it
        L = np.where(mane1, 0.13, L)
        W = np.where(mane1, 0.03, W)
        lift = np.where(mane1, _rad(6), lift)
        sp = np.where(mane1, 0.029, sp)
        L = np.where(plume1, 0.15, L)
        W = np.where(plume1, 0.06, W)
        lift = np.where(plume1, _rad(8) + _rad(4) * smooth(0.5, 0.95, z['tail_t']), lift)
        sp = np.where(plume1, 0.04, sp)
        L = np.where(throat | z['ruff'], 0.065, L)
        W = np.where(throat | z['ruff'], 0.045, W)
        lift = np.where(throat | z['ruff'], _rad(5), lift)
        # round 7b: no cheek fringe cards (pale blades against the mane's indigo ring read as quills)
        # round 8 (review: shards, comb teeth, needles, paper chips): no cards on the mane, the ruff, the throat or the
        # plume; their sculpted locks and clumps are the look
        fringe = belly | leg_back
        skip = ~fringe | z['face'] | z['muzzle'] | (z['eye_d'] < 0.08) | z['ear_inner'] | z['ear_root']
    else:
        L = np.full(k, 0.16)
        W = np.full(k, 0.06)
        lift = np.full(k, _rad(14))
        sp = np.full(k, 0.037)
        plume = z['tail'] & (z['tail_t'] > 0.08)
        britches = np.zeros(k, bool)
        for lg, (lx, ly) in LEGS.items():
            if lg[0] == 'B':
                britches |= z['legs'][lg] & (y > ly - 0.04) & (zz > 0.28)
        mane2 = z['mane'] & (zz < 0.9)
        plume2 = z['plume'] & (z['tail_t'] > 0.2)
        # round 6 (review: a flat pink oval from behind): the plume's rear end gets its own cards, standing out from
        # the core toward a camera behind it
        plume_rear = z['plume'] & (z['tail_t'] > 0.62)
        crown2 = z['crown'] & (np.abs(x) < 0.04) & (y > -0.43) & (y < -0.3)
        L = np.where(britches, 0.1, L)
        W = np.where(britches, 0.05, W)
        sp = np.where(britches, 0.04, sp)
        L = np.where(mane2, 0.14, L)
        W = np.where(mane2, 0.032, W)
        lift = np.where(mane2, _rad(8), lift)
        sp = np.where(mane2, 0.036, sp)
        L = np.where(plume2, 0.18, L)
        W = np.where(plume2, 0.065, W)
        lift = np.where(plume2, _rad(9), lift)
        sp = np.where(plume2, 0.046, sp)
        L = np.where(plume_rear, 0.15, L)
        W = np.where(plume_rear, 0.05, W)
        lift = np.where(plume_rear, _rad(12), lift)        # round 7b: no burst (the sculpted clumps fan there now)
        sp = np.where(plume_rear, 0.036, sp)
        L = np.where(crown2, 0.085, L)
        W = np.where(crown2, 0.035, W)
        lift = np.where(crown2, _rad(35), lift)
        sp = np.where(crown2, 0.014, sp)
        skip = ~(britches | crown2)
    # no cards where the coat changes tone sharply (a dark card over pale fur, or the reverse, glittered at the border)
    # (the face's sharp pale borders only: the legs' gentle gradient keeps its fur)
    border = (t['pale'] > 0.08) & (t['pale'] < 0.92) & z['head']
    skip = skip | border | near_marks(p)
    return np.where(skip, np.nan, sp), L, W, lift, z


# ----------------------------------------------------------------------------- marks: stars, constellations, the brow cluster
_MARKS: dict = {}


def near_marks(p: np.ndarray) -> np.ndarray:
    """Points within reach of a star or a constellation line (the cards keep clear of them)."""
    mk = _MARKS.get('v')
    out = np.zeros(len(p), bool)
    if not mk:
        return out
    for st in mk.get('stars', []) + mk.get('brow', []):
        c = np.array(st[:3])
        r = st[6] * STAR_SCALE * 1.6 + 0.008
        out |= ((p - c) ** 2).sum(1) < r * r
    for ln in mk.get('lines', []):
        a, b = np.array(ln[:3]), np.array(ln[3:6])
        ab = b - a
        t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        out |= np.linalg.norm(p - (a + t[:, None] * ab), axis=1) < 0.007
    # round 7: the charts' stars and lines (a smaller reach: there are hundreds of them, and a card only smears a
    # star's colour when it is rooted right on it)
    cs = mk.get('chart_stars', [])
    if cs:
        c = np.array([st[:3] for st in cs])
        r = np.array([st[3] * 0.9 + 0.003 for st in cs])
        for i0 in range(0, len(p), 4000):
            q = p[i0:i0 + 4000].astype(np.float32)
            d2 = ((q[:, None, :] - c[None].astype(np.float32)) ** 2).sum(2)
            out[i0:i0 + 4000] |= (d2 < (r * r)[None]).any(1)
    for ln in mk.get('chart_lines', []):
        a, b = np.array(ln[:3]), np.array(ln[3:6])
        ab = b - a
        t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        out |= np.linalg.norm(p - (a + t[:, None] * ab), axis=1) < 0.004
    return out


def _surface_pt(bvh: BVHTree, p) -> tuple[np.ndarray, np.ndarray] | None:
    hit = bvh.find_nearest(Vector(tuple(map(float, p))))
    if hit[0] is None:
        return None
    return np.array(hit[0]), np.array(hit[1])


# constellation anchors (left side; the right side gets its own, not a mirror): (centre, stars, spread)
CONSTELLATIONS = {
    1: [((0.155, -0.1, 0.56), 6, 0.06), ((0.155, 0.12, 0.62), 7, 0.065), ((0.17, 0.36, 0.6), 5, 0.06), ((0.05, 0.22, 0.75), 5, 0.06),
        ((0.15, -0.28, 0.3), 4, 0.045), ((0.17, 0.3, 0.42), 4, 0.05), ((0.03, 0.72, 0.82), 4, 0.05),
        ((0.17, -0.18, 0.48), 4, 0.045), ((0.14, -0.3, 0.16), 3, 0.035), ((0.15, 0.5, 0.22), 3, 0.04), ((0.03, 0.44, 0.73), 4, 0.045)],
    -1: [((-0.155, -0.06, 0.6), 6, 0.065), ((-0.16, 0.16, 0.58), 6, 0.06), ((-0.17, 0.4, 0.62), 5, 0.06), ((-0.05, 0.08, 0.76), 4, 0.06),
         ((-0.15, -0.28, 0.24), 4, 0.045), ((-0.17, 0.33, 0.45), 4, 0.05), ((-0.04, 0.6, 0.77), 4, 0.05),
         ((-0.17, -0.16, 0.5), 4, 0.045), ((-0.14, -0.3, 0.14), 3, 0.035), ((-0.15, 0.49, 0.25), 3, 0.04), ((-0.14, -0.4, 0.5), 3, 0.04)],
}


# Round 6: 330 node twinkles plus six more constellations overflowed Cycles' SVM stack ("shader paint_base too big") and
# the body baked black (on the real meshes 200 stars + 81 lines bake, 275 + 81 don't: scratchpad r5/svm_real.py).
# Round 7 (the owner: fewer twinkles than the pictures): the stars moved out of the shader's node graph into STAR
# CHARTS: four images painted in numpy (the left and the right side seen along X, the top seen along Z, the rear seen
# along Y), each sampled by ONE image node at the surface's projected position. Any number of stars and linking lines
# costs the same few nodes, so the coat carries hundreds of twinkles and every constellation keeps its lines. A star
# goes to the chart its surface faces (at least CHART_MIN_FACING) and only where nothing stands in front of it along
# that axis; the body's sources carry per-vertex chart weights (`chart_s`, `chart_t`, `chart_b`: by the skin's normal,
# so a top surface never smears a side chart's stars). Only the brow cluster and a few twinkles on the head and the
# ears, which face no chart, stay as node marks.
TWINKLES = 26            # node twinkles: the head and the ears' backs only
CHART_TWINKLES = 170     # twinkles in the charts (round 8: fewer and bigger; 520 tiny ones read as frost at clip size)
CHART_PX = 1000.0        # texels per metre in a chart (1 mm; the atlas holds about 1.3 mm)
CHART_MIN_FACING = 0.78
_D = 0.7071067811865476
# name, the direction the chart is seen from (unit), the chart's u and v axes (unit), their ranges in metres, the side
# of the body it serves (+1 left, −1 right, 0 both) and the least y. The two diagonal charts cover the bands between
# the flanks and the back, which face neither X nor Z squarely.
CHARTS = [
    ('L', (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (-0.8, 1.32), (0.0, 1.34), 1, -9.0),
    ('R', (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (-0.8, 1.32), (0.0, 1.34), -1, -9.0),
    ('T', (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-0.38, 0.38), (-0.8, 1.32), 0, -9.0),
    ('B', (0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (-0.38, 0.38), (0.0, 1.34), 0, 0.25),
    ('UL', (_D, 0.0, _D), (0.0, 1.0, 0.0), (-_D, 0.0, _D), (-0.8, 1.32), (-0.3, 1.0), 1, -9.0),
    ('UR', (-_D, 0.0, _D), (0.0, 1.0, 0.0), (_D, 0.0, _D), (-0.8, 1.32), (-0.3, 1.0), -1, -9.0),
]
# more linked constellations now that lines are free (the reviews: only one or two linked groups showed)
CONSTELLATIONS_MORE = {
    1: [((0.14, -0.2, 0.72), 5, 0.055), ((0.17, 0.02, 0.5), 5, 0.055), ((0.02, 0.3, 0.745), 4, 0.05), ((0.19, 0.42, 0.45), 5, 0.05),
        ((0.06, -0.04, 0.76), 4, 0.05), ((0.16, 0.24, 0.55), 5, 0.055)],
    -1: [((-0.14, -0.18, 0.7), 5, 0.055), ((-0.17, 0.05, 0.48), 5, 0.055), ((-0.03, 0.4, 0.74), 4, 0.05), ((-0.19, 0.44, 0.42), 5, 0.05),
         ((-0.06, 0.2, 0.76), 4, 0.05), ((-0.16, -0.02, 0.62), 5, 0.055)],
}


BIG_STARS = [(0.16, -0.05, 0.66), (0.17, 0.2, 0.52), (0.19, 0.4, 0.52), (0.17, 0.33, 0.68), (0.15, -0.26, 0.42), (0.16, 0.1, 0.72),
             (0.17, 0.46, 0.34)]


def chart_facing(p, nrm, ci: int) -> float:
    """How squarely the surface at p (normal nrm) faces chart ci: 1 = straight on; −1 if p is outside the chart's part
    of the body."""
    _nm, axis, _eu, _ev, _ur, _vr, side, ymin = CHARTS[ci]
    if (side and p[0] * side <= 0.02) or p[1] < ymin:
        return -1.0
    return float(nrm[0] * axis[0] + nrm[1] * axis[1] + nrm[2] * axis[2])


def chart_of(p, nrm, need: float = CHART_MIN_FACING) -> int | None:
    """The chart a surface point belongs to (the one it faces most squarely, at least `need`), else None."""
    f = [chart_facing(p, nrm, i) for i in range(len(CHARTS))]
    i = int(np.argmax(f))
    return i if f[i] >= need else None


def chart_weights(root: np.ndarray, nrm: np.ndarray) -> dict[str, np.ndarray]:
    """Per vertex: how much each chart shows there, by the skin's normal: `chart_s` (+ the left chart, − the right),
    `chart_d` (+ the upper-left diagonal, − the upper-right), `chart_t` (the top) and `chart_b` (the rear)."""
    w = {}
    for nm, axis, _eu, _ev, _ur, _vr, side, ymin in CHARTS:
        k = smooth(0.5, 0.68, nrm @ v3(axis)) * (root[:, 1] >= ymin)
        if side:
            k = k * (root[:, 0] * side > 0.01)
        w[nm] = k
    return {'chart_s': w['L'] - w['R'], 'chart_d': w['UL'] - w['UR'], 'chart_t': w['T'], 'chart_b': w['B']}


def _seen(bvh: BVHTree, p, nrm, ci: int) -> bool:
    """Nothing stands in front of the point along its chart's axis (a star behind a leg or the mane would show on both)."""
    o = np.asarray(p, float) + np.asarray(nrm, float) * 0.006
    return bvh.ray_cast(Vector(tuple(map(float, o))), Vector(CHARTS[ci][1]))[0] is None


def make_marks(body: bpy.types.Object, seed: int = 25) -> dict:
    if _MARKS.get('v') and _MARKS.get('body') == body.name:
        return _MARKS['v']
    _MARKS['body'] = body.name
    return _make_marks(body, seed)


def _make_marks(body: bpy.types.Object, seed: int = 25) -> dict:
    """The stars on the coat (positions on the high body): constellations of 4–7 stars joined by faint lines, single
    twinkles scattered over the dark fur, and the star cluster on the brow (one big four-pointed star between and
    above the eyes, small ones round it, a few up the crown). Each star: (x, y, z, nx, ny, nz, radius, flare, gold)."""
    rng = np.random.default_rng(seed)
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    co, vn = S.mesh_arrays(body)
    z = zones(co, vn)
    t = tone_masks(co, z)
    ok = ((t['pale'] < 0.1) & (t['inner_ear'] < 0.1) & ~z['paw'] & ~z['mane'] & ~z['ruff'] & ~z['face'] & (t['aurora'] < 0.3)
          & (co[:, 2] > 0.08) & (in_ellipsoid(co, *BROW_PATCH) > 1.5))          # (the brow cluster keeps its own patch)
    # ---- the charts' marks (round 7): [x, y, z, radius, flare (0 a dot, 1 a small sparkle, 2 a big one), gold, chart]
    cstars, clines = [], []
    n_const = 0
    for s in (1, -1):
        # round 8: the bigger figures only, spread wider (4–6 a side read as constellations; many small ones as noise)
        for c, count, spread in [(c_, n_, sp_ * 1.3) for c_, n_, sp_ in CONSTELLATIONS[s] + CONSTELLATIONS_MORE[s] if n_ >= 5]:
            hit = _surface_pt(bvh, c)
            if hit is None:
                continue
            p, nrm = hit
            ci = chart_of(p, nrm, 0.6)
            others = np.array([st[:3] for st in cstars]) if cstars else np.zeros((0, 3))     # the earlier constellations' stars

            def clear_of(q, reach, others=others) -> bool:
                return not len(others) or float(((others - q) ** 2).sum(1).min()) > reach * reach
            if ci is None or not _seen(bvh, p, nrm, ci) or not clear_of(p, 0.06):
                continue
            heading = rng.normal(0, 1, 3)
            chain: list[list[float]] = []
            normals = []
            for i in range(count):
                if i > 0:
                    hit = None
                    for _try in range(6):            # another heading if this one leaves the chart or meets another group
                        tdir = heading - nrm * (heading @ nrm)
                        tdir /= max(np.linalg.norm(tdir), 1e-9)
                        hit = _surface_pt(bvh, p + tdir * spread * rng.uniform(0.65, 1.15))
                        if (hit is not None and chart_facing(hit[0], hit[1], ci) >= 0.5 and _seen(bvh, hit[0], hit[1], ci)
                                and clear_of(hit[0], 0.035)):
                            break
                        hit = None
                        heading = rng.normal(0, 1, 3)
                    if hit is None:
                        break
                    p, nrm = hit
                    heading = heading + rng.normal(0, 1, 3) * 0.9
                big = i == 0 or rng.random() < 0.25
                r = rng.uniform(0.0085, 0.011) if big else rng.uniform(0.005, 0.007)
                cstars.append([*map(float, p), r, 2.0 if big else float(rng.random() < 0.5), float(rng.random() < 0.4), float(ci)])
                if chain:
                    clines.append([*chain[-1], *map(float, p), float(ci)])
                chain.append([float(v) for v in p])
                normals.append(nrm.copy())
            if len(chain) >= 4:               # one branch from the middle star
                a, na = np.array(chain[len(chain) // 2]), normals[len(chain) // 2]
                tdir = rng.normal(0, 1, 3)
                tdir -= na * (tdir @ na)
                tdir /= max(np.linalg.norm(tdir), 1e-9)
                hit = _surface_pt(bvh, a + tdir * spread)
                if hit is not None and chart_facing(hit[0], hit[1], ci) >= 0.5 and _seen(bvh, hit[0], hit[1], ci):
                    cstars.append([*map(float, hit[0]), rng.uniform(0.005, 0.0065), 0.0, float(rng.random() < 0.4), float(ci)])
                    clines.append([*map(float, a), *map(float, hit[0]), float(ci)])
            n_const += 1
    # single twinkles over the dark coat (not the face, the ears' hollows, the paws or the mane): mostly tiny dots, some
    # small four-pointed sparkles and a few big ones; a third of them gold
    pts = np.array([st[:3] for st in cstars]) if cstars else np.zeros((0, 3))
    made = 0
    for i in rng.permutation(np.nonzero(ok)[0]):
        if made >= CHART_TWINKLES:
            break
        q, qn = co[i], vn[i]
        ci = chart_of(q, qn)
        if ci is None or (len(pts) and float(((pts - q) ** 2).sum(1).min()) < 0.028 ** 2) or not _seen(bvh, q, qn, ci):
            continue
        u = rng.random()
        r, fl = ((rng.uniform(0.004, 0.0056), 0.0) if u < 0.5 else (rng.uniform(0.0055, 0.007), 1.0) if u < 0.86
                 else (rng.uniform(0.008, 0.0105), 2.0))
        cstars.append([*map(float, q), r, fl, float(rng.random() < 0.3), float(ci)])
        pts = np.vstack([pts, q])
        made += 1
    # round 8: a dozen bigger blue-white and gold stars on the shoulders, flanks and thighs (2-turnaround side)
    for bx, by, bz in BIG_STARS:
        for sgn in (1, -1):
            hit = _surface_pt(bvh, (bx * sgn, by + rng.normal(0, 0.02), bz + rng.normal(0, 0.02)))
            if hit is None:
                continue
            ci = chart_of(hit[0], hit[1], 0.6)
            if ci is None or not _seen(bvh, hit[0], hit[1], ci) or float(((pts - hit[0]) ** 2).sum(1).min()) < 0.03 ** 2:
                continue
            cstars.append([*map(float, hit[0]), rng.uniform(0.012, 0.015), 2.0, float(rng.random() < 0.4), float(ci)])
            pts = np.vstack([pts, hit[0]])
    # ---- node marks: a few twinkles where no chart looks (the head and the ears' backs), and the brow cluster
    stars: list = []
    head_ok = ok & z['head']
    picked: list[np.ndarray] = []
    for i in rng.permutation(np.nonzero(head_ok)[0]):
        if len(stars) >= TWINKLES:
            break
        q = co[i]
        if chart_of(q, vn[i]) is not None or (picked and float(np.min(np.linalg.norm(np.array(picked) - q, axis=1))) < 0.035):
            continue
        picked.append(q)
        stars.append([*q, *vn[i], rng.uniform(0.0022, 0.0034), float(rng.random() < 0.3), 0.0])
    # the brow cluster (1-hero, 3-faces: always shows): one big four-pointed star, small four-pointed satellites round
    # it and one under it, and a few dots (round 3's long line under the star read as a crosshair; this one is short)
    brow = []
    for dx, dz, r, fl in ((0.0, 0.0, 0.0085, 2.0), (0.027, 0.012, 0.0042, 1.0), (-0.027, 0.012, 0.0042, 1.0), (0.017, 0.036, 0.0036, 1.0),
                          (-0.017, 0.036, 0.0036, 1.0), (0.0, 0.052, 0.0038, 1.0), (0.0, -0.027, 0.0032, 1.0),
                          (0.041, 0.03, 0.0022, 0.0), (-0.043, 0.028, 0.0022, 0.0), (0.03, 0.056, 0.002, 0.0), (-0.012, 0.072, 0.002, 0.0)):
        hit = _surface_pt(bvh, (BROW_STAR.x + dx, BROW_STAR.y + 0.03, BROW_STAR.z + dz))
        if hit is not None:
            brow.append([*hit[0], *hit[1], r, fl, 1.0 if fl == 2.0 else 0.0])
    per = [sum(1 for st in cstars if int(st[6]) == i) for i in range(len(CHARTS))]
    C.log(f'marks: charts {len(cstars)} stars ({n_const} constellations, {made} twinkles; per chart {per}), {len(clines)} lines; '
          f'nodes {len(stars)} twinkles, {len(brow)} on the brow')
    return {'stars': stars, 'lines': [], 'brow': brow, 'chart_stars': cstars, 'chart_lines': clines}


# ----------------------------------------------------------------------------- paint (numpy, per source vertex)
_TONE: dict[str, dict] = {}


def _tones_of(ob, root: np.ndarray, pos: np.ndarray, kind: np.ndarray, tpos: np.ndarray) -> dict:
    """The tone masks a source is painted with, by the root (the markings follow the fur); a lock that crosses a
    border blends toward the tone under its tip along its length."""
    if ob.name not in _TONE:
        t = tone_masks(root, zones(root))
        lock = kind > 0.5
        if lock.any():
            tp = tone_masks(pos[lock], zones(pos[lock]))
            k = 0.6 * tpos[lock]
            for key in t:
                t[key][lock] = t[key][lock] * (1 - k) + tp[key] * k
        _TONE[ob.name] = t
    return _TONE[ob.name]


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    col = colours(pal)
    root = S.attr_array(ob, 'root').astype(np.float64)
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    pos = co.reshape(-1, 3).astype(np.float64)
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    lrand = S.attr_array(ob, 'lrand').astype(np.float64)
    t = _tones_of(ob, root, pos, kind, tpos)
    rgb = tone_rgb(t, col)
    # the clumps: a darker root and a lighter, slightly bluer tip on every lock (layered fur)
    # round 6 (review: a pale silvery streak layer along the back and rump): the clumps stay deep indigo, with only a
    # little lift at the tips
    shade = 0.6 + 0.42 * tpos + 0.12 * (lrand - 0.5)
    shade = shade * (1 - 0.6 * t['pale']) + (0.8 + 0.25 * tpos) * 0.6 * t['pale']
    shade = shade * (1 - t['mane']) + (0.8 + 0.28 * tpos) * t['mane']         # round 7b: the mane's lying locks keep their light
    shade = np.where(kind < 0.5, 1.0, shade)
    tipcol = np.clip(tpos - 0.55, 0, 1)[:, None] * 0.08 * (1 - t['pale'][:, None]) * (1 - t['mane'][:, None]) * (1 - t['aurora'][:, None])
    rgb = rgb * (1 - tipcol) + lin(col['light'])[None] * tipcol
    # the aurora's lock tips paler and lighter (silky, glowing)
    atip = (smooth(0.55, 1.0, tpos) * np.maximum(t['mane'], t['aurora']) * 0.35)[:, None]
    rgb = rgb * (1 - atip) + np.clip(rgb * 1.3 + 0.05, 0, 1) * atip
    # (round 7: round 5's painted strand streaks over the aurora skin are gone: they showed as diagonal hatching, and
    # the sculpted locks and clumps give the mane and the plume their relief now)
    is_lock = kind > 0.5
    # round 8: matter fur (the Lite copy, which has no cards over it, showed a glossy grey-silver streak down the back)
    rough = np.where(is_lock, 0.82 + 0.08 * np.abs(tpos - 0.45), 0.84)
    coat = np.where(is_lock, 0.02, 0.02)
    zr = zones(pos)
    # the nose, the pads and the claws are glossy; the claws slate, the pads dark
    glossy = ell_soft(pos, tuple(NOSE_C), (0.02, 0.017, 0.015), 0.08) * 0.6     # round 5: a smaller, less glossy nose
    pads = np.zeros(len(pos))
    claws = np.zeros(len(pos))
    for leg in LEGS:
        pc, pr = pad_centre(leg)
        pads = np.maximum(pads, ell_soft(pos, tuple(pc), pr, 0.15))
        for tc in toe_centres(leg):
            pads = np.maximum(pads, ell_soft(pos, tuple(tc + Vector((0, 0, -0.022))), (0.016, 0.019, 0.012), 0.2))
        for cc in claw_centres(leg):
            claws = np.maximum(claws, ell_soft(pos, tuple(cc + Vector((0, -0.005, 0))), (0.0095, 0.019, 0.009), 0.15))
    pads *= smooth(0.013, 0.006, pos[:, 2])
    glossy = np.maximum(glossy, np.maximum(pads * 0.6, claws * 0.7))
    rgb = rgb * (1 - pads[:, None]) + lin(col['pad'])[None] * pads[:, None]
    rgb = rgb * (1 - claws[:, None]) + lin(col['claw'])[None] * claws[:, None]
    # round 5 (review: a gloss hotspot on the skull, a plastic bill): the whole head as matte as the body fur
    snout = ell_soft(pos, MUZZLE[0], tuple(r * 1.25 for r in MUZZLE[1]), 0.2)
    rough = np.maximum(rough, 0.92 * snout)
    rough = np.where(zr['head'] & ~zr['ear'], np.maximum(rough, 0.92), rough)
    coat = np.where(zr['head'] & ~zr['ear'], 0.0, coat)
    rough = rough * (1 - glossy) + 0.42 * glossy
    coat = coat * (1 - glossy) + 0.45 * glossy
    # the inner ear's skin: soft, a little satin
    rough = np.where(t['inner_ear'] > 0.5, 0.5, rough)
    dark = np.clip(1.0 - t['pale'] - t['inner_ear'] - t['aurora'] - pads - claws - 0.35 * t['light']
                   - t['mane'] * (1 - t['mane_ind']), 0, 1) * (1 - zr['nose'])        # round 8: no star dust on the teal and rose mane (frost)
    return {'paint': rgb, 'dark': dark, 'shade': shade, 'rough': np.stack([np.ones(len(pos)), rough, coat], axis=1)}


def aurora(u: np.ndarray, layer_k: np.ndarray, lr: np.ndarray, col: dict, zpos: np.ndarray, low: tuple[float, float],
           tip_start: float = 0.64, low_from: tuple[float, float] = (0.25, 0.55)) -> np.ndarray:
    """The aurora along a lock: indigo-teal at the root, teal through most of it, rose toward the tip; lower and outer
    locks turn rose sooner, the lowest-hanging tips are rose (the front view's pink bib and the side's pink fringe),
    and a few locks run more teal or more rose (the pictures' variegated locks)."""
    root = lin(col['aurora_root'])
    teal = lin(col['teal'])
    deep = lin(col['teal_deep'])
    rose = lin(col['rose'])
    k_root = smooth(0.32, 0.0, u) * 0.8
    # teal shades from deep aqua (the lock's first half, the layers lying underneath) to the palette's teal toward the tip
    k_deep = np.clip(smooth(0.7, 0.15, u) * 0.6 + 0.2 * np.clip(layer_k, 0, 1) * smooth(0.95, 0.5, u), 0, 1)
    teal = teal[None] * (1 - k_deep[:, None]) + deep[None] * k_deep[:, None]
    start = tip_start - 0.1 * layer_k + 0.1 * (lr - 0.5)
    tip_rose = smooth(start, start + 0.32, u) * (0.8 + 0.2 * lr)
    k_rose = np.maximum(tip_rose, smooth(low[0], low[1], zpos) * smooth(low_from[0], low_from[1], u))
    rgb = teal * (1 - k_rose[:, None]) + rose[None] * k_rose[:, None]
    rgb = rgb * (1 - k_root[:, None]) + root[None] * k_root[:, None]
    return rgb * (0.8 + 0.2 * lr)[:, None]


def fin_arrays(ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    """The mane's and the tail's aurora locks and the tail star. The locks are a touch below the palette's brightness
    and pale toward their tips (they glow in the game; review: the pilot's membranes bloomed white when painted at full
    strength), with fine strands; the star is warm white-gold."""
    col = colours(pal)
    fan = S.attr_array(ob, 'fan').astype(np.float64)
    part = S.attr_array(ob, 'fin_part')
    lr = S.attr_array(ob, 'lrand').astype(np.float64)
    across = S.attr_array(ob, 'across').astype(np.float64)
    u = fan[:, 0]
    n = len(u)
    co = np.empty(n * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    zpos = co.reshape(-1, 3)[:, 2].astype(np.float64)
    is_mane = (np.abs(part - M.MANE) < 0.5) | (np.abs(part - M.CROWN) < 0.5) | (np.abs(part - M.RUFF) < 0.5)
    layer_k = np.where(is_mane, fan[:, 2] / 6.0, np.clip((fan[:, 2] % 1.0 - 0.3) / 0.65, 0, 1) * 0.6 + 0.2 * np.abs(fan[:, 1]))
    rgb = np.where(is_mane[:, None], aurora(u, layer_k, lr, col, zpos, (0.5, 0.38), 0.62, (0.25, 0.55)) * 1.05,
                   aurora(u, layer_k, lr, col, zpos, (0.72, 0.54), 0.84, (0.0, 0.3))) * 0.86
    # strands: fine lighter and darker lines along the lock
    strand = np.sin(across * math.pi * 11.0 + lr * 20.0 + u * 3.0) * 0.5 + 0.5
    fine = np.sin(across * math.pi * 29.0 + lr * 7.0) * 0.5 + 0.5
    rgb = rgb * (0.84 + 0.16 * strand[:, None] + 0.08 * fine[:, None])
    # round 3: each lock splits into three strands toward its tip (two dark partings): hair, not a leaf
    part_line = np.maximum(np.exp(-((across - 0.34) / 0.07) ** 2), np.exp(-((across + 0.34) / 0.07) ** 2)) * smooth(0.45, 0.8, u)
    rgb = rgb * (1 - 0.45 * part_line[:, None])
    # pale aqua, glowing tips (round 3: less mint)
    tip = smooth(0.65, 1.0, u)[:, None] * 0.45
    is_aur = (is_mane | (np.abs(part - M.TAIL_LOCK) < 0.5))[:, None]
    rosy = smooth(0.5, 0.9, rgb[:, 0:1] / np.maximum(rgb[:, 1:2], 1e-4))
    tipcol = lin(col['teal_pale'])[None] * (1 - rosy) + np.clip(rgb * 1.25 + 0.06, 0, 1) * rosy
    rgb = np.where(is_aur, rgb * (1 - tip) + tipcol * tip, rgb)
    # the bake multiplies 38% of the AO into the colour: brighten where the locks will be most occluded (near the body)
    near = smooth(0.06, 0.0, M.sdf(co.reshape(-1, 3).astype(np.float64)))
    rgb = np.where(is_aur, np.clip(rgb * (1.0 + 0.35 * near)[:, None], 0, 1), rgb)
    # the throat ruff: lavender, lighter toward its tips, matte
    ruff = np.abs(part - M.RUFF) < 0.5
    rgb = np.where(ruff[:, None], (lin(col['light'])[None] * (1 - 0.4 * u[:, None]) + lin(col['pale'])[None] * 0.4 * u[:, None]) * 0.92
                   * (0.88 + 0.16 * lr[:, None]) * (0.9 + 0.1 * strand[:, None]), rgb)
    crown = np.abs(part - M.CROWN) < 0.5
    rgb = np.where(crown[:, None], (lin(col['teal_deep'])[None] * (1 - u[:, None]) + lin(col['teal'])[None] * u[:, None]) * 0.95, rgb)
    # the tail: indigo clumps at the base with star dust, shading to teal, then rose at the end (review round 1:
    # 2-turnaround side and back, 4-details panel 4)
    tl = np.abs(part - M.TAIL_LOCK) < 0.5
    if tl.any():
        tt, th, _r = tail_coords(co.reshape(-1, 3)[tl].astype(np.float64))
        k_teal = smooth(0.3, 0.6, tt)
        k_rose = np.maximum(smooth(0.68, 0.95, tt), smooth(-0.04, -0.14, th) * smooth(0.42, 0.7, tt))
        indigo = lin(C.mix_hex(col['indigo'], col['light'], 0.25))[None] * (0.8 + 0.35 * u[tl])[:, None]
        teal = lin(col['teal_deep'])[None] * (1 - smooth(0.3, 0.9, u[tl]))[:, None] + lin(col['teal'])[None] * smooth(0.3, 0.9, u[tl])[:, None]
        trgb = indigo * (1 - k_teal[:, None]) + teal * k_teal[:, None]
        trgb = trgb * (1 - k_rose[:, None]) + lin(col['rose'])[None] * k_rose[:, None]
        # star dust on the indigo clumps
        idx = np.nonzero(tl)[0]
        dust = ((np.sin(idx * 12.9898) * 43758.5453) % 1.0 > 0.985) & (k_teal < 0.5) & (u[tl] > 0.15) & (u[tl] < 0.85)
        trgb = np.where(dust[:, None], lin(col['star_white'])[None], trgb)
        rgb[tl] = trgb * (0.8 + 0.25 * lr[tl])[:, None]
    star = np.abs(part - M.STAR) < 0.5
    sc = lin(col['tail_star'])[None] * (0.9 + 0.1 * (1 - fan[:, 0:1]))
    rgb = np.where(star[:, None], sc, rgb)
    # round 2: much less gloss on the locks (silky, not plastic)
    rough = np.where(star, 0.4, 0.55 + 0.1 * smooth(0.5, 1.0, u))
    rc = np.stack([np.ones(n), rough, np.where(star, 0.35, 0.08)], axis=1)
    return np.clip(rgb, 0, 1), rc


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.add_attr(ob, 'glow', body_glow(ob))
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'dark', a['dark'])
        S.add_attr(ob, 'shade', a['shade'])
        # round 7: where each star chart shows, by the skin's normal (a lying lock takes the skin's at its root)
        root = S.attr_array(ob, 'root').astype(np.float64)
        nrm = S.attr_array(ob, 'rootn').astype(np.float64) if 'rootn' in ob.data.attributes else S.mesh_arrays(ob)[1]
        for key, val in chart_weights(root, norm(np.asarray(nrm, np.float64).reshape(-1, 3))).items():
            S.add_attr(ob, key, val)
    for ob in fins:
        rgb, rc = fin_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        S.add_attr(ob, 'glow', fin_glow(ob))


# ----------------------------------------------------------------------------- paint (nodes: the crisp details, per pixel)
def _ell(nb, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def _frame(nrm) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = np.array(nrm, float)
    n /= max(np.linalg.norm(n), 1e-9)
    up = np.array((0.0, 0.0, 1.0)) if abs(n[2]) < 0.9 else np.array((0.0, 1.0, 0.0))
    e1 = up - n * (up @ n)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    return e1, e2, n


STAR_REACH = 0.013          # how far out along the skin's normal a star or a line reaches (the lying locks lie over it)
STAR_SCALE = 2.3           # every star's radius × this (review 1: too faint at game distance)


def _map(nb, x, a, b):
    """smoothstep(a, b, x) where a and b may be sockets."""
    n = nb.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nb.put(n.inputs['Value'], x)
    nb.put(n.inputs['From Min'], a)
    nb.put(n.inputs['From Max'], b)
    n.inputs['To Min'].default_value = 0.0
    n.inputs['To Max'].default_value = 1.0
    return n.outputs['Result']


def _group(name: str, inputs: list[tuple[str, str]]):
    """A shader node group with these (name, 'VECTOR' | 'FLOAT') inputs and one float output 'Mask'."""
    from lib.nodes import NB
    g = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    for nm, kind in inputs:
        g.interface.new_socket(name=nm, in_out='INPUT', socket_type='NodeSocketVector' if kind == 'VECTOR' else 'NodeSocketFloat')
    g.interface.new_socket(name='Mask', in_out='OUTPUT', socket_type='NodeSocketFloat')
    nb = NB(g)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')
    return g, nb, gi, go


def star_group():
    """A star's mask (one group, instanced per star): a soft core and, when F = 1, a four-pointed flare in the skin's
    tangent plane (the long arm along E1, up the body). It reaches STAR_REACH out along N so the locks show it too."""
    if 'sh_star' in bpy.data.node_groups:
        return bpy.data.node_groups['sh_star']
    g, nb, gi, go = _group('sh_star', [('Pos', 'VECTOR'), ('C', 'VECTOR'), ('E1', 'VECTOR'), ('E2', 'VECTOR'), ('N', 'VECTOR'),
                                       ('R', 'FLOAT'), ('FL', 'FLOAT'), ('F', 'FLOAT')])
    i = gi.outputs
    q = nb.vmath('SUBTRACT', i['Pos'], i['C'])
    a = nb.vmath('DOT_PRODUCT', q, i['E1'])
    b = nb.vmath('DOT_PRODUCT', q, i['E2'])
    h = nb.vmath('DOT_PRODUCT', q, i['N'])
    dh = nb.math('DIVIDE', h, STAR_REACH)
    d = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', a, i['R']), nb.math('DIVIDE', b, i['R']), dh))
    core = nb.smooth(d, 1.0, 0.35)
    wd = nb.math('MULTIPLY', i['R'], 0.24)
    aa, ab = nb.math('ABSOLUTE', a), nb.math('ABSOLUTE', b)
    arm1 = nb.math('MULTIPLY', _map(nb, ab, wd, 0.0), _map(nb, aa, i['FL'], 0.0))
    arm2 = nb.math('MULTIPLY', _map(nb, aa, wd, 0.0), _map(nb, ab, nb.math('MULTIPLY', i['FL'], 0.7), 0.0))
    arms = nb.math('MULTIPLY', nb.math('MAXIMUM', arm1, arm2), nb.smooth(nb.math('ABSOLUTE', dh), 1.0, 0.5))
    arms = nb.math('MULTIPLY', arms, i['F'])
    nb.link(nb.math('MAXIMUM', core, arms), go.inputs['Mask'])
    return g


def line_group():
    """A faint constellation line from A along D for L, W wide in the tangent plane (across E), reaching out along N."""
    if 'sh_line' in bpy.data.node_groups:
        return bpy.data.node_groups['sh_line']
    g, nb, gi, go = _group('sh_line', [('Pos', 'VECTOR'), ('A', 'VECTOR'), ('D', 'VECTOR'), ('E', 'VECTOR'), ('N', 'VECTOR'),
                                       ('L', 'FLOAT'), ('W', 'FLOAT')])
    i = gi.outputs
    q = nb.vmath('SUBTRACT', i['Pos'], i['A'])
    t = nb.vmath('DOT_PRODUCT', q, i['D'])
    w = nb.vmath('DOT_PRODUCT', q, i['E'])
    h = nb.vmath('DOT_PRODUCT', q, i['N'])
    along = nb.math('MULTIPLY', nb.smooth(t, 0.004, 0.012),
                    _map(nb, t, nb.math('SUBTRACT', i['L'], 0.004), nb.math('SUBTRACT', i['L'], 0.012)))
    across = _map(nb, nb.math('ABSOLUTE', w), i['W'], nb.math('MULTIPLY', i['W'], 0.3))
    out = nb.smooth(nb.math('ABSOLUTE', h), STAR_REACH, STAR_REACH * 0.6)
    nb.link(nb.math('MULTIPLY', nb.math('MULTIPLY', along, across), out), go.inputs['Mask'])
    return g


def _star_inst(nb, grp, pos, st, flare_k: float = 1.0, scale: float = STAR_SCALE):
    x, y, z, nx, ny, nz, r, fl, _gold = st
    e1, e2, n = _frame((nx, ny, nz))
    r = r * scale
    node = nb.new('ShaderNodeGroup')
    node.node_tree = grp
    nb.link(pos, node.inputs['Pos'])
    node.inputs['C'].default_value = (x, y, z)
    node.inputs['E1'].default_value = tuple(e1)
    node.inputs['E2'].default_value = tuple(e2)
    node.inputs['N'].default_value = tuple(n)
    node.inputs['R'].default_value = r
    node.inputs['FL'].default_value = r * (3.4 if fl < 1.5 else 4.8) * flare_k
    node.inputs['F'].default_value = 1.0 if fl > 0.5 else 0.0
    return node.outputs['Mask']


def _line_inst(nb, grp, pos, ln, width: float):
    ax_, ay_, az_, bx, by, bz, nx, ny, nz = ln
    a = np.array((ax_, ay_, az_))
    b = np.array((bx, by, bz))
    n = np.array((nx, ny, nz))
    n /= max(np.linalg.norm(n), 1e-9)
    ab = b - a
    L = float(np.linalg.norm(ab))
    d = ab / max(L, 1e-9)
    e = np.cross(n, d)
    e /= max(np.linalg.norm(e), 1e-9)
    node = nb.new('ShaderNodeGroup')
    node.node_tree = grp
    nb.link(pos, node.inputs['Pos'])
    node.inputs['A'].default_value = tuple(a)
    node.inputs['D'].default_value = tuple(d)
    node.inputs['E'].default_value = tuple(e)
    node.inputs['N'].default_value = tuple(n)
    node.inputs['L'].default_value = L
    node.inputs['W'].default_value = width
    return node.outputs['Mask']


def _speckles(nb, pos):
    """Two scales of tiny dots, thinned by a slow noise so they cluster like a night sky (0..1, before the dark mask)."""
    spk = None
    for scale, rad, amt in ((120.0, 0.085, 0.8),):          # round 8: one sparse scale of dust (two dense ones were frost)
        vo = nb.new('ShaderNodeTexVoronoi')
        vo.feature = 'F1'
        vo.inputs['Scale'].default_value = scale
        vo.inputs['Randomness'].default_value = 1.0
        nb.link(pos, vo.inputs['Vector'])
        dot = nb.math('MULTIPLY', nb.smooth(vo.outputs['Distance'], rad, rad * 0.35), amt)
        spk = dot if spk is None else nb.math('MAXIMUM', spk, dot)
    nz = nb.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 9.0
    nz.inputs['Detail'].default_value = 1.0
    nb.link(pos, nz.inputs['Vector'])
    return nb.math('MULTIPLY', spk, nb.smooth(nz.outputs['Fac'], 0.25, 0.5))


# ----------------------------------------------------------------------------- the star charts (round 7)
def chart_arrays(marks) -> dict[str, np.ndarray]:
    """Each chart as an H × W × 4 array (rows bottom-up, CHART_PX texels a metre): R the white stars, G the gold stars,
    B the constellations' linking lines. A star is a soft dot (solid to 0.35 of its radius), with four tapering arms
    when it is a sparkle (the long pair along the chart's v axis: up the body)."""
    out = {}
    stars = marks.get('chart_stars', [])
    lines = marks.get('chart_lines', [])
    for ci, (nm, _axis, eu, ev, ur, vr, _side, _ymin) in enumerate(CHARTS):
        eu_, ev_ = v3(eu), v3(ev)
        w = int(round((ur[1] - ur[0]) * CHART_PX))
        h = int(round((vr[1] - vr[0]) * CHART_PX))
        arr = np.zeros((h, w, 4), np.float32)
        arr[..., 3] = 1.0

        def px(p, eu_=eu_, ev_=ev_, ur=ur, vr=vr):
            p = np.asarray(p, float)
            return np.array(((float(p @ eu_) - ur[0]) * CHART_PX, (float(p @ ev_) - vr[0]) * CHART_PX))
        for ln in lines:
            if int(ln[6]) != ci:
                continue
            a, b = px(ln[:3]), px(ln[3:6])
            u0, u1 = max(int(min(a[0], b[0])) - 5, 0), min(int(max(a[0], b[0])) + 6, w)
            v0, v1 = max(int(min(a[1], b[1])) - 5, 0), min(int(max(a[1], b[1])) + 6, h)
            if u1 <= u0 or v1 <= v0:
                continue
            du, dv = np.meshgrid(np.arange(u0, u1) + 0.5 - a[0], np.arange(v0, v1) + 0.5 - a[1])
            ab = b - a
            L = max(float(np.hypot(ab[0], ab[1])), 1e-6)
            t = (du * ab[0] + dv * ab[1]) / L
            d = np.abs(du * ab[1] - dv * ab[0]) / L
            m = 0.85 * smooth(4.4, 1.9, d) * smooth(6.0, 15.0, t) * smooth(L - 6.0, L - 15.0, t)      # round 8: wide enough to survive the atlas
            arr[v0:v1, u0:u1, 2] = np.maximum(arr[v0:v1, u0:u1, 2], m)
        for st in stars:
            if int(st[6]) != ci:
                continue
            c = px(st[:3])
            r = st[3] * CHART_PX
            fl = int(st[4])
            arm = r * (3.0 if fl == 1 else 3.6) if fl else 0.0
            half = int(math.ceil(max(r, arm))) + 2
            u0, u1 = max(int(c[0]) - half, 0), min(int(c[0]) + half + 1, w)
            v0, v1 = max(int(c[1]) - half, 0), min(int(c[1]) + half + 1, h)
            if u1 <= u0 or v1 <= v0:
                continue
            du, dv = np.meshgrid(np.arange(u0, u1) + 0.5 - c[0], np.arange(v0, v1) + 0.5 - c[1])
            m = smooth(1.0, 0.35, np.hypot(du, dv) / r)
            if fl:
                wd = max(0.24 * r, 0.9)
                up = smooth(wd, 0.0, np.abs(du)) * smooth(arm, 0.0, np.abs(dv))
                across = smooth(wd, 0.0, np.abs(dv)) * smooth(arm * 0.72, 0.0, np.abs(du))
                m = np.maximum(m, np.maximum(up, across))
            ch = 1 if st[5] > 0.5 else 0
            arr[v0:v1, u0:u1, ch] = np.maximum(arr[v0:v1, u0:u1, ch], m)
        out[nm] = arr
    return out


def chart_images(marks) -> dict:
    """The charts as Blender images (made once per set of marks; non-colour data)."""
    stamp = f"{len(marks.get('chart_stars', []))}:{len(marks.get('chart_lines', []))}:{CHART_PX}"
    out, arrs = {}, None
    for nm, *_rest in CHARTS:
        name = f'starhowl_chart_{nm}'
        img = bpy.data.images.get(name)
        if img is None or img.get('stamp') != stamp:
            if img is not None:
                bpy.data.images.remove(img)
            if arrs is None:
                arrs = chart_arrays(marks)
            a = arrs[nm]
            img = bpy.data.images.new(name, a.shape[1], a.shape[0], alpha=True, float_buffer=False)
            img.colorspace_settings.name = 'Non-Color'
            img.pixels.foreach_set(np.ascontiguousarray(a, dtype=np.float32).ravel())
            img['stamp'] = stamp
            try:
                img.pack()            # it lives in the .blend if a stage saves it
            except RuntimeError:
                pass
        out[nm] = img
    return out


def _chart_masks(nb, pos, marks) -> dict:
    """The charts' masks per pixel ('white', 'gold', 'lines'): each chart sampled at the surface's projected position,
    shown where the skin faces it (the sources' `chart_*` weights) and only on the dark coat."""
    if not marks or not marks.get('chart_stars'):
        return {}
    imgs = chart_images(marks)
    dark = nb.attribute('dark').outputs['Fac']
    ws = nb.attribute('chart_s').outputs['Fac']
    wd = nb.attribute('chart_d').outputs['Fac']
    wt = {'L': nb.math('MAXIMUM', ws, 0.0), 'R': nb.math('MAXIMUM', nb.math('MULTIPLY', ws, -1.0), 0.0),
          'UL': nb.math('MAXIMUM', wd, 0.0), 'UR': nb.math('MAXIMUM', nb.math('MULTIPLY', wd, -1.0), 0.0),
          'T': nb.attribute('chart_t').outputs['Fac'], 'B': nb.attribute('chart_b').outputs['Fac']}
    out = {}
    for nm, _axis, eu, ev, ur, vr, _side, _ymin in CHARTS:
        u = nb.math('DIVIDE', nb.math('SUBTRACT', nb.vmath('DOT_PRODUCT', pos, tuple(eu)), ur[0]), ur[1] - ur[0])
        v = nb.math('DIVIDE', nb.math('SUBTRACT', nb.vmath('DOT_PRODUCT', pos, tuple(ev)), vr[0]), vr[1] - vr[0])
        tex = nb.new('ShaderNodeTexImage', image=imgs[nm])
        tex.extension = 'CLIP'
        tex.interpolation = 'Linear'
        nb.link(nb.comb(u, v, 0.0), tex.inputs['Vector'])
        r, g, b = nb.sep(tex.outputs['Color'])
        k = nb.math('MULTIPLY', wt[nm], dark)
        for key, sock in (('white', r), ('gold', g), ('lines', b)):
            e = nb.math('MULTIPLY', sock, k)
            out[key] = e if key not in out else nb.math('MAXIMUM', out[key], e)
    return out


def _mark_masks(nb, pos, marks) -> dict:
    """The marks' masks per pixel: 'lines' (constellation lines), 'white' and 'gold' (the stars), 'brow' (the cluster):
    the few node marks and (round 7) the star charts."""
    out = dict(_chart_masks(nb, pos, marks))
    if not marks:
        return out
    from lib import marks as MK
    sg, lg = star_group(), line_group()
    # round 6: each kind combined as a balanced MAXIMUM tree (lib.marks.union), not a chain hundreds deep (Cycles ran
    # out of SVM stack space on the chain and baked the body black)
    lines = [_line_inst(nb, lg, pos, ln, 0.0045) for ln in marks.get('lines', [])]     # rounds 5–6: bolder linking lines
    if lines:
        e = MK.union(nb, lines)
        out['lines'] = e if 'lines' not in out else nb.math('MAXIMUM', out['lines'], e)
    for gold, key in ((0.0, 'white'), (1.0, 'gold')):
        stars = [_star_inst(nb, sg, pos, st) for st in marks.get('stars', []) if st[8] == gold]
        if stars:
            e = MK.union(nb, stars)
            out[key] = e if key not in out else nb.math('MAXIMUM', out[key], e)
    brow = [_star_inst(nb, sg, pos, st, flare_k=0.76, scale=1.1) for st in marks.get('brow', [])]
    if brow:
        out['brow'] = MK.union(nb, brow)
    return out


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the painted attribute, the lock shading, then per pixel: fine speckles over the dark fur, the
    constellations (stars and faint lines), the brow cluster, the brows, the nose, the smile, the eye-liner and the
    closed lid."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 0.5)
    dark = nb.attribute('dark').outputs['Fac']
    c = nb.attribute(attr).outputs['Color']
    shade = nb.attribute('shade').outputs['Fac']
    c = nb.mix(1.0, c, nb.comb(shade, shade, shade), blend='MULTIPLY')
    spk = nb.math('MULTIPLY', _speckles(nb, pos), dark)
    c = nb.mix(nb.math('MULTIPLY', spk, 0.6), c, nb.rgb(C.lin('#D4DEFF')))
    mk = _mark_masks(nb, pos, marks)
    # the lines first (faint), then the stars over them
    if 'lines' in mk:
        c = nb.mix(nb.math('MULTIPLY', mk['lines'], 0.85), c, nb.rgb(C.lin(col['line'])))
    if 'white' in mk:
        c = nb.mix(mk['white'], c, nb.rgb(C.lin(col['star_white'])))
    if 'gold' in mk:
        c = nb.mix(mk['gold'], c, nb.rgb(C.lin(col['star_gold'])))
    if 'brow' in mk:
        c = nb.mix(mk['brow'], c, nb.rgb(C.lin('#FFF1CC')))
    # round 7 (1-hero, 3-faces neutral): the brows are short DARK strokes above a lavender upper lid (rounds 2–6 had
    # them pale on dark fur, the reverse of the pictures): thicker and a little lower at the inner end, thinner and
    # higher toward the outer end; paint only (no ridge)
    px, py_, pz = nb.sep(pos)
    front = nb.smooth(py_, -0.44, -0.47)
    brow = None
    for s in (1, -1):
        cc = EYE_C[s]
        # an arched stroke about an eye wide, level across the brow (the eye slants up under it): thick at the inner
        # end, tapering to a point at the outer; drawn per pixel as the distance to a two-segment line in the head's
        # front view (x across, z up)
        u = nb.math('MULTIPLY', nb.math('SUBTRACT', px, cc.x), float(s))
        v = nb.math('SUBTRACT', pz, cc.z)
        e = _stroke_px(nb, u, v, BROW_LINE)
        brow = e if brow is None else nb.math('MAXIMUM', brow, e)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', brow, front), 0.95), c, nb.rgb(C.lin(BROW_HEX)))
    w = nb.math('MULTIPLY', nb.math('MINIMUM', nb.math('MAXIMUM', nb.math('DIVIDE', nb.math('SUBTRACT', pz, NOSE_C.z - 0.017), 0.03), 0.3), 1.0), 0.026)
    tri = _map(nb, nb.math('ABSOLUTE', px), w, nb.math('SUBTRACT', w, 0.004))
    c = nb.mix(nb.math('MULTIPLY', _ell(nb, pos, tuple(NOSE_C), (0.026, 0.021, 0.018), 0.08), tri), c, nb.rgb(C.lin(NOSE_HEX)))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.7, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(MOUTH_HEX)))
    lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
    # round 8: the closed lid keeps the face's own tone under one lash line (a lid-coloured dome inside the liner read
    # as goggles in the blink)
    c = nb.mix(nb.math('MULTIPLY', lid, 0.0), c, nb.rgb(C.lin(col['lid'])))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin(LINER_HEX)))
    # round 7: the eye-liner per pixel (the per-vertex `liner` attribute drew a soft smudge round the eye)
    c = nb.mix(_liner_px(nb, pos), c, nb.rgb(C.lin(LINER_HEX)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# the brow stroke's centre line from the inner end to the outer: (across from the eye's centre toward the outer side,
# up from the eye's centre, half thickness), metres (3-faces neutral: about an eye wide, 7 mm thick, a point at the end)
BROW_LINE = [(-0.017, 0.0395, 0.0042), (-0.003, 0.0445, 0.0042), (0.014, 0.0445, 0.0036), (0.034, 0.0375, 0.0008)]


def _stroke_px(nb, u, v, line):
    """A tapering stroke along a polyline of (u, v, half thickness) points, as a 0..1 mask of the sockets u and v."""
    out = None
    for (au, av, aw), (bu, bv, bw) in zip(line[:-1], line[1:]):
        du, dv = bu - au, bv - av
        eu, ev = nb.math('SUBTRACT', u, au), nb.math('SUBTRACT', v, av)
        t = nb.math('DIVIDE', nb.math('ADD', nb.math('MULTIPLY', eu, du), nb.math('MULTIPLY', ev, dv)), du * du + dv * dv)
        t = nb.math('MINIMUM', nb.math('MAXIMUM', t, 0.0), 1.0)
        d = nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', eu, nb.math('MULTIPLY', t, du)),
                                       nb.math('SUBTRACT', ev, nb.math('MULTIPLY', t, dv)), 0.0))
        w = nb.math('ADD', aw, nb.math('MULTIPLY', t, bw - aw))
        e = _map(nb, d, nb.math('ADD', w, 0.0012), nb.math('MULTIPLY', w, 0.8))
        out = e if out is None else nb.math('MAXIMUM', out, e)
    return out


def _liner_px(nb, pos):
    """The dark eye-liner on the skin round each lens, per pixel (1-hero, 3-faces neutral, 4-details panel 2): a crisp
    band along the lens's rim, bold over the top and thicker toward the outer corner, thin below, and a tapering wing
    that carries the upper lid's line out and up past the outer corner."""
    out = None
    for s in (1, -1):
        c0, xax, yax, look = eye_frame(s)
        q = nb.vmath('SUBTRACT', pos, tuple(c0))
        xe = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', q, tuple(xax)), EYE_R * EYE_W)       # in half-widths
        ye = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', q, tuple(yax)), EYE_R * EYE_H)       # in upper half-heights
        front = nb.smooth(nb.vmath('DOT_PRODUCT', q, tuple(look)), -0.035, -0.02)
        xc = nb.math('MINIMUM', nb.math('MAXIMUM', xe, -1.0), 1.0)
        pinch = nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', nb.math('MULTIPLY', xc, xc), EYE_PINCH))
        low = nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', nb.math('LESS_THAN', ye, 0.0), 1.0 - EYE_LOW))
        yn = nb.math('DIVIDE', ye, nb.math('MULTIPLY', pinch, low))
        r = nb.vmath('LENGTH', nb.comb(xe, yn, 0.0))
        top = nb.smooth(ye, -0.3, 0.3)
        outer = nb.smooth(nb.math('MULTIPLY', xe, float(s)), 0.2, 0.95)
        wdt = nb.math('ADD', nb.math('ADD', 0.025, nb.math('MULTIPLY', top, 0.05)), nb.math('MULTIPLY', nb.math('MULTIPLY', outer, top), 0.05))
        ring = nb.math('MULTIPLY', nb.smooth(r, 0.93, 0.985),
                       _map(nb, r, nb.math('ADD', 1.03, wdt), nb.math('ADD', 0.99, wdt)))
        ring = nb.math('MULTIPLY', ring, nb.math('MULTIPLY', top, 0.8))          # round 8: over the top only (a full ring was a goggle rim in the blink)
        # the wing: the distance to the stroke a → b (in half-widths, upper half-heights), tapering to its tip
        ax_, ay_ = 0.92 * s, 0.08
        bx_, by_ = 1.62 * s, 0.48
        abx, aby = bx_ - ax_, by_ - ay_
        ex, ey = nb.math('SUBTRACT', xe, ax_), nb.math('SUBTRACT', ye, ay_)
        t = nb.math('DIVIDE', nb.math('ADD', nb.math('MULTIPLY', ex, abx), nb.math('MULTIPLY', ey, aby)), abx * abx + aby * aby)
        t = nb.math('MINIMUM', nb.math('MAXIMUM', t, 0.0), 1.0)
        d = nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ex, nb.math('MULTIPLY', t, abx)),
                                       nb.math('SUBTRACT', ey, nb.math('MULTIPLY', t, aby)), 0.0))
        wd = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', t, 0.78)), 0.21)
        wing = _map(nb, d, wd, nb.math('MULTIPLY', wd, 0.55))
        e = nb.math('MULTIPLY', nb.math('MAXIMUM', ring, wing), front)
        out = e if out is None else nb.math('MAXIMUM', out, e)
    return out


# ----------------------------------------------------------------------------- the glow (0..1 per pixel; the runtime's
# emissive = base × glow × strength, allowed to bloom, with a gentle twinkle). The hook names follow RECIPE.md once the
# pipeline publishes them; these build the masks.
GLOW = {'strength': 1.0, 'tint': None}
# modest coverage, so the bloom reads as glints and not a blur
GLOW_PARTS = {'star': 0.95, 'brow': 1.0, 'line': 0.7, 'speckle': 0.1, 'mane_tip': 1.0, 'lock': 0.04, 'tail_star': 1.0, 'iris': 0.6,
              'mane_rim': 0.55}


def _glow_marks(nb, pos, marks):
    """The body's per-pixel glow: the stars' cores and flares, the brow cluster, the lines faintly, the star dust a
    little, all on the dark fur only (the face, the nose and the ears' hollows never glow)."""
    dark = nb.attribute('dark').outputs['Fac']
    g = nb.math('MULTIPLY', nb.math('MULTIPLY', _speckles(nb, pos), dark), GLOW_PARTS['speckle'])
    mk = _mark_masks(nb, pos, marks)
    for key, k in (('lines', GLOW_PARTS['line']), ('white', GLOW_PARTS['star']), ('gold', GLOW_PARTS['star']), ('brow', GLOW_PARTS['brow'])):
        if key in mk:
            g = nb.math('MAXIMUM', g, nb.math('MULTIPLY', mk[key], k))
    return g


def glow_material(name: str, marks) -> bpy.types.Material:
    """The body sources' glow-pass material (RECIPE.md): max(the 'glow' attribute, the marks), as grey emission."""
    try:
        from lib import marks as MK
        if hasattr(MK, 'glow_material'):
            return MK.glow_material(name, lambda nb, pos: _glow_marks(nb, pos, marks))
    except ImportError:
        pass
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    g = nb.math('MAXIMUM', nb.attribute('glow').outputs['Fac'], _glow_marks(nb, pos, marks))
    em = nb.new('ShaderNodeEmission')
    nb.link(nb.comb(g, g, g), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def eye_glow(eyeuv: np.ndarray, s: int = 1) -> np.ndarray:
    """Per vertex of a lens: the pale outer iris glows a little ("glowing pale eyes"); the pupil and the white don't."""
    w = eye_world(eyeuv)
    ri = np.hypot(w[:, 0] - s * IRIS_OUT, w[:, 1] - IRIS_DY) / IRIS_R
    return smooth(0.27, 0.42, ri) * smooth(0.98, 0.9, ri) * GLOW_PARTS['iris']


def body_glow_material(name: str, marks) -> bpy.types.Material:   # (round 1's draft; glow_material is the hook)
    """The body's glow mask (grey emission): the stars' cores and flares, the brow cluster, the constellation lines
    faintly, the speckles a little (all on the dark fur only; the face, the nose and the ears' hollows never glow)."""
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    dark = nb.attribute('dark').outputs['Fac']
    g = nb.math('MULTIPLY', nb.math('MULTIPLY', _speckles(nb, pos), dark), GLOW_PARTS['speckle'])
    mk = _mark_masks(nb, pos, marks)
    for key, k in (('lines', GLOW_PARTS['line']), ('white', GLOW_PARTS['star']), ('gold', GLOW_PARTS['star']), ('brow', GLOW_PARTS['brow'])):
        if key in mk:
            g = nb.math('MAXIMUM', g, nb.math('MULTIPLY', mk[key], k))
    em = nb.new('ShaderNodeEmission')
    nb.link(nb.comb(g, g, g), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def body_glow(ob: bpy.types.Object) -> np.ndarray:
    """Round 4: the softly glowing tips of the aurora (the mane's and the plume's lying locks, toward their tips; the
    skin under them and every other lock 0)."""
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    t = _TONE.get(ob.name)
    if t is None:
        root = S.attr_array(ob, 'root').astype(np.float64)
        t = tone_masks(root, zones(root))
    aur = np.maximum(t['mane'], t['aurora'])
    # round 5: the lock tips glow fully, and the skin itself glows softly where the collar turns rose along its lower
    # rim (the cards there can't glow, so the glow comes from under them)
    co = np.empty(len(kind) * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    zz = co.reshape(-1, 3)[:, 2].astype(np.float64)
    rim = t['mane'] * t['mane_rose'] * smooth(0.7, 0.56, zz) * GLOW_PARTS['mane_rim']
    rim = np.maximum(rim, t['aurora'] * t['rose'] * 0.35)
    rim = np.maximum(rim, t['mane'] * t['lock_tip'] * 1.0)          # the sculpted locks' tips glow (round 8: no cards over them)
    return np.where(kind > 0.5, aur * smooth(0.6, 1.0, tpos) * GLOW_PARTS['mane_tip'], rim)


def fin_glow(ob: bpy.types.Object) -> np.ndarray:
    """Per vertex of a fin source: the tail star glows fully; the mane's and the tail's locks glow softly toward their
    tips (the card: "softly glowing at the tips"), barely at the roots."""
    fan = S.attr_array(ob, 'fan').astype(np.float64)
    part = S.attr_array(ob, 'fin_part')
    u = fan[:, 0]
    g = GLOW_PARTS['lock'] + (GLOW_PARTS['mane_tip'] - GLOW_PARTS['lock']) * smooth(0.62, 1.0, u)
    g = np.where(np.abs(part - M.RUFF) < 0.5, 0.0, g)
    tl = np.abs(part - M.TAIL_LOCK) < 0.5
    if tl.any():
        co = np.empty(len(u) * 3, np.float32)
        ob.data.vertices.foreach_get('co', co)
        tt, _th, _r = tail_coords(co.reshape(-1, 3)[tl].astype(np.float64))
        g[tl] = g[tl] * smooth(0.28, 0.6, tt)
    return np.where(np.abs(part - M.STAR) < 0.5, GLOW_PARTS['tail_star'], g)


def eye_glow_material(name: str) -> bpy.types.Material:
    """The eyes: the pale outer iris glows a little ("glowing pale eyes"); the pupil, the white and the lash don't."""
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    x, y, _z = nb.sep(e)
    xi = nb.math('MULTIPLY', x, EYE_W / EYE_H * 0.78)     # a little oval: the iris fills the almond, white only at the corners
    yi = nb.math('SUBTRACT', y, 0.04)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(xi, yi, 0.0)), 0.9)
    ring = nb.math('MULTIPLY', nb.smooth(ri, 0.28, 0.45), nb.smooth(ri, 0.97, 0.9))
    g = nb.math('MULTIPLY', ring, GLOW_PARTS['iris'])
    em = nb.new('ShaderNodeEmission')
    nb.link(nb.comb(g, g, g), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the fins
def build_fins(high: bool, quick: bool) -> list[bpy.types.Object]:
    """The aurora mane (fin_part 10), the tail's aurora locks (20) and the tail star (30)."""
    return M.build(high, quick)


# ----------------------------------------------------------------------------- the rig (plans/quadruped.py)
MANES = [
    # round 6: lower caps (the collar cards flared into a ragged halo in hit)
    {'name': 'maneB', 'parent': 'neck', 'cap': 2.0, 'counter': 0.6, 'points': [(0.0, -0.33, 1.06), (0.0, -0.2, 0.94), (0.0, -0.07, 0.84), (0.0, 0.04, 0.78)]},
    {'name': 'maneL', 'parent': 'neck', 'cap': 2.5, 'counter': 0.5, 'points': [(0.12, -0.4, 0.97), (0.22, -0.33, 0.84), (0.27, -0.26, 0.7), (0.29, -0.2, 0.56)]},
    {'name': 'maneR', 'parent': 'neck', 'cap': 2.5, 'counter': 0.5, 'points': [(-0.12, -0.4, 0.97), (-0.22, -0.33, 0.84), (-0.27, -0.26, 0.7), (-0.29, -0.2, 0.56)]},
]


def rig_p() -> dict:
    ed = E.tip(1) - EAR_ROOT[1]
    pts = [Vector(p) for p in TAIL_PTS]
    tl = sum((b - a).length for a, b in zip(pts[:-1], pts[1:]))
    return {
        'hip': (0.0, 0.38, 0.6),
        'chest': (0.0, -0.2, 0.66),
        'head_c': tuple(HEAD_C),
        'head_r': 0.12,
        'ear_base': tuple(EAR_ROOT[1]),
        'ear_dir': tuple(ed.normalized()),
        'ear_len': ed.length,
        'tail_base': TAIL_PTS[0],
        'tail_dir': tuple((pts[-1] - pts[0]).normalized()),
        'tail_len': tl,
        'tail_bones': 4,
        'tail_points': TAIL_PTS,
        'legs': {leg: (lx, ly, 0.55 if leg[0] == 'F' else 0.56) for leg, (lx, ly) in LEGS.items()},
        'knee_back': 0.04,
        'ankle_z': 0.045,
        'foot_len': 0.12,
        'leg_radius': 0.09,
        'stride': 0.24,
        'manes': MANES,
        # round 2: a digitigrade hind leg matching the modelled stifle, raised hock and paw (shares of the hip's height)
        'hocks': {'knee': (-0.2, -0.32), 'hock': (0.18, -0.64), 'paw': (0.0, -0.95)},
        # the jaw hinges at the mouth's corner and runs along the lower jaw to the chin's tip (the long muzzle)
        # round 6: the hinge further back (a longer lever: the chin drops more for the plan's bite angle)
        'jaw': {'head': (0.0, -0.5, 0.96), 'tail': (0.0, -0.685, 0.945)},
    }


TAIL_BONES = [f'tail.{k}' for k in range(1, 5)]


def ear_weights(u: np.ndarray) -> dict[str, np.ndarray]:
    """head → ear.1 → ear.2 up the ear: the lower ear stays with the head, the upper swings."""
    w2 = smooth(0.4, 0.85, u)
    w1 = (1 - w2) * smooth(0.02, 0.3, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    z = zones(co)
    out = []
    for s, tag in ((1, 'L'), (-1, 'R')):
        on = z['ear'] & (np.sign(co[:, 0]) == s)
        if on.any():
            w = ear_weights(z['ear_u'][on])
            out.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    tail = z['tail']
    if tail.any():
        out.append((tail, U.chain_weights(co[tail], TAIL_PTS, TAIL_BONES, 'hips')))
    # round 4: the mane mass sways with the mane chains (more toward its outside), its roots stay with the neck and head
    mm = z['mane'] | z['ruff']
    if mm.any():
        p = co[mm]
        ax_, up_, side_ = M.neck_frame()
        rel = p - M.NECK_A
        th_ = np.arctan2(rel @ side_, rel @ up_)
        sector = {'maneB': np.maximum(np.cos(th_), 0) ** 2, 'maneL': np.maximum(np.sin(th_), 0) ** 2, 'maneR': np.maximum(-np.sin(th_), 0) ** 2}
        tot = np.maximum(sum(sector.values()), 1e-6)
        a = smooth(0.09, 0.2, neck_dist(p)) * 0.6 * ~z['ruff'][mm] * ~z['crown_in'][mm]
        head_k = smooth(0.93, 1.03, p[:, 2]) * smooth(-0.3, -0.38, p[:, 1])
        head_k = np.where(z['crown_in'][mm], 1.0, head_k)
        chest_k = smooth(0.74, 0.6, p[:, 2]) * 0.5
        w: dict = {'head': (1 - a) * head_k, 'chest': (1 - a) * (1 - head_k) * chest_k,
                   'neck': (1 - a) * (1 - head_k) * (1 - chest_k)}
        for ch in MANES:
            cw = U.chain_weights(p, ch['points'], [f"{ch['name']}.{k}" for k in range(1, len(ch['points']))], ch['parent'])
            for b, v in cw.items():
                w[b] = w.get(b, 0.0) + v * (sector[ch['name']] / tot) * a
        out.append((mm, w))
    # the lower jaw: the skin under the lip line, from the mouth's corner forward, rides the jaw bone
    ys = np.array([q[0] for q in SMILE_SIDE])
    zs = np.array([q[1] for q in SMILE_SIDE])
    y, zz = co[:, 1], co[:, 2]
    lip = np.interp(y, ys, zs)
    # round 5 (review: the jaws stay shut in strike): the whole lower jaw from the hinge forward rides the jaw bone
    w = (smooth(-0.49, -0.525, y) * smooth(lip + 0.0015, lip - 0.004, zz) * (np.abs(co[:, 0]) < 0.065) * (zz > 0.87)
         * z['head'])
    jm = w > 0.01
    if jm.any():
        out.append((jm, {'jaw': w[jm], 'head': 1.0 - w[jm]}))
    return out


def _mane_root_weights(layer: np.ndarray) -> dict[str, np.ndarray]:
    """Where a mane lock's root sits on the skin: the top rings on the head and the neck, the middle on the neck, the
    lowest on the chest (the locks' roots never leave the skin when the head turns)."""
    head = smooth(1.6, 0.0, layer) * 0.7
    chest = smooth(3.5, 5.0, layer) * 0.6
    return {'head': head, 'neck': 1 - head - chest, 'chest': chest}


def fin_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    part = attr('fin_part')
    fan = attr('fan')
    out = []
    mane = np.abs(part - M.MANE) < 0.5
    if mane.any():
        p = co[mane]
        u = fan[mane, 0]
        th = fan[mane, 1] * math.pi
        layer = fan[mane, 2]
        sector = {'maneB': np.maximum(np.cos(th), 0) ** 2, 'maneL': np.maximum(np.sin(th), 0) ** 2, 'maneR': np.maximum(-np.sin(th), 0) ** 2}
        tot = np.maximum(sum(sector.values()), 1e-6)
        sector = {k: v / tot for k, v in sector.items()}
        a = smooth(0.06, 0.4, u)
        w: dict[str, np.ndarray] = {}

        def add(bone, val):
            w[bone] = w.get(bone, 0.0) + val
        for bone, val in _mane_root_weights(layer).items():
            add(bone, val * (1 - a))
        for ch in MANES:
            cw = U.chain_weights(p, ch['points'], [f'{ch["name"]}.{k}' for k in range(1, len(ch['points']))], ch['parent'])
            for bone, val in cw.items():
                add(bone, val * sector[ch['name']] * a)
        out.append((mane, {b: np.asarray(v, float) * np.ones(int(mane.sum())) for b, v in w.items() if b in names}))
    crown = np.abs(part - M.CROWN) < 0.5
    if crown.any():
        out.append(U.rigid(crown, 'head'))
    ruff = np.abs(part - M.RUFF) < 0.5
    if ruff.any():
        rw = _mane_root_weights(fan[ruff, 2])
        out.append((ruff, {b: np.asarray(v, float) for b, v in rw.items()}))
    tl = np.abs(part - M.TAIL_LOCK) < 0.5
    if tl.any():
        out.append((tl, U.chain_weights(co[tl], TAIL_PTS, TAIL_BONES, 'hips')))
    st = np.abs(part - M.STAR) < 0.5
    if st.any():
        out.append(U.rigid(st, TAIL_BONES[-1]))
    return out


# round 3: the jaw moves the lower jaw's skin (the pounce bites, jaw open about 28°); the eyes' bones never move skin
# round 5: the jaw's automatic heat weights are merged into the head first (they covered the whole muzzle, z up to
# 1.05, so the upper jaw turned with the bite and it read as a head dip); body_weight_regions then gives only the
# lower jaw back to `jaw`
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')

# the big poses: the ears stay up, the mane and the tail sway rather than fling
# round 2 (review: the locks stood up like quills in strike and fanned out like a pincushion in ko): the mane only sways
_M = ('maneB', 'maneL', 'maneR')
CLIP_CALM = {
    '*': {'ear': 0.6, **{m: 0.4 for m in _M}},
    'ko': {'ear': 0.15, 'tail': 0.5, **{m: 0.08 for m in _M}},
    'hit_heavy': {'ear': 0.3, 'tail': 0.6, **{m: 0.25 for m in _M}},
    'hit': {'ear': 0.5, **{m: 0.15 for m in _M}},
    'strike': {'ear': 0.35, **{m: 0.2 for m in _M}},
    'win': {'ear': 0.4, 'tail': 0.7, **{m: 0.35 for m in _M}},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the sky-blue iris, pupil, catchlights and the upper lash band '
             'baked into the atlas; the dark brow strokes, the eye-liner wing, the brow star cluster, the nose and the smile '
             'are baked into the body. No face sheet and no morphs: expressions in clips\' `faces` are hints only. Blinking '
             'scales the blink bones (play `blink` over any clip): each lens squashes onto the closed lid\'s lash line and '
             'sinks into the head, showing the closed lid sculpted and painted under it. The mane\'s locks and the plume\'s '
             'clumps are sculpted into the body under hair cards; the coat\'s stars and constellations are baked into the '
             'atlas and its glow mask; the tail star is a fin (lo_fins) and glows with its own colour.')

REVIEW = {
    'centre': (0.0, 0.26, 0.62),
    'size': 2.0,
    'head': ((0.0, -0.5, 1.05), 0.6),
}
