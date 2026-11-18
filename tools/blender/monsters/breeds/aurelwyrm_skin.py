"""Aurelwyrm's skin weights (Art 2.1 Ultra; RECIPE.md "Rig weights"; the body's as coilfang_skin.py's): the whole body
weighted here, no heat weights (a long tube weights cleanly by its own coordinate): each point blends between the two
spine bones whose middles bracket its place along the body, the head's volumes and the ears rigid on `head`, the lower
jaw rigid on `jaw` (its side of the mouth's cut).
Props: the antlers rigid on the head, the whiskers along their chains, the gold mane locks by their roots' place (the
head's, or the neck's), the mouth's pocket following its lip vertices.
Ribbons: each point takes the spine's weights a little further back along the body than its root (by how far back of
the root it lies), so a ribbon trails the body's bends like silk; the streamers ride their chains, the tail's fan the
last tail bones and then its chain.
"""
from __future__ import annotations

import numpy as np

from lib import ultra as U
from lib.surface import smooth
from monsters.breeds import aurelwyrm_fins as FN
from monsters.breeds import aurelwyrm_form as F
from monsters.breeds import aurelwyrm_mouth as MO
from monsters.breeds import aurelwyrm_props as PR

SEG_BONES = [f'neck.{F.NECK_BONES - k}' for k in range(F.NECK_BONES)] + ['hips'] + [f'tail.{i + 1}' for i in range(F.TAIL_BONES)]
HEAD_MID = -0.12         # where the head bone's share peaks (metres before the back of the head)


def spine_weights(s: np.ndarray) -> dict[str, np.ndarray]:
    """Each point between the middles of the two bones round it (the head's middle in front of the curve's start)."""
    cs = 0.5 * (F.SPINE_S[1:] + F.SPINE_S[:-1])
    cen = np.concatenate([[HEAD_MID], cs])
    names = ['head'] + SEG_BONES
    if len(cen) != len(names):
        raise SystemExit(f'aurelwyrm skin: {len(cen)} bone middles for {len(names)} bones (TAIL_BONES and the spine disagree)')
    s = np.clip(np.asarray(s, float), cen[0], cen[-1])
    i = np.clip(np.searchsorted(cen, s, side='right'), 1, len(cen) - 1)
    t = (s - cen[i - 1]) / np.maximum(cen[i] - cen[i - 1], 1e-9)
    out = {}
    for k, nm in enumerate(names):
        out[nm] = np.where(i - 1 == k, 1.0 - t, 0.0) + np.where(i == k, t, 0.0)
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
        raise SystemExit(f'aurelwyrm skin: the rig has no {missing}')
    return [(np.ones(len(co), bool), {nm: w for nm, w in W.items() if nm in names})]


def _with_root(w: dict, root: str, s_root: np.ndarray) -> dict:
    """A chain's weights with its parent's share handed to the spine bones at the root's place."""
    r = w.pop(root)
    for nm, sw in spine_weights(s_root).items():
        w[nm] = w.get(nm, 0.0) + r * sw
    return w


def prop_regions(co: np.ndarray, attr, names: list[str]) -> list:
    regs = []
    ant = attr('ant') > 0.5
    if ant.any():
        regs.append(U.rigid(ant, 'head'))
    wh = attr('wh') > 0.5
    if wh.any():
        side = attr('wh_side')
        for tag, s in (('L', 1), ('R', -1)):
            m = wh & (side * s > 0)
            if m.any():
                regs.append((m, U.chain_weights(co[m], PR.whisker_points(s), [f'whisker{tag}.{k}' for k in (1, 2, 3)], 'head',
                                                fade=(0.03, -0.06))))
    mn = attr('mn') > 0.5
    if mn.any():
        ms = attr('mn_s')[mn]
        regs.append((mn, spine_weights(np.where(ms < 0, HEAD_MID - 0.05, ms))))
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
            raise SystemExit('aurelwyrm mouth pocket: its lip vertices are not lo_body\'s (bag_a past the body\'s vertices)')
        mid = ia < 0
        lips = np.unique(ia[~mid])
        Wb = W[np.maximum(ia, 0)] * (1.0 - t) + W[np.maximum(ib, 0)] * t
        Wb[mid] = W[lips].mean(axis=0)
        regs.append((bag, {g: Wb[:, k].astype(np.float64) for k, g in enumerate(gn) if g in names and Wb[:, k].any()}))
    return regs


def fin_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """Round 2: a hugging ribbon follows the spine where it lies on the body (its own place along it) and rides its
    chain where it lifts off; the head's flame locks stay on the head; the neck's ribbons and the tail's fan take the
    spine a little further back than their roots, the fan then its chain past the tail's tip."""
    kind = np.rint(attr('rib_kind')).astype(np.int64)
    su, u = attr('rib_su'), attr('rib_u')
    chn = np.rint(attr('rib_chain')).astype(np.int64)
    regs = []
    plain = (chn < 0) & (kind != 4)
    if plain.any():
        regs.append((plain, spine_weights(np.where(su[plain] < 0, HEAD_MID, su[plain]))))
    for m in FN.chains():
        msk = chn == m['index']
        if not msk.any():
            continue
        k = smooth(0.4, 0.75, u[msk])
        W = {nm: w * (1.0 - k) for nm, w in spine_weights(su[msk]).items()}
        cw = U.chain_weights(co[msk], m['points'], [f"{m['name']}.1", f"{m['name']}.2"], m['parent'], fade=(0.0, -0.01))
        for nm, w in cw.items():
            W[nm] = W.get(nm, 0.0) + w * k
        regs.append((msk, W))
    fan = kind == 4
    if fan.any():
        past = np.clip((su[fan] - F.S_TOT) / 0.12, 0.0, 1.0)
        sw = spine_weights(np.minimum(su[fan], F.S_TOT))
        cw = U.chain_weights(co[fan], [tuple(p) for p in FN.tailfin_points()], ['tailfin.1', 'tailfin.2', 'tailfin.3'],
                             f'tail.{F.TAIL_BONES}', fade=(0.0, -0.01))
        W = {nm: w * (1.0 - past) for nm, w in sw.items()}
        for nm, w in cw.items():
            W[nm] = W.get(nm, 0.0) + w * past
        regs.append((fan, W))
    out = []
    for m, W in regs:
        missing = [nm for nm, w in W.items() if nm not in names and np.any(np.asarray(w) > 0)]
        if missing:
            raise SystemExit(f'aurelwyrm ribbons: the rig has no {missing}')
        out.append((m, {nm: np.asarray(w, np.float64) for nm, w in W.items() if nm in names}))
    return out
