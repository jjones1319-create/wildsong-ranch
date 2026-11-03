"""The Crown Amphitheatre's bake stage (see crown.py): every atlas group joined into one mesh, its islands packed (the
floor, plaza and land keep their planar UVs), then Cycles bakes albedo (full size), diffuse light (direct + indirect,
half size, smoothed) and emission; lit = albedo × light + emission, softly compressed above 0.8, stored as sRGB PNG
(plus a half-size copy for Lite). The awnings add a translucent glow: seen from below, sunlit cloth shines through.
Also renders the sky panoramas (Full: sky and far mountains; Lite: the trees and the town too) and builds the domes.
The generic image and bake helpers come from guild_bake (imported, unchanged).
"""
from __future__ import annotations

import hashlib
import json
import math
import time

import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
import kit as K
import guild_bake as GB
import crown as CR
from crown_sky import dome_half, render_skies

TEX = CR.OUT / 'tex'
GLOW = {'velarium': 0.45}
SAMPLES = {'ring': 64, 'apron_w': 64, 'apron_e': 64, 'plaza': 48, 'land': 32, 'velarium': 64, 'outskirts': 48}
FULL_BOWL = ('low_n', 'low_s', 'mid', 'top', 'gallery', 'statues')     # full-only parts the Lite ones overlap


def show_for(g: str) -> None:
    """The Lite bowl and the full bowl overlap: only one of them takes part in a bake (and casts its shadows)."""
    lite_only = CR.GROUPS[g][3]
    for name, spec in CR.GROUPS.items():
        c = bpy.data.collections.get('G_' + name)
        if c is not None:
            c.hide_render = (spec[3] and not lite_only) or (lite_only and name in FULL_BOWL)
    if 'FAR_PANO' in bpy.data.collections:
        bpy.data.collections['FAR_PANO'].hide_render = True


def smart_unwrap(objs: list) -> None:
    """Imported meshes (the statues) get their bake islands from Smart UV Project."""
    if not objs:
        return
    for o in objs:
        if 'BakeUV' not in o.data.uv_layers:
            o.data.uv_layers.new(name='BakeUV')
        o.data.uv_layers.active = o.data.uv_layers['BakeUV']
    C.set_active(objs[0], objs)
    with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode='OBJECT')


def join_group(g: str) -> bpy.types.Object:
    col = bpy.data.collections['G_' + g]
    objs = [o for o in col.objects if o.type == 'MESH' and len(o.data.polygons)]
    smart_unwrap([o for o in objs if not o.get('custom_bake')])
    for o in objs:
        o.hide_set(False)
        o.hide_viewport = False
        me = o.data
        if 'UVMap' not in me.uv_layers:
            me.uv_layers.new(name='UVMap')
        for name in [l.name for l in me.uv_layers if l.name not in ('UVMap', 'BakeUV')]:
            me.uv_layers.remove(me.uv_layers[name])
    act = objs[0]
    if len(objs) > 1:
        with bpy.context.temp_override(active_object=act, object=act, selected_objects=objs, selected_editable_objects=objs):
            bpy.ops.object.join()
    act.name = act.data.name = f'arena_{g}'
    me = act.data
    me.uv_layers.active = me.uv_layers['BakeUV']
    me.uv_layers['UVMap'].active_render = True
    C.log(f'joined {g}: {len(objs)} objects, {K.tri_count(act)} tris, {len(me.materials)} materials')
    return act


def pack(g: str, ob: bpy.types.Object) -> str:
    if CR.GROUPS[g][2] == 'pack':       # (every packed atlas is square; the planar ones keep their UVs)
        C.set_active(ob)
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.select_all(action='SELECT')
            bpy.ops.uv.average_islands_scale()
            bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=0.0024, shape_method='CONCAVE')
            bpy.ops.object.mode_set(mode='OBJECT')
    a = np.empty(len(ob.data.loops) * 2, np.float32)
    ob.data.uv_layers['BakeUV'].data.foreach_get('uv', a)
    used = np.clip(a.reshape(-1, 2), 0, 1)
    digest = hashlib.md5(a.round(5).tobytes()).hexdigest()[:10]
    C.log(f'packed {g}: uv range {used.min(0).round(3).tolist()}..{used.max(0).round(3).tolist()} · {digest}')
    return digest


def bake_group(g: str, ob: bpy.types.Object, quick: bool) -> dict:
    (w, h), _, _, lite_only = CR.GROUPS[g]
    if quick:
        w, h = w // 2, h // 2
    show_for(g)
    t0 = time.time()
    alb = GB.float_image(f'{g}_albedo', w, h)
    GB.set_targets(ob, alb)
    GB.run_bake(ob, 'DIFFUSE', {'COLOR'}, 2 if quick else 4, 8)
    A = GB.image_array(alb)[..., :3]
    em = GB.float_image(f'{g}_emit', w, h)
    GB.set_targets(ob, em)
    GB.run_bake(ob, 'EMIT', set(), 1, 8)
    E = GB.image_array(em)[..., :3]
    irr = GB.float_image(f'{g}_light', w // 2, h // 2)
    GB.set_targets(ob, irr)
    GB.run_bake(ob, 'DIFFUSE', {'DIRECT', 'INDIRECT'}, 32 if quick else SAMPLES.get(g, 112), 6)
    I = GB.upsample2(GB.blur(GB.image_array(irr)[..., :3], 2), h, w) + GLOW.get(g, 0.0)
    lit = A * I + E
    name = f'{g}_lite' if lite_only else g
    GB.save_srgb_png(TEX / f'{name}.png', lit)
    if not lite_only:
        GB.save_srgb_png(TEX / f'{g}_lite.png', GB.downsample2(lit))
    for img in (alb, em, irr):
        bpy.data.images.remove(img)
    q = np.percentile(lit.max(-1), [5, 50, 95, 99.5])
    C.log(f'bake {g}: {w}x{h} in {time.time() - t0:.0f}s · lit p5/p50/p95/p99.5 = {q.round(3).tolist()}')
    return {'size': [w, h], 'seconds': round(time.time() - t0), 'p50': float(q[1]), 'p99': float(q[3])}


def stage_sky(quick: bool) -> None:
    bpy.ops.wm.open_mainfile(filepath=str(CR.OUT / 'crown_src.blend'))
    CR.use_gpu()
    TEX.mkdir(parents=True, exist_ok=True)
    render_skies(quick)


def stage_bake(quick: bool, only: list[str]) -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(CR.OUT / 'crown_src.blend'))
    C.log(f'bake on {CR.use_gpu()}')
    TEX.mkdir(parents=True, exist_ok=True)
    if 'REVIEW' in bpy.data.collections:
        bpy.data.collections['REVIEW'].hide_render = True
    if not only or 'sky' in only:
        render_skies(quick)
    objs, digests = {}, {}
    for g in CR.GROUPS:
        objs[g] = join_group(g)
        digests[g] = pack(g, objs[g])
    stats = {'uv': digests}
    for g, ob in objs.items():
        if not only or g in only:
            stats[g] = bake_group(g, ob, quick)
    for c in bpy.data.collections:                      # the Lite-only bakes hid the full bowl: show every part again
        c.hide_render = c.name == 'FAR_PANO'
    for prefix in ('sky', 'sky_lite'):
        for half in ('front', 'back'):
            img = bpy.data.images.load(str(TEX / f'{prefix}_{half}.png'))
            dome_half(f'{prefix}_{half}', half, img).hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=str(CR.OUT / 'crown_baked.blend'), compress=False)
    old = CR.OUT / 'stats_bake.json'
    prev = json.loads(old.read_text(encoding='utf-8')) if old.exists() else {}
    for g, dg in digests.items():
        if only and g not in only and prev.get('uv', {}).get(g) not in (None, dg):
            C.log(f'WARNING: {g} packed differently from its last bake: re-bake it too')
    prev.update(stats)
    old.write_text(json.dumps(prev, indent=1), encoding='utf-8')
    return stats
