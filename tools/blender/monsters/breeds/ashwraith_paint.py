"""Ashwraith's colours and per-vertex paint (ashwraith_ultra.paint_sources); the per-pixel detail is in ashwraith_shade.

CONTENT §2.2 #14: shroud #A7A3A0, lighter folds #CFCAC6, embers #FF6B3D, eyes #FF6B3D. Colours the palette lacks are
made from it (logged in the recipe's notes):
- the dark inside (the face's void, the core): the shroud darkened to 8.5% with a breath of ember;
- the singed and charred edges: the shroud darkened, a little ember mixed in; the warm light inside: the ember darkened;
- the wisps: the shroud darkened, charcoal at the roots to near black at the tips;
- the cream hands: the lighter folds with a little ember (they keep it on every variant: the variant picture);
- the eyes' hot core: the ember lightened toward a warm white (round 2: the review asked for about #FFB27A);
- Lantern-bearer's iron: its shroud with a little of its folds' colour; its glass and flame: its embers and eyes; its
  shroud painted lighter (the film's toe crushed #2B2F3A to near black) and lit blue round the lantern.
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import ashwraith_body as B
from monsters.breeds import ashwraith_drape as D
from monsters.breeds import ashwraith_form as F
from monsters.breeds import ashwraith_props as PR

BASE = {'body': '#A7A3A0', 'belly': '#CFCAC6', 'accent': '#FF6B3D', 'eye': '#FF6B3D'}
HAND_HEX = C.mix_hex(BASE['belly'], '#F4E8D0', 0.45)     # polish: a soft ivory cream (derived), not a flat white bean
LANTERN_LIGHT = (np.array([0.0, -0.32, 0.34]), 0.27)     # Lantern-bearer: where the flame is, and how far its light reaches
WARM_ASH = (1.025, 1.0, 0.965)       # polish: the base shroud warmed a touch toward ash (it rendered cool and olive)


def _lum(h: str) -> float:
    r, g, b = C.srgb(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def cloth_k(pal: dict) -> float:
    """The cloth's paint under the film's studio light: a touch darker for the pale shroud (it read near white), much
    lighter for a dark one (round 2: Lantern-bearer's #2B2F3A rendered #101015)."""
    return 0.84 if _lum(pal['body']) > 0.35 else 1.7


def _warm(h: str) -> str:
    return '#%02x%02x%02x' % tuple(int(round(255 * min(1.0, c * k))) for c, k in zip(C.srgb(h), WARM_ASH))


def colours(pal: dict) -> dict:
    body, belly, accent, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    warm = C.srgb(eye)[0] > C.srgb(eye)[2]
    if warm:
        body, belly = _warm(body), _warm(belly)
    return {
        'shroud': body, 'light': belly, 'dark': C.shade_hex(body, 0.68), 'lining': C.shade_hex(body, 0.55),
        'void': C.mix_hex(C.shade_hex(body, 0.085), accent, 0.035),
        'void_lift': C.mix_hex(C.shade_hex(body, 0.16), accent, 0.04),
        'singe': C.mix_hex(C.shade_hex(body, 0.4), accent, 0.07),
        'char': C.mix_hex(C.shade_hex(body, 0.2), accent, 0.05),
        'ember': accent, 'ember_hot': C.mix_hex(accent, '#FFFFFF', 0.42), 'ember_deep': C.shade_hex(accent, 0.62),
        'smoke_root': C.mix_hex(C.shade_hex(body, 0.34), accent, 0.04), 'smoke_tip': C.mix_hex(belly, body, 0.15),
        'hand': HAND_HEX, 'hand_crease': C.shade_hex(HAND_HEX, 0.66),
        'eye': eye, 'eye_hot': C.mix_hex(eye, '#FFE9B0' if warm else '#FFFFFF', 0.55), 'eye_deep': C.shade_hex(eye, 0.8),
        'iron': C.mix_hex(C.shade_hex(body, 0.85), belly, 0.15), 'iron_dark': C.shade_hex(body, 0.5),
        'glass': C.mix_hex(accent, C.shade_hex(body, 0.5), 0.5), 'flame': accent, 'flame_core': eye,
    }


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def blend(rgb: np.ndarray, k, hexc: str) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0, 1)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    return rgb * (1 - k[:, None]) + lin(hexc)[None] * k[:, None]


def fold_shade(rgb: np.ndarray, f: np.ndarray, col: dict, k_light: float = 0.72, k_dark: float = 0.65) -> np.ndarray:
    rgb = blend(rgb, np.clip(f, 0, 1) * k_light, col['light'])
    return blend(rgb, np.clip(-f, 0, 1) * k_dark, col['dark'])


def lantern_light(rgb: np.ndarray, p: np.ndarray, pal: dict, col: dict, k: float = 0.55) -> np.ndarray:
    """Lantern-bearer only: the flame's blue light on what is near it."""
    if not pal.get('lantern'):
        return rgb
    c, r = LANTERN_LIGHT
    f = np.clip(1.0 - np.linalg.norm(p - c, axis=1) / r, 0, 1) ** 1.5
    return blend(rgb, f * k, C.mix_hex(col['ember'], '#FFFFFF', 0.2))


def mottle(p: np.ndarray) -> np.ndarray:
    """0.25..1: a soft, smooth patchiness for the warm glow inside (never one flat colour)."""
    q = np.asarray(p, np.float64)
    m = (np.sin(q[:, 0] * 23.0 + 1.3) * np.sin(q[:, 1] * 19.0 + 0.4) + np.sin(q[:, 2] * 31.0 + q[:, 0] * 11.0)) * 0.25 + 0.5
    return 0.25 + 0.75 * np.clip(m, 0, 1) ** 1.5


def ember_spots(p: np.ndarray, density) -> np.ndarray:
    """0..1 small glowing ember specks (about 1-2 cm), more of them and bigger where `density` (0..1) is high."""
    q = np.asarray(p, np.float64)
    n1 = np.sin(q[:, 0] * 71.0 + 0.3) * np.sin(q[:, 1] * 67.0 + 1.1) * np.sin(q[:, 2] * 59.0 + 2.0)
    n2 = np.sin(q[:, 0] * 43.0 + q[:, 2] * 29.0 + 0.7) * np.sin(q[:, 1] * 37.0 - q[:, 2] * 41.0 + 1.9)
    m = 0.6 * n1 + 0.4 * n2
    thr = 0.62 - 0.4 * np.clip(np.asarray(density, np.float64), 0, 1)
    return smooth(thr, thr + 0.16, m) * smooth(0.02, 0.15, np.asarray(density, np.float64))


_HOLES: list = []


def hole_rims(q: np.ndarray) -> np.ndarray:
    """0..1 round each hole cut in the cloth (its singed, charred rim)."""
    if not _HOLES:
        for hu, hv, r in D.CAPE_HOLES:
            _HOLES.append((D.cape_point(np.array([hu]), np.array([hv]))[0], r))
        for hu, hv, r in D.MID_HOLES:
            _HOLES.append((D.mid_point(np.array([hu]), np.array([hv]))[0], r))
        for nm, hs in D.PANEL_HOLES.items():
            for hu, hv, r in hs:
                _HOLES.append((D.panel_point(nm, np.array([hu]), np.array([hv]))[0], r))
    out = np.zeros(len(q))
    for c, r in _HOLES:
        d = np.linalg.norm(q - c, axis=1) / r
        out = np.maximum(out, smooth(2.1, 1.05, d))
    return out


def body_paint(p: np.ndarray, pal: dict) -> dict:
    """Per point of the body: paint, rough (1, roughness, coat), glow, and `inner` (0 cloth .. 1 the dark inside)."""
    col = colours(pal)
    n = len(p)
    z = p[:, 2]
    zz = B.zones(p)
    rgb = np.tile(lin(col['shroud']), (n, 1))
    hc = np.clip(B.hood_creases(p) / 0.004, -1, 1)
    rgb = np.where(zz['hood'][:, None], fold_shade(rgb, hc * 0.7, col, 0.45, 0.4), rgb)
    ok = zz['open_k']
    rgb = blend(rgb, smooth(0.0, 0.03, ok) * (1.0 - smooth(0.04, 0.12, ok)) * 0.45, col['light'])   # the frayed lip
    # round 3: a thin lining just inside the edge, then dark (the wide grey band read as a fur ruff)
    # (the inner wall runs along the view rays, so any change across it streaked like fur: it is all void now)
    rgb = blend(rgb, smooth(0.01, 0.04, ok), col['lining'])
    rgb = blend(rgb, smooth(0.03, 0.08, ok), col['void_lift'])
    rgb = blend(rgb, smooth(0.06, 0.14, ok), col['void'])
    # the hood's torn lower edge where it hangs over the cape (form.hood_drape): singed toward the edge
    rel = p - F.H0
    below = rel[:, 2] < 0
    phi = np.arctan2(p[:, 0], -(p[:, 1] - D.sh_abyc(z)[2]))
    dz = z - F.drape_z(phi)
    edge = zz['hood'] * below * smooth(0.04, 0.0, dz) * smooth(1.05, 1.35, np.abs(np.angle(np.exp(1j * phi))))
    rgb = blend(rgb, edge * 0.18, col['singe'])          # round 3: faint (a dark band read as a seam all round)
    rgb = rgb * np.where(smooth(0.06, 0.14, ok) > 0.5, 1.0, cloth_k(pal))[:, None]
    # polish: the hood's chin under the opening, down to the hands, is the void too (with the panel tops lowered behind
    # the hands it showed as a pale band over a dark slot, a mouth)
    chin = zz['hood'] * smooth(0.615, 0.575, z) * smooth(0.17, 0.12, np.abs(p[:, 0])) * smooth(-0.04, -0.09, p[:, 1])
    rgb = blend(rgb, chin, col['void'])
    # the face: matte dark (round 3: the halo is the eye patches' margin, so a blink closes it too)
    fy = np.clip(-(p[:, 1] - F.F0[1]) / F.FACE_R[1], 0, 1)        # 1 facing straight out of the hood, 0 at its rim
    rgb = np.where(zz['face'][:, None], lin(col['void'])[None] * (0.3 + 0.7 * smooth(0.25, 0.85, fy))[:, None], rgb)
    # the core: dark, warming toward ember low down and on its underside (seen through the tears and under the hems)
    # round 3: charcoal, a soft mottled warm glow only low down (it read as flat orange plastic)
    sp = ember_spots(p, smooth(0.46, 0.28, z))
    core_rgb = blend(np.tile(lin(col['char']), (n, 1)), sp * 0.9, col['ember'])
    rgb = np.where(zz['core'][:, None], core_rgb, rgb)
    inner = np.maximum(np.maximum(smooth(0.06, 0.14, ok), zz['core'] * 1.0), chin)
    rough = np.where(inner > 0.5, 1.0, 0.92)
    glow = np.where(zz['core'], 0.55 * sp, 0.0)
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, np.zeros(n)], axis=1), 'glow': np.clip(glow, 0, 1), 'inner': inner}


def prop_paint(ob, pal: dict) -> dict:
    """The props per vertex: the cloth's folds, soot and charred cut edges, its underside's warm light; the tip; the
    cream hands; the wisps' charcoal to near black; the lantern's iron and glowing glass."""
    col = colours(pal)
    part = np.rint(S.attr_array(ob, 'part')).astype(int)
    pt = S.attr_array(ob, 'pt').astype(np.float64)
    side = S.attr_array(ob, 'side').astype(np.float64)
    co, _vn = S.mesh_arrays(ob)
    n = len(part)
    ck = cloth_k(pal)
    rgb = np.tile(lin(col['shroud']), (n, 1))
    rough = np.full(n, 0.92)
    coat = np.zeros(n)
    glow = np.zeros(n)
    m = np.isin(part, (PR.CAPE, PR.PANEL))
    if m.any():
        q = co[m]
        _a, _b, yc = D.sh_abyc(q[:, 2])
        th = F.theta_of(q, yc)
        deep = 0.018 + 0.085 * smooth(0.62, 0.2, q[:, 2])
        f = np.clip(D.folds(th, q[:, 2]) / deep, -1, 1)
        c = fold_shade(rgb[m], f, col)
        # round 3: the lower third singes from the shroud's grey to a burnt brown, charcoal at the torn ends
        c = blend(c, smooth(0.6, 0.86, pt[m]) * 0.92, col['singe'])
        c = blend(c, smooth(0.84, 1.0, pt[m]) * 0.95, col['char'])
        rim = hole_rims(q)
        c = blend(c, rim * 0.85, col['singe'])
        c = blend(c, smooth(0.5, 0.9, rim) * 0.9, col['char'])
        c = c * ck
        # polish: painted ember specks on the outer cloth near the hem too (more sparks than the shader's dots)
        spo = ember_spots(q + 0.37, smooth(0.66, 1.0, pt[m]) * 0.45)
        c = blend(c, spo * 0.9, col['ember'])
        inner = side[m] < -0.5
        mt = mottle(q)
        # polish: char with glowing ember specks (a uniform warm mix read as flat rust panels in ko and the holes),
        # denser toward the hem and round the holes, with a faint warmth right at the hem
        sp = ember_spots(q, np.maximum(smooth(0.55, 1.0, pt[m]), rim) * (0.55 + 0.45 * mt))
        ci = blend(np.tile(lin(col['char']), (int(m.sum()), 1)), smooth(0.86, 1.0, pt[m]) * 0.16, col['ember_deep'])
        ci = blend(ci, sp * 0.9, col['ember'])
        edge = np.abs(side[m]) < 0.5                         # the cut edges: charred, the odd ember
        ce = blend(np.tile(lin(col['char']), (int(m.sum()), 1)), sp * 0.8, col['ember'])
        rgb[m] = np.where(edge[:, None], ce, np.where(inner[:, None], ci, c))
        glow[m] = np.where(edge | inner, 0.55 * sp, 0.5 * spo)
    m = part == PR.TIP
    if m.any():
        pa = S.attr_array(ob, 'pa').astype(np.float64)[m]
        c = blend(rgb[m], 0.12, col['light'])
        # round 3: its torn thin edges and its end singed
        c = blend(c, (np.abs(np.sin(2 * np.pi * pa)) ** 8 * 0.75 + smooth(0.85, 1.0, pt[m]) * 0.6).clip(0, 1), col['singe'])
        c = blend(c, np.abs(np.sin(2 * np.pi * pa)) ** 20 * 0.7, col['char'])
        rgb[m] = c * ck
    m = part == PR.HAND
    if m.any():
        q = co[m]
        hx = np.where(q[:, 0] > 0, F.ARM['hand'][0], -F.ARM['hand'][0])
        lx = (q[:, 0] - hx) / 0.03
        front = np.clip(-(q[:, 1] - F.ARM['hand'][1]) / 0.024, 0, 1)
        lz = (q[:, 2] - F.ARM['hand'][2]) / 0.026
        crease = np.zeros(len(q))
        for gx in (-0.5, 0.0, 0.5):
            crease = np.maximum(crease, np.exp(-((np.abs(lx) - abs(gx)) / 0.07) ** 2) * front ** 1.5 * (0.4 + 0.6 * np.clip(lz + 0.3, 0, 1)))
        c = np.tile(lin(col['hand']), (len(q), 1))
        c = c * (0.8 + 0.2 * smooth(-0.9, 0.6, lz))[:, None]   # soft shading: lighter on top, a warmer shade underneath
        c = blend(c, crease * 0.75, col['hand_crease'])
        rgb[m] = c
        rough[m] = 0.8
    for pid in (PR.WISP, PR.LASH):                          # round 3: the lash is the thick front wisps
        m = part == pid
        if m.any():
            t = np.clip(pt[m], 0, 1)
            # polish: dark at the root under the char hem, lightening to pale smoke at the tip (black tips read as claws)
            rgb[m] = blend(np.tile(lin(col['smoke_root']), (int(m.sum()), 1)), smooth(0.12, 0.95, t) ** 0.8, col['smoke_tip'])
            rough[m] = 0.9
    m = np.isin(part, (PR.IRON, PR.RING))
    if m.any():
        rgb[m] = lin(col['iron'])
        rough[m] = 0.5
        coat[m] = 0.1
    m = part == PR.GLASS
    if m.any():
        pa = S.attr_array(ob, 'pa').astype(np.float64)[m]
        win, flame = PR.pane_masks(pa, pt[m])
        rgb[m] = lin(col['glass'])
        rough[m] = 0.35
        coat[m] = 0.3
        glow[m] = win * (0.3 + 0.7 * flame)                    # dim panes, the flame bright inside, none on the iron
    rgb = np.where(np.isin(part, PR.LANTERN_PARTS)[:, None], rgb, lantern_light(rgb, co, pal, col))
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, coat], axis=1), 'glow': np.clip(glow, 0, 1)}
