"""Mirrorkin's per-pixel bake materials (mirrorkin_ultra.py): the face drawn in the glass (lavender lids, flick lashes,
brows, the small nose, the calm closed smile, the blush and its sparkles, the closed lids' lash lines under the lenses),
the gold's engraving (the beading, the rope, the cove's line, the back's oval border and diamond, the handle's flutes),
the gloves' stitching, the eye lenses, the glow passes and the props (the cloak's gold trim and embroidered border).
"""
from __future__ import annotations

import math

import bpy

from lib import common as C
from lib import marks as MK
from lib.nodes import NB, new_mat
from monsters.breeds import mirrorkin_cloak as CL
from monsters.breeds import mirrorkin_form as F
from monsters.breeds import mirrorkin_paint as MP


def _rgb(nb: NB, h: str):
    return nb.rgb(C.lin(h))


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


def _mul(nb: NB, *xs):
    out = xs[0]
    for x in xs[1:]:
        out = nb.math('MULTIPLY', out, x)
    return out


# ----------------------------------------------------------------------------- the face
def taper(nb: NB, pos, a, b, r0: float, r1: float):
    """1 within a radius that tapers from r0 at a to r1 at b of the segment a -> b (a lash, a wing), soft-edged."""
    a, b = (tuple(float(v) for v in p) for p in (a, b))
    ab = tuple(bb - aa for aa, bb in zip(a, b))
    ap = nb.vmath('SUBTRACT', pos, a)
    t = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', ap, ab), max(sum(v * v for v in ab), 1e-12), clamp=True)
    q = nb.vmath('ADD', a, nb.vmath('SCALE', ab, scale=t))
    d = nb.vmath('DISTANCE', pos, q)
    r = nb.math('ADD', r0, nb.math('MULTIPLY', t, r1 - r0))
    return MK._smooth(nb, d, nb.math('MULTIPLY', r, 1.25), nb.math('MULTIPLY', r, 0.75))


def _eye_pt(s: int, r: float, ang: float, out: float = 0.0006):
    a = math.radians(ang)
    return F.surface_at(F.EYE_X * s + s * F.EYE_A * r * math.cos(a), F.EYE_Z + F.EYE_B * r * math.sin(a), out)


def face_marks(nb: NB, pos, obs: bool = False) -> dict:
    """The face in the glass (2-turnaround front, 3-faces neutral, 4-details 2): masks 0..1 for each stroke.
    Review round 1: each eye's lash is a solid black wing from the outer corner with two flicked lashes growing from
    it (three thin ticks read as crow's feet, and stood above the closed lid in a blink); under each lens the glass is
    painted as the closed lid (lavender down to the closed lash line), shown when a blink sinks the lens."""
    x, y, z = nb.sep(pos)
    front = MK._smooth(nb, y, -0.03, -0.045)
    lid, lash, shut = [], [], []
    for s in (1, -1):
        c, xa, ya, lk = F.eye_frame(s)
        ex, ey, ez = _local(nb, pos, c, xa / F.EYE_A, ya / F.EYE_B, lk)
        r = nb.vmath('LENGTH', nb.comb(ex, ey, 0.0))
        near = MK._smooth(nb, nb.math('ABSOLUTE', ez), 0.02, 0.01)
        # the closed lid's lash line: a smooth U from corner to corner, below the middle
        xn = nb.math('DIVIDE', ex, 0.92)
        arc = nb.math('MULTIPLY', nb.math('ADD', 0.05, nb.math('MULTIPLY', 0.2, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', xn, xn)))), -1.0)
        th = nb.math('ADD', 0.05, nb.math('MULTIPLY', MK._smooth(nb, nb.math('ABSOLUTE', xn), 0.9, 0.3), 0.04))
        shut.append(_mul(nb, _band(nb, ey, arc, th, 0.02), MK._smooth(nb, nb.math('ABSOLUTE', xn), 0.86, 0.78),
                         MK._smooth(nb, r, 0.95, 0.9), near))
        # the lavender lid: above the eye, fading up toward the brow, a little wider at the outer corner; and under the
        # lens down to the closed lash line
        up = MK._smooth(nb, ey, -0.35, 0.35)
        out = nb.math('MULTIPLY', ex, float(s))
        reach = nb.math('ADD', 1.37 if obs else 1.62, nb.math('MULTIPLY', MK._smooth(nb, out, -0.2, 0.9), 0.13 if obs else 0.22))
        over = _mul(nb, MK._smooth(nb, r, reach, 0.98), up, near)
        under = _mul(nb, MK._smooth(nb, r, 1.02, 0.96), MK._smooth(nb, nb.math('SUBTRACT', ey, arc), -0.02, 0.04), near)
        lid.append(nb.math('MAXIMUM', over, under))
        # the wing from under the lens's outer corner, sweeping out and up, and two lashes flicking up from it
        # polish (review round 3): a thick upper lid line hugging the lens's top, thickening toward the outer corner,
        # sweeping out into one wing (two overlapping tapers); no loose lashes (they read as whiskers)
        rt = nb.math('ADD', 1.1, nb.math('MULTIPLY', MK._smooth(nb, out, -0.1, 0.95), 0.1))
        lash.append(_mul(nb, MK._smooth(nb, r, 0.95, 0.985), MK._smooth(nb, r, nb.math('ADD', rt, 0.015), nb.math('SUBTRACT', rt, 0.01)),
                         MK._smooth(nb, ey, 0.02, 0.28), near))
        lash.append(taper(nb, pos, _eye_pt(s, 0.92, 12.0), _eye_pt(s, 1.68, 30.0), 0.0078, 0.0012))
        lash.append(taper(nb, pos, _eye_pt(s, 1.04, 30.0), _eye_pt(s, 1.55, 45.0), 0.0048, 0.001))
    ink = []
    # the brows: thin arches, thickest just inside the peak, the outer end lower
    for s in (1, -1):
        a = nb.math('DIVIDE', nb.math('SUBTRACT', nb.math('MULTIPLY', x, float(s)), F.BROW_X), 0.039)   # review round 2: shorter
        a2 = nb.math('MINIMUM', nb.math('MULTIPLY', a, a), 1.0)
        zb = nb.math('ADD', F.BROW_Z, nb.math('SUBTRACT', nb.math('MULTIPLY', 0.011, nb.math('SUBTRACT', 1.0, a2)), nb.math('MULTIPLY', a, 0.006)))
        w = nb.math('ADD', 0.0007, nb.math('MULTIPLY', 0.0026, nb.math('POWER', nb.math('SUBTRACT', 1.0, a2), 0.7)))
        ink.append(_mul(nb, _band(nb, z, zb, w, 0.0005), MK._smooth(nb, nb.math('ABSOLUTE', a), 1.02, 0.94), front))
    # the calm closed smile, its stroke thinning toward the upturned ends
    am = nb.math('DIVIDE', nb.math('ABSOLUTE', x), F.MOUTH_W)
    amc = nb.math('MINIMUM', am, 1.15)
    zm = nb.math('ADD', F.MOUTH_Z - F.MOUTH_SAG, nb.math('ADD', nb.math('MULTIPLY', F.MOUTH_SAG, nb.math('MULTIPLY', amc, amc)),
                                                         nb.math('MULTIPLY', MK._smooth(nb, am, 0.82, 1.1), 0.004)))
    wm = nb.math('SUBTRACT', 0.0032, nb.math('MULTIPLY', 0.0016, nb.math('MINIMUM', nb.math('MULTIPLY', am, am), 1.0)))
    mouth = _mul(nb, _band(nb, z, zm, wm, 0.0005), MK._smooth(nb, am, 1.12, 1.02), front)
    nose = MK.dot(nb, pos, tuple(F.surface_at(0.0, F.NOSE[1], 0.004)), (0.0085, 0.012, 0.0072), 0.5)
    nose_hi = MK.dot(nb, pos, tuple(F.surface_at(-0.002, F.NOSE[1] + 0.003, 0.0055)), (0.0026, 0.01, 0.002), 0.5)
    blush, spark = [], []
    for s in (1, -1):
        bc = F.surface_at(F.BLUSH_X * s, F.BLUSH_Z)
        blush.append(MK.dot(nb, pos, tuple(bc), (0.032, 0.03, 0.019), 0.6))
        for dx, dz, r in ((-0.012, 0.006, 0.0018), (0.004, -0.004, 0.0014), (0.016, 0.005, 0.0016), (-0.002, 0.011, 0.0011)):
            spark.append(MK.dot(nb, pos, tuple(F.surface_at(F.BLUSH_X * s + dx * s, F.BLUSH_Z + dz)), r, 0.4))
    return {'lid': MK.union(nb, lid), 'lash': MK.union(nb, lash), 'shut': MK.union(nb, shut), 'ink': MK.union(nb, ink),
            'mouth': mouth, 'nose': nose, 'nose_hi': nose_hi, 'blush': MK.union(nb, blush), 'spark': MK.union(nb, spark)}


# ----------------------------------------------------------------------------- the glass
# polish (review round 3): the glass by contrast, not brightness: two parallel diagonal sheen bands across the upper-left
# third of the picture (the monster's right; about 8% and 4% of the glass's width, a gap between, fading out before the
# eyes, the face drawn over them); a bright bevel line inside the lip on the upper-left arc and the lower-right arc
# darker, so the glass reads curved and thick; the arched window about 1.5x bigger, softer, its lower half fading; a
# narrow sliver of another window cut off by the rim at the upper right
PANES = (((0.112, 0.63), (0.12, 0.19), -11.0, 0.0022, 0.85),     # (centre x, z), (w, h), degrees, edge softness, strength
         ((0.142, 0.93), (0.034, 0.1), -11.0, 0.002, 0.6))


def glass_masks(nb: NB, pos) -> dict:
    """The glass per pixel: 'in' (inside the frame's lip, front side), 'rim' (the bright bevel, upper left), 'rim_dark'
    (the darker bevel, lower right), 'top' / 'low' (for an even tone), 'pane' (the windows and the sheen bands)."""
    x, y, z = nb.sep(pos)
    xn, zn = nb.math('DIVIDE', x, F.GA), nb.math('DIVIDE', nb.math('SUBTRACT', z, F.ZC), F.GB)
    rho = nb.vmath('LENGTH', nb.comb(xn, zn, 0.0))
    front = MK._smooth(nb, y, -0.016, -0.022)
    inside = nb.math('MULTIPLY', MK._smooth(nb, rho, 0.985, 0.978), front)
    ring = nb.math('MULTIPLY', _band(nb, rho, 0.945, 0.02, 0.008), front)
    # which way the rim faces: +1 toward the upper left of the picture (-x, +z), -1 toward the lower right
    diag = nb.math('DIVIDE', nb.math('SUBTRACT', zn, xn), 1.4142)
    rim = nb.math('MULTIPLY', ring, MK._smooth(nb, diag, 0.05, 0.45))
    rim_dark = nb.math('MULTIPLY', _band(nb, rho, 0.93, 0.035, 0.015), nb.math('MULTIPLY', MK._smooth(nb, diag, -0.05, -0.45), front))
    top = MK._smooth(nb, zn, 0.15, 0.85)
    low = MK._smooth(nb, zn, -0.15, -0.85)
    panes = []
    for (cx, cz), (w, h), ang, soft, k in PANES:
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        dx, dz = nb.math('SUBTRACT', x, cx), nb.math('SUBTRACT', z, cz)
        u = nb.math('ADD', nb.math('MULTIPLY', dx, ca), nb.math('MULTIPLY', dz, sa))
        v = nb.math('SUBTRACT', nb.math('MULTIPLY', dz, ca), nb.math('MULTIPLY', dx, sa))
        hw = w / 2
        spring = h / 2 - hw
        vt = nb.math('MAXIMUM', nb.math('SUBTRACT', v, spring), 0.0)
        ell = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', u, hw), nb.math('DIVIDE', vt, hw), 0.0))
        e = soft / hw
        shape = nb.math('MULTIPLY', MK._smooth(nb, ell, 1.0 + e, 1.0 - e), MK._smooth(nb, v, -h / 2 - soft, -h / 2 + soft))
        bars = nb.math('MAXIMUM', MK._smooth(nb, nb.math('ABSOLUTE', u), 0.0036, 0.002),
                       MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', v, spring)), 0.0036, 0.002))
        # the lower half fades right out
        grad = nb.math('MULTIPLY', MK._smooth(nb, v, -h / 2, h * 0.1), k)
        panes.append(_mul(nb, shape, nb.math('SUBTRACT', 1.0, bars), grad))
    # the sheen bands: lines of constant w run down to the right across the upper left of the picture
    wv = nb.math('ADD', nb.math('MULTIPLY', x, 0.6), nb.math('MULTIPLY', nb.math('SUBTRACT', z, F.ZC), 0.8))
    # they fade out along their own length toward the face (an upright cut-off read as a seam down the forehead)
    along = nb.math('SUBTRACT', nb.math('MULTIPLY', x, 0.8), nb.math('MULTIPLY', nb.math('SUBTRACT', z, F.ZC), 0.6))
    keep = MK._smooth(nb, along, -0.06, -0.14)
    band1 = _band(nb, wv, 0.071, 0.015, 0.005)
    band2 = _band(nb, wv, 0.113, 0.0075, 0.0035)
    bands = nb.math('MULTIPLY', nb.math('MAXIMUM', band1, nb.math('MULTIPLY', band2, 0.9)), nb.math('MULTIPLY', keep, 0.85))
    pane = nb.math('MULTIPLY', MK.union(nb, panes + [bands]), nb.math('MULTIPLY', MK._smooth(nb, rho, 0.975, 0.95), front))
    return {'in': inside, 'rim': rim, 'rim_dark': rim_dark, 'top': top, 'low': low, 'pane': pane}


# ----------------------------------------------------------------------------- the gold's engraving
def engraving(nb: NB, pos) -> tuple:
    """(dark, light) masks of the engraving, matching the high source's relief (mirrorkin_ultra.engraving)."""
    x, y, z = nb.sep(pos)
    phi = nb.attribute('rphi').outputs['Fac']
    q = nb.attribute('rq').outputs['Fac']
    rr = nb.attribute('rrho').outputs['Fac']
    gk = nb.math('ABSOLUTE', nb.attribute('gk').outputs['Fac'])
    not_glove = nb.math('SUBTRACT', 1.0, MK._smooth(nb, gk, 0.2, 0.6))
    front = MK._smooth(nb, y, -0.018, -0.024)
    glass = nb.math('MULTIPLY', MK._smooth(nb, rr, 1.0, 0.99), front)
    ring = _mul(nb, nb.math('SUBTRACT', 1.0, glass), not_glove, MK._smooth(nb, z, F.ZC - F.GB - 0.045, F.ZC - F.GB - 0.03))
    # pearl beading: the gaps between the pearls
    c = nb.math('COSINE', nb.math('MULTIPLY', phi, 200.0))
    gap = MK._smooth(nb, nb.math('MULTIPLY', c, c), 0.12, 0.0)
    bead = _mul(nb, gap, MK._smooth(nb, q, 0.003, 0.0045), MK._smooth(nb, q, 0.012, 0.0105), front, ring)
    # the rope's twisted grooves
    f = nb.math('FRACT', nb.math('ADD', nb.math('MULTIPLY', phi, 120.0 / (2 * math.pi)), nb.math('DIVIDE', q, 0.011)))
    rope = _mul(nb, _band(nb, f, 0.5, 0.05, 0.035), MK._smooth(nb, q, 0.019, 0.021), MK._smooth(nb, q, 0.039, 0.037), front, ring)
    # a fine line in the cove
    cove = _mul(nb, _band(nb, q, 0.0148, 0.0008, 0.0005), front, ring)
    # the back: a double oval line round the polished field, the diamond and its star (2-turnaround back)
    back = _mul(nb, MK._smooth(nb, y, 0.033, 0.038), ring)
    oval = nb.math('MAXIMUM', _band(nb, rr, 0.715, 0.0035, 0.002), _band(nb, rr, 0.765, 0.0035, 0.002))
    dia = nb.math('ADD', nb.math('DIVIDE', nb.math('ABSOLUTE', x), 0.07), nb.math('DIVIDE', nb.math('ABSOLUTE', nb.math('SUBTRACT', z, F.ZC)), 0.13))
    dline = nb.math('MAXIMUM', _band(nb, dia, 0.94, 0.012, 0.008), _band(nb, dia, 1.06, 0.012, 0.008))
    star = nb.math('ADD', nb.math('DIVIDE', nb.math('ABSOLUTE', x), 0.025), nb.math('DIVIDE', nb.math('ABSOLUTE', nb.math('SUBTRACT', z, F.ZC)), 0.05))
    sline = _band(nb, star, 1.0, 0.05, 0.03)
    # the arabesques inside the border (2-turnaround back): C-scrolls opening toward the diamond, above, beside, below it
    arcs = []
    for s in (1, -1):
        for cx, cz, r in ((0.052, 0.148, 0.034), (0.1, 0.0, 0.042), (0.052, -0.148, 0.034)):
            dx, dz = nb.math('SUBTRACT', x, cx * s), nb.math('SUBTRACT', z, F.ZC + cz)
            d = nb.vmath('LENGTH', nb.comb(dx, dz, 0.0))
            outward = MK._smooth(nb, nb.math('DIVIDE', nb.math('MULTIPLY', dx, float(s)), nb.math('MAXIMUM', d, 1e-4)), -0.35, 0.05)
            arcs.append(nb.math('MULTIPLY', _band(nb, d, r, 0.0011, 0.0007), outward))
            arcs.append(nb.math('MULTIPLY', _band(nb, d, r * 0.45, 0.001, 0.0006), outward))
    backm = nb.math('MULTIPLY', MK.union(nb, [oval, dline, sline] + arcs), back)
    dark = MK.union(nb, [bead, rope, cove, backm])
    light = _mul(nb, MK._smooth(nb, star, 0.9, 0.5), back)
    # review round 2: crisp pale-gold highlights on the rope's crests and the pearls' tops
    crest = _mul(nb, _band(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', f, 0.5)), 0.5, 0.1, 0.06),
                 MK._smooth(nb, q, 0.019, 0.022), MK._smooth(nb, q, 0.039, 0.036), front, ring)
    pearl = _mul(nb, MK._smooth(nb, nb.math('MULTIPLY', c, c), 0.6, 0.95), MK._smooth(nb, q, 0.004, 0.006),
                 MK._smooth(nb, q, 0.011, 0.009), front, ring)
    light = MK.union(nb, [light, crest, pearl])
    return dark, light


def stitching(nb: NB):
    """The gloves' stitching: three dashed lines down the back of the hand and a seam round the cuff (4-details 3)."""
    gk = nb.math('ABSOLUTE', nb.attribute('gk').outputs['Fac'])
    ga = nb.attribute('ga').outputs['Fac']
    gu = nb.attribute('gu').outputs['Fac']
    gt = nb.attribute('gt').outputs['Fac']
    on = MK._smooth(nb, gk, 0.4, 0.6)
    dash = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', nb.math('DIVIDE', ga, 0.0055)), 0.5)), 0.32, 0.22)
    back = MK._smooth(nb, gu, -0.002, -0.008)
    along = nb.math('MULTIPLY', MK._smooth(nb, ga, 0.028, 0.034), MK._smooth(nb, ga, 0.092, 0.086))
    lines = MK.union(nb, [_band(nb, gt, v, 0.0007, 0.0004) for v in (-0.0125, 0.0, 0.0125)])
    st = _mul(nb, lines, dash, back, along, on)
    ang = nb.math('ARCTAN2', gu, gt)
    dash2 = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', nb.math('MULTIPLY', ang, 9.0)), 0.5)), 0.32, 0.22)
    seam = _mul(nb, _band(nb, ga, -0.024, 0.0008, 0.0005), dash2, on)
    return nb.math('MAXIMUM', st, seam)


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    col = MP.colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    c = nb.attribute(attr).outputs['Color']
    dark, light = engraving(nb, pos)
    c = nb.mix(nb.math('MULTIPLY', light, 0.65), c, _rgb(nb, col['gold_hi']))
    c = nb.mix(nb.math('MULTIPLY', dark, 0.85), c, _rgb(nb, col['gold_deep']))
    c = nb.mix(nb.math('MULTIPLY', stitching(nb), 0.85), c, _rgb(nb, col['stitch']))
    # review round 1: the glass per pixel (a crisp edge at the lip, a thin bright rim, the window panes)
    gm = glass_masks(nb, pos)
    # review round 2: an even tone round the glass colour (the lit top read at the highlight colour, the bottom grey):
    # the top a little deeper, the bottom a little lighter; then the rim and the reflections
    obs = bool(pal.get('obsidian'))
    # Obsidian's black glass stays flat (its faint gradients broke into dark compression blocks)
    g = nb.mix(nb.math('MULTIPLY', gm['top'], 0.0 if obs else 0.22), _rgb(nb, col['glass']), _rgb(nb, col['glass_deep']))
    g = nb.mix(nb.math('MULTIPLY', gm['low'], 0.0 if obs else 0.3), g, _rgb(nb, col['glass_hi']))
    g = nb.mix(nb.math('MULTIPLY', gm['rim_dark'], 0.75), g, _rgb(nb, col['bevel_dark']))
    g = nb.mix(gm['rim'], g, _rgb(nb, col['glass_hi']))
    # Obsidian keeps only its bevel (review round 3: its window reflection broke into dark compression blocks)
    g = nb.mix(nb.math('MULTIPLY', gm['pane'], 0.0 if obs else 0.92), g, _rgb(nb, col['pane']))
    c = nb.mix(gm['in'], c, g)
    # the lip's steep inner wall between the glass and the beads: a dark bevel (it read as a pale crinkled foil)
    rq = nb.attribute('rq').outputs['Fac']
    xx, yy, zz = nb.sep(pos)
    rho_px = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', xx, F.GA), nb.math('DIVIDE', nb.math('SUBTRACT', zz, F.ZC), F.GB), 0.0))
    lipw = _mul(nb, MK._smooth(nb, rq, 0.0052, 0.004), MK._smooth(nb, rho_px, 0.978, 0.986), MK._smooth(nb, yy, -0.016, -0.022))
    c = nb.mix(nb.math('MULTIPLY', lipw, 0.85), c, _rgb(nb, col['gold_lo']))
    fm = face_marks(nb, pos, bool(pal.get('obsidian')))
    c = nb.mix(nb.math('MULTIPLY', fm['lid'], 0.62), c, _rgb(nb, col['lid']))
    c = nb.mix(nb.math('MULTIPLY', fm['blush'], 0.5), c, _rgb(nb, col['blush']))
    c = nb.mix(nb.math('MULTIPLY', fm['spark'], 0.9), c, _rgb(nb, col['sparkle']))
    c = nb.mix(nb.math('MULTIPLY', fm['nose'], 0.75), c, _rgb(nb, col['nose']))
    c = nb.mix(nb.math('MULTIPLY', fm['nose_hi'], 0.6), c, _rgb(nb, col['sparkle']))
    c = nb.mix(fm['ink'], c, _rgb(nb, col['brow']))
    c = nb.mix(fm['mouth'], c, _rgb(nb, col['mouth']))
    c = nb.mix(fm['lash'], c, _rgb(nb, col['lash']))
    c = nb.mix(fm['shut'], c, _rgb(nb, col['lash']))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def glow_material(name: str, marks, pal: dict | None = None) -> bpy.types.Material:
    """The base look: the paint's faint `glow` (the glass's sheen, the gold's ridges), none under the face's strokes.
    Obsidian: `glow_obsidian` (the silver's ridges) and its face glowing pale in the black glass."""
    obs = bool(pal and pal.get('obsidian'))
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    g = nb.attribute('glow_obsidian' if obs else 'glow').outputs['Fac']
    fm = face_marks(nb, pos, obs)
    strokes = MK.union(nb, [fm['ink'], fm['mouth'], fm['lash'], fm['shut']])
    gm = glass_masks(nb, pos)
    if obs:
        # review round 1: a faint glow on the face's lines only (the brows, the smile, the nose, the sparkles; the lids
        # and the blush barely), so the eyes never bloom
        face = MK.union(nb, [nb.math('MULTIPLY', fm['lid'], 0.22), nb.math('MULTIPLY', fm['blush'], 0.2), nb.math('MULTIPLY', fm['nose'], 0.35),
                             nb.math('MULTIPLY', fm['spark'], 0.6), nb.math('MULTIPLY', fm['ink'], 0.85), nb.math('MULTIPLY', fm['mouth'], 0.85)])
        g = nb.math('MAXIMUM', nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, fm['lash'])), face)
        # review round 2: its reflections show faintly in the black glass
        g = nb.math('MAXIMUM', g, nb.math('MULTIPLY', gm['rim'], 0.3))
    else:
        g = nb.math('MAXIMUM', g, nb.math('MULTIPLY', nb.math('MAXIMUM', gm['pane'], gm['rim']), 0.4))
        g = nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, nb.math('MINIMUM', nb.math('ADD', strokes, fm['lid']), 1.0)))
    g = nb.math('MINIMUM', nb.math('MAXIMUM', g, 0.0), 1.0)
    em = nb.new('ShaderNodeEmission')
    nb.link(nb.comb(g, g, g), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the eyes
def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """A painted eye (2-turnaround front, 4-details 2): a large dark violet iris a little above the middle, its lower
    part lit violet, a deep pupil, a thin dark ring, the white round it, a thick lid line along the top, two catchlights
    (the same side in both eyes)."""
    col = MP.colours(pal or {'body': '#CFD8E3', 'belly': '#EEF3F8', 'accent': '#6C5CE7', 'eye': '#2B2B33'})
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.24, 0.42))
        nb.output(em.outputs[0])
        return m
    x, y, _z = nb.sep(nb.attribute('eyeuv').outputs['Vector'])
    side = nb.attribute('eye_side').outputs['Fac']
    # review round 2: the iris a little toward the nose and down, so the white shows on its outer side and under the lid
    ix, iy = nb.math('ADD', x, nb.math('MULTIPLY', side, 0.08)), nb.math('ADD', y, 0.04)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), 0.7)      # 1 at the iris's edge
    r = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    # round 3: a darker iris (4-details 2), the violet light only in its lower part
    low = MK._smooth(nb, nb.math('DIVIDE', iy, 0.74), -0.2, -0.85)
    iris = nb.mix(nb.math('MULTIPLY', low, 0.7), _rgb(nb, col['iris']), _rgb(nb, col['iris_lo']))
    ang = nb.math('ARCTAN2', iy, ix)
    fib = _mul(nb, nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 26.0)), 0.5), 0.5),
               MK._smooth(nb, ri, 0.45, 0.55), MK._smooth(nb, ri, 0.92, 0.8))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.12), iris, _rgb(nb, col['pupil']))
    c = nb.mix(MK._smooth(nb, ri, 0.47, 0.43), iris, _rgb(nb, col['pupil']))
    c = nb.mix(MK._smooth(nb, ri, 0.9, 0.97), c, _rgb(nb, col['pupil']))
    c = nb.mix(MK._smooth(nb, ri, 1.0, 1.04), c, _rgb(nb, col['sclera']))
    # review round 2: a heavy black upper lid over the top of the iris, lowest at the outer corner where the wing
    # leaves it; only a thin line under the eye (no side ticks)
    xo = nb.math('MULTIPLY', x, side)                             # + toward the outer corner
    lid_y = nb.math('SUBTRACT', nb.math('SUBTRACT', 0.4, nb.math('MULTIPLY', nb.math('MULTIPLY', x, x), 0.2)), nb.math('MULTIPLY', xo, 0.12))
    c = nb.mix(MK._smooth(nb, nb.math('SUBTRACT', y, lid_y), -0.02, 0.02), c, _rgb(nb, col['lash']))
    under = MK._smooth(nb, y, 0.0, -0.25)
    c = nb.mix(nb.math('MULTIPLY', MK._smooth(nb, r, 0.93, 0.965), under), c, _rgb(nb, col['lash']))
    big = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, -0.2), nb.math('SUBTRACT', iy, 0.16), 0.0)), 0.15, 0.12)
    small = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, 0.2), nb.math('ADD', iy, 0.24), 0.0)), 0.075, 0.055)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, _rgb(nb, '#FBFCFE'))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the props
def prop_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """The props per pixel: the cloak panels' gold trim with a fine dark line inside it, and the embroidered border
    above the hem and up the front edge: a chain of gold diamond outlines between two running lines (4-details 5)."""
    col = MP.colours(pal)
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    part = nb.attribute('part').outputs['Fac']
    side = nb.attribute('side').outputs['Fac']
    ed = nb.attribute('ed').outputs['Fac']
    es = nb.attribute('es').outputs['Fac']
    pt = nb.attribute('pt').outputs['Fac']
    panel = nb.math('COMPARE', part, float(CL.PANEL), 0.4)
    outer = MK._smooth(nb, side, 0.5, 0.9)
    low = MK._smooth(nb, pt, 0.22, 0.4)
    hood = nb.math('COMPARE', part, float(CL.MANTLE), 0.4)
    trim = nb.math('MULTIPLY', MK._smooth(nb, ed, 0.0078, 0.0068), nb.math('MAXIMUM', panel, hood))
    c = nb.mix(trim, c, _rgb(nb, col['gold']))
    edge_line = _mul(nb, _band(nb, ed, 0.0085, 0.0007, 0.0004), nb.math('MAXIMUM', panel, hood))
    c = nb.mix(nb.math('MULTIPLY', edge_line, 0.8), c, _rgb(nb, col['gold_lo']))
    a = nb.math('SUBTRACT', nb.math('FRACT', nb.math('DIVIDE', es, 0.034)), 0.5)
    b = nb.math('DIVIDE', nb.math('SUBTRACT', ed, 0.026), 0.0085)
    dia = nb.math('ADD', nb.math('MULTIPLY', nb.math('ABSOLUTE', a), 2.0), nb.math('ABSOLUTE', b))
    # review round 1: bolder and brighter (it read as a faint band)
    chain = _band(nb, dia, 0.8, 0.16, 0.05)
    dots = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('MULTIPLY', nb.math('SUBTRACT', nb.math('ABSOLUTE', a), 0.5), 0.034),
                                                    nb.math('SUBTRACT', ed, 0.026), 0.0)), 0.0036, 0.0024)
    run = nb.math('MAXIMUM', _band(nb, ed, 0.0145, 0.0016, 0.0005), _band(nb, ed, 0.0375, 0.0016, 0.0005))
    emb = _mul(nb, MK.union(nb, [chain, dots, run]), panel, outer, low)
    c = nb.mix(emb, c, _rgb(nb, col['gold']))           # review round 2: the frame's gold (it read pale lilac)
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
