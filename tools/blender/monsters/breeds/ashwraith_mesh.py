"""Mesh builders for Ashwraith (ashwraith_body.py, ashwraith_props.py): a collector of parts with their own unwrap.

`Kit` accumulates parts, then makes one object:
- `tube(P, radius, ...)`: a tube or a flattened ribbon along a centre line (rotation-minimising frames, an elliptic
  cross-section, rounded caps), unrolled as one strip (u round it, v along it, in metres);
- `shell(G, thick, ...)`: a thick cloth sheet from a grid of middle-surface points (nv+1 x nu+1 x 3): outer and inner
  faces (each one island, u and v in metres) and the walls round its border;
- `closed(rings, ...)`: a closed surface from rings of points (a lathe-like body), no unwrap.
Per-point attributes for the paint and the weights: part (an id), pt (0 at the start .. 1 at the end), pa (0..1 round a
tube, or across a sheet), pr (a random number per part), side (+1 outer face, -1 inner face, 0 walls). A FACE attribute
texel_k sets each part's share of the atlas. Nothing tapers to zero area (zero-area faces give NaN normals).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S

ATTRS = ('part', 'pt', 'pa', 'pr', 'side')


def frames(P: np.ndarray, hint=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tangents, normals and binormals along a polyline (rotation-minimising; the first normal from `hint`)."""
    k = len(P)
    T = np.zeros_like(P)
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
    return T, N, np.cross(T, N)


def resample(P: np.ndarray, n: int) -> np.ndarray:
    """n points evenly spaced along a polyline."""
    P = np.asarray(P, np.float64)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    t = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(t, s, P[:, i]) for i in range(3)], axis=1)


def catmull(pts, n: int) -> np.ndarray:
    """A smooth curve through the points (centripetal-free uniform Catmull-Rom), n evenly spaced samples."""
    P = np.asarray(pts, np.float64)
    ext = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for t in np.linspace(0.0, 1.0, 24, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return resample(np.array(out), n)


def _hole_r(p: np.ndarray, c: np.ndarray, r: float) -> np.ndarray:
    """A torn hole's radius toward each point: lobed and uneven round its centre (round 3: clean circles read as punched
    confetti), the same shape every build (its phase from its centre)."""
    n = np.array([c[0], c[1], 0.0])
    n /= max(np.linalg.norm(n), 1e-9)
    e1 = np.array([0.0, 0.0, 1.0])
    e2 = np.cross(n, e1)
    d = np.asarray(p, np.float64) - c
    phi = np.arctan2(d @ e1, d @ e2)
    ph = float((c[0] * 91.7 + c[1] * 37.3 + c[2] * 53.1) % (2 * np.pi))
    return r * (1.0 + 0.3 * np.sin(3.0 * phi + ph) + 0.18 * np.sin(5.0 * phi + 2.0 * ph) + 0.1 * np.sin(8.0 * phi + 0.5 * ph))


class Kit:
    def __init__(self):
        self.verts: list[np.ndarray] = []
        self.faces: list[tuple] = []
        self.uvs: list = []
        self.kface: list[float] = []
        self.attrs: dict[str, list[np.ndarray]] = {k: [] for k in ATTRS}
        self.n = 0
        self.cursor = 0.0

    def _add(self, v: np.ndarray, part: float, pt, pa, pr: float, side) -> int:
        base = self.n
        v = np.asarray(v, np.float64).reshape(-1, 3)
        m = len(v)
        self.verts.append(v)
        self.n += m
        self.attrs['part'].append(np.full(m, float(part)))
        self.attrs['pt'].append(np.broadcast_to(np.asarray(pt, np.float64), (m,)).copy())
        self.attrs['pa'].append(np.broadcast_to(np.asarray(pa, np.float64), (m,)).copy())
        self.attrs['pr'].append(np.full(m, float(pr)))
        self.attrs['side'].append(np.broadcast_to(np.asarray(side, np.float64), (m,)).copy())
        return base

    def tube(self, P, radius, sides: int, part: float, pr: float = 0.5, hint=None, aspect=1.0, caps=(True, True),
             relief=None, texel_k: float = 1.0, min_r: float = 0.0015) -> None:
        """One tube along P (k x 3); radius and aspect (thickness / width) a number or k values; relief(pa, s) -> metres
        added to the radius."""
        P = np.asarray(P, np.float64)
        k = len(P)
        r = np.maximum(np.broadcast_to(np.asarray(radius, np.float64), (k,)), min_r)
        asp = np.broadcast_to(np.asarray(aspect, np.float64), (k,))
        T, N, B = frames(P, hint)
        s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        L = float(s[-1])
        a = np.arange(sides) / sides
        ang = a * 2 * np.pi
        rr = r[:, None] + (relief(a[None, :], s[:, None]) if relief is not None else 0.0)
        rr = np.maximum(rr, min_r)
        v = P[:, None, :] + rr[..., None] * (np.cos(ang)[None, :, None] * N[:, None, :]
                                             + (asp[:, None] * np.sin(ang)[None, :])[..., None] * B[:, None, :])
        base = self._add(v.reshape(-1, 3), part, np.repeat(s / max(L, 1e-9), sides), np.tile(a, k), pr, 0.0)
        circ = 2 * np.pi * float(np.mean(r)) * (1 + float(np.mean(asp))) / 2
        u0 = self.cursor
        for i in range(k - 1):
            for j in range(sides):
                j2 = (j + 1) % sides
                self.faces.append((base + i * sides + j, base + i * sides + j2, base + (i + 1) * sides + j2, base + (i + 1) * sides + j))
                self.uvs.append([(u0 + circ * j / sides, s[i]), (u0 + circ * (j + 1) / sides, s[i]),
                                 (u0 + circ * (j + 1) / sides, s[i + 1]), (u0 + circ * j / sides, s[i + 1])])
                self.kface.append(texel_k)
        self.cursor += circ + 0.01
        for end, on in ((0, caps[0]), (k - 1, caps[1])):
            if not on:
                continue
            sgn = -1.0 if end == 0 else 1.0
            c = P[end] + T[end] * sgn * r[end] * 0.6
            ci = self._add(c[None], part, 0.0 if end == 0 else 1.0, 0.0, pr, 0.0)
            cu = self.cursor + r[end]
            for j in range(sides):
                j2 = (j + 1) % sides
                a1, a2 = base + end * sides + j, base + end * sides + j2
                uvj = (cu + r[end] * math.cos(ang[j]), r[end] + r[end] * math.sin(ang[j]))
                uvj2 = (cu + r[end] * math.cos(ang[j2]), r[end] + r[end] * math.sin(ang[j2]))
                if end:
                    self.faces.append((a1, a2, ci))
                    self.uvs.append([uvj, uvj2, (cu, r[end])])
                else:
                    self.faces.append((a2, a1, ci))
                    self.uvs.append([uvj2, uvj, (cu, r[end])])
                self.kface.append(texel_k)
            self.cursor += 2.2 * r[end] + 0.01

    def shell(self, G: np.ndarray, thick, part: float, pr: float = 0.5, inside=None, texel_k: float = 1.0,
              inner_k: float | None = None) -> None:
        """A thick sheet from its middle surface G (nv+1, nu+1, 3); thick a number or (nv+1, nu+1); inside(points) ->
        points the outer face turns away from. Outer face side +1, inner face side -1, the border walls 0."""
        nv, nu = G.shape[0] - 1, G.shape[1] - 1
        du = np.gradient(G, axis=1)
        dv = np.gradient(G, axis=0)
        Nn = np.cross(du, dv)
        Nn /= np.maximum(np.linalg.norm(Nn, axis=-1, keepdims=True), 1e-12)
        if inside is not None:
            ref = inside(G.reshape(-1, 3)).reshape(G.shape)
            flip = ((G - ref) * Nn).sum(-1) < 0
            if flip.mean() > 0.5:
                Nn = -Nn
        t = np.broadcast_to(np.asarray(thick, np.float64), G.shape[:2])[..., None] * 0.5
        outer, inner = G + Nn * t, G - Nn * t
        su = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(G, axis=1), axis=-1).mean(0))])
        sv = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(G, axis=0), axis=-1).mean(1))])
        U, V = np.meshgrid(su / max(su[-1], 1e-9), sv / max(sv[-1], 1e-9))
        bo = self._add(outer.reshape(-1, 3), part, V.ravel(), U.ravel(), pr, 1.0)
        bi = self._add(inner.reshape(-1, 3), part, V.ravel(), U.ravel(), pr, -1.0)

        def idx(b, j, i):
            return b + j * (nu + 1) + i
        u0 = self.cursor
        w = su[-1]
        for j in range(nv):
            for i in range(nu):
                self.faces.append((idx(bo, j, i), idx(bo, j + 1, i), idx(bo, j + 1, i + 1), idx(bo, j, i + 1)))
                self.uvs.append([(u0 + su[i], sv[j]), (u0 + su[i], sv[j + 1]), (u0 + su[i + 1], sv[j + 1]), (u0 + su[i + 1], sv[j])])
                self.kface.append(texel_k)
                self.faces.append((idx(bi, j, i + 1), idx(bi, j + 1, i + 1), idx(bi, j + 1, i), idx(bi, j, i)))
                self.uvs.append([(u0 + w + 0.01 + su[i + 1], sv[j]), (u0 + w + 0.01 + su[i + 1], sv[j + 1]),
                                 (u0 + w + 0.01 + su[i], sv[j + 1]), (u0 + w + 0.01 + su[i], sv[j])])
                self.kface.append(inner_k if inner_k is not None else texel_k)
        # the walls: one strip round the whole border (top, right, hem, left), its own island
        loop = [(0, i) for i in range(nu)] + [(j, nu) for j in range(nv)] + [(nv, i) for i in range(nu, 0, -1)] + [(j, 0) for j in range(nv, 0, -1)]
        tw = float(np.mean(t)) * 2
        x = 0.0
        y0 = sv[-1] + 0.02
        for q in range(len(loop)):
            (j, i), (j2, i2) = loop[q], loop[(q + 1) % len(loop)]
            seg = float(np.linalg.norm(G[j2, i2] - G[j, i]))
            self.faces.append((idx(bo, j, i), idx(bi, j, i), idx(bi, j2, i2), idx(bo, j2, i2)))
            self.uvs.append([(u0 + x, y0), (u0 + x, y0 + tw), (u0 + x + seg, y0 + tw), (u0 + x + seg, y0)])
            self.kface.append(texel_k)
            x += seg
        self.cursor += 2 * w + 0.03

    def ragged(self, G: np.ndarray, thick, part: float, holes=(), pr: float = 0.5, texel_k: float = 1.0, inside=None) -> None:
        """A thick cloth sheet from its middle surface G (nv+1, nu+1, 3) with real holes cut through it: holes are
        (centre xyz, radius m); a quad whose centre lies inside one is dropped and the corners round the cut are moved
        onto its circle, so the holes are round even on the coarse game mesh. Walls close every cut and border edge.
        Attributes: pt = v (0 at row 0 .. 1 at the last row), pa = u (0..1 across), side +1 / -1 / 0. No own unwrap."""
        G = np.array(G, np.float64)
        nv, nu = G.shape[0] - 1, G.shape[1] - 1
        ctr = 0.25 * (G[:-1, :-1] + G[1:, :-1] + G[1:, 1:] + G[:-1, 1:])
        keep = np.ones((nv, nu), bool)
        for c, r in holes:
            keep &= np.linalg.norm(ctr - np.asarray(c, np.float64), axis=-1) > _hole_r(ctr, np.asarray(c, np.float64), r)
        # round the cuts: corners shared by a kept and a dropped quad go onto the hole's circle
        kv = np.zeros((nv + 1, nu + 1), bool)
        dv = np.zeros((nv + 1, nu + 1), bool)
        for dj in (0, 1):
            for di in (0, 1):
                kv[dj:nv + dj, di:nu + di] |= keep
                dv[dj:nv + dj, di:nu + di] |= ~keep
        rim = kv & dv
        for c, r in holes:
            c = np.asarray(c, np.float64)
            d = G - c
            dist = np.linalg.norm(d, axis=-1)
            m = rim & (dist < 1.8 * r) & (dist > 1e-6)
            G[m] = c + d[m] * (_hole_r(G[m], c, r) / dist[m])[:, None]
        if holes:
            # a quad the snap folded or squashed (its two triangles facing apart, or a sliver) joins the hole: a folded face
            # can't be unwrapped without overlapping itself
            a, b, c2, d2 = G[:-1, :-1], G[1:, :-1], G[1:, 1:], G[:-1, 1:]
            n1 = np.cross(b - a, c2 - a)
            n2 = np.cross(c2 - a, d2 - a)
            l1, l2 = np.linalg.norm(n1, axis=-1), np.linalg.norm(n2, axis=-1)
            agree = (n1 * n2).sum(-1) / np.maximum(l1 * l2, 1e-18)
            area = 0.5 * (l1 + l2)
            med = float(np.median(area[keep])) if keep.any() else 0.0
            bad = keep & ((agree < 0.5) | (area < 0.15 * med))
            keep &= ~bad
            kv[:] = False
            for dj in (0, 1):
                for di in (0, 1):
                    kv[dj:nv + dj, di:nu + di] |= keep
        du = np.gradient(G, axis=1)
        dvv = np.gradient(G, axis=0)
        Nn = np.cross(du, dvv)
        Nn /= np.maximum(np.linalg.norm(Nn, axis=-1, keepdims=True), 1e-12)
        if inside is not None:
            # the outer face (side +1) turns away from `inside` (a body axis point per vertex)
            ref = inside(G.reshape(-1, 3)).reshape(G.shape)
            if float(((G - ref) * Nn).sum(-1).mean()) < 0:
                Nn = -Nn
        t = np.broadcast_to(np.asarray(thick, np.float64), G.shape[:2])[..., None] * 0.5
        used = np.argwhere(kv)
        idx = -np.ones((nv + 1, nu + 1), np.int64)
        idx[kv] = np.arange(int(kv.sum()))
        V = np.linspace(0.0, 1.0, nv + 1)[:, None].repeat(nu + 1, 1)
        U = np.linspace(0.0, 1.0, nu + 1)[None, :].repeat(nv + 1, 0)
        pts_o = (G + Nn * t)[kv]
        pts_i = (G - Nn * t)[kv]
        bo = self._add(pts_o, part, V[kv], U[kv], pr, 1.0)
        bi = self._add(pts_i, part, V[kv], U[kv], pr, -1.0)
        # its own unwrap (no smart projection: folds and cuts made it overlap itself): the outer and the inner faces each
        # one island on the grid's own metric (u, v in metres), the cut walls laid in rows of thin strips beside them
        su = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(G, axis=1), axis=-1).mean(0))])
        sv = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(G, axis=0), axis=-1).mean(1))])
        u0, wid, hgt = self.cursor, float(su[-1]), float(sv[-1])
        tw = float(np.mean(t)) * 2 + 0.002
        wx, wy = 0.0, hgt + 0.01

        def guv(j, i, off):
            return (u0 + off + su[i], sv[j])
        for j, i in np.argwhere(keep):
            q = [idx[j, i], idx[j + 1, i], idx[j + 1, i + 1], idx[j, i + 1]]
            corners = [(j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1)]
            self.faces.append(tuple(bo + k for k in q))
            self.uvs.append([guv(a, b, 0.0) for a, b in corners])
            self.faces.append(tuple(bi + k for k in reversed(q)))
            self.uvs.append([guv(a, b, wid + 0.01) for a, b in reversed(corners)])
            self.kface += [texel_k, texel_k]
            for (a, b), (nj, ni) in ((((j, i), (j + 1, i)), (j, i - 1)), (((j + 1, i), (j + 1, i + 1)), (j + 1, i)),
                                     (((j + 1, i + 1), (j, i + 1)), (j, i + 1)), (((j, i + 1), (j, i)), (j - 1, i))):
                if 0 <= nj < nv and 0 <= ni < nu and keep[nj, ni]:
                    continue
                ia, ib = idx[a], idx[b]
                seg = max(float(np.linalg.norm(G[a] - G[b])), 1e-4)
                if wx + seg > 2 * wid + 0.01:
                    wx, wy = 0.0, wy + tw + 0.004
                self.faces.append((bo + ia, bo + ib, bi + ib, bi + ia))
                self.uvs.append([(u0 + wx, wy), (u0 + wx + seg, wy), (u0 + wx + seg, wy + tw), (u0 + wx, wy + tw)])
                self.kface.append(texel_k)
                wx += seg + 0.002
        self.cursor += 2 * wid + 0.03
        _ = used

    def object(self, name: str, own_uv: bool = True, extra: dict | None = None, recalc: bool = True) -> bpy.types.Object:
        verts = np.concatenate(self.verts)
        ob = S.sheet_object(name, verts, self.faces)
        for k, vals in self.attrs.items():
            S.add_attr(ob, k, np.concatenate(vals))
        for k, vals in (extra or {}).items():
            S.add_attr(ob, k, np.asarray(vals, np.float64))
        me = ob.data
        me.attributes.new('texel_k', 'FLOAT', 'FACE').data.foreach_set('value', np.asarray(self.kface, np.float32))
        if own_uv:
            lay = me.uv_layers.new(name='UVMap')
            flat = [c for f in self.uvs for c in f]
            lay.data.foreach_set('uv', np.asarray(flat, np.float32).ravel())
            ob['own_uv'] = True
        if recalc:
            # every part is a closed shell: turn each one's faces outward (the bake's rays and the AO need it); the
            # loops' UVs travel with them
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
            me.update()
        C.log(f'{name}: {len(me.polygons)} faces, {len(verts)} verts')
        return ob


def closed_object(name: str, rings: list[np.ndarray], caps: tuple[np.ndarray | None, np.ndarray | None]) -> bpy.types.Object:
    """A closed surface from rings of points (each m x 3, the same m, in order round), with a pole at each end (a
    point, or None for a flat fan at the ring's centre). Used for the voxel body's extras."""
    m = len(rings[0])
    verts = [np.asarray(r, np.float64) for r in rings]
    faces = []
    for k in range(len(rings) - 1):
        a, b = k * m, (k + 1) * m
        faces += [(a + j, a + (j + 1) % m, b + (j + 1) % m, b + j) for j in range(m)]
    n = len(rings) * m
    for end, pole in ((0, caps[0]), (1, caps[1])):
        c = np.asarray(pole if pole is not None else (rings[0] if end == 0 else rings[-1]).mean(0), np.float64)
        verts.append(c[None])
        r0 = 0 if end == 0 else (len(rings) - 1) * m
        if end == 0:
            faces += [(n, r0 + (j + 1) % m, r0 + j) for j in range(m)]
        else:
            faces += [(n, r0 + j, r0 + (j + 1) % m) for j in range(m)]
        n += 1
    return S.sheet_object(name, np.concatenate(verts), faces)
