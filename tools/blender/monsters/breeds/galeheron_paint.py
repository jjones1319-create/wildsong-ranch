"""Galeheron's paint (Art 2.1 Ultra; chatgpt/monsters/25-galeheron): per-vertex colour and roughness for the body and
every prop, the per-pixel wind swirls on the wings, the closed lids and the eyes.

Colours come from CONTENT: feathers sky blue #6FB7E9, the belly and the front of the neck #F5F8FC, the wind swirls deep
blue #2F5D8A, the beak, the legs and the eyes gold #F2C14E. Dawnwing (variants.ts, the card): feathers peach #F7B59A,
belly #FFF1EA, swirls rose #E86A8A; the beak, legs and eyes keep their gold. Derived (CONTENT has no hex for these; the
pictures show them), always from the base palette so the variant changes only the plumage:
  - the claws: the gold darkened toward the deep blue (a grey horn);
  - the lash and liner lines and the pupils: the deep blue darkened to a near-black navy;
  - the mouth's inside: the gold darkened and warmed;
  - the shading painted in (the film keeps roughness at 0.3 or more and reflects a soft grey studio, so the gold and the
    whites land darker and flatter in the game): sky lighter on the top surfaces, the deep blue in the feather edges,
    the whites shaded a cool blue-grey in the creases and lifted warm on the feather tips; the gold's highlights.
"""
from __future__ import annotations

import math

import numpy as np

from lib import common as C
from lib import surface as S
from lib.nodes import new_mat
from monsters.breeds import galeheron_form as F
from monsters.breeds.galeheron_form import smooth

BASE = {'body': '#6FB7E9', 'belly': '#F5F8FC', 'accent': '#2F5D8A', 'eye': '#F2C14E'}


def lin(h: str) -> np.ndarray:
    return np.array(C.lin_rgb(h))


def _mix(rgb: np.ndarray, col, k) -> np.ndarray:
    k = np.asarray(k, np.float64)
    if k.ndim:
        k = k[:, None]
    col = np.asarray(col, np.float64)
    return rgb * (1.0 - k) + (col if col.ndim == 2 else col[None]) * k


def roles(pal: dict) -> dict:
    """The breed's colour roles from a palette (the plumage) and the base palette (everything the variant keeps)."""
    gold = BASE['eye']
    return {
        'sky': pal['body'], 'sky_hi': C.mix_hex(pal['body'], '#FFFFFF', 0.22), 'sky_lo': C.shade_hex(pal['body'], 0.8),
        'white': pal['belly'], 'white_lo': C.shade_hex(C.mix_hex(pal['belly'], pal['body'], 0.22), 0.86),
        'white_hi': C.mix_hex(pal['belly'], gold, 0.04), 'deep': pal['accent'],
        'gold': gold, 'gold_hi': C.mix_hex(gold, '#FFFFFF', 0.4), 'gold_lo': C.shade_hex(C.mix_hex(gold, '#C46A1E', 0.35), 0.72),
        'claw': C.shade_hex(C.mix_hex(gold, BASE['accent'], 0.55), 0.3), 'claw_tip': C.mix_hex(C.shade_hex(gold, 0.6), '#FFFFFF', 0.2),
        'navy': C.shade_hex(BASE['accent'], 0.32), 'mouth': C.shade_hex(C.mix_hex(gold, '#B0402A', 0.45), 0.55),
    }


# ----------------------------------------------------------------------------- regions of the body
def leg_dist(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The distance to the nearest leg line (drumstick, tarsus, toes, claws) and a claw mask."""
    d = np.full(len(co), np.inf)
    claw = np.zeros(len(co), bool)
    for s in (1, -1):
        k, a, t = (np.array(F.mirror(F.LEG[q], s)) for q in ('knee', 'ankle', 'toe'))
        for p0, p1, r0, r1 in ((k, a, F.SHIN_R[0], F.SHIN_R[1]), (a, t, F.TARSUS_R[0], F.TARSUS_R[1])):
            d = np.minimum(d, F.sd_tube(co, p0, p1, r0, r1))
        # (build 4) the heel's knob and the foot's pad (the knob's back baked white: a pale dot on each heel)
        d = np.minimum(d, F.sd_ell(co, a + np.array((0.0, 0.004, 0.0)), (F.HEEL_R, F.HEEL_R * 1.1, F.HEEL_R * 1.25), (0.0, 0.0, 0.0)))
        d = np.minimum(d, F.sd_ell(co, t + np.array((0.0, -0.004, -0.006)), (0.024, 0.027, 0.014), (0.0, 0.0, 0.0)))
        for b, tip, kk in F.toes(s):
            d = np.minimum(d, F.sd_tube(co, b, tip, F.TOE_R[0] * kk, F.TOE_R[1] * kk))
            dc = F.sd_tube(co, tip, F.claw_tip(b, tip), F.CLAW[1] * kk, 0.0016)
            claw |= (dc < 0.004) & (np.linalg.norm(co - tip, axis=1) > 0.004)
            d = np.minimum(d, dc)
    return d, claw


def white_mask(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """1 on the white front (breast, belly, throat, the face under the eyes), 0 on the sky-blue back, wings and crown.
    (round 2) Judged by the smooth analytic body's normals, not the carved mesh's (the feather plates' normals made the
    neck's border a stair-step), with wider blends."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    n = F.sd_normal(F.body_sd, co)
    nx, ny, nz = n[:, 0], n[:, 1], n[:, 2]
    # the leaning trunk: its front and its underside white, its back and flanks blue (the wings cover the flanks)
    front = -0.85 * ny - 0.55 * nz
    body = smooth(-0.12, 0.22, front) * smooth(0.45, 0.2, nz)             # (polish) the shoulder dome blue
    body = np.maximum(body, smooth(-0.35, -0.7, nz) * smooth(0.42, 0.3, y))
    # the neck: its front half, wider at the base
    neck = smooth(-0.55, 0.3, -ny - 0.2 * np.abs(nx))              # a wide, soft border (ETC1S stair-stepped a sharp one)
    # the head: below the line from the beak's base under the eye to the nape; a white ring round the eye
    zl = np.interp(y, [-0.26, -0.215, -0.17, -0.12, -0.08], [1.452, 1.458, 1.452, 1.428, 1.4])
    head = smooth(0.008, -0.008, z - zl) * smooth(0.4, 0.1, ny) * smooth(-0.06, -0.1, y)   # (polish) the nape blue (a white collar)
    c, xa, ya, la = (np.array(v) for v in F.eye_frame(1))
    p = np.stack([np.abs(x), y, z], axis=1) - c
    er = np.hypot(p @ xa / F.EYE_AX[0], p @ ya / F.EYE_AX[1]) / F.EYE_R
    ring = smooth(1.3, 1.12, er) * (np.abs(p @ la) < 0.03)                # (round 3) a narrow white rim
    head = np.maximum(head, ring)
    wb = smooth(1.1, 1.0, z)                # the trunk below the neck's base
    wh = smooth(1.36, 1.42, z) * smooth(-0.06, -0.1, y)        # the head
    m = body * wb + neck * (1 - wb)
    return np.clip(m * (1 - wh) + head * wh, 0.0, 1.0)


def eye_local(co: np.ndarray) -> np.ndarray:
    """(across, up, out) in the left eye's frame for |x| (both eyes), in the almond lens's own radii (the lens's
    outline is the unit circle)."""
    c, xa, ya, la = (np.array(v) for v in F.eye_frame(1))
    p = np.stack([np.abs(co[:, 0]), co[:, 1], co[:, 2]], axis=1) - c
    return np.stack([p @ xa / F.EYE_AX[0], p @ ya / F.EYE_AX[1], p @ la], axis=1) / F.EYE_R


def body_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    R = roles(pal)
    co, vn = I['co'], I['vn']
    n = len(co)
    plate, rim, top, pid = I['plate'], I['plate_rim'], I['plate_top'], I['plate_id']
    jit = np.where(pid >= 0, ((pid.astype(np.int64) * 2654435761) % 1000003 % 997) / 996.0 - 0.5, 0.0)
    wm = white_mask(co, vn)
    # (polish) the flanks and the rump under the folded wings: blue feathers, lifted against the wings' baked shadow
    # (hit and hit_heavy open the wings and showed them as bare grey skin)
    na = F.sd_normal(F.body_sd, co)
    zlo = np.where(co[:, 1] > 0.15, 0.6, 0.66)
    flank = smooth(0.42, 0.65, np.abs(na[:, 0])) * smooth(zlo, zlo + 0.05, co[:, 2]) * smooth(1.1, 1.04, co[:, 2]) * smooth(-0.13, -0.05, co[:, 1])
    wm = wm * (1.0 - flank)
    up = np.clip(vn[:, 2], -1, 1)
    # the plumage
    sky = _mix(np.tile(lin(R['sky']), (n, 1)), lin(R['sky_hi']), smooth(0.2, 0.9, up) * 0.6)
    sky = _mix(sky, lin(R['sky_lo']), smooth(-0.1, -0.8, up) * 0.6)
    sky = _mix(sky, lin(R['sky_hi']), top * plate * 0.45 + flank * 0.3)
    crown = smooth(1.42, 1.48, co[:, 2])                                   # (round 3) the crown's feathers read
    sky = _mix(sky, lin(R['deep']), rim * plate * (0.22 + 0.2 * crown)) * (1.0 + (0.06 + 0.04 * crown) * jit)[:, None]
    wh = _mix(np.tile(lin(R['white']), (n, 1)), lin(R['white_lo']), smooth(0.0, -0.8, up) * 0.32 + rim * plate * 0.3)
    wh = _mix(wh, lin(R['white_hi']), top * plate * 0.5) * (1.0 + 0.025 * jit)[:, None]
    rgb = _mix(sky, wh, wm)
    # the legs: gold scutes with darker grooves and painted highlights; the claws grey horn
    ld, claw = leg_dist(co)
    # (round 3) a long blend from gold into the feathers at the drumstick's top (no hard 'sock' line)
    # (build 14) gold right up into the belly: the drumstick's top showed white under the trousers (a 'sock' line)
    leg = smooth(0.006, 0.0, ld) * smooth(0.68, 0.63, co[:, 2])
    gold = _mix(np.tile(lin(R['gold']), (n, 1)), lin(R['gold_hi']), smooth(0.3, 0.95, -vn[:, 1] * 0.6 + up * 0.5) * 0.45)
    gold = _mix(gold, lin(R['gold_lo']), I['scute'] * 0.7)
    rgb = _mix(rgb, gold, leg)
    cl = claw.astype(np.float64) * leg
    rgb = _mix(rgb, lin(R['claw']), cl)
    # the eye's surround: the closed lid under the lens (white, shaded), a navy lash line and the liner's flick
    e = I['eye']
    lid = smooth(1.08, 0.95, np.hypot(e[:, 0], e[:, 1])) * (np.abs(e[:, 2]) < 1.5)
    rgb = _mix(rgb, _mix(np.tile(lin(R['white']), (n, 1)), lin(R['white_lo']), smooth(0.2, -0.9, e[:, 1]) * 0.5), lid)
    rough = np.tile(np.array([1.0, 0.64, 0.04]), (n, 1))
    rough[:, 1] = np.where(wm > 0.5, 0.68, 0.6)
    rough[:, 1] = np.where(leg > 0.5, 0.42, rough[:, 1])
    rough[:, 2] = np.where(leg > 0.5, 0.22, rough[:, 2])
    rough[:, 1] = np.where(cl > 0.5, 0.34, rough[:, 1])
    return rgb, rough


def prop_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    R = roles(pal)
    n = len(I['pk'])
    pk, fk, fu, fv, fid = I['pk'], I['fk'], I['fu'], I['fv'], I['fid']
    vn = I['vn']
    up = vn[:, 2]
    jit = (fid - 0.5)
    rgb = np.tile(lin(R['sky']), (n, 1))
    # wing feathers: the flight feathers fade to white at their tips; the coverts sky, a lighter edge; the rachis light
    flight = (pk == 1) & (fk <= 1)
    tipk = np.where(flight, smooth(0.66, 1.0, fu) * np.where(fk == 1, 0.8, 0.65), 0.0)
    tipk = np.where(pk == 3, smooth(0.5, 0.97, fu) * 0.75, tipk)
    tipk = np.where(pk == 2, smooth(0.6, 1.0, fu) * 0.38, tipk)
    rgb = _mix(rgb, lin(R['sky_hi']), smooth(0.2, 0.9, up) * 0.35)
    rgb = _mix(rgb, lin(R['white']), tipk)
    vane = (pk <= 3) | (pk == 6)
    # (round 3) the wing's feathers shade along their tips (rows of scallops), not their sides (vertical ridges)
    wingf = (pk == 1) | (pk == 6)
    tip_sh = smooth(0.78, 0.97, fu) * smooth(1.0, 0.6, np.abs(fv)) * wingf
    rgb = _mix(rgb, lin(R['sky_lo']), tip_sh * 0.3 * (1 - tipk))
    edge = smooth(0.8, 0.98, np.abs(fv)) * ((pk == 2) | (pk == 3))
    rgb = _mix(rgb, lin(R['sky_lo']), edge * 0.15 * (1 - tipk))
    covert = (pk == 1) & (fk >= 2)
    rgb = np.where(covert[:, None], _mix(rgb, lin(R['deep']), 0.05), rgb)
    rgb = rgb * (1.0 + 0.04 * jit)[:, None]
    # the plumes' undersides as bright as their tops (round 2: a dark navy blot inside the crest from behind)
    under = ((pk == 2) | (pk == 3)) & (I['ftop'] < 0)
    rgb = np.where(under[:, None], _mix(rgb, lin(R['sky_hi']), 0.35), rgb)
    # the bib (round 3): white, a cool blue-grey toward the root, the tips the lightest
    bibm = pk == 7
    wb = _mix(np.tile(lin(R['white']), (n, 1)), lin(R['white_lo']), smooth(0.45, 0.0, fu) * 0.35)
    wb = _mix(wb, lin(R['white_hi']), smooth(0.6, 1.0, fu) * 0.5) * (1.0 + 0.03 * jit)[:, None]
    rgb = np.where(bibm[:, None], wb, rgb)
    # the beak: gold, the culmen lighter, the underside and the tip warmer and darker; the inside the mouth's colour
    bk = (pk == 4) | (pk == 5)
    g = _mix(np.tile(lin(R['gold']), (n, 1)), lin(R['gold_hi']), smooth(0.25, 0.95, up) * 0.55)
    g = _mix(g, lin(R['gold_lo']), smooth(-0.2, -0.9, up) * 0.45 + smooth(0.8, 1.0, I['bk_u']) * 0.25)
    g = _mix(g, lin(R['mouth']), I['bk_in'])
    rgb = np.where(bk[:, None], g, rgb)
    rough = np.tile(np.array([1.0, 0.6, 0.04]), (n, 1))
    rough[bk] = (1.0, 0.34, 0.32)
    rough[bk & (I['bk_in'] > 0.5)] = (1.0, 0.5, 0.08)
    return rgb, rough


def _get(ob, name: str, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(len(ob.data.vertices), d)


BODY_KEYS = ('plate', 'plate_rim', 'plate_top', 'scute')
PROP_KEYS = ('pk', 'fk', 'fu', 'fv', 'ftop', 'fid', 'side', 'bk_in', 'bk_u')


def body_inputs(ob) -> dict:
    co, vn = S.mesh_arrays(ob)
    I = {'co': co, 'vn': vn, **{k: _get(ob, k) for k in BODY_KEYS}, 'plate_id': _get(ob, 'plate_id', -1.0)}
    I['eye'] = eye_local(co)
    return I


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import galeheron_ultra as RC
    vid, vpal = next(iter(RC.VARIANTS.items()))
    from lib import ultra as U
    vattr = U.variant_attr(vid, RC.ID)
    for ob in body_srcs:
        I = body_inputs(ob)
        rgb, rough = body_paint(I, RC.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.set_colour_attr(ob, vattr, body_paint(I, vpal)[0])
    for ob in props:
        co, vn = S.mesh_arrays(ob)
        I = {'co': co, 'vn': vn, **{k: _get(ob, k) for k in PROP_KEYS}}
        rgb, rough = prop_paint(I, RC.PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.set_colour_attr(ob, vattr, prop_paint(I, vpal)[0])


# ----------------------------------------------------------------------------- per-pixel passes
def _seg(nb, P, a, b):
    """Distance from P (a node vector (0, y, z)) to the segment a-b in the y-z plane."""
    A = nb.comb(0.0, a[0], a[1])
    ab = (0.0, b[0] - a[0], b[1] - a[1])
    L2 = ab[1] ** 2 + ab[2] ** 2
    AP = nb.vmath('SUBTRACT', P, A)
    t = nb.math('MINIMUM', nb.math('MAXIMUM', nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', AP, ab), L2), 0.0), 1.0)
    proj = nb.vmath('SCALE', nb.comb(*ab), scale=t)
    return nb.vmath('LENGTH', nb.vmath('SUBTRACT', AP, proj)), t


def _spiral(nb, y, z, c, a: float, b: float, s0: float, s1: float, w0: float, w1: float):
    """A band along the arm r = a + b theta (theta unwrapped, s0..s1), w0 wide at s0 to w1 at s1."""
    dy = nb.math('SUBTRACT', y, c[0])
    dz = nb.math('SUBTRACT', z, c[1])
    r = nb.vmath('LENGTH', nb.comb(dy, dz, 0.0))
    th = nb.math('ARCTAN2', dz, dy)
    s = nb.math('DIVIDE', nb.math('SUBTRACT', r, a), b)
    f = nb.math('FRACT', nb.math('DIVIDE', nb.math('SUBTRACT', s, th), 2 * math.pi))
    da = nb.math('MULTIPLY', nb.math('MINIMUM', f, nb.math('SUBTRACT', 1.0, f)), 2 * math.pi * abs(b))
    # the arm's own parameter here: s rounded to the arm through this point
    k = nb.math('ROUND', nb.math('DIVIDE', nb.math('SUBTRACT', s, th), 2 * math.pi))
    sa = nb.math('ADD', th, nb.math('MULTIPLY', k, 2 * math.pi))
    u = nb.math('DIVIDE', nb.math('SUBTRACT', sa, s0), s1 - s0)
    w = nb.math('ADD', w0, nb.math('MULTIPLY', nb.math('MINIMUM', nb.math('MAXIMUM', u, 0.0), 1.0), w1 - w0))
    inside = nb.math('MULTIPLY', nb.smooth(u, -0.02, 0.01), nb.smooth(u, 1.02, 0.99))
    band = nb.math('LESS_THAN', da, w)
    soft = nb.smooth(nb.math('SUBTRACT', da, w), 0.0008, -0.0008)
    return nb.math('MULTIPLY', nb.math('MAXIMUM', band, soft), inside)


# the swirl on the folded wing (2-turnaround side, 1-hero): a big spiral high on the wing, a wave flowing back and down
# into a smaller spiral; a thin stroke above the wave. Coordinates (y, z) on the folded wing, mirrored for the right.
# (round 2) the glyph bigger and its bands two to three times thicker (solid, crisp: the hero), on the wing moved along
# the leaning back
SWIRL_A = ((0.03, 0.93), 0.022 - 0.0093 * 3.0 * math.pi, 0.0093, 3.0 * math.pi, 5.5 * math.pi)
WAVE = [(0.03, 0.835), (0.09, 0.81), (0.15, 0.815), (0.21, 0.84), (0.26, 0.85), (0.3, 0.83), (0.325, 0.785), (0.33, 0.715)]
SWIRL_B = ((0.265, 0.715), 0.065, 0.00716, -2.0 * math.pi, 0.0)
STROKE = [(0.19, 0.878), (0.25, 0.905), (0.31, 0.928), (0.37, 0.935)]


# (round 2) a swirl seen from behind (2-turnaround back view): on the folded wings' rear faces, in (|x|, z)
SWIRL_BACK = ((0.135, 0.85), 0.018 - 0.0083 * 3.0 * math.pi, 0.0083, 3.0 * math.pi, 5.5 * math.pi)
WAVE_BACK = [(0.135, 0.773), (0.115, 0.745), (0.1, 0.7), (0.1, 0.65), (0.11, 0.61)]


def swirl_back_mask(nb, pos):
    px, py, pz = nb.sep(pos)
    ax = nb.math('ABSOLUTE', px)
    P = nb.comb(0.0, ax, pz)
    c, a, b, s0, s1 = SWIRL_BACK
    m = _spiral(nb, ax, pz, c, a, b, s0, s1, 0.009, 0.014)
    for i in range(len(WAVE_BACK) - 1):
        d, t = _seg(nb, P, WAVE_BACK[i], WAVE_BACK[i + 1])
        w = 0.013 - 0.008 * (i + 1) / (len(WAVE_BACK) - 1)
        m = nb.math('MAXIMUM', m, nb.smooth(nb.math('SUBTRACT', d, w), 0.0008, -0.0008))
    return m


def swirl_mask(nb, pos):
    px, py, pz = nb.sep(pos)
    P = nb.comb(0.0, py, pz)
    (ca, aa, ba, s0a, s1a), (cb, ab_, bb, s0b, s1b) = SWIRL_A, SWIRL_B
    m = _spiral(nb, py, pz, ca, aa, ba, s0a, s1a, 0.012, 0.019)
    m = nb.math('MAXIMUM', m, _spiral(nb, py, pz, cb, ab_, bb, s0b, s1b, 0.011, 0.016))
    for pts, w0, w1 in ((WAVE, 0.018, 0.015), (STROKE, 0.0075, 0.002)):
        for i in range(len(pts) - 1):
            d, t = _seg(nb, P, pts[i], pts[i + 1])
            k0, k1 = i / (len(pts) - 1), (i + 1) / (len(pts) - 1)
            w = nb.math('ADD', w0 + (w1 - w0) * k0, nb.math('MULTIPLY', t, (w1 - w0) * (k1 - k0)))
            m = nb.math('MAXIMUM', m, nb.smooth(nb.math('SUBTRACT', d, w), 0.0008, -0.0008))
    return m


def _eye_xy(nb, pos):
    """The left eye's (across, up, out) for |x| in eye radii."""
    c, xa, ya, la = (tuple(v) for v in F.eye_frame(1))
    px, py, pz = nb.sep(pos)
    p = nb.vmath('SUBTRACT', nb.comb(nb.math('ABSOLUTE', px), py, pz), c)
    return (nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', p, xa), F.EYE_R * F.EYE_AX[0]),
            nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', p, ya), F.EYE_R * F.EYE_AX[1]),
            nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', p, la), F.EYE_R))


LASH_Y = -0.12            # the closed lid's lash line, in eye radii below the lens's centre


def lid_lines(nb, pos):
    """The closed eye's lash line (a gentle curve across the lens's footprint), the upper lid's liner round the lens
    and its flick back at the outer corner (1-hero, 3-faces, 4-details panel 2)."""
    ex, ey, ez = _eye_xy(nb, pos)
    near = nb.smooth(nb.math('ABSOLUTE', ez), 1.6, 1.1)
    # the lash line: y = LASH_Y + 0.22 x^2, across the footprint, tapering at the ends
    cy = nb.math('ADD', LASH_Y, nb.math('MULTIPLY', nb.math('MULTIPLY', ex, ex), 0.22))
    dist = nb.math('ABSOLUTE', nb.math('SUBTRACT', ey, cy))
    span = nb.smooth(nb.math('ABSOLUTE', ex), 1.02, 0.8)
    wl = nb.math('MULTIPLY', span, 0.075)
    lash = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', dist, wl), 0.012, -0.012), nb.math('MULTIPLY', near, span))
    # the liner: a ring just outside the lens over its upper half, thickening toward the back corner (+x) and flicking
    # out and up past it
    # (round 2) one strong line hugging the lens's upper edge (the upper lid's lashes), thickest toward the back
    rr = nb.vmath('LENGTH', nb.comb(ex, ey, 0.0))
    upper = nb.smooth(ey, 0.0, 0.3)
    wr = nb.math('ADD', 0.05, nb.math('MULTIPLY', nb.smooth(ex, -0.6, 1.0), 0.07))
    ring = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', nb.math('ABSOLUTE', nb.math('SUBTRACT', rr, 1.0 + 0.0)), wr), 0.012, -0.012),
                   nb.math('MULTIPLY', upper, near))
    # the flick: a tapering wedge from the back corner, out and a little up
    fx = nb.math('SUBTRACT', ex, 1.0)
    fy = nb.math('SUBTRACT', ey, nb.math('ADD', 0.2, nb.math('MULTIPLY', fx, 0.5)))
    fw = nb.math('MULTIPLY', nb.smooth(fx, 0.32, 0.0), 0.09)
    flick = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', nb.math('ABSOLUTE', fy), fw), 0.015, -0.015),
                                        nb.smooth(fx, -0.05, 0.02)), near)
    return nb.math('MAXIMUM', lash, nb.math('MAXIMUM', ring, flick))


def body_material(name: str, attr: str, pal: dict, marks):
    m, nb = new_mat(name)
    R = roles(pal)
    c = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    lines = lid_lines(nb, pos)
    c = nb.mix(lines, c, nb.rgb(C.lin(R['navy'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks):
    """The props' colour: their paint, the wind swirls on the wings' outer faces, fine barbs on every vane, the
    nostril slit on the upper mandible."""
    m, nb = new_mat(name)
    R = roles(pal)
    c = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    pk = nb.attribute('pk').outputs['Fac']
    wing = nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', pk, 1.0)), 0.4, 0.2)
    outer = nb.smooth(nb.attribute('ftop').outputs['Fac'], 0.2, 0.6)
    # the side swirls on faces turned out to the side, the back swirl on faces turned back (wings and back feathers)
    nrm = nb.new('ShaderNodeNewGeometry').outputs['Normal']
    nx_, ny_, _nz = nb.sep(nrm)
    side_f = nb.smooth(nb.math('SUBTRACT', nb.math('ABSOLUTE', nx_), nb.math('MULTIPLY', ny_, 0.9)), -0.1, 0.1)
    back_f = nb.math('SUBTRACT', 1.0, side_f)
    feather = wing                      # (polish) not the scapulars: seen edge-on along the back they read as navy hairlines
    sw = nb.math('MULTIPLY', swirl_mask(nb, pos), nb.math('MULTIPLY', nb.math('MULTIPLY', wing, outer), side_f))
    sb = nb.math('MULTIPLY', swirl_back_mask(nb, pos), nb.math('MULTIPLY', nb.math('MULTIPLY', feather, outer), back_f))
    c = nb.mix(nb.math('MAXIMUM', sw, sb), c, nb.rgb(C.lin(R['deep'])))
    # barbs: fine slanted lines across each vane (both faces), stronger toward the edges
    fu = nb.attribute('fu').outputs['Fac']
    fv = nb.attribute('fv').outputs['Fac']
    fid = nb.attribute('fid').outputs['Fac']
    vane = nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', pk, 4.5)), 0.4, 0.6)
    ph = nb.math('ADD', nb.math('MULTIPLY', fu, 150.0), nb.math('MULTIPLY', nb.math('ABSOLUTE', fv), 9.0))
    ph = nb.math('ADD', ph, nb.math('MULTIPLY', fid, 40.0))
    barb = nb.math('MULTIPLY', nb.smooth(nb.math('SINE', ph), 0.55, 1.0), nb.smooth(nb.math('ABSOLUTE', fv), 0.1, 0.5))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', barb, vane), 0.06), c, nb.rgb(C.lin(R['white'])))
    # (round 3) a visible shaft down every plume (light on the blue ones, a cool grey on the white bib)
    shaft = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', fv), 0.09, 0.03), nb.math('MULTIPLY', nb.smooth(fu, 0.02, 0.12), nb.smooth(fu, 0.96, 0.86)))
    plumeish = nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', pk, 2.5)), 0.7, 0.5)
    bibish = nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', pk, 7.0)), 0.4, 0.2)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', shaft, plumeish), 0.5), c, nb.rgb(C.lin(R['sky_hi'])))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', shaft, bibish), 0.35), c, nb.rgb(C.lin(R['white_lo'])))
    # the swirls again on top: solid, unbroken by the barbs
    c = nb.mix(nb.math('MAXIMUM', sw, sb), c, nb.rgb(C.lin(R['deep'])))
    # the nostril: a short dark slit on each side of the upper mandible near its base
    bu = nb.attribute('bk_u').outputs['Fac']
    up4 = nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', pk, 4.0)), 0.4, 0.2)
    bv = nb.attribute('fv').outputs['Fac']
    slit = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(bu, 0.17, 0.2), nb.smooth(bu, 0.33, 0.29)),
                   nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', nb.math('ABSOLUTE', bv), 0.62)), 0.07, 0.03))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', slit, up4), 0.8), c, nb.rgb(C.lin(R['gold_lo'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- eyes
def eye_material(name: str, rough_pass: bool = False):
    """A big gold iris (a darker rim, lighter round the pupil, fine streaks), a navy pupil, a thin pale sclera at the
    lens's edge, two catchlights (4-details panel 2). The iris sits a little toward the front of the lens: the eyes
    look ahead."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, 0.06, 0.9), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    R = roles(BASE)
    e = nb.attribute('eyeuv').outputs['Vector']
    rx, ry, _z = nb.sep(e)
    # (round 2) the almond lens: eyeuv's unit circle is the lens's outline (1.25 x 0.8 eye radii); the iris is round on
    # the lens (0.72 eye radii), a little toward the front, its top just under the upper lid's dark band
    # (polish) a smaller iris (0.62 eye radii) that never touches the lens's outline, so it stays round from the front
    ix = nb.math('MULTIPLY', nb.math('ADD', rx, 0.08), F.EYE_AX[0] / 0.62)
    iy = nb.math('MULTIPLY', nb.math('ADD', ry, 0.02), F.EYE_AX[1] / 0.62)
    ri = nb.vmath('LENGTH', nb.comb(ix, iy, 0.0))
    gold = R['gold']
    navy = C.shade_hex(BASE['accent'], 0.18)
    k = 1.0 / 2.4
    col = nb.ramp(nb.math('MULTIPLY', ri, k), [(0.0, C.lin(navy)), (0.36 * k, C.lin(navy)), (0.41 * k, C.lin(C.shade_hex(gold, 0.55))),
                                               (0.5 * k, C.lin(C.mix_hex(gold, '#FFFFFF', 0.28))), (0.76 * k, C.lin(gold)),
                                               (0.92 * k, C.lin(C.shade_hex(gold, 0.7))), (0.98 * k, C.lin(C.shade_hex(gold, 0.42))),
                                               (1.04 * k, C.lin('#F1F2F5')), (1.7 * k, C.lin('#E4E8EF')), (1.0, C.lin('#CBD2DD'))])
    ang = nb.math('ARCTAN2', iy, ix)
    streak = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 27.0)), 0.5), 0.5),
                     nb.math('MULTIPLY', nb.smooth(ri, 0.42, 0.5), nb.smooth(ri, 0.95, 0.85)))
    col = nb.mix(nb.math('MULTIPLY', streak, 0.18), col, nb.rgb(C.lin(C.shade_hex(gold, 0.78))))
    # the upper lid: its shadow over the iris, then a dark lash band along the lens's top edge (the haughty lid line)
    shade = nb.math('MULTIPLY', nb.smooth(ry, 0.3, 0.8), 0.3)
    col = nb.mix(shade, col, nb.rgb(C.lin('#7A6030')), blend='MULTIPLY')
    edge = nb.math('SQRT', nb.math('MAXIMUM', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', rx, rx)), 0.0))
    lid = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', edge, ry), 0.2, 0.13), nb.smooth(ry, -0.2, 0.2))
    col = nb.mix(lid, col, nb.rgb(C.lin(navy)))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.3), nb.math('SUBTRACT', ry, 0.38), 0.0)), 0.13, 0.08)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.12), nb.math('ADD', ry, 0.32), 0.0)), 0.06, 0.03)
    col = nb.mix(nb.math('MAXIMUM', big, nb.math('MULTIPLY', small, 0.85)), col, nb.rgb((1.0, 1.0, 1.0)))
    em = nb.new('ShaderNodeEmission')
    nb.link(col, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the shape preview
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import galeheron_ultra as RC
    n = len(co)
    vn = vn if vn is not None else np.tile((0.0, 0.0, 1.0), (n, 1))
    I = {'co': co, 'vn': vn, 'plate': np.zeros(n), 'plate_rim': np.zeros(n), 'plate_top': np.zeros(n), 'scute': np.zeros(n),
         'plate_id': np.full(n, -1.0), 'eye': eye_local(co)}
    return body_paint(I, RC.PALETTE)[0]
