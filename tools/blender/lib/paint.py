"""Painted textures (Blender 5.2): procedural colour fields in object space, baked to a UV image with Cycles.

A recipe lists `Field`s in paint order: each one is a soft mask (ellipsoids, dapples, stripes, gradients) that
mixes its colour over what is already painted. Because everything is evaluated in object space, UV seams are
invisible and "bigger belly patch" is one number.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import bpy

from . import common as C
from .nodes import NB, new_mat


@dataclass
class Field:
    kind: str                                  # ellipsoid | dapple | stripes | gradient | wobble
    color: str = '#ffffff'                     # sRGB hex
    centre: tuple[float, float, float] = (0, 0, 0)
    radii: tuple[float, float, float] = (1, 1, 1)
    soft: float = 0.15                         # edge softness (fraction of the radius)
    strength: float = 1.0                      # mask multiplier
    mirror: bool = False                       # also paint at -X
    # restrict to a half-space: ('z', '<', 0.4) means only where z < 0.4 (with a soft edge `edge`)
    half: tuple[str, str, float] | None = None
    edge: float = 0.05
    # dapple
    scale: float = 6.0
    threshold: float = 0.6
    # stripes
    direction: tuple[float, float, float] = (0, 1, 0)
    freq: float = 8.0
    width: float = 0.35
    # gradient: along axis from a (0) to b (1)
    axis: str = 'z'
    a: float = 0.0
    b: float = 1.0
    extra: dict = field(default_factory=dict)


def _ellipsoid_mask(nb: NB, p, centre, radii, soft, strength=1.0):
    q = nb.vmath('SUBTRACT', p, tuple(centre))
    q = nb.vmath('DIVIDE', q, tuple(radii))
    d = nb.vmath('LENGTH', q)
    m = nb.smooth(d, 1.0 + soft, 1.0 - soft)
    if strength != 1.0:
        m = nb.math('MULTIPLY', m, strength, clamp=True)
    return m


def _half_mask(nb: NB, p, half, edge):
    axis, op, v = half
    comp = nb.sep(p)[{'x': 0, 'y': 1, 'z': 2}[axis]]
    if op == '<':
        return nb.smooth(comp, v + edge, v - edge)
    return nb.smooth(comp, v - edge, v + edge)


def field_mask(nb: NB, p, f: Field, area=None):
    if f.kind == 'ellipsoid':
        m = _ellipsoid_mask(nb, p, f.centre, f.radii, f.soft, f.strength)
        if f.mirror:
            c2 = (-f.centre[0], f.centre[1], f.centre[2])
            m = nb.math('MAXIMUM', m, _ellipsoid_mask(nb, p, c2, f.radii, f.soft, f.strength))
    elif f.kind == 'dapple':
        n = nb.noise(nb.vmath('SCALE', p, scale=f.scale), 1.0, detail=1.5, rough=0.4)
        m = nb.smooth(n, f.threshold - 0.04, f.threshold + 0.04)
        if f.radii != (1, 1, 1) or f.centre != (0, 0, 0):
            m = nb.math('MULTIPLY', m, _ellipsoid_mask(nb, p, f.centre, f.radii, f.soft))
        if f.strength != 1.0:
            m = nb.math('MULTIPLY', m, f.strength)
    elif f.kind == 'stripes':
        q = nb.vmath('SUBTRACT', p, tuple(f.centre))
        u = nb.vmath('DOT_PRODUCT', q, tuple(f.direction))
        s = nb.math('SINE', nb.math('MULTIPLY', u, f.freq * 6.283185))
        m = nb.smooth(s, 1.0 - 2 * f.width - 0.15, 1.0 - 2 * f.width + 0.15)
        m = nb.math('MULTIPLY', m, _ellipsoid_mask(nb, p, f.centre, f.radii, f.soft))
        if f.mirror:
            c2 = (-f.centre[0], f.centre[1], f.centre[2])
            q2 = nb.vmath('SUBTRACT', p, c2)
            u2 = nb.vmath('DOT_PRODUCT', q2, tuple(f.direction))
            s2 = nb.math('SINE', nb.math('MULTIPLY', u2, f.freq * 6.283185))
            m2 = nb.smooth(s2, 1.0 - 2 * f.width - 0.15, 1.0 - 2 * f.width + 0.15)
            m2 = nb.math('MULTIPLY', m2, _ellipsoid_mask(nb, p, c2, f.radii, f.soft))
            m = nb.math('MAXIMUM', m, m2)
        if f.strength != 1.0:
            m = nb.math('MULTIPLY', m, f.strength)
    elif f.kind == 'gradient':
        comp = nb.sep(p)[{'x': 0, 'y': 1, 'z': 2}[f.axis]]
        m = nb.smooth(comp, f.a, f.b)
        if f.strength != 1.0:
            m = nb.math('MULTIPLY', m, f.strength)
    else:
        raise ValueError(f.kind)
    if f.half is not None:
        m = nb.math('MULTIPLY', m, _half_mask(nb, p, f.half, f.edge))
    return m


def build_paint_material(name: str, base_hex: str, fields: list[Field], wobble: tuple[float, float] = (3.0, 0.02)) -> bpy.types.Material:
    """An unlit material whose colour is the painted result (object space). Bake it with `bake_emission`."""
    m, nb = new_mat(name)
    p = nb.coords().outputs['Object']
    if wobble[1] > 0:
        # organic edges: nudge the coordinate by a little noise
        n = nb.new('ShaderNodeTexNoise')
        nb.put(n.inputs['Vector'], p)
        n.inputs['Scale'].default_value = wobble[0]
        n.inputs['Detail'].default_value = 1.0
        off = nb.vmath('SUBTRACT', n.outputs['Color'], (0.5, 0.5, 0.5))
        off = nb.vmath('SCALE', off, scale=wobble[1] * 2)
        p = nb.vmath('ADD', p, off)
    col = nb.rgb(C.lin(base_hex))
    for f in fields:
        mask = field_mask(nb, p, f)
        col = nb.mix(mask, col, nb.rgb(C.lin(f.color)))
    em = nb.new('ShaderNodeEmission')
    nb.link(col, em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.0
    nb.output(em.outputs[0])
    return m


def bake_emission(obj: bpy.types.Object, mat: bpy.types.Material, image: bpy.types.Image, path: Path,
                  samples: int = 4, margin: int = 8) -> None:
    """Bake `mat`'s emission into `image` through `obj`'s UVs, then save it as PNG."""
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    nt = mat.node_tree
    node = nt.nodes.new('ShaderNodeTexImage')
    node.image = image
    node.select = True
    nt.nodes.active = node
    sc = bpy.context.scene
    prev = sc.render.engine
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.render.bake.margin = margin
    sc.render.bake.use_clear = True
    sc.render.bake.use_selected_to_active = False
    C.set_active(obj)
    with C.Timer(f'bake {image.name}'):
        with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
            bpy.ops.object.bake(type='EMIT', margin=margin, use_clear=True)
    sc.render.engine = prev
    nt.nodes.remove(node)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.filepath_raw = str(path)
    image.file_format = 'PNG'
    image.save()
    C.log(f'saved {C.rel(path)}')
