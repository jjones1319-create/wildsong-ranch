"""Porcelain Moatshell's blue painting (Art 2.1 Ultra; variant-porcelain-moatshell.png): large blooms and flowing vines
with leaves over the keep's walls, the tower, the rampart and the merlons, painted per vertex on the high keep (about
3 mm a step), so there is no limit on how many (per-pixel marks in a material hit Cycles' shader stack limit).

paint(co, vn, ck) -> (wash, ink, dark): 0..1 masks. wash is the pale blue fill of the outer petals and leaves, ink the
blue of the inner petals, the outlines and the vines, dark the deep blue of the centres. Only on the stone kinds (ck 1..3).
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import moatshell_castle as KC
from monsters.breeds import moatshell_noise as N

smooth = N.smooth
TAU = KC.TAU


def _wall_pt(which: str, th: float, z: float, out: float = 0.0):
    r = float(KC.wall_radius(which, z)) + out
    d = KC.dirv(th)
    return np.array([d[0] * r, d[1] * r, z])


def _clear(which: str, th: float, z: float, rad: float) -> bool:
    """Clear of the slits (with their brick frames) and the door's arch."""
    r = float(KC.wall_radius(which, z))
    for wh, thd, zc in KC.WINDOWS:
        sp = KC.SLIT[wh]
        if wh == which and abs(float(KC.ang_wrap(th - math.radians(thd)))) * r < rad + sp['a'] + 0.022 and                 -sp['hb'] - 0.02 - rad < z - zc < sp['hs'] + sp['a'] + 0.03 + rad:
            return False
    if which == 'wall':
        dz = KC.door_z0()
        if abs(float(KC.ang_wrap(th - math.radians(KC.DOOR['th'])))) * r < rad + 0.085 and z < dz + 0.2 + rad:
            return False
    return True


def layout() -> dict:
    """Blooms [(centre, radius, turn)], vines [polyline], leaves [(centre, along, half-length, half-width)]."""
    blooms, vines, leaves = [], [], []
    # the main wall, densely (round 1): three staggered rows of large blooms between the slits, each joined to the next
    # by a flowing vine with leaves along it
    placed = []
    for row in range(4):
        for i in range(30):
            th = (i + 0.5 * (row % 2)) * TAU / 30 + 0.05 * math.sin(i * 2.3 + row)
            zt = float(KC.skirt_zt(th))
            z = (zt + 0.06, 0.5 * (zt + KC.WALL_ZTOP), KC.WALL_ZTOP - 0.045, 0.62 * zt + 0.38 * KC.WALL_ZTOP)[row] + 0.012 * math.sin(i * 1.3)
            rad = (0.03 + 0.016 * float(N.hash1(i + 40 * row, 701)[0])) if row < 3 else 0.02
            if z - rad < zt + 0.012 or z + rad > KC.WALL_ZTOP - 0.008 or not _clear('wall', th, z, rad):
                continue
            p = _wall_pt('wall', th, z)
            if any(np.linalg.norm(p - q) < 0.75 * (rad + rq) for q, rq in placed):
                continue
            placed.append((p, rad))
            blooms.append((p, rad, float(N.hash1(i + 40 * row, 702)[0]) * TAU))
    # vines: from each bloom to its nearest neighbour a little round to its left
    for k, (p, rad) in enumerate(placed):
        th0 = math.atan2(p[0], -p[1])
        best = None
        for q, rq in placed:
            th1 = math.atan2(q[0], -q[1])
            dt = float(KC.ang_wrap(th1 - th0))
            if 0.05 < dt < 0.6 and (best is None or dt + 2.0 * abs(q[2] - p[2]) < best[0]):
                best = (dt + 2.0 * abs(q[2] - p[2]), q, dt)
        if best is None:
            continue
        _c, q, dt = best
        pts = []
        for j in range(11):
            u = j / 10.0
            th = th0 + dt * u
            z = p[2] + (q[2] - p[2]) * u + 0.025 * math.sin(u * math.pi * 2.0 + k)
            z = min(max(z, float(KC.skirt_zt(th)) + 0.02), KC.WALL_ZTOP - 0.015)
            pts.append(_wall_pt('wall', th, z))
        vines.append(pts)
        for j in (2, 4, 6, 8):
            a, b = pts[j], pts[j + 1]
            along = (b - a) / max(np.linalg.norm(b - a), 1e-9)
            nrm = np.array([a[0], a[1], 0.0])
            nrm /= max(np.linalg.norm(nrm), 1e-9)
            side = np.cross(nrm, along) * (1 if j % 4 == 2 else -1)
            tilt = along * 0.55 + side * 0.84
            leaves.append((a + side * 0.012, tilt / np.linalg.norm(tilt), 0.015, 0.007))
    # the tower
    for i in range(9):
        th = i * TAU / 9 + 0.35
        z = 0.72 + 0.07 * (i % 2)
        if _clear('tower', th, z, 0.024):
            blooms.append((_wall_pt('tower', th, z), 0.022 + 0.006 * float(N.hash1(i, 711)[0]), float(N.hash1(i, 712)[0]) * TAU))
    # the rampart (round 2: varied, not one centred stamp per block): blooms of different sizes set off-centre on most
    # blocks, leaf sprays on others, a vine weaving from bloom to bloom along it
    rim_pts = []
    for k, thc in enumerate(KC.skirt_block_angles()):
        h1, h2, h3 = (float(N.hash1(k, 721 + j)[0]) for j in range(3))
        dth = (h1 - 0.5) * 0.5 * TAU / KC.SKIRT_N
        sv = 0.36 + 0.32 * h2
        p = np.asarray(KC.skirt_outer(thc + dth, sv), np.float64)
        rim_pts.append(p)
        if k % 4 != 3:
            blooms.append((p, 0.021 + 0.017 * h3, h1 * TAU))
        else:
            nr, nz = KC.skirt_normal(thc)
            d = KC.dirv(thc)
            nrm = np.array([d[0] * nr, d[1] * nr, nz])
            for j in range(3):
                ang = -0.6 + 0.6 * j
                tan = np.array([math.cos(thc), math.sin(thc), 0.0])
                up = np.cross(nrm, tan)
                along = tan * math.cos(ang) + up * math.sin(ang)
                leaves.append((p + along * 0.016, along / np.linalg.norm(along), 0.016, 0.007))
    for k in range(len(rim_pts)):
        a_, b_ = rim_pts[k], rim_pts[(k + 1) % len(rim_pts)]
        tha, thb = math.atan2(a_[0], -a_[1]), math.atan2(b_[0], -b_[1])
        dt = float(KC.ang_wrap(thb - tha))
        pts = []
        for j in range(9):
            u = j / 8.0
            sv = 0.5 + 0.28 * math.sin(u * math.pi * 2.0 + k) * math.sin(u * math.pi)
            pts.append(np.asarray(KC.skirt_outer(tha + dt * u, sv), np.float64))
        vines.append(pts)
    # the merlons: a small flower on each one's outer face
    rc = KC.WALL_RT - 0.5 * KC.WALL_T
    for k in range(KC.MERLON_N):
        thc = (k + 0.5) * TAU / KC.MERLON_N
        d = KC.dirv(thc)
        z = KC.WALL_ZTOP + 0.5 * KC.MERLON_H - 0.004
        r = rc + 0.5 * KC.WALL_T + 0.0015
        blooms.append((np.array([d[0] * r, d[1] * r, z]), 0.016, float(N.hash1(k, 731)[0]) * TAU))
    return {'blooms': blooms, 'vines': vines, 'leaves': leaves}


def _near(co: np.ndarray, order: np.ndarray, xs: np.ndarray, c: np.ndarray, r: float) -> np.ndarray:
    lo, hi = np.searchsorted(xs, c[0] - r), np.searchsorted(xs, c[0] + r)
    idx = order[lo:hi]
    d = co[idx] - c
    return idx[(np.abs(d[:, 1]) < r) & (np.abs(d[:, 2]) < r)]


def paint(co: np.ndarray, vn: np.ndarray, ck: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(co)
    wash, ink, dark = np.zeros(n), np.zeros(n), np.zeros(n)
    stone = (ck > 0.5) & (ck < 3.5)
    order = np.argsort(co[:, 0])
    xs = co[order, 0]
    L = layout()
    for c, R, rot in L['blooms']:
        idx = _near(co, order, xs, c, 1.25 * R)
        idx = idx[stone[idx]]
        if not len(idx):
            continue
        nrm = vn[idx].mean(axis=0)
        nrm /= max(np.linalg.norm(nrm), 1e-9)
        t = np.cross(nrm, np.array([0.0, 0.0, 1.0]))
        t = t / max(np.linalg.norm(t), 1e-9) if np.linalg.norm(t) > 1e-6 else np.array([1.0, 0.0, 0.0])
        b = np.cross(nrm, t)
        q = co[idx] - c
        depth = np.abs(q @ nrm)
        x, y = q @ t, q @ b
        rho = np.sqrt(x * x + y * y) / R
        phi = np.arctan2(y, x) + rot
        ro = 0.62 + 0.38 * np.abs(np.cos(3.0 * phi)) ** 0.6
        ri = 0.56 * (0.6 + 0.4 * np.abs(np.cos(2.5 * phi + 0.4)) ** 0.7)
        ok = depth < 0.35 * R + 0.006
        outer = smooth(ro + 0.03, ro - 0.03, rho) * ok
        inner = smooth(ri + 0.03, ri - 0.03, rho) * ok
        line = np.exp(-((rho - ro) / 0.07) ** 2) * (rho < ro + 0.1) * ok
        vein = np.exp(-(np.sin(3.0 * phi) * rho / 0.05) ** 2) * smooth(0.18, 0.3, rho) * outer * (1 - inner) * 0.6
        cen = smooth(0.24, 0.17, rho) * ok
        wash[idx] = np.maximum(wash[idx], outer)
        ink[idx] = np.maximum(ink[idx], np.maximum.reduce([inner, line, vein]))
        dark[idx] = np.maximum(dark[idx], np.maximum(cen, 0.6 * inner * smooth(0.45, 0.2, rho)))
    for pts in L['vines']:
        pts = np.asarray(pts)
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            mid = 0.5 * (a + b)
            r = 0.5 * np.linalg.norm(b - a) + 0.008
            idx = _near(co, order, xs, mid, r)
            idx = idx[stone[idx]]
            if not len(idx):
                continue
            d, _u = N.seg_dist(co[idx], a, b)
            w = 0.0042 * (0.8 + 0.2 * math.sin(k * 0.9))
            ink[idx] = np.maximum(ink[idx], smooth(w + 0.0012, w - 0.0008, d))
    for c, along, hl, hw in L['leaves']:
        idx = _near(co, order, xs, c, hl + 0.006)
        idx = idx[stone[idx]]
        if not len(idx):
            continue
        q = co[idx] - c
        u = q @ along
        side = np.cross(vn[idx].mean(axis=0), along)
        side /= max(np.linalg.norm(side), 1e-9)
        v = q @ side
        e = (u / hl) ** 2 + (v / (hw * (1.0 - 0.35 * (u / hl)))) ** 2
        leaf = smooth(1.05, 0.9, e)
        rib = np.exp(-(v / 0.0009) ** 2) * leaf
        wash[idx] = np.maximum(wash[idx], leaf)
        ink[idx] = np.maximum(ink[idx], np.maximum(rib, np.exp(-((np.sqrt(e) - 1.0) / 0.08) ** 2) * (e < 1.3)))
    return wash, ink, dark
