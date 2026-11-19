"""vale_land_pieces.py — W17 · the land and the water (OW-62): the Vale kit's pieces for the ground's dressing, imported by
build_kit_vale.py (`vale_land_pieces.build(kit)` at the end of build_vale). Built with kit_lib.py's helpers in the kit's
conventions (origin at the centre of the footprint on the ground, the front toward Blender −Y = game +z, slots by
kit_lib's names: STONE 0 field stone, DSTONE 1 packed earth, WOOD 2 timber, DWOOD 3 bark, CLOTH1 6 leaf, CLOTH2 7 pine,
MOSS 12 grass, BONE 13 plaster/white).

  vale_reed_bed        W14/W37: a dense clump of reeds and cattails (the marsh's reed beds, the ponds' margins)
  vale_lily_pads       W14: a raft of lily pads with two flowers, laid on the water (Unity floats it at the level)
  vale_stepping_stone  W14: a flat-topped boulder for a ford's crossing
  vale_tor             W38: a stack of weathered granite slabs on a fell top
  vale_outcrop         W6: a rock outcrop on a ridge or a knoll
  vale_scree           W38: a fan of loose stones below a tor (no collider: it is walked over)
  vale_cairn           W38: the cairn on Greyfell's top
  vale_drystone_wall   W38: a 3 m length of dry-stone wall (runs along its local x), for the hill road's walls
  vale_pine_bent       W38: a wind-bent pine, its crown swept east
  vale_giant_trunk     W40: a giant's trunk with buttress roots, its crown far overhead (the west edge's old forest)
  vale_bridge_broken   W40: a broken stone-and-timber bridge, its origin on the near bank, its span along +x (half gone)
  vale_bridge_pier     W40: the far bank's pier stump with its broken beams
"""
import math
import random
import zlib

from mathutils import Matrix, Vector

import kit_lib as K
from kit_lib import STONE, DSTONE, WOOD, DWOOD, CLOTH1, CLOTH2, MOSS, BONE, ROPE


def R(name):
    return random.Random(zlib.crc32(name.encode('utf-8')))


def jit(rng, a):
    return rng.uniform(-a, a)


def reed_bed(kit):
    """Fourteen blades and four cattails in a clump about 2.2 m across, taller in the middle."""
    rng = R('vale_reed_bed')
    g = K.Geo()
    for i in range(16):
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform(0.0, 1.0)) * 1.05
        h = rng.uniform(0.95, 1.55) * (1.0 - 0.3 * r)
        c = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        side = Vector((-math.sin(a), math.cos(a), 0)) * rng.uniform(0.025, 0.04)
        lean = Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.05, 0.22)
        g.pf([tuple(c - side), tuple(c + side), tuple(c + lean + Vector((0, 0, h)))], MOSS, 0.32 + jit(rng, 0.12), smooth=0)
    for i in range(4):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.1, 0.7)
        c = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        h = rng.uniform(1.25, 1.6)
        K.tube(g, tuple(c), tuple(c + Vector((jit(rng, 0.06), jit(rng, 0.06), h - 0.2))), 0.012, MOSS, n=3, var=0.36, cap0=False, cap1=False)
        top = c + Vector((0, 0, h - 0.2))
        K.box(g, (top.x - 0.03, top.y - 0.03, top.z), (top.x + 0.03, top.y + 0.03, top.z + 0.2), DWOOD, 0.45, skip=('-z',))
    p = kit.add('vale_reed_bed', g, budget=110, bake={'skip': True}, sheet={'az': 30, 'el': 16})
    p.info['doubleSided'] = True
    p.info['footprint'] = [2.0, 2.0]


def lily_pads(kit):
    """Seven pads (each a disc with its notch) on the water's face and two white flowers."""
    rng = R('vale_lily_pads')
    g = K.Geo()
    spots = [(0.0, 0.0, 0.36), (0.62, 0.18, 0.28), (-0.5, 0.35, 0.3), (0.2, -0.62, 0.26), (-0.42, -0.45, 0.22),
             (0.95, -0.4, 0.2), (-0.1, 0.85, 0.24)]
    for i, (x, y, r) in enumerate(spots):
        notch = rng.uniform(0, 2 * math.pi)
        n = 8
        pts = [(x, y, 0.01)]
        for k in range(n + 1):
            a = notch + 0.35 + (2 * math.pi - 0.7) * k / n
            rr = r * (1 + jit(rng, 0.06))
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr, 0.01))
        for k in range(1, n + 1):
            g.pf([pts[0], pts[k], pts[k + 1]], CLOTH1, 0.42 + jit(rng, 0.1), smooth=0)
    for (x, y) in ((0.62, 0.18), (-0.42, -0.45)):
        for k in range(5):
            a = 2 * math.pi * k / 5
            tip = (x + math.cos(a) * 0.1, y + math.sin(a) * 0.1, 0.09)
            g.pf([(x + math.cos(a - 0.4) * 0.03, y + math.sin(a - 0.4) * 0.03, 0.02), (x + math.cos(a + 0.4) * 0.03, y + math.sin(a + 0.4) * 0.03, 0.02), tip], BONE, 0.6)
    p = kit.add('vale_lily_pads', g, budget=90, bake={'skip': True}, sheet={'az': 30, 'el': 40})
    p.info['footprint'] = [2.2, 2.0]


def stepping_stone(kit):
    rng = R('vale_stepping_stone')
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.28), (0.42, 0.36, 0.3), STONE, n=10, var=0.44)
    for vi in range(len(g.V)):
        v = g.V[vi]
        if v.z > 0.46:
            g.V[vi] = Vector((v.x, v.y, 0.52 + jit(rng, 0.02)))   # a walkable flat top
    kit.add('vale_stepping_stone', g, budget=30, sheet={'az': 30, 'el': 26}).info['footprint'] = [0.8, 0.7]


def tor(kit):
    """Four weathered slabs stacked a little askew, two boulders at the foot."""
    rng = R('vale_tor')
    g = K.Geo()
    z = 0.0
    for i, (hx, hy, hz) in enumerate(((1.7, 1.3, 0.55), (1.35, 1.2, 0.42), (1.3, 0.85, 0.5), (0.8, 0.75, 0.4))):
        ox, oy = jit(rng, 0.45), jit(rng, 0.3)
        mk = g.mark()
        K.cbox(g, (-hx + ox, -hy + oy, z), (hx + ox, hy + oy, z + hz * 2), 0.22, STONE, 0.4 + 0.06 * i)
        a = math.radians(jit(rng, 22))
        g.transform(Matrix.Translation((ox, oy, z)) @ Matrix.Rotation(a, 4, 'Z') @ Matrix.Translation((-ox, -oy, -z)), mk)
        z += hz * 2 - 0.05
    K.rock(g, rng, (1.9, -0.9, 0.3), (0.65, 0.5, 0.4), STONE, n=9, var=0.48)
    K.rock(g, rng, (-1.7, 1.0, 0.25), (0.5, 0.45, 0.32), STONE, n=8, var=0.52)
    p = kit.add('vale_tor', g, budget=220, sheet={'az': 30, 'el': 16})
    p.info['footprint'] = [4.4, 3.4]


def outcrop(kit):
    rng = R('vale_outcrop')
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.9), (1.4, 1.0, 1.25), STONE, n=14, var=0.45)
    K.rock(g, rng, (1.25, 0.35, 0.55), (0.75, 0.7, 0.75), STONE, n=10, var=0.52)
    K.rock(g, rng, (-1.0, -0.55, 0.4), (0.7, 0.55, 0.5), STONE, n=9, var=0.4)
    p = kit.add('vale_outcrop', g, budget=110, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [3.6, 2.4]


def scree(kit):
    rng = R('vale_scree')
    g = K.Geo()
    for i in range(12):
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform(0, 1)) * 1.4
        s = rng.uniform(0.18, 0.36)
        K.rock(g, rng, (math.cos(a) * r, math.sin(a) * r * 0.7, s * 0.4), (s, s * 0.8, s * 0.55), STONE, n=6, var=0.38 + jit(rng, 0.12))
    p = kit.add('vale_scree', g, budget=110, bake={'skip': True}, sheet={'az': 30, 'el': 34})
    p.info['footprint'] = [2.6, 1.8]


def cairn(kit):
    """Rings of stones, each smaller and higher, a flat capstone on top: 2.2 m."""
    rng = R('vale_cairn')
    g = K.Geo()
    rings = ((0.0, 0.95, 7, 0.32), (0.45, 0.75, 6, 0.28), (0.85, 0.55, 5, 0.25), (1.2, 0.35, 4, 0.22), (1.5, 0.15, 2, 0.2))
    for z, r, n, s in rings:
        ph = rng.uniform(0, 1)
        for k in range(n):
            a = 2 * math.pi * (k + ph) / n
            K.rock(g, rng, (math.cos(a) * r, math.sin(a) * r, z + s * 0.7), (s * 1.15, s, s * 0.8), STONE, n=6, var=0.36 + jit(rng, 0.14))
    K.rock(g, rng, (0, 0, 1.95), (0.3, 0.26, 0.16), STONE, n=7, var=0.55)
    p = kit.add('vale_cairn', g, budget=230, sheet={'az': 30, 'el': 14})
    p.info['footprint'] = [2.2, 2.2]


def drystone_wall(kit):
    """A 3 m length of dry-stone wall along x: a battered core 0.9 m high and capstones set on edge."""
    rng = R('vale_drystone_wall')
    g = K.Geo()
    L, d0, d1, h = 1.5, 0.3, 0.18, 0.72
    # a dark hearting inside (the gaps between the stones read as shadow), then the stones course by course
    pts = [(-L, -d0 + 0.14, 0), (L, -d0 + 0.14, 0), (L, d0 - 0.14, 0), (-L, d0 - 0.14, 0), (-L, -d1 + 0.1, h), (L, -d1 + 0.1, h), (L, d1 - 0.1, h), (-L, d1 - 0.1, h)]
    v = [g.v(p) for p in pts]
    for idx in ((0, 1, 5, 4), (2, 3, 7, 6), (4, 5, 6, 7), (1, 2, 6, 5), (3, 0, 4, 7)):
        g.f([v[i] for i in idx], STONE, 0.1)
    for row, (z, sz, depth) in enumerate(((0.12, 0.13, d0), (0.34, 0.12, (d0 + d1) / 2), (0.55, 0.11, d1))):
        x = -L + (0.12 if row % 2 == 0 else 0.26)
        while x < L - 0.12:
            w = rng.uniform(0.48, 0.72)
            w = min(w, L - x)
            K.rock(g, rng, (x + w / 2, jit(rng, 0.02), z), (w * 0.55, depth * 1.2, sz * 1.1), STONE, n=7, var=0.36 + jit(rng, 0.14))
            x += w + 0.02
    x = -L + 0.08
    while x < L - 0.1:   # the capstones on edge
        w = rng.uniform(0.26, 0.36)
        K.rock(g, rng, (x + w / 2, jit(rng, 0.02), h + 0.1), (w * 0.55, 0.17, 0.15), STONE, n=5, var=0.32 + jit(rng, 0.1))
        x += w + 0.03
    p = kit.add('vale_drystone_wall', g, budget=260, sheet={'az': 30, 'el': 20})
    p.info['footprint'] = [3.0, 0.7]


def pine_bent(kit):
    """A wind-bent fell pine: the trunk leans and kinks east (+x), three flattened tiers swept the same way."""
    rng = R('vale_pine_bent')
    g = K.Geo()
    K.tube(g, (0, 0, 0), (0.45, 0.0, 1.6), 0.15, DWOOD, r1=0.11, n=6, var=0.42, cap0=False)
    K.tube(g, (0.45, 0.0, 1.6), (1.2, 0.1, 3.0), 0.11, DWOOD, r1=0.07, n=5, var=0.4, cap0=False)
    for i, (z, r, sweep) in enumerate(((1.9, 1.25, 0.9), (2.55, 1.0, 1.15), (3.15, 0.7, 1.35))):
        mk = g.mark()
        prof = [(0.0, -0.12), (r, 0.0), (0.0, 0.42)]
        K.lathe(g, prof, 7, CLOTH2, lambda b, k, i=i: 0.38 + 0.08 * i + jit(rng, 0.06), smooth=0, cap0=False, cap1=False, phase=rng.uniform(0, 1))
        for vi in range(mk[0], len(g.V)):
            v = g.V[vi]
            # squash across the wind, stretch downwind: the crown streams east
            nx = v.x * 1.35 + (abs(v.y) * 0.15) + sweep * 0.4
            g.V[vi] = Vector((nx + 0.4 + 0.25 * i, v.y * 0.62, v.z * 0.8 + z - (0.1 if v.x < 0 else 0.0)))
    p = kit.add('vale_pine_bent', g, budget=130, sheet={'az': 20, 'el': 12})
    p.info['canopy'] = 3.6
    p.info['footprint'] = [1.0, 1.0]


def giant_trunk(kit):
    """A giant's trunk 2.6 m through with five buttress roots, two great limbs and a crown at 13–19 m."""
    rng = R('vale_giant_trunk')
    g = K.Geo()
    K.tube(g, (0, 0, -0.3), (0.2, 0.1, 13.5), 1.3, DWOOD, r1=0.85, n=9, var=0.38, cap0=False)
    for k in range(5):
        a = 2 * math.pi * k / 5 + jit(rng, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        base = d * 2.6
        top = d * 0.8 + Vector((0, 0, 2.4))
        side = Vector((-d.y, d.x, 0)) * 0.22
        pts = [tuple(d * 0.9 - side + Vector((0, 0, -0.1))), tuple(base - side * 0.5 + Vector((0, 0, -0.1))), tuple(base + side * 0.5 + Vector((0, 0, -0.1))), tuple(d * 0.9 + side + Vector((0, 0, -0.1)))]
        tp = [tuple(top - side * 0.6), tuple(top + side * 0.6)]
        v = [g.v(p) for p in pts + tp]
        g.f((v[0], v[1], v[4]), DWOOD, 0.36)
        g.f((v[1], v[2], v[5], v[4]), DWOOD, 0.34)
        g.f((v[2], v[3], v[5]), DWOOD, 0.36)
    for a, z in ((40, 10.5), (220, 11.8)):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        K.tube(g, tuple(d * 0.5 + Vector((0, 0, z))), tuple(d * 4.2 + Vector((0, 0, z + 3.0))), 0.45, DWOOD, r1=0.25, n=6, var=0.4, cap0=False)
    blobs = [((0.0, 0.0, 16.5), (5.0, 4.6, 2.8), 12)]
    for a, r, z in ((30, 3.8, 14.6), (150, 3.6, 15.0), (270, 3.9, 14.4), (90, 2.4, 18.0)):
        blobs.append(((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, z), (3.0, 2.8, 1.9), 9))
    for i, (c, sz, n) in enumerate(blobs):
        K.rock(g, rng, c, sz, CLOTH1, n=n, var=0.32 + 0.06 * (i % 3), flat=False, smooth=0)
    p = kit.add('vale_giant_trunk', g, budget=260, sheet={'az': 30, 'el': 10})
    p.info['footprint'] = [3.4, 3.4]
    p.info['canopy'] = 19.0


def bridge_broken(kit):
    """The south river's old bridge: a stone abutment on the near bank (x −1.6…0.4), a timber span reaching out along +x
    over the water and broken off at about 4.5 m, two planks hanging; the stonework runs 3 m below its foot."""
    rng = R('vale_bridge_broken')
    g = K.Geo()
    K.box(g, (-1.6, -1.6, -3.0), (0.4, 1.6, 0.95), STONE, 0.42, skip=('-z',))
    K.box(g, (-1.75, -1.75, 0.95), (0.55, 1.75, 1.15), STONE, 0.5, skip=('-z',))
    for y in (-1.15, 1.15):
        K.box(g, (0.3, y - 0.14, 0.75), (4.6 if y < 0 else 3.4, y + 0.14, 0.98), DWOOD, 0.4)
    x = 0.4
    k = 0
    while x < 4.1:
        w = 0.34
        end = 1.3 if k % 3 != 2 else 0.9
        K.box(g, (x, -end, 0.98), (x + w - 0.04, end, 1.06), WOOD, 0.44 + jit(rng, 0.06))
        x += w
        k += 1
    for (px, ang) in ((4.35, 55), (3.6, 35)):
        mk = g.mark()
        K.box(g, (0.0, -0.6, -0.04), (1.4, 0.6, 0.04), WOOD, 0.38)
        g.transform(Matrix.Translation((px, 0.0, 1.02)) @ Matrix.Rotation(math.radians(ang), 4, 'Y'), mk)
    for y in (-1.25, 1.25):
        K.box(g, (0.5, y - 0.06, 1.06), (3.2 if y < 0 else 2.2, y + 0.06, 1.12), DWOOD, 0.4)
        K.box(g, (0.6, y - 0.06, 1.06), (0.72, y + 0.06, 1.95), DWOOD, 0.4)
        K.box(g, (0.5, y - 0.06, 1.85), (2.0 if y < 0 else 1.4, y + 0.06, 1.95), DWOOD, 0.42)
    p = kit.add('vale_bridge_broken', g, budget=300, sheet={'az': 35, 'el': 18})
    p.info['footprint'] = [6.2, 3.5]


def bridge_pier(kit):
    rng = R('vale_bridge_pier')
    g = K.Geo()
    K.box(g, (-1.0, -1.6, -3.0), (1.0, 1.6, 0.9), STONE, 0.4, skip=('-z',))
    K.rock(g, rng, (0.2, 0.5, 1.05), (0.55, 0.45, 0.3), STONE, n=8, var=0.5)
    for y in (-1.15, 1.15):
        mk = g.mark()
        K.box(g, (-1.8, y - 0.14, -0.12), (0.4, y + 0.14, 0.12), DWOOD, 0.36)
        g.transform(Matrix.Translation((0.0, 0.0, 1.0)) @ Matrix.Rotation(math.radians(-14 if y < 0 else -22), 4, 'Y'), mk)
    p = kit.add('vale_bridge_pier', g, budget=110, sheet={'az': 35, 'el': 18})
    p.info['footprint'] = [2.4, 3.4]


def build(kit):
    """Every W17-land piece, in the order the sheet shows them."""
    reed_bed(kit)
    lily_pads(kit)
    stepping_stone(kit)
    tor(kit)
    outcrop(kit)
    scree(kit)
    cairn(kit)
    drystone_wall(kit)
    pine_bent(kit)
    giant_trunk(kit)
    bridge_broken(kit)
    bridge_pier(kit)
