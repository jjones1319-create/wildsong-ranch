"""toon.py — the palette scheme, the review-render toon material and the inverted-hull outline.

Every Gloamvault mesh carries one colour attribute, `gv` (FLOAT_COLOR, point domain, exported as glTF COLOR_0):
R = palette slot / 15, G = body region / 15, B = 0, A = 1 (tools/blender/palette.json). Faces of different slots
are split apart (their shared edges duplicated) so every vertex has exactly one slot, and the smooth normals are kept
as custom normals across the split, so the toon shading stays continuous while colours change crisply.

The client never reads glTF materials: it builds its own palette toon material (one per character). The Blender
material here only exists so the review renders look like the game: a light-driven 4-step ramp (Ascend's round-2
lesson: the ramp is driven by light only, the colour is multiplied in after it) and an emissive lift for the glow and
gem slots.
"""
import os

import bmesh
import bpy
from mathutils import Vector

from common import TOOLS, hexcol, read_json

PALETTE = read_json(os.path.join(TOOLS, 'palette.json'))
SLOT = {s['name']: s['id'] for s in PALETTE['slots']}
REGION = {r['name']: r['id'] for r in PALETTE['regions']}
EMISSIVE = {s['id'] for s in PALETTE['slots'] if s.get('emissive')}
ATTR = 'gv'
RAMP = (0.42, 0.68, 0.90, 1.06)        # the 4 toon steps (Ascend's values)
RAMP_AT = (0.0, 0.22, 0.50, 0.82)


def ensure_attr(me, slot=0, region=0):
    """The `gv` colour attribute on a mesh, created with every vertex at (slot, region)."""
    at = me.color_attributes.get(ATTR)
    if at is None or at.domain != 'POINT' or at.data_type != 'FLOAT_COLOR':
        if at is not None:
            me.color_attributes.remove(at)
        at = me.color_attributes.new(ATTR, 'FLOAT_COLOR', 'POINT')
        for d in at.data:
            d.color = (slot / 15.0, region / 15.0, 0.0, 1.0)
    me.color_attributes.active_color = at
    try:
        me.color_attributes.render_color_index = me.color_attributes.find(ATTR)
    except Exception:
        pass
    return at


def set_vertex_codes(me, slots=None, regions=None):
    """Writes per-vertex slot and/or region lists (None leaves that channel as it is)."""
    at = ensure_attr(me)
    for i, d in enumerate(at.data):
        r, g, b, a = d.color
        if slots is not None:
            r = slots[i] / 15.0
        if regions is not None:
            g = regions[i] / 15.0
        d.color = (r, g, 0.0, 1.0)


def vertex_codes(me):
    """[(slot, region)] per vertex, decoded."""
    at = ensure_attr(me)
    return [(round(d.color[0] * 15), round(d.color[1] * 15)) for d in at.data]


def split_by_face_slots(ob, face_slots, region_of_vertex=None, normals=None):
    """
    Gives every face its palette slot: edges between faces of different slots are split so each vertex belongs to
    one slot, smooth normals are kept as custom normals, and `gv` is rewritten (regions follow the old vertices).
    `face_slots` is a list (one slot per face, in face order) or a dict face index → slot (others keep slot 0).
    `normals` (one per vertex before the split) replaces the mesh's own smooth normals, e.g. a finer mesh's.
    """
    me = ob.data
    n_faces = len(me.polygons)
    if isinstance(face_slots, dict):
        face_slots = [face_slots.get(i, 0) for i in range(n_faces)]
    old_codes = vertex_codes(me)
    # remember each corner's smooth normal before the split
    me.update()
    smooth = [Vector(n) for n in normals] if normals is not None else [v.normal.copy() for v in me.vertices]
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    slot_layer = bm.faces.layers.int.new('gv_slot')
    old_index = bm.verts.layers.int.new('gv_old')
    for v in bm.verts:
        v[old_index] = v.index
    for f in bm.faces:
        f[slot_layer] = face_slots[f.index]
    cut = [e for e in bm.edges if len(e.link_faces) == 2 and e.link_faces[0][slot_layer] != e.link_faces[1][slot_layer]]
    if cut:
        bmesh.ops.split_edges(bm, edges=cut)
    vert_slot = {}
    vert_old = {}
    for f in bm.faces:
        for v in f.verts:
            vert_slot[v.index] = f[slot_layer]
    for v in bm.verts:
        vert_old[v.index] = v[old_index]
    bm.faces.layers.int.remove(slot_layer)
    bm.verts.layers.int.remove(old_index)
    bm.to_mesh(me)
    bm.free()
    me.update()
    slots = [vert_slot.get(i, 0) for i in range(len(me.vertices))]
    regions = [old_codes[vert_old[i]][1] if region_of_vertex is None else region_of_vertex(vert_old[i]) for i in range(len(me.vertices))]
    set_vertex_codes(me, slots, regions)
    loop_normals = [smooth[vert_old[l.vertex_index]] for l in me.loops]
    me.normals_split_custom_set(loop_normals)
    return me


def palette_material(preview=None, name='GV_Palette'):
    """The review material: `gv`.R → the palette colour (16 constant stops) through a light-driven 4-step ramp."""
    colours = dict(PALETTE['preview'])
    colours.update(preview or {})
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); out.location = (1300, 0)
    attr = nt.nodes.new('ShaderNodeAttribute'); attr.attribute_name = ATTR; attr.location = (-900, 0)
    sep = nt.nodes.new('ShaderNodeSeparateColor'); sep.location = (-700, 0)
    nt.links.new(attr.outputs['Color'], sep.inputs[0])

    def slot_ramp(values, loc):
        r = nt.nodes.new('ShaderNodeValToRGB'); r.location = loc
        r.color_ramp.interpolation = 'CONSTANT'
        els = r.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        els[0].position = 0.0
        els[0].color = values[0]
        for i in range(1, 16):
            e = els.new(max(0.0, i / 15.0 - 0.02))
            e.color = values[i]
        nt.links.new(sep.outputs[0], r.inputs[0])
        return r
    names = [s['name'] for s in sorted(PALETTE['slots'], key=lambda s: s['id'])]
    base = slot_ramp([hexcol(colours[n]) for n in names], (-450, 150))
    glow = slot_ramp([(1, 1, 1, 1) if i in EMISSIVE else (0, 0, 0, 1) for i in range(16)], (-450, -250))
    # light-driven toon ramp
    diff = nt.nodes.new('ShaderNodeBsdfDiffuse'); diff.location = (-450, -600)
    diff.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new('ShaderNodeShaderToRGB'); s2r.location = (-250, -600)
    bw = nt.nodes.new('ShaderNodeRGBToBW'); bw.location = (-80, -600)
    ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.location = (80, -600)
    ramp.color_ramp.interpolation = 'CONSTANT'
    els = ramp.color_ramp.elements
    els[0].position = RAMP_AT[0]; els[0].color = (RAMP[0],) * 3 + (1,)
    els[1].position = RAMP_AT[1]; els[1].color = (RAMP[1],) * 3 + (1,)
    for at, v in zip(RAMP_AT[2:], RAMP[2:]):
        e = els.new(at); e.color = (v,) * 3 + (1,)
    nt.links.new(diff.outputs[0], s2r.inputs[0])
    nt.links.new(s2r.outputs[0], bw.inputs[0])
    nt.links.new(bw.outputs[0], ramp.inputs[0])
    mul = nt.nodes.new('ShaderNodeMix'); mul.location = (400, 0)
    mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    nt.links.new(ramp.outputs['Color'], mul.inputs[6])
    nt.links.new(base.outputs['Color'], mul.inputs[7])
    # emissive slots: the flat colour, brighter, regardless of light
    lift = nt.nodes.new('ShaderNodeMix'); lift.location = (650, 0)
    lift.data_type = 'RGBA'; lift.blend_type = 'MIX'
    nt.links.new(glow.outputs['Color'], lift.inputs['Factor'])
    nt.links.new(mul.outputs[2], lift.inputs[6])
    bright = nt.nodes.new('ShaderNodeMix'); bright.location = (400, -250)
    bright.data_type = 'RGBA'; bright.blend_type = 'MULTIPLY'; bright.inputs['Factor'].default_value = 1.0
    bright.inputs[7].default_value = (1.6, 1.6, 1.6, 1)
    nt.links.new(base.outputs['Color'], bright.inputs[6])
    nt.links.new(bright.outputs[2], lift.inputs[7])
    em = nt.nodes.new('ShaderNodeEmission'); em.location = (950, 0)
    nt.links.new(lift.outputs[2], em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def outline_material(name='GV_Outline'):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.006, 0.005, 0.009, 1)
    nt.links.new(em.outputs[0], out.inputs[0])
    m.use_backface_culling = True
    # the hull encloses the surface: if it cast shadows the whole surface would sit in its shade and the toon ramp
    # would read one flat step (found in Phase 5 round 1)
    m.use_backface_culling_shadow = True
    return m


def apply_look(ob, preview=None, outline=0.006):
    """Gives a mesh the review material (slot 0) and an inverted-hull outline (slot 1, a Solidify named Outline)."""
    me = ob.data
    me.materials.clear()
    me.materials.append(palette_material(preview))
    me.materials.append(outline_material())
    for p in me.polygons:
        p.material_index = 0
    if outline and 'Outline' not in ob.modifiers:
        so = ob.modifiers.new('Outline', 'SOLIDIFY')
        so.thickness = outline        # a shell outside the surface (offset 1, flipped normals); a negative thickness
        so.offset = 1.0               # moved every surface inward and made linings swap with their cloth (round 2)
        so.use_flip_normals = True
        so.use_rim = False
        so.material_offset = 1
        so.use_quality_normals = True
    return ob


def remove_outlines(objects=None):
    for ob in objects or bpy.data.objects:
        if ob.type == 'MESH' and 'Outline' in ob.modifiers:
            ob.modifiers.remove(ob.modifiers['Outline'])
