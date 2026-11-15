"""Plumdrake at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md, the
"Biped plan" section).

A big, chunky, huggable cloud dragon standing upright: a gentle giant (chatgpt/monsters/32-plumdrake/; the card decides
the parts, 1-hero the shapes, 2-turnaround the measurements, CONTENT §2.2 #32 the colours):
  - a heavy pear-shaped body on two thick, short legs with broad three-toed feet and blunt cream claws; short, strong
    arms with four-fingered hands (three fingers and a thumb) and cream claws;
  - small, smooth, overlapping plum leaf scales with a satin sheen (laid like shingles on the high body and baked: bigger
    on the back, flanks and thighs, small on the head), meeting a big soft round lilac belly in a scaly border; the belly
    velvety and dusted with tiny darker freckles; the throat and the chin lilac too;
  - a broad rounded head with a wide friendly snout, two small round nostrils, a big warm smile with two little rounded
    cream fangs, big kind amber eyes under soft brow ridges and thick dark brows, a faint blush; small pink-lined ears
    under the horns; a crest of spiky plum locks over the crown and down the back of the head (every picture, not on
    the card's list; kept, like Hearthwing's frills);
  - two short, curled cream ram horns with fine growth ridges, curling back behind the eyes (plumdrake_horns.py);
  - a fluffy cloud-white ruff round the neck and shoulders, and a matching fluffy puff on the tip of the long thick tail
    that lies on the ground (body clumps with lying locks baked in; plumdrake_form.py);
  - two big broad wings (three fingers each): dusky-blue membranes between plum finger bones, a plum scaled arm, and
    two rows of soft cloud-white feathers along the trailing edge (plumdrake_wings.py).

Colours: CONTENT §2.2 #32: scales #7A4E9C, belly #D8C4EE, membranes #5D78B8, eyes #F2A93B, with the card's freckles
#B49AD6, ruff #F5F3FA and horns #F1E3C6. Parts the palette has no colour for are derived from it (`colours`): the
brows and the lash line (the plum, darker), the blush and the inner ears (the lilac toward the amber), the mouth (the
plum, darker and warmer), the pupils (the plum near black), the scales' highlight (the plum toward the lilac).
Stormcloud Plumdrake (secrets.ts `stormcloud-plumdrake`, "storm-grey scales and a silver ruff"; src/art/monster/variants.ts
#5A6070 / #C9D0DC / #3E5C8C / #8FD3FF, and the variant card's freckles #A4AEBE and silver #E9EEF5 for the ruff, the puff
and the feathers): the picture and variants.ts recolour the scales, belly, membranes and eyes too, so it follows them;
the horns, fangs and claws stay cream. The card's "faint crackle of light" in the mane is left out (a crackle pattern
was an originality concern on Stormcrown Nimbusheep).

Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib import marks as MK
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3
from monsters.breeds import hearthwing_mouth as MO
from monsters.breeds import hearthwing_parts as HP
from monsters.breeds import plumdrake_feathers as FE
from monsters.breeds import plumdrake_fluff as FL
from monsters.breeds import plumdrake_form as F
from monsters.breeds import plumdrake_horns as H
from monsters.breeds import plumdrake_wings as WG

ID = 'plumdrake'
LOOK = 'plumdrake-ultra'
PLAN = 'biped'
HEIGHT_UNITS = 270                       # 1.8 x Puddlepup (PROMPTS.md): about 1.78 m to the crest's tip

PALETTE = {'body': '#7A4E9C', 'belly': '#D8C4EE', 'accent': '#5D78B8', 'eye': '#F2A93B',
           'freckle': '#B49AD6', 'ruff': '#F5F3FA', 'horn': '#F1E3C6'}
VARIANTS = {'stormcloud-plumdrake': {'body': '#5A6070', 'belly': '#C9D0DC', 'accent': '#3E5C8C', 'eye': '#8FD3FF',
                                     'freckle': '#A4AEBE', 'ruff': '#E9EEF5', 'horn': '#F1E3C6'}}


def colours(pal: dict) -> dict:
    """Every derived colour of a palette (the base or a variant)."""
    body, belly, eye, ruff, horn = pal['body'], pal['belly'], pal['eye'], pal['ruff'], pal['horn']
    return {
        'body': body, 'belly': belly, 'accent': pal['accent'], 'eye': eye, 'freckle': pal['freckle'], 'ruff': ruff, 'horn': horn,
        'scale_dark': C.shade_hex(body, 0.62),               # a scale's root, tucked under the one before
        'scale_rim': C.shade_hex(body, 0.5),                 # the fine outline and the gaps
        'scale_hi': C.mix_hex(body, belly, 0.42),            # the satin highlight toward each scale's free edge (lesson 2)
        'lip': C.mix_hex(body, belly, 0.45),                 # the upper lip, lighter
        'crest_tip': C.mix_hex(body, belly, 0.2),
        'brow': C.shade_hex(body, 0.36),
        'lash': C.shade_hex(body, 0.2),
        'pupil': C.mix_hex(body, '#000000', 0.88),
        'mouth': C.mix_hex(C.shade_hex(body, 0.32), eye, 0.12),
        # the inner mouth (round 2), from the palette: a deep plum-rose palate and gums, a warm pink tongue, a dark throat
        'palate': C.mix_hex(C.shade_hex(body, 0.55), eye, 0.3),
        'gum': C.mix_hex(C.shade_hex(body, 0.62), eye, 0.35),
        'tongue': C.mix_hex(C.mix_hex(belly, body, 0.3), eye, 0.42),
        'throat': C.shade_hex(body, 0.22),
        'blush': C.mix_hex(belly, C.mix_hex(body, eye, 0.5), 0.5),
        'ear_in': C.mix_hex(belly, C.mix_hex(body, eye, 0.5), 0.42),
        'pad': C.mix_hex(belly, ruff, 0.15),         # round 3: pale paw pads
        'freckle_face': C.mix_hex(body, C.shade_hex(body, 0.6), 0.6),
        'velvet_lo': C.mix_hex(belly, body, 0.1),
        'fluff_root': C.mix_hex(C.mix_hex(ruff, belly, 0.35), horn, 0.25),     # warm lilac-cream in the fluff's depths
        'fluff_tip': C.mix_hex(ruff, '#FFFFFF', 0.35),
        'horn_groove': C.mix_hex(C.shade_hex(horn, 0.74), body, 0.06),
        'horn_hi': C.mix_hex(horn, '#FFFFFF', 0.45),
        'horn_root': C.shade_hex(horn, 0.8),
        'membrane_lite': C.mix_hex(pal['accent'], belly, 0.22),
        'membrane_dark': C.mix_hex(C.shade_hex(pal['accent'], 0.72), body, 0.25),
        'feather_root': C.mix_hex(ruff, C.mix_hex(belly, pal['accent'], 0.4), 0.38),
        'feather_quill': C.mix_hex(ruff, belly, 0.45),
        'iris_deep': C.mix_hex(C.shade_hex(eye, 0.52), body, 0.12),
        'iris_lite': C.mix_hex(eye, '#FFFFFF', 0.3),
        'sclera': C.mix_hex('#FFFFFF', belly, 0.1),
    }


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def blend(rgb: np.ndarray, k, hexcol: str) -> np.ndarray:
    return HP.blend(rgb, k, hexcol)


# ============================================================================= settings
BODY_TRIS = 56000                        # the ruff's wisps, the crest and the puff reach the silhouette
VOXELS = {'hi': 0.0033, 'hi_quick': 0.006, 'lo': 0.0065}
ATLAS_DENSITY = {'lo_eyes': 1.35, 'lo_fins': 0.6, 'lo_props': 0.8}
UV_SMOOTH = 100                          # the scaly, lumpy body unwraps smoothed into fewer, larger islands
NORMAL_SCALE = 0.9                       # round 2: the ruff's relief read as crumpled paper at 1.1
# round 2: the fluff's crevices and the scales' gaps never bake near black (dark specks through the white ruff)
AO_FLOOR = 0.72                          # polish: the fluff's crevices a pale lilac-grey, never dirt-grey
AO_SOFTEN = 2.5
BODY_SHEEN = 0.25                        # round 3: a softer sheen, so the white fluff never glints
# round 2c: no fur cards (Nimbusheep's lesson, nimbusheep_ultra.card_params: cards on white wool read as glassy white
# flakes in the game, whatever their size or lift; ours read as broken glass). The fluff reads soft from its rounded
# lobes, the lying locks baked into the maps and the film's fur sheen; the islands take the whole atlas again.
CARD_LAYERS = 0
ATLAS_STRIP = 0
MEMBRANE_AO_BODY = False                 # the folded wings leave no baked shadow on the back (it stays when they spread)
LITE_PROPS_TRIS = 3200                   # the horns, claws and wing bones are the signature
BLINK_CLOSED = (0.74, 0.04, 0.2)
# the jaw's heat weights go to the head (the heat solve gave the jaw bone, which runs the snout's length, ~0.9 of the
# whole snout, so the strike and the smiles dropped the upper snout off the palate and the fangs: the 'stick' at the
# strike's impact); the jaw moves only the lower jaw's skin below the cut lips (jaw_weights; rig_p 'jaw_open')
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
LOCK_TEMPLATES = {'head': (7, 11, 3, 0.2), 'body': (5, 9, 3, 0.26)}
MOUTH_SOCKET = (0.0, -0.44, 1.34)


# ============================================================================= the body
def all_parts() -> list[Part]:
    return F.all_parts()


def body_extras() -> list[bpy.types.Object]:
    return FL.body_extras()


CORE = F.core_parts()
RUFF = FL.ruff()
PUFF = FL.puff()
CREST = FL.crest()
EARS = FL.ears()
HEAD_PARTS = F.head_parts()[:-1]          # without the neck
RUFF_CORE = F.ruff_parts()


# ============================================================================= the face's lines
def lip(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """The lip line's height at (x, y): a gentle U across the snout's front, then along its sides rising into the cheeks
    (round 2: a big warm smile; 3-faces, 4-details panel 1)."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    # round 2b: a deeper U at the front and corners rising sooner and higher (it read as a flat line from the front)
    return F.SMILE_Z0 + 0.024 * np.minimum((x / 0.1) ** 2, 1.0) + 0.052 * smooth(-0.36, F.CORNER_Y, y) ** 1.1


def smile_z(x: np.ndarray) -> np.ndarray:
    """The lip's height at the snout's front (the fangs, the lip's paint)."""
    return lip(x, np.full(np.shape(x), -0.45))


# the mouth's cut (hearthwing_mouth): the low body parts along the lip line; an inner mouth with a tongue behind it
# polish: the cut stops at y -0.235, on the snout's side (at the corners under the eyes its slit and the inner mouth
# poked out of the jowls); the painted smile carries on up into the cheeks (SMILE_PAINT); the inner mouth's two small
# fangs sit deep inside (they hung out as beads when the jaw opened); ours are the two props
MOUTH = {'lip': lip, 'corner_y': -0.235, 'x_max': 0.16, 'z_band': 0.026, 'back_y': -0.21, 'hinge_y': -0.17,
         'jaw_z0': 0.075, 'fang_y': -0.225, 'k': 1.3, 'tris': 1400}
SMILE_PAINT = {**MOUTH, 'corner_y': F.CORNER_Y, 'x_max': 0.2}


def mouth_mask(co: np.ndarray) -> np.ndarray:
    """0..1 on the lip line (the closed smile's groove), a little wider toward the corners' dimples."""
    m = np.zeros(len(co))
    reg = MO.cut_region(SMILE_PAINT, co) & (co[:, 2] > 1.25)
    if reg.any():
        f = MO.lip_f(SMILE_PAINT, co[reg])
        w = 0.0032 + 0.0018 * smooth(-0.24, F.CORNER_Y, co[reg, 1])
        m[reg] = np.exp(-(f / w) ** 2) * smooth(F.CORNER_Y + 0.012, F.CORNER_Y - 0.004, co[reg, 1])
    return m


LID_LASH, LID_DROP, LID_W = 0.06, 0.15, 0.95


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens: the soft closed lid and its curved lash line, shown only while a blink sinks the lens."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = F.eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax, ay = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1]
        r2 = (xe / ax) ** 2 + (ye / ay) ** 2
        front = ze > -0.04
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * F.EYE_R
        th = 0.0035 + 0.003 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 0.92) & (r2 < 1.1)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(0.92, 0.78, np.abs(xn)))
    return bulge, lash


def eye_rim(co: np.ndarray) -> np.ndarray:
    """0..1 on the skin just round each lens' upper half (the lid line, thicker toward the outer corner)."""
    out = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = F.eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        rr = np.sqrt((xe / (F.EYE_R * F.EYE_SHAPE[0])) ** 2 + (ye / (F.EYE_R * F.EYE_SHAPE[1])) ** 2)
        up = ye / F.EYE_R
        outer = smooth(-0.1, 0.8, xe * s / F.EYE_R)
        th = 0.06 + 0.08 * outer
        out = np.maximum(out, np.exp(-((rr - 1.0) / th) ** 2) * smooth(-0.25, 0.3, up) * (ze > -0.9 * F.EYE_R))
    return out


# ============================================================================= zones
def _belly_k(p: np.ndarray) -> np.ndarray:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    half = 0.25 + 0.06 * smooth(0.95, 0.45, z)
    e = np.sqrt((x / half) ** 2 + ((z - 0.565) / 0.415) ** 2)
    return smooth(1.05, 0.93, e) * smooth(-0.02, -0.14, y)


def _throat_k(p: np.ndarray) -> np.ndarray:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    return smooth(0.17, 0.12, np.abs(x)) * smooth(-0.12, -0.18, y) * smooth(0.88, 0.95, z) * smooth(1.34, 1.3, z)


def _head_mask(p: np.ndarray) -> np.ndarray:
    hc, hr = v3(F.HEAD_C), v3(F.HEAD_R)
    return (in_ellipsoid(p, tuple(hc + v3((0.0, -0.08, -0.04))), tuple(hr * v3((1.3, 1.6, 1.3)))) < 1.0) & (p[:, 2] > 1.24)


def collar(p: np.ndarray) -> np.ndarray:
    """0..1: the skin under the ruff's footprint (round 3: the skin showing between its lobes baked as white blotches on
    the plum shoulders, nape and chest): white from under the jaw down to a soft line round the shoulders, the bib's
    point in front and the back's point behind (1-hero, 2-turnaround)."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    th = np.degrees(np.arctan2(x, -(y + 0.05)))
    a = np.abs(th)                                            # 0 the front .. 180 the back
    lo = np.interp(a, [0, 25, 60, 90, 135, 165, 180], [0.92, 0.97, 1.03, 1.05, 1.06, 1.03, 1.01])
    # polish: lower at the sides (1.27) and the back (1.36) and under the chin (the white crept onto the jowls, the nape
    # and the back of the head), and never on the head itself
    hi = np.interp(a, [0, 40, 90, 140, 180], [1.16, 1.2, 1.27, 1.33, 1.36])
    # round the neck and over the shoulders' tops (the skin showed plum through the side lobes), not the arms below
    near = smooth(0.5, 0.42, np.hypot(x, y + 0.05))
    off_head = smooth(1.0, 1.15, in_ellipsoid(p, tuple(v3(F.HEAD_C) + v3((0.0, -0.06, -0.02))), tuple(v3(F.HEAD_R) * v3((1.15, 1.45, 1.15)))))
    return smooth(lo - 0.01, lo + 0.02, z) * smooth(hi + 0.01, hi - 0.02, z) * near * off_head


def _zones(p: np.ndarray) -> dict:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    n = len(p)
    ax = np.abs(x)
    m = lambda q, s: F.mirror(q, s)
    # the fluff: nearer the ruff's or the puff's volumes than the body's own parts
    # round 3 (a bug): outside the regions measured below, a point counts as on the body (sd_core 0) and far from the
    # fluff (9 m); round 2 left both at 9 m, so the masks came out about 0.16 there and washed the lower body lilac-grey
    sd_core = np.zeros(n)
    sd_r = np.full(n, 9.0)
    sd_p = np.full(n, 9.0)
    up = z > 0.7
    pc = F.puff_centre()
    near_p = np.linalg.norm(p - pc, axis=1) < 0.5
    meas = up | near_p
    if meas.any():
        # the whole body (legs and rump too: near the puff only the tail counted, so the haunch painted white)
        sd_core[meas] = F.sd_parts(p[meas], CORE)
    if up.any():
        sd_r[up] = np.minimum(F.sd_parts(p[up], RUFF_CORE), F.clump_sd(p[up], RUFF))
    if near_p.any():
        sd_p[near_p] = np.minimum(np.linalg.norm(p[near_p] - pc, axis=1) - F.PUFF_R, F.clump_sd(p[near_p], PUFF))
    ruff = np.maximum(smooth(-0.004, 0.012, sd_core - sd_r), collar(p))
    puff = smooth(-0.004, 0.012, sd_core - sd_p) * near_p
    # round 2: the crest is soft plum wisps (FL.crest), its tips lighter; the ears small pointed leaves (FL.ears)
    sd_c = np.full(n, 9.0)
    t_c = np.zeros(n)
    sd_e = np.full(n, 9.0)
    hz = z > 1.3
    if hz.any():
        sd_c[hz], t_c[hz], _w = F.clump_sd(p[hz], CREST, with_t=True)
        sd_e[hz] = F.clump_sd(p[hz], EARS)
    sd_head = np.zeros(n)               # outside the head's band: no crest, no ear (the masks below come out 0)
    if hz.any():
        sd_head[hz] = F.sd_parts(p[hz], HEAD_PARTS)
    on_c = smooth(-0.004, 0.01, sd_head - sd_c)
    crest = on_c * smooth(0.0, 0.06, t_c)
    ear_k = smooth(-0.003, 0.008, sd_head - sd_e)
    ruff = ruff * (1.0 - on_c) * (1.0 - ear_k)
    # round 2c: no white on the cheeks above the jaw line (flecks at the mouth's corners)
    ruff = ruff * (1.0 - smooth(1.31, 1.36, z) * smooth(-0.02, -0.08, y))
    ear_in = np.zeros(n)
    for s in (1, -1):
        b = v3(F.mirror(F.EAR['base'], s))
        ear_in = np.maximum(ear_in, ear_k * (np.sign(x) == s) * smooth(0.0, 0.006, (p - b) @ FL.ear_front(s))
                            * smooth(0.0, 0.02, (p - b) @ HP.unit(v3((F.EAR['dir'][0] * s, F.EAR['dir'][1], F.EAR['dir'][2])))))
    head = _head_mask(p) & (ruff < 0.5)
    snout = in_ellipsoid(p, F.SNOUT[0], tuple(r * 1.12 for r in F.SNOUT[1])) < 1.0
    nose = in_ellipsoid(p, F.NOSE[0], tuple(r * 1.12 for r in F.NOSE[1])) < 1.0
    muzzle = (snout | nose) & head
    eye_d = np.minimum(np.linalg.norm(p - v3(F.EYE_C[1]), axis=1), np.linalg.norm(p - v3(F.EYE_C[-1]), axis=1))
    face = head & (y < -0.17)
    chin = head & (y < -0.12) & (z < lip(x, y) - 0.004) & (ax < F.SMILE_W + 0.03)
    ear = ear_k > 0.5
    hand = np.zeros(n, bool)
    palm = np.zeros(n)
    arm = np.zeros(n, bool)
    foot = np.zeros(n, bool)
    leg = np.zeros(n, bool)
    sole = np.zeros(n)
    for s in (1, -1):
        w, h, _ac, pl = F.hand_frame(s)
        hand |= (np.linalg.norm(p - v3(w + h * 0.05), axis=1) < 0.11) & ((p - v3(w)) @ v3(h) > -0.02)
        palm = np.maximum(palm, smooth(0.0, 0.012, (p - v3(w + h * 0.04)) @ v3(pl)) * (np.linalg.norm(p - v3(w + h * 0.05), axis=1) < 0.08))
        d_arm, _t = F.seg_dist(p, m(F.SHOULDER, s), m(F.WRIST, s))
        arm |= (d_arm < 0.13) & (x * s > 0.24)
        fc = v3(m(F.FOOT_C, s))
        foot |= (z < 0.13) & (np.linalg.norm((p - fc) * v3((1.0, 0.85, 1.0)), axis=1) < 0.24)
        d_leg, _t = F.seg_dist(p, m(F.LEG_HIP, s), m(F.ANKLE, s))
        leg |= (d_leg < 0.2) & (z < 0.36) & (x * s > 0.06)
        sole = np.maximum(sole, (z < 0.02) * (np.linalg.norm((p - fc) * v3((1.0, 0.85, 0.0)), axis=1) < 0.22))
    arm &= ~hand
    leg &= ~foot
    toes = foot & (y < -0.12)
    tt, td, tr = F.tail_param(p)
    tail = (tt > 0.06) & (td < tr * 1.5 + 0.02) & (puff < 0.5) & ~foot
    # round 2: never on the legs (the thighs' fronts took a lilac speckle: the lower body read grey-lilac)
    belly = _belly_k(p) * (1.0 - ruff) * (~head) * (~arm) * (~hand) * (~leg)
    throat = _throat_k(p) * (1.0 - ruff)
    return {'ruff': ruff, 'puff': puff, 'fluff': np.maximum(ruff, puff), 'crest': crest, 'crest_on': on_c, 'crest_t': t_c,
            'head': head, 'face': face, 'muzzle': muzzle, 'snout': snout, 'nose': nose, 'eye_d': eye_d, 'chin': chin,
            'ear': ear, 'ear_in': ear_in, 'hand': hand, 'palm': palm, 'arm': arm, 'foot': foot, 'leg': leg, 'toes': toes,
            'sole': sole, 'tail': tail, 'tail_t': tt, 'belly': belly, 'throat': throat, 'sd_core': sd_core}


_ZCACHE: list = []


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict:
    p = np.asarray(p, np.float64)
    if len(p) < 20000:
        return _zones(p)
    key = (p.shape, float(p[::max(1, len(p) // 251)].sum()), float(p[-1].sum()), float(p[len(p) // 2].sum()))
    for k, v in _ZCACHE:
        if k == key:
            return v
    z = _zones(p)
    _ZCACHE.append((key, z))
    del _ZCACHE[:-6]
    return z


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(z['face'] * 0.9 + z['muzzle'] * 1.0 + (z['eye_d'] < 0.09) * 1.0 + z['toes'] * 0.6 + z['hand'] * 0.6
                   + z['fluff'] * 0.35 + z['crest'] * 0.6 + z['ear'] * 0.8 + z['belly'] * 0.35, 0, 1)


def texel_k(co: np.ndarray) -> np.ndarray:
    """lo_body's texel density per face: the face 1.7, the rest of the head 1.3, the hands and feet 1.15, the belly 0.9,
    the back under the folded wings 0.75, the rest 1."""
    z = zones(co)
    k = np.ones(len(co))
    k = np.where(co[:, 1] > 0.15, 0.8, k)
    k = np.where(z['belly'] > 0.5, 0.9, k)
    k = np.where(z['hand'] | z['foot'], 1.15, k)
    k = np.where(z['head'], 1.3, k)
    k = np.where(z['face'] | (z['eye_d'] < 0.1), 1.7, k)
    return k


def uv_smooth_mask(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    m = np.ones(len(co))
    m = np.where(z['head'], 0.35, m)
    m = np.where(z['face'] | z['muzzle'] | (z['eye_d'] < 0.1), 0.0, m)
    m = np.where(z['hand'] | z['toes'], 0.4, m)
    m = np.where(z['fluff'] > 0.5, 0.3, m)     # round 3: the ruff's lobes smeared into dash streaks when unwrapped smoothed
    return m


# ============================================================================= scales
def scale_flow(p: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Which way each scale's free edge points: back from the nose over the head, down and a little back over the body
    and the legs, down the arms toward the hands, along the tail to its tip."""
    k = len(p)
    z_ = zones(p, n)
    g_head = norm(p - v3((0.0, F.NOSE_C[1] - 0.05, F.NOSE_C[2] + 0.02)))
    g_body = norm(np.tile(v3((0.0, 0.3, -1.0)), (k, 1)))
    side = smooth(0.4, 0.9, np.abs(n[:, 1]))[:, None]
    g_body = norm(g_body * (1 - side) + np.tile(v3((0.0, 0.0, -1.0)), (k, 1)) * side)
    g = np.where(z_['head'][:, None], g_head, g_body)
    lim = np.zeros((k, 3))
    for s in (1, -1):
        da = norm((v3(F.mirror(F.HAND, s)) - v3(F.mirror(F.SHOULDER, s)))[None])[0]
        lim = np.where(((z_['arm'] | z_['hand']) & (np.sign(p[:, 0]) == s))[:, None], np.tile(da, (k, 1)), lim)
    g = np.where((z_['arm'] | z_['hand'])[:, None], lim, g)
    g = np.where((z_['leg'] | z_['foot'])[:, None], np.tile(v3((0.0, -0.15, -1.0)), (k, 1)), g)
    tc = HP.resample(np.array(F.TAIL_PTS), 60)
    T = HP.tangents(tc)
    i = np.clip((np.clip(z_['tail_t'], 0, 1) * 59).astype(int), 0, 59)
    g = np.where(z_['tail'][:, None], T[i], g)
    return tangent(g, n)


def scale_params(p: np.ndarray, n: np.ndarray):
    """Per point (spacing, NaN = none; radius; height) of the plum scales (1-hero, 4-details panel 6: big on the back,
    the flanks and the thighs, smaller on the arms, small on the head; none on the belly, the throat, the chin, the
    fluff, the crest, round the eyes, on the snout's tip or under the feet)."""
    z = zones(p, n)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    sp = np.full(len(p), 0.07)
    sp = np.where(zz > 0.95, 0.05, sp)
    sp = np.where(z['arm'], 0.042, sp)
    sp = np.where(z['hand'], 0.024, sp)
    # round 2: the leg's scales shrink smoothly into the foot's (a size step read as a boot's seam)
    sp = np.where(z['leg'] | z['foot'], 0.034 + 0.022 * smooth(0.06, 0.3, zz), sp)
    sp = np.where(z['tail'], 0.065 - 0.035 * np.clip(z['tail_t'], 0, 1), sp)
    sp = np.where(z['head'], 0.021, sp)
    sp = np.where(z['head'] & (z['muzzle'] | (y < -0.22)), 0.016, sp)
    # near the belly's border the scales shrink a little (4-details panel 6)
    sp = sp * (1.0 - 0.3 * smooth(0.05, 0.45, z['belly']))
    h = np.where(z['head'], sp * 0.13, sp * 0.17)
    skip = (z['belly'] > 0.5) | (z['throat'] > 0.4) | z['chin'] | (z['fluff'] > 0.25) | (z['crest'] > 0.1) | z['ear']
    skip |= (z['eye_d'] < F.EYE_R * 1.45) | (z['sole'] > 0.5) | (z['palm'] > 0.5)
    # the face stays smooth (fine freckles, no scales): the snout, the cheeks' fronts, round the mouth (3-faces); the
    # forehead, the crown, the back of the head and the cheeks' backs keep small scales
    # round 2: no scales below the eyes' tops on the face's sides either (a ragged scaled patch on the cheek)
    skip |= z['head'] & (z['muzzle'] | ((y < -0.02) & (zz < 1.47)))
    skip |= (mouth_mask(p) > 0.05) | (z['head'] & (zz < lip(x, y) + 0.012) & (y < -0.2))
    return np.where(skip, np.nan, sp), sp * 1.28, h


_PLATES: dict = {}


def nostrils(co: np.ndarray) -> np.ndarray:
    """0..1 in the two small round nostrils on top of the nose's tip (4-details panel 1)."""
    out = np.zeros(len(co))
    for s in (1, -1):
        c = v3((F.NOSTRIL_DX * s, F.NOSE_C[1], F.NOSE_C[2] + F.NOSTRIL_DZ))
        d = np.linalg.norm((co - c) / v3((1.25, 1.0, 1.4)), axis=1)
        out = np.maximum(out, np.exp(-(d / F.NOSTRIL_R) ** 2))
    return out


def carve_low(ob: bpy.types.Object) -> None:
    """The mouth's cut along the lip line on the low body, before its decimation (hearthwing_mouth): the lips part a
    hairline and the jaw's skin opens off it."""
    MO.cut(ob, MOUTH)
    ob['mouth_cut'] = 1


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    groove = mouth_mask(co)
    nos = nostrils(co)
    cleft = np.zeros(len(co))
    for s in (1, -1):
        tc = F.toe_centres(s)
        for a, b in zip(tc[:-1], tc[1:]):
            mm = (a + b) * 0.5
            d = np.sqrt(((x - mm.x) / 0.007) ** 2 + ((y - (mm.y - 0.02)) / 0.05) ** 2)
            cleft = np.maximum(cleft, np.exp(-d ** 2) * (z < 0.09) * (z > 0.005))
    bulge, lash = closed_lid(co)
    disp = -0.0045 * groove - 0.006 * nos - 0.007 * cleft + 0.0025 * bulge - 0.0012 * lash
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)
    # the scales: shingles from a Poisson set of plates on the skin (hearthwing_parts.shingle_field)
    co2, vn2 = S.mesh_arrays(ob)
    flow_ = scale_flow(co, vn2)
    sp, rad, h = scale_params(co, vn2)
    plates = U.plate_layout(co2, vn2, sp, rad, h, seed=32, flow=flow_, aspect=1.25, wobble=0.1)
    f = HP.shingle_field(co2, vn2, plates, leaf=0.7)
    rib = HP.scale_midrib(co2, plates, f['pid'])
    on = f['pid'] >= 0
    hh = f['h'] + 0.0005 * rib * on - 0.0004 * (~on) * (np.isfinite(sp))
    S.set_positions(ob, co2 + vn2 * hh[:, None])
    S.add_attr(ob, 'scale_id', np.where(on, f['pid'], -1).astype(np.float64))
    S.add_attr(ob, 'scale_ul', np.where(on, f['ul'], 0.0))
    S.add_attr(ob, 'scale_rho', np.where(on, f['rho'], 2.0))
    S.add_attr(ob, 'midrib', rib * on)
    C.log(f'{ob.name}: {len(plates["c"])} scales over {int(on.sum())} of {len(co)} vertices; relief up to {float(hh.max()) * 1000:.1f} mm')
    _PLATES.clear()
    _PLATES.update({'n': len(co), 'on': on, 'rho': f['rho'], 'ul': f['ul']})


# ============================================================================= the eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 32
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    sx, sy, sz = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1], F.EYE_R * F.EYE_DEPTH[0]
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = F.eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((sx, sy, sz)))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def blink_pivot(s: int):
    c, _xax, yax, look = F.eye_frame(s)
    return c - yax * (F.EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (F.EYE_R * 0.6), yax, look


IRIS_R, PUPIL_R = 0.66, 0.31


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """Big, kind eyes (4-details panel 2, 3-faces): warm white showing round a large iris that runs from a deep ring at
    its rim through the eye colour to a lighter crescent below the pupil, radial fibres, a big dark pupil, a thick dark
    upper lash line flicking out at the outer corner, and two crisp catchlights that sit up and toward the key light."""
    col = colours(pal or PALETTE)
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    ix = nb.math('ADD', x, nb.math('MULTIPLY', side, 0.05))
    iy = nb.math('ADD', y, 0.02)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), IRIS_R)
    pr = PUPIL_R / IRIS_R
    iris = nb.ramp(ri, [(0.0, C.lin(col['pupil'])), (pr * 0.97, C.lin(col['pupil'])), (pr + 0.04, C.lin(col['iris_deep'])),
                        (pr + 0.16, C.lin(C.mix_hex(col['eye'], col['iris_deep'], 0.35))), (0.72, C.lin(col['eye'])),
                        (0.88, C.lin(col['eye'])), (0.95, C.lin(col['iris_deep'])), (1.0, C.lin(C.mix_hex(col['iris_deep'], col['pupil'], 0.5))),
                        (1.05, C.lin(col['sclera'])), (1.8, C.lin(col['sclera']))])
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 40.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', nb.smooth(ri, pr + 0.05, 0.6), nb.smooth(ri, 0.97, 0.85)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.2), iris, nb.rgb(C.lin(col['iris_lite'])))
    low = nb.math('MULTIPLY', nb.smooth(iy, -0.05, -0.55), nb.math('MULTIPLY', nb.smooth(ri, 0.97, 0.62), nb.smooth(ri, pr, pr + 0.14)))
    c = nb.mix(nb.math('MULTIPLY', low, 0.5), iris, nb.rgb(C.lin(col['iris_lite'])))
    rr = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(rr, 0.72, 0.98), nb.smooth(ri, 1.02, 1.12)), 0.3), c,
               nb.rgb(C.lin(C.mix_hex(col['sclera'], col['body'], 0.25))))
    big =nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, 0.2), nb.math('DIVIDE', nb.math('SUBTRACT', iy, 0.24), 1.1), 0.0)), 0.17, 0.135)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, 0.17), nb.math('ADD', iy, 0.2), 0.0)), 0.075, 0.055)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', x, side), 0.15, 0.95), 0.18)
    lash = nb.smooth(nb.math('ADD', y, outer), 0.72, 0.8)
    c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= the coat: lying locks on the fluff and the crest
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    k = len(p)
    radial = p - v3((0.0, -0.05, 0.0))
    radial[:, 2] = 0.0
    radial = norm(radial + 1e-9)
    g = norm(v3((0.0, 0.0, -1.0))[None] + radial * 0.5)
    # the cheek wisps flick out and back
    hi = (p[:, 2] > 1.27)[:, None]
    g = np.where(hi, norm(radial + v3((0.0, 0.5, -0.4))[None]), g)
    pc = F.puff_centre()
    _tip, pax = F.puff_axis()
    rp = norm(p - pc + 1e-9)
    swirl = norm(np.cross(pax[None], rp) + 1e-9)
    g = np.where((z['puff'] > 0.5)[:, None], norm(rp + swirl * 0.6), g)
    # the crest: up and back along each lock
    g = np.where((z['crest'] > 0.05)[:, None], np.tile(v3((0.0, 0.7, 0.7)), (k, 1)), g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


def _deep_fluff(z: dict) -> np.ndarray:
    """0..1: well inside the ruff or the puff (round 2: locks and cards at its edge lay white strands over the plum
    shoulders, arms and neck in the bake)."""
    return z['fluff'] * smooth(0.6, 0.95, z['fluff'])


# round 3: no lying locks on the crest (their dark roots darkened the back of the head, near black on Stormcloud)


def body_lock_params(p, n):
    """The ruff, the cheek wisps and the tail puff: soft cloud-white strands (4-details panel 5), only well inside."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.055)
    W = np.full(k, 0.017)
    lift = np.full(k, _rad(7.0))
    L = np.where(z['puff'] > 0.5, 0.05, L)
    L = np.where(p[:, 2] > 1.28, 0.042, L)
    skip = (_deep_fluff(z) < 0.9) | (z['crest'] > 0.1) | (z['sd_core'] < 0.03) | (p[:, 2] > 1.27)
    return np.where(skip, np.nan, W * 0.6), L, W, lift, z


def card_params(p, n, layer: int):
    """Soft fur cards (round 2: the ruff and the puff read as hard paper plates). Layer 0: long thin hair strands over
    the ruff and the cheek wisps, standing out so its outline turns soft and wispy (the film fades them where they
    face the camera). Layer 1: curly wool tufts over the puff. None near the fluff's edge (white over plum)."""
    z = zones(p, n)
    k = len(p)
    deep = (_deep_fluff(z) > 0.8) & (z['sd_core'] > 0.02) & (z['crest'] < 0.1) & (p[:, 2] < 1.27)
    if layer == 0:
        on = deep & (z['ruff'] > 0.85)
        L = np.full(k, 0.11)
        W = np.full(k, 0.05)
        lift = np.full(k, _rad(30.0))
        sp = np.full(k, 0.03)
    else:
        on = deep & (z['puff'] > 0.9)
        L = np.full(k, 0.09)
        W = np.full(k, 0.055)
        lift = np.full(k, _rad(40.0))
        sp = np.full(k, 0.036)
    return np.where(on, sp, np.nan), L, W, lift, z


# ============================================================================= props: the horns, the fangs, the claws, the wings
P_HORN, P_FANG, P_HCLAW, P_FCLAW = 1, 2, 3, 4


PROP_ATTRS = {'part': 1, 'pside': 1, 'pt': 1, 'pg': 1, 'pq': 1, 'fq': 1, 'fwuv': 3}


def _prop_attrs(ob: bpy.types.Object, kind: int, side: float, t=None, g=None, q=None) -> bpy.types.Object:
    n = len(ob.data.vertices)
    S.add_attr(ob, 'part', np.full(n, float(kind)))
    S.add_attr(ob, 'pside', np.full(n, float(side)))
    S.add_attr(ob, 'pt', np.zeros(n) if t is None else np.asarray(t, np.float64))
    S.add_attr(ob, 'pg', np.zeros(n) if g is None else np.asarray(g, np.float64))
    S.add_attr(ob, 'pq', np.zeros(n) if q is None else np.asarray(q, np.float64))
    if 'UVMap' not in ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    return ob


def _complete_attrs(ob: bpy.types.Object) -> bpy.types.Object:
    """Every prop carries the same point attributes (the build joins props keeping only the common ones)."""
    n = len(ob.data.vertices)
    for a, dim in PROP_ATTRS.items():
        if a not in ob.data.attributes:
            S.add_attr(ob, a, np.zeros(n) if dim == 1 else np.zeros((n, dim)))
    return ob


def build_horns(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for s in (1, -1):
        ob = H.build_horn(f'{tag}_horn{"L" if s > 0 else "R"}', s, high, quick)
        hr = S.attr_array(ob, 'horn').astype(np.float64)
        ob['prop'] = 'horns'
        out.append(_prop_attrs(ob, P_HORN, s, hr[:, 0], hr[:, 1], hr[:, 2]))
    return out


def build_fangs(high: bool) -> list[bpy.types.Object]:
    """Two little rounded fangs peeking down over the lower lip from the upper one (every face of 3-faces)."""
    tag = 'hi' if high else 'lo'
    out = []
    for s in (1, -1):
        x = F.FANG_X * s
        zl = float(smile_z(np.array([x]))[0]) + 0.012
        hit = HP.surface_hit((x, -0.9, zl), (0.0, 1.0, 0.0), HEAD_PARTS, reach=1.0, step=0.001)
        root = (hit if hit is not None else v3((x, -0.44, zl))) + v3((0.0, 0.006, 0.0))
        # round 2: twice the size (they read as rice grains), blunt and rounded
        # round 3: short, wide-based and round-tipped, straight down (round 2's were tusks, one like a buck tooth)
        ob = HP.talon(f'{tag}_fang{"L" if s > 0 else "R"}', root, (0.0, -0.05, -1.0), (0.0, 1.0, 0.0), 0.04, 0.023,
                      curve=0.05, rings=10 if high else 6, seg=12 if high else 7, flat=0.9, blunt='cone', cap=0.75)
        out.append(_prop_attrs(ob, P_FANG, s, S.attr_array(ob, 'talon_t')))
    return out


def build_claws(high: bool) -> list[bpy.types.Object]:
    """Blunt cream claws: one on each finger and the thumb, three on each foot (1-hero, 4-details panel 3)."""
    tag = 'hi' if high else 'lo'
    out = []
    for s in (1, -1):
        w, h, _ac, palm = F.hand_frame(s)
        for k, (b, t, r) in enumerate(F.finger_tips(s)):
            d = (t - b).normalized()
            root = t - d * (r * 0.25)
            ln = 0.066 if k < 3 else 0.052
            ob = HP.talon(f'{tag}_hclaw{"L" if s > 0 else "R"}{k}', tuple(root), tuple(d), tuple(palm), ln, r * 0.86,
                          curve=0.3, rings=10 if high else 6, seg=12 if high else 7, flat=0.88, blunt='cone', cap=0.55)
            out.append(_prop_attrs(ob, P_HCLAW, s, S.attr_array(ob, 'talon_t')))
        for k, (tc, dx) in enumerate(zip(F.toe_centres(s), F.TOE_DX)):
            d = F.toe_dir(s, dx)
            # round 2: one big, blunt, rounded claw on each chunky toe (they read as thin spikes)
            root = v3(tc) + v3(d) * (F.TOE_R[1] * 0.55) + v3((0.0, 0.0, -0.01))
            dd = v3(d) + v3((0.0, 0.0, -0.38))
            ob = HP.talon(f'{tag}_fclaw{"L" if s > 0 else "R"}{k}', tuple(root), tuple(dd), (0.0, 0.0, -1.0), 0.085, 0.047,
                          curve=0.15, rings=11 if high else 6, seg=12 if high else 8, flat=0.92, blunt='cone', cap=0.62)
            out.append(_prop_attrs(ob, P_FCLAW, s, S.attr_array(ob, 'talon_t')))
    return out


P_MOUTH = 5


def build_mouth(high: bool) -> list[bpy.types.Object]:
    """Round 2: the inner mouth behind the cut lips (hearthwing_mouth: the palate, the tongue's floor, the throat), made
    from the cut low body, so only once it exists (not in the shape preview)."""
    lo = bpy.data.objects.get('lo_body')
    if lo is None or not lo.get('mouth_cut'):
        return []
    ob = MO.mouth_mesh(f'{"hi" if high else "lo"}_mouth', lo, MOUTH, target=MOUTH['tris'])
    parts = S.attr_array(ob, 'mouth_part_tmp').astype(np.float64)
    ob.data.attributes.remove(ob.data.attributes['mouth_part_tmp'])
    return [_prop_attrs(ob, P_MOUTH, 0.0, np.zeros(len(parts)), parts)]


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    out = build_horns(high, quick) + build_fangs(high) + build_claws(high) + WG.build_props(high, quick) + build_mouth(high)
    return [_complete_attrs(ob) for ob in out]


def build_fins(high: bool, quick: bool) -> list[bpy.types.Object]:
    return FE.build_fins(high, quick)


def preview_prop_colour(name: str):
    col = colours(PALETTE)
    if name.startswith('mouth'):
        return col['palate']
    if name.startswith('w'):
        return col['body']
    return col['horn']


# ============================================================================= paint
def _hash(pid: np.ndarray, seed: int) -> np.ndarray:
    return U.plate_hash(pid, seed)


def body_paint(p: np.ndarray, pal: dict, kind=None, tpos=None, lrand=None, sc=None) -> dict:
    """Per point of a body source: 'paint' (linear RGB) and 'rough' (1, roughness, clear coat). `p` is each point's root
    on the skin (a lock takes the colour under its root); `sc` the scales' attributes on hi_body."""
    col = colours(pal)
    k = len(p)
    z = zones(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    rgb = np.tile(lin(col['body']), (k, 1))
    rough = np.full(k, 0.52)
    coat = np.full(k, 0.06)
    if sc is not None:
        pid, ul, rho, mid = sc
        on = pid >= 0
        hsh = _hash(pid.astype(np.int64), 3)
        # round 2: a calmer plum (the legs, lower back and tail read as a mottled grey-lilac): less variation per scale,
        # a smaller satin highlight toward each free edge, a crisp darker outline
        rgb = rgb * (0.985 + 0.03 * hsh)[:, None]
        rootk = smooth(0.35, -0.95, ul) * on
        edge = smooth(0.8, 0.97, rho) * on
        rgb = blend(rgb, rootk * 0.45, col['scale_dark'])
        rgb = blend(rgb, mid * 0.12, col['scale_hi'])
        # polish (4-details panel 6): a soft satin highlight along each scale's free edge, a dark outline round the rest
        free = edge * smooth(0.2, 0.7, ul)
        rgb = blend(rgb, np.where(on, (edge - free) * 0.65, 0.0), col['scale_rim'])
        rgb = blend(rgb, free * 0.45, col['scale_hi'])
        gap = (~on) & (z['belly'] < 0.4) & (z['throat'] < 0.3) & ~z['chin'] & (z['fluff'] < 0.3) & (z['crest'] < 0.1)
        rgb = blend(rgb, gap * 0.45, col['scale_rim'])
        # a soft blend at the belly's border: the scales nearest it lighten toward a lilac-plum (not a jagged edge)
        rgb = blend(rgb, on * smooth(0.02, 0.5, _belly_k(p)) * 0.25, C.mix_hex(col['body'], col['belly'], 0.45))
        rough = np.where(on, 0.4 + 0.18 * edge + 0.1 * rootk, 0.55)
        coat = np.where(on, 0.2 * (1 - edge) * (1 - 0.5 * rootk) + 0.04, 0.05)
    # the smooth face (no scales: the snout, the cheeks' fronts) a touch lighter, so it reads as the same plum as the
    # scaled skin's satin average instead of a darker patch
    sface = (z['head'] & (z['muzzle'] | (y < -0.17)) & (zz < 1.5)).astype(float)
    if sc is not None:
        sface = sface * (sc[0] < 0)
    rgb = blend(rgb, sface * 0.3, col['scale_hi'])
    # the head: the upper lip lighter, the chin lilac
    lz = lip(x, y)
    ulip = (z['head'] & (zz < lz + 0.03) & (zz > lz - 0.003) & (y < -0.17)).astype(float)
    ulip = ulip * smooth(F.SMILE_W + 0.03, F.SMILE_W - 0.02, np.abs(x)) * smooth(F.CORNER_Y + 0.01, F.CORNER_Y - 0.03, y)
    rgb = blend(rgb, ulip * 0.55, col['lip'])
    # the belly and the throat: velvety lilac, a touch deeper at the edges
    bel = np.clip(np.maximum(np.maximum(z['belly'], z['throat']), z['chin'] * 1.0), 0, 1)
    if sc is not None:
        bel = np.where(sc[0] >= 0, 0.0, bel)
    vel = np.tile(lin(col['belly']), (k, 1))
    vel = blend(vel, smooth(0.9, 0.5, z['belly']) * 0.35 * (1 - z['chin']), col['velvet_lo'])
    rgb = rgb * (1 - bel[:, None]) + vel * bel[:, None]
    rough = rough * (1 - bel) + 0.72 * bel
    coat = coat * (1 - bel) + 0.0 * bel
    # the tail's underside lilac (2-turnaround side)
    tt, _td, _tr = F.tail_param(p)
    tc = HP.resample(np.array(F.TAIL_PTS), 60)
    i = np.clip((np.clip(tt, 0, 1) * 59).astype(int), 0, 59)
    under = z['tail'] * smooth(0.25, -0.45, (zz - tc[i, 2]) / np.maximum(np.array(F.TAIL_RAD).mean(), 1e-3))
    if sc is not None:
        under = np.where(sc[0] >= 0, under * 0.0, under)
    rgb = blend(rgb, under * 0.85, col['belly'])
    # pads: soles and palms lilac (4-details panel 3)
    pad = np.maximum(z['sole'], z['palm'])
    rgb = blend(rgb, pad * 0.9, col['pad'])
    rough = rough * (1 - pad) + 0.62 * pad
    # inner ears
    rgb = blend(rgb, z['ear_in'] * 0.9, col['ear_in'])
    # the crest: plum, lighter toward the tips
    cr = z['crest']
    crest_col = blend(np.tile(lin(col['body']), (k, 1)), smooth(0.25, 1.0, z['crest_t']) * 0.75, col['crest_tip'])
    rgb = rgb * (1 - cr[:, None]) + crest_col * cr[:, None]
    rough = rough * (1 - cr) + 0.58 * cr
    # the fluff: cloud white, warm lilac-cream in its depths (never grey)
    fl = z['fluff']
    fcol = np.tile(lin(col['ruff']), (k, 1))
    if kind is not None:
        lock = kind > 0.5
        t = np.clip(tpos, 0, 1)
        # polish: a calm, even white (the locks' per-strand variation read as blocky speckle up close)
        fcol = blend(fcol, np.where(lock, (1 - t) * 0.18, 0.15), col['fluff_root'])
        fcol = blend(fcol, np.where(lock, smooth(0.5, 1.0, t) * 0.3, 0.0), col['fluff_tip'])
        cl = lock & (cr > 0.2)
        crest_l = blend(np.tile(lin(col['body']), (k, 1)), smooth(0.3, 1.0, t) * 0.6, col['crest_tip'])
        rgb = np.where(cl[:, None], crest_l * (0.9 + 0.15 * lrand)[:, None], rgb)
    else:
        fcol = blend(fcol, np.full(k, 0.15), col['fluff_root'])
    rgb = rgb * (1 - fl[:, None]) + fcol * fl[:, None]
    rough = rough * (1 - fl) + 0.95 * fl
    coat = coat * (1 - fl)
    # the closed lid, under the lens: plum, under its dark lash line (the body_material draws the line)
    return {'paint': rgb, 'rough': np.stack([np.ones(k), np.clip(rough, 0.3, 1.0), np.clip(coat, 0, 0.5)], axis=1)}


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    sc = None
    if _PLATES.get('n') == len(co):
        sc = (np.where(_PLATES['on'], 1, -1), _PLATES['ul'], _PLATES['rho'], np.zeros(len(co)))
    return body_paint(co, PALETTE, sc=sc)['paint']


def _fin_paint(ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    """The wings' fins (round 2): matte, leathery dusky-blue membranes (a lighter middle in each panel, fine branching
    veins and a faint leather grain, never glossy), and the feathered band along the trailing edge: three rows of soft
    cloud-white feathers, each domed with a pale quill and a soft lilac shadow at its outline, their roots tinted with the
    membrane's blue (4-details panel 4)."""
    col = colours(pal)
    wuv = S.attr_array(ob, 'wing_uv').astype(np.float64)
    fb = S.attr_array(ob, 'fband').astype(np.float64)
    co, _vn = S.mesh_arrays(ob)
    n = len(wuv)
    u, v = wuv[:, 1], wuv[:, 2]
    rgb = np.tile(lin(col['accent']), (n, 1))
    mid = np.sin(np.pi * np.clip(u, 0, 1)) * np.sin(np.pi * np.clip(v, 0, 1))
    rgb = blend(rgb, mid * 0.4, col['membrane_lite'])          # round 3: lighter in each panel's middle, lit through
    rel = U.wing_relief(wuv, WG.NF)
    vn_ = HP.branch_veins(u, v, wuv[:, 0], seed=33, n_main=6, width=0.016, sides_of=lambda q: (0,) if q > WG.NF - 1.5 else (0, 1))
    grain = HP.cell_veins(co, 0.01, seed=21, width=0.18)
    rgb = blend(rgb, rel * 0.3, col['membrane_dark'])
    rgb = blend(rgb, vn_ * 0.42, col['membrane_dark'])
    rgb = blend(rgb, grain * 0.1, col['membrane_dark'])
    rough = 0.84 - 0.04 * rel
    # the feathers
    f = FE.field(fb)
    on = f['level'] >= 0
    aq = np.minimum(np.abs(f['q']), 1.0)
    fc = np.tile(lin(col['ruff']), (n, 1))
    fc = blend(fc, smooth(0.4, 0.0, f['s']) * (0.55 - 0.12 * np.maximum(f['level'], 0)) * on, col['feather_root'])
    fc = blend(fc, smooth(0.7, 1.0, aq) * 0.6 * on, col['fluff_root'])          # round 3: each feather's outline clear
    fc = blend(fc, f['shadow'] * 0.55, col['fluff_root'])                         # the row above's tips shade the row under
    fc = blend(fc, np.exp(-(f['q'] / 0.07) ** 2) * smooth(0.95, 0.5, f['s']) * 0.4 * on, col['feather_quill'])
    barbs = 0.5 + 0.5 * np.sin(f['s'] * 60.0 + aq * 18.0)
    fc = blend(fc, barbs * smooth(0.2, 0.9, aq) * 0.08 * on, col['fluff_root'])
    fc = blend(fc, smooth(0.6, 1.0, f['s']) * (1 - aq) * 0.35 * on, col['fluff_tip'])
    w = f['white']
    rgb = rgb * (1 - w[:, None]) + fc * w[:, None]
    rough = rough * (1 - w) + 0.8 * w
    return rgb, np.stack([np.ones(n), np.clip(rough, 0.3, 1), np.zeros(n)], axis=1)


def _prop_paint(ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal)
    part = np.round(S.attr_array(ob, 'part')).astype(int)
    t = S.attr_array(ob, 'pt').astype(np.float64)
    g = S.attr_array(ob, 'pg').astype(np.float64)
    n = len(part)
    rgb = np.tile(lin(col['horn']), (n, 1))
    rough = np.full(n, 0.4)
    coat = np.full(n, 0.25)
    co, _vn = S.mesh_arrays(ob)
    horn = part == P_HORN
    if horn.any():
        gr = np.clip(g[horn], 0, 1)
        outer = np.clip(S.attr_array(ob, 'pq').astype(np.float64)[horn], 0, 1)
        th = t[horn]
        hc = np.tile(lin(col['horn']), (int(horn.sum()), 1))
        hc = blend(hc, gr * (0.5 + 0.4 * outer), col['horn_groove'])
        # the ridges' crests painted lighter (lesson 2: bright props render darker in game)
        hc = blend(hc, (1 - gr) * (0.25 + 0.25 * outer), col['horn_hi'])
        hc = blend(hc, smooth(0.12, 0.0, th) * 0.5, col['horn_root'])
        hc = blend(hc, smooth(0.75, 1.0, th) * 0.35, col['horn_hi'])
        rgb[horn] = hc
        rough[horn] = 0.34 + 0.14 * gr
        coat[horn] = 0.3 * (1 - 0.4 * gr)
    claw = (part == P_FANG) | (part == P_HCLAW) | (part == P_FCLAW)
    if claw.any():
        cc = np.tile(lin(col['horn']), (int(claw.sum()), 1))
        cc = blend(cc, smooth(0.35, 0.0, t[claw]) * 0.35, col['horn_root'])
        cc = blend(cc, smooth(0.45, 1.0, t[claw]) * 0.4, col['horn_hi'])
        rgb[claw] = cc
        rough[claw] = 0.38
        coat[claw] = 0.28
    wing = (part == WG.P_ARM) | (part == WG.P_KNUCKLE) | (part == WG.P_FINGER)
    if wing.any():
        cells = HP.cell_veins(co[wing], 0.022, seed=13, width=0.13)
        wc = np.tile(lin(col['body']), (int(wing.sum()), 1))
        wc = blend(wc, cells * 0.65, col['scale_rim'])
        wc = blend(wc, (1 - cells) * 0.3, col['scale_hi'])
        fing = part[wing] == WG.P_FINGER
        wc = blend(wc, fing * smooth(0.2, 0.0, t[wing]) * 0.3, col['scale_dark'])
        rgb[wing] = wc
        rough[wing] = 0.45 + 0.12 * cells
        coat[wing] = 0.15
    mo = part == P_MOUTH
    if mo.any():
        mp = g[mo]
        f = MO.lip_f(MOUTH, co[mo])
        tongue = smooth(0.08, 0.05, np.abs(co[mo, 0])) * smooth(-0.001, -0.005, f)
        mc = np.tile(lin(col['palate']), (int(mo.sum()), 1))
        floor = np.tile(lin(col['gum']), (int(mo.sum()), 1)) * (1 - tongue[:, None]) + lin(col['tongue'])[None] * tongue[:, None]
        mc = np.where((mp < -0.5)[:, None], floor, mc)
        mc = np.where((np.abs(mp - 2) < 0.5)[:, None], lin(col['throat'])[None], mc)
        mc = np.where((np.abs(mp - 3) < 0.5)[:, None], lin(col['horn'])[None], mc)
        rim = smooth(0.005, 0.0015, np.abs(f)) * (np.abs(mp) < 1.5)
        mc = mc * (1 - rim[:, None]) + lin(col['mouth'])[None] * rim[:, None]
        rgb[mo] = mc
        rough[mo] = 0.5
        coat[mo] = 0.2
    fea = part == WG.P_FEATHER
    if fea.any():
        fq = S.attr_array(ob, 'fq').astype(np.float64)[fea]
        ft = t[fea]
        row = g[fea]
        fc = np.tile(lin(col['ruff']), (int(fea.sum()), 1))
        fc = blend(fc, smooth(0.45, 0.0, ft) * (0.55 - 0.25 * row), col['feather_root'])
        quill = np.exp(-(fq / 0.09) ** 2) * smooth(0.95, 0.6, ft)
        fc = blend(fc, quill * 0.45, col['feather_quill'])
        barbs = 0.5 + 0.5 * np.sin(ft * 70.0 + np.abs(fq) * 22.0)
        fc = blend(fc, barbs * smooth(0.15, 0.9, np.abs(fq)) * 0.12, col['fluff_root'])
        fc = blend(fc, smooth(0.8, 1.0, np.abs(fq)) * 0.18, col['fluff_root'])
        rgb[fea] = fc
        rough[fea] = 0.74
        coat[fea] = 0.0
    return rgb, np.stack([np.ones(n), np.clip(rough, 0.3, 1.0), np.clip(coat, 0, 0.5)], axis=1)


def _scale_attrs(ob: bpy.types.Object):
    if 'scale_id' not in ob.data.attributes:
        return None
    return (S.attr_array(ob, 'scale_id').astype(np.float64), S.attr_array(ob, 'scale_ul').astype(np.float64),
            S.attr_array(ob, 'scale_rho').astype(np.float64), S.attr_array(ob, 'midrib').astype(np.float64))


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        root = S.attr_array(ob, 'root').astype(np.float64)
        kind = S.attr_array(ob, 'kind')
        tpos = S.attr_array(ob, 'tpos').astype(np.float64)
        lrand = S.attr_array(ob, 'lrand').astype(np.float64)
        sc = _scale_attrs(ob)
        a = body_paint(root, PALETTE, kind, tpos, lrand, sc)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), body_paint(root, var, kind, tpos, lrand, sc)['paint'])
    for ob in fins:
        rgb, rc = _fin_paint(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), _fin_paint(ob, var)[0])
    for ob in props:
        rgb, rc = _prop_paint(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), _prop_paint(ob, var)[0])


# ============================================================================= per-pixel marks (the body material)
_FRECKLES: list = []


def freckles() -> list[tuple]:
    """Tiny darker freckles: about a hundred on the belly (most small, a few bigger), a few on the snout and cheeks
    (1-hero, 4-details panels 1 and 6). (centre on the skin, radius, kind 0 belly / 1 face)."""
    if _FRECKLES:
        return _FRECKLES
    rng = np.random.default_rng(3232)
    core = F.core_parts()
    pts: list = []
    tries = 0
    # round 3: scattered, mixed sizes (round 2's read as a near-regular grid of equal dots)
    while len([q for q in pts if q[2] == 0]) < 120 and tries < 6000:
        tries += 1
        x = rng.uniform(-0.27, 0.27)
        zz = rng.uniform(0.2, 0.95)
        if _belly_k(np.array([[x, -0.4, zz]]))[0] < 0.8:
            continue
        r = 0.0028 + 0.0075 * rng.random() ** 2.5
        if any((x - q[0][0]) ** 2 + (zz - q[0][2]) ** 2 < (r + q[1] + 0.01) ** 2 for q in pts):
            continue
        h = HP.surface_hit((x, -0.9, zz), (0.0, 1.0, 0.0), core, reach=1.0, step=0.002)
        if h is None:
            continue
        pts.append((tuple(map(float, h)), r, 0))
    head = F.head_parts()[:-1]
    for s in (1, -1):
        for x, zz in ((0.06, 1.405), (0.075, 1.39), (0.09, 1.41), (0.105, 1.395), (0.115, 1.42), (0.135, 1.4), (0.15, 1.385),
                      (0.165, 1.41), (0.085, 1.375), (0.125, 1.375)):
            h = HP.surface_hit((x * s, -0.9, zz), (0.0, 1.0, 0.0), head, reach=1.0, step=0.0012)
            if h is not None:
                pts.append((tuple(map(float, h)), 0.0028, 1))
    _FRECKLES.extend(pts)
    return _FRECKLES


def _brow_segments() -> list[tuple]:
    """Each brow: a thick dark arc above the eye, thickest in the middle, rising toward the outer end (3-faces)."""
    head = F.head_parts()[:-1]
    # round 3: a soft arch, both ends up, the outer one higher (round 2's slanted down to the middle: stern)
    arc = [(-0.85, 1.48, 0.045), (-0.45, 1.68, 0.075), (0.0, 1.78, 0.09), (0.45, 1.76, 0.08), (0.85, 1.6, 0.05)]
    out = []
    for s in (1, -1):
        c0 = F.EYE_C[s]
        pts = []
        for dx, dz, th in arc:
            x = c0.x + dx * F.EYE_R * s
            zz = c0.z + dz * F.EYE_R
            h = HP.surface_hit((x, -0.9, zz), (0.0, 1.0, 0.0), head, reach=1.0, step=0.001)
            pts.append(((x, float(h[1]) if h is not None else c0.y, zz), th * F.EYE_R))
        for (a, ta), (b, tb) in zip(pts[:-1], pts[1:]):
            out.append((a, b, 0.5 * (ta + tb)))
    return out


def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the paint, with the face's details and the freckles per pixel: the brows, the blush, the nostrils, the
    smile's line, the lid line and the closed lids' lash lines, the belly's and the face's freckles. The marks sit on
    the pre-carve skin ('root': the scales' relief would break them up)."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.attribute('root').outputs['Vector']
    kind = nb.attribute('kind').outputs['Fac']
    is_body = nb.math('LESS_THAN', kind, 0.5)
    c = nb.attribute(attr).outputs['Color']
    # the blush: soft, under each eye (3-faces)
    blush = None
    for s in (1, -1):
        e = _ell(nb, pos, (0.15 * s, -0.215, 1.425), (0.05, 0.05, 0.032), 0.7)
        blush = e if blush is None else nb.math('MAXIMUM', blush, e)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', blush, 0.4), is_body), c, nb.rgb(C.lin(col['blush'])))
    # the freckles
    fb, ff = [], []
    for cc, r, kk in freckles():
        (fb if kk == 0 else ff).append(MK.dot(nb, pos, cc, r))
    if fb:
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', MK.union(nb, fb), 0.85), is_body), c, nb.rgb(C.lin(col['freckle'])))
    if ff:
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', MK.union(nb, ff), 0.55), is_body), c, nb.rgb(C.lin(col['freckle_face'])))
    # the brows
    segs = [MK.line(nb, pos, a, b, w, soft=0.35) for a, b, w in _brow_segments()]
    c = nb.mix(nb.math('MULTIPLY', MK.union(nb, segs), is_body), c, nb.rgb(C.lin(col['brow'])))
    # the nostrils: two small dark ovals on the nose's front
    nos = None
    for s in (1, -1):
        e = _ell(nb, pos, (F.NOSTRIL_DX * s, F.NOSE_C[1] + 0.004, F.NOSE_C[2] + F.NOSTRIL_DZ),
                 (F.NOSTRIL_R * 1.15, 0.02, F.NOSTRIL_R * 0.8), 0.3)
        nos = e if nos is None else nb.math('MAXIMUM', nos, e)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nos, 0.85), is_body), c, nb.rgb(C.lin(col['mouth'])))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.4, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(col['mouth'])))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.6, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= the rig (plans/biped.py)
RUFF_CHAINS = [
    {'name': 'ruffF', 'parent': 'chest', 'points': [(0.0, -0.33, 1.13), (0.0, -0.375, 1.0), (0.0, -0.37, 0.87)]},
    {'name': 'ruffB', 'parent': 'chest', 'points': [(0.0, 0.26, 1.21), (0.0, 0.31, 1.09), (0.0, 0.3, 0.97)]},
]
HORNS = {'name': 'horns', 'parent': 'head', 'head': (0.0, -0.05, 1.6), 'tail': (0.0, -0.05, 1.72)}
# the hands' goals stay in front of the round belly and the ruff's bib (plans/biped.py hand_clear)
HAND_CLEAR = [
    {'bone': 'spine', 'c': (0.0, -0.07, 0.6), 'r': (0.34, 0.33, 0.37), 'margin': 0.05, 'push': (0.0, -1.0, 0.0)},
    {'bone': 'chest', 'c': (0.0, -0.26, 1.06), 'r': (0.27, 0.17, 0.2), 'margin': 0.04, 'push': (0.0, -1.0, 0.0)},
]


def rig_p() -> dict:
    return {
        'hip': (0.0, 0.0, 0.46), 'chest': (0.0, -0.02, 1.08), 'head_c': F.HEAD_C, 'head_r': 0.19,
        'legs': {'hip': F.LEG_HIP, 'knee': F.KNEE, 'ankle': F.ANKLE, 'toe': F.TOE},
        'arms': {'shoulder': F.SHOULDER, 'elbow': F.ELBOW, 'wrist': F.WRIST, 'hand': F.HAND},
        'arm_relax': 32.0,                      # the arms rest out from the round body (an A-pose of about 37 degrees)
        'tail_bones': 6, 'tail_points': F.TAIL_PTS, 'tail_ground': True, 'tail_puff': {'length': F.PUFF_LEN},
        'wings': WG.WINGS, 'manes': RUFF_CHAINS, 'props': [HORNS],
        'jaw': {'head': F.JAW_HINGE, 'tail': F.JAW_TIP}, 'jaw_open': True,
        'strike_style': 'gust', 'hand_clear': HAND_CLEAR,
        # round 2 (5-poses attack; plans/biped.py `gust`): it rears back and up onto its toes as the wings rise, then leans
        # in over the downbeat with the wings still spread and swept forward (the tips ahead of the chest), the palms
        # pushing out and the mouth open wide, turned toward the in-game strike camera's side
        'gust': {'rear': 38.0, 'toes': 0.2, 'lean': 18.0, 'yaw': 28.0, 'raise': 40.0, 'beat': 50.0, 'sweep': 38.0,
                 'push': (0.1, 1.05, 0.3), 'jaw': 30.0, 'gaze': 0.7},
        # round 3 (5-poses hit): the belly squashes, it rocks back about 15-20 degrees and takes a half-step back;
        # hit_heavy clearly bigger
        'hit_body': {'squash': 0.3, 'lean': -20.0, 'step': 0.5, 'heavy': 1.7},
        # round 3: in ko the head turns its face up out of the ruff and the ground
        'ko_head': (15.0, 6.0, 0.0),           # polish: the head droops over (round 3 propped it up on the ruff)
        # polish: win raises both hands high and wide, a beat apart from the idle (plans/biped.py `win`)
        'win': {'over': (0.5, -0.16, 1.32), 'hand': (-30.0, 0.0, 0.0)},
        # round 2: in ko the half-open wings swing back along the body as it falls (the upper one stood up)
        'ko_wings': {'flap': 20.0, 'sweep': -80.0},
    }


def jaw_weights(co: np.ndarray) -> np.ndarray:
    """The lower jaw's skin below the cut lips (hearthwing_mouth), never the ruff under the chin."""
    return MO.jaw_weight(MOUTH, co) * _head_mask(co) * (zones(co)['fluff'] < 0.3)


def ruff_weights(co: np.ndarray, z: dict) -> tuple[np.ndarray, dict]:
    """Round 2: the whole ruff rides the chest, the neck and (at the cheeks) the head only, never an arm (it stretched
    into grey streaks when the arms moved); its hanging bib and back sway a little on their chains."""
    reg = (z['ruff'] > 0.25) & (z['crest'] < 0.3) & ~z['ear']
    c = co[reg]
    zz = c[:, 2]
    wh = smooth(1.27, 1.37, zz)
    wn = smooth(1.08, 1.22, zz) * (1.0 - wh)
    w = {'head': wh, 'neck': wn, 'chest': 1.0 - wh - wn}
    for ch, front in ((RUFF_CHAINS[0], True), (RUFF_CHAINS[1], False)):
        sub = ((c[:, 1] < -0.18) if front else (c[:, 1] > 0.12)) & (zz < 1.2) & (np.abs(c[:, 0]) < 0.3)
        a = 0.6 * smooth(1.16, 0.95, zz) * smooth(0.3, 0.18, np.abs(c[:, 0])) * sub
        cw = U.chain_weights(c, ch['points'], [f"{ch['name']}.1", f"{ch['name']}.2"], 'chest')
        for b, v in cw.items():
            w[b] = w.get(b, 0.0) + v * a
        w['chest'] = w['chest'] - a
    return reg, w


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    out = []
    z = zones(co)
    # the tail and its puff: the six bones along the tail's points, the puff on its own bone
    tt, td, tr = F.tail_param(co)
    pc = F.puff_centre()
    puff = (z['puff'] > 0.3) | (np.linalg.norm(co - pc, axis=1) < F.PUFF_R + 0.03)
    tail = ((tt > 0.1) & (td < tr * 1.6 + 0.03) & (co[:, 2] < 0.55) & ~z['foot'] & ~z['leg']) | puff
    if tail.any():
        tip, d = F.puff_axis()
        pts = [tuple(p) for p in F.TAIL_PTS] + [tuple(tip + d * F.PUFF_LEN)]
        bones = [f'tail.{i + 1}' for i in range(6)] + ['tail.puff']
        out.append((tail, U.chain_weights(co[tail], pts, bones, 'hips', fade=(0.08, -0.02))))
    reg, w = ruff_weights(co, z)
    if reg.any():
        out.append((reg, {b: v for b, v in w.items() if b in names}))
    jw = jaw_weights(co)
    jm = jw > 0.01
    if jm.any() and 'jaw' in names:
        out.append((jm, {'jaw': jw[jm], 'head': 1.0 - jw[jm]}))
    return out


def fin_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    return WG.fin_regions(co, attr, names)


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    part = np.round(attr('part')).astype(int)
    side = np.round(attr('pside')).astype(int)
    regs = []
    horn = part == P_HORN
    if horn.any():
        regs.append(U.rigid(horn, 'prop.horns' if 'prop.horns' in names else 'head'))
    fang = part == P_FANG
    if fang.any():
        regs.append(U.rigid(fang, 'head'))
    mo = part == P_MOUTH
    if mo.any():
        # the palate, the throat and the fangs on the head; the floor and the tongue with the lower jaw's own blend
        g = attr('pg').astype(np.float64)
        up = mo & (g > -0.5)
        dn = mo & (g < -0.5)
        if up.any():
            regs.append(U.rigid(up, 'head'))
        if dn.any():
            jw = MO.jaw_weight(MOUTH, co[dn])
            regs.append((dn, {'jaw': jw, 'head': 1.0 - jw}))
    for s, tag in ((1, 'L'), (-1, 'R')):
        m = (part == P_HCLAW) & (side == s)
        if m.any():
            regs.append(U.rigid(m, f'hand.{tag}'))
        m = (part == P_FCLAW) & (side == s)
        if m.any():
            regs.append(U.rigid(m, f'foot.{tag}'))
    regs += WG.prop_regions(co, attr, names)
    return regs


# ============================================================================= clips
def calm_group(bone: str) -> str | None:
    """CLIP_CALM's groups (the plan's own, by the bone name's first part), plus the jaw (round 3: the grin opens wider)."""
    if bone == 'jaw':
        return 'jaw'
    pre = bone.split('.')[0]
    return pre if '.' in bone and pre in ('ear', 'tail', 'ruffF', 'ruffB', 'wing') else None


CLIP_CALM = {
    '*': {'tail': 0.8, 'ruffF': 0.6, 'ruffB': 0.6},
    # the open grin with the tongue showing: about the plan's angles (16-18 degrees) now that only the lower jaw's skin
    # moves (round 3 doubled them while the whole snout hung on the jaw and the mouth hardly showed; doubled, the
    # real opening gaped)
    'idle_happy': {'jaw': 1.15, 'tail': 0.8}, 'win': {'jaw': 1.1, 'tail': 0.8}, 'strike': {'jaw': 0.6, 'tail': 0.8},
    # round 3: the wings flinch in on a hit (the plan flares them open)
    'hit': {'wing': -0.8, 'tail': 0.8}, 'hit_heavy': {'wing': -0.6, 'tail': 0.8},
    'idle': {'wing': 0.5, 'tail': 0.8}, 'battle_idle': {'wing': 0.5, 'tail': 0.8},
    'walk': {'tail': 0.6}, 'run': {'tail': 0.6, 'wing': 0.6},
    # round 2: in ko the tail's curl is doubled so it swings round onto the ground (it stood up off the rolled body)
    'ko': {'tail': 2.2},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the amber iris, the big pupil, two catchlights and the upper lash '
             'line baked into the body atlas; the brows, the blush, the freckles and the nostrils are baked into the body; '
             'the two rounded fangs are props on the head. The lips are cut along the smile and an inner mouth (palate, '
             'tongue, throat) sits behind them: the jaw opens it in idle_happy, win, the strike and the hits. No face sheet '
             'and no morphs: expressions in the clips are hints only. Blinking scales the blink bones (play blink over any '
             'clip): each lens squashes onto the closed lid lash line and sinks into the head.')

REVIEW = {'centre': (0.0, 0.25, 0.9), 'size': 2.7, 'head': ((0.0, -0.24, 1.47), 0.82)}
