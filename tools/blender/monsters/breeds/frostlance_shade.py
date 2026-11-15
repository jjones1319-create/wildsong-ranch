"""Frostlance's per-pixel bake materials (frostlance_ultra.py): the white freckles and snowflakes on the teal, the
mid-blue mottling under the waterline and the cheeks' tiny freckles, the face (the closed smile, the brows, the closed
lids' lash lines under the lenses), the eye lenses, and the props' frost, snowflakes and the tusk's ice.

Freckles are 3D Voronoi dots in object space (a random size and presence per cell: round, crisp, never a lattice), at
least 5 mm across so they never shimmer at phone size; the snowflakes are six-armed stars (lib.marks, make_marks), the
big ones with six short arms between. Masks from the paint (`teal`, `band`, `cheek`) gate where each layer lies.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import marks as MK
from lib.nodes import NB, new_mat
from monsters.breeds import frostlance_form as F
from monsters.breeds import frostlance_paint as FP

# freckle layers: (Voronoi scale per metre, radius min, max in cell units, presence threshold, strength)
# round 1: two to three times more tiny white speckles between the snowflakes (the third layer, the second denser)
FRECKLES = [(22.0, 0.12, 0.24, 0.5, 1.0), (55.0, 0.14, 0.22, 0.4, 0.9), (85.0, 0.17, 0.24, 0.42, 0.85)]
MOTTLE = (30.0, 0.15, 0.34, 0.42, 0.7)
MOTTLE_EDGE = (38.0, 0.2, 0.4, 0.25, 0.85)
SPECKS = (95.0, 0.17, 0.26, 0.5, 0.65)
CHEEK_DOTS = (42.0, 0.16, 0.32, 0.5, 0.7)   # polish: the larger blue dapples on the cheeks (3-faces neutral)


def _rgb(nb: NB, h: str):
    return nb.rgb(C.lin(h))


def dots(nb: NB, pos, layer, seed: float = 0.0):
    """A field of round dots: one per Voronoi cell where the cell's random number passes the threshold, each its own size."""
    scale, r0, r1, thr, k = layer
    n = nb.new('ShaderNodeTexVoronoi', feature='F1')
    nb.put(n.inputs['Vector'], nb.vmath('ADD', pos, (seed, 0.37 * seed, 0.71 * seed)) if seed else pos)
    n.inputs['Scale'].default_value = scale
    n.inputs['Randomness'].default_value = 1.0
    r, g, _b = nb.sep_rgb(n.outputs['Color'])
    rad = nb.math('ADD', r0, nb.math('MULTIPLY', r, r1 - r0))
    m = MK._smooth(nb, n.outputs['Distance'], nb.math('MULTIPLY', rad, 1.12), nb.math('MULTIPLY', rad, 0.86))
    on = MK._smooth(nb, g, thr, thr + 0.03)
    return nb.math('MULTIPLY', nb.math('MULTIPLY', m, on), k)


FLAKE_GROUP = 'WS_FrostlanceSnowflake'


def soft_blots(nb: NB, pos, layer, seed: float = 0.0):
    """Soft-edged blotches: one per Voronoi cell where the cell's number passes the threshold, its edge a wide ramp."""
    scale, r0, r1, thr, k = layer
    n = nb.new('ShaderNodeTexVoronoi', feature='F1')
    nb.put(n.inputs['Vector'], nb.vmath('ADD', pos, (seed, 0.29 * seed, 0.61 * seed)))
    n.inputs['Scale'].default_value = scale
    n.inputs['Randomness'].default_value = 1.0
    r, g, _b = nb.sep_rgb(n.outputs['Color'])
    rad = nb.math('ADD', r0, nb.math('MULTIPLY', r, r1 - r0))
    m = MK._smooth(nb, n.outputs['Distance'], nb.math('MULTIPLY', rad, 1.5), nb.math('MULTIPLY', rad, 0.5))
    return nb.math('MULTIPLY', nb.math('MULTIPLY', m, MK._smooth(nb, g, thr, thr + 0.08)), k)


def flake_group() -> bpy.types.ShaderNodeTree:
    """A snowflake lying on the surface (one node group, instanced per flake): six arms tapering to their points, a small
    hexagonal heart, and on each arm two pairs of side branches at 60 degrees (`Branches` 0 leaves them off). The angle is
    folded into one twelfth of the flake, so every arm and branch is the same few nodes."""
    g = bpy.data.node_groups.get(FLAKE_GROUP)
    if g is not None:
        return g
    g, nb, gi, go = MK._group(FLAKE_GROUP, [
        ('Position', 'NodeSocketVector', None), ('Centre', 'NodeSocketVector', None), ('Normal', 'NodeSocketVector', (0.0, 0.0, 1.0)),
        ('Tangent', 'NodeSocketVector', (1.0, 0.0, 0.0)), ('Radius', 'NodeSocketFloat', 0.02), ('Width', 'NodeSocketFloat', 0.11),
        ('Branches', 'NodeSocketFloat', 1.0), ('Depth', 'NodeSocketFloat', 0.02)])
    n = nb.vmath('NORMALIZE', gi.outputs['Normal'])
    d = nb.vmath('SUBTRACT', gi.outputs['Position'], gi.outputs['Centre'])
    h = nb.vmath('DOT_PRODUCT', d, n)
    dp = nb.vmath('SUBTRACT', d, nb.vmath('SCALE', n, scale=h))
    t = nb.vmath('NORMALIZE', nb.vmath('SUBTRACT', gi.outputs['Tangent'], nb.vmath('SCALE', n, scale=nb.vmath('DOT_PRODUCT', gi.outputs['Tangent'], n))))
    b = nb.vmath('CROSS_PRODUCT', n, t)
    R = gi.outputs['Radius']
    x = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', dp, t), R)
    y = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', dp, b), R)
    r = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    th = nb.math('ADD', nb.math('ARCTAN2', y, x), math.pi)
    m = nb.math('FLOORED_MODULO', th, math.pi / 3)
    u = nb.math('MINIMUM', m, nb.math('SUBTRACT', math.pi / 3, m))
    along = nb.math('MULTIPLY', r, nb.math('COSINE', u))
    across = nb.math('MULTIPLY', r, nb.math('SINE', u))
    w = gi.outputs['Width']
    wa = nb.math('MULTIPLY', w, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', 0.45, along)))
    arm = nb.math('MULTIPLY', MK._smooth(nb, across, nb.math('MULTIPLY', wa, 1.25), nb.math('MULTIPLY', wa, 0.75)),
                  MK._smooth(nb, along, 1.03, 0.94))
    heart = MK._smooth(nb, r, 0.24, 0.18)
    out = nb.math('MAXIMUM', arm, heart)
    wb = nb.math('MULTIPLY', w, 0.72)
    for s0, ln in ((0.42, 0.34), (0.68, 0.22)):
        ra = nb.math('SUBTRACT', along, s0)
        tb = nb.math('ADD', nb.math('MULTIPLY', ra, 0.5), nb.math('MULTIPLY', across, 0.866))
        db = nb.math('ABSOLUTE', nb.math('ADD', nb.math('MULTIPLY', ra, -0.866), nb.math('MULTIPLY', across, 0.5)))
        br = nb.math('MULTIPLY', MK._smooth(nb, db, nb.math('MULTIPLY', wb, 1.3), nb.math('MULTIPLY', wb, 0.7)),
                     nb.math('MULTIPLY', MK._smooth(nb, tb, -0.02, 0.03), MK._smooth(nb, tb, ln, ln - 0.06)))
        out = nb.math('MAXIMUM', out, nb.math('MULTIPLY', br, gi.outputs['Branches']))
    deep = MK._smooth(nb, nb.math('ABSOLUTE', h), gi.outputs['Depth'], nb.math('MULTIPLY', gi.outputs['Depth'], 0.5))
    nb.link(nb.math('MULTIPLY', out, deep), go.inputs['Mask'])
    return g


def flakes(nb: NB, pos, items):
    """Snowflakes, each (centre, normal, tangent, radius, big): six arms and a hexagonal heart; the big ones branched
    (2-turnaround, 4-details 6: dendritic flakes), the small ones plain (their branches would be under a texel)."""
    masks = []
    for c, n, t, r, big in items:
        masks.append(MK._instance(nb, flake_group(), pos, {'Centre': c, 'Normal': n, 'Tangent': t, 'Radius': r,
                                                          'Width': 0.085 if big else 0.13, 'Branches': 1.0 if big else 0.0,
                                                          'Depth': max(0.012, r)}))
    return MK.union(nb, masks)


def _local(nb: NB, pos, c, xa, ya):
    d = nb.vmath('SUBTRACT', pos, tuple(c))
    return nb.vmath('DOT_PRODUCT', d, tuple(xa)), nb.vmath('DOT_PRODUCT', d, tuple(ya))


def face_marks(nb: NB, pos) -> dict:
    """The face on the skin (2-turnaround front, 3-faces neutral): the closed smile (a curve curling up into small tucked
    corners under the muzzle), the brows (short round arches on the teal just above the eyes), and under each lens the
    closed lid's lash line."""
    x, y, z = nb.sep(pos)
    front = MK._smooth(nb, y, -0.3, -0.34)
    a = nb.math('DIVIDE', x, F.MOUTH_W)
    a2 = nb.math('MULTIPLY', a, a)
    # round 1: narrower, its corners tucked: past the ends the curve turns up steeply (a4, a8 terms)
    a4 = nb.math('MULTIPLY', a2, a2)
    zs = nb.math('ADD', F.MOUTH_Z, nb.math('ADD', nb.math('MULTIPLY', 0.008, a2),
                                           nb.math('ADD', nb.math('MULTIPLY', 0.003, a4), nb.math('MULTIPLY', 0.004, nb.math('MULTIPLY', a4, a4)))))
    th = nb.math('SUBTRACT', 0.0031, nb.math('MULTIPLY', 0.0012, nb.math('MINIMUM', a2, 1.3)))
    smile = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', z, zs)), nb.math('MULTIPLY', th, 1.3), nb.math('MULTIPLY', th, 0.7))
    smile = nb.math('MULTIPLY', nb.math('MULTIPLY', smile, MK._smooth(nb, nb.math('ABSOLUTE', a), 1.26, 1.16)), front)
    brow = lid = None
    for s in (1, -1):
        c, xa, ya, _lk = F.eye_frame(s)
        ex, ey = _local(nb, pos, c, xa / (F.EYE_R * F.EYE_SHAPE[0]), ya / (F.EYE_R * F.EYE_SHAPE[1]))
        # the brow: a short, round arch above the eye, tapering at both ends (round 1: rounder and nearer the eye, so in
        # ko it reads as a brow, not a fourth dash beside the closed lids)
        bx = nb.math('DIVIDE', ex, 0.62)
        bx2 = nb.math('MULTIPLY', bx, bx)
        arc = nb.math('ADD', 1.36, nb.math('MULTIPLY', 0.24, nb.math('SUBTRACT', 1.0, bx2)))
        bth = nb.math('SUBTRACT', 0.12, nb.math('MULTIPLY', 0.08, bx2))
        b = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', ey, arc)), nb.math('MULTIPLY', bth, 1.25), nb.math('MULTIPLY', bth, 0.7))
        b = nb.math('MULTIPLY', b, MK._smooth(nb, nb.math('ABSOLUTE', bx), 1.0, 0.85))
        brow = b if brow is None else nb.math('MAXIMUM', brow, b)
        # the closed lid (3-faces blink): a gently curved line across the eye, its middle a little low
        xn = nb.math('DIVIDE', ex, 0.92)
        larc = nb.math('SUBTRACT', nb.math('MULTIPLY', 0.12, nb.math('MULTIPLY', xn, xn)), 0.16)
        ln = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', ey, larc)), 0.1, 0.055)
        ln = nb.math('MULTIPLY', ln, MK._smooth(nb, nb.math('ABSOLUTE', xn), 1.0, 0.9))
        lid = ln if lid is None else nb.math('MAXIMUM', lid, ln)
    face = MK._smooth(nb, y, -0.18, -0.24)
    return {'smile': smile, 'brow': nb.math('MULTIPLY', brow, face), 'lid': nb.math('MULTIPLY', lid, face)}


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the paint with, per pixel: a faint skin mottle, the dappled band of mid-blue spots under the teal's edge
    and the cheeks' freckles, the belly's faint grooves, the white freckles, speckles and snowflakes on the teal, the face."""
    col = FP.colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    c = nb.attribute(attr).outputs['Color']
    teal = nb.attribute('teal').outputs['Fac']
    band = nb.attribute('band').outputs['Fac']
    edge = nb.attribute('edge').outputs['Fac']
    cheek = nb.attribute('cheek').outputs['Fac']
    pleat = nb.attribute('pleat').outputs['Fac']
    clear = nb.attribute('clear').outputs['Fac']
    # smooth whale skin with faint mottling (4-details 1): a soft brightness drift, never a lattice
    drift = nb.math('MULTIPLY', nb.math('SUBTRACT', nb.noise(pos, 11.0, 2.0, 0.5), 0.5), 0.16)
    c = nb.mix(nb.math('MAXIMUM', drift, 0.0), c, _rgb(nb, col['belly']))
    c = nb.mix(nb.math('MAXIMUM', nb.math('MULTIPLY', drift, -1.0), 0.0), c, _rgb(nb, col['back_deep']))
    # round 3: the teal back's soft mottling (4-details 6): darker patches and lighter blotches behind the snowflakes,
    # broad soft-edged cells, not an airbrushed gradient
    tm = MK._smooth(nb, nb.attribute('teal').outputs['Fac'], 0.5, 0.95)
    c = nb.mix(nb.math('MULTIPLY', soft_blots(nb, pos, (13.0, 0.3, 0.55, 0.42, 0.55), 0.7), tm), c, _rgb(nb, col['teal_dark']))
    c = nb.mix(nb.math('MULTIPLY', soft_blots(nb, pos, (19.0, 0.25, 0.45, 0.5, 0.4), 3.3), tm), c, _rgb(nb, col['back_soft']))
    # round 1: the teal's edge is a dappled band of mid-blue spots, dense at the edge and thinning below it
    spots = nb.math('MAXIMUM', nb.math('MULTIPLY', dots(nb, pos, MOTTLE, 0.4), band), nb.math('MULTIPLY', dots(nb, pos, MOTTLE_EDGE, 0.9), edge))
    c = nb.mix(spots, c, _rgb(nb, col['mottle']))
    c = nb.mix(nb.math('MULTIPLY', dots(nb, pos, SPECKS, 1.3), cheek), c, _rgb(nb, col['speck']))
    c = nb.mix(nb.math('MULTIPLY', dots(nb, pos, CHEEK_DOTS, 4.7), cheek), c, _rgb(nb, col['mottle']))
    # the belly's faint lengthwise grooves (1-hero): a pale blue line in each (the carving gives them their shading)
    px = nb.sep(pos)[0]
    gv = nb.math('POWER', nb.math('ADD', 0.5, nb.math('MULTIPLY', 0.5, nb.math('COSINE', nb.math('MULTIPLY', px, 2 * math.pi / FP.PLEAT_GAP)))), 10.0)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', gv, pleat), 0.3), c, _rgb(nb, col['body']))
    tk = MK._smooth(nb, teal, 0.45, 0.9)
    fr = None
    for i, layer in enumerate(FRECKLES):
        d = dots(nb, pos, layer, 2.1 + i)
        fr = d if fr is None else nb.math('MAXIMUM', fr, d)
    fl = flakes(nb, pos, (marks or {}).get('body', []))
    if fl is not None:
        fr = nb.math('MAXIMUM', fr, fl)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', fr, tk), clear), c, _rgb(nb, col['freckle']))
    fm = face_marks(nb, pos)
    c = nb.mix(fm['brow'], c, _rgb(nb, col['brow']))
    c = nb.mix(fm['smile'], c, _rgb(nb, col['smile']))
    c = nb.mix(fm['lid'], c, _rgb(nb, col['lid']))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """A big glossy eye (4-details 2): a navy ring round a blue iris, lighter in its lower half, with fine fibres; a big
    pupil (round 1: about 65% of the iris); white showing below and at the outer side; a big catchlight high on one side
    and a small one low on the other; a heavy near-black lash line along the top."""
    col = FP.colours(pal or {'body': '#D8EEF7', 'belly': '#F5FBFE', 'accent': '#1F7A8C', 'eye': '#1B263B'})
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.14, 0.5))
        nb.output(em.outputs[0])
        return m
    x, y, _z = nb.sep(nb.attribute('eyeuv').outputs['Vector'])
    side = nb.attribute('eye_side').outputs['Fac']
    cx = nb.math('MULTIPLY', side, -0.04)
    ix, iy = nb.math('SUBTRACT', x, cx), nb.math('SUBTRACT', y, 0.08)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), 0.86)
    r = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    low = MK._smooth(nb, nb.math('DIVIDE', iy, 0.7), -0.1, -0.8)
    iris = nb.mix(low, _rgb(nb, col['iris']), _rgb(nb, col['iris_light']))
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 28.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', MK._smooth(nb, ri, 0.64, 0.72), MK._smooth(nb, ri, 0.94, 0.84)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.16), iris, _rgb(nb, col['iris_ring']))
    c = nb.mix(MK._smooth(nb, ri, 0.67, 0.63), iris, _rgb(nb, col['pupil']))
    c = nb.mix(MK._smooth(nb, ri, 0.86, 0.96), c, _rgb(nb, col['iris_ring']))
    c = nb.mix(MK._smooth(nb, ri, 1.0, 1.04), c, _rgb(nb, col['sclera']))
    r_in = nb.math('SUBTRACT', 0.9, nb.math('MULTIPLY', MK._smooth(nb, y, -0.2, 0.7), 0.2))
    lidm = nb.math('MULTIPLY', MK._smooth(nb, r, r_in, nb.math('ADD', r_in, 0.035)), MK._smooth(nb, y, -0.45, 0.05))
    c = nb.mix(lidm, c, _rgb(nb, col['lid']))
    # the catchlights on the same side in both eyes (the key light: 1-hero, 4-details 2; eyeuv x is the model's +X in both)
    big = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, 0.24), nb.math('SUBTRACT', iy, 0.26), 0.0)), 0.21, 0.175)
    small = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, 0.26), nb.math('ADD', iy, 0.24), 0.0)), 0.09, 0.065)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """The props per pixel: on the fins and the fluke white freckles and a few snowflakes on the teal (4-details 3, 4), and
    (round 1) darker blue lines between the ice shards, drawn in each slab's own 2D frame (slab_uv); on the tusk a thin
    near-white highlight along the ridge's crest (its helix phase, hcos) and a few faint crack lines (4-details 5)."""
    col = FP.colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    c = nb.attribute(attr).outputs['Color']
    part = nb.attribute('part').outputs['Fac']
    frost = nb.attribute('frost').outputs['Fac']
    groove = nb.attribute('groove').outputs['Fac']
    hcos = nb.attribute('hcos').outputs['Fac']
    shade = nb.attribute('shade').outputs['Fac']
    suv = nb.attribute('slab_uv').outputs['Vector']
    slab = nb.math('LESS_THAN', part, 2.5)
    tusk = nb.math('SUBTRACT', 1.0, slab)
    inner = nb.math('MULTIPLY', slab, MK._smooth(nb, frost, 0.55, 0.15))
    fr = nb.math('MAXIMUM', dots(nb, pos, FRECKLES[0], 5.3), dots(nb, pos, FRECKLES[1], 6.1))
    fl = flakes(nb, pos, (marks or {}).get('props', []))
    if fl is not None:
        fr = nb.math('MAXIMUM', fr, fl)
    c = nb.mix(nb.math('MULTIPLY', fr, inner), c, _rgb(nb, col['freckle']))
    # round 1: darker blue lines between the shards, from each notch in toward the teal (the layered ice of 4-details 3)
    sh = MK.union(nb, [MK.line(nb, suv, a, b, 0.0013, 0.4) for a, b in (marks or {}).get('shards', [])])
    if sh is not None:
        c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', sh, slab), 0.75), c, _rgb(nb, col['mottle']))
    # faint crystal veins in the frost only near the shards (round 1: long noise streaks smeared across the fluke)
    n = nb.noise(pos, 70.0, 0.6, 0.5)
    v = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', n, 0.5)), 0.018, 0.006)
    fv = nb.math('MULTIPLY', nb.math('MULTIPLY', v, MK._smooth(nb, frost, 0.6, 0.95)), nb.math('MULTIPLY', slab, 0.3))
    c = nb.mix(fv, c, _rgb(nb, col['frost_tip']))
    # the tusk: a thin near-white line along the ridge's crest (cos of its helix phase near -1), brightest on the lit side,
    # and a few faint crack lines through the ice
    crest = nb.math('MULTIPLY', MK._smooth(nb, hcos, -0.93, -0.99), nb.math('MULTIPLY', tusk, nb.math('SUBTRACT', 0.9, nb.math('MULTIPLY', shade, 0.4))))
    c = nb.mix(crest, c, _rgb(nb, col['ice_ridge']))
    # round 3: 4 faint white crack streaks running lengthwise inside the ice, and a thin glassy reflection along its top
    tcos = nb.attribute('tcos').outputs['Fac']
    tsin = nb.attribute('tsin').outputs['Fac']
    su = nb.attribute('su').outputs['Fac']
    # polish: 4 short, broken, wandering faint cracks (the long straight stripes read as a seam or tape)
    streaks = None
    for ang, a0, a1, w, ph in ((40.0, 0.12, 0.3, 0.006, 0.3), (140.0, 0.34, 0.5, 0.005, 1.9), (215.0, 0.08, 0.24, 0.006, 3.1),
                               (300.0, 0.45, 0.62, 0.005, 4.4)):
        al = nb.math('ADD', math.radians(ang), nb.math('MULTIPLY', 0.35, nb.math('SINE', nb.math('ADD', nb.math('MULTIPLY', su, 22.0), ph))))
        dt = nb.math('ADD', nb.math('MULTIPLY', tcos, nb.math('COSINE', al)), nb.math('MULTIPLY', tsin, nb.math('SINE', al)))
        ln = MK._smooth(nb, dt, 1.0 - 2.2 * w, 1.0 - w)
        ln = nb.math('MULTIPLY', ln, nb.math('MULTIPLY', MK._smooth(nb, su, a0, a0 + 0.04), MK._smooth(nb, su, a1, a1 - 0.05)))
        streaks = ln if streaks is None else nb.math('MAXIMUM', streaks, ln)
    broken = MK._smooth(nb, nb.noise(pos, 38.0, 0.5, 0.5), 0.4, 0.5)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', streaks, broken), nb.math('MULTIPLY', tusk, 0.45)), c, _rgb(nb, col['ice_ridge']))
    ck = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.noise(pos, 45.0, 0.3, 0.5), 0.5)), 0.012, 0.004)
    gate = MK._smooth(nb, nb.noise(pos, 6.0, 0.5, 0.5), 0.52, 0.6)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', ck, gate), nb.math('MULTIPLY', tusk, 0.4)), c, _rgb(nb, col['ice_ridge']))
    _ = groove
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the snowflakes' places (make_marks)
def _tangent_frame(n: np.ndarray, ang: float):
    a = np.cross(n, (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0))
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    return a * math.cos(ang) + b * math.sin(ang)


def body_flakes(co: np.ndarray) -> list:
    """Snowflakes over the teal (2-turnaround: big ones down the back and on the crown, small ones scattered over the
    head's cap, the flanks and the tail): a fixed seed, kept apart, clear of the eyes, the tusk's root and the fins."""
    rng = np.random.default_rng(1830)
    tk = FP.teal_k(co)
    ok = tk > 0.92
    ok &= F.eye_dist(co) > 0.09
    ok &= np.linalg.norm(co - np.array(F.TUSK_BASE[:]), axis=1) > 0.075
    for s in (1, -1):
        o = np.array(F.fin_axes(s)[0][:])
        ok &= np.linalg.norm(co - o, axis=1) > 0.17                 # round 3: none near the fins' roots (a fleck in the crease)
    ok &= co[:, 1] < 0.45
    idx = np.nonzero(ok)[0]
    rng.shuffle(idx)
    idx = idx[:24000]
    out, placed = [], []
    want_big, want_small = 26, 30                                  # polish: more of them branched (4-details 6)
    nb_big = nb_small = 0
    for i in idx:
        p = co[i]
        top = p[2] - FP._interp(np.array([p[1]]), FP.WATER)[0]
        big = nb_big < want_big and top > 0.1 and abs(p[0]) < 0.17 and p[1] < 0.42
        if not big and nb_small >= want_small:
            continue
        r = float(rng.uniform(0.02, 0.031)) if big else float(rng.uniform(0.012, 0.017))
        gap = (r + 0.03) if big else (r + 0.035)
        if placed and min(float(np.linalg.norm(p - q)) - rq for q, rq in placed) < gap:
            continue
        n = F.normal_of(p[None])[0]
        t = _tangent_frame(n, float(rng.uniform(0, math.pi / 3)))
        out.append((tuple(map(float, p)), tuple(map(float, n)), tuple(map(float, t)), r, bool(big)))
        placed.append((p, r))
        if big:
            nb_big += 1
        else:
            nb_small += 1
        if nb_big >= want_big and nb_small >= want_small:
            break
    return out


def prop_flakes() -> list:
    """A few snowflakes on each fin and the fluke (4-details 3, 4), on their mid-planes (the star's depth reaches both faces)."""
    out = []
    spots = {'fin': [(0.1, -0.02, 0.012, False), (0.17, 0.015, 0.016, True), (0.205, -0.045, 0.011, False)],
             'fluke': [(0.09, 0.07, 0.015, True), (0.16, 0.12, 0.012, False), (0.2, 0.14, 0.009, False)]}
    for s in (1, -1):
        o, a, v, n = F.fin_axes(s)
        for u, w, r, big in spots['fin']:
            u, w = u * F.FIN_K, w * F.FIN_K
            c = o + a * u + v * w + n * (1.1 * w * w)
            out.append((tuple(c), tuple(n), tuple(a), r, big))
        o, u_, v_, n_ = F.fluke_axes()
        for u, w, r, big in spots['fluke']:
            u, w = u * F.FLUKE_K, w * F.FLUKE_K
            c = o + u_ * (u * s) + v_ * w + n_ * (-F.FLUKE_DROOP * u * u)
            out.append((tuple(c), tuple(n_), tuple(u_), r, big))
    return out
