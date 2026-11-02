"""The Breeders' Guild emblem, drawn from signed distances (numpy only): an eighth note whose flag is a leaf, inside a
ring, with a small sprout leaf on the stem. Our own design for Wildsong Ranch.

`emblem_alpha(size)` returns an anti-aliased coverage mask (rows top-down, 0..1).
"""
from __future__ import annotations

import numpy as np


def _rot(x, y, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return x * c + y * s, -x * s + y * c


def sd_circle(x, y, cx, cy, r):
    return np.hypot(x - cx, y - cy) - r


def sd_ring(x, y, cx, cy, r, w):
    return np.abs(np.hypot(x - cx, y - cy) - r) - w * 0.5


def sd_ellipse(x, y, cx, cy, rx, ry, deg):
    u, v = _rot(x - cx, y - cy, deg)
    k = np.hypot(u / rx, v / ry)
    return (k - 1.0) * min(rx, ry)


def sd_box(x, y, cx, cy, hx, hy, deg=0.0, r=0.0):
    u, v = _rot(x - cx, y - cy, deg)
    qx, qy = np.abs(u) - hx + r, np.abs(v) - hy + r
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def sd_leaf(x, y, cx, cy, length, width, deg):
    """A vesica (two intersecting circles): pointed at both ends, `length` long along its axis."""
    u, v = _rot(x - cx, y - cy, deg)
    h = length * 0.5
    w = width * 0.5
    R = (h * h + w * w) / (2 * w)
    d1 = np.hypot(u, v - (w - R)) - R
    d2 = np.hypot(u, v + (w - R)) - R
    return np.maximum(d1, d2)


def emblem_sdf(x, y):
    ring = sd_ring(x, y, 0, 0, 0.43, 0.055)
    head = sd_ellipse(x, y, -0.085, -0.2, 0.135, 0.098, 22)
    stem = sd_box(x, y, 0.03, 0.04, 0.026, 0.25, 0, 0.02)
    flag = sd_leaf(x, y, 0.165, 0.165, 0.34, 0.15, -38)
    vein = sd_box(*_rot(x - 0.165, y - 0.165, -38), 0, 0, 0.12, 0.007)
    sprout = sd_leaf(x, y, -0.07, 0.11, 0.17, 0.075, 40)
    body = np.minimum(np.minimum(np.minimum(head, stem), flag), sprout)
    body = np.maximum(body, -vein)
    return np.minimum(ring, body)


def emblem_alpha(size: int = 1024) -> np.ndarray:
    t = (np.arange(size) + 0.5) / size * 2.0 - 1.0
    x, y = np.meshgrid(t * 0.5, -t * 0.5)       # emblem units: the disc spans −0.5..0.5; rows top-down
    d = emblem_sdf(x, y)
    px = 1.0 / size
    return np.clip(0.5 - d / px, 0.0, 1.0).astype(np.float32)


if __name__ == '__main__':
    import sys
    from PIL import Image
    a = emblem_alpha(512)
    Image.fromarray((a * 255).astype(np.uint8)).save(sys.argv[1] if len(sys.argv) > 1 else 'emblem.png')
