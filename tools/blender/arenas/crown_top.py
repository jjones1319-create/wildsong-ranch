"""The top of the Crown Amphitheatre: the colonnaded gallery above the top tier (its columns, beam, tiled roof and
back wall), the velarium masts on the attic, and the velarium itself: striped awnings drawn over the north half (the
side the battle camera faces), furled on their ropes on the south half, a pennant on every other mast.
"""
from __future__ import annotations

import math

import numpy as np

from crown_geo import MB, bbox, bend, lathe, perimeter, pt, sweep, t_at_arc
import crown_layout as L
from crown_facade import arc_t, ring_sweeps, unwrap

COL_PROFILE = [(0.42, 0.0), (0.42, 0.3), (0.29, 0.38), (0.25, 5.25), (0.42, 5.55), (0.44, 5.9)]
N_MASTS = 36
DRAWN = (math.radians(28), math.radians(152))     # the drawn awnings: masts between these angles (north side)
V_INNER = 23.5                                    # the awnings reach in to this offset ...
V_DROP = 7.5                                      # ... this far below the mast tops


def gallery(mats: dict, lite: bool, columns: bool = True) -> MB:
    mb = MB()
    tb = L.tier_bounds()[2]
    z = tb['z1']
    off_c = tb['off1'] + 0.55
    off_in = L.outer_off()
    top = z + COL_PROFILE[-1][1]
    zr = L.OUTSIDE_Z + L.STOREYS * L.STOREY_H + L.ATTIC_H - 0.35
    a = {'lite': int(lite)}
    if columns:
        P = perimeter(off_c)
        n = int(P / 4.6)
        for k in range(n):
            t = float(t_at_arc(off_c, P * (k + 0.5) / n))
            x, y, _ = pt(t, off_c, 0)
            lathe(mb, COL_PROFILE, 6, (x, y, z), mats['column'], {'lite': 0}, cap=False)
    # the beam on the columns, then the tiled roof up to the outer wall, then the gallery's back wall
    beam = [(off_c + 0.5, top), (off_c - 0.5, top), (off_c - 0.5, top + 0.85)]      # underside, then the front
    for p, ts in ring_sweeps(off_c, None, None, per=4):
        sweep(mb, beam, ts, face_fn=lambda i, j: (mats['trim'], a))
        sweep(mb, [(off_in, top), (off_c + 0.5, top)], ts, face_fn=lambda i, j: (mats['dim'], a))     # the ceiling
        sweep(mb, [(off_c - 0.5, top + 0.85), (off_in, zr)], ts, face_fn=lambda i, j: (mats['roof'], a))
        sweep(mb, [(off_in, z), (off_in, top)], ts, face_fn=lambda i, j: (mats['dim'], a))
    return mb


def mast_ts() -> list[float]:
    off = L.facade_off()
    return [arc_t(off, (2 * k + 0.5) * L.N_BAYS / (2 * N_MASTS)) for k in range(N_MASTS)]


def mast_top(t: float) -> np.ndarray:
    z1 = L.OUTSIDE_Z + L.STOREYS * L.STOREY_H + L.ATTIC_H
    return np.asarray(bend(t, L.facade_off(), 0, 0.42, z1 + 8.5))


def masts(mats: dict) -> MB:
    """Masts standing in stone consoles on the attic's outer face (the velarium's rigging hangs from their tops)."""
    mb = MB()
    off = L.facade_off()
    z1 = L.OUTSIDE_Z + L.STOREYS * L.STOREY_H + L.ATTIC_H
    for t in mast_ts():
        for zc in (z1 - 4.6, z1 - 1.0):
            bbox(mb, t, off, -0.32, 0.32, 0.0, 0.7, zc - 0.35, zc, mats['trim'], {'lite': 1}, skip=('in',))
        x, y, _ = bend(t, off, 0, 0.42, 0)
        lathe(mb, [(0.17, z1 - 5.0), (0.15, z1 + 6.0), (0.11, z1 + 8.6)], 6, (x, y, 0), mats['wood'], {'lite': 1})
    return mb


def _rope(mb: MB, p0, p1, sag: float, mat: int, r: float = 0.05, lite: bool = True) -> None:
    """A rope as two crossed ribbons along a sagging curve (the velarium group is double-sided)."""
    n = 6
    P = [np.asarray(p0) * (1 - s) + np.asarray(p1) * s - np.array([0, 0, sag * 4 * s * (1 - s)]) for s in np.linspace(0, 1, n + 1)]
    side = np.cross(P[-1] - P[0], [0, 0, 1.0])
    side = side / max(1e-6, float(np.linalg.norm(side))) * r
    s = np.concatenate([[0.0], np.cumsum([np.linalg.norm(P[i + 1] - P[i]) for i in range(n)])])
    for o in (side, np.array([0, 0, r])):
        mb.island([[P[i] - o, P[i + 1] - o, P[i + 1] + o, P[i] + o] for i in range(n)],
                  [[(s[i], 0), (s[i + 1], 0), (s[i + 1], 2 * r), (s[i], 2 * r)] for i in range(n)], mat, {'lite': int(lite)})


def velarium(mats: dict) -> MB:
    mb = MB()
    ts = mast_ts()
    tops = [mast_top(t) for t in ts]
    drawn = [DRAWN[0] < (t % (2 * math.pi)) < DRAWN[1] for t in ts]
    inner = []
    for t, top in zip(ts, tops):
        x, y, _ = pt(t, V_INNER, 0)
        inner.append(np.array([x, y, top[2] - V_DROP]))
    for i in range(len(ts)):
        j = (i + 1) % len(ts)
        if drawn[i] and drawn[j]:
            awning(mb, tops[i], tops[j], inner[i], inner[j], mats, i)
    for i, (t, top) in enumerate(zip(ts, tops)):
        _rope(mb, top, inner[i], 1.2 if drawn[i] else 2.4, mats['rope'], 0.05)
        if not drawn[i]:
            furled(mb, top, inner[i], mats)
        if i % 2 == 0:
            pennant(mb, top + np.array([0, 0, 0.1]), t, mats['pennant'][i // 2 % len(mats['pennant'])])
    return mb


def awning(mb: MB, a0, a1, b0, b1, mats: dict, k: int) -> None:
    """One drawn awning between two masts: rigged at its four corners, sagging in the middle, a striped valance on
    its free inner edge. Normals face down (what the arena sees); UVMap u runs across in metres (the stripes)."""
    nu, nv = 5, 7
    width = float(np.linalg.norm(a1 - a0))
    G = np.zeros((nv + 1, nu + 1, 3))
    for jv in range(nv + 1):
        s = jv / nv
        for iu in range(nu + 1):
            u = iu / nu
            p = (a0 * (1 - u) + a1 * u) * (1 - s) + (b0 * (1 - u) + b1 * u) * s
            sag = 1.1 * 4 * u * (1 - u) * (0.4 + 0.6 * math.sin(math.pi * s)) + 0.5 * math.sin(math.pi * s)
            G[jv, iu] = p - np.array([0, 0, sag])
    length = float(np.linalg.norm((a0 + a1) / 2 - (b0 + b1) / 2))
    base = mb.verts(G.reshape(-1, 3))
    mat = mats['awning'][k % len(mats['awning'])]
    for jv in range(nv):
        for iu in range(nu):
            q = (base + jv * (nu + 1) + iu, base + (jv + 1) * (nu + 1) + iu, base + (jv + 1) * (nu + 1) + iu + 1, base + jv * (nu + 1) + iu + 1)
            uv = [(width * iu / nu, length * (1 - jv / nv)), (width * iu / nu, length * (1 - (jv + 1) / nv)),
                  (width * (iu + 1) / nu, length * (1 - (jv + 1) / nv)), (width * (iu + 1) / nu, length * (1 - jv / nv))]
            mb.face(q, uv, uv, mat, {'lite': 1})
    # the valance: a hanging strip along the free edge, cut into tabs
    edge = G[nv]
    drop = np.array([0, 0, 0.9])
    mb.island([[edge[iu + 1] - drop, edge[iu] - drop, edge[iu], edge[iu + 1]] for iu in range(nu)],       # faces the arena
              [[(width * (iu + 1) / nu, 0.0), (width * iu / nu, 0.0), (width * iu / nu, 0.9), (width * (iu + 1) / nu, 0.9)] for iu in range(nu)],
              mats['valance'], {'lite': 1})


def furled(mb: MB, top, inner, mats: dict) -> None:
    """A furled awning: a rolled bundle lashed along the first few metres of its rope."""
    d = inner - top
    for f0, f1, r in ((0.12, 0.42, 0.42), (0.42, 0.55, 0.3)):
        p0, p1 = top + d * f0, top + d * f1
        axis = (p1 - p0) / np.linalg.norm(p1 - p0)
        side = np.cross(axis, [0, 0, 1.0])
        side /= np.linalg.norm(side)
        up = np.cross(side, axis)
        ring = [side * math.cos(2 * math.pi * k / 6) * r + up * math.sin(2 * math.pi * k / 6) * r * 0.8 for k in range(7)]
        Lb = float(np.linalg.norm(p1 - p0))
        for k in range(6):
            mb.quad([p0 + ring[k], p0 + ring[k + 1], p1 + ring[k + 1], p1 + ring[k]],
                    [(k * 0.4, 0), ((k + 1) * 0.4, 0), ((k + 1) * 0.4, Lb), (k * 0.4, Lb)], mats['furled'], {'lite': 1})


def pennant(mb: MB, top, t: float, mat: int) -> None:
    nx, ny = math.cos(t + 1.9), math.sin(t + 1.9)
    p = [top, top + np.array([0, 0, -1.3]), top + np.array([nx * 3.2, ny * 3.2, -0.75])]
    mb.quad(p, [(0, 1.3), (0, 0), (3.2, 0.55)], mat, {'lite': 1})
