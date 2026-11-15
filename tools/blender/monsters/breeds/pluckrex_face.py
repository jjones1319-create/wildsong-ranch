"""Pluckrex's face: the glossy eye lenses (big, bright and determined: an amber-brown iris made from the navy and the
gold, a big navy pupil, two catchlights and a dark upper lash line; 4-details panel 2), the blink pivots, and the body
material's per-pixel face marks (the thick navy brows, the nostrils, the closed lids' lash lines). Metres; -Y front."""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib import marks as MK
from lib import surface as S
from lib.nodes import NB, new_mat
from lib.surface import v3
from monsters.breeds import pluckrex_hide as HD
from monsters.breeds import pluckrex_paint as PA
from monsters.breeds import pluckrex_props as PR

IRIS_R, PUPIL_R = 0.87, 0.5          # round 3: white showing at the corners; the pupil about 57% of the iris


def build_eye(F, name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 32
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    sx, sy, sz = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1], F.EYE_R * F.EYE_DEPTH[0]
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = F.eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((sx, sy, sz)))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def blink_pivot(F, s: int):
    c, _xax, yax, look = F.eye_frame(s)
    return c - yax * (F.EYE_R * (HD.LID_LASH + 0.5 * HD.LID_DROP)) - look * (F.EYE_R * 0.6), yax, look


def eye_material(F, name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    col = PA.colours(pal or F.PALETTE)
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    ix = nb.math('ADD', x, nb.math('MULTIPLY', side, 0.04))
    iy = nb.math('ADD', y, 0.01)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), IRIS_R)
    pr = PUPIL_R / IRIS_R
    # round 2: a big navy pupil, a crisp dark ring, the amber iris lighter toward its middle, a dark outer rim
    # polish: brown at the pupil, warm amber, honey-gold toward the rim, a soft dark rim; wider steps (no stair-steps)
    iris = nb.ramp(ri, [(0.0, C.lin(col['pupil'])), (pr * 0.95, C.lin(col['pupil'])), (pr + 0.05, C.lin(col['iris_deep'])),
                        (0.66, C.lin(col['iris'])), (0.86, C.lin(col['iris_lite'])), (0.95, C.lin(col['iris_rim'])),
                        (1.02, C.lin(col['iris_rim'])), (1.08, C.lin(col['sclera'])), (1.8, C.lin(col['sclera']))])
    ang = nb.math('ARCTAN2', iy, ix)
    # the fibres only on the iris (round 1 had the smoothstep's ends swapped: streaks covered the pupil)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 36.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', nb.smooth(ri, pr + 0.04, pr + 0.14), nb.smooth(ri, 0.95, 0.84)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.3), iris, nb.rgb(C.lin(col['iris_lite'])))      # round 3: clear radial streaks
    low = nb.math('MULTIPLY', nb.smooth(iy, -0.05, -0.55), nb.math('MULTIPLY', nb.smooth(ri, 0.96, 0.75), nb.smooth(ri, pr + 0.02, pr + 0.12)))
    c = nb.mix(nb.math('MULTIPLY', low, 0.55), iris, nb.rgb(C.lin(col['iris_lite'])))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, 0.18), nb.math('DIVIDE', nb.math('SUBTRACT', iy, 0.22), 1.1), 0.0)), 0.15, 0.12)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, 0.17), nb.math('ADD', iy, 0.2), 0.0)), 0.08, 0.06)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    # a crisp, thick dark upper lid line, flicking up at the outer corner
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', x, side), 0.15, 0.95), 0.2)
    lash = nb.smooth(nb.math('ADD', y, outer), 0.76, 0.81)      # polish: the lid's dark edge just over the iris's top
    c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
    lid = nb.smooth(nb.math('ADD', y, outer), 0.86, 0.9)          # the upper lid itself above it, in the hide's colour
    c = nb.mix(lid, c, nb.rgb(C.lin(col['body'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


_BROWS: dict = {}


def brow_segments(F) -> list[tuple]:
    """Each brow: a short, thick navy arc above the eye, rising toward its outer end (2-turnaround front, 3-faces)."""
    if id(F) in _BROWS:
        return _BROWS[id(F)]
    arc = F.G['brow_arc']
    parts = F.head_parts()
    out = []
    for s in (1, -1):
        c, xax, yax, look = F.eye_frame(s)
        pts = []
        for dx, dz, th in arc:
            q = c + Vector((dx * F.EYE_R * s, 0.0, dz * F.EYE_R))
            hit, _n = PR.surface_point(F, (q.x, q.y - 0.3, q.z), (0.0, 1.0, 0.0), parts, reach=0.5, step=0.001)
            p = hit if hit is not None else v3(q)
            pts.append((tuple(map(float, p)), th * F.EYE_R * 1.4))      # polish: thicker navy brows
        for (a, ta), (b, tb) in zip(pts[:-1], pts[1:]):
            out.append((a, b, 0.5 * (ta + tb)))
    _BROWS[id(F)] = out
    return out


def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def body_material(F, name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the paint, with the face's details per pixel on the pre-carve skin ('root'): the brows, the nostrils
    and the closed lids' lash lines."""
    col = PA.colours(pal)
    m, nb = new_mat(name)
    pos = nb.attribute('root').outputs['Vector']
    c = nb.attribute(attr).outputs['Color']
    segs = [MK.line(nb, pos, a, b, w, soft=0.12) for a, b, w in brow_segments(F)]      # round 2: crisp brows
    c = nb.mix(MK.union(nb, segs), c, nb.rgb(C.lin(col['brow'])))
    N = F.G['nose']
    nos = None
    for s in (1, -1):
        e = _ell(nb, pos, (N['dx'] * s, N['c'][1], N['c'][2]), tuple(N['r'] * v for v in N['paint']), 0.3)
        nos = e if nos is None else nb.math('MAXIMUM', nos, e)
    c = nb.mix(nb.math('MULTIPLY', nos, 0.9), c, nb.rgb(C.lin(col['nostril'])))
    lash = nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 2.2, clamp=True)
    c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
    # round 3: no painted smile line (it read as a cut past the corner); the crease is carved only
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
