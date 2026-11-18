"""Aurelwyrm's paint (Art 2.1 Ultra): per-vertex colour and roughness for the skin, the ribbons and the props, the
per-pixel mouth line, the eyes, and the shape preview's colours.

Colours from CONTENT (#F2C14E scales, #FFF4D6 belly, #D64545 ribbon fins, #6B2D0F eyes) and variants.ts (Sunsoul:
#FFF6E0, #FFFFFF, #E8B923, #8A5A12). Derived from the palette (CONTENT has no hex for these; the pictures show where
they go):
  - the scales' pale raised edges (the scale gold lifted toward the belly cream) and their deeper gold grooves (the
    scale gold toward the eye brown): the film's roughness floor and grey studio dull a plain gold, so the shimmer is
    painted in;
  - the ribbons' deep roots (the crimson darkened), their lighter edges and tips (toward the cream) and their gold
    streaks (toward the scale gold);
  - the antlers' velvet cocoa (the eye brown lifted toward the cream) and their gold collars, the whiskers' cream-gold,
    the mane's gold locks (the base palette's scale gold in both looks: the Sunsoul picture keeps them gold), the ears'
    pink lining (the cream toward the crimson), the nose's tan (the cream toward the eye brown).
Sunsoul (the card: "white-gold scales with golden ribbon fins"): the scales, belly, ribbons and eyes take the variant's
colours; the antlers, whiskers, gold mane locks and collars keep their usual colours (the variant picture).
"""
from __future__ import annotations

import colorsys

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.nodes import new_mat
from lib.surface import smooth

BASE = {'body': '#F2C14E', 'belly': '#FFF4D6', 'accent': '#D64545', 'eye': '#6B2D0F'}


def lin(h: str) -> np.ndarray:
    return np.asarray(C.lin_rgb(h), np.float64)


def shadow(h: str, k: float) -> str:
    """A colour's shade: a gold turns warmer toward orange as it darkens (round 2: Sunsoul's #E8B923 read mustard and
    olive in shadow); other hues just darken."""
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    if 25.0 / 360 < hh < 70.0 / 360:
        hh -= 12.0 / 360
        ss = min(1.0, ss * 1.1)
    r, g, b = colorsys.hsv_to_rgb(hh, ss, vv * k)
    return '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in (r, g, b))


def colours(pal: dict) -> dict:
    body, belly, acc, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    gold = BASE['body']
    antler = C.mix_hex(BASE['eye'], BASE['belly'], 0.35)
    out = {
        'scale': body, 'scale_hi': C.mix_hex(body, belly, 0.6), 'scale_lit': C.mix_hex(body, '#FFFFFF', 0.45),
        'groove': C.mix_hex(body, eye, 0.2), 'side': C.mix_hex(body, belly, 0.42),
        'belly': belly, 'scute_edge': C.shade_hex(C.mix_hex(belly, body, 0.3), 0.9), 'scute_hi': C.mix_hex(belly, '#FFFFFF', 0.4),
        'face': belly, 'brow': C.mix_hex(belly, '#FFFFFF', 0.35), 'nose': C.mix_hex(eye, belly, 0.22),
        'nostril': C.shade_hex(C.mix_hex(belly, eye, 0.5), 0.45), 'lash': C.shade_hex(eye, 0.32), 'lid': C.shade_hex(body, 0.86),
        'mouth': C.shade_hex(C.mix_hex(eye, acc, 0.3), 0.62), 'lip': C.mix_hex(belly, body, 0.15),
        'ear_in': C.mix_hex(belly, acc, 0.3),
        # the ribbons
        # round 2: a warmer, lighter root (stacked dark roots read muddy), a pink-orange edge, fine veins
        'rib': acc, 'rib_root': shadow(acc, 0.84), 'rib_edge': C.mix_hex(C.mix_hex(acc, BASE['body'], 0.45), belly, 0.15),
        'rib_vein': shadow(acc, 0.7), 'rib_tip': C.mix_hex(acc, BASE['body'], 0.3),
        'rib_sheen': C.mix_hex(C.mix_hex(acc, BASE['body'], 0.4), belly, 0.25),
        'rib_spark': C.mix_hex(BASE['body'], '#FFFFFF', 0.55),
        # the props (their usual colours in every look)
        'antler': antler, 'antler_dark': C.shade_hex(antler, 0.78), 'antler_tip': C.mix_hex(antler, BASE['belly'], 0.18),
        'collar': gold, 'collar_hi': C.mix_hex(gold, BASE['belly'], 0.5), 'collar_deep': C.mix_hex(gold, BASE['eye'], 0.3),
        'whisker': C.mix_hex(BASE['belly'], gold, 0.38), 'whisker_tip': C.mix_hex(gold, BASE['eye'], 0.08),
        # (polish: warmer all through, no brown at the roots: the shade read olive)
        'mane': C.mix_hex(gold, BASE['accent'], 0.12), 'mane_hi': C.mix_hex(gold, BASE['belly'], 0.45),
        'mane_tip': C.mix_hex(gold, BASE['accent'], 0.42), 'mane_root': C.mix_hex(gold, BASE['accent'], 0.22),
        'fluff': belly, 'fluff_root': C.mix_hex(belly, body, 0.3),
        'bag_rim': '#C85A62', 'bag_deep': '#3A1416', 'bag_bed': '#9A3A46', 'bag_lip': C.shade_hex(C.mix_hex(eye, acc, 0.3), 0.62),
        'eye': eye, 'iris_ring': C.mix_hex(eye, gold, 0.6), 'iris_deep': C.shade_hex(eye, 0.62),
        'pupil': '#120804', 'sclera': '#FBF6EE',
    }
    if sum(int(body[i:i + 2], 16) for i in (1, 3, 5)) > 3 * 235:
        # (round 3) a white-gold body (Sunsoul): its sheen and grooves warm gold from the variant's own gold, never
        # flat chalk (the picture's white-gold shimmer)
        out.update({'scale_hi': C.mix_hex(body, acc, 0.2), 'scale_lit': C.mix_hex(body, acc, 0.38),
                    'groove': C.shade_hex(C.mix_hex(body, acc, 0.5), 0.94), 'side': C.mix_hex(body, belly, 0.4)})
    return out


def _mix(rgb: np.ndarray, col: np.ndarray, k) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    return rgb * (1 - k[:, None]) + col[None] * k[:, None]


# ============================================================================= the skin
SKIN_ATTRS = ('glit', 'tw', 'hw', 'belly', 'scale_rho', 'scale_du', 'scale_id', 'scute_fr', 'scute_on', 'scute_edge', 'scute_id',
              'hscale', 'hrho', 'hid', 'lid', 'lash', 'closed', 'rim', 'nostril', 'lip', 'mspan', 'mcorner', 'phi_body',
              'brow', 'snout', 'nose', 'ear', 'ear_in', 'mouth')


def skin_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal)
    n = len(I['tw'])
    jit = I['scale_id'] - 0.5
    on = smooth(1.15, 0.95, I['scale_rho'])                  # on a scale (not in a groove or off the lattice)
    rho = np.clip(I['scale_rho'], 0, 1.3)
    # (build 2) the base lifted 10% (linear): the film's grey studio and roughness floor dull the gold
    lift_k = 1.18 if pal['body'].upper() == BASE['body'] else 1.0                # (build 3: 1.1 measured #E3B347)
    rgb = np.tile(lin(col['scale']), (n, 1)) * (lift_k + 0.12 * jit)[:, None]
    # each scale bright toward its raised free edge (the shimmer), a pale rim just inside its outline, deeper gold in
    # the grooves (4-details panel 6)
    lift = smooth(-0.4, 0.85, I['scale_du']) * smooth(0.98, 0.55, rho) * on
    rgb = _mix(rgb, lin(col['scale_hi']), 0.55 * lift)
    # (round 3) a soft highlight across each scale's raised half (4-details panel 6)
    rgb = _mix(rgb, lin(col['scale_lit']), 0.5 * np.exp(-((rho - 0.62) / 0.24) ** 2) * smooth(-0.3, 0.5, I['scale_du']) * on)
    groove = smooth(0.88, 1.04, rho) * smooth(0.0, 0.3, I['tw'])
    gap = smooth(1.08, 1.25, np.clip(I['scale_rho'], 0, 2.0)) * smooth(0.0, 0.3, I['tw'])
    rgb = _mix(rgb, lin(col['groove']), 0.45 * groove * (1.0 - 0.6 * gap))
    # the glitter: single bright flecks on the scales' faces (4-details panel 6)
    rgb = _mix(rgb, np.minimum(lin(col['scale_lit']) * 1.3, 1.0), 0.9 * np.clip(I['glit'], 0, 1))
    # the lowest flank rows lighten toward the belly
    phi = np.abs(I['phi_body'])
    rgb = _mix(rgb, lin(col['side']), 0.45 * smooth(1.6, 1.98, phi) * I['tw'])
    # the head: its small scales' outlines, a soft brow over each eye
    hrho = np.clip(I['hrho'], 0, 1.3)
    hs = np.clip(I['hscale'], 0, 1)
    rgb = rgb * (1.0 + 0.06 * (I['hid'] - 0.5) * hs)[:, None]
    rgb = _mix(rgb, lin(col['groove']), 0.38 * smooth(0.82, 1.0, hrho) * hs)
    rgb = _mix(rgb, lin(col['scale_hi']), 0.3 * smooth(0.8, 0.3, hrho) * hs)
    # the belly and the pale face: the chevrons, each a touch lighter toward its raised back edge, a soft seam
    bel = np.tile(lin(col['belly']), (n, 1)) * (0.985 + 0.03 * (I['scute_id'] - 0.5))[:, None]
    bel = _mix(bel, lin(col['scute_hi']), 0.3 * np.sin(np.clip(I['scute_fr'], 0, 1) * np.pi * 0.62) ** 2 * I['scute_on'])
    bel = _mix(bel, lin(col['scute_edge']), 0.45 * smooth(0.3, 0.0, I['scute_fr']) * I['scute_on'])
    pale = np.clip(I['belly'], 0, 1)
    rgb = rgb * (1 - pale[:, None]) + bel * pale[:, None]
    rgb = _mix(rgb, lin(col['lip']), 0.4 * np.clip(I['lip'], 0, 1) * pale)
    rgb = _mix(rgb, lin(col['brow']), 0.85 * np.clip(I['brow'] * 1.3, 0, 1) * (1 - I['lash']))
    rgb = _mix(rgb, lin(col['nose']), 0.92 * np.clip(I['nose'], 0, 1))
    rgb = _mix(rgb, lin(col['ear_in']), 0.9 * np.clip(I['ear_in'], 0, 1))
    # the eyes' lids and lashes, the nostrils, the mouth's corners
    rgb = _mix(rgb, lin(col['lid']), 0.12 * I['lid'] * (1 - I['lash']))
    rgb = _mix(rgb, lin(col['lash']), 0.95 * np.clip(I['lash'] * 1.25, 0, 1))
    rgb = _mix(rgb, lin(col['lash']), 0.9 * np.clip(I['closed'] * 1.2, 0, 1))
    rgb = _mix(rgb, lin(col['nostril']), 0.5 * I['nostril'])
    rgb = _mix(rgb, lin(col['mouth']), 0.8 * np.clip(I['mcorner'], 0, 1))
    # gloss: the scales glossy (a clear coat on their raised middles), the grooves matte, the belly satin, the face soft
    rough = 0.4 - 0.06 * lift + 0.2 * groove
    rough = rough * (1 - pale) + (0.5 + 0.1 * np.clip(I['scute_edge'], 0, 1)) * pale
    rough = rough + 0.15 * I['snout'] * pale + 0.25 * np.clip(I['mouth'] * 1.4, 0, 1) + 0.2 * I['nostril'] + 0.1 * I['brow']
    rough = rough - 0.18 * np.clip(I['glit'], 0, 1)
    coat = (0.32 + 0.12 * lift + 0.25 * np.clip(I['glit'], 0, 1)) * (1 - groove) * (1 - pale) + 0.06 * pale
    coat = coat * (1 - np.clip(I['mouth'] * 1.4, 0, 1)) * (1 - 0.7 * np.clip(I['ear_in'], 0, 1))
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


# ============================================================================= the ribbons
FIN_ATTRS = ('rib_u', 'rib_v', 'rib_id', 'rib_kind')


def fin_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    """Silk (round 2): the crimson a touch deeper at the root, fine parallel veins along the length, a lighter
    pink-orange edge and tip (4-details panel 3); no broad stripes."""
    col = colours(pal)
    n = len(I['rib_u'])
    u, v, rid = I['rib_u'], I['rib_v'], I['rib_id']
    rgb = np.tile(lin(col['rib']), (n, 1)) * (1.0 + 0.06 * (rid - 0.5))[:, None]
    rgb = _mix(rgb, lin(col['rib_root']), 0.3 * smooth(0.25, 0.0, u))
    # (round 3) a lighter orange-pink sheen band along one side, clear lengthwise veins, sparkle flecks
    band = np.exp(-((v - 0.32 + 0.2 * (rid - 0.5)) / 0.2) ** 2) * smooth(0.08, 0.35, u)
    rgb = _mix(rgb, lin(col['rib_sheen']), 0.5 * band)
    vein = np.abs(np.sin(np.pi * 4.5 * (v + 0.13 * rid))) ** 8 * smooth(0.05, 0.2, u) * smooth(0.95, 0.7, np.abs(v))
    rgb = _mix(rgb, lin(col['rib_vein']), 0.55 * vein)
    hsh = np.mod(np.sin(u * 927.13 + v * 331.71 + rid * 71.3) * 43758.5453, 1.0)
    # (build 9: white flecks at 3.5% read as polka dots; sparse warm glints now)
    spark = (hsh > 0.988) * smooth(0.1, 0.3, u)
    rgb = _mix(rgb, lin(col['rib_sheen']), 0.5 * spark)
    rgb = _mix(rgb, lin(col['rib_edge']), 0.6 * smooth(0.7, 1.0, np.abs(v)) * smooth(0.05, 0.3, u))
    rgb = _mix(rgb, lin(col['rib_tip']), 0.4 * smooth(0.6, 1.0, u))
    rough = 0.52 + 0.06 * smooth(0.6, 1.0, u)
    coat = 0.06 + 0.04 * smooth(0.7, 1.0, np.abs(v))
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), rough, coat], axis=1)


# ============================================================================= the props
PROP_ATTRS = ('ant', 'ant_t', 'collar', 'wh', 'wh_u', 'mn', 'mn_u', 'mn_v', 'mn_id', 'mn_cream', 'bag', 'bag_d', 'bag_floor')


def prop_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal)
    n = len(I['ant'])
    rgb = np.zeros((n, 3))
    rough = np.tile(np.array([1.0, 0.5, 0.1]), (n, 1))
    an = I['ant'] > 0.5
    if an.any():
        t, cl = I['ant_t'][an], I['collar'][an]
        a = _mix(np.tile(lin(col['antler']), (int(an.sum()), 1)), lin(col['antler_dark']), 0.6 * smooth(0.35, 0.05, t))
        a = _mix(a, lin(col['antler_tip']), 0.5 * smooth(0.6, 1.0, t))
        g = _mix(np.tile(lin(col['collar']), (int(an.sum()), 1)), lin(col['collar_deep']), 0.5 * smooth(0.6, 1.0, cl))
        a = _mix(a, g, cl)
        rgb[an] = a
        rough[an] = np.stack([np.ones(int(an.sum())), 0.92 - 0.48 * cl, 0.0 + 0.3 * cl], axis=1)
    wh = I['wh'] > 0.5
    if wh.any():
        u = I['wh_u'][wh]
        # (round 3) gold toward the middle, a pale feathered end
        w_ = _mix(np.tile(lin(col['whisker']), (int(wh.sum()), 1)), lin(col['whisker_tip']), 0.6 * smooth(0.2, 0.6, u))
        rgb[wh] = _mix(w_, lin(C.mix_hex(BASE['belly'], BASE['body'], 0.35)), smooth(0.8, 0.99, u))   # the pale-gold tuft
        rough[wh] = np.stack([np.ones(int(wh.sum())), np.full(int(wh.sum()), 0.42), np.full(int(wh.sum()), 0.25)], axis=1)
    mn = I['mn'] > 0.5
    if mn.any():
        u, v, i = I['mn_u'][mn], np.abs(I['mn_v'][mn]), I['mn_id'][mn]
        cr = I['mn_cream'][mn]
        g = np.tile(lin(col['mane']), (int(mn.sum()), 1)) * (1.1 + 0.1 * (i - 0.5))[:, None]
        g = _mix(g, lin(col['mane_root']), 0.4 * smooth(0.25, 0.0, u))
        g = _mix(g, lin(col['mane_hi']), 0.4 * smooth(0.1, 0.45, u) * smooth(0.7, 0.1, v))
        g = _mix(g, lin(col['mane_tip']), 0.75 * smooth(0.5, 1.0, u))
        f = _mix(np.tile(lin(col['fluff']), (int(mn.sum()), 1)), lin(col['fluff_root']), 0.5 * smooth(0.35, 0.0, u))
        g = g * (1 - cr[:, None]) + f * cr[:, None]
        rgb[mn] = g
        # (round 2) soft feathers, not glossy plastic spikes
        rough[mn] = np.stack([np.ones(int(mn.sum())), 0.6 + 0.08 * v, np.full(int(mn.sum()), 0.04)], axis=1)
    bag = I['bag'] > 0.5
    if bag.any():
        d, fl = I['bag_d'][bag], I['bag_floor'][bag]
        bc = _mix(np.tile(lin(col['bag_rim']), (int(bag.sum()), 1)), lin(col['bag_deep']), smooth(0.25, 0.75, d))
        bc = _mix(bc, lin(col['bag_lip']), smooth(0.12, 0.03, d))
        bc = _mix(bc, lin(col['bag_bed']), 0.6 * fl)
        rgb[bag] = bc
        rough[bag] = np.stack([np.ones(int(bag.sum())), np.full(int(bag.sum()), 0.66), np.full(int(bag.sum()), 0.05)], axis=1)
    return np.clip(rgb, 0, 1), rough


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import aurelwyrm_ultra as R
    vid, vpal = next(iter(R.VARIANTS.items()))
    vattr = U.variant_attr(vid, R.ID)
    for ob in body_srcs:
        I = {k: _get(ob, k, 2.0 if k in ('scale_rho', 'hrho') else 0.0) for k in SKIN_ATTRS}
        rgb, rough = skin_paint(I, R.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.set_colour_attr(ob, vattr, skin_paint(I, vpal)[0])
    for ob in fins:
        I = {k: _get(ob, k) for k in FIN_ATTRS}
        rgb, rough = fin_paint(I, R.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.set_colour_attr(ob, vattr, fin_paint(I, vpal)[0])
    for ob in props:
        I = {k: _get(ob, k) for k in PROP_ATTRS}
        rgb, rough = prop_paint(I, R.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.set_colour_attr(ob, vattr, prop_paint(I, vpal)[0])


# ============================================================================= per pixel
def body_material(name: str, attr: str, pal: dict, marks):
    """The skin's colour pass: its paint plus the mouth's one clean line, per pixel from the height above the line
    (linear, so it interpolates exactly)."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    col = colours(pal)
    md = nb.math('ABSOLUTE', nb.attribute('mdz').outputs['Fac'])
    ln = nb.math('MULTIPLY', nb.smooth(md, 0.0032, 0.0011), nb.smooth(nb.attribute('mspan').outputs['Fac'], 0.05, 0.6))
    c = nb.mix(nb.math('MULTIPLY', ln, 0.9), c, nb.rgb(C.lin(col['mouth'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= the eyes
IRIS_RX, IRIS_RY, PUPIL_R = 0.95, 0.66, 0.27   # round 3: the iris fills the opening sideways and touches the lid


def eye_material(name: str, rough_pass: bool, pal: dict):
    """Big kind eyes (3-faces neutral, 4-details panel 2): a large warm brown iris filling the almond opening sideways
    (CONTENT's eye colour, an amber-gold ring toward its rim, fine radial fibres, a thin dark rim), a round pupil, the
    gold upper lid just touching the iris's top with a strong dark lash line under it, two catchlights."""
    col = colours(pal)
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    from monsters.breeds import aurelwyrm_form as F
    asp = F.EYE_SHAPE[1] / F.EYE_SHAPE[0]
    ix = nb.math('ADD', x, nb.math('MULTIPLY', side, 0.03))
    iy = nb.math('MULTIPLY', nb.math('ADD', y, 0.02), asp)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, IRIS_RX), nb.math('DIVIDE', iy, IRIS_RY), 0.0))
    iris = nb.ramp(ri, [(0.0, C.lin(col['iris_deep'])), (0.3, C.lin(col['eye'])),
                        (0.62, C.lin(C.mix_hex(col['eye'], col['iris_ring'], 0.55))), (0.84, C.lin(col['iris_ring'])),
                        (0.94, C.lin(col['iris_deep'])), (1.0, C.lin('#1E0E06')), (1.05, C.lin(col['sclera'])),
                        (1.8, C.lin(col['sclera']))])
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 36.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', nb.smooth(ri, 0.35, 0.6), nb.smooth(ri, 0.97, 0.85)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.22), iris, nb.rgb(C.lin(col['iris_ring'])))
    pr = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), PUPIL_R)
    iris = nb.mix(nb.smooth(pr, 1.0, 0.9), iris, nb.rgb(C.lin(col['pupil'])))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, nb.math('MULTIPLY', side, 0.2)), nb.math('SUBTRACT', iy, 0.2), 0.0)), 0.12, 0.09)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, nb.math('MULTIPLY', side, 0.18)), nb.math('ADD', iy, 0.16), 0.0)), 0.055, 0.035)
    c = nb.mix(nb.math('MAXIMUM', big, small), iris, nb.rgb((1.0, 1.0, 1.0)))
    # the upper lid just over the iris's top, a strong dark lash line under it, thicker toward the outer corner
    x2 = nb.math('MULTIPLY', x, x)
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', x, side), 0.1, 0.9), 0.08)
    edge = nb.math('ADD', nb.math('ADD', y, outer), nb.math('MULTIPLY', x2, 0.18))
    lash = nb.smooth(edge, 0.66, 0.74)
    c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
    lid = nb.smooth(edge, 0.84, 0.9)
    c = nb.mix(lid, c, nb.rgb(C.lin(C.shade_hex(pal['body'], 0.9))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= the shape preview
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import aurelwyrm_carve as CV
    from monsters.breeds import aurelwyrm_ultra as R
    L = CV._LAST
    if L and L.get('n') == len(co):
        I = {k: np.asarray(L.get(k, np.full(len(co), 2.0 if k in ('scale_rho', 'hrho') else 0.0)), np.float64) for k in SKIN_ATTRS}
        I['mouth'] = np.zeros(len(co)) if 'mouth' not in L else L['mouth']
        return skin_paint(I, R.PALETTE)[0]
    from monsters.breeds import aurelwyrm_scales as SC
    z = SC.zones(co)
    return np.where(z['belly'][:, None], lin(R.PALETTE['belly'])[None], lin(R.PALETTE['body'])[None])


def preview_prop_colour(name: str):
    col = colours(BASE)
    return {'antlers': col['antler'], 'whiskers': col['whisker'], 'mane': col['mane'], 'mouthbag': col['bag_deep']}.get(name, col['mane'])
