"""A stand-in recipe for the floater plan (plans/floater.py): NOT a breed, never shipped or registered. A lantern-like orb
with every option on: a cap prop, a jaw, floating gloves (or, with WS_FLOATER_ARMS=1, little two-bone arms instead),
a three-bone tassel hanging to the ground, two wisps trailing back, a stiff zigzag tail and two little fins. A plain
velvet skin (no locks, cards or tuft) keeps its builds fast.

    npm run art:shape -- _floater_test
    tools/blender/slot.sh "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python-exit-code 1 --python tools/blender/monsters/build_ultra.py -- --breed _floater_test_ultra --quick --cpu --out <dir>
"""
from __future__ import annotations

import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import bake as BK
from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import new_mat

ID = '_floater_test'
LOOK = '_floater_test-ultra'
PLAN = 'floater'
HEIGHT_UNITS = 165                       # about 1.08 m tall (the size rule)
PALETTE = {'body': '#E8A33D', 'belly': '#FFE3A8', 'accent': '#C2465A', 'eye': '#2A2233'}
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('eye.L', 'eye.R')     # the jaw moves skin (the mouth opens)
BODY_TRIS = 24000
ATLAS_STRIP = 0
FACE_NOTE = 'A stand-in for the floater plan: baked face, glossy lenses, blink bones.'
ARMS_MODE = os.environ.get('WS_FLOATER_ARMS') == '1'

BODY_C = Vector((0.0, 0.0, 0.62))
BODY_R = 0.27
HEAD_C = Vector((0.0, -0.05, 0.68))
HEAD_R = 0.2
CAP = {'name': 'cap', 'parent': 'head', 'head': (0.0, 0.0, 0.9), 'tail': (0.0, 0.0, 1.03)}
HANDS = {'centre': (0.38, -0.08, 0.5), 'tip': (0.42, -0.18, 0.5), 'parent': 'chest'}
ARMS = {'shoulder': (0.24, -0.02, 0.58), 'elbow': (0.33, -0.04, 0.5), 'hand': (0.38, -0.1, 0.43)}
TASSEL = [(0.0, 0.0, 0.36), (0.0, 0.0, 0.25), (0.0, 0.0, 0.14), (0.0, 0.0, 0.03)]
WISP = [(0.22, 0.08, 0.5), (0.3, 0.22, 0.43), (0.34, 0.36, 0.39), (0.36, 0.5, 0.39)]
TAIL = [(0.0, 0.24, 0.56), (0.0, 0.37, 0.63), (0.0, 0.47, 0.53), (0.0, 0.6, 0.61)]
FIN = [(0.25, -0.02, 0.74), (0.4, 0.02, 0.83)]


def rig_p() -> dict:
    p = {'hip': tuple(BODY_C), 'chest': (0.0, 0.0, 0.92), 'head_c': tuple(HEAD_C), 'head_r': HEAD_R,
         'jaw': {'head': (0.0, -0.17, 0.6), 'tail': (0.0, -0.27, 0.56)},
         'chains': [{'name': 'tassel', 'kind': 'tassel', 'parent': 'hips', 'points': TASSEL},
                    {'name': 'wisp', 'kind': 'wisp', 'parent': 'hips', 'points': WISP, 'mirror': True},
                    {'name': 'tail', 'kind': 'tail', 'parent': 'hips', 'points': TAIL, 'stiff': 0.3},
                    {'name': 'fin', 'kind': 'fin', 'parent': 'chest', 'points': FIN, 'mirror': True}],
         'props': [CAP], 'strike_style': 'pulse'}
    if ARMS_MODE:
        p['arms'] = ARMS
    else:
        p['hands'] = HANDS
    return p


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    ps = [
        Part('orb', 'sphere', loc=tuple(BODY_C), radius=BODY_R, scale=(1.0, 0.95, 1.05)),
        Part('rim', 'capsule', loc=(0, 0, 0.36), to=(0, 0, 0.4), radius=0.12),
        Part('snout', 'sphere', loc=(0.0, -0.21, 0.6), radius=0.07, scale=(1.2, 0.8, 0.7)),
        Part('cap', 'capsule', loc=CAP['head'], to=CAP['tail'], radius=0.05),
        Part('tassel', 'capsule', loc=TASSEL[0], to=TASSEL[-1], radius=0.022),
        Part('knob', 'sphere', loc=(0.0, 0.0, 0.045), radius=0.04),
    ]
    for i in range(len(TAIL) - 1):
        ps.append(Part(f'tail{i}', 'capsule', loc=TAIL[i], to=TAIL[i + 1], radius=0.035 - 0.006 * i))
    for tag, s in (('L', 1), ('R', -1)):
        for i in range(len(WISP) - 1):
            ps.append(Part(f'wisp{tag}{i}', 'tube', loc=_m(WISP[i], s), to=_m(WISP[i + 1], s), radius=0.045 - 0.012 * i, r2=0.035 - 0.012 * i))
        ps.append(Part(f'fin{tag}', 'sphere', loc=_m((0.33, 0.0, 0.79), s), radius=0.07, scale=(1.3, 0.35, 0.8)))
        if ARMS_MODE:
            ps.append(Part(f'upper{tag}', 'capsule', loc=_m(ARMS['shoulder'], s), to=_m(ARMS['elbow'], s), radius=0.035))
            ps.append(Part(f'fore{tag}', 'capsule', loc=_m(ARMS['elbow'], s), to=_m(ARMS['hand'], s), radius=0.035))
        else:
            ps.append(Part(f'glove{tag}', 'sphere', loc=_m(HANDS['centre'], s), radius=0.06, scale=(0.9, 1.1, 0.8)))
            for k, dx in enumerate((-0.025, 0.0, 0.025)):
                ps.append(Part(f'finger{tag}{k}', 'capsule', loc=_m((0.38 + dx, -0.12, 0.5), s), to=_m((0.4 + dx, -0.18, 0.5), s), radius=0.014))
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
    return {'face': (y < -0.15) & (z > 0.55) & (np.abs(x) < 0.18),
            'belly': (y < -0.12) & (z < 0.6) & (z > 0.4) & (np.abs(x) < 0.15)}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    regs = []
    orb = np.linalg.norm((co - np.array(BODY_C[:])) / np.array([1.0, 0.95, 1.05]), axis=1) < BODY_R * 0.97
    tas = _near(co, TASSEL, 0.05) & ~orb
    regs.append((tas, U.chain_weights(co[tas], TASSEL, ['tassel.1', 'tassel.2', 'tassel.3'], 'hips')))
    tl = _near(co, TAIL, 0.05) & ~orb
    regs.append((tl, U.chain_weights(co[tl], TAIL, ['tail.1', 'tail.2', 'tail.3'], 'hips')))
    for tag, s in (('L', 1), ('R', -1)):
        pts = [_m(p, s) for p in WISP]
        wm = _near(co, pts, 0.06) & ~orb
        regs.append((wm, U.chain_weights(co[wm], pts, [f'wisp{tag}.1', f'wisp{tag}.2', f'wisp{tag}.3'], 'hips')))
        fm = (np.linalg.norm((co - np.array(_m((0.33, 0.0, 0.79), s))) / np.array([1.3, 0.35, 0.8]), axis=1) < 0.085) & (np.sign(co[:, 0]) == s)
        regs.append(U.rigid(fm, f'fin{tag}.1'))
        if ARMS_MODE:
            am = _near(co, [_m(ARMS['shoulder'], s), _m(ARMS['elbow'], s), _m(ARMS['hand'], s)], 0.05) & (np.abs(co[:, 0]) > 0.22)
            regs.append((am, U.chain_weights(co[am], [_m(ARMS['shoulder'], s), _m(ARMS['elbow'], s), _m(ARMS['hand'], s)],
                                             [f'upperarm.{tag}', f'forearm.{tag}'], 'chest')))
        else:
            gm = np.linalg.norm(co - np.array(_m((0.39, -0.12, 0.5), s)), axis=1) < 0.11
            regs.append(U.rigid(gm, f'hand.{tag}'))
    cap = (co[:, 2] > 0.88) & (np.abs(co[:, 0]) < 0.08)
    regs.append(U.rigid(cap, 'prop.cap'))
    jaw = (co[:, 1] < -0.17) & (co[:, 2] < 0.6) & (co[:, 2] > 0.52) & (np.abs(co[:, 0]) < 0.1)
    regs.append(U.rigid(jaw, 'jaw'))
    return regs


# ----------------------------------------------------------------------------- eyes
def _eye_centre(s: int) -> Vector:
    return HEAD_C + Vector((0.085 * s, -0.19, 0.05))


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 32 if high else 16
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=0.036)
    c = _eye_centre(s)
    for v in bm.verts:
        v.co = Vector((v.co.x, v.co.y * 0.55, v.co.z * 1.15)) + c
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def blink_pivot(s: int):
    c = _eye_centre(s)
    return c + Vector((0.0, 0.02, -0.01)), Vector((0.0, 0.0, 1.0)), Vector((0.0, -1.0, 0.0))


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
    orb = np.linalg.norm((co - np.array(BODY_C[:])) / np.array([1.0, 0.95, 1.05]), axis=1) < BODY_R * 1.02
    return np.where((~orb)[:, None], _lin(PALETTE['accent'])[None], rgb)


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        co, _ = S.mesh_arrays(ob)
        S.set_colour_attr(ob, 'paint', preview_colours(co, None))
        S.set_colour_attr(ob, 'rough', np.tile(np.array([1.0, 0.55, 0.15]), (len(co), 1)))


def body_material(name: str, attr: str, pal: dict, marks):
    return BK.emission_attr_material(name, attr)


REVIEW = {'centre': (0.0, 0.12, 0.55), 'size': 1.7, 'head': ((0.0, -0.06, 0.68), 0.7)}
