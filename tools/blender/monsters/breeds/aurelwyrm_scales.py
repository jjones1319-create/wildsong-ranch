"""Aurelwyrm's skin (Art 2.1 Ultra; the lattice ported from coilfang_scales.py): the zones, the body's section, and the
relief carved into the high source.

  - Back and flanks: round golden scales in an offset lattice on the tube coordinates (NROWS round the body), each a
    shield rising toward its free edge at the tail's side so it overlaps the next (4-details panel 6), sized by the
    body's thickness and measured on the surface (the bends never stretch them).
  - Belly: wide cream chevron plates (their points toward the tail) up the front of the neck to the throat (4-details
    panel 4).
  - Head: small scales on the gold crown and the brow; the cream muzzle, cheeks and chin smooth (3-faces); the nose;
    the eyes' lids round the lenses; the mouth's soft crease.
The paint reads the attributes stored here (aurelwyrm_paint.py).
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

NROWS = 16                   # scales round the body (round 2: bigger, about 8 across a side: 4-details panel 6)
ASPECT = 1.0                 # a scale's length / its width (round)
PHI_B = 2.0                  # the belly plates start this far round from the spine's top (radians; +-: the cream underside)
SCUTE_K = 0.5                # a belly plate's length / the radius (4-details panel 4: broad chevrons)
PAT_L = 0.08                 # the argyle's half length at the thickest (metres)
PAT_W = math.radians(38.0)   # its half width round the body
_CACHE: dict = {}


# ============================================================================= tables along the body
def _tables():
    s = F.CUM
    r = F.radius(s)
    W = 2 * math.pi * r * (0.5 * (1 + F.SIDE_K)) / NROWS
    L = ASPECT * W
    u = np.concatenate([[0.0], np.cumsum(np.diff(s) * 2.0 / (0.5 * (L[1:] + L[:-1])))])
    pl = PAT_L * (r / F.RMAX) ** 0.7
    P = np.concatenate([[0.0], np.cumsum(np.diff(s) / (0.5 * (pl[1:] + pl[:-1])))])
    sl = SCUTE_K * np.maximum(r, 0.03)
    Wsc = np.concatenate([[0.0], np.cumsum(np.diff(s) / (0.5 * (sl[1:] + sl[:-1])))])
    return {'s': s, 'r': r, 'W': W, 'L': L, 'u': u, 'P': P, 'w': Wsc}


TAB = _tables()

# polish: the lattice laid by the centre line's length stretched the scales on the outside of the neck-to-body bend
# (the surface there is up to 1.7x longer than the axis) into diagonal streaks. As on a real snake, the lattice stays on
# the axis (no shear) but each scale keeps its own size on the surface: on a bend's outside skin opens between the
# scales, on its inside they crowd. The surface's arc-length factor at (s, phi) is 1 - r (radial . dT/ds).
NPHI = 96


def _surface_tables():
    s = F.CUM
    ds = np.diff(s)
    k = np.gradient(F.TAN, s, axis=0)
    ker = np.ones(9) / 9.0
    k = np.stack([np.convolve(k[:, j], ker, mode='same') for j in range(3)], axis=1)
    kD = (k * F.DORSAL).sum(axis=1)
    kL = (k * F.LEFT).sum(axis=1)
    phi = np.linspace(-math.pi, math.pi, NPHI + 1)
    r = TAB['r']
    fac = 1.0 - r[:, None] * (np.cos(phi)[None] * kD[:, None] + np.sin(phi)[None] * kL[:, None])
    fac = np.clip(fac, 0.25, 3.0)
    out = {'phi': phi, 'fac': fac}
    for key, den in (('u', 0.5 * TAB['L']), ('P', PAT_L * (r / F.RMAX) ** 0.7), ('w', SCUTE_K * np.maximum(r, 0.03))):
        g = fac / den[:, None]
        out[key] = np.vstack([np.zeros((1, NPHI + 1)), np.cumsum(0.5 * (g[1:] + g[:-1]) * ds[:, None], axis=0)])
    return out


TAB2 = _surface_tables()


def _at2(s: np.ndarray, phi: np.ndarray, key: str) -> np.ndarray:
    """A surface coordinate (u, P or w) at (s, phi): bilinear in the table, extended along s past the ends."""
    s = np.asarray(s, float)
    t = TAB['s']
    sc = np.clip(s, t[0], t[-1])
    fi = (np.asarray(phi, float) + math.pi) / (2 * math.pi) * NPHI
    j0 = np.clip(np.floor(fi).astype(np.int64), 0, NPHI - 1)
    a = np.clip(fi - j0, 0.0, 1.0)
    i1 = np.clip(np.searchsorted(t, sc, side='right'), 1, len(t) - 1)
    b = (sc - t[i1 - 1]) / np.maximum(t[i1] - t[i1 - 1], 1e-12)
    T = TAB2[key]
    v = ((T[i1 - 1, j0] * (1 - b) + T[i1, j0] * b) * (1 - a) + (T[i1 - 1, j0 + 1] * (1 - b) + T[i1, j0 + 1] * b) * a)
    # past the ends: the axis rate
    over = s - sc
    return v + over * (_at(s + 1e-3, key) - _at(s - 1e-3, key)) / 2e-3


def fac_at(s: np.ndarray, phi: np.ndarray) -> np.ndarray:
    """The surface's arc-length factor along the body at (s, phi): > 1 on a bend's outside, < 1 on its inside."""
    t = TAB['s']
    sc = np.clip(np.asarray(s, float), t[0], t[-1])
    fi = (np.asarray(phi, float) + math.pi) / (2 * math.pi) * NPHI
    j = np.clip(np.round(fi).astype(np.int64), 0, NPHI)
    i = np.clip(np.searchsorted(t, sc), 0, len(t) - 1)
    return TAB2['fac'][i, j]


def _rate(s: np.ndarray, phi: np.ndarray, key: str) -> np.ndarray:
    return (_at2(s + 0.002, phi, key) - _at2(s - 0.002, phi, key)) / 0.004


def _at(s: np.ndarray, key: str) -> np.ndarray:
    """A table along the body at s (extended linearly past the ends)."""
    s = np.asarray(s, float)
    t, y = TAB['s'], TAB[key]
    out = np.interp(s, t, y)
    lo, hi = s < t[0], s > t[-1]
    if lo.any():
        out[lo] = y[0] + (s[lo] - t[0]) * (y[1] - y[0]) / (t[1] - t[0])
    if hi.any():
        out[hi] = y[-1] + (s[hi] - t[-1]) * (y[-1] - y[-2]) / (t[-1] - t[-2])
    return out


def _tc(co: np.ndarray) -> dict:
    key = (len(co), float(co[:: max(1, len(co) // 97)].sum()))
    if _CACHE.get('key') != key:
        _CACHE.clear()
        _CACHE['key'] = key
        _CACHE['tc'] = F.tube_coords(co)
    return _CACHE['tc']


# ============================================================================= zones
def zones(co: np.ndarray) -> dict:
    tc = _tc(co)
    hw = F.head_w(co)
    tw = F.tube_w(co, tc)
    ed = F.eye_d(co)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    # (round 2) the belly ends before the tail's thin tip (a pale sliver showed past the fan)
    belly_t = smooth(PHI_B - 0.12, PHI_B + 0.06, np.abs(tc['phi'])) * tw * smooth(0.97 * F.S_TOT, 0.92 * F.S_TOT, tc['s'])
    # the face: the muzzle, round the eyes, the pale cheeks and chin
    snout = smooth(-1.2, -1.25, y) * (hw > 0.3)
    low = pale_face(co, hw)
    face = (snout > 0.5) | (ed < 2.0 * F.EYE_R) | (low > 0.5)
    muzzle = snout > 0.5
    mouth = MO.mouth_field(co)
    ear = F.ear_w(co)
    return {'face': face, 'muzzle': muzzle, 'eye_d': ed, 'head': hw > 0.5, 'hw': hw, 'tw': tw, 'belly_t': belly_t,
            'belly': belly_t > 0.5, 'low': low, 'snout': snout, 'mband': mouth['span'] * smooth(0.02, 0.0, np.abs(mouth['dz'])),
            's': tc['s'], 'phi': tc['phi'], 'ear': ear}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    k = (0.9 * z['face'] + 0.9 * z['muzzle'] + 1.0 * (z['eye_d'] < 1.8 * F.EYE_R) + 0.5 * z['head'] + 0.9 * z['mband']
         + 0.9 * (z['ear'] > 0.3) + 0.35 * smooth(0.05, 0.02, F.radius(np.clip(z['s'], 0, F.S_TOT))) * z['tw'])
    return np.clip(k, 0.0, 1.0)


def texel_k(fc: np.ndarray) -> np.ndarray:
    z = zones(fc)
    k = np.ones(len(fc))
    k = np.where(z['belly_t'] > 0.5, 0.8, k)
    k = np.where(z['head'], 1.5, k)
    k = np.where(z['face'], 1.9, k)
    k = np.where(z['eye_d'] < 1.6 * F.EYE_R, 2.2, k)
    k = np.where(z['mband'] > 0.05, 2.4, k)
    return k


def pale_face(co: np.ndarray, hw: np.ndarray) -> np.ndarray:
    """0..1 where the head is pale (the belly's cream): the muzzle's sides and the lips, the cheeks below the eyes, the
    chin and the throat; the nose's bridge stays gold down to the nose (3-faces neutral, 4-details panel 1)."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    above = z - MO.mouth_z(MO.mouth_theta(co))
    # (shape 2: lower: the muzzle's top and the face round the eyes gold, the cream below them)
    # (round 2: less cream on the cheeks)
    edge = 0.036 - 0.006 * smooth(-1.22, -1.32, y) - 0.03 * smooth(-1.06, -0.98, y)
    wob = (0.004 * np.sin(x * 80.0) + 0.003 * np.sin(y * 60.0 + 1.0)) * smooth(-1.1, -1.04, y)
    pale = smooth(0.012, -0.012, above - edge - wob)
    # the bridge: a gold band down the top of the muzzle to the nose
    bridge = smooth(0.042, 0.03, np.abs(x)) * smooth(1.245 + F.HDZ, 1.262 + F.HDZ, z)
    front = smooth(-1.0, -1.06, y)
    return pale * (1.0 - bridge) * smooth(0.2, 0.5, hw) * front


def brow(co: np.ndarray, hw: np.ndarray) -> np.ndarray:
    """0..1: the soft cream brow over each eye, sweeping up and out (4-details panel 2, 3-faces)."""
    out = np.zeros(len(co))
    for s in (1, -1):
        rx, ry, ze = F.eye_coords(co, s)
        out_ = rx * s
        arc = 1.3 + 0.18 * out_
        band = np.exp(-((ry - arc) / 0.22) ** 2) * smooth(-0.9, -0.5, out_) * smooth(1.5, 1.1, out_)
        out = np.maximum(out, band * (np.abs(ze) < 2.2 * F.EYE_R))
    return out * smooth(0.4, 0.7, hw)


def nose(co: np.ndarray) -> np.ndarray:
    """0..1: the small flat triangular nose pad on the muzzle's tip, wide at its top (round 3: a round button with
    forward nostrils read as a pig's nose; 4-details panel 1)."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2] - F.HDZ
    top, h = 1.268, 0.024
    t = np.clip((z - (top - h)) / h, 0.0, 1.0)
    half = 0.003 + 0.015 * t
    tri = smooth(half + 0.002, half - 0.001, np.abs(x)) * smooth(top - h - 0.002, top - h + 0.002, z) * smooth(top + 0.002, top - 0.002, z)
    return tri * smooth(-1.302, -1.312, y)


# ============================================================================= the lattice scales
def lattice(s: np.ndarray, phi: np.ndarray) -> dict:
    """The scale under each point: du, dv (-1..1 inside the rhombus; du + toward the tail), rho (0 centre .. 1 outline,
    corners rounded), the scale's centre (s, phi) and an id."""
    u = _at(s, 'u')
    v = phi * NROWS / math.pi
    a, b = 0.5 * (u + v), 0.5 * (u - v)
    ca, cb = np.round(a), np.round(b)
    da, db = a - ca, b - cb
    du, dv = da + db, da - db
    # each scale measured on the surface: stretched along the body by the bend's arc-length factor
    du = du * np.clip(fac_at(s, phi), 0.6, 2.2)
    da, db = 0.5 * (du + dv), 0.5 * (du - dv)
    # the rhombus is the unit square in (a, b): a rounded square there (p 5) rounds the scale's corners
    p = 2.4                 # a round scale (Coilfang's crisp rhombs used 5)
    rho = ((2 * np.abs(da)) ** p + (2 * np.abs(db)) ** p) ** (1.0 / p)
    uc = ca + cb
    vc = ca - cb
    phic = vc * math.pi / NROWS
    sc = np.interp(uc, TAB['u'], TAB['s'])
    sid = (ca.astype(np.int64) * 7919 + cb.astype(np.int64) * 104729) % 1000003
    return {'du': du, 'dv': dv, 'rho': rho, 's_c': sc, 'phi_c': phic, 'id': sid}


def argyle(s: np.ndarray, phi: np.ndarray) -> np.ndarray:
    """1 where (s, phi) falls in a dark diamond of the checker: dark on the spine's top (phi 0) and every second row of
    diamonds round the body, touching tip to tip; 0 in the light ones."""
    P = _at(s, 'P')
    Q = phi / PAT_W
    a, b = 0.5 * (P + Q), 0.5 * (P - Q)
    return np.zeros_like(np.asarray(a, float))           # no argyle: one gold all over


def scale_relief(tc: dict, tw: np.ndarray, belly_t: np.ndarray) -> dict:
    s, phi = tc['s'], tc['phi']
    lat = lattice(s, phi)
    W = _at(np.clip(s, 0, F.S_TOT), 'W')
    H = 0.06 * W
    du, dv, rho = lat['du'], lat['dv'], lat['rho']
    rise = 0.22 + 0.78 * np.clip((du + 1.0) * 0.5, 0, 1) ** 1.35
    edge = np.sqrt(np.clip(1.0 - np.clip(rho, 0, 1) ** 7, 0, 1))
    dome = 0.3 * (1.0 - np.clip(dv, -1, 1) ** 2)
    h = H * (rise * edge + dome * edge) - 0.18 * H * smooth(0.9, 1.05, rho)
    on = tw * (1.0 - belly_t)
    dark = argyle(lat['s_c'], lat['phi_c'])
    return {'h': h * on, 'rho': rho, 'du': du, 'id': lat['id'], 'dark': dark, 'on': on}


def scute_relief(tc: dict, tw: np.ndarray, belly_t: np.ndarray) -> dict:
    s, phi = tc['s'], tc['phi']
    off = np.pi - np.abs(phi)                         # 0 on the belly's middle
    # chevrons: each plate's edge runs back toward the tail at its sides, so its point leads (4-details panel 4)
    w = _at(s, 'w') + 1.35 * np.clip(off / (np.pi - PHI_B), 0, 1.2) ** 1.1      # round 2: deep V's (0.55 read as rings)
    fr = w - np.floor(w)
    r = F.radius(np.clip(s, 0, F.S_TOT))
    HB = 0.03 * r
    # round 2: each plate softly domed along and across, rising to its overlapping back edge (they read as a ribbed hose)
    across = 1.0 - 0.35 * (1.0 - smooth(PHI_B + 0.05, np.pi - 0.2, np.abs(phi)))
    h = HB * (0.18 + 0.82 * np.sin(np.clip(fr, 0, 1) * np.pi * 0.62) ** 1.1) * (1.0 - smooth(0.9, 1.0, fr)) * across         - 0.2 * HB * smooth(0.05, 0.0, fr)
    ends = smooth(PHI_B + 0.02, PHI_B + 0.16, np.abs(phi))
    on = belly_t
    return {'h': h * on * (0.4 + 0.6 * ends), 'fr': fr, 'id': np.floor(w), 'on': on, 'edge': (smooth(0.9, 1.0, fr) + smooth(0.08, 0.0, fr)) * on}
