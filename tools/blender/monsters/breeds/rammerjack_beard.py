"""Rammerjack's beard (v1.25): seven separate tapered wavy locks from the cheeks and chin (1-hero, 3-faces neutral).

Round 3's mane of 36 clumps and v1.24's webbed clumps read as one shield-shaped shell (review, Nov 12). Now:
  - seven locks root along the jaw from below the ears (the mutton chops) to under the chin; the middle one is the
    longest (mid-chest), the side ones shorter over the scarf; their tips spread apart so the scarf shows between;
  - six thinner, shorter locks behind them fill the gaps near the chin (a full mane there), webs only at the roots;
  - every lock is pushed clear of the scarf's band (the scarf wraps under the beard);
  - three spring chains: `beard` (the middle), `beardL` / `beardR` (the chops), each from the head.
The locks are closed meshes voxel-united into the body (`body_extras`); `lookup()` gives any point's lock, how far
along it lies (u), how much is left to its tip, where across it lies and its comb direction, for the zones, the flow,
the paint, the cards and the weights.
"""
from __future__ import annotations

import bpy
import numpy as np
from mathutils.kdtree import KDTree

from lib.surface import smooth, v3
from monsters.breeds import rammerjack_props as RP

CHAINS = {
    'beard': [(0.0, -0.64, 0.835), (0.0, -0.7, 0.7), (0.0, -0.705, 0.58), (0.0, -0.69, 0.455)],
    'beardL': [(0.125, -0.55, 0.875), (0.118, -0.64, 0.77), (0.085, -0.69, 0.655)],
    'beardR': [(-0.125, -0.55, 0.875), (-0.118, -0.64, 0.77), (-0.085, -0.69, 0.655)],
}
NU, SIDES = 30, 10

_CLUMPS: list = []
_KD: dict = {}


def root_on_jaw(th: float) -> np.ndarray:
    """θ −1 (below the right ear) … 0 (under the chin) … 1 (below the left ear)."""
    a = abs(th)
    return v3((0.162 * th, -0.627 + 0.18 * a ** 1.35, 0.834 + 0.1 * a ** 1.6))


def beard_width(z: float) -> float:
    """The beard's half width in the front view at height z (2-turnaround front, 1-hero): ±0.14 m over the scarf,
    narrowing to a soft point at 0.46 m."""
    return 0.145 * max(0.0, min(1.0, (z - 0.455) / 0.31)) ** 0.8


def tip_of(th: float, layer: int) -> np.ndarray:
    if layer == 2:
        # v1.25 final: the short front locks layered over the top of the beard, from the cheeks and chin
        r = root_on_jaw(th)
        return v3((r[0] * 1.08 + 0.012 * np.sign(th), r[1] - 0.035, r[2] - 0.15 - 0.02 * (1 - abs(th))))
    """v1.25: each lock's tip. The middle lock is the longest (mid-chest), the side locks shorter over the scarf; the
    tips spread apart so the scarf shows between them. Layer 1 (the in-between locks) sits behind and ends higher."""
    a = abs(th)
    back = layer == 1
    z = 0.47 + 0.26 * a ** 1.15 + (0.075 if back else 0.0)
    x = np.sign(th) * 0.13 * a ** 0.85 * (0.92 if back else 1.0)
    return v3((x, -0.69 + 0.07 * a + (0.018 if back else 0.0), z))


PRIMARY = 7            # v1.25: the beard's separate locks from the cheeks and chin (review: 6–8 locks, not a shell)


def _clump_specs() -> list[dict]:
    """v1.25 (review, Nov 12: one shield-shaped shell with a torn-paper edge): 7 separate tapered wavy locks from the
    cheeks and chin, and 6 thinner, shorter ones behind them in the gaps (a full mane at the top, separate tips below)."""
    rng = np.random.default_rng(41)
    specs = []
    for th in np.linspace(-1.0, 1.0, PRIMARY):
        specs.append({'th': float(th), 'layer': 0, 'r0': 0.029 - 0.006 * abs(th), 'rng': rng.uniform(0, 6.3, 4)})
    mids = np.linspace(-1.0, 1.0, PRIMARY)
    for th in 0.5 * (mids[:-1] + mids[1:]):
        specs.append({'th': float(th), 'layer': 1, 'r0': 0.021, 'rng': rng.uniform(0, 6.3, 4)})
    # v1.25 final (review: the upper two thirds still one shell): short wavy locks layered over the top, overlapping
    for th in np.linspace(-0.92, 0.92, 6):
        specs.append({'th': float(th), 'layer': 2, 'r0': 0.017, 'rng': rng.uniform(0, 6.3, 4)})
    return specs


def clump_path(sp: dict, scarf_outer) -> tuple[np.ndarray, np.ndarray]:
    """Centre line (NU × 3) and radius (NU) of one lock; `scarf_outer(p)` → (inside the band's shell, the push out)."""
    th, layer, ph = sp['th'], sp['layer'], sp['rng']
    root = root_on_jaw(th) + v3((0.0, 0.006, 0.004)) + v3((0.0, {1: 0.014, 2: -0.012}.get(layer, 0.0), -0.008 * (layer == 2)))
    tip = tip_of(th, layer)
    u = np.linspace(0.0, 1.0, NU)
    P = root[None, :] + (tip - root)[None, :] * u[:, None]
    # it hangs: bulges forward over the scarf in its middle, an S-wave sideways and in depth, the tip curling out
    fwd = -0.012 * np.sin(np.pi * np.clip(u * 1.1, 0, 1)) ** 1.5 * (1.0 - 0.5 * abs(th))
    wave = 0.014 * np.sin(2 * np.pi * u * (1.1 + 0.2 * np.sin(ph[0])) + ph[1]) * smooth(0.1, 0.4, u)
    curl = smooth(0.78, 1.0, u) ** 2
    side = np.sign(th) if abs(th) > 0.05 else np.sign(np.sin(ph[2]))
    P[:, 0] += wave + 0.007 * side * curl
    P[:, 1] += fwd - 0.006 * curl
    P[:, 2] += 0.004 * np.sin(2 * np.pi * u * 0.8 + ph[3])
    P[:, 1] += 0.008 * np.sin(2 * np.pi * u * 0.9 + ph[0]) * smooth(0.1, 0.4, u)
    r = sp['r0'] * (1.0 - 0.9 * u ** 1.2) + 0.0018              # a long taper to a point
    # the chops' roots thin out into the cheek (round 2: a round chestnut ball on the cheek)
    root_k = 0.45 + 0.55 * smooth(0.0, 0.22, u) if abs(th) > 0.7 else 0.75 + 0.25 * smooth(0.0, 0.1, u)
    r = r * root_k
    # the scarf wraps under the beard: push any point of the lock out of the band's shell
    if scarf_outer is not None:
        push = np.minimum(scarf_outer(P, r), 0.035)
        k = np.convolve(np.pad(push, 2, mode='edge'), np.ones(5) / 5.0, mode='valid')
        P = P + k[:, None] * v3((0.0, -1.0, 0.0)) * 1.0
    return P, r


def build_clumps(scarf_outer) -> list[dict]:
    if not _CLUMPS:
        for sp in _clump_specs():
            P, r = clump_path(sp, scarf_outer)
            T = np.gradient(P, axis=0)
            T /= np.linalg.norm(T, axis=1, keepdims=True)
            _CLUMPS.append({**sp, 'P': P, 'r': r, 'T': T})
    return _CLUMPS


def clump_meshes(scarf_outer) -> list[bpy.types.Object]:
    """Closed meshes for the voxel body (new objects on every call)."""
    out = []
    ph = np.linspace(0, 2 * np.pi, SIDES, endpoint=False)
    for i, c in enumerate(build_clumps(scarf_outer)):
        cv = RP.Curve(c['P'])
        _p, T, N, B = cv.at(cv.s)
        # flattened: wider across the beard than deep
        across = np.cross(T, v3((0.0, -1.0, 0.0)))
        across /= np.maximum(np.linalg.norm(across, axis=1, keepdims=True), 1e-9)
        depth = np.cross(across, T)
        rr = c['r']
        ring = (np.cos(ph)[None, :, None] * across[:, None, :] * 1.25 + np.sin(ph)[None, :, None] * depth[:, None, :] * 0.95)
        pts = c['P'][:, None, :] + ring * rr[:, None, None]
        out.append(RP.grid_object(f'beardclump{i}', pts, True, caps=(True, True)))
    # v1.25 final: no webs (the layered front locks fill the top; the webs made it one shell)
    return out


WEB_DEPTH = 0.5        # the web's half depth, a share of its locks' radius
WEB_END = (0.2, 0.38)  # v1.25: webs only near the roots (one mane under the chin); below, the locks part


def web_meshes(scarf_outer) -> list[bpy.types.Object]:
    """3b: a flat web between each pair of neighbouring clumps of a layer, half as deep as the clumps: the grooves
    between them stay shallow and open (round 3: deep narrow slots between the clumps baked black, dark specks)."""
    out = []
    ph = np.linspace(0, 2 * np.pi, SIDES, endpoint=False)
    cl = build_clumps(scarf_outer)
    u = np.linspace(0.0, 1.0, NU)
    keep = u <= WEB_END[1]
    taper = 0.25 + 0.75 * smooth(WEB_END[1], WEB_END[0], u[keep])
    for layer in (0,):
        row = sorted((c for c in cl if c['layer'] == layer), key=lambda c: c['th'])
        for i in range(len(row) - 1):
            A, B = row[i], row[i + 1]
            PA, PB = A['P'][keep], B['P'][keep]
            C = 0.5 * (PA + PB)
            half = 0.5 * np.linalg.norm(PB - PA, axis=1)
            across = (PB - PA) / np.maximum(2 * half[:, None], 1e-9)
            T = np.gradient(C, axis=0)
            T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
            depth = np.cross(across, T)
            depth /= np.maximum(np.linalg.norm(depth, axis=1, keepdims=True), 1e-9)
            rd = WEB_DEPTH * 0.5 * (A['r'][keep] + B['r'][keep]) * taper
            ra = half * (0.5 + 0.5 * taper) + 0.002
            ring = np.cos(ph)[None, :, None] * across[:, None, :] * ra[:, None, None] + np.sin(ph)[None, :, None] * depth[:, None, :] * rd[:, None, None]
            out.append(RP.grid_object(f'beardweb{layer}_{i}', C[:, None, :] + ring, True, caps=(True, True)))
    return out


def _kd():
    if 'kd' not in _KD:
        cl = _CLUMPS
        pts = np.concatenate([c['P'] for c in cl])
        _KD['pts'] = pts
        _KD['u'] = np.concatenate([np.linspace(0, 1, NU) for _ in cl])
        _KD['r'] = np.concatenate([c['r'] for c in cl])
        _KD['T'] = np.concatenate([c['T'] for c in cl])
        _KD['th'] = np.concatenate([np.full(NU, c['th']) for c in cl])
        _KD['cid'] = np.concatenate([np.full(NU, i) for i, _c in enumerate(cl)])
        seg = [np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(c['P'], axis=0), axis=1))]) for c in cl]
        _KD['rem'] = np.concatenate([sg[-1] - sg for sg in seg])
        kd = KDTree(len(pts))
        for i, p in enumerate(pts):
            kd.insert(p, i)
        kd.balance()
        _KD['kd'] = kd
    return _KD


def lookup(p: np.ndarray, pad: float = 0.022) -> dict:
    """Per point: on a clump (within its radius + pad), u along it, its θ (the chain blend) and its comb direction."""
    k = len(p)
    out = {'on': np.zeros(k, bool), 'u': np.zeros(k), 'th': np.zeros(k), 'dir': np.tile(v3((0.0, 0.0, -1.0)), (k, 1)),
           'crown': np.zeros(k), 'cid': np.full(k, -1), 'lat': np.zeros(k), 'rem': np.zeros(k)}
    if not _CLUMPS:
        return out
    box = (np.abs(p[:, 0]) < 0.24) & (p[:, 1] < -0.4) & (p[:, 2] > 0.36) & (p[:, 2] < 0.98)
    idx = np.nonzero(box)[0]
    if len(idx) == 0:
        return out
    D = _kd()
    kd = D['kd']
    j = np.empty(len(idx), np.int64)
    d = np.empty(len(idx))
    for n_, i in enumerate(idx):
        _co, jj, dd = kd.find(p[i])
        j[n_] = jj
        d[n_] = dd
    on = d < D['r'][j] + pad
    sel = idx[on]
    out['on'][sel] = True
    out['u'][sel] = D['u'][j[on]]
    out['th'][sel] = D['th'][j[on]]
    out['dir'][sel] = D['T'][j[on]]
    # how far round its clump toward the beard's front a point lies (1 on the clump's crown, ~0.5 in the groove to the
    # next clump, below 0 behind it): the paint lights each lock's crown and darkens the grooves between them (v1.23:
    # the beard read as one mass from the front)
    js = j[on]
    off = p[sel] - D['pts'][js]
    T = D['T'][js]
    off = off - T * (off * T).sum(1, keepdims=True)
    off /= np.maximum(np.linalg.norm(off, axis=1, keepdims=True), 1e-9)
    th = D['th'][js]
    o = np.stack([0.9 * th, -np.ones(len(js)), np.zeros(len(js))], 1)
    o /= np.linalg.norm(o, axis=1, keepdims=True)
    out['crown'][sel] = (off * o).sum(1)
    out['cid'][sel] = D['cid'][js]
    out['rem'][sel] = D['rem'][js]
    # and where across its clump it lies (−1 … 1 edge to edge, as clump_meshes flattens it): from the front each clump
    # is a wide band over its neighbours, so its edges, not its crown, are where one lock meets the next
    across = np.cross(T, np.array([0.0, -1.0, 0.0]))
    across /= np.maximum(np.linalg.norm(across, axis=1, keepdims=True), 1e-9)
    out['lat'][sel] = np.clip((off * across).sum(1), -1.0, 1.0)
    return out


def chain_blend(th: np.ndarray) -> dict[str, np.ndarray]:
    """How much of each chain a point of clump θ follows."""
    side = smooth(0.25, 0.62, np.abs(th))
    return {'beard': 1.0 - side, 'beardL': side * (th > 0), 'beardR': side * (th <= 0)}
