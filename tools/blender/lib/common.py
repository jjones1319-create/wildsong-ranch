"""Shared helpers for every headless Blender script (Art 2.0, ART_2_PLAN §3.1).

Pinned to the Blender 5.2 Python API. Everything here is scene-agnostic: paths, logging, colour maths
and the small object helpers that `ranch_scenes.py` grew and the monster pipeline reuses.
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent          # tools/blender/lib
BLENDER_DIR = HERE.parent                        # tools/blender
ROOT = BLENDER_DIR.parent.parent                 # the repo
OUT_ROOT = BLENDER_DIR / 'out'

_LOG_FILE = None
_T0 = time.time()


def open_log(path: Path) -> None:
    """Mirror every log line into a file (the build runs in the background; Claude reads the log)."""
    global _LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE = open(path, 'a', encoding='utf-8')
    log(f'--- {time.strftime("%Y-%m-%d %H:%M:%S")} · Blender {bpy.app.version_string} · {" ".join(sys.argv[1:])}')


def log(*a) -> None:
    line = f'[art {time.time() - _T0:7.1f}s] ' + ' '.join(str(x) for x in a)
    print(line, flush=True)
    if _LOG_FILE is not None:
        _LOG_FILE.write(line + '\n')
        _LOG_FILE.flush()


def script_args() -> list[str]:
    """Everything after `--` on the Blender command line."""
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


class Timer:
    def __init__(self, label: str):
        self.label = label

    def __enter__(self):
        self.t = time.time()
        return self

    def __exit__(self, *exc):
        log(f'{self.label}: {time.time() - self.t:.1f}s')


# ----------------------------------------------------------------------------- colour
def srgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(h: str, k: float = 1.0) -> tuple[float, float, float, float]:
    """sRGB hex -> linear RGBA, optionally scaled (the convention `ranch_scenes.py` uses)."""
    r, g, b = srgb(h)
    return (to_linear(r) * k, to_linear(g) * k, to_linear(b) * k, 1.0)


def lin_rgb(h: str) -> tuple[float, float, float]:
    r, g, b = srgb(h)
    return (to_linear(r), to_linear(g), to_linear(b))


def mix_hex(a: str, b: str, t: float) -> str:
    ra, ga, ba = srgb(a)
    rb, gb, bb = srgb(b)
    return '#%02x%02x%02x' % tuple(int(round(255 * (x + (y - x) * t))) for x, y in ((ra, rb), (ga, gb), (ba, bb)))


def shade_hex(h: str, k: float, cool: float = 0.0) -> str:
    """Darken (k < 1) or lighten a colour; `cool` nudges it toward blue, as the art bible's shadows ask."""
    r, g, b = srgb(h)
    r, g, b = r * k, g * k, min(1.0, b * k + cool)
    return '#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255))


def smoothstep(a: float, b: float, x: float) -> float:
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_in_out(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ease_out(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t


# ----------------------------------------------------------------------------- scene helpers
def clear_scene() -> None:
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.node_groups,
                 bpy.data.armatures, bpy.data.actions, bpy.data.images, bpy.data.curves, bpy.data.collections):
        for d in list(coll):
            try:
                coll.remove(d)
            except Exception:
                pass


def collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link_obj(obj: bpy.types.Object, coll: bpy.types.Collection | None = None) -> bpy.types.Object:
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def set_active(obj: bpy.types.Object, selected: list[bpy.types.Object] | None = None) -> None:
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in (selected or [obj]):
        o.select_set(True)
    bpy.context.view_layer.objects.active = obj


def evaluated_mesh(obj: bpy.types.Object) -> bpy.types.Mesh:
    """A new mesh datablock with every modifier of `obj` applied (no operator context needed)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    return me


def apply_modifiers(obj: bpy.types.Object) -> None:
    """Bake all modifiers into the object's mesh and clear the stack."""
    me = evaluated_mesh(obj)
    old = obj.data
    obj.data = me
    obj.modifiers.clear()
    if old.users == 0:
        bpy.data.meshes.remove(old)


def deg(x: float) -> float:
    return math.radians(x)


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace(os.sep, '/')
    except ValueError:
        return str(p)
