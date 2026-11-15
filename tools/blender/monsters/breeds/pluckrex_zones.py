"""Pluckrex's zones: the masks the paint, the pebbles and the weights read (pluckrex_body.Form + the form's 'cream'
numbers). `zones(F, p, n)`: p the points (the skin before carving), n their normals or None. Metres; -Y is the front."""
from __future__ import annotations

import numpy as np

from lib.surface import smooth, v3
from monsters.breeds.pluckrex_form import mirror, polyline_param, sd_parts, seg_dist

_CACHE: list = []


def _key(p: np.ndarray, n) -> tuple:
    return (id(None) if n is None else 1, p.shape, float(p[::max(1, len(p) // 251)].sum()), float(p[-1].sum()),
            float(p[len(p) // 2].sum()))


def zones(F, p: np.ndarray, n: np.ndarray | None = None) -> dict:
    p = np.asarray(p, np.float64)
    if len(p) < 20000:
        return _zones(F, p, n)
    key = (id(F),) + _key(p, n)
    for kk, v in _CACHE:
        if kk == key:
            return v
    z = _zones(F, p, n)
    _CACHE.append((key, z))
    del _CACHE[:-6]
    return z


def _mouth(F, p: np.ndarray, n, head: np.ndarray) -> dict:
    r, phi, _pu, _pl = F.mouth_coords(p)
    k = F.k
    ax = np.abs(p[:, 0])
    pu0, pl0, rl, ri = F.mouth_smooth(ax)
    # smooth limits (the nearest-sample grid made a sawtooth gum line on the lips)
    # polish: never past the corners or the lips (red hairlines on the cream cheek)
    open_ = head & (rl > 0) & (r < rl) & (r > ri + 0.002 * k) & (p[:, 1] < F.HINGE[1] + 0.01 * k)
    mid = 0.5 * (pu0 + pl0)
    ang = open_ & (phi > pu0 - 9.0) & (phi < pl0 + 9.0)
    if n is not None:
        a = np.radians(phi)
        ephi = np.stack([np.zeros(len(p)), np.sin(a), -np.cos(a)], axis=1)
        dn = (n * ephi).sum(1)
        upper = ang & (phi < mid) & (dn > 0.2)
        lower = ang & (phi >= mid) & (dn < -0.2)
    else:
        upper = ang & (phi < mid)
        lower = ang & (phi >= mid)
    inside = upper | lower
    depth = np.where(inside, rl - r, 0.0)       # metres behind the lips
    hw = F.mouth_half_width()
    # round 2: the tongue fills the floor (the reviewer: a maroon slab with studs, no tongue)
    tongue = lower * smooth(0.92 * hw, 0.7 * hw, np.abs(p[:, 0])) * smooth(0.003 * k, 0.01 * k, depth)
    throat = inside * smooth(0.05 * k, 0.1 * k, depth)
    lip = inside * smooth(0.004 * k, 0.001 * k, depth)
    mouth_w = inside * smooth(0.0, 0.003 * k, depth)
    # round 3: a cream upper lip under the blue (hero, grown-4 panel 1): a band just above the palate's rim, outside
    a_ = np.radians(pu0)
    z_rim = F.HINGE[2] - r * np.sin(a_)
    ulip = head & ~inside & (rl > 0) & (r < rl + 0.012 * k) & (r > ri) & (p[:, 1] < F.HINGE[1]) & (p[:, 2] > z_rim - 0.004 * k)
    ulip = ulip * smooth(0.016 * k, 0.008 * k, p[:, 2] - z_rim)
    return {'mouth_in': inside, 'mouth_w': mouth_w, 'upper_lip': ulip, 'palate': upper, 'floor': lower, 'tongue': tongue, 'throat_in': throat, 'lip_in': lip,
            'mouth_depth': depth, 'm_r': r, 'm_phi': phi, 'm_mid': np.where(open_, mid, np.nan)}


def _cream(F, p: np.ndarray, n, z: dict) -> np.ndarray:
    """0..1: the cream skin (the lower jaw and the cheeks under the eyes, the throat and the neck's front, the chest
    and belly, the tail's underside, the patch under the tail, the soles and palms; 2-turnaround, 4-details panel 6)."""
    Cr = F.G['cream']
    k = F.k
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    out = np.zeros(len(p))
    head = z['head']
    # the lower jaw's outside (below the grin)
    # the lower jaw's front and underside only (round 2: from behind, its sides showed as white lumps)
    lowj = (sd_parts(p, F.lower_parts()) < 0.005 * k) & head & ~z['mouth_in'] & (y < F.HINGE[1] - 0.01 * k)
    out = np.maximum(out, lowj * 1.0)
    # the cheeks: under the eyes, the line falling to the lip at the snout
    zl = Cr['lip_z'] + (Cr['cheek_z'] - Cr['lip_z']) * smooth(Cr['snout_w'] * 0.55, Cr['snout_w'] * 1.15, ax)
    zl = zl - (Cr['cheek_z'] - Cr.get('cheek_out_z', Cr['cheek_z'])) * smooth(Cr['snout_w'] * 1.35, Cr['snout_w'] * 2.4, ax)
    cheek = head & (y < F.HEAD_C[1] + Cr.get('cheek_back', 0.35) * F.HEAD_R[1]) & ~z['mouth_in']
    out = np.maximum(out, cheek * smooth(zl + 0.006 * k, zl - 0.006 * k, zz))
    # the throat and the neck's front: facing forward round the neck's axis
    a, b = v3(Cr['neck_axis'][0]), v3(Cr['neck_axis'][1])
    d, t = seg_dist(p, a, b)
    c = a + t[:, None] * (b - a)
    rad = p - c
    rad[:, 2] *= 0.25
    rn = rad / np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-9)
    fwd = -rn[:, 1]
    neck = (d < Cr['neck_r']) & (zz > a[2] - 0.02 * k) & (zz < b[2] + 0.02 * k) & ~head
    out = np.maximum(out, neck * smooth(Cr['neck_cos'] - 0.08, Cr['neck_cos'] + 0.08, fwd))
    # under the chin, round to the neck (the throat under the jaw)
    out = np.maximum(out, head * (zz < Cr['lip_z'] - 0.02 * k) * smooth(-0.1, 0.15, fwd) * (y < F.HINGE[1] + 0.1 * k))
    # the chest and the belly: a front oval
    (cz, hz), wx = Cr['belly'], Cr['belly_w']
    wzx = np.interp(zz, [cz - hz, cz, cz + hz], wx)
    e = (x / wzx) ** 2 + ((zz - cz) / hz) ** 2
    front = (y < Cr['belly_y']) if n is None else ((y < Cr['belly_y']) & (n[:, 1] < 0.5))
    out = np.maximum(out, front * smooth(1.08, 0.92, e) * ~head)
    # the tail's underside
    tt, td, tr = z['tail_t'], z['tail_d'], z['tail_r']
    cz_t = np.interp(tt, np.linspace(0, 1, len(F.TAIL_PTS)), [q[2] for q in F.TAIL_PTS])
    under = z['tail'] * smooth(Cr['tail_under'] + 0.1, Cr['tail_under'] - 0.1, (zz - cz_t) / np.maximum(tr, 1e-3))
    out = np.maximum(out, under * smooth(0.02, 0.12, tt) * smooth(0.95, 0.8, tt))     # the tip blue (no cream pinch)
    # the patch under the tail's root, between the thighs (2-turnaround back)
    uc, ur = Cr['under']
    e2 = np.linalg.norm((p - v3(uc)) / v3(ur), axis=1)
    out = np.maximum(out, smooth(1.08, 0.9, e2))
    # soles, toes' undersides and palms
    sx = abs(F.G['arm']['shoulder'][0])
    out = out * (1.0 - ((z['arm'] | z['hand']) & (ax > sx * 1.15)).astype(float))      # round 3: never the chest's sides
    out = np.maximum(out, z['upper_lip'])
    out = np.maximum(out, np.maximum(z['sole'], z['palm']))
    return np.clip(out, 0.0, 1.0)


def _zones(F, p: np.ndarray, n) -> dict:
    G, k = F.G, F.k
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    np_ = len(p)
    hsd = sd_parts(p, F.head_parts())
    head = (hsd < 0.012 * k) & ((zz > F.HINGE[2] - 0.13 * k) | (y < F.HINGE[1] - 0.06 * k))
    face = head & (y < F.HEAD_C[1] - 0.25 * F.HEAD_R[1])
    eye_d = np.minimum(np.linalg.norm(p - v3(F.EYE_C[1]), axis=1), np.linalg.norm(p - v3(F.EYE_C[-1]), axis=1))
    muzzle = head & (sd_parts(p, F.upper_parts() + F.lower_parts()) < 0.008 * k)
    z = {'head': head, 'face': face, 'eye_d': eye_d, 'muzzle': muzzle, 'head_sd': hsd}
    z.update(_mouth(F, p, n, head))
    A, L = G['arm'], G['leg']
    hand = np.zeros(np_, bool)
    palm = np.zeros(np_)
    arm = np.zeros(np_, bool)
    finger = np.zeros(np_, bool)
    foot = np.zeros(np_, bool)
    toes = np.zeros(np_, bool)
    sole = np.zeros(np_)
    leg = np.zeros(np_, bool)
    for s in (1, -1):
        w, h, _ac, pl = F.hand_frame(s)
        hc = v3(w + h * (A['palm_len'] * 0.6))
        hr = A['palm_len'] + max(A['finger_len']) + 0.01 * k
        near = (np.linalg.norm(p - hc, axis=1) < hr) & ((p - v3(w)) @ v3(h) > -0.01 * k) & (np.sign(x) == s)
        hand |= near
        palm = np.maximum(palm, near * smooth(0.0, 0.25, (n @ v3(pl)) if n is not None else np.zeros(np_)) *
                          smooth(0.003 * k, -0.002 * k, (p - hc) @ v3(-pl)))
        for b, t, r in F.fingers(s):
            dd, _t = seg_dist(p, b, t)
            finger |= (dd < r + 0.006 * k) & (np.sign(x) == s)
        dA, _t = seg_dist(p, mirror(A['shoulder'], s), mirror(A['wrist'], s))
        arm |= (dA < A['r'][0] + 0.03 * k) & (x * s > abs(A['shoulder'][0]) * 0.75)
        fc = v3(mirror(L['foot'][0], s))
        fr = v3(L['foot'][1])
        inf = (zz < L['ankle'][2] + 0.03 * k) & (np.linalg.norm((p - fc) / (fr * v3((1.5, 1.4, 3.0))), axis=1) < 1.0)
        foot |= inf
        for t in F.toe_centres(s):
            toes |= np.linalg.norm((p - v3(t)) / (v3(L['toe_r']) * 1.6), axis=1) < 1.0
        sole = np.maximum(sole, inf * smooth(0.016 * k, 0.004 * k, zz) * ((n[:, 2] < -0.3) if n is not None else 1.0))
        dl, _t = seg_dist(p, mirror(L['hip'], s), mirror(L['ankle'], s))
        leg |= (dl < 0.13 * k) & (x * s > 0.03 * k) & (zz < L['hip'][2] + 0.05 * k)
    arm &= ~hand
    leg &= ~foot
    tt, td, tr = F.tail_param(p)
    tail = (tt > 0.05) & (td < tr * 1.5 + 0.015 * k) & ~foot & ~leg & (y > G['tail']['pts'][0][1] - 0.02 * k)
    tail &= np.abs(x) < tr * 1.15 + 0.01 * k        # polish: never the backs of big thighs (cream patches on grown)
    z.update({'hand': hand, 'palm': palm * hand, 'finger': finger, 'arm': arm, 'foot': foot, 'toes': toes & foot,
              'paw': foot | hand, 'sole': sole, 'leg': leg, 'tail': tail, 'tail_t': tt, 'tail_d': td, 'tail_r': tr})
    z['cream'] = _cream(F, p, n, z)
    # the back's band (bigger pebbles along the spine; the dorsal spines stand on it)
    cz_t = np.interp(tt, np.linspace(0, 1, len(F.TAIL_PTS)), [q[2] for q in F.TAIL_PTS])
    bk = smooth(0.1 * k, 0.04 * k, np.abs(x)) * (y > F.G['back_y'](zz)) * ~head
    bk = np.where(tail, smooth(0.07 * k, 0.03 * k, np.abs(x)) * (zz > cz_t + 0.2 * tr), bk)
    z['back'] = np.clip(bk, 0.0, 1.0) * (1.0 - z['cream'])
    return z
