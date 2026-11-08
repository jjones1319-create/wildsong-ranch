"""Stripeneck at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9; tools/blender/monsters/breeds/RECIPE.md).

A lanky giraffe–zebra grazer, two Puddlepups tall to the tips of its ossicones (chatgpt/monsters/31-stripeneck/: the
card decides the parts, the pictures the shapes, CONTENT §2.2 #31 the colours):
  - giraffe at the front (head, neck, chest, shoulders, front legs): golden tan with rounded chestnut patches outlined
    by thin cream lines; zebra at the back (rump, haunches, back legs, tail): cream with bold charcoal stripes curving
    round the body; a soft wavy blend round the middle where the patches stretch out into stripes (stripeneck_coat);
  - a long, thick neck (a 4-bone chain, `neck_bones`) holding up a round head with a broad, soft cream muzzle, big
    friendly eyes with long lashes (lash props on the blink bones), dark brows and a blush;
  - two short fur-covered ossicones topped with charcoal pom-pom tufts, big upright leaf ears lined pink;
  - a short upright brush mane in charcoal and cream bands from a forelock between the ossicones down the back of the
    neck to the withers (one swept crest, the bands painted on it; stripeneck_parts);
  - four long, chunky legs with fluffy fetlocks and neat dark cloven hooves (plan option `hooves`);
  - a striped zebra tail ending in a long, wavy charcoal tuft (5 tail bones);
  - short, dense velvet fur (fine lying locks baked into the atlas; short cards only where the outline wants fuzz).

Metres; the monster faces −Y, Z is up, +X is its left. Palette CONTENT §2.2 #31: #E3B36A / #F4EBDA / #2F2B30
(patches #8E4F2A, hooves #4A3A30) / #2B1E16. Secret variant Ezgi (src/art/monster/variants.ts; the card's extras: patches
#3B3F73).
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
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3
from monsters.breeds import stripeneck_coat as K
from monsters.breeds import stripeneck_parts as SP

ID = 'stripeneck'
LOOK = 'stripeneck-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 300               # 2 × Puddlepup to the tips of the ossicones (PROMPTS.md: tall)

PALETTE = {'body': '#E3B36A', 'belly': '#F4EBDA', 'accent': '#2F2B30', 'eye': '#2B1E16', 'patch': '#8E4F2A', 'hoof': '#4A3A30'}
# Ezgi's hooves: the variant picture paints them a dark indigo (the card's text says unlisted parts keep their colour; the
# picture wins on where colours go): the midnight accent lifted a little toward the lilac
VARIANTS = {'ezgi-stripeneck': {'body': '#7A7DB8', 'belly': '#E6E4F4', 'accent': '#1F2140', 'eye': '#2B1E16', 'patch': '#3B3F73',
                                'hoof': C.mix_hex('#1F2140', '#E6E4F4', 0.1)}}

# colours CONTENT has none for (the card's pictures suggest them; never sampled)
NOSE_HEX = '#5A3A2E'
MOUTH_HEX = '#5E3A30'
LINING_HEX = '#E8A3A0'
BLUSH_HEX = '#EE9A92'
LASH_HEX = '#231A1C'


def colours(pal: dict) -> dict:
    tan, cream, char = pal['body'], pal['belly'], pal['accent']
    patch = pal.get('patch', '#8E4F2A')
    hoof = pal.get('hoof', '#4A3A30')
    return {
        'tan': tan, 'cream': cream, 'char': char, 'patch': patch, 'hoof': hoof,
        # the patches' darker and lighter cells (the pictures vary a little), never grey: shades of the patch hue
        'patch_dark': C.shade_hex(patch, 0.84),
        'patch_light': C.mix_hex(patch, tan, 0.18),
        # the blend's first stripes are the patch colour turning charcoal
        'stripe_warm': C.mix_hex(patch, char, 0.45),
        # charcoal's shadowed and lifted tones keep its violet hue (review lesson: no grey or green darks)
        'char_soft': C.mix_hex(char, '#5A4E5C', 0.35),
        'fetlock': C.mix_hex(tan, cream, 0.45),
        'char_paint': C.shade_hex(char, 1.4),        # the same hue, lifted (Ezgi's midnight stays indigo)
        'cream_paint': C.shade_hex(cream, 0.95),
        'muzzle': C.shade_hex(C.mix_hex(cream, tan, 0.08), 0.97),
        'freckle': C.mix_hex(cream, patch, 0.35),
        'brow': C.mix_hex(char, patch, 0.15),
        'lining': C.mix_hex(LINING_HEX, cream, 0.12) if pal is PALETTE else C.mix_hex(LINING_HEX, pal['belly'], 0.2),
        'blush': BLUSH_HEX,
        'hoof_dark': C.shade_hex(hoof, 0.7),
        'hoof_light': C.mix_hex(hoof, '#7A6656', 0.4),
        'tuft': char,
    }


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


# ----------------------------------------------------------------------------- the head (2-turnaround.png front and side)
HEAD_C = Vector((0.0, -0.455, 1.62))
HEAD_R = (0.182, 0.158, 0.148)
MUZZLE = ((0.0, -0.652, 1.49), (0.1, 0.092, 0.086))     # round 2: a touch narrower (the blushing cheeks show)
NOSE_C = Vector((0.0, -0.738, 1.522))
NOSTRIL = {s: (0.047 * s, -0.736, 1.525) for s in (1, -1)}
EYE_R = 0.078                      # round 2: 1.2× bigger, set higher; round 3: 1.12× more (review: 10–15%)
EYE_DEPTH = (0.42, 0.3)
EYE_YAW = math.radians(32)        # the eyes look forward and out (both read round from the front and the side)


EYE_AT = (0.108, 1.596)          # each eye's centre: x, z (2-turnaround front); y = the head's surface there (eye_centres)
OSSI_BASE = {s: (0.094 * s, -0.437, 1.705) for s in (1, -1)}
OSSI_TOP = {s: (0.104 * s, -0.417, 1.88) for s in (1, -1)}
# round 2: a fuzzy brush a little wider than the stalk (round 1's balls read as glossy beads); tops at 1.972 m (size rule)
POMPOM = {s: ((0.106 * s, -0.412, 1.924), (0.058, 0.056, 0.048)) for s in (1, -1)}


def _look(s: int) -> Vector:
    return Vector((math.sin(EYE_YAW) * s, -math.cos(EYE_YAW), 0.07)).normalized()


def _inside_parts(p: np.ndarray, parts) -> np.ndarray:
    """Inside the union of unrotated spheres, capsules and tubes (an analytic stand-in for the voxel body)."""
    ins = np.zeros(len(p), bool)
    for q in parts:
        for sx in ((1, -1) if q.mirror else (1,)):
            if q.kind == 'sphere' and not any(q.rot):
                ins |= in_ellipsoid(p, v3(q.loc) * v3((sx, 1, 1)), v3(q.scale) * q.radius) < 1.0
            elif q.kind in ('capsule', 'tube'):
                a, b = v3(q.loc) * v3((sx, 1, 1)), v3(q.to) * v3((sx, 1, 1))
                ab = b - a
                t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
                r = q.radius + (((q.r2 if q.r2 is not None else q.radius) - q.radius) * t if q.kind == 'tube' else 0.0)
                ins |= np.linalg.norm(p - (a + t[:, None] * ab), axis=1) < r
    return ins


def eye_centres() -> dict[int, Vector]:
    """Each eye sits on the head's surface where the front view puts it (EYE_AT): march forward (−Y) from inside the
    head until leaving the union of the head's parts; the lens's centre is a little proud of it along its look (the
    voxel smoothing fills the corners round it)."""
    parts = [q for q in head_parts() if not q.name.startswith(('ossicone', 'pompom'))]
    out = {}
    for s in (1, -1):
        start = v3((EYE_AT[0] * s, HEAD_C.y, EYE_AT[1]))
        ts = np.linspace(0.0, 0.35, 701)
        pts = start[None, :] + ts[:, None] * v3((0.0, -1.0, 0.0))[None, :]
        ins = _inside_parts(pts, parts)
        last = int(np.nonzero(ins)[0].max()) if ins.any() else 0
        out[s] = Vector(tuple(pts[last] + v3(_look(s)) * EYE_PROUD))
    return out


def eye_frame(s: int):
    c = EYE_C[s]
    look = _look(s)
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


LID_LASH, LID_DROP, LID_W = 0.08, 0.16, 0.92


def blink_pivot(s: int):
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.74, 0.04, 0.2)
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_props': 0.5}
BODY_TRIS = 54000


def head_parts() -> list[Part]:
    ps = [
        Part('head', 'sphere', loc=tuple(HEAD_C), radius=1.0, scale=HEAD_R),
        # the round crown and the brow (the forehead slopes down to the bridge in profile)
        Part('forehead', 'sphere', loc=(0.0, -0.505, 1.7), radius=1.0, scale=(0.13, 0.085, 0.07)),
        Part('poll', 'sphere', loc=(0.0, -0.4, 1.69), radius=1.0, scale=(0.13, 0.11, 0.08)),
        # round 2: the bridge sits back (round 1's profile bulged 5 cm ahead of the turnaround's above the muzzle)
        Part('bridge', 'capsule', loc=(0.0, -0.56, 1.655), to=(0.0, -0.645, 1.57), radius=0.058),
        Part('muzzle', 'sphere', loc=MUZZLE[0], radius=1.0, scale=MUZZLE[1]),
        # the muzzle's broad top, blending into the bridge (one soft pad, not a ball on the face)
        Part('muzzletop', 'sphere', loc=(0.0, -0.64, 1.54), radius=1.0, scale=(0.095, 0.085, 0.06)),
        # round 3 (review: the muzzle's front read flat in profile): a rounded nose bulge and a soft lower lip
        Part('nosepad', 'sphere', loc=(0.0, -0.692, 1.528), radius=1.0, scale=(0.088, 0.058, 0.052)),
        Part('lip', 'sphere', loc=(0.0, -0.684, 1.452), radius=1.0, scale=(0.072, 0.05, 0.036)),
        # the full cheeks under and behind the eyes (the face widens toward the jaw in the front view, softly)
        Part('cheek', 'sphere', loc=(0.118, -0.49, 1.5), radius=1.0, scale=(0.078, 0.095, 0.08), mirror=True),
        Part('jaw', 'capsule', loc=(0.0, -0.645, 1.445), to=(0.0, -0.5, 1.445), radius=0.058),
        # the lower face as one broad mass: the muzzle blends into the cheeks (round 1: a ball between hamster cheeks)
        Part('jowl', 'sphere', loc=(0.0, -0.585, 1.49), radius=1.0, scale=(0.138, 0.1, 0.085)),
        Part('chin', 'sphere', loc=(0.0, -0.66, 1.43), radius=1.0, scale=(0.07, 0.06, 0.04)),
        Part('nape', 'sphere', loc=(0.0, -0.36, 1.6), radius=1.0, scale=(0.142, 0.1, 0.13)),
    ]
    for s in (1, -1):
        ps.append(Part(f'ossicone{"L" if s > 0 else "R"}', 'tube', loc=OSSI_BASE[s], to=OSSI_TOP[s], radius=0.04, r2=0.035))
        ps.append(Part(f'pompom{"L" if s > 0 else "R"}', 'sphere', loc=POMPOM[s][0], radius=1.0, scale=POMPOM[s][1]))
    return ps


EYE_PROUD = 0.011               # round 2: the lens sits prouder (round 1's lids swallowed its edge)
EYE_C = eye_centres()

# the dark brows: one smooth arc over each eye, thickest in the middle (2-turnaround front, 3-faces neutral): front-view
# (x, z) points and the half thickness along them (brow_mask)
BROW_ARC = [(0.05, 1.686), (0.068, 1.701), (0.087, 1.711), (0.106, 1.716), (0.125, 1.714), (0.143, 1.706), (0.158, 1.693),
            (0.172, 1.677)]
BROW_THICK = [0.0045, 0.0062, 0.0075, 0.008, 0.008, 0.0072, 0.006, 0.0045]


def brow_mask(p: np.ndarray) -> np.ndarray:
    """0..1: the brows, by each point's distance to the arc in the front view (round 2: the ellipsoid marks read as a
    dotted line), on the front of the face only."""
    ax, z = np.abs(p[:, 0]), p[:, 2]
    d = S.polyline_dist(ax, z, BROW_ARC)
    th = np.interp(ax, [a for a, _ in BROW_ARC], BROW_THICK)
    th = th * smooth(BROW_ARC[0][0] - 0.004, BROW_ARC[0][0] + 0.012, ax) * smooth(BROW_ARC[-1][0] + 0.006, BROW_ARC[-1][0] - 0.01, ax)
    front = (p[:, 1] < -0.47) & (z > 1.63) & (z < 1.77)
    return smooth(th + 0.0018, th - 0.0018, d) * front


# ----------------------------------------------------------------------------- the body's layout
LEGS = {'FL': (0.13, -0.36), 'FR': (-0.13, -0.36), 'BL': (0.168, 0.33), 'BR': (-0.168, 0.33)}
# the hind legs' stifle (knee) and hock: (dy from the leg's y, z); the rig's `hocks` shares come from the same numbers
HIND_JOINTS = {'knee': (-0.06, 0.585), 'hock': (0.068, 0.43)}
HIND_HIP_Z = 0.86
FETLOCK_Z = 0.16
TAIL_POINTS = SP.TAIL_POINTS
STALK_END = 3                     # TAIL_POINTS[:STALK_END + 1] is the striped stalk, the rest is the tuft


def neck_parts() -> list[Part]:
    """The thick neck: ellipsoids deeper than wide, rising almost straight from the chest. Round 2: the throat runs
    straight and forward (y ≈ −0.545) down to z ≈ 0.9 and the base flares into the chest (round 1's throat sat 3–4 cm
    behind the turnaround's while the chest bulged from z 1.0, so the neck read short: review round 1)."""
    return [
        Part('neck1', 'sphere', loc=(0.0, -0.405, 1.47), radius=1.0, scale=(0.108, 0.13, 0.14)),
        Part('neck2', 'sphere', loc=(0.0, -0.405, 1.33), radius=1.0, scale=(0.113, 0.14, 0.14)),
        Part('neck3', 'sphere', loc=(0.0, -0.395, 1.19), radius=1.0, scale=(0.126, 0.15, 0.14)),
        Part('neck4', 'sphere', loc=(0.0, -0.383, 1.06), radius=1.0, scale=(0.148, 0.165, 0.14)),
        Part('neck5', 'sphere', loc=(0.0, -0.37, 0.95), radius=1.0, scale=(0.175, 0.175, 0.13)),
        # build 1: the low body showed faint rings between the ellipsoids; these fill the waists between them
        Part('neck01', 'sphere', loc=(0.0, -0.41, 1.53), radius=1.0, scale=(0.106, 0.125, 0.1)),
        Part('neck12', 'sphere', loc=(0.0, -0.405, 1.4), radius=1.0, scale=(0.11, 0.135, 0.12)),
        Part('neck23', 'sphere', loc=(0.0, -0.4, 1.26), radius=1.0, scale=(0.12, 0.145, 0.12)),
        Part('neck34', 'sphere', loc=(0.0, -0.389, 1.125), radius=1.0, scale=(0.137, 0.158, 0.12)),
    ]


def leg_parts(leg: str) -> list[Part]:
    x, y = LEGS[leg]
    if leg[0] == 'F':
        return [
            Part(f'forearm{leg}', 'tube', loc=(x, y, 0.8), to=(x, y - 0.004, 0.47), radius=0.08, r2=0.067),
            Part(f'knee{leg}', 'sphere', loc=(x, y - 0.006, 0.455), radius=1.0, scale=(0.07, 0.071, 0.072)),
            # round 3 (review): a small knee knob in front
            Part(f'kneecap{leg}', 'sphere', loc=(x, y - 0.042, 0.46), radius=1.0, scale=(0.05, 0.034, 0.046)),
            Part(f'cannon{leg}', 'tube', loc=(x, y - 0.004, 0.44), to=(x, y - 0.006, 0.2), radius=0.055, r2=0.056),
            Part(f'fetlock{leg}', 'sphere', loc=(x, y - 0.006, 0.152), radius=1.0, scale=(0.068, 0.074, 0.066)),
            Part(f'skirt{leg}', 'sphere', loc=(x, y - 0.01, 0.112), radius=1.0, scale=(0.073, 0.082, 0.032)),
        ]
    # round 3 (review: straight tubes plugged into the barrel): the round haunch flows into a thick thigh down to the
    # stifle in front, the gaskin runs back to a hock that points backward, then the cannon drops to the fetlock
    # (2-turnaround side, 1-hero); the rig's `hocks` bend there
    k = HIND_JOINTS
    return [
        Part(f'thigh{leg}', 'tube', loc=(x, y - 0.005, 0.83), to=(x, y + k['knee'][0], k['knee'][1]), radius=0.1, r2=0.08),
        Part(f'stifle{leg}', 'sphere', loc=(x, y + k['knee'][0] - 0.004, k['knee'][1]), radius=1.0, scale=(0.07, 0.07, 0.07)),
        Part(f'gaskin{leg}', 'tube', loc=(x, y + k['knee'][0], k['knee'][1]), to=(x, y + k['hock'][0], k['hock'][1]), radius=0.075, r2=0.056),
        Part(f'gaskinbulge{leg}', 'sphere', loc=(x, y + 0.03, 0.55), radius=1.0, scale=(0.068, 0.07, 0.085)),
        Part(f'hock{leg}', 'sphere', loc=(x, y + k['hock'][0] + 0.008, k['hock'][1]), radius=1.0, scale=(0.058, 0.07, 0.064)),
        Part(f'cannon{leg}', 'tube', loc=(x, y + k['hock'][0], k['hock'][1] - 0.01), to=(x, y + 0.002, 0.2), radius=0.054, r2=0.055),
        Part(f'fetlock{leg}', 'sphere', loc=(x, y - 0.002, 0.152), radius=1.0, scale=(0.068, 0.074, 0.066)),
        Part(f'skirt{leg}', 'sphere', loc=(x, y - 0.008, 0.112), radius=1.0, scale=(0.073, 0.082, 0.032)),
    ]


def torso_parts() -> list[Part]:
    ps = [
        # round 2: a deeper, rounder chest and barrel (the belly at ~0.6 m: back to belly ≈ 25% of the height, review
        # round 1 asked ~1.3× deeper), the chest's front no further forward than the throat (the neck reads long)
        Part('chest', 'sphere', loc=(0.0, -0.335, 0.83), radius=1.0, scale=(0.245, 0.195, 0.225)),
        Part('barrel', 'sphere', loc=(0.0, -0.03, 0.86), radius=1.0, scale=(0.27, 0.4, 0.25)),
        Part('belly', 'sphere', loc=(0.0, -0.06, 0.71), radius=1.0, scale=(0.22, 0.33, 0.12)),
        Part('rump', 'sphere', loc=(0.0, 0.255, 0.91), radius=1.0, scale=(0.25, 0.25, 0.228)),
        Part('haunch', 'sphere', loc=(0.14, 0.31, 0.84), radius=1.0, scale=(0.13, 0.19, 0.23), mirror=True),
        Part('shoulder', 'sphere', loc=(0.15, -0.34, 0.81), radius=1.0, scale=(0.11, 0.15, 0.2), mirror=True),
        Part('withers', 'sphere', loc=(0.0, -0.19, 1.035), radius=1.0, scale=(0.168, 0.22, 0.092)),
        Part('neckbase', 'sphere', loc=(0.0, -0.36, 0.97), radius=1.0, scale=(0.18, 0.185, 0.15)),
        # the neck's base flares into the chest and shoulders without a crease
        Part('collar', 'sphere', loc=(0.0, -0.355, 0.9), radius=1.0, scale=(0.215, 0.19, 0.15)),
        # the striped stalk of the tail
        Part('tailroot', 'tube', loc=TAIL_POINTS[0], to=TAIL_POINTS[1], radius=0.04, r2=0.035),
        Part('tailmid', 'tube', loc=TAIL_POINTS[1], to=TAIL_POINTS[2], radius=0.035, r2=0.032),
        Part('tailend', 'tube', loc=TAIL_POINTS[2], to=tuple(SP.TUFT_TOP + v3((0, 0, -0.04))), radius=0.032, r2=0.034),
    ]
    for leg in LEGS:
        ps.extend(leg_parts(leg))
    return ps


def all_parts() -> list[Part]:
    return head_parts() + neck_parts() + torso_parts()


def body_extras() -> list[bpy.types.Object]:
    """The ear slabs, the brush mane's crest, the hooves' toes and the tail tuft's clumps (new objects on every call; the
    build consumes them)."""
    out = [SP.ear_slab(s) for s in (1, -1)] + [SP.mane_mesh(), SP.forelock_mesh()]
    for leg, (x, y) in LEGS.items():
        out.extend(SP.hoof_toes(x, y - 0.012))
    out.extend(SP.tuft_meshes())
    return out


# ----------------------------------------------------------------------------- zones
def _seg_dist(p: np.ndarray, a, b) -> np.ndarray:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def leg_masks(p: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    out = {}
    for leg, (lx, ly) in LEGS.items():
        r = np.hypot(x - lx, (y - ly) * 0.9)
        top = 0.6 if leg[0] == 'F' else 0.57
        out[leg] = (r < 0.13) & (z < top + 0.06 * smooth(0.0, 0.1, np.abs(x) - np.abs(lx) + 0.05))
    return out


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    el = SP.ear_lookup(p)
    ear = el['on']
    ml = SP.mane_lookup(p)
    fore = SP.forelock_lookup(p) & ~ear
    mane = ml['on'] & ~ear & ~fore
    tl = SP.tuft_lookup(p)
    tuft = tl['on'] & (z < SP.TUFT_TOP[2] + 0.01)
    head = (((in_ellipsoid(p, (0.0, -0.52, 1.6), (0.25, 0.3, 0.24)) < 1.0) & (z > 1.38)) | ear) & ~(mane & (ml['t'] > 0.2))
    muzzle = in_ellipsoid(p, MUZZLE[0], tuple(r * 1.04 for r in MUZZLE[1])) < 1.0
    nose = np.minimum(np.linalg.norm(p - v3(NOSTRIL[1]), axis=1), np.linalg.norm(p - v3(NOSTRIL[-1]), axis=1)) < 0.03
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = head & (y < -0.5) & (z > 1.4) & (z < 1.74) & (ax < 0.17) & ~ear
    ossi = np.zeros(len(p), bool)
    pom = np.zeros(len(p), bool)
    for s in (1, -1):
        # round 2: only below the tuft (round 1 painted the tuft's lower half tan: gold specks on the charcoal)
        ossi |= (_seg_dist(p, OSSI_BASE[s], OSSI_TOP[s]) < 0.055) & (p[:, 2] < POMPOM[s][0][2] - 0.03)
        pom |= in_ellipsoid(p, POMPOM[s][0], tuple(r * 1.25 for r in POMPOM[s][1])) < 1.0
    ossi &= ~pom
    crown = head & (z > 1.72) & ~ear & ~ossi & ~pom & ~mane
    cheek = head & (ax > 0.07) & (z < 1.56) & (y < -0.44) & ~ear & ~muzzle
    chin = head & (z < 1.43) & (y < -0.55)
    legs = leg_masks(p)
    leg = np.zeros(len(p), bool)
    for m in legs.values():
        leg |= m
    leg &= ~head
    hoof = leg & (z < SP.HOOF_H + 0.004)
    fetlock = leg & ~hoof & (z < FETLOCK_Z + 0.06)
    sole = z < 0.005
    stalk = (_seg_dist(p, TAIL_POINTS[0], TAIL_POINTS[1]) < 0.06) | (_seg_dist(p, TAIL_POINTS[1], TAIL_POINTS[2]) < 0.055) | \
            (_seg_dist(p, TAIL_POINTS[2], SP.TUFT_TOP) < 0.055)
    stalk &= (y > 0.49) & ~tuft
    tail = stalk | tuft
    neck = ~head & ~leg & ~tail & (z > 0.98) & (y < -0.12) & ~mane
    torso = ~head & ~leg & ~tail & ~mane & ~neck
    belly = torso & (z < np.interp(y, [-0.55, -0.4, -0.1, 0.2, 0.42, 0.55], [0.68, 0.66, 0.66, 0.68, 0.74, 0.78]))
    back = torso & (z > 1.0)
    # the cream bib: the front of the chest between the front legs (2-turnaround front)
    bib = (torso | neck) & (y < -0.4) & (ax < 0.13 + 0.06 * smooth(0.95, 0.75, z)) & (z > 0.6) & (z < 0.95)
    return {'ear': ear, 'ear_u': el['u'], 'ear_v': el['v'], 'ear_lining': el['lining'], 'ear_h': el['h'],
            'mane': mane, 'fore': fore, 'mane_t': ml['t'], 'mane_h': ml['h'], 'mane_band': ml['band'], 'mane_frac': ml['frac'], 'mane_hmax': ml['hmax'],
            'tuft': tuft, 'tuft_u': tl['u'], 'stalk': stalk, 'tail': tail,
            'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face, 'crown': crown, 'cheek': cheek, 'chin': chin,
            'ossi': ossi, 'pom': pom, 'neck': neck, 'leg': leg, 'legs': legs, 'hoof': hoof, 'fetlock': fetlock, 'sole': sole,
            'toes': hoof, 'paw': hoof | fetlock, 'torso': torso, 'belly': belly, 'back': back, 'bib': bib}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """Build 1: the face, hooves, ears, pom-poms, mane and tuft all protected while a 457k-triangle low body fell to 54k:
    the rest collapsed into big flat facets and the thin ears were lost. Now a coarser low voxel (VOXELS) and protection
    only where detail is small: the face, the eyes, a little on the ears and hooves."""
    z = zones(co)
    # round 3b: the ears whole (review: the decimation picked a jagged line along the thin rim)
    return np.clip(z['face'] * 1.0 + z['muzzle'] * 1.0 + (z['eye_d'] < 0.12) * 1.0 + z['hoof'] * 0.25 + z['ear'] * 1.0
                   + z['pom'] * 0.25, 0, 1)


# build 1's atlas used only 36% of its square (hundreds of small islands on the lumpy parts): the tail's clumps, the
# mane, the pom-poms and the hooves unwrap from a smoothed twin (RECIPE.md), the face, ears and the smooth coat as they are
UV_SMOOTH = 40


def uv_smooth_mask(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    m = np.zeros(len(co))
    m = np.where(z['hoof'], 0.5, m)
    m = np.where(z['pom'], 0.6, m)
    m = np.where(z['mane'], 0.7, m)
    m = np.where(z['tuft'], 1.0, m)
    return m


# a big monster (2 m): the low body at 7.5 mm voxels starts near 250k triangles (5.5 mm made 457k), so the decimation to
# BODY_TRIS is a gentle ~4.5× (Puddlepup's and Rammerjack's range) instead of 8.5×
VOXELS = {'lo': 0.0075}


# ----------------------------------------------------------------------------- the coat's pattern (stripeneck_coat)
def patch_spacing(p: np.ndarray) -> np.ndarray:
    """The giraffe patches' size by region (NaN = none): big on the neck, shoulders and chest; small on the face and
    toward the hooves; none on the muzzle, ears, ossicones, mane, belly, or where the zebra takes over."""
    z = zones(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    sp = np.full(len(p), 0.15)
    sp = np.where(z['neck'], 0.135 - 0.015 * smooth(1.1, 1.45, zz), sp)
    sp = np.where(z['head'], 0.05 + 0.018 * smooth(-0.5, -0.38, y), sp)
    sp = np.where(z['face'] & (zz > 1.64), 0.04, sp)
    leg = z['leg'] & (np.abs(y - LEGS['FL'][1]) < 0.15)
    sp = np.where(leg, 0.064 + 0.036 * smooth(0.2, 0.6, zz), sp)
    none = z['muzzle'] | z['ear'] | z['ossi'] | z['pom'] | z['mane'] | z['tail'] | z['hoof'] | (z['fetlock'] & (zz < 0.15))
    none |= (z['leg'] & (y > 0.0)) | (z['eye_d'] < EYE_R * 1.7) | (z['belly'] & (zz < 0.7))
    # round 2 (review: 3-faces neutral): small spots only on the crown, the forehead's sides and the cheeks; the bridge,
    # the middle of the forehead and round the eyes plain tan
    clear_face = z['head'] & (((y < -0.52) & (zz < 1.64)) | ((np.abs(x) < 0.05) & (y < -0.5) & (zz < 1.74))
                              | (z['eye_d'] < EYE_R * 2.0))
    none |= clear_face | (z['head'] & (zz < 1.47) & (y < -0.45))
    b = coat_blend(p, z)
    none |= b > 0.55                     # round 3: the round patches end early in the blend (lozenges follow)
    return np.where(none, np.nan, sp)


_SEEDS: dict[str, K.Seeds] = {}


def seeds_for(co: np.ndarray, key: str = 'body') -> K.Seeds:
    """The patches' centres, made once from the smooth body's vertices and kept for every source painted after."""
    if key not in _SEEDS:
        _SEEDS[key] = K.make_seeds(co, patch_spacing, seed=31)
        C.log(f'stripeneck coat: {len(_SEEDS[key].c)} giraffe patches')
    return _SEEDS[key]


def coat_blend(p: np.ndarray, z: dict) -> np.ndarray:
    """0 giraffe … 1 zebra everywhere: the torso by K.blend; the head, neck, mane and front legs giraffe; the back legs
    and the tail zebra."""
    b = K.blend(p)
    front_leg = np.zeros(len(p), bool)
    back_leg = np.zeros(len(p), bool)
    for lg, m in z['legs'].items():
        if lg[0] == 'F':
            front_leg |= m
        else:
            back_leg |= m
    b = np.where(z['head'] | z['mane'] | front_leg, 0.0, b)
    # round 3: the neck fades back to giraffe going up it (a flat 0 left a hard vertical cut above the shoulder)
    b = np.where(z['neck'], b * smooth(1.18, 1.0, p[:, 2]), b)
    # the back legs are all zebra below the haunch (blend up into it)
    b = np.where(back_leg, np.maximum(b, smooth(0.66, 0.5, p[:, 2])), b)
    b = np.where(z['tail'], 1.0, b)
    return b


def coat_masks(p: np.ndarray, z: dict, seeds: K.Seeds) -> dict[str, np.ndarray]:
    """Every paint mask of the coat at points p (0..1 each). Round 2 (review: the patches stopped on one hard diagonal):
    across the middle third the patches are cut along the stripes' bands into long curved lozenges that turn into the
    stripes, while the tan fades to cream; the stripes bold (about as wide as the cream gaps) and tapering."""
    zz = p[:, 2]
    b = coat_blend(p, z)
    back_leg = np.zeros(len(p), bool)
    front_leg = np.zeros(len(p), bool)
    chev = np.zeros(len(p))
    for lg, msk in z['legs'].items():
        lx, ly = LEGS[lg]
        if lg[0] == 'B':
            back_leg |= msk
            # the angle round the leg from its outer side: the rings rise toward the front and back (a slight chevron)
            th = np.arctan2(p[:, 1] - ly, (p[:, 0] - lx) * np.sign(lx))
            chev = np.where(msk, 0.34 * (1.0 - np.abs(np.cos(th))), chev)
        else:
            front_leg |= msk
    # patches: smaller and sparser down the front legs
    rho_k = np.where(front_leg, 0.82 + 0.18 * smooth(0.25, 0.55, zz), 1.0)
    # round 3 (review: round patches up to a near-vertical line): each patch's own place in the blend (its centre's),
    # so the last rows stretch into lozenges and drop out whole, patch by patch, on a ragged edge instead of a line
    sc_ = seeds.c
    seed_b = K.blend(sc_) * (sc_[:, 2] < 1.0) * ~((sc_[:, 2] < 0.66) & (np.abs(sc_[:, 1] - LEGS['FL'][1]) < 0.15))
    pm = K.patch_masks(p, seeds, b, rho_k, smooth(0.03, 0.22, seed_b))
    keep = np.where(pm['i'] >= 0, smooth(0.34, 0.25, seed_b[np.maximum(pm['i'], 0)]), 1.0)
    allowed = ~(z['muzzle'] | z['ear'] | z['ossi'] | z['pom'] | z['mane'] | z['fore'] | z['tail'] | z['hoof'])
    # the stripes: arcs round a focus under the flank, chevroned rings down the back legs, rings along the tail
    phase = K.stripe_phase(p, back_leg * smooth(K.LEG_TOP + 0.05, K.LEG_TOP - 0.07, zz), chev)
    tpar, tlen = U.polyline_param(p, np.array(TAIL_POINTS[:STALK_END + 1]))
    phase = np.where(z['stalk'], tpar * tlen / K.TAIL_PERIOD + 0.3, phase)
    # round 3 (review: round patches up to a near-vertical line): across a wide band the last rows of patches give way to
    # long curved lozenges laid along the stripes (dashes with pointed ends, staggered stripe by stripe) that lengthen
    # into the full stripes, while the tan fades to cream (4-details panel 4, 1-hero, 2-turnaround side)
    fy, fz = K.STRIPE_FOCUS
    ry, rz = p[:, 1] - fy, (zz - fz) * K.STRIPE_Z
    along = np.hypot(ry, rz) * np.arctan2(rz, -ry)                     # metres along each stripe's arc
    k_idx = np.floor(phase)
    off = (np.sin(k_idx * 12.9898) * 43758.5453) % 1.0                  # each stripe's dashes staggered
    dash_len = 0.68 + 0.32 * smooth(0.6, 0.92, b)
    period = 0.19 + 0.13 * smooth(0.45, 0.85, b)                       # patch-sized lozenges at the giraffe side, lengthening
    u = (along / period + off) % 1.0
    lens = np.sin(np.pi * np.clip(u / dash_len, 0.0, 1.0)) ** 0.6
    lens = 1.0 - (1.0 - lens) * (1.0 - smooth(0.78, 0.95, b))
    z_str = smooth(0.08, 0.22, b)
    fade = keep * (1.0 - smooth(0.4, 0.55, b))                          # whole patches drop out; a soft net behind
    patch = pm['patch'] * fade * allowed
    outline = pm['outline'] * fade * allowed
    duty = (0.46 + 0.09 * smooth(0.45, 0.85, b)) * lens * z_str          # bold: a stripe about as wide as its gap
    duty = np.where(back_leg, 0.5 * smooth(0.3, 0.6, b), duty)          # the legs' bands (sparser: LEG_PERIOD)
    duty = np.where(z['stalk'], 0.42, duty)
    # stripes taper out on the lowest legs (cream fetlocks) and under the belly
    duty = duty * smooth(0.17, 0.26, zz) * (1 - z['belly'] * smooth(0.72, 0.62, zz) * 0.8)
    stripe = K.duty_mask(phase, duty)
    # the lozenges fill the gaps between the last patches (never painted over them) and keep a patch's cream rim until
    # they lengthen into stripes
    on_body = ~(back_leg | z['stalk'])
    stripe = np.where(on_body, stripe * (1.0 - np.clip(patch + outline, 0.0, 1.0)), stripe)
    rim_k = (1.0 - smooth(0.5, 0.75, b)) * z_str * on_body * allowed
    rim = np.clip(K.duty_mask(phase, duty + 0.16 * smooth(0.0, 0.35, lens)) - stripe, 0.0, 1.0) * rim_k
    rim = rim * (1.0 - np.clip(patch, 0.0, 1.0))
    outline = np.maximum(outline, rim * 0.85)
    # now and then a stripe forks: a thin cream split opens along part of it (body only, not the legs or the tail)
    fork = smooth(0.45, 0.8, K.noise3(p, 5.0, 91, 3)) * (1 - back_leg) * (1 - z['stalk']) * smooth(0.5, 0.8, b)
    stripe = stripe * (1.0 - K.duty_mask(phase, 0.16 * fork))
    # the cream areas: the bib, the belly line, the fetlocks' lighter fur, the muzzle
    # round 4: a small soft cream patch low between the front legs (a wide one muddied the chest's patches)
    # round 3 (review): the cream chest bib between the front legs (2-turnaround front)
    cream = np.maximum(z['bib'] * ell_soft(p, (0.0, -0.5, 0.78), (0.11, 0.17, 0.17), 0.45) * 0.85, 0.0)
    cream = np.maximum(cream, z['belly'] * smooth(0.7, 0.62, zz))
    mz = ell_soft(p, MUZZLE[0], tuple(r * 1.08 for r in MUZZLE[1]), 0.12) * (zz < 1.585)
    lighter = np.maximum(z['fetlock'] * smooth(FETLOCK_Z + 0.05, FETLOCK_Z - 0.02, zz), 0.0)
    return {'b': b, 'patch': patch * (1 - cream * 0.85) * (1 - mz), 'outline': outline * (1 - cream * 0.5) * (1 - mz), 'rnd': pm['rnd'],
            'stripe': stripe * (1 - cream * 0.6), 'cream': cream, 'muzzle': mz, 'lighter': lighter}


def coat_rgb(p: np.ndarray, z: dict, m: dict, pal: dict) -> np.ndarray:
    """The flat colour of every point (linear RGB), from the masks and a palette (the base or a variant)."""
    col = colours(pal)
    zz = p[:, 2]
    b = m['b']
    # round 2: the darks are painted a little above their hex and the zebra's cream a little below (the film render took
    # the charcoal to near black and the cream to white: review round 1), so they read as #2F2B30 and #F4EBDA
    tan, patch = lin(col['tan']), lin(col['patch'])
    cream, char = lin(col['cream_paint']), lin(col['char_paint'])
    # round 3: the tan carries on under the first stripes and fades to cream through the band
    base = K.mix(np.tile(tan, (len(p), 1)), np.tile(cream, (len(p), 1)), smooth(0.4, 0.95, b))
    base = K.mix(base, np.tile(lin(col['fetlock']), (len(p), 1)), m['lighter'] * (1 - smooth(0.3, 0.7, b)))
    base = K.mix(base, np.tile(cream, (len(p), 1)), m['lighter'] * smooth(0.3, 0.7, b))
    base = K.mix(base, np.tile(cream, (len(p), 1)), m['cream'])
    # the patches: a little darker or lighter each, never grey
    pc = K.mix(np.tile(lin(col['patch_dark']), (len(p), 1)), np.tile(lin(col['patch_light']), (len(p), 1)), m['rnd'])
    pc = K.mix(np.tile(patch, (len(p), 1)), pc, np.full(len(p), 0.6))
    sc = K.mix(np.tile(patch, (len(p), 1)), np.tile(char, (len(p), 1)), smooth(0.3, 0.75, b))
    # where the patches break into lozenges they darken toward the stripes' colour
    pc = K.mix(pc, sc, smooth(0.3, 0.75, b))
    rgb = K.mix(base, np.tile(lin(col['cream']), (len(p), 1)), m['outline'])
    rgb = K.mix(rgb, pc, m['patch'])
    rgb = K.mix(rgb, sc, m['stripe'])
    rgb = K.mix(rgb, np.tile(lin(col['muzzle']), (len(p), 1)), m['muzzle'])
    # the mane's bands: charcoal and cream alternate tuft by tuft (the forelock is cream with charcoal sides)
    # round 3: eight uneven bands, charcoal first behind the forelock; the forelock cream down its middle, charcoal at its
    # sides (2-turnaround front, 3-faces neutral); the mane's cream a little warmer so its tips don't read as white shards
    band_char = (z['mane_band'] % 2 == 0).astype(float)
    mane_cream = np.tile(cream * 0.93, (len(p), 1))
    mane_c = K.mix(mane_cream, np.tile(char, (len(p), 1)), band_char)
    rgb = np.where(z['mane'][:, None], mane_c, rgb)
    fore_cream = smooth(0.02, 0.009, np.abs(p[:, 0])) * smooth(-0.438, -0.458, p[:, 1])
    fore_c = K.mix(np.tile(char, (len(p), 1)), mane_cream, fore_cream)
    rgb = np.where(z['fore'][:, None], fore_c, rgb)
    # the ossicones' tufts and the tail's tuft: charcoal; the ossicones' shafts: tan
    rgb = np.where(z['pom'][:, None], char[None, :], rgb)
    rgb = np.where(z['ossi'][:, None], tan[None, :], rgb)
    rgb = np.where(z['tuft'][:, None], char[None, :], rgb)
    # the ears: tan outside, the lining pink with a cream fur rim
    ear_out = z['ear'] & ~z['ear_lining']
    rgb = np.where(ear_out[:, None], K.mix(np.tile(tan, (len(p), 1)), np.tile(cream, (len(p), 1)), 0.35 * smooth(0.7, 1.0, np.abs(z['ear_v']))), rgb)
    # round 2: the pink skin in the middle, a soft cream fur band along the inner edge (its fringe cards take this cream)
    lining = z['ear_lining'] * smooth(0.74, 0.52, np.abs(z['ear_v'])) * smooth(0.06, 0.2, z['ear_u']) * smooth(0.96, 0.8, z['ear_u'])
    ear_in = z['ear_lining']
    rgb = np.where(ear_in[:, None], K.mix(np.tile(lin(col['cream']), (len(p), 1)), np.tile(lin(col['lining']), (len(p), 1)), lining), rgb)
    # the hooves
    hoof = z['hoof'] * smooth(SP.HOOF_H + 0.004, SP.HOOF_H - 0.008, zz)
    rgb = K.mix(rgb, np.tile(lin(col['hoof']), (len(p), 1)), hoof)
    # the brows and the small closed smile (painted on the locks too, so they stay clean lines over the velvet)
    rgb = K.mix(rgb, np.tile(lin(col['brow']), (len(p), 1)), brow_mask(p) * z['head'])
    rgb = K.mix(rgb, np.tile(lin(MOUTH_HEX), (len(p), 1)), np.clip(mouth_mask(p) * 1.4, 0, 1) * z['head'])
    return rgb


# ----------------------------------------------------------------------------- the shape preview's colours
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    z = zones(co, vn)
    seeds = seeds_for(co, 'preview')
    m = coat_masks(co, z, seeds)
    rgb = coat_rgb(co, z, m, PALETTE)
    col = colours(PALETTE)
    # the face's painted details, roughly (the bake does them per pixel)
    blush = np.zeros(len(co))
    for s in (1, -1):
        blush = np.maximum(blush, ell_soft(co, (0.15 * s, -0.56, 1.5), (0.05, 0.06, 0.04), 0.5))
    rgb = K.mix(rgb, np.tile(lin(col['blush']), (len(co), 1)), blush * 0.7)
    nos = np.zeros(len(co))
    for s in (1, -1):
        nos = np.maximum(nos, ell_soft(co, NOSTRIL[s], (0.019, 0.016, 0.011), 0.3))
    rgb = K.mix(rgb, np.tile(lin(NOSE_HEX), (len(co), 1)), nos)
    rgb = K.mix(rgb, np.tile(lin(MOUTH_HEX), (len(co), 1)), np.clip(mouth_mask(co) * 1.2, 0, 1))
    return rgb


# ----------------------------------------------------------------------------- carving (the high source only)
def mouth_curve() -> list[tuple[float, float]]:
    """A small happy smile on the front of the muzzle: the corners curl up (x, z in the front view)."""
    mid = 1.462
    pts = []
    for k in range(-16, 17):
        t = k / 16
        x = 0.058 * t
        zc = mid + 0.014 * t * t + 0.008 * max(0.0, abs(t) - 0.7) / 0.3
        pts.append((x, zc))
    return pts


def mouth_mask(p: np.ndarray) -> np.ndarray:
    d = S.polyline_dist(p[:, 0], p[:, 2], mouth_curve())
    front = smooth(-0.66, -0.7, p[:, 1])
    return np.exp(-(d / 0.0032) ** 2) * front


def closed_lid(co: np.ndarray):
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax, ay = EYE_R * 1.0, EYE_R * 0.95
        r2 = (xe / ax) ** 2 + (ye / ay) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * EYE_R
        th = 0.0024 + 0.0018 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
        # round 2 (review: the closed lids read as goggle domes and the lashes vanished): painted lashes along the closed
        # lid's outer half, each a short stroke down and out from the lash line
        for k in range(6):
            f = k / 5.0
            xa = (0.15 + 0.8 * f) * s                 # along the lid in xn (× s: toward the outer corner)
            ya = -(LID_LASH + LID_DROP * (1.0 - xa ** 2)) * EYE_R
            d = np.array((0.5 * s, -1.0))
            d = d / np.linalg.norm(d)
            ln = EYE_R * (0.28 + 0.24 * f)
            ax0, ay0 = xa * ax * LID_W, ya
            t = np.clip(((xe - ax0) * d[0] + (ye - ay0) * d[1]) / ln, 0.0, 1.0)
            dist = np.hypot(xe - (ax0 + t * ln * d[0]), ye - (ay0 + t * ln * d[1]))
            lash = np.maximum(lash, np.exp(-(dist / (0.0016 * (1.2 - 0.6 * t))) ** 2) * front * (r2 < 2.2))
    return bulge, lash


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    # the giraffe patches' centres, from the high body (the cards are scattered before the paint and need them)
    seeds_for(co, 'body')
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    groove = mouth_mask(co) * (z < 1.5) * (z > 1.42)
    nos = np.zeros_like(x)
    for s in (1, -1):
        c = NOSTRIL[s]
        # a comma: a short slit curling down and out
        dd = np.sqrt(((x - c[0]) / 1.7) ** 2 + ((z - c[2]) / 1.1) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.0095) ** 2))
    nos *= smooth(NOSE_C.y + 0.03, NOSE_C.y + 0.012, y)
    brow = brow_mask(co)
    bulge, lash = closed_lid(co)
    zn = zones(co, vn)
    # the hooves: fine vertical growth lines and a rim where the hoof meets the fetlock's fur
    hoof = zn['hoof']
    ang = np.zeros(len(co))
    for lx, ly in LEGS.values():
        near = np.hypot(x - lx, y - ly) < 0.13
        ang = np.where(near, np.arctan2(y - ly, x - lx), ang)
    hz = (np.sin(ang * 46.0 + np.sin(z * 60.0) * 0.6) * 0.6 + np.sin(z * 520.0) * 0.4) * hoof * smooth(0.0, 0.012, z)
    # the brush mane: bristle grooves running out along each tuft, and a parting between the tufts
    mane = zn['mane']
    bris = np.sin(x * 260.0 + np.sin(zn['mane_t'] * 90.0) * 1.4) * mane * smooth(0.03, 0.08, zn['mane_h'])
    part = np.exp(-((np.abs(zn['mane_frac']) - 0.5) / 0.07) ** 2) * mane * smooth(0.02, 0.06, zn['mane_h'])
    # the tail's tuft: wavy strand grooves down each clump; the pom-poms: a fuzzy stipple
    tuft = zn['tuft']
    tg = np.sin(np.arctan2(y - SP.TUFT_TOP[1], x) * 30.0 + z * 25.0) * tuft
    pom = zn['pom'] * (np.sin(x * 400.0) * np.sin(y * 380.0) * np.sin(z * 410.0))
    disp = (-0.0024 * groove - 0.006 * nos + 0.003 * brow + 0.0008 * bulge - 0.0011 * lash + 0.0004 * hz
            + 0.0026 * bris - 0.006 * part + 0.0022 * tg + 0.0018 * pom)
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * 1.0, v.co.y * EYE_R * 0.95, v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((EYE_R * 1.0, EYE_R * 0.95, EYE_R * EYE_DEPTH[0])))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """A big warm-brown iris (CONTENT's eye colour at its rim, warmer toward the pupil), a large black pupil, a little
    white at the outer corner and below, one big and one small catchlight toward the key light, and the thick dark
    upper lash line with a flick at the outer corner (4-details.png panel 2)."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    pal = pal or PALETTE
    eye_hex = pal['eye']
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    ix = nb.math('SUBTRACT', x, nb.math('MULTIPLY', side, -0.05))
    iy = nb.math('ADD', y, 0.04)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.68), nb.math('DIVIDE', iy, 0.72), 0.0))   # round 2: more white
    warm = C.mix_hex(eye_hex, '#8A5530', 0.6)
    amber = C.mix_hex(warm, '#B57A44', 0.35)
    iris = nb.ramp(ri, [(0.0, C.lin('#0B0807')), (0.47, C.lin('#0B0807')), (0.52, C.lin(C.shade_hex(eye_hex, 0.95))),
                        (0.64, C.lin(warm)), (0.82, C.lin(amber)), (0.93, C.lin(warm)), (0.985, C.lin(eye_hex)),
                        (1.0, C.lin(C.shade_hex(eye_hex, 0.6))), (1.04, C.lin('#F4EFE8')), (1.6, C.lin('#F4EFE8'))])
    shade = nb.math('MULTIPLY', nb.smooth(nb.vmath('LENGTH', nb.comb(x, y, 0.0)), 0.7, 1.0), 0.25)
    c = nb.mix(nb.math('MULTIPLY', shade, nb.smooth(ri, 1.0, 1.05)), iris, nb.rgb(C.lin('#C9BFB4')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', x, 0.2), nb.math('DIVIDE', nb.math('SUBTRACT', y, 0.28), 1.15), 0.0)), 0.2, 0.17)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', x, 0.24), nb.math('ADD', y, 0.28), 0.0)), 0.075, 0.058)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', x, side), 0.2, 0.95), 0.2)
    lash = nb.smooth(nb.math('ADD', y, outer), 0.5, 0.6)                          # round 2: a thick dark lash line
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- props: the lashes (on the blink bones)
def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    parts = SP.lash_meshes(f'{tag}_lash', eye_frame, EYE_R, high)
    from lib import mesh as M
    ob = M.join_meshes(parts, f'{tag}_lashes')
    side = np.concatenate([S.attr_array(o, 'lash_side') for o in parts])
    for o in parts:
        bpy.data.objects.remove(o, do_unlink=True)
    ob.data.shade_smooth()
    S.add_attr(ob, 'lash_side', side)
    ob['prop'] = 'lashes'
    return [ob]


def prop_weight_regions(co: np.ndarray, attr, names: list[str]):
    side = attr('lash_side')
    regs = []
    for s, tag in ((1, 'L'), (-1, 'R')):
        m = np.abs(side - s) < 0.5
        if m.any() and f'eye.{tag}' in names:
            regs.append(U.rigid(m, f'eye.{tag}'))
    return regs


def prop_arrays(ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    n = len(ob.data.vertices)
    rgb = np.tile(lin(LASH_HEX), (n, 1))
    rc = np.stack([np.ones(n), np.full(n, 0.5), np.zeros(n)], axis=1)
    return rgb, rc


# ----------------------------------------------------------------------------- the rig's proportions (plans/quadruped.py)
HIP = (0.0, 0.28, 0.92)
CHEST = (0.0, -0.16, 0.92)
NECK_POINTS = [(0.0, -0.4, 0.92), (0.0, -0.392, 1.1), (0.0, -0.4, 1.26), (0.0, -0.405, 1.4), (0.0, -0.427, 1.52)]


def rig_p() -> dict:
    return {
        'hip': HIP,
        'chest': CHEST,
        'head_c': tuple(HEAD_C),
        'head_r': 0.16,
        'ear_base': tuple(map(float, SP.EAR_ROOT)),
        'ear_dir': tuple(map(float, SP.EAR_DIR)),
        'ear_len': SP.EAR_LEN,
        'tail_base': TAIL_POINTS[0],
        'tail_dir': tuple((v3(TAIL_POINTS[-1]) - v3(TAIL_POINTS[0])) / np.linalg.norm(v3(TAIL_POINTS[-1]) - v3(TAIL_POINTS[0]))),
        'tail_len': float(np.linalg.norm(np.diff(np.array(TAIL_POINTS), axis=0), axis=1).sum()),
        'tail_bones': len(TAIL_POINTS) - 1,
        'tail_points': TAIL_POINTS,
        'neck_bones': len(NECK_POINTS) - 1,
        'neck_points': NECK_POINTS,
        'legs': {leg: (lx, ly, 0.83 if leg[0] == 'F' else HIND_HIP_Z) for leg, (lx, ly) in LEGS.items()},
        # round 3 (review): the hind legs bend at a backward hock (the walk, the crouch and the kick aim at it)
        'hocks': {'knee': (HIND_JOINTS['knee'][0] / HIND_HIP_Z, HIND_JOINTS['knee'][1] / HIND_HIP_Z - 1.0),
                  'hock': (HIND_JOINTS['hock'][0] / HIND_HIP_Z, HIND_JOINTS['hock'][1] / HIND_HIP_Z - 1.0),
                  'paw': (-0.012 / HIND_HIP_Z, -1.0)},
        'knee_back': 0.04,
        'ankle_z': 0.13,
        'foot_len': 0.09,
        'leg_radius': 0.12,
        'stride': 0.3,
        'hooves': True,
        'strike_style': 'kick',                # the card's attack: a spin and a double back-hoof buck (5-poses attack)
    }


REVIEW = {
    'centre': (0.0, 0.02, 0.98),
    'size': 2.35,
    'head': ((0.0, -0.5, 1.64), 0.95),
}


# ----------------------------------------------------------------------------- paint (numpy, per source vertex)
_MASKS: dict[str, tuple] = {}


PAINT_ZONES = ('mane', 'fore', 'mane_band', 'pom', 'ossi', 'tuft', 'ear', 'ear_lining', 'ear_u', 'ear_v', 'hoof', 'head', 'neck')
CHUNK = 400000


def _masks_of(ob, pos: np.ndarray):
    """The coat's masks at every vertex's own position (a lock takes the pattern where it lies, so the patches' cream
    outlines and the stripes stay crisp over the locks). Evaluated in chunks (the lying locks are millions of
    vertices) keeping only what the paint reads; cached per source: the base and the variant share them."""
    if ob.name not in _MASKS:
        zs, ms = [], []
        for i in range(0, len(pos), CHUNK):
            q = pos[i:i + CHUNK]
            z = zones(q)
            ms.append(coat_masks(q, z, _SEEDS['body']))
            zs.append({k: z[k] for k in PAINT_ZONES})
        z = {k: np.concatenate([c[k] for c in zs]) for k in PAINT_ZONES}
        m = {k: np.concatenate([c[k] for c in ms]) for k in ms[0]}
        _MASKS[ob.name] = (z, m)
    return _MASKS[ob.name]


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    pos = co.reshape(-1, 3).astype(np.float64)
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    lrand = S.attr_array(ob, 'lrand').astype(np.float64)
    z, m = _masks_of(ob, pos)
    rgb = np.empty((len(pos), 3))
    for i in range(0, len(pos), CHUNK):
        sl = slice(i, i + CHUNK)
        rgb[sl] = coat_rgb(pos[sl], {k: v[sl] for k, v in z.items()}, {k: v[sl] for k, v in m.items()}, pal)
    is_lock = kind > 0.5
    # round 3b (review: gold specks on the black tufts, white speckle along the mane's band edges): a lock rooted on a
    # hair part (the mane, the forelock, the pom-poms, the tail's tuft) takes its root's colour all along, so a tip that
    # stands off the part never picks up the tan, cream or stripes of the zone it overhangs
    hair_root = np.zeros(len(pos), bool)
    if is_lock.any() and ob.data.attributes.get('root') is not None:
        li = np.nonzero(is_lock)[0]
        roots = S.attr_array(ob, 'root')[li].astype(np.float64)
        ur, inv = np.unique(np.round(roots, 5), axis=0, return_inverse=True)
        inv = np.asarray(inv).ravel()
        zr = zones(ur)
        hr = np.nonzero(zr['mane'] | zr['fore'] | zr['pom'] | zr['tuft'])[0]
        if len(hr):
            sub = ur[hr]
            zs = zones(sub)
            col_r = coat_rgb(sub, zs, coat_masks(sub, zs, _SEEDS['body']), pal)
            j = np.full(len(ur), -1, np.int64)
            j[hr] = np.arange(len(hr))
            jj = j[inv]
            use = jj >= 0
            rgb[li[use]] = col_r[jj[use]]
            hair_root[li[use]] = True
    # each lock: a slightly darker root, lighter tip, a little variation (the velvet's sheen in the colour)
    # round 2: gentler (the darker roots read as grey scratches on the patches: review round 1)
    shade = 0.94 + 0.08 * tpos + 0.05 * (lrand - 0.5)
    shade = np.where(is_lock, shade, 1.0)
    hoof = z['hoof'] * smooth(SP.HOOF_H + 0.004, SP.HOOF_H - 0.008, pos[:, 2])
    rough = np.where(is_lock, 0.5 + 0.25 * np.abs(tpos - 0.45), 0.66)
    coat = np.where(is_lock, 0.1, 0.05)
    glossy = np.zeros(len(pos))
    for s in (1, -1):
        glossy = np.maximum(glossy, ell_soft(pos, NOSTRIL[s], (0.02, 0.016, 0.014), 0.2))
    rough = rough * (1 - glossy) + 0.3 * glossy
    rough = rough * (1 - hoof) + 0.34 * hoof
    coat = coat * (1 - hoof) + 0.45 * hoof
    lining = z['ear_lining'] * 1.0
    rough = rough * (1 - lining) + 0.55 * lining
    # round 2: the brush mane, the ossicones' tufts and the tail's locks matte (round 1 read glossy black)
    hair = (z['mane'] | z['fore'] | z['pom'] | z['tuft'] | hair_root) * 1.0
    rough = rough * (1 - hair) + 0.86 * hair
    coat = coat * (1 - hair)
    # round 3b (review: a glossy yellow streak down the throat): the neck's velvet a little more matte
    neck_m = (z['neck'] & is_lock) * 1.0
    rough = rough * (1 - neck_m) + np.maximum(rough, 0.68) * neck_m
    coat = coat * (1 - neck_m) + 0.03 * neck_m
    return {'paint': rgb, 'shade': shade, 'hoof': hoof, 'rough': np.stack([np.ones(len(pos)), rough, coat], axis=1)}


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
    co, _vn = S.mesh_arrays(body_srcs[0])
    seeds_for(co, 'body')           # made by carve already (the same high body)
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'shade', a['shade'])
        S.add_attr(ob, 'hoof', a['hoof'])
        for vid, vpal in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), paint_arrays(ob, vpal)['paint'])
    for ob in props:
        rgb, rc = prop_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        for vid, vpal in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), prop_arrays(ob, vpal)[0])


# ----------------------------------------------------------------------------- paint (nodes: the crisp face details, per pixel)
def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


FRECKLES = [(sx * x, y, z) for sx in (1, -1) for x, y, z in ((0.05, -0.736, 1.495), (0.066, -0.728, 1.486), (0.058, -0.73, 1.505),
                                                             (0.075, -0.72, 1.497), (0.068, -0.722, 1.476))]


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the painted attribute × each lock's shade; then the crisp face marks by position: the brows, the blush,
    the nostrils, the smile, the muzzle's freckles, the closed lids and their lash line, and scuffs on the hooves."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 0.5)
    c = nb.attribute(attr).outputs['Color']
    shade = nb.attribute('shade').outputs['Fac']
    c = nb.mix(1.0, c, nb.comb(shade, shade, shade), blend='MULTIPLY')
    blush = None
    for s in (1, -1):
        e = _ell(nb, pos, (0.152 * s, -0.56, 1.5), (0.05, 0.062, 0.042), 0.6)
        blush = e if blush is None else nb.math('MAXIMUM', blush, e)
    c = nb.mix(nb.math('MULTIPLY', blush, 0.65), c, nb.rgb(C.lin(col['blush'])))
    fr = None
    for fc in FRECKLES:
        e = _ell(nb, pos, fc, (0.0035, 0.0035, 0.0035), 0.3)
        fr = e if fr is None else nb.math('MAXIMUM', fr, e)
    c = nb.mix(nb.math('MULTIPLY', fr, 0.7), c, nb.rgb(C.lin(col['freckle'])))
    nos = None
    for s in (1, -1):
        e = _ell(nb, pos, NOSTRIL[s], (0.02, 0.016, 0.011), 0.25)
        nos = e if nos is None else nb.math('MAXIMUM', nos, e)
    c = nb.mix(nos, c, nb.rgb(C.lin(NOSE_HEX)))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(MOUTH_HEX)))
    lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
    c = nb.mix(nb.math('MULTIPLY', lid, 0.07), c, nb.rgb((0.0, 0.0, 0.0)))     # round 2: a flat fur lid, not a dark dome
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    hoof = nb.attribute('hoof').outputs['Fac']
    sc = nb.noise(pos, 38.0, 4.0, 0.62)
    scr = nb.smooth(sc, 0.58, 0.68)
    c = nb.mix(nb.math('MULTIPLY', hoof, nb.math('MULTIPLY', scr, 0.3)), c, nb.rgb(C.lin(col['hoof_light'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- how the fur lies
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    x, zz = p[:, 0], p[:, 2]
    k = len(p)
    down = np.tile(v3((0, 0, -1)), (k, 1))
    # head: back from the nose over the crown, down the sides of the face
    g = norm(p - v3((0.0, -0.76, 1.5)))
    wd = (smooth(1.62, 1.5, zz) * smooth(0.05, 0.12, np.abs(x)))[:, None]
    g_head = norm(g * (1 - wd) + down * wd * 1.2)
    # the ears: out along the ear; the ossicones: up the shaft; the pom-poms: out from their centres
    ear_d = np.stack([np.sign(x) * SP.EAR_DIR[0], np.full(k, SP.EAR_DIR[1]), np.full(k, SP.EAR_DIR[2])], 1)
    g_head = np.where(z['ear'][:, None], ear_d, g_head)
    for s in (1, -1):
        d_, a_, _o = SP.ear_axes(s)
        inward = norm(-np.sign(z['ear_v'])[:, None] * a_[None, :] + 0.5 * d_[None, :])
        fringe = z['ear_lining'] & (np.abs(z['ear_v']) > 0.5) & (np.sign(x) == s)
        g_head = np.where(fringe[:, None], inward, g_head)
    g_head = np.where(z['ossi'][:, None], np.tile(v3((0.0, 0.1, 1.0)), (k, 1)), g_head)
    pc = np.where((x >= 0)[:, None], v3(POMPOM[1][0])[None, :], v3(POMPOM[-1][0])[None, :])
    g_head = np.where(z['pom'][:, None], norm(p - pc), g_head)
    # the neck: down and a little back; the body: back toward the tail along the top, down the sides
    g_neck = norm(np.tile(v3((0.0, 0.25, -1.0)), (k, 1)))
    side = np.clip(np.abs(n[:, 0]) * 1.3, 0, 1)[:, None]
    g_torso = norm(v3((0.0, 1.0, -0.15)) * (1 - side) + v3((0.0, 0.4, -1.0)) * side)
    g = np.where(z['torso'][:, None], g_torso, g_head)
    g = np.where(z['neck'][:, None], g_neck, g)
    g = np.where(z['belly'][:, None], np.tile(v3((0.0, 0.4, -0.8)), (k, 1)), g)
    g = np.where(z['leg'][:, None], np.tile(v3((0.0, 0.05, -1.0)), (k, 1)), g)
    g = np.where(z['fore'][:, None], np.tile(v3((0.0, 0.1, 1.0)), (k, 1)), g)
    # the mane's bristles stand out from the neck
    _P, _T, O = SP.mane_frame(np.clip(z['mane_t'], 0, 1))
    g = np.where(z['mane'][:, None], O, g)
    # the tail: down along it; the tuft: down its clumps
    g = np.where(z['tail'][:, None], down, g)
    g = np.where((z['head'] & ~z['mane'])[:, None], g_head, g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


LOCK_TEMPLATES = {'head': (7, 11, 3, 0.15), 'body': (5, 9, 3, 0.16)}
# round 2: the narrow slots between the locks baked near black (grey scratches, black leg stripes): RECIPE.md
AO_FLOOR = 0.38
AO_SOFTEN = 1.5


def head_lock_params(p, n):
    """Short velvet on the face, a touch longer on the crown and cheeks; none on the muzzle's nose, round the eyes or on
    the ears' linings."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.04)
    W = np.full(k, 0.012)
    lift = np.full(k, _rad(2.5))
    L = np.where(z['face'], 0.03, L)
    W = np.where(z['face'], 0.0095, W)
    L = np.where(z['muzzle'], 0.016, L)
    W = np.where(z['muzzle'], 0.0068, W)
    lift = np.where(z['muzzle'], _rad(1.0), lift)
    L = np.where(z['cheek'], 0.048, L)
    L = np.where(z['ear'], 0.032, L)
    W = np.where(z['ear'], 0.009, W)
    L = np.where(z['ossi'], 0.022, L)
    W = np.where(z['ossi'], 0.0075, W)
    L = np.where(z['pom'], 0.03, L)
    lift = np.where(z['pom'], _rad(14.0), lift)
    near_eye = smooth(EYE_R * 1.1, EYE_R * 1.8, z['eye_d'])
    L = L * (0.45 + 0.55 * near_eye)
    W = W * (0.6 + 0.4 * near_eye)
    nose_pad = np.zeros(len(p), bool)
    for s in (1, -1):
        nose_pad |= in_ellipsoid(p, NOSTRIL[s], (0.026, 0.02, 0.02)) < 1.0
    ear_edge = z['ear'] & ((np.abs(z['ear_v']) > 0.6) | (z['ear_u'] > 0.74))
    skip = ~z['head'] | z['mane'] | nose_pad | (mouth_mask(p) > 0.05) | (z['eye_d'] < EYE_R * 1.08) | z['ear_lining'] | ear_edge
    return np.where(skip, np.nan, W * 0.58), L, W, lift, z


def body_lock_params(p, n):
    """The short dense velvet over the neck, body and legs; longer bristles on the mane, long locks down the tail's
    tuft, a fluffy skirt on the fetlocks."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.046)
    W = np.full(k, 0.0155)
    lift = np.full(k, _rad(2.5))
    L = np.where(z['leg'], 0.036, L)
    W = np.where(z['leg'], 0.013, W)
    L = np.where(z['fetlock'], 0.05, L)
    lift = np.where(z['fetlock'], _rad(8.0), lift)
    L = np.where(z['belly'] | z['bib'], 0.056, L)
    L = np.where(z['mane'], 0.075, L)
    W = np.where(z['mane'], 0.012, W)
    lift = np.where(z['mane'], _rad(6.0), lift)
    L = np.where(z['stalk'], 0.032, L)
    W = np.where(z['stalk'], 0.011, W)
    L = np.where(z['tuft'], 0.09, L)
    W = np.where(z['tuft'], 0.013, W)
    skip = (z['head'] & ~z['mane']) | z['hoof'] | z['sole']
    return np.where(skip, np.nan, W * 0.62), L, W, lift, z


CARD_LAYERS = 2
CARD_SHADE = 0.95
# the cards take their colour from a bake of the bare skin (the patches' outlines and the stripes are many colour edges;
# sampling the atlas there picked up the lying locks' other colour: RECIPE.md)
CARD_COLOUR_FROM = 'skin'


def card_params(p, n, layer: int):
    """Soft cards only where the outline wants fuzz. Layer 0: a sparse, short velvet fringe along the top line, the
    belly, the backs of the legs and the throat; layer 1: the brush mane's bristle tips, the pom-poms, the fetlock
    skirts, the ears' cream rims and the tail's tuft."""
    z = zones(p, n)
    k = len(p)
    y, zz = p[:, 1], p[:, 2]
    covered = z['ear_lining'] | z['sole'] | z['hoof'] | z['muzzle'] | z['face'] | (z['eye_d'] < 0.1) | z['ossi']
    if layer == 0:
        L = np.full(k, 0.042)
        W = np.full(k, 0.032)
        lift = np.full(k, _rad(6))
        sp = np.full(k, 0.034)
        topline = z['torso'] & (n[:, 2] > 0.55)
        belly = z['belly'] & (n[:, 2] < -0.4)
        throat = z['neck'] & (n[:, 1] < -0.5)
        leg_back = np.zeros(k, bool)
        for lg, (lx, ly) in LEGS.items():
            if lg[0] == 'F':
                leg_back |= z['legs'][lg] & (y > ly + 0.03) & (zz > 0.25)
        bib = z['bib'] & (n[:, 1] < -0.4)
        L = np.where(belly | bib, 0.055, L)
        # round 3b (review): no cards on the throat (grey teeth under the chin, comb marks on the patches, a glossy
        # streak) or the top line (white speckle on the rump's stripes); only the front legs' backs keep a fringe
        fringe = leg_back & ~(topline | throat)
        skip = ~fringe | covered | z['mane'] | z['tail']
    else:
        L = np.full(k, 0.06)
        W = np.full(k, 0.036)
        lift = np.full(k, _rad(20))
        sp = np.full(k, 0.024)
        # round 2: fanned matte tips along the crest, none on the forelock (round 1's read as a grey shard clump)
        mane_tip = z['mane'] & (z['mane_h'] > z['mane_hmax'] * 0.55) & (z['mane_t'] > 0.1) & (z['mane_band'] % 2 == 0)
        mane_tip &= (z['mane_t'] < 0.7) & (np.abs(z['mane_frac']) < 0.3)
        pom = z['pom']
        fet = z['fetlock'] & (zz > SP.HOOF_H + 0.01)
        # round 2: a soft cream fringe along each ear's inner edge (round 1's cards on the outer rim read as torn paper)
        ear_rim = z['ear_lining'] & (np.abs(z['ear_v']) > 0.58) & (z['ear_u'] > 0.12) & (z['ear_u'] < 0.9)
        tuft = z['tuft']
        L = np.where(mane_tip, 0.042, L)
        W = np.where(mane_tip, 0.028, W)
        lift = np.where(mane_tip, _rad(20), lift)
        sp = np.where(mane_tip, 0.016, sp)
        # build 1: longer cards standing 35° off the ball read as grey shards; a short, flatter fuzz instead
        L = np.where(pom, 0.028, L)
        W = np.where(pom, 0.026, W)
        lift = np.where(pom, _rad(16), lift)
        sp = np.where(pom, 0.012, sp)
        L = np.where(fet, 0.05, L)
        W = np.where(fet, 0.04, W)
        lift = np.where(fet, _rad(18), lift)
        sp = np.where(fet, 0.016, sp)
        L = np.where(ear_rim, 0.04, L)
        W = np.where(ear_rim, 0.03, W)
        lift = np.where(ear_rim, _rad(12), lift)
        sp = np.where(ear_rim, 0.013, sp)
        L = np.where(tuft, 0.1, L)
        W = np.where(tuft, 0.034, W)
        lift = np.where(tuft, _rad(5), lift)
        sp = np.where(tuft, 0.022, sp)
        skip = ~(mane_tip | pom | fet) | (covered & ~pom) | z['fore']
    # no card across a colour edge (a patch's cream outline, a stripe, a mane band): a card takes the skin's colour at
    # its root, so its tip must land on the same tone (a chestnut card over cream glitters at the edge)
    live = ~skip
    if live.any() and 'body' in _SEEDS:
        tip = p[live] + flow(p[live], n[live]) * L[live, None] * 0.85
        lum = v3((0.2126, 0.7152, 0.0722))
        t_root = coat_tone(p[live]) @ lum
        t_tip = coat_tone(tip) @ lum
        cross = np.abs(t_root - t_tip) > 0.12
        skip[np.nonzero(live)[0][cross]] = True
    return np.where(skip, np.nan, sp), L, W, lift, z


def coat_tone(p: np.ndarray) -> np.ndarray:
    """The coat's flat colour (linear RGB) at points p, without the face's painted details."""
    z = zones(p)
    return coat_rgb(p, z, coat_masks(p, z, _SEEDS['body']), PALETTE)


# ----------------------------------------------------------------------------- the rig's weights
def ear_weights(p: np.ndarray, u: np.ndarray) -> dict[str, np.ndarray]:
    w2 = smooth(0.45, 0.9, u)
    w1 = (1 - w2) * smooth(0.0, 0.3, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def body_weight_regions(co: np.ndarray, names: list[str]):
    z = zones(co)
    regions = []
    for s, tag in ((1, 'L'), (-1, 'R')):
        on = z['ear'] & (np.sign(co[:, 0]) == s)
        if on.any():
            w = ear_weights(co[on], np.clip(z['ear_u'][on], 0, 1))
            regions.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    # the tail: the stalk and the tuft follow the chain by how far along it they lie
    tl = z['tail']
    if tl.any():
        tails = [f'tail.{i + 1}' for i in range(len(TAIL_POINTS) - 1)]
        regions.append((tl, U.chain_weights(co[tl], TAIL_POINTS, tails, 'hips', fade=(0.03, -0.04))))
    # the hooves ride their hoof bones rigidly (the proxy body has no hooves)
    for leg, m in z['legs'].items():
        hv = m & (co[:, 2] < SP.HOOF_H - 0.006)
        if hv.any() and f'foot.{leg}' in names:
            regions.append(U.rigid(hv, f'foot.{leg}'))
    return regions


CLIP_CALM = {    # big ears and a long tuft: calmer in the big poses (ART_2_DETAIL §9.2)
    '*': {'ear': 0.65},
    'ko': {'ear': 0.2, 'tail': 0.5},
    'hit': {'ear': 0.45},
    'hit_heavy': {'ear': 0.3, 'tail': 0.6},
    'win': {'ear': 0.4, 'tail': 0.6},
    'strike': {'ear': 0.3},
    'sidestep_l': {'ear': 0.5},
    'sidestep_r': {'ear': 0.5},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the brown iris, pupil, catchlights and the upper lash line baked into '
             'the atlas; the long lashes are small props on the blink bones (a blink folds them down onto the closed lid). '
             'The dark brows, the blush, the nostrils, the freckles and the small smile are baked into the body. No face '
             "sheet and no morphs: expressions in clips' `faces` are hints only. Blinking scales the blink bones (play "
             '`blink` over any clip): each lens squashes onto the closed lid\'s lash line and sinks into the head.')
