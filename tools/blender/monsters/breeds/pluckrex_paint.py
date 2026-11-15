"""Pluckrex's paint: every colour from CONTENT §2.2 #23 (#4F6D8F slate-blue hide, #F1E6CF cream belly and throat,
#F7C548 sunflower-gold crest, #2B2D42 eyes) or derived from them (`colours`). The palette has no grey, pink or red:
the bracers' weathered stone is the navy mixed into the cream; the mouth's inside keeps the shipped Hearthwing mouth's
rose (hearthwing_mouth.MOUTH_COLS), toned toward the navy, as the pictures show a pink tongue no mix of the four can make.
Metres; -Y is the front."""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib.surface import smooth, v3
from monsters.breeds import gloomgrin_stone as K
from monsters.breeds import hearthwing_mouth as MO
from monsters.breeds import pluckrex_props as PR

GOLD_GLOW = '#F7C548'


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def blend(rgb: np.ndarray, kk, hexcol: str) -> np.ndarray:
    kk = np.clip(np.asarray(kk, np.float64), 0.0, 1.0)
    if kk.ndim == 1:
        kk = kk[:, None]
    return rgb * (1.0 - kk) + lin(hexcol)[None] * kk


def warm(h: str, kg: float, kb: float, k: float = 1.0) -> str:
    """A palette colour warmed toward orange: its green and blue scaled down (the gold's own hue, shifted)."""
    r, g, b = C.srgb(h)
    return '#%02x%02x%02x' % (int(min(1.0, r * k) * 255), int(min(1.0, g * kg * k) * 255), int(min(1.0, b * kb * k) * 255))


def colours(pal: dict) -> dict:
    body, belly, gold, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    return {
        'body': body, 'belly': belly, 'accent': gold, 'eye': eye,
        'peb_top': C.mix_hex(body, belly, 0.2),             # a pebble's lighter crown
        'peb_hi': C.mix_hex(body, '#FFFFFF', 0.28),         # its satin rim light (lesson 6), painted in
        'peb_gap': C.shade_hex(body, 0.55),                 # the grooves between pebbles
        'peb_deep': C.mix_hex(C.shade_hex(body, 0.72), eye, 0.18),
        'cream_line': C.mix_hex(belly, body, 0.2),          # the fine outlines of the belly's flat plates
        'cream_lo': C.mix_hex(belly, body, 0.08),
        'cream_hi': C.mix_hex(belly, '#FFFFFF', 0.25),
        'brow': C.mix_hex(eye, body, 0.08),
        'lash': C.shade_hex(eye, 0.8),
        'nostril': C.shade_hex(eye, 0.75),
        'smile': C.mix_hex(eye, body, 0.3),
        'claw': C.mix_hex(eye, body, 0.18),                 # dark charcoal-navy claws, hands and feet alike
        'claw_hi': C.mix_hex(eye, body, 0.4),
        'tooth': C.mix_hex(belly, '#FFFFFF', 0.4),          # matte bone (lesson 4)
        'tooth_root': C.mix_hex(belly, body, 0.12),
        'gold_deep': C.shade_hex(gold, 0.66),               # the petals' grooves and roots, a deeper saturated gold
        'gold_rib': C.mix_hex(gold, '#FFFFFF', 0.3),        # the raised ribs, painted light (lesson 4)
        'gold_edge': C.shade_hex(gold, 0.84),
        'gold_root': warm(gold, 0.7, 0.3, 0.92),             # round 3: deep warm orange at the rib roots
        'gold_tip': C.mix_hex(gold, belly, 0.42),            # bright pale gold at the tips
        'gold_groove': warm(gold, 0.62, 0.25, 0.72),
        'stone': C.mix_hex(eye, belly, 0.5),                # the bracers' weathered grey stone (derived)
        'stone_dark': C.mix_hex(eye, belly, 0.3),
        'stone_hi': C.mix_hex(eye, belly, 0.68),
        'palate': C.mix_hex(MO.MOUTH_COLS['palate'], eye, 0.15),
        'gum': C.mix_hex(MO.MOUTH_COLS['tongue'], MO.MOUTH_COLS['gum'], 0.45),
        'tongue': C.mix_hex(MO.MOUTH_COLS['tongue'], belly, 0.3),     # pinker (the agreed exception to the palette)
        'throat': C.mix_hex(MO.MOUTH_COLS['throat'], eye, 0.3),
        'lip_in': C.mix_hex(belly, MO.MOUTH_COLS['tongue'], 0.25),    # a thin cream lip edge
        # round 3: a warm amber-orange iris (the pictures), the gold warmed toward orange so it never matches the crest
        # polish: warm amber, honey-gold at the rim, brown near the pupil (#935924), from the gold warmed
        'iris': warm(gold, 0.8, 0.62, 0.86),
        'iris_deep': warm(gold, 0.75, 0.83, 0.6),
        'iris_lite': warm(gold, 0.9, 0.75, 0.93),
        'iris_rim': warm(gold, 0.6, 0.5, 0.42),
        'pupil': C.mix_hex(eye, '#000000', 0.25),
        'sclera': C.mix_hex('#FFFFFF', belly, 0.22),
    }


def _hash(pid: np.ndarray, seed: int) -> np.ndarray:
    return K.hash1(np.maximum(pid, 0).astype(np.int64), seed) * (pid >= 0) + 0.5 * (pid < 0)


def body_paint(F, p: np.ndarray, n, z: dict, pal: dict, peb=None, keel=None) -> dict:
    """Per point of the body: 'paint' (linear RGB) and 'rough' (1, roughness, coat). `peb` = (pid, rim, top, plate
    cream, plate back) from the carve; `keel` = (on, ul, rho, rib) for the grown form's ridge scales."""
    col = colours(pal)
    m = len(p)
    cream_v = z['cream']
    cream = cream_v.copy()
    rough = np.full(m, 0.55)
    coat = np.full(m, 0.08)
    rgb = np.tile(lin(col['body']), (m, 1))
    if peb is not None:
        pid, rim, top, pc = peb
        on = pid >= 0
        hsh = _hash(pid, 3)
        # each pebble is wholly blue or wholly cream: across the border band the choice is speckled per pebble
        pcv = np.where(on, pc[np.maximum(pid, 0)], 0.0)
        pick = np.where(on, (pcv + 0.3 * (hsh - 0.5) * smooth(0.05, 0.3, pcv) * smooth(0.98, 0.7, pcv)) > 0.5, False)
        # polish: across the border band the gaps between pebbles stay blue (cream gaps read as white saw-teeth)
        cream = np.where(on, pick.astype(float), np.where((cream_v > 0.1) & (cream_v < 0.9), smooth(0.8, 0.95, cream_v), cream_v))
        # blue pebbles: a satin crown and a light rim toward the key, dark grooves
        b = np.tile(lin(col['body']), (m, 1)) * (0.96 + 0.08 * hsh)[:, None]
        b = blend(b, top * 0.42, col['peb_top'])
        b = blend(b, on * smooth(0.55, 0.9, rim) * smooth(1.0, 0.95, rim) * 0.22, col['peb_hi'])
        b = blend(b, (~on) * 0.75 + on * smooth(0.93, 1.0, rim) * 0.6, col['peb_gap'])
        # cream plates: flat, a fine darker outline, a per-plate tone
        c = np.tile(lin(col['belly']), (m, 1)) * (0.975 + 0.05 * hsh)[:, None]
        c = blend(c, on * smooth(0.86, 0.99, rim) * 0.3 + (~on) * 0.35, col['cream_line'])
        c = blend(c, top * 0.12, col['cream_hi'])
        rgb = b * (1 - cream[:, None]) + c * cream[:, None]
        rough = np.where(on, 0.56 + 0.16 * smooth(0.6, 1.0, rim), 0.72)
        coat = np.where(on, 0.06 * (1 - smooth(0.7, 1.0, rim)), 0.0)
        rough = rough * (1 - cream) + (0.66 + 0.06 * (~on)) * cream
        coat = coat * (1 - cream) + 0.04 * cream
    else:
        rgb = rgb * (1 - cream[:, None]) + lin(col['belly'])[None] * cream[:, None]
    if keel is not None:
        kon, ul, rho, rib = keel
        kc = np.tile(lin(col['body']), (m, 1))
        kc = blend(kc, smooth(-0.6, 0.9, ul) * 0.35, col['peb_top'])
        kc = blend(kc, rib * 0.45, col['peb_hi'])
        kc = blend(kc, smooth(0.8, 0.98, rho) * 0.6, col['peb_gap'])
        rgb = np.where(kon[:, None], kc, rgb)
        rough = np.where(kon, 0.5 + 0.15 * smooth(0.8, 1.0, rho), rough)
        coat = np.where(kon, 0.08, coat)
    # the mouth's inside: a rose palate, a pink tongue on the floor, the throat deep, a darker inner lip
    mi = z['mouth_in']
    if mi.any():
        mc = np.where(z['floor'][:, None], lin(col['gum'])[None], lin(col['palate'])[None])
        mc = blend(mc, z['tongue'], col['tongue'])
        mc = blend(mc, z['throat_in'] * 0.85, col['throat'])
        mc = blend(mc, z['lip_in'] * 0.85, col['lip_in'])
        mw = z['mouth_w']
        rgb = rgb * (1 - mw[:, None]) + mc * mw[:, None]
        rough = rough * (1 - mw) + 0.42 * mw
        coat = coat * (1 - mw) + 0.25 * mw
    # soles and palms: smooth cream pads
    pad = np.maximum(z['sole'], z['palm'])
    rgb = blend(rgb, pad * 0.85, col['cream_lo'])
    rough = rough * (1 - pad) + 0.65 * pad
    return {'paint': np.clip(rgb, 0, 1), 'rough': np.stack([np.ones(m), np.clip(rough, 0.3, 1.0), np.clip(coat, 0, 0.5)], axis=1),
            'cream': cream}


def prop_paint(F, ob, pal: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(paint, rough, glow) per prop vertex."""
    from lib import surface as S
    col = colours(pal)
    gp = np.round(S.attr_array(ob, 'gpart')).astype(int)
    pt = S.attr_array(ob, 'pt').astype(np.float64)
    t, q, f = pt[:, 0], pt[:, 1], pt[:, 2]
    co, _vn = S.mesh_arrays(ob)
    nv = len(gp)
    rgb = np.tile(lin(col['accent']), (nv, 1))
    rough = np.full(nv, 0.45)
    coat = np.full(nv, 0.2)
    glow = np.zeros(nv)
    Gl = F.G.get('glow', {})
    m = gp == PR.P_CREST
    if m.any():
        aq = np.abs(q[m])
        cc = np.tile(lin(col['accent']), (int(m.sum()), 1))
        cc = blend(cc, smooth(0.62, 0.3, t[m]) * 0.85, col['gold_root'])       # round 3: orange roots
        cc = blend(cc, smooth(0.7, 1.0, t[m]) * 0.7, col['gold_tip'])          # pale gold tips
        # round 2: sunflower gold kept bright and smooth (the shading comes from the relief; sharp paint steps blocked up
        # in the KTX2 colour map): soft grooves beside the rib, the rib and the rim bead lighter, a soft sparkle
        cc = blend(cc, smooth(0.12, 0.3, aq) * smooth(0.7, 0.42, aq) * 0.25, col['gold_deep'])
        cc = blend(cc, smooth(0.93, 0.99, aq) * 0.6, col['gold_groove'])        # the groove line between petals
        cc = blend(cc, np.exp(-(aq / 0.14) ** 2) * smooth(0.25, 0.5, t[m]) * 0.45, col['gold_rib'])
        cc = blend(cc, smooth(0.8, 0.93, aq) * 0.35, col['gold_rib'])
        f1, _f2, _fid = K.voronoi(co[m], 0.006 * F.k, 77)
        spark = smooth(0.0011 * F.k, 0.0004 * F.k, f1) * smooth(0.3, 0.6, t[m])
        cc = blend(cc, spark * 0.35, col['gold_rib'])
        rgb[m] = cc
        rough[m] = 0.36 - 0.06 * np.exp(-(aq / 0.13) ** 2)
        coat[m] = 0.32
        # round 3: the glow at the roots and along the rims (an even glow washed the ribs flat), plus the flecks
        glow[m] = Gl.get('crest', 0.6) * (0.25 + 0.75 * smooth(0.8, 0.3, t[m]) * smooth(0.15, 0.32, t[m])
                                          + 0.55 * smooth(0.78, 0.9, aq) * smooth(0.98, 0.92, aq)) + 0.8 * spark
    m = gp == PR.P_SPINE
    if m.any():
        cc = np.tile(lin(col['accent']), (int(m.sum()), 1))
        cc = blend(cc, smooth(0.4, 0.05, t[m]) * 0.6, col['gold_root'])
        cc = blend(cc, smooth(0.55, 0.95, t[m]) * 0.4, col['gold_rib'])
        rgb[m] = cc
        rough[m] = 0.36
        coat[m] = 0.3
        glow[m] = Gl.get('spine', 0.25) * smooth(0.3, 0.75, t[m])
    m = (gp == PR.P_TOOTH_U) | (gp == PR.P_TOOTH_L)
    if m.any():
        cc = np.tile(lin(col['tooth']), (int(m.sum()), 1))
        cc = blend(cc, smooth(0.45, 0.1, t[m]) * 0.5, col['tooth_root'])
        rgb[m] = cc
        rough[m] = 0.62
        coat[m] = 0.0
    m = (gp == PR.P_HCLAW) | (gp == PR.P_FCLAW)
    if m.any():
        cc = np.tile(lin(col['claw']), (int(m.sum()), 1))
        cc = blend(cc, smooth(0.35, 0.95, t[m]) * 0.2, col['claw_hi'])
        rgb[m] = cc
        rough[m] = 0.34
        coat[m] = 0.35
    m = gp == PR.P_BRACER
    if m.any():
        from monsters.breeds import pluckrex_bracers as BR
        c_, r_, k_, g_ = BR.paint(F, pt[m], co[m], col, lin, blend)
        rgb[m], rough[m], coat[m], glow[m] = c_, r_, k_, g_
    return np.clip(rgb, 0, 1), np.stack([np.ones(nv), np.clip(rough, 0.3, 1.0), np.clip(coat, 0, 0.5)], axis=1), np.clip(glow, 0, 1)
