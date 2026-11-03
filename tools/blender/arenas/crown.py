"""The Crown Amphitheatre (Battle 3D's second arena): a Roman-style amphitheatre for the big tournaments.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/arenas/crown.py -- [--stages build,preview,bake,export,review] [--quick]

build    the scene in metres, Z-up (the sand at z = 0 centred on the origin, the duel ring's curb at r = 6.0): the sand
         and the ring barrier, the podium, three tiers of seats (the live crowd's front rows bare, every other row
         painted with a crowd), the gatehouses and the Patrons' box, the top gallery, the outer façade, the velarium,
         statues, urns, braziers and banners, the plaza, land, cypresses and a town, far mountains for the sky
         (crown_build.py); saves crown_src.blend
preview  quick Cycles stills of the source scene (layout checks)
bake     per atlas group: Cycles bakes albedo, light and emission into one lit atlas (crown_bake.py)
export   the game meshes (one per atlas), anchors and seats → crown_raw.glb, crown_lite_raw.glb, crown_build.json
review   Cycles renders of the source scene and of what ships, with 1 m capsule stand-ins (crown_review.py)

Everything lands in tools/blender/out/arena-crown/ (gitignored); `node tools/blender/arenas/crown.ts` ships it to
public/models/arenas/crown/ and draws the review sheet.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # tools/blender → `lib`
sys.path.insert(0, str(HERE))               # tools/blender/arenas → kit, emblem, crown_*

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from lib import common as C  # noqa: E402
from lib.nodes import NB  # noqa: E402
import kit as K  # noqa: E402
import crown_layout as L  # noqa: E402
from crown_scene import setup_scene, setup_world, use_gpu  # noqa: E402,F401  (CR.use_gpu etc.)

OUT = C.OUT_ROOT / 'arena-crown'
REVIEW = C.ROOT / 'art-review' / 'arena-crown'
SUN_DIR = Vector(L.SUN_DIR).normalized()

# Atlas groups: name → ((width, height), double-sided, 'pack' | 'planar', lite-only). One mesh, one texture each.
GROUPS = {
    'ring': ((2048, 2048), False, 'planar', False),
    'apron_w': ((2048, 1536), False, 'planar', False),
    'apron_e': ((2048, 1536), False, 'planar', False),
    'podium': ((2048, 2048), False, 'pack', False),
    'low_n': ((2048, 2048), False, 'pack', False),
    'low_s': ((2048, 2048), False, 'pack', False),
    'mid': ((2048, 2048), False, 'pack', False),
    'top': ((2048, 2048), False, 'pack', False),
    'gallery': ((1024, 1024), False, 'pack', False),
    'facade': ((2048, 2048), False, 'pack', False),
    'monuments': ((2048, 2048), True, 'pack', False),
    'props': ((2048, 2048), True, 'pack', False),
    'statues': ((1024, 1024), False, 'pack', False),
    'velarium': ((1024, 1024), True, 'pack', False),
    'plaza': ((2048, 2048), False, 'pack', False),
    'land': ((1024, 1024), False, 'planar', False),
    'outskirts': ((1024, 1024), True, 'pack', False),
    'lbowl_low': ((1024, 1024), False, 'pack', True),
    'lbowl_high': ((1024, 1024), False, 'pack', True),
    'lstatues': ((512, 512), False, 'pack', True),
}

FLY = [  # eye, target, time (s), vertical fov (deg): over the town, over the south rim, down into the bowl
    ((-85.0, -310.0, 92.0), (0.0, -10.0, 8.0), 0.0, 40.0),
    ((-48.0, -180.0, 74.0), (0.0, -4.0, 6.0), 1.5, 40.0),
    ((-14.0, -62.0, 60.0), (0.0, 6.0, 2.0), 3.0, 40.0),
    ((-7.0, -24.0, 19.0), (-1.0, 4.0, 1.0), 4.2, 38.0),
    ((-9.0, -7.5, 5.0), (0.0, 0.0, 0.6), 5.0, 36.0),
    ((-5.4, -1.35, 1.65), (L.SPAWN_X, 0.0, 0.75), 6.0, 34.0),
]
REVIEW_CAMS = {  # name: eye, target, vertical fov (deg), (w, h)
    'battle': ((-7.2, -16.8, 4.2), (0.6, 0.3, 1.5), 28.0, (1080, 1920)),
    'battle_wide': ((0.0, -17.6, 2.1), (0.0, 0.0, 1.0), 22.0, (1920, 1080)),     # the phone held sideways
    'shoulder': ((-4.45, -1.15, 1.55), (L.SPAWN_X, 0.15, 0.7), 52.0, (900, 1200)),
    'gate': ((7.5, -8.0, 1.8), (24.5, 0.0, 5.0), 50.0, (900, 1200)),
    'establish': ((-96.0, -150.0, 84.0), (0.0, 2.0, 4.0), 40.0, (900, 1200)),
    'fly0': (FLY[0][0], FLY[0][1], FLY[0][3], (900, 1600)),
}


# ----------------------------------------------------------------------------- anchors and review cameras
def look_quat(eye: Vector, target: Vector):
    """Local +Y looks at the target, +Z up: after the glTF export the node's −Z looks at it (a three.js camera)."""
    return (target - eye).normalized().to_track_quat('Y', 'Z')


def build_anchors() -> None:
    g = C.collection('ANCHORS')

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

    face_px = Matrix.Rotation(math.pi / 2, 3, 'Z').to_quaternion()       # local −Y (glTF +Z) toward +x
    face_nx = Matrix.Rotation(-math.pi / 2, 3, 'Z').to_quaternion()
    empty('ring_center', (0, 0, 0), extras={'ringRadius': L.RING_R, 'cameraRadius': L.CAMERA_R})
    empty('spawn_A', (-L.SPAWN_X, 0, 0), face_px)
    empty('spawn_B', (L.SPAWN_X, 0, 0), face_nx)
    empty('gate_A', (-L.RING_R - 0.6, 0, 0), face_px)
    empty('gate_B', (L.RING_R + 0.6, 0, 0), face_nx)
    empty('gate_A_start', (-13.0, 0, 0), face_px)
    empty('gate_B_start', (13.0, 0, 0), face_nx)
    empty('tunnel_A', (-24.3, 0, 0.55), face_px)
    empty('tunnel_B', (24.3, 0, 0.55), face_nx)
    for i, (eye, tgt, t, fov) in enumerate(FLY):
        empty(f'cam_fly_{i}', eye, look_quat(Vector(eye), Vector(tgt)), {'t': t, 'fovDeg': fov, 'target': list(tgt)})
    for name, (eye, tgt, fov, _) in REVIEW_CAMS.items():
        if not name.startswith('fly'):
            empty(f'cam_{name}', eye, look_quat(Vector(eye), Vector(tgt)), {'fovDeg': fov, 'target': list(tgt)})


def capsule(name: str, x: float) -> bpy.types.Object:
    from lib.nodes import new_mat
    import bmesh
    m, nb = new_mat('standin_grey')
    K.principled(nb, (0.5, 0.5, 0.52, 1.0), 0.6, None, 0.3)
    bm = bmesh.new()
    v, f = K.lathe([(0.18, 0.02), (0.28, 0.12), (0.3, 0.3), (0.3, 0.7), (0.27, 0.86), (0.18, 0.96)], 16, (x, 0, 0))
    vv = [bm.verts.new(p) for p in v]
    for fc in f:
        bm.faces.new([vv[i] for i in fc])
    return K.obj_from_bm(name, bm, C.collection('REVIEW'), [m], smooth=True)


def review_camera(name: str, scale: float = 1.0) -> bpy.types.Object:
    eye, tgt, fov, (w, h) = REVIEW_CAMS[name]
    cd = bpy.data.cameras.new(f'cam_{name}')
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(fov)
    cd.clip_start, cd.clip_end = 0.1, 3000.0
    cam = bpy.data.objects.new(f'rcam_{name}', cd)
    C.collection('REVIEW').objects.link(cam)
    cam.location = eye
    cam.rotation_euler = (Vector(tgt) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = int(w * scale), int(h * scale)
    sc.render.resolution_percentage = 100
    return cam


def stage_preview(views: list[str], samples: int, scale: float) -> None:
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'crown_src.blend'))
    dev = use_gpu()
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    for g, spec in GROUPS.items():
        if spec[3] and 'G_' + g in bpy.data.collections:
            bpy.data.collections['G_' + g].hide_render = True          # the Lite bowl overlaps the full one
    capsule('standin_A', -L.SPAWN_X)
    capsule('standin_B', L.SPAWN_X)
    C.log(f'preview on {dev}')
    for v in views:
        review_camera(v, scale)
        out = OUT / 'preview' / f'{v}.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        sc.render.image_settings.file_format = 'PNG'
        sc.render.filepath = str(out)
        with C.Timer(f'preview {v}'):
            bpy.ops.render.render(write_still=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stages', default='build,bake,export,review')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--views', default='battle,battle_wide,shoulder,gate,establish,fly0')
    ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--scale', type=float, default=0.5)
    ap.add_argument('--groups', default='')
    args = ap.parse_args(C.script_args())
    C.ensure_dir(OUT)
    C.open_log(OUT / 'crown.log')
    t0 = time.time()
    stages = args.stages.split(',')
    if 'build' in stages:
        import crown_build
        crown_build.stage_build(args.quick)
    if 'preview' in stages:
        stage_preview(args.views.split(','), args.samples, args.scale)
    if 'bake' in stages:
        import crown_bake
        crown_bake.stage_bake(args.quick, [g for g in args.groups.split(',') if g])
    if 'sky' in stages:
        import crown_bake
        crown_bake.stage_sky(args.quick)
    if 'export' in stages:
        import crown_export
        crown_export.stage_export()
    if 'review' in stages:
        import crown_review
        crown_review.stage_review(args.quick, args.views.split(','))
    C.log(f'crown done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
