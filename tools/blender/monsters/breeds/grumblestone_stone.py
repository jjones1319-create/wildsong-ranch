"""Grumblestone's stone kit (Art 2.1 Ultra; chatgpt/monsters/11-grumblestone): deterministic noise on numpy arrays,
the cracked-shell plates (a Voronoi of seeds laid on the body's own surface: flat chiselled faces, bevelled edges and
narrow cracks between them) and the faceted crystals (rigid props: prisms with a pointed tip, and the gems set in the
knuckles).

The noise functions (hash3 … grain) are a copy of Cobblemaw's kit (cobblemaw_stone.py), kept here so the two breeds
never change each other. Everything is pure numpy except the mesh builders (bmesh). No RNG state is shared with the
build: every pattern comes from a hashed integer lattice and a seed, so the high body, the low body and the paint agree.

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


# ============================================================================= crystals (rigid props)
def _orthonormal(d: np.ndarray, roll: float) -> tuple[np.ndarray, np.ndarray]:
    a = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(d, a)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    c, s = math.cos(roll), math.sin(roll)
    return e1 * c + e2 * s, -e1 * s + e2 * c


def crystal_rings(base, axis, length: float, radius: float, sides: int, seed: int, tip: float = 0.32, bury: float = 0.5,
                  taper: float = 0.85, kind: str = 'prism', aspect: float = 1.0) -> list[np.ndarray]:
    """The vertex rings of one crystal, base (buried) to tip: an irregular hexagonal prism with a pointed pyramid
    (`kind` 'prism'), or a low faceted gem set in a socket (`kind` 'gem': a girdle, a sloped crown and a flat table,
    `aspect` times taller than wide)."""
    rng = np.random.default_rng(seed)
    d = v3(axis) / np.linalg.norm(axis)
    if kind == 'gem':
        up = v3((0.0, 0.0, 1.0)) - d * d[2]
        up = up / max(np.linalg.norm(up), 1e-9)
        e1, e2 = np.cross(up, d), up
    else:
        e1, e2 = _orthonormal(d, rng.uniform(0, 2 * math.pi))
    b = v3(base)
    ang = np.linspace(0, 2 * math.pi, sides, endpoint=False) + rng.uniform(-0.18, 0.18, sides)
    rad = radius * rng.uniform(0.82, 1.14, sides)
    asp = aspect if kind == 'gem' else 1.0
    ring = lambda centre, k: [centre + (e1 * math.cos(a) + e2 * math.sin(a) * asp) * r * k for a, r in zip(ang, rad)]  # noqa: E731
    if kind == 'gem':
        # a set gem: the girdle sunk in the stone, a sloped crown rising to a flat (slightly tilted) table
        lo = ring(b - d * length * bury, 0.92)
        gird = ring(b + d * length * 0.15, 1.0)
        crown = ring(b + d * length * 0.6, 0.8)
        tilt = (e1 * rng.uniform(-1, 1) + e2 * rng.uniform(-1, 1)) * 0.06 * radius
        table = [p + d * length * 0.3 + tilt for p in ring(b + d * length * 0.6, 0.5)]
        return [np.array(lo), np.array(gird), np.array(crown), np.array(table)]
    lo = ring(b - d * length * bury, taper)
    shoulder = ring(b + d * length * (1.0 - tip), 1.0)
    off = (e1 * rng.uniform(-1, 1) + e2 * rng.uniform(-1, 1)) * 0.18 * radius
    apex = b + d * length + off
    return [np.array(lo), np.array(shoulder), np.array([apex])]


def crystals_object(name: str, specs: list[dict]) -> bpy.types.Object:
    """One mesh of faceted crystals, every face with its own vertices (flat facets, a colour per facet). Attributes:
    `xtal` = (t along 0 base … 1 tip, facet shade −1..1, kind 0 prism / 1 gem), `anchor` = the crystal's base on the
    body (its skin weights come from there), `xid` = the crystal's index."""
    verts, faces, t_along, shade, kind, anchor, xid = [], [], [], [], [], [], []
    for i, sp in enumerate(specs):
        rings = crystal_rings(sp['base'], sp['axis'], sp['length'], sp['radius'], sp.get('sides', 6), sp['seed'],
                              tip=sp.get('tip', 0.32), bury=sp.get('bury', 0.5), kind=sp.get('kind', 'prism'),
                              aspect=sp.get('aspect', 1.0))
        rng = np.random.default_rng(sp['seed'] + 7)
        nring = len(rings)
        ts = np.linspace(0.0, 1.0, nring)
        ksh = 1.0 if sp.get('kind') == 'gem' else 0.0

        def add_face(pts, tvals):
            base_i = len(verts)
            fs = rng.uniform(-1, 1)
            for p, tv in zip(pts, tvals):
                verts.append(p)
                t_along.append(tv)
                shade.append(fs)
                kind.append(ksh)
                anchor.append(v3(sp['anchor']))
                xid.append(float(i))
            faces.append(tuple(range(base_i, base_i + len(pts))))
        for r in range(nring - 1):
            A, B = rings[r], rings[r + 1]
            m = len(A)
            for j in range(m):
                jn = (j + 1) % m
                if len(B) == 1:
                    add_face([A[j], A[jn], B[0]], [ts[r], ts[r], ts[r + 1]])
                else:
                    add_face([A[j], A[jn], B[jn], B[j]], [ts[r], ts[r], ts[r + 1], ts[r + 1]])
        last = rings[-1]
        if len(last) > 2:            # the gem's flat table
            add_face(list(last), [1.0] * len(last))
        if sp.get('cap', False):     # the buried base (only for crystals that can show it)
            add_face(list(rings[0])[::-1], [0.0] * len(rings[0]))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    n = len(verts)
    S.add_attr(ob, 'xtal', np.stack([np.array(t_along), np.array(shade), np.array(kind)], axis=1))
    S.add_attr(ob, 'anchor', np.array(anchor).reshape(n, 3))
    S.add_attr(ob, 'xid', np.array(xid))
    # every facet outward: away from its crystal's own axis line
    axes = [(v3(sp['base']), v3(sp['axis']) / np.linalg.norm(sp['axis'])) for sp in specs]

    def inside(c: np.ndarray) -> np.ndarray:
        # the nearest crystal's axis point for each face centre
        best = np.full(len(c), np.inf)
        pts = np.zeros_like(c)
        for b, d in axes:
            t = np.clip((c - b) @ d, -1.0, 2.0)
            p = b[None] + t[:, None] * d[None]
            dd = np.linalg.norm(c - p, axis=1)
            closer = dd < best
            best = np.where(closer, dd, best)
            pts = np.where(closer[:, None], p, pts)
        return pts
    S.orient_away(ob, inside)
    for p in me.polygons:
        p.use_smooth = False
    return ob


def tilt(d: np.ndarray, amount: float, rng: np.random.Generator) -> np.ndarray:
    """A unit direction tilted at random by up to `amount` (as a share of the length) from `d`."""
    v = v3(d) / np.linalg.norm(d) + rng.normal(0, 1, 3) * amount
    return v / np.linalg.norm(v)


def cluster(base, normal, count: int, length: tuple[float, float], spread: float, seed: int, up: float = 0.35,
            lean=(0.0, 0.0, 0.0), radius_k: float = 0.24, jitter: float = 0.05, anchor=None) -> list[dict]:
    """A geode cluster: `count` crystals from one spot on the body, the longest near the middle, fanning out by
    `spread`; `up` pulls them toward the sky, `lean` toward a direction (e.g. outward over the shoulder)."""
    rng = np.random.default_rng(seed)
    nrm = v3(normal) / np.linalg.norm(normal)
    main = nrm + up * v3((0, 0, 1)) + v3(lean)
    main /= np.linalg.norm(main)
    e1, e2 = _orthonormal(nrm, 0.0)
    out = []
    for i in range(count):
        k = i / max(1, count - 1)
        L = length[1] - (length[1] - length[0]) * (k ** 0.8) * rng.uniform(0.75, 1.0)
        ang = rng.uniform(0, 2 * math.pi)
        rr = jitter * math.sqrt(k + 0.05) * rng.uniform(0.6, 1.0)
        b = v3(base) + (e1 * math.cos(ang) + e2 * math.sin(ang)) * rr
        ax = main + (e1 * math.cos(ang) + e2 * math.sin(ang)) * spread * (0.3 + k) + rng.normal(0, 1, 3) * 0.08
        ax /= np.linalg.norm(ax)
        out.append({'base': b, 'axis': ax, 'length': L, 'radius': L * radius_k * rng.uniform(0.85, 1.15), 'seed': seed * 31 + i,
                    'anchor': v3(anchor if anchor is not None else base), 'bury': 0.35})
    return out


def surface_point(co: np.ndarray, vn: np.ndarray, p) -> tuple[np.ndarray, np.ndarray]:
    """The body vertex nearest `p` and its normal (to seat a crystal on the carved surface)."""
    i = int(np.argmin(((co - v3(p)) ** 2).sum(1)))
    return co[i].copy(), vn[i].copy()


def crack_spots(co: np.ndarray, dw: np.ndarray, dj: np.ndarray, ok: np.ndarray, spacing: float, w: np.ndarray,
                seed: int, limit: int) -> np.ndarray:
    """Vertex indices at crack junctions (where three plates meet: near the wall to the 2nd and the 3rd seed), thinned
    to a Poisson set `spacing` apart, at most `limit` (the small crystals that grow in the cracks)."""
    cand = np.nonzero(ok & (dw < 1.2 * w) & (dj < 3.0 * w + 0.01))[0]
    if len(cand) == 0:
        return cand
    rng = np.random.default_rng(seed)
    order = cand[rng.permutation(len(cand))]
    keep: list[int] = []
    pts = []
    for i in order:
        p = co[i]
        if pts and np.min(((np.array(pts) - p) ** 2).sum(1)) < spacing * spacing:
            continue
        keep.append(int(i))
        pts.append(p)
        if len(keep) >= limit:
            break
    return np.array(keep, np.int64)


def smooth01(a, b, x):
    return smooth(a, b, x)
