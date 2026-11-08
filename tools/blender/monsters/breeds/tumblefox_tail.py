"""Tumblefox Ultra: the tail, one huge fluffy spiral (CONTENT §2.2; chatgpt/monsters/02-tumblefox, the card: exactly one
tail).

Read from 2-turnaround.png (side, front and back views), 1-hero.png and 4-details.png panel 4:
  - the tail is a fat round brush wound into a closed snail shell as big as the whole body, over the rump and the back;
  - from the rump (its base as wide as the rump) it runs back and down, up the back of the spiral, over the top, down
    the front and winds on inward about 1.25 more turns, finishing at the centre of the disc with no gap;
  - the spiral's plane is turned about 35° from the body's side toward the monster's left (+X): it shows from the side,
    from behind and face-on to the three-quarter camera (the hero); seen along its plane it is about 60% as thick as it
    is tall (the brush's section is an ellipse, `K` times thicker out of the plane);
  - cream covers the end: from the back of the spiral on its outer side, from the top on its inner side (the orange
    "tongue" between the cream coils), and all of the inner turns.
Round 2 (review 1): round 1's spiral stopped after one turn and left a see-through hole at the centre with the cream
end drooping below it, and its round section read as a flat paddle from three-quarter back.

The centre line is a spiral in that tilted plane: angle θ (degrees, from the plane's back axis toward up), radius r(θ)
from the spiral's centre `O`, the brush's in-plane radius ρ(θ) and an offset w(θ) out of the plane (the root starts on
the body's midline and swings out to the plane). Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Matrix, Vector

from lib.mesh import Part
from lib.surface import smooth, v3

PHI = math.radians(35.0)
AX = np.array([math.sin(PHI), math.cos(PHI), 0.0])      # in the plane: "back" (and out to the left)
BX = np.array([0.0, 0.0, 1.0])                            # in the plane: up
NX = np.cross(AX, BX)                                     # out of the plane, toward the left-front (the 3/4 camera)
O = np.array([0.15, 0.2, 0.555])                          # the spiral's centre: the cream tip winds into it
K = 1.5                                                   # the brush's section: K × thicker out of the plane

# (θ°, r, ρ, w): the root on the rump, back and down, up the back, over the top, down the front, and on inward to the
# centre (the inner turns touch the outer ones: no gap)
CTRL = np.array([
    (250.0, 0.214, 0.084, -0.138),
    (280.0, 0.266, 0.108, -0.092),
    (312.0, 0.278, 0.124, -0.04),
    (348.0, 0.252, 0.13, -0.006),
    (395.0, 0.208, 0.127, 0.0),
    (448.0, 0.164, 0.12, 0.004),
    (500.0, 0.145, 0.11, 0.004),
    (545.0, 0.13, 0.1, 0.004),
    (590.0, 0.11, 0.092, 0.004),
    (635.0, 0.09, 0.083, 0.004),
    (680.0, 0.068, 0.072, 0.004),
    (725.0, 0.046, 0.062, 0.004),
    (770.0, 0.026, 0.052, 0.004),
    (810.0, 0.008, 0.044, 0.004),
])
N_SAMPLES = 1100
CORE = (0.11, 0.19)                                       # the shell's solid centre: in-plane radius, out-of-plane radius
# review 2: the inner turns were thinner than the outer coil, so the centre was a shadowed pocket of grey cards; from the
# top of the spiral on, every turn is at least this thick out of the plane: the disc's faces are flush
FLUSH = (460.0, 520.0, 0.19)


def _catmull(xs: np.ndarray, ys: np.ndarray, x: np.ndarray) -> np.ndarray:
    """A Catmull-Rom spline through (xs, ys) at x (xs increasing; the ends are clamped)."""
    i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
    x0, x1 = xs[i], xs[i + 1]
    t = (x - x0) / (x1 - x0)
    y0 = ys[np.maximum(i - 1, 0)]
    y1, y2 = ys[i], ys[i + 1]
    y3 = ys[np.minimum(i + 2, len(xs) - 1)]
    h = x1 - x0
    hm = xs[i] - xs[np.maximum(i - 1, 0)]
    hp = xs[np.minimum(i + 2, len(xs) - 1)] - xs[i + 1]
    m1 = (y2 - y0) / np.maximum(h + hm, 1e-9) * h
    m2 = (y3 - y1) / np.maximum(h + hp, 1e-9) * h
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y1 + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * y2 + (t3 - t2) * m2


def _build():
    th = np.linspace(CTRL[0, 0], CTRL[-1, 0], N_SAMPLES)
    r = _catmull(CTRL[:, 0], CTRL[:, 1], th)
    rho = _catmull(CTRL[:, 0], CTRL[:, 2], th)
    w = _catmull(CTRL[:, 0], CTRL[:, 3], th)
    a = np.radians(th)
    radial = np.cos(a)[:, None] * AX[None] + np.sin(a)[:, None] * BX[None]
    P = O[None] + r[:, None] * radial + w[:, None] * NX[None]
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    L = np.concatenate([[0.0], np.cumsum(seg)])
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    zmin = smooth(FLUSH[0], FLUSH[1], th) * FLUSH[2]
    return {'theta': th, 'r': r, 'rho': rho, 'w': w, 'zmin': zmin, 'P': P, 'T': T, 'radial': radial, 's': L / L[-1], 'length': float(L[-1])}


PATH = _build()
LENGTH = PATH['length']
BASE = PATH['P'][0]
TIP = PATH['P'][-1]


def _squash(p: np.ndarray) -> np.ndarray:
    """Points in the space where the brush's elliptical section is round (the out-of-plane axis divided by K)."""
    return p - (1.0 - 1.0 / K) * (p @ NX)[:, None] * NX[None]


def at(s) -> dict:
    """The centre line at arc position s (0 root … 1 tip): point, tangent, tube radius, radial (outward from O)."""
    s = np.atleast_1d(np.asarray(s, float))
    out = {}
    for k in ('P', 'T', 'radial'):
        out[k] = np.stack([np.interp(s, PATH['s'], PATH[k][:, i]) for i in range(3)], axis=1)
    out['rho'] = np.interp(s, PATH['s'], PATH['rho'])
    out['theta'] = np.interp(s, PATH['s'], PATH['theta'])
    out['zmin'] = np.interp(s, PATH['s'], PATH['zmin'])
    return out


def points(n: int) -> list[tuple[float, float, float]]:
    """n points at equal arc length from the root to the tip (the rig's `tail_points`)."""
    P = at(np.linspace(0.0, 1.0, n))['P']
    return [tuple(map(float, p)) for p in P]


def _euler(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """XYZ Euler degrees turning the primitive's local X onto `x` and Y onto `y` (Z = X × Y)."""
    y = y / np.linalg.norm(y)
    x = x - y * (x @ y)
    x = x / np.linalg.norm(x)
    z = np.cross(x, y)
    e = Matrix((Vector(x), Vector(y), Vector(z))).transposed().to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def parts() -> list[Part]:
    """The tail's volume: overlapping ellipsoids along the centre line (radius ρ in the plane, K·ρ out of it) and the
    shell's solid core, voxel-united into the body as extras."""
    out = []
    s, k = 0.0, 0
    while s <= 1.0:
        c = at(s)
        rho, T = float(c['rho'][0]), c['T'][0]
        across = np.cross(T, NX)                      # in the plane, square to the centre line
        # the out-of-plane radius eases in from the root (it leaves the rump round)
        kk = 1.0 + (K - 1.0) * float(smooth(0.0, 0.12, s))
        zr = max(rho * kk, float(c['zmin'][0]))
        out.append(Part(f'tail{k:03d}', 'sphere', loc=tuple(c['P'][0]), radius=1.0, scale=(rho, rho * 0.95, zr),
                        rot=_euler(across, T)))
        s += max(0.006, 0.15 * rho) / LENGTH
        k += 1
    out.append(Part('tailcore', 'sphere', loc=tuple(O + NX * 0.004), radius=1.0, scale=(CORE[0], CORE[0], CORE[1]),
                    rot=_euler(AX, BX)))
    return out


def lookup(p: np.ndarray, margin: float = 0.1) -> dict:
    """Per point: s (arc position of the nearest centre-line sample, measured in the space where the brush's section is
    round), theta (the spiral angle there), d (that distance from the centre line), rho (the brush's in-plane radius),
    out (cosine of the point's in-plane direction from the centre line with the radial direction away from the spiral's
    centre: +1 on the outer side of the coil, −1 on the inner side) and T (the tail's direction there). Points outside
    the tail's box get d = 9."""
    k = len(p)
    res = {'s': np.zeros(k), 'theta': np.zeros(k), 'd': np.full(k, 9.0), 'rho': np.full(k, 0.05), 'zmin': np.zeros(k), 'out': np.zeros(k),
           'T': np.tile(v3((0, 1, 0)), (k, 1))}
    P = PATH['P']
    ext = PATH['rho'].max() * K + margin
    lo, hi = P.min(0) - ext, P.max(0) + ext
    idx = np.nonzero(np.all((p >= lo) & (p <= hi), axis=1))[0]
    Ps = _squash(P)
    P32 = Ps.astype(np.float32)
    PP = (P32 * P32).sum(1)
    for a in range(0, len(idx), 16384):
        ii = idx[a:a + 16384]
        qs = _squash(p[ii])
        q = qs.astype(np.float32)
        j = np.argmin((q * q).sum(1)[:, None] - 2.0 * (q @ P32.T) + PP[None], axis=1)
        dv = qs - Ps[j]
        d = np.linalg.norm(dv, axis=1)
        inplane = dv - (dv @ NX)[:, None] * NX[None]
        u = inplane / np.maximum(np.linalg.norm(inplane, axis=1), 1e-9)[:, None]
        res['s'][ii] = PATH['s'][j]
        res['theta'][ii] = PATH['theta'][j]
        res['d'][ii] = d
        res['rho'][ii] = PATH['rho'][j]
        res['zmin'][ii] = PATH['zmin'][j]
        res['out'][ii] = (u * PATH['radial'][j]).sum(1)
        res['T'][ii] = PATH['T'][j]
    return res


def reach(L: dict) -> np.ndarray:
    """How far from the centre line counts as tail: tight at the root (where the brush sinks into the rump and the
    haunches), the brush and its fur further out."""
    k = smooth(0.05, 0.2, L['s'])
    rho = np.maximum(L['rho'], L['zmin'] / K)
    return rho * (1.0 + 0.3 * k) + 0.008 + 0.022 * k


def zone(p: np.ndarray, L: dict | None = None) -> tuple[np.ndarray, dict]:
    """(on the tail, the lookup): the brush and its fur, past the first few centimetres of the root."""
    if L is None:
        L = lookup(p)
    on = (L['d'] < reach(L)) & (L['s'] > 0.03)
    return on, L


CREAM_THETA = (378.0, 705.0)        # cream on the coil's outer half from here … all of it (the tip's hook) from here


def cream(L: dict) -> np.ndarray:
    """0 orange … 1 cream on the tail: the base sweep orange; from the back of the spiral on, the outer half of each
    coil cream and its inner half orange, so the orange tongue winds in between the cream coils to the centre
    (2-turnaround.png side, 4-details.png panel 4); the last ~100° (the hook at the centre) all cream. Round 2: with
    every inner turn cream, the spiral read as a plain cream disc."""
    outer = smooth(-0.18, 0.18, L['out']) * smooth(CREAM_THETA[0] - 12.0, CREAM_THETA[0] + 12.0, L['theta'])
    hook = smooth(CREAM_THETA[1] - 15.0, CREAM_THETA[1] + 15.0, L['theta'])
    return np.maximum(outer, hook)
