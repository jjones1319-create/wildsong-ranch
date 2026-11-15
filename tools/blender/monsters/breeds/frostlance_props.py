"""Frostlance's rigid props (frostlance_ultra.py build_props): the two frost-edged pectoral fins and the tail fluke as
pillowed slabs cut from toothed outlines (a fringe of ice-crystal spikes along their outer and trailing edges, 1-hero,
4-details 3 and 4), and the long spiral tusk of ice (4-details 5) as a grooved tube.

A slab (after zipwisp_props.slab, with a thickness over the whole outline, a bend of its mid-plane and a frost mask): the
outline is resampled, rows of points are set in from its edge, the inside is filled and triangulated (constrained
Delaunay), and the two faces are lifted off the bent mid-plane by a pillow profile: a short wall at the edge (EDGE_HALF,
never zero) rounding up over BEVEL to the part's thickness, so each crystal spike thins to a wedge. Its own unwrap
(`own_uv`): each face flat in its plane, the wall one strip. Attributes for the paint and the weights: part, ed (metres
to the edge), su (0 root .. 1 the far point), sv (across), frost (1 on the spikes and the band inside them, 0 inside),
side (+1 left, -1 right; 0 the fluke and the tusk), face (+1 front, -1 back, 0 wall), groove (the tusk's spiral, 0..1).
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Vector, geometry

from lib import common as C
from lib import surface as S
from lib.surface import smooth
from monsters.breeds import frostlance_form as F

FIN, FLUKE, TUSK = 1, 2, 3
EDGE_HALF = 0.0026                  # half the wall's height at every edge (a slab never thins to nothing)
BEVEL = 0.009                       # how far in from the edge the face rounds up to the full thickness
ROWS = (0.0024, 0.0058)             # rows set in from the edge: the frost's paint changes across them
FROST_BAND = 0.06                   # the icy band inside the crystals' roots (4-details 3: the teal fades to pale ice)
SHARDS = (1.0, 0.55, 0.85, 0.45, 1.3, 0.6, 0.95, 0.5, 1.15, 0.65)   # round 1: layered shards of mixed lengths, not saw-teeth
NOTCHES: dict = {}                  # per slab: [(notch (u, v), inward (du, dv), length)] for the paint's shard lines
TIPS: dict = {}                     # per slab: the shards' points (u, v): the slab thins toward them (round 3)
UV_OFF = {'finL': 0.0, 'finR': 1.0, 'fluke': 2.0}   # each slab's own patch of the shared 2D frame (slab_uv)


def _seg_dist(p: np.ndarray, poly: np.ndarray) -> np.ndarray:
    d = np.full(len(p), np.inf)
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        ab = b - a
        t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-18), 0, 1)
        d = np.minimum(d, np.linalg.norm(p - (a + t[:, None] * ab), axis=1))
    return d


def _inside(p: np.ndarray, poly: np.ndarray) -> np.ndarray:
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


def ccw(poly) -> np.ndarray:
    poly = np.asarray(poly, np.float64)
    area = 0.5 * float(np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]))
    return poly[::-1].copy() if area < 0 else poly


def toothed(base, length_fn, lean_fn, spacing: float, angle: float, seed: int, key: str | None = None) -> np.ndarray:
    """The base outline (closed) with a fringe of crystal spikes wherever `length_fn(p, n_out)` > 0 (their length, metres):
    notches on the base edge, tips out along the outward normal swept `angle` degrees toward `lean_fn(p)` (a 2D direction
    along the edge). Lengths and angles vary a little per spike (a fixed seed)."""
    ring = _resample(ccw(base), 0.0015)
    k = len(ring)
    tng = np.roll(ring, -1, axis=0) - np.roll(ring, 1, axis=0)
    tng /= np.maximum(np.linalg.norm(tng, axis=1), 1e-12)[:, None]
    nout = np.stack([tng[:, 1], -tng[:, 0]], axis=1)            # counter-clockwise: outward is to the right
    ln = np.array([float(length_fn(p, n)) for p, n in zip(ring, nout)])
    if (ln > 0).all() or not (ln > 0).any():
        return ring
    start = int(np.argmax(ln <= 0))
    ring, tng, nout, ln = (np.roll(a, -start, axis=0) for a in (ring, tng, nout, ln))
    seg = np.linalg.norm(np.roll(ring, -1, axis=0) - ring, axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)[:-1]])
    rng = np.random.default_rng(seed)

    def at(x: float):
        i = int(np.clip(np.searchsorted(s, x, side='right') - 1, 0, k - 1))
        j = (i + 1) % k
        w = (x - s[i]) / max(seg[i], 1e-12)
        return ring[i] * (1 - w) + ring[j] * w, tng[i], nout[i], ln[i] * (1 - w) + ln[j] * w

    out = []
    notches = []
    tips = []
    shard = 0
    i = 0
    while i < k:
        if ln[i] <= 0:
            out.append(ring[i])
            i += 1
            continue
        j = i
        while j < k and ln[j] > 0:
            j += 1
        s0, s1 = s[i], s[j - 1]
        n_t = max(1, int(round((s1 - s0) / spacing)))
        for t in range(n_t):
            p, _tg, no, lk0 = at(s0 + (s1 - s0) * t / n_t)
            out.append(p - no * 0.0012)
            if t > 0:
                notches.append((tuple(p - no * 0.0012), tuple(-no), float(lk0)))
            p, tg, no, lk = at(s0 + (s1 - s0) * (t + 0.5) / n_t)
            lk *= SHARDS[shard % len(SHARDS)] * float(rng.uniform(0.85, 1.15))
            shard += 1
            lean = np.asarray(lean_fn(p), np.float64)
            sgn = 1.0 if float(lean @ tg) >= 0 else -1.0
            a = math.radians(angle * float(rng.uniform(0.75, 1.2)))
            d = no * math.cos(a) + tg * sgn * math.sin(a)
            out.append(p + d * lk)
            tips.append(tuple(p + d * lk))
        p, _tg, no, _l = at(s1)
        out.append(p - no * 0.0012)
        i = j
    if key:
        NOTCHES[key] = notches
        TIPS[key] = tips
    return np.array(out)


def slab(name: str, outline, base, origin, ax_u, ax_v, normal, thick, step: float, part: int, attrs: dict | None = None,
         bend=None, high: bool = True, frost_k=None, uv_off: float = 0.0, edge_half: float = EDGE_HALF, bevel: float = BEVEL,
         tips=None, shard_t: float | None = None):
    """A pillowed slab from a 2D outline (u, v metres) in the plane (origin, ax_u, ax_v), its mid-plane bent `bend(u, v)`
    metres along `normal`; `thick(u, v)` its full thickness; `base` the outline without its spikes (the frost mask)."""
    poly = ccw(outline)
    basep = ccw(base)
    ring = _resample(poly, step)
    k = len(ring)
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
    xs = np.arange(poly[:, 0].min(), poly[:, 0].max(), step * 1.2)
    ys = np.arange(poly[:, 1].min(), poly[:, 1].max(), step * 1.2 * math.sqrt(3) / 2)
    gx, gy = np.meshgrid(xs, ys)
    gx = gx + (np.arange(len(ys))[:, None] % 2) * step * 0.6
    grid = np.stack([gx.ravel(), gy.ravel()], axis=1)
    grid = grid[_inside(grid, poly) & (_seg_dist(grid, poly) > ROWS[-1] + step * 0.55)]
    pts2 = np.concatenate([ring] + extra + [grid])
    keep = np.ones(len(pts2), bool)
    for i in range(k, len(pts2)):
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
    loop = [remap[inv[j]] for j in range(k)]
    n2 = len(vco)
    ed = _seg_dist(vco, poly)
    ed[loop] = 0.0
    inb = _inside(vco, basep)
    db = _seg_dist(vco, basep)
    frost = np.where(inb, 1.0 - smooth(0.0, FROST_BAND, db), 1.0)
    if frost_k is not None:
        frost = frost * np.asarray(frost_k(vco[:, 0], vco[:, 1]), np.float64)   # round 1: no frost at the roots
    # round 3: the shards thin toward their points (edge-on they read as thick square-cut blocks), never to zero
    eh = np.full(n2, edge_half)
    if tips is not None and len(tips):
        tp = np.asarray(tips, np.float64)
        dt = np.min(np.linalg.norm(vco[:, None, :] - tp[None, :, :], axis=2), axis=1)
        eh = edge_half * (0.3 + 0.7 * smooth(0.0, 0.02, dt))
    t = np.asarray(thick(vco[:, 0], vco[:, 1]), np.float64)
    if shard_t is not None:
        t = np.where(inb, t, np.minimum(t, shard_t))       # polish: the shards flat blades, not round cones
    t = np.maximum(t, 2 * eh)
    prof = np.sqrt(np.clip(1.0 - (1.0 - np.clip(ed / bevel, 0, 1)) ** 2, 0, 1))
    h = eh + (t * 0.5 - eh) * prof
    O, U, V, N = (np.array(a[:], np.float64) for a in (origin, ax_u, ax_v, normal))
    off = np.asarray(bend(vco[:, 0], vco[:, 1]), np.float64) if bend else np.zeros(n2)
    mid = O + vco[:, :1] * U + vco[:, 1:2] * V + off[:, None] * N
    verts = np.concatenate([mid + h[:, None] * N, mid - h[:, None] * N])
    fl, kinds, wall_out = [], [], []
    for f in faces:
        fl.append(f)
        kinds.append(1)
        fl.append([i + n2 for i in f[::-1]])
        kinds.append(-1)
    for a, b in zip(loop, loop[1:] + loop[:1]):
        fl.append([a, b, b + n2, a + n2])
        kinds.append(0)
        d = vco[b] - vco[a]
        wall_out.append(d[1] * U - d[0] * V)
    nrm = np.array([np.cross(verts[f[1]] - verts[f[0]], verts[f[2]] - verts[f[0]]) for f in fl])
    want = np.zeros_like(nrm)
    kinds = np.array(kinds)
    want[kinds == 1] = N
    want[kinds == -1] = -N
    want[kinds == 0] = np.array(wall_out)
    flip = (nrm * want).sum(axis=1) < 0
    fl = [f[::-1] if fp else f for f, fp in zip(fl, flip)]
    ob = S.sheet_object(name, verts, fl)
    umax = float(np.abs(poly[:, 0]).max())
    two = lambda a: np.concatenate([a, a])      # noqa: E731
    for key, vals in {'part': np.full(n2, float(part)), 'ed': ed, 'su': np.clip(np.abs(vco[:, 0]) / umax, 0, 1),
                      'sv': vco[:, 1], 'frost': frost, 'groove': np.zeros(n2), 'hcos': np.zeros(n2), 'hsin': np.zeros(n2),
                      'shade': np.zeros(n2), 'tcos': np.zeros(n2), 'tsin': np.zeros(n2)}.items():
        S.add_attr(ob, key, two(vals))
    # the slab's own 2D frame per point (exact under interpolation), offset per slab: the paint's shard lines
    S.add_attr(ob, 'slab_uv', two(np.stack([vco[:, 0] + uv_off, vco[:, 1], np.zeros(n2)], axis=1)))
    S.add_attr(ob, 'face', np.concatenate([np.ones(n2), -np.ones(n2)]))
    for key, val in {'side': 0.0, **(attrs or {})}.items():
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
            wrap = max(ps) - min(ps) > half
            for i, p in zip(f, ps):
                if wrap and p < half:
                    p = p + perim[-1]
                flat.append((p, -0.03 - (hgt if i >= n2 else 0.0)))
    lay = ob.data.uv_layers.new(name='UVMap')
    lay.data.foreach_set('uv', np.asarray(flat, np.float32).ravel())
    ob['own_uv'] = True


# ----------------------------------------------------------------------------- the pectoral fins
# the left fin's outline (u out along the fin from its root on the flank, v across: + the leading edge), drawn for a
# 0.3 m fin and scaled by FIN_K: round 3, a leaf about two and a half times as long as wide, sweeping back to a point, a
# smooth leading edge and a full trailing edge (4-details 3), on a narrow root sunk FIN_BURY into its fleshy root
FIN_BASE_0 = [(-F.FIN_BURY, 0.011), (0.0, 0.012), (0.04, 0.015), (0.08, 0.026), (0.16, 0.033), (0.23, 0.026), (0.285, 0.01),
              (0.31, -0.008), (0.29, -0.032), (0.25, -0.055), (0.19, -0.075), (0.12, -0.072), (0.075, -0.04), (0.04, -0.017),
              (0.0, -0.012), (-F.FIN_BURY, -0.011)]
# polish: the root is a narrow stalk, inside its fleshy root until both are thin (its edges broke the skin: a jagged cut
# with a glossy white sliver under it)
FIN_BASE = [(u * F.FIN_K, v * F.FIN_K) for u, v in FIN_BASE_0]


def _fin_teeth(p, n) -> float:
    """Shard length along the fin's edge (round 3): none on the root and the leading edge, long ice shards along the
    trailing edge and round the point (the longest about a quarter of the fin with the SHARDS pattern), swept to the tip."""
    u, v = float(p[0]) / F.FIN_K, float(p[1]) / F.FIN_K
    if u > 0.27:
        return 0.06
    if v < 0.0:
        return (0.05 + 0.024 * float(smooth(0.1, 0.25, u))) * float(smooth(0.05, 0.1, u))
    return 0.0


def fin_thick(u, v):
    return 0.009 + 0.022 * (1.0 - smooth(0.0, F.FIN_LEN * 0.9, u))


def _fin_outline(s: int) -> np.ndarray:
    tag = 'L' if s > 0 else 'R'
    return toothed(np.array(FIN_BASE), _fin_teeth, lambda p: (1.0, 0.0), 0.03, 38.0, 18 if s > 0 else 81, key=f'fin{tag}')


def fin(s: int, high: bool):
    o, a, v, n = F.fin_axes(s)
    tag = 'L' if s > 0 else 'R'
    outline = _fin_outline(s)
    return slab(f"{'hi' if high else 'lo'}_fin{tag}", outline, np.array(FIN_BASE), o, a, v, n, fin_thick,
                0.0035 if high else 0.0078, FIN, {'side': s}, bend=lambda uu, vv: 1.1 * vv * vv, high=high,
                frost_k=lambda uu, vv: smooth(0.07 * F.FIN_K, 0.13 * F.FIN_K, uu), uv_off=UV_OFF[f'fin{tag}'],
                edge_half=0.0016, bevel=0.012, tips=TIPS[f'fin{tag}'], shard_t=0.0042)


# ----------------------------------------------------------------------------- the fluke
# the left lobe's outline (u across: +X, v back along the tail, metres), from the notch out along the trailing edge to
# the tip, then in along the leading edge to the neck, which sinks into the stalk's flattened end; the right lobe
# mirrors it. Round 3: two broad leaves (front to back about 0.55 of the span), 0.5 m across (about 1.2x the body)
FLUKE_LOBE_0 = [(0.0, 0.17), (0.05, 0.198), (0.11, 0.232), (0.17, 0.258), (0.215, 0.268), (0.248, 0.25), (0.25, 0.205),
                (0.225, 0.145), (0.18, 0.095), (0.12, 0.052), (0.065, 0.022), (0.03, 0.0), (0.022, -0.05)]
FLUKE_LOBE = [(u * F.FLUKE_K, v * F.FLUKE_K) if v > 0 else (u, v) for u, v in FLUKE_LOBE_0]


def fluke_base() -> np.ndarray:
    left = [p for p in FLUKE_LOBE]
    right = [(-u, v) for u, v in FLUKE_LOBE[::-1]]
    return np.array(left + right[:-1])


def _fluke_teeth(p, n) -> float:
    """Shards along the trailing edges and round the lobes' points (the same feathered edge as the fins), none on the
    leading edges and the neck."""
    u = abs(float(p[0])) / F.FLUKE_K
    back = float(n[1]) > -0.25 or u > 0.215
    return (0.04 + 0.018 * float(smooth(0.1, 0.22, u))) * float(smooth(0.04, 0.09, u)) * (1.0 if back else 0.0)


def fluke_thick(u, v):
    """Round 3: thinner (edge-on the far lobe read as a thick white slab, and its steep bevel stretched the paint)."""
    au = np.abs(u) / F.FLUKE_K
    # polish: its root thickened into the stalk's flattened end (a thin root sat in the stalk like a sleeve)
    root = 0.026 * smooth(0.075, 0.0, au) * smooth(0.09, 0.0, v)
    return 0.008 + 0.016 * (1.0 - smooth(0.0, 0.2, au)) * (1.0 - 0.5 * smooth(0.04, 0.2, v / F.FLUKE_K)) + root


def _fluke_outline() -> np.ndarray:
    return toothed(fluke_base(), _fluke_teeth, lambda p: (float(np.sign(p[0]) or 1.0), 0.6), 0.03, 34.0, 27, key='fluke')


def fluke(high: bool):
    o, u, v, n = F.fluke_axes()
    outline = _fluke_outline()
    return slab(f"{'hi' if high else 'lo'}_fluke", outline, fluke_base(), o, u, v, n, fluke_thick,
                0.0035 if high else 0.0085, FLUKE, bend=lambda uu, vv: -F.FLUKE_DROOP * uu * uu, high=high,
                frost_k=lambda uu, vv: smooth(0.05, 0.11, np.abs(uu)), uv_off=UV_OFF['fluke'],
                edge_half=0.0014, bevel=0.014, tips=TIPS['fluke'], shard_t=0.0036)


def shard_lines() -> list:
    """The darker lines between the shards (round 1, 4-details 3, 4): from each notch inward, in each slab's 2D frame
    (slab_uv), as (a, b) 3D points for lib.marks.line. Builds the outlines if they aren't built yet (deterministic)."""
    if not all(k in NOTCHES for k in UV_OFF):
        _fin_outline(1)
        _fin_outline(-1)
        _fluke_outline()
    out = []
    for key, off in UV_OFF.items():
        for (pu, pv), (du, dv), ln in NOTCHES[key]:
            L = 0.35 * ln + 0.012
            out.append(((pu + off, pv, 0.0), (pu + off + du * L, pv + dv * L, 0.0)))
    return out


# ----------------------------------------------------------------------------- the tusk
TUSK_DEPTH = 0.24                    # the grooves' depth (share of the radius); round 3: deep V-grooves between crisp ridges


def tusk_radius(along: np.ndarray) -> np.ndarray:
    """The tusk's radius along it (metres from the root, the first TUSK_BURY under the skin): a long straight taper."""
    k = np.clip((along - F.TUSK_BURY) / F.TUSK_LEN, 0.0, 1.0)
    r0, r1 = F.TUSK_R
    return r0 + (r1 - r0) * k ** 0.9                    # round 3: no swell at the root (the fat first roll)


def tusk_phase(along: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """The ridges' phase: TUSK_STARTS grooves round it, TUSK_TURNS ridges along it (round 1: one groove that many turns lay
    nearly flat, stacked rings; three twisted together slant about 30 degrees, a twisted rope of ice as in 4-details 5)."""
    return F.TUSK_STARTS * theta + 2 * np.pi * F.TUSK_TURNS * (along - F.TUSK_BURY) / F.TUSK_LEN


def tusk_groove(along: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """0..1, 1 in the groove: one continuous helical ridge winding TUSK_TURNS times (round 1: a rounded ridge and a wide
    groove, 4-details 5, not narrow cuts between flat rings), fading out under the skin and at the point."""
    k = (along - F.TUSK_BURY) / F.TUSK_LEN
    # round 3: a triangle profile, a crisp ridge between deep V-grooves (rounded rolls read as soft-serve), full depth
    # right from the skin (it faded in, so the first roll stood fat)
    ph = np.mod(tusk_phase(along, theta), 2 * np.pi)
    d = np.abs(ph - np.pi) / np.pi                      # 0 on a crest, 1 in a groove
    return d * smooth(-0.05, -0.012, k) * smooth(0.985, 0.9, k)


def tusk(high: bool):
    rings, seg = (560, 64) if high else (170, 40)     # round 1: more sides (its outline was faceted up close)
    total = F.TUSK_BURY + F.TUSK_LEN
    d = np.array(F.TUSK_DIR[:])
    e1 = np.array((1.0, 0.0, 0.0))
    e2 = np.cross(d, e1)
    up = np.array((0.0, 0.0, 1.0)) - d * d[2]
    up /= np.linalg.norm(up)
    root = np.array(F.TUSK_ROOT[:])
    along = np.linspace(0.0, total, rings + 1)[:, None]
    th = (np.arange(seg) / seg * 2 * np.pi)[None, :]
    g = tusk_groove(along, th)
    ph = tusk_phase(along, th)
    r = tusk_radius(along) * (1.0 - TUSK_DEPTH * g)
    radial = np.cos(th)[..., None] * e1 + np.sin(th)[..., None] * e2
    P = root[None, None, :] + along[..., None] * d + r[..., None] * radial
    shade = np.broadcast_to(smooth(0.3, -0.8, radial @ up), g.shape)
    side_ = np.cross(d, up)
    tcos = np.broadcast_to(radial @ up, g.shape)      # round 3: the angle round it, for the lengthwise streaks
    tsin = np.broadcast_to(radial @ side_, g.shape)
    verts = list(P.reshape(-1, 3))
    faces = []
    for i in range(rings):
        for j in range(seg):
            j2 = (j + 1) % seg
            faces.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    i0, i1 = len(verts), len(verts) + 1
    verts += [root - d * 0.004, root + d * (total + 0.005)]
    for j in range(seg):
        j2 = (j + 1) % seg
        faces.append((j2, j, i0))
        faces.append((rings * seg + j, rings * seg + j2, i1))
    ob = S.sheet_object(f"{'hi' if high else 'lo'}_tusk", np.array(verts), faces)
    S.orient_away(ob, lambda c: root[None] + np.clip((c - root) @ d, 0.0, total)[:, None] * d[None])
    n = len(verts)
    tt = np.concatenate([np.repeat(((along[:, 0] - F.TUSK_BURY) / F.TUSK_LEN), seg), [-0.1, 1.0]])

    def ext(a):
        return np.concatenate([np.asarray(a, np.float64).ravel(), [0.0, 0.0]])
    for key, vals in {'part': np.full(n, float(TUSK)), 'ed': np.full(n, 1.0), 'su': np.clip(tt, -0.2, 1.0), 'sv': np.zeros(n),
                      'frost': np.zeros(n), 'groove': ext(g), 'face': np.zeros(n), 'side': np.zeros(n),
                      'hcos': ext(np.cos(ph)), 'hsin': ext(np.sin(ph)), 'shade': ext(shade), 'tcos': ext(tcos),
                      'tsin': ext(tsin)}.items():
        S.add_attr(ob, key, vals)
    S.add_attr(ob, 'slab_uv', np.tile(np.array([-10.0, -10.0, 0.0]), (n, 1)))
    S.tube_uvs(ob, [tuple(root), tuple(root + d * total)])
    C.log(f'{ob.name}: {len(faces)} faces, {n} verts')
    return ob


def objects(high: bool) -> list:
    return [tusk(high), fin(1, high), fin(-1, high), fluke(high)]
