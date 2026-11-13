"""Starhowl Ultra: the aurora mane, the tail's aurora locks and the tail star (the recipe's `build_fins`).

The mane is long, silky, wavy locks round the neck and shoulders (chatgpt/monsters/06-starhowl: the hero, 2-turnaround,
4-details panel 5), teal shading to rose toward the tips; the tail's lower and outer plume carries shorter locks of the
same kind, and its tip a puffy five-pointed star. All of them are `fin` meshes in the game (double-sided, a soft glow of
their own colour, spring bones), baked from a high version with strand grooves.

Every lock is a curve grown from a root on the body: the roots and the drape come from an analytic signed distance to
the recipe's parts (`sdf`), so the high and low versions are the same locks. A lock is a ribbon with an arched
cross-section that faces away from the body.

Attributes on every sheet: `fan` = (u along the lock 0..1, θ / π round the neck or along the tail, the lock's layer),
`fin_part` = 10 mane · 20 tail lock · 30 star, `lrand` = the lock's random 0..1, `across` = −1..1 across the ribbon.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib.surface import add_attr, norm, smooth

MANE, CROWN, RUFF, TAIL_LOCK, STAR = 10.0, 11.0, 12.0, 20.0, 30.0

# ----------------------------------------------------------------------------- the analytic body (set by the recipe)
_SHAPES: list = []


def configure(parts) -> None:
    """Take the recipe's Part list (spheres with scale and rotation, capsules and tubes)."""
    from mathutils import Euler
    _SHAPES.clear()
    for p in parts:
        for side in ((1, -1) if p.mirror else (1,)):
            if p.kind in ('sphere', 'fin', 'paddle'):
                loc = np.array(p.loc, float)
                rot = np.array(Euler([math.radians(a) for a in p.rot], 'XYZ').to_matrix(), float)
                if side < 0:
                    loc[0] = -loc[0]
                    mirror = np.diag([-1.0, 1.0, 1.0])
                    rot = mirror @ rot @ mirror
                r = np.array(p.scale, float) * p.radius
                _SHAPES.append(('ell', loc, rot, r))
            elif p.kind in ('capsule', 'tube'):
                a, b = np.array(p.loc, float), np.array(p.to or p.loc, float)
                if side < 0:
                    a[0], b[0] = -a[0], -b[0]
                r2 = p.r2 if (p.kind == 'tube' and p.r2 is not None) else p.radius
                _SHAPES.append(('cap', a, b, (p.radius, r2)))


def sdf(p: np.ndarray) -> np.ndarray:
    """Approximate signed distance to the union of the parts (negative inside)."""
    p = np.atleast_2d(p)
    d = np.full(len(p), 9.0)
    for kind, a, b, c in _SHAPES:
        if kind == 'ell':
            q = (p - a) @ b                       # into the ellipsoid's frame (rows are its axes' coordinates)
            k = np.linalg.norm(q / c, axis=1)
            dd = (k - 1.0) * np.min(c)
        else:
            ab = b - a
            L2 = max(float(ab @ ab), 1e-12)
            t = np.clip(((p - a) @ ab) / L2, 0.0, 1.0)
            r = c[0] + (c[1] - c[0]) * t
            dd = np.linalg.norm(p - (a + t[:, None] * ab), axis=1) - r
        d = np.minimum(d, dd)
    return d


def sdf_grad(p: np.ndarray, h: float = 1e-3) -> np.ndarray:
    g = np.zeros_like(p)
    for i in range(3):
        e = np.zeros(3)
        e[i] = h
        g[:, i] = (sdf(p + e) - sdf(p - e)) / (2 * h)
    return norm(g)


def march(origin: np.ndarray, direction: np.ndarray, sink: float = 0.004, far: float = 0.6) -> np.ndarray:
    """From inside the body, step out along `direction` to the surface (sunk `sink`)."""
    t = np.zeros(len(origin))
    for _ in range(80):
        d = sdf(origin + direction * t[:, None])
        t = np.where(d < 0, t + np.maximum(-d * 0.8, 0.002), t)
    for _ in range(12):                            # back off to the surface (bisect)
        d = sdf(origin + direction * t[:, None])
        t = t - (d + sink) * 0.7
    return origin + direction * np.clip(t, 0, far)[:, None]


# ----------------------------------------------------------------------------- one lock: a curve and its ribbon
def grow(root: np.ndarray, out: np.ndarray, fall: np.ndarray, L: np.ndarray, n: int, clear: np.ndarray,
         waves: np.ndarray, amp: np.ndarray, phase: np.ndarray, curl: np.ndarray, bend: float = 0.35,
         hook: np.ndarray | None = None, hook_out: float = 0.6) -> tuple[np.ndarray, np.ndarray]:
    """Many locks at once (k of them): each centre line (k × n × 3) and the body's outward direction along it. A lock
    leaves the skin along `out`, turns to `fall` over the first `bend` of its length, waves sideways, curls its tip
    out, and drapes over the body (pushed `clear[:, 0]` → `clear[:, 1]` off the skin)."""
    out = norm(out)
    fall = norm(fall)
    k = len(root)
    P = np.zeros((k, n, 3))
    O = np.zeros((k, n, 3))
    P[:, 0], O[:, 0] = root, out
    ds = (L / (n - 1))[:, None]
    p = root.copy()
    for j in range(1, n):
        s = j / (n - 1)
        b = float(smooth(0.0, bend, s))
        d = out * (1 - b) + fall * b
        # the tip flicks out, away from the body
        g = sdf_grad(p)
        horiz = g * np.array((1.0, 1.0, 0.0))
        d = d + norm(horiz) * (curl * float(smooth(0.55, 1.0, s)))[:, None]
        p = p + norm(d) * ds
        c = clear[:, 0] + (clear[:, 1] - clear[:, 0]) * float(smooth(0.0, 0.5, s))
        for _ in range(3):
            dist = sdf(p)
            push = np.maximum(c - dist, 0.0)
            if not push.any():
                break
            p = p + sdf_grad(p) * push[:, None]
        P[:, j] = p
        O[:, j] = sdf_grad(p)
    # smooth the drape (the pushes off the body kink it) and the facing (the union's gradient jumps between parts)
    for _ in range(4):
        P[:, 1:-1] = 0.25 * P[:, :-2] + 0.5 * P[:, 1:-1] + 0.25 * P[:, 2:]
        P[:, -1] = 0.5 * P[:, -1] + 0.5 * (2 * P[:, -2] - P[:, -3])
    for _ in range(10):
        O[:, 1:-1] = norm(0.25 * O[:, :-2] + 0.5 * O[:, 1:-1] + 0.25 * O[:, 2:])
        O[:, -1] = O[:, -2]
    # the wave: sideways, growing from the root
    T = norm(np.gradient(P, axis=1))
    A = norm(np.cross(T, O))
    s = np.linspace(0, 1, n)[None, :]
    w = amp[:, None] * np.sin(2 * math.pi * waves[:, None] * s + phase[:, None]) * smooth(0.0, 0.3, s)
    P = P + A * w[..., None]
    if hook is not None:
        # round 3: the tip curls (sideways, the way its last wave leans, and out from the body)
        lean = np.sign(np.sin(2 * math.pi * waves + phase))[:, None, None]
        h = (hook[:, None] * smooth(0.7, 1.0, s) ** 2)[..., None]
        P = P + (A * lean * 0.8 + O * hook_out) * h
    return P, O


def ribbon(P: np.ndarray, O: np.ndarray, width: float, thick: float, rows: int, cols: int, twist: float, rng,
           relief: float = 0.0, strands: int = 0, tip_round: float = 0.6):
    """A ribbon along the curve P (resampled to `rows` + 1 points): `cols` + 1 vertices across with an arched
    cross-section facing out (O), tapering to a point. Returns (verts (rows+1)·(cols+1)+1 × 3, faces, u, across)."""
    # resample by arc length
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    acc = np.concatenate([[0], np.cumsum(seg)])
    tt = np.linspace(0, acc[-1], rows + 2)[:-1]
    Q = np.stack([np.interp(tt, acc, P[:, i]) for i in range(3)], axis=1)
    Oq = norm(np.stack([np.interp(tt, acc, O[:, i]) for i in range(3)], axis=1))
    tip = P[-1]
    u = tt / max(acc[-1], 1e-9)
    T = norm(np.gradient(np.vstack([Q, tip[None]]), axis=0)[:-1])
    A = norm(np.cross(T, Oq))
    N = norm(np.cross(A, T))
    flip = (N * Oq).sum(1) < 0
    N[flip] *= -1
    A[flip] *= -1
    ang = twist * np.sin(math.pi * u) * (0.6 + 0.4 * rng.random())
    A2 = A * np.cos(ang)[:, None] + N * np.sin(ang)[:, None]
    N2 = norm(np.cross(A2, T))
    N2 = np.where(((N2 * Oq).sum(1) < 0)[:, None], -N2, N2)
    cap = np.sqrt(np.clip(1.0 - ((np.maximum(u, 0.78) - 0.78) / 0.22) ** 2, 0.0, 1.0))
    hw = 0.5 * width * (0.92 + 0.08 * smooth(0.0, 0.1, u)) * (1.0 - 0.45 * smooth(0.2, 0.85, u)) * cap
    hh = thick * (1.0 - 0.6 * smooth(0.5, 1.0, u))
    xs = np.linspace(-1.0, 1.0, cols + 1)
    verts, us, acr = [], [], []
    for j in range(rows + 1):
        for x in xs:
            arch = max(0.0, 1.0 - x * x) ** 0.6
            h = hh[j] * arch
            if relief > 0 and strands > 0:
                h += relief * (0.5 + 0.5 * math.cos(x * math.pi * strands)) * arch * (1 - 0.6 * u[j])
            verts.append(Q[j] + A2[j] * (x * hw[j]) + N2[j] * h)
            us.append(u[j])
            acr.append(x)
    verts.append(tip)
    us.append(1.0)
    acr.append(0.0)
    faces = []
    w = cols + 1
    for j in range(rows):
        for i in range(cols):
            faces.append((j * w + i, j * w + i + 1, (j + 1) * w + i + 1, (j + 1) * w + i))
    t_i = len(verts) - 1
    for i in range(cols):
        faces.append((rows * w + i, rows * w + i + 1, t_i))
    return np.array(verts), faces, np.array(us), np.array(acr)


def sheet(name: str, ribbons: list, attrs: dict) -> bpy.types.Object:
    """One object from many ribbons; `attrs` = {name: [one per-vertex array per ribbon]} (vertex order is kept)."""
    bm = bmesh.new()
    uv_l = bm.loops.layers.uv.new('UVMap')
    for V, F, U, X in ribbons:
        vs = [bm.verts.new(v) for v in V]
        for f in F:
            try:
                face = bm.faces.new([vs[i] for i in f])
            except ValueError:
                continue
            for lp, i in zip(face.loops, f):
                lp[uv_l].uv = (0.5 + 0.5 * X[i], U[i])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    for k, chunks in attrs.items():
        add_attr(ob, k, np.concatenate(chunks, axis=0))
    return ob


# ----------------------------------------------------------------------------- the mane
NECK_A = np.array((0.0, -0.395, 1.0))      # the neck axis: under the back of the skull …
NECK_B = np.array((0.0, -0.245, 0.705))      # … down to the withers and the top of the chest
DORSAL = np.array((0.0, 0.62, 0.78))         # the neck's "up" (toward the crest), before orthogonalising


def neck_frame():
    ax = NECK_B - NECK_A
    ax /= np.linalg.norm(ax)
    up = DORSAL - ax * (DORSAL @ ax)
    up /= np.linalg.norm(up)
    side = np.cross(ax, up)          # +X for this axis (down-back) and up (back-up)
    if side[0] < 0:
        side = -side
    return ax, up, side


# Round 2 (review: a stiff apron of blades over the chest): the hero's lion-like ruff.
#  - the RUFF: locks rooted in a ring behind the cheeks and the ears, framing the face and flaring wide at head height;
#  - the NECK: locks down the sides and the crest of the neck to the withers, sweeping back over the shoulders; none
#    round the throat and the chest (the mane parts there and shows the lavender chest ruff); they end about the elbows;
#  - the CROWN: a small teal tuft between the ears.
T_MAX = 1.18
HEAD_RING = (np.array((0.0, -0.42, 1.0)), np.array((0.0, -0.405, 0.965)))    # two rings' centres, inside the head
RUFF_PER_RING = 26
RUFF_PHI = (0.15, 0.7)          # |φ| / π: from just off the top (the crown tuft is between the ears) to under the jaw
NECK_STRATA = 9
NECK_PER_STRATUM = 17
NECK_THETA = 0.78               # |θ| / π covered down the neck (the throat and the chest stay clear)
NECK_LEN = ([0.12, 0.5, 0.9, T_MAX], [0.3, 0.36, 0.33, 0.29])
MANE_W = (0.036, 0.054)
CROWN_LOCKS = [(0.0, -0.385, 0.0, 0.12), (-0.018, -0.378, -18.0, 0.105), (0.018, -0.378, 18.0, 0.105), (-0.032, -0.37, -32.0, 0.09),
         (0.033, -0.37, 32.0, 0.09), (0.0, -0.36, 0.0, 0.1), (-0.012, -0.395, -10.0, 0.085), (0.012, -0.395, 10.0, 0.085)]


_CACHE: dict = {}


def _grow_rows(rows: list[dict], n: int, bend: float):
    roots = march(np.array([r['centre'] for r in rows]), np.array([r['d'] for r in rows]))
    P, O = grow(roots, sdf_grad(roots), np.array([r['fall'] for r in rows]), np.array([r['L'] for r in rows]), n,
                np.array([r['clear'] for r in rows]), np.array([r['waves'] for r in rows]), np.array([r['amp'] for r in rows]),
                np.array([r['phase'] for r in rows]), np.array([r['curl'] for r in rows]), bend=bend,
                hook=np.array([r.get('hook', 0.0) for r in rows]))
    return [(P[i], O[i], r['W'], r['th'], r['layer'], r['r']) for i, r in enumerate(rows)]


def mane_locks(seed: int = 6, quick: bool = False):
    """Every mane lock (the ruff, then the neck): (curve, outward dirs, width, θ/π, layer, rand). θ = 0 is the top /
    back of the neck (the maneB chain), ±0.5 the left / right sides. Cached (the high and low builds share them)."""
    key = ('mane', seed, quick)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(seed)
    k_q = 0.5 if quick else 1.0
    # the ruff: S-curved locks flaring out and back from behind the cheeks and the ears
    ruff = []
    for ri, centre in enumerate(HEAD_RING):
        n = int(RUFF_PER_RING * k_q)
        offs = rng.random()
        for k in range(n):
            f = (k + offs + rng.normal(0, 0.15)) / n
            phi = math.pi * (RUFF_PHI[0] + (RUFF_PHI[1] - RUFF_PHI[0]) * f)
            phi *= 1 if k % 2 == 0 else -1
            sp, cp = math.sin(phi), math.cos(phi)
            d = np.array((sp, 0.22 + 0.5 * max(cp, 0.0), cp))
            d /= np.linalg.norm(d)
            fall = np.array((0.64 * np.sign(sp) * abs(sp), 0.28 + 0.45 * max(cp, 0.0), -0.56 - 0.3 * max(-cp, 0.0)))
            ruff.append(dict(centre=centre + rng.normal(0, 0.006, 3), d=d, fall=fall, L=(0.25 + 0.08 * rng.random()) * (1.0 + 0.1 * ri),
                             clear=(0.006, 0.045 - 0.012 * ri), waves=1.8 + 0.4 * rng.random(), amp=0.026 + 0.012 * rng.random(),
                             hook=0.03 + 0.015 * rng.random(),
                             phase=rng.uniform(0, 2 * math.pi), curl=0.45 + 0.4 * rng.random(), W=MANE_W[0] + (MANE_W[1] - MANE_W[0]) * rng.random(),
                             th=phi / math.pi, layer=0.5 + 0.3 * ri, r=float(rng.random())))
    # the neck: down the sides and the crest to the withers, sweeping back over the shoulders
    ax, up, side = neck_frame()
    neck = []
    for si in range(NECK_STRATA):
        n = int(NECK_PER_STRATUM * k_q)
        offs = rng.random()
        for k in range(n):
            t = 0.12 + (T_MAX - 0.12) * (si + rng.random()) / NECK_STRATA
            th = math.pi * NECK_THETA * (2.0 * (k + offs + rng.normal(0, 0.15)) / n - 1.0)
            th = max(-math.pi * NECK_THETA, min(math.pi * NECK_THETA, th))
            if t > 1.02 and abs(th) > 0.55 * math.pi:
                continue
            d = up * math.cos(th) + side * math.sin(th)
            cth, sth = math.cos(th), math.sin(th)
            dorsal = np.array((0.0, 0.95, -0.3))
            lateral = np.array((0.42 * np.sign(sth), 0.5, -0.76))
            fall = dorsal * max(cth, 0) ** 1.5 + lateral * abs(sth) + np.array((0.0, -0.1, -1.0)) * max(-cth, 0) ** 1.5
            L = float(np.interp(t, *NECK_LEN)) * (0.85 + 0.3 * rng.random())
            neck.append(dict(centre=NECK_A + (NECK_B - NECK_A) * t, d=d, fall=fall, L=L, clear=(0.006, 0.01 + 0.03 * (1.0 - t / T_MAX) ** 1.2),
                             waves=1.8 + 0.4 * rng.random(), amp=0.024 + 0.012 * rng.random(), phase=rng.uniform(0, 2 * math.pi),
                             hook=0.03 + 0.015 * rng.random(),
                             curl=0.3 + 0.35 * rng.random(), W=MANE_W[0] + (MANE_W[1] - MANE_W[0]) * rng.random(), th=th / math.pi,
                             layer=6.0 * t / T_MAX, r=float(rng.random())))
    out = _grow_rows(ruff, 22, 0.22) + _grow_rows(neck, 22, 0.18)
    C.log(f'mane: {len(out)} locks ({len(ruff)} in the ruff, {len(neck)} down the neck)')
    _CACHE[key] = out
    return out


def ruff_locks(seed: int = 14, quick: bool = False):
    """Round 3 (review: a long, bare, thin neck; an alpaca between two curtains): a thick lavender ruff wrapping the
    throat and the upper chest under the jaw, so the chin sits on it."""
    key = ('ruff', seed, quick)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(seed)
    ax, up, side = neck_frame()
    rows = []
    strata, per = 3, (13 if not quick else 7)
    for si in range(strata):
        offs = rng.random()
        for k in range(per):
            t = 0.0 + 0.5 * (si + rng.random()) / strata
            f = (k + offs + rng.normal(0, 0.15)) / per
            th = math.pi * (0.6 + 0.4 * f) * (1 if k % 2 == 0 else -1)
            d = up * math.cos(th) + side * math.sin(th)
            fall = np.array((0.28 * math.sin(th), -0.3, -1.0))
            rows.append(dict(centre=NECK_A + (NECK_B - NECK_A) * t, d=d, fall=fall, L=0.07 + 0.035 * rng.random(),
                             clear=(0.006, 0.01 + 0.016 * (1.0 - si / strata)), waves=0.6 + 0.3 * rng.random(), amp=0.004,
                             phase=rng.uniform(0, 2 * math.pi), curl=0.08, W=0.066 + 0.016 * rng.random(), th=th / math.pi,
                             layer=6.0 * max(t, 0.0) / T_MAX, r=float(rng.random()), hook=0.0))
    out = _grow_rows(rows, 12, 0.25)
    C.log(f'ruff: {len(out)} locks')
    _CACHE[key] = out
    return out


def crown_locks(seed: int = 12):
    """The teal tuft between the ears: short locks standing up and back, curling over."""
    key = ('crown', seed)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(seed)
    rows = []
    for x, y, fan_deg, L in CROWN_LOCKS:
        a = math.radians(fan_deg)
        rows.append(dict(centre=np.array((x * 0.5, y, 1.02)), d=np.array((0.0, 0.05, 1.0)),
                         fall=np.array((math.sin(a) * 0.6, 0.75, 0.55)), L=L * (0.9 + 0.2 * rng.random()), clear=(0.004, 0.012),
                         waves=0.8, amp=0.008, phase=rng.uniform(0, 2 * math.pi), curl=0.0, W=0.03 * (0.85 + 0.3 * rng.random()),
                         th=0.0, layer=0.0, r=float(rng.random())))
    out = _grow_rows(rows, 14, 0.35)
    _CACHE[key] = out
    return out


# ----------------------------------------------------------------------------- the tail: aurora locks and the star
TAIL_PTS: list = []          # set by the recipe (the spine's points, base → tip)
STAR_C = np.zeros(3)
STAR_R = (0.098, 0.043, 0.027)    # outer radius, inner radius, half thickness at the centre


def configure_tail(points, star_c) -> None:
    TAIL_PTS[:] = [np.array(p, float) for p in points]
    STAR_C[:] = np.array(star_c, float)


def spine(t: float) -> tuple[np.ndarray, np.ndarray]:
    """A point on the tail's spine at t 0..1 and its unit tangent."""
    pts = np.array(TAIL_PTS)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    acc = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()
    p = np.array([np.interp(t, acc, pts[:, i]) for i in range(3)])
    h = 0.01
    a = np.array([np.interp(max(0, t - h), acc, pts[:, i]) for i in range(3)])
    b = np.array([np.interp(min(1, t + h), acc, pts[:, i]) for i in range(3)])
    d = b - a
    return p, d / np.linalg.norm(d)


def tail_locks(seed: int = 9, quick: bool = False):
    """The aurora locks on the lower and outer plume: rows along the spine, fanning round its underside and, toward
    the tip, all the way round; they comb toward the tip and hang down a little."""
    key = ('tail', seed, quick)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(seed)
    # round 2 (review: a thin stalk with a small tuft, a third of the reference plume): the plume is these locks, all
    # round the spine from the base to the tip, longest in the middle; base rows lie over the rows after them
    rows_ = [(0.05, 14, 0.15), (0.14, 18, 0.21), (0.24, 20, 0.26), (0.35, 22, 0.3), (0.47, 22, 0.32), (0.59, 22, 0.31),
             (0.71, 22, 0.27), (0.82, 22, 0.21), (0.91, 18, 0.15), (0.97, 14, 0.12), (1.0, 9, 0.09)]
    rows = []
    for li, (t, count, L) in enumerate(rows_):
        if quick:
            count = max(6, count // 2)
        c, tg = spine(t)
        upv = np.array((0.0, 0.0, 1.0)) - tg * tg[2]
        upv /= np.linalg.norm(upv)
        sd = np.cross(tg, upv)
        offs = rng.random()
        for k in range(count):
            phi = 2 * math.pi * (k + offs + rng.normal(0, 0.12)) / count
            d = upv * math.cos(phi) + sd * math.sin(phi)
            fall = tg * 0.85 + d * 0.42 - upv * 0.15
            rows.append(dict(base=c, d=d, fall=fall, L=L * (0.85 + 0.3 * rng.random()),
                             clear=(0.005, 0.014 + 0.03 * (1.0 - t)), waves=1.0 + 0.4 * rng.random(),
                             phase=rng.uniform(0, 2 * math.pi), W=0.064 * (0.8 + 0.4 * rng.random()), phi=phi / math.pi,
                             layer=float(li) + t, r=float(rng.random())))
    k = len(rows)
    roots = march(np.array([r['base'] for r in rows]), np.array([r['d'] for r in rows]))
    P, O = grow(roots, sdf_grad(roots), np.array([r['fall'] for r in rows]), np.array([r['L'] for r in rows]), 16,
                np.array([r['clear'] for r in rows]), np.array([r['waves'] for r in rows]), np.full(k, 0.016),
                np.array([r['phase'] for r in rows]), np.full(k, 0.1), bend=0.15, hook=np.full(k, 0.022))
    out = [(P[i], O[i], r['W'], r['phi'], r['layer'], r['r']) for i, r in enumerate(rows)]
    C.log(f'tail: {len(out)} aurora locks')
    _CACHE[key] = out
    return out


def star_mesh(name: str, high: bool, facing: str = 'x') -> bpy.types.Object:
    """A puffy five-pointed star at the tail tip, its faces looking left and right (facing 'x') or backward (facing
    'y'; round 2: the two cross, so the star reads from the sides and from behind)."""
    ro, ri, th = STAR_R
    n_ring = 3 if not high else 10
    sub = 1 if not high else 6                  # extra points along each edge of the outline
    outline = []
    for k in range(10):
        a0 = math.pi / 2 + k * math.pi / 5
        a1 = math.pi / 2 + (k + 1) * math.pi / 5
        r0 = ro if k % 2 == 0 else ri
        r1 = ro if (k + 1) % 2 == 0 else ri
        for j in range(sub):
            f = j / sub
            a = a0 + (a1 - a0) * f
            r = r0 + (r1 - r0) * f
            outline.append((r * math.cos(a), r * math.sin(a)))
    outline = np.array(outline)
    bm = bmesh.new()
    rings = []
    for side in (1, -1):
        rows = []
        for j in range(n_ring + 1):
            k = j / n_ring                          # 0 = the outline, 1 = the centre: a puffy dome on each face
            pts2 = outline * (1 - k)
            h = th * math.sqrt(max(0.0, 1 - (1 - k) ** 2)) * 0.92 + 0.0035
            rows.append([(side * h, float(p[0]), float(p[1])) for p in pts2])
        rings.append(rows)
    verts = {}
    V = []

    def vid(p):
        key = tuple(round(x, 6) for x in p)
        if key not in verts:
            verts[key] = bm.verts.new(p)
            V.append(verts[key])
        return verts[key]
    m = len(outline)
    for si, side in enumerate((1, -1)):
        rows = rings[si]
        for j in range(n_ring):
            for i in range(m):
                a, b = rows[j][i], rows[j][(i + 1) % m]
                c, d = rows[j + 1][(i + 1) % m], rows[j + 1][i]
                quad = [vid(a), vid(b), vid(c), vid(d)]
                if side < 0:
                    quad.reverse()
                uniq = list(dict.fromkeys(quad))
                if len(uniq) >= 3:
                    try:
                        bm.faces.new(uniq)
                    except ValueError:
                        pass
    # the rim joins the two faces round the outline
    for i in range(m):
        a, b = rings[0][0][i], rings[0][0][(i + 1) % m]
        c, d = rings[1][0][(i + 1) % m], rings[1][0][i]
        try:
            bm.faces.new([vid(a), vid(d), vid(c), vid(b)])
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if high:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=1, use_grid_fill=True)
    # place: centre, the star's own up (+Z) tilted back along the tail
    _p, tg = spine(1.0)
    for v in bm.verts:
        x, y, z = v.co
        if facing == 'x':
            v.co = (x + STAR_C[0], float(STAR_C[1] + y), float(STAR_C[2] + z))
        else:
            v.co = (float(STAR_C[0] - y), float(STAR_C[1] + x), float(STAR_C[2] + z))
    uv_l = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for lp in f.loops:
            h = (lp.vert.co.y - STAR_C[1]) if facing == 'x' else (lp.vert.co.x - STAR_C[0])
            lp[uv_l].uv = (0.5 + h / (2 * ro), 0.5 + (lp.vert.co.z - STAR_C[2]) / (2 * ro))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    co = np.array([v.co[:] for v in me.vertices])
    r = np.linalg.norm((co - STAR_C)[:, 1:] if facing == 'x' else (co - STAR_C)[:, [0, 2]], axis=1) / ro
    add_attr(ob, 'fan', np.stack([np.clip(r, 0, 1), np.zeros(len(co)), np.zeros(len(co))], axis=1))
    add_attr(ob, 'fin_part', np.full(len(co), STAR))
    add_attr(ob, 'lrand', np.full(len(co), 0.5))
    add_attr(ob, 'across', np.zeros(len(co)))
    return ob


# ----------------------------------------------------------------------------- the fins
FIN_LOCKS = False      # round 4: the mane, the ruff and the plume are a sculpted volume with fur cards; only the star is a fin


def build(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    if not FIN_LOCKS:
        return [star_mesh(f'{tag}_star', high, 'x'), star_mesh(f'{tag}_star2', high, 'y')]
    objs = []
    rng = np.random.default_rng(31)
    mane_rc = (12, 3) if not high else ((56, 16) if not quick else (24, 8))
    for part, name, locks, rows_cols, thick in ((MANE, 'mane', mane_locks(quick=quick), mane_rc, 0.0095),
                                                (CROWN, 'crown', crown_locks(), mane_rc, 0.008),
                                                (RUFF, 'ruff', ruff_locks(quick=quick), (6, 3) if not high else ((20, 12) if not quick else (12, 6)), 0.012),
                                                (TAIL_LOCK, 'taillocks', tail_locks(quick=quick),
                                                 (9, 3) if not high else ((36, 12) if not quick else (16, 6)), 0.009)):
        rows, cols = rows_cols
        ribs, fan, lr = [], [], []
        for P, O, W, th, layer, rnd in locks:
            V, F, U, X = ribbon(P, O, W, thick, rows, cols, 0.18, rng, relief=0.0024 if high else 0.0, strands=6 if high else 0)
            ribs.append((V, F, U, X))
            fan.append(np.stack([U, np.full(len(U), th), np.full(len(U), layer)], axis=1))
            lr.append(np.full(len(U), rnd))
        ob = sheet(f'{tag}_{name}', ribs, {'fan': fan, 'lrand': lr, 'across': [r[3] for r in ribs]})
        add_attr(ob, 'fin_part', np.full(len(ob.data.vertices), part))
        C.log(f'{tag}_{name}: {len(ribs)} locks, {sum(len(p.vertices) - 2 for p in ob.data.polygons)} tris')
        objs.append(ob)
    objs.append(star_mesh(f'{tag}_star', high, 'x'))
    objs.append(star_mesh(f'{tag}_star2', high, 'y'))
    return objs
