"""vale_make_pieces.py - W20-make (OW-69; the RPG review's R32, R5): the Vale kit's gathering pieces for the gold and glass
chains, imported by build_kit_vale.py (`vale_make_pieces.build(kit, globals())` at the end of build_vale). Built with
kit_lib.py's helpers in the kit's conventions (origin at the centre of the footprint on the ground, slots by kit_lib's
names: STONE 0 field stone, DSTONE 1 packed earth, ROPE 8 straw gold, BMETAL 9 bright metal, BRASS 10 sand, GLOW 11 glow).

  vale_rock_gold   a mineable rock (the Old Quarry's gold, Mining 40): the ore rock's shape with bigger, brighter flecks of
                   straw gold and a few bright-metal glints, so it reads apart from copper's sandy flecks
  vale_sand_heap   a low heap of pale sand on the mill pond's shore (Foraging 5), a scoop taken out of one side
"""
import math
import random
import zlib

from mathutils import Vector

import kit_lib as K
from kit_lib import STONE, DSTONE, ROPE, BMETAL, BRASS


def R(name):
    return random.Random(zlib.crc32(name.encode('utf-8')))


def jit(rng, a):
    return rng.uniform(-a, a)


def rock_gold(kit):
    """The ore rock (build_kit_vale.ore_rock's shape) with nine gold flecks, larger and higher than copper's, and three
    small bright-metal glints among them."""
    rng = R('vale_rock_gold')
    g = K.Geo()
    # A darker host rock (the variation low) so the gold reads against it.
    K.rock(g, rng, (0, 0, 0.36), (0.9, 0.75, 0.62), STONE, n=13, var=0.18)
    # Two rings of nuggets standing proud of the face, in the straw gold at its brightest.
    for i in range(12):
        a = math.radians(i * 30 + jit(rng, 10))
        r = 0.6 if i % 2 == 0 else 0.46
        c = (math.cos(a) * r, math.sin(a) * r * 0.86, (0.26 if i % 2 == 0 else 0.62) + rng.uniform(-0.06, 0.1))
        K.rock(g, rng, c, (0.2, 0.17, 0.14), ROPE, n=7, var=1.0, flat=False)
    for i in range(3):
        a = math.radians(i * 120 + 20 + jit(rng, 10))
        c = (math.cos(a) * 0.66, math.sin(a) * 0.58, 0.44 + rng.uniform(0.0, 0.18))
        K.rock(g, rng, c, (0.08, 0.07, 0.06), BMETAL, n=5, var=1.0, flat=False)
    p = kit.add('vale_rock_gold', g, budget=180, sheet={'az': 30, 'el': 22})
    p.info['node'] = True


def sand_heap(kit):
    """A low mound of sand about 1.6 m across, a darker damp skirt where it meets the shore, a scoop out of its south side."""
    rng = R('vale_sand_heap')
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.02), (0.85, 0.7, 0.26), BRASS, n=12, var=0.66, smooth=0)
    K.rock(g, rng, (0.12, 0.08, 0.12), (0.5, 0.42, 0.2), BRASS, n=9, var=0.74, smooth=0)
    # The damp skirt: three flat lumps of packed earth at the foot.
    for i in range(3):
        a = math.radians(i * 120 + 40 + jit(rng, 20))
        K.rock(g, rng, (math.cos(a) * 0.7, math.sin(a) * 0.6, -0.02), (0.32, 0.26, 0.06), DSTONE, n=6, var=0.42, flat=True)
    # The scoop: a little pile beside the hollow.
    K.rock(g, rng, (0.35, -0.62, 0.0), (0.16, 0.14, 0.09), BRASS, n=6, var=0.7, flat=False)
    p = kit.add('vale_sand_heap', g, budget=110, bake={'skip': True}, sheet={'az': 30, 'el': 24})
    p.info['node'] = True
    p.info['footprint'] = [1.8, 1.6]


def build(kit, ns=None):
    """Adds the W20-make pieces to `kit`, in order (`ns` unused: kept for the hook's shape)."""
    for fn in (rock_gold, sand_heap):
        fn(kit)
