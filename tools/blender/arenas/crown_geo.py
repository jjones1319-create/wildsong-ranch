"""Geometry core for the Crown Amphitheatre (Blender 5.2): ellipse maths and a mesh builder with bake islands.

The bowl is laid out on concentric ellipses, P(t, off) = ((A0 + off) cos t, (B0 + off) sin t, z), where `off` is the
distance outward from the arena floor's edge. Parts are "bent" along them so they tile the curve.

MB (the mesh builder) writes, per face: the material index, `UVMap` (texture coordinates in metres: along the wall
and up, or along and across for flat faces) and `BakeUV` (the bake-atlas island, also in metres; every island owns its
vertices, so islands never join by accident and crown_bake only has to pack them), plus face attributes (`lite`,
`crowd`, `riser`, `v0`, `row`, `wedge`, …) that the materials and the export read.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

A0, B0 = 27.0, 20.0          # the arena floor's semi-axes (m): 54 x 40 m of sand


# ----------------------------------------------------------------------------- the ellipse
def pt(t: float, off: float, z: float) -> tuple[float, float, float]:
    return ((A0 + off) * math.cos(t), (B0 + off) * math.sin(t), z)


def speed(t: float, off: float) -> float:
    return math.hypot((A0 + off) * math.sin(t), (B0 + off) * math.cos(t))


def normal(t: float, off: float) -> tuple[float, float]:
    """The outward unit normal of the offset ellipse at t (in the ground plane)."""
    nx, ny = (B0 + off) * math.cos(t), (A0 + off) * math.sin(t)
    k = math.hypot(nx, ny)
    return nx / k, ny / k


def bend(t0: float, off: float, x: float, d: float, z: float) -> tuple[float, float, float]:
    """Local (x along the wall, d outward, z up) around angle t0 on the ellipse at offset off."""
    return pt(t0 + x / speed(t0, off), off + d, z)


def arc_table(off: float, n: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    t = np.linspace(0.0, 2 * math.pi, n + 1)
    sp = np.hypot((A0 + off) * np.sin(t), (B0 + off) * np.cos(t))
    s = np.concatenate([[0.0], np.cumsum((sp[1:] + sp[:-1]) * 0.5 * np.diff(t))])
    return t, s


def perimeter(off: float) -> float:
    return float(arc_table(off)[1][-1])


def t_at_arc(off: float, s) -> np.ndarray:
    """The angle where the arc length (from t = 0, counter-clockwise) reaches s (wraps)."""
    t, sv = arc_table(off)
    s = np.mod(np.asarray(s, np.float64), sv[-1])
    return np.interp(s, sv, t)


def arc_at_t(off: float, tt) -> np.ndarray:
    t, sv = arc_table(off)
    return np.interp(np.mod(np.asarray(tt, np.float64), 2 * math.pi), t, sv)


def span_ts(off: float, t0: float, t1: float, step: float) -> list[float]:
    """Angles from t0 to t1 (t1 > t0) spaced about `step` metres of arc apart at offset off (at least 2 columns)."""
    s0, s1 = float(arc_at_t(off, t0)), float(arc_at_t(off, t1))
    if t1 - t0 >= 2 * math.pi - 1e-9:
        s1 = s0 + perimeter(off)
    elif s1 < s0:
        s1 += perimeter(off)
    n = max(1, int(round((s1 - s0) / step)))
    ts = [float(x) for x in t_at_arc(off, np.linspace(s0, s1, n + 1))]
    out = [t0]
    for x in ts[1:-1]:
        while x < out[-1]:
            x += 2 * math.pi
        out.append(x)
    out.append(t1)
    return out


# ----------------------------------------------------------------------------- the mesh builder
class MB:
    def __init__(self) -> None:
        self.v: list[tuple[float, float, float]] = []
        self.f: list[tuple[int, ...]] = []
        self.uv: list[list[tuple[float, float]]] = []
        self.buv: list[list[tuple[float, float]]] = []
        self.m: list[int] = []
        self.fa: list[dict] = []

    def verts(self, pts) -> int:
        base = len(self.v)
        self.v.extend(tuple(map(float, p)) for p in pts)
        return base

    def face(self, idx, uv, buv, mat: int, attrs: dict | None = None) -> None:
        self.f.append(tuple(idx))
        self.uv.append(list(uv))
        self.buv.append(list(buv))
        self.m.append(mat)
        self.fa.append(attrs or {})

    def quad(self, p, uv, mat: int, attrs: dict | None = None, buv=None) -> None:
        """One face as its own island: its own vertices; BakeUV = UVMap unless given."""
        b = self.verts(p)
        self.face(range(b, b + len(p)), uv, buv if buv is not None else uv, mat, attrs)

    def island(self, polys, uvs, mat: int, attrs: dict | None = None) -> None:
        """Several faces as ONE island: corners at the same place (and with the same UV) share a vertex, so the
        faces stay joined in the bake atlas (a bay front, a banner, a rope) instead of each becoming its own island."""
        seen: dict = {}
        for poly, uv in zip(polys, uvs):
            idx = []
            for p, t in zip(poly, uv):
                key = (round(p[0], 4), round(p[1], 4), round(p[2], 4), round(t[0], 4), round(t[1], 4))
                if key not in seen:
                    seen[key] = self.verts([p])
                idx.append(seen[key])
            self.face(idx, uv, uv, mat, attrs)

    def __len__(self) -> int:
        return len(self.f)

    def build(self, name: str, coll, mats, smooth: bool = False) -> bpy.types.Object:
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        for mt in mats:
            me.materials.append(mt)
        if self.f:
            me.polygons.foreach_set('material_index', np.asarray(self.m, np.int32))
            for lname, src in (('UVMap', self.uv), ('BakeUV', self.buv)):
                layer = me.uv_layers.new(name=lname)
                layer.data.foreach_set('uv', np.asarray([c for fc in src for c in fc], np.float32).ravel())
            names = sorted({k for d in self.fa for k in d})
            for an in names:
                vals = [d.get(an, 0) for d in self.fa]
                kind = 'INT' if an in ('lite', 'near') else 'FLOAT'
                a = me.attributes.new(an, kind, 'FACE')
                a.data.foreach_set('value', np.asarray(vals, np.int32 if kind == 'INT' else np.float32))
        me.polygons.foreach_set('use_smooth', np.full(len(me.polygons), smooth, bool))
        ob['custom_bake'] = True
        me.update()
        return ob


# ----------------------------------------------------------------------------- swept and bent parts
def sweep(mb: MB, prof, ts, mat_of=None, attrs_of=None, close: bool = False, face_fn=None) -> None:
    """Sweep a profile [(off, z), ...] along the angles `ts` (one island). Faces face the arena / up when the profile
    runs outward-and-up. mat_of(i) / attrs_of(i) give the material and face attributes of profile segment i, or
    face_fn(i, j) -> (material, attributes) per segment i and column j."""
    n = len(ts)
    rings = [[pt(t, o, z) for t in ts] for o, z in prof]
    arcs = []
    for o, z in prof:
        P = np.asarray([pt(t, o, 0) for t in ts])
        arcs.append(np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]))
    s = [0.0]
    for (o1, z1), (o2, z2) in zip(prof, prof[1:]):
        s.append(s[-1] + math.hypot(o2 - o1, z2 - z1))
    base = mb.verts([p for r in rings for p in r])
    cols = n - 1 if not close else n
    for i in range(len(prof) - 1):
        (o1, z1), (o2, z2) = prof[i], prof[i + 1]
        if abs(o2 - o1) < 1e-6 and abs(z2 - z1) < 1e-6:
            continue
        vert = abs(z2 - z1) > abs(o2 - o1)
        mat = mat_of(i) if mat_of else 0
        at = attrs_of(i) if attrs_of else {}
        for j in range(cols):
            if face_fn is not None:
                mat, at = face_fn(i, j)
                if mat is None:
                    continue
            j2 = (j + 1) % n
            q = (base + i * n + j, base + (i + 1) * n + j, base + (i + 1) * n + j2, base + i * n + j2)
            u = [arcs[i][j], arcs[i + 1][j], arcs[i + 1][j2] if j2 else arcs[i + 1][-1], arcs[i][j2] if j2 else arcs[i][-1]]
            v = [z1, z2, z2, z1] if vert else [o1, o2, o2, o1]
            mb.face(q, list(zip(u, v)), list(zip(u, [s[i], s[i + 1], s[i + 1], s[i]])), mat, at)


def frame(t: float, off: float = 0.0):
    """A straight local frame at angle t: P(x along the tangent, d along the outward normal, z up) → world."""
    ox, oy, _ = pt(t, off, 0.0)
    nx, ny = normal(t, off)
    ax, ay = -ny, nx

    def P(x, d, z):
        return (ox + ax * x + nx * d, oy + ay * x + ny * d, z)
    return P


def bbox(mb: MB, t: float, off: float, x0, x1, d0, d1, z0, z1, mat: int, attrs: dict | None = None,
         skip: tuple = ()) -> None:
    """A box bent along the ellipse (x along, d outward, z up); each face its own island. skip: face names to drop
    ('bottom', 'top', 'in', 'out', 'left', 'right')."""
    fbox(mb, lambda x, d, z: bend(t, off, x, d, z), x0, x1, d0, d1, z0, z1, mat, attrs, skip)


def fbox(mb: MB, P, x0, x1, d0, d1, z0, z1, mat: int, attrs: dict | None = None, skip: tuple = ()) -> None:
    """A box in the local frame P(x, d, z) (x along, d outward, z up: left-handed, as bend and frame are)."""
    X, Dd, Zz = (x0, x1), (d0, d1), (z0, z1)
    # (x along, d outward, z up) is a left-handed frame: these windings give outward normals
    faces = {
        'bottom': [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        'top': [(0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1)],
        'in': [(0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)],
        'out': [(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)],
        'left': [(0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)],
        'right': [(1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)],
    }
    for name, cs in faces.items():
        if name in skip:
            continue
        if name in ('in', 'out'):
            uv = [(X[a], Zz[c]) for a, b, c in cs]
        elif name in ('top', 'bottom'):
            uv = [(X[a], Dd[b]) for a, b, c in cs]
        else:
            uv = [(Dd[b], Zz[c]) for a, b, c in cs]
        mb.quad([P(X[a], Dd[b], Zz[c]) for a, b, c in cs], uv, mat, attrs)


def lathe(mb: MB, profile, segs: int, centre, mat: int, attrs: dict | None = None, cap: bool = True,
          squash=(1.0, 1.0)) -> None:
    """Revolve [(r, z), ...] around a vertical axis at `centre`: one island (unrolled, seam duplicated) plus a top cap."""
    cx, cy, cz = centre
    cols = segs + 1
    s = [0.0]
    for (r1, z1), (r2, z2) in zip(profile, profile[1:]):
        s.append(s[-1] + math.hypot(r2 - r1, z2 - z1))
    rmax = max(r for r, _ in profile)
    pts = []
    for r, z in profile:
        for k in range(cols):
            a = 2 * math.pi * k / segs
            pts.append((cx + r * math.cos(a) * squash[0], cy + r * math.sin(a) * squash[1], cz + z))
    base = mb.verts(pts)
    circ = 2 * math.pi * rmax
    for i in range(len(profile) - 1):
        for k in range(segs):
            q = (base + i * cols + k, base + i * cols + k + 1, base + (i + 1) * cols + k + 1, base + (i + 1) * cols + k)
            uv = [(circ * k / segs, s[i]), (circ * (k + 1) / segs, s[i]), (circ * (k + 1) / segs, s[i + 1]), (circ * k / segs, s[i + 1])]
            mb.face(q, uv, uv, mat, attrs)
    r, z = profile[-1]
    if cap and r > 1e-4:
        ring = [(cx + r * math.cos(2 * math.pi * k / segs) * squash[0], cy + r * math.sin(2 * math.pi * k / segs) * squash[1], cz + z) for k in range(segs)]
        uv = [(r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs)) for k in range(segs)]
        mb.quad(ring, uv, mat, attrs)


def box(mb: MB, centre, size, mat: int, attrs: dict | None = None, yaw: float = 0.0, skip: tuple = ()) -> None:
    """An axis box (turned `yaw` about z), each face its own island; UVMap in metres."""
    cx, cy, cz = centre
    sx, sy, sz = (s / 2 for s in size)
    ca, sa = math.cos(yaw), math.sin(yaw)

    def p(x, y, z):
        return (cx + x * ca - y * sa, cy + x * sa + y * ca, cz + z)
    X, Y, Z = 2 * sx, 2 * sy, 2 * sz
    faces = {
        'bottom': ([p(-sx, -sy, -sz), p(-sx, sy, -sz), p(sx, sy, -sz), p(sx, -sy, -sz)], [(0, 0), (0, Y), (X, Y), (X, 0)]),
        'top': ([p(-sx, -sy, sz), p(sx, -sy, sz), p(sx, sy, sz), p(-sx, sy, sz)], [(0, 0), (X, 0), (X, Y), (0, Y)]),
        '-y': ([p(-sx, -sy, -sz), p(sx, -sy, -sz), p(sx, -sy, sz), p(-sx, -sy, sz)], [(0, 0), (X, 0), (X, Z), (0, Z)]),
        '+y': ([p(sx, sy, -sz), p(-sx, sy, -sz), p(-sx, sy, sz), p(sx, sy, sz)], [(0, 0), (X, 0), (X, Z), (0, Z)]),
        '-x': ([p(-sx, sy, -sz), p(-sx, -sy, -sz), p(-sx, -sy, sz), p(-sx, sy, sz)], [(0, 0), (Y, 0), (Y, Z), (0, Z)]),
        '+x': ([p(sx, -sy, -sz), p(sx, sy, -sz), p(sx, sy, sz), p(sx, -sy, sz)], [(0, 0), (Y, 0), (Y, Z), (0, Z)]),
    }
    for name, (ps, uv) in faces.items():
        if name not in skip:
            mb.quad(ps, uv, mat, attrs)
