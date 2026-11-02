"""Helpers for the arena builds (Blender 5.2): meshes from arrays, UVs, decimation, Poly Haven materials and imports.

Every procedural mesh is built in world coordinates with an identity transform, so `Object` texture coordinates are
world metres before and after the bake stage joins the objects of one atlas group.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib.nodes import NB, new_mat

HERE = Path(__file__).resolve().parent
CACHE = HERE / '.cache'


# ----------------------------------------------------------------------------- objects
def obj_from_arrays(name: str, verts, faces, coll, mats=None, face_mat=None, uvs=None, smooth: bool = False,
                    colors=None) -> bpy.types.Object:
    """verts (N,3) world metres; faces: list of index tuples; uvs: per-loop (L,2) in face order; colors: per-face RGB."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    for m in (mats or []):
        me.materials.append(m)
    if face_mat is not None and len(face_mat):
        me.polygons.foreach_set('material_index', np.asarray(face_mat, np.int32))
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', np.asarray(uvs, np.float32).ravel())
    if colors is not None:
        set_face_colors(ob, colors)
    me.polygons.foreach_set('use_smooth', np.full(len(me.polygons), smooth, bool))
    me.update()
    return ob


def obj_from_bm(name: str, bm: bmesh.types.BMesh, coll, mats=None, smooth: bool = False) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    for m in (mats or []):
        me.materials.append(m)
    me.polygons.foreach_set('use_smooth', np.full(len(me.polygons), smooth, bool))
    me.update()
    return ob


def set_face_colors(ob: bpy.types.Object, colors) -> None:
    """A per-face colour (sRGB 0..1 RGB) into the byte colour attribute `Col` (corner domain)."""
    me = ob.data
    if 'Col' in me.color_attributes:
        me.color_attributes.remove(me.color_attributes['Col'])
    attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    cols = np.asarray(colors, np.float32)
    lin = np.where(cols <= 0.04045, cols / 12.92, ((cols + 0.055) / 1.055) ** 2.4)
    counts = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_total', counts)
    per_loop = np.repeat(lin, counts, axis=0)
    rgba = np.concatenate([per_loop, np.ones((len(per_loop), 1), np.float32)], axis=1)
    attr.data.foreach_set('color', rgba.ravel())
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = me.color_attributes.find('Col')


def apply_transform(ob: bpy.types.Object) -> None:
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)


def tri_count(ob: bpy.types.Object) -> int:
    me = ob.data
    counts = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_total', counts)
    return int((counts - 2).sum())


def decimate_to(ob: bpy.types.Object, target: int) -> None:
    """Collapse decimation, repeated: one pass stalls well above the target on dense scans with many UV seams."""
    for _ in range(5):
        n = tri_count(ob)
        if n <= target * 1.1:
            return
        m = ob.modifiers.new('dec', 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = max(0.01, target / n)
        m.use_collapse_triangulate = True
        C.apply_modifiers(ob)
        if tri_count(ob) > n * 0.9:
            m = ob.modifiers.new('dec2', 'DECIMATE')
            m.decimate_type = 'COLLAPSE'
            m.ratio = max(0.01, target / tri_count(ob))
            m.use_collapse_triangulate = True
            m.use_symmetry = False
            m.vertex_group_factor = 0.0
            C.apply_modifiers(ob)
            if tri_count(ob) > n * 0.9:
                return


def mesh_np(ob: bpy.types.Object):
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    return co.reshape(-1, 3)


def set_co(ob: bpy.types.Object, co: np.ndarray) -> None:
    ob.data.vertices.foreach_set('co', np.asarray(co, np.float32).ravel())
    ob.data.update()


# ----------------------------------------------------------------------------- UVs
def loop_arrays(me: bpy.types.Mesh):
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', lv)
    starts = np.empty(len(me.polygons), np.int32)
    counts = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_start', starts)
    me.polygons.foreach_get('loop_total', counts)
    pn = np.empty(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get('normal', pn)
    poly_of_loop = np.repeat(np.arange(len(me.polygons)), counts)
    return lv, poly_of_loop, pn.reshape(-1, 3)


def box_uv(ob: bpy.types.Object, tile: float = 1.0, layer: str = 'UVMap', grain_z: bool = True) -> None:
    """World-aligned box projection per face: 1 UV unit = `tile` metres. Side faces map (horizontal, z) so wood grain
    (vertical in the source textures) runs up the posts; top faces map (x, y)."""
    me = ob.data
    co = mesh_np(ob)
    lv, pol, pn = loop_arrays(me)
    n = np.abs(pn[pol])
    p = co[lv]
    ax = np.argmax(n, axis=1)
    u = np.where(ax == 0, p[:, 1], np.where(ax == 1, p[:, 0], p[:, 0]))
    v = np.where(ax == 2, p[:, 1], p[:, 2])
    if not grain_z:
        u, v = v, u
    uvl = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    uvl.data.foreach_set('uv', (np.stack([u, v], 1) / tile).astype(np.float32).ravel())


def along_uv(ob: bpy.types.Object, axis: Vector, tile: float = 1.0, layer: str = 'UVMap') -> None:
    """Cylindrical-ish UVs for a long thin part: v along `axis`, u around it (for planks, beams, poles)."""
    me = ob.data
    co = mesh_np(ob)
    lv, pol, pn = loop_arrays(me)
    a = np.array(axis, np.float32)
    a /= np.linalg.norm(a)
    p = co[lv]
    v = p @ a
    ref = np.array([0, 0, 1.0], np.float32) if abs(a[2]) < 0.9 else np.array([1.0, 0, 0], np.float32)
    b1 = np.cross(a, ref)
    b1 /= np.linalg.norm(b1)
    b2 = np.cross(a, b1)
    n = pn[pol]
    u = np.where(np.abs(n @ b1) > np.abs(n @ b2), p @ b2, p @ b1)
    uvl = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    uvl.data.foreach_set('uv', (np.stack([u, v], 1) / tile).astype(np.float32).ravel())


def planar_uv(ob: bpy.types.Object, x0: float, y0: float, size: float, layer: str) -> None:
    """Top-down planar UVs: the square [x0, x0+size] × [y0, y0+size] maps to 0..1."""
    me = ob.data
    co = mesh_np(ob)
    lv, _, _ = loop_arrays(me)
    p = co[lv]
    uv = np.stack([(p[:, 0] - x0) / size, (p[:, 1] - y0) / size], 1)
    uvl = me.uv_layers.get(layer) or me.uv_layers.new(name=layer)
    uvl.data.foreach_set('uv', uv.astype(np.float32).ravel())


# ----------------------------------------------------------------------------- primitives (world coordinates)
def box_obj(name: str, size, centre, coll, mats, rot: Matrix | None = None, bevel: float = 0.0, segs: int = 1) -> bpy.types.Object:
    bm = bmesh.new()
    geom = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=geom['verts'])
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segs, affect='EDGES', profile=0.5, clamp_overlap=True)
    m = Matrix.Translation(Vector(centre)) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return obj_from_bm(name, bm, coll, mats)


def cyl_obj(name: str, p0, p1, r0: float, r1: float, coll, mats, segs: int = 8, caps: bool = True,
            smooth: bool = True) -> bpy.types.Object:
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=segs, radius1=r0, radius2=r1, depth=L)
    rot = d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
    m = Matrix.Translation((p0 + p1) * 0.5) @ rot
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    return obj_from_bm(name, bm, coll, mats, smooth=smooth)


def tube_along(points: np.ndarray, radius, sides: int = 6, twist_u: float = 1.0):
    """A tube through `points` (M,3); radius scalar or (M,). Returns verts, faces, per-loop uvs (u around, v along
    in metres)."""
    P = np.asarray(points, np.float64)
    M = len(P)
    rad = np.full(M, radius) if np.isscalar(radius) else np.asarray(radius)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.array([0, 0, 1.0])
    N = np.cross(T, up)
    bad = np.linalg.norm(N, axis=1) < 1e-6
    N[bad] = np.cross(T[bad], np.array([1.0, 0, 0]))
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    B = np.cross(T, N)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    verts = (P[:, None, :] + rad[:, None, None] * (np.cos(ang)[None, :, None] * N[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :])).reshape(-1, 3)
    seg_len = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    faces, uvs = [], []
    for i in range(M - 1):
        for j in range(sides):
            a, b = i * sides + j, i * sides + (j + 1) % sides
            c, d = (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j
            faces.append((a, b, c, d))
            u0, u1 = j / sides * twist_u, (j + 1) / sides * twist_u
            uvs += [(u0, seg_len[i]), (u1, seg_len[i]), (u1, seg_len[i + 1]), (u0, seg_len[i + 1])]
    return verts, faces, np.asarray(uvs)


def lathe(profile, segs: int, centre, rot: Matrix | None = None, cap_top: bool = True, cap_bottom: bool = True):
    """Revolve a (radius, z) profile around +Z. Returns verts and faces (quads; caps as fans)."""
    prof = list(profile)
    verts, faces = [], []
    cx, cy, cz = centre
    R = rot if rot is not None else Matrix.Identity(3)
    for (r, z) in prof:
        for s in range(segs):
            a = 2 * math.pi * s / segs
            v = R @ Vector((r * math.cos(a), r * math.sin(a), z))
            verts.append((cx + v.x, cy + v.y, cz + v.z))
    n = len(prof)
    for i in range(n - 1):
        for s in range(segs):
            a, b = i * segs + s, i * segs + (s + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    if cap_bottom and prof[0][0] > 1e-4:
        faces.append(tuple(reversed(range(segs))))
    if cap_top and prof[-1][0] > 1e-4:
        faces.append(tuple((n - 1) * segs + s for s in range(segs)))
    return verts, faces


def ico_blob(bm_or_none, centre, radius, scale=(1, 1, 1), subdiv: int = 2, noise: float = 0.0, rng=None):
    bm = bm_or_none or bmesh.new()
    before = set(bm.verts)
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    new = [v for v in bm.verts if v not in before]
    for v in new:
        k = 1.0 + (rng.normal(0, noise) if (rng is not None and noise > 0) else 0.0)
        v.co = Vector((v.co.x * scale[0] * k + centre[0], v.co.y * scale[1] * k + centre[1], v.co.z * scale[2] * k + centre[2]))
    return bm


# ----------------------------------------------------------------------------- Poly Haven sources
def manifest() -> dict:
    p = CACHE / 'manifest.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}


def tex_path(aid: str, kind: str = 'diff') -> Path:
    d = CACHE / 'textures' / aid
    for p in sorted(d.glob(f'{aid}_{kind}_*.jpg')):
        return p
    raise FileNotFoundError(f'{aid} {kind}: run py -I tools/blender/arenas/fetch.py')


_IMAGES: dict[str, bpy.types.Image] = {}


def load_image(path: Path, non_color: bool = False) -> bpy.types.Image:
    key = str(path)
    img = _IMAGES.get(key)
    if img is None or img.name not in bpy.data.images:
        img = bpy.data.images.load(str(path), check_existing=True)
        if non_color:
            img.colorspace_settings.name = 'Non-Color'
        _IMAGES[key] = img
    return img


def import_model(aid: str, coll) -> list[bpy.types.Object]:
    """Import a Poly Haven glTF into `coll`; returns its mesh objects (transforms applied, parents cleared)."""
    path = CACHE / 'models' / aid / f'{aid}.gltf'
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = []
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    for o in new:
        if o.type == 'MESH':
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
            if o.data.users > 1:
                o.data = o.data.copy()
            apply_transform(o)
            # glTF splits vertices at every UV seam; weld them so decimation can collapse across the seams
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
            bm.to_mesh(o.data)
            bm.free()
            meshes.append(o)
    for o in new:
        if o.type != 'MESH':
            bpy.data.objects.remove(o, do_unlink=True)
    return meshes


# ----------------------------------------------------------------------------- materials
def tex_nodes(nb: NB, aid: str, vec, proj: str = 'FLAT', blend: float = 0.25, normal: bool = True):
    """Diffuse (sRGB) and optional normal-map image nodes of a Poly Haven texture fed by `vec`."""
    d = nb.new('ShaderNodeTexImage', image=load_image(tex_path(aid, 'diff')), interpolation='Linear')
    d.projection = proj
    if proj == 'BOX':
        d.projection_blend = blend
    nb.put(d.inputs['Vector'], vec)
    n = None
    if normal:
        n = nb.new('ShaderNodeTexImage', image=load_image(tex_path(aid, 'nor_gl'), non_color=True), interpolation='Linear')
        n.projection = proj
        if proj == 'BOX':
            n.projection_blend = blend
        nb.put(n.inputs['Vector'], vec)
    return d, n


def grade(nb: NB, col, hue: float = 0.5, sat: float = 1.0, val: float = 1.0, tint=None, tint_mix: float = 0.0,
          contrast: float = 0.0):
    """Stylise a photo texture: hue/saturation/value, a soft contrast and a mix toward a flat tint."""
    hs = nb.new('ShaderNodeHueSaturation')
    hs.inputs['Hue'].default_value = hue
    hs.inputs['Saturation'].default_value = sat
    hs.inputs['Value'].default_value = val
    nb.put(hs.inputs['Color'], col)
    out = hs.outputs[0]
    if contrast != 0.0:
        bc = nb.new('ShaderNodeBrightContrast')
        bc.inputs['Contrast'].default_value = contrast
        nb.put(bc.inputs['Color'], out)
        out = bc.outputs[0]
    if tint is not None and tint_mix > 0:
        out = nb.mix(tint_mix, out, tuple(tint[:3]) + (1.0,))
    return out


def coords(nb: NB, kind: str = 'Object', scale: float = 1.0, rot_z: float = 0.0, offset=(0, 0, 0)):
    tc = nb.new('ShaderNodeTexCoord')
    mp = nb.new('ShaderNodeMapping')
    nb.link(tc.outputs[kind], mp.inputs['Vector'])
    mp.inputs['Scale'].default_value = (1 / scale, 1 / scale, 1 / scale)
    mp.inputs['Rotation'].default_value = (0, 0, rot_z)
    mp.inputs['Location'].default_value = offset
    return mp.outputs[0]


def principled(nb: NB, base, rough: float = 0.85, normal=None, spec: float = 0.25):
    b = nb.new('ShaderNodeBsdfPrincipled')
    nb.put(b.inputs['Base Color'], base)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = spec
    if normal is not None:
        nb.link(normal, b.inputs['Normal'])
    nb.output(b.outputs[0])
    return b


def normal_map(nb: NB, img_node, strength: float = 1.0, uv: str = 'UVMap'):
    nm = nb.new('ShaderNodeNormalMap')
    nm.space = 'TANGENT'
    nm.uv_map = uv
    nm.inputs['Strength'].default_value = strength
    nb.link(img_node.outputs['Color'], nm.inputs['Color'])
    return nm.outputs[0]


def bump_from(nb: NB, height, strength: float = 0.3, distance: float = 0.02, normal=None):
    bp = nb.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = distance
    nb.put(bp.inputs['Height'], height)
    if normal is not None:
        nb.link(normal, bp.inputs['Normal'])
    return bp.outputs[0]


def lum(nb: NB, col):
    rgbbw = nb.new('ShaderNodeRGBToBW')
    nb.put(rgbbw.inputs[0], col)
    return rgbbw.outputs[0]


def photo_mat(name: str, aid: str, tile: float, *, proj: str = 'UV', hue: float = 0.5, sat: float = 1.0,
              val: float = 1.0, tint=None, tint_mix: float = 0.0, contrast: float = 0.0, rough: float = 0.85,
              nstrength: float = 0.8, rot_z: float = 0.0, vcol: bool = False, vcol_mix: float = 1.0) -> bpy.types.Material:
    """A Poly Haven texture, stylised: UV (our box/along UVs, tangent normals) or BOX (triplanar on world metres,
    bump from the diffuse's luminance)."""
    m, nb = new_mat(name)
    if proj == 'UV':
        vec = coords(nb, 'UV', tile, rot_z)
        d, n = tex_nodes(nb, aid, vec, 'FLAT')
        nrm = normal_map(nb, n, nstrength)
    else:
        vec = coords(nb, 'Object', tile, rot_z)
        d, _ = tex_nodes(nb, aid, vec, 'BOX', normal=False)
        nrm = bump_from(nb, lum(nb, d.outputs['Color']), 0.35 * nstrength, 0.03)
    col = grade(nb, d.outputs['Color'], hue, sat, val, tint, tint_mix, contrast)
    if vcol:
        a = nb.attribute('Col')
        col = nb.mix(vcol_mix, col, nb.mix(1.0, col, a.outputs['Color'], blend='MULTIPLY'))
    principled(nb, col, rough, nrm)
    return m


def flat_mat(name: str, hex_or_rgb, rough: float = 0.7, vcol: bool = False, linen: float = 0.0) -> bpy.types.Material:
    """A flat stylised colour (or the per-face `Col` attribute), optionally with a linen weave for cloth."""
    m, nb = new_mat(name)
    col = C.lin(hex_or_rgb) if isinstance(hex_or_rgb, str) else tuple(hex_or_rgb) + (1.0,)
    base = nb.attribute('Col').outputs['Color'] if vcol else col
    nrm = None
    if linen > 0:
        vec = coords(nb, 'Object', 0.6)
        d, _ = tex_nodes(nb, 'rough_linen', vec, 'BOX', normal=False)
        l = lum(nb, d.outputs['Color'])
        k = nb.math('MULTIPLY_ADD', l, linen, 1.0 - 0.45 * linen)
        base = nb.mix(1.0, base, nb.comb(k, k, k), blend='MULTIPLY')
        nrm = bump_from(nb, l, 0.25, 0.01)
    principled(nb, base, rough, nrm)
    return m


def emission_image_mat(name: str, image: bpy.types.Image, uv: str = 'UVMap') -> bpy.types.Material:
    m, nb = new_mat(name)
    uvn = nb.new('ShaderNodeUVMap', uv_map=uv)
    t = nb.new('ShaderNodeTexImage', image=image, interpolation='Linear')
    t.extension = 'EXTEND'
    nb.link(uvn.outputs[0], t.inputs['Vector'])
    em = nb.new('ShaderNodeEmission')
    nb.link(t.outputs['Color'], em.inputs['Color'])
    em.inputs['Strength'].default_value = 1.0
    nb.output(em.outputs[0])
    return m
