"""Nibblegrub's paint (Art 2.1 Ultra): the colours, roughness and coat per point of the high source, and the eyes.

CONTENT's palette: body #F2D27A, belly #FFF0C2, segment lines #D9A94F, cheeks #F29C8F, eyes #3B2F2F.
Derived (the pictures show them, the palette has no hex; each made from palette colours):
  - the antenna balls and the toe beans: a peach between the cheeks' pink and the cream, pinker at the balls' tips
    (1-hero, 4-details panel 3);
  - the brows, the lash lines and the mouth's lip line: the eye's dark brown warmed a little toward the segment gold;
  - the mouth's inside: the eye's brown warmed with the cheek pink; the tongue: the cheek pink deepened; the two little
    teeth: the cream lightened (1-hero, 4-details panel 5);
  - the iris: the eye's brown lifted toward the segment gold (4-details panel 2: a warm brown iris round a near-black
    pupil);
  - the body's light and shade painted in (the film keeps yellows matte): a paler yellow on top, a warm gold
    underneath; the cream's shade a warm peach-cream, never grey.
Syrup Nibblegrub (secrets.ts, variants.ts): body #D9892E, belly #FFE2A8, segment lines #8C4A12, eyes #3B2F2F; the
cheeks, the antenna balls, the toe beans, the brows and the mouth keep their usual colours (variant-syrup-nibblegrub.png);
glossy (its own roughness and coat, VARIANT_ORM, and stronger painted highlights).
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from monsters.breeds import nibblegrub_form as F
from monsters.breeds.nibblegrub_form import smooth

CHEEK = '#F29C8F'
LASH_V = -0.12                  # the closed lid's line, in lens radii below the eye's centre
BAND_W = 0.02                  # a band's half width in its crease


def colours(pal: dict, base: dict | None = None) -> dict:
    """Every derived colour (hex) for a palette; `base` (the breed's own) keeps the parts a variant doesn't change."""
    b = base or pal
    body, belly, acc, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    cheek = b.get('cheek', CHEEK)
    return {
        'body': body, 'belly': belly, 'band': acc, 'eye': eye, 'cheek': cheek,
        'hi': C.mix_hex(body, '#FFF8E2', 0.42),
        'deep': C.mix_hex(body, acc, 0.42),
        'warm_cream': C.mix_hex(belly, acc, 0.2),
        'band_deep': C.shade_hex(acc, 0.8),
        'cheek_hi': C.mix_hex(cheek, '#FFF6F0', 0.5),
        'cheek_lo': C.shade_hex(C.mix_hex(cheek, '#E07A6E', 0.4), 0.94),
        'peach': C.mix_hex(cheek, b['belly'], 0.5),
        'peach_tip': C.mix_hex(cheek, b['belly'], 0.18),
        'brow': C.mix_hex(b['eye'], b['accent'], 0.18),
        'mouth': C.mix_hex(b['eye'], cheek, 0.12),
        'inside': C.shade_hex(C.mix_hex(b['eye'], cheek, 0.35), 0.9),
        'tongue': C.shade_hex(cheek, 0.82),
        'tooth': C.mix_hex(b['belly'], '#FFFFFF', 0.6),
        'lash': C.shade_hex(b['eye'], 0.6),
        'iris': C.mix_hex(b['eye'], b['accent'], 0.42),
        'muzzle': C.mix_hex(body, '#FFF8E2', 0.18),
    }


def L(h: str) -> np.ndarray:
    return S.v3(C.lin_rgb(h))


def mix(rgb: np.ndarray, k, h) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    return rgb * (1.0 - k[:, None]) + L(h)[None] * k[:, None]


# ----------------------------------------------------------------------------- the velvet nap (relief and paint)
# round 2: finer (3.2-5 mm, was 4-9) and directional: on the trunk the fibres lie round each segment (the waves run
# along the body), on the head they lie every way; a stipple of round bumps read as stucco
_RNG = np.random.default_rng(2712)


def _waves(n: int, lo: float, hi: float, along: bool):
    d = _RNG.normal(size=(n, 3))
    if along:
        d[:, 1] = np.sign(d[:, 1] + 1e-9) * (1.1 + np.abs(d[:, 1]))     # mostly along Y (polish: less striped)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    return d, 2 * np.pi / _RNG.uniform(lo, hi, n), _RNG.uniform(0, 2 * np.pi, n)


_NAP_T = _waves(12, 0.0032, 0.005, True)
_NAP_H = _waves(12, 0.0032, 0.005, False)
_WARP = _waves(5, 0.03, 0.06, False)


def _sum(co: np.ndarray, spec) -> np.ndarray:
    d, f, p = spec
    v = np.zeros(len(co))
    for dd, ff, pp in zip(d, f, p):
        v += np.sin((co @ dd) * ff + pp)
    return v / np.sqrt(len(f) / 2.0)


def fuzz(co: np.ndarray) -> np.ndarray:
    """The nap (−1..1, about 0.3 rms): fine fibres round the segments, every way on the head, gently warped."""
    w = 0.002 * _sum(co, _WARP)
    q = co + w[:, None]
    head = F.head_zone(co)
    v = (1.0 - head) * _sum(q, _NAP_T) + head * _sum(q, _NAP_H)
    return 0.3 * v


# ----------------------------------------------------------------------------- masks
def masks(co: np.ndarray, vn: np.ndarray) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    fz = fuzz(co)
    # round 3: the cream fades softly up the flanks (2-turnaround)
    border = F.belly_border(co)
    belly = smooth(border + 0.04, border - 0.03, z)
    ds, db = F.antenna_dist(co)
    ball = smooth(F.BALL_R + 0.012, F.BALL_R - 0.004, db)
    toe = smooth(F.TOE_R + 0.005, F.TOE_R + 0.001, F.toe_dist(co))
    legd = F.leg_dist(co)
    # round 3: the legs yellow right up into the body (the cream capped their tops)
    legs = smooth(F.LEG_R[0] + 0.016, F.LEG_R[0] + 0.004, legd) * smooth(0.17, 0.14, z) * (np.abs(x) > 0.12)
    q = F.cheek_q(co)
    cheek = smooth(1.12, 1.0, q) * (z > 0.22)
    blush = smooth(1.75, 1.05, q) * (z > 0.22)
    # the bands: round 3: crisp #D9A94F painted in each pinch (not left to the crease's shade), clean edges (the
    # jittered edge read as a ragged stipple on Syrup), over the top and down to the cream, fading only into the cream
    band = np.zeros(len(co))
    core = np.zeros(len(co))
    for yb in F.BAND_Y:
        d = np.abs(y - yb)
        band = np.maximum(band, smooth(BAND_W + 0.002, BAND_W - 0.002, d))
        core = np.maximum(core, smooth(0.006, 0.0, d))
    head = F.head_zone(co)
    band = band * (1.0 - smooth(0.3, 0.85, belly)) * (1.0 - head) * (1.0 - legs)
    muzzle = smooth(1.5, 1.0, F.ell_q(co, F.MUZZLE)) * (y < -0.44)
    lips = smooth(1.5, 1.0, np.minimum(F.ell_q(co, (F._m(F.LIP[0], 1), F.LIP[1])), F.ell_q(co, (F._m(F.LIP[0], -1), F.LIP[1]))))
    chin = smooth(-0.38, -0.44, y) * smooth(0.13, 0.07, np.abs(x)) * smooth(F.MOUTH[2] - 0.012, F.MOUTH[2] - 0.028, z)
    return {'belly': belly, 'ball': ball, 'toe': toe, 'legs': legs, 'cheek': cheek, 'blush': blush, 'band': band,
            'core': core * band, 'head': head, 'muzzle': muzzle, 'lips': lips * (y < -0.44), 'chin': chin, 'fuzz': fz,
            'ds': ds, 'db': db}


def face_paint(co: np.ndarray, rgb: np.ndarray, cs: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The brows, the lids (an upper lash along each lid's rim; the shut lid's lash line across the flat skin under each
    lens, shown when it blinks shut) and the mouth (its inside, the tongue, two little teeth, the lip line)."""
    lid = np.zeros(len(co))
    marks = np.zeros(len(co))
    for s in (1, -1):
        e = F.eye_local(co, s)
        u, v, w = e[:, 0], e[:, 1], e[:, 2]
        near = (w > -1.2) & (w < 0.9)
        out = u * s
        rho = np.hypot(u, v)
        lidk = smooth(1.05, 0.9, rho) * near
        lid = np.maximum(lid, lidk)
        # the shut lid's lash line: a curve bowing down, thicker toward the outer corner, a small flick out there
        v_arc = LASH_V - 0.2 * (1.0 - (u / 0.85) ** 2)
        thick = 0.06 + 0.03 * smooth(-0.2, 0.75, out)
        line = smooth(thick + 0.035, thick, np.abs(v - v_arc)) * smooth(0.9, 0.78, np.abs(u)) * near
        flick = smooth(0.07, 0.035, np.abs(v - (v_arc + 0.4 * (out - 0.62)))) * smooth(0.6, 0.72, out) * smooth(0.98, 0.86, out) * near
        # (polish) the open eye's upper lash is drawn on the lens (it sinks with it in a blink): none on the skin
        m = np.maximum(line, flick)
        rgb = mix(rgb, m, cs['lash'])
        marks = np.maximum(marks, m)
        # the brow: a short soft arc above the eye (2-turnaround front), thickest in its middle
        v_b = 1.72 + 0.22 * (1.0 - (u / 1.1) ** 2) + 0.06 * out
        th = 0.13 * (1.0 - 0.55 * (u / 1.15) ** 2)
        brow = smooth(th + 0.05, th, np.abs(v - v_b)) * smooth(1.18, 0.98, np.abs(u - 0.04 * s)) * (w > -2.2) * (w < 1.0)
        rgb = mix(rgb, 0.92 * brow, cs['brow'])
        marks = np.maximum(marks, brow)
    # the mouth: the opening's inside (dark, a pink tongue low in it, two little teeth under the lip's cleft), and a
    # thin lip line round it
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    ins = F.mouth_inside(co)
    deep = smooth(0.0, 0.25, ins)
    top, bot = F.mouth_edges(x)
    rgb = mix(rgb, deep, cs['inside'])
    tongue = deep * smooth(0.6, 0.15, (z - bot) / np.maximum(top - bot, 1e-4)) * smooth(0.028, 0.016, np.abs(x))
    rgb = mix(rgb, 0.9 * tongue, cs['tongue'])
    teeth = (smooth(0.0045, 0.0035, np.abs(np.abs(x) - 0.0065)) * smooth(top - 0.0075, top - 0.005, z)
             * smooth(top + 0.002, top - 0.0005, z) * smooth(F.MOUTH[1] + 0.03, F.MOUTH[1] + 0.012, y))
    rgb = mix(rgb, teeth, cs['tooth'])
    rim = F.mouth_inside(co + np.array([0.0, 0.0, 0.0])[None])
    edge = smooth(0.0, 0.08, rim) * smooth(0.3, 0.12, rim) * (y < F.MOUTH[1] + 0.012)
    rgb = mix(rgb, 0.7 * edge, cs['mouth'])
    marks = np.maximum.reduce([marks, deep, edge])
    return rgb, lid, marks, teeth, tongue


def body_colours(co: np.ndarray, vn: np.ndarray, pal: dict, base: dict | None = None, gloss: float = 0.0):
    """(linear rgb, roughness, coat) per point. `gloss` (0..1): the Syrup variant's glossy amber."""
    cs = colours(pal, base)
    mk = masks(co, vn)
    n = len(co)
    nz = vn[:, 2]
    fz = mk['fuzz']
    rgb = np.tile(L(cs['body']), (n, 1))
    # the body's own light: paler on top, warm gold underneath (painted: the film keeps yellows matte)
    rgb = mix(rgb, (0.24 + 0.3 * gloss) * smooth(0.15, 0.95, nz), cs['hi'])
    rgb = mix(rgb, 0.3 * smooth(-0.05, -0.85, nz), cs['deep'])
    # the cream underneath, its shade warm
    cream = np.tile(L(cs['belly']), (n, 1))
    cream = mix(cream, 0.3 * smooth(0.0, -0.9, nz), cs['warm_cream'])
    rgb = rgb * (1.0 - mk['belly'][:, None]) + cream * mk['belly'][:, None]
    # the bands in the creases (a little darker in the very bottom of the crease)
    rgb = mix(rgb, mk['band'], cs['band'])
    rgb = mix(rgb, 0.2 * mk['core'], cs['band_deep'])
    # the legs stay yellow below the cream line (4-details panel 3), the muzzle and the lip a touch paler
    leg_rgb = mix(np.tile(L(cs['body']), (n, 1)), 0.25, cs['hi'])
    rgb = rgb * (1.0 - mk['legs'][:, None]) + leg_rgb * mk['legs'][:, None]
    rgb = mix(rgb, 0.6 * np.maximum(mk['muzzle'], mk['lips']), cs['muzzle'])
    rgb = mix(rgb, 0.45 * mk['chin'], cs['belly'])
    # the nap: a fine light/dark sheen in the fibres
    rgb = rgb * (1.0 + 0.035 * fz)[:, None]
    # the cheeks: shiny pink balls, a highlight on the upper front, a deeper rose underneath, and a soft blush round
    # them fading into the velvet (round 1: a hard pink ring)
    rgb = mix(rgb, 0.45 * mk['blush'], cs['cheek'])
    ck = mk['cheek']
    crgb = np.tile(L(cs['cheek']), (n, 1))
    for s in (1, -1):
        c = F.v3(F._m(F.CHEEK[0], s))
        d = co - c[None]
        nd = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
        spot = F.unit((0.35 * s, -0.62, 0.7))
        hl = smooth(0.72, 0.96, nd @ spot) * (np.sign(co[:, 0]) == s)
        crgb = mix(crgb, 0.7 * hl, cs['cheek_hi'])
        crgb = mix(crgb, 0.4 * smooth(-0.1, -0.8, nd[:, 2]) * (np.sign(co[:, 0]) == s), cs['cheek_lo'])
    rgb = rgb * (1.0 - ck[:, None]) + crgb * ck[:, None]
    # a few crumbs on the cheeks by the mouth (1-hero): tiny gold specks
    crumbs = np.zeros(n)
    for cx, cz_, cr in ((0.075, 0.355, 0.006), (0.095, 0.372, 0.0045), (0.088, 0.334, 0.005), (-0.08, 0.36, 0.0055),
                        (-0.098, 0.342, 0.0045), (-0.07, 0.33, 0.004)):
        dd = np.hypot(co[:, 0] - cx, co[:, 2] - cz_) * (co[:, 1] < -0.4)
        crumbs = np.maximum(crumbs, smooth(cr, cr * 0.5, dd) * (co[:, 1] < -0.4))
    rgb = mix(rgb, 0.9 * crumbs, cs['band'])
    # the antenna balls: peach fuzz, pinker toward the tip (along the stalk), a soft highlight
    bl = mk['ball']
    tipk = np.zeros(n)
    for s in (1, -1):
        a = F.antenna_points(s)
        ax = F.unit(np.array(a[2]) - np.array(a[1]))
        tipk = np.maximum(tipk, smooth(-0.6, 0.6, ((co - np.array(a[2])[None]) @ ax) / F.BALL_R) * (np.sign(co[:, 0]) == s))
    brgb = mix(np.tile(L(cs['peach']), (n, 1)), 0.9 * tipk, cs['peach_tip'])
    brgb = mix(brgb, 0.25 * smooth(0.2, 0.9, nz), cs['cheek_hi'])
    rgb = rgb * (1.0 - bl[:, None]) + brgb * bl[:, None]
    # the toe beans: peach, glossy
    tk = mk['toe']
    trgb = mix(np.tile(L(cs['peach']), (n, 1)), 0.35 * smooth(0.2, 0.9, nz), cs['peach_tip'])
    rgb = rgb * (1.0 - tk[:, None]) + trgb * tk[:, None]
    rgb, lid, marks, teeth, tongue = face_paint(co, rgb, cs)
    # roughness and coat: velvet, the cheeks and beans glossy, the mouth wet, the marks satin; Syrup glossy all over
    rough = np.full(n, 0.8 - 0.42 * gloss)
    rough = np.where(mk['belly'] > 0.5, 0.84 - 0.32 * gloss, rough)
    coat = np.full(n, 0.42 * gloss)
    rough = rough * (1.0 - ck) + 0.3 * ck
    coat = np.maximum(coat, 0.5 * ck)
    rough = rough * (1.0 - crumbs) + 0.8 * crumbs
    rough = rough * (1.0 - tk) + 0.4 * tk
    coat = np.maximum(coat, 0.3 * tk)
    rough = np.where(bl > 0.5, 0.72 - 0.2 * gloss, rough)
    rough = np.where(marks > 0.5, 0.62, rough)
    wet = np.maximum(tongue, teeth)
    rough = rough * (1.0 - wet) + 0.4 * wet
    coat = np.maximum(coat, 0.3 * wet)
    return rgb, rough, coat


def _put(ob, rgb, rough, coat, attr='paint', rattr='rough') -> None:
    S.set_colour_attr(ob, attr, rgb)
    S.set_colour_attr(ob, rattr, np.stack([np.ones(len(rgb)), rough, coat], axis=1))


def paint_sources(body_srcs, fins, props, palette: dict, variants: dict, breed_id: str) -> None:
    from lib import ultra as U
    for ob in body_srcs:
        co, vn = S.mesh_arrays(ob)
        rgb, rough, coat = body_colours(co, vn, palette)
        _put(ob, rgb, rough, coat)
        for vid, vp in variants.items():
            short = U.variant_short(vid, breed_id)
            rgb_v, rough_v, coat_v = body_colours(co, vn, vp, base=palette, gloss=1.0 if short == 'syrup' else 0.0)
            S.set_colour_attr(ob, U.variant_attr(vid, breed_id), rgb_v)
            S.set_colour_attr(ob, f'rough_{short}', np.stack([np.ones(len(co)), rough_v, coat_v], axis=1))


def preview_colours(co: np.ndarray, vn: np.ndarray, palette: dict) -> np.ndarray:
    return body_colours(co, vn, palette)[0]


# ----------------------------------------------------------------------------- the eyes
def eye_material(name: str, rough_pass: bool, pal: dict):
    """A big glossy eye (4-details panel 2, 2-turnaround front): a warm brown iris with a dark rim round a large
    near-black pupil, set a little in and up so a white crescent shows at the outer bottom, two catchlights from the
    upper left (the same side on both eyes). Round 2: the lid ring covers the lens's edge (about 12% of its radius), so
    the iris is drawn for the opening that shows; less gloss (a chrome streak showed in profile)."""
    from lib.nodes import new_mat
    cs = colours(pal)
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.12, 0.6))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    ix = nb.math('ADD', x, nb.math('MULTIPLY', side, 0.07))
    iy = nb.math('SUBTRACT', y, 0.05)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), 0.88)
    eye = cs['eye']
    pupil = C.lin('#120c0b')
    deep = C.lin(C.shade_hex(eye, 0.85))
    mid = C.lin(cs['iris'])
    pale = C.lin(C.mix_hex(cs['iris'], '#F2C98A', 0.35))
    rim = C.lin(C.shade_hex(eye, 0.6))
    sclera = C.lin('#FBF5EA')
    iris = nb.ramp(ri, [(0.0, pupil), (0.54, pupil), (0.6, deep), (0.7, mid), (0.83, pale), (0.92, mid), (0.97, rim),
                        (1.0, rim), (1.03, sclera), (1.5, sclera)])
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 36.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', nb.smooth(ri, 0.55, 0.66), nb.smooth(ri, 0.95, 0.85)))
    c = nb.mix(nb.math('MULTIPLY', fib, 0.18), iris, nb.rgb(C.lin(C.shade_hex(cs['iris'], 0.7))))
    low = nb.math('MULTIPLY', nb.smooth(iy, -0.1, -0.6), nb.math('MULTIPLY', nb.smooth(ri, 0.95, 0.75), nb.smooth(ri, 0.5, 0.62)))
    c = nb.mix(nb.math('MULTIPLY', low, 0.4), c, nb.rgb(pale))
    # the sclera's soft shade under the lid
    sh = nb.math('MULTIPLY', nb.smooth(ri, 0.98, 1.06), nb.smooth(y, 0.3, 0.8))
    c = nb.mix(nb.math('MULTIPLY', sh, 0.35), c, nb.rgb(C.lin('#D9CFC2')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', x, 0.24), nb.math('DIVIDE', nb.math('SUBTRACT', y, 0.26), 1.1), 0.0)), 0.19, 0.155)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', x, 0.22), nb.math('ADD', y, 0.24), 0.0)), 0.08, 0.06)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    # a dark rim under the lid's edge (where the skin meets the lens)
    # (polish) the upper lash along the lens's top edge, thicker toward the outer corner, and a fine dark rim round it
    out = nb.math('MULTIPLY', x, side)
    ey = nb.math('ADD', y, nb.math('MULTIPLY', nb.math('MULTIPLY', x, x), 0.12))
    top = nb.math('SUBTRACT', 0.8, nb.math('MULTIPLY', nb.smooth(out, -0.2, 0.8), 0.12))
    lash = nb.smooth(nb.math('SUBTRACT', ey, top), -0.03, 0.02)
    rim = nb.smooth(nb.vmath('LENGTH', nb.comb(x, y, 0.0)), 0.93, 0.99)
    c = nb.mix(nb.math('MAXIMUM', lash, nb.math('MULTIPLY', rim, 0.8)), c, nb.rgb(C.lin(cs['lash'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
