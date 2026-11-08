"""Per-pixel marks for Ultra bake materials (body_material, glow_material): node groups instanced once per mark.

Building a mark from loose math nodes costs about ten nodes and their links each; four thousand marks took 525 s to
build from Python. Here every kind of mark is one shared node group (made once per file, cached by name), so a mark is
one group node with its numbers set, plus one MAXIMUM node to join it to the others (about 5 s for 4,000).

    from lib import marks as MK
    pos = nb.coords().outputs['Object']                       # object space = the source's own position
    dots = [MK.dot(nb, pos, c, r) for c, r in spots]          # ellipsoids (Puddlepup's dapples)
    stars = [MK.star(nb, pos, c, n, t, 0.012) for c, n, t in stars]
    lines = [MK.line(nb, pos, a, b, 0.002) for a, b in links]
    mask = MK.union(nb, dots + stars + lines)                 # 0..1, the marks' union (a balanced MAXIMUM tree)

Every mark's numbers are plain values (JSON-able, so make_marks can return them and the bake gets them back).
`glow_material(name, marks_fn)` makes the bake material of the glow pass from the `glow` attribute and any marks.
Pinned to Blender 5.2.
"""
from __future__ import annotations

import bpy

from .nodes import NB, new_mat

GROUPS = {'dot': 'WS_MarkDot', 'star': 'WS_MarkStar', 'line': 'WS_MarkLine'}


def _group(name: str, inputs: list[tuple[str, str, object]]) -> tuple[bpy.types.ShaderNodeTree, NB, bpy.types.Node, bpy.types.Node]:
    g = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    for nm, kind, default in inputs:
        s = g.interface.new_socket(nm, in_out='INPUT', socket_type=kind)
        if default is not None:
            s.default_value = default
    g.interface.new_socket('Mask', in_out='OUTPUT', socket_type='NodeSocketFloat')
    nb = NB(g)
    gi = nb.new('NodeGroupInput')
    go = nb.new('NodeGroupOutput')
    return g, nb, gi, go


def _smooth(nb: NB, x, lo, hi):
    """smoothstep from `lo` to `hi` (sockets or numbers; lo > hi gives 1 inside)."""
    n = nb.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    nb.put(n.inputs['Value'], x)
    nb.put(n.inputs['From Min'], lo)
    nb.put(n.inputs['From Max'], hi)
    n.inputs['To Min'].default_value = 0.0
    n.inputs['To Max'].default_value = 1.0
    return n.outputs['Result']


def dot_group() -> bpy.types.ShaderNodeTree:
    """Mask = 1 inside the ellipsoid (Centre, Radii), a soft edge `Soft` (share of the radius) wide."""
    g = bpy.data.node_groups.get(GROUPS['dot'])
    if g is not None:
        return g
    g, nb, gi, go = _group(GROUPS['dot'], [('Position', 'NodeSocketVector', None), ('Centre', 'NodeSocketVector', None),
                                           ('Radii', 'NodeSocketVector', (0.01, 0.01, 0.01)), ('Soft', 'NodeSocketFloat', 0.08)])
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', gi.outputs['Position'], gi.outputs['Centre']), gi.outputs['Radii'])
    d = nb.vmath('LENGTH', q)
    nb.link(_smooth(nb, d, nb.math('ADD', 1.0, gi.outputs['Soft']), nb.math('SUBTRACT', 1.0, gi.outputs['Soft'])), go.inputs['Mask'])
    return g


def star_group() -> bpy.types.ShaderNodeTree:
    """Mask = 1 inside a star lying on the surface: centre, surface normal, a tangent (where the first point aims),
    outer radius, inner/outer ratio, number of points, point sharpness, a soft edge (share of the radius) and a depth
    (metres off the surface's plane that still count)."""
    g = bpy.data.node_groups.get(GROUPS['star'])
    if g is not None:
        return g
    g, nb, gi, go = _group(GROUPS['star'], [
        ('Position', 'NodeSocketVector', None), ('Centre', 'NodeSocketVector', None), ('Normal', 'NodeSocketVector', (0.0, 0.0, 1.0)),
        ('Tangent', 'NodeSocketVector', (1.0, 0.0, 0.0)), ('Radius', 'NodeSocketFloat', 0.01), ('Inner', 'NodeSocketFloat', 0.45),
        ('Points', 'NodeSocketFloat', 5.0), ('Sharp', 'NodeSocketFloat', 3.0), ('Soft', 'NodeSocketFloat', 0.12), ('Depth', 'NodeSocketFloat', 0.01)])
    n = nb.vmath('NORMALIZE', gi.outputs['Normal'])
    d = nb.vmath('SUBTRACT', gi.outputs['Position'], gi.outputs['Centre'])
    h = nb.vmath('DOT_PRODUCT', d, n)
    dp = nb.vmath('SUBTRACT', d, nb.vmath('SCALE', n, scale=h))
    t = nb.vmath('NORMALIZE', nb.vmath('SUBTRACT', gi.outputs['Tangent'], nb.vmath('SCALE', n, scale=nb.vmath('DOT_PRODUCT', gi.outputs['Tangent'], n))))
    b = nb.vmath('CROSS_PRODUCT', n, t)
    x = nb.vmath('DOT_PRODUCT', dp, t)
    y = nb.vmath('DOT_PRODUCT', dp, b)
    rho = nb.vmath('LENGTH', dp)
    th = nb.math('ARCTAN2', y, x)
    c = nb.math('ABSOLUTE', nb.math('COSINE', nb.math('MULTIPLY', th, nb.math('MULTIPLY', gi.outputs['Points'], 0.5))))
    shape = nb.math('POWER', c, gi.outputs['Sharp'])
    inner = gi.outputs['Inner']
    rs = nb.math('MULTIPLY', gi.outputs['Radius'], nb.math('ADD', inner, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, inner), shape)))
    soft = gi.outputs['Soft']
    m = _smooth(nb, rho, nb.math('MULTIPLY', rs, nb.math('ADD', 1.0, soft)), nb.math('MULTIPLY', rs, nb.math('SUBTRACT', 1.0, soft)))
    deep = _smooth(nb, nb.math('ABSOLUTE', h), gi.outputs['Depth'], nb.math('MULTIPLY', gi.outputs['Depth'], 0.5))
    nb.link(nb.math('MULTIPLY', m, deep), go.inputs['Mask'])
    return g


def line_group() -> bpy.types.ShaderNodeTree:
    """Mask = 1 within `Radius` of the segment A → B (a constellation's line, a stripe, a seam), a soft edge."""
    g = bpy.data.node_groups.get(GROUPS['line'])
    if g is not None:
        return g
    g, nb, gi, go = _group(GROUPS['line'], [('Position', 'NodeSocketVector', None), ('A', 'NodeSocketVector', None), ('B', 'NodeSocketVector', None),
                                            ('Radius', 'NodeSocketFloat', 0.002), ('Soft', 'NodeSocketFloat', 0.3)])
    ab = nb.vmath('SUBTRACT', gi.outputs['B'], gi.outputs['A'])
    ap = nb.vmath('SUBTRACT', gi.outputs['Position'], gi.outputs['A'])
    t = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', ap, ab), nb.math('MAXIMUM', nb.vmath('DOT_PRODUCT', ab, ab), 1e-12), clamp=True)
    q = nb.vmath('ADD', gi.outputs['A'], nb.vmath('SCALE', ab, scale=t))
    d = nb.vmath('DISTANCE', gi.outputs['Position'], q)
    r, soft = gi.outputs['Radius'], gi.outputs['Soft']
    nb.link(_smooth(nb, d, nb.math('MULTIPLY', r, nb.math('ADD', 1.0, soft)), nb.math('MULTIPLY', r, nb.math('SUBTRACT', 1.0, soft))), go.inputs['Mask'])
    return g


def _instance(nb: NB, group: bpy.types.ShaderNodeTree, pos, values: dict):
    node = nb.new('ShaderNodeGroup')
    node.node_tree = group
    nb.put(node.inputs['Position'], pos)
    for k, v in values.items():
        if v is not None:
            nb.put(node.inputs[k], tuple(float(x) for x in v) if isinstance(v, (tuple, list)) else float(v))
    return node.outputs['Mask']


def dot(nb: NB, pos, centre, radii, soft: float = 0.08):
    """One ellipsoid mark (radii a number or (x, y, z))."""
    r = (radii,) * 3 if isinstance(radii, (int, float)) else radii
    return _instance(nb, dot_group(), pos, {'Centre': centre, 'Radii': r, 'Soft': soft})


def star(nb: NB, pos, centre, normal, tangent, radius: float, inner: float = 0.45, points: int = 5, sharp: float = 3.0,
         soft: float = 0.12, depth: float | None = None):
    """One star lying on the surface at `centre` (its `normal`, the first point toward `tangent`)."""
    return _instance(nb, star_group(), pos, {'Centre': centre, 'Normal': normal, 'Tangent': tangent, 'Radius': radius, 'Inner': inner,
                                             'Points': points, 'Sharp': sharp, 'Soft': soft, 'Depth': depth if depth is not None else radius})


def line(nb: NB, pos, a, b, radius: float, soft: float = 0.3):
    """One line mark from a to b, `radius` wide on each side."""
    return _instance(nb, line_group(), pos, {'A': a, 'B': b, 'Radius': radius, 'Soft': soft})


def union(nb: NB, masks: list):
    """The marks' union (MAXIMUM), as a balanced tree; None for no marks."""
    masks = [m for m in masks if m is not None]
    if not masks:
        return None
    while len(masks) > 1:
        nxt = [nb.math('MAXIMUM', masks[i], masks[i + 1]) for i in range(0, len(masks) - 1, 2)]
        if len(masks) % 2:
            nxt.append(masks[-1])
        masks = nxt
    return masks[0]


def glow_material(name: str, marks_fn=None, attr: str = 'glow') -> bpy.types.Material:
    """The glow pass's bake material (build_ultra writes the result into the ORM's alpha): emission grey = the larger of
    the per-vertex `attr` (0 where a source has none) and `marks_fn(nb, pos)`'s mask (a socket, or None), in 0..1."""
    m, nb = new_mat(name)
    g = nb.attribute(attr).outputs['Fac']
    if marks_fn is not None:
        pos = nb.coords().outputs['Object']
        mk = marks_fn(nb, pos)
        if mk is not None:
            g = nb.math('MAXIMUM', g, mk)
    g = nb.math('MINIMUM', nb.math('MAXIMUM', g, 0.0), 1.0)
    em = nb.new('ShaderNodeEmission')
    nb.link(nb.comb(g, g, g), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
