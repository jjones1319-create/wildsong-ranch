"""A stand-in recipe for the insect plan (plans/insect.py): NOT a breed, never shipped or registered. By default a
caterpillar (Nibblegrub's options): a round head and four plump segments on six stubby legs, antenna nubs, a chewing
mouth. WS_INSECT_FORM=hover makes it a moth (Velvesper's): a small fuzzy body, two pairs of big wings (prop paddles on
the wing bones), six little dangling legs, feathery antennae, hovering. WS_INSECT_FORM=cocoon makes it the hanging
cocoon (the reduced clip set: idle, wriggle, split), on a twig prop.

    npm run art:shape -- _insect_test
    tools/blender/slot.sh "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python-exit-code 1 --python tools/blender/monsters/build_ultra.py -- --breed _insect_test_ultra --quick --cpu --out <dir>
"""
from __future__ import annotations

import math
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

ID = '_insect_test'
LOOK = '_insect_test-ultra'
PLAN = 'insect'
FORM = os.environ.get('WS_INSECT_FORM', 'crawl')
HOVER, COCOON = FORM == 'hover', FORM == 'cocoon'
HEIGHT_UNITS = {'crawl': 120, 'hover': 165, 'cocoon': 120}[FORM]
PALETTE = {'crawl': {'body': '#F2D27A', 'belly': '#FFF0C2', 'accent': '#F29C8F', 'eye': '#3B2F2F'},
           'hover': {'body': '#EDE3F5', 'belly': '#F7F1FB', 'accent': '#5B3F7A', 'eye': '#1B1424'},
           'cocoon': {'body': '#F4E9D2', 'belly': '#E7C9F0', 'accent': '#8A6A45', 'eye': '#3B2F2F'}}[FORM]
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
BODY_TRIS = 20000
ATLAS_STRIP = 0
FACE_NOTE = 'A stand-in for the insect plan: baked face, glossy lenses, blink bones.'


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


if FORM == 'crawl':
    HIP, CHEST = (0.0, 0.06, 0.24), (0.0, -0.2, 0.27)
    FRONT = [HIP, CHEST, (0.0, -0.46, 0.36)]
    REAR = [HIP, (0.0, 0.34, 0.21), (0.0, 0.62, 0.16)]
    HEAD_C, HEAD_R = Vector((0.0, -0.62, 0.46)), 0.21
    HEAD_TIP = (0.0, -0.8, 0.5)
    JAW = {'head': (0.0, -0.72, 0.38), 'tail': (0.0, -0.82, 0.36)}
    SEGS = [((0.0, -0.36, 0.25), 0.22), ((0.0, -0.08, 0.24), 0.24), ((0.0, 0.22, 0.22), 0.22), ((0.0, 0.48, 0.18), 0.18)]
    LEGS = [{'hip': (0.12, -0.38, 0.14), 'knee': (0.17, -0.4, 0.08), 'foot': (0.17, -0.42, 0.028), 'parent': 'front.1'},
            {'hip': (0.14, -0.2, 0.12), 'knee': (0.19, -0.21, 0.075), 'foot': (0.19, -0.22, 0.028), 'parent': 'chest'},
            {'hip': (0.14, -0.02, 0.12), 'knee': (0.19, -0.02, 0.075), 'foot': (0.19, -0.02, 0.028), 'parent': 'chest'}]
    WINGS: list = []
    CHAINS = [{'name': 'antenna', 'kind': 'antenna', 'parent': 'head', 'mirror': True,
               'points': [(0.08, -0.62, 0.64), (0.1, -0.64, 0.72), (0.11, -0.66, 0.78)]}]
    SHELL: list = []
    PROPS: list = []
elif FORM == 'hover':
    HIP, CHEST = (0.0, 0.0, 0.62), (0.0, -0.12, 0.68)
    FRONT = [HIP, CHEST]
    REAR = [HIP, (0.0, 0.18, 0.56), (0.0, 0.38, 0.46)]
    HEAD_C, HEAD_R = Vector((0.0, -0.24, 0.72)), 0.13
    HEAD_TIP = (0.0, -0.36, 0.72)
    JAW = {'head': (0.0, -0.3, 0.66), 'tail': (0.0, -0.36, 0.65)}
    SEGS = [((0.0, -0.04, 0.64), 0.14), ((0.0, 0.18, 0.54), 0.12), ((0.0, 0.34, 0.47), 0.08)]
    LEGS = [{'hip': (0.06, -0.1, 0.56), 'knee': (0.12, -0.16, 0.44), 'foot': (0.13, -0.2, 0.3)},
            {'hip': (0.07, -0.03, 0.55), 'knee': (0.14, -0.02, 0.42), 'foot': (0.15, 0.0, 0.28)},
            {'hip': (0.06, 0.04, 0.55), 'knee': (0.13, 0.1, 0.42), 'foot': (0.14, 0.16, 0.28)}]
    WINGS = [{'name': 'wing', 'parent': 'chest', 'points': [(0.08, -0.06, 0.7), (0.55, -0.14, 0.92), (1.02, -0.1, 1.04)], 'width': 0.6},
             {'name': 'hind', 'parent': 'chest', 'points': [(0.07, 0.04, 0.64), (0.4, 0.16, 0.62), (0.7, 0.26, 0.56)], 'width': 0.5,
              'lag': 0.04}]
    CHAINS = [{'name': 'antenna', 'kind': 'antenna', 'parent': 'head', 'mirror': True,
               'points': [(0.04, -0.3, 0.82), (0.1, -0.36, 0.95), (0.16, -0.34, 1.05)]}]
    SHELL = []
    PROPS = []
else:
    HIP, CHEST = (0.0, 0.0, 1.2), (0.0, 0.0, 0.95)
    FRONT = [HIP, CHEST, (0.0, 0.0, 0.7)]
    REAR = []
    HEAD_C, HEAD_R = Vector((0.0, 0.0, 0.6)), 0.2
    HEAD_TIP = (0.0, 0.0, 0.42)
    JAW = {'head': (0.0, -0.05, 0.62), 'tail': (0.0, -0.12, 0.6)}
    SEGS = []
    LEGS = []
    WINGS = []
    CHAINS = []
    SHELL = [{'name': 'L', 'head': (0.12, 0.0, 1.08), 'tail': (0.24, 0.0, 0.62), 'parent': 'chest'},
             {'name': 'R', 'head': (-0.12, 0.0, 1.08), 'tail': (-0.24, 0.0, 0.62), 'parent': 'chest'}]
    PROPS = [{'name': 'twig', 'parent': 'root', 'head': (-0.32, 0.0, 1.33), 'tail': (0.36, 0.0, 1.37)}]


def rig_p() -> dict:
    p = {'form': FORM, 'hip': HIP, 'chest': CHEST, 'front': FRONT, 'rear': REAR, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R,
         'head_tip': HEAD_TIP, 'jaw': JAW, 'jaw_open': not COCOON, 'legs': LEGS, 'moth_wings': WINGS, 'chains': CHAINS,
         'shell': SHELL, 'props': PROPS}
    if HOVER:
        p.update({'strike_style': 'dust', 'cast_style': 'glow', 'ko_style': 'flat', 'ko_ground': 0.0, 'beat': 3.0, 'flap': 28.0})
    elif FORM == 'crawl':
        p.update({'strike_style': 'roll', 'cast_style': 'spray', 'ko_style': 'back', 'radius': 0.22, 'hop': 0.6, 'head_reach': 0.27})
    return p


# ----------------------------------------------------------------------------- the body (wings and antennae are props)
def all_parts() -> list[Part]:
    if COCOON:
        return [Part('cocoon', 'sphere', loc=(0.0, 0.0, 0.8), radius=1.0, scale=(0.3, 0.3, 0.42)),
                Part('silk', 'capsule', loc=(0.0, 0.0, 1.16), to=(0.0, 0.0, 1.33), radius=0.05)]
    ps = [Part('head', 'sphere', loc=tuple(HEAD_C), radius=HEAD_R)]
    for i, (c, r) in enumerate(SEGS):
        ps.append(Part(f'seg{i}', 'sphere', loc=c, radius=r))
    if HOVER:
        ps.append(Part('abdomen', 'sphere', loc=(0.0, 0.2, 0.52), radius=1.0, scale=(0.11, 0.2, 0.1)))
    else:
        for s in (1, -1):
            ps.append(Part(f'cheek{s}', 'sphere', loc=(0.13 * s, -0.74, 0.4), radius=0.08))
    for tag, s in (('L', 1), ('R', -1)):
        for i, lg in enumerate(LEGS):
            r = 0.035 if not HOVER else 0.022
            ps += [Part(f'leg{i}{tag}', 'capsule', loc=_m(lg['hip'], s), to=_m(lg['knee'], s), radius=r),
                   Part(f'shin{i}{tag}', 'capsule', loc=_m(lg['knee'], s), to=_m(lg['foot'], s), radius=0.8 * r)]
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
    if COCOON:
        return {'face': (y < -0.25) & (np.abs(z - 0.8) < 0.08) & (np.abs(x) < 0.08), 'belly': z < 0.6}
    return {'face': (y < HEAD_C.y - 0.5 * HEAD_R) & (np.abs(z - HEAD_C.z) < HEAD_R) & (np.abs(x) < HEAD_R),
            'belly': z < (0.1 if not HOVER else 0.5)}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    regs = []
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    if COCOON:
        # the shell halves: the outer sides below the top (they swing open in `split`)
        for sh in SHELL:
            s = 1 if sh['head'][0] > 0 else -1
            regs.append(U.rigid((x * s > 0.14) & (z < 1.05) & (z > 0.45), f"shell.{sh['name']}"))
        return regs
    jh = Vector(JAW['head'])
    lower = (y < jh.y + 0.02) & (z < jh.z + 0.01) & (np.abs(x) < HEAD_R * 0.5) & (np.linalg.norm(co - np.array(HEAD_C), axis=1) < HEAD_R * 1.1)
    regs.append(U.rigid(lower, 'jaw'))
    for tag, s in (('L', 1), ('R', -1)):
        for i, lg in enumerate(LEGS, start=1):
            pts = [_m(lg[k], s) for k in ('hip', 'knee', 'foot')]
            r = 0.05 if not HOVER else 0.04
            lm = _near(co, pts, r) & (np.sign(x) == s) & (np.abs(x) > abs(pts[0][0]) - 0.01)
            regs.append((lm, U.segment_weights(co[lm], [(f'leg{i}.{tag}', pts[0], pts[1]), (f'shin{i}.{tag}', pts[1], pts[2])], power=8.0)))
    return regs


def _paddle(name: str, a, b, width: float) -> Part:
    """A flat wing membrane from a to b (narrow at the root, widest near the tip), level across its width."""
    a, b = Vector(a), Vector(b)
    d = b - a
    L = d.length
    dn = d / L
    rx = math.degrees(math.asin(max(-1.0, min(1.0, dn.z))))
    rz = math.degrees(math.atan2(-dn.x, dn.y))
    return Part(name, 'paddle', loc=tuple((a + b) / 2), radius=1.0, scale=(width / 2, L / 2, 0.012), rot=(rx, 0.0, rz), taper=0.55)


def _prop_parts() -> list[tuple[Part, int]]:
    """Each prop part with its id: 10*wing index + side code for a wing, 100+ for antennae, 200+ for props."""
    out = []
    for i, w in enumerate(WINGS):
        for s in (1, -1):
            pts = [_m(p, s) for p in w['points']]
            out.append((_paddle(f'w{i}{s}', pts[0], pts[-1], w['width']), 10 * i + (1 if s > 0 else 2)))
    for j, c in enumerate(CHAINS):
        for s in ((1, -1) if c.get('mirror') else (1,)):
            pts = [_m(p, s) for p in c['points']]
            r = 0.022 if not HOVER else 0.016
            for k in range(len(pts) - 1):
                out.append((Part(f'an{j}{s}{k}', 'capsule', loc=pts[k], to=pts[k + 1], radius=r), 100 + 2 * j + (0 if s > 0 else 1)))
            if not HOVER:
                out.append((Part(f'nub{j}{s}', 'sphere', loc=pts[-1], radius=0.04), 100 + 2 * j + (0 if s > 0 else 1)))
    for k, pr in enumerate(PROPS):
        out.append((Part(pr['name'], 'tube', loc=pr['head'], to=pr['tail'], radius=0.035, r2=0.025), 200 + k))
    return out


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for p, pid in _prop_parts():
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
                tag = 'L' if s > 0 else 'R'
                pts = [_m(p, s) for p in w['points']]
                segs = [(f"{w['name']}{tag}.{k + 1}", pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
                regs.append((m, U.segment_weights(co[m], segs, power=4.0)))
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


# ----------------------------------------------------------------------------- eyes (a cocoon's hide inside it)
def _eye_centre(s: int) -> Vector:
    if COCOON:
        return Vector((0.05 * s, -0.1, 0.8))
    return HEAD_C + Vector((0.42 * HEAD_R * s, -0.78 * HEAD_R, 0.22 * HEAD_R))


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 32 if high else 16
    r = 0.02 if COCOON else 0.3 * HEAD_R
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    c = _eye_centre(s)
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.8, v.co.y * 0.6, v.co.z)) + c
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def blink_pivot(s: int):
    c = _eye_centre(s)
    return c + Vector((0.0, 0.01, 0.0)), Vector((0.0, 0.0, 1.0)), Vector((0.0, -1.0, 0.0))


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


REVIEW = {'crawl': {'centre': (0.0, -0.1, 0.32), 'size': 1.7, 'head': ((0.0, -0.62, 0.46), 0.6)},
          'hover': {'centre': (0.0, 0.0, 0.66), 'size': 2.3, 'head': ((0.0, -0.24, 0.72), 0.45)},
          'cocoon': {'centre': (0.0, 0.0, 0.85), 'size': 1.3, 'head': ((0.0, 0.0, 0.8), 0.7)}}[FORM]
