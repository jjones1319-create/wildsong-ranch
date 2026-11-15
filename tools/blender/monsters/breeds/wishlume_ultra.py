"""Wishlume at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md, the
"Floater plan" section). The first real breed on plans/floater.py.

A floating paper sky-lantern creature, gentle, dreamy and hopeful (chatgpt/monsters/14-wishlume/): a round lantern of
warm cream paper stretched over ten thin red bamboo ribs, open at the bottom, a warm flame glowing through the paper
from inside; two stubby paper paddle arms with red rims; a red crown with a hanging loop on top; under the opening a
bead and a red silk tassel; big eyes, brows, a small smile and the blush painted on the paper like ink; pressed red
leaves in the paper.

- The shape: wishlume_form.py (measured on 2-turnaround.png) and wishlume_carve.py (the exact profile, the opening's
  inner dome, creases, the paddles' rims).
- The frame, the crown and the tassel: wishlume_props.py (built with wishlume_mesh.py).
- Colours and paint: wishlume_paint.py; the per-pixel bake materials: wishlume_shade.py.

Part counts (the card): two arms, one tassel, no other limbs; the face is painted (no mouth opens: the jaw stays
merged into the head). The crown, its loop and the leaves are in every picture (not on the card's list) and are kept.
Size: about 0.9 x Puddlepup (PROMPTS.md): HEIGHT_UNITS 135; the paper's top (restHeight) 0.835 m, the loop 0.93 m.
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
from lib.surface import smooth
from monsters.breeds import wishlume_carve as K
from monsters.breeds import wishlume_form as F
from monsters.breeds import wishlume_paint as WP
from monsters.breeds import wishlume_props as PR
from monsters.breeds import wishlume_shade as SH

ID = 'wishlume'
LOOK = 'wishlume-ultra'
PLAN = 'floater'
HEIGHT_UNITS = 135

PALETTE = {'body': '#F6E3B4', 'belly': '#FFF2D6', 'accent': '#D94F4F', 'eye': '#3A2A2A', 'glow': '#FFB85C'}
VARIANTS = {'beacon-wishlume': {'body': '#F6F1EA', 'belly': '#FFFFFF', 'accent': '#D9262C', 'eye': '#3A2A2A', 'glow': '#FFB85C',
                                'stripes': True}}

# the inner light (round 3): the paper painted a little darker than lit paper and glowing in its own painted colour
# (cream on top, the lower third toward #FFB85C; the leaves glow red, not rust; a tint made them rust-brown) over all of it, so no side goes grey; strongest in the lower third, the paddles'
# roots, the band over the hoop and the flame inside the opening; least on the face panel; none under the ink.
# `twinkle` 0: steady (the runtime's per-cell twinkle drew a fine square stipple over so much glowing paper).
# Beacon's beam-like glow (the card) is a brighter core, not brighter paper: its paper glows at 0.8 of the base's share,
# tinted #FFB85C so its white bands glow warm, and its red bands hold the light back (true lighthouse red).
GLOW = {'strength': 2.0, 'tint': None, 'twinkle': 0.0}
VARIANT_ORM = {'beacon': {'glow': {'strength': 2.5, 'tint': PALETTE['glow'], 'twinkle': 0.0}}}

ATLAS_STRIP = 0                     # no fur cards, no tuft
BODY_TRIS = 40000
ATLAS_DENSITY = {'lo_eyes': 1.4}
AO_FLOOR = 0.45                     # the opening's inner dome and the rib contacts never bake near black
AO_SOFTEN = 1.5
BODY_SHEEN = 0.0                    # round 2: no sheen (it brightened the outline into a halo)
NORMAL_SCALE = 1.0                  # the paper's creases and fibres at full strength
LITE_PROPS_TRIS = 6000              # the frame and the tassel are the look's signature
BLINK_CLOSED = (0.78, 0.04, 0.2)
MOUTH_SOCKET = (0.0, -0.258, 0.512)
# the heart's beam (the pulse strike) leaves the flame, low in the globe and a little forward (5-poses attack)
SOCKET_POINTS = {'socket_core': (0.0, -0.05, 0.45)}

all_parts = F.all_parts
zones = F.zones
decimate_keep = F.decimate_keep
carve = K.carve
carve_low = K.carve_low
body_material = SH.body_material
glow_material = SH.glow_material
prop_material = SH.prop_material
eye_material = SH.eye_material
colours = WP.colours


def texel_k(co: np.ndarray) -> np.ndarray:
    """lo_body's texel density per face: the face 1.6, the paddles 1.1, the crown's hidden top and the inner dome 0.6."""
    z = F.zones(co)
    k = np.ones(len(co))
    k = np.where(z['arm'] > 0.5, 1.3, k)                  # round 3: crisper leaves on the paddles
    k = np.where(z['face'], 1.6, k)
    k = np.where(z['dish'] | (co[:, 2] > F.TOP_Z - 0.02), 0.6, k)
    return k


# ----------------------------------------------------------------------------- the eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    """Round 3: the eye is a near-round patch laid on the paper itself (the oval in the eye's tangent plane, each point
    carried onto the paper along the globe's radius), bulging EYE_DOME at its centre and tucked EYE_SINK under the paper
    at its rim, so the whole oval shows and it sits flush in profile (the dome before sank under the paper on the nose
    side, a straight cut through the iris, and stood out on the other like a button)."""
    c, xa, ya, lk = F.eye_frame(s)
    ax, ay = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1]
    rings, seg = (24, 72) if high else (8, 36)
    verts, uvw = [np.array(c[:])], [(0.0, 0.0, 1.0)]
    for i in range(1, rings + 1):
        r = i / rings
        for j in range(seg):
            a = 2 * np.pi * j / seg
            verts.append(np.array((c + xa * (ax * r * np.cos(a)) + ya * (ay * r * np.sin(a)))[:]))
            uvw.append((r * np.cos(a), r * np.sin(a), 1.0 - r * r))
    P = np.array(verts)
    on = F.globe_point(P)
    nrm = (on - np.array(F.C0)) / np.linalg.norm(on - np.array(F.C0), axis=1)[:, None]
    w = np.array(uvw)
    h = F.EYE_DOME * w[:, 2] - F.EYE_SINK * (1.0 - w[:, 2])
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
    """Behind the lens at the closed lid's height: a blink squashes the lens onto the painted lash line (a U from
    corner to corner, wishlume_shade.face_marks) and sinks it under the paper."""
    c, _xa, ya, lk = F.eye_frame(s)
    return c - ya * (F.EYE_R * F.EYE_SHAPE[1] * 0.14) - lk * (F.EYE_R * 0.6), ya, lk


# ----------------------------------------------------------------------------- paint
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return WP.body_paint(co, PALETTE)['paint']


def preview_prop_colour(name: str):
    col = WP.colours(PALETTE)
    return {'wraps': col['twine'], 'threads': col['thread'], 'bead': col['lacquer']}.get(name, col['rib'])


def build_props(high: bool, quick: bool) -> list:
    return PR.objects(high)


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        co, _vn = S.mesh_arrays(ob)
        cr = S.attr_array(ob, 'crease').astype(np.float64) if 'crease' in ob.data.attributes else None
        a = WP.body_paint(co, PALETTE, cr)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'glow', a['glow'])
        for vid, var in VARIANTS.items():
            v = WP.body_paint(co, var, cr)
            S.set_colour_attr(ob, U.variant_attr(vid, ID), v['paint'])
            # Beacon: its paper at 0.8 of the base's share, the inside (1.0) as bright as it goes: a brighter core
            S.add_attr(ob, f'glow_{U.variant_short(vid, ID)}', np.where(v['dish'], 0.62, v['glow'] * 0.8))
        if 'armk' not in ob.data.attributes:
            S.add_attr(ob, 'armk', F.arm_k(co))
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
# round 3: the strands end about 1.2 cm off the ground; the chain's tip sits above them, and with the gentler bob (0.4,
# 9 mm) the plan never pools the tassel in idle (it swings back clear of the ground only when the body sinks)
TASSEL = [(0.0, 0.0, PR.JUNCTION_Z), (0.0, 0.0, PR.COLLAR_Z[0]), (0.0, 0.0, 0.12), (0.0, 0.0, 0.05)]
CAP = {'name': 'cap', 'parent': 'head', 'head': (0.0, 0.0, 0.84), 'tail': (0.0, 0.0, 0.918)}


def rig_p() -> dict:
    return {
        'hip': F.C0, 'chest': (0.0, 0.0, F.TOP_Z), 'body_base': (0.0, 0.0, F.Z_OPEN),
        'head_c': (0.0, -0.08, 0.58), 'head_r': 0.24,
        'jaw': {'head': (0.0, -0.16, 0.53), 'tail': (0.0, -0.25, 0.512)},
        'arms': {**F.ARM, 'parent': 'head'},
        'chains': [{'name': 'tassel', 'kind': 'tassel', 'parent': 'head', 'points': TASSEL}],
        'props': [CAP],
        'bob': 0.4, 'strike_style': 'pulse', 'glide_lean': 1.6,
        # the pulse swells evenly rather than stretching into an egg, turned toward its left for the 70-degree shot
        # round 2: it leans back about 12 degrees and pushes forward, the lower front (the heart) toward the target
        'pulse_lean': -26.0, 'pulse_push': 0.07, 'pulse_stretch': 0.4, 'pulse_yaw': 24.0,
        # ko: the lantern lies on its side on the ground (its body hovers at rest; the frame is about 1 cm proud), the
        # paddle underneath swung up beside the crown, the tassel drooping to the ground
        'ko_ground': 0.012, 'ko_arm': (0.0, 120.0, 0.0), 'ko_chain_hang': 0.9,
        # polish: in hit_heavy the tassel lags and droops under gravity (it stood out along the body's axis)
        'hit_heavy_chain_hang': 0.85,
    }


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The paper is one rigid lantern on `head` (the lenses ride the head's blink bones, so the face never slides; the
    squash comes from the hover bone); each paddle bends from the globe at the shoulder and the elbow."""
    regs = [(np.ones(len(co), bool), {'head': np.ones(len(co))})]
    ak = F.arm_k(co)
    for tag, s in (('L', 1), ('R', -1)):
        on = (np.sign(co[:, 0]) == s) & (ak > 0.02)
        if on.any():
            pts = [F.mirror(F.ARM[k], s) for k in ('shoulder', 'elbow', 'hand')]
            regs.append((on, U.chain_weights(co[on], pts, [f'upperarm.{tag}', f'forearm.{tag}'], 'head', fade=(0.25, 0.0))))
    return regs


def tassel_weights(z: np.ndarray) -> dict:
    """The threads and the core by height: tassel.1 at the collar, .2 down the brush, .3 at the ends."""
    h = (PR.THREAD_TOP - z) / (PR.THREAD_TOP - 0.02)
    w1 = 1.0 - smooth(0.0, 0.35, h)
    w3 = smooth(0.45, 0.9, h)
    return {'tassel.1': w1, 'tassel.2': np.clip(1.0 - w1 - w3, 0, 1), 'tassel.3': w3}


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    part = np.rint(attr('part')).astype(int)
    pt = attr('pt').astype(np.float64)
    pr = attr('pr').astype(np.float64)
    out = [(np.ones(len(co), bool), {'head': np.ones(len(co))})]
    out.append(U.rigid(np.isin(part, PR.CAP_PARTS), 'prop.cap'))
    cord = (part == PR.CORD) & (pr < 0.85)
    if cord.any():
        t = smooth(0.55, 1.0, pt[cord])
        out.append((cord, {'head': 1.0 - t, 'tassel.1': t}))
    out.append(U.rigid(((part == PR.CORD) & (pr >= 0.85)) | np.isin(part, (PR.KNOT, PR.BEAD, PR.GOLD, PR.COLLAR)), 'tassel.1'))
    for tag, s in (('L', 1), ('R', -1)):
        rim = (part == PR.ARMRIM) & (np.sign(co[:, 0]) == s)
        if rim.any():
            pts = [F.mirror(F.ARM[k], s) for k in ('shoulder', 'elbow', 'hand')]
            out.append((rim, U.chain_weights(co[rim], pts, [f'upperarm.{tag}', f'forearm.{tag}'], 'head', fade=(0.25, 0.0))))
    br = np.isin(part, (PR.CORE, PR.THREAD))
    if br.any():
        out.append((br, tassel_weights(co[br, 2])))
    return out


CLIP_CALM = {'*': {'tassel': 1.0, 'arm': 1.0}}

FACE_NOTE = ('The face is painted on the paper like ink: the eyes are shallow glossy lenses (lo_eyes) with the brown iris, '
             'its amber lower half, the pupil and two catchlights baked into the body atlas; the ink outlines, the brows, '
             'the small smile, the blush and the closed lids\' lash lines are baked into the body. No face sheet and no '
             'morphs: expressions in clips\' `faces` are hints only; the mouth never opens. Blinking scales the blink '
             'bones (play `blink` over any clip): each lens squashes onto the painted lash line and sinks under the '
             'paper. The inner light is the glow map (ORM alpha, in the paper\'s own colour; Beacon\'s tinted #FFB85C): '
             'modest on the paper and the paddles, hot over the flame inside the opening; socket_core sits at the flame '
             '(the pulse strike\'s beam).')

REVIEW = {'centre': (0.0, 0.0, 0.47), 'size': 1.12, 'head': ((0.0, -0.12, 0.6), 0.62)}
