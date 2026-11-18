"""Aurelwyrm's carving (Art 2.1 Ultra; ported from coilfang_carve.py): the high source's relief (the round scales, the
belly's chevron plates, the crown's small scales, the lids and lashes round the lenses, the nostrils, the lips) and the
low body's large shapes (the section, the lids, the lips). Stores every attribute the paint reads (aurelwyrm_paint.py).
"""
from __future__ import annotations

import math

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.surface import smooth, v3
from monsters.breeds import aurelwyrm_form as F
from monsters.breeds import aurelwyrm_mouth as MO
from monsters.breeds import aurelwyrm_scales as SC


# ============================================================================= the head's small scales
def head_scales(co: np.ndarray, vn: np.ndarray, hw: np.ndarray, face: np.ndarray, seed: int = 41) -> dict:
    """Round 3: the whole head scaled (1-hero, 3-faces, 4-details panel 1): small shingled scales on the crown and the
    cheeks, larger plates on the snout and along both lips, pointing back from the snout; none right round the eyes or
    on the mouth's line. The back of the head carries the body's lattice instead (aurelwyrm_scales.nape)."""
    from monsters.breeds import hearthwing_parts as HP
    y, z = co[:, 1], co[:, 2]
    dz = z - MO.mouth_z(MO.mouth_theta(co))
    pale = SC.pale_face(co, hw)
    on = (hw > 0.25) & (F.eye_d(co) > 1.3 * F.EYE_R) & (np.abs(dz) > 0.005) & (y < -0.985) & (pale < 0.3) & (F.ear_w(co) < 0.2)
    sp = 0.0105 + 0.003 * smooth(-1.18, -1.28, y)
    sp = np.where(on, sp, np.nan)
    flow = co - v3((0.0, -1.42, 1.25 + F.HDZ))
    flow = flow - vn * (flow * vn).sum(axis=1, keepdims=True)
    flow /= np.maximum(np.linalg.norm(flow, axis=1, keepdims=True), 1e-9)
    plates = U.plate_layout(co, vn, sp, sp * 0.64, sp * 0.065, seed=seed, flow=flow, aspect=1.15, wobble=0.08)
    f = HP.shingle_field(co, vn, plates, leaf=0.35)
    k = hw * smooth(-0.985, -1.015, y) * smooth(0.5, 0.2, pale)
    on_s = f['pid'] >= 0
    h = (f['h'] - 0.0004 * smooth(0.85, 1.0, f['rho']) * on_s) * k
    return {'h': h, 'pid': np.where(on_s, f['pid'], -1), 'rho': np.where(on_s, f['rho'], 2.0), 'k': k, 'n': len(plates['c'])}


# ============================================================================= the eyes' lids, the nostrils
LID_DROP = 0.1              # the closed lid's lash line bows down this much in its middle (lens units)
CLOSED_AT = -0.2            # ... from this height at its ends (where a blink squeezes the lens to)
# round 2: bolder, longer lashes flicking out and up at the outer corner, visible from the front
# (round 2b: kept to the outer corner, flicking out: strokes over the top read as angry brows)
# (polish: on the upper lid's edge, flicking up and out at its outer end; strokes behind the eye read as crow's feet)
LASHES = ((40.0, 0.34), (56.0, 0.4), (72.0, 0.32))      # (angle up from the outer corner, length in lens units)


def eye_field(co: np.ndarray) -> dict:
    """Round each lens: a soft upper lid rolling over its top (a fleshy rim, thicker toward the outer corner), a thin
    lower lid; the dark lash line along the upper rim with three lashes flicking out at the outer corner (3-faces,
    4-details panel 2); under the lens the closed lid's curved lash line a blink shows."""
    n = len(co)
    disp, lid, lash, closed, rim = (np.zeros(n) for _ in range(5))
    for s in (1, -1):
        rx, ry, ze = F.eye_coords(co, s)
        r = np.sqrt(rx * rx + ry * ry)
        near = (r < 2.0) & (ze > -0.9 * F.EYE_R) & (ze < 1.6 * F.EYE_R)
        if not near.any():
            continue
        out = rx * s
        up = smooth(-0.35, 0.35, ry / np.maximum(r, 1e-6))
        outer = smooth(-0.2, 0.9, out)
        # round 2: a low soft lid (a raised rim with a dark ring read as goggles)
        roll = (0.001 + 0.0006 * outer) * np.exp(-((r - 1.08) / (0.1 + 0.04 * outer)) ** 2) * up
        lower = 0.0006 * np.exp(-((r - 1.06) / 0.06) ** 2) * (1.0 - up)
        crease = -0.0008 * np.exp(-((r - 1.42) / 0.06) ** 2) * up * smooth(1.0, 0.4, np.abs(rx))
        disp += (roll + lower + crease) * near
        lid = np.maximum(lid, np.exp(-((r - 1.12) / 0.16) ** 2) * up * near)
        ln = np.exp(-((r - 1.02) / (0.032 + 0.03 * outer)) ** 2) * smooth(0.05, 0.4, ry / np.maximum(r, 1e-6)) * near
        fl = np.zeros(n)
        for ang, ln_ in LASHES:
            a = math.radians(ang)
            p0 = np.array((math.cos(a), math.sin(a)))
            d = np.array((math.cos(a - 0.45), math.sin(a - 0.45)))
            q = np.stack([out - p0[0], ry - p0[1]], axis=1)
            t = np.clip(q @ d / ln_, 0.0, 1.0)
            dist = np.linalg.norm(q - (t * ln_)[:, None] * d[None], axis=1)
            fl = np.maximum(fl, smooth(0.1 * (1.0 - 0.8 * t) + 0.012, 0.0, dist) * (1.0 - 0.2 * t))
        lash = np.maximum(lash, np.maximum(ln, fl * smooth(-0.1, 0.0, out)) * near)
        disp += 0.0006 * fl * near
        cl = smooth(1.02, 0.94, r) * near * (ze < 0.6 * F.EYE_R)
        arc = CLOSED_AT - LID_DROP * (1.0 - np.clip(rx, -1, 1) ** 2)
        closed = np.maximum(closed, np.exp(-((ry - arc) / (0.075 + 0.03 * outer)) ** 2) * cl * smooth(1.02, 0.88, np.abs(rx)))
        rim = np.maximum(rim, np.exp(-((r - 1.06) / 0.08) ** 2) * (1.0 - up) * near)
    return {'disp': disp, 'lid': lid, 'lash': np.clip(lash, 0, 1), 'closed': closed, 'rim': rim}


NOSTRILS = [(0.008, -1.322, 1.246 + F.HDZ), (-0.008, -1.322, 1.246 + F.HDZ)]    # round 3: tiny, under the pad      # small, at the nose's front (4-details panel 1)


def nostrils(co: np.ndarray) -> np.ndarray:
    out = np.zeros(len(co))
    for c in NOSTRILS:
        d = np.linalg.norm((co - v3(c)) / v3((1.3, 1.0, 0.8)), axis=1)
        out = np.maximum(out, smooth(0.0034, 0.0012, d))
    return out


# ============================================================================= carving
_LAST: dict = {}


def shape(ob) -> tuple[np.ndarray, dict, np.ndarray]:
    """The large shapes both bodies share: the section (a touch flatter belly, wider flanks); it floats, so nothing
    meets the ground."""
    co, _vn = S.mesh_arrays(ob)
    tc = SC._tc(co)
    tw = F.tube_w(co, tc)
    new = F.reshape(co, tc, tw)
    S.set_positions(ob, new)
    return co, tc, tw


def carve(ob) -> None:
    co0, tc, tw = shape(ob)
    co, vn = S.mesh_arrays(ob)
    z = SC.zones(co0)
    hw = z['hw']
    # the body's scales run on up the back of the neck into the back of the head (under the mane)
    sw = np.maximum(tw, hw * smooth(-1.04, -0.99, co0[:, 1]))
    sr = SC.scale_relief(tc, sw, z['belly_t'])
    sc = SC.scute_relief(tc, tw, z['belly_t'])
    hs = head_scales(co, vn, hw, z['face'])
    E = eye_field(co)
    Mo = MO.mouth_field(co)
    nos = nostrils(co)
    disp = sr['h'] + sc['h'] + hs['h'] + E['disp'] + Mo['disp'] - 0.0012 * nos
    from monsters.breeds import bloatoad_noise as N
    peb = N.fbm(co, 1 / 0.004, 77, 2) * z['face'] * (1.0 - smooth(0.4, 0.8, Mo['span']))
    disp = disp + 0.00018 * peb
    new = co + vn * disp[:, None]
    S.set_positions(ob, new)
    S.base_attrs(ob, co, {'mouth': Mo['mouth']})
    belly = np.clip(z['belly_t'] + SC.pale_face(co, hw), 0, 1)
    cell = np.floor(co / 0.004).astype(np.int64)
    hsh = ((cell[:, 0] * 73856093) ^ (cell[:, 1] * 19349663) ^ (cell[:, 2] * 83492791)) % 1000 / 1000.0
    glit = (hsh > 0.93) * (sr['on'] > 0.5) * (sr['rho'] < 0.9)
    attrs = {'glit': glit.astype(np.float64), 'tw': sw, 'hw': hw, 'belly': belly, 'scale_rho': np.where(sr['on'] > 0.5, sr['rho'], 2.0), 'scale_du': sr['du'],
             'scale_id': (sr['id'] % 9973) / 9972.0, 'dark': sr['dark'] * sr['on'], 'scute_fr': sc['fr'], 'scute_on': sc['on'],
             'scute_edge': sc['edge'], 'scute_id': (np.abs(sc['id']) * 37 % 101) / 100.0,
             'hscale': (hs['pid'] >= 0) * hs['k'], 'hrho': hs['rho'], 'hid': U.plate_hash(hs['pid'], 9),
             'lid': E['lid'], 'lash': E['lash'], 'closed': E['closed'], 'rim': E['rim'], 'nostril': nos, 'lip': Mo['lip'],
             'mdz': np.where(Mo['span'] > 0.01, Mo['dz'], 0.1), 'mspan': Mo['span'], 'mcorner': Mo['corner'],
             's_body': np.clip(tc['s'], -0.5, F.S_TOT + 0.5), 'phi_body': tc['phi'], 'brow': SC.brow(co, hw),
             'snout': z['snout'], 'nose': SC.nose(co), 'ear': z['ear'], 'ear_in': F.ear_inner(co, vn)}
    for k, v in attrs.items():
        S.add_attr(ob, k, np.asarray(v, np.float64))
    _LAST.clear()
    _LAST.update({'n': len(co), 'co': co.copy(), **{k: np.asarray(v).copy() for k, v in attrs.items()}})
    C.log(f'carve: the body {F.S_TOT:.2f} m from the back of the head to the tail tip ({F.S_TOT + 0.37:.2f} m from the snout)')
    C.log(f'carve: {len(co)} vertices; relief {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm; '
          f'{int((sr["on"] > 0.5).sum())} on the lattice scales, {int((sc["on"] > 0.5).sum())} on the scutes, {hs["n"]} head scales')


def carve_low(ob) -> None:
    shape(ob)
    co, vn = S.mesh_arrays(ob)
    E = eye_field(co)
    Mo = MO.mouth_field(co)
    new = co + vn * (0.8 * E['disp'] + Mo['disp'] - 0.0008 * nostrils(co))[:, None]
    S.set_positions(ob, new)
    C.log('carve_low: the section, the lids, the lips and the nostrils')
