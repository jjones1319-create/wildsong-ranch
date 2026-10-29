"""Build one monster look (Art 2.0, ART_2_PLAN §3.1): model, rig, face sheet, painted textures, clips, export.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/monsters/build.py -- --breed puddlepup [--stages model,clips,export,review] [--quick]
        [--clips idle,walk] [--sheets turnaround,faces,textures,variant,clips]

Stages: `model` builds the mesh, rig, skin, face patches and paints the textures, then saves <look>.blend;
`clips` and later stages reload that .blend when `model` is not in the list, so clip tuning is quick.
Outputs go to tools/blender/out/<look>/ (gitignored); `tools/art/optimize.ts` moves the .glb into public/.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # tools/blender → `lib`, `monsters`

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from lib import anim as A  # noqa: E402
from lib import common as C  # noqa: E402
from lib import export as EX  # noqa: E402
from lib import face as F  # noqa: E402
from lib import mesh as M  # noqa: E402
from lib import paint as PT  # noqa: E402
from lib import render as RN  # noqa: E402
from lib import review as RV  # noqa: E402
from lib import rig as R  # noqa: E402
from lib.nodes import emission_mat, new_image, new_mat, principled_image_mat  # noqa: E402

ALL_STAGES = ['model', 'clips', 'export', 'review']
LAYERS = RV.FACE_LAYERS


def load_modules(breed: str):
    recipe = importlib.import_module(f'monsters.breeds.{breed}')
    plan = importlib.import_module(f'monsters.plans.{recipe.PLAN}')
    return recipe, plan


# ----------------------------------------------------------------------------- face materials
def face_material(name: str, sheet: bpy.types.Image, kind: str, eye_hex: str) -> bpy.types.Material:
    """UV → Mapping('cell') → the face sheet → Principled (base colour + alpha). Pupils map the mask channels."""
    m, nb = new_mat(name)
    uv = nb.coords().outputs['UV']
    mp = nb.new('ShaderNodeMapping', vector_type='POINT')
    mp.name = 'cell'
    nb.link(uv, mp.inputs['Vector'])
    tex = nb.new('ShaderNodeTexImage', image=sheet, interpolation='Linear', extension='EXTEND')
    tex.name = 'sheet'
    nb.link(mp.outputs['Vector'], tex.inputs['Vector'])
    bsdf = nb.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.35
    bsdf.inputs['Specular IOR Level'].default_value = 0.3
    if kind == 'pupil':
        # R = iris, G = pupil, B = highlight → colours, for Blender's own renders (the runtime does the same in GLSL)
        r, g, b = nb.sep_rgb(tex.outputs['Color'])
        iris = nb.rgb(C.lin(eye_hex))
        pupil = nb.rgb(C.lin(C.shade_hex(eye_hex, 0.45)))
        col = nb.mix(g, iris, pupil)
        col = nb.mix(b, col, nb.rgb((1, 1, 1)))
        alpha = nb.math('MAXIMUM', nb.math('MAXIMUM', r, g), b)
        nb.link(col, bsdf.inputs['Base Color'])
        nb.link(alpha, bsdf.inputs['Alpha'])
    else:
        nb.link(tex.outputs['Color'], bsdf.inputs['Base Color'])
        nb.link(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
    m.surface_render_method = 'BLENDED'
    m.use_backface_culling = True
    nb.output(bsdf.outputs[0])
    return m


def build_face_patches(recipe, body: bpy.types.Object, sheet: bpy.types.Image) -> dict[str, bpy.types.Object]:
    hc = Vector(recipe.P['head_c'])
    hr = recipe.P['head_r']
    objs: dict[str, bpy.types.Object] = {}
    order = {'white': 0, 'pupil': 1, 'lid': 2}
    for pname, spec in recipe.FACE_PATCHES.items():
        base, _, side = pname.partition('.')
        layers = ['white', 'pupil', 'lid'] if base == 'eye' else ['mouth']
        for layer in layers:
            lname = f'{layer}.{side}' if side else layer
            k = order.get(layer, 0)
            ob = M.sphere_patch(f'face_{lname}', hc, hr, Vector(spec['dir']), spec['half_w'], spec['half_h'],
                                grid=6, offset=0.02, roll_deg=spec.get('roll', 0.0))
            M.shrinkwrap_to(ob, body, 0.0025 + 0.0018 * k)
            mat = face_material(f'face_{lname}', sheet, layer, recipe.PALETTE['eye'])
            ob.data.materials.append(mat)
            objs[lname] = ob
    return objs


# ----------------------------------------------------------------------------- stages
def stage_model(recipe, plan, out: Path, quick: bool) -> dict:
    C.clear_scene()
    sc = bpy.context.scene
    sc.render.fps = A.FPS
    coll = C.collection('MonsterParts')
    with C.Timer('parts'):
        parts: list[bpy.types.Object] = []
        for p in recipe.parts():
            parts.extend(M.build_part(p, coll, segments=24 if quick else 32))
    mesh_cfg = dict(recipe.MESH)
    if quick:
        mesh_cfg['voxel'] = max(mesh_cfg['voxel'], 0.016)
    with C.Timer('merge'):
        body = M.merge_smooth(parts, recipe.ID, voxel=mesh_cfg['voxel'], smooth_iters=mesh_cfg['smooth_iters'],
                              smooth_factor=mesh_cfg['smooth_factor'], target_tris=mesh_cfg['target_tris'])
    M.hide_parts(parts)
    with C.Timer('uv'):
        M.smart_uv(body)
    mn, mx = M.bounds(body)
    C.log(f'bounds min {tuple(round(v, 3) for v in mn)} max {tuple(round(v, 3) for v in mx)}')

    # rig
    specs = plan.rig_specs(recipe.P)
    arm = R.build_armature(f'{recipe.ID}_rig', specs)
    R.log_axes(arm, ['root', 'hips', 'chest', 'head', 'ear.L.1', 'tail.1', 'thigh.FL', 'shin.FL', 'foot.FL'])
    with C.Timer('skin'):
        if not R.skin_auto(body, arm):
            C.log('using distance weights')
            R.skin_distance(body, arm, specs)
        R.smooth_weights(body, iterations=2, factor=0.5)
    sockets = {}
    for name, (bone, pos) in plan.sockets(recipe.P).items():
        R.add_socket(arm, name, bone, Vector(pos))
        sockets[name] = bone

    # face sheet + patches
    sheet_png = out / 'face_sheet.png'
    face_layout = F.render_face_sheet(recipe.FACE, sheet_png, samples=16 if quick else 32)
    sheet = bpy.data.images.load(str(sheet_png))
    sheet.name = f'{recipe.ID}_face'
    sheet.colorspace_settings.name = 'sRGB'
    sheet.alpha_mode = 'STRAIGHT'
    face_objs = build_face_patches(recipe, body, sheet)
    for ob in face_objs.values():
        R.parent_to_bone(ob, arm, 'head')

    # paint: base colour (and the variant sets) baked through the body's UVs
    size = 512 if quick else 1024
    images: dict[str, bpy.types.Image] = {}
    base_img = new_image(f'{recipe.ID}_base', size, alpha=False, color=(0, 0, 0, 1))
    pm = PT.build_paint_material(f'{recipe.ID}_paint', recipe.PAINT['base'], recipe.PAINT['fields'], recipe.PAINT.get('wobble', (3.0, 0.02)))
    PT.bake_emission(body, pm, base_img, out / 'base_color.png', samples=2 if quick else 4)
    images['base'] = base_img
    for vid, v in getattr(recipe, 'VARIANTS', {}).items():
        vimg = new_image(f'{recipe.ID}_{vid}', size, alpha=False, color=(0, 0, 0, 1))
        vm = PT.build_paint_material(f'{recipe.ID}_paint_{vid}', v['palette']['body'], v['fields'], recipe.PAINT.get('wobble', (3.0, 0.02)))
        PT.bake_emission(body, vm, vimg, out / f'base_color_{vid}.png', samples=2 if quick else 4)
        images[vid] = vimg
    # export material on the body
    body_mat = principled_image_mat(recipe.ID, base_img)
    tex = next(n for n in body_mat.node_tree.nodes if n.type == 'TEX_IMAGE')
    tex.name = 'base'
    body.data.materials.clear()
    body.data.materials.append(body_mat)
    # variant holders: a tiny triangle each, so the exporter embeds the texture set
    holders = []
    for vid, vimg in images.items():
        if vid == 'base':
            continue
        me = bpy.data.meshes.new(f'__variant_{vid}')
        me.from_pydata([(0, 0, -0.5), (0.001, 0, -0.5), (0, 0.001, -0.5)], [], [(0, 1, 2)])
        me.update()
        ho = bpy.data.objects.new(f'__variant_{vid}', me)
        ho.data.materials.append(principled_image_mat(f'{recipe.ID}_{vid}', vimg))
        C.link_obj(ho)
        holders.append(ho.name)

    meta = {
        'look': recipe.ID,
        'plan': recipe.PLAN,
        'heightUnits': recipe.HEIGHT_UNITS,
        'restHeight': round(mx.z, 4),
        'bounds': {'min': [round(v, 4) for v in mn], 'max': [round(v, 4) for v in mx]},
        'sockets': sockets,
        'springs': plan.SPRINGS,
        'bones': {'root': 'root', 'head': 'head', 'hips': 'hips'},
        'face': face_layout | {'layers': LAYERS, 'eyeColor': recipe.PALETTE['eye']},
        'variants': {vid: {'texture': f'{recipe.ID}_{vid}', 'eyeColor': v['palette']['eye']} for vid, v in getattr(recipe, 'VARIANTS', {}).items()},
        'holders': holders,
        'triangles': M.tri_count(body),
        'palette': recipe.PALETTE,
    }
    (out / 'model.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    blend = out / f'{recipe.ID}.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    C.log(f'saved {C.rel(blend)}')
    return meta


def load_model(recipe, out: Path) -> dict:
    blend = out / f'{recipe.ID}.blend'
    if not blend.exists():
        raise SystemExit(f'no {blend}; run the model stage first')
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    return json.loads((out / 'model.json').read_text(encoding='utf-8'))


def scene_objects(recipe) -> tuple:
    arm = bpy.data.objects[f'{recipe.ID}_rig']
    body = bpy.data.objects[recipe.ID]
    face_objs = {ln: bpy.data.objects[f'face_{ln}'] for ln in LAYERS}
    return arm, body, face_objs


def stage_clips(recipe, plan, out: Path, only: list[str] | None) -> list[A.ClipMeta]:
    arm, body, _ = scene_objects(recipe)
    # start from a clean slate so the stage is repeatable
    ad = arm.animation_data
    if ad is not None:
        for t in list(ad.nla_tracks):
            ad.nla_tracks.remove(t)
        ad.action = None
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    deform = [b.name for b in arm.data.bones if b.use_deform]
    cb = A.ClipBuilder(arm, deform)
    with C.Timer('clips'):
        clips = plan.make_clips(cb, recipe.P, only)
    missing = [c for c in plan.STAR_CLIPS if c not in [m.name for m in clips]]
    if missing and not only:
        C.log(f'WARNING missing clips: {missing}')
    meta = {m.name: m.to_json() for m in clips}
    (out / 'clips.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f'{recipe.ID}.blend'))
    return clips


def clips_from_scene(recipe) -> list[A.ClipMeta]:
    out = C.OUT_ROOT / recipe.ID
    if not (out / 'clips.json').exists():
        return []
    data = json.loads((out / 'clips.json').read_text(encoding='utf-8'))
    clips = []
    for name, d in data.items():
        act = bpy.data.actions.get(name)
        if act is None:
            continue
        m = A.ClipMeta(name=name, frames=int(round(d['seconds'] * A.FPS)), loop=d['loop'], hold=d['hold'], root_speed=d['rootSpeed'],
                       markers=[(x['name'], int(round(x['t'] * A.FPS))) for x in d['markers']],
                       faces=[(int(round(x['t'] * A.FPS)), x['face']) for x in d['faces']], action=act)
        clips.append(m)
    return clips


def stage_export(recipe, out: Path, model_meta: dict, clips: list[A.ClipMeta]) -> Path:
    arm, body, face_objs = scene_objects(recipe)
    objs = [arm, body] + list(face_objs.values())
    objs += [o for o in bpy.data.objects if o.name.startswith('socket_') or o.name.startswith('__variant_')]
    # the pupil layers' review material decodes the mask channels, which the exporter would write as a second
    # copy of the sheet; export them with the plain sheet material instead (the runtime does the decoding)
    sheet = bpy.data.images.get(f'{recipe.ID}_face')
    swapped = []
    for ln, ob in face_objs.items():
        if ln.startswith('pupil') and sheet is not None:
            prev = ob.data.materials[0]
            plain = bpy.data.materials.get(f'face_{ln}_export') or face_material(f'face_{ln}_export', sheet, 'white', recipe.PALETTE['eye'])
            ob.data.materials[0] = plain
            swapped.append((ob, prev))
    try:
        glb = EX.export_glb(out / f'{recipe.ID}.glb', objs)
    finally:
        for ob, prev in swapped:
            ob.data.materials[0] = prev
    side = {
        'look': model_meta['look'],
        'plan': model_meta['plan'],
        'version': 1,
        'heightUnits': model_meta['heightUnits'],
        'restHeight': model_meta['restHeight'],
        'bounds': model_meta['bounds'],
        'bones': model_meta['bones'],
        'sockets': model_meta['sockets'],
        'springs': model_meta['springs'],
        'face': model_meta['face'],
        'variants': model_meta['variants'],
        'palette': model_meta['palette'],
        'clips': {m.name: m.to_json() for m in clips},
    }
    EX.write_sidecar(out / f'{recipe.ID}.json', side)
    return glb


def stage_review(recipe, out: Path, model_meta: dict, clips: list[A.ClipMeta], sheets: list[str], quick: bool, only_clips: list[str] | None) -> None:
    arm, body, face_objs = scene_objects(recipe)
    rv_out = out / 'review'
    rv_out.mkdir(parents=True, exist_ok=True)
    RN.setup_eevee((480, 480), 24)
    RN.three_point_lights()
    cam = RN.make_camera('ReviewCam', ortho=True)
    body_mat = body.data.materials[0]
    base_img = bpy.data.images.get(f'{recipe.ID}_base')
    variant_images = {vid: bpy.data.images.get(f'{recipe.ID}_{vid}') for vid in model_meta.get('variants', {})}
    rv = recipe.REVIEW
    ctx = RV.ReviewCtx(look=recipe.ID, out=rv_out, arm=arm, body=body, face_objs=face_objs, face_layout=model_meta['face'],
                       clips=clips, centre=Vector(rv['centre']), size=rv['size'], head_centre=Vector(rv['head_centre']),
                       head_size=rv['head_size'], body_mat=body_mat, base_image=base_img, variant_images=variant_images, quick=quick)
    # hide the holders and sockets in renders
    for o in bpy.data.objects:
        if o.name.startswith('__variant_') or o.name.startswith('socket_'):
            o.hide_render = True
    made: list[Path] = []
    if 'turnaround' in sheets:
        made.append(RV.turnaround(ctx))
    if 'faces' in sheets:
        made.append(RV.faces(ctx))
    if 'textures' in sheets:
        made.append(RV.textures(ctx, [(l, Vector(c), s, az, el) for l, c, s, az, el in rv['texture_spots']]))
    if 'variant' in sheets:
        for vid in variant_images:
            p = RV.variant(ctx, vid)
            if p:
                made.append(p)
    if 'clips' in sheets:
        made.extend(RV.clip_strips(ctx, 8, only_clips))
    idx = RV.write_index(ctx, made)
    C.log(f'review index {C.rel(idx)}')


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--breed', required=True)
    ap.add_argument('--stages', default=','.join(ALL_STAGES))
    ap.add_argument('--quick', action='store_true', help='fewer samples, smaller textures (for iteration)')
    ap.add_argument('--clips', default='', help='only these clips (comma list)')
    ap.add_argument('--sheets', default='turnaround,faces,textures,variant,clips')
    args = ap.parse_args(C.script_args())
    stages = [s for s in args.stages.split(',') if s]
    only_clips = [c for c in args.clips.split(',') if c] or None
    sheets = [s for s in args.sheets.split(',') if s]
    recipe, plan = load_modules(args.breed)
    out = C.ensure_dir(C.OUT_ROOT / recipe.ID)
    C.open_log(out / 'build.log')
    C.log(f'build {recipe.ID} stages={stages} quick={args.quick}')
    t0 = time.time()
    if 'model' in stages:
        model_meta = stage_model(recipe, plan, out, args.quick)
    else:
        model_meta = load_model(recipe, out)
    clips: list[A.ClipMeta] = []
    if 'clips' in stages:
        clips = stage_clips(recipe, plan, out, only_clips)
    else:
        clips = clips_from_scene(recipe)
    if 'export' in stages:
        stage_export(recipe, out, model_meta, clips)
    if 'review' in stages:
        stage_review(recipe, out, model_meta, clips, sheets, args.quick, only_clips)
    C.log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
