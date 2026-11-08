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
EAR_CURL = 0.06               # how far the leaf's edges come forward round the cupped lining


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
    return EAR_W * 0.5 * body * (1 - smooth(0.6, 1.02, u) ** 2.0) + 0.009     # round 3b: a rounder tip


def ear_curl(u, v):
    """How far the leaf's edges come forward round the cupped lining. Round 3b (review: a notched tip and a torn rim):
    in proportion to the leaf's width, so the narrowing tip no longer folds 6 cm forward across its last 1 cm."""
    u = np.clip(np.asarray(u, np.float64), 0, 1)
    wk = np.clip(ear_width(u) / (EAR_W * 0.5), 0.0, 1.0)
    return EAR_CURL * np.clip(v, -1, 1) ** 2 * smooth(0.0, 0.5, u) * wk


def ear_point(s: int, u, v, side: float):
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
    mid = root + d * (EAR_LEN * u)[..., None] + a * (v * w)[..., None]
    # the leaf curls: its edges come forward (toward the lining side); the tip droops a touch
    mid = mid + o * ear_curl(u, v)[..., None] - v3((0, 0, 1)) * (0.018 * u ** 2)[..., None]
    if side > 0:
        return mid - o * (th * 0.55)[..., None]
    return mid + o * (th * 0.45)[..., None]


def ear_slab(s: int, nu: int = 44, nv: int = 26) -> bpy.types.Object:
    us = np.linspace(-0.2, 1.0, nu + 1)
    vs = np.linspace(-1.0, 1.0, nv + 1)
    U_, V_ = np.meshgrid(us, vs, indexing='ij')
    back = ear_point(s, U_, V_, 1.0)
    front = ear_point(s, U_, V_, -1.0)
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
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'earslab{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
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
        h = q @ o - ear_curl(u, v) + 0.018 * np.clip(u, 0, 1) ** 2 * (v3((0, 0, 1)) @ o)
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
BAND_EDGES = [0.0, 0.1, 0.22, 0.35, 0.47, 0.6, 0.72, 0.85, 1.0]


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
    uneven = 1.0 + 0.09 * np.sin(i * 2.3 + 0.7)
    return (0.06 + 0.088 * smooth(0.0, 0.22, t) - 0.088 * smooth(0.68, 1.0, t)) * uneven


def mane_width(t):
    """The brush's half width at its root (2-turnaround back: ~0.17 m across at its outer edge)."""
    t = np.asarray(t, np.float64)
    return 0.042 + 0.028 * smooth(0.0, 0.15, t) - 0.018 * smooth(0.85, 1.0, t)


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
    H = H * (1 - 0.1 * np.exp(-(edge_d / 0.014) ** 2))
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
FORELOCK = [(0.0, -0.452, 1.725), (0.0, -0.448, 1.8), (0.0, -0.438, 1.87), (0.0, -0.45, 1.925)]


def forelock_path(n: int = 30) -> tuple[np.ndarray, np.ndarray]:
    path = catmull(FORELOCK, n)
    u = np.linspace(0.0, 1.0, len(path))
    r = 0.04 * (1.0 - 0.15 * u) * (1.0 - smooth(0.5, 1.0, u) ** 1.4) + 0.004
    return path, r


def forelock_mesh() -> bpy.types.Object:
    # flatter front to back (a flame-shaped brush seen from the front)
    return tube('forelock', *forelock_path(), sides=14, squash=0.62, up=(0.0, 1.0, 0.0))


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
TUFT_TIP_Z = 0.4


def tuft_centre(u):
    """The tuft's S-curved centre line: back, then forward to the tip (1-hero, 2-turnaround side)."""
    u = np.asarray(u, np.float64)
    z = TUFT_TOP[2] - (TUFT_TOP[2] - TUFT_TIP_Z) * u
    y = TUFT_TOP[1] + 0.055 * np.sin(1.6 * np.pi * u)
    x = 0.012 * np.sin(np.pi * u)
    return np.stack([x, y, z], axis=-1)


TAIL_POINTS = [(0.0, 0.47, 1.05), (0.0, 0.555, 0.995), (0.0, 0.6, 0.89)] + [tuple(map(float, tuft_centre(u))) for u in (0.2, 0.6, 1.0)]
# round 3 (review): soft wavy locks that gather at the root and taper to one point (round 2: tentacles, a shaggy box);
# thin enough that they part in the middle (a first try merged into one smooth paddle):
# (angle round the centre line, how far it bellies out, width, wave phase)
TUFT_CLUMPS = [(0.0, 0.085, 0.017, 0.0), (0.7, 0.075, 0.016, 1.3), (1.4, 0.09, 0.017, 2.6), (2.1, 0.07, 0.016, 0.4),
               (2.8, 0.088, 0.017, 3.3), (3.5, 0.072, 0.016, 1.9), (4.2, 0.086, 0.017, 4.4), (4.9, 0.074, 0.016, 2.2),
               (5.6, 0.088, 0.017, 5.1), (0.35, 0.03, 0.02, 3.8)]


def clump_path(i: int, n: int = 40) -> tuple[np.ndarray, np.ndarray]:
    """One lock's centre line (n × 3) and radii: from the gathered root it bellies out round the S-curved centre and
    comes back in to the shared tip, with a gentle wave of its own."""
    ang, R, w, ph = TUFT_CLUMPS[i]
    u = np.linspace(0.0, 1.0, n)
    c = tuft_centre(u)
    spread = R * np.sin(np.pi * np.clip(u, 0, 1) ** 0.85) ** 0.9
    wave = 0.02 * np.sin(u * 3.2 * np.pi + ph) * np.sin(np.pi * u)      # each lock waves on its own
    x = c[:, 0] + (spread + wave) * np.cos(ang)
    y = c[:, 1] + (spread + wave) * np.sin(ang) * 0.75
    path = np.stack([x, y, c[:, 2]], axis=1)
    r = w * (0.55 + 0.45 * np.sin(np.pi * np.clip(u * 1.5, 0, 1)) ** 0.6) * (1 - smooth(0.5, 1.0, u) ** 1.3) + 0.004
    return path, r


def tuft_meshes() -> list[bpy.types.Object]:
    return [tube(f'tuftclump{i}', *clump_path(i), sides=12, squash=0.75) for i in range(len(TUFT_CLUMPS))]


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
        for i in range(len(TUFT_CLUMPS)):
            path, r = clump_path(i, 30)
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
    """Long lashes along the outer two thirds of the upper lid: each rises from the lid line, sweeps out and curls up
    (4-details.png panel 2), the outer ones longest. Returns (path n × 3, radii) per lash."""
    c, xax, yax, look = (v3(a) for a in eye_frame(s))
    out = []
    for k in range(N_LASH):
        f = k / (N_LASH - 1)                     # 0 = over the pupil … 1 = the outer corner
        ang = math.radians(102 - 60 * f)         # round 3: a dense fringe over the outer upper lid, turned up (build 3's
        #                                          outer lashes pointed sideways and splayed past the face like whiskers)
        ey = math.sin(ang)
        # xax points out of the left eye's outer corner and into the right eye's inner corner: × s
        root = c + xax * (math.cos(ang) * 0.98 * eye_r) * s + yax * (ey * 1.02 * eye_r) + look * (0.22 * eye_r)
        outward = xax * (math.cos(ang) * s) + yax * ey
        outward = outward / np.linalg.norm(outward)
        L = eye_r * (0.15 + 0.13 * f)        # round 3: short (round 2's long spikes splayed past the head like whiskers)
        n = 10
        u = np.linspace(0.0, 1.0, n)
        # out from the lid, forward a little, then curling up and out
        path = (root[None, :] + outward[None, :] * (L * u)[:, None] + look[None, :] * (L * 0.3 * u)[:, None]
                + (yax * 1.0 + xax * (0.08 * s))[None, :] * (L * 1.0 * u ** 2)[:, None])
        r = 0.0021 * (1 - u) ** 0.9 + 0.0004
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
