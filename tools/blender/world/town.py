"""Tunewick from Ashbrook (docs/WORLD_3D.md §3), W0: the town re-assembled from the Gloamvault snapshot, to check the
placement maths against Gloamvault's own screenshots before the walkable city (C1) is built on it.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/world/town.py -- --layout <layout.json> --kit <kit_vale.glb> --out <dir> [--stages build,review] [--quick]

build   imports the Vale kit (one mesh per piece, vertex colours only), decodes its colour code into a plain colour
        attribute per (piece, paint, cloth) variant — slot = round(R·15) → the palette's sRGB colour or the building's
        paint (plaster 13, timber 2, trim 3 where 0.9 < A < 0.98) or the prop's cloth (slot 7), × (1 + 0.36(G − 0.5))
        for the variation, × mix(0.45, 1, B) for the baked AO, window panes (A < 0.5) as dark glass — then places every
        building, prop and station at location (x, −z, y), rotation z = yaw (no mirroring: Gloamvault's game_matrix),
        and lays the ground (the heightfield coloured by its slots), the road ribbons and the market slab
review  EEVEE stills from the layout's cameras (Gloamvault's three town shots, an overview, a top view) → <out>/review/

The layout comes from tools/world/town-layout.ts (`npm run art:town` runs both and builds the comparison sheet).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # tools/blender → `lib`

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from lib import common as C  # noqa: E402
from lib import render as R  # noqa: E402

# Road kinds (Land.RoadKind): 1 footpath · 2 field track · 3 cart road · 4 flagstones · 5 boards.
ROAD_COLOUR = {1: '#8a7552', 2: '#7d6646', 3: '#6b5538', 4: '#b3ada0', 5: '#9c7a4e'}
GLASS = '#26313a'


def lin(h: str) -> np.ndarray:
    return np.array(C.lin_rgb(h), dtype=np.float32)


# ----------------------------------------------------------------------------- the kit
def import_kit(path: Path) -> dict[str, bpy.types.Mesh]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes: dict[str, bpy.types.Mesh] = {}
    for o in set(bpy.data.objects) - before:
        if o.type == 'MESH':
            meshes[o.name] = o.data
            o.data.use_fake_user = True
    for o in set(bpy.data.objects) - before:
        bpy.data.objects.remove(o, do_unlink=True)
    C.log(f'kit: {len(meshes)} pieces from {path.name}')
    return meshes


def decode(mesh: bpy.types.Mesh, palette: np.ndarray, paint: list | None, cloth: int | None) -> bpy.types.Mesh:
    """A copy of a kit mesh with its colour code turned into a plain linear colour attribute 'Col'."""
    src = mesh.color_attributes[0]
    n = len(src.data)
    raw = np.empty(n * 4, dtype=np.float32)
    src.data.foreach_get('color', raw)
    raw = raw.reshape(n, 4)
    slot = np.clip(np.rint(raw[:, 0] * 15).astype(np.int32), 0, 15)
    var, ao, alpha = raw[:, 1], raw[:, 2], raw[:, 3]
    col = palette[slot].copy()
    if cloth is not None and cloth >= 0:
        col[slot == 7] = palette[cloth]
    if paint:
        walls, timbers, trims = paint
        if walls:
            col[slot == 13] = lin(walls)
        if timbers:
            col[slot == 2] = lin(timbers)
        if trims:
            col[(slot == 3) & (alpha > 0.9) & (alpha < 0.98)] = lin(trims)
    col *= (1.0 + 0.36 * (var - 0.5))[:, None]
    col *= (0.45 + 0.55 * ao)[:, None]
    col[alpha < 0.5] = lin(GLASS)
    out = mesh.copy()
    attr = out.color_attributes.new('Col', 'FLOAT_COLOR', src.domain)
    rgba = np.concatenate([col, np.ones((n, 1), dtype=np.float32)], axis=1)
    attr.data.foreach_set('color', rgba.ravel())
    return out


def vc_material() -> bpy.types.Material:
    m = bpy.data.materials.new('TownVC')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = 'Col'
    nt.links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.9
    for name in ('Specular IOR Level', 'Specular'):
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = 0.15
            break
    return m


def with_material(mesh: bpy.types.Mesh, mat: bpy.types.Material) -> bpy.types.Mesh:
    mesh.materials.clear()
    mesh.materials.append(mat)
    return mesh


# ----------------------------------------------------------------------------- the ground, roads and slab
def ground_mesh(layout: dict, out: Path, palette: np.ndarray, mat: bpy.types.Material) -> bpy.types.Object:
    g = layout['ground']
    nx, nz, step = g['nx'], g['nz'], g['step']
    h = np.fromfile(out / g['heights'], dtype='<f4').reshape(nz, nx)
    s = np.fromfile(out / g['slots'], dtype=np.uint8).reshape(nz, nx)
    xs = g['x0'] + np.arange(nx) * step
    zs = g['z0'] + np.arange(nz) * step
    X, Z = np.meshgrid(xs, zs)
    verts = np.stack([X.ravel(), -Z.ravel(), h.ravel()], axis=1)
    i = np.arange(nx - 1)
    j = np.arange(nz - 1)
    I, J = np.meshgrid(i, j)
    a = (J * nx + I).ravel()
    faces = np.stack([a, a + nx, a + nx + 1, a + 1], axis=1)   # wound so the normals face +Z after the −z flip
    me = bpy.data.meshes.new('ground')
    me.from_pydata(verts.tolist(), [], faces.tolist())
    col = palette[s.ravel()] * 0.92
    attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    attr.data.foreach_set('color', np.concatenate([col, np.ones((len(col), 1), np.float32)], axis=1).ravel())
    with_material(me, mat)
    ob = bpy.data.objects.new('ground', me)
    C.link_obj(ob)
    C.log(f'ground: {nx}×{nz} points')
    return ob


def quads_mesh(name: str, quads: list[dict], mat: bpy.types.Material) -> bpy.types.Object:
    verts, faces, cols = [], [], []
    for q in quads:
        k = len(verts)
        for (x, y, z) in q['c']:
            verts.append((x, -z, y))
        faces.append((k, k + 2, k + 3, k + 1))
        c = list(lin(ROAD_COLOUR.get(q['kind'], ROAD_COLOUR[3]))) + [1.0]
        cols.extend([c] * 4)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    # Faces seen from above: flip any that came out facing down.
    me.update()
    for p in me.polygons:
        if p.normal.z < 0:
            p.flip()
    attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    attr.data.foreach_set('color', np.array(cols, dtype=np.float32).ravel())
    with_material(me, mat)
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


# ----------------------------------------------------------------------------- stages
def build(layout: dict, kit: Path, out: Path) -> None:
    C.clear_scene()
    palette = np.array([C.lin_rgb(h) for h in layout['palette']], dtype=np.float32)
    meshes = import_kit(kit)
    mat = vc_material()
    variants: dict[str, bpy.types.Mesh] = {}
    town = C.collection('Town')
    for p in layout['placements']:
        paint = p.get('paint')
        cloth = p.get('cloth')
        key = f"{p['piece']}|{paint}|{cloth}"
        if key not in variants:
            variants[key] = with_material(decode(meshes[p['piece']], palette, paint, cloth), mat)
        ob = bpy.data.objects.new(p.get('id') or p['piece'], variants[key])
        ob.location = (p['x'], -p['z'], p['y'])
        ob.rotation_euler = (0.0, 0.0, math.radians(p['yaw']))
        ob.scale = (p['scale'],) * 3
        C.link_obj(ob, town)
    C.log(f"placed {len(layout['placements'])} ({len(variants)} mesh variants): {layout['counts']}")
    ground_mesh(layout, out, palette, mat)
    quads_mesh('roads', [q for r in layout['roads'] for q in r['quads']], mat)
    quads_mesh('market', layout['slab'], mat)


def light(layout: dict) -> None:
    sc = bpy.context.scene
    w = sc.world
    for n in w.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs['Color'].default_value = (*C.lin_rgb(layout['sky']), 1.0)
            n.inputs['Strength'].default_value = 0.9
    sun = bpy.data.lights.new('sun', 'SUN')
    sun.energy = 3.6
    sun.angle = math.radians(1.5)
    ob = bpy.data.objects.new('sun', sun)
    dx, dy, dz = layout['sunDir']
    travel = Vector((dx, -dz, dy)).normalized()
    ob.rotation_euler = travel.to_track_quat('-Z', 'Y').to_euler()
    C.link_obj(ob)


def review(layout: dict, out: Path, quick: bool) -> None:
    sc = R.setup_eevee(res=(1170, 540), samples=8 if quick else 32, transparent=False)
    light(layout)
    cam_data = bpy.data.cameras.new('cam')
    cam = bpy.data.objects.new('cam', cam_data)
    C.link_obj(cam)
    sc.camera = cam
    cam_data.clip_end = 2000
    for c in layout['cameras']:
        fx, fy, fz = c['from']
        tx, ty, tz = c['to']
        cam.location = (fx, -fz, fy)
        if c.get('ortho'):
            cam_data.type = 'ORTHO'
            cam_data.ortho_scale = c['ortho']
            cam.rotation_euler = (0.0, 0.0, 0.0)        # straight down, north (game −z = Blender +y) up
            sc.render.resolution_x, sc.render.resolution_y = (1100, 1100)
        else:
            cam_data.type = 'PERSP'
            cam_data.sensor_fit = 'VERTICAL'
            cam_data.angle_y = math.radians(c['fovY'])
            d = Vector((tx - fx, -(tz - fz), ty - fy))
            cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
            sc.render.resolution_x, sc.render.resolution_y = (1170, 540)
        path = R.render_png(out / 'review' / f"{c['name']}.png")
        C.log(f'rendered {C.rel(path)}')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', required=True)
    ap.add_argument('--kit', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--stages', default='build,review')
    ap.add_argument('--quick', action='store_true')
    a = ap.parse_args(C.script_args())
    out = Path(a.out)
    C.open_log(out / 'town.log')
    layout = json.loads(Path(a.layout).read_text(encoding='utf-8'))
    stages = a.stages.split(',')
    with C.Timer('build'):
        build(layout, Path(a.kit), out)
    if 'review' in stages:
        with C.Timer('review'):
            review(layout, out, a.quick)


main()
