"""Coilfang's paint (Art 2.1 Ultra): per-vertex colour and roughness for the skin and the props, the per-pixel mouth line
and feather barbs, the eyes, and the shape preview's colours.

Colours from CONTENT (#2FA37A scales, #DDF2D3 belly, #E8C14E crest, #1B3A2B eyes) and variants.ts (Imperial: #D4A017,
#FFF0B8, #8A1C1C, #1B3A2B). Derived (CONTENT has no hex for these; the card and the pictures show them): the argyle's
darker jade (the card's #23845F; Imperial: its gold darkened and warmed), the scales' lighter raised edges and darker
grooves (the scale colour lifted toward the belly / darkened), the crest's highlights and deep base (the gold lifted
toward cream / darkened toward amber: the film's roughness floor and grey studio flatten a plain gold, so the sheen is
painted in), the fangs' ivory, the tongue's and the mouth's rose (the pictures).
"""
from __future__ import annotations

import colorsys

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.nodes import new_mat
from lib.surface import smooth

IMPERIAL = 'imperial'


def lin(h: str) -> np.ndarray:
    return np.asarray(C.lin_rgb(h), np.float64)


def hsv_hex(h: str, hue: float | None = None, sat_k: float = 1.0, val_k: float = 1.0) -> str:
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    hh = hh if hue is None else hue / 360.0
    r, g, b = colorsys.hsv_to_rgb(hh, min(1.0, ss * sat_k), min(1.0, vv * val_k))
    return '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in (r, g, b))


def colours(pal: dict) -> dict:
    body, belly, acc, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    gold = acc.upper() != '#8A1C1C'
    imperial = body.upper() == '#D4A017'
    dark = hsv_hex(body, sat_k=1.08, val_k=0.66) if imperial else '#1F7656'
    c = {
        'scale': body, 'dark': dark, 'scale_hi': C.mix_hex(body, belly, 0.32), 'dark_hi': C.mix_hex(dark, body, 0.45),
        'groove': C.shade_hex(body, 0.55), 'dark_groove': C.shade_hex(dark, 0.6),
        'side': C.mix_hex(body, belly, 0.45), 'belly': belly, 'scute_edge': C.shade_hex(C.mix_hex(belly, body, 0.25), 0.88),
        'scute_hi': C.mix_hex(belly, '#FFFFFF', 0.35), 'face': C.mix_hex(body, belly, 0.08), 'vee': dark,
        'nostril': C.shade_hex(body, 0.3), 'lash': '#121512', 'lid': C.shade_hex(body, 0.82), 'mouth': C.shade_hex(body, 0.32),
        'lip': C.mix_hex(belly, body, 0.12),
        # the crest: the plain gold reads dark and flat in the film, so its sheen is painted in
        'gold': acc, 'gold_hi': C.mix_hex(acc, '#FFF4C4', 0.55) if gold else hsv_hex(acc, sat_k=0.92, val_k=1.45),
        # round 3: the shaded side warm orange-gold (it went khaki-olive under the cool fill)
        'gold_deep': C.mix_hex(acc, '#D2560A', 0.62) if gold else hsv_hex(acc, val_k=0.62),
        'shaft': C.mix_hex(acc, '#FFF8DC', 0.6) if gold else hsv_hex(acc, sat_k=0.8, val_k=1.6),
        'fang': '#FBF9F2', 'fang_root': '#EDE7D8', 'tongue': '#D2546C', 'tongue_dark': '#9C2E46',
        'bag_rim': '#D9687C', 'bag_deep': '#4A1622', 'bag_bed': '#A23A50', 'bag_lip': '#2C4A38',
        'eye': eye, 'iris_ring': C.mix_hex(eye, '#4FB070', 0.55), 'iris_deep': C.shade_hex(eye, 0.7),
        'pupil': '#07090A', 'sclera': '#F4F6F2',
    }
    return c


def _mix(rgb: np.ndarray, col: np.ndarray, k) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    return rgb * (1 - k[:, None]) + col[None] * k[:, None]


# ============================================================================= the skin
SKIN_ATTRS = ('tw', 'hw', 'belly', 'scale_rho', 'scale_du', 'scale_id', 'dark', 'scute_fr', 'scute_on', 'scute_edge', 'scute_id',
              'hscale', 'hrho', 'hid', 'lid', 'lash', 'closed', 'rim', 'nostril', 'lip', 'mspan', 'mcorner', 'phi_body', 'vee',
              'snout', 'mouth')


def skin_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal)
    n = len(I['tw'])
    jit = I['scale_id'] - 0.5
    on = smooth(1.15, 0.95, I['scale_rho'])                  # on a lattice scale (not in a groove or off the lattice)
    rho = np.clip(I['scale_rho'], 0, 1.3)
    dark = np.clip(I['dark'], 0, 1)
    base = np.tile(lin(col['scale']), (n, 1)) * (1.0 + 0.07 * jit)[:, None]
    dk = np.tile(lin(col['dark']), (n, 1)) * (1.0 + 0.06 * jit)[:, None]
    rgb = base * (1 - dark[:, None]) + dk * dark[:, None]
    # each scale lighter toward its raised free edge and its middle, its outline darker (crisp shields, 4-details panel 6)
    lift = smooth(-0.3, 0.9, I['scale_du']) * smooth(0.95, 0.6, rho) * on
    hi = lin(col['scale_hi']) * (1 - dark[:, None]) + lin(col['dark_hi']) * dark[:, None]
    rgb = rgb * (1 - (0.32 * lift)[:, None]) + hi * (0.32 * lift)[:, None]
    gr = lin(col['groove']) * (1 - dark[:, None]) + lin(col['dark_groove']) * dark[:, None]
    groove = smooth(0.86, 1.02, rho) * smooth(0.0, 0.3, I['tw'])
    # (polish: the skin that opens between the scales on a bend's outside a soft mid tone, never dark patches)
    gap = smooth(1.08, 1.25, np.clip(I['scale_rho'], 0, 2.0)) * smooth(0.0, 0.3, I['tw'])
    gk = 0.55 * groove * (1.0 - 0.65 * gap)
    rgb = rgb * (1 - gk[:, None]) + gr * gk[:, None]
    # the lowest flank rows lighten toward the belly
    phi = np.abs(I['phi_body'])
    rgb = _mix(rgb, lin(col['side']), 0.5 * smooth(1.55, 1.93, phi) * I['tw'] * (1 - dark))
    # the head: its small scales' outlines, the forehead's chevron, a smooth face a touch lighter
    hrho = np.clip(I['hrho'], 0, 1.3)
    hs = np.clip(I['hscale'], 0, 1)
    rgb = _mix(rgb, lin(col['face']), 0.5 * I['snout'])
    rgb = rgb * (1.0 + 0.06 * (I['hid'] - 0.5) * hs)[:, None]
    rgb = _mix(rgb, lin(col['groove']), 0.42 * smooth(0.82, 1.0, hrho) * hs)
    rgb = _mix(rgb, lin(col['scale_hi']), 0.18 * smooth(0.8, 0.3, hrho) * hs)
    rgb = _mix(rgb, lin(col['vee']), 0.85 * I['vee'])
    # the belly and the pale face: the scutes, each a touch lighter toward its raised back edge, darker seams
    bel = np.tile(lin(col['belly']), (n, 1)) * (0.985 + 0.03 * (I['scute_id'] - 0.5))[:, None]
    bel = _mix(bel, lin(col['scute_hi']), 0.32 * np.sin(np.clip(I['scute_fr'], 0, 1) * np.pi * 0.62) ** 2 * I['scute_on'])
    # round 3: each scute's soft shadow just below the one overlapping it (no painted seam lines), and the head's pale
    # scales outlined softly too
    bel = _mix(bel, lin(col['scute_edge']), 0.4 * smooth(0.3, 0.0, I['scute_fr']) * I['scute_on'])
    bel = _mix(bel, lin(col['scute_edge']), 0.4 * smooth(0.8, 1.0, np.clip(I['hrho'], 0, 1.3)) * np.clip(I['hscale'], 0, 1))
    pale = np.clip(I['belly'], 0, 1)
    rgb = rgb * (1 - pale[:, None]) + bel * pale[:, None]
    rgb = _mix(rgb, lin(col['lip']), 0.4 * np.clip(I['lip'], 0, 1) * pale)
    # the eyes' lids and lashes, the nostrils, the mouth's corners
    rgb = _mix(rgb, lin(col['lid']), 0.12 * I['lid'] * (1 - I['lash']))
    rgb = _mix(rgb, lin(col['lash']), 0.95 * np.clip(I['lash'] * 1.25, 0, 1))
    rgb = _mix(rgb, lin(col['lash']), 0.9 * np.clip(I['closed'] * 1.2, 0, 1))
    rgb = _mix(rgb, lin(col['nostril']), 0.9 * I['nostril'])
    rgb = _mix(rgb, lin(col['mouth']), 0.8 * np.clip(I['mcorner'], 0, 1))
    # gloss: the scales glossy (a clear coat on their raised middles), the grooves matte, the belly satin, the face soft
    rough = 0.56 - 0.05 * lift + 0.18 * groove
    rough = rough * (1 - pale) + (0.4 + 0.12 * np.clip(I['scute_edge'], 0, 1)) * pale
    rough = rough + 0.1 * I['snout'] + 0.25 * np.clip(I['mouth'] * 1.4, 0, 1) + 0.2 * I['nostril']
    coat = (0.1 + 0.05 * lift) * (1 - groove) * (1 - pale) + 0.08 * pale
    coat = coat * (1 - 0.6 * I['snout']) * (1 - np.clip(I['mouth'] * 1.4, 0, 1))
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


# ============================================================================= the props
def prop_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal)
    n = len(I['fpart'])
    rgb = np.zeros((n, 3))
    rough = np.tile(np.array([1.0, 0.4, 0.2]), (n, 1))
    # the crest: deep amber at the downy base, gold along the vanes, lit toward each vane's middle and the tips' tops,
    # a pale shaft, the barbs' ridges a touch lighter
    cr = I['fpart'] > 0.5
    if cr.any():
        fu, fv, fb = I['fu'][cr], np.abs(I['fv'][cr]), I['fbarb'][cr]
        var = (np.mod(I['fid'][cr] * 0.618, 1.0) - 0.5)
        g = np.tile(lin(C.mix_hex(col['gold'], '#F2901C', 0.3) if pal['accent'].upper() == '#E8C14E' else col['gold']), (int(cr.sum()), 1)) * (1.0 + 0.08 * var)[:, None]
        g = _mix(g, lin(col['gold_deep']), 0.75 * smooth(0.32, 0.0, fu) + 0.4 * smooth(0.55, 1.0, fv))
        g = _mix(g, lin(col['gold_hi']), 0.3 * smooth(0.15, 0.55, fu) * smooth(0.95, 0.3, fv) * smooth(1.0, 0.75, fu))
        g = _mix(g, lin(col['shaft']), 0.7 * smooth(0.1, 0.03, fv) * smooth(0.05, 0.2, fu))
        rgb[cr] = g
        rough[cr] = np.stack([np.ones(int(cr.sum())), 0.62 + 0.08 * fv, np.full(int(cr.sum()), 0.03)], axis=1)
    tg = I['tpart'] > 0.5
    if tg.any():
        u, v = I['tg_u'][tg], I['tg_v'][tg]
        t = np.tile(lin(col['tongue']), (int(tg.sum()), 1))
        t = _mix(t, lin(col['tongue_dark']), 0.5 * smooth(0.3, 0.0, u) + 0.25 * np.exp(-(v / 0.25) ** 2) * (1 - smooth(0.5, 0.65, u)))
        rgb[tg] = t
        rough[tg] = np.stack([np.ones(int(tg.sum())), np.full(int(tg.sum()), 0.24), np.full(int(tg.sum()), 0.8)], axis=1)
    fg = I['fang'] > 0.5
    if fg.any():
        u = I['fang_u'][fg]
        f = _mix(np.tile(lin(col['fang']), (int(fg.sum()), 1)), lin(col['fang_root']), smooth(0.3, 0.0, u))
        rgb[fg] = f
        rough[fg] = np.stack([np.ones(int(fg.sum())), np.full(int(fg.sum()), 0.34), np.full(int(fg.sum()), 0.3)], axis=1)
    bag = I['bag'] > 0.5
    if bag.any():
        d, fl = I['bag_d'][bag], I['bag_floor'][bag]
        bc = _mix(np.tile(lin(col['bag_rim']), (int(bag.sum()), 1)), lin(col['bag_deep']), smooth(0.25, 0.75, d))
        # the band right behind the lips the mouth line's dark (a simplified Lite lip shows it, never pink)
        bc = _mix(bc, lin(col['bag_lip']), smooth(0.12, 0.03, d))
        bc = _mix(bc, lin(col['bag_bed']), 0.6 * fl)
        rgb[bag] = bc
        rough[bag] = np.stack([np.ones(int(bag.sum())), np.full(int(bag.sum()), 0.66), np.full(int(bag.sum()), 0.05)], axis=1)
    return np.clip(rgb, 0, 1), rough


PROP_ATTRS = ('fpart', 'fu', 'fv', 'fbarb', 'fid', 'tpart', 'tg_u', 'tg_v', 'fang', 'fang_u', 'bag', 'bag_d', 'bag_floor')


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import coilfang_ultra as R
    vid, vpal = next(iter(R.VARIANTS.items()))
    vattr = U.variant_attr(vid, R.ID)
    for ob in body_srcs:
        I = {k: _get(ob, k, 2.0 if k in ('scale_rho', 'hrho') else 0.0) for k in SKIN_ATTRS}
        rgb, rough = skin_paint(I, R.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.set_colour_attr(ob, vattr, skin_paint(I, vpal)[0])
    for ob in props:
        I = {k: _get(ob, k) for k in PROP_ATTRS}
        rgb, rough = prop_paint(I, R.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.set_colour_attr(ob, vattr, prop_paint(I, vpal)[0])


# ============================================================================= per pixel
def body_material(name: str, attr: str, pal: dict, marks):
    """The skin's colour pass: its paint plus the mouth's one clean dark line, per pixel from the height above the line
    (linear, so it interpolates exactly)."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    col = colours(pal)
    md = nb.math('ABSOLUTE', nb.attribute('mdz').outputs['Fac'])
    ln = nb.math('MULTIPLY', nb.smooth(md, 0.0034, 0.0012), nb.smooth(nb.attribute('mspan').outputs['Fac'], 0.05, 0.6))
    c = nb.mix(nb.math('MULTIPLY', ln, 0.92), c, nb.rgb(C.lin(col['mouth'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks):
    """The props' colour pass: their paint, and on the crest fine barb lines per pixel (a feather's vane is ruled by
    its barbs: 4-details panel 5) from the barb count `fbl`."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    col = colours(pal)
    part = nb.attribute('fpart').outputs['Fac']
    bl = nb.attribute('fbl').outputs['Fac']
    fv = nb.math('ABSOLUTE', nb.attribute('fv').outputs['Fac'])
    wave = nb.math('ADD', nb.math('MULTIPLY', nb.math('COSINE', nb.math('MULTIPLY', bl, 6.2831853)), 0.5), 0.5)
    vane = nb.math('MULTIPLY', nb.smooth(fv, 0.06, 0.14), part)
    line = nb.math('MULTIPLY', nb.smooth(wave, 0.55, 0.9), vane)
    c = nb.mix(nb.math('MULTIPLY', line, 0.38), c, nb.rgb(C.lin(col['gold_deep'])))
    lit = nb.math('MULTIPLY', nb.smooth(wave, 0.35, 0.05), vane)
    c = nb.mix(nb.math('MULTIPLY', lit, 0.22), c, nb.rgb(C.lin(col['gold_hi'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= the eyes
IRIS_R, PUPIL_R = 0.75, 0.5


def eye_material(name: str, rough_pass: bool, pal: dict):
    """Big clever eyes (3-faces neutral, 4-details panel 2): white round a large deep-green iris (CONTENT's eye colour,
    a brighter green ring toward its rim, fine radial fibres, a thin dark rim), a big round pupil, a thick dark upper
    lash line on the lens's top, and two catchlights (a big one up toward the key light, a small one low)."""
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
    # the iris a little toward the nose and down: the eyes look ahead and the white shows on the outer side
    ix = nb.math('ADD', x, nb.math('MULTIPLY', side, 0.1))
    iy = nb.math('ADD', y, 0.03)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), IRIS_R)
    pr = PUPIL_R / IRIS_R
    iris = nb.ramp(ri, [(0.0, C.lin(col['pupil'])), (pr * 0.97, C.lin(col['pupil'])), (pr + 0.04, C.lin(col['iris_deep'])),
                        (pr + 0.2, C.lin(col['eye'])), (0.74, C.lin(C.mix_hex(col['eye'], col['iris_ring'], 0.6))),
                        (0.88, C.lin(col['iris_ring'])), (0.95, C.lin(col['iris_deep'])), (1.0, C.lin('#0E1A12')),
                        (1.05, C.lin(col['sclera'])), (1.8, C.lin(col['sclera']))])
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 38.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', nb.smooth(ri, pr + 0.05, 0.6), nb.smooth(ri, 0.97, 0.85)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.22), iris, nb.rgb(C.lin(col['iris_ring'])))
    rr = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(rr, 0.72, 0.98), nb.smooth(ri, 1.02, 1.12)), 0.3), iris,
               nb.rgb(C.lin('#B8BFB8')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, nb.math('MULTIPLY', side, 0.22)), nb.math('DIVIDE', nb.math('SUBTRACT', iy, 0.27), 1.1), 0.0)), 0.17, 0.13)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, nb.math('MULTIPLY', side, 0.2)), nb.math('ADD', iy, 0.24), 0.0)), 0.075, 0.05)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', x, side), 0.2, 0.95), 0.16)
    lash = nb.smooth(nb.math('ADD', y, outer), 0.6, 0.69)
    c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= the shape preview
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import coilfang_carve as CV
    from monsters.breeds import coilfang_ultra as R
    L = CV._LAST
    if L and L.get('n') == len(co):
        I = {k: np.asarray(L.get(k, np.full(len(co), 2.0 if k in ('scale_rho', 'hrho') else 0.0)), np.float64) for k in SKIN_ATTRS}
        I['mouth'] = np.zeros(len(co)) if 'mouth' not in L else L['mouth']
        return skin_paint(I, R.PALETTE)[0]
    from monsters.breeds import coilfang_scales as SC
    z = SC.zones(co)
    return np.where(z['belly'][:, None], lin(R.PALETTE['belly'])[None], lin(R.PALETTE['body'])[None])


def preview_prop_colour(name: str):
    from monsters.breeds import coilfang_ultra as R
    col = colours(R.PALETTE)
    return {'crest': col['gold'], 'tongue': col['tongue'], 'fangs': col['fang'], 'mouthbag': col['bag_deep']}.get(name, col['gold'])
