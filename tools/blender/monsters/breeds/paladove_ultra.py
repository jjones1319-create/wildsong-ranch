"""Paladove (young) at the Art 2.1 Ultra tier (chatgpt/monsters/26-paladove 1-hero .. 5-poses; CONTENT entry 24): a
fluffy, round dove chick, a nearly round puffball of soft white down with small layered wings, short golden legs, a
small golden beak, big blue eyes, a tiny wispy feather crest and a little gold ring floating above its head. On the
avian plan (plans/avian.py; RECIPE.md "Avian plan").

    npm run art:shape -- paladove
    tools/blender/slot.sh npm run art:ultra -- paladove --blender --stages build,bake,rig,clips,export,review > tools/blender/out/paladove-build1.log 2>&1 &

Size: HEIGHT_UNITS 120 (PROMPTS: about 0.8 x Puddlepup's height) -> the crown 0.73 m, the crest's tips about 0.8 m; the
halo floats above it (0.87 m).

The parts:
  - the body (lo_body): one ball (a belly ellipsoid and a head ellipsoid, cheek puffs, a rump) with about 400 soft
    fluff clumps voxel-united on it for the tufted outline; short lying locks baked into the atlas for the fine down;
    the face, blush, brows, the closed lids and the mouth are painted;
  - the props: the wings (each one closed slab of three feather rows, so they never spread into pellets or read as
    needles), the tail fan (seven round feathers on a two-bone chain), the crest (seven wispy curls on a two-bone
    chain), the legs and feet (a scaly tarsus, three front toes and a hind toe with pale claws), the beak (the upper
    half on the head, the lower on the jaw) and the halo (a gold ring on its own bone above the head, glowing softly);
  - the eyes: big glossy blue lenses.
Colours (CONTENT): feathers warm white #F7F4EE, highlights #FFFFFF, beak and halo gold #E3B448, eyes #4A6FA5. The
pictures' pink blush, the mouth's rose and the pale claws are mixed from those (paladove_paint.py), as is the shading.
No variant (CONTENT).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import ultra as U
from lib.mesh import Part
from lib.surface import smooth, v3
from monsters.breeds import paladove_parts as PP

ID = 'paladove'
LOOK = 'paladove-ultra'
PLAN = 'avian'
HEIGHT_UNITS = 120
PALETTE = {'body': '#F7F4EE', 'belly': '#FFFFFF', 'accent': '#E3B448', 'eye': '#4A6FA5'}
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')     # the lower beak is a prop on the jaw; no skin follows it
BODY_TRIS = 42000
VOXELS = {'hi': 0.0026, 'hi_quick': 0.006, 'lo': 0.005}
ATLAS_STRIP = 0
ATLAS_MARGIN = 0.008                            # the gold islands (beak, feet, halo) never bleed at the small mips
ATLAS_DENSITY = {'lo_eyes': 1.3}
NORMAL_SCALE = 0.65                             # round 2: less popcorn relief, softer down
AO_FLOOR = 0.82                                 # polish: no grey mottling
AO_SOFTEN = 3.0
BODY_SHEEN = 0.25                               # build 1: the fur sheen read as foil on the white tufts
GLOW = {'strength': 0.8, 'tint': None, 'twinkle': 0.0}   # the halo only (a saturated gold, moderate glow)
LITE_PROPS_TRIS = 3600
BLINK_CLOSED = (0.96, 0.05, 0.12)               # squashed onto the lid line and sunk under the skin
FACE_NOTE = ('Baked face: big glossy blue lenses (a deep blue iris with a paler ring, a large pupil, two catchlights, a '
             'dark upper lash line flicked at the outer corner) in soft white down, faint warm brows, a peach-pink blush '
             'on each cheek; a small gold beak whose lower half opens on the jaw (a rose mouth inside). Blinking squashes '
             'each lens onto its lid line and sinks it: a closed lid painted on the face, a curved dark lash line.')
LOCK_TEMPLATES = {'body': (5, 9, 3, 0.2)}

# ----------------------------------------------------------------------------- the body (metres)
ELLS = [((0.0, 0.0, 0.33), (0.285, 0.255, 0.29)),        # the belly ball
        ((0.0, -0.025, 0.515), (0.25, 0.23, 0.215)),      # the head, one with it
        ((0.0, 0.12, 0.27), (0.2, 0.15, 0.17)),           # the rump, under the tail
        ((0.0, -0.02, 0.48), (0.25, 0.225, 0.08))]        # round 1: fills the head/body crease (no ledge)
CENTRE = (0.0, 0.0, 0.38)

HIP, CHEST = (0.0, 0.02, 0.22), (0.0, -0.02, 0.4)
NECK = [(0.0, -0.02, 0.4), (0.0, 0.0, 0.49)]
HEAD_C, HEAD_R = (0.0, -0.05, 0.56), 0.22
HEAD_TIP = (0.0, -0.3, 0.52)
LEG = {'hip': (0.1, 0.02, 0.2), 'knee': (0.11, -0.05, 0.13), 'ankle': (0.11, -0.005, 0.075), 'toe': (0.11, -0.02, 0.012),
       'toe_tip': (0.11, -0.09, 0.008)}

# the beak (4-details panel 1, 3-faces): small, gold, a rounded triangle from the front
BEAK_UP = {'base': (0.0, -0.222, 0.522), 'tip': (0.0, -0.306, 0.503), 'width': 0.074, 'height': 0.04, 'hook': 0.008}
BEAK_LO = {'base': (0.0, -0.218, 0.499), 'tip': (0.0, -0.29, 0.494), 'width': 0.058, 'height': 0.021, 'hook': -0.002}
JAW = {'head': (0.0, -0.226, 0.5), 'tail': (0.0, -0.29, 0.494)}

# the eyes: on the head ellipsoid, laid along its normal (round 8's lesson: a lens along the surface's radius)
EYE_R, EYE_DEPTH, EYE_SINK = 0.039, 0.18, 0.004   # polish: the dome follows the face's curve, about 3 mm proud
EYE_AT = (0.075, 0.558)                          # x, z of the left eye's centre on the face


def eye_frame(s: int):
    hc, hr = np.array(ELLS[1][0]), np.array(ELLS[1][1])
    x, z = EYE_AT[0] * s, EYE_AT[1]
    yy = hc[1] - hr[1] * math.sqrt(max(0.0, 1.0 - (x / hr[0]) ** 2 - ((z - hc[2]) / hr[2]) ** 2))
    c = np.array([x, yy, z])
    look = PP.unit((c - hc) / hr ** 2)
    return PP.eye_frame(c, look, s)


# ----------------------------------------------------------------------------- the wings (folded at rest)
_NW = PP.unit((1.0, 0.2, 0.12))                  # the folded wing's plane: out, a little back
_EB = PP.unit(np.array((0.0, 1.0, 0.0)) - _NW * _NW[1])
_ED = np.cross(_EB, _NW)                         # down in the wing's plane
_S0 = np.array((0.262, -0.05, 0.372))             # round 1: lower on the flank


def _wpt(b: float, d: float, hug: float = 0.012) -> tuple:
    """A point of the folded wing's 2-D design (b back, d down from the shoulder), laid onto the body's surface + hug."""
    p = _S0 + _EB * b + _ED * d
    o = np.array(CENTRE)
    q = PP.surface_point(o, p - o, ELLS)
    return tuple(map(float, q + PP.unit(p - o) * hug))


def _spread_dir(v, sweep: float = 20.0) -> np.ndarray:
    a = math.radians(sweep)
    return np.array((v[0] * math.cos(a), v[0] * math.sin(a), v[2]))


def _wing_spec() -> dict:
    sh, el, wr, tp = _wpt(0.0, 0.0, -0.045), _wpt(0.085, 0.01, -0.006), _wpt(0.165, 0.045, 0.004), _wpt(0.3, 0.1, 0.008)
    # spread (2-turnaround's wings view, 5-poses attack): raised up and out, the arm curving out toward the tip, swept
    # back 20 degrees so the dorsal faces show to the front and to the battle camera on the left
    d1, d2, d3 = _spread_dir((0.55, 0, 0.83)), _spread_dir((0.8, 0, 0.6)), _spread_dir((0.92, 0, 0.38))
    s = np.array(sh)
    e2 = s + d1
    w2 = e2 + d2
    t2 = w2 + d3
    return {'name': 'wing', 'parent': 'chest', 'shoulder': sh, 'elbow': el, 'wrist': wr, 'fingers': [tp],
            'attach': _wpt(0.12, 0.13, 0.0),
            'spread': {'elbow': tuple(map(float, e2)), 'wrist': tuple(map(float, w2)), 'fingers': [tuple(map(float, t2))]}}


WING = _wing_spec()
# three overlapping rows (4-details panel 4): long round flight feathers, coverts over their roots, small coverts on top
WING_ROWS = [   # round 1: the chord doubled; the top row is the down-soft coverts at the shoulder
    {'n': 10, 'u': (0.22, 1.0), 'phi': (80.0, 6.0), 'L': (0.15, 0.16), 'W': 0.082, 'T': 0.016, 'lift': 0.0, 'curl': 0.22},
    {'n': 8, 'u': (0.2, 0.88), 'phi': (82.0, 14.0), 'L': (0.105, 0.1), 'W': 0.078, 'T': 0.016, 'lift': 0.005, 'curl': 0.18},
    {'n': 7, 'u': (0.12, 0.72), 'phi': (84.0, 30.0), 'L': (0.068, 0.064), 'W': 0.07, 'T': 0.015, 'lift': 0.009, 'curl': 0.14},
]


def wing_normal(p: np.ndarray) -> np.ndarray:
    """The folded wing hugs the body: half the body's normal, half the wing's plane."""
    return PP.unit(0.7 * PP.ell_normal(p, ELLS)[0] + 0.3 * PP.mirror(_NW, 1 if p[0, 0] >= 0 else -1))[None]


def wing_feathers(s: int) -> list[dict]:
    return PP.wing_feathers(WING, WING_ROWS, wing_normal, s)


# ----------------------------------------------------------------------------- the crest and the tail fan (chains)
CREST_PTS = [(0.0, -0.015, 0.7), (0.0, -0.035, 0.79), (0.0, 0.0, 0.875)]
TAIL_PTS = [(0.0, 0.24, 0.19), (0.0, 0.274, 0.255), (0.0, 0.305, 0.32)]


def crest_feathers() -> list[dict]:
    """Seven wispy curls (1-hero, 2-turnaround): rising from the crown, the middle ones tallest, the outer ones leaning
    out and curling over; leaf-wide to a round tip."""
    out = []
    root = np.array((0.0, -0.015, 0.715))
    # round 1: about 1.7x, soft plumes rising a little forward and curling back over at the tip
    # round 2: seven plumes tapering to fine curling tips, splayed in depth: some lean forward, some sideways, some back
    spec = [(-0.8, -0.25, 0.11), (-0.45, 0.35, 0.14), (-0.2, -0.45, 0.16), (0.02, 0.1, 0.18), (0.25, -0.4, 0.165),
            (0.5, 0.35, 0.14), (0.82, -0.2, 0.11)]
    for k, (lean, fb, L) in enumerate(spec):
        d = PP.unit((0.95 * lean, -0.15 + 1.1 * fb, 1.0))
        n = PP.unit(np.array((0.6 * lean, 0.6 + 0.8 * fb, 0.35)))
        out.append({'root': root + np.array((0.03 * lean, 0.025 * fb, 0.0)), 'd': d, 'n': n, 'L': L, 'W': 0.04, 'T': 0.024,
                    'curl': 0.5 * L, 'level': 0, 'k': k, 'tip': 0.3, 'twist': 0.0})
    return out


def tail_feathers() -> list[dict]:
    """The tail's fan (2-turnaround side and back): seven round feathers radiating from under the rump, back and up."""
    out = []
    root = np.array((0.0, 0.252, 0.2))
    up = PP.unit((0.0, 0.42, 0.9))
    fan_n = PP.unit(np.cross((1.0, 0.0, 0.0), up))       # the fan faces back and a little down
    if fan_n[1] < 0:
        fan_n = -fan_n
    for k in range(7):
        a = math.radians(-66.0 + 22.0 * k)
        d = PP.unit(up * math.cos(a) + np.array((1.0, 0.0, 0.0)) * math.sin(a))
        L = 0.13 - 0.022 * abs(k - 3) / 3
        nk = PP.unit(fan_n + np.array((1.0, 0.0, 0.0)) * 0.55 * math.sin(a))
        out.append({'root': root + np.array((0.0, 0.004 * (k % 2), 0.0)), 'd': d, 'n': nk, 'L': L, 'W': 0.052, 'T': 0.022,
                    'curl': 0.06 * L, 'level': k % 2, 'k': k, 'tip': 0.45, 'twist': 0.0})
    return out


HALO = {'name': 'halo', 'parent': 'head', 'head': (0.0, -0.01, 0.925), 'tail': (0.0, -0.01, 0.975)}
HALO_C, HALO_AX, HALO_R, HALO_T = (0.0, -0.01, 0.95), (0.0, -0.06, 1.0), 0.118, 0.0085


def rig_p() -> dict:
    return {'hip': HIP, 'chest': CHEST, 'neck': NECK, 'head_c': HEAD_C, 'head_r': HEAD_R, 'head_tip': HEAD_TIP, 'jaw': JAW,
            'jaw_open': True, 'legs': LEG, 'wings': WING,
            'chains': [{'name': 'crest', 'kind': 'crest', 'parent': 'head', 'points': CREST_PTS},
                       {'name': 'tail', 'kind': 'plume', 'parent': 'hips', 'points': TAIL_PTS, 'stiff': 0.3}],
            'props': [HALO],
            'strike_style': 'buffet', 'buffet': {'open': 1.0, 'flap': 22.0, 'sweep': 72.0}, 'strike_yaw': 12.0,
            'strike_bones': {'hips': (14.0, 0.0, 0.0)},
            'ko_bones': {'thigh.L': (25.0, 0.0, 0.0), 'thigh.R': (25.0, 0.0, 0.0), 'shin.L': (-45.0, 0.0, 0.0),
                         'shin.R': (-45.0, 0.0, 0.0), 'tarsus.L': (72.0, 0.0, 0.0), 'tarsus.R': (72.0, 0.0, 0.0),
                         'prop.halo': (20.0, 26.0, 0.0)},
            'cast_style': 'beam', 'ko_style': 'roll', 'hop': 0.6, 'sleep_turn': 38.0,
            'fly_pitch': 14.0}


# the ball's head is the top of the body: calm the neck's big bends (a 1-bone neck takes the whole S of the plan)
CLIP_CALM = {'*': {'neck': 0.5, 'head': 0.8},
             'eat': {'neck': 0.3, 'head': 0.75},
             'sleep': {'neck': 0.4, 'head': 0.7},
             'idle_tired': {'neck': 0.4},
             'idle_sad': {'neck': 0.4},
             'hit_heavy': {'neck': 0.4, 'head': 0.7}}


def calm_group(bone: str):
    if bone == 'head':
        return 'head'
    pre = bone.split('.')[0]
    if pre in ('neck', 'wing', 'crest', 'tail'):
        return pre
    if pre in ('thigh', 'shin', 'tarsus', 'toe'):
        return 'leg'
    return None


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    return [Part(f'ell{k}', 'sphere', loc=c, radius=1.0, scale=r) for k, (c, r) in enumerate(ELLS)]


def _wing_zone(p: np.ndarray, pad: float) -> np.ndarray:
    """Points under the folded wings (no fluff clumps there: they'd push through the slab)."""
    m = np.zeros(len(p), bool)
    for s in (1, -1):
        for f in wing_feathers(s):
            a, b, h = PP.feather_local(p, f)
            m |= (a > -0.2) & (a < 1.15) & (np.abs(b) < 1.0 + pad / (0.5 * f['W'])) & (np.abs(h) < 0.06)
        arm = PP.wing_arm(WING, s)
        for i in range(1, len(arm) - 1):
            d = U._seg_dist(p, arm[i], arm[i + 1])
            m |= d < 0.03 + pad
    return m


_PUFFS: list = []


def _skip(p: np.ndarray, n: np.ndarray, pad: float = 0.02, wings: bool = True) -> np.ndarray:
    """No fluff on the face's middle, under the folded wings, at the crest, the tail's root, round the legs or under
    the belly."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    face = (y < -0.1) & (z > 0.4) & (z < 0.69) & (np.abs(x) < 0.19)
    crest = (np.linalg.norm(p - np.array((0.0, -0.01, 0.73)), axis=1) < 0.06) | ((z > 0.69) & (np.abs(x) < 0.09) & (np.abs(y) < 0.09))
    tail = np.linalg.norm(p - np.array((0.0, 0.27, 0.25)), axis=1) < 0.1
    legs = (np.hypot(np.abs(x) - 0.11, y + 0.01) < 0.03) & (z < 0.07)
    m = face | crest | tail | legs | (n[:, 2] < -0.75)
    return (m | _wing_zone(p, pad)) if wings else m


def _comb(p, n) -> np.ndarray:
    """The down's direction on the surface: down and a little back; back over the crown; out and down on the cheeks."""
    gi = np.array((0.0, 0.3, -1.0)) if p[2] < 0.6 else PP.unit((0.0, 1.0, -0.15 - 2.0 * (0.73 - p[2])))
    if p[1] < -0.08 and p[2] > 0.38:
        gi = PP.unit((np.sign(p[0]) * 1.0, 0.25, -0.6))
    t = gi - n * float(gi @ n)
    if np.linalg.norm(t) < 1e-3:
        t = np.cross(n, (1.0, 0.0, 0.0))
    return PP.unit(t)


def puff_specs() -> list[dict]:
    """The down's big soft puffs, in the game mesh (1-hero, 2-turnaround: the ball's outline softly scalloped, the
    breast in rows of soft tufts). Build 1's thin lifted locks read as crumpled foil in the game: these are broad and
    thick, lie almost flat and tuck their tips into the down (no undercuts to shade black), standing out a little
    only at the lower skirt."""
    if _PUFFS:
        return _PUFFS
    o = np.array(CENTRE)
    dirs = PP.fib_dirs(460)
    rnd = np.random.default_rng(2406)
    pts = np.array([PP.surface_point(o, d, ELLS) for d in dirs])
    nrm = PP.ell_normal(pts, ELLS)
    skip = _skip(pts, nrm, 0.015, wings=False)
    under = _wing_zone(pts, 0.015)
    for i in np.nonzero(~skip)[0]:
        p, n = pts[i], nrm[i]
        if under[i]:
            t = _comb(p, n)
            L = 0.065 * (1.0 + 0.1 * rnd.standard_normal())
            _PUFFS.append({'root': p - n * 0.01, 'd': t, 'n': n, 'L': float(L), 'W': float(0.08 + 0.01 * rnd.random()), 'T': 0.012,
                           'curl': float(-0.1 * L), 'k': int(i)})
            continue
        t = _comb(p, n)
        low = smooth(0.42, 0.1, p[2])
        side = abs(float(p[0])) > 0.17
        cheek = side and p[1] < -0.04 and 0.42 < p[2] < 0.57
        flank = abs(float(p[0])) > 0.2 and 0.14 < p[2] < 0.33
        skirt = p[2] < 0.13
        tuft = cheek or flank or skirt
        # round 1: thick soft tufts standing out at the cheeks, the flanks and the skirt break the egg outline;
        # elsewhere broad puffs lie almost flat (thin lifted lobes read as foil in build 1)
        # round 1 (build 9): the cheek ellipsoids stood out like a stubby arm; soft cheek tufts only
        lift = math.radians(((7.0 if cheek else 12.0) if tuft else 3.0 + 3.0 * low) + 2.0 * rnd.standard_normal())
        d = PP.unit(t * math.cos(lift) + n * math.sin(lift))
        L = (0.07 if tuft else 0.062 + 0.014 * low) * (1.0 + 0.1 * rnd.standard_normal())
        near_face = smooth(0.43, 0.3, p[2]) if (p[1] < -0.05 and abs(float(p[0])) < 0.22 and p[2] < 0.43) else 1.0
        _PUFFS.append({'root': p - n * 0.008, 'd': d, 'n': n, 'L': float(L), 'W': float(0.062 + 0.012 * rnd.random()) if tuft else
                       float(0.07 + 0.012 * rnd.random()), 'T': float((0.032 if tuft else 0.024) * (0.35 + 0.65 * near_face)),
                       'curl': float(-0.05 * L if tuft else -0.08 * L), 'k': int(i)})
    return _PUFFS


def body_extras() -> list:
    out = [PP.feather(f'puff{k}', c['root'], c['d'], c['n'], c['L'], c['W'], c['T'], curl=c['curl'], bury=0.45, tip=0.4,
                      rings=9, seg=10) for k, c in enumerate(puff_specs())]
    # the crest is the down's own (build 4: as a prop it read grey-silver, props having no fur sheen); its skin is
    # weighted to the crest chain (body_weight_regions)
    out += [PP.clump(f'crest{f["k"]}', {'base': f['root'], 'dir': f['d'], 'len': f['L'], 'side': np.cross(f['n'], f['d']), 'w': f['W'],
                                         'th': f['T'], 'curl': 0.85, 'bend': f['n'], 'bury': 0.25}, rings=16, seg=10)
            for f in crest_feathers()]
    # round 2: wispy tufts that change the outline (the crown round the crest, the cheeks, the flanks, a skirt over the
    # thighs): tapered pointed locks standing out, in the game mesh
    out += [PP.clump(f'wisp{k}', c, rings=10, seg=9) for k, c in enumerate(wisp_specs())]
    return out


_WISPS: list = []


def wisp_specs() -> list[dict]:
    if _WISPS:
        return _WISPS
    o = np.array(CENTRE)
    dirs = PP.fib_dirs(2400)
    rnd = np.random.default_rng(2408)
    pts = np.array([PP.surface_point(o, d, ELLS) for d in dirs])
    nrm = PP.ell_normal(pts, ELLS)
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    ax = np.abs(x)
    # build 11: wisps all over the sides read as torn paper: only where the outline is (the surface turned to the side
    # or up), fewer and softer
    nx, nz = np.abs(nrm[:, 0]), nrm[:, 2]
    crown = (z > 0.62) & (np.hypot(x, y + 0.015) > 0.07) & (y > -0.16) & (nz > 0.45)
    cheek = (ax > 0.17) & (y < 0.02) & (z > 0.4) & (z < 0.58) & (nx > 0.6)
    flank = (ax > 0.22) & (z > 0.13) & (z < 0.36) & (nx > 0.7) & ~_wing_zone(pts, 0.03)
    skirt = (z > 0.045) & (z < 0.15) & (y < 0.2) & ~((np.hypot(ax - 0.11, y + 0.01) < 0.028) & (z < 0.07))
    on = (crown | cheek | flank | skirt) & ~((y < -0.1) & (z > 0.4) & (z < 0.69) & (ax < 0.17))
    seen = set()
    for i in np.nonzero(on)[0]:
        key = tuple(np.floor(pts[i] / 0.06).astype(int))
        if key in seen:
            continue
        seen.add(key)
        p, n = pts[i], nrm[i]
        t = _comb(p, n)
        if crown[i]:
            t = PP.unit(np.array((0.0, 0.0, 1.0)) - n * n[2] + 0.5 * t)
        lift = math.radians(22.0 + 4.0 * rnd.standard_normal())
        d = PP.unit(t * math.cos(lift) + n * math.sin(lift))
        L = (0.055 if crown[i] else 0.065) * (1.0 + 0.12 * rnd.standard_normal())
        _WISPS.append({'base': tuple(p - n * 0.004), 'dir': tuple(d), 'len': float(max(0.045, L)), 'side': tuple(np.cross(n, t)),
                       'w': float(0.044 + 0.008 * rnd.random()), 'th': 0.03, 'curl': 0.3, 'bend': tuple(-n * 0.3 + t), 'bury': 0.35})
    return _WISPS


def crest_zone(co: np.ndarray) -> np.ndarray:
    m = np.zeros(len(co), bool)
    for f in crest_feathers():
        a, b, h = PP.feather_local(co, f)
        m |= (a > -0.3) & (a < 1.08) & (np.abs(b) < 1.5) & (np.abs(h) < f['T'])
    return m & (co[:, 2] > CREST_PTS[0][2] - 0.02)


def carve(hi_body) -> None:
    """The high source only (baked into the normal map, the AO and the paint): smaller soft tufts over the puffs, laid
    on the high body's own surface, then voxel-united with it."""
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
    rnd = np.random.default_rng(1806)
    order = rnd.permutation(len(co))
    cell = 0.036
    seen = set()
    pick = []
    for i in order:
        key = tuple(np.floor(co[i] / cell).astype(int))
        if key not in seen:
            seen.add(key)
            pick.append(i)
    pick = np.array(pick)
    pick = pick[~_skip(co[pick], vn[pick], 0.01, wings=False)][:0]     # polish: no high-only tufts
    bm = bmesh.new()
    bm.from_mesh(me)
    for k, i in enumerate(pick):
        p, n = co[i], PP.unit(vn[i])
        t = _comb(p, n)
        low = smooth(0.42, 0.1, p[2])
        lift = math.radians(5.0 + 2.0 * low + 2.0 * rnd.standard_normal())
        d = PP.unit(t * math.cos(lift) + n * math.sin(lift))
        L = 0.036 * (1.0 + 0.15 * rnd.standard_normal())
        ob = PP.feather(f'tuft{k}', p - n * 0.003, d, n, float(max(0.024, L)), 0.03, 0.0085, curl=-0.12 * L, bury=0.3, tip=0.36,
                        rings=8, seg=8)
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
    chips = PP.drop_islands(hi_body, 400)
    # round 2: strand grooves down the crest's plumes (baked into the normal map)
    co2, _ = S.mesh_arrays(hi_body)
    me2 = hi_body.data
    vn2 = np.empty(len(me2.vertices) * 3)
    me2.vertices.foreach_get('normal', vn2)
    vn2 = vn2.reshape(-1, 3)
    g = np.zeros(len(co2))
    for f in crest_feathers():
        a_, b_, h_ = PP.feather_local(co2, f)
        on = (a_ > 0.05) & (a_ < 1.05) & (np.abs(b_) < 1.4) & (np.abs(h_) < f['T'])
        g = np.where(on, np.maximum(g, smooth(0.4, 0.9, np.cos(2 * np.pi * b_ * 2.5))), g)
    S.set_positions(hi_body, co2 - vn2 * (0.0012 * g)[:, None])
    hi_body.data.shade_smooth()
    C.log(f'carve: {chips} loose chips dropped; {len(pick)} soft tufts on the high body (voxel {vox:.4f}), {len(hi_body.data.polygons)} faces')
    S.base_attrs(hi_body, S.mesh_arrays(hi_body)[0])


def carve_low(lo_body) -> None:
    """The game mesh: drop any loose chip the voxel remesh left (build 5: one at the crest's tip)."""
    PP.drop_islands(lo_body)

def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    eye_d = np.minimum(*(np.linalg.norm(co - eye_frame(s)[0], axis=1) for s in (1, -1)))
    face = (y < -0.12) & (z > 0.42) & (z < 0.66) & (np.abs(x) < 0.21)
    beak_d = np.linalg.norm(co - np.array((0.0, -0.235, 0.505)), axis=1)
    return {'face': face, 'eye_d': eye_d, 'beak_d': beak_d, 'belly': (y < -0.05) & (z < 0.4)}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(0.9 * (z['eye_d'] < 0.075) + 0.5 * z['face'] + 0.6 * (z['beak_d'] < 0.05), 0, 1)


def texel_k(fc: np.ndarray) -> np.ndarray:
    z = zones(fc)
    k = np.where(z['face'], 1.5, 1.0)
    return np.where(fc[:, 2] < 0.12, 0.65, k)


# ----------------------------------------------------------------------------- the coat: lying locks (baked)
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    """Combed down and a little back over the body; back over the crown from the crest; on the face out from the beak
    and the eyes."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    g = np.tile(np.array((0.0, 0.3, -1.0)), (len(p), 1))
    crown = p - np.array((0.0, -0.01, 0.75))
    crown[:, 2] = crown[:, 2] * 0.3 - 0.05
    g = np.where((zz > 0.6)[:, None], crown, g)
    rad = p - np.array((0.0, -0.3, 0.51))
    rad[:, 2] -= 0.04
    face = ((y < -0.1) & (zz > 0.4) & (zz <= 0.66))[:, None]
    g = np.where(face, rad, g)
    t = g - n * (g * n).sum(axis=1, keepdims=True)
    bad = np.linalg.norm(t, axis=1) < 1e-5
    t[bad] = np.cross(n[bad], np.array((1.0, 0.0, 0.0)))
    return t / np.linalg.norm(t, axis=1, keepdims=True)


def body_lock_params(p, n):
    """Short soft down all over (4-details panel 6), finer on the face; none on the eyes or at the beak's root."""
    z = zones(p, n)
    k = len(p)
    L = np.where(z['face'], 0.02, 0.036)
    W = np.where(z['face'], 0.0085, 0.0095)
    sp = np.where(z['face'], 0.0056, 0.0072)
    lift = np.full(k, math.radians(7.0))
    # build 6: none on the crest's curls (their roots shaded them grey); the bald ring round the beak smaller
    skip = (z['eye_d'] < EYE_R * 0.3) | (z['beak_d'] < 0.038) | crest_zone(p)
    return np.where(skip, np.nan, sp), L, W, lift, z


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The ball moves on four bones, blended by height (the face and the beak's root fully on the head)."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    a = smooth(0.16, 0.3, z)
    h = z + 0.27 * (-y)
    b = smooth(0.42, 0.49, h)
    c = smooth(0.47, 0.53, h)
    w = {'hips': 1.0 - a, 'chest': a * (1.0 - b), 'neck.1': a * b * (1.0 - c), 'head': a * b * c}
    m = crest_zone(co)
    return [(np.ones(len(co), bool), w), (m, U.chain_weights(co[m], CREST_PTS, ['crest.1', 'crest.2'], 'head', fade=(0.12, 0.02)))]


# ----------------------------------------------------------------------------- props
PK_WING, PK_SHIN, PK_TARSUS, PK_TOE, PK_BEAK, PK_JAW, PK_CREST, PK_TAIL, PK_HALO = 1, 2, 3, 4, 5, 6, 7, 8, 9


def _tag(ob, pk: int, side: float = 0.0, extra: dict | None = None):
    from lib import surface as S
    nv = len(ob.data.vertices)
    S.add_attr(ob, 'pk', np.full(nv, float(pk)))
    S.add_attr(ob, 'ps', np.full(nv, float(side)))
    for k, v in (extra or {}).items():
        S.add_attr(ob, k, np.full(nv, float(v)) if np.isscalar(v) else v)
    return ob


def _decimate(ob, tris: int):
    from lib import surface as S
    S.decimate_to(ob, tris, smooth_after=0.0)
    return ob


def build_props(high: bool, quick: bool) -> list:
    from lib import surface as S
    tag = 'hi' if high else 'lo'
    out = []
    vw = 0.0018 if high else 0.0038
    if quick and high:
        vw = 0.003
    for s in (1, -1):
        st = 'L' if s > 0 else 'R'
        fs = wing_feathers(s)
        ob = PP.wing_slab(f'{tag}_wing{st}', fs, WING, s, vw, 0.013, 0.62, smooth_iters=5)
        if high:
            PP.barb_relief(ob, fs, PP.mirror(_NW, s), 0.0007)
        else:
            _decimate(ob, 5000)
        out.append(_tag(ob, PK_WING, s))
        # the leg: a short shin stub hidden in the down, the scaly tarsus, three front toes and a hind toe, pale claws
        lg = {k: PP.mirror(v, s) for k, v in LEG.items()}
        seg = 14 if high else 9
        out.append(_tag(PP.scaled_tube(f'{tag}_shin{st}', lg['knee'] + PP.unit(lg['knee'] - lg['ankle']) * 0.04, lg['ankle'], 0.022, 0.018,
                                       (1, 0, 0), 8, seg), PK_SHIN, s))
        out.append(_tag(PP.scaled_tube(f'{tag}_tarsus{st}', lg['ankle'] + PP.unit(lg['ankle'] - lg['toe']) * 0.028, lg['toe'], 0.0165, 0.0138, (1, 0, 0),
                                       28 if high else 10, seg, ring_k=0.07 if high else 0.0, n_scales=6), PK_TARSUS, s))
        base = lg['toe'] + np.array((0.0, -0.002, 0.0))
        for k, ang in enumerate((-30.0, 0.0, 30.0)):
            a = math.radians(ang * s)
            d = np.array((-math.sin(a) * 1.0, -math.cos(a), -0.06))
            L = 0.062 if k == 1 else 0.054
            ob = PP.toe(f'{tag}_toe{st}{k}', base, d, L, 0.0118, 22 if high else 8, seg, knuckles=3, arch=0.04)
            out.append(_tag(ob, PK_TOE, s))
            tip = base + PP.unit(d) * L * 0.96
            out.append(_tag(PP.talon(f'{tag}_claw{st}{k}', tip - PP.unit(d) * 0.004 + np.array((0, 0, 0.0045)), PP.unit(d + np.array((0, 0, -0.15))),
                                     0.022, 0.0078, 9 if high else 6, 10 if high else 7), PK_TOE, s, {'claw': 1.0}))
        hd = np.array((0.0, 1.0, -0.05))
        out.append(_tag(PP.toe(f'{tag}_hind{st}', base + np.array((0, 0.004, 0.0)), hd, 0.028, 0.0105, 12 if high else 6, seg, knuckles=1),
                        PK_TOE, s))
        out.append(_tag(PP.talon(f'{tag}_hclaw{st}', base + np.array((0, 0.029, 0.0045)), PP.unit((0, 1, -0.15)), 0.016, 0.0068,
                                 8 if high else 6, 10 if high else 7), PK_TOE, s, {'claw': 1.0}))
    seg = 24 if high else 14
    out.append(_tag(PP.beak(f'{tag}_beak', BEAK_UP['base'], BEAK_UP['tip'], BEAK_UP['width'], BEAK_UP['height'], BEAK_UP['hook'],
                            22 if high else 10, seg), PK_BEAK))
    out.append(_tag(PP.beak(f'{tag}_jaw', BEAK_LO['base'], BEAK_LO['tip'], BEAK_LO['width'], BEAK_LO['height'], BEAK_LO['hook'],
                            18 if high else 9, seg, flat_bottom=0.0), PK_JAW))
    # the crest's curls and the tail's fan, each voxel-united into one closed piece
    for nm, fs, pk, vx in (('tail', tail_feathers(), PK_TAIL, vw),):
        objs = [PP.feather(f'{tag}_{nm}_f{f["k"]}', f['root'], f['d'], f['n'], f['L'], f['W'], f['T'], curl=f['curl'], tip=f['tip'])
                for f in fs]
        ob = S.build_body(f'{tag}_{nm}', [], vx, 3, extra=objs)
        if high:
            PP.barb_relief(ob, fs, (0.0, 1.0, -0.3), 0.0007)
        else:
            _decimate(ob, 1300 if nm == 'crest' else 1500)
        out.append(_tag(ob, pk))
    out.append(_tag(halo_ring(f'{tag}_halo', HALO_C, HALO_AX, HALO_R, HALO_T, 96 if high else 56, 16 if high else 8), PK_HALO))
    return out


def halo_ring(name, c, ax, R, r, nu, nv):
    """The halo's torus, every face turned away from its centre circle (an inverted prop bakes inverted normals)."""
    from lib import surface as S
    ob = PP.torus(name, c, ax, R, r, nu, nv)
    axn = PP.unit(ax)

    def inside(fc):
        q = fc - np.asarray(c)[None]
        q = q - (q @ axn)[:, None] * axn[None]
        return np.asarray(c)[None] + q / np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-9) * R
    S.orient_away(ob, inside)
    return ob


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    pk = np.round(attr('pk')).astype(int)
    ps = attr('ps')
    regs = []
    for s in (1, -1):
        st = 'L' if s > 0 else 'R'
        side = np.sign(ps) == s
        m = (pk == PK_WING) & side
        if m.any():
            q = U.wing_points(WING, s)
            nm = U.wing_bone_names(WING, s)
            segs = [(nm[0], q['shoulder'], q['elbow']), (nm[1], q['elbow'], q['wrist']), (nm[2], q['wrist'], q['fingers'][0])]
            regs.append((m, U.segment_weights(co[m], segs, power=6.0)))
        for pkk, bone in ((PK_SHIN, f'shin.{st}'), (PK_TARSUS, f'tarsus.{st}'), (PK_TOE, f'toe.{st}')):
            mm = (pk == pkk) & side
            if mm.any():
                regs.append(U.rigid(mm, bone))
    regs.append(U.rigid(pk == PK_BEAK, 'head'))
    regs.append(U.rigid(pk == PK_JAW, 'jaw'))
    regs.append(U.rigid(pk == PK_HALO, 'prop.halo'))
    m = pk == PK_TAIL
    regs.append((m, U.chain_weights(co[m], TAIL_PTS, ['tail.1', 'tail.2'], 'hips', fade=(0.02, -0.05))))
    return regs


def preview_prop_colour(name: str):
    if any(k in name for k in ('beak', 'jaw', 'tarsus', 'toe', 'hind', 'shin', 'halo')):
        return PALETTE['accent']
    if 'claw' in name:
        return '#F2E6CC'
    return '#E9E4DA'


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool):
    return PP.build_lens(name, eye_frame(s), EYE_R, EYE_DEPTH, EYE_SINK, s, high)


LASH_V = -0.12                                   # the closed lid's line, x the lens's radius below its centre


def blink_pivot(s: int):
    from mathutils import Vector
    c, _xax, yax, look = eye_frame(s)
    p = c - look * EYE_SINK + yax * (EYE_R * LASH_V)
    return Vector(tuple(p)), Vector(tuple(yax)), Vector(tuple(look))


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    return PP.eye_material(name, rough_pass, (pal or PALETTE)['eye'], vis=0.88)


# ----------------------------------------------------------------------------- paint
def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import paladove_paint as PT
    PT.paint_young(body_srcs, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from lib import bake as BK
    return BK.emission_attr_material(name, attr)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import paladove_paint as PT
    return PT.body_colours(co, vn, None, None, eye_frame, young=True)[0]


REVIEW = {'centre': (0.0, 0.0, 0.44), 'size': 1.12, 'head': ((0.0, -0.12, 0.6), 0.5),
          'clips': [('cast', 0.55), ('win', 0.5), ('hit', 0.3), ('fly', 0.25), ('sleep', 0.5)]}

# the every-frame checker's roots (scratchpad paladove_check.py): rest-pose vertices that must stay inside the body
CHECK_BODY_HALO = 0.76                          # body vertices above this (the crest) are checked against the halo
CHECK_ROOTS = {PK_BEAK: lambda p: p[:, 1] > -0.233, PK_JAW: lambda p: p[:, 1] > -0.229,
               PK_TAIL: lambda p: np.linalg.norm(p - np.array((0.0, 0.243, 0.181)), axis=1) < 0.012}
