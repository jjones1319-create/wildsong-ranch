"""Lootlid's gold trim (Art 2.1 Ultra; 1-hero, 2-turnaround, 4-details panels 1, 3 and 5): props baked from detailed
sources, each with real domed rivets.

  - on the box (rigid on `hips`): the rim band all round its top (it stands a little above the wood, hiding most of the
    lid's gap), a strap down each of its four corners, a band along each side's bottom, chunky corner caps at the rim's
    four corners and at the bottom corners, and the hinges' box halves at the back;
  - on the lid (rigid on `head`): an arched strap wrapping each side's rounded edge from the front corner up over the
    barrel top and down the back (the inverted U of the hero and the side view), the hinges' lid halves, and the keyhole
    plate on the front, its keyhole a real cut (lootlid_plate.py);
  - on each post (its shin): a riveted cuff.
Attributes on every piece (the joined lo_props keeps them): 'pk' (the part's kind, below), 'leg' (the post: 1..4),
'bev' (0 on a band's flat top → 1 at its edge), 'top' (1 on the outer face), 'riv' (1 on a rivet), 'u'/'k' (sweep).
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import lootlid_form as F
from monsters.breeds import lootlid_geo as G
from monsters.breeds import lootlid_noise as N

PK_BOX, PK_LID, PK_PLATE, PK_CUFF, PK_HINGE_BOX, PK_HINGE_LID = 1, 2, 3, 4, 5, 6
ATTRS = ('pk', 'leg', 'bev', 'top', 'riv', 'u', 'k', 'cv', 'coin', 'tg', 'emb', 'ham', 'glow', 'deep')
RIVETS: list = []          # every rivet's (centre, radius) on the high source: the paint shades round them
BAND_T = 0.0072            # a band's thickness
SINK = 0.0018              # how far a band's underside sinks into the wood
HINGE_X = (0.2, -0.2)
HINGE_R = 0.0125


def finish(pc: dict, **attrs) -> dict:
    """Every attribute every prop piece carries (zero where unused), so the joined mesh keeps them all."""
    G.tag(pc, **attrs)
    for a in ATTRS:
        if a not in pc['a']:
            pc['a'][a] = np.zeros(len(pc['v']))
    return pc


def profile(a: np.ndarray, half: float, bev: float, t: float) -> np.ndarray:
    """A band's outer height across it: flat, then a rounded bevel down to 45% at the edge."""
    e = np.clip((np.abs(a) - (half - bev)) / bev, 0.0, 1.0)
    return t * (1.0 - 0.55 * (1.0 - np.sqrt(1.0 - e * e)))


def across(half: float, bev: float, high: bool, mid: int = 0) -> np.ndarray:
    """Points across a band: fine on the source; on the game mesh the edges, the bevels' feet and `mid` more between
    (a band wrapped round a rounded corner needs them, or its flat chords sink into the wood)."""
    if high:
        n = max(8, int(2 * half / 0.0016))
        return np.linspace(-half, half, n + 1)
    inner = np.linspace(-half + bev, half - bev, mid + 2)
    return np.concatenate([[-half], inner, [half]])


def slab_rings(base: np.ndarray, nrm: np.ndarray, a: np.ndarray, half: float, bev: float, t: float,
               relief: np.ndarray | None = None, thin: bool = False) -> list[np.ndarray]:
    """Cross-section rings for a band: base (J, K, 3) points on the surface across it, nrm their normals: the outer face
    lifted by the profile (+ relief), the underside sunk (thin: only its two edges, a chord hidden in the wood)."""
    h = profile(a, half, bev, t)[None, :]
    if relief is not None:
        h = h + relief
    top = base + nrm * h[..., None]
    bot = base - nrm * SINK
    if thin:
        return [np.concatenate([top[j], bot[j][[-1, 0]]]) for j in range(len(base))]
    return [np.concatenate([top[j], bot[j][::-1]]) for j in range(len(base))]


def slab_attrs(J: int, K: int, a: np.ndarray, half: float, thin: bool = False) -> dict:
    if thin:
        bev = np.concatenate([np.abs(a) / half, [1.0, 1.0]])
        top = np.concatenate([np.ones(K), np.zeros(2)])
    else:
        bev = np.concatenate([np.abs(a) / half, np.abs(a[::-1]) / half])
        top = np.concatenate([np.ones(K), np.zeros(K)])
    return {'bev': np.tile(bev, J), 'top': np.tile(top, J)}


def band_piece(rings: list[np.ndarray], closed: bool, attrs: dict, ham: np.ndarray | None = None) -> dict:
    pc = G.sweep(rings, closed=closed)
    n_ring = len(rings) * len(rings[0])
    for k, v in attrs.items():
        pc['a'][k] = np.concatenate([v, np.full(len(pc['v']) - n_ring, v.mean() if k != 'top' else 1.0)])
    if ham is not None:
        # the relief on the outer face's points (the underside's 0), per ring
        J, K = ham.shape
        M = len(rings[0])
        hv = np.zeros((J, M))
        hv[:, :K] = ham
        pc['a']['ham'] = np.concatenate([hv.ravel(), np.zeros(len(pc['v']) - n_ring)])
    return pc


def hammer(P: np.ndarray, seed: int) -> np.ndarray:
    """The gold's hammered relief (4-details panel 5): shallow dents and fine dimples, metres outward."""
    f1, f2, _id = N.voronoi(P.reshape(-1, 3), 0.018, seed)
    dent = -0.0011 * N.smooth(0.009, 0.0, f1) * (N.hash1(_id % 100000, seed + 1) > 0.45)
    fine = 0.00025 * N.fbm(P.reshape(-1, 3), 1 / 0.004, seed + 2, 2)
    return (dent + fine).reshape(P.shape[:-1])


def dome(c, n, r: float, h: float, nu: int, nv: int) -> dict:
    """A rivet head: a dome of radius r and height h on the point c, facing n, its base sunk a little."""
    n = np.asarray(n, np.float64)
    n = n / np.linalg.norm(n)
    rows = [(-0.0015, 0.0, 0.0, 0.0, 0.0), (-0.0015, r, r, 0.0, 0.0)]
    for ph in np.radians(np.linspace(0, 90, nv + 1))[:-1]:
        rows.append((h * math.sin(ph), r * math.cos(ph), r * math.cos(ph), 0.0, 0.0))
    rows.append((h, 0.0, 0.0, 0.0, 0.0))
    pc = G.loft(rows, G.unit_ring(2.0, nu))
    x = np.cross(n, [0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.cross(n, [1.0, 0.0, 0.0])
    x /= np.linalg.norm(x)
    y = np.cross(n, x)
    pc['v'] = np.asarray(c)[None] + pc['v'] @ np.stack([x, y, n])
    return G.outward(pc)


def rivets(points, normals, high: bool, r: float = 0.0145, h: float = 0.0085, **attrs) -> list[dict]:
    """Round domed rivet heads (round 2: about twice the size, smooth on the game mesh too)."""
    nu, nv = (40, 10) if high else (12, 2)
    if high:
        RIVETS.extend((np.asarray(p, np.float64), r) for p in points)
    return [finish(dome(p, n, r, h, nu, nv), riv=1.0, top=1.0, **attrs) for p, n in zip(points, normals)]


# ----------------------------------------------------------------------------- the box's surface
_BOX: dict = {}


def box_table():
    if not _BOX:
        _BOX['cs'] = G.unit_ring(F.BOX_N, 4096, F.BOX_B / F.BOX_A)
        c, s = _BOX['cs']
        k = np.nonzero((c > 0) & (s > 0))[0]
        _BOX['uc'] = float(k[np.argmin(np.abs(c[k] - s[k]))] / 4096)      # the corner (45° on the ring)
    return _BOX


def box_point(u, z) -> np.ndarray:
    """The box's outer surface at ring position u (0..1, arc length, CCW from +X) and height z (the rim's own rounding
    ignored: a band there stands just clear of it)."""
    T = box_table()
    u = np.mod(np.asarray(u, np.float64), 1.0)
    z = np.asarray(z, np.float64)
    i = u * 4096
    i0 = np.floor(i).astype(int) % 4096
    t = i - np.floor(i)
    c = T['cs'][0][i0] * (1 - t) + T['cs'][0][(i0 + 1) % 4096] * t
    s = T['cs'][1][i0] * (1 - t) + T['cs'][1][(i0 + 1) % 4096] * t
    zc = np.clip(z, F.Z_BOT, F.Z_BTOP - 0.001)
    ab = np.array([F.box_ab(float(v)) for v in np.ravel(zc)]).reshape(np.shape(zc) + (2,))
    x, y = G.ring_xy((c, s), ab[..., 0], ab[..., 1], F.BOX_BULGE)
    return np.stack([x, y, np.broadcast_to(z, np.shape(x))], axis=-1)


def box_normal(u, z) -> np.ndarray:
    du, dz = 1e-4, 1e-3
    pu = box_point(np.asarray(u) + du, z) - box_point(np.asarray(u) - du, z)
    pz = box_point(u, np.asarray(z) + dz) - box_point(u, np.asarray(z) - dz)
    n = np.cross(pu, pz)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def box_perimeter(z: float) -> float:
    p = box_point(np.linspace(0, 1, 2048, endpoint=False), np.full(2048, z))
    return float(np.linalg.norm(np.roll(p, -1, axis=0) - p, axis=1).sum())


def box_band(us: np.ndarray, zs: np.ndarray, high: bool, half: float, bev: float, t: float, closed: bool, seed: int,
             horizontal: bool, mid: int = 0) -> dict:
    """A band on the box: along u at heights zc ± half (horizontal), or along z at ring positions uc ± half (vertical)."""
    a = across(half, bev, high, mid)
    if horizontal:
        U, Z = np.meshgrid(us, zs[0] + a, indexing='ij')
    else:
        per = np.array([box_perimeter(float(z)) for z in zs])
        U = us[0] + a[None, :] / per[:, None]
        Z = np.repeat(zs[:, None], len(a), axis=1)
    base = box_point(U, Z)
    nrm = box_normal(U, Z)
    rel = hammer(base, seed) if high else None
    rings = slab_rings(base, nrm, a, half, bev, t, rel, thin=not high)
    return finish(band_piece(rings, closed, slab_attrs(len(rings), len(a), a, half, thin=not high), rel), pk=PK_BOX)


def box_trim(high: bool) -> list[dict]:
    T = box_table()
    uc = T['uc']
    corners = [uc, 0.5 - uc, 0.5 + uc, 1.0 - uc]
    out = []
    step = 0.0016 if high else 0.02
    # the rim band, all round: its top 1.5 cm over the wood (most of the gap hidden)
    z_rim, half_rim = 0.4545, 0.036
    n = int(box_perimeter(z_rim) / step)
    us = np.linspace(0, 1, n, endpoint=False)
    out.append(box_band(us, np.array([z_rim]), high, half_rim, 0.006, BAND_T, True, 11, True))
    # the corner straps, under the rim band down to the bottom caps
    for i, u0 in enumerate(corners):
        zs = np.linspace(0.205, 0.43, int(0.225 / (0.0016 if high else 0.025)) + 1)
        out.append(box_band(np.array([u0]), zs, high, 0.04, 0.006, BAND_T * 0.9, False, 20 + i, False, mid=6))
    # the sides' bottom bands (left and right faces only, 2-turnaround side view)
    per = box_perimeter(0.222)
    dw = 0.042 / per
    for side, (u_a, u_b) in enumerate(((-(uc - dw), uc - dw), (0.5 - uc + dw, 0.5 + uc - dw))):
        n = max(2, int((u_b - u_a) * per / step))
        out.append(box_band(np.linspace(u_a, u_b, n + 1), np.array([0.222]), high, 0.022, 0.005, BAND_T * 0.9, False, 30 + side, True))
    # the caps: chunky, at the rim's corners and at the bottom corners
    for i, u0 in enumerate(corners):
        per = box_perimeter(0.45)
        hw = 0.042 / per
        k = int(2 * hw * per / (0.0016 if high else 0.012)) + 1
        out.append(box_band(np.linspace(u0 - hw, u0 + hw, k + 1), np.array([0.4495]), high, 0.0395, 0.008, 0.0135, False, 40 + i, True, mid=1))
        per = box_perimeter(0.2)
        hw = 0.044 / per
        k = int(2 * hw * per / (0.0016 if high else 0.012)) + 1
        out.append(box_band(np.linspace(u0 - hw, u0 + hw, k + 1), np.array([0.2]), high, 0.031, 0.007, 0.012, False, 50 + i, True, mid=1))
    # rivets: along the rim band (clear of the caps and the hinges), three down each strap, three on each side band,
    # two on each cap's faces
    pts, nrms = [], []
    per = box_perimeter(z_rim)
    for u in np.arange(0.0, 1.0, 0.088 / per) + 0.5 * 0.088 / per:
        p = box_point(u, z_rim)
        if min(abs(((u - c + 0.5) % 1.0) - 0.5) for c in corners) * per < 0.066:
            continue
        if p[1] > 0 and min(abs(p[0] - hx) for hx in HINGE_X) < 0.065:
            continue
        pts.append(p)
        nrms.append(box_normal(u, z_rim))
    for u0 in corners:
        for z in (0.255, 0.33):
            pts.append(box_point(u0, z))
            nrms.append(box_normal(u0, z))
    for u_mid in (0.0, 0.5):
        per = box_perimeter(0.222)
        for du in (-0.1, 0.1):
            pts.append(box_point(u_mid + du / per, 0.222))
            nrms.append(box_normal(u_mid + du / per, 0.222))
    lift_r = [(p + n_ * BAND_T) for p, n_ in zip(pts, nrms)]
    out += rivets(lift_r, nrms, high, pk=PK_BOX)
    cap_pts, cap_n = [], []
    for u0 in corners:
        for z, off in ((0.4495, 0.026), (0.2, 0.026)):
            per = box_perimeter(z)
            for d in (-off, off) if z > 0.3 else (0.0,):
                cap_pts.append(box_point(u0 + d / per, z))
                cap_n.append(box_normal(u0 + d / per, z))
    out += rivets([p + n_ * 0.0135 for p, n_ in zip(cap_pts, cap_n)], cap_n, high, r=0.0125, h=0.0075, pk=PK_BOX)
    out.append(rim_flange(high))
    return out


def rim_flange(high: bool) -> dict:
    """A flat gold lip over the box's wooden rim (round 2), from the rim band's face to just inside the hollow: it closes
    the seam's slit (nothing inside shows through a shut lid) and frames the open mouth's front."""
    T_ = box_table()
    n = int(box_perimeter(0.47) / (0.0025 if high else 0.02))
    us = np.linspace(0, 1, n, endpoint=False)
    a, b = F.box_ab(F.Z_BTOP - 0.001)
    rows = [(-0.0072, 0.4905), (F.WALL - 0.002, 0.4905), (F.WALL + 0.003, 0.4893), (F.WALL + 0.003, 0.4868), (-0.0072, 0.4868)]
    c, s_ = np.interp(us * 4096, np.arange(4096), T_['cs'][0], period=4096), np.interp(us * 4096, np.arange(4096), T_['cs'][1], period=4096)
    rings = []
    for j in range(n):
        ring = []
        for ins, z in rows:
            x, y = G.ring_xy((np.array([c[j]]), np.array([s_[j]])), a - ins, b - ins, F.BOX_BULGE)
            ring.append([x[0], y[0], z])
        rings.append(np.array(ring))
    return finish(G.sweep(rings, closed=True), pk=PK_BOX, top=1.0, bev=0.3)


def lid_flange(high: bool) -> dict:
    """Round 3: a gold lip under the lid's wall (its opening's edge), from just outside its face to just inside its
    hollow: an open lid shows a thick wooden rim trimmed in gold, not a paper edge."""
    cs = G.unit_ring(F.LID_N, 4096, F.LID_B / F.LID_A)
    n = int(2.3 / (0.0025 if high else 0.02))
    us = np.linspace(0, 1, n, endpoint=False)
    c = np.interp(us * 4096, np.arange(4096), cs[0], period=4096)
    s_ = np.interp(us * 4096, np.arange(4096), cs[1], period=4096)
    a, b = F.lid_ab(F.Z_LB + 0.004)
    W, cy = F.LID_WALL, 0.5 * F.LID_FRONT_EXTRA
    z0, z1 = F.Z_LB - 0.0026, F.Z_LB + 0.0004
    # (share of the wall, z): 0 is the lid's outer face, 1 its inner wall
    rows = [(-0.06, z1 + 0.004), (-0.06, z0 + 0.0008), (0.0, z0), (1.0, z0), (1.08, z0 + 0.0008), (1.08, z1 + 0.004)]
    rings = []
    for j in range(n):
        ring = []
        for f, z in rows:
            x, y = G.ring_xy((np.array([c[j]]), np.array([s_[j]])), a - W * f, b - (W + cy) * f, F.LID_BULGE)
            ring.append([x[0], y[0] + cy * f, z])
        rings.append(np.array(ring))
    return finish(G.sweep(rings, closed=True), pk=PK_LID, top=1.0, bev=0.3)


def build(high: bool, quick: bool) -> list:
    """The gold, as four objects (the weights go by each vertex's 'pk')."""
    from monsters.breeds import lootlid_plate as PL
    from monsters.breeds import lootlid_straps as SP
    tag = 'hi' if high else 'lo'
    groups = {'trim_box': box_trim(high), 'trim_lid': SP.lid_straps(high) + PL.build(high) + [lid_flange(high)], 'trim_legs': SP.cuffs(high),
              'trim_hinges': SP.hinges(high)}
    obs = [G.make_object(f'{tag}_{k}', G.merge(v)) for k, v in groups.items()]
    if not high:
        for ob in obs:
            set_texel_k(ob)
    return obs


def set_texel_k(ob) -> None:
    """A game-mesh prop's per-face share of the atlas (the FACE attribute texel_k): faces nobody sees (a band's
    underside in the wood, the heap's sides, the coins' backs) get little; the keyhole plate and the tongue more."""
    me = ob.data
    nf = len(me.polygons)
    fn = np.empty(nf * 3, np.float32)
    me.polygons.foreach_get('normal', fn)
    fn = fn.reshape(-1, 3)
    ls = np.empty(nf, np.int64)
    lt = np.empty(nf, np.int64)
    me.polygons.foreach_get('loop_start', ls)
    me.polygons.foreach_get('loop_total', lt)
    vi = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get('vertex_index', vi)

    def face_mean(name: str) -> np.ndarray:
        if name not in me.attributes:
            return np.zeros(nf)
        a = np.empty(len(me.vertices), np.float32)
        me.attributes[name].data.foreach_get('value', a)
        return np.add.reduceat(a[vi].astype(np.float64), ls) / lt
    pk, top, riv = np.round(face_mean('pk')).astype(int), face_mean('top'), face_mean('riv')
    nz = fn[:, 2]
    k = np.ones(nf)
    trim = np.isin(pk, (PK_BOX, PK_LID, PK_CUFF, PK_HINGE_BOX, PK_HINGE_LID))
    k = np.where(trim & (top < 0.5), 0.12, k)
    k = np.where(trim & (riv > 0.5), 0.7, k)
    k = np.where(pk == PK_PLATE, np.where(top < 0.5, 0.2, 1.35), k)
    k = np.where(pk == 7, np.where(nz < -0.2, 0.25, 0.9), k)
    k = np.where(pk == 10, np.where(nz < 0.4, 0.12, 0.75), k)
    k = np.where(pk == 11, np.where(nz < -0.5, 0.6, 1.0), k)
    k = np.where(pk == 8, 1.2, k)
    k = np.where(pk == 9, 0.35, k)
    if 'texel_k' in me.attributes:
        me.attributes.remove(me.attributes['texel_k'])
    me.attributes.new('texel_k', 'FLOAT', 'FACE').data.foreach_set('value', k.astype(np.float32))
