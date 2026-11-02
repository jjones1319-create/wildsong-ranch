"""The Guild arena's bake, export and review stages (see guild.py for the overview).

Lighting ships baked: per atlas group, Cycles bakes the albedo (full size, few samples) and the diffuse light (direct +
indirect, half size, many samples, then lightly smoothed); their product, softly compressed above 0.8 and stored as
sRGB, is the group's one texture. The game draws it unlit (KHR_materials_unlit), so it looks the same on WebGL and
WebGPU and costs one texture fetch per pixel.
"""
from __future__ import annotations

import json
import math
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib.nodes import new_mat
import kit as K
import guild as G

TEX = G.OUT / 'tex'
PANO_EYE = Vector((0.0, 0.0, 1.6))
PANO_LAT = (-12.0, 78.0)
DOME_R = 400.0
SOFT_KNEE = 0.8


# ----------------------------------------------------------------------------- images
def float_image(name: str, w: int, h: int) -> bpy.types.Image:
    img = bpy.data.images.new(name, w, h, alpha=False, float_buffer=True)
    img.generated_color = (0, 0, 0, 1)
    return img


def image_array(img: bpy.types.Image) -> np.ndarray:
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def to_srgb(lin: np.ndarray) -> np.ndarray:
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


def soft_clip(x: np.ndarray) -> np.ndarray:
    """Identity below the knee, then a smooth roll-off that reaches 1.0 asymptotically (keeps cloud and plaster
    highlights from flattening at the 8-bit ceiling)."""
    k = SOFT_KNEE
    return np.where(x < k, x, k + (1 - k) * (1 - np.exp(-(x - k) / (1 - k))))


def save_srgb_png(path, lin_rgb: np.ndarray) -> None:
    """Rows bottom-up (Blender order), linear RGB → an 8-bit sRGB PNG."""
    h, w = lin_rgb.shape[:2]
    img = bpy.data.images.new(path.stem, w, h, alpha=False)
    img.colorspace_settings.name = 'sRGB'
    rgba = np.concatenate([to_srgb(soft_clip(lin_rgb)), np.ones((h, w, 1), np.float32)], -1)
    img.pixels.foreach_set(np.ascontiguousarray(rgba, np.float32).ravel())
    path.parent.mkdir(parents=True, exist_ok=True)
    img.filepath_raw = str(path)
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    C.log(f'saved {C.rel(path)} ({w}x{h})')


def blur(a: np.ndarray, passes: int = 1) -> np.ndarray:
    """A small separable [1 2 1] blur (edges clamped), repeated."""
    for _ in range(passes):
        p = np.pad(a, ((1, 1), (0, 0), (0, 0)), mode='edge')
        a = (p[:-2] + 2 * p[1:-1] + p[2:]) / 4
        p = np.pad(a, ((0, 0), (1, 1), (0, 0)), mode='edge')
        a = (p[:, :-2] + 2 * p[:, 1:-1] + p[:, 2:]) / 4
    return a


def upsample2(a: np.ndarray, h: int, w: int) -> np.ndarray:
    """Bilinear ×2 (pixel centres aligned)."""
    hh, ww = a.shape[:2]
    ys = (np.arange(h) + 0.5) / h * hh - 0.5
    xs = (np.arange(w) + 0.5) / w * ww - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, hh - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, ww - 1)
    y1 = np.clip(y0 + 1, 0, hh - 1)
    x1 = np.clip(x0 + 1, 0, ww - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]
    fx = np.clip(xs - x0, 0, 1)[None, :, None]
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return top * (1 - fy) + bot * fy


def downsample2(a: np.ndarray) -> np.ndarray:
    h, w = a.shape[:2]
    return a[: h // 2 * 2, : w // 2 * 2].reshape(h // 2, 2, w // 2, 2, -1).mean((1, 3))


# ----------------------------------------------------------------------------- joining and unwrapping
def join_group(g: str) -> bpy.types.Object:
    col = bpy.data.collections['G_' + g]
    objs = [o for o in col.objects if o.type == 'MESH']
    for o in objs:
        o.hide_set(False)
        o.hide_viewport = False
    act = objs[0]
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=act, object=act, selected_objects=objs, selected_editable_objects=objs):
            bpy.ops.object.join()
    act.name = f'arena_{g}'
    act.data.name = f'arena_{g}'
    C.log(f'joined {g}: {len(objs)} objects, {K.tri_count(act)} tris, {len(act.data.materials)} materials')
    return act


def bake_uv(g: str, ob: bpy.types.Object) -> None:
    me = ob.data
    src = me.uv_layers.get('UVMap')
    uv = me.uv_layers.new(name='BakeUV')
    me.uv_layers.active = uv
    if src is not None:
        src.active_render = True
    if g in ('ring', 'apron', 'mid', 'far', 'water'):
        a = np.empty(len(me.loops) * 2, np.float32)
        src.data.foreach_get('uv', a)
        uv.data.foreach_set('uv', a)
        return
    C.set_active(ob)
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.003, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        try:
            bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=0.0022, shape_method='CONCAVE')
        except TypeError:
            bpy.ops.uv.pack_islands(rotate=True, margin=0.0022)
        bpy.ops.object.mode_set(mode='OBJECT')
    if src is not None:
        src.active_render = True


def set_targets(ob: bpy.types.Object, img: bpy.types.Image) -> None:
    for slot in ob.material_slots:
        m = slot.material
        if m is None:
            continue
        nt = m.node_tree
        n = nt.nodes.get('BAKE_TARGET')
        if n is None:
            n = nt.nodes.new('ShaderNodeTexImage')
            n.name = 'BAKE_TARGET'
        n.image = img
        n.select = True
        nt.nodes.active = n


def run_bake(ob: bpy.types.Object, kind: str, passes: set, samples: int, margin: int) -> None:
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.hide_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    with bpy.context.temp_override(active_object=ob, object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        kw = dict(type=kind, margin=margin, margin_type='EXTEND', use_clear=True, target='IMAGE_TEXTURES', uv_layer='BakeUV',
                  use_selected_to_active=False)
        if passes:
            kw['pass_filter'] = passes
        bpy.ops.object.bake(**kw)


def bake_group(g: str, ob: bpy.types.Object, quick: bool) -> dict:
    size = G.GROUPS[g][0]
    w, h = (size, size // 4) if g == 'water' else (size, size)
    if quick:
        w, h = w // 2, h // 2
    t0 = time.time()
    alb = float_image(f'{g}_albedo', w, h)
    set_targets(ob, alb)
    if g == 'water':
        run_bake(ob, 'EMIT', set(), 4 if quick else 16, 8)
        lit = image_array(alb)[..., :3]
    else:
        run_bake(ob, "DIFFUSE", {"COLOR"}, 2 if quick else 4, 8)
        irr = float_image(f'{g}_light', w // 2, h // 2)
        set_targets(ob, irr)
        run_bake(ob, 'DIFFUSE', {'DIRECT', 'INDIRECT'}, 32 if quick else 112, 6)
        A = image_array(alb)[..., :3]
        I = blur(image_array(irr)[..., :3], 2)
        lit = A * upsample2(I, h, w)
        bpy.data.images.remove(irr)
    save_srgb_png(TEX / f'{g}.png', lit)
    save_srgb_png(TEX / f'{g}_lite.png', downsample2(lit))
    bpy.data.images.remove(alb)
    q = np.percentile(lit.max(-1), [5, 50, 95, 99.5])
    C.log(f'bake {g}: {w}x{h} in {time.time() - t0:.0f}s · lit p5/p50/p95/p99.5 = {q.round(3).tolist()}')
    return {'size': [w, h], 'seconds': round(time.time() - t0), 'p50': float(q[1]), 'p99': float(q[3])}


# ----------------------------------------------------------------------------- the sky panoramas and domes
def pano_camera(res=(4096, 1024)) -> bpy.types.Object:
    cd = bpy.data.cameras.new('pano')
    cd.type = 'PANO'
    cd.panorama_type = 'EQUIRECTANGULAR'
    cd.latitude_min, cd.latitude_max = math.radians(PANO_LAT[0]), math.radians(PANO_LAT[1])
    cd.longitude_min, cd.longitude_max = -math.pi, math.pi
    cd.clip_start, cd.clip_end = 0.5, 6000.0
    cam = bpy.data.objects.new('pano', cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = PANO_EYE
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)          # looking along +Y, up +Z (the image centre is +Y)
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    return cam


def render_pano(kind: str, show, quick: bool) -> np.ndarray:
    """Render the panorama with only `show(obj)` objects visible; returns linear RGB rows bottom-up (H, W, 3)."""
    sc = bpy.context.scene
    saved = {o.name: o.hide_render for o in sc.objects}
    for o in sc.objects:
        if o.type in ('MESH', 'CURVE'):
            o.hide_render = not show(o)
    for c in bpy.data.collections:
        c.hide_render = False
    res = (2048, 512) if quick else (4096, 1024)
    cam = pano_camera(res)
    sc.cycles.samples = 24 if quick else 48
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    path = G.OUT / f'pano_{kind}.exr'
    sc.render.filepath = str(path)
    vt = sc.view_settings.view_transform
    sc.view_settings.view_transform = 'Standard'
    with C.Timer(f'panorama {kind}'):
        bpy.ops.render.render(write_still=True)
    sc.view_settings.view_transform = vt
    img = bpy.data.images.load(str(path))
    arr = image_array(img)[..., :3].copy()
    bpy.data.images.remove(img)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in sc.objects:
        if o.name in saved:
            o.hide_render = saved[o.name]
    return arr


def split_pano(arr: np.ndarray, name: str, size: tuple[int, int]) -> None:
    """The 360° strip → two 180° halves (front centred on +Y, back on −Y), resampled to `size` (w, h)."""
    h, w = arr.shape[:2]
    q = w // 4
    front = arr[:, q:3 * q]
    back = np.concatenate([arr[:, 3 * q:], arr[:, :q]], axis=1)
    for half, a in (('front', front), ('back', back)):
        tw, th = size
        while a.shape[1] > tw:
            a = downsample2(a)
        save_srgb_png(TEX / f'{name}_{half}.png', a[..., :3])


def dome_half(name: str, half: str, image: bpy.types.Image | None) -> bpy.types.Object:
    """A 180° slice of a sphere around PANO_EYE whose UVs match the panorama half (u: −90°..+90° around its centre
    direction, v: PANO_LAT)."""
    nu, nv = 48, 16
    yaw0 = 0.0 if half == 'front' else math.pi           # the half's centre direction: +Y or −Y
    verts, uvs, faces = [], [], []
    for j in range(nv + 1):
        lat = math.radians(PANO_LAT[0] + (PANO_LAT[1] - PANO_LAT[0]) * j / nv)
        for i in range(nu + 1):
            u = i / nu
            lon = -math.pi / 2 + math.pi * u                # image left → right = turning clockwise seen from above
            az = math.pi / 2 + yaw0 - lon                   # Blender azimuth from +X (counter-clockwise)
            d = Vector((math.cos(lat) * math.cos(az), math.cos(lat) * math.sin(az), math.sin(lat)))
            verts.append(PANO_EYE + d * DOME_R)
            uvs.append((u, j / nv))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + nu + 1, a + nu + 2, a + 1))
    # a cap over the top
    top = len(verts)
    verts.append(PANO_EYE + Vector((0, 0, DOME_R)))
    uvs_cap = []
    for i in range(nu):
        a = nv * (nu + 1) + i
        faces.append((a, a + 1, top))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    uvl = me.uv_layers.new(name='BakeUV')
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    uv_arr = np.asarray(uvs + [(0.5, 1.0)], np.float32)
    # cap loops: use the top row's u at each vertex, v = 1
    loop_uv = uv_arr[lv]
    uvl.data.foreach_set('uv', loop_uv.ravel())
    del uvs_cap
    ob = bpy.data.objects.new(name, me)
    C.collection('SKY').objects.link(ob)
    if image is not None:
        ob.data.materials.append(K.emission_image_mat(f'{name}_mat', image, 'BakeUV'))
    for f in ('visible_diffuse', 'visible_glossy', 'visible_shadow', 'visible_transmission', 'visible_volume_scatter'):
        setattr(ob, f, False)
    return ob


# ----------------------------------------------------------------------------- the bake stage
def render_skies(quick: bool, in_coll, lite_flag) -> None:
    """The two sky panoramas: Full (sky, mountains, far woods, behind the far ground) and Lite (everything beyond the
    arena: the river, Tunewick, the trees past 20 m and the mid and far ground too)."""
    full = render_pano('full', lambda o: in_coll(o, {'FAR_PANO', 'G_far'}), quick)
    split_pano(full, 'sky', (2048, 1024))
    lite = render_pano('lite', lambda o: in_coll(o, {'FAR_PANO', 'G_mid', 'G_far', 'G_town', 'G_water'})
                       or (in_coll(o, {'G_trees'}) and not lite_flag(o)), quick)
    split_pano(lite, 'sky_lite', (1024, 512))


def stage_sky(quick: bool) -> None:
    """Re-render only the sky panoramas (after a change to the sky, the mountains or the HDRI) from guild_src.blend; the
    export and the ship step read the PNGs from disk."""
    bpy.ops.wm.open_mainfile(filepath=str(G.OUT / 'guild_src.blend'))
    G.use_gpu()

    def in_coll(o, names):
        return any(c.name in names for c in o.users_collection)

    def lite_flag(o):
        a = o.data.attributes.get('lite') if o.type == 'MESH' else None
        if a is None or len(a.data) == 0:
            return False
        v = np.empty(len(a.data), np.int32)
        a.data.foreach_get('value', v)
        return bool(v.max() > 0)

    render_skies(quick, in_coll, lite_flag)


def stage_bake(quick: bool) -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(G.OUT / 'guild_src.blend'))
    dev = G.use_gpu()
    C.log(f'bake on {dev}')
    TEX.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    for name in ('REVIEW',):
        if name in bpy.data.collections:
            bpy.data.collections[name].hide_render = True

    def in_coll(o, names):
        return any(c.name in names for c in o.users_collection)

    def lite_flag(o):
        a = o.data.attributes.get('lite') if o.type == 'MESH' else None
        if a is None or len(a.data) == 0:
            return False
        v = np.empty(len(a.data), np.int32)
        a.data.foreach_get('value', v)
        return bool(v.max() > 0)

    render_skies(quick, in_coll, lite_flag)
    bpy.data.collections['FAR_PANO'].hide_render = True
    for o in bpy.data.collections['FAR_PANO'].objects:
        o.hide_render = True

    stats = {}
    objs = {}
    for g in G.GROUPS:
        objs[g] = join_group(g)
        bake_uv(g, objs[g])
    for g, ob in objs.items():
        stats[g] = bake_group(g, ob, quick)
    # the domes (shown only by the export and the review)
    for name, prefix in (('sky', 'sky'), ('sky_lite', 'sky_lite')):
        for half in ('front', 'back'):
            img = bpy.data.images.load(str(TEX / f'{prefix}_{half}.png'))
            ob = dome_half(f'{name}_{half}', half, img)
            ob.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=str(G.OUT / 'guild_baked.blend'), compress=False)
    (G.OUT / 'stats_bake.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    return stats


# ----------------------------------------------------------------------------- the export stage
def face_attr(ob: bpy.types.Object, name: str) -> np.ndarray:
    a = ob.data.attributes.get(name)
    v = np.zeros(len(ob.data.polygons), np.int32)
    if a is not None and a.domain == 'FACE':
        a.data.foreach_get('value', v)
    return v


def subset(ob: bpy.types.Object, keep: np.ndarray, name: str) -> bpy.types.Object:
    """A copy of `ob` with only the faces where `keep` is true."""
    c = ob.copy()
    c.data = ob.data.copy()
    c.name = name
    c.data.name = name
    for col in ob.users_collection:
        col.objects.link(c)
    bm = bmesh.new()
    bm.from_mesh(c.data)
    bm.faces.ensure_lookup_table()
    dead = [f for f in bm.faces if not keep[f.index]]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(c.data)
    bm.free()
    c.data.update()
    return c


def finalise(ob: bpy.types.Object, group: str, lite: bool) -> None:
    """One material named for its atlas, only the bake UVs (as UVMap), no paint attributes."""
    me = ob.data
    for l in [l for l in me.uv_layers if l.name != 'BakeUV']:
        me.uv_layers.remove(l)
    me.uv_layers['BakeUV'].name = 'UVMap'
    for a in [a.name for a in me.attributes if a.name in ('Col', 'dirt', 'wet', 'tip', 'across', 'foam', 'near', 'lite')]:
        me.attributes.remove(me.attributes[a])
    for a in [a.name for a in me.color_attributes]:
        me.color_attributes.remove(me.color_attributes[a])
    tex = f'{group}_lite' if lite else group
    mat = bpy.data.materials.get(f'guild_{tex}')
    if mat is None:
        path = TEX / f'{tex}.png'
        img = bpy.data.images.load(str(path), check_existing=True)
        mat = K.emission_image_mat(f'guild_{tex}', img, 'UVMap')
        mat['atlas'] = group
        mat['doubleSided'] = G.GROUPS.get(group, (0, False))[1]
        mat.use_backface_culling = not G.GROUPS.get(group, (0, False))[1]
    me.materials.clear()
    me.materials.append(mat)


GLTF_FROM_BLENDER = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))     # (x, y, z) Blender → (x, z, −y) glTF


def to_gltf(v) -> list[float]:
    p = GLTF_FROM_BLENDER @ Vector(v)
    return [round(p.x, 4), round(p.y, 4), round(p.z, 4)]


def stage_export() -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(G.OUT / 'guild_baked.blend'))
    O = bpy.data.objects
    full, lite = [], []
    tris_full, tris_lite = {}, {}
    for g in G.GROUPS:
        ob = O[f'arena_{g}']
        near = face_attr(ob, 'near').astype(bool)
        keep_lite = face_attr(ob, 'lite').astype(bool)
        parts = [(ob, g, keep_lite)]
        if near.any():
            main, near_part = subset(ob, ~near, f'arena_{g}_main'), subset(ob, near, 'arena_near')
            ob.name = f'unused_{g}'                # (removing it leaves a stale view-layer entry the exporter trips on)
            ob.hide_render = True
            main.name = main.data.name = f'arena_{g}'
            parts = [(main, g, keep_lite[~near]), (near_part, g, keep_lite[near])]
        for part, grp, in_lite in parts:
            name = part.name
            if in_lite.any():
                lp = subset(part, in_lite, name.replace('arena_', 'lite_'))
                finalise(lp, grp, True)
                lite.append(lp)
                tris_lite[lp.name] = K.tri_count(lp)
            finalise(part, grp, False)
            full.append(part)
            tris_full[part.name] = K.tri_count(part)
    for half in ('front', 'back'):
        for prefix, dst, tri in (('sky', full, tris_full), ('sky_lite', lite, tris_lite)):
            ob = O[f'{prefix}_{half}']
            ob.hide_render = False
            img = bpy.data.images.load(str(TEX / f'{prefix}_{half}.png'), check_existing=True)
            mname = f'guild_{prefix}_{half}'
            mat = bpy.data.materials.get(mname) or K.emission_image_mat(mname, img, 'UVMap')
            mat['atlas'] = f'{prefix}_{half}'
            mat['doubleSided'] = True
            ob.data.uv_layers['BakeUV'].name = 'UVMap'
            ob.data.materials.clear()
            ob.data.materials.append(mat)
            dst.append(ob)
            tri[ob.name] = K.tri_count(ob)
    # an invisible disc over the ring floor: the runtime gives it a ShadowMaterial to catch the fighters' shadows
    segs = 64
    verts = [(0.0, 0.0, 0.004)] + [(6.3 * math.cos(2 * math.pi * i / segs), 6.3 * math.sin(2 * math.pi * i / segs), 0.004) for i in range(segs)]
    catcher = K.obj_from_arrays('shadow_catcher', verts, [(0, 1 + i, 1 + (i + 1) % segs) for i in range(segs)], C.collection('SKY'))
    catcher.data.uv_layers.new(name='UVMap')
    cm, nb = new_mat('guild_shadow_catcher')
    K.principled(nb, (0, 0, 0, 1), 1.0)
    catcher.data.materials.append(cm)
    catcher.hide_render = True
    full.append(catcher)
    lite.append(catcher)
    anchors = [o for o in O if o.type == 'EMPTY' and any(c.name == 'ANCHORS' for c in o.users_collection)]
    from lib import export as EX
    before = dict(EX.EXPORT_OPTIONS)
    EX.EXPORT_OPTIONS.update(export_normals=False, export_tangents=False, export_animations=False, export_skins=False,
                             export_image_format='NONE', export_materials='EXPORT', export_vertex_color='NONE',
                             export_all_vertex_colors=False, export_extras=True, export_apply=True)
    try:
        EX.export_glb(G.OUT / 'guild_raw.glb', full + anchors)
        EX.export_glb(G.OUT / 'guild_lite_raw.glb', lite + anchors)
    finally:
        EX.EXPORT_OPTIONS.clear()
        EX.EXPORT_OPTIONS.update(before)
    man = K.manifest()
    src = json.loads((K.HERE / 'sources.json').read_text(encoding='utf-8'))
    used = src['models']['ids'] + src['textures']['ids'] + src['hdris']['ids']
    info = {
        'units': 'metres, glTF Y-up; the ring floor at y = 0 centred on the origin',
        'ringRadius': G.RING_R,
        'anchors': {o.name: {'position': to_gltf(o.location),
                             'forward': to_gltf((o.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()) if o.name.startswith(('spawn', 'gate')) else None,
                             **({'target': to_gltf(o['target']), 'fovDeg': o['fovDeg']} if 'target' in o else {}),
                             **({'t': o['t']} if 't' in o else {})}
                    for o in anchors},
        'flyIn': [{'node': f'cam_fly_{i}', 'eye': to_gltf(e), 'target': to_gltf(t), 't': tt, 'fovDeg': f} for i, (e, t, tt, f) in enumerate(G.FLY)],
        'sun': {'direction': to_gltf(G.SUN_DIR), 'color': [1.0, 0.94, 0.84]},
        'trianglesFull': tris_full, 'trianglesLite': tris_lite,
        'sources': [{'id': a, **{k: man[a][k] for k in ('type', 'name', 'authors', 'url', 'license')}} for a in used if a in man],
    }
    (G.OUT / 'guild_build.json').write_text(json.dumps(info, indent=1), encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(G.OUT / 'guild_export.blend'), compress=False)
    C.log(f'export: full {sum(tris_full.values())} tris in {len(full)} meshes; lite {sum(tris_lite.values())} in {len(lite)}')
    return info


# ----------------------------------------------------------------------------- the review stage
def render_to(path, samples: int, denoise: bool = True) -> None:
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.filepath = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with C.Timer(f'render {path.name}'):
        bpy.ops.render.render(write_still=True)


def stage_review(quick: bool, views=('battle', 'shoulder', 'establish')) -> None:
    G.REVIEW.mkdir(parents=True, exist_ok=True)
    res = (450, 600) if quick else (600, 800)
    # 1–3: the source scene, path traced
    bpy.ops.wm.open_mainfile(filepath=str(G.OUT / 'guild_src.blend'))
    G.use_gpu()
    G.capsule('standin_A', -G.SPAWN_X)
    G.capsule('standin_B', G.SPAWN_X)
    for v in views:
        G.review_camera(v, res)
        G.hide_near(v == "battle")
        render_to(G.REVIEW / f'cycles_{v}.png', 32 if quick else 64)
    # 4: what ships, drawn unlit (emission) exactly as the game does: full and Lite from the battle camera
    bpy.ops.wm.open_mainfile(filepath=str(G.OUT / 'guild_export.blend'))
    G.use_gpu()
    sc = bpy.context.scene
    sc.world = None
    for o in sc.objects:
        if o.type == 'LIGHT':
            o.hide_render = True
    G.capsule('standin_A', -G.SPAWN_X)
    G.capsule('standin_B', G.SPAWN_X)
    # the stand-ins need light of their own: a sun matching the bake's key, plus a soft sky
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
    so.rotation_euler = (-G.SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
    for kind in ('full', 'lite'):
        for o in sc.objects:
            if o.type != 'MESH' or o.name.startswith('standin'):
                continue
            is_lite = o.name.startswith('lite_') or o.name.startswith('sky_lite')
            is_full = o.name.startswith('arena_') or (o.name.startswith('sky_') and not o.name.startswith('sky_lite'))
            o.hide_render = not ((kind == 'lite' and is_lite) or (kind == 'full' and is_full))
            if o.name in ('arena_near', 'lite_near'):
                o.hide_render = True                    # the battle camera hides the camera-side fence
            if o.hide_render is False:
                for f in ('visible_diffuse', 'visible_glossy', 'visible_shadow'):
                    setattr(o, f, False)
        G.review_camera('battle', res)
        render_to(G.REVIEW / f'shipped_{kind}_battle.png', 16, False)
        if kind == 'full':
            for v in ('shoulder', 'establish'):
                for o in sc.objects:
                    if o.name == 'arena_near':
                        o.hide_render = False
                G.review_camera(v, res)
                render_to(G.REVIEW / f'shipped_full_{v}.png', 16, False)
