"""Galeheron at the Art 2.1 Ultra tier (chatgpt/monsters/25-galeheron; CONTENT entry 11): a tall, elegant wind heron
with long gold legs, a long neck in a gentle S, a long gold dagger beak, streaming sky-blue crest plumes, a white
breast and throat, sky-blue wings with deep-blue wind swirls, and long tail plumes. On the avian plan (plans/avian.py;
RECIPE.md "Avian plan"), its first shipped breed.

    npm run art:shape -- galeheron
    tools/blender/slot.sh npm run art:ultra -- galeheron --blender --stages build,bake,rig,clips,export,review > tools/blender/out/galeheron-build1.log 2>&1 &

Size: HEIGHT_UNITS 255 (PROMPTS: about 1.7 x Puddlepup's height) -> 1.70 m to the crest plumes' tips, the skull 1.57 m.

The parts:
  - the body (lo_body, galeheron_form.py): the leaning trunk, the S-neck, the wedge head with its brows, the gold legs
    with their toes and claws; contour feathers, scutes and lid rims carved into the high source and baked
    (galeheron_carve.py);
  - the props (galeheron_props.py): the wings' feathers on the wing bones, the back's scapulars, the white bib and
    trousers (on the neck, chest and hips), the crest and tail plumes on their chains, the beak's two mandibles (the
    lower on `jaw`);
  - the eyes: glossy gold lenses with navy pupils, a white ring round each and a navy liner with a flick behind.
Dawnwing Galeheron (secrets.ts, variants.ts, the card): peach plumage #F7B59A, the belly and the throat #FFF1EA, rose
swirls #E86A8A; the beak, the legs and the eyes keep their gold.
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import galeheron_form as F
from monsters.breeds import galeheron_paint as PT
from monsters.breeds import galeheron_props as PR

ID = 'galeheron'
LOOK = 'galeheron-ultra'
PLAN = 'avian'
HEIGHT_UNITS = 255
PALETTE = {'body': '#6FB7E9', 'belly': '#F5F8FC', 'accent': '#2F5D8A', 'eye': '#F2C14E'}
VARIANTS = {'dawnwing-galeheron': {'body': '#F7B59A', 'belly': '#FFF1EA', 'accent': '#E86A8A', 'eye': '#F2C14E'}}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 34000
ATLAS_STRIP = 0
ATLAS_MARGIN = 0.006                       # the gold beak and legs beside sky-blue islands
NORMAL_SCALE = 0.85                          # (round 2) the folded wing's front edge read corrugated
AO_FLOOR = 0.55                             # layered feathers and crossing plumes: deep AO read as dark blots (build 1)
AO_SOFTEN = 1.5
LITE_PROPS_TRIS = 7000
ATLAS_DENSITY = {'lo_eyes': 4.0}              # (polish) the almond lenses are small: their irises smeared into wedges
BLINK_CLOSED = (0.9, 0.06, 0.1)             # squashed onto the lash line and sunk behind the lid
# (build 4) the sad and tired droop turned the folded wings' tips forward into the wider belly (the every-frame check:
# about 20% of the wing inside the body)
CLIP_CALM = {'idle_sad': {'wing': 0.3}, 'idle_tired': {'wing': 0.3}}
FACE_NOTE = ('Baked face: white round the eyes and under them, the sky-blue cap above; glossy gold lenses with navy '
             'pupils; a navy liner over each eye with a flick behind it. Blinking squashes each lens onto its lash line '
             'and sinks it, showing a white lid with a navy lash line. The beak is two props: the lower mandible on the '
             'jaw opens it.')


def _hold(t0: float, t1: float, bones: dict) -> dict:
    """clip_bones entries: each bone's rotation in a smooth bump from t0 to t1 (from -1 to 2 a near-constant hold)."""
    return {b: [(t0, t1, v)] for b, v in bones.items()}


# (round 2) flight: the long legs trail straight back under the tail (the plan's angles, made for short legs, pointed
# them up behind the head: thigh 45 + shin 35 + tarsus 55), and each wing turns about its own length so its feathers
# trail back and its faces read from the side (the spread pose hangs them in the frontal plane: edge-on from the side)
_FLY = {'thigh.L': (5.0, 0.0, 0.0), 'thigh.R': (5.0, 0.0, 0.0), 'shin.L': (-25.0, 0.0, 0.0), 'shin.R': (-25.0, 0.0, 0.0),
        'tarsus.L': (-47.0, 0.0, 0.0), 'tarsus.R': (-47.0, 0.0, 0.0), 'toe.L': (-25.0, 0.0, 0.0), 'toe.R': (-25.0, 0.0, 0.0),
        # (round 3) 35 degrees: at 60 the faces read from the side but went edge-on from the front
        'wing.L.1': (0.0, 35.0, 0.0), 'wing.R.1': (0.0, -35.0, 0.0)}
FLY_BONES = {'fly': _hold(-1.0, 2.0, _FLY), 'fly_cast': _hold(-1.0, 2.0, _FLY), 'fly_takeoff': _hold(0.3, 1.7, _FLY)}


def rig_p() -> dict:
    return {'hip': F.HIP, 'chest': F.CHEST, 'neck': F.NECK, 'head_c': F.HEAD_C, 'head_r': F.HEAD_R, 'head_tip': F.HEAD_TIP,
            'jaw': F.JAW, 'jaw_open': True, 'legs': F.LEG, 'wings': PR.WING, 'chains': PR.chains(),
            'strike_style': 'gust', 'cast_style': 'gust', 'ko_style': 'roll', 'strike_yaw': 24.0,
            # (build 2) the gust's impact for the ~70 degree battle camera: the plan sweeps the wings forward and down
            # (the near wing then points at the camera); these hold them wide, a little raised and swept back
            # (round 2) and the neck shoots forward level, the beak thrust at the target (it tilted to the ground)
            # (round 3) measured on the rig at the impact: the S unfolds forward (neck about 10, 35 and 40 degrees above
            # level), the head swings up against it so the beak points 15 degrees down at the target, the beak nearly shut
            'strike_bones': {'wing.L.1': (45.0, 0.0, 30.0), 'wing.R.1': (45.0, 0.0, -30.0), 'hips': (10.0, 0.0, 0.0),
                             'neck.1': (15.0, 0.0, 0.0), 'neck.2': (49.0, 0.0, 0.0), 'neck.3': (-16.0, 0.0, 0.0), 'head': (-85.0, 0.0, 0.0),
                             'jaw': (-20.0, 0.0, 0.0)},
            # (round 2) knocked off its feet with less fling (the near drumstick ballooned out of the belly)
            'hit_heavy_bones': {'thigh.L': (12.0, 0.0, 0.0), 'thigh.R': (12.0, 0.0, 0.0), 'shin.L': (12.0, 0.0, 0.0), 'shin.R': (12.0, 0.0, 0.0)},
            # (round 3) win: both wings wide open and raised (one read half-raised)
            'win_bones': {'wing.L.1': (25.0, 0.0, -36.0), 'wing.R.1': (25.0, 0.0, 36.0)},
            'clip_bones': FLY_BONES,
            # (build 2) the dash's long strides dipped the swinging toes 4 cm into the ground
            'stride': 0.8}


# ----------------------------------------------------------------------------- the body
def all_parts():
    return F.all_parts()


def zones(co: np.ndarray, n=None) -> dict:
    head = (F.head_sd(co) < 0.015) & (co[:, 2] > 1.36)
    e = PT.eye_local(co)
    eye_d = np.hypot(e[:, 0], e[:, 1]) * F.EYE_R
    ld, _ = PT.leg_dist(co)
    toes = (ld < 0.01) & (co[:, 2] < 0.05)
    legs = (ld < 0.01) & (co[:, 2] < 0.58)
    return {'face': head, 'eye_d': eye_d, 'toes': toes, 'legs': legs}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(0.55 * z['face'] + 0.4 * (z['eye_d'] < 0.04) + 0.55 * z['legs'] + 0.3 * z['toes'], 0.0, 1.0)


def texel_k(fc: np.ndarray) -> np.ndarray:
    """The head and the face more of the atlas (the eyes' lids and liner), the legs' scutes a little more; the hidden
    flanks under the folded wings less."""
    z = zones(fc)
    k = np.where(z['face'], 1.7, 1.0)
    # (round 2) the neck finer too: its blue/white border stair-stepped in the compressed colour map
    k = np.where((~z['face']) & (fc[:, 2] > 1.02) & (fc[:, 1] < -0.04), 2.0, k)
    k = np.where(z['legs'], 1.25, k)
    return k                            # (polish) the flanks under the wings at full density: open wings show them


def carve(hi_body) -> None:
    from monsters.breeds import galeheron_carve as K
    K.carve(hi_body)


def carve_low(lo_body) -> None:
    """(polish) The game mesh's eye sockets, as the high source's: no skin over the lenses' edges."""
    from monsters.breeds import galeheron_carve as K
    K.eye_sockets(lo_body)


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The bare legs ride their bones (segment weights over the drumstick, tarsus and toe; the drumstick's top blends
    into the hips under the belly feathers)."""
    regs = []
    x, z = co[:, 0], co[:, 2]
    for s, tag in ((1, 'L'), (-1, 'R')):
        hip, knee, ankle, toe, tip = F.leg_points(s)
        # (round 2) only the leg's own skin (the trousers' feathers hanging round the drumstick stay on the body)
        d = np.minimum(F.sd_tube(co, knee, ankle, F.SHIN_R[0], F.SHIN_R[1]), F.sd_tube(co, ankle, toe, F.TARSUS_R[0], F.TARSUS_R[1]))
        d = np.minimum(d, F.sd_ell(co, ankle + np.array((0.0, 0.004, 0.0)), (F.HEEL_R, F.HEEL_R * 1.1, F.HEEL_R * 1.25), (0.0, 0.0, 0.0)))
        d = np.minimum(d, F.sd_ell(co, toe + np.array((0.0, -0.004, -0.006)), (0.024, 0.027, 0.014), (0.0, 0.0, 0.0)))
        for b, t_, _k in F.toes(s):
            d = np.minimum(d, F.sd_tube(co, b, F.claw_tip(b, t_), F.TOE_R[0], 0.003))
        # the feet whole (their hallux and claws dipped into the ground when a stray vertex kept the proxy's weights)
        dax = F.sd_tube(co, ankle, toe, 0.0, 0.0)
        for b_, t_, _k in F.toes(s):
            dax = np.minimum(dax, F.sd_tube(co, b_, F.claw_tip(b_, t_), 0.0, 0.0))
        m = ((d < 0.008) | ((z < 0.1) & (dax < 0.05))) & (np.sign(x) == s) & (z < 0.6)
        # (round 2) the trousers' feathers round the drumstick's top ride the hips, never the thigh (they ballooned
        # into a white knob when hit_heavy flung the legs up)
        tr = (F.sd_tube(co, knee + (knee - ankle) * 0.4, ankle, 0.0, 0.0) < 0.09) & (z > 0.45) & (z < 0.72) & (np.sign(x) == s) & ~m
        if tr.any():
            regs.append(U.rigid(tr, 'hips'))
        if not m.any():
            continue
        segs = [(f'shin.{tag}', knee, ankle), (f'tarsus.{tag}', ankle, toe), (f'toe.{tag}', toe, tip)]
        w = U.segment_weights(co[m], segs, power=8.0)
        # the toes (and the hallux behind) are rigid on the toe bone
        foot = co[m][:, 2] < float(toe[2]) + 0.012
        for k in w:
            w[k] = np.where(foot, 1.0 if k == f'toe.{tag}' else 0.0, w[k])
        # under the belly the drumstick blends into the hips
        a = smooth_np(0.6, 0.53, co[m][:, 2])
        for k in w:
            w[k] = w[k] * a
        w['hips'] = 1.0 - a
        regs.append((m, w))
    return regs


def smooth_np(a, b, x):
    return F.smooth(a, b, x)


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    return PR.weight_regions(co, attr, names)


# ----------------------------------------------------------------------------- props
def build_props(high: bool, quick: bool) -> list:
    return PR.build(high, quick)


def preview_prop_colour(name: str):  # noqa: D103
    return {'beak': PALETTE['eye'], 'wings': PALETTE['body'], 'plumes': PALETTE['body'], 'bib': PALETTE['belly']}.get(name, PALETTE['body'])


# ----------------------------------------------------------------------------- eyes
EYE_DEPTH = F.EYE_DEPTH


def eye_centre(s: int) -> Vector:
    return F.eye_frame(s)[0]


def eye_matrix(s: int) -> Matrix:
    _c, xa, ya, look = F.eye_frame(s)
    m = Matrix((xa, ya, look)).transposed().to_4x4()
    return Matrix.Translation(eye_centre(s)) @ m


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    r, depth = F.EYE_R, EYE_DEPTH
    bm = bmesh.new()
    seg = 48 if high else 22
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.3]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    unit = np.array([v.co[:] for v in bm.verts])
    # (round 2) the lens follows the head's curve: a low dome on the skin (EYE_PROUD radii at its middle, half a
    # millimetre at its rim), its rim sunk into the head, so no corner of the almond stands off the face
    c, xa, ya, look = (np.array(v) for v in F.eye_frame(s))
    xl, yl = unit[:, 0] * r * F.EYE_AX[0], unit[:, 1] * r * F.EYE_AX[1]
    P = c[None] + xa[None] * xl[:, None] + ya[None] * yl[:, None]
    lo, hi = np.full(len(P), -0.05), np.full(len(P), 0.06)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        inside = F.head_sd(P + look[None] * mid[:, None]) < 0.0
        lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
    hs = 0.5 * (lo + hi)
    zl = np.where(unit[:, 2] >= 0.0, hs + 0.0005 + F.EYE_PROUD * r * np.sqrt(np.clip(unit[:, 2], 0.0, 1.0)) ** 0.8,
                  hs - 0.004 + unit[:, 2] * r * 0.5)
    for v, x_, y_, z_ in zip(bm.verts, xl, yl, zl):
        v.co = Vector((float(x_), float(y_), float(z_)))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    S.add_attr(ob, 'eyeuv', unit)
    S.add_attr(ob, 'eye_side', np.full(len(unit), float(s)))
    return ob


def blink_pivot(s: int):
    _c, xa, ya, look = F.eye_frame(s)
    c = eye_centre(s)
    return c + ya * (F.EYE_R * F.EYE_AX[1] * PT.LASH_Y) - look * (F.EYE_R * 0.4), ya, look


def eye_material(name: str, rough_pass: bool = False):
    return PT.eye_material(name, rough_pass)


# ----------------------------------------------------------------------------- paint
def paint_sources(body_srcs, fins, props=()) -> None:
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    return PT.body_material(name, attr, pal, marks)


def prop_material(name: str, attr: str, pal: dict, marks):
    return PT.prop_material(name, attr, pal, marks)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return PT.preview_colours(co, vn)


REVIEW = {'centre': (0.0, 0.05, 0.86), 'size': 1.95, 'head': ((0.0, -0.22, 1.47), 0.5)}
