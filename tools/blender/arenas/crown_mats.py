"""The Crown Amphitheatre's stone and ground materials (Cycles; baked into the atlases, never shipped as shaders).

Stone: a CC0 Poly Haven photo texture on our metre UVs, graded to travertine, marble or sandstone, then weathered:
patches of a second, older stone, block-to-block tint, rain streaks under every ledge, grime in the crevices and a
pale wear on the edges (both from Cycles' AO node, so the bake carries them), a darker foot and a sand splash band.
"""
from __future__ import annotations

import bpy

from lib import common as C
from lib.nodes import NB, new_mat
import kit as K


# ----------------------------------------------------------------------------- small node helpers
def uv_vec(nb: NB, tile: float, rot: float = 0.0, layer: str = 'UVMap'):
    u = nb.new('ShaderNodeUVMap', uv_map=layer)
    mp = nb.new('ShaderNodeMapping')
    nb.link(u.outputs[0], mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1)
    mp.inputs['Rotation'].default_value = (0, 0, rot)
    return mp.outputs[0]


def obj_co(nb: NB):
    return nb.new('ShaderNodeTexCoord').outputs['Object']


def stretched(nb: NB, vec, sx: float, sy: float, sz: float):
    mp = nb.new('ShaderNodeMapping')
    nb.link(vec, mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (sx, sy, sz)
    return mp.outputs[0]


def attr(nb: NB, name: str):
    return nb.attribute(name).outputs['Fac']


def ao(nb: NB, dist: float, inside: bool = False, samples: int = 8):
    n = nb.new('ShaderNodeAmbientOcclusion')
    n.samples = samples
    n.inside = inside
    n.inputs['Distance'].default_value = dist
    return n.outputs['AO']


def mul(nb: NB, col, k):
    """col × k (k a float socket or number), as a colour."""
    if not isinstance(k, bpy.types.NodeSocket):
        return nb.mix(1.0, col, (k, k, k, 1.0), blend='MULTIPLY')
    return nb.mix(1.0, col, nb.comb(k, k, k), blend='MULTIPLY')


def ramp_const(nb: NB, fac, hexes: list[str]):
    """Pick one of `hexes` by fac in 0..1 (constant steps)."""
    n = nb.new('ShaderNodeValToRGB')
    cr = n.color_ramp
    cr.interpolation = 'CONSTANT'
    cr.elements[0].position = 0.0
    cr.elements[0].color = C.lin(hexes[0])
    cr.elements[1].position = 1.0 / len(hexes)
    cr.elements[1].color = C.lin(hexes[1 % len(hexes)])
    for i, h in enumerate(hexes[2:], start=2):
        e = cr.elements.new(i / len(hexes))
        e.color = C.lin(h)
    nb.put(n.inputs['Fac'], fac)
    return n.outputs['Color']


# ----------------------------------------------------------------------------- weathering
def weather(nb: NB, col, *, streak: float = 0.35, grime: float = 0.45, wear: float = 0.25, foot: float = 0.25,
            splash: float = 0.0, moss: float = 0.0, ao_dist: float = 0.45):
    co = obj_co(nb)
    z = nb.sep(co)[2]
    # rain streaks: noise stretched tall, strongest under the ledges (AO from above stands in for "under a ledge")
    st = nb.smooth(nb.noise(stretched(nb, co, 2.2, 2.2, 0.09), 3.0, 3.0, 0.6), 0.52, 0.78)
    st = nb.math('MULTIPLY', st, nb.smooth(nb.noise(co, 0.25, 2.0, 0.5), 0.35, 0.7))
    col = nb.mix(nb.math('MULTIPLY', st, streak), col, mul(nb, nb.mix(0.35, col, C.lin('#5B5348')), 0.55))
    # grime in the crevices and inside corners, a pale wear on the edges
    occ = ao(nb, ao_dist)
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(occ, 0.95, 0.45), grime), col, mul(nb, nb.mix(0.5, col, C.lin('#4E463C')), 0.7))
    edge = nb.smooth(ao(nb, 0.08, inside=True), 0.75, 1.0)
    col = nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, edge), wear), col, nb.mix(0.5, col, C.lin('#F2EBDD')))
    if foot:
        f = nb.math('MULTIPLY', nb.smooth(z, 1.6, 0.0), nb.smooth(nb.noise(co, 1.4, 3.0, 0.6), 0.25, 0.65))
        col = nb.mix(nb.math('MULTIPLY', f, foot), col, mul(nb, col, 0.6))
    if moss:
        m = nb.math('MULTIPLY', nb.smooth(z, 2.5, 0.2), nb.smooth(nb.noise(co, 0.9, 3.0, 0.6), 0.5, 0.72))
        col = nb.mix(nb.math('MULTIPLY', m, moss), col, C.lin('#6B7346'))
    if splash:
        s = nb.math('MULTIPLY', nb.smooth(z, 0.9, 0.05), nb.smooth(nb.noise(co, 3.0, 3.0, 0.65), 0.3, 0.6))
        col = nb.mix(nb.math('MULTIPLY', s, splash), col, C.lin('#B99A6E'))
    return col


def photo(nb: NB, aid: str, tile: float, rot: float = 0.0, normal: bool = True):
    vec = uv_vec(nb, tile, rot)
    d, n = K.tex_nodes(nb, aid, vec, 'FLAT', normal=normal)
    return d.outputs['Color'], (K.normal_map(nb, n, 0.7) if n is not None else None)


# ----------------------------------------------------------------------------- stone
STONES = {  # name: (texture, tile m, tint, tint mix, second texture, sat, val)
    'travertine': ('sandstone_blocks_08', 3.2, '#D2C2A0', 0.25, 'large_sandstone_blocks_01', 0.8, 1.0),
    'travertine_dark': ('sandstone_blocks_08', 3.2, '#B9AA8C', 0.28, 'large_sandstone_blocks_01', 0.7, 0.92),
    'sandstone': ('sandstone_blocks_04', 2.4, '#CDAE82', 0.25, 'large_sandstone_blocks_01', 0.85, 1.05),
    'ashlar': ('white_sandstone_blocks_02', 2.0, '#D6C7A8', 0.2, 'large_sandstone_blocks_01', 0.7, 1.05),
    'marble': ('marble_01', 2.2, '#E6DCC6', 0.25, None, 0.45, 1.04),
    'paving': ('stone_pavers', 2.6, '#C9B897', 0.25, None, 0.7, 1.05),
    'plaza': ('stone_floor', 3.2, '#D2B386', 0.3, None, 0.9, 1.08),
}


def stone(name: str, kind: str, *, crowd=None, streak=0.35, grime=0.45, wear=0.25, foot=0.25, splash=0.0, moss=0.0,
          val: float = 1.0, warm: float = 0.0) -> bpy.types.Material:
    aid, tile, tint, tmix, second, sat, v0 = STONES[kind]
    m, nb = new_mat(name)
    d, nrm = photo(nb, aid, tile)
    col = K.grade(nb, d, 0.5 + warm * 0.01, sat, v0 * val, C.srgb(tint), tmix, 0.05)
    co = obj_co(nb)
    if second:
        d2, _ = photo(nb, second, tile * 1.15, 0.0, normal=False)
        c2 = K.grade(nb, d2, 0.5, sat * 0.9, v0 * val * 0.95, C.srgb(tint), tmix + 0.1, 0.0)
        patch = nb.smooth(nb.noise(co, 0.11, 3.0, 0.55), 0.48, 0.62)
        col = nb.mix(patch, col, c2)
    big = nb.noise(co, 0.045, 2.0, 0.5)
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(big, 0.35, 0.75), 0.35), col, nb.mix(0.5, col, C.lin('#E8D9B8')))
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(big, 0.6, 0.3), 0.45), col, nb.mix(0.55, col, C.lin('#958B7C')))
    vor = nb.new('ShaderNodeTexVoronoi')                                   # block-to-block tone (one random per cell)
    nb.link(stretched(nb, co, 0.9, 0.9, 1.6), vor.inputs['Vector'])
    vor.inputs['Scale'].default_value = 1.2
    blk = nb.sep_rgb(vor.outputs['Color'])[0]
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(blk, 0.3, 0.9), 0.2), col, mul(nb, col, 0.8))
    stain = nb.math('MULTIPLY', nb.smooth(nb.noise(co, 0.35, 3.0, 0.6), 0.6, 0.8), 0.45)      # warm iron stains
    col = nb.mix(stain, col, mul(nb, nb.mix(0.5, col, C.lin('#B98A52')), 0.9))
    col = weather(nb, col, streak=streak, grime=grime, wear=wear, foot=foot, splash=splash, moss=moss)
    if crowd is not None:
        col = crowd(nb, col)
    K.principled(nb, col, 0.85, nrm, 0.2)
    return m


def marble_obj(name: str, tint: str = '#EEE8DC', tile: float = 0.9) -> bpy.types.Material:
    """Marble for imported shapes with no UVs of ours (statues): box-projected on object metres, veined, weathered."""
    m, nb = new_mat(name)
    vec = K.coords(nb, 'Object', tile)
    d, _ = K.tex_nodes(nb, 'marble_01', vec, 'BOX', normal=False)
    col = K.grade(nb, d.outputs['Color'], 0.5, 0.35, 1.02, C.srgb(tint), 0.3, 0.0)
    co = obj_co(nb)
    vein = nb.new('ShaderNodeTexWave')
    nb.link(stretched(nb, co, 1.0, 1.0, 1.0), vein.inputs['Vector'])
    vein.inputs['Scale'].default_value = 1.6
    vein.inputs['Distortion'].default_value = 9.0
    vein.inputs['Detail'].default_value = 4.0
    v = nb.smooth(vein.outputs['Fac'], 0.9, 1.0)
    col = nb.mix(nb.math('MULTIPLY', v, 0.35), col, C.lin('#8C8A86'))
    col = weather(nb, col, streak=0.5, grime=0.6, wear=0.35, foot=0.0, ao_dist=0.25)
    K.principled(nb, col, 0.5, K.bump_from(nb, K.lum(nb, d.outputs['Color']), 0.15, 0.01), 0.35)
    return m


def bronze(name: str) -> bpy.types.Material:
    """Old bronze: warm metal on the raised parts, verdigris in the hollows and in streaks, dark grime deepest in."""
    m, nb = new_mat(name)
    co = obj_co(nb)
    n = nb.noise(co, 3.0, 4.0, 0.6)
    base = nb.mix(n, C.lin('#7A5530'), C.lin('#A27A45'))
    occ = ao(nb, 0.3)
    green = nb.mix(nb.noise(co, 6.0, 3.0, 0.5), C.lin('#3F8A76'), C.lin('#74B7A0'))
    hollow = nb.smooth(occ, 0.95, 0.55)
    st = nb.smooth(nb.noise(stretched(nb, co, 4.0, 4.0, 0.3), 2.0, 3.0, 0.6), 0.5, 0.75)
    col = nb.mix(nb.math('MINIMUM', 1.0, nb.math('ADD', nb.math('MULTIPLY', hollow, 0.85), nb.math('MULTIPLY', st, 0.4))), base, green)
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(occ, 0.7, 0.3), 0.6), col, C.lin('#2A221A'))
    edge = nb.math('SUBTRACT', 1.0, nb.smooth(ao(nb, 0.05, inside=True), 0.8, 1.0))
    col = nb.mix(nb.math('MULTIPLY', edge, 0.5), col, C.lin('#D6A862'))
    K.principled(nb, col, 0.5, K.bump_from(nb, n, 0.2, 0.01), 0.5)          # not metallic: the bake keeps diffuse only
    return m


def flat(name: str, hexcol: str, rough: float = 0.8, weathered: float = 0.0) -> bpy.types.Material:
    m, nb = new_mat(name)
    col = C.lin(hexcol)
    if weathered:
        co = obj_co(nb)
        col = nb.mix(nb.math('MULTIPLY', nb.noise(co, 2.0, 3.0, 0.6), 0.4 * weathered), col, mul(nb, col, 0.55))
        col = nb.mix(nb.math('MULTIPLY', nb.smooth(ao(nb, 0.3), 0.95, 0.5), weathered), col, mul(nb, col, 0.5))
    K.principled(nb, col, rough, None, 0.2)
    return m


def void(name: str = 'void') -> bpy.types.Material:
    """The dark inside of tunnels and doorways (a little warm, never pure black)."""
    return flat(name, '#1E1A17', 0.95)


def emblem_bronze(name: str, emblem_img) -> bpy.types.Material:
    """A bronze boss with the Guild emblem standing proud (UVMap 0..1 across the boss): polished on the raised
    emblem, verdigris in the field."""
    m, nb = new_mat(name)
    uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
    t = nb.new('ShaderNodeTexImage', image=emblem_img, interpolation='Linear')
    t.extension = 'CLIP'
    u, v, _ = nb.sep(uvn.outputs[0])
    nb.link(nb.comb(nb.math('MULTIPLY_ADD', u, 1.25, -0.125), nb.math('MULTIPLY_ADD', v, 1.25, -0.125), 0.0), t.inputs['Vector'])
    e = nb.sep_rgb(t.outputs['Color'])[0]
    co = obj_co(nb)
    field = nb.mix(nb.noise(co, 8.0, 3.0, 0.6), C.lin('#3F7F6C'), C.lin('#6A9E86'))
    raised = nb.mix(nb.noise(co, 5.0, 3.0, 0.5), C.lin('#B48A4E'), C.lin('#D9AE68'))
    col = nb.mix(e, field, raised)
    col = weather(nb, col, streak=0.3, grime=0.4, wear=0.0, foot=0.0, ao_dist=0.15)
    K.principled(nb, col, 0.5, K.bump_from(nb, e, 0.6, 0.02), 0.4)
    return m


def inset(name: str) -> bpy.types.Material:
    """Coloured marble for the inset panels: the CC0 marble graded to a deep red, its own veins showing through."""
    m, nb = new_mat(name)
    d, nrm = photo(nb, 'marble_01', 1.3)
    col = K.grade(nb, d, 0.5, 0.8, 0.4, C.lin_rgb('#7A2A1E'), 0.78, 0.15)
    col = weather(nb, col, streak=0.3, grime=0.35, wear=0.2, foot=0.0, ao_dist=0.2)
    K.principled(nb, col, 0.35, nrm, 0.4)
    return m
