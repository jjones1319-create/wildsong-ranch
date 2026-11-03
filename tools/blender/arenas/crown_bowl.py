"""The Crown Amphitheatre's bowl: the podium wall and parapet, three tiers of seats cut into wedges by stair aisles,
the vomitoria (doorways) in the walls between the tiers, wooden bench caps on the top tier, and the live crowd's seats.

Every wedge is one bake island; the rows the game seats itself are bare marble, every other row carries the painted
crowd's face attributes (crown_mats2.crowd_paint).
"""
from __future__ import annotations

import math

from crown_geo import MB, bbox, pt, speed, span_ts, sweep, t_at_arc, arc_at_t, perimeter
import crown_layout as L


def intervals(ti: int, off: float) -> list[tuple[str, float, float]]:
    """Around tier ti: ('aisle' | 'wedge', t0, t1) intervals (t1 > t0, may pass 2pi); cut-out zones left out."""
    breaks = []
    for t in L.aisle_ts(ti):
        hw = L.AISLE_W / 2 / speed(t, off)
        breaks.append((t - hw, 'a0'))
        breaks.append((t + hw, 'a1'))
    if ti == 0:
        for tc, half in [(t, L.GATE_HALF) for t in L.GATE_T.values()] + [(L.BOX_T, L.BOX_HALF)]:
            s = float(arc_at_t(0.0, tc))
            breaks.append((float(t_at_arc(0.0, s - half)), 'z0'))
            breaks.append((float(t_at_arc(0.0, s + half)), 'z1'))
    breaks = sorted(((t % (2 * math.pi)), k) for t, k in breaks)
    out = []
    for i, (t0, k0) in enumerate(breaks):
        t1, _ = breaks[(i + 1) % len(breaks)]
        if t1 <= t0:
            t1 += 2 * math.pi
        if k0 == 'z0':
            continue
        out.append(('aisle' if k0 == 'a0' else 'wedge', t0, t1))
    return out


def live_row(r: dict, t: float) -> bool:
    """The rows the game seats (its live crowd): the front marble row everywhere, the second on the long sides."""
    return r['tier'] == 0 and (r['k'] == 0 or (r['k'] == 1 and L.section(t) in ('north', 'south')))


def tier_profile(ti: int) -> list[tuple[float, float, dict]]:
    """[(off, z, segment info to the next point)] for tier ti, from its first riser's foot to the end of its walkway."""
    rs = [r for r in L.rows() if r['tier'] == ti]
    prof = []
    for r in rs:
        prof.append((r['off0'], r['z0'], dict(kind='riser', r=r)))
        prof.append((r['off0'], r['z1'], dict(kind='tread', r=r)))
    last = rs[-1]
    prof.append((last['off1'], last['z1'], dict(kind='walk')))
    prof.append((last['off1'] + L.TIERS[ti]['walk'], last['z1'], {}))
    return prof


def build_tier(ti: int, step: float, mats: dict, wedge_seed: int, lite: bool, caps: bool = True) -> tuple[MB, MB]:
    """Tier ti → (north half, south half) builders. mats: name → index (seat, front, stair, walk, wall)."""
    prof = tier_profile(ti)
    pts = [(o, z) for o, z, _ in prof]
    rs = {r['row']: r for r in L.rows()}
    halves = (MB(), MB())
    for wi, (kind, t0, t1) in enumerate(intervals(ti, pts[0][0])):
        off_mid = pts[len(pts) // 2][0]
        ts = [t0, t1] if kind == 'aisle' else span_ts(off_mid, t0, t1, step)
        tm = (t0 + t1) / 2
        wid = wedge_seed + wi
        dens = 0.9 + 0.08 * ((wid * 0.618034) % 1.0)

        def face(i, j, kind=kind, ts=ts, dens=dens, wid=wid):
            seg = prof[i][2]
            tcol = (ts[j] + ts[min(j + 1, len(ts) - 1)]) / 2
            sk = seg.get('kind')
            if sk == 'walk':
                return mats['walk'], {'lite': int(lite)}
            r = seg['r']
            if sk == 'riser' and r['k'] == 0 and ti > 0:
                return mats['wall'], {'lite': int(lite)}
            if kind == 'aisle':
                return mats['stair'], {'lite': int(lite)}
            front = ti == 0 and r['k'] < L.TIERS[0]['front'][0]
            mat = mats['front'] if front else mats['seat']
            a = {'lite': int(lite), 'wedge': float(wid), 'fan': -math.cos(tcol)}
            if sk == 'tread' and not live_row(r, tcol):
                a.update(crowd=dens, riser=0.0, v0=r['off0'], hgt=r['tread'], row=float(r['row']))
            elif sk == 'riser' and r['k'] > 0:
                prev = rs[r['row'] - 1]
                if not live_row(prev, tcol):
                    a.update(crowd=dens, riser=1.0, v0=r['z0'], hgt=r['riser'], row=float(prev['row']))
            return mat, a
        mb = halves[0 if math.sin(tm) >= 0 else 1]
        sweep(mb, pts, ts, face_fn=face)
        if ti == 2 and kind == 'wedge' and caps:
            cap_ts = ts[::2] + ([ts[-1]] if (len(ts) - 1) % 2 else [])
            bench_caps(mb, cap_ts, mats['wood'], rs, dens, wid, lite)
    return halves


def bench_caps(mb: MB, ts, mat: int, rs: dict, dens: float, wid: int, lite: bool) -> None:
    """Wooden planks along the front of each top-tier tread (top and front faces only)."""
    for r in rs.values():
        if r['tier'] != 2:
            continue
        o0, o1, z = r['off0'] + 0.02, r['off0'] + 0.4, r['z1']
        prof = [(o0 - 0.02, z), (o0 - 0.02, z + 0.07), (o1, z + 0.07)]

        def face(i, j, r=r):
            if i == 1:
                return mat, {'lite': int(lite), 'wedge': float(wid), 'crowd': dens, 'riser': 0.0, 'v0': r['off0'],
                             'hgt': r['tread'], 'row': float(r['row'])}
            return mat, {'lite': int(lite)}
        sweep(mb, prof, ts, face_fn=face)


def build_podium(step: float, mats: dict, lite: bool) -> MB:
    """The podium wall round the sand (marble facing between a moulded base and a cornice), its parapet with a
    coping, and the walkway behind it; left out where the gatehouses and the Patrons' box stand in front."""
    H, (p0, p1, ph) = L.PODIUM_H, L.PARAPET
    prof = [(-0.3, 0.0, 'base'), (-0.3, 0.3, 'base'), (-0.14, 0.42, 'base'), (-0.05, 0.5, 'base'), (0.0, 0.58, 'face'),
            (0.0, H - 0.34, 'trim'), (-0.12, H - 0.24, 'trim'), (-0.26, H - 0.12, 'trim'), (-0.26, H, 'face'),
            (-0.18, H, 'face'), (-0.18, H + ph - 0.12, 'trim'), (-0.28, H + ph - 0.08, 'trim'), (-0.28, H + ph, 'trim'),
            (p1 + 0.06, H + ph, 'trim'), (p1 + 0.06, H + ph - 0.1, 'face'), (p1, H + ph - 0.1, 'face'), (p1, H, 'walk'),
            (L.WALK0, H, None)]
    pts = [(o, z) for o, z, _ in prof]
    mb = MB()
    # the free stretches between the cut-out zones, ending EXACTLY at the zones' edges (where the gatehouse returns,
    # the box's side walls and the seat rows' ends are), so no gap opens under the seats
    zones = sorted([(tc, half) for tc, half in [(t, L.GATE_HALF) for t in L.GATE_T.values()] + [(L.BOX_T, L.BOX_HALF)]])
    edges = [(float(t_at_arc(0.0, float(arc_at_t(0.0, tc)) - h)), float(t_at_arc(0.0, float(arc_at_t(0.0, tc)) + h))) for tc, h in zones]
    spans = []
    for k in range(len(edges)):
        t0, t1 = edges[k][1], edges[(k + 1) % len(edges)][0]
        while t1 <= t0:
            t1 += 2 * math.pi
        spans.append(span_ts(0.0, t0, t1, step))
    for sp in spans:
        for i in range(0, len(sp) - 1, 8):
            ts = sp[i:i + 9]
            if len(ts) >= 2:
                sweep(mb, pts, ts, face_fn=lambda i, j: (mats[prof[i][2]], {'lite': int(lite)}))
    cap = list(pts) + [(L.WALK0, 0.0)]          # close the podium where it stops at a gatehouse or the box
    for sp in spans:
        for t, end in ((sp[0], False), (sp[-1], True)):
            poly = cap if end else cap[::-1]
            mb.quad([pt(t, o, z) for o, z in poly], [(o, z) for o, z in poly], mats['face'], {'lite': int(lite)})
    return mb


def vomitoria(mats: dict, lite: bool) -> MB:
    """A doorway at the head of every aisle of the upper tiers: stone jambs and lintel round a dark opening."""
    mb = MB()
    tb = L.tier_bounds()
    for ti in (1, 2):
        off, z = tb[ti]['off0'], tb[ti]['z0']
        for t in L.aisle_ts(ti):
            w, h = 1.9, 2.25
            a = {'lite': int(lite)}
            bbox(mb, t, off, -w / 2, w / 2, -0.05, 0.0, z, z + h, mats['void'], a, skip=('bottom', 'top', 'left', 'right', 'out'))
            for x0, x1 in ((-w / 2 - 0.38, -w / 2), (w / 2, w / 2 + 0.38)):
                bbox(mb, t, off, x0, x1, -0.32, 0.0, z, z + h + 0.05, mats['wall'], a, skip=('bottom', 'out'))
            bbox(mb, t, off, -w / 2 - 0.5, w / 2 + 0.5, -0.4, 0.0, z + h, z + h + 0.42, mats['wall'], a, skip=('bottom', 'out'))
    return mb


def live_seats() -> list[dict]:
    """The live crowd's seats (Blender frame): on the live rows, every PITCH metres, clear of aisles and zones."""
    PITCH = 0.58
    out = []
    rs = [r for r in L.rows() if r['tier'] == 0 and r['k'] < 2]
    aisles = L.aisle_ts(0)
    for r in rs:
        off = r['off0'] + 0.36
        P = perimeter(off)
        n = int(P / PITCH)
        i = 0
        for k in range(n):
            t = float(t_at_arc(off, P * (k + 0.5) / n))
            if L.zone(t) or not live_row(r, t):
                continue
            if any(abs(L.arc_dist(t, ta, off)) < L.AISLE_W / 2 + 0.3 for ta in aisles):
                continue
            x, y, _ = pt(t, off, 0)
            out.append({'p': (x, y, r['z1']), 'face': math.atan2(-y, -x), 'row': r['k'], 'section': L.section(t),
                        'kind': 'seat', 'lite': i % 2 == 0})
            i += 1
    return out
