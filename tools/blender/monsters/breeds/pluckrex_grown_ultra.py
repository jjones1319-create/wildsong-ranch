"""Pluckrex, the grown form, at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (look
`pluckrex-grown`; RECIPE.md "Grown forms" and "Biped plan").

chatgpt/monsters/12-pluckrex/grown-*.png (PROMPTS.md "the GROWN form"): the same dinosaur grown up, a determined hero.
Taller and sturdier on longer, thicker legs and wide feet, a longer neck (three bones) carrying the young form's face
(the same big eyes, open toothy grin and cream cheeks, the snout a little longer), a round cream belly pushed forward,
a longer, thicker tail; a bigger fan crest with more ribs (a ten-petal fan and a fourteen-petal halo reaching down to
the jaw); bigger gold spines; stone bracers on the forearms carved with a glowing gold sun (pluckrex_bracers.py); a
tougher hide: the pebbles plus keeled ridge scales down the back and the tail's top; bigger claws.
The shared machinery is the young form's (pluckrex_body.Form, pluckrex_recipe); this file holds the grown numbers. The
head is the young head (pluckrex_ultra.G_YOUNG) scaled 1.03 and moved up, its snout and jaw 5 cm longer.
Size: about 1.5 x Puddlepup (PROMPTS.md): HEIGHT_UNITS 225; the head's skin about 1.39 m tall, the crest's top 1.6 m.
Measured on grown-2-turnaround.png at 2.178 mm a pixel (the crest's top at 1.59 m), the side view's y = 0 at the ankles.
Colours: CONTENT §2.2 #23, the same as the young form; the bracers' grey stone is derived (pluckrex_paint).
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import numpy as np

from lib.surface import v3
from monsters.breeds import pluckrex_bracers as BR
from monsters.breeds import pluckrex_form as PF
from monsters.breeds import pluckrex_recipe as RC
from monsters.breeds import pluckrex_ultra as Y
from monsters.breeds.pluckrex_body import Form

ID = 'pluckrex-grown'
LOOK = 'pluckrex-grown-ultra'
PLAN = 'biped'
HEIGHT_UNITS = 225
PALETTE = dict(Y.PALETTE)
VARIANTS: dict = {}

VOXELS = {'hi': 0.0029, 'hi_quick': 0.005, 'lo': 0.0062}
BODY_TRIS = 54000
ATLAS_STRIP = 0
CARD_LAYERS = 0
NORMAL_SCALE = 1.1
BODY_SHEEN = 0.05                    # round 2: less frosty sheen on the back under the rims
AO_FLOOR = 0.55                      # polish: no dark mottling in the crest's overlaps
AO_SOFTEN = 2.0
BLINK_CLOSED = Y.BLINK_CLOSED
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
GLOW = dict(Y.GLOW)                  # round 3: the glow takes each texel's own colour (Y.GLOW tint None)
ATLAS_DENSITY = {'lo_eyes': 2.8, 'lo_props': 1.6}       # polish: smooth pupil and iris edges
UV_SMOOTH = 0                        # polish: the smoothed unwrap stretched the neck, the back and the tail's end
LITE_PROPS_TRIS = 4400

# ----------------------------------------------------------------------------- the head: the young one, moved and grown
# round 2 (the reviewer: the head about 1/7 of the body, the face a smear at 64 px, the snout a third too long): the young
# head scaled 1.3 with the young form's own proportions (no longer snout), the eyes about 1.5x the round-1 grown ones
_CY = v3(Y.G_YOUNG['head']['cranium'][0])
_CG = v3((0.0, -0.14, 1.37))         # polish: carried 10 cm higher on a longer neck
_SH = 1.2


def _tp(c):
    return tuple(map(float, _CG + (v3(c) - _CY) * _SH))


def _te(e):
    return (_tp(e[0]), tuple(float(r) * _SH for r in e[1])) + tuple(e[2:])


_YH = Y.G_YOUNG['head']
HEAD = {key: _te(v) for key, v in _YH.items() if key not in ('hinge', 'jaw_open')}
HEAD['hinge'] = _tp(_YH['hinge'])
HEAD['jaw_open'] = _YH['jaw_open']
# round 3: the hips higher on longer legs: the tail's root rises with them
_TAIL = [(0.0, 0.12, 0.56), (0.0, 0.25, 0.53), (0.0, 0.38, 0.52), (0.0, 0.51, 0.53), (0.0, 0.64, 0.55), (0.0, 0.77, 0.58),
         (0.0, 0.885, 0.62)]
_TAIL_R = [0.22, 0.18, 0.145, 0.11, 0.077, 0.045, 0.016]


def _tail_spine(t: float, h: float) -> dict:
    p, _d = PF.curve_at(_TAIL, t)
    return {'from': (0.0, float(p[1]), float(p[2]) + 0.6), 'dir': (0.0, 0.05, -1.0), 'h': h, 'tilt': 1.0, 'base': 0.45}


_E = Y.G_YOUNG['eye']
_N = Y.G_YOUNG['nose']
G_GROWN = {
    'k': 1.5,
    'head': HEAD,
    'eye': {**_E, 'x': _E['x'] * _SH, 'z': _tp((0.0, -0.2, _E['z']))[2], 'r': _E['r'] * _SH, 'lid': 0.012},
    'brow_arc': Y.G_YOUNG['brow_arc'],
    'smile': Y.G_YOUNG['smile'],
    'nose': {**_N, 'c': _tp(_N['c']), 'dx': _N['dx'] * _SH, 'r': _N['r'] * _SH},
    # round 2: tougher and sturdier: a thicker neck base, a broader chest and thighs
    'neck': [((0.0, -0.18, 0.98), (0.128, 0.195, 0.21)), ((0.0, -0.21, 1.13), (0.115, 0.16, 0.13)),
             ((0.0, -0.225, 1.24), (0.105, 0.135, 0.1))],
    # round 3: the torso about 15% shorter and higher, on longer legs (the reviewer: it read as a chubby squatter)
    'torso': [('chest', (0.0, -0.2, 0.8), (0.2, 0.18, 0.14)),
              ('belly', (0.0, -0.18, 0.6), (0.225, 0.215, 0.22)),
              ('waist', (0.0, -0.19, 0.72), (0.2, 0.18, 0.12)),     # no crease where the chest meets the belly
              ('back', (0.0, -0.01, 0.71), (0.19, 0.155, 0.16)),
              ('hips', (0.0, 0.04, 0.53), (0.22, 0.17, 0.14))],
    # round 3: longer, nearly upright shins and a straighter knee, so a shin and an ankle show (grown-2 side)
    'leg': {'hip': (0.17, -0.04, 0.55), 'knee': (0.225, -0.1, 0.33), 'ankle': (0.255, -0.04, 0.112), 'toe': (0.27, -0.3, 0.04),
            'thigh': ((0.245, -0.06, 0.45), (0.15, 0.22, 0.22), (0.0, 0.0, 0.0)), 'shin_r': (0.105, 0.09),     # polish: heavy drumsticks
            'heel': ((0.255, 0.0, 0.1), (0.095, 0.1, 0.09)), 'foot': ((0.27, -0.13, 0.062), (0.1, 0.175, 0.062)),
            'yaw': 8.0, 'toe_dx': (-0.065, 0.0, 0.065), 'toe_y': -0.25, 'toe_z': 0.05, 'toe_r': (0.042, 0.068, 0.044),
            'claw': (0.06, 0.036)},          # round 2: big, thick, blunt claws
    'arm': {'shoulder': (0.15, -0.15, 0.84), 'elbow': (0.27, -0.17, 0.76), 'wrist': (0.42, -0.26, 0.655), 'hand': (0.475, -0.33, 0.61),
            'r': (0.078, 0.068, 0.064, 0.055), 'palm_len': 0.04, 'palm_w': 0.04, 'palm_size': (0.03, 0.05, 0.052),
            # round 3: stubby fingers with short, thick, dark claws like the feet's
            'finger_ang': (-36.0, 0.0, 36.0), 'finger_len': (0.036, 0.04, 0.036), 'finger_r': 0.022, 'curl': 0.3,
            'claw': (0.034, 0.019)},          # polish: a clear dark claw on each finger
    'tail': {'pts': _TAIL, 'rad': _TAIL_R},
    'back_y': lambda zz: np.interp(zz, [0.26, 0.56, 0.76, 0.92, 1.15], [0.1, 0.06, -0.01, -0.1, -0.15]),
    'cream': {'lip_z': _tp((0.0, -0.3, Y.G_YOUNG['cream']['lip_z']))[2], 'cheek_z': _tp((0.0, -0.2, Y.G_YOUNG['cream']['cheek_z']))[2],
              'cheek_out_z': _tp((0.0, -0.2, Y.G_YOUNG['cream']['cheek_out_z']))[2], 'snout_w': 0.09, 'cheek_back': -0.45,
              'neck_axis': [(0.0, -0.2, 0.82), (0.0, -0.22, 1.24)], 'neck_r': 0.24, 'neck_cos': 0.4,
              'belly': (0.6, 0.24), 'belly_w': (0.12, 0.165, 0.125), 'belly_y': -0.08, 'tail_under': -0.1,
              'under': ((0.0, 0.17, 0.31), (0.08, 0.1, 0.1))},
    # round 2: graded sizes (tiny on the face, medium on the body, large on the thighs), flatter and tightly packed
    'pebbles': {'body': 0.034, 'leg': 0.042, 'foot': 0.022, 'arm': 0.026, 'hand': 0.016, 'tail': (0.038, 0.017), 'back_k': 0.3,
                'head': 0.017, 'face': 0.012, 'cream_k': 1.1, 'dome': 0.2, 'flat': 0.03, 'soft': 0.4, 'seed': 2323, 'leg_dome': 0.9},
    # the tougher hide: keeled ridge scales down the back and the tail's top (grown-4-details panel 5)
    'keel': {'sp': 0.065, 'h': 0.2},     # round 2: taller, readable ridges
    # round 2: the young crest scaled with the head and 1.15 more (about 1.7x the head's width from the front), more ribs,
    # seated on the skull as a fan (the round-1 halo stood upright behind the head: a band from the side)
    'crest': {
        'rib': 0.9,
        'rim': 0.7,
        'fan': {'pivot': _tp(Y.G_YOUNG['crest']['fan']['pivot']), 'angles': [-52, -34, -16, 2, 20, 38, 56, 74, 92, 110, 128],
                'lens': [v * _SH * 1.15 for v in (0.205, 0.23, 0.245, 0.25, 0.255, 0.257, 0.255, 0.245, 0.23, 0.21, 0.18)],
                'root': 0.42, 'w': 0.1 * _SH * 1.1, 'th': 0.026 * _SH, 'stagger': 0.004},
        'halo': {'pivot': _tp(Y.G_YOUNG['crest']['halo']['pivot']),
                 'angles': [-120, -104, -88, -72, -56, -40, -24, -8, 8, 24, 40, 56, 72, 88, 104, 120],
                 'lens': [v * _SH * 1.15 for v in (0.215, 0.24, 0.252, 0.258, 0.26, 0.258, 0.252, 0.25,
                                                    0.25, 0.252, 0.258, 0.26, 0.258, 0.252, 0.24, 0.215)],
                 'back': 22.0, 'back_low': 1.2, 'root': 0.35, 'w': 0.084 * _SH * 1.1, 'th': 0.022 * _SH},
    },
    'spines': {'items': [
        {'from': (0.0, 0.6, z), 'dir': (0.0, -1.0, dz), 'h': h, 'tilt': tl, 'base': 0.5}
        for z, dz, h, tl in ((1.15, 0.0, 0.09, 0.45), (1.07, -0.03, 0.1, 0.5), (0.99, -0.05, 0.1, 0.5), (0.93, -0.08, 0.105, 0.55),
                             (0.86, -0.1, 0.1, 0.6), (0.79, -0.15, 0.095, 0.65), (0.73, -0.2, 0.088, 0.7), (0.67, -0.35, 0.082, 0.8))
    ] + [_tail_spine(t, h) for t, h in ((0.08, 0.082), (0.18, 0.08), (0.28, 0.076), (0.38, 0.071), (0.48, 0.066), (0.58, 0.06),
                                         (0.68, 0.054), (0.78, 0.046), (0.88, 0.036))]},
    'teeth': {'upper': {'n': 9, 'span': 0.8, 'len': 0.016 * _SH, 'r': 0.011 * _SH},
              'lower': {'n': 4, 'span': 0.5, 'len': 0.011 * _SH, 'r': 0.009 * _SH, 'inset': 0.0},
              'inset': 0.006 * _SH, 'fwd': 0.15},
    # round 2: chunkier and longer, carved stone blocks with deep seams and chipped edges, a bigger carved sun
    'bracer': {'t': (0.2, 0.92), 'r': 0.062, 'th': 0.05, 'rim': 0.25, 'groove': 0.2, 'face': (0.3, -1.0, 0.0),
               'sun_r': 0.026, 'carve': 0.003},
    'glow': {'crest': 0.65, 'spine': 0.22, 'sun': 0.8},
    'rig': {'hip': (0.0, -0.02, 0.55), 'chest': (0.0, -0.17, 0.86), 'head_c': _tp(Y.G_YOUNG['rig']['head_c']), 'head_r': 0.15 * _SH,
            'chin': _tp(Y.G_YOUNG['rig']['chin']),
            'crest_bone': (_tp(Y.G_YOUNG['rig']['crest_bone'][0]), _tp(Y.G_YOUNG['rig']['crest_bone'][1])),
            'strike': 'charge', 'stride': 0.38, 'ko_head': (0.0, -22.0, 0.0), 'walk_bob': 1.5, 'ko_jaw': -6.0,
            # round 3: in ko the top arm lies against the body (it stood up like a periscope)
            'ko_arm': {'upper': (-20.0, 85.0, 0.0), 'fore': (-60.0, 0.0, 0.0)},
            'hit_body': {'squash': 0.25, 'lean': -16.0, 'step': 0.45, 'heavy': 1.6},
            # the hands stay clear of the throat (battle_idle buried one), the chest and the belly
            'hand_clear': [{'bone': 'neck.2', 'c': (0.0, -0.18, 0.98), 'r': (0.128, 0.195, 0.21), 'margin': 0.05, 'push': (0.0, -1.0, 0.0)},
                           {'bone': 'chest', 'c': (0.0, -0.2, 0.8), 'r': (0.2, 0.18, 0.14), 'margin': 0.04, 'push': (0.0, -1.0, 0.0)},
                           {'bone': 'spine', 'c': (0.0, -0.18, 0.6), 'r': (0.225, 0.215, 0.22), 'margin': 0.04, 'push': (0.0, -1.0, 0.0)}],
            'relax_k': 0.75, 'lean': 6.0, 'neck_bones': 3,
            'neck_points': [(0.0, -0.17, 0.86), (0.0, -0.19, 0.99), (0.0, -0.22, 1.12), (0.0, -0.215, 1.25)],
            # the charge (grown-5-poses attack; round 2: it read as a level lunging bite): driving forward with the head
            # down about 40 degrees so the forehead and the crest lead, the grin gritted, turned toward the 70-degree camera
            # round 3 (it read as a bow): the spine tipped toward 60 degrees, the rear leg driven out behind, the tail level
            # polish: the head 25 degrees further so the crest's front edge leads, the rear leg straight back, the arms
            # tucked to the chest
            'charge': {'lean': 52.0, 'gaze': 0.0, 'neck': 0.0, 'head': 13.0, 'reach': 0.4, 'step': 0.4, 'back': 0.85, 'tail': -8.0,
                       'yaw': 12.0, 'jaw': -7.0, 'hand': (0.12, -0.34, 0.76)}},
}

FORM = Form(G_GROWN)
G_GROWN['rig']['props'] = BR.prop_bones(FORM)
G_GROWN['rig']['head_base'] = G_GROWN['rig']['neck_points'][-1]
RC.export(FORM, globals(), extra_props=BR.build)

CLIP_CALM = dict(Y.CLIP_CALM)

FACE_NOTE = Y.FACE_NOTE + ' The bracers\' carved suns glow gold too.'

REVIEW = {'centre': (0.0, 0.18, 0.8), 'size': 1.9, 'head': ((0.0, -0.25, 1.26), 0.75)}
