"""The Crown Amphitheatre's review renders (Cycles): the source scene path traced from every review camera, then
what ships (the exported meshes and atlases, drawn unlit exactly as the game draws them), each with grey 1 m capsule
stand-ins at the spawns lit by a key along the bake's sun. → art-review/arena-crown/cycles_*.png, shipped_*.png
"""
from __future__ import annotations

import bpy

from lib import common as C
import guild_bake as GB
import crown as CR


def _standins() -> None:
    CR.capsule('standin_A', -CR.L.SPAWN_X)
    CR.capsule('standin_B', CR.L.SPAWN_X)


def stage_review(quick: bool, views: list[str]) -> None:
    CR.REVIEW.mkdir(parents=True, exist_ok=True)
    scale = 0.5 if quick else 1.0
    bpy.ops.wm.open_mainfile(filepath=str(CR.OUT / 'crown_src.blend'))
    CR.use_gpu()
    for g, spec in CR.GROUPS.items():
        if spec[3] and 'G_' + g in bpy.data.collections:
            bpy.data.collections['G_' + g].hide_render = True
    _standins()
    for v in views:
        CR.review_camera(v, scale)
        GB.render_to(CR.REVIEW / f'cycles_{v}.png', 24 if quick else 64)
    bpy.ops.wm.open_mainfile(filepath=str(CR.OUT / 'crown_export.blend'))
    CR.use_gpu()
    sc = bpy.context.scene
    for c in bpy.data.collections:
        c.hide_render = c.name == 'FAR_PANO'
    for o in sc.objects:
        if o.type == 'LIGHT':
            o.hide_render = True
    _standins()
    w = bpy.data.worlds.new('flat')
    sc.world = w
    if w.node_tree is None:
        w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (0.75, 0.82, 0.92, 1)
    bg.inputs['Strength'].default_value = 0.6
    sun = bpy.data.lights.new('key', 'SUN')
    sun.energy = 3.5
    so = bpy.data.objects.new('key', sun)
    sc.collection.objects.link(so)
    so.rotation_euler = (-CR.SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
    for kind, shots in (('full', ('battle', 'battle_wide', 'shoulder', 'gate', 'establish')), ('lite', ('battle', 'battle_wide', 'establish'))):
        for o in sc.objects:
            if o.type != 'MESH' or o.name.startswith('standin'):
                continue
            is_lite = o.name.startswith('lite_') or o.name.startswith('sky_lite')
            is_full = o.name.startswith('arena_') or (o.name.startswith('sky_') and not o.name.startswith('sky_lite'))
            o.hide_render = not ((kind == 'lite' and is_lite) or (kind == 'full' and is_full))
            if not o.hide_render:
                for f in ('visible_diffuse', 'visible_glossy', 'visible_shadow'):
                    setattr(o, f, False)
        for v in shots:
            if v not in views:
                continue
            CR.review_camera(v, scale * 0.5)
            GB.render_to(CR.REVIEW / f'shipped_{kind}_{v}.png', 16, False)
    C.log('review done')
