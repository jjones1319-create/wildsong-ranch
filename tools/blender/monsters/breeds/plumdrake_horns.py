"""Plumdrake's curled ram horns (Art 2.1 Ultra; chatgpt/monsters/32-plumdrake 1-hero, 2-turnaround, 3-faces, 4-details
panels 1 and 5): short, thick, cream, with fine growth ridges, curling back behind the eyes.

Each horn is a ridged tube swept along a ram's coil beside the head: it leaves the top of the head behind the brows, arcs
up and out (the top at about 1.71 m), back and down behind the head, forward under and curls into its own centre
(about 1.3 turns), so it reads as a coil from the side and as an oval curl from the front (2-turnaround: the coil's
centre at x +-0.27, y +0.09, z 1.56; its outer edge at x +-0.36). Built like nimbusheep_horns.py, with its own numbers
and a root that starts inward and forward of the coil (on the head's top, not beside it).

Metres; the monster faces -Y, Z is up, +X is its left. Rigid props: skinned to `prop.horns`.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import norm, smooth, v3

TILT = math.radians(35)             # the coil's plane turns this far to face forward (the curl shows from the front)
COIL_C = (0.27, 0.085, 1.56)        # the coil's centre (the left horn)
PHI0 = math.radians(160)            # where the horn leaves the head: in front of the centre, a little up
SWEEP = math.radians(480)           # about 1.33 turns
R_COIL = (0.11, 0.022)              # the centre line's radius at the root and at the tip
ROOT_IN = 0.13                      # the root starts this far inward (and a little forward) of the coil, on the head's top
HELIX = 0.03                        # a slight outward helix (a flat coil reads as a shell)
TUBE_R = (0.055, 0.014)             # the tube's radius at the root and at the tip (round 2: thicker bases)
FLAT = 0.88                         # the tube's cross-section: this much thinner along the coil's axis
GROOVES = 26                        # growth ridges along the horn (4-details panel 5)
GROOVE = (0.1, 0.2)                 # round 2: ridges in the shape; groove depth (share of the radius) and width (share of a groove's spacing)


def axes(s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The coil's axis A (outward, turned a little forward), and its in-plane axes B (back) and U (up)."""
    A = v3((s * math.cos(TILT), -math.sin(TILT), 0.0))
    B = v3((s * math.sin(TILT), math.cos(TILT), 0.0))
    return A, B, v3((0.0, 0.0, 1.0))


def centre(s: int) -> np.ndarray:
    return v3((s * COIL_C[0], COIL_C[1], COIL_C[2]))


def coil_radius(t):
    t = np.asarray(t, float)
    return R_COIL[0] + (R_COIL[1] - R_COIL[0]) * smooth(0.2, 1.0, t)


def tube_radius(t):
    t = np.asarray(t, float)
    return TUBE_R[0] + (TUBE_R[1] - TUBE_R[0]) * t ** 1.3


def path(s: int, t) -> np.ndarray:
    """The horn's centre line at t (0 root ... 1 tip), (n, 3)."""
    t = np.atleast_1d(np.asarray(t, float))
    A, B, U = axes(s)
    phi = PHI0 - SWEEP * t
    R = coil_radius(t)
    rin = v3((-s * 1.0, -0.2, 0.0))
    rin = rin / np.linalg.norm(rin)
    inward = ROOT_IN * (1.0 - smooth(0.0, 0.35, t))
    return (centre(s)[None] + (np.cos(phi)[:, None] * B[None] + np.sin(phi)[:, None] * U[None]) * R[:, None]
            + A[None] * (HELIX * t)[:, None] + rin[None] * inward[:, None])


def groove(t) -> np.ndarray:
    """1 in the middle of a growth ridge's groove, 0 between; they crowd a little toward the tip."""
    t = np.asarray(t, float)
    g = t ** 0.88 * GROOVES
    f = g - np.floor(g)
    d = np.minimum(f, 1.0 - f)
    return np.exp(-(d / GROOVE[1]) ** 2) * smooth(0.03, 0.08, t) * smooth(1.0, 0.94, t)


def build_horn(name: str, s: int, high: bool, quick: bool = False) -> bpy.types.Object:
    """One horn: rings along the coil (`horn` = (t, groove, outer side)), a rounded tip and a capped root (buried in the
    head); its own unwrap (one strip)."""
    ns = (40 if not quick else 24) if high else 11
    if high:
        t = np.linspace(0.0, 1.0, 420 if not quick else 180)
    else:
        # the game horn: three rings per groove so the ridges scallop the outline a little
        k = np.arange(GROOVES * 3 + 1) / 3.0
        t = np.clip((k / GROOVES) ** (1 / 0.88), 0.0, 1.0)
        t = np.unique(np.concatenate([[0.0, 0.02, 0.05], t, [0.97, 1.0]]))
    nr = len(t)
    P = path(s, t)
    T = norm(np.gradient(P, axis=0))
    A, _B, _U = axes(s)
    e_ax = norm(A[None] - T * (T @ A)[:, None])
    e_rad = norm(np.cross(e_ax, T))
    ctr = centre(s)[None] + A[None] * (HELIX * t)[:, None]
    if float(np.median(((P - ctr) * e_rad).sum(1))) < 0:
        e_rad *= -1
    e_ax = np.cross(T, e_rad)
    g = groove(t)
    amp = GROOVE[0] * (1.0 if high else 0.8)
    r = tube_radius(t)
    a = np.linspace(0.0, 2 * math.pi, ns, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    outer = np.clip(ca, 0.0, 1.0)
    rr = r[:, None] * (1.0 - amp * g[:, None] * (0.5 + 0.5 * outer[None]))
    if high:
        rr *= 1.0 + 0.004 * np.sin(t * 2 * math.pi * GROOVES * 3.9)[:, None] * (0.4 + 0.6 * outer[None])
    ring = (P[:, None, :] + e_rad[:, None, :] * (rr * ca[None])[..., None] + e_ax[:, None, :] * (rr * sa[None] * FLAT)[..., None])
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    circ = 2 * math.pi * float(np.median(r)) * (0.5 * (1 + FLAT))

    def put(face, coords):
        for lp, (uu, vv) in zip(face.loops, coords):
            lp[uvl].uv = (uu * circ, vv)
    verts = [[bm.verts.new(tuple(ring[i, j])) for j in range(ns)] for i in range(nr)]
    for i in range(nr - 1):
        for j in range(ns):
            jn = (j + 1) % ns
            f = bm.faces.new((verts[i][j], verts[i][jn], verts[i + 1][jn], verts[i + 1][j]))
            put(f, [(j / ns, arc[i]), ((j + 1) / ns, arc[i]), ((j + 1) / ns, arc[i + 1]), (j / ns, arc[i + 1])])
    tip = [verts[-1]]
    capn = 6 if high else 3
    for k in range(1, capn + 1):
        f = k / (capn + 0.6)
        rk = rr[-1] * math.sqrt(max(0.0, 1.0 - f * f))
        c = P[-1] + T[-1] * r[-1] * 0.9 * f
        tip.append([bm.verts.new(tuple(c + e_rad[-1] * rk[j] * ca[j] + e_ax[-1] * rk[j] * sa[j] * FLAT)) for j in range(ns)])
    step = float(r[-1]) * 0.9 / (capn + 0.6)
    for k in range(capn):
        for j in range(ns):
            jn = (j + 1) % ns
            f = bm.faces.new((tip[k][j], tip[k][jn], tip[k + 1][jn], tip[k + 1][j]))
            v0, v1 = arc[-1] + step * k, arc[-1] + step * (k + 1)
            put(f, [(j / ns, v0), ((j + 1) / ns, v0), ((j + 1) / ns, v1), (j / ns, v1)])
    end = bm.verts.new(tuple(P[-1] + T[-1] * r[-1] * 0.95))
    vend = arc[-1] + step * (capn + 0.6)
    for j in range(ns):
        f = bm.faces.new((tip[-1][j], tip[-1][(j + 1) % ns], end))
        put(f, [(j / ns, arc[-1] + step * capn), ((j + 1) / ns, arc[-1] + step * capn), ((j + 0.5) / ns, vend)])
    root = bm.verts.new(tuple(P[0] - T[0] * r[0] * 0.5))
    for j in range(ns):
        f = bm.faces.new((verts[0][(j + 1) % ns], verts[0][j], root))
        put(f, [((j + 1) / ns, 0.0), (j / ns, 0.0), ((j + 0.5) / ns, -float(r[0]) * 0.5)])
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    tt = np.concatenate([np.repeat(t, ns), np.repeat(np.full(capn, 1.0), ns), [1.0], [0.0]])
    gg = np.concatenate([np.repeat(g, ns), np.zeros(capn * ns), [0.0], [0.0]])
    oo = np.concatenate([np.tile(outer, nr), np.tile(outer, capn), [0.5], [0.5]])
    S.add_attr(ob, 'horn', np.stack([tt, gg, oo], axis=1))
    ob['own_uv'] = True
    co, vn = S.mesh_arrays(ob)
    if float(((co - path(s, tt)) * vn).sum()) < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()
    C.log(f'{name}: {len(me.polygons)} faces')
    return ob
