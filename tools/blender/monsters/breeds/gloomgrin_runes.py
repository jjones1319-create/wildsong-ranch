"""Gloomgrin's runes (Art 2.1 Ultra): faint violet lines etched into the stone (the card; 1-hero, 2-turnaround, 4-details
panels 5 and 6). Our own small geometric glyphs (square spirals, diamonds, chevrons, hooks, arcs), each a set of 2-D
polylines in a unit square, laid on the body as a decal: projected along its own normal, so it follows the stone's
plates. Used three ways from the same mask: a shallow etched groove in the high source (the normal map), the violet
paint and the glow (ORM alpha).

Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from lib.surface import smooth, v3

# each glyph: polylines in [-1, 1]² (x right, y up as seen facing the surface)
GLYPHS: dict[str, list[list[tuple[float, float]]]] = {
    # a square spiral set in a diamond (the forehead's big rune, 4-details panel 6)
    'spiral': [[(0.0, 1.0), (1.0, 0.0), (0.0, -1.0), (-1.0, 0.0), (0.0, 1.0)],
               [(0.0, 0.62), (0.62, 0.0), (0.0, -0.62), (-0.42, -0.2), (0.0, 0.22), (0.2, 0.0), (0.0, -0.2)]],
    # a diamond with a small diamond inside (the thighs)
    'diamond': [[(0.0, 1.0), (0.82, 0.0), (0.0, -1.0), (-0.82, 0.0), (0.0, 1.0)],
                [(0.0, 0.34), (0.28, 0.0), (0.0, -0.34), (-0.28, 0.0), (0.0, 0.34)]],
    # an S of square hooks (the back of the head)
    'hook': [[(-0.55, 0.95), (0.5, 0.95), (0.5, 0.1), (-0.5, 0.1), (-0.5, -0.9), (0.55, -0.9), (0.55, -0.35), (0.0, -0.35)]],
    # two nested chevrons (the forearms)
    'chevron': [[(-0.9, 0.7), (0.0, -0.35), (0.9, 0.7)], [(-0.55, 0.85), (0.0, 0.25), (0.55, 0.85)],
                [(0.0, -0.35), (0.0, -0.95)]],
    # a hooked bracket (the cheeks and the chest's sides)
    'bracket': [[(0.6, 0.9), (-0.45, 0.9), (-0.45, -0.9), (0.6, -0.9), (0.6, -0.25), (0.1, -0.25)]],
    # a broken arc with a tick (the sides of the head's back, the hips)
    'arc': [[(-0.95, -0.3), (-0.72, 0.35), (-0.25, 0.78), (0.3, 0.78)], [(0.62, 0.55), (0.92, -0.05)],
            [(-0.25, 0.78), (-0.25, 0.3)]],
}

LINE_HALF = 0.005          # the etched line's half width (metres): about 7 mm wide (round 2: thicker strokes)
GLOW_HALO = 4.0             # the soft glow reaches this many half widths


def frame(c, n, up=(0.0, 0.0, 1.0), roll: float = 0.0):
    n = v3(n) / np.linalg.norm(n)
    u = v3(up) - n * float(v3(up) @ n)
    if np.linalg.norm(u) < 1e-6:
        u = np.array([0.0, 1.0, 0.0]) - n * n[1]
    u = u / np.linalg.norm(u)
    r = np.cross(u, n)                   # right, as seen looking at the surface (against n)
    if roll:
        a = math.radians(roll)
        r, u = r * math.cos(a) + u * math.sin(a), -r * math.sin(a) + u * math.cos(a)
    return v3(c), n, r, u


def _poly_dist(px: np.ndarray, py: np.ndarray, lines) -> np.ndarray:
    d = np.full(len(px), np.inf)
    for line in lines:
        pts = np.array(line, np.float64)
        for a, b in zip(pts[:-1], pts[1:]):
            ab = b - a
            L2 = max(float(ab @ ab), 1e-12)
            t = np.clip(((px - a[0]) * ab[0] + (py - a[1]) * ab[1]) / L2, 0.0, 1.0)
            dx, dy = px - (a[0] + t * ab[0]), py - (a[1] + t * ab[1])
            d = np.minimum(d, np.sqrt(dx * dx + dy * dy))
    return d


def placements() -> list[dict]:
    """Every rune on the body (left-side ones are mirrored to the right): centre, outward normal, size (half extent,
    metres), glyph, roll. From the pictures: the forehead, the cheeks, the shoulders, the forearms, the chest's sides,
    the thighs, the back of the head (one big S and an arc each side), the hips' backs and the tail."""
    one = [
        {'c': (0.0, -0.176, 0.888), 'n': (0.0, -0.8, 0.6), 'size': 0.046, 'glyph': 'spiral'},
        {'c': (0.0, 0.14, 0.745), 'n': (0.0, 0.97, 0.22), 'size': 0.05, 'glyph': 'hook'},
    ]
    both = [
        {'c': (0.185, -0.115, 0.752), 'n': (0.72, -0.68, 0.12), 'size': 0.026, 'glyph': 'bracket', 'facing': 0.3},
        {'c': (0.232, -0.045, 0.47), 'n': (0.72, -0.62, 0.3), 'size': 0.038, 'glyph': 'spiral'},
        {'c': (0.325, -0.06, 0.36), 'n': (0.85, 0.35, 0.1), 'size': 0.024, 'glyph': 'chevron', 'roll': 18.0, 'facing': 0.45},
        {'c': (0.148, 0.02, 0.395), 'n': (1.0, 0.05, -0.05), 'size': 0.028, 'glyph': 'bracket'},
        {'c': (0.17, -0.075, 0.22), 'n': (0.32, -0.95, 0.0), 'size': 0.043, 'glyph': 'diamond'},
    ]
    out = list(one)
    for g in both:
        out.append(dict(g))
        m = dict(g)
        m['c'] = (-g['c'][0], g['c'][1], g['c'][2])
        m['n'] = (-g['n'][0], g['n'][1], g['n'][2])
        m['mirror'] = True
        m['roll'] = -g.get('roll', 0.0)
        out.append(m)
    return out


def rune_field(p: np.ndarray, vn: np.ndarray | None = None, runes: list[dict] | None = None,
               half: float = LINE_HALF) -> tuple[np.ndarray, np.ndarray]:
    """(line 0..1, halo 0..1) per point: the etched line's core and its soft glow, over every placed rune. `vn` (the
    surface normals) keeps a decal off surfaces facing away (the far side of a limb)."""
    line = np.zeros(len(p))
    halo = np.zeros(len(p))
    for r in (runes if runes is not None else placements()):
        c, n, rt, up = frame(r['c'], r['n'], r.get('up', (0.0, 0.0, 1.0)), r.get('roll', 0.0))
        if vn is not None and r.get('snap', True):
            ok = np.nonzero((vn @ n) > 0.5)[0]
            if len(ok):
                c = p[ok[int(np.argmin(((p[ok] - c[None]) ** 2).sum(1)))]].copy()
        size = float(r['size'])
        q = p - c[None]
        dn = q @ n
        x = (q @ rt) / size
        y = (q @ up) / size
        if r.get('mirror'):
            x = -x
        near = (np.abs(dn) < 0.8 * size) & (np.abs(x) < 1.35) & (np.abs(y) < 1.35)
        if vn is not None:
            near &= (vn @ n) > float(r.get('facing', 0.15))
        if not near.any():
            continue
        idx = np.nonzero(near)[0]
        d = _poly_dist(x[idx], y[idx], GLYPHS[r['glyph']]) * size
        line[idx] = np.maximum(line[idx], smooth(half * 1.05, half * 0.45, d))
        halo[idx] = np.maximum(halo[idx], smooth(half * GLOW_HALO, half, d))
    return line, halo


def wing_runes(wuv: np.ndarray, side: np.ndarray, width: float = 0.07) -> tuple[np.ndarray, np.ndarray]:
    """Two small runes on each wing's membrane (2-turnaround, 4-details panel 4), laid in the membrane's own (panel,
    u, v) coordinates: a diamond in the outer panel and a spiral in the inner one. `width` is the line's half width in
    glyph units (about 3 mm on these sizes)."""
    panel, u, v = wuv[:, 0], wuv[:, 1], wuv[:, 2]
    line = np.zeros(len(u))
    halo = np.zeros(len(u))
    for pan, cu, cv, su, sv, g in ((0, 0.5, 0.6, 0.3, 0.13, 'diamond'), (1, 0.45, 0.5, 0.16, 0.16, 'spiral')):
        on = (np.abs(panel - pan) < 0.5) & (side != 0)
        if not on.any():
            continue
        idx = np.nonzero(on)[0]
        x = (u[idx] - cu) / su
        y = (v[idx] - cv) / sv
        d = _poly_dist(x, y, GLYPHS[g])
        line[idx] = np.maximum(line[idx], smooth(width * 1.05, width * 0.45, d))
        halo[idx] = np.maximum(halo[idx], smooth(width * GLOW_HALO, width, d))
    return line, halo
