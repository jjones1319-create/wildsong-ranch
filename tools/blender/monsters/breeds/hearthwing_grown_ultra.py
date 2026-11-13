"""Hearthwing, the grown form, at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (look
`hearthwing-grown`; RECIPE.md "Grown forms").

chatgpt/monsters/09-hearthwing/grown-*.png (PROMPTS.md "the GROWN form"): the same dragon fully grown, proud but kind. A
stocky, broad-chested dragon on four strong legs, a long neck curving forward and up so the head sits in front of the
chest, the young form's face (big gold eyes, a wide smile, cream jaw and cheeks) on one tapered muzzle, long ringed
copper horns sweeping back and up in a C, big orange frills behind the cheeks, large broad wings (a thick teal-scaled
arm, four orange-brown fingers, a veined membrane with an ember edge, a copper wrist claw), large orange-tipped plates
from the crown down the neck, back and tail, a long tail ending in a glowing leaf-shaped spade, copper claws, and the
chest's scales parted like a fireplace grate over a molten glow.

The shared machinery is hearthwing_form.Form; this file holds the grown form's numbers. Round 2 (Nov 8 review, "the
young dragonet's head and build stretched onto stilts"): the torso about 20% longer and lower on shorter, thicker legs
with a slight elbow bend; the neck an S forward then up; the head 15% smaller with one tapered muzzle and the eyes
turned outward; a tail as long as the torso; large diamond back plates; four-finger wings that open above the horns;
the grate's seams glowing orange with no oval outline.
Size: about 2 x Puddlepup (HEIGHT_UNITS 300). Neck: four bones (RECIPE batch 2). Tail: six bones.
Colours: CONTENT §2.2 #21, the same as the young form.
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

from lib.mesh import Part
from monsters.breeds import hearthwing_form as HF

ID = 'hearthwing-grown'
LOOK = 'hearthwing-grown-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 300

PALETTE = {'body': '#1F6F6A', 'belly': '#E9D8B4', 'accent': '#FF8A3D', 'eye': '#FFD166', 'horn': '#B87333'}
VARIANTS: dict = {}

ATLAS_STRIP = 0
BODY_TRIS = 70000
ATLAS_DENSITY = {'lo_eyes': 1.3, 'lo_fins': 0.36, 'lo_props': 0.6}   # Nov 12: the working wings are about 4x the area
UV_SMOOTH = 120                      # the scaly body unwraps smoothed into far fewer, larger islands (uv_smooth_mask)
GLOW = {'strength': 2.2, 'tint': '#FF9A40'}   # Nov 12: the grate's bloom stays orange, never cream or white     # 3b: thin seams at full glow, a moderate strength (the bloom draws the lines)
BLINK_CLOSED = (0.74, 0.04, 0.2)
MOUTH_SOCKET = (0.0, -1.47, 1.6)     # at the lips (the fire breath)
MERGE_INTO_HEAD = ('eye.L', 'eye.R')  # the jaw moves the lower jaw's skin (the strike's bite, the fire breath)
AO_FLOOR = 0.25                      # round 3: deeper crevices between the scales (never near black)
AO_SOFTEN = 1.0
MEMBRANE_AO_BODY = False             # the big folded wings leave no baked shadow on the flank (it stayed when they spread)
LITE_PROPS_TRIS = 5000               # Lite keeps the claws, horns, wing bones and frill spines whole
NORMAL_SCALE = 1.1                   # the baked scales' relief at full strength in the game's film material (default 0.6)
# the high source: the grown body is four times Puddlepup's area; 4.2 mm voxels keep it under ~1.6 M triangles, and the
# scales (3-9 cm) still span ten vertices
VOXELS = {'hi': 0.0042, 'hi_quick': 0.007, 'lo': 0.0075}

HEAD_C = (0.0, -1.12, 1.71)
HEAD_R = (0.205, 0.22, 0.195)
NOSE_C = (0.0, -1.468, 1.655)

G_GROWN = {
    'k': 2.0, 'k_face': 1.25,
    'head_c': HEAD_C, 'head_r': HEAD_R,
    # the eyes turned about 25 degrees further outward (a full eye in profile)
    'eye': {'r': 0.07, 'shape': (1.0, 1.06), 'depth': (0.62, 0.46), 'x': 0.13, 'z': 1.735, 'out': 0.002, 'fwd': 0.4,
            'iris': 0.9, 'pupil': 0.54, 'shift': (0.06, 0.04), 'rim': 0.16, 'lid_top': 0.12, 'lid_paint': 0.9, 'lid_dome': 0.007},
    'nose_c': NOSE_C, 'nose_r': (0.046, 0.02, 0.026),
    'lid': (0.08, 0.16, 0.95),
    'head_parts': [
        Part('head', 'sphere', loc=HEAD_C, radius=1.0, scale=HEAD_R),
        # one tapered muzzle flowing out of the skull (teal on top), the cream lower jaw under it
        Part('muzzle', 'tube', loc=(0.0, -1.22, 1.665), to=(0.0, -1.4, 1.627), radius=0.118, r2=0.08),
        Part('jaw', 'tube', loc=(0.0, -1.18, 1.575), to=(0.0, -1.34, 1.572), radius=0.1, r2=0.058),
        Part('nose', 'sphere', loc=NOSE_C, radius=1.0, scale=(0.046, 0.02, 0.026)),
        Part('cheek', 'sphere', loc=(0.105, -1.19, 1.61), radius=0.045, scale=(1.0, 1.15, 0.85), mirror=True),
        Part('jowl', 'sphere', loc=(0.13, -1.07, 1.61), radius=0.056, scale=(0.85, 1.0, 0.9), mirror=True),
        Part('nape', 'sphere', loc=(0.0, -1.0, 1.62), radius=0.14),
        # round 3: a thick neck base flaring into the barrel chest, then forward and up in an S under the head (from the
        # front about half as much thin neck shows)
        Part('neckbase', 'sphere', loc=(0.0, -0.95, 1.0), radius=1.0, scale=(0.29, 0.26, 0.3)),
        Part('neck1', 'capsule', loc=(0.0, -0.86, 0.92), to=(0.0, -1.08, 1.16), radius=0.235),
        Part('neck2', 'capsule', loc=(0.0, -1.08, 1.16), to=(0.0, -1.1, 1.45), radius=0.2),
    ],
    # a longer, lower torso (about 20%), the belly at about 0.35 m
    'torso_parts': [
        Part('chest', 'sphere', loc=(0.0, -0.74, 0.63), radius=0.34, scale=(1.22, 0.95, 1.38)),
        Part('body', 'capsule', loc=(0.0, -0.45, 0.64), to=(0.0, 0.19, 0.6), radius=0.33),
        Part('belly', 'sphere', loc=(0.0, -0.15, 0.47), radius=1.0, scale=(0.37, 0.48, 0.29)),
        Part('shoulder', 'sphere', loc=(0.27, -0.62, 0.68), radius=0.2, mirror=True),
        Part('haunch', 'sphere', loc=(0.22, 0.14, 0.54), radius=0.18, scale=(0.85, 1.1, 1.05), mirror=True),
        Part('rump', 'sphere', loc=(0.0, 0.26, 0.6), radius=0.22, scale=(1.0, 0.85, 0.9)),
    ],
    'legs': {'FL': (0.32, -0.6), 'FR': (-0.32, -0.6), 'BL': (0.29, 0.14), 'BR': (-0.29, 0.14)},
    # shorter, thicker legs with a slight bend (the elbow set back, the knee forward)
    'leg': {
        'paw_k': {'F': 1.0, 'B': 1.04}, 'toe_dx': (-0.136, -0.046, 0.046, 0.136),
        'toe': {'dy': 0.222, 'dyk': 0.42, 'z': 0.076, 'r': 0.068, 'scale': (0.84, 1.25, 0.92)},
        'cleft': 0.009, 'cleft_len': 0.05, 'pad_colour': 'cream_rim', 'claw_coat': 0.5,
        'lean': {'F': 0.05, 'B': -0.02}, 'top': {'F': 0.66, 'B': 0.56}, 'bottom': 0.21, 'r': {'F': 0.165, 'B': 0.165},
        'arm_dx': 0.015, 'arm_z': {'F': 0.38, 'B': 0.32}, 'arm_r': {'F': 0.2, 'B': 0.17}, 'arm_scale': (1.0, 1.05, 1.3),
        'arm_dy': {'F': 0.07, 'B': -0.035},
        'paw_dy': 0.04, 'paw_z': 0.11, 'paw_r': 0.17, 'paw_scale': (1.1, 1.0, 0.62),
        'heel_dy': 0.05, 'heel_z': 0.12, 'heel_r': 0.13,
        'claw': (0.11, 0.047, 0.42), 'claw_blunt': 'cone', 'hip_z': {'F': 0.66, 'B': 0.58},
    },
    # a tail as long as the torso, tapering, a gentle upward curl to the spade
    'tail': {'pts': [(0.0, 0.26, 0.6), (0.0, 0.49, 0.42), (0.0, 0.76, 0.33), (0.0, 1.02, 0.34), (0.0, 1.22, 0.44), (0.0, 1.34, 0.58)],
             'rad': [0.24, 0.19, 0.145, 0.11, 0.085, 0.07], 'bones': 6, 'tall': 1.2},
    # a rounded, leaf-shaped spade (never a flame), tipped up and back
    # Nov 12 round 2 (originality): the card's spade, a flat leaf / arrowhead about a quarter as thick as wide, a centre
    # ridge, a faint steady glow (never a round glowing bud)
    # Nov 12 final (originality): a short, flat, rounded leaf-spade about 1.3 x as long as wide, its broad face to the
    # side, a midrib, a teal cup where it joins; one flat orange (no glow, no spots, no hot tip)
    'spade': {'base': (0.0, 1.3, 0.52), 'tip': (0.0, 1.56, 0.94), 'width': 0.38, 'thick': 0.1, 'bulge': 0.5, 'curl': 0.0, 'taper': 1.0,
              'profile': True, 'flat': True, 'collar': 0.24, 'midrib': (0.007, 0.014), 'keep': 0.6},
    'spikes': {
        # large plates from the shoulders to the hips, biggest over the shoulders and hips; diamonds from behind
        'dorsal': [(-0.62, 0.2), (-0.48, 0.24), (-0.34, 0.25), (-0.2, 0.24), (-0.06, 0.23), (0.08, 0.24), (0.22, 0.25)],
        'dorsal_up': (0.0, 0.55, 1.0), 'dorsal_w': 1.15, 'dorsal_thick': 0.55,
        # down the back of the neck from the nape
        'neck': [(1.36, 0.11), (1.25, 0.15), (1.14, 0.17), (1.02, 0.18)],
        'neck_up': (0.0, 0.85, 0.6), 'neck_back': (0.0, 0.4, -1.0),
        # on to the spade
        'tail': [(0.06, 0.2), (0.16, 0.19), (0.26, 0.17), (0.36, 0.15), (0.46, 0.135), (0.56, 0.12), (0.66, 0.105), (0.76, 0.09),
                 (0.86, 0.075)],
        'crest': [(0.0, -1.248, 0.063, (0.0, -0.3, 1.0)), (0.0, -1.18, 0.09, (0.0, 0.1, 1.0)), (0.0, -1.111, 0.09, (0.0, 0.45, 1.0)),
                  (0.0, -1.043, 0.085, (0.0, 0.85, 1.0)), (0.0, -0.984, 0.08, (0.0, 1.2, 0.8)),
                  (0.068, -1.2, 0.058, (0.5, -0.1, 1.0)), (-0.068, -1.2, 0.058, (-0.5, -0.1, 1.0)),
                  (0.076, -1.115, 0.066, (0.55, 0.25, 1.0)), (-0.076, -1.115, 0.066, (-0.55, 0.25, 1.0)),
                  (0.072, -1.04, 0.062, (0.5, 0.6, 1.0)), (-0.072, -1.04, 0.062, (-0.5, 0.6, 1.0)),
                  (0.128, -1.15, 0.045, (0.8, 0.1, 0.8)), (-0.128, -1.15, 0.045, (-0.8, 0.1, 0.8))],
        'crest_w': 1.4, 'crest_thick': 0.6,
        # lifted scale tips that break the outline: (p0, p1, outward, pointing, count, length, width, lift)
        'ruff': [
            ((0.2, -1.13, 1.52), (0.21, -1.08, 1.63), (0.85, 0.35, -0.3), (0.2, 0.55, -0.8), 6, 0.08, 0.07, 34),         # behind the cheek
            ((0.14, -0.98, 1.42), (0.2, -0.76, 1.08), (0.7, 0.65, 0.2), (0.0, 0.45, -0.9), 8, 0.085, 0.074, 32),        # down the neck's back
            ((0.17, -1.02, 1.78), (0.06, -0.94, 1.83), (0.6, 0.6, 0.5), (0.1, 0.9, -0.3), 5, 0.075, 0.065, 34),         # round to the nape
            ((0.34, -0.55, 0.85), (0.37, -0.46, 0.6), (0.8, 0.5, 0.1), (0.0, 0.5, -0.85), 6, 0.088, 0.076, 32),         # shoulders' backs
            ((0.31, -0.5, 0.42), (0.32, -0.51, 0.28), (0.3, 0.95, 0.0), (0.0, 0.4, -0.9), 4, 0.072, 0.062, 34),         # elbows
            ((0.18, 0.49, 0.42), (0.08, 1.04, 0.35), (1.0, 0.0, 0.2), (0.0, 1.0, -0.15), 7, 0.055, 0.048, 28),          # the tail's sides
        ],
        'ruff_dark': 0.3,
    },
    'frill': {
        'root_top': (0.16, -1.052, 1.791), 'root_bot': (0.153, -1.11, 1.536),
        'dirs': [(0.5, 0.45, 0.6), (0.75, 0.5, 0.35), (0.86, 0.48, 0.05), (0.82, 0.42, -0.3), (0.62, 0.35, -0.65)],
        'lens': [0.19, 0.245, 0.26, 0.245, 0.19],
        'scallop': 0.28, 'cup': 0.05, 'curl': 0.05, 'relief': 0.0026, 'spine_r': (0.011, 0.003), 'spine_end': 0.9, 'spine_start': 0.05,
    },
    # the smaller second frill above and behind the main one, behind the horn (grown-1-hero)
    'frill2': {
        'root_top': (0.16, -0.99, 1.86), 'root_bot': (0.187, -1.027, 1.774),
        'dirs': [(0.4, 0.45, 0.8), (0.65, 0.55, 0.5), (0.8, 0.55, 0.2)],
        'lens': [0.136, 0.18, 0.16],
        'scallop': 0.27, 'cup': 0.035, 'curl': 0.03, 'relief': 0.002, 'spine_r': (0.01, 0.0028), 'spine_end': 0.9, 'spine_start': 0.05,
    },
    'wings': {
        'parent': 'chest', 'name': 'wing', 'scallop': 0.26,
        # Nov 12 final: folded as a closed fan: the wrist and its claw the high point just behind the shoulder, the forearm along the flank down to the elbow,
        # the fingers bundled beside it (tips inside the membrane); spread: the arm raised, the hand out, the fingers fanning out and down
        'shoulder': (0.22, -0.5, 0.92), 'elbow': (0.52, 0.4, 0.55), 'wrist': (0.38, -0.3, 1.03),
        'fingers': [(0.46, 1.4, 0.6), (0.5, 1.36, 0.54), (0.53, 1.32, 0.48)],
        'attach': (0.2, 0.42, 0.66),
        'spread': {'elbow': (0.87, -0.5, 1.68), 'wrist': (1.82, -0.45, 1.98), 'fingers': [(2.82, -0.5, 2.23), (2.67, -0.15, 1.63), (2.27, 0.05, 1.23)]},
    },
    'wing': {'billow': 0.07, 'res_high': (80, 140), 'res_quick': (24, 40), 'res_low': (7, 14), 'relief': 0.003,
             # a thick, scaled arm tapering from the shoulder (no rings), a round knuckle and a copper claw at the wrist, the
             # leading finger ending blunt (no needle), the fingers raised teal struts
             'arm_r': (0.13, 0.072, 0.055), 'lead_r': (0.05, 0.024), 'finger_r': (0.042, 0.016), 'wclaw': (0.14, 0.046),
             'arm_bands': 20, 'veins': 'branch', 'vein_n': 6, 'vein_w': 0.02, 'vein_relief': 0.0008, 'glow': 0.3, 'hub': 0.55,
             'arm_power': 3, 'wclaw_dir': (0.2, -0.85, 0.5), 'wrist_bulge': 0.0, 'wrist_cap': 0.25, 'rigid_bones': True,
             'mid_lite': 0.5, 'arm_rings': False, 'elbow_bulge': 0.0, 'knuckle_lo': 9, 'arm_seg_lo': 10,
             'finger_teal': True, 'clean_skin': True,
             # the card's ember edge: a glowing band about 3.5% of the membrane's depth along the scalloped trailing edge
             'ember_band': 0.035, 'ember_glow': 0.7, 'ember_paint': 0.85, 'frill_teal': 0.45, 'knuckle': 0.9, 'backlit': True, 'shoulder_dome': True},
    # longer horns (1.5x), ribbed, sweeping back and up in a C
    'horn': {'path': [(0.13, -1.04, 1.81), (0.185, -0.97, 1.88), (0.22, -0.89, 1.92), (0.235, -0.82, 1.965), (0.23, -0.79, 2.03),
                      (0.21, -0.81, 2.085)],
             'r0': 0.088, 'r_tip': 0.012, 'rings': 6, 'groove': 0.15},
    # the smile: a short curve across the muzzle's front, then back along each side of it to the mouth's corner
    'mouth': {'z': 1.603, 'half': 0.08, 'curve': 0.006, 'curl': 0.0, 'dip': 0.003, 'width': 0.0034, 'zmin': 1.48,
              'front': ([0.0, 0.04, 0.06, 0.08], [-1.475, -1.464, -1.444, -1.4]),
              'side': [(-1.435, 1.609), (-1.385, 1.604), (-1.335, 1.604)], 'side_x': 0.05},
    'jaw_skin': {'y0': -1.15, 'y1': -1.22, 'depth': 0.11},
    # Nov 13: a real mouth behind lips cut along the smile and the muzzle's sides (hearthwing_mouth)
    'mouth_cut': {'corner_y': -1.33, 'x_max': 0.1, 'z_band': 0.035, 'back_y': -1.285, 'hinge_y': -1.2, 'jaw_z0': 0.11,
                  'fang_y': -1.455, 'tris': 1000},
    'nostril': {'dx': 0.022, 'dz': 0.01, 'r': 0.0042},
    'zone': {'head': ((0.0, -1.18, 1.68), (0.32, 0.38, 0.28), 1.42), 'muzzle': ((0.0, -1.34, 1.61), (0.13, 0.15, 0.1)),
             'face': (-1.2, 1.48, 1.86, 0.25), 'leg_top': {'F': 0.5, 'B': 0.42}, 'leg_r': 0.27, 'tail_y': 0.29, 'tail_r': 0.32,
             'neck': ((0.0, -0.98, 1.18), (0.28, 0.32, 0.4))},
    'cream': {
        # teal on the muzzle's top, cream jaw and cheeks
        'face_line': ([0.0, 0.05, 0.09, 0.13, 0.18, 0.22], [1.62, 1.622, 1.63, 1.68, 1.69, 1.66]), 'face_y': (-1.06, -1.09),
        'crisp': 0.25, 'border_soft': True, 'smooth_zones': ('head', 'neck'),
        'eye_patch': (1.72, 1.6, 0.08, 0.004), 'v_teal': (0.03, 0.35, 1.655),
        # the cream throat follows the neck's front up to the chin (no teal patch on it), into the chest and the belly
        'bib': ([0.3, 0.45, 0.6, 0.75, 0.9, 1.05, 1.2, 1.45], [0.17, 0.2, 0.22, 0.22, 0.19, 0.15, 0.12, 0.11]),
        'bib_y': (-0.62, -0.68), 'bib_top': (1.0, 0.92),      # the chest only; the throat rule covers the neck
        # the neck's front, by the angle round its axis (from the chest to under the chin): cream where it faces forward
        'throat': ([(0.0, -0.78, 0.82), (0.0, -0.9, 0.98), (0.0, -1.0, 1.16), (0.0, -1.06, 1.34), (0.0, -1.1, 1.52)], (0.0, -1.0, -0.25), 0.62),
        'belly': ([-0.9, -0.6, -0.3, 0.0, 0.2, 0.45], [0.46, 0.38, 0.33, 0.33, 0.36, 0.4]),
        'paw_rim': ((0.26, 0.29, 0.09), 0.06),
    },
    'scales': {'body': 0.055, 'head': 0.028, 'snout': 0.018, 'leg': 0.04, 'paw': 0.028, 'tail': (0.05, 0.028), 'spade': 0.028,
               'band': 0.085, 'neck': 0.045, 'back': (0.085, 0.17, 0.8), 'h_body': 0.024, 'h_head': 0.014, 'h_fine': 0.005,
               'h_band': 0.01, 'overlap': 1.25, 'aspect': 1.4, 'inset': 0.0012, 'leaf': 0.85, 'rib_h': 0.002, 'cream_skip': 0.88,
               'majority': 7, 'h_spade': 0.005, 'contrast': 0.7, 'no_neck_bands': True,
               # the round-3 build's bigger lifted scales protected so much that the weighted decimate stalled and the plain
               # one left 60 cm facets on the chest: the blades keep less
               'keep_blade': (0.26, 0.4)},     # 3b: a little more for the neck's spikes (fewer blades now: no haunch rows)
    # the fireplace grate: raised plates in nested V's, molten orange seams hottest at the centre; no oval outline
    'chevron': {'centre': (0.0, -1.0, 0.64), 'radii': (0.26, 0.22, 0.38), 'rows': 7, 'angle': 50, 'seam': 0.012, 'h': 0.022,
                'plate_tint': ('#E9D8B4', 0.0), 'outline': False, 'soft': 0.2, 'edge_dark': 0.7},
    'glow': {'centre': (0.0, -1.02, 0.66), 'radii': (0.2, 0.2, 0.3), 'heart': 0.0, 'seam': 1.0, 'warm': 0.0, 'seam_warm': 1.0,
             'seam_paint': 1.0, 'under': 0.0, 'seam_hex': '#FF8A3D', 'seam_core': True},
    'fleck_z': 0.75, 'spike_orange': 0.2,
    'brows': [(-0.55, 1.3, (0.42, 0.28, 0.1)), (0.0, 1.44, (0.5, 0.28, 0.12)), (0.6, 1.33, (0.46, 0.28, 0.11))],
    'brow_arc': [(-0.78, 1.2, 0.05), (-0.42, 1.48, 0.08), (0.0, 1.6, 0.095), (0.42, 1.55, 0.088), (0.82, 1.36, 0.06)],
    'blush': ((0.15, -1.25, 1.64), (0.05, 0.07, 0.04)),
    'dots': [], 'dots_y': -1.435,
    'rig': {'hip': (0.0, 0.14, 0.62), 'chest': (0.0, -0.58, 0.76), 'head_r': 0.21, 'knee_back': 0.06, 'ankle_z': 0.09,
            'foot_len': 0.22, 'leg_radius': 0.2, 'stride': 0.28, 'horn_bone': ((0.0, -1.03, 1.85), (0.0, -0.9, 2.0)),
            'jaw': {'head': (0.0, -1.2, 1.6), 'tail': (0.0, -1.41, 1.56)}, 'cast_paw': 0.0, 'cast_rear': 8, 'hit_wing_open': 0.0,
            'neck_bones': 4,
            'neck_points': [(0.0, -0.82, 0.78), (0.0, -0.95, 1.0), (0.0, -1.07, 1.18), (0.0, -1.09, 1.34), (0.0, -1.1, 1.5)]},
    'ember': True, 'lid_teal': True,
}

FORM = HF.Form(G_GROWN, PALETTE)
HF.export(FORM, globals())

CLIP_CALM = {
    '*': {'ear': 0.55, 'tail': 0.8},
    'ko': {'ear': 0.25, 'tail': 0.5, 'wing': 0.5},
    # Nov 13: the big folded wings stay folded at rest (a slight opening lifted them into a sail)
    'battle_idle': {'wing': 0.2}, 'idle': {'wing': 0.3}, 'idle_happy': {'wing': 0.5}, 'run': {'wing': 0.4},
    'hit_heavy': {'ear': 0.35, 'tail': 0.6, 'wing': 0.7},
    'win': {'ear': 0.5},
    'strike': {'ear': 0.4},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the gold iris, the big pupil, the catchlights and the upper lash line '
             'baked into the body atlas; the brows, blush, nostrils and the smile along the muzzle are baked into the body. No '
             'face sheet and no morphs: expressions in clips\' `faces` are hints only. Blinking scales the blink bones (play '
             '`blink` over any clip): each lens squashes onto the closed lid\'s lash line and sinks into the head, showing the '
             'closed lid sculpted and painted on the skin under it. The jaw opens the lower jaw\'s skin. The chest\'s grate, '
             'the spade and the wings\' ember edges are in the glow map (ORM alpha); the fire breath is a runtime effect from '
             'socket_mouth.')

REVIEW = {
    'centre': (0.0, 0.24, 0.95),
    'size': 3.5,
    'head': ((0.0, -1.22, 1.68), 0.92),
}
