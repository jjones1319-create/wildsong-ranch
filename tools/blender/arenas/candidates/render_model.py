"""Render one downloaded arena candidate: an establishing overview and a phone-portrait battle view.

    blender -b --factory-startup --python tools/blender/arenas/candidates/render_model.py -- \
        --name polypizza_colosseum --file <path> --width 140 [--cam-y -8.5] [--quick]

--width scales the model so its larger horizontal extent is that many metres (0 keeps it as authored).
Writes art-review/arena-candidates/renders/<name>_overview.png, <name>_battle.png and <name>.json.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=True)
    p.add_argument('--file', required=True)
    p.add_argument('--width', type=float, default=0)
    p.add_argument('--cam-y', type=float, default=-8.5)
    p.add_argument('--quick', action='store_true')
    return p.parse_args(argv)


def import_file(path: Path) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    ext = path.suffix.lower()
    if ext in ('.glb', '.gltf'):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext == '.obj':
        bpy.ops.wm.obj_import(filepath=str(path))
    elif ext == '.blend':
        with bpy.data.libraries.load(str(path), link=False) as (src, dst):
            dst.objects = list(src.objects)
        for ob in dst.objects:
            if ob is not None and ob.type not in ('CAMERA', 'LIGHT'):
                bpy.context.scene.collection.objects.link(ob)
    else:
        raise ValueError(f'unsupported: {path}')
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.type in ('CAMERA', 'LIGHT') and o.name in bpy.context.scene.objects:
            bpy.data.objects.remove(o)
    return [o for o in new if o.name in bpy.context.scene.objects]


def world_bbox(obs) -> tuple[Vector, Vector]:
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    bpy.context.view_layer.update()
    for o in obs:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return lo, hi


def normalise(obs, width: float) -> None:
    lo, hi = world_bbox(obs)
    root = bpy.data.objects.new('candidate_root', None)
    bpy.context.scene.collection.objects.link(root)
    for o in obs:
        if o.parent is None:
            o.parent = root
    size = max(hi.x - lo.x, hi.y - lo.y)
    s = width / size if width > 0 else 1.0
    root.scale = (s, s, s)
    centre = (lo + hi) / 2
    root.location = (-centre.x * s, -centre.y * s, -lo.z * s)
    bpy.context.view_layer.update()


def floor_at(x: float, y: float, top: float) -> float | None:
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, *_ = bpy.context.scene.ray_cast(dg, Vector((x, y, top + 1)), Vector((0, 0, -1)))
    return loc.z if hit else None


def main() -> None:
    a = args()
    C.reset()
    scene = bpy.context.scene
    eng = C.set_engine(scene, 16 if a.quick else 48)
    obs = import_file(Path(a.file).resolve())
    normalise(obs, a.width)
    model = C.stats()
    lo, hi = Vector(model['min']), Vector(model['max'])
    fz = floor_at(0, 0, hi.z)
    floor_z = fz if fz is not None else lo.z
    C.world_and_sun(scene)
    C.stand_ins(floor_z)
    r = max(hi.x - lo.x, hi.y - lo.y) / 2
    pct = 50 if a.quick else 100
    over = C.camera('cam_overview', (-0.62 * r, -2.05 * r, floor_z + 1.2 * r), (0, 0, floor_z + 0.05 * r), 30)
    battle = C.camera('cam_battle', (0, a.cam_y, floor_z + 1.6), (0, max(20.0, 0.6 * r), floor_z + 4.0), 22)
    C.render(scene, over, 1600 * pct // 100, 1000 * pct // 100, C.OUT / f'{a.name}_overview.png')
    C.render(scene, battle, 1080 * pct // 100, 1920 * pct // 100, C.OUT / f'{a.name}_battle.png')
    model.update({'name': a.name, 'file': a.file, 'scaled_to_width_m': a.width, 'floor_z': round(floor_z, 2),
                  'engine': eng, 'objects': len(obs)})
    C.write_json(C.OUT / f'{a.name}.json', model)
    print('STATS', model, flush=True)


if __name__ == '__main__':
    main()
