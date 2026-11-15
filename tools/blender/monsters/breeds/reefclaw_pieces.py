"""Reefclaw's limb pieces (Art 2.1 Ultra): the voxel parts of every rigid leg, arm and claw segment (layout in
reefclaw_limbs.py). Round 3 (review: lathe-turned sausages with washer rings): each segment is a flattened, rounded box
whose far end flares a little where the next segment tucks in under it, like armour plates; a knuckle at each joint;
the legs end in a long, curved, pointed dactyl.
"""
from __future__ import annotations

import numpy as np

from lib.surface import v3
from monsters.breeds import reefclaw_geo as G
from monsters.breeds import reefclaw_limbs as L


def _plate(prefix: str, a, b, thin: float, broad: float, pn) -> list:
    """Polish (review: flat planks and stepped flanges): a rounded, slightly flattened shell tube from a to b, swelling
    a little toward its far end and tapering into the next segment there (no flat faces, no flange)."""
    a, b = v3(a), v3(b)
    d = b - a
    return [G.ell_seg(prefix, a, b, thin, broad, pn, 0.016),
            G.ell_seg(prefix + 'swell', a + 0.3 * d, b + 0.03 * d, thin * 1.07, broad * 1.06, pn, 0.0)]


def _curve(prefix: str, pts, r: tuple[float, float], segs: int = 6) -> list:
    """A tapering tube along a quadratic curve through 3 points (a dactyl, a claw finger), ending in a point."""
    p0, p1, p2 = (v3(p) for p in pts)
    out = []
    prev = p0
    for k in range(1, segs + 1):
        t = k / segs
        q = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * (2 * p1 - 0.5 * (p0 + p2)) + t ** 2 * p2
        ra = r[0] + (r[1] - r[0]) * (k - 1) / segs
        rb = r[0] + (r[1] - r[0]) * k / segs
        out.append(G.tube(f'{prefix}{k}', prev, q, ra, rb))
        prev = q
    return out


def leg_pieces(i: int, s: int) -> list[tuple]:
    h, k, a = L.leg_points(i, s)
    tag = 'L' if s > 0 else 'R'
    pn = G.unit(np.cross(k - h, a - k))
    sh = a - k
    up = G.unit(np.cross(pn, G.unit(k - h)))
    if up[2] < 0:
        up = -up
    # polish: the joint balls stay inside the segments' ends (they read as rivets when they stood out)
    thigh = [G.ball('hip', h, 0.03)] + _plate('merus', h, k, 0.036, 0.052, pn) + [G.ball('knee', k, 0.03)]
    out_dir = G.unit(v3((s * 1.0, 0.0, 0.0)) - pn * float(pn @ v3((s * 1.0, 0.0, 0.0))))
    da = k + 0.6 * sh
    dmid = da + 0.5 * (a - da) + out_dir * 0.022
    shin = [G.ball('knee2', k, 0.028)] + _plate('carpus', k, k + 0.3 * sh, 0.034, 0.048, pn) + \
        _plate('propodus', k + 0.27 * sh, k + 0.62 * sh, 0.032, 0.045, pn) + \
        _curve('dactyl', [da, dmid, a], (0.034, 0.006)) + [G.ball('toe', a, 0.007)]
    pid = (10 if s > 0 else 20) + i + 1
    return [(f'leg{i + 1}{tag}', pid, thigh, [h, k], L.LEG_TRIS[0], (h, k, None)),
            (f'shin{i + 1}{tag}', pid + 20, shin, [k, k + 0.3 * sh, k + 0.62 * sh], L.LEG_TRIS[1], (k, a, sh))]


def arm_pieces(tag: str) -> list[tuple]:
    A = {k: v3(v) for k, v in L.ARMS[tag].items()}
    at, ab, ft, fb = L.ARM_SIZE[tag]
    pn = G.unit(np.cross(A['elbow'] - A['shoulder'], A['wrist'] - A['elbow']))
    base = 50 if tag == 'L' else 60
    arm = [G.ball('sh', A['shoulder'], 0.8 * at)] + _plate('merus', A['shoulder'], A['elbow'], at, ab, pn) + \
        [G.ball('el', A['elbow'], 0.8 * ft)]
    fore = [G.ball('el2', A['elbow'], 0.78 * ft)] + _plate('carpus', A['elbow'], A['wrist'], ft, fb, pn) + \
        [G.ball('wr', A['wrist'], 0.9 * fb)]
    tri = L.ARM_TRIS[tag]
    return [(f'arm{tag}', base + 1, arm, [A['shoulder'], A['elbow']], tri[0], None),
            (f'forearm{tag}', base + 2, fore, [A['elbow'], A['wrist']], tri[1], None)]


def claw_pieces(tag: str) -> list[tuple]:
    base = 50 if tag == 'L' else 60
    W = v3(L.ARMS[tag]['wrist'])
    c = L.SMALL if tag == 'L' else L.BIG
    P = v3(c['palm'])
    palm = [G.ball('wr', W, 0.06 if tag == 'L' else 0.075), G.ell_seg('palm', W, 2 * P - W, c['palm_r'][0], c['palm_r'][1], c['flat'], 0.0),
            G.ball('bulb', P, c['bulb'])]
    palm += _curve('fix', c['fixed'], c['fixed_r'], 7)
    palm += [G.ball(f't{j}', p, r) for j, (p, r) in enumerate(L.teeth(f'claw{tag}'))]
    if tag == 'R':
        palm += [G.tube(f'co{j}', a, b, ra, rb) for j, (a, b, ra, rb) in enumerate(L.coral()['tubes'])]
        palm += [G.ball(f'kn{j}', p, r) for j, (p, r) in enumerate(L.coral_tips())]
        rng = np.random.default_rng(77)
        for j, (p, r, d) in enumerate(L.coral_tips(True)):          # knobbly: a couple of little nubs at each tip
            for k in range(1 + j % 2):
                q = p + G.unit(d + rng.normal(0.0, 0.8, 3)) * r * 0.8
                palm.append(G.ball(f'nub{j}_{k}', q, r * rng.uniform(0.4, 0.55)))
    dact = [G.ball('hinge', c['hinge'], c['dactyl_r'][0] * 0.95)] + _curve('dac', c['dactyl'], c['dactyl_r'], 7)
    dact += [G.ball(f't{j}', p, r) for j, (p, r) in enumerate(L.teeth(f'pincer{tag}'))]
    tri = L.ARM_TRIS[tag]
    return [(f'claw{tag}', base + 3, palm, [W], tri[2], None), (f'pincer{tag}', base + 4, dact, [v3(c['hinge'])], tri[3], None)]


def pieces() -> list[tuple]:
    out = []
    for s in (1, -1):
        for i in range(len(L.LEGS)):
            out += leg_pieces(i, s)
    for tag in ('L', 'R'):
        out += arm_pieces(tag) + claw_pieces(tag)
    return out
