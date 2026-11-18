"""Lootlid's arched lid straps, leg cuffs and hinges (Art 2.1 Ultra; lootlid_trim.py is the rest of the gold).

The lid's strap wraps each side's rounded edge: its centre line is where the lid's surface turns 45° between the side
face and the front, the barrel top or the back (found ring by ring on a fine copy of the lid's outer loft), from the
front corner at the seam, up and over, to the back corner at the seam; across it, points in the tangent plane are
pulled onto the surface (a BVH), so the gold follows the rounded edge like a bent strap.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import lootlid_form as F
from monsters.breeds import lootlid_geo as G
from monsters.breeds import lootlid_trim as T

STRAP_HALF, STRAP_BEV = 0.06, 0.007
_LID: dict = {}


def vertex_normals(pc: dict) -> np.ndarray:
    v = pc['v']
    t = G.tri_of(pc['f'])
    fn = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    n = np.zeros_like(v)
    for i in range(3):
        np.add.at(n, t[:, i], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def lid_outer():
    """A fine loft of the lid's outer surface only (its BVH, its rings and their normals)."""
    if _LID:
        return _LID
    nu = 1536
    rows = [(F.Z_LB, 0.0, 0.0, 0.0, 0.0)]
    for z in np.linspace(F.Z_LB + 0.002, F.LID_SPRING, 70):
        a, b = F.lid_ab(float(z))
        rows.append((float(z), a, b, 0.0, 0.0))
    for al in np.radians(np.linspace(0.0, 89.5, 240)[1:]):
        z = F.LID_SPRING + F.LID_RZ * math.sin(al)
        a, _b = F.lid_ab(z)
        rows.append((z, a, F.LID_B * math.cos(al), 0.0, 0.0))
    rows.append((F.Z_TOP, 0.0, 0.0, 0.0, 0.0))
    pc = G.loft(rows, G.unit_ring(F.LID_N, nu, F.LID_B / F.LID_A), F.LID_BULGE)
    _LID.update({'pc': pc, 'nu': nu, 'nrows': len(rows), 'n': vertex_normals(pc), 'bvh': G.bvh(pc)})
    return _LID


def _crossing(P: np.ndarray, Nn: np.ndarray, ks: list[int], level: float = 0.7071):
    """Along the ring indices ks (from the side face outward), where the normal's x first drops below `level`."""
    nx = Nn[ks, 0]
    if nx[0] < level:
        return None
    j = np.nonzero(nx < level)[0]
    if not len(j):
        return None
    j = int(j[0])
    t = (nx[j - 1] - level) / max(nx[j - 1] - nx[j], 1e-9)
    p = P[ks[j - 1]] * (1 - t) + P[ks[j]] * t
    n = Nn[ks[j - 1]] * (1 - t) + Nn[ks[j]] * t
    return p, n / np.linalg.norm(n)


def strap_path() -> tuple[np.ndarray, np.ndarray]:
    """The left strap's centre line (front seam → over the top → back seam) and the surface normals on it."""
    L = lid_outer()
    pc, nu, Nv = L['pc'], L['nu'], L['n']
    front, back = [], []
    for r in range(1, L['nrows'] - 1):
        idx = 1 + (r - 1) * nu + np.arange(nu)
        P, Nn = pc['v'][idx], Nv[idx]
        b = _crossing(P, Nn, list(range(0, nu // 4)))
        f = _crossing(P, Nn, [0] + list(range(nu - 1, 3 * nu // 4, -1)))
        if b is None or f is None:
            continue
        front.append(f)
        back.append(b)
    pts = [p for p, _n in front] + [p for p, _n in back[::-1]]
    nrm = [n for _p, n in front] + [n for _p, n in back[::-1]]
    return np.array(pts), np.array(nrm)


def _resample(P: np.ndarray, Nn: np.ndarray, step: float) -> tuple[np.ndarray, np.ndarray]:
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    keep = np.concatenate([[True], seg > 1e-7])
    P, Nn = P[keep], Nn[keep]
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(math.ceil(cum[-1] / step)) + 1)
    w = np.linspace(0.0, cum[-1], n)
    Q = np.stack([np.interp(w, cum, P[:, i]) for i in range(3)], axis=1)
    M = np.stack([np.interp(w, cum, Nn[:, i]) for i in range(3)], axis=1)
    return Q, M / np.linalg.norm(M, axis=1, keepdims=True)


def lid_strap(high: bool) -> tuple[dict, np.ndarray, np.ndarray]:
    """The left strap (a closed slab), and its rivets' points and normals."""
    L = lid_outer()
    P, Nn = strap_path()
    P, Nn = _resample(P, Nn, 0.004)
    P = G.smooth_rows(P, 30, 0.5)
    P, Nn = G.nearest(L['bvh'], P)
    Pr, Nr = P.copy(), G.smooth_rows(Nn, 10, 0.5)
    P, Nn = _resample(P, G.smooth_rows(Nn, 10, 0.5), 0.0016 if high else 0.02)
    Tg = np.gradient(P, axis=0)
    Tg /= np.linalg.norm(Tg, axis=1, keepdims=True)
    A = np.cross(Nn, Tg)
    A /= np.linalg.norm(A, axis=1, keepdims=True)
    a = T.across(STRAP_HALF, STRAP_BEV, high, mid=9)
    raw = P[:, None, :] + a[None, :, None] * A[:, None, :] + Nn[:, None, :] * 0.0005
    loc, nrm = G.nearest(L['bvh'], raw.reshape(-1, 3))
    loc, nrm = loc.reshape(raw.shape), nrm.reshape(raw.shape)
    for _ in range(6):
        nrm[1:-1] = 0.5 * nrm[1:-1] + 0.25 * (nrm[:-2] + nrm[2:])
        nrm[:, 1:-1] = 0.5 * nrm[:, 1:-1] + 0.25 * (nrm[:, :-2] + nrm[:, 2:])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    rel = T.hammer(loc, 61) if high else None
    rings = T.slab_rings(loc, nrm, a, STRAP_HALF, STRAP_BEV, T.BAND_T, rel, thin=not high)
    pc = T.finish(T.band_piece(rings, False, T.slab_attrs(len(rings), len(a), a, STRAP_HALF, thin=not high), rel), pk=T.PK_LID)
    # rivets every 9 cm along the centre, the first a little up from the seam (exact arc lengths of the shared path)
    seg = np.linalg.norm(np.diff(Pr, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    rp, rn = [], []
    for w in np.arange(0.035, cum[-1] - 0.02, 0.09):
        p_ = np.array([np.interp(w, cum, Pr[:, i]) for i in range(3)])
        n_ = np.array([np.interp(w, cum, Nr[:, i]) for i in range(3)])
        n_ /= np.linalg.norm(n_)
        rp.append(p_ + n_ * T.BAND_T)
        rn.append(n_)
    return pc, np.array(rp), np.array(rn)


def mirror_x(pc: dict) -> dict:
    out = {'v': pc['v'] * np.array([-1.0, 1.0, 1.0]), 'f': pc['f'].copy(), 'a': {k: v.copy() for k, v in pc['a'].items()}}
    return G.outward(out)


def lid_straps(high: bool) -> list[dict]:
    pc, rp, rn = lid_strap(high)
    rv = T.rivets(rp, rn, high, pk=T.PK_LID)
    left = [pc] + rv
    return left + [mirror_x(p) for p in left]


# ----------------------------------------------------------------------------- the posts' cuffs
CUFF_Z, CUFF_HALF = 0.082, 0.031


def cuffs(high: bool) -> list[dict]:
    out = []
    a = T.across(CUFF_HALF, 0.006, high)
    for i, key in enumerate(F.LEGS):
        r_mean = F.lerp_tab(F.LEG_R, CUFF_Z)
        n_th = int(2 * math.pi * r_mean / (0.0016 if high else 0.024))
        th = np.linspace(0, 2 * math.pi, n_th, endpoint=False)
        zz = CUFF_Z + a
        base = np.zeros((n_th, len(a), 3))
        for k, z in enumerate(zz):
            c = F.leg_axis(key, float(z))
            r = F.lerp_tab(F.LEG_R, float(z))
            base[:, k] = c[None] + r * np.stack([np.cos(th), np.sin(th), np.zeros_like(th)], axis=1)
        nrm = np.repeat(np.stack([np.cos(th), np.sin(th), np.zeros_like(th)], axis=1)[:, None, :], len(a), axis=1)
        rel = T.hammer(base, 70 + i) if high else None
        rings = T.slab_rings(base, nrm, a, CUFF_HALF, 0.006, 0.0085, rel)
        out.append(T.finish(T.band_piece(rings, True, T.slab_attrs(n_th, len(a), a, CUFF_HALF), rel), pk=T.PK_CUFF, leg=float(i + 1)))
        c = F.leg_axis(key, CUFF_Z)
        r = F.lerp_tab(F.LEG_R, CUFF_Z) + 0.0085
        ang = np.radians(np.arange(5) * 72.0 + 30.0)
        pts = [c + r * np.array([math.cos(t), math.sin(t), 0.0]) for t in ang]
        nrms = [np.array([math.cos(t), math.sin(t), 0.0]) for t in ang]
        out += T.rivets(pts, nrms, high, r=0.0115, h=0.0068, pk=T.PK_CUFF, leg=float(i + 1))
    return out


# ----------------------------------------------------------------------------- the hinges
def slab_xz(x0: float, x1: float, z0: float, z1: float, y0: float, t: float, r: float, nu: int) -> dict:
    """A plate in the XZ plane (rounded corners of radius r), from y0 back to y0 + t."""
    cx, cz, hx, hz = 0.5 * (x0 + x1), 0.5 * (z0 + z1), 0.5 * (x1 - x0), 0.5 * (z1 - z0)
    n = 6.0
    rows = [(0.0, 0.0, 0.0, 0.0, 0.0), (0.0, hx * 0.96, hz * 0.96, 0.0, 0.0), (0.12 * t, hx, hz, 0.0, 0.0),
            (0.88 * t, hx, hz, 0.0, 0.0), (t, hx * 0.96, hz * 0.96, 0.0, 0.0), (t, 0.0, 0.0, 0.0, 0.0)]
    pc = G.loft(rows, G.unit_ring(n, nu, hz / hx))
    v = pc['v']
    pc['v'] = np.stack([cx + v[:, 0], y0 + v[:, 2], cz + v[:, 1]], axis=1)
    return G.outward(pc)


def hinges(high: bool) -> list[dict]:
    hy, hz = F_HINGE()
    out = []
    nu = 40 if high else 10
    for hx in T.HINGE_X:
        for (x0, x1), pk in (((hx - 0.046, hx - 0.0155), T.PK_HINGE_BOX), ((hx - 0.0135, hx + 0.0135), T.PK_HINGE_LID),
                             ((hx + 0.0155, hx + 0.046), T.PK_HINGE_BOX)):
            xs = np.linspace(x0, x1, 12 if high else 3)
            path = np.stack([xs, np.full_like(xs, hy), np.full_like(xs, hz)], axis=1)
            out.append(T.finish(G.tube(path, T.HINGE_R, nu, up_hint=(0.0, 0.0, 1.0)), pk=pk, top=1.0))
        # the leaves: the box's down its back over the rim band, the lid's up the lid's back
        out.append(T.finish(slab_xz(hx - 0.044, hx + 0.044, 0.424, hz - 0.004, 0.3025, 0.0045, 0.008, 48 if high else 12),
                            pk=T.PK_HINGE_BOX, top=1.0))
        out.append(T.finish(slab_xz(hx - 0.03, hx + 0.03, hz + 0.008, 0.566, 0.3035, 0.0045, 0.008, 48 if high else 12),
                            pk=T.PK_HINGE_LID, top=1.0))
        for z, pk in ((0.442, T.PK_HINGE_BOX), (0.546, T.PK_HINGE_LID)):
            for dx in ((-0.026, 0.026) if pk == T.PK_HINGE_BOX else (-0.014, 0.014)):
                out += T.rivets([np.array([hx + dx, 0.3075, z])], [np.array([0.0, 1.0, 0.0])], high, r=0.009, h=0.0055, pk=pk)
    return out


def F_HINGE() -> tuple[float, float]:
    from monsters.breeds import lootlid_ultra as R
    return R.HINGE[1], R.HINGE[2]
