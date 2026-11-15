"""Reefclaw's limbs (Art 2.1 Ultra): six walking legs and two claws as rigid shell segments (props), each a voxel-united
solid riding one bone, so nothing stretches when a joint bends (a crab's armour). Joints are knuckles centred on the
pivots. Built in reefclaw_pieces.py, carved in reefclaw_relief.py.

Round 3 (review: toy-like sausage forms):
- Legs: angular plated segments (rounded boxes, each flaring at its far end where the next one tucks in, like armour),
  no washer rings, ending in a long, curved, pointed dactyl.
- The big claw (its right; 1-hero, 4-details panel 4) is a crab pincer first: a thick flattened palm and fixed finger
  forming one porous coral mass, a smooth curved movable finger with a pale toothed edge, a clear gap. Coral fronds,
  thinner than the fingers, grow off its outer and top edge as flat-ish antler fans, forking three times into small
  pale knobbly tips.
- The small claw (its left; panel 5): a crab pincer held out to the side at shoulder height, facing forward: a bulbous
  palm, the movable finger curving down onto the fixed one, toothed inner edges, pale tips, a gap.
"""
from __future__ import annotations

import numpy as np

from lib.surface import v3
from monsters.breeds import reefclaw_form as F
from monsters.breeds import reefclaw_geo as G

# --------------------------------------------------------------------------- layout (left side; the right mirrors)
LEGS = [{'hip': (0.175, -0.06, 0.235), 'knee': (0.37, -0.10, 0.33), 'ankle': (0.44, -0.24, 0.012)},
        {'hip': (0.205, 0.045, 0.235), 'knee': (0.43, 0.035, 0.355), 'ankle': (0.52, 0.0, 0.012)},
        {'hip': (0.18, 0.155, 0.235), 'knee': (0.38, 0.255, 0.345), 'ankle': (0.46, 0.36, 0.012)}]

ARMS = {'L': {'shoulder': F.SHOULDER, 'elbow': (0.43, -0.27, 0.42), 'wrist': (0.53, -0.32, 0.46)},
        'R': {'shoulder': (-F.SHOULDER[0], F.SHOULDER[1], F.SHOULDER[2]), 'elbow': (-0.45, -0.30, 0.45), 'wrist': (-0.52, -0.28, 0.52)}}
ARM_SIZE = {'L': (0.036, 0.05, 0.04, 0.054), 'R': (0.046, 0.064, 0.05, 0.07)}     # half-sizes: arm thin/broad, forearm thin/broad

# each claw: the palm (centre, thin and broad radii, the bulb, the flat faces' normal), the fixed finger and the movable
# one (dactyl) as 3-point curves with (base, tip) radii, the hinge, and the teeth's side (a unit offset toward the gap)
SMALL = {'palm': (0.555, -0.385, 0.49), 'palm_r': (0.058, 0.078), 'bulb': 0.07, 'flat': (1.0, 0.0, 0.0),
         'fixed': [(0.56, -0.45, 0.47), (0.568, -0.53, 0.49), (0.574, -0.6, 0.535)], 'fixed_r': (0.036, 0.01), 'fixed_in': (0.0, 0.0, 1.0),
         'hinge': (0.555, -0.43, 0.56), 'dactyl': [(0.555, -0.43, 0.56), (0.566, -0.535, 0.6), (0.576, -0.612, 0.555)],
         'dactyl_r': (0.044, 0.011), 'dactyl_in': (0.0, 0.0, -1.0)}
BIG = {'palm': (-0.53, -0.27, 0.63), 'palm_r': (0.095, 0.13), 'bulb': 0.112, 'flat': (0.0, -1.0, 0.0),
       'fixed': [(-0.565, -0.27, 0.71), (-0.56, -0.27, 0.83), (-0.525, -0.265, 0.935)], 'fixed_r': (0.07, 0.022), 'fixed_in': (1.0, 0.0, 0.0),
       'hinge': (-0.43, -0.27, 0.71), 'dactyl': [(-0.43, -0.27, 0.71), (-0.39, -0.27, 0.815), (-0.43, -0.265, 0.92)],
       'dactyl_r': (0.052, 0.012), 'dactyl_in': (-1.0, 0.0, 0.0)}
# coral fronds off the porous mass's outer and top edge (and two off its back edge): (base, direction, length, radius,
# forks). Thinner than the fingers; each forks three times in a flat-ish fan
TRUNKS = [((-0.625, -0.27, 0.62), (-0.9, 0.05, 0.42), 0.085, 0.031, 3), ((-0.625, -0.27, 0.72), (-0.8, -0.05, 0.6), 0.09, 0.033, 3),
          ((-0.615, -0.27, 0.83), (-0.6, 0.05, 0.8), 0.09, 0.032, 3), ((-0.585, -0.27, 0.92), (-0.35, -0.05, 0.94), 0.085, 0.031, 3),
          ((-0.53, -0.26, 0.975), (0.05, -0.1, 1.0), 0.08, 0.029, 3),
          ((-0.56, -0.19, 0.75), (-0.35, 0.8, 0.5), 0.075, 0.028, 2), ((-0.56, -0.2, 0.87), (-0.25, 0.7, 0.65), 0.075, 0.028, 2)]
FWD = (0.0, -1.0, 0.0)

LEG_TRIS = (560, 760)            # thigh, shin
ARM_TRIS = {'L': (460, 460, 1400, 700), 'R': (560, 600, 12000, 900)}     # arm, forearm, claw, pincer


def mirror(p, s: int) -> np.ndarray:
    p = v3(p)
    return v3((p[0] * s, p[1], p[2]))


def leg_points(i: int, s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lg = LEGS[i]
    return mirror(lg['hip'], s), mirror(lg['knee'], s), mirror(lg['ankle'], s)


def _rot2(d: np.ndarray, n, deg: float) -> np.ndarray:
    """d turned `deg` degrees about n (Rodrigues)."""
    a = np.radians(deg)
    n = G.unit(n)
    return d * np.cos(a) + np.cross(n, d) * np.sin(a) + n * float(n @ d) * (1 - np.cos(a))


_CORAL: dict = {}


def coral() -> dict:
    """Every coral tube (a, b, r_a, r_b) and every knobbed tip (centre, radius, outward), cached: each frond bends a
    little upward halfway and forks into two that spread 25-38 degrees in its fan (twisted at most 12 degrees out of
    it), each fork 0.72 as thick; the tips end in small round knobs."""
    if _CORAL:
        return _CORAL
    rng = np.random.default_rng(2031)
    tubes, tips = [], []

    def grow(p, d, L, r, depth, fan):
        m = p + d * L * 0.5
        d2 = G.unit(d + v3((0.0, 0.0, 0.12)) + rng.normal(0.0, 0.05, 3))
        b = m + d2 * L * 0.5
        tubes.extend([(p, m, r, r * 0.93), (m, b, r * 0.93, r * 0.86)])
        if depth <= 0:
            tips.append((b, r * 0.86 * 1.12, d2))
            return
        ax = G.unit(_rot2(fan, d2, rng.uniform(-12.0, 12.0)))
        spread = rng.uniform(25.0, 38.0)
        for sgn in (1, -1):
            dc = G.unit(_rot2(d2, ax, sgn * spread))
            grow(b, dc, L * rng.uniform(0.68, 0.8), r * 0.76, depth - 1, fan)
    for base, d, L, r, depth in TRUNKS:
        d = G.unit(d)
        fan = v3(FWD) if abs(float(d @ v3(FWD))) < 0.7 else v3((1.0, 0.0, 0.0))
        grow(v3(base), d, L, r, depth, fan)
    _CORAL.update(tubes=tubes, tips=tips)
    return _CORAL


def coral_tips(with_dir: bool = False) -> list[tuple]:
    out = coral()['tips']
    return out if with_dir else [(b, r) for b, r, _d in out]


def teeth(name: str) -> list[tuple[np.ndarray, float]]:
    """The claws' bumpy teeth along each finger's inner edge, toward the gap (4-details panels 4 and 5)."""
    c = {'clawL': (SMALL, 'fixed'), 'pincerL': (SMALL, 'dactyl'), 'clawR': (BIG, 'fixed'), 'pincerR': (BIG, 'dactyl')}.get(name)
    if c is None:
        return []
    spec, key = c
    pts = [v3(p) for p in spec[key]]
    r0, r1 = spec[f'{key}_r']
    side = v3(spec[f'{key}_in'])
    out = []
    for k, t in enumerate(np.linspace(0.2, 0.84, 6)):
        p = pts[0] + (pts[1] - pts[0]) * (t * 2) if t < 0.5 else pts[1] + (pts[2] - pts[1]) * (t * 2 - 1)
        r = r0 + (r1 - r0) * t
        out.append((p + side * r * 0.8, r * (0.3 if k % 2 else 0.24)))
    return out
