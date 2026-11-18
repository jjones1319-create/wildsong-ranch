"""A stand-in recipe for the avian plan (plans/avian.py): NOT a breed, never shipped or registered. By default a heron
with every heron option on: long legs (thigh, drumstick, a long tarsus, toes), a three-bone S-neck, a long beak with a
moving lower half, one pair of wings (prop meshes on the wing bones, folded at rest), a pair of crest plumes, a tail fan
of three plumes, and the flying clips. WS_AVIAN_FORM=knight makes it a stout four-winged dove-knight instead (grown
Paladove's options): two wing pairs (the lower one following the upper), a shield prop on the left wing's forearm, a
halo prop over the head, a one-bone neck, a short tail fan.

    npm run art:shape -- _avian_test
    tools/blender/slot.sh "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python-exit-code 1 --python tools/blender/monsters/build_ultra.py -- --breed _avian_test_ultra --quick --cpu --out <dir>
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

ID = '_avian_test'
LOOK = '_avian_test-ultra'
PLAN = 'avian'
KNIGHT = os.environ.get('WS_AVIAN_FORM') == 'knight'
HEIGHT_UNITS = 240 if KNIGHT else 255
PALETTE = ({'body': '#F7F4EE', 'belly': '#FFFFFF', 'accent': '#E3B448', 'eye': '#4A6FA5'} if KNIGHT
           else {'body': '#6FB7E9', 'belly': '#F5F8FC', 'accent': '#F2C14E', 'eye': '#2F3A4A'})
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 24000
ATLAS_STRIP = 0
FACE_NOTE = 'A stand-in for the avian plan: baked face, glossy lenses, blink bones.'


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


if not KNIGHT:
    HIP, CHEST = (0.0, 0.08, 0.95), (0.0, -0.14, 1.08)
    BODY = {'loc': (0.0, -0.02, 1.0), 'r': (0.16, 0.3, 0.16)}
    NECK = [(0.0, -0.2, 1.12), (0.0, -0.25, 1.28), (0.0, -0.18, 1.42), (0.0, -0.22, 1.56)]
    HEAD_C, HEAD_R = Vector((0.0, -0.28, 1.62)), 0.08
    HEAD_TIP = (0.0, -0.36, 1.62)
    BEAK = ((0.0, -0.33, 1.615), (0.0, -0.62, 1.6))
    JAW = {'head': (0.0, -0.33, 1.595), 'tail': (0.0, -0.6, 1.588)}
    LEG = {'hip': (0.09, 0.05, 0.93), 'knee': (0.1, -0.07, 0.8), 'ankle': (0.1, 0.06, 0.46), 'toe': (0.1, 0.0, 0.04),
           'toe_tip': (0.1, -0.15, 0.02)}
    WINGS = [{'name': 'wing', 'parent': 'chest', 'shoulder': (0.12, -0.1, 1.1), 'elbow': (0.17, 0.05, 1.06), 'wrist': (0.16, 0.2, 1.03),
              'fingers': [(0.13, 0.44, 0.97), (0.16, 0.4, 0.92)], 'attach': (0.12, 0.12, 0.98),
              'spread': {'elbow': (0.42, -0.06, 1.18), 'wrist': (0.72, -0.02, 1.24), 'fingers': [(1.02, 0.08, 1.27), (0.97, 0.2, 1.15)]}}]
    CHAINS = [{'name': 'crest', 'kind': 'crest', 'parent': 'head', 'mirror': True,
               'points': [(0.025, -0.25, 1.68), (0.04, -0.1, 1.73), (0.05, 0.06, 1.68)]},
              {'name': 'tail', 'kind': 'plume', 'parent': 'hips', 'points': [(0.0, 0.26, 0.98), (0.0, 0.42, 0.93), (0.0, 0.58, 0.88)]},
              {'name': 'tailside', 'kind': 'plume', 'parent': 'hips', 'mirror': True,
               'points': [(0.05, 0.25, 0.98), (0.09, 0.4, 0.94), (0.12, 0.54, 0.9)]}]
    PROPS: list = []
else:
    HIP, CHEST = (0.0, 0.04, 0.62), (0.0, -0.06, 0.98)
    BODY = {'loc': (0.0, 0.0, 0.78), 'r': (0.27, 0.25, 0.33)}
    NECK = [(0.0, -0.06, 1.02), (0.0, -0.1, 1.12)]
    HEAD_C, HEAD_R = Vector((0.0, -0.16, 1.22)), 0.16
    HEAD_TIP = (0.0, -0.3, 1.22)
    BEAK = ((0.0, -0.3, 1.2), (0.0, -0.4, 1.19))
    JAW = {'head': (0.0, -0.29, 1.18), 'tail': (0.0, -0.39, 1.175)}
    LEG = {'hip': (0.12, 0.02, 0.52), 'knee': (0.13, -0.06, 0.38), 'ankle': (0.13, 0.04, 0.19), 'toe': (0.13, -0.01, 0.03),
           'toe_tip': (0.13, -0.13, 0.015)}
    WINGS = [{'name': 'wing', 'parent': 'chest', 'shoulder': (0.2, 0.0, 0.98), 'elbow': (0.27, 0.1, 0.9), 'wrist': (0.27, 0.2, 0.84),
              'fingers': [(0.25, 0.36, 0.62), (0.27, 0.3, 0.58)], 'attach': (0.2, 0.15, 0.75),
              'spread': {'elbow': (0.45, 0.02, 1.15), 'wrist': (0.7, 0.04, 1.32), 'fingers': [(0.98, 0.08, 1.5), (0.95, 0.16, 1.36)]}},
             {'name': 'wingb', 'parent': 'chest', 'shoulder': (0.2, 0.06, 0.82), 'elbow': (0.26, 0.14, 0.72), 'wrist': (0.26, 0.22, 0.64),
              'fingers': [(0.24, 0.32, 0.46), (0.26, 0.28, 0.44)], 'attach': (0.2, 0.16, 0.6), 'follow': 0.75,
              'spread': {'elbow': (0.42, 0.08, 0.76), 'wrist': (0.62, 0.1, 0.7), 'fingers': [(0.86, 0.14, 0.66), (0.8, 0.2, 0.55)]}}]
    CHAINS = [{'name': 'crest', 'kind': 'crest', 'parent': 'head', 'points': [(0.0, -0.1, 1.36), (0.0, -0.04, 1.44), (0.0, 0.02, 1.47)]},
              {'name': 'tail', 'kind': 'plume', 'parent': 'hips', 'mirror': True, 'points': [(0.05, 0.22, 0.56), (0.08, 0.34, 0.5), (0.1, 0.44, 0.46)]}]
    PROPS = [{'name': 'halo', 'parent': 'head', 'head': (0.0, -0.12, 1.5), 'tail': (0.0, -0.12, 1.55)},
             {'name': 'shield', 'parent': 'wing.L.2', 'head': (0.29, 0.14, 0.86), 'tail': (0.33, 0.14, 0.86)}]


def rig_p() -> dict:
    p = {'hip': HIP, 'chest': CHEST, 'neck': NECK, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R, 'head_tip': HEAD_TIP, 'jaw': JAW,
         'jaw_open': True, 'legs': LEG, 'wings': WINGS[0], 'more_wings': WINGS[1:], 'chains': CHAINS, 'props': PROPS}
    if KNIGHT:
        p.update({'strike_style': 'beam', 'cast_style': 'beam', 'ko_style': 'back', 'hop': 0.6, 'fly_pitch': 14.0})
    else:
        p.update({'strike_style': 'gust', 'cast_style': 'gust', 'ko_style': 'roll', 'strike_yaw': 12.0})
    return p


# ----------------------------------------------------------------------------- the body (wings and plumes are props)
def all_parts() -> list[Part]:
    ps = [Part('body', 'sphere', loc=BODY['loc'], radius=1.0, scale=BODY['r']),
          Part('head', 'sphere', loc=tuple(HEAD_C), radius=HEAD_R),
          Part('beak', 'tube', loc=BEAK[0], to=BEAK[1], radius=0.025 if not KNIGHT else 0.035, r2=0.006)]
    for i in range(len(NECK) - 1):
        ps.append(Part(f'neck{i}', 'capsule', loc=NECK[i], to=NECK[i + 1], radius=0.05 if not KNIGHT else 0.1))
    for tag, s in (('L', 1), ('R', -1)):
        ps += [Part(f'thigh{tag}', 'capsule', loc=_m(LEG['hip'], s), to=_m(LEG['knee'], s), radius=0.05 if not KNIGHT else 0.07),
               Part(f'shin{tag}', 'capsule', loc=_m(LEG['knee'], s), to=_m(LEG['ankle'], s), radius=0.035 if not KNIGHT else 0.05),
               Part(f'tarsus{tag}', 'capsule', loc=_m(LEG['ankle'], s), to=_m(LEG['toe'], s), radius=0.018 if not KNIGHT else 0.03),
               Part(f'toe{tag}', 'capsule', loc=_m(LEG['toe'], s), to=_m(LEG['toe_tip'], s), radius=0.015 if not KNIGHT else 0.022)]
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
    if KNIGHT:
        return {'face': (y < -0.22) & (z > 1.1) & (np.abs(x) < 0.15), 'belly': (y < -0.1) & (z < 0.95) & (z > 0.5)}
    return {'face': (y < -0.3) & (z > 1.56) & (np.abs(x) < 0.08), 'belly': (y < -0.05) & (z < 1.45) & (z > 0.85)}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    regs = []
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    lower = (y < BEAK[0][1] + 0.01) & (z < (BEAK[0][2] + BEAK[1][2]) / 2) & (np.abs(x) < 0.04 if not KNIGHT else np.abs(x) < 0.05)
    regs.append(U.rigid(lower, 'jaw'))
    for tag, s in (('L', 1), ('R', -1)):
        pts = [_m(LEG[k], s) for k in ('hip', 'knee', 'ankle', 'toe', 'toe_tip')]
        lm = _near(co, pts[1:], 0.08) & (np.sign(x) == s) & (z < pts[0][2] - 0.04)
        regs.append((lm, U.segment_weights(co[lm], [(f'shin.{tag}', pts[1], pts[2]), (f'tarsus.{tag}', pts[2], pts[3]),
                                                    (f'toe.{tag}', pts[3], pts[4])], power=8.0)))
    return regs


def _prop_parts() -> list[tuple[Part, int]]:
    """Each prop part with its id: 10*wing index + side code for a wing's pieces, 100+ for plumes, 200+ for props."""
    out = []
    for i, w in enumerate(WINGS):
        for s in (1, -1):
            q = U.wing_points(w, s)
            sc = 10 * i + (1 if s > 0 else 2)
            out.append((Part(f'wa{i}{s}', 'tube', loc=tuple(q['shoulder']), to=tuple(q['elbow']), radius=0.045, r2=0.04), sc))
            out.append((Part(f'wb{i}{s}', 'tube', loc=tuple(q['elbow']), to=tuple(q['wrist']), radius=0.04, r2=0.035), sc))
            for k, f in enumerate(q['fingers']):
                out.append((Part(f'wf{i}{s}{k}', 'tube', loc=tuple(q['wrist']), to=tuple(f), radius=0.035, r2=0.012), sc))
    for j, c in enumerate(CHAINS):
        for s in ((1, -1) if c.get('mirror') else (1,)):
            pts = [_m(p, s) for p in c['points']]
            out.append((Part(f'pl{j}{s}', 'tube', loc=pts[0], to=pts[-1], radius=0.02, r2=0.006), 100 + 2 * j + (0 if s > 0 else 1)))
    for k, pr in enumerate(PROPS):
        if pr['name'] == 'halo':
            out.append((Part('halo', 'sphere', loc=pr['head'], radius=1.0, scale=(0.12, 0.12, 0.012)), 200 + k))
        else:
            out.append((Part(pr['name'], 'sphere', loc=pr['head'], radius=1.0, scale=(0.025, 0.12, 0.12)), 200 + k))
    return out


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for n, (p, pid) in enumerate(_prop_parts()):
        for ob in M.build_part(p, bpy.context.scene.collection, segments=16 if high else 10):
            ob.name = f'{tag}_{p.name}'
            ob.data.name = ob.name
            S.add_attr(ob, 'pid', np.full(len(ob.data.vertices), float(pid)))
            out.append(ob)
    return out


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    pid = attr('pid')
    regs = []
    for i, w in enumerate(WINGS):
        for s in (1, -1):
            m = np.abs(pid - (10 * i + (1 if s > 0 else 2))) < 0.5
            if m.any():
                q = U.wing_points(w, s)
                nm = U.wing_bone_names(w, s)
                segs = [(nm[0], q['shoulder'], q['elbow']), (nm[1], q['elbow'], q['wrist'])]
                segs += [(nm[2 + k], q['wrist'], f) for k, f in enumerate(q['fingers'])]
                regs.append((m, U.segment_weights(co[m], segs, power=8.0)))
    for j, c in enumerate(CHAINS):
        for s in ((1, -1) if c.get('mirror') else (1,)):
            m = np.abs(pid - (100 + 2 * j + (0 if s > 0 else 1))) < 0.5
            if m.any():
                nm = c['name'] + (('L' if s > 0 else 'R') if c.get('mirror') else '')
                pts = [_m(p, s) for p in c['points']]
                regs.append((m, U.chain_weights(co[m], pts, [f'{nm}.{k + 1}' for k in range(len(pts) - 1)], c['parent'])))
    for k, pr in enumerate(PROPS):
        regs.append(U.rigid(np.abs(pid - (200 + k)) < 0.5, f"prop.{pr['name']}"))
    return regs


# ----------------------------------------------------------------------------- eyes
def _eye_centre(s: int) -> Vector:
    if KNIGHT:
        return HEAD_C + Vector((0.07 * s, -0.12, 0.04))
    return HEAD_C + Vector((0.055 * s, -0.04, 0.02))


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 32 if high else 16
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=0.04 if KNIGHT else 0.022)
    c = _eye_centre(s)
    for v in bm.verts:
        v.co = Vector((v.co.x * (0.6 if not KNIGHT else 0.8), v.co.y * (1.0 if not KNIGHT else 0.6), v.co.z)) + c
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def blink_pivot(s: int):
    c = _eye_centre(s)
    if KNIGHT:
        return c + Vector((0.0, 0.012, 0.0)), Vector((0.0, 0.0, 1.0)), Vector((0.0, -1.0, 0.0))
    return c + Vector((-0.01 * s, 0.0, 0.0)), Vector((0.0, 0.0, 1.0)), Vector((float(s), -0.4, 0.0)).normalized()


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
    legs_ = (co[:, 2] < (0.85 if not KNIGHT else 0.48))
    return np.where(legs_[:, None], _lin(PALETTE['accent'])[None], rgb)


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in list(body_srcs) + list(props):
        co, _ = S.mesh_arrays(ob)
        col = preview_colours(co, None) if ob in body_srcs else np.tile(_lin(PALETTE['body'] if 'halo' not in ob.name else PALETTE['accent']), (len(co), 1))
        S.set_colour_attr(ob, 'paint', col)
        S.set_colour_attr(ob, 'rough', np.tile(np.array([1.0, 0.55, 0.15]), (len(co), 1)))


def body_material(name: str, attr: str, pal: dict, marks):
    return BK.emission_attr_material(name, attr)


REVIEW = ({'centre': (0.0, 0.0, 0.75), 'size': 1.9, 'head': ((0.0, -0.16, 1.22), 0.7)} if KNIGHT
          else {'centre': (0.0, 0.0, 0.85), 'size': 2.1, 'head': ((0.0, -0.3, 1.62), 0.5)})
