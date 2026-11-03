"""Scene setup for the Crown Amphitheatre's Blender stages: Cycles settings, the CC0 sky (its own sun clipped out,
turned so its bright side matches ours) with our sun lamp, and the GPU."""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector

from lib.nodes import NB
import kit as K
import crown_layout as L

SUN_DIR = Vector(L.SUN_DIR).normalized()


def setup_scene(quick: bool) -> None:
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.unit_settings.system = 'METRIC'
    sc.cycles.samples = 32 if quick else 128
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 2
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.sample_clamp_indirect = 6.0
    try:
        sc.view_settings.view_transform = 'Khronos PBR Neutral'
    except TypeError:
        sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'


def setup_world() -> float:
    """The CC0 sky (its own sun clipped out, turned so its bright side matches ours) and our sun lamp."""
    hdr = next((K.CACHE / 'hdris' / 'kloofendal_48d_partly_cloudy_puresky').glob('*.hdr'))
    img = bpy.data.images.load(str(hdr), check_existing=True)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    j, i = np.unravel_index(np.argmax(px[..., :3].sum(-1)), px.shape[:2])
    az_sun = -2 * math.pi * (i + 0.5) / w
    rot = math.atan2(SUN_DIR.y, SUN_DIR.x) - az_sun
    wd = bpy.data.worlds.new('CrownWorld')
    bpy.context.scene.world = wd
    if wd.node_tree is None:
        wd.use_nodes = True
    nb = NB(wd.node_tree)
    wd.node_tree.nodes.clear()
    tc = nb.new('ShaderNodeTexCoord')
    mp = nb.new('ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (0, 0, rot)
    nb.link(tc.outputs['Generated'], mp.inputs['Vector'])
    env = nb.new('ShaderNodeTexEnvironment', image=img)
    nb.link(mp.outputs[0], env.inputs['Vector'])
    clip = nb.mix(1.0, env.outputs['Color'], (3.0, 3.0, 3.0, 1.0), blend='DARKEN')
    bg = nb.new('ShaderNodeBackground')
    nb.put(bg.inputs['Color'], clip)
    bg.inputs['Strength'].default_value = 1.25
    out = nb.new('ShaderNodeOutputWorld')
    nb.link(bg.outputs[0], out.inputs['Surface'])
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 3.9
    sun.angle = math.radians(2.5)
    sun.color = (1.0, 0.94, 0.84)
    so = bpy.data.objects.new('Sun', sun)
    bpy.context.scene.collection.objects.link(so)
    so.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
    return rot


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
