"""A stand-in recipe for the blob plan (plans/blob.py): NOT a breed, never shipped or registered. By default a toad with
every toad option on: a pear-shaped body sitting on four short legs (folded frog hind legs), a throat sac that balloons,
a three-bone tongue (a prop mesh inside the mouth) that lashes out, a jaw and a stubby tail chain. With WS_BLOB_OCTO=1
it is an octopus instead: a mantle on eight tentacles (six curled on the ground, one holding a scroll, one free with a
quill: the ink and slap arm), a cap with a hanging tassel and spectacles. A plain velvet skin keeps builds fast.

    npm run art:shape -- _blob_test
    tools/blender/slot.sh "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python-exit-code 1 --python tools/blender/monsters/build_ultra.py -- --breed _blob_test_ultra --quick --cpu --out <dir>
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

ID = '_blob_test'
LOOK = '_blob_test-ultra'
PLAN = 'blob'
HEIGHT_UNITS = 180
OCTO = os.environ.get('WS_BLOB_OCTO') == '1'
PALETTE = ({'body': '#7D5BA6', 'belly': '#CDB4E6', 'accent': '#F2C94C', 'eye': '#1E1E2E'} if OCTO
           else {'body': '#7C9A3E', 'belly': '#F6C49B', 'accent': '#5E7A2E', 'eye': '#E9C46A'})
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')     # the jaw's heat goes to the head; the lower lip is weighted to it below
BODY_TRIS = 24000
ATLAS_STRIP = 0
FACE_NOTE = 'A stand-in for the blob plan: baked face, glossy lenses, blink bones.'


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


if not OCTO:
    HIP = (0.0, 0.02, 0.34)
    TOP = (0.0, -0.04, 0.76)
    BASE = (0.0, 0.02, 0.03)
    BODY = {'loc': (0.0, 0.03, 0.33), 'r': (0.41, 0.36, 0.31)}
    HEAD = {'loc': (0.0, -0.12, 0.58), 'r': (0.26, 0.22, 0.17)}
    HEAD_C = Vector((0.0, -0.22, 0.6))
    HEAD_R = 0.17
    SAC = {'head': (0.0, -0.2, 0.47), 'tail': (0.0, -0.33, 0.37), 'max': 1.9}
    SAC_BALL = ((0.0, -0.27, 0.42), 0.1)
    TONGUE = [(0.0, -0.12, 0.525), (0.0, -0.19, 0.525), (0.0, -0.26, 0.525), (0.0, -0.32, 0.525)]
    LEGS = [{'hip': (0.22, -0.18, 0.3), 'knee': (0.29, -0.25, 0.17), 'ankle': (0.3, -0.3, 0.045), 'toe': (0.31, -0.41, 0.02)},
            {'hip': (0.3, 0.14, 0.24), 'knee': (0.43, 0.01, 0.19), 'ankle': (0.41, 0.2, 0.045), 'toe': (0.44, 0.08, 0.02)}]
    TAIL = [(0.0, 0.38, 0.14), (0.0, 0.46, 0.11), (0.0, 0.52, 0.1)]
else:
    HIP = (0.0, 0.0, 0.44)
    TOP = (0.0, 0.02, 0.86)
    BASE = (0.0, 0.0, 0.12)
    BODY = {'loc': (0.0, 0.02, 0.5), 'r': (0.32, 0.3, 0.37)}
    HEAD_C = Vector((0.0, -0.22, 0.56))
    HEAD_R = 0.16
    GROUND = [('front', [(0.1, -0.16, 0.16), (0.2, -0.3, 0.05), (0.3, -0.42, 0.035), (0.36, -0.47, 0.08)]),
              ('side', [(0.18, -0.02, 0.15), (0.34, -0.02, 0.05), (0.48, 0.0, 0.035), (0.55, 0.04, 0.08)]),
              ('back', [(0.12, 0.16, 0.15), (0.22, 0.3, 0.05), (0.3, 0.42, 0.035), (0.37, 0.47, 0.08)])]
    SCROLL_ARM = [(-0.14, -0.15, 0.2), (-0.24, -0.28, 0.24), (-0.22, -0.37, 0.33), (-0.15, -0.38, 0.4)]
    QUILL_ARM = [(0.17, -0.12, 0.22), (0.3, -0.2, 0.3), (0.34, -0.22, 0.44), (0.31, -0.2, 0.57)]
    CAP = {'name': 'cap', 'parent': 'head', 'head': (0.0, 0.02, 0.84), 'tail': (0.0, 0.02, 0.95)}
    SPECS = {'name': 'specs', 'parent': 'head', 'head': (0.0, -0.27, 0.62), 'tail': (0.0, -0.33, 0.62)}
    SCROLL = {'name': 'scroll', 'parent': 'scrollarm.3', 'head': (-0.15, -0.38, 0.4), 'tail': (-0.15, -0.42, 0.42)}
    QUILL = {'name': 'quill', 'parent': 'quillarm.3', 'head': (0.31, -0.2, 0.57), 'tail': (0.31, -0.2, 0.72)}
    CAP_TASSEL = [(0.13, 0.02, 0.93), (0.16, 0.0, 0.85), (0.17, 0.0, 0.77)]


def rig_p() -> dict:
    p = {'hip': HIP, 'chest': TOP, 'body_base': BASE, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R, 'jaw_open': True}
    if not OCTO:
        p.update({'head_split': 0.62, 'jaw': {'head': (0.0, -0.1, 0.52), 'tail': (0.0, -0.34, 0.5)}, 'sac': SAC,
                  'tongue': {'points': TONGUE, 'parent': 'jaw', 'reach': 0.62}, 'legs': LEGS, 'strike_style': 'tongue',
                  'cast_style': 'inflate', 'ko_style': 'back', 'hop': 0.7,
                  'chains': [{'name': 'tail', 'kind': 'tail', 'parent': 'hips', 'points': TAIL}]})
    else:
        p.update({'head_split': 0.45, 'jaw': {'head': (0.0, -0.2, 0.44), 'tail': (0.0, -0.3, 0.42)},
                  'tentacles': [{'name': nm, 'points': pts, 'role': 'ground', 'mirror': True} for nm, pts in GROUND]
                  + [{'name': 'scrollarm', 'points': SCROLL_ARM, 'role': 'hold'},
                     {'name': 'quillarm', 'points': QUILL_ARM, 'role': 'free'}],
                  'props': [CAP, SPECS, SCROLL, QUILL], 'ink_arm': 'quillarm', 'strike_style': 'ink', 'cast_style': 'raise',
                  'ko_style': 'front', 'ko_pitch': 90.0,
                  'chains': [{'name': 'tassel', 'kind': 'tassel', 'parent': 'prop.cap', 'points': CAP_TASSEL}]})
    return p


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    ps = [Part('body', 'sphere', loc=BODY['loc'], radius=1.0, scale=BODY['r'])]
    if not OCTO:
        ps += [Part('head', 'sphere', loc=HEAD['loc'], radius=1.0, scale=HEAD['r']),
               Part('lip', 'sphere', loc=(0.0, -0.28, 0.5), radius=1.0, scale=(0.2, 0.08, 0.05)),
               Part('sac', 'sphere', loc=SAC_BALL[0], radius=SAC_BALL[1], scale=(1.3, 1.0, 1.0)),
               Part('tail', 'tube', loc=TAIL[0], to=TAIL[-1], radius=0.05, r2=0.02)]
        for b in ((0.08, -0.14, 0.73), (-0.08, -0.14, 0.73), (0.0, -0.06, 0.76)):
            ps.append(Part('bump', 'sphere', loc=b, radius=0.035))
        for tag, s in (('L', 1), ('R', -1)):
            for k, lg in enumerate(LEGS):
                ps.append(Part(f'thigh{k}{tag}', 'capsule', loc=_m(lg['hip'], s), to=_m(lg['knee'], s), radius=0.07 if k else 0.055))
                ps.append(Part(f'shin{k}{tag}', 'capsule', loc=_m(lg['knee'], s), to=_m(lg['ankle'], s), radius=0.05 if k else 0.045))
                ps.append(Part(f'foot{k}{tag}', 'sphere', loc=_m(((lg['ankle'][0] + lg['toe'][0]) / 2, (lg['ankle'][1] + lg['toe'][1]) / 2, 0.03), s),
                               radius=1.0, scale=(0.07, 0.08, 0.025)))
        return ps
    ps.append(Part('mouth', 'sphere', loc=(0.0, -0.27, 0.43), radius=1.0, scale=(0.07, 0.05, 0.04)))
    for nm, pts in GROUND:
        for tag, s in (('L', 1), ('R', -1)):
            for i in range(len(pts) - 1):
                ps.append(Part(f'{nm}{tag}{i}', 'tube', loc=_m(pts[i], s), to=_m(pts[i + 1], s), radius=0.06 - 0.016 * i, r2=0.046 - 0.016 * i))
    for nm, pts in (('scrollarm', SCROLL_ARM), ('quillarm', QUILL_ARM)):
        for i in range(len(pts) - 1):
            ps.append(Part(f'{nm}{i}', 'tube', loc=pts[i], to=pts[i + 1], radius=0.055 - 0.013 * i, r2=0.042 - 0.013 * i))
    return ps


def _near(co: np.ndarray, pts, r: float) -> np.ndarray:
    d = np.full(len(co), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.array(a), np.array(b)
        ab = b - a
        u = np.clip(((co - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        d = np.minimum(d, np.linalg.norm(co - (a + u[:, None] * ab), axis=1))
    return d < r


def _in(co: np.ndarray, e: dict, k: float = 1.0) -> np.ndarray:
    return np.linalg.norm((co - np.array(e['loc'])) / np.array(e['r']), axis=1) < k


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    if not OCTO:
        return {'face': (y < -0.25) & (z > 0.5) & (np.abs(x) < 0.2), 'belly': (y < -0.12) & (z < 0.5) & (np.abs(x) < 0.25)}
    return {'face': (y < -0.2) & (z > 0.45) & (z < 0.7) & (np.abs(x) < 0.16), 'belly': z < 0.1}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    regs = []
    if not OCTO:
        jaw = (co[:, 1] < -0.2) & (co[:, 2] < 0.515) & (co[:, 2] > 0.44) & (np.abs(co[:, 0]) < 0.18)
        regs.append(U.rigid(jaw, 'jaw'))
        c, r = np.array(SAC_BALL[0]), SAC_BALL[1]
        d = np.linalg.norm((co - c) / (r * np.array([1.3, 1.0, 1.0])), axis=1)
        sm = (d < 1.35) & (co[:, 1] < -0.15) & (co[:, 2] < 0.5)
        w = np.clip((1.35 - d[sm]) / 0.5, 0.0, 1.0)
        regs.append((sm, {'sac': w, 'head': 1.0 - w}))
        return regs
    jaw = (co[:, 1] < -0.24) & (co[:, 2] < 0.44) & (co[:, 2] > 0.39) & (np.abs(co[:, 0]) < 0.08)
    regs.append(U.rigid(jaw, 'jaw'))
    arms = [(f'{nm}{tag}', [_m(p, s) for p in pts]) for nm, pts in GROUND for tag, s in (('L', 1), ('R', -1))]
    arms += [('scrollarm', SCROLL_ARM), ('quillarm', QUILL_ARM)]
    for nm, pts in arms:
        m = _near(co, pts, 0.075) & ~_in(co, BODY, 0.93)
        regs.append((m, U.chain_weights(co[m], pts, [f'{nm}.{i + 1}' for i in range(len(pts) - 1)], 'body')))
    return regs


# ----------------------------------------------------------------------------- props (a mesh each: the tongue; the
# octopus's cap, tassel, spectacles, scroll and quill), told apart by their `pid`
def _prop_parts() -> list[Part]:
    if not OCTO:
        return [Part('tongue', 'tube', loc=TONGUE[0], to=TONGUE[-1], radius=0.034, r2=0.028)]
    return [Part('cap', 'sphere', loc=(0.0, 0.02, 0.88), radius=1.0, scale=(0.21, 0.21, 0.06)),
            Part('tassel', 'capsule', loc=CAP_TASSEL[0], to=CAP_TASSEL[-1], radius=0.014),
            Part('specs', 'capsule', loc=(-0.13, -0.29, 0.665), to=(0.13, -0.29, 0.665), radius=0.01),
            Part('scroll', 'capsule', loc=(-0.23, -0.4, 0.41), to=(-0.07, -0.4, 0.41), radius=0.035),
            Part('quill', 'tube', loc=(0.31, -0.2, 0.57), to=(0.31, -0.17, 0.74), radius=0.012, r2=0.03)]


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
    regs = []
    if not OCTO:
        m = np.abs(pid) < 0.5
        regs.append((m, U.chain_weights(co[m], TONGUE, ['tongue.1', 'tongue.2', 'tongue.3'], 'jaw')))
        return regs
    for k, bone in ((0, 'prop.cap'), (2, 'prop.specs'), (3, 'prop.scroll'), (4, 'prop.quill')):
        regs.append(U.rigid(np.abs(pid - k) < 0.5, bone))
    m = np.abs(pid - 1) < 0.5
    regs.append((m, U.chain_weights(co[m], CAP_TASSEL, ['tassel.1', 'tassel.2'], 'prop.cap')))
    return regs


# ----------------------------------------------------------------------------- eyes
def _eye_centre(s: int) -> Vector:
    if OCTO:
        return Vector((0.085 * s, -0.27, 0.62))
    return Vector((0.12 * s, -0.2, 0.7))


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 32 if high else 16
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=0.045 if not OCTO else 0.04)
    c = _eye_centre(s)
    for v in bm.verts:
        v.co = Vector((v.co.x, v.co.y * 0.7, v.co.z * (0.8 if not OCTO else 1.0))) + c
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def blink_pivot(s: int):
    c = _eye_centre(s)
    return c + Vector((0.0, 0.015, 0.0)), Vector((0.0, 0.0, 1.0)), Vector((0.0, -1.0, 0.0))


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
    return np.where(z['belly'][:, None], _lin(PALETTE['belly'])[None], _lin(PALETTE['body'])[None])


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in list(body_srcs) + list(props):
        co, _ = S.mesh_arrays(ob)
        col = preview_colours(co, None) if ob in body_srcs else np.tile(_lin(PALETTE['accent']), (len(co), 1))
        S.set_colour_attr(ob, 'paint', col)
        S.set_colour_attr(ob, 'rough', np.tile(np.array([1.0, 0.55, 0.15]), (len(co), 1)))


def body_material(name: str, attr: str, pal: dict, marks):
    return BK.emission_attr_material(name, attr)


REVIEW = ({'centre': (0.0, 0.0, 0.45), 'size': 1.7, 'head': ((0.0, -0.22, 0.6), 0.7)} if OCTO
          else {'centre': (0.0, -0.02, 0.38), 'size': 1.6, 'head': ((0.0, -0.22, 0.62), 0.7)})
