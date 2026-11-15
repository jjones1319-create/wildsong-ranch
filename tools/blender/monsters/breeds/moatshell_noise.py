"""Moatshell's noise kit (Art 2.1 Ultra; chatgpt/monsters/19-moatshell): deterministic noise on numpy arrays, a copy
of Grumblestone's and Cobblemaw's kits (grumblestone_stone.py), kept here so the breeds never change each other.
Pure numpy: every pattern comes from a hashed integer lattice and a seed, so the high and the low meshes and the paint
agree. Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

_M1 = np.uint64(0x9E3779B97F4A7C15)
_M2 = np.uint64(0xBF58476D1CE4E5B9)
_M3 = np.uint64(0x94D049BB133111EB)


def smooth(a: float, b: float, x):
    """Smoothstep from a to b (either order), clamped."""
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def v3(a) -> np.ndarray:
    return np.asarray(a, np.float64)


def _mix(h: np.ndarray) -> np.ndarray:
    with np.errstate(over='ignore'):
        h = (h ^ (h >> np.uint64(30))) * _M2
        h = (h ^ (h >> np.uint64(27))) * _M3
        return h ^ (h >> np.uint64(31))


def hash3(i: np.ndarray, seed: int, k: int = 0) -> np.ndarray:
    """0..1 per integer lattice point (n×3 int64)."""
    u = np.ascontiguousarray(i.astype(np.int64)).view(np.uint64)
    with np.errstate(over='ignore'):
        h = np.uint64(seed * 7919 + k * 104729 + 1) * _M1
        h = _mix(h ^ u[:, 0])
        h = _mix(h ^ (u[:, 1] * _M1))
        h = _mix(h ^ (u[:, 2] * _M2))
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def hash1(i, seed: int) -> np.ndarray:
    """0..1 per integer (a seed's own random numbers)."""
    i = np.atleast_1d(np.asarray(i, np.int64))
    return hash3(np.stack([i, np.zeros_like(i), np.zeros_like(i)], axis=1), seed)


def value_noise(p: np.ndarray, freq: float, seed: int) -> np.ndarray:
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
    """F1, F2 (in units of p) and the id of the nearest feature point, feature points jittered in a cubic lattice of
    `cell`. F2 − F1 is small along the cell walls."""
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
    """0..1 chipped facets: inside each Voronoi cell a plane cuts in at a random tilt (flat chips with crisp edges)."""
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
            depth = hash3(c, seed, 6) * 1.2 - 0.45
            v = depth + ((q - fp) * g).sum(axis=1) * 0.9
            closer = d < best
            best = np.where(closer, d, best)
            val = np.where(closer, v, val)
        out[a:a + chunk] = np.clip(val, 0.0, 1.0)
    return out


def grain(p: np.ndarray, seed: int = 5) -> np.ndarray:
    """A stone grain, −1..1: pits and bumps of about 4, 8 and 16 mm."""
    return np.clip(0.5 * fbm(p, 1 / 0.004, seed, 1) + 0.35 * fbm(p, 1 / 0.008, seed + 3, 1) + 0.25 * fbm(p, 1 / 0.016, seed + 7, 1), -1, 1)


def seg_dist(p: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    """Distance from each point to the segment a–b, and the parameter 0..1 along it."""
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def poly_dist(p: np.ndarray, pts) -> np.ndarray:
    d = np.full(len(p), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        d = np.minimum(d, seg_dist(p, a, b)[0])
    return d


def ell_sdf(p: np.ndarray, centre, radii) -> np.ndarray:
    """An ellipsoid's approximate signed distance (metres; exact on the axes)."""
    r = v3(radii)
    return (np.linalg.norm((p - v3(centre)) / r[None], axis=1) - 1.0) * float(r.min())


def rot_z(deg: float) -> np.ndarray:
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
