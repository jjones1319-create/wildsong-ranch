"""Wishlume's colours and per-vertex paint (wishlume_ultra.py paint_sources); the per-pixel materials are in
wishlume_shade.py.

The look's heart is the warm flame glowing through thin paper (round 2, after the review: it shaded like an opaque
matte ball, its shadow side grey-olive). The paper is painted a little darker than lit paper would be (ALBEDO_K) and
glows instead (the ORM alpha, tinted a warm cream-orange made from the glow and the lighter paper):
- a floor everywhere, so no side of the paper ever goes grey (the shadow side stays a warm sand);
- the lower third and the paddles' roots saturate toward the glow #FFB85C, fading back to cream by the eye line;
- the face panel stays plain cream with the least glow, so the ink keeps its contrast;
- the inside of the lantern and the band of lit paper over the lowered hoop are the hottest, a pale gold core where the
  flame burns.
The red frame, the tassel and the ink never glow: darker lines against the light.

Colours (CONTENT §2.2 #5): paper #F6E3B4, lighter paper #FFF2D6, ribs and tassel #D94F4F, glow #FFB85C, eyes #3A2A2A.
Beacon Wishlume (secrets.ts `beacon-wishlume`, "red-and-white stripes"; variants.ts): #F6F1EA / #FFFFFF / #D9262C /
#3A2A2A, the glow staying #FFB85C; its paddles stay white. Parts the palette has no colour for are made from it
(`colours`): the twine and the gold bands (the glow toward the ink), the leaves and the blush (the red toward the
paper), the iris (the ink toward the glow: the pictures' amber eyes), the sclera (the lighter paper toward white), the
glow's tint (the glow toward the lighter paper).
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import wishlume_form as F
from monsters.breeds import wishlume_props as PR

GLOW_HEX = '#FFB85C'
HEART = tuple(F.surface_at(0.0, 0.47)[:])  # polish: the glow core on the front paper, a third of the way up, under the mouth
ALBEDO_K = (0.86, 0.8)               # the paper's lit colour, linear (low, high): the glow makes up the rest; the key-lit
                                     # upper half a little lower, so lit paper and glow together stay under the bloom


def colours(pal: dict) -> dict:
    paper, light, red, ink = pal['body'], pal['belly'], pal['accent'], pal['eye']
    glow = pal.get('glow', GLOW_HEX)
    beacon = bool(pal.get('stripes'))
    return {
        'paper': paper, 'light': light, 'red': red, 'ink': ink, 'glow': glow,
        'paper_top': C.mix_hex(paper, glow, 0.08),                       # cream, a touch warm (it glows in its own colour)
        'paper_low': C.mix_hex(paper, glow, 0.55),                       # the lower third, toward the glow
        'heart': C.mix_hex(paper, glow, 0.72),                           # polish: round the glow core under the mouth
        'paper_mid': C.mix_hex(paper, glow, 0.22),
        'arm': paper if beacon else C.mix_hex(paper, glow, 0.18),        # Beacon's paddles stay white
        'arm_root': C.mix_hex(paper, glow, 0.22 if beacon else 0.5),
        'skirt': C.mix_hex(glow, light, 0.35),                           # the lit lip over the hoop
        'skirt_top': C.mix_hex(glow, light, 0.6),
        'inside_rim': C.mix_hex(glow, red, 0.22),                        # round 3: a deep orange inside (glowing, it reads
        'inside': glow,                                                  # #FFB85C) ...
        'inside_core': C.mix_hex(glow, light, 0.3),                      # ... warming to the pale flame (#FFE6A0 and paler)
        'flame_mid': C.mix_hex(light, '#FFFFFF', 0.25),                  # the flame paler still
        'flame_core': C.mix_hex(light, '#FFFFFF', 0.6),
        'flame_edge': C.mix_hex(glow, red, 0.3),
        'tint': C.mix_hex(glow, light, 0.35),                            # the glow's tint
        'leaf': red if beacon else C.mix_hex(red, paper, 0.2),            # polish: Beacon's leaves #D9262C, not maroon
        'leaf_base': C.mix_hex(red, ink, 0.12) if beacon else C.mix_hex(red, ink, 0.06),
        'leaf_rib': C.mix_hex(red, ink, 0.4) if beacon else C.mix_hex(red, ink, 0.28),
        'leaf_edge': light,
        'blush': C.mix_hex(light, red, 0.42),
        'blush_line': C.mix_hex(light, red, 0.66),
        'rib': C.shade_hex(red, 0.94),
        'rib_node': C.mix_hex(red, ink, 0.3),
        'lacquer': red,
        'twine': C.mix_hex(glow, ink, 0.38),
        'twine_dark': C.mix_hex(glow, ink, 0.58),
        'gold': C.shade_hex(C.mix_hex(glow, light, 0.18), 0.86),
        'thread': red,
        'thread_dark': C.mix_hex(red, ink, 0.3),
        'thread_light': C.mix_hex(red, light, 0.16),
        'core': C.mix_hex(red, ink, 0.22),
        'iris': C.mix_hex(ink, glow, 0.2),                         # round 3: a rich brown
        'iris_warm': C.mix_hex(ink, glow, 0.62),
        'iris_deep': C.mix_hex(ink, glow, 0.32),
        'sclera': C.mix_hex(light, '#FFFFFF', 0.55),
        'stripe': red,
    }


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def blend(rgb: np.ndarray, k, hexc: str) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0, 1)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    return rgb * (1 - k[:, None]) + lin(hexc)[None] * k[:, None]


def face_panel(p: np.ndarray) -> np.ndarray:
    """0..1 on the upper front panel round the face (kept plain cream, the least glow)."""
    th = F.theta_deg(p)
    return smooth(44, 30, np.abs(th)) * smooth(0.5, 0.54, p[:, 2]) * smooth(0.73, 0.69, p[:, 2])


def body_paint(p: np.ndarray, pal: dict, crease=None) -> dict:
    """Per point of the body: 'paint' (linear RGB), 'rough' (1, roughness, coat), 'glow' (0..1)."""
    col = colours(pal)
    n = len(p)
    z = p[:, 2]
    ak = F.arm_k(p)
    low = smooth(0.575, 0.4, z)                                      # 0 by the eye line, 1 in the lower third
    edge = smooth(0.375, F.Z_OPEN + 0.004, z)                         # just above the opening
    fp = face_panel(p)
    rgb = np.tile(lin(col['paper_top']), (n, 1))
    rgb = blend(rgb, fp, col['paper'])                                # the face panel plain cream
    rgb = blend(rgb, low * (1 - fp), col['paper_mid'])
    rgb = blend(rgb, low ** 1.6 * 0.95, col['paper_low'])
    # round 3: the glow in the paper's own colour (strength 2.0): a floor, so no side goes grey; the lower third the
    # most, but well under the inside, which is the brightest thing on the model
    th = np.abs(F.theta_deg(p))
    side = smooth(36, 50, th) * smooth(0.76, 0.68, z)   # the flanks, off the face and below the crown
    # polish: a soft glow core a third of the way up the front, under the mouth (#FFC67A round it), and less glow on the
    # upper rim away from the face, where the studio's rim lights and the glow bloomed into a white halo
    heart = np.exp(-(np.linalg.norm(p - v3(HEART), axis=1) / 0.11) ** 2)
    rim_up = smooth(0.6, 0.72, z) * smooth(40, 70, th)
    rgb = blend(rgb, heart * 0.7, col['heart'])
    glow = 0.17 + 0.07 * side + 0.23 * low + 0.1 * edge - 0.05 * fp + 0.16 * heart - 0.08 * rim_up
    # the paddles: warm paper, warmest at the root where the flame's light comes through (1-hero, 4-details 3)
    root = np.zeros(n)
    for s in (1, -1):
        on = np.sign(p[:, 0]) == s
        loc = F.arm_local(p[on], s)
        root[on] = smooth(0.03, -0.08, loc[:, 0])
    arm_rgb = blend(np.tile(lin(col['arm']), (n, 1)), root * 0.85, col['arm_root'])
    rgb = rgb * (1 - ak[:, None]) + arm_rgb * ak[:, None]
    beacon = bool(pal.get('stripes'))
    arm_glow = (0.08 + 0.1 * root) if beacon else (0.14 + 0.16 * root)        # round 3: less (the paddles bloomed into a halo)
    glow = glow * (1 - ak) + arm_glow * ak
    rgb = rgb * (ALBEDO_K[0] + (ALBEDO_K[1] - ALBEDO_K[0]) * smooth(0.55, 0.7, z) - 0.06 * rim_up)[:, None]
    # the inside of the lantern, seen through the opening: the glow at the rim to a pale gold core over the flame
    dish = (z < F.Z_OPEN + F.DISH_D + 0.003) & (F.ellip_r(p) < F.R_OPEN * 1.003) & (ak < 0.5) & (z < 0.42)
    if dish.any():
        sd = np.clip(F.ellip_r(p[dish]) / F.R_OPEN, 0, 1)
        d = np.tile(lin(col['inside_rim']), (int(dish.sum()), 1))
        d = blend(d, smooth(1.0, 0.7, sd), col['inside'])
        d = blend(d, smooth(0.6, 0.15, sd), col['inside_core'])
        rgb[dish] = d
        glow[dish] = 0.5           # polish: a saturated amber well (at 1.0 the tone map washed it pale); the flame burns at 1
    if crease is not None:
        rgb = rgb * (1 - 0.08 * np.clip(crease, 0, 1))[:, None]
    rough = np.where(dish, 0.6, 0.86)
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, np.zeros(n)], axis=1), 'glow': np.clip(glow, 0, 1), 'dish': dish}


def prop_paint(ob, pal: dict) -> dict:
    """The props per vertex: lacquered red frame, twine, gold, silk; the band over the hoop and the hoop's inner face
    lit by the flame."""
    col = colours(pal)
    part = np.rint(S.attr_array(ob, 'part')).astype(int)
    pt = S.attr_array(ob, 'pt').astype(np.float64)
    pr = S.attr_array(ob, 'pr').astype(np.float64)
    co, _vn = S.mesh_arrays(ob)
    n = len(part)
    rgb = np.tile(lin(col['lacquer']), (n, 1))
    rough = np.full(n, 0.4)
    coat = np.full(n, 0.3)
    glow = np.zeros(n)

    def put(mask, hexc, r, c):
        rgb[mask] = lin(hexc)
        rough[mask] = r
        coat[mask] = c
    put(np.isin(part, (PR.RIB, PR.ARMRIM)), col['rib'], 0.42, 0.28)
    put(np.isin(part, (PR.WRAP, PR.RINGWRAP, PR.ROPE, PR.COLLAR, PR.HANDLEBAND)), col['twine'], 0.82, 0.0)
    put(part == PR.GOLD, col['gold'], 0.34, 0.4)
    put(part == PR.CORD, col['rib'], 0.6, 0.08)
    put(part == PR.CORE, col['core'], 0.55, 0.08)
    sk = part == PR.SKIRT
    if sk.any():
        rgb[sk] = lin(col['paper_low']) * ALBEDO_K[0]               # polish: the paper running down to the hoop
        rough[sk] = 0.86
        coat[sk] = 0.0
        glow[sk] = 0.5
    th = part == PR.THREAD
    if th.any():
        t = np.clip(pt[th], 0, 1)
        c = np.tile(lin(col['thread']), (int(th.sum()), 1))
        c = blend(c, smooth(0.25, 0.0, t) * 0.45, col['thread_dark'])            # shaded where they leave the collar
        c = blend(c, (pr[th] > 0.62) * 0.3, col['thread_light'])               # a few lighter strands
        c = blend(c, (pr[th] < 0.18) * 0.3, col['thread_dark'])
        rgb[th] = c
        rough[th] = 0.45
        coat[th] = 0.15
    # the hoop's inner face and the cords near the opening are lit by the flame
    ring = np.isin(part, (PR.RING, PR.RINGWRAP))
    inner = smooth(PR.RING_R + 0.001, PR.RING_R - 0.006, F.ellip_r(co)) * smooth(PR.RING_Z + 0.009, PR.RING_Z - 0.006, co[:, 2])
    glow = np.where(ring, 0.35 * inner, glow)
    rgb[ring] = blend(rgb[ring], inner[ring] * 0.4, col['inside'])
    glow = np.where(part == PR.CORD, 0.14 * smooth(0.29, 0.315, co[:, 2]), glow)
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, coat], axis=1), 'glow': np.clip(glow, 0, 1)}
