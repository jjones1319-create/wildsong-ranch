"""A stand-in recipe for the construct plan (plans/construct.py): NOT a breed, never shipped or registered. By default
a chest on four stubby legs with every lid option on: a lid (the head, with the eyes) split from the box by a 2.5 cm
gap so its weights are a hard split at the hinge, a three-bone tongue prop lying on a coin hoard prop, a wind-up key
on its back that turns (a spinner) and a tassel hanging from the keyhole. With WS_CONSTRUCT_NECK=1 it tries the
Gearhoot hooks instead: a round body, a head on a short neck with a beak (a jaw), two legs, two wing chains, the key.

    npm run art:shape -- _construct_test
    tools/blender/slot.sh "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python-exit-code 1 --python tools/blender/monsters/build_ultra.py -- --breed _construct_test_ultra --quick --cpu --out <dir>
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

ID = '_construct_test'
LOOK = '_construct_test-ultra'
PLAN = 'construct'
HEIGHT_UNITS = 135
NECKED = os.environ.get('WS_CONSTRUCT_NECK') == '1'
PALETTE = {'body': '#9C6B3F', 'belly': '#C99A6B', 'accent': '#F2C94C', 'eye': '#2B1B10'}
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 24000
ATLAS_STRIP = 0
FACE_NOTE = 'A stand-in for the construct plan: baked face, glossy lenses, blink bones.'
# the flat lid and box panels decimate into big faces, rightly: the build's facet check gets more room (largest, 99.9%)
FACE_RATIO_LIMITS = (12000, 1000)


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


KEY = {'name': 'key', 'head': (0.0, 0.23, 0.42), 'tail': (0.0, 0.36, 0.42)}
if not NECKED:
    HIP = (0.0, 0.0, 0.36)
    TOP = (0.0, 0.0, 0.8)
    BASE = {'loc': (0.0, 0.0, 0.355), 'r': (0.3, 0.24, 0.125)}       # z 0.23 … 0.48
    LIDBOX = {'loc': (0.0, 0.0, 0.6), 'r': (0.31, 0.25, 0.095)}      # z 0.505 … 0.695
    LIDTOP = {'loc': (0.0, 0.0, 0.68), 'r': (0.31, 0.25, 0.11)}
    HINGE, LID_FRONT = (0.0, 0.25, 0.49), (0.0, -0.25, 0.49)
    HEAD_C, HEAD_R = Vector((0.0, -0.2, 0.62)), 0.14
    LEGS = [{'hip': (0.2, -0.14, 0.26), 'knee': (0.23, -0.15, 0.15), 'ankle': (0.22, -0.14, 0.05), 'toe': (0.22, -0.23, 0.02)},
            {'hip': (0.2, 0.14, 0.26), 'knee': (0.23, 0.15, 0.15), 'ankle': (0.22, 0.14, 0.05), 'toe': (0.22, 0.05, 0.02)}]
    TONGUE = [(0.0, 0.08, 0.492), (0.0, -0.02, 0.494), (0.0, -0.12, 0.494), (0.0, -0.22, 0.492)]
    TASSEL = [(0.0, -0.27, 0.55), (0.0, -0.285, 0.47), (0.0, -0.29, 0.4)]
else:
    HIP = (0.0, 0.0, 0.42)
    TOP = (0.0, -0.02, 0.62)
    BASE = {'loc': (0.0, 0.0, 0.42), 'r': (0.25, 0.23, 0.26)}
    NECK = [(0.0, -0.02, 0.62), (0.0, -0.04, 0.7)]
    HEAD_C, HEAD_R = Vector((0.0, -0.06, 0.82)), 0.17
    LEGS = [{'hip': (0.1, -0.02, 0.2), 'knee': (0.12, -0.06, 0.12), 'ankle': (0.12, -0.02, 0.04), 'toe': (0.12, -0.12, 0.015)}]
    WING = [(0.24, 0.0, 0.52), (0.29, 0.08, 0.4), (0.3, 0.14, 0.26)]


def rig_p() -> dict:
    p = {'hip': HIP, 'chest': TOP, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R, 'legs': LEGS,
         'spinners': [dict(KEY, parent='hips', rate=0.5)]}
    if not NECKED:
        p.update({'hinge': HINGE, 'lid_front': LID_FRONT, 'lid_max': 70.0, 'mouth': (0.0, -0.24, 0.5),
                  'tongue': {'points': TONGUE, 'parent': 'hips', 'reach': 0.42},
                  'props': [{'name': 'hoard', 'parent': 'hips', 'head': (0.0, 0.0, 0.48), 'tail': (0.0, -0.1, 0.48)}],
                  'chains': [{'name': 'tassel', 'kind': 'tassel', 'parent': 'head', 'points': TASSEL}],
                  'strike_style': 'chomp', 'cast_style': 'spit', 'ko_style': 'roll', 'hop': 0.8})
    else:
        p.update({'head_mode': 'neck', 'neck': NECK, 'head_tip': (0.0, -0.22, 0.84),
                  'jaw': {'head': (0.0, -0.16, 0.79), 'tail': (0.0, -0.24, 0.75)}, 'jaw_open': True,
                  'chains': [{'name': 'wing', 'kind': 'wing', 'parent': 'hips', 'points': WING, 'mirror': True}],
                  'strike_style': 'peck', 'cast_style': 'raise'})
    return p


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    if not NECKED:
        ps = [Part('base', 'box', loc=BASE['loc'], radius=1.0, scale=BASE['r']),
              Part('lid', 'box', loc=LIDBOX['loc'], radius=1.0, scale=LIDBOX['r']),
              Part('lidtop', 'sphere', loc=LIDTOP['loc'], radius=1.0, scale=LIDTOP['r']),
              Part('keyhole', 'sphere', loc=(0.0, -0.255, 0.57), radius=1.0, scale=(0.05, 0.02, 0.06)),
              Part('tassel', 'capsule', loc=TASSEL[0], to=TASSEL[-1], radius=0.016),
              Part('keyshaft', 'capsule', loc=KEY['head'], to=KEY['tail'], radius=0.018),
              Part('keybow', 'sphere', loc=(0.0, 0.37, 0.42), radius=1.0, scale=(0.07, 0.015, 0.05))]
    else:
        ps = [Part('body', 'sphere', loc=BASE['loc'], radius=1.0, scale=BASE['r']),
              Part('neck', 'capsule', loc=NECK[0], to=NECK[-1], radius=0.08),
              Part('head', 'sphere', loc=tuple(HEAD_C), radius=HEAD_R),
              Part('beak', 'sphere', loc=(0.0, -0.2, 0.78), radius=1.0, scale=(0.04, 0.05, 0.05)),
              Part('keyshaft', 'capsule', loc=KEY['head'], to=KEY['tail'], radius=0.018),
              Part('keybow', 'sphere', loc=(0.0, 0.37, 0.42), radius=1.0, scale=(0.07, 0.015, 0.05))]
        for tag, s in (('L', 1), ('R', -1)):
            ps.append(Part(f'wing{tag}', 'sphere', loc=_m((0.27, 0.07, 0.4), s), radius=1.0, scale=(0.04, 0.1, 0.15)))
    for tag, s in (('L', 1), ('R', -1)):
        for k, lg in enumerate(LEGS):
            ps.append(Part(f'thigh{k}{tag}', 'capsule', loc=_m(lg['hip'], s), to=_m(lg['knee'], s), radius=0.06))
            ps.append(Part(f'shin{k}{tag}', 'capsule', loc=_m(lg['knee'], s), to=_m(lg['ankle'], s), radius=0.06))
            ps.append(Part(f'foot{k}{tag}', 'sphere', loc=_m(((lg['ankle'][0] + lg['toe'][0]) / 2, (lg['ankle'][1] + lg['toe'][1]) / 2, 0.035), s),
                           radius=1.0, scale=(0.065, 0.075, 0.035)))
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
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    if not NECKED:
        return {'face': (y < -0.22) & (z > 0.52) & (np.abs(x) < 0.2), 'belly': (z < 0.3) & (np.abs(x) < 0.3)}
    return {'face': (y < -0.12) & (z > 0.72) & (np.abs(x) < 0.15), 'belly': (y < -0.1) & (z < 0.55) & (z > 0.25)}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    regs = []
    if not NECKED:
        # the jaw lesson: the box and the lid are separate shells (the 2.5 cm gap), each rigid, so the seam is a hard
        # split at the hinge and nothing of the lid leaks onto the box when it opens
        inside = (np.abs(x) < 0.34) & (np.abs(y) < 0.28)
        regs.append(U.rigid(inside & (z > 0.2) & (z < 0.4925), 'hips'))
        regs.append(U.rigid(inside & (z >= 0.4925), 'head'))
        ts = _near(co, TASSEL, 0.03) & (y < -0.265)
        regs.append((ts, U.chain_weights(co[ts], TASSEL, ['tassel.1', 'tassel.2'], 'head')))
    else:
        regs.append(U.rigid(np.linalg.norm((co - np.array(BASE['loc'])) / np.array(BASE['r']), axis=1) < 1.04, 'hips'))
        head = np.linalg.norm(co - np.array(HEAD_C[:]), axis=1) < HEAD_R * 1.08
        regs.append(U.rigid(head, 'head'))
        regs.append(U.rigid((y < -0.17) & (z < 0.78) & (z > 0.72) & (np.abs(x) < 0.05), 'jaw'))
        for tag, s in (('L', 1), ('R', -1)):
            pts = [_m(p, s) for p in WING]
            wm = (np.sign(x) == s) & (np.abs(x) > 0.24)
            regs.append((wm, U.chain_weights(co[wm], pts, [f'wing{tag}.1', f'wing{tag}.2'], 'hips')))
    regs.append(U.rigid((y > 0.25) & _near(co, [KEY['head'], KEY['tail'], (0.0, 0.38, 0.42)], 0.08), 'spin.key'))
    for tag, s in (('L', 1), ('R', -1)):
        for k, lg in enumerate(LEGS, start=1):
            pts = [_m(lg['hip'], s), _m(lg['knee'], s), _m(lg['ankle'], s), _m(lg['toe'], s)]
            lm = _near(co, pts, 0.09) & (np.sign(x) == s) & (z < (0.23 if not NECKED else 0.2))
            regs.append((lm, U.segment_weights(co[lm], [(f'leg{k}.{tag}', pts[0], pts[1]), (f'shin{k}.{tag}', pts[1], pts[2]),
                                                        (f'foot{k}.{tag}', pts[2], pts[3])], power=8.0)))
    return regs


# ----------------------------------------------------------------------------- props: the tongue and the coin hoard
def _prop_parts() -> list[Part]:
    if NECKED:
        return []
    return [Part('tongue', 'tube', loc=TONGUE[0], to=TONGUE[-1], radius=0.03, r2=0.026),
            Part('hoard', 'sphere', loc=(0.0, 0.02, 0.475), radius=1.0, scale=(0.26, 0.2, 0.02))]


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for k, p in enumerate(_prop_parts()):
        for ob in M.build_part(p, bpy.context.scene.collection, segments=24 if high else 12):
            ob.name = f'{tag}_{p.name}'
            ob.data.name = ob.name
            S.add_attr(ob, 'pid', np.full(len(ob.data.vertices), float(k)))
            out.append(ob)
    return out


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    pid = attr('pid')
    m = np.abs(pid) < 0.5
    return [(m, U.chain_weights(co[m], TONGUE, ['tongue.1', 'tongue.2', 'tongue.3'], 'hips')),
            U.rigid(np.abs(pid - 1) < 0.5, 'prop.hoard')]


# ----------------------------------------------------------------------------- eyes
def _eye_centre(s: int) -> Vector:
    if NECKED:
        return HEAD_C + Vector((0.07 * s, -0.14, 0.03))
    return Vector((0.11 * s, -0.262, 0.635))


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 32 if high else 16
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=0.045)
    c = _eye_centre(s)
    for v in bm.verts:
        v.co = Vector((v.co.x, v.co.y * 0.5, v.co.z)) + c
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def blink_pivot(s: int):
    c = _eye_centre(s)
    return c + Vector((0.0, 0.012, 0.0)), Vector((0.0, 0.0, 1.0)), Vector((0.0, -1.0, 0.0))


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
    gold = (co[:, 1] > 0.25) | ((co[:, 1] < -0.25) & (np.abs(co[:, 0]) < 0.06) & (co[:, 2] > 0.4))
    return np.where(gold[:, None], _lin(PALETTE['accent'])[None], rgb)


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in list(body_srcs) + list(props):
        co, _ = S.mesh_arrays(ob)
        col = preview_colours(co, None) if ob in body_srcs else np.tile(_lin('#E86A7C' if 'tongue' in ob.name else PALETTE['accent']), (len(co), 1))
        S.set_colour_attr(ob, 'paint', col)
        S.set_colour_attr(ob, 'rough', np.tile(np.array([1.0, 0.55, 0.15]), (len(co), 1)))


def body_material(name: str, attr: str, pal: dict, marks):
    return BK.emission_attr_material(name, attr)


REVIEW = {'centre': (0.0, 0.0, 0.42), 'size': 1.4, 'head': ((0.0, -0.2, 0.6), 0.6)}
