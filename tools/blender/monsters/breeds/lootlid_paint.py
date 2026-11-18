"""Lootlid's paint (Art 2.1 Ultra): per-vertex colour and roughness for the wood (hi_body) and every prop (the gold, the
coins, the tongue, the lining), the per-pixel grain and scratches, and the eyes.

Colours come from CONTENT (wood #9C6B3F, lighter wood #C99A6B, gold #F2C94C, tongue #E86A7C, eyes #2B1B10) and
variants.ts (Gilded: polished gold #E0B030, lighter #F7DE8A, the trim dark bronze #8A5A12, eyes #3A2A10; the tongue
stays pink, the coins gold: the variant picture). Derived from them (CONTENT has no hex for these parts; the pictures
show them): the grain lines and the seams (the wood into the eye colour), the hollows' dark, the eye's cream and its
warm-brown iris (the lighter wood into the eye colour), the mouth lining's dark brown. The film keeps roughness at 0.3
or more and caps the coat, so the gold and the wet tongue carry painted highlights (edges, rivet tops, the tongue's
wet streaks), and the gilded wood its polish.
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.nodes import new_mat
from monsters.breeds import lootlid_noise as N

smooth = N.smooth


def lin(h: str) -> np.ndarray:
    return S.v3(C.lin_rgb(h))


def _mix(rgb: np.ndarray, col, k) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    k = k[:, None] if k.ndim == 1 else k
    return rgb * (1 - k) + np.asarray(col)[None] * k


def colours(pal: dict, gilded: bool) -> dict:
    wood, light, eye = pal['body'], pal['belly'], pal['eye']
    if not gilded:
        return {'wood': wood, 'wood_red': C.mix_hex(wood, '#A0502E', 0.35), 'light': light,
                'grain': C.shade_hex(C.mix_hex(wood, eye, 0.42), 0.82), 'seam': C.shade_hex(C.mix_hex(eye, wood, 0.25), 0.8),
                'knot': C.shade_hex(C.mix_hex(wood, eye, 0.5), 0.85), 'heart': C.shade_hex(eye, 0.8),
                'edge': C.mix_hex(wood, light, 0.55), 'nick': C.mix_hex(light, '#E8C49A', 0.3),
                'inside': C.shade_hex(C.mix_hex(wood, eye, 0.3), 0.55), 'under': C.shade_hex(wood, 0.74),
                'brow': C.shade_hex(C.mix_hex(eye, wood, 0.3), 1.05), 'lid': C.mix_hex(wood, light, 0.18), 'lash': eye,
                'lip': C.shade_hex(C.mix_hex(wood, eye, 0.4), 0.72), 'sole': C.mix_hex(wood, light, 0.35)}
    gold, pale, bronze = pal['body'], pal['belly'], pal['accent']
    return {'wood': gold, 'wood_red': C.mix_hex(gold, '#E8962A', 0.3), 'light': pale,
            'grain': C.mix_hex(gold, '#B8640A', 0.5), 'seam': '#6A3004',
            'knot': C.mix_hex(gold, '#B8640A', 0.55), 'heart': '#7A3608',
            'edge': C.mix_hex(pale, '#FFF6D8', 0.3), 'nick': pale,
            'inside': C.shade_hex(C.mix_hex(bronze, eye, 0.3), 0.6), 'under': C.mix_hex(gold, bronze, 0.3),
            'brow': C.mix_hex(bronze, eye, 0.45), 'lid': C.mix_hex(gold, pale, 0.25), 'lash': eye,
            'lip': C.mix_hex(gold, bronze, 0.6), 'sole': C.mix_hex(gold, pale, 0.3)}


def env(rgb: np.ndarray, nz: np.ndarray, lo: float, hi: float, warm_hex: str, warm: float) -> np.ndarray:
    """A metal's painted reflection: faces turned up lighter, faces turned down darker and warmer (the film floors
    roughness at 0.3 and caps the coat, so a real reflection stays faint)."""
    t = smooth(-0.6, 0.9, nz)
    out = rgb * (lo + (hi - lo) * t)[:, None]
    return np.clip(_mix(out, lin(warm_hex) * 0.8, warm * (1 - t) ** 2), 0, 1)


# ----------------------------------------------------------------------------- the wood
def wood_paint(I: dict, pal: dict, gilded: bool) -> tuple[np.ndarray, np.ndarray]:
    col = colours(pal, gilded)
    co, reg = I['co'], np.round(I['region']).astype(int)
    n = len(co)
    pid = I['pid']
    mott = N.fbm(co, 1 / 0.07, 81, 3)
    # a tone per board, a few redder, a few paler (4-details panel 6)
    rgb = lin(col['wood'])[None] * ((0.97 + 0.04 * pid + 0.02 * mott) if gilded else (0.92 + 0.14 * pid + 0.05 * mott))[:, None]
    rgb = _mix(rgb, lin(col['wood_red']), 0.45 * smooth(0.55, 0.85, np.mod(pid * 7.3, 1.0)))
    rgb = _mix(rgb, lin(col['light']), 0.15 * smooth(0.7, 1.0, np.mod(pid * 3.1, 1.0)) + 0.12 * I['crown'] ** 3 * (0.5 + 0.5 * mott))
    # streaks of lighter wood along the grain, the grain lines, the knots
    gco = I['gco']
    streak = N.fbm(np.stack([gco[:, 0] * 0.12, gco[:, 1], gco[:, 2] * 5], axis=1), 1 / 0.02, 82, 2)
    g_k = 0.12 if gilded else 1.25              # the polished gold keeps its boards, barely any grain; round 3: the wood's grain deeper
    rgb = _mix(rgb, lin(col['light']), 0.2 * g_k * smooth(0.25, 0.7, streak))
    rgb = _mix(rgb, lin(col['grain']), 0.66 * g_k * I['grain'])
    kn = np.clip(I['knot'], 0, 1.5)
    rgb = _mix(rgb, lin(col['knot']), (0.4 if gilded else 0.8) * np.clip(kn, 0, 1))
    # polish pass: a dark-brown heart, not a black hole
    rgb = _mix(rgb, lin(C.mix_hex(col['knot'], col['heart'], 0.45)), 0.85 * smooth(1.05, 1.45, kn))
    # wear: worn corners and crowns lighter, nicks showing fresh wood, cracks and seams dark
    rgb = _mix(rgb, lin(col['edge']), 0.55 * I['edge'])
    rgb = _mix(rgb, lin(col['nick']), 0.75 * smooth(0.15, 0.6, I['nick']))
    rgb = _mix(rgb, lin(col['seam']), (0.75 if gilded else 0.5) * smooth(0.25, 0.85, I['seam']))
    rgb = _mix(rgb, lin(col['seam']), 0.72 * smooth(0.2, 0.8, I['crack']))
    # the parts
    # the wood under the gold (the rim band's strip, and anything inside a band, strap, plate or hinge of the high
    # source): the band's own mean tone, so where the Lite's simplified bands open a hole it shows gold, not wood
    under_band = ((reg == 0) & (co[:, 2] > 0.416)) | (I.get('under', np.zeros(n)) > 0.5)
    band = C.mix_hex(pal['accent'], '#2A1404', 0.3) if gilded else '#B08A30'
    rgb = np.where(under_band[:, None], lin(band)[None] * np.ones((n, 1)), rgb)
    rgb = np.where((reg == 7)[:, None], _mix(rgb, lin(col['under']), 0.5), rgb)
    ins = (reg == 2)
    rgb = np.where(ins[:, None], _mix(rgb, lin(col['inside']), 0.6), rgb)
    sole = reg == 8
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * I['ldist'] / 0.0075)
    s_rgb = _mix(np.tile(lin(col['sole']), (n, 1)), lin(col['grain']), 0.55 * smooth(0.6, 0.95, rings))
    rgb = np.where(sole[:, None], s_rgb, rgb)
    lid = reg == 4
    rgb = np.where(lid[:, None], _mix(rgb, lin(col['lid']), 0.6), rgb)
    rgb = _mix(rgb, lin(col['lash']), 0.95 * smooth(0.25, 0.7, I['lash']))
    rgb = _mix(rgb, lin(col['lip']), 0.7 * I['lip'] * (reg == 5))
    rgb = _mix(rgb, lin(col['brow']), 0.95 * smooth(0.2, 0.75, I['brow']))
    if gilded:
        # polished gold: a painted reflection (the sky above, the floor below), the crowns catching it
        # round 3: polished-gold shading (deep amber below, hot highlights above), not pale lacquered pine
        rgb = env(rgb, I['vn'][:, 2], 0.36, 1.42, '#8A4204', 0.75)
        rgb = _mix(rgb, lin(pal['belly']), 0.2 * I['crown'] ** 4 * smooth(0.0, 0.8, I['vn'][:, 2]) * (reg != 2))
        rgb = _mix(rgb, lin('#FFF8E4'), 0.6 * I['crown'] ** 8 * smooth(0.3, 0.95, I['vn'][:, 2]) * (reg != 2))
        rgb = _mix(rgb, lin('#FFF4D0'), 0.55 * I['edge'] * smooth(-0.2, 0.6, I['vn'][:, 2]) * (reg != 2))
    if not gilded:
        rough = 0.74 - 0.08 * I['crown'] + 0.1 * I['grain'] + 0.12 * smooth(0.2, 0.7, I['seam'])
        rough = np.where(ins, 0.9, rough)
        rough = np.where(I['brow'] > 0.5, 0.55, rough)
        coat = 0.02 + 0.04 * I['edge'] + 0.06 * (I['brow'] > 0.5)
    else:
        rough = 0.24 + 0.04 * I['grain'] + 0.2 * smooth(0.2, 0.7, I['seam']) + 0.15 * I['crack']
        rough = np.where(ins, 0.6, rough)
        coat = 0.5 - 0.3 * smooth(0.2, 0.7, I['seam'])
    rough = np.where(under_band, 0.32, rough)
    coat = np.where(under_band, 0.45, coat)
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


def fine_grain_mask(I: dict) -> np.ndarray:
    """How much of the per-pixel grain (body_material) each vertex takes: the boards, the posts, the hollows."""
    reg = np.round(I['region']).astype(int)
    return np.isin(reg, (0, 1, 2, 3, 5, 7)).astype(np.float64) * (1 - smooth(0.2, 0.6, I['brow']))


# ----------------------------------------------------------------------------- the props
def rivet_ring(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Each point's distance to the nearest rivet's centre on the high source, and that rivet's radius (lootlid_trim.RIVETS)."""
    from mathutils import kdtree
    from monsters.breeds import lootlid_trim as T
    if not T.RIVETS:
        return np.full(len(co), 9.0), np.full(len(co), 0.01)
    kd = kdtree.KDTree(len(T.RIVETS))
    for i, (c, _r) in enumerate(T.RIVETS):
        kd.insert(c, i)
    kd.balance()
    d = np.empty(len(co))
    rr = np.empty(len(co))
    for i, p in enumerate(co):
        _c, j, dist = kd.find(p)
        d[i] = dist
        rr[i] = T.RIVETS[j][1]
    return d, rr


def metal(I: dict, gold_hex: str, deep_hex: str, hot_hex: str, mott: np.ndarray, ring: tuple, warm_hex: str = '#A84A0A') -> np.ndarray:
    """Hammered metal painted with its light (round 1: it read as paint): warm streaks, a reflection (up lit, down dark),
    dents dark with bright rims, bright bevel shoulders over a deep edge, dark rings round the rivets, bright rivet tops."""
    nz = I['vn'][:, 2]
    rgb = lin(gold_hex)[None] * (0.88 + 0.06 * mott)[:, None]
    rgb = _mix(rgb, lin(C.mix_hex(gold_hex, warm_hex, 0.6)), 0.3 * smooth(0.2, 0.8, -mott))
    rgb = env(rgb, nz, 0.48, 1.2, C.mix_hex(gold_hex, deep_hex, 0.6), 0.7)
    ham = I['ham']
    top = I['top'] > 0.5
    rgb = _mix(rgb, lin(deep_hex), 0.65 * smooth(-0.0002, -0.001, ham) * top)
    rgb = _mix(rgb, lin(hot_hex), 0.6 * smooth(0.00004, 0.00024, ham) * top * smooth(-0.2, 0.6, nz))
    bev = I['bev']
    rgb = _mix(rgb, lin(hot_hex), 0.85 * smooth(0.74, 0.82, bev) * smooth(0.9, 0.84, bev) * top * (I['riv'] < 0.5) * smooth(0.35, 0.75, nz))
    rgb = _mix(rgb, lin(deep_hex), 0.4 * smooth(0.95, 1.0, bev) * top * (I['riv'] < 0.5))
    d, rr = ring
    near = smooth(rr + 0.006, rr + 0.0005, d) * smooth(rr - 0.003, rr + 0.0005, d) * (I['riv'] < 0.5)
    rgb = _mix(rgb, lin(deep_hex), 0.85 * near)
    riv = I['riv'] > 0.5
    rgb = _mix(rgb, lin(hot_hex), 0.85 * riv * smooth(0.9 * rr, 0.35 * rr, d) * smooth(-0.3, 0.7, nz))
    rgb = _mix(rgb, lin(deep_hex), 0.55 * riv * smooth(0.8 * rr, 1.0 * rr, d))
    rgb = _mix(rgb, lin(deep_hex), 0.7 * (~top))
    return rgb


def prop_paint(I: dict, pal: dict, gilded: bool) -> tuple[np.ndarray, np.ndarray]:
    from monsters.breeds import lootlid_hoard as H
    from monsters.breeds import lootlid_trim as T
    co = I['co']
    n = len(co)
    pk = np.round(I['pk']).astype(int)
    mott = N.fbm(co, 1 / 0.012, 91, 3)
    trim = pk <= T.PK_HINGE_LID
    if gilded:
        # Gilded: shiny dark bronze (#8A5A12) with bright bronze highlights
        rgb = metal(I, pal['accent'], '#2A1404', '#F0C878', mott * 0.4, I['ring'], warm_hex='#6A3A08')
    else:
        rgb = metal(I, C.mix_hex(pal['accent'], '#E8A030', 0.14), '#572601', '#FFF8EC', mott, I['ring'])
    rgb = _mix(rgb, lin('#120A05'), 0.97 * smooth(0.25, 0.8, I['emb']) * (pk == T.PK_PLATE))
    rough = 0.3 + 0.12 * smooth(-0.0003, -0.0011, I['ham'])
    coat = np.full(n, 0.5)
    hole = (pk == T.PK_PLATE) & (I['emb'] > 0.25)
    rough = np.where(hole, 0.9, rough)
    coat = np.where(hole, 0.0, coat)           # polish pass: no coat in the keyhole (its floor caught the sky: a pale chip)
    # polish pass: the flat gold lip over the box's rim (its wall top, 4 cm wide) caught the sky at a grazing view as a
    # cream-white band round the coins: a duller, darker, barely coated inner lip. The shut lid's gold lip lies 2 mm
    # over it, so each bakes the other: the lid lip's underside gets the same paint
    rimtop = (((pk == T.PK_BOX) & (co[:, 2] > 0.4855) & (I['vn'][:, 2] > 0.6))
              | ((pk == T.PK_LID) & (co[:, 2] < 0.4935) & (I['vn'][:, 2] < -0.6)))
    rgb = np.where(rimtop[:, None], rgb * 0.78, rgb)
    rough = np.where(rimtop, 0.46, rough)
    coat = np.where(rimtop, 0.05, coat)
    out = np.where(trim[:, None], rgb, 0.0)
    # the coins and the heap: always gold (the variant picture keeps them), a tone per coin, bright rims and emblems,
    # a hot glint on some (it also glows: GLOW)
    # polish pass: warm #F2C94C (they read dull khaki), little coat (a grey sky sheen washed them out)
    c = lin('#F2C94C')[None] * (0.94 + 0.12 * I['coin'] + 0.05 * mott)[:, None]
    c = _mix(c, lin('#F0A030'), 0.28 * smooth(0.6, 1.0, np.mod(I['coin'] * 5.7, 1.0)))
    c = _mix(c, lin('#FFE07A'), 0.3 * smooth(0.4, 0.9, I['bev']) + 0.22 * I['emb'])
    c = env(c, I['vn'][:, 2], 0.62, 1.0, '#A05A08', 0.55)
    c = _mix(c, lin('#FFF0C0'), 0.55 * I['glow'])
    # the bottom layer (seen only between the game's coins, through the bake) and the heap: deep amber in shadow, matte
    deep = (pk == H.PK_COIN) & (I['deep'] > 0.5)
    c = np.where(deep[:, None], _mix(c * 0.3, lin('#5A3008'), 0.35), c)
    heap = _mix(np.tile(lin('#2E1A06'), (n, 1)), lin('#5A3A0C'), 0.3 + 0.25 * mott)
    c = np.where((pk == H.PK_HEAP)[:, None], heap, c)
    coinish = np.isin(pk, (H.PK_COIN, H.PK_HEAP))
    out = np.where(coinish[:, None], c, out)
    low = deep | (pk == H.PK_HEAP)
    rough = np.where(coinish, np.where(low, 0.85, 0.4), rough)
    coat = np.where(coinish, np.where(low, 0.0, 0.06), coat)
    # the tongue: pink, darker in its groove, underneath and at the root, wet streaks and a bright wet rim on top
    tg_hex = pal.get('tongue', '#E86A7C')
    up = I['bev']
    t = lin(C.mix_hex(tg_hex, '#F2506A', 0.25))[None] * (0.97 + 0.05 * mott)[:, None]
    t = _mix(t, lin(C.shade_hex(tg_hex, 0.82)), 0.25 * smooth(0.2, 0.0, up) + 0.6 * smooth(0.12, 0.0, I['tg']))
    wet = smooth(0.0, 0.6, N.fbm(co, 1 / 0.018, 92, 2) + 0.35)
    t = _mix(t, lin('#F7A0AE'), 0.35 * smooth(0.45, 0.75, up) * smooth(0.97, 0.84, up) * wet)
    t = _mix(t, lin('#FFD8DE'), 0.3 * smooth(0.6, 0.7, up) * smooth(0.8, 0.7, up) * smooth(0.55, 0.9, wet))
    t = _mix(t, lin(C.shade_hex(C.mix_hex(tg_hex, '#A03048', 0.35), 0.85)), 0.5 * smooth(0.985, 1.0, up))
    tm = pk == H.PK_TONGUE
    out = np.where(tm[:, None], t, out)
    rough = np.where(tm, 0.44, rough)
    coat = np.where(tm, 0.35, coat)
    # the cheeks: plain dark wood (round 1: no flesh)
    lm = pk == H.PK_LINING
    out = np.where(lm[:, None], lin(C.mix_hex(colours(pal, gilded)['inside'], pal['body'], 0.45))[None] * (1.0 + 0.04 * mott)[:, None], out)
    rough = np.where(lm, 0.9, rough)
    coat = np.where(lm, 0.0, coat)
    return np.clip(out, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


def wood_inputs(ob) -> dict:
    co = S.attr_array(ob, 'root').astype(np.float64) if 'root' in ob.data.attributes else S.mesh_arrays(ob)[0]
    I = {'co': co, **{k: _get(ob, k) for k in ('region', 'seam', 'crown', 'pid', 'grain', 'knot', 'nick', 'crack', 'edge', 'lash',
                                              'lip', 'brow', 'sole', 'ldist')}}
    I['gco'] = S.attr_array(ob, 'gco').astype(np.float64) if 'gco' in ob.data.attributes else np.zeros((len(co), 3))
    I['vn'] = S.mesh_arrays(ob)[1]
    return I


def under_trim(co: np.ndarray, props) -> np.ndarray:
    """Polish pass: 1 where a body point lies inside a band, strap, plate or hinge of the high source (the nearest
    gold surface within 1.2 cm faces away from it), else 0."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from monsters.breeds import lootlid_trim as T
    verts, polys = [], []
    for ob in props:
        if 'pk' not in ob.data.attributes or 'region' in ob.data.attributes:
            continue
        pk = np.round(S.attr_array(ob, 'pk')).astype(int)
        gold = np.isin(pk, (T.PK_BOX, T.PK_LID, T.PK_PLATE, T.PK_HINGE_BOX, T.PK_HINGE_LID))
        if not gold.any():
            continue
        vco, _vn = S.mesh_arrays(ob)
        base = len(verts)
        verts += [tuple(v) for v in vco]
        for poly in ob.data.polygons:
            vs = poly.vertices
            if gold[vs[0]]:
                polys.append(tuple(base + i for i in vs))
    out = np.zeros(len(co))
    if not polys:
        return out
    tree = BVHTree.FromPolygons(verts, polys)
    for i, p in enumerate(co):
        hit = tree.find_nearest(Vector(p), 0.012)
        if hit[0] is not None and (Vector(p) - hit[0]).dot(hit[1]) < 0.0:
            out[i] = 1.0
    C.log(f'lootlid paint: {int(out.sum())} body points under the gold')
    return out


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import lootlid_ultra as R
    vid, vpal = next(iter(R.VARIANTS.items()))
    vattr = U.variant_attr(vid, R.ID)
    short = U.variant_short(vid, R.ID)
    for ob in body_srcs:
        I = wood_inputs(ob)
        I['under'] = under_trim(I['co'], props)
        rgb, rough = wood_paint(I, R.PALETTE, False)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        rgb_v, rough_v = wood_paint(I, vpal, True)
        S.set_colour_attr(ob, vattr, rgb_v)
        S.set_colour_attr(ob, f'rough_{short}', rough_v)
        S.add_attr(ob, 'gfine', fine_grain_mask(I))
    for ob in props:
        if 'region' in ob.data.attributes:
            # the posts (lootlid_legs.py) paint as the body's wood (their own fields)
            I = wood_inputs(ob)
            rgb, rough = wood_paint(I, R.PALETTE, False)
            S.set_colour_attr(ob, 'paint', rgb)
            S.set_colour_attr(ob, 'rough', rough)
            rgb_v, rough_v = wood_paint(I, vpal, True)
            S.set_colour_attr(ob, vattr, rgb_v)
            S.set_colour_attr(ob, f'rough_{short}', rough_v)
            continue
        co, _vn = S.mesh_arrays(ob)
        I = {'co': co, 'vn': _vn, **{k: _get(ob, k) for k in ('pk', 'bev', 'top', 'riv', 'emb', 'coin', 'tg', 'cv', 'ham', 'glow', 'deep')}}
        I['ring'] = rivet_ring(co)
        rgb, rough = prop_paint(I, R.PALETTE, False)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        rgb_v, rough_v = prop_paint(I, vpal, True)
        S.set_colour_attr(ob, vattr, rgb_v)
        S.set_colour_attr(ob, f'rough_{short}', rough_v)


# ----------------------------------------------------------------------------- per-pixel passes
def body_material(name: str, attr: str, pal: dict, marks):
    """The wood's colour pass: its paint plus fine grain lines between the painted ones (from the grain coordinates
    'gco', where 'gfine' allows), warm-dark on wood, bronze on the Gilded's gold."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    g = nb.attribute('gco').outputs['Vector']
    gx, gy, gz = nb.sep(g)
    fine = nb.attribute('gfine').outputs['Fac']
    q = nb.comb(nb.math('MULTIPLY', gx, 5.0), nb.math('MULTIPLY', gy, 42.0), nb.math('MULTIPLY', gz, 11.0))
    nv = nb.noise(q, 1.0, 3.0, 0.55)
    ph = nb.math('ADD', nb.math('DIVIDE', gy, 0.0023), nb.math('MULTIPLY', nv, 3.5))
    s1 = nb.math('SINE', nb.math('MULTIPLY', ph, 6.2832))
    lines = nb.smooth(s1, 0.55, 1.0)
    ph2 = nb.math('ADD', nb.math('DIVIDE', gy, 0.0009), nb.math('MULTIPLY', nv, 6.0))
    lines2 = nb.smooth(nb.math('SINE', nb.math('MULTIPLY', ph2, 6.2832)), 0.7, 1.0)
    gilded = attr != 'paint'
    g_k = 0.14 if gilded else 1.0                 # round 3: deeper grain on the wood, faint on the polished gold
    k = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', lines, 0.46 * g_k), nb.math('MULTIPLY', lines2, 0.18 * g_k)),
                nb.math('MULTIPLY', fine, nb.math('ADD', 0.45, nv)))
    tint = C.lin(C.shade_hex(pal['accent'], 0.9)) if gilded else (0.5, 0.36, 0.27)
    c = nb.mix(nb.math('MINIMUM', k, 0.6), c, nb.rgb(tint), blend='MULTIPLY')
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks):
    """The props' colour pass: their paint plus fine bright scratches on the gold (4-details panel 5) and the coins."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    pk = nb.attribute('pk').outputs['Fac']
    metal = nb.smooth(pk, 7.5, 7.3)
    warp = nb.noise(pos, 40.0, 2.0, 0.5)
    sc = None
    for d, cell in (((0.8, 0.3, 0.5), 11.0), ((-0.3, 0.9, 0.25), 13.0), ((0.2, -0.4, 0.9), 9.0)):
        v = nb.math('ADD', nb.vmath('DOT_PRODUCT', pos, d), nb.math('MULTIPLY', warp, 0.004))
        s = nb.math('ABSOLUTE', nb.math('SINE', nb.math('MULTIPLY', v, 2600.0)))
        line = nb.smooth(s, 0.99, 1.0)
        gate = nb.smooth(nb.noise(nb.vmath('ADD', pos, nb.comb(cell, 0.3, 1.7)), cell, 1.0, 0.5), 0.5, 0.6)
        one = nb.math('MULTIPLY', line, gate)
        sc = one if sc is None else nb.math('MAXIMUM', sc, one)
    hi = C.lin('#FFF2C0') if attr == 'paint' else C.lin(C.mix_hex(pal['accent'], '#FFE7A8', 0.5))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', sc, metal), 0.8), c, nb.rgb(hi))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- eyes
def eye_material(name: str, rough_pass: bool, pal: dict):
    """Big friendly eyes (1-hero, 3-faces neutral, 4-details panel 2): a cream eye, a big warm-brown iris (about 62% of
    the lens) finely streaked, a darker ring at its edge and a golden inner ring, a big dark pupil looking ahead (a
    touch toward the nose), a big catchlight up toward the nose and a small one low on the other side; a soft shadow
    under the socket's rim at the top. The rough pass keeps the lens glossy."""
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    ix = nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.04))
    iy = nb.math('ADD', ry, 0.015)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.62), nb.math('DIVIDE', iy, 0.64), 0.0))
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, 0.06, 0.9), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    eye = pal['eye']
    iris = C.mix_hex(eye, '#A8642A', 0.38)
    iris_l = C.mix_hex(iris, '#C8823C', 0.55)
    cream = '#F4E8D2'
    pupil = C.shade_hex(eye, 0.75)
    c = nb.ramp(ri, [(0.0, C.lin(pupil)), (0.46, C.lin(pupil)), (0.5, C.lin(C.shade_hex(iris, 0.7))), (0.56, C.lin(iris_l)),
                     (0.72, C.lin(iris)), (0.9, C.lin(C.shade_hex(iris, 0.72))), (0.98, C.lin(C.shade_hex(eye, 1.2))),
                     (1.03, C.lin(C.mix_hex(cream, '#D8C4A6', 0.5))), (1.12, C.lin(cream)), (3.0, C.lin(cream))])
    ang = nb.math('ARCTAN2', iy, ix)
    streak = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 27.0)), 0.5), 0.5),
                     nb.math('MULTIPLY', nb.smooth(ri, 0.5, 0.6), nb.smooth(ri, 0.95, 0.85)))
    c = nb.mix(nb.math('MULTIPLY', streak, 0.22), c, nb.rgb(C.lin(C.mix_hex(iris_l, '#F0C070', 0.4))))
    # the socket rim's soft shadow over the top of the eye, a cooler cream toward the edge
    rr = nb.vmath('LENGTH', nb.comb(rx, ry, 0.0))
    sh = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(ry, 0.35, 0.95), nb.smooth(rr, 0.55, 0.98)), 0.4)
    c = nb.mix(sh, c, nb.rgb(C.lin('#6A4A34')), blend='MULTIPLY')
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.2)), nb.math('SUBTRACT', ry, 0.24), 0.0)), 0.17, 0.11)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, nb.math('MULTIPLY', side, 0.22)), nb.math('ADD', ry, 0.28), 0.0)), 0.075, 0.045)
    c = nb.mix(nb.math('MAXIMUM', big, nb.math('MULTIPLY', small, 0.9)), c, nb.rgb((1.0, 1.0, 1.0)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the shape preview
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import lootlid_ultra as R
    from monsters.breeds import lootlid_wood as W
    L = W._LAST
    if L and L.get('n') == len(co):
        I = {k: L[k] for k in ('co', 'region', 'seam', 'crown', 'pid', 'grain', 'knot', 'nick', 'crack', 'edge', 'lash', 'lip',
                               'brow', 'gco')}
        I['sole'] = L['sole'].astype(np.float64)
        I['ldist'] = L['ld']
        I['vn'] = L['vn']
        return wood_paint(I, R.PALETTE, False)[0]
    z = R.zones(co)
    return np.where(z['inside'][:, None], lin('#3A2416')[None], lin(R.PALETTE['body'])[None])
