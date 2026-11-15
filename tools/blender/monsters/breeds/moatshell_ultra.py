"""Moatshell at the Art 2.1 Ultra tier (chatgpt/monsters/19-moatshell; CONTENT entry 4): a stocky tortoise whose shell
is a tiny sandstone castle keep, on the shelled plan (plans/shelled.py; RECIPE.md "Shelled plan").

    npm run art:shape -- moatshell
    tools/blender/slot.sh npm run art:ultra -- moatshell --blender > tools/blender/out/moatshell-build1.log 2>&1 &

Size (decided Nov 14; FOR-CLAUDE-CODE §2: the size line sets the size, the pictures the proportions): HEIGHT_UNITS 165
→ 1.10 m to the flag's finial; 1.20 m nose to tail (the pictures' length; the card's "1.5 × Puddlepup's length" does not
apply).

The parts:
  - the body (lo_body): a big round head with a beak-like snout, heavy sleepy lids and wide cheeks, a short thick neck
    with a cream throat, four pillar legs on flat feet with four big cream nails, the cream plastron, a short pointed
    tail; leathery skin in pebbly scales (moatshell_skin.py);
  - the keep (lo_props, rigid on `hips`; the flag on its own three-bone chain): moatshell_castle.py / moatshell_keep.py;
  - the eyes: glossy lenses, brown irises, the upper lid painted across the top third (half-lidded and wise).
Colours (CONTENT): shell and skin #C9A66B, belly plate #E8D4A8, flag #3AA6A1, brick details #9A5B3C, eyes #2B2B2B.
Derived (CONTENT has none; from the palette, moatshell_paint.py): the moss, the door's and the pole's wood, the iron
straps, the brown iris and the off-white of the eye.
Porcelain Moatshell (secrets.ts, variants.ts): white china #F4F7FA shell and skin, #FFFFFF belly, blue #2F5D8A flowers,
vines and flag; the brick voussoirs, the door, the pole and the eyes keep their usual colours; glossy (VARIANT_ORM).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from monsters.breeds import moatshell_castle as KC
from monsters.breeds import moatshell_keep as KP
from monsters.breeds import moatshell_noise as N

ID = 'moatshell'
LOOK = 'moatshell-ultra'
PLAN = 'shelled'
HEIGHT_UNITS = 165
PALETTE = {'body': '#C9A66B', 'belly': '#E8D4A8', 'accent': '#3AA6A1', 'eye': '#2B2B2B'}
BRICK_HEX = '#9A5B3C'
VARIANTS = {'porcelain-moatshell': {'body': '#F4F7FA', 'belly': '#FFFFFF', 'accent': '#2F5D8A', 'eye': '#2B2B2B'}}
VARIANT_ORM = {'porcelain': {}}            # glossy china: its own roughness and coat
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 42000
VOXELS = {'hi': 0.0027}                   # round 1: a finer high source, so the small head scales dome
ATLAS_STRIP = 0
NORMAL_SCALE = 1.1                         # the bricks' grooves and the scales want about full strength (stone breeds 1.0-1.2)
BODY_SHEEN = 0                             # stone and leathery skin: no fur sheen
ATLAS_DENSITY = {'lo_eyes': 1.4}
LITE_PROPS_TRIS = 5500                     # the keep is the signature: keep it legible in the Lite copy
AO_FLOOR = 0.3
AO_SOFTEN = 1.0
SOCKET_POINTS = {'socket_shell': ('hips', (0.0, 0.0, 0.89))}       # the turret's volley leaves the tower's top
FACE_NOTE = ('Baked face: a big round tortoise head with a cream beak-like snout, a small closed smile, wide cheeks and '
             'heavy sleepy upper lids painted across the top third of each glossy brown-eyed lens (half-lidded, wise). '
             'Blinking scales the blink bones: each lens squashes and sinks, showing the closed lid sculpted under it.')
BLINK_CLOSED = (0.74, 0.04, 0.2)

# ----------------------------------------------------------------------------- proportions (2-turnaround; metres)
HIP = (0.0, 0.0, 0.42)
CHEST = (0.0, -0.29, 0.37)
NECK = [(0.0, -0.27, 0.33), (0.0, -0.38, 0.4), (0.0, -0.47, 0.48)]
HEAD_C = Vector((0.0, -0.525, 0.595))
HEAD_R = 0.135
HEAD_TIP = (0.0, -0.715, 0.565)
JAW = {'head': (0.0, -0.575, 0.505), 'tail': (0.0, -0.69, 0.492)}
TAIL = [(0.0, 0.35, 0.27), (0.0, 0.45, 0.235), (0.0, 0.52, 0.243)]
# round 2: the front legs hang from the shell (on `chest` their roots slid back with every tuck and tore the shoulder skin)
LEG_F = {'hip': (0.2, -0.29, 0.33), 'knee': (0.248, -0.335, 0.205), 'ankle': (0.25, -0.35, 0.075), 'toe': (0.25, -0.46, 0.03)}
LEG_B = {'hip': (0.19, 0.16, 0.32), 'knee': (0.232, 0.183, 0.2), 'ankle': (0.232, 0.195, 0.075), 'toe': (0.232, 0.085, 0.03)}
LEGS = [LEG_F, LEG_B]
TORSO = ((0.0, 0.0, 0.33), (0.34, 0.37, 0.2))          # round 1: inside the rampart all round (it bulged out at the back)
PLASTRON = ((0.0, -0.01, 0.245), (0.285, 0.34, 0.115))  # rounder: no flat lip under the chest
BIB = ((0.0, -0.27, 0.32), (0.2, 0.12, 0.15))
CRANIUM = ((0.0, -0.535, 0.6), (0.148, 0.146, 0.117))     # round 2: an egg, longer front to back
FACEPLATE = ((0.0, -0.575, 0.565), (0.14, 0.088, 0.098))
JOWL = ((0.0, -0.553, 0.54), (0.152, 0.1, 0.084))
# round 1: a broad, flatter muzzle blending into the cheeks, with a small hooked tip (no bulb, no ridge between the eyes)
SNOUT = ((0.0, -0.65, 0.54), (0.082, 0.075, 0.05))       # round 2: jutting forward as a beak
HOOK = ((0.0, -0.709, 0.516), (0.042, 0.015, 0.012))      # polish: a broad flat hooked lip (a round knob read as a pug nose)
CHIN = ((0.0, -0.6, 0.487), (0.09, 0.072, 0.046))
EYE_C = {s: Vector((0.093 * s, -0.652, 0.598)) for s in (1, -1)}
EYE_R = 0.036
EYE_SHAPE = (1.0, 0.92)
EYE_DEPTH = (0.45, 0.30)
EYE_LOOK = (0.36, -1.0, 0.1)
TOE_ANG = (-42.0, -14.0, 14.0, 42.0)
smooth = N.smooth


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


def foot_centre(lg: dict, s: int) -> tuple:
    a = lg['ankle']
    return (a[0] * s, a[1] - 0.022, 0.048)


def toe_centres(lg: dict, s: int) -> list[tuple]:
    fx, fy, _fz = foot_centre(lg, s)
    out = []
    for ang in TOE_ANG:
        a = math.radians(ang)
        out.append((fx + 0.092 * math.sin(a) * s, fy - 0.092 * math.cos(a) - 0.012, 0.03))
    return out


def rig_p() -> dict:
    return {'hip': HIP, 'chest': CHEST, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R, 'neck': NECK, 'head_tip': HEAD_TIP,
            'jaw': JAW, 'jaw_open': True, 'legs': LEGS, 'tail': TAIL, 'shell_top': (0.0, 0.0, 0.78),
            'chains': [{'name': 'flag', 'kind': 'flag', 'parent': 'hips', 'points': KC.flag_points()}],
            'cast_style': 'brace', 'strike_yaw': 20.0, 'ko_style': 'roll', 'ko_roll': 87.0,
            'tuck': 1.0, 'tuck_depth': 0.11, 'shell_turn': True, 'ko_settle_meshes': ('lo_body', 'lo_props'),   # the rampart lies on the ground in ko
            # round 1 (review): the card's attack: tucked low and braced, the keep kicking back and up as the volley
            # leaves the tower (the plan's launch), the flag whipping back; a real hop in win
            'strike_style': 'launch', 'launch_pitch': -9.0, 'hop': 0.9,
            'clip_bones': {'strike': {'hips': [(0.44, 0.76, (-5, 0, 0), (0, 0, 0.03))], 'flag.1': [(0.46, 0.84, (0, 0, -20))],
                                      'flag.2': [(0.48, 0.88, (0, 0, -18))], 'flag.3': [(0.5, 0.92, (0, 0, -16))]},
                           # hit_heavy rocks back onto the shell's back edge (the plan also lifts it: take that back)
                           'hit_heavy': {'hips': [(0.0, 0.62, (0, 0, 0), (0, 0, -0.05))],
                                         # polish: most of the plan's tuck taken back, so the throat creases above the
                                         # rigid plate instead of folding under it in flat cards
                                         'chest': [(0.0, 0.62, (0, 0, 0), (0, -0.06, 0.007))]},
                           'hit': {'chest': [(0.0, 0.8, (0, 0, 0), (0, -0.045, 0.005))]},
                           # ko: the head lolls out of the shell instead of pressing into it
                           'ko': {'chest': [(0.35, 1.65, (0, 0, 0), (0, -0.045, 0))]}},
            'hit_heavy_bones': {'hips': (0, 12, 0)},
            # ko: the legs drawn in toward the shell (the plan's splay left them standing out like pegs)
            'ko_bones': {'leg1.L': (0, 16, 0), 'leg1.R': (0, -16, 0), 'leg2.L': (0, 16, 0), 'leg2.R': (0, -16, 0),
                         'shin1.L': (0, 24, 0), 'shin1.R': (0, -24, 0), 'shin2.L': (0, 24, 0), 'shin2.R': (0, -24, 0),
                         'flag.1': (14, 0, 0)}}


# ----------------------------------------------------------------------------- the body
def _ell(name: str, spec, mirror: bool = False) -> Part:
    c, r = spec
    return Part(name, 'sphere', loc=c, radius=1.0, scale=r, mirror=mirror)


def all_parts() -> list[Part]:
    ps = [_ell('torso', TORSO), _ell('bib', BIB),          # round 2: no separate plastron (its edge showed as a flat lip)
          Part('neck', 'tube', loc=(0.0, -0.24, 0.3), to=(0.0, -0.48, 0.48), radius=0.122, r2=0.108),
          _ell('cranium', CRANIUM), _ell('face', FACEPLATE), _ell('jowl', JOWL), _ell('snout', SNOUT),
          _ell('hook', HOOK),
          _ell('chin', CHIN),
          Part('tail', 'tube', loc=TAIL[0], to=TAIL[1], radius=0.066, r2=0.036),
          Part('tailtip', 'tube', loc=TAIL[1], to=(0.0, 0.528, 0.247), radius=0.036, r2=0.007)]
    for tag, s in (('L', 1), ('R', -1)):
        for k, lg in enumerate(LEGS):
            ps.append(Part(f'thigh{k}{tag}', 'tube', loc=_m(lg['hip'], s), to=_m(lg['knee'], s), radius=0.1, r2=0.103))
            a = lg['ankle']
            ps.append(Part(f'shin{k}{tag}', 'tube', loc=_m(lg['knee'], s), to=(a[0] * s, a[1], 0.118), radius=0.103, r2=0.114))
            ps.append(Part(f'foot{k}{tag}', 'sphere', loc=foot_centre(lg, s), radius=1.0, scale=(0.12, 0.13, 0.052)))
            for j, tc in enumerate(toe_centres(lg, s)):
                ps.append(Part(f'toe{k}{j}{tag}', 'sphere', loc=tc, radius=1.0, scale=(0.031, 0.03, 0.027)))
    return ps


def toe_dist(co: np.ndarray) -> np.ndarray:
    """Metres-ish inside (< 0) each toenail's ellipsoid."""
    d = np.full(len(co), np.inf)
    for s in (1, -1):
        for lg in LEGS:
            for tc in toe_centres(lg, s):
                d = np.minimum(d, N.ell_sdf(co, tc, (0.034, 0.035, 0.035)))
    return d


def leg_dist(co: np.ndarray) -> np.ndarray:
    d = np.full(len(co), np.inf)
    for s in (1, -1):
        for lg in LEGS:
            d = np.minimum(d, N.poly_dist(co, [_m(lg['hip'], s), _m(lg['knee'], s), _m(lg['ankle'], s)]))
    return d


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    head = N.ell_sdf(co, CRANIUM[0], (0.2, 0.2, 0.17)) < 0
    face = head & (y < -0.6)
    muzzle = N.ell_sdf(co, SNOUT[0], (0.1, 0.1, 0.085)) < 0
    eye_d = np.minimum(np.linalg.norm(co - np.array(EYE_C[1]), axis=1), np.linalg.norm(co - np.array(EYE_C[-1]), axis=1))
    toes = smooth(0.006, -0.004, toe_dist(co))
    feet = (z < 0.1) & (leg_dist(co) < 0.2)
    # the cream plastron underneath, the bib up the chest and the throat down the neck's front
    ld = leg_dist(co)
    under = (z < 0.24) & (z > 0.1) & (ld > 0.122) & (N.ell_sdf(co, TORSO[0], TORSO[1]) < 0.02) & (y > -0.42) & (y < 0.38)
    # the plastron's rim all round below the skirt (2-turnaround back: cream between the hind legs, round the tail)
    rim = (z < 0.275) & (z > 0.1) & (ld > 0.128) & (N.ell_sdf(co, TORSO[0], TORSO[1]) < 0.015) & (N.poly_dist(co, TAIL) > 0.075)
    under = under | rim
    bib = (y < -0.25) & (np.abs(x) < 0.15) & (z < 0.43) & (leg_dist(co) > 0.128)
    neck_ax = N.seg_dist(co, (0.0, -0.24, 0.3), (0.0, -0.5, 0.5))
    # round 2: a narrower throat (scales on the neck's sides), fading out softly under the chin (no hard seam)
    tw = ((neck_ax[0] < 0.14) & ((z - (0.3 + (0.5 - 0.3) * neck_ax[1])) < -0.01) & (y < -0.3)) * smooth(0.068, 0.045, np.abs(x)) * smooth(0.95, 0.72, neck_ax[1])
    throat = tw > 0.5
    belly = under | bib | throat
    cream = np.maximum((under | bib).astype(np.float64), tw)
    return {'face': face, 'muzzle': muzzle, 'eye_d': eye_d, 'toes': toes, 'paw': feet.astype(float), 'belly': belly,
            'head': head, 'under': under, 'bib': bib, 'throat': throat, 'cream': cream, 'throat_w': tw}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    keep = 1.0 * z['face'] + 1.0 * z['muzzle'] + (z['eye_d'] < 0.07) + 0.35 * z['toes']
    return np.clip(keep, 0, 1)


def texel_k(fc: np.ndarray) -> np.ndarray:
    """The head and face get the most texels, the legs and neck the usual, the plastron less; the torso's top inside
    the keep (never seen) almost none."""
    z = zones(fc)
    k = np.ones(len(fc))
    k = np.where(z['head'], 1.5, k)
    k = np.where(z['face'] | z['muzzle'], 1.9, k)
    k = np.where(z['under'], 0.7, k)
    hidden = (N.ell_sdf(fc, TORSO[0], TORSO[1]) < 0.02) & (fc[:, 2] > 0.4) & (np.hypot(fc[:, 0], fc[:, 1]) < 0.33)
    k = np.where(hidden, 0.15, k)
    return k


def calm_group(bone: str) -> str | None:
    """CLIP_CALM groups: the jaw (the beak opens less than the plan's), the flag, the tail and the neck."""
    if bone == 'jaw':
        return 'jaw'
    g = bone.split('.')[0]
    return g if g in ('flag', 'tail', 'neck') else None


CLIP_CALM = {'*': {'jaw': 0.6}, 'win': {'jaw': 0.9}}


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The shell's body (torso, plastron, the bib's lower half) rigid on `hips`; the bib's top and the neck's root
    blend onto `chest` (it slides back in a tuck); the tail by its chain; the lower beak on `jaw` (the mouth line and
    below, never the snout); the head, neck and legs keep their heat weights."""
    from monsters.breeds import moatshell_skin as SK
    regs = []
    ld = leg_dist(co)
    # round 2: the whole plastron (the torso's underside and the bib up the chest) rides the shell rigidly; the neck
    # leaves it through a soft collar (hips → chest over its first 6 cm), so a tuck or a lifted head folds the throat
    # under the bib's top edge instead of tearing the plates
    torso = (N.ell_sdf(co, TORSO[0], TORSO[1]) < 0.014) | (N.ell_sdf(co, BIB[0], BIB[1]) < 0.012)
    nd, nt = N.seg_dist(co, (0.0, -0.24, 0.3), (0.0, -0.5, 0.5))
    legs = (ld < 0.118) & (co[:, 2] < 0.31)
    neck = (nd < 0.135) & (nt > 0.18) & ~legs
    shell = torso & ~neck & ~legs
    regs.append(U.rigid(shell, 'hips'))
    head = (N.ell_sdf(co, CRANIUM[0], CRANIUM[1]) < 0.012) | (N.ell_sdf(co, JOWL[0], JOWL[1]) < 0.012)
    collar = (nd < 0.15) & ~legs & ~shell & ~head
    if collar.any():
        pts = [(0.0, -0.21, 0.28), NECK[0], NECK[1], NECK[2]]
        regs.append((collar, U.chain_weights(co[collar], pts, ['chest', 'neck.1', 'neck.2'], 'hips', fade=(0.3, 0.1))))
    tl = (N.poly_dist(co, TAIL) < 0.07) & (co[:, 1] > 0.355) & ~legs
    regs.append((tl, U.chain_weights(co[tl], TAIL, ['tail.1', 'tail.2'], 'hips')))
    jw = SK.jaw_mask(co)
    if jw.any():
        w = jw[jw > 0]
        regs.append((jw > 0, {'jaw': w, 'head': 1.0 - w}))
    return regs


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """The keep rides the shell rigidly; the flag follows its three-bone chain from the pole."""
    flag = attr('cpart') > 0.5
    lids = attr('ck') > 8.5
    regs = [U.rigid(~flag & ~lids, 'hips'), U.rigid(lids, 'head')]
    if flag.any():
        regs.append((flag, U.chain_weights(co[flag], KC.flag_points(), ['flag.1', 'flag.2', 'flag.3'], 'hips',
                                           fade=(0.02, -0.04))))
    return regs


# ----------------------------------------------------------------------------- props: the keep
def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    from monsters.breeds import moatshell_lids as LD
    return KP.build(high, quick) + LD.build(high)


def preview_prop_colour(name: str):
    return PALETTE['body']


# ----------------------------------------------------------------------------- eyes
def eye_frame(s: int):
    c = EYE_C[s]
    look = Vector((EYE_LOOK[0] * s, EYE_LOOK[1], EYE_LOOK[2])).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


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
    S.add_attr(ob, 'eyeuv', co / np.array([EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1], EYE_R * EYE_DEPTH[0]]))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


LID_LASH, LID_DROP, LID_W = 0.02, 0.16, 0.94


def blink_pivot(s: int):
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    from monsters.breeds import moatshell_paint as PT
    return PT.eye_material(name, rough_pass, pal or PALETTE)


# ----------------------------------------------------------------------------- the high source
def carve(hi_body) -> None:
    from monsters.breeds import moatshell_skin as SK
    SK.carve(hi_body)


def carve_low(lo_body) -> None:
    from monsters.breeds import moatshell_skin as SK
    SK.carve_low(lo_body)


# ----------------------------------------------------------------------------- paint
def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import moatshell_paint as PT
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import moatshell_paint as PT
    return PT.body_material(name, attr, pal, marks)


def prop_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import moatshell_paint as PT
    return PT.prop_material(name, attr, pal, marks)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import moatshell_paint as PT
    return PT.preview_colours(co, vn)


REVIEW = {'centre': (0.0, -0.08, 0.55), 'size': 1.55, 'head': ((0.0, -0.6, 0.58), 0.48)}
