"""Dressing for the Crown Amphitheatre's close-up surfaces (what the battle cameras see): the podium wall's pilasters,
recessed panels and postern doors; bronze medallions with the Guild emblem (gate attics, the Patrons' box front, the
statues' plinths); cloth festoons along the box's railing.
"""
from __future__ import annotations

import math

import numpy as np

from crown_geo import MB, bend, fbox, frame, perimeter, t_at_arc
import crown_layout as L
from crown_gates import BOX_FLOOR, BOX_FRONT, BOX_W, FRONT_D
from crown_props import statue_spots


def medallion(mb: MB, P, x: float, d: float, z: float, r: float, mat: int, rim: int, sides: int = 12) -> None:
    """A round bronze boss facing the arena (−d) in frame P: UV 0..1 across it (the material draws the emblem), with
    a raised rim ring."""
    ring = [(x + r * math.cos(2 * math.pi * k / sides), z + r * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
    pts = [P(px, d - 0.08, pz) for px, pz in ring][::-1]
    uv = [(0.5 + 0.5 * math.cos(2 * math.pi * k / sides), 0.5 + 0.5 * math.sin(2 * math.pi * k / sides)) for k in range(sides)][::-1]
    mb.quad(pts, uv, mat, {'lite': 1})
    ro = [(x + (r + 0.12) * math.cos(2 * math.pi * k / sides), z + (r + 0.12) * math.sin(2 * math.pi * k / sides)) for k in range(sides + 1)]
    ri = ring + ring[:1]
    for k in range(sides):
        q = [P(ri[k][0], d - 0.1, ri[k][1]), P(ri[k + 1][0], d - 0.1, ri[k + 1][1]), P(ro[k + 1][0], d - 0.04, ro[k + 1][1]), P(ro[k][0], d - 0.04, ro[k][1])]
        mb.quad(q, [(0, 0), (0.3, 0), (0.3, 0.12), (0, 0.12)], rim, {'lite': 1})


def podium_dress(mats: dict) -> MB:
    """Pilasters every ~6.5 m round the podium, a recessed panel between each pair, a postern door in every fourth
    bay and a bronze medallion over each door (none where the gatehouses and the box stand)."""
    mb = MB()
    H = L.PODIUM_H
    P0 = perimeter(0.0)
    n = int(P0 / 6.5)
    ts = [float(t_at_arc(0.0, P0 * k / n)) for k in range(n)]
    ok = [L.zone(t) is None for t in ts]
    for k, t in enumerate(ts):
        if not ok[k]:
            continue
        fbox(mb, lambda x, d, z, t=t: bend(t, 0.0, x, d, z), -0.32, 0.32, -0.16, 0.0, 0.5, H - 0.34, mats['trim'], {'lite': 1}, skip=('out', 'bottom'))
        k2 = (k + 1) % n
        if not ok[k2]:
            continue
        tm = (t + ts[k2] + (2 * math.pi if ts[k2] < t else 0)) / 2
        w = P0 / n

        def P(x, d, z, tm=tm):
            return bend(tm, 0.0, x, d, z)
        if k % 4 == 1:
            door(mb, P, mats)
            medallion(mb, P, 0.0, 0.0, H - 0.75, 0.32, mats['emblem'], mats['bronze'], 10)
        else:
            panel(mb, P, w - 1.3, 0.75, H - 0.75, mats)
    return mb


def panel(mb: MB, P, w: float, z0: float, z1: float, mats: dict) -> None:
    """A moulded frame proud of the wall, with a darker inset panel."""
    f = 0.14
    a = {'lite': 1}
    for (x0, x1, za, zb) in ((-w / 2, w / 2, z0, z0 + f), (-w / 2, w / 2, z1 - f, z1), (-w / 2, -w / 2 + f, z0, z1), (w / 2 - f, w / 2, z0, z1)):
        fbox(mb, P, x0, x1, -0.07, 0.0, za, zb, mats['trim'], a, skip=('out', 'bottom'))
    q = [(-w / 2 + f, z0 + f), (w / 2 - f, z0 + f), (w / 2 - f, z1 - f), (-w / 2 + f, z1 - f)]
    mb.quad([P(x, -0.01, z) for x, z in q][::-1], [(x, z) for x, z in q][::-1], mats['inset'], a)


def door(mb: MB, P, mats: dict) -> None:
    """A small arched postern door in the podium (dark studded wood in a stone frame)."""
    a = {'lite': 1}
    w, h, k = 1.3, 2.05, 6
    pts = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h - w / 2)]
    pts += [(w / 2 * math.cos(math.pi * i / k), h - w / 2 + w / 2 * math.sin(math.pi * i / k)) for i in range(1, k)]
    pts += [(-w / 2, h - w / 2)]
    mb.quad([P(x, -0.02, z) for x, z in pts][::-1], [(x, z) for x, z in pts][::-1], mats['door'], a)
    fbox(mb, P, -w / 2 - 0.22, -w / 2, -0.12, 0.0, 0.0, h - w / 2, mats['trim'], a, skip=('out', 'bottom'))
    fbox(mb, P, w / 2, w / 2 + 0.22, -0.12, 0.0, 0.0, h - w / 2, mats['trim'], a, skip=('out', 'bottom'))
    fbox(mb, P, -0.2, 0.2, -0.14, 0.0, h - 0.12, h + 0.22, mats['trim'], a, skip=('out', 'bottom'))


def monument_dress(mats: dict) -> MB:
    """Medallions on the gate attics and the box front, plaques on the plinths, festoons on the box's railing."""
    mb = MB()
    for tag in ('A', 'B'):
        P = frame(L.GATE_T[tag])
        medallion(mb, P, 0.0, FRONT_D, 12.3, 0.75, mats['emblem'], mats['bronze'], 16)
    P = frame(L.BOX_T)
    for x in (-6.0, -2.0, 2.0, 6.0):
        medallion(mb, P, x, BOX_FRONT, 2.15, 0.62, mats['emblem'], mats['bronze'], 14)
    for s in statue_spots():
        x, y = s['p']
        yaw = s['face']
        cx, cy = math.cos(yaw), math.sin(yaw)

        def Q(px, d, z, x=x, y=y, cx=cx, cy=cy):
            # a frame whose −d looks along the plinth's facing (x along = (sin, −cos), left-handed like crown_geo.frame)
            return (x + cy * px - cx * d, y - cx * px - cy * d, z)
        medallion(mb, Q, 0.0, -0.81, 0.92, 0.36, mats['emblem'], mats['bronze'], 10)
    festoons(mb, frame(L.BOX_T), mats)
    P = frame(L.BOX_T)
    for sx in (-1, 1):                      # a framed panel on each of the box's tall side walls
        def F(a, b, z, sx=sx):
            return P(sx * (BOX_W + 0.5) - sx * b, 1.3 + sx * a, z)
        panel(mb, F, 5.2, 5.4, 10.3, mats)
    return mb


def festoons(mb: MB, P, mats: dict) -> None:
    """Cloth swags hanging in loops along the box's railing, a gold tassel point at each column."""
    a = {'lite': 1}
    xs = [-BOX_W, -7.3, -4.95, -2.6, 0.0, 2.6, 4.95, 7.3, BOX_W]
    z = BOX_FLOOR + 0.85
    for x0, x1 in zip(xs, xs[1:]):
        n = 6
        top = [(x0 + (x1 - x0) * i / n, z) for i in range(n + 1)]
        bot = [(x0 + (x1 - x0) * i / n, z - 0.25 - 0.55 * math.sin(math.pi * i / n)) for i in range(n + 1)]
        qs = [[top[i], top[i + 1], bot[i + 1], bot[i]] for i in range(n)]
        mb.island([[P(px, BOX_FRONT - 0.06, pz) for px, pz in q] for q in qs], [[(px, pz) for px, pz in q] for q in qs], mats['festoon'], a)
