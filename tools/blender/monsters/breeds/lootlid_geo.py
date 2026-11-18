"""Lootlid's mesh builders (Art 2.1 Ultra): numpy pieces (vertices, quad faces, per-vertex attributes), lofts of
rounded-rectangle rings (the box, the lid and the legs are each one closed loft), sweeps of cross-section rings along a
path (the gold bands, the tongue), and a fast Blender mesh maker. The piece format and the maker follow Moatshell's
(moatshell_geo.py), copied here so the breeds never change each other. Metres; the monster faces −Y, Z is up, +X is
its left.

A Piece is a dict: 'v' (n×3), 'f' (m×4 int quads; a triangle repeats its last index), 'a' {name: n or n×3 arrays}.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

from lib import common as C


def piece(v, f, **attrs) -> dict:
    v = np.asarray(v, np.float64).reshape(-1, 3)
    out = {'v': v, 'f': np.asarray(f, np.int64).reshape(-1, 4), 'a': {}}
    return tag(out, **attrs)


def tag(pc: dict, **attrs) -> dict:
    """Set constant (or per-vertex) attributes on a piece; returns it."""
    for k, a in attrs.items():
        a = np.asarray(a, np.float64)
        pc['a'][k] = np.full(len(pc['v']), float(a)) if a.ndim == 0 else a
    return pc


def merge(pieces: list[dict]) -> dict:
    """One piece from many (attributes missing on a piece are 0 there)."""
    pieces = [p for p in pieces if len(p['v'])]
    names = {}
    for p in pieces:
        for k, a in p['a'].items():
            names[k] = a.shape[1:] if a.ndim > 1 else ()
    vs, fs, off = [], [], 0
    attrs = {k: [] for k in names}
    for p in pieces:
        n = len(p['v'])
        vs.append(p['v'])
        fs.append(p['f'] + off)
        for k, shp in names.items():
            attrs[k].append(p['a'][k] if k in p['a'] else np.zeros((n,) + shp))
        off += n
    return {'v': np.concatenate(vs) if vs else np.zeros((0, 3)), 'f': np.concatenate(fs) if fs else np.zeros((0, 4), np.int64),
            'a': {k: np.concatenate(a) for k, a in attrs.items()}}


def grid_faces(nu: int, nv: int, wrap_u: bool = False, flip: bool = False) -> np.ndarray:
    """Quads over a grid of (nu + 1 or nu when wrapped) × (nv + 1) points, index = i * (nv + 1) + j (u major)."""
    cols = nu if wrap_u else nu + 1
    i, j = np.meshgrid(np.arange(nu), np.arange(nv), indexing='ij')
    i, j = i.ravel(), j.ravel()
    i1 = (i + 1) % cols
    a = i * (nv + 1) + j
    b = i1 * (nv + 1) + j
    c = i1 * (nv + 1) + j + 1
    d = i * (nv + 1) + j + 1
    f = np.stack([a, b, c, d], axis=1)
    return f[:, ::-1] if flip else f


def tri_of(f: np.ndarray) -> np.ndarray:
    """Every face as triangles (k×3)."""
    tri = f[:, 2] == f[:, 3]
    quads = f[~tri]
    return np.concatenate([f[tri][:, :3], quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])


def signed_volume(pc: dict) -> float:
    t = tri_of(pc['f'])
    v = pc['v']
    return float(np.einsum('ij,ij->i', v[t[:, 0]], np.cross(v[t[:, 1]], v[t[:, 2]])).sum() / 6.0)


def outward(pc: dict) -> dict:
    """Flip every face of a closed piece when its winding encloses a negative volume (faces point outward after)."""
    if signed_volume(pc) < 0:
        f = pc['f']
        tri = f[:, 2] == f[:, 3]
        g = f[:, ::-1].copy()
        # a triangle stored as (a, b, c, c) reverses to (c, c, b, a): store it as (a, c, b, b) instead
        g[tri] = np.stack([f[tri][:, 0], f[tri][:, 2], f[tri][:, 1], f[tri][:, 1]], axis=1)
        pc['f'] = g
    return pc


# ----------------------------------------------------------------------------- rounded-rectangle rings
def unit_ring(n: float, nu: int, aspect: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """nu points (c, s) on the unit superellipse |c|^n + |s|^n = 1, counter-clockwise from +x, spaced evenly by arc
    length on a ring of the given aspect (b / a)."""
    t = np.linspace(0.0, 2 * math.pi, 8192, endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    c = np.sign(ct) * np.abs(ct) ** (2.0 / n)
    s = np.sign(st) * np.abs(st) ** (2.0 / n)
    p = np.stack([c, s * aspect], axis=1)
    seg = np.linalg.norm(np.roll(p, -1, axis=0) - p, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    want = np.linspace(0.0, cum[-1], nu, endpoint=False)
    tt = np.interp(want, cum, np.concatenate([t, [2 * math.pi]]))
    ct, st = np.cos(tt), np.sin(tt)
    return np.sign(ct) * np.abs(ct) ** (2.0 / n), np.sign(st) * np.abs(st) ** (2.0 / n)


def ring_xy(cs, a, b, bulge: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """A ring's x, y from unit (c, s) and semi-axes a, b, its faces bulged out by `bulge` at their middles."""
    c, s = cs
    x = a * c * (1.0 + bulge * (1.0 - s * s))
    y = b * s * (1.0 + bulge * (1.0 - c * c))
    return x, y


def loft(rows, cs, bulge: float = 0.0) -> dict:
    """A closed mesh from rings: rows [(z, a, b, cx, cy)] in profile order (each the rounded-rectangle ring of semi-axes
    a, b round (cx, cy) at height z; a = b = 0 is a single point, for the closed ends). Attributes: 'row' (the row
    index) and 'ang' (the ring's own angle, 0..1)."""
    nu = len(cs[0])
    vs, rows_a, ang, starts = [], [], [], []
    off = 0
    for i, (z, a, b, cx, cy) in enumerate(rows):
        starts.append(off)
        if a <= 0 and b <= 0:
            vs.append(np.array([[cx, cy, z]]))
            rows_a.append([i])
            ang.append([0.0])
            off += 1
        else:
            x, y = ring_xy(cs, a, b, bulge)
            vs.append(np.stack([x + cx, y + cy, np.full(nu, z)], axis=1))
            rows_a.append(np.full(nu, i))
            ang.append(np.arange(nu) / nu)
            off += nu
    F = []
    k = np.arange(nu)
    k1 = (k + 1) % nu
    for i in range(len(rows) - 1):
        pa, pb = rows[i][1] <= 0 and rows[i][2] <= 0, rows[i + 1][1] <= 0 and rows[i + 1][2] <= 0
        s0, s1 = starts[i], starts[i + 1]
        if pa and pb:
            continue
        if pa:
            F.append(np.stack([np.full(nu, s0), s1 + k1, s1 + k, s1 + k], axis=1))
        elif pb:
            F.append(np.stack([s0 + k, s0 + k1, np.full(nu, s1), np.full(nu, s1)], axis=1))
        else:
            F.append(np.stack([s0 + k, s0 + k1, s1 + k1, s1 + k], axis=1))
    pc = piece(np.concatenate(vs), np.concatenate(F), row=np.concatenate(rows_a).astype(np.float64), ang=np.concatenate(ang))
    return outward(pc)


def sweep(rings: list[np.ndarray], closed: bool = False, cap: bool = True) -> dict:
    """A closed mesh from cross-section rings along a path (each ring M points in the same order): quads between
    neighbours, wrapped round each ring; an open path gets fan caps at both ends. 'u' (the ring's index / count) and
    'k' (the point's index in its ring / M) as attributes."""
    R = np.stack(rings)                  # (J, M, 3)
    J, M = R.shape[0], R.shape[1]
    V = R.reshape(-1, 3)
    j, k = np.meshgrid(np.arange(J if closed else J - 1), np.arange(M), indexing='ij')
    j, k = j.ravel(), k.ravel()
    j1, k1 = (j + 1) % J, (k + 1) % M
    F = [np.stack([j * M + k, j * M + k1, j1 * M + k1, j1 * M + k], axis=1)]
    extra = []
    if not closed and cap:
        for end, jj in ((0, 0), (1, J - 1)):
            c = len(V) + len(extra)
            extra.append(R[jj].mean(axis=0))
            kk = np.arange(M)
            if end == 0:
                F.append(np.stack([np.full(M, c), jj * M + (kk + 1) % M, jj * M + kk, jj * M + kk], axis=1))
            else:
                F.append(np.stack([np.full(M, c), jj * M + kk, jj * M + (kk + 1) % M, jj * M + (kk + 1) % M], axis=1))
    u = np.repeat(np.arange(J) / max(1, J - (0 if closed else 1)), M)
    kk = np.tile(np.arange(M) / M, J)
    if extra:
        V = np.concatenate([V, np.array(extra)])
        u = np.concatenate([u, [0.0, 1.0]])
        kk = np.concatenate([kk, [0.5, 0.5]])
    return outward(piece(V, np.concatenate(F), u=u, k=kk))


def frames(path: np.ndarray, up_hint) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tangents, normals and binormals along a polyline (the normal kept near `up_hint`, one per point or one vector)."""
    t = np.gradient(path, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
    up = np.broadcast_to(np.asarray(up_hint, np.float64), path.shape)
    n = up - t * np.einsum('ij,ij->i', up, t)[:, None]
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return t, n, np.cross(t, n)


def tube(path: np.ndarray, radius, nu: int, up_hint=(0.0, 0.0, 1.0), closed: bool = False) -> dict:
    """A round tube along a polyline (radius a number or one per point), capped at both ends unless closed."""
    path = np.asarray(path, np.float64)
    rad = np.broadcast_to(np.asarray(radius, np.float64), (len(path),))
    t, n, b = frames(path, up_hint)
    a = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    rings = [path[i] + rad[i] * (np.cos(a)[:, None] * n[i] + np.sin(a)[:, None] * b[i]) for i in range(len(path))]
    return sweep(rings, closed=closed)


def uv_sphere(c, r, nu: int, nv: int) -> dict:
    """A UV sphere (r a number or (rx, ry, rz)), closed."""
    r = np.broadcast_to(np.asarray(r, np.float64), (3,))
    rows = []
    for i in range(nv + 1):
        el = -math.pi / 2 + math.pi * i / nv
        z = math.sin(el)
        rr = math.cos(el)
        rows.append((z, rr, rr, 0.0, 0.0) if 0 < i < nv else (z, 0.0, 0.0, 0.0, 0.0))
    pc = loft(rows, unit_ring(2.0, nu))
    pc['v'] = pc['v'] * r[None] + np.asarray(c, np.float64)[None]
    return outward(pc)


# ----------------------------------------------------------------------------- Blender
def make_object(name: str, pc: dict, smooth: bool = True) -> bpy.types.Object:
    """A Blender mesh object from a piece (quads; a triangle written as a quad with its last index repeated)."""
    v, f = pc['v'], pc['f']
    tri = f[:, 2] == f[:, 3]
    loops = np.concatenate([f[~tri].ravel(), f[tri][:, :3].ravel()]).astype(np.int32)
    sizes = np.concatenate([np.full(int((~tri).sum()), 4), np.full(int(tri.sum()), 3)])
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set('co', np.ascontiguousarray(v, np.float32).ravel())
    me.loops.add(len(loops))
    me.loops.foreach_set('vertex_index', loops)
    me.polygons.add(len(sizes))
    me.polygons.foreach_set('loop_start', starts)
    me.update(calc_edges=True)
    me.validate(verbose=False)
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    for k, a in pc['a'].items():
        if len(a) != len(me.vertices):
            continue
        dom = me.attributes.new(k, 'FLOAT' if a.ndim == 1 else 'FLOAT_VECTOR', 'POINT')
        if a.ndim == 1:
            dom.data.foreach_set('value', np.ascontiguousarray(a, np.float32))
        else:
            dom.data.foreach_set('vector', np.ascontiguousarray(a, np.float32).ravel())
    return ob


def bvh(pc: dict) -> BVHTree:
    """A BVH tree of a piece's triangles (for projecting points onto it)."""
    return BVHTree.FromPolygons([tuple(p) for p in pc['v']], [tuple(int(i) for i in t) for t in tri_of(pc['f'])])


def nearest(tree: BVHTree, pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The nearest surface point and its face normal for every point."""
    loc = np.empty_like(pts)
    nrm = np.empty_like(pts)
    for i, p in enumerate(pts):
        hit = tree.find_nearest(p)
        loc[i] = hit[0]
        nrm[i] = hit[1]
    return loc, nrm


def ray(tree: BVHTree, origins: np.ndarray, dirs: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The first hit of each ray: location, face normal, and whether it hit."""
    loc = np.zeros_like(origins)
    nrm = np.zeros_like(origins)
    ok = np.zeros(len(origins), bool)
    for i, (o, d) in enumerate(zip(origins, dirs)):
        hit = tree.ray_cast(o, d)
        if hit[0] is not None:
            loc[i], nrm[i], ok[i] = hit[0], hit[1], True
    return loc, nrm, ok


def smooth_rows(P: np.ndarray, iters: int, k: float = 0.5, closed: bool = False) -> np.ndarray:
    """Laplacian smoothing along the first axis of a (J, ...) array (path samples), the ends kept unless closed."""
    P = P.copy()
    for _ in range(iters):
        if closed:
            Q = 0.5 * (np.roll(P, 1, axis=0) + np.roll(P, -1, axis=0))
            P = P + k * (Q - P)
        else:
            Q = P.copy()
            Q[1:-1] = 0.5 * (P[:-2] + P[2:])
            P = P + k * (Q - P)
    return P


def resample(path: np.ndarray, step: float, closed: bool = False) -> np.ndarray:
    """A polyline resampled at about `step` metres (the ends kept)."""
    P = np.concatenate([path, path[:1]]) if closed else path
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(math.ceil(cum[-1] / step)) + (0 if closed else 1))
    want = np.linspace(0.0, cum[-1], n, endpoint=not closed)
    return np.stack([np.interp(want, cum, P[:, i]) for i in range(3)], axis=1)
