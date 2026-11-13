"""A stand-in recipe for the biped plan (plans/biped.py): NOT a breed, never shipped or registered. It exists to build,
preview and review the biped rig and clips with every option on: a 4-bone tail with a puff, small wings, a three-chain
cape, ears, a weighted jaw and a horns prop. A plain velvet skin (no locks, cards or tuft) keeps its builds fast.

    npm run art:shape -- _biped_test
    tools/blender/slot.sh "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python-exit-code 1 --python tools/blender/monsters/build_ultra.py -- --breed _biped_test_ultra --quick --cpu --out <dir>
"""
from __future__ import annotations

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

ID = '_biped_test'
LOOK = '_biped_test-ultra'
PLAN = 'biped'
HEIGHT_UNITS = 180                 # about 1.18 m tall (the size rule)
PALETTE = {'body': '#7A6FB8', 'belly': '#E8D9B0', 'accent': '#D9534F', 'eye': '#2A2233'}
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('eye.L', 'eye.R')     # the jaw moves skin (the mouth opens)
BODY_TRIS = 24000
ATLAS_STRIP = 0
FACE_NOTE = 'A stand-in for the biped plan: baked face, glossy lenses, blink bones.'

HIP = (0.0, 0.0, 0.38)
CHEST = (0.0, 0.03, 0.74)
HEAD_C = Vector((0.0, -0.05, 0.96))
HEAD_R = 0.17
LEGS = {'hip': (0.1, 0.0, 0.36), 'knee': (0.115, -0.05, 0.2), 'ankle': (0.115, 0.0, 0.055), 'toe': (0.115, -0.14, 0.02)}
ARMS = {'shoulder': (0.19, 0.02, 0.69), 'elbow': (0.27, 0.05, 0.52), 'wrist': (0.31, 0.01, 0.36), 'hand': (0.33, -0.02, 0.27)}
TAIL = [(0.0, 0.12, 0.34), (0.0, 0.3, 0.27), (0.0, 0.46, 0.2), (0.0, 0.6, 0.19), (0.0, 0.72, 0.25)]
EAR = {'base': (0.1, -0.03, 1.08), 'dir': (0.45, 0.15, 0.88), 'len': 0.15}
WINGS = {'parent': 'chest', 'shoulder': (0.09, 0.13, 0.67), 'elbow': (0.18, 0.24, 0.74), 'wrist': (0.17, 0.31, 0.6),
         'fingers': [(0.21, 0.37, 0.42), (0.15, 0.36, 0.5)], 'attach': (0.07, 0.17, 0.5),
         'spread': {'elbow': (0.42, 0.22, 0.86), 'wrist': (0.7, 0.26, 0.95), 'fingers': [(0.9, 0.3, 0.62), (0.66, 0.34, 0.56)]}}
CAPES = [{'name': f'cape{t}', 'parent': 'chest', 'points': [(x, 0.15, 0.71), (x * 1.15, 0.2, 0.56), (x * 1.3, 0.24, 0.41), (x * 1.4, 0.26, 0.27)]}
         for t, x in (('L', 0.06), ('C', 0.0), ('R', -0.06))]
HORNS = {'name': 'horns', 'parent': 'head', 'head': (0.0, -0.04, 1.08), 'tail': (0.0, -0.04, 1.2)}


def rig_p() -> dict:
    return {'hip': HIP, 'chest': CHEST, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R, 'legs': LEGS, 'arms': ARMS,
            'ear_base': EAR['base'], 'ear_dir': EAR['dir'], 'ear_len': EAR['len'],
            'tail_bones': 4, 'tail_points': TAIL, 'tail_puff': {'length': 0.12}, 'wings': WINGS, 'capes': CAPES,
            'props': [HORNS], 'jaw': {'head': (0.0, -0.08, 0.92), 'tail': (0.0, -0.21, 0.86)}, 'strike_style': 'punch'}


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    ps = [
        Part('pelvis', 'sphere', loc=(0, 0.01, 0.38), radius=0.15, scale=(1.05, 0.95, 0.9)),
        Part('torso', 'capsule', loc=(0, 0.01, 0.42), to=(0, 0.03, 0.66), radius=0.14),
        Part('belly', 'sphere', loc=(0, -0.04, 0.5), radius=0.13, scale=(1.0, 0.9, 1.1)),
        Part('shoulders', 'capsule', loc=(-0.16, 0.03, 0.68), to=(0.16, 0.03, 0.68), radius=0.07),
        Part('neck', 'capsule', loc=(0, 0.02, 0.7), to=(0, -0.02, 0.84), radius=0.08),
        Part('head', 'sphere', loc=tuple(HEAD_C), radius=HEAD_R, scale=(1.0, 0.95, 0.92)),
        Part('snout', 'sphere', loc=(0, -0.17, 0.91), radius=0.09, scale=(1.0, 0.9, 0.7)),
        Part('jaw', 'sphere', loc=(0, -0.15, 0.85), radius=0.075, scale=(1.0, 1.0, 0.55)),
        Part('horn', 'capsule', loc=(0.06, -0.05, 1.08), to=(0.09, 0.0, 1.2), radius=0.022, mirror=True),
        Part('ear', 'capsule', loc=EAR['base'], to=tuple(Vector(EAR['base']) + Vector(EAR['dir']).normalized() * EAR['len']), radius=0.03, mirror=True),
        Part('puff', 'sphere', loc=(0, 0.79, 0.29), radius=0.075),
    ]
    for side, s in (('L', 1), ('R', -1)):
        m = lambda p, s=s: (p[0] * s, p[1], p[2])
        ps += [
            Part(f'thigh{side}', 'capsule', loc=m(LEGS['hip']), to=m(LEGS['knee']), radius=0.065),
            Part(f'shin{side}', 'capsule', loc=m(LEGS['knee']), to=m(LEGS['ankle']), radius=0.05),
            Part(f'foot{side}', 'sphere', loc=m((0.115, -0.06, 0.035)), radius=0.06, scale=(0.9, 1.5, 0.6)),
            Part(f'upper{side}', 'capsule', loc=m(ARMS['shoulder']), to=m(ARMS['elbow']), radius=0.045),
            Part(f'fore{side}', 'capsule', loc=m(ARMS['elbow']), to=m(ARMS['wrist']), radius=0.04),
            Part(f'hand{side}', 'sphere', loc=m((0.32, 0.0, 0.31)), radius=0.045, scale=(0.9, 1.0, 1.2)),
        ]
    for i in range(len(TAIL) - 1):
        ps.append(Part(f'tail{i}', 'tube', loc=TAIL[i], to=TAIL[i + 1], radius=0.06 - 0.01 * i, r2=0.05 - 0.01 * i))
    return ps


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    head = np.linalg.norm(co - np.array(HEAD_C[:]), axis=1) < HEAD_R * 1.45
    return {'face': head & (y < -0.1), 'belly': (np.abs(x) < 0.12) & (y < -0.02) & (z > 0.36) & (z < 0.72),
            'tail': (y > 0.18) & (z < 0.36) & (np.abs(x) < 0.12)}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    regs = []
    tail = (y > 0.17) & (z < 0.4) & (np.abs(x) < 0.13)
    regs.append((tail, U.chain_weights(co[tail], TAIL + [(0.0, 0.84, 0.3)], ['tail.1', 'tail.2', 'tail.3', 'tail.4', 'tail.puff'], 'hips')))
    jaw = (y < -0.06) & (z < 0.885) & (z > 0.78) & (np.abs(x) < 0.1)
    regs.append((jaw, {'jaw': np.ones(int(jaw.sum()))}))
    horns = (z > 1.07) & (np.abs(x) < 0.12) & (y > -0.09)
    regs.append(U.rigid(horns, 'prop.horns'))
    for tag, s in (('L', 1), ('R', -1)):
        b = np.array([EAR['base'][0] * s, EAR['base'][1], EAR['base'][2]])
        d = np.array([EAR['dir'][0] * s, EAR['dir'][1], EAR['dir'][2]])
        d /= np.linalg.norm(d)
        along = np.clip((co - b) @ d, 0.0, EAR['len'])
        near = np.linalg.norm(co - (b + along[:, None] * d), axis=1) < 0.05
        ear = near & ((co - b) @ d > -0.01) & (np.sign(x) == s) & ~horns
        pts = [tuple(b), tuple(b + d * EAR['len'] * 0.5), tuple(b + d * EAR['len'])]
        regs.append((ear, U.chain_weights(co[ear], pts, [f'ear.{tag}.1', f'ear.{tag}.2'], 'head')))
    return regs


# ----------------------------------------------------------------------------- membranes: the wings and the cape
def _cape_sheet(name: str, nu: int, nv: int) -> bpy.types.Object:
    cols = [np.array(c['points'], np.float64) for c in reversed(CAPES)]        # R, C, L (x ascending)
    verts, faces, cuv = [], [], []
    for j in range(nv + 1):
        v = j / nv
        row = []
        for c in cols:
            row.append(U._arc([tuple(p) for p in c], np.array([v]))[0] + np.array([0.0, 0.015, 0.0]))
        for i in range(nu + 1):
            u = i / nu
            k = u * (len(cols) - 1)
            a = min(int(k), len(cols) - 2)
            p = row[a] * (1 - (k - a)) + row[a + 1] * (k - a)
            verts.append(p)
            cuv.append((u, v, 0.0))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    n = len(verts)
    return S.sheet_object(name, np.array(verts), faces, {'cape_uv': np.array(cuv), 'wing_uv': np.zeros((n, 3)),
                                                          'wing_side': np.zeros(n)}, out=(0.0, 1.0, 0.0))


def build_fins(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for s in (1, -1):
        ob = S.wing_membrane(f'{tag}_wing{"L" if s > 0 else "R"}', WINGS, s, high, quick)
        S.add_attr(ob, 'cape_uv', np.zeros((len(ob.data.vertices), 3)))
        out.append(ob)
    out.append(_cape_sheet(f'{tag}_cape', 10 if high else 6, 16 if high else 8))
    return out


def fin_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    regs = U.wing_fin_regions(co, attr, names, WINGS)
    cuv = attr('cape_uv')
    cape = (attr('wing_side') == 0)
    if cape.any():
        w: dict[str, np.ndarray] = {}
        u = cuv[cape, 0]
        blend = {'capeR': np.clip(1 - u * 2, 0, 1), 'capeC': 1 - np.abs(u - 0.5) * 2, 'capeL': np.clip(u * 2 - 1, 0, 1)}
        for c in CAPES:
            cw = U.chain_weights(co[cape], c['points'], [f"{c['name']}.{i + 1}" for i in range(3)], 'chest')
            for b, v in cw.items():
                w[b] = w.get(b, 0.0) + v * blend[c['name']]
        regs.append((cape, w))
    return regs


# ----------------------------------------------------------------------------- eyes
def _eye_centre(s: int) -> Vector:
    return HEAD_C + Vector((0.075 * s, -0.135, 0.035))


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 32 if high else 16
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=0.034)
    c = _eye_centre(s)
    for v in bm.verts:
        v.co = Vector((v.co.x, v.co.y * 0.55, v.co.z)) + c
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


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        co, _ = S.mesh_arrays(ob)
        z = zones(co)
        rgb = np.where(z['belly'][:, None], _lin(PALETTE['belly'])[None], _lin(PALETTE['body'])[None])
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', np.tile(np.array([1.0, 0.6, 0.1]), (len(co), 1)))
    for ob in fins:
        n = len(ob.data.vertices)
        cape = 'cape_uv' in ob.data.attributes and np.abs(S.attr_array(ob, 'cape_uv')).sum() > 0
        S.set_colour_attr(ob, 'paint', np.tile(_lin('#B03A48' if cape else PALETTE['accent']), (n, 1)))
        S.set_colour_attr(ob, 'rough', np.tile(np.array([1.0, 0.5, 0.2]), (n, 1)))


def body_material(name: str, attr: str, pal: dict, marks):
    return BK.emission_attr_material(name, attr)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.where(z['belly'][:, None], _lin(PALETTE['belly'])[None], _lin(PALETTE['body'])[None])


REVIEW = {'centre': (0.0, 0.1, 0.6), 'size': 1.9, 'head': ((0.0, -0.08, 0.97), 0.7)}
