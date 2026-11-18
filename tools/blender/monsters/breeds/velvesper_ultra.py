"""Velvesper at the Art 2.1 Ultra tier (chatgpt/monsters/28-velvesper; CONTENT entry 13): a gentle velvet moth hovering
upright, a small fuzzy pale-lavender body with a round head, big soft dark eyes and a rose blush, a thick pale ruff, a
tufted abdomen and six little fuzzy legs dipped in plum; two pairs of big dusky-plum wings with scalloped bands, a pale
gold crescent moon on each forewing and an orange eyespot ringed with pale gold on each hindwing, all dusted with fine
scales and sparkle; two feathery antennae arching up from the crown. On the insect plan (plans/insect.py; RECIPE.md
"Insect plan"), its first hoverer.

    npm run art:shape -- velvesper
    tools/blender/slot.sh npm run art:ultra -- velvesper --blender --stages build,bake,rig,clips,export,review > tools/blender/out/velvesper-build1.log 2>&1 &

Size: HEIGHT_UNITS 165 (PROMPTS: about 1.1 x Puddlepup's height) -> the head's top at 1.085 m (restHeight; the antennae
are props above it, to 1.31 m, as Aurelwyrm's antlers), the forewings 1.75 m tip to tip (the card's wingspan "about
2 x"; the pictures' proportions), the feet hanging 13 cm above the ground.

The parts:
  - the body (lo_body, velvesper_form.py): the round head with its fluffy cheeks and a small muzzle, the thorax under
    a thick ruff of pointed tufts, the tufted abdomen hanging below, six legs; velvety fuzz carved into the high source
    and baked (velvesper_carve.py);
  - the props (velvesper_props.py): the four wings (cupped paddles with a rounded rim, on the wing bones) and the two
    feathery antennae (a shaft and two comb rows of barbs, on their chains);
  - the eyes: glossy lenses, a deep pupil inside a violet iris that glows at the bottom, two catchlights; a dark liner
    and three lashes at each outer corner.
Moonlit Velvesper (secrets.ts, variants.ts, the card): wings #5C5F78 with a silver shimmer, fur #D9DCEC, eyespots and
crescents #C0C4D8, gold eyes #F2E6A0; the antennae and the blush keep their colours.

The plan moves an upright hoverer by the wing options added for it (plans/insect.py, Nov 18, opt-in): the wings beat
about the upright body's long axis (forward = the power stroke), fold down along the flanks and back like a cape when
it lands, and the knock-out lays it on its back on its spread wings (`ko_wing_bias`).
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import velvesper_form as F
from monsters.breeds import velvesper_paint as PT
from monsters.breeds import velvesper_props as PR

ID = 'velvesper'
LOOK = 'velvesper-ultra'
PLAN = 'insect'
HEIGHT_UNITS = 165
PALETTE = {'body': '#5B3F7A', 'belly': '#EDE3F5', 'accent': '#F29E4C', 'eye': '#1B1424', 'ring': '#F7E7B5', 'crescent': '#F7E7B5'}
# the card: eyespots and crescents #C0C4D8; their pale ring the same lightened (derived)
VARIANTS = {'moonlit-velvesper': {'body': '#5C5F78', 'belly': '#D9DCEC', 'accent': '#C0C4D8', 'eye': '#F2E6A0',
                                  'ring': C.mix_hex('#C0C4D8', '#FFFFFF', 0.45), 'crescent': '#C0C4D8'}}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 52000                           # (build 4) the head's outline showed facets in the head shots
ATLAS_STRIP = 0
ATLAS_MARGIN = 0.006                        # the orange eyespots and pale crescents beside plum islands
AO_FLOOR = 0.74                             # the ruff's and the belly's layered tufts (round 1: lilac creases, never grey)
# (round 1) the game mesh from the same 3.5 mm voxels as the source: at 5.5 mm it bridged the narrow gaps between tufts
# and legs that the source keeps open, and the bake's rays fell through the bridges (black and silver specks)
VOXELS = {'lo': 0.0035}
# (round 1) Moonlit's silver wings get a glossier coat of their own (rough_moonlit: velvesper_paint.paint_sources)
VARIANT_ORM = {'moonlit': {}}
AO_SOFTEN = 2.5                             # (round 2) softer crease shading between the clumps
NORMAL_SCALE = 0.8
LITE_PROPS_TRIS = 6000                      # the four wings and the feathery antennae carry the breed
ATLAS_DENSITY = {'lo_eyes': 3.5}
BLINK_CLOSED = (0.95, 0.06, 0.12)           # squashed onto the lash line and sunk behind the lid
GLOW = {'strength': 0.6, 'twinkle': 0.0}    # a soft light in the crescents and the eyespots (never washed to white)
MOUTH_SOCKET = (0.0, -0.188, 0.8)
SOCKET_POINTS = {'socket_back': ('chest', (0.0, 0.16, 0.66))}
FACE_NOTE = ('Baked face: big glossy lenses, a deep pupil inside a violet iris that glows at the bottom, two catchlights; '
             'a dark liner over each eye with three lashes at the outer corner; a rose blush under each eye, a tiny rose '
             'nose and a little closed smile. Blinking squashes each lens onto its lash line and sinks it, showing a '
             'lavender lid with a dark lash line. The mouth does not open (a tiny mouth in the fuzz).')

# the wings beat about the upright body's long axis: + = the forward (power) stroke, dipping a little; the fold sweeps
# them straight back about the upright axis, both pairs alike (a tilted fold swung the hindwings' lobes in across
# each other behind the abdomen): closed behind it like a resting moth's, a cape (5-poses sit)
_BEAT, _FOLD = (0.0, 0.25, -1.0), (0.0, 0.0, 1.0)
MOTH_WINGS = [
    {'name': 'wing', 'parent': 'chest', 'points': PR.wing_bone_points('fore', 1), 'beat_axis': _BEAT, 'fold_axis': _FOLD,
     'fold': 58.0, 'fold_beat': 0.0, 'lag': 0.0},
    # the hindwings beat with the forewings as one surface (a moth's coupled wings; RECIPE's lag would let the pair
    # cut through each other where they overlap): lag -0.08 cancels the plan's own hind offset
    {'name': 'hind', 'parent': 'chest', 'points': PR.wing_bone_points('hind', 1), 'beat_axis': _BEAT, 'fold_axis': _FOLD,
     'fold': 58.0, 'fold_beat': 0.0, 'lag': -0.08},
]
CHAINS = [{'name': 'antenna', 'kind': 'antenna', 'parent': 'head', 'mirror': True, 'points': PR.antenna_points(1)}]


def _landed(t0: float, t1: float, back: float = 4.0, droop: float = 34.0) -> dict:
    """clip_bones for a landed clip (a smooth bump from t0 to t1; -5..6 is a near-constant hold, 0..2 rises to it):
    `back` sweeps the wings further back, the hindwings 6 degrees further, so the forewings close over them like a
    cape; `droop` lowers the forewings' tips down over them (round 2: the wings stood spread upright; a drooped
    hindwing swings its lower lobe in across the other behind the belly). The antennae are lifted clear of the crown.
    The body goes as low as the ground guard lets it (the probes below: the tucked feet, the belly's fluff, the
    hindwings' lobes)."""
    out = {'body': [(t0, t1, (0.0, 0.0, 0.0), (0.0, 0.0, -0.1))]}
    for i in range(1, 4):
        for tag, s in (('L', 1), ('R', -1)):
            out[f'leg{i}.{tag}'] = [(t0, t1, (-40.0 + 6.0 * i, 0.0, -8.0 * s))]
            out[f'shin{i}.{tag}'] = [(t0, t1, (95.0, 0.0, 0.0))]
    out['wingL.1'] = [(t0, t1, (0.0, droop, back))]
    out['wingR.1'] = [(t0, t1, (0.0, -droop, -back))]
    out['hindL.1'] = [(t0, t1, (0.0, 0.0, back + 11.0))]
    out['hindR.1'] = [(t0, t1, (0.0, 0.0, -back - 11.0))]
    out['antennaL.1'] = [(t0, t1, (-22.0, 0.0, 10.0))]
    out['antennaR.1'] = [(t0, t1, (-22.0, 0.0, -10.0))]
    return out


def _probes() -> list:
    """(round 1) The ground guard's extra probes (plans/insect.py `probes`): each foot's ball (a tucked foot turns its
    ball below the shin's end), the belly's and the abdomen's undersides, the hindwings' lowest lobes."""
    out = []
    for i in range(3):
        for tag, s in (('L', 1), ('R', -1)):
            out.append((f'shin{i + 1}.{tag}', tuple(float(v) for v in F.foot_centre(i, s)), F.FOOT_R[2] + 0.004))
    out += [('hips', (0.0, 0.0, 0.15), 0.012), ('rear.1', (0.0, 0.06, 0.155), 0.012), ('hips', (0.0, -0.12, 0.18), 0.012)]
    for tag, s in (('L', 1), ('R', -1)):
        for u, v in ((0.36, -0.42), (0.6, -0.3), (0.2, -0.36)):
            out.append((f'hind{tag}.1', tuple(float(x) for x in PR.wing_world('hind', s, u, v, 0.0).reshape(3)), 0.012))
    return out


def rig_p() -> dict:
    return {'form': 'hover', 'hip': F.HIP, 'chest': F.CHEST, 'front': F.FRONT, 'rear': F.REAR, 'head_c': F.HEAD_C, 'head_r': F.HEAD_R,
            'head_tip': F.HEAD_TIP, 'jaw': F.JAW, 'jaw_open': False, 'legs': F.LEGS, 'moth_wings': MOTH_WINGS, 'chains': CHAINS,
            'strike_style': 'dust', 'cast_style': 'glow', 'ko_style': 'flat', 'ko_ground': 0.0, 'beat': 3.0, 'flap': 24.0,
            'strike_yaw': 25.0,
            # ko: it drifts down and falls back onto its spread wings, face up (an upright moth's 'flat')
            'ko_bones': {'body': (-78.0, 0.0, 0.0)}, 'ko_wing_bias': 20.0,
            # the wings and the antennae are props: the knock-out's settle measures them too (they must not sink)
            'ko_settle_meshes': ('lo_body', 'lo_props'),
            # hit_heavy: knocked back with less tip, the wings flung up, not back and down (they swept 17 cm into the
            # ground; the plan's ground guard probes the body's joints, not the wing tips); hit a little the same
            'hit_heavy_bones': {'body': (14.0, 0.0, 0.0), 'hips': (-14.0, 0.0, 0.0), 'wingL.1': (0.0, -6.0, -14.0), 'wingR.1': (0.0, 6.0, 14.0),
                                'hindL.1': (0.0, -26.0, 12.0), 'hindR.1': (0.0, 26.0, -12.0),
                                # (round 2) crumpled: the outer halves folded back and down
                                'wingL.2': (0.0, 35.0, 40.0), 'wingR.2': (0.0, -35.0, -40.0), 'hindL.2': (0.0, -30.0, 8.0), 'hindR.2': (0.0, 30.0, -8.0)},
            # (round 1) hit crumples the wings back a little (the outer halves bent), not held flat
            'hit_bones': {'wingL.1': (0.0, 0.0, 20.0), 'wingR.1': (0.0, 0.0, -20.0), 'wingL.2': (0.0, 42.0, 45.0), 'wingR.2': (0.0, -42.0, -45.0),
                          'hindL.1': (0.0, 0.0, 20.0), 'hindR.1': (0.0, 0.0, -20.0), 'hindL.2': (0.0, -35.0, 30.0), 'hindR.2': (0.0, 35.0, -30.0)},
            # pet: the head-tilt rolls a hindwing's tip 3 mm into the ground; hover 1.2 cm higher
            # (round 1) landed (sit_down, sit, sleep): the little legs tucked under the belly (thighs forward, shins
            # folded back), the body lower to match, the wings swept back and drooping like a cape (5-poses sit;
            # the reviewer: it stood on straight stilts with its wings open)
            'clip_bones': {'pet': {'body': [(-1.0, 2.0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.012))]},
                           'sit_down': _landed(0.0, 2.0), 'sit': _landed(-5.0, 6.0),
                           # sleep folds 14 degrees further (the plan's full fold): back off so the pairs never meet
                           'sleep': _landed(-5.0, 6.0, back=-10.0, droop=32.0),
                           # the dizzy sway brushed a forewing over the cheek tufts
                           'dizzy': {'wingL.1': [(-5.0, 6.0, (0.0, 0.0, 10.0))], 'wingR.1': [(-5.0, 6.0, (0.0, 0.0, -10.0))],
                                     'hindL.1': [(-5.0, 6.0, (0.0, 0.0, 10.0))], 'hindR.1': [(-5.0, 6.0, (0.0, 0.0, -10.0))]}},
            'probes': _probes(),
            # strike: the hindwings sweep forward less than the forewings (at the impact they cut into the dangling legs)
            # (lab) and stay near their rest sweep: 20 degrees forward put the near one edge-on to the 70-degree camera (a
            # needle in front of the face)
            # (lab) the forewings to about 20 degrees forward, not 54: with the strike's yaw they went edge-on too
            'strike_bones': {'wingL.1': (0.0, 0.0, 34.0), 'wingR.1': (0.0, 0.0, -34.0), 'hindL.1': (0.0, -10.0, 69.0), 'hindR.1': (0.0, 10.0, -69.0)},
            # win: the wings held high in the burst of beats
            'win_bones': {'wingL.1': (0.0, -16.0, 0.0), 'wingR.1': (0.0, 16.0, 0.0)}}


# ----------------------------------------------------------------------------- the body
def all_parts():
    return F.all_parts()


def body_extras():
    return F.body_extras()


def zones(co: np.ndarray, n=None) -> dict:
    head = (F.head_sd(co) < 0.03) & (co[:, 2] > 0.72)
    e = PT.eye_local(co)
    eye_d = np.hypot(e[:, 0], e[:, 1]) * F.EYE_R
    face = head & (co[:, 1] < -0.1) & (np.abs(co[:, 0]) < 0.2) & (co[:, 2] < 0.95)
    ld, _li, _dn = F.leg_dist(co)
    legs = (ld < 0.012) & (co[:, 2] < 0.47)
    return {'face': face, 'head': head, 'eye_d': eye_d, 'legs': legs, 'toes': legs & (co[:, 2] < 0.22)}


def uv_smooth_mask(co: np.ndarray) -> np.ndarray:
    """0 on the face (the eyes' surrounds, the nose, the mouth, the blush), so its unwrap stays true."""
    e = PT.eye_local(co)
    near = F.smooth(2.6, 1.8, np.hypot(e[:, 0], e[:, 1])) * (np.abs(e[:, 2]) < 2.0)
    face = (np.abs(co[:, 0]) < 0.2) & (co[:, 1] < -0.08) & (co[:, 2] > 0.74) & (co[:, 2] < 0.95)
    return np.clip(1.0 - np.maximum(near, face.astype(np.float64)), 0.0, 1.0)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(0.6 * z['face'] + 0.4 * (z['eye_d'] < 0.03) + 0.3 * z['legs'] + 0.3 * z['head'], 0.0, 1.0)


def texel_k(fc: np.ndarray) -> np.ndarray:
    """The face more of the atlas (the liner, the lashes, the nose and the mouth), the head and the legs a little more;
    the abdomen's back, mostly under the wings, a little less."""
    # (round 1) two groups only, the face and the rest: each density group is projected on its own, and the ragged
    # zone borders through the tufts left single faces as islands of their own, some baked no texel (black specks)
    z = zones(fc)
    return np.where(z['face'], 1.5, 1.0)


def carve(hi_body) -> None:
    from monsters.breeds import velvesper_carve as K
    K.carve(hi_body)


def carve_low(lo_body) -> None:
    """The game mesh's eye sockets, as the high source's: no skin over the lenses' edges."""
    from monsters.breeds import velvesper_carve as K
    K.drop_islands(lo_body)
    K.eye_sockets(lo_body)


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The six legs ride their bones (segment weights over thigh and shin; the thigh's top blends into the chest under
    the ruff)."""
    regs = []
    ld, li, _down = F.leg_dist(co)
    for j, (s, tag) in enumerate(((1, 'L'), (-1, 'R'))):
        for i in range(3):
            h, k, f = F.leg_chain(i, s)
            # (round 2) the leg's own fuzz too: the thigh clumps stand up to 4.5 cm off its skin
            fc = F.foot_centre(i, s)
            skel = np.minimum(F.sd_tube(co, h, k, 0.0, 0.0), F.sd_tube(co, k, fc, 0.0, 0.0))
            m = ((ld < 0.008) | (skel < F.THIGH_R[0] + 0.045)) & (li == 3 * j + i) & (co[:, 2] < h[2] - 0.015)
            if not m.any():
                continue
            segs = [(f'leg{i + 1}.{tag}', h, k), (f'shin{i + 1}.{tag}', k, F.foot_centre(i, s))]
            w = U.segment_weights(co[m], segs, power=8.0)
            a = F.smooth(h[2] - 0.015, h[2] - 0.06, co[m][:, 2])
            for b in w:
                w[b] = w[b] * a
            w['chest'] = 1.0 - a
            regs.append((m, w))
    # (round 2) the toe tufts ride their shins
    tm, ti = F.toe_mask(co)
    for j, tag in enumerate(('L', 'R')):
        for i in range(3):
            m = tm & (ti == 3 * j + i)
            if m.any():
                regs.append(U.rigid(m, f'shin{i + 1}.{tag}'))
    return regs


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    return PR.weight_regions(co, attr, names)


# ----------------------------------------------------------------------------- props
def build_props(high: bool, quick: bool) -> list:
    return PR.build(high, quick)


def preview_prop_colour(name: str):  # noqa: D103
    if name.startswith(('fore', 'hind')):
        return PALETTE['body']
    if name.startswith('shaft'):
        return PALETTE['ring']
    return C.mix_hex(PALETTE['belly'], PALETTE['body'], 0.3)


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    r, depth = F.EYE_R, F.EYE_DEPTH
    bm = bmesh.new()
    seg = 48 if high else 22
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.3]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    unit = np.array([v.co[:] for v in bm.verts])
    # the lens follows the head's curve: a low dome on the skin (EYE_PROUD radii at its middle, half a millimetre at its
    # rim), its rim sunk into the head (and the socket under it: velvesper_carve.eye_sockets)
    c, xa, ya, look = (np.array(v) for v in F.eye_frame(s))
    xl, yl = unit[:, 0] * r * F.EYE_AX[0], unit[:, 1] * r * F.EYE_AX[1]
    P = c[None] + xa[None] * xl[:, None] + ya[None] * yl[:, None]
    lo, hi = np.full(len(P), -0.06), np.full(len(P), 0.06)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        inside = F.head_sd(P + look[None] * mid[:, None]) < 0.0
        lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
    hs = 0.5 * (lo + hi)
    zl = np.where(unit[:, 2] >= 0.0, hs - F.EYE_SINK + 0.0005 + F.EYE_PROUD * r * np.sqrt(np.clip(unit[:, 2], 0.0, 1.0)) ** 0.8,
                  hs - 0.004 + unit[:, 2] * r * 0.5)
    for v, x_, y_, z_ in zip(bm.verts, xl, yl, zl):
        v.co = Vector((float(x_), float(y_), float(z_)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = F.eye_matrix(s)
    S.add_attr(ob, 'eyeuv', unit)
    S.add_attr(ob, 'eye_side', np.full(len(unit), float(s)))
    return ob


def blink_pivot(s: int):
    _c, xa, ya, look = F.eye_frame(s)
    c = F.eye_frame(s)[0]
    return c + ya * (F.EYE_R * F.EYE_AX[1] * PT.LASH_Y) - look * (F.EYE_R * 0.4), ya, look


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    return PT.eye_material(name, rough_pass, pal)


# ----------------------------------------------------------------------------- paint
def paint_sources(body_srcs, fins, props=()) -> None:
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    return PT.body_material(name, attr, pal, marks)


def prop_material(name: str, attr: str, pal: dict, marks):
    return PT.prop_material(name, attr, pal, marks)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return PT.preview_colours(co, vn)


REVIEW = {'centre': (0.0, 0.12, 0.7), 'size': 2.0, 'head': ((0.0, -0.08, 0.93), 0.62),
          'clips': [('sit', 0.5), ('sleep', 0.5), ('cast', 0.56), ('idle', 0.12), ('battle_idle', 0.75)]}
