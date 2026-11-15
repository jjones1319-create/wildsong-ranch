"""Scrollopus's per-pixel shading (Art 2.1 Ultra): the bake materials.
  - the ink spots and freckles (1-hero, 4-details panel 5): crisp round ink dots, big on the head's top, back and the
    forehead's sides, small ones in loose arcs on the cheeks under the eyes;
  - the props: the book's gold border and leaf emblem, the seal's stamped leaf, the vane's barbs;
  - the eyes (3-faces neutral, made a little sly): a big dark iris with a violet ring in a white eye, two catchlights,
    the upper lid lowered a little (skin over the lens's top with a thick lash line and two flicks at the outer
    corner), a thin lower lid.
"""
from __future__ import annotations

import math

import numpy as np

from lib import common as C
from lib import marks as MK
from lib import surface as S
from lib.nodes import new_mat
from monsters.breeds import scrollopus_form as F
from monsters.breeds import scrollopus_noise as N
from monsters.breeds import scrollopus_paint as PT


_MARKS: dict = {}


def cheek_point(x: float, z: float) -> np.ndarray:
    """The face's surface at (x, z), found from the front along +Y (the head's ellipsoids, cheeks included)."""
    ys = np.linspace(-0.4, 0.0, 801)
    pts = np.stack([np.full(len(ys), x), ys, np.full(len(ys), z)], axis=1)
    inside = np.nonzero(F.mantle_sdf(pts) < 0.0)[0]
    return pts[inside[0]] if len(inside) else F.head_surface(np.array([x, -0.4, z]))


def make_marks(hi_body=None) -> dict:
    """The ink spots and freckles: centres on the head's surface (snapped to the carved high body when given)."""
    spots = []
    c0 = np.array(F.MANTLE[0])
    from monsters.breeds import scrollopus_cap as CP
    # round 3 (review: rows of wallpaper dots): scattered at random over the head, of widely mixed sizes, denser and
    # bigger toward the crown and the back; kept off the face (the freckles are on the cheeks)
    for i in range(6000):
        if len(spots) >= 110:
            break
        h = N.hash1(np.array([i, i + 1000, i + 2000, i + 3000, i + 4000]), 708)
        z = -1.0 + 2.0 * h[0]
        az = 2.0 * math.pi * h[1]
        d = np.array([math.cos(az) * math.sqrt(1 - z * z), math.sin(az) * math.sqrt(1 - z * z), z])
        p = F.head_surface(c0 + d)
        hem = CP.SKULL_Z - CP.SKULL_TILT * (p[0] / 0.28) - 0.01
        if p[2] > hem or p[2] < 0.415:
            continue
        front = p[1] < -0.1
        if front and (p[2] < 0.785 or abs(p[0]) < 0.06):
            continue
        if p[1] < -0.02 and p[2] < 0.565:
            continue                                   # not on the cheeks' sides (the freckles are there)
        back = float(np.clip((p[1] + 0.06) / 0.3, 0.0, 1.0))
        top = float(np.clip((p[2] - 0.56) / (hem - 0.56), 0.0, 1.0))
        if h[2] > 0.3 + 0.7 * max(top, 0.6 * back):
            continue                                   # sparser low down and on the sides
        big = max(back, top)
        r = 0.0045 + 0.004 * float(h[3]) + 0.034 * big ** 0.8 * float(h[4]) ** 1.4
        if any(np.linalg.norm(p - q) < 0.8 * (r + rq) + 0.006 for q, rq in spots):
            continue
        spots.append((p, r))
    # small clusters at the temples (above and outside the rims)
    for s_ in (1, -1):
        for k in range(7):
            h = N.hash1(np.array([k + 300 + 20 * (s_ > 0), k + 77]), 733)
            a = k / 6.0
            x = s_ * (0.21 + 0.035 * math.cos(a * 5.0) + 0.012 * (h[0] - 0.5))
            z = 0.695 + 0.05 * a + 0.012 * (h[1] - 0.5)
            spots.append((cheek_point(x, z), 0.0042 + 0.0035 * float(h[0])))
    # satellites: a few small dots beside the big ones (4-details panel 5)
    sats = []
    for j, (p, r) in enumerate(spots):
        h = N.hash1(np.array([j, j + 50]), 711)
        if r > 0.02 and h[0] > 0.4:
            t = F._unit(np.cross(p - c0, (0.0, 0.0, 1.0)))
            q = F.head_surface(p + t * (r + 0.009) * (1 if h[1] > 0.5 else -1) + np.array([0, 0, 0.006]))
            sats.append((q, 0.0045 + 0.003 * float(h[1])))
    # the freckles: loose arcs on each cheek under the eye, and a few on the tentacle roots in front
    frk = []
    for s in (1, -1):
        for k in range(11):
            h = N.hash1(np.array([k + 31 * (s > 0), k + 77]), 719)
            a = -0.2 + 0.9 * k / 10.0
            x = s * (0.14 + 0.06 * a + 0.01 * (h[0] - 0.5))
            z = 0.523 - 0.022 * a * a + 0.01 * (h[1] - 0.5) - (0.011 if k % 2 else 0.0)
            # build 5: on the cheek straight in front (cast from the head's centre they landed in the eye sockets)
            p = cheek_point(x, z)
            frk.append((p, 0.0034 + 0.0022 * float(h[0])))
    pts = spots + sats + frk
    lash = closed_lash()
    if hi_body is not None:
        co, _vn = S.mesh_arrays(hi_body)
        from mathutils import Vector
        from mathutils.kdtree import KDTree
        sel = np.nonzero((co[:, 2] > 0.38) & (co[:, 2] < 1.0))[0]
        kd = KDTree(len(sel))
        for i, v in enumerate(co[sel]):
            kd.insert(Vector(v), i)
        kd.balance()
        pts = [(np.array(co[sel[kd.find(Vector(p))[1]]]), r) for p, r in pts]
        # build 4: the lash lines snapped onto the carved dome (on the analytic one they pierced it only in spots)
        snap = lambda p: list(map(float, co[sel[kd.find(Vector(p))[1]]]))  # noqa: E731
        lash = [[snap(a), snap(b), w] for a, b, w in lash]
    out = {'dots': [[list(map(float, p)), float(r)] for p, r in pts], 'lash': lash}
    _MARKS.clear()
    _MARKS.update(out)
    return out


def closed_lash() -> list:
    """The closed lids' lash lines (3-faces blink: a relaxed downward curve, two flicks at the outer corner), as line
    segments lying on the socket's dome under each lens (where the skin shows when a blink sinks the lens)."""
    from monsters.breeds import scrollopus_skin as SK
    from monsters.breeds import scrollopus_ultra as R
    segs = []
    for s in (1, -1):
        c, xax, yax, look = SK.eye_axes(s)
        Rr, sh, dp = F.EYE_R, F.EYE_SHAPE[1], F.EYE_DEPTH

        def on_dome(x, y):
            rr = min(0.999, math.hypot(x, y))
            z = (math.sqrt(1.0 - rr * rr) * dp[0] - dp[1]) * Rr - 0.003
            return c + xax * (x * Rr) + yax * (y * Rr * sh) + look * z

        xs = np.linspace(-0.9, 0.92, 15)
        top = R.LID_EDGE - 0.08
        pts = [on_dome(float(x), float(top - 0.22 * (1.0 - x * x) - 0.04)) for x in xs]
        for a, b in zip(pts[:-1], pts[1:]):
            mid = 0.5 * (a + b) - c
            w = 0.0021 * (1.0 - 0.45 * abs(float(mid @ xax)) / Rr)
            segs.append([list(map(float, a)), list(map(float, b)), float(w)])
        # the flicks: short strokes out and down from the outer corner (x toward the outer side is +s along xax)
        for k, (dx, dy) in enumerate(((0.22, -0.16), (0.12, -0.26))):
            xo = float(xs[-1] if s > 0 else xs[0])
            y0 = float(top - 0.22 * (1.0 - xo * xo) - 0.04) - 0.05 * k
            a = on_dome(xo - 0.05 * k * (1 if s > 0 else -1), y0)
            b = on_dome(xo + dx * (1 if s > 0 else -1) * 0.9, y0 + dy)
            segs.append([list(map(float, a)), list(map(float, b)), 0.0016])
    return segs


def dot_mask(co) -> 'np.ndarray':
    """0..1 per point inside the last made ink dots (the paint's roughness: matte ink, no glint on a dark dot)."""
    m = np.zeros(len(co))
    for p, r in _MARKS.get('dots', []):
        d = np.linalg.norm(co - np.asarray(p), axis=1)
        m = np.maximum(m, np.clip((1.15 * r - d) / (0.3 * r), 0.0, 1.0))
    return m


def body_material(name: str, attr: str, pal: dict, marks):
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    if marks and marks.get('dots'):
        pos = nb.coords().outputs['Object']
        # a tiny wobble on each edge, so the dots read as ink, not stickers
        warp = nb.vmath('ADD', pos, nb.vmath('SCALE', nb.comb(nb.noise(pos, 140.0, 1.0, 0.5), nb.noise(nb.vmath('ADD', pos, nb.comb(2.1, 0.3, 1.7)), 140.0, 1.0, 0.5), 0.5), scale=0.0016))
        # round 2: a soft edge about two texels wide (a hard dark edge stepped in the KTX2 blocks); round 3 softer
        dots = MK.union(nb, [MK.dot(nb, warp, tuple(p), (r, r, r), soft=min(0.3, 0.0045 / max(r, 1e-4))) for p, r in marks['dots']])
        ink = C.lin(PT.colours(pal)['ink'])
        c = nb.mix(nb.math('MULTIPLY', dots, 0.94), c, nb.rgb(ink))
    if marks and marks.get('lash'):
        pos = nb.coords().outputs['Object']
        lash = MK.union(nb, [MK.line(nb, pos, tuple(a), tuple(b), w, soft=0.35) for a, b, w in marks['lash']])
        c = nb.mix(nb.math('MULTIPLY', lash, 0.95), c, nb.rgb(C.lin(pal['eye'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks):
    """The props' colour pass: their paint, plus the book's gold border and leaf on the front cover and fine barbs on
    the vane."""
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    col = PT.colours(pal)
    pk = nb.attribute('pk').outputs['Fac']
    cover = nb.math('MULTIPLY', nb.smooth(pk, 39.5, 39.9), nb.smooth(pk, 40.5, 40.1))
    outer = nb.attribute('outer').outputs['Fac']
    cu = nb.attribute('cu').outputs['Fac']
    cv = nb.attribute('cv').outputs['Fac']
    # the border: a gold line 1 cm in from each edge, a fine one inside it
    du = nb.math('MINIMUM', cu, nb.math('SUBTRACT', 1.0, cu))
    dv = nb.math('MINIMUM', cv, nb.math('SUBTRACT', 1.0, cv))
    dd = nb.math('MINIMUM', nb.math('MULTIPLY', du, F.BOOK['w']), nb.math('MULTIPLY', dv, F.BOOK['h']))
    line = nb.math('MAXIMUM', nb.math('MULTIPLY', nb.smooth(dd, 0.0085, 0.0105), nb.smooth(dd, 0.0145, 0.0125)),
                   nb.math('MULTIPLY', nb.smooth(dd, 0.0175, 0.0185), nb.smooth(dd, 0.0205, 0.0195)))
    # the emblem: a leaf (an almond) with its midrib, in the middle of the cover
    lx = nb.math('MULTIPLY', nb.math('SUBTRACT', cu, 0.5), F.BOOK['w'])
    ly = nb.math('MULTIPLY', nb.math('SUBTRACT', cv, 0.52), F.BOOK['h'])
    leaf_r = nb.math('ADD', nb.math('MULTIPLY', nb.math('MULTIPLY', lx, lx), 1.0 / (0.016 ** 2)),
                     nb.math('MULTIPLY', nb.math('MULTIPLY', ly, ly), 1.0 / (0.034 ** 2)))
    leaf = nb.math('MULTIPLY', nb.smooth(leaf_r, 1.0, 0.92), nb.smooth(nb.math('ABSOLUTE', lx), 0.0012, 0.0022))
    stem = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', lx), 0.0018, 0.0008), nb.math('MULTIPLY', nb.smooth(ly, -0.05, -0.044), nb.smooth(ly, 0.03, 0.02)))
    # round 2: crisp gold corner pieces (a triangle and a fine line inside it), the leaf sharper
    dsum = nb.math('ADD', nb.math('MULTIPLY', du, F.BOOK['w']), nb.math('MULTIPLY', dv, F.BOOK['h']))
    corner = nb.math('MAXIMUM', nb.smooth(dsum, 0.031, 0.029), nb.math('MULTIPLY', nb.smooth(dsum, 0.0375, 0.0365), nb.smooth(dsum, 0.0405, 0.0415)))
    gold = nb.math('MULTIPLY', nb.math('MAXIMUM', nb.math('MAXIMUM', nb.math('MAXIMUM', line, leaf), stem), corner), nb.math('MULTIPLY', cover, outer))
    c = nb.mix(nb.math('MULTIPLY', gold, 0.95), c, nb.rgb(C.lin(col['gold'])))
    # the seal: a leaf stamped into the gold (a shade darker), its midrib
    seal = nb.math('MULTIPLY', nb.smooth(pk, 21.5, 21.9), nb.smooth(pk, 22.5, 22.1))
    su = nb.attribute('su').outputs['Fac']
    sv = nb.attribute('sv').outputs['Fac']
    sl = nb.math('ADD', nb.math('MULTIPLY', nb.math('MULTIPLY', su, su), 1.0 / 0.09), nb.math('MULTIPLY', nb.math('MULTIPLY', sv, sv), 1.0 / 0.36))
    stamp = nb.math('MAXIMUM', nb.math('MULTIPLY', nb.smooth(sl, 1.0, 0.85), nb.smooth(nb.math('ABSOLUTE', su), 0.03, 0.06)),
                    nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', sl), 1.25, 1.05), nb.smooth(nb.math('ABSOLUTE', sl), 1.45, 1.6)))
    # round 3: the leaf raised and lighter than the wax round it
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', stamp, seal), 0.75), c, nb.rgb(C.lin(col['gold_hi'])))
    # the pages' edges: fine lines along the fore-edge and the top (one per few leaves)
    pages = nb.math('MULTIPLY', nb.smooth(pk, 40.5, 40.9), nb.smooth(pk, 41.5, 41.1))
    # polish: a few soft lines (95 a unit stepped into a zipper at the book's texel size)
    lines = nb.math('SINE', nb.math('MULTIPLY', nb.attribute('side').outputs['Fac'], 14.0))
    lines = nb.math('MULTIPLY', nb.smooth(lines, 0.4, 0.95), nb.math('MULTIPLY', pages, 0.12))
    c = nb.mix(lines, c, nb.rgb(C.lin(col['page_line'])))
    # round 3: faint lines of text on the open pages and the loose leaves (rows of broken dashes inside a margin)
    facem = nb.attribute('face').outputs['Fac']
    row = nb.math('SINE', nb.math('MULTIPLY', cv, F.BOOK['h'] * 2.0 * math.pi / 0.0078))
    row = nb.smooth(row, 0.55, 0.85)
    marg = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(cu, 0.13, 0.16), nb.smooth(cu, 0.88, 0.85)),
                   nb.math('MULTIPLY', nb.smooth(cv, 0.09, 0.11), nb.smooth(cv, 0.9, 0.88)))
    pos = nb.coords().outputs['Object']
    words = nb.smooth(nb.noise(pos, 90.0, 1.0, 0.5), 0.42, 0.48)
    text = nb.math('MULTIPLY', nb.math('MULTIPLY', row, marg), nb.math('MULTIPLY', words, nb.math('MULTIPLY', facem, pages)))
    c = nb.mix(nb.math('MULTIPLY', text, 0.32), c, nb.rgb(C.lin(col['page_line'])))
    # the vane's barbs: fine slanted lines (a shade darker between them)
    vane = nb.math('MULTIPLY', nb.smooth(pk, 32.5, 32.9), nb.smooth(pk, 33.5, 33.1))
    along = nb.attribute('along').outputs['Fac']
    w2 = nb.attribute('w2').outputs['Fac']
    barb = nb.math('SINE', nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', along, 1.0), nb.math('MULTIPLY', w2, -0.12)), 520.0))
    barb = nb.math('MULTIPLY', nb.smooth(barb, 0.55, 0.95), nb.math('MULTIPLY', vane, 0.22))
    c = nb.mix(barb, c, nb.rgb(C.lin(C.shade_hex(col['vane'], 0.7))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the eyes
def eye_material(name: str, rough_pass: bool, pal: dict):
    from monsters.breeds import scrollopus_ultra as R
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    rxs = nb.math('MULTIPLY', rx, side)                        # + toward the outer corner
    # the upper lid's edge: arched, a little lower at the outer corner (half-lidded, knowing)
    edge = nb.math('ADD', nb.math('ADD', R.LID_EDGE, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', rx, rx)), 0.1)),
                   nb.math('MULTIPLY', nb.smooth(rxs, 0.2, 1.0), -0.1))
    upper = nb.smooth(nb.math('SUBTRACT', ry, edge), -0.015, 0.015)
    low_edge = nb.math('ADD', -0.9, nb.math('MULTIPLY', nb.math('MULTIPLY', rx, rx), 0.12))
    lower = nb.smooth(nb.math('SUBTRACT', low_edge, ry), -0.02, 0.02)
    lid = nb.math('MAXIMUM', upper, lower)
    # the iris: big and dark, a touch toward the inner corner and up under the lid (a sly look)
    ix = nb.math('SUBTRACT', rx, 0.07)                         # a sly glance toward its left (the camera's side)
    iy = nb.math('SUBTRACT', ry, 0.02)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.66), nb.math('DIVIDE', iy, 0.7), 0.0))
    if rough_pass:
        rr = nb.math('ADD', 0.22, nb.math('MULTIPLY', lid, 0.4))
        cc = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, lid), 0.7)
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, rr, cc), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    eye = pal['eye']
    col = PT.colours(pal)
    ring = C.mix_hex(eye, pal['body'], 0.55)
    white = C.mix_hex(pal['belly'], '#FFFFFF', 0.82)
    c = nb.ramp(nb.math('MINIMUM', ri, 1.0), [(0.0, C.lin(C.shade_hex(eye, 0.6))), (0.52, C.lin(C.shade_hex(eye, 0.6))), (0.6, C.lin(eye)),
                                            (0.8, C.lin(C.mix_hex(eye, ring, 0.6))), (0.93, C.lin(ring)), (0.985, C.lin(C.shade_hex(eye, 0.7))),
                                            (1.0, C.lin(eye))])
    c = nb.mix(nb.smooth(ri, 0.99, 1.03), c, nb.rgb(C.lin(white)))
    # the white's shade under the upper lid
    sh = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ry, edge), -0.4, 0.0), 0.35)
    c = nb.mix(sh, c, nb.rgb(C.lin(C.mix_hex(white, pal['body'], 0.5))))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.2), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.14), 1.1), 0.0)), 0.21, 0.15)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.22), nb.math('ADD', ry, 0.3), 0.0)), 0.075, 0.05)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    # round 3: the spectacles' glass shows as a faint curved glint on its upper left (the glint pieces floated)
    ga = nb.vmath('LENGTH', nb.comb(rx, ry, 0.0))
    gdir = nb.math('ADD', nb.math('MULTIPLY', rx, -0.62), nb.math('MULTIPLY', ry, 0.78))
    glass = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(ga, 0.7, 0.76), nb.smooth(ga, 0.88, 0.82)),
                    nb.smooth(nb.math('DIVIDE', gdir, nb.math('MAXIMUM', ga, 0.01)), 0.72, 0.9))
    c = nb.mix(nb.math('MULTIPLY', glass, 0.42), c, nb.rgb((1.0, 1.0, 1.0)))
    c = nb.mix(upper, c, nb.rgb(C.lin(col['lid'])))
    c = nb.mix(lower, c, nb.rgb(C.lin(C.mix_hex(pal['body'], pal['belly'], 0.3))))
    d = nb.math('SUBTRACT', ry, edge)
    lash = nb.math('MULTIPLY', nb.smooth(d, -0.09, -0.02), nb.smooth(d, 0.085, 0.025))
    # two flicks at the outer corner
    fl = nb.math('MULTIPLY', nb.smooth(rxs, 0.62, 0.8), nb.math('MULTIPLY', nb.smooth(d, -0.02, 0.02), nb.smooth(nb.math('SUBTRACT', d, nb.math('MULTIPLY', nb.math('SUBTRACT', rxs, 0.7), 0.9)), 0.13, 0.05)))
    lash = nb.math('MAXIMUM', lash, fl)
    c = nb.mix(lash, c, nb.rgb(C.lin(eye)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
