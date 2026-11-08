"""Rammerjack Ultra: the hard parts and the shaped slabs (docs/ART_2_DETAIL.md §9; chatgpt/monsters/08-rammerjack/).

  - the horns: two ridged spiral tubes from the top of the head up, back, out, down and forward to a blunt tip beside
    the cheek (2-turnaround.png), with growth rings (geometry on both meshes; fine grain on the high one only);
  - the rope: five bands of two tight loops round each horn, a three-strand twisted rope on the high mesh, a plain
    tube on the game mesh (the twist is baked);
  - the scarf: a thick knitted band round the neck (tilted: high at the nape, low in front), a knot at the front-left,
    one hanging end lying on the chest and a short fringe of seven tassels;
  - the ear slabs and the cloven hooves, joined into the voxel body (`body_extras`).

Everything is numpy and bmesh; metres, the monster faces −Y, Z is up, +X is its left. Each prop object carries a
`part` attribute (PART_*) and its own parameters (`ridge`, `strand`, `knit`, …) for the paint.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3

PART_HORN, PART_ROPE, PART_SCARF, PART_FRINGE = 1.0, 2.0, 3.0, 4.0


# ----------------------------------------------------------------------------- curves
def catmull_rom(ctrl: np.ndarray, n: int) -> np.ndarray:
    """A centripetal Catmull-Rom curve through the control points, `n` samples (ends extrapolated)."""
    P = np.asarray(ctrl, np.float64)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    segs = len(P) - 3
    per = max(2, n // segs)
    for i in range(segs):
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        t0 = 0.0
        t1 = t0 + np.linalg.norm(p1 - p0) ** 0.5
        t2 = t1 + np.linalg.norm(p2 - p1) ** 0.5
        t3 = t2 + np.linalg.norm(p3 - p2) ** 0.5
        for t in np.linspace(t1, t2, per, endpoint=i == segs - 1):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    return np.array(out)


class Curve:
    """An arc-length parametrised polyline with rotation-minimising frames (T, N, B)."""

    def __init__(self, pts: np.ndarray, up=(0.0, 0.0, 1.0)):
        pts = np.asarray(pts, np.float64)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        self.s = np.concatenate([[0.0], np.cumsum(seg)])
        self.length = float(self.s[-1])
        self.pts = pts
        T = np.gradient(pts, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        N = np.zeros_like(T)
        n0 = np.cross(T[0], v3(up))
        if np.linalg.norm(n0) < 1e-6:
            n0 = np.cross(T[0], v3((1, 0, 0)))
        N[0] = n0 / np.linalg.norm(n0)
        for i in range(1, len(T)):
            n = N[i - 1] - T[i] * (N[i - 1] @ T[i])
            N[i] = n / max(np.linalg.norm(n), 1e-9)
        self.T, self.N = T, N
        self.B = np.cross(T, N)

    def at(self, s):
        """Point and frame at arc length(s) `s` (array)."""
        s = np.clip(np.asarray(s, np.float64), 0.0, self.length)
        def interp(a):
            return np.stack([np.interp(s, self.s, a[:, k]) for k in range(3)], axis=-1)
        P, T, N = interp(self.pts), interp(self.T), interp(self.N)
        T /= np.linalg.norm(T, axis=-1, keepdims=True)
        N = N - T * (N * T).sum(-1, keepdims=True)
        N /= np.linalg.norm(N, axis=-1, keepdims=True)
        return P, T, N, np.cross(T, N)


def grid_object(name: str, P: np.ndarray, closed_u: bool, caps: tuple[bool, bool] = (False, False), attrs: dict | None = None,
                flip: bool = False, closed_v: bool = False) -> bpy.types.Object:
    """A quad grid from points P (rows × cols × 3): rows along the length (closed_v wraps them: a torus), cols around
    (closed_u wraps them); caps close the first / last ring with a fan. `attrs` {name: rows × cols (× 3) array} become
    point attributes (caps' centre vertices take their ring's mean). Closed results get outward normals."""
    rows, cols = P.shape[:2]
    bm = bmesh.new()
    V = [[bm.verts.new(P[j, i]) for i in range(cols)] for j in range(rows)]
    extra = []
    nc = cols if closed_u else cols - 1
    nr = rows if closed_v else rows - 1
    for j in range(nr):
        j2 = (j + 1) % rows
        for i in range(nc):
            i2 = (i + 1) % cols
            q = (V[j][i], V[j][i2], V[j2][i2], V[j2][i])
            bm.faces.new(q[::-1] if flip else q)
    for end, on in ((0, caps[0]), (rows - 1, caps[1])):
        if not on or closed_v:
            continue
        c = bm.verts.new(P[end].mean(axis=0))
        extra.append(end)
        for i in range(cols):
            i2 = (i + 1) % cols
            f = (V[end][i], V[end][i2], c) if end == rows - 1 else (V[end][i2], V[end][i], c)
            bm.faces.new(f[::-1] if flip else f)
    bm.normal_update()
    if closed_u:
        # the grid is wound consistently by construction (the caps too); only the overall sign depends on the
        # parametrisation: flip everything when the faces point toward their ring's centre. (recalc_face_normals
        # guessed wrong on the thin, curved scarf end: it shaded pale in the game, round 1.)
        Pa = np.asarray(P, np.float64)
        centre = Pa.mean(axis=1)
        jj = np.arange(nr)
        ii = np.arange(nc)
        a = Pa[jj][:, ii]
        b = Pa[jj][:, (ii + 1) % cols]
        c3 = Pa[(jj + 1) % rows][:, (ii + 1) % cols]
        d4 = Pa[(jj + 1) % rows][:, ii]
        nrm = np.cross(b - a, d4 - a) * (-1.0 if flip else 1.0)
        f_c = (a + b + c3 + d4) * 0.25
        dots = float((nrm * (f_c - centre[jj][:, None, :])).sum())
        if dots < 0:
            for f in bm.faces:
                f.normal_flip()
        bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    for k, a in (attrs or {}).items():
        a = np.asarray(a, np.float64)
        flat = a.reshape(rows * cols, -1) if a.ndim == 3 else a.reshape(rows * cols)
        ext = [a[e].mean(axis=0) for e in extra]
        if ext:
            flat = np.concatenate([flat, np.array(ext).reshape(len(ext), *flat.shape[1:])])
        S.add_attr(ob, k, flat)
    return ob


def join(objs: list[bpy.types.Object], name: str, attrs: tuple[str, ...]) -> bpy.types.Object:
    from lib import mesh as M
    ob = M.join_meshes(objs, name)
    for a in attrs:
        if all(a in o.data.attributes for o in objs):
            S.add_attr(ob, a, np.concatenate([S.attr_array(o, a) for o in objs]))
    own = all(o.get('own_uv') for o in objs)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    ob.data.shade_smooth()
    if own:
        ob['own_uv'] = True
    return ob


# ----------------------------------------------------------------------------- the horns
# The left horn's centre line (x > 0), from the root sunk in the top of the head, up and out over the crown, back to
# the outermost turn behind the ear, down, and forward to the blunt tip beside the cheek (turnaround: the coil spans
# 0.45 m in profile, 0.88 m across the two horns, top 1.29 m; the tips face the front view by the cheeks).
HORN_CTRL = [
    (0.09, -0.43, 1.10),
    (0.142, -0.39, 1.19),
    (0.215, -0.3, 1.226),
    (0.3, -0.18, 1.18),
    (0.36, -0.118, 1.06),
    (0.368, -0.15, 0.93),
    (0.335, -0.24, 0.855),
    (0.293, -0.33, 0.86),
    (0.272, -0.4, 0.905),
]
HORN_R = (0.104, 0.052)         # tube radius at the root and before the tip's taper (round 2: massive, a steady taper)
RING_GAPS = (0.022, 0.046)      # growth rings: irregular gaps along the horn (round 1's even ribs read as a hose)
RIDGE_DEPTH = (0.0038, 0.0085)  # game mesh (a hint in the outline), high source (the bake carries the rest)
ROPE_R = 0.0142
# (start along the horn, loops): 4–5 bands of 2–3 tight coils that follow the taper (round 2)
ROPE_BANDS = [(0.11, 2.0), (0.28, 3.0), (0.47, 2.0), (0.63, 2.5), (0.8, 2.0)]
ROPE_PITCH = 2.04 * ROPE_R


_HORN: dict = {}
_RINGS: dict = {}


def horn_curve(s: int = 1) -> Curve:
    if s not in _HORN:
        ctrl = np.array(HORN_CTRL)
        ctrl[:, 0] *= s
        _HORN[s] = Curve(catmull_rom(ctrl, 1600), up=(s * 1.0, 0.0, 0.0))
    return _HORN[s]


def horn_radius(t):
    """Tube radius along the horn (t 0..1): massive at the root, a steady taper, the last fifth narrowing to a blunt
    cone (round 1's knob tip)."""
    t = np.asarray(t, np.float64)
    r = HORN_R[0] + (HORN_R[1] - HORN_R[0]) * t
    return r * (1.0 - 0.42 * smooth(0.78, 1.0, t) ** 1.2)


def rings(L: float) -> tuple[np.ndarray, np.ndarray]:
    """Growth ring positions (arc length) and each ring's depth factor: irregular, like real keratin."""
    key = round(L, 5)
    if key not in _RINGS:
        rng = np.random.default_rng(23)
        s = [0.035]
        while s[-1] < L + 0.05:
            s.append(s[-1] + rng.uniform(*RING_GAPS))
        _RINGS[key] = (np.array(s), rng.uniform(0.55, 1.0, len(s)))
    return _RINGS[key]


def rope_bands(L: float) -> list[tuple[float, float]]:
    """Each band's span along the horn (arc length, with a margin): the horn is smooth under the rope (seated flush)."""
    out = []
    for start, loops in ROPE_BANDS:
        s0 = start * L
        out.append((s0 - ROPE_R * 1.6, s0 + loops * ROPE_PITCH + ROPE_R * 1.6))
    return out


def ridge_field(s_arc, phi, L: float):
    """(profile 0 groove … 1 crest, depth factor): stacked cones, each ring rising slowly to a crest and dropping sharply
    into the next groove; the rings wobble round the horn, vary in depth, and vanish under the rope bands."""
    rs, dk = rings(L)
    sw = s_arc + 0.0045 * np.sin(phi * 1.0 + 0.9 * np.floor(s_arc / 0.03)) + 0.002 * np.sin(phi * 3.0 + s_arc * 40)
    k = np.clip(np.searchsorted(rs, sw) - 1, 0, len(rs) - 2)
    a, b = rs[k], rs[k + 1]
    p = np.clip((sw - a) / (b - a), 0.0, 1.0)
    # round 3: mostly flat bands, a distinct raised crest near each band's end and a sharp dark groove (round 2's
    # long slopes shaded as broad light and dark stripes, read as painted bands)
    band_flat = smooth(0.0, 0.12, p) * (1.0 - smooth(0.9, 1.0, p))
    crest = np.exp(-((p - 0.8) / 0.065) ** 2)
    prof = np.clip(0.62 * band_flat + 0.38 * crest * smooth(1.0, 0.9, p) + 0.38 * crest * (p < 0.9), 0.0, 1.0)
    band = np.zeros(np.shape(s_arc))
    for s0, s1 in rope_bands(L):
        band = np.maximum(band, smooth(s0 - 0.01, s0, s_arc) * smooth(s1 + 0.01, s1, s_arc))
    return prof, dk[k] * (1.0 - band), band


def horn_mesh(name: str, s: int, high: bool, quick: bool) -> bpy.types.Object:
    cv = horn_curve(s)
    L = cv.length
    sides = (56 if quick else 72) if high else 16
    if high:
        s_main = np.arange(0.0, L, 0.0024 if quick else 0.0015)
    else:
        # game rows: at every ring's groove and crest (an uneven outline)
        rs, _dk = rings(L)
        rows = list(rs[rs < L]) + list((rs[:-1] + 0.8 * np.diff(rs))[rs[:-1] < L])
        for s0, s1 in rope_bands(L):
            rows += list(np.arange(s0 - 0.01, s1 + 0.016, 0.015))
        s_main = np.unique(np.round(np.clip(np.array(rows + [0.0, L]), 0.0, L), 4))
    s_main = np.append(s_main[s_main < L - 0.004], L)
    cap_rows = 6 if high else 2
    caps = np.linspace(0.0, 1.0, cap_rows + 1)[1:]
    P, T, N, B = cv.at(s_main)
    t = s_main / L
    R = horn_radius(t)
    tip_r = float(R[-1])
    phi = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    depth = RIDGE_DEPTH[1] if high else RIDGE_DEPTH[0]
    prof, dk, band = ridge_field(s_main[:, None], phi[None, :], L)
    fade = (smooth(0.02, 0.08, t) * smooth(1.0, 0.95, t))[:, None]
    rad = R[:, None] + depth * dk * (prof - 0.65) * fade
    grain = np.zeros_like(rad)
    if high:
        rng = np.random.default_rng(11 + s)
        ph = rng.uniform(0, 2 * np.pi, 8)
        # fine lengthwise grain: striations along the horn, wandering slowly round it
        grain = (0.0008 * np.sin(phi[None, :] * 57 + ph[0] + 2.5 * np.sin(s_main[:, None] * 7 + ph[1]))
                 + 0.0005 * np.sin(phi[None, :] * 131 + ph[2] + 4.0 * np.sin(s_main[:, None] * 13 + ph[3]))
                 + 0.0003 * np.sin(phi[None, :] * 23 + s_main[:, None] * 31 + ph[4]))
        rad = rad + grain * fade[:, :1] * (1.0 - 0.7 * band)
    ring = np.cos(phi)[None, :, None] * N[:, None, :] + np.sin(phi)[None, :, None] * B[:, None, :]
    pts = P[:, None, :] + ring * rad[..., None]
    # the tip: a short blunt cap over the end of the cone
    Pe, Te, Ne, Be = P[-1], T[-1], N[-1], B[-1]
    cap_pts = []
    for c in caps:
        a = c * np.pi / 2
        off = Te * tip_r * 0.42 * np.sin(a)
        rg = np.cos(phi)[:, None] * Ne[None, :] + np.sin(phi)[:, None] * Be[None, :]
        cap_pts.append(Pe[None, :] + off[None, :] + rg * max(tip_r * np.cos(a), 1e-4))
    pts = np.concatenate([pts, np.array(cap_pts)], axis=0)
    rows = len(pts)
    tt = np.concatenate([t, np.full(cap_rows, 1.0)])
    # 3b: the paint's ridge fades to a neutral 0.5 under the rope bands (round 3: 0 there painted the horn between the
    # coils groove-dark, a dark gap, and a crest's worn highlight ran along each band's edge, a pale seam)
    band_b = np.broadcast_to(band, prof.shape)
    prof_paint = 0.5 + (prof - 0.5) * (1.0 - band_b)
    prof_all = np.concatenate([prof_paint, np.full((cap_rows, sides), 0.6)], axis=0)
    attrs = {
        'part': np.full((rows, sides), PART_HORN),
        'ridge': prof_all,
        'along': np.repeat(tt[:, None], sides, axis=1),
        'side': np.full((rows, sides), float(s)),
        'grain': (np.concatenate([grain, np.zeros((cap_rows, sides))]) if high else np.zeros((rows, sides))) / 0.0014,
        'strand': np.concatenate([np.broadcast_to(band, prof.shape), np.zeros((cap_rows, sides))], axis=0),   # under a rope band
    }
    ob = grid_object(name, pts, True, caps=(True, True), attrs=attrs, flip=s < 0)
    if not high:
        # one strip, u round, v along (the shared tube unwrap): no smart-project confetti in the atlas
        S.tube_uvs(ob, np.vstack([cv.pts[::8], cv.pts[-1:] + cv.T[-1:] * tip_r]))
    return ob


def rope_centre(s: int, start: float, loops: float, n: int):
    """A band's rope centre line: tight coils round the horn, seated flush on its smooth band (round 1 stood off the
    horn with dark gaps), both ends tucked into the horn."""
    cv = horn_curve(s)
    L = cv.length
    s0 = start * L
    span = loops * 2 * np.pi
    a = np.linspace(0.0, span, n)
    sa = s0 + a / (2 * np.pi) * ROPE_PITCH
    P, T, N, B = cv.at(sa)
    R = horn_radius(sa / L)
    # 3b: both ends start and finish on the inner side of the curl (the hidden side: round 3's ends rose out of the
    # horn's top as pale cut spikes); the turn count stretches by up to half a turn to land there
    a0, a1 = inner_angle(cv, sa[0]), inner_angle(cv, sa[-1])
    extra = (a1 - (a0 + s * span) + np.pi) % (2 * np.pi) - np.pi
    ang = a0 + s * a + extra * (a / span)
    rad_dir = np.cos(ang)[:, None] * N + np.sin(ang)[:, None] * B
    # 3b: each end dives into the horn over a third of a turn, fully under its surface (round 3: tapered tips stood
    # off the top of the curl)
    end = np.minimum(a, span - a) / (0.32 * 2 * np.pi)
    tuck = smooth(0.0, 1.0, end)
    off = R + ROPE_R * (0.66 * tuck - 1.6 * (1 - tuck))
    C_ = P + rad_dir * off[:, None]
    return C_, rad_dir, tuck, a


def inner_angle(cv: Curve, s_arc: float) -> float:
    """The angle (in the curve's N/B frame) of the inner side of the horn's curl at arc length `s_arc`."""
    h = 0.02
    _p, Ta, _n, _b = cv.at(np.array([max(s_arc - h, 0.0), min(s_arc + h, cv.length)]))
    _p, _t, N, B = cv.at(np.array([s_arc]))
    k = Ta[1] - Ta[0]
    k = k - _t[0] * (k @ _t[0])
    return float(np.arctan2(k @ B[0], k @ N[0]))


def rope_mesh(name: str, s: int, high: bool, quick: bool) -> list[bpy.types.Object]:
    """Every band of rope on one horn: high = two twisted plies with fibre grooves (round 2: a clearly visible twist);
    game = a round tube (the twist is baked)."""
    out = []
    for bi, (start, loops) in enumerate(ROPE_BANDS):
        arc = loops * 2 * np.pi * (float(horn_radius(start)) + ROPE_R)
        n = int(arc / (0.0015 if high else 0.035)) if not (high and quick) else int(arc / 0.003)
        n = max(n, 16)
        Cc, rd, tuck, a = rope_centre(s, start, loops, n)
        cv = Curve(Cc)
        sl = cv.s
        _P, T, N1, N2 = cv.at(sl)
        if not high:
            sides = 6
            ph = np.linspace(0, 2 * np.pi, sides, endpoint=False)
            r = ROPE_R * 1.04 * (0.8 + 0.2 * tuck)
            pts = Cc[:, None, :] + (np.cos(ph)[None, :, None] * N1[:, None, :] + np.sin(ph)[None, :, None] * N2[:, None, :]) * r[:, None, None]
            attrs = {'part': np.full((n, sides), PART_ROPE), 'strand': np.ones((n, sides)), 'along': np.repeat((sl / cv.length)[:, None], sides, 1),
                     'side': np.full((n, sides), float(s))}
            ob = grid_object(f'{name}{bi}', pts, True, caps=(True, True), attrs=attrs)
            S.tube_uvs(ob, Cc)
            out.append(ob)
            continue
        lay = 0.034                          # one full twist of the two plies every 3.4 cm
        sides = 10 if quick else 14
        ph = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        for k in range(2):
            psi = np.pi * k + 2 * np.pi * sl / lay
            r_off = ROPE_R * 0.44 * (0.8 + 0.2 * tuck)
            sc = Cc + (np.cos(psi)[:, None] * N1 + np.sin(psi)[:, None] * N2) * r_off[:, None]
            scv = Curve(sc)
            _sp, sT, sN, sB = scv.at(scv.s)
            sr = ROPE_R * 0.62 * (0.8 + 0.2 * tuck)
            # fibre grooves spiral round each ply (against the lay)
            fib = 0.00035 * np.sin(ph[None, :] * 8 - (scv.s[:, None] / 0.005) * 2 * np.pi)
            rr = sr[:, None] + fib
            pts = sc[:, None, :] + (np.cos(ph)[None, :, None] * sN[:, None, :] + np.sin(ph)[None, :, None] * sB[:, None, :]) * rr[..., None]
            outward = ((np.cos(ph)[None, :, None] * sN[:, None, :] + np.sin(ph)[None, :, None] * sB[:, None, :]) * (sc - Cc)[:, None, :]).sum(-1)
            crown = np.clip(0.5 + outward / (2 * max(float(r_off.max()), 1e-6)), 0, 1)
            attrs = {'part': np.full((len(sc), sides), PART_ROPE), 'strand': crown, 'along': np.repeat((sl / cv.length)[:, None], sides, 1),
                     'side': np.full((len(sc), sides), float(s))}
            out.append(grid_object(f'{name}{bi}_{k}', pts, True, caps=(True, True), attrs=attrs))
    return out


# ----------------------------------------------------------------------------- the scarf
SCARF_C = np.array((0.0, -0.4, 0.772))          # the band's centre
SCARF_TILT = 0.62                                # the band's plane: z rises this much per metre toward the back
SCARF_W = 0.132                                  # band width (along the neck)
SCARF_T = 0.074                                  # band thickness
KNOT_BETA = math.radians(-58)                    # where the knot sits round the band (0 = the left side, −90° = the front)
END_LEN = 0.2                                   # the hanging end, from under the knot to the fringe
END_W = 0.126
END_T = 0.034
FRINGE = (9, 0.082, 0.0078)                      # tassels: count, length, radius
KNIT = (0.021, 0.016, 0.0062)                  # stitch column width, row height, relief depth


def scarf_axes():
    n = v3((0.0, -SCARF_TILT, 1.0))
    n /= np.linalg.norm(n)
    e1 = v3((1.0, 0.0, 0.0))
    e2 = np.cross(n, e1)                          # toward the back and up
    if e2[1] < 0:
        e2 = -e2
    return e1, e2, n


def knit_relief(s_len, w):
    """Stockinette: columns of chunky V stitches (two plump leaning lobes meeting at the bottom of each V, pointing
    along +s) with a deep channel between the columns, so the knit still reads as ribbed columns at game distance
    (round 1: thin lobes blurred into dots). s along the knitting, w across; returns 0..1."""
    cw, rh, _d = KNIT
    a = w / cw
    col = np.floor(a)
    a = a - col - 0.5
    b = s_len / rh
    b = b - np.floor(b)
    h = np.zeros(np.broadcast(a, b).shape)
    for sg in (-1.0, 1.0):
        for db in (-1.0, 0.0):
            bb = b - db
            t = np.clip(bb, 0.0, 1.0)
            dx = (a - sg * (0.31 - 0.23 * t)) / 0.235
            along = np.sin(np.pi * np.clip(bb / 1.08, 0.0, 1.0)) ** 0.45
            h = np.maximum(h, np.sqrt(np.clip(1 - dx * dx, 0, 1)) * along)
    return h * (1.0 - 0.8 * np.exp(-((np.abs(a) - 0.5) / 0.05) ** 2))


def _band_ring(beta, body_r):
    e1, e2, _n = scarf_axes()
    d = np.cos(beta)[:, None] * e1 + np.sin(beta)[:, None] * e2
    return SCARF_C + d * body_r[:, None], d


def scarf_band(name: str, high: bool, quick: bool, body_radius) -> bpy.types.Object:
    """The band round the neck: a rounded-rectangle tube on the neck's surface (`body_radius(beta)` = the coat's
    distance from SCARF_C in the band's plane), with soft folds and the knit on its outside."""
    e1, e2, n = scarf_axes()
    nb = (1100 if not quick else 400) if high else 56
    na = (360 if not quick else 96) if high else 14
    beta = np.linspace(-np.pi, np.pi, nb, endpoint=False)
    rb = body_radius(beta)
    # soft folds: the band bunches a little and its width wanders
    fold = 1.0 + 0.12 * np.sin(beta * 3 + 0.6) * np.sin(beta * 2 - 0.3) + 0.26 * (0.5 + 0.5 * np.cos(beta * 7 + 0.4)) ** 2 - 0.06
    thick = SCARF_T * fold
    width = SCARF_W * (1.0 + 0.07 * np.sin(beta * 2 + 1.1) + 0.05 * np.cos(beta * 7 + 0.4))
    centre_r = rb + thick * 0.5 + 0.003
    C_, d = _band_ring(beta, centre_r)
    # the cross-section: a rounded rectangle (superellipse) in (radial d, along the neck n)
    th = np.linspace(-np.pi, np.pi, na, endpoint=False)
    cx = np.sign(np.cos(th)) * np.abs(np.cos(th)) ** 0.6
    cy = np.sign(np.sin(th)) * np.abs(np.sin(th)) ** 0.6
    rad = cx[None, :] * thick[:, None] * 0.5
    up = cy[None, :] * width[:, None] * 0.5
    s_len = beta * float(np.mean(centre_r))
    outer = smooth(0.2, 0.9, cx)[None, :]
    knit = np.zeros((nb, na))
    if high:
        knit = knit_relief(s_len[:, None], up)
        rad = rad + KNIT[2] * (knit - 0.5) * (0.35 + 0.65 * outer)
    pts = C_[:, None, :] + d[:, None, :] * rad[..., None] + n[None, None, :] * up[..., None]
    attrs = {'part': np.full((nb, na), PART_SCARF), 'knit': knit if high else np.full((nb, na), 0.5),
             'along': np.repeat((beta / (2 * np.pi) + 0.5)[:, None], na, 1), 'side': np.zeros((nb, na))}
    return grid_object(name, pts, True, attrs=attrs, closed_v=True)


def end_path(body_point) -> tuple[np.ndarray, np.ndarray]:
    """The hanging end's centre line (top → bottom) and its outward normals: from under the knot down the chest's
    front-left, on top of the coat (`body_point(z)` = the coat's surface point and normal on that diagonal)."""
    zs = np.linspace(0.655, 0.655 - END_LEN, 24)
    P, N = [], []
    for k, z in enumerate(zs):
        p, nn = body_point(z)
        u = k / (len(zs) - 1)
        # it hangs a little free of the chest toward the bottom
        P.append(p + nn * (END_T * 0.5 + 0.014 + 0.012 * u))
        N.append(nn)
    return np.array(P), np.array(N)


def scarf_end(name: str, high: bool, quick: bool, body_point) -> list[bpy.types.Object]:
    """The knot, the hanging end and its fringe."""
    out = []
    P, Nn = end_path(body_point)
    cv = Curve(P)
    nl = (300 if not quick else 150) if high else 16
    na = (280 if not quick else 80) if high else 10
    sl = np.linspace(0, cv.length, nl)
    Pc = np.stack([np.interp(sl, cv.s, P[:, k]) for k in range(3)], -1)
    Nc = np.stack([np.interp(sl, cv.s, Nn[:, k]) for k in range(3)], -1)
    T = np.gradient(Pc, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    Nc = Nc - T * (Nc * T).sum(1, keepdims=True)
    Nc /= np.linalg.norm(Nc, axis=1, keepdims=True)
    W = np.cross(T, Nc)
    th = np.linspace(-np.pi, np.pi, na, endpoint=False)
    cx = np.sign(np.cos(th)) * np.abs(np.cos(th)) ** 0.4
    cy = np.sign(np.sin(th)) * np.abs(np.sin(th)) ** 0.4
    u = sl / cv.length
    # a slight flare toward the fringe, and the top tucked into the knot
    width = END_W * (0.82 + 0.18 * smooth(0.0, 0.3, u))
    thick = END_T * (1.0 + 0.3 * smooth(0.12, 0.0, u))
    rad = cx[None, :] * thick[:, None] * 0.5
    acr = cy[None, :] * width[:, None] * 0.5
    knit = np.zeros((nl, na))
    if high:
        knit = knit_relief(sl[:, None], acr)
        front = smooth(-0.2, 0.6, cx)[None, :]
        rad = rad + KNIT[2] * (knit - 0.5) * (0.3 + 0.7 * np.abs(cx)[None, :] ** 2) * (0.5 + 0.5 * front)
    wave = (0.006 * np.sin(u * np.pi * 3.0 + 0.5) * smooth(0.05, 0.25, u))[:, None, None]
    pts = Pc[:, None, :] + Nc[:, None, :] * (rad[..., None] + wave) + W[:, None, :] * acr[..., None]
    attrs = {'part': np.full((nl, na), PART_SCARF), 'knit': knit if high else np.full((nl, na), 0.5),
             'along': np.repeat(u[:, None], na, 1), 'side': np.full((nl, na), 1.0)}
    end_ob = grid_object(f'{name}_end', pts, True, caps=(True, True), attrs=attrs)
    if not high:
        S.tube_uvs(end_ob, Pc)
    out.append(end_ob)
    # the knot: a short, flat wrap over the band where the end comes out (not a ball)
    kc = P[0] + Nn[0] * 0.014 + v3((0.0, 0.0, 0.035))
    kt = np.cross(v3((0, 0, 1)), Nn[0])
    kt /= np.linalg.norm(kt)
    nk = (180 if not quick else 90) if high else 10
    ka = (120 if not quick else 40) if high else 10
    ang = np.linspace(-1.0, 1.0, nk)
    kp = kc[None, :] + kt[None, :] * (ang * 0.074)[:, None]
    kr = 0.04 * np.sqrt(np.clip(1 - ang ** 2, 0, 1)) ** 0.45 + 0.004
    kn = Nn[0]
    kb = np.cross(kt, kn)
    th = np.linspace(-np.pi, np.pi, ka, endpoint=False)
    ring = np.cos(th)[None, :, None] * kn[None, None, :] * 0.5 + np.sin(th)[None, :, None] * kb[None, None, :] * 1.35
    rr = kr[:, None] * np.ones((1, ka))
    knit_k = np.zeros((nk, ka))
    if high:
        knit_k = knit_relief((ang * 0.074)[:, None], th[None, :] * 0.04)
        rr = rr + KNIT[2] * 0.8 * (knit_k - 0.5) * smooth(0.0, 0.2, kr)[:, None]
    kpts = kp[:, None, :] + ring * rr[..., None]
    knot_ob = grid_object(f'{name}_knot', kpts, True, caps=(True, True),
                          attrs={'part': np.full((nk, ka), PART_SCARF), 'knit': knit_k if high else np.full((nk, ka), 0.5),
                                 'along': np.zeros((nk, ka)), 'side': np.full((nk, ka), 1.0)})
    if not high:
        S.tube_uvs(knot_ob, kp)
    out.append(knot_ob)
    # the fringe: seven tassels from the end's bottom edge
    count, flen, fr = FRINGE
    Pb, Tb, Nb_, Wb = Pc[-1], T[-1], Nc[-1], W[-1]
    rng = np.random.default_rng(29)
    for k in range(count):
        acr_k = (k / (count - 1) - 0.5) * END_W * 0.84
        base = Pb + Wb * acr_k - Tb * 0.006
        dirk = Tb + Wb * (acr_k * 0.6) + Nb_ * rng.uniform(-0.05, 0.12)
        dirk /= np.linalg.norm(dirk)
        ln = flen * rng.uniform(0.9, 1.08)
        nrow = (60 if not quick else 30) if high else 4
        sides = 10 if high else 4
        sv = np.linspace(0, 1, nrow)
        cpts = base[None, :] + dirk[None, :] * (sv * ln)[:, None] + Wb[None, :] * (0.004 * np.sin(sv * 3 + k))[:, None]
        tcv = Curve(cpts)
        _p, tT, tN, tB = tcv.at(tcv.s)
        th = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        r = fr * (1.0 - 0.15 * sv) * np.where(sv > 0.92, np.sqrt(np.clip((1 - sv) / 0.08, 0.05, 1)), 1.0)
        twist = np.zeros((nrow, sides))
        if high:
            twist = 0.0009 * np.sin(th[None, :] * 2 + (sv * ln / 0.012)[:, None] * 2 * np.pi)
        rr = r[:, None] + twist
        fpts = cpts[:, None, :] + (np.cos(th)[None, :, None] * tN[:, None, :] + np.sin(th)[None, :, None] * tB[:, None, :]) * rr[..., None]
        f_ob = grid_object(f'{name}_fringe{k}', fpts, True, caps=(True, True),
                           attrs={'part': np.full((nrow, sides), PART_FRINGE), 'knit': 0.5 + twist / 0.0018,
                                  'along': np.repeat(sv[:, None], sides, 1), 'side': np.full((nrow, sides), 1.0)})
        if not high:
            S.tube_uvs(f_ob, cpts)
        out.append(f_ob)
    return out


# ----------------------------------------------------------------------------- the ears (fur slabs in the voxel body)
EAR_ROOT = np.array((0.15, -0.455, 0.985))
EAR_DIR = np.array((1.0, -0.06, -0.12))
EAR_DIR = EAR_DIR / np.linalg.norm(EAR_DIR)
EAR_LEN = 0.19
EAR_W = 0.1                   # the leaf's widest
EAR_OPEN = np.array((0.02, -0.95, -0.3))      # the lining (concave side) looks this way (forward and a little down)


def ear_axes(s: int):
    d = EAR_DIR * v3((s, 1, 1))
    o = EAR_OPEN * v3((s, 1, 1))
    o = o - d * (o @ d)
    o /= np.linalg.norm(o)
    a = np.cross(d, o)
    a /= np.linalg.norm(a)
    return d, a, o


def ear_width(u):
    u = np.asarray(u, np.float64)
    return EAR_W * 0.5 * (0.55 + 0.45 * np.sin(np.pi * np.clip(0.12 + 0.88 * u, 0, 1))) * (1 - smooth(0.62, 1.0, u) ** 1.6) + 0.004


def ear_point(s: int, u, v, side: float):
    """The ear slab's surface: u 0 root → 1 tip, v −1..1 across, side +1 the back (fur) / −1 the lining (cupped)."""
    d, a, o = ear_axes(s)
    u, v = np.broadcast_arrays(np.asarray(u, np.float64), np.asarray(v, np.float64))
    root = EAR_ROOT * v3((s, 1, 1))
    w = ear_width(u)
    cup = 0.013 * (1 - v ** 2) * smooth(0.0, 0.25, u) * smooth(1.0, 0.7, u)
    th = (0.011 * (1 - 0.55 * u) + 0.002) * np.sqrt(np.clip(1 - v ** 2, 0, 1)) ** 0.5
    mid = root + d * (EAR_LEN * u)[..., None] + a * (v * w)[..., None]
    # the whole leaf curls: its edges come forward (toward the lining side), and the tip droops a touch
    mid = mid + o * (0.012 * v ** 2)[..., None] - v3((0, 0, 1)) * (0.012 * u ** 2)[..., None]
    if side > 0:
        return mid - o * th[..., None]
    return mid + o * (th - cup)[..., None] * 0.6


def ear_slab(s: int, nu: int = 40, nv: int = 24) -> bpy.types.Object:
    us = np.linspace(-0.25, 1.0, nu + 1)
    vs = np.linspace(-1.0, 1.0, nv + 1)
    U_, V_ = np.meshgrid(us, vs, indexing='ij')
    back = ear_point(s, U_, V_, 1.0)
    front = ear_point(s, U_, V_, -1.0)
    # a closed slab: the back surface, then the lining surface reversed; sides stitched where v = ±1 (both meet)
    bm = bmesh.new()
    vb = [[bm.verts.new(back[j, i]) for i in range(nv + 1)] for j in range(nu + 1)]
    vf = [[bm.verts.new(front[j, i]) for i in range(nv + 1)] for j in range(nu + 1)]
    for j in range(nu):
        for i in range(nv):
            bm.faces.new((vb[j][i], vb[j + 1][i], vb[j + 1][i + 1], vb[j][i + 1]))
            bm.faces.new((vf[j][i], vf[j][i + 1], vf[j + 1][i + 1], vf[j + 1][i]))
    for j in range(nu):
        for i in (0, nv):
            q = (vb[j][i], vf[j][i], vf[j + 1][i], vb[j + 1][i])
            bm.faces.new(q if i == 0 else q[::-1])
    for j in (0, nu):
        for i in range(nv):
            q = (vb[j][i], vb[j][i + 1], vf[j][i + 1], vf[j][i])
            bm.faces.new(q if j == 0 else q[::-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(f'earslab{"L" if s > 0 else "R"}')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    C.link_obj(ob)
    return ob


def ear_lookup(p: np.ndarray) -> dict:
    """Per point: on an ear (bool), its u (0 root … 1 tip), v (−1..1 across) and which face (lining = True)."""
    k = len(p)
    out = {'on': np.zeros(k, bool), 'u': np.zeros(k), 'v': np.zeros(k), 'lining': np.zeros(k, bool), 's': np.zeros(k)}
    for s in (1, -1):
        d, a, o = ear_axes(s)
        q = p - EAR_ROOT * v3((s, 1, 1))
        u = (q @ d) / EAR_LEN
        w = ear_width(np.clip(u, 0, 1))
        v = (q @ a) / np.maximum(w, 1e-4)
        h = q @ o - 0.012 * np.clip(v, -1, 1) ** 2
        on = (u > 0.02) & (u < 1.12) & (np.abs(v) < 1.35) & (np.abs(h) < 0.03) & (p[:, 0] * s > 0.1)
        out['on'] |= on
        out['u'] = np.where(on, u, out['u'])
        out['v'] = np.where(on, v, out['v'])
        out['lining'] |= on & (h > -0.002) & (np.abs(v) < 0.85) & (u < 0.96)
        out['s'] = np.where(on, s, out['s'])
    return out


# ----------------------------------------------------------------------------- the hooves (cloven; in the voxel body)
HOOF_LEN = 0.172       # heel to toe (round 2: big hooves)
HOOF_H = 0.094         # at the heel
TOE_W = 0.048          # half width of one toe
SPLIT = 0.0135         # the cleft between the toes (stays open at 3.5 mm voxels), closing toward the heel


def hoof_toes(cx: float, cy: float, nring: int = 14, nsides: int = 40) -> list[bpy.types.Object]:
    """Two toes: each a D-shaped column (round outside, straight along the cleft), flat soled, its front wall sloping
    back as it rises; the heel fuller and taller than the toe."""
    out = []
    for sg in (1, -1):
        rings = []
        for j in range(nring + 1):
            h = j / nring
            z = HOOF_H * h
            pts = []
            for i in range(nsides):
                g = 2 * np.pi * i / nsides
                cg, sgn = math.cos(g), math.sin(g)
                ry = HOOF_LEN * 0.5 * (1 - 0.32 * h ** 1.4)
                rx = TOE_W * (1 - 0.18 * h)
                # superellipse outline; the toe tip a little pointed, the heel round
                yy = -math.copysign(abs(sgn) ** 0.8, sgn) * ry
                xx = math.copysign(abs(cg) ** 0.7, cg) * rx
                # the straight cleft side
                xx = max(xx, -rx * 0.62)
                yy = yy + HOOF_LEN * 0.16 * h ** 1.2          # the front wall leans back as it rises
                # the toe tips turn in a touch
                tip = smooth(0.0, -HOOF_LEN * 0.5, yy)
                xx = xx - rx * 0.12 * tip
                x = cx + sg * (SPLIT * 0.5 * (1 - 0.45 * smooth(-0.02, 0.06, yy)) + rx * 0.62 + xx)
                pts.append((x, cy + yy, z))
            rings.append(pts)
        P = np.array(rings)
        if sg < 0:
            P = P[:, ::-1]
        ob = grid_object(f'toe{sg}', P, True, caps=(True, True))
        out.append(ob)
    return out
