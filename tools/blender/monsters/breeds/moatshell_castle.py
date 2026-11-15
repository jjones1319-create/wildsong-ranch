"""Moatshell's castle keep (Art 2.1 Ultra; chatgpt/monsters/19-moatshell): the shell is a tiny sandstone keep. The
layout and the brick patterns live here; moatshell_keep.py builds the meshes from them.

The parts, from the turnaround (side view: 1.10 m tall with the flag, 1.20 m nose to tail):
  - the skirt: a ring of 20 big rounded sandstone blocks sloping out and down like a carapace's rim, lifted over the
    neck at the front (its foot at 0.27 m on the sides, 0.52 m over the neck);
  - the main wall: a slightly battered drum (outer radius 0.338 → 0.318 m) of coursed bricks up to the crenel level
    (0.705 m), 20 merlons on top (6.8 cm), a wooden rail through them, six arched arrow slits framed in brick-red
    voussoirs, and an arched plank door with iron straps and a ring at the back-left (the hero shows it from the left);
  - the tower: a smaller drum (radius 0.153 → 0.145 m) rising from the keep's floor to 0.858 m, 10 merlons, a rail
    and three slits;
  - the pole (wood, a ball finial at 1.10 m) flying a teal swallow-tailed pennant toward the back-left.
Angles θ run from the front (−Y) toward the monster's left (+X): direction (sin θ, −cos θ). Metres.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import moatshell_noise as N

TAU = 2 * math.pi
smooth = N.smooth


def dirv(th) -> np.ndarray:
    th = np.asarray(th, np.float64)
    return np.stack([np.sin(th), -np.cos(th)], axis=-1)


# ----------------------------------------------------------------------------- the skirt (the carapace's rim)
# round 1 (review): one continuous rampart of chunky blocks round the whole shell (thin flat plates read as card), in the
# wall's own sandstone, lifted in an arch over the neck and carried round the back over the tail
SKIRT_N = 22
SKIRT_RI = 0.372                  # its top outer edge, just outside the wall's foot
SKIRT_T = 0.078                   # the blocks' thickness, across the slope (chunky)
SKIRT_GAP = 0.0042                # mortar gaps between blocks (metres at mid-slope; polish: tighter)
SKIRT_ROUND = 0.012               # the blocks' rounded edges (then chipped)


def front_k(th):
    """1 straight over the neck, easing to 0 by the flanks: the rim rises round the neck like a collar (2-turnaround
    front: from 0.27 m at the sides to about 0.5 m beside the neck)."""
    th = np.asarray(th, np.float64)
    return smooth(0.95, 0.0, np.abs(np.sin(th))) * (np.cos(th) > 0)


def back_k(th):
    return smooth(0.2, 1.0, -np.cos(th))


def skirt_zb(th):
    """The skirt's lower outer edge: 0.27 m on the sides, lifted over the neck in front, a touch higher at the back."""
    return 0.272 + 0.25 * front_k(th) + 0.03 * back_k(th)


def skirt_zt(th):
    return skirt_zb(th) + 0.15 - 0.07 * front_k(th)        # shorter blocks in the arch over the neck


def skirt_ro(th):
    return 0.415 - 0.015 * front_k(th)


def skirt_outer(th, s):
    """The skirt's outer surface: s 0 at the top inner edge → 1 at the lower outer edge, bulging out a little."""
    th = np.asarray(th, np.float64)
    s = np.asarray(s, np.float64)
    r = SKIRT_RI + (skirt_ro(th) - SKIRT_RI) * s
    z = skirt_zt(th) + (skirt_zb(th) - skirt_zt(th)) * s
    n_r, n_z = skirt_normal(th)
    bul = 0.011 * np.sin(math.pi * s)
    r = r + n_r * bul
    z = z + n_z * bul
    d = dirv(th)
    return np.stack([d[..., 0] * r, d[..., 1] * r, z], axis=-1)


def skirt_normal(th):
    """(radial, up) unit normal of the slope (outward and a little up)."""
    dr = skirt_ro(th) - SKIRT_RI
    dz = skirt_zb(th) - skirt_zt(th)
    L = np.sqrt(dr * dr + dz * dz)
    return -dz / L, dr / L


def skirt_len(th):
    dr = skirt_ro(th) - SKIRT_RI
    dz = skirt_zb(th) - skirt_zt(th)
    return np.sqrt(dr * dr + dz * dz)


def skirt_block_angles() -> np.ndarray:
    """The blocks' centres: one straight over the neck."""
    return np.arange(SKIRT_N) * TAU / SKIRT_N


# ----------------------------------------------------------------------------- the main wall
WALL_Z0 = 0.27                    # where its batter is measured from (hidden under the skirt)
WALL_RB, WALL_RT = 0.376, 0.333        # round 1: a wider base, tapering in toward the top (2-turnaround front)
WALL_ZTOP = 0.705                 # the crenel level
WALL_T = 0.05                     # the parapet's thickness
FLOOR_Z = 0.655                   # the keep's floor, between the parapet and the tower
MERLON_N, MERLON_SHARE, MERLON_H = 20, 0.66, 0.058       # round 2: squarer, chunkier merlons
RAIL = {'r': WALL_RT - 0.5 * WALL_T, 'z': WALL_ZTOP + 0.022, 'tube': 0.0075}


def wall_r(z):
    return WALL_RB + (WALL_RT - WALL_RB) * (np.asarray(z, np.float64) - WALL_Z0) / (WALL_ZTOP - WALL_Z0)


def wall_zbot(th):
    return skirt_zt(th) - 0.05


# ----------------------------------------------------------------------------- the tower
TOWER_Z0, TOWER_ZTOP = 0.62, 0.858
TOWER_RB, TOWER_RT = 0.153, 0.145
TOWER_T = 0.038
TOWER_FLOOR = 0.83
TMERLON_N, TMERLON_SHARE, TMERLON_H = 10, 0.64, 0.052
TRAIL = {'r': TOWER_RT - 0.5 * TOWER_T, 'z': TOWER_ZTOP + 0.02, 'tube': 0.0065}


def tower_r(z):
    return TOWER_RB + (TOWER_RT - TOWER_RB) * (np.asarray(z, np.float64) - TOWER_Z0) / (TOWER_ZTOP - TOWER_Z0)


# ----------------------------------------------------------------------------- pole and flag
POLE = {'z0': 0.82, 'z1': 1.066, 'r': 0.0105}
FINIAL = {'z': 1.0835, 'r': 0.0185}              # its top at 1.102 m: HEIGHT_UNITS 165 → 1.10 m with the flag
FLAG_DIR = math.radians(40.0)                     # from straight back toward the monster's left
FLAG = {'len': 0.30, 'h0': 0.10, 'h1': 0.084, 'zc': 1.003, 'notch': 0.055, 'thick': 0.0045, 'off': 0.012}


def flag_axes() -> tuple[np.ndarray, np.ndarray]:
    """(along, across): the flag's direction (back-left) and its horizontal normal."""
    a = np.array([math.sin(FLAG_DIR), math.cos(FLAG_DIR), 0.0])
    n = np.array([math.cos(FLAG_DIR), -math.sin(FLAG_DIR), 0.0])
    return a, n


def flag_centre(u):
    """The flag's centre line (u 0 at the pole → 1 at the fly): a slight droop."""
    a, _n = flag_axes()
    u = np.asarray(u, np.float64)
    x = FLAG['off'] + FLAG['len'] * u
    z = FLAG['zc'] - 0.012 * u * u
    return a[None] * x[..., None] + np.stack([np.zeros_like(u), np.zeros_like(u), z], axis=-1)


def flag_points() -> list[tuple[float, float, float]]:
    """The flag chain's 4 points (3 bones) along its centre line."""
    return [tuple(map(float, flag_centre(np.array([k / 3.0]))[0])) for k in range(4)]


# ----------------------------------------------------------------------------- openings
# arrow slits: (wall, θ degrees, centre z); the door on the main wall at the back-left
WINDOWS = [('wall', 40.0, 0.578), ('wall', 95.0, 0.565), ('wall', 185.0, 0.57), ('wall', -40.0, 0.578),
           ('wall', -95.0, 0.565), ('wall', -140.0, 0.57), ('tower', 25.0, 0.765), ('tower', 150.0, 0.765),
           ('tower', -100.0, 0.765)]
SLIT = {'wall': {'a': 0.0135, 'hb': 0.034, 'hs': 0.017}, 'tower': {'a': 0.0115, 'hb': 0.028, 'hs': 0.014}}
DOOR = {'th': 140.0, 'w': 0.12, 'rect': 0.105, 'proud': 0.004, 'thick': 0.012}


def door_z0() -> float:
    return float(skirt_zt(math.radians(DOOR['th']))) - 0.012


def wall_radius(which: str, z):
    return wall_r(z) if which == 'wall' else tower_r(z)


def slit_mask(x, zp, which: str, grow: float = 0.0):
    """0..1 inside an arrow slit's outline (local x across, zp up from its centre), softened over 1.5 mm."""
    sp = SLIT[which]
    a, hb, hs = sp['a'] + grow, sp['hb'] + grow, sp['hs']
    rect = np.maximum(np.abs(x) - a, np.maximum(-hb - zp, zp - hs))
    arch = np.sqrt(x * x + np.maximum(zp - hs, 0.0) ** 2) - a
    sdf = np.where(zp > hs, arch, rect)
    return smooth(0.0015, -0.0005, sdf)


def ang_wrap(a):
    return (np.asarray(a, np.float64) + math.pi) % TAU - math.pi


# ----------------------------------------------------------------------------- coursed bricks
WALL_BRICKS = {'z0': 0.20, 'z1': 0.80, 'row': 0.046, 'row_jit': 0.2, 'len': 0.085, 'len_jit': 0.42, 'r_ref': 0.355,
               'gap': 0.0048, 'depth': 0.0075, 'bevel': 0.0045, 'corner': 0.006, 'seed': 101, 'red': 0.06}
TOWER_BRICKS = {'z0': 0.60, 'z1': 0.90, 'row': 0.039, 'row_jit': 0.18, 'len': 0.066, 'len_jit': 0.4, 'r_ref': 0.15,
                'gap': 0.0042, 'depth': 0.0065, 'bevel': 0.004, 'corner': 0.005, 'seed': 131, 'red': 0.04}
FLOOR_BRICKS = {'z0': 0.10, 'z1': 0.30, 'row': 0.042, 'row_jit': 0.1, 'len': 0.07, 'len_jit': 0.3, 'r_ref': None,
                'gap': 0.004, 'depth': 0.004, 'bevel': 0.004, 'corner': 0.005, 'seed': 151, 'red': 0.0}
TFLOOR_BRICKS = {'z0': 0.0, 'z1': 0.12, 'row': 0.034, 'row_jit': 0.1, 'len': 0.055, 'len_jit': 0.3, 'r_ref': None,
                 'gap': 0.0035, 'depth': 0.0035, 'bevel': 0.0035, 'corner': 0.004, 'seed': 171, 'red': 0.0}


def _rows(spec: dict) -> np.ndarray:
    """Course boundaries from z0 to past z1 (heights jittered per course)."""
    out, z, k = [spec['z0']], spec['z0'], 0
    while z < spec['z1']:
        z += spec['row'] * (1.0 + spec['row_jit'] * (2.0 * float(N.hash1(k, spec['seed'])[0]) - 1.0))
        out.append(z)
        k += 1
    return np.array(out)


def _row_bricks(k: int, circ: float, spec: dict) -> tuple[np.ndarray, float]:
    """One course's brick boundaries round a ring of `circ` metres (lengths jittered, rescaled to close the ring) and
    its phase."""
    seed = spec['seed'] + 7
    ls, tot, i = [], 0.0, 0
    while tot < circ - 0.5 * spec['len']:
        h = float(N.hash3(np.array([[k, i, 3]]), seed)[0])
        L = spec['len'] * (1.0 + spec['len_jit'] * (2.0 * h - 1.0))
        ls.append(L)
        tot += L
        i += 1
    ls = np.array(ls) * (circ / max(tot, 1e-9))
    b = np.concatenate([[0.0], np.cumsum(ls)])
    phase = float(N.hash3(np.array([[k, 0, 9]]), seed)[0]) * spec['len']
    return b, phase


def bricks(s: np.ndarray, z: np.ndarray, circ, spec: dict, rows=None) -> dict:
    """Coursed bricks over (s along the ring in metres, z up): the relief h (metres, ≤ 0: grooves between the bricks
    with rounded edges, a small tilt and bulge per brick) and, per point, 'bid' (0..1 per brick), 'mortar' (0..1 in a
    joint), 'edge' (0..1 near a brick's edge), 'red' (1 on the few brick-red bricks), 'sd' (signed metres to the brick's
    edge, < 0 inside). `circ` is the ring's length in metres (a number, or per point for courses of their own ring)."""
    rows = _rows(spec) if rows is None else rows
    n = len(s)
    circ = np.broadcast_to(np.asarray(circ, np.float64), (n,))
    out = {k: np.zeros(n) for k in ('h', 'bid', 'mortar', 'edge', 'red', 'sd')}
    rk = np.clip(np.searchsorted(rows, z) - 1, 0, len(rows) - 2)
    for k in np.unique(rk):
        m = np.nonzero(rk == k)[0]
        cmean = float(np.mean(circ[m]))
        b, ph = _row_bricks(int(k), cmean, spec)
        sp = np.mod(s[m] * (cmean / circ[m]) - ph, cmean)
        j = np.clip(np.searchsorted(b, sp) - 1, 0, len(b) - 2)
        cs = 0.5 * (b[j] + b[j + 1])
        hs = 0.5 * (b[j + 1] - b[j]) - 0.5 * spec['gap']
        cz = 0.5 * (rows[k] + rows[k + 1])
        hz = 0.5 * (rows[k + 1] - rows[k]) - 0.5 * spec['gap']
        qs, qz = sp - cs, z[m] - cz
        c = spec['corner']
        dx, dz = np.abs(qs) - (hs - c), np.abs(qz) - (hz - c)
        sd = np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dz, 0) ** 2) + np.minimum(np.maximum(dx, dz), 0) - c
        ids = np.stack([np.full(len(m), int(k)), j, np.full(len(m), 5)], axis=1)
        hb = N.hash3(ids, spec['seed'] + 11)
        g = np.stack([N.hash3(ids, spec['seed'] + 12), N.hash3(ids, spec['seed'] + 13)], axis=1) - 0.5
        tilt = 0.0028 * (g[:, 0] * qs / np.maximum(hs, 1e-3) + g[:, 1] * qz / np.maximum(hz, 1e-3))
        bulge = 0.001 * (1.0 - np.clip((qs / np.maximum(hs, 1e-3)) ** 2, 0, 1)) * (1.0 - np.clip((qz / np.maximum(hz, 1e-3)) ** 2, 0, 1))
        face = smooth(0.0, spec['bevel'], -sd)
        out['h'][m] = -spec['depth'] * (1.0 - face) + (tilt + bulge) * face
        out['bid'][m] = hb
        out['mortar'][m] = smooth(-0.0012, 0.0008, sd)
        out['edge'][m] = smooth(-0.012, -0.002, sd)
        out['red'][m] = (N.hash3(ids, spec['seed'] + 14) < spec['red']).astype(np.float64)
        out['sd'][m] = sd
    return out


def stone_detail(p: np.ndarray, edge: np.ndarray, seed: int, chip_cell: float = 0.02, chip_depth: float = 0.004,
                 pits: float = 1.0, big_pits: float = 0.0) -> dict:
    """Chips at the edges (flat facets cut in near them; `edge` 0..1 near an edge), pits and a fine grain over a
    block's face: 'h' (metres) and 'chip' 0..1, 'pit' 0..1."""
    ch = N.facets(p, chip_cell, seed) * edge
    f1, _f2, _ = N.voronoi(p, 0.0075, seed + 1)
    pit = smooth(0.0022, 0.0008, f1) * smooth(-0.2, 0.3, N.fbm(p, 1 / 0.05, seed + 2, 2)) * pits
    gr = N.fbm(p, 1 / 0.006, seed + 3, 2)
    wav = N.fbm(p, 1 / 0.07, seed + 4, 2)
    h = -chip_depth * ch - 0.0016 * pit + 0.00035 * gr + 0.0009 * wav
    if big_pits:
        # round 1: big blocks pitted like the wall's sandstone (4-details panel 6), not smooth card
        g1, _g2, gid = N.voronoi(p, 0.016, seed + 5)
        rad = 0.0022 + 0.0016 * (np.abs(gid) % 97) / 96.0
        bp = smooth(rad, 0.55 * rad, g1) * (N.hash1(np.abs(gid) % 100003, seed + 6) < 0.45) * big_pits
        h = h - 0.0026 * bp
        pit = np.maximum(pit, bp)
    return {'h': h, 'chip': np.clip(ch * 1.6, 0, 1), 'pit': pit}
