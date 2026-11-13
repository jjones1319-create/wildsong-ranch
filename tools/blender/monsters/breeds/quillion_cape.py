"""Quillion's cape (props; quillion_ultra.build_props): a short crimson wool cape fastened at the neck with a small round
clasp (1-hero, 2-turnaround, 4-details 5).

- The cape: one thick cloth shell (about 7 mm, a rolled hem a little thicker) hanging from the shoulders round the back
  and flaring like a bell to a hem about 15% of the height above the ground (2-turnaround side and front: 0.15 m at the
  sides). Its top lies under the quill mantle (the quills lie over it, as in every picture), so it shows from the
  shoulders and from under the quills down. Soft vertical folds grow toward the hem. At the back the hem rises in a
  rounded arch over the tail's root, so the tail leaves the body freely (the tail's ruff and the blade cover it from
  behind). Three spring chains (capeR, capeC, capeL: plans/biped.py `capes`) carry it; quillion_ultra blends their
  weights across the cloth by `qside`.
- The collar: the cape's top folded into a soft roll round the neck, bunched either side of the clasp (the bow of
  the front view), rigid on the chest.
- The clasp: a small round disc with a raised rim and an embossed sprig (4-details 5), rigid on the chest.

Each part carries the props' common attributes (quillion_quills.ATTRS): part, qt (the cloth's v: 0 at the top, 1 at the
hem), qroot, qrand, qside (the cloth's u: −1 at its right front edge, +1 at its left).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import norm, smooth, v3
from monsters.breeds import quillion_quills as Q

THETA = math.radians(82.0)          # the cape wraps from the back round to just behind each arm
NOTCH_H, NOTCH_W = 0.19, 0.42       # the arch over the tail: its height (m) and half-width (radians)
NOTCH_C = 0.3                       # its middle: toward the left, where the tail leaves the rump
CAPE_T = 0.0068                     # the cloth's thickness
HEM_T = 0.0105                      # the rolled hem


def z_top(th):
    return 0.452 + 0.024 * np.cos(th)


def z_hem(th):
    return 0.135 + 0.008 * (1.0 - np.cos(th)) + NOTCH_H * np.exp(-((np.asarray(th) - NOTCH_C) / NOTCH_W) ** 2)


def _radii(v):
    v = np.asarray(v, np.float64)
    k = v ** 0.85
    return 0.124 + 0.15 * k, 0.105 + 0.13 * k, 0.03 + 0.02 * v


def cape_surface(th, v, folds: bool = True):
    """The cloth's middle surface at (θ, v): θ from −THETA (its right front edge) through 0 (the back) to +THETA."""
    th = np.asarray(th, np.float64)
    v = np.asarray(v, np.float64)
    rx, ry, cy = _radii(v)
    z = z_top(th) + (z_hem(th) - z_top(th)) * v
    out = np.stack([np.sin(th) / rx, np.cos(th) / ry, np.zeros_like(th)], axis=-1)
    out = out / np.linalg.norm(out, axis=-1, keepdims=True)
    p = np.stack([rx * np.sin(th), cy + ry * np.cos(th), z], axis=-1)
    if folds:
        f = (0.011 * np.sin(7.5 * th + 0.7) + 0.004 * np.sin(13.0 * th + 2.0)) * v ** 1.4
        f = f * (1.0 - 0.6 * np.exp(-((th - NOTCH_C) / NOTCH_W) ** 2))          # calmer over the arch
        p = p + out * f[..., None]
    return p


def chain_points(th: float) -> list[tuple[float, float, float]]:
    """A column of the cape (its spring chain): four points from the top to the hem at angle θ, no folds."""
    vs = np.array([0.0, 1 / 3, 2 / 3, 1.0])
    p = cape_surface(np.full(4, th), vs, folds=False)
    return [tuple(map(float, q)) for q in p]


def _grid_normals(G: np.ndarray) -> np.ndarray:
    """Normals of a (nv+1, nu+1, 3) grid of points by central differences (pointing outward: away from the body)."""
    du = np.gradient(G, axis=1)
    dv = np.gradient(G, axis=0)
    n = np.cross(du, dv)
    n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
    # outward = away from the cape's own axis
    c = G.copy()
    c[..., 0] = 0.0
    c[..., 1] = 0.04
    c[..., 2] = G[..., 2]
    sgn = np.sign(((G - c) * n).sum(-1, keepdims=True))
    return n * np.where(sgn == 0, 1.0, sgn)


def cape_object(name: str, high: bool) -> bpy.types.Object:
    nu, nv = (128, 52) if high else (34, 12)
    u = np.linspace(-1.0, 1.0, nu + 1)
    v = np.linspace(0.0, 1.0, nv + 1)
    TH, V = np.meshgrid(u * THETA, v)
    G = cape_surface(TH, V)
    if high:
        # the wool's soft nap: a faint lumpy weave (bakes into the normal map), and the stitched hem's groove
        UU, _ = np.meshgrid(u, v)
        nrm = _grid_normals(G)
        weave = 0.00045 * np.sin(UU * 900.0) * np.sin(V * 380.0) + 0.0003 * np.sin(UU * 410.0 + V * 170.0)
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
    # the edges: top, hem and the two front edges join the two sides of the cloth
    for i in range(nu):
        bm.faces.new((vo[0][i + 1], vo[0][i], vi[0][i], vi[0][i + 1]))
        bm.faces.new((vo[nv][i], vo[nv][i + 1], vi[nv][i + 1], vi[nv][i]))
    for j in range(nv):
        bm.faces.new((vo[j][0], vo[j + 1][0], vi[j + 1][0], vi[j][0]))
        bm.faces.new((vo[j + 1][nu], vo[j][nu], vi[j][nu], vi[j + 1][nu]))
    n = len(qt)
    ob = Q._finish(bm, name, {'part': np.full(n, Q.PART_CAPE), 'qt': qt, 'qroot': np.zeros((n, 3)), 'qrand': np.full(n, 0.5),
                              'qside': qside})
    ob['prop'] = 'cape'
    Q.orient_out(ob)
    return ob


# ----------------------------------------------------------------------------- the collar and the clasp
CLASP_C = (0.0, -0.126, 0.441)
CLASP_N = (0.0, -0.96, 0.28)
CLASP_R = 0.02


def collar_ring(phi):
    """The collar's centre line round the neck: φ = 0 at the clasp (front), ±π at the back (under the quills)."""
    phi = np.asarray(phi, np.float64)
    return np.stack([0.123 * np.sin(phi), -0.004 - 0.104 * np.cos(phi), 0.468 - 0.027 * np.cos(phi)], axis=-1)


def collar_object(name: str, high: bool) -> bpy.types.Object:
    nphi, nsec = (160, 24) if high else (40, 10)
    phi = np.linspace(-math.pi, math.pi, nphi, endpoint=False)
    c = collar_ring(phi)
    # bunched either side of the clasp (the front view's bow), pinched at the clasp, thinner round the back
    a = np.abs(phi)
    bunch = np.exp(-((a - 0.78) / 0.42) ** 2)
    pinch = np.exp(-(phi / 0.2) ** 2)
    av = 0.027 + 0.008 * bunch - 0.008 * pinch
    ar = 0.011 + 0.005 * bunch - 0.002 * pinch
    wr = 0.0028 * np.sin(9.0 * phi + 0.4) * (0.4 + bunch)
    up = v3((0.0, 0.0, 1.0))
    tg = np.roll(c, -1, axis=0) - np.roll(c, 1, axis=0)
    tg = norm(tg)
    radial = norm(np.cross(tg, up))
    # radial must point out of the neck
    flip = ((radial * (c - v3((0.0, -0.004, 0.0)) * np.array([1, 1, 0]))).sum(1) < 0)
    radial[flip] *= -1
    vert = norm(np.cross(radial, tg))
    vert[(vert[:, 2] < 0)] *= -1
    bm = bmesh.new()
    rings = []
    qt, qside = [], []
    for i in range(nphi):
        ctr = c[i] + radial[i] * (ar[i] * 0.7)
        ring = []
        for k in range(nsec):
            t = 2 * math.pi * k / nsec
            r_ = ar[i] + wr[i] * (1 if high else 0) * math.cos(3 * t)
            p = ctr + radial[i] * (math.cos(t) * r_) + vert[i] * (math.sin(t) * av[i])
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
                              'qside': qside})
    ob['prop'] = 'collar'
    Q.orient_out(ob)
    return ob


def sprig(x: float, y: float) -> float:
    """The clasp's embossed sprig (4-details 5: a stem with three pairs of leaves and a leaf at the top), 0..1 in the
    disc's unit coordinates (x across, y up)."""
    stem = math.exp(-(x / 0.07) ** 2) * (1.0 if -0.62 < y < 0.55 else 0.0)
    out = stem
    for k, yy in enumerate((-0.3, 0.0, 0.28)):
        for sx in (1, -1):
            # a leaf: an ellipse leaning up and out from the stem
            cx, cy = sx * 0.22, yy + 0.12
            ang = math.radians(48.0) * sx
            dx, dy = x - cx, y - cy
            rx_ = dx * math.cos(ang) + dy * math.sin(ang)
            ry_ = -dx * math.sin(ang) + dy * math.cos(ang)
            out = max(out, max(0.0, 1.0 - (rx_ / 0.1) ** 2 - (ry_ / 0.2) ** 2))
    out = max(out, max(0.0, 1.0 - (x / 0.1) ** 2 - ((y - 0.62) / 0.19) ** 2))
    return min(1.0, out)


def clasp_object(name: str, high: bool) -> bpy.types.Object:
    nr, nseg = (28, 64) if high else (4, 20)
    c = v3(CLASP_C)
    n = norm(v3(CLASP_N)[None])[0]
    ex = norm(np.cross(v3((0.0, 0.0, 1.0)), n)[None])[0]
    ey = np.cross(n, ex)
    R = CLASP_R
    bm = bmesh.new()
    # the front face (with the rim and the sprig on the high source), the bevel, the back face
    rings = []
    radii = np.linspace(0.0, 1.0, nr + 1)[1:]
    centre = bm.verts.new(tuple(c + n * 0.0042))
    qt, qside = [0.0], [0.0]
    for r in radii:
        ring = []
        for k in range(nseg):
            a = 2 * math.pi * k / nseg
            x, y = r * math.cos(a), r * math.sin(a)
            h = 0.0042
            if high:
                h += 0.0009 * smooth(0.8, 0.88, r) * smooth(1.0, 0.93, r)        # the raised rim
                h += 0.0008 * sprig(x / 0.78, y / 0.78) * (r < 0.8)
            p = c + n * h + ex * (x * R * 0.93) + ey * (y * R * 0.93)
            ring.append(bm.verts.new(tuple(p)))
            qt.append(r)
            qside.append(math.cos(a))
        rings.append(ring)
    bev = [bm.verts.new(tuple(c + n * 0.0015 + (ex * math.cos(2 * math.pi * k / nseg) + ey * math.sin(2 * math.pi * k / nseg)) * R))
           for k in range(nseg)]
    back = [bm.verts.new(tuple(c - n * 0.004 + (ex * math.cos(2 * math.pi * k / nseg) + ey * math.sin(2 * math.pi * k / nseg)) * R * 0.95))
            for k in range(nseg)]
    bc = bm.verts.new(tuple(c - n * 0.004))
    qt += [1.0] * nseg + [1.0] * nseg + [0.0]
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
                              'qside': qside})
    ob['prop'] = 'clasp'
    Q.orient_out(ob)
    return ob
