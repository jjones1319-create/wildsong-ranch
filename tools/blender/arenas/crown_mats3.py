"""The Crown Amphitheatre's wood, metal, fire, clay, ground, foliage and far-mountain materials (Cycles, baked), and
the Guild emblem as an image (emblem.py's mask)."""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib.nodes import new_mat
import kit as K
from crown_mats import attr, mul, obj_co, ramp_const, stretched, uv_vec, weather


# ----------------------------------------------------------------------------- wood, iron, fire, clay
def wood(name: str, tint: str = '#8A6748', tile: float = 1.6) -> bpy.types.Material:
    m, nb = new_mat(name)
    d, n = K.tex_nodes(nb, 'weathered_planks', uv_vec(nb, tile, math.pi / 2), 'FLAT')
    col = K.grade(nb, d.outputs['Color'], 0.5, 0.85, 0.95, C.srgb(tint), 0.35, 0.0)
    col = weather(nb, col, streak=0.2, grime=0.4, wear=0.2, foot=0.0, ao_dist=0.3)
    K.principled(nb, col, 0.85, K.normal_map(nb, n, 0.6), 0.2)
    return m


def iron(name: str) -> bpy.types.Material:
    m, nb = new_mat(name)
    co = obj_co(nb)
    rust = nb.smooth(nb.noise(co, 4.0, 4.0, 0.65), 0.5, 0.7)
    col = nb.mix(nb.math('MULTIPLY', rust, 0.7), C.lin('#34302D'), C.lin('#7A4A2A'))
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(nb.noise(stretched(nb, co, 3, 3, 0.4), 3.0, 2.0, 0.5), 0.55, 0.75), 0.5), col, C.lin('#8E5A33'))
    K.principled(nb, col, 0.55, K.bump_from(nb, rust, 0.3, 0.005), 0.4)
    return m


def flame(name: str) -> bpy.types.Material:
    """Fire: emission only, white-gold at the root to orange-red at the tips (UVMap v = metres up the flame)."""
    m, nb = new_mat(name)
    uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
    v = nb.sep(uvn.outputs[0])[1]
    k = nb.math('DIVIDE', v, 0.75)
    col = nb.ramp(k, [(0.0, C.lin('#FFF3C2')), (0.35, C.lin('#FFC24A')), (0.7, C.lin('#F26A1B')), (1.0, C.lin('#B8321A'))])
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], col)
    em.inputs['Strength'].default_value = 3.0
    nb.output(em.outputs[0])
    return m


def terracotta(name: str) -> bpy.types.Material:
    """Clay urns: terracotta with dark glaze bands (UVMap v = metres up the urn)."""
    m, nb = new_mat(name)
    uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
    v = nb.sep(uvn.outputs[0])[1]
    co = obj_co(nb)
    col = nb.mix(nb.noise(co, 5.0, 3.0, 0.5), C.lin('#B4643C'), C.lin('#C97A4C'))
    bands = nb.math('MAXIMUM', nb.math('MAXIMUM', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.55)), 0.09, 0.07),
                                       nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.95)), 0.03, 0.02)),
                    nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.3)), 0.025, 0.015))
    col = nb.mix(bands, col, C.lin('#2B201B'))
    col = weather(nb, col, streak=0.3, grime=0.5, wear=0.3, foot=0.0, ao_dist=0.2)
    K.principled(nb, col, 0.7, None, 0.3)
    return m


def roof_tiles(name: str) -> bpy.types.Material:
    m, nb = new_mat(name)
    d, n = K.tex_nodes(nb, 'clay_roof_tiles_02', uv_vec(nb, 2.0), 'FLAT')
    col = K.grade(nb, d.outputs['Color'], 0.5, 0.9, 1.0, C.srgb('#B5603A'), 0.15, 0.0)
    col = weather(nb, col, streak=0.2, grime=0.3, wear=0.0, foot=0.0, ao_dist=0.5)
    K.principled(nb, col, 0.8, K.normal_map(nb, n, 0.6), 0.2)
    return m


# ----------------------------------------------------------------------------- outside
def grass(name: str) -> bpy.types.Material:
    """Dry summer grass with dusty paths (`path` attribute 0..1) on object metres."""
    m, nb = new_mat(name)
    g, _ = K.tex_nodes(nb, 'leafy_grass', K.coords(nb, 'Object', 2.6), 'FLAT', normal=False)
    dd, _ = K.tex_nodes(nb, 'dry_ground_rocks', K.coords(nb, 'Object', 2.2, 0.4), 'FLAT', normal=False)
    co = obj_co(nb)
    gcol = K.grade(nb, g.outputs['Color'], 0.52, 1.0, 1.15, C.srgb('#9AA552'), 0.35, 0.0)
    dry = nb.smooth(nb.noise(co, 0.02, 3.0, 0.55), 0.4, 0.65)
    gcol = nb.mix(nb.math('MULTIPLY', dry, 0.65), gcol, C.lin('#C9B670'))
    gcol = nb.mix(nb.math('MULTIPLY', nb.smooth(nb.noise(co, 0.3, 3.0, 0.6), 0.5, 0.7), 0.4), gcol, C.lin('#5E7A3A'))
    dcol = K.grade(nb, dd.outputs['Color'], 0.5, 0.8, 1.15, C.srgb('#C9A97A'), 0.3, 0.0)
    vor = nb.new('ShaderNodeTexVoronoi')                     # a patchwork of fields, each with its crop and rows
    nb.link(co, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 0.012
    cell = nb.sep_rgb(vor.outputs['Color'])
    crop = ramp_const(nb, cell[0], ['#C9B66E', '#9DAA55', '#B9A45E', '#7E9548', '#D6C482', '#A08A58', '#8FA35A'])
    rows = nb.smooth(nb.math('SINE', nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.sep(co)[0], nb.math('MULTIPLY_ADD', cell[1], 0.8, 0.2)),
                                                                        nb.math('MULTIPLY', nb.sep(co)[1], nb.math('MULTIPLY_ADD', cell[2], 0.8, 0.2))), 1.8)), -0.2, 0.6)
    crop = nb.mix(nb.math('MULTIPLY', rows, 0.25), crop, mul(nb, crop, 0.75))
    field = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.sep(co)[0], nb.sep(co)[1], 0.0)), 120.0, 160.0)
    gcol = nb.mix(nb.math('MULTIPLY', field, 0.75), gcol, crop)
    path = nb.smooth(nb.math('ADD', attr(nb, 'path'), nb.math('MULTIPLY', nb.math('SUBTRACT', nb.noise(co, 0.8, 3.0, 0.6), 0.5), 0.5)), 0.4, 0.6)
    col = nb.mix(path, gcol, dcol)
    K.principled(nb, col, 0.95, K.bump_from(nb, K.lum(nb, g.outputs['Color']), 0.25, 0.02), 0.15)
    return m


def foliage(name: str) -> bpy.types.Material:
    """Stylised leaves: soft clusters (voronoi), a per-tree tint (the `tint` face attribute picks one of four)."""
    m, nb = new_mat(name)
    co = obj_co(nb)
    cells = nb.voronoi(co, 4.5)
    tint = ramp_const(nb, attr(nb, 'tint'), ['#3E5F35', '#4A6B3A', '#35552F', '#56743E'])
    col = nb.mix(nb.math('MULTIPLY', nb.noise(co, 1.1, 3.0, 0.6), 0.6), tint, nb.mix(1.0, tint, (1.3, 1.25, 0.85, 1.0), blend='MULTIPLY'))
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(cells, 0.15, 0.55), 0.4), col, nb.mix(1.0, tint, (0.5, 0.55, 0.65, 1.0), blend='MULTIPLY'))
    K.principled(nb, col, 0.8, K.bump_from(nb, nb.math('SUBTRACT', 1.0, cells), 0.5, 0.06), 0.25)
    return m


def bark(name: str) -> bpy.types.Material:
    return K.photo_mat(name, 'bark_brown_02', 1.2, proj='BOX', sat=0.9, val=0.9, tint=C.srgb('#6A5440'), tint_mix=0.3)


def mountain(name: str, haze: str = '#C3D3E3') -> bpy.types.Material:
    m, nb = new_mat(name)
    co = obj_co(nb)
    z = nb.sep(co)[2]
    geo = nb.new('ShaderNodeNewGeometry')
    up = nb.sep(geo.outputs['Normal'])[2]
    n = nb.noise(co, 0.01, 4.0, 0.6)
    grass_c = nb.mix(n, C.lin('#6F8A4E'), C.lin('#A8A867'))
    rock = nb.mix(n, C.lin('#8C8476'), C.lin('#B0A796'))
    col = nb.mix(nb.smooth(up, 0.85, 0.6), grass_c, rock)
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(nb.noise(co, 0.004, 2.0, 0.5), 0.45, 0.6), 0.5), col, C.lin('#4E6B3E'))
    snow = nb.math('MULTIPLY', nb.smooth(nb.math('ADD', z, nb.math('MULTIPLY', n, 40.0)), 230.0, 280.0), nb.smooth(up, 0.45, 0.7))
    col = nb.mix(snow, col, C.lin('#F2F4F7'))
    dist = nb.new('ShaderNodeCameraData').outputs['View Distance']
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(dist, 500.0, 3200.0), 0.75), col, C.lin(haze))
    K.principled(nb, col, 0.9, None, 0.1)
    return m


def emblem_image(size: int = 1024) -> bpy.types.Image:
    from emblem import emblem_alpha
    a = emblem_alpha(size)
    img = bpy.data.images.new('crown_emblem', size, size, alpha=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.ascontiguousarray(np.stack([a, a, a, np.ones_like(a)], -1)[::-1], np.float32).ravel())
    img.pack()
    return img


def door(name: str) -> bpy.types.Material:
    """Dark oak planks with iron straps and studs (UVMap in metres across the door)."""
    m, nb = new_mat(name)
    d, _ = K.tex_nodes(nb, 'weathered_planks', uv_vec(nb, 1.2, math.pi / 2), 'FLAT', normal=False)
    col = K.grade(nb, d.outputs['Color'], 0.5, 0.8, 0.55, C.srgb('#4A3424'), 0.45, 0.0)
    uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
    u, v, _ = nb.sep(uvn.outputs[0])
    strap = nb.math('MAXIMUM', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.45)), 0.07, 0.05),
                    nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 1.35)), 0.07, 0.05))
    col = nb.mix(strap, col, C.lin('#2B2724'))
    col = weather(nb, col, streak=0.2, grime=0.5, wear=0.0, foot=0.3, ao_dist=0.2)
    K.principled(nb, col, 0.8, K.bump_from(nb, nb.math('ADD', strap, K.lum(nb, d.outputs['Color'])), 0.3, 0.01), 0.2)
    return m


def house(name: str) -> bpy.types.Material:
    """Town plaster in ochre, cream and rose (one per house, from its position), with shuttered windows and a door
    band drawn on our metre UVs (u along the wall, v up)."""
    m, nb = new_mat(name)
    d, _ = K.tex_nodes(nb, 'white_plaster_rough_01', K.coords(nb, 'Object', 2.2), 'BOX', normal=False)
    co = obj_co(nb)
    vor = nb.new('ShaderNodeTexVoronoi')
    nb.link(co, vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 0.09
    tint = ramp_const(nb, nb.sep_rgb(vor.outputs['Color'])[0], ['#E9D8B4', '#E2C08C', '#EBDDC6', '#D9A98A', '#E5CFA0', '#CFB48E'])
    col = nb.mix(1.0, tint, nb.mix(0.35, (1, 1, 1, 1), d.outputs['Color']), blend='MULTIPLY')
    uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
    u, v, _ = nb.sep(uvn.outputs[0])
    fu = nb.math('FRACT', nb.math('DIVIDE', u, 2.4))
    fv = nb.math('FRACT', nb.math('DIVIDE', nb.math('SUBTRACT', v, 0.6), 3.0))
    win = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(fu, 0.36, 0.4), nb.smooth(fu, 0.66, 0.62)),
                  nb.math('MULTIPLY', nb.smooth(fv, 0.3, 0.34), nb.smooth(fv, 0.8, 0.76)))
    shutter = ramp_const(nb, nb.sep_rgb(vor.outputs['Color'])[1], ['#4E6B4A', '#6B4A33', '#3F5A6E', '#7A5A3A'])
    col = nb.mix(win, col, nb.mix(nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', fu, 0.51)), 0.02, 0.05), C.lin('#2A2522'), shutter))
    col = weather(nb, col, streak=0.35, grime=0.4, wear=0.0, foot=0.4, ao_dist=0.6)
    K.principled(nb, col, 0.9, None, 0.2)
    return m
