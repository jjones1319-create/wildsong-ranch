"""Rammerjack's beard (round 2): a wide mane of wavy chestnut strand clumps (1-hero, 3-faces neutral, 4-details 1).

Round 1's beard was one smooth teardrop and two cheek balls: a brown paddle at 64 px that flipped like a jaw. Now:
  - clumps root along the jaw from below the ears (the mutton chops, framing a cream muzzle and chin) to under the
    chin, and pour down over the scarf to mid-chest, converging on a soft ragged point;
  - two layers (front and back) plus a few thin stray clumps, each a wavy flattened tube tapering to its own tip;
  - every clump is pushed clear of the scarf's band (the scarf wraps under the beard);
  - three spring chains: `beard` (the middle), `beardL` / `beardR` (the chops), each from the head.
The clumps are closed meshes voxel-united into the body (`body_extras`); `lookup()` gives any point's clump, how far
along it lies (u) and its comb direction, for the zones, the flow, the paint and the weights.
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
    a = abs(th)
    z = 0.455 + 0.33 * a ** 1.25 + {0: 0.0, 1: 0.045, 3: 0.09}.get(layer, 0.0)
    return v3((np.sign(th) * 0.92 * beard_width(z), -0.688 + 0.06 * a + {0: 0.0, 1: 0.016, 3: 0.034}.get(layer, 0.0), z))


def _clump_specs() -> list[dict]:
    rng = np.random.default_rng(41)
    specs = []
    for th in np.linspace(-1.0, 1.0, 13):
        specs.append({'th': float(th), 'layer': 0, 'r0': 0.031 - 0.009 * abs(th), 'rng': rng.uniform(0, 6.3, 4)})
    for th in np.linspace(-0.92, 0.92, 12):
        specs.append({'th': float(th), 'layer': 1, 'r0': 0.029 - 0.006 * abs(th), 'rng': rng.uniform(0, 6.3, 4)})
    # round 3: a back layer, so the mane stays as deep as the scarf in profile (round 2: a narrow rope off the chin);
    # round 2's thin strays are gone (one stuck out of the lower edge as a dark spike)
    for th in np.linspace(-0.82, 0.82, 11):
        specs.append({'th': float(th), 'layer': 3, 'r0': 0.028 - 0.006 * abs(th), 'rng': rng.uniform(0, 6.3, 4)})
    return specs


def clump_path(sp: dict, scarf_outer) -> tuple[np.ndarray, np.ndarray]:
    """Centre line (NU × 3) and radius (NU) of one clump; `scarf_outer(p)` → (inside the band's shell, the push out)."""
    th, layer, ph = sp['th'], sp['layer'], sp['rng']
    root = root_on_jaw(th) + v3((0.0, 0.006, 0.004)) + v3((0.0, {0: 0.0, 1: 0.012, 3: 0.024}.get(layer, 0.0), 0.0))
    tip = tip_of(th, layer)
    if layer == 2:
        tip = tip + v3((0.0, -0.012, -0.03 - 0.02 * (1 - abs(th) / 0.35)))
    u = np.linspace(0.0, 1.0, NU)
    P = root[None, :] + (tip - root)[None, :] * u[:, None]
    # it hangs: bulges forward over the scarf in its middle, waves sideways, its tip curls a little out and forward
    fwd = -0.012 * np.sin(np.pi * np.clip(u * 1.1, 0, 1)) ** 1.5 * (1.0 - 0.5 * abs(th))
    # 3b: the wave and the tips' curl calm toward the point, where the clumps crowd together (round 3: crossing tips
    # left narrow slots that baked black, the dark specks in the lower beard)
    wave = (0.011 + 0.004 * (layer == 2)) * np.sin(2 * np.pi * u * (1.2 + 0.3 * np.sin(ph[0])) + ph[1]) * smooth(0.08, 0.35, u)
    wave = wave * (1.0 - 0.55 * smooth(0.55, 0.95, u))
    curl = smooth(0.78, 1.0, u) ** 2
    side = np.sign(th) if abs(th) > 0.05 else np.sign(np.sin(ph[2]))
    P[:, 0] += wave + 0.008 * side * curl
    P[:, 1] += fwd - 0.006 * curl
    P[:, 2] += 0.004 * np.sin(2 * np.pi * u * 0.8 + ph[3])
    # an S-curve in depth too: wavy locks, not straight rods
    P[:, 1] += 0.008 * np.sin(2 * np.pi * u * 0.9 + ph[0]) * smooth(0.1, 0.4, u)
    r = sp['r0'] * (1.0 - 0.86 * u ** 1.35) + 0.0022
    # the chops' roots thin out into the cheek (round 2: a round chestnut ball on the cheek)
    root_k = 0.45 + 0.55 * smooth(0.0, 0.22, u) if abs(th) > 0.7 else 0.75 + 0.25 * smooth(0.0, 0.1, u)
    r = r * root_k
    # the scarf wraps under the beard: push any point of the clump out of the band's shell
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
    out += web_meshes(scarf_outer)
    return out


WEB_DEPTH = 0.55       # the web's half depth, a share of its clumps' radius
WEB_END = (0.6, 0.8)   # u where the webs thin out and stop (the tips stay separate points)


def web_meshes(scarf_outer) -> list[bpy.types.Object]:
    """3b: a flat web between each pair of neighbouring clumps of a layer, half as deep as the clumps: the grooves
    between them stay shallow and open (round 3: deep narrow slots between the clumps baked black, dark specks)."""
    out = []
    ph = np.linspace(0, 2 * np.pi, SIDES, endpoint=False)
    cl = build_clumps(scarf_outer)
    u = np.linspace(0.0, 1.0, NU)
    keep = u <= WEB_END[1]
    taper = 0.25 + 0.75 * smooth(WEB_END[1], WEB_END[0], u[keep])
    for layer in (0, 1, 3):
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
        kd = KDTree(len(pts))
        for i, p in enumerate(pts):
            kd.insert(p, i)
        kd.balance()
        _KD['kd'] = kd
    return _KD


def lookup(p: np.ndarray, pad: float = 0.022) -> dict:
    """Per point: on a clump (within its radius + pad), u along it, its θ (the chain blend) and its comb direction."""
    k = len(p)
    out = {'on': np.zeros(k, bool), 'u': np.zeros(k), 'th': np.zeros(k), 'dir': np.tile(v3((0.0, 0.0, -1.0)), (k, 1))}
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
    return out


def chain_blend(th: np.ndarray) -> dict[str, np.ndarray]:
    """How much of each chain a point of clump θ follows."""
    side = smooth(0.25, 0.62, np.abs(th))
    return {'beard': 1.0 - side, 'beardL': side * (th > 0), 'beardR': side * (th <= 0)}
