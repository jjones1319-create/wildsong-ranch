"""Mesh builders for Mirrorkin's props (mirrorkin_ornament.py, mirrorkin_cloak.py): a collector of parts with their own
unwrap, after ashwraith_mesh.Kit, plus closed loops, faceted gems and per-point extras.

`Kit` accumulates parts, then makes one object:
- `tube(P, radius, ...)`: a tube along a centre line (rotation-minimising frames, an elliptic cross-section, rounded
  caps, or a closed loop), unrolled as one strip (u round it, v along it, in metres);
- `shell(G, thick, ...)`: a thick sheet from a grid of middle-surface points: outer and inner faces (each one island)
  and the walls round its border;
- `gem(...)`: a faceted stone (a marquise or a round cut): a flat table, crown facets, a pavilion behind;
- `closed(rings, poles)`: a closed lathe-like solid (body extras; no unwrap).
Every object carries the same per-point attributes (ATTRS), so the joined props keep them all: part (an id), pt (0 at
a part's start .. 1 at its end), pa (0..1 round a tube or across a sheet), pr (a random number per part), side (+1 a
sheet's outer face, -1 its inner face, 0 elsewhere), ed (a sheet's distance to its free edge, metres), es (the arc
length along that edge, metres), fk (a gem facet's tilt: 1 the table .. 0 the girdle .. -1 the pavilion), fd (a
cloth fold's crest, -1 in the hollows .. +1 on the crests). A FACE
attribute texel_k sets each part's share of the atlas. Nothing tapers to zero area (zero-area faces give NaN normals).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S

ATTRS = ('part', 'pt', 'pa', 'pr', 'side', 'ed', 'es', 'fk', 'fd')


def frames(P: np.ndarray, hint=None, closed: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tangents, normals and binormals along a polyline (rotation-minimising; the first normal from `hint`)."""
    k = len(P)
    if closed:
        T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    else:
        T = np.zeros_like(P)
        T[1:-1] = P[2:] - P[:-2]
        T[0] = P[1] - P[0]
        T[-1] = P[-1] - P[-2]
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    h = np.array(hint if hint is not None else (0.0, 0.0, 1.0), np.float64)
    if abs(float(h @ T[0])) > 0.97:
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


def arclen(P: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.asarray(P, np.float64), axis=0), axis=1))])


def catmull(pts, n: int) -> np.ndarray:
    """A smooth curve through the points (uniform Catmull-Rom), n evenly spaced samples."""
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


class Kit:
    def __init__(self):
        self.verts: list[np.ndarray] = []
        self.faces: list[tuple] = []
        self.uvs: list = []
        self.kface: list[float] = []
        self.flat: list[bool] = []
        self.attrs: dict[str, list[np.ndarray]] = {k: [] for k in ATTRS}
        self.n = 0
        self.cursor = 0.0

    def _add(self, v: np.ndarray, part: float, pt=0.0, pa=0.0, pr: float = 0.5, side=0.0, **extra) -> int:
        base = self.n
        v = np.asarray(v, np.float64).reshape(-1, 3)
        m = len(v)
        self.verts.append(v)
        self.n += m
        vals = {'part': float(part), 'pt': pt, 'pa': pa, 'pr': float(pr), 'side': side}
        vals.update(extra)
        for k in ATTRS:
            self.attrs[k].append(np.broadcast_to(np.asarray(vals.get(k, 0.0), np.float64), (m,)).copy())
        return base

    def _face(self, f, uv, k: float, flat: bool = False) -> None:
        self.faces.append(tuple(f))
        self.uvs.append(uv)
        self.kface.append(k)
        self.flat.append(flat)

    # ------------------------------------------------------------------ tubes
    def tube(self, P, radius, sides: int, part: float, pr: float = 0.5, hint=None, aspect=1.0, caps=(True, True),
             closed: bool = False, relief=None, texel_k: float = 1.0, min_r: float = 0.0012, offset=None, **extra) -> None:
        """One tube along P (k x 3); radius and aspect (thickness along B / width along N) a number or k values;
        relief(pa, s) -> metres added to the radius; offset (k x 2) moves the section centre along (N, B); closed: a loop."""
        P = np.asarray(P, np.float64)
        k = len(P)
        r = np.maximum(np.broadcast_to(np.asarray(radius, np.float64), (k,)), min_r)
        asp = np.broadcast_to(np.asarray(aspect, np.float64), (k,))
        T, N, B = frames(P, hint, closed)
        s = arclen(np.vstack([P, P[:1]]) if closed else P)
        L = float(s[-1])
        s = s[:k]
        a = np.arange(sides) / sides
        ang = a * 2 * np.pi
        rr = r[:, None] + (relief(a[None, :], s[:, None]) if relief is not None else 0.0)
        rr = np.maximum(rr, min_r)
        c = P.copy()
        if offset is not None:
            off = np.asarray(offset, np.float64)
            c = c + off[:, :1] * N + off[:, 1:2] * B
        v = c[:, None, :] + rr[..., None] * (np.cos(ang)[None, :, None] * N[:, None, :]
                                             + (asp[:, None] * np.sin(ang)[None, :])[..., None] * B[:, None, :])
        ex = {kk: (np.repeat(vv, sides) if np.ndim(vv) == 1 and len(vv) == k else vv) for kk, vv in extra.items()}
        base = self._add(v.reshape(-1, 3), part, np.repeat(s / max(L, 1e-9), sides), np.tile(a, k), pr, 0.0, **ex)
        circ = 2 * np.pi * float(np.mean(r)) * (1 + float(np.mean(asp))) / 2
        u0 = self.cursor
        rows = k if closed else k - 1
        for i in range(rows):
            i2 = (i + 1) % k
            sv0, sv1 = s[i], (s[i2] if i2 > i else L)
            for j in range(sides):
                j2 = (j + 1) % sides
                self._face((base + i * sides + j, base + i * sides + j2, base + i2 * sides + j2, base + i2 * sides + j),
                           [(u0 + circ * j / sides, sv0), (u0 + circ * (j + 1) / sides, sv0),
                            (u0 + circ * (j + 1) / sides, sv1), (u0 + circ * j / sides, sv1)], texel_k)
        self.cursor += circ + 0.01
        if closed:
            return
        for end, on in ((0, caps[0]), (k - 1, caps[1])):
            if not on:
                continue
            sgn = -1.0 if end == 0 else 1.0
            cc = c[end] + T[end] * sgn * r[end] * 0.6
            ci = self._add(cc[None], part, 0.0 if end == 0 else 1.0, 0.0, pr, 0.0,
                           **{kk: (vv[end] if np.ndim(vv) == 1 and len(vv) == k else vv) for kk, vv in extra.items()})
            cu = self.cursor + r[end]
            for j in range(sides):
                j2 = (j + 1) % sides
                a1, a2 = base + end * sides + j, base + end * sides + j2
                uvj = (cu + r[end] * math.cos(ang[j]), r[end] + r[end] * math.sin(ang[j]))
                uvj2 = (cu + r[end] * math.cos(ang[j2]), r[end] + r[end] * math.sin(ang[j2]))
                if end:
                    self._face((a1, a2, ci), [uvj, uvj2, (cu, r[end])], texel_k)
                else:
                    self._face((a2, a1, ci), [uvj2, uvj, (cu, r[end])], texel_k)
            self.cursor += 2.2 * r[end] + 0.01

    # ------------------------------------------------------------------ sheets
    def shell(self, G: np.ndarray, thick, part: float, pr: float = 0.5, inside=None, texel_k: float = 1.0,
              inner_k: float | None = None, wall_k: float | None = None, extra: dict | None = None) -> None:
        """A thick sheet from its middle surface G (nv+1, nu+1, 3); thick a number or (nv+1, nu+1); inside(points) ->
        points the outer face turns away from; extra {name: (nv+1, nu+1) values}. Outer face side +1, inner -1, walls 0."""
        nv, nu = G.shape[0] - 1, G.shape[1] - 1
        du = np.gradient(G, axis=1)
        dv = np.gradient(G, axis=0)
        Nn = np.cross(du, dv)
        Nn /= np.maximum(np.linalg.norm(Nn, axis=-1, keepdims=True), 1e-12)
        if inside is not None:
            ref = inside(G.reshape(-1, 3)).reshape(G.shape)
            if float(((G - ref) * Nn).sum(-1).mean()) < 0:
                Nn = -Nn
        t = np.broadcast_to(np.asarray(thick, np.float64), G.shape[:2])[..., None] * 0.5
        outer, inner = G + Nn * t, G - Nn * t
        su = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(G, axis=1), axis=-1).mean(0))])
        sv = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(G, axis=0), axis=-1).mean(1))])
        U, V = np.meshgrid(su / max(su[-1], 1e-9), sv / max(sv[-1], 1e-9))
        ex = {k: np.asarray(v, np.float64).ravel() for k, v in (extra or {}).items()}
        bo = self._add(outer.reshape(-1, 3), part, V.ravel(), U.ravel(), pr, 1.0, **ex)
        bi = self._add(inner.reshape(-1, 3), part, V.ravel(), U.ravel(), pr, -1.0, **ex)

        def idx(b, j, i):
            return b + j * (nu + 1) + i
        u0 = self.cursor
        w = su[-1]
        ik = inner_k if inner_k is not None else texel_k
        for j in range(nv):
            for i in range(nu):
                self._face((idx(bo, j, i), idx(bo, j + 1, i), idx(bo, j + 1, i + 1), idx(bo, j, i + 1)),
                           [(u0 + su[i], sv[j]), (u0 + su[i], sv[j + 1]), (u0 + su[i + 1], sv[j + 1]), (u0 + su[i + 1], sv[j])], texel_k)
                self._face((idx(bi, j, i + 1), idx(bi, j + 1, i + 1), idx(bi, j + 1, i), idx(bi, j, i)),
                           [(u0 + w + 0.01 + su[i + 1], sv[j]), (u0 + w + 0.01 + su[i + 1], sv[j + 1]),
                            (u0 + w + 0.01 + su[i], sv[j + 1]), (u0 + w + 0.01 + su[i], sv[j])], ik)
        loop = [(0, i) for i in range(nu)] + [(j, nu) for j in range(nv)] + [(nv, i) for i in range(nu, 0, -1)] + [(j, 0) for j in range(nv, 0, -1)]
        tw = float(np.mean(t)) * 2
        x = 0.0
        y0 = sv[-1] + 0.02
        wk = wall_k if wall_k is not None else texel_k
        for q in range(len(loop)):
            (j, i), (j2, i2) = loop[q], loop[(q + 1) % len(loop)]
            seg = float(np.linalg.norm(G[j2, i2] - G[j, i]))
            self._face((idx(bo, j, i), idx(bi, j, i), idx(bi, j2, i2), idx(bo, j2, i2)),
                       [(u0 + x, y0), (u0 + x, y0 + tw), (u0 + x + seg, y0 + tw), (u0 + x + seg, y0)], wk)
            x += seg
        self.cursor += 2 * w + 0.03

    # ------------------------------------------------------------------ gems
    def gem(self, c, nrm, up, a: float, b: float, part: float, cut: str = 'marquise', pr: float = 0.5, n: int = 16,
            crown: float = 0.35, table: float = 0.55, pavilion: float = 0.55, texel_k: float = 1.4) -> None:
        """A faceted stone centred at c, its table facing nrm, its long axis (b) along up: a girdle outline (a pointed
        marquise or a round cut), a crown rising `crown` x b to a table `table` of the girdle's size, and a pavilion
        `pavilion` x b deep behind it. Flat-shaded facets."""
        c, nrm, up = (np.asarray(v, np.float64) for v in (c, nrm, up))
        nrm = nrm / np.linalg.norm(nrm)
        up = up - nrm * float(up @ nrm)
        up /= np.linalg.norm(up)
        ac = np.cross(up, nrm)
        t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
        if cut == 'marquise':
            # pointed at both ends of the long axis (a cusp: the width grows as |angle| ** 1.35 near each tip)
            gu = a * np.sin(t) * (np.abs(np.sin(t)) ** 0.35)
            gv = b * np.cos(t)
        else:
            gu, gv = a * np.sin(t), b * np.cos(t)
        h_c = crown * min(a, b) * 1.6
        h_p = pavilion * min(a, b) * 2.2
        gird = c[None] + gu[:, None] * ac + gv[:, None] * up
        gird2 = gird - nrm[None] * (0.08 * h_c)
        tab = c[None] + nrm[None] * h_c + (gu[:, None] * ac + gv[:, None] * up) * table
        base = self._add(np.vstack([tab, gird, gird2, (c + nrm * h_c)[None], (c - nrm * h_p)[None]]), part,
                         0.5, np.concatenate([t, t, t, [0.0], [0.0]]) / (2 * np.pi), pr, 0.0,
                         fk=np.concatenate([np.full(n, 1.0), np.full(n, 0.0), np.full(n, -0.2), [1.0], [-1.0]]))
        ti, gi, g2, ct, cp = base, base + n, base + 2 * n, base + 3 * n, base + 3 * n + 1
        u0 = self.cursor
        sc = 0.5 / max(a, b)

        def uv(p):
            d = p - c
            return (u0 + (float(d @ ac) * sc + 0.5) * 2 * max(a, b), (float(d @ up) * sc + 0.5) * 2 * max(a, b))
        allp = np.vstack([tab, gird, gird2, (c + nrm * h_c)[None], (c - nrm * h_p)[None]])
        for j in range(n):
            j2 = (j + 1) % n
            self._face((ct, ti + j, ti + j2), [uv(allp[3 * n]), uv(allp[j]), uv(allp[j2])], texel_k, True)
            self._face((ti + j, gi + j, gi + j2, ti + j2), [uv(allp[j]), uv(allp[n + j]), uv(allp[n + j2]), uv(allp[j2])], texel_k, True)
        # the girdle's thin wall and the pavilion: their own islands beside the crown (laid out by hand, flat)
        pc = (u0 + 2.2 * 2 * max(a, b), max(a, b))
        for j in range(n):
            j2 = (j + 1) % n
            wx = 2 * max(a, b) * 2 + 0.003 * j
            self._face((gi + j, g2 + j, g2 + j2, gi + j2),
                       [(u0 + wx + 0.0, 0.0), (u0 + wx, 0.002), (u0 + wx + 0.0025, 0.002), (u0 + wx + 0.0025, 0.0)], texel_k, True)
            r1 = (pc[0] + 0.9 * max(a, b) * math.cos(t[j]), pc[1] + 0.9 * max(a, b) * math.sin(t[j]))
            r2 = (pc[0] + 0.9 * max(a, b) * math.cos(t[j2]), pc[1] + 0.9 * max(a, b) * math.sin(t[j2]))
            self._face((g2 + j2, g2 + j, cp), [r2, r1, pc], texel_k * 0.5, True)
        self.cursor += 2 * max(a, b) * 2 + 0.003 * n + 2 * max(a, b) + 0.02

    # ------------------------------------------------------------------ the object
    def object(self, name: str, own_uv: bool = True, recalc: bool = True, flat_gems: bool = True) -> bpy.types.Object:
        verts = np.concatenate(self.verts)
        ob = S.sheet_object(name, verts, self.faces)
        for k, vals in self.attrs.items():
            S.add_attr(ob, k, np.concatenate(vals))
        me = ob.data
        me.attributes.new('texel_k', 'FLOAT', 'FACE').data.foreach_set('value', np.asarray(self.kface, np.float32))
        if own_uv:
            lay = me.uv_layers.new(name='UVMap')
            flat = [cc for f in self.uvs for cc in f]
            lay.data.foreach_set('uv', np.asarray(flat, np.float32).ravel())
            ob['own_uv'] = True
        if recalc:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
            me.update()
        if flat_gems and any(self.flat):
            sm = np.array([not f for f in self.flat], bool)
            me.polygons.foreach_set('use_smooth', sm)
            me.update()
        C.log(f'{name}: {len(me.polygons)} faces, {len(verts)} verts')
        return ob


def closed_object(name: str, rings: list[np.ndarray], caps: tuple[np.ndarray, np.ndarray]) -> bpy.types.Object:
    """A closed surface from rings of points (each m x 3, the same m, in order round), with a pole at each end (a
    voxel body extra: no unwrap). Faces turn outward."""
    m = len(rings[0])
    verts = [np.asarray(r, np.float64) for r in rings]
    faces = []
    for k in range(len(rings) - 1):
        a, b = k * m, (k + 1) * m
        faces += [(a + j, a + (j + 1) % m, b + (j + 1) % m, b + j) for j in range(m)]
    n = len(rings) * m
    for end, pole in ((0, caps[0]), (1, caps[1])):
        verts.append(np.asarray(pole, np.float64)[None])
        r0 = 0 if end == 0 else (len(rings) - 1) * m
        if end == 0:
            faces += [(n, r0 + (j + 1) % m, r0 + j) for j in range(m)]
        else:
            faces += [(n, r0 + j, r0 + (j + 1) % m) for j in range(m)]
        n += 1
    ob = S.sheet_object(name, np.concatenate(verts), faces)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob
