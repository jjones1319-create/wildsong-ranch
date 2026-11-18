"""Paladove (grown) at the Art 2.1 Ultra tier (chatgpt/monsters/26-paladove grown-1-hero .. grown-6-compare; CONTENT
entry 24): a stately dove-knight, a stout upright dove with the young form's face and colours: white-and-gold chest
armour (a rounded breastplate with a heart-shaped gorget and engraved gold trim, round shoulder plates, a leather belt),
four broad wings (two large upper wings and two smaller lower ones), a glowing gold ring halo, a big wispy crest and a
round shield with a gold feather emblem strapped to its left wing. On the avian plan (plans/avian.py; RECIPE.md "Avian
plan" and "Grown forms").

    npm run art:shape -- paladove-grown
    tools/blender/slot.sh npm run art:ultra -- paladove-grown --blender --stages build,bake,rig,clips,export,review > tools/blender/out/paladove-grown-build1.log 2>&1 &

Size: HEIGHT_UNITS 240 (PROMPTS: about 1.6 x Puddlepup's height) -> the crown 1.46 m, the crest's tips about 1.6 m; the
halo floats above it.

The parts:
  - the body (lo_body): an upright egg (belly, breast, head, cheek puffs, rump) with broad soft feather puffs voxel-united
    on it (the game mesh's soft scalloped outline) and the armour raised out of it (the breastplate, the shoulder plates
    and the belt are the body's own mesh, so they bend with the chest); finer tufts and lying locks only in the high
    source (baked); the trim, scrollwork and rivets are painted (the Lite copy keeps them);
  - the props: four wings (each one closed slab of three feather rows; the upper pair with two fingers, the lower pair
    `wingb` following at 0.75), the shield and its strap on the left forearm (`wing.L.2`), the crest (two bones), the
    tail fan (two bones), the legs and feet, the beak (the lower half on the jaw) and the halo (glowing);
  - the eyes: the young form's big glossy blue lenses, bigger.
Colours (CONTENT): feathers #F7F4EE, highlights and armour plates #FFFFFF, beak, trim, emblem and halo #E3B448, eyes
#4A6FA5. The pictures' brown leather is the gold darkened (paladove_paint.py), the blush and mouth as the young form's.
No variant (CONTENT).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import ultra as U
from lib.mesh import Part
from lib.surface import smooth
from monsters.breeds import paladove_parts as PP
from monsters.breeds import paladove_ultra as Y

ID = 'paladove-grown'
LOOK = 'paladove-grown-ultra'
PLAN = 'avian'
HEIGHT_UNITS = 240
PALETTE = dict(Y.PALETTE)
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 50000
VOXELS = {'hi': 0.0036, 'hi_quick': 0.008, 'lo': 0.0072}
ATLAS_STRIP = 0
ATLAS_MARGIN = 0.008
ATLAS_DENSITY = {'lo_eyes': 1.2, 'lo_props': 0.75}   # build 1: the wings took over half the atlas
NORMAL_SCALE = 0.8
AO_FLOOR = 0.82                                  # polish: no dark gashes through the down
AO_SOFTEN = 2.0
BODY_SHEEN = 0.25
GLOW = {'strength': 1.6, 'tint': None, 'twinkle': 0.0}     # the halo (round 1: a visible soft glow; still a saturated base)
LITE_PROPS_TRIS = 7200                            # polish: the cap (60% of the Lite), so the Lite props stop at a 2.5 cm error: the shield rim and halo stay round (6400 ran to a 6 cm pass: a pentagon)
BLINK_CLOSED = Y.BLINK_CLOSED
FACE_NOTE = ('Baked face (the young form\'s, grown): big glossy blue lenses in soft white down, faint warm brows, a '
             'peach-pink blush; a gold beak whose lower half opens on the jaw (a rose mouth inside). Blinking squashes '
             'each lens onto its lid line and sinks it: a closed lid painted on the face, a curved dark lash line.')
LOCK_TEMPLATES = {'body': (5, 9, 3, 0.2)}

PK_WING, PK_SHIN, PK_TARSUS, PK_TOE, PK_BEAK, PK_JAW, PK_CREST, PK_TAIL, PK_HALO = (Y.PK_WING, Y.PK_SHIN, Y.PK_TARSUS, Y.PK_TOE, Y.PK_BEAK,
                                                                                 Y.PK_JAW, Y.PK_CREST, Y.PK_TAIL, Y.PK_HALO)
PK_SHIELD, PK_STRAP = 10, 11

# ----------------------------------------------------------------------------- the body (metres)
ELLS = [((0.0, 0.03, 0.47), (0.47, 0.41, 0.32)),         # the lower belly: a stout pear, widest low (round 1)
        ((0.0, 0.0, 0.78), (0.4, 0.36, 0.33)),            # the upper body
        ((0.0, -0.03, 0.99), (0.31, 0.29, 0.1)),          # the ruff: fills the head/body crease without a ledge
        ((0.0, -0.045, 1.17), (0.37, 0.33, 0.31)),        # the head
        ((0.16, -0.225, 1.095), (0.13, 0.1, 0.095)),      # the cheek puffs
        ((-0.16, -0.225, 1.095), (0.13, 0.1, 0.095)),
        ((0.0, -0.1, 0.8), (0.34, 0.29, 0.27)),           # the breast, under the breastplate
        ((0.0, 0.2, 0.45), (0.3, 0.22, 0.25))]            # the rump
HEAD_ELL = 3
CENTRE = (0.0, 0.0, 0.8)

HIP, CHEST = (0.0, 0.03, 0.45), (0.0, -0.03, 0.92)
NECK = [(0.0, -0.03, 0.92), (0.0, 0.0, 1.1)]
HEAD_C, HEAD_R = (0.0, -0.08, 1.2), 0.29
HEAD_TIP = (0.0, -0.48, 1.1)
LEG = {'hip': (0.2, 0.03, 0.4), 'knee': (0.21, -0.07, 0.29), 'ankle': (0.21, -0.01, 0.175), 'toe': (0.21, -0.045, 0.046),
       'toe_tip': (0.21, -0.23, 0.036)}
BEAK_UP = {'base': (0.0, -0.31, 1.105), 'tip': (0.0, -0.44, 1.078), 'width': 0.11, 'height': 0.058, 'hook': 0.012}
BEAK_LO = {'base': (0.0, -0.305, 1.072), 'tip': (0.0, -0.42, 1.064), 'width': 0.086, 'height': 0.03, 'hook': -0.003}
JAW = {'head': (0.0, -0.316, 1.075), 'tail': (0.0, -0.42, 1.064)}
MOUTH_AT = (0.0, -0.33, 1.074)
EYE_R, EYE_DEPTH, EYE_SINK = 0.06, 0.18, 0.008    # polish: the dome follows the face's curve, about 3 mm proud
EYE_AT = (0.132, 1.178)
LASH_V = Y.LASH_V


def eye_frame(s: int):
    hc, hr = np.array(ELLS[HEAD_ELL][0]), np.array(ELLS[HEAD_ELL][1])
    x, z = EYE_AT[0] * s, EYE_AT[1]
    yy = hc[1] - hr[1] * math.sqrt(max(0.0, 1.0 - (x / hr[0]) ** 2 - ((z - hc[2]) / hr[2]) ** 2))
    c = np.array([x, yy, z])
    look = PP.unit((c - hc) / hr ** 2)
    return PP.eye_frame(c, look, s)


# ----------------------------------------------------------------------------- the four wings (folded at rest)
def _plane(nw):
    nw = PP.unit(nw)
    eb = PP.unit(np.array((0.0, 1.0, 0.0)) - nw * nw[1])
    return nw, eb, np.cross(eb, nw)


# round 1: the folded wings frame the body from the front (grown-1-hero, grown-2 front): the upper pair's outer faces
# turned out and forward, flaring down and out; the lower pair hangs low behind them, its tips showing below their edge
_NW, _EB, _ED = _plane((0.86, -0.45, 0.22))
_NWB, _EBB, _EDB = _plane((0.8, -0.3, 0.45))
_S0 = np.array((0.335, -0.01, 0.955))
_S0B = np.array((0.4, 0.2, 0.5))


def _wpt(s0, nw, eb, ed, b: float, d: float, hug: float) -> tuple:
    """A point of a folded wing's 2-D design (b back, d down from its shoulder in the wing's plane), pushed along the
    plane's normal out to the body's surface + hug (shape 2: projecting from the centre wrapped the wing round the back)."""
    p = s0 + eb * b + ed * d
    # round 1: the wing keeps to its own (flared) plane, off the body by hug; the shoulder sits on the body
    return tuple(map(float, p + nw * hug))


def _spread(s, dirs, sweep: float) -> dict:
    a = math.radians(sweep)
    rot = [np.array((v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a), v[2])) for v in dirs]
    e2 = np.array(s) + rot[0]
    w2 = e2 + rot[1]
    return {'elbow': tuple(map(float, e2)), 'wrist': tuple(map(float, w2)),
            'fingers': [tuple(map(float, w2 + r)) for r in rot[2:]]}


def _wings() -> tuple[dict, dict]:
    """Folded as in grown-2's side and back views: the arm runs back along the wing's top from the shoulder, the hand
    turning down at the back; the long feathers hang down the flank (the lower wing's on the back-flank, under it).
    Spread (grown-2 wings view, grown-5 attack): the upper pair raised up and out with the long feathers hanging out
    and down from the arm, swept back 15 degrees; the lower pair out to the side at the hips."""
    up = (_S0, _NW, _EB, _ED)
    sh, el, wr = _wpt(*up, 0.0, 0.0, -0.045), _wpt(*up, 0.09, 0.02, -0.005), _wpt(*up, 0.16, 0.06, 0.015)
    f1, f2 = _wpt(*up, 0.25, 0.33, 0.045), _wpt(*up, 0.2, 0.45, 0.055)
    wing = {'name': 'wing', 'parent': 'chest', 'shoulder': sh, 'elbow': el, 'wrist': wr, 'fingers': [f1, f2],
            'attach': _wpt(*up, 0.2, 0.45, 0.0),
            'spread': _spread(sh, [(0.6, 0, 0.8), (0.86, 0, 0.51), (0.8, 0, 0.6), (1.0, 0, 0.04)], 30.0)}
    lo = (_S0B, _NWB, _EBB, _EDB)
    shb, elb, wrb = _wpt(*lo, 0.0, 0.0, -0.03), _wpt(*lo, 0.15, 0.02, 0.0), _wpt(*lo, 0.27, 0.06, 0.005)
    g1, g2 = _wpt(*lo, 0.38, 0.14, 0.01), _wpt(*lo, 0.34, 0.22, 0.01)
    wingb = {'name': 'wingb', 'parent': 'chest', 'shoulder': shb, 'elbow': elb, 'wrist': wrb, 'fingers': [g1, g2],
             'attach': _wpt(*lo, 0.12, 0.3, 0.0), 'follow': 0.75,
             'spread': _spread(shb, [(0.8, 0.35, 0.05), (0.9, 0.25, -0.2), (0.93, 0.2, -0.25), (0.7, 0.25, -0.65)], 25.0)}
    return wing, wingb


WING, WINGB = _wings()
MORE_WINGS = [WINGB]
# four rows each (grown-4 panel 4 and 6): long broad flight feathers whose round tips make the lower edge, coverts
# over them, smaller coverts, and the marginal coverts along the arm
WING_ROWS = [   # round 1: long round-tipped flights down to just above the ankle, layered coverts over them
    # build 10: the front flights shorter (they swept through the lower pair in flight); the back ones reach the ankle
    # round 2: three tiers (coverts, secondaries, long round-tipped primaries), broad and overlapping (no sawtooth)
    {'n': 14, 'u': (0.1, 1.0), 'phi': (86.0, 6.0), 'L': (0.7, 0.5), 'W': 0.16, 'T': 0.03, 'lift': 0.0, 'curl': 0.04},
    {'n': 11, 'u': (0.1, 0.86), 'phi': (84.0, 14.0), 'L': (0.42, 0.3), 'W': 0.15, 'T': 0.028, 'lift': 0.016, 'curl': 0.04},
    {'n': 8, 'u': (0.08, 0.62), 'phi': (84.0, 30.0), 'L': (0.2, 0.16), 'W': 0.13, 'T': 0.026, 'lift': 0.032, 'curl': 0.04},
]
WINGB_ROWS = [  # about 60% of the upper wing
    {'n': 10, 'u': (0.08, 1.0), 'phi': (86.0, 24.0), 'L': (0.42, 0.3), 'W': 0.11, 'T': 0.025, 'lift': 0.0, 'curl': 0.04},
    {'n': 8, 'u': (0.08, 0.9), 'phi': (84.0, 30.0), 'L': (0.26, 0.2), 'W': 0.1, 'T': 0.024, 'lift': 0.013, 'curl': 0.04},
    {'n': 6, 'u': (0.06, 0.7), 'phi': (84.0, 40.0), 'L': (0.15, 0.13), 'W': 0.085, 'T': 0.022, 'lift': 0.025, 'curl': 0.04},
]


def _wing_normal_fn(nw):
    def fn(p: np.ndarray) -> np.ndarray:
        return PP.unit(0.2 * PP.ell_normal(p, ELLS)[0] + 0.8 * PP.mirror(nw, 1 if p[0, 0] >= 0 else -1))[None]
    return fn


def wing_feathers(s: int, i: int = 0) -> list[dict]:
    if i == 0:
        return PP.wing_feathers(WING, WING_ROWS, _wing_normal_fn(_NW), s)
    return PP.wing_feathers(WINGB, WINGB_ROWS, _wing_normal_fn(_NWB), s)


# ----------------------------------------------------------------------------- the shield on the left forearm
def shield_frame():
    """(centre, normal, up) of the shield at rest: on the folded left wing's outer face below the forearm, turned 25
    degrees toward the front (grown-1-hero, grown-2 front and side)."""
    e, w = np.array(WING['elbow']), np.array(WING['wrist'])
    mid = e + (w - e) * 0.98
    a = math.radians(10.0)          # polish: the shield's rim kept clear of the wing (its gold baked onto the coverts behind)
    n = PP.unit(_NW * math.cos(a) + np.array((0.0, -1.0, 0.0)) * math.sin(a))
    c = mid + _ED * 0.33 + n * 0.21
    up = PP.unit(np.array((0.0, 0.0, 1.0)) - n * n[2])
    return c, n, up


SHIELD_R = 0.3                                  # round 1: 1.6x, about a third of the body's height
_SC, _SN, _SU = shield_frame()
SHIELD = {'name': 'shield', 'parent': 'wing.L.2', 'head': tuple(map(float, _SC)), 'tail': tuple(map(float, _SC + _SN * 0.06))}


# ----------------------------------------------------------------------------- crest, tail, halo
CREST_PTS = [(0.0, -0.04, 1.42), (0.0, -0.06, 1.55), (0.0, 0.02, 1.68)]
TAIL_PTS = [(0.0, 0.41, 0.34), (0.0, 0.46, 0.43), (0.0, 0.5, 0.53)]


def crest_feathers() -> list[dict]:
    """The grown crest (grown-1-hero, grown-4 panel 1): a tall wispy tuft rising from the crown and sweeping back, the
    middle curls tallest; leaf-wide to round tips."""
    out = []
    root = np.array((0.0, -0.03, 1.44))
    # six broad soft plumes rising up and a little forward from the crown, each curling back over at its tip
    # round 2: seven plumes tapering to fine curling tips, splayed forward, sideways and back (the hero's wispy flame)
    spec = [(-0.75, -0.25, 0.21), (-0.42, 0.35, 0.27), (-0.18, -0.45, 0.3), (0.02, 0.1, 0.33), (0.24, -0.4, 0.3), (0.46, 0.35, 0.26),
            (0.78, -0.2, 0.2)]
    for k, (lean, fb, L) in enumerate(spec):
        d = PP.unit((0.95 * lean, -0.2 + 1.1 * fb, 1.0))
        n = PP.unit(np.array((0.6 * lean, 0.6 + 0.8 * fb, 0.35)))
        out.append({'root': root + np.array((0.055 * lean, 0.045 * fb, 0.0)), 'd': d, 'n': n, 'L': L, 'W': 0.068, 'T': 0.04,
                    'curl': 0.5 * L, 'level': 0, 'k': k, 'tip': 0.3, 'twist': 0.0})
    return out


def tail_feathers() -> list[dict]:
    out = []
    root = np.array((0.0, 0.4, 0.33))
    up = PP.unit((0.0, 0.42, 0.9))
    fan_n = -PP.unit(np.cross((1.0, 0.0, 0.0), up))
    for k in range(7):
        a = math.radians(-60.0 + 20.0 * k)
        d = PP.unit(up * math.cos(a) + np.array((1.0, 0.0, 0.0)) * math.sin(a))
        L = 0.2 - 0.03 * abs(k - 3) / 3
        out.append({'root': root + np.array((0.0, 0.006 * (k % 2), 0.0)), 'd': d, 'n': fan_n, 'L': L, 'W': 0.075, 'T': 0.02,
                    'curl': 0.05 * L, 'level': k % 2, 'k': k, 'tip': 0.45, 'twist': 0.0})
    return out


HALO = {'name': 'halo', 'parent': 'head', 'head': (0.0, -0.02, 1.76), 'tail': (0.0, -0.02, 1.84)}
HALO_C, HALO_AX, HALO_R, HALO_T = (0.0, -0.02, 1.8), (0.0, -0.05, 1.0), 0.33, 0.02


def rig_p() -> dict:
    return {'hip': HIP, 'chest': CHEST, 'neck': NECK, 'head_c': HEAD_C, 'head_r': HEAD_R, 'head_tip': HEAD_TIP, 'jaw': JAW,
            'jaw_open': True, 'legs': LEG, 'wings': WING, 'more_wings': MORE_WINGS,
            'chains': [{'name': 'crest', 'kind': 'crest', 'parent': 'head', 'points': CREST_PTS},
                       {'name': 'tail', 'kind': 'plume', 'parent': 'hips', 'points': TAIL_PTS, 'stiff': 0.3}],
            'props': [HALO, SHIELD],
            'strike_style': 'beam', 'beam': {'open': 1.0, 'flap': -6.0}, 'strike_yaw': 45.0,
            'strike_bones': {'jaw': (16.0, 0.0, 0.0)},
            'cast_style': 'beam', 'ko_style': 'back', 'hop': 0.6, 'fly_pitch': 14.0, 'sleep_turn': 45.0,
            'clip_bones': {'strike': {'prop.halo': [(0.3, 0.85, (-16.0, 0.0, 0.0), (0.0, -0.03, 0.05))]},
                           'cast': {'prop.halo': [(0.35, 0.8, (0.0, 0.0, 0.0), (0.0, 0.0, 0.06))]}},
            'ko_bones': {'prop.halo': (18.0, 24.0, 0.0)}}


CLIP_CALM = {'*': {'neck': 0.55, 'head': 0.85},
             'eat': {'neck': 0.35, 'head': 0.75},
             'sleep': {'neck': 0.45, 'head': 0.75},
             'idle_tired': {'neck': 0.45},
             'idle_sad': {'neck': 0.45},
             'hit_heavy': {'neck': 0.45, 'head': 0.75},
             'win': {'wingb': 1.3},                                 # round 2: the lower pair lifts too (the upper's 1.25 put the shield by the face)
             'fly_cast': {'wing': 0.62, 'wingb': 0.5, 'neck': 0.3, 'head': 0.4},   # round 2: the head stays off the plate
             # build 6: the lower pair stays half tucked in flight and the hop (it came within 5 mm of the upper)
             # build 7: the upper wing's long flights swept through the folded lower pair on the downstroke, so the upper
             # beat is a little smaller in the air and the lower pair stays tucked
             'fly': {'wing': 0.62, 'wingb': 0.5}, 'fly_takeoff': {'wing': 0.62, 'wingb': 0.5},
             'fly_land': {'wing': 0.62, 'wingb': 0.5}, 'hop': {'wing': 0.9, 'wingb': 0.4}, 'celebrate': {'wingb': 0.6}}


def calm_group(bone: str):
    pre = bone.split('.')[0]
    return 'wingb' if pre == 'wingb' else Y.calm_group(bone)


# ----------------------------------------------------------------------------- the armour (the body's own mesh)
PAULDRON = np.array((0.335, -0.07, 0.955))


def plate_mask(p: np.ndarray, soft: float = 0.008) -> tuple[np.ndarray, np.ndarray]:
    """The breastplate (grown-4 panel 3): a rounded plate on the chest, its top a heart-shaped gorget dipping to the
    middle, its bottom a point under the breast; returns (inside 0..1, distance in from its edge in metres)."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    top = 0.995 - 0.085 * np.clip(1.0 - ax / 0.27, 0, 1) ** 1.3
    bot = 0.47 + 0.3 * np.clip(ax / 0.33, 0, 1) ** 1.3          # round 2: the point runs down over the belly
    side = 0.335 - 0.05 * np.clip((z - 0.85) / 0.15, 0, 1)
    dist = np.minimum.reduce([top - z, z - bot, side - ax])
    front = smooth(0.12, -0.05, y)
    return smooth(-soft, soft, dist) * front, dist


def pauldron_mask(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    d = np.minimum(np.linalg.norm(p - PAULDRON, axis=1), np.linalg.norm(p - PAULDRON * np.array((-1, 1, 1)), axis=1))
    return smooth(0.165, 0.15, d), 0.157 - d


def belt_mask(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    z = p[:, 2]
    dist = 0.032 - np.abs(z - 0.6)
    on = smooth(-0.006, 0.006, dist) * (1.0 - plate_mask(p)[0]) * smooth(-0.14, 0.0, p[:, 1])   # round 2: back and sides only
    return on, dist


def armour_height(p: np.ndarray) -> np.ndarray:
    """How far the armour stands out of the body (metres): the plate domed (3 cm at its edge, 6 cm in the middle) with
    a thick raised gold rim and a raised collar band, the shoulder cups domed 7 cm, the belt 1 cm (round 1: a flat bib)."""
    pm, pd = plate_mask(p)
    rim = smooth(0.0, 0.006, pd) * smooth(0.042, 0.032, pd)
    x, z = p[:, 0], p[:, 2]
    top = 0.995 - 0.085 * np.clip(1.0 - np.abs(x) / 0.27, 0, 1) ** 1.3
    collar = smooth(top - 0.09, top - 0.08, z) * smooth(0.042, 0.05, pd)
    h = pm * (0.03 + 0.03 * smooth(0.0, 0.16, pd) + 0.013 * rim + 0.007 * collar) * (0.3 + 0.7 * smooth(0.0, 0.09, top - z))
    qm, qd = pauldron_mask(p)
    h = np.maximum(h, qm * (0.02 + 0.085 * np.sqrt(np.clip(qd / 0.157, 0, 1)) + 0.012 * smooth(0.0, 0.006, qd) * smooth(0.032, 0.022, qd)))
    bm, _bd = belt_mask(p)
    return np.maximum(h, 0.011 * bm)


def armour_zone(p: np.ndarray, pad: float = 0.0) -> np.ndarray:
    pm, pd = plate_mask(p)
    qm, qd = pauldron_mask(p)
    bm, bd = belt_mask(p)
    return (pd > -pad) & (p[:, 1] < 0.1) | (qd > -pad) | (bd > -pad - 0.006)


def _displace(ob) -> None:
    from lib import surface as S
    co, _ = S.mesh_arrays(ob)
    me = ob.data
    vn = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('normal', vn)
    vn = vn.reshape(-1, 3)
    h = armour_height(co)
    S.set_positions(ob, co + vn * h[:, None])


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    return [Part(f'ell{k}', 'sphere', loc=c, radius=1.0, scale=r) for k, (c, r) in enumerate(ELLS)]


def _wing_zone(p: np.ndarray, pad: float) -> np.ndarray:
    m = np.zeros(len(p), bool)
    for i, spec in enumerate((WING, WINGB)):
        for s in (1, -1):
            for f in wing_feathers(s, i):
                a, b, h = PP.feather_local(p, f)
                m |= (a > -0.2) & (a < 1.1) & (np.abs(b) < 1.0 + pad / (0.5 * f['W'])) & (np.abs(h) < 0.08)
            arm = PP.wing_arm(spec, s)
            for j in range(len(arm) - 1):
                m |= U._seg_dist(p, arm[j], arm[j + 1]) < 0.05 + pad
    return m


def _skip(p: np.ndarray, n: np.ndarray, pad: float = 0.02, wings: bool = True) -> np.ndarray:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    face = (y < -0.15) & (z > 0.98) & (z < 1.42) & (np.abs(x) < 0.29)
    crest = (np.linalg.norm(p - np.array((0.0, -0.02, 1.46)), axis=1) < 0.09) | ((z > 1.42) & (np.abs(x) < 0.13) & (np.abs(y) < 0.13))
    tail = np.linalg.norm(p - np.array((0.0, 0.44, 0.42)), axis=1) < 0.13
    legs = (np.hypot(np.abs(x) - 0.21, y + 0.01) < 0.1) & (z < 0.32)
    pm, pd = plate_mask(p)
    qm, qd = pauldron_mask(p)
    bm, bd = belt_mask(p)
    arm = ((pd > 0.012) & (p[:, 1] < 0.1)) | (qd > -0.01) | (bd > -0.01)
    m = face | crest | tail | legs | (n[:, 2] < -0.96) | arm
    return (m | _wing_zone(p, pad)) if wings else m


def _comb(p, n) -> np.ndarray:
    gi = np.array((0.0, 0.3, -1.0)) if p[2] < 1.3 else PP.unit((0.0, 1.0, -0.15 - 1.2 * (1.46 - p[2])))
    if p[1] < -0.12 and p[2] > 0.95:
        gi = PP.unit((np.sign(p[0]) * 1.0, 0.25, -0.6))
    t = gi - n * float(gi @ n)
    if np.linalg.norm(t) < 1e-3:
        t = np.cross(n, (1.0, 0.0, 0.0))
    return PP.unit(t)


_PUFFS: list = []


def puff_specs() -> list[dict]:
    """Broad soft feather puffs (grown-1-hero, grown-4 panel 6: the body in rows of soft rounded feathers, fluffier on
    the head and neck), lying almost flat, tips tucked into the plumage."""
    if _PUFFS:
        return _PUFFS
    o = np.array(CENTRE)
    dirs = PP.fib_dirs(520)
    rnd = np.random.default_rng(2407)
    pts = np.array([PP.surface_point(o, d, ELLS) for d in dirs])
    nrm = PP.ell_normal(pts, ELLS)
    skip = _skip(pts, nrm, 0.02)
    for i in np.nonzero(~skip)[0]:
        p, n = pts[i], nrm[i]
        t = _comb(p, n)
        low = smooth(0.7, 0.22, p[2])
        lift = math.radians(3.0 + 5.0 * low + 2.0 * rnd.standard_normal())
        d = PP.unit(t * math.cos(lift) + n * math.sin(lift))
        L = (0.11 + 0.025 * low) * (1.0 + 0.1 * rnd.standard_normal()) * (0.75 if p[2] > 1.0 else 1.0)
        # round 1: the hem's thin puffs read as a grey see-through fringe: thick, tucked in
        _PUFFS.append({'root': p - n * 0.012, 'd': d, 'n': n, 'L': float(L), 'W': float(0.12 + 0.02 * rnd.random()),
                       'T': 0.022 if p[2] > 1.0 else 0.034 + 0.012 * low, 'curl': float(-0.16 * L), 'k': int(i)})
    return _PUFFS


def body_extras() -> list:
    out = [PP.feather(f'puff{k}', c['root'], c['d'], c['n'], c['L'], c['W'], c['T'], curl=c['curl'], bury=0.45, tip=0.4,
                      rings=9, seg=10) for k, c in enumerate(puff_specs())]
    # the crest is the plumage's own (as a prop it read grey-silver: props have no fur sheen), on the crest chain
    out += [PP.clump(f"crest{f['k']}", {'base': f['root'], 'dir': f['d'], 'len': f['L'], 'side': np.cross(f['n'], f['d']), 'w': f['W'],
                                         'th': f['T'], 'curl': 0.85, 'bend': f['n'], 'bury': 0.25}, rings=16, seg=10)
            for f in crest_feathers()]
    # round 2: a fluffy ruff round the neck, hanging over the plate's collar (one pear, not a ball on a plate)
    out += [PP.feather(f'ruff{k}', c['base'], c['dir'], np.cross(c['dir'], c['side']), c['len'], c['w'], c['th'], curl=-0.1 * c['len'],
                       bury=0.35, tip=0.42, rings=10, seg=10) for k, c in enumerate(ruff_specs())]   # polish: closed round tips
    return out


_RUFF: list = []


def ruff_specs() -> list[dict]:
    if _RUFF:
        return _RUFF
    o = np.array(CENTRE)
    dirs = PP.fib_dirs(3200)
    rnd = np.random.default_rng(2409)
    pts = np.array([PP.surface_point(o, d, ELLS) for d in dirs])
    nrm = PP.ell_normal(pts, ELLS)
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    on = (z > 0.92) & (z < 1.05) & ~((np.abs(x) < 0.27) & (y < -0.15))
    on &= ~((np.abs(np.abs(x) - 0.335) < 0.12) & (np.abs(y + 0.03) < 0.12))      # clear of the wing roots and cups
    seen = set()
    for i in np.nonzero(on)[0]:
        key = tuple(np.floor(pts[i] / 0.07).astype(int))
        if key in seen:
            continue
        seen.add(key)
        p, n = pts[i], nrm[i]
        t = np.array((0.0, 0.0, -1.0)) - n * (-n[2])
        t = PP.unit(t if np.linalg.norm(t) > 1e-3 else np.cross(n, (1.0, 0.0, 0.0)))
        lift = math.radians(24.0 + 3.0 * rnd.standard_normal())      # polish: flatter, so the hem casts no torn shadow
        d = PP.unit(t * math.cos(lift) + n * math.sin(lift))
        _RUFF.append({'base': tuple(p - n * 0.006), 'dir': tuple(d), 'len': float(0.08 * (1.0 + 0.1 * rnd.standard_normal())),
                      'side': tuple(np.cross(n, t)), 'w': float(0.082 + 0.012 * rnd.random()), 'th': 0.045, 'curl': 0.3,
                      'bend': tuple(-n * 0.4 + t), 'bury': 0.35})
    return _RUFF


def crest_zone(co: np.ndarray) -> np.ndarray:
    m = np.zeros(len(co), bool)
    for f in crest_feathers():
        a, b, h = PP.feather_local(co, f)
        m |= (a > -0.3) & (a < 1.08) & (np.abs(b) < 1.5) & (np.abs(h) < f['T'])
    return m & (co[:, 2] > CREST_PTS[0][2] - 0.03)


def carve_low(lo_body) -> None:
    PP.drop_islands(lo_body)
    _displace(lo_body)


def carve(hi_body) -> None:
    """The high source: smaller soft tufts over the plumage (baked), then the armour raised out of the body."""
    import bmesh
    from lib import common as C
    from lib import surface as S
    co, _ = S.mesh_arrays(hi_body)
    me = hi_body.data
    vn = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('normal', vn)
    vn = vn.reshape(-1, 3)
    ed = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get('vertices', ed)
    ed = ed.reshape(-1, 2)
    vox = float(np.median(np.linalg.norm(co[ed[:200000, 0]] - co[ed[:200000, 1]], axis=1))) * 1.15
    rnd = np.random.default_rng(1807)
    order = rnd.permutation(len(co))
    cell = 0.046
    seen = set()
    pick = []
    for i in order:
        key = tuple(np.floor(co[i] / cell).astype(int))
        if key not in seen:
            seen.add(key)
            pick.append(i)
    pick = np.array(pick)
    pick = pick[~_skip(co[pick], vn[pick], 0.01, wings=False) & (co[pick][:, 2] < 1.0)][:0]   # polish: no high-only feathers
    bm = bmesh.new()
    bm.from_mesh(me)
    for k, i in enumerate(pick):
        p, n = co[i], PP.unit(vn[i])
        t = _comb(p, n)
        low = smooth(0.7, 0.22, p[2])
        lift = math.radians(3.0 + 1.5 * rnd.standard_normal())
        d = PP.unit(t * math.cos(lift) + n * math.sin(lift))
        L = 0.095 * (1.0 + 0.1 * rnd.standard_normal())
        # a scalloped contour feather: broad, round-tipped, lying flat, overlapping its neighbours (grown-2 back, grown-4)
        ob = PP.feather(f'tuft{k}', p - n * 0.004, d, n, float(max(0.06, L)), 0.088, 0.02, curl=-0.14 * L, bury=0.3, tip=0.42,
                        rings=9, seg=10)
        bm.from_mesh(ob.data)
        mesh = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    bm.to_mesh(me)
    bm.free()
    rm = hi_body.modifiers.new('remesh', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = vox
    sm = hi_body.modifiers.new('smooth', 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = 2
    C.apply_modifiers(hi_body)
    chips = PP.drop_islands(hi_body)
    hi_body.data.shade_smooth()
    _displace(hi_body)
    _relief(hi_body)
    C.log(f'carve: {chips} loose chips dropped; {len(pick)} soft tufts on the high body (voxel {vox:.4f}), the armour raised; {len(hi_body.data.polygons)} faces')
    S.base_attrs(hi_body, S.mesh_arrays(hi_body)[0])


def _relief(hi_body) -> None:
    """The armour's raised relief, high source only (baked into the normal map; round 1: painted lines read flat): the
    plate's scrollwork and central spear 5 mm proud, the rivets 6 mm domes."""
    from lib import surface as S
    from monsters.breeds import paladove_armour as AR
    co, _ = S.mesh_arrays(hi_body)
    me = hi_body.data
    vn = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('normal', vn)
    vn = vn.reshape(-1, 3)
    pm, _pd = plate_mask(co, 0.004)
    on = np.nonzero(pm > 0.3)[0]
    xz = co[on][:, [0, 2]]
    d = np.full(len(on), 9.0)
    for path in AR.scroll_paths():
        pts = np.array(path, np.float64)
        for a, b in zip(pts[:-1], pts[1:]):
            ab = b - a
            t = np.clip(((xz - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
            d = np.minimum(d, np.linalg.norm(xz - (a + t[:, None] * ab), axis=1))
    h = np.zeros(len(co))
    h[on] = 0.005 * smooth(0.0085, 0.004, d)
    rv = np.array(AR.rivet_points())
    for c in rv:
        dd = np.linalg.norm(co - c[None], axis=1)
        h = np.maximum(h, 0.006 * np.sqrt(np.clip(1.0 - (dd / 0.013) ** 2, 0, 1)))
    S.set_positions(hi_body, co + vn * h[:, None])


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    eye_d = np.minimum(*(np.linalg.norm(co - eye_frame(s)[0], axis=1) for s in (1, -1)))
    face = (y < -0.16) & (z > 0.98) & (z < 1.36) & (np.abs(x) < 0.27)
    beak_d = np.linalg.norm(co - np.array((0.0, -0.31, 1.085)), axis=1)
    return {'face': face, 'eye_d': eye_d, 'beak_d': beak_d, 'belly': (y < -0.05) & (z < 0.7), 'armour': armour_zone(co, 0.004)}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    pm, pd = plate_mask(co)
    edge = (np.abs(pd) < 0.035) & (co[:, 1] < 0.1)
    return np.clip(0.9 * (z['eye_d'] < 0.11) + 0.5 * z['face'] + 0.6 * (z['beak_d'] < 0.08) + 0.5 * edge + 0.45 * (co[:, 2] > 1.0), 0, 1)


def texel_k(fc: np.ndarray) -> np.ndarray:
    z = zones(fc)
    k = np.where(fc[:, 2] > 0.98, 1.35, 1.0)
    k = np.where(z['armour'], 1.4, k)
    k = np.where(z['armour'] & (fc[:, 2] > 0.85), 1.9, k)        # polish: the collar's gold in clean, dense islands
    return np.where(fc[:, 2] < 0.28, 0.65, k)


def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    g = np.tile(np.array((0.0, 0.3, -1.0)), (len(p), 1))
    crown = p - np.array((0.0, -0.02, 1.5))
    crown[:, 2] = crown[:, 2] * 0.3 - 0.08
    g = np.where((zz > 1.3)[:, None], crown, g)
    rad = p - np.array((0.0, -0.42, 1.08))
    rad[:, 2] -= 0.06
    face = ((y < -0.14) & (zz > 0.95) & (zz <= 1.36))[:, None]
    g = np.where(face, rad, g)
    t = g - n * (g * n).sum(axis=1, keepdims=True)
    bad = np.linalg.norm(t, axis=1) < 1e-5
    t[bad] = np.cross(n[bad], np.array((1.0, 0.0, 0.0)))
    return t / np.linalg.norm(t, axis=1, keepdims=True)


def body_lock_params(p, n):
    z = zones(p, n)
    k = len(p)
    L = np.where(z['face'], 0.028, 0.046)
    W = np.where(z['face'], 0.0125, 0.0165)
    sp = np.where(z['face'], 0.0085, 0.0115)
    lift = np.full(k, math.radians(7.0))
    skip = (z['eye_d'] < EYE_R * 0.3) | (z['beak_d'] < 0.05) | z['armour'] | crest_zone(p) | (p[:, 2] < 0.93)
    return np.where(skip, np.nan, sp), L, W, lift, z


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """Four bones blended by height; the armour wholly on the chest, the face and the beak's root on the head."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    a = smooth(0.4, 0.62, z)
    h = z + 0.15 * (-y)
    b = smooth(0.95, 1.08, h)
    c = smooth(1.02, 1.14, h)
    arm = armour_zone(co, 0.03) & (z > 0.5)
    b = np.where(arm & (z < 1.0), 0.0, b)
    a = np.where(arm, 1.0, a)
    w = {'hips': 1.0 - a, 'chest': a * (1.0 - b), 'neck.1': a * b * (1.0 - c), 'head': a * b * c}
    m = crest_zone(co)
    return [(np.ones(len(co), bool), w), (m, U.chain_weights(co[m], CREST_PTS, ['crest.1', 'crest.2'], 'head', fade=(0.12, 0.02)))]


# ----------------------------------------------------------------------------- props
def _tag(ob, pk, side=0.0, extra=None):
    return Y._tag(ob, pk, side, {'pw': 0.0, **(extra or {})})


def build_props(high: bool, quick: bool) -> list:
    from lib import surface as S
    from monsters.breeds import hearthwing_parts as HP
    tag = 'hi' if high else 'lo'
    out = []
    vw = 0.0026 if high else 0.005
    if quick and high:
        vw = 0.0045
    for s in (1, -1):
        st = 'L' if s > 0 else 'R'
        for i, (spec, nm, tris) in enumerate(((WING, 'wing', 8000), (WINGB, 'wingb', 4200))):
            fs = wing_feathers(s, i)
            ob = PP.wing_slab(f'{tag}_{nm}{st}', fs, spec, s, vw, 0.03 if i == 0 else 0.028, 0.62, smooth_iters=5)
            if high:
                PP.barb_relief(ob, fs, PP.mirror(_NW if i == 0 else _NWB, s), 0.0012)   # round 1: barbs, not satin
            else:
                Y._decimate(ob, tris)
            out.append(_tag(ob, PK_WING, s, {'pw': float(i)}))
        lg = {k: PP.mirror(v, s) for k, v in LEG.items()}
        seg = 16 if high else 10
        # round 1: the legs 1.7x thicker, scaled tarsi, bigger taloned feet
        out.append(_tag(PP.scaled_tube(f'{tag}_shin{st}', lg['knee'], lg['ankle'], 0.088, 0.078, (1, 0, 0), 8, seg), PK_SHIN, s))
        out.append(_tag(PP.scaled_tube(f'{tag}_tarsus{st}', lg['ankle'] + PP.unit(lg['ankle'] - lg['toe']) * 0.06, lg['toe'], 0.072, 0.062,
                                       (1, 0, 0), 48 if high else 14, seg, ring_k=0.09 if high else 0.0, n_scales=8), PK_TARSUS, s))
        base = lg['toe'] + np.array((0.0, -0.004, 0.0))
        for k, ang in enumerate((-32.0, 0.0, 32.0)):
            a = math.radians(ang * s)
            d = np.array((-math.sin(a), -math.cos(a), -0.08))
            L = 0.19 if k == 1 else 0.165
            out.append(_tag(PP.toe(f'{tag}_toe{st}{k}', base, d, L, 0.046, 30 if high else 10, seg, knuckles=3, arch=0.05), PK_TOE, s))
            tip = base + PP.unit(d) * L * 0.95
            out.append(_tag(PP.talon(f'{tag}_claw{st}{k}', tip - PP.unit(d) * 0.01 + np.array((0, 0, 0.012)), PP.unit(d + np.array((0, 0, -0.06))),
                                     0.078, 0.029, 10 if high else 6, 12 if high else 7), PK_TOE, s, {'claw': 1.0}))
        out.append(_tag(PP.toe(f'{tag}_hind{st}', base + np.array((0, 0.01, 0.0)), (0.0, 1.0, -0.06), 0.095, 0.04, 16 if high else 6, seg,
                               knuckles=1), PK_TOE, s))
        out.append(_tag(PP.talon(f'{tag}_hclaw{st}', base + np.array((0, 0.1, 0.014)), PP.unit((0, 1, -0.12)), 0.058, 0.025,
                                 9 if high else 6, 12 if high else 7), PK_TOE, s, {'claw': 1.0}))
    seg = 28 if high else 16
    out.append(_tag(PP.beak(f'{tag}_beak', BEAK_UP['base'], BEAK_UP['tip'], BEAK_UP['width'], BEAK_UP['height'], BEAK_UP['hook'],
                            24 if high else 10, seg), PK_BEAK))
    out.append(_tag(PP.beak(f'{tag}_jaw', BEAK_LO['base'], BEAK_LO['tip'], BEAK_LO['width'], BEAK_LO['height'], BEAK_LO['hook'],
                            20 if high else 9, seg, flat_bottom=0.0), PK_JAW))
    for nm, fs, pk, vx, tris in (('tail', tail_feathers(), PK_TAIL, vw, 1400),):
        objs = [PP.feather(f'{tag}_{nm}_f{f["k"]}', f['root'], f['d'], f['n'], f['L'], f['W'], f['T'], curl=f['curl'], tip=f['tip'])
                for f in fs]
        ob = S.build_body(f'{tag}_{nm}', [], vx, 3, extra=objs)
        if high:
            PP.barb_relief(ob, fs, (0.0, 1.0, -0.3), 0.0012)
        else:
            Y._decimate(ob, tris)
        out.append(_tag(ob, pk))
    out.append(_tag(Y.halo_ring(f'{tag}_halo', HALO_C, HALO_AX, HALO_R, HALO_T, 128 if high else 64, 16 if high else 8), PK_HALO))
    # the shield: a domed disc with a raised rim (the emblem, rivets and scrollwork are painted per pixel)
    sh_ob = _tag(_shield(f'{tag}_shield', high), PK_SHIELD, 1.0)
    if not high:     # round 2: the emblem smeared in the Lite copy: the shield takes more of the atlas
        a_ = sh_ob.data.attributes.new('texel_k', 'FLOAT', 'FACE')
        a_.data.foreach_set('value', np.full(len(sh_ob.data.polygons), 2.4, np.float32))
    out.append(sh_ob)
    # its strap: a leather band behind it, round the forearm
    e, w = np.array(WING['elbow']), np.array(WING['wrist'])
    ax = PP.unit(w - e)
    across = PP.unit(np.cross(_SN, ax))
    # build 3: the straight strap's ends floated past the shield like handles; now they bend down into the wing
    # round 2: the strap lies across the wing's face behind the shield, a buckle at its front end (no stubs, no
    # ends piercing the wing)
    pts = np.array([_SC - _SN * 0.038 + ax * t for t in np.linspace(-0.8 * SHIELD_R, 0.8 * SHIELD_R, 13)])
    out.append(_tag(HP.tube(f'{tag}_strap', pts, np.full(13, 0.045), _SU, seg=10 if high else 6, flat=0.3), PK_STRAP, 1.0))
    return out


def _shield(name: str, high: bool):
    """A surface of revolution about the shield's normal: the back, a rounded edge, the raised rim, a dip inside it and
    a gently domed face, with many rings on the face so the paint has room."""
    from monsters.breeds import hearthwing_parts as HP
    R = SHIELD_R
    prof = [(-0.03, 0.84), (-0.024, 0.965), (-0.008, 1.0), (0.016, 1.0), (0.034, 0.97), (0.042, 0.92), (0.036, 0.865), (0.018, 0.84)]
    nf = 60 if high else 7
    for k in range(1, nf + 1):
        r = 0.84 * (1.0 - k / (nf + 1))
        prof.append((0.018 + 0.004 * (1.0 - (r / 0.84) ** 2), r))
    c = np.array([_SC + _SN * dz for dz, _r in prof])
    r = np.array([R * rr for _dz, rr in prof])
    ref = np.cross(_SU, _SN)
    X = np.tile(PP.unit(ref), (len(c), 1))
    Y_ = np.tile(_SU, (len(c), 1))
    ob = HP.loft(name, c, X, Y_, r, r, 256 if high else 44, True, True, _SC + _SN * 0.022)
    from lib import surface as S
    # polish: one centre point turned the rim's inner wall and the inner half of its top inward (culled in the game,
    # so the gold rim floated apart from the face): each face turns away from a point inside its own part of the
    # cross-section (the rim's core for the rim, a point under the face for the face and the back)
    def inside(fc):
        q = fc - _SC[None]
        h = q @ _SN
        rad = q - h[:, None] * _SN[None]
        rr = np.linalg.norm(rad, axis=1)
        ru = rad / np.maximum(rr, 1e-9)[:, None]
        rim = rr > 0.835 * R
        r_in = np.where(rim, 0.92 * R, rr)
        h_in = np.where(rim, 0.01, -0.005)
        return _SC[None] + ru * r_in[:, None] + h_in[:, None] * _SN[None]
    S.orient_away(ob, inside)
    if high:
        from monsters.breeds import paladove_armour as AR
        co, _ = S.mesh_arrays(ob)
        S.set_positions(ob, co + _SN[None] * AR.shield_relief(co)[:, None])
    return ob


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    pk = np.round(attr('pk')).astype(int)
    ps = attr('ps')
    pw = np.round(attr('pw')).astype(int)
    regs = []
    for s in (1, -1):
        st = 'L' if s > 0 else 'R'
        side = np.sign(ps) == s
        for i, spec in enumerate((WING, WINGB)):
            m = (pk == PK_WING) & side & (pw == i)
            if m.any():
                q = U.wing_points(spec, s)
                nm = U.wing_bone_names(spec, s)
                segs = [(nm[0], q['shoulder'], q['elbow']), (nm[1], q['elbow'], q['wrist'])]
                segs += [(nm[2 + k], q['wrist'], f) for k, f in enumerate(q['fingers'])]
                regs.append((m, U.segment_weights(co[m], segs, power=6.0)))
        for pkk, bone in ((PK_SHIN, f'shin.{st}'), (PK_TARSUS, f'tarsus.{st}'), (PK_TOE, f'toe.{st}')):
            mm = (pk == pkk) & side
            if mm.any():
                regs.append(U.rigid(mm, bone))
    regs.append(U.rigid(pk == PK_BEAK, 'head'))
    regs.append(U.rigid(pk == PK_JAW, 'jaw'))
    regs.append(U.rigid(pk == PK_HALO, 'prop.halo'))
    regs.append(U.rigid((pk == PK_SHIELD) | (pk == PK_STRAP), 'prop.shield'))
    m = pk == PK_TAIL
    regs.append((m, U.chain_weights(co[m], TAIL_PTS, ['tail.1', 'tail.2'], 'hips', fade=(0.02, -0.05))))
    return regs


def preview_prop_colour(name: str):
    if 'strap' in name:
        return '#6B4A24'
    if 'shield' in name:
        return '#FFFFFF'
    return Y.preview_prop_colour(name)


# ----------------------------------------------------------------------------- eyes and paint
def build_eye(name: str, s: int, high: bool):
    return PP.build_lens(name, eye_frame(s), EYE_R, EYE_DEPTH, EYE_SINK, s, high)


def blink_pivot(s: int):
    from mathutils import Vector
    c, _xax, yax, look = eye_frame(s)
    p = c - look * EYE_SINK + yax * (EYE_R * LASH_V)
    return Vector(tuple(p)), Vector(tuple(yax)), Vector(tuple(look))


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    return PP.eye_material(name, rough_pass, (pal or PALETTE)['eye'], vis=0.88, pupil=0.36, lid=0.9, light=1.0)   # polish: no dark band at 64 px


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import paladove_armour as AR
    AR.paint_grown(body_srcs, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import paladove_armour as AR
    return AR.armour_material(name, attr)


def prop_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import paladove_armour as AR
    return AR.shield_material(name, attr)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import paladove_armour as AR
    return AR.grown_body_colours(co, vn, None, None)[0]


REVIEW = {'centre': (0.0, 0.0, 0.86), 'size': 2.3, 'head': ((0.0, -0.15, 1.24), 0.85),
          'clips': [('cast', 0.55), ('win', 0.5), ('hit', 0.3), ('fly', 0.25), ('sleep', 0.5)]}

CHECK_ROOT_R = 0.07
CHECK_SHIELD_HEAD = True
CHECK_BODY_HALO = 1.55
CHECK_ROOTS = {PK_BEAK: lambda p: p[:, 1] > -0.335, PK_JAW: lambda p: p[:, 1] > -0.33,
               PK_TAIL: lambda p: np.linalg.norm(p - np.array((0.0, 0.392, 0.307)), axis=1) < 0.02}
