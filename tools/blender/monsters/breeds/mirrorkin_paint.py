"""Mirrorkin's colours and per-vertex paint (mirrorkin_ultra.paint_sources).

Colours come from CONTENT (glass #CFD8E3, highlights #EEF3F8, cloak #6C5CE7, frame #C9A04A, eyes #2B2B33), the card's
glove white #F3F1EC (a part CONTENT has no colour for) and, for Obsidian, src/art/monster/variants.ts (glass #141418,
highlights #2C2C34, the frame and the cloak #7A7A88, the face #E0E0EA). Every other tone is mixed from those:
- the gold's light and shadow from the frame colour (no metalness in the game: the polish is painted, the ridges light,
  the hollows deep amber, from the mesh's own curvature, so it reads the same from every side);
- the gems from the cloak violet darkened toward the eye colour (Obsidian: toward its silver, its picture's lavender-grey
  stones); the eye shadow, the blush and the nose are the violet mixed toward the highlights and the glove white
  (lavender; the pictures' soft pink has no palette colour).
Glass: the base colour, a lighter cool rim inside the frame's lip, soft diagonal reflection streaks and a highlight,
calm round the face (the face itself is per-pixel in mirrorkin_shade.py).
"""
from __future__ import annotations

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth
from monsters.breeds import mirrorkin_cloak as CL
from monsters.breeds import mirrorkin_form as F
from monsters.breeds import mirrorkin_ornament as OR

BASE_VIOLET = '#6C5CE7'
BASE_INK = '#2B2B33'
GLOVE = '#F3F1EC'


def colours(pal: dict) -> dict:
    obs = bool(pal.get('obsidian'))
    glass, hi = pal['body'], pal['belly']
    frame = pal.get('frame', '#C9A04A')
    cloak = pal['accent']
    # review round 2: deep violet stones (about #5A3FC8: the cloak violet richer and deeper; pale periwinkle vanished
    # into the cloak), Obsidian's toward its silver
    deep_violet = rich(BASE_VIOLET, 1.3, 0.83, hue=-14.0)       # polish: a redder amethyst
    gem = C.mix_hex(deep_violet, frame, 0.4) if obs else deep_violet
    col = {
        'glass': glass, 'glass_hi': hi,
        'glass_deep': C.mix_hex(C.shade_hex(glass, 0.8, 0.02), BASE_VIOLET, 0.08) if not obs else C.mix_hex(glass, '#000000', 0.25),
        # review round 1: the gold back at the frame colour (it rendered #D09B2A, too saturated), bronze hollows and
        # crisp pale-gold ridges; Obsidian's frame a lighter silver than its cloak (about #A8A8B6 lit)
        # review round 2: dark bronze hollows (about #6B4A1A), crisp pale-gold ridges (about #F2DC9A), the mid at the
        # frame colour; Obsidian's silver with near-white ridges and dark hollows (it read as matte clay)
        'gold': frame if obs else rich(frame, 1.08, 0.97),
        'gold_hi': C.mix_hex(frame, '#F7F7FB', 0.9) if obs else C.mix_hex(frame, '#FFF0B8', 0.75),
        'gold_lo': C.shade_hex(frame, 0.42) if obs else C.mix_hex(C.shade_hex(frame, 0.5), '#4A2A00', 0.28),
        'gold_deep': C.shade_hex(frame, 0.24) if obs else C.mix_hex(C.shade_hex(frame, 0.3), '#2E1800', 0.32),
        'bevel_dark': C.shade_hex(glass, 0.86, 0.03),
        'pane': C.mix_hex(hi, frame, 0.38) if obs else hi,
        'cloak': cloak, 'cloak_hi': C.mix_hex(cloak, hi if not obs else '#EEF3F8', 0.45 if obs else 0.32),
        'cloak_lo': C.shade_hex(cloak, 0.62), 'lining': C.shade_hex(cloak, 0.8),
        'gem': gem, 'gem_hi': C.mix_hex(gem, '#EEF3F8', 0.55), 'gem_lo': C.shade_hex(gem, 0.48),
        'glove': GLOVE, 'glove_lo': C.mix_hex(GLOVE, BASE_INK, 0.14), 'stitch': C.mix_hex(GLOVE, BASE_INK, 0.28),
        'iris': C.mix_hex(BASE_INK, BASE_VIOLET, 0.16), 'iris_lo': C.mix_hex(BASE_VIOLET, '#EEF3F8', 0.2),
        'pupil': C.shade_hex(BASE_INK, 0.5), 'sclera': C.mix_hex('#EEF3F8', '#FFFFFF', 0.55),
        'lash': BASE_INK, 'brow': C.mix_hex(BASE_INK, BASE_VIOLET, 0.25),
        'lid': C.mix_hex(BASE_VIOLET, '#EEF3F8', 0.6), 'mouth': C.mix_hex(BASE_INK, BASE_VIOLET, 0.32),
        'nose': C.mix_hex(BASE_VIOLET, GLOVE, 0.7), 'blush': C.mix_hex(BASE_VIOLET, GLOVE, 0.58), 'sparkle': '#EEF3F8',
    }
    if obs:
        face = pal['eye']
        col.update({'brow': face, 'mouth': face, 'lid': C.mix_hex(face, frame, 0.3), 'nose': C.mix_hex(face, glass, 0.35),
                    'blush': C.mix_hex(face, glass, 0.45), 'sparkle': face, 'lash': '#141418',
                    'sclera': face})                  # polish: its pale eye whites carry the glow with the smile
    return col


def rich(h: str, sat: float, val: float, hue: float = 0.0) -> str:
    """The colour with its saturation and value scaled (HSV), kept in gamut: the gold's mid, light and shadow tones
    are the frame colour richer or deeper (the game has no metalness, so the polish is painted)."""
    import colorsys
    r, g, b = C.srgb(h)
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb((hh + hue / 360.0) % 1.0, min(1.0, ss * sat), min(1.0, vv * val))
    return '#%02x%02x%02x' % tuple(int(round(255 * c)) for c in (r, g, b))


def lin(h: str) -> np.ndarray:
    return S.v3(C.lin_rgb(h))


def blend(rgb: np.ndarray, k, hexc: str) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0, 1)
    k = k[:, None] if k.ndim == 1 else k
    return rgb * (1 - k) + lin(hexc)[None] * k


# ----------------------------------------------------------------------------- curvature
def cavity(ob: bpy.types.Object, scale: float, iters: int = 2) -> np.ndarray:
    """Per vertex: the mesh's curvature along its normal (+1 convex ridges .. -1 hollows), from the neighbours' mean
    (an umbrella Laplacian), smoothed `iters` times, normalised by `scale` metres of bulge."""
    me = ob.data
    n = len(me.vertices)
    co, vn = S.mesh_arrays(ob)
    e = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get('vertices', e)
    e = e.reshape(-1, 2)
    cnt = np.bincount(e.ravel(), minlength=n).astype(np.float64)
    acc = np.zeros((n, 3))
    np.add.at(acc, e[:, 0], co[e[:, 1]])
    np.add.at(acc, e[:, 1], co[e[:, 0]])
    lap = acc / np.maximum(cnt, 1)[:, None] - co
    c = -(lap * vn).sum(1)                    # convex: the neighbours' mean lies behind the surface
    for _ in range(iters):
        a = np.zeros(n)
        np.add.at(a, e[:, 0], c[e[:, 1]])
        np.add.at(a, e[:, 1], c[e[:, 0]])
        c = 0.5 * c + 0.5 * a / np.maximum(cnt, 1)
    return np.tanh(c / scale)


def metal(rgb_shape: int, col: dict, cav: np.ndarray, up: np.ndarray, extra=None) -> np.ndarray:
    """Polished gold (or silver) by curvature and facing up: ridges catch a pale highlight, hollows go deep amber."""
    b = 0.5 + 0.6 * cav + 0.12 * up
    if extra is not None:
        b = b + extra
    b = np.clip(b, 0, 1)
    rgb = np.tile(lin(col['gold']), (rgb_shape, 1))
    rgb = blend(rgb, 0.95 * smooth(0.44, 0.16, b), col['gold_lo'])
    rgb = blend(rgb, 0.85 * smooth(0.18, 0.02, b), col['gold_deep'])
    rgb = blend(rgb, 0.95 * smooth(0.7, 0.8, b), col['gold_hi'])
    return rgb


def polish(co: np.ndarray) -> np.ndarray:
    """A broad painted reflection over the gold (-0.2 .. +0.25): a soft light band slanting across the mirror and
    its back, a darker band beside it, so the big smooth fields read polished instead of flat mustard."""
    w = co[:, 0] * 0.42 + (co[:, 2] - F.ZC) * 0.9
    # review round 2: no darker band (it greyed the back plate)
    return 0.2 * np.exp(-((w - 0.12) / 0.06) ** 2) + 0.1 * np.exp(-((w + 0.2) / 0.05) ** 2)


# ----------------------------------------------------------------------------- the body
def glass_paint(co: np.ndarray, col: dict) -> tuple[np.ndarray, np.ndarray]:
    """The mirror glass (1-hero, 2-turnaround): cool and a little deeper toward the bottom and just inside the rim, a
    bright cool rim against the lip, the soft light panes of a window reflected low on its right and in a slanting
    band on its left, a soft highlight high up; calm round the face. Returns (colour, sheen 0..1)."""
    x, z = co[:, 0], co[:, 2]
    rho = F.glass_rho(x, z)
    zn = (z - F.ZC) / F.GB
    rgb = np.tile(lin(col['glass']), (len(co), 1))
    # review round 1: the lower half lighter (it read about #A2ABBC; the pictures' glass stays pale all over)
    rgb = blend(rgb, 0.22 * smooth(0.25, -0.9, zn) * smooth(0.1, 0.6, rho), col['glass_deep'])
    rgb = blend(rgb, 0.25 * smooth(0.68, 0.9, rho) * smooth(1.0, 0.93, rho), col['glass_deep'])
    rim = smooth(0.9, 0.975, rho)
    rgb = blend(rgb, 0.9 * rim, col['glass_hi'])
    face = smooth(2.5, 1.5, F.eye_dist(co)) + np.exp(-((x / 0.1) ** 2 + ((z - F.MOUTH_Z) / 0.045) ** 2))
    calm = 1.0 - np.clip(face, 0, 1)
    # review round 1: the soft bars read as chin folds; the window panes are crisp and per pixel now
    # (mirrorkin_shade.panes), and so is the thin bright rim
    return rgb, np.clip(0.85 * rim, 0, 1) * calm


def body_paint(co: np.ndarray, vn: np.ndarray, pal: dict, cav: np.ndarray | None = None) -> dict:
    col = colours(pal)
    n = len(co)
    z = F.zones(co)
    glove = z['glove']
    # the glass by vertex only well inside the lip: the boundary is drawn per pixel (a ragged pale seam ran along it)
    glass = z['glass'] & (F.glass_rho(co[:, 0], co[:, 2]) < 0.97)
    if cav is None:
        cav = np.zeros(n)
    rgb = metal(n, col, cav, vn[:, 2], polish(co))
    # the back's broad dome a touch lighter in its middle (4-details 6: the polished field inside the engraved border)
    back = (co[:, 1] > 0.035) & ~glove & ~z['handle']
    # the back plate at the frame's gold, a touch lighter in its polished field (review round 2: it read grey)
    rgb = blend(rgb, 0.18 * back * smooth(0.8, 0.2, F.glass_rho(co[:, 0], co[:, 2])), col['gold_hi'])
    phi, dd = F.ring_offset(co[:, 0], co[:, 2])
    lip = (dd / F.band_k(phi) < 0.0048) & (F.glass_rho(co[:, 0], co[:, 2]) >= 0.97) & (co[:, 1] < -0.018) & ~glove
    rgb = np.where(lip[:, None], blend(np.tile(lin(col['gold_lo']), (n, 1)), 0.5, col['gold_deep']), rgb)
    g_rgb, g_sheen = glass_paint(co, col)
    rgb = np.where(glass[:, None], g_rgb, rgb)
    gl = np.tile(lin(col['glove']), (n, 1))
    gl = blend(gl, 0.6 * smooth(0.0, -0.6, cav), col['glove_lo'])
    rgb = np.where(glove[:, None], gl, rgb)
    rough = np.full(n, 0.3)
    coat = np.full(n, 0.5)
    rough = np.where(glass, 0.32, rough)
    coat = np.where(glass, 0.36, coat)
    rough = np.where(glove, 0.88, rough)
    coat = np.where(glove, 0.0, coat)
    # glow: a faint lift on the glass's sheen and the gold's highlights, so they read bright in the grey studio
    # review round 2: no glow on the gold (its highlights come from paint and specular); the glass's glow only lifts
    # its lower half a little (the bottom read as a grey chin, the top already at the highlight colour)
    zn = (co[:, 2] - F.ZC) / F.GB
    glow = np.where(glass, 0.04 + 0.18 * smooth(-0.1, -0.8, zn) + 0.3 * g_sheen, 0.0)
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, coat], axis=1), 'glow': np.clip(glow, 0, 1),
            'glass': glass, 'glove': glove}


# ----------------------------------------------------------------------------- the props
def prop_paint(ob: bpy.types.Object, pal: dict, cav: np.ndarray) -> dict:
    col = colours(pal)
    part = np.rint(S.attr_array(ob, 'part')).astype(int)
    side = S.attr_array(ob, 'side').astype(np.float64)
    ed = S.attr_array(ob, 'ed').astype(np.float64)
    fk = S.attr_array(ob, 'fk').astype(np.float64)
    pa = S.attr_array(ob, 'pa').astype(np.float64)
    co, vn = S.mesh_arrays(ob)
    n = len(part)
    rgb = metal(n, col, cav, vn[:, 2])
    rough = np.full(n, 0.3)
    coat = np.full(n, 0.5)
    glow = np.zeros(n)
    gem = part >= OR.GEM
    if gem.any():
        # facets: the table bright, the crown's facets alternating light and dark round the stone, the pavilion deep
        # review round 2: deep violet facets alternating a little, the table a touch lighter, one white glint facet
        facet = (np.floor(pa * 16.0 + 0.5) % 2)
        g = np.tile(lin(col['gem']), (n, 1))
        g = blend(g, np.where(fk > 0.9, 0.22, 0.0), col['gem_hi'])
        g = blend(g, np.where((fk > -0.1) & (fk < 0.9), 0.06 + 0.16 * facet, 0.0), col['gem_hi'])
        glint = (fk > -0.1) & (fk < 0.9) & (np.abs(pa - 0.125) < 0.035)
        g = blend(g, np.where(glint, 0.92, 0.0), '#F4F6FB')
        g = blend(g, np.where(fk < -0.1, 0.5, 0.0), col['gem_lo'])
        rgb[gem] = g[gem]
        rough[gem] = 0.3
        coat[gem] = 0.5
        glow[gem] = np.where(glint[gem], 0.35, 0.0)
    cloth = (part == CL.MANTLE) | (part == CL.PANEL)
    if cloth.any():
        fd = S.attr_array(ob, 'fd').astype(np.float64)
        c = np.tile(lin(col['cloak']), (n, 1))
        c = blend(c, 0.3 * smooth(0.05, 0.7, cav), col['cloak_hi'])
        c = blend(c, 0.45 * smooth(-0.05, -0.7, cav), col['cloak_lo'])
        # review round 1: a satin sheen along the folds' crests, the hollows deeper
        c = blend(c, 0.4 * smooth(-0.2, -0.9, fd), col['cloak_lo'])
        c = blend(c, 0.85 * smooth(0.74, 0.95, fd), col['cloak_hi'])
        c = np.where((side < -0.5)[:, None], blend(c, 0.55, col['lining']), c)
        trim = ((part == CL.PANEL) | (part == CL.MANTLE)) & (ed < 0.0075) & (side > -2)
        c = np.where(trim[:, None], metal(n, col, cav * 0.6, vn[:, 2], 0.1), c)
        rgb[cloth] = c[cloth]
        rough[cloth] = np.where(trim[cloth], 0.38, 0.46)
        coat[cloth] = np.where(trim[cloth], 0.3, 0.22)
        glow[cloth] = 0.0
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, coat], axis=1), 'glow': np.clip(glow, 0, 1)}


def preview_colour(name: str, pal: dict) -> str:
    col = colours(pal)
    return {'mantle': col['cloak'], 'panels': col['cloak'], 'gems': col['gem']}.get(name, col['gold'])
