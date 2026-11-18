"""Grown Paladove's paint (Art 2.1 Ultra): the armour, the belt and the shield, beside the plumage of paladove_paint.py.

  - the breastplate: polished white (#FFFFFF with the faintest cool cast) with a gold rim and a gold gorget band; its
    gold scrollwork (a spear with a diamond head, curling leaves, a scroll each side) and the rivets are per-pixel marks
    in the body's colour pass (armour_material), so they stay crisp and the Lite copy keeps them in the texture;
  - the shoulder plates: white domes with gold rims and three rivets each; the belt: brown leather with gold rivets;
  - the shield: a white face with a gold rim, its gold feather emblem (shaft, barbs, vane), swirls and rim rivets per
    pixel (shield_material, only where the attribute shieldk is 1); its strap brown with a gold buckle.
The palette has no brown: the leather is the gold turned a little toward red and darkened (said in the report).
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth
from monsters.breeds import paladove_parts as PP
from monsters.breeds import paladove_paint as PT

WHITE, HI, GOLD, EYE = PP.WHITE, PP.HI, PP.GOLD, PP.EYE
BELT = C.shade_hex(PT._turn(GOLD, -10.0, 0.9), 0.4)          # the pictures' leather: the gold darkened to a warm brown
PLATE = C.mix_hex(HI, EYE, 0.035)                              # polished white plate, the faintest cool cast
PLATE_LO = C.shade_hex(C.mix_hex(HI, EYE, 0.12), 0.86)
L, _mix = PT.L, PT._mix


def armour_paint(co, vn, rgb, rough, coat):
    from monsters.breeds import paladove_grown_ultra as G
    nz = vn[:, 2]
    pm, pd = G.plate_mask(co, 0.004)
    qm, qd = G.pauldron_mask(co)
    bm, bd = G.belt_mask(co)
    x, z = co[:, 0], co[:, 2]
    top = 0.995 - 0.085 * np.clip(1.0 - np.abs(x) / 0.27, 0, 1) ** 1.3
    white = np.tile(L(PLATE), (len(co), 1))
    white = _mix(white, 0.55 * smooth(0.2, 0.95, nz), HI)
    white = _mix(white, 0.5 * smooth(0.1, -0.8, nz) + 0.25 * smooth(0.05, 0.0, pd), PLATE_LO)
    gold, _r, _c = PT.gold_paint(co, vn, 'trim')
    goldk = np.maximum(smooth(0.03, 0.022, pd), smooth(top - 0.085, top - 0.075, z))
    plate = _mix(white, goldk, gold)
    rgb = _mix(rgb, pm, plate)
    pa = _mix(np.tile(L(PLATE), (len(co), 1)), 0.55 * smooth(0.2, 0.95, nz), HI)
    pa = _mix(pa, smooth(0.022, 0.014, qd), gold)
    rgb = _mix(rgb, qm, pa)
    belt = np.tile(L(BELT), (len(co), 1))
    belt = _mix(belt, 0.35 * smooth(0.2, 0.9, nz), C.mix_hex(BELT, HI, 0.35))
    belt = _mix(belt, 0.5 * smooth(0.008, 0.003, bd), C.shade_hex(BELT, 0.7))
    rgb = _mix(rgb, bm * (1 - pm), belt)
    armour = np.maximum(np.maximum(pm, qm), bm)
    rough = np.where(armour > 0.5, np.where(bm > 0.5, 0.62, 0.32), rough)
    coat = np.where(armour > 0.5, np.where(bm > 0.5, 0.1, 0.5), coat)
    return rgb, rough, coat


def grown_body_colours(co, vn, tpos, lrand):
    from monsters.breeds import paladove_grown_ultra as G
    rgb, rough, coat = PT.body_colours(co, vn, tpos, lrand, G.eye_frame, False, G.EYE_R, G.LASH_V, G.MOUTH_AT, scale=1.55,
                                       crest=G.crest_zone, brows=False)
    return armour_paint(co, vn, rgb, rough, coat)


def _surface_y(x: float, z: float, out: float = 0.004) -> float:
    from monsters.breeds import paladove_grown_ultra as G
    o = np.array((x, 0.05, z))
    t = PP.ray_exit(o, (0.0, -1.0, 0.0), G.ELLS)
    q = o + np.array((0.0, -t, 0.0))
    return float(q[1] - float(G.armour_height(q[None])[0]) - out)


def _spiral(cx: float, cz: float, s: int, r0: float, r1: float, turns: float, n: int, a0: float = 0.0) -> list:
    out = []
    for k in range(n):
        t = k / (n - 1)
        a = a0 + 2 * np.pi * turns * t
        r = r0 + (r1 - r0) * t
        out.append((cx + s * r * np.cos(a), cz + r * np.sin(a)))
    return out


def scroll_paths() -> list:
    """The breastplate's gold scrollwork (grown-4 panel 3), in the front view's (x, z)."""
    paths = [[(0.0, 0.625), (0.0, 0.8)], [(0.0, 0.85), (0.032, 0.79), (0.0, 0.73), (-0.032, 0.79), (0.0, 0.85)]]
    for s in (1, -1):
        paths.append([(0.012 * s, 0.67), (0.05 * s, 0.68), (0.085 * s, 0.705), (0.1 * s, 0.735), (0.09 * s, 0.76)])
        paths.append(_spiral(0.175 * s, 0.795, s, 0.055, 0.012, 1.25, 12, a0=np.pi * 1.15))
        paths.append([(0.12 * s, 0.76), (0.09 * s, 0.735), (0.06 * s, 0.725)])
        paths.append([(x * s, 0.995 - 0.085 * max(0.0, 1.0 - x / 0.27) ** 1.3 - 0.06) for x in np.linspace(0.02, 0.29, 6)])
    return paths


def rivet_points() -> list:
    from monsters.breeds import paladove_grown_ultra as G
    pts = []
    # four rivets round each shoulder cup's rim, two at the ends of the plate's collar band
    o = np.array(G.CENTRE)
    for s in (1, -1):
        c = G.PAULDRON * np.array((s, 1, 1))
        nrm = PP.unit(c - o)
        t1 = PP.unit(np.cross(nrm, (0.0, 0.0, 1.0)))
        t2 = np.cross(nrm, t1)
        for a in (0.4, 1.97, 3.54, 5.11):
            p = c + (t1 * np.cos(a) + t2 * np.sin(a)) * 0.115
            q = PP.surface_point(o, p - o, G.ELLS)
            pts.append(tuple(map(float, q + PP.unit(p - o) * (float(G.armour_height(q[None])[0]) + 0.002))))
        p = np.array((0.235 * s, -0.3, 0.925))
        q = PP.surface_point(o, p - o, G.ELLS)
        pts.append(tuple(map(float, q + PP.unit(p - o) * (float(G.armour_height(q[None])[0]) + 0.002))))
    for a in np.linspace(0.25 * np.pi, 1.75 * np.pi, 16):
        d = np.array((np.sin(a), -np.cos(a), 0.0))
        o = np.array((0.0, 0.0, 0.6))
        pts.append(tuple(map(float, o + d * (PP.ray_exit(o, d, G.ELLS) + 0.012))))
    return pts


def armour_material(name: str, attr: str):
    """The body's colour pass: the vertex paint, plus the plate's gold scrollwork and the rivets per pixel."""
    from lib import marks as MK
    from lib.nodes import new_mat
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    masks = []
    for path in scroll_paths():
        p3 = [(float(x), _surface_y(x, z), float(z)) for x, z in path]
        for a, b in zip(p3[:-1], p3[1:]):
            masks.append(MK.line(nb, pos, a, b, 0.0095))
    scroll = MK.union(nb, masks)
    riv = MK.union(nb, [MK.dot(nb, pos, c, 0.013) for c in rivet_points()])
    col = nb.attribute(attr).outputs['Color']
    c = nb.mix(scroll, col, nb.rgb(C.lin(C.mix_hex(GOLD, HI, 0.1))))
    c = nb.mix(riv, c, nb.rgb(C.lin(C.mix_hex(GOLD, HI, 0.35))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def emblem_field(u: np.ndarray, v: np.ndarray):
    """The feather emblem in the shield's units (radius 1): (vane 0..1, shaft and quill 0..1, barb grooves 0..1)."""
    rot = np.radians(28.0)
    a = u * np.sin(rot) + v * np.cos(rot)            # along the shaft
    b = u * np.cos(rot) - v * np.sin(rot)            # across
    w = 0.27 * np.sqrt(np.clip(1.0 - ((a + 0.02) / 0.62) ** 2, 0, 1)) * (1.0 - 0.55 * np.clip(a, 0, None) / 0.58)
    vane = smooth(0.012, -0.012, np.abs(b) - w) * (a > -0.6) * (a < 0.62)
    shaft = smooth(0.032, 0.02, np.abs(b)) * (a > -0.76) * (a < 0.6)
    groove = smooth(0.7, 0.95, np.cos(2 * np.pi * (a * 7.0 - np.abs(b) * 6.0))) * vane * smooth(0.03, 0.05, np.abs(b))
    return vane, shaft, groove


def shield_relief(co: np.ndarray) -> np.ndarray:
    """The high shield's relief along its normal (round 1: a flat leaf read as a slit eye): the vane 6 mm proud with barb
    grooves, the shaft and quill 9 mm, rivets round the rim."""
    from monsters.breeds import paladove_grown_ultra as G
    c0, ax, up, n = shield_points()
    q = co - G._SC[None]
    u, v = (q @ ax) / G.SHIELD_R, (q @ up) / G.SHIELD_R
    face = (q @ n) > 0.012
    vane, shaft, groove = emblem_field(u, v)
    h = (0.006 * vane - 0.0025 * groove + 0.009 * shaft) * face
    rr = np.hypot(u, v)
    ang = np.arctan2(v, u)
    k = np.round(ang / (2 * np.pi / 16)) * (2 * np.pi / 16)
    dr = np.hypot((u - 0.93 * np.cos(k)), (v - 0.93 * np.sin(k))) * G.SHIELD_R
    h += 0.006 * np.sqrt(np.clip(1.0 - (dr / 0.012) ** 2, 0, 1)) * (rr > 0.85)
    return h


def shield_points():
    from monsters.breeds import paladove_grown_ultra as G
    n, up = G._SN, G._SU
    return G._SC + n * 0.03, np.cross(up, n), up, n


def shield_material(name: str, attr: str):
    """The props' colour pass: the vertex paint, plus on the shield (attribute shieldk) the gold feather emblem, swirls
    on the white field and rivets round the rim (grown-4 panel 4), per pixel."""
    from lib import marks as MK
    from lib.nodes import new_mat
    from monsters.breeds import paladove_grown_ultra as G
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    c0, ax, up, n = shield_points()
    R = G.SHIELD_R

    def P(u, v, d=0.0):
        return tuple(map(float, c0 + ax * u * R + up * v * R + n * d))

    rot = np.radians(28.0)

    def F(a, b):           # the feather's own axes: along its shaft (tilted 28 degrees from upright) and across
        return (a * np.sin(rot) + b * np.cos(rot), a * np.cos(rot) - b * np.sin(rot))
    fill = []
    for k in range(11):
        a = -0.42 + 1.0 * k / 10
        # a feather's vane: full and round low down, tapering to a point at the top (build 3: an even oval read as a bean)
        w = 0.27 * np.sqrt(max(0.0, 1.0 - ((a + 0.02) / 0.62) ** 2)) * (1.0 - 0.55 * max(0.0, a) / 0.58)
        if w > 0.025:
            fill.append(MK.dot(nb, pos, P(*F(a, 0.0)), float(w * R)))
    vane = MK.union(nb, fill)
    lines = [MK.line(nb, pos, P(*F(-0.74, 0.0)), P(*F(0.6, 0.0)), 0.0065)]
    # the barbs: a few broad engraved grooves (build 3: fine ones blurred away at the props' texel density)
    for k in range(5):
        a = -0.3 + 0.17 * k
        for sd in (1, -1):
            reach = 0.22 * np.sqrt(max(0.0, 1 - ((a + 0.02) / 0.62) ** 2)) * (1.0 - 0.55 * max(0.0, a) / 0.58)
            lines.append(MK.line(nb, pos, P(*F(a, 0.0)), P(*F(a + 0.12, sd * reach)), 0.005))
    shaft = MK.union(nb, lines)
    swirls = []
    for sd in (1, -1):
        sp = [(0.45 * sd + u * sd, -0.4 * sd + v) for u, v in _spiral(0.0, 0.0, 1, 0.16, 0.05, 1.1, 9)]
        for a, b in zip(sp[:-1], sp[1:]):
            swirls.append(MK.line(nb, pos, P(*a), P(*b), 0.0028))
    sw = MK.union(nb, swirls)
    rivets = MK.union(nb, [MK.dot(nb, pos, P(0.935 * np.cos(t), 0.935 * np.sin(t), -0.012), 0.0075)
                           for t in np.linspace(0, 2 * np.pi, 16, endpoint=False)])
    on = nb.attribute('shieldk').outputs['Fac']
    col = nb.attribute(attr).outputs['Color']
    c = nb.mix(nb.math('MULTIPLY', sw, nb.math('MULTIPLY', on, 0.85)), col, nb.rgb(C.lin(C.mix_hex(PLATE_LO, GOLD, 0.35))))
    # build 2: a pale vane read faintly on the white field: the vane full gold, the shaft and barbs engraved darker
    c = nb.mix(nb.math('MULTIPLY', vane, on), c, nb.rgb(C.lin(C.mix_hex(GOLD, HI, 0.12))))
    c = nb.mix(nb.math('MULTIPLY', shaft, on), c, nb.rgb(C.lin(C.shade_hex(GOLD, 0.68))))
    c = nb.mix(nb.math('MULTIPLY', rivets, on), c, nb.rgb(C.lin(C.mix_hex(GOLD, HI, 0.4))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def paint_grown(body_srcs, props=()) -> None:
    from monsters.breeds import paladove_grown_ultra as G
    for ob in body_srcs:
        co, _ = S.mesh_arrays(ob)
        vn = PT._normals(ob)
        has_t = 'tpos' in ob.data.attributes and ob.name != 'hi_body'
        tpos = S.attr_array(ob, 'tpos') if has_t else None
        lr = S.attr_array(ob, 'lrand') if has_t else None
        PT._put(ob, *grown_body_colours(co, vn, tpos, lr))
    for ob in props:
        co, _ = S.mesh_arrays(ob)
        vn = PT._normals(ob)
        pk = int(round(float(S.attr_array(ob, 'pk')[0])))
        ps = float(S.attr_array(ob, 'ps')[0])
        claw = 'claw' in ob.data.attributes
        glow = None
        shieldk = np.zeros(len(co))
        if pk == G.PK_WING:
            s = 1 if ps > 0 else -1
            i = int(round(float(S.attr_array(ob, 'pw')[0])))
            rgb, rough, coat = PT.feather_paint(co, vn, G.wing_feathers(s, i), PP.mirror(G._NW if i == 0 else G._NWB, s), seed=3 + s + 7 * i)
        elif pk == G.PK_TAIL:
            rgb, rough, coat = PT.feather_paint(co, vn, G.tail_feathers(), (0.0, 1.0, -0.3), seed=11)
        elif pk == G.PK_CREST:
            rgb, rough, coat = PT.feather_paint(co, vn, G.crest_feathers(), (0.0, -1.0, 0.0), seed=17)
            rgb = _mix(rgb, 0.35 + 0.4 * smooth(1.5, 1.6, co[:, 2]), HI)
        elif claw:
            rgb, rough, coat = PT.gold_paint(co, vn, 'claw')
        elif pk == G.PK_TARSUS and 'tarsus' in ob.name:
            lg = {k: PP.mirror(v, 1 if ps > 0 else -1) for k, v in G.LEG.items()}
            rgb, rough, coat = PT.gold_paint(co, vn, 'scaly', (lg['ankle'], lg['toe']))
        elif pk in (G.PK_TARSUS, G.PK_TOE, G.PK_SHIN):
            rgb, rough, coat = PT.gold_paint(co, vn, 'scaly', None)
        elif pk == G.PK_HALO:
            rgb, rough, coat = PT.gold_paint(co, vn, 'halo')
            glow = np.full(len(co), 0.85)
        elif pk == G.PK_SHIELD:
            c0, ax, up, n = shield_points()
            q = co - c0[None]
            r = np.hypot(q @ ax, q @ up) / G.SHIELD_R
            face = (vn @ n) > 0.35
            white = _mix(np.tile(L(PLATE), (len(co), 1)), 0.5 * smooth(0.2, 0.95, vn[:, 2]), HI)
            white = _mix(white, 0.35 * smooth(0.3, 0.85, r), PLATE_LO)
            gold, _r, _c = PT.gold_paint(co, vn, 'trim')
            rimk = np.maximum(smooth(0.83, 0.86, r), (~face).astype(float))
            rgb = _mix(white, rimk, gold)
            rough = np.where(rimk > 0.5, 0.35, 0.32)
            coat = np.full(len(co), 0.5)
            shieldk = face.astype(float) * smooth(0.83, 0.79, r)
        elif pk == G.PK_STRAP:
            rgb = np.tile(L(BELT), (len(co), 1))
            rgb = _mix(rgb, 0.35 * smooth(0.2, 0.9, vn[:, 2]), C.mix_hex(BELT, HI, 0.35))
            e, w = np.array(G.WING['elbow']), np.array(G.WING['wrist'])
            across = PP.unit(w - e)
            t = (co - G._SC[None]) @ across
            buck = smooth(-0.35, -0.34, t) * smooth(-0.27, -0.28, t)   # one buckle, at the strap's front end
            gold, _r, _c = PT.gold_paint(co, vn, 'trim')
            rgb = _mix(rgb, buck, gold)
            rough = np.where(buck > 0.5, 0.35, 0.6)
            coat = np.where(buck > 0.5, 0.4, 0.1)
        else:
            rgb, rough, coat = PT.gold_paint(co, vn, 'beak')
            inner = co[:, 1] > G.BEAK_LO['tip'][1] + 0.012
            if pk == G.PK_BEAK:
                mk = smooth(-0.35, -0.75, vn[:, 2]) * inner * (co[:, 2] < G.BEAK_UP['base'][2] - 0.008)
                rgb = _mix(rgb, mk, PT.MOUTH)
            else:
                mk = smooth(0.35, 0.75, vn[:, 2]) * inner * (co[:, 2] > G.BEAK_LO['base'][2] - 0.008)
                rgb = _mix(rgb, mk, PT.TONGUE)
            rough = np.where(mk > 0.5, 0.45, rough)
        PT._put(ob, rgb, rough, coat, glow)
        S.add_attr(ob, 'shieldk', shieldk)
