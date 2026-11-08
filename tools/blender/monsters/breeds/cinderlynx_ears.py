"""Cinderlynx Ultra ears: tall pointed lynx ears, each a cupped fur shell voxel-united into the body.

Each ear is a surface F(s, u, v) on side s (+1 = the monster's left): u runs from the root (sunk into the skull, u < 0)
to the tip (1), v across the ear from its inner edge (0, toward the middle of the head) to its outer edge (1).
  - The front face of the shell is the cup (the inner ear: smooth salmon skin, pale fur along the inner edge); the back
    face is charcoal fur. The cup opens forward and a little outward (`TURN`), so both openings show in three-quarter
    view, as in 1-hero.png.
  - `shell()`: the closed shell, joined into the voxel body (`body_extras`), so the coat grows on its back face;
  - `lookup()`: for any points, the nearest (u, v), the signed distance out of the cup's face (+ = the inner-ear side)
    and the shell's thickness there: the coat's zones, the fur's flow up the ear, the skin weights.
  - `tip()`: the ear tip, where the ember tuft grows.
Metres; the monster faces −Y, Z is up. Measured on 2-turnaround.png (front, side): tip (±0.173, −0.31, 1.10), base
corners (±0.054, 0.946) inner and (±0.194, 0.879) outer, the base spanning y −0.36 … −0.23 in profile.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib.surface import smooth

BASE = np.array((0.124, -0.298, 0.9))        # the base centre (left ear)
TIP = np.array((0.178, -0.312, 1.08))        # the tip (round 3: a little shorter, the head now sits higher)
INNER = np.array((0.054, -0.30, 0.946))      # towards the inner base corner (fixes the across axis)
OUTER = np.array((0.194, -0.30, 0.879))
W0 = 0.084                                   # half width at the base (u = 0)
TURN = math.radians(24)                      # the cup turns outward about the ear's long axis
CUP = 0.03                                   # the middle of the ear bulges back by this much at the base
THICK = (0.03, 0.012, 0.011)                 # the shell: at the base, near the tip, along the rims
U0 = -0.32                                   # the root sinks this far into the skull (a share of the length)
TIP_BEND = 0.022                             # the tip bends outward
U_TOP = 0.985                                # the shell stops here (a tiny cap, not a degenerate point)


def _frame():
    a = TIP - BASE
    length = float(np.linalg.norm(a))
    a = a / length
    x = OUTER - INNER
    x = x - a * (x @ a)
    x /= np.linalg.norm(x)
    n = np.cross(x, a)                       # forward (−Y): out of the cup
    n /= np.linalg.norm(n)
    c, s_ = math.cos(TURN), math.sin(TURN)
    n2 = n * c + x * s_                      # the opening turns outward (+X on the left ear)
    x2 = x * c - n * s_
    return a, x2, n2, length


AX, XA, NA, LEN = _frame()


def width(u):
    u = np.asarray(u, float)
    uc = np.clip(u, 0.0, 1.0)
    # a lynx ear: straight-ish sides, a little convex, a fine point; the root keeps the base width
    return W0 * (1.0 - uc) ** 0.92 * (1.0 + 0.28 * uc) * np.where(u < 0, 1.0 - 0.25 * np.clip(u / U0, 0, 1), 1.0)


def cup(u, v):
    u, v = np.asarray(u, float), np.asarray(v, float)
    return CUP * (1.0 - (2.0 * v - 1.0) ** 2) * smooth(1.02, 0.15, u) * smooth(U0, 0.0, u)


def thickness(u, v):
    u, v = np.asarray(u, float), np.asarray(v, float)
    t = THICK[0] + (THICK[1] - THICK[0]) * smooth(0.0, 0.9, u)
    edge = smooth(0.0, 0.22, v) * smooth(1.0, 0.78, v)
    return THICK[2] + (t - THICK[2]) * edge


def face(s: int, u, v) -> np.ndarray:
    """The cup's face (the inner-ear side) at (u, v): (n, 3)."""
    u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
    u, v = u.ravel(), v.ravel()
    across = (2.0 * v - 1.0) * width(u)
    p = (BASE[None] + AX[None] * (LEN * u)[:, None] + XA[None] * across[:, None] - NA[None] * cup(u, v)[:, None]
         + XA[None] * (TIP_BEND * np.clip(u, 0, 1) ** 2)[:, None])
    p[:, 0] *= s
    return p


def normal(s: int) -> np.ndarray:
    n = NA.copy()
    n[0] *= s
    return n


def frame(s: int, u, v):
    """Points, ∂F/∂u, ∂F/∂v and the unit normal out of the cup (forward and outward)."""
    u, v = np.broadcast_arrays(np.asarray(u, float).ravel(), np.asarray(v, float).ravel())
    h = 1e-3
    P = face(s, u, v)
    Fu = (face(s, u + h, v) - face(s, u - h, v)) / (2 * h)
    Fv = (face(s, u, v + h) - face(s, u, v - h)) / (2 * h)
    n = np.cross(Fu, Fv)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    n *= np.sign((n @ normal(s))[:, None] + 1e-12)
    return P, Fu, Fv, n


def root(s: int) -> Vector:
    return Vector(face(s, 0.0, 0.5)[0])


def tip(s: int) -> Vector:
    return Vector(face(s, 1.0, 0.5)[0])


def tip_frame(s: int):
    """(tip point, the ear's long axis there, its outward across axis, the normal out of the cup)."""
    P, Fu, Fv, n = frame(s, 0.97, 0.5)
    a = Fu[0] / np.linalg.norm(Fu[0])
    x = Fv[0] / np.linalg.norm(Fv[0])
    return face(s, U_TOP, 0.5)[0], a, x, n[0]


# ----------------------------------------------------------------------------- the shell (joined into the voxel body)
def shell(s: int, nu: int = 44, nv: int = 18) -> bpy.types.Object:
    """A closed shell: the cup's face in front, its back `thickness` behind, rims along both edges, the root sunk in
    the skull and a small cap at the tip."""
    u = np.linspace(U0, U_TOP, nu + 1)
    v = np.linspace(0.0, 1.0, nv + 1)
    rows_f, rows_b = [], []
    for uj in u:
        P, _fu, _fv, n = frame(s, np.full(len(v), uj), v)
        t = thickness(np.full(len(v), uj), v)[:, None]
        rows_f.append(P)
        rows_b.append(P - n * t)
    bm = bmesh.new()
    vf = [[bm.verts.new(p) for p in row] for row in rows_f]
    vb = [[bm.verts.new(p) for p in row] for row in rows_b]

    def quad(a, b, c, d):
        bm.faces.new((a, b, c, d))
    for j in range(nu):
        for i in range(nv):
            quad(vf[j][i], vf[j][i + 1], vf[j + 1][i + 1], vf[j + 1][i])
            quad(vb[j][i], vb[j + 1][i], vb[j + 1][i + 1], vb[j][i + 1])
    for j in range(nu):
        quad(vf[j][0], vf[j + 1][0], vb[j + 1][0], vb[j][0])
        quad(vf[j][nv], vb[j][nv], vb[j + 1][nv], vf[j + 1][nv])
    for i in range(nv):
        quad(vf[0][i], vb[0][i], vb[0][i + 1], vf[0][i + 1])
        quad(vf[nu][i], vf[nu][i + 1], vb[nu][i + 1], vb[nu][i])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'earshell{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
    return ob


# ----------------------------------------------------------------------------- where points sit on the ears
_GRID: dict = {}


def _grid(s: int) -> dict:
    if s not in _GRID:
        uu, vv = np.meshgrid(np.linspace(U0, 1.0, 60), np.linspace(-0.08, 1.08, 25), indexing='ij')
        P, Fu, Fv, n = frame(s, uu.ravel(), vv.ravel())
        P32 = P.astype(np.float32)
        _GRID[s] = {'P': P, 'P32': P32, 'PP': (P32 * P32).sum(1), 'Fu': Fu, 'Fv': Fv, 'n': n, 'u': uu.ravel(), 'v': vv.ravel()}
    return _GRID[s]


def lookup(p: np.ndarray) -> dict:
    """Per point: s (the ear's side, 0 = far from both), u, v, d (signed distance out of the cup's face: + in front of
    it, − into the shell and behind), t (the shell's thickness there) and up (the ear's unit ∂F/∂u)."""
    k = len(p)
    out = {'s': np.zeros(k), 'u': np.full(k, -9.0), 'v': np.zeros(k), 'd': np.full(k, -9.0), 't': np.zeros(k), 'up': np.zeros((k, 3))}
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
            out['u'][ii] = np.clip(g['u'][j] + (a22 * b1 - a12 * b2) / det, U0, 1.1)
            out['v'][ii] = np.clip(g['v'][j] + (a11 * b2 - a12 * b1) / det, -0.15, 1.15)
            out['d'][ii] = (dlt * g['n'][j]).sum(1)
            out['up'][ii] = fu / np.maximum(np.linalg.norm(fu, axis=1, keepdims=True), 1e-9)
    out['t'] = thickness(np.clip(out['u'], 0, 1), np.clip(out['v'], 0, 1))
    return out


def zone(p: np.ndarray):
    """(on an ear above the skull, its u, on the cup's face, the lookup)."""
    L = lookup(p)
    u, v, d, t = L['u'], L['v'], L['d'], L['t']
    on = (L['s'] != 0) & (u > -0.05) & (v > -0.12) & (v < 1.12) & (d > -t - 0.016) & (d < 0.016)
    inner = on & (d > -0.45 * t) & (v > 0.04) & (v < 0.96)
    return on, u, inner, L
