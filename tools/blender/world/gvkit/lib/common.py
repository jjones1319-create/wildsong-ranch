"""common.py — paths, arguments and scene helpers every Gloamvault Blender script shares.

Scripts run headless: `blender -b [file.blend] -P tools/blender/<script>.py -- --flag value`. Everything after `--`
is ours (`args()`); every path is built from REPO so a script runs from any working directory.
"""
import os
import sys
import json

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)                      # tools/blender
REPO = os.environ.get('GVKIT_ROOT') or os.path.join(os.path.dirname(os.path.dirname(TOOLS)), 'out', 'world', 'gvkit')  # WS: Wildsong's copy writes into tools/blender/out/world/gvkit/ (gitignored); tools/world/import-gloamvault.ts

ART = os.path.join(REPO, 'art')
BUILD = os.path.join(ART, 'build')                 # .blend outputs (git-ignored)
RENDERS = os.path.join(ART, 'renders')             # review PNGs (committed; history/ is ignored)
REF = os.path.join(ART, 'ref')
BUNDLE = os.path.join(REF, 'human-base-meshes', 'human_base_meshes_bundle.blend')
MODELS = os.path.join(REPO, 'client', 'public', 'models')
CONTENT = os.path.join(REPO, 'content')

for d in (BUILD, RENDERS, MODELS):
    os.makedirs(d, exist_ok=True)


def args(argv=None):
    """`-- --species dwarf --quick` → {'species': 'dwarf', 'quick': True}."""
    argv = sys.argv if argv is None else argv
    rest = argv[argv.index('--') + 1:] if '--' in argv else []
    out = {}
    i = 0
    while i < len(rest):
        a = rest[i]
        if a.startswith('--'):
            key = a[2:].replace('-', '_')
            if i + 1 < len(rest) and not rest[i + 1].startswith('--'):
                out[key] = rest[i + 1]
                i += 2
                continue
            out[key] = True
        i += 1
    return out


def log(*parts):
    print('[gv]', *parts, flush=True)


def hexcol(h, alpha=1.0):
    """'#RRGGBB' (sRGB) → linear RGBA, which is what Blender colour sockets take."""
    h = h.lstrip('#')
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(srgb[0]), lin(srgb[1]), lin(srgb[2]), alpha)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def link(ob, col_name='Character'):
    col = collection(col_name)
    if ob.name not in col.objects:
        col.objects.link(ob)
    return ob


def append_objects(blend_path, names):
    """Appends objects by name from another .blend; returns them in the order asked."""
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        missing = [n for n in names if n not in src.objects]
        if missing:
            raise RuntimeError('not in %s: %s' % (blend_path, missing))
        dst.objects = list(names)
    return [bpy.data.objects[n] for n in names]


def set_active(ob):
    bpy.context.view_layer.update()
    for o in bpy.data.objects:
        if o.name in bpy.context.view_layer.objects:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def apply_transforms(ob):
    """Bakes location/rotation/scale into the mesh data (and children keep their world placement)."""
    set_active(ob)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def tri_count(ob, depsgraph=None):
    dg = depsgraph or bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def bbox_world(ob):
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    return lo, hi


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    log('saved', os.path.relpath(path, REPO))
