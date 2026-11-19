"""render.py — the review render set (11-ART-PIPELINE §8) shared by every build script.

`Stage()` sets up Eevee (Workbench if Eevee cannot start headless), a dark world, a key / fill / rim / back light set,
a platform disc and a camera. Its methods render the standard views into a folder: the card view and its 200-px read,
a turntable, an orthographic front/side/back sheet, close-ups, and any named shot. `grid_sheet()` tiles PNGs into one
contact sheet so a matrix (species × class, slots, clips) reads in one image.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Vector

from common import log


def _engine_ids():
    return [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]


class Stage:
    def __init__(self, out_dir, size=1024, quick=False, platform=True, world=(0.012, 0.013, 0.02)):
        self.out = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.sc = bpy.context.scene
        self.quick = quick
        self.size = size
        ids = _engine_ids()
        eng = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in ids else ('BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in ids else 'BLENDER_WORKBENCH')
        self.sc.render.engine = eng
        if eng.startswith('BLENDER_EEVEE'):
            try:
                self.sc.eevee.taa_render_samples = 8 if quick else 32
            except Exception:
                pass
        self.sc.render.resolution_x = self.sc.render.resolution_y = size
        self.sc.render.resolution_percentage = 100
        self.sc.render.film_transparent = False
        self.sc.render.image_settings.file_format = 'PNG'
        self.sc.render.image_settings.color_mode = 'RGBA'
        self.sc.view_settings.view_transform = 'Standard'
        w = bpy.data.worlds.get('GV_World') or bpy.data.worlds.new('GV_World')
        self.sc.world = w
        w.use_nodes = True
        bg = w.node_tree.nodes.get('Background')
        bg.inputs[0].default_value = (*world, 1)
        bg.inputs[1].default_value = 1.0
        # a .blend saved after a review (hero_body.blend) still holds the last stage: clear it, or every light doubles
        old = bpy.data.collections.get('GV_Stage')
        if old is not None:
            for ob in list(old.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(old)
        self.col = bpy.data.collections.new('GV_Stage')
        if self.col.name not in self.sc.collection.children:
            self.sc.collection.children.link(self.col)
        self.platform = []
        if platform:
            self.platform.append(self._disc('GV_Platform', 0.0, 1.6, 0.0, (0.035, 0.05, 0.045)))
            self.platform.append(self._disc('GV_PlatformRing', 1.6, 1.68, 0.002, (0.33, 0.27, 0.12)))
        # energies chosen so a white diffuse facing the key lands on the third toon step and the turn-away faces fall
        # through the lower ones (a sun of strength E gives E / π on a white diffuse)
        self._light('Key', (math.radians(50), math.radians(10), math.radians(35)), 2.3, (1.0, 0.95, 0.87))
        self._light('Fill', (math.radians(60), 0, math.radians(-55)), 0.55, (0.66, 0.74, 1.0))
        self._light('Rim', (math.radians(-55), 0, math.radians(-145)), 1.5, (0.55, 0.85, 1.0))
        self._light('Back', (math.radians(-50), 0, math.radians(150)), 0.7, (0.8, 0.85, 1.0))
        cam = bpy.data.cameras.new('GV_Cam')
        self.cam = bpy.data.objects.new('GV_Cam', cam)
        self.col.objects.link(self.cam)
        self.sc.camera = self.cam
        log('stage', eng, size)

    def _disc(self, name, r_in, r_out, z, rgb, segs=72):
        me = bpy.data.meshes.new(name)
        if r_in == 0:
            vs = [(r_out * math.cos(2 * math.pi * i / segs), r_out * math.sin(2 * math.pi * i / segs), z) for i in range(segs)]
            fs = [tuple(range(segs))]
        else:
            vs, fs = [], []
            for i in range(segs):
                a = 2 * math.pi * i / segs
                vs += [(r_out * math.cos(a), r_out * math.sin(a), z), (r_in * math.cos(a), r_in * math.sin(a), z)]
            for i in range(segs):
                j = (i + 1) % segs
                fs.append((2 * i, 2 * i + 1, 2 * j + 1, 2 * j))
        me.from_pydata(vs, [], fs)
        me.update()
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        o = nt.nodes.new('ShaderNodeOutputMaterial')
        e = nt.nodes.new('ShaderNodeEmission')
        e.inputs[0].default_value = (*rgb, 1)
        nt.links.new(e.outputs[0], o.inputs[0])
        me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        self.col.objects.link(ob)
        return ob

    def _light(self, name, rot, energy, color):
        ld = bpy.data.lights.get('GV_' + name) or bpy.data.lights.new('GV_' + name, 'SUN')
        ld.energy = energy
        ld.color = color
        ld.angle = math.radians(4)
        ob = bpy.data.objects.new('GV_' + name, ld)
        self.col.objects.link(ob)
        ob.rotation_euler = rot
        return ob

    def show_platform(self, on):
        for p in self.platform:
            p.hide_render = not on

    def camera(self, loc, target, lens=50, ortho=None):
        self.cam.location = Vector(loc)
        d = Vector(target) - self.cam.location
        self.cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        self.cam.data.lens = lens
        if ortho:
            self.cam.data.type = 'ORTHO'
            self.cam.data.ortho_scale = ortho
        else:
            self.cam.data.type = 'PERSP'

    def shot(self, name, size=None):
        if size:
            self.sc.render.resolution_x = self.sc.render.resolution_y = size
        path = os.path.join(self.out, name)
        self.sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        if size:
            self.sc.render.resolution_x = self.sc.render.resolution_y = self.size
        return path

    # -------- the standard views; `h` is the subject's height in metres, centred on x = y = 0
    def card(self, h=1.8, name='card_view.png'):
        k = h / 1.8
        self.camera((-1.95 * k, -2.45 * k, 1.45 * k), (0.04 * k, 0, 0.97 * k), lens=55)
        path = self.shot(name)
        small = os.path.join(self.out, name.replace('.png', '_200.png'))
        img = bpy.data.images.load(path)
        img.scale(200, 200)
        img.filepath_raw = small
        img.file_format = 'PNG'
        img.save()
        bpy.data.images.remove(img)
        return path

    def turntable(self, h=1.8, n=24, prefix='turntable'):
        k = h / 1.8
        paths = []
        for i in range(n):
            a = 2 * math.pi * i / n
            r = 3.9 * k
            self.camera((-r * math.sin(a), -r * math.cos(a), 1.35 * k), (0, 0, 0.92 * k), lens=50)
            paths.append(self.shot('%s_%03d.png' % (prefix, i)))
        return paths

    def ortho_sheet(self, h=1.8, name='ortho_sheet.png', views=(('front', (0, -6, 0)), ('side', (-6, 0, 0)), ('back', (0, 6, 0)))):
        self.show_platform(False)
        self.sc.render.film_transparent = True
        parts = []
        for vname, loc in views:
            self.camera((loc[0], loc[1], h / 2), (0, 0, h / 2), ortho=h * 1.15)
            p = self.shot('_ortho_%s.png' % vname)
            parts.append(load_pixels(p))
            os.remove(p)
        sheet = np.concatenate(parts, axis=1)
        bgc = np.array([0.012, 0.013, 0.02, 1.0], dtype=np.float32)
        a = sheet[..., 3:4]
        sheet = sheet * a + bgc * (1 - a)
        sheet[..., 3] = 1.0
        save_pixels(os.path.join(self.out, name), sheet)
        self.sc.render.film_transparent = False
        self.show_platform(True)
        return os.path.join(self.out, name)


def load_pixels(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return px


def save_pixels(path, px):
    h, w, _ = px.shape
    img = bpy.data.images.new('gv_tmp', w, h, alpha=True)
    img.pixels = px.ravel().tolist()
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def grid_sheet(paths, out_path, cols, cell=None, bg=(0.012, 0.013, 0.02)):
    """Tiles PNGs (same size, or scaled to `cell` px) into one sheet, row-major, rows top to bottom."""
    imgs = []
    for p in paths:
        img = bpy.data.images.load(p)
        if cell:
            img.scale(cell, cell)
        w, h = img.size
        px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
        bpy.data.images.remove(img)
        imgs.append(px)
    h, w, _ = imgs[0].shape
    rows = (len(imgs) + cols - 1) // cols
    sheet = np.zeros((rows * h, cols * w, 4), dtype=np.float32)
    sheet[..., :3] = bg
    sheet[..., 3] = 1.0
    for i, px in enumerate(imgs):
        r, c = divmod(i, cols)
        # blender pixel rows run bottom-up: the first row of the sheet goes at the top
        y0 = (rows - 1 - r) * h
        sheet[y0:y0 + h, c * w:(c + 1) * w] = px[:h, :w]
    save_pixels(out_path, sheet)
    return out_path
