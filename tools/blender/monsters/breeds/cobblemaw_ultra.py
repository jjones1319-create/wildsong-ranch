"""Cobblemaw at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9; RECIPE.md): the recipe for `tools/blender/monsters/build_ultra.py`.

A big, slow, heavy bear-like creature on four thick legs, grumpy-looking but gentle (chatgpt/monsters/03-cobblemaw; the
card decides the parts, the hero the shapes, 2-turnaround the measurements, CONTENT §2.2 #3 the colours):
  - a bulky, low body with broad shoulders and a heavy head, a shoulder hump right behind the head;
  - rounded cobblestones over the top of the head, the neck, the shoulders, the back, the flanks, the rump and the
    short stubby tail, like a cobbled path, with soft green moss in every groove (hard plates displaced into the skin:
    `U.plate_layout` + `U.plate_field`, on the high source and, at 0.85, on the low body so they reach the silhouette;
    the moss is a fuzzy mound in the grooves);
  - a matte, stone-grey hide with a fine grain and a crack network like weathered rock; a lighter stone jaw, throat,
    chest and belly;
  - the face: a wide, cave-like lower jaw (an underbite) with two short stubby ivory tusks poking up from it (rigid
    props on `prop.tusks`), a big dark nose on a short snout, small deep-set amber eyes under heavy stone brows, a wide
    closed smile; small round cupped ears;
  - thick legs on big flat feet with three blunt, glossy, pebble-like claws each.
No fur, no tuft: the detail is carved, baked and painted; one layer of short curly cards makes the moss's tufts.

Size: about 1.5 × Puddlepup (PROMPTS.md): HEIGHT_UNITS 225, so the model stands about 1.48 m tall to the top of the
cobbles on its head and hump. Metres; the monster faces −Y, Z is up, +X is its left. Palette: CONTENT §2.2 #3
(#6E7486 / #8E94A4 / #7FAF5A / #F2B544); Granite Cobblemaw: src/art/monster/variants.ts (#8E8E96 / #C9C9CF / #4A4A52
seams where the moss was / #F2B544), polished speckled granite plates.
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
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, v3
from monsters.breeds import cobblemaw_stone as K

ID = 'cobblemaw'
LOOK = 'cobblemaw-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 225

PALETTE = {'body': '#6E7486', 'belly': '#8E94A4', 'accent': '#7FAF5A', 'eye': '#F2B544'}
# Granite: polished, speckled granite plates with a soft sheen, dark grey stone seams where the moss was (variant
# picture); the eyes, the tusks, the claws and the nose keep their colours
VARIANTS = {
    'granite-cobblemaw': {'body': '#8E8E96', 'belly': '#C9C9CF', 'accent': '#4A4A52', 'eye': '#F2B544', 'granite': True},
}
# round 4: Granite bakes its own roughness and coat (rough_granite, written by paint_sources): polished plates
VARIANT_ORM = {'granite': {}}
# round 4: Granite is bare polished stone (the variant picture has no moss): its look hides the moss cards
VARIANT_CARDS_OFF = {'granite'}

# colours CONTENT has no hex for (the card's parts; the pictures show where they go)
NOSE_HEX = '#3B3F47'             # round 3: a dark slate pad, matte (round 2 read as a glossy black ball)
MOUTH_HEX = '#2B262C'
EAR_IN_HEX = '#6B5254'           # the ears' cupped inside: a dusky mauve-brown (1-hero)
CLAW_HEX = '#6E5B44'             # the claws: glossy warm taupe pebbles (4-details panel 3, its swatch)
TUSK_HEX = ('#EDE2C6', '#CDB98F', '#F7F0DE', '#BFA67A')     # ivory, root, tip, growth rings
LICHEN_PALE = '#B9BDB3'           # round 2: crusty white patches, small and crisp (4-details panel 5)
LICHEN_ORANGE = '#C98F35'
LASH_HEX = '#26232A'

# no cards, no tuft: the strip is not needed (RECIPE.md "Coats without fur")
# round 2: the moss's tufts are one layer of short curly cards in the gaps (the wool tiles: curly clumps), so the atlas
# keeps its strip of card tiles; CARD_SHADE darkens the colour they take from the moss under their roots
CARD_LAYERS = 1
CARD_STYLE = 'wool'
CARD_COLOUR_FROM = 'paint'       # round 5: each tuft the moss paint at its root (no grey or brown strays off a stone)
CARD_SHADE = 1.0                 # round 3: the tufts keep the moss's green (0.74 sank them to a dark lawn)
# the game applies body normals at 0.6 by default; the stone facets, chips and hairline cracks need about full strength
NORMAL_SCALE = 1.1
BODY_SHEEN = 0                   # round 5: stone, not felt (no fur sheen or rim halo on the body)
BODY_TRIS = 64000                       # the cobbles' silhouette (Puddlepup 46k for a smooth pup)
# the low body and the weight proxy at 9 mm voxels (the default 5.5 mm): on this big body the proxy, collapsed from
# ~860k to 24k triangles, defeated Blender's heat solve (every bone empty, distance weights instead; 7.5 mm fails too,
# 9 mm and coarser solve). The low body is collapsed to BODY_TRIS anyway, so the silhouette loses nothing it keeps.
VOXELS = {'lo': 0.009}
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_props': 1.0}
UV_SMOOTH = 70                          # the cobbled back unwraps into far fewer, larger islands (Nimbusheep's lesson)


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def colours(pal: dict) -> dict:
    """Every derived colour of a palette (the base or a variant). Darks stay in the palette's blue-grey hue (never a
    neutral grey or a green-grey: the batch-1 reviews)."""
    hide, light, moss = pal['body'], pal['belly'], pal['accent']
    granite = bool(pal.get('granite'))
    out = {
        'hide': hide,
        'hide_dark': C.shade_hex(hide, 0.66, cool=0.025),
        'hide_lift': C.mix_hex(hide, light, 0.35),
        'light': light,
        'light_dark': C.shade_hex(light, 0.78, cool=0.02),
        'nose': NOSE_HEX,
        'mouth': MOUTH_HEX,
        'ear_in': EAR_IN_HEX,
        'claw': CLAW_HEX,
        'claw_tip': C.mix_hex(CLAW_HEX, '#B4AD9E', 0.4),
        'lash': LASH_HEX,
    }
    if granite:
        out.update({
            'stone': C.shade_hex(hide, 0.72),            # round 5: darker (the back view blew to near white)
            'stone_dark': C.shade_hex(hide, 0.72, cool=0.02),
            'stone_top': C.mix_hex(hide, '#B4B4BA', 0.3),
            # the seams: one dark grout tone (the moss strands' relief stays in the shared normal map; flat colour keeps
            # it reading as gritty stone, not bristles)
            # round 3: the seams (and the cards over them) a mid-dark grey, so the cards read as thin seams, not soot
            # round 4: the picture's thin dark seams (the cards over them can only be hidden by a per-variant card switch)
            'moss': C.mix_hex(moss, hide, 0.3), 'moss_deep': C.mix_hex(moss, hide, 0.15), 'moss_tip': C.mix_hex(moss, hide, 0.4),
            'lichen_pale': None, 'lichen_orange': None,
        })
    else:
        out.update({
            # the cobbles: a mid stone grey a little lighter and warmer than the hide (1-hero), varied per stone
            # round 5: a mid warm grey a little lighter than the hide (1-hero ~#7E766F lit); it read as charcoal
            'stone': '#85827D',              # final: mid grey (it read as khaki loaves)
            'stone_dark': '#5C5A57',
            'stone_top': '#A09D98',
            # moss: green all the way down (deep green in the grooves, yellow-green tips), never grey
            # round 3: the CONTENT green, dark only at the roots, yellow-green tips (~#A8BF60; 4-details panel 5)
            'moss': moss, 'moss_deep': C.mix_hex(moss, '#2E4A1E', 0.45), 'moss_tip': C.mix_hex(moss, '#BCC860', 0.85),   # round 4: in-game average lifted toward #7FAF5A
            'lichen_pale': LICHEN_PALE, 'lichen_orange': LICHEN_ORANGE,
        })
    return out


# ============================================================================= the head
# The head is modelled in its own frame, then scaled about the neck by HEAD_K (round 4 against 2-turnaround: the face
# is ~57% of the height in the pictures, it was 48%, and the shoulder hump rose as high as the crown). hp / hr / hy / hz
# map a head point, radii, a y or a z into the model; every head constant and head threshold goes through them.
HEAD_K = 1.1
HEAD_PIVOT = (0.0, -0.62, 1.2)
HEAD_SHIFT = (0.0, 0.04, 0.0)                  # back a little, so the nose stays where the turnaround has it


def hp(q) -> tuple:
    return tuple(float(HEAD_PIVOT[i] + (q[i] - HEAD_PIVOT[i]) * HEAD_K + HEAD_SHIFT[i]) for i in range(3))


def hr(r):
    return tuple(float(x * HEAD_K) for x in r) if isinstance(r, (tuple, list)) else float(r * HEAD_K)


def hy(y: float) -> float:
    return float(HEAD_PIVOT[1] + (y - HEAD_PIVOT[1]) * HEAD_K + HEAD_SHIFT[1])


def hz(z: float) -> float:
    return float(HEAD_PIVOT[2] + (z - HEAD_PIVOT[2]) * HEAD_K)


CRANIUM = (hp((0.0, -0.70, 1.20)), hr((0.29, 0.21, 0.23)))
HEAD_C = Vector(hp((0.0, -0.80, 1.16)))       # the rig's head centre
HEAD_R = hr(0.26)
EYE_C = {s: Vector(hp((0.152 * s, -0.885, 1.215))) for s in (1, -1)}
EYE_R = hr(0.054)                              # round 2: ~15% bigger
EYE_DEPTH = (0.55, 0.44)                       # round 5: seated deeper
EYE_SPREAD = 1.0
EYE_SHAPE = (1.12, 0.94)                       # the lens's width and height (an almond under the heavy lid)
# round 3: a wide flat nose pad (about 1.5x wider than tall) sitting on a short broad snout that blends into the cheeks
NOSE_C = Vector(hp((0.0, -1.2, 1.148)))       # round 5: on the tip of a muzzle about 1.5x longer
NOSE_R = hr((0.1, 0.042, 0.064))
NOSE2 = (hp((0.0, -1.207, 1.108)), hr((0.066, 0.034, 0.03)))       # a soft lower lobe
SNOUT = (hp((0.0, -1.0, 1.13)), hr((0.22, 0.2, 0.108)))
JAW = (hp((0.0, -0.9, 0.93)), hr((0.38, 0.25, 0.19)))       # round 5: under the muzzle (no underbite)      # round 3: one rounded mass, no stacked rings
# the heavy stone brows: a curved ridge over each eye, lower and thicker at the inner end (grumpy, 3-faces neutral)
# round 2: one heavy hide brow ridge across the forehead (3-faces), a little arched over each eye, level (no scowl)
# round 3: two heavy hide brow mounds over the eyes that dip above the nose (not a headband), pebbles riding on top
# round 5: the inner ends raised clear of the eyes (grumpy but gentle, not angry): the iris and a sliver of white show
BROW = [(hp(c), hr(r)) for c, r in [((0.115, -0.95, 1.33), (0.11, 0.08, 0.058)), ((0.222, -0.9, 1.318), (0.078, 0.066, 0.05))]]   # final: heavy, the eyes deep under it
MOUTH_AXIS_Y = hy(-0.75)                           # the mouth line is described round this vertical axis (theta, z)
# round 3: round bear ears ~1.3x bigger, up at the head's corners, facing forward, clear of the stones
EAR_C = {s: v3(hp((0.285 * s, -0.66, 1.345))) for s in (1, -1)}
EAR_N = {s: norm(v3((0.45 * s, -0.85, 0.15))[None])[0] for s in (1, -1)}
EAR_R = hr(0.112)
EAR_T = hr(0.06)                                   # half thickness of the disc
EAR_CUP = hr(0.042)                                # how deep the cup is


def _ell(name: str, c, r, mirror: bool = False, rot=(0, 0, 0)) -> Part:
    return Part(name, 'sphere', loc=tuple(c), radius=1.0, scale=tuple(r), mirror=mirror, rot=rot)


def head_parts() -> list[Part]:
    return [
        _ell('cranium', *CRANIUM),
        _ell('bridge', hp((0.0, -1.0, 1.212)), hr((0.1, 0.16, 0.066))),
        _ell('muzzletip', hp((0.0, -1.13, 1.13)), hr((0.15, 0.09, 0.085))),
        _ell('snout', *SNOUT),
        _ell('nose', tuple(NOSE_C), NOSE_R),
        _ell('nose2', *NOSE2),
        # round 3: no flews; the broad snout blends into the cheeks, a broad jaw sweeps into the chest (4-details 1, 4)
        _ell('jowl', hp((0.23, -0.86, 1.05)), hr((0.17, 0.15, 0.13)), mirror=True),      # final: wide cheeks at the tusks
        _ell('muzzleside', hp((0.125, -1.03, 1.11)), hr((0.12, 0.17, 0.09)), mirror=True),   # round 4: snout into cheeks
        _ell('chin', hp((0.0, -1.06, 1.0)), hr((0.16, 0.12, 0.075))),      # round 5: the lower lip under the muzzle
        _ell('jaw', *JAW),
        # round 4: the jaw sweeps into the chest in one slope (the old throat's underside was the second chin): the
        # throat meets the jaw's front at the jaw's lower curve, the bib carries it down between the front legs
        # round 5: one tilted egg (top forward), tangent to the jaw's front, tapering back into the belly
        _ell('chestfront', (0.0, -0.74, 0.62), (0.28, 0.18, 0.28), rot=(25, 0, 0)),    # final: a third smaller, set back
        _ell('neck', hp((0.0, -0.66, 1.0)), hr((0.37, 0.24, 0.3))),
    ] + [_ell(f'brow{i}', c, r, mirror=True) for i, (c, r) in enumerate(BROW)]


# ============================================================================= body, legs, feet, claws, tail
LEGS = {'FL': (0.37, -0.40), 'FR': (-0.37, -0.40), 'BL': (0.33, 0.45), 'BR': (-0.33, 0.45)}
LEG_TOP = {'F': 0.62, 'B': 0.60}
LEG_R = {'F': (0.25, 0.175), 'B': (0.25, 0.17)}     # round 4: tapered (wide haunch, narrower ankle)
FOOT = {'F': (0.21, 0.24, 0.095), 'B': (0.19, 0.23, 0.095)}       # radii of the flat foot
FOOT_DY = {'F': -0.07, 'B': -0.05}                                  # the foot's centre ahead of the leg
CLAW_DX = (-0.158, 0.0, 0.158)
CLAW_R = ((0.074, 0.096, 0.06), (0.078, 0.1, 0.064), (0.074, 0.096, 0.06))       # round 5: thicker domes      # across, long, thick (a nail)
CLAW_PITCH = 18.0                       # degrees the nail tips front-down (blunt, curving to the ground)
TAIL_POINTS = [(0.0, 0.62, 0.80), (0.0, 0.735, 0.815), (0.0, 0.85, 0.83)]


def claw_centres(leg: str) -> list[tuple[tuple, tuple, float]]:
    """(centre, radii, yaw degrees) of the three claws round the front of a foot."""
    x, y = LEGS[leg]
    f = leg[0]
    fy = y + FOOT_DY[f]
    ry = FOOT[f][1]
    out = []
    for i, dx in enumerate(CLAW_DX):
        side = 0 if dx == 0 else (1 if dx > 0 else -1)
        cy = fy - ry * (0.98 if side == 0 else 0.78)
        r = CLAW_R[i]
        out.append(((x + dx * (FOOT[f][0] / 0.21), cy, 0.078), r, side * 24.0))
    return out


def leg_parts(leg: str) -> list[Part]:
    x, y = LEGS[leg]
    f = leg[0]
    top = LEG_TOP[f]
    r0, r1 = LEG_R[f]
    fy = y + FOOT_DY[f]
    ps = [
        Part(f'leg{leg}', 'tube', loc=(x, y + 0.03, top), to=(x, y - 0.02, 0.17), radius=r0, r2=r1),
        _ell(f'foot{leg}', (x, fy, FOOT[f][2]), FOOT[f]),
        _ell(f'heel{leg}', (x, y + 0.07, 0.12), (FOOT[f][0] * 0.85, 0.14, 0.12)),
    ]
    if f == 'F':
        ps.append(_ell(f'elbow{leg}', (x * 1.02, y + 0.1, 0.44), (0.17, 0.19, 0.2)))
    for i, (c, r, yaw) in enumerate(claw_centres(leg)):
        ps.append(_ell(f'claw{leg}{i}', c, r, rot=(CLAW_PITCH, 0, yaw)))
        # the toe lobe behind each claw (the foot's front reads as three fat toes)
        a = math.radians(yaw)
        back = v3((-math.sin(a), math.cos(a), 0.0)) * 0.035
        ps.append(_ell(f'toe{leg}{i}', tuple(v3(c) + back + v3((0.0, 0.0, -0.012))), (0.088, 0.095, 0.072), rot=(0, 0, yaw)))
    return ps


def torso_parts() -> list[Part]:
    ps = [
        _ell('hump', (0.0, -0.46, 1.04), (0.46, 0.32, 0.28)),
        _ell('chest', (0.0, -0.45, 0.78), (0.46, 0.33, 0.42)),
        _ell('torso', (0.0, -0.02, 0.74), (0.47, 0.62, 0.42)),
        _ell('belly', (0.0, -0.12, 0.52), (0.40, 0.52, 0.26)),
        _ell('rump', (0.0, 0.40, 0.73), (0.43, 0.32, 0.33)),
        _ell('shoulder', (0.36, -0.42, 0.72), (0.22, 0.27, 0.3), mirror=True),
        _ell('haunch', (0.30, 0.44, 0.62), (0.2, 0.27, 0.3), mirror=True),
        _ell('thigh', (0.345, 0.46, 0.41), (0.235, 0.27, 0.2), mirror=True),        # round 3: the hind thighs bulge
        _ell('forearm', (0.385, -0.40, 0.41), (0.235, 0.26, 0.19), mirror=True),    # and the upper front legs
        Part('tail', 'tube', loc=TAIL_POINTS[0], to=TAIL_POINTS[-1], radius=0.105, r2=0.085),
        _ell('tailtip', TAIL_POINTS[-1], (0.088, 0.075, 0.085)),
    ]
    for leg in LEGS:
        ps.extend(leg_parts(leg))
    return ps


def all_parts() -> list[Part]:
    return head_parts() + torso_parts()


# ----------------------------------------------------------------------------- the ears: small round cups (body extras)
def ear_frame(s: int):
    c, n = EAR_C[s], EAR_N[s]
    up = v3((0.0, 0.0, 1.0))
    up = up - n * (up @ n)
    up = up / np.linalg.norm(up)
    across = np.cross(up, n)
    return c, across, up, n


def ear_mesh(s: int) -> bpy.types.Object:
    """A thick round disc whose front face is cupped (a rolled rim round a hollow), facing out and forward."""
    c, ax, up, n = ear_frame(s)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=1.0)
    for v in bm.verts:
        X, Y, Z = v.co.x, v.co.y, v.co.z            # Z along the ear's normal
        r = math.sqrt(X * X + Y * Y)
        w = Z * EAR_T
        if Z > 0:
            w -= EAR_CUP * max(0.0, 1.0 - (r / 0.78) ** 2) ** 0.8
        p = c + ax * (X * EAR_R) + up * (Y * EAR_R * 0.96) + n * w
        v.co = Vector(p)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'ear{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
    return ob


def body_extras() -> list[bpy.types.Object]:
    return [ear_mesh(1), ear_mesh(-1)]


def ear_dist(p: np.ndarray) -> np.ndarray:
    """Metres to the nearer ear's centre."""
    return np.minimum(np.linalg.norm(p - EAR_C[1][None], axis=1), np.linalg.norm(p - EAR_C[-1][None], axis=1))


def ear_lookup(p: np.ndarray) -> dict:
    """Per point: on an ear (bool), its radial share r (0 centre … 1 rim), the offset along the ear's normal (w) and
    whether it is the cupped front (the inside)."""
    k = len(p)
    on = np.zeros(k, bool)
    rr = np.full(k, 9.0)
    ww = np.zeros(k)
    side = np.zeros(k)
    for s in (1, -1):
        c, ax, up, n = ear_frame(s)
        q = p - c
        x, y, w = q @ ax, q @ up, q @ n
        r = np.sqrt((x / EAR_R) ** 2 + (y / (EAR_R * 0.96)) ** 2)
        hit = (r < 1.12) & (w > -EAR_T * 1.1) & (w < EAR_T * 1.6) & (p[:, 0] * s > 0.15)
        on |= hit
        rr = np.where(hit, r, rr)
        ww = np.where(hit, w, ww)
        side = np.where(hit, s, side)
    cupped = on & (rr < 0.74) & (ww > -0.004)
    return {'on': on, 'r': rr, 'w': ww, 's': side, 'inside': cupped}


# ============================================================================= zones
def mouth_theta(p: np.ndarray) -> np.ndarray:
    """Degrees round the head's vertical axis (0 straight ahead, + toward the monster's left)."""
    return np.degrees(np.arctan2(p[:, 0], -(p[:, 1] - MOUTH_AXIS_Y)))


MOUTH_TH = [0.0, 15.0, 30.0, 42.0, 52.0, 60.0, 66.0, 70.0]
MOUTH_Z = [hz(z) for z in (1.03, 1.033, 1.044, 1.064, 1.092, 1.118, 1.138, 1.152)]     # round 2: corners up into the cheeks


def mouth_z(th: np.ndarray) -> np.ndarray:
    return np.interp(np.abs(th), MOUTH_TH, MOUTH_Z)


def crown_z(p: np.ndarray) -> np.ndarray:
    """Above this height the head wears its cobbled crown (it dips toward the ears and falls away behind the cheeks)."""
    x, y = p[:, 0], p[:, 1]
    ax = np.abs(x)
    k = HEAD_K
    zc = hz(1.345) + 0.025 * k * np.exp(-((ax - 0.14 * k) / (0.06 * k)) ** 2) - 0.06 * k * smooth(0.18 * k, 0.3 * k, ax)
    # behind the cheeks the neck wears cobbles all the way down
    zc = zc - 0.75 * smooth(hy(-0.75), hy(-0.62), y)
    return zc


def z_low(y: np.ndarray) -> np.ndarray:
    """The lower edge of the cobbled coat along the body (2-turnaround side): low over the shoulder and the haunch."""
    return np.interp(y, [-0.80, -0.62, -0.46, -0.3, -0.12, 0.0, 0.3, 0.46, 0.65, 0.95],
                     [0.80, 0.56, 0.40, 0.44, 0.52, 0.55, 0.55, 0.52, 0.53, 0.58])


def leg_masks(p: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    out = {}
    for leg, (lx, ly) in LEGS.items():
        f = leg[0]
        r = np.hypot(x - lx, (y - ly - FOOT_DY[f] * smooth(0.25, 0.05, z)) * 0.85)
        out[leg] = (r < 0.3) & (z < LEG_TOP[f] - 0.04) & (x * lx > 0)
    return out


def _claw_local(p: np.ndarray, c, yaw: float) -> np.ndarray:
    """Points in a nail's own frame (undoing the Part's rotation: X by CLAW_PITCH, then Z by yaw)."""
    q = p - v3(c)
    a, b = math.radians(yaw), math.radians(CLAW_PITCH)
    ca, sa = math.cos(a), math.sin(a)
    x1, y1 = q[:, 0] * ca + q[:, 1] * sa, -q[:, 0] * sa + q[:, 1] * ca
    cb, sb = math.cos(b), math.sin(b)
    y2, z2 = y1 * cb + q[:, 2] * sb, -y1 * sb + q[:, 2] * cb
    return np.stack([x1, y2, z2], axis=1)


def claw_dist(p: np.ndarray) -> np.ndarray:
    """The smallest ellipsoid radius (1 = on the surface) over every nail."""
    d = np.full(len(p), 9.0)
    for leg in LEGS:
        for c, r, yaw in claw_centres(leg):
            d = np.minimum(d, np.linalg.norm(_claw_local(p, c, yaw) / v3(r), axis=1))
    return d


def claw_local_best(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per point: the nearest nail's ellipsoid radius (1 = on its surface) and the point in that nail's frame over its
    radii (x across, y along: -1 the tip ... +1 the root, z up)."""
    best = np.full(len(p), 9.0)
    loc = np.zeros((len(p), 3))
    for leg in LEGS:
        for c, r, yaw in claw_centres(leg):
            q = _claw_local(p, c, yaw) / v3(r)
            d = np.linalg.norm(q, axis=1)
            closer = d < best
            best = np.where(closer, d, best)
            loc = np.where(closer[:, None], q, loc)
    return best, loc


def claw_mask(p: np.ndarray, grow: float = 1.0) -> np.ndarray:
    """0..1: on a claw (the nails' ellipsoids in their own frames, a little grown)."""
    return smooth(grow * 1.06, grow * 0.94, claw_dist(p))


def tail_mask(p: np.ndarray) -> np.ndarray:
    a = v3(TAIL_POINTS[0])
    t = (p - a) @ norm((v3(TAIL_POINTS[-1]) - a)[None])[0]
    return (t > 0.02) & (np.abs(p[:, 0]) < 0.2) & (p[:, 2] > 0.6) & (p[:, 2] < 1.02)


_ZC: dict = {}


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    if n is None:
        n = np.tile(v3((0.0, 0.0, 1.0)), (len(p), 1))
    E = ear_lookup(p)
    head = ((in_ellipsoid(p, hp((0.0, -0.86, 1.12)), hr((0.46, 0.44, 0.44))) < 1.0) & (y < hy(-0.6)) & (z > hz(0.72))) | E['on']
    th = mouth_theta(p)
    mz = mouth_z(th)
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    cz = crown_z(p)
    face = head & ~E['on'] & (z < cz) & (y < hy(-0.74)) & (ax < hr(0.36)) & (z > hz(0.78))
    muzzle = (in_ellipsoid(p, hp((0.0, -1.09, 1.12)), hr((0.2, 0.19, 0.1))) < 1.0) & (z > mz - 0.004)
    nose = (in_ellipsoid(p, tuple(NOSE_C), tuple(r * 1.12 for r in NOSE_R)) < 1.0) | (in_ellipsoid(p, NOSE2[0], tuple(r * 1.15 for r in NOSE2[1])) < 1.0)
    # the lower jaw: the face below the mouth line (and the chin and the jaw's sides back to the throat)
    jaw = head & ~E['on'] & (z < mz) & (np.abs(th) < 78) & (y < hy(-0.70))
    legs = leg_masks(p)
    leg = np.zeros(len(p), bool)
    for m in legs.values():
        leg |= m
    leg &= ~head
    claw = claw_mask(p) > 0.5
    paw = leg & (z < 0.2)
    sole = z < 0.012
    tail = tail_mask(p) & ~leg
    torso = ~head & ~leg & ~tail
    zl = z_low(y)
    # the pale stone underside: the throat and chest between the shoulders, the belly between the legs
    chest = torso & (y < -0.5) & (ax < 0.31 + 0.05 * smooth(0.6, 0.35, z)) & (z < 0.98)
    zb = np.interp(y, [-0.6, -0.3, 0.0, 0.3, 0.55], [0.5, 0.44, 0.4, 0.42, 0.46])
    belly = torso & (z < zb) & (ax < 0.36)
    out = {'head': head, 'face': face, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'jaw': jaw, 'ear': E['on'],
           'ear_in': E['inside'], 'ear_r': E['r'], 'leg': leg, 'legs': legs, 'claw': claw, 'paw': paw, 'sole': sole,
           'toes': claw, 'tail': tail, 'torso': torso, 'chest': chest, 'belly': belly, 'theta': th, 'mouth_z': mz,
           'crown_z': cz, 'z_low': zl}
    out['cover'] = cover(p, n, out)
    return out


def cover(p: np.ndarray, n: np.ndarray, z: dict) -> np.ndarray:
    """0..1: the cobbled coat (the top of the head, the neck, the shoulders, the back, the flanks, the rump, the tail),
    with a ragged edge. Bare: the face below the crown, the jaw, the throat and chest, the belly, the legs, the ears."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    rag = 0.045 * K.fbm(p, 1 / 0.16, 21, 2)
    # the body: above the ragged lower line
    body = smooth(-0.015, 0.025, zz - (z['z_low'] + rag))
    # the throat and the chest stay bare between the shoulders (front view: pale from the chin to the belly)
    front = (y < -0.5) & (ax < 0.26 + 0.04 * smooth(0.95, 0.6, zz) + rag) & (zz < 1.02)     # final: stones on the shoulders' front
    body = np.where(front, 0.0, body)
    # the head: the crown and everything behind the cheeks
    # final round: a hood (2-turnaround): the crown, down over the brow sides, round the ears and down the nape,
    # joining the shoulder stones in one mound; the eyes, the brows' inner ends, the muzzle and the jaw stay bare
    crown = smooth(-0.01, 0.02, zz - (z['crown_z'] + rag * 0.4))
    side = smooth(hr(0.19), hr(0.25), ax + rag * 0.5) * smooth(hy(-0.9), hy(-0.84), y) * smooth(hz(1.07), hz(1.13), zz)
    nape = smooth(hy(-0.8), hy(-0.72), y + rag * 0.5) * smooth(hz(0.96), hz(1.02), zz)
    hood = np.maximum(np.maximum(crown, side), nape) * smooth(0.085, 0.115, z['eye_d'])
    c = np.where(z['head'], hood, body)
    c = np.where(z['tail'], 1.0, c)
    c = np.where(z['ear'] | z['jaw'] | z['claw'] | z['nose'], 0.0, c)
    c = np.where(ear_dist(p) < EAR_R * 1.3, 0.0, c)
    c = np.where(z['leg'] & (zz < z['z_low'] - 0.02), 0.0, c)
    return np.clip(c, 0.0, 1.0)


# ============================================================================= the cobbles and the moss
_PLATES: dict = {}
SEED = 303


def _plate_params(p: np.ndarray, n: np.ndarray, z: dict):
    """(spacing, radius, height) per sample point for the main cobbles; spacing NaN off the coat."""
    y, zz = p[:, 1], p[:, 2]
    k = len(p)
    sp = np.full(k, 0.19)
    sp = np.where(y < -0.15, 0.205, sp)                               # neck, hump and shoulders: the biggest
    sp = np.where(z['head'] & (y < hy(-0.6)), 0.125, sp)              # the crown
    sp = np.where(z['head'] & (y >= hy(-0.6)) & (zz < hz(1.15)), 0.14, sp)   # the neck's sides framing the face
    # smaller toward the coat's lower edge, and on the rump's end and the tail
    edge = smooth(0.2, 0.0, zz - z['z_low'])
    sp = sp * (1.0 - 0.38 * edge * ~z['head'])
    sp = np.where(y > 0.62, np.minimum(sp, 0.12), sp)
    sp = np.where(z['tail'], 0.1, sp)                                # the tail: a knob of a few small cobbles
    ok = (z['cover'] > 0.55) & (ear_dist(p) > EAR_R * 1.75)
    # round 2: packed edge to edge (0.6 x the spacing, small fillers in every gap: moss only in the narrow seams) and
    # standing about half their height proud (the outline lumpy, not a dome)
    rad = sp * 0.62                       # final: gaps ~10-15% of a stone, filled with moss
    hgt = np.clip(sp * 0.34, 0.032, 0.075)
    return np.where(ok, sp, np.nan), rad, hgt


def _merge(a: dict, b: dict) -> dict:
    return {key: np.concatenate([a[key], b[key]]) for key in a}


def _clear_of(co: np.ndarray, vn: np.ndarray, plates: dict, margin: float) -> np.ndarray:
    """True where a point lies at least `margin` metres outside every plate's outline (room for a new stone there)."""
    wide = dict(plates)
    wide['a'] = plates['a'] + margin
    wide['b'] = plates['b'] + margin
    return U.plate_field(co, vn, wide, 'cobble')['pid'] < 0


def make_plates(co: np.ndarray, vn: np.ndarray) -> dict:
    """The coat's cobbles (cached: the high source's layout is reused for the low body): big ones first, then small
    fillers in about half the gaps and a row of pebbles along the brow, then a few strays below the coat's edge."""
    if 'plates' in _PLATES:
        return _PLATES['plates']
    z = zones(co, vn)
    sp, rad, hgt = _plate_params(co, vn, z)
    flow = norm(np.cross(vn, v3((1.0, 0.0, 0.0))[None]) + 1e-6)
    big = U.plate_layout(co, vn, sp, rad, hgt, SEED, flow=flow, aspect=1.15, wobble=0.24)
    # fillers only in the wide gaps: at least ~4 cm from every big stone's edge (round 2 pass 2: fillers in every gap
    # made bubble-wrap and left no moss seams); the moss keeps the 1-3 cm seams between the stones
    # medium stones, then small ones, each only where it keeps a 1-1.5 cm seam to every stone already laid
    mid = U.plate_layout(co, vn, np.where(_clear_of(co, vn, big, 0.065) & (z['cover'] > 0.6), 0.115, np.nan), 0.05, 0.034,
                         SEED + 3, aspect=1.15, wobble=0.22)
    laid = _merge(big, mid)
    clear = _clear_of(co, vn, laid, 0.048)
    gap = clear & (z['cover'] > 0.6)
    sp2 = np.where(gap, 0.072, np.nan)
    # the pebbles along the brow: a band just above the crown line on the face
    band = z['head'] & (co[:, 1] < hy(-0.82)) & (np.abs(co[:, 0]) < hr(0.24)) & (co[:, 2] > z['crown_z'] - 0.005) & (co[:, 2] < z['crown_z'] + 0.04)
    sp2 = np.where(band & _clear_of(co, vn, laid, 0.02), 0.042, sp2)
    rad2 = np.where(band, 0.02, 0.032)
    hgt2 = np.where(band, 0.017, 0.026)
    small = U.plate_layout(co, vn, sp2, rad2, hgt2, SEED + 1, aspect=1.15, wobble=0.22)
    fill = _merge(mid, small)
    # strays: loose stones below the coat's edge on the shoulders, flanks and haunches (1-hero)
    below = (co[:, 2] < z['z_low'] - 0.02) & (co[:, 2] > z['z_low'] - 0.2) & z['torso'] & ~z['chest'] & ~z['belly']
    below &= (co[:, 2] > 0.44) & (np.abs(co[:, 0]) > 0.33) & (co[:, 1] > -0.5) & (co[:, 2] > z['z_low'] - 0.1)
    sp3 = np.where(below & (K.hash3(np.floor(co / 0.07).astype(np.int64), 9) < 0.35), 0.22, np.nan)
    strays = U.plate_layout(co, vn, sp3, 0.036, 0.02, SEED + 2, aspect=1.15, wobble=0.14)
    plates = _merge(_merge(big, fill), strays)
    plates['kind'] = np.concatenate([np.zeros(len(big['c'])), np.ones(len(fill['c'])), np.full(len(strays['c']), 2.0)])
    C.log(f'cobbles: {len(big["c"])} big, {len(fill["c"])} fillers and pebbles, {len(strays["c"])} strays')
    _PLATES['plates'] = plates
    return plates


MOSS_H = 0.011                 # round 2: low in the gaps (a 1.9 cm mound sank the stones into a lawn)
LOW_SCALE = 0.95                # the low body's stones (round 2: 0.85 smoothed the outline into a dome)
EDGE_SOFT = 0.25                # rounds the stones' walls a little where they stretch the voxel body (the moss hides the rest)


def moss_height(co: np.ndarray, cov: np.ndarray, fuzz: bool) -> tuple[np.ndarray, np.ndarray]:
    """Round 4: the moss as soft cushions in the gaps (clumps of about 3 cm, 0.6-2.2 cm tall), and its light (-1..1):
    the clumps' tops yellow-green, their roots and the hollows deep; the high source adds a fine fuzz."""
    clump = smooth(0.25, 0.85, K.value_noise(co, 1 / 0.03, 41))
    h = cov * (0.008 + 0.019 * clump ** 1.3)          # round 5b: more moss in every seam
    fz = clump * 2.0 - 1.0
    if fuzz:
        fz = np.clip(0.65 * fz + 0.35 * (0.6 * K.fbm(co, 1 / 0.009, 43, 2) + 0.4 * K.fbm(co, 1 / 0.0045, 47, 1)), -1, 1)
    return h, fz


def facet_cut(co: np.ndarray, pid: np.ndarray, plates: dict, hp: np.ndarray, scale: float) -> np.ndarray:
    """Round 4: each stone cut into flat facets with real edges (4-details panel 5): a flat, slightly tilted top and six
    bevels round its shoulder, their planes different on every stone; the dome stays below them."""
    on = pid >= 0
    if not on.any():
        return hp
    i = pid[on]
    c, t, nrm = plates['c'][i], plates['t'][i], plates['n'][i]
    bt = np.cross(nrm, t)
    d = co[on] - c
    s_ = (d * t).sum(1) / plates['a'][i]
    q_ = (d * bt).sum(1) / plates['b'][i]
    H = plates['h'][i] * scale
    ang = U.plate_hash(i, 12) * 2 * np.pi
    out = np.minimum(hp[on], H * (0.86 + 0.1 * U.plate_hash(i, 11) + 0.12 * U.plate_hash(i, 13) * (s_ * np.cos(ang) + q_ * np.sin(ang))))
    for k in range(6):
        phi = 2 * np.pi * k / 6 + 0.9 * U.plate_hash(i, 20 + k)
        u = s_ * np.cos(phi) + q_ * np.sin(phi)
        u0 = 0.55 + 0.25 * U.plate_hash(i, 30 + k)          # round 5: chipped edges on rounded cobbles (no hex tiles)
        g = 0.9 + 0.7 * U.plate_hash(i, 40 + k)
        out = np.minimum(out, H * (1.0 - g * np.maximum(0.0, u - u0)))
    res = hp.copy()
    res[on] = np.maximum(out, 0.0)
    return res


def coat_field(co: np.ndarray, vn: np.ndarray, plates: dict, z: dict, scale: float, fuzz: bool) -> dict:
    """The cobbles and the moss together: h (metres along the normal), plate (0..1 on a visible stone), moss (0..1),
    rim, top, pid, fuzz."""
    f = U.plate_field(co, vn, plates, 'cobble', scale, edge_soft=EDGE_SOFT)
    hp = facet_cut(co, f['pid'], plates, f['h'], scale)
    cov = z['cover']
    # a ring of moss round each stray stone
    stray = (f['pid'] >= 0) & (plates['kind'][np.clip(f['pid'], 0, None)] > 1.5)
    hm, fz = moss_height(co, cov, fuzz)
    hm = hm * scale * (1.0 - z['tail'])                # no moss on the tail's knob of cobbles
    if fuzz:
        hm = hm + 0.0015 * fz * cov
    vis = smooth(-0.002, 0.003, hp - hm)                 # the stone shows where it stands above the moss
    h = np.maximum(hp, hm)
    moss = cov * (1.0 - vis)
    plate = (f['pid'] >= 0) * vis
    return {'h': h, 'plate': plate, 'moss': moss, 'rim': f['rim'], 'top': f['top'], 'pid': f['pid'], 'fuzz': fz,
            'stray': stray, 'mask': f['mask']}


# ----------------------------------------------------------------------------- the moss's strands (lying locks, baked)
# Short soft strands standing up out of the moss mound (4-details panel 5: fuzzy, bright-tipped clumps). They are
# high-source geometry only: the bake turns them into the normal map, the AO between them and their colour (deep green
# roots, yellow-green tips). No cards: nothing of them ships as geometry.
LOCK_TEMPLATES = {'body': (4, 7, 2, 0.3)}


def _hash_dir(p: np.ndarray, seed: int) -> np.ndarray:
    q = np.floor(p / 0.004).astype(np.int64)
    return np.stack([K.hash3(q, seed, k) - 0.5 for k in range(3)], axis=1)


def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    """The moss strands lean every which way (a random tangent per spot), a little downhill."""
    g = norm(_hash_dir(p, 91) + 1e-6) + v3((0.0, 0.0, -0.25))[None]
    return S.tangent(g, n)


def moss_gaps(p, n, z, slack: float = 0.004) -> np.ndarray:
    """True where the moss shows at sample points on the carved high body (the gaps between the stones, the rings round
    the strays): the stones there stand no higher than the moss mound. Not on the tail's knob."""
    plates = _PLATES.get('plates')
    if plates is None:
        return np.zeros(len(p), bool)
    f = U.plate_field(p, n, plates, 'cobble', edge_soft=EDGE_SOFT)
    hm, _fz = moss_height(p, z['cover'], False)
    return (z['cover'] > 0.35) & (f['h'] < hm + slack) & ~z['tail']


def body_lock_params(p, n):
    """Moss strands where the moss shows (the coat's grooves, the rings round the strays); none on the stones."""
    z = zones(p, n)
    k = len(p)
    moss = moss_gaps(p, n, z)
    clump = K.value_noise(p, 1 / 0.025, 95)
    L = 0.0115 * (0.6 + 0.8 * clump)
    W = np.full(k, 0.0048)
    lift = np.full(k, math.radians(55.0))
    return np.where(moss, 0.006, np.nan), L, W, lift, z


def card_params(p, n, layer: int):
    """Round 2: the moss's tufts (1-hero, 4-details panel 5): short curly cards (CARD_STYLE 'wool') rooted in the gaps,
    rising above the stones' edges and spilling over them; a few hundred, 2.5-4 cm."""
    z = zones(p, n)
    k = len(p)
    moss = moss_gaps(p, n, z, -0.002)
    # round 5: no tufts on the brow or the face below the crown (stray sprigs), short dense mounds on the crown
    moss &= ~(z['head'] & (p[:, 2] < z['crown_z'] + 0.03))
    clump = K.value_noise(p, 1 / 0.04, 101)
    L = 0.038 * (0.8 + 0.5 * clump) * np.where(z['head'], 0.6, 1.0)
    W = np.full(k, 0.03)
    lift = np.full(k, math.radians(44.0))
    return np.where(moss, 0.018, np.nan), L, W, lift, z


# ============================================================================= carving (the high source)
LID_LASH, LID_DROP, LID_W = 0.08, 0.16, 0.92


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye: forward and a little outward (the eyes sit wide on the face)."""
    c = EYE_C[s]
    look = Vector((0.36 * s, -1.0, 0.06)).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


def blink_pivot(s: int) -> tuple[Vector, Vector, Vector]:
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.74, 0.04, 0.2)


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
        th = 0.0022 + 0.0016 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def _face_marks(co: np.ndarray, z: dict) -> dict:
    """The mouth groove, the nostrils, the philtrum and the claws' lip (as 0..1 masks)."""
    x, y, zz = co[:, 0], co[:, 1], co[:, 2]
    th = z['theta']
    front = (y < hy(-0.78)) & z['head'] & (np.abs(th) < 72)
    groove = np.exp(-((zz - z['mouth_z']) / 0.0042) ** 2) * front * smooth(72, 64, np.abs(th))
    # the corners curl up into the cheeks: a short soft crease past the end
    curl = np.zeros(len(co))
    for s in (1, -1):
        cc = v3(hp((0.256 * s, -0.868, 1.146)))
        curl = np.maximum(curl, np.exp(-(np.linalg.norm(co - cc, axis=1) / 0.016) ** 2))
    groove = np.maximum(groove, 0.85 * curl)
    nos = np.zeros(len(co))
    for s in (1, -1):
        dd = np.sqrt(((x - hr(0.046) * s) / 1.5) ** 2 + (zz - (NOSE_C.z - hr(0.016))) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / hr(0.015)) ** 2))
    nos *= smooth(NOSE_C.y + 0.03, NOSE_C.y + 0.008, y)
    phil = np.exp(-(x / 0.0035) ** 2) * (zz < NOSE2[0][2] - 0.02) * (zz > z['mouth_z']) * (y < hy(-1.0))
    lip = np.exp(-((claw_dist(co) - 1.0) / 0.08) ** 2) * (zz > 0.012)
    return {'groove': groove, 'nostril': nos, 'philtrum': phil, 'claw_lip': lip}


def eye_socket(co: np.ndarray) -> np.ndarray:
    """Metres to push in round each eye: a soft dip just outside the lens so the brow, the cheek and the voxel
    smoothing never cover its edge (the eyes are deep-set, but the white must show)."""
    d = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        r = np.sqrt((xe / (EYE_R * EYE_SHAPE[0])) ** 2 + (ye / (EYE_R * EYE_SHAPE[1])) ** 2)
        ring = smooth(0.85, 1.05, r) * smooth(1.6, 1.12, r) * (ze > -0.03) * (ze < 0.05)
        d = np.maximum(d, 0.008 * ring)
    return -d


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
    C.apply_modifiers(ob)                    # a new mesh: look the group up again by name
    left = ob.vertex_groups.get('ws_region_smooth')
    if left is not None:
        ob.vertex_groups.remove(left)


def smooth_masks(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """0..1 per vertex: the jaw-to-chest front below the mouth (the stacked rolls), and the snout's sides (where it
    meets the cheeks), never the nose pad, the eyes, the mouth line or the stones."""
    z = zones(co)
    x, y, zz = co[:, 0], co[:, 1], co[:, 2]
    ax = np.abs(x)
    jaw = (smooth(-0.5, -0.64, y) * smooth(0.3, 0.42, zz) * smooth(z['mouth_z'] - 0.025, z['mouth_z'] - 0.07, zz)
           * smooth(0.47, 0.37, ax) * (1.0 - z['cover']) * (1.0 - z['leg'] * smooth(0.45, 0.3, zz)))
    nose = in_ellipsoid(co, tuple(NOSE_C), tuple(r * 1.5 for r in NOSE_R)) < 1.0
    snout = (smooth(hy(-0.9), hy(-0.96), y) * smooth(z['mouth_z'] + 0.012, z['mouth_z'] + 0.03, zz) * smooth(hz(1.27), hz(1.22), zz)
             * smooth(hr(0.05), hr(0.09), ax) * smooth(hr(0.32), hr(0.26), ax) * smooth(0.07, 0.1, z['eye_d']) * ~nose)
    return np.clip(jaw, 0.0, 1.0), np.clip(snout, 0.0, 1.0)


def leg_smooth_mask(co: np.ndarray) -> np.ndarray:
    """0..1: the legs below the coat, from above the toes to the coat's edge (the union's creases between the thigh,
    the column, the heel and the foot melt into one tapered leg); never the nails or the toes."""
    z = zones(co)
    zz = co[:, 2]
    m = z['leg'] * smooth(0.1, 0.16, zz) * smooth(z['z_low'] + 0.05, z['z_low'] - 0.01, zz) * smooth(1.5, 2.1, claw_dist(co))
    return np.clip(m, 0.0, 1.0)


def smooth_front(ob: bpy.types.Object) -> None:
    """Round 4: melt the stacked rolls under the jaw (the voxel union's creases between the jaw, throat, chest and belly)
    into one rounded mass sweeping into the chest, and blend the snout into the cheeks. The reach is the same on every
    voxel size (about 8.5 cm for the jaw, 2.5 cm for the snout), so the high and low bodies agree."""
    co, _vn = S.mesh_arrays(ob)
    edge = math.sqrt(max(S.mesh_area(ob), 1e-9) / max(len(co), 1))
    jaw, snout = smooth_masks(co)
    _region_smooth(ob, jaw, int(np.clip((0.085 / edge) ** 2, 8, 1800)))
    _region_smooth(ob, leg_smooth_mask(co), int(np.clip((0.04 / edge) ** 2, 6, 260)))
    _region_smooth(ob, snout, int(np.clip((0.025 / edge) ** 2, 4, 120)), 0.5)


def carve(ob: bpy.types.Object) -> None:
    """The high source: the cobbles and the moss, then the stone detail (grain and cracks on the hide, pits and chips
    on the stones, fuzz on the moss), the face's grooves and the closed lids."""
    smooth_front(ob)
    co, vn = S.mesh_arrays(ob)
    z = zones(co, vn)
    plates = make_plates(co, vn)
    f = coat_field(co, vn, plates, z, 1.0, True)
    hide = (1.0 - f['plate']) * (1.0 - f['moss'])
    light = light_mask(co, z)
    # the hide: a weathered-rock grain and a network of cracks (big plates of hide, finer cracks inside them)
    gr = K.grain(co)
    # round 2: a few long hairline cracks (the 8.5 cm polygon network read as crazed porcelain)
    ck_big = K.cracks(co, 0.24, 0.0022, 61, warp=0.06) * smooth(-0.1, 0.25, K.fbm(co, 1 / 0.3, 62, 2))
    pf1, _pf2, _pfid = K.voronoi(co, 0.011, 87)                  # distinct pits (4-details hide swatch)
    dimples = smooth(0.0032, 0.0012, pf1) * smooth(-0.3, 0.2, K.fbm(co, 1 / 0.05, 88, 2))
    face_soft = 1.0 - 0.6 * smooth(0.12, 0.06, z['eye_d']) - 0.5 * z['nose']
    vary = 0.55 + 0.45 * smooth(-0.4, 0.4, K.fbm(co, 1 / 0.25, 63, 2))
    ck_mid = K.cracks(co, 0.12, 0.0016, 64, warp=0.04) * smooth(0.05, 0.35, K.fbm(co, 1 / 0.2, 66, 2))
    crack = np.clip(np.maximum(ck_big, 0.8 * ck_mid * (0.4 + 0.6 * light)) * face_soft * vary * (1.0 - 0.35 * z['head'] * (1 - light)), 0.0, 1.0)
    pitted = np.clip(K.fbm(co, 1 / 0.007, 79, 1) - 0.18, 0.0, 1.0)      # fine pits (4-details hide swatch)
    grain_amp = 0.0005 * (1.0 - 0.35 * light) * (1.0 - 0.5 * z['nose'])       # final: no fleece
    weather = K.fbm(co, 1 / 0.025, 65, 2)                       # broad weathered dips and swellings
    d_hide = (grain_amp * gr + 0.0013 * weather * (1.0 - 0.5 * face_soft * z['face']) - 0.0034 * crack - 0.0008 * pitted - 0.0024 * dimples) * hide * (1.0 - z['claw'])
    # the stones: pits over the crown, chipped edges near the rim
    pits = K.fbm(co, 1 / 0.007, 71, 2)
    # round 2: chipped faceted edges (flat cuts that break at the cell walls) near the rims, flatter facets on the crowns
    chips = K.facets(co, 0.025, 73) * smooth(0.05, 0.7, f['rim'])
    flats = K.facets(co, 0.045, 77) * (0.6 + 0.4 * smooth(0.2, 0.7, f['rim']))      # round 3: facets over the whole stone
    dents = np.clip(-K.fbm(co, 1 / 0.05, 75, 2) - 0.2, 0.0, 1.0)
    # round 4: crusty lichen as a carved attribute (fine ragged patches with a little relief) on the upper faces
    ln = K.fbm(co, 1 / 0.011, 83, 3) + 0.45 * K.fbm(co, 1 / 0.0045, 85, 2)
    crust = smooth(0.3, 0.36, K.fbm(co, 1 / 0.035, 89, 3) + 0.25 * K.fbm(co, 1 / 0.006, 91, 1)) * smooth(0.1, 0.5, f['top'])   # final: ~20%
    lichen = np.maximum(smooth(0.3, 0.36, ln) * (0.25 + 0.75 * smooth(0.05, 0.5, f['top'])), crust) * f['plate']
    d_stone = (0.0024 * pits - 0.018 * chips - 0.003 * flats - 0.004 * dents) * f['plate'] + 0.001 * lichen
    # round 4: nails with a flat top and a crisp edge (not pills)
    cd, cl = claw_local_best(co)
    claw_flat = 0.0 * cd                    # round 5: domed again (the flat tops read as spatulas in profile)
    # the claws: a smooth, pebble surface with a lip where they meet the toe; the soles a little pebbled
    fm = _face_marks(co, z)
    d_face = -0.0035 * fm['groove'] - 0.02 * fm['nostril'] - 0.0018 * fm['philtrum'] - 0.003 * fm['claw_lip']
    bulge, lash = closed_lid(co)
    d_lid = 0.0035 * bulge - 0.0012 * lash
    disp = f['h'] + d_hide + d_stone + d_face + d_lid + eye_socket(co) + claw_flat
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': fm['groove']})
    for name, val in (('plate', f['plate']), ('plate_rim', f['rim']), ('plate_top', f['top']),
                      ('plate_id', f['pid'].astype(np.float64)), ('moss', f['moss']), ('fuzz', f['fuzz']),
                      ('crack', crack), ('lash', lash), ('lid', bulge), ('nostril', fm['nostril']), ('clawm', claw_mask(co, 1.04)), ('claw_u', cl[:, 1]), ('lichen', lichen),
                      ('cover', z['cover'])):
        S.add_attr(ob, name, np.asarray(val, np.float64))
    _LAST.clear()
    _LAST.update({'n': len(co), 'plate': f['plate'], 'moss': f['moss'], 'pid': f['pid'], 'top': f['top'], 'crack': crack,
                  'co': co, 'groove': fm['groove'], 'nostril': fm['nostril']})
    coat = z['cover'] > 0.6
    C.log(f'carve: on the coat {float((f["plate"][coat] > 0.5).mean()) * 100:.0f}% stone, {float((f["moss"][coat] > 0.5).mean()) * 100:.0f}% moss')
    C.log(f'carve: {len(plates["c"])} cobbles, {int((f["plate"] > 0.5).sum())} of {len(co)} vertices on a stone, '
          f'{int((f["moss"] > 0.5).sum())} in the moss; height up to {float(disp.max()) * 1000:.1f} mm')


def carve_low(ob: bpy.types.Object) -> None:
    """The low body takes the same cobbles at 0.85 and the moss mound (no fuzz), so the stones reach the silhouette and
    the bake's cage (2 cm out, 5 cm in) still finds them."""
    smooth_front(ob)
    co, vn = S.mesh_arrays(ob)
    z = zones(co, vn)
    plates = make_plates(co, vn)
    f = coat_field(co, vn, plates, z, LOW_SCALE, False)
    cd, cl = claw_local_best(co)
    claw_flat = 0.0 * cd
    S.set_positions(ob, co + vn * (f['h'] + eye_socket(co) + claw_flat)[:, None])
    C.log(f'carve_low: {int((f["plate"] > 0.5).sum())} of {len(co)} vertices on a stone, height up to {float(f["h"].max()) * 1000:.1f} mm')


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


def _lid_masks(nb: NB, rx, ry, side):
    """The heavy upper lid (lower toward the nose: the grumpy look) and the lower lid, painted on the lens: 0..1 each,
    and both edges' heights."""
    inner = nb.smooth(nb.math('MULTIPLY', nb.math('MULTIPLY', rx, side), -1.0), 0.0, 0.9)
    # round 2: the lid above the iris (its top and a rim of white show): gentle, not scowling
    edge = nb.math('ADD', nb.math('ADD', 0.76, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', rx, rx)), 0.08)),
                   nb.math('MULTIPLY', inner, -0.05))
    upper = nb.smooth(nb.math('SUBTRACT', ry, edge), -0.015, 0.015)
    low_edge = nb.math('ADD', -0.74, nb.math('MULTIPLY', nb.math('MULTIPLY', rx, rx), 0.14))
    lower = nb.smooth(nb.math('SUBTRACT', low_edge, ry), -0.02, 0.02)
    return upper, lower, edge, low_edge


def eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """Small, deep-set amber eyes (4-details panel 2, 3-faces neutral): an almond opening under a heavy upper lid that
    crosses the top of the iris (painted on the lens in the hide's colour, with a dark lash line and a soft shadow),
    a warm white at the corners, a big amber iris with fine streaks, a dark limbal ring and a deeper orange ring round the
    big black pupil, and two crisp catchlights toward the key light. The rough pass keeps the lids matte."""
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    upper, lower, edge, low_edge = _lid_masks(nb, rx, ry, side)
    lid = nb.math('MAXIMUM', upper, lower)
    if rough_pass:
        rr = nb.math('ADD', 0.05, nb.math('MULTIPLY', lid, 0.75))
        cc = nb.math('SUBTRACT', 1.0, lid)
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, rr, cc), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    amber = PALETTE['eye']
    # the iris sits a touch toward the nose and high, so the lid crosses its top
    ix = nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.04))
    iy = nb.math('SUBTRACT', ry, 0.03)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.68), nb.math('DIVIDE', iy, 0.8), 0.0))
    deep = C.mix_hex(amber, '#C2641A', 0.55)
    iris = nb.ramp(ri, [(0.0, C.lin('#0B0806')), (0.42, C.lin('#0B0806')), (0.47, C.lin(C.shade_hex(deep, 0.75))),
                        (0.56, C.lin(deep)), (0.72, C.lin(amber)), (0.86, C.lin(C.mix_hex(amber, '#FFE08A', 0.25))),
                        (0.95, C.lin(C.mix_hex(amber, '#8A4E10', 0.55))), (1.0, C.lin('#4A2A10')), (1.04, C.lin('#EFE8DC')),
                        (1.7, C.lin('#EFE8DC'))])
    ang = nb.math('ARCTAN2', iy, ix)
    streak = nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 23.0)), 0.5)
    streak = nb.math('MULTIPLY', nb.math('ADD', streak, 0.5), nb.math('MULTIPLY', nb.smooth(ri, 0.48, 0.6), nb.smooth(ri, 0.98, 0.9)))
    c = nb.mix(nb.math('MULTIPLY', streak, 0.22), iris, nb.rgb(C.lin(C.mix_hex(amber, '#FFF0B0', 0.4))))
    # the white shades toward the corners
    shade = nb.math('MULTIPLY', nb.smooth(nb.vmath('LENGTH', nb.comb(rx, ry, 0.0)), 0.55, 1.0), 0.35)
    c = nb.mix(nb.math('MULTIPLY', shade, nb.smooth(ri, 1.0, 1.06)), c, nb.rgb(C.lin('#B8AC9F')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.18), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.14), 1.15), 0.0)), 0.15, 0.12)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.2), nb.math('ADD', ry, 0.3), 0.0)), 0.06, 0.045)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    # the upper lid's soft shadow on the eye, then the lids (hide) with a dark lash line at the upper edge
    sh = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ry, edge), -0.3, 0.0), 0.45)
    c = nb.mix(sh, c, nb.rgb(C.lin('#2A2420')), blend='MULTIPLY')
    lid_col = C.shade_hex(PALETTE['body'], 0.86, cool=0.01)
    c = nb.mix(upper, c, nb.rgb(C.lin(lid_col)))
    c = nb.mix(lower, c, nb.rgb(C.lin(C.mix_hex(PALETTE['body'], PALETTE['belly'], 0.3))))
    lash = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ry, edge), -0.07, -0.01), nb.smooth(nb.math('SUBTRACT', ry, edge), 0.06, 0.01))
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    lline = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', low_edge, ry), -0.06, -0.01), nb.smooth(nb.math('SUBTRACT', low_edge, ry), 0.04, 0.0))
    c = nb.mix(nb.math('MULTIPLY', lline, 0.6), c, nb.rgb(C.lin(LASH_HEX)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= the tusks (rigid props)
# round 2: stubbier (about 20% shorter, the width about 0.6 of the visible length), a slight outward tilt
# round 3: ~25% shorter and thicker (width ~0.6 of the visible length), smooth ivory (no rings), at the mouth corners
TUSK = {'base': hp((0.27, -0.99, 1.05)), 'tip': hp((0.294, -1.02, 1.14)), 'bend': hr((0.006, 0.008, 0.0)), 'r': hr((0.042, 0.025)),
        'flat': 0.88, 'rings': False}


def preview_prop_colour(name: str) -> str:
    """The shape preview's colour for a prop: the tusks' ivory."""
    return TUSK_HEX[0]


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    return [K.build_tusk(f'{tag}_tusk{"L" if s > 0 else "R"}', s, TUSK, high) for s in (1, -1)]


# ============================================================================= paint
def light_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """0 hide … 1 the pale stone: the lower jaw and chin, the throat and chest, the belly between the legs."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    jaw = z['head'] * smooth(0.012, -0.012, zz - z['mouth_z']) * smooth(80, 70, np.abs(z['theta'])) * smooth(hy(-0.66), hy(-0.74), y)
    jaw = np.where(z['ear'], 0.0, jaw)
    w = 0.29 + 0.04 * smooth(0.6, 0.35, zz)
    throat = (~z['head'] | (zz < 0.9)) * smooth(-0.52, -0.6, y) * smooth(w + 0.01, w - 0.01, ax) * smooth(1.0, 0.92, zz)
    zb = np.interp(y, [-0.6, -0.3, 0.0, 0.3, 0.55], [0.5, 0.44, 0.4, 0.42, 0.46])
    belly = z['torso'] * ~z['leg'] * smooth(zb + 0.012, zb - 0.012, zz) * smooth(0.37, 0.34, ax)
    m = np.maximum(np.maximum(jaw, throat), belly)
    m = np.where(z['leg'] & (zz < 0.35), m * smooth(0.25, 0.35, zz), m)
    return np.clip(m * (1.0 - z['cover']), 0.0, 1.0)


_PAINT: dict = {}


def _paint_inputs(ob: bpy.types.Object) -> dict:
    """Per vertex, once per source: the zones at the roots and the carved attributes."""
    if ob.name in _PAINT:
        return _PAINT[ob.name]
    root = S.attr_array(ob, 'root').astype(np.float64)
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    z = zones(root)
    get = lambda nm, d=0.0: S.attr_array(ob, nm).astype(np.float64) if nm in ob.data.attributes else np.full(len(root), d)  # noqa: E731
    I = {'root': root, 'kind': kind, 'tpos': tpos, 'z': z, 'light': light_mask(root, z), 'plate': get('plate'),
         'moss': get('moss'), 'rim': get('plate_rim', 1.0), 'top': get('plate_top'), 'pid': get('plate_id', -1.0),
         'fuzz': get('fuzz'), 'crack': get('crack'), 'claw': claw_mask(root), 'claw_u': get('claw_u', 0.0), 'mottle': K.fbm(root, 1 / 0.14, 81, 3),
         'mottle2': K.fbm(root, 1 / 0.05, 83, 2)}
    _PAINT[ob.name] = I
    return I


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    """Per vertex of a body source: 'paint' (linear RGB), 'shade' (1 on the body) and 'rough' (1, roughness, clearcoat).
    The crisp details (lichen, specks, the nose, the mouth, the lids, the granite) are added per pixel by
    `body_material`."""
    col = colours(pal)
    I = _paint_inputs(ob)
    z = I['z']
    k = len(I['root'])
    granite = bool(pal.get('granite'))
    # the hide: mottled a little, lifted on the brows and the tops of the legs, dark in the cracks
    hide = np.tile(lin(col['hide']), (k, 1)) * (1.0 + 0.06 * I['mottle'] + 0.03 * I['mottle2'])[:, None]
    lt = I['light'][:, None]
    rgb = hide * (1 - lt) + lin(col['light'])[None] * (1.0 + 0.04 * I['mottle'])[:, None] * lt
    ck = (I['crack'] * 0.88)[:, None]
    dark = lin(col['hide_dark']) * (1 - lt) + lin(col['light_dark']) * lt
    rgb = rgb * (1 - ck) + dark * ck
    # the stones: a tone per stone, lighter worn crowns, darker chipped rims
    pid = np.round(I['pid']).astype(np.int64)
    ph = U.plate_hash(pid, 5)
    ph2 = U.plate_hash(pid, 9)
    stone = lin(col['stone'])[None] * (0.74 + 0.42 * ph)[:, None]
    warm = (ph2 - 0.5)[:, None] * 0.16
    stone = stone * (1.0 + np.array([[1.0, 0.2, -0.8]]) * warm)
    stone = stone * (1 - 0.45 * I['top'][:, None]) + lin(col['stone_top'])[None] * 0.45 * I['top'][:, None] * (0.9 + 0.2 * ph[:, None])
    rimk = (smooth(0.5, 1.0, I['rim']) * 0.35)[:, None]
    stone = stone * (1 - rimk) + lin(col['stone_dark'])[None] * rimk
    if granite:
        stone = lin(col['stone'])[None] * (0.92 + 0.16 * ph)[:, None]
    pk = I['plate'][:, None]
    rgb = rgb * (1 - pk) + stone * pk
    # the moss: deep green in the grooves, yellow-green on the tufts' tips (the fuzz)
    tip = smooth(-0.45, 0.35, I['fuzz'])[:, None]
    moss = lin(col['moss_deep'])[None] * (1 - tip) + lin(col['moss'])[None] * tip
    moss = moss * (1 - 0.4 * smooth(0.5, 1.0, I['fuzz'])[:, None]) + lin(col['moss_tip'])[None] * 0.4 * smooth(0.5, 1.0, I['fuzz'])[:, None]
    moss = moss * (1.0 + 0.1 * I['mottle2'])[:, None]
    mk = I['moss'][:, None]
    rgb = rgb * (1 - mk) + moss * mk
    # round 3: crisp contact shadow where a stone meets the moss (moss lying on a stone's foot, and the stone's foot)
    contact = np.clip(I['moss'] * (I['pid'] >= 0) * 0.5 + I['plate'] * smooth(0.82, 1.0, I['rim']) * 0.35, 0.0, 0.6)[:, None]
    rgb = rgb * (1.0 - contact)
    # the moss strands (lying locks): deep green at the root, yellow-green at the tip
    lock = I['kind'] > 0.5
    if lock.any():
        t = I['tpos'][lock][:, None]
        lr = (K.hash3(np.floor(I['root'][lock] / 0.003).astype(np.int64), 97) - 0.5)[:, None]
        cl = K.fbm(I['root'][lock], 1 / 0.03, 99, 2)[:, None]          # some clumps olive, some yellow-green
        mc = lin(col['moss_deep'])[None] * (1 - t) + lin(col['moss'])[None] * t
        mc = mc * (1 - 0.45 * smooth(0.55, 1.0, t)) + lin(col['moss_tip'])[None] * 0.45 * smooth(0.55, 1.0, t)
        if granite:
            rgb[lock] = mc * (1.0 + 0.05 * lr)
        else:
            mc = mc * (1.0 + 0.18 * cl)
            olive = smooth(-0.1, -0.6, cl)
            mc = mc * (1 - 0.35 * olive) + lin(C.mix_hex(col['moss_deep'], '#5E6A2E', 0.5))[None] * 0.35 * olive
            rgb[lock] = mc * (1.0 + 0.16 * lr)
    # the ears' insides, the claws, the soles
    ein = (z['ear_in'] * smooth(0.74, 0.5, z['ear_r']) * (1 - I['plate']) * (1 - I['moss']))[:, None]
    rgb = rgb * (1 - ein) + lin(col['ear_in'])[None] * ein
    cl = I['claw'][:, None]
    tipk = smooth(0.1, -0.75, I['claw_u'])[:, None]
    cut = (smooth(0.35, 0.8, I['claw_u']) * 0.55)[:, None]
    ctone = lin('#76685A')[None] * (1 - tipk) + lin('#8E7F6C')[None] * tipk      # round 5: warm olive-brown-grey stone
    ctone = ctone * (1 - cut) + lin('#4A4238')[None] * cut
    rgb = rgb * (1 - cl) + ctone * cl
    # roughness and clear coat: matte hide, slightly glossier stones, soft moss, glossy claws and nose
    rough = np.full(k, 0.84) - 0.06 * I['light']
    coat = np.zeros(k)
    rough = rough * (1 - I['plate']) + (0.64 - 0.08 * I['top']) * I['plate']
    coat = coat * (1 - I['plate']) + 0.12 * I['plate']
    mz = np.maximum(I['moss'], (I['kind'] > 0.5) * 1.0)
    rough = rough * (1 - mz) + 0.9 * mz
    coat = coat * (1 - mz)
    nose = ell_soft(I['root'], tuple(NOSE_C), tuple(r * 1.1 for r in NOSE_R), 0.1)
    gl = np.maximum(I['claw'], nose)
    rough = rough * (1 - gl) + np.where(I['claw'] > nose, 0.6, 0.6) * gl       # round 5: satin, no coat (not pewter)
    coat = coat * (1 - gl) + np.where(I['claw'] > nose, 0.0, 0.08) * gl
    if granite:
        # round 4: polished granite plates (crisp highlights, a clear coat), the hide a touch smoother; seams stay matte
        pk = I['plate']
        # round 5: a matte base under a full coat: the coat's highlight follows the mesh (one soft dome), the base's
        # bumpy normal no longer breaks it into crumpled foil
        rough = rough * (1 - pk) + 0.55 * pk
        coat = coat * (1 - pk) + 0.3 * pk
        hk = (1 - pk) * (1 - mz) * (1 - gl)
        rough = rough - 0.1 * hk
    return {'paint': rgb, 'shade': np.ones(k), 'rough': np.stack([np.ones(k), rough, coat], axis=1)}


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
    """'paint' (base), 'rough', 'shade' and, per variant, `U.variant_attr(vid, ID)` on every source; the tusks' ivory."""
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'shade', a['shade'])
        for vid, pal in VARIANTS.items():
            va = paint_arrays(ob, pal)
            S.set_colour_attr(ob, U.variant_attr(vid, ID), va['paint'])
            if _short(vid) in VARIANT_ORM:
                S.set_colour_attr(ob, f'rough_{_short(vid)}', va['rough'])
    for ob in props:
        rgb, rc = K.tusk_paint(ob, *TUSK_HEX)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        for vid in VARIANTS:
            S.set_colour_attr(ob, U.variant_attr(vid, ID), rgb)
            if _short(vid) in VARIANT_ORM:
                S.set_colour_attr(ob, f'rough_{_short(vid)}', rc)      # every source needs it, or the bake uses 'rough'


def _short(vid: str) -> str:
    return vid[:-len(ID) - 1] if vid.endswith('-' + ID) else vid


def _mell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def body_material(name: str, attr: str, pal: dict, marks=None) -> bpy.types.Material:
    """Emission = the painted attribute, with the per-pixel detail: the hide's fine specks and a few orange lichen
    dots; the stones' pale lichen crusts, orange lichen and dark pits (granite: black, white and rose speckles); the
    moss's strands; the claws' pale scratches; the nose with its nostrils, the smile line and the closed lids."""
    col = colours(pal)
    granite = bool(pal.get('granite'))
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 0.5)
    c = nb.attribute(attr).outputs['Color']
    plate = nb.attribute('plate').outputs['Fac']
    # the moss strands (lying locks) count as moss
    moss = nb.math('MAXIMUM', nb.attribute('moss').outputs['Fac'], nb.math('SUBTRACT', 1.0, is_body))
    hide = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, plate), nb.math('SUBTRACT', 1.0, moss))
    hide = nb.math('MULTIPLY', hide, nb.math('SUBTRACT', 1.0, nb.attribute('clawm').outputs['Fac']))   # no specks on the nails
    # the hide: fine light and dark specks (weathered rock), a few orange lichen dots
    sp = nb.noise(pos, 210.0, 2.0, 0.6)
    light_sp = nb.math('MULTIPLY', nb.smooth(sp, 0.6, 0.7), hide)
    c = nb.mix(nb.math('MULTIPLY', light_sp, 0.45), c, nb.rgb(C.lin(col['hide_lift'])))
    dark_sp = nb.math('MULTIPLY', nb.smooth(sp, 0.36, 0.28), hide)
    c = nb.mix(nb.math('MULTIPLY', dark_sp, 0.5), c, nb.rgb(C.lin(col['hide_dark'])))
    mot = nb.noise(pos, 26.0, 3.0, 0.6)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(mot, 0.5, 0.7), hide), 0.22), c, nb.rgb(C.lin(col['hide_dark'])))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(mot, 0.5, 0.3), hide), 0.18), c, nb.rgb(C.lin(col['hide_lift'])))
    # round 2: tiny white and ochre specks on the hide (4-details hide swatch)
    wsp = nb.smooth(nb.voronoi(nb.vmath('ADD', pos, (2.1, 0.4, 1.7)), 48.0), 0.075, 0.045)
    c = nb.mix(nb.math('MULTIPLY', wsp, nb.math('MULTIPLY', hide, 0.72)), c, nb.rgb(C.lin('#D2D3CC')))
    if col['lichen_orange']:
        dots = nb.smooth(nb.voronoi(pos, 34.0), 0.07, 0.04)
        patch = nb.smooth(nb.noise(pos, 3.0, 2.0, 0.5), 0.4, 0.5)
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', dots, patch), nb.math('MULTIPLY', hide, 0.7)), c, nb.rgb(C.lin(col['lichen_orange'])))
    # the stones
    if granite:
        # the variant picture: speckled granite stones, a plain grey hide (only a faint trace of speckle on it)
        stone_w = nb.math('MAXIMUM', plate, nb.math('MULTIPLY', hide, 0.22))     # round 5: the hide speckled too
        # round 4: dense mixed grains as in the picture (black, white, a warm tan-pink), a coarse and a finer set,
        # their lookup warped so the grains are ragged, not cell polygons (the round-3 "popcorn" was too fine and sparse)
        wn = nb.new('ShaderNodeTexNoise')
        nb.put(wn.inputs['Vector'], pos)
        wn.inputs['Scale'].default_value = 45.0
        wn.inputs['Detail'].default_value = 2.0
        wpos = nb.vmath('ADD', pos, nb.vmath('MULTIPLY', nb.vmath('SUBTRACT', wn.outputs['Color'], (0.5, 0.5, 0.5)), (0.012, 0.012, 0.012)))
        for scale, k, (pb, pw, pp), off in ((70.0, 1.0, (0.8, 0.88, 0.94), (0.37, 1.3, 0.71)), (150.0, 0.85, (0.78, 0.87, 0.94), (2.1, 0.4, 1.9))):
            vo = nb.new('ShaderNodeTexVoronoi', feature='F1')
            nb.put(vo.inputs['Vector'], nb.vmath('ADD', wpos, off))
            vo.inputs['Scale'].default_value = scale
            vo.inputs['Randomness'].default_value = 1.0
            cr, cg, cb = nb.sep_rgb(vo.outputs['Color'])[:3]
            w = nb.math('MULTIPLY', stone_w, k)
            c = nb.mix(nb.math('MULTIPLY', nb.smooth(cr, pb, pb + 0.012), w), c, nb.rgb(C.lin('#24242A')))
            c = nb.mix(nb.math('MULTIPLY', nb.smooth(cg, pw, pw + 0.012), w), c, nb.rgb(C.lin('#D4D4D8')))
            c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(cb, pp, pp + 0.012), w), 0.9), c, nb.rgb(C.lin('#A0806E')))
    else:
        # round 2: the stones mottled mid-to-dark grey (4-details panel 5)
        smot = nb.noise(pos, 16.0, 4.0, 0.6)
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(smot, 0.48, 0.66), plate), 0.28), c, nb.rgb(C.lin(col['stone_dark'])))
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(smot, 0.46, 0.3), plate), 0.32), c, nb.rgb(C.lin(col['stone_top'])))
        # round 4: a finer grey mottle inside each stone (4-details panel 5's grainy stone)
        fmot = nb.noise(nb.vmath('ADD', pos, (0.9, 2.3, 0.4)), 55.0, 3.0, 0.6)
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(fmot, 0.52, 0.66), plate), 0.3), c, nb.rgb(C.lin(col['stone_dark'])))
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(fmot, 0.44, 0.32), plate), 0.22), c, nb.rgb(C.lin(col['stone_top'])))
        # round 3: crusty pale lichen over ~15-30% of each stone's upper face (it lifts the tops above the hide's value)
        # round 4: the lichen is carved (fine ragged patches on the upper faces), mottled inside
        lich = nb.math('MULTIPLY', nb.attribute('lichen').outputs['Fac'], plate)
        c = nb.mix(nb.math('MULTIPLY', lich, 0.8), c, nb.rgb(C.lin(col['lichen_pale'])))
        crusty = nb.math('MULTIPLY', lich, nb.smooth(nb.noise(pos, 140.0, 2.0, 0.6), 0.58, 0.7))
        c = nb.mix(nb.math('MULTIPLY', crusty, 0.45), c, nb.rgb(C.lin('#8F9488')))
        # some crusts yellow-ochre (4-details panel 5), patch by patch
        ochre = nb.math('MULTIPLY', lich, nb.smooth(nb.noise(nb.vmath('ADD', pos, (3.1, 0.7, 2.2)), 12.0, 2.0, 0.5), 0.6, 0.66))
        c = nb.mix(nb.math('MULTIPLY', ochre, 0.4), c, nb.rgb(C.lin('#A08C50')))
        # ochre and orange lichen rings (small rosettes with a paler centre)
        vr = nb.voronoi(nb.vmath('ADD', pos, (1.3, 0.2, 0.7)), 26.0)
        ring = nb.math('MULTIPLY', nb.smooth(vr, 0.07, 0.1), nb.smooth(vr, 0.17, 0.13))
        rpatch = nb.smooth(nb.noise(nb.vmath('ADD', pos, (0.5, 2.0, 0.3)), 4.0, 2.0, 0.5), 0.36, 0.46)
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', ring, rpatch), nb.math('MULTIPLY', plate, 0.95)), c, nb.rgb(C.lin('#B98B34')))
        # the crusts' edges: little islands of pale specks around each crust
        isl = nb.math('MULTIPLY', nb.smooth(nb.noise(pos, 90.0, 1.0, 0.5), 0.66, 0.7), nb.math('MULTIPLY', plate, nb.attribute('plate_top').outputs['Fac']))
        c = nb.mix(nb.math('MULTIPLY', isl, 0.5), c, nb.rgb(C.lin(col['lichen_pale'])))
        orange = nb.smooth(nb.voronoi(nb.vmath('ADD', pos, (0.3, 0.9, 0.1)), 24.0), 0.2, 0.12)     # final: bigger orange splotches
        opatch = nb.smooth(nb.noise(nb.vmath('ADD', pos, (2.0, 0.0, 1.0)), 5.0, 2.0, 0.5), 0.42, 0.52)
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', orange, opatch), nb.math('MULTIPLY', plate, 0.9)), c, nb.rgb(C.lin(col['lichen_orange'])))
        pits = nb.math('MULTIPLY', nb.smooth(nb.noise(pos, 260.0, 1.0, 0.5), 0.33, 0.27), plate)
        c = nb.mix(nb.math('MULTIPLY', pits, 0.45), c, nb.rgb(C.lin(col['stone_dark'])))
    # the moss: fine strands of lighter and deeper green
    st = nb.noise(pos, 320.0, 2.0, 0.65)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(st, 0.54, 0.64), moss), 0.55), c, nb.rgb(C.lin(col['moss_tip'])))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(st, 0.4, 0.3), moss), 0.35), c, nb.rgb(C.lin(col['moss_deep'])))
    # the claws: pale scratches along them
    claw = nb.attribute('clawm').outputs['Fac']
    # round 3: fine dark hairline cracks in the nails
    ve = nb.new('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE')
    nb.put(ve.inputs['Vector'], pos)
    ve.inputs['Scale'].default_value = 16.0
    few = nb.smooth(nb.noise(nb.vmath('ADD', pos, (4.0, 1.0, 2.0)), 9.0, 2.0, 0.5), 0.5, 0.56)
    hair = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(ve.outputs['Distance'], 0.012, 0.004), claw), few)
    c = nb.mix(nb.math('MULTIPLY', hair, 0.15), c, nb.rgb(C.lin('#B8AC9C')))      # round 5: white veins
    scr = nb.noise(nb.vmath('MULTIPLY', pos, (60.0, 8.0, 60.0)), 3.0, 3.0, 0.7)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(scr, 0.66, 0.72), claw), 0.35), c, nb.rgb(C.lin('#B5A792')))
    # the nose (a crisp edge), its nostrils and the smile line
    nose = nb.math('MAXIMUM', _mell(nb, pos, tuple(NOSE_C), tuple(r * 1.05 for r in NOSE_R), 0.06), _mell(nb, pos, NOSE2[0], tuple(r * 1.1 for r in NOSE2[1]), 0.08))
    c = nb.mix(nb.math('MULTIPLY', nose, is_body), c, nb.rgb(C.lin(col['nose'])))
    hl = nb.math('MULTIPLY', _mell(nb, pos, hp((0.0, -1.11, 1.2)), hr((0.06, 0.03, 0.02)), 0.6), 0.08)
    c = nb.mix(hl, c, nb.rgb(C.lin('#7C7E88')))
    nos = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('nostril').outputs['Fac'], 1.6, clamp=True), is_body)
    c = nb.mix(nos, c, nb.rgb(C.lin('#141317')))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(col['mouth'])))
    lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
    c = nb.mix(nb.math('MULTIPLY', lid, 0.18), c, nb.rgb((0.0, 0.0, 0.0)))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """Flat colours for the shape preview: hide, pale stone, stones (a tone each), moss, claws, ear insides, nose."""
    col = colours(PALETTE)
    if _LAST.get('n') == len(co):
        root = _LAST['co']
        plate, moss, pid = _LAST['plate'], _LAST['moss'], _LAST['pid']
    else:
        root = co
        plate = moss = np.zeros(len(co))
        pid = np.full(len(co), -1)
    z = zones(root)
    lt = light_mask(root, z)[:, None]
    rgb = lin(col['hide'])[None] * (1 - lt) + lin(col['light'])[None] * lt
    ph = U.plate_hash(np.asarray(pid, np.int64), 5)[:, None]
    stone = lin(col['stone'])[None] * (0.8 + 0.4 * ph)
    rgb = rgb * (1 - plate[:, None]) + stone * plate[:, None]
    rgb = rgb * (1 - moss[:, None]) + lin(col['moss'])[None] * moss[:, None]
    ein = (z['ear_in'] * smooth(0.74, 0.5, z['ear_r']))[:, None]
    rgb = rgb * (1 - ein) + lin(col['ear_in'])[None] * ein
    cl = claw_mask(root)[:, None]
    rgb = rgb * (1 - cl) + lin(col['claw'])[None] * cl
    nose = ((in_ellipsoid(root, tuple(NOSE_C), NOSE_R) < 1.04) | (in_ellipsoid(root, NOSE2[0], NOSE2[1]) < 1.08))[:, None]
    rgb = np.where(nose, lin(col['nose'])[None], rgb)
    if _LAST.get('n') == len(co):
        g = np.clip(_LAST['groove'] + _LAST['nostril'], 0, 1)[:, None]
        rgb = rgb * (1 - g) + lin(col['mouth'])[None] * g
    return rgb


# ============================================================================= the rig (plans/quadruped.py)
def rig_p() -> dict:
    c, _ax, _up, n = ear_frame(1)
    return {
        'hip': (0.0, 0.42, 0.74),
        'chest': (0.0, -0.38, 0.80),
        'head_c': tuple(HEAD_C),
        'head_r': HEAD_R,
        'ear_base': tuple(map(float, c - n * 0.03)),
        'ear_dir': tuple(map(float, norm((n + v3((0.0, 0.0, 0.9)))[None])[0])),
        'ear_len': 0.13,
        'tail_base': TAIL_POINTS[0],
        'tail_dir': tuple(map(float, norm((v3(TAIL_POINTS[-1]) - v3(TAIL_POINTS[0]))[None])[0])),
        'tail_len': float(np.linalg.norm(v3(TAIL_POINTS[-1]) - v3(TAIL_POINTS[0]))),
        'tail_bones': 2,
        'tail_points': TAIL_POINTS,
        'legs': {leg: (lx, ly, LEG_TOP[leg[0]]) for leg, (lx, ly) in LEGS.items()},
        'knee_back': 0.045,
        'ankle_z': 0.12,
        'foot_len': 0.22,
        'leg_radius': 0.2,
        'stride': 0.2,
        'strike_style': 'slam',               # 5-poses attack: rears up on the hind legs, slams both front paws down
        # round 5 (5-poses attack): rears higher with both forepaws over the head; lands them far forward and wide
        'slam_rear': 58.0, 'slam_paws': (-140.0, -10.0, -20.0), 'slam_ahead': 0.42, 'slam_wide': 24.0, 'slam_squash': 0.06,
        'slam_dip': -3.0,
        'jaw': {'head': hp((0.0, -0.86, 1.06)), 'tail': hp((0.0, -1.12, 1.0))},
        'props': [{'name': 'tusks', 'parent': 'jaw', 'head': hp((0.0, -0.98, 1.0)), 'tail': hp((0.0, -0.98, 1.13))}],
    }


# the ears and the eyes' bones never take heat weights (the ears get theirs from body_weight_regions)
MERGE_INTO_HEAD = ('eye.L', 'eye.R', 'ear.L.1', 'ear.L.2', 'ear.R.1', 'ear.R.2')   # round 5: the jaw moves its skin


def ear_zone(p: np.ndarray):
    E = ear_lookup(p)
    return E['on'], np.clip(E['r'], 0, 1)


def ear_weights(p: np.ndarray, u: np.ndarray) -> dict[str, np.ndarray]:
    """A stiff little cup: the root stays with the head, the rim follows ear.1, a touch of ear.2 at the top."""
    w1 = smooth(0.15, 0.6, u) * 0.8
    w2 = smooth(0.6, 1.0, u) * 0.2
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    z = zones(co)
    out = []
    E = ear_lookup(co)
    for s, tag in ((1, 'L'), (-1, 'R')):
        on = E['on'] & (E['s'] == s)
        if on.any() and f'ear.{tag}.1' in names:
            w = ear_weights(co[on], np.clip(E['r'][on], 0, 1))
            out.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    if z['tail'].any():
        out.append((z['tail'], U.chain_weights(co[z['tail']], TAIL_POINTS, ['tail.1', 'tail.2'], 'hips')))
    # round 5: the lower jaw (below the mouth line, the chin and the jaw's front) rides the jaw bone
    if 'jaw' in names:
        yy, zz = co[:, 1], co[:, 2]
        wj = (smooth(z['mouth_z'] + 0.003, z['mouth_z'] - 0.006, zz) * smooth(hy(-0.72), hy(-0.84), yy)
              * smooth(hz(0.74), hz(0.84), zz) * (1.0 - z['ear']))
        mj = z['head'] & (wj > 0.002)
        if mj.any():
            out.append((mj, {'jaw': wj[mj], 'head': 1.0 - wj[mj]}))
    # the claws ride their foot bones rigidly
    for leg, m in z['legs'].items():
        cl = m & (claw_mask(co, 1.15) > 0.3)
        if cl.any() and f'foot.{leg}' in names:
            out.append(U.rigid(cl, f'foot.{leg}'))
    return out


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    return [U.rigid(np.ones(len(co), bool), 'prop.tusks' if 'prop.tusks' in names else 'head')]


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """0..1 per low-body vertex, how much to protect it from the collapse: the eyes, the nose and the mouth line fully,
    the rest of the face, the claws and the ears lightly. Build 1: protecting the whole (big) face, the claws and the
    ears at 0.6-1 took ~16% of the vertices, and the weighted collapse spent the entire unprotected body (the legs and
    the back half vanished)."""
    z = zones(co)
    mouth = (np.abs(co[:, 2] - z['mouth_z']) < 0.012) & z['head'] & (co[:, 1] < hy(-0.78)) & (np.abs(z['theta']) < 72)
    keep = (z['eye_d'] < 0.085) * 1.0 + z['nose'] * 0.8 + mouth * 0.7 + z['face'] * 0.12 + z['claw'] * 0.25 + z['ear'] * 0.25
    return np.clip(keep, 0, 1)


def uv_smooth_mask(co: np.ndarray) -> np.ndarray:
    """UV_SMOOTH's strength: the cobbled coat smooths fully, the legs and body partly, the face and ears not at all."""
    z = zones(co)
    m = np.clip(z['cover'], 0.0, 1.0) * np.where(z['head'], 0.2, 0.45)
    m = m * (1.0 - light_mask(co, z))         # final: the throat and chest keep their own UVs (stretched streaks)
    m = np.maximum(m, 0.3 * z['torso'])
    # round 2: the legs and the tail keep their own shape (smoothing them stretched the leg columns' texture and
    # crushed the tail's island into a chrome-smooth spot)
    m = np.where(z['face'] | z['ear'] | z['jaw'] | z['leg'] | z['tail'], 0.0, m)
    return m


CLIP_CALM = {
    '*': {'ear': 0.5, 'tail': 0.6},
    'ko': {'ear': 0.2, 'tail': 0.4},
    'hit_heavy': {'ear': 0.3, 'tail': 0.5},
    'win': {'ear': 0.4},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the amber iris, the big pupil, the white, two catchlights and the '
             'heavy upper lid\'s line baked into the body atlas; the stone brows, the nose, the wide smile and the tusks '
             '(lo_props, rigid on prop.tusks) are sculpted. No face sheet and no morphs: expressions in clips\' `faces` '
             'are hints only. Blinking scales the blink bones (play `blink` over any clip): each lens squashes onto the '
             'closed lid\'s lash line and sinks into the head, showing the closed lid sculpted and painted under it.')

REVIEW = {
    'centre': (0.0, -0.12, 0.76),
    'size': 2.75,
    'head': (hp((0.0, -0.86, 1.16)), 1.3),
}
