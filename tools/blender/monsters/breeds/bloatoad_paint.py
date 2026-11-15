"""Bloatoad's paint (Art 2.1 Ultra): per-vertex colour and roughness for the skin (hi_body) and the tongue, the Party
variant's confetti, the per-pixel snout freckles, and the shape preview's colours. The eyes: bloatoad_eyes.py.

Colours come from CONTENT (#7C9A3E skin, #F6C49B belly and throat, #5E7A2E warts, #E9C46A eyes) and variants.ts
(Party: #8FB84A, #FFD9A6, #FF5C8A, #E9C46A). Derived from them (CONTENT has no hex for these parts; the pictures show
them): the lighter yellow-olive toward the peach and on the snout (the skin into the belly), the wart tops (the skin
lifted toward the belly), the dark nodules' valleys (the warts' green darkened), the tongue's rose (the belly's peach
turned to rose in HSV: hue 352°, saturation 0.48, value 0.88) and the mouth (the warts' green into the tongue,
darkened). Party's confetti: pink is its accent; yellow is the eye gold brightened (saturation × 1.5, value × 1.08);
blue is the pink turned to hue 196° at its own saturation and value.
"""
from __future__ import annotations

import colorsys

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.nodes import new_mat
from monsters.breeds import bloatoad_form as F

smooth = F.smooth
PARTY = 'party'


def lin(h: str) -> np.ndarray:
    return np.asarray(C.lin_rgb(h), np.float64)


def hsv_hex(h: str, hue: float | None = None, sat_k: float = 1.0, val_k: float = 1.0, sat: float | None = None,
            val: float | None = None) -> str:
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    hh = hh if hue is None else hue / 360.0
    ss = min(1.0, (ss if sat is None else sat) * sat_k)
    vv = min(1.0, (vv if val is None else val) * val_k)
    r, g, b = colorsys.hsv_to_rgb(hh, ss, vv)
    return '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in (r, g, b))


def colours(pal: dict, party: bool = False) -> dict:
    body, belly, acc, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    base_belly = '#F6C49B'
    tongue = hsv_hex(base_belly, hue=352.0, sat=0.48, val=0.88)
    c = {
        'skin': body, 'skin_top': C.shade_hex(body, 0.9), 'skin_low': C.mix_hex(body, belly, 0.3),
        'wart_top': C.mix_hex(body, belly, 0.1), 'swart': C.mix_hex(body, belly, 0.05),
        'ros': acc, 'ros_top': C.mix_hex(acc, body, 0.3), 'ros_deep': C.shade_hex(acc, 0.72),
        # round 1: the peach a touch lighter (the film look's studio light read it tan: V 0.82 against 0.96)
        # round 2: brighter still (the lit belly read #E2B792, beige): the peach at full value, a touch richer, then lifted
        'belly': C.mix_hex(hsv_hex(belly, sat_k=1.08, val=1.0), '#FFFFFF', 0.12), 'crease': C.shade_hex(C.mix_hex(belly, tongue, 0.25), 0.8), 'border': C.mix_hex(body, belly, 0.55),
        'snout': C.mix_hex(body, belly, 0.38), 'freckle': C.shade_hex('#5E7A2E', 0.62),
        'mouth': C.shade_hex(C.mix_hex('#5E7A2E', tongue, 0.4), 0.3), 'nostril': C.shade_hex('#5E7A2E', 0.35),
        # round 3: a thick olive lower lid (4-details panel 2); olive toe pads, a shade deeper (they read cream)
        'lash': C.shade_hex('#5E7A2E', 0.45), 'lid_hi': C.mix_hex(body, belly, 0.16), 'rim': C.shade_hex(body, 0.86),
        'web': C.mix_hex(belly, tongue, 0.22), 'pad': C.shade_hex(body, 0.86), 'pad_base': C.shade_hex(body, 0.8),
        'lip': C.mix_hex(belly, body, 0.28), 'sac': C.mix_hex(belly, tongue, 0.08),
        'crown': C.shade_hex(body, 0.95), 'tongue': tongue, 'tongue_dark': C.shade_hex(tongue, 0.8),
        'tongue_light': C.mix_hex(tongue, base_belly, 0.35),
        # round 2: the mouth's inside (the slit's walls): a deep rose-brown, the tongue's pink darkened
        'inside': C.shade_hex(tongue, 0.36), 'inside_deep': C.shade_hex(tongue, 0.2),
        # round 3: the mouth bag (the tongue's rose darkened deep inside, lighter by the lips) and its tongue bed
        'bag_rim': C.shade_hex(tongue, 0.86), 'bag_deep': C.shade_hex(tongue, 0.46), 'bag_bed': C.mix_hex(tongue, C.shade_hex(tongue, 0.46), 0.35),
        'drop': C.mix_hex(belly, '#FFFFFF', 0.35), 'sheen': C.mix_hex(belly, '#FFFFFF', 0.62),
    }
    if party:
        c.update({'yellow': hsv_hex(eye, sat_k=1.5, val_k=1.08), 'blue': hsv_hex(acc, hue=196.0),
                  'ros_top': C.mix_hex(acc, '#FFFFFF', 0.22), 'ros_deep': C.shade_hex(acc, 0.8),
                  'freckle': C.shade_hex(body, 0.62)})
    return c


def _mix(rgb: np.ndarray, col: np.ndarray, k) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    return rgb * (1 - k[:, None]) + col[None] * k[:, None]


def _crown_index(co: np.ndarray) -> np.ndarray:
    d = np.stack([np.linalg.norm(co - F.v3(c), axis=1) - r for c, r in F.CROWN], axis=1)
    return np.argmin(d, axis=1)


# ----------------------------------------------------------------------------- the skin
def skin_paint(I: dict, pal: dict, party: bool) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal, party)
    co = I['co']
    n = len(co)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    mott = np.zeros(n) if 'mott' not in I else I['mott']
    # olive: a touch darker over the back, lighter and yellower low on the flanks toward the peach
    rgb = np.tile(lin(col['skin']), (n, 1)) * (0.97 + 0.06 * mott)[:, None]
    rgb = _mix(rgb, lin(col['skin_top']), 0.5 * smooth(0.55, 0.95, z) * smooth(-0.2, 0.1, y))
    peach = np.clip(I['peach'], 0, 1)
    paw = I.get('paw', np.zeros(n))
    rgb = _mix(rgb, lin(col['skin_low']), (0.55 * smooth(0.45, 0.2, z) + 0.6 * smooth(0.02, 0.35, peach)) * (1.0 - paw))
    rgb = _mix(rgb, lin(col['snout']), 0.85 * I['snout'])
    # warts: lighter, yellower tops; the rosettes dark green with lighter nodules and deep valleys between
    rgb = _mix(rgb, lin(col['swart']), 0.7 * I['swart'])
    rgb = _mix(rgb, lin(col['wart_top']), 0.85 * I['wart'] ** 0.7)
    ros = np.clip(I['ros'], 0, 1)
    rc = _mix(np.tile(lin(col['ros']), (n, 1)), lin(col['ros_top']), 0.55 * I['ros_nod'] ** 1.5)
    rc = _mix(rc, lin(col['ros_deep']), 0.5 * (1.0 - smooth(0.0, 0.5, I['ros_nod'] / np.maximum(ros, 1e-3))) * ros)
    rgb = rgb * (1 - ros[:, None]) + rc * ros[:, None]
    if party:
        rgb = _party_spots(rgb, I, col)
    # the crown bumps: the skin, a touch deeper (Party: the little ones pink and yellow, the big one green)
    cr = np.clip(I['crown'], 0, 1)
    if party:
        ci = _crown_index(co)
        cc = np.where((ci == 0)[:, None], lin(col['skin'])[None], np.where((ci % 2 == 1)[:, None], lin(pal['accent'])[None], lin(col['yellow'])[None]))
        rgb = rgb * (1 - cr[:, None]) + cc * cr[:, None]
    else:
        rgb = _mix(rgb, lin(col['crown']), cr)
    # the peach throat and belly, with darker creases, and the feet's salmon webs
    bel = np.tile(lin(col['belly']), (n, 1)) * (0.98 + 0.04 * mott)[:, None]
    bel = _mix(bel, lin(col['crease']), 0.5 * I['crease'])
    border = peach * (1 - peach) * 4.0
    rgb = _mix(rgb, lin(col['border']), 0.35 * border)
    sg = I.get('sacg', np.zeros(n))
    # round 3: the sac a richer peach than the belly (it read pale), its droplets lighter
    bel = _mix(bel, lin(col['sac']), 0.7 * smooth(0.3, 0.8, sg))
    bel = _mix(bel, lin(col['drop']), 0.5 * I.get('drop', np.zeros(n)))
    # polish: one broad soft wet sheen on the sac's upper front, where the key light's highlight sits (none showed in
    # game: the ORM is right, roughness 0.2 and a full coat, but the film keeps texels at roughness 0.3 or more, caps the
    # coat at 0.5 and caps every lit surface's brightness, so on the bright peach the real highlight flattened out)
    sh = smooth(1.0, 0.25, np.linalg.norm((co - F.v3((0.0, -0.6, 0.69))) / F.v3((0.15, 0.11, 0.075)), axis=1))
    bel = _mix(bel, lin(col['sheen']), 0.42 * sh * smooth(0.2, 0.6, sg))
    # the upper lip a peach-tan band over the smile (1-hero)
    uplip = np.clip(I['lip'], 0, 1) * (z > 0.8) * (1.0 - peach)
    rgb = _mix(rgb, lin(col['lip']), 0.6 * uplip)
    rgb = rgb * (1 - peach[:, None]) + bel * peach[:, None]
    rgb = _mix(rgb, lin(col['web']), 0.85 * I['web'])
    # the toe pads and the toes' tops: the skin's olive, glossy (round 2: never cream)
    pad = np.clip(I['pad'], 0, 1)
    rgb = _mix(rgb, lin(col['pad']), np.maximum(pad, paw * (1.0 - I['web']) * 0.8))
    # the face: lips, the mouth's dark line, nostrils; the lids' lash rim, the closed lid's lash, the lower lid
    rgb = _mix(rgb, lin(col['rim']), 0.6 * I['rim'])
    rgb = _mix(rgb, lin(col['lid_hi']), 0.35 * I['lid'] * (1 - I['lash']))
    rgb = _mix(rgb, lin(col['lash']), 0.9 * np.clip(I['lash'] * 1.3, 0, 1))
    rgb = _mix(rgb, lin(col['lash']), 0.85 * np.clip(I['closed'] * 1.2, 0, 1))
    # the mouth's line, and a wider even band of the mouth's dark under it (an opening jaw stretches it: no streaks)
    # round 2: the mouth's slit: its walls the mouth's dark rose inside, deepest at its floor; the smile's line on top;
    # the soft fold round each corner a shade of the skin
    sl = np.clip(I['mband'], 0, 1)
    # polish: no rose band on the lips any more (the mouth's inside is the pocket behind the cut): one clean dark line
    rgb = _mix(rgb, lin(col['mouth']), 0.6 * np.clip(I.get('mcorner', np.zeros(n)), 0, 1))
    rgb = _mix(rgb, lin(C.shade_hex(col['skin'], 0.72)), 0.45 * I.get('mfold', np.zeros(n)))
    rgb = _mix(rgb, lin(col['nostril']), 0.9 * I['nostril'])
    # roughness and coat: wet skin, glossier warts, nodules, pads, crown and the sac; the mouth matte
    # round 2: the sac clearly the wettest (lowest roughness, a full coat, droplets glassy); the belly below matte-ish;
    # the snout and the face below the eyes less glossy (white crescents read as wet plastic there)
    face = np.clip(I['snout'] + 0.8 * I['rim'], 0, 1)
    rough = 0.42 - 0.1 * I['wart'] - 0.06 * I['swart'] - 0.06 * ros - 0.04 * pad - 0.1 * cr + 0.1 * face
    rough = rough * (1 - peach) + (0.52 - 0.32 * sg + 0.06 * I['crease']) * peach
    rough = rough - 0.12 * I.get('drop', np.zeros(n))
    rough = rough + 0.2 * np.clip(I['mouth'] * 1.4 + sl, 0, 1) + 0.15 * I['nostril']
    # round 3: less coat over the head's top and the back (a milky sheen), the sac the glossiest of all
    top = smooth(0.7, 1.0, z) + smooth(0.0, 0.3, y) * smooth(0.5, 0.8, z)
    coat = 0.28 + 0.12 * I['wart'] + 0.08 * ros + 0.05 * pad + 0.06 * cr - 0.2 * face - 0.1 * np.clip(top, 0, 1)
    coat = coat * (1 - peach) + (0.2 + 0.8 * sg) * peach
    coat = np.maximum(coat, I.get('drop', np.zeros(n)))
    coat = coat * (1 - 0.8 * np.clip(I['mouth'] * 1.4 + sl, 0, 1))
    # the mouth's inside fully matte (its stretched walls caught glints in stripes, like teeth)
    inside = smooth(0.3, 0.6, sl)
    rough = rough * (1 - inside) + inside
    coat = coat * (1 - inside)
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


def _party_spots(rgb: np.ndarray, I: dict, col: dict) -> np.ndarray:
    """Confetti (variant picture): the rosettes pink; the big warts yellow, blue or pink; a share of the small ones too.
    Only where the olive skin carries warts (never the peach, the face's front or the feet)."""
    pink, yellow, blue = lin(col['ros']), lin(col['yellow']), lin(col['blue'])
    wid, sid = I['wart_id'], I['swart_id']
    big = np.where((wid < 0.25)[:, None], yellow[None], np.where((wid < 0.42)[:, None], blue[None], pink[None]))
    # round 2: medium confetti (about half a pink spot across): a disc round each big wart, 1.9 times its dome, so the
    # raised glossy dome sits in its middle (the variant picture; they were specks)
    # (round 2 build: discs round every big wart covered the skin; a third of them, spaced, as in the picture)
    wq = I.get('wq', np.full(len(rgb), 9.0))
    # round 3: separate dots on clean green, never on or against a pink patch (they read as a rash)
    clear = smooth(0.12, 0.0, I['ros'])
    # polish: the colour exactly on each chosen raised dome, never a flat ring round it (the 1.8x discs read as spots
    # beside their bumps); no confetti on the small warts (a few vertices across, they painted as hard diamonds)
    dome = np.maximum(np.clip(I['wart'] ** 0.5 * 1.15, 0, 1), smooth(1.1, 0.85, wq) * (I['wart'] > 0.02))
    k = dome * (np.mod(wid * 3.7, 1.0) < 0.6) * (I['peach'] < 0.3) * clear
    return rgb * (1 - k[:, None]) + big * k[:, None]


# ----------------------------------------------------------------------------- the tongue
def tongue_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal)
    u, v, top = I['tg_u'], I['tg_v'], I['tg_top']
    n = len(u)
    rgb = np.tile(lin(col['tongue']), (n, 1))
    rgb = _mix(rgb, lin(col['tongue_dark']), 0.35 * np.exp(-(v / 0.18) ** 2) * top * (1 - smooth(0.7, 0.95, u)))
    rgb = _mix(rgb, lin(col['tongue_light']), 0.4 * (1 - top) + 0.25 * smooth(0.75, 1.0, u))
    rgb = _mix(rgb, lin(col['tongue_dark']), 0.4 * smooth(0.1, 0.0, u))
    # polish: wet and glossy (it read matte: the film keeps every body and prop texel at roughness 0.3 or more, and
    # caps the coat at 0.5): a soft wet sheen down the top on each side of the groove, and the tip's top
    wet = np.exp(-((np.abs(v) - 0.45) / 0.2) ** 2) * top * (0.6 + 0.4 * smooth(0.6, 0.9, u))
    rgb = _mix(rgb, lin(C.mix_hex(col['tongue'], '#FFFFFF', 0.55)), 0.45 * wet)
    rough = 0.2 + 0.06 * (1 - top)
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), rough, np.full(n, 1.0)], axis=1)


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


SKIN_ATTRS = ('mband', 'sacg', 'drop', 'wq', 'mfold', 'paw', 'peach', 'ros', 'ros_nod', 'ros_id', 'ros_rim', 'wart', 'wart_id', 'swart', 'swart_id', 'crease', 'lip',
              'nostril', 'lid', 'lash', 'closed', 'rim', 'socket', 'pad', 'web', 'crown', 'snout', 'sac', 'mouth', 'mcorner')


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import bloatoad_ultra as R
    vid, vpal = next(iter(R.VARIANTS.items()))
    vattr = U.variant_attr(vid, R.ID)
    from monsters.breeds import bloatoad_noise as N
    for ob in body_srcs:
        co = S.attr_array(ob, 'root').astype(np.float64) if 'root' in ob.data.attributes else S.mesh_arrays(ob)[0]
        I = {'co': co, 'mott': N.fbm(co, 1 / 0.12, 61, 3), **{k: _get(ob, k) for k in SKIN_ATTRS}}
        rgb, rough = skin_paint(I, R.PALETTE, False)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        rgb_v, _rv = skin_paint(I, vpal, True)
        S.set_colour_attr(ob, vattr, rgb_v)
    for ob in props:
        I = {k: _get(ob, k) for k in ('tg_u', 'tg_v', 'tg_top', 'bag', 'bag_d', 'bag_floor')}
        rgb, rough = tongue_paint(I, R.PALETTE)
        # round 3: the mouth bag: rose by the lips darkening to the deep inside, the tongue's bed on its floor; matte
        col = colours(R.PALETTE)
        bag = I['bag'] > 0.5
        if bag.any():
            d, fl = I['bag_d'][bag], I['bag_floor'][bag]
            bc = _mix(np.tile(lin(col['bag_rim']), (int(bag.sum()), 1)), lin(col['bag_deep']), smooth(0.0, 0.5, d))
            bc = _mix(bc, lin(col['bag_bed']), 0.7 * fl)
            rgb[bag] = bc
            rough[bag] = np.stack([np.ones(len(d)), np.full(len(d), 0.62), np.full(len(d), 0.08)], axis=1)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.set_colour_attr(ob, vattr, rgb)


# ----------------------------------------------------------------------------- per pixel: the snout's freckles
def body_material(name: str, attr: str, pal: dict, marks):
    """The skin's colour pass: its paint plus fine dark freckles on the snout and round the mouth (2-turnaround front,
    4-details panel 1) and a faint stipple on the peach."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    party = attr != 'paint'
    col = colours(pal, party)
    pos = nb.coords().outputs['Object']
    sn = nb.attribute('snout').outputs['Fac']
    warp = nb.vmath('ADD', pos, nb.vmath('SCALE', nb.comb(nb.noise(pos, 40.0, 1.0, 0.5), nb.noise(nb.vmath('ADD', pos, nb.comb(1.3, 2.1, 0.7)), 40.0, 1.0, 0.5), 0.0), scale=0.002))
    fr = nb.math('MULTIPLY', nb.smooth(nb.voronoi(warp, 160.0, 'F1'), 0.13, 0.07), nb.smooth(sn, 0.25, 0.7))
    c = nb.mix(nb.math('MULTIPLY', fr, 0.75), c, nb.rgb(C.lin(col['freckle'])))
    pe = nb.attribute('peach').outputs['Fac']
    st = nb.math('MULTIPLY', nb.smooth(nb.voronoi(nb.vmath('ADD', warp, nb.comb(2.2, 0.4, 1.7)), 260.0, 'F1'), 0.12, 0.06), nb.smooth(pe, 0.6, 0.95))
    c = nb.mix(nb.math('MULTIPLY', st, 0.22), c, nb.rgb(C.lin(col['crease'])))
    # polish: the mouth's one clean dark line, per pixel from the height above the line (bloatoad_carve 'mdz'), fading
    # out where the smile's span ends
    md = nb.math('ABSOLUTE', nb.attribute('mdz').outputs['Fac'])
    ln = nb.math('MULTIPLY', nb.smooth(md, 0.0034, 0.0011), nb.smooth(nb.attribute('mspan').outputs['Fac'], 0.05, 0.6))
    c = nb.mix(nb.math('MULTIPLY', ln, 0.95), c, nb.rgb(C.lin(col['mouth'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the shape preview
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import bloatoad_carve as CV
    from monsters.breeds import bloatoad_skin as SK
    from monsters.breeds import bloatoad_ultra as R
    L = CV._LAST
    if L and L.get('n') == len(co):
        I = {'co': L['base'], **{k: L[k] for k in SKIN_ATTRS}}
        return skin_paint(I, R.PALETTE, False)[0]
    z = SK.zones(co)
    return np.where(z['belly'][:, None], lin(R.PALETTE['belly'])[None], lin(R.PALETTE['body'])[None])
