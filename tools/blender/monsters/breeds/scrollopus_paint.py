"""Scrollopus's paint (Art 2.1 Ultra): per-vertex colour, roughness and coat for the skin and the props, the per-pixel
ink spots and freckles, the props' per-pixel details and the eyes.

Colours from CONTENT 27: skin #7D5BA6, underside #CDB4E6, ink spots #2E2A4F, cap #3A3A55, tassel #F2C94C (the card puts
the spectacle rims in the same gold), eyes #1E1E2E. Derived (CONTENT has no hex for these; the pictures show where they
go): the suckers' rims and cups (the underside toward white and toward the skin), the blush (the underside mixed toward
the gold, saturated: a rosy lilac), the gold's light and shadow (toward a pale cream and a dark brown, neutrals), the
parchment and the pages (the gold toward white, desaturated), the book's leather (the skin mixed toward the gold,
darkened: a warm brown), the scroll's cord (the skin toward the eyes' near-black: a deep plum), the quill's vane (the
underside toward white, warmed a little by the gold) with the skin's violet at its tip.
"""
from __future__ import annotations

import colorsys

import numpy as np

from lib import common as C
from lib import marks as MK
from lib import surface as S
from lib.nodes import new_mat
from monsters.breeds import scrollopus_form as F
from monsters.breeds import scrollopus_noise as N

smooth = N.smooth


def lin(h: str) -> np.ndarray:
    return N.v3(C.lin_rgb(h))


def sat_hex(h: str, k: float, v: float = 1.0) -> str:
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(hh, min(1.0, ss * k), min(1.0, vv * v))
    return '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in (r, g, b))


def colours(pal: dict) -> dict:
    body, belly, ink, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    cap, gold = pal.get('cap', '#3A3A55'), pal.get('tassel', '#F2C94C')
    # round 2 (review): tan parchment, reddish-brown leather and a red-brown cord, all from the palette
    # round 3: the parchment a more neutral tan (warmed toward the leather), the cord a real red-brown
    redbrown = sat_hex(C.mix_hex(gold, body, 0.55), 1.8)
    parch = C.shade_hex(sat_hex(C.mix_hex(C.mix_hex(gold, '#FFFFFF', 0.4), redbrown, 0.14), 0.62), 0.88)
    cord = C.shade_hex(sat_hex(C.mix_hex(gold, body, 0.62), 3.2), 0.72)
    leather = C.shade_hex(redbrown, 0.5)
    return {
        'skin': body, 'skin_face': C.mix_hex(body, belly, 0.1), 'skin_deep': C.shade_hex(body, 0.86),
        'under': belly, 'rim': C.mix_hex(belly, '#FFFFFF', 0.24), 'cup': C.mix_hex(belly, body, 0.32),
        'pit': C.shade_hex(C.mix_hex(belly, body, 0.6), 0.8),
        'blush': sat_hex(C.mix_hex(belly, gold, 0.34), 2.3), 'ink': ink, 'brow': ink,
        'mouth': C.mix_hex(eye, body, 0.22), 'lip': C.mix_hex(body, belly, 0.3), 'lid': C.mix_hex(body, belly, 0.18),
        'lash': eye,
        'felt': cap, 'felt_light': C.mix_hex(cap, belly, 0.12), 'felt_dark': C.shade_hex(cap, 0.72),
        'gold': gold, 'gold_hi': C.mix_hex(gold, '#FFFBEA', 0.78), 'gold_lo': C.mix_hex(C.shade_hex(gold, 0.5), '#4A2A00', 0.3),
        'gold_deep': C.mix_hex(C.shade_hex(gold, 0.3), '#2E1800', 0.35), 'strand_root': C.shade_hex(gold, 0.86),
        'gold_edge': C.mix_hex(gold, '#FFFFFF', 0.86), 'cup_hl': C.mix_hex(belly, '#FFFFFF', 0.72),
        'glint': C.mix_hex('#FFFFFF', belly, 0.18),
        'parch': parch, 'parch_edge': C.shade_hex(C.mix_hex(parch, gold, 0.35), 0.72), 'parch_in': C.shade_hex(parch, 0.82),
        'plum': cord,
        'leather': leather, 'leather_dark': C.shade_hex(leather, 0.62), 'leather_light': C.mix_hex(leather, gold, 0.15),
        'page': C.mix_hex(parch, '#FFFFFF', 0.38), 'page_line': C.shade_hex(parch, 0.7),
        'vane': C.mix_hex(C.mix_hex(belly, '#FFFFFF', 0.58), gold, 0.12), 'vane_tip': body,
        'vane_edge': C.shade_hex(C.mix_hex(belly, '#FFFFFF', 0.4), 0.86), 'shaft': C.mix_hex(belly, '#FFFFFF', 0.7),
        'slit': eye,
    }


def _mix(rgb: np.ndarray, col: np.ndarray, k) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)[:, None]
    return rgb * (1 - k) + col[None] * k


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


# ----------------------------------------------------------------------------- the skin
def face_mask(co: np.ndarray) -> np.ndarray:
    return smooth(-0.1, -0.17, co[:, 1]) * smooth(0.395, 0.445, co[:, 2]) * smooth(0.765, 0.685, co[:, 2]) * smooth(0.26, 0.18, np.abs(co[:, 0]))


def blush_mask(co: np.ndarray) -> np.ndarray:
    m = np.zeros(len(co))
    for s in (1, -1):
        d = np.linalg.norm((co - np.array([0.155 * s, -0.19, 0.513])) / np.array([0.058, 0.07, 0.036]), axis=1)
        m = np.maximum(m, smooth(1.0, 0.2, d))
    return m * (co[:, 1] < -0.1)


def brow_paint(co: np.ndarray) -> np.ndarray:
    """The brows (1-hero, 3-faces): thick dark arcs over the rims, full at the inner middle and tapering to a point at
    the outer end; the left one (toward the camera) raised higher and more arched: clever, a little sly."""
    from monsters.breeds import scrollopus_skin as SK
    m = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = SK.eye_axes(s)
        q = co - c
        xe, ye, ze = (q @ xax) / F.EYE_R, (q @ yax) / (F.EYE_R * F.EYE_SHAPE[1]), q @ look
        u = xe * s
        # round 2 (review: flat frowning strokes): gentle feathered arches, the left higher
        # round 3 (review): thicker, the full ink colour, the inner ends a little lower (sly)
        base, arch = (1.74, 0.46) if s > 0 else (1.66, 0.38)
        yb = base + arch * (1.0 - np.clip((u - 0.12) / 1.12, -1, 1) ** 2) - 0.12 * smooth(-0.2, -0.95, u)
        t = 0.23 * (1.0 - 0.65 * smooth(0.3, 1.2, u)) * (1.0 - 0.2 * smooth(-0.4, -1.0, u))
        t = t * (1.0 + 0.18 * N.fbm(co, 1 / 0.005, 97, 2))
        d = np.abs(ye - yb)
        stroke = smooth(t, 0.35 * t, d) * smooth(-1.0, -0.78, u) * smooth(1.28, 1.1, u)
        m = np.maximum(m, stroke * smooth(-0.22, -0.15, ze) * smooth(0.1, 0.07, ze))
    return m


def skin_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal)
    co = I['co']
    n = len(co)
    mott = N.fbm(co, 1 / 0.06, 61, 3)
    rgb = lin(col['skin'])[None] * (0.95 + 0.07 * mott)[:, None]
    rgb = _mix(rgb, lin(col['skin_face']), 0.6 * face_mask(co) * (1 - I['share']))
    rgb = _mix(rgb, lin(col['skin_deep']), 0.3 * I['ring'] + 0.4 * I['crease'])
    under = np.clip(I['under'], 0, 1)
    ub = lin(col['under'])[None] * (0.97 + 0.04 * mott)[:, None]
    rgb = rgb * (1 - under[:, None]) + ub * under[:, None]
    rgb = _mix(rgb, lin(col['cup']), 0.85 * I['cup'])
    rgb = _mix(rgb, lin(col['pit']), 0.7 * I['pit'])
    rgb = _mix(rgb, lin(col['rim']), 0.8 * I['rim'] * (1 - 0.6 * I['cup']))
    rgb = _mix(rgb, lin(col['cup_hl']), 0.6 * I['hl'])                 # round 3: each cup's wet highlight
    rgb = _mix(rgb, lin(col['blush']), 0.55 * blush_mask(co))
    rgb = _mix(rgb, lin(col['lid']), 0.5 * I['closed'])
    bp = brow_paint(co)
    rgb = _mix(rgb, lin(col['brow']), 1.0 * bp)
    rgb = _mix(rgb, lin(col['lash']), 0.35 * np.clip(I['lash'], 0, 1))      # the crisp line is a per-pixel mark (scrollopus_shade)
    rgb = _mix(rgb, lin(col['lip']), 0.35 * I['lip'])
    rgb = _mix(rgb, lin(col['mouth']), 0.92 * np.clip(I['mouth'] * 1.25, 0, 1))
    rgb = rgb * (1.0 + 0.06 * I['drop'])[:, None]
    # glossy wet skin, not plastic: a touch rougher in patches, the coat moderate
    crown = smooth(0.79, 0.91, co[:, 2])              # round 2: no white glare on the crown by the cap
    # round 3 (review: a chalky glare on the head's upper left): the upper head a little rougher, its coat lower; the
    # cups glossy (the wet look lives in the suckers and the beads)
    upper = smooth(0.64, 0.8, co[:, 2]) * (1.0 - I['share'])
    rough = (0.34 + 0.05 * mott + 0.06 * under - 0.08 * I['cup'] - 0.1 * I['rim'] - 0.18 * I['hl'] + 0.25 * np.clip(I['mouth'], 0, 1)
             + 0.2 * bp + 0.1 * crown + 0.1 * upper - 0.15 * I['drop'])
    coat = (0.42 - 0.1 * under + 0.2 * I['rim'] + 0.15 * I['cup'] + 0.3 * I['hl'] - 0.35 * np.clip(I['mouth'], 0, 1) - 0.35 * bp
            - 0.22 * crown - 0.14 * upper + 0.3 * I['drop'])
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


SKIN_ATTRS = ('share', 'under', 'rim', 'cup', 'pit', 'hl', 'crease', 'ring', 'lash', 'closed', 'brow', 'lip', 'mouth', 'drop')


def preview_colours(co: np.ndarray, vn) -> np.ndarray:
    from monsters.breeds import scrollopus_skin as SK
    L = SK._LAST
    if L and L.get('n') == len(co):
        I = {'co': L['co'], **{k: L[k] for k in SKIN_ATTRS}}
        return skin_paint(I, F_PAL())[0]
    A = SK.fields(co, vn)
    I = {'co': co, 'share': A['share'], 'under': A['under'], 'rim': A['sk']['rim'], 'cup': A['sk']['cup'], 'pit': A['sk']['pit'],
         'hl': A['sk']['hl'],
         'crease': A['fo']['crease'], 'ring': A['fo']['ring'], 'lash': A['ld']['lash'], 'closed': A['ld']['closed'],
         'brow': A['ld']['brow'], 'lip': A['lip'], 'mouth': A['mouth'], 'drop': A['drop']}
    return skin_paint(I, F_PAL())[0]


def F_PAL() -> dict:
    from monsters.breeds import scrollopus_ultra as R
    return R.PALETTE


# ----------------------------------------------------------------------------- the props
def gold_paint(I: dict, col: dict, n: int, metal=1.0) -> np.ndarray:
    """Polished gold without metalness (the film look clamps roughness), painted from the normal's height as a metal
    reflects its surroundings (round 3, review: flat yellow plastic): the ground's warm bounce underneath, the
    horizon's dark band just below the middle, the pale sky above it and a crisp bright edge on top. `metal` (0..1)
    softens it for the threads."""
    nz = np.clip(I['nz'], -1, 1)
    metal = np.asarray(metal, np.float64)
    rgb = np.tile(lin(col['gold']), (n, 1))
    rgb = _mix(rgb, lin(col['gold_lo']), 0.5 * smooth(-0.25, -0.85, nz))
    rgb = _mix(rgb, lin(col['gold_deep']), 0.72 * metal * np.exp(-((nz + 0.08) / 0.2) ** 2))
    rgb = _mix(rgb, lin(col['gold_hi']), 0.55 * smooth(0.3, 0.62, nz))
    rgb = _mix(rgb, lin(col['gold_edge']), 0.7 * metal * smooth(0.76, 0.93, nz))
    return rgb


def prop_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal)
    pk = np.rint(I['pk']).astype(int)
    co = I['co']
    n = len(pk)
    w2 = I['w2']
    mott = N.fbm(co, 1 / 0.02, 81, 3)
    fine = N.fbm(co, 1 / 0.004, 82, 2)
    rgb = np.zeros((n, 3))
    rough = np.full(n, 0.6)
    coat = np.zeros(n)
    # felt: the skullcap, the board, the button
    felt = (pk >= 1) & (pk <= 3)
    fc = lin(col['felt'])[None] * (0.95 + 0.06 * mott + 0.05 * fine)[:, None]
    fc = _mix(fc, lin(col['felt_dark']), 0.4 * smooth(0.2, 0.0, w2) * (pk == 1))
    fc = _mix(fc, lin(col['felt_dark']), 0.55 * smooth(0.5, 0.75, w2) * (pk == 1))     # polish: the wall under the board in shade
    rgb = np.where(felt[:, None], fc, rgb)
    rough = np.where(felt, 1.0, rough)                     # round 2: felt, no specular
    # gold: the cord, the knot, the strands, the spectacles, the seal, the holder, the book's corners
    goldm = np.isin(pk, (4, 5, 6, 7, 10, 11, 12, 13, 22, 30, 31, 42))
    gl = pk == 14
    # the threads (the cord, the knot, the strands) softer than the metal (the rims, the hinges, the holder, the corners)
    gc = gold_paint(I, col, n, metal=np.where(np.isin(pk, (4, 5, 6, 7)), 0.35, np.where(pk == 22, 0.0, 1.0)))
    # the braid: diagonal strands round the cords; the strands darker at their root, lighter at the ends
    braid = 0.5 + 0.5 * np.sin(I['u_ang'] * 2.0 + w2 * 260.0)
    gc = _mix(gc, lin(col['gold_lo']), 0.45 * smooth(0.55, 0.95, braid) * np.isin(pk, (4, 5)))
    gc = _mix(gc, lin(col['strand_root']), 0.35 * smooth(0.3, 0.0, w2) * (pk == 7))
    gc = _mix(gc, lin(col['gold_hi']), 0.3 * smooth(0.5, 1.0, w2) * (pk == 7) * (0.6 + 0.4 * I['sid']))
    gc = _mix(gc, lin(col['gold_lo']), 0.3 * (pk == 6))
    gc = _mix(gc, lin(col['slit']), 0.9 * I['slit'])
    rgb = np.where(goldm[:, None], gc, rgb)
    rough = np.where(goldm, np.where(np.isin(pk, (7, 4, 5)), 0.55, 0.3), rough)
    coat = np.where(goldm, np.where(np.isin(pk, (7, 4, 5)), 0.1, 0.6), coat)
    rgb = np.where(gl[:, None], np.tile(lin(col['glint']), (n, 1)), rgb)
    rough = np.where(gl, 0.3, rough)
    coat = np.where(gl, 0.5, coat)
    # paper: the scroll (ragged, browned at the ends, the inner turns in shade), the pages
    paper = pk == 20
    pc = lin(col['parch'])[None] * (0.93 + 0.08 * mott + 0.04 * fine)[:, None]
    pc = _mix(pc, lin(col['parch_edge']), 0.7 * smooth(0.86, 1.0, w2) + 0.6 * I['edge'] + 0.25 * smooth(0.0, -0.5, mott))
    pc = _mix(pc, lin(col['parch_in']), 0.5 * I['back'] + 0.35 * smooth(0.85, 0.4, I['turn']))
    rgb = np.where(paper[:, None], pc, rgb)
    rough = np.where(paper, 0.86, rough)
    rgb = np.where((pk == 21)[:, None], lin(col['plum'])[None] * (0.95 + 0.06 * mott)[:, None], rgb)
    rough = np.where(pk == 21, 0.75, rough)
    # the quill's shaft and vane
    sh = pk == 32
    rgb = np.where(sh[:, None], np.tile(lin(col['shaft']), (n, 1)), rgb)
    rough = np.where(sh, 0.45, rough)
    coat = np.where(sh, 0.2, coat)
    va = pk == 33
    along = I['along']
    vc = lin(col['vane'])[None] * (0.95 + 0.06 * fine)[:, None]
    vc = _mix(vc, lin(col['vane_edge']), 0.35 * smooth(0.7, 1.0, w2))
    vc = _mix(vc, lin(col['vane_tip']), 0.97 * smooth(0.58, 0.76, along + 0.08 * w2))
    vc = _mix(vc, lin(C.shade_hex(col['vane_tip'], 0.62)), 0.8 * smooth(0.86, 0.99, along + 0.05 * w2))
    vc = _mix(vc, lin(C.mix_hex(col['vane_tip'], col['vane'], 0.55)), 0.5 * smooth(0.12, 0.0, along))
    rgb = np.where(va[:, None], vc, rgb)
    rough = np.where(va, 0.7, rough)
    # the book: leather covers and spine, gold-edged; the pages
    lea = (pk == 40) | (pk == 43)
    lc = lin(col['leather'])[None] * (0.9 + 0.12 * mott + 0.05 * fine)[:, None]
    lc = _mix(lc, lin(col['leather_dark']), 0.55 * smooth(0.3, 0.0, w2) * (pk == 40) + 0.6 * (1 - I['outer']) * (pk == 40))
    lc = _mix(lc, lin(col['leather_light']), 0.3 * smooth(0.5, 1.0, w2) * I['outer'] * (pk == 40))
    lc = _mix(lc, lin(col['gold']), 0.9 * smooth(0.5, 0.8, w2) * (pk == 43))
    lc = _mix(lc, lin(col['gold']), 0.9 * I['corner'] * I['outer'] * (pk == 40))
    rgb = np.where(lea[:, None], lc, rgb)
    rough = np.where(lea, 0.62 - 0.25 * I['corner'] - 0.2 * smooth(0.5, 0.8, w2) * (pk == 43), rough)
    coat = np.where(lea, 0.15 + 0.3 * I['corner'], coat)
    pg = pk == 41
    pgc = lin(col['page'])[None] * (0.95 + 0.05 * fine)[:, None]
    pgc = _mix(pgc, lin(col['page_line']), 0.3 * smooth(0.5, 1.0, np.abs(I['side'])))
    rgb = np.where(pg[:, None], pgc, rgb)
    rough = np.where(pg, 0.85, rough)
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


PROP_ATTRS = ('pk', 'w2', 'up', 'top', 'sid', 'turn', 'back', 'along', 'outer', 'corner', 'side', 'slit', 'edge', 'loose')


def prop_inputs(ob) -> dict:
    co, vn = S.mesh_arrays(ob)
    I = {'co': co, **{k: _get(ob, k, 1.0 if k in ('turn', 'outer') else 0.0) for k in PROP_ATTRS}}
    I['nz'] = vn[:, 2]
    I['ny'] = vn[:, 1]
    I['u_ang'] = np.arctan2(vn[:, 1], vn[:, 0])
    return I


def paint_sources(body_srcs, fins, props=()) -> None:
    pal = F_PAL()
    from monsters.breeds import scrollopus_shade as SH
    for ob in body_srcs:
        co = S.attr_array(ob, 'root').astype(np.float64) if 'root' in ob.data.attributes else S.mesh_arrays(ob)[0]
        I = {'co': co, **{k: _get(ob, k) for k in SKIN_ATTRS}}
        rgb, rough = skin_paint(I, pal)
        # build 2: the ink dots matte (a studio glint on a glossy dark dot read as a grey disc)
        dm = SH.dot_mask(co)
        rough[:, 1] = rough[:, 1] * (1 - dm) + 0.62 * dm
        rough[:, 2] = rough[:, 2] * (1 - dm) + 0.08 * dm
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
    for ob in props:
        rgb, rough = prop_paint(prop_inputs(ob), pal)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)


def preview_prop_colour(name: str):
    col = colours(F_PAL())
    return {'cap': col['felt'], 'tassel': col['gold'], 'specs': col['gold'], 'scroll': col['parch'], 'quill': col['vane'],
            'book': col['leather']}.get(name, col['gold'])
