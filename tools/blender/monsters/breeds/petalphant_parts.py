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
PART_STAMEN, PART_PISTIL = 8.0, 9.0


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
EAR_YAW = math.radians(-15.0)                 # round 4: 15° toward the front (round 3's 18° showed the near ear edge-on from the side)
# round 4: the petal bends back round the vertical as it leaves the head (BEND degrees at the rim), so its root faces the
# front and its outer half the side: broad in the front, three-quarter and side views alike (2-turnaround side view)
EAR_BEND = 22.0
EAR_SCALE = 1.1                              # round 4: a touch bigger, so the bent petal still spans the front view's width
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
# round 5: the point no longer curls forward (the review wants its tip twisted back into one soft point)
EAR_RIM_DEPTH = [(0.0, -0.06), (0.16, -0.13), (0.36, -0.18), (0.53, -0.2), (0.66, -0.11), (0.76, -0.03), (0.832, -0.02),
                 (0.92, -0.02), (1.0, -0.02)]


def ear_reach(th: np.ndarray) -> np.ndarray:
    deg, r = zip(*EAR_OUTLINE[::-1])
    return np.interp(np.degrees(th), deg, r) * EAR_SCALE


def _bez(a, b, c, t):
    t = np.asarray(t, dtype=np.float64)[..., None]
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c


def ear_rim(V: np.ndarray) -> np.ndarray:
    th = TH_TOP + (TH_BOT - TH_TOP) * V
    # a soft wave along the outline (a petal's edge is never a clean curve), quiet by the root and at the point
    quiet = smooth(0.04, 0.2, V) * smooth(0.97, 0.8, V) * (1.0 - np.exp(-((V - TIP_V) / 0.045) ** 2))
    # round 5: two or three big, uneven lobes (round 4's six even scallops read as a cut-out)
    R = ear_reach(th) * (1.0 + (0.06 * np.sin(2 * np.pi * 2.4 * V + 0.4) + 0.012 * np.sin(2 * np.pi * 4.7 * V + 2.1)) * quiet)
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
    cup = -0.11 * np.sin(np.pi * Uc ** 0.85)        # round 5: deeper (the front face reads concave)
    a, b = zip(*EAR_RIM_DEPTH)
    # round 4: the far lobe's own curl back is now the bend's (below); the rim-depth table keeps the point's forward curl
    tipv = np.interp(V, a, b)
    tip = np.where(tipv < 0, 0.45 * tipv, tipv) * Uc ** 1.5
    # round 5: the upper outer edge rolls forward, toward the face (it rolled back)
    # round 6: wide, gentle gradients only (narrow ones folded the low mesh into straight creases)
    roll = 0.06 * smooth(0.4, 1.0, Uc) ** 2 * smooth(0.6, 0.0, V)
    win = smooth(0.0, 0.15, V) * smooth(1.0, 0.85, V)
    # round 4: a cup across the petal too (its top and bottom edges come forward of its middle: a bowl, not a fan), and
    # only two broad, soft undulations (round 3's six radial pleats shaded as sun-ray streaks)
    vcup = 0.075 * Uc ** 1.2 * (2.0 * np.clip(V, 0, 1) - 1.0) ** 2
    fold = 0.012 * Uc ** 1.6 * np.sin(2 * np.pi * 2.1 * V + 0.9) * win
    # round 6: two or three soft waves along the outer edge (out of the petal's plane), quiet at the point
    ripple = 0.022 * smooth(0.55, 1.0, Uc) ** 1.5 * np.sin(2 * np.pi * 2.6 * V + 0.6) * win * (1.0 - np.exp(-((V - TIP_V) / 0.07) ** 2))
    curl = -0.07 * smooth(0.55, 1.0, Uc) ** 1.5 * np.exp(-((V - TIP_V) / 0.08) ** 2)      # rounds 5-6: the point twists back, softly
    depth = cup + tip + roll + vcup + fold + ripple + curl
    P = root + Uc[..., None] * (rim - root) + depth[..., None] * EAR_N
    # round 4: the bend back round the vertical through each root point, growing toward the rim
    # round 5: the lower lobe under the cheek bends back further, so in profile it shows its face, not a flat tab
    # round 6: the lower lobe's extra bend spread wide (round 5's narrow one folded it into a flat panel with a crease)
    beta = math.radians(EAR_BEND) * smooth(0.08, 1.0, Uc) ** 1.25 + math.radians(9.0) * smooth(0.5, 1.0, V) * smooth(0.0, 0.7, Uc)
    rel = P - root
    cb, sb = np.cos(beta), np.sin(beta)
    P = root + np.stack([rel[..., 0] * cb - rel[..., 1] * sb, rel[..., 0] * sb + rel[..., 1] * cb, rel[..., 2]], axis=-1)
    if s < 0:
        P = P * v3((-1.0, 1.0, 1.0))
    return P


def ear_thickness(U: np.ndarray, V: np.ndarray) -> np.ndarray:
    return 0.0065 + 0.032 * (1.0 - np.clip(U, 0, 1)) ** 1.7


_N0 = 12
_VEINS = []
_rng = np.random.default_rng(20261112)
for _k in range(_N0):
    _r = _rng.uniform(size=12)
    _VEINS.append({'v0': (_k + 0.5 + 0.35 * (_r[0] - 0.5)) / _N0, 'ph': _r[1] * 2 * math.pi, 'cv': 0.6 + 0.8 * _r[2],
                   'uf1': 0.2 + 0.2 * _r[3], 'a1': 0.28 + 0.44 * _r[4],
                   'uf2': (0.18 + 0.14 * _r[5], 0.18 + 0.14 * _r[6]), 'a2': (0.3 + 0.4 * _r[7], 0.3 + 0.4 * _r[8]),
                   'uf3': 0.72 + 0.14 * _r[9]})


def _hash2(i, j, seed):
    h = np.sin(i * 127.1 + j * 311.7 + seed * 74.7) * 43758.5453
    return h - np.floor(h)


def ear_net(U: np.ndarray, V: np.ndarray, cell: float = 0.012) -> np.ndarray:
    """0..1: the fine net of veinlets between the veins (a cellular pattern's cell walls, about 1.2 cm cells), laid out
    in the fan's own plane (radius × angle), so the cells keep their size from the root to the rim."""
    th = TH_TOP + (TH_BOT - TH_TOP) * np.clip(V, 0, 1)
    r = np.clip(U, 0, 1) * 0.62 * EAR_SCALE
    x, y = r * np.cos(th) / cell, r * np.sin(th) / cell
    ix, iy = np.floor(x), np.floor(y)
    f1 = np.full(x.shape, 9.0)
    f2 = np.full(x.shape, 9.0)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ci, cj = ix + di, iy + dj
            px = ci + 0.15 + 0.7 * _hash2(ci, cj, 1.0)
            py = cj + 0.15 + 0.7 * _hash2(ci, cj, 2.0)
            d = np.hypot(x - px, y - py)
            f2 = np.where(d < f1, f1, np.minimum(f2, d))
            f1 = np.minimum(f1, d)
    return np.exp(-((f2 - f1) / 0.09) ** 2)


def ear_veins(U: np.ndarray, V: np.ndarray) -> np.ndarray:
    """0..1: the petal's veins (round 4): 12 main veins from the root, each curving gently toward its side of the petal and
    forking unevenly at its own point (one branch carries on, the other leaves at an angle), each branch forking again,
    and fine veinlets at the end, over a faint net of veinlets between them (ear_net), like a real petal's (rounds 2-3's
    evenly spaced straight forks read as a sun-ray fan). Widths in metres; fading at the root and short of the rim."""
    U = np.clip(U, 0, 1)
    V = np.clip(V, 0, 1)
    arc = (TH_TOP - TH_BOT) * np.maximum(U, 0.03) * 0.62 * EAR_SCALE        # metres per unit of v at this u (about)
    out = np.zeros(np.broadcast(U, V).shape)
    per = 1.0 / _N0

    def line(c, w, strength, gate):
        nonlocal out
        out = np.maximum(out, strength * gate * np.exp(-((V - c) * arc / w) ** 2))

    for vd in _VEINS:
        c0 = vd['v0'] + 0.05 * vd['cv'] * (vd['v0'] - 0.5) * U ** 2 + 0.004 * np.sin(2 * np.pi * 1.1 * U + vd['ph'])
        uf1 = vd['uf1']
        line(c0, 0.0026 * (1.0 - 0.3 * U), 1.0, smooth(uf1 + 0.02, uf1, U))
        d1 = 0.5 * per * smooth(uf1, uf1 + 0.32, U)
        for j, cb in enumerate((c0 - vd['a1'] * d1, c0 + (1.0 - vd['a1']) * d1)):
            uf2 = uf1 + vd['uf2'][j]
            line(cb, 0.0021, 0.88, smooth(uf1 - 0.02, uf1, U) * smooth(uf2 + 0.02, uf2, U))
            d2 = 0.25 * per * smooth(uf2, uf2 + 0.26, U)
            a2 = vd['a2'][j]
            for cs in (cb - a2 * d2, cb + (1.0 - a2) * d2):
                uf3 = max(vd['uf3'], uf2 + 0.1)
                line(cs, 0.0016, 0.74, smooth(uf2 - 0.02, uf2, U) * smooth(uf3 + 0.02, uf3, U))
                d3 = 0.11 * per * smooth(uf3, 1.0, U)
                for cl in (cs - d3, cs + d3):
                    line(cl, 0.0011, 0.5, smooth(uf3 - 0.02, uf3, U))
    net = ear_net(U, V) * smooth(0.18, 0.4, U) * 0.3
    return np.clip(np.maximum(out, net) * smooth(0.0, 0.06, U) * smooth(0.985, 0.93, U), 0, 1)     # round 5: to the root


def ear_fade_t(U: np.ndarray, V: np.ndarray, ve: np.ndarray, inner) -> np.ndarray:
    """The green root's fade (round 4): t < 0 green, 0..1 the fade through a pale petal base, > 1 pink. A short collar
    on the inner face (the fur ruff covers the root), about a quarter of the way up the outer face; a smooth, wide fade
    with no corner (a soft maximum of the distance from the root and the share of the reach), feathered a little along
    the veins. `inner` is a bool or a bool array (the inner face)."""
    U = np.clip(U, 0, 1)
    um = U * ear_reach(TH_TOP + (TH_BOT - TH_TOP) * np.clip(V, 0, 1))
    # round 5: a short fuzzy tuft of green (round 4's wedge reached far into the petal), a little longer on the back
    # round 6: on the back, a broad feathered gradient over the inner quarter to third (round 5's read as a capsule edge)
    G = np.where(inner, 0.0, 0.06)
    capu = np.where(inner, 0.02, 0.14)
    sg = np.where(inner, 0.04, 0.11)
    su = np.where(inner, 0.06, 0.13)
    t = np.logaddexp((um - G) / sg * 3.0, (U - capu) / su * 3.0) / 3.0
    return t - np.where(inner, 0.16, 0.4) * ve * smooth(-0.2, 0.8, t)


def ear_map(nu: int = 768, nv: int = 2304) -> np.ndarray:
    """The ears' per-pixel map for the recipe's prop_material (round 4): nu rows of u (root → rim) by nv columns of v
    (top edge → bottom edge), float32 RGBA: R the veins, G the inner face's fade t, B the outer face's, A 1. Sampled at
    each pixel's (pv, pu), so the veins stay crisp lines at the atlas's texel size and the fade has no vertex steps."""
    U, V = np.meshgrid((np.arange(nu) + 0.5) / nu, (np.arange(nv) + 0.5) / nv, indexing='ij')
    ve = ear_veins(U, V)
    out = np.ones((nu, nv, 4), np.float32)
    out[..., 0] = ve
    out[..., 1] = ear_fade_t(U, V, ve, True)
    out[..., 2] = ear_fade_t(U, V, ve, False)
    return out


def ear_arrays(s: int, high: bool, quick: bool):
    """(verts, quads, attrs) of one ear."""
    # the game mesh 26 x 52: at 20 x 30 the big petal's outline showed straight segments in the game (build 1), and the
    # narrower point needs columns; the high source 140 x 480, so each vein is a crisp line one or two columns wide
    nu, nv = ((140, 480) if not quick else (60, 160)) if high else (30, 58)        # round 6: smoother curvature in the game
    U, V = grid(nu, nv)
    # more rows near the root (the fur and the colour change) and the rim (the roll): an eased u
    Ue = 0.5 - 0.5 * np.cos(np.pi * U) * 0.35 + (U - 0.5) * 0.65
    P = ear_mid(Ue, V, s)
    T = ear_thickness(Ue, V)
    rin = rout = None
    if high:
        # round 4: raised veins and veinlets only (round 3's diagonal ripple added to the streaks)
        vein = ear_veins(Ue, V)
        rin = 0.0008 * vein
        rout = 0.0006 * vein
    th = TH_TOP + (TH_BOT - TH_TOP) * V[0]
    verts, quads, attrs = shell(P, T, rim=5 if high else 3, relief_in=rin, relief_out=rout, flip=s < 0, uv_mode='fan', fan_angles=th)
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
BUD_PETALS = 6            # round 6: six layered petals (three read too simple; 4-details.png panel 4)
BUD_ROLL = 30.0            # degrees: one petal faces forward and down, toward the front camera (plans.quadruped.bud_petals)
BUD_SEPALS = 5
BUD_H = 0.175              # the bud's length along its axis, base to point (2-turnaround: about 0.2 m with the sepals)
BUD_R0, BUD_RMAX = 0.034, 0.047     # profile: radius at the base and the swell's amplitude (0.158 m wide)
BUD_SPAN = math.radians(104.0)      # each petal's width round the axis (round 6: six petals, each overlapping the next)


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
    nu, nv = ((44, 26) if not quick else (24, 14)) if high else (12, 9)       # round 6: six petals
    U, V = grid(nu, nv)
    # round 2: a soft point, not a spike (the open flower read as a thistle): the width holds longer, then rounds off
    span = BUD_SPAN * (1.0 - 0.42 * smooth(0.5, 1.0, U) ** 1.4)     # round 5: a pointed tip on each petal
    # each petal swells across on its own (a cupped petal, not a slice of a smooth egg), its tip flares out a touch, and
    # alternate petals end a little lower so the points stagger
    cupx = 0.008 * np.sin(np.pi * V) * np.sin(np.pi * np.clip(U, 0, 1) ** 0.8)
    flare = 0.004 * smooth(0.75, 1.0, U)
    H = BUD_H * (1.0 - 0.035 * (i % 2))
    # round 3b: the shingle's step fades toward the point, so the tips lie on one another (dark slits between them)
    shingle = 0.17 * (1.0 - 0.7 * smooth(0.55, 1.0, U))          # round 5: the overlaps read clearly
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
    # round 4: lower again (0.155 in round 3b, to fill the hit's slits, which the calmer flick no longer opens): a small
    # light centre in the open flower, not a grey-mauve cone
    P = _round_piece(v3(tip), d, e1, e2, phi, U, V, 0.12, prof, span, 0.1, h0=0.004)
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


def pistil_arrays(tip, prev, high: bool, quick: bool):
    """Round 5: the open flower's pistil: a short pale-green column with a round top at the centre (rigid on the trunk's
    last bone; the stamens ring it). Replaces round 4's cone of inner petals, which read as a grey dome."""
    d, e1, e2, _phis = bud_frame(tip, prev)
    nu, nv = ((16, 24) if not quick else (8, 14)) if high else (5, 8)
    U, V = grid(nu, nv)
    a = 2 * np.pi * V * nv / (nv + 1)
    radial = np.cos(a)[..., None] * e1 + np.sin(a)[..., None] * e2
    r = 0.0075 * np.sqrt(np.clip(1.0 - U ** 6, 0, 1)) + 0.0045 * np.sin(np.pi * np.clip(U, 0, 1) ** 1.5) + 0.0005
    P = v3(tip) + d * (0.006 + 0.03 * U)[..., None] + r[..., None] * radial
    T = np.full(U.shape, 0.003)
    Pu = np.gradient(P, axis=0)
    Pv = np.gradient(P, axis=1)
    q = P[nu // 2, nv // 4] - v3(tip)
    flip = float(np.cross(Pu[nu // 2, nv // 4], Pv[nu // 2, nv // 4]) @ (q - d * (q @ d))) < 0
    return shell(P, T, rim=2, flip=flip, uv_mode='plane')


STAMENS = 14


def stamen_arrays(tip, prev, k: int, high: bool, quick: bool):
    """Round 5: stamen k of the ring round the pistil: a thin cream filament rising and leaning out, ending in a
    yellow anther (the strip widens and thickens at its end)."""
    d, e1, e2, _phis = bud_frame(tip, prev)
    nu, nv = ((10, 3) if not quick else (6, 2)) if high else (4, 1)
    U, V = grid(nu, nv)
    ang = 2 * math.pi * (k + 0.37 * (k % 2)) / STAMENS
    radial = math.cos(ang) * e1 + math.sin(ang) * e2
    side = np.cross(d, radial)
    L = 0.026 + 0.006 * ((k * 7) % 3) / 2.0
    lean = math.radians(24.0 + 8.0 * (k % 3))
    along = math.cos(lean) * d + math.sin(lean) * radial
    w = 0.0024 + 0.0034 * smooth(0.55, 0.9, U)
    base = v3(tip) + d * 0.007 + radial * 0.012
    P = base + along * (L * U)[..., None] + side * (w * (V - 0.5))[..., None]
    T = 0.0022 + 0.0026 * smooth(0.55, 0.9, U)
    Pu = np.gradient(P, axis=0)
    Pv = np.gradient(P, axis=1)
    flip = float(np.cross(Pu[nu // 2, 0], Pv[nu // 2, 0]) @ radial) < 0
    return shell(P, np.broadcast_to(T, U.shape).copy(), rim=2, flip=flip)


def sepal_angle(k: int) -> float:
    """Round 5: sepal k's angle round the bud's axis: five, evenly spaced, independent of the three petals."""
    return math.radians(BUD_ROLL) + 2 * math.pi * (k + 0.5) / BUD_SEPALS


def sepal_bones(k: int) -> list[tuple[int, float]]:
    """(petal index, weight) for sepal k: shared between the two petals either side of it by angle, so it opens with them
    and stays under the open flower."""
    step = 2 * math.pi / BUD_PETALS
    a = (sepal_angle(k) - math.radians(BUD_ROLL)) % (2 * math.pi)
    i = int(a // step)
    t = (a - i * step) / step
    return [(i % BUD_PETALS, 1.0 - t), ((i + 1) % BUD_PETALS, t)]


def sepal_arrays(tip, prev, k: int, high: bool, quick: bool):
    """Sepal k: a pointed green leaf cupping the bud's base and the trunk's end, between petals k and k+1 (skinned half
    and half to their bones, so it opens about 44° with them and stays under the open flower, a calyx)."""
    d, e1, e2, phis = bud_frame(tip, prev)
    nu, nv = ((26, 16) if not quick else (14, 10)) if high else (7, 5)
    U, V = grid(nu, nv)
    phi = sepal_angle(k)
    H = 0.14                  # round 6: long pointed sepals clasping the bud about 40% up, from below its base
    h0 = -0.045
    # radius over the bud's own profile at that height, a little outside it, leaning out at the tip
    hb = np.clip((h0 + H * U) / BUD_H, 0, 1)
    prof = np.maximum(bud_profile(hb), 0.042) + 0.012 + 0.006 * smooth(0.6, 1.0, U)     # just outside the shingled petals
    span = math.radians(66) * (1.0 - smooth(0.15, 1.0, U) ** 1.0 * 0.97)
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
    nu, nv = ((40, 16) if not quick else (20, 10)) if high else (9, 5)
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
