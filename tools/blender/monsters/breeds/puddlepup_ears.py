"""Puddlepup Ultra ears (docs/ART_2_DETAIL.md §9.2): each ear is one hanging fur flap with the coral membrane as its
lining. P1.1's fur cap over a separate fan read as a blade, or gills, at the cheek.

The flap is a surface F(s, u, v) on side s (+1 = the monster's left): u runs from the root on top of the head (0) to
the scalloped bottom edge (1), v from the front edge (0) to the back edge (1). Its outward normal looks out and a little
back, so the lining's hollow faces in and forward (the pictures: teal fur outside, pink inside, flaring into a fan).
  - `slab()`: the fur, a slab on the outside of F down to `u_fur(v)`, joined into the voxel body so the coat grows on it;
  - `lining_point()`: the membrane just inside F, from under the head's curve to the bottom edge; its sides tuck into
    the fur where there is fur, and past the fur it carries on into the ribbed, scalloped fan;
  - `lookup()`: for any points, the nearest (u, v), how far out from F they are and the slab's thickness there (the
    coat's zones, the fur's flow down the flap, the lining side, the skin weights).
Metres; the monster faces −Y, Z is up. `configure()` takes the head's shape from the recipe.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib.surface import smooth

ROOT_Y = (-0.425, -0.305)      # the root line on top of the head, front → back
ROOT_Z = (0.916, 0.93)
LEN = (0.33, 0.36)             # front edge, back edge
ROUND = 0.075                  # the bottom edge is a rounded fan: its middle hangs this much lower
WIDTH = (0.09, 0.27)           # across the flap: at the root, at the bottom edge (it widens in its lower half)
# the flap twists as it falls, so its fan opens forward and the lining shows from the front and in three-quarter
# view (at 35° the near ear's lining was edge-on to the 3/4 camera: a blade)
TURN = math.radians(48)
OUT = (0.02, 0.08)             # the centre line swings out: x += OUT[0]·u + OUT[1]·u²
CUP = 0.026                    # the middle of the flap bulges out: the lining is the hollow
CLEAR = (-0.018, 0.034)        # clearance from the head: sunk in at the root, this much from u = 0.4 down (a lobe, not a cheek)
U_FUR = (0.64, 0.8)            # the fur ends here (front edge, back edge); the membrane carries on to u = 1
U_LINE = 0.1                   # the lining starts under the head's curve
THICK = (0.026, 0.018, 0.011)  # the fur slab: at the root, at the fur's end, at the side edges (review P1.2-1: a thin sliver)
GAP = 0.0045                   # the lining sits this far inside F (tucked into the fur at its sides)

_HEAD: dict = {}
_GRID: dict = {}


def configure(head_c, head_r, cheek) -> None:
    _HEAD.update(c=np.array(head_c, float), r=np.array(head_r, float), cheek=tuple(cheek))
    _GRID.clear()


def side_x(y, z):
    """The half width of the head, cheeks and chest at (y, z): the flap stays outside it."""
    c, r = _HEAD['c'], _HEAD['r']
    q = 1.0 - ((y - c[1]) / r[1]) ** 2 - ((z - c[2]) / r[2]) ** 2
    x = r[0] * np.sqrt(np.clip(q, 0.0, None))
    cx, cy, cz, cr = _HEAD['cheek']
    q = 1.0 - ((y - cy) / (cr * 0.95)) ** 2 - ((z - cz) / (cr * 0.9)) ** 2
    x = np.where(q > 0, np.maximum(x, cx + cr * np.sqrt(np.clip(q, 0.0, None))), x)
    q = 1.0 - ((y + 0.27) / 0.231) ** 2 - ((z - 0.4) / 0.2376) ** 2     # the chest (recipe torso_parts), and its fur
    return np.maximum(x, 0.262 * np.sqrt(np.clip(q, 0.0, None)))


def u_fur(v):
    return U_FUR[0] + (U_FUR[1] - U_FUR[0]) * np.asarray(v, float)


def thickness(u, v):
    u, v = np.asarray(u, float), np.asarray(v, float)
    t = THICK[0] + (THICK[1] - THICK[0]) * smooth(0.0, 1.0, u / u_fur(v))
    edge = smooth(0.0, 0.26, v) * smooth(1.0, 0.74, v)
    return THICK[2] + (t - THICK[2]) * edge * (0.35 + 0.65 * smooth(0.0, 0.3, u))


def flap(s: int, u, v) -> np.ndarray:
    """F(s, u, v) for arrays u, v: (n, 3)."""
    u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
    ym, zm, lm = 0.5 * sum(ROOT_Y), 0.5 * sum(ROOT_Z), 0.5 * sum(LEN)
    turn = TURN * smooth(0.0, 0.75, u)
    # a leaf: narrow at the root, widening fast, then nearly parallel down to the rounded fan
    w = WIDTH[0] + (WIDTH[1] - WIDTH[0]) * (1.0 - (1.0 - np.clip(u, 0, 1)) ** 2.2)
    across = (v - 0.5) * w
    zc = zm - lm * u
    z = zc + (ROOT_Z[0] + (ROOT_Z[1] - ROOT_Z[0]) * v - zm) * (1 - u) - (LEN[0] + (LEN[1] - LEN[0]) * v - lm) * u
    arch = 1.0 - (2.0 * v - 1.0) ** 2
    z = z - ROUND * u * u * arch + 0.03 * (arch - 1.0) * (1.0 - u) ** 3      # the root line arches over the head
    xr = float(side_x(np.array(ym), np.array(zm))) - 0.01
    cup = CUP * smooth(0.12, 0.8, u) * (1.0 - (2.0 * v - 1.0) ** 2)
    x = xr + OUT[0] * u + OUT[1] * u * u - across * np.sin(turn) + cup * np.cos(turn)
    y = ym + 0.012 * u + across * np.cos(turn) + cup * np.sin(turn)
    m = side_x(y, z) + CLEAR[0] + (CLEAR[1] - CLEAR[0]) * smooth(0.02, 0.4, u)
    x = 0.5 * (x + m + np.sqrt((x - m) ** 2 + 0.02 ** 2))
    return np.stack([s * x, y, z], axis=-1).reshape(-1, 3)


def frame(s: int, u, v):
    """Points, ∂F/∂u, ∂F/∂v and the outward unit normal."""
    u, v = np.broadcast_arrays(np.asarray(u, float).ravel(), np.asarray(v, float).ravel())
    h = 1e-3
    P = flap(s, u, v)
    Fu = (flap(s, u + h, v) - flap(s, u - h, v)) / (2 * h)
    Fv = (flap(s, u, v + h) - flap(s, u, v - h)) / (2 * h)
    n = np.cross(Fu, Fv)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    n *= np.sign(n[:, :1] * s + 1e-12)
    return P, Fu, Fv, n


def root(s: int) -> Vector:
    return Vector(flap(s, 0.0, 0.5)[0])


def tip(s: int) -> Vector:
    return Vector(flap(s, 1.0, 0.5)[0])


# ----------------------------------------------------------------------------- the fur slab (joined into the voxel body)
def slab(s: int, nu: int = 40, nv: int = 16) -> bpy.types.Object:
    """A closed slab on the outside of F from the root (sunk into the head) down to where the fur ends."""
    v = np.linspace(0.0, 1.0, nv + 1)
    rows_in, rows_out = [], []
    for j in range(nu + 1):
        u = (j / nu) * u_fur(v)
        P, _fu, _fv, n = frame(s, u, v)
        t = thickness(u, v)[:, None]
        rows_in.append(P + n * 0.0015)
        rows_out.append(P + n * t)
    bm = bmesh.new()
    vin = [[bm.verts.new(p) for p in row] for row in rows_in]
    vout = [[bm.verts.new(p) for p in row] for row in rows_out]

    def quad(a, b, c, d):
        bm.faces.new((a, b, c, d))
    for j in range(nu):
        for i in range(nv):
            quad(vout[j][i], vout[j][i + 1], vout[j + 1][i + 1], vout[j + 1][i])
            quad(vin[j][i], vin[j + 1][i], vin[j + 1][i + 1], vin[j][i + 1])
    for j in range(nu):            # the side rims (front and back edges)
        quad(vin[j][0], vout[j][0], vout[j + 1][0], vin[j + 1][0])
        quad(vin[j][nv], vin[j + 1][nv], vout[j + 1][nv], vout[j][nv])
    for i in range(nv):            # the root and the fur's end
        quad(vin[0][i], vin[0][i + 1], vout[0][i + 1], vout[0][i])
        quad(vin[nu][i], vout[nu][i], vout[nu][i + 1], vin[nu][i + 1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'earslab{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
    return ob


# ----------------------------------------------------------------------------- the lining (the membrane sheet)
def lining_u(uu):
    """The sheet's own 0..1 (root → scalloped edge) onto the flap's u."""
    return U_LINE + (1.0 - U_LINE) * np.asarray(uu, float)


def lining_point(s: int, uu: float, v: float, relief: float = 0.0) -> Vector:
    """The membrane at sheet coordinates (uu, v); `relief` raises the ribs toward the hollow."""
    u = float(lining_u(uu))
    P, _fu, _fv, n = frame(s, u, v)
    edge = max(float(smooth(0.1, 0.0, v)), float(smooth(0.9, 1.0, v)))
    under_fur = float(smooth(float(u_fur(v)) + 0.02, float(u_fur(v)) - 0.05, u))
    top = float(smooth(U_LINE + 0.08, U_LINE, u))
    tuck = min(1.0, max(edge * under_fur, top))
    gap = GAP - (GAP + 0.005) * tuck
    return Vector(P[0] - n[0] * (gap + relief))


# ----------------------------------------------------------------------------- where points sit on the flaps
def _grid(s: int) -> dict:
    if s not in _GRID:
        uu, vv = np.meshgrid(np.linspace(0.0, 1.0, 45), np.linspace(-0.05, 1.05, 21), indexing='ij')
        P, Fu, Fv, n = frame(s, uu.ravel(), vv.ravel())
        P32 = P.astype(np.float32)
        _GRID[s] = {'P': P, 'P32': P32, 'PP': (P32 * P32).sum(1), 'Fu': Fu, 'Fv': Fv, 'n': n, 'u': uu.ravel(), 'v': vv.ravel()}
    return _GRID[s]


def lookup(p: np.ndarray) -> dict:
    """Per point: s (the flap's side, 0 = far from both), u, v, d (signed distance out from F), t (the slab's thickness
    at u, v) and down (the flap's unit ∂F/∂u there)."""
    k = len(p)
    out = {'s': np.zeros(k), 'u': np.zeros(k), 'v': np.zeros(k), 'd': np.full(k, 9.0), 't': np.zeros(k), 'down': np.zeros((k, 3))}
    for s in (1, -1):
        g = _grid(s)
        lo, hi = g['P'].min(0) - 0.05, g['P'].max(0) + 0.05
        idx = np.nonzero(np.all((p >= lo) & (p <= hi), axis=1) & (p[:, 0] * s > 0.05))[0]
        for a in range(0, len(idx), 16384):
            ii = idx[a:a + 16384]
            q = p[ii].astype(np.float32)
            j = np.argmin((q * q).sum(1)[:, None] - 2.0 * (q @ g['P32'].T) + g['PP'][None], axis=1)
            dlt = p[ii] - g['P'][j]
            fu, fv = g['Fu'][j], g['Fv'][j]
            a11, a12, a22 = (fu * fu).sum(1), (fu * fv).sum(1), (fv * fv).sum(1)
            b1, b2 = (dlt * fu).sum(1), (dlt * fv).sum(1)
            det = np.maximum(a11 * a22 - a12 * a12, 1e-12)
            out['s'][ii] = s
            out['u'][ii] = np.clip(g['u'][j] + (a22 * b1 - a12 * b2) / det, 0.0, 1.2)
            out['v'][ii] = np.clip(g['v'][j] + (a11 * b2 - a12 * b1) / det, -0.1, 1.1)
            out['d'][ii] = (dlt * g['n'][j]).sum(1)
            out['down'][ii] = fu / np.maximum(np.linalg.norm(fu, axis=1, keepdims=True), 1e-9)
    out['t'] = thickness(np.clip(out['u'], 0, 1), np.clip(out['v'], 0, 1))
    return out


def zone(p: np.ndarray):
    """(on the fur flap, its u, on the flap's inner face, the lookup): the inner face is the lining's side."""
    L = lookup(p)
    u, v, d, t = L['u'], L['v'], L['d'], L['t']
    on = (L['s'] != 0) & (u > 0.06) & (u < u_fur(np.clip(v, 0, 1)) + 0.05) & (v > -0.08) & (v < 1.08) & (d > -0.012) & (d < t + 0.016)
    inner = on & (d < 0.45 * t)
    return on, u, inner, L


def root_dist(p: np.ndarray) -> np.ndarray:
    """Distance to the nearer flap's root line."""
    out = np.full(len(p), 9.0)
    for s in (1, -1):
        a, b = flap(s, 0.0, 0.0)[0], flap(s, 0.0, 1.0)[0]
        ab = b - a
        t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
        out = np.minimum(out, np.linalg.norm(p - (a + t[:, None] * ab), axis=1))
    return out
