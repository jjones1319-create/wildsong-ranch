"""Scrollopus's mesh builders (Art 2.1 Ultra; a copy of moatshell_geo.py, so the breeds never change each other):
numpy pieces (vertices, quad faces, per-vertex attributes) for the props, and a fast Blender mesh maker. Every builder takes a
grid step, so the same code makes the high source (a few millimetres) and the game mesh (a few centimetres), and the
two agree in shape. Metres; the monster faces −Y, Z is up, +X is its left.

A Piece is a dict: 'v' (n×3), 'f' (m×4 int quads; a triangle repeats its last index), 'a' {name: n or n×3 arrays}.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C


def piece(v, f, **attrs) -> dict:
    v = np.asarray(v, np.float64).reshape(-1, 3)
    out = {'v': v, 'f': np.asarray(f, np.int64).reshape(-1, 4), 'a': {}}
    for k, a in attrs.items():
        a = np.asarray(a, np.float64)
        out['a'][k] = np.full(len(v), float(a)) if a.ndim == 0 else a
    return out


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


def axis_coords(h: float, r: float, step: float, bevel_rows: int) -> np.ndarray:
    """Coordinates along one box axis from −h to h: `bevel_rows` rows inside each rounded band of width r (they land on
    the bevel's arc once rounded) and the flat middle at about `step`."""
    r = min(r, 0.999 * h)
    mid = max(1, int(math.ceil((2 * (h - r)) / max(step, 1e-6))))
    inner = np.linspace(-(h - r), h - r, mid + 1)
    if r <= 1e-6 or bevel_rows <= 0:
        return np.concatenate([[-h], inner[1:-1], [h]]) if r > 1e-6 else inner
    band = np.linspace(0.0, 1.0, bevel_rows + 1)[1:]          # fractions of r past the flat
    lo = -(h - r) - r * band[::-1]
    hi = (h - r) + r * band
    return np.concatenate([lo, inner, hi])


def rounded_box(half, r, step: float, bevel_rows: int = 2) -> dict:
    """A closed box with rounded edges, centred at 0 (local coords): 'v', 'f' and attributes 'edge' (metres to the
    nearest edge of the unrounded box: chips go there), 'loc' (the vertex before rounding, n×3)."""
    half = np.asarray(half, np.float64)
    r = float(min(r, 0.95 * half.min()))
    ax = [axis_coords(float(h), r, step, bevel_rows) for h in half]
    pts, faces = [], []
    off = 0
    for k in range(3):
        u_ax, v_ax = (k + 1) % 3, (k + 2) % 3
        for sgn in (-1.0, 1.0):
            U, V = np.meshgrid(ax[u_ax], ax[v_ax], indexing='ij')
            p = np.zeros(U.shape + (3,))
            p[..., k] = sgn * half[k]
            p[..., u_ax] = U
            p[..., v_ax] = V
            nu, nv = U.shape[0] - 1, U.shape[1] - 1
            f = grid_faces(nu, nv)
            # outward winding: (u × v) points along +k, so flip on the − side
            f = f if sgn > 0 else f[:, ::-1]
            pts.append(p.reshape(-1, 3))
            faces.append(f + off)
            off += p.shape[0] * p.shape[1]
    P = np.concatenate(pts)
    F = np.concatenate(faces)
    key = np.round(P / max(1e-7, 1e-4 * step), 0).astype(np.int64)
    _u, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    P = P[first]
    F = inv[F]
    inner = half - r
    cl = np.clip(P, -inner, inner)
    d = P - cl
    dl = np.linalg.norm(d, axis=1)
    Q = cl + np.where(dl[:, None] > 1e-12, d / np.maximum(dl, 1e-12)[:, None] * r, d)
    gap = np.sort(half[None] - np.abs(P), axis=1)
    edge = gap[:, 1]                                            # the second smallest: the distance to the nearest edge
    return {'v': Q, 'f': F, 'a': {'edge': edge, 'loc': P}}


def torus(R: float, r: float, nu: int, nv: int) -> dict:
    """A torus in the XY plane about Z (u round the ring, v round the tube)."""
    u = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    v = np.linspace(0, 2 * math.pi, nv, endpoint=False)
    U, V = np.meshgrid(u, v, indexing='ij')
    x = (R + r * np.cos(V)) * np.cos(U)
    y = (R + r * np.cos(V)) * np.sin(U)
    z = r * np.sin(V)
    P = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    # wrap both ways: build by hand
    i, j = np.meshgrid(np.arange(nu), np.arange(nv), indexing='ij')
    i, j = i.ravel(), j.ravel()
    a = i * nv + j
    b = ((i + 1) % nu) * nv + j
    c = ((i + 1) % nu) * nv + (j + 1) % nv
    d = i * nv + (j + 1) % nv
    return {'v': P, 'f': np.stack([a, b, c, d], axis=1), 'a': {}}


def tube(points: np.ndarray, radius, nu: int, cap: bool = True) -> dict:
    """A tube along a polyline (radius a number or one per point), with flat caps."""
    pts = np.asarray(points, np.float64)
    rad = np.broadcast_to(np.asarray(radius, np.float64), (len(pts),))
    t = np.gradient(pts, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
    ref = np.array([1.0, 0.0, 0.0]) if abs(t[0] @ np.array([1.0, 0, 0])) < 0.9 else np.array([0.0, 1.0, 0.0])
    rings = []
    nrm = np.cross(t[0], ref)
    nrm /= np.linalg.norm(nrm)
    for k in range(len(pts)):
        nrm = nrm - t[k] * (nrm @ t[k])
        nrm /= max(np.linalg.norm(nrm), 1e-12)
        bn = np.cross(t[k], nrm)
        a = np.linspace(0, 2 * math.pi, nu, endpoint=False)
        rings.append(pts[k] + rad[k] * (np.cos(a)[:, None] * nrm + np.sin(a)[:, None] * bn))
    R = np.stack(rings)              # (n, nu, 3)
    n = len(pts)
    P = R.transpose(1, 0, 2).reshape(-1, 3)     # u major: index = iu * n + k
    F = grid_faces(nu, n - 1, wrap_u=True, flip=True)
    out = {'v': P, 'f': F, 'a': {}}
    if cap:
        extra_v, extra_f = [], []
        base = len(P)
        for end, k in ((0, 0), (1, n - 1)):
            c = base + len(extra_v)
            extra_v.append(pts[k])
            for iu in range(nu):
                a_, b_ = iu * n + k, ((iu + 1) % nu) * n + k
                extra_f.append([c, a_, b_, b_] if end == 0 else [c, b_, a_, a_])
        out['v'] = np.concatenate([P, np.array(extra_v)])
        out['f'] = np.concatenate([F, np.array(extra_f, np.int64)])
    return out


def uv_sphere(c, r, nu: int, nv: int) -> dict:
    u = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    v = np.linspace(-math.pi / 2, math.pi / 2, nv + 1)[1:-1]
    U, V = np.meshgrid(u, v, indexing='ij')
    P = np.stack([np.cos(V) * np.cos(U), np.cos(V) * np.sin(U), np.sin(V)], axis=-1).reshape(-1, 3)
    m = len(v)
    F = list(grid_faces(nu, m - 1, wrap_u=True))
    top = nu * m
    bot = top + 1
    for iu in range(nu):
        a, b = iu * m + m - 1, ((iu + 1) % nu) * m + m - 1
        F.append([a, b, top, top])
        a0, b0 = iu * m, ((iu + 1) % nu) * m
        F.append([b0, a0, bot, bot])
    P = np.concatenate([P, [[0, 0, 1.0], [0, 0, -1.0]]]) * r + np.asarray(c, np.float64)
    return {'v': P, 'f': np.array(F, np.int64), 'a': {}}


def thick_sheet(P: np.ndarray, N: np.ndarray, nu: int, nv: int, t: float) -> dict:
    """A closed slab from a grid of mid-surface points P ((nu+1)·(nv+1), u major) with normals N: the front at +t/2,
    the back at −t/2, and a rim joining their boundaries."""
    front = P + N * (t / 2)
    back = P - N * (t / 2)
    n = len(P)
    Ff = grid_faces(nu, nv)
    Fb = grid_faces(nu, nv)[:, ::-1] + n
    # the boundary loop of the grid, in order
    idx = lambda i, j: i * (nv + 1) + j  # noqa: E731
    loop = [idx(i, 0) for i in range(nu + 1)] + [idx(nu, j) for j in range(1, nv + 1)] + \
           [idx(i, nv) for i in range(nu - 1, -1, -1)] + [idx(0, j) for j in range(nv - 1, 0, -1)]
    rim = []
    for k in range(len(loop)):
        a, b = loop[k], loop[(k + 1) % len(loop)]
        rim.append([a, a + n, b + n, b])
    return {'v': np.concatenate([front, back]), 'f': np.concatenate([Ff, Fb, np.array(rim, np.int64)]), 'a': {}}


def orient_closed(pc: dict) -> dict:
    """Scrollopus: turn a closed piece's faces outward (by the sign of its enclosed volume), whatever the handedness of
    the frame it was laid out in (a mirrored frame turns every face inward: dark, inside-out props in the game)."""
    v, f = pc['v'], pc['f']
    if not len(f):
        return pc
    a, b, c, d = (v[f[:, k]] for k in range(4))
    vol = float((a * np.cross(b, c)).sum() + (a * np.cross(c, d)).sum()) / 6.0
    if vol < 0:
        tri = f[:, 2] == f[:, 3]
        pc['f'] = np.where(tri[:, None], f[:, [2, 1, 0, 0]], f[:, ::-1])
    return pc


def make_object(name: str, pc: dict, smooth: bool = True) -> bpy.types.Object:
    """A Blender mesh object from a piece (quads; a triangle written as a quad with its last index repeated)."""
    v, f = pc['v'], pc['f']
    tri = f[:, 2] == f[:, 3]
    sizes = np.where(tri, 3, 4)
    loops = np.concatenate([f[~tri].ravel(), f[tri][:, :3].ravel()]).astype(np.int32)
    order_sizes = np.concatenate([np.full(int((~tri).sum()), 4), np.full(int(tri.sum()), 3)])
    starts = np.concatenate([[0], np.cumsum(order_sizes)[:-1]]).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(v))
    me.vertices.foreach_set('co', np.ascontiguousarray(v, np.float32).ravel())
    me.loops.add(len(loops))
    me.loops.foreach_set('vertex_index', loops)
    me.polygons.add(len(order_sizes))
    me.polygons.foreach_set('loop_start', starts)
    me.update(calc_edges=True)
    me.validate(verbose=False)
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    # the face attributes ride in face order: quads first, then triangles (as written above)
    ob['_face_order'] = 1
    _ = sizes
    for k, a in pc['a'].items():
        if len(a) != len(v):
            continue
        dom = me.attributes.new(k, 'FLOAT' if a.ndim == 1 else 'FLOAT_VECTOR', 'POINT')
        if a.ndim == 1:
            dom.data.foreach_set('value', np.ascontiguousarray(a, np.float32))
        else:
            dom.data.foreach_set('vector', np.ascontiguousarray(a, np.float32).ravel())
    return ob


def face_order(pc: dict) -> np.ndarray:
    """The order make_object writes a piece's faces in (quads first, then triangles): index into pc['f']."""
    tri = pc['f'][:, 2] == pc['f'][:, 3]
    return np.concatenate([np.nonzero(~tri)[0], np.nonzero(tri)[0]])


def set_face_attr(ob: bpy.types.Object, name: str, values: np.ndarray) -> None:
    me = ob.data
    if name in me.attributes:
        me.attributes.remove(me.attributes[name])
    a = me.attributes.new(name, 'FLOAT', 'FACE')
    a.data.foreach_set('value', np.ascontiguousarray(values, np.float32))
