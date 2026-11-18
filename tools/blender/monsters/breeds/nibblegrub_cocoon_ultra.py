"""Nibblegrub's silk cocoon at the Art 2.1 Ultra tier (chatgpt/monsters/27-nibblegrub cocoon-1-hero, cocoon-2-turnaround;
PROMPTS.md "The cocoon"), on the insect plan's cocoon form (plans/insect.py, `form: 'cocoon'`; RECIPE.md "The cocoon").
Look `nibblegrub-cocoon`; it ships outside the looks registry (it has only COCOON_CLIPS: idle, wriggle, split, and blink).

    npm run art:shape -- nibblegrub-cocoon
    tools/blender/slot.sh npm run art:ultra -- nibblegrub-cocoon --blender --stages build,bake,rig,clips,export,review > tools/blender/out/nibblegrub-cocoon-build1.log 2>&1 &

Size: "about as big as Nibblegrub curled up into a ball": the silk egg 0.62 m wide and 0.88 m tall, the stalk and the
twig above it (1.18 m in all). HEIGHT_UNITS 148 is the inner core's top (lo_body, 0.97 m: what the game's
restHeight measures), so the core stands at Nibblegrub's own size rule; restHeightWithProps is the whole hang.
The parts and colours: nibblegrub_cocoon_parts.py. No variant: it's silk.
"""
from __future__ import annotations

import numpy as np
from mathutils import Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from monsters.breeds import nibblegrub_cocoon_parts as CP
from monsters.breeds.nibblegrub_cocoon_parts import smooth

ID = 'nibblegrub-cocoon'
LOOK = 'nibblegrub-cocoon-ultra'
PLAN = 'insect'
HEIGHT_UNITS = 148
PALETTE = {'body': CP.SILK, 'belly': CP.BANDC, 'accent': CP.ORANGE, 'eye': '#3B2F2F', 'glow': CP.VIOLET}
VARIANTS: dict = {}
BODY_TRIS = 9000                                # the inner core (hidden until the split)
VOXELS = {'hi': 0.004, 'lo': 0.006}
ATLAS_STRIP = 0
ATLAS_MARGIN = 0.006
ATLAS_DENSITY = {'lo_eyes': 0.2}               # the eyes are hidden inside the core
NORMAL_SCALE = 0.9                              # the silk's fibres
BODY_SHEEN = 0.3
AO_FLOOR = 0.5
AO_SOFTEN = 3.0                                 # round 3: soft contact shade at the band edges, no grey outline
LITE_PROPS_TRIS = 7200                          # the shell halves are nearly the whole model
GLOW = {'strength': 0.9, 'tint': None, 'twinkle': 0.0}      # the faint dusk glow (orange and violet)
FACE_NOTE = 'The cocoon: no face shows (the eyes are hidden inside the core, for the build contract only).'
MEMBRANE_AO_BODY = True
# round 2: the wriggle keeps the seam shut (it opened a dark crack, read as hatching): the halves only twitch with
# bulges from inside (their bulge bones, plans/insect.py) and the body's jerks; the split opens a little less (65
# degrees: the right half ran out of the review's frame)
CLIP_CALM = {'wriggle': {'shell': 0.0}, 'split': {'shell': 0.97}}     # round 3: about 70 degrees

FRONT = [CP.HIP, (0.0, 0.0, 0.8), (0.0, 0.0, 0.5)]
SHELL = [{'name': 'L', 'head': (0.022, 0.0, 0.99), 'tail': (0.3, 0.0, 0.45), 'parent': 'chest',
          'bulge': {'head': (0.12, -0.1, 0.58), 'tail': (0.16, -0.18, 0.34), 'deg': 14.0}},
         {'name': 'R', 'head': (-0.022, 0.0, 0.99), 'tail': (-0.3, 0.0, 0.45), 'parent': 'chest',
          'bulge': {'head': (-0.12, -0.1, 0.58), 'tail': (-0.16, -0.18, 0.34), 'deg': 14.0}}]
BULGE_AT = (0.2, -0.2, 0.36)                    # the left half's bulge patch (mirrored), under its bulge bone
TWIG = {'name': 'twig', 'parent': 'root', 'head': CP.TWIG[0], 'tail': CP.TWIG[-1]}
EYE_C = [(0.05, -0.17, 0.46), (-0.05, -0.17, 0.46)]
PID_SHELL_L, PID_SHELL_R, PID_STALK, PID_TWIG, PID_LEAF = 1, 2, 3, 4, 5


def rig_p() -> dict:
    return {'form': 'cocoon', 'hip': CP.HIP, 'chest': FRONT[1], 'front': FRONT, 'rear': [],
            'head_c': (0.0, 0.0, 0.38), 'head_r': 0.25, 'head_tip': (0.0, 0.0, 0.1),
            'jaw': {'head': (0.0, -0.05, 0.4), 'tail': (0.0, -0.12, 0.38)}, 'jaw_open': False,
            'shell': SHELL, 'props': [TWIG], 'legs': [], 'chains': [],
            'body_width': 0.3,               # no ko clip: nothing to measure or settle
            # round 2: the wriggle's jerks (the seam stays shut): three sharp twitches of the whole cocoon
            'clip_bones': {'wriggle': {'chest': [(0.1, 0.2, (5.0, 0.0, 4.0)), (0.44, 0.54, (-4.0, 3.0, -3.0)),
                                                 (0.72, 0.8, (3.0, -3.0, 2.0))]}}}


def calm_group(bone: str):
    if bone.endswith('.bulge'):
        return 'bulge'
    if bone.startswith('shell.'):
        return 'shell'
    return None


# ----------------------------------------------------------------------------- the core (lo_body)
def all_parts():
    """The core: a loft of thin discs following the shell's inner surface 1.5 cm inside it (so it never pokes through
    the shut shell), closing round under the stalk."""
    zi, ri = CP.core_profile()
    zs = np.arange(zi[0] + 0.03, zi[-1] - 0.002, 0.004)
    rs = np.interp(zs, zi, ri)
    return [Part(f'core{k}', 'sphere', loc=(0.0, 0.0, float(z)), radius=1.0, scale=(float(r), float(r), 0.035))
            for k, (z, r) in enumerate(zip(zs, rs)) if r > 0.01]


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The core rides the chest with the shells (so it stays inside them), stirring a little with the lower bones."""
    z = co[:, 2]
    wh = 0.2 * smooth(0.45, 0.15, z)
    wf = 0.22 * smooth(0.8, 0.5, z) * (1.0 - smooth(0.45, 0.15, z))
    return [(np.ones(len(co), bool), {'chest': 1.0 - wh - wf, 'front.1': wf, 'head': wh})]


# ----------------------------------------------------------------------------- the props
def build_props(high: bool, quick: bool):
    tag = 'hi' if high else 'lo'
    fine = high and not quick
    out = [CP.shell_half(f'{tag}_shellL', 1, fine), CP.shell_half(f'{tag}_shellR', -1, fine),
           CP.wisps(f'{tag}_wispL', 1, high), CP.wisps(f'{tag}_wispR', -1, high)]
    seg = 40 if high else 18
    rpm = 300 if high else 70
    # the stalk: a rope of silk strands twisted together from the neck's top (round 3)
    stalk, _ax = CP.rope(f'{tag}_stalk', high)
    CP.tag(stalk, PID_STALK)
    out.append(stalk)
    # the broad silk band wrapped round the twig (round 1's two loops read as ears)
    sleeve, sx = CP.tube(f'{tag}_sleeve', CP.SLEEVE, CP.SLEEVE_R, 40 if high else 18, 600 if high else 120, twist=1.5,
                         ridges=9, ridge_h=0.05 if high else 0.0)
    CP.tag(sleeve, PID_STALK)
    out.append(sleeve)
    if not high:
        S.tube_uvs(sleeve, sx)

    def knots(p, a):
        bump = np.zeros_like(a)
        for kx, ka in CP.KNOTS:
            bump += 0.012 * np.exp(-((p[0] - kx) / 0.018) ** 2) * np.clip(np.cos(a - ka), 0.0, 1.0) ** 3
        return bump
    twig, tax = CP.tube(f'{tag}_twig', CP.TWIG, CP.TWIG_R, 48 if high else 18, 400 if high else 45, twist=0.25, ridges=9,
                        ridge_h=0.07 if high else 0.02, caps='flat', bumps=knots)
    CP.tag(twig, PID_TWIG)
    out.append(twig)
    if not high:
        S.tube_uvs(twig, tax)
    nub, nax = CP.tube(f'{tag}_nub', CP.NUB, [0.015, 0.012, 0.011], 24 if high else 8, 400 if high else 60, caps='flat')
    CP.tag(nub, PID_TWIG)
    out.append(nub)
    if not high:
        S.tube_uvs(nub, nax)
    stem, sax = CP.tube(f'{tag}_stem', CP.STEM, [0.014, 0.01, 0.0075], 24 if high else 8, 400 if high else 50)
    CP.tag(stem, PID_TWIG)
    out.append(stem)
    if not high:
        S.tube_uvs(stem, sax)
    tip = np.array(CP.STEM[-1])
    leaves = [(CP.STEM[1], (-0.55, 0.15, 0.82), (0.25, -0.9, 0.3), 0.21, 0.1, 0.25),
              (CP.STEM[-1], (-0.9, -0.15, 0.45), (0.3, -0.85, 0.5), 0.23, 0.105, -0.2),
              (tuple(tip + np.array([0.0, 0.0, -0.004])), (-0.2, 0.25, 0.95), (0.4, -0.9, 0.2), 0.11, 0.055, 0.3)]
    for k, (b, d, up, Ln, W, curl) in enumerate(leaves):
        lf = CP.leaf(f'{tag}_leaf{k}', b, d, up, Ln, W, curl, 36 if high else 12, 24 if high else 8)
        CP.tag(lf, PID_LEAF)
        out.append(lf)
    return out


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """The halves (and their stray fibres) rigid on their shell bones, a soft patch on each on its bulge bone; the stalk
    from the shell's neck (chest) to the hang (body); the twig rigid on prop.twig."""
    pid = attr('pid')
    regs = []
    for pk, tag, s in ((PID_SHELL_L, 'L', 1), (PID_SHELL_R, 'R', -1)):
        m = np.abs(pid - pk) < 0.5
        if not m.any():
            continue
        c = np.array([BULGE_AT[0] * s, BULGE_AT[1], BULGE_AT[2]])
        wb = 0.75 * smooth(0.17, 0.04, np.linalg.norm(co[m] - c[None], axis=1))
        regs.append((m, {f'shell.{tag}': 1.0 - wb, f'shell.{tag}.bulge': wb}))
    st = np.abs(pid - PID_STALK) < 0.5
    if st.any():
        k = smooth(1.0, 1.09, co[st, 2])
        regs.append((st, {'chest': 1.0 - k, 'body': k}))
    tw = (np.abs(pid - PID_TWIG) < 0.5) | (np.abs(pid - PID_LEAF) < 0.5)
    regs.append(U.rigid(tw, 'prop.twig'))
    return regs


def preview_prop_colour(name: str):
    if 'twig' in name or 'stem' in name or 'nub' in name:
        return CP.BARK
    if 'leaf' in name:
        return CP.LEAF
    if 'shell' in name:
        return CP.SILK
    return CP.BANDC


# ----------------------------------------------------------------------------- the eyes (hidden inside the core)
def build_eye(name: str, s: int, high: bool):
    import bmesh
    import bpy
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16 if high else 8, v_segments=8 if high else 4, radius=0.012)
    c = Vector(EYE_C[0 if s > 0 else 1])
    for v in bm.verts:
        v.co = v.co + c
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    co, _ = S.mesh_arrays(ob)
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def blink_pivot(s: int):
    c = Vector(EYE_C[0 if s > 0 else 1])
    return c, Vector((0.0, 0.0, 1.0)), Vector((0.0, -1.0, 0.0))


def eye_material(name: str, rough_pass: bool = False):
    from lib.nodes import new_mat
    m, nb = new_mat(name)
    em = nb.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 0.5, 0.0, 1.0) if rough_pass else (*C.lin_rgb(CP.VIOLET), 1.0)
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- paint
def _put(ob, rgb, rough, coat, glow) -> None:
    S.set_colour_attr(ob, 'paint', rgb)
    S.set_colour_attr(ob, 'rough', np.stack([np.ones(len(rgb)), rough, coat], axis=1))
    S.add_attr(ob, 'glow', np.clip(glow, 0.0, 1.0))


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        co, vn = S.mesh_arrays(ob)
        _put(ob, *CP.paint_core(co, vn))
    for ob in props:
        co, vn = S.mesh_arrays(ob)
        pid = float(np.median(S.attr_array(ob, 'pid')))
        if 'wisp' in ob.data.attributes:
            _put(ob, *CP.paint_wisps(co, vn))
        elif pid in (PID_SHELL_L, PID_SHELL_R):
            _put(ob, *CP.paint_shell(ob))
        elif pid == PID_STALK:
            if 'tang' in ob.data.attributes:
                strand = 0.5 + 0.5 * np.cos(5 * S.attr_array(ob, 'tang'))
            else:
                strand = 0.5 + 0.5 * np.cos(np.arctan2(co[:, 2] - CP.TWIG_Z, co[:, 1]) * 4)
            _put(ob, *CP.paint_stalk(co, vn, strand))
        elif pid == PID_TWIG:
            groove = 0.5 - 0.5 * np.cos(9 * S.attr_array(ob, 'tang'))
            cap = S.attr_array(ob, 'tcap')
            capr = np.minimum(*(np.linalg.norm(co - np.array(e)[None], axis=1) for e in (CP.TWIG[-1], CP.NUB[-1]))) * cap
            _put(ob, *CP.paint_twig(co, vn, groove, (cap > 0.5).astype(float), capr))
        else:
            _put(ob, *CP.paint_leaf(co, vn, S.attr_array(ob, 'leafu'), S.attr_array(ob, 'leafv')))


def body_material(name: str, attr: str, pal: dict, marks):
    from lib import bake as BK
    return BK.emission_attr_material(name, attr)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return CP.paint_core(co, vn)[0]


# round 3: the whole hang in frame (the review frames a cocoon by this: tools/art/ultra-serve.ts framing)
REVIEW = {'centre': (0.0, 0.0, 0.7), 'size': 1.95, 'head': ((0.0, -0.05, 0.55), 1.1),
          'clips': [('idle', 0.25), ('wriggle', 0.2), ('wriggle', 0.5), ('split', 0.5), ('split', 0.7), ('split', 1.0)]}
