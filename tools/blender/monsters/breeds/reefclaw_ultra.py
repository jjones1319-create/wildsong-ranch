"""Reefclaw at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md, the
"Shelled plan" section, its crab option).

A coral-pink crab knight, steadfast and a little formal (chatgpt/monsters/20-reefclaw/, CONTENT 18): a round glossy
carapace dome with a spiked crown ring and pale tubercles, overhanging a big peach belly of plastron plates; a smile on
the shell's front under two eye stalks, each eye a big glossy ball in a cup under a little knightly visor; aqua
barnacle clusters as shoulder armour; six chunky walking legs; on its right the big claw whose fixed finger is a
porous branching coral column, on its left a small claw.

- The shell: reefclaw_form.py (primitives, layout, noise) and reefclaw_shell.py (the carving). It is one rigid piece
  on `hips` (a crab's carapace never bends).
- The limbs (rigid segments on their bones, so no joint stretches): reefclaw_limbs.py; the barnacles, the stalks, the
  eye cups with the closed-lid balls and the visors: reefclaw_bits.py; both built with reefclaw_geo.py.
- Paint: reefclaw_paint.py (per vertex) and reefclaw_shade.py (the per-pixel flecks and the eyes).

Part counts (the card wins, FOR-CLAUDE-CODE section 2): six walking legs (three a side, as every picture shows; CONTENT
says "biped" for the plan family only), two claws (the big coral one on its right, as 1-hero and 2-turnaround front
show), two eye stalks with visors. The face is baked (one expression: the calm closed smile, eyes open); the mouth
never opens. Size: about 1.2 x Puddlepup (PROMPTS.md): HEIGHT_UNITS 180, the raised coral claw's top at 1.18 m.
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import reefclaw_bits as B
from monsters.breeds import reefclaw_form as F
from monsters.breeds import reefclaw_limbs as L
from monsters.breeds import reefclaw_paint as P
from monsters.breeds import reefclaw_relief as RL
from monsters.breeds import reefclaw_shade as SH
from monsters.breeds import reefclaw_shell as SL

ID = 'reefclaw'
LOOK = 'reefclaw-ultra'
PLAN = 'shelled'
HEIGHT_UNITS = 180

# CONTENT 18: shell coral / belly peach / armour aqua (shell shadow) / eyes
PALETTE = {'body': '#F07C6E', 'belly': '#FFD9CF', 'accent': '#BDE7E0', 'eye': '#1F2A44', 'shell': '#B85B4E'}
# src/art/monster/variants.ts (secrets.ts: "deep-sea blue coral"); its picture: the shell, legs, claws and coral deep
# blue with darker navy shading, lighter blue belly plates, pink barnacles, small glowing pink spots and coral tips
# (deep-sea lights), pale blue eyes. The navy shading, the pink tips and the spots are derived from its palette.
VARIANTS = {'abyss-reefclaw': {'body': '#1C3F6E', 'belly': '#2E6AA8', 'accent': '#F26B8A', 'eye': '#BFE3FF',
                               'shell': C.shade_hex('#1C3F6E', 0.6, cool=0.02), 'tip': C.mix_hex('#F26B8A', '#FFFFFF', 0.2),
                               'spot': C.mix_hex('#F26B8A', '#FFFFFF', 0.1), 'glows': True,
                               'mouth': C.mix_hex('#2E6AA8', '#FFFFFF', 0.45)}}     # polish: a light smile on the navy
# round 2 (review): the spots glow brighter and steady (the per-cell twinkle showed as square texels), and the navy shell
# has its own roughness and a lower coat (its top read chrome-like)
VARIANT_ORM = {'abyss': {'glow': {'strength': 3.2, 'tint': None, 'twinkle': 0.0}}}

ATLAS_STRIP = 0
BODY_TRIS = 32000
VOXELS = {'hi': 0.0025, 'hi_quick': 0.005, 'lo': 0.0055}
ATLAS_DENSITY = {'lo_eyes': 1.5}
NORMAL_SCALE = 1.5                  # round 3 (review: still a satin cap): the pebbles and the pores read as relief
BODY_SHEEN = 0.0                    # a glossy shell: the fur sheen would read as felt
LITE_PROPS_TRIS = 7000              # the legs, the claws, the coral and the barnacles are the look
AO_FLOOR = 0.55                     # polish: no dark smear by the arm roots; the belly's shade stays peach
AO_SOFTEN = 1.2
BLINK_CLOSED = (0.9, 0.05, 0.85)    # the lens squashes inside the closed-lid ball
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
EYE_PARENTS = {'L': 'stalkL.2', 'R': 'stalkR.2'}
MOUTH_SOCKET = (0.0, -0.245, 0.59)

all_parts = F.all_parts
carve = SL.carve
carve_low = SL.carve_low
zones = SL.zones
decimate_keep = SL.decimate_keep
body_material = SH.body_material
prop_material = SH.prop_material


def texel_k(co: np.ndarray) -> np.ndarray:
    """The shell's front (the face) a little denser, the belly's underside and the back's bottom sparser."""
    k = np.ones(len(co))
    k = np.where((co[:, 1] < -0.12) & (co[:, 2] > 0.55), 1.3, k)
    k = np.where(co[:, 2] < 0.2, 0.7, k)
    return k


# ----------------------------------------------------------------------------- the eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    """The whole eyeball as the lens (the cup hides its back): white, the iris on its front."""
    c, x, u, d = B.eye_frame(s)
    bm = bmesh.new()
    seg = 48 if high else 20
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=B.EYE_R)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    loc = np.array([v.co[:] for v in me.vertices])
    M = np.stack([x, u, d], axis=1)                  # local x across, y up, z out (the sphere's own axes)
    world = c[None] + loc @ M.T
    me.vertices.foreach_set('co', world.astype(np.float32).ravel())
    me.update()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    S.add_attr(ob, 'eyeuv', loc / B.EYE_R)
    S.add_attr(ob, 'eye_side', np.full(len(loc), float(s)))
    return ob


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    return SH.eye_material(name, rough_pass, pal or PALETTE)


def blink_pivot(s: int):
    c, _x, u, d = B.eye_frame(s)
    return Vector(c), Vector(u), Vector(d)


# ----------------------------------------------------------------------------- props and paint
def build_props(high: bool, quick: bool) -> list:
    return RL.objects(high, quick) + B.barnacles(high) + B.arm_sockets(high) + B.eye_parts(high)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    m = SL.preview_masks(co)
    if m is None:
        f = SL.fields(co, vn, False)
        m = {k: f[k] for k in SL.ATTRS}
        return P.body_paint(co, m, PALETTE)['paint']
    return P.body_paint(SL._LAST['co'], m, PALETTE)['paint']


def preview_prop_colour(name: str) -> str:
    if 'barnacle' in name:
        return PALETTE['accent']
    if 'cup' in name:
        return C.mix_hex(PALETTE['body'], PALETTE['belly'], 0.4)
    return PALETTE['body']


def _paint_with_spots(rgb: np.ndarray, spots: np.ndarray, pal: dict) -> np.ndarray:
    k = np.clip(spots, 0, 1)[:, None]
    return rgb * (1 - k) + P.lin(P.colours(pal)['spot'])[None] * k


def _abyss_rough(r: np.ndarray) -> np.ndarray:
    """Abyss's roughness and coat: a little rougher and a third of the coat (the navy shell's top read chrome-like)."""
    out = r.copy()
    out[:, 1] = np.clip(r[:, 1] + 0.22, 0.0, 1.0)              # polish: no white sheen on the navy shell's top
    out[:, 2] = r[:, 2] * 0.12
    return out


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        n = len(ob.data.vertices)
        co = S.attr_array(ob, 'root').astype(np.float64)
        m = {k: (S.attr_array(ob, k).astype(np.float64) if k in ob.data.attributes else np.zeros(n)) for k in SL.ATTRS}
        a = P.body_paint(co, m, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        for vid, var in VARIANTS.items():
            v = P.body_paint(co, m, var)
            glow = v['spots'] if var.get('glows') else np.zeros(n)
            S.set_colour_attr(ob, U.variant_attr(vid, ID), _paint_with_spots(v['paint'], glow, var))
            S.add_attr(ob, f'glow_{U.variant_short(vid, ID)}', glow)
            S.set_colour_attr(ob, f'rough_{U.variant_short(vid, ID)}', _abyss_rough(a['rough']))
    for ob in props:
        a = P.prop_paint(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        for vid, var in VARIANTS.items():
            v = P.prop_paint(ob, var)
            glow = v['glow'] if var.get('glows') else np.zeros(len(v['glow']))
            kind = S.attr_array(ob, 'kind')
            spots = glow * ((kind < 1.5) | (kind > 2.5))
            col = _paint_with_spots(v['paint'], spots * (1 - S.attr_array(ob, 'coral')) if 'coral' in ob.data.attributes else spots, var)
            S.set_colour_attr(ob, U.variant_attr(vid, ID), col)
            S.add_attr(ob, f'glow_{U.variant_short(vid, ID)}', spots)
            S.set_colour_attr(ob, f'rough_{U.variant_short(vid, ID)}', _abyss_rough(a['rough']))


# ----------------------------------------------------------------------------- the rig (plans/shelled.py, crab option)
def _t(p) -> tuple:
    return tuple(round(float(v), 4) for v in p)


def claws_spec() -> dict:
    out = {}
    for tag in ('L', 'R'):
        a = L.ARMS[tag]
        c = L.SMALL if tag == 'L' else L.BIG
        tip = c['fixed'][-1]
        out[tag] = {'shoulder': a['shoulder'], 'elbow': a['elbow'], 'wrist': a['wrist'], 'tip': _t(tip),
                    'finger': (_t(c['hinge']), _t(c['dactyl'][-1])),
                    # the big claw's movable finger opens toward the body; the small claw's lifts (it faces forward)
                    'open_axis': (0.0, 1.0, 0.0) if tag == 'R' else (-1.0, 0.0, 0.0)}
    return out


def stalks_spec() -> dict:
    b, m, t = B.stalk_points(1)
    vh, vt = B.visor_bone(1)
    return {'base': _t(b), 'mid': _t(m), 'tip': _t(t), 'visor': (vh, vt)}


SK = HEIGHT_UNITS / 150.0


def rig_p() -> dict:
    return {
        'hip': F.HIP, 'chest': F.CHEST, 'head_c': (0.0, -0.2, 0.61), 'head_r': 0.12,
        'head_base': (0.0, -0.075, 0.67), 'head_tip': (0.0, -0.22, 0.67), 'head_turn': 0.2,
        'jaw': {'head': (0.0, -0.21, 0.59), 'tail': (0.0, -0.245, 0.585)},
        # round 2 (opt-in plan fix): the shell really pitches, rolls and turns as each clip asks (plans/shelled.py)
        'shell_turn': True,
        'shell_top': F.SHELL_TOP,
        'legs': [{'hip': lg['hip'], 'knee': lg['knee'], 'ankle': lg['ankle']} for lg in L.LEGS],
        'claws': claws_spec(), 'big_claw': 'R', 'stalks': stalks_spec(), 'rigid_legs': True,
        'strike_style': 'claw', 'cast_style': 'raise', 'ko_style': 'roll', 'ko_roll': 160.0,
        'hop': 0.7, 'strike_yaw': 12.0,
        # the claws stand upright at rest (2-turnaround): a raise lifts them rather than tipping them over the face
        'claw_keep_up': 0.75,
        # the claw strike (5-poses attack; round 2, review: a wide horizontal arc with a body twist): the wind-up rears the
        # coral claw high and a little back, then the claw tips out to level at the elbow and the arm sweeps it round
        # across the front at the target, the shell twisting into it (the plan's yaw, now that the shell turns)
        'strike_windup_bones': {'arm.R': (0.0, -46.0, 20.0), 'forearm.R': (0.0, 46.0, 0.0)},
        'strike_bones': {'arm.R': (0.0, 5.0, 55.0), 'claw.R': (0.0, -75.0, 0.0)},
        # round 3 (review: the stalks folded back and showed the backs of the eyes): they stay forward while the lids
        # squeeze shut
        'hit_bones': {'hips': (-14.0, 0.0, 6.0), 'stalkL.1': (58.0, 0.0, 0.0), 'stalkR.1': (58.0, 0.0, 0.0),
                      'stalkL.2': (20.0, 0.0, 0.0), 'stalkR.2': (20.0, 0.0, 0.0)},
        'hit_heavy_bones': {'arm.R': (0.0, -30.0, 0.0), 'forearm.R': (0.0, 30.0, 0.0), 'stalkL.1': (78.0, 0.0, 0.0),
                            'stalkR.1': (78.0, 0.0, 0.0), 'stalkL.2': (26.0, 0.0, 0.0), 'stalkR.2': (26.0, 0.0, 0.0)},
        # ko rolls onto its back (the shell's dome on the ground). Its legs and claws are props, so the build's settle
        # measures them too (ko_settle_meshes, opt-in): it pivots over its right legs instead of sinking them through the
        # floor. The big claw tips forward along the roll as it falls (its coral would sweep through the floor), the small
        # one flops out to its left, and the stalks swing forward past level so the eyes lie out in front of the face
        # (the plan folds them back onto the dome's top, the side on the ground)
        'ko_bones': {'arm.R': (90.0, 0.0, 0.0), 'forearm.L': (0.0, 70.0, 0.0),
                     'stalkL.1': (155.0, 15.0, 0.0), 'stalkR.1': (155.0, -15.0, 0.0), 'stalkL.2': (25.0, 0.0, 0.0), 'stalkR.2': (25.0, 0.0, 0.0)},
        'ko_settle_meshes': ('lo_body', 'lo_props', 'lo_eyes'),
        # the legs on the side it rolls onto fold up and in through the middle of the fall (a lower pivot)
        # win and cast raise the claws high: part of the raise moves from the shoulder to the elbow, so the arms pass in
        # front of the barnacle mounds instead of through them; the strike's small claw stays clear of its front leg
        'clip_bones': {'hit': {'hips': [(0.0, 0.85, (0.0, 0.0, 0.0), (0.0, 0.07 / SK, 0.035 / SK))]},
                       'win': {'arm.L': [(-0.5, 1.5, (0.0, 24.0, 0.0))], 'forearm.L': [(-0.5, 1.5, (0.0, -24.0, 0.0))],
                               'arm.R': [(-0.5, 1.5, (0.0, -40.0, 0.0))], 'forearm.R': [(-0.5, 1.5, (0.0, 40.0, 0.0))]},
                       'cast': {'arm.L': [(-0.5, 1.5, (0.0, 38.0, 0.0))], 'forearm.L': [(-0.5, 1.5, (0.0, -38.0, 0.0))],
                                'arm.R': [(-0.5, 1.5, (0.0, -52.0, 0.0))], 'forearm.R': [(-0.5, 1.5, (0.0, 52.0, 0.0))]},
                       'idle_happy': {'arm.R': [(-0.5, 1.5, (0.0, -20.0, 0.0))], 'forearm.R': [(-0.5, 1.5, (0.0, 20.0, 0.0))]},
                       # as the shell twists into the strike, the small claw swings forward with it, clear of its front leg
                       'strike': {'arm.L': [(-0.3, 0.62, (0.0, -8.0, 34.0)), (0.32, 1.3, (0.0, -42.0, -6.0))],
                                  'forearm.L': [(-0.5, 1.5, (0.0, 0.0, 34.0))]},
                       # round 3 (review: the small claw crossed the face like a shush): in every guard it stays held out to
                       # the side at shoulder height, pincer forward (the plan's guard bends its forearm inward)
                       **{c: {'forearm.L': [(-0.5, 1.5, (0.0, 0.0, 34.0))]} for c in ('battle_idle', 'step_fwd', 'step_back',
                                                                                      'strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r')},
                       'ko': {'arm.R': [(0.0, 0.9, (60.0, 0.0, 0.0)), (0.15, 1.0, (0.0, 0.0, 70.0))],
                              'forearm.R': [(0.15, 1.0, (0.0, 0.0, -50.0))],
                              **{f'leg{i}.R': [(0.2, 1.0, (0.0, 50.0, 0.0))] for i in (1, 2, 3)},
                              **{f'shin{i}.R': [(0.2, 1.0, (0.0, -60.0, 0.0))] for i in (1, 2, 3)}}},
    }


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The shell is one rigid piece (the face, the smile and the sockets with it)."""
    return [(np.ones(len(co), bool), {'hips': np.ones(len(co))})]


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """Every piece rides its own bone (reefclaw_limbs / reefclaw_bits `part`); the stalks bend over their two bones."""
    part = np.rint(attr('part')).astype(int)
    regs = [(np.ones(len(co), bool), {'hips': np.ones(len(co))})]
    for s, tag in ((1, 'L'), (-1, 'R')):
        o = 0 if s > 0 else 10
        for i in range(1, len(L.LEGS) + 1):
            regs.append(U.rigid(part == 10 + o + i, f'leg{i}.{tag}'))
            regs.append(U.rigid(part == 30 + o + i, f'shin{i}.{tag}'))
        b = 50 if tag == 'L' else 60
        for k, bone in enumerate(('arm', 'forearm', 'claw', 'pincer'), start=1):
            regs.append(U.rigid(part == b + k, f'{bone}.{tag}'))
        st = part == (81 if s > 0 else 82)
        if st.any():
            regs.append((st, U.chain_weights(co[st], B.stalk_points(s), [f'stalk{tag}.1', f'stalk{tag}.2'], 'head', fade=(0.12, 0.0))))
        regs.append(U.rigid(part == (83 if s > 0 else 84), f'stalk{tag}.2'))
        regs.append(U.rigid(part == (85 if s > 0 else 86), f'visor.{tag}'))
    return regs


CLIP_CALM: dict = {}

FACE_NOTE = ('The face is baked: the smile is painted on the shell\'s front under the stalks and never opens (the jaw is '
             'merged into the head). Each eye is a whole glossy eyeball lens (lo_eyes: white, the navy iris and pupil, two '
             'catchlights) held in a cup at the top of its stalk, under its visor; the blink bones ride the stalks '
             '(EYE_PARENTS). Blinking squashes each lens inside the closed-lid ball behind it (a peach lid with a dark lash '
             'line). The clips\' faces are hints only.')

REVIEW = {'centre': (-0.08, 0.0, 0.55), 'size': 1.6, 'head': ((0.0, -0.12, 0.76), 0.55)}
