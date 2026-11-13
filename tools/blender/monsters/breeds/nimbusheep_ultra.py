"""Nimbusheep at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9; RECIPE.md): the recipe for `tools/blender/monsters/build_ultra.py`.

A round, calm sheep whose wool is a raincloud (chatgpt/monsters/05-nimbusheep; the hero decides shapes, the turnaround
gives the measurements):
  - cloud wool: a cumulus of clumps, each a puff of puffs of puffs (`nimbusheep_wool`), over the body and the top of
    the head, with bluish creases between the puffs, short curly locks baked into the maps and soft cards on the outline;
  - a grey-blue face with soft short fur: big glossy dark eyes, a heavy upper lash line, short dark brows, a pale muzzle,
    a dark rounded nose and a small "w" smile, pink blush;
  - small floppy ears (a fur leaf, cupped, pink inside) under two cream spiral horns (`nimbusheep_horns`, rigid props);
  - four sturdy grey-blue legs on small dark cloven hooves; a little wool tail hidden in the rump.
The drizzle and the rainbow are runtime effects (PROMPTS.md, Notes for Claude Code), not geometry.

Size: 1.1 × Puddlepup (PROMPTS.md): HEIGHT_UNITS 165, so the model stands 1.1 m tall to the top of its wool.
Metres; the monster faces −Y, Z is up, +X is its left. Palette: CONTENT §2.2 #10 (#E9EEF6 / #8C97AD / rainbow /
#2E3440); Stormcrown: src/art/monster/variants.ts (#4A5366 / #2E3440 / #F2D16B / #E6ECF5), horns stay cream.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, norm, smooth, tangent, v3
from monsters.breeds import nimbusheep_horns as H
from monsters.breeds import nimbusheep_wool as W

ID = 'nimbusheep'
LOOK = 'nimbusheep-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 165

PALETTE = {'body': '#E9EEF6', 'belly': '#8C97AD', 'accent': '#F28F8F', 'eye': '#2E3440'}
RAINBOW = ['#F28F8F', '#F7D36B', '#8FD1A8', '#8FB8F2']          # the happy rainbow (a runtime effect)
# Stormcrown: dark thundercloud wool whose edges glow gold where sunlight breaks through (variant picture); the muzzle a
# mid grey on the dark face (muzzle_k); horns, ear linings and blush keep their colours
VARIANTS = {
    'stormcrown-nimbusheep': {'body': '#4A5366', 'belly': '#2E3440', 'accent': '#F2D16B', 'eye': '#E6ECF5',
                              'rim': '#F2D16B', 'muzzle_k': 0.36, 'blush_k': 0.24, 'props': ['crown']},
}
# colours CONTENT has no hex for (the card's suggestions and the pictures' parts)
HORN_HEX = '#F2E6CC'                 # PROMPTS.md: horns cream (the highlights; the body of the horn a touch deeper)
EAR_PINK = '#E3A1AA'                 # the ears' lining (1-hero.png)
BLUSH_HEX = '#F2A2AA'
MOUTH_HEX = '#3A3D47'

BODY_TRIS = 74000                    # round 2: 50k showed facets on the puffs (round 3: 58k; Nov 12: 68k; Nov 13: 74k, the outline's steps)
# Nov 12 (owner, v1.23.0: the wool read slightly crumpled, like plaster, up close): a softer normal map (the game's
# default is 0.6), and the narrow slots between puffs never bake near black
NORMAL_SCALE = 0.5
# the Lite copy: the horns and the crown at 1.3k between them, so the bumpy wool body keeps ~1k more of the 12k (Nov 12:
# the Lite's wool read as crumpled paper, its shading 29° off its own triangles)
LITE_PROPS_TRIS = 1300
AO_FLOOR = 0.5
AO_SOFTEN = 1.5
# Stormcrown's gold glows (the variant picture: sunlight breaking through the storm cloud's edges): its own ORM with a
# glow mask (`glow_stormcrown`, painted in paint_sources)
VARIANT_ORM = {'stormcrown': {'glow': {'strength': 0.75, 'tint': '#ffd36a'}}}     # Nov 13: 1.4 washed the slate gold
ATLAS_DENSITY = {'lo_eyes': 1.35, 'lo_props': 0.9, 'lo_props_stormcrown': 0.55}   # the variant-only crown: less atlas
# round 2: unwrap lo_body at smoothed positions (the lumpy wool smart-projected into ~1,750 islands covering 20% of the
# atlas; a smoothed twin gives ~400 islands and ~56%); 160 half-steps ≈ my 80-step test. The face and ears keep their shape
UV_SMOOTH = 160
CARD_STYLE = 'wool'                  # curly ringlet tiles (the damp-fur locks read as flakes on the wool, round 1)
CARD_LAYERS = 1                      # Nov 13: the ears' short fur only (no wool wisps, no fetlock fringe)
CARD_SHADE = 1.0                     # white wool stays white on the outline (0.88 greyed it)
LOCK_TEMPLATES = {'head': (7, 11, 3, 0.22), 'body': (5, 7, 3, 0.3)}


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def _luma(h: str) -> float:
    r, g, b = C.srgb(h)
    return 0.3 * r + 0.59 * g + 0.11 * b


def colours(pal: dict) -> dict:
    """Every derived colour of a palette (the base or a variant)."""
    wool, skin = pal['body'], pal['belly']
    storm = _luma(wool) < 0.5
    return {
        'wool': wool,
        # the creases between the puffs: a cool lavender-blue shadow (1-hero.png), not grey dirt
        # round 2: crevices a cool lavender-blue of the wool, never grey (the baked AO greys them a little more)
        'crease': C.shade_hex(wool, 0.8, cool=0.02) if storm else '#C8D2E8',   # Nov 12 review: a cool lavender-blue, never grey or pink
        'puff_top': C.mix_hex(wool, '#FFFFFF', 0.06 if storm else 0.6),
        # the baked AO darkens the wool's colour (BASE_AO): the cloud's lit side is painted a touch above its hex
        'wool_lit': C.mix_hex(wool, '#8C97B8', 0.14) if storm else C.mix_hex(wool, '#FFFFFF', 0.4),   # Nov 13: slate, not near-black
        'rim': pal.get('rim'),
        'skin': skin,
        'muzzle': C.mix_hex(skin, '#FFFFFF', pal.get('muzzle_k', 0.76)),
        'brow': C.shade_hex(skin, 0.5 if not storm else 0.72, cool=0.02),
        'nose': C.mix_hex('#3A3D46', skin, 0.12) if not storm else '#1E2026',
        'mouth': MOUTH_HEX if not storm else '#15161A',
        'hoof': '#35373B' if not storm else '#2A2F3A',          # charcoal (rounds 1-2 read bottle-green in game, 3 brown, Nov 12 chrome)
        'pink': C.mix_hex(EAR_PINK, skin, 0.28) if not storm else C.mix_hex(EAR_PINK, '#7A5560', 0.4),   # muted, dusty
        'blush': BLUSH_HEX,
        'horn': HORN_HEX,
    }


# ----------------------------------------------------------------------------- the head
# round 3 (review): the head moves forward HY so the whole profile clears the chest ruff (2-turnaround side); the cap, the
# fringe, the windows, the horns and the crown move with it (nimbusheep_wool.HEAD_DY)
HY = W.HEAD_DY
HEAD_C = Vector((0.0, -0.36 + HY, 0.765))
HEAD_R = (0.19, 0.18, 0.185)
MUZZLE = ((0.0, -0.5 + HY, 0.664), (0.1, 0.09, 0.064))
NOSE_C = Vector((0.0, -0.584 + HY, 0.697))
NOSE_R = (0.04, 0.022, 0.022)
NOSE2 = ((0.0, -0.582 + HY, 0.683), (0.022, 0.018, 0.016))     # the nose narrows to a rounded point below (a soft triangle)
EYE_C = {s: Vector((0.124 * s, -0.503 + HY, 0.766)) for s in (1, -1)}
EYE_R = 0.061
EYE_DEPTH = (0.42, 0.26)                 # round 3: a flatter dome, seated in a socket of lid and cheek pads (eye_pads)
EYE_SPREAD = 1.1
BROWS = [((0.08, -0.508 + HY, 0.846), (0.03, 0.05, 0.0095)), ((0.126, -0.497 + HY, 0.853), (0.03, 0.05, 0.0105))]   # left; mirrored
BLUSH_C = (0.165, -0.47 + HY, 0.682)

HEAD_ELLS = [
    ('head', tuple(HEAD_C), HEAD_R),
    ('brow', (0.0, -0.425 + HY, 0.83), (0.15, 0.1, 0.08)),
    ('cheekL', (0.118, -0.425 + HY, 0.685), (0.095, 0.09, 0.084)),
    ('cheekR', (-0.118, -0.425 + HY, 0.685), (0.095, 0.09, 0.084)),
    ('jaw', (0.0, -0.44 + HY, 0.635), (0.14, 0.11, 0.07)),
    ('muzzle', MUZZLE[0], MUZZLE[1]),
    ('bridge', (0.0, -0.5 + HY, 0.735), (0.055, 0.07, 0.05)),
    ('nose', tuple(NOSE_C), NOSE_R),
    ('nose2', NOSE2[0], NOSE2[1]),
    ('chin', (0.0, -0.5 + HY, 0.616), (0.055, 0.05, 0.035)),
    # Nov 12 (owner: a small dark spot under the chin): the throat fills the slot between the jaw and the collar's puffs
    ('throat', (0.0, -0.42 + HY, 0.585), (0.12, 0.07, 0.05)),
]

# ----------------------------------------------------------------------------- the legs and hooves
LEGS = {'FL': (0.14, -0.25), 'FR': (-0.14, -0.25), 'BL': (0.14, 0.25), 'BR': (-0.14, 0.25)}
LEG_R = 0.047
HOOF_TOP = 0.064
TOE = {'dx': 0.03, 'dy': -0.036, 'zc': 0.026, 'rx': 0.034, 'ry': (0.068, 0.044), 'rz': (0.038, 0.026)}


def leg_ells(leg: str) -> list[tuple]:
    x, y = LEGS[leg]
    return [(f'shank{leg}', (x, y, 0.22), (0.061, 0.052, 0.16)), (f'fetlock{leg}', (x, y - 0.008, 0.078), (0.059, 0.055, 0.032))]


def leg_capsule(leg: str) -> tuple:
    x, y = LEGS[leg]
    return (x, y + 0.012, 0.43), (x, y - 0.004, 0.1), LEG_R


def toe_ells(leg: str) -> list[tuple]:
    """The hoof's two toes as ellipsoids (for zones; the mesh flattens their soles)."""
    x, y = LEGS[leg]
    out = []
    for k in (1, -1):
        out.append(((x + k * TOE['dx'], y + TOE['dy'] - 0.012, TOE['zc'] + 0.006), (TOE['rx'], 0.058, 0.036)))
    return out


def hoof_mesh(name: str) -> bpy.types.Object:
    """Eight toes (two per hoof): rounded, taller at the heel, a flat sole on the ground, pointed a little at the toe;
    the two toes of a hoof meet in a cleft down the front (4-details.png, panel 3)."""
    bm = bmesh.new()
    for leg, (x, y) in LEGS.items():
        for k in (1, -1):
            tmp = bmesh.new()
            bmesh.ops.create_uvsphere(tmp, u_segments=32, v_segments=16, radius=1.0)
            for v in tmp.verts:
                X, Y, Z = v.co
                ry = TOE['ry'][0] if Y < 0 else TOE['ry'][1]
                front = max(0.0, -Y)
                if Z >= 0:
                    z = TOE['zc'] + Z * TOE['rz'][0] * (1.0 - 0.38 * front ** 1.5)
                else:
                    z = TOE['zc'] - TOE['rz'][1] * abs(Z) ** 0.3
                # the toe turns in a little at its tip, so the two toes read as one rounded hoof split down the front
                xx = x + k * TOE['dx'] + X * TOE['rx'] * (1.0 - 0.18 * front) - k * 0.006 * front
                v.co = Vector((xx, y + TOE['dy'] + Y * ry, max(z, 0.0005)))
            me = bpy.data.meshes.new('tmp_toe')
            tmp.to_mesh(me)
            tmp.free()
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


# ----------------------------------------------------------------------------- the ears: a cupped fur leaf, pink inside
EAR_ROOT0 = v3((0.162, -0.318 + HY, 0.742))  # left ear; the first fifth sits inside the head
EAR_TIP0 = v3((0.36, -0.305 + HY, 0.565))        # round 2: down and out about 40 degrees
EAR_LEN = float(np.linalg.norm(EAR_TIP0 - EAR_ROOT0))
EAR_WMAX = 0.066                            # half width at the widest
EAR_T = (0.034, 0.024)                      # half thickness at the root and the tip (round 3: thicker still, never a blade)
EAR_CUP = 0.026                             # the lining's hollow
EAR_BEND = -0.045                           # the tip curls back (away from the lining) this much


def ear_frame(s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Root, along (a), across (b) and the lining's normal (n: forward and a little down) of ear s."""
    m = v3((s, 1, 1))
    r0 = EAR_ROOT0 * m
    a = (EAR_TIP0 - EAR_ROOT0) * m
    a = a / np.linalg.norm(a)
    n0 = v3((0.65 * s, -0.75, 0.0))       # Nov 12 review: turned about 40° out, so the profile shows a cupped leaf, not a blade
    n = n0 - a * (n0 @ a)
    n = n / np.linalg.norm(n)
    b = np.cross(n, a)
    return r0, a, b, n


def _ear_shape(u):
    """(half width, half thickness, cup, bend) at u along the ear; the leaf's ends round off."""
    u = np.clip(np.asarray(u, float), 0.0, 1.0)
    rho = np.sqrt(np.clip(1.0 - (2.0 * u - 1.0) ** 2, 0.0, 1.0))
    # a leaf: widest a little before the middle, tapering to a rounded point (round 1 read as a rectangular card)
    hw = EAR_WMAX * rho ** 0.85 * (1.1 - 0.5 * u)
    ht = (EAR_T[0] + (EAR_T[1] - EAR_T[0]) * u) * rho
    return hw, ht, EAR_CUP * rho * rho, EAR_BEND * u * u


def ear_mesh(s: int) -> bpy.types.Object:
    """A closed leaf: a deformed sphere (u along the ear, the sphere's ring as the leaf's cross-section)."""
    r0, a, b, n = ear_frame(s)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=40, radius=1.0)
    for v in bm.verts:
        X, Y, Z = v.co.x, v.co.z, v.co.y        # the sphere's z axis runs along the ear
        u = (Y + 1.0) * 0.5
        rho = math.sqrt(max(1e-8, 1.0 - Y * Y))
        cs, sn = X / rho, Z / rho
        hw, ht, cup, bend = (float(q) for q in _ear_shape(u))
        across = cs * hw
        nn = sn * ht + bend - cup * max(0.0, sn) ** 3
        p = r0 + a * (EAR_LEN * u) + b * across + n * nn
        v.co = Vector(p)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'ear{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
    return ob


def ear_lookup(p: np.ndarray) -> dict:
    """Per point: s (0 = far from both ears), u along the ear, c across (−1..1 at the edges), m = the offset from the
    leaf's middle surface (+ = the lining side), e (≤ 1 inside the leaf's cross-section)."""
    k = len(p)
    out = {'s': np.zeros(k), 'u': np.zeros(k), 'c': np.zeros(k), 'm': np.zeros(k), 'e': np.full(k, 9.0)}
    for s in (1, -1):
        r0, a, b, n = ear_frame(s)
        q = p - r0
        al, ac, nn = q @ a, q @ b, q @ n
        u = al / EAR_LEN
        hw, ht, cup, bend = _ear_shape(u)
        c = ac / np.maximum(hw, 1e-4)
        m = nn - bend
        e = np.sqrt(np.clip(c, -3, 3) ** 2 + (m / np.maximum(ht, 2e-3)) ** 2)
        on = (u > -0.02) & (u < 1.04) & (e < out['e']) & (p[:, 0] * s > 0.1)
        for key, val in (('s', np.full(k, float(s))), ('u', u), ('c', c), ('m', m), ('e', e)):
            out[key] = np.where(on, val, out[key])
    return out


# ----------------------------------------------------------------------------- the tail
TAIL_BASE = (0.0, 0.43, 0.57)
TAIL_DIR = tuple(v3((0.0, 0.92, 0.2)) / np.linalg.norm((0.0, 0.92, 0.2)))
TAIL_LEN = 0.15
TAIL_PTS = U.chain_points(TAIL_BASE, TAIL_DIR, TAIL_LEN, 2)


# ----------------------------------------------------------------------------- parts
def _ell_part(name: str, c, r) -> Part:
    return Part(name, 'sphere', loc=tuple(c), radius=1.0, scale=tuple(r))


def wool_cores() -> list[tuple]:
    """Smooth masses under the puffs (hidden by them): the weight proxy's body, and a floor for the cloud. Nov 12: the
    floor sits at the clumps' centres (it was 3.5 cm deeper; the review still found black slits), so the gaps between
    clumps are shallow lavender-white dimples, not pits."""
    return [('coreF', W.FRONT[0], tuple(r - W.DEPTH + 0.004 for r in W.FRONT[1])),
            ('coreR', W.REAR[0], tuple(r - W.DEPTH + 0.004 for r in W.REAR[1])),
            ('coreCap', W.CAP[0], tuple(r - W.CAP_DEPTH + 0.004 for r in W.CAP[1]))]


def eye_pads() -> list[Part]:
    """Round 3 (review: the eye was a glass dome bulging past the cheek in profile): an upper lid pad over the top of
    each lens and a soft cheek pad below and outside it, so the eye sits in a socket and reads front-facing from the side."""
    out = []
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        rot = Matrix((xax, yax, look)).transposed().to_euler('XYZ')
        deg = tuple(math.degrees(a) for a in rot)
        cheek = c - yax * (EYE_R * 0.98) + xax * (s * EYE_R * 0.3) - look * (EYE_R * 0.42)
        out.append(Part(f'socket{s}', 'sphere', loc=tuple(cheek), radius=1.0, scale=(EYE_R * 1.05, EYE_R * 0.42, EYE_R * 0.5), rot=deg))
    return out


def all_parts() -> list[Part]:
    ps = [_ell_part(n, c, r) for n, c, r in HEAD_ELLS] + eye_pads()
    for leg in LEGS:
        a, b, r = leg_capsule(leg)
        ps.append(Part(f'leg{leg}', 'capsule', loc=a, to=b, radius=r))
        ps += [_ell_part(n, c, rr) for n, c, rr in leg_ells(leg)]
    ps += [_ell_part(n, c, r) for n, c, r in wool_cores()]
    return ps


def body_extras() -> list[bpy.types.Object]:
    """The wool's puffs, the two ear leaves and the eight toes (new objects on every call; the voxel body consumes them)."""
    return [W.puff_mesh(), ear_mesh(1), ear_mesh(-1), hoof_mesh('hooves')]


# ----------------------------------------------------------------------------- signed distances (the zones)
def _sd_ell(p: np.ndarray, c, r) -> np.ndarray:
    q = (p - v3(c)) / v3(r)
    k0 = np.linalg.norm(q, axis=1)
    k1 = np.linalg.norm(q / v3(r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def _sd_capsule(p: np.ndarray, a, b, r) -> np.ndarray:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1) - r


def skin_sds(p: np.ndarray) -> dict[str, np.ndarray]:
    head = np.full(len(p), 9.0)
    for _n, c, r in HEAD_ELLS:
        head = np.minimum(head, _sd_ell(p, c, r))
    leg = np.full(len(p), 9.0)
    hoof = np.full(len(p), 9.0)
    for lg in LEGS:
        a, b, r = leg_capsule(lg)
        leg = np.minimum(leg, _sd_capsule(p, a, b, r))
        for _n, c, rr in leg_ells(lg):
            leg = np.minimum(leg, _sd_ell(p, c, rr))
        for c, rr in toe_ells(lg):
            hoof = np.minimum(hoof, _sd_ell(p, c, rr))
    return {'head': head, 'leg': leg, 'hoof': hoof}


_ZCACHE: dict = {}


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    wf = W.sample(p)
    sd = skin_sds(p)
    E = ear_lookup(p)
    ear_sd = np.where(E['s'] != 0, (E['e'] - 1.0) * 0.012, 9.0)
    skin_d = np.minimum(np.minimum(sd['head'], sd['leg']), np.minimum(sd['hoof'], ear_sd))
    wool = ((wf['d1'] < skin_d + 0.0035) & (wf['d1'] < 0.05)) | (skin_d > 0.03)
    ear = (~wool) & (E['s'] != 0) & (E['e'] < 1.6) & (E['u'] > 0.12)
    ear_inner = ear & (E['m'] > -0.0015) & (np.abs(E['c']) < 0.8) & (E['u'] > 0.2) & (E['u'] < 0.93)
    hoof = (~wool) & (sd['hoof'] < sd['leg'] + 0.0015) & (z < HOOF_TOP + 0.01)
    leg = (~wool) & (~hoof) & (sd['leg'] < sd['head']) & (z < 0.45) & ~ear
    head = (~wool) & (~leg) & (~hoof)
    muzzle = head & (S.in_ellipsoid(p, MUZZLE[0], tuple(r * 1.08 for r in MUZZLE[1])) < 1.0)
    nose = head & ((S.in_ellipsoid(p, tuple(NOSE_C), tuple(r * 1.25 for r in NOSE_R)) < 1.0)
                   | (S.in_ellipsoid(p, NOSE2[0], tuple(r * 1.3 for r in NOSE2[1])) < 1.0))
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = head & ~ear & (y < -0.42 + HY) & (z > 0.57)
    cheek = face & (ax > 0.13) & (z < 0.74)
    reg = W.layout()['region']
    cid = wf['cid']
    tail = wool & (cid >= 0) & (reg[np.clip(cid, 0, None)] == W.REGIONS['tail'])
    cap = wool & (cid >= 0) & np.isin(reg[np.clip(cid, 0, None)], [W.REGIONS['cap'], W.REGIONS['fringe']])
    sole = z < 0.004
    return {'wool': wool, 'ear': ear, 'ear_u': E['u'], 'ear_c': E['c'], 'ear_m': E['m'], 'ear_inner': ear_inner, 'hoof': hoof, 'leg': leg,
            'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face, 'cheek': cheek, 'tail': tail,
            'cap': cap, 'sole': sole, 'paw': hoof, 'toes': hoof & (z < 0.03), 'field': wf, 'skin_d': skin_d}


def uv_smooth_mask(co: np.ndarray) -> np.ndarray:
    """UV_SMOOTH's strength per lo_body vertex: the wool smooths fully, the legs partly, the face, ears and hooves not at
    all (they unwrap well as they are, and their texel density matters most)."""
    z = zones(co)
    m = np.where(z['wool'], 1.0, 0.0)
    m = np.where(z['leg'], 0.5, m)
    m = np.where(z['head'] & ~z['face'] & ~z['ear'], 0.3, m)
    return m


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(z['face'] * 1.0 + z['muzzle'] * 1.0 + (z['eye_d'] < 0.1) * 1.0 + z['hoof'] * 0.6 + z['ear'] * 0.5, 0, 1)


# ----------------------------------------------------------------------------- carving (the high source only)
def mouth_curve() -> list[tuple[float, float]]:
    """The philtrum down from the nose, then a small "w" smile whose ends curl up (1-hero.png)."""
    # round 2: a short philtrum into a small smile (round 1's read as a wide line)
    mid = 0.656
    pts = [(0.0, NOSE2[0][2] - 0.014), (0.0, mid)]
    right = []
    for k in range(0, 13):
        t = k / 12
        xx = 0.06 * t
        zz = mid - 0.006 * math.sin(math.pi * min(1.0, t * 1.15)) + 0.011 * t * t
        right.append((xx, zz))
    left = [(-a, b) for a, b in reversed(right[1:])]
    return pts + right[1:], left + [(0.0, mid)]


LID_LASH, LID_DROP, LID_W = 0.08, 0.16, 0.8


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye (+Z of its dome looks out, a little forward of the head's normal)."""
    c = EYE_C[s]
    surf_n = Vector(((c.x - HEAD_C.x) / HEAD_R[0] ** 2, (c.y - HEAD_C.y) / HEAD_R[1] ** 2, (c.z - HEAD_C.z) / HEAD_R[2] ** 2)).normalized()
    look = (surf_n * 0.6 + Vector((0, -1, 0)) * 0.4).normalized()    # (round 3: facing further forward buried the inner half)
    look = (look + Vector((0, 0, 0.04))).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


def blink_pivot(s: int) -> tuple[Vector, Vector, Vector]:
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.72, 0.04, 0.2)


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens: the soft closed lid (a bulge) and its lash line, a down-curved arc a little below the eye's
    middle (3-faces.png 'blink'). Hidden by the lens until a blink sinks it into the head."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax_, ay_ = EYE_R * 1.0 * EYE_SPREAD, EYE_R * 1.04 * EYE_SPREAD
        r2 = (xe / ax_) ** 2 + (ye / ay_) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax_ * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * EYE_R
        th = 0.0019 + 0.0015 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.0) & (r2 < 0.8)        # round 3: the lash line stays under the lens
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def _value_noise(p: np.ndarray, freq: float, seed: int) -> np.ndarray:
    """Smooth value noise in 0..1 on a hashed integer lattice (deterministic; no RNG state)."""
    q = p * freq + seed * 17.13
    i0 = np.floor(q).astype(np.int64)
    f = q - i0
    f = f * f * (3.0 - 2.0 * f)
    out = np.zeros(len(p))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                ix, iy, iz = i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz
                h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
                h = (h ^ (h >> 13)) * 1274126177
                v = ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * v
    return out


def cotton(p: np.ndarray) -> np.ndarray:
    """The wool's cotton texture, −1..1: soft bumps of two sizes (2.5 and 1.2 cm), billowy rather than combed
    (4-details.png panels 4 and 6). Sculpted into the high body and baked, instead of lying locks (round 1: the bake
    saw the skin between the locks and the AO came out as dark specks). Nov 12: without the 6 mm octave (the shipped
    1024² normal map aliased it into a crumpled grain)."""
    n = 0.58 * _value_noise(p, 1 / 0.025, 3) + 0.42 * _value_noise(p, 1 / 0.012, 5)
    return np.clip((n - 0.5) * 2.2, -1.0, 1.0)


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    zw = zones(co, vn)
    wool_k = zw['wool'] * smooth(0.002, 0.012, zw['skin_d'] - zw['field']['d1'])
    right, left = mouth_curve()
    md = np.minimum(S.polyline_dist(x, z, right), S.polyline_dist(x, z, left))
    front = smooth(-0.5 + HY, -0.545 + HY, y)
    groove = np.exp(-(md / 0.0026) ** 2) * front * (z < NOSE2[0][2] - 0.008) * (z > 0.62)      # Nov 13: a clearer smile
    nos = np.zeros(len(co))
    for s in (1, -1):
        dd = np.sqrt(((x - 0.017 * s) / 1.5) ** 2 + (z - (NOSE_C.z - 0.01)) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.0066) ** 2))
    nos *= smooth(NOSE_C.y + 0.016, NOSE_C.y + 0.006, y)
    # the hooves: the cleft down the front between the two toes
    cleft = np.zeros(len(co))
    for leg, (lx, ly) in LEGS.items():
        near = (np.hypot(x - lx, y - ly) < 0.12) & (z < 0.09)
        cleft = np.maximum(cleft, np.exp(-((x - lx) / 0.0026) ** 2) * near * smooth(ly - 0.01, ly - 0.05, y) * smooth(0.075, 0.05, z))
    bulge, lash = closed_lid(co)
    # round 3: fill the V between lobes and between clumps a little (a soft cumulus, not lumps with hard creases)
    wf = zw['field']
    # Nov 12: rounder fillets (a soft cumulus: the creases between lobes are U-shaped, not folds) and a gentler cotton
    fillet = (0.0065 * smooth(0.017, 0.0, wf['p2'] - wf['p1']) + 0.009 * smooth(0.03, 0.0, wf['d2'] - wf['d1'])) * wool_k
    disp = (-0.0018 * groove - 0.0062 * nos - 0.003 * cleft + 0.0035 * bulge - 0.0012 * lash + 0.0024 * cotton(co) * wool_k
            + fillet)
    disp = disp + 0.006 * _skin_seam(zw)
    S.set_positions(ob, co + vn * disp[:, None])
    # Nov 12: round off what's left of the V-notch where two puffs or two clumps meet (it baked as thin dark lines, like
    # cracks in plaster): a few smoothing steps only along the seams, which pushes each V out into a soft U
    notch = wool_k * np.maximum(smooth(0.016, 0.0, wf['d2'] - wf['d1']), 0.8 * smooth(0.01, 0.0, wf['p2'] - wf['p1']))
    S.set_positions(ob, _smoothed(ob, 12, 0.6, np.maximum(notch, _skin_seam(zw))))
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)


def carve_low(ob: bpy.types.Object) -> None:
    """The low body before decimation: the high body's fillets and seam smoothing (no cotton, no face carving), so it
    follows the filled creases (Nov 12 review: black slits with chrome edges between the puffs, in the game only: the low
    body kept deep slits where the high one was filled, and the bake's rays there found the wrong surface)."""
    co, vn = S.mesh_arrays(ob)
    zw = zones(co, vn)
    wf = zw['field']
    wool_k = zw['wool'] * smooth(0.002, 0.012, zw['skin_d'] - wf['d1'])
    fillet = (0.0065 * smooth(0.017, 0.0, wf['p2'] - wf['p1']) + 0.009 * smooth(0.03, 0.0, wf['d2'] - wf['d1'])) * wool_k
    S.set_positions(ob, co + vn * (fillet + 0.006 * _skin_seam(zw))[:, None])
    notch = wool_k * np.maximum(smooth(0.016, 0.0, wf['d2'] - wf['d1']), 0.8 * smooth(0.01, 0.0, wf['p2'] - wf['p1']))
    S.set_positions(ob, _smoothed(ob, 12, 0.6, np.maximum(notch, _skin_seam(zw))))


def _skin_seam(zw: dict) -> np.ndarray:
    """0..1 along the join of the skin and the wool (the jaw to the ruff, the neck behind the ears, the tops of the legs),
    where the two surfaces meet in a V (Nov 13 review: a jagged black tear with bright lips under the jaw, a torn neck
    patch): filled out a little and smoothed, so the face skin runs into the ruff. Not on the ears or the eyes."""
    m = smooth(0.014, 0.0, np.abs(zw['field']['d1'] - zw['skin_d']))
    return m * (zw['ear'] < 0.5) * (zw['eye_d'] > EYE_R * 1.6)


def _smoothed(ob: bpy.types.Object, iterations: int, factor: float, mask: np.ndarray) -> np.ndarray:
    """Laplacian smoothing of the positions, each vertex moving `factor` × mask toward its neighbours' mean per step (as
    lib.surface.laplacian_positions, with bincount: fast enough for the multi-million-vertex high body)."""
    co, _ = S.mesh_arrays(ob)
    me = ob.data
    ev = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)
    n = len(co)
    a = np.concatenate([ev[:, 0], ev[:, 1]])
    b = np.concatenate([ev[:, 1], ev[:, 0]])
    deg = np.maximum(np.bincount(a, minlength=n), 1).astype(np.float64)
    k = factor * np.clip(np.asarray(mask, np.float64), 0.0, 1.0)[:, None]
    p = co.astype(np.float64)
    for _ in range(int(iterations)):
        mean = np.stack([np.bincount(a, weights=p[b, i], minlength=n) for i in range(3)], axis=1) / deg[:, None]
        p += k * (mean - p)
    return p


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 64 if high else 40             # round 3: a round outline, no polygon corners
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * 1.0 * EYE_SPREAD, v.co.y * EYE_R * 1.04 * EYE_SPREAD, v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((EYE_R * 1.0, EYE_R * 1.04, EYE_R * EYE_DEPTH[0])))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """A big dark pupil in a blue-grey iris with a dark limbal ring, a white crescent low on the outer side, two crisp
    catchlights toward the key light, and a heavy upper lash line (the sleepy look, 3-faces.png 'neutral'). A pale
    palette eye (Stormcrown #E6ECF5) turns the iris to pale silver round the same dark pupil."""
    m, nb = new_mat(name)
    pale = pal is not None and _luma(pal['eye']) > 0.5
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    # Nov 13 review (3-faces neutral, the hero: sleepy): the upper lid covers the top quarter of the iris, a soft curve a
    # little lower at the outer corner; matte fur, not lens
    lid = nb.smooth(nb.math('ADD', ry, nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', rx, side), 0.1, 0.9), 0.08)), 0.4, 0.46)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.mix(lid, nb.rgb((1.0, 0.05, 1.0)), nb.rgb((1.0, 0.75, 0.0))), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    # round 2 (review): round 1's lower iris glow washed over the pupil, so the eye read as a flat mid-blue oval. Now a
    # big pupil in the palette's eye colour (#2E3440) fills ~70% of the iris, inside a thin slate-blue ring, and the
    # white shows as a crescent low on the outer side
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', rx, 0.86), nb.math('DIVIDE', ry, 0.88), 0.0))
    pupil = C.mix_hex(PALETTE['eye'], '#000000', 0.45)
    if pale:
        e = pal['eye']
        iris = [C.mix_hex(e, '#59647A', 0.45), e, C.mix_hex(e, '#FFFFFF', 0.3), C.mix_hex(e, '#3A4152', 0.6)]
        pupil = '#14161C'
    else:
        iris = ['#33476A', '#4F6A92', '#6A86AE', '#232B3C']
    # round 3: the pupil about 70% of the iris, so the eye reads as a dark dot at 64 px
    iris_c = nb.ramp(ri, [(0.0, C.lin(pupil)), (0.58, C.lin(pupil)), (0.62, C.lin(iris[0])), (0.7, C.lin(iris[1])),
                          (0.76, C.lin(iris[2])), (0.8, C.lin(iris[3])), (0.84, C.lin('#151820')), (1.4, C.lin('#151820'))])
    ring_lo = nb.math('MULTIPLY', nb.smooth(ry, 0.0, -0.6), nb.math('MULTIPLY', nb.smooth(ri, 0.62, 0.7), nb.smooth(ri, 0.9, 0.84)))
    c = nb.mix(nb.math('MULTIPLY', ring_lo, 0.45), iris_c, nb.rgb(C.lin(C.mix_hex(iris[2], '#FFFFFF', 0.25))))
    # the white crescent low and to the outside, inside the seated rim so the head never hides it
    crescent = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(ri, 0.84, 0.88), nb.smooth(ri, 0.95, 0.91)),
                       nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', rx, side), 0.0, 0.4), nb.smooth(ry, -0.1, -0.4)))
    c = nb.mix(crescent, c, nb.rgb(C.lin('#F1F2F4')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.24), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.1), 1.15), 0.0)), 0.19, 0.16)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.26), nb.math('ADD', ry, 0.3), 0.0)), 0.075, 0.058)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', rx, side), 0.2, 0.9), 0.1)
    # a thick dark upper lash line under a slightly heavy lid
    lash = nb.smooth(nb.math('ADD', ry, outer), 0.33, 0.39)
    c = nb.mix(lash, c, nb.rgb(C.lin('#15121A')))
    lp = colours(pal if pal is not None else PALETTE)
    c = nb.mix(lid, c, nb.rgb(C.lin(C.shade_hex(lp['skin'], 0.92))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the horns (rigid props)
def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    """The horns (always worn) and Stormcrown's crown of three tall puffs (that variant's own prop)."""
    return H.build_horns(high, quick) + [W.build_crown(f'{"hi" if high else "lo"}_crown', high, quick)]


# ----------------------------------------------------------------------------- how the coat lies
def _hash3(p: np.ndarray, seed: float) -> np.ndarray:
    """A stable pseudo-random unit vector per point (the wool's curls must not change between calls)."""
    out = []
    for k, w in enumerate(((127.1, 311.7, 74.7), (269.5, 183.3, 246.1), (113.5, 271.9, 124.6))):
        h = np.sin(p @ v3(w) * 1.0 + seed * (k + 1)) * 43758.5453
        out.append(h - np.floor(h) - 0.5)
    return norm(np.stack(out, axis=1))


def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    L = W.layout()
    wf = z['field']
    pid = np.clip(wf['pid'], 0, None)
    # wool: little curls round each puff's centre, with a random lean (curly cotton, not combed fur)
    rel = p - L['pc'][pid]
    swirl = norm(np.cross(n, rel))
    g_wool = norm(swirl + 0.85 * _hash3(p * 90.0, 3.0) + 0.25 * norm(rel))
    # the face: combed back from the nose, turning down below the eyes (Puddlepup's spike)
    # round 3 (review): no starburst whorl between the eyes. The forehead combs straight up into the fringe, the
    # cheeks back, out and down; the two meet in a soft parting below the eyes
    g_up = norm(np.stack([x * 2.2, np.full(len(p), 0.15), np.ones(len(p))], axis=1))
    g_cheek = norm(np.stack([np.sign(x) * 0.9 + x * 2.0, np.full(len(p), 0.45), np.full(len(p), -0.7)], axis=1))
    wup = smooth(0.72, 0.79, zz)[:, None]
    g_head = norm(g_up * wup + g_cheek * (1 - wup))
    # the ears: down the leaf
    a_l, a_r = ear_frame(1)[1], ear_frame(-1)[1]
    g_ear = np.where((x > 0)[:, None], a_l[None], a_r[None])
    g_muz = norm(np.stack([np.sign(x) + 1e-6, np.zeros(len(p)), np.full(len(p), -0.35)], axis=1))
    g_head = np.where(z['muzzle'][:, None], g_muz, g_head)
    g = np.where(z['wool'][:, None], g_wool, g_head)
    g = np.where(z['ear'][:, None], g_ear, g)
    g = np.where((z['leg'] | z['hoof'])[:, None], np.tile(v3((0.0, -0.08, -1.0)), (len(p), 1)), g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


def head_lock_params(p, n):
    """Soft short fur on the face, the ears' backs and the back of the head (velvety, 4-details.png panels 1–2)."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.032)
    Wd = np.full(k, 0.0095)
    lift = np.full(k, _rad(0.5))
    L = np.where(z['cheek'], 0.034, L)
    L = np.where(z['ear'], 0.026, L)
    Wd = np.where(z['ear'], 0.008, Wd)
    near_eye = smooth(EYE_R * 1.12, EYE_R * 1.9, z['eye_d'])
    L = L * (0.5 + 0.5 * near_eye)
    Wd = Wd * (0.62 + 0.38 * near_eye)
    right, left = mouth_curve()
    md = np.minimum(S.polyline_dist(p[:, 0], p[:, 2], right), S.polyline_dist(p[:, 0], p[:, 2], left))
    mouth = (md < 0.007) & (p[:, 1] < -0.5 + HY) & (p[:, 2] < NOSE2[0][2]) & (p[:, 2] > 0.62)
    # round 2: the muzzle is softly furred again (round 1's bare muzzle read as glossy plastic), its locks short and
    # combed sideways (flow) so none lies across the smile
    L = np.where(z['muzzle'], 0.013, L)
    Wd = np.where(z['muzzle'], 0.0055, Wd)
    mouth = (md < 0.0042) & (p[:, 1] < -0.5 + HY) & (p[:, 2] < NOSE2[0][2] - 0.006) & (p[:, 2] > 0.62)
    skip = ~z['head'] | z['nose'] | z['ear_inner'] | (z['eye_d'] < EYE_R * 1.1) | mouth
    skip = skip | (np.abs(z['field']['d1'] - z['skin_d']) < 0.014)        # Nov 13: no locks on the skin/wool seam
    return np.where(skip, np.nan, Wd * 0.38), L, Wd, lift, z


def body_lock_params(p, n):
    """The wool's short curly locks (they stand up a little: a matted cotton texture), and the legs' short fur."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.022)
    Wd = np.full(k, 0.012)
    lift = np.full(k, _rad(5.0))
    sp = np.full(k, 0.0094)
    upper = p[:, 2] > 0.12
    L = np.where(z['leg'], np.where(upper, 0.034, 0.026), L)
    Wd = np.where(z['leg'], 0.0092, Wd)
    lift = np.where(z['leg'], _rad(3.0), lift)
    sp = np.where(z['leg'], 0.0092 * 0.6, sp)
    skip = z['head'] | z['hoof'] | z['sole'] | z['wool']
    return np.where(skip, np.nan, sp), L, Wd, lift, z


def card_params(p, n, layer: int):
    """Soft cards for the outline (they fade out face-on). Layer 0: the wool's fluffy halo, the legs' and the head's
    short fur. Layer 1: longer wisps on the crowns of the puffs and a fringe over each hoof."""
    z = zones(p, n)
    k = len(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    wool = z['wool']
    wf = z['field']
    L_ = W.layout()
    border = np.abs(wf['d1'] - z['skin_d']) < 0.012
    if layer == 0:
        # No cards on the wool: short wisps faded in toward the silhouette (Nov 12) still read as glassy white flakes in the
        # game, as round 2's did. No cards on the legs (Nov 12 review: pale, icy, glassy legs): their velvet matches the face's
        L = np.where(wool, 0.024, 0.024)
        Wd = np.where(wool, 0.03, 0.026)
        lift = np.where(wool, _rad(30), _rad(5))
        sp = np.where(wool, 0.03, 0.022)
        skip = (wool | (z['head'] & ~z['ear']) | z['muzzle'] | z['nose'] | (z['eye_d'] < 0.09)
                | z['ear_inner'] | z['hoof'] | z['sole'] | z['leg'] | (wool & W._in_face(p, 0.035))
                | (z['ear'] & (z['ear_m'] > -0.008)))
    else:
        cn = L_['n'][np.clip(wf['cid'], 0, None)]
        crown = np.zeros(k, bool)
        fringe = np.zeros(k, bool)          # Nov 13 review: the fetlock fringe read as a pale frayed sock
        L = np.where(crown, 0.056, 0.03)
        Wd = np.where(crown, 0.046, 0.026)
        lift = np.where(crown, _rad(42), _rad(-4))
        sp = np.where(crown, 0.07, 0.016)
        skip = ~(crown | fringe)
    skip = skip | border
    return np.where(skip, np.nan, sp), L, Wd, lift, z


# ----------------------------------------------------------------------------- paint (numpy, per source vertex)
def _runs(root: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Elements are runs of vertices sharing a root: (first vertex of each run, run lengths)."""
    if len(root) == 0:
        return np.zeros(0, int), np.zeros(0, int)
    change = np.any(np.diff(root, axis=0) != 0, axis=1)
    starts = np.concatenate([[0], np.nonzero(change)[0] + 1])
    lens = np.diff(np.concatenate([starts, [len(root)]]))
    return starts, lens


_PAINT: dict = {}


def _paint_inputs(ob: bpy.types.Object) -> dict:
    """What every palette's paint needs, evaluated once per source at the unique roots."""
    if ob.name in _PAINT:
        return _PAINT[ob.name]
    root = S.attr_array(ob, 'root').astype(np.float64)
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    lrand = S.attr_array(ob, 'lrand').astype(np.float64)
    if 'rootn' in ob.data.attributes:
        rn = S.attr_array(ob, 'rootn').astype(np.float64)
    else:
        _co, rn = S.mesh_arrays(ob)
    starts, lens = _runs(root)
    r = root[starts]
    z = zones(r)
    wf = z['field']
    L = W.layout()
    cid = np.clip(wf['cid'], 0, None)
    pid = np.clip(wf['pid'], 0, None)
    nr = rn[starts]
    # the wool's shading: creases between clumps (deep) and between puffs (soft), and how far into its clump a point
    # sits; the crown of each puff a touch brighter
    crease_c = smooth(0.03, 0.004, wf['d2'] - wf['d1'])
    crease_p = smooth(0.012, 0.002, wf['p2'] - wf['p1'])
    depth = smooth(0.98, 0.72, np.linalg.norm(r - L['c'][cid], axis=1) / L['R'][cid])
    cav = np.clip(np.maximum.reduce([crease_c, 0.55 * crease_p, 0.5 * depth]), 0, 1)
    # Stormcrown's gold: sunlight breaking through at the upper outer rim of each puff cluster (variant picture): a band
    # where the surface faces up but has turned away from its clump's centre; the clump's middle stays dark. Round 1 put
    # the gold in the crevices (rust), round 2 on the small puffs' tops (speckle)
    # round 3 (review): a thin gold rim tracing the outer edge of each sub-puff (where its surface turns side-on to the
    # puff's own outward direction) round a dark slate centre; never in the crevices
    own1 = np.ones(len(r))
    woolr = z['wool']
    lv1 = L['plevel'] == 1
    for k in np.unique(cid[woolr]):
        on = woolr & (cid == k)
        idx = np.nonzero(lv1 & (L['pclump'] == k))[0]
        if len(idx) == 0:
            continue
        d = np.linalg.norm(r[on][:, None, :] - L['pc'][idx][None], axis=2) - L['pr'][idx][None]
        j = idx[np.argmin(d, axis=1)]
        own1[on] = (nr[on] * norm(r[on] - L['pc'][j])).sum(1)
    facing = (nr * L['n'][cid]).sum(1)
    # round 1 put the gold in the crevices (rust), round 2 on the puffs' tops (lichen), round 3 thin rims on every
    # sub-puff (thin lines); Nov 12 a glowing ring along the seams read as electric crackle (the card rules out
    # lightning); Nov 13 a mask from the bumpy surface read as blotches. Now sunlight breaking through at the top and
    # outer rim of each clump, from the clump's geometry alone (W.rim_gold); the seams and the clumps' faces stay dark
    top = W.rim_gold(r, nr, L['c'][cid], L['n'][cid], wf['d2'] - wf['d1']) * woolr
    crown = smooth(0.55, 0.95, (nr * norm(r - L['pc'][pid])).sum(1)) * (1 - cav)
    rim = smooth(0.34, 0.04, facing) * (1 - 0.75 * crease_c) * smooth(-0.35, 0.0, facing)
    band = smooth(0.032, 0.012, wf['d2'] - wf['d1']) * (1 - smooth(0.008, 0.0, wf['d2'] - wf['d1']))
    vary = (np.sin(cid * 12.9898) * 43758.5453) % 1.0 - 0.5
    rep = lambda a: np.repeat(a, lens, axis=0)  # noqa: E731
    out = {'z': {k: rep(v) for k, v in z.items() if isinstance(v, np.ndarray) and v.ndim == 1},
           'cav': rep(cav), 'nz': rep(nr[:, 2]), 'crown': rep(crown), 'rim': rep(rim), 'band': rep(band), 'vary': rep(vary), 'top': rep(top),
           'kind': kind, 'tpos': tpos, 'lrand': lrand, 'root': root}
    _PAINT[ob.name] = out
    return out


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    """Per vertex: 'paint' (linear RGB, unshaded), 'shade' (a darker root and lighter tip on each lock), 'rough'
    (1, roughness, clearcoat). The brows, blush, nose, mouth and lids are added per pixel by `body_material`."""
    col = colours(pal)
    I = _paint_inputs(ob)
    z = I['z']
    root, kind, tpos, lrand = I['root'], I['kind'], I['tpos'], I['lrand']
    k = len(root)
    wool = z['wool'] > 0.5
    # wool
    rgb_w = lin(col['wool_lit'])[None] * (1 - 0.5 * I['cav'][:, None]) + lin(col['crease'])[None] * (0.5 * I['cav'][:, None])
    rgb_w = rgb_w * (1 - 0.45 * I['crown'][:, None]) + lin(col['puff_top'])[None] * (0.45 * I['crown'][:, None])
    rgb_w *= (1.0 + 0.05 * I['vary'])[:, None]
    # Nov 13 review: a flatter, slightly darker underside to the cloud
    rgb_w *= (1.0 - 0.07 * smooth(-0.2, -0.75, I['nz']))[:, None]
    glow = np.zeros(k)
    if col['rim']:
        gold = np.clip(0.95 * I['top'], 0, 1)
        rgb_w = rgb_w * (1 - gold[:, None]) + lin(col['rim'])[None] * gold[:, None]
        # the glow mask (VARIANT_ORM): the gold's core, a little tighter than the paint so the glow has a soft edge
        glow = smooth(0.18, 0.75, gold) * wool * smooth(0.025, 0.08, z['skin_d'])   # Nov 12: the bloom warmed the legs and face
    # skin: grey-blue fur, the pale muzzle, pink ear linings, dark hooves
    rgb_s = np.tile(lin(col['skin']), (k, 1))
    # round 2: the pale muzzle blends softly into the cheeks; the fur round the eyes a little lighter (4-details 1)
    # Nov 13 review: a near-white muzzle and chin (it measured barely lighter than the forehead)
    muz = np.maximum(ell_soft(root, MUZZLE[0], tuple(r * 1.16 for r in MUZZLE[1]), 0.25),
                     ell_soft(root, HEAD_ELLS[9][1], tuple(r * 1.25 for r in HEAD_ELLS[9][2]), 0.3)) * (z['head'] > 0.5)
    rgb_s = rgb_s * (1 - muz[:, None]) + lin(col['muzzle'])[None] * muz[:, None]
    ring = (smooth(EYE_R * 1.02, EYE_R * 1.3, z['eye_d']) * smooth(EYE_R * 2.2, EYE_R * 1.45, z['eye_d']) * (z['head'] > 0.5) * 0.16)
    rgb_s = rgb_s * (1 - ring[:, None]) + lin(C.mix_hex(col['skin'], '#FFFFFF', 0.5))[None] * ring[:, None]
    ear_in = (z['ear_inner'] > 0.5) & (kind < 0.5)
    # round 2: the pink fades out toward the fur rim and both ends
    pink_k = (smooth(0.74, 0.22, np.abs(z['ear_c'])) * smooth(0.2, 0.4, z['ear_u']) * smooth(0.93, 0.74, z['ear_u']))
    pink = lin(col['pink'])[None] * (0.92 + 0.08 * smooth(0.4, 0.0, np.abs(z['ear_c'])))[:, None]
    rgb_s = np.where(ear_in[:, None], rgb_s * (1 - pink_k[:, None]) + pink * pink_k[:, None], rgb_s)
    rgb_s = np.where((z['hoof'] > 0.5)[:, None], lin(col['hoof'])[None], rgb_s)
    rgb = np.where(wool[:, None], rgb_w, rgb_s)
    # gentle root-to-tip shading: at the atlas's texel size a strong one aliases into a grainy speckle (round 1)
    # round 3: very low contrast along each lock (the review still saw a salt-and-pepper speckle)
    shade = np.where(wool, 0.97 + 0.05 * tpos, 0.94 + 0.07 * tpos) + np.where(wool, 0.03, 0.02) * (lrand - 0.5)
    shade = np.where(kind < 0.5, 1.0, shade)
    is_lock = kind > 0.5
    rough = np.where(wool, 0.97, np.where(is_lock, 0.5 + 0.25 * np.abs(tpos - 0.45), 0.66))      # round 3: matte wool
    coat = np.where(wool, 0.0, np.where(is_lock, 0.12, 0.06))
    rough = np.where(ear_in, 0.5, rough)
    coat = np.where(ear_in, 0.12, coat)
    nose = ell_soft(root, tuple(NOSE_C), tuple(r * 1.1 for r in NOSE_R), 0.08)
    glossy = np.maximum(nose, (z['hoof'] > 0.5) * 1.0)
    # round 2: a matte nose (it read as a shiny blob); the hooves keep a soft gloss
    rough = rough * (1 - glossy) + np.where(z['hoof'] > 0.5, 0.64, 0.52) * glossy
    coat = coat * (1 - glossy) + np.where(z['hoof'] > 0.5, 0.05, 0.12) * glossy
    # Nov 12 (review: the legs read pale, icy and glassy): the leg fur as matte as the face's velvet
    legs = (z['leg'] > 0.5) & (z['hoof'] < 0.5)
    rough = np.where(legs, np.maximum(rough, 0.8), rough)
    coat = np.where(legs, 0.0, coat)
    return {'paint': rgb, 'shade': shade, 'rough': np.stack([np.ones(k), rough, coat], axis=1), 'glow': glow}


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
    """'paint' (base), 'rough', 'shade' and, per variant, `U.variant_attr(vid, ID)` on every source; the horns' cream."""
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'shade', a['shade'])
        for vid, pal in VARIANTS.items():
            va = paint_arrays(ob, pal)
            S.set_colour_attr(ob, U.variant_attr(vid, ID), va['paint'])
            short = U.variant_short(vid, ID)
            if short in VARIANT_ORM and VARIANT_ORM[short].get('glow'):
                # Nov 12: the variant's own glow mask (its gold), for its own ORM's alpha
                S.add_attr(ob, f'glow_{short}', va['glow'])
    for ob in props:
        if 'horn' in ob.data.attributes:
            rgb, rc = H.horn_paint(ob, HORN_HEX, '#C2AB80', '#D9C8A4', '#FAF4E6')
            S.set_colour_attr(ob, 'paint', rgb)
            S.set_colour_attr(ob, 'rough', rc)
            for vid in VARIANTS:
                S.set_colour_attr(ob, U.variant_attr(vid, ID), rgb)
            continue
        # the crown: only Stormcrown wears it; every pass paints it in that variant's wool
        storm = VARIANTS['stormcrown-nimbusheep']
        col = colours(storm)
        rgb, gold = W.crown_paint(ob, col['wool'], col['crease'], col['rim'])
        n = len(ob.data.vertices)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', np.tile(v3((1.0, 0.88, 0.0)), (n, 1)))
        for vid in VARIANTS:
            S.set_colour_attr(ob, U.variant_attr(vid, ID), rgb)
            short = U.variant_short(vid, ID)
            if short in VARIANT_ORM and VARIANT_ORM[short].get('glow'):
                S.add_attr(ob, f'glow_{short}', smooth(0.18, 0.75, gold))


# ----------------------------------------------------------------------------- paint (nodes: the crisp details, per pixel)
def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def body_material(name: str, attr: str, pal: dict, marks=None) -> bpy.types.Material:
    """Emission = the painted attribute × each lock's shade, with the face's marks per pixel: the brows, the blush, the
    nose, the smile line, the closed lids and their lash lines."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 0.5)
    c = nb.attribute(attr).outputs['Color']
    shade = nb.attribute('shade').outputs['Fac']
    c = nb.mix(1.0, c, nb.comb(shade, shade, shade), blend='MULTIPLY')
    brow = None
    for s in (1, -1):
        for bc, br in BROWS:
            e = _ell(nb, pos, (bc[0] * s, bc[1], bc[2]), br, 0.4)
            brow = e if brow is None else nb.math('MAXIMUM', brow, e)
    c = nb.mix(brow, c, nb.rgb(C.lin(col['brow'])))
    blush = None
    for s in (1, -1):
        e = _ell(nb, pos, (BLUSH_C[0] * s, BLUSH_C[1], BLUSH_C[2]), (0.04, 0.07, 0.028), 0.7)
        blush = e if blush is None else nb.math('MAXIMUM', blush, e)
    c = nb.mix(nb.math('MULTIPLY', blush, pal.get('blush_k', 0.42)), c, nb.rgb(C.lin(col['blush'])))
    nose = nb.math('MAXIMUM', _ell(nb, pos, tuple(NOSE_C), tuple(r * 1.06 for r in NOSE_R), 0.06),
                   _ell(nb, pos, NOSE2[0], tuple(r * 1.1 for r in NOSE2[1]), 0.08))
    c = nb.mix(nose, c, nb.rgb(C.lin(col['nose'])))
    # a soft highlight on the top of the nose (1-hero.png)
    hl = nb.math('MULTIPLY', _ell(nb, pos, (0.0, -0.596 + HY, 0.708), (0.02, 0.02, 0.008), 0.6), 0.35)
    c = nb.mix(hl, c, nb.rgb(C.lin('#8C909C')))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.8, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(col['mouth'])))
    lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
    c = nb.mix(nb.math('MULTIPLY', lid, 0.2), c, nb.rgb((0.0, 0.0, 0.0)))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin('#15121A')))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the rig (plans/quadruped.py)
def rig_p() -> dict:
    r0, a, _b, _n = ear_frame(1)
    return {
        'hip': (0.0, 0.22, 0.44),
        'chest': (0.0, -0.2, 0.48),
        'head_c': (0.0, -0.37 + HY, 0.78),
        'head_r': 0.2,
        'ear_base': tuple(map(float, r0 + a * EAR_LEN * 0.18)),
        'ear_dir': tuple(map(float, a)),
        'ear_len': EAR_LEN * 0.82,
        'tail_base': TAIL_BASE,
        'tail_dir': TAIL_DIR,
        'tail_len': TAIL_LEN,
        'tail_bones': 2,
        'legs': {leg: (lx, ly, 0.42 if leg[0] == 'F' else 0.4) for leg, (lx, ly) in LEGS.items()},
        'knee_back': 0.02,
        'ankle_z': 0.068,
        'foot_len': 0.062,
        'leg_radius': 0.075,
        'stride': 0.12,
        'hooves': True,
        'ko_leg_fold': 0.4,                 # ko folds the legs only this much, so they stay outside the wool (round 3b review)
        'strike_style': 'charge',           # head low, horns first (PROMPTS.md: the attack lowers the head)
        'props': [{'name': 'horns', 'parent': 'head', 'head': (0.0, -0.3 + HY, 0.95), 'tail': (0.0, -0.3 + HY, 1.06)}],
    }


def ear_zone(p: np.ndarray):
    z = zones(p)
    return z['ear'], z['ear_u']


def ear_weights(p: np.ndarray, u: np.ndarray) -> dict[str, np.ndarray]:
    """Head → ear.1 → ear.2 along the leaf: the part inside the head stays with it."""
    w2 = smooth(0.5, 0.9, u)
    w1 = (1 - w2) * smooth(0.14, 0.36, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def _spine_segments() -> list[tuple[str, np.ndarray, np.ndarray]]:
    """The trunk's bones as segments, as plans/quadruped.rig_specs places them (size_k = HEIGHT_UNITS / 150)."""
    P = rig_p()
    sk = HEIGHT_UNITS / U.UNITS_PER_METRE
    hip, chest, hc, hr = v3(P['hip']), v3(P['chest']), v3(P['head_c']), P['head_r']
    a = hip + v3((0, -0.12 * sk, 0.02 * sk))
    b = chest + v3((0, 0.06 * sk, -0.01 * sk))
    c = chest + v3((0, -0.12 * sk, 0.0))
    d = hc + v3((0, 0.06 * sk, -hr * 0.55))
    return [('hips', hip, a), ('spine', a, b), ('chest', b, c), ('neck', c, d), ('head', d, hc + v3((0, 0.0, hr)))]


def clump_weights(names: list[str]) -> dict[int, dict[str, float]]:
    """Per wool clump, the trunk bones its centre would follow (the nearest two, by distance to each bone): every puff
    of a clump then moves rigidly as one lump (round 2 review: the neck and shoulder wool stretched into smooth sheets in
    strike). The cap and the fringe ride the head."""
    L = W.layout()
    segs = [(nm, a, b) for nm, a, b in _spine_segments() if nm in names]
    out = {}
    for k, (c, region) in enumerate(zip(L['c'], L['region'])):
        if region in (W.REGIONS['cap'], W.REGIONS['fringe']) and 'head' in names:
            out[k] = {'head': 1.0}
            continue
        if region == W.REGIONS['tail']:
            continue
        if region == W.REGIONS['collar'] and 'chest' in names:
            out[k] = {'chest': 1.0}
            continue
        ds = []
        for nm, a, b in segs:
            if nm in ('neck', 'head'):
                continue
            ab = b - a
            t = float(np.clip((c - a) @ ab / max(ab @ ab, 1e-9), 0, 1))
            ds.append((float(np.linalg.norm(c - (a + t * ab))), nm))
        ds.sort()
        out[k] = {ds[0][1]: 1.0}          # round 3b: one bone per clump (two blended stretched the neck wool into sheets)
    return out


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    z = zones(co)
    out = []
    # the wool: each clump rigid on its trunk bones (the build's weight smoothing then softens the seams in the creases)
    cw = clump_weights(names)
    cid = z['field']['cid'] if 'field' in z else W.sample(co)['cid']
    wool = z['wool'] & ~z['tail'] & (cid >= 0)
    if wool.any():
        bones = sorted({nm for w in cw.values() for nm in w})
        cols = {nm: np.zeros(int(wool.sum())) for nm in bones}
        ids = cid[wool]
        for k, w in cw.items():
            on = ids == k
            for nm, v in w.items():
                cols[nm][on] = v
        miss = np.ones(int(wool.sum()), bool)
        for k in cw:
            miss &= ids != k
        if miss.any() and 'chest' in cols:
            cols['chest'][miss] = 1.0
        out.append((wool, cols))
    for s, tag in ((1, 'L'), (-1, 'R')):
        on = z['ear'] & (np.sign(co[:, 0]) == s)
        if on.any():
            w = ear_weights(co[on], z['ear_u'][on])
            out.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    if z['tail'].any():
        out.append((z['tail'], U.chain_weights(co[z['tail']], TAIL_PTS, ['tail.1', 'tail.2'], 'hips')))
    # the hooves are rigid on their hoof bones; the fetlock fur above blends from the shin into them
    for leg, (lx, ly) in LEGS.items():
        near = np.hypot(co[:, 0] - lx, co[:, 1] - ly + 0.03) < 0.13
        low = near & ~z['wool'] & (co[:, 2] < HOOF_TOP + 0.03)
        if low.any() and f'foot.{leg}' in names and f'shin.{leg}' in names:
            wf = smooth(HOOF_TOP + 0.03, HOOF_TOP - 0.004, co[low, 2])
            out.append((low, {f'foot.{leg}': wf, f'shin.{leg}': 1.0 - wf}))
    return out


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    return [U.rigid(np.ones(len(co), bool), 'prop.horns' if 'prop.horns' in names else 'head')]


CLIP_CALM = {
    '*': {'ear': 0.7, 'tail': 0.6},
    'ko': {'ear': 0.25, 'tail': 0.4},
    'hit_heavy': {'ear': 0.35, 'tail': 0.5},
    'win': {'ear': 0.45},
    # Nov 12 (owner: a stretched strip behind the head in strike): the charge's head and neck turn at 40%, so the
    # cap's back stays near the shoulders' wool (a test pose at 100% pulled a long blade of wool off the cap's back; at
    # 55% it was gone, but the review still saw a sheet; blending the clumps round the cap between head and trunk smoothed
    # the back into a tent, and riding them on the neck bone made the sheet longer);
    # the lean, the hips' drive and the legs keep their full motion
    'strike': {'ear': 0.4, 'headneck': 0.4},
}


def calm_group(bone: str) -> str | None:
    """CLIP_CALM's groups: the default ear and tail chains, plus 'headneck' (the head and the neck bones), so strike
    can calm the charge's head drop alone."""
    if bone == 'head' or bone == 'neck' or bone.startswith('neck.'):
        return 'headneck'
    g = bone.split('.')[0]
    return g if '.' in bone and g in ('ear', 'tail') else None

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the pupil, the blue-grey iris, the catchlights and a heavy upper '
             'lash line (the sleepy look) baked into the body atlas; the brows, blush, nose and the small "w" smile are '
             'baked into the body. No face sheet and no morphs: expressions in clips\' `faces` are hints only. Blinking '
             'scales the blink bones (play `blink` over any clip): each lens squashes onto the closed lid\'s lash line and '
             'sinks into the head, showing the closed lid sculpted and painted on the skin under it. The drizzle and the '
             'happy rainbow (#F28F8F #F7D36B #8FD1A8 #8FB8F2) are runtime effects from socket_back.')

REVIEW = {
    'centre': (0.0, -0.01, 0.56),
    'size': 1.8,                         # round 2: the ko and strike frames cropped the body
    'head': ((0.0, -0.4 + HY, 0.8), 0.86),
}
