"""Gloomgrin's stone kit (Art 2.1 Ultra; chatgpt/monsters/13-gloomgrin): deterministic noise on numpy arrays, the
surface Voronoi for the cracked plates (seeds laid on the body's own surface: flat chiselled faces, bevelled edges and
narrow cracks between them), rounded blocks for the voxel body, and the faceted prop builder (claws, spikes, the tail's
arrowhead: every face its own vertices, each item turned outward against its OWN axis).

A copy of Grumblestone's kit (grumblestone_stone.py, itself a copy of Cobblemaw's noise), kept here so the breeds never
change each other. Everything is pure numpy except the mesh builders (bmesh). No RNG state is shared with the build:
every pattern comes from a hashed integer lattice and a seed, so the high body, the low body and the paint agree.

Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3

_M1 = np.uint64(0x9E3779B97F4A7C15)
_M2 = np.uint64(0xBF58476D1CE4E5B9)
_M3 = np.uint64(0x94D049BB133111EB)


def _mix(h: np.ndarray) -> np.ndarray:
    """splitmix64's finaliser on uint64 arrays (wraps silently)."""
    with np.errstate(over='ignore'):
        h = (h ^ (h >> np.uint64(30))) * _M2
        h = (h ^ (h >> np.uint64(27))) * _M3
        return h ^ (h >> np.uint64(31))


def hash3(i: np.ndarray, seed: int, k: int = 0) -> np.ndarray:
    """0..1 per integer lattice point (n×3 int64), the same for every call with the same seed and channel k."""
    u = i.astype(np.int64).view(np.uint64)
    with np.errstate(over='ignore'):
        h = np.uint64(seed * 7919 + k * 104729 + 1) * _M1
        h = _mix(h ^ u[:, 0])
        h = _mix(h ^ (u[:, 1] * _M1))
        h = _mix(h ^ (u[:, 2] * _M2))
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def hash1(i: np.ndarray, seed: int) -> np.ndarray:
    """0..1 per integer (a seed's own random numbers)."""
    i = np.asarray(i, np.int64)
    return hash3(np.stack([i, np.zeros_like(i), np.zeros_like(i)], axis=1), seed)


def value_noise(p: np.ndarray, freq: float, seed: int) -> np.ndarray:
    """Smooth value noise 0..1 (trilinear on a hashed lattice with a smoothstep fade)."""
    q = p * freq
    i0 = np.floor(q).astype(np.int64)
    f = q - i0
    f = f * f * (3.0 - 2.0 * f)
    out = np.zeros(len(p))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                v = hash3(i0 + np.array([dx, dy, dz], np.int64), seed)
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * v
    return out


def fbm(p: np.ndarray, freq: float, seed: int, octaves: int = 3, gain: float = 0.5) -> np.ndarray:
    """Fractal value noise, centred: about −1..1."""
    out = np.zeros(len(p))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * (value_noise(p, freq * (2.03 ** o), seed + 31 * o) - 0.5) * 2.0
        tot += amp
        amp *= gain
    return out / tot


def voronoi(p: np.ndarray, cell: float, seed: int, jitter: float = 0.85, chunk: int = 400000):
    """F1, F2 (metres) and the id of the nearest feature point (int64), feature points jittered in a cubic lattice of
    `cell` metres. F2 − F1 is small along the cell walls."""
    n = len(p)
    f1 = np.full(n, np.inf)
    f2 = np.full(n, np.inf)
    fid = np.zeros(n, np.int64)
    offs = [np.array([dx, dy, dz], np.int64) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
    for a in range(0, n, chunk):
        q = p[a:a + chunk] / cell
        i0 = np.floor(q).astype(np.int64)
        b1 = np.full(len(q), np.inf)
        b2 = np.full(len(q), np.inf)
        bi = np.zeros(len(q), np.int64)
        for o in offs:
            c = i0 + o
            fp = c + 0.5 + jitter * (np.stack([hash3(c, seed, 0), hash3(c, seed, 1), hash3(c, seed, 2)], axis=1) - 0.5)
            d = np.linalg.norm(q - fp, axis=1)
            cid = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791)
            closer = d < b1
            b2 = np.where(closer, b1, np.minimum(b2, d))
            bi = np.where(closer, cid, bi)
            b1 = np.where(closer, d, b1)
        f1[a:a + chunk] = b1 * cell
        f2[a:a + chunk] = b2 * cell
        fid[a:a + chunk] = bi
    return f1, f2, fid


def facets(p: np.ndarray, cell: float, seed: int, chunk: int = 400000) -> np.ndarray:
    """0..1 chipped facets: inside each Voronoi cell (about `cell` metres) a plane cuts in at a random tilt, so the cut is
    linear across the cell and breaks sharply at its walls (flat chipped faces with crisp edges, not soft dents)."""
    n = len(p)
    out = np.zeros(n)
    offs = [np.array([dx, dy, dz], np.int64) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
    for a in range(0, n, chunk):
        q = p[a:a + chunk] / cell
        i0 = np.floor(q).astype(np.int64)
        best = np.full(len(q), np.inf)
        val = np.zeros(len(q))
        for o in offs:
            c = i0 + o
            fp = c + 0.5 + 0.85 * (np.stack([hash3(c, seed, 0), hash3(c, seed, 1), hash3(c, seed, 2)], axis=1) - 0.5)
            d = np.linalg.norm(q - fp, axis=1)
            g = np.stack([hash3(c, seed, 3), hash3(c, seed, 4), hash3(c, seed, 5)], axis=1) - 0.5
            g = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
            depth = hash3(c, seed, 6) * 1.2 - 0.45                      # some cells cut deep, some not at all
            v = depth + ((q - fp) * g).sum(axis=1) * 0.9
            closer = d < best
            best = np.where(closer, d, best)
            val = np.where(closer, v, val)
        out[a:a + chunk] = np.clip(val, 0.0, 1.0)
    return out


def cracks(p: np.ndarray, cell: float, width: float, seed: int, warp: float = 0.0) -> np.ndarray:
    """0..1 along the walls of a Voronoi pattern (a crack network), `width` metres wide; `warp` bends the walls."""
    q = p
    if warp > 0:
        q = p + warp * np.stack([fbm(p, 1.0 / cell * 1.7, seed + 11 + k, 2) for k in range(3)], axis=1)
    f1, f2, _ = voronoi(q, cell, seed)
    return np.exp(-((f2 - f1) / width) ** 2)


def grain(p: np.ndarray, seed: int = 5) -> np.ndarray:
    """A granite grain, −1..1: pits and bumps of about 4, 8 and 16 mm."""
    return np.clip(0.5 * fbm(p, 1 / 0.004, seed, 1) + 0.35 * fbm(p, 1 / 0.008, seed + 3, 1) + 0.25 * fbm(p, 1 / 0.016, seed + 7, 1), -1, 1)


# ============================================================================= the cracked shell (surface Voronoi)
def nearest_seeds(co: np.ndarray, vn: np.ndarray, sc: np.ndarray, sn: np.ndarray, k: int = 3, compat: float = -0.05,
                  chunk: int = 6000) -> tuple[np.ndarray, np.ndarray]:
    """The k nearest seeds of every vertex (indices and distances, nearest first). A seed whose normal faces away from
    the vertex's (n·n' < compat: the inner side of an arm against the flank) is never a neighbour, so a crack never
    runs across from one limb to the body beside it."""
    n = len(co)
    idx = np.zeros((n, k), np.int64)
    dist = np.full((n, k), np.inf)
    s2 = (sc * sc).sum(1)
    for a in range(0, n, chunk):
        p = co[a:a + chunk]
        d2 = (p * p).sum(1)[:, None] + s2[None, :] - 2.0 * p @ sc.T
        bad = (vn[a:a + chunk] @ sn.T) < compat
        d2 = np.where(bad, np.inf, np.maximum(d2, 0.0))
        part = np.argpartition(d2, k, axis=1)[:, :k]
        pd = np.take_along_axis(d2, part, axis=1)
        o = np.argsort(pd, axis=1)
        idx[a:a + chunk] = np.take_along_axis(part, o, axis=1)
        dist[a:a + chunk] = np.sqrt(np.take_along_axis(pd, o, axis=1))
    return idx, dist


def wall_distance(co: np.ndarray, ca: np.ndarray, cb: np.ndarray) -> np.ndarray:
    """Metres from each point to the bisector plane between its seeds a (nearest) and b: the distance to the crack."""
    ab = cb - ca
    L = np.maximum(np.linalg.norm(ab, axis=1), 1e-6)
    return (((co - cb) ** 2).sum(1) - ((co - ca) ** 2).sum(1)) / (2.0 * L)


def box_sdf(p: np.ndarray, centre, half, rot_deg=(0.0, 0.0, 0.0), mirror: bool = False) -> np.ndarray:
    """Signed distance (metres, < 0 inside) to a box placed like a lib.mesh 'box' Part (scale, then XYZ Euler rotation,
    then the centre; `mirror` = the union with its X-mirrored twin)."""
    from mathutils import Euler
    R = np.array(Euler([math.radians(a) for a in rot_deg], 'XYZ').to_matrix())
    h = v3(half)
    out = np.full(len(p), np.inf)
    for s in ((1, -1) if mirror else (1,)):
        c = v3(centre) * v3((s, 1, 1))
        q = p - c
        if s < 0:
            q = q * v3((-1, 1, 1))
        q = q @ R                       # into the box's frame (R is orthonormal: R^T applied as q @ R)
        d = np.abs(q) - h[None]
        outside = np.linalg.norm(np.maximum(d, 0.0), axis=1)
        inside = np.minimum(d.max(axis=1), 0.0)
        out = np.minimum(out, outside + inside)
    return out


def ell_sdf(p: np.ndarray, centre, radii) -> np.ndarray:
    """An ellipsoid's approximate signed distance (metres; exact on the axes): (|q/r| − 1) · min(r)."""
    r = v3(radii)
    return (np.linalg.norm((p - v3(centre)) / r[None], axis=1) - 1.0) * float(r.min())


# ============================================================================= rounded stone blocks (body extras)
def rounded_block(name: str, centre, half, rot_deg=(0.0, 0.0, 0.0), m=0.42, seg: int = 32, taper: float = 0.0) -> bpy.types.Object:
    """A closed rounded box (a sphere pushed out toward its cube: each unit-sphere component raised to the power m,
    m 1 = an ellipsoid, about 0.4 = a block with soft edges; m may differ per axis), scaled to `half`, its lower half
    narrowed in x by `taper` (0.3 = 30% narrower at the bottom: a shield), rotated (XYZ degrees), moved to `centre`:
    a chiselled finger, toe or brow block, or the face's shield, for the voxel body."""
    from mathutils import Euler, Vector
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    R = Euler([math.radians(a) for a in rot_deg], 'XYZ').to_matrix()
    h = v3(half)
    mm = np.broadcast_to(np.asarray(m, np.float64), (3,))
    c = Vector(tuple(float(x) for x in centre))
    for v in bm.verts:
        q = np.array(v.co[:])
        q = np.sign(q) * np.abs(q) ** mm
        q[0] *= 1.0 - taper * max(0.0, -q[2]) ** 1.5
        v.co = c + R @ Vector(tuple(q * h))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob

