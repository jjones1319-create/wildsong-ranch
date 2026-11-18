"""Gearhoot's high source carving (Art 2.1 Ultra; chatgpt/monsters/29-gearhoot, 1-hero and 4-details): every relief is
pushed along the normals of hi_body and baked into the normal map and the AO; the fields it leaves are the paint's.
  - the brass plates: shingles in staggered rows, each one's lower edge raised over the plate below (lib.ultra
    plate_field 'scale'); the body's rows run round it from the collar down (the light chest plates in front), the
    head's radiate from the facial disc toward the back;
  - a domed copper rivet on each plate, a row round the collar and along the brow mask's V;
  - the brow mask (a raised brass plate over the eyes, dipping to the beak between them), the gear emblems on the chest
    and the forehead, the eye sockets' rims, the mouth under the beak.
Each relief stays in the high source (plates 3 mm, rivets 2.5 mm): lo_body keeps the smooth shells.
"""
from __future__ import annotations

import math

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import gearhoot_form as F
from monsters.breeds import gearhoot_geo as G
from monsters.breeds import gearhoot_noise as N

smooth = N.smooth
PLATE_H = 0.011                            # 3.2 mm read as engraving; rounds 1-2: big plates whose lips cast shadows
RIVET_R, RIVET_H = 0.008, 0.0036
MASK_H = 0.006
# round 2: bigger and raised further (a faint blur at the game camera); the brow's inside the helm plate's V
EMBLEMS = {'chest': {'c': (0.0, -0.28, 0.468), 'r': 0.042, 'teeth': 10},
           'brow': {'c': (0.0, -0.236, float(F.HC[2]) + 0.1), 'r': 0.033, 'teeth': 8}}
_LAST: dict = {}


# ----------------------------------------------------------------------------- the plates' layout
def _cast(tree, origin, dirs) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    o = np.repeat(np.asarray(origin, np.float64)[None], len(dirs), axis=0) if np.ndim(origin) == 1 else np.asarray(origin)
    return G.ray(tree, o, dirs)


def _tangent_down(n: np.ndarray, down) -> np.ndarray:
    t = np.asarray(down, np.float64) - n * (n @ np.asarray(down, np.float64))[..., None] if np.ndim(down) == 1 else down - n * np.sum(down * n, axis=1, keepdims=True)
    ln = np.linalg.norm(t, axis=1, keepdims=True)
    return t / np.maximum(ln, 1e-9)


def body_layout() -> dict:
    """Rows from just under the collar to the bottom, each staggered half a plate, about 8.5 cm apart round the body."""
    tree = G.bvh(F.body_piece(False))
    cs, ns, rows = [], [], []
    zs = [0.49, 0.39, 0.29, 0.195]             # rounds 1-2: 4 rows of big plates (7 small ones read as a motif)
    for i, z in enumerate(zs):
        r = F.body_profile(z)
        circ = math.pi * (F.BODY_A + 0.5 * (F.BODY_BF + F.BODY_BB)) * r
        k = max(6, int(round(circ / 0.115)))
        ph = 2 * math.pi * (np.arange(k) + 0.5 * (i % 2)) / k
        d = np.stack([np.cos(ph), np.sin(ph), np.zeros(k)], axis=1)
        loc, nrm, ok = _cast(tree, np.array([0.0, F.BC[1], z]), d)
        cs.append(loc[ok])
        ns.append(nrm[ok])
        rows.append(np.full(int(ok.sum()), i))
    c, n = np.concatenate(cs), np.concatenate(ns)
    t = _tangent_down(n, np.tile([0.0, 0.0, -1.0], (len(n), 1)))
    k = len(c)
    return {'c': c, 'n': n, 't': t, 'a': np.full(k, 0.074), 'b': np.full(k, 0.07), 'h': np.full(k, PLATE_H),
            'harm': np.zeros((k, 3, 2)), 'row': np.concatenate(rows).astype(np.float64), 'part': np.zeros(k)}


def _head_dir(psi, om):
    return np.stack([np.sin(psi) * np.cos(om), -np.cos(psi) * np.ones_like(om), np.sin(psi) * np.sin(om)], axis=-1)


def head_layout() -> dict:
    """Rings of plates round the facial disc's axis (-Y from the head's centre), each pointing away from the face: the
    cheeks' plates radiate from the disc, the top and the back fall in rows toward the back."""
    tree = G.bvh(F.head_piece(False))
    cs, ns, ts, rows = [], [], [], []
    psis = np.radians([62, 79, 96, 113, 130, 147])
    for i, psi in enumerate(psis):
        circ = 2 * math.pi * 0.205 * math.sin(psi)
        k = max(4, int(round(circ / 0.075)))
        om = 2 * math.pi * (np.arange(k) + 0.5 * (i % 2)) / k + 0.3
        d = _head_dir(np.full(k, psi), om)
        loc, nrm, ok = _cast(tree, F.HC, d)
        # the flow: the direction of growing psi (away from the face), on the surface
        d2 = _head_dir(np.full(k, psi + 0.05), om)
        t = _tangent_down(nrm, d2 - d)
        cs.append(loc[ok])
        ns.append(nrm[ok])
        ts.append(t[ok])
        rows.append(np.full(int(ok.sum()), i))
    # round 1: one round plate caps the back of the head (the rows pinched into a star at the pole)
    loc, nrm, ok = _cast(tree, F.HC, np.array([[0.0, 1.0, 0.0]]))
    cs.append(loc[ok])
    ns.append(nrm[ok])
    ts.append(_tangent_down(nrm[ok], np.array([[0.0, 0.0, -1.0]])))
    rows.append(np.full(int(ok.sum()), len(psis)))
    c, n, t = np.concatenate(cs), np.concatenate(ns), np.concatenate(ts)
    k = len(c)
    a = np.full(k, 0.048)
    a[-int(ok.sum()):] = 0.07
    return {'c': c, 'n': n, 't': t, 'a': a, 'b': a * 0.96, 'h': np.full(k, PLATE_H * 0.6),
            'harm': np.zeros((k, 3, 2)), 'row': np.concatenate(rows).astype(np.float64), 'part': np.ones(k)}  # noqa


def layout() -> dict:
    b, h = body_layout(), head_layout()
    return {k: np.concatenate([b[k], h[k]]) for k in b}


# ----------------------------------------------------------------------------- the face's fields
def head_angle(co: np.ndarray) -> np.ndarray:
    """Each point's angle (radians) from the facial disc's axis (-Y through the head's centre)."""
    d = co - F.HC[None]
    return np.arccos(np.clip(-d[:, 1] / np.maximum(np.linalg.norm(d, axis=1), 1e-9), -1, 1))


def mask_low(x: np.ndarray) -> np.ndarray:
    """The brow mask's lower edge: a V dipping to the beak between the eyes, along the eyes' tops, down at the sides."""
    ax = np.abs(x)
    # round 2: the edge hugs each eye's top like a brow and dips to a point between the eyes just above the beak
    ez = F.EYE[1]['z']
    R, ex = 0.072, F.EYE[1]['x']

    def arc(x):
        return ez + np.sqrt(np.clip(R * R - (x - ex) ** 2, 0.0, None))
    a0, a1 = arc(0.042), arc(0.168)
    return np.where(ax < 0.042, ez + 0.016 + (a0 - ez - 0.016) * (ax / 0.042),
                    np.where(ax <= 0.168, arc(ax), a1 - 0.35 * (ax - 0.168)))


def mask_field(co: np.ndarray, head: np.ndarray) -> np.ndarray:
    """0..1: the brow mask, a raised plate over the face's top (its rim softened over 5 mm)."""
    psi = head_angle(co)
    lo = mask_low(co[:, 0])
    m = smooth(lo - 0.0025, lo + 0.0025, co[:, 2]) * smooth(math.radians(72), math.radians(67), psi)     # round 2: over the forehead
    return m * head * (co[:, 1] < F.HC[1])


def face_field(co: np.ndarray, head: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """0..1: the light-brass facial disc (the flat face and the cheeks round the eyes), under the mask."""
    psi = head_angle(co)
    return smooth(math.radians(65), math.radians(53), psi) * head * (1.0 - mask)      # round 1: a soft seam


def emblem(co: np.ndarray, vn: np.ndarray, spec: dict) -> np.ndarray:
    """0..1: a gear emblem (a toothed ring, a hub, five spokes) raised on the surface near spec['c']."""
    c = np.asarray(spec['c'], np.float64)
    R = spec['r']
    d = co - c[None]
    near = np.linalg.norm(d, axis=1) < 1.6 * R
    out = np.zeros(len(co))
    if not near.any():
        return out
    nrm = np.mean(vn[near], axis=0)
    nrm = nrm / np.linalg.norm(nrm)
    e1 = np.array([1.0, 0.0, 0.0]) - nrm * nrm[0]
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nrm, e1)
    dd = d[near]
    x, y = dd @ e1, dd @ e2
    r = np.hypot(x, y)
    th = np.arctan2(y, x)
    T = spec['teeth']
    ph = np.mod(th * T / (2 * math.pi), 1.0)
    tooth = smooth(0.42, 0.36, np.abs(ph - 0.5))
    rt = R * (0.86 + 0.16 * tooth)
    ring = smooth(rt + 0.0008, rt - 0.0008, r) * smooth(0.5 * R - 0.0008, 0.5 * R + 0.0008, r)
    hub = smooth(0.24 * R + 0.0008, 0.24 * R - 0.0008, r)
    phs = np.mod(th, 2 * math.pi / 5) - math.pi / 5
    spokes = smooth(0.075 * R, 0.05 * R, r * np.abs(np.sin(phs))) * (r < 0.55 * R)
    out[near] = np.clip(np.maximum(np.maximum(ring, hub), spokes), 0, 1)
    return out


# ----------------------------------------------------------------------------- rivets
def rivet_points(pl: dict, mask_c: np.ndarray | None = None) -> np.ndarray:
    """A copper rivet at each plate's tip (its lower, exposed edge)."""
    return pl['c'] + pl['t'] * (0.6 * pl['a'])[:, None]


def collar_rivets() -> np.ndarray:
    k = 30
    a = 2 * math.pi * (np.arange(k) + 0.5) / k
    cx = F.COLLAR['a'] * np.cos(a)
    cy = F.BC[1] + np.where(np.sin(a) < 0, F.COLLAR['b'], F.COLLAR['bb']) * np.sin(a)
    rad = np.stack([np.cos(a), np.sin(a), np.zeros(k)], axis=1)
    up = np.array([0.0, 0.0, 1.0])
    out = np.stack([cx, cy, np.full(k, F.COLLAR['z'])], axis=1) + rad * (F.COLLAR['tr'] * 0.62) + up * (F.COLLAR['tz'] * 0.72)
    return out


def mask_rivets() -> np.ndarray:
    xs = np.array([-0.2, -0.165, -0.13, -0.095, -0.06, -0.03, 0.03, 0.06, 0.095, 0.13, 0.165, 0.2])
    zs = mask_low(xs) + 0.022
    out = []
    tree = G.bvh(F.head_piece(False))
    for x, z in zip(xs, zs):
        loc, _n, ok = G.ray(tree, np.array([[x, -0.5, z]]), np.array([[0.0, 1.0, 0.0]]))
        if ok[0]:
            out.append(loc[0])
    return np.array(out)


def nearest_within(co: np.ndarray, pts: np.ndarray, r: float) -> tuple[np.ndarray, np.ndarray]:
    """Each point's distance to the nearest of `pts` within r (inf beyond) and its index (-1 beyond)."""
    dist = np.full(len(co), np.inf)
    idx = np.full(len(co), -1, np.int64)
    cell = r
    key = np.floor(co / cell).astype(np.int64) + (1 << 20)
    kk = (key[:, 0] * (1 << 21) + key[:, 1]) * (1 << 21) + key[:, 2]
    order = np.argsort(kk, kind='stable')
    sk = kk[order]
    offs = np.array([(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)], np.int64)
    for i, p in enumerate(pts):
        ck = np.floor(p / cell).astype(np.int64) + (1 << 20) + offs
        keys = (ck[:, 0] * (1 << 21) + ck[:, 1]) * (1 << 21) + ck[:, 2]
        lo = np.searchsorted(sk, keys, 'left')
        hi = np.searchsorted(sk, keys, 'right')
        parts = [order[a:b] for a, b in zip(lo, hi) if b > a]
        if not parts:
            continue
        ii = np.concatenate(parts)
        d = np.linalg.norm(co[ii] - p[None], axis=1)
        w = (d < r) & (d < dist[ii])
        dist[ii[w]] = d[w]
        idx[ii[w]] = i
    return dist, idx


# ----------------------------------------------------------------------------- the carving
def fields(co: np.ndarray, vn: np.ndarray, head: np.ndarray | None = None) -> dict:
    head = (F.head_mask(co) if head is None else head).astype(np.float64)
    rc = np.hypot(co[:, 0], (co[:, 1] - F.BC[1]))
    collar = ((head < 0.5) & (co[:, 2] > F.COLLAR['z'] - F.COLLAR['tz'] * 1.2) & (rc > F.COLLAR['a'] - F.COLLAR['tr'] * 1.3)).astype(np.float64)
    mask = mask_field(co, head)
    face = face_field(co, head, mask)
    pl = layout()
    f = U.plate_field(co, vn, pl, 'scale')
    pid = f['pid']
    gone = plates_off(pl)
    # no plates on the face, under the mask or on the collar: whole plates
    off = np.clip(face + mask + collar, 0, 1)
    off = np.where(pid >= 0, np.maximum(gone[np.maximum(pid, 0)], collar), off)
    on = (pid >= 0) & (off < 0.99)
    k = np.where(on, pid, 0)
    d = co - pl['c'][k]
    bt = np.cross(pl['n'][k], pl['t'][k])
    pls = np.where(on, np.einsum('ij,ij->i', d, pl['t'][k]) / pl['a'][k], 0.0)
    plq = np.where(on, np.einsum('ij,ij->i', d, bt) / pl['b'][k], 0.0)
    keep = (1.0 - off) * np.where(head > 0.5, 1.0, smooth(F.COLLAR['z'] - F.COLLAR['tz'] - 0.004, F.COLLAR['z'] - F.COLLAR['tz'] - 0.03, co[:, 2]))
    plate_h = f['h'] * keep
    # rivets: one a plate (on the plates that show), the collar's ring and the mask's V
    rp = rivet_points(pl)
    rk = np.ones(len(rp), bool)
    rp = np.concatenate([rp[rk], collar_rivets(), mask_rivets()])
    rdist, ridx = nearest_within(co, rp, RIVET_R * 1.6)
    on_plate_riv = ridx < int(rk.sum())
    riv_ok = np.where(on_plate_riv, keep, 1.0)
    riv = np.where(np.isfinite(rdist), smooth(RIVET_R, RIVET_R * 0.85, rdist), 0.0) * riv_ok
    riv_h = RIVET_H * np.sqrt(np.clip(1.0 - (np.where(np.isfinite(rdist), rdist, 1.0) / RIVET_R) ** 2, 0, 1)) * riv_ok
    ring = np.where(np.isfinite(rdist), smooth(RIVET_R * 1.55, RIVET_R * 1.1, rdist) * smooth(RIVET_R * 0.95, RIVET_R * 1.1, rdist), 0.0) * riv_ok
    emb = np.maximum(emblem(co, vn, EMBLEMS['chest']), emblem(co, vn, EMBLEMS['brow']))
    # the eye sockets: a soft brass rim round each lens (the monocle's ring covers its own), the floor under the lens
    eyes = {}
    for s in (1, -1):
        c, xax, yax, look = F.eye_frame(s)
        dd = co - c[None]
        r = np.hypot(dd @ xax, dd @ yax) / F.EYE[s]['r']
        r = np.where(np.abs(dd @ look) < 0.03, r, 9.0)          # only on the face, not through the head
        eyes[s] = (r, dd @ yax / F.EYE[s]['r'])
    return {'head': head, 'collar': collar, 'mask': mask, 'face': face, 'pl': pl, 'f': f, 'on': on.astype(np.float64),
            'pid': np.where(on, pid, -1).astype(np.float64), 'pls': pls, 'plq': plq, 'plate_h': plate_h, 'keep': keep,
            'riv': riv, 'riv_h': riv_h, 'rring': ring, 'emb': emb, 'eyes': eyes}


def plates_off(pl: dict) -> np.ndarray:
    """1 for each plate whose centre lies on the facial disc or the helm plate (it goes whole), else 0."""
    c, n = pl['c'], pl['n']
    head = pl['part'] > 0.5
    psi = head_angle(c)
    on_face = head & (psi < math.radians(60))
    on_mask = head & (c[:, 2] > mask_low(c[:, 0]) - 0.01) & (psi < math.radians(74)) & (c[:, 1] < F.HC[1])
    return (on_face | on_mask).astype(np.float64)


def chest_of(co: np.ndarray, W: dict) -> np.ndarray:
    """1 on the light chest plates (whole plates: those centred in front, between the wings), else 0; between plates
    by position."""
    pl = W['pl']
    c = pl['c']
    # round 1: whole plates by their centre's angle from the front (the boundary follows the plates' edges)
    ang = np.degrees(np.arctan2(np.abs(c[:, 0]), -(c[:, 1] - F.BC[1])))
    ch = (pl['part'] == 0) & (ang < 38.0) & (c[:, 2] > 0.17) & (c[:, 2] < 0.45)
    pid = W['pid'].astype(int)
    # between plates: the nearest plate's (round 2: a positional fallback made the chest's edge ragged)
    near = np.full(len(co), -1, np.int64)
    miss = pid < 0
    if miss.any():
        d, j = nearest_within(co[miss], c, 0.12)
        near[miss] = j
    k = np.where(pid >= 0, pid, near)
    return np.where(k >= 0, ch[np.maximum(k, 0)].astype(np.float64), 0.0)


def carve_low(lo_body) -> None:
    """Round 1: the plates raised on the game mesh too (70%), so the silhouette is plated, not a glazed egg."""
    co, vn = S.mesh_arrays(lo_body)
    head = F.shells_of(lo_body).astype(np.float64)
    rc = np.hypot(co[:, 0], co[:, 1] - F.HC[1])
    collar = ((head < 0.5) & (co[:, 2] > F.COLLAR['z'] - F.COLLAR['tz'] * 1.5) & (rc > F.COLLAR['a'] - F.COLLAR['tr'] * 1.5)).astype(np.float64)
    mask = mask_field(co, head)
    face = face_field(co, head, mask)
    pl = layout()
    f = U.plate_field(co, vn, pl, 'scale', scale=1.0)       # round 2: full height (0.7 did not read at the game camera)
    gone = plates_off(pl)
    keep = np.where(f['pid'] >= 0, 1.0 - np.maximum(gone[np.maximum(f['pid'], 0)], collar), 0.0)
    keep = keep * np.where(head > 0.5, 1.0, smooth(F.COLLAR['z'] - F.COLLAR['tz'] - 0.004, F.COLLAR['z'] - F.COLLAR['tz'] - 0.03, co[:, 2]))
    S.set_positions(lo_body, co + vn * (f['h'] * keep)[:, None])
    C.log(f'gearhoot carve_low: plates raised on lo_body, up to {float((f["h"] * keep).max()) * 1000:.1f} mm')


def carve(hi_body) -> None:
    co, vn = S.mesh_arrays(hi_body)
    W = fields(co, vn, F.shells_of(hi_body))
    d = W['plate_h'].copy()
    d += MASK_H * W['mask']
    d += 0.0045 * W['emb'] * (1.0 - W['riv'])
    d += W['riv_h']
    d -= 0.0006 * W['rring']
    # the eye sockets: a raised rim (4 mm wide, 2.5 mm high) round the normal eye, a slight dip under each lens
    r_n, _y = W['eyes'][-1]
    d += 0.0045 * smooth(0.96, 1.04, r_n) * smooth(1.26, 1.14, r_n) * W['head']      # round 2: a deeper socket rim
    for s in (1, -1):
        r_e, _y = W['eyes'][s]
        d -= 0.002 * smooth(1.0, 0.85, r_e) * W['head']
    # the mouth: a small dark slot under the beak
    zc = F.HC[2]
    m = W['head'] * smooth(0.014, 0.009, np.abs(co[:, 0])) * smooth(zc - 0.048, zc - 0.044, co[:, 2]) * smooth(zc - 0.03, zc - 0.034, co[:, 2]) * (co[:, 1] < F.Y_FACE + 0.02)
    # the brow mask's raised edge: a ridge along its V (round 1: paint alone read flat)
    dzm = co[:, 2] - mask_low(co[:, 0])
    ridge = smooth(-0.001, 0.003, dzm) * smooth(0.013, 0.008, dzm) * W['head'] * (co[:, 1] < F.HC[1] - 0.12) * (head_angle(co) < math.radians(70))
    d += 0.004 * ridge
    S.set_positions(hi_body, co + vn * d[:, None])
    hi_body.data.shade_smooth()
    S.base_attrs(hi_body, co)
    rn, yn = W['eyes'][-1]
    rm, ym = W['eyes'][1]
    attrs = {'region': W['head'] + 2.0 * W['collar'], 'mask': W['mask'], 'face': W['face'], 'plate': W['f']['mask'] * W['keep'] * W['on'],
             'prim': W['f']['rim'], 'ptop': W['f']['top'], 'pid': W['pid'], 'pls': W['pls'], 'plq': W['plq'], 'riv': W['riv'],
             'rring': W['rring'], 'emb': W['emb'], 'eyer_n': rn, 'eyey_n': yn, 'eyer_m': rm, 'eyey_m': ym, 'mouth': m,
             'prow': np.where(W['pid'] >= 0, W['pl']['row'][np.maximum(W['pid'].astype(int), 0)], -1.0),
             'ppart': np.where(W['pid'] >= 0, W['pl']['part'][np.maximum(W['pid'].astype(int), 0)], -1.0),
             'pchest': chest_of(co, W),
             # the seat inside the collar and the head's underside: in shadow, painted dark (a neck joint, not a hole)
             'seat': ((W['head'] < 0.5) & (np.hypot(co[:, 0], co[:, 1] - F.HC[1]) < F.COLLAR['a'] - 0.004) & (co[:, 2] > 0.53)).astype(np.float64),
             'under': W['head'] * smooth(F.HC[2] - 0.1, F.HC[2] - 0.13, co[:, 2]), 'mridge': ridge}
    for k, a in attrs.items():
        S.add_attr(hi_body, k, np.asarray(a, np.float64))
    _LAST.clear()
    _LAST.update(attrs)
    _LAST['n'] = len(co)
    _LAST['co'] = co
    _LAST['vn'] = vn
    C.log(f'gearhoot carve: {len(W["pl"]["c"])} plates, {int((W["riv"] > 0.5).sum())} rivet vertices, '
          f'mask {int((W["mask"] > 0.5).sum())}, face {int((W["face"] > 0.5).sum())} of {len(co)} vertices')
