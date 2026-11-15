"""Bloatoad's carving (Art 2.1 Ultra): the high source's relief and the attributes its paint reads, and the low body's
share of it (bloatoad_skin.py has the zones, the eyes' lids and the mouth):
  - warts of every size as raised droplet domes (the big glossy ones, many small, a fine pebbling), and the dark
    rosettes on the back, the head and the legs: raised lobed patches of clustered nodules (4-details panel 6);
  - soft rolls across the throat and the belly, creases at the wrists, the elbows and the hind ankles, the jowl folds
    from the mouth's corners; pores on the peach.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import bloatoad_form as F
from monsters.breeds import bloatoad_skin as SK
from monsters.breeds import bloatoad_noise as N

smooth = F.smooth
v3 = F.v3
_LAST: dict = {}
_ROSETTES: dict = {}


def crown_dist(co: np.ndarray) -> np.ndarray:
    d = np.full(len(co), np.inf)
    for c, r in F.CROWN:
        d = np.minimum(d, np.linalg.norm(co - v3(c), axis=1) - r)
    return d


def warty(co: np.ndarray, z: dict) -> np.ndarray:
    """0..1 where the olive skin carries warts: not on the peach, the lips and the snout, the eyes' openings, the toe
    pads or the crown bumps."""
    ff = SK.face_front(co)
    snout = ff & (co[:, 2] > 0.79) & (co[:, 2] < 0.95) & (np.abs(co[:, 0]) < 0.24)
    w = (1.0 - smooth(0.15, 0.55, z['peach'])) * (1.0 - 0.85 * snout)
    w = w * smooth(0.075, 0.1, z['eye_d']) * smooth(-0.002, 0.012, F.toe_dist(co)) * smooth(0.004, 0.02, crown_dist(co))
    return np.clip(w, 0.0, 1.0)


def rosette_layout(co: np.ndarray, vn: np.ndarray, z: dict) -> dict:
    """The dark rosettes (2-turnaround side and back, 4-details panel 6): big on the back and the top of the head-body
    (6-9 cm across... up to 13), smaller down the flanks, the haunches and the legs; none on the peach, the face or the
    feet. Laid out once per build (the high source first) and kept for the low body."""
    if 'plates' in _ROSETTES:
        return _ROSETTES['plates']
    x, y, zz = co[:, 0], co[:, 1], co[:, 2]
    ok = warty(co, z) > 0.9
    ok &= (zz > 0.16) & (z['eye_d'] > 0.16) & ~(SK.face_front(co) & (zz < 1.0)) & (crown_dist(co) > 0.05)
    back = smooth(0.45, 0.75, zz) * smooth(-0.3, -0.05, y)
    sp = np.where(ok, 0.14 + 0.06 * back, np.nan)
    rad = 0.038 + 0.042 * back + 0.008 * smooth(0.3, 0.5, F.leg_dist(co))
    rad = np.where(F.leg_dist(co) < 0.13, 0.03, rad)
    # round 2: raised clusters standing proud of the skin (they read as flat painted patches at 3 mm)
    plates = U.plate_layout(co, vn, sp, rad, 0.0058, seed=211, wobble=0.3)
    # polish: no rosette reaching the peach: one lay across the crease where each arm meets the belly, its nodules
    # smeared into dark "stubble" in the crease's shadow (flagged in every round)
    from mathutils.kdtree import KDTree
    kd = KDTree(len(co))
    for i, p in enumerate(co):
        kd.insert(p, i)
    kd.balance()
    pe = z['peach']
    nplate = len(plates['c'])
    keep = np.array([max((pe[j] for _c, j, _d in kd.find_range(plates['c'][i], float(plates['a'][i]) * 1.3)), default=0.0) < 0.03
                     for i in range(nplate)])
    plates = {k: (v[keep] if isinstance(v, np.ndarray) and len(v) == nplate else v) for k, v in plates.items()}
    C.log(f'skin: {int((~keep).sum())} rosettes dropped against the peach')
    _ROSETTES['plates'] = plates
    C.log(f'skin: {len(plates["c"])} rosettes')
    return plates


def cells(co: np.ndarray, cell: float, seed: int, keep: float, r0: float, r1: float, power: float = 0.6):
    """Raised domes, one per Voronoi cell where present (a share `keep`): radius r0..r1 (metres) at random, a droplet's
    profile. Returns (profile 0..1, radius per point, cell hash 0..1)."""
    f1, _f2, fid = N.voronoi(co, cell, seed, jitter=0.8)
    h = (np.abs(fid) % 9973) / 9972.0
    h2 = np.mod(h * 7.31 + 0.13, 1.0)
    rr = r0 + (r1 - r0) * h2
    prof = np.clip(1.0 - (f1 / rr) ** 2, 0.0, 1.0) ** power * (h < keep)
    cells.q = np.where(h < keep, f1 / rr, 9.0)          # each point's distance from its dome's centre (× its radius)
    return prof, rr, h


def fold_field(co: np.ndarray, z: dict) -> dict:
    """The soft rolls across the throat and the belly (curving up at their ends like the smile), rings at the wrists,
    the elbows and the hind ankles, and the jowl folds from the mouth's corners down the throat's sides."""
    x, y, zz = co[:, 0], co[:, 1], co[:, 2]
    # round 2: the sac stays a smooth dome; below it many shallow, irregular, slightly curved folds flow down into the
    # belly (2-turnaround front, 4-details panel 4): thin creases that wander, break off and start again, about 3-4 cm
    # apart, curving up a little at their ends (two or three deep even grooves read as stacked tyres)
    # round 3: the folds follow the belly's curve (arcs rising toward its sides like the smile above), wander more and
    # break into shorter pieces (straight even folds read as wood grain)
    warp = 0.45 * N.fbm(co, 1 / 0.16, 301, 2) + 0.25 * N.fbm(co, 1 / 0.06, 303, 2)
    u = (zz - 0.12 * (x / 0.3) ** 2 - 0.1) / (0.03 + 0.008 * N.fbm(co, 1 / 0.3, 305, 1)) + warp
    ph = np.mod(u, 1.0)
    dist = np.minimum(ph, 1.0 - ph)
    k = np.floor(u)
    gate = smooth(-0.15, 0.4, N.fbm(np.stack([x * 2.2, k * 0.61, np.zeros_like(x)], axis=1), 1 / 0.09, 307, 2))
    on = z['peach'] * smooth(-0.3, -0.42, y) * smooth(0.52, 0.42, zz) * smooth(0.1, 0.17, zz) * smooth(0.36, 0.18, np.abs(x))
    crease_b = np.exp(-(dist / 0.07) ** 2) * gate * on
    amp = 0.6 + 0.6 * N.hash1(np.abs(k.astype(np.int64)), 309)
    disp = (-0.0011 * crease_b + 0.0004 * np.exp(-((ph - 0.3) / 0.15) ** 2) * gate * on) * amp
    crease = crease_b * 0.7
    for s in (1, -1):
        k, a = v3(F._m(F.LEG_F['knee'], s)), v3(F._m(F.LEG_F['ankle'], s))
        d, t = F.seg_dist(co, k, a)
        near = smooth(0.11, 0.085, d)
        ring = np.exp(-((t - 0.8) / 0.03) ** 2) + np.exp(-((t - 0.9) / 0.025) ** 2) + 0.7 * np.exp(-((t - 0.1) / 0.04) ** 2)
        disp -= 0.0026 * ring * near
        crease = np.maximum(crease, ring * near)
        k2, a2 = v3(F._m(F.LEG_B['knee'], s)), v3(F._m(F.LEG_B['ankle'], s))
        d2, t2 = F.seg_dist(co, k2, a2)
        ring2 = np.exp(-((t2 - 0.88) / 0.035) ** 2) * smooth(0.12, 0.09, d2)
        disp -= 0.0022 * ring2
        crease = np.maximum(crease, ring2)
        for off, dep in ((0.0, 0.0035), (0.06, 0.0025)):
            p0 = v3((0.355 * s, -0.42 + off, 0.86 - off))
            p1 = v3((0.43 * s, -0.22 + off, 0.6 - off))
            dj, tj = F.seg_dist(co, p0, p1)
            g = np.exp(-(dj / 0.007) ** 2) * smooth(0.0, 0.15, tj) * smooth(1.0, 0.75, tj)
            disp -= dep * g
            crease = np.maximum(crease, g)
    return {'disp': disp, 'crease': np.clip(crease, 0, 1)}


def snout_mask(co: np.ndarray) -> np.ndarray:
    """0..1: the lighter snout round the nostrils and the upper lip (2-turnaround front, 4-details panel 1)."""
    th = SK.mouth_theta(co)
    # (round 1: from 1.5 cm above the mouth's line: freckles at the lip stretched into dark streaks when the jaw opened)
    above = smooth(0.012, 0.026, co[:, 2] - SK.mouth_z(th))
    d = F.ell_sdf(co, (0.0, -0.56, 0.88), (0.25, 0.12, 0.085))
    return above * smooth(0.03, -0.005, d) * SK.face_front(co)


CUT_END = SK.MOUTH_END - 3.0     # polish: the cut runs nearly into the corners (a short uncut corner stretched into a tuft)
CUT_SNAP = 0.22                  # an edge crossed this near one end moves that vertex onto the line (no slivers)


def cut_mouth(ob) -> int:
    """Cut the game mesh along the mouth's line, so the lips part cleanly when the jaw opens and the mouth bag shows
    behind them (bloatoad_props). Polish: run on the final, decimated mesh (bloatoad_props.build calls it before making
    the bag; cut before the decimation, its smoothing pass pulled the two lips' edges apart into a beaded zipper), and
    along the line itself: every edge that crosses the line is split where it crosses (or its near end moved onto it),
    each face split there, and the edges along the line cut, so each lip ends in one smooth curve (the edges of the
    triangles zigzagged before). The corners stay joined. Stores `jside` per vertex (1 the jaw's side, 0 the head's,
    0.5 both: the cut's ends, -1 away from it), which the rig's weights read (bloatoad_skin.weight_regions). Returns
    how many edges were cut."""
    import bmesh
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    lay = bm.verts.layers.float.new('mf')

    def field(v) -> float:
        c = np.array([v.co[:]])
        return float(SK.mouth_z(SK.mouth_theta(c))[0] - c[0, 2])

    def inside(v) -> bool:
        c = np.array([v.co[:]])
        return bool((np.abs(SK.mouth_theta(c)) < CUT_END + 2.0)[0] and SK.face_front(c)[0] and c[0, 1] < -0.33)

    zone = set()
    for v in bm.verts:
        f = field(v)
        v[lay] = f
        if abs(f) < 0.03 and inside(v):
            zone.add(v)

    def on_line(v) -> None:
        c = np.array([v.co[:]])
        v.co.z = float(SK.mouth_z(SK.mouth_theta(c))[0])
        v[lay] = 0.0

    # snap: an edge crossing the line near one end moves that end onto it
    for e in list(bm.edges):
        a, b = e.verts
        if a not in zone or b not in zone:
            continue
        fa, fb = a[lay], b[lay]
        if fa == 0.0 or fb == 0.0 or (fa > 0) == (fb > 0):
            continue
        t = fa / (fa - fb)
        if t < CUT_SNAP:
            on_line(a)
        elif t > 1.0 - CUT_SNAP:
            on_line(b)
    # split every edge still crossing the line where it crosses
    for e in list(bm.edges):
        a, b = e.verts
        if a not in zone or b not in zone:
            continue
        fa, fb = a[lay], b[lay]
        if fa == 0.0 or fb == 0.0 or (fa > 0) == (fb > 0):
            continue
        _ne, nv = bmesh.utils.edge_split(e, a, fa / (fa - fb))
        on_line(nv)
        zone.add(nv)
    # split each face between its two vertices on the line, when it has corners on both sides
    for fc in list(bm.faces):
        vs = list(fc.verts)
        if not any(v in zone for v in vs):
            continue
        ons = [v for v in vs if v[lay] == 0.0 and v in zone]
        if len(ons) != 2:
            continue
        if not (any(v[lay] > 0 for v in vs) and any(v[lay] < 0 for v in vs)):
            continue
        if any(set(e.verts) == set(ons) for e in fc.edges):
            continue
        try:
            bmesh.utils.face_split(fc, ons[0], ons[1])
        except ValueError:
            pass
    big = [fc for fc in bm.faces if len(fc.verts) > 3]
    if big:
        bmesh.ops.triangulate(bm, faces=big)

    def side(fc) -> int:
        f = [v[lay] for v in fc.verts if v[lay] != 0.0]
        return 0 if not f else (1 if sum(f) > 0 else -1)

    cut = []
    for e in bm.edges:
        a, b = e.verts
        if a[lay] != 0.0 or b[lay] != 0.0 or a not in zone or b not in zone or len(e.link_faces) != 2:
            continue
        mid = np.array([[(a.co.x + b.co.x) / 2, (a.co.y + b.co.y) / 2, (a.co.z + b.co.z) / 2]])
        if abs(SK.mouth_theta(mid)[0]) >= CUT_END:
            continue
        s0, s1 = side(e.link_faces[0]), side(e.link_faces[1])
        if s0 * s1 < 0:
            cut.append(e)
    if cut:
        bmesh.ops.split_edges(bm, edges=cut)
    bm.verts.ensure_lookup_table()
    js = np.full(len(bm.verts), -1.0)
    for v in bm.verts:
        if v not in zone and abs(v[lay]) >= 0.03:
            continue
        sides = {side(fc) for fc in v.link_faces} - {0}
        if not sides or not inside(v):
            continue
        js[v.index] = 1.0 if sides == {1} else (0.0 if sides == {-1} else 0.5)
    bm.verts.layers.float.remove(lay)
    bm.to_mesh(me)
    bm.free()
    me.update()
    if me.validate(verbose=False):
        C.log('mouth: validate() fixed invalid geometry after the cut')
    S.add_attr(ob, 'jside', js)
    C.log(f'mouth: cut {len(cut)} edges along the line; {int((js == 1).sum())} jaw-side, {int((js == 0).sum())} head-side vertices')
    return len(cut)


def ground(z: np.ndarray) -> np.ndarray:
    """The belly and the soles resting on the ground: anything below 1.5 cm eases toward it and never under it (a hard
    clamp folded the skin under the ground into a flat doubled sheet, which the decimation collapsed across the body)."""
    g = 0.015
    return np.where(z < g, g * np.exp((np.minimum(z, g) - g) / g), z)


def carve(ob) -> None:
    SK.blend_creases(ob, 180)
    co, vn = S.mesh_arrays(ob)
    z = SK.zones(co)
    E = SK.eye_field(co, vn)
    Mo = SK.mouth_field(co, vn)
    wt = warty(co, z)
    pl = rosette_layout(co, vn, z)
    rf = U.plate_field(co, vn, pl, 'cobble', 1.0, 0.0, edge_soft=0.55)
    ros = rf['mask'] * wt
    nod, _rr, _nid = cells(co, 0.017, 223, 1.0, 0.007, 0.0095, power=0.5)
    ros_id = U.plate_hash(rf['pid'], 5)
    head = z['head'].astype(float)
    med, med_r, med_id = cells(co, 0.046, 231, 0.7, 0.01, 0.021)
    med_q = cells.q
    sml, sml_r, sml_id = cells(co, 0.022, 241, 0.66, 0.0045, 0.008)
    tny, _tr, _ti = cells(co, 0.0095, 251, 0.85, 0.0028, 0.0038, power=0.8)
    lidk = smooth(0.3, 0.8, E['lid'])
    med = med * wt * (1.0 - lidk) * (1.0 - 0.5 * head) * (1.0 - ros)
    sml = sml * wt * (1.0 - 0.6 * lidk) * (1.0 - 0.7 * ros)
    # the lips stay smooth (an opening jaw stretches them: fine relief there turned into streaks)
    lips = 1.0 - (1.0 - smooth(0.02, 0.035, np.abs(co[:, 2] - SK.mouth_z(SK.mouth_theta(co))))) * SK.face_front(co)
    # round 3: no small warts or pebbles down in the body's creases (they read as stubble in the inner thigh's shadow)
    cm = 1.0 - smooth(0.15, 0.5, SK.crease_mask(co))
    tny = tny * wt * lips * cm
    sml = sml * lips * cm
    med = med * lips
    Fo = fold_field(co, z)
    peach = z['peach']
    pores = N.fbm(co, 1 / 0.007, 261, 2)
    # round 2: fine bumps and pores on the head, the brow and the snout too (they read smoother than the body)
    face = np.maximum(snout_mask(co), smooth(0.02, -0.02, F.ell_sdf(co, F.HEAD[0], F.HEAD[1])) * smooth(0.72, 0.8, co[:, 2]))
    face = face * lips * smooth(0.085, 0.11, z['eye_d']) * (1.0 - smooth(0.4, 0.8, E['lid']))
    fb, _fr, _fi = cells(co, 0.009, 271, 0.7, 0.0022, 0.0034, power=0.7)
    fp = smooth(0.0016, 0.0006, N.voronoi(co, 0.006, 281)[0]) * smooth(-0.1, 0.4, N.fbm(co, 1 / 0.05, 283, 2))
    # droplets on the sac and the throat (1-hero, 4-details panel 4)
    sg = SK.sac_gloss(co)
    drop, _dr, _di = cells(co * np.array([1.0, 1.0, 0.62]), 0.05, 291, 0.32, 0.005, 0.008, power=0.45)
    drop = drop * smooth(0.4, 0.8, sg)
    sw = SK.sac_weight(co)
    # a fine pore stipple on the peach (2-turnaround front)
    pit = smooth(0.0021, 0.0009, N.voronoi(co, 0.0075, 311)[0]) * peach * (1.0 - smooth(0.4, 0.8, sg))
    disp = (-0.00035 * pit + E['disp'] + Mo['disp'] + rf['h'] * wt + 0.003 * nod * ros + 0.48 * med_r * med + 0.55 * sml_r * sml
            + 0.0005 * tny + Fo['disp'] + 0.00025 * pores * peach * (1.0 - sg) + (0.00055 * fb - 0.0005 * fp) * face
            + 0.0026 * drop)
    new = co + vn * disp[:, None] + E['vec'] + Mo['vec']
    new[:, 2] = ground(new[:, 2])
    S.set_positions(ob, new)
    S.base_attrs(ob, co, {'mouth': Mo['mouth']})
    attrs = {'peach': peach, 'ros': ros, 'ros_nod': nod * ros, 'ros_id': ros_id, 'ros_rim': rf['rim'] * (rf['pid'] >= 0) * wt,
             'wart': med, 'wart_id': med_id, 'swart': sml, 'swart_id': sml_id, 'crease': Fo['crease'], 'lip': Mo['lip'],
             'nostril': Mo['nostril'], 'lid': E['lid'], 'lash': E['lash'], 'closed': E['closed'], 'rim': E['rim'],
             'socket': E['socket'], 'pad': smooth(0.003, -0.004, F.toe_dist(co)), 'web': SK.web_mask(co),
             'crown': smooth(0.006, -0.002, crown_dist(co)), 'snout': snout_mask(co), 'sac': sw, 'mband': Mo['band'],
             'sacg': sg, 'drop': drop, 'wq': np.minimum(med_q, 9.0) * (wt > 0.5) + 9.0 * (wt <= 0.5), 'mfold': Mo['fold'],
             # polish: the mouth's line drawn per pixel by the colour pass (bloatoad_paint.body_material) from its height
             # above the line (linear, so it interpolates exactly): as vertex colour, a few millimetres wide on a 3 mm
             # mesh, it beaded; the corner's tuck stays painted
             'mdz': np.where(Mo['span'] > 0.01, Mo['dz'], 0.1), 'mspan': Mo['span'], 'mcorner': Mo['corner'],
             'paw': F.foot_mask(co)}
    for k, v in attrs.items():
        S.add_attr(ob, k, np.asarray(v, np.float64))
    _LAST.clear()
    _LAST.update({'n': len(co), 'base': co.copy(), **{k: np.asarray(v).copy() for k, v in attrs.items()}, 'mouth': Mo['mouth']})
    C.log(f'carve: {len(co)} vertices, height {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm, '
          f'{int((peach > 0.5).sum())} peach, {int((ros > 0.5).sum())} rosette, {int((med > 0.3).sum())} wart')


def carve_low(ob) -> None:
    """The low body takes the eyes' lids and sockets (the half-lidded look is geometry), the rosettes' plateaus and the
    belly's rolls, so its outline is the high source's."""
    SK.blend_creases(ob, 60)
    co, vn = S.mesh_arrays(ob)
    z = SK.zones(co)
    E = SK.eye_field(co, vn)
    wt = warty(co, z)
    pl = rosette_layout(co, vn, z)
    rf = U.plate_field(co, vn, pl, 'cobble', 0.8, 0.0, edge_soft=0.55)
    Fo = fold_field(co, z)
    Mo = SK.mouth_field(co, vn)
    # round 2: the mouth's slit is geometry here too (the jaw opens it)
    disp = E['disp'] + rf['h'] * wt + 0.7 * Fo['disp'] + Mo['disp']
    new = co + vn * disp[:, None] + E['vec'] + Mo['vec']
    new[:, 2] = ground(new[:, 2])
    S.set_positions(ob, new)
    C.log(f'carve_low: {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm')
    # (the mouth is cut after the decimation: bloatoad_props.build calls cut_mouth)
