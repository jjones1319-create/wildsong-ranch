"""Zipwisp's rigid props (zipwisp_ultra.py build_props): the two spark wings and the zigzag bolt tail as crisp pillowed
slabs cut from their outlines (zipwisp_form), and the little yellow sparks crackling round the ball as thin zigzag
tubes.

A slab: the outline is resampled, rows of points are set in from its edge (so the white rim paints and glows crisply
per vertex), the inside is filled and triangulated (Blender's constrained Delaunay), and the two faces are lifted off
the mid-plane by a pillow profile: a short wall at the edge (EDGE_HALF, never zero), rounding up over BEVEL to the
part's thickness. Its own unwrap (`own_uv`): each face laid flat in its plane, the wall as one strip. Attributes for the
paint and the weights: part, ed (metres to the edge), su (0 root .. 1 the far point), side (+1 left wing, -1 right),
face (+1 front, -1 back, 0 wall).
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Vector, geometry

from lib import common as C
from lib import surface as S
from monsters.breeds import zipwisp_form as F

WING, TAIL, SPARK = 1, 2, 3
EDGE_HALF = 0.003                     # half the wall's height at every edge (a slab never thins to nothing)
BEVEL = 0.008                         # how far in from the edge the face rounds up to the full thickness
ROWS = (0.0022, 0.0048)               # rows set in from the edge: the rim's paint and glow change across them


def _seg_dist(p: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Distance from 2D points to a closed polygon's edges."""
    d = np.full(len(p), np.inf)
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        ab = b - a
        t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-18), 0, 1)
        d = np.minimum(d, np.linalg.norm(p - (a + t[:, None] * ab), axis=1))
    return d


def _inside(p: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Even-odd rule."""
    x, y = p[:, 0], p[:, 1]
    inside = np.zeros(len(p), bool)
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        cond = (a[1] > y) != (b[1] > y)
        xi = a[0] + (y - a[1]) * (b[0] - a[0]) / np.where(np.abs(b[1] - a[1]) < 1e-18, 1e-18, b[1] - a[1])
        inside ^= cond & (x < xi)
    return inside


def _resample(poly: np.ndarray, step: float) -> np.ndarray:
    out = []
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / step)))
        for k in range(n):
            out.append(a + (b - a) * k / n)
    return np.array(out)


def slab(name: str, outline, origin: Vector, ax_u: Vector, ax_v: Vector, normal: Vector, thick, part: int, step: float,
         attrs: dict | None = None):
    """A pillowed slab from a 2D outline (u, v metres) in the plane (origin, ax_u, ax_v); `thick(u)` its full thickness;
    the front face toward `normal`. Returns the object."""
    poly = np.asarray(outline, np.float64)
    area = 0.5 * float(np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]))
    if area < 0:
        poly = poly[::-1].copy()                       # counter-clockwise
    ring = _resample(poly, step)
    k = len(ring)
    # rows set in from the edge, along each point's inward normal (kept only where the true distance agrees)
    e_prev = ring - np.roll(ring, 1, axis=0)
    e_next = np.roll(ring, -1, axis=0) - ring
    def inward(e):
        n = np.stack([-e[:, 1], e[:, 0]], axis=1)
        return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    nin = inward(e_prev) + inward(e_next)
    nin /= np.maximum(np.linalg.norm(nin, axis=1), 1e-12)[:, None]
    extra = []
    for d in ROWS:
        cand = ring + nin * d
        dd = _seg_dist(cand, poly)
        ok = _inside(cand, poly) & (np.abs(dd - d) < 0.3 * d)
        extra.append(cand[ok])
    # the fill: a hex grid inside, clear of the rows
    xs = np.arange(poly[:, 0].min(), poly[:, 0].max(), step * 1.2)
    ys = np.arange(poly[:, 1].min(), poly[:, 1].max(), step * 1.2 * math.sqrt(3) / 2)
    gx, gy = np.meshgrid(xs, ys)
    gx = gx + (np.arange(len(ys))[:, None] % 2) * step * 0.6
    grid = np.stack([gx.ravel(), gy.ravel()], axis=1)
    grid = grid[_inside(grid, poly) & (_seg_dist(grid, poly) > ROWS[-1] + step * 0.55)]
    pts2 = np.concatenate([ring] + extra + [grid])
    # thin out points that crowd each other (the rows at sharp corners)
    keep = np.ones(len(pts2), bool)
    for i in range(k, len(pts2)):
        if not keep[i]:
            continue
        dd = np.linalg.norm(pts2[:i] - pts2[i], axis=1)
        if (dd[keep[:i]] < step * 0.45).any():
            keep[i] = False
    pts2 = pts2[keep]
    res = geometry.delaunay_2d_cdt([Vector(p) for p in pts2], [], [list(range(k))], 1, 1e-7)
    vco, faces, orig = np.array([v[:] for v in res[0]], np.float64), [list(f) for f in res[2]], res[3]
    used = sorted({i for f in faces for i in f})
    remap = {o: i for i, o in enumerate(used)}
    vco = vco[used]
    faces = [[remap[i] for i in f] for f in faces]
    inv = {}
    for out_i, ins in enumerate(orig):
        for j in ins:
            inv[j] = out_i
    loop = [remap[inv[j]] for j in range(k)]           # the outline, in order, as output vertices
    n2 = len(vco)
    ed = _seg_dist(vco, poly)
    ed[loop] = 0.0
    umax = float(poly[:, 0].max())
    su = np.clip(vco[:, 0] / max(umax, 1e-9), 0, 1)
    t = np.array([thick(float(u)) for u in vco[:, 0]])
    prof = np.sqrt(np.clip(1.0 - (1.0 - np.clip(ed / BEVEL, 0, 1)) ** 2, 0, 1))
    h = EDGE_HALF + (np.maximum(t * 0.5, EDGE_HALF) - EDGE_HALF) * prof
    O, U, V, N = (np.array(a[:], np.float64) for a in (origin, ax_u, ax_v, normal))
    mid = O + vco[:, :1] * U + vco[:, 1:2] * V
    front = mid + h[:, None] * N
    back = mid - h[:, None] * N
    verts = np.concatenate([front, back])
    fl = []
    kinds = []
    for f in faces:
        fl.append(f)
        kinds.append(1)
        fl.append([i + n2 for i in f[::-1]])
        kinds.append(-1)
    wall_out = []
    for a, b in zip(loop, loop[1:] + loop[:1]):
        fl.append([a, b, b + n2, a + n2])
        kinds.append(0)
        d = vco[b] - vco[a]                            # the outline runs counter-clockwise: outward is to its right
        wall_out.append(d[1] * U - d[0] * V)
    # every face turned outward: the faces by the slab's normal, the wall away from the outline's inside
    nrm = np.array([np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]]) for f in fl])
    want = np.zeros_like(nrm)
    kinds = np.array(kinds)
    want[kinds == 1] = N
    want[kinds == -1] = -N
    want[kinds == 0] = np.array(wall_out)
    flip = (nrm * want).sum(axis=1) < 0
    fl = [f[::-1] if fp else f for f, fp in zip(fl, flip)]
    ob = S.sheet_object(name, verts, fl)
    for key, vals in {'part': np.full(2 * n2, float(part)), 'ed': np.concatenate([ed, ed]), 'su': np.concatenate([su, su]),
                      'face': np.concatenate([np.ones(n2), -np.ones(n2)])}.items():
        S.add_attr(ob, key, vals)
    for key, val in {'side': 0.0, 'spark_id': -1.0, **(attrs or {})}.items():
        S.add_attr(ob, key, np.full(2 * n2, float(val)))
    _own_uvs(ob, fl, vco, kinds, loop, n2)
    C.log(f'{name}: {len(fl)} faces, {len(verts)} verts')
    return ob


def _own_uvs(ob, faces, vco, kinds, loop, n2) -> None:
    """Front laid flat in its plane, the back mirrored beside it, the wall as one strip (metres; the packer scales)."""
    w = float(vco[:, 0].max() - vco[:, 0].min()) + 0.02
    u0, v0 = float(vco[:, 0].min()), float(vco[:, 1].min())
    perim = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(vco[loop + loop[:1]], axis=0), axis=1))])
    pos = {v: perim[i] for i, v in enumerate(loop)}
    flat = []
    hgt = 2 * EDGE_HALF
    half = 0.5 * perim[-1]
    for f, kd in zip(faces, kinds):
        if kd == 1:
            flat += [(vco[i % n2, 0] - u0, vco[i % n2, 1] - v0) for i in f]
        elif kd == -1:
            flat += [(2 * w - (vco[i % n2, 0] - u0), vco[i % n2, 1] - v0) for i in f]
        else:
            ps = [pos[i % n2] for i in f]
            wrap = max(ps) - min(ps) > half            # the strip's last quad, closing the loop
            for i, p in zip(f, ps):
                if wrap and p < half:
                    p = p + perim[-1]
                flat.append((p, -0.03 - (hgt if i >= n2 else 0.0)))
    lay = ob.data.uv_layers.new(name='UVMap')
    lay.data.foreach_set('uv', np.asarray(flat, np.float32).ravel())
    ob['own_uv'] = True


# ----------------------------------------------------------------------------- the wings and the tail
def wing(s: int, high: bool):
    o, u, v, n = F.wing_axes(s)
    outline = [(a, b) for a, b in F.WING_OUTLINE]
    t0, t1 = F.WING_T

    def thick(x: float) -> float:
        k = min(1.0, max(0.0, x / (0.17 * F.WING_K)))
        return t0 + (t1 - t0) * k ** 0.7
    tag = 'L' if s > 0 else 'R'
    return slab(f"{'hi' if high else 'lo'}_wing{tag}", outline, o, u, v, n, thick, WING, 0.0035 if high else 0.0065, {'side': s})


def tail_outline() -> list[tuple[float, float]]:
    """The bolt's outline in its plane (s, w metres): its centre line offset by the half widths, mitred at each corner
    into a sharp point, closing to the tip."""
    _o, _s, _w, _n, L = F.tail_axes()
    c = np.array([(a * L, b) for a, b in F.TAIL_LINE])
    hw = np.array(F.TAIL_HALF)
    up, dn = [], []
    for i in range(len(c)):
        if i == len(c) - 1:
            up.append(c[i])
            continue
        if i == 0:
            d = c[1] - c[0]
            d /= np.linalg.norm(d)
            nn = np.array([-d[1], d[0]])
            up.append(c[i] + nn * hw[i])
            dn.append(c[i] - nn * hw[i])
            continue
        d0 = (c[i] - c[i - 1]) / np.linalg.norm(c[i] - c[i - 1])
        d1 = (c[i + 1] - c[i]) / np.linalg.norm(c[i + 1] - c[i])
        n0 = np.array([-d0[1], d0[0]])
        n1 = np.array([-d1[1], d1[0]])
        m = n0 + n1
        m /= np.linalg.norm(m)
        k = hw[i] / max(float(m @ n0), 0.35)          # the mitre, capped at sharp turns
        up.append(c[i] + m * k)
        dn.append(c[i] - m * k)
    return [tuple(p) for p in up] + [tuple(p) for p in dn[::-1]]


def tail(high: bool):
    o, s, w, n, L = F.tail_axes()
    t0, t1 = F.TAIL_T

    def thick(x: float) -> float:
        return t0 + (t1 - t0) * min(1.0, max(0.0, x / L))
    return slab(f"{'hi' if high else 'lo'}_tail", tail_outline(), o, s, w, n, thick, TAIL, 0.0035 if high else 0.0065)


# ----------------------------------------------------------------------------- the sparks
# Review 1: about 25 bolts (1-hero), floating in a shell round the ball rather than on or in the fur, none in front of the
# face, every one clear of the wings, the tail, the crown's flames, the tongues and the other sparks. Review 3: thin bolts
# tapering to points, each with its own 2-3 bends of varied angle and length, some forked (one blunt Z each read as a
# letter); a loose shell at about 1.05-1.3x the fuzzy radius; no more than 3 over the body from any of 8 views round it
# (about 10 stacked on the back read as a sleepy "Z Z Z"); none over the back core.
N_SPARKS = 24
SPARK_LEN = (0.06, 0.09)
SPARK_R = (0.0011, 0.0032)           # the tube's radius at its points, and how much more at its thickest
VIEW_LIMIT = 3
_LAYOUT: list = []


def _clutter() -> np.ndarray:
    """Points the sparks must keep clear of: the wings' and the tail's outlines and fills, the crown and the curl,
    the tongues' upper parts."""
    pts = []
    for sd in (1, -1):
        o, u, v, _n = F.wing_axes(sd)
        poly = np.array(F.WING_OUTLINE)
        for x in np.linspace(poly[:, 0].min(), poly[:, 0].max(), 14):
            for y in np.linspace(poly[:, 1].min(), poly[:, 1].max(), 12):
                if _inside(np.array([[x, y]]), poly)[0]:
                    pts.append(np.array((o + u * x + v * y)[:]))
        for x, y in _resample(poly, 0.01):
            pts.append(np.array((o + u * x + v * y)[:]))
    o, s_, w, _n, _L = F.tail_axes()
    for x, y in _resample(np.array(tail_outline()), 0.01):
        pts.append(np.array((o + s_ * x + w * y)[:]))
    for line in F.CROWN + [F.CURL]:
        for a_, b_ in zip(line[:-1], line[1:]):
            for t in np.linspace(0, 1, 5):
                pts.append(np.array(a_) + (np.array(b_) - np.array(a_)) * t)
    for lk in F.licks():
        pts += [np.array(q) for q in lk['pts'][2:]]
    return np.array(pts)


def _eye_rays() -> list[tuple[np.ndarray, np.ndarray]]:
    """Segments from each eye out toward the review's cameras (front, the sides, three-quarter): no spark may hang in
    front of an eye from those views (review 1: one crossed the top of an eye in the side view)."""
    out = []
    for s in (1, -1):
        c = np.array(F.EYE_C[s][:])
        for d in ((0.0, -1.0, 0.0), (s, 0.0, 0.0), (0.57 * s, -0.82, 0.0), (0.82 * s, -0.57, 0.0), (0.0, -0.94, 0.34)):
            d = np.array(d) / np.linalg.norm(d)
            out.append((c, c + d * 0.45))
    return out


VIEWS = [np.array((math.sin(math.radians(a)) * math.cos(math.radians(10)), -math.cos(math.radians(a)) * math.cos(math.radians(10)),
                   math.sin(math.radians(10)))) for a in range(0, 360, 45)]


def _over_body(c: np.ndarray) -> list[int]:
    """The views (of VIEWS) in which a spark at c hangs over the ball (in front of it, inside its outline)."""
    d = c - np.array(F.C0)
    out = []
    for k, v in enumerate(VIEWS):
        along = float(d @ v)
        if along > 0 and float(np.linalg.norm(d - v * along)) < 0.215:
            out.append(k)
    return out


def _bolt(c, along, across, across2, length, rng) -> list[np.ndarray]:
    """A bolt round c: 3 or 4 strokes of varied length, zigzagging at varied angles (and a little out of their plane),
    and now and then a short fork from its second bend. Returns its polylines (the bolt, then any fork)."""
    n = int(rng.integers(3, 5))
    lens = rng.uniform(0.5, 1.5, n)
    lens = lens / lens.sum() * length
    pts = [np.zeros(3)]
    for i in range(n):
        th = math.radians(float(rng.uniform(32, 62)))
        ph = float(rng.uniform(-0.5, 0.5))
        side = (across * math.cos(ph) + across2 * math.sin(ph)) * (1 if i % 2 == 0 else -1)
        d = along * math.cos(th) + side * math.sin(th)
        pts.append(pts[-1] + d * lens[i])
    P = np.array(pts)
    P = P - P.mean(axis=0) + c
    out = [P]
    if rng.uniform() < 0.3:
        b0 = P[2]
        fd = P[3] - P[2]
        fd = fd / np.linalg.norm(fd)
        turn = across2 if rng.uniform() < 0.5 else -across2
        f1 = b0 + (fd * 0.55 + turn * 0.83) * length * 0.18
        f2 = f1 + (fd * 0.9 - turn * 0.44) * length * 0.14
        out.append(np.array([b0, f1, f2]))
    return out


def spark_layout() -> list[list[np.ndarray]]:
    """Each spark's polylines, chosen from a fixed spread of candidates, kept where it clears everything."""
    if _LAYOUT:
        return _LAYOUT
    rng = np.random.default_rng(3516)
    cl = _clutter()
    rays = _eye_rays()
    U = F._fib(320)
    U += rng.normal(0, 0.05, U.shape)
    U /= np.linalg.norm(U, axis=1)[:, None]
    order = rng.permutation(len(U))
    views = [0] * len(VIEWS)
    centres: list = []
    for i in order:
        u = U[i]
        if F.face_angle((np.array(F.C0) + u * 0.2)[None])[0] < 62:
            continue                                   # never in front of the face (nor across an eye from the side)
        if F.dir_angle((np.array(F.C0) + u * 0.2)[None], F.CORE_BACK)[0] < 45:
            continue                                   # never over the back core (it washed to white there)
        rho = float(F.rho_unit(u[None])[0])
        a = np.cross(u, (0.0, 0.0, 1.0) if abs(u[2]) < 0.9 else (1.0, 0.0, 0.0))
        a /= np.linalg.norm(a)
        b = np.cross(u, a)
        tr = float(rng.uniform(0, math.pi))
        along = a * math.cos(tr) + b * math.sin(tr)
        across = u * 0.75 + np.cross(u, along) * 0.66
        across /= np.linalg.norm(across)
        across2 = np.cross(along, across)
        length = float(rng.uniform(*SPARK_LEN))
        for shell in (float(rng.uniform(1.18, 1.36)), 1.48):
            c = np.array(F.C0) + u * rho * shell
            lines = _bolt(c, along, across, across2, length, rng)
            dense = np.concatenate([Q[j] + (Q[j + 1] - Q[j]) * t[:, None] for Q in lines for j in range(len(Q) - 1)
                                    for t in [np.linspace(0, 1, 6)]])
            if np.min(np.linalg.norm(dense[:, None, :] - cl[None], axis=2)) < 0.03:
                continue
            if min(float(np.min(np.linalg.norm(dense - (a_ + np.clip(((dense - a_) @ (b_ - a_)) / float((b_ - a_) @ (b_ - a_)), 0, 1)[:, None]
                                                         * (b_ - a_)), axis=1))) for a_, b_ in rays) < 0.06:
                continue
            if centres and min(float(np.linalg.norm(c - q)) for q in centres) < 0.085:
                continue
            if float(np.min(F.outside(dense))) < 0.035:
                continue                               # off the fur
            if float(dense[:, 2].min()) < 0.1:
                continue                               # the ball hovers only 5 cm up: none under it (they hit the ground)
            over = _over_body(c)
            if any(views[k] >= VIEW_LIMIT for k in over):
                continue
            for k in over:
                views[k] += 1
            centres.append(c)
            _LAYOUT.append(lines)
            break
        if len(_LAYOUT) == N_SPARKS:
            break
    return _LAYOUT


def spark_points(i: int) -> np.ndarray:
    return spark_layout()[i][0]


def _tube(P: np.ndarray, radius: np.ndarray, sides: int):
    """A tube along P with a pointed cap at each end (the caps' tips sit a little past the ends: never zero area)."""
    k = len(P)
    T = np.zeros_like(P)
    T[1:-1] = P[2:] - P[:-2]
    T[0], T[-1] = P[1] - P[0], P[-1] - P[-2]
    T /= np.linalg.norm(T, axis=1)[:, None]
    h = np.array((0.0, 0.0, 1.0)) if abs(T[0, 2]) < 0.9 else np.array((1.0, 0.0, 0.0))
    Nn = np.zeros_like(P)
    nn = h - T[0] * float(h @ T[0])
    Nn[0] = nn / np.linalg.norm(nn)
    for i in range(1, k):
        nn = Nn[i - 1] - T[i] * float(Nn[i - 1] @ T[i])
        Nn[i] = nn / max(np.linalg.norm(nn), 1e-12)
    B = np.cross(T, Nn)
    ang = np.arange(sides) / sides * 2 * np.pi
    ring = P[:, None, :] + radius[:, None, None] * (np.cos(ang)[None, :, None] * Nn[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :])
    verts = list(ring.reshape(-1, 3))
    faces = []
    for i in range(k - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            faces.append((i * sides + j, i * sides + j2, (i + 1) * sides + j2, (i + 1) * sides + j))
    tip0 = P[0] - T[0] * radius[0] * 2.2
    tip1 = P[-1] + T[-1] * radius[-1] * 2.2
    i0, i1 = len(verts), len(verts) + 1
    verts += [tip0, tip1]
    for j in range(sides):
        j2 = (j + 1) % sides
        faces.append((j2, j, i0))
        faces.append(((k - 1) * sides + j, (k - 1) * sides + j2, i1))
    return np.array(verts), faces


def sparks(high: bool):
    """Every spark in one object (rigid on its own bone, prop.sparks), each face turned away from its centre line."""
    allv, allf, sid, st = [], [], [], []
    base = 0
    sides = 8 if high else 6
    for i, lines in enumerate(spark_layout()):
        for li, P in enumerate(lines):
            # extra points at each corner keep the tube from pinching where the bolt turns
            fine = [P[0]]
            for a, b in zip(P[:-1], P[1:]):
                for t in (0.5, 1.0):
                    fine.append(a + (b - a) * t)
            P = np.array(fine)
            n = len(P)
            tt = np.linspace(0, 1, n)
            # thin points at both ends (never zero), thickest a little before the middle; a fork thinner still
            r = SPARK_R[0] + SPARK_R[1] * (0.55 if li else 1.0) * np.sin(np.pi * tt) ** 0.7
            v, f = _tube(P, r, sides)
            allv.append(v)
            allf += [tuple(x + base for x in ff) for ff in f]
            sid.append(np.full(len(v), float(i)))
            st.append(np.concatenate([np.repeat(tt * (0.5 if li else 1.0), sides), [0.0, 1.0]]))
            base += len(v)
    ob = S.sheet_object(f"{'hi' if high else 'lo'}_sparks", np.concatenate(allv), allf)
    S.add_attr(ob, 'part', np.full(base, float(SPARK)))
    S.add_attr(ob, 'spark_id', np.concatenate(sid))
    S.add_attr(ob, 'su', np.concatenate(st))
    S.add_attr(ob, 'ed', np.zeros(base))
    S.add_attr(ob, 'face', np.zeros(base))
    S.add_attr(ob, 'side', np.zeros(base))
    segs = [(a, b) for lines in spark_layout() for P in lines for a, b in zip(P[:-1], P[1:])]

    def inside(c):
        # the nearest point on any spark's centre line (the sparks lie far apart against their thickness)
        best = np.full(len(c), np.inf)
        bp = np.zeros_like(c)
        for a, b in segs:
            ab = b - a
            t = np.clip(((c - a) @ ab) / float(ab @ ab), 0, 1)
            pt = a + t[:, None] * ab
            d = np.linalg.norm(c - pt, axis=1)
            better = d < best
            best[better] = d[better]
            bp[better] = pt[better]
        return bp
    S.orient_away(ob, inside)
    C.log(f"{ob.name}: {len(ob.data.polygons)} faces, {len(spark_layout())} sparks")
    return ob


def objects(high: bool) -> list:
    return [wing(1, high), wing(-1, high), tail(high), sparks(high)]
