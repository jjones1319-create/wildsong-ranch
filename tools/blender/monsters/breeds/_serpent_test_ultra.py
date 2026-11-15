"""A stand-in recipe for the serpent plan (plans/serpent.py): NOT a breed, never shipped or registered. A snake in a
loose S-coil with its head raised and every option on: 14 spine bones (the anchor at the body's first curve, a 4-bone
neck, an 8-bone tail), a jaw with two fangs, a forked tongue prop that flicks and a feathered crest chain. With
WS_SERPENT_FLOAT=1 it tries the Aurelwyrm hooks instead: it floats, with ribbon fins and whiskers.

    npm run art:shape -- _serpent_test
    tools/blender/slot.sh "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python-exit-code 1 --python tools/blender/monsters/build_ultra.py -- --breed _serpent_test_ultra --quick --cpu --out <dir>
"""
from __future__ import annotations

import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import bake as BK
from lib import common as C
from lib import mesh as M
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import new_mat

ID = '_serpent_test'
LOOK = '_serpent_test-ultra'
PLAN = 'serpent'
HEIGHT_UNITS = 150
FLOATING = os.environ.get('WS_SERPENT_FLOAT') == '1'
PALETTE = {'body': '#2FA37A', 'belly': '#DDF2D3', 'accent': '#E8C14E', 'eye': '#1B3A2B'}
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 24000
ATLAS_STRIP = 0
FACE_NOTE = 'A stand-in for the serpent plan: baked face, glossy lenses, blink bones.'

RAD = 0.09
# the centre line from the back of the head to the tail's tip: the neck comes down to the ground, then a loose S
SPINE = [(0.0, -0.15, 0.78), (0.0, -0.1, 0.62), (0.0, -0.04, 0.45), (0.0, 0.02, 0.28), (0.02, 0.08, 0.12),
         (0.15, 0.22, RAD), (0.35, 0.36, RAD), (0.4, 0.58, RAD), (0.25, 0.76, RAD), (0.02, 0.84, RAD), (-0.2, 0.92, 0.085),
         (-0.32, 1.1, 0.075), (-0.26, 1.32, 0.06), (-0.08, 1.45, 0.045), (0.1, 1.5, 0.07)]
TAPER = [0.075, 0.08, 0.085, 0.09, 0.09, 0.09, 0.09, 0.088, 0.085, 0.08, 0.072, 0.062, 0.05, 0.036, 0.02]
HEAD_C = Vector((0.0, -0.27, 0.82))
HEAD_R = 0.13
HEAD_TIP = (0.0, -0.42, 0.8)
CREST = [(0.0, -0.24, 0.94), (0.0, -0.14, 1.0), (0.0, -0.03, 1.02)]
TONGUE = [(0.0, -0.3, 0.765), (0.0, -0.36, 0.765), (0.0, -0.42, 0.765)]
LIFT = 0.3 if FLOATING else 0.0


def _up(p):
    return (p[0], p[1], p[2] + LIFT)


def rig_p() -> dict:
    p = {'spine': [_up(q) for q in SPINE], 'hip': _up(SPINE[6]), 'chest': _up(SPINE[4]), 'radius': RAD, 'neck_bones': 4,
         'head_c': tuple(_up(HEAD_C)), 'head_r': HEAD_R, 'head_tip': _up(HEAD_TIP),
         'jaw': {'head': _up((0.0, -0.2, 0.775)), 'tail': _up((0.0, -0.38, 0.755))}, 'jaw_open': True,
         'tongue': {'points': [_up(q) for q in TONGUE], 'parent': 'jaw', 'reach': 0.12},
         'chains': [{'name': 'crest', 'kind': 'crest', 'parent': 'head', 'points': [_up(q) for q in CREST]}],
         'strike_style': 'lunge', 'cast_style': 'hiss', 'ko_style': 'belly', 'strike_yaw': 15.0}
    if FLOATING:
        p['float'] = LIFT
        p['chains'] += [{'name': 'whisker', 'kind': 'whisker', 'parent': 'head', 'mirror': True,
                         'points': [_up((0.06, -0.38, 0.78)), _up((0.14, -0.42, 0.7)), _up((0.2, -0.4, 0.6))]},
                        {'name': 'ribbon', 'kind': 'ribbon', 'parent': 'spine.1',
                         'points': [_up((0.0, 0.14, 0.2)), _up((0.0, 0.24, 0.24)), _up((0.0, 0.36, 0.22))]}]
    return p


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    ps = []
    for i in range(len(SPINE) - 1):
        ps.append(Part(f'seg{i}', 'tube', loc=_up(SPINE[i]), to=_up(SPINE[i + 1]), radius=TAPER[i], r2=TAPER[i + 1]))
    ps += [Part('head', 'sphere', loc=_up(HEAD_C), radius=1.0, scale=(0.12, 0.15, 0.1)),
           Part('snout', 'sphere', loc=_up((0.0, -0.37, 0.8)), radius=1.0, scale=(0.08, 0.07, 0.05)),
           Part('lowjaw', 'sphere', loc=_up((0.0, -0.33, 0.755)), radius=1.0, scale=(0.08, 0.08, 0.025)),
           Part('crest', 'tube', loc=_up(CREST[0]), to=_up(CREST[-1]), radius=0.035, r2=0.06)]
    for s in (1, -1):
        ps.append(Part('fang', 'capsule', loc=_up((0.03 * s, -0.38, 0.77)), to=_up((0.03 * s, -0.385, 0.74)), radius=0.008))
    if FLOATING:
        for s in (1, -1):
            ps.append(Part('whisker', 'tube', loc=_up((0.06 * s, -0.38, 0.78)), to=_up((0.2 * s, -0.4, 0.6)), radius=0.01, r2=0.004))
        ps.append(Part('ribbon', 'sphere', loc=_up((0.0, 0.26, 0.24)), radius=1.0, scale=(0.012, 0.12, 0.05)))
    return ps


def _near(co: np.ndarray, pts, r: float) -> np.ndarray:
    d = np.full(len(co), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.array(a), np.array(b)
        ab = b - a
        u = np.clip(((co - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        d = np.minimum(d, np.linalg.norm(co - (a + u[:, None] * ab), axis=1))
    return d < r


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2] - LIFT
    return {'face': (y < -0.3) & (z > 0.72) & (np.abs(x) < 0.12), 'belly': z < 0.05}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    regs = []
    x, y, z = co[:, 0], co[:, 1], co[:, 2] - LIFT
    regs.append(U.rigid((y < -0.25) & (z < 0.77) & (z > 0.72) & (np.abs(x) < 0.07), 'jaw'))
    cr = [_up(q) for q in CREST]
    cm = _near(co, cr, 0.07) & (z > 0.9)
    regs.append((cm, U.chain_weights(co[cm], cr, ['crest.1', 'crest.2'], 'head')))
    if FLOATING:
        for tag, s in (('L', 1), ('R', -1)):
            wp = [_up((0.06 * s, -0.38, 0.78)), _up((0.14 * s, -0.42, 0.7)), _up((0.2 * s, -0.4, 0.6))]
            wm = _near(co, wp, 0.02) & (np.sign(x) == s) & (np.abs(x) > 0.07)
            regs.append((wm, U.chain_weights(co[wm], wp, [f'whisker{tag}.1', f'whisker{tag}.2'], 'head')))
        rp = [_up((0.0, 0.14, 0.2)), _up((0.0, 0.24, 0.24)), _up((0.0, 0.36, 0.22))]
        rm = _near(co, rp, 0.06) & (np.abs(x) < 0.015) & (z > 0.17)
        regs.append((rm, U.chain_weights(co[rm], rp, ['ribbon.1', 'ribbon.2'], 'spine.1')))
    return regs


def _prop_parts() -> list[Part]:
    return [Part('tongue', 'tube', loc=_up(TONGUE[0]), to=_up(TONGUE[-1]), radius=0.01, r2=0.006)]


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for k, p in enumerate(_prop_parts()):
        for ob in M.build_part(p, bpy.context.scene.collection, segments=16 if high else 8):
            ob.name = f'{tag}_{p.name}'
            ob.data.name = ob.name
            S.add_attr(ob, 'pid', np.full(len(ob.data.vertices), float(k)))
            out.append(ob)
    return out


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    m = np.abs(attr('pid')) < 0.5
    return [(m, U.chain_weights(co[m], [_up(q) for q in TONGUE], ['tongue.1', 'tongue.2'], 'jaw'))]


# ----------------------------------------------------------------------------- eyes
def _eye_centre(s: int) -> Vector:
    return Vector(_up(HEAD_C)) + Vector((0.075 * s, -0.08, 0.04))


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 32 if high else 16
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=0.035)
    c = _eye_centre(s)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.6, v.co.y, v.co.z)) + c
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def blink_pivot(s: int):
    c = _eye_centre(s)
    return c + Vector((-0.012 * s, 0.0, 0.0)), Vector((0.0, 0.0, 1.0)), Vector((float(s), -0.6, 0.0)).normalized()


def eye_material(name: str, rough_pass: bool = False):
    m, nb = new_mat(name)
    em = nb.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (1.0, 0.08, 1.0, 1.0) if rough_pass else (*C.lin_rgb(PALETTE['eye']), 1.0)
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- paint
def _lin(h: str) -> np.ndarray:
    return S.v3(C.lin_rgb(h))


def preview_colours(co: np.ndarray, vn) -> np.ndarray:
    z = zones(co)
    rgb = np.where(z['belly'][:, None], _lin(PALETTE['belly'])[None], _lin(PALETTE['body'])[None])
    crest = (co[:, 2] - LIFT > 0.9)
    return np.where(crest[:, None], _lin(PALETTE['accent'])[None], rgb)


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in list(body_srcs) + list(props):
        co, _ = S.mesh_arrays(ob)
        col = preview_colours(co, None) if ob in body_srcs else np.tile(_lin('#C0485A'), (len(co), 1))
        S.set_colour_attr(ob, 'paint', col)
        S.set_colour_attr(ob, 'rough', np.tile(np.array([1.0, 0.55, 0.15]), (len(co), 1)))


def body_material(name: str, attr: str, pal: dict, marks):
    return BK.emission_attr_material(name, attr)


REVIEW = {'centre': (0.1, 0.6, 0.45 + LIFT), 'size': 2.4, 'head': ((0.0, -0.27, 0.82 + LIFT), 0.6)}
