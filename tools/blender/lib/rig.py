"""Armatures, skinning and sockets (Blender 5.2)."""
from __future__ import annotations

from dataclasses import dataclass

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import common as C


@dataclass
class BoneSpec:
    name: str
    head: tuple[float, float, float]
    tail: tuple[float, float, float]
    parent: str | None = None
    roll: float = 0.0
    deform: bool = True
    connect: bool = False
    radius: float = 0.18          # distance-weight falloff radius (fallback skinning)
    inherit_scale: str = 'FULL'   # FULL | NONE | FIX_SHEAR ...


def build_armature(name: str, specs: list[BoneSpec]) -> bpy.types.Object:
    data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, data)
    C.link_obj(arm)
    C.set_active(arm)
    with bpy.context.temp_override(object=arm, active_object=arm, selected_objects=[arm], selected_editable_objects=[arm]):
        bpy.ops.object.mode_set(mode='EDIT')
        ebs = {}
        for s in specs:
            eb = data.edit_bones.new(s.name)
            eb.head = Vector(s.head)
            eb.tail = Vector(s.tail)
            eb.roll = s.roll
            eb.use_deform = s.deform
            eb.inherit_scale = s.inherit_scale
            ebs[s.name] = eb
        for s in specs:
            if s.parent:
                ebs[s.name].parent = ebs[s.parent]
                ebs[s.name].use_connect = s.connect
        bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    data.display_type = 'STICK'
    deform = [s.name for s in specs if s.deform]
    C.log(f'armature {name}: {len(specs)} bones, {len(deform)} deform')
    return arm


def rest_matrix(arm: bpy.types.Object, bone: str) -> Matrix:
    """The bone's rest matrix in armature space (3x3)."""
    return arm.data.bones[bone].matrix_local.to_3x3()


def bone_world(arm: bpy.types.Object, bone: str) -> tuple[Vector, Vector]:
    b = arm.data.bones[bone]
    return arm.matrix_world @ b.head_local, arm.matrix_world @ b.tail_local


def skin_auto(body: bpy.types.Object, arm: bpy.types.Object) -> bool:
    """Automatic (heat) weights. Returns False when Blender could not solve them."""
    try:
        C.set_active(arm, [body, arm])
        with bpy.context.temp_override(object=arm, active_object=arm, selected_objects=[body, arm], selected_editable_objects=[body, arm]):
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    except Exception as e:  # noqa: BLE001
        C.log(f'automatic weights failed: {e}')
        return False
    groups = [g for g in body.vertex_groups]
    if not groups:
        C.log('automatic weights: no vertex groups made')
        return False
    # a bone with no weight at all means the solve failed quietly for it
    counts = {g.name: 0 for g in groups}
    for v in body.data.vertices:
        for g in v.groups:
            if g.weight > 0.01:
                counts[body.vertex_groups[g.group].name] += 1
    empty = [n for n, c in counts.items() if c == 0]
    if empty:
        C.log(f'automatic weights: empty groups {empty}')
    return True


def _segment_dist(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(1e-9, ab @ ab), 0.0, 1.0)
    proj = a + t[:, None] * ab
    return np.linalg.norm(p - proj, axis=1)


def skin_distance(body: bpy.types.Object, arm: bpy.types.Object, specs: list[BoneSpec], max_influences: int = 4) -> None:
    """Deterministic fallback: weights fall off with distance to each deform bone's segment."""
    verts = np.array([body.matrix_world @ v.co for v in body.data.vertices], dtype=np.float64)
    names = [s.name for s in specs if s.deform]
    W = np.zeros((len(verts), len(names)), dtype=np.float64)
    for j, s in enumerate(specs):
        if not s.deform:
            continue
        a = np.array(arm.matrix_world @ Vector(s.head))
        b = np.array(arm.matrix_world @ Vector(s.tail))
        d = _segment_dist(verts, a, b)
        W[:, names.index(s.name)] = np.clip(1.0 - d / s.radius, 0.0, 1.0) ** 2
    # keep the strongest influences, normalise
    if max_influences < W.shape[1]:
        idx = np.argsort(-W, axis=1)[:, max_influences:]
        np.put_along_axis(W, idx, 0.0, axis=1)
    s = W.sum(axis=1, keepdims=True)
    s[s == 0] = 1.0
    W /= s
    body.vertex_groups.clear()
    for j, n in enumerate(names):
        vg = body.vertex_groups.new(name=n)
        for i in np.nonzero(W[:, j] > 1e-4)[0]:
            vg.add([int(i)], float(W[i, j]), 'REPLACE')
    mod = body.modifiers.get('Armature') or body.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    body.parent = arm
    body.matrix_parent_inverse = arm.matrix_world.inverted()


def smooth_weights(body: bpy.types.Object, iterations: int = 3, factor: float = 0.5) -> None:
    """Laplacian smoothing of all vertex groups (keeps joints from pinching after automatic weights)."""
    me = body.data
    n = len(me.vertices)
    groups = list(body.vertex_groups)
    if not groups or n == 0:
        return
    W = np.zeros((n, len(groups)), dtype=np.float64)
    for v in me.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    # adjacency
    edges = np.array([[e.vertices[0], e.vertices[1]] for e in me.edges], dtype=np.int64)
    deg = np.bincount(edges.ravel(), minlength=n).astype(np.float64)
    deg[deg == 0] = 1.0
    for _ in range(iterations):
        acc = np.zeros_like(W)
        np.add.at(acc, edges[:, 0], W[edges[:, 1]])
        np.add.at(acc, edges[:, 1], W[edges[:, 0]])
        avg = acc / deg[:, None]
        W = W * (1.0 - factor) + avg * factor
        s = W.sum(axis=1, keepdims=True)
        s[s == 0] = 1.0
        W /= s
    for j, g in enumerate(groups):
        g.remove(list(range(n)))
        nz = np.nonzero(W[:, j] > 1e-3)[0]
        for i in nz:
            g.add([int(i)], float(W[i, j]), 'REPLACE')


def add_socket(arm: bpy.types.Object, name: str, bone: str, world_pos: Vector) -> bpy.types.Object:
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = 0.05
    C.link_obj(e)
    e.parent = arm
    e.parent_type = 'BONE'
    e.parent_bone = bone
    bpy.context.view_layer.update()
    e.matrix_world = Matrix.Translation(Vector(world_pos))
    return e


def parent_to_bone(obj: bpy.types.Object, arm: bpy.types.Object, bone: str) -> None:
    world = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = 'BONE'
    obj.parent_bone = bone
    bpy.context.view_layer.update()
    obj.matrix_world = world


def reset_pose(arm: bpy.types.Object) -> None:
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)


def log_axes(arm: bpy.types.Object, names: list[str]) -> None:
    for n in names:
        m = rest_matrix(arm, n)
        x, y, z = m.col[0], m.col[1], m.col[2]
        C.log(f'  axes {n}: X=({x.x:+.2f},{x.y:+.2f},{x.z:+.2f}) Y=({y.x:+.2f},{y.y:+.2f},{y.z:+.2f}) Z=({z.x:+.2f},{z.y:+.2f},{z.z:+.2f})')
