"""The Crown Amphitheatre's outer wall: three arcaded storeys and an attic (seen in the fly-in and the establishing
view), and the ambulatory behind the arches (its floors and back wall, seen through them).

Each storey: arched bays with a moulded archivolt and a keystone, engaged half-columns between the bays standing on
pedestals and carrying a string course. The attic: flat pilasters, small square windows and a deep top cornice.
Sweep profiles that face outward run top to bottom (crown_geo.sweep faces the left of the profile's direction).
"""
from __future__ import annotations

import math

from crown_geo import MB, bbox, bend, perimeter, pt, sweep, t_at_arc
import crown_layout as L


def arc_t(off: float, k: float) -> float:
    """The angle at arc position k (in bays) round the ellipse at offset off."""
    return float(t_at_arc(off, perimeter(off) * k / L.N_BAYS))


def unwrap(ts: list[float]) -> list[float]:
    for i in range(1, len(ts)):
        while ts[i] < ts[i - 1]:
            ts[i] += 2 * math.pi
    return ts


def _ccw(poly) -> bool:
    return sum(x1 * z2 - x2 * z1 for (x1, z1), (x2, z2) in zip(poly, poly[1:] + poly[:1])) > 0


def arch_bay(mb: MB, j: int, off: float, depth: float, z0: float, h: float, open_frac: float, spring: float,
             mats: dict, k: int, detail: bool) -> None:
    """Bay j of a storey: the outer face (at off + depth) with an arched opening, the opening's rim through the wall,
    and (detail) a moulded archivolt and a keystone. x along the bay maps linearly between its two edge angles, so
    neighbouring bays meet exactly."""
    oo = off + depth
    ta, tb = unwrap([arc_t(oo, j - 0.5), arc_t(oo, j + 0.5)])
    w = perimeter(oo) / L.N_BAYS
    ow = w * open_frac

    def P(x, d, z):
        return pt(ta + (x / w + 0.5) * (tb - ta), off + d, z)
    a = {'lite': 1}
    arc = [(-ow / 2 * math.cos(math.pi * i / k), spring + ow / 2 * math.sin(math.pi * i / k)) for i in range(k + 1)]
    polys = [[(-w / 2, 0), (-ow / 2, 0), (-ow / 2, spring), (-ow / 2, h), (-w / 2, h)],
             [(ow / 2, 0), (w / 2, 0), (w / 2, h), (ow / 2, h), (ow / 2, spring)]]
    polys += [[(x1, z1), (x2, z2), (x2, h), (x1, h)] for (x1, z1), (x2, z2) in zip(arc, arc[1:])]
    polys = [p if _ccw(p) else p[::-1] for p in polys]
    mb.island([[P(x, depth, z0 + z) for x, z in p] for p in polys], [[(x, z0 + z) for x, z in p] for p in polys], mats['wall'], a)
    rim = [(-ow / 2, 0)] + arc + [(ow / 2, 0)]
    s = [0.0]
    for (x1, z1), (x2, z2) in zip(rim, rim[1:]):
        s.append(s[-1] + math.hypot(x2 - x1, z2 - z1))
    mb.island([[P(x1, 0, z0 + z1), P(x2, 0, z0 + z2), P(x2, depth, z0 + z2), P(x1, depth, z0 + z1)] for (x1, z1), (x2, z2) in zip(rim, rim[1:])],
              [[(s[i], 0), (s[i + 1], 0), (s[i + 1], depth), (s[i], depth)] for i in range(len(rim) - 1)], mats['rim'], a)
    if not detail:
        return
    a = {'lite': 0}
    band, proud = 0.42, 0.09
    rin = [(-ow / 2 * math.cos(math.pi * i / k), spring + ow / 2 * math.sin(math.pi * i / k)) for i in range(k + 1)]
    rout = [(-(ow / 2 + band) * math.cos(math.pi * i / k), spring + (ow / 2 + band) * math.sin(math.pi * i / k)) for i in range(k + 1)]
    D = depth + proud
    qs = [[rin[i], rout[i], rout[i + 1], rin[i + 1]] for i in range(k)]
    qs = [q if _ccw(q) else q[::-1] for q in qs]
    mb.island([[P(x, D, z0 + z) for x, z in q] for q in qs], [[(x, z0 + z) for x, z in q] for q in qs], mats['trim'], a)
    s = [0.0]
    for (x1, z1), (x2, z2) in zip(rout, rout[1:]):
        s.append(s[-1] + math.hypot(x2 - x1, z2 - z1))
    mb.island([[P(rout[i][0], depth, z0 + rout[i][1]), P(rout[i][0], D, z0 + rout[i][1]), P(rout[i + 1][0], D, z0 + rout[i + 1][1]),
                P(rout[i + 1][0], depth, z0 + rout[i + 1][1])] for i in range(k)],
              [[(s[i], 0), (s[i], proud), (s[i + 1], proud), (s[i + 1], 0)] for i in range(k)], mats['trim'], a)
    top = spring + ow / 2
    bbox(mb, (ta + tb) / 2, oo, -0.32, 0.32, 0.0, proud + 0.12, z0 + top - 0.28, z0 + top + band + 0.14, mats['trim'], a, skip=('bottom', 'in'))


def half_column(mb: MB, t: float, off: float, z0: float, z1: float, mats: dict) -> None:
    """An engaged half-column (half an octagon) on a pedestal, with a capital block, against the face at off."""
    a = {'lite': 0}
    r = 0.42
    bbox(mb, t, off, -0.62, 0.62, 0.0, 0.64, z0, z0 + 1.15, mats['trim'], a, skip=('bottom', 'in'))
    ring = [(r * math.cos(math.pi * i / 4), r * math.sin(math.pi * i / 4)) for i in range(5)]
    zs, ze = z0 + 1.15, z1 - 0.55
    for (x1, d1), (x2, d2) in zip(ring, ring[1:]):
        L1 = math.hypot(x2 - x1, d2 - d1)
        q = [bend(t, off, -x, d, z) for x, d, z in ((x1, d1, zs), (x2, d2, zs), (x2, d2, ze), (x1, d1, ze))]
        mb.quad(q, [(0, zs), (L1, zs), (L1, ze), (0, ze)], mats['wall'], a)
    bbox(mb, t, off, -0.6, 0.6, 0.0, 0.62, z1 - 0.55, z1, mats['trim'], a, skip=('bottom', 'in'))


def ring_sweeps(off: float, prof, mats_of, per: int = 6) -> list:
    """(profile, ts) pairs for a moulding all round the wall, one island per `per` bays."""
    out = []
    for i0 in range(0, L.N_BAYS, per):
        ts = unwrap([arc_t(off, k - 0.5) for k in range(i0, i0 + per + 1)])
        out.append((prof, ts))
    return out


def string_course(mb: MB, off: float, z: float, mats: dict, deep: float = 0.42) -> None:
    """A moulded band round the whole façade (runs top to bottom, so it faces out)."""
    prof = [(off, z + 0.2), (off + deep, z + 0.12), (off + deep, z - 0.05), (off + 0.16, z - 0.2), (off + 0.16, z - 0.62), (off, z - 0.75)]
    for p, ts in ring_sweeps(off, prof, None):
        sweep(mb, p, ts, face_fn=lambda i, j: (mats['trim'], {'lite': 1}))


def attic(mb: MB, off_in: float, off_out: float, mats: dict) -> None:
    z0 = L.OUTSIDE_Z + L.STOREYS * L.STOREY_H
    z1 = z0 + L.ATTIC_H
    prof = [(off_in, z1 - 0.35), (off_in, z1), (off_out + 0.55, z1), (off_out + 0.55, z1 - 0.25), (off_out + 0.25, z1 - 0.7),
            (off_out, z1 - 0.9), (off_out, z0 + 0.2)]
    last = len(prof) - 2
    for p, ts in ring_sweeps(off_out, prof, None):
        sweep(mb, p, ts, face_fn=lambda i, j: (mats['wall'] if i == last else mats['trim'], {'lite': 1}))
    for j in range(L.N_BAYS):
        tb = arc_t(off_out, j + 0.5)
        bbox(mb, tb, off_out, -0.45, 0.45, 0.0, 0.14, z0 + 0.2, z1 - 0.9, mats['trim'], {'lite': 0}, skip=('bottom', 'in'))
        if j % 2 == 0:
            bbox(mb, arc_t(off_out, j), off_out, -0.7, 0.7, 0.0, 0.025, z0 + 1.7, z0 + 3.0, mats['void'], {'lite': 1},
                 skip=('bottom', 'top', 'in', 'left', 'right'))


def build_facade(mats: dict, k_arc: int = 7) -> MB:
    mb = MB()
    off_in = L.outer_off()
    off_out = off_in + L.FACADE_D
    for s in range(L.STOREYS):
        z0 = L.OUTSIDE_Z + s * L.STOREY_H
        for j in range(L.N_BAYS):
            arch_bay(mb, j, off_in, L.FACADE_D, z0, L.STOREY_H, 0.6 if s < 2 else 0.56, L.STOREY_H * 0.6, mats, k_arc, True)
            half_column(mb, arc_t(off_out, j + 0.5), off_out, z0, z0 + L.STOREY_H - 0.75, mats)
        string_course(mb, off_out, z0 + L.STOREY_H, mats)
    attic(mb, off_in, off_out, mats)
    return mb


def build_ambulatory(mats: dict) -> MB:
    """Behind the arches: the ground-floor paving, the upper floors (ceiling and top) and the back wall."""
    mb = MB()
    off_in = L.outer_off()
    back = off_in - 4.6
    z_top = L.OUTSIDE_Z + L.STOREYS * L.STOREY_H - 1.0
    a = {'lite': 1}
    for p, ts in ring_sweeps(off_in, None, None, per=3):
        sweep(mb, [(back, z_top), (back, L.OUTSIDE_Z)], ts, face_fn=lambda i, j: (mats['dim'], a))
        sweep(mb, [(back, L.OUTSIDE_Z), (off_in + L.FACADE_D, L.OUTSIDE_Z)], ts, face_fn=lambda i, j: (mats['floor'], a))
        for s in range(1, L.STOREYS):
            z = L.OUTSIDE_Z + s * L.STOREY_H
            sweep(mb, [(off_in, z - 0.6), (back, z - 0.6)], ts, face_fn=lambda i, j: (mats['dim'], a))
            sweep(mb, [(back, z), (off_in, z)], ts, face_fn=lambda i, j: (mats['floor'], a))
    return mb
