"""Gloomgrin's ringed props (Art 2.1 Ultra): claws, spikes, horns, the wing's arm and finger struts, the tail's
arrowhead. Each item is a stack of vertex rings along its own path (base to tip; a ring of radius 0 is an apex).

Flat items give every face its own vertices (crisp chipped facets, a shade per facet); smooth items share them (a horn,
a wing limb). Every face is turned outward against its OWN item's path, never a neighbour's (Grumblestone's lesson: a
cluster oriented by the nearest axis flipped faces and showed a "folded flag").

Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import v3


def path_frames(path: np.ndarray, up=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per path point: the tangent T and two normals E1, E2, carried along by parallel transport (so a curved claw or a
    horn doesn't twist). E1 starts as `up` made square to the first tangent (else world Z, or X for a vertical start)."""
    path = np.asarray(path, np.float64)
    k = len(path)
    seg = path[1:] - path[:-1]
    seg = seg / np.maximum(np.linalg.norm(seg, axis=1, keepdims=True), 1e-12)
    T = np.zeros((k, 3))
    T[0], T[-1] = seg[0], seg[-1]
    for i in range(1, k - 1):
        t = seg[i - 1] + seg[i]
        T[i] = t / max(float(np.linalg.norm(t)), 1e-12)
    ref = v3(up) if up is not None else (np.array([0.0, 0.0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0.0, 0.0]))
    e = ref - T[0] * float(ref @ T[0])
    if np.linalg.norm(e) < 1e-6:
        e = np.array([1.0, 0.0, 0.0]) - T[0] * T[0][0]
    e = e / np.linalg.norm(e)
    E1 = [e]
    for i in range(1, k):
        e = e - T[i] * float(e @ T[i])
        e = e / max(float(np.linalg.norm(e)), 1e-12)
        E1.append(e)
    E1 = np.array(E1)
    E2 = np.cross(T, E1)
    return T, E1, E2


def ring_points(item: dict) -> tuple[list[np.ndarray], np.ndarray]:
    """The vertex rings of one ringed item, base to tip (a ring of radius 0 is a single apex point), and the path."""
    path = np.asarray(item['path'], np.float64)
    radii = list(item['radii'])
    n = int(item.get('sides', 8))
    k1, k2 = item.get('aspect', (1.0, 1.0))
    T, E1, E2 = path_frames(path, item.get('up'))
    rng = np.random.default_rng(int(item.get('seed', 0)))
    roll = float(item.get('roll', 0.0))
    ang = np.linspace(0.0, 2 * math.pi, n, endpoint=False) + roll
    jit = float(item.get('jitter', 0.0))
    pw = float(item.get('power', 1.0))           # < 1: a squarish cross-section (a tooth), 1: an ellipse
    rings = []
    for i, (c, r) in enumerate(zip(path, radii)):
        if r <= 1e-9:
            rings.append(c[None].copy())
            continue
        rr = r * (1.0 + jit * rng.uniform(-1.0, 1.0, n))
        aa = ang + jit * 0.5 * rng.uniform(-1.0, 1.0, n)
        ca, sa = np.cos(aa), np.sin(aa)
        if pw != 1.0:
            ca, sa = np.sign(ca) * np.abs(ca) ** pw, np.sign(sa) * np.abs(sa) ** pw
        pts = c[None] + (E1[i][None] * (ca * k1)[:, None] + E2[i][None] * (sa * k2)[:, None]) * rr[:, None]
        rings.append(pts)
    return rings, path


def ringed_object(name: str, items: list[dict], flat: bool = True, extra_attrs=()) -> bpy.types.Object:
    """One mesh of ringed items (each: path, radii, sides, aspect, up, roll, jitter, seed, kind, anchor, cap, and any
    `extra_attrs` keys as numbers). Attributes: `pt` (t along 0 base … 1 tip, facet shade −1..1, around 0..1), `gpart`
    (the item's kind), `anchor` (where its skin weights come from), `item` (its index), and each extra key."""
    verts: list[np.ndarray] = []
    faces: list[list[int]] = []
    a_t, a_sh, a_ar, a_kind, a_anchor, a_item = [], [], [], [], [], []
    extra = {k: [] for k in extra_attrs}

    for ii, it in enumerate(items):
        rings, path = ring_points(it)
        rng = np.random.default_rng(int(it.get('seed', 0)) + 911)
        K = len(rings)
        ts = np.linspace(0.0, 1.0, K)
        anchor = v3(it.get('anchor', path[0]))
        kind = float(it.get('kind', 0.0))
        T0 = path[1] - path[0]
        T0 = T0 / max(float(np.linalg.norm(T0)), 1e-12)

        def axis_at(tm: float, path=path, K=K) -> np.ndarray:
            x = tm * (K - 1)
            i0 = min(int(math.floor(x)), K - 2)
            f = x - i0
            return path[i0] * (1 - f) + path[i0 + 1] * f

        def push_vertex(p, tv, av, fs, it=it, kind=kind, anchor=anchor, ii=ii) -> int:
            verts.append(p)
            a_t.append(tv)
            a_sh.append(fs)
            a_ar.append(av)
            a_kind.append(kind)
            a_anchor.append(anchor)
            a_item.append(float(ii))
            for kx in extra:
                extra[kx].append(float(it.get(kx, 0.0)))
            return len(verts) - 1

        def emit(pts, tv, av, out_ref, shared=None, rng=rng) -> None:
            nrm = np.zeros(3)
            for j in range(len(pts)):
                nrm += np.cross(pts[j], pts[(j + 1) % len(pts)])
            order = list(range(len(pts)))
            if float(nrm @ out_ref) < 0:
                order = order[::-1]
            if shared is not None:
                faces.append([shared[j] for j in order])
                return
            fs = rng.uniform(-1.0, 1.0)
            faces.append([push_vertex(pts[j], tv[j], av[j], fs) for j in order])

        idx = None
        if not flat:
            idx = [[push_vertex(p, ts[r], j / max(1, len(ring)), 0.0) for j, p in enumerate(ring)] for r, ring in enumerate(rings)]
        for r in range(K - 1):
            A, B = rings[r], rings[r + 1]
            ref_c = axis_at((ts[r] + ts[r + 1]) * 0.5)
            m = len(A)
            for j in range(m):
                jn = (j + 1) % m
                if len(B) == 1:
                    pts = [A[j], A[jn], B[0]]
                    tv = [ts[r], ts[r], ts[r + 1]]
                    av = [j / m, jn / m, j / m]
                    sh = [idx[r][j], idx[r][jn], idx[r + 1][0]] if idx is not None else None
                else:
                    pts = [A[j], A[jn], B[jn], B[j]]
                    tv = [ts[r], ts[r], ts[r + 1], ts[r + 1]]
                    av = [j / m, jn / m, jn / m, j / m]
                    sh = [idx[r][j], idx[r][jn], idx[r + 1][jn], idx[r + 1][j]] if idx is not None else None
                emit(pts, tv, av, np.mean(pts, axis=0) - ref_c, sh)
        if it.get('cap', False) and len(rings[0]) > 2:
            pts = list(rings[0])
            sh = list(idx[0]) if idx is not None else None
            emit(pts, [0.0] * len(pts), [0.0] * len(pts), -T0, sh)
        if it.get('cap_tip', False) and len(rings[-1]) > 2:
            T1 = path[-1] - path[-2]
            pts = list(rings[-1])
            sh = list(idx[-1]) if idx is not None else None
            emit(pts, [1.0] * len(pts), [0.0] * len(pts), T1, sh)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in verts], [], [tuple(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    n = len(verts)
    S.add_attr(ob, 'pt', np.stack([np.array(a_t), np.array(a_sh), np.array(a_ar)], axis=1))
    S.add_attr(ob, 'gpart', np.array(a_kind))
    S.add_attr(ob, 'anchor', np.array(a_anchor).reshape(n, 3))
    S.add_attr(ob, 'item', np.array(a_item))
    for kx, vals in extra.items():
        S.add_attr(ob, kx, np.array(vals))
    for p in me.polygons:
        p.use_smooth = not flat
    return ob


def subdivide(ob: bpy.types.Object, cuts: int) -> None:
    """Subdivide every face (simple, no smoothing), interpolating the point attributes (a high source dense enough to
    carry a per-vertex rune or ring groove)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=int(cuts), use_grid_fill=True)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def bezier(p0, p1, p2, n: int) -> list[np.ndarray]:
    """n points on a quadratic Bézier (a curved claw, horn or spike)."""
    p0, p1, p2 = v3(p0), v3(p1), v3(p2)
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in np.linspace(0.0, 1.0, n)]
