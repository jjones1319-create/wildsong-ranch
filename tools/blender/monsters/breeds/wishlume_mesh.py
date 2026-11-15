"""Mesh builders for Wishlume's props (wishlume_props.py): bundles of tubes with their own unwrap, and lathe solids.

A bundle is one object holding many tubes (the ribs, the tassel's threads): rotation-minimising frames along each
centre line, an optional elliptic cross-section, rounded end caps, and an own unwrap (`own_uv`): each tube one strip
(u round it, v along it, in metres; the seam mended per face) and each cap one disc, so the packer keeps whole
strips instead of smart-projecting thin tubes into slivers. Per-point attributes for the paint and the weights:
part (an id), pt (0 at the start .. 1 at the end), pa (0..1 round the tube), pr (a random number per tube), plen (the
tube's length in metres). A FACE attribute texel_k sets each part's share of the atlas.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S


def frames(P: np.ndarray, hint=None, closed: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tangents, normals and binormals along a polyline (rotation-minimising; the first normal from `hint`)."""
    k = len(P)
    T = np.zeros_like(P)
    if closed:
        T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    else:
        T[1:-1] = P[2:] - P[:-2]
        T[0] = P[1] - P[0]
        T[-1] = P[-1] - P[-2]
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    h = np.array(hint if hint is not None else (0.0, 0.0, 1.0), np.float64)
    if abs(float(h @ T[0])) > 0.95:
        h = np.array((1.0, 0.0, 0.0)) if abs(T[0, 0]) < 0.9 else np.array((0.0, 1.0, 0.0))
    N = np.zeros_like(P)
    n = h - T[0] * float(h @ T[0])
    N[0] = n / np.linalg.norm(n)
    for i in range(1, k):
        n = N[i - 1] - T[i] * float(N[i - 1] @ T[i])
        N[i] = n / max(np.linalg.norm(n), 1e-12)
    B = np.cross(T, N)
    return T, N, B


class Bundle:
    """Accumulates tubes, then makes one object (Bundle.object)."""

    def __init__(self):
        self.verts: list[np.ndarray] = []
        self.faces: list[tuple] = []
        self.uvs: list[list[tuple[float, float]]] = []
        self.kface: list[float] = []
        self.attrs: dict[str, list[np.ndarray]] = {k: [] for k in ('part', 'pt', 'pa', 'pr', 'plen')}
        self.n = 0
        self.cursor = 0.0           # where the next tube's strip goes in the initial layout (the packer moves them)

    def _add_verts(self, v: np.ndarray, part: float, pt: np.ndarray, pa: np.ndarray, pr: float, plen: float) -> int:
        base = self.n
        self.verts.append(v)
        self.n += len(v)
        self.attrs['part'].append(np.full(len(v), part))
        self.attrs['pt'].append(pt)
        self.attrs['pa'].append(pa)
        self.attrs['pr'].append(np.full(len(v), pr))
        self.attrs['plen'].append(np.full(len(v), plen))
        return base

    def tube(self, P, radius, sides: int, part: float, pr: float = 0.5, closed: bool = False, hint=None, aspect: float = 1.0,
             caps: tuple[bool, bool] = (False, False), relief=None, texel_k: float = 1.0) -> None:
        """One tube along P (k x 3) with radius (a number or k values); relief(pa, s) -> metres added to the radius."""
        P = np.asarray(P, np.float64)
        k = len(P)
        r = np.broadcast_to(np.asarray(radius, np.float64), (k,)).copy()
        T, N, B = frames(P, hint, closed)
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        s = np.concatenate([[0.0], np.cumsum(seg)])
        L = float(s[-1] + (np.linalg.norm(P[0] - P[-1]) if closed else 0.0))
        a = np.arange(sides) / sides
        ang = a * 2 * np.pi
        rr = r[:, None] + (relief(a[None, :], s[:, None]) if relief is not None else 0.0)
        v = (P[:, None, :] + rr[..., None] * (np.cos(ang)[None, :, None] * N[:, None, :]
                                              + aspect * np.sin(ang)[None, :, None] * B[:, None, :]))
        pt = np.repeat(s / max(L, 1e-9), sides)
        pa = np.tile(a, k)
        base = self._add_verts(v.reshape(-1, 3), part, pt, pa, pr, L)
        circ = 2 * np.pi * float(np.mean(r)) * (1 + aspect) / 2
        u0 = self.cursor
        rows = k if closed else k - 1
        for i in range(rows):
            i2 = (i + 1) % k
            for j in range(sides):
                j2 = (j + 1) % sides
                self.faces.append((base + i * sides + j, base + i * sides + j2, base + i2 * sides + j2, base + i2 * sides + j))
                vv = s[i + 1] if i + 1 < k else L
                self.uvs.append([(u0 + circ * j / sides, s[i]), (u0 + circ * (j + 1) / sides, s[i]),
                                 (u0 + circ * (j + 1) / sides, vv), (u0 + circ * j / sides, vv)])
                self.kface.append(texel_k)
        self.cursor += circ + 0.01
        for end, on in ((0, caps[0]), (k - 1, caps[1])):
            if not on:
                continue
            sgn = -1.0 if end == 0 else 1.0
            c = P[end] + T[end] * sgn * r[end] * 0.55
            ci = self._add_verts(c[None], part, np.array([0.0 if end == 0 else 1.0]), np.array([0.0]), pr, L)
            cu = self.cursor + r[end]
            for j in range(sides):
                j2 = (j + 1) % sides
                a1, a2 = base + end * sides + j, base + end * sides + j2
                tri = (a1, a2, ci) if end else (a2, a1, ci)
                uvj = (cu + r[end] * math.cos(ang[j]), r[end] + r[end] * math.sin(ang[j]))
                uvj2 = (cu + r[end] * math.cos(ang[j2]), r[end] + r[end] * math.sin(ang[j2]))
                self.faces.append(tri)
                self.uvs.append([uvj, uvj2, (cu, r[end])] if end else [uvj2, uvj, (cu, r[end])])
                self.kface.append(texel_k)
            self.cursor += 2.2 * r[end] + 0.01

    def lathe(self, prof, centre, sides: int, part: float, axis=(0.0, 0.0, 1.0), ref=(1.0, 0.0, 0.0), pr: float = 0.5,
              texel_k: float = 1.0) -> None:
        """A solid of revolution: prof = [(r, h), ...] from the bottom (r 0 = on the axis) outward, up and back in."""
        ax = np.asarray(axis, np.float64)
        ax /= np.linalg.norm(ax)
        e1 = np.asarray(ref, np.float64) - ax * float(np.asarray(ref) @ ax)
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(ax, e1)
        cen = np.asarray(centre, np.float64)
        ang = np.arange(sides) / sides * 2 * np.pi
        rings = []
        arc = np.concatenate([[0.0], np.cumsum([math.hypot(prof[i + 1][0] - prof[i][0], prof[i + 1][1] - prof[i][1]) for i in range(len(prof) - 1)])])
        for (r, h), sa in zip(prof, arc):
            if r <= 1e-7:
                p = cen + ax * h
                rings.append(('pole', self._add_verts(p[None], part, np.array([sa / arc[-1]]), np.array([0.0]), pr, float(arc[-1]))))
            else:
                v = cen + ax * h + r * (np.cos(ang)[:, None] * e1 + np.sin(ang)[:, None] * e2)
                rings.append(('ring', self._add_verts(v, part, np.full(sides, sa / arc[-1]), np.arange(sides) / sides, pr, float(arc[-1]))))
        for (ka, ba), (kb, bb) in zip(rings[:-1], rings[1:]):
            for j in range(sides):
                j2 = (j + 1) % sides
                if ka == 'pole' and kb == 'ring':
                    self.faces.append((ba, bb + j2, bb + j))
                elif ka == 'ring' and kb == 'pole':
                    self.faces.append((ba + j, ba + j2, bb))
                elif ka == 'ring':
                    self.faces.append((ba + j, ba + j2, bb + j2, bb + j))
                else:
                    continue
                self.uvs.append(None)
                self.kface.append(texel_k)

    def object(self, name: str, own_uv: bool = True) -> bpy.types.Object:
        verts = np.concatenate(self.verts)
        ob = S.sheet_object(name, verts, self.faces)
        for k, vals in self.attrs.items():
            S.add_attr(ob, k, np.concatenate(vals))
        me = ob.data
        a = me.attributes.new('texel_k', 'FLOAT', 'FACE')
        a.data.foreach_set('value', np.asarray(self.kface, np.float32))
        if own_uv and all(u is not None for u in self.uvs):
            lay = me.uv_layers.new(name='UVMap')
            flat = [c for f in self.uvs for c in f]
            lay.data.foreach_set('uv', np.asarray(flat, np.float32).ravel())
            ob['own_uv'] = True
        C.log(f'{name}: {len(me.polygons)} faces, {len(verts)} verts')
        return ob


def torus_path(centre, normal, ref, R: float, n: int, ry: float | None = None) -> np.ndarray:
    """n points round a circle (or an ellipse, half axes R along ref and ry across) in the plane of `normal`."""
    nn = np.asarray(normal, np.float64)
    nn /= np.linalg.norm(nn)
    e1 = np.asarray(ref, np.float64) - nn * float(np.asarray(ref) @ nn)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nn, e1)
    t = np.arange(n) / n * 2 * np.pi
    return np.asarray(centre, np.float64) + R * np.cos(t)[:, None] * e1 + (ry if ry is not None else R) * np.sin(t)[:, None] * e2
