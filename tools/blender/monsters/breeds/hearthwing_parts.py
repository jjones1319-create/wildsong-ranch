"""Hearthwing (young and grown) at Art 2.1 Ultra: the geometry both recipes share.

Closed lofted meshes for the body extras (dorsal spikes, the crest's blades, the tail's spade), lofted props (ringed
horns, talons, the wings' arm and finger tubes), fan sheets for the ear frills, an analytic inside test of the recipe's
parts (to seat spikes, horns and frills on the skin before the body exists), the scale plates' midribs and a vein
network for the membranes. Nothing here knows the breed's numbers: hearthwing_ultra.py (young) and
hearthwing_grown_ultra.py (grown) pass them in.

Metres; the monster faces -Y, Z is up, +X is its left. Pinned to Blender 5.2.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Euler, Vector

from lib import common as C
from lib import surface as S
from lib.mesh import Part
from lib.surface import norm, smooth, v3


# ============================================================================= small maths
def unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def catmull(pts, n_per: int = 12) -> np.ndarray:
    """A Catmull-Rom curve through the points (the ends repeated), n_per samples a span."""
    P = [v3(p) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n_per):
            t = k / n_per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def arc_lengths(pts: np.ndarray) -> np.ndarray:
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(d)])


def resample(curve: np.ndarray, n: int) -> np.ndarray:
    """n points at equal arc length along a polyline."""
    s = arc_lengths(curve)
    t = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(t, s, curve[:, i]) for i in range(3)], axis=1)


def curve_at(curve: np.ndarray, t) -> np.ndarray:
    """Points at arc-length share t (0..1) along a polyline."""
    s = arc_lengths(curve)
    tt = np.clip(np.atleast_1d(np.asarray(t, float)), 0, 1) * s[-1]
    return np.stack([np.interp(tt, s, curve[:, i]) for i in range(3)], axis=1)


def tangents(c: np.ndarray) -> np.ndarray:
    return norm(np.gradient(c, axis=0))


def side_frames(c: np.ndarray, ref) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(T, X, Y) along a centre line: T the tangent, X the reference direction made perpendicular to T, Y = T x X, so
    X x Y = T (rings wound round +T face outward)."""
    T = tangents(c)
    r = np.broadcast_to(v3(ref), c.shape).copy()
    X = r - T * (r * T).sum(axis=1, keepdims=True)
    bad = np.linalg.norm(X, axis=1) < 1e-6
    if bad.any():
        alt = np.cross(T[bad], np.array([0.0, 0.0, 1.0]))
        alt[np.linalg.norm(alt, axis=1) < 1e-6] = (1.0, 0.0, 0.0)
        X[bad] = alt
    X = norm(X)
    Y = np.cross(T, X)
    return T, X, Y


# ============================================================================= meshes
def mesh_object(name: str, verts, faces, coll=None) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    me.update()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob, coll)
    return ob


def loft(name: str, centres: np.ndarray, X: np.ndarray, Y: np.ndarray, rx: np.ndarray, ry: np.ndarray, seg: int = 16,
         cap0: bool = True, cap1: bool = True, tip1=None, coll=None, ring_attrs: dict | None = None) -> bpy.types.Object:
    """A closed tube: one ring of `seg` vertices per centre (half axes rx along X, ry along Y), faces wound outward when
    X x Y points along the centre line; a fan cap at the start and, at the end, a fan to the centre or to `tip1` (a
    point). `ring_attrs` {name: per-ring values} become point attributes (caps take their ring's value)."""
    n = len(centres)
    a = np.linspace(0.0, 2 * math.pi, seg, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    ring = (centres[:, None, :] + X[:, None, :] * (rx[:, None] * ca[None])[..., None]
            + Y[:, None, :] * (ry[:, None] * sa[None])[..., None])
    verts = list(ring.reshape(-1, 3))
    faces = []
    for i in range(n - 1):
        for j in range(seg):
            jn = (j + 1) % seg
            faces.append((i * seg + j, i * seg + jn, (i + 1) * seg + jn, (i + 1) * seg + j))
    per_ring = [list(range(i * seg, (i + 1) * seg)) for i in range(n)]
    ring_of = [i for i in range(n) for _ in range(seg)]
    if cap0:
        c0 = len(verts)
        verts.append(centres[0])
        ring_of.append(0)
        for j in range(seg):
            faces.append((c0, per_ring[0][(j + 1) % seg], per_ring[0][j]))
    if cap1:
        c1 = len(verts)
        verts.append(v3(tip1) if tip1 is not None else centres[-1])
        ring_of.append(n - 1)
        for j in range(seg):
            faces.append((c1, per_ring[-1][j], per_ring[-1][(j + 1) % seg]))
    ob = mesh_object(name, verts, faces, coll)
    for k, vals in (ring_attrs or {}).items():
        vals = np.asarray(vals, np.float64)
        S.add_attr(ob, k, vals[np.array(ring_of)])
    return ob


def blade_axis(base, up, back, length: float, width: float, thick: float, bend: float = 0.3, bury: float = 0.4,
               rings: int = 12, lean: float = 0.25):
    """A blade spike's centre line and half axes: (centres, X, Y, rx, ry, t) with t from -bury (under the skin) to 1
    (the tip)."""
    up, back = unit(up), unit(back)
    back = unit(back - up * (back @ up))
    t = np.linspace(-bury, 1.0, rings)
    tt = np.clip(t, 0.0, 1.0)
    c = v3(base)[None] + up[None] * (length * t)[:, None] + back[None] * (bend * length * tt ** 2 + lean * width * tt)[:, None]
    T, X, Y = side_frames(c, back)
    prof = np.where(t < 0, 1.0 + 0.15 * (t / max(bury, 1e-6)), (1.0 - tt) ** 0.85)
    return c, X, Y, 0.5 * width * prof, 0.5 * thick * prof ** 0.8, t


def blade(name: str, spec: dict, rings: int = 12, seg: int = 12, coll=None) -> bpy.types.Object:
    """A spike shaped like a shark's fin, for the voxel body (spec: base, up, back, length, width, thick, bend, bury,
    lean): rises from `base` along `up` (its root buried `bury` of the length under the skin), bending toward `back` by
    `bend` of its length at the tip; cross-section an ellipse `width` long (along `back`) and `thick` across, tapering to
    a point; `lean` slides the sections toward `back` as it rises (a swept leading edge, a hollow trailing one)."""
    c, X, Y, rx, ry, _t = blade_axis(spec['base'], spec['up'], spec['back'], spec['length'], spec['width'], spec['thick'],
                                     spec.get('bend', 0.3), spec.get('bury', 0.4), rings, spec.get('lean', 0.25))
    return loft(name, c[:-1], X[:-1], Y[:-1], rx[:-1], ry[:-1], seg, True, True, c[-1], coll)


def blade_field(p: np.ndarray, specs: list[dict], pad: float = 0.004, rings: int = 10) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For points p: (on a blade, t along it 0 skin .. 1 tip, which blade): a point is on a blade when it lies within
    the blade's half width (+ pad) of its centre line, above the skin."""
    p = v3(p).reshape(-1, 3)
    best = np.full(len(p), np.inf)
    tb = np.zeros(len(p))
    idx = np.full(len(p), -1, np.int64)
    for k, sp in enumerate(specs):
        c, _X, _Y, rx, _ry, t = blade_axis(sp['base'], sp['up'], sp['back'], sp['length'], sp['width'], sp['thick'],
                                           sp.get('bend', 0.3), sp.get('bury', 0.4), rings, sp.get('lean', 0.25))
        lo = c.min(axis=0) - rx.max() - pad
        hi = c.max(axis=0) + rx.max() + pad
        near = np.all((p > lo) & (p < hi), axis=1)
        if not near.any():
            continue
        q = p[near]
        dmin = np.full(len(q), np.inf)
        tmin = np.zeros(len(q))
        rmin = np.zeros(len(q))
        for i in range(len(c) - 1):
            ab = c[i + 1] - c[i]
            u = np.clip(((q - c[i]) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
            d = np.linalg.norm(q - (c[i] + u[:, None] * ab), axis=1)
            better = d < dmin
            dmin = np.where(better, d, dmin)
            tmin = np.where(better, t[i] + u * (t[i + 1] - t[i]), tmin)
            rmin = np.where(better, rx[i] + u * (rx[i + 1] - rx[i]), rmin)
        score = dmin / np.maximum(rmin + pad, 1e-4)
        ok = (score < 1.0) & (tmin > -0.15)
        sub = np.nonzero(near)[0]
        win = ok & (score < best[sub])
        best[sub[win]] = score[win]
        tb[sub[win]] = tmin[win]
        idx[sub[win]] = k
    return idx >= 0, np.clip(tb, 0.0, 1.0), idx


def teardrop(name: str, base, tip, side, width: float, thick: float, bulge: float = 0.4, curl: float = 0.0, rings: int = 22,
             seg: int = 20, coll=None, taper: float = 1.6) -> bpy.types.Object:
    """A plump leaf (the tail's spade): from a rounded `base` to a pointed `tip`, widest at `bulge` of its length;
    `width` along `side`, `thick` across; `curl` bends the tip toward the leaf's thin axis (metres at the tip)."""
    b, tp = v3(base), v3(tip)
    ax = unit(tp - b)
    L = float(np.linalg.norm(tp - b))
    sd = unit(v3(side) - ax * (v3(side) @ ax))
    nrm = np.cross(ax, sd)
    t = np.linspace(0.0, 1.0, rings)
    c = b[None] + ax[None] * (L * t)[:, None] + nrm[None] * (curl * t ** 2)[:, None]
    T, X, Y = side_frames(c, sd)
    # rounded base (a quarter circle into the widest point), then a long taper to the point
    k = np.where(t < bulge, np.sqrt(np.clip(1.0 - ((bulge - t) / bulge) ** 2, 0.0, 1.0)),
                 1.0 - np.clip((t - bulge) / (1.0 - bulge), 0.0, 1.0) ** taper)
    k = np.clip(k, 0.0, 1.0) ** 0.9
    rx = 0.5 * width * k
    ry = 0.5 * thick * k
    rx[0] = ry[0] = 0.0
    return loft(name, c[1:-1], X[1:-1], Y[1:-1], np.maximum(rx[1:-1], 1e-4), np.maximum(ry[1:-1], 1e-4), seg, True, True, c[-1], coll)


def tube(name: str, pts: np.ndarray, radii: np.ndarray, ref, seg: int = 12, flat: float = 1.0, tip=None, cap0: bool = True,
         coll=None, ring_attrs: dict | None = None) -> bpy.types.Object:
    """A tube along a polyline (props: arm and finger bones, talons, horns); `flat` < 1 squashes it along Y."""
    T, X, Y = side_frames(pts, ref)
    radii = np.asarray(radii, np.float64)
    return loft(name, pts, X, Y, radii, radii * flat, seg, cap0, True, tip, coll, ring_attrs)


def talon(name: str, root, direction, down, length: float, radius: float, curve: float = 0.35, rings: int = 9, seg: int = 10,
          flat: float = 0.8, coll=None, ring_attrs: dict | None = None, blunt: bool = False) -> bpy.types.Object:
    """A curved claw: from `root` along `direction`, hooking toward `down` (curve x length at the tip), round at the
    root, a sharp point; `flat` < 1 makes it narrower side to side. `blunt`: an acorn (full almost to the end, then a
    rounded tip), for short, fat toe claws."""
    d = unit(direction)
    dn = unit(v3(down) - d * (v3(down) @ d))
    t = np.linspace(0.0, 1.0, rings)
    if blunt == 'cone':
        t = 1.0 - (1.0 - t) ** 1.6           # rings closer together toward the round tip
    c = v3(root)[None] + d[None] * (length * t)[:, None] + dn[None] * (curve * length * t ** 2)[:, None]
    if blunt == 'cone':
        # round 3: a smooth cone tapering straight to a blunt, round point (a cap of 0.38 x the root's radius)
        rt = 0.38 * radius
        tc = 1.0 - rt / length
        cone = radius + (rt - radius) * np.clip(t / tc, 0.0, 1.0)
        cap = rt * np.sqrt(np.clip(1.0 - ((t - tc) / (1.0 - tc)) ** 2, 0.0, 1.0))
        r = np.where(t < tc, cone, cap) * (0.93 + 0.07 * np.sqrt(np.clip(t * 6, 0, 1)))
    elif blunt:
        r = radius * np.sqrt(np.clip(1.0 - t ** 2.4, 0.0, 1.0)) * (0.9 + 0.1 * np.sqrt(np.clip(t * 5, 0, 1)))
    else:
        r = radius * np.clip(1.0 - t ** 1.3, 0.04, 1.0) * (0.85 + 0.15 * np.sqrt(np.clip(t * 6, 0, 1)))
    T, X, Y = side_frames(c, dn)
    attrs = dict(ring_attrs or {})
    attrs.setdefault('talon_t', t)
    return loft(name, c[:-1], X[:-1], Y[:-1], r[:-1], r[:-1] * flat, seg, True, True, c[-1], coll,
                {k: (np.asarray(v)[:-1] if np.ndim(v) else np.full(rings - 1, float(v))) for k, v in attrs.items()})


def ringed_horn(name: str, path: np.ndarray, r0: float, r_tip: float, rings_n: int, groove: float, high: bool, seg: int,
                ref, coll=None) -> bpy.types.Object:
    """A copper horn: a tube along `path` (root inside the head to the tip), its radius tapering from r0, with
    `rings_n` ring grooves (`groove` = depth as a share of the radius; shallower on the game mesh), a rounded tip.
    Attributes: horn = (t along, groove 0..1, 0), own unwrap (one strip)."""
    n = len(path)
    t = np.linspace(0.0, 1.0, n)
    r = r0 * (1.0 - t) ** 0.75 + r_tip * t
    g_ph = (t ** 0.85) * rings_n
    f = g_ph - np.floor(g_ph)
    gv = np.exp(-(np.minimum(f, 1 - f) / 0.12) ** 2) * smooth(0.06, 0.14, t) * smooth(0.98, 0.88, t)
    rr = r * (1.0 - groove * (1.0 if high else 0.35) * gv)
    if high:
        rr = rr * (1.0 + 0.006 * np.sin(t * 2 * math.pi * rings_n * 3.7))
    T, X, Y = side_frames(path, ref)
    tip = path[-1] + T[-1] * r_tip * 0.8
    ob = loft(name, path, X, Y, rr, rr, seg, True, True, tip, coll, {'horn_t': t, 'horn_g': gv})
    S.add_attr(ob, 'horn', np.stack([S.attr_array(ob, 'horn_t'), S.attr_array(ob, 'horn_g'), np.zeros(len(ob.data.vertices))], axis=1))
    S.tube_uvs(ob, path)
    return ob


# ============================================================================= the parts' inside test (seating extras)
def _part_inside(p: np.ndarray, part: Part, side: int) -> np.ndarray:
    q = p.copy()
    if side < 0:
        q[:, 0] = -q[:, 0]
    if part.kind in ('capsule', 'tube'):
        a, b = v3(part.loc), v3(part.to or part.loc)
        ab = b - a
        t = np.clip(((q - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
        r2 = part.r2 if (part.kind == 'tube' and part.r2 is not None) else part.radius
        r = part.radius + (r2 - part.radius) * t
        return np.linalg.norm(q - (a[None] + t[:, None] * ab[None]), axis=1) < r
    if part.kind == 'box':
        R = np.array(Euler([math.radians(x) for x in part.rot], 'XYZ').to_matrix())
        loc = (q - v3(part.loc)) @ R
        h = v3(part.scale) * part.radius
        return np.all(np.abs(loc) < h, axis=1)
    R = np.array(Euler([math.radians(x) for x in part.rot], 'XYZ').to_matrix())
    loc = (q - v3(part.loc)) @ R
    return (((loc / (v3(part.scale) * part.radius)) ** 2).sum(axis=1)) < 1.0


def inside(p, parts: list[Part]) -> np.ndarray:
    p = v3(p).reshape(-1, 3)
    m = np.zeros(len(p), bool)
    for pt in parts:
        for side in ((1, -1) if pt.mirror else (1,)):
            m |= _part_inside(p, pt, side)
    return m


def surface_hit(origin, direction, parts: list[Part], reach: float = 2.0, step: float = 0.0015) -> np.ndarray | None:
    """The first point where a ray from `origin` (outside) enters the parts, or None."""
    o, d = v3(origin), unit(direction)
    s = np.arange(0.0, reach, step)
    pts = o[None] + d[None] * s[:, None]
    m = inside(pts, parts)
    if not m.any():
        return None
    return pts[int(np.argmax(m))]


def top_of(x: float, y: float, parts: list[Part], z0: float = 3.0) -> float | None:
    h = surface_hit((x, y, z0), (0, 0, -1), parts, reach=z0)
    return None if h is None else float(h[2])


def side_of(y: float, z: float, parts: list[Part], x0: float = 1.5) -> float | None:
    h = surface_hit((x0, y, z), (-1, 0, 0), parts, reach=x0)
    return None if h is None else float(h[0])


# ============================================================================= sheets (the ear frills)
def fan_sheet(name: str, point_fn, nu: int, nv: int, out=None, attrs_fn=None) -> bpy.types.Object:
    """A sheet over (u 0 root .. 1 edge, v 0..1 across): `point_fn(U, V)` -> (n, 3) points, `attrs_fn(U, V)` -> {name:
    per-point values}; faces turned toward `out` (a direction, or a callable of the face centres)."""
    uu = np.linspace(0.0, 1.0, nu + 1)
    vv = np.linspace(0.0, 1.0, nv + 1)
    Ug, Vg = np.meshgrid(uu, vv, indexing='ij')
    P = point_fn(Ug.ravel(), Vg.ravel())
    faces = []
    for j in range(nu):
        for i in range(nv):
            a = j * (nv + 1) + i
            faces.append((a, a + 1, a + nv + 2, a + nv + 1))
    ob = S.sheet_object(name, P, faces, None, out=out if out is not None and not callable(out) else None)
    if callable(out):
        S.orient_away(ob, lambda c: c - out(c))
    if attrs_fn is not None:
        for k, v in attrs_fn(Ug.ravel(), Vg.ravel()).items():
            S.add_attr(ob, k, np.asarray(v, np.float64))
    me = ob.data
    if 'UVMap' not in me.uv_layers:
        me.uv_layers.new(name='UVMap')
    return ob


# ============================================================================= scales
def shingle_field(co: np.ndarray, vn: np.ndarray, plates: dict, scale: float = 1.0, lift: float = 0.12,
                  leaf: float = 0.22) -> dict[str, np.ndarray]:
    """Overlapping scales laid like shingles (4-details panel 6), for plates from lib.ultra.plate_layout: each scale rises
    from its root (tucked under the scale before it, `lift` of its height) to its free edge (toward the plate's t, the
    flow), where it drops steeply; the highest wins where scales overlap, so every free edge stands over the next scale's
    root as a small step. Returns h (metres along the normal), pid (-1 off the scales), ul (-1 root .. 1 free edge along
    the scale), uq (across), rho (0 middle .. 1 outline) of the winning scale. Same neighbourhood search as
    lib.ultra.plate_field."""
    co, vn = v3(co).reshape(-1, 3), v3(vn).reshape(-1, 3)
    n = len(co)
    best = np.full(n, -np.inf)
    pid = np.full(n, -1, np.int64)
    ul_w = np.zeros(n)
    uq_w = np.zeros(n)
    rho_w = np.full(n, 2.0)
    k = len(plates['c'])
    if k == 0:
        z = np.zeros(n)
        return {'h': z, 'pid': pid, 'ul': z, 'uq': z, 'rho': z + 2.0}
    R = np.maximum(plates['a'], plates['b']) * (1.0 + np.abs(plates['harm'][:, :, 0]).sum(axis=1))
    cell = float(R.max())
    key = np.floor(co / cell).astype(np.int64) + (1 << 20)
    kk = (key[:, 0] * (1 << 21) + key[:, 1]) * (1 << 21) + key[:, 2]
    order = np.argsort(kk, kind='stable')
    sk = kk[order]
    offs = np.array([(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)], np.int64)
    for i in range(k):
        c = plates['c'][i]
        ck = np.floor(c / cell).astype(np.int64) + (1 << 20) + offs
        keys = (ck[:, 0] * (1 << 21) + ck[:, 1]) * (1 << 21) + ck[:, 2]
        lo = np.searchsorted(sk, keys, 'left')
        hi = np.searchsorted(sk, keys, 'right')
        parts = [order[a:b] for a, b in zip(lo, hi) if b > a]
        if not parts:
            continue
        idx = np.concatenate(parts)
        d = co[idx] - c
        nrm, t = plates['n'][i], plates['t'][i]
        bt = np.cross(nrm, t)
        s_, q_, r_ = d @ t, d @ bt, d @ nrm
        a, b = plates['a'][i], plates['b'][i]
        th = np.arctan2(q_ / b, s_ / a)
        hm = plates['harm'][i]
        mod = 1.0 + sum(hm[j, 0] * np.cos((j + 2) * th + hm[j, 1]) for j in range(hm.shape[0]))
        # a leaf: narrower toward its free end (`leaf` 0.22: a rounded end; ~0.85: a pointed leaf tip), full at the root
        ul = s_ / a
        width = np.maximum(1.0 - leaf * np.clip(ul, 0, 1) ** 1.5, 0.08)
        rho = np.sqrt((s_ / a) ** 2 + (q_ / (b * width)) ** 2) / mod
        near = (rho < 1.0) & (np.abs(r_) < 0.6 * max(a, b)) & ((vn[idx] @ nrm) > 0.2)
        if not near.any():
            continue
        idx, rho, ul, uq = idx[near], rho[near], ul[near], (q_ / b)[near]
        rise = lift + (1.0 - lift) * np.clip((ul + 1.0) * 0.5, 0, 1) ** 1.1
        prof = rise * np.sqrt(np.clip(1.0 - rho ** 6, 0, 1))
        hh = plates['h'][i] * prof
        win = hh > best[idx]
        w = idx[win]
        best[w] = hh[win]
        pid[w] = i
        ul_w[w] = ul[win]
        uq_w[w] = uq[win]
        rho_w[w] = rho[win]
    inside = pid >= 0
    return {'h': np.where(inside, best, 0.0) * scale, 'pid': pid, 'ul': ul_w, 'uq': uq_w, 'rho': rho_w}


def scale_midrib(co: np.ndarray, plates: dict, pid: np.ndarray, width: float = 0.09) -> np.ndarray:
    """0..1 per vertex: the raised midrib down each scale's long axis (4-details: leaf scales with a vein), strongest in
    the scale's middle, fading at its root and tip."""
    out = np.zeros(len(co))
    on = pid >= 0
    if not on.any():
        return out
    i = pid[on]
    d = co[on] - plates['c'][i]
    nrm, t = plates['n'][i], plates['t'][i]
    bt = np.cross(nrm, t)
    s_ = (d * t).sum(axis=1) / plates['a'][i]
    q_ = (d * bt).sum(axis=1) / plates['b'][i]
    out[on] = np.exp(-(q_ / width) ** 2) * smooth(-0.85, -0.3, s_) * smooth(0.95, 0.55, s_)
    return out


def scale_local(co: np.ndarray, plates: dict, pid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(s along the scale's long axis, q across), each about -1..1 inside a scale; 0 off the plates."""
    s_ = np.zeros(len(co))
    q_ = np.zeros(len(co))
    on = pid >= 0
    if on.any():
        i = pid[on]
        d = co[on] - plates['c'][i]
        nrm, t = plates['n'][i], plates['t'][i]
        bt = np.cross(nrm, t)
        s_[on] = (d * t).sum(axis=1) / plates['a'][i]
        q_[on] = (d * bt).sum(axis=1) / plates['b'][i]
    return s_, q_


# ============================================================================= membrane veins
def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0xFFFFFF)


def cell_veins(p: np.ndarray, cell: float, seed: int = 1, width: float = 0.07) -> np.ndarray:
    """A network of fine veins (cells, like a leaf's): 1 on a cell's edge (F2 - F1 of a jittered grid), 0 inside."""
    q = v3(p) / cell
    base = np.floor(q).astype(np.int64)
    f1 = np.full(len(q), 9.0)
    f2 = np.full(len(q), 9.0)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = base + np.array([dx, dy, dz])
                jx = _hash(c[:, 0], c[:, 1], c[:, 2], seed)
                jy = _hash(c[:, 0], c[:, 1], c[:, 2], seed + 7)
                jz = _hash(c[:, 0], c[:, 1], c[:, 2], seed + 13)
                fp = c + np.stack([jx, jy, jz], axis=1) * 0.9 + 0.05
                d = np.linalg.norm(q - fp, axis=1)
                f2 = np.where(d < f1, f1, np.minimum(f2, d))
                f1 = np.minimum(f1, d)
    return np.exp(-((f2 - f1) / width) ** 2)


def _seg_dist(px: np.ndarray, py: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = max(dx * dx + dy * dy, 1e-12)
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy)), t


def branch_veins(x: np.ndarray, y: np.ndarray, pid: np.ndarray, seed: int = 3, n_main: int = 4, width: float = 0.03,
                 sides=(0, 1), sides_of=None) -> np.ndarray:
    """0..1: veins branching from the bones on a membrane panel's sides (x = 0 and x = 1; y runs from the root, 0, to
    the free edge, 1) out toward the free edge, each with two side branches, tapering (round 3: branching veins from the
    finger bones, not crackle cells). `sides_of(panel)` may limit which sides carry bones."""
    out = np.zeros(len(x))
    rng = np.random.default_rng(seed)
    for p in np.unique(np.round(pid).astype(int)):
        m = np.round(pid).astype(int) == p
        px, py = x[m], y[m]
        best = np.zeros(int(m.sum()))
        for side in (sides_of(p) if sides_of else sides):
            sg = 1.0 if side == 0 else -1.0
            for i in range(n_main):
                y0 = 0.1 + (i + rng.uniform(0.15, 0.55)) * 0.78 / n_main
                ang = rng.uniform(0.5, 0.85)
                L = rng.uniform(0.3, 0.46)
                pts = [(float(side), y0)]
                for f in (0.34, 0.67, 1.0):
                    dx = L * f
                    pts.append((side + sg * dx, y0 + ang * dx + 0.3 * dx * dx))
                segs = [(pts[j], pts[j + 1], width * (1.0 - 0.22 * j)) for j in range(3)]
                for j, (fa, fb_, steep) in enumerate(((0.34, 0.2, 1.6), (0.67, 0.16, 0.25))):
                    bx, by = pts[1 + j]
                    segs.append(((bx, by), (bx + sg * fb_, by + steep * fb_ + 0.04), width * (0.55 - 0.1 * j)))
                for a, b, w in segs:
                    d, t = _seg_dist(px, py, a, b)
                    best = np.maximum(best, np.exp(-(d / (w * (1.0 - 0.35 * t))) ** 2))
        out[m] = best * smooth(0.02, 0.08, py) * smooth(1.02, 0.94, py)
    return np.clip(out, 0.0, 1.0)


def plate_majority(centres: np.ndarray, on: np.ndarray, k: int = 8, flip: int = 6, iters: int = 2) -> np.ndarray:
    """Round 3: a scale whose colour disagrees with at least `flip` of its `k` nearest neighbours takes theirs, so the
    cream border is a clean scaly sawtooth with no one- or two-scale islands of cream on teal (or teal on cream)."""
    from mathutils.kdtree import KDTree
    n = len(centres)
    if n < k + 1:
        return on.astype(np.float64)
    kd = KDTree(n)
    for i, c in enumerate(centres):
        kd.insert(Vector(tuple(map(float, c))), i)
    kd.balance()
    nb = np.array([[j for _co, j, _d in kd.find_n(Vector(tuple(map(float, c))), k + 1) if j != i][:k] for i, c in enumerate(centres)])
    v = on.astype(bool).copy()
    for _ in range(iters):
        agree = v[nb].sum(axis=1)
        v = np.where(v & (k - agree >= flip), False, np.where(~v & (agree >= flip), True, v))
    return v.astype(np.float64)


# ============================================================================= paint helpers
def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def blend(rgb: np.ndarray, k, hexcol: str) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    if k.ndim == 1:
        k = k[:, None]
    return rgb * (1.0 - k) + lin(hexcol)[None] * k


def eye_material_nodes(name: str, rough_pass: bool, eye_hex: str, iris_r: float = 0.8, pupil_r: float = 0.5,
                       iris_shift: tuple[float, float] = (0.05, 0.03)):
    """A big glossy cartoon eye (3-faces, 4-details panel 2): a gold iris (CONTENT's eye colour, deep amber at its rim
    and toward the pupil, radial fibres), a large black pupil, white showing round it, a thin dark rim, a thick upper
    lash line flicked at the outer corner, and two crisp catchlights (one big up toward the key light, one small)."""
    from lib.nodes import new_mat
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.04, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    # the iris sits a little toward the nose and up (the eyes look ahead, white showing on the outer side and below)
    ix = nb.math('ADD', x, nb.math('MULTIPLY', side, iris_shift[0]))
    iy = nb.math('SUBTRACT', y, iris_shift[1])
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), iris_r)
    gold = C.lin(eye_hex)
    deep = C.lin(C.mix_hex(eye_hex, '#A0520F', 0.55))
    iris = nb.ramp(ri, [(0.0, C.lin('#05060A')), (pupil_r / iris_r * 0.98, C.lin('#05060A')), (pupil_r / iris_r + 0.03, C.lin('#5A2A08')),
                        (pupil_r / iris_r + 0.1, deep), (0.74, C.lin(C.mix_hex(eye_hex, '#F2A23A', 0.35))), (0.86, gold),
                        (0.94, deep), (1.0, C.lin('#2A1606')), (1.05, C.lin('#F3EFE6')), (1.6, C.lin('#F3EFE6'))])
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 42.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', nb.smooth(ri, pupil_r / iris_r + 0.05, 0.7), nb.smooth(ri, 0.97, 0.85)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.22), iris, nb.rgb(C.lin('#FFE7A0')))
    low = nb.math('MULTIPLY', nb.smooth(iy, -0.05, -0.65), nb.math('MULTIPLY', nb.smooth(ri, 0.97, 0.6), nb.smooth(ri, pupil_r / iris_r, pupil_r / iris_r + 0.12)))
    c = nb.mix(nb.math('MULTIPLY', low, 0.45), iris, nb.rgb(C.lin('#FFE9A8')))
    # the white is greyer toward the lens' rim (it curves away into the socket)
    rr = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(rr, 0.7, 0.98), nb.smooth(ri, 1.02, 1.1)), 0.35), c, nb.rgb(C.lin('#B9B4AC')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, 0.26), nb.math('DIVIDE', nb.math('SUBTRACT', iy, 0.3), 1.15), 0.0)), 0.21, 0.17)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, 0.24), nb.math('ADD', iy, 0.28), 0.0)), 0.08, 0.06)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    rim = nb.smooth(rr, 0.9, 0.97)
    c = nb.mix(rim, c, nb.rgb(C.lin('#24140C')))
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', x, side), 0.2, 0.95), 0.16)
    lash = nb.smooth(nb.math('ADD', y, outer), 0.6, 0.69)
    c = nb.mix(lash, c, nb.rgb(C.lin('#14100E')))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
