"""Gearhoot at the Art 2.1 Ultra tier (chatgpt/monsters/29-gearhoot; CONTENT entry 17): a clockwork owl of overlapping
brass plates with copper rivets, one eye a big glowing teal monocle lens in a copper ring and one a normal round eye,
bent brass ear tufts, a small hooked beak, wing feathers of plates and little gears, sturdy brass talons and a wind-up
key turning on its back. On the construct plan (plans/construct.py; RECIPE.md "Construct plan"), 'neck' head mode.

    npm run art:shape -- gearhoot
    tools/blender/slot.sh npm run art:ultra -- gearhoot --blender --stages build,bake,rig,clips,export,review > tools/blender/out/gearhoot-build1.log 2>&1 &

Size: HEIGHT_UNITS 150 (PROMPTS: about 1 x Puddlepup's height) -> 1.0 m to the ear tufts' tips, the head's dome 0.905 m.

The parts:
  - the body (lo_body, gearhoot_form.py): the egg body with its riveted collar (rigid on `hips`) and the head (rigid on
    `head`), separate shells: the head sits in the collar as a ball in a socket and turns about its own centre, so the
    owl's far turn never stretches anything. The plates, rivets, engravings, the brow mask and the gear emblems are
    carved into the high source and baked (gearhoot_carve.py);
  - the props (gearhoot_props.py): the wings (plates and gears on three-bone chains, two gears a side turning), the key,
    the legs and talons, the ear tufts, the beak (its lower half on the jaw) and the monocle's ring and bracket;
  - the eyes: the left (+X) is the monocle's teal glass lens, glowing (opaque glass with a painted reflection, not
    see-through: the game has no glass material and see-through quads speckle under GTAO); the right a normal round
    eye, pale with a warm-brown iris.
Colours (CONTENT): brass #C9A04A, light brass #E9D7A6, lens teal #5CC9C0, copper #B86B3C, eyes pale #F7F3E3.
Silver Gearhoot (secrets.ts, variants.ts, the card): plates silver #BFC5CC, chest #E8ECF0, rivets, trim, gear teeth and
the monocle ring dark steel #5B6670, the eye's iris #F2B544; the lens keeps its teal glow.
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from monsters.breeds import gearhoot_form as F
from monsters.breeds import gearhoot_props as PR

ID = 'gearhoot'
LOOK = 'gearhoot-ultra'
PLAN = 'construct'
HEIGHT_UNITS = 150
PALETTE = {'body': '#C9A04A', 'belly': '#E9D7A6', 'accent': '#5CC9C0', 'eye': '#F7F3E3', 'copper': '#B86B3C'}
VARIANTS = {'silver-gearhoot': {'body': '#BFC5CC', 'belly': '#E8ECF0', 'accent': '#5B6670', 'eye': '#F2B544', 'copper': '#5B6670'}}
EYE_PARENTS = {'L': 'prop.monocle'}        # the lens rides the monocle's ring
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 40000
VOXELS = {'hi': 0.003}
ATLAS_STRIP = 0
ATLAS_MARGIN = 0.006
NORMAL_SCALE = 1.3                         # the plates' edges read in the game (round 1: too soft)
BODY_SHEEN = 0
ATLAS_DENSITY = {'lo_eyes': 1.4}
LITE_PROPS_TRIS = 7000
FACE_RATIO_LIMITS = (12000, 1000)
GLOW = {'strength': 0.45, 'tint': None, 'twinkle': 0.0}   # round 1: the lens washed out to #B1FAF4 at 1.0
AO_FLOOR = 0.45                            # round 2: the wing backs and the belly's props AO read as smudges
AO_SOFTEN = 1.2
BLINK_CLOSED = (0.88, 0.06, 0.1)             # round 3: sunk under the lid (a pale sliver showed on the lash line)
FACE_NOTE = ('Baked face: a flat light-brass facial disc under a brass brow mask; the left eye (+X) is a big teal glass '
             'lens (glowing) in the monocle\'s copper ring, the right a pale round eye with a warm-brown iris; a small '
             'hooked brass beak whose lower half opens on the jaw. Blinking squashes each lens onto its lash line: the '
             'normal eye shows a brass lid, the monocle a darker teal glass with a closed lid line.')

# ----------------------------------------------------------------------------- the rig (metres)
HIP = (0.0, -0.03, 0.32)
TOP = (0.0, -0.03, 0.55)
NECK = [(0.0, float(F.HC[1]), float(F.HC[2]) - 0.05), tuple(F.HC)]
HEAD_TIP = (0.0, -0.25, float(F.HC[2]))
_mc, _mx, _my, _ml = PR.monocle_frame()
MONOCLE = {'name': 'monocle', 'parent': 'head', 'head': tuple(_mc), 'tail': tuple(_mc + _ml * 0.04)}


# the key turns slowly in the ranch clips and winds faster in battle, cast and win; it stops asleep (wound down). The
# coverts' two big gears tick round with it and spin fast in cast (5-poses: 'wings open showing spinning gears').
# plans/construct.py spinners 'clips' (Nov 17, opt-in): {clip: rate factor}, one-shots included
KEY_CLIPS = {'battle_idle': 1.6, 'strike': 2.0, 'cast': 3.0, 'win': 3.0, 'celebrate': 2.0, 'idle_happy': 1.5, 'sleep': 0.0}
GEAR_CLIPS = {'battle_idle': 2.0, 'strike': 5.0, 'cast': 7.0, 'win': 4.0, 'celebrate': 3.0, 'hit': 3.0, 'sleep': 0.0}


def _spinners() -> list[dict]:
    out = [{'name': 'key', 'head': tuple(PR.KEY_BASE), 'tail': tuple(PR.KEY_BASE + PR.KEY_DIR * PR.KEY_LEN), 'parent': 'hips',
            'rate': 0.5, 'clips': KEY_CLIPS}]
    for s, tag in ((1, 'L'), (-1, 'R')):
        for name, rate, sense in (('gear1', 0.25, 1), ('gear2', 0.33, -1)):
            c, n = PR.gear_axis(name, s)
            a, b = c - n * 0.01 * sense, c + n * 0.03 * sense
            out.append({'name': f'gear{tag}{name[-1]}', 'head': tuple(a), 'tail': tuple(b), 'parent': f'wing{tag}.1', 'rate': rate,
                        'clips': GEAR_CLIPS})
    return out


def spread(k: float, lift: float = 45.0) -> dict:
    """The wings opened k of the way to 2-turnaround's 'wings' view: each swung forward about the shoulder until it
    faces ahead (z), lifted out and up (x), the secondaries and primaries fanned on (world-aligned degrees)."""
    out = {}
    for tag, s in (('L', 1), ('R', -1)):
        # round 1: lower and wider (it rose above the head at 67 degrees): the tips reach 0.83-0.88 m out (FK check)
        out[f'wing{tag}.1'] = (lift * k, 0.0, -85.0 * k * s)
        out[f'wing{tag}.2'] = (0.0, 0.0, 0.0)
        out[f'wing{tag}.3'] = (-4.0 * k, 0.0, 0.0)
    return out


def bump(t0: float, t1: float, bones: dict, offsets: dict | None = None) -> dict:
    """clip_bones entries: each bone's rotation in a smooth bump from t0 to t1 (a bump from -1 to 2 is a near-constant
    hold, 0.87-1.0, that closes its loop)."""
    out = {b: [(t0, t1, v)] for b, v in bones.items()}
    for b, o in (offsets or {}).items():
        out.setdefault(b, []).append((t0, t1, (0.0, 0.0, 0.0), o))
    return out


def merge(*ds: dict) -> dict:
    out: dict = {}
    for d in ds:
        for b, items in d.items():
            out.setdefault(b, []).extend(items)
    return out


def _plus(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = tuple(x + y for x, y in zip(out.get(k, (0.0, 0.0, 0.0)), v))
    return out


CLIP_BONES = {
    # the attack picture: wings flung open showing the gears, the monocle pushed out a little as it fires
    'cast': merge(bump(0.06, 0.98, spread(1.0)), bump(0.3, 0.8, {}, {'prop.monocle': (0.0, -0.012, 0.0)})),
    'celebrate': merge(bump(0.03, 0.37, spread(0.75)), bump(0.38, 0.72, spread(0.75))),
    'battle_idle': bump(-1.0, 2.0, spread(0.2)),
    'strike': bump(0.3, 0.78, {}, {'hips': (0.0, -0.1, 0.0)}),
    # the owl's far turn: the plan's 34 degrees and 55 more on the head
    'look_around': merge(bump(0.08, 0.56, {'head': (0.0, 0.0, 55.0)}), bump(0.5, 0.98, {'head': (0.0, 0.0, -55.0)})),
}


def rig_p() -> dict:
    return {'hip': HIP, 'chest': TOP, 'head_c': (0.0, -0.12, float(F.HC[2]) + 0.02), 'head_r': 0.2, 'legs': [PR.LEG],
            'head_mode': 'neck', 'neck': NECK, 'head_tip': HEAD_TIP, 'jaw': PR.JAW, 'jaw_open': True,
            'chains': [{'name': 'wing', 'kind': 'wing', 'parent': 'hips', 'points': PR.WING, 'mirror': True}],
            'spinners': _spinners(), 'props': [MONOCLE], 'wing_tuck': False,
            'strike_style': 'peck', 'cast_style': 'raise', 'ko_style': 'roll',
            'clip_bones': CLIP_BONES,
            # the peck made big for the battle camera: leaning back with the wings half open, then the body pitched
            # forward and the head jabbing down, the wings flung back
            # (round 1: the monocle faces the target at the impact, the attack being a bolt from the lens: the plan's
            # 30 degree nod is taken back and the head held level against the body's 14 degree lean; it slides 10 cm)
            # (round 2: both wings held open with the gears showing through the impact)
            'strike_windup_bones': _plus(spread(0.5), {'hips': (-6.0, 0.0, 0.0), 'head': (6.0, 0.0, 0.0), 'neck.1': (4.0, 0.0, 0.0)}),
            'strike_bones': _plus(spread(0.95), {'hips': (6.0, 0.0, 0.0), 'head': (-29.0, 0.0, 0.0), 'neck.1': (-15.0, 0.0, 0.0)}),
            # round 2: hit_heavy's head held to ~30 degrees back (the face pointed at the sky); win's wings above the shoulders
            'hit_bones': _plus(spread(0.55), {'hips': (-6.0, 0.0, 0.0)}),
            'hit_heavy_bones': _plus(spread(0.75), {'head': (14.0, 0.0, 0.0), 'neck.1': (6.0, 0.0, 0.0)}),
            'win_bones': spread(0.95, lift=62.0), 'ko_bones': spread(0.3),
            'ko_settle_meshes': ('lo_body', 'lo_props')}


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    """Cores well inside the shells (body_extras are the real body): they give the heat-weight proxy something to solve
    on; every vertex is then weighted rigidly by body_weight_regions."""
    return [Part('core_body', 'sphere', loc=(0.0, -0.03, 0.33), radius=1.0, scale=(0.15, 0.16, 0.15)),
            Part('core_head', 'sphere', loc=tuple(F.HC), radius=1.0, scale=(0.15, 0.15, 0.12))]


def body_extras() -> list:
    return F.objects(fine=True)


def zones(co: np.ndarray, n=None) -> dict:
    head = F.head_mask(co)
    eye_d = np.minimum(np.linalg.norm(co - F.eye_frame(1)[0], axis=1), np.linalg.norm(co - F.eye_frame(-1)[0], axis=1))
    face = head & (co[:, 1] < F.Y_FACE + 0.03)
    return {'head': head, 'face': face, 'eye_d': eye_d}


def texel_k(fc: np.ndarray) -> np.ndarray:
    """Round 1: the head more of the atlas (its engraving stair-stepped), the face most; the underside and the seat
    under the neck dome less."""
    head = F.head_mask(fc)
    k = np.where(head, 1.3, 1.0)
    k = np.where(head & (fc[:, 1] < F.HC[1] - 0.12), 1.6, k)
    k = np.where(fc[:, 2] < 0.2, 0.7, k)
    seat = (~head) & (np.hypot(fc[:, 0], fc[:, 1] - F.HC[1]) < 0.19) & (fc[:, 2] > 0.5)
    return np.where(seat, 0.4, k)


def carve_low(lo_body) -> None:
    from monsters.breeds import gearhoot_carve as K
    K.carve_low(lo_body)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(0.8 * (z['eye_d'] < 0.09) + 0.4 * z['face'], 0, 1)


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    ob = bpy.data.objects.get('lo_body')
    head = F.shells_of(ob) if ob is not None and len(ob.data.vertices) == len(co) else F.head_mask(co)
    return [U.rigid(~head, 'hips'), U.rigid(head, 'head')]


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    bn = np.round(attr('bn')).astype(int)
    return [U.rigid(bn == i, b) for i, b in enumerate(PR.BONES) if (bn == i).any()]


# ----------------------------------------------------------------------------- props
def build_props(high: bool, quick: bool) -> list:
    return PR.build(high, quick)


def preview_prop_colour(name: str):  # noqa: D103
    return {'wings': PALETTE['copper'], 'key': PALETTE['body'], 'legs': PALETTE['body'], 'head': PALETTE['body']}.get(name, PALETTE['body'])


# ----------------------------------------------------------------------------- eyes
def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = (Vector(v) for v in F.eye_frame(s))
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * F.EYE_SINK) @ m


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    """A glossy lens: a cap of a sphere sunk in the face (the monocle's lens a little flatter and bigger)."""
    e = F.EYE[s]
    r, depth = e['r'], e['depth']
    bm = bmesh.new()
    seg = 56 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * r, v.co.y * r, v.co.z * r * depth))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / np.array([r, r, r * depth]))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    S.add_attr(ob, 'glow', np.full(len(co), 1.0 if s > 0 else 0.0))
    return ob


LASH_Y = -0.1                              # the closed lid's lash line, x the lens's radius below its centre


def blink_pivot(s: int):
    c, _xax, yax, look = (Vector(v) for v in F.eye_frame(s))
    return c + yax * (F.EYE[s]['r'] * LASH_Y) - look * F.EYE_SINK, yax, look


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    from monsters.breeds import gearhoot_paint as PT
    return PT.eye_material(name, rough_pass, pal or PALETTE)


# ----------------------------------------------------------------------------- the high source and the paint
def carve(hi_body) -> None:
    from monsters.breeds import gearhoot_carve as K
    K.carve(hi_body)


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import gearhoot_paint as PT
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import gearhoot_paint as PT
    return PT.body_material(name, attr, pal, marks)


def prop_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import gearhoot_paint as PT
    return PT.prop_material(name, attr, pal, marks)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import gearhoot_paint as PT
    return PT.preview_colours(co, vn)


REVIEW = {'centre': (0.0, 0.0, 0.5), 'size': 1.3, 'head': ((0.0, -0.2, 0.69), 0.62),
          'clips': [('idle', 0.25), ('cast', 0.53), ('look_around', 0.32), ('win', 0.6), ('hit_heavy', 0.31), ('dash', 0.45),
                    ('ko', 0.86)]}
