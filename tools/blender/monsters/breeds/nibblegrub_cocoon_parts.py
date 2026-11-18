"""Nibblegrub's cocoon (Art 2.1 Ultra; chatgpt/monsters/27-nibblegrub cocoon-1-hero, cocoon-2-turnaround): the form,
the props' geometry and the paint. Look `nibblegrub-cocoon` (breeds/nibblegrub_cocoon_ultra.py).

A plump silk lemon (0.62 m wide, 0.88 m tall: about Nibblegrub curled into a ball): sheer silk with a strong dusk light
inside (a hot orange-gold heart at the middle front fading into violet and lavender swirls toward the sides, the bottom
and the back), wrapped in broad, flat, frayed cream bands that mostly spiral one way (upper left to lower right seen
from the front) with two crossing; stray fibres stand off it; its top tapers into a gathered silk stalk that wraps the
twig in a broad band; a thick, crooked twig with knots, a side nub, clumps of moss and three leaves.
The meshes:
  - lo_body: the inner core (the chrysalis: glowing from its middle outward, faint folded-wing lines), hidden until the
    shell splits;
  - lo_props: the two shell halves (thick silk, split front to back, each its own closed solid with its own UVs, the
    bands flat on them, a fibrous lining; rigid on shell.L / shell.R, hinged at the top, a bulge bone under each), the
    stray fibres (on the halves), the stalk and its band round the twig (on `body`, the hang point), and the twig with
    its nub and leaves (prop.twig, on root).
Colours (the card's cocoon section): silk #F1E9DA, bands #D9CBB0, inner glow #F29E4C and #5B3F7A. Derived (the
pictures show them, no hex given): the twig's bark from Nibblegrub's eye brown warmed with its segment gold, the cut
wood from its segment gold and cream, the leaves' and the moss's green from its body yellow turned toward green; the
dusk's hot heart is the orange lightened with the silk, its lavender the violet lightened with the silk.
Round 3 (the review): the dusk a soft radial patch over silk, long fibres, soft band edges, a rope of strands
for the stalk, a long tapering neck, short pale stray fibres lying close, cream cut edges.
Round 2 (the review): the dusk painted into the silk's own colour (it showed only as a faint blush), fibre streaks and
stray fibres (smooth cloth), flat, wide, frayed, one-way bands (round ribbed tubes in a diamond net), a lemon shape
(a blunt egg with a sudden neck), a broad band round the twig (two loops read as ears), a thick crooked twig, own UVs
and a finer source (grid and moire patches, dashed seams in the bake).
"""
from __future__ import annotations

import colorsys
import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S

# ----------------------------------------------------------------------------- the form
Z0, H, R = 0.04, 0.96, 0.31                 # the shell's bottom, its height to the neck's top, its widest radius
CENTRE = np.array([0.0, 0.0, 0.47])         # the egg's middle (the inner surface is the outer drawn toward it)
INNER_K = 0.86                              # the shell's thickness: ~4 cm at the waist (polish: the open rim read blade-thin)
# round 3: a lemon whose top tapers on into a long neck (round 2 stepped from a shoulder into a plain tube), the
# bottom pulled to a soft point
_PROF_S = [0.0, 0.015, 0.04, 0.085, 0.16, 0.26, 0.38, 0.5, 0.6, 0.69, 0.77, 0.84, 0.9, 0.95, 0.98, 1.0]
_PROF_F = [0.0, 0.13, 0.27, 0.46, 0.69, 0.87, 0.98, 1.0, 0.95, 0.83, 0.66, 0.47, 0.3, 0.19, 0.12, 0.05]   # (polish) closes into the rope
GAP = 0.0                                   # the halves meet exactly (a gap read as a dark seam down the front)
HIP = (0.0, 0.0, 1.11)                      # the hang point: the stalk meets the twig
TWIG_Z = 1.13
# a thick, crooked twig with two knots and a side nub (round 3: thicker, more crooked)
TWIG = [(-0.45, 0.03, 1.16), (-0.27, -0.02, 1.136), (-0.1, 0.018, 1.13), (0.0, 0.0, TWIG_Z), (0.15, -0.024, 1.14),
        (0.3, 0.014, 1.158), (0.43, -0.016, 1.17)]
TWIG_R = [0.026, 0.032, 0.036, 0.039, 0.041, 0.043, 0.044]
KNOTS = [(-0.2, 2.4), (0.22, 0.6), (0.36, 3.9)]       # (x, angle round the twig) of the knots
NUB = [(0.27, 0.006, 1.16), (0.3, 0.04, 1.2), (0.316, 0.055, 1.228)]
STEM = [(-0.37, 0.016, 1.16), (-0.44, 0.0, 1.195), (-0.51, -0.008, 1.225)]
# the stalk: round 3: a rope of silk strands twisted together, from the neck's top up into the band round the twig
ROPE_Z = (0.93, 1.1)
ROPE_STRANDS = 5
SLEEVE = [(-0.05, 0.0, TWIG_Z), (0.0, 0.0, TWIG_Z), (0.05, 0.0, TWIG_Z)]      # the broad silk band round the twig
SLEEVE_R = [0.053, 0.06, 0.053]
# the bands: (start angle, turns over the height, layer): four spiral one way (from the front: upper left to lower
# right), two cross them; round 3: flatter, their edges soft and frayed (no grey outline)
BANDS = [(0.0, -1.0, 0), (1.57, -1.0, 2), (3.14, -1.0, 0), (4.71, -1.0, 2), (0.9, 0.6, 1), (4.0, 0.6, 3)]
BAND_W, BAND_H = 0.041, 0.0032              # half width (± a quarter), height


def smooth(a: float, b: float, x):
    t = np.clip((np.asarray(x, np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _profile_table(n: int = 2001) -> tuple[np.ndarray, np.ndarray]:
    s = np.linspace(0.0, 1.0, n)
    f = np.interp(s, _PROF_S, _PROF_F)
    k = np.exp(-0.5 * (np.arange(-60, 61) / 22.0) ** 2)
    k /= k.sum()
    fp = np.pad(f, 60, mode='edge')
    fs = np.convolve(fp, k, mode='valid')
    fs[0] = 0.0
    return s, fs


_S, _F = _profile_table()


def shell_r(s) -> np.ndarray:
    """The shell's outer radius (before the bands) at height share s (0 bottom, 1 the neck's top)."""
    return R * np.interp(np.asarray(s, np.float64), _S, _F)


def shell_z(s) -> np.ndarray:
    return Z0 + H * np.asarray(s, np.float64)


def core_profile(gap: float = 0.015) -> tuple[np.ndarray, np.ndarray]:
    """(z, radius) of the inner core: the shell's inner surface (the outer drawn toward CENTRE) less `gap`."""
    s = np.linspace(0.0, 1.0, 801)
    ri = INNER_K * shell_r(s)
    zi = CENTRE[2] + INNER_K * (shell_z(s) - CENTRE[2])
    return zi, np.maximum(ri - gap, 0.0)


def _rng_waves(seed: int, n: int, lo: float, hi: float):
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    return d, 2 * np.pi / rng.uniform(lo, hi, n), rng.uniform(0, 2 * np.pi, n)


_SWIRL = _rng_waves(3302, 6, 0.18, 0.4)


def waves(co: np.ndarray, spec) -> np.ndarray:
    d, f, p = spec
    v = np.zeros(len(co))
    for dd, ff, pp in zip(d, f, p):
        v += np.sin((co @ dd) * ff + pp)
    return v / math.sqrt(len(f) / 2.0)


def wrap_angle(phi, sh) -> np.ndarray:
    """The angle round the egg measured across the main wrap (constant along the main bands' helix)."""
    return np.asarray(phi) - 2 * np.pi * BANDS[0][1] * np.asarray(sh)


def fibres(phi, sh, lam: float = 0.006) -> np.ndarray:
    """Long soft silk fibres (−1..1) along the main wrap, their phases drifting slowly along it. (polish) Whole numbers
    of fibres round the egg, so the pattern is seamless where the two halves meet (the grain broke at the front seam)."""
    a = wrap_angle(phi, sh)
    sh = np.asarray(sh)
    n0 = max(8, int(round(2 * np.pi * 0.26 / lam)))
    v = np.zeros_like(a)
    for k, (m, w) in enumerate(((1.0, 0.5), (1.7, 0.3), (2.9, 0.2))):
        v += w * np.cos(int(round(n0 / m)) * a + 0.6 * np.sin(sh * (13.0 + 5.0 * k) + 1.3 * k))
    # (polish) faded out toward the tip and the neck, where the lines crowd together (a crosshatch moire at the tip)
    return v * smooth(0.06, 0.26, sh) * smooth(0.97, 0.88, sh)


def sheer(phi, sh) -> np.ndarray:
    """A wispy sheer overlay (0..1): long thin veils of lighter silk along the wrap (seamless, as fibres())."""
    a = wrap_angle(phi, sh)
    sh = np.asarray(sh)
    va = 0.5 + 0.5 * np.cos(53 * a + 0.4 * np.sin(sh * 9.0))
    vb = 0.5 + 0.5 * np.cos(31 * a + 0.5 * np.sin(sh * 6.5 + 1.0))
    return smooth(0.55, 0.95, 0.6 * va + 0.4 * vb) * smooth(0.04, 0.17, sh) * smooth(0.97, 0.88, sh)


def band_fields(phi: np.ndarray, s: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(height of the flat bands, their cover 0..1, the fibre relief blended over the bands under each point) at
    points of the egg given by angle, height share and radius. No hard switch where bands cross; the edge is a soft
    shoulder with a slow fray (round 2's fine fray aliased into smears and grey outlines)."""
    dr = np.gradient(_F, _S) * R
    drds = np.interp(s, _S, dr)
    h = np.zeros_like(phi)
    cover = np.zeros_like(phi)
    fib = np.zeros_like(phi)
    wsum = np.full_like(phi, 1e-9)
    for k, (p0, turns, layer) in enumerate(BANDS):
        dphi = (phi - (p0 + 2 * np.pi * turns * s) + np.pi) % (2 * np.pi) - np.pi
        a_round = np.maximum(r, 1e-4) * 2 * np.pi * abs(turns)
        a_up = np.sqrt(H * H + drds * drds)
        cosA = a_up / np.sqrt(a_up * a_up + a_round * a_round)
        d = dphi * np.maximum(r, 1e-4) * cosA * np.sign(turns)
        fade = smooth(0.03, 0.12, s) * smooth(0.995, 0.93, s)
        w = BAND_W * (1.0 + 0.25 * np.sin(2 * np.pi * (1.7 * s + 0.37 * k)) + 0.1 * np.sin(2 * np.pi * (4.3 * s + 0.61 * k)))
        w = w * (0.45 + 0.55 * smooth(0.82, 0.6, s))          # thinner up the neck, where they run into the rope
        fray = 0.07 * np.sin(s * 63.0 + k * 1.3) * np.sin(s * 23.0 + phi * 3.0 + k)
        u = np.abs(d) / w + fray
        ck = np.clip(1.0 - u ** 4, 0.0, 1.0) * fade
        hk = BAND_H * ck
        lift = hk + 0.001 * layer * (hk > 1e-6)
        h = np.maximum(h, lift)
        cover = np.maximum(cover, ck)
        fib += ck * np.cos(2 * np.pi * d / 0.009) * smooth(0.06, 0.26, s)
        wsum += ck
    return h, cover, fib / np.maximum(wsum, 1.0)


# ----------------------------------------------------------------------------- mesh helpers
def mesh_from(name: str, verts: np.ndarray, faces: list) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], faces)
    me.validate(verbose=False)
    me.update()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def tag(ob, pid: int, extra: dict | None = None) -> bpy.types.Object:
    n = len(ob.data.vertices)
    S.add_attr(ob, 'pid', np.full(n, float(pid)))
    for k, v in (extra or {}).items():
        S.add_attr(ob, k, v)
    return ob


# ----------------------------------------------------------------------------- tubes: the stalk, the loops, the twig
def frames_along(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tangents and rotation-minimising normals/binormals along a polyline."""
    t = np.gradient(pts, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    ref = np.array([0.0, 0.0, 1.0]) if abs(t[0][2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    n = [np.cross(t[0], ref)]
    n[0] /= np.linalg.norm(n[0])
    for k in range(1, len(pts)):
        v = n[-1] - t[k] * (n[-1] @ t[k])
        n.append(v / np.linalg.norm(v))
    n = np.array(n)
    return t, n, np.cross(t, n)


def tube(name: str, pts, radii, seg: int, rings_per_m: float, twist: float = 0.0, ridges: int = 0, ridge_h: float = 0.0,
         caps: str = 'round', bumps=None) -> tuple[bpy.types.Object, np.ndarray]:
    """A closed tube along a smooth polyline (Catmull-Rom through `pts`), radius interpolated from `radii`; optional
    twisted ridges (the stalk's strands, the bark's grooves); caps 'round' (domes) or 'flat' at the far end."""
    P = np.array(pts, np.float64)
    L = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
    n = max(8, int(L * rings_per_m))
    # Catmull-Rom
    Pp = np.concatenate([P[:1] * 2 - P[1:2], P, P[-1:] * 2 - P[-2:-1]])
    u = np.linspace(0, len(P) - 1, n + 1)
    k = np.minimum(u.astype(int), len(P) - 2)
    f = (u - k)[:, None]
    p0, p1, p2, p3 = Pp[k], Pp[k + 1], Pp[k + 2], Pp[k + 3]
    axis = 0.5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)
    rad = np.interp(u, np.arange(len(radii)), radii)
    t, nn, bb = frames_along(axis)
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    verts, faces = [], []
    tu, tang, tcap = [], [], []
    for i in range(n + 1):
        a = ang + twist * 2 * np.pi * i / n
        tu.extend([i / n] * seg)
        tang.extend(list(a))
        tcap.extend([0.0] * seg)
        rr = rad[i] * (1.0 + (ridge_h * np.cos(ridges * a) if ridges else 0.0))
        if bumps is not None:
            rr = rr + bumps(axis[i], a)
        ring = axis[i][None] + rr[:, None] * (np.cos(ang)[:, None] * nn[i][None] + np.sin(ang)[:, None] * bb[i][None]) if np.ndim(rr) else \
            axis[i][None] + rr * (np.cos(ang)[:, None] * nn[i][None] + np.sin(ang)[:, None] * bb[i][None])
        verts.extend(ring)
    for i in range(n):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    nv = len(verts)
    # caps: a dome at the start, a dome or a flat disc at the end (each a pole fan)
    for end, i0, sgn in ((0, 0, -1.0), (1, n, 1.0)):
        c = axis[i0] + t[i0] * sgn * (rad[i0] * (0.0 if (end == 1 and caps == 'flat') else 0.6))
        if end == 1 and caps == 'flat':
            # a flat disc: one ring a hair inside, then the pole
            verts.extend(axis[i0][None] + 0.82 * rad[i0] * (np.cos(ang)[:, None] * nn[i0][None] + np.sin(ang)[:, None] * bb[i0][None]))
            tu.extend([1.0] * seg)
            tang.extend([0.0] * seg)
            tcap.extend([1.0] * seg)
            base = nv
            for j in range(seg):
                a, b = i0 * seg + j, i0 * seg + (j + 1) % seg
                faces.append((a, b, base + (j + 1) % seg, base + j) if sgn > 0 else (b, a, base + j, base + (j + 1) % seg))
            verts.append(c)
            tu.append(1.0)
            tang.append(0.0)
            tcap.append(1.0)
            pole = base + seg
            for j in range(seg):
                a, b = base + j, base + (j + 1) % seg
                faces.append((a, b, pole) if sgn > 0 else (b, a, pole))
            nv = len(verts)
        else:
            verts.append(c)
            tu.append(float(end))
            tang.append(0.0)
            tcap.append(0.0)
            pole = nv
            for j in range(seg):
                a, b = i0 * seg + j, i0 * seg + (j + 1) % seg
                faces.append((a, b, pole) if sgn > 0 else (b, a, pole))
            nv += 1
    ob = mesh_from(name, np.array(verts), faces)
    S.add_attr(ob, 'tu', np.array(tu))
    S.add_attr(ob, 'tang', np.array(tang))
    S.add_attr(ob, 'tcap', np.array(tcap))
    return ob, axis


def ring(name: str, centre, axis_dir, R_: float, r_: float, nu: int, nv: int) -> bpy.types.Object:
    """A torus round `axis_dir` (the stalk's loop round the twig)."""
    a = np.asarray(axis_dir, np.float64)
    a /= np.linalg.norm(a)
    e1 = np.cross(a, [0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.cross(a, [1.0, 0.0, 0.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    verts, faces = [], []
    for i in range(nu):
        th = 2 * np.pi * i / nu
        d = np.cos(th) * e1 + np.sin(th) * e2
        for j in range(nv):
            ph = 2 * np.pi * j / nv
            rr = r_ * (1.0 + 0.12 * np.cos(4 * ph + 3 * th))
            verts.append(np.asarray(centre) + d * (R_ + rr * np.cos(ph)) + a * rr * np.sin(ph))
    for i in range(nu):
        for j in range(nv):
            i2, j2 = (i + 1) % nu, (j + 1) % nv
            faces.append((i * nv + j, i * nv + j2, i2 * nv + j2, i2 * nv + j))
    ob = mesh_from(name, np.array(verts), faces)
    S.orient_away(ob, lambda fc: np.asarray(centre)[None] + ((fc - centre) - np.outer((fc - centre) @ a, a)) /
                  np.maximum(np.linalg.norm((fc - centre) - np.outer((fc - centre) @ a, a), axis=1, keepdims=True), 1e-9) * R_)
    return ob


def leaf(name: str, base, direction, up, L: float, W: float, curl: float, nu: int, nv: int) -> bpy.types.Object:
    """A closed, thin leaf: a flattened tube swept along its midrib (pointed at both ends), folded a little along
    the rib and curled."""
    d = np.asarray(direction, np.float64)
    d /= np.linalg.norm(d)
    up = np.asarray(up, np.float64)
    up = up - d * (up @ d)
    up /= np.linalg.norm(up)
    side = np.cross(d, up)
    verts, faces = [], []
    us = np.linspace(0.0, 1.0, nu + 1)
    for i, u in enumerate(us):
        w = W * 0.5 * math.sin(math.pi * u ** 0.85) ** 0.9
        th = 0.0045 * math.sin(math.pi * u) + 0.0006
        bend = curl * L * u * u
        c = np.asarray(base) + d * (L * u) + up * bend
        for j in range(nv):
            a = 2 * np.pi * j / nv
            cv, sv = math.cos(a), math.sin(a)
            fold = 0.16 * W * abs(cv) * math.sin(math.pi * u)
            verts.append(c + side * (w * cv) + up * (th * sv + fold))
    # (side, up, d) is left-handed, so the rings run clockwise round d: the quads and the end fans are wound to match
    for i in range(nu):
        for j in range(nv):
            a, b = i * nv + j, i * nv + (j + 1) % nv
            faces.append((a, a + nv, b + nv, b))
    p0 = len(verts)
    verts.append(np.asarray(base) - d * 0.0008)
    p1 = len(verts)
    verts.append(np.asarray(base) + d * (L * 1.0008) + up * (curl * L))
    for j in range(nv):
        a, b = j, (j + 1) % nv
        faces.append((a, b, p0))
        a, b = nu * nv + j, nu * nv + (j + 1) % nv
        faces.append((b, a, p1))
    ob = mesh_from(name, np.array(verts), faces)
    co, _ = S.mesh_arrays(ob)
    q = co - np.asarray(base)[None]
    S.add_attr(ob, 'leafu', np.clip(q @ d / L, 0, 1))
    S.add_attr(ob, 'leafv', (q @ side) / (0.5 * W))
    return ob


# ----------------------------------------------------------------------------- the shell halves
def shell_half(name: str, side: int, high: bool) -> bpy.types.Object:
    """One closed half of the thick silk shell (side +1: x > 0, the monster's left), the bands flat on it, long fibres
    in the high source (round 3: only long, low streaks in the geometry; the fine fibres are paint: the fine relief
    beat into a crosshatch moire). Its own UVs (one island per surface). Round 3: the cut faces and the rims have
    their own vertices (attribute `cut`), so they take a cream, lit-from-within colour without touching the outer
    skin's (they read as a grey blade). Attributes: cover, outer, cut, sh, phi."""
    nphi, ns = (480, 560) if high else (56, 80)
    half = np.pi / 2 - GAP / R
    phis = np.linspace(-half, half, nphi + 1) + (0.0 if side > 0 else np.pi)
    ss = np.concatenate([[0.0004, 0.003], np.linspace(0.008, 1.0, ns - 1)])
    PH, SS = np.meshgrid(phis, ss, indexing='ij')
    r = shell_r(SS)
    z = shell_z(SS)
    dr = np.gradient(shell_r(ss), ss)[None, :] * np.ones_like(SS)
    nr, nz = H, -dr
    ln = np.sqrt(nr * nr + nz * nz)
    nr, nz = nr / ln, nz / ln
    h, cover, fib = band_fields(PH, SS, r)
    o = np.stack([r * np.cos(PH), r * np.sin(PH), z], axis=-1)
    lift = h.copy()
    lining = np.zeros_like(h)
    if high:
        lift = lift + 0.0005 * fib * (cover > 0.02) + (1.0 - np.clip(cover, 0, 1)) * 0.0007 * fibres(PH, SS, 0.012)
        lining = 0.0006 * fibres(PH, SS, 0.014)
    nrm = np.stack([nr * np.cos(PH), nr * np.sin(PH), nz], axis=-1)
    out = o + nrm * lift[..., None]
    inner = CENTRE + (o - CENTRE) * INNER_K - nrm * lining[..., None]
    J = ns + 1
    no, ni = out.reshape(-1, 3), inner.reshape(-1, 3)
    n1 = len(no)
    rbar = shell_r(ss)
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(shell_z(ss)), np.diff(rbar)))])
    phl = phis - phis[0]
    thick = 0.03
    verts = [no, ni]
    nv = 2 * n1
    faces, uvs = [], []

    def vo(i, j):
        return i * J + j

    def vi(i, j):
        return n1 + i * J + j

    def uo(i, j):
        return ((phl[i] - 0.5 * phl[-1]) * max(rbar[j], 0.06), arc[j])     # (polish) more texels at the tip
    for i in range(nphi):
        for j in range(J - 1):
            faces.append((vo(i, j), vo(i + 1, j), vo(i + 1, j + 1), vo(i, j + 1)))
            uvs.append([uo(i, j), uo(i + 1, j), uo(i + 1, j + 1), uo(i, j + 1)])
            faces.append((vi(i, j), vi(i, j + 1), vi(i + 1, j + 1), vi(i + 1, j)))
            uvs.append([(a + 4.0, b) for a, b in (uo(i, j), uo(i, j + 1), uo(i + 1, j + 1), uo(i + 1, j))])
    # the rims, on their own vertices: a strip of (outer, inner) pairs each
    cut_start = nv

    def strip(pairs):
        nonlocal nv
        pts = []
        for a, b in pairs:
            pts.append(no[a])
            pts.append(ni[b - n1] if b >= n1 else ni[b])
        verts.append(np.array(pts))
        base = nv
        nv += len(pts)
        return base
    # the cut at the start (i = 0) and at the end (i = nphi): along j
    b0 = strip([(vo(0, j), vi(0, j)) for j in range(J)])
    b1 = strip([(vo(nphi, j), vi(nphi, j)) for j in range(J)])
    for j in range(J - 1):
        o0, i0, o1, i1 = b0 + 2 * j, b0 + 2 * j + 1, b0 + 2 * j + 2, b0 + 2 * j + 3
        faces.append((o0, o1, i1, i0))
        uvs.append([(8.0, arc[j]), (8.0, arc[j + 1]), (8.0 + thick, arc[j + 1]), (8.0 + thick, arc[j])])
        o0, i0, o1, i1 = b1 + 2 * j, b1 + 2 * j + 1, b1 + 2 * j + 2, b1 + 2 * j + 3
        faces.append((o0, i0, i1, o1))
        uvs.append([(10.0, arc[j]), (10.0 + thick, arc[j]), (10.0 + thick, arc[j + 1]), (10.0, arc[j + 1])])
    # the top rim (j = J − 1) and the bottom rim (j = 0): along i
    bt = strip([(vo(i, J - 1), vi(i, J - 1)) for i in range(nphi + 1)])
    bb = strip([(vo(i, 0), vi(i, 0)) for i in range(nphi + 1)])
    for i in range(nphi):
        a0, a1 = phl[i] * rbar[-1], phl[i + 1] * rbar[-1]
        o0, i0, o1, i1 = bt + 2 * i, bt + 2 * i + 1, bt + 2 * i + 2, bt + 2 * i + 3
        faces.append((o0, o1, i1, i0))
        uvs.append([(12.0 + a0, 0.0), (12.0 + a1, 0.0), (12.0 + a1, thick), (12.0 + a0, thick)])
        c0, c1 = phl[i] * 0.01, phl[i + 1] * 0.01
        o0, i0, o1, i1 = bb + 2 * i, bb + 2 * i + 1, bb + 2 * i + 2, bb + 2 * i + 3
        faces.append((o0, i0, i1, o1))
        uvs.append([(14.0 + c0, 0.0), (14.0 + c0, thick), (14.0 + c1, thick), (14.0 + c1, 0.0)])
    allv = np.concatenate(verts)
    ob = mesh_from(name, allv, faces)
    me = ob.data
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', np.array([c for f in uvs for c in f], np.float32).ravel())
    ob['own_uv'] = True
    me.set_sharp_from_angle(angle=np.radians(50.0))
    ncut = len(allv) - cut_start
    grid = lambda a: np.concatenate([a.reshape(-1), a.reshape(-1)])

    def rim_vals(a):
        a2 = a.reshape(nphi + 1, J)
        parts = [np.repeat(a2[0, :], 2), np.repeat(a2[nphi, :], 2), np.repeat(a2[:, J - 1], 2), np.repeat(a2[:, 0], 2)]
        return np.concatenate(parts)
    tag(ob, 1 if side > 0 else 2, {
        'cover': np.concatenate([grid(cover), np.zeros(ncut)]),
        'outer': np.concatenate([np.ones(n1), np.zeros(n1), np.zeros(ncut)]),
        'cut': np.concatenate([np.zeros(2 * n1), np.ones(ncut)]),
        'sh': np.concatenate([grid(SS), rim_vals(SS)]), 'phi': np.concatenate([grid(PH), rim_vals(PH)])})
    return ob


# ----------------------------------------------------------------------------- stray fibres
def wisps(name: str, side: int, high: bool, n: int = 30) -> bpy.types.Object:
    """Stray silk fibres (round 3: pale, short, many, lying close to the surface and thinning to nothing at both tips;
    round 2's standing loops read as wire staples and springs): low arcs 2-4 cm long along the wrap, 2-6 mm up."""
    rng = np.random.default_rng(4100 + side)
    objs = []
    for k in range(n):
        s0 = rng.uniform(0.12, 0.86)
        # (polish) a few, on the sides and the back only (on the face they read as grey dashes)
        ph0 = rng.uniform(-0.5, np.pi / 2 - 0.06) * side + (0.0 if side > 0 else np.pi)
        L = rng.uniform(0.02, 0.042)
        rise = rng.uniform(0.0005, 0.0015)          # (polish) lying flat (they hooked at the outline)
        dirs = rng.choice([-1.0, 1.0])
        r0 = max(float(shell_r(s0)), 0.05)
        pts = []
        for q in np.linspace(0.0, 1.0, 5):
            s = s0 + dirs * 0.45 * L / H * q
            ph = ph0 - dirs * (L / r0) * q * 0.85
            rr = float(shell_r(s)) + BAND_H + 0.0012 + rise * math.sin(math.pi * q)
            pts.append((rr * math.cos(ph), rr * math.sin(ph), float(shell_z(s))))
        ob, _ax = tube(f'{name}_{k}', pts, [0.0005, 0.0013, 0.0005], 5 if high else 3, 300 if high else 40)
        objs.append(ob)
    from lib import mesh as M
    ob = M.join_meshes(objs, name)
    ob.data.name = name
    tag(ob, 1 if side > 0 else 2, {'wisp': np.ones(len(ob.data.vertices))})
    return ob


def rope(name: str, high: bool) -> tuple[bpy.types.Object, list]:
    """The stalk (round 3): silk strands twisted into a rope from the neck's top up into the band round the twig, round
    a core strand."""
    objs = []
    z0, z1 = ROPE_Z
    zs = np.linspace(z0, z1, 7)
    for k in range(ROPE_STRANDS):
        pts = []
        for q, z in enumerate(zs):
            u = q / (len(zs) - 1)
            a = 2 * np.pi * k / ROPE_STRANDS + 2 * np.pi * 0.7 * u
            rad = 0.03 - 0.012 * u
            pts.append((rad * math.cos(a), rad * math.sin(a), float(z)))
        ob, _ = tube(f'{name}_s{k}', pts, [0.02, 0.016, 0.014], 14 if high else 7, 300 if high else 60)
        objs.append(ob)
    core, ax = tube(f'{name}_core', [(0.0, 0.0, z0), (0.0, 0.0, 0.5 * (z0 + z1)), (0.0, 0.0, z1)], [0.03, 0.024, 0.02],
                    16 if high else 8, 300 if high else 40)
    objs.append(core)
    from lib import mesh as M
    ob = M.join_meshes(objs, name)
    ob.data.name = name
    return ob, ax


# ----------------------------------------------------------------------------- colours and paint
SILK, BANDC, ORANGE, VIOLET = '#F1E9DA', '#D9CBB0', '#F29E4C', '#5B3F7A'


def _turn(h: str, deg: float, sat: float = 1.0, val: float = 1.0) -> str:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb((hh + deg / 360.0) % 1.0, min(1.0, ss * sat), min(1.0, vv * val))
    return '#%02x%02x%02x' % tuple(int(round(255 * x)) for x in (r, g, b))


BARK = C.mix_hex('#3B2F2F', '#D9A94F', 0.38)            # Nibblegrub's eye brown warmed with its segment gold
BARK_DK = C.shade_hex(BARK, 0.62)
WOOD = C.mix_hex('#D9A94F', '#FFF0C2', 0.45)            # the cut end: its gold and cream
LEAF = _turn('#F2D27A', 52.0, 1.25, 0.72)               # its body yellow turned toward green
LEAF_HI = _turn('#F2D27A', 40.0, 1.0, 0.92)
MOSS = _turn('#F2D27A', 38.0, 1.3, 0.78)
HOT = C.mix_hex(ORANGE, '#FFE7B0', 0.35)                # the dusk's heart: the card's orange, lightened toward gold
LAVENDER = C.mix_hex(VIOLET, SILK, 0.5)                 # the card's violet lightened with the silk
SOFT_VIOLET = C.mix_hex(VIOLET, SILK, 0.3)
CREAM_LIT = C.mix_hex(SILK, '#FFF6E6', 0.4)             # silk lit from within (the cut edges, the lining)


def L(h: str) -> np.ndarray:
    return S.v3(C.lin_rgb(h))


def mix(rgb: np.ndarray, k, h) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    return rgb * (1.0 - k[:, None]) + L(h)[None] * k[:, None]


def heat_of(phi, sh) -> np.ndarray:
    """0..1: the inner light's hot spot, a soft radial patch at the front (−Y) centre, mid-height (round 3)."""
    dphi = (np.asarray(phi) + np.pi / 2 + np.pi) % (2 * np.pi) - np.pi
    return np.exp(-(dphi / 0.95) ** 2 - ((np.asarray(sh) - 0.5) / 0.24) ** 2)


def dusk_tint(co, phi, sh) -> tuple[np.ndarray, np.ndarray]:
    """The inner light seen through the silk (cocoon-1-hero): the silk the base everywhere; over it a soft radial
    #F29E4C patch at the front centre fading to #5B3F7A toward the sides, the bottom and the back, in soft swirls, and
    pale silk at the top and the rims. Returns (the tint's colour, its strength)."""
    heat = heat_of(phi, sh)
    sw = 0.5 + 0.5 * waves(co, _SWIRL)
    n = len(co)
    col = mix(np.tile(L(SOFT_VIOLET), (n, 1)), 0.5 * sw, LAVENDER)
    col = mix(col, smooth(0.15, 0.6, heat), ORANGE)
    col = mix(col, smooth(0.6, 0.95, heat), HOT)
    haze = (0.42 + 0.2 * sw) * smooth(0.02, 0.1, sh) * (1.0 - smooth(0.74, 0.9, sh))
    amt = np.maximum(haze, 0.85 * smooth(0.0, 0.7, heat))
    return col, amt


def paint_core(co: np.ndarray, vn: np.ndarray):
    """The chrysalis inside: it glows from its middle outward (round 3: a small hot heart in front of its middle, an
    orange ring round it, violet at its edges; round 2 read as an opaque mango), with faint folded-wing lines."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    n = len(co)
    q = (co - np.array([0.0, -0.1, 0.5])) / np.array([0.19, 0.21, 0.24])
    heart = np.exp(-(q ** 2).sum(axis=1))
    q2 = (co - np.array([0.0, -0.05, 0.5])) / np.array([0.25, 0.28, 0.3])
    body = np.exp(-(q2 ** 2).sum(axis=1))
    # (final round) its edges a lavender haze, not dark violet (it read as a plum or a mango), the hot heart larger
    rgb = mix(np.tile(L(SOFT_VIOLET), (n, 1)), 0.55 * (0.5 + 0.5 * waves(co, _SWIRL)), LAVENDER)
    rgb = mix(rgb, smooth(0.1, 0.55, body), ORANGE)
    rgb = mix(rgb, smooth(0.15, 0.75, heart), HOT)
    rgb = mix(rgb, 0.45 * smooth(0.55, 1.0, heart), '#FFF3D6')
    front = smooth(0.0, -0.1, y)
    lines = np.zeros(n)
    for s in (1, -1):
        zz = np.clip((0.78 - z) / 0.6, 0.0, 1.0)
        for k, wk in ((1.0, 0.0045), (0.68, 0.003), (0.38, 0.003)):
            xc = s * (0.025 + k * 0.17 * np.sin(np.pi * zz ** 0.9))
            lines = np.maximum(lines, smooth(wk + 0.003, wk, np.abs(x - xc)) * (z > 0.2) * (z < 0.78))
    rgb = mix(rgb, 0.4 * lines * front, C.mix_hex(LAVENDER, SILK, 0.4))
    glow = 0.18 + 0.3 * body + 0.45 * heart
    return rgb, np.full(n, 0.72), np.zeros(n), glow


def paint_shell(ob) -> tuple:
    co, vn = S.mesh_arrays(ob)
    n = len(co)
    outer = S.attr_array(ob, 'outer') > 0.5
    cut = S.attr_array(ob, 'cut') > 0.5
    cover = np.clip(S.attr_array(ob, 'cover'), 0.0, 1.0)
    phi, sh = S.attr_array(ob, 'phi'), S.attr_array(ob, 'sh')
    fb = fibres(phi, sh)
    sv = sheer(phi, sh)
    heat = heat_of(phi, sh)
    # the panels: silk, the dusk tint over it, fine fibres and a wispy sheer veil of lighter silk on top
    col, amt = dusk_tint(co, phi, sh)
    panel = mix(np.tile(L(SILK), (n, 1)), amt, '#000000') + col * amt[:, None]
    panel = mix(panel, 0.35 * sv + 0.08 * (0.5 + 0.5 * fb), SILK)
    # the bands: cream, fibres along them, lit from behind over the hot spot, a soft fray into the panel (no outline)
    # (polish) no wrap-direction fibres painted on the bands (they crossed the bands' own relief: a crosshatch)
    band = mix(np.tile(L(BANDC), (n, 1)), 0.12, SILK)
    band = mix(band, 0.4 * smooth(0.2, 0.85, heat), C.mix_hex(ORANGE, SILK, 0.45))
    ck = smooth(0.15, 0.7, cover)
    rgb = panel * (1.0 - ck[:, None]) + band * ck[:, None]
    shade = smooth(0.0, 0.15, cover) * (1.0 - smooth(0.15, 0.45, cover))
    rgb = rgb * (1.0 - 0.07 * shade)[:, None]
    # the lining: warm silk lit from within, fibrous; the cut faces and rims cream, lit (round 2: a grey blade)
    lin = mix(np.tile(L(CREAM_LIT), (n, 1)), 0.08 + 0.12 * heat, ORANGE) * (1.0 + 0.05 * fb)[:, None]     # (polish) pale silk
    ins = (~outer) & (~cut)
    rgb[ins] = lin[ins]
    rgb[cut] = (np.tile(L(CREAM_LIT), (n, 1)) * (1.0 + 0.05 * fb)[:, None])[cut]
    # light painted in: the top a little paler, the underside a warm shade (never grey)
    rgb = mix(rgb, 0.1 * smooth(0.2, 0.95, vn[:, 2]) * outer, '#FFFBF4')
    rgb = mix(rgb, 0.1 * smooth(-0.1, -0.9, vn[:, 2]) * outer, C.mix_hex(BANDC, ORANGE, 0.15))
    rough = np.where(cover > 0.5, 0.62, 0.72)
    coat = np.zeros(n)
    # the glow: the hot heart moderate (and the bands over it a little), the lining and the cut faces lit faintly
    glow = np.where(outer, 0.42 * heat ** 1.5 * (1.0 - 0.6 * ck), 0.0)
    glow = np.where(ins, 0.3 + 0.1 * heat, glow)          # (polish) the lining read grey-taupe when open
    glow = np.where(cut, 0.35, glow)
    return rgb, rough, coat, glow


def paint_wisps(co: np.ndarray, vn: np.ndarray):
    n = len(co)
    rgb = np.tile(L(SILK), (n, 1))
    return rgb, np.full(n, 0.85), np.zeros(n), np.full(n, 0.12)     # (polish) cream, matte, lit a little (no dark core)


def paint_stalk(co: np.ndarray, vn: np.ndarray, strand: np.ndarray):
    n = len(co)
    rgb = mix(np.tile(L(SILK), (n, 1)), 0.35 * strand, BANDC)
    rgb = mix(rgb, 0.1 * smooth(-0.1, -0.9, vn[:, 2]), C.mix_hex(BANDC, ORANGE, 0.15))
    low = smooth(1.0, 0.96, co[:, 2])                    # its foot, seen when the shell opens, lit from within
    rgb = mix(rgb, 0.5 * low, CREAM_LIT)
    return rgb, np.full(n, 0.68), np.zeros(n), 0.25 * low


def paint_twig(co: np.ndarray, vn: np.ndarray, groove: np.ndarray, cap: np.ndarray, capr: np.ndarray):
    n = len(co)
    rgb = mix(np.tile(L(BARK), (n, 1)), 0.6 * groove, BARK_DK)
    rgb = mix(rgb, 0.2 * smooth(0.3, 1.0, vn[:, 2]), C.mix_hex(BARK, WOOD, 0.4))
    # moss in clumps on the top
    moss = np.zeros(n)
    for mx, mr in ((-0.33, 0.04), (-0.12, 0.032), (0.11, 0.034), (0.34, 0.036)):
        d = np.hypot(co[:, 0] - mx, (co[:, 1] - 0.0) * 1.5)
        moss = np.maximum(moss, smooth(mr, mr * 0.45, d))
    moss = moss * smooth(0.15, 0.6, vn[:, 2]) * smooth(0.25, 0.7, 0.5 + 0.5 * waves(co * 4.0, _SWIRL))
    rgb = mix(rgb, moss, MOSS)
    rings = 0.5 + 0.5 * np.cos(2 * np.pi * capr / 0.0055)
    wood = mix(np.tile(L(WOOD), (n, 1)), 0.35 * rings * smooth(0.002, 0.006, capr), C.shade_hex(WOOD, 0.78))
    rgb = rgb * (1.0 - cap[:, None]) + wood * cap[:, None]
    rough = np.where(moss > 0.5, 0.9, 0.82)
    return rgb, rough, np.zeros(n), np.zeros(n)


def paint_leaf(co: np.ndarray, vn: np.ndarray, u: np.ndarray, v: np.ndarray):
    n = len(co)
    rgb = mix(np.tile(L(LEAF), (n, 1)), 0.35 * smooth(0.0, 0.9, vn[:, 2]), LEAF_HI)
    rib = smooth(0.09, 0.03, np.abs(v)) * smooth(0.95, 0.7, u)
    veins = smooth(0.82, 0.97, np.cos(2 * np.pi * (u * 6.0 - np.abs(v) * 0.9))) * smooth(0.95, 0.6, np.abs(v)) * smooth(0.1, 0.25, np.abs(v))
    rgb = mix(rgb, 0.6 * np.maximum(rib, 0.5 * veins), LEAF_HI)
    return rgb, np.full(n, 0.45), np.full(n, 0.2), np.zeros(n)
