"""Review rendering (Blender 5.2): EEVEE setup, framing cameras, three-point light, PNG stills and contact
sheets composed in numpy (no ffmpeg needed for stills)."""
from __future__ import annotations

import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

from . import common as C


def setup_eevee(res: tuple[int, int] = (512, 512), samples: int = 24, transparent: bool = True) -> bpy.types.Scene:
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.fps = 30
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.render.image_settings.color_depth = '8'
    sc.render.film_transparent = transparent
    sc.render.use_persistent_data = True
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.view_settings.look = 'None'
    except TypeError:
        pass
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_shadows = True
    sc.eevee.shadow_resolution_scale = 1.0
    sc.eevee.use_raytracing = False
    sc.render.filter_size = 1.3
    w = bpy.data.worlds.get('ReviewWorld') or bpy.data.worlds.new('ReviewWorld')
    sc.world = w
    if w.node_tree is None:
        w.use_nodes = True
    for n in w.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs['Color'].default_value = (0.55, 0.6, 0.7, 1)
            n.inputs['Strength'].default_value = 0.35
    return sc


def three_point_lights() -> list[bpy.types.Object]:
    out = []
    for name, (az, el), energy, color in (
        ('Key', (-35, 40), 3.2, (1.0, 0.96, 0.9)),
        ('Fill', (60, 20), 1.1, (0.85, 0.9, 1.0)),
        ('Rim', (160, 35), 2.0, (1.0, 0.9, 0.8)),
    ):
        ld = bpy.data.lights.new(name, 'SUN')
        ld.energy = energy
        ld.color = color
        ld.angle = math.radians(8)
        lo = bpy.data.objects.new(name, ld)
        C.link_obj(lo)
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        lo.location = d * 6
        lo.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        out.append(lo)
    return out


def make_camera(name: str = 'ReviewCam', ortho: bool = True) -> bpy.types.Object:
    cd = bpy.data.cameras.new(name)
    cd.type = 'ORTHO' if ortho else 'PERSP'
    cd.lens = 85
    cd.clip_start = 0.01
    cd.clip_end = 100
    cam = bpy.data.objects.new(name, cd)
    C.link_obj(cam)
    bpy.context.scene.camera = cam
    return cam


def aim_camera(cam: bpy.types.Object, centre: Vector, azimuth_deg: float, elevation_deg: float, size: float,
               distance: float = 6.0) -> None:
    """Point an ortho camera at `centre` from the front (azimuth 0 = the monster's face, 90 = its left side),
    framing a box of `size` metres."""
    a, e = math.radians(azimuth_deg), math.radians(elevation_deg)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = centre + d * distance
    cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    cam.data.ortho_scale = size
    if cam.data.type == 'PERSP':
        cam.data.lens = 85
        cam.location = centre + d * (size * 2.2)


def render_png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


# ----------------------------------------------------------------------------- contact sheets
_FONT = {
    'A': ['01110', '10001', '10001', '11111', '10001', '10001', '10001'],
    'B': ['11110', '10001', '10001', '11110', '10001', '10001', '11110'],
    'C': ['01110', '10001', '10000', '10000', '10000', '10001', '01110'],
    'D': ['11110', '10001', '10001', '10001', '10001', '10001', '11110'],
    'E': ['11111', '10000', '10000', '11110', '10000', '10000', '11111'],
    'F': ['11111', '10000', '10000', '11110', '10000', '10000', '10000'],
    'G': ['01110', '10001', '10000', '10111', '10001', '10001', '01111'],
    'H': ['10001', '10001', '10001', '11111', '10001', '10001', '10001'],
    'I': ['01110', '00100', '00100', '00100', '00100', '00100', '01110'],
    'J': ['00111', '00010', '00010', '00010', '00010', '10010', '01100'],
    'K': ['10001', '10010', '10100', '11000', '10100', '10010', '10001'],
    'L': ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
    'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001'],
    'N': ['10001', '10001', '11001', '10101', '10011', '10001', '10001'],
    'O': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'],
    'P': ['11110', '10001', '10001', '11110', '10000', '10000', '10000'],
    'Q': ['01110', '10001', '10001', '10001', '10101', '10010', '01101'],
    'R': ['11110', '10001', '10001', '11110', '10100', '10010', '10001'],
    'S': ['01111', '10000', '10000', '01110', '00001', '00001', '11110'],
    'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
    'U': ['10001', '10001', '10001', '10001', '10001', '10001', '01110'],
    'V': ['10001', '10001', '10001', '10001', '10001', '01010', '00100'],
    'W': ['10001', '10001', '10001', '10101', '10101', '10101', '01010'],
    'X': ['10001', '10001', '01010', '00100', '01010', '10001', '10001'],
    'Y': ['10001', '10001', '01010', '00100', '00100', '00100', '00100'],
    'Z': ['11111', '00001', '00010', '00100', '01000', '10000', '11111'],
    '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
    '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
    '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
    '3': ['11110', '00001', '00001', '01110', '00001', '00001', '11110'],
    '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
    '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
    '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
    '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
    '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
    '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
    '_': ['00000', '00000', '00000', '00000', '00000', '00000', '11111'],
    '-': ['00000', '00000', '00000', '11111', '00000', '00000', '00000'],
    '.': ['00000', '00000', '00000', '00000', '00000', '01100', '01100'],
    ':': ['00000', '01100', '01100', '00000', '01100', '01100', '00000'],
    '/': ['00001', '00010', '00010', '00100', '01000', '01000', '10000'],
    ' ': ['00000', '00000', '00000', '00000', '00000', '00000', '00000'],
    '%': ['11001', '11010', '00010', '00100', '01000', '01011', '10011'],
}


def draw_text(canvas: np.ndarray, x: int, y: int, text: str, scale: int = 2, color=(0.1, 0.1, 0.12)) -> None:
    """Draw uppercase text onto an RGBA float canvas (rows top-down)."""
    h, w = canvas.shape[:2]
    cx = x
    for ch in text.upper():
        g = _FONT.get(ch)
        if g is None:
            g = _FONT[' ']
        for r, row in enumerate(g):
            for c, bit in enumerate(row):
                if bit == '1':
                    y0 = y + r * scale
                    x0 = cx + c * scale
                    if 0 <= y0 < h - scale and 0 <= x0 < w - scale:
                        canvas[y0:y0 + scale, x0:x0 + scale, :3] = color
                        canvas[y0:y0 + scale, x0:x0 + scale, 3] = 1.0
        cx += 6 * scale


def load_rgba(path: Path) -> np.ndarray:
    """A PNG as an (H, W, 4) float array with rows top-down."""
    img = bpy.data.images.load(str(path))
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    arr = buf.reshape(h, w, 4)[::-1].copy()
    return arr


def save_rgba(path: Path, arr: np.ndarray) -> None:
    h, w = arr.shape[:2]
    img = bpy.data.images.new('sheet_tmp', width=w, height=h, alpha=True)
    img.colorspace_settings.name = 'sRGB'
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1], dtype=np.float32).ravel())
    path.parent.mkdir(parents=True, exist_ok=True)
    img.filepath_raw = str(path)
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def contact_sheet(cells: list[tuple[Path, str]], cols: int, out: Path, cell: tuple[int, int] | None = None,
                  bg=(0.86, 0.87, 0.89), label_h: int = 22, title: str | None = None) -> Path:
    """Tile PNGs (composited over a neutral background) with a label under each, into one PNG."""
    imgs = [load_rgba(p) for p, _ in cells]
    if cell is None:
        cell = (max(i.shape[1] for i in imgs), max(i.shape[0] for i in imgs))
    cw, ch = cell
    rows = (len(cells) + cols - 1) // cols
    top = 28 if title else 0
    canvas = np.zeros((top + rows * (ch + label_h), cols * cw, 4), dtype=np.float32)
    canvas[..., :3] = bg
    canvas[..., 3] = 1.0
    if title:
        draw_text(canvas, 8, 6, title, 2)
    for k, ((_, label), im) in enumerate(zip(cells, imgs)):
        r, c = divmod(k, cols)
        y0 = top + r * (ch + label_h)
        x0 = c * cw
        h, w = im.shape[:2]
        h = min(h, ch)
        w = min(w, cw)
        tile = im[:h, :w]
        a = tile[..., 3:4]
        region = canvas[y0:y0 + h, x0:x0 + w, :3]
        canvas[y0:y0 + h, x0:x0 + w, :3] = tile[..., :3] * a + region * (1 - a)
        # a thin frame
        canvas[y0:y0 + ch, x0, :3] = 0.7
        canvas[y0:y0 + ch, min(x0 + cw - 1, canvas.shape[1] - 1), :3] = 0.7
        draw_text(canvas, x0 + 6, y0 + ch + 4, label, 2)
    save_rgba(out, canvas)
    C.log(f'sheet {C.rel(out)} ({canvas.shape[1]}x{canvas.shape[0]})')
    return out
