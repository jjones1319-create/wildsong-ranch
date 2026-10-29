"""Mesh building (Blender 5.2): rounded primitives, merging into one smooth body, UVs and head patches.

Recipes are data (ART_2_PLAN §3.1): a breed is a list of primitives placed and sized by numbers; this module
turns them into one smooth, decimated, UV-unwrapped mesh.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from . import common as C

BODY_COLL = 'MonsterParts'


@dataclass
class Part:
    """One rounded primitive of a recipe. Scale is applied before rotation; location last."""
    name: str
    kind: str                                   # sphere | capsule | tube | fin | paddle | box
    loc: tuple[float, float, float] = (0, 0, 0)
    radius: float = 0.1
    scale: tuple[float, float, float] = (1, 1, 1)
    rot: tuple[float, float, float] = (0, 0, 0)   # degrees XYZ
    # capsule / tube: from loc to `to`, with radius (and r2 for tapered tubes)
    to: tuple[float, float, float] | None = None
    r2: float | None = None
    # fin / paddle: taper 0..1 along +Y of the primitive (before rotation)
    taper: float = 0.6
    mirror: bool = False                          # also build the X-mirrored twin (name + '.R')
    extra: dict = field(default_factory=dict)


def _mesh_from_bm(name: str, bm: bmesh.types.BMesh) -> bpy.types.Mesh:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def _transform(bm: bmesh.types.BMesh, fn) -> None:
    for v in bm.verts:
        v.co = fn(v.co)


def _part_matrix(p: Part) -> Matrix:
    return Matrix.Translation(Vector(p.loc)) @ Euler([math.radians(a) for a in p.rot], 'XYZ').to_matrix().to_4x4()


def build_part(p: Part, coll: bpy.types.Collection, segments: int = 32) -> list[bpy.types.Object]:
    objs = []
    for side in ((1, -1) if p.mirror else (1,)):
        bm = bmesh.new()
        if p.kind in ('sphere', 'fin', 'paddle'):
            bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=segments // 2, radius=p.radius)
            sx, sy, sz = p.scale
            if p.kind == 'fin':
                # A flattened teardrop: wide at the base (−Y), narrowing toward the tip (+Y).
                t = p.taper
                r = p.radius

                def f(co, sx=sx, sy=sy, sz=sz, t=t, r=r):
                    k = (co.y / r + 1.0) * 0.5          # 0 at the base, 1 at the tip
                    w = 1.0 - t * C.ease_in(k)
                    return Vector((co.x * sx * w, co.y * sy, co.z * sz * (0.7 + 0.3 * w)))
                _transform(bm, f)
            elif p.kind == 'paddle':
                # A flattened paddle: narrow at the base, widest near the tip, rounded.
                t = p.taper
                r = p.radius

                def f(co, sx=sx, sy=sy, sz=sz, t=t, r=r):
                    k = (co.y / r + 1.0) * 0.5
                    w = (1.0 - t) + t * math.sin(min(1.0, k * 1.15) * math.pi * 0.5)
                    return Vector((co.x * sx * w, co.y * sy, co.z * sz))
                _transform(bm, f)
            else:
                _transform(bm, lambda co, sx=sx, sy=sy, sz=sz: Vector((co.x * sx, co.y * sy, co.z * sz)))
        elif p.kind in ('capsule', 'tube'):
            a = Vector(p.loc)
            b = Vector(p.to or p.loc)
            axis = b - a
            length = max(1e-4, axis.length)
            r1 = p.radius
            r2 = p.r2 if (p.kind == 'tube' and p.r2 is not None) else p.radius
            bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r1, radius2=r2, depth=length)
            # cone runs along Z centred at 0: move so it spans 0..length, then end spheres
            _transform(bm, lambda co: Vector((co.x, co.y, co.z + length * 0.5)))
            s1 = bmesh.new()
            bmesh.ops.create_uvsphere(s1, u_segments=segments, v_segments=segments // 2, radius=r1)
            s2 = bmesh.new()
            bmesh.ops.create_uvsphere(s2, u_segments=segments, v_segments=segments // 2, radius=r2)
            _transform(s2, lambda co: Vector((co.x, co.y, co.z + length)))
            for s in (s1, s2):
                tmp = bpy.data.meshes.new('tmp')
                s.to_mesh(tmp)
                s.free()
                bm.from_mesh(tmp)
                bpy.data.meshes.remove(tmp)
            # orient Z onto the axis
            q = Vector((0, 0, 1)).rotation_difference(axis.normalized())
            m = q.to_matrix().to_4x4()
            _transform(bm, lambda co, m=m: m @ co)
            # the matrix below only translates to `loc`
        elif p.kind == 'box':
            bmesh.ops.create_cube(bm, size=1.0)
            sx, sy, sz = p.scale
            _transform(bm, lambda co, sx=sx, sy=sy, sz=sz: Vector((co.x * sx * 2 * p.radius, co.y * sy * 2 * p.radius, co.z * sz * 2 * p.radius)))
        else:
            raise ValueError(p.kind)

        if p.kind in ('capsule', 'tube'):
            m = Matrix.Translation(Vector(p.loc))
        else:
            m = _part_matrix(p)
        if side < 0:
            m = Matrix.Diagonal((-1, 1, 1, 1)) @ m
        _transform(bm, lambda co, m=m: m @ co)
        if side < 0:
            # mirroring flips winding; fix normals
            for f_ in bm.faces:
                f_.normal_flip()
        me = _mesh_from_bm(p.name + ('.R' if side < 0 else ''), bm)
        me.shade_smooth()
        ob = bpy.data.objects.new(me.name, me)
        ob['part'] = p.name
        C.link_obj(ob, coll)
        objs.append(ob)
    return objs


def join_meshes(objs: list[bpy.types.Object], name: str) -> bpy.types.Object:
    bm = bmesh.new()
    for o in objs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = _mesh_from_bm(name, bm)
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def tri_count(obj: bpy.types.Object) -> int:
    me = obj.data
    return sum(len(p.vertices) - 2 for p in me.polygons)


def merge_smooth(parts: list[bpy.types.Object], name: str, voxel: float = 0.012, smooth_iters: int = 6,
                 smooth_factor: float = 0.5, target_tris: int = 8000) -> bpy.types.Object:
    """Join → voxel remesh → smooth → decimate to budget → smooth shading. Returns the new body object."""
    body = join_meshes(parts, name)
    with C.Timer('remesh'):
        rm = body.modifiers.new('remesh', 'REMESH')
        rm.mode = 'VOXEL'
        rm.voxel_size = voxel
        rm.use_smooth_shade = True
        sm = body.modifiers.new('smooth', 'SMOOTH')
        sm.factor = smooth_factor
        sm.iterations = smooth_iters
        C.apply_modifiers(body)
    n = tri_count(body)
    C.log(f'{name}: remeshed {n} tris')
    if n > target_tris:
        with C.Timer('decimate'):
            dm = body.modifiers.new('decimate', 'DECIMATE')
            dm.decimate_type = 'COLLAPSE'
            dm.ratio = target_tris / n
            dm.use_collapse_triangulate = True
            C.apply_modifiers(body)
        # a light smoothing pass evens out the collapse
        sm = body.modifiers.new('smooth2', 'SMOOTH')
        sm.factor = 0.35
        sm.iterations = 2
        C.apply_modifiers(body)
    body.data.shade_smooth()
    C.log(f'{name}: {tri_count(body)} tris, {len(body.data.vertices)} verts')
    return body


def smart_uv(obj: bpy.types.Object, angle_deg: float = 66.0, margin: float = 0.02) -> None:
    C.set_active(obj)
    with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg), island_margin=margin, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode='OBJECT')


def hide_parts(parts: list[bpy.types.Object]) -> None:
    for o in parts:
        o.hide_render = True
        o.hide_viewport = True
        o.hide_set(True)


def sphere_patch(name: str, centre: Vector, radius: float, direction: Vector, half_w: float, half_h: float,
                 grid: int = 6, offset: float = 0.004, roll_deg: float = 0.0) -> bpy.types.Object:
    """A curved quad patch on a sphere around `direction` (angles in radians), UV 0..1 (u right, v up).

    The patch is later shrink-wrapped to the real body, so the sphere only needs to be roughly right.
    """
    d = direction.normalized()
    up = Vector((0, 0, 1))
    right = d.cross(up)
    if right.length < 1e-4:
        right = Vector((1, 0, 0))
    right.normalize()
    up2 = right.cross(d).normalized()
    if roll_deg:
        rot = Matrix.Rotation(math.radians(roll_deg), 4, d)
        right = (rot @ right).normalized()
        up2 = (rot @ up2).normalized()
    bm = bmesh.new()
    verts = []
    for j in range(grid + 1):
        row = []
        for i in range(grid + 1):
            u = i / grid
            v = j / grid
            a = (u - 0.5) * 2 * half_w
            b = (v - 0.5) * 2 * half_h
            # rotate d by a around up2, then by b around right
            dir_ = (Matrix.Rotation(-a, 4, up2) @ Matrix.Rotation(b, 4, right) @ d).normalized()
            co = centre + dir_ * (radius + offset)
            row.append(bm.verts.new(co))
        verts.append(row)
    bm.verts.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.new('UVMap')
    for j in range(grid):
        for i in range(grid):
            f = bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
            for loop in f.loops:
                vv = loop.vert
                # find grid indices
                for jj in range(grid + 1):
                    if vv in verts[jj]:
                        ii = verts[jj].index(vv)
                        loop[uv_layer].uv = (ii / grid, jj / grid)
                        break
    bm.normal_update()
    # make faces point outward (away from the sphere centre)
    flip = 0
    for f in bm.faces:
        if f.normal.dot(f.calc_center_median() - centre) < 0:
            flip += 1
    if flip > len(bm.faces) / 2:
        for f in bm.faces:
            f.normal_flip()
    me = _mesh_from_bm(name, bm)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def shrinkwrap_to(obj: bpy.types.Object, target: bpy.types.Object, offset: float) -> None:
    sw = obj.modifiers.new('wrap', 'SHRINKWRAP')
    sw.target = target
    sw.wrap_method = 'NEAREST_SURFACEPOINT'
    sw.wrap_mode = 'ABOVE_SURFACE'
    sw.offset = offset
    C.apply_modifiers(obj)
    obj.data.shade_smooth()


def bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for v in obj.data.vertices:
        co = obj.matrix_world @ v.co
        for k in range(3):
            mn[k] = min(mn[k], co[k])
            mx[k] = max(mx[k], co[k])
    return mn, mx
