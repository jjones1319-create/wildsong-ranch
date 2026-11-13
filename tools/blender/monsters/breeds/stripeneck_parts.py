"""Stripeneck Ultra: the shaped parts (docs/ART_2_DETAIL.md §9; chatgpt/monsters/31-stripeneck/).

  - the ears: big leaf flaps, cupped, the pink lining facing forward and out (fur slabs in the voxel body);
  - the brush mane: one crest swept along the back of the neck, from a forelock between the ossicones down to the
    withers, flat-topped and splaying toward its outer edge, which dips a little between the bands (charcoal and cream
    alternate band by band), as in 2-turnaround.png back and side and 4-details.png panel 5 (closed mesh, voxel body);
  - the tail tuft: wavy clumps hanging from the end of the striped tail, each a swept tube that tapers to a point and
    waves left and right (closed meshes in the voxel body);
  - the cloven hooves: two D-shaped toes per hoof with a clear cleft, a front wall sloping back, flat soles (voxel body);
  - the lashes: long curved lashes fanning up and out from the outer two thirds of each upper lid (props on the blink
    bones, so a blink folds them down onto the closed lid's lash line).

Everything is numpy and bmesh; metres, the monster faces −Y, Z is up, +X is its left. Size: HEIGHT_UNITS 300, two
Puddlepups tall (1.97 m to the ossicone tufts).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3


# ----------------------------------------------------------------------------- mesh helpers
def grid_object(name: str, P: np.ndarray, closed_u: bool, caps: tuple[bool, bool] = (False, False)) -> bpy.types.Object:
    """A quad grid from points P (rows × cols × 3): rows along the length, cols around (closed_u wraps them); caps close
    the first / last ring with a fan. Faces point away from each ring's centre."""
    rows, cols = P.shape[:2]
    bm = bmesh.new()
    V = [[bm.verts.new(P[j, i]) for i in range(cols)] for j in range(rows)]
    nc = cols if closed_u else cols - 1
    for j in range(rows - 1):
        for i in range(nc):
            i2 = (i + 1) % cols
            bm.faces.new((V[j][i], V[j][i2], V[j + 1][i2], V[j + 1][i]))
    for end, on in ((0, caps[0]), (rows - 1, caps[1])):
        if not on:
            continue
        c = bm.verts.new(P[end].mean(axis=0))
        for i in range(cols):
            i2 = (i + 1) % cols
            f = (V[end][i], V[end][i2], c) if end == rows - 1 else (V[end][i2], V[end][i], c)
            bm.faces.new(f)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.normal_update()
    # orient: the mean of (face normal · (face centre − its ring's centre)) must be positive
    ctr = v3(P.reshape(-1, 3).mean(axis=0))
    acc = 0.0
    for f in bm.faces:
        acc += float(v3(f.normal) @ (v3(f.calc_center_median()) - ctr))
    if acc < 0:
        for f in bm.faces:
            f.normal_flip()
        bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def frames(path: np.ndarray, up=(1.0, 0.0, 0.0)) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rotation-minimising frames (T, N, B) along a polyline (n × 3)."""
    T = np.gradient(path, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    N = np.zeros_like(T)
    n0 = np.cross(T[0], v3(up))
    if np.linalg.norm(n0) < 1e-6:
        n0 = np.cross(T[0], v3((0.0, 0.0, 1.0)))
    N[0] = n0 / np.linalg.norm(n0)
    for i in range(1, len(T)):
        n = N[i - 1] - T[i] * (N[i - 1] @ T[i])
        N[i] = n / max(np.linalg.norm(n), 1e-9)
    return T, N, np.cross(T, N)


def tube(name: str, path: np.ndarray, radii: np.ndarray, sides: int = 14, squash: float = 1.0, up=(1.0, 0.0, 0.0)) -> bpy.types.Object:
    """A closed tube swept along `path` (n × 3) with per-ring radius; `squash` flattens it along B (a ribbon-ish clump)."""
    T, N, B = frames(path, up)
    g = np.linspace(0.0, 2 * np.pi, sides, endpoint=False)
    ring = np.cos(g)[None, :, None] * N[:, None, :] + (np.sin(g) * squash)[None, :, None] * B[:, None, :]
    P = path[:, None, :] + ring * np.asarray(radii)[:, None, None]
    return grid_object(name, P, True, caps=(True, True))


def catmull(ctrl, n: int) -> np.ndarray:
    """A centripetal Catmull-Rom curve through the control points, about n samples."""
    P = np.asarray(ctrl, np.float64)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    segs = len(P) - 3
    per = max(2, n // segs)
    for i in range(segs):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-9) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-9) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-9) ** 0.5
        for t in np.linspace(t1, t2, per, endpoint=i == segs - 1):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    return np.array(out)


# ----------------------------------------------------------------------------- the ears (fur slabs in the voxel body)
EAR_ROOT = np.array((0.158, -0.385, 1.715))
EAR_DIR = np.array((0.66, 0.46, 0.6))
EAR_DIR = EAR_DIR / np.linalg.norm(EAR_DIR)
EAR_LEN = 0.27
EAR_W = 0.172                 # the leaf's widest (round 2: broader; round 1 read as a narrow cone)
EAR_OPEN = np.array((0.5, -0.86, 0.12))     # the lining (cupped side) looks this way: forward and out (front, side, 3/4)
EAR_CURL = 0.088              # how far the leaf's edges come forward round the cupped lining (upgrade: deeper cups;
#                               v1.23.0's read as flat discs)


def ear_axes(s: int):
    """(along, across, open) unit axes of an ear; `open` is the lining's side."""
    d = EAR_DIR * v3((s, 1, 1))
    o = EAR_OPEN * v3((s, 1, 1))
    o = o - d * (o @ d)
    o /= np.linalg.norm(o)
    a = np.cross(d, o)
    a /= np.linalg.norm(a)
    return d, a, o


def ear_width(u):
    """Half-width along the ear: a broad leaf, widest a little below the middle, closing to a rounded point."""
    u = np.asarray(u, np.float64)
    body = 0.45 + 0.55 * np.sin(np.pi * np.clip(0.08 + 0.9 * u, 0, 1))
    # round 3b: a rounder tip; review Nov 13 (a notch bitten from the tip): closing to a point, no square end
    return EAR_W * 0.5 * body * (1 - smooth(0.6, 1.02, u) ** 2.0) + 0.009 * (1 - smooth(0.84, 1.0, u)) + 0.0015


EAR_BOWL = 0.024             # review Nov 12: a real cup (the lining's middle sits back, the back rounds out)


def ear_bowl(u, v):
    """How far the leaf's middle sits back from its edges (a bowl in both directions)."""
    u = np.clip(np.asarray(u, np.float64), 0, 1)
    v = np.clip(np.asarray(v, np.float64), -1, 1)
    return EAR_BOWL * (1 - v ** 2) * np.sin(np.pi * np.clip(u / 0.92, 0, 1)) ** 0.8


def ear_curl(u, v):
    """How far the leaf's edges come forward round the cupped lining. Round 3b (review: a notched tip and a torn rim):
    in proportion to the leaf's width, so the narrowing tip no longer folds 6 cm forward across its last 1 cm."""
    u = np.clip(np.asarray(u, np.float64), 0, 1)
    wk = np.clip(ear_width(u) / (EAR_W * 0.5), 0.0, 1.0)
    return EAR_CURL * np.clip(v, -1, 1) ** 2 * smooth(0.0, 0.5, u) * wk


def ear_point(s: int, u, v, side: float, thin: bool = False):
    """The slab's surface: u 0 root → 1 tip, v −1..1 across, side +1 the back (fur) / −1 the lining (cupped)."""
    d, a, o = ear_axes(s)
    u, v = np.broadcast_arrays(np.asarray(u, np.float64), np.asarray(v, np.float64))
    root = EAR_ROOT * v3((s, 1, 1))
    w = ear_width(u)
    # a slab of even thickness (thinning toward the tip and the edges) bent into a cup: round 1's lining crossed the
    # back surface in the middle and the voxel body tore holes there
    # round 3: the rim keeps 80% of the thickness (a soft rounded fur edge) (a rounded fur edge; round 1's knife edge decimated into a torn-paper rim)
    # round 3b (review: still a jagged torn-paper rim): thicker to the very edge and the tip (4+ low voxels), a rolled rim
    th = (0.031 * (1 - 0.35 * u) + 0.009) * (0.92 + 0.08 * np.sqrt(np.clip(1 - v ** 2, 0, 1)) ** 0.5)
    if thin:
        # the prop: thin, a rim that rounds off and thins toward the tip (no voxel staircase)
        th = (0.02 * (1 - 0.55 * np.clip(u, 0, 1)) + 0.005) * (0.55 + 0.45 * np.sqrt(np.clip(1 - v ** 2, 0, 1)))
    mid = root + d * (EAR_LEN * u)[..., None] + a * (v * w)[..., None]
    # the leaf curls: its edges come forward (toward the lining side); the tip droops a touch
    mid = mid + o * (ear_curl(u, v) - ear_bowl(u, v))[..., None] - v3((0, 0, 1)) * (0.018 * u ** 2)[..., None]
    if side > 0:
        return mid - o * (th * 0.55)[..., None]
    return mid + o * (th * 0.45)[..., None]


def ear_slab(s: int, nu: int = 44, nv: int = 26, thin: bool = False, name: str | None = None) -> bpy.types.Object:
    us = np.linspace(-0.2, 1.0, nu + 1)
    # the prop: rows crowd toward the rim so its rounded edge stays smooth
    vs = np.sin(np.linspace(-np.pi / 2, np.pi / 2, nv + 1)) if thin else np.linspace(-1.0, 1.0, nv + 1)
    U_, V_ = np.meshgrid(us, vs, indexing='ij')
    back = ear_point(s, U_, V_, 1.0, thin)
    front = ear_point(s, U_, V_, -1.0, thin)
    bm = bmesh.new()
    vb = [[bm.verts.new(back[j, i]) for i in range(nv + 1)] for j in range(nu + 1)]
    vf = [[bm.verts.new(front[j, i]) for i in range(nv + 1)] for j in range(nu + 1)]
    for j in range(nu):
        for i in range(nv):
            bm.faces.new((vb[j][i], vb[j + 1][i], vb[j + 1][i + 1], vb[j][i + 1]))
            bm.faces.new((vf[j][i], vf[j][i + 1], vf[j + 1][i + 1], vf[j + 1][i]))
    for j in range(nu):
        for i in (0, nv):
            q = (vb[j][i], vf[j][i], vf[j + 1][i], vb[j + 1][i])
            bm.faces.new(q if i == 0 else q[::-1])
    for j in (0, nu):
        for i in range(nv):
            q = (vb[j][i], vb[j][i + 1], vf[j][i + 1], vf[j][i])
            bm.faces.new(q if j == 0 else q[::-1])
    if thin:
        # review Nov 13 (streaked, stepped pink): the prop's own unwrap, the back and the lining each one flat island
        # laid out by (u, v), the rims and the ends thin strips beside them; the ears side by side (no overlap)
        uvl = bm.loops.layers.uv.new('UVMap')
        where = {}
        for j in range(nu + 1):
            for i in range(nv + 1):
                where[vb[j][i]] = (us[j], vs[i], 0)
                where[vf[j][i]] = (us[j], vs[i], 1)
        ox = 0.0 if s > 0 else 0.5
        for f in bm.faces:
            keys = [where[lp.vert] for lp in f.loops]
            sides = {k[2] for k in keys}
            vv = [k[1] for k in keys]
            uu = [k[0] for k in keys]
            for lp, (uk, vk, sk) in zip(f.loops, keys):
                if len(sides) == 1:                       # a sheet: the back (0) or the lining (1)
                    lp[uvl].uv = (ox + 0.02 + (uk + 0.2) * 0.3, 0.02 + sk * 0.3 + (vk + 1) * 0.12)
                elif max(abs(x) for x in vv) > 0.999 and min(abs(x) for x in vv) > 0.999:   # a rim strip
                    lp[uvl].uv = (ox + 0.02 + (uk + 0.2) * 0.3, 0.62 + (0.0 if vv[0] < 0 else 0.06) + sk * 0.02)
                else:                                     # an end (root or tip)
                    lp[uvl].uv = (ox + 0.02 + (vk + 1) * 0.1, 0.74 + (0.0 if uu[0] < 0.5 else 0.06) + sk * 0.02)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name or f'earslab{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
    return ob


def ear_coords(p: np.ndarray, s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(u, v, h) of points on ear `s` (h > 0 on the lining's side of the leaf's middle)."""
    d, a, o = ear_axes(s)
    q = p - EAR_ROOT * v3((s, 1, 1))
    u = (q @ d) / EAR_LEN
    w = ear_width(np.clip(u, 0, 1))
    v = (q @ a) / np.maximum(w, 1e-4)
    h = q @ o - ear_curl(u, v) + ear_bowl(u, v) + 0.018 * np.clip(u, 0, 1) ** 2 * (v3((0, 0, 1)) @ o)
    return u, v, h


def ear_prop(s: int, high: bool, name: str) -> bpy.types.Object:
    """One ear as a prop: the thin cup, smooth enough for its own clean UVs (review Nov 12: the voxel rim tore)."""
    nu, nv = (64, 36) if high else (30, 16)
    ob = ear_slab(s, nu, nv, thin=True, name=name)
    # which face each vertex belongs to (0 back, 1 lining), by build order: the back grid's vertices first
    nb = (nu + 1) * (nv + 1)
    if len(ob.data.vertices) == 2 * nb:
        S.add_attr(ob, 'ear_face', np.concatenate([np.zeros(nb), np.ones(nb)]))
    if not high:
        ob['own_uv'] = True
    return ob


def ear_lookup(p: np.ndarray) -> dict:
    """Per point: on an ear (bool), its u (0 root … 1 tip), v (−1..1 across), and on the lining (bool)."""
    k = len(p)
    out = {'on': np.zeros(k, bool), 'u': np.zeros(k), 'v': np.zeros(k), 'lining': np.zeros(k, bool), 'h': np.zeros(k)}
    for s in (1, -1):
        d, a, o = ear_axes(s)
        q = p - EAR_ROOT * v3((s, 1, 1))
        u = (q @ d) / EAR_LEN
        w = ear_width(np.clip(u, 0, 1))
        v = (q @ a) / np.maximum(w, 1e-4)
        h = q @ o - ear_curl(u, v) + ear_bowl(u, v) + 0.018 * np.clip(u, 0, 1) ** 2 * (v3((0, 0, 1)) @ o)
        # round 3b (review: a brown fleck on the tip): across by distance too, so the narrow tip's rounded end is still ear
        # (by v alone it fell outside and took the coat's patches)
        on = (u > 0.05) & (u < 1.15) & (np.abs(q @ a) < 1.35 * w + 0.015) & (np.abs(h) < 0.045) & (p[:, 0] * s > 0.12)
        out['on'] |= on
        out['u'] = np.where(on, u, out['u'])
        out['v'] = np.where(on, v, out['v'])
        out['h'] = np.where(on, h, out['h'])
        out['lining'] |= on & (h > -0.001) & (np.abs(v) < 0.88) & (u < 0.97)
    return out


# ----------------------------------------------------------------------------- the brush mane (a closed crest in the voxel body)
# The crest's root line on the back of the neck (from the forelock between the ossicones, over the poll, down to the
# withers), and how far each tuft stands out (2-turnaround side: the outer edge stands ~0.15 m off the neck's back).
MANE_ROOT = [(0.0, -0.41, 1.79), (0.0, -0.33, 1.765), (0.0, -0.292, 1.64), (0.0, -0.272, 1.5), (0.0, -0.252, 1.36),
             (0.0, -0.218, 1.23), (0.0, -0.15, 1.13), (0.0, -0.06, 1.097), (0.0, 0.03, 1.09)]
# round 3 (review): eight uneven bands, charcoal first behind the cream forelock, running on to the withers with no gap
# upgrade (review: "a regular barber-pole slab of about 5 even bands"): wide and narrow bands alternate unevenly
BAND_EDGES = [0.0, 0.09, 0.21, 0.29, 0.43, 0.52, 0.67, 0.77, 1.0]


def _mane_curve() -> tuple[np.ndarray, np.ndarray]:
    path = catmull(MANE_ROOT, 160)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    return path, s / s[-1]


def mane_frame(t):
    """Point on the crest's root line at share t (0 poll … 1 withers), its tangent (down the neck) and the outward
    direction (away from the neck, in the midplane)."""
    path, s = _mane_curve()
    t = np.atleast_1d(np.asarray(t, np.float64))
    P = np.stack([np.interp(t, s, path[:, i]) for i in range(3)], axis=1)
    T = np.gradient(path, axis=0)
    T = np.stack([np.interp(t, s, T[:, i]) for i in range(3)], axis=1)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    out = np.cross(v3((1.0, 0.0, 0.0))[None, :], T)        # X × T: back (+Y) and up from a downward tangent
    out /= np.linalg.norm(out, axis=1, keepdims=True)
    return P, T, out


def mane_band(t):
    """(band index, position 0..1 inside the band) along the crest."""
    t = np.clip(np.asarray(t, np.float64), 0.0, 1.0)
    e = np.array(BAND_EDGES)
    i = np.clip(np.searchsorted(e, t, side='right') - 1, 0, len(e) - 2)
    return i, (t - e[i]) / (e[i + 1] - e[i])


def tuft_height(t):
    """How far the brush stands out from the neck (2-turnaround side: ~0.15 m off the neck's back). Round 3: a thicker,
    upright brush, each band a little uneven, still about 6 cm tall where it meets the withers (no tan gap)."""
    t = np.asarray(t, np.float64)
    i, _f = mane_band(t)
    uneven = 1.0 + 0.16 * np.sin(i * 2.3 + 0.7)
    # review Nov 12 (a stack of rolled towels as wide as the neck): only a thin low core; the hair cards are the brush
    return (0.022 + 0.032 * smooth(0.0, 0.22, t) - 0.026 * smooth(0.68, 1.0, t)) * uneven


def mane_width(t):
    """The brush's half width at its root (2-turnaround back: ~0.17 m across at its outer edge)."""
    t = np.asarray(t, np.float64)
    return 0.021 + 0.013 * smooth(0.0, 0.15, t) - 0.008 * smooth(0.85, 1.0, t)


def mane_mesh(nt: int = 170, nr: int = 40) -> bpy.types.Object:
    """The brush mane as one crest swept along the back of the neck: a rounded section that splays wider toward its outer
    edge, dipping a little at each band's edge; tapered at both ends (closed mesh for the voxel body)."""
    ts = np.linspace(0.0, 1.0, nt)
    P, T, O = mane_frame(ts)
    X = np.cross(O, T)
    X *= np.sign(X[:, :1] + 1e-12)
    H = tuft_height(ts)
    e = np.array(BAND_EDGES[1:-1])
    edge_d = np.min(np.abs(ts[:, None] - e[None, :]), axis=1)
    H = H * (1 - 0.2 * np.exp(-(edge_d / 0.016) ** 2))             # upgrade: a deeper parting between the tufts
    wx = mane_width(ts)
    taper = (0.35 + 0.65 * smooth(0.0, 0.05, ts) ** 0.6) * (0.55 + 0.45 * smooth(1.0, 0.94, ts))
    base = -0.03
    th = np.linspace(0.0, 2 * np.pi, nr, endpoint=False)
    cs, sn = np.cos(th), np.sin(th)
    n = 2.5
    px = np.sign(cs) * np.abs(cs) ** (2 / n)
    py = np.sign(sn) * np.abs(sn) ** (2 / n)
    centre = (H + base) * 0.5
    half = (H - base) * 0.5
    hc = centre[:, None] + py[None, :] * half[:, None]
    across = px[None, :] * wx[:, None] * (1.0 + 0.32 * np.clip(hc / np.maximum(H[:, None], 1e-6), 0, 1))
    hc = centre[:, None] + (hc - centre[:, None]) * taper[:, None]
    across = across * taper[:, None]
    pts = P[:, None, :] + O[:, None, :] * hc[..., None] + X[:, None, :] * across[..., None]
    return grid_object('manecrest', pts, True, caps=(True, True))


MANE_BOX = ((-0.13, -0.56, 1.0), (0.13, 0.14, 2.0))


def mane_lookup(p: np.ndarray) -> dict:
    """Per point: t along the crest (0..1), how far out from the root line (metres, along `out`), the band (index and
    position 0..1 inside it) and on the mane (bool). Only points inside MANE_BOX are measured (the rest: t = −1)."""
    from lib.ultra import polyline_param
    k = len(p)
    out = {'on': np.zeros(k, bool), 't': np.full(k, -1.0), 'h': np.zeros(k), 'band': np.zeros(k, np.int64), 'frac': np.zeros(k),
           'hmax': np.zeros(k)}
    lo, hi = v3(MANE_BOX[0]), v3(MANE_BOX[1])
    inb = np.all((p >= lo) & (p <= hi), axis=1)
    if not inb.any():
        return out
    q0 = p[inb]
    path, _s = _mane_curve()
    t, _L = polyline_param(q0, path)
    P, _T, O = mane_frame(np.clip(t, 0, 1))
    h = ((q0 - P) * O).sum(axis=1)
    idx, f = mane_band(t)
    frac = f - 0.5
    hmax = tuft_height(np.clip(t, 0, 1))
    on = (t > -0.03) & (t < 1.02) & (h > 0.012) & (np.abs(q0[:, 0]) < 0.12) & (h < hmax + 0.05)
    out['on'][inb], out['t'][inb], out['h'][inb], out['band'][inb], out['frac'][inb], out['hmax'][inb] = on, t, h, idx, frac, hmax
    return out


# ----------------------------------------------------------------------------- the forelock (round 3)
# a cream-and-charcoal tuft rising between the ossicones (2-turnaround front, 3-faces neutral), the mane starting behind it
# upgrade (review: "a striped cone that reads as a third horn"): only a low rounded mound in the body; its hair cards
# (card_params) stand up and fan out into the soft cream-and-charcoal tuft
FORELOCK = [(0.0, -0.452, 1.718), (0.0, -0.453, 1.76), (0.0, -0.457, 1.8)]


def forelock_path(n: int = 30) -> tuple[np.ndarray, np.ndarray]:
    path = catmull(FORELOCK, n)
    u = np.linspace(0.0, 1.0, len(path))
    r = 0.036 * (1.0 - 0.25 * u) * (1.0 - smooth(0.55, 1.0, u) ** 1.4) + 0.008
    return path, r


def forelock_mesh() -> bpy.types.Object:
    return tube('forelock', *forelock_path(), sides=14, squash=0.72, up=(0.0, 1.0, 0.0))


def forelock_lookup(p: np.ndarray) -> np.ndarray:
    """On the forelock (bool)."""
    on = np.zeros(len(p), bool)
    box = np.all((p >= v3((-0.08, -0.53, 1.7))) & (p <= v3((0.08, -0.37, 1.96))), axis=1)
    if not box.any():
        return on
    q = p[box]
    path, r = forelock_path(24)
    best = np.full(len(q), np.inf)
    for j in range(len(path) - 1):
        a, b = path[j], path[j + 1]
        ab = b - a
        t = np.clip(((q - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        d = np.linalg.norm(q - (a + t[:, None] * ab), axis=1) - (r[j] + (r[j + 1] - r[j]) * t)
        best = np.minimum(best, d)
    on[box] = best < 0.012
    return on


# ----------------------------------------------------------------------------- the tail: a striped stalk, a wavy tuft
TUFT_TOP = np.array((0.0, 0.608, 0.81))
TUFT_TIP_Z = 0.29                 # review Nov 12: about twice as long, to the hocks


def tuft_centre(u):
    """The tuft's S-curved centre line: back, then forward to the tip (1-hero, 2-turnaround side)."""
    u = np.asarray(u, np.float64)
    z = TUFT_TOP[2] - (TUFT_TOP[2] - TUFT_TIP_Z) * u
    y = TUFT_TOP[1] + 0.075 * np.sin(1.6 * np.pi * u)
    x = 0.012 * np.sin(np.pi * u)
    return np.stack([x, y, z], axis=-1)


TAIL_POINTS = [(0.0, 0.47, 1.05), (0.0, 0.555, 0.995), (0.0, 0.6, 0.89)] + [tuple(map(float, tuft_centre(u))) for u in (0.2, 0.6, 1.0)]
# upgrade (review: "a black mitten with finger-like locks from behind, a leaf shape from the side"): a full teardrop core
# along the S-curve, gathered thin at the root, fullest a third of the way down and tapering to a point at hock height;
# thin wavy locks hug it and part from it toward the tip; the hair cards (card_params) over it make the strands
# (angle round the centre line, how far it bellies out, width, wave phase)
TUFT_CLUMPS = [(0.0, 0.05, 0.012, 0.0), (0.7, 0.058, 0.011, 1.3), (1.4, 0.052, 0.012, 2.6), (2.1, 0.06, 0.011, 0.4),
               (2.8, 0.05, 0.012, 3.3), (3.5, 0.058, 0.011, 1.9), (4.2, 0.054, 0.012, 4.4), (4.9, 0.06, 0.011, 2.2),
               (5.6, 0.052, 0.012, 5.1)]


def core_radius(u):
    """The tuft core's radius down the S-curve: gathered at the root, fullest a third of the way down, a point at the tip."""
    u = np.asarray(u, np.float64)
    return 0.012 + 0.034 * np.sin(np.pi * np.clip(u / 0.9, 0, 1)) ** 0.75 * (1 - smooth(0.55, 1.0, u) ** 1.5) + 0.003


def core_path(n: int = 40) -> tuple[np.ndarray, np.ndarray]:
    u = np.linspace(0.0, 1.0, n)
    return tuft_centre(u), core_radius(u)


def clump_path(i: int, n: int = 40) -> tuple[np.ndarray, np.ndarray]:
    """One lock's centre line (n × 3) and radii: from the gathered root it follows the core's surface, waves on its own
    and parts from the core toward the shared tip."""
    ang, R, w, ph = TUFT_CLUMPS[i]
    u = np.linspace(0.0, 1.0, n)
    c = tuft_centre(u)
    # review Nov 12: gathered at the root, fanning out toward the tip, each lock waving on its own
    spread = R * (0.15 + 0.85 * np.clip(u, 0, 1) ** 0.9)
    wave = 0.022 * np.sin(u * 3.2 * np.pi + ph) * np.sin(np.pi * np.clip(u, 0, 1) ** 0.7)
    x = c[:, 0] + (spread + wave) * np.cos(ang)
    y = c[:, 1] + (spread + wave) * np.sin(ang) * 0.8
    path = np.stack([x, y, c[:, 2]], axis=1)
    r = w * (0.55 + 0.45 * np.sin(np.pi * np.clip(u * 1.5, 0, 1)) ** 0.6) * (1 - smooth(0.55, 1.0, u) ** 1.3) + 0.0035
    return path, r


def tuft_tubes(n: int = 40) -> list[tuple[np.ndarray, np.ndarray]]:
    return [core_path(n)] + [clump_path(i, n) for i in range(len(TUFT_CLUMPS))]


def tuft_meshes() -> list[bpy.types.Object]:
    return [tube(f'tuftclump{i}', path, r, sides=16 if i == 0 else 12, squash=0.85 if i == 0 else 0.75)
            for i, (path, r) in enumerate(tuft_tubes())]


TUFT_BOX = ((-0.26, 0.38, 0.1), (0.26, 0.9, 0.86))


def tuft_lookup(p: np.ndarray) -> dict:
    """On the tail's tuft (bool), the nearest clump's u (0 top … 1 tip) and the signed distance to the clumps. Only
    points inside TUFT_BOX are measured."""
    k = len(p)
    best_all = np.full(k, np.inf)
    u_all = np.zeros(k)
    lo, hi = v3(TUFT_BOX[0]), v3(TUFT_BOX[1])
    inb = np.all((p >= lo) & (p <= hi), axis=1)
    if inb.any():
        q = p[inb]
        best = np.full(len(q), np.inf)
        u_best = np.zeros(len(q))
        for path, r in tuft_tubes(30):
            for j in range(len(path) - 1):
                a, b = path[j], path[j + 1]
                ab = b - a
                t = np.clip(((q - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
                d = np.linalg.norm(q - (a + t[:, None] * ab), axis=1) - (r[j] + (r[j + 1] - r[j]) * t)
                better = d < best
                best = np.where(better, d, best)
                u_best = np.where(better, (j + t) / (len(path) - 1), u_best)
        best_all[inb] = best
        u_all[inb] = u_best
    return {'on': best_all < 0.012, 'u': u_all, 'd': best_all}


# ----------------------------------------------------------------------------- the hooves (cloven; in the voxel body)
HOOF_LEN = 0.178       # heel to toe
HOOF_H = 0.1           # at the toe's front wall (the heel lower, under the fetlock's fur)
TOE_W = 0.046          # one toe's half width
SPLIT = 0.02          # the cleft between the toes (stays open at 3.5 mm voxels), closing toward the heel


def hoof_toes(cx: float, cy: float, nring: int = 16, nsides: int = 44) -> list[bpy.types.Object]:
    """Two toes: each a D-shaped column (round outside, straight along the cleft), flat soled, its front wall sloping
    back as it rises, the heel lower and rounder than the toe (4-details.png panel 3)."""
    out = []
    for sg in (1, -1):
        rings = []
        for j in range(nring + 1):
            h = j / nring
            z = HOOF_H * h
            pts = []
            for i in range(nsides):
                g = 2 * np.pi * i / nsides
                cg, sn = math.cos(g), math.sin(g)
                # round 2: a rounder bell (round 1's toes were boxy boots): narrower toward the top
                ry = HOOF_LEN * 0.5 * (1 - 0.3 * h ** 1.3)
                rx = TOE_W * (1 - 0.24 * h ** 1.2)
                yy = -math.copysign(abs(sn) ** 0.92, sn) * ry
                xx = math.copysign(abs(cg) ** 0.88, cg) * rx
                xx = max(xx, -rx * 0.62)                       # the straight cleft side
                yy = yy + HOOF_LEN * 0.27 * h ** 1.25          # the front wall leans back as it rises
                tip = smooth(0.0, -HOOF_LEN * 0.5, yy)
                xx = xx - rx * 0.1 * tip                       # the toe tips turn in a touch
                # the heel (back) sinks under the fetlock fur: lower there
                zz = z * (1.0 - 0.32 * smooth(-0.01, HOOF_LEN * 0.45, yy - HOOF_LEN * 0.27 * h ** 1.25))
                x = cx + sg * (SPLIT * 0.5 * (1 - 0.5 * smooth(-0.02, 0.06, yy)) + rx * 0.62 + xx)
                pts.append((x, cy + yy, zz))
            rings.append(pts)
        P = np.array(rings)
        if sg < 0:
            P = P[:, ::-1]
        out.append(grid_object(f'toe{sg}', P, True, caps=(True, True)))
    return out


# ----------------------------------------------------------------------------- the lashes (props on the blink bones)
N_LASH = 18


def lash_paths(eye_frame, eye_r: float, s: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Four graduated clumps of lashes on the upper lid line (4-details panel 2): each leans forward and curls up, only a
    touch outward, the outer clump longest. Final polish (Nov 13): the roots sit ON the visible lid line (the painted
    lash line runs about 0.55 r above the lens centre), not at the eye sphere's top 0.9 r up; those roots were under the
    far side's skin, so the far eye's lashes came out of the head beyond its outline and hung in the air in every
    three-quarter view."""
    c, xax, yax, look = (v3(a) for a in eye_frame(s))
    out = []
    clumps = [(0.12, 0.16), (0.36, 0.19), (0.6, 0.22), (0.82, 0.24)]       # (place 0 inner … 1 outer, length / r)
    for f0, ln in clumps:
        for k, df in enumerate((-0.05, 0.0, 0.05)):
            f = f0 + df
            xo = (-0.15 + 0.85 * f) * eye_r
            yo = (0.6 - 0.14 * f * f) * eye_r
            root = c + xax * (s * xo) + yax * yo + look * (0.22 * eye_r)
            fwd = v3((0.0, -1.0, 0.0)) - yax * float(v3((0.0, -1.0, 0.0)) @ yax)
            grow = yax * 0.62 + fwd / max(np.linalg.norm(fwd), 1e-6) * 0.7 + xax * (s * 0.05 * f)
            grow = grow / np.linalg.norm(grow)
            L = eye_r * ln * (0.86 + 0.14 * (k == 1))
            n = 10
            uu = np.linspace(0.0, 1.0, n)
            path = root[None, :] + grow[None, :] * (L * uu)[:, None] + (yax * 0.6)[None, :] * (L * 0.35 * uu ** 2)[:, None]
            r = 0.0022 * (1 - uu) ** 0.9 + 0.0004
            out.append((path, r))
    return out


def lash_meshes(name: str, eye_frame, eye_r: float, high: bool) -> list[bpy.types.Object]:
    obs = []
    for s in (1, -1):
        for k, (path, r) in enumerate(lash_paths(eye_frame, eye_r, s)):
            ob = tube(f'{name}{"L" if s > 0 else "R"}{k}', path, r, sides=8 if high else 5)
            S.add_attr(ob, 'lash_side', np.full(len(ob.data.vertices), float(s)))
            obs.append(ob)
    return obs
