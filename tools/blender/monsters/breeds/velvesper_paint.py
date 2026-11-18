"""Velvesper's paint (Art 2.1 Ultra; chatgpt/monsters/28-velvesper): per-vertex colour and roughness for the body and the
antennae, the wings' markings per pixel (scalloped bands, the crescent moons, the eyespots, veins, scale dust and
sparkle), the face's fine lines (liner, lashes, the closed lid, the nose and the little mouth) and the eyes.

Colours come from CONTENT: wings plum #5B3F7A ('body'), the body's fur pale lavender #EDE3F5 ('belly'), the eyespots
orange #F29E4C ('accent') ringed with pale gold #F7E7B5 ('ring', CONTENT's eyespot colour; the crescents too, as the
card and every picture show), eyes #1B1424. Moonlit Velvesper (secrets.ts, variants.ts, the card): wings #5C5F78 with a
silver shimmer, fur #D9DCEC, eyespots and crescents #C0C4D8, eyes #F2E6A0 (the iris; the pupil keeps the dark).
Derived (CONTENT has no hex for these; the pictures show them), always from the palette:
  - the blush and the nose: the orange warmed toward the plum, lightened with the fur (a dusty rose);
  - the liner, the lashes and the mouth line: the eye colour; the iris of the dark eye: the plum lightened;
  - the antennae (kept by the variant, as the card says): the shaft the pale gold, the barbs the fur deepened toward
    the plum, their tips the pale gold warmed with the orange (peach);
  - the wings' scalloped bands and fringe: the plum lightened with the fur; their outlines and the sparkle: the pale
    gold warmed with the orange; the dusk glow at the wings' roots: the orange dimmed into the plum;
  - the feet's dipped tips: the wing colour (so the Moonlit feet go slate, as its picture shows);
  - painted shading (the film keeps roughness >= 0.3 and reflects a soft grey studio: pale fur goes chalky, warm marks
    go matte): fur tips lifted, creases a cool lavender, the orange's centre lit.
"""
from __future__ import annotations

import math

import numpy as np

from lib import common as C
from lib import surface as S
from lib.nodes import new_mat
from monsters.breeds import velvesper_form as F
from monsters.breeds import velvesper_props as PR
from monsters.breeds.velvesper_form import smooth

BASE = {'body': '#5B3F7A', 'belly': '#EDE3F5', 'accent': '#F29E4C', 'eye': '#1B1424', 'ring': '#F7E7B5', 'crescent': '#F7E7B5'}


def lin(h: str) -> np.ndarray:
    return np.array(C.lin_rgb(h))


def _mix(rgb: np.ndarray, col, k) -> np.ndarray:
    k = np.asarray(k, np.float64)
    if k.ndim:
        k = k[:, None]
    col = np.asarray(col, np.float64)
    return rgb * (1.0 - k) + (col if col.ndim == 2 else col[None]) * k


def sat(h: str, k: float) -> str:
    """The colour with its saturation scaled by k (sRGB, about its grey): the film desaturates plum and lavender."""
    r, g, b = C.srgb(h)
    m = (r + g + b) / 3.0
    return '#%02x%02x%02x' % tuple(int(round(255 * min(1.0, max(0.0, m + (c - m) * k)))) for c in (r, g, b))


def roles(pal: dict) -> dict:
    """The breed's colour roles from a palette (the wings, the fur, the spots, the eyes) and the base palette (what the
    variant keeps: the antennae, the blush, the dark lines)."""
    # (build 3) in game the plum measured #594365 and the bands grey-rose: painted 20% more saturated
    wing, fur, spot = sat(pal['body'], 1.2), pal['belly'], pal['accent']
    ring, cres = pal.get('ring', BASE['ring']), pal.get('crescent', BASE['crescent'])
    dark_eye = sum(C.srgb(pal['eye'])) < 0.9
    pink = sat(C.mix_hex(C.mix_hex(BASE['accent'], BASE['body'], 0.45), BASE['belly'], 0.32), 1.25)
    # (build 1) the fur measured #DFD6E8 in game (grey, chalky): painted a touch lighter and more lavender, so it lands
    # on the palette's #EDE3F5; the shadows lavender, never grey
    fur_p = C.mix_hex(C.mix_hex(fur, '#FFFFFF', 0.36), pal['body'], 0.1)
    # (round 1) the bands a light lilac (they read as a muddy dusty rose), a touch of rose; Moonlit: silver
    band = sat(C.mix_hex(C.mix_hex(fur, pal['body'], 0.34), spot, 0.08), 1.2)
    return {
        'fur': fur_p, 'fur_hi': C.mix_hex(fur_p, '#FFFFFF', 0.3), 'fur_lo': C.mix_hex(fur, wing, 0.16),
        'ruff': C.mix_hex(fur_p, '#FFFFFF', 0.22), 'ruff_lo': sat(C.mix_hex(fur, pal['body'], 0.24), 1.35),     # (round 1) lilac creases
        'foot': wing, 'foot_hi': C.mix_hex(wing, fur, 0.35),
        'wing': wing, 'wing_dk': C.shade_hex(wing, 0.66, 0.02), 'wing_hi': C.mix_hex(wing, fur, 0.22),
        'scallop': C.mix_hex(wing, band, 0.72), 'scallop_hi': band,
        'fringe': C.mix_hex(fur, band, 0.3),
        'edge': C.mix_hex(ring, spot, 0.42), 'edge_hi': C.mix_hex(ring, spot, 0.2), 'spark': C.mix_hex(ring, spot, 0.3),
        'dusk': C.mix_hex(C.mix_hex(spot, ring, 0.3), wing, 0.12),
        'spot': spot, 'spot_hi': C.mix_hex(spot, ring, 0.22), 'spot_lo': C.shade_hex(C.mix_hex(spot, wing, 0.3), 0.8),
        'ring': ring, 'crescent': cres, 'crescent_lo': C.mix_hex(cres, spot, 0.3),
        # (round 2) a dark violet iris round the pupil, lighter only low down (it rendered #7B6395: not dark eyes)
        'iris': C.mix_hex(pal['eye'], BASE['body'], 0.55) if dark_eye else pal['eye'],
        'iris_hi': C.mix_hex(BASE['body'], BASE['belly'], 0.18) if dark_eye else C.mix_hex(pal['eye'], '#FFFFFF', 0.35),
        'pupil': pal['eye'] if dark_eye else BASE['eye'],
        'lash': BASE['eye'], 'mouth': C.mix_hex(BASE['eye'], BASE['body'], 0.35),
        'blush': pink, 'nose': C.mix_hex(pink, BASE['body'], 0.12),
        'shaft': C.mix_hex(C.mix_hex(BASE['ring'], BASE['accent'], 0.12), C.mix_hex(BASE['belly'], BASE['body'], 0.36), 0.35),
        'barb': C.mix_hex(BASE['belly'], BASE['body'], 0.36),
        'barb_hi': C.mix_hex(BASE['belly'], BASE['body'], 0.18), 'barb_tip': C.mix_hex(BASE['ring'], BASE['accent'], 0.3),
    }


# ----------------------------------------------------------------------------- regions of the body
def eye_local(co: np.ndarray) -> np.ndarray:
    """(across, up, out) in the left eye's frame for |x| (both eyes), in the lens's own radii (its outline is the unit
    circle)."""
    c, xa, ya, la = (np.array(v) for v in F.eye_frame(1))
    p = np.stack([np.abs(co[:, 0]), co[:, 1], co[:, 2]], axis=1) - c
    return np.stack([p @ xa / F.EYE_AX[0], p @ ya / F.EYE_AX[1], p @ la], axis=1) / F.EYE_R


def regions(co: np.ndarray) -> dict:
    ld, _li, down = F.leg_dist(co)
    leg = smooth(0.012, 0.002, ld) * smooth(0.5, 0.44, co[:, 2])
    head = (F.head_sd(co) < 0.03) & (co[:, 2] > 0.72)
    ruff = smooth(0.8, 0.74, co[:, 2]) * smooth(0.44, 0.5, co[:, 2]) * (1.0 - head)
    return {'leg': leg, 'down': down, 'head': head, 'ruff': ruff}


def body_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    R = roles(pal)
    co, vn = I['co'], I['vn']
    n = len(co)
    plate, rim, top, pid = I['plate'], I['plate_rim'], I['plate_top'], I['plate_id']
    jit = np.where(pid >= 0, ((pid.astype(np.int64) * 2654435761) % 1000003 % 997) / 996.0 - 0.5, 0.0)
    rg = regions(co)
    up = np.clip(vn[:, 2], -1, 1)
    # (build 3) the clumps' tops only a little lighter: bright clump tips stepped into ETC1S's 4x4 blocks (pale squares)
    # (round 2) the crown no longer lifted toward white by the up-facing (it bloomed in the raw view)
    fur = _mix(np.tile(lin(R['fur']), (n, 1)), lin(R['fur_hi']), smooth(0.1, 0.9, up) * 0.12 + top * plate * 0.16)
    fur = _mix(fur, lin(R['fur_lo']), smooth(0.0, -0.85, up) * 0.36 + rim * plate * 0.12)
    ruff = _mix(np.tile(lin(R['ruff']), (n, 1)), lin(R['ruff_lo']), smooth(0.1, -0.8, up) * 0.4 + rim * plate * 0.14)
    ruff = _mix(ruff, lin(R['fur_hi']), top * plate * 0.12)
    rgb = _mix(fur, ruff, rg['ruff'] * 0.85)
    # (build 4) each tuft lighter toward its tip, the skin between the tufts a soft lavender, so the ruff, the abdomen
    # and the cheeks read as fluff (they read as flat paper flakes); h = how far a point stands off the base body
    h = F.body_sd(co) * (1.0 - rg['leg'])
    tuft = smooth(0.004, 0.04, h)
    rgb = _mix(rgb, lin(R['fur_hi']), tuft * 0.5)
    rgb = _mix(rgb, lin(R['ruff_lo']), (1.0 - tuft) * smooth(0.0, 0.5, rg['ruff'] + (co[:, 2] < 0.45)) * 0.35)
    rgb = rgb * (1.0 + 0.05 * jit)[:, None]
    # the legs: lavender fur, the tips dipped in the wing colour (4-details panel 3), the very end a little lighter
    tip = np.maximum(smooth(0.74, 0.86, rg['down']) * rg['leg'], F.toe_mask(co)[0].astype(np.float64))
    foot = _mix(np.tile(lin(R['foot']), (n, 1)), lin(R['foot_hi']), smooth(0.2, 0.9, up) * 0.3 + top * plate * 0.25)
    rgb = _mix(rgb, foot, tip)
    # the blush: a soft rose oval under and outside each eye (1-hero, 3-faces)
    bc = np.array((0.142, -0.14, 0.79))
    q = (np.stack([np.abs(co[:, 0]), co[:, 1], co[:, 2]], axis=1) - bc) / np.array((0.058, 0.07, 0.04))
    blush = smooth(1.0, 0.25, np.linalg.norm(q, axis=1)) * (co[:, 1] < -0.06)
    rgb = _mix(rgb, lin(R['blush']), blush * 0.95)
    # the eye's surround: the closed lid under the lens (fur, shaded toward the lash line)
    e = I['eye']
    lid = smooth(1.1, 0.96, np.hypot(e[:, 0], e[:, 1])) * (np.abs(e[:, 2]) < 1.6)
    rgb = _mix(rgb, _mix(np.tile(lin(R['fur']), (n, 1)), lin(R['fur_lo']), smooth(0.3, -0.9, e[:, 1]) * 0.5), lid)
    rough = np.tile(np.array([1.0, 0.72, 0.02]), (n, 1))
    rough[:, 1] = np.where(tip > 0.5, 0.56, rough[:, 1])
    return rgb, rough


def wing_marks_np(wu: np.ndarray, wv: np.ndarray, pk: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The crescent (forewings) and the eyespot's disc (hindwings), 0..1 per point: the glow's mask."""
    c, r = np.array(PR.CRESCENT['c']), PR.CRESCENT['r']
    bite = c + np.array(PR.CRESCENT['bite']) * r
    p = np.stack([wu, wv], axis=1)
    d1 = np.linalg.norm(p - c, axis=1) / r
    d2 = np.linalg.norm(p - bite, axis=1) / (r * PR.CRESCENT['bite_r'])
    cres = smooth(1.04, 0.96, d1) * smooth(0.96, 1.04, d2) * (np.abs(pk - 1.0) < 0.5)
    ce = np.array(PR.EYESPOT['c'])
    de = np.linalg.norm(p - ce, axis=1)
    disc = smooth(PR.EYESPOT['r'][0] + 0.004, PR.EYESPOT['r'][0] - 0.004, de) * (np.abs(pk - 2.0) < 0.5)
    return cres, disc


def band_edge_np(wu, wv, ws, pk) -> np.ndarray:
    """0..1 along the outer band's scalloped edge on the wings (as wing_colour draws it): its soft peach glow."""
    fc, hc = PR.WINGS['fore']['centre'], PR.WINGS['hind']['centre']
    fore = pk < 1.5
    cu, cv = np.where(fore, fc[0], hc[0]), np.where(fore, fc[1], hc[1])
    ang = np.arctan2(wv - cv, wu - cu)
    b_o = 0.82 + 0.095 * np.abs(np.cos(ang * 3.5)) ** 0.55
    return np.exp(-((ws - b_o) / 0.014) ** 2) * (pk < 2.5) * (ws > 0.05)


def prop_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    R = roles(pal)
    pk, au, aw = I['pk'], I['au'], I['aw']
    n = len(pk)
    up = I['vn'][:, 2]
    rgb = np.tile(lin(R['wing']), (n, 1))
    # the antennae: the shaft pale gold warming toward the tip; the barbs lavender deepening at the shaft, peach tips
    shaft = np.abs(pk - 3.0) < 0.5
    sc = _mix(np.tile(lin(R['shaft']), (n, 1)), lin(R['barb_tip']), smooth(0.4, 1.0, au) * 0.45)
    vane = pk > 3.5
    # the plume (round 1, 4-details panel 3): lavender barbs, lighter outward, the peach-gold blended into their tips
    vc = _mix(np.tile(lin(R['barb']), (n, 1)), lin(R['barb_hi']), smooth(0.3, 0.7, aw) * 0.5)
    vc = _mix(vc, lin(R['barb_tip']), smooth(0.62, 0.98, aw) * 0.85)
    vc = _mix(vc, lin(R['fur_hi']), smooth(0.2, 0.9, up) * 0.1) * (1.0 + 0.06 * (I['tooth'] - 0.5))[:, None]
    rgb = np.where(shaft[:, None], sc, rgb)
    rgb = np.where(vane[:, None], vc, rgb)
    rough = np.tile(np.array([1.0, 0.62, 0.02]), (n, 1))
    rough[shaft] = (1.0, 0.45, 0.12)
    rim = (pk < 2.5) & (I['wd'] < 0.012)
    rough[rim] = (1.0, 0.86, 0.0)                     # (round 2) a matte fringe, never a glossy rolled rim
    return rgb, rough


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


BODY_KEYS = ('plate', 'plate_rim', 'plate_top')
PROP_KEYS = ('pk', 'au', 'aw', 'tooth', 'wu', 'wv', 'ws', 'wd', 'wface', 'side')


def body_inputs(ob) -> dict:
    co, vn = S.mesh_arrays(ob)
    I = {'co': co, 'vn': vn, **{k: _get(ob, k) for k in BODY_KEYS}, 'plate_id': _get(ob, 'plate_id', -1.0)}
    I['eye'] = eye_local(co)
    return I


def paint_sources(body_srcs, fins, props=()) -> None:
    from lib import ultra as U
    from monsters.breeds import velvesper_ultra as RC
    vs = [(U.variant_attr(vid, RC.ID), vpal) for vid, vpal in RC.VARIANTS.items()]
    for ob in body_srcs:
        I = body_inputs(ob)
        rgb, rough = body_paint(I, RC.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        for vattr, vpal in vs:
            S.set_colour_attr(ob, vattr, body_paint(I, vpal)[0])
    for ob in props:
        co, vn = S.mesh_arrays(ob)
        I = {'co': co, 'vn': vn, **{k: _get(ob, k) for k in PROP_KEYS}}
        rgb, rough = prop_paint(I, RC.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        for vattr, vpal in vs:
            S.set_colour_attr(ob, vattr, prop_paint(I, vpal)[0])
        cres, disc = wing_marks_np(I['wu'], I['wv'], I['pk'])
        edge = band_edge_np(I['wu'], I['wv'], I['ws'], I['pk'])
        S.add_attr(ob, 'glow', np.clip(0.5 * cres + 0.62 * disc + 0.4 * edge, 0.0, 1.0))
        # Moonlit's silver wings: a little more sheen (a glossier coat on the wings; VARIANT_ORM)
        rv = rough.copy()
        wingm = I['pk'] < 2.5
        rv[wingm] = (1.0, 0.36, 0.42)
        S.set_colour_attr(ob, 'rough_moonlit', rv)
    for ob in body_srcs:
        S.set_colour_attr(ob, 'rough_moonlit', np.asarray(S.attr_array(ob, 'rough'))[:, :3].astype(np.float64))


# ----------------------------------------------------------------------------- per-pixel passes
def _eye_xy(nb, pos):
    """The left eye's (across, up, out) for |x| in eye radii."""
    c, xa, ya, la = (tuple(v) for v in F.eye_frame(1))
    px, py, pz = nb.sep(pos)
    p = nb.vmath('SUBTRACT', nb.comb(nb.math('ABSOLUTE', px), py, pz), c)
    return (nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', p, xa), F.EYE_R * F.EYE_AX[0]),
            nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', p, ya), F.EYE_R * F.EYE_AX[1]),
            nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', p, la), F.EYE_R))


LASH_Y = -0.08            # the closed lid's lash line, in eye radii below the lens's centre


def lid_lines(nb, pos):
    """The closed eye's lash line (a soft downward curve across the lens's footprint, the lashes at its outer end), the
    upper lid's dark liner hugging the lens and thickening toward the outer corner, and three lashes flicking up and
    out there (1-hero, 3-faces, 4-details panel 2)."""
    ex, ey, ez = _eye_xy(nb, pos)
    near = nb.smooth(nb.math('ABSOLUTE', ez), 1.7, 1.2)
    cy = nb.math('ADD', LASH_Y, nb.math('MULTIPLY', nb.math('MULTIPLY', ex, ex), 0.26))
    dist = nb.math('ABSOLUTE', nb.math('SUBTRACT', ey, cy))
    span = nb.smooth(nb.math('ABSOLUTE', ex), 1.02, 0.82)
    wl = nb.math('MULTIPLY', span, 0.075)
    lash = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', dist, wl), 0.014, -0.014), nb.math('MULTIPLY', near, span))
    # (build 2) no liner ring on the skin (it stayed round the closed eye as an empty outline): the lens's own dark rim
    # is the open eye's line; three lashes flick up and out from the outer corner, where the closed lid's line ends
    lashes = None
    for ang, L in ((2.0, 0.3), (16.0, 0.36), (30.0, 0.28)):
        a = math.radians(ang)
        ox, oy = math.cos(a), math.sin(a)
        da = math.radians(ang + 26.0)
        dx, dy = math.cos(da), math.sin(da)
        sx = nb.math('SUBTRACT', ex, ox * 1.0)
        sy = nb.math('SUBTRACT', ey, oy * 1.0)
        t = nb.math('ADD', nb.math('MULTIPLY', sx, dx), nb.math('MULTIPLY', sy, dy))
        lat = nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('MULTIPLY', sy, dx), nb.math('MULTIPLY', sx, dy)))
        lat = nb.math('SUBTRACT', lat, nb.math('MULTIPLY', nb.math('MULTIPLY', t, t), 0.5))
        w = nb.math('MULTIPLY', nb.smooth(t, L, 0.0), 0.05)
        st = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', nb.math('ABSOLUTE', lat), w), 0.012, -0.012),
                                         nb.math('MULTIPLY', nb.smooth(t, -0.05, 0.02), nb.smooth(t, L + 0.02, L - 0.02))), near)
        lashes = st if lashes is None else nb.math('MAXIMUM', lashes, st)
    return nb.math('MAXIMUM', lash, lashes)


def face_marks(nb, pos):
    """The tiny nose (a rounded rose triangle on the muzzle) and the little closed smile under it (3-faces neutral):
    returns (nose mask, mouth line mask)."""
    px, py, pz = nb.sep(pos)
    front = nb.smooth(py, -0.13, -0.16)
    ax = nb.math('ABSOLUTE', px)
    # the nose: wider at the top, rounded
    nx = nb.math('DIVIDE', ax, nb.math('ADD', 0.0085, nb.math('MULTIPLY', nb.math('SUBTRACT', pz, 0.812), 0.45)))
    ny = nb.math('DIVIDE', nb.math('SUBTRACT', pz, 0.8185), 0.0072)
    nose = nb.math('MULTIPLY', nb.smooth(nb.vmath('LENGTH', nb.comb(nx, ny, 0.0)), 1.08, 0.92), front)
    # the philtrum and the two little arcs of the smile
    phil = nb.math('MULTIPLY', nb.smooth(ax, 0.0017, 0.0009), nb.math('MULTIPLY', nb.smooth(pz, 0.812, 0.81), nb.smooth(pz, 0.8, 0.802)))
    cx = nb.math('SUBTRACT', ax, 0.0088)
    cz = nb.math('SUBTRACT', pz, 0.8085)
    rr = nb.vmath('LENGTH', nb.comb(cx, cz, 0.0))
    arc = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', rr, 0.0088)), 0.0018, 0.001), nb.smooth(cz, 0.002, -0.002))
    arc = nb.math('MULTIPLY', arc, nb.smooth(ax, 0.02, 0.0175))
    mouth = nb.math('MULTIPLY', nb.math('MAXIMUM', phil, arc), front)
    return nose, mouth


def body_material(name: str, attr: str, pal: dict, marks):
    m, nb = new_mat(name)
    R = roles(pal)
    c = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    lines = lid_lines(nb, pos)
    nose, mouth = face_marks(nb, pos)
    c = nb.mix(nose, c, nb.rgb(C.lin(R['nose'])))
    c = nb.mix(nb.math('MAXIMUM', lines, mouth), c, nb.rgb(C.lin(R['lash'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def _scallop(nb, ang, lobes: float):
    """1 at each lobe's middle, falling to 0 at the cusps between them (a scalloped edge's bulge)."""
    return nb.math('POWER', nb.math('ABSOLUTE', nb.math('COSINE', nb.math('MULTIPLY', ang, lobes * 0.5))), 0.55)


def wing_colour(nb, R: dict):
    """The wing's markings per pixel (1-hero, 2-turnaround, 4-details panels 4-6)."""
    A = nb.attribute
    wu, wv = A('wu').outputs['Fac'], A('wv').outputs['Fac']
    ws, wd = A('ws').outputs['Fac'], A('wd').outputs['Fac']
    pk = A('pk').outputs['Fac']
    fore = nb.smooth(pk, 1.6, 1.4)
    hind = nb.math('SUBTRACT', 1.0, fore)
    fc, hc = PR.WINGS['fore']['centre'], PR.WINGS['hind']['centre']
    cu = nb.math('ADD', hc[0], nb.math('MULTIPLY', fore, fc[0] - hc[0]))
    cv = nb.math('ADD', hc[1], nb.math('MULTIPLY', fore, fc[1] - hc[1]))
    ang = nb.math('ARCTAN2', nb.math('SUBTRACT', wv, cv), nb.math('SUBTRACT', wu, cu))
    r0 = nb.vmath('LENGTH', nb.comb(wu, wv, 0.0))
    phi = nb.math('ARCTAN2', wv, wu)
    rgb = lambda h: nb.rgb(C.lin(h))      # noqa: E731
    # the plum, a touch lighter in the middle, darker toward the margin; the dusk glow round the roots
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(ws, 0.55, 0.0), 0.35), rgb(R['wing']), rgb(R['wing_hi']))
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(ws, 0.84, 0.97), 0.55), c, rgb(R['wing_dk']))
    dusk = nb.math('MULTIPLY', nb.math('POWER', nb.smooth(r0, 0.36, 0.04), 1.6), nb.smooth(ws, 0.95, 0.75))
    c = nb.mix(nb.math('MULTIPLY', dusk, 0.85), c, rgb(R['dusk']))
    # veins: lighter lines fanning out from the root, fading toward the margin
    vein = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SINE', nb.math('ADD', nb.math('MULTIPLY', phi, 11.0), 0.4))), 0.06, 0.0),
                   nb.math('MULTIPLY', nb.smooth(r0, 0.06, 0.2), nb.smooth(ws, 0.92, 0.62)))
    c = nb.mix(nb.math('MULTIPLY', vein, 0.3), c, rgb(R['dusk']))
    # the scale dust (round 1: the regular shingle rows striped like corduroy): a fine speckle of lighter and darker
    # scales; the relief is in the source wing's geometry (velvesper_props DUST), baked into the normal map
    vec = nb.comb(wu, wv, nb.math('MULTIPLY', pk, 3.7))
    fine = nb.noise(vec, 150.0, 2.0)
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(fine, 0.55, 0.78), 0.2), c, rgb(R['scallop_hi']))
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(fine, 0.45, 0.22), 0.16), c, rgb(R['wing_dk']))
    # the outer band (1-hero, 2-turnaround): rose-lavender scallops in two overlapping rows following the margin, each
    # scallop lighter toward its free edge, the outer row edged in warm pale gold; the plum darker beyond it
    sc9 = _scallop(nb, ang, 7.0)                                    # (build 2) fewer, deeper scallops (tree rings)
    sc9b = _scallop(nb, nb.math('ADD', ang, math.pi / 7.0), 7.0)
    b_o = nb.math('ADD', 0.82, nb.math('MULTIPLY', sc9, 0.095))
    b_m = nb.math('ADD', 0.72, nb.math('MULTIPLY', sc9b, 0.08))
    b_i = nb.math('ADD', 0.6, nb.math('MULTIPLY', sc9, 0.07))
    band = nb.math('MULTIPLY', ss(nb, ws, nb_val(nb, b_i, -0.01), b_i), ss(nb, ws, nb_val(nb, b_o, 0.005), b_o))
    row_o = ss(nb, ws, b_m, b_o)                                    # 0 at the inner row's edge .. 1 at the outer edge
    row_i = ss(nb, ws, b_i, b_m)
    lift = nb.math('MAXIMUM', nb.math('MULTIPLY', row_o, nb.smooth(ws, 0.0, 0.01)), nb.math('MULTIPLY', row_i, nb.math('SUBTRACT', 1.0, row_o)))
    bc = nb.mix(lift, rgb(R['scallop']), rgb(R['scallop_hi']))
    c = nb.mix(nb.math('MULTIPLY', band, 0.92), c, bc)
    edge_m = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', ws, b_m)), 0.006, 0.0015), band)
    c = nb.mix(nb.math('MULTIPLY', edge_m, 0.35), c, rgb(R['edge']))
    # (round 1) the band's scalloped outer edge glows peach (1-hero, 4-details): a bright line in a soft warm halo
    # (and a modest glow from the wings' `glow` attribute)
    do = nb.math('ABSOLUTE', nb.math('SUBTRACT', ws, b_o))
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(do, 0.035, 0.0), 0.3), c, rgb(R['edge']))
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(do, 0.009, 0.002), 0.95), c, rgb(R['edge_hi']))
    beyond = ss(nb, ws, nb_val(nb, b_o, 0.004), nb_val(nb, b_o, 0.03))
    c = nb.mix(nb.math('MULTIPLY', beyond, 0.35), c, rgb(R['wing_dk']))
    # the inner band (forewings): a softer row of scallops between the dusk glow and the crescent
    b_2 = nb.math('ADD', 0.44, nb.math('MULTIPLY', _scallop(nb, ang, 7.0), 0.05))
    band2 = nb.math('MULTIPLY', nb.math('MULTIPLY', ss(nb, ws, nb_val(nb, b_2, -0.12), nb_val(nb, b_2, -0.03)), ss(nb, ws, nb_val(nb, b_2, 0.005), b_2)), fore)
    c = nb.mix(nb.math('MULTIPLY', band2, 0.6), c, rgb(R['scallop']))
    edge_2 = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', ws, b_2)), 0.006, 0.0015), fore)
    c = nb.mix(nb.math('MULTIPLY', edge_2, 0.5), c, rgb(R['edge']))
    # the fringe: a pale, soft rim all round (round 1: softer and wider, fading in over 1.6 cm)
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(wd, 0.02, 0.003), 0.7), c, rgb(R['edge']))
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(wd, 0.006, 0.0), 0.5), c, rgb(R['fringe']))
    # sparkle: sparse warm specks, thicker in the bands and the margin
    vor = nb.voronoi(vec, 120.0)
    thin = nb.smooth(nb.noise(vec, 34.0, 1.0), 0.36, 0.5)                 # (round 2) more of the peach glints
    spark = nb.math('MULTIPLY', nb.smooth(vor, 0.2, 0.1), nb.math('MULTIPLY', thin, nb.math('ADD', 0.5, nb.math('MULTIPLY', band, 0.5))))
    c = nb.mix(nb.math('MULTIPLY', spark, 0.95), c, rgb(R['edge_hi']))
    # the crescent moon on each forewing: the bite toward the body and up (2-turnaround front, 1-hero)
    cr = PR.CRESCENT
    cc = cr['c']
    bc = (cc[0] + cr['bite'][0] * cr['r'], cc[1] + cr['bite'][1] * cr['r'])
    d1 = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', wu, cc[0]), nb.math('SUBTRACT', wv, cc[1]), 0.0)), cr['r'])
    d2 = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', wu, bc[0]), nb.math('SUBTRACT', wv, bc[1]), 0.0)), cr['r'] * cr['bite_r'])
    cres = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(d1, 1.03, 0.97), nb.smooth(d2, 0.97, 1.03)), fore)
    halo = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(d1, 1.45, 1.0), nb.math('SUBTRACT', 1.0, cres)), fore)
    c = nb.mix(nb.math('MULTIPLY', halo, 0.3), c, rgb(R['scallop']))
    ccol = nb.mix(nb.smooth(d1, 0.6, 1.0), rgb(R['crescent']), rgb(R['crescent_lo']))
    c = nb.mix(cres, c, ccol)
    # the eyespot on each hindwing: an orange disc lit at its centre, a pale gold ring, a thin plum ring and a
    # scalloped lavender band round it (4-details panel 4)
    es = PR.EYESPOT
    r1, r2, r3 = es['r']
    ex = nb.math('SUBTRACT', wu, es['c'][0])
    ey = nb.math('SUBTRACT', wv, es['c'][1])
    de = nb.vmath('LENGTH', nb.comb(ex, ey, 0.0))
    ea = nb.math('ARCTAN2', ey, ex)
    r3s = nb.math('ADD', r3 - 0.012, nb.math('MULTIPLY', _scallop(nb, ea, 10.0), 0.014))
    outer = nb.math('MULTIPLY', ss(nb, de, nb_val(nb, r3s, 0.003), r3s), hind)
    c = nb.mix(nb.math('MULTIPLY', outer, 0.7), c, rgb(R['scallop']))
    c = nb.mix(nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', de, r3s)), 0.007, 0.002), nb.math('MULTIPLY', hind, 0.7)), c, rgb(R['edge']))
    # (round 1) no dark line round the ring; the orange glows softly out into the pale gold ring
    ringm = nb.math('MULTIPLY', nb.smooth(de, r2 + 0.007, r2 - 0.003), hind)
    c = nb.mix(ringm, c, rgb(R['ring']))
    disc = nb.math('MULTIPLY', nb.smooth(de, r1 + 0.009, r1 - 0.006), hind)
    dcol = nb.ramp(nb.math('DIVIDE', de, r1), [(0.0, C.lin(R['spot_hi'])), (0.35, C.lin(C.mix_hex(R['spot'], R['spot_hi'], 0.4))),
                                                (0.75, C.lin(R['spot'])), (1.0, C.lin(R['spot_lo']))])
    speck = nb.math('MULTIPLY', nb.smooth(nb.voronoi(vec, 260.0), 0.22, 0.12), 0.35)
    dcol = nb.mix(speck, dcol, rgb(R['spot_hi']))
    c = nb.mix(disc, c, dcol)
    return c


def nb_val(nb, sock, add: float):
    return nb.math('ADD', sock, add)


def ss(nb, x, a, b):
    """smoothstep(a, b, x) with node-socket bounds (nb.smooth takes numbers only)."""
    t = nb.math('DIVIDE', nb.math('SUBTRACT', x, a), nb.math('SUBTRACT', b, a))
    t = nb.math('MINIMUM', nb.math('MAXIMUM', t, 0.0), 1.0)
    return nb.math('MULTIPLY', nb.math('MULTIPLY', t, t), nb.math('SUBTRACT', 3.0, nb.math('MULTIPLY', t, 2.0)))


def prop_material(name: str, attr: str, pal: dict, marks):
    """The props' colour: the wings' markings per pixel, the antennae's paint with fine barbules along every tooth."""
    m, nb = new_mat(name)
    R = roles(pal)
    c = nb.attribute(attr).outputs['Color']
    pk = nb.attribute('pk').outputs['Fac']
    wing = nb.smooth(pk, 2.6, 2.4)
    au = nb.attribute('au').outputs['Fac']
    aw = nb.attribute('aw').outputs['Fac']
    vane = nb.smooth(pk, 3.5, 3.7)
    barb = nb.math('MULTIPLY', nb.smooth(nb.math('SINE', nb.math('ADD', nb.math('MULTIPLY', au, 900.0), nb.math('MULTIPLY', aw, 14.0))), 0.4, 0.95),
                   nb.math('MULTIPLY', nb.smooth(aw, 0.3, 0.5), vane))
    c = nb.mix(nb.math('MULTIPLY', barb, 0.14), c, nb.rgb(C.lin(R['fur_hi'])))
    c = nb.mix(wing, c, wing_colour(nb, R))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- eyes
def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    """Big soft eyes (4-details panel 2): a deep pupil filling most of the lens, the iris a ring round it that glows
    lighter at the bottom, a dark rim, a sliver of pale sclera; a big catchlight high on the inner side and a small one
    low on the outer side."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, 0.06, 0.9), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    R = roles(pal or BASE)
    e = nb.attribute('eyeuv').outputs['Vector']
    rx, ry, _z = nb.sep(e)
    side = nb.attribute('eye_side').outputs['Fac']
    ix = nb.math('DIVIDE', nb.math('ADD', rx, 0.0), 0.9)
    iy = nb.math('DIVIDE', nb.math('ADD', ry, 0.05), 0.9)
    ri = nb.vmath('LENGTH', nb.comb(ix, iy, 0.0))
    k = 1.0 / 1.6
    pupil, iris, hi = C.lin(R['pupil']), C.lin(R['iris']), C.lin(R['iris_hi'])
    # (round 1) a thinner dark outer ring (it read as a thick black rim)
    col = nb.ramp(nb.math('MULTIPLY', ri, k), [(0.0, pupil), (0.5 * k, pupil), (0.6 * k, C.lin(C.mix_hex(R['pupil'], R['iris'], 0.55))),
                                               (0.9 * k, iris), (1.03 * k, C.lin(C.shade_hex(R['iris'], 0.6))), (1.08 * k, C.lin(R['pupil'])),
                                               (1.0, C.lin(R['pupil']))])
    # the iris glows lighter toward the bottom
    low = nb.math('MULTIPLY', nb.smooth(iy, 0.1, -0.7), nb.math('MULTIPLY', nb.smooth(ri, 0.5, 0.62), nb.smooth(ri, 0.95, 0.85)))
    col = nb.mix(nb.math('MULTIPLY', low, 0.75), col, nb.rgb(hi))
    # the upper lid's shadow over the top of the lens
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(ry, 0.45, 0.9), 0.5), col, nb.rgb(C.lin(R['pupil'])))
    # catchlights: high on the inner side (toward the nose: -x on the left eye) and small low on the outer side
    sx = nb.math('MULTIPLY', rx, side)
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', sx, 0.26), nb.math('SUBTRACT', ry, 0.3), 0.0)), 0.2, 0.14)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', sx, 0.28), nb.math('ADD', ry, 0.3), 0.0)), 0.085, 0.05)
    col = nb.mix(nb.math('MAXIMUM', big, nb.math('MULTIPLY', small, 0.9)), col, nb.rgb((1.0, 1.0, 1.0)))
    em = nb.new('ShaderNodeEmission')
    nb.link(col, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the shape preview
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import velvesper_ultra as RC
    n = len(co)
    vn = vn if vn is not None else np.tile((0.0, 0.0, 1.0), (n, 1))
    I = {'co': co, 'vn': vn, 'plate': np.zeros(n), 'plate_rim': np.zeros(n), 'plate_top': np.zeros(n), 'plate_id': np.full(n, -1.0),
         'eye': eye_local(co)}
    return body_paint(I, RC.PALETTE)[0]
