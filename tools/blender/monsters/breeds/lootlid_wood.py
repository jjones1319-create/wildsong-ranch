"""Lootlid's wood (Art 2.1 Ultra; 4-details panels 1, 2, 3 and 6): the carving of the high source, baked into the normal
map, and the per-vertex fields the paint reads.

  - planks: horizontal boards on the box and the lid's front, back and sides, barrel staves running across the lid's
    arch (the seams where 2-turnaround draws them), each board a little crowned so its edges read worn, with a few
    butt joints;
  - grain: long wavy lines along each board (grooved a hair deep), bending round the knots; a few big knots with
    their rings and a dark heart (the box front, the lid front by the plate, the backs, a side);
  - wear: nicks chipped out of the board edges and the shell's corners, short cracks along the grain;
  - the face: the closed eyelid under each lens (a lid fold and its lash line), the socket rims, the brows;
  - the posts: vertical grain and cracks, end grain rings on the soles.
Attributes written (besides lib.surface.base_attrs): 'region' (0 box, 1 lid, 2 inside, 3 post, 4 eyelid, 5 socket rim,
6 brow, 7 underside, 8 sole), 'seam', 'crown', 'pid', 'gco' (grain coordinates: along, across, plank), 'grain', 'knot',
'nick', 'crack', 'edge', 'lash', 'lip'.
"""
from __future__ import annotations

import math

import numpy as np

from lib import surface as S
from monsters.breeds import lootlid_form as F
from monsters.breeds import lootlid_noise as N

BOX_SEAMS = (0.232, 0.292, 0.356, 0.419)
LID_SEAMS = (0.086, 0.253, 0.373, 0.478)             # arc length up the lid's front (and back) from its bottom edge
LID_SIDE_SEAMS = (0.578, 0.69, 0.79)
SEAM_W, SEAM_D = 0.0042, 0.0068         # round 3: deeper carved seams (the paint barely darkens them)
CROWN = 0.0026                          # each board's face rounded: worn edges
# knots: (region, face, along, across, half-length, half-width): 2-turnaround and 4-details
# round 2: three big ringed knots where the pictures put them (the base's front left of centre, the lid's front right of
# the keyhole, the lid's back), smaller ones on the back and a side
KNOTS = [(0, 'front', -0.12, 0.305, 0.074, 0.05), (1, 'front', 0.232, 0.052, 0.052, 0.034), (1, 'back', 0.03, 0.31, 0.068, 0.046),
         (0, 'back', 0.12, 0.27, 0.045, 0.03), (0, 'side+', 0.06, 0.31, 0.04, 0.027), (1, 'side-', -0.04, 0.62, 0.036, 0.024)]
_ARC: dict = {}
_LAST: dict = {}                 # the last carve's fields (the shape preview paints with them)


def lid_arc(z: np.ndarray) -> np.ndarray:
    """Arc length up the lid's profile from its bottom edge to height z (the front and the back alike)."""
    if not _ARC:
        al = np.linspace(0, math.pi / 2, 2001)
        ds = np.sqrt((F.LID_B * np.sin(al)) ** 2 + (F.LID_RZ * np.cos(al)) ** 2)
        _ARC['al'] = al
        _ARC['s'] = np.concatenate([[0.0], np.cumsum(0.5 * (ds[1:] + ds[:-1]) * np.diff(al))])
    z = np.asarray(z, np.float64)
    al = np.arcsin(np.clip((z - F.LID_SPRING) / F.LID_RZ, 0, 1))
    return np.minimum(z, F.LID_SPRING) - F.Z_LB + np.interp(al, _ARC['al'], _ARC['s'])


def ab_at(z: np.ndarray, lid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    zs = np.linspace(0.0, 1.0, 401)
    B = np.array([F.box_ab(float(v)) for v in zs])
    L = np.array([F.lid_ab(float(v)) for v in zs])
    a = np.where(lid, np.interp(z, zs, L[:, 0]), np.interp(z, zs, B[:, 0]))
    b = np.where(lid, np.interp(z, zs, L[:, 1]), np.interp(z, zs, B[:, 1]))
    return a, b


def seam_field(v: np.ndarray, seams, lo: float, plank_key: np.ndarray):
    """For a coordinate across the boards: distance to the nearest seam, the board's index and its crown (0 at an
    edge → 1 in the middle)."""
    edges = np.array([lo] + list(seams) + [10.0])
    idx = np.clip(np.searchsorted(edges, v) - 1, 0, len(edges) - 2)
    a, b = edges[idx], np.minimum(edges[idx + 1], 1.0)
    d = np.minimum(np.abs(v - a) + 9 * (idx == 0) * (a == lo), np.abs(b - v))
    width = np.maximum(b - a, 1e-3)
    crown = 1.0 - (2.0 * (v - a) / width - 1.0) ** 2
    return d, idx + 16 * plank_key, np.clip(crown, 0, 1)


def curvature(ob, co: np.ndarray, vn: np.ndarray, iters: int = 6) -> np.ndarray:
    """A convexity measure (metres⁻¹-ish, + on convex corners), smoothed over a few rings."""
    me = ob.data
    e = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get('vertices', e)
    e = e.reshape(-1, 2)
    deg = np.bincount(e.ravel(), minlength=len(co)).astype(np.float64)
    acc = np.zeros_like(co)
    np.add.at(acc, e[:, 0], co[e[:, 1]])
    np.add.at(acc, e[:, 1], co[e[:, 0]])
    lap = acc / np.maximum(deg, 1)[:, None] - co
    k = -np.einsum('ij,ij->i', lap, vn)
    for _ in range(iters):
        s = np.zeros(len(co))
        np.add.at(s, e[:, 0], k[e[:, 1]])
        np.add.at(s, e[:, 1], k[e[:, 0]])
        k = 0.5 * k + 0.5 * s / np.maximum(deg, 1)
    return k


def eye_local(co: np.ndarray, s: int):
    c, xax, yax, look = F.eye_frame(s)
    q = co - c
    return (q @ xax) / F.EYE_R, (q @ yax) / F.EYE_R, q @ look


def fields(ob) -> dict:
    """Every field of the wood for the mesh's vertices (before any carving): see the module's note."""
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    n = len(co)
    from monsters.breeds import lootlid_ultra as R
    zn = R.zones(co)
    lid = zn['lid']
    a, b = ab_at(z, lid)
    xn, yn = x / np.maximum(a, 1e-3), y / np.maximum(b, 1e-3)
    fb = np.abs(yn) >= np.abs(xn)
    under = (~lid) & (vn[:, 2] < -0.6) & (z < F.Z_BOT + 0.03)
    region = np.where(lid, 1, 0)
    region = np.where(under, 7, region)
    region = np.where(zn['inside'], 2, region)
    # the face: the closed eyelids (under the lenses), the socket rims, the brows
    eyelid = np.zeros(n, bool)
    rim = np.zeros(n, bool)
    lash = np.zeros(n)
    lip = np.zeros(n)
    for s in (1, -1):
        xe, ye, ze = eye_local(co, s)
        r = np.hypot(xe, ye)
        on = lid & (ze > -0.03) & (r < 1.45)
        eyelid |= on & (r < 0.86) & (ze > -0.012)
        rim |= on & (r >= 0.8) & (r < 1.3)
        lc = F.EYE_R * 0 + (-0.12 - 0.13 * (1 - np.clip(xe / 0.86, -1, 1) ** 2))
        lash = np.maximum(lash, on * (r < 0.86) * np.exp(-((ye - lc) / 0.045) ** 2) * N.smooth(0.86, 0.7, r))
        lip = np.maximum(lip, on * N.smooth(0.74, 0.86, r) * N.smooth(1.0, 0.86, r))
    region = np.where(rim, 5, region)
    region = np.where(eyelid, 4, region)
    brow = np.zeros(n)
    for s in (1, -1):
        u = (x * s - F.BROW['x']) / F.BROW['half']
        zc = F.BROW['z'] + F.BROW['arch'] * (1 - np.clip(u, -1, 1) ** 2) - 0.006 * u
        hit = lid & (np.abs(u) < 1.1) & (np.abs(z - zc) < 0.02) & (y < -0.15)
        brow = np.maximum(brow, hit * N.smooth(0.016, 0.008, np.abs(z - zc)) * N.smooth(1.1, 0.9, np.abs(u)))
    region = np.where(brow > 0.5, 6, region)
    # boards: along, across, which face
    along = np.where(fb, x, y)
    side_key = np.where(fb, np.where(y < 0, 0, 1), np.where(x > 0, 2, 3))
    across = np.where(lid & fb, lid_arc(z), z)
    seams = np.full(n, 9.0)
    pidx = np.zeros(n, np.int64)
    crown = np.ones(n)
    # the underside: boards along x, seams across y (the ko shows it)
    under_m = region == 7
    across = np.where(under_m, y, across)
    along = np.where(under_m, x, along)
    for reg, msk, sm, lo in ((0, (~lid) & ~under_m, BOX_SEAMS, F.Z_BOT - 0.05),
                             (1, lid & fb, LID_SEAMS + (0.5 * (LID_SEAMS[-1] + lid_arc(np.array([F.Z_TOP]))[0] + 0.1),), 0.0),
                             (2, lid & ~fb, LID_SIDE_SEAMS, F.Z_LB), (3, under_m, (-0.12, 0.0, 0.12), -0.4)):
        d, idx, cr = seam_field(across[msk], sm, lo, side_key[msk] + 4 * reg)
        seams[msk], pidx[msk], crown[msk] = d, idx, cr
    # round 2: long boards running the full width; a butt joint on only about one board in four
    hb = N.hash1(pidx, 41)
    j1 = (hb - 0.5) * 0.4
    butt = np.where(hb > 0.76, np.abs(along - j1), 9.0)
    face_area = zn['face'] & ((np.minimum(np.linalg.norm(co - F.eye_frame(1)[0], axis=1), np.linalg.norm(co - F.eye_frame(-1)[0], axis=1)) < 0.1)
                              | ((np.abs(x) < 0.12) & (z < 0.67)))
    plankish = np.isin(region, (0, 1, 7)) & ~face_area
    seam = np.exp(-(seams / SEAM_W) ** 2) * plankish
    seam = np.maximum(seam, np.exp(-(butt / SEAM_W) ** 2) * plankish)
    pid = N.hash1(pidx, 43)
    # grain coordinates: along the board, across it (warped), the board
    g_al, g_ac = along, across
    P = np.stack([g_al * 0.18, g_ac, pid * 7.0], axis=1)
    warp = 0.011 * N.fbm(P, 1 / 0.025, 51, 3)
    # knots: rings, a dark heart, the grain bending round them
    knot = np.zeros(n)
    face_name = np.choose(side_key, ['front', 'back', 'side+', 'side-'])
    for reg, fname, ka, kc, ra, rc in KNOTS:
        m = (region == reg) & (face_name == fname)
        if not m.any():
            continue
        du, dv = (g_al[m] - ka) / ra, (g_ac[m] - kc) / rc
        d = np.hypot(du, dv)
        warp[m] += np.sign(dv + 1e-6) * rc * 1.6 * np.exp(-d * d * 0.32)
        ang = np.arctan2(dv, du)
        swirl = 0.5 + 0.5 * np.cos(2 * math.pi * (d * 3.4 + 0.12 * np.sin(ang * 2.0)))
        knot[m] = np.maximum(knot[m], np.exp(-d * d * 0.45) * (0.35 + 0.65 * swirl) * N.smooth(1.25, 0.9, d)
                             + 1.3 * N.smooth(0.2, 0.08, d))
    ph = (g_ac + warp) / 0.0072
    lines = 0.5 + 0.5 * np.cos(2 * math.pi * ph)
    grain = N.smooth(0.72, 0.97, lines) * (0.6 + 0.4 * N.fbm(P * np.array([1, 4, 1]), 1 / 0.05, 52, 2))
    gco = np.stack([g_al, g_ac + warp, pid], axis=1)
    # nicks along the board edges and on the shell's corners, cracks along the grain
    curv = curvature(ob, co, vn)
    edge = N.smooth(4.0, 22.0, curv) * (region != 2)
    f1, _f2, cid = N.voronoi(co, 0.016, 61)
    chip_cell = N.hash1(cid % 1000003, 62) < 0.36
    # chipped board ends: the boards' ends near the shell's vertical corners (under and beside the corner straps)
    ends = N.smooth(0.72, 0.9, np.abs(np.where(fb, xn, yn))) * plankish
    nick = chip_cell * N.smooth(0.014, 0.0, f1) * np.maximum.reduce([N.smooth(0.007, 0.001, seams) * plankish,
                                                                     edge * (N.hash1(cid % 1000003, 63) < 0.55),
                                                                     ends * N.smooth(0.012, 0.002, seams)])
    crack = np.zeros(n)
    cr_ph = (g_ac + warp * 0.7) / 0.021
    crk = np.abs(cr_ph - np.round(cr_ph))
    crack_cell = N.hash1(np.floor(cr_ph).astype(np.int64) * 131 + np.floor(g_al / 0.09).astype(np.int64), 64)
    span = 0.5 + 0.5 * np.cos(2 * math.pi * (g_al / 0.09 - np.floor(g_al / 0.09) - 0.5))
    crack = (crack_cell < 0.2) * N.smooth(0.07, 0.0, crk) * N.smooth(0.15, 0.7, span) * np.isin(region, (0, 1, 7)) * ~face_area
    # splits running in from the boards' ends
    crack = np.maximum(crack, (crack_cell < 0.3) * N.smooth(0.06, 0.0, crk) * ends * N.smooth(0.82, 0.95, np.abs(np.where(fb, xn, yn))))
    return {'co': co, 'vn': vn, 'region': region.astype(np.float64), 'seam': seam, 'crown': crown, 'pid': pid, 'gco': gco,
            'grain': grain, 'knot': np.clip(knot, 0, 1.5), 'nick': nick, 'crack': crack, 'edge': edge, 'lash': lash,
            'lip': lip, 'brow': brow, 'sole': np.zeros(n, bool), 'ld': np.zeros(n)}


def carve(hi_body) -> None:
    """Carve the wood into the high source along its normals and store the fields for the paint."""
    W = fields(hi_body)
    _LAST.clear()
    _LAST.update(W)
    _LAST['n'] = len(W['co'])
    co, vn = W['co'], W['vn']
    reg = W['region']
    wood = np.isin(reg, (0, 1, 7))
    d = np.zeros(len(co))
    d += wood * (CROWN * W['crown'] ** 0.5 - SEAM_D * W['seam'])
    d -= 0.0014 * W['grain'] * np.isin(reg, (0, 1, 2, 7))
    d += 0.0002 * N.fbm(co, 1 / 0.003, 71, 2) * np.isin(reg, (0, 1, 7))
    d -= 0.0036 * W['nick']
    d -= 0.0026 * W['crack']
    # knots: rings stand proud, the heart a little lower but still proud (polish pass: the pit's 1.6 mm cliff at the
    # heart's edge baked as a black hole)
    d += 0.0016 * np.minimum(W['knot'], 1.0) - 0.0009 * N.smooth(1.0, 1.45, W['knot'])
    # the eyelid's fold over the lash line, the lash a groove; the socket rim's inner lip
    d += 0.0016 * N.smooth(0.0, 0.25, W['lash']) * (reg == 4) - 0.0012 * W['lash']
    S.set_positions(hi_body, co + vn * d[:, None])
    hi_body.data.shade_smooth()
    S.base_attrs(hi_body, co)
    for k in ('region', 'seam', 'crown', 'pid', 'grain', 'knot', 'nick', 'crack', 'edge', 'lash', 'lip', 'brow'):
        S.add_attr(hi_body, k, W[k].astype(np.float64))
    S.add_attr(hi_body, 'gco', W['gco'])
    S.add_attr(hi_body, 'sole', W['sole'].astype(np.float64))
    S.add_attr(hi_body, 'ldist', W['ld'])
