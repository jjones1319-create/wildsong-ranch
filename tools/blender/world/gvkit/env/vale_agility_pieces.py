"""vale_agility_pieces.py — W21-agility (OW-72): the Vale kit's pieces for the Agility courses and shortcuts, imported by
build_kit_vale.py (`vale_agility_pieces.build(kit)` at the end of build_vale). Built with kit_lib.py's helpers in the
kit's conventions (origin at the centre of the footprint on the ground, the front toward Blender −Y = game +z, slots by
kit_lib's names). Every piece is crossed along its own x (the generator turns it along the obstacle's way).

  vale_balance_beam    a squared beam on three trestles, its top at 0.5 m (the Ashbrook course)
  vale_log_bridge      a felled log laid over a brook, its top at 0.6 m; it rests on its two ends' ground (`span`)
  vale_climb_net       a rope net over an A-frame, the top rail at 2.6 m
  vale_crawl_pipe      a hollow log lying on its side, crawled through
  vale_vault_wall      three logs stacked between stakes, 1 m high (the Thornwood's vault)
  vale_wall_ladder     a ladder up each face of the town wall (2 m thick, 5.4 m high) and a plank over its top
  vale_rope_swing      a frame of two posts and a beam with a knotted rope (stands in the water it swings over)
  vale_stile           steps up and over a fence on both sides, and a post to hold (the fence itself is the land's)
  vale_palisade_gap    two broken stakes leaning into a gap in a palisade, a cut rope (squeezed through)
  vale_hop_stone       a flat-topped stone pillar, its origin at its top: stood `hopTop` above dry ground or
                       `waterTop` above the water (Unity's AgilityPieces.Rest), a jump's stepping place
  vale_course_flag     a course's start or end: a post with a pennant (slot 7: a prop's `cloth` repaints it)
"""
import math
import random
import zlib

from mathutils import Matrix, Vector

import kit_lib as K
from kit_lib import STONE, DSTONE, WOOD, DWOOD, IRON, CLOTH2, ROPE


def R(name):
    return random.Random(zlib.crc32(name.encode('utf-8')))


def jit(rng, a):
    return rng.uniform(-a, a)


def bar(g, p0, p1, w, slot, var=0.4):
    """A square bar (a rope strand, a rung) from p0 to p1, `w` across (12 triangles)."""
    mt, ln = K.orient(p0, p1)
    mk = K.box(g, (-w / 2, -w / 2, 0.0), (w / 2, w / 2, ln), slot, var, skip=('-z', '+z'))
    g.transform(mt, mk)


def balance_beam(kit):
    rng = R('vale_balance_beam')
    g = K.Geo()
    K.box(g, (-2.4, -0.11, 0.38), (2.4, 0.11, 0.5), WOOD, 0.5, skip=())
    for x in (-2.1, 0.0, 2.1):
        for s in (-1, 1):
            K.tube(g, (x, s * 0.32, 0.0), (x + jit(rng, 0.02), s * 0.06, 0.4), 0.05, DWOOD, n=4, var=0.38, cap0=False)
        K.box(g, (x - 0.04, -0.26, 0.16), (x + 0.04, 0.26, 0.22), DWOOD, 0.36)
    p = kit.add('vale_balance_beam', g, budget=200, sheet={'az': 30, 'el': 20})
    p.info['footprint'] = [4.8, 0.7]


def log_bridge(kit):
    """A felled log 7.4 m long lying along x on its two ends' ground, its top worn flat at 0.6 m, two lopped branches."""
    rng = R('vale_log_bridge')
    g = K.Geo()
    K.tube(g, (-3.7, 0.0, 0.3), (3.7, 0.0, 0.27), 0.3, DWOOD, r1=0.27, n=8, var=0.36, cap0=True, cap1=True)
    K.box(g, (-3.55, -0.12, 0.53), (3.55, 0.12, 0.6), WOOD, 0.46, skip=('-z',))   # the worn top
    for x, a in ((-1.6, 40), (1.2, -55)):
        d = Vector((math.cos(math.radians(a)) * 0.2, math.sin(math.radians(a)), 0.25)).normalized()
        K.tube(g, (x, 0.0, 0.32), tuple(Vector((x, 0.0, 0.32)) + d * 0.55), 0.06, DWOOD, r1=0.04, n=5, var=0.34, cap0=False)
    for k in range(3):   # the root plate's stubs at the thick end
        a = 2 * math.pi * k / 3 + jit(rng, 0.3)
        K.tube(g, (-3.6, 0.0, 0.3), (-3.95, math.cos(a) * 0.4, 0.3 + math.sin(a) * 0.35), 0.08, DWOOD, r1=0.04, n=4, var=0.32, cap0=False)
    p = kit.add('vale_log_bridge', g, budget=200, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = [7.4, 0.8]
    p.info['span'] = 3.7


def climb_net(kit):
    """Two A-frames 3 m apart joined by a top rail at 2.6 m, a rope net down each slope to a foot rail."""
    g = K.Geo()
    top = 2.6
    for y in (-1.5, 1.5):
        for s in (-1, 1):
            K.tube(g, (s * 1.3, y, 0.0), (s * 0.05, y, top + 0.1), 0.07, DWOOD, n=5, var=0.38, cap0=False)
    K.tube(g, (0.0, -1.65, top), (0.0, 1.65, top), 0.07, WOOD, n=6, var=0.44)
    for s in (-1, 1):
        K.tube(g, (s * 1.25, -1.55, 0.15), (s * 1.25, 1.55, 0.15), 0.05, WOOD, n=5, var=0.42)
        # the net: six strands down the slope, five across
        for k in range(6):
            y = -1.25 + k * 0.5
            bar(g, (s * 1.22, y, 0.18), (s * 0.06, y, top - 0.02), 0.025, ROPE, 0.42)
        for k in range(1, 6):
            u = k / 6
            x = s * (1.22 - (1.22 - 0.06) * u)
            z = 0.18 + (top - 0.2) * u
            bar(g, (x, -1.3, z), (x, 1.3, z), 0.025, ROPE, 0.42)
    p = kit.add('vale_climb_net', g, budget=420, sheet={'az': 30, 'el': 16})
    p.info['footprint'] = [2.6, 3.2]


def crawl_pipe(kit):
    """A hollow log 3.2 m long on its side along x: the bark outside, the pale bore inside (0.9 m), rims at the ends."""
    g = K.Geo()
    n, ro, ri, cz, L = 10, 0.55, 0.45, 0.52, 1.6
    ring = lambda r, x: [g.v((x, math.cos(2 * math.pi * k / n + 0.3) * r, cz + math.sin(2 * math.pi * k / n + 0.3) * r)) for k in range(n)]
    o0, o1, i0, i1 = ring(ro, -L), ring(ro, L), ring(ri, -L), ring(ri, L)
    for k in range(n):
        k2 = (k + 1) % n
        g.f((o0[k], o0[k2], o1[k2], o1[k]), DWOOD, 0.36 + 0.04 * (k % 3), 40.0)   # bark
        g.f((i0[k], i1[k], i1[k2], i0[k2]), WOOD, 0.3, 40.0)                       # the bore
        g.f((o0[k2], o0[k], i0[k], i0[k2]), WOOD, 0.52)                            # the rims
        g.f((o1[k], o1[k2], i1[k2], i1[k]), WOOD, 0.52)
    for x in (-1.2, 1.2):   # chocks so it does not roll
        K.box(g, (x - 0.12, -0.62, 0.0), (x + 0.12, -0.4, 0.16), DWOOD, 0.34)
        K.box(g, (x - 0.12, 0.4, 0.0), (x + 0.12, 0.62, 0.16), DWOOD, 0.34)
    p = kit.add('vale_crawl_pipe', g, budget=160, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [3.2, 1.3]


def vault_wall(kit):
    """Three logs stacked between two pairs of stakes, across the way (along y), the top at 1 m."""
    rng = R('vale_vault_wall')
    g = K.Geo()
    for i, z in enumerate((0.17, 0.5, 0.83)):
        K.tube(g, (jit(rng, 0.03), -1.3, z), (jit(rng, 0.03), 1.3, z), 0.17, DWOOD, r1=0.15 + jit(rng, 0.02), n=6, var=0.36 + 0.04 * i)
    for y in (-1.05, 1.05):
        for s in (-1, 1):
            K.tube(g, (s * 0.22, y, 0.0), (s * 0.2, y, 1.15), 0.05, WOOD, n=4, var=0.42, cap0=False)
    p = kit.add('vale_vault_wall', g, budget=140, sheet={'az': 40, 'el': 18})
    p.info['footprint'] = [0.6, 2.6]


def wall_ladder(kit):
    """A ladder up each face of a wall 2 m thick and 5.4 m high (its feet 1.8 m out), a plank across the top between them."""
    g = K.Geo()
    top, face, foot = 5.45, 1.02, 2.8
    for s in (-1, 1):
        for y in (-0.24, 0.24):
            K.box(g, (-0.04, y - 0.04, 0.0), (0.04, y + 0.04, math.hypot(foot - face, top)), WOOD, 0.44, skip=('-z',),
                  m=Matrix.Translation((s * foot, 0, 0)) @ Matrix.Rotation(-s * math.atan2(foot - face, top), 4, 'Y'))
        n = 14
        for k in range(1, n):
            u = k / n
            x = s * (foot - (foot - face) * u)
            bar(g, (x, -0.26, top * u), (x, 0.26, top * u), 0.035, DWOOD, 0.4)
    K.box(g, (-face - 0.1, -0.28, top), (face + 0.1, 0.28, top + 0.06), WOOD, 0.5)
    p = kit.add('vale_wall_ladder', g, budget=260, sheet={'az': 50, 'el': 14})
    p.info['footprint'] = [5.6, 0.7]


def rope_swing(kit):
    """Two posts either side of the way, a beam across them at 5.1 m, a knotted rope hanging to 1.6 m with a handle;
    the posts run 1.2 m below the ground (it stands in a brook's bed)."""
    g = K.Geo()
    for y in (-1.4, 1.4):
        K.tube(g, (0.0, y, -1.2), (0.0, y * 0.94, 5.25), 0.1, DWOOD, r1=0.08, n=6, var=0.38, cap0=False)
    K.box(g, (-0.09, -1.55, 5.0), (0.09, 1.55, 5.18), WOOD, 0.46)
    bar(g, (0.0, 0.0, 5.0), (0.0, 0.0, 1.62), 0.045, ROPE, 0.46)
    for z in (2.4, 3.3):
        K.box(g, (-0.06, -0.06, z - 0.05), (0.06, 0.06, z + 0.05), ROPE, 0.4)   # knots
    K.tube(g, (0.0, -0.3, 1.6), (0.0, 0.3, 1.6), 0.035, WOOD, n=5, var=0.5)
    p = kit.add('vale_rope_swing', g, budget=160, sheet={'az': 30, 'el': 14})
    p.info['footprint'] = [0.6, 3.0]


def stile(kit):
    """Two steps either side of a fence on the line x = 0 (a low one, a high one) and a post to hold."""
    g = K.Geo()
    for s in (-1, 1):
        for (x0, x1, h) in ((0.46, 0.8, 0.36), (0.12, 0.42, 0.72)):
            K.box(g, (s * x0 if s > 0 else s * x1, -0.34, h - 0.06), (s * x1 if s > 0 else s * x0, 0.34, h), WOOD, 0.48)
            for y in (-0.28, 0.28):
                xm = s * (x0 + x1) / 2
                K.box(g, (xm - 0.04, y - 0.04, 0.0), (xm + 0.04, y + 0.04, h - 0.06), DWOOD, 0.36, skip=('-z',))
    K.box(g, (-0.06, 0.38, 0.0), (0.06, 0.5, 1.45), DWOOD, 0.4, skip=('-z',))
    p = kit.add('vale_stile', g, budget=140, sheet={'az': 35, 'el': 18})
    p.info['footprint'] = [1.6, 1.0]


def palisade_gap(kit):
    """A gap in a palisade (along y): a pointed stake leaning in from each side, one broken short, and a cut rope."""
    rng = R('vale_palisade_gap')
    g = K.Geo()
    for (y0, y1, z1, broke) in ((-1.0, -0.38, 2.3, False), (1.0, 0.45, 1.45, True)):
        K.tube(g, (jit(rng, 0.04), y0, -0.1), (jit(rng, 0.06), y1, z1), 0.13, DWOOD, r1=0.11, n=6, var=0.38, cap1=broke)
        if not broke:
            K.tube(g, (0.0, y1, z1), (0.0, y1 + 0.08 * (1 if y1 > y0 else -1), z1 + 0.35), 0.11, DWOOD, r1=0.01, n=6, var=0.4, cap0=False)
    K.box(g, (-0.06, -0.08, 0.0), (0.06, 0.08, 0.35), DWOOD, 0.34, skip=('-z',))   # a stump in the gap's side
    bar(g, (0.15, -0.9, 1.7), (0.18, -0.55, 1.1), 0.03, ROPE, 0.44)
    bar(g, (0.15, 0.9, 1.25), (0.2, 0.62, 0.8), 0.03, ROPE, 0.44)
    p = kit.add('vale_palisade_gap', g, budget=150, sheet={'az': 60, 'el': 16})
    p.info['footprint'] = [0.5, 2.0]


def hop_stone(kit):
    """A flat-topped stone pillar 2.2 m long, its origin at its top (Unity stands it so the top is where the hop lands)."""
    rng = R('vale_hop_stone')
    g = K.Geo()
    prof = [(0.44, -2.2), (0.42, -0.5), (0.38, -0.08), (0.31, 0.0), (0.0, 0.0)]
    K.lathe(g, prof, 7, STONE, lambda i, k: 0.4 + jit(rng, 0.06) + 0.04 * i, smooth=30.0, cap0=False, cap1=False, phase=rng.uniform(0, 1))
    p = kit.add('vale_hop_stone', g, budget=60, sheet={'az': 30, 'el': 26, 'ground': -0.6})
    p.info['footprint'] = [0.9, 0.9]
    p.info['hopTop'] = 0.45
    p.info['waterTop'] = 0.2


def course_flag(kit):
    """A post with a pennant (slot 7, a prop's `cloth` repaints it) and an iron finial: a course's start or end."""
    g = K.Geo()
    K.tube(g, (0.0, 0.0, 0.0), (0.0, 0.0, 2.5), 0.05, DWOOD, r1=0.04, n=5, var=0.4, cap0=False)
    K.tube(g, (0.0, 0.0, 2.5), (0.0, 0.0, 2.62), 0.05, IRON, r1=0.0, n=5, var=0.5, cap0=False)
    g.pf([(0.04, 0.0, 2.45), (0.72, 0.0, 2.25), (0.04, 0.0, 2.02)], CLOTH2, 0.5)
    g.pf([(0.04, 0.0, 2.02), (0.72, 0.0, 2.25), (0.04, 0.0, 2.45)], CLOTH2, 0.46)
    K.box(g, (-0.18, -0.05, 0.0), (0.18, 0.05, 0.12), STONE, 0.4, skip=('-z',))
    p = kit.add('vale_course_flag', g, budget=60, sheet={'az': 30, 'el': 14})
    p.info['footprint'] = [0.8, 0.4]
    p.info['no_collider'] = True


def build(kit):
    """Every W21-agility piece, in the order the sheet shows them."""
    balance_beam(kit)
    log_bridge(kit)
    climb_net(kit)
    crawl_pipe(kit)
    vault_wall(kit)
    wall_ladder(kit)
    rope_swing(kit)
    stile(kit)
    palisade_gap(kit)
    hop_stone(kit)
    course_flag(kit)
