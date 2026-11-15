"""Pluckrex's hide, carved into the high source and baked (no fur, no cards): pebbly domed scales of mixed sizes
(bigger along the back, small on the head, the limbs and the tail's end; 1-hero, 4-details panel 6), flat polygonal
plates on the cream belly and throat, small fillers in the wide gaps, and (grown) keeled ridge scales down the back and
the tail (grown-4-details panel 5). Also the face's small sculpting: the nostrils, the closed lids under the lenses,
the toes' clefts. Metres; -Y is the front."""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.surface import norm, smooth, tangent, v3
from monsters.breeds import gloomgrin_stone as K
from monsters.breeds import hearthwing_parts as HP
from monsters.breeds import pluckrex_props as PR
from monsters.breeds import pluckrex_zones as Z

_PLATES: dict = {}


def nostrils(F, co: np.ndarray) -> np.ndarray:
    N = F.G['nose']
    out = np.zeros(len(co))
    for s in (1, -1):
        c = v3((N['dx'] * s, N['c'][1], N['c'][2]))
        d = np.linalg.norm((co - c) / v3(N['shape']), axis=1)
        out = np.maximum(out, np.exp(-(d / N['r']) ** 2))
    return out


LID_LASH, LID_DROP, LID_W = 0.06, 0.15, 0.95


def closed_lid(F, co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens: the soft closed lid and its curved lash line, seen only while a blink sinks the lens."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = F.eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax, ay = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1]
        r2 = (xe / ax) ** 2 + (ye / ay) ** 2
        front = ze > -0.6 * F.EYE_R
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * F.EYE_R
        th = (0.0035 + 0.003 * smooth(0.2, 1.0, xn * s)) * F.k
        on = front & (np.abs(xn) < 0.92) & (r2 < 1.1)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(0.92, 0.78, np.abs(xn)))
    return bulge, lash


def lid_rim(F, co: np.ndarray) -> np.ndarray:
    """0..1: a soft raised lid round each lens, fullest over its upper half (round 2: the lens' edge stood proud of
    the face with nothing round it)."""
    out = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = F.eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        rr = np.sqrt((xe / (F.EYE_R * F.EYE_SHAPE[0])) ** 2 + (ye / (F.EYE_R * F.EYE_SHAPE[1])) ** 2)
        up = smooth(-0.55, 0.25, ye / F.EYE_R)
        out = np.maximum(out, np.exp(-((rr - 1.08) / 0.1) ** 2) * (0.35 + 0.65 * up) * (ze > -0.8 * F.EYE_R))
    return out


def toe_clefts(F, co: np.ndarray) -> np.ndarray:
    out = np.zeros(len(co))
    for s in (1, -1):
        tc = F.toe_centres(s)
        for a, b in zip(tc[:-1], tc[1:]):
            mm = (a + b) * 0.5
            d = np.sqrt(((co[:, 0] - mm.x) / (0.006 * F.k)) ** 2 + ((co[:, 1] - (mm.y + 0.02 * F.k)) / (0.05 * F.k)) ** 2)
            out = np.maximum(out, np.exp(-d ** 2) * (co[:, 2] < 0.08 * F.k) * (co[:, 2] > 0.004))
    return out


# ============================================================================= the pebbles
def pebble_params(F, p: np.ndarray, n: np.ndarray, z: dict):
    """(spacing NaN = none, radius, height) per sample point."""
    Pb = F.G['pebbles']
    k = F.k
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    sp = np.full(len(p), Pb['body'])
    sp = np.where(z['leg'] | z['foot'], Pb['leg'], sp)
    sp = np.where(z['foot'], Pb['foot'], sp)
    sp = np.where(z['arm'], Pb['arm'], sp)
    sp = np.where(z['hand'], Pb['hand'], sp)
    sp = np.where(z['tail'], Pb['tail'][0] + (Pb['tail'][1] - Pb['tail'][0]) * np.clip(z['tail_t'], 0, 1), sp)
    sp = sp * (1.0 + Pb['back_k'] * z['back'])
    sp = np.where(z['head'], Pb['head'], sp)
    sp = np.where(z['head'] & (z['muzzle'] | (y < F.EYE_C[1].y + 0.01 * k)), Pb['face'], sp)
    # mixed sizes: a smooth size field (a few pebbles across) and a little per point
    vn_ = K.value_noise(p, 1.0 / (0.07 * k), 11)
    sp = sp * (0.78 + 0.5 * vn_) * (0.93 + 0.14 * K.hash1(np.arange(len(p)), 5))
    cream = z['cream']
    sp = sp * (1.0 + (Pb['cream_k'] - 1.0) * smooth(0.3, 0.7, cream))
    rad = sp * (0.56 + 0.04 * smooth(0.3, 0.7, cream))
    hgt = rad * (Pb['dome'] * (1.0 - smooth(0.3, 0.7, cream)) + Pb['flat'] * smooth(0.3, 0.7, cream))
    hgt = np.where(z['leg'] | z['foot'], hgt * Pb.get('leg_dome', 0.8), hgt)
    hgt = np.where(z['head'] & (z['muzzle'] | (y < F.EYE_C[1].y + 0.01 * k)), hgt * 0.5, hgt)    # round 3: tiny, flat on the snout
    # tiny, low pebbles on the lids under the lenses (a smooth dome read as a goggle when the eyes shut)
    lid = z['eye_d'] < F.EYE_R * 1.22
    sp = np.where(lid, Pb['face'] * 0.7, sp)
    rad = np.where(lid, sp * 0.56, rad)
    hgt = np.where(lid, rad * 0.5 * Pb['dome'], hgt)
    skip = z['mouth_in'] | (z['sole'] > 0.5) | (z['palm'] > 0.5) | z['finger']
    skip |= (nostrils(F, p) > 0.15)
    return np.where(skip, np.nan, sp), rad, hgt


def _merge(a: dict, b: dict) -> dict:
    return {key: np.concatenate([a[key], b[key]]) for key in a}


def _clear_of(co, vn, plates, margin) -> np.ndarray:
    wide = dict(plates)
    wide['a'] = plates['a'] + margin
    wide['b'] = plates['b'] + margin
    return U.plate_field(co, vn, wide, 'cobble')['pid'] < 0


def make_pebbles(F, co: np.ndarray, vn: np.ndarray) -> dict:
    z = Z.zones(F, co, vn)
    sp, rad, hgt = pebble_params(F, co, vn, z)
    # round 3: front to back on the head (a downward flow is undefined on the skull's top: a star of stretched pebbles)
    g = np.where(z['head'][:, None], v3((0.0, 1.0, 0.0))[None], v3((0.0, 0.25, -1.0))[None])
    flow = tangent(np.broadcast_to(g, (len(co), 3)).copy(), vn)
    seed = F.G['pebbles'].get('seed', 1212)
    # polish: more candidates (the tail's thin end got no scales: stretched smooth blue)
    main = U.plate_layout(co, vn, sp, rad, hgt, seed, flow=flow, aspect=1.12, wobble=0.16, max_candidates=240000)
    gap = _clear_of(co, vn, main, 0.004 * F.k) & np.isfinite(sp) & ~(z['leg'] | z['foot']) & (z['cream'] < 0.5)
    fill = U.plate_layout(co, vn, np.where(gap, sp * 0.5, np.nan), rad * 0.5, hgt * 0.55, seed + 1, flow=flow, aspect=1.1, wobble=0.14)
    plates = _merge(main, fill)
    plates['kind'] = np.concatenate([np.zeros(len(main['c'])), np.ones(len(fill['c']))])
    zc = Z.zones(F, plates['c'], plates['n'])
    plates['cream'] = zc['cream']
    plates['back'] = zc['back']
    C.log(f'pluckrex: {len(main["c"])} pebbles + {len(fill["c"])} fillers')
    return plates


def keel_field(F, co, vn, z):
    """Grown: keeled ridge scales down the back and the tail's top (overlapping shingles, a raised midrib)."""
    Kl = F.G.get('keel')
    if not Kl:
        return None
    on = (z['back'] > 0.35) & np.isfinite(co[:, 0])
    sp = np.where(on, Kl['sp'] * (1.0 + 0.6 * smooth(0.0, 0.08 * F.k, -np.abs(co[:, 0]) + 0.08 * F.k)), np.nan)
    sp = np.where(z['tail'], sp * (1.0 - 0.45 * np.clip(z['tail_t'], 0, 1)), sp)
    flow = tangent(np.where(z['tail'][:, None], v3((0.0, 1.0, 0.1))[None], v3((0.0, 0.35, -1.0))[None]), vn)
    pl = U.plate_layout(co, vn, sp, sp * 0.62, sp * Kl['h'], F.G['pebbles'].get('seed', 1212) + 7, flow=flow, aspect=1.5, wobble=0.06)
    f = HP.shingle_field(co, vn, pl, leaf=0.75)
    rib = HP.scale_midrib(co, pl, f['pid'])
    return pl, f, rib


def carve(F, ob) -> None:
    co, vn = S.mesh_arrays(ob)
    k = F.k
    nos = nostrils(F, co)
    cleft = toe_clefts(F, co)
    bulge, lash = closed_lid(F, co)
    crease = np.exp(-(PR.smile_dist(F, co) / (0.0035 * k)) ** 2)
    rim = lid_rim(F, co)
    S.base_attrs(ob, co, {'mouth': crease})
    S.add_attr(ob, 'rootn', vn)
    S.add_attr(ob, 'lash', lash)
    disp = (-0.006 * k * nos - 0.006 * k * cleft + 0.0015 * k * bulge - 0.0016 * k * lash - 0.002 * k * crease
            + F.G['eye'].get('lid', 0.006) * rim)
    S.set_positions(ob, co + vn * disp[:, None])
    co2, vn2 = S.mesh_arrays(ob)
    plates = make_pebbles(F, co, vn)
    f = U.plate_field(co2, vn2, plates, 'cobble', 1.0, inset=0.0004 * k, edge_soft=F.G['pebbles'].get('soft', 0.55))
    h = f['h']
    pid = f['pid']
    keel = None
    z = Z.zones(F, co, vn)
    kf = keel_field(F, co2, vn2, z)
    if kf is not None:
        pl, kfld, rib = kf
        kon = kfld['pid'] >= 0
        kh = kfld['h'] + 0.0012 * k * rib * kon
        h = np.where(kon, np.maximum(kh, 0.0), h)
        pid = np.where(kon, -1, pid)
        keel = (kon, kfld['ul'], kfld['rho'], rib)
    S.set_positions(ob, co2 + vn2 * h[:, None])
    on = pid >= 0
    S.add_attr(ob, 'peb_id', pid.astype(np.float64))
    S.add_attr(ob, 'peb_rim', np.where(on, f['rim'], 1.0))
    S.add_attr(ob, 'peb_top', np.where(on, f['top'], 0.0))
    if keel is not None:
        S.add_attr(ob, 'keel', keel[0].astype(np.float64))
        S.add_attr(ob, 'keel_ul', np.where(keel[0], keel[1], 0.0))
        S.add_attr(ob, 'keel_rho', np.where(keel[0], keel[2], 2.0))
        S.add_attr(ob, 'keel_rib', keel[3] * keel[0])
    C.log(f'{ob.name}: pebbles on {int(on.sum())} of {len(co)} vertices; relief up to {float(h.max()) * 1000:.1f} mm')
    _PLATES.clear()
    _PLATES.update({'n': len(co), 'plates': plates, 'pid': pid, 'rim': np.where(on, f['rim'], 1.0), 'top': np.where(on, f['top'], 0.0),
                    'keel': keel})
