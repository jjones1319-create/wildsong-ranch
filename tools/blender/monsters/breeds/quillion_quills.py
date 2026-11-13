"""Quillion's quills and blade (props; quillion_ultra.build_props).

The mantle's quills (1-hero, 2-turnaround, 4-details 1 and 6): chunky clumps of spines that sweep back from the forehead
over the head and down the back, standing out from the spine-bed in shingled rows, chestnut with lighter cream tips.
Each is a flattened cone along a gently bent axis; the high source is a clump of five strands (lobes that run to the
point, with fine fibre grooves) whose relief bakes into the low cone's normal map. The tail's ruff (4-details 4) is the
same clumps round the tail, swept back to wrap the blade's root. The blade-quill (4-details 4): one long, polished silver
quill curved like a scimitar, round at its root and flattening into a two-edged blade toward the needle tip.

Every quill is rigid; its roots' skin weights carry it (quillion_ultra.prop_weight_regions copies lo_body's weights at
its root, stored per vertex as `qroot`). Every part carries the same per-point attributes (the props mesh keeps only
the common ones): part (1 quill, 2 tail quill, 3 blade, 4 cape, 5 collar, 6 clasp), qt (0 root .. 1 tip, along the
part), qroot (the root on the skin), qrand (0..1 per quill), qside (−1..1 across).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

from lib import common as C
from lib import surface as S
from lib.surface import norm, smooth, v3
from monsters.breeds import quillion_form as F

PART_QUILL, PART_TAILQ, PART_BLADE, PART_CAPE, PART_COLLAR, PART_CLASP = 1.0, 2.0, 3.0, 4.0, 5.0, 6.0
ATTRS = ('part', 'qt', 'qroot', 'qrand', 'qside')

QUILL_SPACING = 0.025       # Poisson spacing of the roots on the mantle
QUILL_BURY = 0.016          # how deep a root sinks into the skin
_LAYOUT: dict = {}


# ----------------------------------------------------------------------------- the layout (cached: hi and lo share it)
def _coarse_body():
    """A coarse copy of the voxel body (the quills' roots are sampled on it), in its own collection; removed after."""
    ob = S.build_body('qz_body', F.all_parts(), 0.007, 3, segments=28, coll='QuillLayout')
    return ob


def _spacing(p: np.ndarray, n: np.ndarray) -> np.ndarray:
    q = F.quill_zone(p, soft=0.004)
    sp = np.full(len(p), QUILL_SPACING)
    # a little denser over the crown and round the face's edge (the halo of the front view)
    sp = sp * (1.0 - 0.12 * smooth(0.6, 0.75, p[:, 2]))
    return np.where(q > 0.5, sp, np.nan)


def layout() -> dict:
    """The quills' roots, normals, directions and sizes (deterministic)."""
    if _LAYOUT:
        return _LAYOUT
    body = _coarse_body()
    P, N = S.scatter(body, _spacing, seed=17, oversample=9.0)
    bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
    rng = np.random.default_rng(23)
    k = len(P)
    z = P[:, 2]
    f = F.quill_flow(P, N)
    # how far each quill stands out of the skin: higher round the face's edge and over the crown (the halo), lower on
    # the back where the rows lie like shingles
    side = np.clip(np.abs(N[:, 0]) * 1.25, 0, 1) * smooth(0.4, 0.52, z)
    crown = smooth(0.7, 0.8, z)
    low = smooth(0.44, 0.3, z)
    fore = smooth(0.0, -0.09, P[:, 1]) * smooth(0.66, 0.74, z)     # the forehead's front rows sweep back over the head
    elev = np.radians(30.0 + 24.0 * side + 4.0 * crown - 10.0 * low + 12.0 * fore) + np.radians(4.0) * rng.normal(0, 1, k).clip(-2, 2)
    d = norm(N * np.sin(elev)[:, None] + f * np.cos(elev)[:, None])
    # a little jitter round the flow
    jit = np.radians(9.0) * rng.normal(0, 1, k).clip(-2, 2)
    across = norm(np.cross(d, N))
    d = norm(d * np.cos(jit)[:, None] + across * np.sin(jit)[:, None])
    # lengths: long on the back and the crown, shorter at the hairline, the lower edge and by the neck
    hl = P[:, 1] - F.hairline_y(z)
    L = (0.13 + 0.03 * smooth(0.4, 0.55, z) * smooth(0.8, 0.66, z) + 0.025 * side) * (1.0 - 0.18 * crown)
    L = L * (0.72 + 0.28 * smooth(0.0, 0.07, hl))
    L = L * (0.78 + 0.22 * smooth(0.3, 0.4, z))
    L = L * (1.0 + 0.13 * rng.normal(0, 1, k).clip(-2, 2))
    W = 0.054 * (1.0 + 0.12 * rng.normal(0, 1, k).clip(-2, 2)) * (0.85 + 0.15 * smooth(0.3, 0.42, z))
    bend = np.radians(8.0 + 6.0 * rng.random(k))
    # the root, sunk under the skin along the normal (found on the coarse body: the real skin is within a few mm)
    root = P - N * QUILL_BURY
    _LAYOUT.update({'P': P, 'N': N, 'root': root, 'D': d, 'F': f, 'L': L, 'W': W, 'bend': bend, 'rand': rng.random(k)})
    bpy.data.objects.remove(body, do_unlink=True)
    del bvh
    C.log(f'quills: {k} on the mantle (spacing {QUILL_SPACING} m)')
    _LAYOUT.update(tail_layout())
    return _LAYOUT


def tail_layout() -> dict:
    """The tail's ruff: clumps round the tail tube from its middle to its end, swept back along it and flaring out, the
    longest at the end where they wrap the blade's root (4-details 4)."""
    a, b, r1, r2 = F.TAIL_TUBE
    a, b = v3(a), v3(b)
    ax = (b - a) / np.linalg.norm(b - a)
    e1 = norm(np.cross(ax, v3((1.0, 0.0, 0.0)))[None])[0]     # up-ish, perpendicular to the tail
    e2 = np.cross(ax, e1)
    rng = np.random.default_rng(41)
    P, N, D, L, W = [], [], [], [], []
    rows = ((0.22, 6, 0.0), (0.42, 7, 0.5), (0.6, 8, 0.0), (0.78, 8, 0.5), (0.93, 8, 0.0))
    for t, n, ph in rows:
        r = r1 + (r2 - r1) * t
        c = a + (b - a) * t
        for i in range(n):
            ang = 2 * math.pi * (i + ph) / n + 0.25 * rng.normal()
            nn = e1 * math.cos(ang) + e2 * math.sin(ang)
            p = c + nn * r
            flare = math.radians(20.0 + 8.0 * t)
            d = ax * math.cos(flare) + nn * math.sin(flare)
            P.append(p)
            N.append(nn)
            D.append(d / np.linalg.norm(d))
            L.append((0.1 + 0.08 * t) * (1.0 + 0.1 * rng.normal()))
            W.append(0.034 + 0.006 * t)
    P, N, D = np.array(P), np.array(N), np.array(D)
    return {'tP': P, 'tN': N, 'troot': P - N * 0.012, 'tD': D, 'tL': np.array(L), 'tW': np.array(W),
            'tbend': np.radians(6.0) * np.ones(len(P)), 'trand': rng.random(len(P))}


# ----------------------------------------------------------------------------- one quill's mesh
def _quill_axis(root, d, n, L, bend, nseg):
    """Points along a quill's gently bent axis (bending back toward the skin, away from its normal, toward the tip)."""
    t = np.linspace(0.0, 1.0, nseg + 1)
    side = n - d * float(d @ n)
    sl = np.linalg.norm(side)
    side = side / sl if sl > 1e-6 else np.cross(d, v3((1.0, 0.0, 0.0)))
    # the axis leaves the root along d and curls back by `bend` at the tip
    ang = bend * t ** 1.6
    pts = []
    pos = root.copy()
    pts.append(pos.copy())
    for i in range(1, nseg + 1):
        a = 0.5 * (ang[i - 1] + ang[i])
        di = d * math.cos(a) - side * math.sin(a)
        pos = pos + di * L * (t[i] - t[i - 1])
        pts.append(pos.copy())
    return np.array(pts), t


def _radius(t: np.ndarray, w: float) -> np.ndarray:
    """The clump's half-width along its length: full near the root, a long soft taper to the point."""
    return 0.5 * w * (0.85 + 0.15 * smooth(0.0, 0.2, t)) * np.clip(1.0 - t, 0, 1) ** 0.62


def quill_mesh(bm, root, d, n, L, W, bend, high: bool, rnd: float, flat: float = 0.6):
    """Add one quill to `bm`; returns its new verts (in order) and each one's (qt, qside)."""
    nsides = 20 if high else 6
    across = np.cross(d, n)
    al = np.linalg.norm(across)
    across = across / al if al > 1e-6 else norm(np.cross(d, v3((0.0, 0.0, 1.0)))[None])[0]
    # rings along the length (the high clump has more toward the point); the tip is one vertex
    t = np.linspace(0.0, 1.0, 19) ** 1.25 if high else np.array([0.0, 0.24, 0.52, 0.8, 1.0])
    full, tf = _quill_axis(root, d, n, L, bend, 24)
    pts = np.stack([np.interp(t, tf, full[:, i]) for i in range(3)], axis=1)
    rad = _radius(t, W)
    verts, info = [], []
    rings = []
    for i in range(len(t) - 1):
        tg = pts[min(i + 1, len(t) - 1)] - pts[max(i - 1, 0)]
        tg = tg / max(np.linalg.norm(tg), 1e-9)
        ex = across - tg * float(across @ tg)
        ex = ex / max(np.linalg.norm(ex), 1e-9)
        ey = np.cross(tg, ex)
        ring = []
        for k in range(nsides):
            phi = 2 * math.pi * k / nsides
            cx, cy = math.cos(phi), math.sin(phi)
            r = rad[i]
            if high:
                # five strands in the clump: lobes that run to the point, a fine fibre groove on each
                lobe = 0.13 * math.cos(5 * phi + rnd * 6.0) * (1.0 - 0.6 * t[i])
                fib = 0.035 * math.cos(17 * phi + rnd * 11.0) * (1.0 - t[i])
                r = r * (1.0 + lobe + fib)
            p = pts[i] + ex * (cx * r) + ey * (cy * r * flat)
            ring.append(bm.verts.new(tuple(p)))
            info.append((t[i], cx))
        rings.append(ring)
    tip = bm.verts.new(tuple(pts[-1]))
    info.append((1.0, 0.0))
    for i in range(len(rings) - 1):
        for k in range(nsides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % nsides], rings[i + 1][(k + 1) % nsides], rings[i + 1][k]))
    for k in range(nsides):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % nsides], tip))
    # the root stays open: it is buried under the skin, never seen
    return info


def _finish(bm, name: str, attrs: dict) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    for k, a in attrs.items():
        S.add_attr(ob, k, np.asarray(a, np.float64))
    return ob


def quills_object(name: str, high: bool) -> bpy.types.Object:
    """Every mantle quill and the tail's ruff in one object (part 1 and 2)."""
    Lo = layout()
    bm = bmesh.new()
    part, qt, qroot, qrand, qside = [], [], [], [], []
    sets = [(PART_QUILL, Lo['root'], Lo['D'], Lo['N'], Lo['L'], Lo['W'], Lo['bend'], Lo['rand'], Lo['P']),
            (PART_TAILQ, Lo['troot'], Lo['tD'], Lo['tN'], Lo['tL'], Lo['tW'], Lo['tbend'], Lo['trand'], Lo['tP'])]
    for pid, R, D, N, L, W, B, RND, P in sets:
        for i in range(len(R)):
            info = quill_mesh(bm, R[i], D[i], N[i], float(L[i]), float(W[i]), float(B[i]), high, float(RND[i]))
            for tq, sd in info:
                part.append(pid)
                qt.append(tq)
                qroot.append(P[i])
                qrand.append(RND[i])
                qside.append(sd)
    ob = _finish(bm, name, {'part': part, 'qt': qt, 'qroot': np.array(qroot), 'qrand': qrand, 'qside': qside})
    ob['prop'] = 'quills'
    C.log(f'{name}: {len(Lo["root"])} + {len(Lo["troot"])} quills, {len(ob.data.polygons)} faces')
    return ob


# ----------------------------------------------------------------------------- the blade-quill
def bezier(s: np.ndarray):
    p0, p1, p2 = (v3(p) for p in F.BLADE_BEZ)
    s = np.asarray(s, np.float64)[:, None]
    pos = (1 - s) ** 2 * p0 + 2 * s * (1 - s) * p1 + s ** 2 * p2
    tan = 2 * (1 - s) * (p1 - p0) + 2 * s * (p2 - p1)
    return pos, norm(tan)


BLADE_W = 0.017             # half-width at its widest (the hero: about 3 cm across)
BLADE_T = 0.0072            # half-thickness at the root


def blade_section(s: np.ndarray):
    """Half-width, half-thickness and roundness along the blade (0 root .. 1 tip)."""
    hw = BLADE_W * (0.85 + 0.15 * smooth(0.0, 0.2, s)) * (1.0 - smooth(0.35, 1.0, s) ** 1.15)
    ht = BLADE_T * np.clip(1.0 - s, 0, 1) ** 0.55 + 0.0006
    rnd = smooth(0.3, 0.0, s)
    return hw, ht, rnd


def blade_object(name: str, high: bool) -> bpy.types.Object:
    nlen, nsides = (140, 48) if high else (26, 12)
    s = np.linspace(0.0, 1.0, nlen + 1) ** 1.12
    pos, tan = bezier(s)
    # the blade lies in the curve's own plane: its faces look along the plane's normal (about ±X), its edges in it
    p0, p1, p2 = (v3(p) for p in F.BLADE_BEZ)
    xax = norm(np.cross(p1 - p0, p2 - p0)[None])[0]
    if xax[0] < 0:
        xax = -xax
    hw, ht, rnd = blade_section(s)
    bm = bmesh.new()
    rings = []
    part, qt, qroot, qrand, qside = [], [], [], [], []
    root = pos[0]
    for i in range(nlen):
        wv = np.cross(xax, tan[i])                       # the blade's width lies in its own plane
        wv = wv / np.linalg.norm(wv)
        ring = []
        for k in range(nsides):
            phi = 2 * math.pi * k / nsides
            u, w = math.cos(phi), math.sin(phi)
            # a lens with two edges (thin at |u| = 1), rounder at the root; a shallow fuller ridge on each face
            lens = (1.0 - abs(u)) ** 0.55
            th = ht[i] * (lens * (1 - rnd[i]) + math.sqrt(max(0.0, 1 - u * u)) * rnd[i])
            if high:
                th *= 1.0 + 0.08 * math.exp(-(u / 0.12) ** 2) * (1 - rnd[i])
            p = pos[i] + wv * (u * hw[i]) + xax * (w * th)
            ring.append(bm.verts.new(tuple(p)))
            part.append(PART_BLADE)
            qt.append(s[i])
            qroot.append(root)
            qrand.append(0.5)
            qside.append(u)
        rings.append(ring)
    tip = bm.verts.new(tuple(pos[-1] + tan[-1] * 0.002))
    part.append(PART_BLADE)
    qt.append(1.0)
    qroot.append(root)
    qrand.append(0.5)
    qside.append(0.0)
    for i in range(len(rings) - 1):
        for k in range(nsides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % nsides], rings[i + 1][(k + 1) % nsides], rings[i + 1][k]))
    for k in range(nsides):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % nsides], tip))
    base = bm.verts.new(tuple(pos[0] - tan[0] * 0.003))
    part.append(PART_BLADE)
    qt.append(0.0)
    qroot.append(root)
    qrand.append(0.5)
    qside.append(0.0)
    for k in range(nsides):
        bm.faces.new((rings[0][(k + 1) % nsides], rings[0][k], base))
    ob = _finish(bm, name, {'part': part, 'qt': qt, 'qroot': np.array(qroot), 'qrand': qrand, 'qside': qside})
    ob['prop'] = 'blade'
    return ob


def orient_out(ob: bpy.types.Object) -> None:
    """Turn every face outward (each part is a closed shell round its own axis)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
