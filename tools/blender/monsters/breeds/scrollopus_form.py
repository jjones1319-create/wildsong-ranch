"""Scrollopus's form (Art 2.1 Ultra; chatgpt/monsters/22-scrollopus): the layout every other Scrollopus module reads.

  - the head-body (the mantle): a big round egg with the face on its lower front (cheeks, a small muzzle), sitting on a
    soft core where the eight tentacles join;
  - the eight tentacles as centrelines: dense samples with their arc length, tube radius and the sucker side ('under'),
    and the four bone joints the rig uses. Five lie low on the ground with big spiral curls at their tips (the suckers
    on the curls' outsides): front-left, right, back-right, back and the ink arm on its left-back. Three hold things:
    the scroll (front-right, low), the quill (its right, raised) and the book (its left), each tip wrapped round its
    prop (1-hero, 2-turnaround).

Metres; the monster faces −Y, Z is up, +X is its left. Angles round the body: 0 = straight ahead, + toward its left.
"""
from __future__ import annotations

import math

import numpy as np

from lib.mesh import Part
from monsters.breeds import scrollopus_noise as N

smooth = N.smooth
v3 = N.v3
Z = np.array([0.0, 0.0, 1.0])

# ----------------------------------------------------------------------------- the head-body (2-turnaround: 1.10 m
# with the cap; round 3: the crown at 0.98 m, the eye line at 0.6 m, the head about 0.56 m wide)
# round 2 (review: a ball on a pinched neck): one pear, fuller low down, flaring straight into the thick roots; no
# muzzle and no cheek pads (a flat, smooth face)
# round 3 (review: a capsule on stilts): a rounder ball set lower, flowing straight into a pile of thick arms; the
# core under it fills the base (no daylight between the roots, no cleft under the chin)
MANTLE = ((0.0, 0.01, 0.668), (0.282, 0.274, 0.308))
CROWN = ((0.0, 0.03, 0.72), (0.23, 0.23, 0.23))             # round 3: inside the ball (its edge showed as a ledge)
CORE = ((0.0, 0.01, 0.24), (0.27, 0.25, 0.18))              # under the arms' roots, filling the base (clear of the scroll)
HEAD_TOP = MANTLE[0][2] + MANTLE[1][2]

# the face (3-faces neutral): big eyes behind round spectacles, a small sly smile low between the cheeks
EYE_C = {s: np.array([0.097 * s, -0.246, 0.6]) for s in (1, -1)}
EYE_R = 0.058                                                 # round 2: a little larger, filling more of each lens
EYE_SHAPE = (1.0, 1.06)
EYE_DEPTH = (0.42, 0.28)
EYE_LOOK = {s: (0.28 * s, -1.0, 0.06) for s in (1, -1)}
MOUTH_C = (0.0, -0.232, 0.5)
HEAD_C = (0.0, -0.19, 0.585)
HEAD_R = 0.21


def ell_sdf(co: np.ndarray, spec, mirror: int = 0) -> np.ndarray:
    c, r = spec
    c = v3(c).copy()
    if mirror:
        c[0] *= mirror
    return N.ell_sdf(co, c, r)


def mantle_sdf(co: np.ndarray) -> np.ndarray:
    """About metres outside (> 0) the head-body's ellipsoids (the core excluded)."""
    return np.minimum(ell_sdf(co, MANTLE), ell_sdf(co, CROWN))


def head_surface(p, out: float = 0.0) -> np.ndarray:
    """The point on the mantle's main ellipsoid along the ray from its centre through p, pushed `out` metres."""
    c, r = v3(MANTLE[0]), v3(MANTLE[1])
    q = (v3(p) - c) / r
    q = q / max(float(np.linalg.norm(q)), 1e-9)
    s = c + q * r
    n = q / r
    n = n / np.linalg.norm(n)
    return s + n * out


# ----------------------------------------------------------------------------- tentacles
def dirv(theta_deg: float) -> np.ndarray:
    a = math.radians(theta_deg)
    return np.array([math.sin(a), -math.cos(a), 0.0])


def _bezier(p0, p1, p2, p3, n: int) -> np.ndarray:
    t = np.linspace(0.0, 1.0, n)[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def _catmull(ctrl: np.ndarray, per: int = 12) -> np.ndarray:
    """A centripetal Catmull-Rom curve through the control points (ends extended)."""
    P = np.asarray(ctrl, np.float64)
    P = np.concatenate([[2 * P[0] - P[1]], P, [2 * P[-1] - P[-2]]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** 0.5
        for t in np.linspace(t1, t2, per, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(P[-2])
    return np.array(out)


def resample(pts: np.ndarray, step: float = 0.004) -> np.ndarray:
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(math.ceil(s[-1] / step)) + 1)
    si = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(si, s, pts[:, k]) for k in range(3)], axis=1)


def arclen(pts: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])


def tangents(pts: np.ndarray) -> np.ndarray:
    t = np.gradient(pts, axis=0)
    return t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)


def _unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def perp_unit(g: np.ndarray, t: np.ndarray) -> np.ndarray:
    g = g - t * (g * t).sum(axis=1, keepdims=True)
    return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)


# the five low tentacles: angle round the body, where it touches down, the run along the ground, the curl's size and
# turns, a sideways drift of the curl (so its turns never fuse), the root's height
ROOT_R, ROOT_Z = 0.14, 0.38     # round 3: the roots leave the ball's underside, flaring out at once
GROUND = [
    # round 3: each lies along the ground in an S (`wig` sideways), its curl leaning (`lean` degrees) to show its suckers
    {'name': 'tentFL', 'theta': 26.0, 'touch': 0.33, 'run': 0.12, 'wig': 0.05, 'curl': 0.104, 'turns': 0.84, 'drift': -0.03, 'lean': -24.0, 'root_z': ROOT_Z},
    {'name': 'tentR', 'theta': -60.0, 'touch': 0.34, 'run': 0.11, 'wig': -0.05, 'curl': 0.102, 'turns': 0.84, 'drift': 0.03, 'lean': 22.0, 'root_z': ROOT_Z},
    {'name': 'tentBR', 'theta': -136.0, 'touch': 0.33, 'run': 0.12, 'wig': 0.05, 'curl': 0.102, 'turns': 0.86, 'drift': 0.028, 'lean': 20.0, 'root_z': ROOT_Z},
    {'name': 'tentB', 'theta': 172.0, 'touch': 0.325, 'run': 0.11, 'wig': -0.05, 'curl': 0.1, 'turns': 0.84, 'drift': -0.028, 'lean': -20.0, 'root_z': ROOT_Z},
    {'name': 'inkarm', 'theta': 114.0, 'touch': 0.335, 'run': 0.11, 'wig': 0.045, 'curl': 0.102, 'turns': 0.84, 'drift': -0.03, 'lean': -22.0, 'root_z': ROOT_Z},
]
R_ROOT, R_TIP = 0.108, 0.018                     # round 3: thick all the way to the curls


def radius_profile(u: np.ndarray, r_root: float = R_ROOT, r_tip: float = R_TIP, k: float = 0.56) -> np.ndarray:
    """The tube's radius by arc fraction (0 root … 1 tip): thick at the root, tapering, a rounded tip."""
    r = r_tip + (r_root - r_tip) * (1.0 - u) ** k
    return r * (1.0 - 0.45 * smooth(0.975, 1.0, u))


def ground_tentacle(g: dict) -> dict:
    d = dirv(g['theta'])
    lat = np.cross(Z, d)                       # toward the tentacle's own left
    r0, z0 = ROOT_R, g['root_z']
    zg = float(radius_profile(np.array([0.42]))[0]) + 0.002
    # round 3: the root flares outward at once from the flank and settles onto the ground (a pile, not stilts)
    A = _bezier(np.array([r0, z0]), np.array([r0 + 0.12, z0 - 0.05]), np.array([g['touch'] - 0.1, zg + 0.004]),
                np.array([g['touch'], zg]), 40)
    B = np.stack([np.linspace(g['touch'], g['touch'] + g['run'], 18), np.full(18, zg)], axis=1)[1:]
    R0 = g['curl']
    rc, zc = g['touch'] + g['run'], zg + R0
    ph = np.linspace(-0.5 * math.pi, -0.5 * math.pi + 2 * math.pi * g['turns'], 60)[1:]
    v = (ph + 0.5 * math.pi) / (2 * math.pi * g['turns'])
    Rr = R0 * (1.0 - 0.68 * v)
    Cc = np.stack([rc + Rr * np.cos(ph), zc + Rr * np.sin(ph)], axis=1)
    rz = np.concatenate([A, B, Cc])
    # the ground run snakes sideways in one S hump; the curl drifts on and leans to its side (its suckers face out)
    tb = np.linspace(0.0, 1.0, len(B) + 1)[1:]
    w = np.concatenate([np.zeros(len(A)), g['wig'] * np.sin(np.pi * tb) * (1.0 - 0.35 * tb), g['drift'] * v ** 1.5])
    ln = math.radians(g['lean'])
    Zt = Z * math.cos(ln) + lat * math.sin(ln)
    lean_w = np.concatenate([np.zeros(len(A) + len(B)), smooth(0.0, 0.25, v)])
    zz = rz[:, 1:2]
    up_dir = Z[None] * (1 - lean_w[:, None]) + Zt[None] * lean_w[:, None]
    raw = rz[:, :1] * d[None] + zg * Z[None] + (zz - zg) * up_dir + w[:, None] * lat[None]
    sr = arclen(raw)
    s_td, s_cs = float(sr[len(A) - 1]), float(sr[len(A) + len(B) - 1])
    k0 = len(A) + len(B) + int(np.argmin(np.abs(ph)))
    p_out = raw[k0]                            # the curl's outermost point: the last bone's tail
    pts = resample(raw)
    s = arclen(pts)
    L = s[-1]
    T = tangents(pts)
    # the sucker side: the in-plane normal turned from the tangent (down on the ground run, outward round the curl)
    s_pts = arclen(pts)
    s_r = arclen(raw)
    lw = np.interp(s_pts, s_r, lean_w)
    Zp = Z[None] * (1 - lw[:, None]) + Zt[None] * lw[:, None]
    U0 = np.cross(T, np.cross(d[None], Zp))
    # round 2: on the root's bulge and descent the sucker side turns outward and down (it shows from outside, as in
    # the pictures), easing back to straight down by the ground run
    s_raw = arclen(raw)
    k_out = np.interp(arclen(pts), [0.0, 0.6 * s_raw[len(A) - 1], s_raw[len(A) - 1] + 0.02], [0.9, 0.9, 0.0])
    U = perp_unit(U0 + k_out[:, None] * (d[None] - 0.2 * Z[None]), T)
    joints = [0.0, 0.5 * s_td, s_td, s_cs]
    return finish({'name': g['name'], 'role': 'ground', 'theta': g['theta'], 'pts': pts, 's': s, 'T': T, 'U': U,
                   'rad': radius_profile(s / L), 'joints': joints, 'tail': p_out, 'rigid_from': s_cs + 0.03, 'grip': None,
                   'curl_c': rc * d + zc * Z, 'lat': lat, 'd': d})


def perp_dir(v, axis) -> np.ndarray:
    a = _unit(axis)
    return _unit(v3(v) - a * float(v3(v) @ a))


def helix(centre, axis, start_dir, to_dir, rho: float, turns: float, rise: float, n: int, shrink: float = 0.0) -> np.ndarray:
    """A helix round `axis` through `centre` (its middle): it starts at `start_dir` from the axis and winds toward
    `to_dir` for `turns` turns, moving `rise` metres along the axis in all; its radius shrinks by `shrink` (share)."""
    a = _unit(axis)
    e1 = perp_dir(start_dir, a)
    e2 = np.cross(a, e1)
    sense = 1.0 if float(perp_dir(to_dir, a) @ e2) >= 0 else -1.0
    tau = np.linspace(0.0, 1.0, n)
    ang = sense * 2 * math.pi * turns * tau
    rr = rho * (1.0 - shrink * tau)
    return (v3(centre)[None] + a[None] * (rise * (tau - 0.5))[:, None]
            + rr[:, None] * (np.cos(ang)[:, None] * e1[None] + np.sin(ang)[:, None] * e2[None]))


# ----------------------------------------------------------------------------- the held things (1-hero, 2-turnaround)
# the scroll: low in front of its right side, angled down toward its left
SCROLL = {'c': v3((-0.17, -0.41, 0.345)), 'axis': _unit((1.0, -0.2, -0.3)), 'len': 0.36, 'r': 0.056}
# the quill: upright on its right, leaning out at the top; the gold holder is where the tentacle grips it
QUILL = {'nib': v3((-0.37, -0.2, 0.36)), 'axis': _unit((-0.11, 0.035, 1.0)), 'holder': (0.045, 0.2), 'r': 0.016,
         'vane': (0.23, 0.62), 'grip': 0.12}
# the book: upright on its left, its front cover toward the front-left, opened a little at the fore-edge
# polish (review: the open spread face-on read as a fan of cards): its cover turned to 35 degrees off the front, so the cover and
# the spine show beside the pages, as in the hero; a little further out (its fore-edge now toward the face)
BOOK = {'c': v3((0.39, -0.15, 0.47)), 'face': _unit((0.574, -0.819, 0.0)), 'h': 0.236, 'w': 0.166, 't': 0.058, 'open': 60.0, 'tilt': 14.0}


def quill_point(k: float) -> np.ndarray:
    """A point up the quill's axis, k metres from the nib's tip."""
    return QUILL['nib'] + QUILL['axis'] * k


def book_frame():
    """(centre, face (out of the front cover), across (spine → fore-edge, seen from the front), up)."""
    f0 = BOOK['face']
    across = -np.cross(Z, f0)            # the fore-edge toward the body's middle, the spine outward
    # tipped back a little (the top away from the front), so the pages fanning at the top show from the front
    a = math.radians(BOOK['tilt'])
    up = Z * math.cos(a) - f0 * math.sin(a)
    f = np.cross(across, up)
    f = f if f @ f0 > 0 else -f
    return BOOK['c'], f, across, up


def hold_tentacle(name: str, theta: float, approach: list, wrap: np.ndarray, under_fn, grip, axis, tip: list | None = None,
                  r_root: float = 0.084) -> dict:
    """A holding tentacle: from its root through the approach points, then wrapped round its prop (`wrap`, a dense
    curve), then the tip's points; `under_fn(p)` gives the sucker side's target (the prop it grips)."""
    d = dirv(theta)
    root = d * ROOT_R + Z * ROOT_Z
    ctrl = [root] + [v3(p) for p in approach]
    k_wrap = len(ctrl)
    wrap = np.asarray(wrap)
    ctrl += list(wrap[:: max(1, len(wrap) // 14)]) + ([wrap[-1]] if len(wrap) % 14 else [])
    ctrl += [v3(p) for p in (tip or [])]
    ctrl = np.array(ctrl)
    raw = _catmull(ctrl, 10)
    sr = arclen(raw)
    s_wrap = float(sr[min(len(sr) - 1, 10 * (k_wrap - 1))])
    pts = resample(raw)
    s = arclen(pts)
    L = s[-1]
    T = tangents(pts)
    body_side = -0.8 * Z[None] + 0.5 * d[None] + 0.0 * pts          # round 2: outward and down (seen from outside)
    toward = np.array([under_fn(p) for p in pts])
    w = smooth(s_wrap - 0.12, s_wrap, s)[:, None]
    U = perp_unit((1 - w) * body_side + w * toward, T)
    # polish: the last joint at least 3 cm past the third (the book's short reach made a 4 mm bone 3, and bone 4 took
    # the arm's middle, fused with the front-left arm)
    joints = [0.0, 0.3 * s_wrap, 0.62 * s_wrap, max(s_wrap - 0.06, 0.62 * s_wrap + 0.03)]
    rad = radius_profile(s / L, r_root=r_root, r_tip=0.016, k=0.75)
    return finish({'name': name, 'role': 'hold', 'theta': theta, 'pts': pts, 's': s, 'T': T, 'U': U, 'rad': rad,
                   'joints': joints, 'tail': v3(grip), 'rigid_from': s_wrap, 'grip': (v3(grip), _unit(axis)), 'd': d})


def _toward_axis(c, a):
    c, a = v3(c), _unit(a)

    def f(p):
        q = v3(p) - c
        return -(q - a * float(q @ a))
    return f


def scroll_tentacle() -> dict:
    c, a = SCROLL['c'], SCROLL['axis']
    gc = c + a * 0.035
    down = perp_dir(-Z, a)
    front = perp_dir((0, -1, 0), a)
    back = -front
    wrap = helix(gc, a, 0.55 * down + 0.45 * back, front, SCROLL['r'] + 0.04, 0.92, 0.09, 60, shrink=0.12)
    approach = [(-0.1, -0.27, 0.35), gc + 0.11 * (0.7 * down + 0.7 * back) + a * (-0.03)]
    return hold_tentacle('scrollarm', -22.0, approach, wrap, _toward_axis(c, a), gc, a)


def quill_tentacle() -> dict:
    a = QUILL['axis']
    gc = quill_point(QUILL['grip'])
    inward = perp_dir((1.0, 0.4, 0.0), a)
    front = perp_dir((0.0, -1.0, 0.0), a)
    wrap = helix(gc, a, inward, -front, QUILL['r'] + 0.034, 1.05, 0.085, 60, shrink=0.1)
    # round 3: rising straight to the quill (a U-hook down and back up fused with the right arm's root: a knot)
    # polish (review: a crumpled knot where it enters the wrap): no point 3 cm off the wrap's start (a kink there)
    approach = [(-0.25, -0.03, 0.39), (-0.33, -0.09, 0.405)]
    out = perp_dir((-1.0, -0.6, 0.0), a)
    tip = [wrap[-1] + 0.025 * out + a * 0.012]
    return hold_tentacle('quillarm', -98.0, approach, wrap, _toward_axis(gc, a), gc, a, tip)


def book_tentacle() -> dict:
    """Round 2: the book opens in a V toward the front (its pages to the camera), its spine at the back; the tentacle
    comes to the spine, runs under the book and curls its tip up the outer cover's side."""
    c, f, across, up = book_frame()
    h = BOOK['h']
    bottom = c - up * (0.5 * h)
    # polish (review: the arm poked up through the page block): from behind the back cover it wraps round the spine's
    # lower third, clear of it, and its tip lies along the front cover's outside; never under or between the pages
    sp = -across * (0.5 * BOOK['w'])                   # the spine, from the bottom edge's middle
    p1 = bottom + up * 0.07 + sp + across * 0.06 - f * 0.09
    p2 = bottom + up * 0.085 + sp - across * 0.032 - f * 0.056
    p3 = bottom + up * 0.096 + sp - across * 0.064
    p4 = bottom + up * 0.106 + sp - across * 0.034 + f * 0.056
    p5 = bottom + up * 0.116 + sp + across * 0.02 + f * 0.068
    p6 = bottom + up * 0.126 + sp + across * 0.058 + f * 0.088
    wrap = _catmull(np.array([p1, p2, p3, p4, p5, p6]), 12)
    # (kept forward of the ink arm's root: touching it, the two shared skin that tore in ko and the strike)
    approach = [(0.2, -0.075, 0.418), bottom + up * 0.06 + sp + across * 0.13 - f * 0.11]

    def toward(p):
        q = v3(p) - bottom
        return (bottom + sp + up * float(q @ up)) - v3(p)       # the spine's axis at the same height
    grip = bottom + sp + up * 0.096
    # (a little slimmer: between the head's underside and the front-left arm's root, a thick one shared skin with both)
    return hold_tentacle('bookarm', 72.0, approach, wrap, toward, grip, up, r_root=0.072)


# ----------------------------------------------------------------------------- all of them
def finish(m: dict) -> dict:
    """The bone points on the centreline (the joints' arc lengths, then the tail) and the arc → bone map."""
    s, pts = m['s'], m['pts']
    jp = [np.array([np.interp(j, s, pts[:, k]) for k in range(3)]) for j in m['joints']]
    m['bone_pts'] = [tuple(round(float(x), 4) for x in p) for p in jp + [v3(m['tail'])]]
    j3 = m['joints'][-1]
    m['knots'] = list(m['joints']) + [j3 + 2.0 * max(0.01, m['rigid_from'] - j3)]
    m['L'] = float(s[-1])
    return m


_CACHE: dict = {}


def tentacles() -> list[dict]:
    if 'all' not in _CACHE:
        _CACHE['all'] = [ground_tentacle(g) for g in GROUND] + [scroll_tentacle(), quill_tentacle(), book_tentacle()]
    return _CACHE['all']


def by_name() -> dict:
    return {m['name']: m for m in tentacles()}


def tube_parts(m: dict) -> list[Part]:
    """The tentacle as overlapping tapered tubes (the voxel union smooths them into one)."""
    pts, rad, s = m['pts'], m['rad'], m['s']
    out = []
    i = 0
    k = 0
    while i < len(pts) - 1:
        step = float(np.clip(0.5 * rad[i], 0.006, 0.024))
        j = int(np.searchsorted(s, s[i] + step))
        j = min(max(j, i + 1), len(pts) - 1)
        out.append(Part(f"{m['name']}{k}", 'tube', loc=tuple(map(float, pts[i])), to=tuple(map(float, pts[j])),
                        radius=float(rad[i]), r2=float(rad[j])))
        i = j
        k += 1
    return out


def all_parts() -> list[Part]:
    ps = [Part('mantle', 'sphere', loc=MANTLE[0], radius=1.0, scale=MANTLE[1]),
          Part('crown', 'sphere', loc=CROWN[0], radius=1.0, scale=CROWN[1]),
          Part('core', 'sphere', loc=CORE[0], radius=1.0, scale=CORE[1])]
    for m in tentacles():
        ps += tube_parts(m)
    return ps

