"""Frostlance's colours and per-vertex paint (frostlance_ultra.py paint_sources); the per-pixel bake materials (the
freckles, snowflakes, mottling, the face) are in frostlance_shade.py.

Smooth whale skin (1-hero, 2-turnaround, 4-details 1 and 6): a deep-teal back from the forehead over the whole top and
down the flanks to a soft, wavy waterline that drops from the brows to the tail's underside; pale blue-white sides and
face below it; the chin, the throat and the belly white. The tail is teal with a pale line underneath; the fins and the
fluke teal, paler at the root, with frosty icy edges. The tusk is bright frosty ice: a pale core with darker spiral
grooves and paler ridges.

Colours (CONTENT §2.2 #30): body #D8EEF7, underside #F5FBFE, back #1F7A8C, tusk #BDE8F5 (the card's extra), eyes
#1B263B. Parts the palette has no colour for are made from it (`colours`): the mottling (the back's teal mixed 45% into
the body's pale blue), the freckles and snowflakes (the underside's white), the frost (the tusk's ice toward the white),
the tusk's grooves (the ice 30% toward the teal) and ridges (toward the white), the iris (the eyes' navy toward the
teal, lifted), the brows, lash lines and the smile (the eyes' navy toward the teal).
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import frostlance_form as F
from monsters.breeds import frostlance_props as PR


def colours(pal: dict) -> dict:
    body, belly, back, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    ice = pal.get('tusk', '#BDE8F5')
    return {
        'body': body, 'belly': belly, 'back': back, 'eye': eye, 'ice': ice,
        'back_deep': C.mix_hex(back, eye, 0.3),              # the top of the back: the film's light lifts the teal about
                                                              # 1.7x and veils it (measured 81,159,178 against the
                                                              # pictures' 50,133,156), so the paint sits deeper
        'back_soft': C.mix_hex(back, body, 0.22),            # the waterline's teal side
        'mottle': C.mix_hex(back, body, 0.35),               # round 1: the dappled band's mid-blue spots (about #5FA6BD)
        'speck': C.mix_hex(back, body, 0.4),                 # the cheeks' tiny blue freckles
        'freckle': belly,                                     # the white freckles and snowflakes
        'fin_root': C.mix_hex(back, body, 0.45),
        'frost': C.mix_hex(ice, belly, 0.45),                # the fins' and the fluke's icy shards (round 3: about #DCEFF7)
        'frost_tip': C.mix_hex(ice, belly, 0.75),            # the crystals' points and veins
        'ice_core': C.mix_hex(ice, belly, 0.1),              # the tusk's clear icy body
        'ice_groove': C.mix_hex(ice, back, 0.62),            # its grooves, deep steel blue (polish: deeper than the crests)
        'teal_dark': C.mix_hex(back, eye, 0.45),             # round 3: the back's darker mottled patches (4-details 6)
        'ice_ridge': C.mix_hex(ice, belly, 0.7),             # its ridges' frosty crests
        'ice_tip': C.mix_hex(ice, belly, 0.35),              # its point, paler
        'iris': C.mix_hex(C.shade_hex(eye, 2.2), back, 0.35),
        'iris_light': C.mix_hex(C.shade_hex(eye, 3.4), back, 0.3),
        'iris_ring': eye,
        'pupil': C.shade_hex(eye, 0.55),
        'sclera': C.mix_hex(belly, body, 0.15),
        'lid': C.shade_hex(eye, 0.55),                        # round 1: a heavier, near-black lash line
        'brow': C.shade_hex(eye, 0.8),                        # round 1: on the teal now, dark navy
        'smile': C.mix_hex(eye, back, 0.2),
    }


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def blend(rgb: np.ndarray, k, hexc) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0, 1)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    c = lin(hexc) if isinstance(hexc, str) else np.asarray(hexc, np.float64)
    c = c[None] if c.ndim == 1 else c
    return rgb * (1 - k[:, None]) + c * k[:, None]


# ----------------------------------------------------------------------------- the coat's layout
# the waterline (the teal's lower edge) and the belly line, by y (snout -0.4 .. tail 0.7)
WATER = [(-0.42, 0.705), (-0.34, 0.7), (-0.26, 0.66), (-0.18, 0.6), (-0.1, 0.54), (0.0, 0.5), (0.1, 0.475), (0.2, 0.46),
         (0.4, 0.45), (0.6, 0.45), (0.8, 0.45)]
# round 1: the teal runs down the flanks to about the fins' roots and over the face to just above the eyes (the brows
# sit on teal: 1-hero, 2-turnaround, 3-faces)
BELLY = [(-0.42, 0.578), (-0.33, 0.563), (-0.25, 0.52), (-0.15, 0.47), (-0.05, 0.44), (0.1, 0.4), (0.3, 0.39), (0.45, 0.405),
         (0.6, 0.415), (0.8, 0.41)]


def _interp(y: np.ndarray, tab) -> np.ndarray:
    ys, zs = zip(*tab)
    return np.interp(y, ys, zs)


def _wave(p: np.ndarray, amp: float, seed: float) -> np.ndarray:
    """A smooth, wavy offset along the body (a sum of low sines: no lattice)."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    return amp * (0.55 * np.sin(17.0 * y + 5.0 * np.abs(x) + seed) + 0.3 * np.sin(31.0 * y - 9.0 * z + 2.1 * seed)
                  + 0.15 * np.sin(53.0 * y + 21.0 * np.abs(x) + 0.7 * seed))


def water(p: np.ndarray) -> np.ndarray:
    """The teal's lower edge (z) at each point: the flank line by y, lifted over the face to just above the eyes."""
    x, y = p[:, 0], p[:, 1]
    zw = _interp(y, WATER) + _wave(p, 0.012, 0.3)
    front = smooth(-0.24, -0.33, y)
    return zw + front * (0.04 * smooth(0.21, 0.14, np.abs(x)) + 0.012 * smooth(0.08, 0.0, np.abs(x)))


def teal_k(p: np.ndarray) -> np.ndarray:
    """0..1: the deep-teal back, a soft edge (the dappled band under it does the rest)."""
    p = np.asarray(p, np.float64)
    zw = water(p)
    return smooth(zw - 0.03, zw + 0.03, p[:, 2])


def belly_k(p: np.ndarray) -> np.ndarray:
    """0..1: the white underside (the chin under the smile, the throat, the belly, a line under the tail)."""
    p = np.asarray(p, np.float64)
    zb = _interp(p[:, 1], BELLY) + _wave(p, 0.008, 1.7)
    return smooth(zb + 0.03, zb - 0.03, p[:, 2])


def band_k(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(band, edge) 0..1: the dappled band of mid-blue spots under the teal's edge (4-details 1, 2), densest at the edge
    and thinning out below it; never on the lids."""
    p = np.asarray(p, np.float64)
    d = water(p) - p[:, 2]
    clear = smooth(F.EYE_R * 1.25, F.EYE_R * 1.6, F.eye_dist(p))
    # polish: not in the middle of the face (between the eyes, round the tusk's root): 3-faces keeps it clean
    clear = clear * (1.0 - smooth(-0.26, -0.33, p[:, 1]) * smooth(0.095, 0.05, np.abs(p[:, 0])))
    band = smooth(-0.03, 0.0, d) * smooth(0.14, 0.05, d) * clear
    edge = smooth(-0.035, -0.01, d) * smooth(0.05, 0.015, d) * clear
    return band, edge


def cheek_k(p: np.ndarray) -> np.ndarray:
    """0..1: the cheeks under and beside the eyes, where tiny blue freckles lie (3-faces neutral)."""
    p = np.asarray(p, np.float64)
    out = np.zeros(len(p))
    for s in (1, -1):
        c = v3(F.EYE_C[s][:]) + np.array([0.035 * s, 0.03, -0.07])
        out = np.maximum(out, smooth(0.075, 0.035, np.linalg.norm(p - c, axis=1)))
    return out


def body_paint(p: np.ndarray, pal: dict, vn: np.ndarray | None = None) -> dict:
    """Per point of the body: 'paint' (linear RGB), 'rough' (1, roughness, coat), 'glow' and the masks the bake reads per
    pixel. The glow (round 1) is a soft fill on the underside: the studio's light never reaches it, so the white belly
    rendered flat grey (#95-#9F) below a #D2EAF3 face, where the pictures' belly is the brightest part (about #CDDADF).
    Its baked AO was already 1; the glow lifts only what faces down at rest, in its own colour, under the bloom."""
    col = colours(pal)
    n = len(p)
    tk, bk = teal_k(p), belly_k(p)
    # polish: the stalk's end teal all round (a pale underside there smeared into streaks seen from behind)
    tk = np.maximum(tk, smooth(0.47, 0.53, p[:, 1]))
    bk = bk * (1 - smooth(0.47, 0.53, p[:, 1]))
    rgb = np.tile(lin(col['body']), (n, 1))
    rgb = blend(rgb, bk, col['belly'])
    rgb = blend(rgb, tk, col['back_soft'])
    deep = smooth(0.04, 0.14, (p[:, 2] - water(p)))
    rgb = blend(rgb, tk * deep, col['back'])
    rgb = blend(rgb, 0.85 * tk * deep, col['back_deep'])
    rough = 0.56 + 0.14 * tk                                   # the teal matte (its specular veiled it pale)
    coat = 0.08 - 0.06 * tk
    # polish: matte round the fins' roots (the only glossy patch was a sliver in that crease)
    near = np.zeros(n)
    for s_ in (1, -1):
        near = np.maximum(near, smooth(0.16, 0.1, np.linalg.norm(p - np.array(F.fin_axes(s_)[0][:]), axis=1)))
    rough = rough * (1 - near) + 0.8 * near
    coat = coat * (1 - near)
    band, edge = band_k(p)
    glow = np.zeros(n)
    if vn is not None:
        # round 1 (second pass): weaker, over a slightly deeper underside, so a belly turned up to the key (win, hit_heavy, ko) stays
        # under the bloom (at 0.6 it lit thousands of near-white pixels and a halo)
        down = smooth(0.15, -0.55, vn[:, 2])
        glow = 0.5 * down * (0.4 + 0.6 * bk) * (1 - tk)
        # round 3: the shaded underside cool blue-grey, not neutral grey: the white turns toward the body's pale blue
        # where it faces down (about the same value; the glow carries the hue too)
        rgb = blend(rgb, 0.8 * down * bk, col['body'])
        rgb = rgb * (1.0 - 0.06 * down * bk)[:, None]
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, coat], axis=1), 'glow': np.clip(glow, 0, 1),
            'teal': tk, 'band': band * (1 - 0.6 * tk), 'edge': edge, 'cheek': cheek_k(p) * (1 - tk),
            'pleat': pleat_k(p, vn), 'clear': clear_k(p)}


def clear_k(p: np.ndarray) -> np.ndarray:
    """0..1, 0 where no freckle or snowflake may lie (round 3): round the fins' fleshy roots (a white fleck sat in the
    crease) and on the stalk's flattened end (its speckles stretched into streaks)."""
    p = np.asarray(p, np.float64)
    k = smooth(0.5, 0.46, p[:, 1])
    # polish: none on the tail stock's underside either (seen from behind they smeared into radial streaks)
    zc = np.interp(p[:, 1], F._SW[:, 0], F._SW[:, 1])
    k = k * (1.0 - smooth(0.28, 0.34, p[:, 1]) * smooth(zc + 0.01, zc - 0.02, p[:, 2]))
    for s_ in (1, -1):
        o = np.array(F.fin_axes(s_)[0][:])
        k = k * smooth(0.11, 0.15, np.linalg.norm(p - o, axis=1))
    return k


# ----------------------------------------------------------------------------- the belly's grooves (round 1)
PLEAT_GAP = 0.034                   # metres between the throat's and the belly's lengthwise grooves (1-hero, 2-turnaround)


def pleat_k(p: np.ndarray, vn: np.ndarray | None = None) -> np.ndarray:
    """0..1: where the faint lengthwise grooves run: the white underside from the chin to mid-belly, facing down."""
    p = np.asarray(p, np.float64)
    k = belly_k(p) * smooth(-0.36, -0.3, p[:, 1]) * smooth(0.3, 0.18, p[:, 1]) * smooth(0.11, 0.04, np.abs(p[:, 0]))
    if vn is not None:
        k = k * smooth(0.25, -0.2, vn[:, 2])
    return k


def pleat_depth(p: np.ndarray) -> np.ndarray:
    """0..1 groove profile across x: even, parallel, evenly spaced (round 3: they wobbled into crumpled creases)."""
    return (0.5 + 0.5 * np.cos(2 * np.pi * p[:, 0] / PLEAT_GAP)) ** 2      # polish: broad, shallow, 5-7 of them


# ----------------------------------------------------------------------------- the props
def prop_paint(ob, pal: dict) -> dict:
    """The fins and the fluke: teal (paler at a fin's root, where it leaves the pale flank), fading through the frost band
    to pale ice at the shards; the tusk: clear ice in value (round 1): a pale core, steel-blue grooves and shadow side,
    a near-white crest on the ridge (per pixel, frostlance_shade). Each with its roughness, coat and glow."""
    col = colours(pal)
    part = np.rint(S.attr_array(ob, 'part')).astype(int)
    su = S.attr_array(ob, 'su').astype(np.float64)
    frost = S.attr_array(ob, 'frost').astype(np.float64)
    groove = S.attr_array(ob, 'groove').astype(np.float64)
    shade = S.attr_array(ob, 'shade').astype(np.float64)
    ed = S.attr_array(ob, 'ed').astype(np.float64)
    n = len(part)
    rgb = np.tile(lin(col['back']), (n, 1))
    rough = np.full(n, 0.5)
    coat = np.full(n, 0.15)
    glow = np.zeros(n)
    slab = part != PR.TUSK
    if slab.any():
        c = np.tile(lin(col['back']), (n, 1))
        fin = part == PR.FIN
        root = np.where(fin, smooth(0.3, 0.0, su), 0.0)                  # the fluke stays teal at its root (a pale bar showed)
        # polish: a fin's root takes the body's own paint where it leaves the skin, matte (a frosted, coated root edge
        # caught the key as a glossy white sliver)
        co = S.mesh_arrays(ob)[0]
        skin = body_paint(co, pal)['paint']
        rk = np.where(fin, smooth(0.2, 0.08, su), 0.0)
        c = blend(c, 0.75 * root * (1 - rk), col['fin_root'])
        c = c * (1 - rk[:, None]) + skin * rk[:, None]
        c = blend(c, smooth(0.0, 0.55, frost) * 0.55, col['back_soft'])
        c = blend(c, smooth(0.35, 1.0, frost), col['frost'])
        tip = smooth(0.006, 0.0, ed) * frost
        c = blend(c, tip, col['frost_tip'])
        rgb[slab] = c[slab]
        rough[slab] = (0.5 - 0.16 * frost + 0.12 * rk)[slab]
        coat[slab] = ((0.12 + 0.3 * frost) * (1 - rk))[slab]
        glow[slab] = (0.2 * frost ** 1.5 * (1 - rk))[slab]
    tk = part == PR.TUSK
    if tk.any():
        c = np.tile(lin(col['ice_core']), (n, 1))
        c = blend(c, smooth(0.4, 0.95, groove) * 0.95, col['ice_groove'])
        c = blend(c, 0.5 * smooth(0.22, 0.0, groove), col['ice_ridge'])      # polish: the crests clearly paler
        c = blend(c, 0.04 * shade, col['ice_groove'])
        c = blend(c, 0.45 * smooth(0.6, 1.0, su) * (1 - shade), col['ice_tip'])
        c = blend(c, 0.8 * smooth(0.83, 0.97, su), col['ice_ridge'])          # round 3: the last 15% nearly white
        base = smooth(0.04, -0.05, su)                 # the root under the skin a little darker (never seen)
        c = blend(c, 0.4 * base, col['ice_groove'])
        rgb[tk] = c[tk]
        # round 3: one sharp highlight, not a broad satin sheen (the coat's wide lobe read as plastic)
        rough[tk] = 0.3
        coat[tk] = 0.06
        # polish: its shadow side lifted by a small untinted self-light (from the front it rendered #4B6C75-#658D98, a
        # grey stone horn); the lit side keeps only a faint light on the crests
        glow[tk] = (0.1 * smooth(0.3, 0.0, groove) * (1 - shade) + 0.85 * shade)[tk] * smooth(-0.02, 0.03, su[tk])
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, coat], axis=1), 'glow': np.clip(glow, 0, 1)}
