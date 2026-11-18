"""Lootlid at the Art 2.1 Ultra tier (chatgpt/monsters/30-lootlid; CONTENT entry 19): a wooden treasure chest on four
stubby legs whose lid is its mouth, with a long pink tongue and a hoard of gold coins inside and a gold keyhole plate for
a "nose". The first breed on the construct plan (plans/construct.py; RECIPE.md "Construct plan").

    npm run art:shape -- lootlid
    tools/blender/slot.sh npm run art:ultra -- lootlid --blender --stages build,bake,rig,clips,export,review > tools/blender/out/lootlid-build1.log 2>&1 &

Size: HEIGHT_UNITS 135 (0.9 × Puddlepup's height) → 0.89 m to the lid's ridge; 0.71 m wide, 0.6 m deep (2-turnaround).

The parts:
  - the body (lo_body): the box (rigid on `hips`, hollow inside), the lid (rigid on `head`, the bone turning about the
    hinge at the back; a 2 cm gap and a recess underneath, so it is a separate shell: the jaw lesson), the four posts
    (each on its leg chain), the eyes' wooden sockets, the closed eyelids under the lenses and the carved brows. The wood
    (planks, grain, knots, nicks, cracks, worn edges) is carved into the high source and baked (lootlid_wood.py);
  - the gold trim (lo_props, lootlid_trim.py): the box's rim band and corner straps, the lid's arched corner straps, the
    corner caps, the leg cuffs, the hinges and the keyhole plate, all with real domed rivets;
  - the hoard (lootlid_hoard.py): a heap of real coins, the tongue (three bones that slide out), and the dark cheeks that
    close the mouth's sides whenever the lid opens (a closed mouth from every angle);
  - the eyes: glossy lenses, cream with a big warm-brown iris, set in the sockets; no teeth anywhere (goofy, never
    menacing: the card).
Colours (CONTENT): wood #9C6B3F, lighter wood #C99A6B, gold trim and coins #F2C94C, tongue #E86A7C, eyes #2B1B10.
Gilded Lootlid (secrets.ts, variants.ts): polished gold #E0B030 with lighter #F7DE8A, the trim dark bronze #8A5A12, eyes
#3A2A10; the tongue stays pink and the coins gold (the variant picture); its own roughness (VARIANT_ORM).
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
from monsters.breeds import lootlid_form as F
from monsters.breeds import lootlid_noise as N

ID = 'lootlid'
LOOK = 'lootlid-ultra'
PLAN = 'construct'
HEIGHT_UNITS = 135
PALETTE = {'body': '#9C6B3F', 'belly': '#C99A6B', 'accent': '#F2C94C', 'eye': '#2B1B10', 'tongue': '#E86A7C'}
VARIANTS = {'gilded-lootlid': {'body': '#E0B030', 'belly': '#F7DE8A', 'accent': '#8A5A12', 'eye': '#3A2A10', 'tongue': '#E86A7C'}}
VARIANT_ORM = {'gilded': {}}               # polished gold: its own roughness and coat
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 36000
VOXELS = {'hi': 0.0026}                    # the planks' grooves and the grain want a fine high source
ATLAS_STRIP = 0
NORMAL_SCALE = 1.1                         # carved wood and hammered gold: about full strength
BODY_SHEEN = 0                             # wood: no fur sheen
ATLAS_DENSITY = {'lo_eyes': 1.4}
LITE_PROPS_TRIS = 7000                     # the gold trim, its rivets and the posts: keep them legible in the Lite copy
GLOW = {'strength': 0.9, 'tint': None, 'twinkle': 1.0}    # glints on a few coins (the card: 'coins glinting'); round 3: softer
AO_FLOOR = 0.3
AO_SOFTEN = 1.0
FACE_RATIO_LIMITS = (12000, 1000)          # the flat panels rightly decimate into big faces
BLINK_CLOSED = (0.78, 0.05, 0.12)          # polish pass: narrower and sunk deeper (its ends showed past the lash line in hit)
FACE_NOTE = ('Baked face: two big round glossy eyes (cream, a big warm-brown iris round a dark pupil, two catchlights) set '
             'in carved wooden sockets on the lid\'s front, dark carved brows over them and the gold keyhole plate below '
             'as its nose; the lid itself is the mouth (it opens on the head bone, with the tongue and the coins inside). '
             'Blinking scales the blink bones: each lens squashes onto its lash line and sinks, showing the closed wooden '
             'eyelid carved under it. The idles hold the lid cracked open with the tongue hanging over the front lip.')

# ----------------------------------------------------------------------------- the rig (metres)
HIP = (0.0, 0.0, 0.32)
TOP = (0.0, 0.0, F.Z_TOP)
HINGE = (0.0, 0.316, 0.486)                # the lid's hinge, at the back seam, just under the lid's back edge
LID_FRONT = (0.0, -0.31, 0.486)
HEAD_C = Vector((0.0, -0.31, 0.64))
HEAD_R = 0.2
MOUTH = (0.0, -0.27, 0.495)


def _leg(f: int) -> dict:
    from monsters.breeds import lootlid_legs as L
    return L.leg_bones(f)


LEGS = [_leg(1), _leg(-1)]
# the tongue: a short root at the back (dives into the coins), the long body, the front that hangs over the lip once out
TONGUE = [(0.0, 0.17, 0.508), (0.0, 0.11, 0.514), (0.0, -0.14, 0.524), (0.0, -0.25, 0.518)]


def _open(wag: float, rate: float) -> dict:
    """The hero's look (1-hero; round 1 review): the lid cracked about 14°, the tongue out over the front lip and hanging a
    quarter of the way down the front."""
    return {'mouth': 0.31, 'tongue': 0.45, 'bones': {'tongue.2': (-5.0, 0.0, 0.0), 'tongue.3': (70.0, 0.0, 0.0)}, 'wag': wag, 'rate': rate}


HOLD_OPEN = {'idle': _open(6.0, 1.0), 'look_around': _open(6.0, 1.0), 'battle_idle': _open(10.0, 2.0),
             'strafe_l': _open(8.0, 2.0), 'strafe_r': _open(8.0, 2.0),
             # clips whose own tongue comes out part way: out over the lip, hanging
             'idle_happy': {'tongue': 0.1, 'bones': {'tongue.2': (-5.0, 0.0, 0.0), 'tongue.3': (60.0, 0.0, 0.0)}},
             'pet': {'tongue': 0.2, 'bones': {'tongue.2': (-5.0, 0.0, 0.0), 'tongue.3': (60.0, 0.0, 0.0)}},
             'sit': {'tongue': 0.25, 'bones': {'tongue.2': (-5.0, 0.0, 0.0), 'tongue.3': (64.0, 0.0, 0.0)}},
             'dizzy': {'tongue': 0.25, 'bones': {'tongue.2': (-5.0, 0.0, 0.0), 'tongue.3': (52.0, 0.0, 0.0)}},
             'celebrate': {'tongue': 0.05, 'bones': {'tongue.2': (-5.0, 0.0, 0.0)}},
             'win': {'bones': {'tongue.2': (-5.0, 0.0, 0.0)}}, 'ko': {'tongue': 0.08},
             # polish pass: the hop sideways holds the hero look too (its lid crack showed the tongue's tip end-on)
             'sidestep_l': _open(8.0, 2.0), 'sidestep_r': _open(8.0, 2.0)}


def _loll(t0: float, t1: float, extra: float, hang: float) -> dict:
    """Round 3: the same lolling tongue in the clips whose own tongue only peeks out (cast, strike, hit, win's jump): a
    bump from t0 to t1 sliding it a further `extra` of its reach and hanging its last bone `hang` degrees over the lip."""
    step = 0.42 * extra / 2 / (HEIGHT_UNITS / 150.0)
    return {'tongue.2': [(t0, t1, (-5.0, 0.0, 0.0), (0.0, -step, 0.0))],
            'tongue.3': [(t0, t1, (hang, 0.0, 0.0), (0.0, -step, 0.0))]}


def _hit() -> dict:
    """hit: the lolling tongue, its sideways wag mostly undone (it lay along the rim as a thin rod)."""
    d = _loll(0.0, 0.8, 0.2, 55.0)
    d['tongue.1'] = [(0.0, 0.8, (0.0, 0.0, 12.0))]
    d['tongue.2'].append((0.0, 0.8, (0.0, 0.0, 6.0)))
    d['tongue.3'].append((0.0, 0.8, (0.0, 0.0, 6.0)))
    return d


CLIP_BONES = {'strike': _loll(0.38, 0.96, 0.24, 64.0), 'cast': _loll(0.45, 0.98, 0.22, 64.0),
              'hit': _hit(), 'win': _loll(0.0, 0.42, 0.45, 62.0),
              # polish pass: hit_heavy's tip curled up into a thin blade; it hangs forward over the lip instead
              'hit_heavy': {'tongue.2': [(0.0, 0.62, (5.0, 0.0, 0.0))], 'tongue.3': [(0.0, 0.62, (100.0, 0.0, 0.0))]}}
# polish pass: the posts are rigid on a box: outside the gaits the feet ride with the body (no bend at the hip), and the
# body never dips under its legs (plans/construct.py ride_legs)
LEGS_RIDE = {'*': 1.0, 'run': 0.5, 'dash': 0.6}   # the fast gaits also skid half their stride (a post swings <= 10°)
# ko: the posts splay only 10° in the air (the plan's 30° less 20 here)
KO_BONES = {'leg1.L': (0.0, 20.0, 0.0), 'leg2.L': (0.0, 20.0, 0.0), 'leg1.R': (0.0, -20.0, 0.0), 'leg2.R': (0.0, -20.0, 0.0)}
GAIT_LIFT = 0.3                            # and the gaits shuffle (the swing foot lifts 30%), the feet carried with the
                                           # body's bob and roll, short strides (gait_carry, stride)
HOARD = {'name': 'hoard', 'parent': 'hips', 'head': (0.0, 0.0, 0.42), 'tail': (0.0, -0.1, 0.42)}


def rig_p() -> dict:
    return {'hip': HIP, 'chest': TOP, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R, 'legs': LEGS,
            'hinge': HINGE, 'lid_front': LID_FRONT, 'lid_max': 45.0, 'mouth': MOUTH,
            # a long lid hinged at the back: 45° is wide open (the attack picture), 14° clears the tongue (the hero)
            'tongue': {'points': TONGUE, 'parent': 'hips', 'reach': 0.42}, 'tongue_lid': 14.0,
            'props': [HOARD],
            # round 2: the card's attack: shut and reared back, then the lid flung wide at the impact (coins burst out)
            'strike_style': 'spit', 'cast_style': 'spit', 'ko_style': 'roll', 'ko_roll': 82.0,
            'strike_yaw': 20.0, 'hop': 0.8, 'sit_drop': 0.03,
            # the tongue bends only at its last bone, once that is out past the lip; the hero's open look in the idles
            'tongue_hang': {'shares': (0.0, 0.0, 1.9), 'out': 0.42}, 'hold_open': HOLD_OPEN, 'clip_bones': CLIP_BONES,
            'legs_ride': LEGS_RIDE, 'gait_lift': GAIT_LIFT, 'gait_carry': 1.0, 'stride': 0.8, 'ko_bones': KO_BONES,
            'ko_settle_meshes': ('lo_body', 'lo_props')}


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    """Cores well inside the shells (body_extras are the real body): they leave the voxel union unchanged and give the
    rig's heat-weight proxy something to solve on (every vertex is then weighted by body_weight_regions)."""
    return [Part('core_box', 'box', loc=(0.0, 0.0, 0.29), radius=1.0, scale=(0.2, 0.16, 0.08)),
            Part('core_lid', 'box', loc=(0.0, 0.0, 0.68), radius=1.0, scale=(0.22, 0.17, 0.08))]


def body_extras() -> list:
    return F.objects(fine=True)


def _inside_ring(co: np.ndarray, ab_fn, ins: float, n: float) -> np.ndarray:
    """ρ ≤ 1 inside the shell's ring (semi-axes ab_fn(z) − ins) at each point's height."""
    zs = np.linspace(0.0, 1.0, 201)
    A = np.array([ab_fn(float(z)) for z in zs])
    a = np.interp(co[:, 2], zs, A[:, 0]) - ins
    b = np.interp(co[:, 2], zs, A[:, 1]) - ins
    return (np.abs(co[:, 0] / np.maximum(a, 1e-3)) ** n + np.abs(co[:, 1] / np.maximum(b, 1e-3)) ** n) ** (1.0 / n)


def _inside_lid(co: np.ndarray) -> np.ndarray:
    """ρ ≤ 1 inside the lid's hollow grown by half a wall (its inner surface and the air in it)."""
    zs = np.linspace(F.Z_LB - 0.01, F.LID_SPRING + F.LID_RZ - F.LID_WALL, 301)
    A = np.array([F.lid_inner(float(z)) for z in zs])
    a = np.interp(co[:, 2], zs, A[:, 0], right=0.0) + 0.5 * F.LID_WALL
    b = np.interp(co[:, 2], zs, A[:, 1], right=0.0) + 0.5 * F.LID_WALL
    cy = A[0, 2]
    rho = (np.abs(co[:, 0] / np.maximum(a, 1e-3)) ** F.LID_N + np.abs((co[:, 1] - cy) / np.maximum(b, 1e-3)) ** F.LID_N) ** (1.0 / F.LID_N)
    return np.where(co[:, 2] > zs[-1] + 0.5 * F.LID_WALL, 9.0, rho)


def leg_dist(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The distance to the nearest post's axis (z from 0 to its top) and which post (index into F.LEGS)."""
    d = np.full(len(co), np.inf)
    which = np.zeros(len(co), np.int64)
    for i, key in enumerate(F.LEGS):
        dd, _t = N.seg_dist(co, F.leg_axis(key, 0.0), F.leg_axis(key, 0.25))
        closer = dd < d
        d = np.where(closer, dd, d)
        which = np.where(closer, i, which)
    return d, which


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    lid = z > F.Z_SEAM
    ld, _w = leg_dist(co)
    leg = (z < F.Z_BOT + 0.03) & (ld < 0.105)
    box_in = (~lid) & (z > F.FLOOR_Z - 0.004) & (_inside_ring(co, F.box_ab, 0.5 * F.WALL, F.BOX_N) < 1.0)
    lid_in = lid & (_inside_lid(co) < 1.0)
    eye_d = np.minimum(np.linalg.norm(co - F.eye_frame(1)[0], axis=1), np.linalg.norm(co - F.eye_frame(-1)[0], axis=1))
    brow = lid & (np.abs(z - F.BROW['z'] - 0.012) < 0.04) & (np.abs(np.abs(x) - F.BROW['x']) < 0.075) & (y < -0.1)
    face = lid & (y < -0.2) & (z < 0.83) & (np.abs(x) < 0.27)
    return {'lid': lid, 'leg': leg, 'inside': box_in | lid_in, 'box_in': box_in, 'lid_in': lid_in, 'eye_d': eye_d,
            'brow': brow, 'face': face}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """The eye sockets and the brows keep their shape; the interior gives the most up."""
    z = zones(co)
    keep = 0.75 * (z['eye_d'] < 0.1) + 0.6 * z['brow']
    return np.clip(keep, 0, 1)


def texel_k(fc: np.ndarray) -> np.ndarray:
    """The face most, the outside as usual, the hollows (dark, half hidden) far less."""
    z = zones(fc)
    k = np.ones(len(fc))
    k = np.where(z['face'], 1.45, k)
    k = np.where(z['eye_d'] < 0.1, 1.7, k)
    k = np.where(fc[:, 2] < F.Z_BOT + 0.012, 0.85, k)          # round 2: the ko shows the underside
    k = np.where(z['inside'], 0.55, k)              # round 3: the open lid shows its hollow
    return k


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The box rigid on `hips`, the lid rigid on `head`: two shells, a hard split at the gap (round 2: the legs are rigid
    props, lootlid_legs.py)."""
    lid = co[:, 2] > F.Z_SEAM
    return [U.rigid(~lid, 'hips'), U.rigid(lid, 'head')]


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    from monsters.breeds import lootlid_hoard as H
    return H.prop_weight_regions(co, attr, names)


# ----------------------------------------------------------------------------- props
def build_props(high: bool, quick: bool) -> list:
    from monsters.breeds import lootlid_hoard as H
    from monsters.breeds import lootlid_legs as L
    from monsters.breeds import lootlid_trim as T
    return T.build(high, quick) + H.build(high, quick) + L.build(high)


def preview_prop_colour(name: str):
    if name.startswith('tongue'):
        return PALETTE['tongue']
    if name.startswith('lining'):
        return '#4A3020'
    if name.startswith('legs'):
        return PALETTE['body']
    return PALETTE['accent']


# ----------------------------------------------------------------------------- eyes
EYE_R = F.EYE_R
EYE_SHAPE = (1.0, 0.97)
EYE_DEPTH = 0.45                           # the lens's bulge, × EYE_R
EYE_SINK = 0.0065                          # the lens's base plane behind the lid's surface


def eye_frame(s: int):
    c, xax, yax, look = F.eye_frame(s)
    return Vector(c), Vector(xax), Vector(yax), Vector(look)


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * EYE_SINK) @ m


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    """A glossy lens: a cap of a sphere in the wooden socket (its rim hides the lens's edge)."""
    bm = bmesh.new()
    seg = 56 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * EYE_SHAPE[0], v.co.y * EYE_R * EYE_SHAPE[1], v.co.z * EYE_R * EYE_DEPTH))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / np.array([EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1], EYE_R * EYE_DEPTH]))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


LASH_Y = -0.12                             # the closed lid's lash line, × EYE_R below the eye's centre


def blink_pivot(s: int):
    """The lens squashes onto the lash line of the wooden eyelid under it and sinks into it."""
    c, _xax, yax, look = eye_frame(s)
    return c + yax * (EYE_R * LASH_Y) - look * EYE_SINK, yax, look


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    from monsters.breeds import lootlid_paint as PT
    return PT.eye_material(name, rough_pass, pal or PALETTE)


# ----------------------------------------------------------------------------- the high source and the paint
def carve(hi_body) -> None:
    from monsters.breeds import lootlid_wood as W
    W.carve(hi_body)


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import lootlid_paint as PT
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import lootlid_paint as PT
    return PT.body_material(name, attr, pal, marks)


def prop_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import lootlid_paint as PT
    return PT.prop_material(name, attr, pal, marks)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import lootlid_paint as PT
    return PT.preview_colours(co, vn)


REVIEW = {'centre': (0.0, 0.0, 0.45), 'size': 1.32, 'head': ((0.0, -0.3, 0.63), 0.56),
          # round 2: the hero's open idle, the cast (lid flung wide), the happy idle and win, on both review sheets
          'clips': [('idle', 0.25), ('cast', 0.6), ('idle_happy', 0.3), ('win', 0.6),
                     # polish pass: the legs' extreme frames (hit_heavy's knock, the dash's widest stride, ko's splay)
                     ('hit_heavy', 0.31), ('dash', 0.45), ('ko', 0.86)]}
