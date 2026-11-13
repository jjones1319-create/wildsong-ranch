"""Nimbusheep's spiral horns (Art 2.1 Ultra; chatgpt/monsters/05-nimbusheep 1-hero, 2-turnaround, 4-details panel 5).

Each horn is a ridged tube swept along a ram's coil beside the head: it leaves the wool cap at the top of the head,
arcs back over, down behind, forward under and curls up into its own centre (about 1.2 turns), moving outward as it
goes, so from the side it reads as a full spiral and from the front as a curl standing out past the cheeks (front view:
the outer edge at x ±0.375, the curl's eye at x ±0.32, z 0.80; side view: the coil y −0.39..−0.15, z 0.71..0.955).
The ring grooves are sculpted on the high horn (baked into the normal map) and, gentler, on the game horn's outline.

Metres; the monster faces −Y, Z is up, +X is its left. Rigid props: the build skins them to `prop.horns`.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import norm, smooth, v3
from monsters.breeds.nimbusheep_wool import HEAD_DY

TILT = math.radians(50)            # the coil's plane turns this far to face forward (round 3: 30; Nov 12 review: the coil shows from the front)
COIL_C = (0.28, -0.3 + HEAD_DY, 0.8)  # beside the temple, at eye level (moves with the head)        # the coil's centre (left horn)
PHI0 = math.radians(128)           # where the horn leaves the head: up and a little forward of the centre
SWEEP = math.radians(530)           # about 1.47 turns, so about 1.3 show past the wool
R_COIL = (0.08, 0.012)             # the centre line's radius at the root and at the tip (Nov 12: the tip sits against the last turn)
W_AXIAL = (-0.055, 0.012)          # round 3: the curl stays in the coil's plane (a hole showed at the centre)            # offset along the coil's axis (outward) at the root and once it has swung out
TUBE_R = (0.06, 0.012)             # the tube's radius at the root and at the tip (Nov 12 review: root 20% thicker; a tip thick
                                    # enough to close the spiral's centre: an open serrated hole showed there)
FLAT = 0.86                         # the tube's cross-section: this much thinner along the coil's axis
GROOVES = 28                        # ring grooves along the horn (review: about 20 per turn)
GROOVE = (0.07, 0.16)               # groove depth (share of the radius) and width (share of a groove's spacing)


def axes(s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The coil's axis A (outward, turned a little forward), and its in-plane axes B (back) and U (up)."""
    A = v3((s * math.cos(TILT), -math.sin(TILT), 0.0))
    B = v3((s * math.sin(TILT), math.cos(TILT), 0.0))
    U = v3((0.0, 0.0, 1.0))
    return A, B, U


def centre(s: int) -> np.ndarray:
    return v3((s * COIL_C[0], COIL_C[1], COIL_C[2]))


def coil_radius(t):
    t = np.asarray(t, float)
    return R_COIL[0] + (R_COIL[1] - R_COIL[0]) * smooth(0.2, 1.0, t)


def axial(t):
    t = np.asarray(t, float)
    # Nov 13 review: a slight outward helix (the coil was flat, like an ammonite)
    return W_AXIAL[0] + (W_AXIAL[1] - W_AXIAL[0]) * (1.0 - (1.0 - np.clip(t / 0.5, 0, 1)) ** 2) + 0.03 * t


def tube_radius(t):
    t = np.asarray(t, float)
    return TUBE_R[0] + (TUBE_R[1] - TUBE_R[0]) * t ** 1.35       # Nov 13: fuller inner turns, so they close on each other


def path(s: int, t) -> np.ndarray:
    """The horn's centre line at t (0 root … 1 tip), (n, 3)."""
    t = np.atleast_1d(np.asarray(t, float))
    A, B, U = axes(s)
    phi = PHI0 - SWEEP * t
    R = coil_radius(t)
    return centre(s)[None] + (np.cos(phi)[:, None] * B[None] + np.sin(phi)[:, None] * U[None]) * R[:, None] + A[None] * axial(t)[:, None]


def groove(t) -> np.ndarray:
    """1 in the middle of a ring groove, 0 between; the grooves crowd a little toward the tip."""
    g = np.asarray(t, float) ** 0.88 * GROOVES
    f = g - np.floor(g)
    d = np.minimum(f, 1.0 - f)
    return np.exp(-(d / GROOVE[1]) ** 2) * smooth(0.02, 0.07, np.asarray(t, float)) * smooth(1.0, 0.94, np.asarray(t, float))


def build_horn(name: str, s: int, high: bool, quick: bool = False) -> bpy.types.Object:
    """One horn: rings along the coil (`horn` attribute = (t, groove, outer side), `horn_side` = s), a rounded tip and
    a capped root (buried in the wool cap)."""
    nr, ns = ((420, 40) if not quick else (180, 24)) if high else (0, 10)
    if high:
        t = np.linspace(0.0, 1.0, nr)
    else:
        # the game horn: four rings per groove (crest, flank, groove, flank) so the ridges scallop the outline
        k = np.arange(GROOVES * 4 + 1) / 4.0
        t = np.clip((k / GROOVES) ** (1 / 0.88), 0.0, 1.0)
        t = np.unique(np.concatenate([[0.0, 0.03, 0.06], t, [0.97, 1.0]]))
        nr = len(t)
    P = path(s, t)
    T = np.gradient(P, axis=0)
    T = norm(T)
    A, _B, _U = axes(s)
    e_ax = norm(A[None] - T * (T @ A)[:, None])
    e_rad = norm(np.cross(e_ax, T))
    # e_rad must point away from the coil's centre (the outside of the curl)
    ctr = centre(s)[None] + A[None] * axial(t)[:, None]
    # one sign for the whole horn (the cross product is continuous; a per-ring test flips near the closed tip)
    if float(np.median(((P - ctr) * e_rad).sum(1))) < 0:
        e_rad *= -1
    e_ax = np.cross(T, e_rad)
    g = groove(t)
    amp = GROOVE[0] * (1.0 if high else 0.9)     # round 3: raised rings that scallop the game horn's outline too
    r = tube_radius(t)
    a = np.linspace(0.0, 2 * math.pi, ns, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    outer = np.clip(ca, 0.0, 1.0)
    # the grooves are deeper on the outside of the curl, shallow on the inside (4-details.png, panel 5)
    rr = r[:, None] * (1.0 - amp * g[:, None] * (0.45 + 0.55 * outer[None]))
    if high:
        # fine growth lines between the grooves
        rr *= 1.0 + 0.004 * np.sin(t * 2 * math.pi * GROOVES * 4.1)[:, None] * (0.4 + 0.6 * outer[None])
    ring = (P[:, None, :] + e_rad[:, None, :] * (rr * ca[None])[..., None] + e_ax[:, None, :] * (rr * sa[None] * FLAT)[..., None])
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    # the horn's own unwrap, one strip (round 2; smart-project cut it into many islands): u round the tube, v along the
    # centre line, both in metres; the build only rescales it to the atlas's density (own_uv)
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
    # the tip: a rounded cap of a few shrinking rings
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
    root = bm.verts.new(tuple(P[0] - T[0] * r[0] * 0.4))
    for j in range(ns):
        f = bm.faces.new((verts[0][(j + 1) % ns], verts[0][j], root))
        put(f, [((j + 1) / ns, 0.0), (j / ns, 0.0), ((j + 0.5) / ns, -float(r[0]) * 0.4)])
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    # per vertex: t along the horn, the groove, and how much it faces the outside of the curl
    tt = np.concatenate([np.repeat(t, ns), np.repeat(np.full(capn, 1.0), ns), [1.0], [0.0]])
    gg = np.concatenate([np.repeat(g, ns), np.zeros(capn * ns), [0.0], [0.0]])
    oo = np.concatenate([np.tile(outer, nr), np.tile(outer, capn), [0.5], [0.5]])
    S.add_attr(ob, 'horn', np.stack([tt, gg, oo], axis=1))
    S.add_attr(ob, 'horn_side', np.full(len(tt), float(s)))
    # outward faces (a sanity flip: the ring order above winds them outward, but a mirrored side reverses it)
    co, vn = S.mesh_arrays(ob)
    ob['own_uv'] = True
    if float(((co - path(s, tt)) * vn).sum()) < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()
    C.log(f'{name}: {len(me.polygons)} faces')
    return ob


def build_horns(high: bool, quick: bool = False) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    return [build_horn(f'{tag}_horn{"L" if s > 0 else "R"}', s, high, quick) for s in (1, -1)]


def horn_paint(ob: bpy.types.Object, cream: str, groove_hex: str, root_hex: str, tip_hex: str) -> tuple[np.ndarray, np.ndarray]:
    """(linear RGB, rough) per vertex: cream, a deeper warm tone in the grooves (stronger on the outside of the curl),
    a little darker where it leaves the wool, paler toward the tip; glossy with a clear coat, a touch rougher in the
    grooves."""
    h = S.attr_array(ob, 'horn').astype(np.float64)
    t, g, o = h[:, 0], h[:, 1], h[:, 2]
    lin = lambda x: v3(C.lin_rgb(x))  # noqa: E731
    rgb = np.tile(lin(cream), (len(t), 1))
    k = (g * (0.55 + 0.45 * o))[:, None]
    rgb = rgb * (1 - k) + lin(groove_hex)[None] * k
    rk = smooth(0.12, 0.0, t)[:, None] * 0.6
    rgb = rgb * (1 - rk) + lin(root_hex)[None] * rk
    tk = smooth(0.7, 1.0, t)[:, None] * 0.5
    rgb = rgb * (1 - tk) + lin(tip_hex)[None] * tk
    rough = 0.22 + 0.12 * g                    # round 2: a satin gloss (round 1 read matte)
    rc = np.stack([np.ones(len(t)), rough, np.full(len(t), 0.7) * (1 - 0.3 * g)], axis=1)
    return rgb, rc
