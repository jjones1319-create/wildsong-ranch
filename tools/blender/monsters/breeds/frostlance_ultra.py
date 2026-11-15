"""Frostlance at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md, the
"Floater plan" section).

A narwhal that swims through the air, cool, precise and quietly proud (chatgpt/monsters/18-frostlance/): a plump,
torpedo-shaped whale body, pale blue-white on the sides and the face, white underneath, with a deep-teal back speckled
with white freckles and snowflakes; a long, straight spiral tusk of clear ice from the forehead; two frost-edged
pectoral fins and a broad tail fluke fringed with ice crystals; big gentle eyes and a small closed smile under the
snout. Its trail of drifting snowflakes is the runtime's effect, not the model.

- The shape: frostlance_form.py (measured on 2-turnaround.png); the fins, the fluke and the tusk: frostlance_props.py.
- Colours and paint: frostlance_paint.py; the per-pixel bake materials and the snowflakes' places: frostlance_shade.py.

Part counts (the card): two pectoral fins, one fluke, one tusk; no arms or legs. The tusk leaves the forehead between
and above the eyes as every picture shows (the card's text says the upper lip: the pictures place parts). The face is
painted and the mouth never opens (the jaw stays merged into the head): a closed smile, as the turnaround and the
neutral face show it. Size (the owner's decision, Nov 12): 0.9 x Puddlepup's height (HEIGHT_UNITS 135, the back's top
0.887 m) and the pictures' length, 1.18 m snout to tail (the tusk's point 0.29 m ahead of the snout).
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.surface import smooth, v3
from monsters.breeds import frostlance_form as F
from monsters.breeds import frostlance_paint as FP
from monsters.breeds import frostlance_props as PR
from monsters.breeds import frostlance_shade as SH

ID = 'frostlance'
LOOK = 'frostlance-ultra'
PLAN = 'floater'
HEIGHT_UNITS = 135

PALETTE = {'body': '#D8EEF7', 'belly': '#F5FBFE', 'accent': '#1F7A8C', 'eye': '#1B263B', 'tusk': '#BDE8F5'}
VARIANTS: dict = {}

# the tusk's ice and the fins' frost glow faintly in their own colour (untinted, steady), so the pale ice reads bright
# beside the body instead of grey in its shadow; the body never glows
GLOW = {'strength': 0.5, 'tint': None, 'twinkle': 0.0}

ATLAS_STRIP = 0                     # no fur cards, no tuft
BODY_TRIS = 44000
VOXELS = {'hi': 0.003, 'hi_quick': 0.005, 'lo': 0.0048}
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_props': 1.25}    # polish: more texels on the fins and the fluke
AO_FLOOR = 0.68                     # round 3: the fins' roots met the flank in a tight crease that baked dark specks
AO_SOFTEN = 2.5
BODY_SHEEN = 0.06                   # smooth whale skin: a faint sheen (more veiled the deep teal in cyan)
NORMAL_SCALE = 0.85                 # the tusk's grooves and the fins' pillows read; the body is smooth
LITE_PROPS_TRIS = 4500              # the tusk, the fins and the fluke are the look
BLINK_CLOSED = (0.85, 0.05, 0.22)
MOUTH_SOCKET = (0.0, F.MOUTH_C.y - 0.01, F.MOUTH_Z)

all_parts = F.all_parts
zones = F.zones
decimate_keep = F.decimate_keep
body_material = SH.body_material
prop_material = SH.prop_material
eye_material = SH.eye_material
colours = FP.colours


def texel_k(co: np.ndarray) -> np.ndarray:
    """lo_body's texel density per face: the face 1.5 (the eyes' lids, the brows, the smile), the underside 0.8."""
    k = np.ones(len(co))
    k = np.where(co[:, 2] < 0.42, 0.8, k)
    k = np.where(F.face_k(co) > 0.5, 1.5, k)
    return k


# ----------------------------------------------------------------------------- carving
def _settle(ob) -> None:
    """Snap the voxel skin onto the exact surface without folds (polish). Under each fin root's tip the snap folded the
    skin over itself (faces turned inward: a glossy white sliver under the root, dark specks over it), so: snap, rebuild
    a clean skin from that at the same voxel size, snap again (now every vertex moves only a few millimetres)."""
    co, _vn = S.mesh_arrays(ob)
    S.set_positions(ob, F.snap(co))
    me = ob.data
    ev = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)
    co, _vn = S.mesh_arrays(ob)
    vox = float(np.median(np.linalg.norm(co[ev[:, 0]] - co[ev[:, 1]], axis=1)))
    rm = ob.modifiers.new('resettle', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = vox
    C.apply_modifiers(ob)
    co, _vn = S.mesh_arrays(ob)
    S.set_positions(ob, F.snap(co))
    ob.data.shade_smooth()


def carve(ob) -> None:
    """The voxel union's skin snapped onto the exact smooth surface (the eye lenses are laid on it), then (round 1) the
    faint lengthwise grooves pressed into the throat and the belly (1-hero, 2-turnaround), 2 mm deep, for the normal map."""
    _settle(ob)
    co, vn = S.mesh_arrays(ob)
    co = co - vn * (0.0011 * FP.pleat_depth(co) * FP.pleat_k(co, vn))[:, None]
    S.set_positions(ob, co)
    S.base_attrs(ob, co)


def carve_low(ob) -> None:
    _settle(ob)


# ----------------------------------------------------------------------------- the eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    """An oval patch laid on the head itself (the oval in the eye's tangent plane, each point snapped onto the body),
    bulging EYE_DOME at its middle and tucked EYE_SINK under the skin at its rim, so the whole oval shows and it sits
    flush in profile (Wishlume's and Zipwisp's lesson)."""
    c, xa, ya, lk = F.eye_frame(s)
    ax, ay = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1]
    rings, seg = (24, 72) if high else (7, 32)
    verts, uvw = [np.array(c[:])], [(0.0, 0.0, 1.0)]
    for i in range(1, rings + 1):
        r = i / rings
        for j in range(seg):
            a = 2 * np.pi * j / seg
            verts.append(np.array((c + xa * (ax * r * np.cos(a)) + ya * (ay * r * np.sin(a)))[:]))
            uvw.append((r * np.cos(a), r * np.sin(a), 1.0 - r * r))
    on = F.snap(np.array(verts))
    nrm = F.normal_of(on)
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
    (frostlance_shade.face_marks) and sinks it under the skin."""
    c, _xa, ya, lk = F.eye_frame(s)
    return c - ya * (F.EYE_R * F.EYE_SHAPE[1] * 0.16) - lk * (F.EYE_R * 0.6), ya, lk


# ----------------------------------------------------------------------------- paint
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return FP.body_paint(co, PALETTE, vn)['paint']


def preview_prop_colour(name: str):
    return PALETTE['tusk'] if 'tusk' in name else PALETTE['accent']


def build_props(high: bool, quick: bool) -> list:
    return PR.objects(high)


def make_marks(hi_body) -> dict:
    co, _vn = S.mesh_arrays(hi_body)
    return {'body': SH.body_flakes(co), 'props': SH.prop_flakes(), 'shards': [[list(a), list(b)] for a, b in PR.shard_lines()]}


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        co, vn = S.mesh_arrays(ob)
        a = FP.body_paint(co, PALETTE, vn)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        for k in ('teal', 'band', 'edge', 'cheek', 'pleat', 'glow', 'clear'):
            S.add_attr(ob, k, a[k])
    for ob in props:
        a = FP.prop_paint(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'glow', a['glow'])


# ----------------------------------------------------------------------------- the rig (plans/floater.py)
def rig_p() -> dict:
    """A swimmer: the squash chain runs from the rear to the snout (more forward than up), so the spin strike rolls and
    hit_heavy tumbles (5-poses hit: knocked spinning backward). The tail (3 bones, the fluke on the last) beats up and
    down like a whale's (axis 'x'); the pectoral fins flap; the tusk rides the head."""
    return {
        'hip': F.HIP, 'chest': F.CHEST, 'body_base': F.BASE, 'head_c': F.HEAD_C, 'head_r': F.HEAD_R,
        'chains': [{'name': 'tail', 'kind': 'tail', 'parent': 'hips', 'points': F.TAIL_PTS, 'axis': 'x', 'stiff': 0.0},
                   {'name': 'fin', 'kind': 'fin', 'parent': 'chest', 'points': F.fin_bone_points(1), 'mirror': True, 'heat': False}],
        'props': [{'name': 'tusk', 'parent': 'head', 'head': tuple(F.TUSK_BASE), 'tail': tuple(F.TUSK_TIP)}],
        'strike_style': 'ram',
        # the tusk thrust (5-poses attack): it rears back on the wind-up, then darts in nose-down so the tusk (33 degrees
        # up at rest) points almost level at the target, the tail rising behind; turned a little toward its left, so the
        # face shows in the in-game strike shot (70 degrees)
        'ram_yaw': 25.0,
        # round 1: the card's spiralling thrust: one full roll along the body as it darts, upright again by the impact
        'ram_roll': 360.0, 'ram_roll_span': (0.28, 0.52),
        # round 1: the fins lift as it winds up and rolls, and it rises a little in the dart, so the bigger fins clear the
        # ground through the roll (measured: lowest +50 mm)
        'strike_bones': {'hover': (22.0, 0.0, 0.0), 'finL.1': (0.0, -30.0, 0.0), 'finR.1': (0.0, 30.0, 0.0)},
        'strike_windup_bones': {'hover': (-8.0, 0.0, 0.0), 'finL.1': (0.0, -30.0, 0.0), 'finR.1': (0.0, 30.0, 0.0)},
        'glide_lean': 0.7,
        # polish: how far the body sinks in sleep, sit and the tired and sad idles, given (the measured value moved with the
        # rebuilt skin and sleep pushed a fin 59 mm under the ground; at 0.28 every fin stays clear)
        'sink': 0.28,
        # ko: it lies on its right side on the ground (its body hovers at rest); the fin underneath swings toward the belly
        # and lies flat on the ground, the top fin droops over the belly, the tail curls down to the ground and the fluke
        # lies flat on it (each stood up like a blade)
        'ko_ground': 0.01,
        # (each measured on the posed meshes through the whole fall, round 3: the fin underneath at least 26 mm up, the
        # broader fluke 70 mm up)
        'ko_bones': {'finR.1': (0.0, -40.0, -55.0), 'finL.1': (0.0, 50.0, 0.0),
                     'tail.1': (0.0, 0.0, 14.0), 'tail.2': (0.0, 0.0, 20.0), 'tail.3': (0.0, 80.0, 0.0)},
        # hit_heavy: the tumble (5-poses hit: knocked spinning backward). The plan tips a swimmer's nose up 45 degrees
        # before it rolls, so upside down the tusk pointed into the ground; here the nose dips about 10 degrees instead,
        # and rolled over the tusk points up and away (the picture's belly-up spin)
        'hit_heavy_bones': {'hover': (55.0, 0.0, 0.0)},
        # round 1: win is a celebration: an upward corkscrew (the nose up, a half roll and back as it rises) with a flick of
        # the fluke at the top, then the plan's spin; the fins flare
        'clip_bones': {'win': {'hover': [(0.0, 0.42, (-34.0, 0.0, 0.0), (0.0, 0.0, 0.1)), (0.04, 0.4, (0.0, 70.0, 0.0))],
                               'tail.2': [(0.18, 0.42, (26.0, 0.0, 0.0))], 'tail.3': [(0.2, 0.44, (36.0, 0.0, 0.0))],
                               'finL.1': [(0.05, 0.45, (0.0, -30.0, 0.0))], 'finR.1': [(0.05, 0.45, (0.0, 30.0, 0.0))]},
                       'strike': {'hover': [(0.22, 0.62, (0.0, 0.0, 0.0), (0.0, 0.0, 0.06))]},
                       # the bigger fin underneath folds early as it falls (measured: never under the ground, lowest +26 mm)
                       'ko': {'finR.1': [(0.26, 0.76, (0.0, -75.0, -25.0))]}},
    }


# round 1: the glides swim: the tail beats up and down more (the plan's beat scaled per clip)
CLIP_CALM = {'walk': {'tail': 1.9}, 'run': {'tail': 1.5}, 'dash': {'tail': 1.3}, 'step_fwd': {'tail': 1.6}, 'step_back': {'tail': 1.4}}


def _tail_k(co: np.ndarray) -> np.ndarray:
    return smooth(0.18, 0.26, co[:, 1])


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The body bends smoothly along the squash chain (hips at the rear, chest in the middle, head at the front: the face,
    the eyes and the tusk's root ride the head whole), and the rear hands over to the tail chain down the stalk."""
    sq = [tuple(p) for p in F.squash_points()]
    allm = np.ones(len(co), bool)
    regs = [(allm, U.chain_weights(co, sq, ['hips', 'chest', 'head'], 'hover', fade=(-0.5, -0.6)))]
    m = co[:, 1] > 0.18
    if m.any():
        w = U.chain_weights(co[m], F.TAIL_PTS, ['tail.1', 'tail.2', 'tail.3'], 'hips', fade=(0.24, -0.02))
        sqw = U.chain_weights(co[m], sq, ['hips', 'chest', 'head'], 'hover', fade=(-0.5, -0.6))
        k = _tail_k(co[m])
        out = {b: v * k for b, v in w.items()}
        for b, v in sqw.items():
            out[b] = out.get(b, 0.0) + v * (1.0 - k)
        regs.append((m, out))
    # round 1: each fin's fleshy root follows its fin outward from the flank (the squash chain's own weights hand over)
    for tag, s in (('L', 1), ('R', -1)):
        o, a, _v, _n = F.fin_axes(s)
        d = co - np.array(o[:])
        u = d @ np.array(a[:])
        perp = np.linalg.norm(d - u[:, None] * np.array(a[:])[None], axis=1)
        m = (u > -0.03) & (u < 0.2) & (perp < 0.08) & (np.sign(co[:, 0]) == s)
        if m.any():
            w = fin_root_weights(co[m], s, tag)
            par = w.pop('chest')
            sqw = U.chain_weights(co[m], sq, ['hips', 'chest', 'head'], 'hover', fade=(-0.5, -0.6))
            out = dict(w)
            for b, v in sqw.items():
                out[b] = out.get(b, 0.0) + v * par
            regs.append((m, out))
    return regs


def fin_root_weights(co: np.ndarray, s: int, tag: str) -> dict:
    """A fin's chain from its root: the chest (the flank) up to the skin, the fin's bones from about 7 cm out (the root's
    flesh and the fin's slab share these weights, so the slab never cuts through its root as it flaps)."""
    return U.chain_weights(co, F.fin_bone_points(s), [f'fin{tag}.1', f'fin{tag}.2'], 'chest', fade=(0.22, 0.065))


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """The tusk rigid on its bone; each fin along its chain from the root (sunk in the flank: the chest); the fluke on the
    tail chain like the stalk it grows from."""
    part = np.rint(attr('part')).astype(int)
    side = np.rint(attr('side')).astype(int)
    out = [(np.ones(len(co), bool), {'head': np.ones(len(co))})]
    out.append(U.rigid(part == PR.TUSK, 'prop.tusk'))
    for tag, s in (('L', 1), ('R', -1)):
        m = (part == PR.FIN) & (side == s)
        if m.any():
            out.append((m, fin_root_weights(co[m], s, tag)))
    m = part == PR.FLUKE
    if m.any():
        out.append((m, U.chain_weights(co[m], F.TAIL_PTS, ['tail.1', 'tail.2', 'tail.3'], 'hips', fade=(0.24, -0.02))))
    return out


FACE_NOTE = ('The face is baked on the head: the eyes are glossy lenses (lo_eyes) with the blue iris, the pupil and two '
             'catchlights painted in; the closed smile, the brows and the closed lids\' lash lines are baked into the body. No '
             'face sheet and no morphs: expressions in clips\' `faces` are hints only; the mouth never opens. Blinking scales '
             'the blink bones (play `blink` over any clip): each lens squashes onto the painted lash line and sinks under the '
             'skin. The glow (ORM alpha, untinted, steady) is a soft fill on the underside (the studio light never reaches the '
             'white belly) and a faint light on the tusk\'s ridges and the fins\' and the fluke\'s frost. socket_tusk is the tusk\'s point (the ice-lance effects), socket_tail the fluke (the snowflake trail).')

REVIEW = {'centre': (0.0, 0.12, 0.6), 'size': 1.65, 'head': ((0.0, -0.27, 0.7), 0.62)}
