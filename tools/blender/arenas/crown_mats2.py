"""The Crown Amphitheatre's painted crowd, cloth, metal, fire, ground and foliage materials (Cycles, baked).

The painted far crowd: every seat row the game does not seat itself is painted with people, one per ~0.52 m of row,
drawn from face attributes the bowl writes (`crowd` = how full, `riser` = 1 on the step fronts, `v0` + `hgt` = where
the face starts and how tall or deep it is, `row` and `wedge` = the seeds). On the step fronts (what you see from the
floor) each person is a torso and a head with hair or a hat; on the treads (seen from above) a lap, shoulders and the
top of a head. Gaps between people are dark, so the rows read as depth.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib.nodes import NB, new_mat
import kit as K
from crown_mats import attr, ao, mul, obj_co, ramp_const, stretched, uv_vec, weather

CLOTHES = ['#A8483E', '#C98E4A', '#4C8478', '#55759E', '#76608E', '#CDB878', '#6E8A55', '#DCD0B4', '#A06476',
           '#6890A0', '#93573A', '#7D8648', '#C58668', '#3E5A74', '#E6DCC6', '#8A7A60']
SKIN = ['#F2D0B3', '#E8B894', '#D69E78', '#B97F59', '#8F5E3E', '#6B4430', '#F6DCC4', '#C48E68']
HAIR = ['#2E2119', '#5C3B22', '#1F1A17', '#A06F38', '#D2AE6C', '#7E3626', '#8F8A84', '#E9D9A0']
GAP = '#3A322B'
PITCH = 0.52


def _wn(nb: NB, vec):
    n = nb.new('ShaderNodeTexWhiteNoise', noise_dimensions='3D')
    nb.put(n.inputs['Vector'], vec)
    return n.outputs['Value'], n.outputs['Color']


def _ellipse(nb: NB, x, y, cx: float, cy, rx: float, ry: float, soft: float = 0.12):
    """1 inside the ellipse centred (cx, cy) with radii rx, ry (all in 'person' units), soft edge."""
    dx = nb.math('DIVIDE', nb.math('SUBTRACT', x, cx), rx)
    dy = nb.math('DIVIDE', nb.math('SUBTRACT', y, cy), ry)
    d = nb.math('ADD', nb.math('MULTIPLY', dx, dx), nb.math('MULTIPLY', dy, dy))
    return nb.smooth(d, 1.0 + soft, 1.0 - soft)


def _band(nb: NB, x, lo: float, hi: float, soft: float = 0.03):
    return nb.math('MULTIPLY', nb.smooth(x, lo - soft, lo + soft), nb.smooth(x, hi + soft, hi - soft))


def crowd_paint(nb: NB, stone):
    """Mix the painted crowd over `stone` where the face asks for one."""
    uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
    u, v, _ = nb.sep(uvn.outputs[0])
    dens, riser, v0, hgt = attr(nb, 'crowd'), attr(nb, 'riser'), attr(nb, 'v0'), attr(nb, 'hgt')
    row, wedge = attr(nb, 'row'), attr(nb, 'wedge')
    cu = nb.math('ADD', nb.math('DIVIDE', u, PITCH), nb.math('MULTIPLY', row, 0.383))     # each row staggered
    ci = nb.math('FLOOR', cu)
    r1, c1 = _wn(nb, nb.comb(ci, row, wedge))
    r2, c2 = _wn(nb, nb.comb(nb.math('ADD', ci, 17.3), nb.math('ADD', row, 5.1), wedge))
    rr = nb.sep_rgb(c1)
    rs = nb.sep_rgb(c2)
    fx = nb.math('SUBTRACT', nb.math('FRACT', cu), nb.math('MULTIPLY_ADD', rs[0], 0.16, 0.42))    # -0.5..0.5, jittered
    vn = nb.math('DIVIDE', nb.math('SUBTRACT', v, v0), nb.math('MAXIMUM', hgt, 0.05))
    present = nb.smooth(nb.math('SUBTRACT', dens, r1), -0.02, 0.02)
    shirt = ramp_const(nb, rr[0], CLOTHES)
    fan = attr(nb, 'fan')                                    # supporters: teal toward gate A, coral toward gate B
    fan_on = nb.math('LESS_THAN', r2, nb.math('MULTIPLY', nb.math('ABSOLUTE', fan), 0.4))
    shirt = nb.mix(fan_on, shirt, nb.mix(nb.math('GREATER_THAN', fan, 0.0), C.lin('#C24F38'), C.lin('#1F7A72')))
    shirt = mul(nb, shirt, nb.math('MULTIPLY_ADD', rr[1], 0.3, 0.8))
    skin = ramp_const(nb, rr[2], SKIN)
    hair = ramp_const(nb, rs[1], HAIR)
    hat = nb.smooth(rs[2], 0.78, 0.8)                       # about one in five wears a hat (a shirt colour, lighter)
    hair = nb.mix(hat, hair, nb.mix(0.45, ramp_const(nb, r2, CLOTHES), C.lin('#F4ECD8')))
    ax = nb.math('ABSOLUTE', fx)
    # --- the step fronts: torso, head, hair (vn 0 at the foot of the riser, 1 at its top)
    tall = nb.math('MULTIPLY_ADD', rs[0], 0.12, 0.0)          # people differ in height a little
    vt = nb.math('SUBTRACT', vn, tall)
    width = nb.math('SUBTRACT', 0.4, nb.math('MULTIPLY', vt, 0.14))          # narrower toward the shoulders
    torso = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', width, ax), 0.0, 0.06), nb.smooth(vt, 0.66, 0.58))
    head = _ellipse(nb, fx, vt, 0.0, 0.79, 0.145, 0.175)
    hair_m = nb.math('MULTIPLY', head, nb.smooth(nb.math('SUBTRACT', vt, nb.math('MULTIPLY', ax, 0.5)), 0.78, 0.84))
    arm = nb.math('MULTIPLY', nb.smooth(r2, 0.9, 0.92), nb.math('MULTIPLY', _band(nb, fx, 0.28, 0.38), _band(nb, vt, 0.45, 1.05)))
    behind = nb.mix(0.55, C.lin(GAP), mul(nb, ramp_const(nb, nb.math('FRACT', nb.math('MULTIPLY', r1, 7.3)), CLOTHES), 0.42))   # people further back
    round_ = nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', nb.math('POWER', nb.math('DIVIDE', ax, 0.4), 2.0), 0.45))
    front = nb.mix(torso, behind, mul(nb, shirt, round_))
    front = nb.mix(nb.math('MAXIMUM', head, arm), front, skin)
    front = nb.mix(hair_m, front, hair)
    shade = nb.math('MULTIPLY_ADD', vt, 0.25, 0.8)            # a little darker low down, lighter on the shoulders
    front = mul(nb, front, nb.math('MINIMUM', 1.05, shade))
    # --- the treads, from above (vn 0 at the front edge, 1 at the back): knees, shoulders, the top of the head
    lap = nb.math('MULTIPLY', _band(nb, vn, 0.05, 0.45), nb.smooth(ax, 0.34, 0.28))
    back = nb.math('MULTIPLY', _band(nb, vn, 0.4, 0.78), nb.smooth(ax, 0.44, 0.38))
    # (smooth(x, a, b) with a > b falls from 1 to 0: inside the half-width)
    crown = _ellipse(nb, fx, vn, 0.0, 0.6, 0.17, 0.14)
    top = nb.mix(lap, behind, mul(nb, shirt, 0.55))
    top = nb.mix(back, top, shirt)
    top = nb.mix(crown, top, hair)
    paint = nb.mix(riser, top, front)
    # a little of the stone's own light and grain shows through, so the paint sits in the same world
    paint = nb.mix(0.12, paint, stone, blend='MULTIPLY')
    return nb.mix(present, mul(nb, stone, 0.72), paint)          # an empty seat sits in the crowd's shade


# ----------------------------------------------------------------------------- cloth
def linen(nb: NB, base, tile: float = 0.35):
    d, _ = K.tex_nodes(nb, 'rough_linen', uv_vec(nb, tile), 'FLAT', normal=False)
    k = nb.math('MULTIPLY_ADD', K.lum(nb, d.outputs['Color']), 0.5, 0.72)
    return nb.mix(1.0, base, nb.comb(k, k, k), blend='MULTIPLY'), d


def stripes(name: str, a: str, b: str, width: float, edge: str | None = None) -> bpy.types.Material:
    """Awning cloth: stripes `width` m wide along UVMap u, a hem colour near v = 0 (the free edge)."""
    m, nb = new_mat(name)
    uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
    u, v, _ = nb.sep(uvn.outputs[0])
    s = nb.smooth(nb.math('PINGPONG', nb.math('DIVIDE', u, width), 1.0), 0.48, 0.52)
    col = nb.mix(s, C.lin(a), C.lin(b))
    if edge:
        col = nb.mix(nb.smooth(v, 0.55, 0.45), col, C.lin(edge))
    col, d = linen(nb, col, 0.5)
    col = weather(nb, col, streak=0.2, grime=0.25, wear=0.0, foot=0.0, ao_dist=0.6)
    K.principled(nb, col, 0.9, K.bump_from(nb, K.lum(nb, d.outputs['Color']), 0.2, 0.01), 0.15)
    return m


def banner(name: str, base: str, trim: str, emblem_img, gold: str = '#E7B24C') -> bpy.types.Material:
    """A hanging banner (UV 0..1 over the cloth, v = 1 at the top): linen, a border, the Guild emblem in gold."""
    m, nb = new_mat(name)
    uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
    u, v, _ = nb.sep(uvn.outputs[0])
    col, d = linen(nb, C.lin(base), 0.08)
    du = nb.math('ABSOLUTE', nb.math('SUBTRACT', u, 0.5))
    yw = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, v), nb.math('MAXIMUM', attr(nb, 'aspect'), 1.0))   # banner widths down from the top
    border = nb.math('MAXIMUM', nb.smooth(du, 0.4, 0.42), nb.smooth(yw, 0.07, 0.05))
    border = nb.math('MAXIMUM', border, nb.math('SUBTRACT', 1.0, nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', yw, 0.17)), 0.012, 0.022)))
    col = nb.mix(border, col, C.lin(trim))
    t = nb.new('ShaderNodeTexImage', image=emblem_img, interpolation='Linear')
    t.extension = 'CLIP'
    em_uv = nb.comb(nb.math('MULTIPLY_ADD', nb.math('SUBTRACT', u, 0.5), 1.3, 0.5), nb.math('MULTIPLY_ADD', nb.math('SUBTRACT', 0.72, yw), 1.3, 0.5), 0.0)
    nb.link(em_uv, t.inputs['Vector'])
    em = nb.sep_rgb(t.outputs['Color'])[0]
    col = nb.mix(em, col, C.lin(gold))
    col = weather(nb, col, streak=0.15, grime=0.2, wear=0.0, foot=0.0, ao_dist=0.3)
    K.principled(nb, col, 0.85, K.bump_from(nb, nb.math('ADD', em, K.lum(nb, d.outputs['Color'])), 0.12, 0.004), 0.2)
    return m


def cloth(name: str, hexcol: str) -> bpy.types.Material:
    m, nb = new_mat(name)
    col, d = linen(nb, C.lin(hexcol), 0.3)
    col = weather(nb, col, streak=0.15, grime=0.3, wear=0.0, foot=0.0, ao_dist=0.4)
    K.principled(nb, col, 0.9, K.bump_from(nb, K.lum(nb, d.outputs['Color']), 0.2, 0.01), 0.15)
    return m
