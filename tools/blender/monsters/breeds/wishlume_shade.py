"""Wishlume's per-pixel bake materials (wishlume_ultra.py): the paper (fibres, leaves, the inked face, the paddles'
red rims, Beacon's stripes), the glow pass, the props (twine, bamboo nodes) and the eye lenses.

Leaves are one node group (`WS_WishLeaf`) instanced per leaf: a pointed leaf lying on the surface with a midrib.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

from lib import common as C
from lib import marks as MK
from lib.nodes import NB, new_mat
from monsters.breeds import wishlume_carve as K
from monsters.breeds import wishlume_form as F
from monsters.breeds import wishlume_paint as WP

LEAF_GROUP = 'WS_WishLeaf'
STRIPE = {'period': 0.095, 'red': 0.5, 'phase': 0.0}        # Beacon's bands: 9.5 cm apart, half red


def _group_leaf() -> bpy.types.ShaderNodeTree:
    g = bpy.data.node_groups.get(LEAF_GROUP)
    if g is not None:
        return g
    g = bpy.data.node_groups.new(LEAF_GROUP, 'ShaderNodeTree')
    for nm, kind, dv in (('Position', 'NodeSocketVector', None), ('Centre', 'NodeSocketVector', None),
                         ('Normal', 'NodeSocketVector', (0.0, -1.0, 0.0)), ('Along', 'NodeSocketVector', (0.0, 0.0, 1.0)),
                         ('Half', 'NodeSocketFloat', 0.03), ('Width', 'NodeSocketFloat', 0.01), ('Depth', 'NodeSocketFloat', 0.01)):
        s = g.interface.new_socket(nm, in_out='INPUT', socket_type=kind)
        if dv is not None:
            s.default_value = dv
    for nm in ('Mask', 'Rib', 'T'):
        g.interface.new_socket(nm, in_out='OUTPUT', socket_type='NodeSocketFloat')
    nb = NB(g)
    gi, go = nb.new('NodeGroupInput'), nb.new('NodeGroupOutput')
    d = nb.vmath('SUBTRACT', gi.outputs['Position'], gi.outputs['Centre'])
    h = nb.vmath('DOT_PRODUCT', d, gi.outputs['Normal'])
    a = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', d, gi.outputs['Along']), gi.outputs['Half'])
    side = nb.vmath('CROSS_PRODUCT', gi.outputs['Normal'], gi.outputs['Along'])
    b = nb.math('ABSOLUTE', nb.vmath('DOT_PRODUCT', d, side))
    a2 = nb.math('MINIMUM', nb.math('MULTIPLY', a, a), 1.0)
    # the outline: |b| < W (1 - a^2), a little fuller toward the base (a < 0)
    full = nb.math('ADD', 1.0, nb.math('MULTIPLY', nb.math('MINIMUM', a, 0.0), -0.25))
    wa = nb.math('MULTIPLY', nb.math('MULTIPLY', gi.outputs['Width'], nb.math('SUBTRACT', 1.0, a2)), full)
    soft = nb.math('MULTIPLY', gi.outputs['Width'], 0.12)
    m = MK._smooth(nb, b, nb.math('ADD', wa, soft), nb.math('SUBTRACT', wa, soft))
    dep = MK._smooth(nb, nb.math('ABSOLUTE', h), gi.outputs['Depth'], nb.math('MULTIPLY', gi.outputs['Depth'], 0.6))
    m = nb.math('MULTIPLY', nb.math('MULTIPLY', m, dep), nb.math('LESS_THAN', nb.math('ABSOLUTE', a), 1.0))
    rib = nb.math('MULTIPLY', MK._smooth(nb, b, nb.math('MULTIPLY', gi.outputs['Width'], 0.09), nb.math('MULTIPLY', gi.outputs['Width'], 0.03)),
                  nb.math('LESS_THAN', a, 0.82))
    nb.link(m, go.inputs['Mask'])
    nb.link(nb.math('MULTIPLY', rib, m), go.inputs['Rib'])
    nb.link(nb.math('MULTIPLY', nb.math('ADD', a, 1.0), 0.5), go.inputs['T'])
    return g


# the front sprig (round 2, 1-hero: five leaves on a curved stem, about a quarter of the body's height), front-view
# (x, z) metres on the paper: the stem's points, then each leaf (base, tip, half width)
SPRIG_STEM = [(-0.008, 0.35), (-0.024, 0.39), (-0.046, 0.43), (-0.066, 0.468)]
SPRIG_LEAVES = [((-0.012, 0.36), (0.03, 0.408), 0.015), ((-0.028, 0.392), (-0.08, 0.418), 0.015),
                ((-0.04, 0.418), (0.0, 0.462), 0.014), ((-0.056, 0.444), (-0.104, 0.466), 0.013),
                ((-0.066, 0.466), (-0.072, 0.512), 0.012)]


def leaf_specs() -> list[tuple]:
    """(centre, normal, along, half length, half width, strength) per leaf: the front sprig and a spray on the front's
    right (1-hero, 2-turnaround), sprays on the sides and the back, two on each paddle's faces (front and back). Round 2: everything larger, the leaves a stronger red."""
    out = []

    def on_surface(xb, zb, xt, zt, w, front=True, k=1.0):
        a, b = F.surface_at(xb, zb, front), F.surface_at(xt, zt, front)
        c = F.surface_at((xb + xt) / 2, (zb + zt) / 2, front)
        n = F.normal_at(c)
        al = (b - a) - n * (b - a).dot(n)
        out.append((tuple(c), tuple(n), tuple(al.normalized()), 0.5 * (b - a).length, w, k))

    def px(x, y, axis):
        return (x - axis) * F.PX, (783 - y) * F.PX
    for (xb, zb), (xt, zt), w in SPRIG_LEAVES:
        on_surface(xb, zb, xt, zt, w)
    for (xb, zb), (xt, zt), w in (((0.112, 0.36), (0.172, 0.432), 0.017), ((0.104, 0.352), (0.165, 0.378), 0.014),
                                  ((0.126, 0.372), (0.136, 0.448), 0.014)):
        on_surface(xb, zb, xt, zt, w)
    for (xb, yb), (xt, yt), w in (((1250, 520), (1196, 452), 0.016), ((1300, 523), (1258, 445), 0.017), ((1432, 522), (1460, 494), 0.012)):
        (x0, z0), (x1, z1) = px(xb, yb, 1340), px(xt, yt, 1340)
        on_surface(-x0, z0, -x1, z1, w, front=False)
    for s in (1, -1):
        # the sides (side view: low and a little forward)
        for (th0, z0), (th1, z1), w in (((84, 0.365), (76, 0.455), 0.016), ((88, 0.36), (103, 0.425), 0.014)):
            a, b = F.surface_dir(th0 * s, z0), F.surface_dir(th1 * s, z1)
            c = (a + b) / 2
            c = F.surface_dir(math.degrees(math.atan2(c.x, -c.y)), c.z)
            n = F.normal_at(c)
            al = (b - a) - n * (b - a).dot(n)
            out.append((tuple(c), tuple(n), tuple(al.normalized()), 0.5 * (b - a).length, w, 1.0))
    # polish: the three small leaves near the crown are gone (on the curved crown they baked as soft pink smears)
    for s in (1, -1):
        al, fa, up = F.arm_axes(s)
        bc = Vector(F.mirror(F.ARM_BULB, s))
        thick = F.ARM_HALF[2]
        for face in (1, -1):
            n = fa * face
            for du, dv, ang, L in ((-0.008, 0.016, 58, 0.044), (0.022, -0.016, 28, 0.038)):
                c = bc + al * du + up * dv + n * (thick * 0.92)
                t = (up * math.cos(math.radians(ang)) + al * math.sin(math.radians(ang)))
                out.append((tuple(c), tuple(n), tuple(t.normalized()), L, L * 0.4, 1.0))
    return out


def sprig_stem(nb: NB, pos):
    """The front sprig's stem: short lines along the paper."""
    pts = [F.surface_at(x, z) for x, z in SPRIG_STEM]
    return MK.union(nb, [MK.line(nb, pos, tuple(a), tuple(b), 0.0017, 0.35) for a, b in zip(pts[:-1], pts[1:])])


def leaves(nb: NB, pos) -> tuple:
    """(mask, rib mask, along 0 base..1 tip) of every leaf, each faint leaf at its strength."""
    g = _group_leaf()
    masks, ribs, ts = [], [], []
    for c, n, al, half, w, k in leaf_specs():
        node = nb.new('ShaderNodeGroup')
        node.node_tree = g
        nb.link(pos, node.inputs['Position'])
        for nm, v in (('Centre', c), ('Normal', n), ('Along', al)):
            node.inputs[nm].default_value = v
        node.inputs['Half'].default_value = half
        node.inputs['Width'].default_value = w
        node.inputs['Depth'].default_value = 0.012
        masks.append(nb.math('MULTIPLY', node.outputs['Mask'], k) if k < 1 else node.outputs['Mask'])
        ribs.append(node.outputs['Rib'])
        ts.append(nb.math('MULTIPLY', node.outputs['T'], node.outputs['Mask']))
    return MK.union(nb, masks), MK.union(nb, ribs), MK.union(nb, ts)


def _local(nb: NB, pos, c, xa, ya, za=None):
    d = nb.vmath('SUBTRACT', pos, tuple(c))
    out = [nb.vmath('DOT_PRODUCT', d, tuple(xa)), nb.vmath('DOT_PRODUCT', d, tuple(ya))]
    if za is not None:
        out.append(nb.vmath('DOT_PRODUCT', d, tuple(za)))
    return out


def _band(nb: NB, v, centre, half, soft):
    """1 within half of centre (sockets or numbers), soft-edged."""
    d = nb.math('ABSOLUTE', nb.math('SUBTRACT', v, centre))
    return MK._smooth(nb, d, nb.math('ADD', half, soft), nb.math('SUBTRACT', half, soft))


def face_marks(nb: NB, pos) -> dict:
    """The inked face (2-turnaround front, 3-faces, 4-details 2): the closed lid's curved lash line under each lens
    (shown when a blink sinks it; the eyes' outlines are on the lenses, round 2 without the flick lashes), the arched
    brows, the small smile with its upturned ends, the blush with three little hatch strokes."""
    x, y, z = nb.sep(pos)
    front = MK._smooth(nb, y, -0.12, -0.15)
    ink, lid = [], []
    for s in (1, -1):
        c, xa, ya, lk = F.eye_frame(s)
        ex, ey, ez = _local(nb, pos, c, xa / (F.EYE_R * F.EYE_SHAPE[0]), ya / (F.EYE_R * F.EYE_SHAPE[1]), lk)
        r = nb.vmath('LENGTH', nb.comb(ex, ey, 0.0))
        near = MK._smooth(nb, nb.math('ABSOLUTE', ez), 0.02, 0.012)
        # the closed lid: a smooth U from corner to corner, 0.2 below the middle (3-faces blink)
        xn = nb.math('DIVIDE', ex, 0.88)
        arc = nb.math('MULTIPLY', nb.math('ADD', 0.03, nb.math('MULTIPLY', 0.19, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', xn, xn)))), -1.0)
        th = nb.math('ADD', 0.05, nb.math('MULTIPLY', MK._smooth(nb, nb.math('ABSOLUTE', xn), 0.9, 0.3), 0.035))
        lid.append(nb.math('MULTIPLY', nb.math('MULTIPLY', _band(nb, ey, arc, th, 0.02), MK._smooth(nb, nb.math('ABSOLUTE', xn), 1.0, 0.92)), near))
    # brows: arched strokes, thickest at the peak, the outer end lower
    for s in (1, -1):
        a = nb.math('DIVIDE', nb.math('SUBTRACT', nb.math('MULTIPLY', x, float(s)), F.BROW_X), 0.031)
        a2 = nb.math('MINIMUM', nb.math('MULTIPLY', a, a), 1.0)
        zb = nb.math('ADD', F.BROW_Z + 0.001, nb.math('SUBTRACT', nb.math('MULTIPLY', 0.0075, nb.math('SUBTRACT', 1.0, a2)), nb.math('MULTIPLY', a, 0.0035)))
        w = nb.math('ADD', 0.0012, nb.math('MULTIPLY', 0.0046, nb.math('POWER', nb.math('SUBTRACT', 1.0, a2), 0.6)))
        ink.append(nb.math('MULTIPLY', nb.math('MULTIPLY', _band(nb, z, zb, w, 0.0006), MK._smooth(nb, nb.math('ABSOLUTE', a), 1.04, 0.96)), front))
    # the smile (wishlume_carve.smile_z), its stroke thinning toward the ends
    am = nb.math('DIVIDE', nb.math('ABSOLUTE', x), F.MOUTH_W)
    amc = nb.math('MINIMUM', am, 1.2)
    zm = nb.math('ADD', F.MOUTH_Z - F.MOUTH_SAG, nb.math('ADD', nb.math('MULTIPLY', F.MOUTH_SAG, nb.math('MULTIPLY', amc, amc)),
                                                         nb.math('MULTIPLY', MK._smooth(nb, am, 0.8, 1.08), 0.0035)))
    wm = nb.math('SUBTRACT', 0.0024, nb.math('MULTIPLY', 0.001, nb.math('MINIMUM', nb.math('MULTIPLY', am, am), 1.0)))
    ink.append(nb.math('MULTIPLY', nb.math('MULTIPLY', _band(nb, z, zm, wm, 0.0005), MK._smooth(nb, am, 1.1, 1.0)), front))
    blush, hatch = [], []
    for s in (1, -1):
        bc = F.surface_at(F.BLUSH_X * s, F.BLUSH_Z)
        blush.append(MK.dot(nb, pos, tuple(bc), (F.BLUSH_R[0], 0.02, F.BLUSH_R[1]), 0.55))
        for k in (-1, 0, 1):
            a = F.surface_at(F.BLUSH_X * s + 0.009 * k - 0.003, F.BLUSH_Z - 0.0045)
            b = F.surface_at(F.BLUSH_X * s + 0.009 * k + 0.003, F.BLUSH_Z + 0.0045)
            hatch.append(MK.line(nb, pos, tuple(a), tuple(b), 0.0011, 0.4))
    return {'ink': MK.union(nb, ink), 'lid': MK.union(nb, lid), 'blush': MK.union(nb, blush), 'hatch': MK.union(nb, hatch)}


def arm_rims(nb: NB, armk) -> object:
    """The paddles' red rims, per pixel: where the skin turns edge-on to the broad face (wishlume_carve.rim_band)."""
    geo = nb.new('ShaderNodeNewGeometry')
    pos = nb.coords().outputs['Object']
    x = nb.sep(pos)[0]
    out = None
    for s in (1, -1):
        al, fa, _up = F.arm_axes(s)
        d = nb.math('ABSOLUTE', nb.vmath('DOT_PRODUCT', geo.outputs['Normal'], tuple(fa)))
        along = nb.vmath('DOT_PRODUCT', nb.vmath('SUBTRACT', pos, F.mirror(F.ARM_BULB, s)), tuple(al))
        side = nb.math('GREATER_THAN', nb.math('MULTIPLY', x, float(s)), 0.0)
        m = nb.math('MULTIPLY', nb.math('MULTIPLY', MK._smooth(nb, d, 0.36, 0.26), MK._smooth(nb, along, -0.09, -0.06)), side)
        out = m if out is None else nb.math('MAXIMUM', out, m)
    return nb.math('MULTIPLY', out, MK._smooth(nb, armk, 0.55, 0.8))


def stripes(nb: NB, z):
    """Beacon's horizontal red bands (variant picture): 1 on a red band, soft-edged."""
    ph = nb.math('FRACT', nb.math('DIVIDE', nb.math('SUBTRACT', z, STRIPE['phase']), STRIPE['period']))
    return nb.math('MULTIPLY', MK._smooth(nb, ph, 0.0, 0.025), MK._smooth(nb, ph, STRIPE['red'], STRIPE['red'] - 0.025))


FIBRE_DIRS = [((25.0, 10.0, 35.0), (5.0, 70.0, 70.0)), ((-30.0, 40.0, -15.0), (6.0, 80.0, 80.0)), ((60.0, -20.0, 80.0), (5.0, 75.0, 75.0)),
              ((10.0, 70.0, -40.0), (7.0, 90.0, 90.0))]


def _fibres(nb: NB, pos):
    """The paper's fibres (4-details 2 and 6, round 3): thin, long, wispy strands criss-crossing in four directions that
    never close into cells (the ridge where a stretched noise crosses its middle), plus a soft mottle and tiny flecks."""
    lines = None
    for k, (rot, scale) in enumerate(FIBRE_DIRS):
        mp = nb.new('ShaderNodeMapping')
        nb.link(pos, mp.inputs['Vector'])
        mp.inputs['Rotation'].default_value = tuple(math.radians(a) for a in rot)
        mp.inputs['Scale'].default_value = scale
        mp.inputs['Location'].default_value = (0.37 * k, 0.11 * k, 0.53 * k)
        n = nb.new('ShaderNodeTexNoise')
        nb.link(mp.outputs['Vector'], n.inputs['Vector'])
        n.inputs['Scale'].default_value = 1.0
        n.inputs['Detail'].default_value = 1.5
        n.inputs['Roughness'].default_value = 0.5
        ridge = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', n.outputs['Fac'], 0.5)), 0.022, 0.004)
        # break each fibre into lengths, so none runs on for ever
        gate = MK._smooth(nb, nb.noise(pos, 9.0 + 3 * k, 1.0, 0.5), 0.46, 0.56)
        f = nb.math('MULTIPLY', ridge, gate)
        lines = f if lines is None else nb.math('MAXIMUM', lines, f)
    mott = nb.math('SUBTRACT', nb.noise(pos, 16.0, 4.0, 0.55), 0.5)
    fleck = MK._smooth(nb, nb.noise(pos, 520.0, 1.0, 0.5), 0.71, 0.76)
    return lines, mott, fleck


def _rgb(nb: NB, h: str):
    return nb.rgb(C.lin(h))


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the paint (the inner light's gradient) with, per pixel: the paper's fibres and flecks, Beacon's red
    bands, the pressed leaves, the paddles' red rims, the inked face, the blush."""
    col = WP.colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    z = nb.sep(pos)[2]
    c = nb.attribute(attr).outputs['Color']
    armk = nb.attribute('armk').outputs['Fac']
    paper = MK._smooth(nb, z, F.Z_OPEN + 0.002, F.Z_OPEN + 0.008)          # not the inside of the lantern
    lines, mott, fleck = _fibres(nb, pos)
    k = nb.math('ADD', 1.0, nb.math('MULTIPLY', mott, 0.04))
    c = nb.mix(1.0, c, nb.comb(k, k, k), blend='MULTIPLY')
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', lines, 0.2), paper), c, _rgb(nb, C.mix_hex(col['paper'], col['light'], 0.85)))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', fleck, 0.35), paper), c, _rgb(nb, col['twine']))
    if pal.get('stripes'):
        sm = nb.math('MULTIPLY', nb.math('MULTIPLY', stripes(nb, z), paper), nb.math('SUBTRACT', 1.0, MK._smooth(nb, armk, 0.3, 0.6)))
        sc = nb.mix(lines, _rgb(nb, col['stripe']), _rgb(nb, C.mix_hex(col['stripe'], col['light'], 0.25)))
        c = nb.mix(nb.math('MULTIPLY', sm, 0.92), c, sc)
    lm, lr, lt = leaves(nb, pos)
    leaf = nb.mix(MK._smooth(nb, lt, 0.05, 0.55), _rgb(nb, col['leaf_base']), _rgb(nb, col['leaf']))
    leaf = nb.mix(nb.math('MULTIPLY', lr, 0.7), leaf, _rgb(nb, col['leaf_rib']))
    if pal.get('stripes'):
        # Beacon: deep red leaves with a pale edge, so the sprig still reads on a red band (variant picture)
        edge = nb.math('MULTIPLY', nb.math('MULTIPLY', lm, nb.math('SUBTRACT', 1.0, lm)), 4.0)
        leaf = nb.mix(nb.math('MULTIPLY', edge, 0.75), leaf, _rgb(nb, col['leaf_edge']))
    c = nb.mix(nb.math('MULTIPLY', lm, 0.95), c, leaf)
    c = nb.mix(nb.math('MULTIPLY', sprig_stem(nb, pos), 0.9), c, _rgb(nb, col['leaf_rib']))
    fl = flame(nb, pos)
    c = nb.mix(nb.math('MULTIPLY', fl['body'], 0.9), c, _rgb(nb, col['flame_mid']))
    c = nb.mix(fl['core'], c, _rgb(nb, col['flame_core']))
    c = nb.mix(nb.math('MULTIPLY', fl['edge'], 0.8), c, _rgb(nb, col['flame_edge']))
    c = nb.mix(arm_rims(nb, armk), c, _rgb(nb, col['red']))
    # polish: only a faint warm shadow where each paddle grows out of the globe (round 3's red contact line baked as a
    # blurry, stair-stepped second rim)
    contact = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', armk, 0.5)), 0.25, 0.1)
    c = nb.mix(nb.math('MULTIPLY', contact, 0.12), c, _rgb(nb, col['flame_edge']))
    fm = face_marks(nb, pos)
    c = nb.mix(nb.math('MULTIPLY', fm['blush'], 0.85), c, _rgb(nb, col['blush']))       # round 3: a soft oval, no hatching
    c = nb.mix(fm['ink'], c, _rgb(nb, col['ink']))
    c = nb.mix(fm['lid'], c, _rgb(nb, col['ink']))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def flame(nb: NB, pos) -> dict:
    """The flame inside the opening (4-details 5), painted on the inner dome as seen from below: a teardrop whose round
    end is toward the front and whose tip points back and up the dome, with a paler core."""
    x, y, z = nb.sep(pos)
    inside = nb.math('MULTIPLY', MK._smooth(nb, z, F.Z_OPEN + 0.004, F.Z_OPEN + 0.012), MK._smooth(nb, z, 0.43, 0.415))
    v = nb.math('DIVIDE', nb.math('SUBTRACT', y, -0.035), 0.11)                  # 0 at the round end .. 1 at the tip
    vc = nb.math('MINIMUM', nb.math('MAXIMUM', v, 0.0), 1.0)
    w = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.math('POWER', nb.math('SUBTRACT', 1.0, vc), 1.1), nb.math('POWER', vc, 0.45)), 0.08)
    wob = nb.math('MULTIPLY', nb.math('SUBTRACT', nb.noise(pos, 40.0, 2.0, 0.5), 0.5), 0.008)
    ax = nb.math('ADD', nb.math('ABSOLUTE', x), wob)
    body = nb.math('MULTIPLY', MK._smooth(nb, ax, nb.math('ADD', w, 0.004), nb.math('SUBTRACT', w, 0.004)), inside)
    core = nb.math('MULTIPLY', MK._smooth(nb, ax, nb.math('MULTIPLY', w, 0.6), nb.math('MULTIPLY', w, 0.35)), body)
    edge = nb.math('MULTIPLY', _band(nb, ax, w, 0.0025, 0.0015), inside)
    return {'body': body, 'core': core, 'edge': edge}


def glow_material(name: str, marks, pal: dict | None = None) -> bpy.types.Material:
    """The glow pass: the paint's `glow` (Beacon: `glow_beacon`, its white bands glowing through and its red bands
    holding the light back), none under the ink, less under the leaves and the blush, the flame inside the opening at
    full strength."""
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    z = nb.sep(pos)[2]
    beacon = bool(pal and pal.get('stripes'))
    g = nb.attribute('glow_beacon' if beacon else 'glow').outputs['Fac']
    lm, _lr, _lt = leaves(nb, pos)
    g = nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', lm, 0.9 if beacon else 0.15)))
    # backlit paper (4-details 6): the fibres' net glows a little brighter, the creases (more layers of paper) darker,
    # so both show whatever the lighting (round 2: the lit relief alone was lost under the glow)
    paper = MK._smooth(nb, z, F.Z_OPEN + 0.002, F.Z_OPEN + 0.008)
    lines, _mott, _fleck = _fibres(nb, pos)
    g = nb.math('MULTIPLY', g, nb.math('ADD', 1.0, nb.math('MULTIPLY', nb.math('MULTIPLY', lines, 0.25), paper)))
    cr = nb.attribute('crease').outputs['Fac']
    g = nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', nb.math('MINIMUM', cr, 1.0), 0.45)))
    fm = face_marks(nb, pos)
    g = nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, nb.math('MINIMUM', nb.math('ADD', fm['ink'], fm['lid']), 1.0)))
    g = nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', fm['blush'], 0.35)))
    if beacon:
        armk = nb.attribute('armk').outputs['Fac']
        sm = nb.math('MULTIPLY', nb.math('MULTIPLY', stripes(nb, z), paper), nb.math('SUBTRACT', 1.0, MK._smooth(nb, armk, 0.3, 0.6)))
        g = nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', sm, 0.92)))      # round 3: true red bands
    fl = flame(nb, pos)
    g = nb.math('MAXIMUM', g, fl['body'])
    g = nb.math('MINIMUM', nb.math('MAXIMUM', g, 0.0), 1.0)
    em = nb.new('ShaderNodeEmission')
    nb.link(nb.comb(g, g, g), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """A painted eye (4-details 2, 1-hero; polish): a large rich-brown iris that fills the eye, set a little up and
    toward the nose so the white shows only as a crescent at the lower outer side, amber in its lower third, the
    ink-coloured ring and pupil, a clean moderately thick upper lid line along the top (no flick), two white highlights
    (the same side in both eyes). It meets the paper at about 0.96 of the patch."""
    col = WP.colours(pal or {'body': '#F6E3B4', 'belly': '#FFF2D6', 'accent': '#D94F4F', 'eye': '#3A2A2A'})
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.5, 0.12))          # matte ink on paper (round 2: it read as a glossy button)
        nb.output(em.outputs[0])
        return m
    x, y, _z = nb.sep(nb.attribute('eyeuv').outputs['Vector'])
    side = nb.attribute('eye_side').outputs['Fac']
    cx = nb.math('MULTIPLY', side, -0.09)                       # toward the nose
    ix, iy = nb.math('SUBTRACT', x, cx), nb.math('SUBTRACT', y, 0.07)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), 0.8)     # 1 at the iris's edge
    r = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    warm = MK._smooth(nb, nb.math('DIVIDE', iy, 0.8), -0.3, -0.62)            # the lower third only
    iris = nb.mix(warm, _rgb(nb, col['iris']), _rgb(nb, col['iris_warm']))
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 28.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', MK._smooth(nb, ri, 0.42, 0.5), MK._smooth(nb, ri, 0.9, 0.8)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.12), iris, _rgb(nb, col['iris_deep']))
    c = nb.mix(MK._smooth(nb, ri, 0.42, 0.38), iris, _rgb(nb, col['ink']))               # the pupil
    c = nb.mix(MK._smooth(nb, ri, 0.9, 0.96), c, _rgb(nb, col['ink']))                   # the iris's ring
    c = nb.mix(MK._smooth(nb, ri, 1.0, 1.04), c, _rgb(nb, col['sclera']))                # the white: a lower outer crescent
    # the outline: thin round the sides and below, a clean moderately thick lid line along the top
    r_in = nb.math('SUBTRACT', 0.9, nb.math('MULTIPLY', MK._smooth(nb, y, 0.1, 0.75), 0.11))
    c = nb.mix(MK._smooth(nb, r, r_in, nb.math('ADD', r_in, 0.025)), c, _rgb(nb, col['ink']))
    big = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, 0.24), nb.math('SUBTRACT', iy, 0.24), 0.0)), 0.145, 0.12)
    small = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, 0.2), nb.math('ADD', iy, 0.26), 0.0)), 0.07, 0.052)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """The props per pixel: twisted twine strands on the wraps, the rope and the collar; the bamboo ribs' fine grain
    and their darker nodes; a silk sheen streak down each thread."""
    col = WP.colours(pal)
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    part = nb.attribute('part').outputs['Fac']
    pt = nb.attribute('pt').outputs['Fac']
    pa = nb.attribute('pa').outputs['Fac']
    plen = nb.attribute('plen').outputs['Fac']
    s = nb.math('MULTIPLY', pt, plen)

    def is_part(*ids):
        out = None
        for i in ids:
            e = nb.math('COMPARE', part, float(i), 0.4)
            out = e if out is None else nb.math('MAXIMUM', out, e)
        return out
    from monsters.breeds import wishlume_props as PR
    tw = is_part(PR.WRAP, PR.RINGWRAP, PR.ROPE, PR.CORD, PR.HANDLEBAND)
    strand = nb.math('SINE', nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', pa, 3.0), nb.math('DIVIDE', s, 0.0045)), 2 * math.pi))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', MK._smooth(nb, strand, 0.2, -0.6), 0.55), tw), c, _rgb(nb, col['twine_dark']))
    # the handle: red cord wound round it (round 2, 4-details 1)
    hd = is_part(PR.LOOP)
    wind = nb.math('SINE', nb.math('MULTIPLY', nb.math('ADD', pa, nb.math('DIVIDE', s, 0.0042)), 2 * math.pi))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', MK._smooth(nb, wind, 0.1, -0.7), 0.45), hd), c, _rgb(nb, col['rib_node']))
    collar = is_part(PR.COLLAR)
    rings = nb.math('SINE', nb.math('MULTIPLY', pt, 140.0))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', MK._smooth(nb, rings, 0.1, -0.5), 0.5), collar), c, _rgb(nb, col['twine_dark']))
    rib = is_part(PR.RIB)
    node = nb.math('FRACT', nb.math('DIVIDE', nb.math('SUBTRACT', s, 0.05), 0.09))
    nd = nb.math('MAXIMUM', MK._smooth(nb, node, 0.035, 0.0), MK._smooth(nb, node, 0.965, 1.0))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nd, 0.75), rib), c, _rgb(nb, col['rib_node']))
    grain = nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', pa, 2 * math.pi * 6)), 0.04)
    gk = nb.math('ADD', 1.0, nb.math('MULTIPLY', grain, rib))
    c = nb.mix(1.0, c, nb.comb(gk, gk, gk), blend='MULTIPLY')
    th = is_part(PR.THREAD)
    sheen = nb.math('MULTIPLY', nb.math('MULTIPLY', MK._smooth(nb, pt, 0.15, 0.45), MK._smooth(nb, pt, 0.95, 0.7)), th)
    c = nb.mix(nb.math('MULTIPLY', sheen, 0.22), c, _rgb(nb, col['thread_light']))
    # the tassel's core: fine strands side by side down the bell (round 2: one silky mass, no see-through gaps)
    core = is_part(PR.CORE)
    st = nb.math('SINE', nb.math('MULTIPLY', pa, 2 * math.pi * 90))
    st2 = nb.math('SINE', nb.math('MULTIPLY', pa, 2 * math.pi * 37))
    streak = nb.math('ADD', nb.math('MULTIPLY', st, 0.6), nb.math('MULTIPLY', st2, 0.4))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', MK._smooth(nb, streak, -0.2, 0.7), 0.45), core), c, _rgb(nb, col['thread']))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', MK._smooth(nb, streak, 0.5, 0.95), 0.3), core), c, _rgb(nb, col['thread_light']))
    # the band of lit paper over the hoop: the paper's fine veins
    # the lip (polish): the lower paper running down to the hoop, so the hoop is the paper's lower edge (1-hero)
    sk = is_part(PR.SKIRT)
    c = nb.mix(sk, c, _rgb(nb, C.shade_hex(col['paper_low'], 0.95)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
