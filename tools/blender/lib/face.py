"""The face sheet (Blender 5.2): anime-style eyes and mouths drawn as filled 2D curves and rendered once.

Layout (512×512, pixel rects with a top-left origin; the runtime reads them as glTF UVs):
  rows 0–3  eye cells 128×80: whites (open, wide, arc, closed, blink, strain, dizzy) then lids (none, tired,
            sad, angry, sick, stressed, half, happy/blush)
  rows 4–6  mouth cells 128×48: smile, grin, flat, worried, frown, angry, small_o, wobble, grit, wavy, big_o
  row 7     48-px cells: pupil masks (R iris, G pupil, B highlight), sparkle, sweat
The three layers of each eye (white, pupil, lid) are separate head patches, so the pupil sits under the lids.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import bpy
import numpy as np

from . import common as C
from .nodes import emission_mat

SHEET = 512
EYE_W, EYE_H = 128, 80
MOUTH_W, MOUTH_H = 128, 48
SMALL = 48

WHITES = ['open', 'wide', 'arc', 'closed', 'blink', 'strain', 'dizzy', 'pupil']
LIDS = ['none', 'tired', 'sad', 'angry', 'sick', 'stressed', 'half', 'happy']
MOUTHS = ['smile', 'grin', 'flat', 'worried', 'frown', 'angry', 'small_o', 'wobble', 'grit', 'wavy', 'big_o', 'spare']
SMALLS = ['sparkle', 'sweat']

# expression → (white, lid, mouth, pupil visible, pupil scale)
EXPRESSIONS = {
    'neutral': ('open', 'none', 'smile', True, 1.0),
    'happy': ('arc', 'happy', 'grin', False, 1.0),
    'tired': ('open', 'tired', 'flat', True, 1.0),
    'stressed': ('open', 'stressed', 'worried', True, 0.8),
    'sad': ('open', 'sad', 'frown', True, 1.0),
    'angry': ('open', 'angry', 'angry', True, 0.9),
    'sleepy': ('closed', 'none', 'small_o', False, 1.0),
    'sick': ('open', 'sick', 'wobble', True, 0.9),
    'strain': ('strain', 'none', 'grit', False, 1.0),
    'dizzy': ('dizzy', 'none', 'wavy', False, 1.0),
    'surprised': ('wide', 'none', 'big_o', True, 0.7),
}


def cell_rects() -> dict[str, dict[str, list[int]]]:
    rects: dict[str, dict[str, list[int]]] = {'white': {}, 'lid': {}, 'mouth': {}, 'small': {}}
    for i, n in enumerate(WHITES):
        rects['white'][n] = [(i % 4) * EYE_W, (i // 4) * EYE_H, EYE_W, EYE_H]
    for i, n in enumerate(LIDS):
        rects['lid'][n] = [(i % 4) * EYE_W, 160 + (i // 4) * EYE_H, EYE_W, EYE_H]
    for i, n in enumerate(MOUTHS):
        rects['mouth'][n] = [(i % 4) * MOUTH_W, 320 + (i // 4) * MOUTH_H, MOUTH_W, MOUTH_H]
    for i, n in enumerate(SMALLS):
        rects['small'][n] = [i * SMALL, 464, SMALL, SMALL]
    return rects


# ----------------------------------------------------------------------------- 2D geometry (numpy)
def ellipse(cx, cy, rx, ry, n=72, a0=0.0, a1=2 * math.pi, rot=0.0):
    a = np.linspace(a0, a1, n, endpoint=abs(a1 - a0) < 2 * math.pi - 1e-6)
    x = rx * np.cos(a)
    y = ry * np.sin(a)
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        x, y = x * c - y * s, x * s + y * c
    return np.stack([cx + x, cy + y], axis=1)


def quad_curve(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = (np.array(p, dtype=float) for p in (p0, p1, p2))
    return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2


def cubic_curve(p0, p1, p2, p3, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.array(p, dtype=float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def polyline(pts):
    return np.array(pts, dtype=float)


def sine_line(x0, x1, y, amp, waves, n=80, phase=0.0):
    x = np.linspace(x0, x1, n)
    t = (x - x0) / (x1 - x0)
    return np.stack([x, y + amp * np.sin(t * waves * 2 * math.pi + phase)], axis=1)


def spiral(cx, cy, r0, r1, turns, n=160):
    t = np.linspace(0, 1, n)
    a = t * turns * 2 * math.pi
    r = r0 + (r1 - r0) * t
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1)


def stroke(pts, w, caps=True):
    """Outline polygon of a polyline of width w (round caps)."""
    pts = np.asarray(pts, dtype=float)
    d = np.gradient(pts, axis=0)
    ln = np.linalg.norm(d, axis=1)
    ln[ln == 0] = 1
    nrm = np.stack([-d[:, 1], d[:, 0]], axis=1) / ln[:, None]
    left = pts + nrm * (w / 2)
    right = pts - nrm * (w / 2)
    out = [left]
    if caps:
        # end cap
        e = pts[-1]
        ang0 = math.atan2(nrm[-1][1], nrm[-1][0])
        cap = [e + (w / 2) * np.array([math.cos(ang0 - k * math.pi / 8), math.sin(ang0 - k * math.pi / 8)]) for k in range(1, 8)]
        out.append(np.array(cap))
    out.append(right[::-1])
    if caps:
        s = pts[0]
        ang1 = math.atan2(-nrm[0][1], -nrm[0][0])
        cap = [s + (w / 2) * np.array([math.cos(ang1 - k * math.pi / 8), math.sin(ang1 - k * math.pi / 8)]) for k in range(1, 8)]
        out.append(np.array(cap))
    return np.concatenate(out, axis=0)


def arc_band(cx, cy, rx, ry, thick, a0_deg, a1_deg, n=60):
    a0, a1 = math.radians(a0_deg), math.radians(a1_deg)
    outer = ellipse(cx, cy, rx, ry, n, a0, a1)
    inner = ellipse(cx, cy, rx - thick, ry - thick, n, a0, a1)[::-1]
    return np.concatenate([outer, inner], axis=0)


def clip_above(poly, line_fn, n_line=40):
    """The part of a convex polygon above y = line_fn(x) (used for lids over the eye white)."""
    poly = np.asarray(poly, dtype=float)
    keep = poly[:, 1] >= line_fn(poly[:, 0])
    if not keep.any():
        return None
    # rotate so the kept run is contiguous
    idx = np.nonzero(~keep)[0]
    if len(idx) == 0:
        return poly
    start = (idx[-1] + 1) % len(poly)
    order = np.r_[start:len(poly), 0:start]
    poly = poly[order]
    keep = keep[order]
    kept = poly[keep]
    # close along the line from the last kept x back to the first kept x
    xs = np.linspace(kept[-1][0], kept[0][0], n_line)
    line = np.stack([xs, line_fn(xs)], axis=1)
    return np.concatenate([kept, line], axis=0)


def clip_below(poly, line_fn, n_line=40):
    """The part of a convex polygon below y = line_fn(x)."""
    poly = np.asarray(poly, dtype=float)
    flipped = clip_above(poly * np.array([1.0, -1.0]), lambda x: -line_fn(x), n_line)
    return None if flipped is None else flipped * np.array([1.0, -1.0])


def star(cx, cy, r_out, r_in, points=4, rot=0.0):
    pts = []
    for i in range(points * 2):
        a = rot + i * math.pi / points
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def round_rect(x0, y0, x1, y1, r, n=8):
    pts = []
    corners = [(x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi), (x1 - r, y0 + r, 3 * math.pi / 2)]
    for cx, cy, a0 in corners:
        for k in range(n + 1):
            a = a0 + (k / n) * (math.pi / 2)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


# ----------------------------------------------------------------------------- the cells
@dataclass
class Shape:
    poly: np.ndarray
    color: str
    alpha: float = 1.0


@dataclass
class FaceColors:
    outline: str      # darker tint of the body colour, never black
    skin: str         # the lid colour (body colour, a touch darker)
    white: str = '#fff9f0'
    mouth: str = '#2e2330'
    tongue: str = '#f28fa8'
    teeth: str = '#fff9f0'
    blush: str = '#f28fa8'
    sweat: str = '#9fdcf7'
    highlight: str = '#ffffff'


def eye_cells(k: FaceColors) -> dict[str, list[Shape]]:
    cx, cy, rx, ry = 64, 40, 47, 34
    out = k.outline
    cells: dict[str, list[Shape]] = {}
    ring = lambda rx_, ry_: [Shape(ellipse(cx, cy, rx_ + 3.5, ry_ + 3.5), out), Shape(ellipse(cx, cy, rx_, ry_), k.white)]
    cells['open'] = ring(rx, ry)
    cells['wide'] = ring(51, 36)
    # the pupil masks share the eye cell's shape so the iris stays round on the patch: R iris, G pupil, B highlights
    cells['pupil'] = [Shape(ellipse(cx, cy, 26, 26), '#ff0000'), Shape(ellipse(cx, cy - 2, 14, 14.5), '#00ff00'),
                      Shape(ellipse(cx - 9.5, cy + 9, 7, 7), '#0000ff'), Shape(ellipse(cx + 10, cy - 9, 3.4, 3.4), '#0000ff')]
    cells['arc'] = [Shape(arc_band(cx, 28, 42, 34, 10, 12, 168), out)]
    cells['closed'] = [Shape(stroke(quad_curve((20, 36), (64, 56), (108, 36)), 6), out)]
    cells['blink'] = [Shape(stroke(quad_curve((18, 40), (64, 50), (110, 40)), 5.5), out),
                      Shape(stroke(polyline([(22, 42), (12, 50)]), 4), out),
                      Shape(stroke(polyline([(30, 36), (24, 24)]), 4), out)]
    cells['strain'] = [Shape(stroke(polyline([(30, 66), (84, 40)]), 7), out), Shape(stroke(polyline([(84, 40), (30, 14)]), 7), out)]
    cells['dizzy'] = [Shape(stroke(spiral(cx, cy, 3, 30, 2.4), 5), out)]
    cells['spare'] = []
    # lids (drawn over the white and the pupil)
    full = ellipse(cx, cy, rx + 3.5, ry + 3.5, 96)
    lids: dict[str, list[Shape]] = {'none': []}

    def lid_from_line(fn, lash=True):
        poly = clip_above(full, fn)
        shapes = [Shape(poly, k.skin)] if poly is not None else []
        if lash and poly is not None:
            xs = np.linspace(cx - rx - 2, cx + rx + 2, 40)
            shapes.append(Shape(stroke(np.stack([xs, fn(xs)], axis=1), 3.5, caps=False), out))
        return shapes

    lids['tired'] = lid_from_line(lambda x: 48 - 3 * np.cos((x - cx) / rx * 1.4))
    lids['half'] = lid_from_line(lambda x: 36 - 2 * np.cos((x - cx) / rx * 1.4))
    # sad: the outer (left) side droops; brow rises toward the inner corner
    lids['sad'] = lid_from_line(lambda x: 26 + (x - 14) * 0.38) + [Shape(stroke(polyline([(22, 72), (98, 82)]), 4), out, 0.85)]
    # angry: the inner (right) side comes down; brow slants down toward the nose
    lids['angry'] = lid_from_line(lambda x: 66 - (x - 14) * 0.36) + [Shape(stroke(polyline([(26, 82), (102, 68)]), 4.5), out, 0.9)]
    sick = lid_from_line(lambda x: 50 - 2 * np.cos((x - cx) / rx * 1.4))
    low = clip_below(full, lambda x: 20 + 2 * np.cos((x - cx) / rx * 1.4))
    if low is not None:
        sick.append(Shape(low, k.skin))
        xs = np.linspace(cx - rx + 2, cx + rx - 2, 30)
        sick.append(Shape(stroke(np.stack([xs, 20 + 2 * np.cos((xs - cx) / rx * 1.4)], axis=1), 3, caps=False), out, 0.8))
    lids['sick'] = sick
    lids['stressed'] = [Shape(stroke(quad_curve((22, 74), (64, 88), (106, 74)), 4), out, 0.9),
                        Shape(stroke(polyline([(cx - rx + 10, 10), (cx + rx - 10, 10)]), 3), out, 0.6)]
    lids['happy'] = [Shape(ellipse(34, 11, 26, 9), k.blush, 0.6)]
    return cells | {'lid:' + n: s for n, s in lids.items()}


def mouth_cells(k: FaceColors) -> dict[str, list[Shape]]:
    out = k.outline
    cells: dict[str, list[Shape]] = {}
    cells['smile'] = [Shape(stroke(quad_curve((26, 32), (64, 6), (102, 32)), 5.5), out)]
    top = polyline([(22, 31), (106, 31)])
    bottom = cubic_curve((106, 31), (104, -2), (24, -2), (22, 31), 48)
    grin = np.concatenate([top, bottom[1:-1]], axis=0)
    cells['grin'] = [Shape(stroke(np.concatenate([grin, grin[:1]]), 3.5, caps=False), out), Shape(grin, k.mouth),
                     Shape(ellipse(64, 8, 20, 9), k.tongue), Shape(polyline([(28, 31), (100, 31), (100, 26), (28, 26)]), k.teeth)]
    cells['flat'] = [Shape(stroke(polyline([(38, 22), (90, 22)]), 4.5), out)]
    cells['worried'] = [Shape(stroke(sine_line(30, 98, 22, 3, 1.5, phase=math.pi), 4.5), out)]
    cells['frown'] = [Shape(stroke(quad_curve((28, 14), (64, 36), (100, 14)), 5), out)]
    atop = cubic_curve((26, 16), (28, 42), (100, 42), (102, 16), 48)
    aback = polyline([(102, 16), (26, 16)])
    ang = np.concatenate([atop, aback[1:-1]], axis=0)
    cells['angry'] = [Shape(stroke(np.concatenate([ang, ang[:1]]), 3.5, caps=False), out), Shape(ang, k.mouth),
                      Shape(polyline([(40, 30), (48, 22), (56, 30)]), k.teeth), Shape(polyline([(72, 30), (80, 22), (88, 30)]), k.teeth)]
    cells['small_o'] = [Shape(ellipse(64, 22, 10.5, 12.5), out), Shape(ellipse(64, 22, 7.5, 9.5), k.mouth)]
    cells['wobble'] = [Shape(stroke(sine_line(26, 102, 22, 4, 3), 4.5), out)]
    rr = round_rect(28, 14, 100, 32, 7)
    grit = [Shape(stroke(np.concatenate([rr, rr[:1]]), 3.5, caps=False), out), Shape(rr, k.teeth)]
    for x in (43, 57, 71, 85):
        grit.append(Shape(stroke(polyline([(x, 15), (x, 31)]), 2.2), out, 0.8))
    cells['grit'] = grit
    cells['wavy'] = [Shape(stroke(sine_line(24, 104, 22, 6, 2), 5), out)]
    cells['big_o'] = [Shape(ellipse(64, 24, 17.5, 21.5), out), Shape(ellipse(64, 24, 14, 18), k.mouth), Shape(ellipse(64, 11, 9, 5), k.tongue)]
    cells['spare'] = []
    return cells


def small_cells(k: FaceColors) -> dict[str, list[Shape]]:
    cells: dict[str, list[Shape]] = {}
    cells['sparkle'] = [Shape(star(22, 24, 19, 5, 4), k.highlight), Shape(star(39, 11, 7, 2, 4), k.highlight)]
    drop = np.concatenate([ellipse(24, 18, 11, 11, 48, math.radians(-150), math.radians(150))[::-1], np.array([[24, 42]])], axis=0)
    cells['sweat'] = [Shape(drop, k.sweat), Shape(ellipse(19, 21, 3, 4), k.highlight, 0.9)]
    return cells


# ----------------------------------------------------------------------------- rendering
def _curve_object(name: str, poly: np.ndarray, mat: bpy.types.Material, x0: float, y0: float, z: float, coll) -> bpy.types.Object:
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    sp = cu.splines.new('POLY')
    sp.points.add(len(poly) - 1)
    for i, (x, y) in enumerate(poly):
        sp.points[i].co = (x0 + float(x), y0 + float(y), 0.0, 1.0)
    sp.use_cyclic_u = True
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    ob.location = (0, 0, z)
    coll.objects.link(ob)
    return ob


def render_face_sheet(colors: FaceColors, out_png: Path, samples: int = 32) -> dict:
    """Draw every cell into a fresh scene and render the 512×512 sheet. Returns the cell rects."""
    rects = cell_rects()
    sc = bpy.data.scenes.new('FaceSheet')
    coll = bpy.data.collections.new('FaceCells')
    sc.collection.children.link(coll)
    mats: dict[tuple[str, float], bpy.types.Material] = {}

    def mat_for(color: str, alpha: float):
        key = (color, round(alpha, 3))
        if key not in mats:
            mats[key] = emission_mat(f'face_{color}_{alpha}', C.lin(color), 1.0, alpha)
        return mats[key]

    z = 0.0

    def place(shapes: list[Shape], rect: list[int], tag: str):
        nonlocal z
        x, y, w, h = rect
        x0 = x
        y0 = SHEET - (y + h)          # Blender's y goes up; the sheet's origin is top-left
        for i, s in enumerate(shapes):
            z += 0.001
            _curve_object(f'{tag}_{i}', s.poly, mat_for(s.color, s.alpha), x0, y0, z, coll)

    eyes = eye_cells(colors)
    for n in WHITES:
        place(eyes[n], rects['white'][n], f'white_{n}')
    for n in LIDS:
        place(eyes['lid:' + n], rects['lid'][n], f'lid_{n}')
    mouths = mouth_cells(colors)
    for n in MOUTHS:
        place(mouths[n], rects['mouth'][n], f'mouth_{n}')
    smalls = small_cells(colors)
    for n in SMALLS:
        place(smalls[n], rects['small'][n], f'small_{n}')

    cam_data = bpy.data.cameras.new('FaceCam')
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = SHEET
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    cam = bpy.data.objects.new('FaceCam', cam_data)
    cam.location = (SHEET / 2, SHEET / 2, 10)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = sc.render.resolution_y = SHEET
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.filter_size = 1.3
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'Standard'
    try:
        sc.view_settings.look = 'None'
    except TypeError:
        pass
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_shadows = False
    w = bpy.data.worlds.new('FaceWorld')
    sc.world = w
    if w.node_tree is None:
        w.use_nodes = True
    for n in w.node_tree.nodes:
        if n.type == 'BACKGROUND':
            n.inputs['Strength'].default_value = 0.0
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(out_png)
    with C.Timer('face sheet render'):
        bpy.ops.render.render(write_still=True, scene=sc.name)
    C.log(f'saved {C.rel(out_png)}')
    bpy.data.scenes.remove(sc)
    return {
        'sheet': SHEET,
        'cells': rects,
        'expressions': {n: {'white': w_, 'lid': l, 'mouth': m, 'pupil': p, 'pupilScale': ps} for n, (w_, l, m, p, ps) in EXPRESSIONS.items()},
    }
