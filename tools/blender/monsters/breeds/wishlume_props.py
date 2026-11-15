"""Wishlume's props (wishlume_ultra.py build_props): the lacquered bamboo frame, the crown and its handle, the tassel.

- ribs: ten thin bamboo ribs on the paper from under the crown down past the paper's edge to the bottom hoop (the
  front one stops between the eyes), with flat twine bindings (4-details 1, 6).
- the opening (round 2, 4-details 5, 2-turnaround front): the hoop hangs a little below the paper's edge and flares,
  about 1.5 x a rib's thickness, with a tan binding where each rib meets it; between them a glowing band of paper lit
  from inside (the `skirt`), so even a level camera sees a bright crescent under the body.
- the crown (round 2, 4-details 1): a flared red base, a coil of tan rope, a stacked red cap and a thick arched handle
  wrapped in red cord, tan bindings at its feet (turned 35 degrees toward the three-quarter camera).
- the tassel (round 2, 1-hero, 4-details 4): four cords from the hoop meet in a knot with two loops under the
  opening, a short cord, the red bead with gold bands, the wrapped collar, then one silky mass: a solid bell-shaped
  core with about seventy fat strands lying on it that fall past its rim and curl softly, and a few hanging from
  its underside (geometry: fur cards read as glassy flakes in this renderer).
- the paddles' rims: a red cord round each paddle's outline (4-details 3).

Every object carries part / pt / pa / pr / plen (wishlume_mesh.Bundle) for the paint and the weights.
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Vector

from lib.surface import smooth
from monsters.breeds import wishlume_form as F
from monsters.breeds.wishlume_mesh import Bundle, torus_path

# part ids (the paint and the weights read them)
(RIB, WRAP, CROWN, ROPE, LOOP, RING, RINGWRAP, CORD, KNOT, BEAD, GOLD, COLLAR, CORE, THREAD, ARMRIM, SKIRT,
 HANDLEBAND) = range(1, 18)
CAP_PARTS = (CROWN, ROPE, LOOP, HANDLEBAND)
TASSEL_PARTS = (BEAD, GOLD, COLLAR, CORE, THREAD)

HANDLE_C, HANDLE_R, HANDLE_TUBE = (0.0, 0.0, 0.871), 0.034, 0.0155     # round 3: half again as thick
LOOP_TURN = 35.0
RING_Z = 0.318                                  # the hoop: a little below the paper's edge (F.Z_OPEN 0.339) ...
RING_R, RING_TUBE, RING_ASPECT = 0.154, 0.0072, 1.25     # ... flared wider than the body's bottom, 1.5 x a rib's thickness
# round 3: the lit lip between the paper's edge and the hoop flares out to it (it read as a pinched collar)
LIP = [(0.1325, 0.3455), (0.1345, 0.3395), (0.1528, 0.3228), (0.1508, 0.3196), (0.1316, 0.3375), (0.1306, 0.3442), (0.1325, 0.3455)]
JUNCTION_Z = 0.31                               # round 3: the four cords meet here; a short cord with the knot hangs below
KNOT_Z = 0.297
BEAD_C, BEAD_R = 0.252, 0.0357                  # polish: the bead 1.4x
COLLAR_Z = (0.197, 0.222)
THREAD_TOP, THREAD_R = 0.205, 0.003            # polish: slightly fatter strands
# round 3: the core ends well inside the strands, tapered to a point (its flat end showed like a plug in hit_heavy)
CORE_PROFILE = [(0.0, 0.095), (0.012, 0.101), (0.028, 0.118), (0.042, 0.146), (0.037, 0.174), (0.026, 0.196), (0.021, 0.206),
                (0.0, 0.208)]


def _arclen(P: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])


def _resample(P: np.ndarray, n: int) -> np.ndarray:
    s = _arclen(P)
    si = np.linspace(0, s[-1], n)
    return np.stack([np.interp(si, s, P[:, k]) for k in range(3)], axis=1)


def _ring_xy(theta: float, r: float) -> tuple[float, float]:
    t = math.radians(theta)
    return r * math.sin(t), -r * math.cos(t) * F.A_Y / F.A_X


def rib_path(theta: float, n: int, front: bool = False) -> np.ndarray:
    """A rib's centre line: on the paper at angle theta from under the crown's base to the paper's edge (lifted by 0.72
    of its radius, sunk a little into the paper), then down over the glowing band to the hoop (the front rib stops
    between the eyes); resampled to n points evenly along it."""
    psi = np.linspace(0.05, 2.95, 500)
    t = math.radians(theta)
    u = np.stack([np.sin(psi) * math.sin(t), -np.sin(psi) * math.cos(t), np.cos(psi)], axis=1)
    p = F.globe_point(np.asarray(F.C0) + u)
    rxy = np.sqrt(p[:, 0] ** 2 + p[:, 1] ** 2)
    keep = (rxy >= F.RIB_TOP_R - 0.005) & (p[:, 2] >= (F.FRONT_RIB_END if front else F.Z_OPEN + 0.004))
    p = p[keep]
    nrm = np.array([F.normal_at(Vector(q))[:] for q in p])
    p = p + nrm * F.RIB_R * 0.72
    if not front:
        # down the lit lip's outer face (LIP) to the top of the flared hoop
        x1, y1 = _ring_xy(theta, 0.1436 + F.RIB_R * 0.85)
        x2, y2 = _ring_xy(theta, RING_R + 0.0005)
        tail = np.array([[x1, y1, 0.3312], [x2, y2, RING_Z + RING_TUBE * 0.7]])
        p = np.concatenate([p, tail])
    return _resample(p, n)


def ribs(b: Bundle, high: bool) -> None:
    n = 120 if high else 48
    sides = 12 if high else 7
    grain = (lambda pa, s: 0.00012 * np.cos(2 * np.pi * pa * 6)) if high else None
    for k, th in enumerate(F.rib_angles()):
        front = k == 0
        P = rib_path(th, n, front)
        s = _arclen(P)
        nodes = np.array([0.035, 0.19, 0.35] if not front else [0.035, 0.19])
        nodes = nodes[nodes < s[-1] - 0.01]
        # polish: a slight node bulge at each tan binding (bamboo)
        r = F.RIB_R * (1 + 0.14 * np.exp(-((s[:, None] - nodes[None]) / 0.011) ** 2).sum(axis=1))
        if front:
            r = r * (0.62 + 0.38 * smooth(s[-1], s[-1] - 0.02, s))       # round 3: a blunt end at the brow line
        b.tube(P, r, sides, RIB, pr=k / F.RIBS, caps=(False, front), relief=grain, texel_k=0.8)


def twine(pa, s, strands: int = 3, pitch: float = 0.0045, depth: float = 0.00045):
    return depth * np.cos(2 * np.pi * (pa * strands + s / pitch))


def band_at(b: Bundle, P: np.ndarray, s0: float, r0: float, high: bool, part: int, half: float = 0.006, aspect: float = 1.0,
            hint=None, swell: float = 0.0012) -> None:
    """A flat binding of twine round a rod (centre line P, radius r0) at arc length s0 (round 2: flat cord bands, not
    beads): it stands `swell` proud along its length and closes onto the rod at both ends (no open hole)."""
    s = _arclen(P)
    si = np.linspace(s0 - half, s0 + half, 11 if high else 6)
    Q = np.stack([np.interp(si, s, P[:, k]) for k in range(3)], axis=1)
    t = np.linspace(0, 1, len(si))
    r = r0 * 0.97 + swell * smooth(0.0, 0.14, t) * smooth(1.0, 0.86, t)
    b.tube(Q, r, 10 if high else 6, part, pr=float(s0 % 1.0), aspect=aspect, hint=hint,
           relief=(lambda pa, ss: twine(pa, ss, 4, 0.004, 0.0003)) if high else None)


def rib_wraps(b: Bundle, high: bool) -> None:
    for k, th in enumerate(F.rib_angles()):
        front = k == 0
        P = rib_path(th, 200, front)
        L = _arclen(P)[-1]
        at = [0.035, 0.19] if front else [0.035, 0.19, 0.35]
        for s0 in at:
            band_at(b, P, s0, F.RIB_R * 1.13, high, WRAP)


def ring_path(n: int, z: float = RING_Z, r: float = RING_R) -> np.ndarray:
    return torus_path((0.0, 0.0, z), (0, 0, 1), (1, 0, 0), r, n, r * F.A_Y / F.A_X)


def ring(b: Bundle, high: bool) -> None:
    relief = (lambda pa, s: 0.00012 * np.cos(2 * np.pi * pa * 7)) if high else None
    b.tube(ring_path(220 if high else 96), RING_TUBE, 14 if high else 10, RING, closed=True, hint=(1, 0, 0), aspect=RING_ASPECT,
           relief=relief, texel_k=0.9)


def lip(b: Bundle, high: bool) -> None:
    """The lit lip between the paper's edge and the hoop (round 3: flared out to the hoop, a closed ring section):
    the brightest band on the model with the inside (wishlume_paint: its own glowing paint)."""
    b.lathe(LIP, (0, 0, 0), 120 if high else 56, SKIRT, texel_k=0.8)


def ring_wraps(b: Bundle, high: bool) -> None:
    P0 = ring_path(720)
    for th in F.rib_angles():
        ang = np.degrees(np.arctan2(P0[:, 0], -P0[:, 1]))
        i = int(np.argmin(np.abs((ang - th + 180) % 360 - 180)))
        P = np.roll(P0, len(P0) // 2 - i, axis=0)          # the band's spot mid-path (the loop's start is a seam)
        band_at(b, P, float(_arclen(P)[len(P0) // 2]), RING_TUBE, high, RINGWRAP, half=0.0075, aspect=RING_ASPECT,
                hint=(1, 0, 0), swell=0.0014)


def cords(b: Bundle, high: bool) -> None:
    """Four cords from inside the hoop meet under the opening (4-details 5); from there a short cord hangs through the
    knot (two loops, 1-hero, 4-details 4) into the bead (round 3: long enough to see between the hoop and the bead)."""
    for k in range(4):
        th = 45 + 90 * k
        x0, y0 = _ring_xy(th, RING_R - 0.009)
        x1, y1 = _ring_xy(th, 0.05)
        x2, y2 = _ring_xy(th, 0.004)
        a = np.array([x0, y0, RING_Z - 0.004])
        c = np.array([x1, y1, RING_Z - 0.01])
        e = np.array([x2, y2, JUNCTION_Z])
        t = np.linspace(0, 1, 18 if high else 10)[:, None]
        P = (1 - t) ** 2 * a + 2 * (1 - t) * t * c + t ** 2 * e
        b.tube(P, 0.0023, 8 if high else 6, CORD, pr=k / 4, relief=(lambda pa, s: twine(pa, s, 2, 0.006, 0.0003)) if high else None,
               texel_k=0.7)
    P = np.stack([np.zeros(8), np.zeros(8), np.linspace(JUNCTION_Z + 0.002, BEAD_C + BEAD_R * 0.7, 8)], axis=1)
    b.tube(P, 0.0034, 8 if high else 6, CORD, pr=0.9, relief=(lambda pa, s: twine(pa, s, 2, 0.006, 0.0003)) if high else None,
           texel_k=0.7, caps=(True, False))
    # the knot's two loops, turned toward the three-quarter camera
    t = math.radians(LOOP_TURN)
    for s in (1, -1):
        c = (s * 0.0118 * math.cos(t), s * 0.0118 * math.sin(t), KNOT_Z - 0.001)
        P = torus_path(c, (math.sin(t), -math.cos(t), 0.0), (0, 0, 1), 0.0074, 40 if high else 18)
        b.tube(P, 0.0026, 8 if high else 6, KNOT, closed=True, hint=(0, 0, 1), texel_k=0.7)


def bead_parts(high: bool) -> Bundle:
    """The knot's button, the bead, the collar and the tassel's solid core (lathes, smart-projected)."""
    b = Bundle()
    sides = 40 if high else 20
    knot = [(0.0, KNOT_Z - 0.0105), (0.0066, KNOT_Z - 0.009), (0.0104, KNOT_Z - 0.004), (0.011, KNOT_Z + 0.0005),
            (0.0088, KNOT_Z + 0.0055), (0.004, KNOT_Z + 0.0082), (0.0, KNOT_Z + 0.009)]
    b.lathe(knot, (0, 0, 0), sides, KNOT)
    phi = np.linspace(0, math.pi, 16 if high else 11)
    bead = [(float(BEAD_R * math.sin(f)), float(BEAD_C - BEAD_R * 0.9 * math.cos(f))) for f in phi]
    bead[0], bead[-1] = (0.0, bead[0][1]), (0.0, bead[-1][1])
    b.lathe(bead, (0, 0, 0), sides + 8, BEAD)
    collar = [(0.0, COLLAR_Z[0]), (0.0178, COLLAR_Z[0]), (0.0198, COLLAR_Z[0] + 0.0025), (0.0202, COLLAR_Z[1] - 0.003),
              (0.0184, COLLAR_Z[1]), (0.0, COLLAR_Z[1])]
    b.lathe(collar, (0, 0, 0), sides, COLLAR)
    b.lathe(CORE_PROFILE, (0, 0, 0), 56 if high else 40, CORE, texel_k=0.7)
    return b


def gold_bands(b: Bundle, high: bool) -> None:
    for z, R, tube in ((BEAD_C - 0.008, BEAD_R * 0.958, 0.0026), (BEAD_C + BEAD_R * 0.86, 0.009, 0.0021),
                       (COLLAR_Z[0] + 0.004, 0.0203, 0.0021), (COLLAR_Z[1] - 0.0042, 0.0204, 0.0021)):
        P = torus_path((0, 0, z), (0, 0, 1), (1, 0, 0), R, 64 if high else 28)
        b.tube(P, tube, 8 if high else 6, GOLD, closed=True, hint=(0, 0, 1))


def _core_r(z: np.ndarray) -> np.ndarray:
    zs = np.array([p[1] for p in CORE_PROFILE[3:-1]])            # ascending, from its widest up to the collar
    rs = np.array([p[0] for p in CORE_PROFILE[3:-1]])
    return np.interp(z, zs, rs)


def threads(b: Bundle, high: bool) -> None:
    """The silk (round 3, 1-hero, 4-details 4): strands lie side by side on the core from the collar, then fall in a
    bell that flares out to about 0.2 m across at the fringe, a gentle sweep round it and the ends curling softly
    outward; an inner layer fills the bell, so the core (which ends well inside) is never seen end-on."""
    rng = np.random.default_rng(1405)
    n = 22 if high else 13
    sides = 8 if high else 6
    t = np.linspace(0, 1, n)
    on_core = 0.32                                              # the share of the length lying on the core
    zc = 0.146
    for layer, (count, r_tip, z_tip, rad) in enumerate(((160, 0.11, 0.012, THREAD_R), (68, 0.074, 0.022, THREAD_R * 0.9))):
        for i in range(count):
            a0 = 2 * math.pi * (i + 0.5 * layer + rng.uniform(-0.25, 0.25)) / count
            zt = z_tip + rng.uniform(0.0, 0.014)
            rt = r_tip + rng.uniform(-0.008, 0.008)
            curl = rng.uniform(0.006, 0.014)
            u = np.clip((t - on_core) / (1 - on_core), 0, 1)
            z = np.where(t < on_core, THREAD_TOP + (zc - THREAD_TOP) * (t / on_core), zc + (zt - zc) * u)
            r_on = _core_r(np.clip(z, zc, THREAD_TOP)) + THREAD_R * 0.85 - 0.004 * layer
            r = r_on + (rt - r_on) * u ** 1.5 + curl * smooth(0.78, 1.0, u)
            z = z + 0.007 * smooth(0.85, 1.0, u) * (curl / 0.014)
            ang = a0 + (0.1 + rng.uniform(-0.06, 0.06)) * u ** 1.4
            P = np.stack([r * np.sin(ang), -r * np.cos(ang), z], axis=1)
            b.tube(P, rad * (1.0 - 0.32 * t), (8 if high else 5) if layer == 0 else 5, THREAD, pr=float(rng.uniform()), caps=(False, True),
                   texel_k=0.45)


def crown(high: bool) -> Bundle:
    """The flared red base on the paper and the stacked red cap above the rope's coil (lathes)."""
    b = Bundle()
    base = [(0.0, 0.808), (0.06, 0.81), (0.078, 0.818), (0.0812, 0.826), (0.0775, 0.8325), (0.066, 0.8345), (0.0, 0.835)]
    b.lathe(base, (0, 0, 0), 72 if high else 36, CROWN)
    cap = [(0.0, 0.833), (0.0598, 0.834), (0.0598, 0.8575), (0.0628, 0.8595), (0.0625, 0.8665), (0.058, 0.8712), (0.04, 0.8728),
           (0.0, 0.8732)]
    b.lathe(cap, (0, 0, 0), 64 if high else 32, CROWN)
    return b


def rope_and_handle(b: Bundle, high: bool) -> None:
    """The rope's coil round the cap (three turns of tan twine) and the thick arched handle, cord-wrapped, its feet
    sunk in the cap with a tan binding at each (4-details 1)."""
    turns, z0, z1, rr = 3.0, 0.8372, 0.8548, 0.0638
    k = 260 if high else 110
    u = np.linspace(0, 1, k)
    a = 2 * math.pi * turns * u
    P = np.stack([rr * np.cos(a), rr * np.sin(a), z0 + (z1 - z0) * u], axis=1)
    rope = (lambda pa, s: 0.0009 * np.abs(np.cos(np.pi * (2 * pa + s / 0.011)))) if high else None
    b.tube(P, 0.0034, 10 if high else 7, ROPE, hint=(0, 0, 1), relief=rope, caps=(True, True))
    t = math.radians(LOOP_TURN)
    nrm = np.array([math.sin(t), -math.cos(t), 0.0])
    side = np.array([math.cos(t), math.sin(t), 0.0])
    ang = np.linspace(-0.12, math.pi + 0.12, 70 if high else 30)
    c = np.array(HANDLE_C)
    P = c + HANDLE_R * (np.cos(ang)[:, None] * side + np.sin(ang)[:, None] * np.array([0.0, 0.0, 1.0]))
    wrap = (lambda pa, s: twine(pa, s, 1, 0.0042, 0.0006)) if high else None
    b.tube(P, HANDLE_TUBE, 14 if high else 10, LOOP, hint=nrm, relief=wrap, caps=(True, True))
    s = _arclen(P)
    for s0 in (0.012, s[-1] - 0.012):
        band_at(b, P, s0, HANDLE_TUBE, high, HANDLEBAND, half=0.0055, hint=nrm, swell=0.0015)


def _analytic_outline(a: float) -> np.ndarray:
    """The paddle part's own outline point at angle a in its middle plane (lib.mesh 'paddle': the tapered ellipse)."""
    sx, sy, _sz = F.ARM_HALF
    lo, hi = 0.0, 0.3
    for _ in range(40):
        rho = 0.5 * (lo + hi)
        ly, lx = rho * math.cos(a), rho * math.sin(a)
        kk = min(max((ly / sy + 1) / 2, 0.0), 1.0)
        w = (1 - F.ARM_TAPER) + F.ARM_TAPER * math.sin(min(1.0, kk * 1.15) * math.pi / 2)
        if (lx / (sx * w)) ** 2 + (ly / sy) ** 2 > 1:
            hi = rho
        else:
            lo = rho
    rho = 0.5 * (lo + hi) - 0.0006
    return np.array(F.ARM_C[:]) + np.array(F.ARM_M) @ np.array([rho * math.sin(a), rho * math.cos(a), 0.0])


def paddle_outline(n: int = 480) -> np.ndarray:
    """The left paddle's outline in its middle plane, from where it leaves the globe round the tip and back: the red
    cord's path (4-details 3). Polish: found on the built body itself (rays from the paddle's centre in its middle
    plane), so the cord follows the real edge over the root's fillet right to the shoulder instead of stopping where
    the paddle part's own outline sank into the fillet; the paddle part's outline without a body (or a missed ray)."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    body = bpy.data.objects.get('hi_body')
    bvh = None
    if body is not None and body.type == 'MESH':
        me = body.data
        verts = [v.co.copy() for v in me.vertices]
        bvh = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
    M = np.array(F.ARM_M)
    c = Vector(F.ARM_C[:])
    th = np.linspace(-math.pi, math.pi, n, endpoint=False)
    pts = []
    for a in th:
        d = M @ np.array([math.sin(a), math.cos(a), 0.0])
        hit = bvh.ray_cast(c, Vector(d), 0.4) if bvh is not None else (None,)
        pts.append(np.array(hit[0][:]) - d * 0.0008 if hit[0] is not None else _analytic_outline(a))
    pts = np.array(pts)
    out = F.outside(pts) > 0.0025
    i0 = n // 2                                       # theta 0: the tip
    lo_i = i0
    while lo_i > 0 and out[lo_i - 1]:
        lo_i -= 1
    hi_i = i0
    while hi_i < n - 1 and out[hi_i + 1]:
        hi_i += 1
    P = pts[lo_i:hi_i + 1]
    # a light smoothing along it (the voxel body's facets)
    for _ in range(3):
        P[1:-1] = 0.25 * P[:-2] + 0.5 * P[1:-1] + 0.25 * P[2:]
    return P


def arm_rims(b: Bundle, high: bool) -> None:
    P0 = _resample(paddle_outline(), 90 if high else 40)
    t = np.linspace(0, 1, len(P0))
    r = 0.0048 * (0.55 + 0.45 * smooth(0.0, 0.06, t) * smooth(1.0, 0.94, t))
    for side in (1, -1):
        b.tube(P0 * np.array([side, 1.0, 1.0]), r, 10 if high else 7, ARMRIM, pr=0.5 + 0.25 * side, caps=(True, True),
               relief=(lambda pa, ss: 0.00012 * np.cos(2 * np.pi * pa * 7)) if high else None, texel_k=0.8)


def objects(high: bool) -> list:
    tag = 'hi' if high else 'lo'
    out = []
    b = Bundle()
    ribs(b, high)
    out.append(b.object(f'{tag}_ribs'))
    b = Bundle()
    rib_wraps(b, high)
    ring_wraps(b, high)
    out.append(b.object(f'{tag}_wraps'))
    b = Bundle()
    ring(b, high)
    cords(b, high)
    arm_rims(b, high)
    out.append(b.object(f'{tag}_ring'))
    cb = crown(high)
    lip(cb, high)
    out.append(cb.object(f'{tag}_crown', own_uv=False))
    b = Bundle()
    rope_and_handle(b, high)
    gold_bands(b, high)
    out.append(b.object(f'{tag}_loop'))
    out.append(bead_parts(high).object(f'{tag}_bead', own_uv=False))
    b = Bundle()
    threads(b, high)
    out.append(b.object(f'{tag}_threads'))
    return out
