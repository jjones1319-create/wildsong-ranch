"""Plumdrake's fluff and soft parts as lock clumps for the voxel body (Art 2.1 Ultra; round 2 of the review): the
cloud-white ruff, the tail's puff, the plum crest and the small pointed ears. Each is a list of clump specs for
plumdrake_form.clump_object / clump_sd (a soft lock: a curved, tapering lens of an elliptic section).

- The ruff (1-hero, 2-turnaround, 4-details panel 5): many thin, curving wisps in rows round the neck and over the
  shoulders, hanging down and out, their tips curling out; a bib to a soft point in front (about 0.86 m) and behind
  (about 0.98 m); wisps at the cheeks. Fur cards round its outline come from the recipe (card_params).
- The puff (2-turnaround back, 1-hero): a round swirl of wisps about 0.6 m across, wrapping the tail's tip.
- The crest: a soft feathery plum tuft flowing back over the crown and down the back of the head (round 1's hard
  cones read as spikes), and a few flicks behind the cheeks.
- The ears (4-details panel 1): small pointed leaves under the horns, pink inside.

Deterministic (seeded). Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib.mesh import Part
from lib.surface import smooth, v3
from monsters.breeds import hearthwing_parts as HP
from monsters.breeds import plumdrake_form as F


def _ring_dir(theta: float) -> np.ndarray:
    """Outward in plan at angle theta (0 = the front, -Y; +90 = the monster's left, +X)."""
    a = math.radians(theta)
    return v3((math.sin(a), -math.cos(a), 0.0))


_RUFF: list = []


def ruff() -> list[dict]:
    if _RUFF:
        return _RUFF
    rng = np.random.default_rng(3206)
    core = F.ruff_parts() + [Part('neck', 'capsule', loc=F.NECK[0], to=F.NECK[1], radius=F.NECK[2]), F._ell('chest', F.CHEST),
                             F._ell('shoulder', F.SHOULDER_M, True)]
    axis = v3((0.0, -0.05, 0.0))
    out = []
    # rows: (z of the bases at the front, at the side, at the back; length; how far down they point; count)
    # round 3: six rows of locks of mixed sizes (round 2's four tiers of same-size lobes read as stiff plates), the top
    # one tucking up under the chin and up the cheeks
    # polish: fewer, broader lobes with blunt curled tips; the front pulled down and back so the ruff frames the jaw
    rows = [
        (1.16, 1.31, 1.37, 0.12, 0.75, 22),
        (1.1, 1.24, 1.31, 0.17, 0.9, 26),
        (1.04, 1.17, 1.24, 0.2, 1.05, 28),
        (0.98, 1.1, 1.17, 0.2, 1.2, 26),
        (0.94, 1.03, 1.1, 0.18, 1.35, 20),
        (0.92, 1.0, 1.06, 0.16, 1.45, 14),
    ]
    for ri, (zf, zs, zb, L0, down, n) in enumerate(rows):
        for j in range(n):
            th = -180.0 + 360.0 * (j + 0.5 * (ri % 2)) / n + rng.uniform(-3, 3)
            a = abs(((th + 180.0) % 360.0) - 180.0)            # 0 front .. 180 back
            z0 = np.interp(a, [0, 90, 180], [zf, zs, zb])
            fr = smooth(55.0, 0.0, a)
            bk = smooth(130.0, 180.0, a)
            if ri == 0 and a > 120:
                continue
            if ri >= 4 and not (fr > 0.05 or bk > 0.05):
                continue
            if ri == 5 and fr < 0.35 and bk < 0.35:
                continue
            od = _ring_dir(th)
            hit = HP.surface_hit(axis + v3((0.0, 0.0, z0)) + od * 0.9, -od, core, reach=1.0, step=0.004)
            if hit is None:
                continue
            base = hit - od * 0.03 + v3((0.0, 0.0, rng.uniform(-0.012, 0.012)))
            tang = v3((math.cos(math.radians(th)), math.sin(math.radians(th)), 0.0))
            outk = (0.55 + 0.25 * max(fr, bk)) * (1.0 - 0.15 * ri / 5)
            d = od * outk + v3((0.0, 0.0, -down)) + tang * rng.uniform(-0.35, 0.35)
            size = rng.choice([0.7, 0.85, 1.0, 1.15, 1.3])
            L = L0 * size * rng.uniform(0.9, 1.1) * (1.0 + 0.2 * fr * (ri >= 2) + 0.12 * bk * (ri >= 2))
            # round 3: wavy locks that curl out at the tip in an S (round 2b's rounded lobes read as plates): a sideways
            # wave and a curl, mixed sizes, soft rounded tips
            out.append({'base': tuple(base), 'dir': tuple(d), 'len': L, 'w': 0.1 * size * rng.uniform(0.9, 1.15),
                        'th': 0.05 * size * rng.uniform(0.9, 1.1), 'tip': (2.4, 0.5), 'side': tuple(tang),
                        'bend_dir': tuple(od * 0.8 + v3((0.0, 0.0, 0.35))), 'curl': rng.uniform(0.45, 0.6),
                        'wave': rng.choice([-1, 1]) * rng.uniform(0.12, 0.22), 'bury': 0.4})
    for x, zb, L in ((0.0, 0.97, 0.18), (0.06, 0.99, 0.16), (-0.06, 0.99, 0.16), (0.11, 1.01, 0.14), (-0.11, 1.01, 0.14)):
        hit = HP.surface_hit(v3((x, -0.9, zb)), v3((0.0, 1.0, 0.0)), core, reach=1.2, step=0.004)
        if hit is not None:
            out.append({'base': tuple(hit + v3((0.0, 0.03, 0.0))), 'dir': (x * 0.8, -0.3, -1.0), 'len': L, 'w': 0.095, 'th': 0.052,
                        'tip': (2.2, 0.55), 'side': (1.0, 0.0, 0.0), 'bend_dir': (0.0, -0.75, 0.3), 'curl': 0.4,
                        'wave': 0.12 * np.sign(x + 1e-6), 'bury': 0.4})
    for x, zb, L in ((0.0, 1.1, 0.17), (0.07, 1.12, 0.15), (-0.07, 1.12, 0.15)):
        hit = HP.surface_hit(v3((x, 0.9, zb)), v3((0.0, -1.0, 0.0)), core, reach=1.2, step=0.004)
        if hit is not None:
            out.append({'base': tuple(hit + v3((0.0, -0.03, 0.0))), 'dir': (x * 0.8, 0.3, -1.0), 'len': L, 'w': 0.095, 'th': 0.052,
                        'tip': (2.2, 0.55), 'side': (1.0, 0.0, 0.0), 'bend_dir': (0.0, 0.75, 0.3), 'curl': 0.4, 'wave': 0.0, 'bury': 0.4})
    # the cheek wisps: white tufts at the sides of the jaw (1-hero, 3-faces); round 2b: only the lower two (the upper ones
    # lay over the head's skin and baked white splotches onto it)
    for s in (1, -1):
        for y, z, L, dz in ():                                  # polish: none (they stuck out at the jaw's sides)
            hit = HP.surface_hit(v3((0.6 * s, y, z)), v3((-s * 1.0, 0.0, 0.0)), core, reach=0.8, step=0.003)
            if hit is None:
                continue
            out.append({'base': tuple(hit + v3((-0.022 * s, 0.0, 0.0))), 'dir': (1.0 * s, 0.6, dz), 'len': L, 'w': 0.06, 'th': 0.032,
                        'tip': (1.4, 0.75), 'side': (0.0, 0.0, 1.0), 'bend_dir': (0.0, 0.5, 0.6), 'curl': 0.4, 'wave': 0.12 * s, 'bury': 0.4})
    _RUFF.extend(out)
    return _RUFF


_PUFF: list = []


def puff() -> list[dict]:
    """Round 3: a swirl of 12 big, soft, curved locks spiralling round the tail's tip (2-turnaround back, the variant
    picture), lying round the core like a rosette (round 2's many small lobes read as a spiky mace)."""
    if _PUFF:
        return _PUFF
    rng = np.random.default_rng(9103)
    c = F.puff_centre()
    _tip, ax = F.puff_axis()
    e1 = HP.unit(np.cross(ax, v3((0.0, 1.0, 0.0))))
    e2 = np.cross(ax, e1)
    out = []
    for ring, (lat, n, L, w, th) in enumerate(((-0.25, 6, 0.34, 0.2, 0.11), (0.35, 5, 0.3, 0.18, 0.1), (0.85, 3, 0.22, 0.16, 0.09))):
        for i in range(n):
            phi = 2 * math.pi * (i + 0.5 * ring) / n + rng.uniform(-0.15, 0.15)
            rad = e1 * math.cos(phi) + e2 * math.sin(phi)
            d = HP.unit(rad * math.cos(lat) + ax * math.sin(lat))
            sw = HP.unit(np.cross(ax, d)) if np.linalg.norm(np.cross(ax, d)) > 1e-4 else e1
            # polish: broader, blunt locks curling in toward the centre (no hard points, no core showing)
            out.append({'base': tuple(c + d * (F.PUFF_R * 0.4)), 'dir': tuple(d * 0.35 + sw), 'len': L * rng.uniform(0.92, 1.08),
                        'w': w * 1.2, 'th': th * 1.1, 'tip': (2.4, 0.5), 'side': tuple(d), 'bend_dir': tuple(-d * 0.8 + sw * 0.2),
                        'curl': rng.uniform(0.65, 0.8), 'wave': rng.uniform(-0.08, 0.08), 'bury': 0.25})
    _PUFF.extend(out)
    return _PUFF


_CREST: list = []


def crest() -> list[dict]:
    """A soft feathery plum tuft: wisps standing up and flowing back over the crown from the forehead, a fan of them down
    the back of the head to the ruff, and a few flicks behind the cheeks (2-turnaround side and back, 3-faces)."""
    if _CREST:
        return _CREST
    rng = np.random.default_rng(1707)
    head = F.head_parts()[:4]
    out = []
    # the crown: (x, y on the head's top, length, how far back it leans, how far out)
    crown = [(0.0, -0.205, 0.12, 0.35, 0.0), (0.0, -0.155, 0.2, 0.35, 0.0), (0.0, -0.1, 0.2, 0.55, 0.0), (0.0, -0.04, 0.17, 0.85, 0.0),
             (0.04, -0.175, 0.12, 0.45, 0.4), (-0.04, -0.175, 0.12, 0.45, -0.4), (0.05, -0.12, 0.15, 0.6, 0.45),
             (-0.05, -0.12, 0.15, 0.6, -0.45), (0.055, -0.06, 0.13, 0.85, 0.5), (-0.055, -0.06, 0.13, 0.85, -0.5),
             (0.09, -0.13, 0.1, 0.55, 0.9), (-0.09, -0.13, 0.1, 0.55, -0.9), (0.03, -0.02, 0.13, 1.0, 0.3), (-0.03, -0.02, 0.13, 1.0, -0.3)]
    for x, y, L, back, outw in crown:
        z = HP.top_of(x, y, head)
        if z is None:
            continue
        d = v3((outw * 0.6, back * 0.75, 1.0))
        out.append({'base': (x, y, z - 0.012), 'dir': tuple(d), 'len': L, 'w': 0.065, 'th': 0.04, 'tip': (2.2, 0.5),
                    'side': (1.0, 0.0, 0.0) if abs(outw) < 0.2 else (0.0, 1.0, 0.0), 'bend_dir': (outw * 0.3, 1.0, -0.3),
                    'curl': 0.5, 'wave': rng.uniform(-0.12, 0.12), 'bury': 0.45})
    # the back of the head: a fan flowing down to the ruff
    for x, z, L in ((0.0, 1.58, 0.12), (0.06, 1.56, 0.11), (-0.06, 1.56, 0.11), (0.11, 1.53, 0.09), (-0.11, 1.53, 0.09),
                    (0.03, 1.52, 0.1), (-0.03, 1.52, 0.1)):
        hit = HP.surface_hit(v3((x, 0.6, z)), v3((0.0, -1.0, 0.0)), head, reach=0.8, step=0.003)
        if hit is None:
            continue
        out.append({'base': tuple(hit - v3((0.0, 0.015, 0.0))), 'dir': (x * 1.5, 0.75, -0.8), 'len': L, 'w': 0.07, 'th': 0.04,
                    'tip': (2.2, 0.5), 'side': (1.0, 0.0, 0.0), 'bend_dir': (0.0, -0.3, -1.0), 'curl': 0.3,
                    'wave': rng.uniform(-0.1, 0.1), 'bury': 0.45})
    for s in ():                       # round 3: none (they poked through the ruff as torn flaps)
        for y, z, L in ():
            hit = HP.surface_hit(v3((0.6 * s, y, z)), v3((-s * 1.0, 0.0, 0.0)), head + [F._ell('neckmass', ((0.0, -0.05, 1.3), (0.16, 0.14, 0.14)))],
                                 reach=0.8, step=0.003)
            if hit is None:
                continue
            out.append({'base': tuple(hit + v3((-0.012 * s, 0.0, 0.0))), 'dir': (0.8 * s, 0.75, 0.1), 'len': L, 'w': 0.05, 'th': 0.024,
                        'tip': (1.2, 0.85), 'side': (0.0, 0.0, 1.0), 'bend_dir': (0.0, 1.0, -0.3), 'curl': 0.35, 'wave': 0.0, 'bury': 0.45})
    _CREST.extend(out)
    return _CREST


def ears() -> list[dict]:
    """Two small pointed leaf ears under the horns (4-details panel 1), the broad side forward, the tip back and out."""
    E = F.EAR
    out = []
    for s in (1, -1):
        d = v3((E['dir'][0] * s, E['dir'][1], E['dir'][2]))
        out.append({'base': F.mirror(E['base'], s), 'dir': tuple(d), 'len': E['len'], 'w': E['w'], 'th': E['th'], 'tip': (1.0, 0.9),
                    'side': (0.0, 0.0, 1.0), 'bend_dir': (0.0, 1.0, 0.2), 'curl': 0.15, 'wave': 0.0, 'bury': 0.45})
    return out


def ear_front(s: int) -> np.ndarray:
    """The ear's lining side (its thin axis, toward the front)."""
    E = F.EAR
    d = HP.unit(v3((E['dir'][0] * s, E['dir'][1], E['dir'][2])))
    n = HP.unit(np.cross(d, v3((0.0, 0.0, 1.0))))
    return n if n[1] < 0 else -n


def body_extras() -> list[bpy.types.Object]:
    objs = []
    for tag, specs in (('ruff', ruff()), ('puff', puff()), ('crest', crest()), ('ear', ears())):
        for i, sp in enumerate(specs):
            objs.append(F.clump_object(f'{tag}{i}', sp))
    return objs
