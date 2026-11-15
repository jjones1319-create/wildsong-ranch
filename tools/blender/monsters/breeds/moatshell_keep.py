"""Moatshell's keep meshes (Art 2.1 Ultra): the castle of moatshell_castle.py built as rigid props, the game mesh
(`high` False: a few centimetres a step, crisp merlons and blocks) and the high source (`high` True: about 3 mm, the
bricks, grooves, chips, pits, slits and moss bumps displaced into it). Both come from the same parametric surfaces, so
the bake's rays find the source a few millimetres from the game mesh everywhere.

Paint attributes on the high source: ck (the kind: 1 coursed wall brick, 2 big block (skirt, merlon, parapet), 3 floor
paving, 4 brick-red (window and door voussoirs), 5 wood (door, rails, pole), 6 iron, 7 flag cloth, 8 the finial),
bid (0..1 per brick or block), mortar, bedge (near an edge), chip, pit, red, slit, moss, u (along the wood or flag).
The game mesh carries cpart (1 on the flag: its chain weights) and tk (texel density share, made a face attribute).
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import moatshell_castle as K
from monsters.breeds import moatshell_geo as G
from monsters.breeds import moatshell_noise as N

TAU = K.TAU
smooth = N.smooth
CK = {'wall': 1, 'block': 2, 'floor': 3, 'red': 4, 'wood': 5, 'iron': 6, 'flag': 7, 'finial': 8}


def _tang(th):
    return np.stack([np.cos(th), np.sin(th)], axis=-1)


def map_ring(loc: np.ndarray, thc: float, rc: float, zc: float) -> np.ndarray:
    """Local (x across, y out, z up) round the keep's axis at radius rc: x bends along the ring (toward the monster's
    right for +x, so the frame stays right-handed)."""
    th = thc - loc[:, 0] / rc
    R = rc + loc[:, 1]
    d = K.dirv(th)
    return np.stack([d[:, 0] * R, d[:, 1] * R, zc + loc[:, 2]], axis=1)


def map_wall(loc: np.ndarray, which: str, thc: float, zc: float) -> np.ndarray:
    """Local (x across, y out of the wall's surface, z up) on the main wall or the tower, following its batter."""
    z = zc + loc[:, 2]
    r = K.wall_radius(which, z)
    th = thc - loc[:, 0] / r
    R = r + loc[:, 1]
    d = K.dirv(th)
    return np.stack([d[:, 0] * R, d[:, 1] * R, z], axis=1)


def map_skirt(loc: np.ndarray, thc: float) -> np.ndarray:
    """Local (x across, y down the slope, z out of the slab) on the skirt's slope; z = +T/2 is the outer face."""
    L = float(K.skirt_len(thc))
    rmid = K.SKIRT_RI + 0.5 * (float(K.skirt_ro(thc)) - K.SKIRT_RI)
    th = thc - loc[:, 0] / rmid
    s = np.clip(0.5 + loc[:, 1] / L, -0.2, 1.2)
    P = K.skirt_outer(th, s)
    nr, nz = K.skirt_normal(th)
    d = K.dirv(th)
    off = loc[:, 2] - 0.5 * K.SKIRT_T
    return P + np.stack([d[:, 0] * nr * off, d[:, 1] * nr * off, nz * off], axis=1)


def rot_xz(loc: np.ndarray, phi: float) -> np.ndarray:
    """Turn local points by phi in the x–z plane (about −y)."""
    c, s = math.cos(phi), math.sin(phi)
    out = loc.copy()
    out[:, 0] = loc[:, 0] * c - loc[:, 2] * s
    out[:, 2] = loc[:, 0] * s + loc[:, 2] * c
    return out


def box_on(half, r, step, rows, mapper, high: bool, **attrs) -> dict:
    """A rounded box placed by `mapper(local) -> world`; keeps 'edge' and the local position 'lz' (its height share)."""
    b = G.rounded_box(half, r, step, rows if high else 1)
    loc = b['v']
    pc = G.piece(mapper(loc), b['f'], edge=b['a']['edge'], lz=loc[:, 2] / max(half[2], 1e-6), ly=loc[:, 1] / max(half[1], 1e-6))
    return G.tag(pc, **attrs)


# ----------------------------------------------------------------------------- drums (the main wall, the tower)
def drum(which: str, step: float, high: bool) -> dict:
    """The outer face, the parapet's top and its inner face down to the floor, as one grid round the ring."""
    if which == 'wall':
        r_top, t, ztop, zin = K.WALL_RT, K.WALL_T, K.WALL_ZTOP, K.FLOOR_Z - 0.01
        zbot = lambda th: K.wall_zbot(th)  # noqa: E731
        rfun = K.wall_r
    else:
        r_top, t, ztop, zin = K.TOWER_RT, K.TOWER_T, K.TOWER_ZTOP, K.TOWER_FLOOR - 0.008
        zbot = lambda th: np.full_like(th, K.TOWER_Z0)  # noqa: E731
        rfun = K.tower_r
    nth = max(24, int(round(TAU * r_top / step)))
    th = np.arange(nth) * TAU / nth
    zb = zbot(th)
    nz_out = max(4, int(round((ztop - float(zb.min())) / step)))
    v_out = np.linspace(0.0, 1.0, nz_out + 1)
    n_top = max(1, int(round(t / step)))
    n_in = max(1, int(round((ztop - zin) / step)))
    # one profile per θ: up the outer face, across the top (inward), down the inner face
    Z = zb[:, None] + v_out[None, :] * (ztop - zb[:, None])
    R = rfun(Z)
    prof_r = [R]
    prof_z = [Z]
    rt = np.linspace(r_top, r_top - t, n_top + 1)[1:]
    prof_r.append(np.broadcast_to(rt, (nth, n_top)))
    prof_z.append(np.full((nth, n_top), ztop))
    zi = np.linspace(ztop, zin, n_in + 1)[1:]
    prof_r.append(np.full((nth, n_in), r_top - t))
    prof_z.append(np.broadcast_to(zi, (nth, n_in)))
    Rr = np.concatenate(prof_r, axis=1)
    Zz = np.concatenate(prof_z, axis=1)
    part = np.concatenate([np.zeros(nz_out + 1), np.ones(n_top), np.full(n_in, 2.0)])
    nv = Rr.shape[1] - 1
    d = K.dirv(th)
    P = np.stack([d[:, None, 0] * Rr, d[:, None, 1] * Rr, Zz], axis=-1).reshape(-1, 3)
    F = G.grid_faces(nth, nv, wrap_u=True)
    TH = np.repeat(th, nv + 1)
    pc = G.piece(P, F, th=TH, dpart=np.tile(part, nth))
    # the strip winds one way all along its profile: check it on the outer face (radially out)
    outer = pc['a']['dpart'][pc['f']].max(axis=1) == 0
    v, f = pc['v'], pc['f'][outer]
    nrm = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    cen = v[f].mean(axis=1)
    if float(np.einsum('ij,ij->i', nrm[:, :2], cen[:, :2]).mean()) < 0:
        pc['f'] = pc['f'][:, ::-1]
    return pc


def _orient(pc: dict, expect) -> None:
    """Flip every face if most of them face against `expect(face centres) -> direction`."""
    v, f = pc['v'], pc['f']
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)
    cen = v[f].mean(axis=1)
    e = expect(cen)
    if float(np.sum(np.einsum('ij,ij->i', n, e) > 0)) < 0.5 * len(f):
        pc['f'] = pc['f'][:, ::-1]


def floor_disc(r_in: float, r_out: float, z: float, step: float) -> dict:
    """An annulus (or a disc, r_in 0) facing up."""
    nr = max(1, int(round((r_out - r_in) / step)))
    nth = max(24, int(round(TAU * r_out / step)))
    th = np.arange(nth) * TAU / nth
    rr = np.linspace(max(r_in, 0.004), r_out, nr + 1)
    d = K.dirv(th)
    P = np.stack([d[:, None, 0] * rr[None], d[:, None, 1] * rr[None], np.full((nth, nr + 1), z)], axis=-1).reshape(-1, 3)
    pc = G.piece(P, G.grid_faces(nth, nr, wrap_u=True), th=np.repeat(th, nr + 1), rr=np.tile(rr, nth))
    _orient(pc, lambda c: np.tile([0.0, 0.0, 1.0], (len(c), 1)))
    if r_in <= 0:
        # close the hole at the centre with a fan
        c = len(pc['v'])
        fan = [[c, i * (nr + 1), ((i + 1) % nth) * (nr + 1), ((i + 1) % nth) * (nr + 1)] for i in range(nth)]
        pc['v'] = np.concatenate([pc['v'], [[0.0, 0.0, z]]])
        for k in pc['a']:
            pc['a'][k] = np.concatenate([pc['a'][k], [0.0]])
        fan = np.array(fan, np.int64)
        a, b, cc = pc['v'][fan[:, 0]], pc['v'][fan[:, 1]], pc['v'][fan[:, 2]]
        if float(np.cross(b - a, cc - a)[:, 2].mean()) < 0:
            fan = fan[:, [0, 2, 1, 1]]
        pc['f'] = np.concatenate([pc['f'], fan])
    return pc


# ----------------------------------------------------------------------------- blocks and merlons
def skirt_blocks(step: float, high: bool) -> list[dict]:
    out = []
    for k, thc in enumerate(K.skirt_block_angles()):
        L = float(K.skirt_len(thc))
        rmid = K.SKIRT_RI + 0.5 * (float(K.skirt_ro(thc)) - K.SKIRT_RI)
        hx = 0.5 * (TAU * rmid / K.SKIRT_N - K.SKIRT_GAP)
        half = (hx, 0.5 * L - 0.003, 0.5 * K.SKIRT_T)
        pc = box_on(half, K.SKIRT_ROUND, step, 6, lambda loc, thc=thc: map_skirt(loc, thc), high,
                    ck=CK['block'], bid=float(N.hash1(k, 61)[0]), part=1.0)
        out.append(pc)
    return out


def merlons(which: str, step: float, high: bool) -> list[dict]:
    if which == 'wall':
        n, share, h, rt, t, ztop, seed = K.MERLON_N, K.MERLON_SHARE, K.MERLON_H, K.WALL_RT, K.WALL_T, K.WALL_ZTOP, 71
    else:
        n, share, h, rt, t, ztop, seed = K.TMERLON_N, K.TMERLON_SHARE, K.TMERLON_H, K.TOWER_RT, K.TOWER_T, K.TOWER_ZTOP, 81
    rc = rt - 0.5 * t
    sink = 0.012
    out = []
    for k in range(n):
        thc = (k + 0.5) * TAU / n
        hx = 0.5 * share * TAU * rc / n
        half = (hx, 0.5 * t + 0.005, 0.5 * (h + sink))          # 5 mm proud of the wall's face: chunky
        zc = ztop - sink + half[2]
        pc = box_on(half, 0.0042, step, 5, lambda loc, thc=thc, rc=rc, zc=zc: map_ring(loc, thc, rc, zc), high,
                    ck=CK['block'], bid=float(N.hash1(k, seed)[0]), part=2.0)
        out.append(pc)
    return out


# ----------------------------------------------------------------------------- window and door voussoirs
def _voussoir_layout(a: float, hb: float, hs: float, k: float, n_arch: int, n_jamb: int, sill: bool):
    """(centre (x, z), half (across, along), turn) of each brick round an arched opening of half-width a: the jambs from
    −hb up to the spring line hs, `n_arch` voussoirs over the arch, a sill below."""
    w = 0.0105 * k                       # half the bricks' width across the frame
    ring = a + w + 0.0012
    out = []
    hj = (hb + hs) / n_jamb
    for sgn in (-1.0, 1.0):
        for j in range(n_jamb):
            zc = -hb + (j + 0.5) * hj
            out.append(((sgn * ring, zc), (w, 0.5 * hj - 0.0013 * k), 0.0))
    for j in range(n_arch):
        phi = (j + 0.5) * math.pi / n_arch
        c = (ring * math.cos(phi), hs + ring * math.sin(phi))
        ht = 0.5 * (math.pi * ring / n_arch) - 0.0013 * k
        out.append((c, (w, ht), phi))
    if sill:
        out.append(((0.0, -hb - 0.0085 * k), (a + 2 * w + 0.002, 0.0072 * k), 0.0))
    return out


def opening_bricks(which: str, thc_deg: float, zc: float, step: float, high: bool, k: float, n_arch: int, n_jamb: int,
                   sill: bool, a: float, hb: float, hs: float, seed: int) -> list[dict]:
    out = []
    depth = 0.0098 * k
    for i, ((cx, cz), (hw, hl), phi) in enumerate(_voussoir_layout(a, hb, hs, k, n_arch, n_jamb, sill)):
        if phi:
            half = (hw, depth, hl)          # its width runs out from the arch's centre (local x), turned by phi
        else:
            half = (hw, depth, hl)

        def mapper(loc, cx=cx, cz=cz, phi=phi):
            q = rot_xz(loc, phi) if phi else loc.copy()
            q[:, 0] += cx
            q[:, 1] += 0.0006
            q[:, 2] += cz
            return map_wall(q, which, math.radians(thc_deg), zc)
        out.append(box_on(half, 0.0032 * k, step, 3, mapper, high, ck=CK['red'], bid=float(N.hash1(i, seed)[0]), part=3.0))
    return out


def windows(step: float, high: bool) -> list[dict]:
    out = []
    for i, (which, thd, zc) in enumerate(K.WINDOWS):
        sp = K.SLIT[which]
        k = 1.0 if which == 'wall' else 0.86
        out += opening_bricks(which, thd, zc, step, high, k, 5, 2, True, sp['a'], sp['hb'], sp['hs'], 900 + 17 * i)
    return out


def door(step: float, high: bool) -> list[dict]:
    """The arched plank door (a slab 4 mm proud of the wall, sunk into it behind), its brick arch, two iron straps and a
    ring on a plate."""
    D = K.DOOR
    thc = math.radians(D['th'])
    z0 = K.door_z0()
    R, rect, thick = 0.5 * D['w'], D['rect'], D['thick']
    nu = max(4, int(round(D['w'] / step)))
    nv = max(4, int(round((rect + R) / step)))
    X, V = np.meshgrid(np.linspace(-R, R, nu + 1), np.linspace(0.0, 1.0, nv + 1), indexing='ij')
    top = rect + np.sqrt(np.maximum(R * R - X * X, 0.0))
    loc = np.stack([X.ravel(), np.full(X.size, D['proud'] - 0.5 * thick), (V * top).ravel()], axis=1)
    P = map_wall(loc, 'wall', thc, z0)
    P2 = map_wall(loc + np.array([0.0, 0.001, 0.0]), 'wall', thc, z0)
    Nn = (P2 - P) / 0.001
    sheet = G.thick_sheet(P, Nn, nu, nv, thick)
    sheet['f'] = sheet['f'][:, ::-1]          # the grid (across, up) winds into the wall: face it out
    xs = np.concatenate([X.ravel(), X.ravel()])
    zs = np.concatenate([(V * top).ravel(), (V * top).ravel()])
    out = [G.tag(G.piece(sheet['v'], sheet['f']), ck=CK['wood'], u=xs, w2=zs, part=4.0, bid=0.3)]
    out += opening_bricks('wall', D['th'], z0, step, high, 1.15, 9, 4, False, R, 0.0, rect, 977)
    for i, zc in enumerate((0.03, 0.094)):
        def mp(loc, zc=zc):
            q = loc.copy()
            q[:, 0] += -0.012
            q[:, 1] += D['proud'] + 0.0016
            q[:, 2] += zc
            return map_wall(q, 'wall', thc, z0)
        out.append(box_on((0.046, 0.0022, 0.0064), 0.0015, step, 2, mp, high, ck=CK['iron'], bid=0.2 + 0.3 * i, part=4.0))
    tor = G.torus(0.0135, 0.0027, 40 if high else 12, 12 if high else 6)
    q = tor['v'][:, [0, 2, 1]] + np.array([0.033, D['proud'] + 0.0045, 0.054])
    out.append(G.tag(G.piece(map_wall(q, 'wall', thc, z0), tor['f'][:, ::-1]), ck=CK['iron'], bid=0.7, part=4.0))

    def plate(loc):
        q = loc.copy()
        q[:, 0] += 0.033
        q[:, 1] += D['proud'] + 0.0012
        q[:, 2] += 0.069
        return map_wall(q, 'wall', thc, z0)
    out.append(box_on((0.0075, 0.0018, 0.0075), 0.0015, step, 2, plate, high, ck=CK['iron'], bid=0.5, part=4.0))
    return out


def rails(step: float, high: bool) -> list[dict]:
    out = []
    for spec in (K.RAIL, K.TRAIL):
        nu = max(48, int(round(TAU * spec['r'] / (0.6 * step)))) if high else (96 if spec is K.RAIL else 48)
        tor = G.torus(spec['r'], spec['tube'], nu, 16 if high else 6)
        v = tor['v'] + np.array([0.0, 0.0, spec['z']])
        ang = np.arctan2(v[:, 1], v[:, 0])
        out.append(G.piece(v, tor['f'], ck=CK['wood'], u=ang * spec['r'], w2=np.zeros(len(v)), part=5.0, bid=0.6))
    return out


def pole(step: float, high: bool) -> list[dict]:
    P, F = K.POLE, K.FINIAL
    n = 80 if high else 3
    pts = np.stack([np.zeros(n), np.zeros(n), np.linspace(P['z0'], P['z1'], n)], axis=1)
    tb = G.tube(pts, P['r'], 28 if high else 10)
    out = [G.piece(tb['v'], tb['f'], ck=CK['wood'], u=tb['v'][:, 2], w2=np.arctan2(tb['v'][:, 1], tb['v'][:, 0]) * P['r'],
                   part=6.0, bid=0.45)]
    sp = G.uv_sphere((0.0, 0.0, F['z']), F['r'], 40 if high else 12, 20 if high else 7)
    out.append(G.piece(sp['v'], sp['f'], ck=CK['finial'], u=sp['v'][:, 2], part=6.0, bid=0.5))
    for z, R_, r_ in ((P['z1'] - 0.0005, 0.0118, 0.0042), (0.951, 0.0122, 0.0027), (0.9455, 0.0122, 0.0027)):
        tor = G.torus(R_, r_, 36 if high else 10, 10 if high else 5)
        v = tor['v'] + np.array([0.0, 0.0, z])
        out.append(G.piece(v, tor['f'], ck=CK['wood'], u=v[:, 2], part=6.0, bid=0.15 if z < 1.0 else 0.5, rope=float(z < 1.0)))
    return out


def flag(step: float, high: bool) -> dict:
    """The swallow-tailed pennant: a 4.5 mm slab rippling as it flies back-left from the pole."""
    Fp = K.FLAG
    a, n = K.flag_axes()
    nu = max(16, int(round(Fp['len'] / step))) if high else 16
    nv = max(6, int(round(Fp['h0'] / step))) if high else 6
    U, V = np.meshgrid(np.linspace(0.0, 1.0, nu + 1), np.linspace(-1.0, 1.0, nv + 1), indexing='ij')
    x = Fp['off'] + U * Fp['len'] - Fp['notch'] * (1.0 - np.abs(V)) * smooth(0.55, 1.0, U)
    h = Fp['h0'] + (Fp['h1'] - Fp['h0']) * U
    ztop = Fp['zc'] + 0.5 * Fp['h0'] - 0.006 * U - 0.01 * U * U
    z = ztop - 0.5 * (1.0 - V) * h
    wave = 0.017 * np.sin(TAU * 0.95 * U + 0.4) * U ** 0.8 + 0.005 * np.sin(TAU * 2.1 * U + 1.1 * V + 0.3) * U
    dw = np.gradient(wave, axis=0) / np.maximum(np.gradient(x, axis=0), 1e-6)
    P = a[None, None] * x[..., None] + n[None, None] * wave[..., None] + np.stack([np.zeros_like(z), np.zeros_like(z), z], axis=-1)
    Nn = n[None, None] - a[None, None] * dw[..., None]
    Nn /= np.linalg.norm(Nn, axis=-1, keepdims=True)
    sheet = G.thick_sheet(P.reshape(-1, 3), Nn.reshape(-1, 3), nu, nv, Fp['thick'])
    uu = np.concatenate([U.ravel(), U.ravel()])
    vv = np.concatenate([V.ravel(), V.ravel()])
    return G.piece(sheet['v'], sheet['f'], ck=CK['flag'], u=uu, w2=vv, part=7.0, cpart=1.0, bid=0.5)


def floors(step: float, high: bool) -> list[dict]:
    a = floor_disc(K.TOWER_RB - 0.004, K.WALL_RT - K.WALL_T + 0.004, K.FLOOR_Z, step)
    b = floor_disc(0.0, K.TOWER_RT - K.TOWER_T + 0.003, K.TOWER_FLOOR, step)
    return [G.tag(a, ck=CK['floor'], part=8.0, which=0.0), G.tag(b, ck=CK['floor'], part=8.0, which=1.0)]


def pieces(step: float, high: bool) -> list[dict]:
    """Every part of the keep (not yet displaced). The game mesh takes its own step per part."""
    st = (lambda lo: step) if high else (lambda lo: lo)  # noqa: E731
    # the high wall finer (round 2: Porcelain's painted blooms were soft there)
    wl = G.tag(drum('wall', (0.65 * step) if high else 0.025, high), ck=CK['wall'], part=9.0, which=0.0)
    tw = G.tag(drum('tower', st(0.022), high), ck=CK['wall'], part=9.0, which=1.0)
    out = [wl, tw] + floors(st(0.05), high) + skirt_blocks(st(0.045), high)
    out += merlons('wall', st(0.05), high) + merlons('tower', st(0.05), high)
    out += windows(st(0.05), high) + door(st(0.03), high)
    out += rails(step, high) + pole(step, high) + [flag(step, high)]
    return out


# ----------------------------------------------------------------------------- the high source's relief and paint attributes
def _moss(pc: dict, mortar: np.ndarray) -> np.ndarray:
    """0..1 moss (round 1: tufts and short vines, not smears): in the mortar seams at the wall's foot and under the
    parapet, short trailing vines under some crenels, on the rampart's top ledge and in its gaps, at the merlons' feet
    and on some of their tops, patches on the floors (1-hero, 4-details panel 6)."""
    P, a = pc['v'], pc['a']
    part = float(a['part'][0])
    patch = smooth(0.05, 0.4, N.fbm(P, 1 / 0.04, 501, 3))
    tuft = smooth(-0.2, 0.45, N.fbm(P, 1 / 0.009, 502, 2))
    n = len(P)
    w = np.zeros(n)
    if part == 9.0:
        th, z, dp = a['th'], P[:, 2], a['dpart']
        wall = float(a['which'][0]) == 0.0
        base = K.skirt_zt(th) if wall else np.full(n, K.FLOOR_Z)
        nm, ztop = (K.MERLON_N, K.WALL_ZTOP) if wall else (K.TMERLON_N, K.TOWER_ZTOP)
        # round 2: clumps (thin trailing vines read as cracks): in the lower mortar seams and spilling over the
        # bricks round them, and in tufts under the parapet
        seam = np.maximum(smooth(0.11, 0.0, z - base), 0.7 * smooth(0.05, 0.0, ztop - z))
        clump = smooth(0.25, 0.55, N.fbm(P, 1 / 0.03, 504, 2))
        w = seam * np.maximum(mortar * patch, clump * patch)
        w = np.where(dp > 0, 0.75 * patch, w)
    elif part == 1.0:
        ledge = smooth(-0.45, -0.85, a['ly']) * smooth(0.2, 0.7, a['lz'])
        gaps = smooth(0.014, 0.004, a['edge']) * smooth(0.4, -0.4, a['ly'])
        w = np.maximum(1.0 * ledge * smooth(0.0, 0.25, patch), 0.85 * gaps * smooth(0.0, 0.3, patch))
    elif part == 2.0:
        w = np.maximum(1.0 * smooth(-0.45, -0.9, a['lz']) * smooth(-0.1, 0.25, patch), 0.7 * smooth(0.75, 0.97, a['lz']) * patch)
    elif part == 8.0:
        w = 0.8 * patch
    return np.clip(w * (0.55 + 0.45 * tuft), 0.0, 1.0)


def detail(pc: dict, quick: bool) -> None:
    """The relief ('disp', metres along the normal) and the paint attributes of one high piece."""
    P, a = pc['v'], pc['a']
    n = len(P)
    part = float(a['part'][0])
    zero = np.zeros(n)
    mortar, bedge, chip, pit, red, slit = zero.copy(), zero.copy(), zero.copy(), zero.copy(), zero.copy(), zero.copy()
    bid = a['bid'].copy() if 'bid' in a else np.full(n, 0.5)
    if part == 9.0:
        wall = float(a['which'][0]) == 0.0
        spec = K.WALL_BRICKS if wall else K.TOWER_BRICKS
        which = 'wall' if wall else 'tower'
        th, z, dp = a['th'], P[:, 2], a['dpart']
        br = K.bricks(th * spec['r_ref'], z, TAU * spec['r_ref'], spec)
        det = K.stone_detail(P, br['edge'] * (1 - br['mortar']), spec['seed'] + 50, 0.02, 0.0062, big_pits=0.9)
        h = br['h'] + det['h'] * (1.0 - br['mortar'])
        # the parapet's top and inner face: capstones about 6 cm long
        arc = th * K.wall_radius(which, z)
        seg = np.floor(arc / 0.065).astype(np.int64)
        cap = smooth(0.004, 0.0012, 0.0325 - np.abs(np.mod(arc, 0.065) - 0.0325))
        hc = -0.003 * cap + K.stone_detail(P, zero, spec['seed'] + 60, 0.02, 0.0)['h']
        top = dp > 0
        h = np.where(top, hc, h)
        mortar = np.where(top, cap, br['mortar'])
        bid = np.where(top, N.hash1(seg, spec['seed'] + 61), br['bid'])
        bedge = np.where(top, 0.0, br['edge'])
        chip = np.where(top, 0.0, det['chip'])
        pit = det['pit']
        red = np.where(top, 0.0, br['red'])
        for wh, thd, zc in K.WINDOWS:
            if wh != which:
                continue
            x = K.ang_wrap(th - math.radians(thd)) * K.wall_radius(which, z)
            m = K.slit_mask(x, z - zc, which) * (~top)
            slit = np.maximum(slit, m)
            h = h * (1 - m) - 0.017 * m
    elif part == 8.0:
        spec = K.FLOOR_BRICKS if float(a['which'][0]) == 0.0 else K.TFLOOR_BRICKS
        rr = np.maximum(a['rr'], 0.004)
        br = K.bricks(a['th'] * rr, rr, TAU * rr, spec)
        det = K.stone_detail(P, br['edge'] * (1 - br['mortar']), spec['seed'] + 50, 0.018, 0.003)
        h = br['h'] + det['h'] * (1 - br['mortar'])
        mortar, bid, bedge, chip, pit = br['mortar'], br['bid'], br['edge'], det['chip'], det['pit']
    elif part in (1.0, 2.0, 3.0):
        big = part != 3.0
        e = smooth(0.022, 0.003, a['edge']) if big else smooth(0.008, 0.0015, a['edge'])
        det = K.stone_detail(P, e, 300 + int(part), 0.026 if big else 0.012, 0.0072 if big else 0.003, big_pits=1.0 if big else 0.0)
        h = det['h']
        bedge, chip, pit = smooth(0.012, 0.0, a['edge']), det['chip'], det['pit']
    elif part in (4.0, 5.0, 6.0):
        ck = a['ck']
        u, w2 = a.get('u', zero), a.get('w2', zero)
        # wood grain runs along u (the door's planks run up: along w2)
        q = np.stack([u * 1.0, w2 * 0.12, zero], axis=1) if part == 4.0 else np.stack([u * 0.12, w2, zero], axis=1)
        h = 0.00045 * N.fbm(q, 1 / 0.004, 401, 3)
        if part == 4.0:
            groove = sum(np.exp(-((u - x0) / 0.0013) ** 2) for x0 in (-0.03, 0.0, 0.03)) * (ck == CK['wood'])
            h = h - 0.0026 * groove
            mortar = groove
        rope = a.get('rope', zero)
        if rope.any():
            ang = np.arctan2(P[:, 1], P[:, 0])
            h = np.where(rope > 0.5, 0.0005 * np.sin(ang * 9.0 + P[:, 2] * 900.0), h)
        iron = ck == CK['iron']
        h = np.where(iron, 0.0003 * N.fbm(P, 1 / 0.003, 409, 2), h)
        pit = np.where(iron, smooth(0.2, 0.6, N.fbm(P, 1 / 0.004, 410, 2)), 0.0)
    elif part == 7.0:
        u, v = a['u'], a['w2']
        hem = np.exp(-((np.minimum(1.0 - np.abs(v), 0.4) * K.FLAG['h0'] * 0.5 - 0.006) / 0.0011) ** 2)
        hem = np.maximum(hem, np.exp(-(((1.0 - u) * K.FLAG['len'] - 0.007) / 0.0011) ** 2) * smooth(0.2, 0.6, np.abs(v)))
        h = -0.0005 * hem + 0.00012 * N.fbm(P, 1 / 0.0016, 421, 1)
        mortar = hem
    else:
        h = zero
    moss = _moss(pc, mortar)
    # moss clumps: lumpy cushions (4 mm) with fine tufts
    h = h + smooth(0.25, 0.75, moss) * (0.0028 * smooth(-0.4, 0.5, N.fbm(P, 1 / 0.008, 503, 2)) + 0.0013 * smooth(-0.3, 0.6, N.fbm(P, 1 / 0.0025, 505, 1)))
    if part == 9.0 and float(a['which'][0]) == 0.0:
        pc['a']['base'] = smooth(0.1, 0.0, P[:, 2] - K.skirt_zt(a['th'])) * (a['dpart'] == 0)
    pc['a'].update({'disp': h, 'mortar': mortar, 'bedge': bedge, 'chip': chip, 'pit': pit, 'red': red, 'slit': slit,
                    'moss': moss, 'bid': bid})


LO_TK = {9.0: 1.0, 8.0: 0.35, 1.0: 0.95, 2.0: 0.85, 3.0: 1.25, 4.0: 1.4, 5.0: 0.6, 6.0: 0.75, 7.0: 1.1}
HI_ATTRS = ('ck', 'bid', 'mortar', 'bedge', 'chip', 'pit', 'red', 'slit', 'moss', 'u', 'w2', 'rope', 'part', 'base')


def build(high: bool, quick: bool):
    """[hi_keep] (displaced; painted from its attributes) or [lo_keep] (cpart, ck; texel_k per face)."""
    from lib import surface as S
    step = (0.006 if quick else 0.0028) if high else 0.035
    pcs = pieces(step, high)
    if high:
        for pc in pcs:
            detail(pc, quick)
        allp = G.merge(pcs)
        disp = allp['a']['disp']
        allp['a'] = {k: allp['a'][k] for k in HI_ATTRS if k in allp['a']}
        ob = G.make_object('hi_keep', allp)
        co, vn = S.mesh_arrays(ob)
        S.set_positions(ob, co + vn * disp[:, None])
        ob['prop'] = 'keep'
        return [ob]
    for pc in pcs:
        part = float(pc['a']['part'][0])
        tk = np.full(len(pc['v']), LO_TK.get(part, 1.0))
        if part == 9.0:
            tk = np.where(pc['a']['dpart'] > 0, 0.45, tk)
        if part == 1.0:
            tk = np.where(pc['a']['lz'] > 0.6, 1.0, 0.45)
        if 'cpart' not in pc['a']:
            pc['a']['cpart'] = np.zeros(len(pc['v']))
        pc['a']['tk'] = tk
    allp = G.merge(pcs)
    allp['a'] = {k: allp['a'][k] for k in ('cpart', 'tk', 'ck')}
    ob = G.make_object('lo_keep', allp)
    order = G.face_order(allp)
    G.set_face_attr(ob, 'texel_k', allp['a']['tk'][allp['f'][order]].mean(axis=1))
    ob['prop'] = 'keep'
    return [ob]
