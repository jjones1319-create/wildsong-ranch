"""kit_lib.py — the shared toolkit of the room-kit builds (Phase 6; tools/blender/README.md → "Phase 6 → Environments").

Every zone kit (`tools/blender/env/build_kit_<zone>.py`) models its pieces with these helpers, so the kits agree on
units, pivots, palette codes, ambient-occlusion baking, export and review renders. Zone shapes live in the zone build;
this file stays general and its signatures stable (add arguments with defaults, never change what one means). Written by
the shared + Cellars pass; `build_kit_cellars.py` is the worked example of every helper.

UNITS AND PIVOTS (07 §2.2 owns the grid)
  Metres. Blender: Z up; the exports are +Y up. Game space (templates, client): +x east, +z south, y up.
      game (x, y, z) = Blender (x, z, −y)                  Blender (x, y, z) = game (x, −z, y)
  A template's rotationY θ (degrees, three.js about +y) is Blender rotation_euler.z = radians(θ) — the same turn.
  A piece's FRONT faces Blender −Y (= game +z, the way rotationY 0 faces into the room; the same as the heroes).
  Grid: cell 8 × 8 m, floor tile 2 × 2 m, wall segment 2 m long × WALL_H 3.5 m. Walls stand OUTSIDE the room's edge
  (WALL_T 0.4 m thick, client layout.ts), so the floor is exactly the footprint.
  * floor tile     origin at its centre; its top at z 0 … ~0.05 (stones stand a few cm proud of the joints).
  * wall segment   origin = the centre of its base ON THE ROOM-SIDE FACE; masonry over x −1…+1, back to y +WALL_T.
  * doorway        a DOOR_W 2 m opening at a cell edge's middle. A doorway piece is DOOR_PIECE_W 4 m wide (the opening
                   + 1 m of wall each side) and replaces the two 2 m segments in the middle of a cell edge, so an 8 m
                   edge is  segment · doorway · segment  (2 + 4 + 2 m) and a closed edge four segments. The opening is
                   the same in every zone so the shared lit-door marker fits: straight jambs to DOOR_SPRING 2.1 m, a
                   round arch to DOOR_APEX 3.1 m (`opening_outline`). Origin: the opening's centre on the room face.
  * corner post    origin at the room's inside corner on the floor; the room lies in the piece's local +x / −y
                   quadrant (Blender; = game +x / +z), i.e. as placed at the NW corner with rotationY 0 — NE −90°,
                   SE 180°, SW 90° (`CORNERS`). It fills the square where the two walls' backs meet.
  * cut-away       walls whose OUTER side faces the template camera are cut down to CUT_H 0.55 m by the client
                   (layout.ts CUTAWAY_HEIGHT); each zone builds cut versions of its wall, doorway and corner (same
                   footprints; their outer faces and the cut top dressed — the camera sees the outside of those walls).
                   A full-height segment needs END faces: next to a cut corner on the camera's side its end shows.
  * free props     origin on the floor under their centre; long things (tables, carts, casks, shelves) run along their
                   local x, their front toward Blender −Y.
  * wall-hung      origin where the templates place them, HANG_OFF 0.1 m in front of the wall face (a 1×1 room puts
                   sconces at ±3.9), reaching back 0.1 m (to Blender y +0.1) to touch the wall.
  * moving parts   a second object `<meshId>.<part>` (chest `lid`, door `leaf`, portcullis `gate`, secret-door `panel`,
                   cage `prisoner`) parented to the piece, its origin at the hinge / pivot; custom properties
                   kind 'part', part, piece, axis. NB three.js strips '.' from node names (`shr_chest_small.lid` loads
                   as `shr_chest_smalllid`): find parts by userData.part / userData.piece.
  * points         empties `light_<n>` (a flame or lamp the client lights; userData.light = torch | fire | brazier |
                   lamp | candle) and `fx_<n>` (an effect the client draws; userData.fx = glow | drip | motes | smoke |
                   embers), parented to the piece. n is unique across one Blender session (object names are global),
                   so match the prefix, not a number.

COLOUR — the `gv` attribute (FLOAT_COLOR, point domain → glTF COLOR_0, linear, 16-bit normalised)
      R = palette slot / 15     G = variation (0.5 neutral; lower = grimier / darker, higher = worn / lighter)
      B = baked ambient occlusion (1 open … 0 enclosed)
      A = 1, or 0 on a WINDOW PANE (`glaze`): the lit-window mask — a day–night shader glows A < 0.5 warm at night
          (slot 15 water aside: the Vault's own build writes its opacity there). Doors, dark openings, slits and ink
          trim keep A = 1. `realize` writes it per face, `bake_ao` keeps it.
          A = TRIM_A 0.95 on TRIM (`trim`): a door leaf or a shutter the game repaints per building (W18-town);
          above 0.5, so it never lights at night.
  Slots (fixed meanings, so shared pieces work in every zone):
      0 stone — the zone's WALL masonry (the Cellars' brick)   1 dark stone / mortar — also floors, paving, loose stones
      2 wood · 3 dark wood · 4 iron · 5 ink (voids, deep joints, pits) · 6 cloth1 (banners) · 7 cloth2 (sacking,
      awnings) · 8 leather / rope / straw · 9 bright metal · 10 brass / gold / trim · 11 glow (fire, embers, runes, lit
      spirals; EMISSIVE) · 12 moss / slime / damp · 13 bone · 14 crystal / gem (EMISSIVE) · 15 water / liquid / glass
  Palettes: tools/blender/palettes/<zone>.json = {"zone", "about", "names": [16], "colours": [16 × "#rrggbb"]}; one
  per zone, owned by that zone's build. SHARED pieces (`shr_`) carry slots only and take the palette of the zone they
  stand in; palettes/shared.json is the neutral palette their own kit sheet renders with.
  The review renders shade exactly as the client is asked to (`env_material`):
      colour = palette[slot] × toonRamp(light) × mix(AO_FLOOR, 1, B) × (1 + VAR_GAIN × (G − 0.5));
      the emissive slots ignore light and AO (× 1.6).
  Ambient occlusion: Cycles AO (distance AO_DIST) baked per piece into a temporary colour attribute and copied into B,
  with stand-ins for the room as occluders: a floor plane, a wall plane behind wall-hung pieces, and copies of the
  tiling neighbours (floor tiles all round, wall segments either side) so the seams match (`Kit.add(..., bake=…)`).

THE API (see each docstring; signatures are stable — the Crypts and Vault builds call them)
  Geo                          vertices + faces, one slot / variation / smoothing angle / pane flag per face;
                               glaze(g, faces) marks window panes (gv.A = 0); trim(g, faces) marks trim (gv.A = 0.95)
  primitives                   quad, poly, box, bevel_box, cbox, hull, rock, lathe, tube (orient), prism, slab_xz,
                               torus, surface, disc, ribbon, chain, bricks, backing, flagstone, inset_poly,
                               opening_outline, rect_hits_opening
  objects                      realize(name, geo) → a mesh object with `gv` and custom normals; mesh_tris(ob)
  Kit / Piece                  Kit(zone, colours).add(meshId, geo, budget, bake, sheet, role) → Piece;
                               kit.part(piece, 'lid', geo, pivot), kit.light(piece, at, kind), kit.fx(piece, at, kind)
  bake_ao(pieces)              Cycles AO into gv.B (each piece's `bake` spec: ground, ground_hole, wall, occluders,
                               fade, skip)
  palettes                     write_palette(zone, colours, about), read_palette(zone)
  look                         env_material(colours, name), apply_look(objects, material, outline), add_outline
  spaces                       game_to_blender, blender_to_game, game_matrix(x, y, z, rotationY), CORNERS,
                               SIDE_NORMAL, SIDE_YAW
  review                       Labels, compose, load_px, save_px, shrink, world_bounds, look_dir, aim, frame_ortho;
                               rooms: camera_dir, faces_camera, nearest_side, room_placements, build_room, clear_room,
                               template_camera
  export                       export_kit(kit, glb_path, json_path, shell, about, extra), game_bounds
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), 'lib')
if LIB not in sys.path:
    sys.path.insert(0, LIB)
from common import CONTENT, MODELS, REPO, TOOLS, hexcol, log, read_json, write_json  # noqa: E402
import toon  # noqa: E402

# ---------------------------------------------------------------------------------------------------- constants
CELL = 8.0
TILE = 2.0
SEG = 2.0
WALL_H = 3.5
WALL_T = 0.4
CUT_H = 0.55
DOOR_W = 2.0
DOOR_SPRING = 2.1
DOOR_APEX = 3.1
DOOR_PIECE_W = 4.0
HANG_OFF = 0.1

(STONE, DSTONE, WOOD, DWOOD, IRON, INK, CLOTH1, CLOTH2, ROPE, BMETAL, BRASS, GLOW, MOSS, BONE, GEM, WATER) = range(16)
SLOT_NAMES = ['stone', 'darkStone', 'wood', 'darkWood', 'iron', 'ink', 'cloth1', 'cloth2', 'rope', 'brightMetal',
              'brass', 'glow', 'moss', 'bone', 'gem', 'water']
EMISSIVE = (GLOW, GEM)

AO_DIST = 0.8          # metres: creases, joints and contact shadows; a room's large-scale shading is the torches' job
AO_FLOOR = 0.45        # the darkest an occluded vertex gets (mix(AO_FLOOR, 1, B))
VAR_GAIN = 0.36        # G 0 → ×0.82, G 1 → ×1.18
TRIM_A = 0.95          # gv.A on trim faces (`trim`: door leaves, shutters the game repaints; W18-town)

PALETTES = os.path.join(TOOLS, 'palettes')
ENV_MODELS = os.path.join(MODELS, 'env')
TEMPLATES = os.path.join(CONTENT, 'dungeons')

# the room's corners: (game x sign, game z sign, rotationY of the corner piece, the two sides that meet there)
CORNERS = (
    (-1, -1, 0.0, ('north', 'west')),
    (1, -1, -90.0, ('north', 'east')),
    (1, 1, 180.0, ('south', 'east')),
    (-1, 1, 90.0, ('south', 'west')),
)
SIDE_NORMAL = {'north': (0.0, -1.0), 'east': (1.0, 0.0), 'south': (0.0, 1.0), 'west': (-1.0, 0.0)}   # game (x, z), outward
SIDE_YAW = {'north': 0.0, 'east': -90.0, 'south': 180.0, 'west': 90.0}   # a wall piece's rotationY on that side


def _val(x, *a):
    return x(*a) if callable(x) else x


def game_to_blender(p):
    return Vector((p[0], -p[2], p[1]))


def blender_to_game(p):
    return [round(p[0], 4) + 0.0, round(p[2], 4) + 0.0, round(-p[1], 4) + 0.0]


def game_matrix(x, y, z, yaw_deg=0.0):
    """The Blender world matrix of a piece placed at game (x, y, z) with a template rotationY (degrees)."""
    return Matrix.Translation(game_to_blender((x, y, z))) @ Matrix.Rotation(math.radians(yaw_deg), 4, 'Z')


# ---------------------------------------------------------------------------------------------------- geometry
class Geo:
    """Vertices and faces with one palette slot, one variation value (G), one smoothing angle (degrees) and one pane
    flag (`P`: True = a window pane, gv.A = 0, see `glaze`; 'trim' = trim, gv.A = TRIM_A, see `trim`) per face. Faces
    wind counter-clockwise seen from outside. `mark()` → (vertex, face) counts, used to transform or repaint what was
    added after it."""

    def __init__(self):
        self.V = []
        self.F = []
        self.S = []
        self.G = []
        self.A = []
        self.P = []

    def v(self, p):
        self.V.append(Vector((float(p[0]), float(p[1]), float(p[2]))))
        return len(self.V) - 1

    def f(self, idx, slot, var=None, smooth=0.0):
        idx = tuple(int(i) for i in idx)
        if len(set(idx)) < 3:
            return -1
        self.F.append(idx)
        self.S.append(int(slot))
        self.G.append(0.5 if var is None else min(1.0, max(0.0, float(var))))
        self.A.append(float(smooth))
        self.P.append(False)
        return len(self.F) - 1

    def pf(self, pts, slot, var=None, smooth=0.0):
        """A face through new vertices at `pts`."""
        return self.f([self.v(p) for p in pts], slot, var, smooth)

    def mark(self):
        return (len(self.V), len(self.F))

    def transform(self, m, mark=(0, 0)):
        m = Matrix(m)
        if len(m) == 3:
            m = m.to_4x4()
        for i in range(mark[0], len(self.V)):
            self.V[i] = m @ self.V[i]
        if m.to_3x3().determinant() < 0:
            for k in range(mark[1], len(self.F)):
                self.F[k] = tuple(reversed(self.F[k]))
        return self

    def paint(self, mark, slot=None, var=None):
        for k in range(mark[1], len(self.F)):
            if slot is not None:
                self.S[k] = int(slot)
            if var is not None:
                self.G[k] = float(var)

    def extend(self, other, m=None):
        mk = self.mark()
        off = len(self.V)
        self.V += [v.copy() for v in other.V]
        self.F += [tuple(i + off for i in f) for f in other.F]
        self.S += list(other.S)
        self.G += list(other.G)
        self.A += list(other.A)
        self.P += list(getattr(other, 'P', ())) + [False] * (len(other.F) - len(getattr(other, 'P', ())))
        if m is not None:
            self.transform(m, mk)
        return mk

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def bounds(self):
        lo = Vector((min(v.x for v in self.V), min(v.y for v in self.V), min(v.z for v in self.V)))
        hi = Vector((max(v.x for v in self.V), max(v.y for v in self.V), max(v.z for v in self.V)))
        return lo, hi


def glaze(g, faces=None, since=None, pane=True):
    """Marks faces as WINDOW PANES (gv.A = 0: the faces a day–night shader lights warm at night): `faces` a face index
    (what `Geo.f` / `Geo.pf` return) or a list of them, and/or `since` a `mark()` (every face added after it)."""
    idx = []
    if isinstance(faces, int):
        idx.append(faces)
    elif faces is not None:
        idx += list(faces)
    if since is not None:
        idx += list(range(since[1], len(g.F)))
    if len(g.P) < len(g.F):
        g.P += [False] * (len(g.F) - len(g.P))
    for k in idx:
        if k is not None and 0 <= k < len(g.F):
            g.P[k] = bool(pane)


def trim(g, faces=None, since=None):
    """Marks faces as TRIM (gv.A = TRIM_A 0.95: a door leaf or a shutter the game repaints per building; W18-town),
    `faces` and `since` as in `glaze`."""
    idx = []
    if isinstance(faces, int):
        idx.append(faces)
    elif faces is not None:
        idx += list(faces)
    if since is not None:
        idx += list(range(since[1], len(g.F)))
    if len(g.P) < len(g.F):
        g.P += [False] * (len(g.F) - len(g.P))
    for k in idx:
        if k is not None and 0 <= k < len(g.F):
            g.P[k] = 'trim'


def quad(g, a, b, c, d, slot, var=None, smooth=0.0):
    return g.pf((a, b, c, d), slot, var, smooth)


def poly(g, pts, slot, var=None, smooth=0.0):
    return g.pf(pts, slot, var, smooth)


def box(g, lo, hi, slot, var=None, smooth=0.0, skip=(), slots=None, m=None):
    """An axis-aligned box. `skip` names sides left out ('-x', '+x', '-y', '+y', '-z', '+z'); `slots` overrides a
    side's slot ({'+z': IRON}); `var` may be a callable(side) → G."""
    mk = g.mark()
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    p = [g.v(c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                          (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    sides = {'+z': (4, 5, 6, 7), '-z': (0, 3, 2, 1), '-y': (0, 1, 5, 4), '+y': (2, 3, 7, 6),
             '-x': (3, 0, 4, 7), '+x': (1, 2, 6, 5)}
    for k, idx in sides.items():
        if k in skip:
            continue
        s = (slots or {}).get(k, slot)
        g.f([p[i] for i in idx], s, _val(var, k), smooth)
    if m is not None:
        g.transform(m, mk)
    return mk


def hull(g, pts, slot, var=None, smooth=0.0, m=None, planar=2.0):
    """The convex hull of `pts`, coplanar triangles merged. `slot` / `var` may be callables (centre, normal) → value."""
    mk = g.mark()
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(p)) for p in pts]
    out = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    kill = list({e for e in out['geom_interior'] + out['geom_unused'] if isinstance(e, bmesh.types.BMVert)})
    if kill:
        bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(planar), use_dissolve_boundaries=False,
                             verts=list(bm.verts), edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    idx = {}
    for v in bm.verts:
        idx[v] = g.v(v.co)
    for f in bm.faces:
        c = f.calc_center_median()
        n = f.normal.copy()
        g.f([idx[v] for v in f.verts], _val(slot, c, n), _val(var, c, n), smooth)
    bm.free()
    if m is not None:
        g.transform(m, mk)
    return mk


def cbox(g, lo, hi, c, slot, var=None, smooth=0.0, m=None):
    """A box with every edge chamfered by `c` (44 triangles)."""
    pts = []
    for sx in (0, 1):
        for sy in (0, 1):
            for sz in (0, 1):
                x = hi[0] if sx else lo[0]
                y = hi[1] if sy else lo[1]
                z = hi[2] if sz else lo[2]
                dx = -c if sx else c
                dy = -c if sy else c
                dz = -c if sz else c
                pts += [(x, y + dy, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z)]
    return hull(g, pts, slot, var, smooth, m)


def bevel_box(g, lo, hi, c, slot, var=None, smooth=0.0, m=None, top_slot=None):
    """A box whose top edges are chamfered by `c`, its bottom left open (it stands on something): 18 triangles.
    `var` may be a callable('side' | 'bevel' | 'top') → G."""
    mk = g.mark()
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    b = [g.v(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0))]
    mid = [g.v(p) for p in ((x0, y0, z1 - c), (x1, y0, z1 - c), (x1, y1, z1 - c), (x0, y1, z1 - c))]
    t = [g.v(p) for p in ((x0 + c, y0 + c, z1), (x1 - c, y0 + c, z1), (x1 - c, y1 - c, z1), (x0 + c, y1 - c, z1))]
    ts = slot if top_slot is None else top_slot
    for k in range(4):
        k2 = (k + 1) % 4
        g.f((b[k], b[k2], mid[k2], mid[k]), slot, _val(var, 'side'), smooth)
        g.f((mid[k], mid[k2], t[k2], t[k]), ts, _val(var, 'bevel'), smooth)
    g.f(t, ts, _val(var, 'top'), smooth)
    if m is not None:
        g.transform(m, mk)
    return mk


def rock(g, rng, centre, size, slot, n=9, var=None, flat=True, m=None, smooth=0.0):
    """A chunky low-poly stone: the hull of `n` jittered points on an ellipsoid of half-sizes `size`; with `flat` its
    underside is cut level (it sits on the floor)."""
    cx, cy, cz = centre
    sx, sy, sz = size
    pts = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1 - y * y))
        a = golden * i + rng.uniform(0, 0.6)
        k = rng.uniform(0.78, 1.08)
        p = Vector((math.cos(a) * r * k, math.sin(a) * r * k, y * k))
        pts.append((cx + p.x * sx, cy + p.y * sy, cz + p.z * sz))
    if flat:
        pts = [(x, y, max(z, cz - sz * 0.55)) for x, y, z in pts]
    return hull(g, pts, slot, var, smooth, m)


def lathe(g, prof, n, slot, var=None, smooth=40.0, cap0=True, cap1=True, phase=0.0, m=None, scale=(1.0, 1.0),
          cap_slot=None):
    """A surface of revolution about +Z: `prof` = [(radius, z), …] bottom to top (radius 0 = a pole). `slot` / `var`
    may be callables (band index, segment index) → value; caps take `cap_slot` (default: the nearest band's)."""
    mk = g.mark()
    rings = []
    for r, z in prof:
        if r <= 1e-6:
            rings.append([g.v((0.0, 0.0, z))])
        else:
            rings.append([g.v((r * math.cos(phase + 2 * math.pi * k / n) * scale[0],
                               r * math.sin(phase + 2 * math.pi * k / n) * scale[1], z)) for k in range(n)])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(n):
            k2 = (k + 1) % n
            s = _val(slot, i, k)
            vv = _val(var, i, k)
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                g.f((a[0], b[k2], b[k]), s, vv, smooth)
            elif len(b) == 1:
                g.f((a[k], a[k2], b[0]), s, vv, smooth)
            else:
                g.f((a[k], a[k2], b[k2], b[k]), s, vv, smooth)
    if cap0 and len(rings[0]) > 2:
        g.f(tuple(reversed(rings[0])), cap_slot if cap_slot is not None else _val(slot, 0, 0), _val(var, -1, 0), 0.0)
    if cap1 and len(rings[-1]) > 2:
        g.f(tuple(rings[-1]), cap_slot if cap_slot is not None else _val(slot, len(rings) - 2, 0), _val(var, -2, 0), 0.0)
    if m is not None:
        g.transform(m, mk)
    return mk


def orient(p0, p1):
    """(matrix taking +Z to the direction p0 → p1 with its origin at p0, length)."""
    d = Vector(p1) - Vector(p0)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized()) if d.length > 1e-9 else Matrix.Identity(3).to_quaternion()
    return Matrix.Translation(Vector(p0)) @ q.to_matrix().to_4x4(), d.length


def tube(g, p0, p1, r0, slot, r1=None, n=6, var=None, smooth=50.0, cap0=True, cap1=True, phase=None):
    """A cylinder (or frustum) from p0 to p1."""
    mt, ln = orient(p0, p1)
    return lathe(g, [(r0, 0.0), (r0 if r1 is None else r1, ln)], n, slot, var, smooth, cap0, cap1,
                 phase=(math.pi / n if phase is None else phase), m=mt)


def prism(g, pts2, z0, z1, slot, var=None, smooth=0.0, cap0=True, cap1=True, m=None, cap_slot=None, side_slot=None):
    """A polygon (counter-clockwise seen from +Z, in XY) extruded from z0 to z1."""
    mk = g.mark()
    b = [g.v((p[0], p[1], z0)) for p in pts2]
    t = [g.v((p[0], p[1], z1)) for p in pts2]
    n = len(pts2)
    for k in range(n):
        k2 = (k + 1) % n
        g.f((b[k], b[k2], t[k2], t[k]), side_slot if side_slot is not None else slot, _val(var, k), smooth)
    if cap1:
        g.f(t, cap_slot if cap_slot is not None else slot, _val(var, 'top'), 0.0)
    if cap0:
        g.f(tuple(reversed(b)), cap_slot if cap_slot is not None else slot, _val(var, 'bottom'), 0.0)
    if m is not None:
        g.transform(m, mk)
    return mk


def slab_xz(g, pts2, y0, y1, slot, var=None, smooth=0.0, front=True, back=True, m=None, edge_slot=None,
            front_slot=None):
    """A polygon in the XZ plane (counter-clockwise seen from the front, −Y: x right, z up) extruded from y0 (its
    front face) back to y1."""
    mk = g.mark()
    f = [g.v((p[0], y0, p[1])) for p in pts2]
    b = [g.v((p[0], y1, p[1])) for p in pts2]
    n = len(pts2)
    for k in range(n):
        k2 = (k + 1) % n
        g.f((f[k], b[k], b[k2], f[k2]), edge_slot if edge_slot is not None else slot, _val(var, k), smooth)
    if front:
        g.f(f, front_slot if front_slot is not None else slot, _val(var, 'front'), 0.0)
    if back:
        g.f(tuple(reversed(b)), slot, _val(var, 'back'), 0.0)
    if m is not None:
        g.transform(m, mk)
    return mk


def torus(g, R, r, n_major, n_minor, slot, var=None, smooth=60.0, m=None, phase=0.0):
    """A ring about +Z through the origin."""
    mk = g.mark()
    rings = []
    for i in range(n_major):
        a = 2 * math.pi * i / n_major
        c, s = math.cos(a), math.sin(a)
        ring = []
        for j in range(n_minor):
            b = phase + 2 * math.pi * j / n_minor
            rr = R + r * math.cos(b)
            ring.append(g.v((rr * c, rr * s, r * math.sin(b))))
        rings.append(ring)
    for i in range(n_major):
        a, bb = rings[i], rings[(i + 1) % n_major]
        for j in range(n_minor):
            j2 = (j + 1) % n_minor
            g.f((a[j], bb[j], bb[j2], a[j2]), slot, _val(var, i, j), smooth)
    if m is not None:
        g.transform(m, mk)
    return mk


def surface(g, nu, nv, fn, slot, var=None, smooth=30.0, closed_u=False, m=None):
    """A grid of quads through fn(i, j) → point, i in 0..nu, j in 0..nv; a face winds (i, j) → (i+1, j) → (i+1, j+1)
    → (i, j+1), so with u to the right and v up the front faces the viewer. `slot`/`var` take (i, j) callables."""
    mk = g.mark()
    cols = nu if closed_u else nu + 1
    grid = [[g.v(fn(i, j)) for j in range(nv + 1)] for i in range(cols)]
    for i in range(nu):
        i2 = (i + 1) % cols
        for j in range(nv):
            g.f((grid[i][j], grid[i2][j], grid[i2][j + 1], grid[i][j + 1]), _val(slot, i, j), _val(var, i, j), smooth)
    if m is not None:
        g.transform(m, mk)
    return mk


def disc(g, r, n, slot, z=0.0, var=None, m=None, rng=None, jitter=0.0, scale=(1.0, 1.0), phase=0.0):
    """A flat polygon facing +Z (coins, decals, puddles); `jitter` roughens its rim."""
    mk = g.mark()
    pts = []
    for k in range(n):
        a = phase + 2 * math.pi * k / n
        k_r = r * (1 + (rng.uniform(-jitter, jitter) if rng else 0.0))
        pts.append((math.cos(a) * k_r * scale[0], math.sin(a) * k_r * scale[1], z))
    g.pf(pts, slot, var)
    if m is not None:
        g.transform(m, mk)
    return mk


def ribbon(g, path, width, slot, var=None, normal=(0, -1, 0), smooth=30.0, m=None):
    """A flat strip `width` wide along `path` (points), facing `normal`."""
    mk = g.mark()
    nrm = Vector(normal).normalized()
    left, right = [], []
    for i, p in enumerate(path):
        p = Vector(p)
        a = Vector(path[max(0, i - 1)])
        b = Vector(path[min(len(path) - 1, i + 1)])
        t = (b - a).normalized()
        side = t.cross(nrm).normalized() * (width / 2)
        left.append(g.v(p + side))
        right.append(g.v(p - side))
    for i in range(len(path) - 1):
        g.f((left[i], left[i + 1], right[i + 1], right[i]), _val(slot, i), _val(var, i), smooth)
    if m is not None:
        g.transform(m, mk)
    return mk


def chain(g, p0, p1, slot, link=0.11, wire=0.014, var=None, segs=(4, 3)):
    """Iron links from p0 to p1, alternately turned a quarter; segs = (around the link, round the wire): the default
    (4, 3) is a diamond-section link of 24 triangles, enough at room distance."""
    mk = g.mark()
    mt, ln = orient(p0, p1)
    count = max(1, int(round(ln / (link * 0.8))))
    step = ln / count
    for i in range(count):
        c = (i + 0.5) * step
        local = (Matrix.Translation((0, 0, c)) @ Matrix.Rotation(math.pi / 2 if i % 2 else 0.0, 4, 'Z')
                 @ Matrix.Rotation(math.pi / 2, 4, 'X') @ Matrix.Diagonal((0.62, 1.0, 1.0, 1.0)))
        torus(g, link * 0.5, wire, segs[0], segs[1], slot, var, smooth=0.0, m=mt @ local, phase=math.pi / segs[1])
    return mk


def inset_poly(poly, d):
    """A convex counter-clockwise polygon (2D) moved `d` inward along every edge."""
    P = [Vector((p[0], p[1])) for p in poly]
    n = len(P)
    out = []
    for k in range(n):
        a, b, c = P[k - 1], P[k], P[(k + 1) % n]
        e1 = (b - a).normalized()
        e2 = (c - b).normalized()
        n1 = Vector((-e1.y, e1.x))
        n2 = Vector((-e2.y, e2.x))
        p1 = b + n1 * d
        p2 = b + n2 * d
        den = e1.x * e2.y - e1.y * e2.x
        if abs(den) < 1e-9:
            out.append(p1)
            continue
        t = ((p2.x - p1.x) * e2.y - (p2.y - p1.y) * e2.x) / den
        out.append(p1 + e1 * t)
    return [(p.x, p.y) for p in out]


def flagstone(g, poly2, h, slot, var=None, joint=0.035, bevel=0.025, tilt=(0.0, 0.0), z0=0.0, m=None):
    """A paving stone in a joint of width `joint`: its foot is the cell `poly2` (convex, counter-clockwise, XY) inset
    by joint / 2 at z0, its top inset a further `bevel` at z0 + h, tilted as a plane by `tilt` (dz/dx, dz/dy)."""
    mk = g.mark()
    base = inset_poly(poly2, joint / 2)
    top = inset_poly(poly2, joint / 2 + bevel)
    cx = sum(p[0] for p in poly2) / len(poly2)
    cy = sum(p[1] for p in poly2) / len(poly2)
    ib = [g.v((p[0], p[1], z0)) for p in base]
    it = [g.v((p[0], p[1], z0 + h + tilt[0] * (p[0] - cx) + tilt[1] * (p[1] - cy))) for p in top]
    n = len(base)
    for k in range(n):
        k2 = (k + 1) % n
        g.f((ib[k], ib[k2], it[k2], it[k]), slot, var)
    g.f(it, slot, var)
    if m is not None:
        g.transform(m, mk)
    return mk


def bricks(g, rng, x0, x1, z0, z1, slot=STONE, y=0.0, bw=2.0 / 3.0, bh=0.335, joint=0.03, depth=0.025,
           bevel=0.022, base_z=0.0, phase_x=None, var=0.13, grime=0.10, moss=0.0, moss_rows=2, moss_slot=MOSS,
           keep=None, tilt=1.6, jitter=0.004, flush=(True, True), m=None):
    """Running-bond bricks on the plane y, facing −Y, over x0..x1 × z0..z1 (no mortar: add `backing`). Courses are
    counted from `base_z` and bricks from `phase_x` (default x0), so pieces built on the 2 m grid continue each other's
    bond; odd courses are offset half a brick and their end halves stop flush with x0 / x1 (`flush`), so two segments
    side by side join those halves into one brick. Each brick is its front (tilted a little at random) and a top bevel
    back to the mortar plane at y + depth (a course cut by z1 gets no bevel: the cut face covers it).
    `keep(xa, xb, za, zb)` → False drops a brick (its two halves are tried). G: ± `var` per brick, darker by `grime`
    near base_z; `moss` = the chance a brick in the lowest `moss_rows` courses takes `moss_slot`."""
    mk = g.mark()
    px = x0 if phase_x is None else phase_x
    k = int(math.floor((z0 - base_z) / bh + 1e-6))
    ends = {}
    while True:
        za = base_z + k * bh
        zb = za + bh
        if za >= z1 - 1e-6:
            break
        ca, cb = max(za, z0), min(zb, z1)
        if cb - ca < 0.04:
            k += 1
            continue
        off = bw / 2 if k % 2 else 0.0
        start = px - off
        i = math.floor((x0 - start) / bw + 1e-9)
        while True:
            xa = start + i * bw
            xb = xa + bw
            i += 1
            if xa >= x1 - 1e-6:
                break
            ua, ub = max(xa, x0), min(xb, x1)
            if ub - ua < 0.06:
                continue
            cut_l = xa < x0 - 1e-6
            cut_r = xb > x1 + 1e-6
            cand = [(ua, ub, cut_l, cut_r)]
            if keep is not None and not keep(ua, ub, ca, cb):
                mid = (ua + ub) / 2
                cand = [c for c in ((ua, mid, cut_l, False), (mid, ub, False, cut_r)) if keep(c[0], c[1], ca, cb)]
            for (ba, bb, cl, cr) in cand:
                gl = 0.0 if (cl and flush[0]) else joint / 2
                gr = 0.0 if (cr and flush[1]) else joint / 2
                top_cut = cb < zb - 1e-6
                gb = joint / 2 if ca <= za + 1e-6 else 0.0
                bev = 0.0 if top_cut else bevel
                gt = 0.0 if top_cut else joint / 2
                if cl or cr:
                    key = (k, 'end')
                    if key not in ends:
                        ends[key] = rng.uniform(-var, var)
                    dv, tdy, jit = ends[key], 0.0, 0.0
                else:
                    dv = rng.uniform(-var, var)
                    tdy = math.tan(math.radians(rng.uniform(-tilt, tilt))) * (cb - ca) / 2
                    jit = rng.uniform(-jitter, jitter)
                zc = (ca + cb) / 2 - base_z
                gval = 0.5 + dv - grime * max(0.0, 1.0 - zc / 0.9)
                s = slot
                if moss > 0 and k < moss_rows and rng.random() < moss:
                    s = moss_slot
                xl, xr = ba + gl, bb - gr
                vb, vt = ca + gb, cb - gt
                yf = y + jit
                ia = [g.v(p) for p in ((xl, yf + tdy, vb), (xr, yf + tdy, vb), (xr, yf - tdy, vt - bev),
                                       (xl, yf - tdy, vt - bev))]
                g.f(ia, s, gval)
                if bev > 0:
                    q2 = g.v((xr, y + depth, vt))
                    q3 = g.v((xl, y + depth, vt))
                    g.f((ia[3], ia[2], q2, q3), s, min(1.0, gval + 0.06))
        k += 1
    if m is not None:
        g.transform(m, mk)
    return mk


def backing(g, x0, x1, z0, z1, slot=DSTONE, y=0.025, var=0.45, m=None):
    """The mortar plane behind a brick face (facing −Y)."""
    mk = g.mark()
    g.pf(((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)), slot, var)
    if m is not None:
        g.transform(m, mk)
    return mk


def opening_outline(n_arch=9, inset=0.0, half=DOOR_W / 2, spring=DOOR_SPRING, z0=0.0):
    """The doorway opening (XZ, counter-clockwise from the front): straight jambs to `spring`, a round arch over it."""
    r = half - inset
    pts = [(-r, z0), (r, z0), (r, spring)]
    for i in range(1, n_arch):
        a = math.pi * i / n_arch
        pts.append((r * math.cos(a), spring + r * math.sin(a)))
    pts.append((-r, spring))
    return pts


def rect_hits_opening(xa, xb, za, zb, half=DOOR_W / 2, spring=DOOR_SPRING, margin=0.0):
    """True when the rectangle overlaps the doorway opening grown by `margin`."""
    h = half + margin
    if za < spring and xa < h and xb > -h:
        return True
    if zb > spring:
        cx = min(max(0.0, xa), xb)
        cz = min(max(spring, za), zb)
        return math.hypot(cx, cz - spring) < h
    return False


# ---------------------------------------------------------------------------------------------------- objects
def _collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def realize(name, g, collection_name='Kit'):
    """A mesh object from a Geo: hard edges split by each face's smoothing angle, faces of different (slot, G, pane)
    split apart, smooth normals kept as custom normals across those splits, `gv` written with B = 1 (AO comes later)
    and A = 0 on window panes (`glaze`), TRIM_A on trim (`trim`), else 1."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in g.V], [], list(g.F))
    me.update(calc_edges=True)
    if len(me.polygons) != len(g.F):
        raise RuntimeError('%s: %d faces in, %d out (degenerate faces?)' % (name, len(g.F), len(me.polygons)))
    codes = {}
    code_of = []
    panes = list(getattr(g, 'P', ())) + [False] * (len(g.F) - len(getattr(g, 'P', ())))
    for s, v, pn in zip(g.S, g.G, panes):
        key = (s, round(v, 4), 'trim' if pn == 'trim' else bool(pn))
        if key not in codes:
            codes[key] = len(codes)
        code_of.append(codes[key])
    table = {i: k for k, i in codes.items()}
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    lc = bm.faces.layers.int.new('gv_code')
    ls = bm.faces.layers.float.new('gv_smooth')
    for f in bm.faces:
        f[lc] = code_of[f.index]
        f[ls] = g.A[f.index]
    bm.normal_update()
    sharp = []
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2:
            continue
        lim = min(lf[0][ls], lf[1][ls])
        n0, n1 = lf[0].normal, lf[1].normal
        if lim <= 0 or n0.length < 0.5 or n1.length < 0.5 or n0.angle(n1, math.pi) >= math.radians(lim):
            sharp.append(e)
    if sharp:
        bmesh.ops.split_edges(bm, edges=sharp)
    bm.normal_update()
    ln = bm.verts.layers.float_vector.new('gv_n')
    for v in bm.verts:
        v[ln] = v.normal if v.normal.length > 0.5 else Vector((0, 0, 1))
    seams = [e for e in bm.edges if len(e.link_faces) == 2 and e.link_faces[0][lc] != e.link_faces[1][lc]]
    if seams:
        bmesh.ops.split_edges(bm, edges=seams)
    bm.verts.index_update()
    bm.faces.index_update()
    vcode = [0] * len(bm.verts)
    for f in bm.faces:
        for v in f.verts:
            vcode[v.index] = f[lc]
    normals = [v[ln].copy() for v in bm.verts]
    bm.faces.layers.int.remove(lc)
    bm.faces.layers.float.remove(ls)
    bm.verts.layers.float_vector.remove(ln)
    bm.to_mesh(me)
    bm.free()
    me.update()
    for a in [a.name for a in me.attributes if a.name.startswith('gv_')]:
        me.attributes.remove(me.attributes[a])
    at = me.color_attributes.new(toon.ATTR, 'FLOAT_COLOR', 'POINT')
    for i, d in enumerate(at.data):
        s, v, pn = table[vcode[i]]
        d.color = (s / 15.0, v, 1.0, 0.0 if pn is True else (TRIM_A if pn == 'trim' else 1.0))
    me.color_attributes.active_color = at
    try:
        me.color_attributes.render_color_index = me.color_attributes.find(toon.ATTR)
    except Exception:
        pass
    for p in me.polygons:
        p.use_smooth = True
    me.normals_split_custom_set_from_vertices([tuple(n) for n in normals])
    ob = bpy.data.objects.new(name, me)
    _collection(collection_name).objects.link(ob)
    return ob


def mesh_tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


_POINTS = {'light': 0, 'fx': 0}


class Piece:
    """One kit piece: its object, moving parts, light / fx points, triangle budget (07), bake spec and sheet view.
    `info` is merged into the piece's entry in <zone>.json (e.g. a stair's `hole`)."""

    def __init__(self, kit, mesh_id, ob, budget, bake, sheet, role):
        self.kit = kit
        self.id = mesh_id
        self.ob = ob
        self.parts = []
        self.points = []
        self.budget = budget
        self.bake = bake
        self.sheet = sheet or {}
        self.role = role
        self.info = {}

    def meshes(self):
        return [self.ob] + self.parts

    def objects(self):
        return [self.ob] + self.parts + self.points

    def tris(self):
        return sum(mesh_tris(o) for o in self.meshes())


class Kit:
    """The pieces of one zone (or the shared kit), in build order.

    bake spec (a dict; `Kit.add(bake=…)`, default {'ground': 0.0}): ground — the floor plane's z (None: none);
    ground_hole — (x0, y0, x1, y1): a floor plane at z 0 with that hole (a stair pit); wall —
    the y of a wall plane behind the piece (None: none); occluders — [(meshId, (dx, dy, dz)), …] copies of pieces
    (itself included) placed around it while baking (tiling neighbours); fade — f(world co) → a factor multiplied into
    B (the stairs' fade to black); skip — True leaves B at 1.
    roles: 'shell' (floor, wall, doorway, corner and their variants), 'prop', 'wall-hung', 'hanging', 'decal'.
    """

    def __init__(self, zone, colours, collection_name=None):
        self.zone = zone
        self.colours = list(colours)
        self.pieces = {}
        self.col = collection_name or ('Kit_' + zone)

    def add(self, mesh_id, g, budget=None, bake=None, sheet=None, role='prop'):
        if mesh_id in self.pieces:
            raise RuntimeError('duplicate piece ' + mesh_id)
        ob = realize(mesh_id, g, self.col)
        p = Piece(self, mesh_id, ob, budget, bake if bake is not None else {'ground': 0.0}, sheet, role)
        self.pieces[mesh_id] = p
        return p

    def part(self, piece, part, g, pivot, axis='z', note=None):
        """A moving part `<meshId>.<part>`: `g` is modelled in the piece's space; the part's origin sits at `pivot`."""
        pv = Vector(pivot)
        g.transform(Matrix.Translation(-pv))
        ob = realize('%s.%s' % (piece.id, part), g, self.col)
        ob.parent = piece.ob
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = pv
        ob['kind'] = 'part'
        ob['part'] = part
        ob['piece'] = piece.id
        ob['axis'] = axis
        if note:
            ob['note'] = note
        piece.parts.append(ob)
        return ob

    def _point(self, piece, kind, at, sub):
        n = _POINTS[kind]
        _POINTS[kind] += 1
        e = bpy.data.objects.new('%s_%d' % (kind, n), None)
        e.empty_display_type = 'SPHERE' if kind == 'light' else 'PLAIN_AXES'
        e.empty_display_size = 0.08
        _collection(self.col).objects.link(e)
        e.parent = piece.ob
        e.matrix_parent_inverse = Matrix.Identity(4)
        e.location = Vector(at)
        e['kind'] = kind
        e[kind] = sub
        e['piece'] = piece.id
        piece.points.append(e)
        return e

    def light(self, piece, at, kind='torch'):
        return self._point(piece, 'light', at, kind)

    def fx(self, piece, at, kind='glow'):
        return self._point(piece, 'fx', at, kind)

    def objects(self):
        out = []
        for p in self.pieces.values():
            out += p.objects()
        return out


# ---------------------------------------------------------------------------------------------------- AO bake
def _plane(name, corners):
    me = bpy.data.meshes.new(name)
    me.from_pydata(corners, [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bake_ao(pieces, samples=128, distance=AO_DIST, lookup=None):
    """Bakes Cycles AO into gv.B for every piece (and its parts) following its bake spec. `lookup` maps meshIds to
    Pieces for occluder copies (default: the pieces given)."""
    sc = bpy.context.scene
    lookup = lookup or {p.id: p for p in pieces}
    prev_engine = sc.render.engine
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    try:
        sc.cycles.use_denoising = False
    except Exception:
        pass
    if sc.world is None:
        sc.world = bpy.data.worlds.new('GV_BakeWorld')
    sc.world.light_settings.distance = distance
    hidden = {o.name: o.hide_render for o in bpy.data.objects}
    for p in pieces:
        spec = p.bake or {}
        if spec.get('skip'):
            continue
        for o in bpy.data.objects:
            o.hide_render = True
        temps = []
        if spec.get('ground') is not None:
            z = spec['ground'] - 0.004
            temps.append(_plane('_bake_ground', [(-30, -30, z), (30, -30, z), (30, 30, z), (-30, 30, z)]))
        if spec.get('ground_hole') is not None:
            x0, y0, x1, y1 = spec['ground_hole']
            z = -0.004
            for c in (((-30, -30), (30, -30), (30, y0), (-30, y0)), ((-30, y1), (30, y1), (30, 30), (-30, 30)),
                      ((-30, y0), (x0, y0), (x0, y1), (-30, y1)), ((x1, y0), (30, y0), (30, y1), (x1, y1))):
                temps.append(_plane('_bake_ground', [(x, y, z) for x, y in c]))
        if spec.get('wall') is not None:
            y = spec['wall'] + 0.002
            temps.append(_plane('_bake_wall', [(-30, y, -5), (-30, y, 30), (30, y, 30), (30, y, -5)]))
        for mid, off in spec.get('occluders', ()):
            src = lookup.get(mid)
            if src is None:
                continue
            for so in src.meshes():
                o = bpy.data.objects.new('_bake_occ', so.data)
                bpy.context.scene.collection.objects.link(o)
                o.matrix_world = Matrix.Translation(Vector(off)) @ so.matrix_world
                temps.append(o)
        for o in temps:
            o.hide_render = False
        targets = p.meshes()
        for o in targets:
            o.hide_render = False
            me = o.data
            at = me.color_attributes.get('ao_tmp') or me.color_attributes.new('ao_tmp', 'FLOAT_COLOR', 'POINT')
            me.color_attributes.active_color = at
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in targets:
            o.select_set(True)
        bpy.context.view_layer.objects.active = targets[0]
        bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
        fade = spec.get('fade')
        for o in targets:
            me = o.data
            ao = me.color_attributes['ao_tmp']
            gv = me.color_attributes[toon.ATTR]
            mw = o.matrix_world
            vals = [d.color[0] for d in ao.data]
            for i, d in enumerate(gv.data):
                a = vals[i]
                if fade is not None:
                    a *= fade(mw @ me.vertices[i].co)
                c = d.color
                d.color = (c[0], c[1], max(0.0, min(1.0, a)), c[3])        # A (the pane mask) kept
            me.color_attributes.remove(ao)
            me.color_attributes.active_color = me.color_attributes[toon.ATTR]
        for o in temps:
            me = o.data if o.type == 'MESH' else None
            bpy.data.objects.remove(o, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    for o in bpy.data.objects:
        if o.name in hidden:
            o.hide_render = hidden[o.name]
    sc.render.engine = prev_engine


# ---------------------------------------------------------------------------------------------------- palettes
def write_palette(zone, colours, about=''):
    if len(colours) != 16:
        raise RuntimeError('a palette has 16 colours')
    write_json(os.path.join(PALETTES, zone + '.json'),
               {'zone': zone, 'about': about, 'names': SLOT_NAMES, 'colours': [c.lower() for c in colours]})


def read_palette(zone):
    return read_json(os.path.join(PALETTES, zone + '.json'))['colours']


# ---------------------------------------------------------------------------------------------------- the look
def env_material(colours, name, night=False):
    """The review material: palette colour (gv.R) × the light-driven 4-step toon ramp (toon.RAMP) × AO (gv.B) ×
    variation (gv.G); slots 11 and 14 emissive. Eevee only (Shader to RGB). `night`: the lit-window check — every
    face dimmed to a blue night except the window panes (gv.A < 0.5), which glow warm."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    attr = nt.nodes.new('ShaderNodeAttribute')
    attr.attribute_name = toon.ATTR
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    L(attr.outputs['Color'], sep.inputs[0])

    def stops(values):
        r = nt.nodes.new('ShaderNodeValToRGB')
        r.color_ramp.interpolation = 'CONSTANT'
        els = r.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        els[0].position = 0.0
        els[0].color = values[0]
        for i in range(1, 16):
            e = els.new(max(0.0, i / 15.0 - 0.02))
            e.color = values[i]
        L(sep.outputs[0], r.inputs[0])
        return r
    base = stops([hexcol(c) for c in colours])
    glow = stops([(1, 1, 1, 1) if i in EMISSIVE else (0, 0, 0, 1) for i in range(16)])
    diff = nt.nodes.new('ShaderNodeBsdfDiffuse')
    diff.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new('ShaderNodeShaderToRGB')
    bw = nt.nodes.new('ShaderNodeRGBToBW')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation = 'CONSTANT'
    els = ramp.color_ramp.elements
    els[0].position = toon.RAMP_AT[0]
    els[0].color = (toon.RAMP[0],) * 3 + (1,)
    els[1].position = toon.RAMP_AT[1]
    els[1].color = (toon.RAMP[1],) * 3 + (1,)
    for at, v in zip(toon.RAMP_AT[2:], toon.RAMP[2:]):
        e = els.new(at)
        e.color = (v,) * 3 + (1,)
    L(diff.outputs[0], s2r.inputs[0])
    L(s2r.outputs[0], bw.inputs[0])
    L(bw.outputs[0], ramp.inputs[0])

    def maprange(src, lo, hi):
        n = nt.nodes.new('ShaderNodeMapRange')
        n.inputs['From Min'].default_value = 0.0
        n.inputs['From Max'].default_value = 1.0
        n.inputs['To Min'].default_value = lo
        n.inputs['To Max'].default_value = hi
        L(src, n.inputs['Value'])
        return n.outputs['Result']

    def mul(a, b):
        n = nt.nodes.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.blend_type = 'MULTIPLY'
        n.inputs['Factor'].default_value = 1.0
        L(a, n.inputs[6])
        L(b, n.inputs[7])
        return n.outputs[2]
    ao = maprange(sep.outputs[2], AO_FLOOR, 1.0)
    var = maprange(sep.outputs[1], 1.0 - VAR_GAIN / 2, 1.0 + VAR_GAIN / 2)
    lit = mul(mul(mul(base.outputs['Color'], ramp.outputs['Color']), ao), var)
    bright = nt.nodes.new('ShaderNodeMix')
    bright.data_type = 'RGBA'
    bright.blend_type = 'MULTIPLY'
    bright.inputs['Factor'].default_value = 1.0
    bright.inputs[7].default_value = (1.6, 1.6, 1.6, 1)
    L(base.outputs['Color'], bright.inputs[6])
    lift = nt.nodes.new('ShaderNodeMix')
    lift.data_type = 'RGBA'
    lift.blend_type = 'MIX'
    L(glow.outputs['Color'], lift.inputs['Factor'])
    L(lit, lift.inputs[6])
    L(bright.outputs[2], lift.inputs[7])
    em = nt.nodes.new('ShaderNodeEmission')
    final = lift.outputs[2]
    if night:
        dim = nt.nodes.new('ShaderNodeMix')
        dim.data_type = 'RGBA'
        dim.blend_type = 'MULTIPLY'
        dim.inputs['Factor'].default_value = 1.0
        dim.inputs[7].default_value = (0.2, 0.23, 0.36, 1)
        L(final, dim.inputs[6])
        pane = nt.nodes.new('ShaderNodeMath')
        pane.operation = 'LESS_THAN'
        pane.inputs[1].default_value = 0.5
        L(attr.outputs['Alpha'], pane.inputs[0])
        lit_win = nt.nodes.new('ShaderNodeMix')
        lit_win.data_type = 'RGBA'
        lit_win.blend_type = 'MIX'
        L(pane.outputs[0], lit_win.inputs['Factor'])
        L(dim.outputs[2], lit_win.inputs[6])
        lit_win.inputs[7].default_value = (1.6, 0.95, 0.38, 1)
        final = lit_win.outputs[2]
    L(final, em.inputs['Color'])
    L(em.outputs[0], out.inputs[0])
    return m


def add_outline(ob, thickness):
    """The inverted-hull outline toon.apply_look adds (for instances that share an already-dressed mesh)."""
    if 'Outline' in ob.modifiers or thickness <= 0:
        return
    so = ob.modifiers.new('Outline', 'SOLIDIFY')
    so.thickness = thickness
    so.offset = 1.0
    so.use_flip_normals = True
    so.use_rim = False
    so.material_offset = 1
    so.use_quality_normals = True


def apply_look(objects, material, outline=0.0):
    """toon.apply_look (palette slot + outline material + the Outline hull), then the zone's env material in slot 0."""
    for ob in objects:
        if ob.type != 'MESH':
            continue
        toon.apply_look(ob, outline=outline)
        ob.data.materials[0] = material


# ---------------------------------------------------------------------------------------------------- labels, sheets
def load_px(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return px


def save_px(path, px):
    h, w, _ = px.shape
    img = bpy.data.images.new('gv_tmp', w, h, alpha=True)
    img.pixels = px.ravel().tolist()
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def shrink(px, factor):
    """Box-filters an image down by an integer factor (a phone-size read of a render)."""
    h, w, c = px.shape
    h2, w2 = h // factor, w // factor
    return px[:h2 * factor, :w2 * factor].reshape(h2, factor, w2, factor, c).mean(axis=(1, 3))


class Labels:
    """Text strips rendered in their own Workbench scene, for labelling contact-sheet cells."""

    def __init__(self, tmp_dir):
        self.tmp = tmp_dir
        sc = bpy.data.scenes.get('GV_Labels') or bpy.data.scenes.new('GV_Labels')
        sc.render.engine = 'BLENDER_WORKBENCH'
        sc.display.shading.light = 'FLAT'
        sc.display.shading.color_type = 'SINGLE'
        sc.display.shading.single_color = (0.93, 0.90, 0.82)
        w = bpy.data.worlds.get('GV_LabelWorld') or bpy.data.worlds.new('GV_LabelWorld')
        w.color = (0.03, 0.032, 0.045)
        sc.world = w
        sc.view_settings.view_transform = 'Standard'
        sc.render.image_settings.file_format = 'PNG'
        sc.render.image_settings.color_mode = 'RGBA'
        sc.render.resolution_percentage = 100
        sc.render.film_transparent = False
        if 'GV_Label' not in sc.objects:
            cu = bpy.data.curves.new('GV_Label', 'FONT')
            cu.align_x = 'LEFT'
            cu.align_y = 'CENTER'
            txt = bpy.data.objects.new('GV_Label', cu)
            sc.collection.objects.link(txt)
            cam = bpy.data.objects.new('GV_LabelCam', bpy.data.cameras.new('GV_LabelCam'))
            cam.data.type = 'ORTHO'
            cam.data.ortho_scale = 10.0
            cam.location = (0, 0, 10)
            sc.collection.objects.link(cam)
            sc.camera = cam
        self.txt = sc.objects['GV_Label']
        self.sc = sc

    def image(self, text, w, h):
        sc = self.sc
        sc.render.resolution_x, sc.render.resolution_y = w, h
        hm = 10.0 * h / w
        lines = text.count('\n') + 1
        self.txt.data.body = text
        self.txt.data.size = hm * (0.56 if lines == 1 else 0.36)
        self.txt.location = (-5.0 + 0.2, (hm * 0.05 if lines > 1 else 0.0), 0)
        path = os.path.join(self.tmp, '_label.png')
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True, scene=sc.name)
        px = load_px(path)
        os.remove(path)
        return px


def compose(cells, labels, cols, out_path, bg=(0.112, 0.118, 0.152)):
    """Cells (pixel arrays of one size) each above its label strip, row-major, the first row at the top."""
    blocks = [np.concatenate([lab, img], axis=0) for img, lab in zip(cells, labels)]
    h, w, _ = blocks[0].shape
    rows = (len(blocks) + cols - 1) // cols
    sheet = np.zeros((rows * h, cols * w, 4), dtype=np.float32)
    sheet[..., :3] = bg
    sheet[..., 3] = 1.0
    for i, b in enumerate(blocks):
        r, c = divmod(i, cols)
        y0 = (rows - 1 - r) * h
        sheet[y0:y0 + h, c * w:(c + 1) * w] = b
    save_px(out_path, sheet)
    return out_path


def world_bounds(objects):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objects:
        if o.type != 'MESH':
            continue
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
    return lo, hi


def look_dir(az_deg, el_deg):
    """The direction from a subject to a camera `az_deg` round from its front (−Y) toward its left (−X), `el_deg` up."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))


def aim(cam, loc, target):
    cam.location = Vector(loc)
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def frame_ortho(cam, objects, az=35.0, el=30.0, margin=1.12):
    """Points an orthographic camera at the objects from (az, el) and fits them in a square frame."""
    lo, hi = world_bounds(objects)
    c = (lo + hi) / 2
    d = look_dir(az, el)
    r = (hi - lo).length / 2 + 0.5
    aim(cam, c + d * (r * 3 + 5), c)
    fwd = -d
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd).normalized()
    xs, ys = [], []
    for x in (lo.x, hi.x):
        for y in (lo.y, hi.y):
            for z in (lo.z, hi.z):
                p = Vector((x, y, z)) - c
                xs.append(p.dot(right))
                ys.append(p.dot(up))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * margin
    cam.data.shift_x = ((max(xs) + min(xs)) / 2) / cam.data.ortho_scale
    cam.data.shift_y = ((max(ys) + min(ys)) / 2) / cam.data.ortho_scale
    cam.data.clip_start = 0.05
    cam.data.clip_end = 500
    return lo, hi


# ---------------------------------------------------------------------------------------------------- rooms
def camera_dir(tpl):
    """The horizontal unit direction (game x, z) from the template's look-at point to its camera (layout.ts)."""
    cp, la = tpl['camera']['position'], tpl['camera']['lookAt']
    dx, dz = cp[0] - la[0], cp[2] - la[2]
    ln = math.hypot(dx, dz)
    return (0.0, 1.0) if ln < 1e-6 else (dx / ln, dz / ln)


def faces_camera(side, cdir):
    n = SIDE_NORMAL[side]
    return n[0] * cdir[0] + n[1] * cdir[1] > 0.5


def nearest_side(w, d, x, z):
    dx = w / 2 - abs(x)
    dz = d / 2 - abs(z)
    if dx < dz:
        return 'east' if x > 0 else 'west'
    return 'south' if z > 0 else 'north'


def _pick(rng, base, alts):
    """`base` unless one of `alts` [(meshId, chance)] wins its roll."""
    for mid, p in alts or ():
        if rng.random() < p:
            return mid
    return base


def room_placements(tpl, shell, rng, pieces, floor=None, wall_alts=None, hide_camera_side_hung=True):
    """Every piece of a template as the client builds it: [(meshId, Matrix, tag)]. `shell` names the zone's floor,
    wall, doorway, corner and their cut versions (wallCut, doorwayCut, cornerCut); `floor` = [(meshId, chance), …]
    rolled per tile (the rest is shell['floor']); `wall_alts` likewise per full-height segment. Tiles turn a random
    quarter; a piece's info['hole'] (game x0, z0, x1, z1 around its origin) removes the tiles whose centres fall in
    it; wall-hung props on walls that face the camera are left out (the client hides them)."""
    fw, fh = tpl['footprint']['w'], tpl['footprint']['h']
    W, D = fw * CELL, fh * CELL
    cdir = camera_dir(tpl)
    out = []
    holes = []
    for p in tpl['props']:
        pc = pieces.get(p['meshId'])
        if pc is not None and 'hole' in pc.info:
            x0, z0, x1, z1 = pc.info['hole']
            a = math.radians(p['rotationY'])
            cs, sn = math.cos(a), math.sin(a)
            xs, zs = [], []
            for (lx, lz) in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
                xs.append(p['position'][0] + lx * cs + lz * sn)
                zs.append(p['position'][2] - lx * sn + lz * cs)
            holes.append((min(xs), min(zs), max(xs), max(zs)))
    x = -W / 2 + TILE / 2
    while x < W / 2:
        z = -D / 2 + TILE / 2
        while z < D / 2:
            if not any(h[0] < x < h[2] and h[1] < z < h[3] for h in holes):
                mid = _pick(rng, shell['floor'], floor)
                out.append((mid, game_matrix(x, 0.0, z, 90.0 * rng.randrange(4)), 'floor'))
            z += TILE
        x += TILE
    doors = {(d['side'], d['offset']) for d in tpl['doors']}
    for side in ('north', 'east', 'south', 'west'):
        n = SIDE_NORMAL[side]
        along_x = side in ('north', 'south')
        count = fw if along_x else fh
        cut = faces_camera(side, cdir)
        length = W if along_x else D
        fixed = (n[1] * D / 2) if along_x else (n[0] * W / 2)
        yaw = SIDE_YAW[side]
        for i in range(count):
            a = -length / 2 + i * CELL
            if (side, i) in doors:
                spans = [(a + 1.0, 'wall'), (a + 4.0, 'doorway'), (a + 7.0, 'wall')]
            else:
                spans = [(a + 1.0 + 2.0 * k, 'wall') for k in range(4)]
            for c, kind in spans:
                gx, gz = (c, fixed) if along_x else (fixed, c)
                if kind == 'wall':
                    mid = shell['wallCut'] if cut else _pick(rng, shell['wall'], wall_alts)
                else:
                    mid = shell['doorwayCut'] if cut else shell['doorway']
                out.append((mid, game_matrix(gx, 0.0, gz, yaw), kind + (' cut' if cut else '')))
    for sx, sz, yaw, sides in CORNERS:
        cut = any(faces_camera(s, cdir) for s in sides)
        out.append((shell['cornerCut'] if cut else shell['corner'], game_matrix(sx * W / 2, 0.0, sz * D / 2, yaw),
                    'corner' + (' cut' if cut else '')))
    for p in tpl['props']:
        mid = p['meshId']
        px, py, pz = p['position']
        pc = pieces.get(mid)
        if pc is None:
            log('room %s: no piece %s' % (tpl['id'], mid))
            continue
        if hide_camera_side_hung and pc.role == 'wall-hung' and faces_camera(nearest_side(W, D, px, pz), cdir):
            continue
        out.append((mid, game_matrix(px, py, pz, p['rotationY']), 'prop'))
    return out


def build_room(placements, pieces, collection_name='Room', outline=0.0):
    """Linked duplicates of the kit meshes at their placements; returns (objects, lights [(world pos, kind, meshId)],
    stats {tris, instances, unique})."""
    col = _collection(collection_name)
    objs, lights = [], []
    tris = 0
    unique = set()
    for mid, mw, tag in placements:
        pc = pieces[mid]
        base_inv = pc.ob.matrix_world.inverted()
        for so in pc.meshes():
            o = bpy.data.objects.new('%s~' % so.name, so.data)
            col.objects.link(o)
            o.matrix_world = mw @ (base_inv @ so.matrix_world)
            if outline > 0 and pc.role not in ('shell', 'decal'):
                add_outline(o, outline)
            objs.append(o)
            tris += mesh_tris(so)
            unique.add(so.data.name)
        for e in pc.points:
            if e['kind'] == 'light':
                lights.append((mw @ (base_inv @ e.matrix_world).translation, e['light'], mid))
    return objs, lights, {'tris': tris, 'instances': len(objs), 'unique': len(unique)}


def clear_room(collection_name='Room'):
    col = bpy.data.collections.get(collection_name)
    if col is None:
        return
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def template_camera(cam, tpl):
    """The template's own camera (game position, lookAt, vertical fov) on a Blender camera."""
    c = tpl['camera']
    aim(cam, game_to_blender(c['position']), game_to_blender(c['lookAt']))
    cam.data.type = 'PERSP'
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.angle_y = math.radians(c['fov'])
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.data.clip_start = 0.1
    cam.data.clip_end = 300


# ---------------------------------------------------------------------------------------------------- export
def game_bounds(objects):
    lo, hi = world_bounds(objects)
    return {'min': [round(lo.x, 3) + 0.0, round(lo.z, 3) + 0.0, round(-hi.y, 3) + 0.0],
            'max': [round(hi.x, 3) + 0.0, round(hi.z, 3) + 0.0, round(-lo.y, 3) + 0.0]}


def unity_fbx_path(zone):
    """Where the Unity app reads a kit: unity/Assets/Gloamvault/Resources/Env/kit_<zone>.fbx (generated, git-ignored)."""
    return os.path.join(REPO, 'unity', 'Assets', 'Gloamvault', 'Resources', 'Env', 'kit_%s.fbx' % zone)


def export_kit(kit, glb_path, json_path, shell=None, about=None, extra=None, fbx_path=None):
    """Writes the kit's .glb (pieces named by meshId at the origin, parts and points as children, extras kind / zone /
    tris / role) and the piece list the client reads: {zone, about, palette, shell, pieces: {meshId: {tris, budget,
    role, bounds, parts, lights, fx, …info}}}. Coordinates in the .json are game space (`at`, `pivot`, `bounds`)."""
    import export as gexport
    objs = kit.objects()
    gexport.prepare_for_export(objs)
    pieces = {}
    for p in kit.pieces.values():
        p.ob['kind'] = 'kit'
        p.ob['zone'] = kit.zone
        p.ob['tris'] = p.tris()
        p.ob['role'] = p.role
        for o in p.parts:
            o['zone'] = kit.zone
            o['tris'] = mesh_tris(o)
        entry = {'tris': p.tris(), 'budget': p.budget, 'role': p.role, 'bounds': game_bounds(p.meshes()),
                 'parts': [dict({'name': o.name, 'part': o['part'], 'tris': mesh_tris(o),
                                 'pivot': blender_to_game(o.matrix_world.translation), 'axis': o['axis']},
                                **({'note': o['note']} if 'note' in o else {})) for o in p.parts],
                 'lights': [{'name': e.name, 'kind': e['light'], 'at': blender_to_game(e.matrix_world.translation)}
                            for e in p.points if e['kind'] == 'light'],
                 'fx': [{'name': e.name, 'kind': e['fx'], 'at': blender_to_game(e.matrix_world.translation)}
                        for e in p.points if e['kind'] == 'fx']}
        entry.update(p.info)
        pieces[p.id] = entry
    kb = gexport.export_glb(glb_path, objs)
    if fbx_path:
        # The same pieces for Unity (Phase 11, D-140): meshes only — the lights and fx points are in the .json.
        gexport.export_fbx(fbx_path, [o for o in objs if o.type == 'MESH'])
    data = {'zone': kit.zone, 'about': about or '', 'palette': kit.colours, 'shell': shell, 'pieces': pieces}
    data.update(extra or {})
    write_json(json_path, data)
    return kb
