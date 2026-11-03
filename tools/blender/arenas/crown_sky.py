"""The Crown Amphitheatre's sky: equirectangular panoramas rendered from above the sand (Full: the sky and the far
mountains; Lite: the trees, the town and the plaza's stalls too), split into two 180° halves, and the half-domes
that carry them in the game."""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
import kit as K
import guild_bake as GB
import crown as CR

TEX = CR.OUT / 'tex'
PANO_EYE = Vector((0.0, 0.0, 12.0))
PANO_LAT = (-16.0, 80.0)
DOME_R = 600.0


# ----------------------------------------------------------------------------- the sky
def render_pano(kind: str, show, quick: bool) -> np.ndarray:
    sc = bpy.context.scene
    saved = {o.name: o.hide_render for o in sc.objects}
    for c in bpy.data.collections:
        c.hide_render = False
    for o in sc.objects:
        if o.type in ('MESH', 'CURVE'):
            o.hide_render = not show(o)
    cd = bpy.data.cameras.new('pano')
    cd.type = 'PANO'
    cd.panorama_type = 'EQUIRECTANGULAR'
    cd.latitude_min, cd.latitude_max = math.radians(PANO_LAT[0]), math.radians(PANO_LAT[1])
    cd.longitude_min, cd.longitude_max = -math.pi, math.pi
    cd.clip_start, cd.clip_end = 0.5, 8000.0
    cam = bpy.data.objects.new('pano', cd)
    sc.collection.objects.link(cam)
    cam.location = PANO_EYE
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = (2048, 512) if quick else (4096, 1024)
    sc.render.resolution_percentage = 100
    sc.cycles.samples = 24 if quick else 64
    sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    path = CR.OUT / f'pano_{kind}.exr'
    sc.render.filepath = str(path)
    vt = sc.view_settings.view_transform
    sc.view_settings.view_transform = 'Standard'
    with C.Timer(f'panorama {kind}'):
        bpy.ops.render.render(write_still=True)
    sc.view_settings.view_transform = vt
    img = bpy.data.images.load(str(path))
    arr = GB.image_array(img)[..., :3].copy()
    bpy.data.images.remove(img)
    bpy.data.objects.remove(cam, do_unlink=True)
    for o in sc.objects:
        if o.name in saved:
            o.hide_render = saved[o.name]
    return arr


def split_pano(arr: np.ndarray, name: str, width: int) -> None:
    h, w = arr.shape[:2]
    q = w // 4
    for half, a in (('front', arr[:, q:3 * q]), ('back', np.concatenate([arr[:, 3 * q:], arr[:, :q]], axis=1))):
        while a.shape[1] > width:
            a = GB.downsample2(a)
        GB.save_srgb_png(TEX / f'{name}_{half}.png', a)


def dome_half(name: str, half: str, image) -> bpy.types.Object:
    """A 180° slice of a sphere round PANO_EYE whose UVs match the panorama half (front centred on +Y)."""
    nu, nv = 48, 16
    yaw0 = 0.0 if half == 'front' else math.pi
    verts, uvs, faces = [], [], []
    for j in range(nv + 1):
        lat = math.radians(PANO_LAT[0] + (PANO_LAT[1] - PANO_LAT[0]) * j / nv)
        for i in range(nu + 1):
            u = i / nu
            az = math.pi / 2 + yaw0 - (-math.pi / 2 + math.pi * u)
            verts.append(PANO_EYE + Vector((math.cos(lat) * math.cos(az), math.cos(lat) * math.sin(az), math.sin(lat))) * DOME_R)
            uvs.append((u, j / nv))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + nu + 1, a + nu + 2, a + 1))
    top = len(verts)
    verts.append(PANO_EYE + Vector((0, 0, DOME_R)))
    uvs.append((0.5, 1.0))
    for i in range(nu):
        a = nv * (nu + 1) + i
        faces.append((a, a + 1, top))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    me.uv_layers.new(name='BakeUV').data.foreach_set('uv', np.asarray(uvs, np.float32)[lv].ravel())
    ob = bpy.data.objects.new(name, me)
    C.collection('SKY').objects.link(ob)
    if image is not None:
        me.materials.append(K.emission_image_mat(f'{name}_mat', image, 'BakeUV'))
    for f in ('visible_diffuse', 'visible_glossy', 'visible_shadow', 'visible_transmission', 'visible_volume_scatter'):
        setattr(ob, f, False)
    return ob


def render_skies(quick: bool) -> None:
    def in_coll(o, names):
        return any(c.name in names for c in o.users_collection)
    full = render_pano('full', lambda o: in_coll(o, {'FAR_PANO', 'G_land'}), quick)
    split_pano(full, 'sky', 2048)
    lite = render_pano('lite', lambda o: in_coll(o, {'FAR_PANO', 'G_land', 'G_outskirts'}), quick)
    split_pano(lite, 'sky_lite', 1024)
