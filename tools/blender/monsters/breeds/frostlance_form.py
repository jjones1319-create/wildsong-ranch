"""Frostlance's shape (frostlance_ultra.py): the plump whale body as one smooth implicit surface, the face's places, the
tusk's, the fins' and the fluke's frames, the rig's chains, and the zones.

Measured on chatgpt/monsters/18-frostlance/2-turnaround.png (1774 x 887), side view: the ground line y 637, the back's
top y 272 (0.887 m, the size rule for HEIGHT_UNITS 135: 1 px = 2.43 mm); the snout's tip x 473, the fluke's end x 960
(1.18 m snout to tail: the length follows the pictures, the owner's size decision of Nov 12); the body's deepest point
0.26-0.36 m behind the snout; the tail stalk narrowest (6.8 cm) 0.92 m behind it, its centre line dropping from 0.60 to
0.45 m; the tusk leaving the forehead 6.6 cm behind the snout at 0.79 m and rising 25 degrees (the hero about 40; 33 here),
0.36-0.42 m long; the eyes at +-0.135 m (front view), their centres at 0.69 m, about 9 cm tall; the pectoral fins leaving
the lower flanks 0.31 m behind the snout at 0.5 m and reaching out, back and down about 0.3 m; the fluke 0.47 m across.
Where the views disagree (the front view's body is taller, its fluke hangs below the belly) the hero decides: a plump,
round body with a low belly, the fluke drooping a little so it shows under the body from the front and the back.

The body is a smooth union of four ellipsoids (the body, the round head, the little snout bump, the rear) and a
tapering tail stalk. all_parts() gives the same primitives to the voxel builder; carve() then snaps every vertex onto
the exact smooth surface (field / snap), so the eye lenses laid on it sit flush and the paint reads the true shape.

Metres; the monster faces -Y, Z is up, +X is its left. Pure numpy / mathutils (no scene access).
"""
from __future__ import annotations

import math

import numpy as np
from mathutils import Matrix, Vector

from lib.mesh import Part
from lib.surface import smooth, v3

PX = 0.00243                        # metres per turnaround pixel (side view)

# ----------------------------------------------------------------------------- the body: a smooth union
# (name, centre, radii); the fins' fleshy roots (rotated, along each fin) are added at the end of the module (_ROOTS)
ELLS = [
    ('head', (0.0, -0.17, 0.64), (0.19, 0.25, 0.237)),         # round 3: 16% narrower (the front view is an egg, not a ball)
    # round 1: a rounded muzzle under the tusk's root, the smile curling under it (1-hero), so the profile isn't an egg
    ('muzzle', (0.0, -0.37, 0.612), (0.078, 0.072, 0.062)),     # polish: proud enough to read in profile
]
# the body, the rear and the tail stalk: one sweep along y, its centre line, half height and width (against the half
# height) through these keys (y, z, half height, width), from the measured top and belly lines (2-turnaround side: the
# hump 0.887 m high 0.26 m behind the snout, the belly low and flat at about 0.3 m, the back sloping to the stalk, which
# rises a little toward the fluke as the hero carries it); smooth (a Catmull-Rom curve through the keys), closing to a
# rounded point inside the fluke's root. The round head makes the face and the hump's front (the sweep's top stays a
# little under it there, so the union never bulges along the back), and the snout bump.
SWEEP = [(-0.3, 0.6, 0.12, 0.74), (-0.2, 0.6, 0.235, 0.71), (-0.1, 0.585, 0.272, 0.67), (-0.05, 0.585, 0.285, 0.66),
         (0.05, 0.573, 0.273, 0.68), (0.14, 0.565, 0.225, 0.71), (0.24, 0.55, 0.165, 0.78), (0.34, 0.525, 0.11, 0.88),
         (0.39, 0.512, 0.0875, 0.92), (0.46, 0.515, 0.054, 0.94), (0.51, 0.534, 0.036, 1.15), (0.54, 0.549, 0.031, 1.4),
         (0.56, 0.559, 0.022, 1.6), (0.572, 0.565, 0.014, 1.7), (0.582, 0.57, 0.0, 1.7)]
# polish: the end closes inside the fluke's thickened root, on its plane (it hung below the notch as a teal stub)
# round 3: the end stays 4-5 cm thick until it closes inside the fluke's root (a thinner wedge baked colour from its far
# side: white speckles stretched into streaks under the tail)
# round 3: the body 15-18% narrower side to side (2-turnaround front: about 1.4x taller than wide; it read as a puffer
# ball at 1.15x), and its lower rear tapering into the stalk sooner (the belly line rises from 0.14 back), height and
# length unchanged
# round 1: the stalk's end flattens sideways into the fluke's root (wider than the fluke's neck, as thick as its slab), so
# the fluke grows out of it instead of a square-ended bar poking out of a round stalk
BLEND = 0.03                        # the smooth union's blending distance (metres)
ROOT_BLEND = 0.045                  # the fins' roots melt into the flank softly (a tight crease baked dark specks and a bright sliver)
SNOUT_Y = -0.432                    # the muzzle's front
STALK = [((0.0, 0.53, 0.54), 0.03)]     # the stalk's end (the fluke's root)


def _catmull(keys: np.ndarray, n: int = 400) -> np.ndarray:
    """A dense Catmull-Rom curve through the keys (rows), for np.interp."""
    k = np.vstack([2 * keys[0] - keys[1], keys, 2 * keys[-1] - keys[-2]])
    out = []
    for i in range(1, len(k) - 2):
        p0, p1, p2, p3 = k[i - 1], k[i], k[i + 1], k[i + 2]
        for t in np.linspace(0, 1, n // (len(keys) - 1), endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(keys[-1])
    return np.array(out)


_SW = _catmull(np.array(SWEEP))


def _ell(p: np.ndarray, c, r, axes=None) -> np.ndarray:
    """An ellipsoid's approximate signed distance (good near its surface); `axes` (3 unit rows) turns it."""
    q = (p - v3(c)) if axes is None else (p - v3(c)) @ np.asarray(axes, np.float64).T
    q = q / v3(r)
    k0 = np.linalg.norm(q, axis=1)
    k1 = np.linalg.norm(q / v3(r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def _sweep(p: np.ndarray) -> np.ndarray:
    """The rear's and the stalk's approximate signed distance: elliptic sections along y."""
    y0, y1 = float(_SW[0, 0]), float(_SW[-1, 0])
    y = np.clip(p[:, 1], y0, y1)
    zc = np.interp(y, _SW[:, 0], _SW[:, 1])
    b = np.maximum(np.interp(y, _SW[:, 0], _SW[:, 2]), 1e-4)
    a = b * np.interp(y, _SW[:, 0], _SW[:, 3])
    q = np.sqrt((p[:, 0] / a) ** 2 + ((p[:, 2] - zc) / b) ** 2)
    d = (q - 1.0) * np.minimum(a, b)
    return d + np.maximum(0.0, p[:, 1] - y1) + np.maximum(0.0, y0 - p[:, 1])


_ROOTS: list = []                   # the fins' fleshy roots (filled at the end of the module, from fin_axes)


def field(p: np.ndarray, roots: bool = True) -> np.ndarray:
    """The body's signed distance (negative inside): the primitives' smooth (exponential) union."""
    p = np.asarray(p, np.float64).reshape(-1, 3)
    fs = np.stack([_ell(p, c, r) for _n, c, r in ELLS] + [_sweep(p)], axis=1)
    m = fs.min(axis=1)
    body = m - BLEND * np.log(np.exp(-(fs - m[:, None]) / BLEND).sum(axis=1))
    if not (roots and _ROOTS):
        return body
    fs = np.stack([body] + [_ell(p, c, r, ax) for c, r, ax in _ROOTS], axis=1)
    m = fs.min(axis=1)
    return m - ROOT_BLEND * np.log(np.exp(-(fs - m[:, None]) / ROOT_BLEND).sum(axis=1))


def gradient(p: np.ndarray, h: float = 2e-4) -> np.ndarray:
    p = np.asarray(p, np.float64).reshape(-1, 3)
    g = np.zeros_like(p)
    for i in range(3):
        e = np.zeros(3)
        e[i] = h
        g[:, i] = (field(p + e) - field(p - e)) / (2 * h)
    return g


def normal_of(p: np.ndarray) -> np.ndarray:
    g = gradient(p)
    return g / np.maximum(np.linalg.norm(g, axis=1), 1e-12)[:, None]


def snap(p: np.ndarray, iters: int = 6) -> np.ndarray:
    """Points moved onto the surface (Newton steps along the gradient)."""
    q = np.asarray(p, np.float64).reshape(-1, 3).copy()
    for _ in range(iters):
        g = gradient(q)
        q = q - (field(q) / np.maximum((g * g).sum(axis=1), 1e-12))[:, None] * g
    return q


def ray_hit(origin, direction, far: float = 1.5, roots: bool = True) -> Vector:
    """The first surface point along a ray from outside (bisection)."""
    o, d = v3(origin), v3(direction) / np.linalg.norm(v3(direction))
    ts = np.linspace(0.0, far, 600)
    f = field(o[None] + ts[:, None] * d[None], roots)
    i = int(np.argmax(f < 0))
    lo, hi = ts[max(i - 1, 0)], ts[i]
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if field((o + mid * d)[None], roots)[0] > 0:
            lo = mid
        else:
            hi = mid
    return Vector((o + hi * d).tolist())


def front_point(x: float, z: float) -> Vector:
    """The body's surface at (x, z) seen from the front."""
    return ray_hit((x, -0.8, z), (0.0, 1.0, 0.0))


def side_point(y: float, z: float, s: int = 1) -> Vector:
    """The flank's surface at (y, z) seen from the side `s` (+1 its left)."""
    return ray_hit((0.6 * s, y, z), (-s, 0.0, 0.0), roots=False)


def all_parts() -> list[Part]:
    """The voxel builder's rough body (carve snaps it onto the exact surface): the ellipsoids and the sweep as tapering
    tubes between its keys."""
    ps = [Part(n, 'sphere', loc=c, radius=1.0, scale=r) for n, c, r in ELLS]
    # polish: the sweep as overlapping ellipsoids every 2 cm (its true elliptic sections). Round tubes the width of the
    # narrowed body fell about 9 cm short of the belly, and snapping that far folded the skin round the fins' roots
    for i, y in enumerate(np.arange(float(_SW[0, 0]), float(_SW[-1, 0]), 0.02)):
        zc, b, w = (float(np.interp(y, _SW[:, 0], _SW[:, k])) for k in (1, 2, 3))
        if b > 0.006:
            ps.append(Part(f'sweep{i}', 'sphere', loc=(0.0, float(y), zc), radius=1.0, scale=(b * w * 0.98, 0.03, b * 0.98)))
    for i, (c, r, ax) in enumerate(_ROOTS):
        m = Matrix([ax[0], ax[1], ax[2]]).transposed()
        ps.append(Part(f'finroot{i}', 'sphere', loc=tuple(c), radius=1.0, scale=tuple(r), rot=tuple(math.degrees(a) for a in m.to_euler('XYZ'))))
    return ps


# ----------------------------------------------------------------------------- the face
EYE_X, EYE_Z = 0.128, 0.666
EYE_R = 0.0625                      # the eye's half width (round 1: 1.25x, about 19% of the head's width, 3-faces)
EYE_SHAPE = (1.0, 1.06)             # a little taller than wide (3-faces, 4-details 2)
EYE_DOME, EYE_SINK = 0.013, 0.0006
MOUTH_Z, MOUTH_W = 0.571, 0.056     # the closed smile curling under the muzzle (polish: its corners reach round to show in profile)


def eye_centre(s: int) -> Vector:
    return front_point(EYE_X * s, EYE_Z)


EYE_C = {s: eye_centre(s) for s in (1, -1)}


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye: the look follows the head's curve, a little toward the front."""
    c = EYE_C[s]
    n = Vector(normal_of(np.array([c[:]]))[0].tolist())
    look = (n * 0.72 + Vector((0, -1, 0)) * 0.28).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_dist(p: np.ndarray) -> np.ndarray:
    return np.minimum(np.linalg.norm(p - v3(EYE_C[1][:]), axis=1), np.linalg.norm(p - v3(EYE_C[-1][:]), axis=1))


def eye_local(p: np.ndarray, s: int) -> np.ndarray:
    """(x, y) in the eye's frame, in eye radii (x toward the monster's left... its own right axis)."""
    c, xa, ya, _lk = eye_frame(s)
    d = p - v3(c[:])
    return np.stack([d @ v3(xa[:]) / (EYE_R * EYE_SHAPE[0]), d @ v3(ya[:]) / (EYE_R * EYE_SHAPE[1])], axis=1)


MOUTH_C = front_point(0.0, MOUTH_Z)


# ----------------------------------------------------------------------------- the tusk (a prop on the head)
TUSK_LEN = 0.42
TUSK_PITCH = 33.0                   # degrees above level
TUSK_R = (0.047, 0.0022)            # radius at the skin, at the point (round 3: a sharper point)
TUSK_TURNS = 7.5                    # the spiral ridges crossing any line along it (4-details 5)
TUSK_STARTS = 3                     # grooves twisted together (round 1)
TUSK_BURY = 0.035                   # how far its root sinks into the forehead
TUSK_DIR = Vector((0.0, -math.cos(math.radians(TUSK_PITCH)), math.sin(math.radians(TUSK_PITCH))))
TUSK_BASE = front_point(0.0, 0.77)  # where it leaves the forehead, between the eyes and above them (the hero: so the far eye
                                    # shows beside it in the three-quarter view)
TUSK_ROOT = TUSK_BASE - TUSK_DIR * TUSK_BURY
TUSK_TIP = TUSK_BASE + TUSK_DIR * TUSK_LEN


# ----------------------------------------------------------------------------- the pectoral fins (props on their chains)
FIN_ROOT_YZ = (-0.07, 0.49)
FIN_AXIS = Vector((0.72, 0.5, -0.48)).normalized()        # the left fin: out, back and down (round 1: spread wider, so
                                                            # the far fin's tip no longer pokes out under the chin)
FIN_FACE = Vector((0.5, -0.7, 0.5))                         # its broad face looks out, forward and up (the front and 3/4 views)
FIN_LEN = 0.42                      # round 1: 25% bigger (2-turnaround front: they reach out 0.6 of the head's width)
FIN_K = 1.4                         # the outline's scale (frostlance_props.FIN_BASE is drawn for 0.3 m)
FIN_BURY = 0.05


def fin_axes(s: int):
    """Origin (on the flank), u (out along the fin), v (across: toward the leading edge) and the face's normal."""
    o = side_point(FIN_ROOT_YZ[0], FIN_ROOT_YZ[1], s)
    a = Vector((FIN_AXIS.x * s, FIN_AXIS.y, FIN_AXIS.z))
    f = Vector((FIN_FACE.x * s, FIN_FACE.y, FIN_FACE.z))
    n = (f - a * f.dot(a)).normalized()
    v = n.cross(a).normalized()
    if v.y > 0:                     # the leading edge faces forward
        v = -v
    return o, a, v, n


def fin_bone_points(s: int) -> list[tuple]:
    o, a, _v, _n = fin_axes(s)
    return [tuple(o - a * 0.03), tuple(o + a * 0.13), tuple(o + a * FIN_LEN)]


# ----------------------------------------------------------------------------- the tail and its fluke
FLUKE_O = Vector(STALK[0][0])       # the fluke's root: the stalk's end
FLUKE_PITCH = -30.0                 # degrees its back edge droops below the stalk's line (negative: it rises, as the hero
                                    # carries it; level or drooping, it was edge-on to the raised three-quarter camera)
FLUKE_DROOP = -0.5                  # the lobes' tips droop (metres per metre squared across; negative: they curve up
                                    # into a V, as in the hero and the poses: about 4 cm at the tips)
FLUKE_K = 1.0                       # round 3: the lobes are drawn at size (0.5 m across, about 1.2x the body's width)


def fluke_axes():
    """Origin, u (across: +X), v (back along the tail, drooping) and the face's normal (up)."""
    p = math.radians(FLUKE_PITCH)
    u = Vector((1.0, 0.0, 0.0))
    v = Vector((0.0, math.cos(p), -math.sin(p)))
    n = u.cross(v).normalized()
    if n.z < 0:
        n = -n
    return FLUKE_O.copy(), u, v, n


def _tail_pts() -> list[tuple]:
    o, _u, v, _n = fluke_axes()
    return [(0.0, 0.22, 0.535), (0.0, 0.4, 0.508), tuple(o), tuple(o + v * 0.2)]


TAIL_PTS = _tail_pts()              # tail.1, tail.2 down the stalk, tail.3 the fluke


# ----------------------------------------------------------------------------- the rig's frame
HIP = (0.0, -0.06, 0.6)
CHEST = (0.0, -0.41, 0.635)         # the squash chain's top: the snout (a swimmer)
BASE = (0.0, 0.22, 0.54)            # its rear
HEAD_C = (0.0, -0.24, 0.65)
HEAD_R = 0.22


def squash_points() -> list[np.ndarray]:
    b, t = v3(BASE), v3(CHEST)
    return [b, b + (t - b) / 3, b + 2 * (t - b) / 3, t]


# ----------------------------------------------------------------------------- zones
def face_k(p: np.ndarray) -> np.ndarray:
    """0..1: the face (the front of the head round the eyes, the smile and the brows)."""
    p = np.asarray(p, np.float64)
    return smooth(-0.17, -0.25, p[:, 1]) * smooth(0.5, 0.56, p[:, 2]) * smooth(0.84, 0.8, p[:, 2]) * smooth(0.24, 0.2, np.abs(p[:, 0]))


def zones(p: np.ndarray, n=None) -> dict:
    p = np.asarray(p, np.float64)
    return {'face': face_k(p) > 0.5, 'eye_d': eye_dist(p), 'muzzle': np.linalg.norm(p - v3(MOUTH_C[:]), axis=1) < 0.08}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    # polish: the creases round the fins' roots keep their triangles, so the low body follows them and the baked normals
    # don't swing (a glossy sliver under each root, dark specks over it)
    root = np.zeros(len(co))
    for s in (1, -1):
        root = np.maximum(root, smooth(0.14, 0.09, np.linalg.norm(co - v3(fin_axes(s)[0][:]), axis=1)))
    return np.clip(0.75 * face_k(co) + (z['eye_d'] < 0.07) * 1.0 + 0.6 * z['muzzle'] + 0.9 * root, 0, 1)


# ----------------------------------------------------------------------------- the fins' fleshy roots (round 1)
def _fin_roots() -> list:
    """Each fin grows out of a rounded, fleshy root (4-details 3): an ellipsoid along the fin from the flank, as wide as
    the fin's root and a little thicker, tapering into it (the fin's slab sinks into it: no cut edge on the skin)."""
    out = []
    for s in (1, -1):
        o, a, v, n = fin_axes(s)
        ax = [a, v, n] if a.cross(v).dot(n) > 0 else [a, v, -n]
        # polish: about half the bulk (they stood out as pointed shoulders), still enclosing the fin's narrow root
        out.append((tuple(o + a * 0.0), (0.088, 0.04, 0.022), [tuple(x) for x in ax]))
    return out


_ROOTS.extend(_fin_roots())
