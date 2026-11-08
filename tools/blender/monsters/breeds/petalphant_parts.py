"""Petalphant's props (Art 2.1 Ultra, `petalphant_ultra.py`): the magnolia-petal ears, the trunk's flower bud (five outer
petals on the bud bones, a small inner core and five sepals), the leaf sprout on the crown and the tail's three leaves.

Every part is a closed shell around a mid-surface F(u, v) (u from the root, v across): an inner and an outer face a
thickness apart and a rounded rim all the way round, root included, so no edge reads as a paper shard (the batch-1
reviews' most common note). Thick at the root, thin at the rim. Pure numpy: the recipe turns the arrays into objects.

Metres; the monster faces −Y, Z is up, +X is its left. Shapes from chatgpt/monsters/07-petalphant/ (2-turnaround.png
gives the measurements at 2.72 mm per pixel; the hero decides shapes).
"""
from __future__ import annotations

import math

import numpy as np

# ----------------------------------------------------------------------------- small helpers
PART_EAR, PART_PETAL, PART_CORE, PART_SEPAL, PART_LEAF, PART_TAIL_LEAF, PART_HEART = 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0


def v3(a) -> np.ndarray:
    return np.asarray(a, dtype=np.float64)


def unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def smooth(a: float, b: float, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def grid(nu: int, nv: int) -> tuple[np.ndarray, np.ndarray]:
    uu = np.linspace(0.0, 1.0, nu + 1)
    vv = np.linspace(0.0, 1.0, nv + 1)
    return np.meshgrid(uu, vv, indexing='ij')


def catmull(pts, n_per: int = 12) -> np.ndarray:
    """A centripetal-free (uniform) Catmull-Rom curve through `pts`, n_per samples per span, ends included."""
    P = v3(pts)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n_per):
            t = k / n_per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def arc_lengths(pts: np.ndarray) -> np.ndarray:
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def resample(curve: np.ndarray, shares) -> np.ndarray:
    """Points at arc-length shares (0..1) of a dense polyline."""
    s = arc_lengths(curve)
    s = s / s[-1]
    return np.stack([np.interp(shares, s, curve[:, i]) for i in range(3)], axis=1)


# ----------------------------------------------------------------------------- the closed shell
def shell(P: np.ndarray, T: np.ndarray, rim: int = 4, relief_in: np.ndarray | None = None,
          relief_out: np.ndarray | None = None, flip: bool = False, bulge: float = 1.0, uv_mode: str = 'arc',
          fan_angles: np.ndarray | None = None, cyl: tuple | None = None):
    """A closed shell around the mid-surface P ((nu+1) x (nv+1) x 3, u = axis 0 from the root, v = axis 1 across) with
    full thickness T ((nu+1) x (nv+1)). The inner face lies on +N (N = dP/du x dP/dv, or −N with `flip`), the outer on
    −N, and a rounded rim of `rim` steps joins them along the whole boundary (top edge v=0, the far edge u=1, the bottom
    edge v=1 and the root u=0). `relief_in` / `relief_out` push each face out (veins for the high source's normal map).
    Returns (verts n x 3, quads m x 4, attrs {pu, pv, pface (+1 inner, −1 outer, between on the rim), prim (0 on the
    faces, 1 at the rim's crest), and '_quv': m x 4 x 2 corner UVs in metres}). The UVs are the shell's own unwrap
    (the build keeps them with own_uv): the inner face, the outer face and the rim strip as three islands laid out by
    arc length along the grid, so nothing folds or overlaps (smart-project left shared texels at thin tips).
    `uv_mode` 'plane' lays each face out by its projection on its best-fitting plane instead (a wide fan or a dome,
    whose rows lengthen too fast for the arc-length grid), and 'fan' (the ears) lays each column out as a ray from the
    root line at its own angle `fan_angles` (one per column, radians) with its true length: it can't fold; 'cyl' (the
    bud's petals) unrolls round the bud's axis, `cyl` = (tip, axis d, centre direction r, tangent t): arc length round
    the axis by height along it, which can't fold either (the planar layout folded at each petal's tucked base)."""
    nu1, nv1, _ = P.shape
    Pu = np.gradient(P, axis=0)
    Pv = np.gradient(P, axis=1)
    N = np.cross(Pu, Pv)
    N /= np.maximum(np.linalg.norm(N, axis=2, keepdims=True), 1e-12)
    if flip:
        N = -N
    h = 0.5 * T[..., None]
    ri = relief_in[..., None] if relief_in is not None else 0.0
    ro = relief_out[..., None] if relief_out is not None else 0.0
    I = P + N * (h + ri)
    O = P - N * (h + ro)
    U, V = grid(nu1 - 1, nv1 - 1)
    nI = nu1 * nv1
    iI = np.arange(nI).reshape(nu1, nv1)
    iO = iI + nI
    verts = [I.reshape(-1, 3), O.reshape(-1, 3)]
    pu = [U.ravel(), U.ravel()]
    pv = [V.ravel(), V.ravel()]
    pface = [np.ones(nI), -np.ones(nI)]
    prim = [np.zeros(nI), np.zeros(nI)]
    quads, want = [], []
    a, b = iI[:-1, :-1].ravel(), iI[1:, :-1].ravel()
    c, d = iI[1:, 1:].ravel(), iI[:-1, 1:].ravel()
    nf = 0.25 * (N[:-1, :-1] + N[1:, :-1] + N[1:, 1:] + N[:-1, 1:]).reshape(-1, 3)
    quads.append(np.stack([a, b, c, d], axis=1))
    want.append(nf)
    quads.append(np.stack([a + nI, b + nI, c + nI, d + nI], axis=1))
    want.append(-nf)
    # the boundary loop: top (v=0) root → far, far edge (u=1) top → bottom, bottom (v=1) far → root, root (u=0) back up
    loop = ([(j, 0) for j in range(nu1 - 1)] + [(nu1 - 1, i) for i in range(nv1 - 1)]
            + [(j, nv1 - 1) for j in range(nu1 - 1, 0, -1)] + [(0, i) for i in range(nv1 - 1, 0, -1)])
    jj = np.array([p[0] for p in loop])
    ii = np.array([p[1] for p in loop])
    # the rim's outward direction at each boundary point (in the surface, away from the inside), corners averaged
    e = np.zeros((len(loop), 3))
    e += np.where((ii == 0)[:, None], -Pv[jj, ii], 0.0)
    e += np.where((jj == nu1 - 1)[:, None], Pu[jj, ii], 0.0)
    e += np.where((ii == nv1 - 1)[:, None], Pv[jj, ii], 0.0)
    e += np.where((jj == 0)[:, None], -Pu[jj, ii], 0.0)
    nb = N[jj, ii]
    e = e - nb * (e * nb).sum(axis=1, keepdims=True)
    e /= np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-12)
    Ib, Ob = I[jj, ii], O[jj, ii]
    M = 0.5 * (Ib + Ob)
    H = 0.5 * (Ib - Ob)
    hl = np.linalg.norm(H, axis=1, keepdims=True)
    rows = [iI[jj, ii]]
    base = 2 * nI
    for k in range(1, rim):
        ang = math.pi * k / rim
        pts = M + H * math.cos(ang) + e * hl * math.sin(ang) * bulge
        verts.append(pts)
        rows.append(base + np.arange(len(loop)))
        base += len(loop)
        pu.append(U[jj, ii])
        pv.append(V[jj, ii])
        pface.append(np.full(len(loop), math.cos(ang)))
        prim.append(np.full(len(loop), math.sin(ang)))
    rows.append(iO[jj, ii])
    nxt = np.roll(np.arange(len(loop)), -1)
    for k in range(rim):
        r0, r1 = rows[k], rows[k + 1]
        quads.append(np.stack([r0, r0[nxt], r1[nxt], r1], axis=1))
        want.append(0.5 * (e + e[nxt]))
    V_ = np.concatenate(verts)
    Q = np.concatenate(quads)
    W = np.concatenate(want)
    fn = np.cross(V_[Q[:, 2]] - V_[Q[:, 0]], V_[Q[:, 3]] - V_[Q[:, 1]])
    # one winding per group (inner face, outer face, rim strip), by majority: a quad that disagrees with the smoothed
    # normal where the petal curls hard is still wound like its neighbours (flipping it alone turned it inside out)
    agree = (fn * W).sum(axis=1)
    sizes = [len(q_) for q_ in quads[:2]] + [sum(len(q_) for q_ in quads[2:])]
    bad = np.zeros(len(Q), bool)
    start = 0
    for n_ in sizes:
        bad[start:start + n_] = np.sum(np.sign(agree[start:start + n_])) < 0
        start += n_
    # own UVs per quad corner (metres): each face grid by arc length along its rows and columns, the rim strip by its
    # length round the boundary and across the rim's profile
    def face_uv(G):
        if uv_mode == 'cyl':
            tip_, d_, r_, t_ = (v3(x_) for x_ in cyl)
            q_ = G - tip_
            h_ = q_ @ d_
            rad_ = q_ - h_[..., None] * d_
            al_ = np.arctan2(rad_ @ t_, rad_ @ r_)
            return np.stack([al_ * np.linalg.norm(rad_, axis=2), h_], axis=2)
        if uv_mode == 'fan':
            su = np.vstack([np.zeros((1, nv1)), np.cumsum(np.linalg.norm(np.diff(G, axis=0), axis=2), axis=0)])
            rs = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(G[0], axis=0), axis=1))])
            ca, sa = np.cos(fan_angles)[None], np.sin(fan_angles)[None]
            return np.stack([su * ca, -rs[None] + su * sa], axis=2)
        if uv_mode == 'plane':
            c = G.reshape(-1, 3).mean(axis=0)
            _s, _w, vt = np.linalg.svd(G.reshape(-1, 3) - c, full_matrices=False)
            return np.stack([(G - c) @ vt[0], (G - c) @ vt[1]], axis=2)
        su = np.vstack([np.zeros((1, nv1)), np.cumsum(np.linalg.norm(np.diff(G, axis=0), axis=2), axis=0)])
        tv = np.hstack([np.zeros((nu1, 1)), np.cumsum(np.linalg.norm(np.diff(G, axis=1), axis=2), axis=1)])
        return np.stack([tv - tv[:, nv1 // 2][:, None], su], axis=2)
    uvI, uvO = face_uv(I), face_uv(O)
    jq, iq = np.meshgrid(np.arange(nu1 - 1), np.arange(nv1 - 1), indexing='ij')
    jq, iq = jq.ravel(), iq.ravel()
    corners = [(jq, iq), (jq + 1, iq), (jq + 1, iq + 1), (jq, iq + 1)]
    quv = [np.stack([uvI[a_, b_] for a_, b_ in corners], axis=1), np.stack([uvO[a_, b_] for a_, b_ in corners], axis=1)]
    rowpos = [Ib] + [verts[2 + k] for k in range(rim - 1)] + [Ob]
    rr = np.zeros((rim + 1, len(loop)))
    for k in range(rim):
        rr[k + 1] = rr[k] + np.linalg.norm(rowpos[k + 1] - rowpos[k], axis=1)
    seg = np.linalg.norm(M[nxt] - M, axis=1)
    sL = np.concatenate([[0.0], np.cumsum(seg)[:-1]])
    for k in range(rim):
        quv.append(np.stack([np.stack([sL, rr[k]], 1), np.stack([sL + seg, rr[k][nxt]], 1),
                             np.stack([sL + seg, rr[k + 1][nxt]], 1), np.stack([sL, rr[k + 1]], 1)], axis=1))
    QUV = np.concatenate(quv)
    island = np.concatenate([np.zeros(len(quv[0])), np.ones(len(quv[1])), np.full(len(QUV) - len(quv[0]) - len(quv[1]), 2.0)])
    Q[bad] = Q[bad][:, ::-1]
    QUV[bad] = QUV[bad][:, ::-1]
    # one handedness for every island (a mirrored island bakes a flipped tangent-space normal map), then apart
    x, y = QUV[..., 0], QUV[..., 1]
    area = 0.5 * (x * np.roll(y, -1, axis=1) - np.roll(x, -1, axis=1) * y).sum(axis=1)
    off = 0.0
    for k in (0.0, 1.0, 2.0):
        m = island == k
        if area[m].sum() < 0:
            QUV[m, :, 0] *= -1.0
        QUV[m, :, 0] += off - QUV[m, :, 0].min()
        QUV[m, :, 1] -= QUV[m, :, 1].min()
        off = QUV[m, :, 0].max() + 0.05
    attrs = {'pu': np.concatenate(pu), 'pv': np.concatenate(pv), 'pface': np.concatenate(pface), 'prim': np.concatenate(prim),
             '_quv': QUV, '_island': island}
    return V_, Q, attrs


# ----------------------------------------------------------------------------- the ears: big magnolia petals
# The left ear (+X); the right one is mirrored. A fan from a root curve on the side of the head (behind the eye, under
# the fur clumps): v runs from the top edge (θ_TOP, up and out) round to the bottom edge (θ_BOT, down and out); the
# petal's gentle point hangs at the bottom and curls forward. The inner face looks forward and out (2-turnaround front
# and side views both show it; the back view shows the green-rooted outer face).
EAR_ROOT = (v3((0.19, -0.405, 1.232)), v3((0.226, -0.372, 1.108)), v3((0.228, -0.332, 0.982)))   # top, mid (control), bottom
EAR_MID = v3((0.215, -0.37, 1.108))          # the fan's centre: the outline is polar round it
EAR_YAW = math.radians(-18.0)                 # round 3: the whole fan turned 18° toward the front about the vertical
_c, _s = math.cos(EAR_YAW), math.sin(EAR_YAW)
_EAR_OUT0 = unit((0.906, 0.423, -0.05))
EAR_OUT = unit((_EAR_OUT0[0] * _c - _EAR_OUT0[1] * _s, _EAR_OUT0[0] * _s + _EAR_OUT0[1] * _c, _EAR_OUT0[2]))   # out (and a touch back)
EAR_W = unit(v3((0.0, 0.0, 1.0)) - EAR_OUT * EAR_OUT[2])      # across the fan (about up)
EAR_N = unit(np.cross(EAR_OUT, EAR_W))        # the inner face's normal at the root: about 7° from the front
TH_TOP, TH_BOT = math.radians(72.0), math.radians(-77.0)
# the rim, polar round EAR_MID in the fan's plane (θ degrees from EAR_OUT toward EAR_W, reach in metres), from
# 2-turnaround.png: the top at (0.40, −0.17, 1.365), the broad far lobe at (0.74, 0.18, 0.98), the gentle point hanging at
# (0.6, −0.27, 0.57) (the depth term below curls it 0.2 m forward), the lower edge tucking back under the cheek
# round 2 (review): the gentle point at about −52° pushed out 0.1 m and narrowed, so it reads as a magnolia petal's point
EAR_OUTLINE = [(72, 0.15), (64, 0.23), (56, 0.3), (48, 0.36), (36, 0.45), (22, 0.51), (8, 0.555), (-7, 0.575), (-20, 0.56),
               (-32, 0.57), (-40, 0.6), (-45, 0.645), (-49, 0.71), (-52, 0.76), (-55, 0.7), (-58, 0.6), (-63, 0.47),
               (-68, 0.33), (-72, 0.24), (-77, 0.12)]
TIP_V = (72.0 + 52.0) / 149.0                 # v of the point (θ = −52°)
# how far the rim leaves the fan's plane along EAR_N (+ forward and out): the petal curves like a C seen from above (its
# inner face toward the front by the root, the top and the broad far lobe curling back), and the gentle point curls
# forward, so it reads big in the front, side and three-quarter views
EAR_RIM_DEPTH = [(0.0, -0.06), (0.16, -0.13), (0.36, -0.18), (0.53, -0.2), (0.66, -0.11), (0.76, -0.0), (0.832, 0.06),
                 (0.92, 0.03), (1.0, -0.02)]


def ear_reach(th: np.ndarray) -> np.ndarray:
    deg, r = zip(*EAR_OUTLINE[::-1])
    return np.interp(np.degrees(th), deg, r)


def _bez(a, b, c, t):
    t = np.asarray(t, dtype=np.float64)[..., None]
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c


def ear_rim(V: np.ndarray) -> np.ndarray:
    th = TH_TOP + (TH_BOT - TH_TOP) * V
    # a soft wave along the outline (a petal's edge is never a clean curve), quiet by the root and at the point
    quiet = smooth(0.04, 0.2, V) * smooth(0.97, 0.8, V) * (1.0 - np.exp(-((V - TIP_V) / 0.045) ** 2))
    R = ear_reach(th) * (1.0 + 0.028 * np.sin(2 * np.pi * 6.5 * V + 0.4) * quiet)
    return EAR_MID + R[..., None] * (np.cos(th)[..., None] * EAR_OUT + np.sin(th)[..., None] * EAR_W)


def ear_mid(U: np.ndarray, V: np.ndarray, s: int = 1) -> np.ndarray:
    """The ear's mid-surface: (u, v) arrays → points; u from the root curve (0) to the rim (1), v from the top edge (0)
    round to the bottom edge (1)."""
    root = _bez(EAR_ROOT[0], EAR_ROOT[1], EAR_ROOT[2], V)
    rim = ear_rim(V)
    Uc = np.clip(U, 0, 1)
    # depth along the inner normal: a soft cup (the middle sits behind the rim), the lower point curling forward, the
    # very rim rolling back a little, and three soft folds toward the edge
    # round 2 (review): a deeper cup, the top edge rolling back, a rippled edge, and the point curling outward (away from
    # the inner face) at its very end, as a magnolia petal's does (1-hero.png, 4-details.png panel 5)
    cup = -0.07 * np.sin(np.pi * Uc ** 0.85)
    a, b = zip(*EAR_RIM_DEPTH)
    tip = np.interp(V, a, b) * Uc ** 1.5
    roll = -0.014 * smooth(0.84, 1.0, Uc) - 0.06 * smooth(0.74, 1.0, Uc) ** 1.5 * smooth(0.45, 0.08, V)
    win = smooth(0.0, 0.15, V) * smooth(1.0, 0.85, V)
    fold = (0.028 * Uc ** 1.6 * np.sin(2 * np.pi * 3.2 * V + 0.9) + 0.011 * Uc ** 2 * np.sin(2 * np.pi * 6.6 * V + 2.1)) * win
    ripple = 0.017 * smooth(0.72, 1.0, Uc) * np.sin(2 * np.pi * 8.5 * V + 0.3) * win * (1.0 - np.exp(-((V - TIP_V) / 0.05) ** 2))
    curl = -0.055 * smooth(0.82, 1.0, Uc) * np.exp(-((V - TIP_V) / 0.04) ** 2)
    depth = cup + tip + roll + fold + ripple + curl
    P = root + Uc[..., None] * (rim - root) + depth[..., None] * EAR_N
    if s < 0:
        P = P * v3((-1.0, 1.0, 1.0))
    return P


def ear_thickness(U: np.ndarray, V: np.ndarray) -> np.ndarray:
    return 0.0065 + 0.032 * (1.0 - np.clip(U, 0, 1)) ** 1.7


def ear_veins(U: np.ndarray, V: np.ndarray) -> np.ndarray:
    """0..1: the petal's veins (round 3): 14 main veins fanning from the root, each splitting in a Y at about 40% of the
    reach and each branch splitting again at about 70%, so they branch toward the rim like a magnolia petal's (round 2's
    parallel in-between lines read as even sun-ray streaks); gently meandering, fading at the root and short of the
    cream rim. Widths in the high grid's columns (480 across): main about 3, branches about 2."""
    U = np.clip(U, 0, 1)
    n0 = 14.0
    vv = V + 0.008 * np.sin(np.pi * U) * np.sin(2 * np.pi * 2.0 * V + 0.7)
    q = vv * n0
    kk = np.floor(q)
    w = q - kk - 0.5 + 0.05 * np.sin(kk * 1.7 + U * 3.0)            # position inside this vein's period, its centre 0
    s1 = smooth(0.36, 1.0, U) ** 0.8
    s2 = smooth(0.66, 1.0, U) ** 0.8
    d1 = 0.25 * s1
    d2 = 0.125 * s2
    main = np.exp(-(w / 0.05) ** 2) * (1.0 - 0.55 * s1)
    br = np.maximum(np.exp(-((w - d1) / 0.04) ** 2), np.exp(-((w + d1) / 0.04) ** 2)) * smooth(0.34, 0.44, U) * 0.9
    sub = np.zeros_like(w)
    for sa in (-1.0, 1.0):
        for sb in (-1.0, 1.0):
            sub = np.maximum(sub, np.exp(-((w - sa * d1 - sb * d2) / 0.032) ** 2))
    sub = sub * smooth(0.64, 0.74, U) * 0.7
    return np.clip(np.maximum.reduce([main, br, sub]) * smooth(0.05, 0.18, U) * smooth(0.985, 0.93, U), 0, 1)


def ear_arrays(s: int, high: bool, quick: bool):
    """(verts, quads, attrs) of one ear."""
    # the game mesh 26 x 52: at 20 x 30 the big petal's outline showed straight segments in the game (build 1), and the
    # narrower point needs columns; the high source 140 x 480, so each vein is a crisp line one or two columns wide
    nu, nv = ((140, 480) if not quick else (60, 160)) if high else (26, 52)
    U, V = grid(nu, nv)
    # more rows near the root (the fur and the colour change) and the rim (the roll): an eased u
    Ue = 0.5 - 0.5 * np.cos(np.pi * U) * 0.35 + (U - 0.5) * 0.65
    P = ear_mid(Ue, V, s)
    T = ear_thickness(Ue, V)
    rin = rout = None
    if high:
        vein = ear_veins(Ue, V)
        rin = 0.0008 * vein + 0.0002 * np.sin(Ue * 160.0 + V * 40.0) * smooth(0.2, 0.5, Ue)
        rout = 0.0006 * vein
    th = TH_TOP + (TH_BOT - TH_TOP) * V[0]
    verts, quads, attrs = shell(P, T, rim=5 if high else 4, relief_in=rin, relief_out=rout, flip=s < 0, uv_mode='fan', fan_angles=th)
    attrs['pu'] = np.interp(attrs['pu'], U[:, 0], Ue[:, 0])
    attrs['vein'] = ear_veins(attrs['pu'], attrs['pv'])
    return verts, quads, attrs


def ear_bone(s: int = 1) -> tuple[np.ndarray, np.ndarray, float]:
    """(base, direction, length) for the ear bones: from the root's middle toward the petal's broad far lobe."""
    base = _bez(EAR_ROOT[0], EAR_ROOT[1], EAR_ROOT[2], 0.5)
    far = ear_mid(np.array(0.75), np.array(0.5), 1)
    d = far - base
    if s < 0:
        base, d = base * v3((-1, 1, 1)), d * v3((-1, 1, 1))
    return base, unit(d), float(np.linalg.norm(far - base)) * 1.15


# ----------------------------------------------------------------------------- the bud (on the trunk's tip)
BUD_PETALS = 5
BUD_ROLL = 36.0            # degrees: one petal faces forward and down, toward the front camera (plans.quadruped.bud_petals)
BUD_H = 0.175              # the bud's length along its axis, base to point (2-turnaround: about 0.2 m with the sepals)
BUD_R0, BUD_RMAX = 0.034, 0.047     # profile: radius at the base and the swell's amplitude (0.158 m wide)
BUD_SPAN = math.radians(140.0)      # each petal's width round the axis (overlapping shingles; round 2: broader petals)


def bud_frame(tip, prev, n: int = BUD_PETALS, roll: float = BUD_ROLL):
    """The bud's axis d and each petal's radial direction r_i, exactly as plans/quadruped.py bud_petals builds the bones
    (so petal i sits on bone bud.(i+1)), plus e1, e2."""
    tip, prev = v3(tip), v3(prev)
    d = unit(tip - prev)
    ref = v3((1, 0, 0)) if abs(d[0]) < 0.9 else v3((0, 0, 1))
    e1 = unit(np.cross(d, ref))
    e2 = unit(np.cross(d, e1))
    phis = [math.radians(roll) + 2 * math.pi * i / n for i in range(n)]
    return d, e1, e2, phis


def bud_profile(u: np.ndarray) -> np.ndarray:
    """The closed bud's radius along its axis: a swelling egg narrowing to a soft point."""
    u = np.clip(u, 0, 1)
    return BUD_R0 * (1 - u) ** 1.2 + BUD_RMAX * np.sin(np.pi * u ** 0.72) ** 0.9 + 0.003 * (1 - u)


def _round_piece(tip, d, e1, e2, phi, U, V, H, prof, span, shingle, h0=0.0, lean=None):
    """A piece wrapped round the axis d: u along it (h0 → h0 + H), v across the piece (span(u) wide at angle phi)."""
    a = phi + (V - 0.5) * span
    rho = prof * (1.0 + shingle * (V - 0.5))
    if lean is not None:
        rho = rho + lean
    radial = np.cos(a)[..., None] * e1 + np.sin(a)[..., None] * e2
    return tip + d * (h0 + H * U)[..., None] + rho[..., None] * radial


def petal_arrays(tip, prev, i: int, high: bool, quick: bool):
    """Outer petal i (on bone bud.(i+1)): a curved shell of the egg-shaped bud, pointed at the tip, overlapping its
    neighbours (each one's leading edge a little outside, its trailing edge tucked under the next)."""
    d, e1, e2, phis = bud_frame(tip, prev)
    nu, nv = ((44, 30) if not quick else (24, 16)) if high else (16, 12)      # round 3: the game mesh denser (stair-stepped edges)
    U, V = grid(nu, nv)
    # round 2: a soft point, not a spike (the open flower read as a thistle): the width holds longer, then rounds off
    span = BUD_SPAN * (1.0 - 0.3 * smooth(0.5, 1.0, U) ** 1.4)      # round 3b: more overlap at the point (dark slits)
    # each petal swells across on its own (a cupped petal, not a slice of a smooth egg), its tip flares out a touch, and
    # alternate petals end a little lower so the points stagger
    cupx = 0.008 * np.sin(np.pi * V) * np.sin(np.pi * np.clip(U, 0, 1) ** 0.8)
    flare = 0.004 * smooth(0.75, 1.0, U)
    H = BUD_H * (1.0 - 0.035 * (i % 2))
    # round 3b: the shingle's step fades toward the point, so the tips lie on one another (dark slits between them)
    shingle = 0.13 * (1.0 - 0.75 * smooth(0.55, 1.0, U))
    P = _round_piece(v3(tip), d, e1, e2, phis[i], U, V, H, bud_profile(U) + cupx + flare, span, 0.0)
    radial_k = 1.0 + shingle * (V - 0.5)
    P = v3(tip) + d * (H * U)[..., None] + (P - v3(tip) - d * (H * U)[..., None]) * radial_k[..., None]
    T = 0.0042 * (1 - 0.45 * U) + 0.0012
    rin = None
    if high:
        k = (V * 9.0) % 1.0
        rin = 0.00035 * np.exp(-((np.minimum(k, 1 - k)) / 0.1) ** 2) * smooth(0.05, 0.3, U) * smooth(1.0, 0.8, U)
    # the outer (visible) face away from the axis: the shell's inner side (+N) is the one facing out
    r_i = np.cos(phis[i]) * e1 + np.sin(phis[i]) * e2
    verts, quads, attrs = shell(P, np.broadcast_to(T, U.shape).copy(), rim=3 if high else 2, relief_in=rin, flip=_faces_axis(P, d, tip),
                                uv_mode='cyl', cyl=(tip, d, r_i, np.cross(d, r_i)))
    return verts, quads, attrs


def _faces_axis(P: np.ndarray, d, tip) -> bool:
    """True when dP/du x dP/dv points toward the axis at the piece's middle (so `shell` flips it outward)."""
    Pu = np.gradient(P, axis=0)
    Pv = np.gradient(P, axis=1)
    j, i = P.shape[0] // 2, P.shape[1] // 2
    n = np.cross(Pu[j, i], Pv[j, i])
    q = P[j, i] - v3(tip)
    radial = q - d * (q @ d)
    return float(n @ radial) < 0


def core_arrays(tip, prev, k: int, high: bool, quick: bool):
    """The inner core: three small, paler petals closed round the axis (shown when the bud opens; rigid on the trunk's
    last bone). Kept within 1.8 cm of the axis so the outer petals' inner faces bake their own colour (cage 2 cm)."""
    d, e1, e2, phis = bud_frame(tip, prev)
    nu, nv = ((22, 16) if not quick else (12, 10)) if high else (7, 5)
    U, V = grid(nu, nv)
    # round 2: the inner ring of the open magnolia, upright: broader and taller (it still keeps 2 cm inside the closed
    # outer petals for the bake's cage)
    phi = phis[0] + math.pi / 5 + 2 * math.pi * k / 3
    prof = 0.013 * (1 - U) + 0.023 * np.sin(np.pi * U ** 0.7) + 0.002
    span = math.radians(165) * (1 - 0.6 * smooth(0.55, 1.0, U) ** 1.4)
    # round 3b: up into the point, so any gap between the closed petals' tips shows this pale pink, not the dark inside
    P = _round_piece(v3(tip), d, e1, e2, phi, U, V, 0.155, prof, span, 0.1, h0=0.004)
    T = np.full(U.shape, 0.0035)
    return shell(P, T, rim=2, flip=_faces_axis(P, d, tip))


def heart_arrays(tip, prev, high: bool, quick: bool):
    """The flower's heart: a low yellow-green dome at the base of the petals, round the core (shown when the bud opens;
    rigid on the trunk's last bone). It closes the cup over the trunk's end, 3 cm wide (inside the bake's 2 cm cage)."""
    d, e1, e2, _phis = bud_frame(tip, prev)
    nu, nv = ((10, 40) if not quick else (6, 24)) if high else (4, 14)
    U, V = grid(nu, nv)
    Uu = 0.08 + 0.92 * U
    a = 2 * np.pi * V * nv / (nv + 1)          # one step short of the full turn: no seam where two rims would lie together
    radial = np.cos(a)[..., None] * e1 + np.sin(a)[..., None] * e2
    P = v3(tip) + d * (0.006 + 0.008 * (1 - Uu ** 2))[..., None] + (0.03 * Uu)[..., None] * radial
    T = np.full(U.shape, 0.006)
    # the dome's top face looks along d
    Pu = np.gradient(P, axis=0)
    Pv = np.gradient(P, axis=1)
    flip = float(np.cross(Pu[nu // 2, nv // 4], Pv[nu // 2, nv // 4]) @ d) < 0
    return shell(P, T, rim=2, flip=flip, uv_mode='plane')


def sepal_arrays(tip, prev, k: int, high: bool, quick: bool):
    """Sepal k: a pointed green leaf cupping the bud's base and the trunk's end, between petals k and k+1 (skinned half
    and half to their bones, so it opens about 44° with them and stays under the open flower, a calyx)."""
    d, e1, e2, phis = bud_frame(tip, prev)
    nu, nv = ((26, 16) if not quick else (14, 10)) if high else (8, 6)
    U, V = grid(nu, nv)
    phi = phis[k] + math.pi / BUD_PETALS
    H = 0.104
    h0 = -0.03
    # radius over the bud's own profile at that height, a little outside it, leaning out at the tip
    hb = np.clip((h0 + H * U) / BUD_H, 0, 1)
    prof = np.maximum(bud_profile(hb), 0.045) + 0.0075 + 0.012 * smooth(0.55, 1.0, U)
    span = math.radians(68) * (1.0 - smooth(0.12, 1.0, U) ** 0.9 * 0.94)
    P = _round_piece(v3(tip), d, e1, e2, phi, U, V, H, prof, span, 0.0, h0=h0)
    T = 0.0042 * (1 - 0.5 * U) + 0.0013
    rin = None
    if high:
        rin = 0.0005 * np.exp(-((V - 0.5) / 0.06) ** 2) * smooth(0.0, 0.2, U)
    return shell(P, np.broadcast_to(T, U.shape).copy(), rim=3 if high else 2, relief_in=rin, flip=_faces_axis(P, d, tip))


# ----------------------------------------------------------------------------- leaves (the crown's sprout, the tail's tuft)
def leaf_mid(U: np.ndarray, V: np.ndarray, base, along, face, length: float, width: float, fold: float = 0.3,
             curl: float = 0.18, twist: float = 0.0) -> np.ndarray:
    """A pointed leaf: u from the stalk to the tip, v across; `face` is the upper face's normal at the base. The leaf
    folds up along its midrib (a shallow V), curls toward `face` × `curl` and twists `twist` radians toward the tip."""
    a = unit(along)
    n0 = unit(v3(face) - a * (v3(face) @ a))
    b0 = unit(np.cross(n0, a))
    tw = twist * U
    b = np.cos(tw)[..., None] * b0 + np.sin(tw)[..., None] * n0
    n = np.cos(tw)[..., None] * n0 - np.sin(tw)[..., None] * b0
    x = 2.0 * V - 1.0
    w = 0.5 * width * np.sin(np.pi * np.clip(U, 0, 1) ** 0.8) ** 0.55 + 0.06 * width * (1 - U)
    # the curl bends the leaf's axis (a quarter circle at most), the fold lifts the edges
    ang = curl * U * U
    along_k = np.cos(ang)[..., None] * a + np.sin(ang)[..., None] * n
    P = v3(base) + along_k * (length * U)[..., None] + b * (w * x)[..., None] + n * (fold * np.abs(x) * w)[..., None]
    return P


def leaf_arrays(base, along, face, length: float, width: float, high: bool, quick: bool, fold=0.3, curl=0.18, twist=0.0,
                thick: float = 0.0028):
    nu, nv = ((40, 16) if not quick else (20, 10)) if high else (10, 6)
    U, V = grid(nu, nv)
    P = leaf_mid(U, V, base, along, face, length, width, fold, curl, twist)
    T = thick * (1 - 0.6 * U) + 0.0012
    rin = None
    if high:
        x = 2 * V - 1
        mid = np.exp(-(x / 0.08) ** 2)
        k = ((U - 0.55 * np.abs(x)) * 7.0) % 1.0
        side = 0.5 * np.exp(-((np.minimum(k, 1 - k)) / 0.09) ** 2) * smooth(0.12, 0.4, np.abs(x)) * smooth(0.95, 0.6, np.abs(x))
        rin = -0.0005 * mid + 0.00025 * side
    # the upper face (toward `face`) is the shell's +N side
    Pu = np.gradient(P, axis=0)
    Pv = np.gradient(P, axis=1)
    j, i = P.shape[0] // 2, P.shape[1] // 2
    flip = float(np.cross(Pu[j, i], Pv[j, i]) @ v3(face)) < 0
    verts, quads, attrs = shell(P, np.broadcast_to(T, U.shape).copy(), rim=3 if high else 2, relief_in=rin, flip=flip)
    x = 2 * attrs['pv'] - 1
    attrs['vein'] = np.exp(-(x / 0.1) ** 2)
    return verts, quads, attrs
