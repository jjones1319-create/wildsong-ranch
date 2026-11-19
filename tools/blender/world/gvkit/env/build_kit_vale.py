"""build_kit_vale.py — the Vale kit (`vale_`), Phase W2 (OPEN-WORLD-BRIEF §4; OW-8): the open world's outdoor pieces —
trees, rocks, grass and reeds, Ashbrook's buildings as whole pieces, the well, the smithy, the shrine, a market
stall, fences, a bridge, a camp fire, a hay bale, a scarecrow and a signpost (Phase W8 adds the walled town: the
bank, store, inn, chapel, Skill Hall, a tall house, a guardhouse, the palisade, wall towers and gate arch, a fountain,
lamp posts, barrels and crates, a hen coop, the mine's cart and mouth, bushes and the ground loot; then five shops, two
open-fronted workshop shells and the crafts' equipment: a workbench, a tanning rack, a spinning wheel, a fletching
bench, an alchemy table and a cooking range; Phase W10 the wilds for levels 5–20: a tent and a big camp tent, the
toll-house ruin, a broken wall, the drowned chapel, the troll cave's mouth, Gravehollow Keep's gate (the dungeon door),
the wyvern's nest, a steel-stone rock, an ash, a willow, a dead tree and bones, and fuller oak and pine canopies; every
window pane carries gv.A = 0 (K.glaze) so the night lights it) — built procedurally
with kit_lib.py (read its docstring for the conventions: pivots, the `gv` codes, the bake, the export), AO baked into
gv.B, exported rigid to client/public/models/env/kit_vale.glb + vale.json and to Unity as Resources/Env/kit_vale.fbx.

Run (Blender 5.2, headless; ~2 minutes, ~1 with --quick):
  blender -b -P tools/blender/env/build_kit_vale.py -- [--quick] [--no-bake] [--no-export] [--no-renders] [--no-fbx]
      [--only id,id] [--closeups id,id] [--no-night]
  --only renders just those pieces (kit_sheet_only.png) instead of the whole sheet; --closeups renders each named piece
  from four sides at 560 px (closeup_<id>.png); the night sheet (kit_night.png: every piece with window panes, the
  panes glowing — gv.A = 0, K.glaze — and the rest dimmed) is rendered unless --no-night.

Pivots: every piece's origin is at the centre of its footprint on the ground (z 0 in Blender); a building's front
(its door) faces Blender −Y = game +z, so a house placed with rotationY 0 opens to the south. Foliage pieces are
double-sided (the manifest says so); the ground itself is not a kit piece — Unity builds it from the land data.

Palette slots here: 0 field stone · 1 packed earth (the roads, the beds) · 2 timber · 3 bark / dark planks · 4 iron ·
5 ink (openings) · 6 leaf green (oaks, awnings' alt) · 7 pine green · 8 thatch and straw (#b8945a since the town
review of 2026-11-04) · 9 bright metal · 10 sand
(the pond's rim) · 11 glow (fire) · 12 grass (the ground, the tufts) · 13 plaster · 14 ember (emissive) · 15 water.
Foliage: leaves 6 (oak, ash, willow, bushes, berry bush, cabbages) and 7 (pine, one bush lobe); grass, reeds and herbs
12 (also the drowned chapel's algae). Slots 6 and 7 are also cloth in the town (awnings, banners, pennants). Window
panes: slot 5 with gv.A = 0; everything else A = 1.
"""
import math
import os
import random
import sys
import time
import zlib

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import kit_lib as K  # noqa: E402
from kit_lib import (STONE, DSTONE, WOOD, DWOOD, IRON, INK, CLOTH1, CLOTH2, ROPE, BMETAL, BRASS, GLOW, MOSS,  # noqa: E402
                     BONE, GEM, WATER)
from common import BUILD, RENDERS, REPO, args, log, save_blend  # noqa: E402
import vale_land_pieces  # noqa: E402  W17-land: the land's pieces (reed beds, lily pads, tors, walls, the cairn, the edges)
import vale_town_pieces  # noqa: E402  W18-town
import vale_make_pieces  # noqa: E402  W20-make (OW-69): the gold rock, the sand heap
import vale_agility_pieces  # noqa: E402  W21-agility: the courses' and shortcuts' pieces (OW-72)

ARGS = args()
QUICK = bool(ARGS.get('quick'))
NO_BAKE = bool(ARGS.get('no_bake'))
NO_EXPORT = bool(ARGS.get('no_export'))
NO_RENDERS = bool(ARGS.get('no_renders'))

OUT = os.path.join(RENDERS, 'env', 'vale')

# slot order: field stone · packed earth · timber · bark · iron · ink · leaf · pine · thatch · bright metal · sand ·
# glow · grass · plaster · ember · water
VALE = ['#8a8578', '#6b5538', '#9c7a4e', '#5a4330', '#4a4a52', '#1e1b1a', '#5f8a3c', '#2f5a3a',
        '#b8945a', '#b0b3ba', '#c7b07a', '#ffb347', '#6f9a44', '#e2d8c0', '#ff7a3a', '#4f8a96']
# Slot 8 (thatch and straw) was #c9a95a until the town review of 2026-11-04 ("banana yellow … reads as plastic"):
# now a dull straw gold-brown; the hay bales keep a lighter variation (G 0.6) so fresh hay stays brighter than a roof.
VALE_ABOUT = ('The Vale (OPEN-WORLD-BRIEF §4): a green and gold open country — grass #6F9A44, leaf #5F8A3C, pine '
              '#2F5A3A, packed-earth roads #6B5538, plaster #E2D8C0 and thatch #B8945A on the town, field stone '
              '#8A8578, sand #C7B07A at the pond, water #4F8A96. Slot 12 is the ground\'s grass; slot 1 the roads.')


def R(name):
    return random.Random(zlib.crc32(name.encode('utf-8')))


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def Rz(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def Rx(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'X')


def Ry(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Y')


def jit(rng, a):
    return rng.uniform(-a, a)


# ---------------------------------------------------------------------------------------------------- foliage
def pine(kit, mesh_id='vale_pine', h=5.2, rng_name=None):
    rng = R(rng_name or mesh_id)
    g = K.Geo()
    K.tube(g, (0, 0, 0), (0, 0, h * 0.3), 0.16, DWOOD, r1=0.11, n=6, var=0.42, cap0=False)
    # Phase W10 ("fuller canopies"): five tiers instead of four, broader at the foot (1.32 m against 1.05), 9 → 6
    # sides, each tier's rim ragged (±9 % out) and drooping up to 12 cm; the same slot (7) and the same height
    tiers = [(0.19, 0.48, 1.32, 9), (0.32, 0.61, 1.1, 9), (0.46, 0.74, 0.88, 8), (0.6, 0.87, 0.64, 7),
             (0.74, 1.0, 0.38, 6)]
    for i, (z0, z1, r, n) in enumerate(tiers):
        mk = g.mark()
        prof = [(0.0, z0 * h - 0.08), (r, z0 * h), (0.0, z1 * h)]
        K.lathe(g, prof, n, CLOTH2, lambda b, k, i=i, rng=rng: 0.36 + 0.1 * i + jit(rng, 0.08), smooth=0,
                cap0=False, cap1=False, phase=rng.uniform(0, 1))
        for vi in range(mk[0], len(g.V)):
            v = g.V[vi]
            if math.hypot(v.x, v.y) > 0.5 * r:
                k = 1 + jit(rng, 0.09)
                g.V[vi] = Vector((v.x * k, v.y * k, v.z - rng.uniform(0.0, 0.12)))
    p = kit.add(mesh_id, g, budget=110, sheet={'az': 30, 'el': 14})
    p.info['doubleSided'] = False
    p.info['canopy'] = h
    return p


def oak(kit):
    rng = R('vale_oak')
    g = K.Geo()
    K.tube(g, (0, 0, 0), (0.08, 0.05, 2.3), 0.26, DWOOD, r1=0.18, n=7, var=0.4, cap0=False)
    # three limbs toward the canopy
    for a in (20, 140, 260):
        d = Vector((math.cos(math.radians(a)) * 0.9, math.sin(math.radians(a)) * 0.9, 1.1))
        K.tube(g, (0.04, 0.02, 1.9), tuple(Vector((0.04, 0.02, 1.9)) + d), 0.1, DWOOD, r1=0.06, n=5, var=0.38, cap0=False)
    # Phase W10 ("fuller canopies"): eight overlapping leaf masses instead of five — a big round crown, a skirt of
    # four lobes round it, two above and one on top — ~5.2 m across instead of ~4.2, the same top (5.2 m), slot 6
    blobs = [((0.0, 0.0, 3.85), (1.8, 1.75, 1.3), 11)]
    for a, r, z, sz in ((30, 1.45, 3.3, (1.05, 1.0, 0.85)), (120, 1.5, 3.45, (1.0, 0.95, 0.85)),
                        (210, 1.45, 3.25, (1.05, 1.0, 0.85)), (300, 1.5, 3.4, (1.0, 0.95, 0.85)),
                        (75, 0.8, 4.45, (1.0, 0.95, 0.72)), (255, 0.85, 4.4, (1.0, 0.95, 0.72)),
                        (160, 0.3, 4.6, (0.85, 0.8, 0.6))):
        blobs.append(((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, z), sz, 9))
    for i, (c, sz, n) in enumerate(blobs):
        K.rock(g, rng, c, sz, CLOTH1, n=n, var=0.42 + 0.1 * (i % 3), flat=False, smooth=0)
    p = kit.add('vale_oak', g, budget=220, sheet={'az': 30, 'el': 14})
    p.info['canopy'] = 5.2
    return p


def rock_small(kit):
    rng = R('vale_rock_small')
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.14), (0.42, 0.34, 0.26), STONE, n=9, var=0.46)
    kit.add('vale_rock_small', g, budget=24, sheet={'az': 30, 'el': 24})


def rock_big(kit):
    rng = R('vale_rock_big')
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.42), (1.1, 0.85, 0.75), STONE, n=14, var=0.5)
    K.rock(g, rng, (0.7, -0.3, 0.18), (0.45, 0.4, 0.3), STONE, n=8, var=0.4)
    kit.add('vale_rock_big', g, budget=60, sheet={'az': 30, 'el': 22})


def grass_tuft(kit):
    rng = R('vale_grass_tuft')
    g = K.Geo()
    for i in range(6):
        a = math.radians(i * 60 + jit(rng, 18))
        lean = rng.uniform(0.08, 0.2)
        h = rng.uniform(0.26, 0.42)
        d = Vector((math.cos(a), math.sin(a), 0))
        base0 = d * 0.02 + Vector((-d.y, d.x, 0)) * 0.05
        base1 = d * 0.02 - Vector((-d.y, d.x, 0)) * 0.05
        tip = d * lean + Vector((0, 0, h))
        g.pf([tuple(base0), tuple(base1), tuple(tip)], MOSS, 0.5 + jit(rng, 0.16), smooth=0)
    p = kit.add('vale_grass_tuft', g, budget=8, bake={'skip': True}, sheet={'az': 30, 'el': 20})
    p.info['doubleSided'] = True


def reeds(kit):
    rng = R('vale_reeds')
    g = K.Geo()
    for i in range(8):
        a = math.radians(i * 45 + jit(rng, 20))
        r = rng.uniform(0.05, 0.22)
        h = rng.uniform(0.9, 1.4)
        c = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        side = Vector((-math.sin(a), math.cos(a), 0)) * 0.03
        g.pf([tuple(c - side), tuple(c + side), tuple(c + Vector((jit(rng, 0.1), jit(rng, 0.1), h)))], MOSS,
             0.3 + jit(rng, 0.1), smooth=0)
        if i % 3 == 0:
            top = c + Vector((0, 0, h))
            K.box(g, (top.x - 0.025, top.y - 0.025, h - 0.18), (top.x + 0.025, top.y + 0.025, h), DWOOD, 0.5)
    p = kit.add('vale_reeds', g, budget=50, bake={'skip': True}, sheet={'az': 30, 'el': 16})
    p.info['doubleSided'] = True


# ---------------------------------------------------------------------------------------------------- the town
def gable_roof(g, x0, x1, y0, y1, z_eave, z_ridge, slot, var=0.5, overhang=0.35, thick=0.14):
    """A thatch roof over a footprint: two slopes with an overhang, ridge along X, the undersides closed."""
    ox0, ox1 = x0 - overhang, x1 + overhang
    oy0, oy1 = y0 - overhang, y1 + overhang
    ym = (y0 + y1) / 2
    # front slope (−Y side) and back slope, each a thick slab
    for (ya, yb) in ((oy0, ym), (ym, oy1)):
        za = z_eave if ya == oy0 else z_ridge
        zb = z_ridge if ya == oy0 else z_eave
        top = [(ox0, ya, za), (ox1, ya, za), (ox1, yb, zb), (ox0, yb, zb)]
        bot = [(x, y, z - thick) for x, y, z in top]
        g.pf(top, slot, var, smooth=0)
        g.pf(list(reversed(bot)), slot, var - 0.12, smooth=0)
        # the eave edge and the gable ends
        g.pf([top[0], bot[0], bot[1], top[1]] if ya == oy0 else [top[3], top[2], bot[2], bot[3]], slot, var - 0.08)
        g.pf([top[0], top[3], bot[3], bot[0]], slot, var - 0.1)
        g.pf([top[1], bot[1], bot[2], top[2]], slot, var - 0.1)


def timber_walls(g, rng, w, d, h, plaster=BONE, beam=WOOD, sill=DSTONE, lean=False):
    """Plastered walls on a stone sill with corner posts and a top beam; the footprint is centred, −Y the front.
    lean=True (the Phase W8 shops) leaves out the faces nobody sees (bottoms, tops under the roof) and draws the studs
    as flat battens: 66 tris instead of 132, the same look."""
    hx, hy = w / 2, d / 2
    nz, nzz = (('-z',), ('-z', '+z')) if lean else ((), ())
    K.box(g, (-hx - 0.05, -hy - 0.05, 0), (hx + 0.05, hy + 0.05, 0.35), sill, 0.45, skip=nz)
    K.box(g, (-hx, -hy, 0.3), (hx, hy, h), plaster, 0.5 + jit(rng, 0.06), skip=nzz)
    for x in (-hx, hx):
        for y in (-hy, hy):
            K.box(g, (x - 0.12, y - 0.12, 0.3), (x + 0.12, y + 0.12, h + 0.02), beam, 0.42, skip=nzz)
    K.box(g, (-hx - 0.08, -hy - 0.08, h - 0.22), (hx + 0.08, hy + 0.08, h + 0.02), beam, 0.4, skip=nzz)
    # a brace on the front and the back
    for y in (-hy - 0.06, hy + 0.06):
        if lean:
            yf = -hy - 0.02 if y < 0 else hy + 0.02
            for xa, xb in ((-hx * 0.55, -hx * 0.55 + 0.12), (hx * 0.55 - 0.12, hx * 0.55)):
                q = [(xa, yf, 0.35), (xb, yf, 0.35), (xb, yf, h - 0.2), (xa, yf, h - 0.2)]
                g.pf(q if y < 0 else [(xb + xa - x, yy, z) for x, yy, z in q], beam, 0.44)
            continue
        K.box(g, (-hx * 0.55, y - 0.06, 0.35), (-hx * 0.55 + 0.12, y + 0.06, h - 0.2), beam, 0.44)
        K.box(g, (hx * 0.55 - 0.12, y - 0.06, 0.35), (hx * 0.55, y + 0.06, h - 0.2), beam, 0.44)


def door_and_windows(g, hx, hy, h, door_x=0.0, windows=(-1.8, 1.8), door_w=1.0, door_h=2.1, shutters=True):
    y = -hy
    # the door proud of the wall in dark planks, a frame in timber
    K.box(g, (door_x - door_w / 2 - 0.1, y - 0.12, 0.3), (door_x + door_w / 2 + 0.1, y + 0.02, door_h + 0.1), WOOD, 0.42)
    K.trim(g, since=K.box(g, (door_x - door_w / 2, y - 0.14, 0.32), (door_x + door_w / 2, y - 0.1, door_h), DWOOD,
                          0.38))                                                # W18-town: the leaf is trim
    K.box(g, (door_x + door_w / 2 - 0.2, y - 0.19, 1.05), (door_x + door_w / 2 - 0.12, y - 0.13, 1.13), IRON, 0.5)
    for wx in windows:
        K.box(g, (wx - 0.45, y - 0.1, 1.2), (wx + 0.45, y + 0.02, 2.0), WOOD, 0.42)
        K.glaze(g, since=K.box(g, (wx - 0.36, y - 0.12, 1.28), (wx + 0.36, y - 0.09, 1.92), INK, 0.5))   # the pane
        K.box(g, (wx - 0.03, y - 0.14, 1.28), (wx + 0.03, y - 0.09, 1.92), WOOD, 0.46)
        if shutters:                                                            # W18-town: open shutters
            town_shutters(g, 0.72, 0.64, T(wx, y, 1.28))


def house_small(kit, mesh_id='vale_house_small', roof=ROPE, roof_var=0.52, mirror=False):
    """The small cottage: timber and plaster, a door at x −1.2 and one window at +1.4 on the front, a thatch roof with
    its ridge along x, a chimney at the back right. Town review 2026-11-04: `mirror` builds its twin with the door on
    the other side (`vale_house_small_m`, the chimney then at the back left); `roof` / `roof_var` the roof's slot
    (`vale_house_small_b`: slate)."""
    rng = R(mesh_id)
    g = K.Geo()
    w, d, h = 6.0, 5.0, 2.7
    timber_walls(g, rng, w, d, h)
    door_and_windows(g, w / 2, d / 2, h, door_x=-1.2, windows=(1.4,))
    # the gable ends in plaster up to the ridge
    z_ridge = 4.6
    for x, sgn in ((-w / 2, -1), (w / 2, 1)):
        pts = [(x, -d / 2, h), (x, d / 2, h), (x, 0, z_ridge)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), BONE, 0.48, smooth=0)
    gable_roof(g, -w / 2, w / 2, -d / 2, d / 2, h - 0.05, z_ridge, roof, var=roof_var)
    K.box(g, (1.6, 0.6, h), (2.3, 1.3, z_ridge + 0.5), STONE, 0.45)   # the chimney
    if mirror:
        g.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
    p = kit.add(mesh_id, g, budget=260, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [w, d]
    p.info['door'] = [1.2 if mirror else -1.2, 0.0, d / 2]                 # the threshold's centre, game (x, y, z)
    p.info['chimney'] = [-1.95 if mirror else 1.95, z_ridge + 0.5, -0.95]   # the flue's top, game (x, y, z)
    return p


def house_long(kit):
    rng = R('vale_house_long')
    g = K.Geo()
    w, d, h = 9.0, 5.5, 3.0
    timber_walls(g, rng, w, d, h)
    door_and_windows(g, w / 2, d / 2, h, door_x=0.0, windows=(-2.9, 2.9), door_w=1.3, door_h=2.3)
    z_ridge = 5.2
    for x, sgn in ((-w / 2, -1), (w / 2, 1)):
        pts = [(x, -d / 2, h), (x, d / 2, h), (x, 0, z_ridge)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), BONE, 0.48, smooth=0)
    gable_roof(g, -w / 2, w / 2, -d / 2, d / 2, h - 0.05, z_ridge, ROPE, var=0.5)
    K.box(g, (-3.2, 0.8, h), (-2.5, 1.5, z_ridge + 0.4), STONE, 0.45)
    # a hanging sign on the front
    K.box(g, (2.2, -d / 2 - 0.9, 2.5), (2.3, -d / 2 + 0.02, 2.62), IRON, 0.5)
    K.box(g, (1.5, -d / 2 - 0.9, 1.85), (3.0, -d / 2 - 0.84, 2.5), DWOOD, 0.42)
    p = kit.add('vale_house_long', g, budget=320, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [w, d]


def barn(kit):
    rng = R('vale_barn')
    g = K.Geo()
    w, d, h = 8.0, 6.0, 3.4
    hx, hy = w / 2, d / 2
    K.box(g, (-hx - 0.05, -hy - 0.05, 0), (hx + 0.05, hy + 0.05, 0.3), DSTONE, 0.45)
    K.box(g, (-hx, -hy, 0.25), (hx, hy, h), DWOOD, 0.46 + jit(rng, 0.04))
    # plank lines as thin proud strips on the long sides
    for i in range(1, 7):
        z = 0.25 + i * 0.48
        for y in (-hy - 0.02, hy):
            K.box(g, (-hx, y, z), (hx, y + 0.02, z + 0.03), DWOOD, 0.34)
    # the big door opening, open: an ink slab set into the front
    K.box(g, (-1.6, -hy - 0.03, 0.25), (1.6, -hy + 0.05, 2.9), INK, 0.5)
    K.box(g, (-1.75, -hy - 0.1, 0.25), (-1.6, -hy + 0.02, 3.0), WOOD, 0.42)
    K.box(g, (1.6, -hy - 0.1, 0.25), (1.75, -hy + 0.02, 3.0), WOOD, 0.42)
    K.box(g, (-1.75, -hy - 0.1, 2.9), (1.75, -hy + 0.02, 3.05), WOOD, 0.42)
    z_ridge = 5.6
    for x, sgn in ((-hx, -1), (hx, 1)):
        pts = [(x, -hy, h), (x, hy, h), (x, 0, z_ridge)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), DWOOD, 0.44, smooth=0)
    gable_roof(g, -hx, hx, -hy, hy, h - 0.05, z_ridge, ROPE, var=0.46, overhang=0.45)
    p = kit.add('vale_barn', g, budget=300, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [w, d]


def smithy(kit):
    rng = R('vale_smithy')
    g = K.Geo()
    w, d, h = 6.0, 5.0, 2.9
    hx, hy = w / 2, d / 2
    K.box(g, (-hx - 0.3, -hy - 0.3, 0), (hx + 0.3, hy + 0.3, 0.12), DSTONE, 0.4)   # a flagged floor
    for x in (-hx, hx):
        for y in (-hy, hy):
            K.box(g, (x - 0.15, y - 0.15, 0), (x + 0.15, y + 0.15, h), WOOD, 0.42)
    K.box(g, (-hx - 0.1, -hy - 0.1, h - 0.2), (hx + 0.1, hy + 0.1, h), WOOD, 0.4)
    # the back wall in stone with the furnace built into it
    K.box(g, (-hx, hy - 0.4, 0), (hx, hy, h - 0.2), STONE, 0.46)
    K.box(g, (1.2, hy - 1.4, 0), (2.8, hy, 1.5), STONE, 0.5)        # the furnace block
    K.box(g, (1.5, hy - 1.42, 0.55), (2.5, hy - 1.3, 1.15), GLOW, 0.5)   # its mouth, glowing
    K.box(g, (1.6, hy - 1.0, 1.5), (2.4, hy - 0.2, h + 1.2), STONE, 0.44)   # the chimney
    # the anvil on its stump
    K.tube(g, (-1.2, -0.2, 0), (-1.2, -0.2, 0.6), 0.3, DWOOD, n=7, var=0.4, cap0=False)
    K.box(g, (-1.65, -0.4, 0.6), (-0.75, 0.0, 0.85), IRON, 0.5)
    K.box(g, (-1.95, -0.33, 0.7), (-1.65, -0.07, 0.85), IRON, 0.52)
    # the water trough
    K.box(g, (-2.6, 1.2, 0), (-1.4, 1.9, 0.6), DWOOD, 0.4)
    K.box(g, (-2.52, 1.28, 0.5), (-1.48, 1.82, 0.56), WATER, 0.5)
    z_ridge = 4.4
    gable_roof(g, -hx, hx, -hy, hy, h - 0.05, z_ridge, ROPE, var=0.48, overhang=0.5)
    p = kit.add('vale_smithy', g, budget=320, sheet={'az': 28, 'el': 18})
    kit.light(p, (2.0, hy - 1.5, 0.9), 'fire')
    kit.fx(p, (2.0, hy - 1.45, 0.85), 'glow')
    p.info['footprint'] = [w, d]
    p.info['open'] = True


def well(kit):
    rng = R('vale_well')
    g = K.Geo()
    K.lathe(g, [(0.95, 0.0), (0.95, 0.9), (0.72, 0.9), (0.72, 0.1)], 10, STONE, lambda b, k: 0.42 + jit(rng, 0.1),
            smooth=0, cap0=False, cap1=False)
    K.disc(g, 0.72, 10, WATER, z=0.1)
    for x in (-0.6, 0.6):
        K.box(g, (x - 0.07, -0.07, 0.9), (x + 0.07, 0.07, 2.3), WOOD, 0.42)
    K.box(g, (-0.75, -0.06, 2.2), (0.75, 0.06, 2.32), WOOD, 0.4)
    gable_roof(g, -0.7, 0.7, -0.8, 0.8, 2.25, 2.9, ROPE, var=0.5, overhang=0.2, thick=0.1)
    K.tube(g, (-0.62, 0, 1.9), (0.62, 0, 1.9), 0.06, DWOOD, n=6, var=0.4)   # the windlass
    K.box(g, (-0.14, -0.14, 1.1), (0.14, 0.14, 1.36), DWOOD, 0.38)        # the bucket
    p = kit.add('vale_well', g, budget=170, sheet={'az': 30, 'el': 20})
    p.info['footprint'] = [2.0, 2.0]


def shrine(kit):
    rng = R('vale_shrine')
    g = K.Geo()
    K.box(g, (-0.7, -0.7, 0), (0.7, 0.7, 0.25), DSTONE, 0.44)
    K.box(g, (-0.45, -0.45, 0.25), (0.45, 0.45, 1.9), STONE, 0.48)
    K.box(g, (-0.32, -0.46, 0.9), (0.32, -0.1, 1.6), INK, 0.5)        # the niche
    K.box(g, (-0.06, -0.3, 0.9), (0.06, -0.18, 1.18), GLOW, 0.5)       # the candle
    K.box(g, (-0.6, -0.6, 1.9), (0.6, 0.6, 2.1), STONE, 0.42)
    pts = [(-0.5, -0.5, 2.1), (0.5, -0.5, 2.1), (0.5, 0.5, 2.1), (-0.5, 0.5, 2.1), (0, 0, 2.7)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        g.pf([a, b, pts[4]], DSTONE, 0.4, smooth=0)
    p = kit.add('vale_shrine', g, budget=70, sheet={'az': 30, 'el': 20})
    kit.light(p, (0, -0.3, 1.1), 'candle')
    p.info['footprint'] = [1.4, 1.4]


def stall(kit):
    rng = R('vale_stall')
    g = K.Geo()
    w, d = 3.2, 2.0
    for x in (-w / 2, w / 2):
        for y in (-d / 2, d / 2):
            K.box(g, (x - 0.07, y - 0.07, 0), (x + 0.07, y + 0.07, 2.3), WOOD, 0.42)
    K.box(g, (-w / 2 - 0.1, -d / 2 - 0.1, 0.85), (w / 2 + 0.1, -d / 2 + 0.7, 0.98), WOOD, 0.46)   # the counter
    K.box(g, (-w / 2 - 0.1, -d / 2 - 0.1, 0.1), (w / 2 + 0.1, -d / 2 + 0.7, 0.85), DWOOD, 0.4)
    # the awning: stripes of cloth1 and plaster
    for i in range(6):
        x0 = -w / 2 - 0.25 + i * (w + 0.5) / 6
        x1 = x0 + (w + 0.5) / 6
        g.pf([(x0, -d / 2 - 0.5, 2.1), (x1, -d / 2 - 0.5, 2.1), (x1, d / 2 + 0.2, 2.45), (x0, d / 2 + 0.2, 2.45)],
             CLOTH1 if i % 2 == 0 else BONE, 0.5, smooth=0)
        g.pf([(x0, d / 2 + 0.2, 2.45), (x1, d / 2 + 0.2, 2.45), (x1, -d / 2 - 0.5, 2.1), (x0, -d / 2 - 0.5, 2.1)],
             CLOTH1 if i % 2 == 0 else BONE, 0.4, smooth=0)
    for i, (x, y) in enumerate(((-0.9, -0.4), (0.1, -0.5), (0.9, -0.3))):
        K.box(g, (x - 0.25, y - 0.2, 0.98), (x + 0.25, y + 0.2, 1.3), (ROPE, BRASS, CLOTH2)[i], 0.5)
    p = kit.add('vale_stall', g, budget=140, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [w + 0.4, d + 0.6]


def fence(kit):
    rng = R('vale_fence')
    g = K.Geo()
    for x in (-1.0, 1.0):
        K.box(g, (x - 0.07, -0.07, 0), (x + 0.07, 0.07, 1.15), WOOD, 0.4 + jit(rng, 0.05))
    for z in (0.45, 0.95):
        K.box(g, (-1.1, -0.04, z), (1.1, 0.04, z + 0.1), WOOD, 0.46)
    p = kit.add('vale_fence', g, budget=50, sheet={'az': 30, 'el': 18})
    p.info['span'] = 2.0


def bridge(kit):
    rng = R('vale_bridge')
    g = K.Geo()
    L, W = 5.0, 2.2
    for y in (-W / 2 + 0.15, W / 2 - 0.15):
        K.box(g, (-L / 2, y - 0.12, 0.25), (L / 2, y + 0.12, 0.5), DWOOD, 0.4)
    n = 14
    for i in range(n):
        x0 = -L / 2 + i * L / n
        K.box(g, (x0 + 0.02, -W / 2, 0.5), (x0 + L / n - 0.02, W / 2, 0.58), WOOD, 0.44 + jit(rng, 0.06))
    for x in (-L / 2 + 0.2, L / 2 - 0.2):
        for y in (-W / 2, W / 2):
            K.box(g, (x - 0.07, y - 0.07, 0), (x + 0.07, y + 0.07, 1.3), WOOD, 0.4)
    for y in (-W / 2, W / 2):
        K.box(g, (-L / 2 + 0.1, y - 0.04, 1.2), (L / 2 - 0.1, y + 0.04, 1.3), WOOD, 0.42)
    p = kit.add('vale_bridge', g, budget=280, sheet={'az': 30, 'el': 18})
    p.info['span'] = L
    p.info['walkable'] = 0.58


def campfire(kit):
    rng = R('vale_campfire')
    g = K.Geo()
    for i in range(7):
        a = math.radians(i * 360 / 7 + jit(rng, 10))
        K.rock(g, rng, (math.cos(a) * 0.55, math.sin(a) * 0.55, 0.08), (0.16, 0.13, 0.11), STONE, n=7, var=0.45)
    for a in (15, 75, 135):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0)) * 0.42
        K.tube(g, tuple(-d + Vector((0, 0, 0.08))), tuple(d + Vector((0, 0, 0.2))), 0.07, DWOOD, n=5, var=0.35)
    K.lathe(g, [(0.0, 0.1), (0.14, 0.25), (0.08, 0.45), (0.0, 0.62)], 6, GLOW, 0.5, smooth=0, cap0=False)
    p = kit.add('vale_campfire', g, budget=150, sheet={'az': 30, 'el': 24})
    kit.light(p, (0, 0, 0.4), 'fire')
    kit.fx(p, (0, 0, 0.35), 'glow')


def hay_bale(kit):
    rng = R('vale_hay_bale')
    g = K.Geo()
    K.lathe(g, [(0.0, -0.55), (0.52, -0.55), (0.52, 0.55), (0.0, 0.55)], 9, ROPE, lambda b, k: 0.6 + jit(rng, 0.1),
            smooth=35, m=T(0, 0, 0.52) @ Ry(90))     # G 0.6: fresh hay a shade lighter than the thatch (2026-11-04)
    kit.add('vale_hay_bale', g, budget=40, sheet={'az': 30, 'el': 22})


def scarecrow(kit):
    rng = R('vale_scarecrow')
    g = K.Geo()
    K.box(g, (-0.05, -0.05, 0), (0.05, 0.05, 2.2), WOOD, 0.4)
    K.box(g, (-0.8, -0.04, 1.6), (0.8, 0.04, 1.68), WOOD, 0.42)
    K.box(g, (-0.3, -0.16, 0.9), (0.3, 0.16, 1.75), CLOTH1, 0.5)       # the coat
    K.box(g, (-0.78, -0.1, 1.5), (0.78, 0.1, 1.68), CLOTH1, 0.44)      # the sleeves
    K.rock(g, rng, (0, 0, 2.0), (0.2, 0.2, 0.22), ROPE, n=8, var=0.5, flat=False)   # the sack head
    K.lathe(g, [(0.0, 2.15), (0.34, 2.17), (0.14, 2.2), (0.0, 2.42)], 7, ROPE, 0.42, smooth=0, cap0=False)   # the hat
    kit.add('vale_scarecrow', g, budget=90, sheet={'az': 30, 'el': 16})


def signpost(kit):
    """The signpost (town review 2026-11-04: "blank boards"): a square oak post on a stone foot with a diamond finial,
    three pointed arms — toward +x at 2.3 m, toward −x at 1.9 m and toward −y at 1.5 m — each with a plain pale face
    on both sides big enough for a name (0.85 × 0.24 m; the game overlays the text; `info['boards']` lists every
    face's centre, yaw and size in game space). A stouter, taller silhouette than the lamp post, with no lantern."""
    g = K.Geo()
    K.box(g, (-0.22, -0.22, 0), (0.22, 0.22, 0.28), STONE, 0.42, skip=('-z',))
    K.box(g, (-0.09, -0.09, 0.28), (0.09, 0.09, 2.75), WOOD, 0.4, skip=('-z',))
    K.lathe(g, [(0.0, 2.75), (0.15, 2.9), (0.0, 3.05)], 4, WOOD, 0.46, smooth=0, phase=math.pi / 4)
    boards = []
    for yaw, z in ((0, 2.3), (180, 1.9), (-90, 1.5)):
        mk = g.mark()
        K.box(g, (0.09, -0.035, z), (1.05, 0.035, z + 0.32), WOOD, 0.46, skip=('-x',))
        tip = (1.24, 0.0, z + 0.16)
        g.pf([(1.05, -0.035, z), tip, (1.05, -0.035, z + 0.32)], WOOD, 0.44)
        g.pf([(1.05, 0.035, z + 0.32), tip, (1.05, 0.035, z)], WOOD, 0.44)
        g.pf([(1.05, -0.035, z + 0.32), tip, (1.05, 0.035, z + 0.32)], WOOD, 0.5)
        g.pf([(1.05, 0.035, z), tip, (1.05, -0.035, z)], WOOD, 0.38)
        face = [(0.15, z + 0.04), (1.0, z + 0.04), (1.0, z + 0.28), (0.15, z + 0.28)]
        plate(g, face, -0.037, BONE, 0.62)
        g.pf([(x, 0.037, zz) for x, zz in reversed(face)], BONE, 0.62)
        g.transform(Rz(yaw), mk)
        for side, dy in ((0, -0.037), (180, 0.037)):
            at = Rz(yaw) @ Vector((0.575, dy, z + 0.16))
            boards.append({'at': K.blender_to_game(at), 'yaw': (yaw + side) % 360, 'size': [0.85, 0.24]})
    p = kit.add('vale_signpost', g, budget=100, sheet={'az': 30, 'el': 16})
    p.info['footprint'] = plan_size(g)
    p.info['boards'] = boards


# ====================================================================== the gathering (Phase W5)
def ore_rock(kit, mesh_id, ore_slot, var=0.5):
    """A mineable rock: the big rock with flecks of ore showing through its face."""
    rng = R(mesh_id)
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.36), (0.9, 0.75, 0.62), STONE, n=13, var=0.48)
    for i in range(7):
        a = math.radians(i * 51 + jit(rng, 15))
        c = (math.cos(a) * 0.55, math.sin(a) * 0.5, 0.3 + rng.uniform(-0.12, 0.28))
        K.rock(g, rng, c, (0.16, 0.13, 0.1), ore_slot, n=7, var=var, flat=False)
    p = kit.add(mesh_id, g, budget=120, sheet={'az': 30, 'el': 22})
    p.info['node'] = True


def rock_empty(kit):
    rng = R('vale_rock_empty')
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.3), (0.8, 0.65, 0.5), DSTONE, n=11, var=0.42)
    kit.add('vale_rock_empty', g, budget=40, sheet={'az': 30, 'el': 22})


def stump(kit):
    rng = R('vale_stump')
    g = K.Geo()
    K.lathe(g, [(0.3, 0.0), (0.28, 0.3), (0.22, 0.42), (0.0, 0.42)], 8, DWOOD, lambda b, k: 0.4 + jit(rng, 0.08), smooth=0, cap0=False, cap1=False)
    K.disc(g, 0.22, 8, WOOD, z=0.42, var=0.62)
    for a in (20, 140, 250):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        K.tube(g, tuple(d * 0.22 + Vector((0, 0, 0.04))), tuple(d * 0.5 + Vector((0, 0, 0.0))), 0.07, DWOOD, r1=0.03, n=5, var=0.38)
    kit.add('vale_stump', g, budget=110, sheet={'az': 30, 'el': 22})


def fishing_spot(kit):
    rng = R('vale_fishing_spot')
    g = K.Geo()
    # ripples: three rings of thin flat bands on the water, pale
    for r in (0.35, 0.65, 0.95):
        pts = [(math.cos(2 * math.pi * k / 14) * r, math.sin(2 * math.pi * k / 14) * r, 0.0) for k in range(15)]
        K.ribbon(g, pts, 0.07, BONE, var=0.55, normal=(0, 0, 1), smooth=0)
    # a fish's back breaking the surface
    K.lathe(g, [(0.0, -0.18), (0.05, -0.08), (0.06, 0.06), (0.0, 0.18)], 6, DSTONE, 0.5, smooth=30, m=Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Translation((0.2, 0, 0.02)))
    p = kit.add('vale_fishing_spot', g, budget=120, bake={'skip': True}, sheet={'az': 30, 'el': 40})
    p.info['doubleSided'] = True
    p.info['node'] = True
    p.info['onWater'] = True


def snare_spot(kit):
    rng = R('vale_snare_spot')
    g = K.Geo()
    for x in (-0.3, 0.3):
        K.box(g, (x - 0.03, -0.03, 0), (x + 0.03, 0.03, 0.55), WOOD, 0.42)
    K.box(g, (-0.33, -0.02, 0.5), (0.33, 0.02, 0.56), WOOD, 0.44)
    pts = [(0.0, 0.0, 0.5), (0.0, 0.0, 0.3), (0.12, 0.0, 0.18), (0.0, 0.0, 0.08), (-0.12, 0.0, 0.18), (0.0, 0.0, 0.3)]
    K.ribbon(g, pts, 0.012, ROPE, var=0.5, normal=(0, -1, 0), smooth=0)
    K.rock(g, rng, (0.25, 0.25, 0.05), (0.1, 0.08, 0.05), STONE, n=6, var=0.45)
    p = kit.add('vale_snare_spot', g, budget=60, sheet={'az': 30, 'el': 18})
    p.info['doubleSided'] = True
    p.info['node'] = True


def berry_bush(kit):
    rng = R('vale_berry_bush')
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.42), (0.6, 0.55, 0.42), CLOTH1, n=12, var=0.46, flat=False)
    K.rock(g, rng, (0.3, 0.2, 0.3), (0.35, 0.3, 0.28), CLOTH1, n=8, var=0.54, flat=False)
    for i in range(12):
        a = rng.uniform(0, 2 * math.pi)
        c = (math.cos(a) * rng.uniform(0.25, 0.6), math.sin(a) * rng.uniform(0.2, 0.55), 0.35 + rng.uniform(0, 0.4))
        K.rock(g, rng, c, (0.045, 0.045, 0.045), GEM, n=5, var=0.5, flat=False)
    p = kit.add('vale_berry_bush', g, budget=160, sheet={'az': 30, 'el': 20})
    p.info['node'] = True


def mushrooms(kit):
    rng = R('vale_mushrooms')
    g = K.Geo()
    for (x, y, h, r) in ((0, 0, 0.26, 0.14), (0.22, 0.12, 0.18, 0.1), (-0.18, 0.15, 0.2, 0.11), (0.08, -0.22, 0.14, 0.08), (-0.1, -0.12, 0.1, 0.06)):
        K.tube(g, (x, y, 0), (x, y, h), 0.03, BONE, n=6, var=0.55)
        K.lathe(g, [(0.0, h - 0.04), (r, h - 0.02), (r * 0.7, h + 0.05), (0.0, h + 0.08)], 8, CLOTH1 if r > 0.09 else ROPE, 0.5, smooth=30, cap0=False, m=Matrix.Translation((x, y, 0)))
    p = kit.add('vale_mushrooms', g, budget=280, sheet={'az': 30, 'el': 22})
    p.info['node'] = True


def herb_patch(kit):
    rng = R('vale_herb_patch')
    g = K.Geo()
    for i in range(9):
        a = math.radians(i * 40 + jit(rng, 15))
        c = Vector((math.cos(a) * rng.uniform(0.1, 0.4), math.sin(a) * rng.uniform(0.1, 0.4), 0))
        for j in range(3):
            b = math.radians(j * 120 + jit(rng, 30))
            tip = c + Vector((math.cos(b) * 0.12, math.sin(b) * 0.12, rng.uniform(0.18, 0.3)))
            side = Vector((-math.sin(b), math.cos(b), 0)) * 0.035
            g.pf([tuple(c - side), tuple(c + side), tuple(tip)], MOSS, 0.6 + jit(rng, 0.1), smooth=0)
        K.rock(g, rng, tuple(c + Vector((0, 0, 0.16))), (0.05, 0.05, 0.04), BRASS, n=5, var=0.5, flat=False)
    p = kit.add('vale_herb_patch', g, budget=120, bake={'skip': True}, sheet={'az': 30, 'el': 20})
    p.info['doubleSided'] = True
    p.info['node'] = True


# ====================================================================== the stations (Phases W6–W7)
def furnace(kit):
    """A free-standing smelting furnace: a stone block with a glowing mouth on its front (−Y), a short chimney."""
    rng = R('vale_furnace')
    g = K.Geo()
    K.box(g, (-0.9, -0.8, 0), (0.9, 0.8, 0.12), DSTONE, 0.42)                        # a flagged base
    K.box(g, (-0.8, -0.7, 0.12), (0.8, 0.7, 1.5), STONE, 0.48 + jit(rng, 0.04))     # the block
    K.box(g, (-0.85, -0.75, 1.5), (0.85, 0.75, 1.6), DSTONE, 0.44)                   # the cap course
    K.box(g, (-0.5, -0.72, 0.35), (0.5, -0.6, 1.15), INK, 0.5)                       # the mouth's dark surround
    K.box(g, (-0.38, -0.74, 0.45), (0.38, -0.62, 1.0), GLOW, 0.5)                    # the mouth, glowing
    for z in (0.55, 1.2):                                                            # two iron bands
        K.box(g, (-0.84, -0.74, z), (0.84, 0.74, z + 0.1), IRON, 0.5)
    K.box(g, (-0.3, 0.1, 1.6), (0.3, 0.7, 2.5), STONE, 0.46)                         # the chimney
    K.box(g, (-0.36, 0.04, 2.5), (0.36, 0.76, 2.62), DSTONE, 0.42)                   # its cap
    K.box(g, (-0.16, 0.24, 2.62), (0.16, 0.56, 2.64), INK, 0.5)                      # the flue
    p = kit.add('vale_furnace', g, budget=160, sheet={'az': 30, 'el': 18})
    kit.light(p, (0.0, -0.85, 0.75), 'fire')
    kit.fx(p, (0.0, -0.78, 0.72), 'glow')
    p.info['node'] = True
    p.info['footprint'] = [1.8, 1.6]


def anvil(kit):
    """The smithy's anvil as a free-standing piece: an iron body with a horn on a round stump, the horn toward −X."""
    rng = R('vale_anvil')
    g = K.Geo()
    K.tube(g, (0, 0, 0), (0, 0, 0.6), 0.3, DWOOD, n=7, var=0.4, cap0=False)         # the stump
    K.box(g, (-0.33, -0.33, 0.5), (0.33, 0.33, 0.56), IRON, 0.46)                     # a strap round the stump's top
    K.box(g, (-0.15, -0.2, 0.6), (0.45, 0.2, 0.85), IRON, 0.5)                        # the body
    K.lathe(g, [(0.13, 0.0), (0.0, 0.32)], 6, IRON, 0.52, smooth=0, cap0=False,      # the horn, a cone toward −X
            m=T(-0.15, 0, 0.775) @ Ry(-90))
    p = kit.add('vale_anvil', g, budget=90, sheet={'az': 30, 'el': 22})
    p.info['node'] = True
    p.info['footprint'] = [1.0, 0.7]


def altar(kit):
    """A runecrafting altar: a stone plinth, a tilted slab with a glowing disc, four standing stones round it
    (the front, -Y, is the gap between the two nearer stones)."""
    rng = R('vale_altar')
    g = K.Geo()
    K.box(g, (-0.7, -0.7, 0), (0.7, 0.7, 0.15), DSTONE, 0.44)                        # the step
    K.box(g, (-0.52, -0.52, 0.15), (0.52, 0.52, 0.8), STONE, 0.48)                   # the plinth
    K.box(g, (-0.03, -0.53, 0.3), (0.03, -0.51, 0.62), GLOW, 0.5)                    # a rune line on the front
    K.box(g, (-0.16, -0.53, 0.44), (0.16, -0.51, 0.48), GLOW, 0.5)
    tilt = T(0, 0, 0.86) @ Rx(8) @ T(0, 0, -0.86)                                    # the slab dips to the front
    K.box(g, (-0.62, -0.62, 0.8), (0.62, 0.62, 0.92), STONE, 0.5, m=tilt)
    K.lathe(g, [(0.38, 0.92), (0.38, 0.96), (0.3, 0.96)], 10, DSTONE, 0.42, smooth=0,   # the ring round the disc
            cap0=False, cap1=False, m=tilt)
    K.disc(g, 0.3, 10, GLOW, z=0.955, var=0.5, m=tilt)                                # the glowing disc
    for i, a in enumerate((45, 135, 225, 315)):                                       # the standing stones
        ang = math.radians(a + jit(rng, 8))
        cx, cy = math.cos(ang) * 1.1, math.sin(ang) * 1.1
        h = 1.0 + jit(rng, 0.1)
        pts = [(-0.15, -0.15, 0), (0.15, -0.15, 0), (0.15, 0.15, 0), (-0.15, 0.15, 0),
               (-0.11, -0.1, h), (0.1, -0.11, h * 0.94), (0.11, 0.1, h), (-0.1, 0.11, h * 0.9)]
        # STONE, not DSTONE: the Vale palette's slot 1 is packed earth (brown) and reads as timber on a post
        K.hull(g, pts, STONE, 0.36 + jit(rng, 0.05), m=T(cx, cy, 0) @ Rz(a) @ Ry(-3 - rng.uniform(0, 3)))
    p = kit.add('vale_altar', g, budget=220, sheet={'az': 30, 'el': 22})
    kit.fx(p, (0, 0, 0.98), 'glow')
    p.info['node'] = True
    p.info['footprint'] = [2.5, 2.5]


# ====================================================================== the town (Phase W8)
# Closed buildings (the hero does not go in): a door and windows on the front (−Y), the footprint centred on the
# origin. The town wall is three pieces because a collider is a whole-piece box: the palisade tiles along x, the
# towers stand at its corners and either side of a gate, and the gate's overhead arch has no posts (no collider).
def eave_z(wall_top, z_ridge, run, overhang, thick=0.14):
    """The eave height that tucks a gable_roof's underside just over a wall top at `run` from the ridge line (so no
    slit of sky shows between the wall and the roof)."""
    k = overhang / (run + overhang)
    return (wall_top - 0.04 + thick - z_ridge * k) / (1 - k)


def gable_roof_y(g, x0, x1, y0, y1, z_eave, z_ridge, slot, var=0.5, overhang=0.35, thick=0.14):
    """gable_roof with its ridge along Y (a gable end to the front)."""
    mk = g.mark()
    gable_roof(g, y0, y1, -x1, -x0, z_eave, z_ridge, slot, var, overhang, thick)
    g.transform(Rz(90), mk)


def on_face(side, at, along, z):
    """The matrix that stands a front-facing detail (modelled facing −Y, its back at y 0) on a wall face: side '-y' /
    '+y' / '-x' / '+x', `at` the face's plane (y for ±y, x for ±x), `along` its place along the wall, z its foot."""
    if side == '-y':
        return T(along, at, z)
    if side == '+y':
        return T(along, at, z) @ Rz(180)
    if side == '-x':
        return T(at, along, z) @ Rz(-90)
    return T(at, along, z) @ Rz(90)


def town_shutters(g, w, h, m=None):
    """W18-town: two shutter leaves standing open flat against the wall either side of a w × h window (local origin =
    the sill's centre on the wall face, facing −Y): each a quad 3 cm off the wall, (w/2 + 0.04) wide and (h + 0.06)
    tall from x ±(w/2 + 0.1) outward, marked trim (K.trim: the game repaints them) (4 tris)."""
    mk = g.mark()
    sw = w / 2 + 0.04
    for x0 in (-(w / 2 + 0.1) - sw, w / 2 + 0.1):
        K.trim(g, g.pf([(x0, -0.03, -0.03), (x0 + sw, -0.03, -0.03), (x0 + sw, -0.03, h + 0.03), (x0, -0.03, h + 0.03)],
                       DWOOD, 0.4))
    if m is not None:
        g.transform(m, mk)


def town_window(g, m, w=0.9, h=1.1, frame=WOOD, fvar=0.42, pane=INK, cross=True, glass=None, shutters=False):
    """A window: a frame proud of the wall, a dark pane, a cross of glazing bars (16 tris); local origin = the sill's
    centre on the wall face, facing −Y. `glass` (default: an ink pane is glass, a plank one a shutter) marks the pane
    as a lit window (gv.A = 0, K.glaze). W18-town: `shutters` adds two open shutters (town_shutters, 4 tris)."""
    mk = g.mark()
    K.box(g, (-w / 2 - 0.08, -0.08, -0.08), (w / 2 + 0.08, 0.02, h + 0.08), frame, fvar, skip=('+y',))
    y = -0.1
    f = g.pf([(-w / 2, y, 0), (w / 2, y, 0), (w / 2, y, h), (-w / 2, y, h)], pane, 0.5)
    if (pane == INK) if glass is None else glass:
        K.glaze(g, f)
    if cross:
        y = -0.12
        g.pf([(-0.035, y, 0), (0.035, y, 0), (0.035, y, h), (-0.035, y, h)], frame, fvar + 0.04)
        zc = h * 0.56
        y = -0.125
        g.pf([(-w / 2, y, zc - 0.035), (w / 2, y, zc - 0.035), (w / 2, y, zc + 0.035), (-w / 2, y, zc + 0.035)],
             frame, fvar + 0.04)
    if shutters:                                                                # W18-town: open shutters
        town_shutters(g, w, h)
    g.transform(m, mk)


def town_door(g, m, w=1.0, h=2.1, frame=WOOD, fvar=0.42, leaf=DWOOD, double=False, back=0.02):
    """A door: a frame proud of the wall (`back` = how far it reaches into the wall), a plank leaf, iron handles (12
    tris, 16 double); local origin = the threshold's centre on the wall face, facing −Y."""
    mk = g.mark()
    K.box(g, (-w / 2 - 0.1, -0.1, 0), (w / 2 + 0.1, back, h + 0.12), frame, fvar, skip=('+y', '-z'))
    y = -0.12
    K.trim(g, g.pf([(-w / 2, y, 0.0), (w / 2, y, 0.0), (w / 2, y, h), (-w / 2, y, h)], leaf, 0.38))   # W18-town: trim
    y = -0.14
    if double:
        g.pf([(-0.03, y, 0.0), (0.03, y, 0.0), (0.03, y, h), (-0.03, y, h)], frame, fvar - 0.1)
    for hx in ((-0.16, 0.16) if double else (w / 2 - 0.18,)):
        g.pf([(hx - 0.045, y, 1.0), (hx + 0.045, y, 1.0), (hx + 0.045, y, 1.09), (hx - 0.045, y, 1.09)], IRON, 0.5)
    g.transform(m, mk)


def lancet(g, m, w=0.55, h=1.8, rim=0.1, depth=0.1, frame=STONE, fvar=0.68, pane=INK, pvar=0.5, glass=None):
    """A tall pointed window (or, with a plank pane, a door) in a dressed-stone surround (16 tris); local origin = the
    sill's centre on the wall face, facing −Y. An ink pane is glass (a lit window, K.glaze) unless `glass` says not."""
    mk = g.mark()
    a = w * 0.75
    outer = [(-w / 2 - rim, -rim), (w / 2 + rim, -rim), (w / 2 + rim, h), (0.0, h + a + rim * 1.3), (-w / 2 - rim, h)]
    K.slab_xz(g, outer, -depth, 0.02, frame, fvar, back=False)
    y = -depth - 0.02
    inner = [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h), (0.0, h + a), (-w / 2, h)]
    f = g.pf([(x, y, z) for x, z in inner], pane, pvar)
    if (pane == INK) if glass is None else glass:
        K.glaze(g, f)
    g.transform(m, mk)


def ring_wall(g, x0, y0, x1, y1, t, z0, z1, slot, var=0.46):
    """A hollow square parapet `t` thick: its outer faces, inner faces and top (24 tris)."""
    o = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    i = [(x0 + t, y0 + t), (x1 - t, y0 + t), (x1 - t, y1 - t), (x0 + t, y1 - t)]
    for k in range(4):
        a, b = o[k], o[(k + 1) % 4]
        c, d = i[k], i[(k + 1) % 4]
        g.pf([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], slot, var)
        g.pf([(d[0], d[1], z0), (c[0], c[1], z0), (c[0], c[1], z1), (d[0], d[1], z1)], slot, var - 0.08)
        g.pf([(a[0], a[1], z1), (b[0], b[1], z1), (d[0], d[1], z1), (c[0], c[1], z1)], slot, var + 0.06)


def pyramid(g, cx, cy, hw, hd, z0, apex, slot, var=0.45, under=True):
    """A four-sided pyramid roof over a rectangle (4 tris, 6 with its underside)."""
    c = [(cx - hw, cy - hd, z0), (cx + hw, cy - hd, z0), (cx + hw, cy + hd, z0), (cx - hw, cy + hd, z0)]
    for k in range(4):
        g.pf([c[k], c[(k + 1) % 4], (cx, cy, apex)], slot, var + (0.05 if k % 2 else -0.02))
    if under:
        g.pf(list(reversed(c)), slot, var - 0.12)


def flat_strip(g, m, a, b, width, slot, var=0.5, y=-0.01):
    """A flat strip from a to b ((x, z) on a wall face, front −Y): a brace or a batten seen from the front (2 tris)."""
    mk = g.mark()
    d = Vector((b[0] - a[0], b[1] - a[1])).normalized()
    n = Vector((-d.y, d.x)) * (width / 2)
    pts = [(a[0] - n.x, a[1] - n.y), (b[0] - n.x, b[1] - n.y), (b[0] + n.x, b[1] + n.y), (a[0] + n.x, a[1] + n.y)]
    g.pf([(x, y, z) for x, z in pts], slot, var)
    g.transform(m, mk)


def recentre(g):
    """Moves the geometry so its plan bounds are centred on the origin → [w, d]."""
    lo, hi = g.bounds()
    g.transform(T(-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, 0))
    return [round(hi.x - lo.x, 2), round(hi.y - lo.y, 2)]


def barred_window(g, m, w=1.0, h=1.2, bars=3):
    """A barred window (the bank's ground floor): a pale dressed-stone frame, a dark pane (lit at night), `bars` iron
    bars across it (12 + 2 per bar tris); local origin = the sill's centre on the wall face, facing −Y."""
    mk = g.mark()
    town_window(g, Matrix.Identity(4), w=w, h=h, frame=STONE, fvar=0.66, cross=False)
    for k in range(bars):
        x = -w / 2 + (k + 1) * w / (bars + 1)
        stroke(g, (x, 0.0), (x, h), 0.05, -0.125, IRON, 0.5)
    g.transform(m, mk)


def bank(kit):
    """The bank (town review 2026-11-04: the Greek temple front replaced): a merchant's stone house with a strongroom
    feel — two storeys of field stone on a plinth with pale quoins and a string course, a round-headed door of iron-
    banded planks up a step, barred windows on the ground floor, cross windows above, crow-stepped gables at both
    ends under a slate roof whose ridge runs along x, a chimney on the back slope, a brass coin hung from an iron
    bracket by the door and a barred strongroom vent low on the right flank. 11 × 8 m with the step."""
    rng = R('vale_bank')
    g = K.Geo()
    hx, hy, zs, h, zr = 5.2, 3.45, 3.4, 6.5, 8.6             # the block 10.4 × 6.9 m, the string course, eaves, ridge
    K.box(g, (-5.5, -3.75, 0), (5.5, 3.75, 0.45), STONE, 0.34, skip=('-z',))                        # the plinth
    K.box(g, (-1.3, -4.0, 0), (1.3, -3.75, 0.24), STONE, 0.42, skip=('-z', '+y'))                   # the step
    K.box(g, (-hx, -hy, 0.45), (hx, hy, zs), STONE, 0.48 + jit(rng, 0.03), skip=('-z', '+z'))      # the ground floor
    K.box(g, (-hx - 0.12, -hy - 0.12, zs), (hx + 0.12, hy + 0.12, zs + 0.22), STONE, 0.66,
          skip=('-z',))                                                                             # the string course
    K.box(g, (-hx, -hy, zs + 0.22), (hx, hy, h), STONE, 0.55 + jit(rng, 0.03), skip=('-z', '+z'))  # the upper floor
    for sx in (-1, 1):                                                                              # pale quoins
        for sy in (-1, 1):
            xa, xb = sorted((sx * (hx - 0.5), sx * (hx + 0.08)))
            ya, yb = sorted((sy * (hy - 0.5), sy * (hy + 0.08)))
            K.box(g, (xa, ya, 0.45), (xb, yb, h), STONE, 0.74, skip=('-z', '+z'))
    # the crow-stepped gables at ±x: three steps a side up to a cap over the ridge, 0.4 m thick, standing proud
    steps = [(hy + 0.25, h - 0.4), (hy + 0.25, 6.85), (2.9, 6.85), (2.9, 7.55), (1.75, 7.55), (1.75, 8.25),
             (0.6, 8.25), (0.6, zr + 0.3)]
    outline = steps + [(-a, z) for a, z in reversed(steps)]
    for side, x in (('-x', -hx), ('+x', hx)):
        K.slab_xz(g, outline, -0.15, 0.25, STONE, 0.6, back=False, m=on_face(side, x, 0.0, 0.0))
    gable_roof(g, -hx + 0.3, hx - 0.3, -hy, hy, eave_z(h + 0.02, zr, hy, 0.35), zr, IRON, var=0.46, overhang=0.35)
    K.box(g, (2.6, 1.6, 7.0), (3.3, 2.3, 9.3), STONE, 0.45, skip=('-z',))                           # the chimney
    K.box(g, (2.52, 1.52, 9.3), (3.38, 2.38, 9.45), STONE, 0.36, skip=('-z',))
    # the door: round-headed, a pale surround, plank leaves with two iron bands, a centre line and a ring
    round_window(g, T(0, -hy, 0.45), w=1.4, h=2.0, rim=0.14, depth=0.12, pane=DWOOD, pvar=0.36)
    yb = -hy - 0.15
    for z in (1.1, 2.1):
        stroke(g, (-0.68, z), (0.68, z), 0.1, yb, IRON, 0.5)
    stroke(g, (0.0, 0.47), (0.0, 2.45), 0.03, yb, DWOOD, 0.2)
    for x in (-2.9, 2.9):                                                                           # barred below
        barred_window(g, T(x, -hy, 1.2), w=1.0, h=1.2)
    for side, at in (('-x', -hx), ('+x', hx)):
        barred_window(g, on_face(side, at, -1.0, 1.2), w=1.0, h=1.2)
    for x in (-2.9, 0.0, 2.9):                                                                      # cross windows above
        town_window(g, T(x, -hy, 4.2), w=1.0, h=1.3, frame=STONE, fvar=0.66)
    mk = g.mark()                                                                                   # the strongroom vent
    plate(g, [(-0.25, -0.15), (0.25, -0.15), (0.25, 0.15), (-0.25, 0.15)], -0.012, INK, 0.5)
    for x in (-0.09, 0.09):
        stroke(g, (x, -0.15), (x, 0.15), 0.04, -0.016, IRON, 0.5)
    g.transform(on_face('+x', hx, 1.6, 0.75), mk)
    # the coin sign: an iron arm and stay by the door, a brass coin hung from the arm's end on two rings
    sx = 1.95
    K.box(g, (sx - 0.05, -hy - 0.9, 3.05), (sx + 0.05, -hy, 3.15), IRON, 0.46, skip=('+y',))
    K.tube(g, (sx, -hy, 2.6), (sx, -hy - 0.7, 3.06), 0.025, IRON, n=4, var=0.46, cap0=False, cap1=False)
    for y in (-hy - 0.42, -hy - 0.68):
        K.tube(g, (sx, y, 3.05), (sx, y, 2.9), 0.02, IRON, n=3, var=0.44, cap0=False, cap1=False)
    for dx, rot in ((-0.03, -90), (0.03, 90)):
        K.disc(g, 0.42, 10, BRASS, var=0.66, m=T(sx + dx, -hy - 0.55, 2.48) @ Ry(rot))
        K.disc(g, 0.28, 8, BRASS, var=0.4, m=T(sx + dx * 1.3, -hy - 0.55, 2.48) @ Ry(rot))
    p = kit.add('vale_bank', g, budget=420, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [11.0, 8.0]
    p.info['door'] = [0.0, 0.45, hy]                      # the threshold's centre, game (x, y, z)
    p.info['chimney'] = [2.95, 9.45, -1.95]               # the flue's top, game (x, y, z)


def shop(kit, mesh_id, awning=CLOTH2, roof=DWOOD, roof_var=0.46, board=(2.3, 3.2, 1.95, 2.62), icon=None,
         extra=None, lean=False, mirror=False, budget=320):
    """A shop (the general store's plan, Phase W8 shares it): a timber-and-plaster building, a striped awning of
    `awning` and plaster over its wide window, a board on an iron bracket by the door (`icon(g, cx, yb, cz)` draws its
    mark on the board's face at y yb), a roof of `roof`; `extra(g, rng, y0)` adds what stands by the door (y0 = the
    front wall's face), `mirror` swaps the door and the sign to the other side."""
    rng = R(mesh_id)
    g = K.Geo()
    w, d, h, sy = 7.0, 4.6, 3.2, 0.6                 # the walls sit 0.6 m back so the awning stays in the footprint
    hx, y0, y1 = w / 2, sy - d / 2, sy + d / 2
    mk = g.mark()
    timber_walls(g, rng, w, d, h, lean=lean)
    g.transform(T(0, sy, 0), mk)
    zr = 5.3
    for x, sgn in ((-hx, -1), (hx, 1)):
        pts = [(x, y0, h), (x, y1, h), (x, sy, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), BONE, 0.48)
    gable_roof(g, -hx, hx, y0, y1, eave_z(h + 0.02, zr, d / 2, 0.35), zr, roof, var=roof_var)
    town_door(g, T(-2.55, y0, 0.3), w=1.0, h=2.1)
    town_window(g, T(0.2, y0, 1.0), w=2.4, h=1.2)
    for side, at in (('-x', -hx), ('+x', hx)):
        town_window(g, on_face(side, at, sy, 1.2), w=0.9, h=1.0)
    # the awning: stripes of the shop's colour and plaster over the window, a scalloped edge, two iron stays
    ax0, ax1, n, yo = -1.3, 1.7, 6, y0 - 1.15
    for i in range(n):
        xa = ax0 + i * (ax1 - ax0) / n
        xb = xa + (ax1 - ax0) / n
        xm = (xa + xb) / 2
        s = awning if i % 2 == 0 else BONE
        g.pf([(xa, yo, 2.3), (xb, yo, 2.3), (xb, y0, 2.8), (xa, y0, 2.8)], s, 0.52)
        g.pf([(xa, y0, 2.8), (xb, y0, 2.8), (xb, yo, 2.3), (xa, yo, 2.3)], s, 0.38)
        g.pf([(xm, yo, 2.1), (xb, yo, 2.3), (xa, yo, 2.3)], s, 0.5)
        g.pf([(xa, yo, 2.3), (xb, yo, 2.3), (xm, yo, 2.1)], s, 0.4)
    for x in (ax0 + 0.06, ax1 - 0.06):
        K.tube(g, (x, y0, 1.95), (x, yo + 0.06, 2.3), 0.025, IRON, n=4, var=0.46, cap0=False, cap1=False)
    # the sign: an iron arm out from the wall, a board hung from it with the shop's mark
    bx0, bx1, bz0, bz1 = board
    K.box(g, (2.7, y0 - 0.95, 2.62), (2.8, y0, 2.72), IRON, 0.46, skip=('+y',))
    K.tube(g, (2.75, y0, 2.15), (2.75, y0 - 0.6, 2.64), 0.025, IRON, n=4, var=0.46, cap0=False, cap1=False)
    K.box(g, (bx0, y0 - 0.92, bz0), (bx1, y0 - 0.84, bz1), DWOOD, 0.44)
    yb = y0 - 0.93
    if icon is None:
        g.pf([(2.75, yb, 2.03), (2.98, yb, 2.285), (2.75, yb, 2.54), (2.52, yb, 2.285)], BRASS, 0.6)
    else:
        icon(g, (bx0 + bx1) / 2, yb, (bz0 + bz1) / 2)
    if extra is not None:
        extra(g, rng, y0)
    if mirror:
        g.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
    p = kit.add(mesh_id, g, budget=budget, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [w, 6.0]
    return p


def general_store(kit):
    """The general store: a timber-and-plaster shop, a striped pine-green awning over its wide window, a board with a
    brass diamond on an iron bracket by the door, a shingle roof."""
    shop(kit, 'vale_store')


def inn(kit):
    """The inn: two storeys of timber and plaster on a stone sill, the upper floor jettied out over the street on
    braces, a thatch roof and a chimney, a bench by the door and a sign on an iron bracket."""
    rng = R('vale_inn')
    g = K.Geo()
    gx, gy0, gy1, gh = 4.5, -2.65, 3.2, 3.0          # the ground floor
    ux, uy0, uy1, uh = 4.8, -3.1, 3.35, 5.6          # the upper floor, jettied 0.45 m out to the front
    K.box(g, (-gx - 0.1, gy0 - 0.1, 0), (gx + 0.1, gy1 + 0.1, 0.35), STONE, 0.4, skip=('-z',))
    K.box(g, (-gx, gy0, 0.3), (gx, gy1, gh), BONE, 0.5 + jit(rng, 0.04), skip=('-z', '+z'))
    for x in (-gx, gx):
        for y in (gy0, gy1):
            K.box(g, (x - 0.12, y - 0.12, 0.3), (x + 0.12, y + 0.12, gh), WOOD, 0.42, skip=('-z', '+z'))
    K.box(g, (-ux - 0.05, uy0 - 0.1, 2.85), (ux + 0.05, uy0 + 0.2, 3.1), DWOOD, 0.4)            # the jetty's beam
    K.box(g, (-ux, uy0, gh), (ux, uy1, uh), BONE, 0.54 + jit(rng, 0.04), skip=('+z',))
    for x in (-ux, ux):
        for y in (uy0, uy1):
            K.box(g, (x - 0.11, y - 0.11, gh + 0.1), (x + 0.11, y + 0.11, uh), WOOD, 0.42, skip=('-z', '+z'))
    K.box(g, (-ux - 0.08, uy0 - 0.08, uh - 0.22), (ux + 0.08, uy1 + 0.08, uh + 0.02), WOOD, 0.4, skip=('-z', '+z'))
    for x in (-1.6, 1.6):                                                                      # studs between windows
        K.box(g, (x - 0.08, uy0 - 0.08, gh + 0.1), (x + 0.08, uy0, uh - 0.2), WOOD, 0.44, skip=('+y', '-z', '+z'))
    for x in (-3.6, -1.2, 1.2, 3.6):                                                           # braces under the jetty
        K.tube(g, (x, gy0, 2.2), (x, uy0 + 0.05, 2.9), 0.06, WOOD, n=4, var=0.4, cap0=False, cap1=False)
    zr = 7.8
    run, ym = (uy1 - uy0) / 2, (uy0 + uy1) / 2
    for x, sgn in ((-ux, -1), (ux, 1)):
        pts = [(x, uy0, uh), (x, uy1, uh), (x, ym, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), BONE, 0.5)
    gable_roof(g, -ux, ux, uy0, uy1, eave_z(uh + 0.02, zr, run, 0.4), zr, ROPE, var=0.5, overhang=0.4)
    K.box(g, (3.3, 0.7, 4.0), (4.1, 1.5, 8.5), STONE, 0.46, skip=('-z',))                       # the chimney
    K.box(g, (3.22, 0.62, 8.5), (4.18, 1.58, 8.68), STONE, 0.36, skip=('-z',))
    town_door(g, T(0, gy0, 0.3), w=1.3, h=2.2, double=True)
    for x in (-2.7, 2.7):
        town_window(g, T(x, gy0, 1.2), w=1.1, h=1.1)
    for x in (-3.2, 0.0, 3.2):
        town_window(g, T(x, uy0, 3.75), w=1.0, h=1.1)
    for side, at in (('-x', -ux), ('+x', ux)):
        town_window(g, on_face(side, at, ym, 3.75), w=1.0, h=1.1)
    # the sign: an iron arm off the upper floor's corner, a board with a straw-gold tankard on it
    sx = -4.4
    K.box(g, (sx - 0.05, uy0 - 1.15, 4.3), (sx + 0.05, uy0, 4.4), IRON, 0.46, skip=('+y',))
    K.tube(g, (sx, uy0, 3.7), (sx, uy0 - 0.8, 4.32), 0.03, IRON, n=4, var=0.46, cap0=False, cap1=False)
    K.box(g, (sx - 0.58, uy0 - 1.12, 3.2), (sx + 0.58, uy0 - 1.03, 4.3), DWOOD, 0.44)
    yb = uy0 - 1.13
    g.pf([(sx - 0.26, yb, 3.38), (sx + 0.14, yb, 3.38), (sx + 0.14, yb, 4.06), (sx - 0.26, yb, 4.06)], ROPE, 0.62)
    g.pf([(sx + 0.14, yb, 3.54), (sx + 0.34, yb, 3.54), (sx + 0.34, yb, 3.9), (sx + 0.14, yb, 3.9)], ROPE, 0.5)
    # the bench by the door
    K.box(g, (-2.75, -3.2, 0.42), (-1.25, -2.88, 0.5), WOOD, 0.5)
    for x in (-2.6, -1.4):
        K.box(g, (x - 0.05, -3.16, 0), (x + 0.05, -2.92, 0.42), DWOOD, 0.4, skip=('-z', '+z'))
    p = kit.add('vale_inn', g, budget=420, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [10.0, 7.0]


def buttress(g, x, y, sgn, depth=0.5, half=0.22, z_wall=3.3, z_out=1.7, slot=STONE, var=0.42):
    """A sloped buttress against the side wall at x (sgn +1: the +x wall, −1: the −x wall); 8 tris."""
    mk = g.mark()
    xi, xo, ya, yb = 0.0, depth, y - half, y + half
    g.pf([(xi, ya, 0), (xo, ya, 0), (xo, ya, z_out), (xi, ya, z_wall)], slot, var)
    g.pf([(xi, yb, z_wall), (xo, yb, z_out), (xo, yb, 0), (xi, yb, 0)], slot, var)
    g.pf([(xo, ya, 0), (xo, yb, 0), (xo, yb, z_out), (xo, ya, z_out)], slot, var + 0.04)
    g.pf([(xo, ya, z_out), (xo, yb, z_out), (xi, yb, z_wall), (xi, ya, z_wall)], slot, var + 0.1)
    g.transform(T(x, 0, 0) @ Matrix.Diagonal((float(sgn), 1.0, 1.0, 1.0)), mk)


def chapel(kit):
    """The chapel: a stone nave with its long axis front to back, sloped buttresses and tall pointed windows down its
    sides, a slate roof; a short square bell tower stands against the front gable with the door in its foot and an
    open belfry (a brass bell) under a slate spire."""
    rng = R('vale_chapel')
    g = K.Geo()
    nx, ny0, ny1, nh, zr = 3.1, -2.95, 5.2, 4.6, 7.4
    K.box(g, (-nx - 0.1, ny0, 0), (nx + 0.1, ny1 + 0.1, 0.3), STONE, 0.34, skip=('-z',))
    K.box(g, (-nx, ny0, 0.3), (nx, ny1, nh), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    g.pf([(-nx, ny0, nh), (nx, ny0, nh), (0.0, ny0, zr - 0.06)], STONE, 0.5)
    g.pf([(nx, ny1, nh), (-nx, ny1, nh), (0.0, ny1, zr - 0.06)], STONE, 0.5)
    gable_roof_y(g, -nx, nx, ny0, ny1, eave_z(nh, zr, nx, 0.3), zr, IRON, var=0.48, overhang=0.3)
    for y in (-1.4, 1.5, 4.4):
        for sgn in (-1, 1):
            buttress(g, sgn * nx, y, sgn)
    for y in (0.05, 2.95):
        for side, at in (('-x', -nx), ('+x', nx)):
            lancet(g, on_face(side, at, y, 1.4), w=0.55, h=1.9)
    for x in (-2.2, 2.2):
        lancet(g, T(x, ny0, 1.6), w=0.45, h=1.5)
    for r, slot, v, dy in ((0.62, STONE, 0.7, 0.0), (0.46, INK, 0.5, 0.03)):                  # the round window
        mk = K.disc(g, r, 8, slot, var=v, m=T(0, ny1 + 0.02 + dy, 5.55) @ Rx(-90))
        if slot == INK:
            K.glaze(g, since=mk)
    # the tower
    tx, ty0, ty1 = 1.3, -5.3, -2.7
    tyc = (ty0 + ty1) / 2
    K.box(g, (-0.95, ty0 - 0.25, 0), (0.95, ty0, 0.18), STONE, 0.4, skip=('-z', '+y'))          # the step
    K.box(g, (-tx, ty0, 0), (tx, ty1, 6.6), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    lancet(g, T(0, ty0, 0.18), w=1.2, h=2.0, pane=DWOOD, pvar=0.38)                              # the door
    g.pf([(0.3, ty0 - 0.15, 1.1), (0.38, ty0 - 0.15, 1.1), (0.38, ty0 - 0.15, 1.18), (0.3, ty0 - 0.15, 1.18)],
         IRON, 0.5)
    lancet(g, T(0, ty0, 3.6), w=0.5, h=1.3)
    K.box(g, (-tx - 0.12, ty0 - 0.12, 6.5), (tx + 0.12, ty1 + 0.12, 6.72), STONE, 0.38, skip=('-z',))  # belfry ledge
    for xa in (-tx, tx - 0.45):
        for ya in (ty0, ty1 - 0.45):
            K.box(g, (xa, ya, 6.72), (xa + 0.45, ya + 0.45, 8.4), STONE, 0.5, skip=('-z', '+z'))
    K.box(g, (-tx - 0.15, ty0 - 0.15, 8.4), (tx + 0.15, ty1 + 0.15, 8.65), STONE, 0.4, skip=('-z',))
    pyramid(g, 0, tyc, tx + 0.15, (ty1 - ty0) / 2 + 0.15, 8.65, 10.6, IRON, var=0.46, under=False)
    K.box(g, (-0.85, tyc - 0.08, 7.92), (0.85, tyc + 0.08, 8.06), DWOOD, 0.4, skip=('-x', '+x'))   # the bell's beam
    K.lathe(g, [(0.42, 7.0), (0.3, 7.35), (0.2, 7.8), (0.0, 7.93)], 6, BRASS, 0.6, smooth=65, cap_slot=INK,
            m=T(0, tyc, 0))
    K.tube(g, (0, tyc, 10.5), (0, tyc, 10.9), 0.045, BRASS, n=4, var=0.55, cap0=False, cap1=False)
    K.lathe(g, [(0.0, 10.82), (0.13, 10.93), (0.0, 11.12)], 4, BRASS, 0.62, smooth=0, m=T(0, tyc, 0))
    p = kit.add('vale_chapel', g, budget=420, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [7.0, 11.0]


def skill_hall(kit):
    """The Skill Hall: a long timber hall on a tall stone foot, a shingle roof with a louvred cupola on its ridge, a
    double door up a step and two long green banners hanging either side of it."""
    rng = R('vale_hall')
    g = K.Geo()
    hx, hy, zf, h, zr = 6.25, 3.15, 1.2, 4.0, 6.6
    K.box(g, (-hx - 0.15, -hy - 0.15, 0), (hx + 0.15, hy + 0.15, zf), STONE, 0.44 + jit(rng, 0.03), skip=('-z',))
    K.box(g, (-hx, -hy, zf), (hx, hy, h), WOOD, 0.5, skip=('-z', '+z'))
    for z0, z1 in ((zf, zf + 0.18), (h - 0.25, h)):                                            # sill and wall plate
        K.box(g, (-hx - 0.08, -hy - 0.08, z0), (hx + 0.08, hy + 0.08, z1), DWOOD, 0.4, skip=('-z', '+z'))
    for x in (-hx, hx):
        for y in (-hy, hy):
            K.box(g, (x - 0.13, y - 0.13, zf), (x + 0.13, y + 0.13, h), DWOOD, 0.42, skip=('-z', '+z'))
    for x in (-3.6, 3.6):
        K.box(g, (x - 0.11, -hy - 0.12, zf + 0.18), (x + 0.11, -hy, h - 0.25), DWOOD, 0.44, skip=('+y', '-z', '+z'))
        K.box(g, (x - 0.11, hy, zf + 0.18), (x + 0.11, hy + 0.12, h - 0.25), DWOOD, 0.44, skip=('-y', '-z', '+z'))
    for x, sgn in ((-hx, -1), (hx, 1)):
        pts = [(x, -hy, h), (x, hy, h), (x, 0.0, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), WOOD, 0.46)
    gable_roof(g, -hx, hx, -hy, hy, eave_z(h, zr, hy, 0.4), zr, DWOOD, var=0.44, overhang=0.4)
    # the cupola on the ridge
    K.box(g, (-0.55, -0.55, 5.9), (0.55, 0.55, 7.0), WOOD, 0.48, skip=('-z', '+z'))
    g.pf([(-0.35, -0.57, 6.25), (0.35, -0.57, 6.25), (0.35, -0.57, 6.8), (-0.35, -0.57, 6.8)], INK, 0.5)
    g.pf([(0.35, 0.57, 6.25), (-0.35, 0.57, 6.25), (-0.35, 0.57, 6.8), (0.35, 0.57, 6.8)], INK, 0.5)
    pyramid(g, 0, 0, 0.75, 0.75, 7.0, 7.7, DWOOD, var=0.42)
    K.box(g, (4.4, 1.0, 4.5), (5.1, 1.7, 7.0), STONE, 0.46, skip=('-z',))                        # the chimney
    # the door up a step, windows
    K.box(g, (-1.6, -hy - 0.6, 0), (1.6, -hy - 0.15, 0.2), STONE, 0.4, skip=('-z', '+y'))
    town_door(g, T(0, -hy - 0.15, 0.2), w=2.0, h=2.8, double=True, back=0.17)
    for x in (-4.8, 4.8):
        town_window(g, T(x, -hy, 2.0), w=1.1, h=1.2)
    for side, at in (('-x', -hx), ('+x', hx)):
        town_window(g, on_face(side, at, 0.0, 2.0), w=1.1, h=1.2)
    # the banners: green cloth on a pole under the wall plate, a brass diamond on each
    for x in (-2.3, 2.3):
        K.box(g, (x - 0.62, -hy - 0.28, 3.55), (x + 0.62, -hy, 3.65), DWOOD, 0.4, skip=('+y',))
        yb = -hy - 0.16
        K.slab_xz(g, [(x, 1.85), (x + 0.5, 2.3), (x + 0.5, 3.55), (x - 0.5, 3.55), (x - 0.5, 2.3)], yb - 0.06, yb,
                  CLOTH2, 0.5, back=False)
        g.pf([(x, yb - 0.08, 2.5), (x + 0.24, yb - 0.08, 2.85), (x, yb - 0.08, 3.2), (x - 0.24, yb - 0.08, 2.85)],
             BRASS, 0.62)
    p = kit.add('vale_hall', g, budget=380, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [13.0, 7.0]


def house_tall(kit, mesh_id='vale_house_tall', roof=ROPE, roof_var=0.52, mirror=False):
    """A two-storey cottage, gable to the street: a stone ground floor, a plastered and timbered upper floor, a thatch
    roof, a chimney, a little pent roof over the door and a flower box (a second house so the streets don't repeat).
    Town review 2026-11-04: `mirror` builds its twin with the door at +1.1 instead of −1.1 (`vale_house_tall_m`);
    `roof` / `roof_var` the roof's slot (`vale_house_tall_b`: dark shingles)."""
    rng = R(mesh_id)
    g = K.Geo()
    gx, ux, gh, uh, zr = 2.8, 2.9, 2.7, 5.1, 7.4
    K.box(g, (-gx, -gx, 0), (gx, gx, gh), STONE, 0.48 + jit(rng, 0.03), skip=('-z', '+z'))
    K.box(g, (-ux - 0.05, -ux - 0.05, gh - 0.1), (ux + 0.05, ux + 0.05, gh + 0.15), DWOOD, 0.4, skip=('-z',))
    K.box(g, (-ux, -ux, gh + 0.15), (ux, ux, uh), BONE, 0.52 + jit(rng, 0.03), skip=('-z', '+z'))
    for x in (-ux, ux):
        for y in (-ux, ux):
            K.box(g, (x - 0.11, y - 0.11, gh + 0.15), (x + 0.11, y + 0.11, uh), WOOD, 0.42, skip=('-z', '+z'))
    K.box(g, (-ux - 0.07, -ux - 0.07, uh - 0.2), (ux + 0.07, ux + 0.07, uh + 0.02), WOOD, 0.4, skip=('-z', '+z'))
    g.pf([(-ux, -ux, uh), (ux, -ux, uh), (0.0, -ux, zr - 0.06)], BONE, 0.5)
    g.pf([(ux, ux, uh), (-ux, ux, uh), (0.0, ux, zr - 0.06)], BONE, 0.5)
    gable_roof_y(g, -ux, ux, -ux, ux, eave_z(uh + 0.02, zr, ux, 0.35), zr, roof, var=roof_var, overhang=0.35)
    K.box(g, (1.2, 0.8, 4.4), (1.9, 1.5, 8.1), STONE, 0.45, skip=('-z',))                        # the chimney
    K.box(g, (-1.7, -gx - 0.35, 0), (-0.5, -gx, 0.12), STONE, 0.38, skip=('-z', '+y'))          # the doorstep
    town_door(g, T(-1.1, -gx, 0.12), w=1.0, h=2.05)
    K.hull(g, [(-1.85, -gx, 2.45), (-0.35, -gx, 2.45), (-1.85, -gx, 2.57), (-0.35, -gx, 2.57),     # the door's hood
               (-1.85, -gx - 0.6, 2.22), (-0.35, -gx - 0.6, 2.22), (-1.85, -gx - 0.6, 2.32),
               (-0.35, -gx - 0.6, 2.32)], DWOOD, 0.42)
    town_window(g, T(1.2, -gx, 0.95), w=1.0, h=1.1, shutters=True)                            # W18-town: shutters
    for x in (-1.25, 1.25):
        town_window(g, T(x, -ux, 3.4), w=0.8, h=1.0, shutters=True)
    town_window(g, T(0, -ux, 5.55), w=0.6, h=0.6)
    for side, at in (('-x', -ux), ('+x', ux)):
        town_window(g, on_face(side, at, 0.0, 3.4), w=0.8, h=1.0, shutters=True)
    K.box(g, (0.72, -ux - 0.24, 3.12), (1.78, -ux, 3.32), DWOOD, 0.4, skip=('+y',))              # a flower box
    K.rock(g, rng, (1.25, -ux - 0.12, 3.36), (0.5, 0.11, 0.1), CLOTH1, n=6, var=0.55, flat=False)
    if mirror:
        g.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
    p = kit.add(mesh_id, g, budget=300, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [6.0, 6.0]
    p.info['door'] = [1.1 if mirror else -1.1, 0.12, gx]                    # the threshold's centre, game (x, y, z)
    p.info['chimney'] = [-1.55 if mirror else 1.55, 8.15, -1.15]            # the flue's top, game (x, y, z)
    return p


def guardhouse(kit):
    """A guardhouse: a squat stone block with a flat crenellated top, arrow slits, a plank door under a shield, a
    pennant on the roof."""
    rng = R('vale_guardhouse')
    g = K.Geo()
    hx, o, t, zc = 2.3, 2.42, 0.42, 3.6
    K.box(g, (-2.45, -2.45, 0), (2.45, 2.45, 0.35), STONE, 0.34, skip=('-z',))
    K.box(g, (-hx, -hx, 0.35), (hx, hx, 3.35), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    K.box(g, (-2.5, -2.5, 3.35), (2.5, 2.5, zc), STONE, 0.38, skip=('-z',))
    ring_wall(g, -o, -o, o, o, t, zc, 4.1, STONE, 0.5)
    merlons = [((sx * o, sx * (o - t)), (sy * o, sy * (o - t))) for sx in (-1, 1) for sy in (-1, 1)]
    for c in (-0.75, 0.75):
        merlons += [((c - 0.3, c + 0.3), (-o, -o + t)), ((c - 0.3, c + 0.3), (o - t, o)),
                    ((-o, -o + t), (c - 0.3, c + 0.3)), ((o - t, o), (c - 0.3, c + 0.3))]
    for (xa, xb), (ya, yb) in merlons:
        K.box(g, (min(xa, xb), min(ya, yb), 4.1), (max(xa, xb), max(ya, yb), 4.55), STONE, 0.52 + jit(rng, 0.04),
              skip=('-z',))
    town_door(g, T(0, -hx, 0.35), w=1.1, h=2.1, frame=STONE, fvar=0.7)
    for side, at, along in (('-y', -hx, -1.4), ('-y', -hx, 1.4), ('-x', -hx, 0.0), ('+x', hx, 0.0), ('+y', hx, 0.0)):
        mk = g.mark()
        g.pf([(-0.07, -0.02, 0), (0.07, -0.02, 0), (0.07, -0.02, 1.1), (-0.07, -0.02, 1.1)], INK, 0.5)   # arrow slits
        g.transform(on_face(side, at, along, 1.5), mk)
    y = -hx - 0.02                                                                              # the shield
    g.pf([(0.0, y, 2.68), (0.36, y, 2.86), (0.36, y, 3.28), (-0.36, y, 3.28), (-0.36, y, 2.86)], BRASS, 0.6)
    y = -hx - 0.04
    g.pf([(0.0, y, 2.77), (0.28, y, 2.91), (0.28, y, 3.2), (-0.28, y, 3.2), (-0.28, y, 2.91)], CLOTH2, 0.5)
    K.tube(g, (1.5, 1.5, zc), (1.5, 1.5, 6.0), 0.04, DWOOD, n=3, var=0.4, cap0=False, cap1=False)
    flag = [(1.5, 1.5, 5.95), (1.5, 1.5, 5.45), (0.75, 1.5, 5.7)]
    g.pf(flag, CLOTH2, 0.5)
    g.pf(list(reversed(flag)), CLOTH2, 0.44)
    p = kit.add('vale_guardhouse', g, budget=220, sheet={'az': 32, 'el': 20})
    p.info['footprint'] = [5.0, 5.0]


def palisade(kit):
    """A 4 m run of the town wall: seven upright logs, diamond in section so the joins read as round logs, sharpened
    at the top; it tiles end to end along x (the end logs' outer edges meet at x ±2)."""
    rng = R('vale_palisade')
    g = K.Geo()
    n, L, b = 7, 4.0, 0.25
    a = L / n / 2
    for i in range(n):
        xc = -L / 2 + a * (2 * i + 1)
        h = 2.42 + jit(rng, 0.08)
        apex = (xc, 0.0, h + 0.38 + jit(rng, 0.05))
        v = 0.42 + jit(rng, 0.07)
        r0 = [(xc, -b, 0.0), (xc + a, 0.0, 0.0), (xc, b, 0.0), (xc - a, 0.0, 0.0)]
        r1 = [(x, y, h) for x, y, _ in r0]
        for k in range(4):
            k2 = (k + 1) % 4
            g.pf([r0[k], r0[k2], r1[k2], r1[k]], DWOOD, v)
            g.pf([r1[k], r1[k2], apex], WOOD, 0.5 + jit(rng, 0.05))
    p = kit.add('vale_palisade', g, budget=90, sheet={'az': 30, 'el': 18},
                bake={'ground': 0.0, 'occluders': [('vale_palisade', (-L, 0, 0)), ('vale_palisade', (L, 0, 0))]})
    p.info['span'] = L
    p.info['footprint'] = [L, 2 * b]


def wall_tower(kit):
    """A timber watchtower for the town wall's corners and gates: a braced plank base, four corner posts carrying a
    railed lookout platform and a shingle pyramid roof, a pennant on top."""
    rng = R('vale_wall_tower')
    g = K.Geo()
    b, zp, zr0, zr1 = 1.3, 3.6, 5.6, 6.9
    K.box(g, (-b, -b, 0), (b, b, zp), DWOOD, 0.44 + jit(rng, 0.03), skip=('-z', '+z'))
    for side, at in (('-y', -b), ('+y', b), ('-x', -b), ('+x', b)):
        m = on_face(side, at, 0.0, 0.0)
        flat_strip(g, m, (-1.1, 0.3), (1.1, 3.3), 0.16, WOOD, 0.5, y=-0.015)
        flat_strip(g, m, (1.1, 0.3), (-1.1, 3.3), 0.16, WOOD, 0.46, y=-0.03)
    for x in (-b - 0.02, b + 0.02):
        for y in (-b - 0.02, b + 0.02):
            K.box(g, (x - 0.17, y - 0.17, 0), (x + 0.17, y + 0.17, zr0), WOOD, 0.42, skip=('-z', '+z'))
    K.box(g, (-1.65, -1.65, zp), (1.65, 1.65, zp + 0.2), WOOD, 0.46)
    ring_wall(g, -1.6, -1.6, 1.6, 1.6, 0.12, zp + 0.2, zp + 1.15, WOOD, 0.5)
    pyramid(g, 0, 0, 1.95, 1.95, zr0, zr1, DWOOD, var=0.44)
    K.tube(g, (0, 0, zr1 - 0.2), (0, 0, zr1 + 0.9), 0.035, DWOOD, n=3, var=0.4, cap0=False, cap1=False)
    flag = [(0.0, 0.0, zr1 + 0.85), (0.0, 0.0, zr1 + 0.45), (0.7, 0.0, zr1 + 0.65)]
    g.pf(flag, CLOTH2, 0.5)
    g.pf(list(reversed(flag)), CLOTH2, 0.44)
    p = kit.add('vale_wall_tower', g, budget=200, sheet={'az': 32, 'el': 16})
    p.info['footprint'] = [3.0, 3.0]


def gate_arch(kit):
    """The overhead part of a town gate: a heavy lintel 8 m long at 4.2–4.7 m under a plank parapet and a little
    shingle roof, a lantern hung over the road — no posts (the towers either side carry it), so no collider."""
    rng = R('vale_gate_arch')
    g = K.Geo()
    L, zr = 4.0, 5.6
    K.box(g, (-L, -0.35, 4.2), (L, 0.35, 4.7), DWOOD, 0.42 + jit(rng, 0.03), skip=('+z',))
    K.box(g, (-L, -0.55, 4.7), (L, 0.55, 5.1), WOOD, 0.46, skip=('+z',))
    for x, sgn in ((-L, -1), (L, 1)):
        pts = [(x, -0.55, 5.1), (x, 0.55, 5.1), (x, 0.0, zr - 0.05)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), WOOD, 0.44)
    gable_roof(g, -L, L, -0.55, 0.55, eave_z(5.1, zr, 0.55, 0.2, 0.1), zr, DWOOD, var=0.44, overhang=0.2, thick=0.1)
    K.box(g, (-0.03, -0.03, 3.88), (0.03, 0.03, 4.2), IRON, 0.44, skip=('-z', '+z'))            # the lantern's rod
    K.box(g, (-0.15, -0.15, 3.32), (0.15, 0.15, 3.72), GLOW, 0.5, skip=('-z', '+z'))
    pyramid(g, 0, 0, 0.2, 0.2, 3.72, 3.92, IRON, var=0.42)
    g.pf([(-0.17, -0.17, 3.32), (-0.17, 0.17, 3.32), (0.17, 0.17, 3.32), (0.17, -0.17, 3.32)], IRON, 0.4)
    p = kit.add('vale_gate_arch', g, budget=120, sheet={'az': 30, 'el': 16})
    kit.light(p, (0, 0, 3.52), 'lamp')
    p.info['footprint'] = [2 * L, 1.5]
    p.info['span'] = 2 * L
    p.info['no_collider'] = True


def fountain(kit):
    """A round stone fountain: a stepped basin of water, a column carrying a shallow bowl, four thin falls of water."""
    rng = R('vale_fountain')
    g = K.Geo()
    prof = [(1.78, 0.0), (1.78, 0.14), (1.6, 0.14), (1.6, 0.62), (1.36, 0.62), (1.36, 0.4)]
    band_var = [0.38, 0.42, 0.5, 0.64, 0.44]
    K.lathe(g, prof, 10, STONE, lambda b, k: band_var[b] + jit(rng, 0.04), smooth=0, cap0=False, cap1=False)
    K.disc(g, 1.36, 10, WATER, z=0.48, var=0.5)
    K.tube(g, (0, 0, 0.48), (0, 0, 1.4), 0.2, STONE, n=6, var=0.5, smooth=65, cap0=False, cap1=False)
    K.lathe(g, [(0.2, 1.3), (0.72, 1.56), (0.72, 1.68), (0.58, 1.68)], 8, STONE,
            lambda b, k: (0.46, 0.52, 0.64)[b], smooth=0, cap0=False, cap1=False)
    K.disc(g, 0.58, 8, WATER, z=1.64, var=0.55)
    K.lathe(g, [(0.14, 1.64), (0.08, 2.0), (0.0, 2.28)], 6, STONE, 0.56, smooth=0, cap0=False)
    for a in (45, 135, 225, 315):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        K.tube(g, (0.7 * c, 0.7 * s, 1.6), (1.12 * c, 1.12 * s, 0.48), 0.035, WATER, n=3, var=0.7, cap0=False,
               cap1=False)
    p = kit.add('vale_fountain', g, budget=220, sheet={'az': 30, 'el': 24})
    p.info['footprint'] = [3.6, 3.6]


def lamppost(kit):
    """A street lamp: an iron post on a stone foot, a glowing lantern under a pointed iron cap (a warm light)."""
    g = K.Geo()
    K.box(g, (-0.16, -0.16, 0), (0.16, 0.16, 0.3), STONE, 0.44, skip=('-z',))
    K.tube(g, (0, 0, 0.3), (0, 0, 2.58), 0.055, IRON, n=4, var=0.46, cap0=False, cap1=False)
    K.box(g, (-0.18, -0.18, 2.55), (0.18, 0.18, 2.62), IRON, 0.42)
    K.box(g, (-0.14, -0.14, 2.62), (0.14, 0.14, 2.96), GLOW, 0.5, skip=('-z', '+z'))
    pyramid(g, 0, 0, 0.2, 0.2, 2.96, 3.22, IRON, var=0.42)
    K.tube(g, (0, 0, 3.18), (0, 0, 3.34), 0.025, IRON, n=3, var=0.4, cap0=False)
    p = kit.add('vale_lamppost', g, budget=60, sheet={'az': 30, 'el': 16})
    kit.light(p, (0, 0, 2.8), 'lamp')


def barrel(kit):
    rng = R('vale_barrel')
    g = K.Geo()
    K.lathe(g, [(0.31, 0.0), (0.36, 0.14), (0.37, 0.66), (0.31, 0.8)], 7, lambda b, k: IRON if b != 1 else WOOD,
            lambda b, k: 0.46 + jit(rng, 0.06), smooth=0, cap0=False, cap_slot=DWOOD)
    kit.add('vale_barrel', g, budget=50, sheet={'az': 30, 'el': 24})


def crate(kit):
    g = K.Geo()
    s = 0.35
    K.box(g, (-s, -s, 0), (s, s, 0.7), WOOD, 0.5, skip=('-z',))
    for side, at in (('-y', -s), ('+y', s), ('-x', -s), ('+x', s)):
        flat_strip(g, on_face(side, at, 0.0, 0.0), (-0.28, 0.08), (0.28, 0.62), 0.1, DWOOD, 0.42, y=-0.012)
    for y0, y1 in ((-0.26, -0.15), (0.15, 0.26)):
        g.pf([(-s + 0.03, y0, 0.712), (s - 0.03, y0, 0.712), (s - 0.03, y1, 0.712), (-s + 0.03, y1, 0.712)], DWOOD, 0.42)
    kit.add('vale_crate', g, budget=24, sheet={'az': 30, 'el': 24})


def hen_coop(kit):
    """A hen house: a little plank coop on four short legs, a sloped plank roof, a small door on the front and a
    pop-hole on its side with a cleated ramp down to the ground."""
    g = K.Geo()
    x0, x1, y0, y1, zb, zf, zk = -1.05, 0.35, -0.62, 0.62, 0.45, 1.45, 1.22
    K.hull(g, [(x0, y0, zb), (x1, y0, zb), (x1, y1, zb), (x0, y1, zb),
               (x0, y0, zf), (x1, y0, zf), (x1, y1, zk), (x0, y1, zk)], WOOD, 0.5)
    slope = (zk - zf) / (y1 - y0)
    K.hull(g, [(x, y, zf + slope * (y - y0) + dz) for x in (-1.2, 0.5) for y in (-0.9, 0.9) for dz in (0.0, 0.07)],
           DWOOD, 0.44)
    for x in (x0 + 0.08, x1 - 0.08):
        for y in (y0 + 0.08, y1 - 0.08):
            K.box(g, (x - 0.045, y - 0.045, 0), (x + 0.045, y + 0.045, zb), DWOOD, 0.4, skip=('-z', '+z'))
    yf = y0 - 0.01
    g.pf([(-0.8, yf, 0.58), (-0.25, yf, 0.58), (-0.25, yf, 1.28), (-0.8, yf, 1.28)], WOOD, 0.3)         # door frame
    yf -= 0.01
    g.pf([(-0.74, yf, 0.62), (-0.31, yf, 0.62), (-0.31, yf, 1.22), (-0.74, yf, 1.22)], DWOOD, 0.4)      # the door
    yf -= 0.01
    g.pf([(-0.42, yf, 0.9), (-0.36, yf, 0.9), (-0.36, yf, 0.96), (-0.42, yf, 0.96)], IRON, 0.5)
    xf = x1 + 0.01
    g.pf([(xf, -0.15, 0.5), (xf, 0.15, 0.5), (xf, 0.15, 0.82), (xf, -0.15, 0.82)], INK, 0.5)           # pop-hole
    K.hull(g, [(x1, -0.2, 0.48), (x1, 0.2, 0.48), (x1, -0.2, 0.44), (x1, 0.2, 0.44),
               (1.2, -0.2, 0.04), (1.2, 0.2, 0.04), (1.2, -0.2, 0.0), (1.2, 0.2, 0.0)], WOOD, 0.46)
    for t in (0.25, 0.5, 0.75):
        x = x1 + (1.2 - x1) * t
        z = 0.48 + (0.04 - 0.48) * t + 0.012
        g.pf([(x - 0.025, -0.18, z + 0.013), (x + 0.025, -0.18, z - 0.013), (x + 0.025, 0.18, z - 0.013),
              (x - 0.025, 0.18, z + 0.013)], DWOOD, 0.4)
    p = kit.add('vale_coop', g, budget=140, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = [2.4, 1.8]


def minecart(kit):
    """A mine cart: a tapered plank tub with two iron bands, heaped with ore, on four iron wheels on a short length of
    track (three sleepers, two rails) running along x."""
    rng = R('vale_minecart')
    g = K.Geo()
    for x in (-0.8, 0.0, 0.8):
        K.box(g, (x - 0.1, -0.6, 0), (x + 0.1, 0.6, 0.08), DWOOD, 0.4 + jit(rng, 0.05), skip=('-z',))
    for y in (-0.37, 0.37):
        K.box(g, (-1.2, y - 0.03, 0.08), (1.2, y + 0.03, 0.16), IRON, 0.5, skip=('-z', '-x', '+x'))
    zb, zt = 0.28, 0.85

    def tub(z0, z1, grow, slot, var):
        pts = []
        for z in (z0, z1):
            f = (z - zb) / (zt - zb)
            hx, hy = 0.5 + 0.12 * f + grow, 0.32 + 0.1 * f + grow
            pts += [(-hx, -hy, z), (hx, -hy, z), (hx, hy, z), (-hx, hy, z)]
        K.hull(g, pts, slot, var)
    tub(zb, zt, 0.0, lambda c, n: INK if n.z > 0.9 else WOOD, 0.46)
    for z in (0.36, 0.7):
        tub(z, z + 0.08, 0.02, IRON, 0.44)
    K.rock(g, rng, (0, 0, 0.82), (0.5, 0.32, 0.16), STONE, n=8, var=0.42)                       # the ore
    for x in (-0.32, 0.32):
        K.disc(g, 0.15, 6, IRON, var=0.4, m=T(x, -0.37, 0.31) @ Rx(90))
        K.disc(g, 0.15, 6, IRON, var=0.4, m=T(x, 0.37, 0.31) @ Rx(-90))
    p = kit.add('vale_minecart', g, budget=110, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = [2.4, 1.2]


def mine_frame(kit):
    """A mine's mouth: a dark adit in a mass of rock, framed by two timber posts, a lintel and knee braces, a lantern
    on the left post, rubble at its foot (the front, −Y, is the opening)."""
    rng = R('vale_mine_frame')
    g = K.Geo()
    for (c, s, n, v) in (((-2.0, 1.0), (1.05, 1.45, 2.6), 13, 0.46), ((2.0, 1.05), (1.0, 1.4, 2.4), 13, 0.5),
                         ((0.0, 2.2), (1.8, 1.1, 2.2), 10, 0.4)):
        K.rock(g, rng, (c[0], c[1], 0.55 * s[2] - 0.02), s, STONE, n=n, var=v)
    K.rock(g, rng, (0.0, 1.1, 4.0), (1.9, 1.35, 1.0), STONE, n=12, var=0.44, flat=False)
    K.rock(g, rng, (-1.9, -0.75, 0.09), (0.32, 0.26, 0.2), STONE, n=7, var=0.4)                # rubble
    K.rock(g, rng, (2.0, -0.6, 0.07), (0.26, 0.22, 0.16), STONE, n=6, var=0.44)
    K.box(g, (-1.25, -0.42, 0), (1.25, 1.9, 2.95), INK, 0.5, skip=('-z', '+y'))                   # the dark adit
    for x in (-1.32, 1.32):
        K.box(g, (x - 0.15, -0.62, 0), (x + 0.15, -0.32, 2.95), WOOD, 0.42 + jit(rng, 0.04), skip=('-z',))
    K.box(g, (-1.8, -0.68, 2.95), (1.8, -0.28, 3.32), WOOD, 0.44)                               # the lintel
    for sgn in (-1, 1):
        K.tube(g, (sgn * 1.17, -0.47, 2.3), (sgn * 0.6, -0.47, 2.95), 0.07, WOOD, n=4, var=0.4, cap0=False,
               cap1=False)
    K.box(g, (-1.43, -0.84, 1.95), (-1.21, -0.62, 2.25), GLOW, 0.5, skip=('-z',))               # the lantern
    pyramid(g, -1.32, -0.73, 0.14, 0.14, 2.25, 2.4, IRON, var=0.42, under=False)
    fp = recentre(g)
    p = kit.add('vale_mine_frame', g, budget=220, sheet={'az': 28, 'el': 16})
    p.info['footprint'] = fp


def bush(kit):
    """A plain round leafy bush (no berries): three overlapping leaf masses on flat feet."""
    rng = R('vale_bush')
    g = K.Geo()
    for (x, y, sx, sy, sz, n, slot, v) in ((0.0, 0.0, 0.62, 0.58, 0.7, 13, CLOTH1, 0.48),
                                           (0.3, -0.2, 0.38, 0.34, 0.4, 8, CLOTH1, 0.58),
                                           (-0.32, 0.2, 0.36, 0.34, 0.38, 8, CLOTH2, 0.52)):
        K.rock(g, rng, (x, y, 0.55 * sz - 0.02), (sx, sy, sz), slot, n=n, var=v)   # flat feet just under the ground
    kit.add('vale_bush', g, budget=60, sheet={'az': 30, 'el': 20})


# Ground loot: what a monster drops, left where it fell. Small, but chunky and pale or bright so it reads on grass
# from the follow camera.
def loot_sack(kit):
    """A dropped loot sack: a pale canvas bag tied at the neck, three coins spilled beside it (one catching the light)."""
    rng = R('vale_loot_sack')
    g = K.Geo()
    K.rock(g, rng, (0, 0, 0.105), (0.21, 0.19, 0.19), BONE, n=9, var=0.48)
    K.lathe(g, [(0.085, 0.22), (0.075, 0.3), (0.13, 0.41), (0.0, 0.45)], 5, lambda b, k: DWOOD if b == 0 else BONE,
            0.52, smooth=0, cap0=False)
    for (x, y, r, slot, rot) in ((0.25, -0.12, 0.06, BRASS, 12), (0.2, -0.25, 0.055, GLOW, -18),
                                 (-0.22, -0.15, 0.055, BRASS, 25)):
        K.disc(g, r, 6, slot, var=0.62, m=T(x, y, 0.02) @ Rx(rot))
    kit.add('vale_loot_sack', g, budget=60, sheet={'az': 30, 'el': 30})


def loot_bones(kit):
    """Dropped bones: a skull with dark sockets beside three long bones with knobbed ends (one snapped)."""
    rng = R('vale_loot_bones')
    g = K.Geo()
    K.rock(g, rng, (0.06, 0.04, 0.06), (0.11, 0.13, 0.11), BONE, n=8, var=0.62)
    for x in (0.02, 0.1):
        K.rock(g, rng, (x, -0.085, 0.085), (0.026, 0.026, 0.026), INK, n=4, var=0.5, flat=False)
    for (a, b, knobs) in (((-0.24, -0.12), (0.12, 0.17), 2), ((-0.22, 0.14), (0.18, -0.1), 2),
                          ((0.06, -0.24), (-0.14, -0.08), 1)):
        K.tube(g, (a[0], a[1], 0.03), (b[0], b[1], 0.03), 0.028, BONE, n=3, var=0.58, cap0=False, cap1=False)
        for e in (a, b)[:knobs]:
            K.rock(g, rng, (e[0], e[1], 0.04), (0.045, 0.045, 0.04), BONE, n=4, var=0.6, flat=False)
    kit.add('vale_loot_bones', g, budget=60, sheet={'az': 30, 'el': 30})


def loot_coins(kit):
    """A dropped pile of coins: a low heap with loose coins on and around it, two of them catching the light."""
    rng = R('vale_loot_coins')
    g = K.Geo()
    K.lathe(g, [(0.17, 0.0), (0.11, 0.055), (0.0, 0.1)], 7, lambda b, k: GLOW if b == 1 and k % 3 == 0 else BRASS,
            lambda b, k: 0.5 + jit(rng, 0.16), smooth=0, cap0=False)
    for (x, y, z, rx, ry, slot) in ((0.04, -0.05, 0.085, 18, 6, GLOW), (-0.07, 0.03, 0.075, -10, 22, BRASS),
                                    (0.2, -0.08, 0.012, 6, 0, BRASS), (-0.15, -0.15, 0.012, -8, 4, GLOW),
                                    (0.12, 0.15, 0.03, 15, -20, BRASS)):
        K.disc(g, 0.05, 6, slot, var=0.64, m=T(x, y, z) @ Rx(rx) @ Ry(ry))
    kit.add('vale_loot_coins', g, budget=50, sheet={'az': 30, 'el': 30})


# ====================================================================== shops and workshops (Phase W8)
# The owner's ask: shops where the hero buys basic supplies, and a building for each crafting skill where its equipment
# is used. A shop is closed like the general store (`shop`, a bigger sign board, its own awning, roof and icon, the
# lean walls). A workshop is an OPEN-FRONTED shell the hero walks into; its equipment is placed inside as separate
# pieces, each standing on the ground with its working side (where the hero stands) to the front, −Y.
SIGN = (2.25, 3.25, 1.8, 2.62)      # a shop's sign board (x0, x1, z0, z1): a little bigger than the store's, for its icon


def plate(g, pts, y, slot, var=0.5):
    """A flat mark on a face at y, facing −Y: `pts` are (x, z), counter-clockwise seen from the front (→ its face)."""
    return g.pf([(x, y, z) for x, z in pts], slot, var)


def stroke(g, a, b, width, y, slot, var=0.5):
    """A straight flat stroke from a to b ((x, z)) on a face at y, facing −Y (2 tris)."""
    flat_strip(g, Matrix.Identity(4), a, b, width, slot, var, y=y)


def strip_xy(g, a, b, width, z, slot, var=0.5):
    """A flat strip lying at height z from a to b ((x, y)), facing up (2 tris): a blade on a table."""
    d = Vector((b[0] - a[0], b[1] - a[1])).normalized()
    n = Vector((-d.y, d.x)) * (width / 2)
    g.pf([(a[0] - n.x, a[1] - n.y, z), (b[0] - n.x, b[1] - n.y, z), (b[0] + n.x, b[1] + n.y, z),
          (a[0] + n.x, a[1] + n.y, z)], slot, var)


def card(g, pts, slot, var=0.5, gap=0.01):
    """A thin two-sided plate (a blade, an axe head): the polygon `pts`, counter-clockwise from its front, and its back
    a hair behind (2 × (n − 2) tris)."""
    a, b, c = (Vector(p) for p in pts[:3])
    n = (b - a).cross(c - a).normalized()
    g.pf(pts, slot, var)
    g.pf([tuple(Vector(p) - n * gap) for p in reversed(pts)], slot, max(0.0, var - 0.06))


def plan_size(g):
    """[w, d] of the rectangle centred on the origin that holds the piece's plan."""
    lo, hi = g.bounds()
    return [round(2 * max(-lo.x, hi.x), 2), round(2 * max(-lo.y, hi.y), 2)]


def workshop(kit, mesh_id, stone=False, budget=260):
    """A workshop shell, 8 × 6 m, OPEN at the front (−Y) so the hero walks in to the equipment placed inside (the shell
    is empty): a floor a step up, a back wall and two side walls, a front beam across the whole opening on corner
    posts, a gable roof with its ridge front to back so the follow camera sees in under the open front gable (a
    king-post truss in it), a few tools on a batten on the back wall, a sign with a hammer on an iron bracket off the
    front-left post. The timber one: plank walls on a sandy earth floor, a thatch roof. stone=True, its sibling, so
    two neighbours don't look cloned: a stone back wall with a chimney, stone piers, plastered and timbered side walls
    on stone footings with a window each, a flagged floor, a slate roof."""
    rng = R(mesh_id)
    g = K.Geo()
    w, d, h, zr = 8.0, 6.0, 3.0, 5.4
    hx, hy = w / 2, d / 2
    zf = 0.1 if stone else 0.08                                                               # the floor's top
    # the floor: flags, or for the timber one swept sandy earth (pale, so the equipment reads in the roof's shade)
    K.box(g, (-hx, -hy, -0.25), (hx, hy, zf), STONE if stone else BRASS, (0.36 if stone else 0.44) + jit(rng, 0.03),
          skip=('-z',))
    tb = 0.4 if stone else 0.22                                                               # the back wall
    if stone:
        K.box(g, (-hx, hy - tb, zf), (hx, hy, h), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
        for sgn in (-1, 1):
            x0, x1 = sorted((sgn * hx, sgn * (hx - 0.22)))
            K.box(g, (x0 - 0.04, -hy + 0.2, zf), (x1 + 0.04, hy - tb, 0.75), STONE, 0.44, skip=('-z', '-y', '+y'))
            K.box(g, (x0, -hy + 0.2, 0.75), (x1, hy - tb, h - 0.24), BONE, 0.5 + jit(rng, 0.04),
                  skip=('-z', '+z', '-y', '+y'))
            side = '-x' if sgn < 0 else '+x'
            m = on_face(side, sgn * hx, 0.0, 0.0)
            for a in (-1.55, 1.55):                                                           # timber studs
                flat_strip(g, m, (a, 0.75), (a, h - 0.24), 0.16, WOOD, 0.44, y=-0.012)
            town_window(g, on_face(side, sgn * hx, 0.0, 1.35), w=0.8, h=0.8)
            xc = sgn * (hx - 0.15)                                                            # a stone pier in front
            K.box(g, (xc - 0.22, -hy - 0.04, zf), (xc + 0.22, -hy + 0.4, h - 0.26), STONE, 0.56, skip=('-z',))
        K.box(g, (1.6, hy - 0.3, 1.2), (2.4, hy + 0.5, zr + 0.7), STONE, 0.46, skip=('-z',))     # the chimney
        K.box(g, (1.52, hy - 0.38, zr + 0.7), (2.48, hy + 0.58, zr + 0.85), STONE, 0.38, skip=('-z',))
        g.pf([(1.75, hy - 0.15, zr + 0.86), (2.25, hy - 0.15, zr + 0.86), (2.25, hy + 0.35, zr + 0.86),
              (1.75, hy + 0.35, zr + 0.86)], INK, 0.5)                                          # its flue
    else:
        K.box(g, (-hx, hy - tb, zf), (hx, hy, h - 0.24), WOOD, 0.48 + jit(rng, 0.03), skip=('-z', '+z', '-x', '+x'))
        for sgn in (-1, 1):
            x0, x1 = sorted((sgn * hx, sgn * (hx - 0.22)))
            K.box(g, (x0, -hy + 0.2, zf), (x1, hy - tb, h - 0.24), WOOD, 0.46 + jit(rng, 0.03),
                  skip=('-z', '+z', '-y', '+y'))
            xc = sgn * (hx - 0.12)
            for y in (-hy + 0.14, hy - 0.12):                                                 # corner posts
                K.box(g, (xc - 0.16, y - 0.16, zf), (xc + 0.16, y + 0.16, h - 0.24), DWOOD, 0.42, skip=('-z', '+z'))
        K.box(g, (-hx - 0.06, hy - 0.26, h - 0.24), (hx + 0.06, hy + 0.06, h), DWOOD, 0.42, skip=('-z', '+z'))
        for side, at, half in (('-x', -hx, hy - 0.3), ('+x', hx, hy - 0.3), ('+y', hy, hx - 0.3)):   # plank seams
            m = on_face(side, at, 0.0, 0.0)
            for z in (0.75, 1.45, 2.15):
                flat_strip(g, m, (-half, z), (half, z), 0.05, DWOOD, 0.34, y=-0.01)
    for sgn in (-1, 1):                                                                       # the side plates
        x0, x1 = sorted((sgn * (hx + 0.06), sgn * (hx - 0.26)))
        K.box(g, (x0, -hy + 0.26, h - 0.24), (x1, hy - (tb if stone else 0.26), h), DWOOD, 0.42,
              skip=('-z', '+z', '-y', '+y'))
    K.box(g, (-hx - 0.1, -hy - 0.06, h - 0.26), (hx + 0.1, -hy + 0.26, h), DWOOD, 0.42)         # the front beam
    ze = eave_z(h, zr, hx, 0.4)
    gable_roof_y(g, -hx, hx, -hy, hy, ze, zr, IRON if stone else ROPE, var=0.48 if stone else 0.5, overhang=0.4)
    gs = STONE if stone else WOOD
    g.pf([(hx, hy, h), (-hx, hy, h), (0.0, hy, zr - 0.06)], gs, 0.5)                           # the back gable
    g.pf([(-hx, hy - tb, h), (hx, hy - tb, h), (0.0, hy - tb, zr - 0.06)], gs, 0.42)          # and inside it

    def under(x):                                                                              # the roof's underside
        return ze + (zr - ze) * (hx + 0.4 - abs(x)) / (hx + 0.4) - 0.14
    yt = -hy + 0.1                                                                             # the open gable's truss
    K.box(g, (-0.1, yt - 0.1, h), (0.1, yt + 0.1, zr - 0.2), DWOOD, 0.44, skip=('-z', '+z'))
    for sgn in (-1, 1):
        K.tube(g, (sgn * 0.08, yt, h + 0.1), (sgn * 1.9, yt, under(1.9) - 0.04), 0.07, DWOOD, n=4, var=0.42,
               cap0=False, cap1=False)
    # tools on a batten on the back wall's inner face: a saw, a hammer, tongs, a coil of rope
    yi = hy - tb
    K.box(g, (-1.6, yi - 0.08, 1.95), (1.6, yi, 2.05), DWOOD, 0.42, skip=('+y',))
    yw = yi - 0.09
    plate(g, [(-1.3, 1.2), (-1.14, 1.2), (-1.08, 1.8), (-1.32, 1.8)], yw, BMETAL, 0.6)
    plate(g, [(-1.34, 1.8), (-1.06, 1.8), (-1.06, 1.97), (-1.34, 1.97)], yw, WOOD, 0.4)
    stroke(g, (-0.5, 1.38), (-0.5, 1.96), 0.05, yw, WOOD, 0.46)
    plate(g, [(-0.63, 1.3), (-0.37, 1.3), (-0.37, 1.42), (-0.63, 1.42)], yw - 0.004, IRON, 0.5)
    stroke(g, (0.3, 1.25), (0.38, 1.96), 0.04, yw, IRON, 0.5)
    stroke(g, (0.52, 1.25), (0.42, 1.96), 0.04, yw - 0.004, IRON, 0.5)
    K.disc(g, 0.18, 6, ROPE, var=0.5, m=T(1.15, yw, 1.72) @ Rx(90))
    # the sign: an iron arm off the front-left post, a board with a hammer on it
    px, yf = -(hx - (0.15 if stone else 0.12)), -hy - (0.04 if stone else 0.02)
    K.box(g, (px - 0.05, -hy - 0.95, 2.5), (px + 0.05, yf, 2.6), IRON, 0.46, skip=('+y',))
    K.tube(g, (px, yf, 2.02), (px, -hy - 0.62, 2.52), 0.025, IRON, n=4, var=0.46, cap0=False, cap1=False)
    K.box(g, (px - 0.42, -hy - 0.93, 1.76), (px + 0.42, -hy - 0.85, 2.5), DWOOD, 0.44)
    yb = -hy - 0.94
    a, b = Vector((px - 0.2, 1.88)), Vector((px + 0.1, 2.28))
    stroke(g, tuple(a), tuple(b), 0.07, yb, BRASS, 0.62)
    n = (b - a).normalized()
    n = Vector((-n.y, n.x)) * 0.16
    stroke(g, tuple(b - n), tuple(b + n), 0.12, yb - 0.005, BMETAL, 0.62)
    p = kit.add(mesh_id, g, budget=budget, sheet={'az': 22, 'el': 22})
    p.info['footprint'] = [w, d]
    p.info['open'] = True
    return p


def workbench(kit):
    """The crafting workbench (leather, cloth and gems): a sturdy table ~2 × 0.9 m with a tan hide spread on its left
    half and hanging over the front edge, shears on the hide, a mallet, a little tray of gems catching the light, a
    stool pushed half under the front."""
    rng = R('vale_workbench')
    g = K.Geo()
    L, D, zt = 1.0, 0.45, 0.84
    K.box(g, (-L, -D, zt), (L, D, zt + 0.1), WOOD, 0.5, skip=('-z',))
    for x in (-L + 0.13, L - 0.13):
        for y in (-D + 0.11, D - 0.11):
            K.box(g, (x - 0.07, y - 0.07, 0), (x + 0.07, y + 0.07, zt), DWOOD, 0.42, skip=('-z', '+z'))
    K.box(g, (-L + 0.2, D - 0.15, 0.16), (L - 0.2, D - 0.07, 0.28), DWOOD, 0.38, skip=('-x', '+x'))   # a stretcher
    zs = zt + 0.105
    hide = [(-0.85, -0.45), (-0.2, -0.45), (-0.05, -0.1), (-0.15, 0.32), (-0.6, 0.38), (-0.92, 0.05)]
    g.pf([(x, y, zs) for x, y in hide], ROPE, 0.42)
    y = -D - 0.006
    g.pf([(-0.8, y, zt - 0.14), (-0.25, y, zt - 0.11), (-0.2, y, zs), (-0.85, y, zs)], ROPE, 0.36)     # its drape
    strip_xy(g, (-0.66, -0.26), (-0.3, 0.06), 0.04, zs + 0.006, BMETAL, 0.64)                        # the shears
    strip_xy(g, (-0.66, 0.02), (-0.3, -0.24), 0.04, zs + 0.009, BMETAL, 0.58)
    K.box(g, (0.28, 0.06, zt + 0.1), (0.52, 0.22, zt + 0.25), DWOOD, 0.44, skip=('-z',))          # the mallet
    K.tube(g, (0.36, 0.06, zt + 0.17), (0.18, -0.3, zt + 0.13), 0.025, WOOD, n=4, var=0.56, cap0=False, cap1=False)
    K.box(g, (0.6, -0.32, zt + 0.1), (0.9, -0.1, zt + 0.15), DWOOD, 0.38, skip=('-z',))           # the gem tray
    for (x, yy) in ((0.68, -0.2), (0.81, -0.24)):
        K.rock(g, rng, (x, yy, zt + 0.19), (0.045, 0.045, 0.05), GLOW, n=4, var=0.55, flat=False)
    sx, sy = 0.45, -0.42                                                                          # the stool
    K.box(g, (sx - 0.16, sy - 0.16, 0.46), (sx + 0.16, sy + 0.16, 0.52), WOOD, 0.52, skip=('-z',))
    for a in (90, 210, 330):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        K.tube(g, (sx + 0.1 * c, sy + 0.1 * s, 0.46), (sx + 0.16 * c, sy + 0.16 * s, 0.0), 0.025, DWOOD, n=3,
               var=0.4, cap0=False, cap1=False)
    fp = plan_size(g)
    p = kit.add('vale_workbench', g, budget=130, sheet={'az': 28, 'el': 30})
    p.info['node'] = True
    p.info['footprint'] = fp


def tanning_rack(kit):
    """A tanning rack (decor): an easel-like frame leaning back on a prop, a tan hide laced into it with dark thongs."""
    rng = R('vale_tanning_rack')
    g = K.Geo()
    mk = g.mark()
    W = 0.7
    for x in (-W, W):
        K.box(g, (x - 0.06, -0.06, 0), (x + 0.06, 0.06, 2.0), WOOD, 0.44 + jit(rng, 0.04), skip=('-z',))
    for z in (0.32, 1.82):
        K.box(g, (-W - 0.06, -0.05, z), (W + 0.06, 0.05, z + 0.1), DWOOD, 0.42, skip=('-x', '+x'))
    hide = [(-0.5, 0.52), (0.5, 0.52), (0.58, 1.12), (0.48, 1.72), (-0.48, 1.72), (-0.58, 1.12)]
    plate(g, hide, -0.012, ROPE, 0.46)
    g.pf([(x, 0.012, z) for x, z in reversed(hide)], ROPE, 0.38)
    for a, b in (((-0.5, 0.52), (-W, 0.42)), ((0.5, 0.52), (W, 0.42)), ((0.48, 1.72), (W, 1.82)),
                 ((-0.48, 1.72), (-W, 1.82))):
        stroke(g, a, b, 0.03, -0.02, DWOOD, 0.36)
    g.transform(Rx(-9), mk)                                                                   # the frame leans back
    K.tube(g, (0, 0.34, 1.8), (0, 0.95, 0.0), 0.04, DWOOD, n=3, var=0.4, cap0=False, cap1=False)   # the prop
    p = kit.add('vale_tanning_rack', g, budget=60, sheet={'az': 30, 'el': 16})
    p.info['footprint'] = plan_size(g)


def spinning_wheel(kit):
    """A small spinning wheel (decor): a bench on two splayed legs, a spoked wheel standing between two uprights over
    its right end (the uprights are its other legs), a pale twist of wool on the distaff at its left end."""
    rng = R('vale_spinning_wheel')
    g = K.Geo()
    K.box(g, (-0.5, -0.11, 0.32), (0.5, 0.11, 0.4), WOOD, 0.48 + jit(rng, 0.04), skip=('-z',))
    for y in (-0.08, 0.08):
        K.tube(g, (-0.4, y, 0.33), (-0.5, y * 2.2, 0.0), 0.025, DWOOD, n=3, var=0.4, cap0=False, cap1=False)
    cx, cz, r0, r1 = 0.24, 0.86, 0.36, 0.43
    for y in (-0.07, 0.07):
        K.tube(g, (cx, y, 0.0), (cx, y, cz + 0.06), 0.022, DWOOD, n=3, var=0.42, cap0=False, cap1=False)
    for k in range(8):                                                                         # the rim, both faces
        a0, a1 = math.radians(22.5 + 45 * k), math.radians(22.5 + 45 * (k + 1))
        q = [(cx + r0 * math.cos(a0), cz + r0 * math.sin(a0)), (cx + r1 * math.cos(a0), cz + r1 * math.sin(a0)),
             (cx + r1 * math.cos(a1), cz + r1 * math.sin(a1)), (cx + r0 * math.cos(a1), cz + r0 * math.sin(a1))]
        plate(g, q, -0.012, WOOD, 0.5)
        g.pf([(x, 0.012, z) for x, z in reversed(q)], WOOD, 0.44)
    for a in (0, 90):                                                                          # the spokes
        c, s = math.cos(math.radians(a)) * r0, math.sin(math.radians(a)) * r0
        K.tube(g, (cx - c, 0, cz - s), (cx + c, 0, cz + s), 0.018, DWOOD, n=3, var=0.44, cap0=False, cap1=False)
    K.tube(g, (-0.38, 0, 0.4), (-0.36, 0, 0.94), 0.065, BONE, r1=0.025, n=4, var=0.6, cap0=False)   # the wool
    p = kit.add('vale_spinning_wheel', g, budget=90, sheet={'az': 30, 'el': 16})
    p.info['footprint'] = plan_size(g)


def bow(g, m, slot=DWOOD):
    """A strung bow 1.45 m tall in the XZ plane, facing −Y and +Y, its foot at the origin, the belly toward +x (16
    tris)."""
    mk = g.mark()
    path = [(0.0, 0.0, 0.0), (0.14, 0.0, 0.42), (0.14, 0.0, 1.03), (0.0, 0.0, 1.45)]
    K.ribbon(g, path, 0.05, slot, 0.5, normal=(0, -1, 0), smooth=0)
    K.ribbon(g, [(x, 0.012, z) for x, _, z in path], 0.05, slot, 0.42, normal=(0, 1, 0), smooth=0)
    stroke(g, (0.0, 0.02), (0.0, 1.43), 0.014, -0.004, BONE, 0.6)
    g.pf([(0.007, 0.016, 0.02), (-0.007, 0.016, 0.02), (-0.007, 0.016, 1.43), (0.007, 0.016, 1.43)], BONE, 0.54)
    g.transform(m, mk)


def fletching_bench(kit):
    """The bowyer's bench (Fletching): a plank bench on trestle ends, a vice at its left end holding a fresh bow stave
    out over the top, a bundle of arrows with green fletching on it, a basket of feathers on the ground at its right
    end, two finished bows propped against its back."""
    rng = R('vale_fletching_bench')
    g = K.Geo()
    L, D, zt = 0.8, 0.3, 0.72
    K.box(g, (-L, -D, zt), (L, D, zt + 0.08), WOOD, 0.5, skip=('-z',))
    for x in (-L + 0.14, L - 0.14):
        K.box(g, (x - 0.05, -D + 0.04, 0), (x + 0.05, D - 0.04, zt), DWOOD, 0.42, skip=('-z', '+z'))
    zs = zt + 0.08
    K.box(g, (-0.78, -0.13, zs), (-0.52, 0.13, zs + 0.2), DWOOD, 0.4, skip=('-z',))              # the vice
    K.tube(g, (-0.65, -0.13, zs + 0.13), (-0.65, -0.34, zs + 0.13), 0.025, IRON, n=3, var=0.5, cap0=False,
           cap1=False)
    K.tube(g, (-0.95, 0, zs + 0.15), (0.62, 0, zs + 0.17), 0.032, ROPE, r1=0.016, n=4, var=0.5, cap0=False,
           cap1=False)                                                                       # the stave
    K.tube(g, (0.62, -0.16, zs + 0.05), (0.05, -0.14, zs + 0.05), 0.045, BRASS, n=4, var=0.56, cap1=False)   # arrows
    K.tube(g, (0.12, -0.143, zs + 0.05), (0.0, -0.14, zs + 0.05), 0.058, CLOTH1, n=4, var=0.5, cap0=False)
    bx, by = 1.02, -0.05                                                                     # the feather basket
    K.lathe(g, [(0.13, 0.0), (0.17, 0.26)], 6, ROPE, 0.44, smooth=0, cap1=False, m=T(bx, by, 0))
    K.rock(g, rng, (bx, by, 0.28), (0.15, 0.15, 0.09), BONE, n=6, var=0.62, flat=False)
    bow(g, T(-0.4, D + 0.25, 0) @ Rx(16) @ Rz(4))                                             # the bows
    bow(g, T(0.3, D + 0.25, 0) @ Rx(16) @ Rz(176))
    fp = plan_size(g)
    p = kit.add('vale_fletching_bench', g, budget=130, sheet={'az': 28, 'el': 24})
    p.info['node'] = True
    p.info['footprint'] = fp


def flask(g, rng, x, y, z, slot, r=0.075, n=6):
    """A round flask: a glass (or glowing) body and a pale neck (~2n + 2 tris)."""
    K.rock(g, rng, (x, y, z + r), (r, r, r), slot, n=n, var=0.55, flat=False)
    K.tube(g, (x, y, z + 1.6 * r), (x, y, z + 2.9 * r), 0.022, BONE, n=3, var=0.6, cap0=False, cap1=False)


def alchemy_table(kit):
    """The alchemy table (potions): a dark table, a glowing potion warming on a little iron burner with its flame
    showing, a second glowing potion, a tall glass bottle, a stone mortar with its pestle, a closed book."""
    rng = R('vale_alchemy_table')
    g = K.Geo()
    L, D, zt = 0.8, 0.4, 0.78
    K.box(g, (-L, -D, zt), (L, D, zt + 0.08), DWOOD, 0.5, skip=('-z',))
    for x in (-L + 0.1, L - 0.1):
        for y in (-D + 0.1, D - 0.1):
            K.box(g, (x - 0.05, y - 0.05, 0), (x + 0.05, y + 0.05, zt), DWOOD, 0.36, skip=('-z', '+z'))
    zs = zt + 0.08
    bx, by = -0.5, -0.05                                                                      # the burner
    K.tube(g, (bx, by, zs), (bx, by, zs + 0.16), 0.08, IRON, n=4, var=0.46, cap0=False)
    plate(g, [(bx - 0.035, zs + 0.02), (bx + 0.035, zs + 0.02), (bx, zs + 0.12)], by - 0.062, GLOW, 0.5)
    flask(g, rng, bx, by, zs + 0.16, GLOW, r=0.1, n=7)
    flask(g, rng, 0.1, 0.02, zs, GLOW, r=0.115, n=7)
    K.tube(g, (-0.2, 0.17, zs), (-0.2, 0.17, zs + 0.3), 0.065, WATER, n=4, var=0.6, cap0=False)      # a tall bottle
    K.tube(g, (-0.2, 0.17, zs + 0.3), (-0.2, 0.17, zs + 0.4), 0.022, ROPE, n=3, var=0.5, cap0=False, cap1=False)
    mx, my = 0.45, -0.12                                                                      # the mortar
    K.lathe(g, [(0.07, zs), (0.11, zs + 0.1)], 6, STONE, 0.52, smooth=0, cap1=False, m=T(mx, my, 0))
    K.disc(g, 0.095, 6, CLOTH1, z=zs + 0.08, var=0.42, m=T(mx, my, 0))
    K.tube(g, (mx - 0.02, my, zs + 0.05), (mx + 0.1, my - 0.06, zs + 0.22), 0.02, STONE, n=3, var=0.6, cap0=False,
           cap1=False)
    K.box(g, (0.42, 0.1, zs), (0.7, 0.3, zs + 0.06), CLOTH2, 0.5, skip=('-z',))              # a book
    fp = plan_size(g)
    p = kit.add('vale_alchemy_table', g, budget=140, sheet={'az': 28, 'el': 30})
    p.info['node'] = True
    p.info['footprint'] = fp


def cooking_range(kit):
    """The cooking range (Cooking): a brick range 1.6 × 1 m on a stone hearth, an iron hob with a pot of stew on it, a
    glowing fire mouth with a grate and an iron oven door on its front (−Y), mortar courses, a stove pipe up to 2.4 m,
    two logs by its left end; a fire light and a glow at the mouth, as the furnace."""
    rng = R('vale_range')
    g = K.Geo()
    K.box(g, (-0.9, -0.62, 0), (0.9, 0.6, 0.1), STONE, 0.4, skip=('-z',))                       # the hearth
    K.box(g, (-0.8, -0.5, 0.1), (0.8, 0.5, 1.0), DSTONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))   # the brick body
    K.box(g, (-0.85, -0.55, 1.0), (0.85, 0.55, 1.1), IRON, 0.46, skip=('-z',))                  # the hob
    for side, at, half, zz in (('-y', -0.5, 0.8, (0.18, 0.88)), ('-x', -0.8, 0.5, (0.38, 0.62, 0.86)),
                               ('+x', 0.8, 0.5, (0.38, 0.62, 0.86))):
        m = on_face(side, at, 0.0, 0.0)
        for z in zz:
            flat_strip(g, m, (-half, z), (half, z), 0.035, STONE, 0.58, y=-0.006)
    y = -0.508                                                                                # the fire mouth
    plate(g, [(-0.62, 0.24), (-0.08, 0.24), (-0.08, 0.8), (-0.62, 0.8)], y, INK, 0.5)
    plate(g, [(-0.55, 0.3), (-0.15, 0.3), (-0.15, 0.72), (-0.55, 0.72)], y - 0.006, GLOW, 0.5)
    for x in (-0.42, -0.28):
        stroke(g, (x, 0.3), (x, 0.72), 0.03, y - 0.012, IRON, 0.42)
    K.box(g, (0.1, -0.54, 0.26), (0.6, -0.5, 0.78), IRON, 0.5, skip=('+y',))                  # the oven door
    plate(g, [(0.47, 0.5), (0.55, 0.5), (0.55, 0.56), (0.47, 0.56)], -0.548, BRASS, 0.62)
    K.tube(g, (0.35, 0.05, 1.1), (0.35, 0.05, 1.36), 0.2, IRON, n=6, var=0.44, cap0=False, cap1=False)   # the pot
    K.disc(g, 0.19, 6, ROPE, z=1.32, var=0.4, m=T(0.35, 0.05, 0))
    K.tube(g, (-0.45, 0.25, 1.1), (-0.45, 0.25, 2.28), 0.09, IRON, n=5, var=0.46, cap0=False, cap1=False)   # the pipe
    K.lathe(g, [(0.13, 2.26), (0.13, 2.4)], 5, IRON, 0.42, smooth=0, cap0=False, cap_slot=INK, m=T(-0.45, 0.25, 0))
    for (xx, yy, zz) in ((-1.04, -0.02, 0.11), (-1.02, 0.07, 0.32)):                            # two logs
        K.tube(g, (xx, yy - 0.3, zz), (xx, yy + 0.3, zz), 0.11, DWOOD, n=5, var=0.42 + jit(rng, 0.05))
    p = kit.add('vale_range', g, budget=150, sheet={'az': 30, 'el': 22})
    kit.light(p, (-0.35, -0.66, 0.5), 'fire')
    kit.fx(p, (-0.35, -0.58, 0.5), 'glow')
    p.info['node'] = True
    p.info['footprint'] = plan_size(g)


# The shops' signs and what stands by their doors (the shop plan's door is at x −2.55, its window from −1.08; y0 is
# the front wall's face). Each mark is drawn on the board's face at yb, centred on (cx, cz).
def shop_arms(kit):
    """The armoury: a red-and-cream awning (the ember slot, the Vale's only red: it is emissive, so it stays bright), a
    slate roof, a sign of two crossed swords behind a shield, a rack by the door with a spear, a sword and an axe."""
    def icon(g, cx, yb, cz):
        for s in (-1, 1):
            a, b = Vector((cx - s * 0.36, cz - 0.3)), Vector((cx + s * 0.3, cz + 0.32))
            stroke(g, tuple(a), tuple(b), 0.07, yb, BMETAL, 0.64)                             # a blade
            dd = (b - a).normalized()
            q, nn = a + dd * 0.13, Vector((-dd.y, dd.x)) * 0.12
            stroke(g, tuple(q - nn), tuple(q + nn), 0.05, yb - 0.004, BRASS, 0.6)              # its guard
        shield = [(cx, cz - 0.27), (cx + 0.2, cz - 0.05), (cx + 0.2, cz + 0.22), (cx - 0.2, cz + 0.22),
                  (cx - 0.2, cz - 0.05)]
        plate(g, shield, yb - 0.01, BRASS, 0.62)
        plate(g, [(cx + (x - cx) * 0.72, cz + 0.01 + (z - cz - 0.01) * 0.72) for x, z in shield], yb - 0.016, GEM, 0.5)

    def rack(g, rng, y0):
        xc, yr = -1.5, y0 - 0.1                                      # the rack's back stands 0.1 m off the wall
        for x in (xc - 0.36, xc + 0.36):
            K.box(g, (x - 0.04, yr - 0.08, 0), (x + 0.04, yr, 1.3), DWOOD, 0.42, skip=('-z',))
        K.box(g, (xc - 0.36, yr - 0.08, 1.12), (xc + 0.36, yr, 1.2), DWOOD, 0.4, skip=('-x', '+x'))
        K.box(g, (xc - 0.42, y0 - 0.41, 0), (xc + 0.42, y0 - 0.29, 0.12), DWOOD, 0.38, skip=('-z',))

        def P(x, z):                                                 # leaning from the foot rail to the top bar
            return (x, y0 - 0.35 + (z - 0.12) * 0.16 / 1.04, z)
        x = xc - 0.24                                                # the spear
        K.tube(g, P(x, 0.1), P(x, 1.95), 0.022, WOOD, n=3, var=0.5, cap0=False, cap1=False)
        card(g, [P(x, 1.92), P(x + 0.055, 2.04), P(x, 2.24), P(x - 0.055, 2.04)], BMETAL, 0.64)
        x = xc                                                       # the sword, point down
        card(g, [P(x, 0.12), P(x + 0.035, 0.2), P(x + 0.035, 0.95), P(x - 0.035, 0.95), P(x - 0.035, 0.2)], BMETAL, 0.64)
        card(g, [P(x - 0.13, 0.95), P(x + 0.13, 0.95), P(x + 0.13, 1.0), P(x - 0.13, 1.0)], BRASS, 0.6)
        card(g, [P(x - 0.025, 1.0), P(x + 0.025, 1.0), P(x + 0.025, 1.2), P(x - 0.025, 1.2)], DWOOD, 0.4)
        x = xc + 0.24                                                # the axe
        K.tube(g, P(x, 0.1), P(x, 1.32), 0.024, WOOD, n=3, var=0.5, cap0=False, cap1=False)
        card(g, [P(x, 1.06), P(x + 0.18, 0.98), P(x + 0.2, 1.3), P(x, 1.24)], BMETAL, 0.6)

    shop(kit, 'vale_shop_arms', awning=GEM, roof=IRON, roof_var=0.5, board=SIGN, icon=icon, extra=rack, lean=True,
         budget=340)


def shop_bows(kit):
    """The bowyer: a green-and-cream awning (leaf green), a thatch roof, a sign of a bow with an arrow nocked, a
    bundle of staves tied with a cord leaning by the door; the door on the right (the shop's plan mirrored)."""
    def icon(g, cx, yb, cz):
        arc = [(cx - 0.08, yb, cz - 0.36), (cx - 0.24, yb, cz - 0.22), (cx - 0.3, yb, cz), (cx - 0.24, yb, cz + 0.22),
               (cx - 0.08, yb, cz + 0.36)]
        K.ribbon(g, arc, 0.065, BRASS, 0.62, normal=(0, -1, 0), smooth=0)
        stroke(g, (cx - 0.08, cz - 0.36), (cx - 0.08, cz + 0.36), 0.018, yb - 0.004, BONE, 0.6)
        stroke(g, (cx - 0.17, cz), (cx + 0.29, cz), 0.035, yb - 0.008, BONE, 0.56)
        plate(g, [(cx + 0.28, cz - 0.075), (cx + 0.43, cz), (cx + 0.28, cz + 0.075)], yb - 0.008, BMETAL, 0.64)
        plate(g, [(cx - 0.19, cz + 0.015), (cx - 0.06, cz + 0.015), (cx - 0.16, cz + 0.09)], yb - 0.012, CLOTH1, 0.56)
        plate(g, [(cx - 0.16, cz - 0.09), (cx - 0.06, cz - 0.015), (cx - 0.19, cz - 0.015)], yb - 0.012, CLOTH1, 0.56)

    def staves(g, rng, y0):
        xc = -1.5
        feet, tops = [], []
        for i, dx in enumerate((-0.13, -0.06, 0.01, 0.08, -0.02, 0.05)):
            f = Vector((xc + dx * 1.7, y0 - 0.42 + jit(rng, 0.04), 0.0))
            t = Vector((xc + dx * 0.5 + jit(rng, 0.03), y0 - 0.05, 1.72 + jit(rng, 0.12)))
            K.tube(g, tuple(f), tuple(t), 0.024, (WOOD, DWOOD, ROPE)[i % 3], n=3, var=0.46 + jit(rng, 0.06),
                   cap0=False, cap1=False)
            feet.append(f)
            tops.append(t)
        f = sum(feet, Vector()) / len(feet)
        t = sum(tops, Vector()) / len(tops)
        K.tube(g, tuple(f.lerp(t, 0.6)), tuple(f.lerp(t, 0.66)), 0.12, ROPE, n=6, var=0.62, cap0=False, cap1=False)

    shop(kit, 'vale_shop_bows', awning=CLOTH1, roof=ROPE, roof_var=0.5, board=SIGN, icon=icon, extra=staves, lean=True,
         mirror=True, budget=340)


def rune_sigil(g, cx, y, cz, s, slot=GLOW):
    """The Vale's rune: a lozenge on a staff with a bar at its foot, drawn in strokes on a face at y (12 tris)."""
    lz = [(cx, cz - 0.17 * s), (cx + 0.15 * s, cz + 0.05 * s), (cx, cz + 0.27 * s), (cx - 0.15 * s, cz + 0.05 * s)]
    for k in range(4):
        stroke(g, lz[k], lz[(k + 1) % 4], 0.05 * s, y, slot, 0.5)
    stroke(g, (cx, cz - 0.33 * s), (cx, cz + 0.36 * s), 0.05 * s, y - 0.004, slot, 0.5)
    stroke(g, (cx - 0.12 * s, cz - 0.27 * s), (cx + 0.12 * s, cz - 0.27 * s), 0.05 * s, y, slot, 0.5)


def shop_runes(kit):
    """The rune shop: a slate-and-cream awning (the Vale has no blue or purple slot; iron, the slate of the roofs, is
    its bluest dark), a thatch roof, a sign with a glowing rune, a standing stone by the door with the rune glowing on
    its face."""
    def icon(g, cx, yb, cz):
        rune_sigil(g, cx, yb, cz, 1.0)

    def stone(g, rng, y0):
        mk = g.mark()
        hgt = 1.05
        K.hull(g, [(-0.2, -0.12, 0), (0.2, -0.12, 0), (0.2, 0.13, 0), (-0.2, 0.13, 0),
                   (-0.15, -0.12, hgt), (0.14, -0.12, hgt * 0.94), (0.15, 0.09, hgt), (-0.14, 0.1, hgt * 0.9)],
               STONE, 0.44)
        rune_sigil(g, 0.0, -0.13, 0.52, 0.85)
        g.transform(T(-1.5, y0 - 0.4, 0) @ Rz(jit(rng, 6)), mk)

    shop(kit, 'vale_shop_runes', awning=IRON, roof=ROPE, roof_var=0.5, board=SIGN, icon=icon, extra=stone, lean=True,
         budget=340)


def shop_larder(kit):
    """The larder (food): a yellow-and-cream awning (straw gold), a shingle roof, a sign of a loaf over a fish, a basket
    of produce (a cabbage, apples, an onion) and a flour sack by the door."""
    def icon(g, cx, yb, cz):
        plate(g, [(cx - 0.3, cz + 0.04), (cx + 0.3, cz + 0.04), (cx + 0.34, cz + 0.14), (cx + 0.2, cz + 0.32),
                  (cx - 0.2, cz + 0.32), (cx - 0.34, cz + 0.14)], yb, ROPE, 0.64)
        for k in (-1, 0, 1):
            stroke(g, (cx + k * 0.15 - 0.05, cz + 0.12), (cx + k * 0.15 + 0.05, cz + 0.27), 0.03, yb - 0.005, DWOOD, 0.3)
        plate(g, [(cx - 0.3, cz - 0.19), (cx - 0.04, cz - 0.31), (cx + 0.17, cz - 0.19), (cx - 0.04, cz - 0.07)], yb,
              BMETAL, 0.62)
        plate(g, [(cx + 0.15, cz - 0.19), (cx + 0.32, cz - 0.3), (cx + 0.32, cz - 0.08)], yb, BMETAL, 0.54)
        plate(g, [(cx - 0.22, cz - 0.18), (cx - 0.17, cz - 0.18), (cx - 0.17, cz - 0.13), (cx - 0.22, cz - 0.13)],
              yb - 0.005, INK, 0.5)

    def produce(g, rng, y0):
        bx, by = -1.62, y0 - 0.42
        K.lathe(g, [(0.2, 0.0), (0.27, 0.34)], 6, ROPE, 0.46, smooth=0, cap1=False, m=T(bx, by, 0))
        K.disc(g, 0.25, 6, DSTONE, z=0.3, var=0.4, m=T(bx, by, 0))
        K.rock(g, rng, (bx - 0.06, by + 0.04, 0.37), (0.14, 0.14, 0.12), CLOTH1, n=7, var=0.56, flat=False)
        for dx, dy, slot in ((0.13, -0.09, GEM), (0.11, 0.11, GEM), (-0.12, -0.12, BRASS)):
            K.rock(g, rng, (bx + dx, by + dy, 0.36), (0.065, 0.065, 0.065), slot, n=5, var=0.55, flat=False)
        K.rock(g, rng, (-1.2, y0 - 0.32, 0.27), (0.2, 0.17, 0.28), BONE, n=9, var=0.5)

    shop(kit, 'vale_shop_larder', awning=ROPE, roof=DWOOD, roof_var=0.44, board=SIGN, icon=icon, extra=produce,
         lean=True, budget=340)


def shop_apothecary(kit):
    """The apothecary: a teal-and-cream awning (the water slot), a slate roof, a sign of a round flask of green
    potion, a shelf under the display window with two glowing potions and a glass bottle; the door on the right."""
    def icon(g, cx, yb, cz):
        c, r = (cx, cz - 0.12), 0.22
        plate(g, [(c[0] + r * math.cos(math.radians(22.5 + 45 * k)), c[1] + r * math.sin(math.radians(22.5 + 45 * k)))
                  for k in range(8)], yb, BONE, 0.62)
        stroke(g, (cx, cz + 0.05), (cx, cz + 0.27), 0.1, yb, BONE, 0.62)
        stroke(g, (cx, cz + 0.25), (cx, cz + 0.33), 0.12, yb - 0.005, ROPE, 0.5)
        plate(g, [(c[0] + 0.8 * r * math.cos(math.radians(a)), c[1] + 0.8 * r * math.sin(math.radians(a)))
                  for a in (180, 225, 270, 315, 360)], yb - 0.006, CLOTH1, 0.56)

    def shelf(g, rng, y0):
        K.box(g, (-1.0, y0 - 0.36, 0.84), (1.4, y0, 0.92), DWOOD, 0.42, skip=('+y',))
        flask(g, rng, -0.55, y0 - 0.22, 0.92, GLOW, r=0.13, n=7)
        flask(g, rng, 0.85, y0 - 0.22, 0.92, GLOW, r=0.12, n=7)
        K.tube(g, (0.15, y0 - 0.22, 0.92), (0.15, y0 - 0.22, 1.26), 0.08, WATER, n=4, var=0.6, cap0=False)
        K.tube(g, (0.15, y0 - 0.22, 1.26), (0.15, y0 - 0.22, 1.38), 0.026, ROPE, n=3, var=0.5, cap0=False, cap1=False)

    shop(kit, 'vale_shop_apothecary', awning=WATER, roof=IRON, roof_var=0.48, board=SIGN, icon=icon, extra=shelf,
         lean=True, mirror=True, budget=340)


# ====================================================================== the medieval town (Phase W8, OW-20)
# James: "look up medieval towns and base it on that … the whole town, there should also be an arena". The research is
# docs/research/medieval-towns.md, the layout the town tables in tools/content/gen-world-land.ts. The town turns its
# north and south wall runs to face in and its east and west runs to face out, so the wall pieces and the gate arch
# are the same from both faces. Buildings face −Y like the rest of the kit; tiling pieces span their x axis.
def crenels(g, x0, x1, n, ya, yb, z0, z1, slot=STONE, var=0.52, rng=None):
    """n merlons evenly along x from x0 to x1, each half its bay wide, between ya and yb, z0 to z1 (10 tris each)."""
    bay = (x1 - x0) / n
    for i in range(n):
        xc = x0 + (i + 0.5) * bay
        K.box(g, (xc - bay / 4, ya, z0), (xc + bay / 4, yb, z1), slot, var + (jit(rng, 0.04) if rng else 0.0),
              skip=('-z',))


def tower_top(g, rng, o, z0, mids=1, t=0.45, corners=True, slot=STONE):
    """A crenellated top over a square of half-size o: a corbelled course z0 − 0.45 … z0 (its top is the roof), a
    parapet ring to z0 + 0.5 and merlons on it — one at each corner (unless turrets stand there) and `mids` evenly
    along each side (34 tris + 10 per merlon)."""
    K.box(g, (-o, -o, z0 - 0.45), (o, o, z0), slot, 0.4, skip=('-z',))
    ring_wall(g, -o, -o, o, o, t, z0, z0 + 0.5, slot, 0.5)
    zm0, zm1, c, w = z0 + 0.5, z0 + 1.05, 0.75, 0.8
    if corners:
        for sx in (-1, 1):
            for sy in (-1, 1):
                xa, xb = sorted((sx * o, sx * (o - c)))
                ya, yb = sorted((sy * o, sy * (o - c)))
                K.box(g, (xa, ya, zm0), (xb, yb, zm1), slot, 0.52 + jit(rng, 0.04), skip=('-z',))
    span = o - c
    for k in range(mids):
        a = -span + (k + 1) * 2 * span / (mids + 1)
        for lo, hi in (((a - w / 2, -o, zm0), (a + w / 2, -o + t, zm1)), ((a - w / 2, o - t, zm0), (a + w / 2, o, zm1)),
                       ((-o, a - w / 2, zm0), (-o + t, a + w / 2, zm1)), ((o - t, a - w / 2, zm0), (o, a + w / 2, zm1))):
            K.box(g, lo, hi, slot, 0.52 + jit(rng, 0.04), skip=('-z',))


def slit(g, m, h=1.0, w=0.14):
    """An arrow slit (2 tris); local origin = its foot's centre on the wall face, facing −Y."""
    mk = g.mark()
    g.pf([(-w / 2, -0.012, 0.0), (w / 2, -0.012, 0.0), (w / 2, -0.012, h), (-w / 2, -0.012, h)], INK, 0.5)
    g.transform(m, mk)


def round_window(g, m, w=0.8, h=1.8, rim=0.12, depth=0.1, frame=STONE, fvar=0.68, pane=INK, pvar=0.5, segs=3,
                 glass=None):
    """A tall round-headed window (or, with a plank pane, a door) in a dressed-stone surround (20 tris); local origin =
    the sill's centre on the wall face, facing −Y. An ink pane is glass (a lit window, K.glaze) unless `glass` says not."""
    mk = g.mark()

    def outline(hw, z0):
        return [(-hw, z0), (hw, z0)] + [(math.cos(math.pi * k / segs) * hw, h + math.sin(math.pi * k / segs) * hw)
                                         for k in range(segs + 1)]
    K.slab_xz(g, outline(w / 2 + rim, -rim), -depth, 0.02, frame, fvar, back=False)
    f = plate(g, outline(w / 2, 0.0), -depth - 0.02, pane, pvar)
    if (pane == INK) if glass is None else glass:
        K.glaze(g, f)
    g.transform(m, mk)


def book_mark(g, cx, y, cz, s=1.0):
    """An open book facing −Y at y: two covers, two pages, a line of text on each (12 tris)."""
    for sgn in (-1, 1):
        cov = [(cx, cz - 0.38 * s), (cx + sgn * 0.5 * s, cz - 0.3 * s), (cx + sgn * 0.5 * s, cz + 0.3 * s),
               (cx, cz + 0.22 * s)]
        pg = [(cx + sgn * 0.03 * s, cz - 0.3 * s), (cx + sgn * 0.44 * s, cz - 0.23 * s),
              (cx + sgn * 0.44 * s, cz + 0.24 * s), (cx + sgn * 0.03 * s, cz + 0.15 * s)]
        if sgn < 0:
            cov, pg = list(reversed(cov)), list(reversed(pg))
        plate(g, cov, y, CLOTH2, 0.5)
        plate(g, pg, y - 0.006, BONE, 0.66)
        stroke(g, (cx + sgn * 0.1 * s, cz + 0.02 * s), (cx + sgn * 0.37 * s, cz + 0.06 * s), 0.035 * s, y - 0.012, INK,
               0.4)


def wall_stone(kit):
    """A 4 m run of the stone town wall, tiling end to end along x (−2…+2): a plinth, the curtain 1.6 m thick up to a
    walkway at 4.4 m between two crenellated parapets (the same both ways). Town review 2026-11-04 ("a flat grey
    plane per 4 m"): three dark course bands on each face, a pale coping on the parapets, the curtain's ends closed,
    and a pier at the +x end (0.5 m long, 0.2 m proud of both faces, to 5.4 m under a low pyramid cap) that straddles
    the join with the next segment — on uneven ground, where neighbours sit at different heights, the pier and the
    closed ends hide the step instead of showing a gap. Place a run with one yaw so every join has exactly one pier."""
    rng = R('vale_wall_stone')
    g = K.Geo()
    L, hw, zw = 2.0, 0.8, 4.4
    K.box(g, (-L, -hw - 0.15, 0), (L, hw + 0.15, 0.7), STONE, 0.4, skip=('-z', '-x', '+x'))        # the plinth
    K.box(g, (-L, -hw, 0.7), (L, hw, zw), STONE, 0.5 + jit(rng, 0.03), skip=('-z',))              # the curtain
    for sy in (-1, 1):
        ya, yb = sorted((sy * hw, sy * (hw - 0.35)))
        K.box(g, (-L, ya, zw), (L, yb, zw + 0.45), STONE, lambda s: 0.72 if s == '+z' else 0.56, skip=('-z',))
        crenels(g, -L, L, 2, ya, yb, zw + 0.45, zw + 1.0, rng=rng)
        m = on_face('-y' if sy < 0 else '+y', sy * hw, 0.0, 0.0)
        for z in (1.45, 2.6, 3.75):                                                                 # course bands
            flat_strip(g, m, (-L, z), (L, z), 0.14, STONE, 0.0, y=-0.008)
    K.box(g, (L - 0.25, -hw - 0.2, 0), (L + 0.25, hw + 0.2, zw + 0.7), STONE, 0.46, skip=('-z',))  # the end pier
    pyramid(g, L, 0.0, 0.25, hw + 0.2, zw + 0.7, zw + 1.0, STONE, var=0.62, under=False)
    p = kit.add('vale_wall_stone', g, budget=110, sheet={'az': 30, 'el': 18},
                bake={'ground': 0.0, 'occluders': [('vale_wall_stone', (-2 * L, 0, 0)), ('vale_wall_stone', (2 * L, 0, 0))]})
    p.info['span'] = 2 * L
    p.info['footprint'] = [2 * L + 0.5, 2 * (hw + 0.2)]


def wall_tower_stone(kit):
    """A tower of the stone town wall, 4.4 m square and 8 m tall (the wall runs into it along x): a battered foot, arrow
    slits on every face (those on the ±x faces above the wall), a corbelled crenellated top."""
    rng = R('vale_wall_tower_stone')
    g = K.Geo()
    h, zt = 2.2, 7.0
    K.box(g, (-h - 0.3, -h - 0.3, 0), (h + 0.3, h + 0.3, 0.9), STONE, 0.42, skip=('-z',))
    K.box(g, (-h, -h, 0.9), (h, h, zt - 0.45), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    tower_top(g, rng, h + 0.2, zt, mids=1)
    for side, at in (('-y', -h), ('+y', h)):
        slit(g, on_face(side, at, 0.0, 2.3))
        slit(g, on_face(side, at, 0.0, 4.7))
    for side, at in (('-x', -h), ('+x', h)):
        slit(g, on_face(side, at, 0.0, 5.55), h=0.8)
    p = kit.add('vale_wall_tower_stone', g, budget=160, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [2 * h, 2 * h]


def gate_tower(kit):
    """A gatehouse tower, 5 m square and ~10 m to its parapet (two stand 12 m apart either side of a road with the stone
    arch between them): a battered foot, slits, a pointed window up each ±Y face, a corbelled crenellated top with a
    slate cap inside the parapet and a green pennant."""
    rng = R('vale_gate_tower')
    g = K.Geo()
    h, zt = 2.5, 8.6
    K.box(g, (-h - 0.35, -h - 0.35, 0), (h + 0.35, h + 0.35, 1.1), STONE, 0.42, skip=('-z',))
    K.box(g, (-h, -h, 1.1), (h, h, zt - 0.45), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    o = h + 0.25
    tower_top(g, rng, o, zt, mids=1)
    pyramid(g, 0, 0, o - 0.45, o - 0.45, zt, zt + 2.4, IRON, var=0.46, under=False)
    for side, at in (('-y', -h), ('+y', h)):
        slit(g, on_face(side, at, 0.0, 2.6))
        lancet(g, on_face(side, at, 0.0, 5.3), w=0.55, h=1.1)
    for side, at in (('-x', -h), ('+x', h)):
        slit(g, on_face(side, at, 0.0, 2.6))
    K.tube(g, (0, 0, zt + 2.2), (0, 0, zt + 3.6), 0.035, DWOOD, n=3, var=0.4, cap0=False, cap1=False)
    flag = [(0.0, 0.0, zt + 3.55), (0.0, 0.0, zt + 3.05), (0.9, 0.0, zt + 3.3)]
    g.pf(flag, CLOTH2, 0.5)
    g.pf(list(reversed(flag)), CLOTH2, 0.44)
    p = kit.add('vale_gate_tower', g, budget=200, sheet={'az': 30, 'el': 16})
    p.info['footprint'] = [2 * h, 2 * h]


def gate_arch_stone(kit):
    """The overhead part of a stone gatehouse: a segmental stone arch 8 m long whose ends sit 0.5 m into the two gate
    towers (their faces at x ±3.5), its soffit 4.5 m at the towers and 5.35 m at the crown, its deck at 6.8 m between
    two crenellated parapets, a lantern hung over the road (its foot at 4.42 m) — no posts, no collider."""
    rng = R('vale_gate_arch_stone')
    g = K.Geo()
    L, d, top = 4.0, 1.4, 6.8
    xs, zs = (-4.0, -1.75, 0.0, 1.75, 4.0), (4.5, 5.12, 5.35, 5.12, 4.5)
    for i in range(4):
        q = [(xs[i], zs[i]), (xs[i + 1], zs[i + 1]), (xs[i + 1], top), (xs[i], top)]
        plate(g, q, -d, STONE, 0.5 + jit(rng, 0.03))
        g.pf([(x, d, z) for x, z in reversed(q)], STONE, 0.5 + jit(rng, 0.03))
        g.pf([(xs[i], -d, zs[i]), (xs[i], d, zs[i]), (xs[i + 1], d, zs[i + 1]), (xs[i + 1], -d, zs[i + 1])], STONE, 0.4)
    g.pf([(-L, -d, top), (L, -d, top), (L, d, top), (-L, d, top)], STONE, 0.46)
    for sy in (-1, 1):
        ya, yb = sorted((sy * d, sy * (d - 0.35)))
        K.box(g, (-L, ya, top), (L, yb, top + 0.4), STONE, 0.56, skip=('-z', '-x', '+x'))
        crenels(g, -L, L, 3, ya, yb, top + 0.4, top + 0.9, rng=rng)
    K.tube(g, (0, 0, 5.35), (0, 0, 4.92), 0.025, IRON, n=3, var=0.44, cap0=False, cap1=False)    # the lantern
    K.box(g, (-0.15, -0.15, 4.44), (0.15, 0.15, 4.8), GLOW, 0.5, skip=('-z', '+z'))
    pyramid(g, 0, 0, 0.2, 0.2, 4.8, 4.95, IRON, var=0.42)
    g.pf([(-0.17, -0.17, 4.42), (-0.17, 0.17, 4.42), (0.17, 0.17, 4.42), (0.17, -0.17, 4.42)], IRON, 0.4)
    p = kit.add('vale_gate_arch_stone', g, budget=120, sheet={'az': 30, 'el': 14})
    kit.light(p, (0, 0, 4.62), 'lamp')
    p.info['footprint'] = [2 * L, 2 * d]
    p.info['span'] = 2 * L
    p.info['no_collider'] = True


def keep(kit):
    """The lord's keep: a square stone tower ~11 m across and 14 m to its parapet on a battered foot, a round turret at
    each corner rising to a slate cone (~17.6 m), a corbelled crenellated parapet between them, arrow slits, two pointed
    windows and a long green banner on the front (−Y) over a door reached up a short stair."""
    rng = R('vale_keep')
    g = K.Geo()
    h, zt, zb = 5.2, 13.6, 1.3
    K.box(g, (-h - 0.45, -h - 0.45, 0), (h + 0.45, h + 0.45, zb), STONE, 0.42, skip=('-z',))
    K.box(g, (-h, -h, zb), (h, h, zt - 0.45), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    tower_top(g, rng, h + 0.25, zt, mids=3, corners=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            m = T(sx * 5.0, sy * 5.0, 0)
            K.lathe(g, [(1.35, 0.0), (1.35, 15.4)], 8, STONE, 0.56 + jit(rng, 0.04), smooth=0, cap0=False, cap1=False,
                    phase=math.pi / 8, m=m)
            K.lathe(g, [(1.6, 15.4), (0.0, 17.6)], 8, IRON, 0.48, smooth=0, cap0=False, phase=math.pi / 8, m=m)
    for k in range(3):                                                                         # the stair and door
        K.box(g, (-1.1, -h - 1.2 + k * 0.25, 0), (1.1, -h - 0.45, zb * (k + 1) / 3), STONE, 0.4 + 0.04 * k,
              skip=('-z', '+y'))
    lancet(g, T(0, -h, zb), w=1.5, h=2.3, pane=DWOOD, pvar=0.38)
    for side, at in (('+y', h), ('-x', -h), ('+x', h)):
        for a in (-2.0, 2.0):
            for z in (5.0, 9.5):
                slit(g, on_face(side, at, a, z), h=1.1)
    for a in (-2.6, 2.6):
        lancet(g, T(a, -h, 7.4), w=0.7, h=1.5)
        slit(g, T(a, -h, 3.8), h=1.1)
    K.box(g, (-0.85, -h - 0.25, 10.9), (0.85, -h, 11.02), DWOOD, 0.4, skip=('+y',))           # the banner
    yb = -h - 0.12
    plate(g, [(0.0, 6.6), (0.7, 7.2), (0.7, 10.9), (-0.7, 10.9), (-0.7, 7.2)], yb, CLOTH2, 0.5)
    plate(g, [(0.0, 8.4), (0.32, 8.9), (0.0, 9.4), (-0.32, 8.9)], yb - 0.01, BRASS, 0.62)
    fp = plan_size(g)
    p = kit.add('vale_keep', g, budget=450, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = fp


def church(kit):
    """The parish church, the town's largest building, its long axis along x: a west tower at −x (5 m square, 14 m: a
    door in its −Y face, belfry openings, corner pinnacles, a slate spire with a brass cross), a tall nave with pointed
    windows between sloped buttresses, a lower chancel at +x with a great east window, slate roofs."""
    rng = R('vale_church')
    g = K.Geo()
    nx0, nx1, ny, nh, nzr = -5.4, 6.6, 4.0, 6.2, 10.0                                        # the nave
    K.box(g, (nx0, -ny - 0.1, 0), (nx1 + 0.1, ny + 0.1, 0.4), STONE, 0.36, skip=('-z',))
    K.box(g, (nx0, -ny, 0.4), (nx1, ny, nh), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    gable_roof(g, nx0, nx1, -ny, ny, eave_z(nh, nzr, ny, 0.35), nzr, IRON, var=0.48, overhang=0.35)
    g.pf([(nx0, ny, nh), (nx0, -ny, nh), (nx0, 0.0, nzr - 0.06)], STONE, 0.5)
    g.pf([(nx1, -ny, nh), (nx1, ny, nh), (nx1, 0.0, nzr - 0.06)], STONE, 0.5)
    for x in (-3.5, 0.3, 4.1):
        lancet(g, on_face('-y', -ny, x, 1.8), w=0.8, h=2.4)
        lancet(g, on_face('+y', ny, x, 1.8), w=0.8, h=2.4)
    for x in (-1.6, 2.2, 6.15):
        for sgn in (-1, 1):
            mk = g.mark()
            buttress(g, sgn * ny, -x, sgn, depth=0.55, half=0.25, z_wall=4.6, z_out=2.0)
            g.transform(Rz(90), mk)
    cx0, cx1, cy, ch, czr = nx1, 10.1, 3.0, 5.0, 8.2                                         # the chancel
    K.box(g, (cx0, -cy - 0.1, 0), (cx1 + 0.1, cy + 0.1, 0.4), STONE, 0.36, skip=('-z', '-x'))
    K.box(g, (cx0, -cy, 0.4), (cx1, cy, ch), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z', '-x'))
    gable_roof(g, cx0, cx1, -cy, cy, eave_z(ch, czr, cy, 0.3), czr, IRON, var=0.46, overhang=0.3)
    g.pf([(cx1, -cy, ch), (cx1, cy, ch), (cx1, 0.0, czr - 0.06)], STONE, 0.5)
    for side, at in (('-y', -cy), ('+y', cy)):
        lancet(g, on_face(side, at, 8.4, 1.5), w=0.7, h=2.0)
    lancet(g, on_face('+x', cx1, 0.0, 1.4), w=1.3, h=2.2)
    tx0, tx1, ty, th = -10.38, -5.4, 2.5, 14.0                                               # the tower
    tcx = (tx0 + tx1) / 2
    K.box(g, (tx0 - 0.1, -ty - 0.1, 0), (tx1, ty + 0.1, 0.5), STONE, 0.36, skip=('-z', '+x'))
    K.box(g, (tx0, -ty, 0.5), (tx1, ty, th), STONE, 0.52 + jit(rng, 0.03), skip=('-z',))
    for z in (5.4, 9.6):
        K.box(g, (tx0 - 0.12, -ty - 0.12, z), (tx1, ty + 0.12, z + 0.25), STONE, 0.38, skip=('-z', '+x'))
    for sx in (tx0 + 0.35, tx1 - 0.35):
        for sy in (-ty + 0.35, ty - 0.35):
            K.box(g, (sx - 0.3, sy - 0.3, th), (sx + 0.3, sy + 0.3, th + 0.9), STONE, 0.5, skip=('-z', '+z'))
            pyramid(g, sx, sy, 0.34, 0.34, th + 0.9, th + 2.0, STONE, var=0.56, under=False)
    pyramid(g, tcx, 0, 1.95, 1.95, th, th + 7.5, IRON, var=0.46, under=False)
    K.tube(g, (tcx, 0, th + 7.3), (tcx, 0, th + 8.4), 0.04, BRASS, n=3, var=0.6, cap0=False, cap1=False)
    card(g, [(tcx - 0.3, 0, th + 7.85), (tcx + 0.3, 0, th + 7.85), (tcx + 0.3, 0, th + 7.97), (tcx - 0.3, 0, th + 7.97)],
         BRASS, 0.62)
    for side, at in (('-y', -ty), ('+y', ty)):
        lancet(g, on_face(side, at, tcx, 10.2), w=0.9, h=1.5)
    lancet(g, on_face('-x', tx0, 0.0, 10.2), w=0.9, h=1.5)
    lancet(g, on_face('-x', tx0, 0.0, 5.9), w=0.55, h=1.6)
    lancet(g, T(tcx, -ty, 0.5), w=1.4, h=2.2, pane=DWOOD, pvar=0.38)                          # the door
    K.box(g, (tcx - 0.95, -ty - 0.55, 0), (tcx + 0.95, -ty - 0.1, 0.25), STONE, 0.42, skip=('-z', '+y'))
    fp = plan_size(g)
    p = kit.add('vale_church', g, budget=500, sheet={'az': 28, 'el': 18})
    p.info['footprint'] = fp


def framed_upper(g, rng, ux, uy, z0, z1, studs_y=(), studs_x=()):
    """A timber-framed plastered storey over a footprint of half-size ux × uy from z0 to z1: corner posts, a wall plate
    and flat studs at `studs_y` along the ±Y faces and `studs_x` along the ±X faces (56 + 4 per stud tris)."""
    K.box(g, (-ux, -uy, z0), (ux, uy, z1), BONE, 0.52 + jit(rng, 0.04), skip=('-z', '+z'))
    for x in (-ux, ux):
        for y in (-uy, uy):
            K.box(g, (x - 0.13, y - 0.13, z0), (x + 0.13, y + 0.13, z1), WOOD, 0.42, skip=('-z', '+z'))
    K.box(g, (-ux - 0.08, -uy - 0.08, z1 - 0.22), (ux + 0.08, uy + 0.08, z1 + 0.02), WOOD, 0.4, skip=('-z', '+z'))
    for side, at, studs in (('-y', -uy, studs_y), ('+y', uy, studs_y), ('-x', -ux, studs_x), ('+x', ux, studs_x)):
        m = on_face(side, at, 0.0, 0.0)
        for a in studs:
            flat_strip(g, m, (a, z0), (a, z1 - 0.22), 0.16, WOOD, 0.44, y=-0.012)


def guildhall(kit):
    """The guildhall (the Skill Hall's home): a timber-framed hall raised on an open arcade of eight stone pillars over a
    flagged floor (townsfolk walk beneath it), windows all round, a shingle roof with a cupola on the ridge — a clock
    on its front and a brass bell in its open belfry."""
    rng = R('vale_guildhall')
    g = K.Geo()
    K.box(g, (-5.8, -3.8, 0), (5.8, 3.8, 0.12), STONE, 0.4, skip=('-z',))
    for x in (-5.4, -1.8, 1.8, 5.4):
        for y in (-3.4, 3.4):
            K.box(g, (x - 0.3, y - 0.3, 0.12), (x + 0.3, y + 0.3, 3.0), STONE, 0.54 + jit(rng, 0.04),
                  skip=('-z', '+z'))
    K.box(g, (-5.9, -3.85, 3.0), (5.9, 3.85, 3.35), DWOOD, 0.4)
    ux, uy, z0, z1, zr = 6.1, 4.05, 3.35, 6.6, 9.3
    framed_upper(g, rng, ux, uy, z0, z1, studs_y=(-2.8, 0.0, 2.8), studs_x=(0.0,))
    for x in (-4.2, -1.4, 1.4, 4.2):
        town_window(g, T(x, -uy, 4.4), w=1.0, h=1.2)
    for x in (-1.4, 1.4):
        town_window(g, on_face('+y', uy, x, 4.4), w=1.0, h=1.2)
    for side, at in (('-x', -ux), ('+x', ux)):
        town_window(g, on_face(side, at, -1.8, 4.4), w=1.0, h=1.2)
    gable_roof(g, -ux, ux, -uy, uy, eave_z(z1 + 0.02, zr, uy, 0.35), zr, DWOOD, var=0.44, overhang=0.35)
    for x, sgn in ((-ux, -1), (ux, 1)):
        pts = [(x, -uy, z1), (x, uy, z1), (x, 0.0, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), BONE, 0.5)
    zc = zr - 0.5                                                                              # the cupola
    K.box(g, (-0.7, -0.7, zc), (0.7, 0.7, zr + 0.9), WOOD, 0.48, skip=('-z',))
    K.disc(g, 0.5, 8, BONE, var=0.68, m=T(0, -0.715, zr + 0.25) @ Rx(90), phase=math.pi / 8)   # the clock
    stroke(g, (0.0, zr + 0.25), (0.0, zr + 0.6), 0.06, -0.725, INK, 0.4)
    stroke(g, (0.0, zr + 0.25), (0.26, zr + 0.25), 0.06, -0.73, INK, 0.4)
    for sx in (-0.55, 0.55):
        for sy in (-0.55, 0.55):
            K.tube(g, (sx, sy, zr + 0.9), (sx, sy, zr + 1.9), 0.06, WOOD, n=3, var=0.44, cap0=False, cap1=False)
    K.lathe(g, [(0.32, zr + 1.05), (0.24, zr + 1.4), (0.0, zr + 1.58)], 6, BRASS, 0.62, smooth=50, cap_slot=INK)
    pyramid(g, 0, 0, 0.82, 0.82, zr + 1.9, zr + 2.6, DWOOD, var=0.42)
    K.tube(g, (0, 0, zr + 2.5), (0, 0, zr + 3.0), 0.03, BRASS, n=3, var=0.6, cap0=False)
    p = kit.add('vale_guildhall', g, budget=420, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [2 * ux, 2 * uy]


def library(kit):
    """The library and scriptorium: a tall stone hall on a plinth, two storeys of tall round-headed windows either side
    of a string course, a steep slate roof with a round window in each gable, a round-headed door under an open book
    carved on a plaque."""
    rng = R('vale_library')
    g = K.Geo()
    hx, hy, h, zr = 4.5, 3.5, 7.2, 10.8
    K.box(g, (-hx - 0.12, -hy - 0.12, 0), (hx + 0.12, hy + 0.12, 0.5), STONE, 0.36, skip=('-z',))
    K.box(g, (-hx, -hy, 0.5), (hx, hy, h), STONE, 0.56 + jit(rng, 0.03), skip=('-z', '+z'))
    K.box(g, (-hx - 0.08, -hy - 0.08, 3.55), (hx + 0.08, hy + 0.08, 3.8), STONE, 0.36, skip=('-z',))
    K.box(g, (-hx - 0.14, -hy - 0.14, h - 0.3), (hx + 0.14, hy + 0.14, h), STONE, 0.4, skip=('-z', '+z'))
    gable_roof(g, -hx, hx, -hy, hy, eave_z(h, zr, hy, 0.35), zr, IRON, var=0.46, overhang=0.35)
    for x, sgn in ((-hx, -1), (hx, 1)):
        pts = [(x, -hy, h), (x, hy, h), (x, 0.0, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), STONE, 0.54)
        side = '+x' if sgn > 0 else '-x'
        for r, slot, v, dd in ((0.62, STONE, 0.7, 0.0), (0.46, INK, 0.5, 0.02)):
            mk = K.disc(g, r, 8, slot, var=v, m=on_face(side, x, 0.0, 8.4) @ T(0, -0.02 - dd, 0) @ Rx(90))
            if slot == INK:
                K.glaze(g, since=mk)
        round_window(g, on_face(side, x, 0.0, 4.2), w=0.8, h=1.9)
    for x in (-2.6, 2.6):
        round_window(g, T(x, -hy, 1.0), w=0.8, h=1.6)
        round_window(g, T(x, -hy, 4.2), w=0.8, h=1.9)
        round_window(g, on_face('+y', hy, x, 4.2), w=0.8, h=1.9)
    round_window(g, T(0, -hy, 0.5), w=1.3, h=1.9, pane=DWOOD, pvar=0.38)                       # the door
    K.box(g, (-1.0, -hy - 0.55, 0), (1.0, -hy - 0.12, 0.25), STONE, 0.42, skip=('-z', '+y'))
    K.box(g, (-0.75, -hy - 0.06, 4.15), (0.75, -hy, 5.05), STONE, 0.66, skip=('+y',))          # the book plaque
    book_mark(g, 0.0, -hy - 0.07, 4.62, s=0.62)
    p = kit.add('vale_library', g, budget=340, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [2 * hx, 2 * hy]


def stables(kit):
    """The stables: a long plank stable block on a stone sill, four stalls opening to the front (−Y) under a deep thatch
    eave, each with a half-door and the dark stall above it, a loft hatch with hay and a hoist beam in the +x gable,
    a water trough and a hay bale in front, a louvred vent on the ridge, shuttered windows at the back."""
    rng = R('vale_stables')
    g = K.Geo()
    hx, hy, h, zr = 4.5, 2.8, 3.0, 5.7
    K.box(g, (-hx - 0.1, -hy - 0.1, 0), (hx + 0.1, hy + 0.1, 0.3), STONE, 0.4, skip=('-z',))
    K.box(g, (-hx, -hy, 0.3), (hx, hy, h), DWOOD, 0.46 + jit(rng, 0.03), skip=('-z', '+z'))
    for side, at, half in (('-x', -hx, hy - 0.1), ('+x', hx, hy - 0.1), ('+y', hy, hx - 0.1)):
        m = on_face(side, at, 0.0, 0.0)
        for z in (1.0, 1.7, 2.4):
            flat_strip(g, m, (-half, z), (half, z), 0.04, DWOOD, 0.32, y=-0.008)
    yf = -hy
    for x in (-3.375, -1.125, 1.125, 3.375):                                                 # the stalls
        plate(g, [(x - 0.85, 1.35), (x + 0.85, 1.35), (x + 0.85, 2.55), (x - 0.85, 2.55)], yf - 0.01, INK, 0.5)
        K.box(g, (x - 0.85, yf - 0.07, 0.3), (x + 0.85, yf - 0.01, 1.32), WOOD, 0.5 + jit(rng, 0.05), skip=('+y',))
        stroke(g, (x - 0.78, 0.38), (x + 0.78, 1.24), 0.08, yf - 0.075, DWOOD, 0.4)
    for x in (-hx, -2.25, 0.0, 2.25, hx):
        K.box(g, (x - 0.13, yf - 0.16, 0.3), (x + 0.13, yf, h), DWOOD, 0.4, skip=('-z', '+z', '+y'))
    K.box(g, (-hx - 0.1, yf - 0.18, 2.6), (hx + 0.1, yf, 2.86), DWOOD, 0.38, skip=('+y',))
    gable_roof(g, -hx, hx, -hy, hy, eave_z(h, zr, hy, 0.5), zr, ROPE, var=0.5, overhang=0.5)
    for x, sgn in ((-hx, -1), (hx, 1)):
        pts = [(x, -hy, h), (x, hy, h), (x, 0.0, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), DWOOD, 0.44)
    mk = g.mark()                                                                              # the loft hatch
    plate(g, [(-0.5, 0.0), (0.5, 0.0), (0.5, 0.95), (-0.5, 0.95)], -0.01, INK, 0.5)
    g.transform(on_face('+x', hx, 0.0, 3.25), mk)
    K.rock(g, rng, (hx + 0.12, 0.0, 3.4), (0.28, 0.45, 0.22), ROPE, n=8, var=0.6)
    K.box(g, (hx - 0.1, -0.08, 4.45), (hx + 0.5, 0.08, 4.6), DWOOD, 0.4, skip=('-x',))
    K.box(g, (-2.0, yf - 0.85, 0), (-0.4, yf - 0.35, 0.55), DWOOD, 0.42, skip=('-z',))         # the trough
    g.pf([(-1.92, yf - 0.78, 0.56), (-0.48, yf - 0.78, 0.56), (-0.48, yf - 0.42, 0.56), (-1.92, yf - 0.42, 0.56)],
         WATER, 0.55)
    K.box(g, (0.9, yf - 1.0, 0), (1.8, yf - 0.45, 0.5), ROPE, 0.56, skip=('-z',))              # a hay bale
    K.box(g, (-0.45, -0.45, zr - 0.4), (0.45, 0.45, zr + 0.45), WOOD, 0.46, skip=('-z',))      # the vent
    for y, sgn in ((-0.46, 1), (0.46, -1)):
        q = [(-0.3, y, zr), (0.3, y, zr), (0.3, y, zr + 0.32), (-0.3, y, zr + 0.32)]
        g.pf(q if sgn > 0 else [(-x, yy, z) for x, yy, z in q], INK, 0.5)
    pyramid(g, 0, 0, 0.62, 0.62, zr + 0.45, zr + 0.9, ROPE, var=0.46)
    for x in (-2.25, 2.25):
        town_window(g, on_face('+y', hy, x, 1.6), w=0.7, h=0.6, pane=DWOOD, cross=False)
    p = kit.add('vale_stables', g, budget=320, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [2 * hx, 2 * hy]


def watermill(kit):
    """The watermill: a stone ground floor and a plastered, timber-framed upper floor under a thatch roof, a door and
    flour sacks at the front (−Y); on the +x gable end an overshot water wheel (ten paddles to 2.9 m, hanging beyond the
    footprint) fed by a timber mill race on two posts that brings the water from behind (+Y) and spills onto it.
    W18-town: the wheel itself is the piece vale_mill_wheel (placed at the same point and yaw); its axle stays here."""
    rng = R('vale_watermill')
    g = K.Geo()
    hx, hy, zs, zu, zr = 4.6, 3.6, 3.4, 6.0, 8.9
    K.box(g, (-hx - 0.12, -hy - 0.12, 0), (hx + 0.12, hy + 0.12, 0.45), STONE, 0.36, skip=('-z',))
    K.box(g, (-hx, -hy, 0.45), (hx, hy, zs), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    K.box(g, (-hx - 0.1, -hy - 0.1, zs - 0.1), (hx + 0.1, hy + 0.1, zs + 0.15), DWOOD, 0.4, skip=('-z',))
    framed_upper(g, rng, hx, hy, zs + 0.15, zu, studs_y=(-1.5, 1.5))
    gable_roof(g, -hx, hx, -hy, hy, eave_z(zu + 0.02, zr, hy, 0.4), zr, ROPE, var=0.5, overhang=0.4)
    for x, sgn in ((-hx, -1), (hx, 1)):
        pts = [(x, -hy, zu), (x, hy, zu), (x, 0.0, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), BONE, 0.5)
    town_door(g, T(-1.6, -hy, 0.45), w=1.3, h=2.2)
    town_window(g, T(1.6, -hy, 1.4), w=1.0, h=1.0)
    for x in (-3.0, 3.0):
        town_window(g, T(x, -hy, 4.2), w=1.0, h=1.0)
        town_window(g, on_face('+y', hy, x, 4.2), w=1.0, h=1.0)
    town_window(g, on_face('-x', -hx, 0.0, 1.4), w=1.0, h=1.0)
    K.rock(g, rng, (-0.45, -hy - 0.4, 0.3), (0.26, 0.22, 0.32), BONE, n=7, var=0.56)           # flour sacks
    K.rock(g, rng, (0.15, -hy - 0.36, 0.26), (0.24, 0.2, 0.28), BONE, n=7, var=0.5)
    wx, cz, r0, r1 = 5.4, 2.6, 2.2, 2.5                                                        # the wheel
    # W18-town: the wheel (paddle rings, paddles, spokes) is its own piece, vale_mill_wheel (vale_town_pieces.py), so
    # the game can turn it; the axle stays here
    K.tube(g, (hx, 0, cz), (wx + 0.4, 0, cz), 0.14, IRON, n=4, var=0.46, cap0=False)
    xa, xb, ya, yb = wx - 0.38, wx + 0.38, -0.5, 5.0                                          # the mill race
    za, zb = 5.72, 5.9
    g.pf([(xa, ya, za), (xa, yb, zb), (xb, yb, zb), (xb, ya, za)], DWOOD, 0.4)                   # its underside
    for x, sgn in ((xa, -1), (xb, 1)):                                                       # its sides, both faces
        out = [(x, ya, za), (x, yb, zb), (x, yb, zb + 0.38), (x, ya, za + 0.38)]
        inn = [(x - sgn * 0.02, y, z) for _, y, z in out]
        g.pf(out if sgn > 0 else list(reversed(out)), WOOD, 0.48)
        g.pf(list(reversed(inn)) if sgn > 0 else inn, WOOD, 0.4)
    g.pf([(xa, ya, za + 0.28), (xb, ya, za + 0.28), (xb, yb, zb + 0.28), (xa, yb, zb + 0.28)], WATER, 0.6)
    card(g, [(xa + 0.08, ya, za + 0.28), (xb - 0.08, ya, za + 0.28), (xb - 0.08, ya - 0.55, cz + 2.75),
             (xa + 0.08, ya - 0.55, cz + 2.75)], WATER, 0.62)
    for y in (3.4, 4.6):                                                                     # its posts, clear of the wheel
        K.tube(g, (wx, y, 0.0), (wx, y, za + (zb - za) * (y - ya) / (yb - ya)), 0.1, DWOOD, n=4, var=0.4,
               cap0=False, cap1=False)
    p = kit.add('vale_watermill', g, budget=420, sheet={'az': 40, 'el': 18})
    p.info['footprint'] = [2 * hx, 2 * hy]


def tannery(kit):
    """The tannery: an open-sided timber shed under a thatch roof with a plank back wall (+Y), hides thrown over two
    drying rails under it, a scraping beam inside, a hide stretched on a frame at the front-left and three round
    tanning vats in front (−Y) — two of brown tan liquor, one of white lime."""
    rng = R('vale_tannery')
    g = K.Geo()
    hx, y0, y1, h, zr = 4.4, -2.1, 2.5, 3.1, 5.5
    for x in (-4.25, 0.0, 4.25):
        for y in (y0 + 0.15, y1 - 0.3):
            K.box(g, (x - 0.13, y - 0.13, 0), (x + 0.13, y + 0.13, h - 0.25), DWOOD, 0.42 + jit(rng, 0.04),
                  skip=('-z', '+z'))
    K.box(g, (-hx, y1 - 0.2, 0), (hx, y1, h - 0.25), WOOD, 0.46, skip=('-z', '+z'))
    K.box(g, (-hx - 0.05, y0, h - 0.25), (hx + 0.05, y0 + 0.3, h), DWOOD, 0.4)
    K.box(g, (-hx - 0.05, y1 - 0.3, h - 0.25), (hx + 0.05, y1, h), DWOOD, 0.4, skip=('-z',))
    for x in (-4.25, 4.25):
        K.box(g, (x - 0.12, y0 + 0.3, h - 0.25), (x + 0.12, y1 - 0.3, h), DWOOD, 0.4, skip=('-y', '+y'))
    gable_roof(g, -hx, hx, y0, y1, eave_z(h, zr, (y1 - y0) / 2, 0.4), zr, ROPE, var=0.5, overhang=0.4)
    ym = (y0 + y1) / 2
    for x, sgn in ((-hx, -1), (hx, 1)):
        pts = [(x, y0, h), (x, y1, h), (x, ym, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), DWOOD, 0.44)
        g.pf(list(reversed(pts)) if sgn > 0 else pts, DWOOD, 0.38)
    for y in (-1.5, 0.4):                       # drying rails near the open front, their ends under the tie beams
        K.tube(g, (-4.3, y, h - 0.29), (4.3, y, h - 0.29), 0.04, DWOOD, n=4, var=0.4, cap0=False, cap1=False)
        for i, x in enumerate((-2.6, -1.0 if y < 0 else 1.0, 2.6)):
            slot = (ROPE, DSTONE, BONE)[(i + (y > 0)) % 3]
            for sgn in (-1, 1):
                q = [(x - 0.5, y, h - 0.26), (x + 0.5, y, h - 0.26), (x + 0.45, y + sgn * 0.12, 1.45),
                     (x - 0.45, y + sgn * 0.12, 1.45)]
                g.pf(q if sgn > 0 else list(reversed(q)), slot, 0.48 + jit(rng, 0.05))
    K.tube(g, (-3.4, 1.5, 0.0), (-2.1, 1.5, 1.0), 0.13, DWOOD, n=5, var=0.46, cap0=False)      # the scraping beam
    K.tube(g, (-2.35, 1.35, 0.0), (-2.25, 1.5, 0.85), 0.04, DWOOD, n=3, var=0.4, cap0=False, cap1=False)
    K.tube(g, (-2.35, 1.65, 0.0), (-2.25, 1.5, 0.85), 0.04, DWOOD, n=3, var=0.4, cap0=False, cap1=False)
    mk = g.mark()                                                                              # the stretching frame
    for x in (-0.6, 0.6):
        K.box(g, (x - 0.05, -0.05, 0), (x + 0.05, 0.05, 1.85), WOOD, 0.44, skip=('-z',))
    for z in (0.3, 1.65):
        K.box(g, (-0.65, -0.04, z), (0.65, 0.04, z + 0.09), DWOOD, 0.42, skip=('-x', '+x'))
    hide = [(-0.45, 0.48), (0.45, 0.48), (0.5, 1.0), (0.42, 1.56), (-0.42, 1.56), (-0.5, 1.0)]
    plate(g, hide, -0.01, ROPE, 0.46)
    g.pf([(x, 0.01, z) for x, z in reversed(hide)], ROPE, 0.38)
    g.transform(T(-3.5, -3.3, 0) @ Rz(12) @ Rx(-6), mk)
    for x, liquor in ((-1.9, DSTONE), (0.0, BONE), (1.9, DSTONE)):                             # the vats
        K.lathe(g, [(0.72, 0.0), (0.72, 0.72), (0.6, 0.72)], 7, DWOOD, lambda b, k: 0.44 + 0.1 * b, smooth=0,
                cap0=False, cap1=False, m=T(x, -3.75, 0))
        K.disc(g, 0.6, 7, liquor, z=0.69, var=0.36 if liquor == DSTONE else 0.62, m=T(x, -3.75, 0))
    p = kit.add('vale_tannery', g, budget=360, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = [2 * hx, 2 * max(-y0, y1)]


def market_hall(kit):
    """The market hall: a timber-framed upper room raised on eight stone pillars over a flagged floor where traders
    sell in the shade (the hero walks under it), windows on all sides, a shingle roof with a little lantern on the
    ridge."""
    rng = R('vale_market_hall')
    g = K.Geo()
    K.box(g, (-4.7, -2.8, 0), (4.7, 2.8, 0.12), STONE, 0.4, skip=('-z',))
    for x in (-4.3, -1.43, 1.43, 4.3):
        for y in (-2.4, 2.4):
            K.box(g, (x - 0.25, y - 0.25, 0.12), (x + 0.25, y + 0.25, 2.75), STONE, 0.54 + jit(rng, 0.04),
                  skip=('-z', '+z'))
    K.box(g, (-4.65, -2.75, 2.75), (4.65, 2.75, 3.05), DWOOD, 0.4)
    ux, uy, z0, z1, zr = 4.72, 2.95, 3.05, 5.3, 7.3
    framed_upper(g, rng, ux, uy, z0, z1, studs_y=(-2.4, 0.0, 2.4), studs_x=(0.0,))
    for x in (-1.2, 1.2):
        town_window(g, T(x, -uy, 3.75), w=0.9, h=1.0)
        town_window(g, on_face('+y', uy, x, 3.75), w=0.9, h=1.0)
    for side, at in (('-x', -ux), ('+x', ux)):
        town_window(g, on_face(side, at, -1.4, 3.75), w=0.9, h=1.0)
    gable_roof(g, -ux, ux, -uy, uy, eave_z(z1 + 0.02, zr, uy, 0.2), zr, DWOOD, var=0.44, overhang=0.2)
    for x, sgn in ((-ux, -1), (ux, 1)):
        pts = [(x, -uy, z1), (x, uy, z1), (x, 0.0, zr - 0.06)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), BONE, 0.5)
    K.box(g, (-0.3, -0.3, zr - 0.3), (0.3, 0.3, zr + 0.45), WOOD, 0.48, skip=('-z',))         # the ridge lantern
    pyramid(g, 0, 0, 0.42, 0.42, zr + 0.45, zr + 1.0, DWOOD, var=0.42)
    p = kit.add('vale_market_hall', g, budget=300, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = [2 * ux, 2 * uy]


def market_cross(kit):
    """The market cross: three octagonal steps, a slender tapering shaft and a cross head, ~4.5 m."""
    rng = R('vale_market_cross')
    g = K.Geo()
    for i, (r, z0, z1) in enumerate(((1.5, 0.0, 0.28), (1.1, 0.28, 0.56), (0.72, 0.56, 0.84))):
        K.lathe(g, [(r, z0), (r, z1)], 8, STONE, 0.42 + 0.07 * i + jit(rng, 0.02), smooth=0, cap0=False,
                phase=math.pi / 8)
    K.tube(g, (0, 0, 0.84), (0, 0, 4.5), 0.17, STONE, r1=0.1, n=4, var=0.62, smooth=0, cap0=False)
    K.box(g, (-0.38, -0.08, 3.85), (0.38, 0.08, 4.02), STONE, 0.66)
    p = kit.add('vale_market_cross', g, budget=90, sheet={'az': 30, 'el': 16})
    p.info['footprint'] = [3.0, 3.0]


def stocks(kit):
    """The stocks: two posts holding a two-part board with two leg holes, a plank bench behind it."""
    g = K.Geo()
    for x in (-0.75, 0.75):
        K.box(g, (x - 0.07, -0.07, 0), (x + 0.07, 0.07, 0.95), DWOOD, 0.42, skip=('-z',))
    K.box(g, (-0.82, -0.05, 0.3), (0.82, 0.05, 0.68), WOOD, 0.5, skip=('-x', '+x'))
    stroke(g, (-0.68, 0.49), (0.68, 0.49), 0.02, -0.055, DWOOD, 0.3)
    for x in (-0.3, 0.3):
        K.disc(g, 0.08, 6, INK, var=0.5, m=T(x, -0.058, 0.49) @ Rx(90))
    K.box(g, (-0.7, 0.35, 0), (0.7, 0.65, 0.42), WOOD, 0.46, skip=('-z',))
    p = kit.add('vale_stocks', g, budget=50, sheet={'az': 30, 'el': 20})
    p.info['footprint'] = plan_size(g)


def low_wall(kit):
    """A 2 m run of the churchyard's low wall of rough stone, tiling along x (−1…+1): a body under a pale coping, two
    courses on each face."""
    rng = R('vale_low_wall')
    g = K.Geo()
    K.box(g, (-1.0, -0.27, 0), (1.0, 0.27, 0.8), STONE, 0.44 + jit(rng, 0.04), skip=('-z', '-x', '+x'))
    K.box(g, (-1.0, -0.32, 0.8), (1.0, 0.32, 0.98), STONE, 0.62, skip=('-z', '-x', '+x'))
    for side, at in (('-y', -0.27), ('+y', 0.27)):
        m = on_face(side, at, 0.0, 0.0)
        for z in (0.28, 0.55):
            flat_strip(g, m, (-1.0, z), (1.0, z), 0.05, STONE, 0.3, y=-0.006)
    p = kit.add('vale_low_wall', g, budget=24, sheet={'az': 30, 'el': 20},
                bake={'ground': 0.0, 'occluders': [('vale_low_wall', (-2.0, 0, 0)), ('vale_low_wall', (2.0, 0, 0))]})
    p.info['span'] = 2.0
    p.info['footprint'] = [2.0, 0.64]


def gravestone(kit):
    """A small headstone with a rounded head and a cross cut in it, leaning a little back and to one side."""
    g = K.Geo()
    K.slab_xz(g, [(-0.24, -0.15), (0.24, -0.15), (0.24, 0.6), (0.12, 0.76), (-0.12, 0.76), (-0.24, 0.6)], -0.06, 0.06,
              STONE, 0.58)
    stroke(g, (0.0, 0.32), (0.0, 0.64), 0.045, -0.065, INK, 0.4)
    stroke(g, (-0.1, 0.53), (0.1, 0.53), 0.045, -0.065, INK, 0.4)
    g.transform(Ry(5) @ Rx(-7))
    p = kit.add('vale_gravestone', g, budget=24, sheet={'az': 30, 'el': 20})
    p.info['footprint'] = [0.6, 0.3]


def garden_plot(kit):
    """A burgage garden, 5 × 4 m: a bed of dug earth in three ridged rows, cabbages along two of them, two wigwams of
    bean poles with their green climbing them on the third, a low wattle edge round it."""
    rng = R('vale_garden_plot')
    g = K.Geo()
    W, D = 2.5, 2.0
    g.pf([(-W, -D, 0.02), (W, -D, 0.02), (W, D, 0.02), (-W, D, 0.02)], DSTONE, 0.42)
    for y in (-1.1, 0.0, 1.1):
        g.pf([(-2.2, y - 0.3, 0.02), (2.2, y - 0.3, 0.02), (2.2, y, 0.18), (-2.2, y, 0.18)], DSTONE, 0.5)
        g.pf([(2.2, y + 0.3, 0.02), (-2.2, y + 0.3, 0.02), (-2.2, y, 0.18), (2.2, y, 0.18)], DSTONE, 0.36)
        g.pf([(-2.2, y + 0.3, 0.02), (-2.2, y - 0.3, 0.02), (-2.2, y, 0.18)], DSTONE, 0.4)
        g.pf([(2.2, y - 0.3, 0.02), (2.2, y + 0.3, 0.02), (2.2, y, 0.18)], DSTONE, 0.4)
    for x, y in ((-1.5, -1.1), (0.0, -1.1), (1.5, -1.1), (-0.75, 0.0), (0.75, 0.0)):
        K.rock(g, rng, (x + jit(rng, 0.1), y, 0.32), (0.3, 0.3, 0.2), CLOTH1, n=6, var=0.58 + jit(rng, 0.06),
               flat=False)
    for x in (-1.2, 1.2):
        for a in (90, 210, 330):
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            K.tube(g, (x + 0.32 * c, 1.1 + 0.32 * s, 0.05), (x, 1.1, 1.7), 0.022, WOOD, n=3, var=0.5, cap0=False,
                   cap1=False)
        K.rock(g, rng, (x, 1.1, 0.85), (0.24, 0.24, 0.6), CLOTH1, n=6, var=0.46, flat=False)
    for sy in (-1, 1):
        K.box(g, (-W, sy * D - 0.04, 0), (W, sy * D + 0.04, 0.38), DWOOD, 0.5 + jit(rng, 0.04), skip=('-z', '-x', '+x'))
    for sx in (-1, 1):
        K.box(g, (sx * W - 0.04, -D, 0), (sx * W + 0.04, D, 0.38), DWOOD, 0.46 + jit(rng, 0.04), skip=('-z', '-y', '+y'))
    p = kit.add('vale_garden_plot', g, budget=140, sheet={'az': 30, 'el': 34})
    p.info['footprint'] = [2 * W, 2 * D]


def cart(kit):
    """A two-wheeled hand cart: a plank bed with low sides and a tail board, two handles to the front (−x) resting on
    the ground, solid plank wheels on an axle, two sacks in it."""
    rng = R('vale_cart')
    g = K.Geo()
    K.box(g, (-0.7, -0.5, 0.5), (0.75, 0.5, 0.58), WOOD, 0.48, skip=('-z',))
    for sy in (-1, 1):
        ya, yb = sorted((sy * 0.5, sy * 0.44))
        K.box(g, (-0.7, ya, 0.58), (0.75, yb, 0.82), WOOD, 0.44, skip=('-z', '-x', '+x'))
    K.box(g, (0.69, -0.44, 0.58), (0.75, 0.44, 0.82), WOOD, 0.44, skip=('-z', '-y', '+y'))
    for sy in (-1, 1):
        K.tube(g, (-0.6, sy * 0.4, 0.54), (-1.55, sy * 0.4, 0.05), 0.035, DWOOD, n=3, var=0.42, cap0=False, cap1=False)
    cx, cz, r = 0.12, 0.42, 0.42
    for sy in (-1, 1):
        K.disc(g, r, 6, DWOOD, var=0.46, m=T(cx, sy * 0.6, cz) @ Rx(-90 * sy), phase=math.pi / 6)
        K.disc(g, r, 6, DWOOD, var=0.38, m=T(cx, sy * 0.56, cz) @ Rx(90 * sy), phase=math.pi / 6)
        K.disc(g, 0.12, 4, BRASS, var=0.56, m=T(cx, sy * 0.61, cz) @ Rx(-90 * sy))             # its hub
    K.tube(g, (cx, -0.6, cz), (cx, 0.6, cz), 0.04, IRON, n=3, var=0.44, cap0=False, cap1=False)
    K.rock(g, rng, (-0.2, 0.0, 0.78), (0.28, 0.3, 0.22), BONE, n=7, var=0.56)
    K.rock(g, rng, (0.38, 0.05, 0.76), (0.26, 0.28, 0.2), ROPE, n=7, var=0.5)
    p = kit.add('vale_cart', g, budget=90, sheet={'az': 30, 'el': 24})
    p.info['footprint'] = plan_size(g)


def arena_stand(kit):
    """One segment of the arena's ring of stands (twenty stand round a circle of radius 19.5 m, each facing the centre):
    a wedge 5 m deep whose ends follow the ring's radii (5.4 m wide at the front, 7 m at the back) so neighbours meet;
    at the front (−Y, the arena) a stone barrier with a timber rail and an aisle, three stepped tiers with plank
    benches rising away from the floor, a back wall 4.5 m tall with three merlons, a hanging banner and two pennants."""
    rng = R('vale_arena_stand')
    g = K.Geo()
    tn = math.tan(math.radians(9.0))

    def hw(y):
        return (19.5 + y) * tn
    ys = [-2.5, -1.4, -0.3, 0.8, 1.9, 2.5]
    zs = [1.2, 1.9, 2.6, 3.3, 4.5]
    for i in range(5):
        ya, yb, z, zlo = ys[i], ys[i + 1], zs[i], (zs[i - 1] if i else 0.0)
        v = 0.5 + jit(rng, 0.03)
        g.pf([(-hw(ya), ya, zlo), (hw(ya), ya, zlo), (hw(ya), ya, z), (-hw(ya), ya, z)], STONE, v)          # riser
        g.pf([(-hw(ya), ya, z), (hw(ya), ya, z), (hw(yb), yb, z), (-hw(yb), yb, z)], STONE, v + 0.1)        # tread
        g.pf([(-hw(yb), yb, 0.0), (-hw(ya), ya, 0.0), (-hw(ya), ya, z), (-hw(yb), yb, z)], STONE, v - 0.04)  # ends
        g.pf([(hw(ya), ya, 0.0), (hw(yb), yb, 0.0), (hw(yb), yb, z), (hw(ya), ya, z)], STONE, v - 0.04)
    g.pf([(hw(2.5), 2.5, 0.0), (-hw(2.5), 2.5, 0.0), (-hw(2.5), 2.5, 4.5), (hw(2.5), 2.5, 4.5)], STONE, 0.48)
    m = T(0, 2.5, 0) @ Rz(180)
    for z in (1.5, 3.0):
        flat_strip(g, m, (-hw(2.5), z), (hw(2.5), z), 0.06, STONE, 0.34, y=-0.006)
    K.box(g, (-hw(-2.5), -2.5, 1.2), (hw(-2.5), -2.32, 1.55), WOOD, 0.5, skip=('-z', '-x', '+x'))           # the rail
    for i in (1, 2, 3):                                                                                     # benches
        ya = ys[i]
        K.box(g, (-hw(ya) + 0.02, ya + 0.12, zs[i]), (hw(ya) - 0.02, ya + 0.52, zs[i] + 0.4), WOOD,
              0.48 + jit(rng, 0.04), skip=('-z', '-x', '+x'))
    crenels(g, -hw(2.2), hw(2.2), 3, 1.9, 2.5, 4.5, 5.0, rng=rng)
    yb = 1.88                                                                                               # banner
    plate(g, [(0.0, 3.42), (0.42, 3.75), (0.42, 4.42), (-0.42, 4.42), (-0.42, 3.75)], yb, CLOTH1, 0.5)
    plate(g, [(0.0, 3.8), (0.17, 4.04), (0.0, 4.28), (-0.17, 4.04)], yb - 0.01, BRASS, 0.62)
    for x in (-hw(2.2) + 0.4, hw(2.2) - 0.4):                                                               # pennants
        K.tube(g, (x, 2.2, 5.0), (x, 2.2, 6.5), 0.035, DWOOD, n=3, var=0.4, cap0=False, cap1=False)
        flag = [(x, 2.2, 6.45), (x, 2.2, 6.0), (x + 0.75, 2.2, 6.22)]
        g.pf(flag, CLOTH2, 0.5)
        g.pf(list(reversed(flag)), CLOTH2, 0.44)
    p = kit.add('vale_arena_stand', g, budget=160, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = [round(2 * hw(2.5), 2), 5.0]
    p.info['ring'] = {'radius': 19.5, 'segments': 20}


def arena_arch(kit):
    """The arena's main gate: two stone piers either side of a 4.8 m opening carrying a segmental stone arch (its soffit
    4.0 m at the piers, 4.75 m at the crown), a plank sign board on top with three red claw marks on both faces, two
    green banners hung from the arch on each face and a brazier glowing at each end; open beneath (the hero walks
    through along y), no collider."""
    rng = R('vale_arena_arch')
    g = K.Geo()
    W, pw, d, top = 3.0, 0.6, 0.7, 5.3
    for sx in (-1, 1):
        x0, x1 = sorted((sx * W, sx * (W - pw)))
        K.box(g, (x0, -d, 0), (x1, d, 4.0), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    xs, zs = (-3.0, -2.4, -1.2, 0.0, 1.2, 2.4, 3.0), (4.0, 4.0, 4.55, 4.75, 4.55, 4.0, 4.0)
    for i in range(6):
        q = [(xs[i], zs[i]), (xs[i + 1], zs[i + 1]), (xs[i + 1], top), (xs[i], top)]
        plate(g, q, -d, STONE, 0.52 + jit(rng, 0.03))
        g.pf([(x, d, z) for x, z in reversed(q)], STONE, 0.52 + jit(rng, 0.03))
        if 0 < i < 5:
            g.pf([(xs[i], -d, zs[i]), (xs[i], d, zs[i]), (xs[i + 1], d, zs[i + 1]), (xs[i + 1], -d, zs[i + 1])],
                 STONE, 0.42)
    g.pf([(-W, -d, top), (W, -d, top), (W, d, top), (-W, d, top)], STONE, 0.46)
    for x, sgn in ((-W, -1), (W, 1)):
        q = [(x, -d, 4.0), (x, d, 4.0), (x, d, top), (x, -d, top)]
        g.pf(q if sgn > 0 else list(reversed(q)), STONE, 0.46)
    K.box(g, (-1.8, -0.1, top), (1.8, 0.1, top + 1.0), DWOOD, 0.44, skip=('-z',))           # the sign board
    for yb, sgn in ((-0.105, 1), (0.105, -1)):
        for k in (-1, 0, 1):
            a, b = (k * 0.42 - 0.22, top + 0.2), (k * 0.42 + 0.22, top + 0.82)
            if sgn < 0:
                a, b = (-a[0], a[1]), (-b[0], b[1])
            mk = g.mark()
            stroke(g, a, b, 0.1, -0.105, GEM, 0.5)
            if sgn < 0:
                g.transform(Rz(180), mk)
    for x in (-2.7, 2.7):                                                                     # the banners
        for yb, sgn in ((-d - 0.02, 1), (d + 0.02, -1)):
            q = [(x, 1.9), (x + 0.32, 2.3), (x + 0.32, 4.0), (x - 0.32, 4.0), (x - 0.32, 2.3)]
            if sgn > 0:
                plate(g, q, yb, CLOTH2, 0.5)
            else:
                g.pf([(xx, yb, z) for xx, z in reversed(q)], CLOTH2, 0.46)
    for x in (-2.7, 2.7):                                                                     # the braziers
        K.lathe(g, [(0.12, top), (0.32, top + 0.32)], 5, IRON, 0.46, smooth=0, cap1=False, m=T(x, 0, 0))
        K.lathe(g, [(0.24, top + 0.26), (0.0, top + 0.78)], 4, GLOW, 0.5, smooth=0, cap0=False, m=T(x, 0, 0))
    p = kit.add('vale_arena_arch', g, budget=140, sheet={'az': 30, 'el': 14})
    for x in (-2.7, 2.7):
        kit.light(p, (x, 0, top + 0.6), 'fire')
        kit.fx(p, (x, 0, top + 0.5), 'glow')
    p.info['footprint'] = [2 * W, 2 * d]
    p.info['no_collider'] = True


def arena_beast_gate(kit):
    """The beasts' gate: a heavy timber portcullis (five uprights with iron spikes at their feet, three cross bars),
    closed, in a stone frame 6 m wide — two piers and a deep lintel with a horned skull on its outer face (−Y) — and from
    the arena (+Y) the dark passage beyond the bars."""
    rng = R('vale_arena_beast_gate')
    g = K.Geo()
    W, ow, d, oh = 3.0, 2.15, 0.8, 3.6
    for sx in (-1, 1):
        x0, x1 = sorted((sx * W, sx * ow))
        K.box(g, (x0, -d, 0), (x1, d, oh), STONE, 0.5 + jit(rng, 0.03), skip=('-z', '+z'))
    K.box(g, (-W, -d, oh), (W, d, oh + 1.0), STONE, 0.46)
    # the dark passage beyond the bars, seen from the arena (+Y: the town turns the gate's front, −Y, outward)
    g.pf([(x, -0.75, z) for x, z in reversed([(-ow, 0.0), (ow, 0.0), (ow, oh), (-ow, oh)])], INK, 0.5)
    for i in range(5):                                                                        # the portcullis
        x = -1.7 + i * 0.85
        K.box(g, (x - 0.09, -0.09, 0.16), (x + 0.09, 0.09, oh), WOOD, 0.5 + jit(rng, 0.05), skip=('-z', '+z'))
        K.lathe(g, [(0.0, 0.0), (0.1, 0.16)], 4, IRON, 0.5, smooth=0, cap1=False, phase=math.pi / 4, m=T(x, 0, 0))
    for z in (0.8, 1.9, 3.0):
        K.box(g, (-ow, -0.13, z), (ow, 0.13, z + 0.17), IRON, 0.46, skip=('-x', '+x'))
    yb = -d - 0.01                                                                            # the horned skull
    plate(g, [(0.0, oh + 0.12), (0.2, oh + 0.3), (0.22, oh + 0.62), (-0.22, oh + 0.62), (-0.2, oh + 0.3)], yb, BONE,
          0.64)
    for sgn in (-1, 1):
        plate(g, [(sgn * 0.08, oh + 0.36), (sgn * 0.16, oh + 0.36), (sgn * 0.16, oh + 0.46), (sgn * 0.08, oh + 0.46)]
              if sgn > 0 else [(-0.16, oh + 0.36), (-0.08, oh + 0.36), (-0.08, oh + 0.46), (-0.16, oh + 0.46)],
              yb - 0.006, INK, 0.5)
        tri = [(sgn * 0.2, oh + 0.56), (sgn * 0.52, oh + 0.86), (sgn * 0.26, oh + 0.64)]
        plate(g, tri if sgn > 0 else list(reversed(tri)), yb, BONE, 0.58)
    p = kit.add('vale_arena_beast_gate', g, budget=140, sheet={'az': 205, 'el': 14})
    p.info['footprint'] = [2 * W, 2 * d]


# ====================================================================== the wilds, levels 5 to 20 (Phase W10)
# The places past the town: camps (a tent, a big camp tent), ruins (the toll house, a broken wall), the marsh (the
# drowned chapel, a dead tree, bones), the troll cave, the wyvern's nest, Gravehollow Keep's gate (the dungeon door),
# steel-stone, an ash and a willow. Same conventions: the origin at the footprint's centre on the ground, the front
# (a door, an opening) toward −Y, info['footprint'] the plan's [x, y] in metres.
def newell(pts):
    """The (unnormalised) normal of a polygon, robust to collinear corners."""
    n = Vector((0.0, 0.0, 0.0))
    for i in range(len(pts)):
        a, b = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


def face_to(g, pts, slot, var, toward):
    """A face through `pts` (repeated corners dropped) wound so its normal points along `toward` (→ its index)."""
    q = []
    for c in pts:
        if not q or (Vector(c) - Vector(q[-1])).length > 1e-5:
            q.append(tuple(c))
    if len(q) > 2 and (Vector(q[0]) - Vector(q[-1])).length < 1e-5:
        q.pop()
    if len(q) < 3:
        return None
    if newell(q).dot(Vector(toward)) < 0:
        q = list(reversed(q))
    return g.pf(q, slot, var)


def canvas(g, pts, slot, var, toward, inner=0.3, gap=0.02):
    """A sheet seen from both sides: its face toward `toward` at G `var`, its back a hair behind at G `inner`."""
    face_to(g, pts, slot, var, toward)
    d = Vector(toward).normalized() * gap
    face_to(g, [tuple(Vector(p) - d) for p in pts], slot, inner, tuple(-Vector(toward)))


def ccw(pts):
    """(x, z) points ordered counter-clockwise as seen from the front (−Y)."""
    s = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    return list(pts) if s > 0 else list(reversed(pts))


def rope(g, a, b, r=0.014):
    K.tube(g, a, b, r, ROPE, n=3, var=0.56, cap0=False, cap1=False)


def peg(g, x, y):
    K.tube(g, (x, y, -0.04), (x, y, 0.17), 0.03, WOOD, n=3, var=0.4, cap0=False)


def hinge(a, b, deg):
    """The matrix turning `deg` degrees about the axis a → b."""
    a, b = Vector(a), Vector(b)
    return Matrix.Translation(a) @ Matrix.Rotation(math.radians(deg), 4, (b - a).normalized()) @ Matrix.Translation(-a)


def beam(g, p0, p1, w, h, slot, var=0.42):
    """A squared timber from p0 to p1, w wide and h deep (12 tris)."""
    d = Vector(p1) - Vector(p0)
    q = Vector((1, 0, 0)).rotation_difference(d.normalized())
    K.box(g, (0.0, -w / 2, -h / 2), (d.length, w / 2, h / 2), slot, var,
          m=Matrix.Translation(Vector(p0)) @ q.to_matrix().to_4x4())


def lerp3(a, b, f):
    return tuple(Vector(a).lerp(Vector(b), f))


def ruin_wall(g, rng, x0, x1, t, tops, openings=(), z0=0.0, slot=STONE, var=0.46, ends=(True, True), back=True):
    """A broken stone wall from x0 to x1 along x, its face at y 0 toward −Y and `t` thick (to y t), standing on z0.
    `tops` = [(x, z), …] its broken top (piecewise linear over x0 … x1); `openings` = [(xc, hw, sill, spring, apex),
    …] doorways and windows through it (sill ≤ z0: down to the foot; apex == spring: a flat lintel, else a pointed
    head) — where the top falls below an opening's head the head is gone and the opening is a gap. Fronts, backs,
    sloped tops, reveals, sills and soffits, the ends (`ends`); 6 tris a top segment. Returns its mark."""
    mk = g.mark()
    tx = [p[0] for p in tops]
    tz = [p[1] for p in tops]

    def top(x):
        if x <= tx[0]:
            return tz[0]
        for i in range(len(tx) - 1):
            if x <= tx[i + 1]:
                return tz[i] + (tz[i + 1] - tz[i]) * (x - tx[i]) / max(1e-9, tx[i + 1] - tx[i])
        return tz[-1]

    def head(o, x):
        xc, hw, sill, spring, apex = o
        return spring + (apex - spring) * max(0.0, 1.0 - abs(x - xc) / hw)

    xs = {x0, x1} | {x for x in tx if x0 < x < x1}
    for o in openings:
        xs |= {x for x in (o[0] - o[1], o[0], o[0] + o[1]) if x0 < x < x1}
    pts = []
    for x in sorted(xs):
        if not pts or x - pts[-1] > 1e-4:
            pts.append(x)

    def block(a, b, ba, bb, ta, tb, soffit):
        if ta - ba < 0.02 and tb - bb < 0.02:
            return
        v = var + jit(rng, 0.05)
        face_to(g, [(a, 0, ba), (b, 0, bb), (b, 0, tb), (a, 0, ta)], slot, v, (0, -1, 0))
        if back:
            face_to(g, [(a, t, ba), (b, t, bb), (b, t, tb), (a, t, ta)], slot, v - 0.06, (0, 1, 0))
        face_to(g, [(a, 0, ta), (b, 0, tb), (b, t, tb), (a, t, ta)], slot, min(1.0, v + 0.1), (0, 0, 1))
        if soffit:
            face_to(g, [(a, 0, ba), (b, 0, bb), (b, t, bb), (a, t, ba)], slot, v - 0.12, (0, 0, -1))

    built = {}
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        mid = (a + b) / 2
        ta, tb = top(a), top(b)
        oi = next((k for k, o in enumerate(openings) if o[0] - o[1] - 1e-6 <= mid <= o[0] + o[1] + 1e-6), None)
        if oi is None:
            block(a, b, z0, z0, ta, tb, False)
            continue
        o = openings[oi]
        xc, hw, sill, spring, apex = o
        if sill > z0 + 1e-3:
            block(a, b, z0, z0, min(sill, ta), min(sill, tb), False)
        ha, hb = head(o, a), head(o, b)
        ok = ta > ha + 0.05 and tb > hb + 0.05
        built[(oi, 'l' if mid < xc else 'r')] = ok
        if ok:
            block(a, b, ha, hb, ta, tb, True)
    if ends[0]:
        face_to(g, [(x0, 0, z0), (x0, t, z0), (x0, t, top(x0)), (x0, 0, top(x0))], slot, var - 0.04, (-1, 0, 0))
    if ends[1]:
        face_to(g, [(x1, 0, z0), (x1, t, z0), (x1, t, top(x1)), (x1, 0, top(x1))], slot, var - 0.04, (1, 0, 0))
    for oi, (xc, hw, sill, spring, apex) in enumerate(openings):
        zb = max(z0, sill)
        for xj, toward, side in ((xc - hw, 1, 'l'), (xc + hw, -1, 'r')):
            if not (x0 < xj < x1):
                continue
            zt = top(xj) if not built.get((oi, side), False) else min(spring, top(xj))
            if zt - zb > 0.02:
                face_to(g, [(xj, 0, zb), (xj, t, zb), (xj, t, zt), (xj, 0, zt)], slot, var - 0.1, (toward, 0, 0))
        hl, hr = built.get((oi, 'l'), False), built.get((oi, 'r'), False)
        if hl != hr:                                        # half a head standing: its broken end at the apex
            face_to(g, [(xc, 0, apex), (xc, t, apex), (xc, t, top(xc)), (xc, 0, top(xc))], slot, var - 0.08,
                    (1 if hl else -1, 0, 0))
    return mk


def flip_tops(tops):
    """A wall's tops given along the world's x for a wall turned 180° (its local x runs the other way)."""
    return [(-x, z) for x, z in reversed(tops)]


def algae(g, rng, x0, x1, y, z0, z1, toward, n):
    """A ragged band of algae (slot 12) on a wall face at y facing ±Y (`toward` −1 / +1), from z0 up to about z1."""
    xs = [x0 + (x1 - x0) * i / n for i in range(n + 1)]
    zs = [z1 + jit(rng, 0.14) for _ in xs]
    for i in range(n):
        face_to(g, [(xs[i], y, z0), (xs[i + 1], y, z0), (xs[i + 1], y, zs[i + 1]), (xs[i], y, zs[i])], MOSS,
                0.16 + jit(rng, 0.05), (0, toward, 0))


def tent(kit):
    """A canvas A-frame tent 2.6 m wide and 3 m long, its ridge along y on two poles and a ridge pole, the front (−Y)
    open with both flaps tied back, a bedroll and a pack inside; guy ropes from the ridge ends to pegs, a peg at each
    corner (a camp's sleeping tent)."""
    rng = R('vale_tent')
    g = K.Geo()
    hx, hy, zr = 1.3, 1.5, 2.3
    ys = (-hy, 0.0, hy)
    for sx in (-1, 1):
        ridge = [(0.0, y, zr) for y in ys]
        eave = [(sx * (hx - (0.08 if y == 0.0 else 0.0)), y, 0.02) for y in ys]
        for i in range(2):
            canvas(g, [ridge[i], ridge[i + 1], eave[i + 1], eave[i]], BONE, 0.48 + jit(rng, 0.03), (sx, 0, 0.55))
    canvas(g, [(-hx, hy, 0.02), (hx, hy, 0.02), (0.0, hy, zr)], BONE, 0.44, (0, 1, 0))           # the back
    for sx in (-1, 1):                                                                        # the flaps, tied back
        a, b, p = (0.0, -hy, zr), (sx * hx, -hy, 0.02), (0.0, -hy, 0.02)
        sgn = 1 if (hinge(a, b, 5) @ Vector(p)).y < -hy else -1
        m = hinge(a, b, sgn * 250)                    # swung out and folded back against the slope's outside
        canvas(g, [a, b, tuple(m @ Vector(p))], BONE, 0.54, tuple(m.to_3x3() @ Vector((0, -1, 0))), inner=0.4)
    for y in (-hy, hy):                                                                       # the poles
        K.tube(g, (0, y, 0), (0, y, zr + 0.06), 0.035, WOOD, n=4, var=0.42, cap0=False, cap1=False)
    K.tube(g, (0, -hy - 0.14, zr + 0.03), (0, hy + 0.14, zr + 0.03), 0.04, WOOD, n=4, var=0.46)
    for sy in (-1, 1):                                                                        # guy ropes and pegs
        for sx in (-1, 1):
            rope(g, (0, sy * (hy + 0.1), zr + 0.02), (sx * 0.95, sy * 1.96, 0.04))
            peg(g, sx * 0.95, sy * 1.96)
            peg(g, sx * (hx + 0.05), sy * (hy - 0.1))
    K.lathe(g, [(0.0, -0.8), (0.16, -0.77), (0.16, 0.77), (0.0, 0.8)], 5, ROPE,               # the bedroll
            lambda b, k: 0.4 if b == 1 else 0.52, smooth=40, m=T(0.5, 0.2, 0.15) @ Rx(90))
    K.rock(g, rng, (-0.5, 0.8, 0.2), (0.24, 0.2, 0.24), DWOOD, n=7, var=0.46)                   # a pack
    p = kit.add('vale_tent', g, budget=180, sheet={'az': 28, 'el': 20})
    p.info['footprint'] = [3.0, 4.0]


def tent_large(kit):
    """A big camp tent: canvas walls 1.5 m high under a pitched roof (ridge 2.75 m) over 3.8 × 4 m, a door in its front
    (−Y) with the flaps tied back, a cot and a strong chest inside; over it on its own poles an ochre fly (ridge 3.15 m)
    that runs 0.75 m out over the door as a porch, a valance along its front, a brass finial on the front pole; guy
    ropes from the fly's corners to pegs (the bandit chief's tent; the mining camp's)."""
    rng = R('vale_tent_large')
    g = K.Geo()
    hx, y0, y1, zw, zr = 1.9, -2.0, 2.0, 1.5, 2.75

    def roof_z(x):
        return zw + (zr - zw) * (1 - abs(x) / hx)
    for sx in (-1, 1):
        canvas(g, [(sx * hx, y0, 0.0), (sx * hx, y1, 0.0), (sx * hx, y1, zw), (sx * hx, y0, zw)], BONE,
               0.48 + jit(rng, 0.03), (sx, 0, 0))
        canvas(g, [(sx * hx, y0, zw), (sx * hx, y1, zw), (0.0, y1, zr), (0.0, y0, zr)], BONE, 0.52, (sx, 0, 1.5))
    canvas(g, [(-hx, y1, 0), (hx, y1, 0), (hx, y1, zw), (0, y1, zr), (-hx, y1, zw)], BONE, 0.44, (0, 1, 0))
    dw, dh = 0.62, 2.0                                                                        # the front and door
    for sx in (-1, 1):
        canvas(g, [(sx * hx, y0, 0), (sx * dw, y0, 0), (sx * dw, y0, roof_z(dw)), (sx * hx, y0, zw)], BONE, 0.46,
               (0, -1, 0))
    canvas(g, [(-dw, y0, dh), (dw, y0, dh), (dw, y0, roof_z(dw)), (0, y0, zr), (-dw, y0, roof_z(dw))], BONE, 0.46,
           (0, -1, 0))
    for sx in (-1, 1):                                                                        # the flaps, tied back
        a, b = (sx * dw, y0, 0.0), (sx * dw, y0, dh)
        sgn = 1 if (hinge(a, b, 5) @ Vector((0.0, y0, 0.0))).y < y0 else -1
        m = hinge(a, b, sgn * 155)
        q = [a, b, tuple(m @ Vector((0.0, y0, dh))), tuple(m @ Vector((0.0, y0, 0.0)))]
        canvas(g, q, BONE, 0.54, tuple(m.to_3x3() @ Vector((0, -1, 0))), inner=0.4)
    fx, fy0, fy1, fe, fr = 2.15, -2.75, 2.3, 1.62, 3.12                                       # the fly
    ym = (fy0 + fy1) / 2
    for sx in (-1, 1):
        for ya, yb in ((fy0, ym), (ym, fy1)):
            ea = fe - (0.07 if ya == ym else 0.0)
            eb = fe - (0.07 if yb == ym else 0.0)
            canvas(g, [(0, ya, fr), (0, yb, fr), (sx * fx, yb, eb), (sx * fx, ya, ea)], ROPE, 0.44 + jit(rng, 0.03),
                   (sx, 0, 1.4), inner=0.3)
        canvas(g, [(0, fy0, fr), (sx * fx, fy0, fe), (sx * fx, fy0, fe - 0.22), (0, fy0, fr - 0.22)], ROPE, 0.38,
               (0, -1, 0), inner=0.3)                                                         # the valance
    for x, y, z in ((0.0, fy0 - 0.03, fr + 0.26), (0.0, fy1 + 0.03, fr + 0.06)):              # the poles
        K.tube(g, (x, y, 0), (x, y, z), 0.045, WOOD, n=4, var=0.42, cap0=False, cap1=False)
    for sx in (-1, 1):
        zp = fe + (fr - fe) * (1 - (fx - 0.12) / fx)
        K.tube(g, (sx * (fx - 0.12), fy0 + 0.06, 0), (sx * (fx - 0.12), fy0 + 0.06, zp), 0.04, WOOD, n=4, var=0.4,
               cap0=False, cap1=False)
    K.tube(g, (0, fy0 - 0.12, fr + 0.03), (0, fy1 + 0.12, fr + 0.03), 0.045, WOOD, n=4, var=0.46)
    K.lathe(g, [(0.0, fr + 0.24), (0.07, fr + 0.33), (0.0, fr + 0.46)], 4, BRASS, 0.6, smooth=0)
    for sx in (-1, 1):                                                                        # guy ropes, pegs
        for (y, yp) in ((fy0, -2.97), (fy1, 2.97)):
            rope(g, (sx * fx, y, fe), (sx * 2.45, yp, 0.04))
            peg(g, sx * 2.45, yp)
    K.box(g, (-0.45, 1.25, 0), (0.45, 1.8, 0.55), DWOOD, 0.44, skip=('-z',))                  # the chest
    K.box(g, (-0.47, 1.23, 0.36), (0.47, 1.82, 0.43), IRON, 0.46, skip=('-z',))
    K.box(g, (0.75, -0.2, 0), (1.7, 1.75, 0.4), ROPE, 0.4, skip=('-z',))                     # the cot
    p = kit.add('vale_tent_large', g, budget=260, sheet={'az': 28, 'el': 20})
    p.info['footprint'] = [5.0, 6.0]


def toll_ruin(kit):
    """The old toll house by the road, roofless: broken stone walls 0.5 m thick round a 7.2 × 5.2 m room — an empty
    doorway and a window in the front (−Y), the west gable standing to 4 m with its little window, the east wall fallen
    almost to the ground — a roof beam fallen in across the room, rubble at the walls' feet, and before the door the
    toll bar's post with its striped bar snapped off and lying in the road."""
    rng = R('vale_toll_ruin')
    g = K.Geo()
    hx, hy, t = 3.6, 2.6, 0.5

    def wall(tops, openings, m, x0, x1):
        w = K.Geo()
        ruin_wall(w, rng, x0, x1, t, tops, openings, var=0.48)
        g.extend(w, m)
    wall([(-hx, 2.6), (-3.0, 2.6), (-2.96, 2.95), (-2.3, 2.95), (-1.8, 2.55), (-0.2, 2.8), (0.3, 2.8), (0.34, 2.2),
          (1.5, 2.35), (1.95, 2.35), (1.99, 1.55), (2.6, 1.3), (2.64, 0.95), (hx, 0.9)],
         [(-1.0, 0.6, 0.0, 2.0, 2.0), (1.5, 0.45, 0.95, 1.85, 1.85)], T(0, -hy, 0), -hx, hx)
    back = [(-hx, 3.3), (-2.9, 3.3), (-2.86, 3.0), (-1.9, 3.05), (-1.0, 3.45), (-0.4, 3.45), (-0.36, 2.75),
            (1.0, 2.6), (1.6, 2.2), (2.2, 2.2), (2.24, 1.6), (hx, 1.2)]
    wall(flip_tops(back), [(0.9, 0.45, 1.2, 2.1, 2.1)], T(0, hy, 0) @ Rz(180), -hx, hx)
    iw = hy - t                                                                               # the end walls fit between
    wall([(-iw, 3.3), (-1.0, 3.7), (-0.2, 4.0), (0.35, 4.0), (0.39, 3.4), (1.2, 3.55), (1.6, 3.55), (1.64, 3.0),
          (iw, 3.0)],
         [(0.0, 0.4, 1.4, 2.3, 2.3)], T(-hx, 0, 0) @ Rz(-90), -iw, iw)                       # west, the gable
    wall([(-iw, 1.0), (-1.2, 0.65), (-0.3, 0.35), (0.6, 0.45), (1.4, 0.95), (iw, 1.3)], [],
         T(hx, 0, 0) @ Rz(90), -iw, iw)                                                      # east, fallen
    beam(g, (-2.7, 1.5, 0.12), (3.35, -0.75, 0.62), 0.24, 0.22, DWOOD, 0.4)                   # the fallen beam
    beam(g, (-2.0, -1.4, 0.1), (-0.6, -1.9, 0.1), 0.2, 0.18, DWOOD, 0.36)
    for (c, s, v) in (((3.62, -0.6, 0.16), (0.3, 0.26, 0.2), 0.44), ((3.68, 0.7, 0.12), (0.24, 0.2, 0.16), 0.5),
                      ((3.72, 1.6, 0.1), (0.2, 0.16, 0.13), 0.4), ((-3.05, -2.0, 0.14), (0.28, 0.24, 0.18), 0.46),
                      ((2.4, 1.85, 0.12), (0.26, 0.22, 0.16), 0.42), ((0.35, -2.8, 0.1), (0.22, 0.16, 0.13), 0.48),
                      ((-2.6, 1.9, 0.11), (0.22, 0.2, 0.14), 0.44)):
        K.rock(g, rng, c, s, STONE, n=7, var=v)
    K.box(g, (2.72, -2.98, 0), (2.88, -2.82, 1.25), WOOD, 0.42, skip=('-z',))                # the toll bar's post
    K.box(g, (2.66, -2.96, 1.0), (2.94, -2.84, 1.12), IRON, 0.44)
    stub = [Vector((2.8, -2.9, 1.06)), Vector((2.8, -2.9, 1.06)) + Vector((-0.55, 0, 0.45))]
    for k, (f0, f1) in enumerate(((0.0, 0.5), (0.5, 1.0))):                                    # its snapped stub
        beam(g, lerp3(stub[0], stub[1], f0), lerp3(stub[0], stub[1], f1), 0.1, 0.1, BONE if k == 0 else IRON,
             0.6 if k == 0 else 0.5)
    bar = [Vector((2.35, -2.9, 0.06)), Vector((0.2, -2.78, 0.06))]
    for k in range(3):                                                                        # the bar in the road
        beam(g, lerp3(bar[0], bar[1], k / 3), lerp3(bar[0], bar[1], (k + 1) / 3), 0.11, 0.11,
             IRON if k % 2 else BONE, 0.5 if k % 2 else 0.62)
    p = kit.add('vale_toll_ruin', g, budget=600, sheet={'az': 30, 'el': 30})
    p.info['footprint'] = [8.0, 6.0]
    p.info['door'] = {'x': -1.0, 'width': 1.2}


def ruin_wall_piece(kit):
    """A 4 m run of broken wall for ruins, 0.6 m thick, its top ragged between 0.6 and 2 m and back to 1 m at both
    ends (so runs can butt end to end along x), two fallen stones at its foot."""
    rng = R('vale_ruin_wall')
    g = K.Geo()
    mk = ruin_wall(g, rng, -2.0, 2.0, 0.6, [(-2.0, 1.0), (-1.45, 1.0), (-1.41, 1.5), (-0.6, 2.0), (-0.15, 2.0),
                                           (-0.11, 1.45), (0.75, 0.75), (1.35, 0.6), (1.6, 1.0), (2.0, 1.0)],
                   var=0.48)
    g.transform(T(0, -0.3, 0), mk)
    K.rock(g, rng, (0.95, -0.33, 0.08), (0.2, 0.06, 0.09), STONE, n=6, var=0.42)
    K.rock(g, rng, (-1.45, 0.33, 0.08), (0.18, 0.06, 0.09), STONE, n=6, var=0.46)
    p = kit.add('vale_ruin_wall', g, budget=80, sheet={'az': 30, 'el': 22},
                bake={'ground': 0.0, 'occluders': [('vale_ruin_wall', (-4.0, 0, 0)), ('vale_ruin_wall', (4.0, 0, 0))]})
    p.info['span'] = 4.0
    p.info['footprint'] = [4.0, 0.8]


def drowned_chapel(kit):
    """A chapel sinking into the marsh, roofless: the nave's broken walls (8.6 × 6 m, 0.5 m thick) with pointed window
    openings, a sunk doorway in the front (−Y) wall, the west gable standing to 6.4 m round its great window, the east
    wall broken low; at the east end the square bell tower (2.5 m, ~9 m) leaning out of true with its belfry openings
    dark and its top broken; a roof timber fallen across the nave, rubble and the bell half-sunk by the tower; green
    algae at the waterline. The whole sits 0.6 m down (the waterline is the origin's ground, z 0) and tips a little to
    the front."""
    rng = R('vale_drowned_chapel')
    g = K.Geo()
    z0, t = -0.6, 0.5
    nx0, nx1, ny = -6.0, 2.6, 3.0
    iw = ny - t

    def wall(x0, x1, tops, openings, m):
        w = K.Geo()
        ruin_wall(w, rng, x0, x1, t, tops, openings, z0=z0, var=0.44)
        cuts = sorted((o[0] - o[1], o[0] + o[1]) for o in openings if o[2] <= z0 + 1e-3)
        spans, a = [], x0
        for c0, c1 in cuts:
            spans.append((a, c0))
            a = c1
        spans.append((a, x1))
        for a, b in spans:
            if b - a > 0.2:
                n = max(1, int(round((b - a) / 0.9)))
                algae(w, rng, a, b, -0.012, -0.06, 0.3, -1, n)
                algae(w, rng, a, b, t + 0.012, -0.06, 0.24, 1, n)
        g.extend(w, m)
    win = (0.45, 1.3, 2.8, 3.5)
    wall(nx0, nx1, [(-6.0, 4.3), (-5.1, 3.9), (-4.2, 4.2), (-3.2, 3.3), (-2.2, 3.6), (-1.2, 2.95), (0.0, 3.05),
                    (0.8, 2.3), (1.7, 2.55), (2.6, 3.3)],
         [(-1.2, 0.7, z0, 1.5, 2.4), (-4.2,) + win, (1.2,) + win], T(0, -ny, 0))                # the front (−Y)
    wall(-nx1, -nx0, flip_tops([(-6.0, 4.5), (-5.0, 4.8), (-3.9, 3.8), (-2.8, 4.4), (-1.6, 3.5), (-0.4, 3.9),
                                (0.6, 2.8), (1.6, 3.25), (2.6, 2.4)]),
         [(4.2,) + win, (1.0,) + win, (-1.2,) + win], T(0, ny, 0) @ Rz(180))                     # the back
    wall(-iw, iw, [(-iw, 4.4), (-1.5, 5.3), (-0.6, 6.1), (0.0, 6.4), (0.6, 5.5), (1.3, 5.65), (iw, 4.3)],
         [(0.0, 0.75, 1.6, 3.6, 4.8)], T(nx0, 0, 0) @ Rz(-90))                                  # the west gable
    wall(-iw, iw, [(-iw, 3.2), (-1.6, 2.2), (-0.7, 1.15), (0.4, 1.5), (1.3, 0.85), (iw, 2.4)], [],
         T(nx1, 0, 0) @ Rz(90))                                                                # the east, broken
    for x in (-5.3, -2.9, 0.2):                                                              # buttress stumps
        for sgn in (-1, 1):
            mk = g.mark()
            buttress(g, sgn * ny, -x, sgn, depth=0.45, half=0.32, z_wall=2.3, z_out=0.95)
            g.transform(Rz(90), mk)
            g.transform(T(0, 0, z0), mk)
    # the tower, upright in its own frame, then leaning out of true
    tg = K.Geo()
    tcx, th, tz = 3.85, 1.25, 8.2
    K.box(tg, (tcx - th, -th, z0), (tcx + th, th, tz), STONE, 0.47, skip=('-z', '+z'))
    K.box(tg, (tcx - th - 0.08, -th - 0.08, 5.5), (tcx + th + 0.08, th + 0.08, 5.7), STONE, 0.36, skip=('-z',))
    tg.pf([(tcx - th, -th, tz), (tcx + th, -th, tz), (tcx + th, th, tz), (tcx - th, th, tz)], STONE, 0.52)
    for (sx, sy, hgt) in ((-1, -1, 0.95), (1, -1, 0.4), (1, 1, 0.75)):                       # its broken top
        xa, xb = sorted((tcx + sx * th, tcx + sx * (th - 0.55)))
        ya, yb = sorted((sy * th, sy * (th - 0.55)))
        K.box(tg, (xa, ya, tz), (xb, yb, tz + hgt), STONE, 0.5 + jit(rng, 0.04), skip=('-z',))
    belfry = [(-0.3, 0.0), (0.3, 0.0), (0.3, 1.0), (0.0, 1.45), (-0.3, 1.0)]
    for side, at, along in (('-y', -th, tcx), ('+y', th, tcx), ('-x', tcx - th, 0.0), ('+x', tcx + th, 0.0)):
        mk = tg.mark()
        plate(tg, belfry, -0.012, INK, 0.5)
        tg.transform(on_face(side, at, along, 6.1), mk)
    mk = tg.mark()
    plate(tg, [(-0.45, z0 - 0.0), (0.45, z0), (0.45, 1.1), (0.0, 1.75), (-0.45, 1.1)], -0.012, INK, 0.5)
    tg.transform(T(tcx, -th, 0), mk)                                                         # its sunk door
    for side, at, along in (('-y', -th, tcx), ('+y', th, tcx), ('-x', tcx - th, 0.0), ('+x', tcx + th, 0.0)):
        mk = tg.mark()
        algae(tg, rng, -th, th, -0.014, -0.06, 0.34, -1, 2)
        tg.transform(on_face(side, at, along, 0.0), mk)
    lean = T(tcx, 0, 0) @ Ry(5.0) @ Rx(2.0) @ T(-tcx, 0, 0)
    g.extend(tg, lean)
    beam(g, (-5.0, 1.9, -0.1), (-2.0, -2.42, 1.7), 0.3, 0.26, DWOOD, 0.34)                    # the fallen rafter
    for (c, s, v) in (((-3.4, 0.6, 0.0), (0.55, 0.45, 0.42), 0.44), ((-0.9, -1.0, -0.05), (0.42, 0.36, 0.3), 0.4),
                      ((0.9, 1.4, 0.0), (0.5, 0.4, 0.36), 0.46), ((-4.75, -3.22, -0.05), (0.3, 0.2, 0.22), 0.42),
                      ((1.8, -3.35, -0.05), (0.3, 0.2, 0.22), 0.46)):
        K.rock(g, rng, c, s, STONE, n=7, var=v)
    K.lathe(g, [(0.42, 0.0), (0.3, 0.36), (0.2, 0.8), (0.0, 0.93)], 6, BRASS, 0.36, smooth=50, cap_slot=INK,
            m=T(2.55, -2.05, -0.12) @ Rz(-35) @ Ry(78))                                       # the fallen bell
    g.transform(Rx(1.5))                                                                      # the whole tips forward
    p = kit.add('vale_drowned_chapel', g, budget=780, sheet={'az': 30, 'el': 24, 'ground': 0.0})
    p.info['footprint'] = plan_size(g)
    p.info['waterline'] = 0.0
    p.info['sunk'] = 0.6
    p.info['door'] = {'x': -1.2, 'width': 1.4}


def cave_mouth(kit):
    """A rocky outcrop on a hillside, ~9 × 6 m and 6 m high, with a big dark cave opening in its front (−Y): flank
    rocks either side, a brow over the mouth, a back mass topped by a crag and shoulders running down to the ground,
    boulders and scree at the foot; the opening ~4.2 m wide at its floor and ~3.8 m high under the brow, a black throat
    3.4 m deep behind it (trolls stand at its mouth)."""
    rng = R('vale_cave_mouth')
    g = K.Geo()
    yf, yb = -1.3, 0.5                                     # the throat's mouth and its end (1.8 m deep)
    arch = [(-2.1, 0.0), (2.1, 0.0), (2.25, 1.5), (1.95, 2.8), (1.1, 3.7), (0.0, 4.0), (-1.15, 3.65), (-2.0, 2.75),
            (-2.3, 1.4)]
    K.slab_xz(g, list(reversed(arch)), yf, yb, INK, 0.5, front=False)                        # the throat, black
    outer = [(-3.6, 0.0), (3.6, 0.0), (3.85, 1.7), (3.35, 3.5), (2.2, 4.75), (0.0, 5.3), (-2.3, 4.85), (-3.45, 3.4),
             (-3.9, 1.6)]
    yo = [yf + 0.3 + jit(rng, 0.15) for _ in outer]
    for i in range(1, len(arch)):                                                            # the facade (no sill)
        j = (i + 1) % len(arch)
        a0, a1 = (arch[i][0], yf, arch[i][1]), (arch[j][0], yf, arch[j][1])
        o0, o1 = (outer[i][0], yo[i], outer[i][1]), (outer[j][0], yo[j], outer[j][1])
        face_to(g, [a0, a1, o1], STONE, 0.4 + jit(rng, 0.05), (0, -1, 0))
        face_to(g, [a0, o1, o0], STONE, 0.44 + jit(rng, 0.05), (0, -1, 0))
    y0c, y1c, shrink = min(yo) - 0.02, 2.9, 0.58                                             # the core: a mound that
    front = [(x, y0c, z) for x, z in outer]                                                  # tapers back into the hill
    back = [(x * shrink, y1c, z * shrink) for x, z in outer]
    for i in range(1, len(outer)):
        j = (i + 1) % len(outer)
        mx, mz = (outer[i][0] + outer[j][0]) / 2, (outer[i][1] + outer[j][1]) / 2
        face_to(g, [front[i], front[j], back[j], back[i]], STONE, 0.42 + jit(rng, 0.04), (mx, 0.35, mz - 1.6))
    face_to(g, back, STONE, 0.4, (0, 1, 0))
    for (c, sz, n, v) in (((-3.45, 0.35), (0.95, 1.6, 2.7), 12, 0.46), ((3.5, 0.5), (0.9, 1.5, 2.45), 12, 0.5),
                          ((0.0, 2.0), (3.0, 0.95, 3.25), 12, 0.42), ((-3.85, 1.85), (0.6, 1.0, 1.25), 9, 0.44),
                          ((3.9, 1.95), (0.55, 0.95, 1.05), 9, 0.4), ((-2.4, 2.3), (1.0, 0.75, 1.9), 9, 0.46),
                          ((2.5, 2.4), (0.95, 0.7, 1.7), 9, 0.44)):
        K.rock(g, rng, (c[0], c[1], 0.55 * sz[2] - 0.02), sz, STONE, n=n, var=v)
    K.rock(g, rng, (0.2, -1.0, 4.75), (2.4, 0.72, 0.75), STONE, n=11, var=0.5, flat=False)     # the brow
    K.rock(g, rng, (-0.5, 0.6, 4.9), (1.8, 1.2, 0.9), STONE, n=10, var=0.46, flat=False)       # the crag on top
    K.rock(g, rng, (-2.85, 0.15, 3.55), (0.9, 0.8, 0.75), STONE, n=8, var=0.44, flat=False)    # its shoulders
    K.rock(g, rng, (2.8, 0.3, 3.25), (0.85, 0.75, 0.7), STONE, n=8, var=0.48, flat=False)
    for (c, sz) in (((-2.85, -1.75, 0.2), (0.42, 0.36, 0.3)), ((2.75, -1.7, 0.17), (0.36, 0.32, 0.26)),
                    ((3.7, -1.15, 0.12), (0.26, 0.24, 0.18)), ((-3.95, -0.95, 0.14), (0.3, 0.26, 0.2)),
                    ((1.7, -2.2, 0.06), (0.16, 0.14, 0.1)), ((-1.9, -2.25, 0.06), (0.15, 0.13, 0.09))):
        K.rock(g, rng, c, sz, STONE, n=7, var=0.42 + jit(rng, 0.05))
    p = kit.add('vale_cave_mouth', g, budget=320, sheet={'az': 24, 'el': 16})
    p.info['footprint'] = plan_size(g)
    p.info['opening'] = {'at': K.blender_to_game((0.0, yf, 0.0)), 'width': 4.2, 'height': 3.8, 'depth': yb - yf}


def keep_gate(kit):
    """Gravehollow Keep's gate, the dungeon's door: a grim gatehouse of dark stone 16 m across — two square towers
    (4.3 × 5.9 m, 13 m to their broken crenellations) on battered feet with arrow slits, and between them, recessed
    0.9 m, the gate block (8.8 m, a parapet with broken merlons) with a pointed arch of pale dressed stone over a great
    iron-bound double door, shut, at the centre of the front at ground level; a skull carved over the arch, a torn dark
    banner with a pale fang on each tower, two braziers glowing either side of the threshold and two skulls on iron
    spikes before it."""
    rng = R('vale_keep_gate')
    g = K.Geo()
    zt = 11.6
    for sx in (-1, 1):                                                                        # the towers
        cx, cy, hx, hy = sx * 5.45, -0.15, 2.15, 2.95
        x0, x1, y0, y1 = cx - hx, cx + hx, cy - hy, cy + hy
        b = 0.35
        lo = [(x0 - b, y0 - b, 0.0), (x1 + b, y0 - b, 0.0), (x1 + b, y1 + b, 0.0), (x0 - b, y1 + b, 0.0)]
        hi = [(x0, y0, 1.4), (x1, y0, 1.4), (x1, y1, 1.4), (x0, y1, 1.4)]
        for k in range(4):
            q = [lo[k], lo[(k + 1) % 4], hi[(k + 1) % 4], hi[k]]
            mid = sum((Vector(p) for p in q), Vector()) / 4
            face_to(g, q, IRON, 0.38, (mid.x - cx, mid.y - cy, 0.3))
        K.box(g, (x0, y0, 1.4), (x1, y1, zt - 0.45), IRON, 0.46 + jit(rng, 0.03), skip=('-z', '+z'))
        K.box(g, (x0 - 0.2, y0 - 0.2, zt - 0.45), (x1 + 0.2, y1 + 0.2, zt), IRON, 0.38, skip=('-z',))
        ring_wall(g, x0 - 0.2, y0 - 0.2, x1 + 0.2, y1 + 0.2, 0.4, zt, zt + 0.5, IRON, 0.46)
        o0, o1, p0, p1 = x0 - 0.2, x1 + 0.2, y0 - 0.2, y1 + 0.2
        merlons = [((o0, o0 + 0.75), (p0, p0 + 0.75)), ((o1 - 0.75, o1), (p0, p0 + 0.75)),
                   ((o1 - 0.75, o1), (p1 - 0.75, p1)), ((o0, o0 + 0.75), (p1 - 0.75, p1)),
                   ((cx - 0.4, cx + 0.4), (p0, p0 + 0.4)), ((cx - 0.4, cx + 0.4), (p1 - 0.4, p1)),
                   ((o0, o0 + 0.4), (cy - 0.4, cy + 0.4)), ((o1 - 0.4, o1), (cy - 0.4, cy + 0.4))]
        heights = (1.1, 0.35, 1.1, 0.0, 0.6, 1.1, 1.1, 0.0) if sx < 0 else (1.1, 1.1, 0.0, 1.1, 1.1, 0.5, 1.1, 1.1)
        for ((xa, xb), (ya, yb)), hgt in zip(merlons, heights):
            if hgt > 0:
                K.box(g, (xa, ya, zt + 0.5), (xb, yb, zt + 0.5 + hgt + jit(rng, 0.06)), IRON, 0.48 + jit(rng, 0.04),
                      skip=('-z',))
        for z in (4.2, 7.6):
            slit(g, on_face('-y', y0, cx, z), h=1.2)
        slit(g, on_face('+x' if sx > 0 else '-x', x1 if sx > 0 else x0, cy, 5.8), h=1.2)
        K.box(g, (cx - 0.8, y0 - 0.3, 9.2), (cx + 0.8, y0, 9.32), DWOOD, 0.4, skip=('+y',))   # the banner's pole
        yb_ = y0 - 0.15
        xs = [cx - 0.7 + 0.35 * i for i in range(5)]
        bots = [5.9 + jit(rng, 0.1), 5.25, 6.25, 5.55, 6.35 + jit(rng, 0.1)]
        for i in range(4):
            plate(g, [(xs[i], bots[i]), (xs[i + 1], bots[i + 1]), (xs[i + 1], 9.2), (xs[i], 9.2)], yb_, INK, 0.62)
        plate(g, [(cx, 7.3), (cx + 0.34, 8.4), (cx - 0.34, 8.4)], yb_ - 0.01, BONE, 0.6)           # the pale fang
        plate(g, [(cx - 0.42, 8.55), (cx + 0.42, 8.55), (cx + 0.42, 8.7), (cx - 0.42, 8.7)], yb_ - 0.01, BONE, 0.56)
    hw, sp, ap = 1.9, 3.6, 5.4                                                               # the gate block
    mk = ruin_wall(g, rng, -3.3, 3.3, 0.8, [(-3.3, 8.8), (3.3, 8.8)], [(0.0, hw, 0.0, sp, ap)], slot=IRON, var=0.46,
                   ends=(False, False), back=False)
    g.transform(T(0, -2.2, 0), mk)
    K.box(g, (-3.3, -1.4, 0), (3.3, 2.8, 8.8), IRON, 0.44, skip=('-y', '-x', '+x', '-z'))
    K.box(g, (-3.3, -2.38, 8.8), (3.3, -2.0, 9.3), IRON, 0.48, skip=('-z', '-x', '+x'))       # the parapets
    K.box(g, (-3.3, 2.42, 8.8), (3.3, 2.8, 9.3), IRON, 0.46, skip=('-z', '-x', '+x'))
    for xc, hgt in ((-2.55, 0.62), (-1.25, 0.0), (0.0, 0.62), (1.25, 0.3), (2.55, 0.62)):
        if hgt > 0:
            K.box(g, (xc - 0.36, -2.38, 9.3), (xc + 0.36, -2.0, 9.3 + hgt), IRON, 0.5 + jit(rng, 0.04), skip=('-z',))
    ya = -2.2                                                                                # the arch's dressed stone
    for sx in (-1, 1):
        for pts in ([(sx * (hw + 0.38), 0.0), (sx * hw, 0.0), (sx * hw, sp), (sx * (hw + 0.38), sp)],
                    [(sx * (hw + 0.38), sp), (sx * hw, sp), (0.0, ap), (0.0, ap + 0.55)]):
            K.slab_xz(g, ccw(pts), ya - 0.14, ya, STONE, 0.34, back=False)
    yd = -1.42                                                                               # the door, shut
    for sx in (-1, 1):
        plate(g, ccw([(0.0, 0.0), (sx * hw, 0.0), (sx * hw, sp), (0.0, ap)]), yd, DWOOD, 0.36)
        for xp in (0.65, 1.3):
            stroke(g, (sx * xp, 0.0), (sx * xp, sp + (ap - sp) * (1 - xp / hw) - 0.04), 0.035, yd - 0.006, DWOOD,
                   0.22)
        for z in (0.7, 1.9, 3.1):
            plate(g, ccw([(sx * 0.05, z), (sx * (hw - 0.04), z), (sx * (hw - 0.04), z + 0.16), (sx * 0.05, z + 0.16)]),
                  yd - 0.02, IRON, 0.44)
        K.disc(g, 0.12, 6, IRON, var=0.5, m=T(sx * 0.32, yd - 0.035, 1.45) @ Rx(90))           # ring pulls
    stroke(g, (0.0, 0.0), (0.0, ap - 0.05), 0.06, yd - 0.01, INK, 0.4)                       # the seam
    K.box(g, (-2.3, -2.78, 0), (2.3, -2.2, 0.18), STONE, 0.32, skip=('-z', '+y'))              # the threshold
    ys_ = ya - 0.015                                                                         # the skull over the arch
    plate(g, [(0.0, 6.0), (0.3, 6.2), (0.38, 6.62), (0.22, 6.95), (-0.22, 6.95), (-0.38, 6.62), (-0.3, 6.2)], ys_,
          BONE, 0.6)
    for sx in (-1, 1):
        plate(g, ccw([(sx * 0.07, 6.5), (sx * 0.24, 6.5), (sx * 0.24, 6.7), (sx * 0.07, 6.7)]), ys_ - 0.006, INK, 0.5)
    plate(g, [(0.0, 6.28), (0.06, 6.42), (-0.06, 6.42)], ys_ - 0.006, INK, 0.5)
    for sx in (-1, 1):                                                                       # the braziers
        bx, by = sx * 2.75, -2.75
        K.tube(g, (bx, by, 0.0), (bx, by, 1.0), 0.06, IRON, n=4, var=0.44, cap0=False, cap1=False)
        K.lathe(g, [(0.14, 0.98), (0.36, 1.3)], 6, IRON, 0.42, smooth=0, cap1=False, m=T(bx, by, 0))
        K.lathe(g, [(0.3, 1.24), (0.12, 1.6), (0.0, 1.95)], 5, GLOW, 0.5, smooth=0, cap0=False, m=T(bx, by, 0))
    for sx in (-1, 1):                                                                       # skulls on spikes
        kx, ky = sx * 1.95, -3.3
        K.tube(g, (kx, ky, 0.0), (kx, ky, 1.95), 0.035, IRON, n=3, var=0.4, cap0=False, cap1=False)
        K.rock(g, rng, (kx, ky, 2.02), (0.13, 0.15, 0.13), BONE, n=8, var=0.6, flat=False)
        for ex in (-0.05, 0.05):
            K.rock(g, rng, (kx + ex, ky - 0.13, 2.04), (0.035, 0.02, 0.035), INK, n=4, var=0.5, flat=False)
    p = kit.add('vale_keep_gate', g, budget=640, sheet={'az': 26, 'el': 16})
    for sx in (-1, 1):
        kit.light(p, (sx * 2.75, -2.75, 1.6), 'fire')
        kit.fx(p, (sx * 2.75, -2.75, 1.5), 'glow')
    p.info['footprint'] = plan_size(g)
    p.info['door'] = {'at': K.blender_to_game((0.0, yd, 0.0)), 'width': 2 * hw, 'height': ap}


def wyvern_nest(kit):
    """A wyvern's nest, ~6 m across: a ring of rocks (taller at the back), flattened straw inside with strands sticking
    up round its rim, three great ribs arching in over it from a long-dead beast, a big horned skull and a thigh bone,
    an unhatched egg and two broken half shells."""
    rng = R('vale_wyvern_nest')
    g = K.Geo()
    face_to(g, [(math.cos(2 * math.pi * k / 10) * (1.95 + jit(rng, 0.18)),
                 math.sin(2 * math.pi * k / 10) * (1.95 + jit(rng, 0.18)), 0.04) for k in range(10)], ROPE, 0.5,
            (0, 0, 1))
    K.lathe(g, [(2.3, 0.03), (1.95, 0.34), (1.5, 0.03)], 10, ROPE, lambda b, k: 0.56 if b == 0 else 0.62 + jit(rng, 0.05),
            smooth=0, cap0=False, cap1=False, phase=0.3)                                     # the straw rim
    for k in range(11):                                                                      # the ring of rocks
        a = 2 * math.pi * k / 11 + jit(rng, 0.1)
        back = 0.5 + 0.5 * math.sin(a)                                                       # 1 at the back (+y)
        sz = 0.34 + 0.42 * back + jit(rng, 0.04)
        K.rock(g, rng, (math.cos(a) * 2.3, math.sin(a) * 2.3, 0.55 * sz - 0.02), (0.6, 0.5, sz), STONE, n=7,
               var=0.44 + jit(rng, 0.06))
    for a in (60, 95, 130):                                                                  # three great ribs
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        pts = [d * 2.1, d * 1.75 + Vector((0, 0, 0.8)), d * 1.15 + Vector((0, 0, 1.1)), d * 0.65 + Vector((0, 0, 0.8))]
        for i in range(3):
            K.tube(g, tuple(pts[i]), tuple(pts[i + 1]), 0.075 - 0.012 * i, BONE, r1=0.063 - 0.012 * i, n=3,
                   var=0.58, cap0=False, cap1=(i == 2))
    sx_, sy_ = 1.0, -1.05                                                                    # the horned skull
    K.rock(g, rng, (sx_, sy_, 0.22), (0.3, 0.46, 0.22), BONE, n=10, var=0.62, flat=True)
    for ex in (-0.12, 0.12):
        K.rock(g, rng, (sx_ + ex, sy_ - 0.28, 0.3), (0.06, 0.04, 0.05), INK, n=4, var=0.5, flat=False)
        K.lathe(g, [(0.07, 0.0), (0.0, 0.5)], 4, BONE, 0.7, smooth=0, cap0=False,
                m=T(sx_ + ex * 1.6, sy_ + 0.2, 0.34) @ Rx(-62) @ Ry(ex * 220))
    K.tube(g, (-1.35, -0.6, 0.07), (-0.45, -1.3, 0.07), 0.055, BONE, n=4, var=0.56, cap0=False, cap1=False)
    for c in ((-1.35, -0.6, 0.08), (-0.45, -1.3, 0.08)):
        K.rock(g, rng, c, (0.1, 0.1, 0.08), BONE, n=5, var=0.6, flat=False)
    K.rock(g, rng, (-0.35, 0.45, 0.32), (0.24, 0.24, 0.32), BONE, n=10, var=0.76, flat=False)    # the egg
    for (x, y, rz) in ((0.4, 0.6, 30), (-0.9, -0.05, -50)):                                  # broken shells
        K.lathe(g, [(0.26, 0.0), (0.2, 0.22), (0.0, 0.34)], 6, BONE, lambda b, k: 0.4 if b < 0 else 0.74, smooth=40,
                cap0=True, cap1=False, m=T(x, y, 0.2) @ Rz(rz) @ Rx(-105))      # the open side up toward -Y
    p = kit.add('vale_wyvern_nest', g, budget=340, sheet={'az': 30, 'el': 34})
    p.info['footprint'] = plan_size(g)


def rock_steel(kit):
    """A mining rock like the iron one, streaked with blue-grey steel-stone: pale bright-metal veins and dark iron
    ones running slantwise across its face (the tin rock has lumps; this one has streaks)."""
    rng = R('vale_rock_steel')
    g = K.Geo()
    mk = K.rock(g, rng, (0, 0, 0.36), (0.9, 0.75, 0.62), STONE, n=13, var=0.42)
    c0 = Vector((0.0, 0.0, 0.36))
    planes = []
    for k in range(mk[1], len(g.F)):
        pts = [g.V[i] for i in g.F[k]]
        planes.append((newell(pts).normalized(), pts[0].copy()))

    def surf(d):
        d = d.normalized()
        t = min(n.dot(q - c0) / n.dot(d) for n, q in planes if n.dot(d) > 1e-6)
        return c0 + d * t
    # five streaks, each a strip of six segments lying 2.5 cm proud of the rock's face, slanting across it
    for i in range(5):
        a0 = math.radians(i * 72 + jit(rng, 15))
        slope = rng.uniform(-0.5, 0.5)
        lift = rng.uniform(-0.05, 0.25)
        pts = []
        for j in range(7):
            a = a0 + (j - 3) * 0.16
            d = Vector((math.cos(a), math.sin(a), lift + slope * (j - 3) * 0.12))
            pts.append(surf(d) + d.normalized() * 0.025)
        slot, v = (BMETAL, 0.34) if i % 2 == 0 else (IRON, 0.62)
        for j in range(6):
            p0, p1 = pts[j], pts[j + 1]
            o0, o1 = (p0 - c0).normalized(), (p1 - c0).normalized()
            tdir = (p1 - p0).normalized()
            w0 = tdir.cross(o0).normalized() * 0.055
            w1 = tdir.cross(o1).normalized() * 0.055
            face_to(g, [tuple(p0 - w0), tuple(p1 - w1), tuple(p1 + w1), tuple(p0 + w0)], slot, v, tuple(o0 + o1))
    p = kit.add('vale_rock_steel', g, budget=120, sheet={'az': 30, 'el': 22})
    p.info['node'] = True
    p.info['footprint'] = plan_size(g)


def ash(kit):
    """An ash: a tall straight grey trunk, three branches reaching up, and a light airy crown of small leaf clusters
    with sky between them, a lighter green than the oak's (slot 6 at a high G), to ~6.9 m."""
    rng = R('vale_ash')
    g = K.Geo()
    K.tube(g, (0, 0, 0), (0.05, -0.03, 4.9), 0.2, STONE, r1=0.1, n=6, var=0.4, cap0=False)
    # seven leaf clusters, each on its own branch from the trunk, sky between them
    clusters = [((0.05, -0.03, 5.75), (1.0, 0.95, 0.8), None), ((1.25, 0.45, 4.6), (0.85, 0.8, 0.62), 3.2),
                ((-1.2, 0.6, 4.85), (0.85, 0.8, 0.62), 3.6), ((0.3, -1.25, 4.45), (0.85, 0.75, 0.6), 3.0),
                ((-0.65, -0.95, 5.4), (0.75, 0.7, 0.55), 4.0), ((0.8, 0.95, 5.7), (0.7, 0.65, 0.52), 4.3),
                ((-0.35, 1.05, 6.25), (0.6, 0.55, 0.45), 4.5), ((-1.0, -0.2, 3.95), (0.7, 0.65, 0.5), 2.8),
                ((0.85, -0.45, 6.1), (0.6, 0.55, 0.45), 4.6)]
    for i, (c, sz, zb) in enumerate(clusters):
        c = (c[0] * 1.3, c[1] * 1.3, c[2])                                                   # a wider crown
        if zb is not None:
            K.tube(g, (0.03, -0.02, zb - 0.3), (c[0] * 0.8, c[1] * 0.8, c[2] - 0.15), 0.07, STONE, r1=0.03, n=3,
                   var=0.44, cap0=False, cap1=False)
        K.rock(g, rng, c, tuple(v * 1.35 for v in sz), CLOTH1, n=9, var=0.74 + 0.06 * (i % 3), flat=False, smooth=0)
    p = kit.add('vale_ash', g, budget=200, sheet={'az': 30, 'el': 14})
    lo, hi = g.bounds()
    p.info['canopy'] = round(hi.z, 2)
    p.info['footprint'] = plan_size(g)


def willow(kit):
    """A weeping willow by the brook: a stout trunk, four limbs, a low dome of leaves and from its rim a pleated
    curtain of hanging fronds down to 0.7–1.3 m (long and short strands), shaded inside."""
    rng = R('vale_willow')
    g = K.Geo()
    K.tube(g, (0, 0, 0), (0.1, 0.05, 2.1), 0.36, DWOOD, r1=0.27, n=7, var=0.4, cap0=False)
    for a in (35, 125, 215, 305):
        d = Vector((math.cos(math.radians(a)) * 1.45, math.sin(math.radians(a)) * 1.45, 1.25))
        K.tube(g, (0.1, 0.05, 1.9), tuple(Vector((0.1, 0.05, 1.9)) + d), 0.15, DWOOD, r1=0.07, n=5, var=0.38,
               cap0=False)
    K.lathe(g, [(2.0, 3.25), (1.85, 3.95), (1.05, 4.5), (0.0, 4.68)], 10, CLOTH1,
            lambda b, k: 0.34 if b < 0 else 0.6 + jit(rng, 0.06), smooth=0, cap0=True, cap1=False, phase=0.2)
    # fourteen fronds hang from the crown's rim, touching at the top, bulging out, then hanging and tapering to long
    # and short tips (0.7 / 1.2 m) with gaps between them; both faces (the inner one shaded)
    N = 14
    for k in range(N):
        a = 2 * math.pi * k / N + 0.15 + jit(rng, 0.05)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        sd = Vector((-d.y, d.x, 0.0))
        tip = (0.7 if k % 2 == 0 else 1.2) + jit(rng, 0.12)
        rows = [(1.95, 3.3, 0.47), (2.45, 2.35, 0.36), (2.55, tip, 0.13)]
        v = (0.56 if k % 2 == 0 else 0.68) + jit(rng, 0.03)
        for i in range(2):
            (r0, z0, w0), (r1, z1, w1) = rows[i], rows[i + 1]
            q = [d * r0 - sd * w0 + Vector((0, 0, z0)), d * r0 + sd * w0 + Vector((0, 0, z0)),
                 d * r1 + sd * w1 + Vector((0, 0, z1)), d * r1 - sd * w1 + Vector((0, 0, z1))]
            canvas(g, [tuple(p) for p in q], CLOTH1, v, (d.x, d.y, 0.25), inner=0.32, gap=0.01)
    p = kit.add('vale_willow', g, budget=260, sheet={'az': 30, 'el': 14})
    lo, hi = g.bounds()
    p.info['canopy'] = round(hi.z, 2)
    p.info['footprint'] = plan_size(g)


def dead_tree(kit):
    """A dead tree of the marsh, ~5 m: a bare, bleached grey trunk with a slight twist and a dark knot-hole, five
    crooked branches (two snapped short), three roots flaring into the ground."""
    rng = R('vale_dead_tree')
    g = K.Geo()
    pts = [(0.0, 0.0, 0.0), (0.15, 0.05, 1.4), (-0.1, 0.12, 2.7), (0.2, -0.05, 3.8), (0.05, 0.1, 4.6)]
    rs = [0.3, 0.22, 0.16, 0.1, 0.045]
    for i in range(4):
        K.tube(g, pts[i], pts[i + 1], rs[i], STONE, r1=rs[i + 1], n=5, var=0.58 + jit(rng, 0.04), cap0=False,
               cap1=(i == 3), smooth=40)
    for (bi, f, a, ln, up, r) in ((1, 0.55, 20, 1.4, 0.9, 0.09), (2, 0.3, 145, 1.5, 0.7, 0.08),
                                  (2, 0.8, 250, 1.1, 1.0, 0.07), (3, 0.5, 60, 0.6, 0.35, 0.06),
                                  (1, 0.2, 300, 0.55, 0.15, 0.07)):
        p0 = Vector(lerp3(pts[bi], pts[bi + 1], f))
        d0 = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        d1 = Vector((math.cos(math.radians(a + 40)), math.sin(math.radians(a + 40)), 0))
        p1 = p0 + d0 * ln * 0.55 + Vector((0, 0, up * 0.5))
        p2 = p1 + d1 * ln * 0.5 + Vector((0, 0, up * 0.6))
        K.tube(g, tuple(p0), tuple(p1), r, STONE, r1=r * 0.6, n=4, var=0.56 + jit(rng, 0.05), cap0=False,
               cap1=False)
        K.tube(g, tuple(p1), tuple(p2), r * 0.6, STONE, r1=0.012, n=3, var=0.6, cap0=False, cap1=False)
    for a in (40, 170, 290):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        K.tube(g, (0, 0, 0.4), tuple(d * 0.75 + Vector((0, 0, -0.03))), 0.13, STONE, r1=0.04, n=3, var=0.52,
               cap0=False, cap1=False)
    K.disc(g, 0.07, 5, INK, var=0.5, m=T(0.05, -0.215, 1.7) @ Rx(90) @ Matrix.Diagonal((1.0, 1.6, 1.0, 1.0)))
    p = kit.add('vale_dead_tree', g, budget=150, sheet={'az': 30, 'el': 14})
    lo, hi = g.bounds()
    p.info['canopy'] = round(hi.z, 2)
    p.info['footprint'] = plan_size(g)


def bones(kit):
    """A scatter of old bones, ~1.5 m across: a skull with dark sockets and its jaw beside it, a long bone and a
    shorter one with knobbed ends, three ribs curving up out of the ground."""
    rng = R('vale_bones')
    g = K.Geo()
    K.rock(g, rng, (0.3, -0.22, 0.1), (0.12, 0.15, 0.11), BONE, n=8, var=0.62)                  # the skull
    for ex in (-0.045, 0.045):
        K.rock(g, rng, (0.3 + ex, -0.35, 0.12), (0.03, 0.02, 0.03), INK, n=4, var=0.5, flat=False)
    for (a, b) in (((0.02, -0.52, 0.025), (0.17, -0.46, 0.025)), ((0.02, -0.52, 0.025), (0.06, -0.37, 0.025))):
        K.tube(g, a, b, 0.02, BONE, n=3, var=0.58, cap0=False, cap1=False)                   # its jaw
    sp0, sp1 = Vector((-0.6, 0.25, 0.04)), Vector((0.15, 0.4, 0.04))
    K.tube(g, tuple(sp0), tuple(sp1), 0.032, BONE, n=3, var=0.54, cap0=False, cap1=False)    # the spine
    for k in range(3):                                                                       # ribs arching off it
        b = sp0.lerp(sp1, 0.2 + 0.28 * k)
        pts = [b, b + Vector((0.02, -0.12, 0.17)), b + Vector((0.04, -0.33, 0.1))]
        for i in range(2):
            K.tube(g, tuple(pts[i]), tuple(pts[i + 1]), 0.022, BONE, n=3, var=0.58 + jit(rng, 0.04), cap0=False,
                   cap1=False)
    a, b = (-0.62, -0.3, 0.035), (-0.08, -0.62, 0.035)                                       # a long bone
    K.tube(g, a, b, 0.032, BONE, n=3, var=0.56, cap0=False, cap1=False)
    for c in (a, b):
        K.rock(g, rng, c, (0.055, 0.055, 0.045), BONE, n=6, var=0.6, flat=False)
    p = kit.add('vale_bones', g, budget=100, sheet={'az': 30, 'el': 34})
    p.info['footprint'] = plan_size(g)


# ====================================================================== the town review (2026-11-04)
# docs/feedback/2026-11-04-town-review.md, "Kit fixes where they matter": the thatch slot shifted to straw (VALE),
# the bank rebuilt (bank), the houses mirrored and re-roofed (house_small / house_tall), the curtain wall dressed
# (wall_stone), the signpost made readable (signpost); and here the new pieces — a narrow shop-house for the street
# fronts, hanging signs for the four workshops, a kerb and a cobble patch, the quarry's rock faces, the arena's crowd
# and banners, and the doorstep clutter (bench, basket, sacks, firewood, trough, dog, handcart).
def shophouse(kit, mesh_id='vale_shophouse', mirror=False):
    """A narrow two-storey shop-house for the street fronts, 5 × 8 m with its jetty, gable to the street: a stone sill,
    a timbered ground floor with the shop's opening at the left of the front — its lower shutter let down as a
    counter with wares on it, its upper shutter propped out as a hood — and the house door at the right, the household's
    floor jettied 0.5 m out over the street on three braces with two cross windows and a little gable window, a thatch
    roof, a chimney on the right slope. The front wall stands at y −3.05 (the jetty's face at −3.55, the counter 0.8 m
    further out), the back wall at +3.95. `mirror` builds its twin with the door at the left."""
    rng = R(mesh_id)
    g = K.Geo()
    w, d, gh, uh, zr = 5.0, 7.0, 2.9, 5.5, 7.9
    hx, hy = w / 2, d / 2
    K.box(g, (-hx - 0.08, -hy - 0.08, 0), (hx + 0.08, hy + 0.08, 0.3), DSTONE, 0.45, skip=('-z',))     # the sill
    K.box(g, (-hx, -hy, 0.28), (hx, hy, gh), BONE, 0.5 + jit(rng, 0.04), skip=('-z', '+z'))           # the ground floor
    for x in (-hx, hx):
        for y in (-hy, hy):
            K.box(g, (x - 0.12, y - 0.12, 0.28), (x + 0.12, y + 0.12, gh + 0.02), WOOD, 0.42, skip=('-z', '+z'))
    for side, at in (('-x', -hx), ('+x', hx)):
        flat_strip(g, on_face(side, at, 0.0, 0.0), (0.0, 0.3), (0.0, gh - 0.05), 0.18, WOOD, 0.44, y=-0.012)
    # the shop opening: 1.9 m wide at the left of the front, its sill 0.95 m up; the dark shop inside; the lower
    # shutter let down as a counter on two chains, the upper propped out as a hood on two poles; wares on the counter
    ox0, ox1, zs, zh = -2.15, -0.25, 0.95, 2.25
    yf = -hy
    K.box(g, (ox0 - 0.1, yf - 0.1, zs - 0.1), (ox1 + 0.1, yf + 0.02, zh + 0.1), WOOD, 0.42, skip=('+y',))
    plate(g, [(ox0, zs), (ox1, zs), (ox1, zh), (ox0, zh)], yf - 0.11, INK, 0.5)
    K.box(g, (ox0, yf - 0.8, zs - 0.06), (ox1, yf - 0.1, zs), WOOD, 0.52, skip=('+y',))                 # the counter
    for x in (ox0 + 0.08, ox1 - 0.08):
        K.tube(g, (x, yf - 0.76, zs), (x, yf - 0.1, zh - 0.3), 0.015, IRON, n=3, var=0.44, cap0=False, cap1=False)
    hood = [(ox0, yf - 0.1, zh + 0.1), (ox1, yf - 0.1, zh + 0.1), (ox1, yf - 0.95, zh + 0.3), (ox0, yf - 0.95, zh + 0.3)]
    K.hull(g, hood + [(x, y, z - 0.05) for x, y, z in hood], WOOD, 0.46)
    for x in (ox0 + 0.08, ox1 - 0.08):
        K.tube(g, (x, yf - 0.9, zh + 0.25), (x, yf, zh - 0.6), 0.025, DWOOD, n=4, var=0.4, cap0=False, cap1=False)
    K.box(g, (ox0 + 0.1, yf - 0.62, zs), (ox0 + 0.6, yf - 0.22, zs + 0.16), CLOTH1, 0.5, skip=('-z',))     # bolts of cloth
    K.box(g, (ox0 + 0.1, yf - 0.62, zs + 0.16), (ox0 + 0.55, yf - 0.26, zs + 0.3), CLOTH2, 0.54, skip=('-z',))
    K.rock(g, rng, (ox1 - 0.45, yf - 0.42, zs + 0.11), (0.22, 0.17, 0.11), BRASS, n=7, var=0.56)         # a loaf
    K.rock(g, rng, (-1.1, yf - 0.4, zs + 0.09), (0.16, 0.14, 0.09), ROPE, n=6, var=0.6)                   # a basket
    # the house door at the right, a doorstep
    dx = 1.55
    K.box(g, (dx - 0.7, yf - 0.3, 0), (dx + 0.7, yf, 0.1), STONE, 0.4, skip=('-z', '+y'))
    town_door(g, T(dx, yf, 0.1), w=0.95, h=2.1)
    # the jetty: a beam across the front, three braces, the framed upper floor 0.5 m out over the street
    jy = yf - 0.5
    K.box(g, (-hx - 0.06, jy - 0.1, gh - 0.15), (hx + 0.06, yf + 0.2, gh + 0.12), DWOOD, 0.4)
    for x in (-1.9, 0.0, 1.9):
        K.tube(g, (x, yf, gh - 0.8), (x, jy + 0.08, gh - 0.17), 0.06, WOOD, n=4, var=0.42, cap0=False, cap1=False)
    ux, uy = hx + 0.06, (d + 0.5) / 2
    mk = g.mark()
    framed_upper(g, rng, ux, uy, gh + 0.12, uh, studs_y=(-1.5, 1.5), studs_x=(-1.2, 1.2))
    g.transform(T(0, -0.25, 0), mk)
    for x in (-1.3, 1.3):
        town_window(g, T(x, jy, gh + 1.0), w=0.9, h=1.0, shutters=True)                          # W18-town: shutters
    g.pf([(-ux, jy, uh), (ux, jy, uh), (0.0, jy, zr - 0.06)], BONE, 0.5)                                  # the gables
    g.pf([(ux, hy, uh), (-ux, hy, uh), (0.0, hy, zr - 0.06)], BONE, 0.5)
    for a, b in (((-ux + 0.2, uh), (-0.15, zr - 0.45)), ((ux - 0.2, uh), (0.15, zr - 0.45))):
        flat_strip(g, T(0, jy, 0), a, b, 0.14, WOOD, 0.44, y=-0.012)
    town_window(g, T(0, jy, uh + 0.3), w=0.6, h=0.6)
    gable_roof_y(g, -ux, ux, jy, hy, eave_z(uh + 0.02, zr, ux, 0.35), zr, ROPE, var=0.5, overhang=0.35)
    K.box(g, (1.5, 1.2, 5.0), (2.1, 1.8, 8.4), STONE, 0.45, skip=('-z',))                                 # the chimney
    K.box(g, (1.42, 1.12, 8.4), (2.18, 1.88, 8.55), STONE, 0.36, skip=('-z',))
    g.transform(T(0, 0.45, 0))                                   # the footprint centred on the walls plus the jetty
    if mirror:
        g.transform(Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0)))
    p = kit.add(mesh_id, g, budget=400, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [w, 8.0]
    p.info['door'] = [-dx if mirror else dx, 0.1, hy - 0.45]           # the threshold's centre, game (x, y, z)
    p.info['chimney'] = [-1.8 if mirror else 1.8, 8.55, -1.95]         # the flue's top, game (x, y, z)
    return p


def sym_bow(g, cx, y, cz):
    """A strung bow with an arrow across it (the fletcher)."""
    arc = [(cx + 0.1 + 0.3 * math.cos(math.radians(a)), cz + 0.3 * math.sin(math.radians(a))) for a in range(100, 261, 32)]
    for a, b in zip(arc, arc[1:]):
        stroke(g, a, b, 0.07, y, BRASS, 0.66)
    stroke(g, arc[0], arc[-1], 0.03, y - 0.002, BONE, 0.7)
    stroke(g, (cx - 0.34, cz), (cx + 0.3, cz), 0.04, y - 0.004, BMETAL, 0.62)
    plate(g, [(cx + 0.28, cz - 0.08), (cx + 0.42, cz), (cx + 0.28, cz + 0.08)], y - 0.006, BMETAL, 0.62)
    for dz in (-1, 1):
        stroke(g, (cx - 0.34, cz), (cx - 0.22, cz + dz * 0.09), 0.04, y - 0.006, CLOTH2, 0.5)


def sym_flask(g, cx, y, cz):
    """A round flask of green brew with a bubble (the alchemist)."""
    K.disc(g, 0.19, 8, BMETAL, var=0.74, m=T(cx, y, cz - 0.1) @ Rx(90))
    stroke(g, (cx, cz + 0.02), (cx, cz + 0.3), 0.11, y, BMETAL, 0.74)
    stroke(g, (cx - 0.1, cz + 0.3), (cx + 0.1, cz + 0.3), 0.05, y - 0.002, BMETAL, 0.6)
    K.disc(g, 0.13, 8, CLOTH1, var=0.62, m=T(cx, y - 0.004, cz - 0.12) @ Rx(90))
    K.disc(g, 0.035, 5, BONE, var=0.7, m=T(cx + 0.05, y - 0.008, cz - 0.05) @ Rx(90))


def sym_needle(g, cx, y, cz):
    """A needle with its thread and a bone button (the craft workshop)."""
    stroke(g, (cx - 0.3, cz - 0.3), (cx + 0.3, cz + 0.3), 0.07, y, BMETAL, 0.7)
    plate(g, [(cx + 0.2, cz + 0.18), (cx + 0.26, cz + 0.24), (cx + 0.22, cz + 0.28), (cx + 0.16, cz + 0.22)], y - 0.004,
          INK, 0.5)
    path = [(cx + 0.22, cz + 0.24), (cx + 0.36, cz + 0.12), (cx + 0.3, cz - 0.08), (cx + 0.1, cz - 0.3),
            (cx - 0.12, cz - 0.36)]
    for a, b in zip(path, path[1:]):
        stroke(g, a, b, 0.045, y - 0.002, CLOTH2, 0.46)
    K.disc(g, 0.13, 8, BONE, var=0.72, m=T(cx - 0.24, y - 0.004, cz + 0.18) @ Rx(90))
    for dx, dz in ((-0.04, -0.04), (0.04, -0.04), (-0.04, 0.04), (0.04, 0.04)):
        K.disc(g, 0.025, 4, INK, var=0.5, m=T(cx - 0.24 + dx, y - 0.008, cz + 0.18 + dz) @ Rx(90))


def sym_loaf(g, cx, y, cz):
    """A round loaf with three slashes on a pale plate (the bakehouse)."""
    K.disc(g, 0.36, 10, BONE, var=0.7, m=T(cx, y, cz) @ Rx(90), scale=(1.0, 0.78))
    K.disc(g, 0.3, 10, ROPE, var=0.72, m=T(cx, y - 0.004, cz + 0.01) @ Rx(90), scale=(1.0, 0.72))
    for k in (-1, 0, 1):
        stroke(g, (cx + k * 0.13 - 0.07, cz + 0.1), (cx + k * 0.13 + 0.07, cz - 0.08), 0.035, y - 0.008, INK, 0.4)


def hanging_sign(kit, mesh_id, symbol, budget=130):
    """A workshop's sign (town review 2026-11-04: the fletcher's and alchemist's shells, the craft workshop's and the
    bakehouse's, each get their own): a timber post on a stone foot, an iron arm with a stay out to its left (−x), a
    plank board hung from the arm on two rings, `symbol(g, cx, y, cz)` drawn bold on both faces (readable from 15 m);
    the board faces −Y and +Y. Stands by a workshop's front corner with the board along the street."""
    g = K.Geo()
    K.box(g, (-0.2, -0.2, 0), (0.2, 0.2, 0.3), STONE, 0.44, skip=('-z',))
    K.box(g, (-0.09, -0.09, 0.3), (0.09, 0.09, 3.1), WOOD, 0.42, skip=('-z',))
    pyramid(g, 0, 0, 0.13, 0.13, 3.1, 3.3, WOOD, var=0.38, under=False)
    K.box(g, (-1.2, -0.04, 2.72), (-0.09, 0.04, 2.8), IRON, 0.46, skip=('+x',))
    K.tube(g, (-0.09, 0, 2.2), (-0.9, 0, 2.72), 0.025, IRON, n=4, var=0.46, cap0=False, cap1=False)
    for x in (-1.05, -0.35):
        K.tube(g, (x, 0, 2.72), (x, 0, 2.58), 0.02, IRON, n=3, var=0.44, cap0=False, cap1=False)
    K.box(g, (-1.18, -0.04, 1.7), (-0.22, 0.04, 2.58), DWOOD, 0.44)
    symbol(g, -0.7, -0.045, 2.14)
    mk = g.mark()
    symbol(g, -0.7, -0.045, 2.14)
    g.transform(Matrix.Diagonal((1.0, -1.0, 1.0, 1.0)), mk)
    p = kit.add(mesh_id, g, budget=budget, sheet={'az': 20, 'el': 12})
    p.info['footprint'] = plan_size(g)
    p.info['board'] = [-0.7, 2.14, 0.0]      # the board's centre, game (x, y, z); it faces ±z (south and north)
    return p


def kerb(kit):
    """A 2 m kerb stone, 0.3 wide and 0.15 high, tiling along x: where the market's paving meets the street. No
    collider (the hero steps over it)."""
    g = K.Geo()
    K.bevel_box(g, (-1.0, -0.15, 0), (1.0, 0.15, 0.15), 0.03, STONE,
                var=lambda s: {'side': 0.48, 'bevel': 0.6, 'top': 0.68}[s])
    p = kit.add('vale_kerb', g, budget=20, sheet={'az': 30, 'el': 26},
                bake={'ground': 0.0, 'occluders': [('vale_kerb', (-2.0, 0, 0)), ('vale_kerb', (2.0, 0, 0))]})
    p.info['span'] = 2.0
    p.info['footprint'] = [2.0, 0.3]
    p.info['no_collider'] = True


def cobbles(kit):
    """A 3 × 3 m cobbled patch raised 0.1 m — a doorstep, the well's surround: an irregular slab in dark joint stone with
    a 6 × 6 field of slightly jittered cobbles on top, each a shade apart. No collider."""
    rng = R('vale_cobbles')
    g = K.Geo()
    n = 12
    ring = []
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        r = 1.5 / max(abs(math.cos(a)), abs(math.sin(a))) * rng.uniform(0.95, 1.0)
        ring.append((r * math.cos(a), r * math.sin(a)))
    K.prism(g, ring, 0.0, 0.1, STONE, lambda k: 0.3 if k == 'top' else 0.38, cap0=False)
    pitch, half = 0.46, 1.38
    for i in range(6):
        for j in range(6):
            x0, y0 = -half + i * pitch, -half + j * pitch
            q = [(x0 + 0.03, y0 + 0.03), (x0 + pitch - 0.03, y0 + 0.03), (x0 + pitch - 0.03, y0 + pitch - 0.03),
                 (x0 + 0.03, y0 + pitch - 0.03)]
            g.pf([(x + jit(rng, 0.035), y + jit(rng, 0.035), 0.105) for x, y in q], STONE, 0.44 + jit(rng, 0.18))
    p = kit.add('vale_cobbles', g, budget=110, sheet={'az': 30, 'el': 40})
    p.info['footprint'] = [3.0, 3.0]
    p.info['no_collider'] = True


QUARRY_PROFILE = [(-1.5, 0.0), (-1.25, 1.35), (-0.65, 1.5), (-0.45, 2.85), (0.2, 3.0), (0.35, 4.0), (1.5, 4.0)]
# the cut face's section (y, z) from its foot at the front (−Y) up two ledges 0.6 m deep to the top at 4 m, then
# back 1.15 m to the rear edge (the hillside takes it from there); segment 5 (the top) is turf


def quarry_section(g, pts, toward, var=0.5):
    """A cut face's end (the section closed to the ground) facing `toward`."""
    face_to(g, pts + [(pts[-1][0], pts[-1][1], 0.0)], STONE, var, toward)


def quarry_face(kit):
    """A cut rock face for the quarry's pit, 6 × 3 m and 4 m tall, tiling along x: QUARRY_PROFILE swept along x with
    its inner vertices jittered (the ends exact, so neighbours meet), the ledges' treads paler, the top turf, closed
    ends and back, two rubble stones at the foot. Place it with its face (−Y) toward the pit and its back in the rim."""
    rng = R('vale_quarry_face')
    g = K.Geo()
    L, nu, prof = 3.0, 6, QUARRY_PROFILE
    last = len(prof) - 1

    def fn(i, j):
        x = -L + 2 * L * i / nu
        y, z = prof[j]
        if 0 < i < nu and 0 < j < last:
            y += jit(rng, 0.15)
            z += jit(rng, 0.11)
        elif 0 < i < nu and j == 0:
            y += jit(rng, 0.12)
        return (x, y, z)
    K.surface(g, nu, last, fn, lambda i, j: MOSS if j == last - 1 else STONE,
              lambda i, j: (0.66 if j in (1, 3) else 0.42) + jit(rng, 0.06), smooth=0)
    quarry_section(g, [(L, y, z) for y, z in prof], (1, 0, 0), 0.46)
    quarry_section(g, [(-L, y, z) for y, z in prof], (-1, 0, 0), 0.46)
    face_to(g, [(-L, 1.5, 0.0), (L, 1.5, 0.0), (L, 1.5, 4.0), (-L, 1.5, 4.0)], STONE, 0.4, (0, 1, 0))
    K.rock(g, rng, (-1.7, -1.5, 0.26), (0.52, 0.42, 0.4), STONE, n=9, var=0.5)
    K.rock(g, rng, (1.2, -1.55, 0.22), (0.44, 0.36, 0.34), STONE, n=8, var=0.56)
    p = kit.add('vale_quarry_face', g, budget=160, sheet={'az': 30, 'el': 20},
                bake={'ground': 0.0, 'occluders': [('vale_quarry_face', (-2 * L, 0, 0)), ('vale_quarry_face', (2 * L, 0, 0))]})
    p.info['span'] = 2 * L
    p.info['footprint'] = [2 * L, 3.0]
    p.info['ledges'] = [[1.5, 0.6], [3.0, 0.65]]       # (height, depth) of the two ledges


def quarry_face_corner(kit):
    """The pit's inside corner, 3 × 3 m: the cut face's section swept a quarter turn about the corner's foot at local
    (−1.5, −1.5), so a straight face continues from its −x side (the same yaw) and another from its −y side (turned
    a quarter to face −x); the pit lies toward (−x, −y). Closed at the back, open at the two joins (the straight faces'
    ends close them)."""
    rng = R('vale_quarry_face_corner')
    g = K.Geo()
    C = Vector((-1.5, -1.5, 0.0))
    nu, prof = 4, QUARRY_PROFILE
    last = len(prof) - 1
    rings = []
    for j in range(0, last + 1):
        ring = []
        for i in range(nu + 1):
            a = math.radians(90.0 * (1 - i / nu))
            r, z = prof[j][0] + 1.5, prof[j][1]
            # the lower rings bulge out mid-arc (a shoulder of uncut rock in the corner, so the first ledge does not
            # pinch to the axis); the joins (i 0 and nu) and the top stay exact
            r += (0.65, 0.5, 0.42, 0.2, 0.1, 0.0, 0.0)[j] * math.sin(math.pi * i / nu)
            if 0 < i < nu and 0 < j < last:
                r += jit(rng, 0.15)
                z += jit(rng, 0.11)
            ring.append(g.v((C.x + r * math.cos(a), C.y + r * math.sin(a), z)))
        rings.append(ring)
    for j in range(last):
        slot = MOSS if j == last - 1 else STONE
        for i in range(nu):
            v = (0.66 if j in (1, 3) else 0.42) + jit(rng, 0.06)
            g.f((rings[j][i], rings[j][i + 1], rings[j + 1][i + 1], rings[j + 1][i]), slot, v)
    back = rings[last]
    foot = [g.v((g.V[k].x, g.V[k].y, 0.0)) for k in back]
    for i in range(nu):
        g.f((back[i], foot[i], foot[i + 1], back[i + 1]), STONE, 0.4)
    K.rock(g, rng, (-0.7, -1.25, 0.22), (0.42, 0.36, 0.34), STONE, n=8, var=0.52)
    p = kit.add('vale_quarry_face_corner', g, budget=100, sheet={'az': 50, 'el': 24})
    p.info['footprint'] = [3.0, 3.0]


def arena_crowd(kit):
    """A stand's crowd (town review 2026-11-04: the stands were empty tiers): twelve seated figures on the two upper
    benches of `vale_arena_stand` — a coloured block each with a round head, in the town's cloth colours — and a
    string of bunting slung between the back wall's two pennant poles. Built in the stand's frame: place it at a
    stand's own position and yaw."""
    rng = R('vale_arena_crowd')
    g = K.Geo()
    tn = math.tan(math.radians(9.0))

    def hw(y):
        return (19.5 + y) * tn
    ys = [-2.5, -1.4, -0.3, 0.8, 1.9, 2.5]
    zs = [1.2, 1.9, 2.6, 3.3, 4.5]
    cloths = ((CLOTH1, 0.5), (WATER, 0.45), (BONE, 0.4), (CLOTH2, 0.56), (ROPE, 0.42), (DSTONE, 0.56), (CLOTH1, 0.3),
              (BONE, 0.6), (WATER, 0.6), (DWOOD, 0.6), (CLOTH2, 0.36), (ROPE, 0.6))
    k = 0
    for i in (2, 3):
        ya, zb, yc = ys[i], zs[i] + 0.4, ys[i] + 0.32
        span = hw(ya) - 0.4
        for n in range(6):
            x = -span + (n + 0.5) * 2 * span / 6 + jit(rng, 0.08)
            slot, v = cloths[k % len(cloths)]
            k += 1
            h = 0.58 + jit(rng, 0.06)
            K.box(g, (x - 0.21, yc - 0.19, zb), (x + 0.21, yc + 0.19, zb + h), slot, v + jit(rng, 0.06), skip=('-z',))
            K.lathe(g, [(0.0, zb + h - 0.02), (0.13, zb + h + 0.13), (0.0, zb + h + 0.28)], 4, BRASS,
                    0.46 + jit(rng, 0.16), smooth=0, m=T(x, yc, 0) @ Rz(math.radians(jit(rng, 30))))
    xa, xb, z0 = -hw(2.2) + 0.4, hw(2.2) - 0.4, 5.85                                       # the bunting
    pts = [(xa, 2.2, z0), (xa + (xb - xa) / 3, 2.2, z0 - 0.3), (xa + 2 * (xb - xa) / 3, 2.2, z0 - 0.3), (xb, 2.2, z0)]
    for a, b in zip(pts, pts[1:]):
        K.tube(g, a, b, 0.012, ROPE, n=3, var=0.6, cap0=False, cap1=False)
    flags = (CLOTH1, BONE, CLOTH2, WATER, CLOTH1, BONE, CLOTH2)
    for n, slot in enumerate(flags):
        t = (n + 0.5) / len(flags)
        seg = min(2, int(t * 3))
        f = t * 3 - seg
        a, b = Vector(pts[seg]), Vector(pts[seg + 1])
        top = a.lerp(b, f)
        d = (b - a).normalized() * 0.16
        canvas(g, [tuple(top - d), tuple(top + d), (top.x, top.y, top.z - 0.34)], slot, 0.56, (0, -1, 0), inner=0.4)
    p = kit.add('vale_arena_crowd', g, budget=300, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = [round(2 * hw(2.5), 2), 5.0]
    p.info['on'] = 'vale_arena_stand'


def arena_banner(kit):
    """A banner for the arena's outer face (town review 2026-11-04: "a bare drum"): an iron wall plate and arm at
    4.1 m carrying a cross-rod, a long green cloth hung from it swaying 0.1 m out at its swallow-tailed foot, a brass
    boss on both sides. Its origin on the ground under the cloth with the wall plate's back at y 0 and the cloth 0.4 m
    out toward −Y: place one on each stand's back wall (the stand's local y +2.5, its yaw + 180) for the ring."""
    g = K.Geo()
    K.box(g, (-0.08, -0.03, 3.9), (0.08, 0.0, 4.3), IRON, 0.44, skip=('+y',))
    K.tube(g, (0, -0.03, 4.1), (0, -0.42, 4.1), 0.025, IRON, n=4, var=0.46, cap0=False, cap1=False)
    K.tube(g, (-0.52, -0.4, 4.1), (0.52, -0.4, 4.1), 0.025, IRON, n=4, var=0.46)
    cloth = [(-0.42, -0.4, 4.08), (0.42, -0.4, 4.08), (0.42, -0.5, 2.3), (0.0, -0.49, 2.7), (-0.42, -0.5, 2.3)]
    canvas(g, cloth, CLOTH1, 0.52, (0, -1, 0), inner=0.36)
    for y, rot in ((-0.455, 90), (-0.42, -90)):
        K.disc(g, 0.15, 8, BRASS, var=0.64, m=T(0, y, 3.35) @ Rx(rot))
    p = kit.add('vale_arena_banner', g, budget=60, sheet={'az': 20, 'el': 10})
    p.info['footprint'] = [1.1, 0.6]
    p.info['mount'] = 'wall'


def bench(kit):
    """A plank bench on two trestles, 1.5 m, for a doorstep (its back to +Y)."""
    g = K.Geo()
    K.box(g, (-0.75, -0.17, 0.42), (0.75, 0.17, 0.5), WOOD, 0.5, skip=('-z',))
    for x in (-0.6, 0.6):
        K.box(g, (x - 0.05, -0.13, 0), (x + 0.05, 0.13, 0.42), DWOOD, 0.4, skip=('-z', '+z'))
    p = kit.add('vale_bench', g, budget=30, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = [1.5, 0.34]


def basket(kit):
    """A wicker basket of green apples with a bail handle."""
    rng = R('vale_basket')
    g = K.Geo()
    K.lathe(g, [(0.2, 0.0), (0.27, 0.17), (0.3, 0.34)], 6, ROPE, lambda b, k: 0.46 + jit(rng, 0.06), smooth=0,
            cap1=False)
    K.rock(g, rng, (0, 0, 0.36), (0.24, 0.24, 0.1), CLOTH1, n=8, var=0.6)
    for a, b in (((-0.27, 0, 0.3), (-0.2, 0, 0.6)), ((-0.2, 0, 0.6), (0.2, 0, 0.6)), ((0.2, 0, 0.6), (0.27, 0, 0.3))):
        K.tube(g, a, b, 0.02, DWOOD, n=3, var=0.42, cap0=False, cap1=False)
    p = kit.add('vale_basket', g, budget=70, sheet={'az': 30, 'el': 24})
    p.info['footprint'] = [0.6, 0.6]


def sacks(kit):
    """Three grain sacks leaning together, tied at the neck."""
    rng = R('vale_sacks')
    g = K.Geo()
    for (x, y, sz, slot, v) in ((-0.3, 0.1, (0.3, 0.26, 0.26), BONE, 0.5), (0.3, 0.05, (0.3, 0.27, 0.28), ROPE, 0.56),
                                (0.0, -0.3, (0.28, 0.24, 0.22), BONE, 0.42)):
        K.rock(g, rng, (x, y, sz[2] * 0.55), sz, slot, n=9, var=v)
        zt = sz[2] * 1.05
        K.lathe(g, [(0.07, zt - 0.02), (0.1, zt + 0.1), (0.0, zt + 0.17)], 4, lambda b, k, s=slot: DWOOD if b == 0 else s,
                v, smooth=0, cap0=False, m=T(x, y, 0))
    p = kit.add('vale_sacks', g, budget=100, sheet={'az': 30, 'el': 24})
    p.info['footprint'] = plan_size(g)


def firewood_stack(kit):
    """A stack of split firewood between two stakes, its log ends to the front (−Y), three logs on top."""
    rng = R('vale_firewood_stack')
    g = K.Geo()
    W, D, H = 0.65, 0.3, 0.72
    K.box(g, (-W, -D, 0), (W, D, H), DWOOD, 0.34, skip=('-z',))
    for z, n in ((0.12, 5), (0.36, 4), (0.6, 5)):
        for k in range(n):
            x = -W + 0.13 + k * (2 * W - 0.26) / (n - 1) + jit(rng, 0.02)
            K.disc(g, 0.095 + jit(rng, 0.015), 5, WOOD, var=0.54 + jit(rng, 0.14), m=T(x, -D - 0.004, z) @ Rx(90),
                   phase=rng.uniform(0, 1))
    for x in (-W - 0.05, W + 0.05):
        K.box(g, (x - 0.04, -0.04, 0), (x + 0.04, 0.04, H + 0.2), WOOD, 0.42, skip=('-z',))
    for x, y in ((-0.25, -0.06), (0.3, 0.04)):
        K.tube(g, (x, y - 0.3, H + 0.08), (x + 0.05, y + 0.3, H + 0.08), 0.08, DWOOD, n=3, var=0.44)
    p = kit.add('vale_firewood_stack', g, budget=90, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = [1.5, 0.7]


def water_trough(kit):
    """A plank water trough with two iron bands, 1.6 × 0.6 m, full."""
    g = K.Geo()
    L, D, H = 0.8, 0.3, 0.55
    K.box(g, (-L, -D, 0), (L, D, H), DWOOD, 0.42, skip=('-z', '+z'))
    t = 0.06
    o = [(-L, -D), (L, -D), (L, D), (-L, D)]
    n = [(-L + t, -D + t), (L - t, -D + t), (L - t, D - t), (-L + t, D - t)]
    for k in range(4):
        a, b, c, d = o[k], o[(k + 1) % 4], n[(k + 1) % 4], n[k]
        g.pf([(a[0], a[1], H), (b[0], b[1], H), (c[0], c[1], H), (d[0], d[1], H)], DWOOD, 0.5)
        g.pf([(d[0], d[1], H - 0.1), (c[0], c[1], H - 0.1), (c[0], c[1], H), (d[0], d[1], H)], DWOOD, 0.3)
    g.pf([(n[0][0], n[0][1], H - 0.1), (n[1][0], n[1][1], H - 0.1), (n[2][0], n[2][1], H - 0.1),
          (n[3][0], n[3][1], H - 0.1)], WATER, 0.55)
    for x in (-0.5, 0.5):
        flat_strip(g, T(0, -D, 0), (x, 0.04), (x, H - 0.04), 0.07, IRON, 0.46, y=-0.008)
    p = kit.add('vale_water_trough', g, budget=40, sheet={'az': 30, 'el': 26})
    p.info['footprint'] = [1.6, 0.6]


def dog(kit):
    """A sitting dog, static: a brown hound sat on its haunches facing −Y — a rump on the ground, a chest rising to the
    shoulders, straight forelegs, a head with a square muzzle, two dropped ears, a pale chest patch, a green collar and a
    tail curled on the ground; ~0.8 m to the ear tips."""
    rng = R('vale_dog')
    g = K.Geo()
    C = DSTONE
    K.rock(g, rng, (0, 0.14, 0.19), (0.2, 0.27, 0.2), C, n=7, var=0.5)                        # the haunches
    ring = lambda c, r, z: [(c[0] + r * math.cos(a), c[1] + r * math.sin(a), z) for a in (0.3, 1.5, 2.7, 3.9, 5.1)]
    K.hull(g, ring((0, 0.1), 0.17, 0.26) + ring((0, -0.14), 0.12, 0.6), C, 0.52)               # the chest and neck
    K.rock(g, rng, (0, -0.2, 0.68), (0.1, 0.12, 0.1), C, n=8, var=0.54, flat=False)            # the head
    K.box(g, (-0.05, -0.42, 0.6), (0.05, -0.28, 0.68), C, 0.4, skip=('+y',))                    # the muzzle
    K.box(g, (-0.03, -0.43, 0.65), (0.03, -0.4, 0.69), INK, 0.5, skip=('+y',))                  # the nose
    for sx in (-1, 1):                                                                           # the ears
        card(g, [(sx * 0.07, -0.16, 0.72), (sx * 0.13, -0.13, 0.7), (sx * 0.17, -0.1, 0.52), (sx * 0.11, -0.12, 0.54)],
             C, 0.36)
    for sx in (-1, 1):                                                                           # the forelegs
        K.tube(g, (sx * 0.08, -0.2, 0.0), (sx * 0.08, -0.17, 0.4), 0.035, C, n=3, var=0.42, cap0=True, cap1=False)
    K.tube(g, (0.12, 0.34, 0.04), (0.34, 0.44, 0.05), 0.03, C, r1=0.015, n=3, var=0.46, cap0=False)   # the tail
    plate(g, [(-0.07, 0.3), (0.07, 0.3), (0.05, 0.48), (-0.05, 0.48)], -0.27, BONE, 0.62)           # the chest patch
    K.lathe(g, [(0.1, 0.56), (0.1, 0.6)], 5, CLOTH1, 0.5, smooth=0, cap0=False, cap1=False, m=T(0, -0.17, 0))   # collar
    p = kit.add('vale_dog', g, budget=100, sheet={'az': 30, 'el': 16})
    p.info['footprint'] = plan_size(g)
    p.info['no_collider'] = True


def cart_hand(kit):
    """A small handcart — a wheelbarrow: a plank box on two rails, one plank wheel at the front (−Y) on an iron axle,
    two handles to the back resting on two short legs, a sack in it."""
    rng = R('vale_cart_hand')
    g = K.Geo()
    K.box(g, (-0.3, -0.5, 0.42), (0.3, 0.3, 0.72), WOOD, 0.48, skip=('-z', '+z'))
    inner = [(-0.27, -0.47), (0.27, -0.47), (0.27, 0.27), (-0.27, 0.27)]
    g.pf([(x, y, 0.45) for x, y in inner], WOOD, 0.36)
    for k in range(4):
        a, b = inner[k], inner[(k + 1) % 4]
        g.pf([(b[0], b[1], 0.45), (a[0], a[1], 0.45), (a[0], a[1], 0.72), (b[0], b[1], 0.72)], WOOD, 0.32)
    K.rock(g, rng, (0.03, -0.08, 0.72), (0.22, 0.25, 0.16), BONE, n=8, var=0.5)
    for sx in (-1, 1):
        K.box(g, (sx * 0.22 - 0.03, -0.62, 0.36), (sx * 0.22 + 0.03, 0.85, 0.42), DWOOD, 0.4, skip=('+z',))
        K.tube(g, (sx * 0.22, 0.85, 0.39), (sx * 0.27, 1.15, 0.52), 0.025, DWOOD, n=3, var=0.44, cap0=False)
        K.box(g, (sx * 0.22 - 0.03, 0.55, 0), (sx * 0.22 + 0.03, 0.61, 0.36), DWOOD, 0.4, skip=('-z', '+z'))
    for sx, rot in ((-1, -90), (1, 90)):
        K.disc(g, 0.28, 8, DWOOD, var=0.46, m=T(sx * 0.05, -0.62, 0.28) @ Ry(rot))
    K.tube(g, (-0.26, -0.62, 0.28), (0.26, -0.62, 0.28), 0.03, IRON, n=4, var=0.44)
    p = kit.add('vale_cart_hand', g, budget=110, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = plan_size(g)


# ====================================================================== install 2: the living Vale
def flute(g, mk, n, k_in=0.84):
    """Pulls every other vertex of a lathe added since `mk` toward its axis: a fluted trunk."""
    for vi in range(mk[0], len(g.V)):
        v = g.V[vi]
        r = math.hypot(v.x, v.y)
        if r < 1e-6:
            continue
        k = int(round(math.atan2(v.y, v.x) / (2 * math.pi / n))) % n
        if k % 2:
            g.V[vi] = Vector((v.x * k_in, v.y * k_in, v.z))


def yew(kit):
    """A yew (Woodcutting 60): a stout, dark, fluted trunk leaning a little, four limbs, and a dense dark-green dome
    (slot 7, the pine's) broad and low — ~6.5 m across, 6.5 m tall."""
    rng = R('vale_yew')
    g = K.Geo()
    mk = g.mark()
    K.lathe(g, [(0.5, 0.0), (0.42, 0.6), (0.36, 1.5), (0.3, 2.3), (0.22, 3.0)], 10, DWOOD,
            lambda b, k: 0.3 + jit(rng, 0.05), smooth=30, cap0=False, cap1=False)
    flute(g, mk, 10)
    g.transform(Matrix.Shear('XY', 4, (0.05, 0.03)), mk)
    for a, zt in ((15, 4.0), (110, 3.9), (200, 4.1), (300, 3.8)):
        d = Vector((math.cos(math.radians(a)) * 1.5, math.sin(math.radians(a)) * 1.5, 0))
        K.tube(g, (0.1, 0.05, 2.6), tuple(d + Vector((0.1, 0.05, zt))), 0.12, DWOOD, r1=0.05, n=4, var=0.34,
               cap0=False, cap1=False)
    blobs = [((0.1, 0.05, 4.8), (2.5, 2.4, 1.7), 11)]
    for a, r, z, sz in ((20, 2.0, 3.95, (1.5, 1.4, 1.1)), (95, 2.1, 4.1, (1.45, 1.35, 1.05)), (165, 2.0, 3.9, (1.5, 1.4, 1.1)),
                        (240, 2.1, 4.05, (1.45, 1.35, 1.05)), (310, 2.0, 4.0, (1.5, 1.4, 1.1)),
                        (60, 1.0, 5.5, (1.2, 1.1, 0.8)), (230, 1.0, 5.4, (1.2, 1.1, 0.8))):
        blobs.append(((0.1 + math.cos(math.radians(a)) * r, 0.05 + math.sin(math.radians(a)) * r, z), sz, 9))
    for i, (c, sz, n) in enumerate(blobs):
        K.rock(g, rng, c, sz, CLOTH2, n=n, var=0.38 + 0.08 * (i % 3), flat=False, smooth=0)
    p = kit.add('vale_yew', g, budget=280, sheet={'az': 30, 'el': 14})
    lo, hi = g.bounds()
    p.info['canopy'] = round(hi.z, 2)
    p.info['footprint'] = plan_size(g)
    p.info['node'] = True
    return p


def yew_old(kit):
    """The ancient yew of the glade: a huge hollow trunk (its opening to −Y, 1.2 m wide, 3.3 m tall inside — a
    hero stands in it), five great limbs, a vast dome 9 m across and 9 m tall, six roots flaring out and moss at the
    foot. The inside walls wind inward so the hollow reads from within."""
    rng = R('vale_yew_old')
    g = K.Geo()
    n = 12
    a0, a1 = math.radians(300), math.radians(600)        # the gap 240..300 degrees: centred on −Y

    def ring(r, z, wob=0.0):
        pts = []
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            rr = r * (1 + (jit(rng, wob) if 0 < i < n else 0.0))
            pts.append(g.v((rr * math.cos(a), rr * math.sin(a), z)))
        return pts
    outer = [ring(1.85, 0.0, 0.08), ring(1.55, 1.3, 0.07), ring(1.35, 2.7, 0.06), ring(1.2, 4.0, 0.05), ring(1.05, 5.0, 0.04)]
    inner = [ring(1.35, 0.0, 0.05), ring(1.2, 1.5, 0.05), ring(0.85, 2.9, 0.04), ring(0.06, 3.3)]
    for rows, wind in ((outer, 1), (inner, -1)):
        for j in range(len(rows) - 1):
            a, b = rows[j], rows[j + 1]
            for i in range(n):
                f = (a[i], a[i + 1], b[i + 1], b[i])
                g.f(f if wind > 0 else tuple(reversed(f)), DWOOD, 0.3 + jit(rng, 0.05), smooth=30)
    # the jambs of the opening and its lintel
    for col, wind in ((0, 1), (n, -1)):
        for (ja, jb) in ((0, 0), (1, 1), (2, 2)):
            f = (outer[ja][col], outer[ja + 1][col], inner[jb + 1][col], inner[jb][col])
            g.f(f if wind > 0 else tuple(reversed(f)), DWOOD, 0.26, smooth=0)
    g.f((outer[3][0], outer[3][n], inner[3][n], inner[3][0]), DWOOD, 0.24, smooth=0)
    g.f((inner[2][0], inner[2][n], inner[3][n], inner[3][0]), DWOOD, 0.24, smooth=0)
    g.f(tuple(outer[4]), DWOOD, 0.36, smooth=0)                                       # the trunk's top
    flute(g, (0, 0), n, 0.93)
    for a, zt, ln in ((10, 7.0, 3.0), (85, 6.6, 3.2), (160, 7.2, 2.9), (235, 6.7, 3.1), (300, 7.1, 3.0)):
        d = Vector((math.cos(math.radians(a)) * ln, math.sin(math.radians(a)) * ln, 0))
        K.tube(g, (math.cos(math.radians(a)) * 0.6, math.sin(math.radians(a)) * 0.6, 4.6), tuple(d + Vector((0, 0, zt))), 0.3,
               DWOOD, r1=0.1, n=5, var=0.3, cap0=False, cap1=False)
    blobs = [((0, 0, 7.3), (3.8, 3.6, 1.7), 13)]
    for a, r, z, sz in ((0, 2.7, 6.3, (1.9, 1.8, 1.4)), (60, 2.8, 6.5, (1.85, 1.75, 1.35)), (120, 2.7, 6.2, (1.9, 1.8, 1.4)),
                        (180, 2.8, 6.4, (1.85, 1.75, 1.35)), (240, 2.7, 6.3, (1.9, 1.8, 1.4)), (300, 2.8, 6.5, (1.85, 1.75, 1.35)),
                        (30, 1.4, 8.0, (1.6, 1.5, 0.9)), (210, 1.4, 7.9, (1.6, 1.5, 0.9))):
        blobs.append(((math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, z), sz, 9))
    for i, (c, sz, nn) in enumerate(blobs):
        K.rock(g, rng, c, sz, CLOTH2, n=nn, var=0.36 + 0.08 * (i % 3), flat=False, smooth=0)
    for a in (20, 80, 140, 200, 220, 340):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        K.tube(g, tuple(d * 1.6 + Vector((0, 0, 0.7))), tuple(d * 3.4 + Vector((0, 0, -0.05))), 0.3, DWOOD, r1=0.08, n=4,
               var=0.3, cap0=False, cap1=False)
    for a, r in ((40, 2.2), (170, 2.1), (320, 2.3)):
        c = (math.cos(math.radians(a)) * r, math.sin(math.radians(a)) * r, 0.12)
        K.rock(g, rng, c, (0.5, 0.45, 0.22), MOSS, n=7, var=0.4)
    p = kit.add('vale_yew_old', g, budget=520, sheet={'az': 30, 'el': 12})
    lo, hi = g.bounds()
    p.info['canopy'] = round(hi.z, 2)
    p.info['footprint'] = [9.0, 9.0]
    p.info['opening'] = K.blender_to_game(Vector((0.0, -1.6, 0.0)))     # the hollow's mouth on the ground, game (x, y, z)
    p.info['hollow'] = 1.2                                               # the hollow's inner radius
    return p


def log_tube(g, p0, p1, r, var=0.4, n=6):
    """A cut log: dark bark round, pale timber on the cut ends."""
    mt, ln = K.orient(p0, p1)
    K.lathe(g, [(r, 0.0), (r, ln)], n, DWOOD, var, smooth=50, cap_slot=WOOD, m=mt, phase=math.pi / n)


def sawmill(kit):
    """The sawmill, 8 × 6 m, OPEN at the front (−Y) and open-sided above waist height: a plank floor a step up, six
    posts, a plank back wall, half-height side walls, a plank roof with its ridge front to back; inside, a heavy saw
    bench with a big toothed circular blade standing through its slot and a log part-sawn on it, a flywheel on the
    right wall with a crank, a log ramp up the left side, two stacks of planks on the right and a sawdust heap.
    `info['saw']` is the blade's centre, `info['use']` where the hero stands to saw (facing the blade, north)."""
    rng = R('vale_sawmill')
    g = K.Geo()
    w, d, h, zr = 8.0, 6.0, 2.9, 5.0
    hx, hy = w / 2, d / 2
    zf = 0.12
    K.box(g, (-hx, -hy, -0.2), (hx, hy, zf), WOOD, 0.42, skip=('-z',))                        # the deck
    for x in (-hx + 0.15, 0.0, hx - 0.15):
        for y in (-hy + 0.15, hy - 0.15):
            K.box(g, (x - 0.14, y - 0.14, zf), (x + 0.14, y + 0.14, h), DWOOD, 0.4, skip=('-z', '+z'))
    K.box(g, (-hx, hy - 0.18, zf), (hx, hy, h - 0.2), WOOD, 0.48 + jit(rng, 0.03), skip=('-z', '+z', '-x', '+x'))
    m = on_face('+y', hy, 0.0, 0.0)
    for z in (0.8, 1.5, 2.2):
        flat_strip(g, m, (-hx + 0.3, z), (hx - 0.3, z), 0.05, DWOOD, 0.34, y=-0.01)
    for sgn in (-1, 1):                                                                       # the low side walls
        x0, x1 = sorted((sgn * hx, sgn * (hx - 0.18)))
        K.box(g, (x0, -hy + 0.3, zf), (x1, hy - 0.18, 1.2), WOOD, 0.46, skip=('-z', '-y', '+y'))
    K.box(g, (-hx - 0.1, -hy - 0.06, h - 0.26), (hx + 0.1, -hy + 0.26, h), DWOOD, 0.42)           # the front beam
    K.box(g, (-hx - 0.1, hy - 0.26, h - 0.26), (hx + 0.1, hy + 0.06, h), DWOOD, 0.42)             # the back beam
    for sgn in (-1, 1):
        x0, x1 = sorted((sgn * (hx + 0.06), sgn * (hx - 0.26)))
        K.box(g, (x0, -hy + 0.26, h - 0.24), (x1, hy - 0.26, h), DWOOD, 0.42, skip=('-z', '+z', '-y', '+y'))
    ze = eave_z(h, zr, hx, 0.4)
    gable_roof_y(g, -hx, hx, -hy, hy, ze, zr, DWOOD, var=0.52, overhang=0.4)
    g.pf([(hx, hy, h), (-hx, hy, h), (0.0, hy, zr - 0.06)], WOOD, 0.5)                          # the back gable
    g.pf([(-hx, hy - 0.18, h), (hx, hy - 0.18, h), (0.0, hy - 0.18, zr - 0.06)], WOOD, 0.42)
    K.box(g, (-0.1, -hy + 0.1 - 0.1, h), (0.1, -hy + 0.1 + 0.1, zr - 0.2), DWOOD, 0.44, skip=('-z', '+z'))   # the king post
    # the saw bench and its blade
    bx, by, bz = -0.6, 0.4, 0.9
    K.box(g, (bx - 1.3, by - 0.5, bz - 0.12), (bx + 1.3, by + 0.5, bz), DWOOD, 0.4)
    for x in (bx - 1.1, bx + 1.1):
        for y in (by - 0.38, by + 0.38):
            K.box(g, (x - 0.07, y - 0.07, zf), (x + 0.07, y + 0.07, bz - 0.12), DWOOD, 0.36, skip=('-z', '+z'))
    mk = g.mark()
    K.lathe(g, [(0.58, -0.012), (0.58, 0.012)], 24, BMETAL, 0.62, smooth=0, phase=0.0)
    for vi in range(mk[0], len(g.V)):
        v = g.V[vi]
        k = int(round(math.atan2(v.y, v.x) / (2 * math.pi / 24))) % 24
        if k % 2:
            g.V[vi] = Vector((v.x * 0.93, v.y * 0.93, v.z))
    g.transform(T(bx, by, bz - 0.05) @ Rx(90), mk)                                              # the blade stands in the XZ plane
    K.tube(g, (bx, by - 0.6, bz - 0.05), (bx, by + 0.6, bz - 0.05), 0.04, IRON, n=4, var=0.4)   # the arbor
    log_tube(g, (bx - 2.0, by, bz + 0.2), (bx - 0.05, by, bz + 0.2), 0.2, 0.38)                  # the log, sawn to the blade
    log_tube(g, (bx + 0.05, by, bz + 0.2), (bx + 1.1, by, bz + 0.2), 0.2, 0.38)
    # the flywheel on the right wall, a crank on it
    fx, fy, fz = hx - 0.45, 1.6, 1.3
    for xx, rot in ((fx - 0.05, 90), (fx + 0.05, -90)):
        K.disc(g, 0.7, 10, DWOOD, var=0.44, m=T(xx, fy, fz) @ Ry(rot))
    K.tube(g, (fx - 0.3, fy, fz), (fx + 0.12, fy, fz), 0.05, IRON, n=4, var=0.4)
    K.tube(g, (fx - 0.3, fy, fz), (fx - 0.3, fy + 0.45, fz + 0.45), 0.03, IRON, n=4, var=0.46)
    K.tube(g, (fx - 0.3, fy + 0.45, fz + 0.45), (fx - 0.65, fy + 0.45, fz + 0.45), 0.03, WOOD, n=4, var=0.46)
    # the log ramp up the left side, a log waiting on it
    for y in (-0.3, 0.9):
        K.box(g, (-hx + 0.3, y - 0.08, zf), (-hx + 2.2, y + 0.08, 0.3), DWOOD, 0.38, skip=('-z',))
        g.pf([(-hx + 2.2, y - 0.08, 0.3), (-hx + 2.2, y + 0.08, 0.3), (-hx + 2.9, y + 0.08, 0.78), (-hx + 2.9, y - 0.08, 0.78)], DWOOD, 0.4)
        g.pf([(-hx + 2.9, y - 0.08, 0.78), (-hx + 2.9, y + 0.08, 0.78), (-hx + 2.9, y + 0.08, 0.7), (-hx + 2.9, y - 0.08, 0.7)], DWOOD, 0.32)
    log_tube(g, (-hx + 0.4, 0.3, 0.52), (-hx + 2.3, 0.3, 0.52), 0.21, 0.36)
    # two stacks of planks on the right, a sawdust heap by the bench
    for y0 in (-2.4, 0.0):
        K.box(g, (hx - 2.2, y0, zf), (hx - 0.4, y0 + 1.1, zf + 0.5), WOOD, 0.5, skip=('-z',))
        m = on_face('-y', y0, 0.0, 0.0)
        for z in (zf + 0.12, zf + 0.25, zf + 0.38):
            flat_strip(g, m, (hx - 2.2, z), (hx - 0.4, z), 0.03, DWOOD, 0.34, y=-0.005)
    K.rock(g, rng, (bx + 0.4, by - 0.9, zf + 0.12), (0.5, 0.4, 0.14), BRASS, n=7, var=0.62)
    p = kit.add('vale_sawmill', g, budget=480, sheet={'az': 22, 'el': 22})
    p.info['footprint'] = [w, d]
    p.info['open'] = True
    p.info['saw'] = K.blender_to_game(Vector((bx, by, bz + 0.2)))                 # the blade's centre, game (x, y, z)
    p.info['use'] = {'at': K.blender_to_game(Vector((bx, by - 1.2, 0.0))), 'yaw': 180}   # the hero's stand, facing the bench
    return p


def woodcutter_hut(kit):
    """The woodcutter's cabin, 6 × 5 m: walls of stacked logs crossing at the corners (every other course sticks
    out), a steep shingled roof with its ridge along x, a stone chimney at the back right, a plank door at x −1.2
    and one glazed window at +1.4 on the front, an axe sunk in a chopping block beside the door."""
    rng = R('vale_woodcutter_hut')
    g = K.Geo()
    w, d = 6.0, 5.0
    hx, hy = w / 2, d / 2
    t = 0.3
    lz = 0.38
    courses = 7
    for i in range(courses):
        z0, z1 = i * lz, (i + 1) * lz
        ext = 0.25 if i % 2 == 0 else 0.0
        extb = 0.25 if i % 2 == 1 else 0.0
        ins = 0.04 if i % 2 else 0.0          # every other course a little inset: its ledges catch the light
        insb = 0.04 if i % 2 == 0 else 0.0
        v = 0.36 + jit(rng, 0.05)
        K.box(g, (-hx - ext, -hy - t / 2 + ins, z0), (hx + ext, -hy + t / 2, z1), DWOOD, v, skip=('+y',))
        K.box(g, (-hx - ext, hy - t / 2, z0), (hx + ext, hy + t / 2 - ins, z1), DWOOD, v, skip=('-y',))
        K.box(g, (-hx - t / 2 + insb, -hy - extb, z0), (-hx + t / 2, hy + extb, z1), DWOOD, v - 0.02, skip=('+x',))
        K.box(g, (hx - t / 2, -hy - extb, z0), (hx + t / 2 - insb, hy + extb, z1), DWOOD, v - 0.02, skip=('-x',))
    hwall = courses * lz
    z_ridge = 4.5
    for x, sgn in ((-hx, -1), (hx, 1)):                                                          # plank gables
        pts = [(x, -hy, hwall), (x, hy, hwall), (x, 0, z_ridge)]
        g.pf(pts if sgn > 0 else list(reversed(pts)), WOOD, 0.46, smooth=0)
    gable_roof(g, -hx, hx, -hy, hy, hwall - 0.05, z_ridge, DWOOD, var=0.58, overhang=0.4, thick=0.14)
    # shingle rows: three flat strips laid on each slope, a hair proud of it
    for sy in (-1, 1):
        ya, yb = (-hy - 0.4, 0.0) if sy < 0 else (hy + 0.4, 0.0)
        za, zb = hwall - 0.05, z_ridge
        along = Vector((0, yb - ya, zb - za)).normalized()
        nrm = Vector((0, -(zb - za), yb - ya)).normalized()
        if nrm.z < 0:
            nrm = -nrm
        for k in (0.25, 0.5, 0.75):
            c = Vector((0, ya + (yb - ya) * k, za + (zb - za) * k)) + nrm * 0.012
            a_, b_ = c - along * 0.045, c + along * 0.045
            quad = [(-hx - 0.4, a_.y, a_.z), (hx + 0.4, a_.y, a_.z), (hx + 0.4, b_.y, b_.z), (-hx - 0.4, b_.y, b_.z)]
            g.pf(quad if sy < 0 else list(reversed(quad)), DWOOD, 0.4)
    K.box(g, (1.5, hy - 0.2, 1.0), (2.3, hy + 0.5, z_ridge + 0.45), STONE, 0.45, skip=('-z',))     # the chimney
    g.pf([(1.65, hy - 0.05, z_ridge + 0.46), (2.15, hy - 0.05, z_ridge + 0.46), (2.15, hy + 0.35, z_ridge + 0.46), (1.65, hy + 0.35, z_ridge + 0.46)], INK, 0.5)
    town_door(g, on_face('-y', -hy - t / 2, -1.2, 0.0), w=1.0, h=2.0, leaf=WOOD)
    town_window(g, on_face('-y', -hy - t / 2, 1.4, 1.1), w=0.9, h=0.9)
    # the chopping block with an axe sunk in it
    sx, sy = 2.55, -hy - 0.55
    K.lathe(g, [(0.24, 0.0), (0.22, 0.42)], 7, DWOOD, 0.38, smooth=0, cap0=False, cap_slot=WOOD, m=T(sx, sy, 0))
    K.tube(g, (sx + 0.05, sy, 0.44), (sx + 0.45, sy + 0.1, 1.05), 0.022, WOOD, n=4, var=0.46, cap0=False)
    card(g, [(sx - 0.08, sy, 0.44), (sx + 0.14, sy, 0.44), (sx + 0.17, sy, 0.78), (sx - 0.02, sy, 0.7)], BMETAL, 0.62, gap=0.025)
    p = kit.add('vale_woodcutter_hut', g, budget=420, sheet={'az': 32, 'el': 18})
    p.info['footprint'] = [w, d]
    p.info['door'] = [-1.2, 0.0, hy + t / 2]                            # the threshold's centre, game (x, y, z)
    p.info['chimney'] = [1.9, z_ridge + 0.45, -hy - 0.15]               # the flue's top, game (x, y, z)
    return p


def lumber_pile(kit):
    """A stack of trimmed logs on two bearers: four, three and two, 3 m long, the cut ends pale."""
    rng = R('vale_lumber_pile')
    g = K.Geo()
    for x in (-1.0, 1.0):
        K.box(g, (x - 0.1, -0.75, 0), (x + 0.1, 0.75, 0.2), DWOOD, 0.36, skip=('-z',))
    r = 0.17
    rows = [(0.2 + r, (-0.56, -0.19, 0.19, 0.56)), (0.2 + r + 2 * r * 0.88, (-0.37, 0.0, 0.37)), (0.2 + r + 4 * r * 0.88, (-0.18, 0.18))]
    for z, ys in rows:
        for y in ys:
            dx = jit(rng, 0.08)
            log_tube(g, (-1.5 + dx, y, z), (1.5 + dx, y, z), r * (1 + jit(rng, 0.06)), 0.36 + jit(rng, 0.06))
    p = kit.add('vale_lumber_pile', g, budget=220, sheet={'az': 30, 'el': 22})
    p.info['footprint'] = plan_size(g)
    return p


def fallen_trunk(kit):
    """A fallen tree, 7 m, lying along x: a mossy trunk in three bends tapering to the tip at +x, its torn root
    plate standing up at the −x end with six roots clawing at the air, two snapped branch stubs, moss on top."""
    rng = R('vale_fallen_trunk')
    g = K.Geo()
    pts = [(-3.0, 0.0, 0.75), (-1.2, 0.08, 0.58), (0.8, -0.05, 0.42), (2.6, 0.1, 0.34), (3.5, 0.15, 0.3)]
    rs = [0.55, 0.46, 0.36, 0.26, 0.12]
    for i in range(4):
        K.tube(g, pts[i], pts[i + 1], rs[i], DWOOD, r1=rs[i + 1], n=7, var=0.34 + jit(rng, 0.04), cap0=False,
               cap1=(i == 3), smooth=45)
    # the root plate: a ragged disc standing at the butt, roots out of its rim
    K.disc(g, 0.95, 9, DWOOD, var=0.3, m=T(-3.05, 0.0, 0.85) @ Ry(-90), rng=rng, jitter=0.15)
    K.disc(g, 0.95, 9, DSTONE, var=0.4, m=T(-3.12, 0.0, 0.85) @ Ry(90), rng=rng, jitter=0.15)
    for a in (20, 70, 115, 160, 250, 300):
        d = Vector((0, math.cos(math.radians(a)), math.sin(math.radians(a))))
        K.tube(g, tuple(Vector((-3.08, 0, 0.85)) + d * 0.8), tuple(Vector((-3.3, 0, 0.85)) + d * 1.45 + Vector((-0.2, 0, 0))),
               0.12, DWOOD, r1=0.03, n=4, var=0.3, cap0=False, cap1=False)
    for (x, a, ln) in ((-0.4, 60, 0.6), (1.6, 120, 0.5)):
        d = Vector((0.2, math.cos(math.radians(a)), math.sin(math.radians(a)))).normalized()
        base = Vector((x, 0.0, 0.5))
        K.tube(g, tuple(base), tuple(base + d * ln), 0.1, DWOOD, r1=0.05, n=4, var=0.32, cap0=False)
    for (x, y, z, s) in ((-2.0, 0.05, 1.1, 0.45), (-0.6, -0.1, 0.95, 0.4), (0.9, 0.0, 0.76, 0.38), (2.2, 0.1, 0.6, 0.3)):
        K.rock(g, rng, (x, y, z - 0.04), (s * 1.3, s * 0.9, 0.1), MOSS, n=7, var=0.34, flat=False, smooth=0)
    K.rock(g, rng, (-2.6, -0.5, 0.08), (0.55, 0.45, 0.16), MOSS, n=7, var=0.34)
    p = kit.add('vale_fallen_trunk', g, budget=240, sheet={'az': 30, 'el': 20})
    p.info['footprint'] = plan_size(g)
    return p


def glade_stone(kit):
    """A standing stone, 2.6 m: a tapering slab with a flat front face (−Y) carrying a carved spiral (a dark groove),
    moss at its foot."""
    rng = R('vale_glade_stone')
    g = K.Geo()
    pts = []
    for (hw, hd, z, front_flat) in ((0.6, 0.5, 0.0, True), (0.55, 0.48, 1.3, True), (0.4, 0.34, 2.45, True), (0.25, 0.2, 2.6, False)):
        for sx in (-1, 1):
            for sy in (-1, 1):
                y = -hd if (sy < 0 and front_flat) else sy * hd * (1 + jit(rng, 0.12))
                pts.append((sx * hw * (1 + jit(rng, 0.1)), y, z + (jit(rng, 0.08) if z > 0 else 0.0)))
    K.hull(g, pts, STONE, 0.44, smooth=0)
    path = []
    cx, cz = 0.0, 1.5
    for i in range(34):
        u = i / 33
        th = u * 2 * math.pi * 2.6
        r = 0.05 + 0.3 * u
        path.append((cx + r * math.cos(th), -0.5 - 0.012, cz + r * math.sin(th)))
    K.ribbon(g, path, 0.04, INK, var=0.5, normal=(0, -1, 0), smooth=0)
    for (x, y, s) in ((-0.5, -0.35, 0.35), (0.45, 0.3, 0.3), (0.1, -0.55, 0.28)):
        K.rock(g, rng, (x, y, 0.08), (s, s * 0.9, 0.14), MOSS, n=7, var=0.34)
    p = kit.add('vale_glade_stone', g, budget=140, sheet={'az': 20, 'el': 14})
    p.info['footprint'] = plan_size(g)
    return p


def bird_nest(kit):
    """A bird's nest, 0.6 m across: a straw bowl, twigs poking from its rim, three pale eggs in the hollow; its
    origin at the nest's base so it sits on a roof or in a canopy."""
    rng = R('vale_bird_nest')
    g = K.Geo()
    K.lathe(g, [(0.12, 0.0), (0.27, 0.09), (0.3, 0.2), (0.25, 0.25), (0.19, 0.16), (0.0, 0.13)], 8, ROPE,
            lambda b, k: 0.4 + jit(rng, 0.08), smooth=30, cap0=True, cap1=False, phase=0.2)
    for a in (15, 80, 150, 210, 290, 340):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        K.tube(g, tuple(d * 0.22 + Vector((0, 0, 0.2))), tuple(d * 0.38 + Vector((jit(rng, 0.05), jit(rng, 0.05), 0.2 + jit(rng, 0.06)))),
               0.012, DWOOD, r1=0.006, n=3, var=0.4, cap0=False, cap1=False)
    for (x, y, rot) in ((-0.06, -0.03, 20), (0.06, -0.02, -15), (0.0, 0.07, 5)):
        K.lathe(g, [(0.0, 0.0), (0.04, 0.03), (0.04, 0.065), (0.0, 0.095)], 5, BONE, 0.68, smooth=40,
                m=T(x, y, 0.125) @ Rx(rot))
    p = kit.add('vale_bird_nest', g, budget=190, sheet={'az': 30, 'el': 32})
    p.info['footprint'] = plan_size(g)
    p.info['no_collider'] = True
    return p


def hunters_hide(kit):
    """A hunter's hide: two posts, a low plank platform at 1.0 m on cross-bearers, a ladder up its back (+Y) and a
    leafy screen along the front rail. `info['walkable']` is the platform's top."""
    rng = R('vale_hunters_hide')
    g = K.Geo()
    for x in (-0.9, 0.9):
        K.box(g, (x - 0.08, -0.08, 0), (x + 0.08, 0.08, 2.4), DWOOD, 0.38, skip=('-z',))
    zp = 1.0
    K.box(g, (-0.95, -0.6, zp - 0.08), (0.95, 0.6, zp), WOOD, 0.46)
    for y in (-0.45, 0.45):
        K.box(g, (-1.0, y - 0.06, zp - 0.2), (1.0, y + 0.06, zp - 0.08), DWOOD, 0.36, skip=('+z',))
    for x in (-0.3, 0.3):                                                                        # the ladder rails
        K.tube(g, (x, 1.0, 0.0), (x, 0.62, zp + 0.3), 0.035, DWOOD, n=3, var=0.4, cap0=False)
    for k in range(4):
        z = 0.22 + k * 0.26
        y = 1.0 - 0.38 * (z / (zp + 0.3))
        K.tube(g, (-0.3, y, z), (0.3, y, z), 0.025, WOOD, n=3, var=0.46, cap0=False, cap1=False)
    K.box(g, (-0.95, -0.66, 1.85), (0.95, -0.54, 1.95), DWOOD, 0.4)                               # the front rail
    for (x, z, s) in ((-0.65, 1.35, 0.5), (-0.1, 1.5, 0.55), (0.5, 1.3, 0.5), (0.9, 1.75, 0.42), (-0.9, 1.75, 0.42), (0.2, 1.95, 0.45)):
        K.rock(g, rng, (x, -0.62, z), (s, 0.22, s * 0.85), CLOTH1, n=8, var=0.46 + jit(rng, 0.08), flat=False, smooth=0)
    p = kit.add('vale_hunters_hide', g, budget=220, sheet={'az': 30, 'el': 18})
    p.info['footprint'] = plan_size(g)
    p.info['walkable'] = zp
    return p


def wagon(kit):
    """A travelling merchant's covered wagon, its length along y (the horse to −Y): four plank wheels on iron
    axles, a plank bed with boarded sides, a hooped canvas top open at the back where the wares show — a barrel, a
    crate, a rolled rug, two sacks — a driver's box and footboard at the front, two shafts reaching forward.
    `info['hitch']` is where the horse stands (its origin, facing the same way as the wagon)."""
    rng = R('vale_wagon')
    g = K.Geo()
    y0, y1 = -1.4, 1.9
    K.box(g, (-0.9, y0, 0.78), (0.9, y1, 0.88), WOOD, 0.46, skip=('+z',))
    g.pf([(-0.86, y0 + 0.04, 0.88), (0.86, y0 + 0.04, 0.88), (0.86, y1 - 0.04, 0.88), (-0.86, y1 - 0.04, 0.88)], WOOD, 0.4)
    for sx in (-1, 1):
        xa, xb = sorted((sx * 0.9, sx * 0.84))
        K.box(g, (xa, y0, 0.88), (xb, y1, 1.3), WOOD, 0.44, skip=('-z',))
    K.box(g, (-0.84, y0, 0.88), (0.84, y0 + 0.05, 1.3), WOOD, 0.44, skip=('-z', '-x', '+x'))      # the headboard
    K.box(g, (-0.84, y1 - 0.05, 0.88), (0.84, y1, 1.12), WOOD, 0.44, skip=('-z', '-x', '+x'))      # the tailboard, low
    for (yw, r, zw) in ((1.1, 0.56, 0.56), (-0.75, 0.42, 0.42)):                                   # the wheels
        for sx in (-1, 1):
            K.disc(g, r, 8, DWOOD, var=0.44, m=T(sx * 1.08, yw, zw) @ Ry(sx * 90), phase=math.pi / 8)
            K.disc(g, r, 8, DWOOD, var=0.36, m=T(sx * 1.0, yw, zw) @ Ry(-sx * 90), phase=math.pi / 8)
            K.disc(g, 0.12, 5, BRASS, var=0.56, m=T(sx * 1.1, yw, zw) @ Ry(sx * 90))
        K.tube(g, (-1.1, yw, zw), (1.1, yw, zw), 0.045, IRON, n=4, var=0.42, cap0=False, cap1=False)
    # the canvas: a half-ellipse hoop swept along the bed, closed at the front, open at the back
    nu, nv = 8, 4

    def canvas(i, j):
        a = math.pi * i / nu
        return (1.02 * math.cos(a), y0 + 0.1 + (y1 - y0 - 0.1) * j / nv, 1.3 + 1.4 * math.sin(a))
    K.surface(g, nu, nv, canvas, BONE, var=lambda i, j: 0.58 - 0.05 * (j % 2), smooth=30)        # the bays between hoops
    K.surface(g, nu, nv, lambda i, j: canvas(nu - i, j), BONE, var=0.42, smooth=30)              # its inside
    g.pf([canvas(i, 0) for i in range(nu + 1)], BONE, 0.5)                                       # the front panel
    # the driver's box and footboard, the shafts
    K.box(g, (-0.7, y0 - 0.55, 0.88), (0.7, y0 - 0.1, 1.2), DWOOD, 0.4, skip=('-z',))
    K.box(g, (-0.8, y0 - 0.9, 0.72), (0.8, y0 - 0.55, 0.78), WOOD, 0.44)
    for sx in (-1, 1):
        K.tube(g, (sx * 0.62, y0 - 0.2, 0.7), (sx * 0.55, -2.5, 0.78), 0.04, DWOOD, n=4, var=0.4, cap0=False)
    # the wares at the back
    K.lathe(g, [(0.25, 0.0), (0.28, 0.25), (0.28, 0.45), (0.25, 0.7)], 7, DWOOD, 0.42, smooth=40, cap0=False,
            m=T(-0.45, 1.45, 0.88))
    K.lathe(g, [(0.29, 0.12), (0.29, 0.18)], 7, IRON, 0.44, smooth=0, cap0=False, cap1=False, m=T(-0.45, 1.45, 0.88))
    K.lathe(g, [(0.29, 0.5), (0.29, 0.56)], 7, IRON, 0.44, smooth=0, cap0=False, cap1=False, m=T(-0.45, 1.45, 0.88))
    K.box(g, (0.1, 1.2, 0.88), (0.75, 1.8, 1.38), WOOD, 0.5, skip=('-z',))
    K.tube(g, (-0.75, 0.2, 1.1), (0.75, 0.2, 1.1), 0.2, CLOTH2, n=6, var=0.48)                   # a rolled rug
    K.rock(g, rng, (0.4, 0.75, 1.08), (0.32, 0.32, 0.22), ROPE, n=7, var=0.56)
    K.rock(g, rng, (-0.35, 0.8, 1.08), (0.3, 0.3, 0.2), BONE, n=7, var=0.5)
    p = kit.add('vale_wagon', g, budget=440, sheet={'az': 32, 'el': 20})
    p.info['footprint'] = plan_size(g)
    p.info['hitch'] = K.blender_to_game(Vector((0.0, -2.95, 0.0)))     # the horse's origin, game (x, y, z); same yaw
    return p


def gallows(kit):
    """An empty roadside gallows: a stone footing, a square post, an arm out to the front (−Y) on a brace, a rope
    with a noose dangling from the arm's end. Nobody in it."""
    g = K.Geo()
    py = 1.0
    K.box(g, (-0.45, py - 0.45, 0), (0.45, py + 0.45, 0.3), STONE, 0.42, skip=('-z',))
    K.box(g, (-0.13, py - 0.13, 0.3), (0.13, py + 0.13, 4.0), DWOOD, 0.38, skip=('-z',))
    K.box(g, (-0.1, -1.25, 3.76), (0.1, py + 0.13, 4.0), DWOOD, 0.4)
    K.tube(g, (0, py - 0.13, 2.5), (0, -0.4, 3.74), 0.06, DWOOD, n=4, var=0.36, cap0=False, cap1=False)
    K.tube(g, (0, -1.05, 3.76), (0, -1.05, 2.55), 0.025, ROPE, n=4, var=0.5, cap0=False, cap1=False)
    K.torus(g, 0.15, 0.025, 8, 3, ROPE, var=0.5, smooth=0, m=T(0, -1.05, 2.4) @ Rx(90))
    p = kit.add('vale_gallows', g, budget=100, sheet={'az': 30, 'el': 14})
    p.info['footprint'] = plan_size(g)
    return p


def mushroom_ring(kit):
    """A fairy ring of toadstools 2.5 m across: twelve tawny-capped toadstools on pale stems round a ring, pale
    flecks on the caps, a few grass blades between them."""
    rng = R('vale_mushroom_ring')
    g = K.Geo()
    for i in range(12):
        a = math.radians(i * 30 + jit(rng, 9))
        r = 1.12 + jit(rng, 0.1)
        x, y = math.cos(a) * r, math.sin(a) * r
        h = rng.uniform(0.16, 0.32)
        cr = h * 0.55 + rng.uniform(0.0, 0.04)
        K.tube(g, (x, y, 0), (x + jit(rng, 0.03), y + jit(rng, 0.03), h), 0.03 + h * 0.06, BONE, r1=0.025, n=4, var=0.58,
               cap0=False, cap1=False)
        K.lathe(g, [(0.0, h - 0.05), (cr, h - 0.02), (cr * 0.75, h + 0.05), (0.0, h + 0.1)], 6, ROPE,
                lambda b, k: 0.46 + jit(rng, 0.05), smooth=30, cap0=False, m=T(x, y, 0), phase=rng.uniform(0, 1))
        tilt = math.degrees(math.atan2(0.12, cr))
        for k in range(2):
            sa = rng.uniform(0, 2 * math.pi)
            sr = cr * rng.uniform(0.25, 0.55)
            zs = h + 0.1 - 0.12 * (sr / cr) + 0.005
            K.disc(g, cr * 0.16, 3, BONE, var=0.72, m=T(x + math.cos(sa) * sr, y + math.sin(sa) * sr, zs) @ Rz(math.degrees(sa)) @ Ry(tilt))
    for i in range(10):
        a = math.radians(i * 36 + 15 + jit(rng, 10))
        r = 1.1 + jit(rng, 0.25)
        c = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        side = Vector((-math.sin(a), math.cos(a), 0)) * 0.03
        g.pf([tuple(c - side), tuple(c + side), tuple(c + Vector((jit(rng, 0.06), jit(rng, 0.06), rng.uniform(0.18, 0.3))))], MOSS,
             0.5 + jit(rng, 0.12), smooth=0)
    p = kit.add('vale_mushroom_ring', g, budget=420, sheet={'az': 30, 'el': 28})
    p.info['footprint'] = plan_size(g)
    p.info['node'] = True
    p.info['no_collider'] = True
    p.info['doubleSided'] = True
    return p



def build_vale(kit):
    pine(kit)
    oak(kit)
    rock_small(kit)
    rock_big(kit)
    grass_tuft(kit)
    reeds(kit)
    house_small(kit)
    house_long(kit)
    barn(kit)
    smithy(kit)
    well(kit)
    shrine(kit)
    stall(kit)
    fence(kit)
    bridge(kit)
    campfire(kit)
    hay_bale(kit)
    scarecrow(kit)
    signpost(kit)
    # Phase W5: the gathering
    ore_rock(kit, 'vale_rock_copper', BRASS, 0.55)
    ore_rock(kit, 'vale_rock_tin', BMETAL, 0.5)
    ore_rock(kit, 'vale_rock_iron', IRON, 0.4)
    ore_rock(kit, 'vale_rock_coal', INK, 0.5)
    rock_empty(kit)
    stump(kit)
    fishing_spot(kit)
    snare_spot(kit)
    berry_bush(kit)
    mushrooms(kit)
    herb_patch(kit)
    # Phase W6–W7: the stations
    furnace(kit)
    anvil(kit)
    altar(kit)
    ore_rock(kit, 'vale_rock_essence', GLOW, 0.6)
    # Phase W8: the town
    bank(kit)
    general_store(kit)
    inn(kit)
    chapel(kit)
    skill_hall(kit)
    house_tall(kit)
    guardhouse(kit)
    palisade(kit)
    wall_tower(kit)
    gate_arch(kit)
    fountain(kit)
    lamppost(kit)
    barrel(kit)
    crate(kit)
    hen_coop(kit)
    minecart(kit)
    mine_frame(kit)
    bush(kit)
    loot_sack(kit)
    loot_bones(kit)
    loot_coins(kit)
    # Phase W8: shops and workshops
    workshop(kit, 'vale_workshop')
    workshop(kit, 'vale_workshop_slate', stone=True, budget=280)
    workbench(kit)
    tanning_rack(kit)
    spinning_wheel(kit)
    fletching_bench(kit)
    alchemy_table(kit)
    cooking_range(kit)
    shop_arms(kit)
    shop_bows(kit)
    shop_runes(kit)
    shop_larder(kit)
    shop_apothecary(kit)
    # Phase W8: the medieval town
    wall_stone(kit)
    wall_tower_stone(kit)
    gate_tower(kit)
    gate_arch_stone(kit)
    keep(kit)
    church(kit)
    guildhall(kit)
    library(kit)
    stables(kit)
    watermill(kit)
    tannery(kit)
    market_hall(kit)
    market_cross(kit)
    stocks(kit)
    low_wall(kit)
    gravestone(kit)
    garden_plot(kit)
    cart(kit)
    arena_stand(kit)
    arena_arch(kit)
    arena_beast_gate(kit)
    # Phase W10: the wilds, levels 5 to 20
    tent(kit)
    tent_large(kit)
    toll_ruin(kit)
    ruin_wall_piece(kit)
    drowned_chapel(kit)
    cave_mouth(kit)
    keep_gate(kit)
    wyvern_nest(kit)
    rock_steel(kit)
    ash(kit)
    willow(kit)
    dead_tree(kit)
    bones(kit)
    # The town review (2026-11-04): house twins and roof variants, the shop-houses, the workshops' signs, the kerb and
    # the cobbles, the quarry's faces, the arena's crowd and banners, the doorstep clutter
    house_small(kit, 'vale_house_small_m', mirror=True)
    house_small(kit, 'vale_house_small_b', roof=IRON, roof_var=0.46)
    house_tall(kit, 'vale_house_tall_m', mirror=True)
    house_tall(kit, 'vale_house_tall_b', roof=DWOOD, roof_var=0.44)
    shophouse(kit)
    shophouse(kit, 'vale_shophouse_m', mirror=True)
    hanging_sign(kit, 'vale_sign_bow', sym_bow)
    hanging_sign(kit, 'vale_sign_flask', sym_flask)
    hanging_sign(kit, 'vale_sign_needle', sym_needle)
    hanging_sign(kit, 'vale_sign_loaf', sym_loaf)
    kerb(kit)
    cobbles(kit)
    quarry_face(kit)
    quarry_face_corner(kit)
    arena_crowd(kit)
    arena_banner(kit)
    bench(kit)
    basket(kit)
    sacks(kit)
    firewood_stack(kit)
    water_trough(kit)
    dog(kit)
    cart_hand(kit)
    # install 2 (the living Vale): the yews, the sawmill and the woodcutter's hut, the glade's dressing, the wagon,
    # the gallows, the fairy ring
    yew(kit)
    yew_old(kit)
    sawmill(kit)
    woodcutter_hut(kit)
    lumber_pile(kit)
    fallen_trunk(kit)
    glade_stone(kit)
    bird_nest(kit)
    hunters_hide(kit)
    wagon(kit)
    gallows(kit)
    mushroom_ring(kit)
    vale_land_pieces.build(kit)   # W17-land (OW-62)
    vale_town_pieces.build(kit, globals())  # W18-town: the woods' and the town's new pieces
    vale_make_pieces.build(kit, globals())  # W20-make: the gold rock and the sand heap (OW-69)
    vale_agility_pieces.build(kit)  # W21-agility (OW-72)


# ---------------------------------------------------------------------------------------------------- review
class Review:
    def __init__(self):
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'lib'))
        from render import Stage
        self.stage = Stage(OUT, size=400, quick=QUICK, platform=False)
        self.sc = bpy.context.scene
        self.cam = self.stage.cam
        self.labels = K.Labels(OUT)
        gm = bpy.data.meshes.new('GV_SheetGround')
        gm.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
        mat = bpy.data.materials.new('GV_SheetGroundMat')
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs[0].default_value = (0.09, 0.12, 0.06, 1)
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], out.inputs[0])
        gm.materials.append(mat)
        self.ground = bpy.data.objects.new('GV_SheetGround', gm)
        self.stage.col.objects.link(self.ground)

    def sheet(self, pieces, name, cols, cell):
        os.makedirs(OUT, exist_ok=True)
        sc = self.sc
        everything = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('GV_')]
        cells, labels = [], []
        for p in pieces:
            for o in everything:
                o.hide_render = True
            for o in p.meshes():
                o.hide_render = False
            sp = p.sheet
            lo, hi = K.frame_ortho(self.cam, p.meshes(), az=sp.get('az', 35), el=sp.get('el', 28), margin=1.1)
            self.ground.hide_render = False
            self.ground.location = (0, 0, sp.get('ground', min(0.0, lo.z)) - 0.002)
            sc.render.resolution_x = sc.render.resolution_y = cell
            path = os.path.join(OUT, '_cell.png')
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            cells.append(K.load_px(path))
            os.remove(path)
            budget = '—' if p.budget is None else str(p.budget)
            labels.append(self.labels.image('%s\n%d tris  (budget %s)' % (p.id, p.tris(), budget), cell, 46))
        self.ground.hide_render = True
        for o in everything:
            o.hide_render = False
        out = K.compose(cells, labels, cols, os.path.join(OUT, name))
        log('sheet', os.path.relpath(out, REPO))
        return out

    def closeup(self, p, cell=560):
        """One piece from four sides (front, front-left, left side, back-right) → closeup_<id>.png."""
        sc = self.sc
        everything = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('GV_')]
        cells, labels = [], []
        for az, el, what in ((0, 8, 'front (-Y)'), (35, 24, 'front-left'), (90, 10, 'left side (-X)'),
                             (210, 26, 'back-right')):
            for o in everything:
                o.hide_render = True
            for o in p.meshes():
                o.hide_render = False
            lo, hi = K.frame_ortho(self.cam, p.meshes(), az=az, el=el, margin=1.08)
            self.ground.hide_render = False
            self.ground.location = (0, 0, p.sheet.get('ground', min(0.0, lo.z)) - 0.002)
            sc.render.resolution_x = sc.render.resolution_y = cell
            path = os.path.join(OUT, '_cell.png')
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            cells.append(K.load_px(path))
            os.remove(path)
            labels.append(self.labels.image('%s — %s' % (p.id, what), cell, 40))
        self.ground.hide_render = True
        for o in everything:
            o.hide_render = False
        out = K.compose(cells, labels, 2, os.path.join(OUT, 'closeup_%s.png' % p.id))
        log('closeup', os.path.relpath(out, REPO))
        return out


def has_panes(p):
    """True when a piece carries window panes (gv.A < 0.5 on some vertex)."""
    for o in p.meshes():
        at = o.data.color_attributes.get('gv')
        if at is not None and any(d.color[3] < 0.5 for d in at.data):
            return True
    return False


def report(kit):
    lines = ['| piece | tris | budget | role | lights / fx |', '|---|---:|---:|---|---|']
    for p in kit.pieces.values():
        pts = ', '.join('%s (%s)' % (e.name, e.get('light', e.get('fx'))) for e in p.points)
        over = ' OVER' if p.budget is not None and p.tris() > p.budget else ''
        lines.append('| %s | %d%s | %s | %s | %s |' % (p.id, p.tris(), over, '—' if p.budget is None else p.budget, p.role, pts))
    return lines


def main():
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    K.write_palette('vale', VALE, VALE_ABOUT)
    kit = K.Kit('vale', VALE)
    build_vale(kit)
    log('built %d vale pieces in %.1f s' % (len(kit.pieces), time.time() - t0))
    if not NO_BAKE:
        K.bake_ao(list(kit.pieces.values()), samples=48 if QUICK else 160, lookup=dict(kit.pieces))
        log('baked AO in %.1f s' % (time.time() - t0))
    if not NO_EXPORT:
        os.makedirs(K.ENV_MODELS, exist_ok=True)
        fbx = None if ARGS.get('no_fbx') else K.unity_fbx_path('vale')
        K.export_kit(kit, os.path.join(K.ENV_MODELS, 'kit_vale.glb'), os.path.join(K.ENV_MODELS, 'vale.json'),
                     shell=None, about=VALE_ABOUT + ' Conventions: tools/blender/env/kit_lib.py; build_kit_vale.py.',
                     extra={'outdoor': True}, fbx_path=fbx)
    save_blend(os.path.join(BUILD, 'kit_vale.blend'))
    for line in report(kit):
        print(line)
    if NO_RENDERS:
        return
    mat = K.env_material(VALE, 'GV_Env_vale')
    rv = Review()
    K.apply_look(kit.objects(), mat, outline=0.008)
    only = [s for s in str(ARGS.get('only') or '').split(',') if s in kit.pieces]
    if only:
        rv.sheet([kit.pieces[s] for s in only], 'kit_sheet_only.png', min(6, len(only)), 300 if QUICK else 400)
    else:
        rv.sheet(list(kit.pieces.values()), 'kit_sheet.png', 6, 300 if QUICK else 400)
    for s in str(ARGS.get('closeups') or '').split(','):
        if s in kit.pieces:
            rv.closeup(kit.pieces[s])
    if not ARGS.get('no_night'):
        lit = [p for p in kit.pieces.values() if has_panes(p)]
        log('pieces with window panes: %s' % ', '.join(p.id for p in lit))
        night = K.env_material(VALE, 'GV_Env_vale_night', night=True)
        for p in lit:
            for o in p.meshes():
                o.data.materials[0] = night
        rv.sheet(lit, 'kit_night.png', 6, 300 if QUICK else 400)
        for p in lit:
            for o in p.meshes():
                o.data.materials[0] = mat
    log('done in %.1f s' % (time.time() - t0))


main()
