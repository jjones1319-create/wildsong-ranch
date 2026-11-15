"""Reefclaw's shape (Art 2.1 Ultra; chatgpt/monsters/20-reefclaw/, CONTENT 18): the shell's primitives and carving, the
rig's points, the props' layout numbers and a small deterministic noise kit (numpy only).

Measured on 2-turnaround.png at 0.0027 m per pixel (the raised coral claw's tip is the top, 1.18 m; the ground at the
legs' tips) and on 1-hero.png for the shapes: a round coral-pink carapace dome (0.66 m wide, its spiked crown ring
0.78 m up) overhanging a big peach belly of plastron plates, a smile on the shell's front under two eye stalks, aqua
barnacle clusters on both shoulders, six chunky walking legs, the big branching coral claw on its right, the small
claw on its left. Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from lib.mesh import Part
from lib.surface import smooth, v3

# ============================================================================= noise (hashed lattice; no RNG state)
_M1 = np.uint64(0x9E3779B97F4A7C15)
_M2 = np.uint64(0xBF58476D1CE4E5B9)
_M3 = np.uint64(0x94D049BB133111EB)


def _mix(h: np.ndarray) -> np.ndarray:
    with np.errstate(over='ignore'):
        h = (h ^ (h >> np.uint64(30))) * _M2
        h = (h ^ (h >> np.uint64(27))) * _M3
        return h ^ (h >> np.uint64(31))


def hash3(i: np.ndarray, seed: int, k: int = 0) -> np.ndarray:
    """0..1 per integer lattice point (n x 3), the same for every call with the same seed and channel."""
    u = i.astype(np.int64).view(np.uint64)
    with np.errstate(over='ignore'):
        h = np.uint64(seed * 7919 + k * 104729 + 1) * _M1
        h = _mix(h ^ u[:, 0])
        h = _mix(h ^ (u[:, 1] * _M1))
        h = _mix(h ^ (u[:, 2] * _M2))
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def cells(p: np.ndarray, cell: float, seed: int, jitter: float = 0.9, chunk: int = 300000):
    """Voronoi on a jittered cubic lattice: F1 and F2 (metres) and a 0..1 hash per nearest cell (sizes, chances)."""
    n = len(p)
    f1, f2, h = np.full(n, np.inf), np.full(n, np.inf), np.zeros(n)
    offs = [np.array([dx, dy, dz], np.int64) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]
    for a in range(0, n, chunk):
        q = p[a:a + chunk] / cell
        i0 = np.floor(q).astype(np.int64)
        b1, b2, bh = np.full(len(q), np.inf), np.full(len(q), np.inf), np.zeros(len(q))
        for o in offs:
            c = i0 + o
            fp = c + 0.5 + jitter * (np.stack([hash3(c, seed, 0), hash3(c, seed, 1), hash3(c, seed, 2)], axis=1) - 0.5)
            d = np.linalg.norm(q - fp, axis=1)
            closer = d < b1
            b2 = np.where(closer, b1, np.minimum(b2, d))
            bh = np.where(closer, hash3(c, seed, 3), bh)
            b1 = np.where(closer, d, b1)
        f1[a:a + chunk], f2[a:a + chunk], h[a:a + chunk] = b1 * cell, b2 * cell, bh
    return f1, f2, h


def bumps(p: np.ndarray, cell: float, seed: int, r: tuple[float, float], chance: float) -> tuple[np.ndarray, np.ndarray]:
    """Scattered round bumps of varied size (lesson: an even grid of one size reads as bubble wrap): (0..1 dome height
    per point, the bump's own 0..1 hash). A cell holds a bump with probability `chance`, radius between r[0] and r[1]."""
    f1, _f2, h = cells(p, cell, seed)
    rad = r[0] + (r[1] - r[0]) * ((h * 7.31) % 1.0)
    on = h < chance
    dome = np.sqrt(np.clip(1.0 - (f1 / rad) ** 2, 0.0, 1.0)) * on
    return dome, h


# ============================================================================= the shell (lo_body)
# round 2 (review): lowered 5 cm (the belly nearly on the ground), and a dome wider than it is tall
CARA_C, CARA_R = (0.0, 0.03, 0.47), (0.35, 0.31, 0.26)        # the carapace dome
# round 3 (review: the belly was the biggest, brightest egg): a smaller, flatter plastron set back under the rim
BELLY_C, BELLY_R = (0.0, -0.09, 0.27), (0.25, 0.14, 0.16)     # the plastron in front, under the lip
UNDER_C, UNDER_R = (0.0, 0.04, 0.215), (0.24, 0.26, 0.10)     # the underside between the legs
TELSON_C, TELSON_R = (0.0, 0.2, 0.165), (0.12, 0.06, 0.045)  # the folded tail flap under the back point
HIP = (0.0, 0.03, 0.42)
CHEST = (0.0, -0.15, 0.42)
SHELL_TOP = (0.0, 0.03, 0.73)
SHOULDER = (0.25, -0.20, 0.38)                               # the left arm's root (mirrored)
ARM_DIR = (0.18, -0.07, 0.04)                                  # the left arm's way out of its socket


def all_parts() -> list[Part]:
    return [Part('carapace', 'sphere', loc=CARA_C, radius=1.0, scale=CARA_R),
            Part('belly', 'sphere', loc=BELLY_C, radius=1.0, scale=BELLY_R),
            Part('under', 'sphere', loc=UNDER_C, radius=1.0, scale=UNDER_R),
            Part('telson', 'sphere', loc=TELSON_C, radius=1.0, scale=TELSON_R)]


def ell_point(phi: float, el: float, c=CARA_C, r=CARA_R) -> np.ndarray:
    """A point on an ellipsoid by angle round from the front (phi degrees, + toward its left) and elevation."""
    f, e = math.radians(phi), math.radians(el)
    return v3((c[0] + r[0] * math.sin(f) * math.cos(e), c[1] - r[1] * math.cos(f) * math.cos(e), c[2] + r[2] * math.sin(e)))


def ell_normal(p, c=CARA_C, r=CARA_R) -> np.ndarray:
    g = (v3(p) - v3(c)) / v3(r) ** 2
    return g / np.linalg.norm(g, axis=-1, keepdims=True)


def ell_metric(co: np.ndarray, c=CARA_C, r=CARA_R) -> np.ndarray:
    return np.linalg.norm((co - v3(c)) / v3(r), axis=1)


def phi_of(co: np.ndarray) -> np.ndarray:
    """Radians round the shell from the front (+ toward its left; +-pi at the back)."""
    return np.arctan2(co[:, 0], -(co[:, 1] - CARA_C[1]))


def rim_z(phi: np.ndarray) -> np.ndarray:
    """The carapace's lower edge: 0.42 m in front (a shallow V at the middle), 0.29 at the sides over the legs, 0.21 at
    the back point."""
    return 0.305 + 0.115 * np.cos(phi) + 0.02 * np.cos(2 * phi) - 0.018 * np.exp(-(phi / 0.22) ** 2)


# the stalks' sockets, the spikes and the big knobs (on the carapace)
STALK_BASE = {s: v3((0.115 * s, -0.07, 0.70)) for s in (1, -1)}
STALK_AXIS = {s: v3((0.08 * s, -0.09, 1.0)) / np.linalg.norm((0.08, -0.09, 1.0)) for s in (1, -1)}


def spike_specs() -> list[tuple[np.ndarray, np.ndarray, float, float]]:
    """(base point, direction, height, base radius) per spike: a crown ring round the top (2-turnaround: the front's top
    outline and the back's ring), a few lower on the back and the sides, little ones at the rim's front corners, and
    the back point."""
    out = []
    for i, phi in enumerate(range(-162, 163, 18)):
        if min(abs(phi - 46), abs(phi + 46)) < 10:
            continue
        el = 56.0 + 3.0 * math.cos(math.radians(phi))
        h = 0.034 + 0.008 * (i % 3 == 1) - 0.006 * (abs(phi) > 120)
        out.append((phi, el, h, 0.021))
    # round 2 (review: spikes round the sides and over the back, a faint centre ridge): a second ring and a low one
    for i, phi in enumerate(range(-171, 172, 19)):
        if abs(phi) <= 100:                                  # not in front, nor under the barnacle mounds
            continue
        out.append((phi, 32.0 + 4.0 * (i % 2), 0.026 + 0.006 * (i % 3 == 0), 0.017))
    for i, phi in enumerate(range(-165, 166, 22)):
        if abs(phi) <= 100:
            continue
        out.append((phi, 12.0 + 3.0 * (i % 2), 0.018 + 0.004 * (i % 2), 0.013))
    for el in (44.0, 66.0, 80.0):                            # down the back's centre ridge
        out.append((180.0, el, 0.022, 0.015))
    out.append((0.0, 82.0, 0.024, 0.018))
    for phi in (-34, 34):                                    # the rim's front corners
        out.append((phi, -4.0, 0.018, 0.013))
    # round 3 (review: the rim spikes carried round the sides): a row just above the rim's edge
    for phi in range(-160, 161, 20):
        if abs(phi) < 25:
            continue
        zr = float(rim_z(np.array([math.radians(phi)]))[0]) + 0.02
        el = math.degrees(math.asin(max(-1.0, min(1.0, (zr - CARA_C[2]) / CARA_R[2]))))
        out.append((phi, el, 0.016, 0.012))
    specs = []
    for phi, el, h, r in out:
        p = ell_point(phi, el)
        n = ell_normal(p)
        if abs(el) < 10:
            n = n + v3((0.0, 0.0, -0.35))                    # the corner spikes point a little down
            n /= np.linalg.norm(n)
        specs.append((p, n, h, r))
    p = v3((0.0, 0.185, 0.262))                              # the back point, pointing back and down
    specs.append((p, v3((0.0, 0.62, -0.78)), 0.024, 0.024))
    return specs


KNOBS = [(-21, -3, 0.016, 0.009), (21, -3, 0.016, 0.009), (-12, 18, 0.011, 0.006), (12, 18, 0.011, 0.006),
         (0, 66, 0.013, 0.007), (-62, 22, 0.012, 0.007), (62, 22, 0.012, 0.007), (-130, 52, 0.012, 0.007),
         (130, 52, 0.012, 0.007), (-98, 48, 0.011, 0.006), (98, 48, 0.011, 0.006), (180, 64, 0.012, 0.007),
         (-160, 20, 0.011, 0.006), (160, 20, 0.011, 0.006)]

# the plastron's plates: seeds (x, z) on the belly's front, a seam down the middle (1-hero)
# round 3 (review: 8-10 larger, straight-edged turtle-like plates with a centre seam): exact mirror pairs, no warp
PLATE_SEEDS = [(-0.07, 0.355), (0.07, 0.355), (-0.068, 0.275), (0.068, 0.275), (-0.062, 0.195), (0.062, 0.195),
               (-0.185, 0.32), (0.185, 0.32), (-0.175, 0.215), (0.175, 0.215)]

# the smile (3-faces neutral, 1-hero): a soft curve on the shell's front under the stalks
MOUTH_Z, MOUTH_W, MOUTH_DIP = 0.605, 0.088, 0.024


def mouth_z(x: np.ndarray) -> np.ndarray:
    return MOUTH_Z - MOUTH_DIP * (1.0 - np.clip(x / MOUTH_W, -1.0, 1.0) ** 2)


def _seg_dist(p: np.ndarray, a, b) -> tuple[np.ndarray, np.ndarray]:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1), t
