"""A stand-in recipe for the shelled plan (plans/shelled.py): NOT a breed, never shipped or registered. By default a
tortoise with every tortoise option on: a domed shell with a tower prop, a pole prop flying a three-bone flag, a hanging
tassel at the back, a two-bone neck, a jaw, four legs with feet and a short tail. With WS_SHELLED_CRAB=1 it is the crab
option instead: an upright shell on six legs, two claws (the big one on its right) with moving pincers, eye stalks with
visors (the blink bones ride them: EYE_PARENTS), two feelers and a crest prop. A plain velvet skin keeps builds fast.

    npm run art:shape -- _shelled_test
    tools/blender/slot.sh "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python-exit-code 1 --python tools/blender/monsters/build_ultra.py -- --breed _shelled_test_ultra --quick --cpu --out <dir>
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

ID = '_shelled_test'
LOOK = '_shelled_test-ultra'
PLAN = 'shelled'
HEIGHT_UNITS = 165
PALETTE = {'body': '#C9A66B', 'belly': '#E8D4A8', 'accent': '#3AA6A1', 'eye': '#2B2B2B'}
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')     # the jaw's heat goes to the head; the lower lip is weighted to it below
BODY_TRIS = 24000
ATLAS_STRIP = 0
FACE_NOTE = 'A stand-in for the shelled plan: baked face, glossy lenses, blink bones.'
CRAB = os.environ.get('WS_SHELLED_CRAB') == '1'


def _m(p, s: int):
    return (p[0] * s, p[1], p[2])


if not CRAB:
    HIP = (0.0, 0.02, 0.42)
    CHEST = (0.0, -0.3, 0.38)
    SHELL = {'loc': (0.0, 0.02, 0.42), 'r': (0.36, 0.43, 0.26)}
    HEAD_C = Vector((0.0, -0.58, 0.55))
    HEAD_R = 0.12
    NECK = [(0.0, -0.3, 0.38), (0.0, -0.4, 0.43), (0.0, -0.48, 0.5)]
    LEGS = [{'hip': (0.22, -0.22, 0.32), 'knee': (0.27, -0.24, 0.2), 'ankle': (0.27, -0.25, 0.06), 'toe': (0.27, -0.33, 0.03),
             'parent': 'chest'},
            {'hip': (0.22, 0.25, 0.32), 'knee': (0.27, 0.27, 0.2), 'ankle': (0.27, 0.28, 0.06), 'toe': (0.27, 0.2, 0.03)}]
    TAIL = [(0.0, 0.44, 0.3), (0.0, 0.53, 0.25), (0.0, 0.6, 0.2)]
    TOWER = {'name': 'tower', 'parent': 'hips', 'head': (0.0, 0.08, 0.64), 'tail': (0.0, 0.08, 0.86)}
    POLE = {'name': 'pole', 'parent': 'prop.tower', 'head': (0.0, 0.08, 0.86), 'tail': (0.0, 0.08, 1.04)}
    FLAG = [(0.0, 0.08, 1.0), (0.08, 0.09, 0.995), (0.16, 0.1, 0.99), (0.24, 0.11, 0.985)]
    TASSEL = [(0.0, 0.42, 0.3), (0.0, 0.45, 0.22), (0.0, 0.46, 0.14)]
    EYE_PARENTS = None
else:
    HIP = (0.0, 0.02, 0.4)
    CHEST = (0.0, -0.12, 0.38)
    SHELL = {'loc': (0.0, 0.02, 0.42), 'r': (0.325, 0.21, 0.26)}
    HEAD_C = Vector((0.0, -0.17, 0.5))
    HEAD_R = 0.12
    LEGS = [{'hip': (0.22, -0.08, 0.32), 'knee': (0.36, -0.12, 0.38), 'ankle': (0.44, -0.16, 0.03)},
            {'hip': (0.24, 0.02, 0.3), 'knee': (0.4, 0.03, 0.36), 'ankle': (0.48, 0.05, 0.03)},
            {'hip': (0.22, 0.12, 0.3), 'knee': (0.36, 0.17, 0.34), 'ankle': (0.42, 0.24, 0.03)}]
    CLAWS = {'L': {'shoulder': (0.24, -0.12, 0.44), 'elbow': (0.34, -0.24, 0.42), 'wrist': (0.3, -0.36, 0.44),
                   'tip': (0.27, -0.48, 0.46), 'finger': ((0.29, -0.38, 0.41), (0.27, -0.47, 0.41)), 'open_axis': (1, 0, 0)},
             'R': {'shoulder': (-0.25, -0.12, 0.46), 'elbow': (-0.38, -0.22, 0.5), 'wrist': (-0.38, -0.34, 0.58),
                   'tip': (-0.36, -0.52, 0.7), 'finger': ((-0.4, -0.36, 0.52), (-0.4, -0.52, 0.6)), 'open_axis': (1, 0, 0)}}
    STALKS = {'base': (0.07, -0.12, 0.64), 'mid': (0.08, -0.13, 0.74), 'tip': (0.09, -0.14, 0.82),
              'visor': ((0.09, -0.12, 0.87), (0.09, -0.2, 0.86))}
    FEELER = [(0.04, -0.18, 0.58), (0.06, -0.26, 0.66), (0.07, -0.3, 0.74)]
    CREST = {'name': 'crest', 'parent': 'hips', 'head': (0.0, 0.02, 0.66), 'tail': (0.0, 0.02, 0.76)}
    EYE_PARENTS = {'L': 'stalkL.2', 'R': 'stalkR.2'}


def rig_p() -> dict:
    p = {'hip': HIP, 'chest': CHEST, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R, 'legs': LEGS, 'jaw_open': True,
         'shell_top': (0.0, 0.02, 0.68)}
    if not CRAB:
        p.update({'neck': NECK, 'head_tip': (0.0, -0.68, 0.56), 'jaw': {'head': (0.0, -0.55, 0.5), 'tail': (0.0, -0.67, 0.49)},
                  'tail': TAIL, 'props': [TOWER, POLE], 'strike_style': 'bash', 'ko_roll': 85.0,
                  'chains': [{'name': 'flag', 'kind': 'flag', 'parent': 'prop.pole', 'points': FLAG},
                             {'name': 'tassel', 'kind': 'tassel', 'parent': 'hips', 'points': TASSEL}]})
    else:
        p.update({'head_base': (0.0, -0.06, 0.5), 'head_tip': (0.0, -0.2, 0.5),
                  'jaw': {'head': (0.0, -0.16, 0.4), 'tail': (0.0, -0.22, 0.38)}, 'claws': CLAWS, 'big_claw': 'R',
                  'stalks': STALKS, 'props': [CREST], 'strike_style': 'claw', 'ko_roll': 165.0,
                  'chains': [{'name': 'feeler', 'kind': 'antenna', 'parent': 'head', 'points': FEELER, 'mirror': True}]})
    return p


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    sl, sr = SHELL['loc'], SHELL['r']
    if not CRAB:
        ps = [Part('carapace', 'sphere', loc=sl, radius=1.0, scale=sr),
              Part('plastron', 'sphere', loc=(0.0, 0.0, 0.3), radius=0.3, scale=(1.0, 1.25, 0.4)),
              Part('neck', 'tube', loc=NECK[0], to=NECK[-1], radius=0.075, r2=0.065),
              Part('head', 'sphere', loc=tuple(HEAD_C), radius=HEAD_R, scale=(0.95, 1.1, 0.9)),
              Part('beak', 'sphere', loc=(0.0, -0.66, 0.53), radius=0.06, scale=(1.0, 0.9, 0.7)),
              Part('jaw', 'sphere', loc=(0.0, -0.62, 0.49), radius=0.055, scale=(1.0, 1.1, 0.5)),
              Part('tail', 'tube', loc=TAIL[0], to=TAIL[-1], radius=0.04, r2=0.015),
              Part('tower', 'capsule', loc=TOWER['head'], to=TOWER['tail'], radius=0.09),
              Part('pole', 'capsule', loc=POLE['head'], to=POLE['tail'], radius=0.012),
              Part('tassel', 'capsule', loc=TASSEL[0], to=TASSEL[-1], radius=0.02)]
        for i in range(len(FLAG) - 1):
            ps.append(Part(f'flag{i}', 'box', loc=tuple((Vector(FLAG[i]) + Vector(FLAG[i + 1])) / 2 + Vector((0, 0, -0.035 + 0.005 * i))),
                           radius=1.0, scale=(0.045, 0.012, 0.04 - 0.008 * i)))
        for tag, s in (('L', 1), ('R', -1)):
            for k, lg in enumerate(LEGS):
                ps.append(Part(f'thigh{k}{tag}', 'capsule', loc=_m(lg['hip'], s), to=_m(lg['knee'], s), radius=0.07))
                ps.append(Part(f'shin{k}{tag}', 'capsule', loc=_m(lg['knee'], s), to=_m(lg['ankle'], s), radius=0.065))
                ps.append(Part(f'foot{k}{tag}', 'sphere', loc=_m((0.27, lg['toe'][1] + 0.03, 0.04), s), radius=0.07, scale=(1.0, 1.2, 0.55)))
        return ps
    ps = [Part('shell', 'sphere', loc=sl, radius=1.0, scale=sr),
          Part('belly', 'sphere', loc=(0.0, -0.08, 0.36), radius=0.2, scale=(1.2, 0.6, 0.9)),
          Part('mouth', 'sphere', loc=(0.0, -0.18, 0.4), radius=0.05, scale=(1.4, 0.6, 0.6)),
          Part('crest', 'capsule', loc=CREST['head'], to=CREST['tail'], radius=0.03)]
    for tag, s in (('L', 1), ('R', -1)):
        ps.append(Part(f'stalk{tag}', 'tube', loc=_m(STALKS['base'], s), to=_m(STALKS['tip'], s), radius=0.025, r2=0.02))
        ps.append(Part(f'visor{tag}', 'sphere', loc=_m((0.09, -0.15, 0.865), s), radius=0.05, scale=(1.0, 1.1, 0.35)))
        ps.append(Part(f'feeler{tag}', 'tube', loc=_m(FEELER[0], s), to=_m(FEELER[-1], s), radius=0.012, r2=0.005))
        for k, lg in enumerate(LEGS):
            ps.append(Part(f'thigh{k}{tag}', 'capsule', loc=_m(lg['hip'], s), to=_m(lg['knee'], s), radius=0.04))
            ps.append(Part(f'shin{k}{tag}', 'tube', loc=_m(lg['knee'], s), to=_m(lg['ankle'], s), radius=0.035, r2=0.012))
        c = CLAWS[tag]
        big = tag == 'R'
        ps.append(Part(f'arm{tag}', 'capsule', loc=c['shoulder'], to=c['elbow'], radius=0.05 if big else 0.035))
        ps.append(Part(f'fore{tag}', 'capsule', loc=c['elbow'], to=c['wrist'], radius=0.06 if big else 0.04))
        ps.append(Part(f'claw{tag}', 'tube', loc=c['wrist'], to=c['tip'], radius=0.085 if big else 0.05, r2=0.02))
        ps.append(Part(f'pincer{tag}', 'tube', loc=c['finger'][0], to=c['finger'][1], radius=0.04 if big else 0.025, r2=0.012))
    return ps


def _near(co: np.ndarray, pts, r: float) -> np.ndarray:
    d = np.full(len(co), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.array(a), np.array(b)
        ab = b - a
        u = np.clip(((co - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        d = np.minimum(d, np.linalg.norm(co - (a + u[:, None] * ab), axis=1))
    return d < r


def _in_shell(co: np.ndarray, k: float = 1.0) -> np.ndarray:
    return np.linalg.norm((co - np.array(SHELL['loc'])) / np.array(SHELL['r']), axis=1) < k


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    if not CRAB:
        return {'face': (y < -0.6) & (z > 0.45) & (np.abs(x) < 0.12), 'belly': (z < 0.24) & (np.abs(x) < 0.25) & (np.abs(y) < 0.35)}
    return {'face': (y < -0.12) & (z > 0.34) & (z < 0.56) & (np.abs(x) < 0.16), 'belly': (y < -0.1) & (z < 0.36) & (np.abs(x) < 0.2)}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    regs = []
    if not CRAB:
        # the shell (and the tower on it) rigid; the neck, head and legs keep their heat weights outside it
        plastron = np.linalg.norm((co - np.array([0.0, 0.0, 0.3])) / np.array([0.3, 0.375, 0.12]), axis=1) < 1.06
        shell = _in_shell(co, 1.04) | plastron
        open_ = _near(co, NECK[:2], 0.1) & ~_in_shell(co, 0.9)
        regs.append(U.rigid(shell & ~open_, 'hips'))
        tower = _near(co, [TOWER['head'], TOWER['tail']], 0.11) & (co[:, 2] > 0.62)
        regs.append(U.rigid(tower, 'prop.tower'))
        pole = _near(co, [POLE['head'], POLE['tail']], 0.03) & (co[:, 2] > 0.86)
        regs.append(U.rigid(pole, 'prop.pole'))
        fl = (co[:, 2] > 0.9) & (co[:, 0] > 0.012)
        regs.append((fl, U.chain_weights(co[fl], FLAG, ['flag.1', 'flag.2', 'flag.3'], 'prop.pole')))
        ts = _near(co, TASSEL, 0.035) & ~_in_shell(co, 0.98)
        regs.append((ts, U.chain_weights(co[ts], TASSEL, ['tassel.1', 'tassel.2'], 'hips')))
        tl = _near(co, TAIL, 0.05) & ~_in_shell(co, 1.0) & (co[:, 1] > 0.42)
        regs.append((tl, U.chain_weights(co[tl], TAIL, ['tail.1', 'tail.2'], 'hips')))
        jaw = (co[:, 1] < -0.56) & (co[:, 2] < 0.505) & (co[:, 2] > 0.44) & (np.abs(co[:, 0]) < 0.07)
        regs.append(U.rigid(jaw, 'jaw'))
        return regs
    regs.append(U.rigid(_in_shell(co, 1.06) | (_near(co, [(0, -0.08, 0.36)], 0.26) & (co[:, 2] > 0.18)), 'hips'))
    face = (co[:, 1] < -0.14) & (co[:, 2] > 0.42) & (co[:, 2] < 0.6) & (np.abs(co[:, 0]) < 0.14)
    regs.append(U.rigid(face, 'head'))
    jaw = (co[:, 1] < -0.15) & (co[:, 2] < 0.42) & (co[:, 2] > 0.34) & (np.abs(co[:, 0]) < 0.08)
    regs.append(U.rigid(jaw, 'jaw'))
    regs.append(U.rigid((co[:, 2] > 0.66) & (np.abs(co[:, 0]) < 0.05) & (np.abs(co[:, 1] - 0.02) < 0.05), 'prop.crest'))
    for tag, s in (('L', 1), ('R', -1)):
        side = np.sign(co[:, 0]) == s
        sp = [_m(STALKS[k], s) for k in ('base', 'mid', 'tip')]
        st = _near(co, sp, 0.04) & side & (co[:, 2] > 0.62)
        regs.append((st, U.chain_weights(co[st], sp, [f'stalk{tag}.1', f'stalk{tag}.2'], 'head')))
        vz = (np.linalg.norm((co - np.array(_m((0.09, -0.15, 0.865), s))) / np.array([1.0, 1.1, 0.35]), axis=1) < 0.065) & side
        regs.append(U.rigid(vz, f'visor.{tag}'))
        fp = [_m(p, s) for p in FEELER]
        fm = _near(co, fp, 0.025) & side & (co[:, 2] > 0.57)
        regs.append((fm, U.chain_weights(co[fm], fp, [f'feeler{tag}.1', f'feeler{tag}.2'], 'head')))
        for k, lg in enumerate(LEGS, start=1):
            pts = [_m(lg['hip'], s), _m(lg['knee'], s), _m(lg['ankle'], s)]
            lm = _near(co, pts, 0.05) & side & ~_in_shell(co, 0.95)
            regs.append((lm, U.segment_weights(co[lm], [('hips', pts[0], pts[0]), (f'leg{k}.{tag}', pts[0], pts[1]),
                                                        (f'shin{k}.{tag}', pts[1], pts[2])])))
        c = CLAWS[tag]
        big = tag == 'R'
        segs = [(f'arm.{tag}', c['shoulder'], c['elbow']), (f'forearm.{tag}', c['elbow'], c['wrist']),
                (f'claw.{tag}', c['wrist'], c['tip']), (f'pincer.{tag}', c['finger'][0], c['finger'][1])]
        cm = _near(co, [c['shoulder'], c['elbow'], c['wrist'], c['tip']], 0.1 if big else 0.07) & side & ~_in_shell(co, 0.97)
        cm |= _near(co, list(c['finger']), 0.05 if big else 0.035) & side
        regs.append((cm, U.segment_weights(co[cm], segs, power=8.0)))
    return regs


# ----------------------------------------------------------------------------- eyes
def _eye_centre(s: int) -> Vector:
    if CRAB:
        return Vector(_m(STALKS['tip'], s)) + Vector((0.0, -0.025, 0.005))
    return HEAD_C + Vector((0.06 * s, -0.08, 0.035))


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 32 if high else 16
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=0.04 if CRAB else 0.03)
    c = _eye_centre(s)
    for v in bm.verts:
        v.co = Vector((v.co.x, v.co.y * (0.9 if CRAB else 0.6), v.co.z)) + c
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
    rgb = np.where(z['belly'][:, None], _lin(PALETTE['belly'])[None], _lin(PALETTE['body'])[None])
    if not CRAB:
        acc = (co[:, 2] > 0.9) & (co[:, 0] > 0.012)
    else:
        acc = (np.abs(co[:, 0]) > 0.2) & (co[:, 1] < -0.2)
    return np.where(acc[:, None], _lin(PALETTE['accent'])[None], rgb)


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        co, _ = S.mesh_arrays(ob)
        S.set_colour_attr(ob, 'paint', preview_colours(co, None))
        S.set_colour_attr(ob, 'rough', np.tile(np.array([1.0, 0.55, 0.15]), (len(co), 1)))


def body_material(name: str, attr: str, pal: dict, marks):
    return BK.emission_attr_material(name, attr)


REVIEW = ({'centre': (0.0, -0.05, 0.42), 'size': 1.5, 'head': ((0.0, -0.17, 0.62), 0.7)} if CRAB
          else {'centre': (0.0, -0.05, 0.45), 'size': 1.7, 'head': ((0.0, -0.58, 0.55), 0.6)})
