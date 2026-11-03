"""Geometry and material helpers for the grand-amphitheatre blockout (grand_blockout.py). Research only.

Everything is laid out on concentric ellipses: P(t, off) = ((A0 + off) cos t, (B0 + off) sin t), where off is the
distance outward from the arena floor's edge. Bays and boxes are "bent" along the ellipse so they tile exactly.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import bpy

A0, B0 = 27.0, 20.0   # the arena floor's semi-axes (m): 54 x 40 m of sand


def pt(t: float, off: float, z: float) -> tuple[float, float, float]:
    return ((A0 + off) * math.cos(t), (B0 + off) * math.sin(t), z)


def speed(t: float, off: float) -> float:
    return math.hypot((A0 + off) * math.sin(t), (B0 + off) * math.cos(t))


def bend(t0: float, off: float, x: float, d: float, z: float) -> tuple[float, float, float]:
    """Local (x along the wall, d outward, z up) around angle t0 on the ellipse at offset off."""
    return pt(t0 + x / speed(t0, off), off + d, z)


class MeshBuilder:
    def __init__(self) -> None:
        self.v: list[tuple[float, float, float]] = []
        self.f: list[tuple[int, ...]] = []
        self.m: list[int] = []

    def add(self, verts, faces, mat: int = 0) -> None:
        base = len(self.v)
        self.v.extend(verts)
        for fc in faces:
            self.f.append(tuple(base + i for i in fc))
            self.m.append(mat)

    def build(self, name: str, mats: list[bpy.types.Material], smooth: bool = False) -> bpy.types.Object:
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        for mt in mats:
            me.materials.append(mt)
        me.polygons.foreach_set('material_index', self.m)
        if smooth:
            me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def sweep(mb: MeshBuilder, prof: list[tuple[float, float, int]], n: int, t0=0.0, t1=2 * math.pi) -> None:
    """Sweep a profile [(off, z, mat_of_segment_to_next)] around the ellipse; faces face up / toward the arena."""
    closed = abs(t1 - t0 - 2 * math.pi) < 1e-6
    cols = n if closed else n + 1
    rings = [[pt(t0 + (t1 - t0) * j / n, o, z) for j in range(cols)] for o, z, _ in prof]
    for i in range(len(prof) - 1):
        verts = rings[i] + rings[i + 1]
        faces = []
        for j in range(n):
            j2 = (j + 1) % cols
            faces.append((j, cols + j, cols + j2, j2))
        mb.add(verts, faces, prof[i][2])


def arch_outline(w: float, h: float, ow: float, spring: float, k: int = 8):
    """Front-face polygons of one arched bay in local (x, z) plus the opening's rim polyline."""
    arc = [(-ow / 2 * math.cos(math.pi * i / k), spring + ow / 2 * math.sin(math.pi * i / k)) for i in range(k + 1)]
    polys = [[(-w / 2, 0), (-ow / 2, 0), (-ow / 2, spring), (-ow / 2, h), (-w / 2, h)],
             [(ow / 2, 0), (w / 2, 0), (w / 2, h), (ow / 2, h), (ow / 2, spring)]]
    for i in range(k):
        (x1, z1), (x2, z2) = arc[i], arc[i + 1]
        polys.append([(x1, z1), (x1, h), (x2, h), (x2, z2)])
    rim = [(-ow / 2, 0)] + arc + [(ow / 2, 0)]
    return polys, rim


def bent_bays(mb: MeshBuilder, off: float, depth: float, z0: float, h: float, n: int, open_frac: float,
              spring_frac: float, mat: int, rim_mat: int, face_out: bool = True, phase: float = 0.0) -> None:
    """A ring of n arched bays (one storey) between offsets off and off+depth."""
    for j in range(n):
        t = 2 * math.pi * (j + phase) / n
        w = speed(t, off) * 2 * math.pi / n
        bent_arch(mb, t, off, depth, z0, w, h, w * open_frac, h * spring_frac, mat, rim_mat, face_out)


def bent_arch(mb: MeshBuilder, t: float, off: float, depth: float, z0: float, w: float, h: float, ow: float,
              spring: float, mat: int, rim_mat: int, face_out: bool = True) -> None:
    """One arched bay: a wall w x h with an arched opening ow wide, springing at `spring`, `depth` thick."""
    polys, rim = arch_outline(w, h, ow, spring)
    for side, d in ((0, 0.0), (1, depth)):
        for poly in polys:
            vs = [bend(t, off, x, d, z0 + z) for x, z in poly]
            order = list(range(len(vs)))
            if (side == 0) == face_out:
                order.reverse()
            mb.add(vs, [tuple(order)], mat)
    for (x1, z1), (x2, z2) in zip(rim, rim[1:]):
        vs = [bend(t, off, x1, 0, z0 + z1), bend(t, off, x2, 0, z0 + z2),
              bend(t, off, x2, depth, z0 + z2), bend(t, off, x1, depth, z0 + z1)]
        mb.add(vs, [(0, 1, 2, 3)], rim_mat)


def bent_box(mb: MeshBuilder, t: float, off: float, x0, x1, d0, d1, z0, z1, mat: int) -> None:
    c = [bend(t, off, x, d, z) for z in (z0, z1) for d in (d0, d1) for x in (x0, x1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mb.add(c, faces, mat)


def banner(mb: MeshBuilder, t: float, off: float, w: float, top: float, length: float, mat: int,
           notch: float = 0.5) -> None:
    """A hanging cloth banner with a swallow-tail, just in front of a wall facing the arena."""
    pts = [(-w / 2, top), (w / 2, top), (w / 2, top - length), (0, top - length + notch), (-w / 2, top - length)]
    mb.add([bend(t, off, x, -0.06, z) for x, z in pts], [(0, 1, 2, 3, 4)], mat)


def pennant(mb: MeshBuilder, t: float, off: float, z: float, length: float, mat: int) -> None:
    vs = [bend(t, off, 0, 0, z), bend(t, off, 0, 0, z - 1.1), bend(t, off, length, -0.4, z - 0.5)]
    mb.add(vs, [(0, 1, 2)], mat)


def crowd(rows: list[tuple[float, float, float]], density: float, seed: int, palette) -> bpy.types.Object:
    """Placeholder spectators (two boxes each) on rows [(off of tread start, tread z, tread depth)]."""
    rng = random.Random(seed)
    mb = MeshBuilder()
    cols: list[tuple[float, float, float, float]] = []
    for off, z, depth in rows:
        o = off + depth * 0.45
        n = int(2 * math.pi * math.sqrt(((A0 + o) ** 2 + (B0 + o) ** 2) / 2) / 0.56)
        for j in range(n):
            if rng.random() > density:
                continue
            t = 2 * math.pi * (j + rng.random() * 0.3) / n
            col = palette[rng.randrange(len(palette))]
            skin = (0.55 + rng.random() * 0.3, 0.42 + rng.random() * 0.2, 0.32 + rng.random() * 0.15, 1)
            hh = 0.58 + rng.random() * 0.12
            bent_box(mb, t, o, -0.2, 0.2, -0.14, 0.14, z, z + hh, 0)
            bent_box(mb, t, o, -0.11, 0.11, -0.11, 0.11, z + hh, z + hh + 0.24, 0)
            cols.extend([(*col, 1)] * 8 + [skin] * 8)
    ob = mb.build('crowd_placeholder', [])
    attr = ob.data.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    attr.data.foreach_set('color', [c for rgba in cols for c in rgba])
    m = bpy.data.materials.new('crowd')
    m.use_nodes = True
    nt = m.node_tree
    a = nt.nodes.new('ShaderNodeAttribute')
    a.attribute_name = 'Col'
    nt.links.new(a.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    nt.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
    ob.data.materials.append(m)
    return ob


def pbr(name: str, folder: Path, tex_id: str, tile_m: float, tint=(1, 1, 1), bump: float = 0.25):
    """Box-projected Poly Haven material (object coordinates; no UVs needed): diffuse, roughness, bump from normal."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / tile_m,) * 3
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])

    def tex(kind: str, non_color: bool):
        f = next((folder / tex_id).glob(f'{tex_id}_{kind}_*.jpg'))
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(str(f), check_existing=True)
        if non_color:
            n.image.colorspace_settings.name = 'Non-Color'
        n.projection = 'BOX'
        n.projection_blend = 0.25
        nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
        return n

    d = tex('diff', False)
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs['Factor'].default_value = 1.0
    nt.links.new(d.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = (*tint, 1)
    nt.links.new(mix.outputs['Result'], p.inputs['Base Color'])
    r = tex('rough', True)
    nt.links.new(r.outputs['Color'], p.inputs['Roughness'])
    b = nt.nodes.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = bump
    nt.links.new(r.outputs['Color'], b.inputs['Height'])
    nt.links.new(b.outputs['Normal'], p.inputs['Normal'])
    return m
