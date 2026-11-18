"""Lootlid's shells (Art 2.1 Ultra; chatgpt/monsters/30-lootlid): the box, the lid and the four legs, each one closed
loft of rounded-rectangle rings (lootlid_geo.loft), voxel-united into the body by the build (body_extras), plus the
face parts on the lid: the eyes' wooden sockets, the closed eyelids under the lenses and the carved brows.

Proportions from 2-turnaround (front, side, back; the hero for the shapes), at 135 units = 0.89 m to the lid's ridge:
  - the box: 0.69 m wide and 0.58 m deep at its rim, tapering a little to a rounded, bellied bottom 0.165 m up; its
    faces bulge gently; a hollow inside (3.5 cm walls, the floor 7 cm under the rim) holds the coin hoard;
  - the lid (the mouth): 0.71 × 0.60 m, a barrel top (an elliptical arch from 0.665 m to the ridge at 0.89 m), the
    front-view corners rounded; a 2 cm gap from the box (the jaw lesson: separate shells, so the weights split hard at
    the hinge) and a 6 cm recess underneath, so an open mouth shows a hollow lid;
  - four stubby wooden posts on flat feet, splayed a little outward, about 0.07 m in radius.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import lootlid_geo as G

# ----------------------------------------------------------------------------- dimensions
Z_BOT = 0.165              # the box's flat bottom
Z_BTOP = 0.472             # the box's rim top
Z_LB = 0.495               # the lid's bottom edge (2.3 cm over the rim: the gap; round 3: a gold lip under it)
Z_TOP = 0.89               # the lid's ridge
Z_SEAM = 0.5 * (Z_BTOP + Z_LB)
BOX_A, BOX_B = 0.345, 0.29
BOX_TAPER = 0.032
BOX_FILLET = 0.088          # round 3: curving under at the bottom
BOX_N, BOX_BULGE = 5.0, 0.06
BOX_BARREL = 0.016          # round 3: the walls bellied like a barrel (the most at mid-height)
WALL, FLOOR_Z, FLOOR_R, RIM_R = 0.035, 0.40, 0.02, 0.008
LID_A, LID_B = 0.355, 0.30
LID_N, LID_BULGE = 5.0, 0.022
LID_SPRING = 0.665
LID_RZ = Z_TOP - LID_SPRING
LID_RC = 0.07              # the front view's rounded top corners
LID_WALL, LID_RECESS, LID_CEIL_R, LID_EDGE_R = 0.035, 0.06, 0.015, 0.008
LID_FRONT_EXTRA = 0.026    # round 3: the lid is a hollow shell; its front wall thicker (the eyes sit in it)
# the legs: bottom centre, top centre (a little inward), the post's radius at the foot and up the post
# polish pass: the post runs on up to 0.25 (on the same line) so its top stays 4-8 cm inside the box (the outer side
# only enters the box's rounded bottom at about 0.205): a turned post never shows its cut top
LEG_TOP_Z = 0.25
LEGS = {(s, f): {'bot': (0.247 * s, -0.172 * f, 0.0),
                 'top': (s * (0.247 - 0.021 * LEG_TOP_Z / 0.215), -f * (0.172 - 0.007 * LEG_TOP_Z / 0.215), LEG_TOP_Z)}
        for s in (1, -1) for f in (1, -1)}
LEG_R = ((0.0, 0.08), (0.03, 0.077), (0.07, 0.072), (0.14, 0.07), (0.215, 0.069))
LEG_EDGE = 0.022                # round 2: a rounder foot (a rigid post rocks on it as it tilts)
# the face: the eyes' centres on the lid's front, the socket rims, the closed lids, the brows
EYE_X, EYE_Z = 0.148, 0.652
EYE_R = 0.074
RIM_RADIUS = 0.077
BROW = {'x': 0.155, 'z': 0.778, 'half': 0.056, 'arch': 0.022, 'r': 0.0095}


def lerp_tab(tab, z: float) -> float:
    zs, vs = zip(*tab)
    return float(np.interp(z, zs, vs))


# ----------------------------------------------------------------------------- the box
def box_ab(z: float) -> tuple[float, float]:
    """The box's outer semi-axes at height z: a straight taper, the rounded bottom under it."""
    u = min(1.0, max(0.0, (Z_BTOP - z) / (Z_BTOP - Z_BOT)))
    taper = BOX_TAPER * u - BOX_BARREL * math.sin(math.pi * u)
    a, b = BOX_A - taper, BOX_B - 0.85 * taper
    zf = Z_BOT + BOX_FILLET
    if z < zf:
        dz = zf - z
        ins = BOX_FILLET - math.sqrt(max(0.0, BOX_FILLET ** 2 - dz * dz))
        a, b = a - ins, b - ins
    return a, b


def _arc(n: int, a0: float = 0.0, a1: float = 90.0, first: bool = False) -> np.ndarray:
    ang = np.radians(np.linspace(a0, a1, n + 1))
    return ang if first else ang[1:]


def box_rows(step: float = 0.006) -> list:
    rows = [(Z_BOT, 0.0, 0.0, 0.0, 0.0)]
    a0, b0 = box_ab(Z_BOT)
    for k in np.linspace(0.06, 1.0, 14):
        rows.append((Z_BOT, k * a0, k * b0, 0.0, 0.0))
    zf = Z_BOT + BOX_FILLET
    for ph in _arc(18):
        z = zf - BOX_FILLET * math.cos(ph)
        a, b = box_ab(z)
        rows.append((z, a, b, 0.0, 0.0))
    z_hi = Z_BTOP - RIM_R
    for z in np.linspace(zf, z_hi, max(2, int((z_hi - zf) / step)) + 1)[1:]:
        a, b = box_ab(z)
        rows.append((z, a, b, 0.0, 0.0))
    for ph in _arc(6):
        z = z_hi + RIM_R * math.sin(ph)
        ins = RIM_R * (1 - math.cos(ph))
        a, b = box_ab(z)
        rows.append((z, a - ins, b - ins, 0.0, 0.0))
    for ins in np.linspace(RIM_R, WALL - RIM_R, 5)[1:]:
        a, b = box_ab(Z_BTOP)
        rows.append((Z_BTOP, a - ins, b - ins, 0.0, 0.0))
    for ph in _arc(6):
        ins = WALL - RIM_R + RIM_R * math.sin(ph)
        z = z_hi + RIM_R * math.cos(ph)
        a, b = box_ab(z)
        rows.append((z, a - ins, b - ins, 0.0, 0.0))
    z_lo = FLOOR_Z + FLOOR_R
    for z in np.linspace(z_hi, z_lo, max(2, int((z_hi - z_lo) / step)) + 1)[1:]:
        a, b = box_ab(z)
        rows.append((z, a - WALL, b - WALL, 0.0, 0.0))
    for ph in _arc(6):
        z = z_lo - FLOOR_R * math.sin(ph)
        ins = WALL + FLOOR_R * (1 - math.cos(ph))
        a, b = box_ab(z)
        rows.append((z, a - ins, b - ins, 0.0, 0.0))
    a, b = box_ab(FLOOR_Z)
    af, bf = a - WALL - FLOOR_R, b - WALL - FLOOR_R
    for k in np.linspace(1.0, 0.06, 12)[1:]:
        rows.append((FLOOR_Z, k * af, k * bf, 0.0, 0.0))
    rows.append((FLOOR_Z, 0.0, 0.0, 0.0, 0.0))
    return rows


# ----------------------------------------------------------------------------- the lid
def lid_ab(z: float) -> tuple[float, float]:
    """The lid's outer semi-axes at height z: straight up to the spring, then the barrel arch; the front view's top
    corners rounded."""
    a, b = LID_A, LID_B
    if z > LID_SPRING:
        t = min(1.0, (z - LID_SPRING) / LID_RZ)
        b = LID_B * math.sqrt(max(0.0, 1.0 - t * t))
    zc = Z_TOP - LID_RC
    if z > zc:
        dz = z - zc
        a -= LID_RC - math.sqrt(max(0.0, LID_RC ** 2 - dz * dz))
    return a, b


def lid_inner(z: float) -> tuple[float, float, float]:
    """The lid's hollow at height z (round 3: a real shell): semi-axes and the centre's y (the front wall is thicker)."""
    cy = 0.5 * LID_FRONT_EXTRA
    a, _b = lid_ab(z)
    b0 = LID_B - LID_WALL - cy
    t = min(1.0, max(0.0, (z - LID_SPRING) / (LID_RZ - LID_WALL)))
    return a - LID_WALL, b0 * math.sqrt(max(0.0, 1.0 - t * t)), cy


def lid_rows(step: float = 0.006) -> list:
    W, R = LID_WALL, LID_EDGE_R
    cy = 0.5 * LID_FRONT_EXTRA
    b0 = LID_B - W - cy
    z_ti = LID_SPRING + LID_RZ - W
    rows = [(z_ti, 0.0, 0.0, 0.0, cy)]
    for al in np.radians(np.linspace(89.5, 0.0, 70)):
        z = LID_SPRING + (LID_RZ - W) * math.sin(al)
        a, _b = lid_ab(z)
        rows.append((z, a - W, b0 * math.cos(al), 0.0, cy))
    z_lo = Z_LB + R
    for z in np.linspace(LID_SPRING, z_lo, max(2, int((LID_SPRING - z_lo) / step)) + 1)[1:]:
        a, _b = lid_ab(z)
        rows.append((z, a - W, b0, 0.0, cy))

    def ring(z: float, f: float):
        # f: 1 on the inner wall, 0 on the outer surface
        a, b = lid_ab(z)
        return (z, a - W * f, b - (W + cy) * f, 0.0, cy * f)
    for ph in _arc(5):
        rows.append(ring(z_lo - R * math.sin(ph), 1.0 - (R / W) * (1 - math.cos(ph))))
    for f in np.linspace(1.0 - R / W, R / W, 4)[1:-1]:
        rows.append(ring(Z_LB, float(f)))
    for ph in _arc(5, first=True):
        rows.append(ring(z_lo - R * math.cos(ph), (R / W) * (1 - math.sin(ph))))
    for z in np.linspace(z_lo, LID_SPRING, max(2, int((LID_SPRING - z_lo) / step)) + 1)[1:]:
        a, b = lid_ab(z)
        rows.append((z, a, b, 0.0, 0.0))
    # the arch, by its angle (even spacing over the curve)
    for al in np.radians(np.linspace(0.0, 89.0, 64)[1:]):
        z = LID_SPRING + LID_RZ * math.sin(al)
        a, _b = lid_ab(z)
        rows.append((z, a, LID_B * math.cos(al), 0.0, 0.0))
    rows.append((Z_TOP, 0.0, 0.0, 0.0, 0.0))
    return rows


# ----------------------------------------------------------------------------- the legs
def leg_axis(key, z: float) -> np.ndarray:
    lg = LEGS[key]
    b, t = np.array(lg['bot']), np.array(lg['top'])
    k = (z - b[2]) / (t[2] - b[2])
    return b + (t - b) * k


def post_r(z: float) -> float:
    """The post's radius at height z; polish pass: its hidden top (above 0.22, inside the box) narrows to 60%, so a
    post swung in a run keeps it inside."""
    t = min(1.0, max(0.0, (z - 0.22) / (LEG_TOP_Z - 0.22)))
    return lerp_tab(LEG_R, z) * (1.0 - 0.4 * t * t * (3 - 2 * t))


def leg_rows(key, step: float = 0.006, coarse: bool = False) -> list:
    rows = []
    z_top = LEGS[key]['top'][2]

    def at(z: float, ins: float = 0.0, k: float = 1.0):
        c = leg_axis(key, z)
        r = (post_r(z) - ins) * k
        return (z, r, r, float(c[0]), float(c[1]))
    c0 = leg_axis(key, 0.0)
    rows.append((0.0, 0.0, 0.0, float(c0[0]), float(c0[1])))
    for k in np.linspace(0.08, 1.0, 3 if coarse else 9):
        rows.append(at(0.0, LEG_EDGE, k))
    for ph in _arc(3 if coarse else 7):
        z = LEG_EDGE * (1 - math.cos(ph))
        rows.append(at(z, LEG_EDGE * (1 - math.sin(ph))))
    for z in np.linspace(LEG_EDGE, z_top, max(2, int((z_top - LEG_EDGE) / step)) + 1)[1:]:
        rows.append(at(float(z)))
    for k in np.linspace(1.0, 0.1, 3 if coarse else 6)[1:]:
        rows.append(at(z_top, 0.0, k))
    ct = leg_axis(key, z_top)
    rows.append((z_top, 0.0, 0.0, float(ct[0]), float(ct[1])))
    return rows


# ----------------------------------------------------------------------------- the lid's front surface
_FRONT: dict = {}


def _front_table():
    """The lid's front surface y(x, z) on a grid (the eyes, the brows and the keyhole plate sit on it)."""
    if _FRONT:
        return _FRONT
    cs = G.unit_ring(LID_N, 4096, LID_B / LID_A)
    zs = np.linspace(Z_LB + LID_EDGE_R, Z_TOP - 0.004, 240)
    xs = np.linspace(-0.3, 0.3, 241)
    Y = np.full((len(zs), len(xs)), np.nan)
    for i, z in enumerate(zs):
        a, b = lid_ab(float(z))
        x, y = G.ring_xy(cs, a, b, LID_BULGE)
        m = y < 0
        o = np.argsort(x[m])
        Y[i] = np.interp(xs, x[m][o], y[m][o], left=np.nan, right=np.nan)
    _FRONT.update({'z': zs, 'x': xs, 'y': Y})
    return _FRONT


def front_y(x, z) -> np.ndarray:
    """The lid's front surface (its y, negative) at (x, z), bilinear on the table."""
    T = _front_table()
    x, z = np.atleast_1d(np.asarray(x, np.float64)), np.atleast_1d(np.asarray(z, np.float64))
    fx = np.clip((x - T['x'][0]) / (T['x'][1] - T['x'][0]), 0, len(T['x']) - 1.001)
    fz = np.clip((z - T['z'][0]) / (T['z'][1] - T['z'][0]), 0, len(T['z']) - 1.001)
    i0, j0 = np.floor(fz).astype(int), np.floor(fx).astype(int)
    tz, tx = fz - i0, fx - j0
    Y = T['y']
    return ((Y[i0, j0] * (1 - tx) + Y[i0, j0 + 1] * tx) * (1 - tz) + (Y[i0 + 1, j0] * (1 - tx) + Y[i0 + 1, j0 + 1] * tx) * tz)


def front_point(x, z) -> np.ndarray:
    x, z = np.atleast_1d(np.asarray(x, np.float64)), np.atleast_1d(np.asarray(z, np.float64))
    return np.stack([x, front_y(x, z), z], axis=1)


def front_normal(x, z) -> np.ndarray:
    """The lid's front surface's outward normal at (x, z)."""
    x, z = np.atleast_1d(np.asarray(x, np.float64)), np.atleast_1d(np.asarray(z, np.float64))
    e = 0.004
    fx = (front_y(x + e, z) - front_y(x - e, z)) / (2 * e)
    fz = (front_y(x, z + e) - front_y(x, z - e)) / (2 * e)
    n = np.stack([fx, -np.ones_like(x), fz], axis=1)
    return n / np.linalg.norm(n, axis=1, keepdims=True)


# ----------------------------------------------------------------------------- the eyes' frames
EYE_TURN = 0.1             # the eyes look a little outward (x share of the look)


def eye_frame(s: int):
    """(centre on the lid's surface, x axis toward the eye's outer side for the left eye, up, look)."""
    c = front_point(EYE_X * s, EYE_Z)[0]
    n = front_normal(EYE_X * s, EYE_Z)[0]
    look = n + np.array([EYE_TURN * s, 0.0, 0.03])
    look /= np.linalg.norm(look)
    xax = np.cross(np.array([0.0, 0.0, 1.0]), look)
    xax /= np.linalg.norm(xax)
    yax = np.cross(look, xax)
    return c, xax, yax, look


def rim_piece(s: int, nu: int, nv: int) -> dict:
    """The eye's wooden socket rim: a ring on the lid's surface round the lens, thicker over the top (the wood overhangs
    the eye a little, as in 3-faces neutral)."""
    c, xax, yax, look = eye_frame(s)
    ph = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    q = c[None] + RIM_RADIUS * (np.cos(ph)[:, None] * xax + np.sin(ph)[:, None] * yax)
    top = np.clip(np.sin(ph), 0, 1)
    p = front_point(q[:, 0], q[:, 2])
    p = p - look[None] * 0.002 - yax[None] * (0.008 * top ** 2)[:, None] + look[None] * (0.004 * top ** 2)[:, None]
    rad = 0.0105 + 0.009 * top ** 1.5
    nrm = front_normal(q[:, 0], q[:, 2])
    t = np.roll(p, -1, axis=0) - np.roll(p, 1, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    n = nrm - t * np.einsum('ij,ij->i', nrm, t)[:, None]
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    b = np.cross(t, n)
    a = np.linspace(0, 2 * math.pi, nv, endpoint=False)
    rings = [p[i] + rad[i] * (np.cos(a)[:, None] * n[i] + np.sin(a)[:, None] * b[i]) for i in range(nu)]
    return G.sweep(rings, closed=True)


def lidball_piece(s: int, nu: int, nv: int) -> dict:
    """The closed eyelid under the lens: a low wooden dome a blink shows (the lens hides it when open)."""
    c, xax, yax, look = eye_frame(s)
    sph = G.uv_sphere((0, 0, 0), 1.0, nu, nv)
    v = sph['v']
    M = np.stack([xax * 0.064, yax * 0.06, look * 0.031])        # rows: local x, y, z → world
    sph['v'] = (c - look * 0.012)[None] + v @ M
    return G.outward(sph)


def brow_piece(s: int, n: int, nv: int) -> dict:
    """A carved brow over the eye: an arched ridge, thick in the middle, tapered at both ends."""
    u = np.linspace(-1.0, 1.0, n)
    x = (BROW['x'] + 0.004 * u) * s + BROW['half'] * u * s
    z = BROW['z'] + BROW['arch'] * (1 - u * u) - 0.006 * u
    p = front_point(x, z)
    nrm = front_normal(x, z)
    rad = BROW['r'] * (0.25 + 0.75 * np.sqrt(np.clip(1 - u * u, 0, 1)))
    p = p + nrm * (rad * 0.35)[:, None]
    t = np.gradient(p, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    nn = nrm - t * np.einsum('ij,ij->i', nrm, t)[:, None]
    nn /= np.linalg.norm(nn, axis=1, keepdims=True)
    b = np.cross(t, nn)
    a = np.linspace(0, 2 * math.pi, nv, endpoint=False)
    # a flattened section: wider along the surface than it stands out
    rings = [p[i] + rad[i] * (0.75 * np.cos(a)[:, None] * nn[i] + 1.5 * np.sin(a)[:, None] * b[i]) for i in range(n)]
    return G.sweep(rings, closed=False)


# ----------------------------------------------------------------------------- the pieces
def shells(fine: bool = True) -> dict[str, dict]:
    """Every closed piece of the body: 'box', 'lid', 'rim<s>', 'lidball<s>', 'brow<s>' (round 2: the legs are rigid
    props, lootlid_legs.py)."""
    step = 0.004 if fine else 0.008
    nu = 560 if fine else 280
    out = {'box': G.loft(box_rows(step), G.unit_ring(BOX_N, nu, BOX_B / BOX_A), BOX_BULGE),
           'lid': G.loft(lid_rows(step), G.unit_ring(LID_N, nu, LID_B / LID_A), LID_BULGE)}
    for s in (1, -1):
        out[f'rim{s}'] = rim_piece(s, 120 if fine else 64, 24 if fine else 12)
        out[f'lidball{s}'] = lidball_piece(s, 64 if fine else 32, 32 if fine else 16)
        out[f'brow{s}'] = brow_piece(s, 48 if fine else 24, 20 if fine else 10)
    return out


def objects(fine: bool = True) -> list:
    return [G.make_object(f'lootlid_{k}', pc, smooth=False) for k, pc in shells(fine).items()]
