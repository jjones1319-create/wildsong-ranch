"""Ashwraith's small props (ashwraith_ultra.build_props): the hood's tip, the two little hands, and Lantern-bearer's
iron lantern (that variant only). The cloth is in ashwraith_cloth.py, the wisps in ashwraith_wisps.py.

- The tip (round 2): a fat, soft cloth tube from inside the hood's point up to its top, flopping forward and to the
  monster's right and curling over into a wisp, its end torn into a few frayed strands; it rides the `hood` chain.
- The hands (round 2): soft cream mittens clutching the cloak's front panels at the chest, no sleeves (4-details 3):
  a palm, four plump fingers merged into a mitten curled over the cloth, a thumb.
- The lantern (Lantern-bearer, variant picture; round 2): about a quarter of the body's height, held up at the chest
  by its ring in both hands: a domed cap, a hexagonal iron frame, glowing blue panes with the flame painted on them.
Each object carries ashwraith_mesh.ATTRS (part, pt, pa, pr, side).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib.surface import smooth, v3
from monsters.breeds import ashwraith_form as F
from monsters.breeds import ashwraith_mesh as AM

CAPE, TIP, HAND, CUFF, WISP, SPRIG, IRON, GLASS, RING, PANEL, LASH = 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
LANTERN_PARTS = (IRON, GLASS, RING)


# ----------------------------------------------------------------------------- the hood's tip
def tip_path(n: int) -> np.ndarray:
    root = np.array([-0.06, 0.005, 0.975])
    rise = AM.catmull([root, F.HOOD_TIP[0], F.HOOD_TIP[1], F.HOOD_TIP[2]], 40)
    m = 90
    u = np.linspace(0.0, 1.0, m)
    phi = F.TIP_PHI[0] + (F.TIP_PHI[1] - F.TIP_PHI[0]) * u
    R = F.TIP_R[0] + (F.TIP_R[1] - F.TIP_R[0]) * u ** 0.85
    up = np.array([0.0, 0.0, 1.0])
    curl = F.TIP_C[None] + R[:, None] * (np.cos(phi)[:, None] * F.TIP_W[None] + np.sin(phi)[:, None] * up[None])
    rise = rise + (curl[0] - rise[-1])[None] * np.linspace(0.0, 1.0, len(rise))[:, None] ** 2
    return AM.resample(np.vstack([rise, curl[1:]]), n)


def tip_size(t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Round 3: a broad, flattened cloth tip (it read as a thin round tube): its half thickness and its half width (in
    the curl's plane) along it: 2.2 cm by 5 cm at the hood's point, 1.4 by 3.4 at its top, 0.6 by 1.4 at the spiral's end."""
    th = np.interp(t, [0.0, 0.2, 0.45, 0.75, 1.0], [0.022, 0.017, 0.013, 0.009, 0.006])
    wd = np.interp(t, [0.0, 0.2, 0.45, 0.75, 1.0], [0.05, 0.04, 0.032, 0.022, 0.014])
    return th, wd


def tip_object(name: str, high: bool) -> bpy.types.Object:
    n = 220 if high else 72
    P = tip_path(n)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    t = s / s[-1]
    sides = 44 if high else 14
    th, wd = tip_size(t)
    plane_n = np.cross(F.TIP_W, np.array([0.0, 0.0, 1.0]))
    plane_n /= np.linalg.norm(plane_n)

    def relief(a, ss):
        # soft cloth folds across it, and a torn, frayed edge along its two thin sides (a = 0.25, 0.75)
        edge = np.abs(np.sin(2 * np.pi * a)) ** 6
        tear = 0.004 * edge * (0.5 + 0.5 * np.sin(ss / 0.006 + 3.0 * a)) * (1.0 if high else 0.6)
        return 0.0025 * np.sin(2 * np.pi * (2 * a + 0.35 * np.sin(ss / 0.045))) - tear
    kit = AM.Kit()
    # width in the curl's plane (the broad side shows the spiral), thickness across it
    kit.tube(P, th, sides, TIP, hint=tuple(plane_n), aspect=wd / th, relief=relief, texel_k=1.0)
    T = P[-1] - P[-4]
    T /= np.linalg.norm(T)
    side = np.cross(T, plane_n)
    side /= max(np.linalg.norm(side), 1e-9)
    for k, (sa, ln, w) in enumerate(((-1.0, 0.045, 0.009), (-0.35, 0.06, 0.01), (0.35, 0.05, 0.009), (1.0, 0.04, 0.008))):
        q0 = P[-6] + side * sa * 0.01
        q1 = q0 + T * ln * 0.5 + side * sa * 0.012
        q2 = q1 + T * ln * 0.4 + side * sa * 0.01 + np.array([0.0, 0.0, 0.008])
        S_ = AM.catmull([q0, q1, q2], 14 if high else 6)
        kit.tube(S_, np.linspace(w, 0.0025, len(S_)), 12 if high else 6, TIP, hint=side, aspect=0.6, texel_k=1.0)
    ob = kit.object(name)
    ob['prop'] = 'tip'
    return ob


# ----------------------------------------------------------------------------- the hands
def _blob(kit: AM.Kit, c: np.ndarray, axes, half, part: int, high: bool, k_tex: float = 1.3) -> None:
    """A closed ellipsoid (axes: three unit vectors, half: their half lengths) added to the kit."""
    nu, nv = (40, 22) if high else (14, 8)
    ex, ey, ez = (np.asarray(v, np.float64) for v in axes)
    rings = []
    for ph in np.linspace(-np.pi / 2, np.pi / 2, nv)[1:-1]:
        th = np.linspace(-np.pi, np.pi, nu, endpoint=False)
        rings.append(c[None] + (np.cos(ph) * np.cos(th))[:, None] * ex * half[0] + (np.cos(ph) * np.sin(th))[:, None] * ey * half[1]
                     + np.sin(ph) * ez[None] * half[2])
    m = nu
    base = kit._add(np.concatenate(rings), part, 0.0, 0.0, 0.5, 0.0)
    for k in range(len(rings) - 1):
        for j in range(m):
            j2 = (j + 1) % m
            kit.faces.append((base + k * m + j, base + k * m + j2, base + (k + 1) * m + j2, base + (k + 1) * m + j))
            kit.uvs.append(None)
            kit.kface.append(k_tex)
    for end, sg in ((0, -1.0), (1, 1.0)):
        pole = kit._add((c + ez * half[2] * sg)[None], part, 0.0, 0.0, 0.5, 0.0)
        r0 = base + (0 if end == 0 else (len(rings) - 1) * m)
        for j in range(m):
            j2 = (j + 1) % m
            kit.faces.append((pole, r0 + j2, r0 + j) if end == 0 else (pole, r0 + j, r0 + j2))
            kit.uvs.append(None)
            kit.kface.append(k_tex)


def _mitten(kit: AM.Kit, s: int, high: bool) -> None:
    """Round 3: one soft mitten (five stacked rolls read as a garlic bulb): a rounded pad, its front curled down over the
    cloth, three shallow creases between the fingers, a small thumb bump on the inner side; half tucked into the folds."""
    h = v3(F.mirror(F.ARM['hand'], s))
    nu, nv = (56, 36) if high else (18, 12)
    X, Y, Z = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    half = (0.03, 0.024, 0.026)
    rings = []
    for ph in np.linspace(-np.pi / 2, np.pi / 2, nv)[1:-1]:
        ring = []
        for a in np.linspace(-np.pi, np.pi, nu, endpoint=False):
            lx, ly, lz = math.cos(ph) * math.cos(a), math.sin(ph), math.cos(ph) * math.sin(a)   # x across, y back, z up
            r = 1.0
            front = max(0.0, -ly)
            # the fingers curl down: the front's lower half bulges a little forward and down
            r += 0.14 * front * max(0.0, -lz)       # polish: curled over the cloth's edge (it read as a bean)
            # three shallow creases across the front, between four fingers
            for gx in (-0.5, 0.0, 0.5):
                r -= 0.12 * math.exp(-((lx - gx) / 0.08) ** 2) * front ** 1.5 * (0.4 + 0.6 * max(0.0, lz + 0.3))
            # the thumb on the inner side
            r += 0.16 * math.exp(-(((lx * s) + 0.85) / 0.25) ** 2 - ((ly + 0.2) / 0.5) ** 2 - ((lz - 0.1) / 0.5) ** 2)
            ring.append(h + Y * 0.004 + (X * lx * half[0] + Y * ly * half[1] + Z * lz * half[2]) * r)
        rings.append(np.array(ring))
    m = nu
    base = kit._add(np.concatenate(rings), HAND, 0.0, 0.0, 0.5, 0.0)
    for k in range(len(rings) - 1):
        for j in range(m):
            j2 = (j + 1) % m
            kit.faces.append((base + k * m + j, base + k * m + j2, base + (k + 1) * m + j2, base + (k + 1) * m + j))
            kit.uvs.append(None)
            kit.kface.append(1.3)
    for end, sg in ((0, -1.0), (1, 1.0)):
        pole = kit._add((h + Y * 0.004 + Y * half[1] * sg)[None], HAND, 0.0, 0.0, 0.5, 0.0)
        r0 = base + (0 if end == 0 else (len(rings) - 1) * m)
        for j in range(m):
            j2 = (j + 1) % m
            kit.faces.append((pole, r0 + j2, r0 + j) if end == 0 else (pole, r0 + j, r0 + j2))
            kit.uvs.append(None)
            kit.kface.append(1.3)


def hands_object(name: str, high: bool) -> bpy.types.Object:
    kit = AM.Kit()
    for s in (1, -1):
        _mitten(kit, s, high)
    ob = kit.object(name, own_uv=False)
    ob['prop'] = 'hands'
    return ob


# ----------------------------------------------------------------------------- the lantern (Lantern-bearer only)
LANTERN_C = np.array([0.0, -0.33, 0.0])          # its axis (x, y): clear of the front panels; heights below
# polish (the variant picture: both hands hold its ring at centre front, the lantern hanging below them): the ring faces
# forward between the hands, which grip its sides; a short bail drops from it to the cap
RING_C = (0.0, -0.262, 0.5)
RING_R = 0.044
LANTERN_Z = {'ring': 0.5, 'cap_top': 0.41, 'cap': 0.384, 'top': 0.374, 'bottom': 0.246, 'base': 0.226}
LANTERN_R = 0.05                                 # the hexagon's corner radius


def _hex(z: float, r: float, rot: float = 0.0) -> np.ndarray:
    a = np.arange(6) / 6 * 2 * np.pi + rot
    return np.stack([LANTERN_C[0] + r * np.cos(a), LANTERN_C[1] + r * np.sin(a), np.full(6, z)], axis=1)


def lantern_object(name: str, high: bool) -> bpy.types.Object:
    """A dark iron lantern: a ring between the hands, a bail to the domed cap, six thick corner posts and rims, a base;
    each pane glass behind iron fretwork with an arched window, the flame painted inside (shade.prop_material)."""
    kit = AM.Kit()
    Z, R = LANTERN_Z, LANTERN_R
    ax = np.array([LANTERN_C[0], LANTERN_C[1], 0.0])
    ring_c = np.array(RING_C)
    t = np.linspace(0, 2 * np.pi, 41 if high else 17)
    loop = ring_c + RING_R * np.stack([np.cos(t), np.zeros_like(t), np.sin(t)], 1)
    kit.tube(loop, 0.0055, 12 if high else 6, RING, caps=(False, False), hint=(0, 1, 0), texel_k=1.0)
    bail = AM.catmull([ring_c + np.array([0.0, 0.0, -RING_R]), ring_c + np.array([0.0, -0.035, -RING_R - 0.03]),
                       ax + np.array([0.0, 0.0, Z['cap_top'] + 0.006])], 10 if high else 5)
    kit.tube(bail, 0.004, 8 if high else 5, IRON, caps=(True, True), texel_k=1.0)
    prof = [(0.008, Z['cap_top'] + 0.008), (0.016, Z['cap_top']), (0.04, Z['cap'] + 0.014), (R * 1.14, Z['cap']), (R * 1.16, Z['top'] - 0.002)]
    nseg = 36 if high else 12
    for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
        P = np.array([ax + np.array([0, 0, z0]), ax + np.array([0, 0, z1])])
        kit.tube(P, (r0, r1), nseg, IRON, caps=(False, False), hint=(1, 0, 0), texel_k=1.0)
    for c0, c1 in zip(_hex(Z['top'], R), _hex(Z['bottom'], R)):
        kit.tube(np.array([c0, c1]), 0.0072, 8 if high else 5, IRON, caps=(True, True), texel_k=1.0)
    for z in (Z['top'], Z['bottom']):
        hx = _hex(z, R)
        kit.tube(np.vstack([hx, hx[:1]]), 0.0075, 8 if high else 5, IRON, caps=(False, False), hint=(0, 0, 1), texel_k=1.0)
    kit.tube(np.array([ax + np.array([0, 0, Z['base']]), ax + np.array([0, 0, Z['bottom'] - 0.002])]), (R * 1.2, R * 1.12), nseg, IRON,
             caps=(True, True), hint=(1, 0, 0), texel_k=1.0)
    for i in range(6):
        a0, a1 = _hex(Z['top'], R * 0.93)[i], _hex(Z['top'], R * 0.93)[(i + 1) % 6]
        b0, b1 = _hex(Z['bottom'], R * 0.93)[i], _hex(Z['bottom'], R * 0.93)[(i + 1) % 6]
        nv, nu = (40, 26) if high else (4, 3)
        uu = np.linspace(0, 1, nu + 1)
        vv = np.linspace(0, 1, nv + 1)
        top = a0[None] + (a1 - a0)[None] * uu[:, None]
        bot = b0[None] + (b1 - b0)[None] * uu[:, None]
        grid = top[None] + (bot - top)[None] * vv[:, None, None]
        kit.shell(grid, 0.003, GLASS, pr=i / 6.0, inside=lambda q: np.stack([np.full(len(q), LANTERN_C[0]), np.full(len(q), LANTERN_C[1]), q[:, 2]], 1),
                  texel_k=1.8)
    ob = kit.object(name)
    ob['prop'] = 'lantern'
    return ob


def pane_masks(pa: np.ndarray, pt: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(window, flame) 0..1 on a pane (pa across 0..1, pt down 0..1): an arched window in the iron fretwork, a flame
    standing in its middle (numpy twin of shade.prop_material's, for the glow)."""
    x = pa - 0.5
    y = pt
    arch = np.where(y < 0.3, np.hypot(x / 0.34, (y - 0.3) / 0.22) < 1.0, (np.abs(x) < 0.34) & (y < 0.88))
    win = arch.astype(np.float64)
    fy = y - 0.62
    w = 0.3 * np.maximum(fy * 1.6 + 0.6, 0.0) ** 0.7
    flame = smooth(w + 0.04, w, np.abs(x)) * smooth(0.3, 0.22, fy) * smooth(-0.42, -0.34, fy)
    return win, flame


def objects(high: bool, quick: bool = False) -> list:
    tag = 'hi' if high else 'lo'
    return [tip_object(f'{tag}_tip', high), hands_object(f'{tag}_hands', high), lantern_object(f'{tag}_lantern', high)]
