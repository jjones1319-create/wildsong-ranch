"""Scrollopus's held things (Art 2.1 Ultra; 1-hero, 2-turnaround, 4-details panel 4), each rigid on its tentacle's
last bone:
  - the scroll: parchment rolled in three turns (the spiral shows at its ragged ends), a loose outer edge, bound by a
    cord in three wraps with a gold wax seal stamped with a leaf;
  - the quill: a steel nib with its slit, a gold holder with raised rings, the shaft, and a curved feather vane with
    real notches in its edges, cream with a violet tip;
  - the book: two leather covers opened a little at the fore-edge, a rounded spine with raised bands, the page block
    between them and a few pages fanning at the top; gold corner pieces.
Every piece carries `pk` (its kind) and `w2` (a coordinate along or across it). Metres; the monster faces −Y.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import scrollopus_form as F
from monsters.breeds import scrollopus_geo as G
from monsters.breeds import scrollopus_noise as N

smooth = N.smooth
v3 = N.v3

PK = {'paper': 20, 'scord': 21, 'seal': 22, 'nib': 30, 'holder': 31, 'shaft': 32, 'vane': 33,
      'cover': 40, 'pages': 41, 'gold': 42, 'spine': 43, 'leaf': 44}


def _frame(axis):
    a = F._unit(axis)
    e1 = F._unit(np.cross(a, (0.0, 0.0, 1.0)) if abs(a[2]) < 0.9 else np.cross(a, (1.0, 0.0, 0.0)))
    e2 = np.cross(a, e1)
    return a, e1, e2


# ----------------------------------------------------------------------------- the scroll
def scroll_paper(high: bool):
    """Round 2 (review: a smooth butter tube): parchment rolled in three turns, its loose outer edge and both ends
    deckled (torn, uneven), the spiral showing at the ends. The game mesh rolls its outer turn and a quarter the same
    way over a solid core (the inner turns bake onto the core's ends)."""
    c, a, L, R = F.SCROLL['c'], F.SCROLL['axis'], F.SCROLL['len'], F.SCROLL['r']
    a, e1, e2 = _frame(a)
    up = F.perp_dir((0.0, -0.35, 1.0), a)          # the loose outer edge lies on its top-front
    side = np.cross(a, up)
    turns, r_in = 3.0, 0.018
    t = 0.0013 if high else 0.0026
    th_max = 2 * math.pi * turns
    th0 = 0.0 if high else 2 * math.pi * (turns - 1.3)
    nu, nv = (240, 80) if high else (44, 9)
    U, X = np.meshgrid(np.linspace(0.0, 1.0, nu + 1), np.linspace(-0.5, 0.5, nv + 1), indexing='ij')
    # the outer edge torn: where the sheet ends varies along the scroll's length
    xs = np.stack([X.ravel() * 6.0, np.full(X.size, 1.3), np.full(X.size, 0.4)], axis=1)
    tear = (0.36 * (0.5 + 0.5 * N.fbm(xs, 1.0, 93, 3)) + 0.1 * (0.5 + 0.5 * N.fbm(xs * 4.0, 1.0, 94, 1))).reshape(X.shape)
    TH = th0 + (th_max - tear - th0) * U
    rr = r_in + (R - 0.5 * t - r_in) * TH / th_max
    lift = 0.011 * smooth(th_max - 1.6, th_max, TH) ** 1.5          # round 3: the outer lip curls up off the roll
    ang = TH + 0.6
    # the ends deckled: each turn's end edge uneven
    ends = np.stack([np.cos(ang).ravel() * 3.0, np.sin(ang).ravel() * 3.0, TH.ravel() * 0.4], axis=1)
    rag = (0.0035 * N.fbm(ends, 2.2, 91, 3)).reshape(X.shape)
    xx = X * L + np.sign(X) * smooth(0.42, 0.5, np.abs(X)) * rag
    P = c[None, None] + a * xx[..., None] + (rr + lift)[..., None] * (np.cos(ang)[..., None] * up + np.sin(ang)[..., None] * side)
    nrm = np.cos(ang)[..., None] * up + np.sin(ang)[..., None] * side
    sh = G.thick_sheet(P.reshape(-1, 3), nrm.reshape(-1, 3), nu, nv, t)
    n = (nu + 1) * (nv + 1)
    w2 = np.concatenate([np.abs(X).ravel() * 2] * 2)
    turn = np.concatenate([(TH / th_max).ravel()] * 2)
    edge = np.concatenate([smooth(th_max - tear - 0.35, th_max - tear, TH).ravel()] * 2)
    pcs = [G.piece(sh['v'], sh['f'], pk=PK['paper'], w2=w2, turn=turn, edge=edge, back=np.concatenate([np.zeros(n), np.ones(n)]))]
    if not high:
        # the core inside the outer turns: closed, its ends where the inner turns' spiral bakes
        r_core = r_in + (R - r_in) * th0 / th_max - t
        pts = np.array([c - a * (0.5 * L - 0.001), c + a * (0.5 * L - 0.001)])
        core = G.tube(pts, r_core, 16)
        pcs.append(G.tag(core, pk=PK['paper'], w2=1.0, turn=0.3, edge=0.0, back=0.0))
    return pcs


def scroll_cord(high: bool) -> list[dict]:
    c, a, R = F.SCROLL['c'], F.SCROLL['axis'], F.SCROLL['r']
    a, e1, e2 = _frame(a)
    up = F.perp_dir((0.0, -0.35, 1.0), a)
    side = np.cross(a, up)
    centre = c - a * 0.075
    pcs = []
    for k in range(3):
        u = np.linspace(0, 2 * math.pi, 64 if high else 30)
        off = (k - 1) * 0.0105
        ring = centre[None] + a[None] * (off + 0.003 * np.sin(u))[:, None] + (R + 0.0035) * (np.cos(u)[:, None] * up + np.sin(u)[:, None] * side)
        pc = G.tube(ring, 0.0052, 10 if high else 7, cap=True)
        pcs.append(G.tag(pc, pk=PK['scord'], w2=float(k) / 2))
    # the seal: a gold disc on the front-top of the binding, a leaf stamped in it (carved by the paint's relief)
    sn = F._unit(0.55 * up - 0.83 * side if (0.55 * up - 0.83 * side)[1] < 0 else 0.55 * up + 0.83 * side)
    sc = centre + sn * (R + 0.008)
    disc = np.array([sc - sn * 0.004, sc + sn * 0.002, sc + sn * 0.0045])
    pc = G.tube(disc, np.array([0.025, 0.023, 0.016]), 32 if high else 12)
    sa = F._unit(np.cross(sn, a))
    sb = np.cross(sn, sa)
    q = pc['v'] - sc[None]
    pcs.append(G.tag(pc, pk=PK['seal'], w2=0.0, su=(q @ sa) / 0.025, sv=(q @ sb) / 0.025))
    return pcs


# ----------------------------------------------------------------------------- the quill
def quill_parts(high: bool) -> list[dict]:
    a = F.QUILL['axis']
    _a, e1, e2 = _frame(a)
    face = F.perp_dir((0.25, -1.0, 0.0), a)            # the vane faces front, turned a little toward its right
    across = np.cross(a, face)
    pcs = []
    # the nib: a pointed steel blade with a slit (slit carved by the paint's relief)
    kk = np.array([0.0, 0.008, 0.02, 0.034, 0.047])
    pts = np.array([F.quill_point(k) for k in kk])
    pcs.append(G.tag(G.tube(pts, np.array([0.0012, 0.004, 0.0075, 0.0098, 0.0105]), 16 if high else 6), pk=PK['nib'], w2=0.0))
    # the gold holder: a waisted tube with raised rings at both ends and in the middle
    hk = np.linspace(0.045, 0.2, 90 if high else 12)
    hr = F.QUILL['r'] * (1.0 + 0.12 * np.exp(-((hk - 0.06) / 0.006) ** 2) + 0.12 * np.exp(-((hk - 0.185) / 0.007) ** 2)
                         + 0.08 * np.exp(-((hk - 0.125) / 0.005) ** 2) - 0.08 * smooth(0.07, 0.12, hk) * smooth(0.18, 0.14, hk))
    if high:
        # round 2: engraved rings round the ferrule (fine grooves between the raised bands)
        hr = hr * (1.0 - 0.07 * smooth(0.55, 0.95, np.cos(2 * math.pi * (hk - 0.045) / 0.013)) * smooth(0.075, 0.09, hk) * smooth(0.175, 0.16, hk))
    hr[-1] *= 0.7
    pcs.append(G.tag(G.tube(np.array([F.quill_point(k) for k in hk]), hr, 28 if high else 10), pk=PK['holder'], w2=0.0))
    # the shaft and the vane, bending out (toward its right, away from the head) as they rise
    k0, k1 = F.QUILL['vane']
    sk = np.linspace(0.19, k1 + 0.01, 60 if high else 14)
    bend = 0.045 * ((sk - 0.19) / (k1 - 0.19)) ** 2
    out = F.perp_dir((-1.0, 0.0, 0.0), a)
    spts = np.array([F.quill_point(k) for k in sk]) + bend[:, None] * out[None]
    pcs.append(G.tag(G.tube(spts, np.linspace(0.0055, 0.0018, len(sk)), 10 if high else 5), pk=PK['shaft'], w2=0.0))
    nu, nv = (220, 22) if high else (72, 4)
    for side in (1, -1):
        uu = np.linspace(0.0, 1.0, nu + 1)
        vv = np.linspace(0.0, 1.0, nv + 1)
        Uu, Vv = np.meshgrid(uu, vv, indexing='ij')
        k = k0 + (k1 - k0) * Uu
        width = (0.078 if side > 0 else 0.064) * np.sin(np.pi * np.clip(Uu, 0, 1) ** 0.75) ** 0.8 * (1.0 - 0.25 * Uu)
        # notches: a few V-gaps where the barbs part (real geometry, so they read in silhouette)
        notch = np.zeros_like(Uu)
        # round 2: many small partings where the barbs separate (a feathery edge, not a cut-out), a few deeper
        # round 3 (review: a sawtooth cut-out): only three soft partings; the barbs are fine grooves and lines
        for j, uc in enumerate((0.34, 0.58, 0.77)):
            uc = uc + (0.04 if side < 0 else 0.0)
            dep = 0.28
            notch = np.maximum(notch, dep * np.exp(-((Uu - uc - 0.07 * Vv) / 0.011) ** 2) * Vv ** 1.8)
        wv = width * Vv * (1.0 - notch)
        bk = 0.045 * ((k - 0.19) / (k1 - 0.19)) ** 2
        base = np.array([F.quill_point(kv) for kv in k.ravel()]).reshape(k.shape + (3,)) + bk[..., None] * out
        # the barbs sweep up toward the tip and the vane curls back a little at its edge
        P = base + (side * wv)[..., None] * across + (0.35 * wv)[..., None] * a - (0.34 * wv * Vv)[..., None] * face
        if high:
            # the barbs: fine grooves slanting from the shaft toward the tip (the same lines prop_material paints)
            q = (Uu - 0.12 * Vv) * 520.0 / (2 * math.pi)
            P = P + (0.0007 * np.sin(2 * math.pi * q) * smooth(0.05, 0.2, Vv))[..., None] * face
        nrm = np.broadcast_to(face, P.shape)
        sh = G.thick_sheet(P.reshape(-1, 3), np.ascontiguousarray(nrm).reshape(-1, 3), nu, nv, 0.0022 if high else 0.003)
        n = (nu + 1) * (nv + 1)
        w2 = np.concatenate([Vv.ravel(), Vv.ravel()])
        along = np.concatenate([Uu.ravel(), Uu.ravel()])
        pcs.append(G.piece(sh['v'], sh['f'] if side > 0 else sh['f'][:, ::-1], pk=PK['vane'], w2=w2, along=along,
                           vside=float(side), back=np.concatenate([np.zeros(n), np.ones(n)])))
    return pcs


# ----------------------------------------------------------------------------- the book
def _place(L: np.ndarray, origin, ex, ey, ez) -> np.ndarray:
    return origin[None] + L[:, :1] * ex[None] + L[:, 1:2] * ey[None] + L[:, 2:3] * ez[None]


def book_parts(high: bool) -> list[dict]:
    """Round 2 (review: a closed block held edge-on): the book open in a V about its spine (its spine outward, the
    pages toward its face), each cover with its half of the page block, a fan of loose pages between them."""
    c, f, across, up = F.book_frame()
    h, w = F.BOOK['h'], F.BOOK['w']
    spine = c - across * (0.5 * w)
    half = math.radians(0.5 * F.BOOK['open'])
    pcs = []
    step = 0.006 if high else 0.045
    for side in (1, -1):
        dirc = F._unit(across * math.cos(half) + side * f * math.sin(half))
        out = F._unit(np.cross(up, dirc))
        out = out if float(out @ (side * f)) > 0 else -out          # the cover's outer face, away from the pages
        # the cover: a leather board 8 mm thick, a little larger than its pages
        box = G.rounded_box((0.5 * w + 0.005, 0.5 * h + 0.006, 0.0042), 0.0032, step, 2 if high else 1)
        Lc = box['v']
        P = _place(np.stack([Lc[:, 0] + 0.5 * w + 0.002, Lc[:, 1], Lc[:, 2]], axis=1), spine + out * 0.0005, dirc, up, out)
        du = 0.5 * w + 0.005 - np.abs(Lc[:, 0])
        dv = 0.5 * h + 0.006 - np.abs(Lc[:, 1])
        pcs.append(G.piece(P, box['f'], pk=PK['cover'], w2=np.clip(np.minimum(du, dv) / 0.02, 0, 1),
                           cu=(Lc[:, 0] + 0.5 * w) / w, cv=Lc[:, 1] / h + 0.5, outer=(Lc[:, 2] > 0).astype(float),
                           corner=0.0, cside=float(side)))
        # its half of the page block, inside the cover (7 mm in from its edges)
        pb = G.rounded_box((0.5 * w - 0.004, 0.5 * h - 0.004, 0.016), 0.004, 0.01 if high else 0.06, 2 if high else 1)
        Lp = pb['v']
        P = _place(np.stack([Lp[:, 0] + 0.5 * w - 0.002, Lp[:, 1], Lp[:, 2] - 0.0202], axis=1), spine, dirc, up, out)
        pcs.append(G.piece(P, pb['f'], pk=PK['pages'], w2=np.clip(Lp[:, 1] / h + 0.5, 0, 1),
                           cu=(Lp[:, 0] + 0.5 * w) / w, cv=Lp[:, 1] / h + 0.5, side=Lp[:, 2] / 0.016,
                           face=(np.abs(Lp[:, 2]) < 0.0155).astype(float) * 0.0 + (Lp[:, 2] < -0.0155).astype(float)))
    # the loose pages fanning between the halves: thin sheets from the spine, each bowed and a little shorter
    nu, nv = (30, 18) if high else (12, 4)
    for k, a in enumerate(np.linspace(-0.4, 0.4, 3)):
        ang = half * a * 0.62
        dirp = F._unit(across * math.cos(ang) + f * math.sin(ang))
        nrm = F._unit(np.cross(up, dirp))
        uu, vv = np.meshgrid(np.linspace(0.0, 1.0, nu + 1), np.linspace(-0.5, 0.5, nv + 1), indexing='ij')
        reach = (w - 0.012) * (0.95 - 0.04 * abs(k - 1))
        bow = 0.014 * np.sin(np.pi * uu) * (1.0 if a >= 0 else -1.0) + 0.008 * uu ** 2 * (k - 1)
        lift = 0.008 * uu * (1 + abs(k - 1))                      # the free corners curl up a little
        P = (spine[None, None] + dirp * (uu * reach)[..., None] + up * (vv * (h - 0.012) + lift * (vv + 0.5))[..., None]
             + nrm * bow[..., None])
        N = np.broadcast_to(nrm, P.shape)
        sh = G.thick_sheet(P.reshape(-1, 3), np.ascontiguousarray(N).reshape(-1, 3), nu, nv, 0.0012 if high else 0.002)
        n = (nu + 1) * (nv + 1)
        pcs.append(G.piece(sh['v'], sh['f'], pk=PK['pages'], w2=np.concatenate([(vv + 0.5).ravel()] * 2),
                           cu=np.concatenate([uu.ravel()] * 2), cv=np.concatenate([(vv + 0.5).ravel()] * 2),
                           side=np.zeros(2 * n), loose=1.0, face=1.0))
    # the spine: a rounded back with three raised bands
    nu, nv = (24, 40) if high else (8, 6)
    angs = np.linspace(-0.5 * math.pi, 0.5 * math.pi, nu + 1)
    zz = np.linspace(-0.5 * h - 0.006, 0.5 * h + 0.006, nv + 1)
    A_, Zz = np.meshgrid(angs, zz, indexing='ij')
    band = sum(np.exp(-((Zz - z0) / 0.006) ** 2) for z0 in (-0.065, 0.0, 0.065))
    rr = 0.016 + 0.0035 * band
    P = spine[None, None] + (-across)[None, None] * (np.cos(A_) * rr)[..., None] + f[None, None] * (np.sin(A_) * rr * 1.2)[..., None] + up[None, None] * Zz[..., None]
    nrm = F._unit(-across)[None, None] * np.cos(A_)[..., None] + f[None, None] * np.sin(A_)[..., None]
    sh = G.thick_sheet(P.reshape(-1, 3), nrm.reshape(-1, 3), nu, nv, 0.004)
    pcs.append(G.piece(sh['v'], sh['f'], pk=PK['spine'], w2=np.concatenate([band.ravel(), band.ravel()]),
                       cv=np.concatenate([(Zz / h + 0.5).ravel()] * 2)))
    return pcs


def scroll(high: bool) -> list[dict]:
    return scroll_paper(high) + scroll_cord(high)


def quill(high: bool) -> list[dict]:
    return quill_parts(high)


def book(high: bool) -> list[dict]:
    return book_parts(high)
