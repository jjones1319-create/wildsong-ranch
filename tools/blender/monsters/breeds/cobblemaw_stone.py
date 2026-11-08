"""Cobblemaw's stone kit (Art 2.1 Ultra; chatgpt/monsters/03-cobblemaw): deterministic noise and Voronoi on numpy
arrays, the hide's grain and cracks, and the two tusks (rigid props with their own UVs).

Everything here is pure numpy except `build_tusk` (bmesh). No RNG state is shared with the build: every pattern comes
from a hashed integer lattice and a seed, so the high body, the low body and the paint agree.

Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import norm, smooth, v3

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
    u = i.astype(np.int64).view(np.uint64) if i.dtype == np.int64 else i.astype(np.int64).view(np.uint64)
    with np.errstate(over='ignore'):
        h = np.uint64(seed * 7919 + k * 104729 + 1) * _M1
        h = _mix(h ^ u[:, 0])
        h = _mix(h ^ (u[:, 1] * _M1))
        h = _mix(h ^ (u[:, 2] * _M2))
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


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
    `cell` metres. F2 − F1 is small along the cell walls (cracks)."""
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
    """The weathered-rock grain of the hide, −1..1: pits and bumps of about 4, 8 and 16 mm."""
    return np.clip(0.5 * fbm(p, 1 / 0.004, seed, 1) + 0.35 * fbm(p, 1 / 0.008, seed + 3, 1) + 0.25 * fbm(p, 1 / 0.016, seed + 7, 1), -1, 1)


# ----------------------------------------------------------------------------- the tusks (rigid props)
def tusk_path(base: np.ndarray, tip: np.ndarray, bend: np.ndarray, t: np.ndarray) -> np.ndarray:
    """A gently curved centre line from the root to the tip (a quadratic bend toward `bend`)."""
    t = np.asarray(t, float)[:, None]
    mid = (base + tip) * 0.5 + bend
    return (1 - t) ** 2 * base[None] + 2 * (1 - t) * t * mid[None] + t ** 2 * tip[None]


def build_tusk(name: str, s: int, spec: dict, high: bool) -> bpy.types.Object:
    """One short stubby tusk: an oval cone along a curved centre line from below the lip (buried) to a blunt round tip;
    `tusk` attribute = (t along, growth ring, the front side), `tusk_side` = s; its own unwrap (one strip)."""
    base = v3(spec['base']) * v3((s, 1, 1))
    tip = v3(spec['tip']) * v3((s, 1, 1))
    bend = v3(spec['bend']) * v3((s, 1, 1))
    nr, ns = (90, 40) if high else (14, 14)
    t = np.linspace(0.0, 1.0, nr)
    P = tusk_path(base, tip, bend, t)
    T = norm(np.gradient(P, axis=0))
    ref = v3((s * 1.0, 0.0, 0.0))
    e1 = norm(ref[None] - T * (T @ ref)[:, None])          # across (outward)
    e2 = np.cross(T, e1)                                      # front / back
    r0, r1 = spec['r']
    # a stubby cone: full at the root, rounding off into a blunt tip
    r = r0 + (r1 - r0) * t ** 1.4
    ring = np.zeros(nr)
    if high and spec.get('rings', True):
        # faint growth rings near the root and a fine lengthwise grain (baked into the normal map)
        g = t * 7.0
        ring = np.exp(-((g - np.round(g)) / 0.12) ** 2) * smooth(0.05, 0.15, t) * smooth(0.8, 0.5, t)
    a = np.linspace(0.0, 2 * math.pi, ns, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    rr = np.tile(r[:, None] * (1.0 - 0.025 * ring[:, None]), (1, ns))
    if high:
        rr = rr * (1.0 + 0.006 * np.sin(a * 9.0 + 1.3)[None] + 0.004 * np.sin(a * 17.0)[None])
    flat = spec.get('flat', 0.85)                             # oval: thinner front to back
    pts = P[:, None, :] + e1[:, None, :] * (rr * ca[None])[..., None] + e2[:, None, :] * (rr * sa[None] * flat)[..., None]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    circ = 2 * math.pi * float(np.median(r)) * (0.5 * (1 + flat))

    def put(face, coords):
        for lp, (uu, vv) in zip(face.loops, coords):
            lp[uvl].uv = (uu * circ, vv)
    verts = [[bm.verts.new(tuple(pts[i, j])) for j in range(ns)] for i in range(nr)]
    for i in range(nr - 1):
        for j in range(ns):
            jn = (j + 1) % ns
            f = bm.faces.new((verts[i][j], verts[i][jn], verts[i + 1][jn], verts[i + 1][j]))
            put(f, [(j / ns, arc[i]), ((j + 1) / ns, arc[i]), ((j + 1) / ns, arc[i + 1]), (j / ns, arc[i + 1])])
    # the blunt tip: a rounded cap
    capn = 7 if high else 3
    rings = [verts[-1]]
    for k in range(1, capn + 1):
        f = k / (capn + 0.4)
        rk = rr[-1] * math.sqrt(max(0.0, 1.0 - f * f))
        c = P[-1] + T[-1] * r[-1] * 0.95 * f
        rings.append([bm.verts.new(tuple(c + e1[-1] * rk[j] * ca[j] + e2[-1] * rk[j] * sa[j] * flat)) for j in range(ns)])
    step = float(r[-1]) * 0.95 / (capn + 0.4)
    for k in range(capn):
        for j in range(ns):
            jn = (j + 1) % ns
            f = bm.faces.new((rings[k][j], rings[k][jn], rings[k + 1][jn], rings[k + 1][j]))
            v0, v1 = arc[-1] + step * k, arc[-1] + step * (k + 1)
            put(f, [(j / ns, v0), ((j + 1) / ns, v0), ((j + 1) / ns, v1), (j / ns, v1)])
    end = bm.verts.new(tuple(P[-1] + T[-1] * r[-1] * 0.98))
    for j in range(ns):
        f = bm.faces.new((rings[-1][j], rings[-1][(j + 1) % ns], end))
        put(f, [(j / ns, arc[-1] + step * capn), ((j + 1) / ns, arc[-1] + step * capn), ((j + 0.5) / ns, arc[-1] + step * (capn + 0.4))])
    root = bm.verts.new(tuple(P[0] - T[0] * r[0] * 0.3))
    for j in range(ns):
        f = bm.faces.new((verts[0][(j + 1) % ns], verts[0][j], root))
        put(f, [((j + 1) / ns, 0.0), (j / ns, 0.0), ((j + 0.5) / ns, -float(r[0]) * 0.3)])
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    tt = np.concatenate([np.repeat(t, ns), np.full(capn * ns, 1.0), [1.0], [0.0]])
    rg = np.concatenate([np.repeat(ring, ns), np.zeros(capn * ns), [0.0], [0.0]])
    fr = np.concatenate([np.tile(np.clip(-sa, 0, 1), nr), np.tile(np.clip(-sa, 0, 1), capn), [0.5], [0.5]])
    S.add_attr(ob, 'tusk', np.stack([tt, rg, fr], axis=1))
    S.add_attr(ob, 'tusk_side', np.full(len(tt), float(s)))
    ob['own_uv'] = True
    # every face outward (away from the centre line)
    flipped = S.orient_away(ob, lambda c: tusk_path(base, tip, bend, np.clip(_nearest_t(c, base, tip, bend), 0, 1)))
    C.log(f'{name}: {len(me.polygons)} faces ({flipped} flipped outward)')
    return ob


def _nearest_t(c: np.ndarray, base, tip, bend) -> np.ndarray:
    """The centre line's parameter nearest each point (sampled)."""
    ts = np.linspace(-0.1, 1.1, 121)
    P = tusk_path(base, tip, bend, ts)
    d = np.linalg.norm(c[:, None, :] - P[None], axis=2)
    return ts[np.argmin(d, axis=1)]


def tusk_paint(ob: bpy.types.Object, ivory: str, root_hex: str, tip_hex: str, ring_hex: str) -> tuple[np.ndarray, np.ndarray]:
    """(linear RGB, rough) per vertex: warm ivory, a deeper cream at the root (where it leaves the lip), paler toward the
    tip, faint darker growth rings; satin with a light clear coat."""
    a = S.attr_array(ob, 'tusk').astype(np.float64)
    t, ring, front = a[:, 0], a[:, 1], a[:, 2]
    lin = lambda h: v3(C.lin_rgb(h))  # noqa: E731
    rgb = np.tile(lin(ivory), (len(t), 1))
    rk = (smooth(0.35, 0.0, t) * 0.7)[:, None]
    rgb = rgb * (1 - rk) + lin(root_hex)[None] * rk
    tk = (smooth(0.6, 1.0, t) * 0.45)[:, None]
    rgb = rgb * (1 - tk) + lin(tip_hex)[None] * tk
    gk = (ring * 0.35)[:, None]
    rgb = rgb * (1 - gk) + lin(ring_hex)[None] * gk
    rough = 0.34 + 0.08 * ring + 0.06 * (1 - front)
    rc = np.stack([np.ones(len(t)), rough, np.full(len(t), 0.45)], axis=1)
    return rgb, rc
