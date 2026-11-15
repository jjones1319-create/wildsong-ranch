"""Scrollopus's cap, tassel and spectacles (Art 2.1 Ultra; 1-hero, 2-turnaround, 4-details panel 1).

  - the scholar's cap: a soft felt skullcap fitted over the crown with a rolled hem, under a flat felt board with
    rounded corners, tilted down toward its left and back, a covered button at its middle;
  - the tassel: a braided gold cord from the button across the board to its front-left corner, hanging from there to a
    bound knot and a bunch of gold strands (two chain bones on the cap);
  - the spectacles: round gold rims (thick enough to read at 64 px), a high arched bridge, hinge blocks and temples
    running back along the head; no glass, so the eyes show through clean (4-details: the rims are the look).

Every piece carries `pk` (its kind, for the paint and the weights) and `w2` (a 0..1 coordinate along or across it).
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import scrollopus_form as F
from monsters.breeds import scrollopus_geo as G
from monsters.breeds import scrollopus_noise as N

smooth = N.smooth
v3 = N.v3
Z = np.array([0.0, 0.0, 1.0])

PK = {'skull': 1, 'board': 2, 'button': 3, 'cord': 4, 'hang': 5, 'knot': 6, 'strand': 7,
      'rim': 10, 'bridge': 11, 'hinge': 12, 'temple': 13, 'glint': 14}

# the board: its normal tilted down toward its left and back (2-turnaround front and side), a corner to the front-left
# round 2 (review): a smaller cap at a jaunty tilt toward the tassel's side (its left), a shallower band so more of
# the spotted crown shows, a thicker felt board with soft edges seated on the band (a gap under it showed through)
BOARD_N = F._unit((0.31, 0.1, 1.0))
BOARD_SIDE, BOARD_R, BOARD_T, BOARD_EDGE = 0.34, 0.075, 0.052, 0.023
BOARD_TURN = -24.0                  # the board's +x edge turned toward the front (the tassel shows from the camera)
SKULL_Z = F.MANTLE[0][2] + 0.237     # the skullcap's hem height at the middle; lower toward its left, higher on its right
SKULL_TILT = 0.036
SPEC_R, SPEC_TUBE = 0.072, 0.0048   # round 2: the rims about 60% as thick (they read as tubes), a little wider
SPEC_OUT = 0.022                    # round 3: the rims just in front of the eyes (they floated a third of a lens forward)


def union_radius(dirs: np.ndarray) -> np.ndarray:
    """From the mantle's centre along each unit direction: the distance to the head's surface (the larger of the
    mantle's and the crown's ellipsoids along that ray)."""
    c0 = v3(F.MANTLE[0])
    best = np.zeros(len(dirs))
    for c, r in (F.MANTLE, F.CROWN):
        o = (c0 - v3(c)) / v3(r)
        dd = dirs / v3(r)
        a = (dd * dd).sum(axis=1)
        b = 2 * (o * dd).sum(axis=1)
        cc = float(o @ o) - 1.0
        disc = np.maximum(b * b - 4 * a * cc, 0.0)
        t = (-b + np.sqrt(disc)) / (2 * a)
        best = np.maximum(best, t)
    return best


def skullcap(high: bool) -> dict:
    """Round 3 (review: the board sat on a peg with a see-through slot under it): a soft felt band from its hem up the
    head, then rounding up into the board's underside all round a ring 13 cm out from the board's middle, so the board
    sits flush on it (a little puffy, as felt is)."""
    nu, nv = (128, 30) if high else (40, 9)
    c0 = v3(F.MANTLE[0])
    cb, bx, by, bn = board_frame()
    # polish (review: a pale sliver under the board): the band's top ends inside the board, at its middle plane (2 mm
    # in, the board's soft sag lifted its underside off the ring and the low copies opened a gap)
    bottom = cb
    th = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    zt = np.linspace(0.0, 1.0, nv + 1)
    z_hem = SKULL_Z - SKULL_TILT * np.cos(th) + 0.008 * np.sin(th)
    el0 = np.arcsin(np.clip((z_hem - c0[2]) / F.MANTLE[1][2], -1.0, 1.0))
    el1 = el0 + (math.radians(70.0) - el0) * 0.55
    # the ring on the board's underside, in the direction of each column
    dirs_h = np.stack([np.cos(th), np.sin(th), np.zeros(nu)], axis=1)
    ring_d = dirs_h - bn[None] * (dirs_h @ bn)[:, None]
    ring_d /= np.linalg.norm(ring_d, axis=1, keepdims=True)
    ring = bottom[None] + ring_d * 0.15
    # polish (review: a pale shelf under the board read as a gap): each column follows the head up to the point
    # straight below its ring point, then rises straight up into the board (no up-facing shelf to catch the light);
    # where that point lies below the hem (the board's overhanging left side) the band flares out to it instead
    d0 = np.stack([np.cos(th) * np.cos(el0), np.sin(th) * np.cos(el0), np.sin(el0)], axis=1)
    ra, rb = v3(F.MANTLE[1]), v3(F.MANTLE[0])
    q = 1.0 - ((ring[:, 0] - rb[0]) / ra[0]) ** 2 - ((ring[:, 1] - rb[1]) / ra[1]) ** 2
    zh = rb[2] + ra[2] * np.sqrt(np.clip(q, 0.0, 1.0))
    # (clamped to just above the hem, continuously: a hard switch between the two cases creased the band)
    # (4 cm above the hem at least: thinner strips quantised into shared texels in the shipped copy)
    below = np.stack([ring[:, 0], ring[:, 1], np.maximum(zh, z_hem + 0.04)], axis=1)
    d1 = below - c0[None]
    d1 /= np.linalg.norm(d1, axis=1, keepdims=True)
    p1 = c0[None] + d1 * (union_radius(d1) + 0.005)[:, None]
    # a soft fillet where the band turns up into the wall (a sharp inside corner baked pale specks and caught the
    # screen-space shading): the band along the head stops 2 cm short of the wall's foot, then curves up into it
    p_hem = c0[None] + d0 * (union_radius(d0) + 0.005)[:, None]
    al = np.clip(0.02 / np.maximum(np.linalg.norm(p_hem - p1, axis=1), 1e-6), 0.0, 0.45)[:, None]
    d1f = d1 + (d0 - d1) * al
    d1f /= np.linalg.norm(d1f, axis=1, keepdims=True)
    p1f = c0[None] + d1f * (union_radius(d1f) + 0.005)[:, None]
    m = p1 + (ring - p1) * 0.22
    rows = []
    for k, w in enumerate(zt):
        if w <= 0.6:
            t = w / 0.6
            d = d0 * (1 - t) + d1f * t
            d /= np.linalg.norm(d, axis=1, keepdims=True)
            rr = union_radius(d) + 0.005
            rows.append(c0[None] + d * rr[:, None])
        else:
            t = (w - 0.6) / 0.4
            rows.append((1 - t) ** 2 * p1f + 2 * t * (1 - t) * m + t ** 2 * ring)
    P = np.stack(rows, axis=1)
    Pf = P.reshape(-1, 3)
    nrm = Pf - c0
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    tk = 0.011
    outer = Pf
    inner = Pf - nrm * tk
    n = len(Pf)
    Fo = G.grid_faces(nu, nv, wrap_u=True)
    Fi = G.grid_faces(nu, nv, wrap_u=True)[:, ::-1] + n
    hem = [[i * (nv + 1), i * (nv + 1) + n, ((i + 1) % nu) * (nv + 1) + n, ((i + 1) % nu) * (nv + 1)] for i in range(nu)]
    top_o, top_i = 2 * n, 2 * n + 1
    tops = [[i * (nv + 1) + nv, ((i + 1) % nu) * (nv + 1) + nv, top_o, top_o] for i in range(nu)]
    tops += [[((i + 1) % nu) * (nv + 1) + nv + n, i * (nv + 1) + nv + n, top_i, top_i] for i in range(nu)]
    V = np.concatenate([outer, inner, [bottom, bottom - bn * tk]])
    Fa = np.concatenate([Fo, Fi, np.array(hem), np.array(tops)])
    w2 = np.concatenate([np.tile(zt, nu), np.tile(zt, nu), [1.0, 1.0]])
    u = np.concatenate([np.repeat(th / (2 * math.pi), nv + 1)] * 2 + [[0.0, 0.0]])
    return G.piece(V, Fa, pk=PK['skull'], w2=w2, u=u)


def board_frame():
    n = BOARD_N
    top = v3(F.MANTLE[0]) + n * float(union_radius(n[None])[0] + 0.02)      # round 3: the band rises to meet it
    centre = top + n * (0.5 * BOARD_T)
    e1 = F._unit(np.cross(n, (0.0, 1.0, 0.0)))
    e1 = -e1 if e1[0] < 0 else e1
    a = math.radians(BOARD_TURN)
    e2 = np.cross(n, e1)
    x = e1 * math.cos(a) + e2 * math.sin(a)
    y = np.cross(n, x)
    return centre, x, y, n


def corner(k: int) -> np.ndarray:
    """The board's corner k (0..3), on its top face, 2 cm in from the rounded edge."""
    c, x, y, n = board_frame()
    sx, sy = ((1, 1), (-1, 1), (-1, -1), (1, -1))[k]
    h = 0.5 * BOARD_SIDE - BOARD_R
    p = c + x * sx * h + y * sy * h + n * (0.5 * BOARD_T)
    return p + (x * sx + y * sy) / math.sqrt(2) * (BOARD_R - 0.02)


def edge_mid() -> np.ndarray:
    """The middle of the board's +x edge (toward its left and a little forward), on its top face."""
    c, x, y, n = board_frame()
    return c + x * (0.5 * BOARD_SIDE - 0.012) + n * (0.5 * BOARD_T)


def tassel_points() -> list[tuple]:
    """The tassel chain: from where the cord comes over the board's edge, to the knot, to the strands' ends."""
    c, x, y, n = board_frame()
    e = edge_mid()
    out = x
    p0 = e + out * 0.024 - n * (0.5 * BOARD_T + 0.004)
    p1 = p0 + v3((0.012, -0.004, -0.125))
    p2 = p1 + v3((0.004, 0.0, -0.105))
    return [tuple(round(float(v), 4) for v in p) for p in (p0, p1, p2)]


def board(high: bool) -> dict:
    c, x, y, n = board_frame()
    step = 0.006 if high else 0.03
    pc = G.rounded_box((0.5 * BOARD_SIDE, 0.5 * BOARD_SIDE, 0.5 * BOARD_T), BOARD_EDGE, step, 4 if high else 2)
    L = pc['v']
    # the rounded corners in plan: pull the square's corners in onto arcs of BOARD_R
    h = 0.5 * BOARD_SIDE - BOARD_R
    q = np.abs(L[:, :2])
    over = np.maximum(q - h, 0.0)
    rr = np.linalg.norm(over, axis=1)
    lim = BOARD_R - 0.0
    k = np.where(rr > lim, lim / np.maximum(rr, 1e-9), 1.0)
    L2 = L.copy()
    L2[:, :2] = np.sign(L[:, :2]) * (np.minimum(q, h) + over * k[:, None])
    # a soft sag: felt, not a plank (the middle a touch higher, the corners droop)
    rho = np.linalg.norm(L2[:, :2], axis=1) / (0.5 * BOARD_SIDE * math.sqrt(2))
    L2[:, 2] += 0.006 * (1.0 - rho ** 2) - 0.004 * smooth(0.6, 1.0, rho)
    V = c[None] + L2[:, :1] * x[None] + L2[:, 1:2] * y[None] + L2[:, 2:3] * n[None]
    edge = np.minimum(0.5 * BOARD_SIDE - np.abs(L2[:, 0]), 0.5 * BOARD_SIDE - np.abs(L2[:, 1]))
    top = (L2[:, 2] > 0.25 * BOARD_T).astype(float)
    return G.piece(V, pc['f'], pk=PK['board'], w2=np.clip(edge / 0.05, 0, 1), top=top)


def button(high: bool) -> dict:
    c, x, y, n = board_frame()
    nu = 20 if high else 8
    base = c + n * (0.5 * BOARD_T)
    pts = np.array([base - n * 0.004, base + n * 0.006, base + n * 0.012])
    pc = G.tube(pts, np.array([0.022, 0.02, 0.012]), nu)
    return G.tag(pc, pk=PK['button'], w2=0.0)


def braid_tube(pts: np.ndarray, r: float, nu: int, kind: int, high: bool) -> dict:
    pts = F.resample(np.asarray(pts, np.float64), 0.004 if high else 0.02)
    pc = G.tube(pts, r, nu)
    s = F.arclen(pts)
    w2 = np.concatenate([np.tile(s / max(s[-1], 1e-6), nu), [0.0, 1.0]])
    G.tag(pc, pk=kind, w2=w2)
    return pc


def cord(high: bool) -> dict:
    """The braided cord from the button across the board's top to the corner (rigid on the cap)."""
    c, x, y, n = board_frame()
    e = edge_mid()
    a = c + n * (0.5 * BOARD_T + 0.008)
    p_edge = e + x * 0.012 + n * 0.006
    tp = tassel_points()
    pts = [a, 0.5 * (a + p_edge) + n * 0.005, p_edge, p_edge + x * 0.012 - n * 0.016, v3(tp[0]) + n * 0.004]
    return braid_tube(F._catmull(np.array(pts), 8), 0.0072, 10 if high else 6, PK['cord'], high)


def tassel(high: bool) -> list[dict]:
    p0, p1, p2 = (v3(p) for p in tassel_points())
    pcs = [braid_tube(np.array([p0, 0.5 * (p0 + p1), p1 + v3((0, 0, 0.012))]), 0.0068, 10 if high else 6, PK['hang'], high)]
    # the knot: a bound collar, then a round head the strands spring from
    ax = F._unit(p2 - p1)
    kn = np.array([p1 + ax * (-0.012), p1, p1 + ax * 0.02, p1 + ax * 0.032])
    pcs.append(G.tag(G.tube(kn, np.array([0.011, 0.018, 0.017, 0.016]), 16 if high else 8), pk=PK['knot'], w2=0.0))
    # the strands: a bunch fanning out a little toward the ends
    nstr = 22 if high else 9
    rs = 0.0056 if high else 0.0095
    e1 = F._unit(np.cross(ax, (1.0, 0.0, 0.0)))
    e2 = np.cross(ax, e1)
    for i in range(nstr):
        a = 2 * math.pi * i / nstr * 2.618
        rad = 0.013 * math.sqrt((i + 0.5) / nstr)
        h = N.hash1(i, 551)[0]
        top = p1 + ax * 0.026 + (e1 * math.cos(a) + e2 * math.sin(a)) * rad
        bot = p2 + ax * (-0.01 + 0.02 * float(h)) + (e1 * math.cos(a) + e2 * math.sin(a)) * (rad * 1.9 + 0.006)
        mid = 0.5 * (top + bot) + (e1 * math.cos(a) + e2 * math.sin(a)) * 0.004
        pts = F._catmull(np.array([top, mid, bot]), 6)
        r = np.linspace(rs, rs * 0.75, len(pts))
        pc = G.tube(pts, r, 6 if high else 4)
        w2 = np.concatenate([np.tile(np.linspace(0, 1, len(pts)), 6 if high else 4), [0.0, 1.0]])
        pcs.append(G.tag(pc, pk=PK['strand'], w2=w2, sid=float(h)))
    return pcs


# ----------------------------------------------------------------------------- spectacles
def rim_frame(s: int):
    c = F.EYE_C[s]
    look = F._unit(F.EYE_LOOK[s])
    rc = c + look * SPEC_OUT
    x = F._unit(np.cross(Z, look))
    x = x if x[0] * s > 0 else -x
    y = np.cross(look, x)
    y = y if y[2] > 0 else -y
    return rc, x, y, look


def rim(s: int, high: bool) -> dict:
    rc, x, y, look = rim_frame(s)
    nu, nv = (96, 14) if high else (32, 6)
    u = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    v = np.linspace(0, 2 * math.pi, nv, endpoint=False)
    U, V = np.meshgrid(u, v, indexing='ij')
    # the tube a little deeper (front to back) than wide, so it reads as a solid ring from the front and at an angle
    ring = (SPEC_R + SPEC_TUBE * 0.85 * np.cos(V))
    P = (rc[None, None] + ring[..., None] * (np.cos(U)[..., None] * x + np.sin(U)[..., None] * y)
         + (SPEC_TUBE * 1.15 * np.sin(V))[..., None] * look)
    tor = G.torus(1.0, 0.5, nu, nv)
    w2 = (0.5 + 0.5 * np.sin(V)).ravel()          # 1 at the front face of the ring
    up = (0.5 + 0.5 * np.sin(U)).ravel()          # 1 at the top of the ring
    return G.piece(P.reshape(-1, 3), tor['f'], pk=PK['rim'], w2=w2, up=up)


def rim_point(s: int, ang_deg: float, out: float = 0.0) -> np.ndarray:
    rc, x, y, look = rim_frame(s)
    a = math.radians(ang_deg)
    return rc + (SPEC_R + out) * (math.cos(a) * x + math.sin(a) * y)


def bridge(high: bool) -> dict:
    a = rim_point(1, 168.0, 0.004)
    b = rim_point(-1, 168.0, 0.004)
    top = 0.5 * (a + b) + v3((0.0, -0.006, 0.026))
    pts = F._catmull(np.array([a, 0.5 * (a + top) + v3((0, 0, 0.006)), top, 0.5 * (b + top) + v3((0, 0, 0.006)), b]), 10)
    pc = G.tube(F.resample(pts, 0.004 if high else 0.015), 0.0042, 12 if high else 6)
    return G.tag(pc, pk=PK['bridge'], w2=0.0)


def temple(s: int, high: bool) -> list[dict]:
    """A hinge block on the rim's outer side, and the temple running back along the head, 9 mm off its skin."""
    h0 = rim_point(s, 6.0, SPEC_TUBE * 0.6)              # the rim's frame points outward on both sides
    rc, x, y, look = rim_frame(s)
    hinge = G.rounded_box((0.008, 0.005, 0.0065), 0.002, 0.003 if high else 0.02, 2 if high else 1)
    M = np.stack([x * s, look, y], axis=1)
    hv = h0[None] + hinge['v'] @ M.T + look * (-0.004)
    pcs = [G.piece(hv, hinge['f'], pk=PK['hinge'], w2=0.0)]
    pts = [h0 - look * 0.006]
    ez = float(F.EYE_C[1][2])
    # polish (review: a temple through the raised book): a little closer to the skin and tucked in sooner
    for k, (az, zz) in enumerate(((54.0, ez + 0.009), (68.0, ez + 0.018), (82.0, ez + 0.029), (92.0, ez + 0.038))):
        a = math.radians(az)
        d = np.array([s * math.sin(a), -math.cos(a), 0.0])
        p0 = v3(F.MANTLE[0]).copy()
        p0[2] = zz
        pts.append(F.head_surface(p0 + d * 0.3, out=0.007 if k < 3 else -0.006))
    pts = F.resample(F._catmull(np.array(pts), 10), 0.004 if high else 0.02)
    pc = G.tube(pts, np.linspace(0.0042, 0.0036, len(pts)), 10 if high else 6)
    pcs.append(G.tag(pc, pk=PK['temple'], w2=0.0))
    return pcs


def glint(s: int, high: bool) -> list[dict]:
    """Round 2 (the glass): no lens card (they read as glassy flakes), but two thin glint strokes inside each rim
    on its upper side toward its right, where a soft reflection on clear glass would sit; tapering at both ends."""
    rc, x, y, look = rim_frame(s)
    pcs = []
    for a0, a1, rad, wid in ((118.0, 152.0, 0.8, 0.0038), (124.0, 138.0, 0.62, 0.0026)):
        if s < 0:                                    # the same side of the world for both lenses (toward its right)
            a0, a1 = 180.0 - a1, 180.0 - a0
        nu = 24 if high else 8
        ang = np.radians(np.linspace(a0, a1, nu + 1))
        taper = np.sin(np.linspace(0.0, math.pi, nu + 1)) ** 0.6
        pts = np.array([rc + SPEC_R * rad * (math.cos(aa) * x + math.sin(aa) * y) - look * 0.004 for aa in ang])
        pc = G.tube(pts, np.maximum(wid * taper, 0.0005), 6 if high else 4)
        pcs.append(G.tag(pc, pk=PK['glint'], w2=0.0))
    return pcs


def specs(high: bool) -> list[dict]:
    # round 3: no glint pieces (edge-on they floated as white flecks); the glass's glint is painted on the eye
    return [rim(1, high), rim(-1, high), bridge(high)] + temple(1, high) + temple(-1, high)


def cap(high: bool) -> list[dict]:
    return [skullcap(high), board(high), button(high), cord(high)]
