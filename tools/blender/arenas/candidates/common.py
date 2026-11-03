"""Shared helpers for the arena-candidate renders (Blender 5.2, headless). Research only: nothing here ships.

Imported by render_model.py and grand_blockout.py (both add this folder to sys.path).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CACHE = HERE.parent / '.cache'
OUT = ROOT / 'art-review' / 'arena-candidates' / 'renders'
HDRI = CACHE / 'hdris' / 'kloofendal_48d_partly_cloudy_puresky' / 'kloofendal_48d_partly_cloudy_puresky_4k.hdr'
RING_R = 6.0          # the duel ring is 12 m across
SPAWN_X = 2.3         # the two stand-ins are 4.6 m apart
CAPSULE_H = 1.0


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def set_engine(scene: bpy.types.Scene, samples: int = 32) -> str:
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    ee = scene.eevee
    for attr, val in (('taa_render_samples', samples), ('use_shadows', True), ('use_raytracing', False)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    scene.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in
        scene.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    return scene.render.engine


def world_and_sun(scene: bpy.types.Scene, sun_strength: float = 3.5, hdri_strength: float = 1.0) -> None:
    w = bpy.data.worlds.new('World')
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    env.image = bpy.data.images.load(str(HDRI))
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs['Strength'].default_value = hdri_strength
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = sun_strength
    sun.angle = math.radians(1.5)
    ob = bpy.data.objects.new('Sun', sun)
    ob.rotation_euler = (math.radians(50), 0, math.radians(35))
    scene.collection.objects.link(ob)


def flat_mat(name: str, rgb: tuple[float, float, float], rough: float = 0.6, emit: float = 0.0) -> bpy.types.Material:
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*rgb, 1)
    p.inputs['Roughness'].default_value = rough
    if emit:
        p.inputs['Emission Color'].default_value = (*rgb, 1)
        p.inputs['Emission Strength'].default_value = emit
    return m


def capsule(name: str, x: float, y: float, z: float, r: float = 0.3) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=r)
    for v in bm.verts:
        if v.co.z > 1e-5:
            v.co.z += CAPSULE_H - 2 * r
        v.co.z += r
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ob.location = (x, y, z)
    me.materials.append(flat_mat('capsule_grey', (0.55, 0.55, 0.57), 0.45))
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ring_marker(z: float) -> bpy.types.Object:
    me = bpy.data.meshes.new('ring12m')
    bm = bmesh.new()
    n = 128
    vs = []
    for i in range(n):
        a = 2 * math.pi * i / n
        vs.append((bm.verts.new((math.cos(a) * (RING_R - 0.06), math.sin(a) * (RING_R - 0.06), 0)),
                   bm.verts.new((math.cos(a) * (RING_R + 0.06), math.sin(a) * (RING_R + 0.06), 0))))
    for i in range(n):
        a, b = vs[i], vs[(i + 1) % n]
        bm.faces.new((a[0], b[0], b[1], a[1]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('ring12m', me)
    ob.location.z = z + 0.03
    me.materials.append(flat_mat('ring_white', (0.95, 0.93, 0.85), 0.8, 0.4))
    bpy.context.scene.collection.objects.link(ob)
    return ob


def stand_ins(floor_z: float) -> None:
    ring_marker(floor_z)
    capsule('spawnA', -SPAWN_X, 0, floor_z)
    capsule('spawnB', SPAWN_X, 0, floor_z)


def look_at(ob: bpy.types.Object, target: Vector) -> None:
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(name: str, loc, target, lens: float) -> bpy.types.Object:
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_fit = 'AUTO'
    cam.clip_start = 0.1
    cam.clip_end = 5000
    ob = bpy.data.objects.new(name, cam)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    look_at(ob, Vector(target))
    return ob


def render(scene: bpy.types.Scene, cam: bpy.types.Object, w: int, h: int, path: Path) -> None:
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print('rendered', path, flush=True)


def stats(skip: tuple[str, ...] = ('spawnA', 'spawnB', 'ring12m')) -> dict:
    dg = bpy.context.evaluated_depsgraph_get()
    tris, lo, hi = 0, Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for ob in bpy.context.scene.objects:
        if ob.type not in ('MESH', 'CURVE', 'META') or ob.name in skip:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        for c in ev.bound_box:
            wc = ev.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, wc))
            hi = Vector(map(max, hi, wc))
        ev.to_mesh_clear()
    imgs = [(i.name, i.size[0], i.size[1]) for i in bpy.data.images if i.size[0] and not i.name.endswith('.hdr')]
    return {'triangles': tris, 'size_m': [round(hi[i] - lo[i], 1) for i in range(3)],
            'min': [round(v, 1) for v in lo], 'max': [round(v, 1) for v in hi], 'images': imgs}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')
