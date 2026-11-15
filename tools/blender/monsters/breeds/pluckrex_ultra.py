"""Pluckrex (young) at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (breeds/RECIPE.md, "Biped
plan").

A brave little two-legged dinosaur, a plucky underdog (chatgpt/monsters/12-pluckrex/: the card decides the parts,
1-hero the shapes, 2-turnaround the measurements, CONTENT §2.2 #23 the colours):
  - a big head on a small, sturdy pear body; strong legs on three-toed feet with big dark claws; stubby little arms
    with three-fingered hands and dark claws, held forward; a thick, short tail;
  - a wide open toothy grin (the hero; modelled open, a row of small rounded teeth on each rim, a pink tongue), bright
    big eyes under thick navy brows, a rounded snout with two nostrils, wide cream cheeks;
  - the fan crest: a sagittal fan of broad ribbed petals over the crown and down the back of the head, and a halo of
    petals round the back of the head (from the front a sunflower with a tall rib in the middle, from the side a
    semicircular fan: 2-turnaround), sunflower gold and glowing (the glow map); a row of gold spines down the nape, the
    back and the tail's top;
  - a pebbly slate-blue hide of mixed domed pebbles (bigger along the back), and a smooth cream throat, belly, tail
    underside and lower jaw with flat plates, the border speckled pebble by pebble.
The shared machinery: pluckrex_body.Form (shape), pluckrex_zones, pluckrex_hide (the pebbles), pluckrex_props,
pluckrex_paint, pluckrex_face and pluckrex_recipe; this file holds the young form's numbers.
Size: about 1 x Puddlepup (PROMPTS.md): HEIGHT_UNITS 150; the head's skin about 0.91 m tall, the crest's top 1.06 m.
Measured on 2-turnaround.png at 1.436 mm a pixel (the crest's top at 1.06 m), the side view's y = 0 at the ankles.
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import numpy as np

from monsters.breeds import pluckrex_form as PF
from monsters.breeds import pluckrex_recipe as RC
from monsters.breeds.pluckrex_body import Form

ID = 'pluckrex'
LOOK = 'pluckrex-ultra'
PLAN = 'biped'
HEIGHT_UNITS = 150
PALETTE = {'body': '#4F6D8F', 'belly': '#F1E6CF', 'accent': '#F7C548', 'eye': '#2B2D42'}
VARIANTS: dict = {}

VOXELS = {'hi': 0.0022, 'hi_quick': 0.004, 'lo': 0.0048}
BODY_TRIS = 54000                    # round 3: a rounder skull outline against the crest
ATLAS_STRIP = 0
CARD_LAYERS = 0
NORMAL_SCALE = 1.05                  # the pebbles' baked relief
BODY_SHEEN = 0.08                    # scaled hide: little sheen (round 2: less wet shine)
AO_FLOOR = 0.55                      # polish: no dark mottling in the crest's overlaps or black holes in the mouth
AO_SOFTEN = 2.0
BLINK_CLOSED = (0.7, 0.02, 0.08)     # polish: no iris sliver past the shut lid (hit, hit_heavy, ko)
# the jaw's heat weights go to the head; only the lower jaw's skin below the grin rides the jaw (pluckrex_recipe.jaw_weight)
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
# round 3: the glow takes each texel's own colour (orange roots, gold tips); a fixed gold tint also lit the hide gold
# wherever the small mip levels mix a crest texel in (the specks at 64 px)
GLOW = {'strength': 1.5, 'tint': None}
ATLAS_DENSITY = {'lo_eyes': 3.0, 'lo_props': 1.6}       # polish: smooth pupil and iris edges
UV_SMOOTH = 0                        # polish: the smoothed unwrap stretched the neck, the back and the tail's end
LITE_PROPS_TRIS = 3600                # the crest, the spines, the teeth and the claws are the signature

_TAIL = [(0.0, 0.06, 0.235), (0.0, 0.2, 0.265), (0.0, 0.32, 0.295), (0.0, 0.42, 0.318), (0.0, 0.515, 0.335)]
_TAIL_R = [0.13, 0.1, 0.07, 0.042, 0.014]


def _tail_spine(t: float, h: float) -> dict:
    p, _d = PF.curve_at(_TAIL, t)
    return {'from': (0.0, float(p[1]), float(p[2]) + 0.4), 'dir': (0.0, 0.05, -1.0), 'h': h, 'tilt': 1.0, 'base': 0.45}


G_YOUNG = {
    'k': 1.0,
    'head': {
        'cranium': ((0.0, -0.07, 0.775), (0.172, 0.15, 0.135)),
        # round 2: no cheek pouches; a wider, lower face makes the jowls (the reviewer: hamster pouches, ear-like from behind)
        'face': ((0.0, -0.13, 0.765), (0.152, 0.112, 0.105)),
        # round 2: the upper jaw tipped nose-down 10 degrees, with side walls down to the lip line, so it flows from the
        # skull and its lip line rises toward the corners (a U-shaped smile), never a ball overhanging the mouth
        # round 3: about 25% narrower, longer and tapering, its top running up into the forehead in one line, so both
        # eyes sit fully above it (a round snout ball covered their inside corners)
        'snout': ((0.0, -0.242, 0.703), (0.082, 0.125, 0.064), (10.0, 0.0, 0.0)),
        'upperlip': ((0.07, -0.235, 0.684), (0.044, 0.118, 0.032), (10.0, 0.0, 0.0)),
        'bridge': ((0.0, -0.225, 0.755), (0.048, 0.118, 0.048), (6.0, 0.0, 0.0)),
        'nose': ((0.0, -0.33, 0.72), (0.05, 0.036, 0.036)),
        'jaw': ((0.0, -0.232, 0.632), (0.115, 0.112, 0.052)),
        # a rounded tongue on the floor of the mouth (round 3: depth, not a flat pink slab)
        'tongue': ((0.0, -0.245, 0.655), (0.06, 0.082, 0.026)),     # polish: fused with the floor (no black pocket)
        # the fold under the jaw filled (stretched scales and dark shards where the jaw met the neck)
        'gullet': ((0.0, -0.16, 0.6), (0.085, 0.09, 0.06)),
        # the wide cream jowls are the lower jaw's sides, behind the corners (no pouches above them)
        'jawside': ((0.068, -0.17, 0.648), (0.05, 0.076, 0.05), (-8.0, 0.0, 0.0)),     # polish: tucked inside the neck from behind
        'chin': ((0.0, -0.2, 0.615), (0.105, 0.1, 0.05)),
        'throat': ((0.0, -0.12, 0.6), (0.095, 0.1, 0.075)),
        'hinge': (0.0, -0.12, 0.69),
        'jaw_open': 8.0,
    },
    # round 2: bigger (15%), higher, turned further out so a round iris shows in profile, seated deeper under a lid
    # round 3: a little higher (fully above the snout) and domed out so it reads round from the side
    # polish: sunk about a third into the skull under a fuller lid, turned 10 degrees more to the front
    'eye': {'x': 0.106, 'z': 0.775, 'r': 0.062, 'shape': (1.0, 1.05), 'depth': (0.6, 0.42), 'out': 0.48, 'up': 0.03, 'lid': 0.009},
    # the smile's crease: from each corner of the grin up and back into the cheek (x out, y back, z up; 3-faces, 1-hero)
    'smile': None,                       # polish: no carved crease (it read as a cut on the cream cheek)
    'brow_arc': [(-0.45, 1.18, 0.13), (-0.05, 1.33, 0.18), (0.4, 1.36, 0.17), (0.8, 1.22, 0.11)],     # a crisp stroke just above the lid
    'nose': {'dx': 0.021, 'c': (0.0, -0.362, 0.724), 'r': 0.0068, 'shape': (1.2, 1.0, 1.0), 'paint': (1.25, 2.2, 0.85)},
    'neck': [((0.0, -0.04, 0.55), (0.08, 0.1, 0.13))],
    'torso': [('chest', (0.0, -0.03, 0.42), (0.125, 0.125, 0.11)),
              ('belly', (0.0, -0.06, 0.27), (0.16, 0.16, 0.165)),     # round 3: a rounder pot belly
              ('back', (0.0, 0.035, 0.38), (0.12, 0.1, 0.13)),
              ('hips', (0.0, 0.04, 0.22), (0.15, 0.13, 0.11))],
    'leg': {'hip': (0.115, 0.0, 0.27), 'knee': (0.155, -0.065, 0.165), 'ankle': (0.185, 0.005, 0.075), 'toe': (0.195, -0.16, 0.025),
            'thigh': ((0.145, -0.025, 0.245), (0.1, 0.125, 0.13), (0.0, 0.0, 0.0)), 'shin_r': (0.064, 0.054),
            'heel': ((0.18, 0.03, 0.068), (0.06, 0.065, 0.058)), 'foot': ((0.185, -0.055, 0.042), (0.072, 0.115, 0.042)),
            'yaw': 6.0, 'toe_dx': (-0.045, 0.0, 0.045), 'toe_y': -0.13, 'toe_z': 0.034, 'toe_r': (0.029, 0.046, 0.03),
            'claw': (0.04, 0.024)},
    'arm': {'shoulder': (0.1, -0.07, 0.46), 'elbow': (0.18, -0.1, 0.39), 'wrist': (0.24, -0.16, 0.345), 'hand': (0.275, -0.207, 0.325),
            'r': (0.05, 0.044, 0.042, 0.036), 'palm_len': 0.028, 'palm_w': 0.027, 'palm_size': (0.02, 0.032, 0.035),
            # round 2: three distinct clawed fingers (spread wider, slimmer), not a mitten
            # round 3: stubby fingers with short, thick, dark claws like the feet's
            'finger_ang': (-36.0, 0.0, 36.0), 'finger_len': (0.024, 0.027, 0.024), 'finger_r': 0.0145, 'curl': 0.3,
            'claw': (0.017, 0.0105)},
    'tail': {'pts': _TAIL, 'rad': _TAIL_R},
    'back_y': lambda zz: np.interp(zz, [0.1, 0.3, 0.45, 0.6, 0.72], [0.06, 0.04, 0.01, -0.02, -0.03]),
    'cream': {'lip_z': 0.655, 'cheek_z': 0.665, 'cheek_out_z': 0.645, 'snout_w': 0.085, 'cheek_back': -0.45,
              'neck_axis': [(0.0, -0.03, 0.42), (0.0, -0.07, 0.64)], 'neck_r': 0.16, 'neck_cos': 0.45,
              'belly': (0.31, 0.22), 'belly_w': (0.095, 0.135, 0.09), 'belly_y': 0.02, 'tail_under': -0.1,
              'under': ((0.0, 0.13, 0.11), (0.06, 0.07, 0.065))},
    'pebbles': {'body': 0.026, 'leg': 0.032, 'foot': 0.016, 'arm': 0.019, 'hand': 0.013, 'tail': (0.028, 0.013), 'back_k': 0.35,
                'head': 0.017, 'face': 0.012, 'cream_k': 1.1, 'dome': 0.28, 'flat': 0.03, 'soft': 0.55, 'seed': 1212},
    # round 3: keeled scales along the spine (graded hide: tiny on the snout, medium on the body, larger on the thighs)
    'keel': {'sp': 0.042, 'h': 0.12},
    'crest': {
        'rib': 0.9,
        'rim': 0.7,
        # the sagittal fan: from over the forehead (leaning 52 degrees forward) round to the back of the neck
        'fan': {'pivot': (0.0, -0.014, 0.768), 'angles': [-52, -30, -8, 14, 36, 58, 80, 102, 124],
                'lens': [0.21, 0.235, 0.25, 0.255, 0.26, 0.255, 0.24, 0.215, 0.18], 'root': 0.42, 'w': 0.1, 'th': 0.026,
                'stagger': 0.003},
        # the halo round the back of the head (a sunflower from the front), down to the eyes' level
        # round 2: sixteen petals wrapping lower round the head (one sunflower halo from the front, not two wings)
        'halo': {'pivot': (0.0, -0.01, 0.78), 'angles': [-114, -98, -82, -66, -50, -34, -18, 18, 34, 50, 66, 82, 98, 114],
                 'lens': [0.215, 0.245, 0.255, 0.26, 0.26, 0.255, 0.25, 0.25, 0.255, 0.26, 0.26, 0.255, 0.245, 0.215],
                 'back': 22.0, 'back_low': 1.2, 'root': 0.35, 'w': 0.086, 'th': 0.022},
    },
    # one row of rounded gold plates: up the back of the head under the fan, down the nape, the back and the tail
    'spines': {'items': [
        {'from': (0.0, 0.5, z), 'dir': (0.0, -1.0, dz), 'h': h, 'tilt': tl, 'base': 0.5}
        for z, dz, h, tl in ((0.59, -0.05, 0.062, 0.5), (0.535, -0.1, 0.062, 0.55),
                             (0.48, -0.1, 0.06, 0.6), (0.425, -0.15, 0.056, 0.65), (0.37, -0.2, 0.052, 0.7), (0.32, -0.4, 0.05, 0.8))
    ] + [_tail_spine(t, h) for t, h in ((0.1, 0.048), (0.21, 0.046), (0.32, 0.043), (0.43, 0.04), (0.54, 0.036), (0.65, 0.032),
                                         (0.76, 0.027), (0.87, 0.021))]},
    'teeth': {'upper': {'n': 9, 'span': 0.8, 'len': 0.016, 'r': 0.011}, 'lower': {'n': 4, 'span': 0.5, 'len': 0.011, 'r': 0.009, 'inset': 0.0},
              'inset': 0.006, 'fwd': 0.15},
    'glow': {'crest': 0.65, 'spine': 0.22},
    'rig': {'hip': (0.0, 0.0, 0.27), 'chest': (0.0, -0.035, 0.47), 'head_c': (0.0, -0.1, 0.77), 'head_r': 0.15,
            'chin': (0.0, -0.33, 0.6), 'crest_bone': ((0.0, -0.02, 0.86), (0.0, 0.0, 0.98)), 'strike': 'headbutt',
            'relax_k': 0.75,
            # the hopping headbutt (5-poses attack): a real hop with the feet tucked, the body thrown forward, the head
            # held up so the face and the crest read from the in-game strike camera (70 degrees), turned toward it
            # round 2 (the reviewer: it read as a bite): the wind-up crouches with the head drawn down and back, then the
            # impact is airborne with the head pitched down so the forehead and the crest's base lead, the grin gritted
            # round 3: a deeper wind-up (knees bent, head pulled down and back, arms tucked) and the head further down
            # polish: toward the long horizontal hop (5-poses attack): the body thrown forward, the legs trailing back,
            # the crown leading and the eyes forward
            'headbutt': {'hop': 0.22, 'rear': 8.0, 'lean': 48.0, 'reach': 0.34, 'gaze': 0.0, 'neck': -4.0, 'head': -10.0,
                         'lift': 0.2, 'trail': 0.28, 'yaw': 12.0, 'jaw': -7.0, 'crouch': 0.38, 'neck_wind': 12.0,
                         'head_wind': 20.0, 'jaw_wind': -6.0, 'arm_wind': 55.0},
            # the hits move the whole body: the torso squashes, it rocks back and the right foot steps back (5-poses)
            'hit_body': {'squash': 0.5, 'lean': -4.0, 'step': 0.8, 'heavy': 1.4},     # polish: more squash, hips and a foot back
            'walk_bob': 2.0, 'ko_jaw': -6.0,
            'stride': 0.24,                       # a longer walk with a body bob (the reviewer: the feet barely separated)
            'ko_head': (0.0, -22.0, 0.0),         # the face turns with the body toward the camera in ko
            # the hands stay in front of the round belly and the chest (clip_hit buried them)
            'hand_clear': [{'bone': 'spine', 'c': (0.0, -0.04, 0.27), 'r': (0.155, 0.14, 0.165), 'margin': 0.03, 'push': (0.0, -1.0, 0.0)},
                           {'bone': 'chest', 'c': (0.0, -0.03, 0.42), 'r': (0.125, 0.125, 0.11), 'margin': 0.03, 'push': (0.0, -1.0, 0.0)}]},
}



def _lift_head(G: dict, dz: float) -> None:
    """Round 2: the head carried dz higher on a longer neck (the reviewer: the jaw rested on the shoulders)."""
    up = lambda p: (float(p[0]), float(p[1]), float(p[2]) + dz)
    H = G['head']
    for key, v in list(H.items()):
        if key == 'hinge':
            H[key] = up(v)
        elif isinstance(v, tuple) and len(v) >= 2 and isinstance(v[0], tuple):
            H[key] = (up(v[0]),) + tuple(v[1:])
    G['eye']['z'] += dz
    G['nose']['c'] = up(G['nose']['c'])
    for part in ('fan', 'halo'):
        G['crest'][part]['pivot'] = up(G['crest'][part]['pivot'])
    R = G['rig']
    R['head_c'], R['chin'] = up(R['head_c']), up(R['chin'])
    R['crest_bone'] = (up(R['crest_bone'][0]), up(R['crest_bone'][1]))
    Cr = G['cream']
    for key in ('lip_z', 'cheek_z', 'cheek_out_z'):
        Cr[key] += dz
    Cr['neck_axis'] = [Cr['neck_axis'][0], up(Cr['neck_axis'][1])]
    for it in G['spines']['items']:
        if it['from'][2] >= 0.64:
            it['from'] = up(it['from'])
    (c, r), = G['neck']
    G['neck'] = [((c[0], c[1], c[2] + dz * 0.5), (r[0], r[1], r[2] + dz * 0.5))]


_lift_head(G_YOUNG, 0.03)
FORM = Form(G_YOUNG)
RC.export(FORM, globals())

CLIP_CALM = {
    '*': {'tail': 0.85},
    # the grin is modelled open: the plan's smiles and strikes open it further, by less
    'idle_happy': {'jaw': 0.6}, 'win': {'jaw': 0.6}, 'strike': {'jaw': 0.6}, 'cast': {'jaw': 0.6},
    # round 3: the hits keep the mouth from gaping at the sky
    'hit': {'jaw': -0.8}, 'hit_heavy': {'jaw': -0.8}, 'idle_tired': {'jaw': 0.6},     # polish: gritted, never a yawn
}

FACE_NOTE = ('Baked face: glossy lenses (lo_eyes) with an amber-brown iris, a big navy pupil, two catchlights and the '
             'upper lash line; the thick navy brows and the nostrils baked into the body. The grin is modelled open (a '
             'real mouth with a rose palate and a pink tongue painted inside), small rounded teeth on both rims (props on '
             'the head and the jaw); the jaw opens it wider in the smiles and the strikes. No face sheet and no morphs. '
             'Blinking scales the blink bones: each lens squashes onto the closed lid\'s lash line and sinks into the '
             'head. The fan crest and the spines glow sunflower gold (ORM alpha).')

REVIEW = {'centre': (0.0, 0.08, 0.52), 'size': 1.25, 'head': ((0.0, -0.13, 0.78), 0.6)}
