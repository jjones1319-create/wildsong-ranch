"""The sand's fine relief for the Crown Amphitheatre, drawn with numpy (no Blender here, so it can be checked alone).

A height field (metres) of rake grooves (round the ellipse outside the ring, in circles inside it), trampled where
fighters walk, paw-print trails in from the gates and scuffles inside the ring, skid marks, pebbles and low dunes;
lit by the arena's sun in software, because the baked light is too soft to carry 5 mm grooves. Returns RGB images:
R = the relief's light (×2), G = how disturbed the sand is (darker, damper), B = chalk (the ring line, the start marks
and the Guild emblem at the centre).
"""
from __future__ import annotations

import math

import numpy as np

A0, B0 = 27.0, 20.0


def _grid(x0: float, x1: float, y0: float, y1: float, w: int, h: int):
    x = x0 + (np.arange(w) + 0.5) / w * (x1 - x0)
    y = y0 + (np.arange(h) + 0.5) / h * (y1 - y0)
    return np.meshgrid(x, y)            # rows = y (bottom-up order is chosen by the caller)


def _noise(X, Y, scale: float, seed: int) -> np.ndarray:
    """Cheap smooth noise: a sum of a few randomly oriented sines."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(X)
    for k in range(6):
        a = rng.uniform(0, math.pi)
        f = scale * (1.6 ** k) * rng.uniform(0.8, 1.2)
        out += np.sin((X * math.cos(a) + Y * math.sin(a)) * f + rng.uniform(0, 6.3)) / (1.5 ** k)
    return out / 2.2


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def trails(seed: int = 3) -> list[tuple[np.ndarray, float]]:
    """Paw-print trails: (points (N, 3) = x, y, heading, paw size)."""
    rng = np.random.default_rng(seed)
    out = []
    for sx in (-1, 1):                                    # in from each gate ramp to the start marks
        for k in range(3):
            pts = []
            x, y = sx * 19.5, rng.uniform(-1.2, 1.2)
            while abs(x) > 2.0:
                h = math.atan2(-y * 0.05, -sx) + rng.normal(0, 0.12)
                x, y = x + math.cos(h) * 0.42, y + math.sin(h) * 0.42
                pts.append((x, y, h))
            out.append((np.asarray(pts), rng.uniform(0.85, 1.25)))
    for k in range(14):                                   # scuffles inside the ring
        pts = []
        r, a = rng.uniform(0.5, 4.8), rng.uniform(0, 2 * math.pi)
        x, y, h = r * math.cos(a), r * math.sin(a), rng.uniform(0, 2 * math.pi)
        for _ in range(rng.integers(10, 30)):
            h += rng.normal(0, 0.35)
            x, y = x + math.cos(h) * 0.36, y + math.sin(h) * 0.36
            if math.hypot(x, y) > 5.6:
                h += math.pi * 0.8
            pts.append((x, y, h))
        out.append((np.asarray(pts), rng.uniform(0.8, 1.3)))
    for k in range(5):                                    # attendants' boots round the outer sand
        pts = []
        a0 = rng.uniform(0, 2 * math.pi)
        rho = rng.uniform(0.55, 0.9)
        for i in range(60):
            a = a0 + i * 0.012
            x, y = A0 * rho * math.cos(a), B0 * rho * math.sin(a)
            h = math.atan2(B0 * math.cos(a), -A0 * math.sin(a))
            pts.append((x, y, h))
        out.append((np.asarray(pts), -1.0))
    return out


def _stamp(H, D, X0, Y0, px, x, y, h, size, side, boot: bool) -> None:
    """One print into height H and disturbance D (in place). px = metres per pixel."""
    ca, sa = math.cos(h), math.sin(h)
    ox, oy = x - sa * side * 0.09 * size, y + ca * side * 0.09 * size
    pads = [(0.0, 0.0, 0.045 * size, 0.040 * size, 1.0)] if not boot else [(0.0, 0.0, 0.055, 0.13, 0.8)]
    if not boot:
        for k, ang in enumerate((-0.75, -0.25, 0.25, 0.75)):
            pads.append((0.07 * size * math.cos(ang * 0.6), 0.07 * size * math.sin(ang * 0.6) * 1.4, 0.019 * size, 0.017 * size, 0.8))
    r = int(0.16 * max(size, 1.0) / px) + 2
    i0, j0 = int((ox - X0) / px), int((oy - Y0) / px)
    if i0 < r or j0 < r or i0 >= H.shape[1] - r or j0 >= H.shape[0] - r:
        return
    sl = (slice(j0 - r, j0 + r), slice(i0 - r, i0 + r))
    lx = X0 + (np.arange(i0 - r, i0 + r) + 0.5) * px - ox
    ly = Y0 + (np.arange(j0 - r, j0 + r) + 0.5) * px - oy
    LX, LY = np.meshgrid(lx, ly)
    u, v = LX * ca + LY * sa, -LX * sa + LY * ca
    dent = np.zeros_like(u)
    for (cu, cv, ru, rv, depth) in pads:
        d = ((u - cu) / ru) ** 2 + ((v - cv) / rv) ** 2
        dent = np.maximum(dent, depth * _smooth(1.25, 0.6, d))
    H[sl] -= 0.006 * dent
    rim = _smooth(2.2, 1.0, ((u - 0.01) / (0.1 * size)) ** 2 + (v / (0.08 * size)) ** 2) - dent
    H[sl] += 0.0015 * np.clip(rim, 0, 1)
    D[sl] = np.maximum(D[sl], 0.55 * dent)


def relief(x0: float, x1: float, y0: float, y1: float, w: int, h: int, sun, emblem=None) -> np.ndarray:
    """RGB (h, w, 3) float rows bottom-up (Blender's order) for the floor rectangle [x0, x1] × [y0, y1]."""
    X, Y = _grid(x0, x1, y0, y1, w, h)
    px = (x1 - x0) / w
    r = np.hypot(X, Y)
    rho = np.sqrt((X / A0) ** 2 + (Y / B0) ** 2) * B0          # ~metres in from the wall along the short axis
    warp = 0.05 * _noise(X, Y, 0.9, 1)
    band = np.floor((rho + warp) / 0.62)
    phase = (band * 0.618) % 1.0
    outer = np.sin(2 * math.pi * ((rho + warp) / 0.075 + phase * 3.0)) * 0.0022
    inner = np.sin(2 * math.pi * ((r + 0.05 * _noise(X, Y, 1.4, 2)) / 0.06)) * 0.0011 * (0.55 + 0.45 * _noise(X, Y, 0.7, 8))
    trample = np.clip(_smooth(1.1, 0.0, np.abs(r - 6.2)) * 0.9 + _smooth(2.6, 0.6, np.abs(Y)) * _smooth(5.0, 7.0, np.abs(X)) * 0.8
                      + _smooth(1.4, 0.2, np.hypot(np.abs(X) - 2.4, Y)) * 0.7, 0, 1)
    H = np.where(r < 6.0, inner, outer) * (1.0 - 0.85 * trample)
    H += 0.004 * _noise(X, Y, 0.35, 4) + 0.0012 * _noise(X, Y, 6.0, 5)
    D = 0.25 * trample * (0.6 + 0.4 * _noise(X, Y, 2.0, 6))
    rng = np.random.default_rng(9)
    for pts, size in trails():
        boot = size < 0
        for k, (x, y, hd) in enumerate(pts):
            if x0 - 0.3 < x < x1 + 0.3 and y0 - 0.3 < y < y1 + 0.3:
                _stamp(H, D, x0, y0, px, x, y, hd, abs(size) if not boot else 1.0, 1 if k % 2 else -1, boot)
    for _ in range(9):                                            # skid marks inside the ring
        a, rr = rng.uniform(0, 2 * math.pi), rng.uniform(1.0, 4.5)
        cx, cy, hd, ln = rr * math.cos(a), rr * math.sin(a), rng.uniform(0, 2 * math.pi), rng.uniform(0.8, 2.4)
        u = (X - cx) * math.cos(hd) + (Y - cy) * math.sin(hd)
        v = -(X - cx) * math.sin(hd) + (Y - cy) * math.cos(hd) - 0.08 * (u / ln) ** 2
        m = _smooth(0.09, 0.03, np.abs(v)) * _smooth(0.0, 0.3, u) * _smooth(ln, ln - 0.4, u)
        H -= 0.004 * m
        D = np.maximum(D, 0.5 * m)
    peb = rng.random(X.shape) > 0.9993
    H += 0.003 * peb
    gx, gy = np.gradient(H, px, axis=1), np.gradient(H, px, axis=0)
    s = np.asarray(sun, np.float64) / np.linalg.norm(sun)
    light = 1.0 + (-gx * s[0] - gy * s[1]) / s[2]
    light = np.clip(light, 0.55, 1.45) * (1.0 - np.clip(-H, 0, 0.01) * 18.0)
    chalk = np.zeros_like(X)
    chalk = np.maximum(chalk, _smooth(0.045, 0.025, np.abs(r - 1.55)) * 0.3)
    chalk = np.maximum(chalk, _smooth(0.05, 0.03, np.abs(np.abs(X) - 2.4)) * _smooth(0.5, 0.44, np.abs(Y)))
    if emblem is not None:                                       # the Guild emblem, 2.6 m across, lime-washed
        n = emblem.shape[0]
        iu = np.clip(((X / 2.6 + 0.5) * n).astype(int), 0, n - 1)
        iv = np.clip(((0.5 - Y / 2.6) * n).astype(int), 0, n - 1)
        inside = (np.abs(X) < 1.3) & (np.abs(Y) < 1.3)
        chalk = np.maximum(chalk, np.where(inside, emblem[iv, iu], 0.0) * 0.24)
    chalk *= 0.55 + 0.45 * _smooth(-0.3, 0.6, _noise(X, Y, 9.0, 7)) * (1.0 - 0.7 * np.clip(D * 2, 0, 1))
    return np.stack([light / 2.0, np.clip(D, 0, 1), np.clip(chalk, 0, 1)], -1).astype(np.float32)
