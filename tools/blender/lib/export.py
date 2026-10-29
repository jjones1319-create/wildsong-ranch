"""glTF export (Blender 5.2) and the sidecar JSON a look ships with."""
from __future__ import annotations

import json
from pathlib import Path

import bpy

from . import common as C

# What the runtime needs besides the .glb (ART_2_PLAN §5 metadata): written by `write_sidecar`.
EXPORT_OPTIONS = dict(
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_yup=True,
    export_texcoords=True,
    export_normals=True,
    export_tangents=False,
    export_materials='EXPORT',
    export_image_format='WEBP',
    export_image_quality=88,
    export_cameras=False,
    export_lights=False,
    export_extras=True,
    export_animations=True,
    export_animation_mode='NLA_TRACKS',
    export_force_sampling=True,
    export_frame_step=1,
    export_anim_slide_to_zero=True,
    export_negative_frame='SLIDE',
    export_optimize_animation_size=True,
    export_optimize_animation_keep_anim_armature=False,
    export_optimize_animation_keep_anim_object=False,
    export_bake_animation=False,
    export_nla_strips=True,
    export_anim_single_armature=True,
    export_def_bones=True,
    export_skins=True,
    export_influence_nb=4,
    export_morph=False,
    export_rest_position_armature=True,
    export_leaf_bone=False,
    export_hierarchy_flatten_bones=False,
    export_armature_object_remove=False,
    export_shared_accessors=True,
    export_unused_images=False,
    export_unused_textures=False,
    export_attributes=False,
    export_all_vertex_colors=False,
    export_gn_mesh=False,
    export_current_frame=False,
    use_mesh_edges=False,
    use_mesh_vertices=False,
)


def export_glb(path: Path, objects: list[bpy.types.Object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    props = {p.identifier for p in bpy.ops.export_scene.gltf.get_rna_type().properties}
    opts = {k: v for k, v in EXPORT_OPTIONS.items() if k in props}
    dropped = sorted(set(EXPORT_OPTIONS) - set(opts))
    if dropped:
        C.log(f'export: options not in this Blender: {dropped}')
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objects:
        o.hide_set(False)
        o.hide_viewport = False
        o.hide_render = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    with C.Timer('glTF export'):
        bpy.ops.export_scene.gltf(filepath=str(path), **opts)
    size = path.stat().st_size
    C.log(f'wrote {C.rel(path)} ({size / 1024:.0f} KB)')
    return path


def write_sidecar(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=False) + '\n', encoding='utf-8')
    C.log(f'wrote {C.rel(path)}')
    return path
