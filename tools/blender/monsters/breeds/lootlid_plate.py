"""Lootlid's keyhole plate, its "nose" (Art 2.1 Ultra; 1-hero, 3-faces, 4-details panel 1): a thick gold escutcheon on
the lid's front between and below the eyes: a round top lobe, two side lobes and a broad foot on the lid's bottom edge,
bevelled all round, with four rivets and a real keyhole (a round hole over a tapering slot) cut 7.5 mm deep into the
high source (the game mesh's flat face gets it from the bake). Built as a polar loft round its centre, rigid on `head`.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import lootlid_form as F
from monsters.breeds import lootlid_geo as G
from monsters.breeds import lootlid_trim as T

CENTRE = (0.0, 0.567)
THICK, BEVEL = 0.016, 0.0055          # round 3: a thick plate standing proud
KEY_DEPTH = 0.013                      # a real cut keyhole, on the game mesh too


def _circle(x, z, c, r):
    return np.hypot(x - c[0], z - c[1]) - r


def _rrect(x, z, c, half, r):
    qx = np.abs(x - c[0]) - (half[0] - r)
    qz = np.abs(z - c[1]) - (half[1] - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qz, 0)) + np.minimum(np.maximum(qx, qz), 0) - r


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def outline_sdf(x, z) -> np.ndarray:
    d = _circle(x, z, (0.0, 0.618), 0.041)
    for s in (1, -1):
        d = _smin(d, _circle(x, z, (0.066 * s, 0.553), 0.039), 0.012)
    d = _smin(d, _rrect(x, z, (0.0, 0.556), (0.052, 0.054), 0.01), 0.01)
    d = _smin(d, _rrect(x, z, (0.0, 0.512), (0.071, 0.0155), 0.007), 0.012)
    return d


def keyhole_sdf(x, z) -> np.ndarray:
    """The keyhole: a round hole over a slot widening downward."""
    d = _circle(x, z, (0.0, 0.59), 0.0158)
    t = np.clip((0.586 - z) / (0.586 - 0.527), 0, 1)
    half = 0.0062 + 0.0048 * t
    slot = np.maximum(np.abs(x) - half, np.maximum(z - 0.586, 0.527 - z))
    return np.minimum(d, slot)


def radius_at(th: np.ndarray) -> np.ndarray:
    """The outline's distance from the centre in each direction (the first exit, refined)."""
    cx, cz = CENTRE
    c, s = np.cos(th), np.sin(th)
    r = np.zeros_like(th)
    out = np.zeros(len(th), bool)
    for step in np.arange(0.0005, 0.2, 0.0005):
        hit = (~out) & (outline_sdf(cx + step * c, cz + step * s) > 0)
        r = np.where(hit, step, r)
        out |= hit
    lo, hi = r - 0.0005, r.copy()
    for _ in range(14):
        m = 0.5 * (lo + hi)
        inside = outline_sdf(cx + m * c, cz + m * s) <= 0
        lo, hi = np.where(inside, m, lo), np.where(inside, hi, m)
    return 0.5 * (lo + hi)


def build(high: bool) -> list[dict]:
    nth = 320 if high else 52
    th = np.linspace(0, 2 * math.pi, nth, endpoint=False)
    r = radius_at(th)
    # rows: (k = share of the outline radius, height): the flat top, the rounded bevel, the wall, the underside
    if high:
        ks = np.concatenate([np.linspace(0.02, 1.0, 80)])
    else:
        ks = np.concatenate([np.linspace(0.04, 0.84, 13), [0.93, 1.0]])
    rows = []
    for k in ks:
        d_edge = (1.0 - k) * r                      # metres to the edge, per direction
        e = np.clip((BEVEL - d_edge) / BEVEL, 0, 1)
        h = THICK * (1.0 - 0.5 * (1.0 - np.sqrt(1.0 - e * e)))
        rows.append((k, h, True))
    rows.append((1.0, np.full(nth, -0.0025), False))
    rows.append((0.04, np.full(nth, -0.0025), False))
    rings, kh = [], []
    cx, cz = CENTRE
    for k, h, top in rows:
        x = cx + k * r * np.cos(th)
        z = cz + k * r * np.sin(th)
        base = F.front_point(x, z)
        n = F.front_normal(x, z)
        hk = np.array(h, np.float64)
        key = np.zeros(nth)
        if top:
            key = np.clip(0.5 - keyhole_sdf(x, z) / (0.0016 if high else 0.004), 0, 1)
            key = key * key * (3 - 2 * key)
            hk = hk - KEY_DEPTH * key
        rings.append(base + n * hk[:, None])
        kh.append(key)
    pc = G.sweep(rings, closed=False)
    n_ring = len(rings) * nth
    khv = np.concatenate([np.concatenate(kh), np.zeros(len(pc['v']) - n_ring)])
    bev = np.concatenate([np.repeat([k for k, _h, _t in rows], nth), np.zeros(len(pc['v']) - n_ring)])
    pc = T.finish(pc, pk=T.PK_PLATE, top=1.0, bev=np.clip((bev - 0.9) / 0.1, 0, 1), emb=khv)
    # four rivets: on the side lobes and the foot's corners
    pts, nrms = [], []
    for x, z in ((0.07, 0.555), (-0.07, 0.555), (0.056, 0.51), (-0.056, 0.51)):
        n = F.front_normal(x, z)[0]
        pts.append(F.front_point(x, z)[0] + n * THICK)
        nrms.append(n)
    return [pc] + T.rivets(pts, nrms, high, r=0.0105, h=0.0062, pk=T.PK_PLATE)
