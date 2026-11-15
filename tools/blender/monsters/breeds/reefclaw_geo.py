"""Reefclaw's geometry kit (Art 2.1 Ultra): voxel-united solids for the shell-armoured limbs and the coral claw, surfaces
of revolution (barnacles, visors, eye cups, the lid balls) and swept tubes (the eye stalks), each a closed mesh with
outward faces. Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Matrix

from lib import common as C
from lib import surface as S
from lib.mesh import Part
from lib.surface import v3

PROPS_COLL = 'ReefclawParts'


def unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def ell_seg(name: str, a, b, thin: float, broad: float, plane_n, extra: float = 0.0) -> Part:
    """An ellipsoid whose long axis runs from a to b (plus `extra` past each end), `thin` across the plane whose normal
    is `plane_n` (a crab leg's flat sides) and `broad` in that plane."""
    a, b = v3(a), v3(b)
    d = b - a
    L = float(np.linalg.norm(d))
    X = d / L
    Y = unit(np.asarray(plane_n, float) - X * float(X @ np.asarray(plane_n, float)))
    Z = np.cross(X, Y)
    rot = Matrix([[X[0], Y[0], Z[0]], [X[1], Y[1], Z[1]], [X[2], Y[2], Z[2]]]).to_euler('XYZ')
    return Part(name, 'sphere', loc=tuple((a + b) / 2), radius=1.0, scale=(L / 2 + extra, thin, broad),
                rot=tuple(math.degrees(v) for v in rot))


def box_seg(name: str, a, b, thin: float, broad: float, plane_n, extra: float = 0.0) -> Part:
    """A flattened box from a to b (plus `extra` past each end), half-sizes `thin` across the plane whose normal is
    `plane_n` and `broad` in that plane: a plated, angular crab segment once the voxel union rounds its edges."""
    a, b = v3(a), v3(b)
    d = b - a
    L = float(np.linalg.norm(d))
    X = d / L
    Y = unit(np.asarray(plane_n, float) - X * float(X @ np.asarray(plane_n, float)))
    Z = np.cross(X, Y)
    rot = Matrix([[X[0], Y[0], Z[0]], [X[1], Y[1], Z[1]], [X[2], Y[2], Z[2]]]).to_euler('XYZ')
    return Part(name, 'box', loc=tuple((a + b) / 2), radius=0.5, scale=(L + 2 * extra, 2 * thin, 2 * broad),
                rot=tuple(math.degrees(v) for v in rot))


def ball(name: str, c, r: float) -> Part:
    return Part(name, 'sphere', loc=tuple(map(float, c)), radius=float(r))


def tube(name: str, a, b, r1: float, r2: float) -> Part:
    return Part(name, 'tube', loc=tuple(map(float, a)), to=tuple(map(float, b)), radius=float(r1), r2=float(r2))


def solid(name: str, parts: list[Part], high: bool, quick: bool, tris: int, voxel: tuple[float, float, float] = (0.002, 0.004, 0.004)) -> bpy.types.Object:
    """The parts voxel-united into one smooth closed mesh: fine for the high source, coarse and decimated to `tris` for the
    game. voxel = (high, high quick, low)."""
    v = (voxel[1] if quick else voxel[0]) if high else voxel[2]
    ob = S.build_body(name, parts, v, 3 if high else 2, segments=32 if high else 24, coll=PROPS_COLL)
    if not high:
        S.decimate_to(ob, tris, smooth_after=0.0)
    return ob


def _signed_volume(V: np.ndarray, faces: list) -> float:
    tot = 0.0
    for f in faces:
        a = V[f[0]]
        for k in range(1, len(f) - 1):
            tot += float(a @ np.cross(V[f[k]], V[f[k + 1]]))
    return tot / 6.0


def orient(V: np.ndarray, faces: list) -> list:
    """One closed shell's faces, turned outward (its signed volume made positive)."""
    if _signed_volume(V, faces) < 0:
        return [tuple(reversed(f)) for f in faces]
    return [tuple(f) for f in faces]


def mesh(name: str, V: np.ndarray, faces: list, attrs: dict | None = None) -> bpy.types.Object:
    """A mesh object from shells already turned outward (orient each closed shell first)."""
    return S.sheet_object(name, V, faces, attrs)


def lathe(profile: list[tuple[float, float]], seg: int, origin, axis, ref=None, rmod=None, hmod=None):
    """A surface of revolution: `profile` (r, h) from one pole (r 0) round to the other, about `axis` through `origin`.
    rmod(theta, k) / hmod(theta, k) scale each ring's radius / shift its height (k = the profile index) for ribs and
    teeth. Returns (verts, faces, (theta, k) per vertex)."""
    o, ax = v3(origin), unit(axis)
    if ref is None:
        ref = (1.0, 0.0, 0.0) if abs(float(ax[0])) < 0.9 else (0.0, 1.0, 0.0)
    r0 = v3(ref)
    r0 = unit(r0 - ax * float(r0 @ ax))
    r1 = np.cross(ax, r0)
    th = np.linspace(0.0, 2 * math.pi, seg, endpoint=False)
    V, tk, rings = [], [], []
    for k, (r, h) in enumerate(profile):
        if r <= 1e-9:
            rings.append(len(V))
            V.append(o + ax * h)
            tk.append((0.0, float(k)))
            continue
        rr = r * (rmod(th, k) if rmod else 1.0)
        hh = h + (hmod(th, k) if hmod else 0.0)
        pts = o[None] + ax[None] * np.broadcast_to(hh, th.shape)[:, None] + (np.cos(th)[:, None] * r0[None] + np.sin(th)[:, None] * r1[None]) * np.broadcast_to(rr, th.shape)[:, None]
        rings.append(np.arange(len(V), len(V) + seg))
        V.extend(pts)
        tk.extend((float(t), float(k)) for t in th)
    faces = []
    for k in range(len(rings) - 1):
        a, b = rings[k], rings[k + 1]
        for j in range(seg):
            jn = (j + 1) % seg
            if isinstance(a, int):
                faces.append((a, b[jn], b[j]))
            elif isinstance(b, int):
                faces.append((a[j], a[jn], b))
            else:
                faces.append((a[j], a[jn], b[jn], b[j]))
    return np.array(V), faces, np.array(tk)


def sweep(path: np.ndarray, radii: np.ndarray, seg: int, up=(0.0, 0.0, 1.0)):
    """A tube along `path` (k x 3) with a radius per point, closed by a pole at each end (the first and last radius 0
    make the poles). Returns (verts, faces, (theta, t) per vertex) with t 0..1 along the path."""
    P = v3(path)
    k = len(P)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    n = unit(np.cross(T[0], up) if abs(float(T[0] @ v3(up))) < 0.95 else np.cross(T[0], (1.0, 0.0, 0.0)))
    N = [n]
    for i in range(1, k):                    # parallel transport: the frame turns only as much as the path does
        v = N[-1] - T[i] * float(N[-1] @ T[i])
        N.append(unit(v))
    N = np.array(N)
    B = np.cross(T, N)
    seglen = np.linalg.norm(np.diff(P, axis=0), axis=1)
    tt = np.concatenate([[0.0], np.cumsum(seglen)]) / max(float(seglen.sum()), 1e-9)
    th = np.linspace(0.0, 2 * math.pi, seg, endpoint=False)
    V, tk, rings = [], [], []
    for i in range(k):
        if radii[i] <= 1e-9:
            rings.append(len(V))
            V.append(P[i])
            tk.append((0.0, tt[i]))
            continue
        pts = P[i][None] + (np.cos(th)[:, None] * N[i][None] + np.sin(th)[:, None] * B[i][None]) * radii[i]
        rings.append(np.arange(len(V), len(V) + seg))
        V.extend(pts)
        tk.extend((float(t), tt[i]) for t in th)
    faces = []
    for i in range(k - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(seg):
            jn = (j + 1) % seg
            if isinstance(a, int):
                faces.append((a, b[jn], b[j]))
            elif isinstance(b, int):
                faces.append((a[j], a[jn], b))
            else:
                faces.append((a[j], a[jn], b[jn], b[j]))
    return np.array(V), faces, np.array(tk)


def displace(ob: bpy.types.Object, d: np.ndarray) -> None:
    co, vn = S.mesh_arrays(ob)
    S.set_positions(ob, co + vn * d[:, None])


def tag(ob: bpy.types.Object, part: int, **attrs) -> bpy.types.Object:
    """Every prop piece carries `part` (which bone it rides; the joined lo_props keeps it) plus its paint fields."""
    n = len(ob.data.vertices)
    S.add_attr(ob, 'part', np.full(n, float(part)))
    for k, v in attrs.items():
        S.add_attr(ob, k, np.asarray(v, np.float64) if np.ndim(v) else np.full(n, float(v)))
    C.log(f'{ob.name}: {sum(len(p.vertices) - 2 for p in ob.data.polygons)} tris')
    return ob
