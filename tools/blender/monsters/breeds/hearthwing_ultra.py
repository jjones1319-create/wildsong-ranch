"""Hearthwing, the young form, at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py`.

chatgpt/monsters/09-hearthwing/ (PROMPTS.md, 1-hero, 2-turnaround, 3-faces, 4-details, 5-poses): a round, stubby baby
dragon on four short, thick legs. A big round head with a short rounded snout, big gold eyes, a wide smile, copper nub
horns, a crest of orange-tipped spiky scales and an orange frill behind each cheek; tiny wings at the shoulders (folded
at rest: a teal arm, orange-brown finger bones, a veined orange membrane, a copper claw at the wrist); a row of
orange-tipped spikes from the nape to the tail; a short tail with a glowing orange spade; copper claws, four a paw.

The shared machinery (parts, scales, paint, rig hooks) is hearthwing_form.Form; this file holds the young form's numbers
(measured off 2-turnaround: crest 517 px tall = 0.986 m, so 1 px = 1.91 mm; the feet's midpoint is y 0).
Coat without fur: leaf scales laid like shingles on the high body, chevron bands down the cream chest; the chest's warm
heart and the spade in the glow pass. Size: about 1 x Puddlepup (HEIGHT_UNITS 150).

Part counts (the card): four legs, two wings, two horns, one tail with a spade. The frills behind the cheeks are in every
picture (not on the card's list): modelled as membranes on the ear bones. Wings: three fingers each (the pictures show
three ribs; RECIPE's estimate said about two).
Colours: CONTENT §2.2 #21 (#1F6F6A scales, #E9D8B4 belly, #FF8A3D membranes and glow, horns #B87333, eyes #FFD166).
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

from lib.mesh import Part
from monsters.breeds import hearthwing_form as HF

ID = 'hearthwing'
LOOK = 'hearthwing-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 150

PALETTE = {'body': '#1F6F6A', 'belly': '#E9D8B4', 'accent': '#FF8A3D', 'eye': '#FFD166', 'horn': '#B87333'}
VARIANTS: dict = {}

ATLAS_STRIP = 0                      # no fur cards, no tuft: the islands take the whole atlas
BODY_TRIS = 64000
ATLAS_DENSITY = {'lo_eyes': 1.3, 'lo_fins': 0.42, 'lo_props': 0.6}   # Nov 12: the working wings are about 4x the area
UV_SMOOTH = 120                      # round 3: the scaly body unwraps smoothed into far fewer, larger islands (uv_smooth_mask)
GLOW = {'strength': 2.2, 'tint': '#FF9F45'}   # Nov 12: the bloom stays orange (it went cream to white on the cream bib)    # round 2: the chest's heart and the spade glow clearly in-game
BLINK_CLOSED = (0.74, 0.04, 0.2)
MOUTH_SOCKET = (0.0, -0.566, 0.622)  # at the lips (the attack's flame puff; the plan's default sat 5 cm inside the snout)
MERGE_INTO_HEAD = ('eye.L', 'eye.R')  # round 2: the jaw moves the lower jaw's skin (the strike's snap, the open smiles)
AO_FLOOR = 0.35                      # round 2: the deeper scales' crevices never bake near black
AO_SOFTEN = 1.0
MEMBRANE_AO_BODY = False             # the folded wings leave no baked shadow on the flank (it stayed when they spread)
LITE_PROPS_TRIS = 4200               # Lite keeps the claws, horns, wing bones and frill spines whole (36 parts, 2.9k)
NORMAL_SCALE = 1.3                   # the baked scales' relief at full strength in the game's film material (default 0.6)

HEAD_C = (0.0, -0.25, 0.765)
NOSE_C = (0.0, -0.605, 0.705)

G_YOUNG = {
    'k': 1.0, 'k_face': 1.0,
    'head_c': HEAD_C, 'head_r': (0.2, 0.21, 0.185),
    # Nov 12 round 2: sunk about a third deeper (no lens edge in profile), a teal upper lid and a lid line with lashes
    # instead of the dark ring, a rounder closed lid
    'eye': {'r': 0.074, 'shape': (1.0, 1.06), 'depth': (0.6, 0.42), 'x': 0.122, 'z': 0.73, 'out': 0.004, 'fwd': 0.56,
            'iris': 0.95, 'pupil': 0.56, 'shift': (0.06, 0.04), 'rim': 0.12, 'lid_top': 0.1, 'lid_paint': 0.9,
            'lid_dome': 0.006},
    'nose_c': NOSE_C, 'nose_r': (0.018, 0.009, 0.011),
    'lid': (0.08, 0.16, 0.95),
    'head_parts': [
        Part('head', 'sphere', loc=HEAD_C, radius=1.0, scale=(0.2, 0.21, 0.185)),
        # Nov 12 round 2: one short rounded snout (the ridge between the eyes flattened into the brow, the nose knob 40%
        # smaller, the cream chin pulled back behind the nose tip)
        Part('snout', 'sphere', loc=(0.0, -0.5, 0.69), radius=1.0, scale=(0.062, 0.11, 0.054)),
        Part('bridge', 'sphere', loc=(0.0, -0.46, 0.73), radius=1.0, scale=(0.045, 0.09, 0.03)),
        Part('muzzle', 'sphere', loc=(0.0, -0.47, 0.64), radius=1.0, scale=(0.08, 0.1, 0.052)),
        Part('nose', 'sphere', loc=NOSE_C, radius=1.0, scale=(0.018, 0.011, 0.012)),
        Part('cheek', 'sphere', loc=(0.1, -0.365, 0.648), radius=0.047, scale=(1.0, 0.9, 0.82), mirror=True),
        Part('jowl', 'sphere', loc=(0.13, -0.29, 0.648), radius=0.052, scale=(0.85, 1.0, 0.9), mirror=True),
        Part('neck', 'capsule', loc=(0.0, -0.3, 0.5), to=(0.0, -0.28, 0.65), radius=0.165),
        Part('nape', 'sphere', loc=(0.0, -0.14, 0.66), radius=0.15, scale=(1.0, 1.0, 0.95)),
    ],
    'torso_parts': [
        Part('chest', 'sphere', loc=(0.0, -0.27, 0.37), radius=0.212, scale=(1.06, 0.9, 1.0)),
        Part('body', 'capsule', loc=(0.0, -0.15, 0.36), to=(0.0, 0.22, 0.335), radius=0.215),
        Part('belly', 'sphere', loc=(0.0, 0.0, 0.27), radius=1.0, scale=(0.215, 0.32, 0.15)),
        Part('shoulder', 'sphere', loc=(0.13, -0.24, 0.38), radius=0.12, mirror=True),
        Part('haunch', 'sphere', loc=(0.165, 0.245, 0.3), radius=0.138, scale=(0.86, 1.1, 1.05), mirror=True),
        Part('rump', 'sphere', loc=(0.0, 0.27, 0.36), radius=0.18, scale=(1.0, 0.85, 0.9)),
    ],
    'legs': {'FL': (0.15, -0.25), 'FR': (-0.15, -0.25), 'BL': (0.175, 0.255), 'BR': (-0.175, 0.255)},
    'leg': {
        'paw_k': {'F': 1.0, 'B': 1.04}, 'toe_dx': (-0.084, -0.028, 0.028, 0.084),
        'toe': {'dy': 0.134, 'dyk': 0.42, 'z': 0.044, 'r': 0.042, 'scale': (0.84, 1.25, 0.92)},
        'cleft': 0.011, 'cleft_len': 0.05, 'heart_pad': (0.02, 0.03, 0.022),
        'lean': {'F': 0.012, 'B': 0.012}, 'top': {'F': 0.36, 'B': 0.3}, 'bottom': 0.105, 'r': {'F': 0.086, 'B': 0.084},
        'arm_dx': 0.01, 'arm_z': {'F': 0.25, 'B': 0.2}, 'arm_r': {'F': 0.093, 'B': 0.093}, 'arm_scale': (1.0, 1.05, 1.35),
        'paw_dy': 0.025, 'paw_z': 0.064, 'paw_r': 0.107, 'paw_scale': (1.12, 1.0, 0.62),
        'heel_dy': 0.03, 'heel_z': 0.07, 'heel_r': 0.075,
        'claw': (0.05, 0.028, 0.14), 'claw_blunt': 'cone', 'claw_cap': 0.55, 'hip_z': {'F': 0.38, 'B': 0.34},
    },
    'tail': {'pts': [(0.0, 0.3, 0.37), (0.0, 0.45, 0.325), (0.0, 0.6, 0.305), (0.0, 0.72, 0.318), (0.0, 0.805, 0.36)],
             'rad': [0.128, 0.102, 0.076, 0.056, 0.044], 'bones': 4, 'tall': 1.2},
    # Nov 12 round 2 (originality): the card's spade, a flat leaf / arrowhead about a quarter as thick as wide, a centre
    # ridge, a faint steady glow (never a round glowing bud)
    # Nov 12 final (originality): a short, flat, rounded leaf-spade about 1.3 x as long as wide, its broad face to the
    # side, a midrib, a teal cup where it joins; one flat orange (no glow, no spots, no hot tip)
    'spade': {'base': (0.0, 0.78, 0.34), 'tip': (0.0, 0.95, 0.58), 'width': 0.23, 'thick': 0.06, 'bulge': 0.5, 'curl': 0.0,
              'taper': 1.0, 'profile': True, 'flat': True, 'collar': 0.24, 'midrib': (0.004, 0.01), 'keep': 0.6},
    'spikes': {
        # the dorsal row, big over the shoulders (2-turnaround side: 12 from the nape to the spade)
        'dorsal': [(-0.115, 0.08), (-0.035, 0.1), (0.05, 0.108), (0.135, 0.104), (0.215, 0.095), (0.29, 0.084)],
        'dorsal_up': (0.0, 0.55, 1.0), 'dorsal_w': 0.95, 'dorsal_thick': 0.4,
        'tail': [(0.12, 0.075), (0.27, 0.068), (0.42, 0.06), (0.56, 0.054), (0.69, 0.047), (0.8, 0.04)],
        # the crest: a mohawk of spiky scales over the crown, the midline ones orange-tipped (2-turnaround front)
        'crest': [(0.0, -0.37, 0.042, (0.0, -0.3, 1.0)), (0.0, -0.3, 0.058, (0.0, 0.1, 1.0)), (0.0, -0.225, 0.054, (0.0, 0.45, 1.0)),
                  (0.0, -0.155, 0.05, (0.0, 0.85, 1.0)), (0.0, -0.095, 0.05, (0.0, 1.2, 0.8)),
                  (0.05, -0.335, 0.036, (0.5, -0.1, 1.0)), (-0.05, -0.335, 0.036, (-0.5, -0.1, 1.0)),
                  (0.055, -0.265, 0.042, (0.55, 0.25, 1.0)), (-0.055, -0.265, 0.042, (-0.55, 0.25, 1.0)),
                  (0.05, -0.195, 0.038, (0.5, 0.6, 1.0)), (-0.05, -0.195, 0.038, (-0.5, 0.6, 1.0)),
                  (0.09, -0.3, 0.03, (0.8, 0.1, 0.8)), (-0.09, -0.3, 0.03, (-0.8, 0.1, 0.8))],
        'crest_w': 1.4, 'crest_thick': 0.6,
        # round 2: lifted scale tips that break the outline (1-hero): (p0, p1, outward, pointing, count, length, width, lift)
        'ruff': [
            ((0.18, -0.27, 0.57), (0.19, -0.24, 0.66), (0.85, 0.35, -0.3), (0.2, 0.55, -0.8), 5, 0.058, 0.04, 42),     # behind the cheek
            ((0.17, -0.2, 0.62), (0.19, -0.12, 0.5), (0.9, 0.3, 0.0), (0.0, 0.7, -0.7), 5, 0.055, 0.04, 40),           # down the neck's side
            ((0.165, -0.165, 0.84), (0.06, -0.1, 0.905), (0.6, 0.6, 0.55), (0.1, 0.9, -0.3), 6, 0.055, 0.04, 42),      # round to the nape
            ((0.22, -0.18, 0.44), (0.23, -0.13, 0.3), (0.8, 0.5, 0.1), (0.0, 0.5, -0.85), 5, 0.052, 0.038, 38),       # shoulders' backs
            ((0.15, -0.185, 0.24), (0.16, -0.19, 0.15), (0.3, 0.95, 0.0), (0.0, 0.4, -0.9), 4, 0.044, 0.033, 42),      # elbows
            ((0.2, 0.33, 0.4), (0.22, 0.38, 0.24), (0.6, 0.75, 0.2), (0.0, 0.6, -0.8), 6, 0.058, 0.04, 38),            # haunches
            ((0.18, 0.32, 0.16), (0.18, 0.31, 0.08), (0.2, 1.0, 0.0), (0.0, 0.45, -0.9), 3, 0.04, 0.03, 42),           # heels
        ],
    },
    'frill': {
        'root_top': (0.152, -0.18, 0.79), 'root_bot': (0.13, -0.225, 0.62),
        # spine directions (left side), top to bottom, and their lengths: fanning back and out behind the cheek
        'dirs': [(0.5, 0.42, 0.78), (0.78, 0.5, 0.36), (0.86, 0.46, -0.06), (0.7, 0.38, -0.6)],
        'lens': [0.16, 0.21, 0.21, 0.155],
        'scallop': 0.27, 'cup': 0.04, 'curl': 0.035, 'relief': 0.0018, 'spine_r': (0.0105, 0.0026), 'spine_start': 0.05,
    },
    # round 2: the smaller second frill above and behind the main one (1-hero)
    'frill2': {
        'root_top': (0.15, -0.13, 0.86), 'root_bot': (0.165, -0.16, 0.795),
        'dirs': [(0.4, 0.45, 0.8), (0.65, 0.55, 0.5), (0.8, 0.55, 0.2)],
        'lens': [0.09, 0.12, 0.11],
        'scallop': 0.27, 'cup': 0.025, 'curl': 0.02, 'relief': 0.0014, 'spine_r': (0.0078, 0.002), 'spine_start': 0.05,
    },
    'wings': {
        'parent': 'chest', 'name': 'wing', 'scallop': 0.26,
        # Nov 12 final: folded as a closed fan: the wrist and its claw the high point just behind the shoulder, the forearm along the flank down to the elbow,
        # the fingers bundled beside it (tips inside the membrane); spread: the arm raised, the hand out, the fingers fanning out and down
        'shoulder': (0.12, 0.0, 0.5), 'elbow': (0.33, 0.32, 0.35), 'wrist': (0.24, 0.06, 0.62),
        'fingers': [(0.262, 0.756, 0.424), (0.29, 0.74, 0.38), (0.31, 0.72, 0.33)],
        'attach': (0.15, 0.38, 0.38),
        'spread': {'elbow': (0.77, 0.0, 1.26), 'wrist': (1.72, 0.05, 1.56), 'fingers': [(2.72, 0.0, 1.81), (2.57, 0.35, 1.21), (2.17, 0.55, 0.81)]},
    },
    'wing': {'billow': 0.06, 'res_high': (80, 140), 'res_quick': (24, 40), 'res_low': (7, 14), 'relief': 0.0016,
             # a thick, scaled arm tapering from the shoulder (no rings), a round knuckle and a copper claw at the wrist, the
             # leading finger ending blunt (no needle), the fingers raised teal struts
             'arm_r': (0.075, 0.05, 0.042), 'lead_r': (0.03, 0.013), 'finger_r': (0.02, 0.008), 'wclaw': (0.075, 0.026),
             'wclaw_dir': (0.2, -0.85, 0.5), 'arm_rings': False, 'elbow_bulge': 0.0, 'knuckle_lo': 9, 'arm_seg_lo': 10,
             'finger_teal': True, 'clean_skin': True,
             'arm_bands': 16, 'veins': 'branch', 'vein_n': 5, 'vein_w': 0.022, 'vein_relief': 0.0011, 'glow': 0.34, 'arm_power': 3,
             'mid_lite': 0.55, 'backlit': True, 'finger_dark': 0.45,
             'wrist_bulge': 0.0, 'wrist_cap': 0.25, 'rigid_bones': True, 'knuckle': 0.95, 'shoulder_dome': True},
    'horn': {'path': [(0.15, -0.2, 0.825), (0.182, -0.194, 0.885), (0.192, -0.172, 0.94), (0.166, -0.138, 0.988)],
             'r0': 0.046, 'r_tip': 0.007, 'rings': 5, 'groove': 0.1},
    'mouth': {'z': 0.622, 'half': 0.07, 'curve': 0.016, 'curl': 0.02, 'dip': 0.004, 'width': 0.0024, 'zmin': 0.55,
              'front': ([0.0, 0.04, 0.06, 0.072], [-0.564, -0.549, -0.526, -0.496])},
    # round 2: the lower jaw's skin (below the smile, from the mouth's corners forward) rides the jaw bone
    'jaw_skin': {'y0': -0.42, 'y1': -0.46, 'depth': 0.09},
    # Nov 13: a real mouth behind lips cut along the smile (hearthwing_mouth): the fire breath shows open jaws
    'mouth_cut': {'corner_y': -0.485, 'x_max': 0.08, 'z_band': 0.035, 'back_y': -0.455, 'hinge_y': -0.44, 'jaw_z0': 0.09,
                  'fang_y': -0.552, 'tris': 1000},
    'nostril': {'dx': 0.015, 'dz': 0.008, 'r': 0.0032},
    'zone': {'head': ((0.0, -0.31, 0.75), (0.32, 0.31, 0.29), 0.52), 'muzzle': ((0.0, -0.5, 0.66), (0.11, 0.13, 0.09)),
             'face': (-0.36, 0.55, 0.86, 0.22), 'leg_top': {'F': 0.3, 'B': 0.22}, 'leg_r': 0.15, 'tail_y': 0.33, 'tail_r': 0.2},
    'cream': {
        'face_line': ([0.0, 0.045, 0.075, 0.12, 0.19, 0.24], [0.672, 0.674, 0.695, 0.7, 0.705, 0.68]), 'face_y': (-0.215, -0.235),
        'eye_patch': (1.62, 1.52, 0.075, 0.004), 'v_teal': (0.026, 0.35, 0.712),
        'bib': ([0.1, 0.22, 0.35, 0.48, 0.58, 0.66], [0.12, 0.135, 0.135, 0.12, 0.105, 0.11]), 'bib_y': (-0.22, -0.245), 'bib_top': (0.68, 0.62),
        'crisp': 0.25,
        'belly': ([-0.3, -0.15, 0.0, 0.2, 0.3, 0.42], [0.24, 0.19, 0.17, 0.16, 0.15, 0.14]),
        'paw_rim': ((0.15, 0.17, 0.055), 0.035),
    },
    # round 2: pointed leaf scales (about 1.4:1, a midrib) at about 3x the relief, overlapping so each tip casts a shadow
    'scales': {'body': 0.032, 'head': 0.02, 'snout': 0.012, 'leg': 0.024, 'paw': 0.017, 'tail': (0.028, 0.016), 'spade': 0.016,
               'band': 0.05, 'h_body': 0.019, 'h_head': 0.0105, 'contrast': 0.7, 'h_fine': 0.003, 'h_band': 0.006, 'overlap': 1.25, 'aspect': 1.4,
               'inset': 0.0008, 'leaf': 0.85, 'rib_h': 0.0012, 'cream_skip': 0.88, 'majority': 7, 'h_spade': 0.006,
               'uv_blade': 0.85},
    # the chest's chevrons: rows of leaf plates in V's down the cream chest (4-details panel 5)
    'chevron': {'centre': (0.0, -0.44, 0.37), 'radii': (0.13, 0.09, 0.17), 'rows': 5, 'angle': 48, 'seam': 0.0065, 'h': 0.008,
                'outline': False},
    # a faint warm heart in the middle of the chest
    'glow': {'centre': (0.0, -0.45, 0.37), 'radii': (0.075, 0.08, 0.09), 'heart': 1.0, 'seam': 0.45, 'warm': 1.0, 'seam_warm': 0.4,
             'seam_paint': 0.0, 'under': 0.0},
    'fleck_z': 0.4, 'spike_orange': 0.35,
    # brows (in eye radii from the eye's centre: across, up, half axes): a short thick arc above each eye
    'brows': [(-0.55, 1.3, (0.42, 0.28, 0.1)), (0.0, 1.44, (0.5, 0.28, 0.12)), (0.6, 1.33, (0.46, 0.28, 0.11))],
    # round 2: one continuous thick arched brow per eye (eye radii: across, up, half thickness), thickest in the middle
    'brow_arc': [(-0.78, 1.2, 0.05), (-0.42, 1.48, 0.08), (0.0, 1.6, 0.095), (0.42, 1.55, 0.088), (0.82, 1.36, 0.06)],
    'blush': ((0.15, -0.37, 0.66), (0.05, 0.065, 0.042)),
    'dots': [(0.048, 0.645), (0.06, 0.652), (0.054, 0.635), (0.067, 0.642), (0.072, 0.657), (0.062, 0.665)], 'dots_y': -0.56,
    'rig': {'hip': (0.0, 0.24, 0.4), 'chest': (0.0, -0.22, 0.42), 'head_r': 0.19, 'knee_back': 0.03, 'ankle_z': 0.045,
            'foot_len': 0.13, 'leg_radius': 0.1, 'stride': 0.14, 'horn_bone': ((0.0, -0.19, 0.89), (0.0, -0.15, 0.99)),
            # round 2: the jaw hinges at the mouth's corners and runs to the chin's tip
            'jaw': {'head': (0.0, -0.44, 0.63), 'tail': (0.0, -0.57, 0.6)}, 'cast_paw': 0.0, 'cast_rear': 8, 'hit_wing_open': 0.0},
    'ember': False, 'lid_teal': True,
}

FORM = HF.Form(G_YOUNG, PALETTE)
HF.export(FORM, globals())

CLIP_CALM = {
    '*': {'ear': 0.6, 'tail': 0.85},
    'ko': {'ear': 0.25, 'tail': 0.5, 'wing': 0.6},
    # Nov 13: the big folded wings stay folded at rest (a slight opening lifted them into a sail)
    'battle_idle': {'wing': 0.2}, 'idle': {'wing': 0.3}, 'idle_happy': {'wing': 0.5}, 'run': {'wing': 0.4},
    'hit_heavy': {'ear': 0.35, 'tail': 0.6},
    'win': {'ear': 0.5},
    'strike': {'ear': 0.4},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the gold iris, the big pupil, the catchlights and the upper lash line '
             'baked into the body atlas; the brows, blush, nostrils and the wide smile are baked into the body. No face sheet '
             'and no morphs: expressions in clips\' `faces` are hints only. Blinking scales the blink bones (play `blink` '
             'over any clip): each lens squashes onto the closed lid\'s lash line and sinks into the head, showing the '
             'closed lid sculpted and painted on the skin under it. The chest\'s warm heart and the tail\'s spade are in the '
             'glow map (ORM alpha); the little flame puff of the attack is a runtime effect from socket_mouth.')

REVIEW = {
    'centre': (0.0, 0.17, 0.5),
    'size': 1.62,
    'head': ((0.0, -0.36, 0.75), 0.78),
}
