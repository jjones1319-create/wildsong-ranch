"""Moatshell's paint (Art 2.1 Ultra): per-vertex colour and roughness for the skin (hi_body) and the keep (hi_keep),
the per-pixel flecks, the Porcelain variant's blue flowers and vines, and the eyes.

Colours come from CONTENT (#C9A66B shell and skin, #E8D4A8 belly plate, #3AA6A1 flag, #9A5B3C brick details,
#2B2B2B eyes) and variants.ts (Porcelain: #F4F7FA, #FFFFFF, #2F5D8A, #2B2B2B). Derived from them (CONTENT has no hex
for these parts; 1-hero and 4-details show them): the moss (flag teal into sandstone, darkened), the wood (brick into
the eye colour), the iron (the eye colour, lifted so it reads in the grey studio), the mortar and the pits (sandstone
darkened toward brick), the brown iris (brick into the eye colour) and the off-white of the eye (the belly, lightened).
"""
from __future__ import annotations

import math

import numpy as np

from lib import bake as BK
from lib import common as C
from lib import marks as MK
from lib import surface as S
from lib import ultra as U
from lib.nodes import new_mat
from monsters.breeds import moatshell_castle as KC
from monsters.breeds import moatshell_noise as N
from monsters.breeds import moatshell_ultra as R

smooth = N.smooth
BRICK = R.BRICK_HEX
PORC = 'porcelain'


def lin(h: str) -> np.ndarray:
    return N.v3(C.lin_rgb(h))


def sat_hex(h: str, k: float, v: float = 1.0) -> str:
    """The colour with its saturation × k and its value × v (HSV): a derived colour stays on its palette hue."""
    import colorsys
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(hh, min(1.0, ss * k), min(1.0, vv * v))
    return '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in (r, g, b))


def colours(pal: dict, porcelain: bool = False) -> dict:
    body, belly, acc, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    c = {
        'skin': body, 'skin_top': C.mix_hex(body, belly, 0.3), 'skin_warm': C.mix_hex(body, BRICK, 0.22),
        'skin_groove': C.shade_hex(C.mix_hex(body, BRICK, 0.2), 0.74),       # round 2: a soft shadow, not dark grout
        'belly': belly, 'seam': C.shade_hex(C.mix_hex(belly, body, 0.45), 0.66),
        'beak': C.mix_hex(belly, body, 0.38), 'speck': C.shade_hex(C.mix_hex(body, BRICK, 0.3), 0.5),
        'nail': C.mix_hex(belly, '#FFFFFF', 0.18), 'nail_base': C.shade_hex(body, 0.55),
        'mouth': C.shade_hex(C.mix_hex(body, BRICK, 0.5), 0.36), 'brow': C.shade_hex(C.mix_hex(body, BRICK, 0.7), 0.45),
        'lash': eye,
        'stone': C.mix_hex(body, belly, 0.36), 'stone_light': C.mix_hex(body, belly, 0.6), 'stone_dark': C.shade_hex(body, 0.8),
        'mortar': C.shade_hex(C.mix_hex(body, BRICK, 0.35), 0.28), 'pit': C.shade_hex(C.mix_hex(body, BRICK, 0.35), 0.42),
        'brick': BRICK, 'brick_light': C.mix_hex(BRICK, body, 0.32), 'brick_dark': C.shade_hex(BRICK, 0.74),
        'wood': C.shade_hex(C.mix_hex(BRICK, '#2B2B2B', 0.38), 0.95), 'wood_light': C.mix_hex(BRICK, body, 0.12),
        'iron': C.mix_hex('#2B2B2B', '#6A6A70', 0.3), 'iron_light': C.mix_hex('#2B2B2B', '#B0B0B6', 0.5),
        'rope': C.mix_hex(body, belly, 0.4), 'finial': C.mix_hex(BRICK, body, 0.22),
        'flag': acc, 'flag_hem': C.mix_hex(acc, belly, 0.3), 'flag_dark': C.shade_hex(acc, 0.8),
        'slit': C.shade_hex('#2B2B2B', 0.55),
        # round 1: yellow-green moss (the flag's teal into the sandstone, saturated on that hue), not grey-green grime
        'moss': sat_hex(C.mix_hex(body, acc, 0.42), 2.3, 0.72), 'moss_tip': sat_hex(C.mix_hex(body, acc, 0.3), 2.2, 0.95),
    }
    if porcelain:
        c.update({'skin_top': C.mix_hex(body, '#FFFFFF', 0.6), 'skin_warm': body,
                  'skin_groove': C.shade_hex(C.mix_hex(body, acc, 0.1), 0.78, cool=0.01),
                  'seam': C.shade_hex(C.mix_hex(belly, acc, 0.08), 0.84), 'beak': C.mix_hex(body, belly, 0.5), 'speck': body,
                  'nail': belly, 'nail_base': C.shade_hex(body, 0.78), 'mouth': C.shade_hex(body, 0.45),
                  'brow': C.shade_hex(C.mix_hex(body, acc, 0.15), 0.62),
                  'stone': body, 'stone_light': C.mix_hex(body, '#FFFFFF', 0.7), 'stone_dark': C.shade_hex(body, 0.92, cool=0.01),
                  'mortar': C.mix_hex(body, acc, 0.42), 'pit': C.mix_hex(body, acc, 0.12), 'moss': body, 'moss_tip': body,
                  'rope': C.mix_hex(body, '#C9A66B', 0.4)})
    return c


def _mix(rgb: np.ndarray, col: np.ndarray, k) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)[:, None]
    return rgb * (1 - k) + col[None] * k


# ----------------------------------------------------------------------------- the skin
def brow_mask(co: np.ndarray) -> np.ndarray:
    """The brown brow strokes arching over each eye (1-hero, 3-faces), thicker in the middle."""
    m = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = (N.v3(v) for v in R.eye_frame(s))
        q = co - c
        xe, ye, ze = (q @ xax) / R.EYE_R, (q @ yax) / R.EYE_R, q @ look
        u = xe * s                                    # + toward the outer corner
        arc = 1.42 + 0.24 * (1.0 - np.clip((u - 0.15) / 1.25, -1, 1) ** 2) - 0.2 * smooth(0.1, -1.0, u)
        w = (0.07 + 0.06 * (1.0 - np.clip((u - 0.15) / 1.25, -1, 1) ** 2)) * (1.0 - 0.35 * smooth(-0.2, -1.0, u))
        m = np.maximum(m, np.exp(-((ye - arc) / w) ** 2) * smooth(-1.15, -0.8, u) * smooth(1.55, 1.2, u) * (ze > -0.05) * (ze < 0.06))
    return m


def lid_crease(I: dict) -> np.ndarray:
    return np.clip(I.get('crease', np.zeros(len(I['co']))), 0, 1)


def skin_paint(I: dict, pal: dict, porcelain: bool) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal, porcelain)
    co = I['co']
    n = len(co)
    sid = I['sid']
    sid2 = np.mod(sid * 7.31, 1.0)
    mott = N.fbm(co, 1 / 0.09, 61, 3)
    # round 1: a warmer, a little deeper skin, so the head separates from the lighter keep at 64 px
    # round 2: one golden tan (the blotchy per-scale tints read as spots)
    rgb = lin(col['skin'])[None] * ((0.97 if porcelain else 0.9) + 0.05 * sid + 0.03 * mott)[:, None]
    rgb = _mix(rgb, lin(col['skin_warm']), np.full(n, 0.35))
    rgb = _mix(rgb, lin(col['skin_top']), 0.14 * I['stop'] ** 6)
    rgb = _mix(rgb, lin(col['skin_groove']), (0.0 if porcelain else 0.45) * I['sgroove'])
    if porcelain:
        rgb = _mix(rgb, lin('#FFFFFF'), 0.45 * I['sgroove'])
    cream = np.clip(I['cream'], 0, 1)
    belly = lin(col['belly'])[None] * (0.97 + 0.05 * mott)[:, None]
    belly = _mix(belly, lin(col['seam']), 0.16 * I.get('bevel', 0.0 * I['seam']) + 0.06 * I['seam'])
    rgb = rgb * (1 - cream[:, None]) + belly * cream[:, None]
    rgb = _mix(rgb, lin(col['beak']), I['beak'])
    rgb = _mix(rgb, lin(col['speck']), 0.45 * I['speck'] * (0.4 + 0.6 * I['beak']) * (1 - cream))
    nb = np.exp(-(R.toe_dist(co) / 0.0022) ** 2) * (R.toe_dist(co) > -0.004)
    rgb = _mix(rgb, lin(col['nail']), I['nail'])
    rgb = _mix(rgb, lin(col['nail_base']), 0.6 * nb)
    mo = np.clip(I['mouth'] * 1.3, 0, 1)
    rgb = _mix(rgb, lin(col['mouth']), 0.88 * mo)
    rgb = _mix(rgb, lin(col['mouth']), 0.8 * I['nostril'])
    rgb = _mix(rgb, lin(col['brow']), 0.92 * brow_mask(co))
    rgb = _mix(rgb, lin(col['skin_groove']), 0.6 * lid_crease(I))
    rgb = _mix(rgb, lin(col['lash']), 0.85 * np.clip(I['lash'], 0, 1))
    rough = 0.66 - 0.06 * I['stop'] + 0.16 * I['sgroove']
    rough = rough * (1 - cream) + (0.55 + 0.25 * I['seam']) * cream
    rough = rough * (1 - I['beak']) + 0.45 * I['beak']
    rough = rough * (1 - I['nail']) + 0.36 * I['nail']
    coat = 0.04 + 0.04 * cream + 0.12 * I['beak'] + 0.3 * I['nail']
    if porcelain:
        rough = 0.12 + 0.2 * I['sgroove'] + 0.15 * I['seam'] + 0.3 * mo
        coat = 0.95 - 0.3 * I['sgroove'] - 0.5 * mo
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


# ----------------------------------------------------------------------------- the keep
def keep_paint(I: dict, pal: dict, porcelain: bool) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal, porcelain)
    ck, bid = I['ck'], I['bid']
    n = len(ck)
    co = I['co']
    mott = N.fbm(co, 1 / 0.08, 71, 3)
    stone = (ck >= 0.5) & (ck <= 3.5)
    rgb = np.zeros((n, 3))
    # sandstone: a tone per brick, a few lighter and darker, brick-red ones here and there
    s = lin(col['stone'])[None] * (0.9 + 0.2 * bid + 0.05 * mott)[:, None]
    s = _mix(s, lin(col['stone_light']), 0.45 * smooth(0.62, 1.0, bid))
    s = _mix(s, lin(col['stone_dark']), 0.4 * smooth(0.3, 0.0, bid))
    s = _mix(s, lin(col['brick_light']), 0.6 * I['red'] * (0 if porcelain else 1))
    if not porcelain:
        # round 2: a few bricks toward orange, a few toward grey (4-details panel 6)
        tint = np.mod(bid * 13.7, 1.0)
        s = _mix(s, lin(C.mix_hex(col['stone'], BRICK, 0.38)), 0.7 * (tint < 0.07) * (ck == 1))
        # (polish: wall bricks only; one whole rampart block went grey and read as a pasted-on slab)
        s = _mix(s, lin(sat_hex(col['stone'], 0.3, 0.86)), 0.75 * ((tint > 0.93) & (ck == 1)))
    s = s * np.where(ck == 3, 0.93, 1.0)[:, None]
    s = _mix(s, lin(col['stone_light']), 0.14 * I['bedge'] + 0.45 * I['chip'])
    s = _mix(s, lin(col['pit']), 0.55 * I['pit'])
    s = _mix(s, lin(col['mortar']), 0.92 * I['mortar'])
    # round 1: the shadow at the keep's foot, so it separates from the head and the rampart at 64 px
    s = s * (1.0 - 0.3 * I.get('base', np.zeros(n)))[:, None]
    if porcelain:
        # china: a fine blue line along the blocks' edges, blue glaze pooling in the joints, and the blue painting:
        # large blooms and flowing vines with leaves (moatshell_china.py; variant picture)
        line = smooth(0.35, 0.7, I['bedge']) * smooth(1.0, 0.8, I['bedge']) * (ck == 2)
        s = _mix(s, lin(pal['accent']), 0.75 * line)
        ch = I.get('china')
        if ch is not None:
            wash, ink, dark = ch
            s = _mix(s, lin(C.mix_hex(pal['accent'], '#FFFFFF', 0.42)), 0.95 * wash)
            s = _mix(s, lin(pal['accent']), 0.95 * ink)
            s = _mix(s, lin(C.shade_hex(pal['accent'], 0.6)), 0.9 * dark)
    else:
        mk = smooth(0.2, 0.55, I['moss'])
        mc = _mix(np.tile(lin(col['moss']), (n, 1)), lin(col['moss_tip']), smooth(-0.2, 0.6, N.fbm(co, 1 / 0.006, 73, 2)))
        s = s * (1 - mk[:, None]) + mc * mk[:, None]
    rgb = np.where(stone[:, None], s, rgb)
    # brick-red voussoirs
    b = lin(col['brick'])[None] * (0.88 + 0.24 * bid + 0.05 * mott)[:, None]
    b = _mix(b, lin(col['brick_light']), 0.5 * smooth(0.65, 1.0, bid) + 0.4 * I['chip'] + 0.12 * I['bedge'])
    b = _mix(b, lin(col['brick_dark']), 0.5 * smooth(0.3, 0.0, bid) + 0.4 * I['pit'])
    rgb = np.where((ck == 4)[:, None], b, rgb)
    # wood: the door's planks (grain up them), the rails and the pole; the rope bindings
    u, w2 = I['u'], I['w2']
    q = np.stack([u * 1.0, w2 * 0.12, np.zeros(n)], axis=1)
    q2 = np.stack([u * 0.12, w2, np.zeros(n)], axis=1)
    grain = np.where(I['part'] == 4, N.fbm(q, 1 / 0.006, 81, 3), N.fbm(q2, 1 / 0.006, 82, 3))
    w = _mix(np.tile(lin(col['wood']), (n, 1)), lin(col['wood_light']), smooth(-0.1, 0.7, grain) * 0.55)
    w = _mix(w, lin(col['wood_light']), 0.35 * (I['part'] != 4))
    w = _mix(w, lin(col['wood']) * 0.45, 0.8 * I['mortar'] * (I['part'] == 4))
    w = _mix(w, lin(col['rope']), I['rope'])
    rgb = np.where((ck == 5)[:, None], w, rgb)
    ir = _mix(np.tile(lin(col['iron']), (n, 1)), lin(col['iron_light']), 0.6 * I['bedge'] + 0.2 * (1 - I['pit']))
    rgb = np.where((ck == 6)[:, None], ir, rgb)
    fl = lin(col['flag'])[None] * (0.95 + 0.06 * mott)[:, None]
    fl = _mix(fl, lin(col['flag_hem']), 0.45 * I['mortar'])
    fl = _mix(fl, lin(col['flag_dark']), 0.3 * smooth(0.6, 1.0, np.abs(w2)) * (1 - I['mortar']))
    rgb = np.where((ck == 7)[:, None], fl, rgb)
    fi = _mix(np.tile(lin(col['finial']), (n, 1)), lin(col['wood_light']) * 1.3, smooth(KC.FINIAL['z'], KC.FINIAL['z'] + 0.018, co[:, 2]) * 0.5)
    rgb = np.where((ck == 8)[:, None], fi, rgb)
    # the eyelids (moatshell_lids.py): the skin's colour, a touch darker toward the fold, the dark lash line at the edge
    lv = I['w2']
    ld = lin(col['skin'])[None] * (1.0 - 0.1 * smooth(0.2, 0.9, lv))[:, None]
    ld = _mix(ld, lin(col['skin_top']), 0.35 * smooth(0.16, 0.06, lv) * smooth(0.03, 0.07, lv))
    ld = _mix(ld, lin(pal['eye']), 0.9 * smooth(0.05, 0.02, lv))
    rgb = np.where((ck == 9)[:, None], ld, rgb)
    rgb = _mix(rgb, lin(col['slit']), I['slit'])
    rough = np.select([stone, ck == 4, ck == 5, ck == 6, ck == 7, ck == 8, ck == 9],
                      [0.86 + 0.08 * I['mortar'], np.full(n, 0.78), 0.64 + 0.2 * I['rope'], np.full(n, 0.46), np.full(n, 1.0),
                       np.full(n, 0.4), np.full(n, 0.62)], 0.8)
    coat = np.select([ck == 5, ck == 6, ck == 8], [np.full(n, 0.03), np.full(n, 0.15), np.full(n, 0.25)], 0.0)
    if porcelain:
        # round 1: glazed, not chalky: a mirror-smooth glaze with a full coat (the runtime floors roughness at 0.3)
        rough = np.where(stone, 0.1 + 0.3 * I['mortar'] + 0.15 * I['pit'], rough)
        coat = np.where(stone, np.where(ck == 1, 0.55, 1.0) - 0.4 * I['mortar'], coat)   # the curved wall: a softer coat (white streaks)
        rough = np.where(ck == 9, 0.15, rough)
        coat = np.where(ck == 9, 0.9, coat)
    rough = np.where(I['slit'] > 0.5, 0.95, rough)
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


def paint_sources(body_srcs, fins, props=()) -> None:
    vid, vpal = next(iter(R.VARIANTS.items()))
    vattr = U.variant_attr(vid, R.ID)
    for ob in body_srcs:
        co = S.attr_array(ob, 'root').astype(np.float64) if 'root' in ob.data.attributes else S.mesh_arrays(ob)[0]
        I = {'co': co, **{k: _get(ob, k) for k in ('sid', 'sgroove', 'stop', 'cream', 'beak', 'nail', 'seam', 'nostril', 'lash',
                                                   'lid', 'speck', 'mouth', 'crease', 'bevel')}}
        rgb, rough = skin_paint(I, R.PALETTE, False)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        rgb_v, rough_v = skin_paint(I, vpal, True)
        S.set_colour_attr(ob, vattr, rgb_v)
        S.set_colour_attr(ob, f'rough_{PORC}', rough_v)
    for ob in props:
        co, vn = S.mesh_arrays(ob)
        I = {'co': co, **{k: _get(ob, k) for k in ('ck', 'bid', 'mortar', 'bedge', 'chip', 'pit', 'red', 'slit', 'moss', 'u', 'w2',
                                                   'rope', 'part', 'base')}}
        rgb, rough = keep_paint(I, R.PALETTE, False)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        from monsters.breeds import moatshell_china as CH
        I['china'] = CH.paint(co, vn, I['ck'])
        rgb_v, rough_v = keep_paint(I, vpal, True)
        S.set_colour_attr(ob, vattr, rgb_v)
        S.set_colour_attr(ob, f'rough_{PORC}', rough_v)


# ----------------------------------------------------------------------------- the Porcelain flowers (per pixel)
def _wall_point(which: str, th: float, z: float):
    r = float(KC.wall_radius(which, z))
    d = KC.dirv(th)
    p = (float(d[0] * r), float(d[1] * r), float(z))
    k = (KC.WALL_RT - KC.WALL_RB) / (KC.WALL_ZTOP - KC.WALL_Z0) if which == 'wall' else (KC.TOWER_RT - KC.TOWER_RB) / (KC.TOWER_ZTOP - KC.TOWER_Z0)
    nrm = np.array([d[0], d[1], -k])
    nrm = nrm / np.linalg.norm(nrm)
    return p, tuple(map(float, nrm))


def _clear_of_openings(which: str, th: float, z: float, margin: float) -> bool:
    r = float(KC.wall_radius(which, z))
    for wh, thd, zc in KC.WINDOWS:
        if wh == which and abs(float(KC.ang_wrap(th - math.radians(thd)))) * r < margin + 0.03 and abs(z - zc) < margin + 0.05:
            return False
    if which == 'wall':
        dz = KC.door_z0()
        if abs(float(KC.ang_wrap(th - math.radians(KC.DOOR['th'])))) * r < margin + 0.075 and z < dz + 0.2:
            return False
    return True


def make_marks():
    """Porcelain's blue flowers, vines and leaves on the keep (variant picture): positions on the walls, the tower and the
    skirt, kept clear of the slits and the door. JSON-able lists; prop_material draws them for the porcelain pass."""
    flowers, vines, leaves = [], [], []
    k = 0
    for i in range(40):
        if len(flowers) >= 15:
            break
        th = (i * 0.618034 % 1.0) * KC.TAU
        zt = float(KC.skirt_zt(th))
        z = zt + 0.05 + (KC.WALL_ZTOP - 0.035 - zt - 0.05) * float(N.hash1(i, 601)[0])
        if z > KC.WALL_ZTOP - 0.03 or not _clear_of_openings('wall', th, z, 0.03):
            continue
        p, nrm = _wall_point('wall', th, z)
        rad = 0.025 + 0.011 * float(N.hash1(i, 602)[0])
        flowers.append([p, nrm, rad, float(N.hash1(i, 603)[0]) * 6.283])
        if k % 3 != 2:
            # a vine: a gentle S from the flower along the wall, with leaves
            dirn = 1.0 if N.hash1(i, 604)[0] > 0.5 else -1.0
            pts = []
            for j in range(7):
                t = j / 6.0
                thj = th + dirn * (0.03 + 0.42 * t) / float(KC.wall_radius('wall', z))
                zj = z + 0.028 * math.sin(t * 2 * math.pi * 1.1 + i) - 0.02 * t
                zj = min(max(zj, float(KC.skirt_zt(thj)) + 0.02), KC.WALL_ZTOP - 0.015)
                pts.append(_wall_point('wall', thj, zj)[0])
            vines.append(pts)
            for j in (1, 3, 5):
                a, b = np.array(pts[j]), np.array(pts[j + 1])
                mid = 0.5 * (a + b)
                side = np.cross(b - a, np.array(_wall_point('wall', th, z)[1]))
                side = side / max(np.linalg.norm(side), 1e-9) * (0.009 if j % 4 == 1 else -0.009)
                leaves.append([tuple(map(float, mid + side)), 0.0085])
        k += 1
    for i in range(14):
        th = (i * 0.618034 + 0.31) % 1.0 * KC.TAU
        z = 0.7 + 0.11 * float(N.hash1(i, 611)[0])
        if not _clear_of_openings('tower', th, z, 0.02):
            continue
        p, nrm = _wall_point('tower', th, z)
        flowers.append([p, nrm, 0.017 + 0.006 * float(N.hash1(i, 612)[0]), float(N.hash1(i, 613)[0]) * 6.283])
        if len(flowers) >= 20:
            break
    for j, thc in enumerate(KC.skirt_block_angles()):
        if j % 2:
            continue
        p = KC.skirt_outer(thc, 0.5)
        nr, nz = KC.skirt_normal(thc)
        d = KC.dirv(thc)
        nrm = (float(d[0] * nr), float(d[1] * nr), float(nz))
        flowers.append([tuple(map(float, p)), nrm, 0.03, float(N.hash1(j, 621)[0]) * 6.283])
    return {'flowers': flowers, 'vines': vines, 'leaves': leaves}


def _flower_masks(nb, pos, marks):
    petals, inner, centres, vine = [], [], [], []
    for p, nrm, rad, rot in marks.get('flowers', []):
        n = np.array(nrm)
        t = np.cross(n, np.array([0.0, 0.0, 1.0]))
        if np.linalg.norm(t) < 1e-6:
            t = np.array([1.0, 0.0, 0.0])
        t = t / np.linalg.norm(t)
        b = np.cross(n, t)
        tan = tuple(map(float, t * math.cos(rot) + b * math.sin(rot)))
        petals.append(MK.star(nb, pos, tuple(p), tuple(nrm), tan, rad, inner=0.42, points=5, sharp=0.9, soft=0.14, depth=0.012))
        inner.append(MK.star(nb, pos, tuple(p), tuple(nrm), tan, rad * 0.55, inner=0.5, points=5, sharp=1.2, soft=0.2, depth=0.012))
        centres.append(MK.dot(nb, pos, tuple(p), rad * 0.2, soft=0.3))
    for pts in marks.get('vines', []):
        for a, b in zip(pts[:-1], pts[1:]):
            vine.append(MK.line(nb, pos, tuple(a), tuple(b), 0.0032, soft=0.35))
    for c, r in marks.get('leaves', []):
        vine.append(MK.dot(nb, pos, tuple(c), (r, r, r), soft=0.25))
    return MK.union(nb, petals), MK.union(nb, inner), MK.union(nb, centres), MK.union(nb, vine)


def prop_material(name: str, attr: str, pal: dict, marks):
    """The keep's colour pass: its paint plus dark and pale flecks in the sandstone (4-details panel 6); for Porcelain,
    the blue flowers, vines and leaves over the china (only on the stone, never the voussoirs, the door or the flag)."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    ck = nb.attribute('ck').outputs['Fac']
    stone = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(ck, 3.6, 3.4), nb.smooth(ck, 0.4, 0.6)),
                    nb.math('SUBTRACT', 1.0, nb.attribute('slit').outputs['Fac']))
    porcelain = attr != 'paint'
    col = colours(pal, porcelain)
    if not porcelain:
        moss = nb.smooth(nb.attribute('moss').outputs['Fac'], 0.5, 0.25)
        warp = nb.vmath('ADD', pos, nb.vmath('SCALE', nb.comb(nb.noise(pos, 50.0, 1.0, 0.5), nb.noise(nb.vmath('ADD', pos, nb.comb(1.3, 2.1, 0.7)), 50.0, 1.0, 0.5), 0.0), scale=0.003))
        dark = nb.math('MULTIPLY', nb.smooth(nb.voronoi(warp, 210.0, 'F1'), 0.2, 0.12), nb.math('MULTIPLY', stone, moss))
        dark = nb.math('MULTIPLY', dark, nb.smooth(nb.noise(nb.vmath('ADD', pos, nb.comb(4.1, 0.2, 2.2)), 9.0, 1.0, 0.5), 0.25, 0.5))
        c = nb.mix(nb.math('MULTIPLY', dark, 0.8), c, nb.rgb(C.lin(col['pit'])))
        # round 2: bigger dark speckles, sparser
        big = nb.math('MULTIPLY', nb.smooth(nb.voronoi(nb.vmath('ADD', warp, nb.comb(-2.7, 1.9, 3.3)), 95.0, 'F1'), 0.13, 0.07), nb.math('MULTIPLY', stone, moss))
        big = nb.math('MULTIPLY', big, nb.smooth(nb.noise(nb.vmath('ADD', pos, nb.comb(1.1, 7.2, 0.6)), 14.0, 1.0, 0.5), 0.45, 0.62))
        c = nb.mix(nb.math('MULTIPLY', big, 0.7), c, nb.rgb(C.lin(C.shade_hex(col['pit'], 0.8))))
        pale = nb.math('MULTIPLY', nb.smooth(nb.voronoi(nb.vmath('ADD', warp, nb.comb(3.3, 5.5, 1.1)), 300.0, 'F1'), 0.15, 0.09), nb.math('MULTIPLY', stone, moss))
        c = nb.mix(nb.math('MULTIPLY', pale, 0.4), c, nb.rgb(C.lin(col['stone_light'])))
    elif marks:
        mk = marks
        pet, inn, cen, vine = _flower_masks(nb, pos, mk)
        blue, deep, pale = C.lin(pal['accent']), C.lin(C.shade_hex(pal['accent'], 0.62)), C.lin(C.mix_hex(pal['accent'], '#FFFFFF', 0.55))
        if vine is not None:
            c = nb.mix(nb.math('MULTIPLY', vine, nb.math('MULTIPLY', stone, 0.9)), c, nb.rgb(blue))
        if pet is not None:
            c = nb.mix(nb.math('MULTIPLY', pet, stone), c, nb.rgb(blue))
            c = nb.mix(nb.math('MULTIPLY', inn, stone), c, nb.rgb(deep))
            c = nb.mix(nb.math('MULTIPLY', cen, stone), c, nb.rgb(pale))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def body_material(name: str, attr: str, pal: dict, marks):
    """The skin's colour pass: its paint plus sparse dark specks on the skin and the beak (1-hero, 4-details)."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    if attr == 'paint':
        pos = nb.coords().outputs['Object']
        cream = nb.attribute('cream').outputs['Fac']
        keep = nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', cream, 0.8))
        sp = nb.math('MULTIPLY', nb.smooth(nb.voronoi(pos, 150.0, 'F1'), 0.16, 0.1), keep)
        sp = nb.math('MULTIPLY', sp, nb.smooth(nb.noise(nb.vmath('ADD', pos, nb.comb(0.7, 3.1, 2.3)), 12.0, 1.0, 0.5), 0.4, 0.62))
        c = nb.mix(nb.math('MULTIPLY', sp, 0.5), c, nb.rgb(C.lin(colours(pal)['speck'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- eyes
def eye_material(name: str, rough_pass: bool, pal: dict):
    """Sleepy wise eyes (1-hero, 3-faces neutral, 4-details panel 2): a big warm-brown iris round a dark pupil on an
    off-white eye, two catchlights, and the heavy upper lid in the skin's colour across the top third (a dark lash line
    at its edge, a soft shadow under it); a thin lower lid. The rough pass keeps the lids matte."""
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    # the lid's edge: moatshell_lids.edge (drooping at the outer corner)
    rxs = nb.math('MULTIPLY', rx, side)
    inner = nb.smooth(nb.math('MULTIPLY', rxs, -1.0), 0.0, 0.9)
    outer = nb.smooth(rxs, 0.15, 1.0)
    edge = nb.math('ADD', nb.math('ADD', 0.30, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', rx, rx)), 0.17)),
                   nb.math('ADD', nb.math('MULTIPLY', outer, -0.22), nb.math('MULTIPLY', inner, 0.03)))
    upper = nb.smooth(nb.math('SUBTRACT', ry, edge), -0.015, 0.015)
    low_edge = nb.math('ADD', -0.86, nb.math('MULTIPLY', nb.math('MULTIPLY', rx, rx), 0.16))
    lower = nb.smooth(nb.math('SUBTRACT', low_edge, ry), -0.02, 0.02)
    lid = nb.math('MAXIMUM', upper, lower)
    # round 1: a big brown iris (about 70% of the opening) set a little low under the lid, a big pupil
    ix = nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.05))
    iy = nb.math('ADD', ry, 0.1)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.8), nb.math('DIVIDE', iy, 0.8), 0.0))
    if rough_pass:
        pupil = nb.smooth(ri, 0.55, 0.45)
        rr = nb.math('ADD', nb.math('ADD', 0.3, nb.math('MULTIPLY', pupil, 0.08)), nb.math('MULTIPLY', lid, 0.42))
        cc = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, lid), 0.6)
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, rr, cc), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    eye = pal['eye']
    iris = C.mix_hex(eye, BRICK, 0.62)
    white = C.mix_hex(pal['belly'], '#FFFFFF', 0.72) if pal is R.PALETTE else C.mix_hex(R.PALETTE['belly'], '#FFFFFF', 0.72)
    c = nb.ramp(ri, [(0.0, C.lin(C.shade_hex(eye, 0.55))), (0.5, C.lin(C.shade_hex(eye, 0.55))), (0.56, C.lin(C.shade_hex(iris, 0.7))),
                     (0.62, C.lin(iris)), (0.86, C.lin(C.mix_hex(iris, '#D9A066', 0.28))), (0.95, C.lin(C.shade_hex(iris, 0.6))),
                     (1.0, C.lin(eye)), (1.04, C.lin(white)), (2.0, C.lin(white))])
    ang = nb.math('ARCTAN2', iy, ix)
    streak = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 23.0)), 0.5), 0.5),
                     nb.math('MULTIPLY', nb.smooth(ri, 0.52, 0.62), nb.smooth(ri, 0.95, 0.85)))
    c = nb.mix(nb.math('MULTIPLY', streak, 0.18), c, nb.rgb(C.lin(C.mix_hex(iris, '#E8B070', 0.4))))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.22), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.05), 1.1), 0.0)), 0.22, 0.16)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.24), nb.math('ADD', ry, 0.36), 0.0)), 0.08, 0.055)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    sh = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ry, edge), -0.35, 0.0), 0.3)
    c = nb.mix(sh, c, nb.rgb(C.lin('#3A2A20')), blend='MULTIPLY')
    # the lid: the skin's colour, a touch darker up toward the fold, lighter just above the lash line
    # under the lid prop (moatshell_lids.py) the eyeball's top lies in the lid's shadow: dark, so no sliver of a look's
    # skin colour shows on another look (the game keeps the base atlas on the eyes for Porcelain)
    # round 2: the skin's tone (a broken lid in the simplified Lite copy showed this as black patches)
    c = nb.mix(upper, c, nb.rgb(C.lin(C.shade_hex(R.PALETTE['body'], 0.78))))
    c = nb.mix(lower, c, nb.rgb(C.lin(C.mix_hex(pal['body'], pal['belly'], 0.4))))
    d = nb.math('SUBTRACT', ry, edge)
    lash = nb.math('MULTIPLY', nb.smooth(d, -0.07, -0.015), nb.smooth(d, 0.07, 0.02))
    c = nb.mix(lash, c, nb.rgb(C.lin(eye)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the shape preview
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import moatshell_skin as SK
    L = SK._LAST
    if L and L.get('n') == len(co):
        I = {'co': L['base'], **{k: L[k] for k in ('sid', 'sgroove', 'stop', 'cream', 'beak', 'nail', 'seam', 'nostril', 'lash', 'lid',
                                                   'speck', 'mouth', 'crease')}}
        return skin_paint(I, R.PALETTE, False)[0]
    z = R.zones(co, vn)
    return np.where(z['belly'][:, None], lin(R.PALETTE['belly'])[None], lin(R.PALETTE['body'])[None])
