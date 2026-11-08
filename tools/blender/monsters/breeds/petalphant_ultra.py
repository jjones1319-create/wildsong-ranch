"""Petalphant at Art 2.1 Ultra (docs/ART_2_DETAIL.md; batch 2): the recipe for `tools/blender/monsters/build_ultra.py`.

A round, chubby sage-green elephant calf (chatgpt/monsters/07-petalphant/: the card, 1-hero.png and 2-turnaround.png):
  - velvety skin with no locks and no tuft: the detail is carved into the high source and baked: ring wrinkles on the
    trunk, deep rings at the knees and ankles, broad curved folds behind the shoulders and in front of the hips, fine
    soft wrinkles, folds at the throat; per-pixel velvet specks and a faint leaf-vein pattern on the pale chest; the
    only fur cards are a short ruff of soft 'hair' cards round each ear's base (round 3);
  - huge magnolia-petal ears, the trunk's flower bud (5 petals that open on the bud bones, an inner core, 5 sepals), the
    leaf sprout on the crown and the tail's three leaves are props (`petalphant_parts.py`): closed shells with rounded
    rims, thick at the root (no paper edges);
  - the trunk is skin (part of the body) on a 5-bone chain with the bud at its tip (plans/quadruped.py `trunk`);
  - pillar legs with five glossy pale toenails each (part of the body, a groove round each), a flat sole.
Not in the card but in every picture: the leaf sprout on the crown (kept: the pictures decide shapes; decided Nov 7).

Size: 1.4 × Puddlepup (the card) → HEIGHT_UNITS 210, modelled 1.4 m to the top of the crown's leaves (the ears' top at
1.37 m, the head's dome at 1.27 m), measured from 2-turnaround.png at 2.72 mm per pixel.
Palette: CONTENT §2.2 #26 (#8FB996 / #DCEFD9 / #F4A7B9 / #3B3B3B); no secret variant. Toenails and the leaves have no
CONTENT colour: the toenails take 4-details.png's swatch (a pale cream), the leaves a deeper green of the skin.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from lib import common as C
from lib import marks as MK
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, smooth, v3
from monsters.breeds import petalphant_parts as PP

ID = 'petalphant'
LOOK = 'petalphant-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 210

PALETTE = {'body': '#8FB996', 'belly': '#DCEFD9', 'accent': '#F4A7B9', 'eye': '#3B3B3B'}
VARIANTS: dict = {}

NAIL_HEX = '#F3E3C8'          # 4-details.png's toenail swatch (CONTENT has no toenail colour)
BROW_HEX = '#4B3F3A'
LASH_HEX = '#211816'
MOUTH_HEX = '#5B3A3A'

# velvet skin without locks or tuft; round 3: one short ruff of soft 'hair' cards wraps each ear's base (the sculpted
# lobes read as a caterpillar), so the atlas keeps its strip for the card tiles
CARD_LAYERS = 2
# round 3b: the default soft fur lobes; the 'hair' tiles' thin strands and highlight lines read as scratchy white glints
CARD_SHADE = 0.72                # round 3b: with the skin's own paint (below) the ruff reads sage-green (0.82 read pale)
CARD_COLOUR_FROM = 'paint'       # round 3b: the skin's paint at each root, not the atlas: the ear-root crease's AO greyed the cards
CARD_EDGE_FADE = (0.05, 0.35)    # round 3b: the cards show more face-on (the default fade washed them to sparse strands)
# round 3: the normal map's strength in the game (the folds and the fine wrinkles read at film distance)
NORMAL_SCALE = 1.0
AO_FLOOR = 0.4                   # round 3b: the closed bud's inside never bakes near black (it showed as dark slits)
# round 3: a light see-through glow on the ears' cream rim
GLOW = {'strength': 0.5, 'tint': None}
BODY_TRIS = 60000                # rounds 2-3b: a rounder belly in ko and a smooth topline (52k faceted into planes)
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_props': 1.1}     # build 1: the big ears read a little soft
# the Lite copy keeps 4.5k triangles of props (the default 2.4k would crush the ears and the bud: 15.4k at Ultra)
LITE_PROPS_TRIS = 4500


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def colours(pal: dict) -> dict:
    skin, pale, pink = pal['body'], pal['belly'], pal['accent']
    leaf = C.mix_hex(skin, '#4C9156', 0.42)
    return {
        'skin': skin,
        'skin_top': C.shade_hex(skin, 0.9, cool=0.012),
        # the creases: a deeper, cooler green (never grey or olive)
        'crease': C.mix_hex(C.shade_hex(skin, 0.7), '#3F7A66', 0.3),
        'sole': C.mix_hex(NAIL_HEX, '#D9BFA3', 0.35),          # round 2: cream sole pads (5-poses.png hit), not green
        'pale': pale,
        'face_pale': C.mix_hex(skin, pale, 0.66),
        'pink': pink,
        'pink_deep': C.mix_hex(pink, '#E5839C', 0.45),
        'pink_rim': C.mix_hex(pink, '#FFF2EE', 0.55),
        'pink_vein': C.mix_hex(pink, '#D96E8B', 0.42),
        'pink_pale': C.mix_hex(pink, '#FFF4F2', 0.35),
        'blush': C.mix_hex(pink, '#F2869A', 0.35),
        'leaf': leaf,
        'leaf_light': C.mix_hex(leaf, '#E4F2D6', 0.42),
        'leaf_dark': C.shade_hex(leaf, 0.78, cool=0.01),
        'leaf_deep': C.mix_hex(skin, '#2C6E3E', 0.72),
        'ear_rim': C.mix_hex(pink, '#FFF4EA', 0.8),
        'ear_base': C.mix_hex(C.mix_hex(skin, '#FFF6E6', 0.62), pink, 0.25),
        'ear_vein': C.mix_hex(pink, '#B9466C', 0.62),
        'petal_inside': C.mix_hex(pink, '#FFF5EF', 0.6),
        'petal_heart': '#FBEFD2',
        'nail': NAIL_HEX,
        'nail_shade': C.mix_hex(NAIL_HEX, '#C9B08E', 0.45),
        'brow': BROW_HEX,
        'chest_vein': C.mix_hex(pale, skin, 0.42),
        'speck': C.mix_hex(pale, '#FFFFFF', 0.4),
    }


# ----------------------------------------------------------------------------- measurements (2-turnaround.png, 2.72 mm/px)
HEAD_C = Vector((0.0, -0.48, 1.02))
HEAD_R = (0.265, 0.235, 0.245)
CHEEK = ((0.15, -0.55, 0.835), (0.1, 0.085, 0.088))     # rounds 2-3: sunk into the face (they stood off as balls in profile)
FOREHEAD = ((0.0, -0.575, 1.07), (0.2, 0.125, 0.15))
JAW = ((0.0, -0.588, 0.8), (0.18, 0.11, 0.1))         # round 3: wider, so the cheeks blend into a full lower face

# the trunk's centre line (x = 0): down from between the eyes, hanging, its end curled forward and up into a hook that
# holds the bud (2-turnaround side view); radius along it
TRUNK_CTRL = [(0.0, -0.6, 0.985), (0.0, -0.712, 0.885), (0.0, -0.758, 0.765), (0.0, -0.778, 0.645), (0.0, -0.795, 0.548),
              (0.0, -0.825, 0.476), (0.0, -0.874, 0.466), (0.0, -0.912, 0.522)]
TRUNK_RAD = [(0.0, 0.094), (0.14, 0.09), (0.32, 0.084), (0.52, 0.076), (0.7, 0.066), (0.84, 0.058), (1.0, 0.05)]
TRUNK_CURVE = PP.catmull(TRUNK_CTRL, 14)
TRUNK_S = PP.arc_lengths(TRUNK_CURVE)
TRUNK_LEN = float(TRUNK_S[-1])
TRUNK_SHARES = [0.0, 0.22, 0.44, 0.64, 0.9, 1.0]     # the last bone is the hook's tip: the bud's axis (55° up)
TRUNK_PTS = [tuple(map(float, q)) for q in PP.resample(TRUNK_CURVE, TRUNK_SHARES)]
TRUNK_BONES = [f'trunk.{i + 1}' for i in range(len(TRUNK_PTS) - 1)]


def trunk_radius(t):
    a, r = zip(*TRUNK_RAD)
    return np.interp(t, a, r)


# the bud's frame (the same as the bud bones': plans.quadruped.bud_petals on the last trunk bone)
BUD_TIP, BUD_PREV = v3(TRUNK_PTS[-1]), v3(TRUNK_PTS[-2])
BUD_POINT = BUD_TIP + PP.bud_frame(BUD_TIP, BUD_PREV)[0] * PP.BUD_H

# sockets: the lips under the trunk's root (the plan's default sits inside the trunk), and the bud's point on the trunk's
# last bone, where the seed and petal sneezes start (5-poses.png attack)
MOUTH_SOCKET = (0.0, -0.712, 0.79)
SOCKET_POINTS = {'socket_bud': (f'trunk.{len(TRUNK_PTS) - 1}', tuple(map(float, BUD_POINT)))}

# legs: pillar legs, the front at ±0.225 m, the hind ones a little wider under the haunches
LEGS = {'FL': (0.225, -0.33), 'FR': (-0.225, -0.33), 'BL': (0.245, 0.31), 'BR': (-0.245, 0.31)}
LEG_R = {'F': 0.124, 'B': 0.12}
FOOT_C = 0.07
FOOT_R = (0.142, 0.146, 0.085)          # the foot's ellipsoid; it dips under the ground and the carving flattens the sole
NAIL_ANG = (0.0, 50.0, -50.0)            # round 2: three taller, rounder domes across the front, skin between them
NAIL_R = (0.042, 0.03, 0.05)             # across, out, up


def nail_centres(leg: str) -> list[tuple[Vector, tuple[float, float, float], float]]:
    """(centre, radii, angle) of a foot's five toenails round the front of the foot, on the ground."""
    lx, ly = LEGS[leg]
    zc = 0.05
    rf = FOOT_R[0] * math.sqrt(max(0.0, 1.0 - ((zc - FOOT_C) / FOOT_R[2]) ** 2))
    out = []
    for a in NAIL_ANG:
        k = 1.0 if abs(a) < 60 else 0.85
        ph = math.radians(a)
        r = Vector((math.sin(ph), -math.cos(ph), 0.0))
        c = Vector((lx, ly - 0.005, zc)) + r * (rf - 0.013 * k)
        out.append((c, (NAIL_R[0] * k, NAIL_R[1] * k, NAIL_R[2] * (0.95 if k < 1 else 1.0)), a))
    return out


TAIL_PTS = [(0.0, 0.405, 0.69), (0.0, 0.468, 0.625), (0.0, 0.528, 0.528)]
TAIL_END = v3(TAIL_PTS[-1])
TAIL_DIR = PP.unit(v3(TAIL_PTS[-1]) - v3(TAIL_PTS[-2]))

CROWN = v3((0.0, -0.525, 1.243))         # the leaf sprout's root, a little under the skin of the crown


# ----------------------------------------------------------------------------- eyes
EYE_R = 0.07
EYE_SHAPE = (0.96, 1.02)
EYE_DEPTH = (0.7, 0.3)           # rounds 2-3: the lens bulges, so the eye reads round from the side too
EYE_XZ = (0.18, 0.96)


def _head_front_y(x: float, z: float) -> float:
    q = 1.0 - (x / HEAD_R[0]) ** 2 - ((z - HEAD_C.z) / HEAD_R[2]) ** 2
    return HEAD_C.y - HEAD_R[1] * math.sqrt(max(q, 0.0))


# the lens's centre a little in front of the skin (Puddlepup's sits 5 mm out), so the whole round eye shows
EYE_C = {s: Vector((EYE_XZ[0] * s, _head_front_y(EYE_XZ[0], EYE_XZ[1]) - 0.012, EYE_XZ[1])) for s in (1, -1)}


def eye_frame(s: int):
    c = EYE_C[s]
    surf_n = Vector(((c.x - HEAD_C.x) / HEAD_R[0] ** 2, (c.y - HEAD_C.y) / HEAD_R[1] ** 2, (c.z - HEAD_C.z) / HEAD_R[2] ** 2)).normalized()
    # the pictures' eyes look out of the front of the face (big and round): mostly forward, a little out
    # round 2: turned about 12° further out (side views showed the lens edge-on, a coin); the painted iris sits toward
    # the nose (eye_material), so the gaze still reads forward from the front
    # round 3: further out still (about 31° from the front): the side view showed an edge-on sliver
    look = (surf_n * 0.8 + Vector((0, -1, 0)) * 0.2).normalized()
    look = (look + Vector((0, 0, 0.03))).normalized()
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


def eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """A big round eye (4-details.png panel 2): a large black pupil, the iris CONTENT's #3B3B3B warmed toward brown and
    lighter low down, a thin dark limbal ring, white showing round it, one big catchlight up toward the key light and a
    small one low on the other side, and the dark upper lash line, thicker toward the outer corner."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    eye_hex = PALETTE['eye']
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    ix = nb.math('SUBTRACT', rx, nb.math('MULTIPLY', side, -0.12))
    iy = nb.math('ADD', ry, 0.04)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.8), nb.math('DIVIDE', iy, 0.84), 0.0))
    warm = C.mix_hex(eye_hex, '#7A5A44', 0.5)
    light = C.mix_hex(eye_hex, '#A88262', 0.62)
    iris = nb.ramp(ri, [(0.0, C.lin('#0B0909')), (0.5, C.lin('#0B0909')), (0.55, C.lin(C.shade_hex(eye_hex, 0.7))),
                        (0.68, C.lin(warm)), (0.86, C.lin(C.mix_hex(warm, eye_hex, 0.3))), (0.95, C.lin(eye_hex)),
                        (1.0, C.lin(C.shade_hex(eye_hex, 0.45))), (1.045, C.lin('#F3F0EB')), (1.6, C.lin('#F3F0EB'))])
    low = nb.math('MULTIPLY', nb.smooth(ry, -0.12, -0.62), nb.math('MULTIPLY', nb.smooth(ri, 0.56, 0.66), nb.smooth(ri, 0.98, 0.88)))
    c = nb.mix(nb.math('MULTIPLY', low, 0.7), iris, nb.rgb(C.lin(light)))
    shade = nb.math('MULTIPLY', nb.smooth(nb.vmath('LENGTH', nb.comb(rx, ry, 0.0)), 0.72, 1.0), 0.3)
    c = nb.mix(nb.math('MULTIPLY', shade, nb.smooth(ri, 1.0, 1.06)), c, nb.rgb(C.lin('#C5BDB3')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.2), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.27), 1.15), 0.0)), 0.2, 0.17)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.25), nb.math('ADD', ry, 0.28), 0.0)), 0.075, 0.058)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', rx, side), 0.2, 0.9), 0.1)
    lash = nb.smooth(nb.math('ADD', ry, outer), 0.6, 0.68)
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    # a soft lower lid line (4-details.png panel 2), not a ring: thin, fading toward the corners
    rl = nb.vmath('LENGTH', nb.comb(rx, ry, 0.0))
    lower = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(rl, 0.9, 0.97), nb.smooth(ry, -0.3, -0.6)), 0.55)
    c = nb.mix(lower, c, nb.rgb(C.lin('#6B5650')))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- body parts
def _ell(name: str, c, r, mirror: bool = False, rot=(0.0, 0.0, 0.0)) -> Part:
    return Part(name, 'sphere', loc=tuple(c), radius=1.0, scale=tuple(r), mirror=mirror, rot=rot)


def trunk_parts() -> list[Part]:
    """The trunk as a chain of short tapered tubes along the curve (the voxel union makes one smooth trunk)."""
    out = []
    # the skin ends under the sepals (its round end 2.5 cm short of the bud's base, tapering into the sepals' cup), so
    # the open flower shows its heart and core, not the trunk's tip
    s_end = TRUNK_LEN - 0.058
    keep = np.nonzero(TRUNK_S <= s_end)[0]
    curve = np.vstack([TRUNK_CURVE[keep], PP.resample(TRUNK_CURVE, [s_end / TRUNK_LEN])])
    ss = np.concatenate([TRUNK_S[keep], [s_end]])
    r = trunk_radius(ss / TRUNK_LEN)
    r = r - (r - 0.037) * smooth(s_end - 0.08, s_end, ss)
    idx = list(range(0, len(curve), 3))
    if idx[-1] != len(curve) - 1:
        idx.append(len(curve) - 1)
    for k, (a, b) in enumerate(zip(idx[:-1], idx[1:])):
        out.append(Part(f'trunk{k}', 'tube', loc=tuple(curve[a]), to=tuple(curve[b]), radius=float(r[a]), r2=float(r[b])))
    return out


def fur_clumps() -> list[Part]:
    """Soft green fur at each ear's root (over the petal's base, front and back) and down the cheek's side, as in every
    picture: tapered clumps that the voxel union turns into tufts, hiding where the petal meets the head."""
    out = []
    for s in (1, -1):
        mx = v3((s, 1, 1))
        # round 3: no lobes (they read as a caterpillar) and no cheek clump: one low smooth collar along the ear's root
        # blends the petal into the head, and the hair cards (card_params) make the soft ruff over it
        for k, (va, vb) in enumerate(((0.1, 0.4), (0.36, 0.66), (0.62, 0.94))):
            a_ = PP._bez(PP.EAR_ROOT[0], PP.EAR_ROOT[1], PP.EAR_ROOT[2], va) - v3((0.006, 0.0, 0.0))
            b_ = PP._bez(PP.EAR_ROOT[0], PP.EAR_ROOT[1], PP.EAR_ROOT[2], vb) - v3((0.006, 0.0, 0.0))
            out.append(Part(f'collar{s}_{k}', 'capsule', loc=tuple(a_ * mx), to=tuple(b_ * mx), radius=0.024))
    return out


def head_parts() -> list[Part]:
    return [
        _ell('head', HEAD_C, HEAD_R),
        _ell('forehead', *FOREHEAD),
        _ell('cheek', *CHEEK, mirror=True),
        _ell('jaw', *JAW),
        _ell('chin', (0.0, -0.66, 0.77), (0.062, 0.045, 0.036)),
        _ell('trunkroot', (0.0, -0.66, 0.92), (0.082, 0.085, 0.13)),
        Part('neck', 'capsule', loc=(0.0, -0.33, 0.7), to=(0.0, -0.45, 0.86), radius=0.21),
    ] + trunk_parts() + fur_clumps()


def leg_parts(leg: str) -> list[Part]:
    lx, ly = LEGS[leg]
    r = LEG_R[leg[0]]
    top = 0.5 if leg[0] == 'F' else 0.48
    ps = [
        Part(f'leg{leg}', 'capsule', loc=(lx, ly + 0.005, top), to=(lx, ly, 0.17), radius=r),
        _ell(f'ankle{leg}', (lx, ly - 0.003, 0.13), (r * 1.03, r * 1.04, 0.09)),
        # round 2: a soft knee (the legs read as smooth tubes): forward on the front legs, back on the hind ones
        _ell(f'knee{leg}', (lx, ly + (-0.014 if leg[0] == 'F' else 0.014), 0.28 if leg[0] == 'F' else 0.29), (r * 1.03, r * 1.07, 0.07)),
        _ell(f'foot{leg}', (lx, ly - 0.005, FOOT_C), FOOT_R),
    ]
    for k, (c, rr, a) in enumerate(nail_centres(leg)):
        ps.append(Part(f'nail{leg}{k}', 'sphere', loc=tuple(c), radius=1.0, scale=rr, rot=(0.0, 0.0, a)))
    return ps


def torso_parts() -> list[Part]:
    ps = [
        _ell('torso', (0.0, -0.03, 0.54), (0.355, 0.48, 0.32)),
        _ell('chest', (0.0, -0.28, 0.55), (0.32, 0.25, 0.3)),
        _ell('belly', (0.0, 0.02, 0.4), (0.33, 0.42, 0.2)),
        _ell('rump', (0.0, 0.265, 0.53), (0.34, 0.19, 0.3)),
        _ell('back', (0.0, 0.14, 0.6), (0.31, 0.3, 0.255)),      # round 3b: fills the notch between the back and the rump
        _ell('shoulder', (0.2, -0.3, 0.5), (0.14, 0.17, 0.2), mirror=True),
        _ell('haunch', (0.2, 0.3, 0.48), (0.16, 0.19, 0.22), mirror=True),
        Part('tailroot', 'tube', loc=TAIL_PTS[0], to=TAIL_PTS[1], radius=0.03, r2=0.021),
        Part('tail', 'tube', loc=TAIL_PTS[1], to=TAIL_PTS[2], radius=0.021, r2=0.016),
    ]
    for leg in LEGS:
        ps.extend(leg_parts(leg))
    return ps


def all_parts() -> list[Part]:
    return head_parts() + torso_parts()


# ----------------------------------------------------------------------------- lookups
def trunk_lookup(p: np.ndarray) -> dict:
    """Per point: t (share along the trunk's curve, may run under 0 at the root), d (distance to the curve), r (the
    trunk's radius there), s (arc length) and ang (round the trunk from its front: 0 front, ±π back)."""
    n = len(p)
    best = np.full(n, np.inf)
    tt = np.zeros(n)
    near = (np.abs(p[:, 0]) < 0.22) & (p[:, 1] < -0.5) & (p[:, 2] < 1.1) & (p[:, 2] > 0.36)
    idx = np.nonzero(near)[0]
    out = {'t': np.full(n, -1.0), 'd': np.full(n, 1.0), 'r': np.full(n, 0.05), 's': np.zeros(n), 'ang': np.zeros(n)}
    if len(idx) == 0:
        return out
    q = p[idx]
    bd = np.full(len(idx), np.inf)
    bs = np.zeros(len(idx))
    bfoot = np.zeros((len(idx), 3))
    btan = np.zeros((len(idx), 3))
    for i in range(len(TRUNK_CURVE) - 1):
        a, b = TRUNK_CURVE[i], TRUNK_CURVE[i + 1]
        ab = b - a
        L = float(np.linalg.norm(ab))
        u = np.clip(((q - a) @ ab) / max(L * L, 1e-12), -np.inf if i == 0 else 0.0, 1.0)
        f = a + u[:, None] * ab
        d = np.linalg.norm(q - f, axis=1)
        better = d < bd
        bd = np.where(better, d, bd)
        bs = np.where(better, TRUNK_S[i] + u * L, bs)
        bfoot[better] = f[better]
        btan[better] = ab / max(L, 1e-12)
    t = bs / TRUNK_LEN
    rel = q - bfoot
    side = v3((1.0, 0.0, 0.0))
    up = np.cross(btan, side)
    ang = np.arctan2(rel @ side, -(rel * up).sum(axis=1))
    out['t'][idx] = t
    out['d'][idx] = bd
    out['r'][idx] = trunk_radius(np.clip(t, 0, 1))
    out['s'][idx] = bs
    out['ang'][idx] = ang
    return out


def tail_lookup(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    t, _L = U.polyline_param(p, np.asarray(TAIL_PTS))
    pts = v3(TAIL_PTS)
    d = np.full(len(p), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        ab = b - a
        u = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
        d = np.minimum(d, np.linalg.norm(p - (a + u[:, None] * ab), axis=1))
    return t, d


def ear_root_dist(p: np.ndarray) -> np.ndarray:
    vv = np.linspace(0, 1, 9)
    pts = PP._bez(PP.EAR_ROOT[0], PP.EAR_ROOT[1], PP.EAR_ROOT[2], vv)
    q = p.copy()
    q[:, 0] = np.abs(q[:, 0])
    return np.min(np.linalg.norm(q[:, None, :] - pts[None], axis=2), axis=1)


def leg_masks(p: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    out = {}
    for leg, (lx, ly) in LEGS.items():
        r = np.hypot(x - lx, y - ly)
        top = 0.42 if leg[0] == 'F' else 0.4
        out[leg] = (r < 0.17 + 0.03 * smooth(0.2, 0.0, z)) & (z < top + 0.04 * np.sign(x * lx))
    return out


def nail_field(p: np.ndarray, grow: float = 1.0) -> np.ndarray:
    """The smallest normalised ellipsoid distance to any toenail (< 1 inside)."""
    best = np.full(len(p), 9.0)
    for leg, (lx, ly) in LEGS.items():
        near = np.hypot(p[:, 0] - lx, p[:, 1] - ly) < 0.22
        if not near.any():
            continue
        q = p[near]
        b = best[near]
        for c, rr, a in nail_centres(leg):
            ph = math.radians(a)
            ca, sa = math.cos(ph), math.sin(ph)
            dq = q - v3(c)
            lx_ = dq[:, 0] * ca + dq[:, 1] * sa
            ly_ = -dq[:, 0] * sa + dq[:, 1] * ca
            dd = np.sqrt((lx_ / (rr[0] * grow)) ** 2 + (ly_ / (rr[1] * grow)) ** 2 + (dq[:, 2] / (rr[2] * grow)) ** 2)
            b = np.minimum(b, dd)
        best[near] = b
    return best


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    tl = trunk_lookup(p)
    trunk = (tl['d'] < tl['r'] + 0.016) & (tl['t'] > 0.07)
    head = ((in_ellipsoid(p, (0.0, -0.53, 0.99), (0.42, 0.36, 0.37)) < 1.0) & (z > 0.68)) | trunk
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = head & ~trunk & (y < -0.55) & (z > 0.72) & (z < 1.18) & (ax < 0.3)
    legs = leg_masks(p)
    leg = np.zeros(len(p), bool)
    for m in legs.values():
        leg |= m
    leg &= ~head
    paw = leg & (z < 0.19)
    nf = nail_field(p, 1.25)
    toes = nf < 1.0
    sole = leg & (z < 0.012)
    tt, td = tail_lookup(p)
    tail = (td < 0.045) & (tt > 0.08) & ~leg
    torso = ~head & ~leg & ~tail
    ear_root = (ear_root_dist(p) < 0.11) & (z > 0.86) & ~trunk
    return {'head': head, 'trunk': trunk, 'trunk_t': tl['t'], 'trunk_s': tl['s'], 'trunk_ang': tl['ang'], 'face': face,
            'eye_d': eye_d, 'legs': legs, 'leg': leg, 'paw': paw, 'toes': toes, 'nail': nf, 'sole': sole, 'tail': tail,
            'torso': torso, 'ear_root': ear_root, 'muzzle': face & (z < 0.88)}


def ear_root_near(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(distance to the nearer ear's root curve, the curve's v there) per point; only points by the side of the head
    are measured (the rest get 1 m and v 0.5), so it stays cheap over the whole high body."""
    n = len(p)
    dist = np.ones(n)
    vv = np.full(n, 0.5)
    m = (np.abs(p[:, 0]) > 0.09) & (p[:, 2] > 0.82) & (p[:, 1] > -0.6) & (p[:, 1] < -0.12)
    if m.any():
        vs = np.linspace(0.0, 1.0, 41)
        pts = PP._bez(PP.EAR_ROOT[0], PP.EAR_ROOT[1], PP.EAR_ROOT[2], vs)
        q = p[m].copy()
        q[:, 0] = np.abs(q[:, 0])
        d = np.linalg.norm(q[:, None, :] - pts[None], axis=2)
        k = d.argmin(axis=1)
        dist[m] = d[np.arange(len(q)), k]
        vv[m] = vs[k]
    return dist, vv


def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    """The hair cards' comb (they grow only round the ear roots): out along the petal from the head, as the fan's ray
    at the nearest root point runs, drooping a little."""
    _d, v = ear_root_near(p)
    th = PP.TH_TOP + (PP.TH_BOT - PP.TH_TOP) * v
    g = np.cos(th)[:, None] * PP.EAR_OUT[None] + np.sin(th)[:, None] * PP.EAR_W[None]
    g[:, 0] *= np.where(p[:, 0] < 0, -1.0, 1.0)
    g = g + v3((0.0, 0.0, -0.1))
    return S.tangent(S.norm(g), n)


def card_params(p, n, layer: int):
    """Round 3: a short, soft ruff of 'hair' cards wrapping each ear's base on the head (1-hero.png, 4-details.png panel
    1): a dense short layer within 8 cm of the root, a longer, sparser one within 5.5 cm; none near the eyes or on the
    face. Everywhere else the skin stays card-free (NaN spacing)."""
    k = len(p)
    dr, _v = ear_root_near(p)
    eye = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    # round 3b: longer, wider, denser and standing up more (round 3's short cards read as a few thin wisps)
    # round 3b: denser and shorter, lying flatter, and short at the top of the root (they poked above the head's outline)
    reach = 0.085 if layer == 0 else 0.06
    near = (dr < reach) & (p[:, 2] > 0.87) & (eye > 0.12) & (np.abs(p[:, 0]) > 0.12)
    sp = np.where(near, 0.0085 if layer == 0 else 0.012, np.nan)
    top = smooth(0.32, 0.08, _v) * 0.5
    L = (0.046 if layer == 0 else 0.062) * (0.75 + 0.4 * smooth(reach, 0.0, dr)) * (1.0 - top)
    W = np.full(k, 0.028 if layer == 0 else 0.034)
    lift = np.full(k, math.radians(14.0 if layer == 0 else 19.0))
    return sp, L, W, lift, None


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    keep = 1.0 * z['face'] + 1.0 * (z['eye_d'] < 0.1) + 0.45 * z['trunk'] + 0.8 * z['toes'] + 0.3 * z['paw'] + 0.35 * z['ear_root']
    keep = keep + 0.5 * z['tail'] + 0.5 * (z['torso'] & (co[:, 2] < 0.45)) + 0.45 * (z['torso'] & (co[:, 2] > 0.68))
    return np.clip(keep, 0, 1)


# ----------------------------------------------------------------------------- carving (the high source)
def mouth_lines() -> list[list[tuple[float, float]]]:
    """Two small smiles in the front view (x, z), one each side of the trunk's base, curling up at the outer corner."""
    out = []
    for s in (1, -1):
        pts = []
        for k in range(15):
            t = k / 14
            x = 0.094 + 0.064 * t
            zc = 0.79 + 0.006 * t + 0.03 * t ** 2.4
            pts.append((x * s, zc))
        out.append(pts)
    return out


def mouth_groove(co: np.ndarray, z: dict) -> np.ndarray:
    x, y, zz = co[:, 0], co[:, 1], co[:, 2]
    d = np.full(len(co), 1.0)
    for pts in mouth_lines():
        d = np.minimum(d, S.polyline_dist(x, zz, pts))
    front = smooth(-0.6, -0.65, y) * (~z['trunk']) * (zz > 0.74) * (zz < 0.86)
    return np.exp(-(d / 0.0024) ** 2) * front


def closed_lid(co: np.ndarray):
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
        th = 0.0023 + 0.0017 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def wrinkles(co: np.ndarray, z: dict) -> dict[str, np.ndarray]:
    """The skin's creases, 0..1 each: rings round the trunk, deep rings at the knees and ankles (faint ones between),
    curved folds behind the shoulders and in front of the hips, long creases on the flanks, soft folds at the throat."""
    x, y, zz = co[:, 0], co[:, 1], co[:, 2]
    n = len(co)
    # trunk rings: every 2.1 cm, a little wavy, strongest on the trunk's front and sides
    ring_k = 0.021
    ph = z['trunk_s'] / ring_k + 0.16 * np.sin(z['trunk_ang'] * 2.0 + z['trunk_s'] * 31.0)
    fr = ph % 1.0
    dist = np.minimum(fr, 1 - fr) * ring_k
    face_w = 0.55 + 0.45 * np.cos(np.clip(z['trunk_ang'], -np.pi, np.pi)) ** 2
    rings = np.exp(-(dist / 0.0021) ** 2) * z['trunk'] * smooth(0.06, 0.16, z['trunk_t']) * smooth(1.0, 0.9, z['trunk_t']) * face_w
    # round 2 (review: the even crackle network read as cracked glaze or reptile hide): long soft folds instead.
    # The legs: three or four deep wavy rings at each knee and ankle, faint ones between
    legc = np.zeros(n)
    for leg, (lx, ly) in LEGS.items():
        m = z['legs'][leg] & ~z['toes']
        if not m.any():
            continue
        az = np.arctan2(x[m] - lx, -(y[m] - ly))
        zm = zz[m]
        kz = 0.28 if leg[0] == 'F' else 0.29
        rings_at = [kz - 0.036, kz - 0.012, kz + 0.012, kz + 0.036, 0.088, 0.108, 0.128]
        acc = np.zeros(int(m.sum()))
        for j, zr in enumerate(rings_at):
            zc = zr + 0.006 * np.sin(az * 2.0 + j * 1.7 + lx * 9.0) + 0.003 * np.sin(az * 5.0 + j)
            strength = 0.75 + 0.25 * np.sin(az * 3.0 + j * 2.3)
            acc = np.maximum(acc, np.exp(-((zm - zc) / 0.0032) ** 2) * strength)
        k = 0.03
        ph = zm / k + 0.3 * np.sin(az * 2.0 + zm * 9.0)
        fr = ph % 1.0
        faint = np.exp(-((np.minimum(fr, 1 - fr) * k) / 0.0022) ** 2) * 0.25 * smooth(0.04, 0.06, zm)
        legc[m] = np.maximum(acc, faint) * smooth(0.012, 0.03, zm)
    # the body (round 3): two broad, soft, clearly curved folds behind each shoulder and in front of each hip (round 2's
    # thin straight lines read as long dark vertical lines), no flank lines
    side = smooth(0.17, 0.24, np.abs(x)) * z['torso']
    body = np.zeros(n)
    for y0, c in ((-0.16, 1.3), (-0.11, 1.1)):
        yc = y0 + c * (zz - 0.5) ** 2
        body = np.maximum(body, np.exp(-((y - yc) / 0.0075) ** 2) * smooth(0.28, 0.38, zz) * smooth(0.72, 0.6, zz))
    for y0, c in ((0.12, -1.3), (0.165, -1.1)):
        yc = y0 + c * (zz - 0.48) ** 2
        body = np.maximum(body, np.exp(-((y - yc) / 0.0075) ** 2) * smooth(0.26, 0.36, zz) * smooth(0.7, 0.58, zz) * 0.9)
    net = body * side * (1.0 - 0.5 * pale_mask(co, z))
    # fine soft wrinkles over the coat: short, broken, wavy lines that read at film distance (normal map only)
    coat = (z['torso'] | z['leg'] | (z['head'] & ~z['face'] & ~z['trunk'])) & ~z['toes']
    ph = (y * 0.8 + zz * 0.6) / 0.013 + 1.4 * _noise(co, 9.0, 2.0)
    fr = ph % 1.0
    brk = smooth(-0.1, 0.45, _noise(co, 17.0, 5.0))
    fine = np.exp(-((np.minimum(fr, 1 - fr) * 0.013) / 0.0016) ** 2) * brk * coat * (1.0 - 0.6 * pale_mask(co, z))
    # the throat: three soft folds under the chin
    thr = (y < -0.36) & (zz > 0.6) & (zz < 0.8) & (np.abs(x) < 0.26) & ~z['trunk'] & ~z['face']
    ph = (zz - 0.62 + 0.25 * x * x) / 0.045
    fr = ph % 1.0
    folds = np.exp(-((np.minimum(fr, 1 - fr) * 0.045) / 0.005) ** 2) * thr * smooth(0.26, 0.12, np.abs(x))
    return {'rings': rings, 'legc': legc, 'net': net, 'folds': folds, 'fine': fine}


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    z = zones(co, vn)
    w = wrinkles(co, z)
    groove = mouth_groove(co, z)
    lip = np.exp(-((z['nail'] - 1.0) / 0.07) ** 2) * (z['nail'] < 1.6)
    bulge, lash = closed_lid(co)
    disp = (-0.0014 * w['rings'] - 0.0022 * w['legc'] - 0.0026 * w['net'] - 0.0022 * w['folds'] - 0.0004 * w['fine'] - 0.0022 * groove
            - 0.0016 * lip + 0.0032 * bulge - 0.0011 * lash)
    new = co + vn * disp[:, None]
    new[:, 2] = np.maximum(new[:, 2], 0.0)          # the flat soles
    S.set_positions(ob, new)
    crease = np.clip(np.maximum.reduce([w['rings'], w['legc'], w['net'] * 0.45, w['folds'], lip * 0.8, w['fine'] * 0.12]), 0, 1)
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'crease', crease)
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)


def carve_low(ob: bpy.types.Object) -> None:
    """The low body: only the flat soles (the creases are the high source's, baked into the normal map)."""
    co, _ = S.mesh_arrays(ob)
    co[:, 2] = np.maximum(co[:, 2], 0.0)
    S.set_positions(ob, co)


# ----------------------------------------------------------------------------- paint masks
def pale_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """0 skin … 1 pale belly green: the chest bib from under the chin down between the front legs, the belly and the
    insides of the thighs (2-turnaround front and side); the lower face is lighter too (face_mask)."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    bib = ell_soft(p, (0.0, -0.47, 0.5), (0.27, 0.2, 0.3), 0.35)
    throat = ell_soft(p, (0.0, -0.5, 0.72), (0.2, 0.16, 0.1), 0.4)
    zb = np.interp(y, [-0.55, -0.3, 0.0, 0.3, 0.5], [0.42, 0.34, 0.33, 0.33, 0.36])
    belly = smooth(zb + 0.03, zb - 0.04, zz) * z['torso']
    inner = np.zeros(len(p))
    for leg, (lx, ly) in LEGS.items():
        inner = np.maximum(inner, ell_soft(p, (lx * 0.55, ly, 0.33), (0.1, 0.12, 0.12), 0.5))
    m = np.maximum.reduce([bib * smooth(0.3, 0.2, ax) * (~z['leg'] | (zz > 0.3)), throat, belly, inner * 0.8])
    m = m * (~z['trunk']) * (~z['tail'])
    return np.clip(m, 0, 1)


def face_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """The lighter lower face: the cheeks round and under the eyes, the mouth and the chin (not the trunk)."""
    m = np.zeros(len(p))
    for s in (1, -1):
        m = np.maximum(m, ell_soft(p, (0.17 * s, -0.64, 0.835), (0.13, 0.1, 0.1), 0.5))
        m = np.maximum(m, ell_soft(p, (0.15 * s, -0.66, 0.95), (0.08, 0.06, 0.06), 0.6) * 0.7)
    m = np.maximum(m, ell_soft(p, (0.0, -0.64, 0.76), (0.14, 0.09, 0.07), 0.5))
    return np.clip(m * (~z['trunk']), 0, 1)


def nail_mask(z: dict) -> np.ndarray:
    return smooth(1.12, 0.98, z['nail'])


def body_colour(p: np.ndarray, z: dict, pal: dict, crease: np.ndarray | None = None) -> np.ndarray:
    col = colours(pal)
    zz = p[:, 2]
    rgb = np.tile(lin(col['skin']), (len(p), 1))
    top = smooth(0.62, 0.86, zz) * z['torso'] * 0.7 + smooth(1.12, 1.24, zz) * z['head'] * 0.4
    rgb = rgb * (1 - top[:, None]) + lin(col['skin_top'])[None] * top[:, None]
    fm = face_mask(p, z) * 0.85
    rgb = rgb * (1 - fm[:, None]) + lin(col['face_pale'])[None] * fm[:, None]
    pm = pale_mask(p, z)
    rgb = rgb * (1 - pm[:, None]) + lin(col['pale'])[None] * pm[:, None]
    if crease is not None:
        k = (np.clip(crease, 0, 1) * 0.55)[:, None]
        rgb = rgb * (1 - k) + lin(col['crease'])[None] * k
    sole = smooth(0.016, 0.005, zz) * z['leg']
    rgb = rgb * (1 - sole[:, None]) + lin(col['sole'])[None] * sole[:, None]
    nm = nail_mask(z)
    nail = lin(col['nail'])[None]
    shade_n = smooth(0.06, 0.0, zz)[:, None] * 0.35
    nail_c = nail * (1 - shade_n) + lin(col['nail_shade'])[None] * shade_n
    rgb = rgb * (1 - nm[:, None]) + nail_c * nm[:, None]
    return rgb


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    z = zones(co, vn)
    return body_colour(co, z, PALETTE)


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    root = S.attr_array(ob, 'root').astype(np.float64)
    z = zones(root)
    crease = S.attr_array(ob, 'crease').astype(np.float64) if 'crease' in ob.data.attributes else np.zeros(len(root))
    rgb = body_colour(root, z, pal, crease)
    nm = nail_mask(z)
    pm = pale_mask(root, z)
    # round 3: rougher velvet, no clearcoat (the lit tops washed out to pale mint in the game)
    rough = 0.8 + 0.04 * pm + 0.06 * crease
    coat = np.full(len(root), 0.0)
    rough = rough * (1 - nm) + 0.24 * nm
    coat = coat * (1 - nm) + 0.85 * nm
    mouth = S.attr_array(ob, 'mouth').astype(np.float64)
    rough = rough * (1 - mouth) + 0.45 * mouth
    return {'paint': rgb, 'rough': np.stack([np.ones(len(root)), rough, coat], axis=1)}


# ----------------------------------------------------------------------------- props: ears, bud, leaves
def _obj(name: str, verts, quads, attrs: dict, part: float, side: float, pid: float) -> bpy.types.Object:
    n = len(verts)
    full = {'part': np.full(n, part), 'side': np.full(n, side), 'pid': np.full(n, pid)}
    for k in ('pu', 'pv', 'pface', 'prim'):
        full[k] = attrs[k]
    full['vein'] = attrs.get('vein', np.zeros(n))
    ob = S.sheet_object(name, verts, quads.tolist(), full)
    if name.startswith('lo_'):
        # the shell's own unwrap (inner face, outer face, rim: three fold-free islands); build_ultra keeps it (own_uv)
        # and only scales it to the common texel density and packs it (smart-project left shared texels at thin tips)
        me = ob.data
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', np.asarray(attrs['_quv'], np.float32).ravel())
        ob['own_uv'] = True
    return ob


def head_leaves() -> list[dict]:
    """The crown's sprout: three upright leaves and four lower ones fanning out, their tips curling out (every picture)."""
    out = []
    # round 3: a rosette that reads from the front as 5-7 leaves (the low ones hid behind the crown)
    for az, el, ln, wd, curl in ((90, 76, 0.17, 0.076, -0.3), (210, 72, 0.16, 0.072, -0.35), (330, 72, 0.16, 0.072, -0.35),
                                 (30, 46, 0.135, 0.064, -0.55), (150, 44, 0.13, 0.062, -0.55), (210 + 20, 44, 0.13, 0.062, -0.55),
                                 (330 - 20, 46, 0.135, 0.064, -0.55)):
        a, e = math.radians(az), math.radians(el)
        along = v3((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        face = v3((-math.sin(a) * math.sin(e), math.cos(a) * math.sin(e), math.cos(e)))
        base = CROWN + along * 0.008
        out.append({'base': base, 'along': along, 'face': face, 'length': ln, 'width': wd, 'curl': curl, 'twist': 0.15})
    return out


def tail_leaves() -> list[dict]:
    """The tail's tuft: three leaves round the tail's tip, leaning out of its line (2-turnaround side and back)."""
    t = TAIL_DIR
    q1 = PP.unit(v3((0.0, 0.0, 1.0)) - t * t[2])
    q2 = PP.unit(np.cross(t, q1))
    out = []
    for k, (psi, ln) in enumerate(((0.0, 0.2), (125.0, 0.215), (235.0, 0.215))):
        ps = math.radians(psi)
        radial = math.cos(ps) * q1 + math.sin(ps) * q2
        lean = math.radians(52.0 if k == 0 else 46.0)
        along = math.cos(lean) * t + math.sin(lean) * radial
        # round 2: broad flat ovals turned half toward the side and half toward the back, so they read from both
        # (they read as thin blades: a grass blade from the side, a peeled banana from behind)
        vref = v3((0.75 if k < 2 else -0.75, 0.62, 0.12))
        face = PP.unit(vref - along * (vref @ along))
        out.append({'base': TAIL_END + t * 0.004, 'along': along, 'face': face, 'length': ln, 'width': 0.128, 'curl': -0.12, 'twist': 0.0,
                    'fold': 0.12})
    return out


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for s in (1, -1):
        v, q, a = PP.ear_arrays(s, high, quick)
        out.append(_obj(f'{tag}_ear{"L" if s > 0 else "R"}', v, q, a, PP.PART_EAR, float(s), 0.0))
    for i in range(PP.BUD_PETALS):
        v, q, a = PP.petal_arrays(BUD_TIP, BUD_PREV, i, high, quick)
        out.append(_obj(f'{tag}_petal{i}', v, q, a, PP.PART_PETAL, 0.0, float(i)))
    for k in range(3):
        v, q, a = PP.core_arrays(BUD_TIP, BUD_PREV, k, high, quick)
        out.append(_obj(f'{tag}_core{k}', v, q, a, PP.PART_CORE, 0.0, float(k)))
    v, q, a = PP.heart_arrays(BUD_TIP, BUD_PREV, high, quick)
    out.append(_obj(f'{tag}_heart', v, q, a, PP.PART_HEART, 0.0, 0.0))
    for k in range(PP.BUD_PETALS):
        v, q, a = PP.sepal_arrays(BUD_TIP, BUD_PREV, k, high, quick)
        out.append(_obj(f'{tag}_sepal{k}', v, q, a, PP.PART_SEPAL, 0.0, float(k)))
    for k, lf in enumerate(head_leaves()):
        v, q, a = PP.leaf_arrays(lf['base'], lf['along'], lf['face'], lf['length'], lf['width'], high, quick, curl=lf['curl'], twist=lf['twist'])
        out.append(_obj(f'{tag}_leaf{k}', v, q, a, PP.PART_LEAF, 0.0, float(k)))
    for k, lf in enumerate(tail_leaves()):
        v, q, a = PP.leaf_arrays(lf['base'], lf['along'], lf['face'], lf['length'], lf['width'], high, quick, curl=lf['curl'],
                                 twist=lf['twist'], thick=0.0032, fold=lf.get('fold', 0.3))
        out.append(_obj(f'{tag}_tailleaf{k}', v, q, a, PP.PART_TAIL_LEAF, 0.0, float(k)))
    return out


def _noise(p: np.ndarray, f: float, seed: float) -> np.ndarray:
    return (np.sin(p @ v3((1.7, 2.3, 1.1)) * f + seed) * np.sin(p @ v3((-2.1, 0.9, 1.9)) * f * 1.3 + seed * 2.1)
            + 0.5 * np.sin(p @ v3((0.7, -1.6, 2.6)) * f * 2.1 + seed * 3.7))


def prop_arrays(ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    """Per vertex of a prop: the ears pink with a green root (further up the back), deeper pink toward the root of the
    pink, fine darker veins, a pale translucent-looking rim; the bud's petals pink, paler at the base and inside, a
    blush toward the tips; the core paler still; the sepals and leaves a deeper leaf green with a light midrib and edge."""
    col = colours(pal)
    A = {k: S.attr_array(ob, k).astype(np.float64) for k in ('part', 'pu', 'pv', 'pface', 'prim', 'vein', 'side')}
    co, _ = S.mesh_arrays(ob)
    n = len(co)
    part, u, v, face, rim, vein = A['part'], A['pu'], A['pv'], A['pface'], A['prim'], A['vein']
    rgb = np.zeros((n, 3))
    rough = np.full(n, 0.5)
    coat = np.full(n, 0.1)
    mottle = _noise(co, 55.0, 1.0) * 0.5
    ear = np.abs(part - PP.PART_EAR) < 0.1
    if ear.any():
        uu, ff, ve = u[ear], face[ear], vein[ear]
        reach = PP.ear_reach(PP.TH_TOP + (PP.TH_BOT - PP.TH_TOP) * v[ear])
        um = uu * reach                       # metres from the root
        dist_rim = (1.0 - uu) * reach         # metres from the rim
        # round 2: the green root feathers into the pink along the veins over about 5 cm (no hard sawtooth): a short
        # collar on the inner face (the fur covers the root), a third of the way up the back (2-turnaround back view)
        # round 3b: a wide, smooth fade (about 9 cm) with no corner, feathered along the veins, through a pale cream-green
        # petal base: the narrow sage/pink edge broke into ETC1S blocks with a peach fringe in the game
        G = np.where(ff > 0, 0.04, 0.17)
        capu = np.where(ff > 0, 0.1, 0.34)
        t = np.log(np.exp((um - G) / 0.09 * 3.0) + np.exp((uu - capu) / 0.12 * 3.0)) / 3.0
        t = t - 0.45 * ve * smooth(-0.2, 0.8, t)
        green = 1.0 - smooth(0.0, 1.0, t)
        pale_base = (smooth(-0.1, 0.45, t) * smooth(1.25, 0.55, t) * 0.55)[:, None]
        base = lin(col['pink'])[None] * np.ones((len(uu), 1))
        deep = smooth(G, G + 0.1, um) * smooth(0.85, 0.35, uu) * 0.45
        base = base * (1 - deep[:, None]) + lin(col['pink_deep'])[None] * deep[:, None]
        base = base * (1.0 + 0.035 * mottle[ear])[:, None]
        # fine crisp veins in a deeper pink, forking toward the rim
        vk = (ve * smooth(G + 0.01, G + 0.07, um) * 0.92)[:, None]
        base = base * (1 - vk) + lin(col['ear_vein'])[None] * vk
        # lighter toward the rim, then a pale cream rim about 2 cm wide (and the rounded edge itself)
        lite = (smooth(0.55, 0.95, uu) * 0.22)[:, None]
        base = base * (1 - lite) + lin(col['pink_rim'])[None] * lite
        band = np.clip(smooth(0.03, 0.012, dist_rim) * 0.85 + rim[ear] * 0.35, 0, 0.9)[:, None]
        base = base * (1 - band) + lin(col['ear_rim'])[None] * band
        base = base * (1 - pale_base) + lin(col['ear_base'])[None] * pale_base
        skin = lin(col['skin'])[None] * np.ones((len(uu), 1))
        rgb[ear] = base * (1 - green[:, None]) + skin * green[:, None]
        rough[ear] = 0.42 + 0.12 * smooth(0.5, 1.0, uu) + 0.15 * green
        coat[ear] = 0.12 * (1 - green)
    pet = (np.abs(part - PP.PART_PETAL) < 0.1) | (np.abs(part - PP.PART_CORE) < 0.1)
    if pet.any():
        uu, ff = u[pet], face[pet]
        core = np.abs(part[pet] - PP.PART_CORE) < 0.1
        base = np.where(core[:, None], lin(col['pink_pale'])[None], lin(col['pink'])[None]) * np.ones((len(uu), 1))
        # round 2: the open flower's inside is pale pink fading to cream at the heart (it read as a dark mauve well)
        inside = smooth(0.2, -0.6, ff) * smooth(0.82, 0.62, uu)        # round 3b: deep pink inside near the point
        base = base * (1 - (inside * 0.75)[:, None]) + lin(col['petal_inside'])[None] * (inside * 0.75)[:, None]
        foot = (smooth(0.35, 0.0, uu) * (0.35 + 0.55 * inside))[:, None]
        base = base * (1 - foot) + lin(col['petal_heart'])[None] * foot
        blush = (smooth(0.45, 0.95, uu) * 0.35)[:, None]
        base = base * (1 - blush) + lin(col['pink_deep'])[None] * blush
        vk = (np.exp(-((((v[pet] * 9.0) % 1.0) - 0.5) / 0.1) ** 2) * smooth(0.1, 0.4, uu) * 0.18)[:, None]
        base = base * (1 - vk) + lin(col['pink_vein'])[None] * vk
        # each petal deeper pink down its middle and paler along its edges, so the overlapping petals read one by one
        across = np.abs(v[pet] - 0.5) * 2.0
        mid = ((1 - smooth(0.0, 0.7, across)) * smooth(0.15, 0.4, uu) * 0.3 * (ff > 0))[:, None]
        base = base * (1 - mid) + lin(col['pink_deep'])[None] * mid
        edge = np.clip(rim[pet] * 0.5 + smooth(0.6, 1.0, across) * 0.45, 0, 0.75)[:, None]
        base = base * (1 - edge) + lin(col['pink_rim'])[None] * edge
        rgb[pet] = base
        rough[pet] = 0.4
        coat[pet] = 0.18
    heart = np.abs(part - PP.PART_HEART) < 0.1
    if heart.any():
        uu = u[heart]
        c0 = lin(C.mix_hex('#F2D45E', col['leaf_light'], 0.15))[None]
        c1 = lin(col['leaf_light'])[None]
        k = smooth(0.3, 1.0, uu)[:, None]
        dots = (0.5 + 0.5 * np.sin(co[heart] @ v3((900.0, 700.0, 800.0))))[:, None] * 0.25
        rgb[heart] = (c0 * (1 - k) + c1 * k) * (1.0 - dots * (1 - k))
        rough[heart] = 0.6
        coat[heart] = 0.0
    leafy = (np.abs(part - PP.PART_SEPAL) < 0.1) | (np.abs(part - PP.PART_LEAF) < 0.1) | (np.abs(part - PP.PART_TAIL_LEAF) < 0.1)
    if leafy.any():
        uu, ff = u[leafy], face[leafy]
        tailk = (np.abs(part[leafy] - PP.PART_TAIL_LEAF) < 0.1)[:, None]
        base = np.where(tailk, lin(col['leaf_deep'])[None], lin(col['leaf'])[None]) * np.ones((len(uu), 1))
        under = smooth(0.2, -0.6, ff)[:, None] * np.where(tailk, 0.18, 0.35)
        base = base * (1 - under) + lin(col['leaf_light'])[None] * under
        dark = smooth(0.3, 0.0, uu)[:, None] * 0.45
        base = base * (1 - dark) + lin(col['leaf_dark'])[None] * dark
        mid = (vein[leafy] * np.where(np.abs(part[leafy] - PP.PART_TAIL_LEAF) < 0.1, 0.75, 0.5))[:, None]
        base = base * (1 - mid) + lin(col['leaf_light'])[None] * mid
        edge = (rim[leafy] * 0.55 + smooth(0.8, 1.0, uu) * 0.25)[:, None]
        base = base * (1 - np.clip(edge, 0, 0.7)) + lin(col['leaf_light'])[None] * np.clip(edge, 0, 0.7)
        base = base * (1.0 + 0.05 * mottle[leafy])[:, None]
        rgb[leafy] = base
        rough[leafy] = 0.5
        coat[leafy] = 0.12
    return rgb, np.stack([np.ones(n), rough, coat], axis=1)


def rim_glow(ob: bpy.types.Object) -> np.ndarray:
    """Round 3: the ears' cream rim (about 2 cm) glows a little, as light through a petal's edge; nothing else glows."""
    part = S.attr_array(ob, 'part').astype(np.float64)
    u = S.attr_array(ob, 'pu').astype(np.float64)
    v = S.attr_array(ob, 'pv').astype(np.float64)
    rim = S.attr_array(ob, 'prim').astype(np.float64)
    reach = PP.ear_reach(PP.TH_TOP + (PP.TH_BOT - PP.TH_TOP) * v)
    band = np.clip(smooth(0.03, 0.01, (1.0 - u) * reach) + 0.5 * rim * smooth(0.5, 0.9, u), 0, 1)
    return np.where(np.abs(part - PP.PART_EAR) < 0.1, 0.45 * band, 0.0)


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), paint_arrays(ob, var)['paint'])
    for ob in props:
        rgb, rc = prop_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        S.add_attr(ob, 'glow', rim_glow(ob))
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), prop_arrays(ob, var)[0])


# ----------------------------------------------------------------------------- per-pixel marks
BROWS = [(0.122, 1.116, 0.0045), (0.148, 1.132, 0.0065), (0.178, 1.137, 0.0068), (0.206, 1.128, 0.0058), (0.228, 1.112, 0.004)]
BLUSH = ((0.215, -0.6, 0.85), (0.09, 0.09, 0.065))


def _snap(bvh, p) -> tuple[float, float, float]:
    hit = bvh.find_nearest(Vector(tuple(map(float, p))))
    return tuple(hit[0]) if hit[0] is not None else tuple(map(float, p))


def make_marks(hi_body: bpy.types.Object):
    """Positions snapped onto the high body: the brows (short dark arcs), three lash flicks at each eye's outer corner,
    and the pale chest's faint leaf veins (a midrib from the throat with paired side veins)."""
    bvh = BVHTree.FromObject(hi_body, bpy.context.evaluated_depsgraph_get())
    brows, flicks, veins = [], [], []
    for s in (1, -1):
        for x, zc, r in BROWS:
            y = _head_front_y(x, zc)
            brows.append([list(_snap(bvh, (x * s, y, zc))), r])
        c, xax, yax, look = eye_frame(s)
        for k, (ang, ln) in enumerate(((58.0, 0.016), (40.0, 0.018), (22.0, 0.015))):
            a = math.radians(ang)
            dirv = xax * (s * math.cos(a)) + yax * math.sin(a)
            p0 = c + dirv * (EYE_R * 1.02)
            p1 = c + dirv * (EYE_R * 1.02 + ln) + yax * 0.004
            flicks.append([list(_snap(bvh, p0)), list(_snap(bvh, p1))])
    # the chest's leaf veins: a midrib down the bib, side veins angling down and out (rays cast forward from inside the
    # chest, so a point never lands on the trunk hanging in front of it)
    def chest(x: float, zc: float):
        hit = bvh.ray_cast(Vector((x, -0.22, zc)), Vector((0.0, -1.0, 0.0)), 0.6)
        return tuple(hit[0]) if hit[0] is not None else None

    mid = [chest(0.0, zc) for zc in np.linspace(0.66, 0.3, 8)]
    for a, b in zip(mid[:-1], mid[1:]):
        if a and b:
            veins.append([list(a), list(b)])
    for zc in (0.6, 0.51, 0.42, 0.34):
        for s in (1, -1):
            pts = [chest(s * (0.012 + 0.05 * k), zc - 0.035 * k - 0.006 * k * k) for k in range(4)]
            for a, b in zip(pts[:-1], pts[1:]):
                if a and b:
                    veins.append([list(a), list(b)])
    return {'brows': brows, 'flicks': flicks, 'veins': veins}


def _ell_node(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the painted attribute, then per pixel: a soft velvet mottle and fine pale specks, the chest's leaf
    veins, the blush, the brows, the lash flicks, the smile, the closed lids and their lash line."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 0.5)
    c = nb.attribute(attr).outputs['Color']
    # velvet: a slow mottle (±4%) and fine pale specks (4-details.png panel 6)
    mot = nb.noise(pos, 22.0, 3.0, 0.55)
    c = nb.mix(1.0, c, nb.comb(*(nb.math('ADD', 0.96, nb.math('MULTIPLY', mot, 0.08)),) * 3), blend='MULTIPLY')
    vor = nb.voronoi(pos, 85.0)
    speck = nb.math('MULTIPLY', nb.smooth(vor, 0.17, 0.1), 0.34)
    c = nb.mix(speck, c, nb.rgb(C.lin(col['speck'])))
    marks = marks or {}
    vl = [MK.line(nb, pos, a, b, 0.0016, 0.5) for a, b in marks.get('veins', [])]
    if vl:
        c = nb.mix(nb.math('MULTIPLY', MK.union(nb, vl), 0.55), c, nb.rgb(C.lin(col['chest_vein'])))
    blush = None
    for s in (1, -1):
        bc, br = BLUSH
        e = _ell_node(nb, pos, (bc[0] * s, bc[1], bc[2]), br, 0.95)
        blush = e if blush is None else nb.math('MAXIMUM', blush, e)
    c = nb.mix(nb.math('MULTIPLY', blush, 0.62), c, nb.rgb(C.lin(col['blush'])))
    br = marks.get('brows', [])
    bl = [MK.line(nb, pos, a[0], b[0], 0.5 * (a[1] + b[1]), 0.45) for a, b in zip(br[:-1], br[1:]) if (a[0][0] > 0) == (b[0][0] > 0)]
    if bl:
        c = nb.mix(MK.union(nb, bl), c, nb.rgb(C.lin(col['brow'])))
    fl = [MK.line(nb, pos, a, b, 0.0017, 0.4) for a, b in marks.get('flicks', [])]
    if fl:
        c = nb.mix(MK.union(nb, fl), c, nb.rgb(C.lin(LASH_HEX)))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(MOUTH_HEX)))
    lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
    c = nb.mix(nb.math('MULTIPLY', lid, 0.18), c, nb.rgb((0.0, 0.0, 0.0)))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the rig
def rig_p() -> dict:
    eb, ed, el = PP.ear_bone(1)
    return {
        'hip': (0.0, 0.27, 0.6),
        'chest': (0.0, -0.3, 0.62),
        'head_c': tuple(HEAD_C),
        'head_r': 0.245,
        'ear_base': tuple(map(float, eb)),
        'ear_dir': tuple(map(float, ed)),
        'ear_len': el,
        'tail_base': TAIL_PTS[0],
        'tail_dir': tuple(map(float, PP.unit(v3(TAIL_PTS[-1]) - v3(TAIL_PTS[0])))),
        'tail_len': float(np.linalg.norm(v3(TAIL_PTS[-1]) - v3(TAIL_PTS[0]))),
        'tail_bones': 2,
        'tail_points': TAIL_PTS,
        'legs': {leg: (lx, ly, 0.56) for leg, (lx, ly) in LEGS.items()},
        'knee_back': 0.03,
        'ankle_z': 0.1,
        'foot_len': 0.12,
        'leg_radius': 0.14,
        'stride': 0.2,
        # a heavy calf charges head-low with the trunk leading rather than leaping like a cat (decided Nov 7)
        'strike_style': 'charge',
        # round 3: a third of the charge's head turn and roll, so the near petal ear doesn't stand up like a sail
        'charge_head_turn': 0.3,
        'trunk': {'points': TRUNK_PTS, 'parent': 'head', 'curl': 1.0, 'counter': 0.5,
                  # open 50°, not the default 70: a cupped magnolia (4-details.png panel 4), not a flat star
                  'bud': {'petals': PP.BUD_PETALS, 'length': 0.11, 'closed': 14.0, 'open': 50.0, 'roll': PP.BUD_ROLL}},
    }


def ear_weights(u: np.ndarray) -> dict[str, np.ndarray]:
    w2 = smooth(0.42, 0.88, u)
    w1 = (1 - w2) * smooth(0.04, 0.24, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    z = zones(co)
    regions = []
    # the skin round the ear roots (and its fur clumps) stays on the head: the big ear bones would drag it
    er = z['ear_root'] | ((ear_root_dist(co) < 0.16) & (co[:, 2] > 0.88) & z['head'] & ~z['trunk'])
    if er.any():
        regions.append(U.rigid(er, 'head'))
    tr = z['trunk']
    if tr.any() and 'trunk.1' in names:
        regions.append((tr, U.chain_weights(co[tr], TRUNK_PTS, TRUNK_BONES, 'head', fade=(0.04, -0.06))))
    tl = z['tail']
    if tl.any():
        regions.append((tl, U.chain_weights(co[tl], TAIL_PTS, ['tail.1', 'tail.2'], 'hips')))
    # round 2: the belly follows the body bones only (the thighs' heat weights pinched it into flat planes in ko)
    bl = z['torso'] & (co[:, 2] < 0.5) & (np.abs(co[:, 1]) < 0.42)
    if bl.any():
        y = co[bl, 1]
        wh = smooth(-0.1, 0.25, y)
        wc = smooth(0.05, -0.3, y)
        ws = np.clip(1.0 - wh - wc, 0.0, 1.0)
        tot = wh + wc + ws
        regions.append((bl, {'hips': wh / tot, 'chest': wc / tot, 'spine': ws / tot}))
    return regions


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    part, side, pid, pu = attr('part'), attr('side'), attr('pid'), attr('pu')
    regions = []
    for s, tag in ((1, 'L'), (-1, 'R')):
        m = (np.abs(part - PP.PART_EAR) < 0.1) & (np.abs(side - s) < 0.1)
        if m.any():
            w = ear_weights(np.clip(pu[m], 0, 1))
            regions.append((m, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    for i in range(PP.BUD_PETALS):
        m = (np.abs(part - PP.PART_PETAL) < 0.1) & (np.abs(pid - i) < 0.1)
        if m.any():
            regions.append(U.rigid(m, f'bud.{i + 1}'))
    m = (np.abs(part - PP.PART_CORE) < 0.1) | (np.abs(part - PP.PART_HEART) < 0.1)
    if m.any():
        regions.append(U.rigid(m, TRUNK_BONES[-1]))
    # each sepal sits between petals k and k+1: half on each bone, so it opens with them (about 44°, the blend of two
    # 50° turns 72° apart) and stays under the open flower instead of standing inside it
    for k in range(PP.BUD_PETALS):
        m = (np.abs(part - PP.PART_SEPAL) < 0.1) & (np.abs(pid - k) < 0.1)
        if m.any():
            n = int(m.sum())
            regions.append((m, {f'bud.{k + 1}': np.full(n, 0.5), f'bud.{(k + 1) % PP.BUD_PETALS + 1}': np.full(n, 0.5)}))
    m = np.abs(part - PP.PART_LEAF) < 0.1
    if m.any():
        regions.append(U.rigid(m, 'head'))
    m = np.abs(part - PP.PART_TAIL_LEAF) < 0.1
    if m.any():
        regions.append(U.rigid(m, 'tail.2'))
    return regions


# the ears are huge petals: calm them everywhere, more in the big poses; the trunk hangs heavy in the hits
CLIP_CALM = {
    '*': {'ear': 0.5},
    # round 2: the near ear stood up like a sail in strike and hit_heavy flicked the far ear up like a rabbit's; and
    # never spread the ears like wings in the airborne clips
    'ko': {'ear': 0.12, 'tail': 0.5, 'trunk': 0.6},
    'hit_heavy': {'ear': 0.0, 'tail': 0.6, 'trunk': 0.7},       # round 3: the far ear still flicked up like a rabbit's
    'strike': {'ear': 0.1},
    'hit': {'ear': 0.3, 'bud': 0.3},  # round 3b: the bud's surprised flick only hints (it parted the tips: dark slits)
    'win': {'ear': 0.18},
    'celebrate': {'ear': 0.25},
    'hop': {'ear': 0.25},
    'cast': {'ear': 0.35},
    'sidestep_l': {'ear': 0.35},
    'sidestep_r': {'ear': 0.35},
    'run': {'ear': 0.4},
    'dash': {'ear': 0.3},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the big black pupil, the warm grey-brown iris, the catchlights and the '
             'upper lash line baked into the atlas; the brows, the lash flicks, the blush and the two small smiles beside '
             'the trunk are baked into the body. No face sheet and no morphs: expressions in clips\' `faces` are hints '
             'only. Blinking scales the blink bones (play `blink` over any clip): each lens squashes onto the closed lid\'s '
             'lash line and sinks into the head, showing the closed lid sculpted and painted under it. The trunk\'s bud '
             'opens on its petal bones (bud.1..5) in idle_happy, pet, celebrate and win.')

REVIEW = {
    'centre': (0.0, -0.12, 0.7),
    'size': 2.05,
    'head': ((0.0, -0.47, 1.0), 1.75),
}
