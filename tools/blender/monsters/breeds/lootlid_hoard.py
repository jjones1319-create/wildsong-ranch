"""Lootlid's hoard and tongue (Art 2.1 Ultra; 1-hero, 2-turnaround open view, 4-details panel 4):

  - the coin heap (rigid on `prop.hoard`): a mound filling the box's hollow and rising above its rim in the middle; the
    high source piles about 250 real coins on it (a raised rim, a four-petal emblem, a few on edge, a glint on some),
    the game mesh keeps the heap and the hundred or so coins on top as real discs (the rest come from the bake);
  - the tongue (three bones that slide out, plans/construct.py): long, broad, thick and round, with a groove down its
    middle and a rounded tip, lying on the coins from the back of the box to just inside its front wall; its root
    dives into the heap; a trough under it keeps the coins out of its bake.
Round 3 (review): no mouth lining. A chest is hollow: an open lid shows its sides open, as in 1-hero.
"""
from __future__ import annotations

import math

import numpy as np

from lib import ultra as U
from monsters.breeds import lootlid_form as F
from monsters.breeds import lootlid_geo as G
from monsters.breeds import lootlid_noise as N
from monsters.breeds import lootlid_trim as T

PK_COIN, PK_TONGUE, PK_LINING, PK_HEAP = 7, 8, 9, 10
COIN_T = 0.0058
TROUGH_Z = 0.455


# ----------------------------------------------------------------------------- the heap
def heap_h(x, y) -> np.ndarray:
    """The heap's surface height (under the coins)."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    p = np.stack([x, y, np.zeros_like(x)], axis=-1).reshape(-1, 3)
    # round 2: piled level with the front rim, a mound rising above it in the middle; polish pass: the mound is two
    # heaps either side of the tongue's trough (the middle one was all trough), rising 2.5-3 cm over the rim
    lobe = np.exp(-(((np.abs(x) - 0.205) / 0.115) ** 2 + ((y - 0.03) / 0.165) ** 2))
    h = (0.474 + 0.024 * np.exp(-((x / 0.22) ** 2 + ((y - 0.02) / 0.16) ** 2)) + 0.042 * lobe
         + 0.005 * N.fbm(p, 1 / 0.06, 401, 2).reshape(x.shape))
    # a flat floor under the tongue's footprint, low enough that its bake sees only itself (coins 2 cm under it)
    tr = N.smooth(0.19, 0.13, np.abs(x)) * N.smooth(-0.27, -0.24, y)
    return h * (1 - tr) + np.minimum(h, TROUGH_Z) * tr


def heap_normal(x, y) -> np.ndarray:
    e = 0.004
    hx = (heap_h(x + e, y) - heap_h(x - e, y)) / (2 * e)
    hy = (heap_h(x, y + e) - heap_h(x, y - e)) / (2 * e)
    n = np.stack([-hx, -hy, np.ones_like(hx)], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def cavity_ab(z: float, extra: float = 0.0) -> tuple[float, float]:
    a, b = F.box_ab(z)
    return a - F.WALL - extra, b - F.WALL - extra


def heap(high: bool) -> dict:
    """The heap's mound (a closed lump: its top under the coins, its sides down the hollow's walls to the floor)."""
    nu = 160 if high else 40
    cs = G.unit_ring(F.BOX_N, nu, F.BOX_B / F.BOX_A)
    a, b = cavity_ab(0.45, 0.004)
    ks = np.linspace(0.04, 1.0, 60 if high else 10)
    rings = []
    for k in ks:
        x, y = G.ring_xy(cs, a * k, b * k, F.BOX_BULGE)
        h = heap_h(x, y) + (0.0 if high else -0.002)
        rings.append(np.stack([x, y, h], axis=1))
    x, y = G.ring_xy(cs, a, b, F.BOX_BULGE)
    rings.append(np.stack([x, y, np.full(nu, F.FLOOR_Z + 0.006)], axis=1))
    rings.append(np.stack([x * 0.04, y * 0.04, np.full(nu, F.FLOOR_Z + 0.006)], axis=1))
    return T.finish(G.sweep(rings, closed=False), pk=PK_HEAP, top=1.0)


# ----------------------------------------------------------------------------- the coins
def coin_layout() -> list[dict]:
    """Every coin of the high source (three loose layers), each with its centre, normal, spin, radius and whether the
    game mesh keeps it (the top layer's, spaced out)."""
    coins = []
    a, b = cavity_ab(0.45, 0.0)
    for layer, (step, lift, seed) in enumerate(((0.036, 0.0022, 501), (0.036, 0.0052, 502), (0.042, 0.0085, 503))):
        off = 0.5 * step * (layer % 2)
        xs = np.arange(-a, a + 1e-9, step) + off
        ys = np.arange(-b, b + 1e-9, step * 0.92) + off
        X, Y = np.meshgrid(xs, ys, indexing='ij')
        X, Y = X.ravel(), Y.ravel()
        n = len(X)
        r1, r2, r3, r4, r5 = (N.hash1(np.arange(n) + 1000 * layer, seed + i) for i in range(5))
        X = X + (r1 - 0.5) * step * 0.7
        Y = Y + (r2 - 0.5) * step * 0.7
        rad = 0.0205 + 0.0045 * r3
        rho = (np.abs(X / (a - 0.03)) ** F.BOX_N + np.abs(Y / (b - 0.03)) ** F.BOX_N) ** (1 / F.BOX_N)
        ok = (rho < 1.0) & (np.abs(X) < a - 0.006 - rad) & (Y < b - 0.006 - rad) & (Y > -b + 0.02)
        # in the trough under the tongue only the two lower layers, and none by its root
        ok &= (np.abs(X) > 0.156) | ((layer < 2) & (Y < 0.12))
        if layer == 2:
            ok &= r4 > 0.25
        for i in np.nonzero(ok)[0]:
            hn = heap_normal(X[i], Y[i])
            tilt = np.array([math.cos(r4[i] * 6.283), math.sin(r4[i] * 6.283), 0.0]) * (0.28 + 0.4 * r5[i] * (layer == 2))
            if abs(X[i]) < 0.18:
                tilt *= 0.35               # beside the tongue: lying flat, low in the trough
            elif layer == 2 and r5[i] > 0.86:
                tilt *= 4.5                # round 3: a few standing nearly on edge
            nrm = hn + tilt
            nrm /= np.linalg.norm(nrm)
            c = np.array([X[i], Y[i], float(heap_h(X[i], Y[i])) + lift])
            coins.append({'c': c, 'n': nrm, 'spin': float(r1[i]) * 6.283, 'r': float(rad[i]), 'layer': layer,
                          'glint': bool(r5[i] > 0.8) and layer > 0, 'deep': layer == 0})
    # the game keeps the top layer's coins, at least 4.6 cm apart, plus every coin near the front (seen first)
    kept = []
    for cn in sorted(coins, key=lambda d: -d['c'][2]):
        if cn['layer'] < 1:
            continue
        if all(np.linalg.norm(cn['c'][:2] - k['c'][:2]) > 0.027 for k in kept):
            kept.append(cn)
            cn['lo'] = True
    return coins


def coin_piece(cn: dict, high: bool) -> dict:
    """One coin in its own frame (a disc with a raised rim and, high, a four-petal emblem), placed."""
    R, t = cn['r'], COIN_T
    nth = 44 if high else 11
    th = np.linspace(0, 2 * math.pi, nth, endpoint=False)
    if high:
        ks = np.concatenate([np.linspace(0.03, 0.8, 16), [0.84, 0.88, 0.93, 0.97, 1.0]])
        rows = []
        for k in ks:
            petal = 0.46 * (0.55 + 0.45 * np.abs(np.cos(2 * th)) ** 0.7)
            emb = np.clip((petal - k) / 0.05, 0, 1) * (k > 0.1) + np.clip((0.1 - k) / 0.04, 0, 1)
            rim = np.clip((k - 0.82) / 0.04, 0, 1) * np.clip((0.995 - k) / 0.05, 0, 1)
            h = 0.5 * t + 0.0006 * emb + 0.0009 * rim - 0.0012 * np.clip((k - 0.95) / 0.05, 0, 1)
            rows.append((k, h, emb))
        rows += [(1.0, np.full(nth, 0.0), 0.0), (0.97, np.full(nth, -0.5 * t), 0.0), (0.04, np.full(nth, -0.5 * t), 0.0)]
    else:
        rows = [(1.0, np.full(nth, 0.5 * t), 0.0), (1.0, np.full(nth, -0.5 * t), 0.0)]
    n = cn['n']
    x = np.cross(n, [0.0, 0.0, 1.0]) if abs(n[2]) < 0.95 else np.cross(n, [1.0, 0.0, 0.0])
    x /= np.linalg.norm(x)
    y = np.cross(n, x)
    cs, sn = math.cos(cn['spin']), math.sin(cn['spin'])
    x, y = x * cs + y * sn, -x * sn + y * cs
    rings, embs = [], []
    for k, h, e in rows:
        loc = (k * R * np.cos(th))[:, None] * x + (k * R * np.sin(th))[:, None] * y + np.asarray(h)[:, None] * n
        rings.append(cn['c'] + loc)
        embs.append(np.broadcast_to(np.asarray(e, np.float64), (nth,)))
    pc = G.sweep(rings, closed=False)
    m = len(rings) * nth
    glow = np.zeros(len(pc['v']))
    if high and cn.get('glint'):
        ga = cn['spin'] * 1.7
        gx, gy = 0.5 * R * np.cos(ga), 0.5 * R * np.sin(ga)
        for j, (k, h, _e) in enumerate(rows):
            if np.all(np.asarray(h) > 0):
                d = np.hypot(k * R * np.cos(th) - gx, k * R * np.sin(th) - gy)
                glow[j * nth:(j + 1) * nth] = np.clip((0.26 * R - d) / (0.14 * R), 0, 1)
    emb = np.concatenate([np.concatenate(embs), np.zeros(len(pc['v']) - m)])
    rim = np.concatenate([np.repeat([k for k, _h, _e in rows], nth), np.zeros(len(pc['v']) - m)])
    return T.finish(pc, pk=PK_COIN, top=1.0, emb=emb, bev=np.clip((rim - 0.8) / 0.2, 0, 1), coin=float(N.hash1(int(cn['spin'] * 1e4), 7)[0]),
                    glow=glow, deep=1.0 if cn.get('deep') else 0.0)


def coins(high: bool) -> list[dict]:
    """The game mesh's coins; the high source has those plus the bottom layer (polish pass: only those: the game
    heap's gaps bake the dark bottom layer and the heap, not a pale bed of loose top coins it doesn't have)."""
    return [coin_piece(cn, high) for cn in coin_layout() if cn.get('lo') or (high and cn.get('deep'))]


# ----------------------------------------------------------------------------- the tongue
def _catmull(pts: np.ndarray, n: int) -> np.ndarray:
    P = np.concatenate([[2 * pts[0] - pts[1]], pts, [2 * pts[-1] - pts[-2]]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return np.array(out)


def tongue_points() -> np.ndarray:
    from monsters.breeds import lootlid_ultra as R
    return np.array(R.TONGUE, np.float64)


def tongue(high: bool) -> dict:
    """Broad and thick, a groove down its middle, the tip rounded; the root dives into the heap behind the bones."""
    pts = tongue_points()
    root = pts[0] + np.array([0.0, 0.07, -0.03])
    path = _catmull(np.concatenate([[root], pts]), 40 if high else 6)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    L = s[-1]
    tip_len = 0.055
    Tg, Nm, B = G.frames(path, (0.0, 0.0, 1.0))
    nph = 48 if high else 20
    ph = np.linspace(0, 2 * math.pi, nph, endpoint=False)
    rings = []
    for j in range(len(path)):
        u = s[j] / L
        # polish pass: broader, widening toward the tip (about a third of the box's width)
        hw = 0.09 + 0.016 * N.smooth(0.0, 0.85, u) + 0.006 * math.sin(math.pi * min(1.0, u * 1.3))
        ht = 0.027 - 0.004 * u
        d = L - s[j]
        if d < tip_len:
            q = math.sqrt(max(0.0, 1.0 - ((tip_len - d) / tip_len) ** 2))
            hw, ht = hw * max(q, 0.06), ht * max(math.sqrt(q), 0.12)
        c, sn = np.cos(ph), np.sin(ph)
        groove = 0.4 * np.exp(-(c / 0.18) ** 2) * (sn > 0) * min(1.0, (L - s[j]) / 0.05)
        yy = sn * ht * (1.0 - groove)
        flat = np.sign(sn) * np.abs(sn) ** 0.7 * ht * (1.0 - groove)
        yy = 0.92 * yy + 0.08 * flat
        if high:
            p3 = path[j][None] + (c * hw)[:, None] * B[j] + yy[:, None] * Nm[j]
            yy = yy + 0.00035 * N.fbm(p3, 1 / 0.0035, 411, 1) * (sn > -0.2)
        rings.append(path[j][None] + (c * hw)[:, None] * B[j] + yy[:, None] * Nm[j])
    pc = G.sweep(rings, closed=False)
    m = len(rings) * nph
    tg = np.concatenate([np.repeat(s / L, nph), [0.0, 1.0]])
    up = np.concatenate([np.tile(np.sin(ph), len(rings)), np.zeros(len(pc['v']) - m)])
    return T.finish(pc, pk=PK_TONGUE, top=1.0, tg=tg, bev=np.clip(up, 0, 1))


def build(high: bool, quick: bool) -> list:
    tag = 'hi' if high else 'lo'
    groups = {'hoard': [heap(high)] + coins(high), 'tongue': [tongue(high)]}
    obs = [G.make_object(f'{tag}_{name}', G.merge(pcs)) for name, pcs in groups.items()]
    if not high:
        for ob in obs:
            T.set_texel_k(ob)
    return obs


# ----------------------------------------------------------------------------- weights
def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    from monsters.breeds import lootlid_ultra as R
    pk = np.round(attr('pk')).astype(int)
    leg = np.round(attr('leg')).astype(int)
    regs = [U.rigid(np.isin(pk, (T.PK_BOX, T.PK_HINGE_BOX)), 'hips'),
            U.rigid(np.isin(pk, (T.PK_LID, T.PK_PLATE, T.PK_HINGE_LID)), 'head'),
            U.rigid(np.isin(pk, (PK_COIN, PK_HEAP)), 'prop.hoard')]
    from monsters.breeds import lootlid_legs as L
    for i in range(len(F.LEGS)):
        regs.append(U.rigid(np.isin(pk, (T.PK_CUFF, L.PK_LEG)) & (leg == i + 1), L.bone_of(i)))
    tm = pk == PK_TONGUE
    if tm.any():
        y = co[tm, 1]
        wh = N.smooth(0.175, 0.215, y)
        w1 = N.smooth(0.02, 0.15, y) * (1 - wh)
        w3 = N.smooth(-0.1, -0.175, y)
        w2 = np.clip(1.0 - wh - w1 - w3, 0, 1)
        regs.append((tm, {'hips': wh, 'tongue.1': w1, 'tongue.2': w2, 'tongue.3': w3}))
    lm = pk == PK_LINING
    if lm.any():
        cv = np.clip(attr('cv')[lm], 0, 1)
        regs.append((lm, {'hips': 1.0 - cv, 'head': cv}))
    return regs
