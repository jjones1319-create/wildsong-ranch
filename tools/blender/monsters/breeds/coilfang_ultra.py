"""Coilfang at the Art 2.1 Ultra tier (chatgpt/monsters/23-coilfang; CONTENT entry 9): a jade serpent resting in a loose
S with its head raised on a near-vertical neck, a feathered golden crest fanning from the top of its head, two neat
white fangs, big clever eyes, crisp overlapping scales with an argyle of darker jade diamonds down its back, and wide
cream-green belly scutes; on the serpent plan (plans/serpent.py; RECIPE.md "Serpent plan").

    npm run art:shape -- coilfang
    tools/blender/slot.sh npm run art:ultra -- coilfang --blender --stages build,bake,rig,clips,export,review > tools/blender/out/coilfang-build1.log 2>&1 &

Size: HEIGHT_UNITS 150 (coiled, 1 x Puddlepup's height) -> 0.986 m to the crest's top (the crest is a prop; the body's own
top, restHeight, is the skull's); about 3.3 m from the snout to the tail's tip along the body (the card: 3.5 x
Puddlepup's length; the turnaround's path measures about that).

The parts:
  - the body (lo_body): the head (a rounded wedge with wide jowls, the snout overhanging the chin, brow ridges, the
    eyeballs under the lenses), the neck and the S of the body as one skin, cut along the mouth's line so the jaw opens;
    crisp rhombic scales in a regular diagonal lattice (bigger on the back, smaller toward the head and the tail), wide
    overlapping belly scutes, small scales on the head and a smooth face (coilfang_scales.py);
  - the props (lo_props): the crest's feathers on two mirrored chains crestL / crestR, the forked tongue on the jaw's
    chain tongue.1..2, the two fangs (rigid on the head) and the mouth's dark pocket (coilfang_props.py);
  - the eyes: glossy lenses with a deep green iris, a big pupil, lashes on the lid (coilfang_paint.py).
Colours (CONTENT): scales #2FA37A, belly #DDF2D3, crest #E8C14E, eyes #1B3A2B. Derived (CONTENT has none; the card
suggests #23845F): the diamonds' darker jade; the fangs' ivory and the mouth's rose from the pictures.
Imperial Coilfang (secrets.ts "gold scales", variants.ts): scales #D4A017 (the diamonds a darker gold), belly #FFF0B8,
crest #8A1C1C, eyes #1B3A2B.
"""
from __future__ import annotations

import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.surface import smooth, v3
from monsters.breeds import coilfang_form as F
from monsters.breeds import coilfang_mouth as MO
from monsters.breeds import coilfang_props as PR

ID = 'coilfang'
LOOK = 'coilfang-ultra'
PLAN = 'serpent'
HEIGHT_UNITS = 150
PALETTE = {'body': '#2FA37A', 'belly': '#DDF2D3', 'accent': '#E8C14E', 'eye': '#1B3A2B'}
VARIANTS = {'imperial-coilfang': {'body': '#D4A017', 'belly': '#FFF0B8', 'accent': '#8A1C1C', 'eye': '#1B3A2B'}}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')     # the lower lip is weighted to the jaw below (RECIPE.md, Serpent plan)
BODY_TRIS = 52000
VOXELS = {'hi': 0.0024, 'hi_quick': 0.006, 'lo': 0.0052}
ATLAS_STRIP = 0
NORMAL_SCALE = 1.1
BODY_SHEEN = 0.0                                 # scales: the gloss is the clearcoat
ATLAS_MARGIN = 0.008                             # round 3: wider gutters (gold hairlines on the skin at the small mips)
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_props': 0.85}
AO_FLOOR = 0.42
AO_SOFTEN = 1.5
LITE_PROPS_TRIS = 6000                           # the crest's feathers are the signature (the simplifier breaks thin shells)
BLINK_CLOSED = (0.97, 0.04, 0.12)
FACE_NOTE = ('Baked face: big glossy lenses with a deep green iris, a large pupil and two catchlights, dark lashes on '
             'the upper lid flicking out at the outer corner, a small smile with two white fangs (props) at its front. '
             'Blinking scales the blink bones: each lens squashes down and sinks, showing the closed lid sculpted under it.')
CREST_CHAIN = [(0.04, -0.69, 0.76), (0.11, -0.62, 0.87), (0.17, -0.53, 0.96)]
HEAD_C, HEAD_R = F.HEAD_C, F.HEAD_R


def rig_p() -> dict:
    return {'spine': F.SPINE, 'hip': F.SPINE[F.ANCHOR], 'chest': F.SPINE[F.ANCHOR - 1], 'radius': F.RMAX, 'neck_bones': 4,
            'head_c': F.HEAD_C, 'head_r': F.HEAD_R, 'head_tip': F.HEAD_TIP,
            'jaw': {'head': MO.JAW_HINGE, 'tail': MO.JAW_TIP}, 'jaw_open': True,
            'tongue': {'points': PR.TONGUE, 'parent': 'jaw', 'reach': PR.TONGUE_REACH},
            'chains': [{'name': 'crest', 'kind': 'crest', 'parent': 'head', 'mirror': True, 'points': CREST_CHAIN}],
            'coil': {'turn': 1, 'spacing': 2.05 * F.RMAX, 'inner': 1.3 * F.RMAX},
            'strike_style': 'lunge', 'cast_style': 'hiss', 'ko_style': 'belly', 'strike_yaw': 15.0,
            # plans/serpent.py knobs (Nov 17, opt-in): twists roll every bone the same way; the strong Fang Snap
            'roll_fix': True,
            # round 2: a coiled-spring wind-up (the neck drawn back into a tight S, the head cocked back and low, the
            # front bunched, the crest laid back, the eyes narrowed), then the head out at mid height, jaws wide, the
            # trailing body keeping its S (5-poses attack)
            # round 3: the neck folds into a Z in the wind-up; at the drive the head lifts (the upper jaw up, the lower
            # down: a gape of about 60 degrees with the fangs and the pink mouth at the front) and the eyes stay narrowed
            'lunge': {'elev': 44.0, 'elev_rise': 0.0, 'slide': 0.12, 'straight': 0.3, 'jaw': 62.0,
                      'wind_elev': [35.0, 118.0, 148.0, 60.0], 'ph_max': 2.65, 'back': 0.12, 'head_up': 22.0, 'coil': 0.6,
                      'crest_wind': -22.0, 'crest_back': 24.0, 'wave': 16.0, 'drive_wave': 9.0, 'squint': 0.45,
                      'squint_drive': 0.4, 'jaw_wind': 4.0, 'head_drive': 16.0},
            'win_squint': 0.45,
            # the upright neck can't rise further: the front of the body rears instead (battle_idle's raised S, the hiss)
            'rear': 0.09,
            # ko and hit_heavy roll the top away from the three-quarter camera (the belly and the face toward it), the
            # crowned head less than the body
            'ko_twist': -100.0, 'ko_head_roll': -50.0, 'hit_heavy_roll': -45.0, 'hit_heavy_head_roll': -18.0,
            # sleep: the neck lays down only partly, so the head rests on the coil, not buried in it (5-poses brace)
            'sleep_neck': 0.6,
            # the tongue flicks pass between the lips: the jaw parts a little for each
            'clip_bones': {'idle': {'jaw': [(0.27, 0.45, (5.0, 0.0, 0.0))]},
                           # win: a wide open smile through the jump (the in-game shot is airborne, at t 0.2)
                           'win': {'jaw': [(0.0, 0.55, (22.0, 0.0, 0.0))]},
                           # round 3: hit and hit_heavy clench the mouth (with the eyes squeezed an open smile read as
                           # laughing): the same bumps as the plan's jaw keys, taken back
                           'hit': {'jaw': [(0.0, 0.8, (-16.0, 0.0, 0.0))]},
                           'hit_heavy': {'jaw': [(0.0, 0.62, (-22.0, 0.0, 0.0))]},
                           'look_around': {'jaw': [(0.27, 0.45, (5.0, 0.0, 0.0)), (0.69, 0.87, (5.0, 0.0, 0.0))]},
                           'sit': {'jaw': [(0.17, 0.35, (5.0, 0.0, 0.0))]},
                           'battle_idle': {'jaw': [(0.47, 0.65, (5.0, 0.0, 0.0))]}}}


# ----------------------------------------------------------------------------- the body
def all_parts():
    return F.all_parts()


def zones(co: np.ndarray, n=None) -> dict:
    from monsters.breeds import coilfang_scales as SC
    return SC.zones(co)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    from monsters.breeds import coilfang_scales as SC
    return SC.decimate_keep(co)


def texel_k(fc: np.ndarray) -> np.ndarray:
    from monsters.breeds import coilfang_scales as SC
    return SC.texel_k(fc)


def carve(hi_body) -> None:
    from monsters.breeds import coilfang_carve as CV
    CV.carve(hi_body)


def carve_low(lo_body) -> None:
    from monsters.breeds import coilfang_carve as CV
    CV.carve_low(lo_body)


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    from monsters.breeds import coilfang_skin as SK
    return SK.body_regions(co, names)


def build_props(high: bool, quick: bool):
    return PR.build(high, quick)


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    from monsters.breeds import coilfang_skin as SK
    return SK.prop_regions(co, attr, names, CREST_CHAIN)


def preview_prop_colour(name: str):
    from monsters.breeds import coilfang_paint as PT
    return PT.preview_prop_colour(name)


# ----------------------------------------------------------------------------- eyes
def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = F.eye_frame(s)
    m = Matrix((tuple(xax), tuple(yax), tuple(look))).transposed().to_4x4()
    return Matrix.Translation(Vector(tuple(c - look * (F.EYE_R * F.EYE_DEPTH[1])))) @ m


def build_eye(name: str, s: int, high: bool):
    import bmesh
    import bpy
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.3]
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
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / np.array([sx, sy, sz]))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


LID_LASH = 0.62          # the closed lid's lash line, below the lens's centre (x EYE_R): where a blink squeezes the lens


def blink_pivot(s: int):
    c, _xax, yax, look = F.eye_frame(s)
    c0 = c - look * (F.EYE_R * F.EYE_DEPTH[1])
    # at the closed lid's lash line (coilfang_carve CLOSED_AT and LID_DROP): the lens squeezes onto it and sinks
    p = c0 - yax * (F.EYE_R * F.EYE_SHAPE[1] * 0.25) + look * (F.EYE_R * 0.08)
    return Vector(tuple(p)), Vector(tuple(yax)), Vector(tuple(look))


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    from monsters.breeds import coilfang_paint as PT
    return PT.eye_material(name, rough_pass, pal or PALETTE)


# ----------------------------------------------------------------------------- paint
def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import coilfang_paint as PT
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import coilfang_paint as PT
    return PT.body_material(name, attr, pal, marks)


def prop_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import coilfang_paint as PT
    return PT.prop_material(name, attr, pal, marks)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import coilfang_paint as PT
    return PT.preview_colours(co, vn)


# the crest flares higher at the top of win's jump
CLIP_CALM = {'win': {'crest': 1.6}}
REVIEW = {'centre': (0.05, 0.06, 0.42), 'size': 2.4, 'head': ((0.0, -0.76, 0.68), 0.82)}
