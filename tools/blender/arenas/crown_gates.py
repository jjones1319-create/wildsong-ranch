"""The Crown Amphitheatre's two gatehouses (on the long axis: A at -x, B at +x) and the Patrons' box (on +y).

A gatehouse: a frontispiece standing 2.2 m out on the sand, its arch with a half-raised iron portcullis, paired
half-columns, an entablature and an attic with a bronze medallion; a vaulted tunnel behind; a paved ramp down onto
the sand between low walls; a terrace over the cut-away seats behind it. The Patrons' box: a marble balcony with a
railing, slender columns under a cloth canopy, a back wall hung with the Guild's banners.
Both are built in straight local frames (crown_geo.frame: x along, d out of the arena, z up).
"""
from __future__ import annotations

import math

from crown_geo import MB, fbox, frame, lathe, sweep, span_ts, speed
import crown_layout as L

FRONT_D = -2.2          # the gatehouse front, out on the sand
GATE_W = 7.2            # half its width
ARCH_W, ARCH_SPRING = 6.0, 6.0
BOX_FRONT = -2.0
BOX_W = 8.0
BOX_FLOOR = 4.4


def _cw(poly) -> list:
    a = sum(x1 * z2 - x2 * z1 for (x1, z1), (x2, z2) in zip(poly, poly[1:] + poly[:1]))
    return poly if a < 0 else poly[::-1]


def arched_front(mb: MB, P, half: float, d: float, depth: float, h: float, ow: float, spring: float, mats: dict,
                 a: dict, k: int = 9) -> None:
    """A wall face at d (facing the arena) from x = -half..half, z 0..h, with an arched opening and its rim."""
    arc = [(-ow / 2 * math.cos(math.pi * i / k), spring + ow / 2 * math.sin(math.pi * i / k)) for i in range(k + 1)]
    polys = [[(-half, 0), (-ow / 2, 0), (-ow / 2, spring), (-ow / 2, h), (-half, h)],
             [(ow / 2, 0), (half, 0), (half, h), (ow / 2, h), (ow / 2, spring)]]
    polys += [[(x1, z1), (x2, z2), (x2, h), (x1, h)] for (x1, z1), (x2, z2) in zip(arc, arc[1:])]
    polys = [_cw(p) for p in polys]
    mb.island([[P(x, d, z) for x, z in p] for p in polys], [[(x, z) for x, z in p] for p in polys], mats['face'], a)
    rim = [(-ow / 2, 0)] + arc + [(ow / 2, 0)]
    s = [0.0]
    for (x1, z1), (x2, z2) in zip(rim, rim[1:]):
        s.append(s[-1] + math.hypot(x2 - x1, z2 - z1))
    mb.island([[P(x1, d, z1), P(x2, d, z2), P(x2, d + depth, z2), P(x1, d + depth, z1)] for (x1, z1), (x2, z2) in zip(rim, rim[1:])],
              [[(s[i], 0), (s[i + 1], 0), (s[i + 1], depth), (s[i], depth)] for i in range(len(rim) - 1)], mats['rim'], a)
    band = 0.5
    rin = arc
    rout = [(-(ow / 2 + band) * math.cos(math.pi * i / k), spring + (ow / 2 + band) * math.sin(math.pi * i / k)) for i in range(k + 1)]
    qs = [_cw([rin[i], rout[i], rout[i + 1], rin[i + 1]]) for i in range(k)]
    mb.island([[P(x, d - 0.1, z) for x, z in q] for q in qs], [[(x, z) for x, z in q] for q in qs], mats['trim'], a)
    fbox(mb, P, -0.38, 0.38, d - 0.22, d, spring + ow / 2 - 0.3, spring + ow / 2 + band + 0.2, mats['trim'], a, skip=('out',))


def half_col(mb: MB, P, x: float, d: float, z0: float, z1: float, mats: dict, a: dict, r: float = 0.4) -> None:
    fbox(mb, P, x - 0.58, x + 0.58, d - 0.6, d, z0, z0 + 1.2, mats['trim'], a, skip=('out', 'bottom'))
    ring = [(x + r * math.cos(math.pi * i / 4), d - r * math.sin(math.pi * i / 4)) for i in range(5)]
    for (x1, d1), (x2, d2) in zip(ring[::-1], ring[::-1][1:]):
        L1 = math.hypot(x2 - x1, d2 - d1)
        mb.quad([P(x1, d1, z0 + 1.2), P(x2, d2, z0 + 1.2), P(x2, d2, z1 - 0.6), P(x1, d1, z1 - 0.6)][::-1],
                [(0, 0), (L1, 0), (L1, z1 - z0), (0, z1 - z0)][::-1], mats['face'], a)
    fbox(mb, P, x - 0.55, x + 0.55, d - 0.58, d, z1 - 0.6, z1, mats['trim'], a, skip=('out',))


def gatehouse(tag: str, mats: dict) -> MB:
    mb = MB()
    t = L.GATE_T[tag]
    P = frame(t)
    a = {'lite': 1}
    H = 13.4
    arched_front(mb, P, GATE_W, FRONT_D, 2.2, 10.2, ARCH_W, ARCH_SPRING, mats, a)
    for x in (-6.35, -4.15, 4.15, 6.35):
        half_col(mb, P, x, FRONT_D, 0.0, 10.2, mats, a)
    fbox(mb, P, -GATE_W - 0.35, GATE_W + 0.35, FRONT_D - 0.75, FRONT_D + 0.2, 10.2, 11.25, mats['trim'], a, skip=('out',))
    fbox(mb, P, -GATE_W, GATE_W, FRONT_D, 0.0, 11.25, H - 0.4, mats['face'], a, skip=('bottom',))
    fbox(mb, P, -GATE_W - 0.3, GATE_W + 0.3, FRONT_D - 0.45, 0.25, H - 0.4, H, mats['trim'], a, skip=('bottom',))
    for sx in (-1, 1):   # the returns of the front block, back to the podium
        fbox(mb, P, GATE_W if sx > 0 else -GATE_W - 0.3, GATE_W + 0.3 if sx > 0 else -GATE_W, FRONT_D, 3.0, 0.0, 10.2, mats['face'], a,
             skip=('out', 'top', 'bottom', 'left' if sx > 0 else 'right'))
    tunnel(mb, P, mats)
    portcullis(mb, P, mats)
    ramp(mb, P, mats)
    wing(mb, t, L.GATE_HALF, mats)
    return mb


def tunnel(mb: MB, P, mats: dict) -> None:
    a = {'lite': 1}
    w, d0, d1 = ARCH_W / 2, FRONT_D, 22.0
    for sx in (-1, 1):
        q = [(sx * w, d0, 0.0), (sx * w, d1, 0.0), (sx * w, d1, ARCH_SPRING), (sx * w, d0, ARCH_SPRING)]
        if sx < 0:
            q = q[::-1]
        mb.quad([P(*p) for p in q], [(p[1], p[2]) for p in q], mats['dim'], a)
    k = 8
    for i in range(k):
        a0, a1 = math.pi * i / k, math.pi * (i + 1) / k
        x0, z0 = -w * math.cos(a0), ARCH_SPRING + w * math.sin(a0)
        x1, z1 = -w * math.cos(a1), ARCH_SPRING + w * math.sin(a1)
        mb.quad([P(x1, d0, z1), P(x1, d1, z1), P(x0, d1, z0), P(x0, d0, z0)], [(1, d0), (1, d1), (0, d1), (0, d0)], mats['dim'], a)
    mb.quad([P(-w, d1, ARCH_SPRING + w), P(w, d1, ARCH_SPRING + w), P(w, d1, 0), P(-w, d1, 0)], [(0, 9), (6, 9), (6, 0), (0, 0)], mats['void'], a)
    zf = lambda d: 0.55 + (d - d0) / (d1 - d0) * 0.45  # noqa: E731  (the tunnel floor climbs toward the plaza)
    n = 6
    for i in range(n):
        da, db = d0 + (d1 - d0) * i / n, d0 + (d1 - d0) * (i + 1) / n
        mb.quad([P(-w, da, zf(da)), P(w, da, zf(da)), P(w, db, zf(db)), P(-w, db, zf(db))][::-1], [(-w, da), (w, da), (w, db), (-w, db)][::-1], mats['paving'], a)


def portcullis(mb: MB, P, mats: dict) -> None:
    """The iron grille, raised to 3.6 m: bars clipped to the arch, cross bars, spiked feet."""
    a = {'lite': 1}
    d = FRONT_D + 1.0
    bottom = 3.6
    r = ARCH_W / 2
    for i in range(9):
        x = -r + 0.35 + i * (ARCH_W - 0.7) / 8
        top = ARCH_SPRING + math.sqrt(max(0.0, r * r - x * x)) - 0.05
        fbox(mb, P, x - 0.06, x + 0.06, d - 0.06, d + 0.06, bottom, top, mats['iron'], a, skip=('top', 'bottom'))
        mb.quad([P(x - 0.06, d - 0.06, bottom), P(x + 0.06, d - 0.06, bottom), P(x, d - 0.06, bottom - 0.32)], [(0, 0.3), (0.12, 0.3), (0.06, 0)], mats['iron'], a)
    for z in (bottom + 0.35, bottom + 1.5, bottom + 2.65, bottom + 3.8):
        half = math.sqrt(max(0.0, r * r - max(0.0, z - ARCH_SPRING) ** 2)) - 0.1
        fbox(mb, P, -half, half, d - 0.09, d - 0.03, z - 0.07, z + 0.07, mats['iron'], a, skip=('out',))


def ramp(mb: MB, P, mats: dict) -> None:
    """The paved ramp from the arch down onto the sand, between low walls ending in the statues' plinths."""
    a = {'lite': 1}
    w, d0, d1 = ARCH_W / 2 + 0.2, FRONT_D, FRONT_D - 6.0
    mb.quad([P(-w, d0, 0.55), P(w, d0, 0.55), P(w, d1, 0.0), P(-w, d1, 0.0)], [(-w, 6), (w, 6), (w, 0), (-w, 0)], mats['paving'], a)
    for sx in (-1, 1):
        xa, xb = (w, w + 0.55) if sx > 0 else (-w - 0.55, -w)
        fbox(mb, P, xa, xb, d1, d0, 0.0, 1.0, mats['trim'], a, skip=('bottom', 'out'))


def wing(mb: MB, tc: float, half: float, mats: dict) -> None:
    """The terrace over the seats cut away behind a gatehouse or the box: a paved top at the lowest tier's top
    with a low parapet, and side walls along the cut that close the rows' ends."""
    a = {'lite': 1}
    tb = L.tier_bounds()[0]
    z = tb['z1'] + 0.35
    off1 = tb['walk_end']
    t0, t1 = tc - half / speed(tc, 0.0), tc + half / speed(tc, 0.0)
    ts = span_ts(8.0, t0, t1, 2.0)
    sweep(mb, [(0.0, z), (off1, z)], ts, face_fn=lambda i, j: (mats['paving'], a))
    sweep(mb, [(0.0, z), (0.0, z + 1.0), (0.4, z + 1.0)], ts, face_fn=lambda i, j: (mats['trim'], a))
    from crown_geo import pt
    for tt, sgn in ((t0, -1), (t1, 1)):
        oz = [(0.0, 0.0), (off1, 0.0), (off1, z), (0.0, z)]      # faces toward smaller t: right for the t0 side
        if sgn > 0:
            oz = oz[::-1]
        mb.quad([pt(tt, o, zz) for o, zz in oz], oz, mats['face'], a)


def patrons_box(mats: dict) -> MB:
    mb = MB()
    P = frame(L.BOX_T)
    a = {'lite': 1}
    W, d0, back = BOX_W, BOX_FRONT, 4.6
    fbox(mb, P, -W, W, d0, back, 0.0, BOX_FLOOR, mats['face'], a, skip=('out', 'bottom'))
    fbox(mb, P, -W - 0.3, W + 0.3, d0 - 0.35, d0 + 0.3, 0.0, 0.45, mats['trim'], a, skip=('out', 'bottom'))
    fbox(mb, P, -W - 0.25, W + 0.25, d0 - 0.3, d0 + 0.2, BOX_FLOOR - 0.35, BOX_FLOOR, mats['trim'], a, skip=('out',))
    for x in (-6.0, -2.0, 2.0, 6.0):                                   # inset panels behind the medallions
        fbox(mb, P, x - 1.0, x + 1.0, d0 - 0.05, d0, 1.05, 3.25, mats['inset'], a, skip=('out', 'bottom'))
    for x in [-W + 0.15 + i * (2 * W - 0.3) / 15 for i in range(16)]:            # the railing's balusters
        lathe(mb, [(0.09, 0.0), (0.06, 0.35), (0.09, 0.75)], 5, P(x, d0 + 0.18, BOX_FLOOR), mats['marble'], {'lite': 0}, cap=False)
    fbox(mb, P, -W, W, d0 + 0.02, d0 + 0.36, BOX_FLOOR + 0.75, BOX_FLOOR + 0.9, mats['trim'], a, skip=('out',))
    for x in (-7.3, -2.6, 2.6, 7.3):
        lathe(mb, [(0.32, 0.0), (0.32, 0.25), (0.22, 0.3), (0.19, 5.0), (0.32, 5.3), (0.34, 5.5)], 7, P(x, d0 + 0.45, BOX_FLOOR), mats['marble'], a)
    fbox(mb, P, -W, W, back, back + 0.5, BOX_FLOOR, 11.2, mats['face'], a, skip=('out',))
    for sx in (-1, 1):
        x0, x1 = (W, W + 0.5) if sx > 0 else (-W - 0.5, -W)
        fbox(mb, P, x0, x1, d0, back + 0.5, 0.0, 11.2, mats['face'], a, skip=('bottom',))       # down to the sand: hides the podium's cut end
    fbox(mb, P, -W - 0.3, W + 0.3, d0 + 0.3, d0 + 0.6, BOX_FLOOR + 5.5, BOX_FLOOR + 5.8, mats['bronze'], a)
    canopy(mb, P, -W - 0.3, W + 0.3, d0 + 0.45, BOX_FLOOR + 5.75, back, 10.9, mats)
    for row, (dd, dz) in enumerate(((0.9, 0.0), (2.6, 0.45))):
        fbox(mb, P, -W + 0.6, W - 0.6, dd - 0.1, back, BOX_FLOOR, BOX_FLOOR + dz + 0.01, mats['marble'], a, skip=('bottom', 'out'))
    wing(mb, L.BOX_T, L.BOX_HALF, mats)
    return mb


def canopy(mb: MB, P, x0: float, x1: float, df: float, zf: float, db: float, zb: float, mats: dict) -> None:
    """The box's cloth canopy: sagging between the front beam and the back wall, normals down (seen from the sand),
    with a scalloped valance hanging from its front edge (UVMap u across in metres: the stripes)."""
    nu, nv = 10, 5
    G = []
    for jv in range(nv + 1):
        s = jv / nv
        row = []
        for iu in range(nu + 1):
            u = iu / nu
            x = x0 + (x1 - x0) * u
            sag = 0.55 * math.sin(math.pi * s) * (0.6 + 0.4 * math.sin(math.pi * u))
            row.append(P(x, df + (db - df) * s, zf + (zb - zf) * s - sag))
        G.append(row)
    width, depth = x1 - x0, db - df
    qs, uvs = [], []
    for jv in range(nv):
        for iu in range(nu):
            qs.append([G[jv][iu], G[jv][iu + 1], G[jv + 1][iu + 1], G[jv + 1][iu]])
            uvs.append([(width * iu / nu, depth * jv / nv), (width * (iu + 1) / nu, depth * jv / nv),
                        (width * (iu + 1) / nu, depth * (jv + 1) / nv), (width * iu / nu, depth * (jv + 1) / nv)])
    mb.island(qs, uvs, mats['canopy'], {'lite': 1})
    for iu in range(nu):
        xa, xb = x0 + width * iu / nu, x0 + width * (iu + 1) / nu
        xm = (xa + xb) / 2
        pts = [P(xa, df - 0.02, zf), P(xb, df - 0.02, zf), P(xb, df - 0.02, zf - 0.55), P(xm, df - 0.02, zf - 0.85), P(xa, df - 0.02, zf - 0.55)]
        mb.quad(pts, [(xa, 0.85), (xb, 0.85), (xb, 0.3), (xm, 0.0), (xa, 0.3)], mats['valance'], {'lite': 1})    # faces the sand


def patron_seats() -> list[dict]:
    """The live crowd's seats in the box: two rows on the marble benches facing the sand."""
    P = frame(L.BOX_T)
    out = []
    for row, (dd, dz, n) in enumerate(((0.55, 0.0, 9), (2.2, 0.45, 9))):
        for i in range(n):
            x = -6.4 + 12.8 * i / (n - 1)
            px, py, pz = P(x, dd, BOX_FLOOR + dz + 0.45)
            out.append({'p': (px, py, pz), 'face': -math.pi / 2, 'row': row, 'section': 'patrons', 'kind': 'seat', 'lite': i % 2 == 0})
    return out
