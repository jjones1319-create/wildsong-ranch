"""Ashwraith's drape (round 2 of the review): the shroud's cloth hanging over the dark core, as separate ragged pieces.

- The shroud surface S(theta, z): the cloth falls straight down from the hood's widest part and flares to 0.64 m at
  the hems (2-turnaround), the back trailing; deep vertical folds (the same field for every piece, faded at a piece's
  side edges so overlapping edges never cross).
- The cape: one long piece from under the hood round the back and sides to beside the face (its top tucked inside
  the hood, so the hood drapes straight into it: no ridge, no second tier), its hem torn into staggered tatters (the
  back lowest), real holes cut near the hem.
- Four front panels the hands clutch closed at the chest (1-hero, 2-turnaround front): two inner ones crossing under
  the face (the left over the right) and gathered in each hand, two outer ones under them at the sides, over the
  cape's front edges; each falls from the gather to a torn hem.
- The chains: eight `wisp` chains round the hems (front, sides, back sides, back) carry the hems and the wisps; two
  `ribbon` streamers hang from the hands' grip down the front (the lash strike whips them up past the hands).
Pure numpy.
"""
from __future__ import annotations

import math

import numpy as np

from lib.surface import smooth
from monsters.breeds import ashwraith_form as F

D2R = math.pi / 180.0
SH_Z = np.array([0.08, 0.20, 0.30, 0.40, 0.50, 0.58, 0.66, 0.74, 0.80])
SH_A = np.array([0.318, 0.316, 0.31, 0.298, 0.284, 0.276, 0.27, 0.261, 0.254])     # half width
SH_B = np.array([0.302, 0.298, 0.29, 0.275, 0.256, 0.238, 0.214, 0.19, 0.18])      # half depth
SH_YC = np.array([0.078, 0.068, 0.055, 0.04, 0.026, 0.018, 0.014, 0.017, 0.017])    # the back trails; at z 0.74 it meets
                                                                                  # the hood's widest part (+5 mm)


def sh_abyc(z):
    z = np.asarray(z, np.float64)
    return np.interp(z, SH_Z, SH_A), np.interp(z, SH_Z, SH_B), np.interp(z, SH_Z, SH_YC)


def folds(th, z) -> np.ndarray:
    """The shroud's vertical folds: a relative bulge, deepest low down (round 2: deeper, sharper valleys)."""
    th, z = np.asarray(th, np.float64), np.asarray(z, np.float64)
    deep = 0.024 + 0.12 * smooth(0.64, 0.2, z)          # round 3: deeper, sharper valleys (dark grooves in the AO)
    s = np.sin(9.0 * th + 0.4 + 1.5 * z)
    return deep * (0.62 * np.sign(s) * np.abs(s) ** 0.5 + 0.38 * np.sin(14.0 * th + 1.3 + 2.0 * z))


def shroud_point(th, z, extra=0.0, fold_k=1.0) -> np.ndarray:
    """A point on the shroud surface at angle th (0 front, +pi/2 its left) and height z, `extra` metres further out."""
    th, z = np.broadcast_arrays(np.asarray(th, np.float64), np.asarray(z, np.float64))
    a, b, yc = sh_abyc(z)
    k = 1.0 + folds(th, z) * fold_k
    ex = np.asarray(extra, np.float64)
    return np.stack([(a * k + ex) * np.sin(th), yc - (b * k + ex) * np.cos(th), z], axis=-1)


def tatters(u, spec, zig=0.012) -> np.ndarray:
    """Extra drop (metres) along a hem: pointed strips (u centre, half width, drop), plus a frayed zigzag."""
    u = np.asarray(u, np.float64)
    out = np.zeros_like(u)
    for c, w, d in spec:
        out = np.maximum(out, d * np.clip(1.0 - np.abs(u - c) / w, 0, 1) ** 1.3)
    fray = (0.5 + 0.5 * np.sin(57.0 * u + 0.7)) * (0.6 + 0.4 * np.sin(23.0 * u + 1.9)) + 0.45 * np.abs(np.sin(131.0 * u + 0.3)) ** 3
    return out + zig * 1.5 * fray                         # round 3: a more frayed, uneven torn edge


# ============================================================================ the cape
CAPE_TOP = 0.78
CAPE_TH = (80.0 * D2R, 120.0 * D2R)      # its front edges, round from the back: behind the hood's sides at the top (they hung
                                         # beside the face like stiff flaps), coming forward below the face
CAPE_T = 0.008
CAPE_TATTERS = [(-0.9, 0.05, 0.05), (-0.66, 0.07, 0.085), (-0.45, 0.04, 0.05), (-0.22, 0.06, 0.075), (-0.02, 0.05, 0.08),
                (0.2, 0.07, 0.06), (0.43, 0.04, 0.085), (0.64, 0.06, 0.07), (0.86, 0.05, 0.055), (-0.33, 0.03, 0.04),
                (0.55, 0.03, 0.04), (0.1, 0.03, 0.035)]


def cape_theta(u, v) -> np.ndarray:
    tb = np.asarray(u, np.float64) * (CAPE_TH[0] + (CAPE_TH[1] - CAPE_TH[0]) * smooth(0.0, 0.3, v))
    return math.pi - tb


def cape_hem_z(u) -> np.ndarray:
    """The cape's hem: lowest at the back (0.17), rising to the sides and the front edges (0.3), torn into tatters."""
    u = np.asarray(u, np.float64)
    base = 0.175 + 0.13 * np.abs(u) ** 1.6
    return np.maximum(base - tatters(u, CAPE_TATTERS), 0.088)


def cape_fold_k(u) -> np.ndarray:
    return 1.0 - smooth(0.8, 1.0, np.abs(np.asarray(u, np.float64)))


def cape_point(u, v) -> np.ndarray:
    """Its top tucked inside the hood (the hood's lower back hangs over it in tatters: form.hood_drape)."""
    u, v = np.broadcast_arrays(np.asarray(u, np.float64), np.asarray(v, np.float64))
    th = cape_theta(u, v)
    z = CAPE_TOP + (cape_hem_z(u) - CAPE_TOP) * v ** 0.95
    tuck = -0.012 * smooth(0.16, 0.0, v)
    return shroud_point(th, z, tuck, fold_k=cape_fold_k(u) * smooth(0.05, 0.3, v))


CAPE_HOLES = [(-0.55, 0.78, 0.02), (-0.2, 0.86, 0.016), (0.12, 0.74, 0.022), (0.38, 0.84, 0.018), (0.7, 0.8, 0.016),
              (-0.8, 0.72, 0.014), (0.88, 0.7, 0.013), (-0.05, 0.62, 0.012), (0.55, 0.66, 0.013)]    # (u, v, radius m)

# ============================================================================ the middle cape (round 3)
# a second, shorter layer over the long cape at the back and sides, from under the hood's drape to an uneven torn hem
# (2-turnaround back view: the cloth falls in overlapping layers of uneven lengths, never in level tiers)
MID_TH = 104.0 * D2R
MID_TOP = 0.72
MID_TATTERS = [(-0.75, 0.08, 0.06), (-0.45, 0.06, 0.08), (-0.12, 0.07, 0.07), (0.18, 0.06, 0.09), (0.5, 0.08, 0.06),
               (0.8, 0.06, 0.07), (-0.3, 0.03, 0.04), (0.35, 0.03, 0.04)]
MID_HOLES = [(-0.4, 0.8, 0.016), (0.25, 0.86, 0.014), (0.62, 0.78, 0.012)]


def mid_hem_z(u) -> np.ndarray:
    u = np.asarray(u, np.float64)
    return 0.335 + 0.12 * np.abs(u) ** 1.4 + 0.035 * np.sin(2.3 * u + 0.6) - tatters(u, MID_TATTERS)


def mid_point(u, v) -> np.ndarray:
    u, v = np.broadcast_arrays(np.asarray(u, np.float64), np.asarray(v, np.float64))
    th = math.pi - u * MID_TH
    z = MID_TOP + (mid_hem_z(u) - MID_TOP) * v ** 0.95
    layer = 0.016 * smooth(0.12, 0.35, v) - 0.012 * smooth(0.14, 0.0, v)
    return shroud_point(th, z, layer, fold_k=(1.0 - smooth(0.82, 1.0, np.abs(u))) * smooth(0.05, 0.3, v))


# ============================================================================ the front panels
# each: the top edge's two ends (theta, z), the gather in the hand (theta range, z, radius), the hem's theta range and
# height, the layer (metres outside the shroud surface), its tatters (u in -1..1); the right ones mirror the left
PANELS = {
    'innerL': {'top': ((-14.0, 0.548), (18.0, 0.552)), 'gather': ((-2.0, 22.0), 0.5, 0.238), 'hem': ((-8.0, 46.0), 0.185),
               'layer': 0.032, 'tat': [(-0.75, 0.12, 0.06), (-0.2, 0.15, 0.085), (0.35, 0.1, 0.05), (0.8, 0.14, 0.07)]},
    'innerR': {'top': ((14.0, 0.548), (-18.0, 0.55)), 'gather': ((2.0, -22.0), 0.5, 0.238), 'hem': ((8.0, -46.0), 0.2),
               'layer': 0.021, 'tat': [(-0.6, 0.13, 0.07), (0.05, 0.12, 0.06), (0.55, 0.15, 0.085)]},
    'outerL': {'top': ((34.0, 0.57), (104.0, 0.69)), 'gather': ((16.0, 84.0), 0.48, 0.252), 'hem': ((18.0, 94.0), 0.24),
               'layer': 0.012, 'tat': [(-0.5, 0.12, 0.07), (0.15, 0.1, 0.05), (0.7, 0.14, 0.08)]},
    'outerR': {'top': ((-34.0, 0.57), (-104.0, 0.69)), 'gather': ((-16.0, -84.0), 0.48, 0.252), 'hem': ((-18.0, -94.0), 0.25),
               'layer': 0.012, 'tat': [(-0.65, 0.14, 0.08), (-0.05, 0.1, 0.05), (0.6, 0.12, 0.065)]},
}
PANEL_VG = 0.2                       # the gather's share of the way down a panel
PANEL_TOP_R = 0.12                   # its top row's radius: hidden inside the hood's chin and the core
PANEL_TUCK_UP = -0.03                # the top edge drops as it tucks in, behind the hands (polish: a level tuck high up
                                     # made a shelf under the face, a square 'arm' with a dark hole from the side)
PANEL_T = 0.007
PANEL_HOLES = {'innerL': [(0.1, 0.82, 0.014), (-0.55, 0.9, 0.011)], 'innerR': [(0.3, 0.85, 0.013)],
               'outerL': [(-0.2, 0.86, 0.014)], 'outerR': [(0.25, 0.84, 0.012), (-0.5, 0.92, 0.01)]}


def panel_point(name: str, u, v) -> np.ndarray:
    """A panel's middle surface: u -1..1 across, v 0 at the top edge, PANEL_VG at the gather, 1 at the hem."""
    sp = PANELS[name]
    u, v = np.broadcast_arrays(np.asarray(u, np.float64), np.asarray(v, np.float64))
    w = (u + 1.0) * 0.5
    (ta, za), (tb, zb) = sp['top']
    (ga, gb), zg, rg = sp['gather']
    (ha, hb), zh = sp['hem']
    th_top, z_top = (ta + (tb - ta) * w) * D2R, za + (zb - za) * w
    th_g = (ga + (gb - ga) * w) * D2R
    th_h = (ha + (hb - ha) * w) * D2R
    z_hem = np.maximum(zh - tatters(u, sp['tat'], 0.01), 0.088)
    up = v <= PANEL_VG
    a1 = smooth(0.0, 1.0, np.clip(v / PANEL_VG, 0, 1))
    a2 = np.clip((v - PANEL_VG) / (1.0 - PANEL_VG), 0, 1)
    th = np.where(up, th_top + (th_g - th_top) * a1, th_g + (th_h - th_g) * smooth(0.0, 1.0, a2) ** 0.8)
    z = np.where(up, z_top + (zg - z_top) * a1, zg + (z_hem - zg) * a2)
    edge = 1.0 - np.abs(u) ** 4
    fk = edge * smooth(0.02, 0.45, a2) * (~up)
    # above the hand, soft wrinkles bunch up into the grip (round 2: the tops read as a starched flat collar)
    a0 = np.clip(v / PANEL_VG, 0, 1)
    bunch = 0.006 * np.sin(np.pi * 4.0 * w + 0.6) * smooth(0.15, 0.85, a0) * up * edge
    base = shroud_point(th, z, sp['layer'] * smooth(0.0, 0.3, a2), fold_k=fk)
    r_here = np.hypot(base[..., 0], base[..., 1] - sh_abyc(z)[2])
    # toward the gather the cloth pulls in to the hand's radius
    pull = np.where(up, smooth(0.35, 1.0, np.clip(v / PANEL_VG, 0, 1)), smooth(0.35, 0.0, a2))
    r_t = r_here + (rg - r_here) * pull + bunch
    # its top edge is tucked away behind the chin and inside the hood (round 2: the top edges read as a starched collar)
    r_t = r_t + (PANEL_TOP_R - r_t) * smooth(0.09, 0.0, v)
    # polish: the tops start just above the hands (the void shows whole down to them) and tuck down and in behind them
    z = z + PANEL_TUCK_UP * smooth(0.09, 0.0, v)
    # every panel keeps a little of its layer all the way up, so the two inner ones never coincide where they cross
    r_t = r_t + 0.5 * sp['layer'] * (1.0 - smooth(0.0, 0.3, a2))
    k = r_t / np.maximum(r_here, 1e-9)
    yc = sh_abyc(z)[2]
    return np.stack([base[..., 0] * k, yc + (base[..., 1] - yc) * k, z], axis=-1)


# ============================================================================ the chains
WISP_TH = (25.0 * D2R, 70.0 * D2R, 115.0 * D2R, 160.0 * D2R)    # the left side; mirrored for the right
WISPS = [('wisp' + 'ABCD'[i], t0) for i, t0 in enumerate(WISP_TH)]


def hem_at(th) -> np.ndarray:
    """A smooth guess of the cloth's hem height round the body (the front panels 0.2, the sides 0.26, the back 0.18)."""
    a = np.abs(np.angle(np.exp(1j * np.asarray(th, np.float64))))
    return np.interp(a, [0.0, 0.5, 1.2, 2.2, math.pi], [0.19, 0.2, 0.26, 0.22, 0.175])


def wisp_chain(t0: float, s: int) -> list[tuple[float, float, float]]:
    """A wisp chain: inside the core, the hem, then hanging down and out to the wisps' ends (all hanging)."""
    th = s * t0
    zh = float(hem_at(th)) + 0.02
    root = F.core_point(np.array([th]), np.array([0.37]))[0]
    pts = [root, shroud_point(th, zh, 0.0, 0.0), shroud_point(th, zh - 0.065, 0.016, 0.0), shroud_point(th, max(zh - 0.125, 0.085), 0.032, 0.0)]
    return [tuple(map(float, q)) for q in pts]


def lash_chain(s: int) -> list[tuple[float, float, float]]:
    """Round 3: a thick front wisp's chain at the front hem, just in front of the inner panels' hem (the lash strike
    coils it back and whips it forward and up past the hands); it hangs down and out, then curls up."""
    th = s * 9.0 * D2R
    out = []
    for z, ex in ((0.205, 0.05), (0.14, 0.078), (0.1, 0.112), (0.12, 0.15)):
        out.append(tuple(map(float, shroud_point(th, z, ex, 0.0))))
    return out
