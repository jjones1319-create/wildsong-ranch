"""The Crown Amphitheatre's layout: every dimension the builders share (metres, Blender Z-up, the arena floor at z = 0
centred on the origin; offsets `off` are measured outward from the sand's elliptical edge, see crown_geo).

From the sand outward: the podium wall and its parapet, a walkway, then three tiers of stone seats (the cavea), each
cut into wedges by stair aisles and fed by doorways (vomitoria) in the wall at its foot; a colonnaded gallery at the
top; the outer wall (three arcaded storeys and an attic) with the ambulatory behind its arches.
"""
from __future__ import annotations

import math

from crown_geo import A0, B0, arc_at_t, perimeter, t_at_arc  # noqa: F401  (re-exported)

RING_R = 6.0                      # the duel ring: its curb's inner edge
SPAWN_X = 2.4
CAMERA_R = 18.5                   # cameras on the floor stay within this radius (the sand's half-width is 20)
SUN_DIR = (-0.50, -0.56, 0.66)    # toward the sun: behind-left of the side camera, about 41° up

PODIUM_H = 3.0
PARAPET = (0.0, 0.5, 0.85)        # parapet from off 0 to 0.5, standing 0.85 above the podium top
WALK0 = 1.6                       # the first seat riser stands here (a walkway behind the parapet)
TIERS = [  # first riser height, riser, tread, rows, walkway after, aisles
    dict(first=0.42, riser=0.42, tread=0.85, rows=14, walk=1.8, aisles=20, front=(2, 1.0)),
    dict(first=2.6, riser=0.50, tread=0.85, rows=14, walk=1.6, aisles=24, front=(0, 0.0)),
    dict(first=2.6, riser=0.55, tread=0.80, rows=10, walk=3.6, aisles=28, front=(0, 0.0)),
]
AISLE_W = 1.3                     # stair aisles (arc metres at the tier's foot)
STOREY_H, STOREYS, ATTIC_H = 9.2, 3, 5.4
OUTSIDE_Z = 1.0                   # the plaza outside stands 1 m above the sand; the gate ramps come down
FACADE_D = 2.4                    # the outer arcade's depth
N_BAYS = 72                       # outer arcade bays (divisible by 4 so the gates sit on bay centres)

# zones cut out of the lower seats: the two gatehouses on the long axis and the Patrons' box on +y (arc metres at the
# podium, either side of the centre angle)
GATE_T = {'A': math.pi, 'B': 0.0}
GATE_HALF = 7.4                   # the seats are cut away 7.4 m either side of the gate axis (its front is 14.4 m wide)
GATE_DEPTH = 15.6                 # it fills the lowest tier behind it
BOX_T = math.pi / 2
BOX_HALF = 8.5


def rows() -> list[dict]:
    """Every seat row: tier, global row, row in tier, riser foot (off0, z0), tread top z1, tread back off1."""
    out = []
    off, z = WALK0, PODIUM_H
    g = 0
    for ti, T in enumerate(TIERS):
        nfront, dfront = T['front']
        for k in range(T['rows']):
            h = T['first'] if k == 0 else T['riser']
            d = dfront if k < nfront else T['tread']
            out.append(dict(tier=ti, row=g, k=k, off0=off, z0=z, z1=z + h, off1=off + d, riser=h, tread=d))
            off, z, g = off + d, z + h, g + 1
        off += T['walk']
    return out


def tier_bounds() -> list[dict]:
    """Per tier: the foot (off, z) of its first riser and the far edge (off, z) of the walkway after it."""
    rs = rows()
    out = []
    for ti, T in enumerate(TIERS):
        r = [x for x in rs if x['tier'] == ti]
        out.append(dict(off0=r[0]['off0'], z0=r[0]['z0'], off1=r[-1]['off1'], z1=r[-1]['z1'], walk_end=r[-1]['off1'] + T['walk']))
    return out


def outer_off() -> float:
    """The outer wall's inner face (the back of the top gallery)."""
    return tier_bounds()[-1]['walk_end']


def facade_off() -> float:
    return outer_off() + FACADE_D


def height() -> float:
    return OUTSIDE_Z + STOREYS * STOREY_H + ATTIC_H


def arc_dist(t: float, t0: float, off: float = 0.0) -> float:
    """Signed arc length from t0 to t (shortest way round) on the ellipse at offset off."""
    p = perimeter(off)
    d = float(arc_at_t(off, t) - arc_at_t(off, t0))
    return (d + p / 2) % p - p / 2


def zone(t: float, off: float = 0.0) -> str | None:
    """'gateA' / 'gateB' / 'box' when the angle falls in a cut-out zone (measured at the podium), else None."""
    for g, tg in GATE_T.items():
        if abs(arc_dist(t, tg)) < GATE_HALF:
            return 'gate' + g
    if abs(arc_dist(t, BOX_T)) < BOX_HALF:
        return 'box'
    return None


def section(t: float) -> str:
    c, s = math.cos(t), math.sin(t)
    if abs(s) * A0 >= abs(c) * B0 * 1.25:
        return 'north' if s > 0 else 'south'
    return 'east' if c > 0 else 'west'


def aisle_ts(ti: int) -> list[float]:
    """The aisle centre angles of tier ti: evenly spaced in arc at the tier's foot, staggered tier to tier, and none
    inside a cut-out zone (tier 0) or within half a wedge of it."""
    T = TIERS[ti]
    off = tier_bounds()[ti]['off0']
    n = T['aisles']
    phase = 0.5 if ti % 2 else 0.0
    P = perimeter(off)
    ts = [float(t_at_arc(off, P * (i + phase + 0.25) / n)) for i in range(n)]
    if ti == 0:
        ts = [t for t in ts if zone(t) is None]
    return ts
