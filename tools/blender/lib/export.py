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


# the glTF exporter drops a sampled bone channel whose values vary by less than this over a clip (NLA_TRACKS mode treats
# every channel as baked: io_scene_gltf2 .../sampled/armature/keyframes.py fcurve_is_constant)
EXPORT_CONSTANT_TOL = 1e-4
# the nudge that keeps a held, non-rest channel: 3x the tolerance, on one middle frame (0.02 degrees, 0.3 mm)
HOLD_NUDGE = 3e-4
CHANNELS = {'location': 'translation', 'rotation_quaternion': 'rotation', 'scale': 'scale'}
REST = {'location': (0.0, 0.0, 0.0), 'rotation_quaternion': (1.0, 0.0, 0.0, 0.0), 'scale': (1.0, 1.0, 1.0)}


def _bone_channels(fcurves) -> dict:
    """{(bone, property): {array_index: fcurve}} for pose-bone location / rotation_quaternion / scale curves."""
    out: dict = {}
    for fc in fcurves:
        p = fc.data_path
        if not p.startswith('pose.bones["'):
            continue
        bone = p[len('pose.bones["'):p.index('"]')]
        prop = p.rsplit('.', 1)[-1]
        if prop in REST:
            out.setdefault((bone, prop), {})[fc.array_index] = fc
    return out


def _held(chans: dict, prop: str) -> tuple[bool, bool]:
    """(constant over the clip, away from the rest value) for one bone property's curves."""
    const, off = True, False
    for i, fc in chans.items():
        vals = [k.co[1] for k in fc.keyframe_points]
        if not vals:
            continue
        if max(vals) - min(vals) >= EXPORT_CONSTANT_TOL:
            const = False
        if abs(vals[0] - REST[prop][i]) > EXPORT_CONSTANT_TOL:
            off = True
    return const, off


def hold_constant_channels(arm: bpy.types.Object, fcurves_of) -> dict[str, list[str]]:
    """Keep every held pose through the export: a bone channel keyed with one constant value away from rest (a bud
    held open, a trunk held up) is dropped by the exporter, and the bone then sits at rest in the game. Each such
    channel gets an invisible nudge on one middle frame (HOLD_NUDGE on its smallest component, so the sampled values
    vary by more than the exporter's tolerance). Channels at rest, and bones a clip does not key (blink and the other
    overlays key only their own bones), are left alone. Returns {clip: ['bone.property', ...]} that were nudged."""
    done: dict[str, list[str]] = {}
    for tr in arm.animation_data.nla_tracks if arm.animation_data else []:
        for strip in tr.strips:
            act = strip.action
            if act is None:
                continue
            for (bone, prop), chans in _bone_channels(fcurves_of(act)).items():
                const, off = _held(chans, prop)
                if not (const and off):
                    continue
                f0, f1 = act.frame_range
                mid = round((f0 + f1) / 2)
                # the component nearest zero: a nudge there changes the normalised rotation by about its own size
                i = min(chans, key=lambda k: abs(chans[k].keyframe_points[0].co[1]))
                fc = chans[i]
                v = fc.evaluate(mid)
                fc.keyframe_points.insert(mid, v + HOLD_NUDGE, options={'FAST'})
                fc.update()
                done.setdefault(tr.name, []).append(f'{bone}.{prop}')
    return done


def glb_channels(path: Path) -> dict[str, set[tuple[str, str]]]:
    """{animation name: {(node name, path)}} read straight from a .glb's JSON chunk."""
    import struct
    data = Path(path).read_bytes()
    n = struct.unpack_from('<I', data, 12)[0]
    gl = json.loads(data[20:20 + n].decode('utf-8'))
    names = [nd.get('name', '') for nd in gl.get('nodes', [])]
    return {a.get('name', ''): {(names[c['target']['node']], c['target']['path']) for c in a.get('channels', []) if 'node' in c['target']}
            for a in gl.get('animations', [])}


def check_exported_channels(path: Path, arm: bpy.types.Object, fcurves_of) -> None:
    """Stop in words when an exported clip lacks a channel its action keys away from rest (a held pose lost: the bone
    would sit at rest in the game)."""
    got = glb_channels(path)
    missing = []
    for tr in arm.animation_data.nla_tracks if arm.animation_data else []:
        for strip in tr.strips:
            if strip.action is None:
                continue
            have = got.get(tr.name, set())
            for (bone, prop), chans in _bone_channels(fcurves_of(strip.action)).items():
                _const, off = _held(chans, prop)
                varies = not _const
                if (off or varies) and (bone, CHANNELS[prop]) not in have:
                    missing.append(f'{tr.name}: {bone} {CHANNELS[prop]}')
    if missing:
        raise SystemExit(f'{path.name}: {len(missing)} keyed bone channels are missing from the export, so those bones would sit at '
                         f'rest in the game: {"; ".join(missing[:12])}{" …" if len(missing) > 12 else ""}')
    C.log(f'export check: every keyed, non-rest bone channel of {sum(len(t.strips) for t in arm.animation_data.nla_tracks)} clips is in the .glb')


def write_sidecar(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=False) + '\n', encoding='utf-8')
    C.log(f'wrote {C.rel(path)}')
    return path
