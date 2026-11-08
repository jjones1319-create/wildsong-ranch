"""Tumblefox Ultra ears: tall pointed cups with cream fluff inside and dark tips (1-hero.png, 4-details.png panel 5).

Each ear is a surface F(s, u, v) on side s (+1 = the monster's left): u runs from the root, sunk into the skull (0), to
the tip (1); v across the ear from its inner edge, by the head's midline (0), to its outer edge (1). The middle of the
ear sits behind its rims (the cup), so the front is a hollow that holds the cream fluff and the back is a rounded
shell of short orange fur, dark plum toward the tip.
  - `slab()`: the ear as a closed slab behind F (thick at the root, thin at the rims and the tip), joined into the voxel
    body so the coat grows on it;
  - `lookup()` / `zone()`: for any points, the nearest (u, v), the signed distance in front of F and the slab's
    thickness there (the coat's zones, the fur's flow up the ear, the inner side, the skin weights).
Measured on 2-turnaround.png at 0.9 m tall: the tips at x ±0.14, z 0.9; the ear ~0.15 m across where it leaves the head;
the opening faces forward and a little out, so the cream shows from the front, the side and the three-quarter view.
Metres; the monster faces −Y, Z is up.
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib.mesh import Part
from lib.surface import smooth

ROOT = np.array([0.108, -0.232, 0.684])      # the root's middle (left ear), sunk into the skull
TIP = np.array([0.146, -0.256, 0.882])
OPEN = np.array([0.62, -1.0, 0.1])          # the opening faces forward, a little out and up
WIDTH = 0.21                                # across at the root
CUP = 0.026                                 # the middle sits this far behind the rims
THICK = (0.03, 0.011, 0.009)                # the slab: at the root, at the tip, at the rims
U_TIP = 0.7                                 # dark plum from here to the tip (the back, and the rims at the front)

_GRID: dict = {}
_HEAD: dict = {}


def configure(head_c, head_r) -> None:
    """The skull ellipsoid the root sinks into (from the recipe)."""
    _HEAD.update(c=np.array(head_c, float), r=np.array(head_r, float))
    _GRID.clear()


def _on_skull(P: np.ndarray, sink: float) -> np.ndarray:
    """Points projected from the skull's centre onto its surface, then `sink` metres in along its normal."""
    c, r = _HEAD['c'], _HEAD['r']
    q = P - c[None]
    t = 1.0 / np.sqrt(np.maximum(((q / r[None]) ** 2).sum(1), 1e-12))
    S = c[None] + q * t[:, None]
    n = (S - c[None]) / (r[None] ** 2)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    return S - n * sink


def _frame0(s: int):
    root = ROOT * np.array([s, 1, 1])
    tip = TIP * np.array([s, 1, 1])
    up = tip - root
    length = float(np.linalg.norm(up))
    up = up / length
    n0 = OPEN * np.array([s, 1, 1])
    n0 = n0 - up * (n0 @ up)
    n0 /= np.linalg.norm(n0)
    across = np.cross(up, n0) * s           # inner edge → outer edge
    return root, up, n0, across, length


def half_width(u):
    u = np.clip(np.asarray(u, float), 0.0, 1.0)
    # full at the root, the sides gently convex, a narrow rounded tip
    return 0.5 * WIDTH * (1.0 - u ** 1.25) ** 0.85 * (1.0 + 0.12 * np.sin(np.pi * np.clip(u / 0.6, 0, 1)))


def surface(s: int, u, v) -> np.ndarray:
    """F(s, u, v) for arrays u, v: (n, 3)."""
    u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
    root, up, n0, across, length = _frame0(s)
    a = 2.0 * v - 1.0
    cup = CUP * (1.0 - a * a) * (1.0 - np.clip(u, 0, 1)) ** 0.55
    P = (root[None] + up[None] * (length * u.ravel())[:, None] + across[None] * (a * half_width(u)).ravel()[:, None]
         - n0[None] * cup.ravel()[:, None])
    if _HEAD:
        # the root follows the skull: the bottom of the ear slides onto the head's curve (no floating outer corner)
        P0 = root[None] + across[None] * (a * half_width(np.zeros_like(u))).ravel()[:, None] - n0[None] * (CUP * (1.0 - a * a)).ravel()[:, None]
        k = (1.0 - smooth(0.0, 0.32, u)).ravel()[:, None]
        P = P + (_on_skull(P0, 0.016) - P0) * k
    return P.reshape(-1, 3)


def frame(s: int, u, v):
    """Points, ∂F/∂u, ∂F/∂v and the unit normal out of the ear's front (the opening)."""
    u, v = np.broadcast_arrays(np.asarray(u, float).ravel(), np.asarray(v, float).ravel())
    h = 1e-3
    P = surface(s, u, v)
    Fu = (surface(s, u + h, v) - surface(s, u - h, v)) / (2 * h)
    Fv = (surface(s, u, v + h) - surface(s, u, v - h)) / (2 * h)
    n = np.cross(Fu, Fv)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    _r, _up, n0, _a, _l = _frame0(s)
    n *= np.sign(n @ n0 + 1e-12)[:, None]
    return P, Fu, Fv, n


def thickness(u, v):
    u, v = np.asarray(u, float), np.asarray(v, float)
    t = THICK[0] + (THICK[1] - THICK[0]) * smooth(0.0, 1.0, u)
    a = np.abs(2.0 * v - 1.0)
    edge = smooth(1.0, 0.6, a)
    return THICK[2] + (t - THICK[2]) * edge


def root(s: int) -> Vector:
    return Vector(surface(s, 0.0, 0.5)[0])


def tip(s: int) -> Vector:
    return Vector(surface(s, 1.0, 0.5)[0])


def slab(s: int, nu: int = 40, nv: int = 18) -> bpy.types.Object:
    """A closed slab behind F, from the root (sunk into the skull) to the tip."""
    v = np.linspace(0.0, 1.0, nv + 1)
    rows_in, rows_out = [], []
    for j in range(nu + 1):
        u = np.full(nv + 1, j / nu * 0.995)
        P, _fu, _fv, n = frame(s, u, v)
        t = thickness(u, v)[:, None]
        rows_in.append(P + n * 0.0012)
        rows_out.append(P - n * t)
    bm = bmesh.new()
    vin = [[bm.verts.new(p) for p in row] for row in rows_in]
    vout = [[bm.verts.new(p) for p in row] for row in rows_out]

    def quad(a, b, c, d):
        bm.faces.new((a, b, c, d))
    for j in range(nu):
        for i in range(nv):
            quad(vout[j][i], vout[j][i + 1], vout[j + 1][i + 1], vout[j + 1][i])
            quad(vin[j][i], vin[j + 1][i], vin[j + 1][i + 1], vin[j][i + 1])
    for j in range(nu):
        quad(vin[j][0], vout[j][0], vout[j + 1][0], vin[j + 1][0])
        quad(vin[j][nv], vin[j + 1][nv], vout[j + 1][nv], vout[j][nv])
    for i in range(nv):
        quad(vin[0][i], vin[0][i + 1], vout[0][i + 1], vout[0][i])
        quad(vin[nu][i], vout[nu][i], vout[nu][i + 1], vin[nu][i + 1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'earslab{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
    return ob


def _grid(s: int) -> dict:
    if s not in _GRID:
        uu, vv = np.meshgrid(np.linspace(0.0, 1.0, 41), np.linspace(-0.05, 1.05, 23), indexing='ij')
        P, Fu, Fv, n = frame(s, uu.ravel(), vv.ravel())
        P32 = P.astype(np.float32)
        _GRID[s] = {'P': P, 'P32': P32, 'PP': (P32 * P32).sum(1), 'Fu': Fu, 'Fv': Fv, 'n': n, 'u': uu.ravel(), 'v': vv.ravel()}
    return _GRID[s]


def lookup(p: np.ndarray) -> dict:
    """Per point: s (the ear's side, 0 = far from both), u, v, d (signed distance in front of F: the hollow is +, the
    back of the ear −), t (the slab's thickness at u, v) and up (the ear's unit ∂F/∂u there)."""
    k = len(p)
    out = {'s': np.zeros(k), 'u': np.zeros(k), 'v': np.zeros(k), 'd': np.full(k, 9.0), 't': np.zeros(k), 'up': np.zeros((k, 3)),
           'n': np.zeros((k, 3))}
    for s in (1, -1):
        g = _grid(s)
        lo, hi = g['P'].min(0) - 0.04, g['P'].max(0) + 0.04
        idx = np.nonzero(np.all((p >= lo) & (p <= hi), axis=1) & (p[:, 0] * s > 0.02))[0]
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
            out['u'][ii] = np.clip(g['u'][j] + (a22 * b1 - a12 * b2) / det, -0.1, 1.1)
            out['v'][ii] = np.clip(g['v'][j] + (a11 * b2 - a12 * b1) / det, -0.1, 1.1)
            out['d'][ii] = (dlt * g['n'][j]).sum(1)
            out['up'][ii] = fu / np.maximum(np.linalg.norm(fu, axis=1, keepdims=True), 1e-9)
            out['n'][ii] = g['n'][j]
    out['t'] = thickness(np.clip(out['u'], 0, 1), np.clip(out['v'], 0, 1))
    return out


def zone(p: np.ndarray, L: dict | None = None):
    """(on the ear, its u, on the ear's front (the hollow), the lookup)."""
    if L is None:
        L = lookup(p)
    u, v, d, t = L['u'], L['v'], L['d'], L['t']
    on = (L['s'] != 0) & (u > 0.12) & (u < 1.06) & (v > -0.08) & (v < 1.08) & (d > -t - 0.016) & (d < FLUFF_REACH)
    inner = on & (d > -0.4 * t)
    return on, u, inner, L


# ----------------------------------------------------------------------------- the fluff in the hollow (round 2)
# Review 1: the ear's insides rendered as flat grey fins (#918C84 to #B3AB9D), shadowed in the cup. 4-details.png panel 5
# fills the hollow with cream fluff that spills past the inner rim: soft lumps rising from the hollow, up and out of the
# opening, voxel-united into the body so the cream coat grows on them and catches the light.
# (u, v, length, thickness, out): along the ear, across it, the lump's length, its thickness, how far it leans out
# round 2 in-game check: the lumps deepened the cup's shadow (a dark, blotchy inside); the fluff is cards now
FLUFF: list = []
FLUFF_REACH = 0.055                 # the ear zone reaches this far in front of F (the lumps)


def _euler(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    from mathutils import Matrix
    import math
    y = y / np.linalg.norm(y)
    x = x - y * (x @ y)
    x = x / np.linalg.norm(x)
    z = np.cross(x, y)
    e = Matrix((Vector(x), Vector(y), Vector(z))).transposed().to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def fluff_parts() -> list[Part]:
    """Review 2: the ear's insides still read grey. A soft cream pillow fills each cup from near the root to two thirds
    up, its front a little proud of the rims (the fluff spilling past the inner rim, 4-details.png panel 5): convex, so
    it faces the light instead of sitting in the cup's shadow."""
    out = []
    for s in (1, -1):
        _root, up, _n0, across, _length = _frame0(s)
        P, _fu, _fv, n = frame(s, 0.32, 0.47)
        c = P[0] + n[0] * 0.006
        out.append(Part(f'earpillow{"L" if s > 0 else "R"}', 'sphere', loc=tuple(c), radius=1.0, scale=(0.05, 0.085, 0.026),
                        rot=_euler(across, up)))
    return out
