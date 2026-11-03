"""The Crown Amphitheatre's hanging banners, each with the Guild emblem (crown_mats2.banner; UV 0..1, v = 1 at the
top): on the podium wall between the gates, flanking each gate's arch (A teal, B coral), from the top gallery's beam
all round, and on the back wall of the Patrons' box (plum).
"""
from __future__ import annotations

import math

from crown_geo import MB, frame, perimeter, t_at_arc
import crown_layout as L
from crown_gates import BOX_W, FRONT_D
from crown_top import COL_PROFILE

COLOURS = ('teal', 'coral', 'plum')


def cloth(mb: MB, P, x: float, d: float, top: float, w: float, length: float, mat: int, seed: float = 0.0,
          notch: float = 0.45, lite: bool = True) -> None:
    """A banner hanging in the frame P (x along, d out, z up) facing the arena, with a swallowtail foot."""
    nu, nv = 4, 8
    G = []
    for jv in range(nv + 1):
        v = 1.0 - jv / nv
        row = []
        for iu in range(nu + 1):
            u = iu / nu
            z = top - (1 - v) * length
            if jv == nv:
                z += notch * (1 - abs(u - 0.5) * 2)
            wave = 0.05 * math.sin(u * math.pi * 2 + v * 2.1 + seed) * (1 - v * 0.7) - 0.03 * (1 - v)
            row.append((P(x + (u - 0.5) * w, d + wave, z), (u, max(0.0, 1 - (top - z) / length))))
        G.append(row)
    qs = [[G[jv][iu], G[jv][iu + 1], G[jv + 1][iu + 1], G[jv + 1][iu]] for jv in range(nv) for iu in range(nu)]   # faces the arena
    mb.island([[p for p, _ in q] for q in qs], [[uv for _, uv in q] for q in qs], mat, {'lite': int(lite), 'aspect': length / w})


def build_banners(mats: dict) -> MB:
    mb = MB()
    k = 0
    # the podium wall, between the gates and clear of the box and its statues
    off = -0.3
    Pm = perimeter(0.0)
    n = 16
    for i in range(n):
        t = float(t_at_arc(0.0, Pm * (i + 0.5) / n))
        if L.zone(t) is not None or abs(L.arc_dist(t, L.BOX_T)) < 14.0 or min(abs(L.arc_dist(t, g)) for g in L.GATE_T.values()) < 13.0:
            continue
        cloth(mb, frame(t, off), 0.0, -0.05, L.PODIUM_H + L.PARAPET[2] - 0.12, 1.5, 2.7, mats['banner'][COLOURS[k % 3]], k)
        k += 1
    # flanking each gate's arch
    for tag, colour in (('A', 'teal'), ('B', 'coral')):
        P = frame(L.GATE_T[tag])
        for sx in (-1, 1):
            cloth(mb, P, sx * 5.25, FRONT_D - 0.1, 10.1, 1.3, 5.4, mats['banner'][colour], sx)
    # from the top gallery's beam, all round
    tb = L.tier_bounds()[2]
    off_c = tb['off1'] + 0.55
    top = tb['z1'] + COL_PROFILE[-1][1] + 0.75
    Pc = perimeter(off_c)
    n = 20
    for i in range(n):
        t = float(t_at_arc(off_c, Pc * (i + 0.25) / n))
        cloth(mb, frame(t, off_c), 0.0, -0.62, top, 2.6, 5.6, mats['banner'][COLOURS[i % 3]], i * 1.7, notch=0.7, lite=i % 2 == 0)
    # the Patrons' box
    P = frame(L.BOX_T)
    for sx in (-1, 1):
        cloth(mb, P, sx * (BOX_W * 0.5), 4.55, 10.0, 2.1, 4.4, mats['banner']['plum'], sx * 2)
    return mb
