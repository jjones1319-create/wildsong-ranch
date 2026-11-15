"""Pluckrex's shape, shared by the young form (pluckrex_ultra.py) and the grown form (pluckrex_grown_ultra.py).

`Form(G)` turns one form's numbers (a dict of landmarks in metres, measured on that form's 2-turnaround.png) into the
body's rounded parts, the face's frames (eyes, the open grin's hinge), the hands, feet and tail, and the zone tests the
paint, the weights and the pebbles read. The props live in pluckrex_props.py, the paint in pluckrex_paint.py and the
recipe glue in pluckrex_recipe.py.

The grin is modelled open (the hero, 1-hero.png, is the design lock): the lower jaw is a rounded part turned down
`jaw_open` degrees about the hinge, so the voxel body has a real mouth between the snout and the jaw (palate, tongue
and throat painted inside it, the teeth as props on its rims). The plan's jaw bone opens it wider in the smiles and
the strikes.

Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Euler, Matrix, Vector

from lib.mesh import Part
from lib.surface import norm, smooth, v3


def mirror(p, s: int) -> tuple[float, float, float]:
    return (float(p[0]) * s, float(p[1]), float(p[2]))


def unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def basis_euler(xax, zax) -> tuple[float, float, float]:
    """XYZ Euler degrees turning a part's +X onto `xax` and (as near as it can) its +Z onto `zax`."""
    x = Vector(xax).normalized()
    z = Vector(zax)
    z = (z - x * z.dot(x)).normalized()
    y = z.cross(x)
    e = Matrix((x, y, z)).transposed().to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def rot_x(p, centre, deg: float) -> np.ndarray:
    """Points turned `deg` degrees about the X axis through `centre` (+ = the front, -Y, goes down)."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    q = v3(p).reshape(-1, 3) - v3(centre)
    y = q[:, 1] * c - q[:, 2] * s
    z = q[:, 1] * s + q[:, 2] * c
    return np.stack([q[:, 0], y, z], axis=1) + v3(centre)


def _ell(name: str, e, mirror_: bool = False, rot=None) -> Part:
    """An ellipsoid part from (centre, radii[, (rx, ry, rz) degrees])."""
    if rot is None:
        rot = tuple(e[2]) if len(e) > 2 else (0.0, 0.0, 0.0)
    return Part(name, 'sphere', loc=tuple(map(float, e[0])), radius=1.0, scale=tuple(map(float, e[1])), rot=tuple(rot),
                mirror=mirror_)


def _sd_ell(q: np.ndarray, c, r, rot=None) -> np.ndarray:
    q = q - v3(c)
    if rot is not None:
        q = q @ rot
    rr = v3(r)
    k = np.linalg.norm(q / rr, axis=1)
    return (k - 1.0) * float(rr.min())


def _sd_tube(p: np.ndarray, a, b, r1: float, r2: float) -> np.ndarray:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1) - (r1 + (r2 - r1) * t)


def sd_parts(p: np.ndarray, parts: list[Part]) -> np.ndarray:
    """The approximate signed distance (metres, negative inside) to the union of the parts (the mirrored twin by
    mirroring the point)."""
    p = v3(p).reshape(-1, 3)
    d = np.full(len(p), 9.0)
    for pt in parts:
        rot = None
        if pt.kind == 'sphere' and any(abs(a) > 1e-9 for a in pt.rot):
            rot = np.array(Euler([math.radians(a) for a in pt.rot], 'XYZ').to_matrix())
        for side in ((1, -1) if pt.mirror else (1,)):
            q = p if side > 0 else p * v3((-1.0, 1.0, 1.0))
            if pt.kind == 'sphere':
                d = np.minimum(d, _sd_ell(q, pt.loc, tuple(pt.radius * s_ for s_ in pt.scale), rot))
            elif pt.kind in ('capsule', 'tube'):
                r2 = pt.r2 if (pt.kind == 'tube' and pt.r2 is not None) else pt.radius
                d = np.minimum(d, _sd_tube(q, pt.loc, pt.to, pt.radius, r2))
    return d


def seg_dist(p: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / float(ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t


def polyline_param(p: np.ndarray, pts, rad) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(t 0..1 along the polyline by length, the distance to it, its radius there)."""
    pts = np.asarray(pts, np.float64)
    rad = np.asarray(rad, np.float64)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    best_d = np.full(len(p), 9.0)
    best_t = np.zeros(len(p))
    best_r = np.zeros(len(p))
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        u = np.clip(((p - a) @ ab) / float(ab @ ab), 0, 1)
        d = np.linalg.norm(p - (a + u[:, None] * ab), axis=1)
        better = d < best_d
        best_d = np.where(better, d, best_d)
        best_t = np.where(better, cum[i] + u * (cum[i + 1] - cum[i]), best_t)
        best_r = np.where(better, rad[i] + u * (rad[i + 1] - rad[i]), best_r)
    return best_t, best_d, best_r


def curve_at(pts, t: float) -> tuple[np.ndarray, np.ndarray]:
    """(the point at length share t along the polyline, its unit direction)."""
    pts = np.asarray(pts, np.float64)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    i = min(int(np.searchsorted(cum, t, side='right') - 1), len(seg) - 1)
    i = max(i, 0)
    f = (t - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    return pts[i] * (1 - f) + pts[i + 1] * f, unit(pts[i + 1] - pts[i])


def interp_radius(rad, t: float) -> float:
    rad = list(rad)
    x = t * (len(rad) - 1)
    i = min(int(x), len(rad) - 2)
    return float(rad[i] + (rad[i + 1] - rad[i]) * (x - i))
