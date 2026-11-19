"""export.py — glTF export with Gloamvault's settings, plus validation and the re-import check (11 §7, §8.5).

Settings: GLB, +Y up, deform bones only, 4 influences, modifiers applied (the review outline is removed first —
outlines are the client's job), no glTF materials (the client builds its palette toon material), the active colour
attribute `gv` as COLOR_0, morph targets without morph normals (smaller files; toon shading hides it), custom
properties as `extras`. Only the keyword arguments this Blender's exporter knows are passed.
"""
import os

import bpy

from common import REPO, log, tri_count
from toon import remove_outlines

BASE_SETTINGS = dict(
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_yup=True,
    export_def_bones=True,
    export_skins=True,
    export_influence_nb=4,
    export_all_influences=False,
    export_morph=True,
    export_morph_normal=False,
    export_morph_tangent=False,
    export_texcoords=True,
    export_normals=True,
    export_tangents=False,
    export_materials='NONE',
    export_vertex_color='ACTIVE',
    export_all_vertex_colors=False,
    export_extras=True,
    export_cameras=False,
    export_lights=False,
    export_optimize_animation_size=False,
    export_reset_pose_bones=True,
)


def _supported(kwargs):
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    return {k: v for k, v in kwargs.items() if k in props}


def export_glb(path, objects, animations=False, animation_mode='ACTIONS', extra=None):
    """Exports exactly `objects` (and nothing else) to `path`; returns the file size in KB."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for ob in objects:
        ob.hide_viewport = False
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    kw = dict(BASE_SETTINGS)
    kw['export_animations'] = animations
    if animations:
        kw['export_animation_mode'] = animation_mode
        kw['export_nla_strips'] = animation_mode == 'NLA_TRACKS'
    kw.update(extra or {})
    bpy.ops.export_scene.gltf(filepath=path, **_supported(kw))
    kb = os.path.getsize(path) / 1024
    log('exported', os.path.relpath(path, REPO), '%.1f KB' % kb)
    return kb


FBX_SETTINGS = dict(
    use_selection=True,
    object_types={'MESH'},
    apply_scale_options='FBX_SCALE_ALL',   # metres stay metres in Unity (no 100× unit scale)
    axis_forward='-Z',
    axis_up='Y',
    bake_space_transform=True,              # the axis change baked into the vertices: identity transforms in Unity
    use_mesh_modifiers=True,
    mesh_smooth_type='OFF',                 # per-loop (custom split) normals written as they are
    use_custom_props=True,
    colors_type='LINEAR',                   # the `gv` codes as linear floats: slot/15 stays a whole code
    add_leaf_bones=False,
    use_armature_deform_only=True,
    bake_anim=False,
    embed_textures=False,
    path_mode='AUTO',
)


def _fbx_supported(kwargs):
    props = bpy.ops.export_scene.fbx.get_rna_type().properties.keys()
    return {k: v for k, v in kwargs.items() if k in props}


RIGGED_FBX_SETTINGS = dict(
    object_types={'MESH', 'ARMATURE', 'EMPTY'},  # the rig and the socket empties come too
    bake_space_transform=False,                  # a skinned mesh keeps its armature's frame; Unity applies the axes
    bake_anim=True,                              # every action as a take, named <armature>|<action>
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=True,
    bake_anim_force_startend_keying=True,
    bake_anim_step=1.0,
    bake_anim_simplify_factor=0.0,
    primary_bone_axis='Y',
    secondary_bone_axis='X',
    armature_nodetype='NULL',
    use_mesh_modifiers=False,                    # shape keys survive only when modifiers are not applied
)


def export_fbx(path, objects, at_origin=True, extra=None, rigged=False):
    """
    Exports exactly `objects` to an FBX for Unity (D-140, Phase 11): metres, -Z forward / Y up baked into the vertices,
    linear vertex colours, custom normals. With `at_origin` every top-level object is moved to the origin for the
    export and put back (a kit's pieces are a library, not a layout). `rigged` (Phase 12): armatures, socket empties,
    shape keys and every action as an animation take — for heroes and monsters. Returns the file size in KB.
    """
    if rigged:
        at_origin = False
        extra = dict(RIGGED_FBX_SETTINGS, **(extra or {}))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    saved = {}
    if at_origin:
        for ob in objects:
            if ob.parent is None or ob.parent not in objects:
                saved[ob] = ob.matrix_world.copy()
                ob.matrix_world = ob.matrix_world.__class__.Translation((0.0, 0.0, 0.0)) @ ob.matrix_world.to_3x3().to_4x4()
        bpy.context.view_layer.update()
    try:
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for ob in objects:
            ob.hide_viewport = False
            ob.hide_set(False)
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        kw = dict(FBX_SETTINGS)
        kw.update(extra or {})
        bpy.ops.export_scene.fbx(filepath=path, **_fbx_supported(kw))
    finally:
        for ob, m in saved.items():
            ob.matrix_world = m
        if saved:
            bpy.context.view_layer.update()
    kb = os.path.getsize(path) / 1024
    log('exported', os.path.relpath(path, REPO), '%.1f KB' % kb)
    return kb


def stash_actions(arm_ob, names):
    """Puts each named action on its own muted NLA track so the ACTIONS export mode writes all of them (Ascend's lesson)."""
    adt = arm_ob.animation_data or arm_ob.animation_data_create()
    adt.action = None
    for t in list(adt.nla_tracks):
        adt.nla_tracks.remove(t)
    for nm in names:
        act = bpy.data.actions[nm]
        tr = adt.nla_tracks.new()
        tr.name = nm
        st = tr.strips.new(nm, 0, act)
        st.name = nm
        tr.mute = True


def validate(objects, armature=None):
    """Lines for the build log: tris per mesh, weight sums, unapplied scale, deform bones."""
    lines = ['| object | tris | verts |', '|---|---:|---:|']
    total = 0
    for ob in sorted((o for o in objects if o.type == 'MESH'), key=lambda o: o.name):
        n = tri_count(ob)
        total += n
        lines.append('| %s | %d | %d |' % (ob.name, n, len(ob.data.vertices)))
    lines.append('| **total** | **%d** | |' % total)
    bad = 0
    for ob in objects:
        if ob.type != 'MESH' or not ob.vertex_groups:
            continue
        for v in ob.data.vertices:
            s = sum(g.weight for g in v.groups)
            if abs(s - 1.0) > 0.01:
                bad += 1
    lines.append('')
    lines.append('- vertices whose weights do not sum to 1 (±0.01): **%d**' % bad)
    unapplied = [o.name for o in objects if o.type in ('MESH', 'ARMATURE') and any(abs(s - 1.0) > 1e-5 for s in o.scale)]
    lines.append('- objects with unapplied scale: **%s**' % (', '.join(unapplied) if unapplied else 'none'))
    if armature:
        lines.append('- bones on %s: %d (deform %d)' % (armature.name, len(armature.data.bones), len([b for b in armature.data.bones if b.use_deform])))
    return lines


def normalize_weights(ob, limit=4):
    """Keeps the 4 strongest influences per vertex and makes them sum to 1."""
    groups = ob.vertex_groups
    for v in ob.data.vertices:
        ws = sorted(((g.group, g.weight) for g in v.groups if g.weight > 0), key=lambda t: -t[1])
        keep = ws[:limit]
        drop = ws[limit:]
        for gi, _ in drop:
            groups[gi].remove([v.index])
        s = sum(w for _, w in keep)
        if s <= 0:
            continue
        for gi, w in keep:
            groups[gi].add([v.index], w / s, 'REPLACE')


def reimport_report(glb_path, render_path=None):
    """Imports the .glb into a clean scene: meshes, armatures, animations, COLOR_0 present; an optional Workbench render."""
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('Icosphere')]
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    lines = ['- re-import of %s: %d meshes, %d armatures, %d animations' % (os.path.basename(glb_path), len(meshes), len(arms), len(bpy.data.actions))]
    for o in meshes:
        cols = [a.name for a in o.data.color_attributes]
        keys = len(o.data.shape_keys.key_blocks) - 1 if o.data.shape_keys else 0
        lines.append('  - %s: %d verts, colour attributes %s, morph targets %d, skinned %s' % (o.name, len(o.data.vertices), cols, keys, bool(o.vertex_groups)))
    for a in arms:
        lines.append('  - armature %s: %d bones' % (a.name, len(a.data.bones)))
    if bpy.data.actions:
        lines.append('  - animations: %s' % ', '.join(sorted(a.name for a in bpy.data.actions)))
    if render_path:
        sc = bpy.context.scene
        sc.render.engine = 'BLENDER_WORKBENCH'
        sc.display.shading.light = 'STUDIO'
        sc.display.shading.color_type = 'VERTEX' if any(o.data.color_attributes for o in meshes) else 'MATERIAL'
        sc.render.resolution_x = sc.render.resolution_y = 768
        cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
        sc.collection.objects.link(cam)
        cam.location = (-2.0, -2.6, 1.5)
        d = Vector((0.0, 0, 0.9)) - cam.location
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = 50
        sc.camera = cam
        w = bpy.data.worlds.new('W')
        sc.world = w
        w.color = (0.05, 0.05, 0.07)
        sc.render.filepath = render_path
        bpy.ops.render.render(write_still=True)
        lines.append('  - rendered %s' % os.path.relpath(render_path, REPO))
    return lines


def prepare_for_export(objects):
    remove_outlines(objects)
