"""Ashwraith's per-pixel bake materials (ashwraith_ultra.py; round 2 of the review): the cloth's coarse, uneven weave
(it read as a fine canvas grid), the embers drifting in the dark (the face's void, the core seen through the tears,
the outer folds by the hems, along the wisps), the closed lids' faint arcs under the eye patches; the glow pass; the
props (the weave on the cloth's outside, the lantern's flame on its glass); the ember crescent on the eye patches.
The holes are real cuts in the cloth (ashwraith_mesh.Kit.ragged), so nothing paints holes any more.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import marks as MK
from lib import surface as S
from lib.nodes import NB, new_mat
from monsters.breeds import ashwraith_body as B
from monsters.breeds import ashwraith_drape as D
from monsters.breeds import ashwraith_form as F
from monsters.breeds import ashwraith_paint as WP
from monsters.breeds import ashwraith_props as PR

WEAVE = 0.0048                       # the weave's thread spacing (metres; polish: about 4.6x finer, low contrast)


def _rgb(nb: NB, h: str):
    return nb.rgb(C.lin_rgb(h))


def embers(nb: NB, pos, spots):
    """0..1 over the embers (tiny soft dots); and their hot cores."""
    if not spots:
        return None, None
    m = MK.union(nb, [MK.dot(nb, pos, tuple(c), float(r), 0.35) for c, r in spots])
    core = MK.union(nb, [MK.dot(nb, pos, tuple(c), float(r) * 0.45, 0.4) for c, r in spots[: len(spots) // 4]])
    return m, core


def weave(nb: NB, pos):
    """A fine, low-contrast burlap weave (polish: the round-3 one read as big tiles, cobblestones or croc skin): a plain
    weave of wavering threads, each its own tone and slubbed along its length, broken by value noise. Across, the
    threads follow the arc length round the shroud's oval (an angle alone stretched the cells into tall rectangles on
    the narrower back), mirrored left and right so there is no seam. A brightness factor near 1."""
    x, y, z = nb.sep(pos)
    wob = nb.math('SUBTRACT', nb.noise(pos, 6.0, 2.0, 0.5), 0.5)
    wob2 = nb.math('SUBTRACT', nb.noise(pos, 17.0, 1.0, 0.5), 0.5)
    ang = nb.math('ABSOLUTE', nb.math('ARCTAN2', x, nb.math('SUBTRACT', 0.03, y)))
    # the oval's half-width a and half-depth b (rounder up in the hood): arc length ~ (a+b)/2 ang - (a-b)/4 sin(2 ang)
    tb = nb.math('MINIMUM', nb.math('MAXIMUM', nb.math('DIVIDE', nb.math('SUBTRACT', z, 0.6), 0.12), 0.0), 1.0)
    b = nb.math('ADD', 0.19, nb.math('MULTIPLY', tb, 0.06))
    a = 0.26
    arc = nb.math('SUBTRACT', nb.math('MULTIPLY', ang, nb.math('MULTIPLY', nb.math('ADD', b, a), 0.5)),
                  nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 2.0)), nb.math('MULTIPLY', nb.math('SUBTRACT', a, b), 0.25)))
    u = nb.math('DIVIDE', nb.math('ADD', arc, nb.math('ADD', nb.math('MULTIPLY', wob, 0.05), nb.math('MULTIPLY', wob2, 0.011))), WEAVE)
    v = nb.math('DIVIDE', nb.math('ADD', z, nb.math('ADD', nb.math('MULTIPLY', wob, -0.044), nb.math('MULTIPLY', wob2, 0.01))), WEAVE)

    def threads(t):
        d = nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', t), 0.5))
        return MK._smooth(nb, d, 0.46, 0.26)

    def dip(t):
        d = nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('FRACT', t), 0.5)), 2.0)
        return nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', nb.math('MULTIPLY', d, d), 0.4))
    fu, fv = nb.math('FLOOR', u), nb.math('FLOOR', v)
    # each thread its own tone, slubbed (thicker, lighter stretches) along its length
    tone_u = nb.math('ADD', 0.75, nb.math('MULTIPLY', nb.noise(nb.comb(fu, nb.math('MULTIPLY', v, 0.07), 0.0), 1.3, 1.0, 0.5), 0.5))
    tone_v = nb.math('ADD', 0.75, nb.math('MULTIPLY', nb.noise(nb.comb(nb.math('MULTIPLY', u, 0.07), fv, 3.7), 1.3, 1.0, 0.5), 0.5))
    tu = nb.math('MULTIPLY', nb.math('MULTIPLY', threads(u), dip(v)), tone_u)
    tv = nb.math('MULTIPLY', nb.math('MULTIPLY', threads(v), dip(u)), tone_v)
    par = nb.math('GREATER_THAN', nb.math('FRACT', nb.math('MULTIPLY', nb.math('ADD', fu, fv), 0.5)), 0.25)
    w = nb.mix(par, tu, tv, dtype='FLOAT')
    mott = nb.math('SUBTRACT', nb.noise(pos, 9.0, 3.0, 0.55), 0.5)
    grime = nb.math('SUBTRACT', nb.noise(pos, 2.8, 2.0, 0.5), 0.5)
    k = nb.math('MULTIPLY', nb.math('SUBTRACT', w, 0.62), 0.075)
    k = nb.math('ADD', k, nb.math('ADD', nb.math('MULTIPLY', mott, 0.1), nb.math('MULTIPLY', grime, 0.12)))
    return nb.math('ADD', 1.0, k)


def lid_lines(nb: NB, pos):
    """The closed lids: a thin ember arc on the face along each crescent's spine (a blink sinks the patch onto it)."""
    segs = []
    phi = np.linspace(-F.CRES_PHI * 0.9, F.CRES_PHI * 0.9, 8)
    sp = F.cres_spine(phi)
    for s in (1, -1):
        c, xa, ya, _lk = F.eye_frame(s)
        pts = [tuple(F.face_point(np.array([(c + xa * float(q[0]) + ya * float(q[1]))[:]]))[0]) for q in sp]
        segs += [MK.line(nb, pos, a_, b_, 0.0018, 0.35) for a_, b_ in zip(pts[:-1], pts[1:])]
    return MK.union(nb, segs)


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    col = WP.colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    c = nb.attribute(attr).outputs['Color']
    inner = nb.attribute('inner').outputs['Fac']
    kk = nb.mix(nb.math('SUBTRACT', 1.0, inner), 1.0, weave(nb, pos), dtype='FLOAT')
    c = nb.mix(1.0, c, nb.comb(kk, kk, kk), blend='MULTIPLY')
    e, core = embers(nb, pos, (marks or {}).get('embers', []))
    if e is not None:
        c = nb.mix(e, c, _rgb(nb, col['ember']))
        c = nb.mix(nb.math('MULTIPLY', core, 0.8), c, _rgb(nb, col['ember_hot']))
    c = nb.mix(nb.math('MULTIPLY', lid_lines(nb, pos), 0.7), c, _rgb(nb, col['eye_deep']))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def glow_material(name: str, marks, pal: dict | None = None) -> bpy.types.Material:
    """The glow pass: the paint's `glow` (the core's warm light, the eyes' halo), the embers, the closed lids' arcs."""
    def fn(nb: NB, pos):
        parts = [nb.math('MULTIPLY', lid_lines(nb, pos), 0.3)]
        e, _core = embers(nb, pos, (marks or {}).get('embers', []))
        if e is not None:
            parts.append(e)
        return MK.union(nb, parts)
    return MK.glow_material(name, fn)


# ----------------------------------------------------------------------------- marks
def make_marks(hi_body) -> dict:
    """The embers on the body: sparks over the face's void (more toward its lower half) and over the core's lower
    half, seen through the tears and under the hems (deterministic)."""
    co, _vn = S.mesh_arrays(hi_body)
    zz = B.zones(co)
    rng = np.random.default_rng(1415)
    out = []

    def pick(mask, n, r0, r1, weight=None):
        idx = np.nonzero(mask)[0]
        if not len(idx):
            return
        p = None if weight is None else weight[idx] / weight[idx].sum()
        for i in rng.choice(idx, size=min(n, len(idx)), replace=False, p=p):
            out.append((tuple(map(float, co[i])), float(rng.uniform(r0, r1))))
    far = zz['eye_d'] > 0.07
    pick(zz['face'] & far, 22, 0.0018, 0.0034, weight=1.0 + 2.0 * (co[:, 2] < 0.7))
    pick(zz['core'] & (co[:, 2] < 0.5), 80, 0.0028, 0.0055)
    return {'embers': [[list(c), r] for c, r in out]}


_PM: dict = {}


def prop_marks() -> dict:
    """Embers on the cloth's outer folds near the hems (in the valleys) and along the wisps (deterministic)."""
    if _PM:
        return _PM
    rng = np.random.default_rng(77)
    em = []
    tries = 0
    while len(em) < 96 and tries < 5000:           # polish: more hem embers (with the painted specks, about twice)
        tries += 1
        u, v = rng.uniform(-0.95, 0.95), rng.uniform(0.62, 0.98)
        if rng.uniform() < 0.6:
            q = D.cape_point(np.array([u]), np.array([v]))[0]
        else:
            q = D.panel_point(('innerL', 'innerR', 'outerL', 'outerR')[int(rng.integers(4))], np.array([u]), np.array([v]))[0]
        _a, _b, yc = D.sh_abyc(q[2])
        th = math.atan2(q[0], -(q[1] - yc))
        if D.folds(th, q[2]) > 0.0 and rng.uniform() < 0.7:
            continue                                     # mostly in the valleys
        em.append([list(map(float, q)), float(rng.uniform(0.004, 0.0065))])
    from monsters.breeds import ashwraith_wisps as WS
    for r in WS.strand_paths():
        for t in rng.uniform(0.08, 0.6, 1 if r['part'] == WS.WISP else 2):     # (the SVM stack holds about 200 dots)
            q = r['P'][int(t * (len(r['P']) - 1))]
            em.append([list(map(float, q)), float(rng.uniform(0.0035, 0.005))])
    _PM['embers'] = em
    return _PM


def prop_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    col = WP.colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    c = nb.attribute(attr).outputs['Color']
    part = nb.attribute('part').outputs['Fac']
    pt = nb.attribute('pt').outputs['Fac']
    pa = nb.attribute('pa').outputs['Fac']
    side = nb.attribute('side').outputs['Fac']

    def is_part(*ids):
        o = None
        for i in ids:
            e = nb.math('COMPARE', part, float(i), 0.4)
            o = e if o is None else nb.math('MAXIMUM', o, e)
        return o
    cloth = is_part(PR.CAPE, PR.PANEL, PR.TIP)
    outer = nb.math('MULTIPLY', cloth, nb.math('GREATER_THAN', side, 0.5))
    tipk = is_part(PR.TIP)
    kk = nb.mix(nb.math('MAXIMUM', outer, tipk), 1.0, weave(nb, pos), dtype='FLOAT')
    c = nb.mix(1.0, c, nb.comb(kk, kk, kk), blend='MULTIPLY')
    e, core = embers(nb, pos, prop_marks()['embers'])
    if e is not None:
        c = nb.mix(e, c, _rgb(nb, col['ember']))
        c = nb.mix(nb.math('MULTIPLY', core, 0.8), c, _rgb(nb, col['ember_hot']))
    # the lantern's glass (round 3): dark iron fretwork with an arched window; inside it dim blue glass and the flame
    # standing in the middle, its core the eyes' colour (PR.pane_masks is the numpy twin, for the glow)
    glass = is_part(PR.GLASS)
    fx = nb.math('SUBTRACT', pa, 0.5)
    ry = nb.math('DIVIDE', nb.math('SUBTRACT', pt, 0.3), 0.22)
    arch_top = nb.math('LESS_THAN', nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', fx, 0.34), ry, 0.0)), 1.0)
    arch_side = nb.math('MULTIPLY', nb.math('LESS_THAN', nb.math('ABSOLUTE', fx), 0.34), nb.math('LESS_THAN', pt, 0.88))
    win = nb.math('MAXIMUM', nb.math('MULTIPLY', arch_top, nb.math('LESS_THAN', pt, 0.3)), nb.math('MULTIPLY', arch_side, nb.math('GREATER_THAN', pt, 0.299)))
    fy = nb.math('SUBTRACT', pt, 0.62)
    wdt = nb.math('MULTIPLY', 0.3, nb.math('POWER', nb.math('MAXIMUM', nb.math('ADD', nb.math('MULTIPLY', fy, 1.6), 0.6), 0.0), 0.7))
    flame = nb.math('MULTIPLY', MK._smooth(nb, nb.math('ABSOLUTE', fx), nb.math('ADD', wdt, 0.04), wdt), MK._smooth(nb, fy, 0.3, 0.22))
    flame = nb.math('MULTIPLY', flame, MK._smooth(nb, fy, -0.42, -0.34))
    corem = nb.math('MULTIPLY', flame, MK._smooth(nb, nb.math('ABSOLUTE', fx), nb.math('MULTIPLY', wdt, 0.5), nb.math('MULTIPLY', wdt, 0.25)))
    c = nb.mix(nb.math('MULTIPLY', glass, nb.math('SUBTRACT', 1.0, win)), c, _rgb(nb, col['iron_dark']))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', flame, win), glass), c, _rgb(nb, col['flame']))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', corem, win), glass), c, _rgb(nb, col['flame_core']))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """The crescent patch (eyeuv = (s along it -1..1, w across it: |w| 1 at the crescent's edges, e metres beyond
    them)): a hot core along its spine (about #FFB27A on the usual look) to the ember colour, deeper at the edges, then a
    thin halo fading to the face's dark at the patch's rim; matte."""
    col = WP.colours(pal or WP.BASE)
    m, nb = new_mat(name)
    em = nb.new('ShaderNodeEmission')
    if rough_pass:
        nb.put(em.inputs['Color'], (1.0, 1.0, 0.0))
    else:
        s, w, e = nb.sep(nb.attribute('eyeuv').outputs['Vector'])
        aw = nb.math('ABSOLUTE', w)
        halo = nb.math('POWER', MK._smooth(nb, e, F.CRES_MARGIN, 0.0), 1.6)
        c = nb.mix(halo, _rgb(nb, col['void']), _rgb(nb, col['eye_deep']))
        c = nb.mix(MK._smooth(nb, aw, 1.06, 0.94), c, _rgb(nb, col['eye_deep']))
        c = nb.mix(MK._smooth(nb, aw, 0.96, 0.8), c, _rgb(nb, col['eye']))
        # polish: the fill is the ember colour, with only a thin hotter line along the spine
        c = nb.mix(nb.math('MULTIPLY', MK._smooth(nb, aw, 0.24, 0.08), 0.9), c, _rgb(nb, col['eye_hot']))
        nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
