"""Reefclaw's limb relief and build (Art 2.1 Ultra): carve the high limb pieces (dense pebbles of varied size, cuff
rings between the plated segments, the coral's pores as real pits with raised rims, so the normal map and the AO show
them instead of painted dots) and return their paint fields; build every high and game limb piece.
"""
from __future__ import annotations

import numpy as np

from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import reefclaw_form as F
from monsters.breeds import reefclaw_geo as G
from monsters.breeds import reefclaw_limbs as L
from monsters.breeds import reefclaw_pieces as PC


def coral_mask(co: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(coral 0..1, tip paleness 0..1, the knobs' outer caps 0..1) on the big claw."""
    near = np.zeros(len(co))
    for a, b, ra, rb in L.coral()['tubes']:
        d, t = F._seg_dist(co, a, b)
        r = ra + (rb - ra) * t
        near = np.maximum(near, smooth(r * 1.55, r * 1.02, d))
    tipk, cap = np.zeros(len(co)), np.zeros(len(co))
    for p, r, dr in L.coral_tips(True):
        d = np.linalg.norm(co - p, axis=1)
        near = np.maximum(near, smooth(r * 2.0, r * 1.1, d))
        tipk = np.maximum(tipk, smooth(0.03, 0.0, d - r))
        cap = np.maximum(cap, smooth(r * 1.6, r * 1.05, d) * smooth(0.1, 0.55, ((co - p) @ dr) / r))
    return np.clip(near, 0, 1), np.clip(tipk, 0, 1), np.clip(cap, 0, 1)


def _craters(co: np.ndarray, cell: float, seed: int, r: tuple[float, float], chance: float) -> tuple[np.ndarray, np.ndarray]:
    """(displacement in units of the pore's radius, the pit's darkness 0..1): a pit with a raised rim per cell."""
    f1, _f2, h = F.cells(co, cell, seed)
    rad = r[0] + (r[1] - r[0]) * ((h * 7.31) % 1.0)
    on = h < chance
    q = f1 / rad
    pit = np.sqrt(np.clip(1.0 - q ** 2, 0.0, 1.0)) * on
    rim = np.exp(-((q - 1.15) / 0.22) ** 2) * on
    return (-0.85 * pit + 0.22 * rim) * rad, pit


def relief(ob, name: str, joints: list, leg) -> dict:
    co, vn = S.mesh_arrays(ob)
    n = len(co)
    up = vn[:, 2]
    outer = smooth(-0.55, 0.15, up)
    peb, ph = F.bumps(co, 0.011, 61, (0.0018, 0.0045), 0.75)
    big, bh = F.bumps(co + 0.11, 0.026, 67, (0.004, 0.0075), 0.45)
    prad = 0.0018 + 0.0027 * ((ph * 7.31) % 1.0)
    brad = 0.004 + 0.0035 * ((bh * 7.31) % 1.0)
    disp = np.maximum(peb * 0.5 * prad, big * 0.6 * brad) * outer
    tuber = np.maximum(big, peb * (ph < 0.25)) * outer
    joint = np.zeros(n)
    for p in joints:
        joint = np.maximum(joint, smooth(0.055, 0.035, np.linalg.norm(co - v3(p), axis=1)))
    under = smooth(0.1, -0.55, up)
    tip = coral = ctip = pore = tooth = ccap = np.zeros(n)
    if leg is not None:
        a, b, sh = leg
        _d, t = F._seg_dist(co, a, b)
        if sh is not None:
            tip = smooth(0.6, 0.66, t)                     # the long curved dactyl: darker, smooth and glossy
            tuber = tuber * (1 - tip)
            disp = disp * np.where(tip > 0.5, 0.2, 1.0)
    if name == 'clawR':
        # round 3 (review): the palm and the fixed finger are one porous coral mass (pits everywhere), the fronds coral
        # with smaller, denser pits toward their pale tips; only the wrist stays shell
        fr, ctip, ccap = coral_mask(co)
        wrist = smooth(0.11, 0.07, np.linalg.norm(co - v3(L.ARMS['R']['wrist']), axis=1))
        coral = np.clip(1.0 - wrist, 0.0, 1.0)
        d1, p1 = _craters(co, 0.017, 71, (0.004, 0.0085), 0.8)
        d2, p2 = _craters(co - 0.07, 0.0085, 73, (0.0016, 0.0032), 0.75)
        big = 1.0 - fr                                      # the big pits on the mass, the small ones on the fronds
        cdisp = np.where(p1 * big > 0.01, d1, d2) * (1.0 - 0.75 * ctip)
        pore = np.maximum(p1 * big, p2) * (1.0 - 0.75 * ctip)
        disp = disp * (1 - coral) + coral * cdisp
        pore = pore * coral
        tuber = tuber * (1 - coral)
    if name in ('clawL', 'clawR', 'pincerL', 'pincerR'):
        spec = L.SMALL if name.endswith('L') else L.BIG
        key = 'dactyl' if name.startswith('pincer') else 'fixed'
        pts = spec[key]
        d0, t0 = F._seg_dist(co, pts[0], pts[1])
        d1_, t1 = F._seg_dist(co, pts[1], pts[2])
        t = np.where(d0 < d1_, 0.5 * t0, 0.5 + 0.5 * t1)
        near = smooth(spec[f'{key}_r'][0] * 1.7, spec[f'{key}_r'][0] * 1.0, np.minimum(d0, d1_))
        tip = smooth(0.6, 0.95, t) * near * (1 - 0.6 * coral)
        for p, r in L.teeth(name):
            tooth = np.maximum(tooth, smooth(r * 1.6, r * 0.8, np.linalg.norm(co - p, axis=1)))
    G.displace(ob, disp)
    return {'tuber': tuber, 'under': under, 'joint': joint, 'tip': tip, 'coral': coral, 'pore': pore, 'ctip': ctip,
            'tooth': tooth, 'ccap': ccap}


def objects(high: bool, quick: bool) -> list:
    out = []
    pre = 'hi' if high else 'lo'
    for name, pid, parts, joints, tris, leg in PC.pieces():
        ob = G.solid(f'{pre}_{name}', parts, high, quick, tris)
        if high:
            G.tag(ob, pid, kind=1.0 if pid >= 50 else 0.0, **relief(ob, name, joints, leg))
        else:
            G.tag(ob, pid)
        out.append(ob)
    return out
