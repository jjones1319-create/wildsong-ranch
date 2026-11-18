"""Coilfang's skin weights (Art 2.1 Ultra; RECIPE.md "Rig weights"): the whole body weighted here, no heat weights (a
long tube weights cleanly by its own coordinate): each point blends between the two spine bones whose middles bracket
its place along the body (linear between the bones' middles, so every bend is smooth), the head's volumes rigid on
`head`, the lower jaw rigid on `jaw` (its side of the mouth's cut). Props: the crest's feathers on the two mirrored
chains crestL / crestR by their side and along each feather, the tongue on its chain, the fangs rigid on the head, the
mouth's pocket following its lip vertices.
"""
from __future__ import annotations

import numpy as np

from lib import ultra as U
from lib.surface import smooth
from monsters.breeds import coilfang_form as F
from monsters.breeds import coilfang_mouth as MO
from monsters.breeds import coilfang_props as PR

SEG_BONES = ['neck.4', 'neck.3', 'neck.2', 'neck.1', 'hips'] + [f'tail.{i + 1}' for i in range(F.TAIL_BONES)]
HEAD_MID = -0.1          # where the head bone's share peaks (metres before the back of the head)


def spine_weights(s: np.ndarray) -> dict[str, np.ndarray]:
    """Each point between the middles of the two bones round it (the head's middle in front of the curve's start)."""
    cs = 0.5 * (F.SPINE_S[1:] + F.SPINE_S[:-1])
    cen = np.concatenate([[HEAD_MID], cs])
    names = ['head'] + SEG_BONES
    if len(cen) != len(names):
        raise SystemExit(f'coilfang skin: {len(cen)} bone middles for {len(names)} bones (TAIL_BONES and the spine disagree)')
    s = np.clip(s, cen[0], cen[-1])
    i = np.clip(np.searchsorted(cen, s, side='right'), 1, len(cen) - 1)
    t = (s - cen[i - 1]) / np.maximum(cen[i] - cen[i - 1], 1e-9)
    out = {nm: np.zeros(len(s)) for nm in names}
    for k, nm in enumerate(names):
        a = i - 1 == k
        b = i == k
        out[nm] = np.where(a, 1.0 - t, 0.0) + np.where(b, t, 0.0)
    return out


def body_regions(co: np.ndarray, names: list[str]) -> list:
    tc = F.tube_coords(co)
    hw = F.head_w(co)
    sw = spine_weights(tc['s'])
    wj = MO.jaw_weight(co)
    js = MO.jside(len(co))
    if js is not None:
        near = js >= 0.0
        wj = np.where(near, np.clip(js, 0.0, 1.0) * np.maximum(wj, smooth(-0.01, 0.0, MO.mouth_z(MO.mouth_theta(co)) - co[:, 2])), wj)
    W = {nm: (1.0 - hw) * w for nm, w in sw.items()}
    W['head'] = W.get('head', 0.0) + hw
    W = {nm: w * (1.0 - wj) for nm, w in W.items()}
    W['jaw'] = wj
    missing = [nm for nm in W if nm not in names and np.any(W[nm] > 0)]
    if missing:
        raise SystemExit(f'coilfang skin: the rig has no {missing}')
    return [(np.ones(len(co), bool), {nm: w for nm, w in W.items() if nm in names})]


def prop_regions(co: np.ndarray, attr, names: list[str], chain) -> list:
    regs = []
    crest = attr('fpart') > 0.5
    if crest.any():
        fu = np.clip(attr('fu')[crest], 0.0, 1.0)
        left = smooth(-0.35, 0.35, attr('fside')[crest])
        head = smooth(0.16, 0.0, fu)
        b1 = np.clip(1.0 - np.abs(fu - 0.3) / 0.45, 0.0, 1.0)
        b2 = smooth(0.3, 0.8, fu)
        tot = np.maximum(b1 + b2, 1e-6)
        b1, b2 = b1 / tot * (1.0 - head), b2 / tot * (1.0 - head)
        regs.append((crest, {'head': head, 'crestL.1': b1 * left, 'crestL.2': b2 * left, 'crestR.1': b1 * (1.0 - left),
                             'crestR.2': b2 * (1.0 - left)}))
    tg = attr('tpart') > 0.5
    if tg.any():
        regs.append((tg, U.chain_weights(co[tg], PR.TONGUE, ['tongue.1', 'tongue.2'], 'jaw', fade=(0.02, -0.05))))
    fang = attr('fang') > 0.5
    if fang.any():
        regs.append(U.rigid(fang, 'head'))
    bag = attr('bag') > 0.5
    if bag.any():
        import bpy
        from lib import surface as S
        lo = bpy.data.objects['lo_body']
        gn, W = S.body_weights(lo)
        ia = np.rint(attr('bag_a')[bag]).astype(np.int64)
        ib = np.rint(attr('bag_b')[bag]).astype(np.int64)
        t = attr('bag_t')[bag][:, None]
        if ia.max() >= len(W):
            raise SystemExit('coilfang mouth pocket: its lip vertices are not lo_body\'s (bag_a past the body\'s vertices)')
        mid = ia < 0
        lips = np.unique(ia[~mid])
        Wb = W[np.maximum(ia, 0)] * (1.0 - t) + W[np.maximum(ib, 0)] * t
        Wb[mid] = W[lips].mean(axis=0)
        regs.append((bag, {g: Wb[:, k].astype(np.float64) for k, g in enumerate(gn) if g in names and Wb[:, k].any()}))
    return regs
