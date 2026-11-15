"""Zipwisp's colours and per-vertex paint (zipwisp_ultra.py paint_sources); the per-pixel bake materials are in
zipwisp_shade.py.

A ball of cyan static with a bright white core shining through (1-hero, 4-details 5): the body is painted a saturated
cyan a little under its CONTENT colour (ALBEDO_K) and glows in its own colour (a low floor, so no side goes grey and the
tone map never washes it to white); the flame licks' tips are lighter; the underside a touch deeper. The core is white
and glows hot: round the mouth on the front, a star on the back. The wings and the tail are cyan with a white glowing
rim; the sparks yellow and glowing.

Colours (CONTENT §2.2 #15): body #6EF2FF, core #FFFFFF, sparks #FFE14D, eyes #0E2A40. Prism Zipwisp (secrets.ts
`prism-zipwisp`, "rainbow sparks"; variants.ts): body #F5F2FF, core #FFFFFF, sparks #9B5CFF, eyes #2A2140; its picture
recolours the body pearly and lays rainbow sheens on the wings, the tail and a few sparks. Parts the palette has no
colour for are made from it (`colours`): the deeper cyan (the body toward the eyes' navy), the lighter tips and the
strands (the body toward the core), the rims (the core toward the body), the iris (the eyes' navy lifted 2.4x, its
lower half 3.3x: a clear blue), the mouth (the eyes' navy, its tongue lifted 1.8x); Prism's rainbow from the variant's
"rainbow sparks", softened into its pearl.
"""
from __future__ import annotations

import colorsys

import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import zipwisp_form as F
from monsters.breeds import zipwisp_props as PR

ALBEDO_K = 0.72                      # the lit body under the palette colour; the glow makes up the rest (review 2: more
                                     # self-lit, less shaded: energy, not frost)
FILM_SAT = 0.35                      # round 1: the film's tone map paled the cyan (#8AE6F2 measured for #6EF2FF), so the
                                     # paint is the palette colour pushed that much further from white (#3BEEFF)


def film(h: str, k: float = FILM_SAT) -> str:
    """The colour pushed further from white by k (each channel's distance to the brightest one grows): what the film
    renderer's tone map takes back. A near-white (Prism's pearl) barely changes."""
    r, g, b = C.srgb(h)
    m = max(r, g, b)
    return '#%02x%02x%02x' % tuple(int(round(255 * max(0.0, m - (m - c) * (1 + k)))) for c in (r, g, b))


def colours(pal: dict) -> dict:
    # review 1: the sparks too (a stronger glow would wash them toward white); Prism's violet barely changes
    body, core, spark, eye = film(pal['body']), pal['belly'], film(pal['accent']), pal['eye']
    prism = bool(pal.get('rainbow'))
    return {
        'body': body, 'core': core, 'spark': spark, 'eye': eye,
        'deep': C.mix_hex(body, spark, 0.3) if prism else C.mix_hex(body, eye, 0.1),   # review 2: the lower fur less dull
        'lavender': C.mix_hex(body, spark, 0.12),                 # Prism's pearl: a pearly neutral (review 2 grey, review 3 lilac)
        'bright': C.mix_hex(body, core, 0.5),                     # the tongues' tips (review 2: about #A8F6FF)
        'core_soft': C.mix_hex(core, body, 0.12),                 # the front core: palest cyan, not white (hit washed it)
        'strand': C.mix_hex(body, core, 0.78),          # the filaments, about #CFFAFF
        'rim': C.mix_hex(core, body, 0.1),
        'wing': C.mix_hex(body, core, 0.12),
        'wing_root': C.mix_hex(body, eye, 0.08) if not prism else C.mix_hex(body, spark, 0.15),
        'spark_hot': C.mix_hex(spark, core, 0.55),
        'sclera': C.mix_hex(core, body, 0.07),
        'iris': C.shade_hex(eye, 1.9),           # round 1: darker, so the eyes read at 64 px
        'iris_light': C.shade_hex(eye, 2.8),
        'iris_ring': eye,
        'pupil': C.shade_hex(eye, 0.6),
        'lid': eye,
        'mouth': C.shade_hex(eye, 0.7),                 # review 2: darker inside (the core's glow greyed it)
        'tongue': C.shade_hex(eye, 1.8),
        'fang': core,
    }


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def blend(rgb: np.ndarray, k, hexc) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0, 1)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    c = lin(hexc) if isinstance(hexc, str) else np.asarray(hexc, np.float64)
    c = c[None] if c.ndim == 1 else c
    return rgb * (1 - k[:, None]) + c * k[:, None]


def rainbow(t: np.ndarray, pearl: str, soft: float = 0.5) -> np.ndarray:
    """Pastel rainbow (linear RGB) along t 0..1 (blue, green, yellow, orange, pink), softened `soft` into the pearl."""
    t = np.clip(np.asarray(t, np.float64), 0, 1)
    hue = (0.62 - 0.72 * t) % 1.0
    rgb = np.array([colorsys.hsv_to_rgb(h, 0.62, 1.0) for h in hue])
    lin_rgb = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return lin_rgb * (1 - soft) + lin(pearl)[None] * soft


def core_k(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The white core shining through: (front, back) 0..1 by the angle from each core's direction."""
    f = np.exp(-(F.dir_angle(p, F.CORE_FRONT) / 23.0) ** 2)
    b = np.exp(-(F.dir_angle(p, F.CORE_BACK) / 19.0) ** 2)
    return f, b


def body_paint(p: np.ndarray, pal: dict) -> dict:
    """Per point of the body: 'paint' (linear RGB), 'rough' (1, roughness, coat), 'glow' (0..1)."""
    col = colours(pal)
    n = len(p)
    z = p[:, 2]
    out = F.outside(p)
    lick = smooth(0.004, 0.02, out)
    low = smooth(0.2, 0.07, z)
    cf, cb = core_k(p)
    tip = smooth(0.007, 0.024, out)                                  # the outer third of each tongue
    prism = bool(pal.get('rainbow'))
    d = p - v3(F.C0)
    under = smooth(0.15, -0.55, d[:, 2] / np.maximum(np.linalg.norm(d, axis=1), 1e-9))   # 1 on the underside
    rgb = np.tile(lin(col['body']), (n, 1))
    if prism:
        rgb = blend(rgb, 0.3 * (1 - tip), col['lavender'])
    rgb = blend(rgb, 0.3 * low * (1 - under), col['deep'])
    # the roots darker, the tips bright; review 3: the underside's tips brightest (the lower outline read dark teal),
    # the key-lit upper tips less (lit and glowing, their ridges overflowed into white streaks)
    rgb = blend(rgb, 0.3 * lick + tip * (0.38 + 0.4 * under), col['bright'])
    if prism:
        # a few rainbow glints on the small tongues' tips (variant-prism-zipwisp.png; the crown's flames and the curl took
        # a whole rainbow tip, a pink horn): review 2, a spread of cyan, yellow, orange and pink, not only mint
        pick = np.floor(((7.1 * p[:, 0] + 11.3 * p[:, 1] + 5.7 * p[:, 2]) * 3.0) % 4.0).astype(int)
        t = np.array([0.1, 0.63, 0.82, 0.97])[np.clip(pick, 0, 3)]
        glint = smooth(0.8, 0.97, np.sin(23 * p[:, 0] + 17 * p[:, 1] + 29 * p[:, 2])) * tip * smooth(0.04, 0.03, out)
        rgb = blend(rgb, 0.4 * glint, rainbow(t, col['body'], 0.5))             # review 3: fewer and softer
        # review 3: the crown's flames and the curl a soft pearly sheen, pink to cyan up their length (matte grey plaster)
        crest = smooth(0.03, 0.05, out) * smooth(0.42, 0.5, z)
        rgb = blend(rgb, 0.3 * crest, rainbow(np.clip((z - 0.45) / 0.15, 0, 1) * 0.85 + 0.1, col['body'], 0.55))
    rgb = blend(rgb, cf ** 0.8, col['core_soft'])
    rgb = blend(rgb, smooth(0.45, 0.85, cf), col['core'])                  # review 3: a white heart to the spot
    rgb = blend(rgb, cb ** 0.9, col['core'])
    rgb = rgb * ALBEDO_K
    # the glow: a floor in the body's own colour; round 1: higher (the shadow side read teal-grey) on a darker albedo.
    # Review 1: the tongues' tips glow brighter through their lighter paint (emissive = base x mask, so an even mask
    # lights the pale tips most: a thin cyan halo round the outline, never white; a per-tongue mask made the ORM map too
    # busy for the Lite copy's 1.5 MB); the front core, now round the mouth and up to the eyes, glows less hot than
    # before (clip_hit washed its front-left to white)
    # Review 2: a higher even floor on the darker albedo (more self-lit: the lit tips reach the bloom, a soft halo), the
    # core's share kept as it was at the face, and none round the eyes
    # review 3: the floor lower on top (the lit tips' ridges overflowed into white streaks) and higher underneath (the
    # lower outline glows cyan); the front core a stronger spot above the mouth (all smooth: the Lite copy's 1.5 MB)
    glow = 0.32 + 0.2 * under + 0.55 * cf ** 1.5 * eye_hole(p) + 0.85 * cb ** 1.2
    rough = np.full(n, 0.95)                                         # matte (review 1 and 2: streaks along the ridges)
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, np.zeros(n)], axis=1), 'glow': np.clip(glow, 0, 1)}


def prism_body_glow(p: np.ndarray) -> np.ndarray:
    """Prism's own glow (VARIANT_ORM): its pale pearl would bloom white at the base's floor, so the body barely glows;
    the core still burns."""
    cf, cb = core_k(p)
    d = p - v3(F.C0)
    under = smooth(0.15, -0.55, d[:, 2] / np.maximum(np.linalg.norm(d, axis=1), 1e-9))
    # review 2: Prism glows at strength 3 (its violet sparks need it to bloom), so its mask is a third of the base's
    return np.clip(0.07 + 0.06 * under + 0.3 * cf ** 1.5 * eye_hole(p) + 0.4 * cb ** 1.2, 0, 1)


def eye_hole(p: np.ndarray) -> np.ndarray:
    """0 round the eyes, 1 away from them: the core's glow stops before the eye whites (review 2)."""
    return smooth(0.045, 0.072, F.eye_dist(p))


def prop_paint(ob, pal: dict) -> dict:
    """The props per vertex: the wings and the tail cyan with a white rim (the wall and the band in from the edge) and
    a little deeper at the root; the sparks yellow. Prism: pearl with a pastel rainbow along each wing and the tail,
    violet sparks, five of them a rainbow glint."""
    col = colours(pal)
    prism = bool(pal.get('rainbow'))
    part = np.rint(S.attr_array(ob, 'part')).astype(int)
    ed = S.attr_array(ob, 'ed').astype(np.float64)
    su = S.attr_array(ob, 'su').astype(np.float64)
    n = len(part)
    rgb = np.tile(lin(col['wing']), (n, 1))
    rough = np.full(n, 0.5)
    coat = np.zeros(n)
    glow = np.zeros(n)
    slab = np.isin(part, (PR.WING, PR.TAIL))
    if slab.any():
        root = smooth(0.25, 0.0, su)
        c = np.tile(lin(col['wing']), (n, 1))
        if prism:
            c = rainbow(su, col['body'], 0.45)
        c = blend(c, 0.6 * root, col['wing_root'])
        rim = smooth(0.0042, 0.0016, ed)
        c = blend(c, rim, col['rim'])
        rgb[slab] = c[slab] * ALBEDO_K
        rough[slab] = 0.7
        glow[slab] = (0.3 + 0.62 * rim)[slab] if not prism else (0.05 + 0.25 * rim)[slab]
    sp = part == PR.SPARK
    if sp.any():
        sid = np.rint(S.attr_array(ob, 'spark_id')).astype(int)
        c = np.tile(lin(col['spark']), (n, 1))
        if prism:
            glint = np.isin(sid, (2, 7, 12, 17, 22))
            c[glint] = rainbow((sid[glint] % 5) / 4.0, col['spark'], 0.3)
        mid = np.sin(np.pi * np.clip(su, 0, 1))
        c = blend(c, (0.35 if prism else 0.15) * mid, col['spark_hot'])
        rgb[sp] = c[sp]
        rough[sp] = 0.6
        # review 1: a soft halo, the stroke still yellow; review 2: Prism's violet sparks glow too (strength 3)
        glow[sp] = (0.85 + 0.12 * mid[sp]) if not prism else (0.75 + 0.25 * mid[sp])
    return {'paint': rgb, 'rough': np.stack([np.ones(n), rough, coat], axis=1), 'glow': np.clip(glow, 0, 1)}
