"""Paladove's paint (young and grown; Art 2.1 Ultra): soft feathered white that never reads as paper or chalk (warm lock
roots, bright tips toward the sky, a faint cool shade underneath, the feather rows' fine warm outlines), gold with its
highlights painted in (the film renderer keeps roughness >= 0.3 and reflects a soft grey studio: unpainted gold reads
dark and matte), and the face: blush, brows, the closed lids under the lenses, the mouth.

Colours are CONTENT's: #F7F4EE, #FFFFFF, #E3B448, #4A6FA5. The palette can't mix a pink, so the blush and the mouth are
the gold turned toward red (a hue turn of the palette's gold) and softened with the white; the lashes are the eye blue
darkened; the brows and claws are the white mixed with the gold.
"""
from __future__ import annotations

import colorsys

import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import paladove_parts as PP

WHITE, HI, GOLD, EYE = PP.WHITE, PP.HI, PP.GOLD, PP.EYE


def _turn(h: str, deg: float, sat: float = 1.0, val: float = 1.0) -> str:
    r, g, b = C.srgb(h)
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    r2, g2, b2 = colorsys.hsv_to_rgb((hh + deg / 360.0) % 1.0, min(1.0, ss * sat), min(1.0, vv * val))
    return '#%02X%02X%02X' % tuple(int(round(255 * c)) for c in (r2, g2, b2))


BLUSH = C.mix_hex(_turn(GOLD, -30.0, 0.85), WHITE, 0.5)       # a soft peach-pink
MOUTH = _turn(GOLD, -38.0, 0.62, 0.8)                           # a rose mouth
TONGUE = C.mix_hex(_turn(GOLD, -34.0, 0.55, 0.95), WHITE, 0.25)
LASH = C.shade_hex(EYE, 0.22)
BROW = C.shade_hex(C.mix_hex(WHITE, GOLD, 0.5), 0.82)
CLAW = C.mix_hex(WHITE, GOLD, 0.22)
WARM = C.shade_hex(C.mix_hex(WHITE, GOLD, 0.17), 0.95)          # the down's roots and creases
COOL = C.shade_hex(C.mix_hex(WHITE, EYE, 0.1), 0.93)            # the underside's faint cool shade
EDGE = C.shade_hex(C.mix_hex(WHITE, GOLD, 0.24), 0.91)          # a feather's fine outline (build 3: softer, warmer)
SHAFT = C.shade_hex(C.mix_hex(WHITE, GOLD, 0.15), 0.9)
GOLD_HI = C.mix_hex(GOLD, HI, 0.42)
GOLD_LO = C.shade_hex(_turn(GOLD, -6.0), 0.72)


def L(h: str) -> np.ndarray:
    return PP.lin(h)


def _mix(rgb: np.ndarray, k, h) -> np.ndarray:
    k = np.clip(np.asarray(k, np.float64), 0.0, 1.0)
    if k.ndim == 0:
        k = np.full(len(rgb), float(k))
    c = L(h) if isinstance(h, str) else np.asarray(h)
    return rgb * (1.0 - k[:, None]) + (c[None] if c.ndim == 1 else c) * k[:, None]


UNDER = C.shade_hex(C.mix_hex(WHITE, GOLD, 0.13), 0.95)       # round 1: the shade under the down is warm cream


def plumage_light(rgb: np.ndarray, vn: np.ndarray, top: float = 0.6, under: float = 0.32) -> np.ndarray:
    """Bright toward the sky, a faint cool shade underneath (the soft studio's own light, painted in so the whites keep
    their form in the game's capped light)."""
    nz = vn[:, 2]
    rgb = _mix(rgb, smooth(0.1, 0.9, nz) * top, HI)
    return _mix(rgb, smooth(-0.1, -0.85, nz) * under, UNDER)


def face_paint(co: np.ndarray, rgb: np.ndarray, eye_frame, eye_r: float, lash_v: float, scale: float = 1.0, brows: bool = True):
    """Blush, brows and the closed lids (under each lens: a soft lid and a curved dark lash line, shown when the lens
    blinks shut), on any source by position."""
    lid = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - c[None]
        u = (q @ xax) / eye_r
        v = (q @ yax) / eye_r
        w = q @ look
        near = np.abs(w) < 0.03 * scale
        out = u * s                                    # + toward the face's outside
        rho = np.hypot(u, v)
        # the lid: faintly warmer than the down, inside the lens's footprint
        lidk = smooth(1.08, 0.9, rho) * near * smooth(lash_v - 0.25, lash_v + 0.05, v)
        rgb = _mix(rgb, 0.0 * lidk, WARM)          # round 1: the shut lid is the face's own down
        # the lash line: a curve bowing down (3-faces blink, sleepy), thicker toward the outer corner
        v_arc = lash_v - 0.16 * (1.0 - (u / 0.78) ** 2)
        thick = 0.05 + 0.025 * smooth(-0.2, 0.7, out)
        line = smooth(thick + 0.03, thick, np.abs(v - v_arc)) * smooth(0.8, 0.7, np.abs(u)) * near
        # a little flick of lashes at the outer corner
        flick = smooth(0.06, 0.03, np.abs(v - (v_arc + 0.35 * (out - 0.55)))) * smooth(0.5, 0.6, out) * smooth(0.82, 0.72, out) * near
        rgb = _mix(rgb, np.maximum(line, flick), LASH)
        lid = np.maximum(lid, np.maximum(line, flick))
        # a faint warm brow above the eye, higher toward the outside
        v_b = 1.62 + 0.12 * (1.0 - u ** 2) + 0.24 * out
        brow = smooth(0.13, 0.06, np.abs(v - v_b)) * smooth(0.8, 0.6, np.abs(u - 0.05 * s)) * (np.abs(w) < 0.05 * scale)
        if brows:
            rgb = _mix(rgb, 0.45 * brow, BROW)
        # the blush on the cheek, below and outside the eye
        cb = c + yax * (-0.07 * scale) + xax * (0.03 * s * scale) - look * 0.004
        d = np.linalg.norm(co - cb[None], axis=1)
        rgb = _mix(rgb, 0.62 * smooth(0.048 * scale, 0.012 * scale, d), BLUSH)
    return rgb, lid


def body_colours(co, vn, tpos, lrand, eye_frame, young: bool = True, eye_r: float = 0.046, lash_v: float = -0.12,
                 mouth_at=(0.0, -0.236, 0.5), scale: float = 1.0, crest=None, brows: bool = True):
    """The down's colour, roughness and coat per point (the body and its lying locks)."""
    n = len(co)
    rgb = np.tile(L(WHITE), (n, 1))
    rgb = plumage_light(rgb, vn)
    if tpos is not None:
        rgb = _mix(rgb, 0.32 * (1.0 - tpos) ** 2, WARM)
        rgb = _mix(rgb, 0.7 * smooth(0.45, 1.0, tpos), HI)
        rgb = rgb * (0.975 + 0.05 * lrand)[:, None]
    else:
        rgb = _mix(rgb, 0.22, WARM)
    rgb, lid = face_paint(co, rgb, eye_frame, eye_r, lash_v, scale, brows)
    if crest is not None:
        # the crest's curls: brighter and a touch warmer than the down (they read grey-silver in the close-ups)
        ck = crest(co).astype(float)
        rgb = _mix(rgb, 0.55 * ck, C.mix_hex(HI, GOLD, 0.06))
    # the mouth: a small rose patch at the beak's root, between its halves (shows when the beak opens)
    m = np.asarray(mouth_at)
    mk = smooth(0.03 * scale, 0.018 * scale, np.hypot(co[:, 0] - m[0], (co[:, 2] - m[2]) * 1.8)) * (co[:, 1] < m[1] + 0.03 * scale)
    rgb = _mix(rgb, mk, MOUTH)
    rough = np.full(n, 0.8)
    rough = np.where(lid > 0.3, 0.6, rough)
    rough = np.where(mk > 0.5, 0.45, rough)
    coat = np.where(mk > 0.5, 0.25, 0.0)
    return rgb, rough, coat


def _put(ob, rgb, rough, coat, glow=None) -> None:
    S.set_colour_attr(ob, 'paint', rgb)
    S.set_colour_attr(ob, 'rough', np.stack([np.ones(len(rgb)), rough, coat], axis=1))
    if glow is not None:
        S.add_attr(ob, 'glow', glow)


def _normals(ob) -> np.ndarray:
    me = ob.data
    vn = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('normal', vn)
    return vn.reshape(-1, 3)


def gold_paint(co, vn, kind: str, axis=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gold with its light painted in: a pale highlight toward the sky, a deeper orange underneath; the tarsus and
    toes get scutes (darker grooves), the claws are pale."""
    n = len(co)
    nz = vn[:, 2]
    rgb = np.tile(L(GOLD), (n, 1))
    rgb = _mix(rgb, 0.75 * smooth(0.15, 0.95, nz), GOLD_HI)
    rgb = _mix(rgb, 0.55 * smooth(-0.1, -0.9, nz), GOLD_LO)
    rough = np.full(n, 0.42)
    coat = np.full(n, 0.35)
    if kind == 'scaly' and axis is not None:
        a, b = v3(axis[0]), v3(axis[1])
        t = ((co - a) @ (b - a)) / max(float((b - a) @ (b - a)), 1e-9)
        groove = smooth(0.82, 0.97, np.cos(2 * np.pi * 6 * t))
        rgb = _mix(rgb, 0.45 * groove, GOLD_LO)
        rough = np.full(n, 0.5)
        coat = np.full(n, 0.2)
    if kind == 'claw':
        rgb = np.tile(L(CLAW), (n, 1))
        rgb = _mix(rgb, 0.4 * smooth(0.1, 0.9, nz), HI)
        rough = np.full(n, 0.4)
        coat = np.full(n, 0.3)
    if kind == 'halo':
        rough = np.full(n, 0.32)
        coat = np.full(n, 0.45)
    return rgb, rough, coat


def feather_paint(co, vn, feathers, plane_n, seed: int = 0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # build 3: the props' feathers read cooler and harder than the down (no fur sheen on props): a warmer base,
    # a lighter cool shade underneath
    base = L(C.mix_hex(WHITE, GOLD, 0.07))
    rgb, _ed = PP.wing_paint(co, vn, feathers, v3(plane_n)[None], base, L(HI), L(EDGE), L(SHAFT), seed)
    rgb = _mix(rgb, 0.22 * PP.feather_groove(co, vn, feathers, plane_n), EDGE)
    rgb = plumage_light(rgb, vn, top=0.3, under=0.12)
    return rgb, np.full(len(co), 0.78), np.zeros(len(co))


def paint_young(body_srcs, props=()) -> None:
    from monsters.breeds import paladove_ultra as R
    for ob in body_srcs:
        co, _ = S.mesh_arrays(ob)
        vn = _normals(ob)
        has_t = 'tpos' in ob.data.attributes and ob.name != 'hi_body'
        tpos = S.attr_array(ob, 'tpos') if has_t else None
        lr = S.attr_array(ob, 'lrand') if has_t else None
        rgb, rough, coat = body_colours(co, vn, tpos, lr, R.eye_frame, True, R.EYE_R, R.LASH_V, crest=R.crest_zone)
        _put(ob, rgb, rough, coat)
    for ob in props:
        co, _ = S.mesh_arrays(ob)
        vn = _normals(ob)
        pk = int(round(float(S.attr_array(ob, 'pk')[0])))
        ps = float(S.attr_array(ob, 'ps')[0])
        claw = 'claw' in ob.data.attributes
        glow = None
        if pk == R.PK_WING:
            s = 1 if ps > 0 else -1
            rgb, rough, coat = feather_paint(co, vn, R.wing_feathers(s), PP.mirror(R._NW, s), seed=3 + s)
        elif pk == R.PK_TAIL:
            rgb, rough, coat = feather_paint(co, vn, R.tail_feathers(), (0.0, 1.0, -0.3), seed=11)
        elif pk == R.PK_CREST:
            rgb, rough, coat = feather_paint(co, vn, R.crest_feathers(), (0.0, -1.0, 0.0), seed=17)
            rgb = _mix(rgb, 0.2 + 0.35 * smooth(0.72, 0.8, co[:, 2]), C.mix_hex(HI, GOLD, 0.05))
        elif claw:
            rgb, rough, coat = gold_paint(co, vn, 'claw')
        elif pk == R.PK_TARSUS and 'tarsus' in ob.name:
            lg = {k: PP.mirror(v, 1 if ps > 0 else -1) for k, v in R.LEG.items()}
            rgb, rough, coat = gold_paint(co, vn, 'scaly', (lg['ankle'], lg['toe']))
        elif pk in (R.PK_TARSUS, R.PK_TOE, R.PK_SHIN):
            rgb, rough, coat = gold_paint(co, vn, 'scaly', None)
        elif pk == R.PK_HALO:
            rgb, rough, coat = gold_paint(co, vn, 'halo')
            glow = np.full(len(co), 0.62)
        else:          # the beak's halves: gold outside, the mouth's rose inside
            rgb, rough, coat = gold_paint(co, vn, 'beak')
            inner = co[:, 1] > -0.284
            if pk == R.PK_BEAK:
                mk = smooth(-0.35, -0.75, vn[:, 2]) * inner * (co[:, 2] < 0.512)
                rgb = _mix(rgb, mk, MOUTH)
            else:
                mk = smooth(0.35, 0.75, vn[:, 2]) * inner * (co[:, 2] > 0.494)
                rgb = _mix(rgb, mk, TONGUE)
            rough = np.where(mk > 0.5, 0.45, rough)
        _put(ob, rgb, rough, coat, glow)
