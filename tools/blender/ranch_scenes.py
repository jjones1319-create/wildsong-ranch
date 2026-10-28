"""Wildsong Ranch: pre-rendered scenery clips (welcome, sad, abandoned, note).

Builds an original low-poly ranch set procedurally (no external assets), lights it
per scene with a soft toon shader, and renders PNG frames with EEVEE.

Usage, from the repo root (Git Bash):
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python tools/blender/ranch_scenes.py -- --scene welcome [--preview] [--frames 1,84] [--samples 32]

  --scene    welcome | sad | abandoned | note | all
  --preview  half resolution, 8 evenly spaced frames, fewer samples -> out/<scene>-preview/
  --frames   comma list of frames to render (full resolution unless --preview)
  --samples  override the EEVEE render samples
  --save-blend  also save the built scene to out/<scene>.blend for inspection

Frames go to tools/blender/out/<scene>/f_0001.png ...; tools/blender/encode.ts turns
them into public/baked/scenes/<scene>.mp4 + .webp.

Pinned to the Blender 5.2 Python API (EEVEE engine id 'BLENDER_EEVEE').
Everything is deterministic: fixed seeds, Perlin noise from mathutils, and all
motion comes from drivers on `frame` or the Geometry Nodes Scene Time.
"""
import argparse
import math
import os
import random
import sys
import time

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Matrix, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_ROOT = os.path.join(HERE, 'out')
FPS = 24
RES = (720, 960)
TEMPLATE_Z = -500.0  # instance templates live far below the ground


def log(*a):
    print('[ranch]', *a, flush=True)


# --------------------------------------------------------------------------- helpers
def lin(h, k=1.0):
    """sRGB hex -> linear RGBA tuple, optionally scaled."""
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        c = c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        out.append(c * k)
    return (out[0], out[1], out[2], 1.0)


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def nz(x, y, z=0.0):
    return noise.noise(Vector((x, y, z)))


# Mood envelope for the current scene (driver expression of `frame`), set in main().
ENV = '0'


# --------------------------------------------------------------------------- node builder
class NB:
    """Tiny helper for building node trees from Python."""

    def __init__(self, tree):
        self.t = tree

    def new(self, kind, **props):
        n = self.t.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.t.links.new(a, b)

    def put(self, sock, val):
        if isinstance(val, bpy.types.NodeSocket):
            self.t.links.new(val, sock)
        elif val is not None:
            if isinstance(val, tuple):
                n = len(sock.default_value)
                val = tuple(val[:n]) + (1.0,) * max(0, n - len(val))
            sock.default_value = val

    @staticmethod
    def sin_(n, ident):
        return next(s for s in n.inputs if s.identifier == ident)

    @staticmethod
    def sout(n, ident):
        return next(s for s in n.outputs if s.identifier == ident)

    @staticmethod
    def by_name(socks, name, typ=None):
        for s in socks:
            if s.name == name and s.enabled and (typ is None or s.type == typ):
                return s
        raise KeyError(name)

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if c is not None:
            self.put(n.inputs[2], c)
        return n.outputs[0]

    def vmath(self, op, a, b=None, c=None, scale=None):
        n = self.new('ShaderNodeVectorMath', operation=op)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if c is not None:
            self.put(n.inputs[2], c)
        if scale is not None:
            self.put(n.inputs[3], scale)
        if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE'):
            return n.outputs[1]
        return n.outputs[0]

    def mix(self, fac, a, b, dtype='RGBA', blend='MIX'):
        n = self.new('ShaderNodeMix', data_type=dtype)
        if dtype == 'RGBA':
            n.blend_type = blend
        key = {'FLOAT': 'Float', 'VECTOR': 'Vector', 'RGBA': 'Color'}[dtype]
        self.put(self.sin_(n, 'Factor_Float'), fac)
        self.put(self.sin_(n, 'A_' + key), a)
        self.put(self.sin_(n, 'B_' + key), b)
        return self.sout(n, 'Result_' + key)

    def sep(self, v):
        n = self.new('ShaderNodeSeparateXYZ')
        self.put(n.inputs[0], v)
        return n.outputs

    def comb(self, x, y, z):
        n = self.new('ShaderNodeCombineXYZ')
        self.put(n.inputs[0], x)
        self.put(n.inputs[1], y)
        self.put(n.inputs[2], z)
        return n.outputs[0]

    def rgb(self, c):
        n = self.new('ShaderNodeRGB')
        n.outputs[0].default_value = c
        return n.outputs[0]

    def val(self, v):
        n = self.new('ShaderNodeValue')
        n.outputs[0].default_value = v
        return n.outputs[0]

    def smooth(self, x, a, b):
        """smoothstep(a, b, x) in 0..1 (works for a > b too)."""
        n = self.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        self.put(n.inputs['Value'], x)
        n.inputs['From Min'].default_value = a
        n.inputs['From Max'].default_value = b
        n.inputs['To Min'].default_value = 0.0
        n.inputs['To Max'].default_value = 1.0
        return n.outputs['Result']

    def noise(self, vec, scale, detail=2.0, rough=0.5):
        n = self.new('ShaderNodeTexNoise')
        self.put(n.inputs['Vector'], vec)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        return n.outputs['Fac']

    def param(self, name, a, b=None):
        """A scene parameter node; animated a->b with the mood envelope if b is given."""
        if isinstance(a, tuple):
            n = self.new('ShaderNodeRGB')
            n.outputs[0].default_value = a
            if b is not None:
                for i in range(3):
                    fc = n.outputs[0].driver_add('default_value', i)
                    fc.driver.type = 'SCRIPTED'
                    fc.driver.expression = f'{a[i]:.6f}+({b[i] - a[i]:.6f})*{ENV}'
        else:
            n = self.new('ShaderNodeValue')
            n.outputs[0].default_value = a
            if b is not None:
                fc = n.outputs[0].driver_add('default_value')
                fc.driver.type = 'SCRIPTED'
                fc.driver.expression = f'{a:.6f}+({b - a:.6f})*{ENV}'
        n.name = name
        n.label = name
        return n.outputs[0]


def drive(obj, path, expr, index=-1):
    fc = obj.driver_add(path, index) if index >= 0 else obj.driver_add(path)
    fc.driver.type = 'SCRIPTED'
    fc.driver.expression = expr
    return fc


def iface(ng, name, io, kind, default=None):
    item = ng.interface.new_socket(name=name, in_out=io, socket_type=kind)
    if default is not None:
        item.default_value = default
    return item


# --------------------------------------------------------------------------- scene moods
def P2(P, key):
    return P.get(key + '2')


MOODS = {
    'welcome': dict(
        sunCol=lin('#ffd08e'), sunK=1.12, sun_dir=(-0.62, 0.70, 0.27),
        ambSky=lin('#a9bdd6', 0.66), ambGround=lin('#9a8256', 0.42),
        rimK=1.25, sheen=0.0, sat=1.08, wet=0.0,
        fogCol=lin('#f6d4a0'), fogDen=0.0065, hfogDen=0.0, hfogTop=1.0,
        sky_h=lin('#ffdca6'), sky_m=lin('#f6c69b'), sky_t=lin('#8db4d6'),
        glowCol=lin('#ffd38c'), glowK=0.65, glowPow=5.0,
        cloudLit=lin('#fff1da'), cloudShade=lin('#e2b2a6'),
        grassA='#6e9e45', grassB='#97c25e', dirtA='#c79b65', dirtB='#a98251',
    ),
    'sad': dict(
        sunCol=lin('#f7e2bc'), sunCol2=lin('#b8c1cb'), sunK=0.95, sunK2=0.0,
        sun_dir=(-0.55, -0.55, 0.62),
        ambSky=lin('#a7b5c6', 0.62), ambSky2=lin('#9ea9b6', 0.74),
        ambGround=lin('#7a735c', 0.40), ambGround2=lin('#5b6166', 0.42),
        rimK=0.55, rimK2=0.0, sheen=0.0, sheen2=0.12, sat=0.92, sat2=0.42, wet=0.0, wet2=0.15,
        fogCol=lin('#dfd9cb'), fogCol2=lin('#9aa2ab'), fogDen=0.007, fogDen2=0.011,
        hfogDen=0.0, hfogTop=1.0,
        sky_h=lin('#f1e4ca'), sky_h2=lin('#aeb5bd'), sky_m=lin('#cad6e0'), sky_m2=lin('#969ea8'),
        sky_t=lin('#9bb8d0'), sky_t2=lin('#747d89'),
        glowCol=lin('#fff0c8'), glowK=0.3, glowK2=0.0, glowPow=6.0,
        cloudLit=lin('#f8f4ee'), cloudLit2=lin('#9aa1a9'), cloudShade=lin('#bcc2cb'), cloudShade2=lin('#646c75'),
        grassA='#6c9846', grassB='#8fb75b', dirtA='#bf9665', dirtB='#a27c50',
    ),
    'abandoned': dict(
        sunCol=lin('#b4c3d6'), sunK=0.28, sun_dir=(-0.4, 0.3, 0.85),
        ambSky=lin('#8a9cb3', 0.66), ambGround=lin('#46525a', 0.50),
        rimK=0.0, sheen=0.38, sat=0.66, wet=1.0,
        fogCol=lin('#64727f'), fogDen=0.016, hfogDen=0.14, hfogTop=0.9,
        sky_h=lin('#6c7a88'), sky_m=lin('#56626f'), sky_t=lin('#3b4552'),
        glowCol=lin('#000000'), glowK=0.0, glowPow=6.0,
        cloudLit=lin('#6c7782'), cloudShade=lin('#444e58'),
        grassA='#55743c', grassB='#6f8a45', dirtA='#8a6a48', dirtB='#6f5236',
    ),
    'note': dict(
        sunCol=lin('#ffd0ae'), sunK=0.62, sun_dir=(0.55, -0.82, 0.14),
        ambSky=lin('#7f7cad', 0.46), ambGround=lin('#4c3f4a', 0.38),
        rimK=0.9, sheen=0.32, sat=0.92, wet=0.7,
        fogCol=lin('#8a7fa3'), fogDen=0.018, hfogDen=0.06, hfogTop=0.8,
        sky_h=lin('#e9a58f'), sky_m=lin('#9a7fa6'), sky_t=lin('#2f3a68'),
        glowCol=lin('#ffb08a'), glowK=0.0, glowPow=6.0,
        cloudLit=lin('#f2a894'), cloudShade=lin('#5d5a7c'),
        grassA='#577f43', grassB='#6f9650', dirtA='#8f6c4f', dirtB='#76563c',
    ),
}


# --------------------------------------------------------------------------- shared shaders
TOON = None


def build_toon_group(P):
    """Soft toon: hemispheric ambient + stepped sun (with shadows) + rim + saturation + fog."""
    ng = bpy.data.node_groups.new('WS_Toon', 'ShaderNodeTree')
    iface(ng, 'Color', 'INPUT', 'NodeSocketColor', (0.8, 0.8, 0.8, 1.0))
    iface(ng, 'Rim', 'INPUT', 'NodeSocketFloat', 1.0)
    iface(ng, 'AO', 'INPUT', 'NodeSocketFloat', 1.0)
    iface(ng, 'Fog', 'INPUT', 'NodeSocketFloat', 1.0)
    iface(ng, 'Emit', 'INPUT', 'NodeSocketFloat', 0.0)
    iface(ng, 'Shader', 'OUTPUT', 'NodeSocketShader')
    nb = NB(ng)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')

    sunCol = nb.param('P_sunCol', P['sunCol'], P2(P, 'sunCol'))
    sunK = nb.param('P_sunK', P['sunK'], P2(P, 'sunK'))
    ambSky = nb.param('P_ambSky', P['ambSky'], P2(P, 'ambSky'))
    ambGround = nb.param('P_ambGround', P['ambGround'], P2(P, 'ambGround'))
    rimK = nb.param('P_rimK', P['rimK'], P2(P, 'rimK'))
    sheen = nb.param('P_sheen', P['sheen'], P2(P, 'sheen'))
    sat = nb.param('P_sat', P['sat'], P2(P, 'sat'))
    wet = nb.param('P_wet', P['wet'], P2(P, 'wet'))
    fogCol = nb.param('P_fogCol', P['fogCol'], P2(P, 'fogCol'))
    fogDen = nb.param('P_fogDen', P['fogDen'], P2(P, 'fogDen'))
    hfogDen = nb.param('P_hfogDen', P['hfogDen'])
    hfogTop = nb.param('P_hfogTop', P['hfogTop'])

    # sun term (Shader to RGB keeps the shadows), stepped by a soft ramp
    diff = nb.new('ShaderNodeBsdfDiffuse')
    diff.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = nb.new('ShaderNodeShaderToRGB')
    nb.link(diff.outputs[0], s2r.inputs[0])
    bw = nb.new('ShaderNodeRGBToBW')
    nb.link(s2r.outputs['Color'], bw.inputs[0])
    ramp = nb.new('ShaderNodeValToRGB')
    nb.link(bw.outputs[0], ramp.inputs['Fac'])
    els = ramp.color_ramp.elements
    els[0].position = 0.035
    els[0].color = (0, 0, 0, 1)
    els[1].position = 0.17
    els[1].color = (0.8, 0.8, 0.8, 1)
    e = els.new(0.55)
    e.color = (1, 1, 1, 1)
    lit = nb.sep(ramp.outputs['Color'])[0]

    geo = nb.new('ShaderNodeNewGeometry')
    nzv = nb.sep(geo.outputs['Normal'])[2]
    hemi = nb.math('MULTIPLY_ADD', nzv, 0.5, 0.5)
    amb = nb.mix(hemi, ambGround, ambSky)
    ao = nb.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.7
    aof = nb.math('MULTIPLY_ADD', nb.math('SUBTRACT', ao.outputs['AO'], 1.0), gi.outputs['AO'], 1.0)
    amb = nb.vmath('SCALE', amb, scale=aof)
    sunTerm = nb.vmath('SCALE', sunCol, scale=nb.math('MULTIPLY', lit, sunK))
    light = nb.vmath('ADD', amb, sunTerm)

    base = nb.vmath('SCALE', gi.outputs['Color'], scale=nb.math('MULTIPLY_ADD', wet, -0.30, 1.0))
    col = nb.vmath('MULTIPLY', base, light)

    lw = nb.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.45
    rimf = nb.math('MULTIPLY', nb.math('POWER', lw.outputs['Facing'], 2.6), gi.outputs['Rim'])
    rimA = nb.vmath('SCALE', sunCol, scale=nb.math('MULTIPLY', rimf, nb.math('MULTIPLY', lit, nb.math('MULTIPLY', rimK, sunK))))
    rimB = nb.vmath('SCALE', ambSky, scale=nb.math('MULTIPLY', rimf, sheen))
    col = nb.vmath('ADD', col, rimA)
    col = nb.vmath('ADD', col, rimB)
    col = nb.vmath('ADD', col, nb.vmath('SCALE', gi.outputs['Color'], scale=gi.outputs['Emit']))

    hs = nb.new('ShaderNodeHueSaturation')
    nb.put(hs.inputs['Color'], col)
    nb.put(hs.inputs['Saturation'], sat)
    col = hs.outputs['Color']

    cam = nb.new('ShaderNodeCameraData')
    dist = cam.outputs['View Distance']
    fd = nb.math('SUBTRACT', 1.0, nb.math('EXPONENT', nb.math('MULTIPLY', nb.math('MULTIPLY', dist, fogDen), -1.0)))
    pz = nb.sep(geo.outputs['Position'])[2]
    hb = nb.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nb.put(hb.inputs['Value'], pz)
    nb.put(hb.inputs['From Min'], hfogTop)
    hb.inputs['From Max'].default_value = -0.25
    hb.inputs['To Min'].default_value = 0.0
    hb.inputs['To Max'].default_value = 1.0
    dfar = nb.math('MAXIMUM', nb.math('SUBTRACT', dist, 4.5), 0.0)
    hfd = nb.math('MULTIPLY', hb.outputs['Result'],
                  nb.math('SUBTRACT', 1.0, nb.math('EXPONENT', nb.math('MULTIPLY', nb.math('MULTIPLY', dfar, hfogDen), -1.0))))
    keep = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, fd), nb.math('SUBTRACT', 1.0, hfd))
    f = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, keep), gi.outputs['Fog'], clamp=True)
    final = nb.mix(f, col, fogCol)
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], final)
    nb.link(em.outputs[0], go.inputs['Shader'])
    return ng


def new_mat(name):
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, NB(m.node_tree)


def toon(name, color, rim=1.0, ao=1.0, fog=1.0, emit=0.0):
    m, nb = new_mat(name)
    g = nb.new('ShaderNodeGroup')
    g.node_tree = TOON
    if callable(color):
        c = color(nb)
    else:
        c = nb.rgb(lin(color) if isinstance(color, str) else color)
    nb.put(g.inputs['Color'], c)
    g.inputs['Rim'].default_value = rim
    g.inputs['AO'].default_value = ao
    g.inputs['Fog'].default_value = fog
    g.inputs['Emit'].default_value = emit
    out = nb.new('ShaderNodeOutputMaterial')
    nb.link(g.outputs['Shader'], out.inputs['Surface'])
    return m


def island_tint(ha, hb, grain=0.0, grain_axis=(30.0, 30.0, 1.5), noise_scale=2.5):
    """Colour varying per mesh island (each plank/post) plus optional wood grain."""
    def f(nb):
        geo = nb.new('ShaderNodeNewGeometry')
        tc = nb.new('ShaderNodeTexCoord')
        n = nb.noise(tc.outputs['Object'], noise_scale, 2.0)
        fac = nb.math('MULTIPLY_ADD', geo.outputs['Random Per Island'], 0.65, nb.math('MULTIPLY', n, 0.35))
        c = nb.mix(fac, lin(ha), lin(hb))
        if grain > 0:
            g = nb.noise(nb.vmath('MULTIPLY', tc.outputs['Object'], grain_axis), 1.0, 6.0, 0.62)
            g2 = nb.noise(nb.vmath('MULTIPLY', tc.outputs['Object'], tuple(a * 3.1 for a in grain_axis)), 1.0, 3.0, 0.5)
            g = nb.math('MULTIPLY_ADD', g2, 0.45, nb.math('MULTIPLY', g, 0.55))
            gm = nb.math('MULTIPLY_ADD', nb.smooth(g, 0.38, 0.68), -grain, 1.0)
            c = nb.vmath('SCALE', c, scale=gm)
        return c
    return f


def attr_gradient(attr, ha, hb, rnd_k=0.0, hc=None):
    """Colour from a per-vertex 0..1 attribute (base->tip), with per-instance variation."""
    def f(nb):
        a = nb.new('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name=attr)
        c = nb.mix(a.outputs['Fac'], lin(ha), lin(hb))
        if rnd_k > 0:
            oi = nb.new('ShaderNodeObjectInfo')
            alt = lin(hc) if hc else lin(hb)
            c = nb.mix(nb.math('MULTIPLY', oi.outputs['Random'], rnd_k), c, alt)
        return c
    return f


def palette_by_random(hexes):
    def f(nb):
        oi = nb.new('ShaderNodeObjectInfo')
        r = nb.new('ShaderNodeValToRGB')
        nb.link(oi.outputs['Random'], r.inputs['Fac'])
        r.color_ramp.interpolation = 'CONSTANT'
        els = r.color_ramp.elements
        els[0].position = 0.0
        els[0].color = lin(hexes[0])
        els[1].position = 1.0 / len(hexes)
        els[1].color = lin(hexes[1])
        for i, h in enumerate(hexes[2:], start=2):
            e = els.new(i / len(hexes))
            e.color = lin(h)
        return r.outputs['Color']
    return f


def sky_material(P, sun_dir):
    m, nb = new_mat('M_sky')
    geo = nb.new('ShaderNodeNewGeometry')
    d = nb.vmath('NORMALIZE', nb.vmath('SCALE', geo.outputs['Incoming'], scale=-1.0))
    ez = nb.sep(d)[2]
    h = nb.param('S_h', P['sky_h'], P2(P, 'sky_h'))
    mcol = nb.param('S_m', P['sky_m'], P2(P, 'sky_m'))
    t = nb.param('S_t', P['sky_t'], P2(P, 'sky_t'))
    c = nb.mix(nb.smooth(ez, -0.01, 0.20), h, mcol)
    c = nb.mix(nb.smooth(ez, 0.08, 0.40), c, t)
    sd = Vector(sun_dir).normalized()
    dot = nb.math('MAXIMUM', nb.vmath('DOT_PRODUCT', d, tuple(sd)), 0.0)
    glowK = nb.param('S_glowK', P['glowK'], P2(P, 'glowK'))
    g = nb.math('MULTIPLY', nb.math('POWER', dot, P['glowPow']), glowK)
    c = nb.vmath('ADD', c, nb.vmath('SCALE', nb.rgb(P['glowCol']), scale=g))
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], c)
    out = nb.new('ShaderNodeOutputMaterial')
    nb.link(em.outputs[0], out.inputs['Surface'])
    return m


def cloud_material(P, sun_dir, cam_loc):
    m, nb = new_mat('M_cloud')
    geo = nb.new('ShaderNodeNewGeometry')
    n = geo.outputs['Normal']
    sd = tuple(Vector(sun_dir).normalized())
    k = nb.math('ADD', nb.math('MULTIPLY_ADD', nb.vmath('DOT_PRODUCT', n, sd), 0.45, 0.35),
                nb.math('MULTIPLY', nb.sep(n)[2], 0.35))
    k = nb.smooth(k, 0.25, 0.85)
    litc = nb.param('C_lit', P['cloudLit'], P2(P, 'cloudLit'))
    shc = nb.param('C_shade', P['cloudShade'], P2(P, 'cloudShade'))
    c = nb.mix(k, shc, litc)
    # fade toward the horizon colour low in the sky
    rel = nb.vmath('NORMALIZE', nb.vmath('SUBTRACT', geo.outputs['Position'], tuple(cam_loc)))
    hz = nb.smooth(nb.sep(rel)[2], 0.02, 0.30)
    h = nb.param('C_h', P['sky_h'], P2(P, 'sky_h'))
    c = nb.mix(nb.math('MULTIPLY_ADD', hz, -0.55, 0.55), c, h)
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], c)
    out = nb.new('ShaderNodeOutputMaterial')
    nb.link(em.outputs[0], out.inputs['Surface'])
    return m


def path_shader_mask(nb, x, y):
    """Mirror of path_cx/path_hw in the shader. Returns 0..1 dirt mask."""
    s = nb.math('SINE', nb.math('MULTIPLY_ADD', y, 0.45, 0.3))
    ypos = nb.math('MAXIMUM', y, 0.0)
    cx = nb.math('SUBTRACT', nb.math('MULTIPLY', s, 0.10), nb.math('MULTIPLY', nb.math('MULTIPLY', ypos, ypos), PATH_BEND))
    hw = nb.math('MULTIPLY_ADD', nb.math('MAXIMUM', nb.math('MULTIPLY', y, -1.0), 0.0), 0.035, 0.62)
    return cx, hw


PATH_BEND = 0.086
PATH_END_Y = 6.4


def path_cx(y):
    return 0.10 * math.sin(0.45 * y + 0.3) - PATH_BEND * max(y, 0.0) ** 2


def path_hw(y):
    return 0.62 + 0.035 * max(-y, 0.0)


def path_dist(x, y):
    """Signed distance outside the dirt path (negative = on the path)."""
    if y > PATH_END_Y + 0.6:
        return 9.0
    return abs(x - path_cx(y)) - path_hw(y)


def ground_material(P):
    def f(nb):
        geo = nb.new('ShaderNodeNewGeometry')
        pos = geo.outputs['Position']
        x, y, _z = nb.sep(pos)
        n1 = nb.noise(pos, 0.16, 2.0)
        n2 = nb.noise(pos, 1.3, 3.0)
        grass = nb.mix(nb.smooth(n1, 0.38, 0.66), lin(P['grassA']), lin(P['grassB']))
        grass = nb.vmath('SCALE', grass, scale=nb.math('MULTIPLY_ADD', n2, 0.22, 0.89))
        cx, hw = path_shader_mask(nb, x, y)
        dist = nb.math('ABSOLUTE', nb.math('SUBTRACT', x, cx))
        dist = nb.math('ADD', dist, nb.math('MULTIPLY', nb.math('SUBTRACT', nb.noise(pos, 2.2, 2.0), 0.5), 0.16))
        mr = nb.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        nb.put(mr.inputs['Value'], dist)
        nb.put(mr.inputs['From Min'], nb.math('ADD', hw, 0.06))
        nb.put(mr.inputs['From Max'], nb.math('SUBTRACT', hw, 0.06))
        mask = nb.math('MULTIPLY', mr.outputs['Result'], nb.smooth(y, PATH_END_Y + 0.6, PATH_END_Y - 0.4))
        dirt = nb.mix(nb.smooth(n2, 0.3, 0.7), lin(P['dirtA']), lin(P['dirtB']))
        c = nb.mix(mask, grass, dirt)
        edge = nb.math('MULTIPLY', nb.math('MULTIPLY', mask, nb.math('SUBTRACT', 1.0, mask)), 4.0)
        c = nb.vmath('SCALE', c, scale=nb.math('MULTIPLY_ADD', edge, -0.16, 1.0))
        return c
    return f


# --------------------------------------------------------------------------- terrain
def terrain_h(x, y):
    near = 0.16 * nz(x * 0.12, y * 0.12, 0.5) + 0.05 * nz(x * 0.4, y * 0.4, 3.1)
    calm = 1.0 - 0.65 * math.exp(-(y * y) / 5.0)
    h = near * calm
    far = smoothstep(9.0, 34.0, y)
    h += far * (2.6 + 2.2 * nz(x * 0.05, y * 0.04, 7.3) + 0.6 * nz(x * 0.13, y * 0.1, 9.9))
    d = path_dist(x, y)
    if d < 0.4:
        h -= 0.035 * (1.0 - smoothstep(-0.1, 0.4, d))
    return h


def link_obj(name, mesh, coll=None):
    ob = bpy.data.objects.new(name, mesh)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def mesh_from_bm(name, bm, mats, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if smooth:
        me.shade_smooth()
    else:
        me.shade_flat()
    return me


def tag(verts, mi):
    for v in verts:
        for f in v.link_faces:
            f.material_index = mi


def add_box(bm, center, size, rot=(0, 0, 0), mi=0):
    M = Matrix.Translation(center) @ Euler(rot, 'XYZ').to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1.0))
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    tag(r['verts'], mi)
    return r['verts']


def add_cone(bm, base, r1, r2, depth, segs=6, rot=(0, 0, 0), mi=0):
    M = Matrix.Translation(base) @ Euler(rot, 'XYZ').to_matrix().to_4x4() @ Matrix.Translation((0, 0, depth / 2))
    r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2,
                              depth=depth, matrix=M)
    tag(r['verts'], mi)
    return r['verts']


def add_ico(bm, center, radius, subdiv=1, scale=(1, 1, 1), mi=0, jitter=0.0, rng=None):
    M = Matrix.Translation(center) @ Matrix.Diagonal((radius * scale[0], radius * scale[1], radius * scale[2], 1.0))
    r = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0, matrix=M)
    if jitter and rng:
        for v in r['verts']:
            v.co += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * jitter * radius
    tag(r['verts'], mi)
    return r['verts']


def build_ground(mat):
    xs = [-48.0 + i * 0.6 for i in range(161)]
    ys = []
    y = -14.0
    while y < 86.0:
        ys.append(y)
        y += 0.32 + 0.032 * max(y + 10.0, 0.0)
    rng = random.Random(11)
    verts = []
    for y in ys:
        for x in xs:
            jx = rng.uniform(-0.12, 0.12)
            jy = rng.uniform(-0.08, 0.08)
            verts.append((x + jx, y + jy, terrain_h(x + jx, y + jy)))
    nx = len(xs)
    faces = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new('ground')
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    me.shade_smooth()
    return link_obj('Ground', me)


def build_ridge(name, y0, base, amp, freq, seed, mat):
    xs = [-320.0 + i * 5.0 for i in range(129)]
    rows = [(y0, 0.25), (y0 + 14.0, 1.0), (y0 + 30.0, 0.92)]
    verts = []
    for (yy, k) in rows:
        for x in xs:
            hgt = base + amp * (0.65 * nz(x * freq, seed, 1.3) + 0.35 * nz(x * freq * 2.7, seed + 4.0, 2.1))
            verts.append((x, yy, hgt * k))
    nx = len(xs)
    faces = []
    for j in range(len(rows) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    me.shade_smooth()
    return link_obj(name, me)


def build_sky(mat):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=450.0)
    me = mesh_from_bm('sky', bm, [mat], smooth=True)
    ob = link_obj('Sky', me)
    ob.visible_shadow = False
    return ob


def build_cloud(name, center, size, seed, mat, flat=0.72):
    rng = random.Random(seed)
    bm = bmesh.new()
    n = rng.randint(4, 7)
    for i in range(n):
        t = (i / (n - 1) - 0.5) if n > 1 else 0.0
        r = size * (0.30 + 0.22 * rng.random()) * (1.0 - abs(t) * 0.7)
        c = Vector((t * size * 1.15 + rng.uniform(-0.08, 0.08) * size,
                    rng.uniform(-0.12, 0.12) * size,
                    r * 0.45 * rng.random()))
        add_ico(bm, c, r, subdiv=2, scale=(1.0, 0.8, flat))
    floor = -size * 0.06
    for v in bm.verts:
        if v.co.z < floor:
            v.co.z = floor + (v.co.z - floor) * 0.12
    me = mesh_from_bm(name, bm, [mat], smooth=True)
    ob = link_obj(name, me)
    ob.location = center
    ob.visible_shadow = False
    return ob


# --------------------------------------------------------------------------- props
def build_fence(mats, cfg):
    """mats: [rail, post]. Posts every ~2.1 m along y=0 except the gate gap."""
    rng = random.Random(23)
    bm = bmesh.new()
    xs_left = [-0.86 - 2.1 * i for i in range(1, 9)]
    xs_right = [0.86 + 2.1 * i for i in range(1, 9)]
    posts = []
    for x in sorted(xs_left) + xs_right:
        yj = rng.uniform(-0.04, 0.04)
        g = terrain_h(x, yj)
        lean = (rng.uniform(-0.035, 0.035), rng.uniform(-0.035, 0.035), rng.uniform(-0.2, 0.2))
        hgt = 1.12 + rng.uniform(-0.04, 0.04)
        add_box(bm, (x, yj, g + hgt / 2 - 0.15), (0.13, 0.13, hgt + 0.3), lean, mi=1)
        add_cone(bm, (x, yj, g + hgt - 0.15 + 0.15), 0.093, 0.0, 0.07, segs=4, rot=(0, 0, math.pi / 4), mi=1)
        posts.append((x, yj, g))
    # rails between neighbours on each side + the gate posts
    def rails(seq, broken=None):
        for (a, b) in zip(seq[:-1], seq[1:]):
            for k, zr in enumerate((0.45, 0.90)):
                pa = Vector((a[0], a[1] - 0.085, a[2] + zr))
                pb = Vector((b[0], b[1] - 0.085, b[2] + zr))
                if broken and abs(a[0] - broken[0]) < 0.01 and k == 1:
                    pb = Vector((b[0] - 0.25, b[1] - 0.35, terrain_h(b[0] - 0.25, b[1] - 0.35) + 0.05))
                mid = (pa + pb) / 2
                d = pb - pa
                L = d.length + 0.12
                yaw = math.atan2(d.y, d.x)
                pitch = -math.atan2(d.z, math.hypot(d.x, d.y))
                add_box(bm, mid, (L, 0.045, 0.11 + rng.uniform(-0.01, 0.01)),
                        (rng.uniform(-0.03, 0.03), pitch, yaw), mi=0)
    gl = (-0.86, 0.0, terrain_h(-0.86, 0.0))
    gr = (0.86, 0.0, terrain_h(0.86, 0.0))
    left = [p for p in posts if p[0] < 0] + [gl]
    right = [gr] + [p for p in posts if p[0] > 0]
    rails(left, broken=(left[-2][0],) if cfg.get('broken_rail') else None)
    rails(right)
    me = mesh_from_bm('fence', bm, mats)
    return link_obj('Fence', me)


def build_gate(mats, open_deg, sag_deg):
    """mats: [wood, post, metal]. Returns (posts object, hinge empty, leaf object)."""
    bm = bmesh.new()
    for x in (-0.86, 0.86):
        g = terrain_h(x, 0.0)
        add_box(bm, (x, 0.0, g + 0.62), (0.17, 0.17, 1.55), mi=1)
        add_cone(bm, (x, 0.0, g + 1.395), 0.122, 0.0, 0.09, segs=4, rot=(0, 0, math.pi / 4), mi=1)
    # latch block on the right post
    g = terrain_h(0.86, 0.0)
    add_box(bm, (0.86 - 0.09, -0.02, g + 0.98), (0.03, 0.05, 0.10), mi=2)
    posts = link_obj('GatePosts', mesh_from_bm('gateposts', bm, mats))

    gz = terrain_h(-0.86, 0.0)
    hinge = bpy.data.objects.new('GateHinge', None)
    bpy.context.scene.collection.objects.link(hinge)
    hinge.location = (-0.775, 0.0, gz + 1.02)
    hinge.rotation_euler = (0.0, math.radians(sag_deg), math.radians(open_deg))

    bm = bmesh.new()
    L = 1.53
    zb = -0.86  # bottom board relative to the hinge (top hinge height)
    for zz in (zb, zb + 0.40, zb + 0.80):
        add_box(bm, (L / 2, 0.0, zz), (L, 0.04, 0.115), mi=0)
    for xx in (0.05, L - 0.05):
        add_box(bm, (xx, 0.012, zb + 0.40), (0.09, 0.045, 0.95), mi=0)
    # diagonal brace (hinge bottom -> free end top)
    a = Vector((0.16, -0.03, zb + 0.10))
    b = Vector((L - 0.16, -0.03, zb + 0.70))
    d = b - a
    add_box(bm, (a + b) / 2, (d.length, 0.035, 0.10), (0, -math.atan2(d.z, d.x), 0), mi=0)
    for zz in (zb + 0.80, zb):
        add_box(bm, (0.17, -0.03, zz), (0.30, 0.012, 0.05), mi=2)
    leaf = link_obj('GateLeaf', mesh_from_bm('gateleaf', bm, mats))
    leaf.parent = hinge
    return posts, hinge, leaf


def build_barn(mats, cfg):
    """mats: [wall, roof, trim, dark]."""
    bm = bmesh.new()
    W, D, Hw, Hr = 4.6, 5.6, 2.7, 4.25
    add_box(bm, (0, 0, Hw / 2 - 0.2), (W, D, Hw + 0.4), mi=0)
    # gables
    for sy in (-1, 1):
        y = sy * D / 2
        vs = [bm.verts.new((-W / 2, y, Hw - 0.01)), bm.verts.new((W / 2, y, Hw - 0.01)), bm.verts.new((0, y, Hr))]
        f = bm.faces.new(vs if sy > 0 else list(reversed(vs)))
        f.material_index = 0
    rise = Hr - Hw
    half = W / 2
    slab = math.hypot(half, rise) + 0.42
    ang = math.atan2(rise, half)
    for sx in (-1, 1):
        c = Vector((sx * (half / 2 + 0.12), 0.0, Hw + rise / 2 + 0.05))
        add_box(bm, c, (slab, D + 0.55, 0.13), (0, sx * ang, 0), mi=1)
    # ridge cap
    add_box(bm, (0, 0, Hr + 0.08), (0.22, D + 0.6, 0.10), mi=1)
    # front: big door with cream trim and an X brace, hayloft door
    fy = -D / 2 - 0.03
    add_box(bm, (0, fy, 1.05), (1.9, 0.06, 2.1), mi=3 if cfg.get('door_open') else 0)
    for (x, z, sx, sz) in ((-0.98, 1.08, 0.12, 2.25), (0.98, 1.08, 0.12, 2.25), (0, 2.16, 2.08, 0.12)):
        add_box(bm, (x, fy - 0.03, z), (sx, 0.06, sz), mi=2)
    if not cfg.get('door_open'):
        for s in (-1, 1):
            add_box(bm, (0, fy - 0.035, 1.05), (2.45, 0.05, 0.11), (0, s * math.atan2(2.0, 1.8), 0), mi=2)
    add_box(bm, (0, fy, 3.25), (0.85, 0.06, 0.75), mi=3)
    add_box(bm, (0, fy - 0.03, 3.25), (1.0, 0.05, 0.1), mi=2)
    add_box(bm, (0, fy - 0.03, 3.65), (1.0, 0.05, 0.1), mi=2)
    # corner boards
    for sx in (-1, 1):
        for sy in (-1, 1):
            add_box(bm, (sx * (W / 2 + 0.01), sy * (D / 2 + 0.01), Hw / 2 - 0.2), (0.14, 0.14, Hw + 0.4), mi=2)
    # side window
    add_box(bm, (W / 2 + 0.03, -0.6, 1.6), (0.06, 0.8, 0.7), mi=3)
    add_box(bm, (W / 2 + 0.05, -0.6, 1.6), (0.05, 0.92, 0.09), mi=2)
    add_box(bm, (-W / 2 - 0.03, 0.6, 1.6), (0.06, 0.8, 0.7), mi=3)
    if cfg.get('roof_hole'):
        c = Vector((-(half / 2 + 0.12) - 0.08, -0.9, Hw + rise / 2 + 0.13))
        add_box(bm, c, (0.9, 1.1, 0.03), (0, -ang, 0), mi=3)
    me = mesh_from_bm('barn', bm, mats)
    ob = link_obj('Barn', me)
    return ob


def build_tree(name, loc, height, crown, seed, mats, sway=0.0, coll=None):
    rng = random.Random(seed)
    x, y = loc
    g = terrain_h(x, y)
    bm = bmesh.new()
    add_cone(bm, (0, 0, -0.3), 0.20 * height / 4.2, 0.11 * height / 4.2, height * 0.62 + 0.3, segs=6, mi=0)
    for (a, b, z) in ((0.35, -0.2, 0.42), (-0.45, 0.1, 0.5)):
        add_cone(bm, (0, 0, height * z), 0.06, 0.03, 0.7 * height / 4.2, segs=5,
                 rot=(b, a, 0), mi=0)
    trunk = link_obj(name + '_trunk', mesh_from_bm(name + '_trunk', bm, [mats[0]]), coll)
    trunk.location = (x, y, g)
    bm = bmesh.new()
    top = height * 0.62
    blobs = [(0, 0, crown * 0.55, 1.0)]
    for i in range(4):
        a = i * math.pi / 2 + rng.uniform(-0.4, 0.4)
        r = crown * rng.uniform(0.45, 0.62)
        blobs.append((math.cos(a) * crown * 0.55, math.sin(a) * crown * 0.45, crown * rng.uniform(0.15, 0.6), r / crown))
    blobs.append((rng.uniform(-0.2, 0.2) * crown, 0, crown * 1.05, 0.6))
    for (bx, by, bz, rr) in blobs:
        add_ico(bm, Vector((bx, by, bz)), crown * rr, subdiv=1, scale=(1.0, 1.0, 0.86), mi=0,
                jitter=0.07, rng=rng)
    cr = link_obj(name + '_crown', mesh_from_bm(name + '_crown', bm, [mats[1]]), coll)
    cr.location = (x, y, g + top)
    if sway:
        ph = rng.uniform(0, 6.28)
        drive(cr, 'rotation_euler', f'{sway:.4f}*sin(2*pi*frame/{LOOP_FRAMES}*2+{ph:.3f})', 1)
        drive(cr, 'rotation_euler', f'{sway * 0.5:.4f}*sin(2*pi*frame/{LOOP_FRAMES}*3+{ph * 1.7:.3f})', 0)
    return trunk, cr


def build_rock(name, loc, size, seed, mat, squash=0.6):
    rng = random.Random(seed)
    bm = bmesh.new()
    add_ico(bm, Vector((0, 0, 0)), 1.0, subdiv=1, scale=(1.0, rng.uniform(0.7, 1.0), squash), jitter=0.18, rng=rng)
    me = mesh_from_bm(name, bm, [mat])
    ob = link_obj(name, me)
    x, y = loc
    ob.location = (x, y, terrain_h(x, y) + size * squash * 0.35)
    ob.scale = (size, size, size)
    ob.rotation_euler = (0, 0, rng.uniform(0, 6.28))
    return ob


# --------------------------------------------------------------------------- instance templates
def template(name, bm, mats, smooth=False, attrs=None, up_normals=False):
    me = mesh_from_bm(name, bm, mats, smooth or up_normals)
    if up_normals:
        me.normals_split_custom_set_from_vertices([(0.0, 0.0, 1.0)] * len(me.vertices))
    if attrs:
        for an, vals in attrs.items():
            a = me.attributes.new(an, 'FLOAT', 'POINT')
            a.data.foreach_set('value', vals)
    ob = link_obj('T_' + name, me)
    ob.location = (0, 0, TEMPLATE_Z)
    ob.hide_render = False
    ob.visible_shadow = False  # instances inherit this: vegetation/particles never cast shadows
    return ob


def blade_tuft(name, seed, n, hmin, hmax, width, lean, mats, segs=2, heads=0, head_mi=1, head_r=0.022):
    """Low-poly tuft: n tapered blades around the origin; vertex attribute 'h' = 0 base .. 1 tip."""
    rng = random.Random(seed)
    bm = bmesh.new()
    hv = {}
    for i in range(n):
        a = i * 2 * math.pi / n + rng.uniform(-0.4, 0.4)
        dirv = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-dirv.y, dirv.x, 0))
        hgt = rng.uniform(hmin, hmax)
        w = width * rng.uniform(0.8, 1.2)
        ln = lean * rng.uniform(0.5, 1.3)
        root = dirv * rng.uniform(0.0, 0.035)
        ring = []
        for s in range(segs + 1):
            t = s / segs
            c = root + dirv * (ln * hgt * t * t) + Vector((0, 0, hgt * t * (1 - 0.18 * t * ln)))
            ww = w * (1 - t) * 0.5
            if s < segs:
                v1 = bm.verts.new(c - side * ww)
                v2 = bm.verts.new(c + side * ww)
                hv[v1] = t
                hv[v2] = t
                ring.append((v1, v2))
            else:
                vt = bm.verts.new(c)
                hv[vt] = 1.0
                ring.append((vt,))
        for s in range(segs):
            a0 = ring[s]
            a1 = ring[s + 1]
            if len(a1) == 2:
                f = bm.faces.new((a0[0], a0[1], a1[1], a1[0]))
            else:
                f = bm.faces.new((a0[0], a0[1], a1[0]))
            f.material_index = 0
    for i in range(heads):
        a = rng.uniform(0, 6.28)
        dirv = Vector((math.cos(a), math.sin(a), 0))
        hgt = rng.uniform(hmax * 0.9, hmax * 1.25)
        tip = dirv * hgt * 0.18 + Vector((0, 0, hgt))
        side = Vector((-dirv.y, dirv.x, 0)) * 0.006
        v0 = bm.verts.new(-side)
        v1 = bm.verts.new(side)
        v2 = bm.verts.new(tip)
        for v, t in ((v0, 0.0), (v1, 0.0), (v2, 1.0)):
            hv[v] = t
        bm.faces.new((v0, v1, v2)).material_index = 0
        hverts = add_ico(bm, tip + Vector((0, 0, head_r * 1.4)), head_r, subdiv=1, scale=(0.7, 0.7, 1.9), mi=head_mi)
        for v in hverts:
            hv[v] = 1.0
    bm.verts.index_update()
    vals = [0.0] * len(bm.verts)
    for v in bm.verts:
        vals[v.index] = hv.get(v, 1.0)
    return template(name, bm, mats, attrs={'h': vals}, up_normals=True)


def flower_tuft(name, seed, mats, count=3):
    """mats: [stem, petal, centre]."""
    rng = random.Random(seed)
    bm = bmesh.new()
    for i in range(count):
        a = rng.uniform(0, 6.28)
        base = Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.0, 0.07)
        hgt = rng.uniform(0.14, 0.26)
        top = base + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), hgt))
        side = Vector((0.004, 0, 0))
        v = [bm.verts.new(base - side), bm.verts.new(base + side), bm.verts.new(top)]
        bm.faces.new(v).material_index = 0
        r = rng.uniform(0.028, 0.04)
        tilt = Matrix.Rotation(rng.uniform(0.2, 0.6), 4, Vector((math.cos(a), math.sin(a), 0)).cross(Vector((0, 0, 1))))
        cverts = []
        for k in range(5):
            ang = k * 2 * math.pi / 5 + a
            p1 = Vector((math.cos(ang - 0.45) * r * 0.45, math.sin(ang - 0.45) * r * 0.45, 0))
            p2 = Vector((math.cos(ang) * r, math.sin(ang) * r, 0.004))
            p3 = Vector((math.cos(ang + 0.45) * r * 0.45, math.sin(ang + 0.45) * r * 0.45, 0))
            vv = [bm.verts.new(top + (tilt @ p)) for p in (Vector((0, 0, 0.002)), p1, p2, p3)]
            bm.faces.new(vv).material_index = 1
        cv = add_ico(bm, top + Vector((0, 0, 0.008)), r * 0.32, subdiv=1, scale=(1, 1, 0.6), mi=2)
        cverts.extend(cv)
    return template(name, bm, mats)


def leaf_template(name, mats, size=0.07):
    bm = bmesh.new()
    pts = [(0, -size / 2, 0), (size * 0.28, -size * 0.05, 0.006), (0, size / 2, 0.0), (-size * 0.28, -size * 0.05, 0.006)]
    vs = [bm.verts.new(p) for p in pts]
    mid = bm.verts.new((0, 0, -0.004))
    bm.faces.new((vs[0], vs[1], mid))
    bm.faces.new((vs[1], vs[2], mid))
    bm.faces.new((vs[2], vs[3], mid))
    bm.faces.new((vs[3], vs[0], mid))
    return template(name, bm, mats)


def gn_ids(gn):
    return {it.name: it.identifier for it in gn.interface.items_tree if getattr(it, 'in_out', '') == 'INPUT'}


def set_inputs(mod, gn, **values):
    """Blender 5.x: modifier inputs live at mod.properties.inputs.<Socket_N>.value."""
    ids = gn_ids(gn)
    for k, v in values.items():
        getattr(mod.properties.inputs, ids[k]).value = v


def input_path(modname, gn, name):
    return f'modifiers["{modname}"].properties.inputs.{gn_ids(gn)[name]}.value'


def scatter_object(name, pts, gn, inst, wind, freq, scale_mul=1.0):
    """pts: list of (x, y, z, yaw, scale, phase)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(p[0], p[1], p[2]) for p in pts], [], [])
    for i, an in ((3, 'yaw'), (4, 'scale'), (5, 'phase')):
        a = me.attributes.new(an, 'FLOAT', 'POINT')
        a.data.foreach_set('value', [p[i] for p in pts])
    ob = link_obj(name, me)
    ob.visible_shadow = False
    mod = ob.modifiers.new('Scatter', 'NODES')
    mod.node_group = gn
    set_inputs(mod, gn, Instance=inst, Wind=wind, Freq=freq, ScaleMul=scale_mul)
    return ob


def particles_object(name, gn, inst, **kw):
    me = bpy.data.meshes.new(name)
    ob = link_obj(name, me)
    ob.visible_shadow = False
    mod = ob.modifiers.new('Particles', 'NODES')
    mod.node_group = gn
    set_inputs(mod, gn, Instance=inst, **kw)
    return ob


# --------------------------------------------------------------------------- geometry node groups
def gn_tree(name):
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    try:
        ng.is_modifier = True
    except AttributeError:
        pass
    return ng


def build_gn_scatter():
    ng = gn_tree('WS_Scatter')
    iface(ng, 'Geometry', 'OUTPUT', 'NodeSocketGeometry')
    iface(ng, 'Geometry', 'INPUT', 'NodeSocketGeometry')
    iface(ng, 'Instance', 'INPUT', 'NodeSocketObject')
    iface(ng, 'Wind', 'INPUT', 'NodeSocketFloat', 0.1)
    iface(ng, 'Freq', 'INPUT', 'NodeSocketFloat', 1.5)
    iface(ng, 'ScaleMul', 'INPUT', 'NodeSocketFloat', 1.0)
    nb = NB(ng)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')

    def attr(n):
        a = nb.new('GeometryNodeInputNamedAttribute', data_type='FLOAT')
        a.inputs['Name'].default_value = n
        return a.outputs['Attribute']

    oi = nb.new('GeometryNodeObjectInfo')
    nb.link(gi.outputs['Instance'], oi.inputs['Object'])
    oi.inputs['As Instance'].default_value = True
    e2r = nb.new('FunctionNodeEulerToRotation')
    nb.put(e2r.inputs['Euler'], nb.comb(0.0, 0.0, attr('yaw')))
    iop = nb.new('GeometryNodeInstanceOnPoints')
    nb.link(gi.outputs['Geometry'], iop.inputs['Points'])
    nb.link(oi.outputs['Geometry'], iop.inputs['Instance'])
    nb.link(e2r.outputs['Rotation'], iop.inputs['Rotation'])
    nb.put(iop.inputs['Scale'], nb.math('MULTIPLY', attr('scale'), gi.outputs['ScaleMul']))

    t = nb.new('GeometryNodeInputSceneTime').outputs['Seconds']
    px, py, _pz = nb.sep(nb.new('GeometryNodeInputPosition').outputs['Position'])
    a = nb.math('ADD', nb.math('MULTIPLY', t, gi.outputs['Freq']),
                nb.math('ADD', nb.math('MULTIPLY', px, 0.55), nb.math('MULTIPLY', py, 0.35)))
    w = nb.math('ADD', nb.math('SINE', a),
                nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY_ADD', a, 2.0, attr('phase'))), 0.4))
    ry = nb.math('MULTIPLY', gi.outputs['Wind'], nb.math('MULTIPLY_ADD', w, 0.7, 0.55))
    b = nb.math('ADD', nb.math('MULTIPLY', t, nb.math('MULTIPLY', gi.outputs['Freq'], 2.0)),
                nb.math('ADD', nb.math('MULTIPLY', py, 0.9), attr('phase')))
    rx = nb.math('MULTIPLY', gi.outputs['Wind'], nb.math('MULTIPLY', nb.math('SINE', b), 0.35))
    e2 = nb.new('FunctionNodeEulerToRotation')
    nb.put(e2.inputs['Euler'], nb.comb(rx, ry, 0.0))
    ri = nb.new('GeometryNodeRotateInstances')
    nb.link(iop.outputs['Instances'], ri.inputs['Instances'])
    nb.link(e2.outputs['Rotation'], ri.inputs['Rotation'])
    nb.link(nb.new('GeometryNodeInputPosition').outputs['Position'], ri.inputs['Pivot Point'])
    ri.inputs['Local Space'].default_value = False
    nb.link(ri.outputs['Instances'], go.inputs['Geometry'])
    return ng


def build_gn_particles():
    ng = gn_tree('WS_Particles')
    iface(ng, 'Geometry', 'OUTPUT', 'NodeSocketGeometry')
    iface(ng, 'Geometry', 'INPUT', 'NodeSocketGeometry')
    iface(ng, 'Instance', 'INPUT', 'NodeSocketObject')
    iface(ng, 'Count', 'INPUT', 'NodeSocketInt', 100)
    iface(ng, 'BoxMin', 'INPUT', 'NodeSocketVector', (-5.0, -5.0, 0.0))
    iface(ng, 'BoxMax', 'INPUT', 'NodeSocketVector', (5.0, 5.0, 5.0))
    iface(ng, 'Velocity', 'INPUT', 'NodeSocketVector', (0.0, 0.0, -1.0))
    iface(ng, 'Seed', 'INPUT', 'NodeSocketInt', 0)
    iface(ng, 'Sway', 'INPUT', 'NodeSocketFloat', 0.0)
    iface(ng, 'SwayFreq', 'INPUT', 'NodeSocketFloat', 1.0)
    iface(ng, 'Tumble', 'INPUT', 'NodeSocketFloat', 0.0)
    iface(ng, 'Spin', 'INPUT', 'NodeSocketFloat', 0.0)
    iface(ng, 'ScaleMin', 'INPUT', 'NodeSocketFloat', 1.0)
    iface(ng, 'ScaleMax', 'INPUT', 'NodeSocketFloat', 1.0)
    iface(ng, 'Fade', 'INPUT', 'NodeSocketFloat', 0.08)
    nb = NB(ng)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')
    G = gi.outputs

    def rnd(kind, lo, hi, seed_off):
        r = nb.new('FunctionNodeRandomValue', data_type=kind)
        typ = 'VECTOR' if kind == 'FLOAT_VECTOR' else 'VALUE'
        nb.put(NB.by_name(r.inputs, 'Min', typ), lo)
        nb.put(NB.by_name(r.inputs, 'Max', typ), hi)
        nb.put(NB.by_name(r.inputs, 'Seed'), nb.math('ADD', G['Seed'], float(seed_off)))
        return NB.by_name(r.outputs, 'Value', 'VECTOR' if kind == 'FLOAT_VECTOR' else 'VALUE')

    t = nb.new('GeometryNodeInputSceneTime').outputs['Seconds']
    size = nb.vmath('SUBTRACT', G['BoxMax'], G['BoxMin'])
    p0 = nb.vmath('ADD', G['BoxMin'], nb.vmath('MULTIPLY', rnd('FLOAT_VECTOR', (0, 0, 0), (1, 1, 1), 0), size))
    p = nb.vmath('ADD', p0, nb.vmath('SCALE', G['Velocity'], scale=t))
    pw = nb.vmath('WRAP', p, G['BoxMax'], G['BoxMin'])
    ph = rnd('FLOAT', 0.0, 6.2832, 1)
    tf = nb.math('MULTIPLY', t, G['SwayFreq'])
    sx = nb.math('SINE', nb.math('ADD', tf, ph))
    sy = nb.math('SINE', nb.math('ADD', tf, nb.math('MULTIPLY_ADD', ph, 1.7, 1.0)))
    sz = nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY_ADD', tf, 2.0, ph)), 0.5)
    pos = nb.vmath('ADD', pw, nb.vmath('SCALE', nb.comb(sx, sy, sz), scale=G['Sway']))
    # fade to zero size near the wrap faces of the box
    tn = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', pw, G['BoxMin']), size)
    fades = []
    for c in nb.sep(tn):
        lo = nb.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        nb.put(lo.inputs['Value'], c)
        lo.inputs['From Min'].default_value = 0.0
        nb.put(lo.inputs['From Max'], G['Fade'])
        hi = nb.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        nb.put(hi.inputs['Value'], c)
        hi.inputs['From Min'].default_value = 1.0
        nb.put(hi.inputs['From Max'], nb.math('SUBTRACT', 1.0, G['Fade']))
        fades.append(nb.math('MINIMUM', lo.outputs['Result'], hi.outputs['Result']))
    fade = nb.math('MINIMUM', nb.math('MINIMUM', fades[0], fades[1]), fades[2])

    pts = nb.new('GeometryNodePoints')
    nb.put(pts.inputs['Count'], G['Count'])
    nb.put(pts.inputs['Position'], pos)
    rr = rnd('FLOAT_VECTOR', (0, 0, 0), (6.2832, 6.2832, 6.2832), 2)
    spin = nb.math('MULTIPLY', nb.math('MULTIPLY', t, G['Spin']), rnd('FLOAT', 0.5, 1.5, 3))
    rot = nb.vmath('SCALE', nb.vmath('ADD', rr, nb.comb(spin, nb.math('MULTIPLY', spin, 0.7), nb.math('MULTIPLY', spin, 0.4))),
                   scale=G['Tumble'])
    e2r = nb.new('FunctionNodeEulerToRotation')
    nb.put(e2r.inputs['Euler'], rot)
    oi = nb.new('GeometryNodeObjectInfo')
    nb.link(G['Instance'], oi.inputs['Object'])
    oi.inputs['As Instance'].default_value = True
    iop = nb.new('GeometryNodeInstanceOnPoints')
    nb.link(pts.outputs[0], iop.inputs['Points'])
    nb.link(oi.outputs['Geometry'], iop.inputs['Instance'])
    nb.link(e2r.outputs['Rotation'], iop.inputs['Rotation'])
    nb.put(iop.inputs['Scale'], nb.math('MULTIPLY', rnd('FLOAT', G['ScaleMin'], G['ScaleMax'], 4), fade))
    nb.link(iop.outputs['Instances'], go.inputs['Geometry'])
    return ng


def build_gn_flutter():
    ng = gn_tree('WS_Flutter')
    iface(ng, 'Geometry', 'OUTPUT', 'NodeSocketGeometry')
    iface(ng, 'Geometry', 'INPUT', 'NodeSocketGeometry')
    iface(ng, 'Amp', 'INPUT', 'NodeSocketFloat', 1.0)
    iface(ng, 'Freq', 'INPUT', 'NodeSocketFloat', 6.0)
    iface(ng, 'Height', 'INPUT', 'NodeSocketFloat', 0.2)
    nb = NB(ng)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')
    G = gi.outputs
    x, _y, z = nb.sep(nb.new('GeometryNodeInputPosition').outputs['Position'])
    s = nb.math('DIVIDE', nb.math('MULTIPLY', z, -1.0), G['Height'], clamp=True)
    s15 = nb.math('POWER', s, 1.5)
    t = nb.new('GeometryNodeInputSceneTime').outputs['Seconds']
    tf = nb.math('MULTIPLY', t, G['Freq'])
    w1 = nb.math('SINE', nb.math('MULTIPLY_ADD', s, -2.4, tf))
    w2 = nb.math('SINE', nb.math('ADD', nb.math('MULTIPLY', tf, 2.0), nb.math('MULTIPLY_ADD', x, 14.0, nb.math('MULTIPLY', s, 3.6))))
    lift = nb.math('MULTIPLY', s15, nb.math('MULTIPLY_ADD', w1, 0.030, 0.042))
    lift = nb.math('ADD', lift, nb.math('MULTIPLY', nb.math('MULTIPLY', s, 0.012), w2))
    twist = nb.math('MULTIPLY', nb.math('MULTIPLY', x, s), nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY_ADD', tf, 3.0, 0.7)), 0.55))
    lift = nb.math('MAXIMUM', nb.math('MULTIPLY', nb.math('ADD', lift, twist), G['Amp']), 0.0)
    sxo = nb.math('MULTIPLY', nb.math('MULTIPLY', s15, nb.math('SINE', nb.math('MULTIPLY_ADD', tf, 1.0, 1.9))), nb.math('MULTIPLY', G['Amp'], 0.010))
    off = nb.comb(sxo, nb.math('MULTIPLY', lift, -1.0), nb.math('MULTIPLY', lift, 0.32))
    sp = nb.new('GeometryNodeSetPosition')
    nb.link(G['Geometry'], sp.inputs['Geometry'])
    nb.put(sp.inputs['Offset'], off)
    nb.link(sp.outputs['Geometry'], go.inputs['Geometry'])
    return ng


def build_gn_drips():
    ng = gn_tree('WS_Drips')
    iface(ng, 'Geometry', 'OUTPUT', 'NodeSocketGeometry')
    iface(ng, 'Geometry', 'INPUT', 'NodeSocketGeometry')
    iface(ng, 'Instance', 'INPUT', 'NodeSocketObject')
    nb = NB(ng)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')
    G = gi.outputs

    def attr(n):
        a = nb.new('GeometryNodeInputNamedAttribute', data_type='FLOAT')
        a.inputs['Name'].default_value = n
        return a.outputs['Attribute']

    t = nb.new('GeometryNodeInputSceneTime').outputs['Seconds']
    per = attr('period')
    tau = nb.math('FLOORED_MODULO', nb.math('ADD', t, attr('phase')), per)
    hang = nb.math('MULTIPLY', per, 0.68)
    fall = nb.math('MAXIMUM', nb.math('SUBTRACT', tau, hang), 0.0)
    grow = nb.math('DIVIDE', tau, hang, clamp=True)
    dz = nb.math('SUBTRACT', nb.math('MULTIPLY', nb.math('MULTIPLY', fall, fall), -4.9), nb.math('MULTIPLY', grow, 0.006))
    sp = nb.new('GeometryNodeSetPosition')
    nb.link(G['Geometry'], sp.inputs['Geometry'])
    nb.put(sp.inputs['Offset'], nb.comb(0.0, 0.0, dz))
    cmp_ = nb.new('FunctionNodeCompare', data_type='FLOAT', operation='GREATER_THAN')
    nb.put(cmp_.inputs[0], dz)
    cmp_.inputs[1].default_value = -1.4
    sxy = nb.math('MULTIPLY_ADD', grow, 0.65, 0.35)
    szz = nb.math('MULTIPLY', sxy, nb.math('ADD', 1.0, nb.math('MINIMUM', nb.math('MULTIPLY', fall, 9.0), 1.3)))
    oi = nb.new('GeometryNodeObjectInfo')
    nb.link(G['Instance'], oi.inputs['Object'])
    oi.inputs['As Instance'].default_value = True
    iop = nb.new('GeometryNodeInstanceOnPoints')
    nb.link(sp.outputs['Geometry'], iop.inputs['Points'])
    nb.link(cmp_.outputs['Result'], iop.inputs['Selection'])
    nb.link(oi.outputs['Geometry'], iop.inputs['Instance'])
    nb.put(iop.inputs['Scale'], nb.comb(sxy, sxy, szz))
    nb.link(iop.outputs['Instances'], go.inputs['Geometry'])
    return ng


# --------------------------------------------------------------------------- special materials
def emission_mat(name, color, strength=1.0, alpha=None, method='DITHERED'):
    m, nb = new_mat(name)
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], color if isinstance(color, bpy.types.NodeSocket) else color)
    em.inputs['Strength'].default_value = strength
    out = nb.new('ShaderNodeOutputMaterial')
    if alpha is None:
        nb.link(em.outputs[0], out.inputs['Surface'])
    else:
        tr = nb.new('ShaderNodeBsdfTransparent')
        mx = nb.new('ShaderNodeMixShader')
        nb.put(mx.inputs['Fac'], alpha)
        nb.link(tr.outputs[0], mx.inputs[1])
        nb.link(em.outputs[0], mx.inputs[2])
        nb.link(mx.outputs[0], out.inputs['Surface'])
        m.surface_render_method = method
    return m, nb


def rain_material(P):
    m, nb = new_mat('M_rain')
    lw = nb.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.5
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], lin('#c6d3df'))
    em.inputs['Strength'].default_value = 0.75
    tr = nb.new('ShaderNodeBsdfTransparent')
    mx = nb.new('ShaderNodeMixShader')
    nb.put(mx.inputs['Fac'], 0.30)
    nb.link(tr.outputs[0], mx.inputs[1])
    nb.link(em.outputs[0], mx.inputs[2])
    out = nb.new('ShaderNodeOutputMaterial')
    nb.link(mx.outputs[0], out.inputs['Surface'])
    m.surface_render_method = 'DITHERED'
    return m


def puddle_material(P, time_expr):
    m, nb = new_mat('M_puddle')
    geo = nb.new('ShaderNodeNewGeometry')
    pos = geo.outputs['Position']
    tnode = nb.new('ShaderNodeValue')
    drive_socket(tnode.outputs[0], time_expr)
    T = tnode.outputs[0]
    base = nb.mix(nb.noise(pos, 1.6, 2.0), lin('#3c4855'), lin('#4f5c6a'))
    rings_total = None
    for (scale, rate, seed) in ((7.0, 1.25, 0.0), (10.0, 1.25, 0.37)):
        v = nb.new('ShaderNodeTexVoronoi')
        v.voronoi_dimensions = '2D'
        nb.put(v.inputs['Vector'], nb.vmath('ADD', nb.vmath('SCALE', pos, scale=scale), (seed * 10, seed * 7, 0)))
        v.inputs['Scale'].default_value = 1.0
        rnd = nb.sep(v.outputs['Color'])[0]
        tt = nb.math('FRACT', nb.math('MULTIPLY_ADD', T, rate, rnd))
        rad = nb.math('MULTIPLY', tt, 0.42)
        dd = nb.math('ABSOLUTE', nb.math('SUBTRACT', v.outputs['Distance'], rad))
        fade = nb.math('POWER', nb.math('SUBTRACT', 1.0, tt), 2.0)
        ring = nb.math('MULTIPLY', nb.smooth(dd, 0.06, 0.0), fade)
        rings_total = ring if rings_total is None else nb.math('MAXIMUM', rings_total, ring)
    c = nb.vmath('ADD', base, nb.vmath('SCALE', lin('#a9b8c6'), scale=nb.math('MULTIPLY', rings_total, 0.30)))
    # darker rim where the water meets the mud
    a = nb.new('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name='edge')
    c = nb.vmath('ADD', c, nb.vmath('SCALE', lin('#7d8b99'), scale=nb.math('MULTIPLY', nb.smooth(a.outputs['Fac'], 0.8, 1.0), 0.18)))
    hs = nb.new('ShaderNodeHueSaturation')
    nb.put(hs.inputs['Color'], c)
    hs.inputs['Saturation'].default_value = 0.7
    cam = nb.new('ShaderNodeCameraData')
    f = nb.math('SUBTRACT', 1.0, nb.math('EXPONENT', nb.math('MULTIPLY', cam.outputs['View Distance'], -P['fogDen'])))
    fin = nb.mix(f, hs.outputs['Color'], P['fogCol'])
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], fin)
    out = nb.new('ShaderNodeOutputMaterial')
    nb.link(em.outputs[0], out.inputs['Surface'])
    return m


def mist_material(P):
    m, nb = new_mat('M_mist')
    tc = nb.new('ShaderNodeTexCoord')
    gen = tc.outputs['Generated']
    _gx, _gy, gz = nb.sep(gen)
    n = nb.noise(nb.vmath('MULTIPLY', tc.outputs['Object'], (0.22, 0.22, 0.9)), 1.0, 3.0, 0.55)
    dens = nb.math('MULTIPLY', nb.smooth(n, 0.35, 0.75), nb.smooth(gz, 0.95, 0.15))
    dens = nb.math('MULTIPLY', dens, nb.smooth(gz, 0.0, 0.12))
    alpha = nb.math('MULTIPLY', dens, 0.55)
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], tuple(min(1.0, c * 1.12) for c in P['fogCol'][:3]) + (1.0,))
    tr = nb.new('ShaderNodeBsdfTransparent')
    mx = nb.new('ShaderNodeMixShader')
    nb.put(mx.inputs['Fac'], alpha)
    nb.link(tr.outputs[0], mx.inputs[1])
    nb.link(em.outputs[0], mx.inputs[2])
    out = nb.new('ShaderNodeOutputMaterial')
    nb.link(mx.outputs[0], out.inputs['Surface'])
    m.surface_render_method = 'BLENDED'
    return m


def water_drop_material():
    m, nb = new_mat('M_drop')
    lw = nb.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.6
    c = nb.mix(lw.outputs['Facing'], lin('#c9d4ec'), lin('#fff1e2'))
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], c)
    em.inputs['Strength'].default_value = 0.95
    tr = nb.new('ShaderNodeBsdfTransparent')
    mx = nb.new('ShaderNodeMixShader')
    nb.put(mx.inputs['Fac'], nb.math('MULTIPLY_ADD', lw.outputs['Facing'], 0.5, 0.45))
    nb.link(tr.outputs[0], mx.inputs[1])
    nb.link(em.outputs[0], mx.inputs[2])
    out = nb.new('ShaderNodeOutputMaterial')
    nb.link(mx.outputs[0], out.inputs['Surface'])
    m.surface_render_method = 'BLENDED'
    return m


def drive_socket(sock, expr):
    fc = sock.driver_add('default_value')
    fc.driver.type = 'SCRIPTED'
    fc.driver.expression = expr
    return fc


# --------------------------------------------------------------------------- camera
LENS = 24.6
PITCH = 6.0
CAM_H = 1.75
LOOP_FRAMES = 168


def make_camera(name):
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = 'VERTICAL'
    cd.sensor_height = 24.0
    cd.sensor_width = 18.0
    cd.clip_start = 0.05
    cd.clip_end = 1500.0
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def project(cam, p):
    co = world_to_camera_view(bpy.context.scene, cam, Vector(p))
    return co.x, 1.0 - co.y, co.z


def screen_to_ground(cam, u, v):
    sc = bpy.context.scene
    tr, br, bl, tl = cam.data.view_frame(scene=sc)
    top = tl.lerp(tr, u)
    bot = bl.lerp(br, u)
    pt = top.lerp(bot, v)
    mw = cam.matrix_world
    o = mw.translation.copy()
    d = (mw.to_3x3() @ pt).normalized()
    lo, hi = 0.0, 400.0
    for _ in range(64):
        mid = (lo + hi) / 2
        q = o + d * mid
        if q.z > terrain_h(q.x, q.y):
            lo = mid
        else:
            hi = mid
    return o + d * hi


def place_ranch_camera(cam):
    cam.data.lens = LENS
    target = Vector((0.0, -0.3, terrain_h(0.0, -0.3)))
    lo, hi = -24.0, -4.0
    for _ in range(40):
        yc = (lo + hi) / 2
        cam.location = (0.0, yc, terrain_h(0.0, yc) + CAM_H)
        cam.rotation_euler = (math.radians(90.0 - PITCH), 0.0, 0.0)
        bpy.context.view_layer.update()
        _u, v, _d = project(cam, target)
        if v < 0.58:
            lo = yc
        else:
            hi = yc
    bpy.context.view_layer.update()
    return cam


# --------------------------------------------------------------------------- zones (screen space, 0..1, v from top)
def zone_welcome(u, v):
    if v < 0.50:
        return False
    hw = 0.085 + max(v - 0.56, 0.0) * 0.45
    return abs(u - 0.5) < hw


ZONES = {
    'welcome': [zone_welcome],
    'sad': [lambda u, v: 0.45 < u < 0.72 and 0.50 < v < 0.75],
    'abandoned': [lambda u, v: 0.37 < u < 0.69 and 0.60 < v < 0.83,
                  lambda u, v: 0.32 < u < 0.48 and 0.70 < v < 0.82],
}


def blocked(cam, zones, p, hgt, spread=0.0):
    offs = [(0.0, 0.0)]
    if spread:
        offs += [(spread, 0.0), (-spread, 0.0), (0.0, spread), (0.0, -spread)]
    for k in (0.0, 0.5, 1.0):
        for (ox, oy) in offs:
            u, v, d = project(cam, (p[0] + ox * k, p[1] + oy * k, p[2] + hgt * k))
            if d <= 0:
                continue
            for z in zones:
                if z(u, v):
                    return True
    return False


# --------------------------------------------------------------------------- build
def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.node_groups):
        for d in list(coll):
            coll.remove(d)


def setup_render(scene_name, cfg, preview, samples):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 50 if preview else 100
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = cfg['frames']
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.film_transparent = False
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.view_settings.look = 'None'
    except TypeError:
        pass
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.eevee.taa_render_samples = samples or (12 if preview else cfg.get('samples', 32))
    sc.eevee.use_shadows = True
    sc.eevee.shadow_resolution_scale = 1.0
    sc.eevee.use_raytracing = False
    sc.render.filter_size = 1.2
    w = bpy.data.worlds.new('W')
    sc.world = w
    w.color = (0, 0, 0)
    if w.node_tree is None:
        w.use_nodes = True
    for n in w.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs['Color'].default_value = (0, 0, 0, 1)
            n.inputs['Strength'].default_value = 0.0
    try:
        bpy.context.preferences.filepaths.use_scripts_auto_execute = True
    except Exception:
        pass


SCENES = {
    'welcome': dict(frames=168, gate_open=-93.0, gate_sag=0.0, wind=0.07, wind_freq=2 * math.pi * 2 / 7,
                    flowers=True, still=96),
    'sad': dict(frames=192, gate_open=0.0, gate_sag=0.0, wind=-0.13, wind_freq=2 * math.pi * 3 / 8,
                flowers=True, flower_k=0.5, still=180, env='smoothstep(6, 100, frame)'),
    'abandoned': dict(frames=192, gate_open=21.0, gate_sag=7.0, wind=0.10, wind_freq=2 * math.pi * 3 / 8,
                      flowers=False, overgrown=True, broken_rail=True, roof_hole=True, still=110),
    'note': dict(frames=168, gate_open=0.0, gate_sag=0.0, wind=0.05, wind_freq=2 * math.pi * 2 / 7,
                 flowers=True, flower_k=0.4, still=90, samples=40),
}


def build(scene_name, preview, samples):
    global TOON, ENV, LOOP_FRAMES
    cfg = SCENES[scene_name]
    P = MOODS[scene_name]
    ENV = cfg.get('env', '0')
    LOOP_FRAMES = cfg['frames']
    T = cfg['frames'] / FPS
    clear_scene()
    setup_render(scene_name, cfg, preview, samples)
    sc = bpy.context.scene

    # camera first: scatter placement uses its projection
    cam = make_camera('CamRanch')
    place_ranch_camera(cam)
    sc.camera = cam
    log('ranch camera', tuple(round(c, 3) for c in cam.location))

    TOON = build_toon_group(P)
    sun_dir = Vector(P['sun_dir']).normalized()

    M = {}
    M['ground'] = toon('M_ground', ground_material(P), rim=0.35)
    M['hill'] = toon('M_hill', '#6f9a58', rim=0.3, fog=1.0)
    M['hill2'] = toon('M_hill2', '#6d8f6e', rim=0.0, fog=1.35)
    M['hill3'] = toon('M_hill3', '#7a8f85', rim=0.0, fog=1.6)
    M['rail'] = toon('M_rail', island_tint('#9a6c44', '#7d5636', grain=0.25, grain_axis=(1.4, 55.0, 55.0)), rim=1.0)
    M['post'] = toon('M_post', island_tint('#7a5234', '#5f3f28', grain=0.16, grain_axis=(28.0, 28.0, 1.2)), rim=1.0)
    M['gpost'] = toon('M_gpost', island_tint('#7a5439', '#5e4130', grain=0.38, grain_axis=(70.0, 70.0, 1.6),
                                             noise_scale=4.0), rim=1.0)
    M['metal'] = toon('M_metal', '#3e3a38', rim=0.6)
    M['wall'] = toon('M_wall', barn_wall_color('#a24a37', '#8c3d2f'), rim=0.8)
    M['roof'] = toon('M_roof', island_tint('#5c3f38', '#4b332e'), rim=0.6)
    M['trim'] = toon('M_trim', '#efe2c9', rim=0.6)
    M['dark'] = toon('M_dark', '#2b201e', rim=0.0, ao=0.3)
    M['trunk'] = toon('M_trunk', island_tint('#6f4c33', '#5a3d29'), rim=0.8)
    M['leaves'] = toon('M_leaves', island_tint('#5e9a45', '#7fb251', noise_scale=1.2), rim=1.2)
    M['leaves_far'] = toon('M_leaves_far', island_tint('#5a8f48', '#6f9e52'), rim=0.6)
    M['rock'] = toon('M_rock', island_tint('#a19b90', '#8a857c', noise_scale=3.0), rim=0.8)
    M['grass'] = toon('M_grass', attr_gradient('h', '#6aa24a', '#c2e27f', 0.35, '#93c45a'), rim=0.7, ao=0.3)
    if scene_name == 'abandoned':
        M['grass'] = toon('M_grass_wet', attr_gradient('h', '#3d5a2c', '#7f9a4c', 0.45, '#8d8a4a'), rim=0.6, ao=0.5)
    M['weed'] = toon('M_weed', attr_gradient('h', '#3c5230', '#8c8e4f', 0.5, '#6f7a3c'), rim=0.6, ao=0.5)
    M['weedhead'] = toon('M_weedhead', '#a38d62', rim=0.5)
    M['stem'] = toon('M_stem', '#5b8a3d', rim=0.5, ao=0.4)
    M['petal'] = toon('M_petal', palette_by_random(['#f3ead8', '#f2b544', '#f4a7b0', '#c9b6e8', '#ffffff']), rim=0.8, emit=0.08)
    M['fcentre'] = toon('M_fcentre', '#e7a33a', rim=0.4)
    M['leaf'] = toon('M_leaf', palette_by_random(['#d9822f', '#c4632b', '#e0a63c', '#9a5a2e']), rim=1.0)
    M['leaf_ground'] = toon('M_leafg', palette_by_random(['#8a5a34', '#6f4a2c', '#9a6e3a']), rim=0.3)
    M['sky'] = sky_material(P, sun_dir)
    M['cloud'] = cloud_material(P, sun_dir, cam.location)

    build_ground(M['ground'])
    build_ridge('Ridge1', 95.0, 8.5, 5.0, 0.018, 3.0, M['hill2'])
    build_ridge('Ridge2', 160.0, 17.0, 8.0, 0.012, 8.0, M['hill3'])
    build_sky(M['sky'])

    # sun (strength pi so Shader-to-RGB reads ~1.0 on a surface facing it)
    ld = bpy.data.lights.new('Sun', 'SUN')
    ld.energy = math.pi
    ld.angle = math.radians(3.5)
    ld.use_shadow = True
    sun = bpy.data.objects.new('Sun', ld)
    sc.collection.objects.link(sun)
    sun.rotation_euler = (-sun_dir).to_track_quat('-Z', 'Y').to_euler()

    # set pieces
    build_fence([M['rail'], M['post']], cfg)
    build_gate([M['rail'], M['gpost'], M['metal']], cfg['gate_open'], cfg['gate_sag'])
    barn = build_barn([M['wall'], M['roof'], M['trim'], M['dark']], cfg)
    bx, by = -6.3, 11.5
    barn.location = (bx, by, terrain_h(bx, by) - 0.05)
    barn.rotation_euler = (0, 0, math.radians(30.0))
    build_tree('TreeA', (3.7, 3.6), 4.4, 1.75, 5, [M['trunk'], M['leaves']], sway=0.012)
    build_tree('TreeB', (8.5, 13.0), 5.6, 2.3, 6, [M['trunk'], M['leaves']], sway=0.008)
    build_tree('TreeC', (-11.5, 17.0), 5.0, 2.1, 7, [M['trunk'], M['leaves']], sway=0.008)
    rngt = random.Random(77)
    for i in range(26):
        x = rngt.uniform(-38, 38)
        y = rngt.uniform(26, 58)
        if abs(x - bx) < 6 and y < 20:
            continue
        build_tree(f'FarTree{i}', (x, y), rngt.uniform(3.5, 6.5), rngt.uniform(1.4, 2.6), 100 + i,
                   [M['trunk'], M['leaves_far']])

    zones_shared = ZONES['welcome'] + ZONES['sad'] + ZONES['abandoned']
    rocks = [((-1.55, -3.3), 0.26), ((1.75, -1.4), 0.2), ((-2.4, -0.9), 0.33), ((2.6, -6.4), 0.42),
             ((-2.6, -6.6), 0.36), ((1.25, 0.9), 0.18), ((-4.2, 2.2), 0.45), ((4.6, -2.8), 0.3)]
    for i, ((x, y), s) in enumerate(rocks):
        if blocked(cam, zones_shared, (x, y, terrain_h(x, y)), s):
            continue
        build_rock(f'Rock{i}', (x, y), s, 40 + i, M['rock'])

    # clouds
    rngc = random.Random(scene_name == 'welcome' and 3 or (5 if scene_name == 'sad' else 9))
    n_clouds = {'welcome': 5, 'sad': 10, 'abandoned': 14, 'note': 6}[scene_name]
    speed = {'welcome': 0.06, 'sad': 0.24, 'abandoned': 0.05, 'note': 0.04}[scene_name]
    for i in range(n_clouds):
        az = rngc.uniform(-0.75, 0.75)
        el = rngc.uniform(0.07, 0.42) if scene_name != 'abandoned' else rngc.uniform(0.05, 0.36)
        dist = rngc.uniform(230, 330)
        dvec = Vector((math.sin(az), math.cos(az), math.tan(el))).normalized()
        c = cam.location + dvec * dist
        size = rngc.uniform(28, 60) * (1.5 if scene_name == 'abandoned' else 1.0)
        if scene_name == 'sad' and i >= 5:
            c.x -= 70 + 40 * (i - 5)
            size *= 1.25
        ob = build_cloud(f'Cloud{i}', c, size, 200 + i, M['cloud'])
        if scene_name == 'sad':  # one-shot clip: clouds keep rolling in
            drive(ob, 'location', f'{c.x:.3f}+{speed:.4f}*frame', 0)
        else:  # looping clips: a slow sway that returns to its start on the last frame
            amp = speed * LOOP_FRAMES / (2 * math.pi)
            drive(ob, 'location', f'{c.x:.3f}+{amp:.3f}*sin(2*pi*frame/{LOOP_FRAMES}+{i * 0.9:.2f})', 0)

    # instance templates + scatter
    gn_scatter = build_gn_scatter()
    t_grass = [blade_tuft(f'grass{i}', 300 + i, 7, 0.10, 0.22, 0.036, 0.4, [M['grass']]) for i in range(3)]
    rng = random.Random(1234)
    scale_mul = 1.0
    grass_pts = [[], [], []]
    n_try = 14000 if not cfg.get('overgrown') else 20000
    for _ in range(n_try):
        x = rng.uniform(-14.0, 14.0)
        y = rng.uniform(-8.0, 22.0)
        if rng.random() > max(0.12, 1.0 - (y + 8.0) / 24.0):
            continue
        pd = path_dist(x, y)
        on_path_ok = cfg.get('overgrown') and rng.random() < 0.25
        if pd < 0.05 and not on_path_ok:
            continue
        if abs(x - bx) < 4.2 and abs(y - by) < 4.2:
            continue
        z = terrain_h(x, y)
        s = rng.uniform(0.75, 1.3)
        if blocked(cam, zones_shared, (x, y, z), 0.3 * s):
            continue
        grass_pts[rng.randrange(3)].append((x, y, z, rng.uniform(0, 6.28), s, rng.uniform(0, 6.28)))
    if cfg.get('overgrown'):
        scale_mul = 1.35
    for i in range(3):
        scatter_object(f'Grass{i}', grass_pts[i], gn_scatter, t_grass[i], cfg['wind'], cfg['wind_freq'], scale_mul)
    log('grass tufts', sum(len(g) for g in grass_pts))

    if cfg.get('flowers'):
        t_fl = [flower_tuft(f'flower{i}', 400 + i, [M['stem'], M['petal'], M['fcentre']]) for i in range(2)]
        fl_pts = [[], []]
        k = cfg.get('flower_k', 1.0)
        clusters = [(-1.45, -0.55), (1.5, -0.5), (-2.3, -2.6), (2.1, -3.8), (-3.4, -5.2), (3.2, 1.4), (-2.0, 1.6),
                    (3.0, -6.0), (-1.9, -7.2)]
        for (cx, cy) in clusters:
            for _ in range(int(16 * k)):
                x = cx + rng.gauss(0, 0.45)
                y = cy + rng.gauss(0, 0.35)
                if path_dist(x, y) < 0.08:
                    continue
                z = terrain_h(x, y)
                if blocked(cam, zones_shared, (x, y, z), 0.25):
                    continue
                fl_pts[rng.randrange(2)].append((x, y, z, rng.uniform(0, 6.28), rng.uniform(1.3, 1.8), rng.uniform(0, 6.28)))
        for _ in range(int(160 * k)):
            x = rng.uniform(-9, 9)
            y = rng.uniform(-6, 14)
            if path_dist(x, y) < 0.1:
                continue
            z = terrain_h(x, y)
            if blocked(cam, zones_shared, (x, y, z), 0.25):
                continue
            fl_pts[rng.randrange(2)].append((x, y, z, rng.uniform(0, 6.28), rng.uniform(1.1, 1.6), rng.uniform(0, 6.28)))
        for i in range(2):
            scatter_object(f'Flowers{i}', fl_pts[i], gn_scatter, t_fl[i], cfg['wind'], cfg['wind_freq'])

    if cfg.get('overgrown'):
        t_weed = [blade_tuft(f'weed{i}', 500 + i, 8, 0.26, 0.58, 0.04, 0.5, [M['weed'], M['weedhead']], segs=3,
                             heads=2 if i else 0, head_r=0.011) for i in range(3)]
        wz = ZONES['abandoned']
        w_pts = [[], [], []]
        for _ in range(3600):
            r = rng.random()
            s = rng.uniform(0.7, 1.2)
            if r < 0.55:   # along the fence line
                x = rng.uniform(-13, 13)
                y = rng.gauss(0.08, 0.38)
            elif r < 0.85:  # path edges, smaller near the camera
                y = rng.uniform(-6.5, 6.0)
                side = 1 if rng.random() < 0.5 else -1
                x = path_cx(y) + side * (path_hw(y) + abs(rng.gauss(0.1, 0.35)))
                if y < -3.5:
                    s *= 0.55
            else:
                x = rng.uniform(-12, 12)
                y = rng.uniform(-3, 14)
            if abs(x - bx) < 3.6 and abs(y - by) < 3.6:
                continue
            if abs(x) < 0.7 and -0.2 < y < 0.25:
                continue
            z = terrain_h(x, y)
            if blocked(cam, wz, (x, y, z), 0.6 * s, spread=0.3 * s):
                continue
            w_pts[rng.randrange(3)].append((x, y, z, rng.uniform(0, 6.28), s, rng.uniform(0, 6.28)))
        for i in range(3):
            scatter_object(f'Weeds{i}', w_pts[i], gn_scatter, t_weed[i], cfg['wind'] * 1.2, cfg['wind_freq'])
        log('weeds', sum(len(g) for g in w_pts))

    if scene_name in ('sad', 'abandoned'):
        t_lg = leaf_template('leafground', [M['leaf_ground']], 0.075)
        lg = []
        n_leaves = 160 if scene_name == 'abandoned' else 60
        for _ in range(n_leaves * 3):
            x = rng.uniform(-6, 6)
            y = rng.uniform(-7.5, 4)
            z = terrain_h(x, y) + 0.01
            if len(lg) >= n_leaves:
                break
            lg.append((x, y, z, rng.uniform(0, 6.28), rng.uniform(0.8, 1.3), 0.0))
        scatter_object('GroundLeaves', lg, gn_scatter, t_lg, 0.0, 0.0)

    # --------------------------------------------------------------- per-scene extras
    gn_particles = build_gn_particles()
    if scene_name == 'welcome':
        pol = emission_mat('M_pollen', lin('#ffdf96'), 1.25)[0]
        bm = bmesh.new()
        add_ico(bm, Vector((0, 0, 0)), 0.011, subdiv=1)
        t_pol = template('pollen', bm, [pol], smooth=True)
        particles_object('Pollen', gn_particles, t_pol, Count=170, BoxMin=(-5.0, -6.5, 0.15), BoxMax=(5.0, 9.0, 2.25),
                         Velocity=(0.0, 0.0, 2.1 / T), Seed=5, Sway=0.35, SwayFreq=2 * math.pi * 2 / T,
                         ScaleMin=0.6, ScaleMax=1.5, Fade=0.15)
        build_butterflies(M, T)
    if scene_name == 'sad':
        t_leaf = leaf_template('leaf', [M['leaf']], 0.11)
        particles_object('Leaves', gn_particles, t_leaf, Count=40, BoxMin=(-5.0, -6.0, -0.3), BoxMax=(6.0, 4.0, 4.2),
                         Velocity=(-0.95, -0.12, -0.42), Seed=8, Sway=0.3, SwayFreq=2.4, Tumble=1.0, Spin=3.0,
                         ScaleMin=1.0, ScaleMax=1.6, Fade=0.06)
    if scene_name == 'abandoned':
        build_rain(M, P, gn_particles, T)
        build_puddles(cam, P, T)
        build_bowl(cam, M)
        build_mist(P, T)
    if scene_name == 'note':
        cam2 = build_note_shot(M, P, T)
        sc.camera = cam2

    report_anchors(scene_name, sc.camera)
    return sc


def barn_wall_color(ha, hb):
    def f(nb):
        tc = nb.new('ShaderNodeTexCoord')
        ox, oy, _oz = nb.sep(tc.outputs['Object'])
        nx, ny, _nz = nb.sep(tc.outputs['Normal'])
        coord = nb.math('ADD', nb.math('MULTIPLY', ox, nb.math('ABSOLUTE', ny)), nb.math('MULTIPLY', oy, nb.math('ABSOLUTE', nx)))
        fr = nb.math('FRACT', nb.math('MULTIPLY', coord, 3.4))
        line = nb.math('MULTIPLY', nb.smooth(fr, 0.0, 0.06), nb.smooth(fr, 1.0, 0.94))
        n = nb.noise(tc.outputs['Object'], 1.5, 2.0)
        c = nb.mix(n, lin(ha), lin(hb))
        return nb.vmath('SCALE', c, scale=nb.math('MULTIPLY_ADD', line, 0.16, 0.84))
    return f


def build_butterflies(M, T):
    wing = toon('M_wing', palette_by_random(['#f2b544', '#f3ead8']), rim=1.0, emit=0.12)
    body = toon('M_bbody', '#3a2c26', rim=0.3)
    for i, (cx, cy, cz, seed) in enumerate(((-2.05, -2.7, 0.55, 1), (2.55, 0.4, 0.95, 2))):
        root = bpy.data.objects.new(f'Fly{i}', None)
        bpy.context.scene.collection.objects.link(root)
        u = f'(2*pi*frame/{LOOP_FRAMES})'
        ph = seed * 1.3
        drive(root, 'location', f'{cx}+0.55*sin({u}*2+{ph})', 0)
        drive(root, 'location', f'{cy}+0.35*sin({u}*4+{ph})', 1)
        drive(root, 'location', f'{cz}+0.14*sin({u}*6+{ph}+1)', 2)
        drive(root, 'rotation_euler', f'atan2(0.35*4*cos({u}*4+{ph}), 0.55*2*cos({u}*2+{ph}))-pi/2', 2)
        bm = bmesh.new()
        add_ico(bm, Vector((0, 0, 0)), 0.006, subdiv=1, scale=(1, 3.2, 1))
        b = link_obj(f'FlyBody{i}', mesh_from_bm(f'flybody{i}', bm, [body]))
        b.parent = root
        flap = f'0.25+1.05*abs(sin(2*pi*frame/{LOOP_FRAMES}*24))'
        for side in (-1, 1):
            bm = bmesh.new()
            pts = [(0, 0.012, 0), (side * 0.034, 0.024, 0), (side * 0.03, -0.002, 0), (0, -0.004, 0)]
            vs = [bm.verts.new(p) for p in pts]
            bm.faces.new(vs if side > 0 else list(reversed(vs)))
            pts2 = [(0, -0.002, 0), (side * 0.026, -0.006, 0), (side * 0.018, -0.026, 0), (0, -0.014, 0)]
            vs2 = [bm.verts.new(p) for p in pts2]
            bm.faces.new(vs2 if side > 0 else list(reversed(vs2)))
            w = link_obj(f'FlyWing{i}{side}', mesh_from_bm(f'flywing{i}{side}', bm, [wing]))
            w.parent = root
            drive(w, 'rotation_euler', f'{-side}*({flap})', 1)
            w.visible_shadow = False


def build_rain(M, P, gn, T):
    rm = rain_material(P)
    vel = Vector((2.0, 0.0, -8.0))
    bm = bmesh.new()
    axis = vel.normalized()
    rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=rot @ Matrix.Diagonal((0.0045, 0.0045, 0.30, 1.0)))
    _ = r
    t_rain = template('rain', bm, [rm])
    t_rain.visible_shadow = False
    particles_object('Rain', gn, t_rain, Count=2000, BoxMin=(-8.0, -8.5, -1.0), BoxMax=(8.0, 18.0, 7.0),
                     Velocity=(2.0, 0.0, -8.0), Seed=13, Sway=0.0, ScaleMin=0.7, ScaleMax=1.25, Fade=0.02)


def build_puddles(cam, P, T):
    mat = puddle_material(P, 'frame/24')
    rng = random.Random(55)
    spots = [((0.27, 0.90), 0.30), ((0.75, 0.885), 0.26), ((0.31, 0.63), 0.30), ((0.64, 0.585), 0.24),
             ((0.82, 0.70), 0.24)]
    for i, ((u, v), r) in enumerate(spots):
        p = screen_to_ground(cam, u, v)
        bm = bmesh.new()
        n = 22
        centre = bm.verts.new((0, 0, 0))
        ring = []
        for k in range(n):
            a = k * 2 * math.pi / n
            rr = r * (1.0 + 0.22 * math.sin(3 * a + i) + 0.12 * math.sin(5 * a + 2 * i)) * (1.0 + rng.uniform(-0.05, 0.05))
            ring.append(bm.verts.new((math.cos(a) * rr * 1.25, math.sin(a) * rr * 0.85, 0)))
        for k in range(n):
            bm.faces.new((centre, ring[k], ring[(k + 1) % n]))
        bm.verts.index_update()
        edge = [0.0] + [1.0] * n
        me = mesh_from_bm(f'puddle{i}', bm, [mat], smooth=True)
        a = me.attributes.new('edge', 'FLOAT', 'POINT')
        a.data.foreach_set('value', edge)
        ob = link_obj(f'Puddle{i}', me)
        ob.location = (p.x, p.y, terrain_h(p.x, p.y) + 0.035)
        ob.rotation_euler = (0, 0, rng.uniform(-0.4, 0.4))
        ob.visible_shadow = False


def build_bowl(cam, M):
    mat = toon('M_bowl', '#d0743f', rim=1.0, emit=0.12)
    inner = toon('M_bowl_in', '#b0714b', rim=0.4, emit=0.06)
    p = screen_to_ground(cam, 0.40, 0.765)
    bm = bmesh.new()
    prof = [(0.0, 0.0), (0.072, 0.0), (0.082, 0.014), (0.112, 0.024), (0.148, 0.072), (0.168, 0.118),
            (0.176, 0.13), (0.163, 0.132), (0.15, 0.108), (0.115, 0.05), (0.0, 0.04)]
    segs = 18
    rings = []
    for (r, z) in prof:
        rings.append([bm.verts.new((math.cos(k * 2 * math.pi / segs) * r, math.sin(k * 2 * math.pi / segs) * r, z))
                      for k in range(segs)])
    for j in range(len(prof) - 1):
        for k in range(segs):
            f = bm.faces.new((rings[j][k], rings[j][(k + 1) % segs], rings[j + 1][(k + 1) % segs], rings[j + 1][k]))
            f.material_index = 0 if j < 7 else 1
    me = mesh_from_bm('bowl', bm, [mat, inner])
    ob = link_obj('Bowl', me)
    # tipped on its side, opening toward the camera and the monster spot on its right
    rot = Euler((math.radians(76), math.radians(-5), math.radians(74)), 'XYZ')
    sc = 1.15
    mw = rot.to_matrix().to_4x4() @ Matrix.Diagonal((sc, sc, sc, 1.0))
    low = min((mw @ v.co).z for v in me.vertices)
    ob.scale = (sc, sc, sc)
    ob.rotation_euler = rot
    ob.location = (p.x, p.y, terrain_h(p.x, p.y) - low - 0.012)  # rests on (slightly in) the mud
    log('bowl at', tuple(round(c, 2) for c in ob.location))


def build_mist(P, T):
    mat = mist_material(P)
    for i, (y, h, x0) in enumerate(((1.2, 1.3, 0.0), (5.5, 1.7, 3.0), (11.0, 2.4, -2.0), (-3.5, 0.9, 1.0))):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0,
                              matrix=Matrix.Diagonal((16.0, h / 2, 1.0, 1.0)))
        me = mesh_from_bm(f'mist{i}', bm, [mat], smooth=True)
        ob = link_obj(f'Mist{i}', me)
        ob.rotation_euler = (math.radians(90), 0, 0)
        ob.location = (x0, y, terrain_h(0, y) + h / 2 - 0.25)
        ob.visible_shadow = False
        drive(ob, 'location', f'{x0}+0.9*sin(2*pi*frame/{LOOP_FRAMES}+{i * 1.7:.2f})', 0)


def build_note_shot(M, P, T):
    """Close-up of the right gate post with a pinned paper note and dripping rails."""
    sc = bpy.context.scene
    gx = 0.86
    g = terrain_h(gx, 0.0)
    face_y = -0.085 - 0.002
    note_top = g + 1.255
    W, H = 0.152, 0.19
    # paper: grid with a soft vertical fold and a curled corner
    paper = toon('M_paper', '#fbf6ec', rim=1.0, emit=0.2, ao=0.4)
    bm = bmesh.new()
    nxs, nzs = 8, 10
    grid = []
    for j in range(nzs + 1):
        row = []
        for i in range(nxs + 1):
            x = -W / 2 + W * i / nxs
            z = -H * j / nzs
            # pressed flat at the pin, the two halves of the old fold spring away from the post
            fold = 0.003 + 0.013 * (abs(x) / (W / 2)) ** 1.5 * smoothstep(0.0, 0.06, -z)
            crease_h = 0.005 * (1.0 - min(abs(z + H * 0.5) / (H * 0.12), 1.0)) * smoothstep(0.0, 0.05, abs(x))
            curl = 0.020 * max(0.0, (x / (W / 2))) ** 2 * max(0.0, (-z / H - 0.6) / 0.4) ** 2
            row.append(bm.verts.new((x, -fold - crease_h - curl, z)))
        grid.append(row)
    for j in range(nzs):
        for i in range(nxs):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    me = mesh_from_bm('note', bm, [paper])
    note = link_obj('Note', me)
    note.location = (gx + 0.006, face_y - 0.004, note_top)
    mod = note.modifiers.new('Flutter', 'NODES')
    gnf = build_gn_flutter()
    mod.node_group = gnf
    set_inputs(mod, gnf, Freq=2 * math.pi * 6 / T, Height=H)
    amp_expr = '0.30+0.85*smoothstep(36, 60, frame)*(1-smoothstep(110, 132, frame))'
    drive(note, input_path('Flutter', gnf, 'Amp'), amp_expr)
    drive(note, 'rotation_euler', f'0.05*({amp_expr})*sin(2*pi*frame/{LOOP_FRAMES}*4+0.4)', 1)
    # nail
    nail_m = toon('M_nail', '#6d6a68', rim=1.4)
    bm = bmesh.new()
    add_cone(bm, (0, 0, 0), 0.0068, 0.0058, 0.004, segs=8, rot=(math.pi / 2, 0, 0))
    add_cone(bm, (0, 0, 0), 0.0022, 0.0022, 0.04, segs=6, rot=(-math.pi / 2, 0, 0))
    nail = link_obj('Nail', mesh_from_bm('nail', bm, [nail_m]))
    nail.location = (gx + 0.006, face_y - 0.0085, note_top - 0.018)

    # water beads + drips under the top rails near the post
    drop_m = water_drop_material()
    bm = bmesh.new()
    add_ico(bm, Vector((0, 0, -0.008)), 0.0095, subdiv=2, scale=(1, 1, 1.25))
    t_drop = template('drop', bm, [drop_m], smooth=True)
    t_drop.visible_shadow = False
    pts = []
    rng = random.Random(91)
    periods = [1.75, 7 / 3, 3.5, 1.4, 7 / 4, 7 / 3, 3.5]
    for i, x in enumerate((0.52, 0.63, 0.71, 1.00, 1.09, 1.24, 0.40)):
        zr = (g + 0.90 - 0.057) if x > gx else (terrain_h(-0.86, 0.0) + 1.02 - 0.86 + 0.80 - 0.06)
        yr = -0.085 if x > gx else 0.0
        pts.append((x, yr, zr, periods[i], rng.uniform(0, 3.5)))
    me = bpy.data.meshes.new('drips')
    me.from_pydata([(p[0], p[1], p[2]) for p in pts], [], [])
    for idx, an in ((3, 'period'), (4, 'phase')):
        a = me.attributes.new(an, 'FLOAT', 'POINT')
        a.data.foreach_set('value', [p[idx] for p in pts])
    dob = link_obj('Drips', me)
    dob.visible_shadow = False
    mod = dob.modifiers.new('Drips', 'NODES')
    gnd = build_gn_drips()
    mod.node_group = gnd
    set_inputs(mod, gnd, Instance=t_drop)
    # static beads along the rail undersides
    bm = bmesh.new()
    for k in range(26):
        x = rng.uniform(0.0, 1.6)
        if abs(x - gx) < 0.1:
            continue
        zr = (g + 0.90 - 0.057) if x > gx else (terrain_h(-0.86, 0.0) + 1.02 - 0.86 + 0.80 - 0.06)
        yr = -0.085 if x > gx else 0.0
        add_ico(bm, Vector((x, yr + rng.uniform(-0.012, 0.012), zr - 0.004)), rng.uniform(0.003, 0.0055), subdiv=1,
                scale=(1, 1, 1.2))
    beads = link_obj('Beads', mesh_from_bm('beads', bm, [drop_m], smooth=True))
    beads.visible_shadow = False

    cam = make_camera('CamNote')
    cam.data.lens = 35.0
    target = Vector((gx, face_y, note_top - H / 2))
    cam.location = target + Vector((0.40, -1.34, -0.12))
    d = (target - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (target - cam.location).length
    cam.data.dof.aperture_fstop = 2.2
    sc.camera = cam
    bpy.context.view_layer.update()
    # shift so the note centre lands at x 55 %, y 45 %
    for _ in range(4):
        u, v, _d = project(cam, target)
        cam.data.shift_x -= (0.55 - u) * 0.75
        cam.data.shift_y += (0.45 - v) * 1.0
        bpy.context.view_layer.update()
    u, v, _d = project(cam, target)
    ul, _vl, _ = project(cam, target + Vector((-W / 2, 0, 0)))
    ur, _vr, _ = project(cam, target + Vector((W / 2, 0, 0)))
    log(f'note centre at u={u:.3f} v={v:.3f}, width {100 * (ur - ul):.1f}% of frame')
    return cam


def report_anchors(scene_name, cam):
    if scene_name == 'note':
        return
    pts = {'gate base (0,-0.3)': Vector((0, -0.3, terrain_h(0, -0.3)))}
    for nm, (u, v) in (('welcome start', (0.5, 0.58)), ('welcome end', (0.5, 0.84)), ('sad', (0.58, 0.68)),
                       ('abandoned', (0.52, 0.74)), ('bowl', (0.40, 0.765))):
        g = screen_to_ground(cam, u, v)
        uu, vv, _ = project(cam, g)
        log(f'anchor {nm}: screen ({u:.2f},{v:.2f}) -> ground ({g.x:.2f},{g.y:.2f},{g.z:.2f}) check ({uu:.3f},{vv:.3f})')
    for nm, p in pts.items():
        u, v, _ = project(cam, p)
        log(f'{nm}: ({u:.3f},{v:.3f})')


# --------------------------------------------------------------------------- render
def render(scene_name, preview, frames, outdir):
    sc = bpy.context.scene
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.endswith('.png'):
            os.remove(os.path.join(outdir, f))
    n = sc.frame_end
    if frames:
        todo = frames
    elif preview:
        todo = [round(1 + i * (n - 1) / 7) for i in range(8)]
    else:
        todo = None
    t0 = time.time()
    if todo is None:
        sc.render.filepath = os.path.join(outdir, 'f_')
        bpy.ops.render.render(animation=True)
    else:
        for fr in todo:
            t1 = time.time()
            sc.frame_set(fr)
            sc.render.filepath = os.path.join(outdir, f'f_{fr:04d}.png')
            bpy.ops.render.render(write_still=True)
            log(f'frame {fr}: {time.time() - t1:.1f}s')
    log(f'{scene_name}: rendered in {time.time() - t0:.1f}s -> {outdir}')


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--scene', required=True, choices=list(SCENES) + ['all'])
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--frames', default='')
    ap.add_argument('--samples', type=int, default=0)
    ap.add_argument('--save-blend', action='store_true')
    args = ap.parse_args(argv)
    log('Blender', bpy.app.version_string)
    names = list(SCENES) if args.scene == 'all' else [args.scene]
    frames = [int(f) for f in args.frames.split(',') if f.strip()] if args.frames else None
    for nm in names:
        t0 = time.time()
        build(nm, args.preview, args.samples)
        log(f'{nm}: built in {time.time() - t0:.1f}s')
        outdir = os.path.join(OUT_ROOT, nm + ('-preview' if args.preview or frames else ''))
        if args.save_blend:
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_ROOT, nm + '.blend'))
        render(nm, args.preview, frames, outdir)


if __name__ == '__main__':
    main()
