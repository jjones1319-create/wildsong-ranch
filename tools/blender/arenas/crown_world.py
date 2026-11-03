"""Around the Crown Amphitheatre (seen in the fly-in and the establishing view): the paved plaza, rolling dry
grassland rising to hills, the two roads out from the gates lined with cypresses, umbrella pines, a small town of
plastered houses with tiled roofs (the fly-in starts above it), and far mountains for the sky panorama only.
"""
from __future__ import annotations

import math

import numpy as np

from crown_geo import A0, B0, MB, box, lathe, pt, sweep, span_ts
import crown_layout as L

PLAZA = 22.0                 # the plaza reaches this far beyond the façade
LAND_R = 330.0
TOWN = (-45.0, -168.0)       # the town's centre (the fly-in starts behind and above it)


def ground_h(x, y):
    """Height of the land (m): the plaza level near the amphitheatre, rolling further out, hills at the edge."""
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    r = np.hypot(x / (A0 + 70) * (B0 + 70), y)
    k = np.clip((r - 110.0) / 60.0, 0.0, 1.0)
    k = k * k * (3 - 2 * k)
    roll = 1.6 * np.sin(x * 0.021 + 0.7) * np.cos(y * 0.017 + 0.3) + 0.9 * np.sin(x * 0.047 + y * 0.031)
    hills = np.clip((r - 190.0) / 140.0, 0.0, 1.0) ** 1.6 * (26.0 + 10.0 * np.sin(np.arctan2(y, x) * 3 + 0.8))
    road = np.exp(-(y / 9.0) ** 2) * (np.abs(x) > 90)
    return L.OUTSIDE_Z - 0.15 + k * roll * (1 - 0.8 * road) + hills


def plaza(mats: dict) -> MB:
    mb = MB()
    o0 = L.facade_off() - 0.2
    for k in range(16):
        t0, t1 = 2 * math.pi * k / 16, 2 * math.pi * (k + 1) / 16
        ts = span_ts(o0, t0, t1, 4.0)
        sweep(mb, [(o0, L.OUTSIDE_Z), (o0 + PLAZA, L.OUTSIDE_Z)], ts, face_fn=lambda i, j: (mats['plaza'], {'lite': 1}))
        sweep(mb, [(o0 + PLAZA, L.OUTSIDE_Z), (o0 + PLAZA + 0.6, L.OUTSIDE_Z - 0.18)], ts, face_fn=lambda i, j: (mats['plaza'], {'lite': 1}))
    return mb


def plaza_dress(mats: dict, seed: int = 13) -> MB:
    """A ring of squat stone bollards round the amphitheatre, and market stalls with striped awnings by the gates."""
    from crown_geo import perimeter, t_at_arc, frame
    mb = MB()
    off = L.facade_off() + 15.0
    P = perimeter(off)
    n = 88
    for k in range(n):
        t = float(t_at_arc(off, P * (k + 0.5) / n))
        x, y, _ = pt(t, off, 0)
        if abs(y) < 9.0:
            continue
        box(mb, (x, y, L.OUTSIDE_Z + 0.55), (0.55, 0.55, 1.1), mats['stone'], {'lite': 0}, yaw=t, skip=('bottom',))
    rng = np.random.default_rng(seed)
    for tg in (0.0, math.pi):
        for side in (-1, 1):
            for i in range(4):
                Pf = frame(tg, L.facade_off() + 6.0 + i * 4.2)
                x, y, _ = Pf(side * (12.0 + rng.uniform(-0.5, 0.5)), 0.0, 0.0)
                yaw = math.atan2(y, x) + math.pi / 2
                z = L.OUTSIDE_Z
                box(mb, (x, y, z + 0.45), (2.6, 1.2, 0.9), mats['wood'], {'lite': 0}, yaw=yaw, skip=('bottom',))
                for cx in (-1.2, 1.2):
                    for cy in (-0.9, 0.9):
                        px, py = x + cx * math.cos(yaw) - cy * math.sin(yaw), y + cx * math.sin(yaw) + cy * math.cos(yaw)
                        box(mb, (px, py, z + 1.15), (0.1, 0.1, 2.3), mats['wood'], {'lite': 0}, yaw=yaw, skip=('bottom', 'top'))
                _gable(mb, x, y, z + 2.3, 3.0, 2.4, 0.5, yaw, mats['awning'][(i + (side > 0)) % 2], mats['awning'][(i + (side > 0)) % 2])
    return mb


def land(mats: dict) -> MB:
    """The grass beyond the plaza (planar bake UVs over ±LAND_R; `path` marks the roads)."""
    mb = MB()
    segs, rings = 96, 16
    o0 = L.facade_off() + PLAZA + 0.4
    rows = []
    for i in range(rings + 1):
        f = (i / rings) ** 1.7
        row = []
        for s in range(segs):
            t = 2 * math.pi * s / segs
            x0, y0, _ = pt(t, o0, 0)
            rr = math.hypot(x0, y0)
            R = rr + (LAND_R - rr) * f
            x, y = x0 / rr * R, y0 / rr * R
            z = float(ground_h(x, y)) if i else L.OUTSIDE_Z - 0.18
            row.append((x, y, z))
        rows.append(row)
    S = 2 * LAND_R
    for i in range(rings):
        for s in range(segs):
            s2 = (s + 1) % segs
            q = [rows[i][s], rows[i + 1][s], rows[i + 1][s2], rows[i][s2]]
            b = mb.verts(q)
            path = max(math.exp(-(p[1] / 5.5) ** 2) for p in q)
            mb.face(range(b, b + 4), [(p[0], p[1]) for p in q], [((p[0] + LAND_R) / S, (p[1] + LAND_R) / S) for p in q], mats['grass'], {'lite': 1, 'path': path})
    return mb


def trees(mats: dict, seed: int = 21) -> MB:
    mb = MB()
    rng = np.random.default_rng(seed)
    x0 = A0 + L.facade_off() + PLAZA + 6.0
    spots = []
    for sx in (-1, 1):                                   # cypress avenues along both roads
        for k in range(13):
            x = sx * (x0 + 13.0 * k)
            for sy in (-1, 1):
                spots.append(('cypress', x + rng.normal(0, 0.6), sy * (8.0 + rng.normal(0, 0.4))))
    while len(spots) < 120:
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(125.0, 300.0)
        x, y = r * math.cos(a), r * math.sin(a)
        if abs(y) < 16 or math.hypot(x - TOWN[0], y - TOWN[1]) < 45:
            continue
        spots.append(('pine' if rng.random() < 0.55 else 'cypress', x, y))
    tints = ['#3E5F35', '#4A6B3A', '#35552F', '#56743E']
    for kind, x, y in spots:
        z = float(ground_h(x, y)) - 0.2
        tint = tints[rng.integers(len(tints))]
        if kind == 'cypress':
            h = rng.uniform(9.0, 14.0)
            prof = [(0.0, 0.0), (0.9, 0.08 * h), (1.25, 0.3 * h), (1.0, 0.62 * h), (0.45, 0.88 * h), (0.0, h)]
            lathe(mb, [(0.2, 0.0), (0.15, 1.2)], 5, (x, y, z), mats['bark'], {'lite': 0}, cap=False)
            lathe(mb, [(r * h / 12, zz) for r, zz in prof], 7, (x, y, z + 0.9), mats['leaf'], {'lite': 0, 'tint': _tint(tint)}, cap=False)
        else:
            h = rng.uniform(8.0, 13.0)
            lathe(mb, [(0.35, 0.0), (0.22, h * 0.8)], 5, (x + 0.3, y, z), mats['bark'], {'lite': 0}, cap=False)
            w = h * rng.uniform(0.45, 0.6)
            prof = [(0.0, 0.0), (w * 0.8, 0.12 * w), (w, 0.3 * w), (w * 0.7, 0.48 * w), (0.0, 0.56 * w)]
            lathe(mb, prof, 8, (x + 0.3 + 0.18 * h, y, z + h * 0.68), mats['leaf'], {'lite': 0, 'tint': _tint(tint)}, cap=False)
    return mb


def _tint(hexcol: str) -> float:
    """Tints go through one float attribute (crown_mats2.foliage picks the colour from it)."""
    return ['#3E5F35', '#4A6B3A', '#35552F', '#56743E'].index(hexcol) / 4.0 + 0.125


def town(mats: dict, seed: int = 5) -> MB:
    """A small hill town of plastered houses with red tiled roofs, along winding lanes."""
    mb = MB()
    rng = np.random.default_rng(seed)
    cx, cy = TOWN
    n = 0
    while n < 46:
        a, r = rng.uniform(0, 2 * math.pi), abs(rng.normal(0, 26.0))
        x, y = cx + r * math.cos(a), cy + r * math.sin(a) * 0.7
        w, d, h = rng.uniform(5, 9), rng.uniform(5, 8), rng.uniform(4.5, 9.0)
        yaw = rng.choice([0.0, math.pi / 2]) + rng.normal(0, 0.12)
        z = float(ground_h(x, y)) - 0.3
        box(mb, (x, y, z + h / 2), (w, d, h), mats['plaster'], {'lite': 1}, yaw=yaw, skip=('bottom', 'top'))
        _gable(mb, x, y, z + h, w + 0.5, d + 0.5, 1.8, yaw, mats['roof'], mats['plaster'])
        n += 1
    return mb


def _gable(mb: MB, x, y, z, w, d, rise, yaw, mat, wall) -> None:
    ca, sa = math.cos(yaw), math.sin(yaw)

    def p(u, v, zz):
        return (x + u * ca - v * sa, y + u * sa + v * ca, zz)
    hw, hd = w / 2, d / 2
    for sv in (-1, 1):
        q = [p(-hw, sv * hd, z), p(hw, sv * hd, z), p(hw, 0, z + rise), p(-hw, 0, z + rise)]
        if sv > 0:
            q = q[::-1]
        mb.quad(q, [(0, 0), (w, 0), (w, hd), (0, hd)], mat, {'lite': 1})
    for su in (-1, 1):
        q = [p(su * hw, -hd, z), p(su * hw, hd, z), p(su * hw, 0, z + rise)]
        if su < 0:
            q = q[::-1]
        mb.quad(q, [(0, 0), (d, 0), (hd, rise)], wall, {'lite': 1})


def mountains(mats: dict) -> MB:
    """Far hills and mountains for the sky panorama only (never shipped as geometry): they start under the land's
    edge, roll up into hills, then rise to ridged mountains far off."""
    mb = MB()
    segs, rings = 240, 26
    radii = np.geomspace(LAND_R - 20.0, 2600.0, rings)
    ph = np.random.default_rng(11).uniform(0, 2 * np.pi, 8)
    G = []
    for r in radii:
        row = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            base = float(ground_h(LAND_R * math.cos(a), LAND_R * math.sin(a))) - 2.0
            t = min(1.0, max(0.0, (r - LAND_R) / 260.0))
            t = t * t * (3 - 2 * t)
            hill = (22.0 + 15.0 * math.sin(a * 7 + ph[4]) + 9.0 * math.sin(a * 13 + ph[5]) + 6.0 * math.sin(a * 29 + ph[6])) * t
            k = min(1.0, max(0.0, (r - 750.0) / 700.0))
            ridge = (0.55 + 0.45 * math.sin(a * 2 + ph[0])) * (0.6 + 0.4 * math.sin(a * 5 + ph[1])) + 0.25 * math.sin(a * 11 + ph[2]) + 0.12 * math.sin(a * 23 + ph[3])
            peak = (280.0 * max(0.0, ridge) + 50.0) * k
            row.append((r * math.cos(a), r * math.sin(a), base * (1 - t) + hill + peak))
        G.append(row)
    qs = [[G[i][s], G[i + 1][s], G[i + 1][(s + 1) % segs], G[i][(s + 1) % segs]] for i in range(rings - 1) for s in range(segs)]
    mb.island(qs, [[(0.0, 0.0)] * 4 for _ in qs], mats['mountain'], {'lite': 0})
    return mb
