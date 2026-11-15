"""Scrollopus's skin (Art 2.1 Ultra): the high source's carving and the attributes its paint reads (4-details panels 2,
3, 5, 6; 1-hero).
  - suckers: real cups on every tentacle's underside (two staggered rows, one toward the thin tips, smaller as the
    tentacle tapers): a raised rim, a shallow cup and a small pit in its middle; they run round the outsides of the
    curls, where the undersides roll outward;
  - the skin: fine papillae all over, soft rings across the tentacles' tops, a few soft folds where the head meets the
    tentacles and broad, very shallow undulations on the head (no balloon);
  - the face: a soft brow ridge over each eye, the sockets under the lenses (a closed lid 3 mm behind each, its lash
    line carved: the blink shows it), the upper lids' fold, and a small sly smile, its left corner a touch higher.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from lib import common as C
from lib import surface as S
from monsters.breeds import scrollopus_field as FL
from monsters.breeds import scrollopus_form as F
from monsters.breeds import scrollopus_noise as N

smooth = N.smooth
v3 = N.v3
_LAST: dict = {}


# ----------------------------------------------------------------------------- suckers
def _sucker_index(m: dict) -> np.ndarray:
    """Per centreline sample: the running count of sucker spacings from the root (n(s) = ∫ ds / spacing)."""
    rs = sucker_r(m['rad'])
    sp = SPACING * rs
    ds = np.diff(m['s'])
    inc = ds / np.maximum(0.5 * (sp[1:] + sp[:-1]), 1e-4)
    return np.concatenate([[0.0], np.cumsum(inc)])


SPACING = 2.05          # round 3 (review: 8-10 cups per curl, packed close)


def sucker_r(r):
    """Round 2 (review): big cups, about half the tentacle's width (two smaller rows where it is thick)."""
    two = smooth(0.05, 0.07, r)
    return r * (0.48 - 0.1 * two)


def suckers(co: np.ndarray, f: dict, share: np.ndarray) -> dict:
    T = F.tentacles()
    n = len(co)
    s = f['s']
    r = f['r']
    rs = sucker_r(r)
    sp = SPACING * rs
    nidx = np.zeros(n)
    for i, m in enumerate(T):
        sel = f['tid'] == i
        if sel.any():
            nidx[sel] = np.interp(np.clip(s[sel], 0, m['L']), m['s'], _sucker_index(m))
    phi = np.arctan2(f['su'], f['cu'])
    two = smooth(0.05, 0.07, r)
    rim = np.zeros(n)
    cup = np.zeros(n)
    pit = np.zeros(n)
    hl = np.zeros(n)
    h = np.zeros(n)
    for off, row_phi, amp in ((0.5, 0.42, 1.0), (0.0, -0.42, 1.0)):
        ph = row_phi * two
        a = amp * (two if off == 0.0 else 1.0)
        k = np.round(nidx - off)
        along = (nidx - off - k) * sp
        around = (phi - ph) * r
        d = np.sqrt(along ** 2 + around ** 2) / np.maximum(rs, 1e-4)
        # round 2: a raised, rimmed cup: a low collar, a crisp rim, a deep cup and a pit
        hh = (0.4 * smooth(1.14, 0.9, d) + 0.16 * np.exp(-((d - 0.8) / 0.1) ** 2) - 0.62 * smooth(0.68, 0.44, d)
              - 0.16 * smooth(0.2, 0.06, d))
        # one sucker in ten a little smaller, so the rows don't read as a stamp
        jit = 1.0 - 0.18 * (N.hash1((k * 7 + int(off * 2) + 1).astype(np.int64), 41) > 0.9)
        live = a * jit
        h = np.where(np.abs(hh * live) > np.abs(h), hh * live, h)
        rim = np.maximum(rim, live * smooth(1.12, 0.92, d) * smooth(0.6, 0.72, d))
        cup = np.maximum(cup, live * smooth(0.7, 0.5, d))
        pit = np.maximum(pit, live * smooth(0.22, 0.08, d))
        # round 3: a wet highlight on each cup's inner wall, all on the same side (one light)
        cosang = (0.6 * along - 0.8 * around) / np.maximum(d * rs, 1e-6)
        hl = np.maximum(hl, live * np.exp(-((d - 0.5) / 0.13) ** 2) * smooth(0.3, 0.85, cosang))
    # on the tube's own skin only (never the fused roots, where they smeared), past the root's bulge
    tube = smooth(0.42, 0.22, np.abs(f['d'] - r) / np.maximum(r, 1e-4))
    # round 3: from a little further out (the quill arm's root crumpled where the first cups met the webbing)
    on = share * tube * smooth(0.2, 0.28, s) * smooth(-0.2, 0.15, f['cu'])
    return {'h': h * rs * 0.78 * on, 'rim': rim * on, 'cup': cup * on, 'pit': pit * on, 'hl': hl * on}


# ----------------------------------------------------------------------------- the face
def eye_axes(s: int):
    from monsters.breeds import scrollopus_ultra as R
    c, xax, yax, look = R.eye_frame(s)
    return v3(c), v3(xax), v3(yax), v3(look)


def eye_socket(co: np.ndarray, vn: np.ndarray | None = None) -> np.ndarray:
    """Metres to move each vertex near an eye along its normal: inside the lens's outline the face becomes a dome 3 mm
    behind the lens (the closed lid), easing out into the cheek and the brow."""
    out = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_axes(s)
        q = co - c
        xe, ye, ze = q @ xax, q @ yax, q @ look
        rr = np.sqrt((xe / (F.EYE_R * F.EYE_SHAPE[0])) ** 2 + (ye / (F.EYE_R * F.EYE_SHAPE[1])) ** 2)
        lens = (np.sqrt(np.clip(1.0 - rr * rr, 0.0, 1.0)) * F.EYE_DEPTH[0] - F.EYE_DEPTH[1]) * F.EYE_R - 0.003
        blend = smooth(1.18, 0.98, rr) * (ze > -0.07) * (ze < 0.1)
        delta = (lens - ze) * blend
        if vn is not None:
            delta = delta / np.clip(vn @ look, 0.6, 1.0)
        delta = np.clip(delta, -0.05, 0.004)
        out = np.where(blend > 0, delta, out)
    return out


def lids(co: np.ndarray) -> dict:
    """The upper lid's fold over each lens's top (so the eye sits in the head), a thin lower rim, the brow ridge above,
    and the closed lid's lash line (hidden under the lens until a blink): metres of bulge and 0..1 masks."""
    from monsters.breeds import scrollopus_ultra as R
    up = np.zeros(len(co))
    lash = np.zeros(len(co))
    closed = np.zeros(len(co))
    brow = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_axes(s)
        q = co - c
        xe, ye, ze = (q @ xax) / F.EYE_R, (q @ yax) / (F.EYE_R * F.EYE_SHAPE[1]), q @ look
        r = np.sqrt(xe ** 2 + ye ** 2)
        # a soft window along the look axis (a hard one cut the brow ridge into steps: two slashes on the forehead)
        near = smooth(-0.11, -0.06, ze) * smooth(0.1, 0.07, ze)
        top = smooth(-0.3, 0.3, ye)
        b = 0.004 * smooth(0.93, 1.05, r) * smooth(1.55, 1.16, r) * top + 0.0018 * smooth(0.95, 1.03, r) * smooth(1.28, 1.07, r) * (1 - top)
        up = np.maximum(up, b * near)
        # the brow ridge: an arc over the eye, the left one (s = +1, toward the camera) higher and more arched (sly)
        u = xe * s
        arc = 1.62 + (0.2 if s > 0 else 0.08) + (0.22 if s > 0 else 0.12) * (1.0 - np.clip((u + 0.05) / 1.15, -1, 1) ** 2)
        bw = np.exp(-((ye - arc) / 0.28) ** 2) * smooth(-1.3, -0.9, u) * smooth(1.45, 1.05, u)
        brow = np.maximum(brow, bw * near)
        # the closed lid under the lens: a soft dome and its lash line (lowered to the lid's edge, curved)
        xn = np.clip(xe, -1.0, 1.0)
        la = (R.LID_EDGE - 0.08) - 0.22 * (1.0 - xn * xn) - 0.04
        on = (r < 1.06) & (ze > -0.03)
        lash = np.maximum(lash, np.exp(-((ye - la) / 0.06) ** 2) * on * smooth(1.04, 0.88, np.abs(xe)))
        closed = np.maximum(closed, np.clip(1.0 - r * r, 0.0, 1.0) * on)
    return {'up': up, 'lash': lash, 'closed': closed, 'brow': brow}


def eye_r(co: np.ndarray) -> np.ndarray:
    """The smaller of the two eyes' normalized radii (1 at a lens's outline), for points in front of the face."""
    out = np.full(len(co), 9.0)
    for s in (1, -1):
        c, xax, yax, look = eye_axes(s)
        q = co - c
        r = np.sqrt(((q @ xax) / (F.EYE_R * F.EYE_SHAPE[0])) ** 2 + ((q @ yax) / (F.EYE_R * F.EYE_SHAPE[1])) ** 2)
        out = np.minimum(out, np.where((q @ look) > -0.06, r, 9.0))
    return out


def mouth_z(x: np.ndarray) -> np.ndarray:
    """The smile's line: a soft curve, its left corner (toward the camera) lifted a little higher: sly."""
    xn = x / 0.046
    return F.MOUTH_C[2] + 0.011 * xn ** 2 + 0.005 * np.clip(xn, 0, None) ** 2


def mouth(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    front = (y < -0.2) & (np.abs(x) < 0.07)
    end = 0.044 + 0.004 * (x > 0)
    g = np.exp(-((z - mouth_z(x)) / 0.0026) ** 2) * smooth(end + 0.004, end - 0.006, np.abs(x)) * front
    # a small dimple at the left corner (the smirk), a fainter one at the right
    dl = np.sqrt(((x - 0.049) / 0.006) ** 2 + ((z - mouth_z(np.full(len(x), 0.048)) - 0.002) / 0.0055) ** 2)
    dr = np.sqrt(((x + 0.046) / 0.005) ** 2 + ((z - mouth_z(np.full(len(x), -0.045)) - 0.001) / 0.0045) ** 2)
    dimple = np.maximum(0.8 * smooth(1.0, 0.3, dl), 0.45 * smooth(1.0, 0.3, dr)) * front
    lip = np.exp(-((z - mouth_z(x) + 0.0065) / 0.004) ** 2) * smooth(end, end - 0.012, np.abs(x)) * front
    return np.maximum(g, dimple), lip


# ----------------------------------------------------------------------------- the skin's texture and folds
def papillae(co: np.ndarray) -> np.ndarray:
    # round 3 (4-details panel 6): bigger pebbles
    f1, f2, _id = N.voronoi(co, 0.009, 23, jitter=0.85)
    dome = np.sqrt(np.clip(1.0 - (f1 / 0.006) ** 2, 0.0, 1.0))
    return dome * (0.55 + 0.45 * smooth(-0.35, 0.25, N.fbm(co, 1 / 0.05, 24, 2)))


def droplets(co: np.ndarray) -> np.ndarray:
    """Round 2 (4-details panel 6): sparse round wet beads on the skin, a few millimetres across."""
    f1, _f2, fid = N.voronoi(co, 0.015, 25, jitter=0.9)
    keep = (np.abs(fid) % 7) < 4
    rad = 0.0028 + 0.0016 * ((np.abs(fid) % 5) / 4.0)
    return np.sqrt(np.clip(1.0 - (f1 / rad) ** 2, 0.0, 1.0)) * keep


def folds(co: np.ndarray, f: dict, share: np.ndarray) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    head = (1.0 - share) * smooth(0.0, 0.012, -F.mantle_sdf(co) + 0.012)
    # where the head meets the tentacles: two soft creases following the head's lower rim (not in front of the face)
    rim_d = F.mantle_sdf(co) - F.ell_sdf(co, F.CORE)
    front = smooth(-0.14, -0.2, y) * smooth(0.12, 0.06, np.abs(x))
    neck = (1.0 - share) * smooth(0.5, 0.42, z) * smooth(0.3, 0.36, z) * (1.0 - 0.8 * front)
    crease = 0.0 * neck * rim_d            # round 2: no crease under the head (it read as a neck)
    # broad shallow undulations on the head's back and top (a soft mantle, not a balloon)
    und = N.fbm(co, 1 / 0.07, 31, 2) * head * smooth(-0.05, 0.12, y + 0.08 * (z - 0.7))
    # soft rings across the tentacles' tops (fading on the underside and in the curls' tight turns)
    ring = np.zeros(len(co))
    if share.any():
        wave = 0.5 + 0.5 * np.cos(2 * math.pi * f['s'] / (0.85 * np.maximum(f['r'], 0.015) + 0.009))
        ring = smooth(0.55, 1.0, wave) * share * smooth(0.1, -0.3, f['cu']) * smooth(0.12, 0.2, f['s'])
    return {'crease': crease, 'und': und, 'ring': ring, 'head': head}


# ----------------------------------------------------------------------------- the carving
def fields(co: np.ndarray, vn: np.ndarray) -> dict:
    f = FL.nearest(co)
    share = FL.tentacle_share(co, f)
    sk = suckers(co, f, share)
    fo = folds(co, f, share)
    ld = lids(co)
    mg, lip = mouth(co)
    pap = papillae(co)
    drop = droplets(co)
    # round 2: the lilac underside the whole length of every tentacle (the lower half and a little more)
    under = share * smooth(-0.32, -0.1, f['cu'])
    # the oral side under the core (it shows between the roots from low angles)
    under = np.maximum(under, (1.0 - share) * smooth(0.27, 0.2, co[:, 2]) * smooth(0.16, 0.08, np.hypot(co[:, 0], co[:, 1])))
    return {'f': f, 'share': share, 'sk': sk, 'fo': fo, 'ld': ld, 'mouth': mg, 'lip': lip, 'pap': pap, 'under': under,
            'drop': drop}


ATTRS = ('share', 'under', 'rim', 'cup', 'pit', 'hl', 'tu', 'tid', 'crease', 'ring', 'lash', 'closed', 'brow', 'lip', 'pap', 'drop')


def carve(ob) -> None:
    co, vn = S.mesh_arrays(ob)
    A = fields(co, vn)
    sk, fo, ld = A['sk'], A['fo'], A['ld']
    disp = sk['h'].copy()
    # build 4: no papillae on the closed lids (the blink's lash line lies on a smooth dome)
    calm = np.clip(1.0 - 0.9 * sk['rim'] - 0.9 * sk['cup'], 0.0, 1.0) * smooth(1.05, 1.3, eye_r(co))
    disp += (0.0013 * A['pap'] + 0.0009 * A['drop']) * calm
    disp += -0.0007 * fo['ring'] - 0.0026 * fo['crease'] + 0.0016 * fo['und']
    disp += eye_socket(co, vn) + ld['up'] + 0.0022 * ld['brow']
    disp += -0.0026 * A['mouth'] + 0.0008 * A['lip']
    new = co + vn * disp[:, None]
    new[:, 2] = np.maximum(new[:, 2], 0.0)
    S.set_positions(ob, new)
    S.base_attrs(ob, co, {'mouth': A['mouth']})
    attrs = {'share': A['share'], 'under': A['under'], 'rim': sk['rim'], 'cup': sk['cup'], 'pit': sk['pit'], 'hl': sk['hl'],
             'tu': np.clip(A['f']['s'] / np.maximum(np.array([m['L'] for m in F.tentacles()])[A['f']['tid']], 1e-6), 0, 1),
             'tid': A['f']['tid'].astype(np.float64), 'crease': fo['crease'], 'ring': fo['ring'], 'lash': ld['lash'],
             'closed': ld['closed'], 'brow': ld['brow'], 'lip': A['lip'], 'pap': A['pap'], 'drop': A['drop'] * calm}
    for k, v in attrs.items():
        S.add_attr(ob, k, np.asarray(v, np.float64))
    _LAST.clear()
    _LAST.update({'n': len(co), 'co': co.copy(), 'mouth': A['mouth'].copy(), **{k: np.asarray(v).copy() for k, v in attrs.items()}})
    C.log(f'carve: {len(co)} vertices, {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm, '
          f'{int((A["share"] > 0.5).sum())} on tentacles, {int((sk["rim"] > 0.5).sum())} on sucker rims')


def carve_low(ob) -> None:
    """The low body takes the eye sockets and the lids' fold (the lenses sit flush on it too) and a part of the
    suckers' rims, so the curls' outlines show them."""
    co, vn = S.mesh_arrays(ob)
    f = FL.nearest(co)
    share = FL.tentacle_share(co, f)
    sk = suckers(co, f, share)
    disp = eye_socket(co, vn) + lids(co)['up'] + 1.0 * sk['h']        # round 2: the cups' rims in the outline
    new = co + vn * disp[:, None]
    new[:, 2] = np.maximum(new[:, 2], 0.0)
    S.set_positions(ob, new)
    C.log(f'carve_low: {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm')
