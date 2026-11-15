"""Zipwisp's per-pixel bake materials (zipwisp_ultra.py): the fizzing static (strands swirling with the ball, white
specks, thin branching filaments), the back star, the face (the small open smile, the closed lids' lash lines under the
lenses), the glow pass, the eye lenses, and the wings' and the tail's lightning lines and rims.

The strands follow the swirl (zipwisp_form.swirl_coords): psi is computed per pixel from the object position, so the
lines run with the vortex round the front-to-back axis, densest round the back star. (Review 2: the painted yellow
bolts on the skin are gone: they peeked out between the tongues like buried sparks; the floating sparks carry it.)
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib import marks as MK
from lib.nodes import NB, new_mat
from monsters.breeds import zipwisp_form as F
from monsters.breeds import zipwisp_paint as WP

STRANDS = [(240, 0.94, 0.75), (120, 0.96, 0.95)]     # (lines round the axis: N * 0.6 whole, threshold, strength); review 2: thin


def _rgb(nb: NB, h: str):
    return nb.rgb(C.lin(h))


def swirl(nb: NB, pos):
    """(psi, sin(alpha)) per pixel: the strand coordinate (zipwisp_form.swirl_coords) and how far from the axis."""
    d = nb.vmath('SUBTRACT', pos, F.Q)
    dx, dy, dz = nb.sep(d)
    r = nb.math('MAXIMUM', nb.vmath('LENGTH', d), 1e-6)
    c = nb.math('MINIMUM', nb.math('MAXIMUM', nb.math('DIVIDE', dy, r), -0.9999), 0.9999)
    L = nb.math('MULTIPLY', 0.5, nb.math('LOGARITHM', nb.math('DIVIDE', nb.math('SUBTRACT', 1.0, c), nb.math('ADD', 1.0, c)), math.e))
    phi = nb.math('ARCTAN2', dz, dx)
    s, k = F.SPIRAL
    psi = nb.math('ADD', nb.math('MULTIPLY', L, k), nb.math('MULTIPLY', phi, F.SPIN * s))
    sa = nb.math('SQRT', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', c, c)))
    return psi, sa


def strands(nb: NB, pos):
    """The fizzing strands (4-details 5, 6): thin lines along the swirl, wavering, broken into lengths, fading where
    they crowd round the axis; and tiny white specks."""
    psi, sa = swirl(nb, pos)
    out = None
    for i, (n_lines, thr, k) in enumerate(STRANDS):
        warp = nb.math('MULTIPLY', nb.math('SUBTRACT', nb.noise(pos, 9.0 + 5 * i, 2.0, 0.5), 0.5), 0.09)
        wave = nb.math('SINE', nb.math('MULTIPLY', nb.math('ADD', psi, warp), float(n_lines)))
        line = MK._smooth(nb, wave, thr, 1.0)
        gate = MK._smooth(nb, nb.noise(pos, 9.0 + 5 * i, 0.5, 0.5), 0.47, 0.56)          # long, sparse runs
        m = nb.math('MULTIPLY', nb.math('MULTIPLY', line, gate), k)
        out = m if out is None else nb.math('MAXIMUM', out, m)
    fade = MK._smooth(nb, sa, 0.22, 0.45)
    out = nb.math('MULTIPLY', out, fade)
    speck = MK._smooth(nb, nb.noise(pos, 420.0, 0.5, 0.5), 0.75, 0.775)                    # review 2: sparse pinpoints
    return out, speck


def filaments(nb: NB, pos):
    """Review 1 (4-details 6): thin branching filaments wandering through the static (where two noise fields cross their
    middle), broken into lengths; the face gets these and the specks instead of the swirl's lines."""
    out = None
    # review 2: smooth noise (little detail) so the lines run long and branch rather than crackle into a mottle
    for k, sc in enumerate((16.0, 29.0)):
        n = nb.noise(nb.vmath('ADD', pos, (0.21 * k, 0.47 * k, 0.13 * k)), sc, 0.6, 0.5)
        ridge = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', n, 0.5)), 0.009 - 0.002 * k, 0.002)
        gate = MK._smooth(nb, nb.noise(pos, 7.0 + 5 * k, 0.5, 0.5), 0.46, 0.56)
        m = nb.math('MULTIPLY', ridge, gate)
        out = m if out is None else nb.math('MAXIMUM', out, m)
    return out


def back_star(nb: NB, pos):
    """The core's star on the back (2-turnaround back, 4-details 5): eight soft rays round a white heart."""
    c = F.surface_dir(F.CORE_BACK)
    n = Vector(F.normal_of(np.array([c[:]]))[0].tolist())
    rays = MK.star(nb, pos, tuple(c), tuple(n), (0.0, 0.0, 1.0), 0.06, inner=0.18, points=8, sharp=2.2, soft=0.3, depth=0.05)
    heart = MK.dot(nb, pos, tuple(c), 0.022, 0.5)
    return nb.math('MAXIMUM', rays, heart)


def _local(nb: NB, pos, c, xa, ya):
    d = nb.vmath('SUBTRACT', pos, tuple(c))
    return nb.vmath('DOT_PRODUCT', d, tuple(xa)), nb.vmath('DOT_PRODUCT', d, tuple(ya))


def face_marks(nb: NB, pos) -> dict:
    """The face on the skin (1-hero, 3-faces): the small open smile (a D, its top edge curving up at the corners, two
    tiny fangs, the tongue in its lower half) and, under each lens, the closed lid's lash line (a blink shows it)."""
    x, y, z = nb.sep(pos)
    front = MK._smooth(nb, y, -0.1, -0.14)
    # the mouth: top edge z0 + 0.006 a^2 (corners up), bottom a half ellipse
    a = nb.math('DIVIDE', x, F.MOUTH_W)
    a2 = nb.math('MULTIPLY', a, a)
    top = nb.math('ADD', F.MOUTH_Z, nb.math('MULTIPLY', 0.0055, a2))
    depth = nb.math('MULTIPLY', F.MOUTH_H, nb.math('SQRT', nb.math('MAXIMUM', nb.math('SUBTRACT', 1.0, a2), 0.0)))
    bot = nb.math('SUBTRACT', top, depth)
    below_top = MK._smooth(nb, z, nb.math('ADD', top, 0.0008), nb.math('SUBTRACT', top, 0.0008))
    above_bot = MK._smooth(nb, z, nb.math('SUBTRACT', bot, 0.0008), nb.math('ADD', bot, 0.0008))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', below_top, above_bot), front)
    # the tongue: a soft mound in the lower half
    tz = nb.math('DIVIDE', nb.math('SUBTRACT', z, nb.math('SUBTRACT', F.MOUTH_Z, F.MOUTH_H * 0.95)), F.MOUTH_H * 0.55)
    tr = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', x, F.MOUTH_W * 0.62), tz, 0.0))
    tongue = nb.math('MULTIPLY', MK._smooth(nb, tr, 1.0, 0.85), mouth)
    # one tiny fang hanging from the top edge (review 1: two matching ones read bat-like; 1-hero, 3-faces happy)
    fangs = None
    for s in (1,):
        fx = nb.math('DIVIDE', nb.math('SUBTRACT', x, s * F.MOUTH_W * 0.52), 0.0042)
        fy = nb.math('DIVIDE', nb.math('SUBTRACT', top, z), 0.0058)
        tri = nb.math('SUBTRACT', 1.0, nb.math('ADD', nb.math('ABSOLUTE', fx), fy))
        f = nb.math('MULTIPLY', MK._smooth(nb, tri, 0.0, 0.12), MK._smooth(nb, fy, -0.05, 0.05))
        fangs = f if fangs is None else nb.math('MAXIMUM', fangs, f)
    fangs = nb.math('MULTIPLY', fangs, mouth)
    lid = None
    for s in (1, -1):
        c, xa, ya, _lk = F.eye_frame(s)
        ex, ey = _local(nb, pos, c, xa / (F.EYE_R * F.EYE_SHAPE[0]), ya / (F.EYE_R * F.EYE_SHAPE[1]))
        # 3-faces blink: a gently curved line across the eye, its middle a little low
        xn = nb.math('DIVIDE', ex, 0.9)
        arc = nb.math('SUBTRACT', nb.math('MULTIPLY', 0.1, nb.math('MULTIPLY', xn, xn)), 0.18)
        band = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', ey, arc)), 0.095, 0.05)
        ln = nb.math('MULTIPLY', band, MK._smooth(nb, nb.math('ABSOLUTE', xn), 1.0, 0.9))
        lid = ln if lid is None else nb.math('MAXIMUM', lid, ln)
    lid = nb.math('MULTIPLY', lid, front)
    hx = nb.math('DIVIDE', x, F.MOUTH_W * 1.3)
    hz = nb.math('DIVIDE', nb.math('SUBTRACT', z, F.MOUTH_Z - F.MOUTH_H * 0.45), F.MOUTH_H * 1.05)
    halo = nb.math('MULTIPLY', MK._smooth(nb, nb.vmath('LENGTH', nb.comb(hx, hz, 0.0)), 1.45, 1.05), front)
    return {'mouth': mouth, 'tongue': tongue, 'fangs': fangs, 'lid': lid, 'halo': halo}


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the paint with, per pixel: the strands, filaments and specks, the back star, the face."""
    col = WP.colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    c = nb.attribute(attr).outputs['Color']
    st, speck = strands(nb, pos)
    # review 1: none of the swirl's regular lines on the face (they read as a fingerprint); filaments and specks instead
    face = MK._smooth(nb, nb.vmath('DOT_PRODUCT', nb.vmath('NORMALIZE', nb.vmath('SUBTRACT', pos, F.C0)), tuple(F.FACE_DIR)), 0.68, 0.82)
    calm = nb.math('SUBTRACT', 1.0, face)
    strand_c = _rgb(nb, col['strand'])
    if pal.get('rainbow'):
        # Prism: the strands catch a soft rainbow, its hue drifting with the swirl
        psi, _sa = swirl(nb, pos)
        hue = nb.math('FRACT', nb.math('ADD', nb.math('MULTIPLY', psi, 0.35), nb.math('MULTIPLY', nb.noise(pos, 3.0, 1.0, 0.5), 1.2)))
        stops = [(i / 6, tuple(WP.rainbow(np.array([i / 6]), col['strand'], 0.55)[0])) for i in range(7)]
        strand_c = nb.ramp(hue, stops)
    # round 1: lighten only (over the white core a plain mix drew them as darker lines, like a fingerprint)
    c = nb.mix(nb.math('MULTIPLY', st, calm), c, strand_c, blend='LIGHTEN')
    c = nb.mix(nb.math('MULTIPLY', filaments(nb, pos), 0.7), c, strand_c, blend='LIGHTEN')
    c = nb.mix(nb.math('MULTIPLY', speck, 0.8), c, _rgb(nb, col['core']), blend='LIGHTEN')
    star = back_star(nb, pos)
    c = nb.mix(nb.math('MULTIPLY', star, 0.9), c, _rgb(nb, col['core']))
    # review 2: no painted bolts on the skin any more (they peeked out between the tongues like buried sparks)
    fm = face_marks(nb, pos)
    c = nb.mix(fm['mouth'], c, _rgb(nb, col['mouth']))
    c = nb.mix(nb.math('MULTIPLY', fm['tongue'], 0.85), c, _rgb(nb, col['tongue']))
    c = nb.mix(fm['fangs'], c, _rgb(nb, col['fang']))
    c = nb.mix(fm['lid'], c, _rgb(nb, col['lid']))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def glow_material(name: str, marks, pal: dict | None = None) -> bpy.types.Material:
    """The glow pass: the paint's `glow` (Prism: `glow_prism`), the back star;
    none in the mouth or on the lash lines."""
    prism = bool(pal and pal.get('rainbow'))
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    g = nb.attribute('glow_prism' if prism else 'glow').outputs['Fac']
    # round 1: the strands and specks no longer glow (their fine detail in the ORM's alpha put the Lite copy over 1.5 MB);
    # they show in the colour
    g = nb.math('MAXIMUM', g, nb.math('MULTIPLY', back_star(nb, pos), 0.9 * (0.45 if prism else 1.0)))
    fm = face_marks(nb, pos)
    g = nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, nb.math('MINIMUM', nb.math('ADD', fm['mouth'], fm['lid']), 1.0)))
    # round 1: a soft dark ring round the mouth, so the core's bloom doesn't wash it out
    g = nb.math('MULTIPLY', g, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', fm['halo'], 0.6)))   # a thin, soft ring (a wide one read as a grey patch)
    g = nb.math('MINIMUM', nb.math('MAXIMUM', g, 0.0), 1.0)
    em = nb.new('ShaderNodeEmission')
    nb.link(nb.comb(g, g, g), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """A glossy eye (4-details 2, 1-hero): a white rim of sclera round a big blue iris (the eyes' navy lifted, lighter in
    its lower half, a navy ring), a large pupil, a big catchlight up toward the nose... and a small one low on the other
    side (the same side in both eyes), a dark lid line along the top."""
    col = WP.colours(pal or {'body': '#6EF2FF', 'belly': '#FFFFFF', 'accent': '#FFE14D', 'eye': '#0E2A40'})
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.14, 0.5))          # glossy, a coat
        nb.output(em.outputs[0])
        return m
    x, y, _z = nb.sep(nb.attribute('eyeuv').outputs['Vector'])
    side = nb.attribute('eye_side').outputs['Fac']
    # review 1: a big iris set a little up and toward the nose, so the white shows mostly below and outside it (not a
    # ring all round), and a heavy lid line along the top fading to nothing below (4-details 2)
    cx = nb.math('MULTIPLY', side, -0.05)                       # a little toward the nose
    ix, iy = nb.math('SUBTRACT', x, cx), nb.math('SUBTRACT', y, 0.15)
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), 0.88)    # review 2: bigger and higher, white only below
    r = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    low = MK._smooth(nb, nb.math('DIVIDE', iy, 0.7), -0.12, -0.78)
    iris = nb.mix(low, _rgb(nb, col['iris']), _rgb(nb, col['iris_light']))
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 26.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', MK._smooth(nb, ri, 0.5, 0.6), MK._smooth(nb, ri, 0.92, 0.8)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.14), iris, _rgb(nb, col['iris_ring']))
    c = nb.mix(MK._smooth(nb, ri, 0.55, 0.51), iris, _rgb(nb, col['pupil']))                 # the pupil
    c = nb.mix(MK._smooth(nb, ri, 0.86, 0.95), c, _rgb(nb, col['iris_ring']))                # the iris's ring
    c = nb.mix(MK._smooth(nb, ri, 1.0, 1.04), c, _rgb(nb, col['sclera']))                    # the white round it
    # the lid line: heavy along the top, thinning down the sides, gone below
    r_in = nb.math('SUBTRACT', 0.97, nb.math('MULTIPLY', MK._smooth(nb, y, -0.2, 0.7), 0.24))
    lidm = nb.math('MULTIPLY', MK._smooth(nb, r, r_in, nb.math('ADD', r_in, 0.025)), MK._smooth(nb, y, -0.45, 0.05))
    c = nb.mix(lidm, c, _rgb(nb, col['lid']))
    big = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, 0.2), nb.math('SUBTRACT', iy, 0.26), 0.0)), 0.16, 0.13)
    small = MK._smooth(nb, nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, 0.24), nb.math('ADD', iy, 0.24), 0.0)), 0.075, 0.055)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """The props per pixel: static veins over the wings and the tail (fine light lines wandering through the cyan,
    4-details 3, 4), the white rim crisp from the edge distance; the sparks as painted."""
    col = WP.colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    c = nb.attribute(attr).outputs['Color']
    part = nb.attribute('part').outputs['Fac']
    ed = nb.attribute('ed').outputs['Fac']
    slab = nb.math('LESS_THAN', part, 2.5)
    veins = None
    # review 2: fine crackling lightning lines (4-details 3), not a mottle like pool water: smooth noise, thin ridges
    for k, sc in enumerate((14.0, 26.0)):
        n = nb.noise(nb.vmath('ADD', pos, (0.31 * k, 0.17 * k, 0.53 * k)), sc, 0.8, 0.5)
        v = MK._smooth(nb, nb.math('ABSOLUTE', nb.math('SUBTRACT', n, 0.5)), 0.012 - 0.003 * k, 0.003)
        veins = v if veins is None else nb.math('MAXIMUM', veins, v)
    inner = MK._smooth(nb, ed, 0.004, 0.007)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', veins, inner), nb.math('MULTIPLY', slab, 0.6)), c, _rgb(nb, col['strand']))
    rim = nb.math('MULTIPLY', MK._smooth(nb, ed, 0.0036, 0.0022), slab)
    c = nb.mix(rim, c, _rgb(nb, col['rim']))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
