"""The Breeders' Guild arena by the river in Tunewick (ART_2_PLAN §7.3, CONTENT §1): the first 3D battle arena.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/arenas/guild.py -- [--stages build,bake,export,review] [--quick]

build   the scene in metres, Z-up (the ring floor at z = 0, centred on the origin, the inner fence line at r = 6.0):
        the packed-earth ring and its low earth rim, rope-fence posts with sagging hessian ropes and two gates on the
        A–B axis (x), stepped wooden stands (their crowd is the game's, at the exported seats), banner poles carrying the Guild emblem, bunting,
        Poly Haven CC0 props, the river, Tunewick (plaster, timber-frame and thatch houses, a bridge, a mill, the
        Shrine on its hill), stylised trees and grass, and far mountains for the sky panorama; saves guild_src.blend
bake    per atlas group: join, unwrap, then Cycles bakes albedo (full size) and diffuse light (direct + indirect, half
        size, smoothed) and multiplies them into one lit-colour atlas (the arena ships unlit, lighting baked in);
        renders the sky panoramas (full: sky + mountains; Lite: everything beyond the arena too); builds the domes;
        saves guild_baked.blend
export  the game meshes (one per atlas = one draw call each), the anchors (ring_center, spawn_A/B, gate_A/B and their
        walk-in starts, cam_fly_0…N, the review cameras) → guild_raw.glb and guild_lite_raw.glb, plus guild_build.json
review  Cycles beauty renders of the source scene (battle side-on, over A's shoulder, establishing) and of the shipped
        Lite version, each with grey 1 m capsule stand-ins at the spawns → art-review/arena-guild/

Everything lands in tools/blender/out/arena-guild/ (gitignored); `node tools/blender/arenas/guild.ts` turns it into
public/models/arenas/guild/. Every number below is the arena's own data (it has no runtime rules).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # tools/blender → `lib`
sys.path.insert(0, str(HERE))               # tools/blender/arenas → kit, emblem

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from lib import common as C  # noqa: E402
from lib.nodes import NB, new_image, new_mat  # noqa: E402
import kit as K  # noqa: E402
from emblem import emblem_alpha  # noqa: E402

OUT = C.OUT_ROOT / 'arena-guild'
REVIEW = C.ROOT / 'art-review' / 'arena-guild'

# ----------------------------------------------------------------------------- the interface the battle code reads
RING_R = 6.0                    # the inner fence line; everything inside is flat (z = 0) and clear
SPAWN_X = 2.4
GATE_HALF = 1.05                # half the gate opening (m)
POST_R = 6.24                   # post centres
ROPE_R = 6.12                   # the ropes run along the posts' inner faces
SUN_DIR = Vector((-0.42, -0.58, 0.70)).normalized()     # toward the sun: front-left of the battle camera, ~44° up

# Guild palette (sRGB)
TEAL, TEAL_D, CORAL, CREAM, GOLD, PLUM = '#2E8F86', '#1E6A64', '#E2694F', '#F3E4C3', '#E7B24C', '#8061A8'
SKY_HAZE = '#B4CBE6'

# Atlas groups: name → (size, double-sided). One mesh, one material, one texture each in the game.
GROUPS = {
    'ring': (2048, False), 'timber': (2048, True), 'props': (2048, True), 'crowd': (2048, True),
    'apron': (2048, False), 'mid': (2048, False), 'far': (1024, False), 'town': (2048, True),
    'trees': (2048, True), 'water': (2048, False),
}
APRON_R = (6.9, 17.0)           # the near ground ring (planar UV over ±17 m)
MID_R = 52.0                    # mid ground out to here (planar UV over ±52 m), far ground beyond
FAR_R = 210.0
WATER_Z = -0.62

# ----------------------------------------------------------------------------- small maths
def ss(a, b, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def river_y(x):
    return 22.0 + 2.6 * np.sin(np.asarray(x) / 23.0 + 0.4)


def terrain_h(x, y):
    """Ground height (m). Flat (0) inside r < 12.5 so the ring, stands and gate paths sit level."""
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    r = np.hypot(x, y)
    th = np.arctan2(y, x)
    h = ss(12.5, 26.0, r) * (0.32 * np.sin(x * 0.13 + 1.3) * np.cos(y * 0.11) + 0.18 * np.sin(x * 0.29 + y * 0.17 + 0.6))
    h = h + ss(26.0, 120.0, y) * np.clip(y - 26.0, 0.0, 70.0) * 0.08                 # the town's hillside (+Y)
    h = h + 9.0 * np.exp(-((x - 18.0) ** 2 + (y - 104.0) ** 2) / (2 * 22.0 ** 2))    # the Shrine's hill
    h = h + ss(-20.0, -90.0, y) * np.minimum(-y - 20.0, 70.0) * 0.05               # a gentle rise behind the camera
    h = h + ss(120.0, 200.0, r) * (5.0 + 3.0 * np.sin(th * 3.0 + 0.5) + 2.0 * np.sin(th * 7.0 + 1.1))
    d = np.abs(y - river_y(x))
    h = h * ss(3.5, 9.0, d) - 1.45 * (1.0 - ss(2.6, 6.2, d))                       # the river channel
    return h


# ----------------------------------------------------------------------------- scene setup
def setup_scene(quick: bool) -> None:
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.unit_settings.system = 'METRIC'
    sc.cycles.samples = 32 if quick else 128
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.sample_clamp_indirect = 6.0
    try:
        sc.view_settings.view_transform = 'Khronos PBR Neutral'
    except TypeError:
        sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0


def hdri_sun_azimuth(img: bpy.types.Image) -> tuple[float, float]:
    """Azimuth/elevation (radians, Blender world) of the brightest pixel of an equirectangular HDRI."""
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    lumi = px[..., 0] * 0.2126 + px[..., 1] * 0.7152 + px[..., 2] * 0.0722
    j, i = np.unravel_index(np.argmax(lumi), lumi.shape)          # j = row from the bottom
    u, v = (i + 0.5) / w, (j + 0.5) / h
    return -2 * math.pi * u, (v - 0.5) * math.pi        # Blender's equirect: u = atan2(y, -x)/2pi + 0.5


def setup_world() -> dict:
    hdr = next((K.CACHE / 'hdris' / 'kloofendal_48d_partly_cloudy_puresky').glob('*.hdr'))
    img = bpy.data.images.load(str(hdr), check_existing=True)
    az_sun, el_sun = hdri_sun_azimuth(img)
    want = math.atan2(SUN_DIR.y, SUN_DIR.x)
    rot = want - az_sun
    w = bpy.data.worlds.new('ArenaWorld')
    bpy.context.scene.world = w
    if w.node_tree is None:
        w.use_nodes = True
    nb = NB(w.node_tree)
    w.node_tree.nodes.clear()
    tc = nb.new('ShaderNodeTexCoord')
    mp = nb.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, rot)
    nb.link(tc.outputs['Generated'], mp.inputs['Vector'])
    env = nb.new('ShaderNodeTexEnvironment', image=img)
    nb.link(mp.outputs[0], env.inputs['Vector'])
    # the HDRI's own sun is clipped out (our sun lamp gives the key); the sky keeps its clouds and colour
    clip = nb.mix(1.0, env.outputs['Color'], (3.0, 3.0, 3.0, 1.0), blend='DARKEN')
    bg = nb.new('ShaderNodeBackground')
    nb.put(bg.inputs['Color'], clip)
    bg.inputs['Strength'].default_value = 1.3       # a bright sky fill: soft, cool, never black shadows (ART_2_PLAN §2.2)
    out = nb.new('ShaderNodeOutputWorld')
    nb.link(bg.outputs[0], out.inputs['Surface'])
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 3.7
    sun.angle = math.radians(4.0)
    sun.color = (1.0, 0.94, 0.84)
    so = bpy.data.objects.new('Sun', sun)
    bpy.context.scene.collection.objects.link(so)
    so.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
    C.log(f'HDRI sun at az {math.degrees(az_sun):.0f}° el {math.degrees(el_sun):.0f}°, rotated {math.degrees(rot):.0f}°')
    return {'hdri_rot': rot}


def coll(name: str) -> bpy.types.Collection:
    return C.collection(name)


def gcoll(group: str) -> bpy.types.Collection:
    return coll('G_' + group)


def tag(ob: bpy.types.Object, near: bool = False, lite: bool = True) -> bpy.types.Object:
    """Face flags carried through the joins: `near` (the camera-side fence the battle camera may hide) and `lite`
    (kept in the Lite version)."""
    me = ob.data
    for name, val in (('near', near), ('lite', lite)):
        a = me.attributes.get(name) or me.attributes.new(name, 'INT', 'FACE')
        a.data.foreach_set('value', np.full(len(me.polygons), int(val), np.int32))
    return ob


# ----------------------------------------------------------------------------- materials
class Mats:
    def __init__(self):
        self.emblem = self._emblem_image()
        self.floor = self._floor()
        self.berm = K.photo_mat('berm', 'dry_ground_rocks', 1.8, proj='BOX', sat=0.9, val=1.0, tint=C.srgb('#B08A5E'), tint_mix=0.2)
        self.post = K.photo_mat('post_wood', 'rough_wood', 1.2, sat=0.95, val=0.95, tint=C.srgb('#8C6A4A'), tint_mix=0.32, contrast=-0.05)
        self.plank = K.photo_mat('plank_wood', 'weathered_planks', 1.6, sat=1.05, val=1.05, tint=C.srgb('#A57A4F'), tint_mix=0.3)
        self.plank_paint = K.photo_mat('plank_paint', 'weathered_planks', 1.6, sat=0.9, val=1.1, tint=C.srgb(TEAL), tint_mix=0.62, vcol=True, vcol_mix=1.0)
        self.rope = self._rope()
        self.stone = K.photo_mat('rim_stone', 'rock_boulder_dry', 0.9, proj='BOX', sat=0.8, val=1.0, tint=C.srgb('#B9AE9C'), tint_mix=0.25)
        self.river_stone = K.photo_mat('river_stone', 'mossy_rock', 1.2, proj='BOX', sat=0.9, tint=C.srgb('#7F8C6E'), tint_mix=0.2)
        self.gold = K.flat_mat('gold', GOLD, 0.35)
        self.iron = K.flat_mat('iron', '#3B3A3C', 0.45)
        self.cloth = K.flat_mat('crowd_cloth', CREAM, 0.8, vcol=True, linen=0.5)
        self.skin = K.flat_mat('crowd_skin', CREAM, 0.6, vcol=True)
        self.banner = {c: self._banner(c, b) for c, b in (('teal', (TEAL, CREAM)), ('coral', (CORAL, CREAM)))}
        self.sign = self._banner('sign', (TEAL_D, CREAM), wood=True)
        self.grass_ground = self._ground()
        self.plaster = K.photo_mat('plaster', 'white_plaster_rough_01', 2.2, proj='BOX', sat=0.45, val=1.45, vcol=True, vcol_mix=1.0)
        self.beam = K.photo_mat('beam', 'rough_wood', 1.5, sat=0.9, val=0.7, tint=C.srgb('#5A4232'), tint_mix=0.45)
        self.thatch = K.photo_mat('thatch', 'thatch_roof_angled', 2.0, proj='BOX', sat=1.1, val=1.15, tint=C.srgb('#D9B36C'), tint_mix=0.38)
        self.cobble = K.photo_mat('cobble', 'cobblestone_floor_01', 2.0, proj='BOX', sat=0.8, tint=C.srgb('#A99A86'), tint_mix=0.2)
        self.window = K.flat_mat('window', '#2D3A44', 0.25)
        self.shutter = K.flat_mat('shutter', '#FFFFFF', 0.7, vcol=True)
        self.bark = K.photo_mat('bark', 'bark_brown_02', 1.2, proj='BOX', sat=0.9, val=0.9, tint=C.srgb('#6E5440'), tint_mix=0.3)
        self.leaf = self._leaves()
        self.grass_blade = self._blades()
        self.flowers = K.flat_mat('flowers', '#FFFFFF', 0.6, vcol=True)
        self.water = self._water()
        self.mountain = self._mountain()

    def _emblem_image(self) -> bpy.types.Image:
        a = emblem_alpha(1024)
        img = bpy.data.images.new('guild_emblem', 1024, 1024, alpha=True)
        img.colorspace_settings.name = 'Non-Color'
        rgba = np.stack([a, a, a, np.ones_like(a)], -1)[::-1]
        img.pixels.foreach_set(np.ascontiguousarray(rgba, np.float32).ravel())
        img.pack()
        return img

    def _emblem_mask(self, nb: NB, uv_vec):
        t = nb.new('ShaderNodeTexImage', image=self.emblem, interpolation='Linear')
        t.extension = 'CLIP'
        nb.put(t.inputs['Vector'], uv_vec)
        return t.outputs['Color']

    def _floor(self) -> bpy.types.Material:
        """Packed earth: the warm worn centre, pebbly darker edges, scuffs, chalk spawn marks and a faded emblem."""
        m, nb = new_mat('ring_floor')
        tc = nb.new('ShaderNodeTexCoord')
        obj = tc.outputs['Object']
        xyz = nb.sep(obj)
        r = nb.vmath('LENGTH', nb.comb(xyz[0], xyz[1], 0.0))
        v1 = K.coords(nb, 'Object', 2.3)
        d1, _ = K.tex_nodes(nb, 'dirt_floor', v1, 'FLAT', normal=False)
        v2 = K.coords(nb, 'Object', 2.0, 0.7)
        d2, _ = K.tex_nodes(nb, 'dry_ground_rocks', v2, 'FLAT', normal=False)
        c1 = K.grade(nb, d1.outputs['Color'], 0.5, 1.08, 1.08, C.srgb('#D6A86E'), 0.14, 0.04)
        c2 = K.grade(nb, d2.outputs['Color'], 0.5, 0.85, 0.95, C.srgb('#A9845B'), 0.25, -0.05)
        n1 = nb.noise(obj, 0.6, 3.0, 0.55)
        edge = nb.smooth(nb.math('ADD', r, nb.math('MULTIPLY', nb.math('SUBTRACT', n1, 0.5), 1.6)), 4.3, 6.1)
        col = nb.mix(edge, c1, c2)
        # the worn middle: a lighter, smoother, slightly paler disc where the fights happen
        worn = nb.math('SUBTRACT', 1.0, nb.smooth(nb.math('ADD', r, nb.math('MULTIPLY', nb.math('SUBTRACT', n1, 0.5), 1.2)), 2.0, 4.4))
        col = nb.mix(nb.math('MULTIPLY', worn, 0.28), col, C.lin('#DDBD8C'))
        # scuffs: stretched noise streaks, a little darker
        mp = nb.new('ShaderNodeMapping')
        nb.link(obj, mp.inputs['Vector'])
        mp.inputs['Scale'].default_value = (0.35, 2.6, 1.0)
        mp.inputs['Rotation'].default_value = (0, 0, 0.5)
        sc = nb.smooth(nb.noise(mp.outputs[0], 2.4, 2.0, 0.6), 0.6, 0.78)
        col = nb.mix(nb.math('MULTIPLY', sc, 0.22), col, C.lin('#7E6040'))
        # chalk spawn marks at x = ±2.4 (a short line across the A–B axis) and a faint centre circle
        ax = nb.math('ABSOLUTE', xyz[0])
        line = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', ax, SPAWN_X)), 0.025, 0.045)),
                       nb.math('SUBTRACT', 1.0, nb.smooth(nb.math('ABSOLUTE', xyz[1]), 0.42, 0.48)))
        circ = nb.math('SUBTRACT', 1.0, nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', r, 1.55)), 0.018, 0.034))
        chalk = nb.math('MAXIMUM', line, nb.math('MULTIPLY', circ, 0.35))
        wear = nb.smooth(nb.noise(obj, 9.0, 3.0, 0.7), 0.35, 0.62)
        chalk = nb.math('MULTIPLY', chalk, nb.math('MULTIPLY_ADD', wear, 0.55, 0.25))
        col = nb.mix(chalk, col, C.lin('#F4EEDC'))
        # the Guild emblem in faded lime-wash at the centre (1.25 m radius)
        uv = nb.vmath('ADD', nb.vmath('SCALE', nb.comb(xyz[0], xyz[1], 0.0), None, scale=1.0 / 2.5), (0.5, 0.5, 0.0))
        em = self._emblem_mask(nb, uv)
        e = nb.math('MULTIPLY', nb.sep_rgb(em)[0], nb.math('MULTIPLY_ADD', nb.smooth(nb.noise(obj, 5.0, 3.0, 0.65), 0.3, 0.7), 0.16, 0.05))
        col = nb.mix(e, col, C.lin('#F1E7CC'))
        bump = K.bump_from(nb, K.lum(nb, nb.mix(edge, d1.outputs['Color'], d2.outputs['Color'])), 0.35, 0.02)
        K.principled(nb, col, 0.92, bump, 0.2)
        return m

    def _rope(self) -> bpy.types.Material:
        m, nb = new_mat('rope')
        uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
        uv = nb.sep(uvn.outputs[0])
        helix = nb.math('SINE', nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', uv[0], 3.0), nb.math('MULTIPLY', uv[1], 1 / 0.035)), 2 * math.pi))
        v = K.coords(nb, 'UV', 0.25)
        d, _ = K.tex_nodes(nb, 'hessian_230', v, 'FLAT', normal=False)
        col = K.grade(nb, d.outputs['Color'], 0.5, 1.0, 1.05, C.srgb('#C9A672'), 0.45)
        col = nb.mix(nb.math('MULTIPLY_ADD', helix, 0.12, 0.12), col, C.lin('#6E5434'))
        K.principled(nb, col, 0.9, K.bump_from(nb, helix, 0.6, 0.01), 0.15)
        return m

    def _banner(self, name: str, colours, wood: bool = False) -> bpy.types.Material:
        """Linen in the Guild colour, a cream border and the emblem (UV 0..1 over the cloth, v = 1 at the top)."""
        m, nb = new_mat(f'banner_{name}')
        uvn = nb.new('ShaderNodeUVMap', uv_map='UVMap')
        uv = nb.sep(uvn.outputs[0])
        base, trim = C.lin(colours[0]), C.lin(colours[1])
        u, v = uv[0], uv[1]
        if wood:
            vec = K.coords(nb, 'UV', 0.6)
            d, _ = K.tex_nodes(nb, 'weathered_planks', vec, 'FLAT', normal=False)
            grain = K.lum(nb, d.outputs['Color'])
            col = nb.mix(1.0, base, nb.comb(nb.math('MULTIPLY_ADD', grain, 0.6, 0.7), nb.math('MULTIPLY_ADD', grain, 0.6, 0.7), nb.math('MULTIPLY_ADD', grain, 0.6, 0.7)), blend='MULTIPLY')
            border = nb.math('MAXIMUM', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', u, 0.5)), 0.43, 0.445),
                             nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.5)), 0.39, 0.405))
            em_uv = nb.comb(nb.math('MULTIPLY_ADD', nb.math('SUBTRACT', u, 0.5), 2.45, 0.5), nb.math('MULTIPLY_ADD', nb.math('SUBTRACT', v, 0.5), 1.0, 0.5), 0.0)
        else:
            vec = K.coords(nb, 'UV', 0.35)
            d, _ = K.tex_nodes(nb, 'rough_linen', vec, 'FLAT', normal=False)
            weave = K.lum(nb, d.outputs['Color'])
            k = nb.math('MULTIPLY_ADD', weave, 0.5, 0.72)
            col = nb.mix(1.0, base, nb.comb(k, k, k), blend='MULTIPLY')
            border = nb.math('MAXIMUM', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', u, 0.5)), 0.38, 0.40),
                             nb.math('SUBTRACT', 1.0, nb.smooth(v, 0.9, 0.915)))
            border = nb.math('MAXIMUM', border, nb.math('SUBTRACT', 1.0, nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, 0.9)), 0.014, 0.022)))
            em_uv = nb.comb(nb.math('MULTIPLY_ADD', nb.math('SUBTRACT', u, 0.5), 1.25, 0.5), nb.math('MULTIPLY_ADD', nb.math('SUBTRACT', v, 0.6), 0.48, 0.5), 0.0)
        tcol = nb.mix(1.0, trim, nb.comb(0.95, 0.95, 0.95), blend='MULTIPLY')
        col = nb.mix(border, col, tcol)
        em = nb.sep_rgb(self._emblem_mask(nb, em_uv))[0]
        col = nb.mix(em, col, trim)
        K.principled(nb, col, 0.85, K.bump_from(nb, nb.math('ADD', em, 0.0), 0.15, 0.004), 0.2)
        return m

    def _ground(self) -> bpy.types.Material:
        """Grass with trampled dirt round the ring and along the paths (painted by a `dirt` vertex attribute)."""
        m, nb = new_mat('ground')
        tc = nb.new('ShaderNodeTexCoord')
        obj = tc.outputs['Object']
        g, _ = K.tex_nodes(nb, 'leafy_grass', K.coords(nb, 'Object', 2.4), 'FLAT', normal=False)
        dd, _ = K.tex_nodes(nb, 'dirt_floor', K.coords(nb, 'Object', 2.3, 0.3), 'FLAT', normal=False)
        gcol = K.grade(nb, g.outputs['Color'], 0.53, 1.25, 1.18, C.srgb('#7DAA4A'), 0.28, 0.0)
        big = nb.noise(obj, 0.05, 2.0, 0.5)
        gcol = nb.mix(nb.math('MULTIPLY', big, 0.5), gcol, C.lin('#A8B848'))
        # meadow variety: darker lush clumps and a few sun-dried patches, so the lawn never reads as flat paint
        clump = nb.smooth(nb.noise(obj, 0.35, 3.0, 0.6), 0.45, 0.7)
        gcol = nb.mix(nb.math('MULTIPLY', clump, 0.45), gcol, C.lin('#3F7A34'))
        dry = nb.smooth(nb.noise(obj, 0.12, 2.0, 0.5), 0.62, 0.75)
        gcol = nb.mix(nb.math('MULTIPLY', dry, 0.35), gcol, C.lin('#C2B45E'))
        dcol = K.grade(nb, dd.outputs['Color'], 0.5, 0.9, 1.08, C.srgb('#C29C6A'), 0.3, -0.1)
        a = nb.attribute('dirt').outputs['Fac']
        brk = nb.noise(obj, 1.2, 3.0, 0.6)
        mask = nb.smooth(nb.math('ADD', a, nb.math('MULTIPLY', nb.math('SUBTRACT', brk, 0.5), 0.6)), 0.35, 0.6)
        col = nb.mix(mask, gcol, dcol)
        wet = nb.attribute('wet').outputs['Fac']
        col = nb.mix(nb.math('MULTIPLY', wet, 0.75), col, C.lin('#6B6A4C'))
        bump = K.bump_from(nb, K.lum(nb, nb.mix(mask, g.outputs['Color'], dd.outputs['Color'])), 0.3, 0.02)
        K.principled(nb, col, 0.95, bump, 0.15)
        return m

    def _leaves(self) -> bpy.types.Material:
        """Stylised foliage: soft leaf clusters (voronoi), lighter tips toward the sky, a per-tree tint (`Col`)."""
        m, nb = new_mat('leaves')
        tc = nb.new('ShaderNodeTexCoord')
        obj = tc.outputs['Object']
        vor = nb.new('ShaderNodeTexVoronoi', feature='F1')
        nb.put(vor.inputs['Vector'], obj)
        vor.inputs['Scale'].default_value = 7.0
        cells = vor.outputs['Distance']
        n2 = nb.noise(obj, 1.3, 3.0, 0.6)
        tint = nb.attribute('Col').outputs['Color']
        col = nb.mix(nb.math('MULTIPLY', n2, 0.6), tint, nb.mix(1.0, tint, (1.25, 1.2, 0.8, 1.0), blend='MULTIPLY'))
        col = nb.mix(nb.math('MULTIPLY', nb.smooth(cells, 0.15, 0.55), 0.35), col, nb.mix(1.0, tint, (0.55, 0.6, 0.7, 1.0), blend='MULTIPLY'))
        bump = K.bump_from(nb, nb.math('SUBTRACT', 1.0, cells), 0.55, 0.06)
        b = K.principled(nb, col, 0.75, bump, 0.3)
        b.inputs['Subsurface Weight'].default_value = 0.0
        return m

    def _blades(self) -> bpy.types.Material:
        m, nb = new_mat('grass_blades')
        tip = nb.attribute('tip').outputs['Fac']
        tint = nb.attribute('Col').outputs['Color']
        col = nb.mix(tip, nb.mix(1.0, tint, (0.45, 0.55, 0.45, 1.0), blend='MULTIPLY'), nb.mix(1.0, tint, (1.2, 1.15, 0.85, 1.0), blend='MULTIPLY'))
        K.principled(nb, col, 0.7, None, 0.3)
        return m

    def _water(self) -> bpy.types.Material:
        """The river, painted (it ships unlit): deep teal in the middle, shallow turquoise and a sandy shelf at the banks,
        foam ribbons, sky glints. Emission only: the bake reads it as the final colour. UV: u along, v across (0..1)."""
        m, nb = new_mat('water')
        tc = nb.new('ShaderNodeTexCoord')
        obj = tc.outputs['Object']
        across = nb.attribute('across').outputs['Fac']                  # 0 at the middle → 1 at the bank
        deep, shallow, shelf = C.lin('#1E6F73'), C.lin('#45A9A4'), C.lin('#9DB79A')
        col = nb.mix(nb.smooth(across, 0.15, 0.85), deep, shallow)
        col = nb.mix(nb.smooth(across, 0.82, 1.0), col, shelf)
        mp = nb.new('ShaderNodeMapping')
        nb.link(obj, mp.inputs['Vector'])
        mp.inputs['Scale'].default_value = (0.25, 1.6, 1.0)
        streak = nb.noise(mp.outputs[0], 0.9, 4.0, 0.6)
        sky = nb.math('MULTIPLY', nb.smooth(streak, 0.5, 0.7), 0.35)
        col = nb.mix(sky, col, C.lin('#B7DCE6'))
        foam_n = nb.noise(obj, 1.6, 3.0, 0.65)
        foam = nb.math('MULTIPLY', nb.smooth(across, 0.72, 0.92), nb.smooth(foam_n, 0.48, 0.6))
        foam = nb.math('MAXIMUM', foam, nb.math('MULTIPLY', nb.attribute('foam').outputs['Fac'], nb.smooth(foam_n, 0.35, 0.55)))
        col = nb.mix(nb.math('MULTIPLY', foam, 0.85), col, C.lin('#EEF6F2'))
        glint = nb.smooth(nb.noise(mp.outputs[0], 6.0, 2.0, 0.5), 0.72, 0.8)
        col = nb.mix(nb.math('MULTIPLY', glint, 0.5), col, (1.0, 1.0, 0.95, 1.0))
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], nb.mix(1.0, col, (0.72, 0.72, 0.72, 1.0), blend='MULTIPLY'))
        em.inputs['Strength'].default_value = 1.0
        # in the source scene the river also reflects a little (the beauty renders); the bake uses the emission only
        gl = nb.new('ShaderNodeBsdfGlossy')
        gl.inputs['Roughness'].default_value = 0.08
        fr = nb.new('ShaderNodeLayerWeight')
        fr.inputs['Blend'].default_value = 0.25
        mx = nb.new('ShaderNodeMixShader')
        nb.link(nb.math('MULTIPLY', fr.outputs['Fresnel'], 0.6), mx.inputs[0])
        nb.link(em.outputs[0], mx.inputs[1])
        nb.link(gl.outputs[0], mx.inputs[2])
        nb.output(mx.outputs[0])
        return m

    def _mountain(self) -> bpy.types.Material:
        m, nb = new_mat('mountain')
        tc = nb.new('ShaderNodeTexCoord')
        obj = tc.outputs['Object']
        z = nb.sep(obj)[2]
        cam = nb.new('ShaderNodeCameraData')
        dist = cam.outputs['View Distance']
        geo = nb.new('ShaderNodeNewGeometry')
        up = nb.sep(geo.outputs['Normal'])[2]
        n = nb.noise(obj, 0.012, 4.0, 0.6)
        grass = nb.mix(n, C.lin('#4E7F4A'), C.lin('#6A9452'))
        rock = nb.mix(n, C.lin('#7A8294'), C.lin('#9C9DA6'))
        col = nb.mix(nb.smooth(up, 0.82, 0.6), grass, rock)
        snow = nb.math('MULTIPLY', nb.smooth(nb.math('ADD', z, nb.math('MULTIPLY', n, 40.0)), 165.0, 205.0), nb.smooth(up, 0.45, 0.7))
        col = nb.mix(snow, col, C.lin('#F4F6FA'))
        haze = nb.smooth(dist, 120.0, 1500.0)
        col = nb.mix(nb.math('MULTIPLY', haze, 0.9), col, C.lin(SKY_HAZE))
        b = K.principled(nb, col, 0.9, None, 0.1)
        return m


# ----------------------------------------------------------------------------- the ring
def build_ring(M: Mats) -> None:
    g = gcoll('ring')
    rings = np.concatenate([np.linspace(0.0, 5.6, 15), [5.85, 6.0, 6.12, 6.24, 6.38, 6.52, 6.68, 6.84, 7.0]])
    segs = 128
    verts, faces = [(0.0, 0.0, 0.0)], []
    for r in rings[1:]:
        for s in range(segs):
            a = 2 * math.pi * s / segs
            verts.append((r * math.cos(a), r * math.sin(a), 0.0))
    for s in range(segs):
        faces.append((0, 1 + s, 1 + (s + 1) % segs))
    for i in range(len(rings) - 2):
        for s in range(segs):
            a, b = 1 + i * segs + s, 1 + i * segs + (s + 1) % segs
            faces.append((a, a + segs, b + segs, b))          # counter-clockwise from above: facing up
    V = np.asarray(verts)
    r = np.hypot(V[:, 0], V[:, 1])
    rim = 0.17 * ss(6.0, 6.24, r) * (1 - ss(6.62, 6.98, r))
    open_ = ss(GATE_HALF + 0.35, GATE_HALF - 0.05, np.abs(V[:, 1])) * (np.abs(V[:, 0]) > 5.0)   # flat through the gates
    V[:, 2] = rim * (1 - open_)
    ob = K.obj_from_arrays('ring_floor', V, faces, g, [M.floor])
    K.planar_uv(ob, -7.2, -7.2, 14.4, 'UVMap')
    tag(ob)


# ----------------------------------------------------------------------------- the fence, gates and stones
def catenary(p0: Vector, p1: Vector, sag: float, n: int) -> np.ndarray:
    t = np.linspace(0, 1, n)
    P = np.outer(1 - t, p0) + np.outer(t, p1)
    P[:, 2] -= sag * 4 * t * (1 - t)
    return P


def build_fence(M: Mats, rng) -> dict:
    gt, gn = gcoll('timber'), gcoll('timber')
    gate_ang = math.asin((GATE_HALF + 0.12) / POST_R)
    arcs = [(gate_ang, math.pi - gate_ang), (math.pi + gate_ang, 2 * math.pi - gate_ang)]
    posts = []
    for a0, a1 in arcs:
        n = int(round((a1 - a0) * POST_R / 1.6))
        for i in range(n + 1):
            posts.append(a0 + (a1 - a0) * i / n)
    post_tops = []
    for k, a in enumerate(posts):
        near = math.sin(a) < -0.26
        c = Vector((POST_R * math.cos(a), POST_R * math.sin(a), 0.0))
        is_gate = abs(math.sin(a) * POST_R) < GATE_HALF + 0.3
        h = 1.18 + rng.normal(0, 0.03)
        lean = Matrix.Rotation(rng.normal(0, 0.025), 3, 'X') @ Matrix.Rotation(rng.normal(0, 0.025), 3, 'Y') @ Matrix.Rotation(a + rng.normal(0, 0.08), 3, 'Z')
        ob = K.box_obj(f'post_{k}', (0.17, 0.16, h + 0.25), c + Vector((0, 0, (h - 0.25) / 2)), gn, [M.post], lean, bevel=0.022)
        K.box_uv(ob, 1.0)
        tag(ob, near=near)
        post_tops.append((c, h, near, is_gate))
    # ropes: two sagging rows along the inner faces
    for row_h, sag in ((0.56, 0.07), (1.0, 0.1)):
        for arc_i, (a0, a1) in enumerate(arcs):
            idx = [i for i, a in enumerate(posts) if a0 - 1e-6 <= a <= a1 + 1e-6]
            for i0, i1 in zip(idx[:-1], idx[1:]):
                pa, pb = posts[i0], posts[i1]
                p0 = Vector((ROPE_R * math.cos(pa), ROPE_R * math.sin(pa), row_h))
                p1 = Vector((ROPE_R * math.cos(pb), ROPE_R * math.sin(pb), row_h))
                P = catenary(p0, p1, sag * (0.85 + 0.3 * rng.random()), 11)
                v, f, uv = K.tube_along(P, 0.024, 6)
                near = math.sin((pa + pb) / 2) < -0.26
                ob = K.obj_from_arrays(f'rope_{arc_i}_{i0}_{row_h}', v, f, gn, [M.rope], uvs=uv, smooth=True)
                tag(ob, near=near)
                # a wrap where the rope meets each post
                for pc in (p0, p1):
                    Pw = np.array([pc + Vector((0, 0, -0.07)), pc + Vector((0, 0, 0.07))])
                    v2, f2, uv2 = K.tube_along(Pw, 0.045, 6)
                    w = K.obj_from_arrays(f'wrap_{arc_i}_{i0}', v2, f2, gn, [M.rope], uvs=uv2, smooth=True)
                    tag(w, near=near)
    # the gates: tall posts, a crossbeam with braces, a hanging sign with the emblem
    gates = {}
    for name, sx in (('A', -1.0), ('B', 1.0)):
        x0 = sx * POST_R
        for sy in (-1, 1):
            ob = K.box_obj(f'gatepost_{name}{sy}', (0.24, 0.24, 3.05), (x0, sy * (GATE_HALF + 0.12), 1.3), gt, [M.post], bevel=0.03)
            K.box_uv(ob, 1.2)
            tag(ob, near=False)
            br = K.box_obj(f'brace_{name}{sy}', (0.11, 0.1, 0.75), (x0, sy * (GATE_HALF - 0.12), 2.42), gt, [M.post],
                           Matrix.Rotation(math.radians(48 * sy), 3, 'X'), bevel=0.012)
            K.box_uv(br, 1.0)
            tag(br)
        beam = K.box_obj(f'gatebeam_{name}', (0.26, 2 * GATE_HALF + 0.9, 0.22), (x0, 0, 2.72), gt, [M.post], bevel=0.03)
        K.box_uv(beam, 1.2, grain_z=False)
        tag(beam)
        # the sign board hangs inside the ring side of the beam, facing the ring centre
        sign = sign_board(f'sign_{name}', Vector((x0 - sx * 0.02, 0, 2.18)), -sx, M, gt)
        tag(sign)
        for sy in (-0.42, 0.42):
            P = np.array([[x0 - sx * 0.02, sy, 2.62], [x0 - sx * 0.02, sy, 2.4]])
            v, f, uv = K.tube_along(P, 0.012, 4)
            tag(K.obj_from_arrays(f'signrope_{name}{sy}', v, f, gt, [M.rope], uvs=uv))
        gates[name] = Vector((x0, 0, 0))
    return {'posts': post_tops, 'gates': gates}


def sign_board(name: str, centre: Vector, facing_x: float, M: Mats, g) -> bpy.types.Object:
    """A plank board 1.15 × 0.5 m, its painted face toward -x·facing (the ring)."""
    w, h, t = 1.15, 0.5, 0.05
    bm = bmesh.new()
    geom = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((t, w, h)), verts=geom['verts'])
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.012, segments=1, affect='EDGES', profile=0.5, clamp_overlap=True)
    bmesh.ops.translate(bm, vec=centre, verts=bm.verts)
    ob = K.obj_from_bm(name, bm, g, [M.sign])
    # UVs: the face toward the ring gets 0..1 (u along y, v up); everything else a sliver of the border
    me = ob.data
    co = K.mesh_np(ob)
    lv, pol, pn = K.loop_arrays(me)
    p = co[lv]
    u = (p[:, 1] - centre.y) / w * (-facing_x) + 0.5
    v = (p[:, 2] - centre.z) / h + 0.5
    face = (pn[pol][:, 0] * facing_x) > 0.5
    u = np.where(face, u, 0.03)
    v = np.where(face, v, 0.5)
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', np.stack([u, v], 1).astype(np.float32).ravel())
    return ob


def build_rim_stones(M: Mats, rng) -> None:
    g = gcoll('timber')
    bm = bmesh.new()
    k = 0
    a = 0.0
    while a < 2 * math.pi:
        a += (0.055 + 0.07 * rng.random())
        r = 6.42 + rng.normal(0, 0.12)
        x, y = r * math.cos(a), r * math.sin(a)
        if abs(y) < GATE_HALF + 0.45 and abs(x) > 4:
            continue
        s = 0.11 + 0.1 * rng.random()
        K.ico_blob(bm, (x, y, 0.06 + s * 0.12), s, (1.0 + 0.5 * rng.random(), 0.8 + 0.4 * rng.random(), 0.55 + 0.25 * rng.random()), 1, 0.08, rng)
        k += 1
    ob = K.obj_from_bm('rim_stones', bm, g, [M.stone], smooth=True)
    tag(ob)
    C.log(f'rim stones: {k}')


# ----------------------------------------------------------------------------- the stands and the crowd
STANDS = [  # (angle from, angle to (deg), tiers, near side?)
    (27.0, 153.0, 3, False),
    (205.0, 238.0, 2, True),
    (302.0, 335.0, 2, True),
]
TIER0_R, TIER_STEP_R, TIER0_H, TIER_STEP_H, SEAT_D = 8.55, 0.86, 0.44, 0.42, 0.36


def build_stands(M: Mats, rng) -> list[tuple[Vector, float, float]]:
    """Stepped wooden stands (straight sections along an arc), painted risers in the Guild colours. Returns seats:
    (position on the seat, the yaw toward the ring centre, the tier's seat height)."""
    g = gcoll('timber')
    seats = []
    for si, (d0, d1, tiers, near) in enumerate(STANDS):
        a0, a1 = math.radians(d0), math.radians(d1)
        rmid = TIER0_R + TIER_STEP_R * tiers / 2
        nseg = max(2, int(round((a1 - a0) * rmid / 2.1)))
        for k in range(nseg):
            b0, b1 = a0 + (a1 - a0) * k / nseg, a0 + (a1 - a0) * (k + 1) / nseg
            bm_mid = (b0 + b1) / 2
            yaw = bm_mid + math.pi            # facing the centre
            R = Matrix.Rotation(bm_mid, 3, 'Z')
            for t in range(tiers):
                r = TIER0_R + TIER_STEP_R * t
                h = TIER0_H + TIER_STEP_H * t
                chord = 2 * (r + SEAT_D) * math.sin((b1 - b0) / 2) + 0.02
                c = Vector(((r) * math.cos(bm_mid), (r) * math.sin(bm_mid), h - 0.025))
                seat = K.box_obj(f'seat_{si}_{k}_{t}', (SEAT_D + 0.06, chord, 0.05), c, g, [M.plank], R, bevel=0.008)
                K.along_uv(seat, R @ Vector((0, 1, 0)), 1.6)
                tag(seat, lite=True)
                # the riser below the seat front (painted, colour by stand)
                rc = Vector(((r - SEAT_D / 2) * math.cos(bm_mid), (r - SEAT_D / 2) * math.sin(bm_mid), h / 2 - 0.02))
                rh = h - 0.02
                riser = K.box_obj(f'riser_{si}_{k}_{t}', (0.035, chord - 0.01, rh), rc, g, [M.plank_paint], R)
                K.along_uv(riser, R @ Vector((0, 1, 0)), 1.6)
                col = C.srgb([TEAL, CREAM, CORAL][(k + t) % 3]) if t == 0 else C.srgb([CREAM, TEAL, GOLD][(k + 2 * t) % 3])
                K.set_face_colors(riser, [col] * len(riser.data.polygons))
                tag(riser)
                # a footboard in front of the riser for t > 0 is the seat below; the back: a solid back panel
                if t == tiers - 1:
                    bc = Vector(((r + SEAT_D / 2 + 0.04) * math.cos(bm_mid), (r + SEAT_D / 2 + 0.04) * math.sin(bm_mid), h / 2 + 0.25))
                    back = K.box_obj(f'back_{si}_{k}', (0.05, chord + 0.02, h + 0.5), bc, g, [M.plank], R, bevel=0.006)
                    K.along_uv(back, R @ Vector((0, 1, 0)), 1.6)
                    tag(back)
                    rail_c = Vector(((r + SEAT_D / 2 + 0.04) * math.cos(bm_mid), (r + SEAT_D / 2 + 0.04) * math.sin(bm_mid), h + 0.52))
                    rail = K.box_obj(f'rail_{si}_{k}', (0.1, chord + 0.04, 0.07), rail_c, g, [M.post], R, bevel=0.01)
                    K.along_uv(rail, R @ Vector((0, 1, 0)), 1.2)
                    tag(rail)
                # seats for the crowd (spaced ~0.6 m)
                nseat = max(1, int(chord / 0.6))
                for j in range(nseat):
                    f = (j + 0.5) / nseat
                    b = b0 + (b1 - b0) * f
                    seats.append((Vector((r * math.cos(b), r * math.sin(b), h)), b + math.pi, t, near))
            # the end walls of each stand
        for b in (a0, a1):
            R = Matrix.Rotation(b, 3, 'Z')
            for t in range(tiers):
                r = TIER0_R + TIER_STEP_R * t
                h = TIER0_H + TIER_STEP_H * t
                c = Vector((r * math.cos(b), r * math.sin(b), h / 2))
                end = K.box_obj(f'end_{si}_{b:.2f}_{t}', (TIER_STEP_R + 0.02, 0.05, h), c, g, [M.plank], R)
                K.box_uv(end, 1.6)
                tag(end)
    return seats


PALETTE_CLOTHES = ['#D9534A', '#E9A23B', '#3E8E7E', '#4F79B5', '#8E5DA8', '#E7C76A', '#6FA05A', '#F0E2C6', '#C46A8A',
                   '#5A9CB3', '#B5552E', '#7B8F3A', '#E58F6B', '#356A8F', '#F2B6A0']
SKIN = ['#F2D0B3', '#E8B894', '#D69E78', '#B97F59', '#8F5E3E', '#6B4430', '#F6DCC4']
HAIR = ['#3B2A20', '#6A4528', '#2A2420', '#B07B3E', '#D9B26A', '#8C3B2A', '#9A9590']
HATS = ['#E8C873', '#D9B45E', '#7A5A3C', '#3E8E7E', '#C94F3F', '#F0E2C6']


def person(bm_cloth, bm_skin, colors_cloth: list, colors_skin: list, base: Vector, yaw: float, rng, seated: bool,
           scale: float = 1.0, cheer: float = 0.0) -> None:
    """One stylised townsperson: a bell-shaped body, a round head, maybe a hat or hair bun, arms (raised when
    cheering), and thighs when seated. Faces are per-face colours (Col)."""
    R = Matrix.Rotation(yaw, 3, 'Z')
    s = scale * (0.92 + 0.16 * rng.random())
    w = (0.38 + 0.1 * rng.random()) * s
    th = (0.62 if seated else 1.0) * s * (0.95 + 0.1 * rng.random())
    cloth = C.srgb(PALETTE_CLOTHES[rng.integers(len(PALETTE_CLOTHES))])
    skin = C.srgb(SKIN[rng.integers(len(SKIN))])

    def add(bm, verts, faces, col, cols):
        vv = [bm.verts.new(v) for v in verts]
        for f in faces:
            try:
                bm.faces.new([vv[i] for i in f])
                cols.append(col)
            except ValueError:
                pass

    prof = [(w * 0.5, 0.0), (w * 0.54, th * 0.3), (w * 0.47, th * 0.68), (w * 0.33, th * 0.92), (w * 0.12, th)]
    v, f = K.lathe(prof, 7, base, R, cap_top=True, cap_bottom=True)
    add(bm_cloth, v, f, cloth, colors_cloth)
    hr = (0.125 + 0.02 * rng.random()) * s
    hc = base + Vector((0, 0, th + hr * 0.85))
    hp = [(hr * math.sin(math.pi * i / 6), -hr * math.cos(math.pi * i / 6)) for i in range(7)]
    hp[0], hp[-1] = (0.0, -hr), (0.0, hr)
    hp = [(max(r, 0.0), z) for r, z in hp]
    v, f = K.lathe(hp[1:-1], 6, hc, R, cap_top=True, cap_bottom=True)
    add(bm_skin, v, f, skin, colors_skin)
    k = rng.random()
    if k < 0.32:                                     # a straw sun hat or a felt hat
        hat = C.srgb(HATS[rng.integers(len(HATS))])
        v, f = K.lathe([(hr * 1.9, hr * 0.45), (hr * 1.9, hr * 0.52), (hr * 0.95, hr * 0.6), (hr * 0.85, hr * 1.1), (hr * 0.3, hr * 1.25)], 6, hc, R)
        add(bm_cloth, v, f, hat, colors_cloth)
    elif k < 0.55:                                   # hair cap and maybe a bun
        hair = C.srgb(HAIR[rng.integers(len(HAIR))])
        v, f = K.lathe([(hr * 1.04, hr * 0.05), (hr * 1.02, hr * 0.5), (hr * 0.75, hr * 0.85), (hr * 0.2, hr * 1.04)], 6, hc, R, cap_bottom=False)
        add(bm_cloth, v, f, hair, colors_cloth)
        if rng.random() < 0.5:
            v, f = K.lathe([(0.0, -hr * 0.35), (hr * 0.38, -hr * 0.2), (hr * 0.4, hr * 0.05), (hr * 0.2, hr * 0.3), (0.0, hr * 0.32)][1:-1], 6,
                           hc + R @ Vector((-hr * 0.85, 0, hr * 0.55)), R)
            add(bm_cloth, v, f, hair, colors_cloth)
    elif k < 0.68:                                   # a headscarf in a bright colour
        sc = C.srgb(PALETTE_CLOTHES[rng.integers(len(PALETTE_CLOTHES))])
        v, f = K.lathe([(hr * 1.08, -hr * 0.1), (hr * 1.07, hr * 0.45), (hr * 0.78, hr * 0.85), (hr * 0.2, hr * 1.06)], 6, hc, R, cap_bottom=False)
        add(bm_cloth, v, f, sc, colors_cloth)
    # arms: down at the sides, or up and out when cheering
    sh = th * 0.82
    for side in (-1, 1):
        up = rng.random() < cheer
        p0 = base + R @ Vector((0.0, side * w * 0.42, sh))
        if up:
            d = R @ Vector((0.12 * rng.normal(1, 0.3), side * 0.18, 0.42)).normalized()
        else:
            d = R @ Vector((0.18, side * 0.1, -0.5)).normalized()
        L = 0.42 * s
        P = np.array([p0, p0 + d * L * 0.55, p0 + d * L])
        v, f, _ = K.tube_along(P, np.array([0.055, 0.05, 0.045]) * s, 4)
        add(bm_cloth, v, f, cloth, colors_cloth)
    if seated:                                       # thighs forward over the seat edge, shins down
        legs = C.srgb(['#5B4636', '#3D4A5C', '#6E5B3E', '#4A3A30', '#2F3C4A'][rng.integers(5)])
        for side in (-1, 1):
            p0 = base + R @ Vector((0.05, side * w * 0.2, 0.08))
            p1 = base + R @ Vector((0.36 * s, side * w * 0.22, 0.06))
            p2 = base + R @ Vector((0.4 * s, side * w * 0.22, -0.36))
            P = np.array([p0, p1, p2])
            v, f, _ = K.tube_along(P, np.array([0.08, 0.07, 0.06]) * s, 4)
            add(bm_cloth, v, f, legs, colors_cloth)


def little_fan(bm, cols, base: Vector, yaw: float, rng) -> None:
    """A small round fan monster (our own): a soft egg body, two rounded ears, a pale tummy patch."""
    R = Matrix.Rotation(yaw, 3, 'Z')
    body = C.srgb(['#8FD0C2', '#F2B36B', '#C9A3E0', '#F5D76E', '#A6D58A'][rng.integers(5)])
    s = 0.22 + 0.06 * rng.random()
    v, f = K.lathe([(s * 0.6, 0.0), (s * 0.95, s * 0.35), (s * 0.95, s * 0.8), (s * 0.7, s * 1.2), (s * 0.25, s * 1.42)], 8, base, R)
    vv = [bm.verts.new(x) for x in v]
    for fc in f:
        bm.faces.new([vv[i] for i in fc])
        cols.append(body)
    for side in (-1, 1):
        c = base + R @ Vector((0.0, side * s * 0.5, s * 1.38))
        v, f = K.lathe([(s * 0.18, 0.0), (s * 0.2, s * 0.25), (s * 0.08, s * 0.45)], 5, c, R @ Matrix.Rotation(side * 0.35, 3, 'X'))
        vv = [bm.verts.new(x) for x in v]
        for fc in f:
            bm.faces.new([vv[i] for i in fc])
            cols.append(body)


def build_crowd(M: Mats, seats, rng) -> int:
    g = gcoll('crowd')
    bm_c, bm_s = bmesh.new(), bmesh.new()
    cc, cs = [], []
    n = 0
    lite_cloth, lite_skin = [], []
    for (p, yaw, tier, near) in seats:
        if rng.random() < 0.16:
            continue
        if rng.random() < 0.05 and tier < 2:
            little_fan(bm_c, cc, p + Vector((0, 0, 0.02)), yaw, rng)
            continue
        f0c, f0s = len(cc), len(cs)
        person(bm_c, bm_s, cc, cs, p - Vector((math.cos(yaw), math.sin(yaw), 0)) * (-0.06), yaw + rng.normal(0, 0.15), rng, True, 1.0, cheer=0.3)
        keep = (n % 2 == 0)
        lite_cloth += [keep] * (len(cc) - f0c)
        lite_skin += [keep] * (len(cs) - f0s)
        n += 1
    # a standing row behind the long stand, and folk by the gates and the near corners
    standing = []
    for k in range(14):
        a = math.radians(32 + (148 - 32) * (k + 0.5) / 18 + rng.normal(0, 1.5))
        standing.append(Vector((11.35 * math.cos(a), 11.35 * math.sin(a), 0.0)))
    for (gx, sy) in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        for j in range(3):
            standing.append(Vector((gx * (7.3 + 0.9 * j + rng.random() * 0.4), sy * (2.2 + 0.7 * rng.random() + 0.5 * j), 0.0)))
    for p in standing:
        yaw = math.atan2(-p.y, -p.x)
        f0c, f0s = len(cc), len(cs)
        person(bm_c, bm_s, cc, cs, p, yaw + rng.normal(0, 0.2), rng, False, 1.0 + rng.normal(0, 0.05), cheer=0.35)
        lite_cloth += [n % 2 == 0] * (len(cc) - f0c)
        lite_skin += [n % 2 == 0] * (len(cs) - f0s)
        n += 1
    lite_cloth += [True] * (len(cc) - len(lite_cloth))
    ob_c = K.obj_from_bm('crowd_cloth', bm_c, g, [M.cloth], smooth=True)
    K.set_face_colors(ob_c, cc)
    ob_s = K.obj_from_bm('crowd_skin', bm_s, g, [M.skin], smooth=True)
    K.set_face_colors(ob_s, cs)
    for ob, lite in ((ob_c, lite_cloth), (ob_s, lite_skin)):
        tag(ob)
        a = ob.data.attributes['lite']
        a.data.foreach_set('value', np.asarray(lite[:len(ob.data.polygons)] + [True] * max(0, len(ob.data.polygons) - len(lite)), np.int32))
    C.log(f'crowd: {n} people, {K.tri_count(ob_c) + K.tri_count(ob_s)} tris')
    return n


def drop_baked_crowd(M: Mats, seats, rng) -> None:
    """The crowd lives in the game now (src/art3d/duel/crowd.ts: animated, filled by Fame). The old baked people are still
    built and then thrown away, only so the shared random stream stays the same and the banners, props, town and trees
    (and the fly-in path threaded between them) stay exactly where they were."""
    build_crowd(M, seats, rng)
    for name in ('crowd_cloth', 'crowd_skin'):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me)


# Where the game's crowd sits or stands (guild.json → seats). Bench seats every SEAT_PITCH along each tier, kids at the
# rail in front of the stands, and standing folk by the gates and along the open front. All deterministic.
SEAT_PITCH = 0.44                 # the straight planks get 3–5 seats each, 0.45–0.55 m apart
GROUND_R, GROUND_PITCH = 7.85, 0.62
GATE_SPOTS = [(7.2, 3.1), (8.0, 3.22), (8.8, 3.12), (10.3, 2.05), (11.05, 2.6)]     # (|x|, |y|) per gate and side
FRONT = [(8.0, 256.0, 290.0)]          # (radius, from°, to°) rows (one: the crowd's triangle budget)
FRONT_PITCH = 0.62


def crowd_spots() -> list[dict]:
    """Every seat and standing spot, Blender frame (z up): p = the seat top or the ground under the spot, `face` = the
    yaw (radians, Blender, from +x) the person faces (the ring centre), row (tier; -1 on the ground), section, kind
    (seat / ground / stand) and lite (every other spot of each row, so Lite keeps an even half)."""
    out = []

    def add(x, y, z, row, section, kind, i):
        out.append({'p': (x, y, z), 'face': math.atan2(-y, -x), 'row': row, 'section': section, 'kind': kind, 'lite': i % 2 == 0})

    names = ['long', 'nearA', 'nearB']
    for si, (d0, d1, tiers, _near) in enumerate(STANDS):
        a0, a1 = math.radians(d0), math.radians(d1)
        rmid = TIER0_R + TIER_STEP_R * tiers / 2
        nseg = max(2, int(round((a1 - a0) * rmid / 2.1)))
        for t in range(tiers):
            r = TIER0_R + TIER_STEP_R * t
            h = TIER0_H + TIER_STEP_H * t
            i = 0
            for k in range(nseg):
                b0, b1 = a0 + (a1 - a0) * k / nseg, a0 + (a1 - a0) * (k + 1) / nseg
                m = (b0 + b1) / 2
                L = 2 * r * math.tan((b1 - b0) / 2)                       # the straight plank's length at radius r
                n = max(1, int(L / SEAT_PITCH))
                for j in range(n):
                    s = ((j + 0.5) / n - 0.5) * L
                    add(r * math.cos(m) - s * math.sin(m), r * math.sin(m) + s * math.cos(m), h, t, names[si], 'seat', i)
                    i += 1
        # kids at the rail in front of the stand (clear of its end walls)
        span = (a1 - a0) - 2 * 0.3 / GROUND_R
        n = int(span * GROUND_R / GROUND_PITCH)
        for j in range(n):
            b = a0 + 0.3 / GROUND_R + span * (j + 0.5) / n
            add(GROUND_R * math.cos(b), GROUND_R * math.sin(b), 0.0, -1, names[si], 'ground', j)
    for gate, sx in (('gateA', -1.0), ('gateB', 1.0)):
        i = 0
        for sy in (-1.0, 1.0):
            for (ax, ay) in GATE_SPOTS:
                add(sx * ax, sy * ay, 0.0, -1, gate, 'stand', i)
                i += 1
    for ri, (r, d0, d1) in enumerate(FRONT):
        a0, a1 = math.radians(d0), math.radians(d1)
        n = int((a1 - a0) * r / FRONT_PITCH) + 1
        for j in range(n):
            b = a0 + (a1 - a0) * j / max(1, n - 1)
            add(r * math.cos(b), r * math.sin(b), 0.0, -1 - ri, 'front', 'stand', j)
    return out


# ----------------------------------------------------------------------------- banners and bunting
BANNER_POLES = [(40, 11.95), (65, 12.0), (90, 12.05), (115, 12.0), (140, 11.95)]


def banner_cloth(name: str, top: Vector, yaw: float, w: float, h: float, mat, g, rng) -> bpy.types.Object:
    """A hanging linen banner with a swallowtail foot and a gentle wave; UV 0..1 (v = 1 at the top)."""
    nu, nv = 7, 14
    R = Matrix.Rotation(yaw, 3, 'Z')
    verts, uvs_v = [], []
    for j in range(nv + 1):
        v = 1 - j / nv
        for i in range(nu + 1):
            u = i / nu
            y = (u - 0.5) * w
            z = -(1 - v) * h
            notch = 0.32 * (1 - abs(u - 0.5) * 2)                 # the swallowtail cut
            z = max(z, -h + notch * (1 if v < 0.25 else 0)) if v < 0.25 else z
            x = 0.05 * math.sin(u * math.pi * 2.0 + v * 1.3 + rng.random() * 0.2) * (1 - v * 0.6) + 0.04 * (1 - v)
            verts.append(top + R @ Vector((x, y, z)))
            uvs_v.append((u, max(0.0, (z + h) / h)))
    faces, uvs = [], []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            q = (a, a + nu + 1, a + nu + 2, a + 1)                  # the front faces the ring
            faces.append(q)
            uvs += [uvs_v[k] for k in q]
    return K.obj_from_arrays(name, verts, faces, g, [mat], uvs=uvs, smooth=True)


def build_banners(M: Mats, rng) -> list[Vector]:
    gt, gc = gcoll('timber'), gcoll('crowd')
    tops = []
    poles = [(math.radians(a), r) for a, r in BANNER_POLES]
    for (gx) in (-1, 1):                       # flanking each gate, outside
        for sy in (-1, 1):
            p = Vector((gx * 7.6, sy * 2.3, 0))
            poles.append((math.atan2(p.y, p.x), p.length))
    for k, (a, r) in enumerate(poles):
        base = Vector((r * math.cos(a), r * math.sin(a), 0))
        tall = 5.8 if k < len(BANNER_POLES) else 4.6
        pole = K.cyl_obj(f'pole_{k}', base + Vector((0, 0, -0.3)), base + Vector((0, 0, tall)), 0.075, 0.06, gt, [M.post], 8)
        K.along_uv(pole, Vector((0, 0, 1)), 1.2)
        tag(pole)
        knob = bmesh.new()
        bmesh.ops.create_icosphere(knob, subdivisions=1, radius=0.11)
        bmesh.ops.translate(knob, vec=base + Vector((0, 0, tall + 0.08)), verts=knob.verts)
        kb = K.obj_from_bm(f'finial_{k}', knob, gt, [M.gold], smooth=True)
        tag(kb)
        yaw = a + math.pi                       # the banner faces the ring
        Rb = Matrix.Rotation(yaw, 3, 'Z')
        bar_c = base + Rb @ Vector((-0.12, 0, tall - 0.22))
        bar = K.box_obj(f'bar_{k}', (0.07, 1.1, 0.07), bar_c, gt, [M.post], Rb, bevel=0.01)
        K.along_uv(bar, Rb @ Vector((0, 1, 0)), 1.2)
        tag(bar)
        colour = 'teal' if k % 2 == 0 else 'coral'
        b = banner_cloth(f'banner_{k}', bar_c + Rb @ Vector((-0.05, 0, -0.04)), yaw, 0.92, 2.3 if k < len(BANNER_POLES) else 1.8, M.banner[colour], gc, rng)
        tag(b)
        tops.append(base + Vector((0, 0, tall - 0.6)))
    # bunting between the tall poles over the long stand, and from the gate arches to the flanking poles
    flags = bmesh.new()
    cols = []
    spans = list(zip(tops[:len(BANNER_POLES) - 1], tops[1:len(BANNER_POLES)]))
    for p0, p1 in spans:
        P = catenary(p0, p1, 0.75, 24)
        v, f, uv = K.tube_along(P, 0.012, 3)
        tag(K.obj_from_arrays(f'bunting_line_{len(cols)}', v, f, gt, [M.rope], uvs=uv))
        L = (p1 - p0).length
        nf = int(L / 0.42)
        for i in range(nf):
            t = (i + 0.5) / nf
            q0 = P[int(t * 23)]
            q1 = P[min(23, int(t * 23) + 1)]
            d = Vector(q1 - q0).normalized()
            c = Vector(q0)
            a = c - d * 0.13
            b = c + d * 0.13
            tip = c + Vector((0, 0, -0.3))
            va = [flags.verts.new(x) for x in (a, b, tip)]
            flags.faces.new(va)
            cols.append(C.srgb([CREAM, TEAL, CORAL, GOLD][i % 4]))
    ob = K.obj_from_bm('bunting_flags', flags, gc, [M.cloth])
    K.set_face_colors(ob, cols)
    tag(ob)
    return tops


# ----------------------------------------------------------------------------- props (Poly Haven CC0)
PROPS = [  # (asset, x, y, yaw deg, scale, decimate-to tris, lite)
    ('wine_barrel_01', -7.7, -1.75, 10, 0.95, 1000, True),
    ('wine_barrel_01', -8.35, -1.55, 64, 0.9, 1000, False),
    ('wooden_crate_01', -7.5, 1.95, 15, 1.0, 900, True),
    ('wooden_crate_01', -7.55, 1.95, 22, 0.85, 900, False),     # stacked (z set below)
    ('wooden_bucket_01', -6.95, 2.55, 0, 0.95, 900, True),
    ('wicker_basket_01', -8.25, 2.6, 30, 0.95, 800, False),
    ('wine_barrel_01', 7.6, 1.8, -20, 0.95, 1000, True),
    ('wooden_crate_01', 7.55, -1.95, -12, 1.0, 900, True),
    ('wooden_bucket_02', 6.95, -2.55, 40, 0.9, 900, False),
    ('wicker_basket_02', 8.3, -2.45, -25, 0.9, 800, True),
    ('wooden_stool_02', 8.4, 2.35, 70, 1.0, 900, False),
    ('painted_wooden_bench', -6.9, -9.3, 200, 1.15, 700, True),
    ('painted_wooden_bench', 7.2, -9.4, 160, 1.15, 700, False),
    ('wooden_bucket_01', 5.9, -8.4, 20, 0.95, 900, True),
    ('wooden_crate_01', -9.6, -6.1, 33, 1.0, 900, True),
    ('wine_barrel_01', 9.7, -6.0, 5, 0.95, 1000, True),
    ('wicker_basket_01', 9.0, -6.75, -10, 0.9, 800, False),
    ('painted_wooden_stool', -8.9, -6.85, 10, 1.0, 600, False),
    ('folding_wooden_stool', 6.9, -7.4, 35, 1.0, 900, False),
    ('wooden_lantern_01', -7.5, 1.95, 0, 1.25, 700, True),     # on the crates (z set below)
    ('wooden_lantern_01', 7.6, 1.8, 0, 1.25, 700, True),       # on the barrel
    ('tree_stump_01', -12.6, -9.5, 10, 1.0, 800, False),
    ('tree_stump_01', 13.2, 7.0, 100, 0.9, 800, False),
    ('boulder_01', -18.0, 14.8, 30, 1.0, 900, False),
    ('boulder_01', 15.5, 16.0, 200, 0.7, 800, False),
    ('boulder_01', 26.0, 17.4, 120, 0.55, 1000, False),
]


def build_props(rng) -> None:
    g = gcoll('props')
    staging = coll('PH_staging')
    proto: dict[str, list[bpy.types.Object]] = {}
    tops: dict[tuple[float, float], float] = {}
    for k, (aid, x, y, yaw, scale, tris, lite) in enumerate(PROPS):
        if aid not in proto:
            proto[aid] = K.import_model(aid, staging)
        objs = []
        for o in proto[aid]:
            c = o.copy()
            c.data = o.data.copy()
            g.objects.link(c)
            objs.append(c)
        # bottom of the prototype at z = 0, centred on x/y
        co = np.concatenate([K.mesh_np(o) for o in objs])
        mn, mx = co.min(0), co.max(0)
        z0 = tops.get((round(x, 1), round(y, 1)), 0.0) if aid in ('wooden_lantern_01',) or k == 3 else 0.0
        if k == 3:
            z0 = tops.get((-7.5, 1.9), 0.0)
        m = (Matrix.Translation((x, y, z0)) @ Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Scale(scale, 4)
             @ Matrix.Translation((-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2])))
        total = sum(K.tri_count(o) for o in objs)
        for o in objs:
            o.data.transform(m)
            o.matrix_world = Matrix.Identity(4)
            K.decimate_to(o, max(60, int(tris * K.tri_count(o) / max(1, total))))
            tag(o, lite=lite)
        h = (mx[2] - mn[2]) * scale + z0
        tops[(round(x, 1), round(y, 1))] = max(tops.get((round(x, 1), round(y, 1)), 0.0), h)
    for objs in proto.values():
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)


# ----------------------------------------------------------------------------- terrain and river
def polar_grid(r0: float, r1: float, n_r: int, segs: int, growth: float):
    radii = [r0]
    while radii[-1] < r1:
        radii.append(min(r1, radii[-1] * growth + 0.35))
    verts = []
    for r in radii:
        for s in range(segs):
            a = 2 * math.pi * (s + 0.5 * (len(verts) // segs % 2)) / segs
            verts.append((r * math.cos(a), r * math.sin(a)))
    faces = []
    for i in range(len(radii) - 1):
        for s in range(segs):
            a, b = i * segs + s, i * segs + (s + 1) % segs
            faces.append((a, a + segs, b + segs, b))
    return np.asarray(verts), faces


def ground_attrs(ob: bpy.types.Object) -> None:
    """`dirt` (trampled earth round the ring, under the stands, the paths) and `wet` (the river's muddy edge)."""
    co = K.mesh_np(ob)
    x, y = co[:, 0], co[:, 1]
    r = np.hypot(x, y)
    dirt = (1 - ss(10.5, 13.5, r)) * 0.9
    path_a = (1 - ss(1.1, 2.0, np.abs(y + 0.04 * x))) * (x < -6) * (1 - ss(14, 30, -x))
    path_b = (1 - ss(1.1, 2.0, np.abs(y - 0.03 * x))) * (x > 6) * (1 - ss(16, 32, x))
    # the lane from gate A curving to the bridge (x ≈ -30)
    lane = np.zeros_like(r)
    for t in np.linspace(0, 1, 40):
        px, py = -14 - 16 * t, -0.5 + 15.0 * t * t
        lane = np.maximum(lane, 1 - ss(1.2, 2.2, np.hypot(x - px, y - py)))
    lane2 = (1 - ss(1.4, 2.4, np.abs(x + 30 + 0.05 * (y - 30)))) * (y > 25) * (y < 60)
    dirt = np.maximum.reduce([dirt, path_a, path_b, lane, lane2])
    d = np.abs(y - river_y(x))
    wet = (1 - ss(4.2, 6.0, d))
    me = ob.data
    for name, val in (('dirt', dirt), ('wet', wet)):
        a = me.attributes.get(name) or me.attributes.new(name, 'FLOAT', 'POINT')
        a.data.foreach_set('value', val.astype(np.float32))


def build_terrain(M: Mats) -> None:
    for name, r0, r1, segs, growth, size in (('apron', APRON_R[0], APRON_R[1], 160, 1.045, APRON_R[1]),
                                             ('mid', APRON_R[1], MID_R, 192, 1.04, MID_R),
                                             ('far', MID_R, FAR_R, 160, 1.07, FAR_R)):
        xy, faces = polar_grid(r0, r1, 0, segs, growth)
        z = terrain_h(xy[:, 0], xy[:, 1])
        if name == 'apron':
            z = np.where(np.hypot(xy[:, 0], xy[:, 1]) < 7.05, 0.0, z) - 0.0
        V = np.column_stack([xy, z])
        ob = K.obj_from_arrays(f'ground_{name}', V, faces, gcoll(name), [M.grass_ground], smooth=True)
        K.planar_uv(ob, -size, -size, 2 * size, 'UVMap')
        ground_attrs(ob)
        tag(ob, lite=(name == 'apron'))
        C.log(f'terrain {name}: {K.tri_count(ob)} tris')


def build_river(M: Mats, rng) -> None:
    g = gcoll('water')
    xs = np.concatenate([np.linspace(-FAR_R, -40, 24), np.linspace(-40, 40, 81)[1:-1], np.linspace(40, FAR_R, 24)])
    nv = 6
    verts, faces, across = [], [], []
    half = 5.6
    for x in xs:
        yc = float(river_y(x))
        for j in range(nv + 1):
            t = j / nv * 2 - 1
            verts.append((x, yc + t * half, WATER_Z))
            across.append(abs(t))
    for i in range(len(xs) - 1):
        for j in range(nv):
            a = i * (nv + 1) + j
            faces.append((a, a + nv + 1, a + nv + 2, a + 1))
    V = np.asarray(verts)
    uv_u = 0.5 + 0.5 * np.arcsinh(V[:, 0] / 18.0) / np.arcsinh(FAR_R / 18.0)
    uv_v = (V[:, 1] - river_y(V[:, 0]) + half) / (2 * half)
    ob = K.obj_from_arrays('river', V, faces, g, [M.water])
    me = ob.data
    lv, _, _ = K.loop_arrays(me)
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', np.stack([uv_u[lv], uv_v[lv]], 1).astype(np.float32).ravel())
    for name, val in (('across', np.asarray(across)), ('foam', np.zeros(len(V)))):
        a = me.attributes.new(name, 'FLOAT', 'POINT')
        a.data.foreach_set('value', val.astype(np.float32))
    tag(ob, lite=False)
    # stones along both banks (the river group's neighbour: they bake into the trees/nature atlas)
    bm = bmesh.new()
    for k in range(70):
        x = rng.uniform(-60, 60)
        side = rng.choice([-1, 1])
        y = float(river_y(x)) + side * (4.4 + rng.normal(0, 0.5))
        s = 0.18 + 0.35 * rng.random() ** 2
        z = float(terrain_h(x, y)) + s * 0.1
        K.ico_blob(bm, (x, y, z), s, (1.2, 1.0, 0.6), 1, 0.1, rng)
    ob = K.obj_from_bm('river_stones', bm, gcoll('trees'), [M.river_stone], smooth=True)
    tag(ob, lite=False)


# ----------------------------------------------------------------------------- Tunewick
def house(name: str, x: float, y: float, yaw: float, w: float, d: float, floors: int, plaster: str, M: Mats, rng,
          g) -> None:
    z0 = float(min(terrain_h(x + dx, y + dy) for dx in (-w / 2, w / 2) for dy in (-d / 2, d / 2))) - 0.15
    R = Matrix.Rotation(yaw, 3, 'Z')
    o = Vector((x, y, z0))
    fh = 2.5
    H = 0.45 + floors * fh

    def at(lx, ly, lz):
        return o + R @ Vector((lx, ly, lz))

    plinth = K.box_obj(f'{name}_plinth', (w + 0.16, d + 0.16, 0.6), at(0, 0, 0.3), g, [M.cobble], R, bevel=0.03)
    K.box_uv(plinth, 1.0)
    walls = K.box_obj(f'{name}_walls', (w, d, H - 0.45), at(0, 0, 0.45 + (H - 0.45) / 2), g, [M.plaster], R)
    K.box_uv(walls, 2.0)
    K.set_face_colors(walls, [C.srgb(plaster)] * len(walls.data.polygons))
    # timber frame: corner posts, a band at each floor, braces on the long walls
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = K.box_obj(f'{name}_cp', (0.2, 0.2, H - 0.45), at(sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), 0.45 + (H - 0.45) / 2), g, [M.beam], R)
            K.box_uv(b, 1.5)
    for fl in range(floors + 1):
        zb = 0.45 + fl * fh - (0.1 if fl == floors else 0.0) + (0.12 if fl == 0 else 0.0)
        for sy in (-1, 1):
            b = K.box_obj(f'{name}_band', (w + 0.04, 0.12, 0.18), at(0, sy * (d / 2 + 0.03), zb), g, [M.beam], R)
            K.along_uv(b, R @ Vector((1, 0, 0)), 1.5)
        for sx in (-1, 1):
            b = K.box_obj(f'{name}_bandx', (0.12, d + 0.04, 0.18), at(sx * (w / 2 + 0.03), 0, zb), g, [M.beam], R)
            K.along_uv(b, R @ Vector((0, 1, 0)), 1.5)
    nwin = max(1, int(w / 2.0))
    for fl in range(floors):
        zc = 0.45 + fl * fh + 1.35
        for sy in (-1, 1):
            for i in range(nwin):
                lx = (i + 0.5) / nwin * w - w / 2
                if fl == 0 and sy == -1 and i == nwin // 2:
                    door = K.box_obj(f'{name}_door', (0.95, 0.08, 1.95), at(lx, sy * (d / 2 + 0.02), 0.45 + 0.98), g, [M.shutter], R)
                    K.set_face_colors(door, [C.srgb(['#6B4A33', '#2E6E68', '#A8483A', '#47607F'][rng.integers(4)])] * len(door.data.polygons))
                    continue
                win = K.box_obj(f'{name}_win', (0.72, 0.06, 0.82), at(lx, sy * (d / 2 + 0.02), zc), g, [M.window], R)
                frame = K.box_obj(f'{name}_sill', (0.9, 0.14, 0.08), at(lx, sy * (d / 2 + 0.05), zc - 0.45), g, [M.beam], R)
                K.box_uv(frame, 1.0)
                sh = C.srgb(['#2E8F86', '#E2694F', '#E7B24C', '#5E7FA8', '#7FA05A', '#F3E4C3'][rng.integers(6)])
                for side in (-1, 1):
                    s = K.box_obj(f'{name}_shutter', (0.34, 0.05, 0.86), at(lx + side * 0.56, sy * (d / 2 + 0.04), zc), g, [M.shutter], R)
                    K.set_face_colors(s, [sh] * len(s.data.polygons))
                if rng.random() < 0.5 and fl == 0:
                    fb = K.box_obj(f'{name}_flowers', (0.86, 0.2, 0.18), at(lx, sy * (d / 2 + 0.14), zc - 0.36), g, [M.flowers], R, bevel=0.04)
                    K.set_face_colors(fb, [C.srgb(['#E65A6E', '#F2C14E', '#F08FB0', '#FFFFFF'][rng.integers(4)])] * len(fb.data.polygons))
                del win
    # thatch roof: a thick gable with soft rounded eaves, overhanging all round
    ov, rise, th = 0.55, 0.62 * d + 0.4, 0.38
    prof = []
    for t in np.linspace(0, 1, 4):
        prof.append((-(d / 2 + ov) * (1 - t), rise * t))
    for t in np.linspace(0, 1, 4)[1:]:
        prof.append(((d / 2 + ov) * t, rise * (1 - t)))
    bm = bmesh.new()
    L = w + 2 * ov * 0.8
    outer, inner = [], []
    for (py, pz) in prof:
        k = 1.0 - 0.25 * (1 - abs(py) / (d / 2 + ov))
        outer.append((py, pz + th * k))
        inner.append((py * 0.98, pz))
    ring_pts = outer + inner[::-1]
    loops = []
    nsec = 6
    for i in range(nsec):
        t = i / (nsec - 1)
        lx = -L / 2 + L * t
        # rounded hip at the ends: pull the profile in and down near the gable ends
        hip = (1 - ss(0.0, 0.18, min(t, 1 - t)))
        loop = []
        for (py, pz) in ring_pts:
            sc = 1 - 0.18 * hip
            loop.append(bm.verts.new(at(lx * (1 - 0.06 * hip), py * sc, H + pz * (1 - 0.5 * hip) - 0.25)))
        loops.append(loop)
    n = len(ring_pts)
    for i in range(nsec - 1):
        for j in range(n):
            bm.faces.new([loops[i][j], loops[i][(j + 1) % n], loops[i + 1][(j + 1) % n], loops[i + 1][j]])
    bm.faces.new(loops[0][::-1])
    bm.faces.new(loops[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)     # outward, or the bake lights the inside
    roof = K.obj_from_bm(f'{name}_roof', bm, g, [M.thatch], smooth=True)
    del roof
    # a gable wall triangle under the roof ends (plaster), and a stone chimney
    for sx in (-1, 1):
        v = [at(sx * w / 2, -d / 2, H), at(sx * w / 2, d / 2, H), at(sx * w / 2, 0, H + rise * 0.86)]
        gw = K.obj_from_arrays(f'{name}_gable', v, [(0, 1, 2) if sx > 0 else (2, 1, 0)], g, [M.plaster])
        K.box_uv(gw, 2.0)
        K.set_face_colors(gw, [C.srgb(plaster)])
    if rng.random() < 0.75:
        cx = (rng.random() - 0.5) * w * 0.6
        ch = K.box_obj(f'{name}_chimney', (0.6, 0.6, rise + 1.1), at(cx, d * 0.12, H + (rise + 1.1) / 2 - 0.1), g, [M.cobble], R, bevel=0.03)
        K.box_uv(ch, 1.0)


HOUSES = [  # x, y, yaw (deg, 0 = front toward -y), w, d, floors, plaster
    (-48, 37, 4, 6.5, 5.0, 2, '#F4E7CF'), (-38, 39, -6, 5.5, 4.6, 1, '#F2D9B8'), (-20, 33, 3, 6.0, 4.8, 2, '#F6EBD5'),
    (-11, 36, -4, 5.0, 4.4, 1, '#EFD6A6'), (-2, 34, 2, 6.8, 5.2, 2, '#F4E3C8'), (9, 36, -3, 5.4, 4.6, 2, '#E9D7BE'),
    (19, 34, 6, 6.2, 4.8, 1, '#F7E6C6'), (44, 38, -5, 5.6, 4.6, 2, '#F1DCC0'), (56, 41, 8, 6.4, 5.0, 1, '#F3E1BF'),
    (-30, 50, 12, 6.0, 5.0, 2, '#F0D9B6'), (-14, 52, -8, 5.2, 4.6, 1, '#F6EAD2'), (2, 49, 5, 6.6, 5.2, 2, '#EED8B4'),
    (16, 51, -10, 5.4, 4.4, 2, '#F4E2C4'), (31, 53, 7, 6.0, 4.8, 1, '#F2DDBB'), (-40, 63, -14, 5.8, 4.8, 1, '#F3E4CC'),
    (-6, 66, 4, 6.2, 5.0, 2, '#F1DFC2'), (10, 70, -6, 5.6, 4.6, 1, '#F5E6CB'), (36, 68, 10, 6.0, 4.8, 2, '#EFDABB'),
    (-60, 46, 15, 5.4, 4.4, 1, '#F2E0C0'), (64, 54, -12, 5.6, 4.6, 2, '#F4E5CB'),
]


def build_town(M: Mats, rng) -> None:
    g = gcoll('town')
    for k, (x, y, yaw, w, d, fl, pl) in enumerate(HOUSES):
        house(f'house_{k}', x, y, math.radians(yaw), w, d, fl, pl, M, rng, g)
    # the stone bridge where the lane from gate A crosses (an arched deck over the river at x ≈ -30)
    bx = -30.0
    yc = float(river_y(bx))
    span = 13.0
    nseg = 16
    bm = bmesh.new()
    verts_top = []
    for i in range(nseg + 1):
        t = i / nseg
        yy = yc - span / 2 + span * t
        zz = 0.2 + 1.1 * math.sin(math.pi * t)
        verts_top.append((yy, zz))
    deck = []
    for (yy, zz) in verts_top:
        deck.append([bm.verts.new((bx + sx * 1.7, yy, zz + dz)) for sx, dz in ((-1, 0.0), (1, 0.0), (1, -0.9), (-1, -0.9))])
    for i in range(nseg):
        for j in range(4):
            bm.faces.new([deck[i][j], deck[i][(j + 1) % 4], deck[i + 1][(j + 1) % 4], deck[i + 1][j]])
    bm.faces.new(deck[0][::-1])
    bm.faces.new(deck[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    br = K.obj_from_bm('bridge_deck', bm, g, [M.cobble], smooth=False)
    del br
    for sx in (-1, 1):
        for i in range(nseg):
            (y0, z0), (y1, z1) = verts_top[i], verts_top[i + 1]
            c = Vector((bx + sx * 1.62, (y0 + y1) / 2, (z0 + z1) / 2 + 0.35))
            ang = math.atan2(z1 - z0, y1 - y0)
            b = K.box_obj('bridge_wall', (0.28, (y1 - y0) / math.cos(ang) + 0.02, 0.62), c, g, [M.cobble], Matrix.Rotation(ang, 3, 'X'))
            K.box_uv(b, 1.0)
    # the watermill: a house on the far bank with a wheel in the water
    mx = 36.0
    my = float(river_y(mx)) + 7.5
    house('mill', mx, my, math.radians(-4), 7.0, 5.6, 2, '#F2DEC0', M, rng, g)
    wheel_c = Vector((mx - 1.0, my - 4.0, WATER_Z + 1.6))
    for k in range(12):
        a = 2 * math.pi * k / 12
        R = Matrix.Rotation(a, 3, 'X')
        p = K.box_obj('mill_paddle', (0.5, 0.06, 0.9), wheel_c + R @ Vector((0, 0, 1.55)), g, [M.post], R)
        K.box_uv(p, 1.0)
    for sx in (-0.28, 0.28):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=20, radius1=2.0, radius2=2.0, depth=0.12)
        bmesh.ops.transform(bm, matrix=Matrix.Translation(wheel_c + Vector((sx, 0, 0))) @ Matrix.Rotation(math.pi / 2, 4, 'Y'), verts=bm.verts)
        r = K.obj_from_bm('mill_rim', bm, g, [M.post])
        K.box_uv(r, 1.0)
    # the Shrine of Echoes on its hill: a round white stone tower with a teal cone roof and a gold finial
    sx_, sy_ = 18.0, 104.0
    sz = float(terrain_h(sx_, sy_)) - 0.3
    v, f = K.lathe([(2.2, 0.0), (2.2, 4.2), (2.35, 4.4), (2.35, 4.7)], 16, (sx_, sy_, sz))
    tower = K.obj_from_arrays('shrine_tower', v, f, g, [M.plaster])
    K.box_uv(tower, 2.0)
    K.set_face_colors(tower, [C.srgb('#F5F0E4')] * len(tower.data.polygons))
    v, f = K.lathe([(2.9, 0.0), (2.5, 0.5), (1.4, 2.1), (0.25, 3.6), (0.05, 3.7)], 16, (sx_, sy_, sz + 4.6))
    cone = K.obj_from_arrays('shrine_roof', v, f, g, [M.shutter])
    K.set_face_colors(cone, [C.srgb('#3B8E9A')] * len(cone.data.polygons))
    knob = bmesh.new()
    bmesh.ops.create_icosphere(knob, subdivisions=1, radius=0.25)
    bmesh.ops.translate(knob, vec=Vector((sx_, sy_, sz + 8.5)), verts=knob.verts)
    K.obj_from_bm('shrine_finial', knob, g, [M.gold], smooth=True)
    for o in list(g.objects):
        tag(o, lite=False)


# ----------------------------------------------------------------------------- trees, bushes and grass
def canopy(name: str, centre: Vector, radius: float, shape: str, tint: str, M: Mats, g, rng, tris: int = 700):
    parts = []
    bm = bmesh.new()
    if shape == 'round':
        blobs = [(Vector((0, 0, 0)), 1.0)] + [(Vector((rng.normal(0, 0.55), rng.normal(0, 0.55), rng.normal(0.1, 0.35))).normalized() * 0.62, 0.62 + 0.15 * rng.random()) for _ in range(6)]
        sc = (1.0, 1.0, 0.85)
    elif shape == 'tall':
        blobs = [(Vector((0, 0, z)), 0.75 * (1 - abs(z) * 0.32)) for z in (-1.1, -0.4, 0.3, 0.95)] + [(Vector((rng.normal(0, 0.22), rng.normal(0, 0.22), float(np.clip(rng.normal(0, 0.5), -0.9, 0.9)))), 0.45) for _ in range(4)]
        sc = (0.75, 0.75, 1.0)
    else:   # bush
        blobs = [(Vector((rng.normal(0, 0.5), rng.normal(0, 0.5), 0)), 0.65 + 0.2 * rng.random()) for _ in range(4)]
        sc = (1.0, 1.0, 0.75)
    # overlapping soft clumps (no remesh: decimating a remeshed crown to a few hundred triangles left torn sheets);
    # the big blobs get a finer sphere, the small ones a coarse one
    blobs = blobs[: max(3, tris // 90)]
    for c, r in blobs:
        K.ico_blob(bm, tuple(centre + Vector((c.x * radius * sc[0], c.y * radius * sc[1], c.z * radius * sc[2]))), r * radius, sc,
                   2 if r >= 0.9 and tris >= 400 else 1, 0.05, rng)
    ob = K.obj_from_bm(name, bm, g, [M.leaf])
    co = K.mesh_np(ob)
    d = co - np.asarray(centre)
    n = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
    bump = 0.05 * radius * np.sin(co[:, 0] * 3.1 / radius * 2.2 + 1.3) * np.sin(co[:, 1] * 2.7 / radius * 2.2) * np.sin(co[:, 2] * 3.3 / radius * 2.2 + 0.4)
    K.set_co(ob, co + n * bump[:, None])
    ob.data.polygons.foreach_set('use_smooth', np.ones(len(ob.data.polygons), bool))
    jitter = np.clip(np.asarray(C.srgb(tint)) * (0.92 + 0.16 * rng.random()), 0, 1)
    K.set_face_colors(ob, [tuple(jitter)] * len(ob.data.polygons))
    return ob


TREE_TINTS = ['#5E9E45', '#6FAA4A', '#4F8F48', '#7FB14E', '#58A060', '#8DB650']


def tree(name: str, x: float, y: float, h: float, shape: str, M: Mats, g, rng, lite: bool) -> None:
    z = float(terrain_h(x, y))
    trunk_h = h * (0.42 if shape == 'round' else 0.25)
    t = K.cyl_obj(f'{name}_trunk', (x, y, z - 0.3), (x, y, z + trunk_h + h * 0.15), 0.12 + h * 0.025, 0.07 + h * 0.012, g, [M.bark], 7)
    K.along_uv(t, Vector((0, 0, 1)), 1.2)
    tag(t, lite=lite)
    if shape == 'round':
        c = canopy(f'{name}_crown', Vector((x, y, z + trunk_h + h * 0.28)), h * 0.34, 'round', TREE_TINTS[rng.integers(len(TREE_TINTS))], M, g, rng, 400)
    else:
        c = canopy(f'{name}_crown', Vector((x, y, z + trunk_h + h * 0.36)), h * 0.3, 'tall', TREE_TINTS[rng.integers(len(TREE_TINTS))], M, g, rng, 360)
    tag(c, lite=lite)


def tufts(name: str, points, M: Mats, g, rng, lite: bool) -> None:
    """Grass tufts: 6–9 bent blades each (3 triangles per blade), darker at the root, a few flower heads."""
    bm = bmesh.new()
    tip_vals, cols = [], []
    fl = bmesh.new()
    fcols = []
    for (x, y, s) in points:
        z = float(terrain_h(x, y)) if math.hypot(x, y) > 7.05 else 0.0
        tint = C.srgb(['#7DB24F', '#8CBF55', '#6CA34A', '#9AC25C'][rng.integers(4)])
        for b in range(rng.integers(5, 8)):
            a = rng.uniform(0, 2 * math.pi)
            lean = rng.uniform(0.15, 0.6)
            h = s * rng.uniform(0.18, 0.34)
            w = 0.022 * s * 1.5
            d = Vector((math.cos(a), math.sin(a), 0))
            side = Vector((-d.y, d.x, 0)) * w
            base = Vector((x, y, z - 0.01)) + d * rng.uniform(0, 0.06) * s
            mid = base + d * lean * h * 0.4 + Vector((0, 0, h * 0.55))
            tip = base + d * lean * h + Vector((0, 0, h))
            vs = [bm.verts.new(p) for p in (base - side, base + side, mid + side * 0.7, mid - side * 0.7, tip)]
            for f in ((0, 1, 2), (0, 2, 3), (3, 2, 4)):
                bm.faces.new([vs[i] for i in f])
                cols.append(tint)
            tip_vals += [0.0, 0.0, 0.55, 0.55, 1.0]
        if rng.random() < 0.18:
            fc = C.srgb(['#FFF6D8', '#F7D24A', '#F09AB8', '#FFFFFF'][rng.integers(4)])
            c = Vector((x + rng.normal(0, 0.05), y + rng.normal(0, 0.05), z + s * 0.3))
            v = [fl.verts.new(c + Vector((math.cos(k * 2.0944) * 0.04, math.sin(k * 2.0944) * 0.04, 0))) for k in range(3)]
            fl.faces.new(v)
            fcols.append(fc)
    ob = K.obj_from_bm(name, bm, g, [M.grass_blade])
    K.set_face_colors(ob, cols)
    a = ob.data.attributes.new('tip', 'FLOAT', 'POINT')
    a.data.foreach_set('value', np.asarray(tip_vals, np.float32))
    tag(ob, lite=lite)
    if fcols:
        fo = K.obj_from_bm(name + '_flowers', fl, g, [M.flowers])
        K.set_face_colors(fo, fcols)
        tag(fo, lite=lite)
    else:
        fl.free()


def build_nature(M: Mats, rng) -> None:
    g = gcoll('trees')
    spots = []
    # behind the long stand, both sides (keeping the middle open so the town shows over the crowd)
    for (x, y, h, s) in ((-17, 9, 9.5, 'round'), (-21, 3, 8.0, 'tall'), (-15, 14.5, 7.5, 'round'), (16, 10, 9.0, 'round'),
                         (21, 4, 7.5, 'tall'), (19, 14, 8.0, 'round'), (-25, -10, 9.0, 'round'), (24, -11, 8.5, 'round'),
                         (-31, -2, 7.0, 'tall'), (30, 0, 7.5, 'tall'), (-14, -22, 8.5, 'round'), (13, -24, 9.5, 'round'),
                         (-2, -33, 10.0, 'round'), (-36, -19, 8.0, 'tall'), (26, -27, 8.0, 'round'), (40, -14, 9.0, 'round'),
                         (-42, -12, 8.5, 'round'), (-35, 15, 9.0, 'round'), (36, 18, 8.0, 'tall'), (-55, 22, 10.0, 'round'),
                         (52, 26, 9.0, 'round'), (-26, 42, 8.0, 'round'), (-8, 43, 7.0, 'tall'), (24, 44, 8.5, 'round'),
                         (40, 47, 7.5, 'tall'), (-48, 54, 9.0, 'round'), (-20, 60, 8.5, 'round'), (22, 62, 9.0, 'round'),
                         (48, 62, 8.0, 'round'), (4, 82, 9.0, 'round'), (-30, 76, 8.0, 'tall'), (30, 88, 8.5, 'round'),
                         (-60, 34, 8.0, 'tall'), (62, 36, 8.5, 'round'), (-10, 26.5, 7.0, 'round'), (10, 27.5, 6.5, 'tall')):
        spots.append((x, y, h, s))
    for k, (x, y, h, s) in enumerate(spots):
        tree(f'tree_{k}', x, y, h, s, M, g, rng, lite=math.hypot(x, y) < 20)
    bushes = [(-12.6, 7.8), (12.8, 8.2), (-12.2, -6.5), (12.0, -6.4), (-9.6, 10.6), (9.8, 10.8), (-16, -15), (16, -16),
              (-6, 15.5), (6.5, 15.8), (-22, 12), (23, 11), (-28, 18.5), (29, 18), (-36, 26), (-14, 28.5), (14, 29.5), (35, 27)]
    for k, (x, y) in enumerate(bushes):
        z = float(terrain_h(x, y))
        b = canopy(f'bush_{k}', Vector((x, y, z + 0.45)), 0.95 + 0.4 * rng.random(), 'bush', TREE_TINTS[rng.integers(len(TREE_TINTS))], M, g, rng, 170)
        tag(b, lite=math.hypot(x, y) < 20)
    # grass: round the rim, at post feet, along the stands, the near apron and the river banks
    pts_near, pts_far = [], []
    for k in range(190):
        a = rng.uniform(0, 2 * math.pi)
        r = 6.75 + abs(rng.normal(0, 0.25))
        x, y = r * math.cos(a), r * math.sin(a)
        if abs(y) < GATE_HALF + 0.6 and abs(x) > 4:
            continue
        pts_near.append((x, y, rng.uniform(0.7, 1.2)))
    for k in range(200):
        x, y = rng.uniform(-17, 17), rng.uniform(-17, 17)
        r = math.hypot(x, y)
        if r < 7.2 or r > 17 or (abs(x) < 7.5 and y < -7.0) or (abs(y) < 2.6 and abs(x) > 6) or (8.0 < r < 11.3 and y > 2.5):
            continue
        pts_near.append((x, y, rng.uniform(0.8, 1.4)))
    for k in range(60):
        x = rng.uniform(-50, 50)
        y = float(river_y(x)) + rng.choice([-1, 1]) * (5.2 + abs(rng.normal(0, 2.2)))
        pts_far.append((x, y, rng.uniform(1.0, 1.7)))
    tufts('grass_near', pts_near, M, g, rng, True)
    tufts('grass_far', pts_far, M, g, rng, False)


# ----------------------------------------------------------------------------- the far mountains (panorama only)
def build_mountains(M: Mats) -> None:
    g = coll('FAR_PANO')
    segs, rings = 360, 34
    radii = np.geomspace(FAR_R - 5, 2600.0, rings)
    verts = []
    rng = np.random.default_rng(11)
    ph = rng.uniform(0, 2 * np.pi, 8)
    for r in radii:
        for s in range(segs):
            a = 2 * math.pi * s / segs
            x, y = r * math.cos(a), r * math.sin(a)
            base = float(terrain_h(x, y)) if r < FAR_R + 1 else 0.0
            k = ss(520.0, 1150.0, r)
            ridge = (0.55 + 0.45 * math.sin(a * 2 + ph[0])) * (0.6 + 0.4 * math.sin(a * 5 + ph[1])) + 0.25 * math.sin(a * 11 + ph[2]) + 0.12 * math.sin(a * 23 + ph[3])
            ridge += 0.12 * math.sin(a * 17 + ph[5] + r * 0.003) + 0.05 * math.sin(a * 31 + ph[6] - r * 0.006)
            ridge *= 0.75 + 0.25 * math.sin(r * 0.0045 + a * 3 + ph[7])
            peak = (170.0 * max(0.0, ridge) + 35.0) * k * (1 - ss(1800.0, 2600.0, r) * 0.5)
            hills = 12.0 * ss(FAR_R, 400.0, r) * (1 + math.sin(a * 7 + ph[4]) * 0.5) * (1 - k)
            verts.append((x, y, base * (1 - ss(FAR_R, 320.0, r)) + hills + peak))
    faces = []
    for i in range(rings - 1):
        for s in range(segs):
            a, b = i * segs + s, i * segs + (s + 1) % segs
            faces.append((a, a + segs, b + segs, b))
    K.obj_from_arrays('mountains', verts, faces, g, [M.mountain], smooth=True)
    # woods on the far hills (panorama only, so they cost the game nothing): clusters of soft round crowns
    V = np.asarray(verts)
    r = np.hypot(V[:, 0], V[:, 1])
    cand = np.where((r > 225) & (r < 700) & (V[:, 2] < 140))[0]
    bm = bmesh.new()
    cols = []
    for i in rng.choice(cand, size=min(len(cand), 700), replace=False):
        x, y, z = V[i]
        for _ in range(rng.integers(1, 4)):
            s = rng.uniform(3.5, 7.5)
            n0 = len(bm.faces)
            K.ico_blob(bm, (x + rng.normal(0, 6), y + rng.normal(0, 6), z + s * 0.7), s, (1, 1, 1.2), 1, 0.1, rng)
            cols += [C.srgb(['#3F6E3A', '#4C7D3F', '#365F35', '#5A8A45'][rng.integers(4)])] * (len(bm.faces) - n0)
    woods = K.obj_from_bm('far_woods', bm, g, [M.leaf], smooth=True)
    K.set_face_colors(woods, cols)


# ----------------------------------------------------------------------------- anchors and cameras
def look_quat(eye: Vector, target: Vector):
    """Blender orientation whose local +Y looks at `target` and +Z is up: after the glTF export (Y-up) the node's
    local −Z looks at the target and +Y is up, as a three.js camera expects."""
    return (target - eye).normalized().to_track_quat('Y', 'Z')


FLY = [  # eye, target, time (s), vertical fov (deg)
    ((34.0, 64.0, 34.0), (0.0, 6.0, 1.0), 0.0, 42.0),
    ((16.0, 38.0, 24.0), (0.0, 2.0, 0.8), 1.4, 42.0),
    ((-6.0, 22.0, 15.0), (0.0, 0.0, 0.8), 2.8, 40.0),
    ((-12.0, 4.0, 10.0), (0.0, 0.0, 0.8), 4.0, 38.0),  # clear of tree_0's crown at (-17, 9), above every treetop
    # in over the open front (clear of gate A's sign board), then the runtime's face-off over the player's shoulder
    ((-5.0, -8.0, 6.0), (-4.4, 0.0, 0.6), 5.0, 36.0),  # looking down at A walking in through its gate
    ((-5.4, -1.35, 1.65), (SPAWN_X, 0.0, 0.75), 6.0, 34.0),
]
REVIEW_CAMS = {  # name: eye, target, vertical fov (deg) in a 3:4 portrait frame
    'battle': ((0.0, -15.5, 1.6), (0.0, 0.0, 0.7), 40.0),
    'shoulder': ((-4.45, -1.15, 1.55), (SPAWN_X, 0.15, 0.7), 52.0),
    'establish': ((-22.0, -36.0, 21.0), (0.0, 12.0, 1.0), 50.0),
}


def build_anchors() -> dict:
    g = coll('ANCHORS')
    out = {}

    def empty(name, loc, quat=None, extras=None):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = 'ARROWS'
        e.location = loc
        if quat is not None:
            e.rotation_mode = 'QUATERNION'
            e.rotation_quaternion = quat
        for k, v in (extras or {}).items():
            e[k] = v
        g.objects.link(e)
        out[name] = e
        return e

    empty('ring_center', (0, 0, 0), extras={'ringRadius': RING_R})
    # spawns: local −Y (Blender) = the glTF/three local +Z faces the opponent
    empty('spawn_A', (-SPAWN_X, 0, 0), Matrix.Rotation(math.pi / 2, 3, 'Z').to_quaternion())
    empty('spawn_B', (SPAWN_X, 0, 0), Matrix.Rotation(-math.pi / 2, 3, 'Z').to_quaternion())
    empty('gate_A', (-RING_R - 0.25, 0, 0), Matrix.Rotation(math.pi / 2, 3, 'Z').to_quaternion())
    empty('gate_B', (RING_R + 0.25, 0, 0), Matrix.Rotation(-math.pi / 2, 3, 'Z').to_quaternion())
    empty('gate_A_start', (-11.5, 0, 0), Matrix.Rotation(math.pi / 2, 3, 'Z').to_quaternion())
    empty('gate_B_start', (11.5, 0, 0), Matrix.Rotation(-math.pi / 2, 3, 'Z').to_quaternion())
    for i, (eye, tgt, t, fov) in enumerate(FLY):
        empty(f'cam_fly_{i}', eye, look_quat(Vector(eye), Vector(tgt)), {'t': t, 'fovDeg': fov, 'target': list(tgt)})
    for name, (eye, tgt, fov) in REVIEW_CAMS.items():
        empty(f'cam_{name}', eye, look_quat(Vector(eye), Vector(tgt)), {'fovDeg': fov, 'target': list(tgt)})
    return out


# ----------------------------------------------------------------------------- build stage
def stage_build(quick: bool) -> dict:
    C.clear_scene()
    setup_scene(quick)
    info = setup_world()
    rng = np.random.default_rng(7)
    with C.Timer('materials'):
        M = Mats()
    with C.Timer('ring'):
        build_ring(M)
    with C.Timer('fence'):
        build_fence(M, rng)
        build_rim_stones(M, rng)
    with C.Timer('stands'):
        seats = build_stands(M, rng)
    with C.Timer('crowd'):
        drop_baked_crowd(M, seats, rng)
        spots = crowd_spots()
        C.log(f'crowd spots: {len(spots)} ({sum(s["lite"] for s in spots)} in Lite)')
    with C.Timer('banners'):
        build_banners(M, rng)
    with C.Timer('props'):
        build_props(rng)
    with C.Timer('terrain'):
        build_terrain(M)
        build_river(M, rng)
    with C.Timer('town'):
        build_town(M, rng)
    with C.Timer('nature'):
        build_nature(M, rng)
    with C.Timer('mountains'):
        build_mountains(M)
    build_anchors()
    stats = {g: sum(K.tri_count(o) for o in gcoll(g).objects if o.type == 'MESH') for g in GROUPS}
    stats['total'] = sum(stats.values())
    stats['hdri_rot'] = info['hdri_rot']
    C.log('triangles by group: ' + json.dumps(stats))
    if 'PH_staging' in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections['PH_staging'])
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'guild_src.blend'), compress=False)
    (OUT / 'stats_build.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    return stats


# ----------------------------------------------------------------------------- review renders (shared)
def capsule(name: str, x: float) -> bpy.types.Object:
    m, nb = new_mat('standin_grey')
    K.principled(nb, (0.5, 0.5, 0.52, 1.0), 0.6, None, 0.3)
    bm = bmesh.new()
    v, f = K.lathe([(0.0, 0.0), (0.18, 0.02), (0.28, 0.12), (0.3, 0.3), (0.3, 0.7), (0.27, 0.86), (0.18, 0.96), (0.0, 1.0)][1:-1], 16, (x, 0, 0))
    vv = [bm.verts.new(p) for p in v]
    for fc in f:
        bm.faces.new([vv[i] for i in fc])
    ob = K.obj_from_bm(name, bm, coll('REVIEW'), [m], smooth=True)
    return ob


def review_camera(name: str, res=(900, 1200)) -> bpy.types.Object:
    eye, tgt, fov = REVIEW_CAMS[name]
    cd = bpy.data.cameras.new(f'cam_{name}')
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(fov)
    cd.clip_start = 0.1
    cd.clip_end = 3000.0
    cam = bpy.data.objects.new(f'rcam_{name}', cd)
    coll('REVIEW').objects.link(cam)
    cam.location = eye
    cam.rotation_euler = (Vector(tgt) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    return cam


def hide_near(hidden: bool) -> None:
    """The battle camera hides the camera-side fence (the game hides `arena_near`): do the same in the source scene."""
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and "near" in o.data.attributes and len(o.data.polygons):
            v = np.empty(len(o.data.polygons), np.int32)
            o.data.attributes["near"].data.foreach_get("value", v)
            if v.max() > 0:
                o.hide_render = hidden


def use_gpu() -> str:
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for kind in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = kind
            prefs.refresh_devices()
            if [d for d in prefs.devices if d.type == kind]:
                for d in prefs.devices:
                    d.use = d.type == kind
                sc.cycles.device = 'GPU'
                return kind
        except Exception:
            pass
    sc.cycles.device = 'CPU'
    return 'CPU'


def stage_preview(views: list[str], samples: int) -> None:
    """Quick Cycles stills of the source scene (layout checks while building)."""
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'guild_src.blend'))
    dev = use_gpu()
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    for c in ('FAR_PANO',):
        if c in bpy.data.collections:
            bpy.data.collections[c].hide_render = False
    capsule('standin_A', -SPAWN_X)
    capsule('standin_B', SPAWN_X)
    C.log(f'preview on {dev}')
    for v in views:
        review_camera(v, (450, 600))
        hide_near(v == "battle")
        out = OUT / 'preview' / f'{v}.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        sc.render.image_settings.file_format = 'PNG'
        sc.render.filepath = str(out)
        with C.Timer(f'preview {v}'):
            bpy.ops.render.render(write_still=True)


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stages', default='build,bake,export,review')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--views', default='battle,shoulder,establish')
    ap.add_argument('--samples', type=int, default=24)
    args = ap.parse_args(C.script_args())
    C.ensure_dir(OUT)
    C.open_log(OUT / 'guild.log')
    t0 = time.time()
    stages = args.stages.split(',')
    if 'build' in stages:
        stage_build(args.quick)
    if 'preview' in stages:
        stage_preview(args.views.split(','), args.samples)
    if 'bake' in stages:
        import guild_bake
        guild_bake.stage_bake(args.quick)
    if 'sky' in stages:
        import guild_bake
        guild_bake.stage_sky(args.quick)
    if 'export' in stages:
        import guild_bake
        guild_bake.stage_export()
    if 'review' in stages:
        import guild_bake
        guild_bake.stage_review(args.quick)
    C.log(f'guild done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
