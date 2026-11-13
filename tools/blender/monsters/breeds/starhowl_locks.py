"""Starhowl Ultra: the sculpted locks of the mane and the plume, the throat ruff's clumps and the legs' cuffs (the
recipe's `body_extras`).

The owner's review of v1.23.0: the mane is thinner than the hero's dense mass and the plume is thin from behind. The
mane's big S-curved locks and the plume's pointed clumps are VOLUMES united into the body: each is a flattened, tapered
tube swept along a curve from `starhowl_mane.grow` (draped over the body's signed distance, waving sideways, the tip
curling out), so the silhouette is layered locks and not a smooth collar (chatgpt/monsters/06-starhowl: 1-hero,
2-turnaround front and back, 4-details panels 4 and 5).

The upgrade review (Nov 12): the hair cards over the locks read as shards, needles and comb teeth, and the Lite copy
(the bare sculpt) read more like locks. So the sculpt IS the mane now (no cards on it): fewer, wider, flatter clumps in
uneven lengths past the elbows, from the ear bases down; the throat ruff's "paper chip" cards became sculpted clumps
('bib'), and each lower leg has a fluffy cuff ('cuff').

A coarse grid remembers where each set's locks are, how far along its lock a point lies (root 0 … tip 1) and which way
the lock runs, for the recipe's zones, paint and comb direction.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib.surface import norm, smooth
from monsters.breeds import starhowl_mane as M

_COLLAR: list = []            # the recipe's COLLAR_KEYS: (z, x_half, y_front, y_back, back_from, radii)
_PLUME_AXIS: list = []        # the plume's own centre line (through its lobes), base → tip
_CUFFS: list = []             # (centre of the lower leg at the cuff's height (x, y, z), radius reached)
_LOCKS: dict = {}             # name → list of lock dicts (P, O, W, th)
_GRIDS: dict = {}             # name → (origin, h, inside, u, tangent)
SETS = ('mane', 'tail', 'bib', 'cuff', 'crown')

# z, locks per side, |θ| / π from … to (0 the crest behind the neck, 1 the throat), length, width, waves, sideways wave.
# Round 8: fewer, wider clumps in uneven lengths (the sides fall past the elbows; no straight hem), the first tier from
# behind the ears and the cheeks (2-turnaround front: the mane frames the face up to the ear bases)
MANE_TIERS = [
    # round 9 (review: a stole of shards): long tapered locks, 4-5 times as long as they are wide, each with a clear
    # S-bend and a flipped tip; rooted on the crown behind the ears, the cheeks and the nape; none below elbow height
    # round 9b (the first ribbons were round and even: tentacles): wider, flat, tapering all the way down
    (1.03, 2, (0.2, 0.55), (0.36, 0.44), (0.078, 0.092), 1.15, 0.04),       # the crown, behind the ears
    (0.98, 3, (0.56, 0.9), (0.3, 0.38), (0.07, 0.084), 1.1, 0.036),         # the cheeks: forward past the jaw
    (0.95, 2, (0.04, 0.3), (0.36, 0.44), (0.08, 0.095), 1.2, 0.042),        # the nape
    (0.87, 6, (0.1, 0.86), (0.3, 0.38), (0.078, 0.095), 1.3, 0.046),
    (0.78, 5, (0.16, 0.8), (0.22, 0.29), (0.07, 0.085), 1.2, 0.04),
]
MANE_THICK = 0.28             # a lock's thickness as a share of its width (a flat lock of three strands)
# share of the plume's axis, clumps round it, length, width: wide, flat, close-lying feather clumps in overlapping rows
# (4-details panel 4), not spikes
TAIL_ROWS = [(0.08, 7, 0.14, 0.080), (0.19, 8, 0.16, 0.088), (0.30, 9, 0.17, 0.092), (0.41, 10, 0.18, 0.096),
             (0.52, 10, 0.18, 0.096), (0.63, 10, 0.18, 0.094), (0.74, 9, 0.16, 0.088), (0.84, 9, 0.11, 0.076),
             (0.93, 8, 0.085, 0.062), (0.99, 6, 0.065, 0.05)]
# the throat ruff: rows of soft clumps down the bib (height, clumps across, half-width covered)
# (round 8d: the lowest row hung free under the chest as a dark flap; the ruff ends in a soft point on the chest)
BIB_ROWS = [(0.845, 3, 0.055), (0.795, 3, 0.06), (0.74, 4, 0.065), (0.69, 2, 0.032)]
# round 8d: the crown's sculpted tuft (x, y, sideways fan, length, width): five short locks from between the ears,
# swept back down the nape to meet the mane (the card tuft drew floating dashes over the head)
CROWN_ROWS = [(-0.02, -0.38, -0.4, 0.12, 0.034), (0.0, -0.39, 0.05, 0.15, 0.038), (0.021, -0.38, 0.42, 0.12, 0.034)]
CUFF_CLUMPS = 7


def configure(collar_keys, plume_axis, cuffs=()) -> None:
    """The recipe's collar keys, the plume's centre line and the legs' cuff rings (call after starhowl_mane.configure)."""
    _COLLAR[:] = list(collar_keys)
    _PLUME_AXIS[:] = [np.array(p, float) for p in plume_axis]
    _CUFFS[:] = [np.array(c, float) for c in cuffs]
    _LOCKS.clear()
    _GRIDS.clear()


def collar_section(z: float) -> tuple[float, float, float]:
    """The collar's section at height z: (half-width, centre y, half-depth)."""
    zs = np.array([k[0] for k in _COLLAR])[::-1]

    def col(i: int) -> float:
        return float(np.interp(z, zs, np.array([k[i] for k in _COLLAR])[::-1]))
    xh, yf, yb = col(1), col(2), col(3)
    return xh, 0.5 * (yf + yb), 0.5 * (yb - yf)


def _axis_point(pts: np.ndarray, t: float) -> tuple[np.ndarray, np.ndarray]:
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    acc = np.concatenate([[0], np.cumsum(seg)]) / seg.sum()
    p = np.array([np.interp(t, acc, pts[:, i]) for i in range(3)])
    a = np.array([np.interp(max(0.0, t - 0.02), acc, pts[:, i]) for i in range(3)])
    b = np.array([np.interp(min(1.0, t + 0.02), acc, pts[:, i]) for i in range(3)])
    d = b - a
    return p, d / np.linalg.norm(d)


def _rows(name: str, rng) -> list[dict]:
    rows = []
    if name == 'mane':
        for ti, (z, per, (a, b), (l0, l1), (w0, w1), waves, amp) in enumerate(MANE_TIERS):
            xh, cy, ay = collar_section(z)
            for side in (1, -1):
                offs = rng.random() * 0.6
                for k in range(per):
                    f = (k + 0.2 + offs + rng.normal(0, 0.1)) / per
                    th = math.pi * (a + (b - a) * min(max(f, 0.0), 1.0)) * side
                    sth, cth = math.sin(th), math.cos(th)
                    d = np.array((xh * sth, ay * cth, 0.1 * (xh + ay)))
                    d /= np.linalg.norm(d)
                    back, front = max(cth, 0.0) ** 1.5, max(-cth, 0.0)
                    # round 9: long ribbons that leave the collar outward (the cheeks' forward, past the jaw), then
                    # sweep out and back over the shoulders (the sides hung straight down as sleeves)
                    fall = np.array((0.26 * sth, 0.34 * abs(sth) + 0.75 * back - 0.1 * front, -1.0 + 0.5 * back))
                    L = (l0 + (l1 - l0) * rng.random() ** 0.8) * (0.82 + 0.18 * abs(sth)) * (1.0 - 0.1 * back)
                    # the upper tiers lie over the lower ones; every tip ends in a curl (out and up, a little aside)
                    rows.append(dict(centre=np.array((0.0, cy, z)) + rng.normal(0, 0.004, 3), d=d, fall=fall, L=L,
                                     clear=(0.004, 0.028 - 0.0035 * ti), waves=waves * (0.9 + 0.2 * rng.random()),
                                     amp=amp * (0.85 + 0.3 * rng.random()), phase=rng.uniform(0, 2 * math.pi),
                                     curl=0.05, hook=0.0, hook_out=0.2, W=w0 + (w1 - w0) * rng.random(), th=MANE_THICK,
                                     n=40, bend=0.3, taper=0.5, t0=0.45, tip_fat=0.5, strands=0, rings=36,
                                     tip=(0.2 + 0.06 * rng.random(), math.pi * (0.38 + 0.17 * rng.random()),
                                          float(rng.choice((-1.0, 1.0))))))
    elif name == 'tail':
        axis = np.array(_PLUME_AXIS)
        for ri, (t, count, L, W) in enumerate(TAIL_ROWS):
            c, tg = _axis_point(axis, t)
            upv = np.array((0.0, 0.0, 1.0)) - tg * tg[2]
            upv /= np.linalg.norm(upv)
            sd = np.cross(tg, upv)
            for k in range(count):
                phi = 2 * math.pi * (k + 0.5 * (ri % 2) + rng.normal(0, 0.08)) / count
                d = upv * math.cos(phi) + sd * math.sin(phi)
                tuft = float(smooth(0.8, 1.0, t))
                fall = tg * (0.95 - 0.1 * tuft) + d * (0.12 + 0.07 * tuft) - upv * (0.06 - 0.11 * tuft)
                rows.append(dict(centre=c, d=d, fall=fall, L=L * (0.85 + 0.3 * rng.random()), clear=(0.002, 0.005 + 0.003 * tuft),
                                 waves=0.4 + 0.3 * rng.random(), amp=0.006, phase=rng.uniform(0, 2 * math.pi), curl=0.03 + 0.03 * tuft,
                                 hook=0.004 + 0.003 * tuft, W=W * (0.9 + 0.2 * rng.random()), th=0.38, n=14, bend=0.2,
                                 taper=0.62 - 0.22 * tuft, strands=3))
    elif name == 'bib':
        for ri, (z, count, half) in enumerate(BIB_ROWS):
            for k in range(count):
                x = half * (2.0 * (k + 0.5) / count - 1.0) + rng.normal(0, 0.006)
                rows.append(dict(centre=np.array((x * 0.5, -0.42, z)), d=np.array((x * 1.4, -1.0, 0.05)),
                                 fall=np.array((x * 1.2, -0.12, -1.0)), L=0.085 + 0.03 * rng.random(), clear=(0.002, 0.006),
                                 waves=0.5, amp=0.004, phase=rng.uniform(0, 2 * math.pi), curl=0.06, hook=0.006,
                                 W=0.058 + 0.014 * rng.random(), th=0.4, n=12, bend=0.3))
    elif name == 'crown':
        for x, y, fan, L, W in CROWN_ROWS:
            # round 9b: three thin, flat wisps swept back between the ears (stood-up tubes read as coral)
            rows.append(dict(centre=np.array((x, y, 1.08)), d=np.array((x * 1.5, 0.35, 1.0)), fall=np.array((fan * 0.6, 1.0, -0.12)),
                             L=L * (0.92 + 0.16 * rng.random()), clear=(0.003, 0.014), waves=0.8, amp=0.01,
                             phase=rng.uniform(0, 2 * math.pi), curl=0.0, hook=0.0, hook_out=0.3, W=W, th=0.4, n=24, bend=0.45,
                             taper=0.6, t0=0.35, tip_fat=1.2, rings=20, tip=(0.25, math.pi * 0.5, float(np.sign(fan) or 1.0))))
    else:
        for c in _CUFFS:
            offs = rng.random()
            for k in range(CUFF_CLUMPS):
                a = 2 * math.pi * (k + offs) / CUFF_CLUMPS
                d = np.array((math.cos(a), math.sin(a), 0.1))
                rows.append(dict(centre=c + rng.normal(0, 0.002, 3), d=d, fall=np.array((0.22 * math.cos(a), 0.22 * math.sin(a), -1.0)),
                                 L=0.075 + 0.025 * rng.random(), clear=(0.002, 0.007), waves=0.5, amp=0.004,
                                 phase=rng.uniform(0, 2 * math.pi), curl=0.3, hook=0.012, W=0.046 + 0.012 * rng.random(), th=0.44,
                                 n=12, bend=0.3))
    return rows


def sculpt_locks(name: str, seed: int = 41) -> list[dict]:
    """The sculpted locks of a set ('mane', 'tail', 'bib', 'cuff'): each {'P': centre line, 'O': outward dirs, 'W': full
    width, 'th': thickness share}. Cached (the high, low and proxy bodies and the grid share them)."""
    if name in _LOCKS:
        return _LOCKS[name]
    rows = _rows(name, np.random.default_rng(seed + 7 * SETS.index(name)))
    out = []
    for n in sorted({r['n'] for r in rows}):
        grp = [r for r in rows if r['n'] == n]
        d = norm(np.array([r['d'] for r in grp], float))
        roots = M.march(np.array([r['centre'] for r in grp]), d, sink=0.008)
        P, O = M.grow(roots, M.sdf_grad(roots), np.array([r['fall'] for r in grp]), np.array([r['L'] for r in grp]), n,
                      np.array([r['clear'] for r in grp]), np.array([r['waves'] for r in grp]), np.array([r['amp'] for r in grp]),
                      np.array([r['phase'] for r in grp]), np.array([r['curl'] for r in grp]), bend=grp[0]['bend'],
                      hook=np.array([r['hook'] for r in grp]), hook_out=grp[0].get('hook_out', 0.6))
        for i, r in enumerate(grp):
            Pi, Oi = (_curl_tip(P[i], O[i], *r['tip']) if r.get('tip') else (P[i], O[i]))
            out.append(dict(P=Pi, O=Oi, W=r['W'], th=r['th'], taper=r.get('taper', 0.78), t0=r.get('t0', 0.6), tip_fat=r.get('tip_fat', 0.0), strands=int(r.get('strands', 0)),
                            rings=r.get('rings')))
    C.log(f'sculpted locks: {len(out)} in the {name}')
    _LOCKS[name] = out
    return out


def _unit(v: np.ndarray) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-9)


def _curl_tip(P: np.ndarray, O: np.ndarray, frac: float, angle: float, side: float):
    """The last `frac` of a lock's centre line rolled into a curl of `angle` radians: out from the body and up, a
    little to one side (round 9: curled tips, not points)."""
    n = len(P)
    k0 = max(2, int(round((n - 1) * (1.0 - frac))))
    m = n - 1 - k0
    if m < 2:
        return P, O
    T0 = _unit(P[k0] - P[k0 - 1])
    O0 = _unit(O[k0] - T0 * float(O[k0] @ T0))
    Cd = _unit(O0 + 0.25 * side * np.cross(T0, O0))
    r = float(np.linalg.norm(np.diff(P[k0:], axis=0), axis=1).sum()) / angle
    P, O = P.copy(), O.copy()
    for j in range(1, m + 1):
        th = angle * j / m
        P[k0 + j] = P[k0] + r * (math.sin(th) * T0 + (1.0 - math.cos(th)) * Cd)
        O[k0 + j] = math.cos(th) * Cd - math.sin(th) * T0
    return P, O


def lock_profile(u: np.ndarray, taper: float = 0.78, t0: float = 0.6) -> np.ndarray:
    """A lock's half-width along it (share of the full half-width): narrower at the root, widest at about a third,
    tapering by `taper` toward the tip."""
    return (0.55 + 0.45 * smooth(0.0, 0.3, u)) * (1.0 - taper * smooth(t0, 1.0, u) ** 1.4)


def _resample(P: np.ndarray, O: np.ndarray, m: int):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    acc = np.concatenate([[0], np.cumsum(seg)])
    tt = np.linspace(0, acc[-1], m)
    Q = np.stack([np.interp(tt, acc, P[:, i]) for i in range(3)], axis=1)
    Oq = norm(np.stack([np.interp(tt, acc, O[:, i]) for i in range(3)], axis=1))
    return Q, Oq, tt / max(acc[-1], 1e-9)


def lock_mesh(name: str, rings: int = 16, sides: int = 10) -> bpy.types.Object:
    """Every sculpted lock of `name` as one object of closed tubes (for the recipe's body_extras)."""
    bm = bmesh.new()
    for lk in sculpt_locks(name):
        strands = int(lk.get('strands', 0))
        rings_ = int(lk.get('rings') or rings)
        sides_ = 20 if strands else sides
        Q, Oq, u = _resample(lk['P'], lk['O'], rings_)
        T = norm(np.gradient(Q, axis=0))
        A = norm(np.cross(T, Oq))
        N = norm(np.cross(A, T))
        N = np.where(((N * Oq).sum(1) < 0)[:, None], -N, N)
        hw = 0.5 * lk['W'] * lock_profile(u, lk.get('taper', 0.78), lk.get('t0', 0.6))
        # flat at the root and the middle, rounder toward the thin tip (a paper-thin tip breaks up in the game mesh)
        ht = hw * lk['th'] * (1.0 + lk.get('tip_fat', 0.0) * smooth(0.5, 1.0, u))
        # sunk a little so the underside is inside the body (no slot under the lock), less toward the free tip
        Q = Q - N * (ht * 0.5 * (1.0 - smooth(0.6, 1.0, u)))[:, None]
        ring_v = []
        for j in range(rings_ - 1):
            vs = []
            for i in range(sides_):
                a = 2 * math.pi * i / sides_
                ca = math.cos(a)
                # a ribbon of `strands` strands: grooves between them, across its width
                k = 0.62 + 0.38 * abs(math.sin(strands * math.pi * (0.5 * ca + 0.5))) if strands else 1.0
                vs.append(bm.verts.new(Q[j] + A[j] * (hw[j] * ca) + N[j] * (ht[j] * math.sin(a) * k)))
            ring_v.append(vs)
        root = bm.verts.new(Q[0] - T[0] * 0.012)
        tip = bm.verts.new(Q[-1])
        for i in range(sides_):
            i2 = (i + 1) % sides_
            bm.faces.new((root, ring_v[0][i2], ring_v[0][i]))
            for j in range(rings_ - 2):
                bm.faces.new((ring_v[j][i], ring_v[j][i2], ring_v[j + 1][i2], ring_v[j + 1][i]))
            bm.faces.new((ring_v[-1][i], ring_v[-1][i2], tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'locks_{name}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(f'locks_{name}', me)
    C.link_obj(ob)
    return ob


def _grid(name: str, h: float = 0.006):
    """(origin, h, inside, u, tangent) of the sculpted locks of `name`: cells within a lock (a little fatter)."""
    if name in _GRIDS:
        return _GRIDS[name]
    locks = sculpt_locks(name)
    pts = np.concatenate([lk['P'] for lk in locks])
    lo = pts.min(0) - 0.09
    dims = np.ceil((pts.max(0) + 0.09 - lo) / h).astype(int) + 1
    best = np.full(dims, 9.0, np.float32)            # (distance / radius) to the nearest lock sample
    ug = np.zeros(dims, np.float32)
    vg = np.zeros(dims, np.float32)
    tg = np.zeros((*dims, 3), np.float32)
    for lk in locks:
        Q, Oq_, u = _resample(lk['P'], lk['O'], 48)
        T = norm(np.gradient(Q, axis=0))
        Ax = norm(np.cross(T, Oq_))
        hw_ = np.maximum(0.5 * lk['W'] * lock_profile(u, lk.get('taper', 0.78), lk.get('t0', 0.6)), 1e-4)
        rad = hw_ * 1.12 + 0.006
        for j in range(len(Q)):
            r = float(rad[j])
            i0 = np.maximum(np.floor((Q[j] - r - lo) / h).astype(int), 0)
            i1 = np.minimum(np.ceil((Q[j] + r - lo) / h).astype(int) + 1, dims)
            if (i1 <= i0).any():
                continue
            gx, gy, gz = np.meshgrid(*(lo[a] + h * np.arange(i0[a], i1[a]) for a in range(3)), indexing='ij')
            d = np.sqrt((gx - Q[j][0]) ** 2 + (gy - Q[j][1]) ** 2 + (gz - Q[j][2]) ** 2) / r
            sl = (slice(i0[0], i1[0]), slice(i0[1], i1[1]), slice(i0[2], i1[2]))
            win = d < best[sl]
            best[sl] = np.where(win, d, best[sl])
            ug[sl] = np.where(win, u[j], ug[sl])
            vv = ((gx - Q[j][0]) * Ax[j][0] + (gy - Q[j][1]) * Ax[j][1] + (gz - Q[j][2]) * Ax[j][2]) / hw_[j]
            vg[sl] = np.where(win, vv, vg[sl])
            tg[sl] = np.where(win[..., None], T[j].astype(np.float32), tg[sl])
    _GRIDS[name] = (lo, h, best < 1.0, ug, tg, vg)
    return _GRIDS[name]


def lookup(p: np.ndarray, name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For points: (inside one of `name`'s sculpted locks, how far along it 0 root … 1 tip, the lock's direction)."""
    lo, h, inside, ug, tg, _vg = _grid(name)
    idx = np.floor((np.atleast_2d(p) - lo) / h + 0.5).astype(int)
    dims = np.array(inside.shape)
    ok = ((idx >= 0) & (idx < dims)).all(1)
    idx = np.clip(idx, 0, dims - 1)
    ins = inside[idx[:, 0], idx[:, 1], idx[:, 2]] & ok
    return ins, np.where(ins, ug[idx[:, 0], idx[:, 1], idx[:, 2]], 0.0), tg[idx[:, 0], idx[:, 1], idx[:, 2]].astype(np.float64)


def lookup_v(p: np.ndarray, name: str) -> np.ndarray:
    """For points: how far across the nearest sculpted lock of `name` (-1 … 1 between its edges; 0 outside)."""
    lo, h, inside, _ug, _tg, vg = _grid(name)
    idx = np.floor((np.atleast_2d(p) - lo) / h + 0.5).astype(int)
    dims = np.array(inside.shape)
    ok = ((idx >= 0) & (idx < dims)).all(1)
    idx = np.clip(idx, 0, dims - 1)
    ins = inside[idx[:, 0], idx[:, 1], idx[:, 2]] & ok
    return np.where(ins, np.clip(vg[idx[:, 0], idx[:, 1], idx[:, 2]], -1.2, 1.2), 0.0).astype(np.float64)
