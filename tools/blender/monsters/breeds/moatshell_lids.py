"""Moatshell's heavy upper lids (Art 2.1 Ultra): a thin skin shell over the top third of each lens, its lower edge the
lash line (1-hero, 3-faces neutral, 4-details panel 2: sleepy, half-lidded). They are props rigid on `head`, so their
colour comes from the props' atlas of each look: Porcelain's lids are china white. (Painted on the lens they took the
base look's sandstone in every look, since the game keeps the base atlas on the eyes when a variant's eye colour is the
same.) Their far sides tuck under the sculpted lid fold round each eye (moatshell_skin.lid_fold).

Attributes: ck 9 (the paint's kind), w2 (0 at the lash line → 1 at the top), cpart 0, tk (the texel share).
"""
from __future__ import annotations

import numpy as np

from monsters.breeds import moatshell_geo as G
from monsters.breeds import moatshell_noise as N
from monsters.breeds import moatshell_ultra as R

CK_LID = 9.0
OFFSET = 0.0007          # in front of the lens: seated on it (2.4 mm, then 1.2 mm, read as a visor in profile)
THICK = 0.002            # at the fold; the lash edge tapers to 0.8 mm


def edge(rx: np.ndarray, s: int) -> np.ndarray:
    """The lid's edge on the lens (ry in the lens's units for rx across): the same arc eye_material paints."""
    r = np.clip(rx, -1.0, 1.0)
    # round 1: drooping at the outer corner (kindly and sleepy, not a level bar), a touch higher at the inner one
    return 0.30 + 0.17 * (1.0 - r * r) - 0.22 * N.smooth(0.15, 1.0, r * s) + 0.03 * N.smooth(0.0, 0.9, -r * s)


def lid_piece(s: int, high: bool) -> dict:
    c, xax, yax, look = (np.array(v, np.float64) for v in R.eye_frame(s))
    Rr, b, dp = R.EYE_R, R.EYE_SHAPE[1], R.EYE_DEPTH
    c0 = c - look * (Rr * dp[1])
    nu, nv = (72, 24) if high else (14, 5)
    # a cap over the lens's top only: from the lash line up to just past the lens's outline, where it dives back under
    # the sculpted fold (a rectangle reaching past the eye stood out like a slab)
    uu, vv = np.meshgrid(np.linspace(-1.03, 1.03, nu + 1), np.linspace(0.0, 1.0, nv + 1), indexing='ij')
    ry0 = edge(uu, s)
    top = np.maximum(ry0 + 0.06, np.sqrt(np.clip(1.12 ** 2 - uu * uu, 0.0, None)))
    ry = ry0 + vv * (top - ry0)
    rr = np.sqrt(uu * uu + ry * ry)
    zl = dp[0] * Rr * np.sqrt(np.clip(1.0 - rr * rr, 0.0, 1.0)) - 1.6 * Rr * np.clip(rr - 0.97, 0.0, None)
    X, Y, Z = uu * Rr, ry * b * Rr, zl + OFFSET
    P = c0[None, None] + xax[None, None] * X[..., None] + yax[None, None] * Y[..., None] + look[None, None] * Z[..., None]
    du = np.gradient(P, axis=0)
    dv = np.gradient(P, axis=1)
    Nn = np.cross(du, dv)
    Nn /= np.maximum(np.linalg.norm(Nn, axis=-1, keepdims=True), 1e-12)
    flip = (Nn.reshape(-1, 3) @ look).mean() < 0
    if flip:
        Nn = -Nn
    taper = (0.4 + 0.6 * N.smooth(0.0, 0.35, vv))[..., None]
    sheet = G.thick_sheet(P.reshape(-1, 3), (Nn * taper).reshape(-1, 3), nu, nv, THICK)
    if flip:
        sheet['f'] = sheet['f'][:, ::-1]
    w2 = np.concatenate([vv.ravel(), vv.ravel()])
    return G.piece(sheet['v'], sheet['f'], ck=CK_LID, w2=w2, part=10.0, cpart=0.0, tk=1.8, bid=0.5)


def build(high: bool):
    from lib import surface as S
    pcs = [lid_piece(s, high) for s in (1, -1)]
    allp = G.merge(pcs)
    if high:
        P = allp['v']
        # fine creases along the lid, parallel to its edge
        w = allp['a']['w2']
        disp = -0.00018 * N.smooth(0.7, 1.0, np.cos(w * np.pi * 7.0)) * N.smooth(0.12, 0.3, w)
        keep = {k: allp['a'][k] for k in ('ck', 'w2', 'part', 'bid')}
        allp['a'] = keep
        ob = G.make_object('hi_lids', allp)
        co, vn = S.mesh_arrays(ob)
        S.set_positions(ob, co + vn * disp[:, None])
        ob['prop'] = 'lids'
        return [ob]
    allp['a'] = {k: allp['a'][k] for k in ('cpart', 'tk', 'ck')}
    ob = G.make_object('lo_lids', allp)
    order = G.face_order(allp)
    G.set_face_attr(ob, 'texel_k', allp['a']['tk'][allp['f'][order]].mean(axis=1))
    ob['prop'] = 'lids'
    return [ob]
