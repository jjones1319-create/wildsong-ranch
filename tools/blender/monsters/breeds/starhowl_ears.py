"""Starhowl Ultra ears: tall, pointed wolf ears standing on top of the head (chatgpt/monsters/06-starhowl: the hero and
2-turnaround.png), each a fur shell with a pink hollow facing forward.

Each ear is built round a mid surface M(s, u, v) on side s (+1 = the monster's left): u runs from the root on the skull
(0; the slab starts a little below it, sunk into the head) to the tip (1), v across from the inner edge (0) to the outer
edge (1). Its back normal `nb` looks backward (+Y) and a little inward.
  - the back (outer) surface: M + nb · (a rounded cone's depth + the rim), furred like the head;
  - the front (inner) surface: M + nb · cup, a hollow that faces forward and a little out, painted pink, with pale
    fluff at its bottom (no lying locks or cards on it);
  - `slab()`: the closed shell, joined into the voxel body (`body_extras`);
  - `lookup()` / `zone()`: for any points, the nearest (u, v), which face they're on (the fur, the hollow, the rims and
    the skin weights).
Metres; the monster faces −Y, Z is up.
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib.surface import smooth

# the left ear (s = +1); the right one mirrors x. Measured on 2-turnaround.png (front and side) at 1.28 m tall.
ROOT_IN = np.array((0.045, -0.405, 1.112))      # the inner edge's root, near the top of the skull
ROOT_OUT = np.array((0.168, -0.382, 1.04))      # the outer edge's root, down the side of the head
TIP = np.array((0.152, -0.392, 1.282))
U0 = -0.12                                      # the slab starts this far below the root line (sunk into the head)
BULGE = 0.014                                   # the edges bow outward (a leaf, not a straight-sided triangle)
CONE = 0.03                                     # the back's rounded depth at the root (a cone, not a flat card)
CUP = 0.026                                     # the hollow's depth at the root
RIM = (0.009, 0.0065)                           # the rim's thickness: at the root, near the tip
TIP_ROUND = 0.9                                 # the last share of u closes round to the point

_GRID: dict = {}


def _axes(s: int):
    ri, ro, t = ROOT_IN.copy(), ROOT_OUT.copy(), TIP.copy()
    for a in (ri, ro, t):
        a[0] *= s
    up = t - 0.5 * (ri + ro)
    across = ro - ri
    nb = np.cross(up, across) if s > 0 else np.cross(across, up)
    nb /= np.linalg.norm(nb)
    if nb[1] < 0:
        nb = -nb
    return ri, ro, t, nb


def mid(s: int, u, v) -> np.ndarray:
    """M(s, u, v) for arrays u, v: (n, 3)."""
    u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
    u, v = u.ravel(), v.ravel()
    ri, ro, t, nb = _axes(s)
    root = ri[None] + (ro - ri)[None] * v[:, None]
    p = root + (t[None] - root) * np.clip(u, None, 1.0)[:, None]
    across = (ro - ri) / np.linalg.norm(ro - ri)
    w = 2.0 * v - 1.0
    # the edges bow out in the middle of the ear's height
    p += across[None] * (BULGE * np.sin(np.pi * np.clip(u, 0, 1)) * w)[:, None]
    # the tip leans back a touch (the hero's ears tip backward slightly)
    p += nb[None] * (0.012 * np.clip(u, 0, 1) ** 2)[:, None]
    return p


def depth_back(u, v):
    w = 2.0 * np.asarray(v, float) - 1.0
    k = np.clip(1.0 - np.clip(u, 0, 1), 0, 1)
    rim = RIM[0] + (RIM[1] - RIM[0]) * np.clip(u, 0, 1)
    return CONE * k ** 0.8 * np.sqrt(np.clip(1.0 - w * w, 0, 1)) + rim


def depth_front(u, v):
    w = 2.0 * np.asarray(v, float) - 1.0
    k = np.clip(1.0 - np.clip(u, 0, 1), 0, 1)
    return CUP * k ** 1.1 * (1.0 - w * w) * smooth(-0.05, 0.12, np.asarray(u, float))


def surfaces(s: int, u, v):
    """(front, back) points of the shell."""
    _ri, _ro, _t, nb = _axes(s)
    m = mid(s, u, v)
    u_, v_ = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
    u_, v_ = u_.ravel(), v_.ravel()
    # close the tip: both faces meet the mid surface's centre line
    close = smooth(TIP_ROUND, 1.0, u_)
    front = m + nb[None] * depth_front(u_, v_)[:, None]
    back = m + nb[None] * (depth_back(u_, v_) * (1 - 0.7 * close))[:, None]
    return front, back


def root(s: int) -> Vector:
    return Vector(mid(s, 0.0, 0.5)[0])


def tip(s: int) -> Vector:
    return Vector(mid(s, 1.0, 0.5)[0])


def slab(s: int, nu: int = 36, nv: int = 18) -> bpy.types.Object:
    """The closed shell from below the root (sunk into the head) to the tip."""
    us = U0 + (1.0 - U0) * np.linspace(0.0, 1.0, nu + 1)
    vs = np.linspace(0.0, 1.0, nv + 1)
    bm = bmesh.new()
    vf, vb = [], []
    for u in us:
        uu = np.full(len(vs), min(u, 0.995))
        f, b = surfaces(s, uu, vs)
        vf.append([bm.verts.new(p) for p in f])
        vb.append([bm.verts.new(p) for p in b])
    tipv = bm.verts.new(mid(s, 1.0, 0.5)[0])

    def face(*vs_):
        try:
            bm.faces.new(vs_)
        except ValueError:
            pass
    for j in range(nu):
        for i in range(nv):
            face(vf[j][i], vf[j][i + 1], vf[j + 1][i + 1], vf[j + 1][i])
            face(vb[j][i], vb[j + 1][i], vb[j + 1][i + 1], vb[j][i + 1])
    for j in range(nu):
        face(vf[j][0], vf[j + 1][0], vb[j + 1][0], vb[j][0])
        face(vf[j][nv], vb[j][nv], vb[j + 1][nv], vf[j + 1][nv])
    for i in range(nv):
        face(vf[0][i], vb[0][i], vb[0][i + 1], vf[0][i + 1])
        face(vf[nu][i], vf[nu][i + 1], tipv)
        face(vb[nu][i + 1], vb[nu][i], tipv)
    face(vf[nu][0], tipv, vb[nu][0])
    face(vf[nu][nv], vb[nu][nv], tipv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'earslab{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
    return ob


# ----------------------------------------------------------------------------- where points sit on the ears
def _grid(s: int) -> dict:
    if s not in _GRID:
        uu, vv = np.meshgrid(np.linspace(U0, 1.0, 50), np.linspace(-0.05, 1.05, 25), indexing='ij')
        u, v = uu.ravel(), vv.ravel()
        h = 1e-3
        P = mid(s, u, v)
        Fu = (mid(s, u + h, v) - mid(s, u - h, v)) / (2 * h)
        Fv = (mid(s, u, v + h) - mid(s, u, v - h)) / (2 * h)
        P32 = P.astype(np.float32)
        _GRID[s] = {'P': P, 'P32': P32, 'PP': (P32 * P32).sum(1), 'Fu': Fu, 'Fv': Fv, 'u': u, 'v': v}
    return _GRID[s]


def lookup(p: np.ndarray) -> dict:
    """Per point: s (the ear's side, 0 = far from both), u, v, d (signed distance back from M along nb), and the
    shell's front and back depths there."""
    k = len(p)
    out = {'s': np.zeros(k), 'u': np.zeros(k), 'v': np.zeros(k), 'd': np.full(k, 9.0), 'up': np.zeros((k, 3))}
    for s in (1, -1):
        g = _grid(s)
        _ri, _ro, _t, nb = _axes(s)
        lo, hi = g['P'].min(0) - 0.06, g['P'].max(0) + 0.06
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
            out['v'][ii] = np.clip(g['v'][j] + (a11 * b2 - a12 * b1) / det, -0.1, 1.1)
            out['d'][ii] = dlt @ nb
            out['up'][ii] = fu / np.maximum(np.linalg.norm(fu, axis=1, keepdims=True), 1e-9)
    uc, vc = np.clip(out['u'], 0, 1), np.clip(out['v'], 0, 1)
    out['front'] = depth_front(uc, vc)
    out['back'] = depth_back(uc, vc)
    return out


def zone(p: np.ndarray):
    """(on the ear, its u, on the hollow's face, on the rim, the lookup)."""
    L = lookup(p)
    u, v, d = L['u'], L['v'], L['d']
    on = (L['s'] != 0) & (u > 0.0) & (u < 1.06) & (v > -0.1) & (v < 1.1) & (d > -0.02) & (d < L['back'] + 0.02)
    middle = 0.5 * (L['front'] + L['back'])
    inner = on & (d < middle) & (v > 0.06) & (v < 0.94) & (u < 0.94)
    rim = on & ~inner & ((v < 0.1) | (v > 0.9))
    return on, u, inner, rim, L


def root_dist(p: np.ndarray) -> np.ndarray:
    """Distance to the nearer ear's root line."""
    out = np.full(len(p), 9.0)
    for s in (1, -1):
        a, b = mid(s, 0.0, 0.0)[0], mid(s, 0.0, 1.0)[0]
        ab = b - a
        t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
        out = np.minimum(out, np.linalg.norm(p - (a + t[:, None] * ab), axis=1))
    return out
