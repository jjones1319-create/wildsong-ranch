"""Surface elements for Art 2.1 (docs/ART_2_DETAIL.md §3.1, §3.2): smooth voxel bodies, scattering, flow, sculpted
locks (baked into the maps), soft fur cards and tufts (the game's outline), and skinning them to the body.

Generalised from the detail spike (tools/blender/spikes/detail_spike.py). Everything is numbers and numpy; nothing here
knows a breed. A breed supplies:
  - `params_fn(points, normals) -> (spacing, length, width, lift, zones)`: per point, NaN spacing = no element there;
  - `flow_fn(points, normals, zones) -> unit tangents`: the direction the fur is combed.
Pinned to Blender 5.2.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

from . import common as C
from . import mesh as M

# kind attribute values (the paint shaders read them)
KIND_BODY, KIND_LOCK, KIND_TUFT, KIND_CARD = 0.0, 1.0, 2.0, 3.0
# element attributes every element object carries (joined layers keep them)
ELEMENT_ATTRS = ('root', 'rootn', 'across', 'tpos', 'lrand', 'kind')


# ----------------------------------------------------------------------------- numpy helpers
def v3(a) -> np.ndarray:
    return np.asarray(a, dtype=np.float64)


def smooth(a: float, b: float, x):
    """smoothstep(a, b, x); works for a > b too."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def norm(a: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    return a / np.maximum(n, 1e-9)


def tangent(g: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Project directions onto the surface's tangent plane."""
    return norm(g - n * (g * n).sum(axis=1, keepdims=True))


def in_ellipsoid(p, c, r) -> np.ndarray:
    """Squared normalised distance (< 1 inside)."""
    return (((p - v3(c)) / v3(r)) ** 2).sum(axis=1)


def ell_soft(p, c, r, soft: float = 0.08) -> np.ndarray:
    """1 inside the ellipsoid, 0 outside, a smooth edge `soft` (share of the radius) wide."""
    d = np.sqrt(in_ellipsoid(p, c, r))
    return smooth(1.0 + soft, 1.0 - soft, d)


def polyline_dist(px: np.ndarray, pz: np.ndarray, pts: list[tuple[float, float]]) -> np.ndarray:
    d = np.full(px.shape, 1e9)
    for (ax, az), (bx, bz) in zip(pts[:-1], pts[1:]):
        abx, abz = bx - ax, bz - az
        t = np.clip(((px - ax) * abx + (pz - az) * abz) / (abx * abx + abz * abz), 0, 1)
        dx = px - (ax + t * abx)
        dz = pz - (az + t * abz)
        d = np.minimum(d, np.sqrt(dx * dx + dz * dz))
    return d


def barycentric(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0.dot(v0), v0.dot(v1), v1.dot(v1)
    d20, d21 = v2.dot(v0), v2.dot(v1)
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-14:
        return (1.0, 0.0, 0.0)
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    return (1.0 - v - w, v, w)


# ----------------------------------------------------------------------------- mesh data
def mesh_arrays(ob: bpy.types.Object):
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    vn = np.empty(n * 3, np.float32)
    me.vertex_normals.foreach_get('vector', vn)
    return co.reshape(-1, 3).astype(np.float64), vn.reshape(-1, 3).astype(np.float64)


def set_positions(ob: bpy.types.Object, co: np.ndarray) -> None:
    ob.data.vertices.foreach_set('co', co.astype(np.float32).ravel())
    ob.data.update()


def add_attr(ob: bpy.types.Object, name: str, values: np.ndarray) -> None:
    me = ob.data
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
    if values.ndim == 1:
        a = me.attributes.new(name, 'FLOAT', 'POINT')
        a.data.foreach_set('value', values.astype(np.float32))
    else:
        a = me.attributes.new(name, 'FLOAT_VECTOR', 'POINT')
        a.data.foreach_set('vector', values.astype(np.float32).ravel())


def attr_array(ob: bpy.types.Object, name: str) -> np.ndarray:
    a = ob.data.attributes[name]
    n = len(a.data)
    if a.data_type == 'FLOAT':
        out = np.empty(n, np.float32)
        a.data.foreach_get('value', out)
        return out
    if a.data_type in ('FLOAT_COLOR', 'BYTE_COLOR'):
        out = np.empty(n * 4, np.float32)
        a.data.foreach_get('color', out)
        return out.reshape(-1, 4)
    out = np.empty(n * 3, np.float32)
    a.data.foreach_get('vector', out)
    return out.reshape(-1, 3)


def set_colour_attr(ob: bpy.types.Object, name: str, rgb: np.ndarray, active: bool = False) -> None:
    """A per-point FLOAT_COLOR attribute (linear RGB; alpha 1)."""
    me = ob.data
    if name in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[name])
    ca = me.color_attributes.new(name, 'FLOAT_COLOR', 'POINT')
    cols = np.ones((len(rgb), 4), np.float32)
    cols[:, :3] = rgb[:, :3]
    ca.data.foreach_set('color', cols.ravel())
    if active:
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.active_color_index


def mesh_area(ob: bpy.types.Object) -> float:
    return float(sum(p.area for p in ob.data.polygons))


def base_attrs(ob: bpy.types.Object, co: np.ndarray, extra: dict | None = None) -> None:
    """The attributes a smooth body carries so the paint shaders treat it like an element (root = its own position)."""
    n = len(co)
    add_attr(ob, 'root', co)
    add_attr(ob, 'tpos', np.zeros(n))
    add_attr(ob, 'lrand', np.full(n, 0.5))
    add_attr(ob, 'kind', np.full(n, KIND_BODY))
    for k in ('mouth', 'dots'):
        add_attr(ob, k, (extra or {}).get(k, np.zeros(n)))


# ----------------------------------------------------------------------------- smooth bodies
def build_body(name: str, parts: list[M.Part], voxel: float, smooth_iters: int, segments: int = 48,
               coll: str = 'SurfaceParts', extra: list[bpy.types.Object] | None = None) -> bpy.types.Object:
    """Join rounded primitives (and any `extra` closed meshes, e.g. a breed's ear slabs; they are consumed), voxel-remesh
    them into one closed skin and smooth it."""
    c = C.collection(coll)
    objs = list(extra or [])
    for p in parts:
        objs.extend(M.build_part(p, c, segments=segments))
    body = M.join_meshes(objs, name)
    rm = body.modifiers.new('remesh', 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel
    sm = body.modifiers.new('smooth', 'SMOOTH')
    sm.factor = 0.5
    sm.iterations = smooth_iters
    C.apply_modifiers(body)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    body.data.shade_smooth()
    C.log(f'{name}: {M.tri_count(body)} tris at voxel {voxel}')
    return body


def decimate_to(ob: bpy.types.Object, target: int, smooth_after: float = 0.3) -> None:
    dm = ob.modifiers.new('decimate', 'DECIMATE')
    dm.decimate_type = 'COLLAPSE'
    dm.ratio = min(1.0, target / max(1, M.tri_count(ob)))
    dm.use_collapse_triangulate = True
    C.apply_modifiers(ob)
    if smooth_after > 0:
        sm = ob.modifiers.new('smooth', 'SMOOTH')
        sm.factor = smooth_after
        sm.iterations = 1
        C.apply_modifiers(ob)
    ob.data.shade_smooth()


# ----------------------------------------------------------------------------- scattering
def scatter(ob: bpy.types.Object, spacing_fn, seed: int, oversample: float = 7.0):
    """Area-weighted candidates on `ob`, thinned to a variable-radius Poisson set. Returns points and normals."""
    rng = np.random.default_rng(seed)
    me = ob.data
    me.calc_loop_triangles()
    nt = len(me.loop_triangles)
    tv = np.empty(nt * 3, np.int32)
    me.loop_triangles.foreach_get('vertices', tv)
    tv = tv.reshape(-1, 3)
    co, vn = mesh_arrays(ob)
    a, b, c = co[tv[:, 0]], co[tv[:, 1]], co[tv[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    probe_p = (a + b + c) / 3
    probe_n = norm(vn[tv[:, 0]] + vn[tv[:, 1]] + vn[tv[:, 2]])
    sp = spacing_fn(probe_p, probe_n)
    ok = np.isfinite(sp)
    dens = np.zeros(len(sp))
    dens[ok] = 1.0 / np.maximum(sp[ok], 1e-3) ** 2
    n_cand = int((area * dens).sum() * oversample) + 10
    w = area * (dens > 0)
    pick = rng.choice(nt, size=n_cand, p=w / w.sum())
    r1 = np.sqrt(rng.random(n_cand))
    r2 = rng.random(n_cand)
    w0, w1, w2 = 1 - r1, r1 * (1 - r2), r1 * r2
    P = a[pick] * w0[:, None] + b[pick] * w1[:, None] + c[pick] * w2[:, None]
    N = norm(vn[tv[pick, 0]] * w0[:, None] + vn[tv[pick, 1]] * w1[:, None] + vn[tv[pick, 2]] * w2[:, None])
    S = spacing_fn(P, N)
    ok = np.isfinite(S)
    P, N, S = P[ok], N[ok], S[ok]
    order = rng.permutation(len(P))
    cell = float(np.max(S))
    grid: dict[tuple[int, int, int], list[int]] = {}
    keep: list[int] = []
    for i in order:
        p = P[i]
        key = (int(p[0] // cell), int(p[1] // cell), int(p[2] // cell))
        clash = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        r = 0.5 * (S[i] + S[j])
                        q = P[j] - p
                        if q[0] * q[0] + q[1] * q[1] + q[2] * q[2] < r * r:
                            clash = True
                            break
                    if clash:
                        break
                if clash:
                    break
            if clash:
                break
        if not clash:
            grid.setdefault(key, []).append(i)
            keep.append(i)
    keep = np.array(keep, dtype=int)
    C.log(f'scatter {ob.name}: {n_cand} candidates → {len(keep)} points')
    return P[keep], N[keep]


# ----------------------------------------------------------------------------- element shapes
def leaf_width(v: float) -> float:
    """Half-width of a lock along its length: full and rounded across, then a long soft taper to the tip."""
    return (0.85 + 0.15 * float(smooth(0.0, 0.2, v))) * max(0.0, 1.0 - float(smooth(0.25, 1.0, v)) ** 1.5) ** 0.7


def leaf_height(v: float) -> float:
    return math.sqrt(max(0.0, 1.0 - v ** 1.6))


def lock_template(nu: int, nv: int, ridges: int, strand: float = 0.14, closed: bool = True):
    """A lock of damp fur, flat and soft-edged with shallow strand grooves: x across [-1, 1], y along [0, 1], z up
    (height 1 = the lock's thickness). Returns (verts, faces, uvs). `closed=False` keeps the top surface only (lying
    locks: a bake ray that slips between overlapping locks must never meet an underside, which bakes dark)."""
    top, uvs = [], []
    rows = []
    for j in range(nv):
        v = j / nv
        hw = leaf_width(v)
        row = []
        for i in range(nu + 1):
            u = -1.0 + 2.0 * i / nu
            arch = max(0.0, 1.0 - u * u) ** 0.7
            strands = strand * (0.5 + 0.5 * math.cos(u * math.pi * ridges)) * arch - strand * 0.5 * arch
            h = (arch * 0.9 + strands) * leaf_height(v)
            row.append(len(top))
            top.append((u * hw, v, h))
            uvs.append(((u + 1) * 0.5, v))
        rows.append(row)
    tip = len(top)
    top.append((0.0, 1.0, 0.0))
    uvs.append((0.5, 1.0))
    faces = []
    for j in range(nv - 1):
        for i in range(nu):
            faces.append((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    for i in range(nu):
        faces.append((rows[nv - 1][i], rows[nv - 1][i + 1], tip))
    if not closed:
        return np.array(top), faces, np.array(uvs)
    under = []
    for j in range(nv):
        v = j / nv
        hw = leaf_width(v)
        row = [rows[j][0]]
        for i in range(1, nu):
            u = -1.0 + 2.0 * i / nu
            row.append(len(top))
            top.append((u * hw, v, -0.25 * max(0.0, 1.0 - u * u) * leaf_height(v)))
            uvs.append(((u + 1) * 0.5, v))
        row.append(rows[j][nu])
        under.append(row)
    for j in range(nv - 1):
        for i in range(nu):
            faces.append((under[j][i + 1], under[j][i], under[j + 1][i], under[j + 1][i + 1]))
    for i in range(nu):
        faces.append((under[nv - 1][i + 1], under[nv - 1][i], tip))
    for i in range(nu):
        quad = (rows[0][i + 1], rows[0][i], under[0][i], under[0][i + 1])
        uniq = tuple(dict.fromkeys(quad))
        if len(uniq) >= 3:
            faces.append(uniq)
    return np.array(top), faces, np.array(uvs)


def low_strand_template(rows_v=(0.0, 0.2, 0.4, 0.6, 0.78, 0.92)):
    """The game version of a tuft lock: a ridge (3 columns) over six rows and a rounded tip, open underneath."""
    vs, uvs = [], []
    rows = []
    for v in rows_v:
        hw = leaf_width(v)
        h = 0.9 * leaf_height(v)
        row = []
        for u, hh in ((-1.0, 0.0), (0.0, h), (1.0, 0.0)):
            row.append(len(vs))
            vs.append((u * hw, v, hh))
            uvs.append(((u + 1) * 0.5, v))
        rows.append(row)
    tip = len(vs)
    vs.append((0.0, 1.0, 0.0))
    uvs.append((0.5, 1.0))
    faces = []
    for j in range(len(rows) - 1):
        for i in range(2):
            a, b, c, d = rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]
            faces += [(a, b, c), (a, c, d)]
    last = rows[-1]
    faces += [(last[0], last[1], tip), (last[1], last[2], tip)]
    return np.array(vs), faces, np.array(uvs)


def card_template():
    """A soft fur card: a strip bent in two along its length (4 triangles); its texture carries the locks."""
    vs, uvs = [], []
    for v in (0.0, 0.45, 1.0):
        for u in (-1.0, 1.0):
            vs.append((u, v, 0.0))
            uvs.append(((u + 1) * 0.5, v))
    faces = [(0, 1, 3), (0, 3, 2), (2, 3, 5), (2, 5, 4)]
    return np.array(vs), faces, np.array(uvs)


CARD_VERTS = len(card_template()[0])


# ----------------------------------------------------------------------------- placing elements
def lock_frames(P, N, F, L, W, lift, rng, bvh=None, jitter_deg: float = 10.0):
    """Per element: its axes (across, along, normal), jittered length / width / lift, and how far the surface falls
    away under its tip (so it bends down and lies on a curved body instead of sticking out)."""
    k = len(P)
    jit = rng.normal(0, 1, (k, 4))
    Lk = L * (1.0 + 0.18 * np.clip(jit[:, 0], -2, 2))
    Wk = W * (1.0 + 0.14 * np.clip(jit[:, 1], -2, 2))
    ang = np.radians(jitter_deg) * np.clip(jit[:, 2], -2, 2)
    liftk = lift + np.radians(2.5) * np.clip(jit[:, 3], -2, 2)
    side = norm(np.cross(F, N))
    Fj = norm(F * np.cos(ang)[:, None] + side * np.sin(ang)[:, None])
    Xa = norm(np.cross(Fj, N))
    drop = np.zeros(k)
    if bvh is not None:
        tips = P + Fj * Lk[:, None]
        for i in range(k):
            hit = bvh.find_nearest(Vector(tips[i]))
            if hit[0] is not None:
                drop[i] = float((np.array(hit[0]) - tips[i]) @ N[i])
    return {'X': Xa, 'F': Fj, 'N': N, 'L': Lk, 'W': Wk, 'lift': liftk, 'drop': np.minimum(drop, 0.0), 'P': P}


def instance(template, fr: dict, thickness: float, bury: float) -> np.ndarray:
    """Place `template` on every frame. `thickness` is height / width; `bury` sinks the root (share of width)."""
    tv = template[0]
    y = tv[None, :, 1]
    lx = tv[None, :, 0] * (fr['W'][:, None] * 0.5)
    ly = y * fr['L'][:, None]
    lz = tv[None, :, 2] * (fr['W'][:, None] * thickness) - bury * fr['W'][:, None]
    lz = lz + fr['drop'][:, None] * y ** 2 + np.tan(fr['lift'])[:, None] * fr['L'][:, None] * y ** 2.2
    return (fr['P'][:, None, :] + fr['X'][:, None, :] * lx[..., None] + fr['F'][:, None, :] * ly[..., None]
            + fr['N'][:, None, :] * lz[..., None])


def mesh_from_template(name: str, verts: np.ndarray, faces_tpl) -> bpy.types.Mesh:
    """k copies of a template's faces over `verts` (k, nvt, 3), built with foreach_set (millions of locks in seconds;
    the same calls `Mesh.from_pydata` makes, without its Python lists)."""
    k, nvt = verts.shape[0], verts.shape[1]
    me = bpy.data.meshes.new(name)
    me.vertices.add(k * nvt)
    me.vertices.foreach_set('co', np.ascontiguousarray(verts.reshape(-1), dtype=np.float32))
    sizes = np.array([len(f) for f in faces_tpl], np.int64)
    flat = np.array([i for f in faces_tpl for i in f], np.int64)
    loops = (flat[None, :] + (np.arange(k, dtype=np.int64) * nvt)[:, None]).ravel().astype(np.int32)
    tot = np.tile(sizes, k)
    starts = np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int32)
    me.loops.add(len(loops))
    me.loops.foreach_set('vertex_index', loops)
    me.polygons.add(len(tot))
    me.polygons.foreach_set('loop_start', starts)
    me.update(calc_edges=True)
    return me


def elements_object(name: str, verts: np.ndarray, template, roots: np.ndarray, kind: float, rng,
                    rootn: np.ndarray | None = None) -> bpy.types.Object:
    tv, tf, tuv = template
    k, nvt = verts.shape[0], verts.shape[1]
    me = mesh_from_template(name, verts, tf)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    add_attr(ob, 'root', np.repeat(roots, nvt, axis=0))
    add_attr(ob, 'rootn', np.repeat(rootn if rootn is not None else np.tile(v3((0, 0, 1)), (k, 1)), nvt, axis=0))
    add_attr(ob, 'tpos', np.tile(tv[:, 1], k))
    add_attr(ob, 'across', np.tile(tv[:, 0], k))
    add_attr(ob, 'lrand', np.repeat(rng.random(k), nvt))
    add_attr(ob, 'kind', np.full(k * nvt, kind))
    add_attr(ob, 'mouth', np.zeros(k * nvt))
    add_attr(ob, 'dots', np.zeros(k * nvt))
    C.log(f'{name}: {k} elements, {M.tri_count(ob)} tris')
    return ob


def scatter_layer(name: str, surface, params_fn, flow_fn, seed: int, template, quick: bool, thickness: float,
                  bury: float, kind: float, jitter_deg: float = 10.0, sparse: float = 1.2):
    """Scatter one layer of elements over `surface` (Poisson by the params' spacing, combed by `flow_fn`)."""
    def spacing(p, n):
        sp, *_ = params_fn(p, n)
        return sp * (sparse if quick else 1.0)
    P, N = scatter(surface, spacing, seed)
    sp, L, W, lift, zones = params_fn(P, N)
    F = flow_fn(P, N, zones)
    bvh = BVHTree.FromObject(surface, bpy.context.evaluated_depsgraph_get())
    fr = lock_frames(P, N, F, L, W, lift, np.random.default_rng(seed + 1), bvh, jitter_deg)
    ob = elements_object(name, instance(template, fr, thickness, bury), template, P, kind, np.random.default_rng(seed + 2), N)
    return ob, fr


def join_elements(objs: list[bpy.types.Object], name: str, attrs=ELEMENT_ATTRS, remove: bool = True) -> bpy.types.Object:
    """Join element layers into one object, keeping their per-point attributes."""
    joined = M.join_meshes(objs, name)
    for a in attrs:
        if all(a in o.data.attributes for o in objs):
            add_attr(joined, a, np.concatenate([attr_array(o, a) for o in objs]))
    if remove:
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
    return joined


def element_count(ob: bpy.types.Object, nvt: int) -> int:
    return len(ob.data.vertices) // max(1, nvt)


# ----------------------------------------------------------------------------- shading as one coat
def coat_normals(elems: bpy.types.Object, round_k: float, nvt: int | None = None) -> None:
    """Cards and locks shade as one coat with the body: the body's normal at the root, rounded a little across."""
    rootn = attr_array(elems, 'rootn')
    across = attr_array(elems, 'across')
    tpos = attr_array(elems, 'tpos')
    co = np.empty(len(elems.data.vertices) * 3, np.float32)
    elems.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3).astype(np.float64)
    if nvt is None:
        n_el = len(np.unique(attr_array(elems, 'root'), axis=0))
        nvt = len(co) // max(1, n_el) if n_el else 1
    centre = co.reshape(-1, nvt, 3).mean(axis=1)
    side = co - np.repeat(centre, nvt, axis=0)
    side = side - rootn * (side * rootn).sum(axis=1, keepdims=True)
    side = norm(side)
    n = norm(rootn + side * (np.clip(across, -1, 1)[:, None] * round_k) * (1 - 0.5 * tpos[:, None]))
    elems.data.normals_split_custom_set_from_vertices([tuple(x) for x in n])


# ----------------------------------------------------------------------------- skinning elements to the body
def body_weights(body: bpy.types.Object) -> tuple[list[str], np.ndarray]:
    """The body's vertex-group weights as a dense (verts × groups) array."""
    names = [g.name for g in body.vertex_groups]
    W = np.zeros((len(body.data.vertices), len(names)), np.float32)
    for v in body.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    return names, W


def write_weights(ob: bpy.types.Object, names: list[str], W: np.ndarray, arm: bpy.types.Object | None = None,
                  max_influences: int = 4) -> None:
    """Replace `ob`'s vertex groups with dense weights (top `max_influences`, normalised) and bind it to `arm`."""
    W = W.astype(np.float64).copy()
    if max_influences < W.shape[1]:
        idx = np.argsort(-W, axis=1)[:, max_influences:]
        np.put_along_axis(W, idx, 0.0, axis=1)
    s = W.sum(axis=1, keepdims=True)
    s[s == 0] = 1.0
    W /= s
    ob.vertex_groups.clear()
    for j, n in enumerate(names):
        nz = np.nonzero(W[:, j] > 1e-4)[0]
        if len(nz) == 0:
            continue
        vg = ob.vertex_groups.new(name=n)
        # group equal weights so one add() call covers many vertices (cards copy whole rows)
        vals = np.round(W[nz, j], 4)
        order = np.argsort(vals, kind='stable')
        nz, vals = nz[order], vals[order]
        cuts = np.nonzero(np.diff(vals))[0] + 1
        for run_i, run_w in zip(np.split(nz, cuts), np.split(vals, cuts)):
            vg.add(run_i.tolist(), float(run_w[0]), 'REPLACE')
    if arm is not None:
        mod = ob.modifiers.get('Armature') or ob.modifiers.new('Armature', 'ARMATURE')
        mod.object = arm
        ob.parent = arm
        ob.matrix_parent_inverse = arm.matrix_world.inverted()


def copy_weights_at_roots(elems: bpy.types.Object, body: bpy.types.Object, arm: bpy.types.Object, nvt: int | None = None) -> None:
    """Skin cards or locks to the body: every vertex of an element copies the weights of the body vertex nearest to the
    element's root, so the whole element moves rigidly with the skin under it (ART_2_DETAIL §3.2)."""
    names, W = body_weights(body)
    co = np.empty(len(body.data.vertices) * 3, np.float32)
    body.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    kd = KDTree(len(co))
    for i, p in enumerate(co):
        kd.insert(Vector(p), i)
    kd.balance()
    roots = attr_array(elems, 'root')
    if nvt:
        per = roots[::nvt]
        idx = np.array([kd.find(Vector(r))[1] for r in per], dtype=np.int64)
        idx = np.repeat(idx, nvt)
    else:
        cache: dict[tuple, int] = {}
        idx = np.empty(len(roots), np.int64)
        for i, r in enumerate(roots):
            key = (round(float(r[0]), 5), round(float(r[1]), 5), round(float(r[2]), 5))
            if key not in cache:
                cache[key] = kd.find(Vector(r))[1]
            idx[i] = cache[key]
    write_weights(elems, names, W[idx], arm)
    C.log(f'skinned {elems.name}: {len(roots)} verts copy their root vertex weights')
