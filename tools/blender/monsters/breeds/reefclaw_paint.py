"""Reefclaw's paint (Art 2.1 Ultra): per-vertex colour, roughness/coat and the Abyss variant's glow, for the high body and
every high prop. Colours come from the palette (CONTENT 18 and src/art/monster/variants.ts); every other tone is derived
from them (CONTENT has no hex for tubercles, pores, the mouth, the lid or the visor windows).

Gloss is painted into the colour (lesson: the film renderer floors roughness at 0.3 against a grey studio), so the shell
carries lit tops, darker lower edges and pale tubercles rather than relying on a specular streak. No value-noise lattice
in the paint (it turns into blocky KTX2 squares): Voronoi spots and smooth gradients only.
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import reefclaw_bits as B
from monsters.breeds import reefclaw_form as F


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def colours(pal: dict) -> dict:
    body, belly, acc = pal['body'], pal['belly'], pal['accent']
    shadow = pal.get('shell') or C.shade_hex(body, 0.62, cool=0.02)
    return {
        'coral': body, 'coral_hi': C.mix_hex(body, belly, 0.3), 'coral_lo': C.mix_hex(body, shadow, 0.6), 'shadow': shadow,
        'deep': C.shade_hex(shadow, 0.5), 'pale': C.mix_hex(belly, '#FFFFFF', 0.3), 'peach': belly,
        'peach_dk': C.shade_hex(belly, 0.8), 'peach_warm': C.mix_hex(belly, body, 0.38),
        'barn': acc, 'barn_dk': C.shade_hex(acc, 0.66, cool=0.02), 'barn_deep': C.shade_hex(acc, 0.36, cool=0.03),
        'barn_pale': C.mix_hex(acc, '#FFFFFF', 0.45),
        'mouth': pal.get('mouth') or C.shade_hex(shadow, 0.4), 'dact': C.mix_hex(shadow, body, 0.25), 'lid': C.mix_hex(body, belly, 0.5),
        'window': C.shade_hex(shadow, 0.32), 'tip': pal.get('tip') or C.mix_hex(belly, '#FFFFFF', 0.12),
        'spot': pal.get('spot') or acc,
    }


def _mixc(rgb: np.ndarray, k: np.ndarray, col) -> np.ndarray:
    k = np.clip(k, 0.0, 1.0)[:, None]
    return rgb * (1 - k) + (lin(col)[None] if isinstance(col, str) else col) * k


def _get(ob, name: str, n: int, d: float = 0.0) -> np.ndarray:
    return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(n, d)


def body_paint(co: np.ndarray, m: dict, pal: dict) -> dict:
    """co: the uncarved positions ('root'); m: the carve's masks. Returns paint, rough and the glow spots."""
    c = colours(pal)
    n = len(co)
    z = co[:, 2]
    zr = F.rim_z(F.phi_of(co))
    top = smooth(0.48, 0.8, z)
    rgb = np.tile(lin(c['coral']), (n, 1)) * (0.94 + 0.1 * top)[:, None]
    rgb = _mixc(rgb, 0.4 * top, c['coral_hi'])
    rgb = _mixc(rgb, 0.55 * smooth(zr + 0.09, zr + 0.01, z), c['coral_lo'])
    rgb = _mixc(rgb, 0.45 * m['lip'], c['coral_hi'])
    rgb = _mixc(rgb, 0.75 * m['under'], c['shadow'])
    rgb = _mixc(rgb, 0.85 * smooth(0.45, 1.0, m['spike']), c['pale'])
    rgb = _mixc(rgb, 0.3 * smooth(0.0, 0.3, m['spike']) * (1 - smooth(0.45, 1.0, m['spike'])), c['coral_hi'])
    rgb = _mixc(rgb, 0.8 * smooth(0.25, 0.85, m['knob']), c['pale'])
    rgb = _mixc(rgb, 0.45 * smooth(0.25, 0.85, m.get('peb', np.zeros(n))), c['coral_hi'])  # every pebble's crown lit
    rgb = _mixc(rgb, 0.9 * smooth(0.55, 0.92, m['tuber']), c['pale'])                      # pale only on the tips
    rgb = _mixc(rgb, 0.55 * m['pit'], c['deep'])
    rgb = _mixc(rgb, 0.3 * m['ridge'], c['coral_hi'])
    rgb = _mixc(rgb, 0.9 * m['socket'], c['deep'])
    rgb = _mixc(rgb, m['mouth'], c['mouth'])
    # under the lip: the peach plastron (plates lighter in the middle, the grooves darker) and the warmer underside
    # round 3 (review: the belly was the brightest shape): a warmer, calmer peach, the plates' grooves darker
    # polish (review: grey-pink in shade, a dirty egg): the card's peach itself, a touch warmer in its shade, lighter
    # grooves (the AO floor rose too)
    bel = np.tile(lin(C.mix_hex(c['peach'], '#FFC9AE', 0.3)), (n, 1)) * (0.98 + 0.04 * m['plate'])[:, None]
    bel = _mixc(bel, 0.7 * m['groove'], c['peach_dk'])
    side = smooth(-0.12, 0.05, co[:, 1]) + smooth(0.2, 0.27, np.abs(co[:, 0]))
    bel = _mixc(bel, 0.4 * np.clip(side, 0, 1) + 0.2 * smooth(0.24, 0.16, z), c['peach_warm'])
    bel = _mixc(bel, 0.5 * smooth(zr - 0.03, zr, z), c['peach_warm'])
    sh = np.clip(m['shell'], 0, 1)[:, None]
    rgb = rgb * sh + bel * (1 - sh)
    # round 2 (review: a wetter, glossier shell): the full clearcoat the runtime allows on the carapace
    rough = np.stack([np.ones(n), 0.3 + 0.06 * (1 - sh[:, 0]) + 0.25 * m['pit'] + 0.2 * m['mouth'] + 0.2 * m['socket'],
                      0.5 * sh[:, 0] + 0.35 * (1 - sh[:, 0]) - 0.3 * m['pit']], axis=1)
    spots, _ = F.bumps(co, 0.035, 91, (0.007, 0.012), 0.7)
    calm = (1 - m['socket']) * (1 - m['mouth']) * (1 - smooth(0.05, 0.25, m['spike'])) * (1 - m['lip']) * (1 - m['under'])
    glow = np.clip(smooth(0.2, 0.6, spots) * (sh[:, 0] > 0.5) * calm, 0, 1)
    return {'paint': np.clip(rgb, 0, 1), 'rough': np.clip(rough, 0, 1), 'spots': glow}


def prop_paint(ob, pal: dict) -> dict:
    """Every high prop by its kind: 0 legs, 1 arms and claws (coral on the big one), 2 barnacles, 3 stalks, 4 cups and
    lid balls, 5 visors."""
    c = colours(pal)
    co, vn = S.mesh_arrays(ob)
    n = len(co)
    kind = int(round(float(_get(ob, 'kind', n)[0])))
    g = {k: _get(ob, k, n) for k in ('tuber', 'under', 'joint', 'tip', 'coral', 'pore', 'ctip', 'ccap', 'tooth', 'crater', 'rib',
                                     'pgap', 'brim', 'bh', 'along', 'lid', 'win')}
    up = vn[:, 2]
    rgb = np.tile(lin(c['coral']), (n, 1))
    rough = np.tile(np.array([1.0, 0.3, 0.45]), (n, 1))
    glow = np.zeros(n)
    spots, _ = F.bumps(co + 0.5, 0.03, 93, (0.006, 0.012), 0.7)
    if kind in (0, 1, 3, 4, 5):
        rgb = rgb * (0.95 + 0.08 * smooth(-0.3, 0.8, up))[:, None]
        rgb = _mixc(rgb, 0.3 * smooth(0.0, 0.9, up), c['coral_hi'])
        rgb = _mixc(rgb, 0.6 * g['under'], c['peach_warm'])
        rgb = _mixc(rgb, 0.85 * smooth(0.25, 0.75, g['tuber']), c['pale'])
        rgb = _mixc(rgb, 0.25 * g['joint'], c['coral_lo'])
        glow = smooth(0.2, 0.6, spots) * (1 - g['under'])
    if kind == 0:
        rgb = _mixc(rgb, 0.92 * g['tip'], c['shadow'])        # round 3: the long dactyl in the shell shadow
        rough[:, 2] += 0.2 * g['tip']
    if kind == 1:
        rgb = _mixc(rgb, 0.8 * g['tip'], c['tip'])
        rgb = _mixc(rgb, 0.85 * g['tooth'], c['pale'])
        # the coral: a pinker coral, deep pores, the fronds paling to round knobbed tips
        cor = np.tile(lin(c['coral']), (n, 1)) * (0.98 + 0.06 * up)[:, None]
        cor = _mixc(cor, 0.85 * g['ctip'], c['tip'])
        cor = _mixc(cor, 0.12 * g['pore'], c['shadow'])        # the pits are carved: the AO darkens them, not paint
        rgb = _mixc(rgb, g['coral'], cor)
        rough[:, 1] += 0.22 * g['coral']
        rough[:, 2] -= 0.3 * g['coral']
        glow = np.maximum(glow * (1 - g['coral']), g['ccap'])
    if kind == 2:
        # round 3 (review: still grey-teal): lighter plates, ribs and rims
        rgb = np.tile(lin(C.mix_hex(c['barn'], '#FFFFFF', 0.26)), (n, 1))       # polish: lighter still, rims pale
        rgb = _mixc(rgb, 0.16 * g['pgap'], c['barn_dk'])
        rgb = _mixc(rgb, 0.07 * g['rib'], c['barn_dk'])
        rgb = _mixc(rgb, 0.9 * g['brim'], c['barn_pale'])
        rgb = _mixc(rgb, 0.12 * smooth(0.4, 0.0, g['bh']) * (1 - g['crater']), c['barn_dk'])
        rgb = _mixc(rgb, g['crater'] * 0.55 * smooth(0.86, 0.76, g['bh']), c['barn_dk'])    # only the opening dark
        f1, _f2, h = F.cells(co, 0.006, 97)
        rgb = _mixc(rgb, 0.55 * smooth(0.0016, 0.0008, f1) * (h < 0.35), c['shadow'])
        rough = np.tile(np.array([1.0, 0.58, 0.08]), (n, 1))
    if kind == 3:
        rgb = _mixc(rgb, 0.35 * smooth(0.35, 0.0, g['along']), c['coral_lo'])
    if kind == 4:
        lid = g['lid']
        s = np.where(co[:, 0] >= 0, 1, -1)
        lidc = np.tile(lin(c['lid']), (n, 1))
        for side in (1, -1):
            on = (s == side) & (lid > 0.5)
            if not on.any():
                continue
            ce, xa, u, d = B.eye_frame(side)
            p = co[on] - ce
            yl = (p @ u) / B.EYE_R
            xl = (p @ xa) / B.EYE_R
            front = smooth(-0.1, 0.25, (p @ d) / B.EYE_R)
            lash = np.exp(-((yl + 0.06 - 0.18 * xl ** 2) / 0.07) ** 2) * front
            lidc[on] = _mixc(lidc[on], 0.95 * lash, c['mouth'])
            lidc[on] = _mixc(lidc[on], 0.25 * smooth(0.0, -0.6, yl), c['peach_warm'])
        rgb = _mixc(rgb, lid, lidc)
        glow *= 1 - lid
    if kind == 6:                                             # the arm sockets' shell collars
        rgb = _mixc(rgb, 0.4 * _get(ob, 'rim', n), c['coral_hi'])
        rgb = _mixc(rgb, 0.6 * _get(ob, 'inner', n), c['coral_lo'])
    if kind == 5:
        rgb = _mixc(rgb, 0.55 * smooth(0.012, 0.0, _visor_h(co)), c['coral_hi'])
        rgb = _mixc(rgb, 0.5 * smooth(0.0, 0.6, g['win']), c['coral_lo'])
        rgb = _mixc(rgb, 0.95 * smooth(0.6, 0.95, g['win']), c['window'])
        glow = np.maximum(glow, 0.8 * g['win'])
    return {'paint': np.clip(rgb, 0, 1), 'rough': np.clip(rough, 0, 1), 'glow': np.clip(glow, 0, 1)}


def _visor_h(co: np.ndarray) -> np.ndarray:
    """Height along each visor's axis above its brim (metres): the brim's roll paler."""
    out = np.full(len(co), 1.0)
    for s in (1, -1):
        o, ax = B.visor_frame(s)
        on = np.sign(co[:, 0]) == s
        out[on] = (co[on] - o) @ ax
    return out
