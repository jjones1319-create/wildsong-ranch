"""Moatshell's skin (Art 2.1 Ultra): the high source's carving and the attributes its paint reads.
  - leathery skin in pebbly scales (a Voronoi of cells sized by region: big on the legs' pillars, small on the cheeks
    and neck; domed, with grooves between): 1-hero, 4-details panels 1-3;
  - the cream plastron in scutes (a midline and cross seams), the bib up the chest (level seams), the throat's folds;
  - the face: a smooth cream beak-like snout with two nostrils, a closed smile curling up at the corners, the brow
    folds, the sockets under the lenses (a closed lid 3 mm behind each: the blink shows it, with its lash line);
  - the four big nails on each foot, set off by a groove.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from monsters.breeds import moatshell_noise as N
from monsters.breeds import moatshell_ultra as R

smooth = N.smooth
v3 = N.v3
MOUTH_AXIS_Y = -0.6
# round 1: a wider smile curling up into the cheeks, under the new broad muzzle
MOUTH_TH = [0.0, 15.0, 30.0, 42.0, 52.0, 60.0, 66.0]
MOUTH_Z = [0.502, 0.504, 0.509, 0.518, 0.531, 0.547, 0.564]       # polish: the ends lifted into the cheeks
NOSTRILS = [(0.019, -0.696, 0.558), (-0.019, -0.696, 0.558)]
_LAST: dict = {}


def mouth_theta(p: np.ndarray) -> np.ndarray:
    return np.degrees(np.arctan2(p[:, 0], -(p[:, 1] - MOUTH_AXIS_Y)))


def mouth_z(th: np.ndarray) -> np.ndarray:
    return np.interp(np.abs(th), MOUTH_TH, MOUTH_Z)


def snout_mask(co: np.ndarray) -> np.ndarray:
    """0..1 on the smooth cream beak: the snout and the chin's front."""
    a = smooth(0.02, -0.008, N.ell_sdf(co, R.SNOUT[0], v3(R.SNOUT[1]) * 1.1))
    b = smooth(0.01, -0.004, N.ell_sdf(co, R.CHIN[0], v3(R.CHIN[1]) * 1.1)) * smooth(-0.6, -0.64, co[:, 1])
    return np.clip(np.maximum(a, b) * smooth(-0.6, -0.635, co[:, 1]), 0.0, 1.0)


def jaw_mask(co: np.ndarray) -> np.ndarray:
    """0..1: the lower beak below the mouth line (weight on `jaw`), fading out behind the chin."""
    th = mouth_theta(co)
    mz = mouth_z(th)
    w = smooth(0.0, 0.004, mz - co[:, 2]) * smooth(62.0, 54.0, np.abs(th)) * smooth(-0.585, -0.628, co[:, 1])
    w = w * smooth(0.425, 0.455, co[:, 2]) * (N.ell_sdf(co, R.CHIN[0], (0.12, 0.11, 0.085)) < 0)
    return np.clip(w, 0.0, 1.0)


def mouth_groove(co: np.ndarray) -> np.ndarray:
    th = mouth_theta(co)
    near = N.ell_sdf(co, (0.0, -0.63, 0.525), (0.15, 0.12, 0.085)) < 0
    g = np.exp(-((co[:, 2] - mouth_z(th)) / 0.0032) ** 2) * smooth(66.0, 58.0, np.abs(th)) * near * (co[:, 1] < -0.6)
    # polish: a small dimple at each end of the smile, up in the cheek
    d = np.sqrt(((np.abs(th) - 65.0) / 3.2) ** 2 + ((co[:, 2] - (mouth_z(np.full(len(co), 66.0)) + 0.002)) / 0.0042) ** 2)
    g = np.maximum(g, 0.75 * smooth(1.0, 0.35, d) * near)
    return g


def eye_axes(s: int):
    c, xax, yax, look = R.eye_frame(s)
    return v3(c), v3(xax), v3(yax), v3(look)


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens: the closed lid (a soft bulge) and its lash line, curved; hidden until a blink sinks the lens."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_axes(s)
        q = co - c
        xe, ye, ze = q @ xax, q @ yax, q @ look
        ax_, ay_ = R.EYE_R * R.EYE_SHAPE[0], R.EYE_R * R.EYE_SHAPE[1]
        r2 = (xe / ax_) ** 2 + (ye / ay_) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax_ * R.LID_W)
        arc = -(R.LID_LASH + R.LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * R.EYE_R
        th = 0.0022 + 0.0014 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def eye_socket(co: np.ndarray, vn: np.ndarray | None = None) -> np.ndarray:
    """Metres to move each vertex near an eye along its normal: inside the lens's outline the face becomes a dome 3 mm
    behind the lens (the closed lid), easing out into the cheek and the brow (never pulled forward much)."""
    out = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_axes(s)
        q = co - c
        xe, ye, ze = q @ xax, q @ yax, q @ look
        r = np.sqrt((xe / (R.EYE_R * R.EYE_SHAPE[0])) ** 2 + (ye / (R.EYE_R * R.EYE_SHAPE[1])) ** 2)
        lens = (np.sqrt(np.clip(1.0 - r * r, 0.0, 1.0)) * R.EYE_DEPTH[0] - R.EYE_DEPTH[1]) * R.EYE_R - 0.003
        blend = smooth(1.16, 0.98, r) * (ze > -0.06) * (ze < 0.1)
        delta = (lens - ze) * blend
        if vn is not None:
            delta = delta / np.clip(vn @ look, 0.6, 1.0)
        delta = np.clip(delta, -0.05, 0.004)
        out = np.where(blend > 0, delta, out)
    return out


def lid_fold(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The heavy upper lid's fold round the top of each lens (it overlaps the lens's rim, so the eye sits in the head,
    1-hero, 4-details panel 2), a thinner lower rim, and the crease above the fold: (bulge metres, crease 0..1)."""
    up = np.zeros(len(co))
    crease = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_axes(s)
        q = co - c
        xe, ye, ze = q @ xax, q @ yax, q @ look
        Rr = R.EYE_R
        r = np.sqrt((xe / Rr) ** 2 + (ye / (Rr * R.EYE_SHAPE[1])) ** 2)
        near = (ze > -0.04) & (ze < 0.05)
        top = smooth(-0.35, 0.25, ye / Rr)
        b = 0.0048 * smooth(0.93, 1.06, r) * smooth(1.62, 1.18, r) * top + 0.0022 * smooth(0.95, 1.04, r) * smooth(1.32, 1.08, r) * (1 - top)
        up = np.maximum(up, b * near)
        crease = np.maximum(crease, np.exp(-((r - 1.66) / 0.07) ** 2) * smooth(0.15, 0.55, ye / Rr) * near)
    return up, crease


def scale_size(co: np.ndarray, z: dict) -> np.ndarray:
    """Scale size (metres) by region (round 1): big pebbles on the legs, small on the head, face and neck."""
    ld = R.leg_dist(co)
    s = np.full(len(co), 0.026)
    s = np.where(ld < 0.14, 0.032, s)
    s = np.where((ld < 0.14) & (co[:, 2] < 0.1), 0.021, s)
    nk = N.seg_dist(co, (0.0, -0.24, 0.3), (0.0, -0.5, 0.5))[0] < 0.135
    s = np.where(nk & (ld > 0.12), 0.0155, s)
    s = np.where(z['head'], 0.018, s)
    s = np.where(z['head'] & (co[:, 1] < -0.6), 0.014, s)
    s = np.where(N.poly_dist(co, R.TAIL) < 0.07, 0.018, s)
    return s


def scales(co: np.ndarray, s: np.ndarray, seed: int = 7) -> dict:
    """Round 1: domed, rounded pebble scales with soft valleys between them (the crisp groove network read as cracked
    mud). Cells come from a Voronoi over p / s, so they scale with the region's size; each cell rises as a dome from its
    walls to its centre (rho 0 at the centre → 1 at a wall)."""
    q = co / s[:, None]
    f1, f2, fid = N.voronoi(q, 1.0, seed, jitter=0.8)
    wq = 0.5 * (f2 - f1)
    # round pebbles: a dome of radius ~0.46 cell round each seed, never past its cell's walls; the corners between
    # pebbles are the soft valleys (Voronoi walls alone read as cracked mud)
    rr = f1 / 0.66
    dome = np.sqrt(np.clip(1.0 - rr ** 3, 0.0, 1.0)) * smooth(0.0, 0.1, wq)
    rho = 1.0 - dome
    w = wq * s
    sid = (np.abs(fid) % 9973) / 9972.0
    return {'w': w, 'rho': rho, 'dome': dome, 'valley': smooth(0.6, 0.97, rho), 'sid': sid}


def plate_seams(co: np.ndarray, z: dict) -> tuple[np.ndarray, np.ndarray]:
    """Round 1: (seam 0..1, bevel 0..1). The plastron's scutes (a midline and cross seams underneath, level seams up the
    chest) are bevelled plates: each slopes down over about 9 mm into a thin seam. The throat gets soft broad creases."""
    x, y, zz = co[:, 0], co[:, 1], co[:, 2]
    d = np.full(len(co), 1.0)
    und = z['under']
    d = np.where(und, np.minimum(d, np.abs(x)), d)
    for yc in (-0.3, -0.15, 0.02, 0.18, 0.31):
        d = np.where(und, np.minimum(d, np.abs(y - yc - 0.03 * (x / 0.3) ** 2)), d)
    bib = z['bib'] & ~und
    for zc in (0.27, 0.325, 0.38):
        d = np.where(bib, np.minimum(d, np.abs(zz - zc + 0.02 * (x / 0.18) ** 2)), d)
    d = np.where(bib & (zz < 0.36), np.minimum(d, np.abs(x)), d)
    plate = und | bib
    seam = np.exp(-(d / 0.0018) ** 2) * plate
    bevel = (1.0 - smooth(0.0, 0.009, d)) * plate
    _d, t = N.seg_dist(co, (0.0, -0.24, 0.3), (0.0, -0.5, 0.5))
    fold = 0.5 + 0.5 * np.cos(t * 2 * np.pi * 7.0)
    crease = smooth(0.55, 1.0, fold) * z['throat_w'] * smooth(0.8, 0.6, t) * ~plate
    return np.maximum(seam, 0.35 * crease), np.maximum(bevel, crease)


def carve(ob) -> None:
    co, vn = S.mesh_arrays(ob)
    z = R.zones(co, vn)
    cream = z['cream']                       # soft under the chin (round 2: no hard seam)
    beak = snout_mask(co)
    nail = smooth(0.003, -0.003, R.toe_dist(co))
    s = scale_size(co, z)
    sc = scales(co, s)
    # the muzzle and the skin round the eyes stay smooth (fading out into the scales)
    scaly = (1.0 - cream) * (1.0 - beak) * (1.0 - nail) * smooth(0.06, 0.085, z['eye_d'])
    depth = np.where(R.leg_dist(co) < 0.14, 0.0026, 0.0019)
    d_scale = (depth * (sc['dome'] - 1.0) - 0.0005 * (1.0 - smooth(0.0, 0.0011, sc['w']))) * scaly
    seams, bevel = plate_seams(co, z)
    d_plate = (-0.0035 * bevel - 0.0008 * seams + 0.0005 * N.fbm(co, 1 / 0.03, 31, 2)) * cream
    mg = mouth_groove(co)
    nos = np.zeros(len(co))
    for c in NOSTRILS:
        nos = np.maximum(nos, smooth(0.0055, 0.002, np.linalg.norm(co - v3(c), axis=1)))
    nb = np.exp(-(R.toe_dist(co) / 0.0022) ** 2) * (R.toe_dist(co) > -0.004)
    bulge, lash = closed_lid(co)
    fold, crease = lid_fold(co)
    speck = smooth(0.0016, 0.0006, N.voronoi(co, 0.007, 41)[0]) * smooth(-0.1, 0.4, N.fbm(co, 1 / 0.04, 42, 2))
    grain = N.fbm(co, 1 / 0.003, 43, 2)
    disp = d_scale + d_plate - 0.0034 * mg - 0.003 * nos - 0.0022 * nb - 0.0012 * lash + eye_socket(co, vn) + fold - 0.0016 * crease
    disp = disp + (0.00022 * grain - 0.0006 * speck) * (beak + nail) + 0.00015 * grain * scaly
    new = co + vn * disp[:, None]
    new[:, 2] = np.maximum(new[:, 2], 0.0)
    S.set_positions(ob, new)
    S.base_attrs(ob, co, {'mouth': mg})
    attrs = {'sid': sc['sid'], 'sgroove': sc['valley'] * scaly, 'stop': sc['dome'] * scaly, 'cream': cream, 'beak': beak,
             'nail': nail, 'seam': seams * cream, 'nostril': nos, 'lash': lash, 'lid': bulge, 'speck': speck, 'crease': crease,
             'bevel': bevel * cream}
    for k, v in attrs.items():
        S.add_attr(ob, k, np.asarray(v, np.float64))
    _LAST.clear()
    _LAST.update({'n': len(co), 'base': co.copy(), **{k: np.asarray(v).copy() for k, v in attrs.items()}, 'mouth': mg})
    C.log(f'carve: {len(co)} vertices, height {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm, '
          f'{int((cream > 0.5).sum())} cream, {int((scaly > 0.5).sum())} scaly')


def carve_low(ob) -> None:
    """The low body takes the eye sockets, so the lenses sit flush on it too."""
    co, vn = S.mesh_arrays(ob)
    disp = eye_socket(co, vn) + lid_fold(co)[0]
    new = co + vn * disp[:, None]
    new[:, 2] = np.maximum(new[:, 2], 0.0)          # flat soles on the ground
    S.set_positions(ob, new)
    C.log(f'carve_low: sockets {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm')
