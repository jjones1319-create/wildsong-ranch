"""Velvesper's form (Art 2.1 Ultra; chatgpt/monsters/28-velvesper; CONTENT entry 13): the joints, the body's primitives,
the fluffy lobes of the ruff, the abdomen and the cheeks (body_extras), the eyes' frames and an analytic distance field
of the body that the lobes and the props lean on.

Measured on 2-turnaround (front view, 3.65 mm a pixel: the head's top at 1.085 m, HEIGHT_UNITS 165): the head 0.48 m
wide (the cheeks' fluff) and 0.365 m tall, the eyes on the eye line at 0.84 m, the ruff below it down to 0.45 m and
0.38 m wide, the abdomen hanging to 0.2 m, six little legs dangling to 0.13 m (the hover gap), the feathery antennae
arching up to 1.31 m and out to 0.45 m each side; the forewings 1.75 m tip to tip (the card: about 2 x Puddlepup's
height), their tips at 1.0 m, their tops at 1.11 m; the hindwings 1.26 m across and down to 0.18 m. The side view and the
hero: the body hovers upright, the wings swept back about 30 degrees (the three-quarter hero shows the near wing face-on).

Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib.mesh import Part

# ----------------------------------------------------------------------------- joints
HIP = (0.0, 0.0, 0.52)                      # the pivot (`body`): the thorax's lower middle
NECK = (0.0, 0.0, 0.745)                    # the head's base: the one front segment runs hip -> neck
CHEST = (0.0, 0.0, 0.64)
FRONT = [HIP, NECK]
REAR = [HIP, (0.0, 0.01, 0.37), (0.0, 0.05, 0.2)]        # the big round belly (hips, rear.1)
HEAD_C = (0.0, -0.01, 0.9)
HEAD_R = 0.2
HEAD_TIP = (0.0, -0.18, 0.86)               # on the face's front
JAW = {'head': (0.0, -0.14, 0.78), 'tail': (0.0, -0.17, 0.778)}
# the legs: hip, knee and the sole (the plan lands the lowest sole 1 cm off the ground)
# (round 2) little legs, two thirds as long again (the reviewer: still a hand of six fingers under the ruff): each
# from the big belly's lower front and sides, only its lower half showing, bent forward at a knee, tapering from a
# fuzzy thigh to a small dark foot with two toe tufts; the pairs staggered front to back and up; knees and feet 2-4 cm
# apart
LEGS = [{'hip': (0.065, -0.13, 0.29), 'knee': (0.09, -0.21, 0.22), 'foot': (0.075, -0.2, 0.138)},
        {'hip': (0.12, -0.09, 0.28), 'knee': (0.165, -0.15, 0.215), 'foot': (0.15, -0.14, 0.15)},
        {'hip': (0.15, -0.02, 0.28), 'knee': (0.2, -0.06, 0.225), 'foot': (0.185, -0.055, 0.162)}]
THIGH_R, SHIN_R, FOOT_R = (0.042, 0.034), (0.032, 0.024), (0.026, 0.03, 0.028)

# ----------------------------------------------------------------------------- helpers


def unit(v) -> np.ndarray:
    v = np.asarray(v, np.float64)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def mirror(p, s: int) -> tuple[float, float, float]:
    return (float(p[0]) * s, float(p[1]), float(p[2]))


def smooth(a: float, b: float, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def basis(d, n) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """An orthonormal frame: Y along d, Z as close to n as allowed, X = Y x Z."""
    y = unit(d)
    z = unit(np.asarray(n, np.float64) - y * float(np.dot(n, y)))
    x = np.cross(y, z)
    return x, y, z


# ----------------------------------------------------------------------------- the body's primitives
# (centre, radii, rotation in degrees XYZ)
ELLS = {
    # (round 1) no cheek domes (they read as earmuffs on a helmet): a rounder skull, and flared cheek tufts (lobe_specs)
    'skull': ((0.0, 0.0, 0.896), (0.235, 0.195, 0.19), (0.0, 0.0, 0.0)),
    # (build 1) the cheeks back and up, the muzzle small: in front they made a 'moustache' under the eyes
    'muzzle': ((0.0, -0.14, 0.8), (0.062, 0.05, 0.043), (0.0, 0.0, 0.0)),
    # (polish) a soft bridge between the eyes, so from the side the face stands in front of them
    'bridge': ((0.0, -0.163, 0.848), (0.032, 0.036, 0.052), (0.0, 0.0, 0.0)),
    'thorax': ((0.0, 0.0, 0.615), (0.195, 0.17, 0.165), (0.0, 0.0, 0.0)),
    # (build 1) fills the crease under the chin: the ruff's top tufts and the cheeks left a deep slot there that the
    # game mesh bridged and the bake's rays fell into (black under the chin)
    'neck': ((0.0, -0.03, 0.735), (0.16, 0.115, 0.075), (0.0, 0.0, 0.0)),
    # (polish) a soft chin from the muzzle down into the ruff: the crease under the muzzle baked no texels (dark specks
    # under the chin in every close-up)
    'chin': ((0.0, -0.11, 0.76), (0.13, 0.07, 0.045), (0.0, 0.0, 0.0)),
    # (round 2) the hero's BIG round fluffy belly under the ruff, about as wide as the head, the legs out of its lower
    # half (round 1's was half this and hid behind the legs)
    'belly': ((0.0, 0.0, 0.39), (0.2, 0.19, 0.2), (0.0, 0.0, 0.0)),        # up into the ruff: no waist between them
}
HEAD_PARTS = ('skull', 'muzzle', 'bridge')


def leg_points(s: int) -> list[np.ndarray]:
    return [np.array(mirror(LEGS[i][k], s)) for i in range(3) for k in ('hip', 'knee', 'foot')]


def leg_chain(i: int, s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lg = LEGS[i]
    return tuple(np.array(mirror(lg[k], s)) for k in ('hip', 'knee', 'foot'))


def foot_centre(i: int, s: int) -> np.ndarray:
    f = np.array(mirror(LEGS[i]['foot'], s))
    return f + np.array((0.0, -0.004, FOOT_R[2] - 0.001))


def all_parts() -> list[Part]:
    ps = []
    for nm, (c, r, rot) in ELLS.items():
        ps.append(Part(nm, 'sphere', loc=tuple(c), radius=1.0, scale=tuple(r), rot=tuple(rot)))
    for s in (1, -1):
        for i in range(3):
            h, k, f = leg_chain(i, s)
            fc = foot_centre(i, s)
            ps += [Part(f'thigh{i}{s}', 'tube', loc=tuple(h), to=tuple(k), radius=THIGH_R[0], r2=THIGH_R[1]),
                   Part(f'shin{i}{s}', 'tube', loc=tuple(k), to=tuple(fc), radius=SHIN_R[0], r2=SHIN_R[1]),
                   Part(f'foot{i}{s}', 'sphere', loc=tuple(fc), radius=1.0, scale=FOOT_R)]
    return ps


# ----------------------------------------------------------------------------- an analytic distance field
def _rotm(rot) -> np.ndarray:
    rx, ry, rz = (math.radians(a) for a in rot)
    X = np.array(((1, 0, 0), (0, math.cos(rx), -math.sin(rx)), (0, math.sin(rx), math.cos(rx))))
    Y = np.array(((math.cos(ry), 0, math.sin(ry)), (0, 1, 0), (-math.sin(ry), 0, math.cos(ry))))
    Z = np.array(((math.cos(rz), -math.sin(rz), 0), (math.sin(rz), math.cos(rz), 0), (0, 0, 1)))
    return Z @ Y @ X


def sd_ell(p: np.ndarray, c, r, rot) -> np.ndarray:
    q = (np.asarray(p) - np.asarray(c)) @ _rotm(rot)
    r = np.asarray(r, np.float64)
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def sd_tube(p: np.ndarray, a, b, r1: float, r2: float) -> np.ndarray:
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    ab = b - a
    t = np.clip(((np.asarray(p) - a) @ ab) / float(ab @ ab), 0.0, 1.0)
    return np.linalg.norm(np.asarray(p) - (a + t[..., None] * ab), axis=-1) - (r1 + (r2 - r1) * t)


def body_sd(p: np.ndarray, head: bool = True) -> np.ndarray:
    """The head, thorax and abdomen (no legs): what the lobes lie on."""
    p = np.asarray(p, np.float64)
    d = np.full(p.shape[:-1], np.inf)
    for nm, (c, r, rot) in ELLS.items():
        if not head and nm in HEAD_PARTS:
            continue
        d = np.minimum(d, sd_ell(p, c, r, rot))
    return d


def head_sd(p: np.ndarray) -> np.ndarray:
    d = np.full(np.asarray(p).shape[:-1], np.inf)
    for nm in HEAD_PARTS:
        c, r, rot = ELLS[nm]
        d = np.minimum(d, sd_ell(p, c, r, rot))
    return d


def leg_dist(co: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The distance to the nearest leg's skin (thigh, shin, foot), the leg's index (0..5: L0 L1 L2 R0 R1 R2) and how far
    down that leg a point lies (0 hip .. 1 sole)."""
    co = np.asarray(co, np.float64)
    best = np.full(len(co), np.inf)
    idx = np.full(len(co), -1)
    down = np.zeros(len(co))
    for j, s in enumerate((1, -1)):
        for i in range(3):
            h, k, f = leg_chain(i, s)
            fc = foot_centre(i, s)
            d = np.minimum(sd_tube(co, h, k, *THIGH_R), sd_tube(co, k, fc, *SHIN_R))
            d = np.minimum(d, sd_ell(co, fc, FOOT_R, (0.0, 0.0, 0.0)))
            m = d < best
            best = np.where(m, d, best)
            idx = np.where(m, 3 * j + i, idx)
            L = float(np.linalg.norm(k - h) + np.linalg.norm(f - k))
            t1 = np.clip(((co - h) @ (k - h)) / float((k - h) @ (k - h)), 0, 1) * np.linalg.norm(k - h)
            t2 = np.clip(((co - k) @ (f - k)) / float((f - k) @ (f - k)), 0, 1) * np.linalg.norm(f - k)
            dn = np.where(t2 > 0, np.linalg.norm(k - h) + t2, t1) / L
            down = np.where(m, dn, down)
    return best, idx, down


def toe_mask(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(round 2) The feet's toe tufts: 1 within 6.5 cm of a foot's ball and no higher than its middle; and which leg
    (0..5: L0 L1 L2 R0 R1 R2)."""
    co = np.asarray(co, np.float64)
    best = np.full(len(co), np.inf)
    idx = np.full(len(co), -1)
    for j, s in enumerate((1, -1)):
        for i in range(3):
            fc = foot_centre(i, s)
            d = np.linalg.norm(co - fc, axis=1) + np.maximum(co[:, 2] - fc[2] - 0.004, 0.0) * 4.0
            m = d < best
            best = np.where(m, d, best)
            idx = np.where(m, 3 * j + i, idx)
    return best < 0.065, idx


def sd_normal(fn, p: np.ndarray, e: float = 0.002) -> np.ndarray:
    p = np.asarray(p, np.float64)
    g = np.stack([fn(p + np.array(v) * e) - fn(p - np.array(v) * e) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1))], axis=-1)
    return g / np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-9)


def surface_hit(fn, origin, dirs: np.ndarray, far: float = 0.6) -> np.ndarray:
    """Where rays from `origin` (inside) along `dirs` leave the field's zero set (bisection)."""
    dirs = np.asarray(dirs, np.float64).reshape(-1, 3)
    lo, hi = np.zeros(len(dirs)), np.full(len(dirs), far)
    o = np.asarray(origin, np.float64)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        inside = fn(o + dirs * mid[:, None]) < 0.0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    return o + dirs * (0.5 * (lo + hi))[:, None]


# ----------------------------------------------------------------------------- the fluffy lobes
def _tuft(rng, root, n_, d, L, W, T=0.022, lift=0.003, bury=0.014, split=3) -> list[dict]:
    """(round 1) One soft clump with split, wispy tips (the reviewer: zig-zag paper petals): a main lobe and one or two
    slimmer side lobes from the same root, their tips fanning apart a little."""
    out = [{'root': root, 'n': n_, 'd': d, 'L': L, 'W': W * 0.62, 'T': T, 'lift': lift, 'bury': bury}]
    side = unit(np.cross(n_, d))
    for sg in (1.0, -1.0)[:max(0, split - 1)]:
        a = math.radians(15.0 + 6.0 * rng.uniform(-1, 1)) * sg
        dk = unit(d * math.cos(a) + side * math.sin(a))
        out.append({'root': root + side * sg * W * 0.2, 'n': n_, 'd': dk, 'L': L * (0.8 + 0.1 * rng.uniform(-1, 1)), 'W': W * 0.48,
                    'T': T * 0.85, 'lift': lift * 1.5, 'bury': bury})
    return out


def _ring(rng, centre, el: float, n: int, L: float, W: float, span=(0.0, 360.0), outward: float = 0.25, lift: float = 0.003,
          fn=None, skip=None, down=(0.0, 0.0, -1.0), flare: float = 0.0, split: int = 3, T: float = 0.022) -> list[dict]:
    """A ring of soft clumps round `centre` at elevation `el` (degrees), lying along the surface and hanging down with
    their tips lifted a little off it (the fur's tufts: 1-hero, 2-turnaround back view); `flare` turns the ones at the
    sides further out (the ruff flaring over the shoulders)."""
    fn = fn or body_sd
    out = []
    a0, a1 = span
    full = abs(a1 - a0) >= 359.0
    for az in np.linspace(a0, a1, n, endpoint=not full) + rng.uniform(-6, 6):
        a, e = math.radians(az + rng.uniform(-4, 4)), math.radians(el + rng.uniform(-3, 3))
        d = np.array((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        root = surface_hit(fn, centre, d[None])[0]
        if skip is not None and skip(root):
            continue
        n_ = sd_normal(fn, root[None])[0]
        g = np.asarray(down, np.float64) + n_ * (outward + flare * abs(math.sin(a)))
        dd = unit(g - n_ * float(np.dot(g, n_)))
        k = 1.0 + 0.12 * rng.uniform(-1, 1)
        out += _tuft(rng, root, n_, dd, L * k, W * k, T=T * k, lift=lift, split=split)
    return out


def _near_eye(p) -> bool:
    for s in (1, -1):
        c = np.array(mirror(EYE_C, s))
        if np.linalg.norm(np.asarray(p) - c) < 2.0 * EYE_R:
            return True
    return False


def _scatter(rng, centre, n: int, el_range, L, W, T, fn, outward: float = 0.45, flare: float = 0.0, twist: float = 24.0,
             down=(0.0, 0.0, -1.0), skip=None, reject=None) -> list[dict]:
    """(round 2) Clumps scattered over a part (Fibonacci directions with jitter, not tidy rings: the rows read as
    shingles, an artichoke), each turned a little at random about the surface, of random length."""
    out = []
    ga = math.pi * (3.0 - math.sqrt(5.0))
    e0, e1 = (math.sin(math.radians(v)) for v in el_range)
    for k in range(n):
        z = e0 + (e1 - e0) * (k + 0.5) / n + rng.uniform(-0.5, 0.5) * (e1 - e0) / n
        a = k * ga + rng.uniform(-0.2, 0.2)
        rr = math.sqrt(max(0.0, 1.0 - z * z))
        d = np.array((math.sin(a) * rr, -math.cos(a) * rr, z))
        root = surface_hit(fn, centre, d[None])[0]
        if skip is not None and skip(root):
            continue
        n_ = sd_normal(fn, root[None])[0]
        g = np.asarray(down, np.float64) + n_ * (outward + flare * abs(math.sin(a)))
        dd = unit(g - n_ * float(np.dot(g, n_)))
        tw = math.radians(rng.uniform(-twist, twist))
        side = unit(np.cross(n_, dd))
        dd = unit(dd * math.cos(tw) + side * math.sin(tw))
        kL = rng.uniform(0.75, 1.2)
        if reject is not None and reject(root, dd, L * kL):
            continue
        out += _tuft(rng, root, n_, dd, L * kL, W * rng.uniform(0.85, 1.15), T=T, lift=0.006, split=3)
    return out


def _crosses_wing_root(root, d, L) -> bool:
    """(polish) True when a clump (root along d for L, plus 2 cm of thickness) reaches a wing's plane near its root."""
    from monsters.breeds import velvesper_props as PR
    p0, p1 = np.asarray(root, np.float64), np.asarray(root, np.float64) + np.asarray(d, np.float64) * L
    for s in (1, -1):
        eu, _ev, n = PR.frame(s)
        for name in ('fore', 'hind'):
            spec = PR.WINGS[name]
            o = np.array((PR.WING_ROOT[0] * s, PR.WING_ROOT[1], spec['z'])) + n * spec['offset']
            d0, d1 = float((p0 - o) @ n), float((p1 - o) @ n)
            if d0 * d1 > 0 and min(abs(d0), abs(d1)) > 0.02:
                continue
            f = 0.5 if d0 * d1 > 0 else d0 / (d0 - d1)
            q = p0 + (p1 - p0) * f
            u, v = float((q - o) @ eu), float(q[2] - o[2])
            if -0.06 < u < 0.4 and -0.45 < v < 0.45:
                return True
    return False


def lobe_specs() -> list[dict]:
    """(round 2) The fluff: soft, thick, rounded clumps (about as thick as they are wide, so no view sees a flat petal),
    each with three split tips, scattered (not in rows) and turned and sized at random. The ruff from under the chin
    round the thorax and across its back, flaring over the shoulders and down over the belly's top (no bare band); the
    big round belly all round (between the legs too); fuzz down each little leg; the cheeks' clumps from the face's
    sides right round to the back of the head; the crown's clumps; two little dark toe tufts on every foot (1-hero,
    3-faces, 4-details panel 3)."""
    rng = np.random.default_rng(13)
    out = []
    nohead = lambda p: body_sd(p, head=False)              # noqa: E731
    th = np.array(ELLS['thorax'][0])
    # (polish) the top row off the chin (dark smudges baked in the slot under it), the lower fringe further down over
    # the belly (no waist seam), and no clump through a wing's root (its peach rim poked out of the ruff)
    out += _scatter(rng, th, 116, (-56.0, 50.0), 0.1, 0.075, 0.04, nohead, outward=0.5, flare=0.45, reject=_crosses_wing_root)
    bc = np.array(ELLS['belly'][0])
    out += _scatter(rng, bc, 110, (-66.0, 42.0), 0.09, 0.07, 0.038, nohead, outward=0.45, reject=_crosses_wing_root)
    # the legs' thighs: a few small clumps round each, hanging down to the knee
    for s in (1, -1):
        for i in range(3):
            h, k, f = leg_chain(i, s)
            ax = unit(k - h)
            ref = unit(np.cross(ax, np.array((0.0, 0.0, 1.0)))) if abs(ax[2]) < 0.95 else np.array((1.0, 0.0, 0.0))
            ref2 = np.cross(ax, ref)
            for j in range(5):
                a = 2 * math.pi * j / 5 + rng.uniform(-0.3, 0.3)
                n_ = unit(ref * math.cos(a) + ref2 * math.sin(a))
                c = h + (k - h) * rng.uniform(0.35, 0.65)
                root = c + n_ * THIGH_R[0] * 0.8
                d = unit(ax * 1.0 + n_ * 0.25)
                out.append({'root': root, 'n': n_, 'd': d, 'L': 0.05, 'W': 0.034, 'T': 0.022, 'lift': 0.004, 'bury': 0.01})
    hc = np.array(ELLS['skull'][0])
    # the cheeks, from the face's sides round to the back of the head, combed out and down
    for el, L in ((6.0, 0.085), (-8.0, 0.095), (-22.0, 0.095), (-36.0, 0.085)):
        for side_span in ((58.0, 150.0), (-150.0, -58.0)):
            out += _ring(rng, hc, el, 6, L, 0.062, span=side_span, outward=0.75, lift=0.008, fn=head_sd, skip=_near_eye,
                         down=(0.0, 0.25, -1.0), T=0.04)
    # the crown: clumps over the top, the back and round the antennae's roots, combed back
    for az0, az1 in ((-24.0, 18.0), (44.0, 64.0), (-64.0, -44.0)):
        out += _ring(rng, hc, 66.0, 2 if az1 - az0 < 30 else 3, 0.065, 0.055, span=(az0, az1), outward=0.35, lift=0.004, fn=head_sd,
                     down=(0.0, 0.6, 0.5), split=2, T=0.036)
    for el, n, L, W, span in ((78.0, 6, 0.07, 0.058, (60.0, 300.0)), (60.0, 11, 0.075, 0.06, (66.0, 294.0)),
                              (42.0, 12, 0.08, 0.062, (96.0, 264.0)), (22.0, 10, 0.08, 0.062, (116.0, 244.0))):
        out += _ring(rng, hc, el, n, L, W, span=span, outward=0.3, lift=0.004, fn=head_sd, down=(0.0, 1.0, -0.6), split=2, T=0.036)
    # the toes: two little tufts at every foot's tip, splayed a little, pointing down and forward
    for s in (1, -1):
        for i in range(3):
            fc = foot_centre(i, s)
            for sg in (1.0, -1.0):
                d = unit(np.array((0.35 * sg, -0.55, -1.0)))
                root = fc + np.array((0.008 * sg, -0.006, -0.012))
                out.append({'root': root, 'n': unit(np.array((0.0, -1.0, 0.25))), 'd': d, 'L': 0.042, 'W': 0.022, 'T': 0.019,
                            'lift': 0.0, 'bury': 0.012})
    return out


def lobe_object(name: str, f: dict, seg: int = 14) -> bpy.types.Object:
    """A soft tuft drawn to a point (the ruff's and the abdomen's tufts are pointed, like down feathers: 2-turnaround):
    root buried, lying along the surface, the tip lifted a little."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2 + 2, radius=1.0)
    X, Y, Z = basis(f['d'], f['n'])
    L, W, T = f['L'], f['W'], f['T']
    for v in bm.verts:
        t = (v.co.y + 1.0) * 0.5                         # 0 root ... 1 tip
        # (round 1) a rounded tip on every clump (the pointed ones read as spikes, an artichoke): soft fingers
        w = math.sin(0.5 * math.pi * min(1.0, t * 2.0 + 0.3)) ** 0.6 * (1.0 - t ** 2.6) ** 0.5
        th = T * (1.0 - 0.35 * t)
        lx, ly, lz = v.co.x * W * 0.5 * w, t * L, v.co.z * th * 0.5 + f['lift'] * t * t
        p = f['root'] - Z * f['bury'] + X * lx + Y * ly + Z * lz
        v.co = Vector(tuple(p))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def body_extras() -> list[bpy.types.Object]:
    return [lobe_object(f'lobe{i}', f) for i, f in enumerate(lobe_specs())]


# ----------------------------------------------------------------------------- eyes
EYE_C = (0.096, -0.165, 0.865)
EYE_R = 0.055
EYE_LOOK = (0.22, -0.97, 0.06)              # (polish) a little more to the front: it stood out of the side profile
EYE_AX = (1.0, 1.06)                        # the lens's across and up radii, in EYE_R (round, a little tall)
EYE_DEPTH = 0.5                             # the lens flattened along its look
EYE_PROUD = 0.04                            # how far it stands out of the skin, in radii (round 2: flush with the face)
EYE_SINK = 0.005                            # (polish) the lens and its socket set this much into the face


def eye_frame(s: int):
    """(centre, across, up, look) of one lens: its centre set back from the skin along the look so the lens stands
    EYE_PROUD radii proud of it."""
    c0 = Vector(mirror(EYE_C, s))
    look = Vector(mirror(EYE_LOOK, s)).normalized()
    up = Vector((0.0, 0.0, 1.0))
    yax = (up - look * up.dot(look)).normalized()
    xax = yax.cross(look).normalized()
    hit = surface_hit(head_sd, np.array(c0) - np.array(look) * 0.05, np.array(look)[None], 0.12)[0]
    c = Vector(tuple(hit)) - look * (EYE_R * (EYE_DEPTH - EYE_PROUD))
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xa, ya, look = eye_frame(s)
    return Matrix.Translation(c) @ Matrix((xa, ya, look)).transposed().to_4x4()
