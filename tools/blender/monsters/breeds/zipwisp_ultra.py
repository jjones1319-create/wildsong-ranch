"""Zipwisp at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md, the
"Floater plan" section).

A small fizzing ball of cyan static, hyper and giggly, always jittering (chatgpt/monsters/16-zipwisp/): a round ball of
glowing cyan energy whose outline is a swirl of flame licks, a bright white core shining through (round the small
open smile on the front, a star on the back), flames rising off the crown with one big curl leaning to its right, two
stubby spark wings with zigzag edges and a white glowing rim, a zigzag bolt of a tail off its lower back, tiny yellow
sparks crackling round it and on its skin, and a simple face: two big glossy oval eyes and a small mouth.

- The shape: zipwisp_form.py (measured on 2-turnaround.png); the wings, the tail and the sparks: zipwisp_props.py.
- Colours and paint: zipwisp_paint.py; the per-pixel bake materials: zipwisp_shade.py.

Part counts (the card): two spark wings, one zigzag tail, sparks; no arms or legs; the face is painted (the mouth never
opens: the jaw stays merged into the head). The crown's curl is in every picture (not on the card) and is kept.
Size: about 0.6 x Puddlepup (PROMPTS.md): HEIGHT_UNITS 90; the curl's top 0.595 m, the bare ball's top 0.475 m.
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import bpy
import numpy as np
from mathutils import Vector

from lib import surface as S
from lib import ultra as U
from lib.surface import smooth, v3
from monsters.breeds import zipwisp_form as F
from monsters.breeds import zipwisp_paint as WP
from monsters.breeds import zipwisp_props as PR
from monsters.breeds import zipwisp_shade as SH

ID = 'zipwisp'
LOOK = 'zipwisp-ultra'
PLAN = 'floater'
HEIGHT_UNITS = 90

PALETTE = {'body': '#6EF2FF', 'belly': '#FFFFFF', 'accent': '#FFE14D', 'eye': '#0E2A40'}
VARIANTS = {'prism-zipwisp': {'body': '#F5F2FF', 'belly': '#FFFFFF', 'accent': '#9B5CFF', 'eye': '#2A2140', 'rainbow': True}}

# the glow in each texel's own colour (untinted): a low floor on the cyan (no side goes grey, the tone map never washes
# it white), the licks' tips a little more, the core round the mouth and the back star hot, the wings' and tail's rims
# and the sparks bright. Steady (`twinkle` 0): the runtime's per-cell twinkle stippled Wishlume's large glowing paper.
# Prism has its own mask (VARIANT_ORM): its pale pearl barely glows, or it would bloom into a white blob.
GLOW = {'strength': 1.6, 'tint': None, 'twinkle': 0.0}
VARIANT_ORM = {'prism': {'glow': {'strength': 3.0, 'tint': None, 'twinkle': 0.0}}}   # review 2: its violet sparks bloom

ATLAS_STRIP = 0                     # no fur cards, no tuft
BODY_TRIS = 44000
VOXELS = {'hi': 0.0024, 'hi_quick': 0.0045, 'lo': 0.0038}   # review 2: finer tongue tips
ATLAS_DENSITY = {'lo_eyes': 1.4}
AO_FLOOR = 0.9                      # glowing energy: the licks' roots and the wings' roots never bake dark
AO_SOFTEN = 3.0
BODY_SHEEN = 0.0
NORMAL_SCALE = 0.5                   # round 2: softer relief; review 3: softer still (wet-looking streaks along the strands)
LITE_PROPS_TRIS = 2600              # the wings and the bolt are the look's signature; round 2: the lick-covered body can't
                                    # simplify below about 7k, so the props give way to keep the Lite copy under 12k
BLINK_CLOSED = (0.82, 0.04, 0.22)
MOUTH_SOCKET = (0.0, -0.188, 0.24)
MEMBRANE_AO_BODY = False

all_parts = F.all_parts
zones = F.zones
decimate_keep = F.decimate_keep
body_material = SH.body_material
glow_material = SH.glow_material
prop_material = SH.prop_material
eye_material = SH.eye_material
colours = WP.colours


def texel_k(co: np.ndarray) -> np.ndarray:
    """lo_body's texel density per face: the face 1.5 (the mouth and the lash lines), the underside 0.8."""
    k = np.ones(len(co))
    k = np.where(co[:, 2] < 0.13, 0.8, k)
    k = np.where(F.face_angle(co) < 40, 1.5, k)
    # review 3: the mouth on one clean island of its own (planar UVs survive the Lite copy's simplification; across seams
    # its paint came out a skewed, jagged triangle)
    mc = np.array(F.front_point(0.0, F.MOUTH_Z - 0.4 * F.MOUTH_H)[:])
    k = np.where(np.linalg.norm(co - mc, axis=1) < 0.05, 1.8, k)
    return k


# ----------------------------------------------------------------------------- carving
def _snap(co: np.ndarray) -> np.ndarray:
    """The bare ball's skin onto its exact shape (the voxel smoothing shrinks it a little), so the eye lenses, laid on
    it along its radius, sit flush; the licks and the crown keep their own shape."""
    # review 1: only round the eyes (the face's new low wisps keep their shape elsewhere)
    w = (smooth(0.006, 0.002, F.outside(co)) * smooth(0.095, 0.072, F.eye_dist(co)))[:, None]
    return co * (1 - w) + F.ball_point(co) * w


def mouth_mask(co: np.ndarray) -> np.ndarray:
    a = co[:, 0] / F.MOUTH_W
    a2 = np.clip(a * a, 0, 4)
    top = F.MOUTH_Z + 0.0055 * a2
    bot = top - F.MOUTH_H * np.sqrt(np.clip(1 - a2, 0, 1))
    return smooth(0.0012, -0.0006, co[:, 2] - top) * smooth(-0.0012, 0.0006, co[:, 2] - bot) * (np.abs(a) < 1.05) * (co[:, 1] < -0.12)


def carve(ob) -> None:
    co, _vn = S.mesh_arrays(ob)
    co = _snap(co)
    S.set_positions(ob, co)
    co, vn = S.mesh_arrays(ob)
    mouth = mouth_mask(co)
    # review 1: no raised strands any more (they caught white specular streaks along the ridges); review 2: no dent at
    # the mouth either (its rim and AO read as a pale muzzle ring): the smile is paint, flush in the glow
    S.base_attrs(ob, co, {'mouth': mouth})


def carve_low(ob) -> None:
    co, _vn = S.mesh_arrays(ob)
    S.set_positions(ob, _snap(co))


# ----------------------------------------------------------------------------- the eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    """The eye is an oval patch laid on the ball itself (the oval in the eye's tangent plane, each point carried onto
    the ball along its radius from the centre), bulging EYE_DOME at its middle and tucked EYE_SINK under the skin at
    its rim, so the whole oval shows and it sits flush in profile (Wishlume's lesson)."""
    c, xa, ya, lk = F.eye_frame(s)
    ax, ay = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1]
    rings, seg = (24, 72) if high else (6, 32)       # review 2: a lighter game lens (the Lite copy's 12k)
    verts, uvw = [np.array(c[:])], [(0.0, 0.0, 1.0)]
    for i in range(1, rings + 1):
        r = i / rings
        for j in range(seg):
            a = 2 * np.pi * j / seg
            verts.append(np.array((c + xa * (ax * r * np.cos(a)) + ya * (ay * r * np.sin(a)))[:]))
            uvw.append((r * np.cos(a), r * np.sin(a), 1.0 - r * r))
    P = np.array(verts)
    on = F.ball_point(P)
    nrm = (on - v3(F.C0)) / np.linalg.norm(on - v3(F.C0), axis=1)[:, None]
    w = np.array(uvw)
    h = F.EYE_DOME * w[:, 2] ** 0.8 - F.EYE_SINK * (1.0 - w[:, 2])
    co = on + nrm * h[:, None]
    faces = [(0, 1 + j, 1 + (j + 1) % seg) for j in range(seg)]
    for i in range(rings - 1):
        b0, b1 = 1 + i * seg, 1 + (i + 1) * seg
        faces += [(b0 + j, b1 + j, b1 + (j + 1) % seg, b0 + (j + 1) % seg) for j in range(seg)]
    ob = S.sheet_object(name, co, faces, out=tuple(lk))
    S.add_attr(ob, 'eyeuv', w)
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def blink_pivot(s: int):
    """Behind the lens at the closed lid's height: a blink squashes the lens onto the painted lash line
    (zipwisp_shade.face_marks) and sinks it under the skin."""
    c, _xa, ya, lk = F.eye_frame(s)
    return c - ya * (F.EYE_R * F.EYE_SHAPE[1] * 0.18) - lk * (F.EYE_R * 0.6), ya, lk


# ----------------------------------------------------------------------------- paint
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return WP.body_paint(co, PALETTE)['paint']


def preview_prop_colour(name: str):
    return PALETTE['accent'] if 'spark' in name else WP.colours(PALETTE)['wing']


def build_props(high: bool, quick: bool) -> list:
    return PR.objects(high)


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        co, _vn = S.mesh_arrays(ob)
        a = WP.body_paint(co, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'glow', a['glow'])
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), WP.body_paint(co, var)['paint'])
            S.add_attr(ob, f'glow_{U.variant_short(vid, ID)}', WP.prism_body_glow(co))
    for ob in props:
        a = WP.prop_paint(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'glow', a['glow'])
        for vid, var in VARIANTS.items():
            v = WP.prop_paint(ob, var)
            S.set_colour_attr(ob, U.variant_attr(vid, ID), v['paint'])
            S.add_attr(ob, f'glow_{U.variant_short(vid, ID)}', v['glow'])


# ----------------------------------------------------------------------------- the rig (plans/floater.py)
def rig_p() -> dict:
    return {
        'hip': F.C0, 'chest': (0.0, 0.0, F.TOP_Z), 'body_base': (0.0, 0.0, F.BOT_Z),
        'head_c': (0.0, -0.07, 0.3), 'head_r': 0.17,
        # the bolt first: socket_tail is the first tail-kind chain's tip
        'chains': [{'name': 'tail', 'kind': 'tail', 'parent': 'head', 'points': F.TAIL_BONES, 'stiff': 0.5},
                   {'name': 'tuft', 'kind': 'tail', 'parent': 'head', 'points': F.TUFT, 'stiff': 0.35},
                   {'name': 'wing', 'kind': 'fin', 'parent': 'head', 'points': F.wing_bone_points(1), 'mirror': True}],
        # the sparks ride their own bone from the ball's centre, so ko can fizzle them out and win can burst them
        'props': [{'name': 'sparks', 'parent': 'head', 'head': F.C0, 'tail': (0.0, 0.0, F.C0[2] + 0.1)}],
        'jitter': 1.3, 'bob': 0.8, 'strike_style': 'ram',
        # the dart turns a little toward its left (the in-game strike shot is from 70 degrees). Review 1: it leans in
        # 20 degrees (with the plan's 1.2 x 0.91 stretch along the dart), the wings sweep flat back and the bolt trails
        # straight behind (5-poses attack)
        # review 2: the pitch capped near 12 degrees and a wider turn, so the face looks at the target and the camera
        # review 3: nose-down about 20 degrees, the wings swept back only to about 30 (folded flat they went edge-on), the
        # bolt swung straight behind; the wind-up tilts back about 15 and spreads the wings
        'ram_yaw': 35.0,
        'strike_bones': {'hover': (12.0, 0.0, 0.0), 'wingL.1': (0.0, 0.0, 12.0), 'wingR.1': (0.0, 0.0, -12.0), 'tail.1': (0.0, 0.0, -70.0)},
        'strike_windup_bones': {'hover': (-8.0, 0.0, 0.0), 'wingL.1': (0.0, -30.0, 0.0), 'wingR.1': (0.0, 30.0, 0.0)},
        'glide_lean': 1.5,                          # review 3: the glides lean into the travel (walk about 12 degrees)
        # the knocks tip the ball back; the low bolt lifts with them instead of going through the ground. Review 1:
        # hit_heavy tips back about 23 degrees, not 45, and turns less away, so the squeezed eyes stay on camera
        # review 2: neither knock turns the face into profile (it stays within a few degrees of front)
        'hit_bones': {'hover': (0.0, 0.0, 30.0), 'tail.1': (0.0, 15.0, 0.0)},
        'hit_heavy_bones': {'hover': (22.0, 0.0, 36.0), 'tail.1': (0.0, 20.0, 0.0)},
        # review 1: win flares both wings up through the jump and the spin, the sparks bursting out to 1.3x in the jump
        # review 3: flaps between level and about 45 degrees up (raised to vertical they read as pointed ears)
        'win_bones': {'wingL.1': (0.0, -15.0, 0.0), 'wingR.1': (0.0, 15.0, 0.0)}, 'win_scale': {'prop.sparks': 1.3},
        # ko: the ball lies on its side on the ground (its body hovers at rest); the wing underneath folds up along the
        # ball, the bolt swings round behind it (neither pierces the ground) and the top wing lies swept back (raised,
        # it stood up like a crown)
        'ko_ground': 0.006,
        # review 1: it rolls only about 45 degrees (the plan's 80 less 35 on the hover bone: rolled flat, the mouth read as
        # an eye between two lid lines), the top wing droops, and the sparks fizzle out over the last frames
        # review 2: both wings droop further and the curl flops over
        # the bolt (out to its right since review 3) swings round behind it, so it lies clear of the ground
        'ko_bones': {'hover': (0.0, 35.0, 0.0), 'wingR.1': (0.0, 55.0, 0.0), 'wingL.1': (0.0, 60.0, 0.0), 'tail.1': (0.0, 15.0, -65.0),
                     'tuft.1': (0.0, -35.0, 0.0), 'tuft.2': (0.0, -30.0, 0.0)},
        'ko_scale': {'prop.sparks': 0.02},
    }


def _blend(w: dict, k: np.ndarray, parent: str = 'head') -> dict:
    out = {b: v * k for b, v in w.items()}
    out[parent] = out.get(parent, 0.0) + (1.0 - k)
    return out


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The ball is one rigid body on `head` (the lenses ride the head's blink bones, so the face never slides; the
    squash and the jitter come from the hover bone); the crown's curl bends on its two bones."""
    regs = [(np.ones(len(co), bool), {'head': np.ones(len(co))})]
    tk = F.tuft_k(co)
    m = tk > 0.01
    if m.any():
        regs.append((m, _blend(U.chain_weights(co[m], F.TUFT, ['tuft.1', 'tuft.2'], 'head', fade=(0.08, -0.04)), tk[m])))
    return regs


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """The wings on their chains from the root (buried in the ball: the head), the bolt one bone per stroke, the
    sparks rigid on their own bone."""
    part = np.rint(attr('part')).astype(int)
    side = np.rint(attr('side')).astype(int)
    out = [(np.ones(len(co), bool), {'head': np.ones(len(co))})]
    out.append(U.rigid(part == PR.SPARK, 'prop.sparks'))
    for tag, s in (('L', 1), ('R', -1)):
        m = (part == PR.WING) & (side == s)
        if m.any():
            out.append((m, U.chain_weights(co[m], F.wing_bone_points(s), [f'wing{tag}.1', f'wing{tag}.2'], 'head', fade=(0.06, -0.02))))
    m = part == PR.TAIL
    if m.any():
        out.append((m, U.chain_weights(co[m], F.TAIL_BONES, ['tail.1', 'tail.2', 'tail.3', 'tail.4'], 'head', fade=(0.04, -0.03))))
    return out


CLIP_CALM = {'*': {'tuft': 0.8}}

FACE_NOTE = ('The face is baked on the ball: the eyes are glossy lenses (lo_eyes) with the blue iris, the pupil and two '
             'catchlights painted in; the small open smile (navy, a lighter tongue, two tiny fangs) and the closed lids\' '
             'lash lines are baked into the body. No face sheet and no morphs: expressions in clips\' `faces` are hints '
             'only; the mouth never opens. Blinking scales the blink bones (play `blink` over any clip): each lens squashes '
             'onto the painted lash line and sinks under the skin. The glow is the ORM alpha in each texel\'s own colour: a '
             'low floor on the cyan, the white core round the mouth and the back star hot, the wings\' and the tail\'s '
             'rims and the sparks bright; socket_core is the ball\'s centre.')

REVIEW = {'centre': (0.0, 0.06, 0.31), 'size': 0.86, 'head': ((0.0, -0.08, 0.3), 0.5)}
