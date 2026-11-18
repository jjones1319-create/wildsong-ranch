"""Aurelwyrm at the Art 2.1 Ultra tier (chatgpt/monsters/24-aurelwyrm; CONTENT entry 20): a golden serpent dragon that
floats without wings, its long body in gentle S-curves, crimson ribbon fins running along its back and sides and
trailing like silk, a golden mane round a kind, regal face, small branching velvet antlers and long whiskers; on the
serpent plan (plans/serpent.py; RECIPE.md "Serpent plan").

    npm run art:shape -- aurelwyrm
    tools/blender/slot.sh npm run art:ultra -- aurelwyrm --blender --stages build,bake,rig,clips,export,review > tools/blender/out/aurelwyrm-build1.log 2>&1 &

Size: HEIGHT_UNITS 225 (the card: its raised head floats about 1.5 x Puddlepup's height above the ground) -> 1.479 m to
the skull's top (restHeight; the antlers are props above it); about 4.3 m from the snout to the tail's tip along the body
(the card: 4.5 x Puddlepup's length). It is modelled floating, as the pictures show it at rest, so the plan's `float`
lift stays 0 (it would lift the floating rest pose again); nothing in its rest pose touches the ground, the plan's
ground guard sits at the body's radius, and ko falls to the ground (`ko_ground`).

The parts:
  - the body (lo_body): the head (a domed skull, round cheeks, a short soft muzzle, small pointed ears, the eyeballs
    under the lenses), the neck and the S of the body as one skin, cut along the mouth's line so the jaw opens; round
    overlapping gold scales, cream chevron plates under the belly and the throat, a cream muzzle, cheeks and chin
    (aurelwyrm_scales.py, aurelwyrm_carve.py);
  - the ribbons (lo_fins): the mane's crimson flame locks, the dorsal and side ribbons, the two streamers on their
    chains and the tail's fan (aurelwyrm_fins.py);
  - the props (lo_props): the velvet antlers (rigid on the head), the whiskers on their chains, the golden mane locks
    and the mouth's pocket (aurelwyrm_props.py);
  - the eyes: glossy lenses with a warm brown iris and an amber ring, dark lashes (aurelwyrm_paint.py).
No legs, no wings: the card ("No legs and no wings") wins over the plan note.
Colours (CONTENT): scales #F2C14E, belly #FFF4D6, ribbon fins #D64545, eyes #6B2D0F; the rest derived from them
(aurelwyrm_paint.py says how).
Sunsoul Aurelwyrm (secrets.ts "white-gold", variants.ts): scales #FFF6E0, belly #FFFFFF, ribbon fins #E8B923, eyes
#8A5A12; the antlers, whiskers and the gold mane keep their colours (the card: "white-gold scales with golden ribbon
fins"; the variant picture).
"""
from __future__ import annotations

import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from monsters.breeds import aurelwyrm_fins as FN
from monsters.breeds import aurelwyrm_form as F
from monsters.breeds import aurelwyrm_mouth as MO
from monsters.breeds import aurelwyrm_props as PR

ID = 'aurelwyrm'
LOOK = 'aurelwyrm-ultra'
PLAN = 'serpent'
HEIGHT_UNITS = 225
PALETTE = {'body': '#F2C14E', 'belly': '#FFF4D6', 'accent': '#D64545', 'eye': '#6B2D0F'}
VARIANTS = {'sunsoul-aurelwyrm': {'body': '#FFF6E0', 'belly': '#FFFFFF', 'accent': '#E8B923', 'eye': '#8A5A12'}}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')     # the lower lip is weighted to the jaw (RECIPE.md, Serpent plan)
BODY_TRIS = 54000
VOXELS = {'hi': 0.0026, 'hi_quick': 0.0065, 'lo': 0.0056}
ATLAS_STRIP = 0
NORMAL_SCALE = 1.2                               # round 2: the bigger scales' relief
BODY_SHEEN = 0.0                                 # scales: the gloss is the clearcoat
ATLAS_MARGIN = 0.008                             # wide gutters: the gold islands never bleed at the small mips
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_fins': 0.6, 'lo_props': 0.8}   # round 2: fewer ribbons, more texels each
AO_FLOOR = 0.48
AO_SOFTEN = 1.5
MEMBRANE_AO_BODY = False                         # the ribbons move: no baked shadows of them on the skin
LITE_PROPS_TRIS = 3400                           # round 3: the Lite stays under 1.5 MiB with the finer ruff
BLINK_CLOSED = (0.97, 0.04, 0.12)
MOUTH_SOCKET = (0.0, -1.3, 1.229)               # at the lips: the sunfire leaves the mouth, not the snout
FACE_NOTE = ('Baked face: almond glossy lenses with a heavy gold upper lid, a large warm brown iris with an amber ring, a '
             'round pupil and two catchlights, a dark lash line, a soft cream brow, a small kind smile under a cream muzzle. Blinking scales the '
             'blink bones: each lens squashes down and sinks, showing the closed lid sculpted under it.')
HEAD_C, HEAD_R = F.HEAD_C, F.HEAD_R


DORSAL = [f'dorsal{k}' for k in range(1, 6)]
FLANK = ['flankL1', 'flankL2', 'flankR1', 'flankR2']


def _rib(d: tuple, f: tuple, fan: tuple, extra: dict | None = None) -> dict:
    """{bone: (x, y, z) degrees} for the ribbon chains (world-aligned, + x lifts a back-pointing ribbon's tip): d and f
    the dorsal and flank runs' first and second bones, fan the tail fan's three; plus any other bones."""
    out = {}
    for n in DORSAL:
        out[f'{n}.1'], out[f'{n}.2'] = (d[0], 0.0, 0.0), (d[1], 0.0, 0.0)
    for n in FLANK:
        out[f'{n}.1'], out[f'{n}.2'] = (f[0], 0.0, 0.0), (f[1], 0.0, 0.0)
    for k, a in enumerate(fan):
        out[f'tailfin.{k + 1}'] = (a, 0.0, 0.0)
    out.update(extra or {})
    return out


def rig_p() -> dict:
    return {'spine': F.SPINE, 'hip': F.SPINE[F.ANCHOR], 'chest': F.SPINE[F.ANCHOR - 1], 'radius': F.RMAX,
            'neck_bones': F.NECK_BONES,
            'head_c': F.HEAD_C, 'head_r': F.HEAD_R, 'head_tip': F.HEAD_TIP,
            'jaw': {'head': MO.JAW_HINGE, 'tail': MO.JAW_TIP}, 'jaw_open': True,
            # round 2: the long ribbons' free halves ride chains of two bones (dorsal1..5, flankL1/2, flankR1/2), so
            # they trail and lift in the clips; the whiskers 3 bones each; the tail's fan 3
            'chains': [{'name': 'whisker', 'kind': 'whisker', 'parent': 'head', 'mirror': True, 'points': PR.WHISKER}]
                      + [{'name': m['name'], 'kind': 'ribbon', 'parent': m['parent'], 'points': m['points']} for m in FN.chains()]
                      + [{'name': 'tailfin', 'kind': 'ribbon', 'parent': f'tail.{F.TAIL_BONES}',
                          'points': [tuple(p) for p in FN.tailfin_points()]}],
            'coil': {'turn': 1, 'spacing': 2.3 * F.RMAX, 'inner': 1.5 * F.RMAX},
            'strike_style': 'lunge', 'cast_style': 'rise', 'ko_style': 'belly', 'strike_yaw': 15.0,
            'roll_fix': True,
            # the sunfire breath (5-poses attack): the neck rears back into an S, then the head drives forward and up,
            # level, the mouth wide, the body's front following
            # (round 2: it rears: the front lifts 0.22 m, the neck stays steep, the head tilts up and the jaw opens wide)
            # (round 3: the wind-up rears the neck up and back, the head about a head-height clear of the body (the
            # front also lifts: clip_bones below); the drive then strikes down and forward with a wide gape)
            'lunge': {'elev': 52.0, 'elev_rise': -12.0, 'slide': 0.1, 'straight': 0.25, 'jaw': 66.0, 'wind_low': 84.0,
                      'wind_high': 112.0, 'back': 0.1, 'head_up': 24.0, 'coil': 0.3, 'wave': 12.0, 'drive_wave': 6.0,
                      'squint': 0.3, 'squint_drive': 0.1, 'jaw_wind': 8.0, 'head_drive': -8.0, 'ph_max': 2.1, 'lift': 0.04},
            # round 2: the ribbons flare in the wind-up and stream back on the breath; hit and hit_heavy kink the body
            # and fling the ribbons; win rises high (hop), coils the tail up, throws the head up and lifts the ribbons
            'strike_windup_bones': _rib((12.0, 8.0), (14.0, 8.0), (10.0, 6.0, 4.0)),
            'strike_bones': _rib((-16.0, -12.0), (26.0, 16.0), (18.0, 12.0, 8.0)),
            # (round 3) hit and hit_heavy bend the mid-body into a sideways C and throw the tail's fan up and forward
            # over it (5-poses hit)
            'hit_bones': _rib((26.0, 18.0), (32.0, 20.0), (45.0, 35.0, 25.0),
                              {f'tail.{k}': (0.0, 0.0, 9.0) for k in range(3, 10)}),
            'hit_heavy_bones': _rib((34.0, 24.0), (40.0, 26.0), (65.0, 45.0, 30.0),
                                    {f'tail.{k}': (0.0, 0.0, 13.0) for k in range(3, 10)}),
            'win_bones': _rib((30.0, 22.0), (36.0, 24.0), (26.0, 18.0, 12.0),
                              {'head': (-16.0, 0.0, 0.0), 'tail.6': (14.0, 0.0, 10.0), 'tail.8': (16.0, 0.0, 12.0),
                               'tail.10': (18.0, 0.0, 14.0), 'tail.12': (20.0, 0.0, 14.0)}),
            'hop': 2.2,
            'win_squint': 0.4,
            'ko_ground': 0.0,
            'ko_twist': -90.0, 'ko_head_roll': -45.0, 'hit_heavy_roll': -40.0, 'hit_heavy_head_roll': -15.0,
            'sleep_neck': 0.55,
            # it floats: a slow hover bob through the idles (two soft rises a loop)
            'clip_bones': {# hit and hit_heavy clench the mouth (5-poses hit: eyes shut tight, teeth together; with the eyes
                           # squeezed an open mouth read as laughing): the plan's jaw keys taken back
                           'hit': {'jaw': [(0.0, 0.8, (-16.0, 0.0, 0.0))]},
                           'hit_heavy': {'jaw': [(0.0, 0.62, (-22.0, 0.0, 0.0))]},
                           # the strike's wind-up lifts the front (with the neck rearing back, the head clears the body)
                           'strike': {'hips': [(0.0, 0.5, (0.0, 0.0, 0.0), (0.0, 0.0, 0.14))]},
                           'idle': {'hips': [(0.0, 0.5, (0.0, 0.0, 0.0), (0.0, 0.0, 0.022)),
                                             (0.5, 1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.022))]},
                           'battle_idle': {'hips': [(0.0, 0.5, (0.0, 0.0, 0.0), (0.0, 0.0, 0.016)),
                                                    (0.5, 1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.016))]},
                           'idle_happy': {'hips': [(0.0, 0.5, (0.0, 0.0, 0.0), (0.0, 0.0, 0.03)),
                                                   (0.5, 1.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.03))]}}}


# ----------------------------------------------------------------------------- the body
def all_parts():
    return F.all_parts()


def zones(co: np.ndarray, n=None) -> dict:
    from monsters.breeds import aurelwyrm_scales as SC
    return SC.zones(co)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    from monsters.breeds import aurelwyrm_scales as SC
    return SC.decimate_keep(co)


def texel_k(fc: np.ndarray) -> np.ndarray:
    from monsters.breeds import aurelwyrm_scales as SC
    return SC.texel_k(fc)


def carve(hi_body) -> None:
    from monsters.breeds import aurelwyrm_carve as CV
    CV.carve(hi_body)


def carve_low(lo_body) -> None:
    from monsters.breeds import aurelwyrm_carve as CV
    CV.carve_low(lo_body)


def build_fins(high: bool, quick: bool):
    return FN.build_fins(high, quick)


def build_props(high: bool, quick: bool):
    return PR.build(high, quick)


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    from monsters.breeds import aurelwyrm_skin as SK
    return SK.body_regions(co, names)


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    from monsters.breeds import aurelwyrm_skin as SK
    return SK.prop_regions(co, attr, names)


def fin_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    from monsters.breeds import aurelwyrm_skin as SK
    return SK.fin_regions(co, attr, names)


def preview_prop_colour(name: str):
    from monsters.breeds import aurelwyrm_paint as PT
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
        # round 2: an almond (narrowing toward the corners, the outer corner lifted)
        x = v.co.x
        v.co = Vector((x * sx, (v.co.y * (1.0 - F.EYE_ALMOND * x * x) + F.EYE_TILT * x * s) * sy, v.co.z * sz))
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


def blink_pivot(s: int):
    c, _xax, yax, look = F.eye_frame(s)
    c0 = c - look * (F.EYE_R * F.EYE_DEPTH[1])
    # at the closed lid's lash line (aurelwyrm_carve CLOSED_AT and LID_DROP): the lens squeezes onto it and sinks
    p = c0 - yax * (F.EYE_R * F.EYE_SHAPE[1] * 0.25) + look * (F.EYE_R * 0.08)
    return Vector(tuple(p)), Vector(tuple(yax)), Vector(tuple(look))


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    from monsters.breeds import aurelwyrm_paint as PT
    return PT.eye_material(name, rough_pass, pal or PALETTE)


# ----------------------------------------------------------------------------- paint
def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import aurelwyrm_paint as PT
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import aurelwyrm_paint as PT
    return PT.body_material(name, attr, pal, marks)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import aurelwyrm_paint as PT
    return PT.preview_colours(co, vn)


# round 2: in the moving clips the ribbons stream behind (the plan's small trail, scaled: the dorsal run lies back (-),
# the flank runs and the fan lift toward level (+)); the whiskers calm in the strike (they read beaded)
_MOVE = {'ribbon': 2.6, **{n: -2.2 for n in DORSAL}}
# (round 3) the tail's fan sways wide a beat behind the body in walk, battle_idle and idle (it held a rigid spray)
_MOVE = {**_MOVE, 'tailfin': 4.5}
CLIP_CALM = {'walk': _MOVE, 'run': _MOVE, 'dash': _MOVE, 'step_fwd': _MOVE, 'step_back': _MOVE, 'strike': {'whisker': 0.4},
             'battle_idle': {'tailfin': 4.0}, 'idle': {'tailfin': 3.0}}
REVIEW = {'centre': (0.0, 0.42, 0.9), 'size': 3.8, 'head': ((0.0, -1.1, 1.42), 0.7)}
