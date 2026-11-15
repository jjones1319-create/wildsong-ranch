"""Quillion's cape (props; quillion_ultra.build_props): a short crimson wool cape fastened at the neck with a small round
brass clasp (1-hero, 2-turnaround, 4-details 5).

- The cape: one thick cloth shell (about 7 mm, a rolled hem a little thicker) from the collar over both shoulders and
  down the back, flaring like a bell to a hem about 15% of the height above the ground (2-turnaround side and front).
  Round 2 (review): one continuous piece from the clasp: its front edges start under the collar beside the clasp,
  run over the shoulder tops (the arms come out under them) and hang behind the arms, wider than the body, so it
  frames the body from the front and reads from the collar down in profile (round 1 started under the quills at
  mid-back). At the back its top lies under the quill mantle (the quills lie over it, as in every picture). Soft
  vertical folds grow toward the hem; a rounded arch at the back lets the tail leave the rump. Three spring chains
  (capeR, capeC, capeL: plans/biped.py `capes`) carry it; quillion_ultra blends their weights across the cloth by `qside`.
- The collar: the cape's top folded into a soft band round the neck and over the shoulders, its folds gathering
  toward the clasp; rigid on the chest.
- The clasp: a brass disc with a raised rim and an embossed sprig (4-details 5), rigid on the chest; it fastens the
  cape's two front edges (round 2: it must read as a cape clasp, not a bell on a collar).

Each part carries the props' common attributes (quillion_quills.ATTRS): part, qt (the cloth's v: 0 at the top, 1 at the
hem; the clasp's radius), qroot, qrand, qside (the cloth's u: −1 at its right front edge, +1 at its left).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib.surface import norm, smooth, v3
from monsters.breeds import quillion_quills as Q

THETA_TOP = math.radians(150.0)     # the cape's front edges at the collar: either side of the clasp
THETA_HEM = math.radians(104.0)     # ... and from the shoulders down: wrapping the shoulders and upper arms (round 3)
NOTCH_H, NOTCH_W = 0.0, 0.42        # round 3: one piece across the back (the tail leaves under the hem)
CAPE_T = 0.007                      # the cloth's thickness
HEM_T = 0.011                       # the rolled hem


def theta_max(v):
    return THETA_HEM + (THETA_TOP - THETA_HEM) * (1.0 - smooth(0.0, 0.26, np.asarray(v, np.float64)))


def z_top(th):
    return 0.47 + 0.022 * np.cos(th)


def z_hem(th):
    return 0.135 + 0.008 * (1.0 - np.cos(th)) + NOTCH_H * np.exp(-(np.asarray(th) / NOTCH_W) ** 2)


def _radii(v):
    v = np.asarray(v, np.float64)
    k = v ** 0.8
    return 0.15 + 0.15 * k, 0.13 + 0.11 * k, 0.025 + 0.02 * v


def cape_surface(u, v, folds: bool = True):
    """The cloth's middle surface at (u, v): u from −1 (its right front edge) through 0 (the back) to +1, v 0 at the
    collar, 1 at the hem."""
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    th = u * theta_max(v)
    rx, ry, cy = _radii(v)
    z = z_top(th) + (z_hem(th) - z_top(th)) * v
    out = np.stack([np.sin(th) / rx, np.cos(th) / ry, np.zeros_like(th)], axis=-1)
    out = out / np.linalg.norm(out, axis=-1, keepdims=True)
    p = np.stack([rx * np.sin(th), cy + ry * np.cos(th), z], axis=-1)
    if folds:
        f = (0.017 * np.sin(6.0 * th + 0.7) + 0.005 * np.sin(13.0 * th + 2.0)) * v ** 1.1     # round 3: soft deep folds
        f = f * (1.0 - 0.6 * np.exp(-(th / NOTCH_W) ** 2))          # calmer over the arch
        # soft folds gathering toward the clasp near the front edges' tops
        f = f + 0.0035 * np.sin(22.0 * th) * smooth(0.25, 0.0, v) * smooth(1.6, 2.4, np.abs(th))
        p = p + out * f[..., None]
    return p


def chain_points(u: float) -> list[tuple[float, float, float]]:
    """A column of the cape (its spring chain): four points from the collar to the hem at u, no folds."""
    vs = np.array([0.0, 1 / 3, 2 / 3, 1.0])
    p = cape_surface(np.full(4, u), vs, folds=False)
    return [tuple(map(float, q)) for q in p]


def _grid_normals(G: np.ndarray) -> np.ndarray:
    """Normals of a (nv+1, nu+1, 3) grid (pointing away from the body's vertical axis)."""
    du = np.gradient(G, axis=1)
    dv = np.gradient(G, axis=0)
    n = np.cross(du, dv)
    n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
    c = G.copy()
    c[..., 0] = 0.0
    c[..., 1] = 0.03
    sgn = np.sign(((G - c) * n).sum(-1, keepdims=True))
    return n * np.where(sgn == 0, 1.0, sgn)


def cape_object(name: str, high: bool) -> bpy.types.Object:
    nu, nv = (136, 56) if high else (36, 13)
    u = np.linspace(-1.0, 1.0, nu + 1)
    v = np.linspace(0.0, 1.0, nv + 1)
    UU, V = np.meshgrid(u, v)
    G = cape_surface(UU, V)
    if high:
        # the wool's weave (a fine basket weave, about 3 mm) for the normal map
        nrm = _grid_normals(G)
        su = np.cumsum(np.r_[0.0, np.linalg.norm(np.diff(G, axis=1), axis=-1).mean(0)])[None, :]
        sv = np.cumsum(np.r_[0.0, np.linalg.norm(np.diff(G, axis=0), axis=-1).mean(1)])[:, None]
        weave = 0.0009 * np.sin(su * 2 * math.pi / 0.006) * np.sin(sv * 2 * math.pi / 0.006) + 0.0004 * np.sin((su + sv) * 2 * math.pi / 0.017)
        G = G + nrm * weave[..., None]
    N = _grid_normals(G)
    T = (CAPE_T + (HEM_T - CAPE_T) * smooth(0.9, 1.0, V))[..., None] * 0.5
    outer = G + N * T
    inner = G - N * T
    bm = bmesh.new()
    vo = [[bm.verts.new(tuple(outer[j, i])) for i in range(nu + 1)] for j in range(nv + 1)]
    vi = [[bm.verts.new(tuple(inner[j, i])) for i in range(nu + 1)] for j in range(nv + 1)]
    qt, qside = [], []
    for j in range(nv + 1):
        for i in range(nu + 1):
            qt.append(v[j])
            qside.append(u[i])
    qt = qt + qt
    qside = qside + qside
    for j in range(nv):
        for i in range(nu):
            bm.faces.new((vo[j][i], vo[j][i + 1], vo[j + 1][i + 1], vo[j + 1][i]))
            bm.faces.new((vi[j][i + 1], vi[j][i], vi[j + 1][i], vi[j + 1][i + 1]))
    for i in range(nu):
        bm.faces.new((vo[0][i + 1], vo[0][i], vi[0][i], vi[0][i + 1]))
        bm.faces.new((vo[nv][i], vo[nv][i + 1], vi[nv][i + 1], vi[nv][i]))
    for j in range(nv):
        bm.faces.new((vo[j][0], vo[j + 1][0], vi[j + 1][0], vi[j][0]))
        bm.faces.new((vo[j + 1][nu], vo[j][nu], vi[j][nu], vi[j + 1][nu]))
    n = len(qt)
    ob = Q._finish(bm, name, {'part': np.full(n, Q.PART_CAPE), 'qt': qt, 'qroot': np.zeros((n, 3)), 'qrand': np.full(n, 0.5),
                              'qside': qside}, texel_k=0.95)
    ob['prop'] = 'cape'
    Q.orient_out(ob)
    return ob


# ----------------------------------------------------------------------------- the collar and the clasp
CLASP_C = (0.0, -0.1185, 0.443)    # polish: seated on the collar (it stood off like a coin on edge)
CLASP_N = (0.0, -0.96, 0.28)
CLASP_R = 0.025


def collar_ring(phi):
    """The collar's centre line: φ = 0 at the clasp (front), ±π at the back (under the quills); over the shoulder tops
    at the sides, where the cape starts."""
    phi = np.asarray(phi, np.float64)
    return np.stack([0.15 * np.sin(phi), 0.022 - 0.124 * np.cos(phi), 0.47 - 0.024 * np.cos(phi)], axis=-1)


def collar_object(name: str, high: bool) -> bpy.types.Object:
    nphi, nsec = (180, 24) if high else (44, 10)
    phi = np.linspace(-math.pi, math.pi, nphi, endpoint=False)
    c = collar_ring(phi)
    # a soft folded band lying on the shoulders: taller than thick, a little fuller either side of the clasp, pinched
    # under it, with folds gathering toward it
    a = np.abs(phi)
    bunch = np.exp(-((a - 0.7) / 0.5) ** 2)
    pinch = np.exp(-(phi / 0.22) ** 2)
    av = 0.022 + 0.006 * bunch - 0.006 * pinch + 0.004 * np.sin(7.0 * phi) * (0.5 + 0.5 * bunch)
    ar = 0.0095 + 0.004 * bunch - 0.002 * pinch
    wr = 0.006 * np.sin(11.0 * phi + 0.4) * (0.4 + 0.6 * np.exp(-(a / 0.8) ** 2))     # round 3: gathers at the clasp
    up = v3((0.0, 0.0, 1.0))
    tg = norm(np.roll(c, -1, axis=0) - np.roll(c, 1, axis=0))
    radial = norm(np.cross(tg, up))
    flip = ((radial * (c - v3((0.0, 0.022, 0.0)) * np.array([1, 1, 0]))).sum(1) < 0)
    radial[flip] *= -1
    vert = norm(np.cross(radial, tg))
    vert[(vert[:, 2] < 0)] *= -1
    # the band leans out over the shoulders (its lower edge further out than its upper one)
    lean = 0.35 * smooth(0.6, 1.4, a) * smooth(2.6, 1.8, a)
    bm = bmesh.new()
    rings = []
    qt, qside = [], []
    for i in range(nphi):
        ctr = c[i] + radial[i] * (ar[i] * 0.8)
        vax = norm((vert[i] - radial[i] * lean[i])[None])[0]
        ring = []
        for k in range(nsec):
            t = 2 * math.pi * k / nsec
            r_ = ar[i] + (wr[i] if high else 0.5 * wr[i]) * math.cos(3 * t)
            p = ctr + radial[i] * (math.cos(t) * r_) + vax * (math.sin(t) * av[i])
            ring.append(bm.verts.new(tuple(p)))
            qt.append(0.5 + 0.5 * math.sin(t))
            qside.append(phi[i] / math.pi)
        rings.append(ring)
    for i in range(nphi):
        a_, b_ = rings[i], rings[(i + 1) % nphi]
        for k in range(nsec):
            bm.faces.new((a_[k], a_[(k + 1) % nsec], b_[(k + 1) % nsec], b_[k]))
    n = len(qt)
    ob = Q._finish(bm, name, {'part': np.full(n, Q.PART_COLLAR), 'qt': qt, 'qroot': np.zeros((n, 3)), 'qrand': np.full(n, 0.5),
                              'qside': qside}, texel_k=0.85)
    ob['prop'] = 'collar'
    Q.orient_out(ob)
    return ob


def sprig(x: float, y: float) -> float:
    """The clasp's embossed sprig (4-details 5: a stem with three pairs of leaves and a leaf at the top), 0..1 in the
    disc's unit coordinates (x across, y up)."""
    stem = math.exp(-(x / 0.07) ** 2) * (1.0 if -0.62 < y < 0.55 else 0.0)
    out = stem
    for yy in (-0.3, 0.0, 0.28):
        for sx in (1, -1):
            cx, cy = sx * 0.22, yy + 0.12
            ang = math.radians(48.0) * sx
            dx, dy = x - cx, y - cy
            rx_ = dx * math.cos(ang) + dy * math.sin(ang)
            ry_ = -dx * math.sin(ang) + dy * math.cos(ang)
            out = max(out, max(0.0, 1.0 - (rx_ / 0.1) ** 2 - (ry_ / 0.2) ** 2))
    out = max(out, max(0.0, 1.0 - (x / 0.1) ** 2 - ((y - 0.62) / 0.19) ** 2))
    return min(1.0, out)


def clasp_object(name: str, high: bool) -> bpy.types.Object:
    nr, nseg = (32, 72) if high else (4, 22)
    c = v3(CLASP_C)
    n = norm(v3(CLASP_N)[None])[0]
    ex = norm(np.cross(v3((0.0, 0.0, 1.0)), n)[None])[0]
    ey = np.cross(n, ex)
    R = CLASP_R
    bm = bmesh.new()
    rings = []
    radii = np.linspace(0.0, 1.0, nr + 1)[1:]
    centre = bm.verts.new(tuple(c + n * 0.0045))
    qt, qside = [0.0], [0.0]
    for r in radii:
        ring = []
        for k in range(nseg):
            a = 2 * math.pi * k / nseg
            x, y = r * math.cos(a), r * math.sin(a)
            h = 0.0045 - 0.001 * r * r                                        # a gently domed face
            if high:
                h += 0.0014 * smooth(0.8, 0.88, r) * smooth(1.0, 0.93, r)    # the raised rim
                h += 0.0016 * sprig(x / 0.76, y / 0.76) * (r < 0.8)          # the embossed sprig
            p = c + n * h + ex * (x * R * 0.93) + ey * (y * R * 0.93)
            ring.append(bm.verts.new(tuple(p)))
            qt.append(r)
            qside.append(math.cos(a))
        rings.append(ring)
    bev = [bm.verts.new(tuple(c + n * 0.0015 + (ex * math.cos(2 * math.pi * k / nseg) + ey * math.sin(2 * math.pi * k / nseg)) * R))
           for k in range(nseg)]
    back = [bm.verts.new(tuple(c - n * 0.0025 + (ex * math.cos(2 * math.pi * k / nseg) + ey * math.sin(2 * math.pi * k / nseg)) * R * 0.95))
            for k in range(nseg)]
    bc = bm.verts.new(tuple(c - n * 0.0025))
    qt += [1.0] * nseg + [1.0] * nseg + [1.0]
    qside += [0.0] * (2 * nseg + 1)
    for k in range(nseg):
        bm.faces.new((centre, rings[0][k], rings[0][(k + 1) % nseg]))
    for i in range(len(rings) - 1):
        for k in range(nseg):
            bm.faces.new((rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % nseg], rings[i][(k + 1) % nseg]))
    for ra, rb in ((rings[-1], bev), (bev, back)):
        for k in range(nseg):
            bm.faces.new((ra[k], rb[k], rb[(k + 1) % nseg], ra[(k + 1) % nseg]))
    for k in range(nseg):
        bm.faces.new((bc, back[(k + 1) % nseg], back[k]))
    m = len(qt)
    ob = Q._finish(bm, name, {'part': np.full(m, Q.PART_CLASP), 'qt': qt, 'qroot': np.zeros((m, 3)), 'qrand': np.full(m, 0.5),
                              'qside': qside}, texel_k=1.6)
    ob['prop'] = 'clasp'
    Q.orient_out(ob)
    return ob
