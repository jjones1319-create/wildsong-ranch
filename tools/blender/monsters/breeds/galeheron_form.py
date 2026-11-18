"""Galeheron's form (Art 2.1 Ultra; chatgpt/monsters/25-galeheron; CONTENT entry 11): the joints, the body's primitives,
the white breast's shaggy feather lobes (body_extras), the eyes' frames and an analytic distance field of the body that
the props (wing feathers, plumes) hug.

Measured on 2-turnaround (side view, 2.555 mm a pixel: the crest's top 1.70 m, the skull 1.57 m; the legs at y = 0):
the dagger beak from the face (y -0.20, z 1.42) to its tip (y -0.455, z 1.265), the eye at (y -0.195, z 1.465), the
S-neck from the shoulders (y -0.10, z 1.04) forward to y -0.19 at z 1.2 and back up under the skull, the white breast's
front at y -0.36, the belly's lower edge at z 0.57, the heel at z 0.42, the folded wing from the shoulder (z 1.13) back
to its tip (y 0.45, z 0.5), the tail plumes down to z 0.15 behind; front view: the body with the folded wings 0.48 m
wide, the feet 0.15 m apart, the toes spread 0.48 m.

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
HIP = (0.0, 0.05, 0.8)
CHEST = (0.0, -0.16, 0.98)
# (round 2) a real S: the neck leaves the leaning chest, bows forward low, then curves back up under the skull
NECK = [(0.0, -0.17, 1.0), (0.0, -0.29, 1.12), (0.0, -0.205, 1.27), (0.0, -0.15, 1.385)]     # (round 3) a deeper S
HEAD_C = (0.0, -0.172, 1.482)
HEAD_R = 0.075
HEAD_TIP = (0.0, -0.235, 1.445)
GAPE = (0.0, -0.198, 1.418)                 # the beak's gape corner (the jaw's hinge)
BEAK_TIP = (0.0, -0.458, 1.266)
JAW = {'head': GAPE, 'tail': (0.0, -0.446, 1.272)}
LEG = {'hip': (0.075, 0.05, 0.8), 'knee': (0.08, -0.05, 0.66), 'ankle': (0.077, 0.03, 0.42), 'toe': (0.075, -0.005, 0.034),
       'toe_tip': (0.075, -0.19, 0.016)}
EYE_C = (0.04, -0.215, 1.466)                  # (round 3) further forward, into the face
EYE_R = 0.023
EYE_LOOK = (0.47, -0.88, 0.04)

# ----------------------------------------------------------------------------- helpers


def unit(v) -> np.ndarray:
    v = np.asarray(v, np.float64)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def mirror(p, s: int) -> tuple[float, float, float]:
    return (float(p[0]) * s, float(p[1]), float(p[2]))


def smooth(a: float, b: float, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def euler_of(xax, yax, zax) -> tuple[float, float, float]:
    m = Matrix((tuple(map(float, xax)), tuple(map(float, yax)), tuple(map(float, zax)))).transposed()
    e = m.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def basis(d, n) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """An orthonormal frame: Y along d, Z as close to n as allowed, X = Y x Z."""
    y = unit(d)
    z = unit(np.asarray(n, np.float64) - y * float(np.dot(n, y)))
    x = np.cross(y, z)
    return x, y, z


# ----------------------------------------------------------------------------- the body's primitives
# (centre, radii, rotation in degrees XYZ) of the body's ellipsoids; the neck's tubes run through NECK
ELLS = {
    # (round 2) a sleek trunk leaning forward (its back about 35 degrees from level, 1-hero), a slimmer chest; no
    # separate belly ball (it creased against the chest)
    'core': ((0.0, 0.03, 0.84), (0.175, 0.34, 0.155), (-32.0, 0.0, 0.0)),
    'breast': ((0.0, -0.17, 0.92), (0.115, 0.115, 0.13), (-36.0, 0.0, 0.0)),        # (round 3) slimmer: the bib gives the volume
    'shoulders': ((0.0, -0.07, 1.025), (0.135, 0.15, 0.075), (-26.0, 0.0, 0.0)),
    'rump': ((0.0, 0.3, 0.665), (0.12, 0.16, 0.085), (-38.0, 0.0, 0.0)),
    # (round 2) a broader head, so the eyes sit inside its outline from the front (they stood out like bulbs)
    # (round 3) a wedge: broad at the back of the skull, narrowing to the beak, with a brow ledge over each eye
    'skull': ((0.0, -0.162, 1.485), (0.07, 0.08, 0.064), (8.0, 0.0, 0.0)),
    'face': ((0.0, -0.214, 1.448), (0.043, 0.052, 0.04), (0.0, 0.0, 0.0)),
    'chin': ((0.0, -0.18, 1.414), (0.042, 0.045, 0.036), (0.0, 0.0, 0.0)),
    'browL': ((0.04, -0.213, 1.489), (0.026, 0.04, 0.013), (0.0, 0.0, 22.0)),
    'browR': ((-0.04, -0.213, 1.489), (0.026, 0.04, 0.013), (0.0, 0.0, -22.0)),
    'nape': ((0.0, -0.13, 1.44), (0.046, 0.05, 0.05), (0.0, 0.0, 0.0)),
}
NECK_R = (0.064, 0.05, 0.045, 0.046)             # (round 3) slimmer: it was as wide as the head
# the leg's radii: the drumstick at the knee and the heel, the heel's knob, the tarsus at the heel and the foot
SHIN_R, HEEL_R, TARSUS_R = (0.034, 0.021), 0.0235, (0.0185, 0.016)
TOE_R = (0.0145, 0.0092)                   # (round 2) chunkier toes
CLAW = (0.026, 0.0068)                      # a claw's length and its radius at the toe


def toes(s: int) -> list[tuple[np.ndarray, np.ndarray, float]]:
    """(base, tip, radius scale) of one foot's toes: three forward (the outer splayed 40 degrees, the inner 26) and the
    hallux behind (4-details panel 3)."""
    b = np.array(mirror(LEG['toe'], s))
    out = []
    for ang, L, k in ((0.0, 0.185, 1.0), (40.0, 0.16, 0.95), (-26.0, 0.135, 0.92), (180.0, 0.08, 0.9)):
        a = math.radians(ang) * s
        d = np.array((math.sin(a), -math.cos(a), 0.0))
        tip = b + d * L + np.array((0.0, 0.0, -0.019))
        out.append((b + d * 0.012, tip, k))
    return out


def claw_tip(base, tip) -> np.ndarray:
    d = unit(np.asarray(tip) - np.asarray(base))
    return np.asarray(tip) + unit(d + np.array((0.0, 0.0, -0.55))) * CLAW[0]


def all_parts() -> list[Part]:
    ps = []
    for nm, (c, r, rot) in ELLS.items():
        ps.append(Part(nm, 'sphere', loc=tuple(c), radius=1.0, scale=tuple(r), rot=tuple(rot)))
    for i in range(len(NECK) - 1):
        ps.append(Part(f'neck{i}', 'tube', loc=NECK[i], to=NECK[i + 1], radius=NECK_R[i], r2=NECK_R[i + 1]))
    for s in (1, -1):
        k, a, t = (np.array(mirror(LEG[q], s)) for q in ('knee', 'ankle', 'toe'))
        ps += [Part(f'shin{s}', 'tube', loc=tuple(k), to=tuple(a), radius=SHIN_R[0], r2=SHIN_R[1]),
               Part(f'heel{s}', 'sphere', loc=tuple(a + np.array((0.0, 0.004, 0.0))), radius=1.0, scale=(HEEL_R, HEEL_R * 1.1, HEEL_R * 1.25)),
               Part(f'tarsus{s}', 'tube', loc=tuple(a), to=tuple(t), radius=TARSUS_R[0], r2=TARSUS_R[1]),
               Part(f'pad{s}', 'sphere', loc=tuple(t + np.array((0.0, -0.004, -0.006))), radius=1.0, scale=(0.024, 0.027, 0.014))]
        for j, (b, tip, kk) in enumerate(toes(s)):
            ps.append(Part(f'toe{s}{j}', 'tube', loc=tuple(b), to=tuple(tip), radius=TOE_R[0] * kk, r2=TOE_R[1] * kk))
            ps.append(Part(f'claw{s}{j}', 'tube', loc=tuple(tip), to=tuple(claw_tip(b, tip)), radius=CLAW[1] * kk, r2=0.0016))
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
    """The trunk, neck and head (no legs): what the wing feathers and the breast lobes lie on."""
    p = np.asarray(p, np.float64)
    d = np.full(p.shape[:-1], np.inf)
    for nm, (c, r, rot) in ELLS.items():
        if not head and nm in ('skull', 'face', 'chin', 'browL', 'browR'):
            continue
        d = np.minimum(d, sd_ell(p, c, r, rot))
    for i in range(len(NECK) - 1):
        d = np.minimum(d, sd_tube(p, NECK[i], NECK[i + 1], NECK_R[i], NECK_R[i + 1]))
    return d


def head_sd(p: np.ndarray) -> np.ndarray:
    d = np.full(np.asarray(p).shape[:-1], np.inf)
    for nm in ('skull', 'face', 'chin', 'nape', 'browL', 'browR'):
        c, r, rot = ELLS[nm]
        d = np.minimum(d, sd_ell(p, c, r, rot))
    return d


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


def outside_x(y: np.ndarray, z: np.ndarray, x0: float = 0.0, head: bool = False) -> np.ndarray:
    """The body's surface x (> 0) at each (y, z): bisection from the midline outward (0 where the line misses)."""
    y, z = np.asarray(y, np.float64), np.asarray(z, np.float64)
    lo, hi = np.full(y.shape, x0), np.full(y.shape, 0.45)
    miss = body_sd(np.stack([lo, y, z], axis=-1), head) > 0.0
    for _ in range(36):
        mid = 0.5 * (lo + hi)
        inside = body_sd(np.stack([mid, y, z], axis=-1), head) < 0.0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    return np.where(miss, 0.0, 0.5 * (lo + hi))


# ----------------------------------------------------------------------------- the breast's shaggy lobes
def lobe_specs() -> list[dict]:
    """(round 2) Soft, broad, rounded white feathers shingled over the breast and the belly, lying flat with only their
    tips lifted (1-hero: the breast's layered white feathers), and longer ones round each leg's top hanging down over
    the drumstick (the heron's feathered 'trousers': no bald thigh). The round 1 spiky tufts read as a thistle with dark
    crescents under them, and the throat's tufts as zig-zag collars."""
    rng = np.random.default_rng(11)
    out = []
    o = np.array((0.0, -0.1, 0.86))
    rows = [(38.0, 7, 0.095, 0.066), (24.0, 8, 0.1, 0.068), (10.0, 9, 0.1, 0.07), (-4.0, 9, 0.105, 0.07),
            (-18.0, 10, 0.11, 0.07), (-32.0, 10, 0.115, 0.07), (-46.0, 9, 0.12, 0.068), (-60.0, 8, 0.125, 0.066)]
    for r, (el, n, L, W) in enumerate(rows):
        span = 70.0 + 2.0 * r
        for az in np.linspace(-span, span, n) + (5.0 if r % 2 else -5.0):
            a, e = math.radians(az + rng.uniform(-3, 3)), math.radians(el + rng.uniform(-2, 2))
            d = np.array((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
            root = surface_hit(body_sd, o, d[None])[0]
            if abs(root[0]) > 0.12 and root[2] > 0.72:
                continue                     # under the folded wing
            n_ = sd_normal(body_sd, root[None])[0]
            g = np.array((0.0, 0.2, -1.0))
            down = unit(g - n_ * float(np.dot(g, n_)))
            k = 1.0 + 0.1 * rng.uniform(-1, 1)
            out.append({'root': root, 'n': n_, 'd': down, 'L': L * k, 'W': W * k, 'T': 0.013, 'lift': 0.005 + 0.003 * (r / 7),
                        'bury': 0.01})
    for xg in (-0.1, -0.05, 0.0, 0.05, 0.1):          # (build 8) the underside behind the legs (bare in hit_heavy)
        for yg in (0.09, 0.17, 0.25):
            p0 = np.array((xg + 0.01 * rng.uniform(-1, 1), yg, 0.82 - 0.4 * (yg - 0.05)))
            root = surface_hit(body_sd, p0, np.array([[0.0, 0.12, -1.0]]) / np.linalg.norm((0.0, 0.12, -1.0)), 0.4)[0]
            n_ = sd_normal(body_sd, root[None])[0]
            g = np.array((0.0, 0.55, -1.0))
            out.append({'root': root, 'n': n_, 'd': unit(g - n_ * float(np.dot(g, n_))), 'L': 0.12, 'W': 0.068, 'T': 0.013,
                        'lift': 0.006, 'bury': 0.01})
    for s in (1, -1):                           # the trousers: round each leg's top, hanging down over the drumstick
        c = np.array((0.075 * s, -0.02, 0.8))
        for j, ang in enumerate(np.linspace(0.0, 360.0, 8, endpoint=False) + 22.5):
            a = math.radians(ang)
            d = unit(np.array((0.55 * math.cos(a), 0.55 * math.sin(a), -1.0)))
            root = surface_hit(body_sd, c, d[None])[0]
            n_ = sd_normal(body_sd, root[None])[0]
            out_ = unit(np.array((math.cos(a), math.sin(a), 0.0)))
            down = unit(np.array((0.0, 0.0, -1.0)) + out_ * 0.18)
            out.append({'root': root, 'n': unit(out_ + n_), 'd': down, 'L': 0.13 + 0.015 * rng.uniform(-1, 1), 'W': 0.06, 'T': 0.013,
                        'lift': 0.01, 'bury': 0.012})
    return out


def lobe_object(name: str, f: dict, seg: int = 14) -> bpy.types.Object:
    """A broad feather with a rounded tip: root buried, lying along the surface, the tip lifted a little."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2 + 2, radius=1.0)
    X, Y, Z = basis(f['d'], f['n'])
    L, W, T = f['L'], f['W'], f['T']
    for v in bm.verts:
        t = (v.co.y + 1.0) * 0.5                         # 0 root ... 1 tip
        w = (1.0 - t ** 2.6) ** 0.5 * (0.7 + 0.3 * math.sin(math.pi * min(1.0, t * 1.6)))
        th = T * (1.0 - 0.5 * t)
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
# (round 2) an almond lens (wider than tall), flatter and sunk into the head: the round 1 bulging spheres read as goggles
EYE_AX = (1.12, 0.86)                       # the lens's across and up radii, in EYE_R (polish: rounder; its pointed ends clipped the iris)
EYE_DEPTH = 0.55                            # the lens flattened along its look
EYE_PROUD = 0.26                            # how far it stands out of the skin, in radii


def eye_frame(s: int):
    """(centre, across, up, look) of one lens: its centre set back from the skin along the look so the lens stands
    EYE_PROUD radii proud of it."""
    c0 = Vector(mirror(EYE_C, s))
    look = Vector(mirror(EYE_LOOK, s)).normalized()
    up = Vector((0.0, 0.0, 1.0))
    yax = (up - look * up.dot(look)).normalized()
    xax = yax.cross(look).normalized()
    hit = surface_hit(head_sd, np.array(c0) - np.array(look) * 0.03, np.array(look)[None], 0.08)[0]
    c = Vector(tuple(hit)) - look * (EYE_R * (EYE_DEPTH - EYE_PROUD))
    return c, xax, yax, look


def leg_points(s: int) -> list[np.ndarray]:
    return [np.array(mirror(LEG[k], s)) for k in ('hip', 'knee', 'ankle', 'toe', 'toe_tip')]
