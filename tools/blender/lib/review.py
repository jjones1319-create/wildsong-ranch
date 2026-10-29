"""The §6 Blender review sheets: turnaround, faces, texture close-ups, the secret variant and clip strips."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import bpy
from mathutils import Vector

from . import anim as A
from . import common as C
from . import face as F
from . import render as RN

FACE_LAYERS = ['white.L', 'pupil.L', 'lid.L', 'white.R', 'pupil.R', 'lid.R', 'mouth']


@dataclass
class ReviewCtx:
    look: str
    out: Path
    arm: bpy.types.Object
    body: bpy.types.Object
    face_objs: dict[str, bpy.types.Object]
    face_layout: dict
    clips: list[A.ClipMeta]
    centre: Vector
    size: float
    head_centre: Vector
    head_size: float
    body_mat: bpy.types.Material
    base_image: bpy.types.Image
    variant_images: dict[str, bpy.types.Image] = field(default_factory=dict)
    quick: bool = False


def _cell_uv(rect: list[int], mirror: bool) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    x, y, w, h = rect
    u0 = x / F.SHEET
    v0 = 1.0 - (y + h) / F.SHEET
    fw = w / F.SHEET
    fh = h / F.SHEET
    if mirror:
        return (u0 + fw, v0, 0.0), (-fw, fh, 1.0)
    return (u0, v0, 0.0), (fw, fh, 1.0)


def set_face(ctx: ReviewCtx, expression: str) -> None:
    """Point every face layer's Mapping node at the cells of `expression`."""
    ex = ctx.face_layout['expressions'][expression]
    cells = ctx.face_layout['cells']
    for layer, obj in ctx.face_objs.items():
        kind, _, side = layer.partition('.')
        mirror = side == 'R'
        if kind == 'white':
            rect = cells['white'][ex['white']]
        elif kind == 'lid':
            rect = cells['lid'][ex['lid']]
        elif kind == 'pupil':
            rect = cells['white']['pupil']
            obj.hide_render = not ex['pupil']
        else:
            rect = cells['mouth'][ex['mouth']]
        loc, scale = _cell_uv(rect, mirror)
        for mat in obj.data.materials:
            node = mat.node_tree.nodes.get('cell')
            if node is not None:
                node.inputs['Location'].default_value = loc
                node.inputs['Scale'].default_value = scale


def _tex_image_node(mat: bpy.types.Material):
    for n in mat.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.name == 'base':
            return n
    return None


def turnaround(ctx: ReviewCtx, tag: str = 'turnaround', image: bpy.types.Image | None = None) -> Path:
    node = _tex_image_node(ctx.body_mat)
    prev = node.image if node else None
    if node is not None and image is not None:
        node.image = image
    set_face(ctx, 'neutral')
    cam = bpy.context.scene.camera
    res = 360 if ctx.quick else 480
    RN.setup_eevee((res, res), 12 if ctx.quick else 24)
    cells = []
    for az in (0, 45, 90, 135, 180):
        RN.aim_camera(cam, ctx.centre, az, 10, ctx.size)
        p = RN.render_png(ctx.out / 'frames' / f'{tag}_{az:03d}.png')
        cells.append((p, f'{az} deg'))
    if node is not None and prev is not None:
        node.image = prev
    return RN.contact_sheet(cells, 5, ctx.out / f'{tag}.png', title=f'{ctx.look} {tag}')


def faces(ctx: ReviewCtx) -> Path:
    cam = bpy.context.scene.camera
    res = 240 if ctx.quick else 320
    RN.setup_eevee((res, res), 12 if ctx.quick else 24)
    cells = []
    for name in F.EXPRESSIONS:
        set_face(ctx, name)
        RN.aim_camera(cam, ctx.head_centre, 0, 6, ctx.head_size)
        p = RN.render_png(ctx.out / 'frames' / f'face_{name}.png')
        cells.append((p, name))
    # the blink cell and the half lid, as the runtime shows them mid-blink
    set_face(ctx, 'neutral')
    cells_ = ctx.face_layout['cells']
    for layer, obj in ctx.face_objs.items():
        if layer.startswith('white'):
            loc, scale = _cell_uv(cells_['white']['blink'], layer.endswith('.R'))
            obj.data.materials[0].node_tree.nodes['cell'].inputs['Location'].default_value = loc
            obj.data.materials[0].node_tree.nodes['cell'].inputs['Scale'].default_value = scale
        if layer.startswith('pupil'):
            obj.hide_render = True
    p = RN.render_png(ctx.out / 'frames' / 'face_blink.png')
    cells.append((p, 'blink'))
    set_face(ctx, 'neutral')
    return RN.contact_sheet(cells, 4, ctx.out / 'faces.png', title=f'{ctx.look} faces')


def textures(ctx: ReviewCtx, spots: list[tuple[str, Vector, float, float, float]]) -> Path:
    """Close-ups: (label, centre, size, azimuth, elevation). Rendered unlit so the paint reads as painted."""
    from .nodes import emission_mat  # noqa: PLC0415
    unlit = emission_mat('unlit_base', (1, 1, 1, 1))
    nb_tree = unlit.node_tree
    tex = nb_tree.nodes.new('ShaderNodeTexImage')
    tex.image = ctx.base_image
    em = next(n for n in nb_tree.nodes if n.type == 'EMISSION')
    nb_tree.links.new(tex.outputs['Color'], em.inputs['Color'])
    prev = list(ctx.body.data.materials)
    ctx.body.data.materials[0] = unlit
    set_face(ctx, 'neutral')
    cam = bpy.context.scene.camera
    res = 300 if ctx.quick else 400
    RN.setup_eevee((res, res), 8)
    cells = []
    for label, centre, size, az, el in spots:
        RN.aim_camera(cam, centre, az, el, size)
        p = RN.render_png(ctx.out / 'frames' / f'tex_{label}.png')
        cells.append((p, label))
    ctx.body.data.materials[0] = prev[0]
    return RN.contact_sheet(cells, 4, ctx.out / 'textures.png', title=f'{ctx.look} textures (unlit)')


def variant(ctx: ReviewCtx, variant_id: str) -> Path | None:
    img = ctx.variant_images.get(variant_id)
    if img is None:
        return None
    return turnaround(ctx, tag=f'variant_{variant_id}', image=img)


def clip_strips(ctx: ReviewCtx, frames_per_clip: int = 8, only: list[str] | None = None) -> list[Path]:
    cam = bpy.context.scene.camera
    res = 200 if ctx.quick else 260
    RN.setup_eevee((res, res), 8 if ctx.quick else 16)
    out: list[Path] = []
    sc = bpy.context.scene
    for meta in ctx.clips:
        if only and meta.name not in only:
            continue
        A.set_clip(ctx.arm, meta)
        cells = []
        for k in range(frames_per_clip):
            f = 1 + round(k * meta.frames / (frames_per_clip - 1 if not meta.loop else frames_per_clip))
            f = max(1, min(1 + meta.frames, f))
            sc.frame_set(f)
            face_now = 'neutral'
            for ft, fname in meta.faces:
                if ft <= f:
                    face_now = fname
            set_face(ctx, face_now)
            RN.aim_camera(cam, ctx.centre + Vector((0, 0, 0.02)), 40, 12, ctx.size * 1.25)
            p = RN.render_png(ctx.out / 'frames' / f'clip_{meta.name}_{k:02d}.png')
            cells.append((p, f'f{f}'))
        A.clear_clip(ctx.arm)
        sc.frame_set(1)
        out.append(RN.contact_sheet(cells, frames_per_clip, ctx.out / 'clips' / f'{meta.name}.png',
                                    title=f'{ctx.look} {meta.name} {meta.seconds:.2f}s'))
    set_face(ctx, 'neutral')
    return out


def write_index(ctx: ReviewCtx, sheets: list[Path]) -> Path:
    rows = ''.join(f'<h2>{p.stem}</h2><img src="{p.relative_to(ctx.out).as_posix()}">' for p in sheets)
    html = f'<!doctype html><meta charset="utf-8"><title>{ctx.look} review</title><style>body{{font:14px system-ui;background:#eee;margin:16px}}img{{max-width:100%;display:block;margin:0 0 20px;background:#ddd}}</style><h1>{ctx.look}: Blender review sheets</h1>{rows}'
    p = ctx.out / 'index.html'
    p.write_text(html, encoding='utf-8')
    return p
