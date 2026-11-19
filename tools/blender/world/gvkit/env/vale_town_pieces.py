"""vale_town_pieces.py — W18-town: new pieces for the Vale kit (`vale_`), built into the same kit by
build_kit_vale.build_vale (its last line: `vale_town_pieces.build(kit, globals())`).

  ground cover (W7, W10)   short grass, seeding grass, flowers (slot 13 = the head the game repaints), a fern, bracken,
                           leaf litter and needle litter, root flares for a tree's foot, a mossy stone, a fallen branch
  second tree shapes (W8)  vale_oak_b, vale_pine_b, vale_ash_b, vale_yew_b: the same height class, slots and budget
                           as the first shape, a different silhouette
  back yards (W18, W20)    an open crate of cabbages, a water butt, a bean bed, a washing line, a woodshed, a privy, a
                           hen run, a hedge that tiles along x
  landmarks (W30, W33)     a tower windmill and its sails (a separate piece the game turns), the watermill's wheel cut
                           out of vale_watermill (likewise), a beacon tower, Gravehollow Keep's towers on the skyline

This module must NOT import build_kit_vale (that runs main() on import): the build's own helpers (R, T, Rz, jit, card,
town_window, town_door, on_face, face_to, …) come from the globals() dict build() is given. Conventions: kit_lib.py's
docstring (pivots, the `gv` codes — A 0 = a window pane, A 0.95 = trim the game repaints), build_kit_vale.py's header
(the Vale's slots: 1 is packed EARTH here, not dark stone). Every piece: origin at the centre of its footprint on the
ground, its front toward Blender −Y.
"""
import math

from mathutils import Matrix, Vector

import kit_lib as K
from kit_lib import (STONE, DSTONE, WOOD, DWOOD, IRON, INK, CLOTH1, CLOTH2, ROPE, BRASS, GLOW, MOSS, BONE, WATER)

EARTH = DSTONE                  # slot 1: the Vale's packed earth (roads, beds)
UP = Vector((0.0, 0.0, 1.0))

# The build's helpers, bound from its globals() by build() (see the module docstring).
R = T = Rz = Rx = Ry = jit = card = town_window = town_door = on_face = face_to = flute = plan_size = None
pyramid = slit = flat_strip = None
_SHARED = ('R', 'T', 'Rz', 'Rx', 'Ry', 'jit', 'card', 'town_window', 'town_door', 'on_face', 'face_to', 'flute',
           'plan_size', 'pyramid', 'slit', 'flat_strip')


def _bind(ns):
    missing = [k for k in _SHARED if k not in ns]
    if missing:
        raise RuntimeError('vale_town_pieces: build_kit_vale has no ' + ', '.join(missing))
    g = globals()
    for k in _SHARED:
        g[k] = ns[k]


def _dir(deg):
    """(the horizontal unit direction at `deg`, its left-hand side)."""
    a = math.radians(deg)
    d = Vector((math.cos(a), math.sin(a), 0.0))
    return d, Vector((-d.y, d.x, 0.0))


def _cover(p, double=True):
    """Ground cover: walked through (no collider), and two-sided unless it lies flat."""
    p.info['no_collider'] = True
    if double:
        p.info['doubleSided'] = True
    return p


def _tri(g, a, b, c, slot, var, toward, smooth=0.0):
    i = face_to(g, [tuple(a), tuple(b), tuple(c)], slot, var, tuple(toward))
    if smooth and i is not None:
        g.A[i] = float(smooth)
    return i


def _lump(g, rng, x, y, z, r, rise, slot, var):
    """A low round lump (a cabbage, a turnip): a four-sided pyramid with smoothed normals and no base (4 tris)."""
    a0 = rng.uniform(0.0, 90.0)
    base = [Vector((x + r * math.cos(math.radians(a0 + 90 * k)), y + r * math.sin(math.radians(a0 + 90 * k)), z))
            for k in range(4)]
    apex = Vector((x + jit(rng, 0.02), y + jit(rng, 0.02), z + rise))
    ib = [g.v(tuple(q)) for q in base]                      # shared corners, so the smoothing rounds the lump
    ia = g.v(tuple(apex))
    for k in range(4):
        g.f((ib[k], ib[(k + 1) % 4], ia), slot, var, smooth=75)


# ====================================================================== ground cover (W7, W10)
def grass_short(kit):
    """A short tuft: four single-triangle blades 0.15–0.26 m, leaning out a little from a 0.08 m foot."""
    rng = R('vale_grass_short')
    g = K.Geo()
    for i in range(4):
        d, s = _dir(i * 90 + 20 + jit(rng, 22))
        c = d * rng.uniform(0.012, 0.035)
        w = rng.uniform(0.026, 0.034)
        tip = c + d * rng.uniform(0.05, 0.11) + s * jit(rng, 0.025) + UP * rng.uniform(0.15, 0.26)
        g.pf([tuple(c + s * w), tuple(c - s * w), tuple(tip)], MOSS, rng.uniform(0.42, 0.58), smooth=0)
    p = kit.add('vale_grass_short', g, budget=4, bake={'skip': True}, sheet={'az': 30, 'el': 20})
    return _cover(p)


def grass_seed(kit):
    """Seeding grass: three thin blades 0.32–0.48 m and two dry stalks to ~0.55 m, each with a thin seed head."""
    rng = R('vale_grass_seed')
    g = K.Geo()
    for i in range(3):
        d, s = _dir(i * 120 + 10 + jit(rng, 20))
        c = d * rng.uniform(0.01, 0.035)
        w = rng.uniform(0.02, 0.026)
        tip = c + d * rng.uniform(0.08, 0.16) + s * jit(rng, 0.03) + UP * rng.uniform(0.32, 0.48)
        g.pf([tuple(c + s * w), tuple(c - s * w), tuple(tip)], MOSS, rng.uniform(0.44, 0.56), smooth=0)
    for i in range(2):
        d, s = _dir(i * 180 + 70 + jit(rng, 25))
        c = d * 0.02
        top = c + d * rng.uniform(0.06, 0.11) + UP * rng.uniform(0.53, 0.57)
        g.pf([tuple(c + s * 0.009), tuple(c - s * 0.009), tuple(c.lerp(top, 0.8))], ROPE, 0.46, smooth=0)   # stalk
        foot = c.lerp(top, 0.72)
        g.pf([tuple(foot + s * 0.024), tuple(foot - s * 0.024), tuple(top)], ROPE, 0.55, smooth=0)          # head
    p = kit.add('vale_grass_seed', g, budget=8, bake={'skip': True}, sheet={'az': 30, 'el': 16})
    return _cover(p)


def flowers(kit):
    """Wild flowers: three leaf-blade stems 0.18–0.3 m, each holding a flat six-pointed head (two triangles, ~0.08 m
    across, tilted up and out) in slot 13 — the game repaints slot 13 on this piece white, yellow or violet — and one
    short blade at the foot."""
    rng = R('vale_flowers')
    g = K.Geo()
    for i in range(3):
        d, s = _dir(i * 120 + 30 + jit(rng, 18))
        c = d * rng.uniform(0.02, 0.05)
        top = c + d * rng.uniform(0.04, 0.09) + UP * rng.uniform(0.18, 0.3)
        g.pf([tuple(c + s * 0.026), tuple(c - s * 0.026), tuple(top)], MOSS, rng.uniform(0.4, 0.5), smooth=0)
        t = math.radians(rng.uniform(20, 32))
        n = (UP * math.cos(t) + d * math.sin(t)).normalized()
        u = s.normalized()
        v = n.cross(u)
        for j, ph in enumerate((90.0, 30.0)):
            ctr = top + n * (0.004 + 0.003 * j)
            pts = [ctr + (u * math.cos(math.radians(ph + 120 * k)) + v * math.sin(math.radians(ph + 120 * k))) * 0.04
                   for k in range(3)]
            face_to(g, [tuple(q) for q in pts], BONE, 0.62 - 0.05 * j, tuple(n))
    d, s = _dir(rng.uniform(0, 360))
    c = d * 0.03
    g.pf([tuple(c + s * 0.03), tuple(c - s * 0.03), tuple(c + d * 0.07 + UP * 0.13)], MOSS, 0.46, smooth=0)
    p = kit.add('vale_flowers', g, budget=10, bake={'skip': True}, sheet={'az': 30, 'el': 34})
    return _cover(p)


def fern(kit):
    """A fern: seven arching fronds from the centre, each a tapering strip bent once (3 tris), rising to ~0.5 m and
    arching out to ~0.6 m."""
    rng = R('vale_fern')
    g = K.Geo()
    for i in range(7):
        d, s = _dir(i * 360.0 / 7 + jit(rng, 14))
        k = rng.uniform(0.86, 1.06)
        b = d * 0.03 + UP * 0.02
        m = d * 0.28 * k + s * jit(rng, 0.03) + UP * rng.uniform(0.44, 0.52)
        tip = d * 0.62 * k + s * jit(rng, 0.05) + UP * rng.uniform(0.15, 0.23)
        bw, mw = 0.02, rng.uniform(0.085, 0.1)
        v = rng.uniform(0.32, 0.48)
        g.pf([tuple(b - s * bw), tuple(b + s * bw), tuple(m + s * mw), tuple(m - s * mw)], CLOTH1, v, smooth=0)
        g.pf([tuple(m - s * mw), tuple(m + s * mw), tuple(tip)], CLOTH1, v, smooth=0)
    p = kit.add('vale_fern', g, budget=26, bake={'skip': True}, sheet={'az': 30, 'el': 30})
    return _cover(p)


def bracken(kit):
    """Bracken: four stems 0.65–0.9 m, each ending in a broad flat frond (a fan of four triangles) tilted down and out;
    one frond dying (straw)."""
    rng = R('vale_bracken')
    g = K.Geo()
    for i in range(4):
        a = i * 90 + 40 + jit(rng, 18)
        d, s = _dir(a)
        slot, v = (ROPE, 0.4) if i == 2 else (CLOTH1, rng.uniform(0.42, 0.52))
        c = d * rng.uniform(0.03, 0.08)
        hub = c + d * rng.uniform(0.1, 0.16) + UP * rng.uniform(0.65, 0.9)
        g.pf([tuple(c + s * 0.014), tuple(c - s * 0.014), tuple(hub)], slot, v - 0.12, smooth=0)          # the stem
        d2, s2 = _dir(a + jit(rng, 12))
        pitch = math.tan(math.radians(rng.uniform(8, 18)))
        roll = rng.uniform(-0.25, 0.25)

        def at(along, side, droop=0.0):
            q = hub + d2 * along + s2 * side
            return q + UP * (-pitch * along + roll * side - droop)
        rim = [at(0.05, -0.27), at(0.33, -0.17, 0.02), at(0.62, 0.0, 0.07), at(0.33, 0.17, 0.02), at(0.05, 0.27)]
        for k in range(4):
            _tri(g, hub, rim[k], rim[k + 1], slot, v + jit(rng, 0.03), UP)
    p = kit.add('vale_bracken', g, budget=24, bake={'skip': True}, sheet={'az': 30, 'el': 26})
    return _cover(p)


def _litter(kit, mesh_id, rx, ry, slot, var, rim_n, flecks, budget):
    """A flat patch of litter at z 0.015 (a fan round its centre, one shade per triangle) and single flecks at z 0.02,
    all facing up; flecks = [(slot, var, length, width)]."""
    rng = R(mesh_id)
    g = K.Geo()
    ctr = Vector((0.0, 0.0, 0.016))
    rim = []
    for k in range(rim_n):
        a = 2 * math.pi * k / rim_n + jit(rng, 0.25)
        f = 1 + jit(rng, 0.18)
        rim.append(Vector((math.cos(a) * rx * f, math.sin(a) * ry * f, 0.015)))
    for k in range(rim_n):
        _tri(g, ctr, rim[k], rim[(k + 1) % rim_n], slot, rng.uniform(*var), UP)
    for (fs, fv, ln, wd) in flecks:
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.15, 0.65)
        c = Vector((math.cos(a) * rx * r, math.sin(a) * ry * r, 0.02))
        d, s = _dir(rng.uniform(0, 360))
        _tri(g, c - d * (ln / 2) + s * (wd / 2), c - d * (ln / 2) - s * (wd / 2), c + d * (ln / 2) + s * jit(rng, wd / 3),
             fs, fv, UP)
    p = kit.add(mesh_id, g, budget=budget, bake={'skip': True}, sheet={'az': 30, 'el': 55})
    return _cover(p, double=False)


def leaf_litter(kit):
    """Fallen leaves for the broadleaf woods: a darker earth patch ~1.6 × 1.2 m and five leaf flecks (straw, sand)."""
    return _litter(kit, 'vale_leaf_litter', 0.8, 0.6, EARTH, (0.32, 0.45), 8,
                   [(ROPE, 0.52, 0.1, 0.07), (BRASS, 0.56, 0.09, 0.07), (ROPE, 0.6, 0.08, 0.06),
                    (BRASS, 0.5, 0.1, 0.06), (ROPE, 0.46, 0.09, 0.07)], 14)


def needle_litter(kit):
    """Fallen needles for the pinewoods: a bark-brown patch ~1.5 × 1.3 m and four straw flecks (needle drifts)."""
    return _litter(kit, 'vale_needle_litter', 0.75, 0.65, DWOOD, (0.45, 0.55), 8,
                   [(ROPE, 0.5, 0.16, 0.03), (ROPE, 0.56, 0.14, 0.025), (ROPE, 0.46, 0.15, 0.03),
                    (ROPE, 0.6, 0.12, 0.03)], 12)


def roots(kit):
    """Root flares for a tree's foot: four low wedges radiating from the trunk (r 0.22; their inner ends tucked in to
    r 0.12 so a thinner trunk still meets them) out to 0.8–1.3 m, 0.12–0.22 m high at the trunk and running into the
    ground at the tip, each bent a little (6 tris)."""
    rng = R('vale_roots')
    g = K.Geo()
    for i in range(4):
        d, s = _dir(i * 90 + 30 + jit(rng, 20))
        ln = rng.uniform(0.8, 1.3)
        h = rng.uniform(0.12, 0.22)
        w = rng.uniform(0.11, 0.15)
        bend = jit(rng, 0.14)
        rm = 0.22 + 0.32 * (ln - 0.22)
        ci, cm, ct = d * 0.12, d * rm + s * bend * 0.4, d * ln + s * bend
        lo = Vector((0, 0, -0.02))
        li, ri, ti = ci + s * w + lo, ci - s * w + lo, ci + UP * h
        lm, rm_, tm = cm + s * w * 0.62 + lo, cm - s * w * 0.62 + lo, cm + UP * h * 0.42
        tip = ct + Vector((0, 0, -0.01))
        v = rng.uniform(0.38, 0.46)
        left, right = s + UP * 0.6, -s + UP * 0.6
        _tri(g, li, lm, tm, DWOOD, v, left, 35)
        _tri(g, li, tm, ti, DWOOD, v, left, 35)
        _tri(g, lm, tip, tm, DWOOD, v, left, 35)
        _tri(g, ri, ti, tm, DWOOD, v - 0.03, right, 35)
        _tri(g, ri, tm, rm_, DWOOD, v - 0.03, right, 35)
        _tri(g, rm_, tm, tip, DWOOD, v - 0.03, right, 35)
    p = kit.add('vale_roots', g, budget=26, bake={'skip': True}, sheet={'az': 30, 'el': 40})
    return _cover(p, double=False)


def moss_stone(kit):
    """A stone ~0.5 × 0.4 × 0.3 m whose upward faces are mossed over (normal z > 0.55: slot 12)."""
    rng = R('vale_moss_stone')
    g = K.Geo()
    K.rock(g, rng, (0.0, 0.0, 0.55 * 0.2 - 0.02), (0.27, 0.22, 0.2),
           lambda c, n: MOSS if n.z > 0.55 else STONE, n=12,
           var=lambda c, n: 0.4 if n.z > 0.55 else 0.4 + 0.04 * (c.x > 0))
    p = kit.add('vale_moss_stone', g, budget=24, bake={'skip': True}, sheet={'az': 30, 'el': 26})
    return _cover(p, double=False)


def branch(kit):
    """A fallen branch on the ground: a bent run of three segments (r 0.06 → 0.035, ~1.75 m) with an open underside,
    a pale cut at the thick end, the thin end closed, and one short fork (22 tris)."""
    rng = R('vale_branch')
    g = K.Geo()
    path = [Vector((-0.85, -0.04, 0)), Vector((-0.3, 0.07, 0)), Vector((0.25, 0.0, 0)), Vector((0.85, 0.13, 0))]
    radii = [0.06, 0.052, 0.044, 0.035]
    rings, frames = [], []
    for i, (c, r) in enumerate(zip(path, radii)):
        t = (path[min(i + 1, 3)] - path[max(i - 1, 0)]).normalized()
        s = Vector((-t.y, t.x, 0.0))
        frames.append((t, s))
        if i < 3:
            rings.append([c - s * 0.95 * r + UP * -0.006, c - s * 0.6 * r + UP * 1.5 * r,
                          c + s * 0.6 * r + UP * 1.5 * r, c + s * 0.95 * r + UP * -0.006])
        else:
            rings.append([c - s * 0.9 * r + UP * -0.006, c + UP * 1.4 * r, c + s * 0.9 * r + UP * -0.006])
    for i in range(3):
        a, b = rings[i], rings[i + 1]
        t, s = frames[i]
        v = rng.uniform(0.4, 0.46)
        if len(b) == 4:
            for (j, side) in ((0, -s + UP * 0.3), (1, UP), (2, s + UP * 0.3)):
                _tri(g, a[j], b[j], b[j + 1], DWOOD, v, side)
                _tri(g, a[j], b[j + 1], a[j + 1], DWOOD, v, side)
        else:
            _tri(g, a[0], b[0], b[1], DWOOD, v, -s + UP * 0.3)
            _tri(g, a[0], b[1], a[1], DWOOD, v, -s + UP * 0.3)
            _tri(g, a[1], b[1], a[2], DWOOD, v, UP)
            _tri(g, a[2], b[1], b[2], DWOOD, v, s + UP * 0.3)
            _tri(g, a[2], b[2], a[3], DWOOD, v, s + UP * 0.3)
    t0 = frames[0][0]
    face_to(g, [tuple(p) for p in rings[0]], WOOD, 0.56, tuple(-t0))                               # the cut end
    _tri(g, rings[3][0], rings[3][1], rings[3][2], DWOOD, 0.38, frames[3][0])                     # the thin end
    base = path[1].lerp(path[2], 0.6)
    t, s = frames[1]
    df = (t * math.cos(math.radians(38)) + s * math.sin(math.radians(38))).normalized()
    sf = Vector((-df.y, df.x, 0.0))
    fl, ft, fr = base - sf * 0.028 + UP * -0.004, base + UP * 0.05, base + sf * 0.028 + UP * -0.004
    tip = base + df * 0.42 + UP * 0.02
    _tri(g, fl, tip, ft, DWOOD, 0.43, -sf + UP)
    _tri(g, ft, tip, fr, DWOOD, 0.4, sf + UP)
    p = kit.add('vale_branch', g, budget=22, bake={'skip': True}, sheet={'az': 30, 'el': 34})
    return _cover(p, double=False)


# ====================================================================== second tree shapes (W8)
def oak_b(kit):
    """A second oak: a trunk leaning a little and forking into two limbs (and a short third), the crown an irregular
    tall oval of seven leaf masses set off to one side (+x) — not vale_oak's round dome — to ~5.8 m."""
    rng = R('vale_oak_b')
    g = K.Geo()
    K.tube(g, (0, 0, 0), (0.22, 0.08, 2.0), 0.26, DWOOD, r1=0.19, n=7, var=0.4, cap0=False)
    fork = (0.2, 0.07, 1.9)
    for end, r in (((1.05, 0.35, 3.9), 0.15), ((-0.25, -0.1, 4.05), 0.14), ((0.7, -0.6, 3.5), 0.09)):
        K.tube(g, fork, end, r, DWOOD, r1=r * 0.55, n=5, var=0.38, cap0=False)
    blobs = [((0.55, 0.05, 4.1), (1.35, 1.25, 1.55), 11), ((1.6, 0.35, 3.55), (0.95, 0.9, 0.8), 9),
             ((-0.5, -0.25, 3.8), (0.95, 0.9, 0.85), 9), ((0.95, -0.95, 4.2), (0.85, 0.8, 0.8), 9),
             ((0.15, 0.95, 4.45), (0.9, 0.85, 0.85), 9), ((0.75, 0.25, 5.15), (0.85, 0.8, 0.6), 9),
             ((1.7, -0.25, 4.7), (0.7, 0.65, 0.6), 9)]
    for i, (c, sz, n) in enumerate(blobs):
        c = (c[0], c[1], c[2] + 0.2)                                          # the crown's top to ~5.8 m
        K.rock(g, rng, c, sz, CLOTH1, n=n, var=0.42 + 0.1 * (i % 3), flat=False, smooth=0)
    p = kit.add('vale_oak_b', g, budget=220, sheet={'az': 30, 'el': 14})
    lo, hi = g.bounds()
    p.info['canopy'] = round(hi.z, 2)
    return p


def pine_b(kit):
    """A second pine: taller and narrower than vale_pine (6.4 m, six tiers at ~0.8 of its radii), the lower tiers
    drooping more; the same slot (7), single-sided like the pine."""
    rng = R('vale_pine_b')
    h = 6.4
    g = K.Geo()
    K.tube(g, (0, 0, 0), (0, 0, h * 0.28), 0.15, DWOOD, r1=0.1, n=6, var=0.42, cap0=False)
    tiers = [(0.15, 0.40, 1.06, 8), (0.28, 0.52, 0.92, 8), (0.41, 0.64, 0.78, 7), (0.54, 0.76, 0.63, 7),
             (0.67, 0.88, 0.48, 6), (0.79, 1.0, 0.31, 5)]
    for i, (z0, z1, r, n) in enumerate(tiers):
        droop = 0.26 - 0.04 * i
        mk = g.mark()
        prof = [(0.0, z0 * h - 0.1 - droop), (r, z0 * h), (0.0, z1 * h)]
        K.lathe(g, prof, n, CLOTH2, lambda b, k, i=i: 0.36 + 0.08 * i + jit(rng, 0.08), smooth=0,
                cap0=False, cap1=False, phase=rng.uniform(0, 1))
        for vi in range(mk[0], len(g.V)):
            v = g.V[vi]
            if math.hypot(v.x, v.y) > 0.5 * r:
                k = 1 + jit(rng, 0.09)
                g.V[vi] = Vector((v.x * k, v.y * k, v.z - rng.uniform(droop * 0.5, droop)))
    p = kit.add('vale_pine_b', g, budget=120, sheet={'az': 30, 'el': 14})
    p.info['doubleSided'] = False
    p.info['canopy'] = h
    return p


def ash_b(kit):
    """A second ash: vale_ash's straight grey trunk and airy clusters, but the crown set higher and opened into two
    lobes (left and right of a gap) with a small leader between them."""
    rng = R('vale_ash_b')
    g = K.Geo()
    K.tube(g, (0, 0, 0), (-0.05, 0.04, 5.3), 0.2, STONE, r1=0.1, n=6, var=0.4, cap0=False)
    clusters = [((-0.05, 0.04, 6.75), (0.75, 0.7, 0.6), None),                                   # the leader
                ((-1.75, 0.35, 5.7), (1.25, 1.15, 0.95), 4.3), ((-2.3, -0.75, 5.0), (0.95, 0.9, 0.72), 3.9),
                ((-1.05, -0.95, 6.35), (0.9, 0.85, 0.7), 4.7), ((-1.35, 1.25, 6.45), (0.8, 0.75, 0.6), 4.9),
                ((1.65, -0.25, 6.05), (1.25, 1.15, 0.95), 4.6), ((2.2, 0.85, 5.3), (0.95, 0.9, 0.72), 4.1),
                ((0.95, 0.95, 6.8), (0.9, 0.85, 0.65), 5.1), ((1.85, -1.3, 5.25), (0.8, 0.75, 0.6), 4.2)]
    for i, (c, sz, zb) in enumerate(clusters):
        if zb is not None:
            K.tube(g, (0.0, 0.0, zb - 0.3), (c[0] * 0.8, c[1] * 0.8, c[2] - 0.15), 0.08 if sz[0] > 1.0 else 0.07,
                   STONE, r1=0.03, n=3, var=0.44, cap0=False, cap1=False)
        K.rock(g, rng, c, sz, CLOTH1, n=9, var=0.74 + 0.06 * (i % 3), flat=False, smooth=0)
    p = kit.add('vale_ash_b', g, budget=200, sheet={'az': 30, 'el': 14})
    lo, hi = g.bounds()
    p.info['canopy'] = round(hi.z, 2)
    p.info['footprint'] = plan_size(g)
    return p


def yew_b(kit):
    """A second yew: vale_yew's dark fluted trunk, shorter, splitting into two leaders under a broad, low crown cleft
    in two (two domes either side of a notch, six lobes round their skirts) — ~8 m across, ~5.4 m tall."""
    rng = R('vale_yew_b')
    g = K.Geo()
    mk = g.mark()
    K.lathe(g, [(0.55, 0.0), (0.46, 0.5), (0.4, 1.2), (0.34, 1.8), (0.26, 2.4)], 10, DWOOD,
            lambda b, k: 0.3 + jit(rng, 0.05), smooth=30, cap0=False, cap1=False)
    flute(g, mk, 10)
    g.transform(Matrix.Shear('XY', 4, (-0.04, 0.03)), mk)
    lift = 0.5                                                      # the crown raised so its top is ~5.4 m
    for a, zt, ln, r in ((0, 3.5, 1.9, 0.16), (180, 3.4, 1.9, 0.16), (95, 3.1, 1.5, 0.1), (275, 3.0, 1.5, 0.1)):
        zt += lift
        d = Vector((math.cos(math.radians(a)) * ln, math.sin(math.radians(a)) * ln, 0))
        K.tube(g, (-0.04, 0.03, 2.1), tuple(d + Vector((-0.04, 0.03, zt))), r, DWOOD, r1=0.05, n=4, var=0.34,
               cap0=False, cap1=False)
    blobs = [((-1.8, 0.05, 3.85), (2.2, 2.1, 1.35), 11), ((1.85, -0.1, 3.7), (2.1, 2.0, 1.3), 11)]
    for (x, y, z, sz) in ((-3.0, 1.0, 3.1, (1.3, 1.2, 0.95)), (-2.7, -1.45, 3.0, (1.3, 1.2, 0.9)),
                          (-0.35, 1.7, 3.25, (1.25, 1.15, 0.9)), (0.3, -1.7, 3.15, (1.25, 1.15, 0.9)),
                          (3.0, 1.2, 3.0, (1.3, 1.2, 0.9)), (2.8, -1.5, 3.05, (1.3, 1.2, 0.95))):
        blobs.append(((x, y, z), sz, 9))
    for i, (c, sz, n) in enumerate(blobs):
        K.rock(g, rng, (c[0], c[1], c[2] + lift), sz, CLOTH2, n=n, var=0.38 + 0.08 * (i % 3), flat=False, smooth=0)
    p = kit.add('vale_yew_b', g, budget=280, sheet={'az': 30, 'el': 14})
    lo, hi = g.bounds()
    p.info['canopy'] = round(hi.z, 2)
    p.info['footprint'] = plan_size(g)
    p.info['node'] = True
    return p


# ====================================================================== back yards (W18, W20)
def crate_b(kit):
    """An open crate heaped with cabbages: a slatted crate 0.9 × 0.6 × 0.45 m (two boards a side) brimming with dark
    leaves and four round heads on top."""
    rng = R('vale_crate_b')
    g = K.Geo()
    hx, hy, h = 0.45, 0.3, 0.45
    zs = (0.0, 0.225, h)
    cs = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    for k in range(4):
        (xa, ya), (xb, yb) = cs[k], cs[(k + 1) % 4]
        for j in range(2):
            g.pf([(xa, ya, zs[j]), (xb, yb, zs[j]), (xb, yb, zs[j + 1]), (xa, ya, zs[j + 1])], WOOD,
                 (0.38, 0.6)[j] + jit(rng, 0.03))
    g.pf([(-hx, -hy, h), (hx, -hy, h), (hx, hy, h), (-hx, hy, h)], CLOTH1, 0.12)                     # the leaves
    for (x, y) in ((-0.22, -0.13), (0.21, -0.14), (-0.2, 0.14), (0.23, 0.13)):
        _lump(g, rng, x, y, h - 0.01, rng.uniform(0.155, 0.17), rng.uniform(0.16, 0.19), CLOTH1,
              rng.uniform(0.58, 0.7))
    p = kit.add('vale_crate_b', g, budget=34, sheet={'az': 30, 'el': 32})
    p.info['footprint'] = [0.9, 0.6]
    return p


def barrel_b(kit):
    """A water butt: a short wide barrel (r 0.42, h 0.65) of seven staves' faces, an iron hoop round its top, open,
    the water a few centimetres below the rim."""
    g = K.Geo()
    n, ph = 7, 0.3
    prof = [(0.385, 0.0), (0.42, 0.56), (0.405, 0.65)]
    K.lathe(g, prof, n, lambda b, k: WOOD if b == 0 else IRON, lambda b, k: (0.44 + 0.04 * (k % 2)) if b == 0 else 0.44,
            smooth=0, cap0=False, cap1=False, phase=ph)
    zw = 0.615
    rw = prof[1][0] + (prof[2][0] - prof[1][0]) * (zw - prof[1][1]) / (prof[2][1] - prof[1][1])
    K.disc(g, rw, n, WATER, z=zw, var=0.5, phase=ph)
    p = kit.add('vale_barrel_b', g, budget=34, sheet={'az': 30, 'el': 34})
    p.info['footprint'] = [0.85, 0.85]
    return p


def bean_rows(kit):
    """A vegetable bed 3.0 × 1.8 m: a low raised bed of earth (0.12 m), two bean-pole wigwams at the back (thin poles
    to 1.6 m, the beans climbing them) and a row of four cabbages at the front."""
    rng = R('vale_bean_rows')
    g = K.Geo()
    bx, by, tx, ty, zt = 1.5, 0.9, 1.38, 0.78, 0.12
    b = [(-bx, -by, -0.02), (bx, -by, -0.02), (bx, by, -0.02), (-bx, by, -0.02)]
    t = [(-tx, -ty, zt), (tx, -ty, zt), (tx, ty, zt), (-tx, ty, zt)]
    g.pf(t, EARTH, 0.42)
    for k in range(4):
        k2 = (k + 1) % 4
        g.pf([b[k], b[k2], t[k2], t[k]], EARTH, 0.36)
    for cx in (-0.75, 0.75):
        cy = 0.3
        cross = Vector((cx, cy, 1.45))
        for a in (90, 210, 330):
            a = math.radians(a + jit(rng, 10))
            base = Vector((cx + 0.36 * math.cos(a), cy + 0.36 * math.sin(a), zt - 0.02))
            top = base + (cross - base) * 1.11
            K.tube(g, tuple(base), tuple(top), 0.022, DWOOD, r1=0.014, n=3, var=0.42 + jit(rng, 0.04), cap0=False,
                   cap1=False)
        K.rock(g, rng, (cx, cy, 0.8), (0.26, 0.26, 0.55), CLOTH1, n=6, var=0.46 + jit(rng, 0.04), flat=False)
    for x in (-1.05, -0.35, 0.35, 1.05):
        _lump(g, rng, x + jit(rng, 0.05), -0.42 + jit(rng, 0.04), zt - 0.01, 0.2, rng.uniform(0.17, 0.21), CLOTH1,
              0.6 + jit(rng, 0.04))
    p = kit.add('vale_bean_rows', g, budget=80, sheet={'az': 30, 'el': 32})
    p.info['footprint'] = [3.0, 1.8]
    p.info['no_collider'] = True
    return p


def washing_line(kit):
    """A washing line: two posts 1.9 m tall 3.6 m apart along x, a sagging rope between them and four cloths hung on
    it (two pale sheets, a green and a sand one), each turned a little."""
    rng = R('vale_washing_line')
    g = K.Geo()
    for x in (-1.8, 1.8):
        K.box(g, (x - 0.045, -0.045, 0), (x + 0.045, 0.045, 1.9), DWOOD, 0.4 + jit(rng, 0.04), skip=('-z',))
    xs = (-1.8, -0.9, 0.0, 0.9, 1.8)
    zs = (1.84, 1.765, 1.735, 1.765, 1.84)

    def rope_z(x):
        for i in range(4):
            if xs[i] <= x <= xs[i + 1]:
                f = (x - xs[i]) / (xs[i + 1] - xs[i])
                return zs[i] + (zs[i + 1] - zs[i]) * f
        return zs[-1]
    K.ribbon(g, [(x, 0.0, z) for x, z in zip(xs, zs)], 0.025, ROPE, 0.56, normal=(0, -1, 0))
    # W18 (the town view's draws): both faces built, so the line draws with the town's single-sided pieces.
    K.ribbon(g, [(x, 0.0, z) for x, z in zip(xs, zs)], 0.025, ROPE, 0.56, normal=(0, 1, 0))
    for (xc, w, drop, slot, var) in ((-1.2, 0.7, 0.85, BONE, 0.62), (-0.4, 0.45, 0.55, CLOTH1, 0.55),
                                     (0.35, 0.55, 0.62, BRASS, 0.55), (1.15, 0.75, 0.9, BONE, 0.54)):
        turn = math.radians(rng.uniform(5, 12) * rng.choice((-1, 1)))
        x0, x1 = xc - w / 2, xc + w / 2
        z0, z1 = rope_z(x0) - 0.012, rope_z(x1) - 0.012
        sway = rng.uniform(0.02, 0.05)
        pts = [(x0, sway, z0 - drop), (x1, sway, z1 - drop), (x1, 0.0, z1), (x0, 0.0, z0)]
        m = T(xc, 0, 0) @ Rz(math.degrees(turn)) @ T(-xc, 0, 0)
        g.pf([tuple(m @ Vector(q)) for q in pts], slot, var)
        g.pf([tuple(m @ Vector(q)) for q in reversed(pts)], slot, var - 0.04)
    p = kit.add('vale_washing_line', g, budget=60, sheet={'az': 25, 'el': 16})
    p.info['footprint'] = [3.8, 0.4]
    p.info['doubleSided'] = False
    p.info['no_collider'] = True
    return p


def woodshed(kit):
    """A lean-to log store 2.6 × 1.4 m: a plank back wall, three posts at the front (1.9 m), a pent roof of dark
    planks sloping to the back at ~1.5 m, and the store filled with stacked logs, their pale cut ends to the front."""
    rng = R('vale_woodshed')
    g = K.Geo()
    K.box(g, (-1.25, 0.62, 0), (1.25, 0.7, 1.55), WOOD, 0.46, skip=('-z', '-x', '+x'))                # the back wall
    for x in (-1.2, 0.0, 1.2):
        K.box(g, (x - 0.05, -0.65, 0), (x + 0.05, -0.55, 1.88), DWOOD, 0.4 + jit(rng, 0.04), skip=('-z', '+z'))
    K.hull(g, [(x, y, z + dz) for x in (-1.42, 1.42) for (y, z) in ((-0.82, 1.92), (0.86, 1.48)) for dz in (0.0, 0.07)],
           DWOOD, 0.42)                                                                              # the roof
    K.box(g, (-1.15, -0.5, 0), (1.15, 0.62, 1.1), DWOOD, 0.34, skip=('-z', '+y'))                    # the stack
    for z, xs in ((0.2, (-0.87, -0.29, 0.29, 0.87)), (0.53, (-0.58, 0.0, 0.58)), (0.86, (-0.87, -0.29, 0.29))):
        for x in xs:
            K.disc(g, 0.19 + jit(rng, 0.015), 6, WOOD, var=0.54 + jit(rng, 0.1),
                   m=T(x + jit(rng, 0.02), -0.505, z + jit(rng, 0.015)) @ Rx(90), phase=rng.uniform(0, 1))
    p = kit.add('vale_woodshed', g, budget=90, sheet={'az': 30, 'el': 20})
    p.info['footprint'] = [2.6, 1.4]
    return p


def privy(kit):
    """A privy: a little plank hut 1.1 × 1.1 m, 2.1 m at the front, under a pent roof sloping to the back, a plank door
    on the front (its leaf trim, which the game repaints) with a vent cut high in it."""
    g = K.Geo()
    hx, zf, zb = 0.55, 2.1, 1.9
    c = [(-hx, -hx), (hx, -hx), (hx, hx), (-hx, hx)]
    tops = (zf, zf, zb, zb)
    for k in range(4):
        k2 = (k + 1) % 4
        g.pf([(c[k][0], c[k][1], 0.0), (c[k2][0], c[k2][1], 0.0), (c[k2][0], c[k2][1], tops[k2]),
              (c[k][0], c[k][1], tops[k])], WOOD, (0.5, 0.46, 0.48, 0.44)[k])
    K.hull(g, [(x, y, z + dz) for x in (-0.68, 0.68) for (y, z) in ((-0.7, 2.12), (0.72, 1.86)) for dz in (0.0, 0.06)],
           DWOOD, 0.42)
    m = T(0, -hx, 0)
    K.trim(g, g.pf([(-0.32, -hx - 0.015, 0.05), (0.32, -hx - 0.015, 0.05), (0.32, -hx - 0.015, 1.85),
                    (-0.32, -hx - 0.015, 1.85)], DWOOD, 0.38))                                       # the door leaf
    for a, b in (((-0.37, 0.0), (-0.37, 1.94)), ((0.37, 0.0), (0.37, 1.94)), ((-0.41, 1.9), (0.41, 1.9))):
        flat_strip(g, m, a, b, 0.08, WOOD, 0.36, y=-0.01)                                            # its frame
    g.pf([(-0.08, -hx - 0.02, 1.58), (0.08, -hx - 0.02, 1.58), (0.08, -hx - 0.02, 1.68), (-0.08, -hx - 0.02, 1.68)],
         INK, 0.5)                                                                                   # the vent
    g.pf([(0.2, -hx - 0.022, 0.95), (0.26, -hx - 0.022, 0.95), (0.26, -hx - 0.022, 1.03), (0.2, -hx - 0.022, 1.03)],
         IRON, 0.5)                                                                                  # the latch
    for side, at in (('-x', -hx), ('+x', hx)):
        flat_strip(g, on_face(side, at, 0.0, 0.0), (0.0, 0.05), (0.0, 1.85), 0.1, WOOD, 0.4, y=-0.01)
    p = kit.add('vale_privy', g, budget=40, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [1.2, 1.2]
    return p


def hen_run(kit):
    """A hen run 3.2 × 2.2 m: woven hurdle panels 0.7 m tall round it, a gap at the front, and a little hen house at
    the back right (1.0 × 0.8 × 0.8 m on short legs, a pent roof, a pop-hole and a ramp to the ground)."""
    rng = R('vale_hen_run')
    g = K.Geo()
    zt = 0.7
    top = {'+z': WOOD}
    K.box(g, (-1.54, 1.04, 0), (1.54, 1.1, zt), DWOOD, 0.4, skip=('-z', '-x', '+x'), slots=top)        # the back
    K.box(g, (-1.6, -1.1, 0), (-1.54, 1.1, zt), DWOOD, 0.36, skip=('-z', '-y', '+y'), slots=top)       # the sides
    K.box(g, (1.54, -1.1, 0), (1.6, 1.1, zt), DWOOD, 0.44, skip=('-z', '-y', '+y'), slots=top)
    K.box(g, (-1.54, -1.1, 0), (-0.45, -1.04, zt), DWOOD, 0.42, skip=('-z', '-x'), slots=top)        # the front,
    K.box(g, (0.45, -1.1, 0), (1.54, -1.04, zt), DWOOD, 0.38, skip=('-z', '+x'), slots=top)          # a gap between
    x0, x1, y0, y1, zb, zf, zk = 0.25, 1.25, 0.12, 0.92, 0.3, 1.1, 0.95
    K.hull(g, [(x0, y0, zb), (x1, y0, zb), (x1, y1, zb), (x0, y1, zb),
               (x0, y0, zf), (x1, y0, zf), (x1, y1, zk), (x0, y1, zk)], WOOD, 0.5)
    slope = (zk - zf) / (y1 - y0)
    K.hull(g, [(x, y, zf + slope * (y - y0) + dz) for x in (0.15, 1.35) for y in (0.0, 1.02) for dz in (0.0, 0.06)],
           DWOOD, 0.42)
    for x in (x0 + 0.07, x1 - 0.07):
        for y in (y0 + 0.07, y1 - 0.07):
            K.tube(g, (x, y, 0.0), (x, y, zb + 0.01), 0.035, DWOOD, n=3, var=0.4 + jit(rng, 0.04), cap0=False,
                   cap1=False)
    g.pf([(0.6, y0 - 0.006, 0.36), (0.85, y0 - 0.006, 0.36), (0.85, y0 - 0.006, 0.62), (0.6, y0 - 0.006, 0.62)],
         INK, 0.5)                                                                                    # the pop-hole
    face_to(g, [(0.6, y0 - 0.01, 0.34), (0.85, y0 - 0.01, 0.34), (0.85, -0.45, 0.0), (0.6, -0.45, 0.0)], WOOD, 0.46,
            (0, -0.6, 1))                                                                             # the ramp
    p = kit.add('vale_hen_run', g, budget=90, sheet={'az': 30, 'el': 30})
    p.info['footprint'] = [3.2, 2.2]
    return p


def hedge(kit):
    """A 2 m run of hedge tiling along x (−1…+1): three lumpy leaf masses, darker than a bush, ~1.0 m tall and 0.75 m
    deep, the end ones reaching a little past the ends so a run of them reads as one hedge."""
    rng = R('vale_hedge')
    g = K.Geo()
    for x, sx, sz, v in ((-0.64, 0.6, 0.64, 0.34), (0.0, 0.6, 0.67, 0.4), (0.64, 0.6, 0.62, 0.37)):
        K.rock(g, rng, (x, jit(rng, 0.03), 0.55 * sz - 0.02), (sx, 0.37, sz), CLOTH1, n=7, var=v + jit(rng, 0.02))
    p = kit.add('vale_hedge', g, budget=32, sheet={'az': 30, 'el': 22},
                bake={'ground': 0.0, 'occluders': [('vale_hedge', (-2.0, 0, 0)), ('vale_hedge', (2.0, 0, 0))]})
    p.info['footprint'] = [2.0, 0.75]
    p.info['span'] = 2.0
    return p


# ====================================================================== landmarks (W30) and things that turn (W33)
MILL_HUB = (0.0, -1.75, 8.4)          # the windmill's sail hub (Blender), shared by vale_windmill and its sails


def windmill(kit):
    """A tower windmill: an octagonal tower tapering from 3.2 m across at the foot to 2.5 m at the top — a proud stone
    course to 1.0 m, plaster to 8.0 m — under a boat-shaped cap (to ~9.6 m) with the windshaft's stub at the front, a
    door and two small windows, the tail pole and its two struts down the back (+Y). The sails are vale_windmill_sails
    (placed at the same point and yaw)."""
    g = K.Geo()
    c8 = math.cos(math.pi / 8)
    slope = (1.6 - 1.25) / 8.0

    def ap(z):                                                       # the plaster faces' distance from the axis
        return 1.6 - slope * z
    tilt = math.degrees(math.atan(slope))
    K.lathe(g, [((ap(0) + 0.05) / c8, 0.0), ((ap(1.0) + 0.05) / c8, 1.0), (ap(1.0) / c8, 1.0), (ap(8.0) / c8, 8.0)], 8,
            lambda b, k: BONE if b == 2 else STONE, lambda b, k: (0.44, 0.5, 0.52)[b], smooth=0, cap0=False,
            cap1=False, phase=math.pi / 8)
    cap = []
    for (z, ax, ay) in ((7.95, 1.45, 1.6), (8.85, 1.08, 1.45)):
        for k in range(10):
            a = 2 * math.pi * k / 10
            cap.append((ax * math.cos(a), 0.05 + ay * math.sin(a), z))
    cap += [(0.0, -1.05, 9.6), (0.0, 1.15, 9.6)]
    K.hull(g, cap, DWOOD, lambda c, n: 0.36 if n.z < 0.3 else 0.44)                               # the cap
    K.tube(g, (0.0, -1.35, MILL_HUB[2]), (0.0, -1.66, MILL_HUB[2]), 0.11, DWOOD, n=6, var=0.38, cap0=False, cap1=False)
    town_door(g, T(0.0, -(ap(0) + 0.05), 0.0) @ Rx(-tilt), w=0.9, h=1.95, back=0.12)
    town_window(g, T(0.0, -ap(4.6), 4.6) @ Rx(-tilt), w=0.55, h=0.75)
    town_window(g, on_face('-x', -ap(3.0), 0.0, 3.0) @ Rx(-tilt), w=0.55, h=0.75)
    top, foot = Vector((0.0, 1.4, 8.3)), Vector((0.0, 2.75, 0.75))                                  # the tail pole
    K.tube(g, tuple(top), tuple(foot), 0.085, DWOOD, n=4, var=0.4, cap0=False)
    mid = top.lerp(foot, 0.6)
    for sx in (-1, 1):
        K.tube(g, (sx * 1.0, 1.2, 8.05), tuple(mid), 0.05, DWOOD, n=3, var=0.42, cap0=False, cap1=False)
    p = kit.add('vale_windmill', g, budget=230, sheet={'az': 32, 'el': 16})
    p.info['footprint'] = [3.6, 3.6]
    p.info['door'] = [0.0, 0.0, round(ap(0) + 0.05, 3)]               # the threshold's centre, game (x, y, z)
    return p


def windmill_sails(kit):
    """The windmill's four sails, in vale_windmill's own frame (placed at the same point and yaw): round the hub at
    MILL_HUB in the vertical XZ plane, turning about the Blender Y axis (game z). Each sail a stock (a crossed pair of
    flat bars to 5.4 m), a cloth panel 1.0 m wide from r 0.8 to r 5.2 on one side of it, three sail bars and an edge
    lath across it; the four are identical copies a quarter-turn apart, with a square boss on the hub, so the piece's
    bounds are centred on the hub (the game turns it about its bounds' centre)."""
    g = K.Geo()
    arm = K.Geo()
    face_to(arm, [(0.2, -0.06, -0.07), (5.4, -0.06, -0.07), (5.4, -0.06, 0.07), (0.2, -0.06, 0.07)], DWOOD, 0.4,
            (0, -1, 0))                                                                      # the stock: front
    face_to(arm, [(0.2, -0.06, 0.0), (5.4, -0.06, 0.0), (5.4, 0.06, 0.0), (0.2, 0.06, 0.0)], DWOOD, 0.34, (0, 0, 1))
    face_to(arm, [(0.8, -0.02, 0.08), (5.2, -0.02, 0.08), (5.2, -0.02, 1.08), (0.8, -0.02, 1.08)], BONE, 0.55,
            (0, -1, 0))                                                                      # the cloth
    for x in (1.9, 3.0, 4.1):
        face_to(arm, [(x - 0.03, -0.045, 0.07), (x + 0.03, -0.045, 0.07), (x + 0.03, -0.045, 1.12),
                      (x - 0.03, -0.045, 1.12)], DWOOD, 0.4, (0, -1, 0))                    # the sail bars
    face_to(arm, [(0.8, -0.045, 1.08), (5.2, -0.045, 1.08), (5.2, -0.045, 1.14), (0.8, -0.045, 1.14)], DWOOD, 0.42,
            (0, -1, 0))                                                                      # the edge lath
    hub = T(*MILL_HUB)
    for k in range(4):
        g.extend(arm, hub @ Ry(90.0 * k))
    hx, hy, hz = MILL_HUB
    K.box(g, (hx - 0.3, hy - 0.17, hz - 0.3), (hx + 0.3, hy + 0.13, hz + 0.3), DWOOD, 0.36)       # the boss
    p = kit.add('vale_windmill_sails', g, budget=80, bake={'ground': None}, sheet={'az': 20, 'el': 10})
    p.info['doubleSided'] = True
    p.info['no_collider'] = True
    return p


def mill_wheel(kit):
    """vale_watermill's overshot wheel as its own piece, in the watermill's own frame (placed at the same point and
    yaw) so the game can turn it about the x axis: the same ten paddle-ring quads (both faces), ten paddle cards and
    two spokes that the watermill had, centred on the hub (x 5.4, z 2.6) — its bounds are symmetric about it. The
    axle stays in vale_watermill. 92 tris: the wheel as it was (the spec's 80 undercounted it)."""
    g = K.Geo()
    wx, cz, r0, r1 = 5.4, 2.6, 2.2, 2.5
    for k in range(10):
        a0, a1 = 2 * math.pi * k / 10, 2 * math.pi * (k + 1) / 10
        q = [(r0 * math.cos(a0), cz + r0 * math.sin(a0)), (r1 * math.cos(a0), cz + r1 * math.sin(a0)),
             (r1 * math.cos(a1), cz + r1 * math.sin(a1)), (r0 * math.cos(a1), cz + r0 * math.sin(a1))]
        g.pf([(wx + 0.03, y, z) for y, z in q], DWOOD, 0.46)
        g.pf([(wx - 0.03, y, z) for y, z in reversed(q)], DWOOD, 0.4)
        am = (a0 + a1) / 2
        ca, sa = math.cos(am), math.sin(am)
        card(g, [(wx - 0.32, 2.1 * ca, cz + 2.1 * sa), (wx + 0.32, 2.1 * ca, cz + 2.1 * sa),
                 (wx + 0.32, 2.9 * ca, cz + 2.9 * sa), (wx - 0.32, 2.9 * ca, cz + 2.9 * sa)], WOOD, 0.5)
    for a in (0.0, 90.0):
        c, s = math.cos(math.radians(a)) * r0, math.sin(math.radians(a)) * r0
        K.tube(g, (wx, -c, cz - s), (wx, c, cz + s), 0.06, DWOOD, n=3, var=0.42, cap0=False, cap1=False)
    p = kit.add('vale_mill_wheel', g, budget=92, bake={'ground': None}, sheet={'az': 70, 'el': 14})
    p.info['no_collider'] = True
    return p


def beacon(kit):
    """A beacon tower: a round tapered stone tower of ten faces, 2.8 m across at the foot, corbelled out under a
    crenellated parapet (five merlons) to 6.5 m, an iron fire basket on a post above the platform holding a fire at
    ~7.2 m, one arrow slit on the front."""
    rng = R('vale_beacon')
    g = K.Geo()
    n, ro, ri, z0, zf = 10, 1.32, 1.08, 5.78, 5.85
    K.lathe(g, [(1.4, 0.0), (1.15, 5.6), (ro, z0)], n, STONE, lambda b, k: (0.46, 0.38)[b], smooth=0, cap0=False,
            cap1=False)
    tops = [6.5 if k % 2 == 0 else 6.12 for k in range(n)]

    def ring(r, k, z):
        a = 2 * math.pi * k / n
        return (r * math.cos(a), r * math.sin(a), z)
    for k in range(n):
        k2 = (k + 1) % n
        am = 2 * math.pi * (k + 0.5) / n
        out = (math.cos(am), math.sin(am), 0.0)
        zt = tops[k]
        v = 0.48 + jit(rng, 0.03)
        face_to(g, [ring(ro, k, z0), ring(ro, k2, z0), ring(ro, k2, zt), ring(ro, k, zt)], STONE, v, out)
        face_to(g, [ring(ri, k, zf), ring(ri, k2, zf), ring(ri, k2, zt), ring(ri, k, zt)], STONE, v - 0.08,
                (-out[0], -out[1], 0.0))
        face_to(g, [ring(ro, k, zt), ring(ro, k2, zt), ring(ri, k2, zt), ring(ri, k, zt)], STONE, v + 0.06, (0, 0, 1))
        zn = tops[k2]
        a2 = 2 * math.pi * k2 / n
        tan = (-math.sin(a2), math.cos(a2), 0.0)                    # toward the next merlon or gap
        lo, hi = min(zt, zn), max(zt, zn)
        face_to(g, [ring(ro, k2, lo), ring(ri, k2, lo), ring(ri, k2, hi), ring(ro, k2, hi)], STONE, v - 0.04,
                tan if zt > zn else (-tan[0], -tan[1], 0.0))
    K.disc(g, ri, n, STONE, z=zf, var=0.34)                                                     # the platform
    slope = (1.4 - 1.15) * math.cos(math.pi / n) / 5.6
    zs = 2.6
    slit(g, T(0.0, -(1.4 - (1.4 - 1.15) * zs / 5.6) * math.cos(math.pi / n), zs) @ Rx(-math.degrees(math.atan(slope))),
         h=1.0)
    K.tube(g, (0, 0, zf), (0, 0, 6.52), 0.09, IRON, n=4, var=0.4, cap0=False, cap1=False)          # the basket's post
    K.lathe(g, [(0.2, 6.5), (0.62, 7.1)], 6, IRON, 0.42, smooth=0, cap0=False, cap1=False)          # the basket
    K.rock(g, rng, (0.0, 0.0, 7.05), (0.5, 0.5, 0.26), GLOW, n=6, var=0.5, flat=False)              # the fire
    K.rock(g, rng, (0.08, -0.05, 7.35), (0.3, 0.28, 0.32), GLOW, n=5, var=0.55, flat=False)
    p = kit.add('vale_beacon', g, budget=170, sheet={'az': 30, 'el': 16})
    kit.light(p, (0, 0, 7.3), 'fire')
    kit.fx(p, (0, 0, 7.5), 'glow')
    p.info['footprint'] = [3.0, 3.0]
    return p


def _lancet(g, m, w, h):
    """A tall pointed window seen from afar: a pale dressed surround and a glazed pane (lit at night) (6 tris)."""
    mk = g.mark()
    a, rim = w * 0.7, 0.16
    outer = [(-w / 2 - rim, -rim), (w / 2 + rim, -rim), (w / 2 + rim, h), (0.0, h + a + rim * 1.5), (-w / 2 - rim, h)]
    inner = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h), (0.0, h + a), (-w / 2, h)]
    g.pf([(x, -0.02, z) for x, z in outer], STONE, 0.42)
    K.glaze(g, g.pf([(x, -0.04, z) for x, z in inner], INK, 0.5))
    g.transform(m, mk)


def keep_towers(kit):
    """Gravehollow Keep on the skyline behind its gate (a backdrop standing ~18 m north of vale_keep_gate, its front
    (−Y) to the gate): three square towers of dark stone — the middle one 9 × 10 m under a steep slate pyramid to
    ~28 m, the flank towers 6.5 × 7.2 m to 22 m with corbelled, crenellated tops — joined by two curtain walls 14 m
    high with merlons along their fronts; tall glazed lancets (lit at night). ~32 m wide, ~10 m deep."""
    rng = R('vale_keep_towers')
    g = K.Geo()

    def merlon(x0, x1, y0, y1, z0, z1, skip=('-z',)):
        K.box(g, (x0, y0, z0), (x1, y1, z1), STONE, 0.32 + jit(rng, 0.02), skip=skip)
    # the middle tower
    K.box(g, (-4.5, -5.0, 0), (4.5, 5.0, 22.2), STONE, 0.3, skip=('-z', '+z'))
    K.box(g, (-4.8, -5.3, 22.2), (4.8, 5.3, 22.8), STONE, 0.27, skip=('+z',))
    pyramid(g, 0.0, 0.0, 4.95, 5.45, 22.8, 28.4, IRON, var=0.42, under=True)
    _lancet(g, T(0.0, -5.0, 8.0), 1.1, 3.2)
    _lancet(g, T(0.0, -5.0, 14.6), 1.0, 2.8)
    for side, at in (('-x', -4.5), ('+x', 4.5)):                                  # above the curtain walls
        _lancet(g, on_face(side, at, 0.0, 15.5), 1.0, 3.0)
    # the flank towers
    for sx in (-1, 1):
        cx = sx * 12.75
        K.box(g, (cx - 3.25, -3.6, 0), (cx + 3.25, 3.6, 20.2), STONE, 0.29 + jit(rng, 0.02), skip=('-z', '+z'))
        ox, oy, za, zb = 3.5, 3.85, 20.9, 22.0
        K.box(g, (cx - ox, -oy, 20.2), (cx + ox, oy, za), STONE, 0.26, skip=('-z',))
        for ex in (-1, 1):
            for ey in (-1, 1):
                xa, xb = sorted((cx + ex * ox, cx + ex * (ox - 1.1)))
                ya, yb = sorted((ey * oy, ey * (oy - 1.1)))
                merlon(xa, xb, ya, yb, za, zb)
        merlon(cx - 0.6, cx + 0.6, -oy, -oy + 0.5, za, zb)
        for ex in (-1, 1):
            xa, xb = sorted((cx + ex * ox, cx + ex * (ox - 0.5)))
            merlon(xa, xb, -0.6, 0.6, za, zb)
        _lancet(g, T(cx, -3.6, 10.5), 0.9, 2.6)
        _lancet(g, on_face('+x' if sx > 0 else '-x', sx * 16.0, 0.0, 13.5), 0.9, 2.6)
    # the curtain walls, merlons along their fronts
    for sx in (-1, 1):
        xa, xb = sorted((sx * 4.5, sx * 9.5))
        K.box(g, (xa, -1.5, 0), (xb, 1.2, 13.2), STONE, 0.28 + jit(rng, 0.02), skip=('-z', '-x', '+x'))
        bay = (xb - xa) / 3
        for i in range(3):
            xm = xa + bay * (i + 0.5)
            merlon(xm - 0.45, xm + 0.45, -1.5, -1.0, 13.2, 14.0, skip=('-z', '+y'))
    p = kit.add('vale_keep_towers', g, budget=320, sheet={'az': 24, 'el': 10})
    p.info['footprint'] = [32, 10]
    return p


# ====================================================================== the hook
def build(kit, ns):
    """Adds every W18-town piece to `kit`, in order; `ns` is build_kit_vale's globals() (its helpers)."""
    _bind(ns)
    for fn in (grass_short, grass_seed, flowers, fern, bracken, leaf_litter, needle_litter, roots, moss_stone, branch,
               oak_b, pine_b, ash_b, yew_b,
               crate_b, barrel_b, bean_rows, washing_line, woodshed, privy, hen_run, hedge,
               windmill, windmill_sails, mill_wheel, beacon, keep_towers):
        fn(kit)
