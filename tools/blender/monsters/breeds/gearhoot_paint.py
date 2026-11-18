"""Gearhoot's paint (Art 2.1 Ultra; chatgpt/monsters/29-gearhoot): per-vertex colour and roughness for the brass body
(hi_body) and every prop, the per-pixel engraving and brushing, and the eyes.

Colours come from CONTENT (brass #C9A04A, light brass #E9D7A6, lens teal #5CC9C0, copper #B86B3C, eyes pale #F7F3E3)
and variants.ts / the card (Silver: plates #BFC5CC, chest #E8ECF0, rivets, trim, gear teeth and the monocle ring dark
steel #5B6670, the iris #F2B544; the lens keeps its teal). Derived from them (CONTENT has no hex for these; the pictures
show them): the brass's painted highlight (the brass toward the pale #F7F3E3) and its dark patina (the brass toward the
copper, darkened), the normal eye's warm-brown iris (the copper darkened) and pupil, the mouth (the copper, dark), the
monocle's darker glass and pupil (the teal, darkened). The film keeps roughness at 0.3 or more and caps the coat, so the
brass carries its reflection painted in: faces turned up lighter, down darker and warmer, bright plate edges and rivet
tops (the Lootlid lesson: brass lands darker and more matte in the game).
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.nodes import new_mat
from monsters.breeds import gearhoot_form as F
from monsters.breeds import gearhoot_noise as N
from monsters.breeds import gearhoot_props as PR

smooth = N.smooth
LENS = '#5CC9C0'
SCLERA = '#F7F3E3'
LIFT = 1.32                                 # the brass painted a little above its hex: the film renders it darker


def lin(h: str) -> np.ndarray:
    return S.v3(C.lin_rgb(h))


def _mix(rgb: np.ndarray, col, k) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    k = k[:, None] if k.ndim == 1 else k
    col = np.asarray(col, np.float64)
    return rgb * (1 - k) + (col[None] if col.ndim == 1 else col) * k


def roles(pal: dict) -> dict:
    """The paint's colours from a palette: brass (the plates), light (the chest and the face), trim (copper, or the
    Silver's dark steel: rivets, the monocle ring, hubs, the key's housing), gear (brass, or the Silver's steel)."""
    silver = pal['body'].upper() == '#BFC5CC'
    brass, light, trim = pal['body'], pal['belly'], pal['copper']
    if silver:
        return {'silver': True, 'brass': brass, 'brass_hi': C.mix_hex(brass, '#FFFFFF', 0.7), 'deep': C.shade_hex(C.mix_hex(brass, '#2A3038', 0.75), 0.55),
                'light': light, 'light_hi': '#FFFFFF', 'trim': trim, 'trim_hi': C.mix_hex(trim, '#D8E0E8', 0.5),
                'trim_deep': C.shade_hex(trim, 0.5), 'wingcu': C.mix_hex(brass, '#8A949E', 0.35), 'gear': trim,
                'iris': pal['eye'], 'warm': '#4A525C'}
    return {'silver': False, 'brass': brass, 'brass_hi': C.mix_hex(brass, SCLERA, 0.55), 'deep': C.shade_hex(C.mix_hex(brass, '#6A3A0C', 0.55), 0.62),
            'light': light, 'light_hi': C.mix_hex(light, '#FFFFFF', 0.45), 'trim': trim, 'trim_hi': C.mix_hex(trim, light, 0.45),
            'trim_deep': C.shade_hex(trim, 0.5), 'wingcu': C.mix_hex(trim, brass, 0.25), 'gear': brass,
            'iris': C.shade_hex(C.mix_hex(trim, '#3A1C0A', 0.45), 0.85), 'warm': '#8A4A12'}


def env(rgb: np.ndarray, nz: np.ndarray, lo: float, hi: float, warm_hex: str, warm: float) -> np.ndarray:
    """A metal's painted reflection: faces turned up lighter, faces turned down darker and warmer."""
    t = smooth(-0.6, 0.9, nz)
    out = rgb * (lo + (hi - lo) * t)[:, None]
    return np.clip(_mix(out, lin(warm_hex) * 0.8, warm * (1 - t) ** 2), 0, 1)


# ----------------------------------------------------------------------------- the body
def body_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    R = roles(pal)
    co, nz = I['co'], I['vn'][:, 2]
    n = len(co)
    mott = N.fbm(co, 1 / 0.02, 31, 3)
    ph = U.plate_hash(np.round(I['pid']).astype(np.int64), 3)
    region = np.round(I['region']).astype(int)
    head, collar = region == 1, region == 2
    chest = (region == 0) & (I['pchest'] > 0.5)
    lift = LIFT if not R['silver'] else 0.86            # the silver is light already (it read white, then chalky)
    rgb = lin(R['brass'])[None] * (lift * (0.94 + 0.12 * ph + 0.05 * mott))[:, None]
    rgb = np.where(chest[:, None], lin(R['light'])[None] * (0.97 + 0.06 * ph)[:, None], rgb)
    rgb = _mix(rgb, lin(R['brass']) * lift * 1.04, collar.astype(float))     # round 1: a mid-brass rim, not cream
    face_k = I['face'] * (1.0 - smooth(0.01, 0.3, I['plate']))
    rgb = _mix(rgb, lin(R['light']) * lift, face_k)
    rgb = _mix(rgb, lin(R['brass']) * lift * 0.9, I['mask'])         # round 2: the helm no hotter than the body
    rgb = _mix(rgb, lin(R['brass_hi']), 0.35 * I['mridge'])           # the helm plate's raised edge catches the light
    # round 1: less hot on top (the dome read glazed against the sides); the silver with more contrast
    rgb = env(rgb, nz, 0.68, 1.0, R['warm'], 0.55) if not R['silver'] else env(rgb, nz, 0.55, 1.08, R['warm'], 0.5)
    if R['silver']:
        # polished silver: a darker horizon band in the reflection (round 2: chalky porcelain)
        rgb = rgb * (1.0 - 0.32 * smooth(-0.35, 0.0, nz) * smooth(0.35, 0.05, nz))[:, None]
    # the plates: the lower (exposed) edge's bright lip, then the dark line under it; the crown's sheen
    lower = smooth(-0.1, 0.3, I['pls'])
    plate = I['plate'] > 0.01
    rgb = _mix(rgb, np.where(chest[:, None], lin(R['light_hi'])[None], lin(R['brass_hi'])[None]), 0.32 * I['ptop'] * plate)
    # round 1: the plates read as engraving; a bolder shadow line under each lower edge and a warm patina toward it
    rgb = _mix(rgb, lin(R['deep']), 0.85 * smooth(0.8, 0.98, I['prim']) * lower * plate)
    rgb = _mix(rgb, lin(C.mix_hex(R['deep'], R['trim'], 0.35)), 0.22 * smooth(0.55, 0.85, I['prim']) * smooth(0.3, 0.9, I['pls']) * plate)
    # patina in the hollows (between plates, round the collar's foot)
    rgb = _mix(rgb, lin(R['deep']), 0.26 * smooth(0.1, 0.7, mott) * (1 - I['mask']) * (1 - I['face']))
    # the brow mask's rim and the facial disc's edge
    rgb = _mix(rgb, lin(R['deep']), 0.35 * smooth(0.0, 0.25, I['mask']) * smooth(0.6, 0.25, I['mask']))
    rgb = _mix(rgb, lin(R['deep']), 0.25 * smooth(0.0, 0.3, I['face']) * smooth(0.7, 0.3, I['face']) * (1 - I['mask']))
    # emblems: the raised gear bright, its ground dark
    rgb = _mix(rgb, lin(R['brass_hi']), 0.45 * I['emb'])
    # rivets: copper domes with a bright top, a dark ring round each
    riv = I['riv']
    rc = env(np.tile(lin(R['trim']), (n, 1)), nz, 0.7, 1.15, R['warm'], 0.3)
    rc = _mix(rc, lin(R['trim_hi']), 0.6 * smooth(0.2, 0.9, nz) * smooth(0.6, 1.0, riv))
    rgb = _mix(rgb, rc, riv)
    rgb = _mix(rgb, lin(R['deep']), 0.55 * I['rring'] * (1 - riv))
    # the eye sockets' floors (seen when the lenses squash shut): a brass lid with a dark lash line under the normal eye,
    # darker teal glass with a lid line in the monocle
    lash_n = smooth(0.1, 0.05, np.abs(I['eyey_n'] + 0.1)) * (I['eyer_n'] < 1.03)
    lid = I['eyer_n'] < 1.0
    rgb = np.where(lid[:, None], lin(C.mix_hex(R['brass'], R['light'], 0.45))[None] * np.ones((n, 1)), rgb)
    rgb = _mix(rgb, lin(R['deep']), 0.85 * lash_n)
    mono = I['eyer_m'] < 1.04
    glass = lin(LENS)[None] * (0.88 + 0.12 * smooth(0.4, -0.6, I['eyey_m']))[:, None]       # round 2: bright teal shut
    rgb = np.where(mono[:, None], glass, rgb)
    lash_m = smooth(0.1, 0.05, np.abs(I['eyey_m'] + 0.1)) * (I['eyer_m'] < 1.0)
    rgb = _mix(rgb, lin(C.shade_hex(LENS, 0.18)), 0.9 * lash_m)
    # the mouth under the beak
    # (round 2: no mouth paint; the slot under the beak read as a dark wedge)
    rgb = _mix(rgb, lin(R['deep']) * 0.35, 0.9 * I['seat'])
    rgb = _mix(rgb, lin(R['deep']) * 0.6, 0.5 * I['under'])
    # round 1: brushed metal, not glaze: rougher, little coat
    rough = 0.44 + 0.12 * smooth(0.1, 0.7, mott) * (1 - I['mask'])
    coat = np.full(n, 0.2)
    rough = np.where(I['face'] > 0.5, 0.4, rough)
    rough = np.where(riv > 0.5, 0.3, rough)
    rough = np.where(I['mask'] > 0.5, 0.55, rough)                     # round 2: no white flare on the crown
    coat = np.where(I['mask'] > 0.5, 0.05, coat)
    rough = np.where(mono, 0.12, rough)
    coat = np.where(mono, 0.9, coat)
    rough = np.where(I['mouth'] > 0.3, 0.8, rough)
    # the neck's seat and the head's underside: matte, no coat (round 2: the coat caught the sky as a pale ring)
    dark = np.maximum(I['seat'], I['under']) > 0.3
    rough = np.where(dark, 0.85, rough)
    coat = np.where(dark, 0.0, coat)
    coat = np.where(I['mouth'] > 0.3, 0.0, coat)
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


# ----------------------------------------------------------------------------- the props
def prop_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    R = roles(pal)
    co, nz = I['co'], I['vn'][:, 2]
    n = len(co)
    pk = np.round(I['pk']).astype(int)
    mott = N.fbm(co, 1 / 0.015, 41, 3)
    brass = np.tile(lin(R['brass']) * (LIFT if not R['silver'] else 1.06), (n, 1)) * (0.95 + 0.06 * mott)[:, None]
    rgb = brass.copy()
    # the wings: brass and copper plates by turns (1-hero), a raised midrib, dark edges and roots
    wing = pk == PR.PK_WING
    cu = I['cu'] > 0.5
    w = np.where(cu[:, None], np.tile(lin(R['wingcu']) * 1.05, (n, 1)), brass)     # round 1: the lifted copper read pink
    w = env(w, nz, 0.6, 1.12, R['warm'], 0.45)
    w = _mix(w, lin(R['brass_hi']), 0.35 * smooth(0.82, 0.97, I['h']) * (I['face'] > 0) * smooth(0.25, 0.0, np.abs(I['q'])))
    w = _mix(w, lin(R['deep']), 0.5 * smooth(0.72, 0.98, np.abs(I['q'])) + 0.45 * smooth(0.25, 0.05, I['u']))
    w = np.where((I['face'] < 0)[:, None], w * 1.5, w)           # rounds 1-3: brighter backs (their baked AO is deep)
    rgb = np.where(wing[:, None], w, rgb)
    # gears: the rim and teeth bright, the inner edge dark; copper hubs
    gear = pk == PR.PK_GEAR
    g = env(np.tile(lin(R['gear']) * (LIFT if not R['silver'] else 1.0), (n, 1)), nz, 0.62, 1.15, R['warm'], 0.35)
    g = _mix(g, lin(R['brass_hi'] if not R['silver'] else R['trim_hi']), 0.4 * I['tooth'])
    g = _mix(g, lin(R['deep'] if not R['silver'] else R['trim_deep']), 0.45 * smooth(0.8, 0.74, I['gr']) * (I['gr'] > 0.6))
    rgb = np.where(gear[:, None], g, rgb)
    copper = np.isin(pk, (PR.PK_HUB, PR.PK_RING, PR.PK_BRACKET, PR.PK_KEYBASE, PR.PK_KNEE))
    cc = env(np.tile(lin(R['trim']), (n, 1)), nz, 0.66, 1.18, R['warm'], 0.3)
    cc = _mix(cc, lin(R['trim_hi']), 0.35 * smooth(0.3, 0.95, nz))
    rgb = np.where(copper[:, None], cc, rgb)
    # polished brass: the beak, the claws, the screw knob (brighter, warmer)
    pol = np.isin(pk, (PR.PK_BEAK, PR.PK_CLAW, PR.PK_KNOB))
    pc = env(np.tile(lin(R['brass']) * (LIFT * 1.06 if not R['silver'] else 0.92), (n, 1)), nz, 0.66, 1.12, R['warm'], 0.3)     # golden; the Silver's talons not bone-white
    rgb = np.where(pol[:, None], pc, rgb)
    # plain brass: the tufts, the key, the boots, the toes; darker cuffs
    plain = np.isin(pk, (PR.PK_TUFT, PR.PK_KEY, PR.PK_BOOT, PR.PK_TOE, PR.PK_CUFF, PR.PK_NECK))
    pb = env(brass, nz, 0.62, 1.12, R['warm'], 0.4)
    pb = np.where((pk == PR.PK_CUFF)[:, None], pb * 0.8, pb)
    # the tufts: a darker bevelled rim round each blade, a bright ridge along it
    ck = np.abs(np.cos(2 * np.pi * I['k']))
    tuft = pk == PR.PK_TUFT
    pb = np.where(tuft[:, None], _mix(_mix(pb, lin(R['deep']), 0.5 * smooth(0.8, 0.97, ck)), lin(R['brass_hi']), 0.3 * smooth(0.25, 0.05, ck) * smooth(-0.2, 0.6, nz)), pb)
    rgb = np.where(plain[:, None], pb, rgb)
    # the neck dome: a ring of riveted plates (radial seams, a scalloped row; the rivets per pixel, prop_material)
    neck = pk == PR.PK_NECK
    if neck.any():
        ang = np.arctan2(co[:, 1] - F.HC[1], co[:, 0])
        fa = np.mod(ang * 14 / (2 * np.pi), 1.0)
        rr = np.hypot(co[:, 0], co[:, 1] - F.HC[1])
        seam = smooth(0.06, 0.02, np.minimum(fa, 1 - fa)) + smooth(0.006, 0.002, np.abs(rr - 0.15 - 0.012 * np.cos(2 * np.pi * fa)))
        rgb = np.where(neck[:, None], _mix(rgb, lin(R['deep']), 0.7 * np.clip(seam, 0, 1)), rgb)
    rough = np.full(n, 0.42)
    coat = np.full(n, 0.25)
    rough = np.where(pol, 0.3, rough)
    coat = np.where(pol, 0.6, coat)
    rough = np.where(wing & (I['face'] < 0), 0.6, rough)
    return np.clip(rgb, 0, 1), np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1)


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


BODY_KEYS = ('region', 'mask', 'face', 'plate', 'prim', 'ptop', 'pid', 'pls', 'plq', 'riv', 'rring', 'emb', 'eyer_n', 'eyey_n',
             'eyer_m', 'eyey_m', 'mouth', 'pchest', 'seat', 'under', 'mridge')
PROP_KEYS = ('pk', 'cu', 'q', 'h', 'face', 'u', 'gr', 'tooth', 'k')


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import gearhoot_ultra as R
    vid, vpal = next(iter(R.VARIANTS.items()))
    vattr = U.variant_attr(vid, R.ID)
    short = U.variant_short(vid, R.ID)
    for ob in body_srcs:
        co, vn = S.mesh_arrays(ob)
        I = {'co': S.attr_array(ob, 'root').astype(np.float64) if 'root' in ob.data.attributes else co, 'vn': vn,
             **{k: _get(ob, k, 9.0 if k.startswith('eyer') else 0.0) for k in BODY_KEYS}}
        rgb, rough = body_paint(I, R.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        rgb_v, rough_v = body_paint(I, vpal)
        S.set_colour_attr(ob, vattr, rgb_v)
        S.set_colour_attr(ob, f'rough_{short}', rough_v)
        mono = I['eyer_m'] < 1.04
        S.add_attr(ob, 'glow', np.where(mono, 0.35, 0.0))
    for ob in props:
        co, vn = S.mesh_arrays(ob)
        I = {'co': co, 'vn': vn, **{k: _get(ob, k) for k in PROP_KEYS}}
        rgb, rough = prop_paint(I, R.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        rgb_v, rough_v = prop_paint(I, vpal)
        S.set_colour_attr(ob, vattr, rgb_v)
        S.set_colour_attr(ob, f'rough_{short}', rough_v)


# ----------------------------------------------------------------------------- per-pixel passes
def _scratches(nb, pos):
    """Fine brushed lines in three directions, gated by noise (4-details panel 6)."""
    warp = nb.noise(pos, 40.0, 2.0, 0.5)
    sc = None
    for d, cell in (((0.8, 0.3, 0.5), 11.0), ((-0.3, 0.9, 0.25), 13.0), ((0.2, -0.4, 0.9), 9.0)):
        v = nb.math('ADD', nb.vmath('DOT_PRODUCT', pos, d), nb.math('MULTIPLY', warp, 0.004))
        s = nb.math('ABSOLUTE', nb.math('SINE', nb.math('MULTIPLY', v, 2600.0)))
        line = nb.smooth(s, 0.985, 1.0)
        gate = nb.smooth(nb.noise(nb.vmath('ADD', pos, nb.comb(cell, 0.3, 1.7)), cell, 1.0, 0.5), 0.5, 0.6)
        one = nb.math('MULTIPLY', line, gate)
        sc = one if sc is None else nb.math('MAXIMUM', sc, one)
    return sc


def _ring_line(nb, x, y, cx, cy, r, w):
    """1 on a thin circle (radius r about (cx, cy)) in a plate's own coordinates."""
    d = nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', x, cx), nb.math('SUBTRACT', y, cy), 0.0))
    return nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', d, r)), w, 0.4 * w)


def body_material(name: str, attr: str, pal: dict, marks):
    """The body's colour pass: its paint, the engraving on every plate (an inner border along the exposed edge and a
    pair of curled scrolls: 4-details panel 6), fine swirls on the facial disc, and brushing scratches."""
    m, nb = new_mat(name)
    R = roles(pal)
    c = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    s = nb.attribute('pls').outputs['Fac']
    q = nb.attribute('plq').outputs['Fac']
    plate = nb.smooth(nb.attribute('plate').outputs['Fac'], 0.05, 0.3)
    rr = nb.vmath('LENGTH', nb.comb(s, q, 0.0))
    border = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', rr, 0.7)), 0.03, 0.012), nb.smooth(s, -0.05, 0.2))
    sc1 = nb.math('MULTIPLY', _ring_line(nb, s, q, 0.32, 0.26, 0.2, 0.026), nb.smooth(q, 0.12, 0.2))
    sc2 = nb.math('MULTIPLY', _ring_line(nb, s, q, 0.32, -0.26, 0.2, 0.026), nb.smooth(q, -0.12, -0.2))
    stem = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', q), 0.028, 0.012), nb.math('MULTIPLY', nb.smooth(s, 0.05, 0.12), nb.smooth(s, 0.55, 0.45)))
    eng = nb.math('MULTIPLY', nb.math('MAXIMUM', border, nb.math('MAXIMUM', sc1, sc2)), plate)
    # the facial disc's swirls: wavy engraved lines on the cheeks, away from the eyes
    face = nb.attribute('face').outputs['Fac']
    px, py, pz = nb.sep(pos)
    ax_ = nb.math('ABSOLUTE', px)
    zc = float(F.HC[2])
    sw = None
    for cx, cz, r in ((0.045, zc - 0.07, 0.02), (0.15, zc - 0.075, 0.024), (0.19, zc - 0.015, 0.02), (0.175, zc + 0.06, 0.018)):
        outer = nb.math('MULTIPLY', _ring_line(nb, ax_, pz, cx, cz, r, 0.0035), nb.smooth(nb.math('SUBTRACT', pz, cz), -0.003, 0.003))
        inner = nb.math('MULTIPLY', _ring_line(nb, ax_, pz, cx - 0.5 * r, cz, 0.5 * r, 0.003), nb.smooth(nb.math('SUBTRACT', pz, cz), 0.003, -0.003))
        one = nb.math('MAXIMUM', outer, inner)
        sw = one if sw is None else nb.math('MAXIMUM', sw, one)
    away = nb.math('MULTIPLY', nb.smooth(nb.attribute('eyer_n').outputs['Fac'], 1.15, 1.3), nb.smooth(nb.attribute('eyer_m').outputs['Fac'], 1.25, 1.4))
    sw = nb.math('MULTIPLY', nb.math('MULTIPLY', sw, nb.smooth(face, 0.6, 0.95)), away)
    eng = nb.math('MAXIMUM', nb.math('MULTIPLY', eng, 0.7), nb.math('MULTIPLY', sw, 0.85))
    sock = nb.math('MULTIPLY', nb.smooth(nb.attribute('eyer_n').outputs['Fac'], 1.0, 1.08), nb.smooth(nb.attribute('eyer_m').outputs['Fac'], 1.0, 1.08))
    eng = nb.math('MULTIPLY', eng, sock)
    tint = C.lin(C.shade_hex(R['deep'], 1.1))
    c = nb.mix(nb.math('MULTIPLY', eng, 0.7), c, nb.rgb(tint))
    hi = C.lin(R['brass_hi'])
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', _scratches(nb, pos), 0.45), sock), c, nb.rgb(hi))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks):
    """The props' colour pass: their paint, an engraved border and a curl on each wing plate, brushing scratches."""
    m, nb = new_mat(name)
    R = roles(pal)
    c = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    pk = nb.attribute('pk').outputs['Fac']
    wing = nb.math('MULTIPLY', nb.smooth(pk, 0.5, 0.8), nb.smooth(pk, 1.5, 1.2))
    u = nb.attribute('u').outputs['Fac']
    q = nb.attribute('q').outputs['Fac']
    face = nb.smooth(nb.attribute('face').outputs['Fac'], 0.0, 0.5)
    aq = nb.math('ABSOLUTE', q)
    border = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', aq, 0.66)), 0.05, 0.02), nb.smooth(u, 0.3, 0.4))
    curl = _ring_line(nb, nb.math('MULTIPLY', u, 2.4), q, 1.65, 0.0, 0.3, 0.05)
    eng = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.math('MAXIMUM', border, curl), wing), face)
    c = nb.mix(nb.math('MULTIPLY', eng, 0.65), c, nb.rgb(C.lin(C.shade_hex(R['deep'], 1.1))))
    # the neck dome's copper rivets: one on each of its 14 plates (round 1)
    neck = nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', pk, 16.0)), 0.4, 0.2)
    nx, ny, _nz = nb.sep(pos)
    ny = nb.math('SUBTRACT', ny, float(F.HC[1]))
    nr = nb.vmath('LENGTH', nb.comb(nx, ny, 0.0))
    na = nb.math('MULTIPLY', nb.math('ARCTAN2', ny, nx), 14.0 / 6.2832)
    fa = nb.math('SUBTRACT', nb.math('FRACT', na), 0.5)
    du = nb.math('MULTIPLY', fa, nb.math('MULTIPLY', nr, 6.2832 / 14.0))
    dot = nb.smooth(nb.vmath('LENGTH', nb.comb(du, nb.math('SUBTRACT', nr, 0.172), 0.0)), 0.0075, 0.005)
    c = nb.mix(nb.math('MULTIPLY', dot, neck), c, nb.rgb(C.lin(R['trim_hi'])))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', _scratches(nb, pos), 0.4), nb.math('SUBTRACT', 1.0, neck)), c, nb.rgb(C.lin(R['brass_hi'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- eyes
def eye_material(name: str, rough_pass: bool, pal: dict):
    """The left lens (+X) is the monocle's teal glass (4-details panel 2): bright teal, a darker iris ring, a deep
    pupil, a broad white reflection arc high on the nose side and a small catchlight; the right a pale round eye with a
    warm-brown iris (the Silver's #F2B544), a big black pupil and two catchlights (1-hero). Glossy both."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, 0.06, 0.9), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    R = roles(pal)
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    mono = nb.smooth(side, -0.5, 0.5)
    # the normal eye (on the right, -X): the iris a touch toward the nose (+X) and up, looking at the viewer
    ix = nb.math('SUBTRACT', rx, 0.06)
    iy = nb.math('SUBTRACT', ry, 0.02)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), 1.3)
    iris = R['iris']
    iris_l = C.mix_hex(iris, '#F0C080', 0.3)
    pupil = '#0E0A08'
    n_col = nb.ramp(ri, [(0.0, C.lin(pupil)), (0.25, C.lin(pupil)), (0.28, C.lin(C.shade_hex(iris, 0.6))), (0.33, C.lin(iris_l)),
                         (0.42, C.lin(iris)), (0.47, C.lin(C.shade_hex(iris, 0.55))), (0.5, C.lin(C.mix_hex(SCLERA, '#C8B89A', 0.5))),
                         (0.56, C.lin(SCLERA)), (1.0, C.lin(SCLERA))])
    ang = nb.math('ARCTAN2', iy, ix)
    streak = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 23.0)), 0.5), 0.5),
                     nb.math('MULTIPLY', nb.smooth(ri, 0.28, 0.33), nb.smooth(ri, 0.47, 0.42)))
    n_col = nb.mix(nb.math('MULTIPLY', streak, 0.2), n_col, nb.rgb(C.lin(iris_l)))
    rr = nb.vmath('LENGTH', nb.comb(rx, ry, 0.0))
    shade = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(ry, 0.3, 0.95), nb.smooth(rr, 0.55, 0.98)), 0.35)
    n_col = nb.mix(shade, n_col, nb.rgb(C.lin('#8A6A40')), blend='MULTIPLY')
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.24), nb.math('SUBTRACT', ry, 0.26), 0.0)), 0.16, 0.1)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.12), nb.math('ADD', ry, 0.22), 0.0)), 0.07, 0.04)
    n_col = nb.mix(nb.math('MAXIMUM', big, nb.math('MULTIPLY', small, 0.85)), n_col, nb.rgb((1.0, 1.0, 1.0)))
    # the monocle's glass
    gx = nb.math('ADD', rx, 0.04)
    gr = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(gx, ry, 0.0)), 1.3)
    t_col = nb.ramp(gr, [(0.0, C.lin(C.shade_hex(LENS, 0.15))), (0.19, C.lin(C.shade_hex(LENS, 0.2))), (0.23, C.lin(C.shade_hex(LENS, 0.5))),
                         (0.3, C.lin(C.shade_hex(LENS, 0.9))), (0.42, C.lin(LENS)), (0.48, C.lin(C.shade_hex(LENS, 0.7))),
                         (0.54, C.lin(C.shade_hex(LENS, 0.88))), (0.64, C.lin(C.shade_hex(LENS, 0.82))), (0.7, C.lin(C.shade_hex(LENS, 0.45))),
                         (1.0, C.lin(C.shade_hex(LENS, 0.35)))])
    rd = nb.vmath('LENGTH', nb.comb(rx, ry, 0.0))
    arc = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', rd, 0.66)), 0.15, 0.04),
                  nb.math('MULTIPLY', nb.smooth(ry, -0.15, 0.3), nb.smooth(rx, 0.25, -0.3)))
    spot = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.24), nb.math('SUBTRACT', ry, 0.34), 0.0)), 0.09, 0.05)
    t_col = nb.mix(nb.math('MAXIMUM', nb.math('MULTIPLY', arc, 0.62), spot), t_col, nb.rgb((0.85, 0.98, 0.96)))
    c = nb.mix(mono, n_col, t_col)
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the shape preview
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import gearhoot_carve as K
    from monsters.breeds import gearhoot_ultra as R
    L = K._LAST
    if L and L.get('n') == len(co):
        I = {'co': co, 'vn': L['vn'], **{k: L[k] for k in BODY_KEYS}}
        return body_paint(I, R.PALETTE)[0]
    head = F.head_mask(co)
    rgb = np.tile(lin(R.PALETTE['body']), (len(co), 1))
    rgb[head & (co[:, 1] < F.Y_FACE + 0.02)] = lin(R.PALETTE['belly'])
    return rgb
