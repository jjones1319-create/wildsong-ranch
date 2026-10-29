"""Node-tree helpers (Blender 5.2): the NB builder from `ranch_scenes.py`, plus small material factories."""
from __future__ import annotations

import bpy


class NB:
    """Tiny helper for building shader node trees from Python."""

    def __init__(self, tree: bpy.types.NodeTree):
        self.t = tree

    def new(self, kind: str, **props):
        n = self.t.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.t.links.new(a, b)

    def put(self, sock, val):
        if isinstance(val, bpy.types.NodeSocket):
            self.t.links.new(val, sock)
        elif val is not None:
            if isinstance(val, tuple):
                try:
                    n = len(sock.default_value)
                except TypeError:
                    n = 1
                if n > 1:
                    val = tuple(val[:n]) + (1.0,) * max(0, n - len(val))
                else:
                    val = val[0]
            sock.default_value = val

    @staticmethod
    def sin_(n, ident):
        return next(s for s in n.inputs if s.identifier == ident)

    @staticmethod
    def sout(n, ident):
        return next(s for s in n.outputs if s.identifier == ident)

    @staticmethod
    def by_name(socks, name, typ=None):
        for s in socks:
            if s.name == name and s.enabled and (typ is None or s.type == typ):
                return s
        raise KeyError(name)

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if c is not None:
            self.put(n.inputs[2], c)
        return n.outputs[0]

    def vmath(self, op, a, b=None, c=None, scale=None):
        n = self.new('ShaderNodeVectorMath', operation=op)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if c is not None:
            self.put(n.inputs[2], c)
        if scale is not None:
            self.put(n.inputs[3], scale)
        if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE'):
            return n.outputs[1]
        return n.outputs[0]

    def mix(self, fac, a, b, dtype='RGBA', blend='MIX'):
        n = self.new('ShaderNodeMix', data_type=dtype)
        if dtype == 'RGBA':
            n.blend_type = blend
        key = {'FLOAT': 'Float', 'VECTOR': 'Vector', 'RGBA': 'Color'}[dtype]
        self.put(self.sin_(n, 'Factor_Float'), fac)
        self.put(self.sin_(n, 'A_' + key), a)
        self.put(self.sin_(n, 'B_' + key), b)
        return self.sout(n, 'Result_' + key)

    def sep(self, v):
        n = self.new('ShaderNodeSeparateXYZ')
        self.put(n.inputs[0], v)
        return n.outputs

    def sep_rgb(self, c):
        n = self.new('ShaderNodeSeparateColor')
        self.put(n.inputs[0], c)
        return n.outputs

    def comb(self, x, y, z):
        n = self.new('ShaderNodeCombineXYZ')
        self.put(n.inputs[0], x)
        self.put(n.inputs[1], y)
        self.put(n.inputs[2], z)
        return n.outputs[0]

    def rgb(self, c):
        n = self.new('ShaderNodeRGB')
        n.outputs[0].default_value = tuple(c[:3]) + (1.0,)
        return n.outputs[0]

    def val(self, v):
        n = self.new('ShaderNodeValue')
        n.outputs[0].default_value = v
        return n.outputs[0]

    def smooth(self, x, a, b):
        """smoothstep(a, b, x) in 0..1 (works for a > b too)."""
        n = self.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        self.put(n.inputs['Value'], x)
        n.inputs['From Min'].default_value = a
        n.inputs['From Max'].default_value = b
        n.inputs['To Min'].default_value = 0.0
        n.inputs['To Max'].default_value = 1.0
        return n.outputs['Result']

    def noise(self, vec, scale, detail=2.0, rough=0.5):
        n = self.new('ShaderNodeTexNoise')
        self.put(n.inputs['Vector'], vec)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        return n.outputs['Fac']

    def voronoi(self, vec, scale, feature='F1', randomness=1.0):
        n = self.new('ShaderNodeTexVoronoi', feature=feature)
        self.put(n.inputs['Vector'], vec)
        n.inputs['Scale'].default_value = scale
        n.inputs['Randomness'].default_value = randomness
        return n.outputs['Distance']

    def attribute(self, name, kind='GEOMETRY'):
        n = self.new('ShaderNodeAttribute', attribute_name=name, attribute_type=kind)
        return n

    def coords(self):
        return self.new('ShaderNodeTexCoord')

    def ramp(self, fac, stops):
        """A colour ramp from [(pos, (r,g,b)), ...] with linear interpolation."""
        n = self.new('ShaderNodeValToRGB')
        cr = n.color_ramp
        cr.interpolation = 'LINEAR'
        while len(cr.elements) > 1:
            cr.elements.remove(cr.elements[-1])
        cr.elements[0].position = stops[0][0]
        cr.elements[0].color = tuple(stops[0][1][:3]) + (1.0,)
        for pos, col in stops[1:]:
            e = cr.elements.new(pos)
            e.color = tuple(col[:3]) + (1.0,)
        self.put(n.inputs['Fac'], fac)
        return n.outputs['Color']

    def output(self, shader):
        out = self.new('ShaderNodeOutputMaterial')
        self.link(shader, out.inputs['Surface'])
        return out


def new_mat(name: str) -> tuple[bpy.types.Material, NB]:
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    m.node_tree.nodes.clear()
    return m, NB(m.node_tree)


def emission_mat(name: str, color, strength: float = 1.0, alpha: float = 1.0) -> bpy.types.Material:
    """A flat, unlit colour. `color` is linear RGB(A)."""
    m, nb = new_mat(name)
    em = nb.new('ShaderNodeEmission')
    nb.put(em.inputs['Color'], tuple(color[:3]) + (1.0,))
    em.inputs['Strength'].default_value = strength
    if alpha < 1.0:
        tr = nb.new('ShaderNodeBsdfTransparent')
        mx = nb.new('ShaderNodeMixShader')
        mx.inputs[0].default_value = alpha
        nb.link(tr.outputs[0], mx.inputs[1])
        nb.link(em.outputs[0], mx.inputs[2])
        nb.output(mx.outputs[0])
        m.surface_render_method = 'BLENDED'
    else:
        nb.output(em.outputs[0])
    return m


def principled_image_mat(name: str, image: bpy.types.Image, emission: bpy.types.Image | None = None,
                         alpha_from_image: bool = False, roughness: float = 0.8) -> bpy.types.Material:
    """The export material the glTF exporter understands: Principled with a base-colour (and optional emission) image."""
    m, nb = new_mat(name)
    tex = nb.new('ShaderNodeTexImage', image=image, interpolation='Linear')
    bsdf = nb.new('ShaderNodeBsdfPrincipled')
    nb.link(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Specular IOR Level'].default_value = 0.2
    if alpha_from_image:
        nb.link(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
        m.surface_render_method = 'BLENDED'
    if emission is not None:
        et = nb.new('ShaderNodeTexImage', image=emission, interpolation='Linear')
        nb.link(et.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = 1.0
    nb.output(bsdf.outputs[0])
    return m


def new_image(name: str, size: int, alpha: bool = True, color=(0, 0, 0, 0), srgb: bool = True) -> bpy.types.Image:
    img = bpy.data.images.new(name, width=size, height=size, alpha=alpha, float_buffer=False)
    img.generated_color = color
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    img.alpha_mode = 'STRAIGHT'
    return img
