"""Lootlid's legs (Art 2.1 Ultra; 2-turnaround, 4-details panel 3; round 1 review): four stubby wooden posts, each a rigid
prop on its own thigh bone (`leg<k>.<L|R>`), so it pivots stiffly at its hip (just under the box) and never bends; its
top runs on up into the box, so the joint never shows a torn edge. One riveted gold cuff two-thirds down (lootlid_straps)
and a thin gold cap at the top ride the same bone (round 3: a collar on the box sheared as the post turned). The posts carry their own wood: grain and splits up them, a rounded, chipped foot, end-grain rings
and checks on the sole. The fields the paint reads are the body's (lootlid_wood), so the posts paint like the box.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import lootlid_form as F
from monsters.breeds import lootlid_geo as G
from monsters.breeds import lootlid_noise as N
from monsters.breeds import lootlid_trim as T

PK_LEG = 11
HIP_Z = 0.15               # the pivot, in the middle of the collar
COLLAR_Z = (0.126, 0.192)
COLLAR_GAP, COLLAR_T = 0.006, 0.0085
WOOD_KEYS = ('region', 'seam', 'crown', 'pid', 'grain', 'knot', 'nick', 'crack', 'edge', 'lash', 'lip', 'brow', 'sole', 'ldist')


def leg_bones(f: int) -> dict:
    """The left leg's bones (front f = 1, back f = −1): the thigh is the whole post, from the hip in the collar to just
    above the foot; a short shin to the ankle; the foot forward."""
    ax = lambda z: F.leg_axis((1, f), z)            # noqa: E731
    hip, knee, ankle = ax(HIP_Z), ax(0.045) + np.array([0.008, 0.0, 0.0]), ax(0.02)
    toe = (float(ankle[0]), float(ankle[1]) - 0.07, 0.008)
    return {'hip': tuple(map(float, hip)), 'knee': tuple(map(float, knee)), 'ankle': tuple(map(float, ankle)), 'toe': toe}


def bone_of(i: int) -> str:
    s, f = list(F.LEGS)[i]
    return f"leg{1 if f > 0 else 2}.{'L' if s > 0 else 'R'}"


def _wood(pc: dict, key, i: int, high: bool) -> dict:
    """The post's wood fields (and, high, its carving): vertical grain and splits, the sole's rings and checks."""
    v = pc['v']
    n = len(v)
    c = np.array([F.leg_axis(key, float(z)) for z in v[:, 2]])
    d = v - c
    d[:, 2] = 0.0
    r = np.linalg.norm(d, axis=1)
    ang = np.arctan2(d[:, 1], d[:, 0])
    sole = (v[:, 2] < 0.0015) & (r < F.lerp_tab(F.LEG_R, 0.0) - F.LEG_EDGE * 0.6)
    pid = float(N.hash1(i, 33)[0])
    g_al, g_ac = v[:, 2], ang * 0.075
    P = np.stack([g_al * 0.18, g_ac, np.full(n, pid * 7.0)], axis=1)
    warp = 0.011 * N.fbm(P, 1 / 0.025, 51 + i, 3)
    lines = 0.5 + 0.5 * np.cos(2 * math.pi * (g_ac + warp) / 0.0068)
    grain = N.smooth(0.72, 0.97, lines) * (0.6 + 0.4 * N.fbm(P * np.array([1, 4, 1]), 1 / 0.05, 52, 2))
    # two or three splits up each post from the foot, and checks across the sole
    split = np.zeros(n)
    for k in range(3):
        a0 = float(N.hash1(i * 7 + k, 34)[0]) * 2 * math.pi
        top = 0.05 + 0.08 * float(N.hash1(i * 7 + k, 35)[0])
        da = np.abs(np.angle(np.exp(1j * (ang - a0)))) * r
        split = np.maximum(split, N.smooth(0.003, 0.0, da) * N.smooth(top, top - 0.02, v[:, 2]) * (~sole))
    check = np.zeros(n)
    for k in range(4):
        a0 = float(N.hash1(i * 11 + k, 36)[0]) * 2 * math.pi
        da = np.abs(np.angle(np.exp(1j * (ang - a0)))) * r
        check = np.maximum(check, N.smooth(0.0025, 0.0, da) * N.smooth(0.012, 0.03, r) * sole)
    rings = N.smooth(0.6, 0.95, 0.5 + 0.5 * np.cos(2 * math.pi * r / 0.0075)) * sole
    foot_edge = N.smooth(0.03, 0.006, v[:, 2]) * (~sole)
    f1, _f2, cid = N.voronoi(v, 0.014, 60 + i)
    nick = (N.hash1(cid % 1000003, 62) < 0.22) * N.smooth(0.008, 0.0, f1) * foot_edge
    crack = np.maximum(split, check)
    if high:
        nrm = np.where(sole[:, None], np.array([[0.0, 0.0, -1.0]]), d / np.maximum(r, 1e-6)[:, None])
        disp = -0.0008 * grain - 0.0022 * crack - 0.0007 * rings - 0.0025 * nick + 0.0002 * N.fbm(v, 1 / 0.003, 71, 2)
        pc['v'] = v + nrm * disp[:, None]
    W = {'region': np.where(sole, 8.0, 3.0), 'seam': np.zeros(n), 'crown': np.ones(n), 'pid': np.full(n, pid), 'grain': grain,
         'knot': np.zeros(n), 'nick': nick, 'crack': crack, 'edge': 0.6 * foot_edge, 'lash': np.zeros(n), 'lip': np.zeros(n),
         'brow': np.zeros(n), 'sole': sole.astype(np.float64), 'ldist': r}
    pc['a']['gco'] = np.stack([g_al, g_ac + warp, np.full(n, pid)], axis=1)
    for k2, val in W.items():
        pc['a'][k2] = val
    return pc


def posts(high: bool) -> list[dict]:
    out = []
    for i, key in enumerate(F.LEGS):
        pc = G.loft(F.leg_rows(key, 0.003 if high else 0.03, coarse=not high), G.unit_ring(2.0, 128 if high else 16))
        pc = T.finish(pc, pk=PK_LEG, leg=float(i + 1), top=1.0)
        out.append(_wood(pc, key, i, high))
    return out


def collars(high: bool) -> list[dict]:
    """A gold collar round each post's top, fixed under the box: the post turns inside it (6 mm of room)."""
    out = []
    z0, z1 = COLLAR_Z
    half = 0.5 * (z1 - z0)
    a = T.across(half, 0.006, high)
    for i, key in enumerate(F.LEGS):
        r0 = F.lerp_tab(F.LEG_R, 0.5 * (z0 + z1)) + COLLAR_GAP
        n_th = int(2 * math.pi * r0 / (0.0016 if high else 0.024))
        th = np.linspace(0, 2 * math.pi, n_th, endpoint=False)
        base = np.zeros((n_th, len(a), 3))
        for k, z in enumerate(0.5 * (z0 + z1) + a):
            c = F.leg_axis(key, float(z))
            base[:, k] = c[None] + r0 * np.stack([np.cos(th), np.sin(th), np.zeros_like(th)], axis=1)
        nrm = np.repeat(np.stack([np.cos(th), np.sin(th), np.zeros_like(th)], axis=1)[:, None, :], len(a), axis=1)
        rel = T.hammer(base, 80 + i) if high else None
        rings = T.slab_rings(base, nrm, a, half, 0.006, COLLAR_T, rel, thin=not high)
        out.append(T.finish(T.band_piece(rings, True, T.slab_attrs(n_th, len(a), a, half, thin=not high), rel), pk=T.PK_BOX))
        c = F.leg_axis(key, 0.146)
        ang = np.radians(np.arange(4) * 90.0 + 45.0)
        pts = [c + (r0 + COLLAR_T) * np.array([math.cos(t), math.sin(t), 0.0]) for t in ang]
        out += T.rivets(pts, [np.array([math.cos(t), math.sin(t), 0.0]) for t in ang], high, r=0.0105, h=0.0062, pk=T.PK_BOX)
    return out


CAP_Z = (0.151, 0.167)


def caps(high: bool) -> list[dict]:
    """Round 3: a thin gold cap round each post's top where it meets the box, rigid on the post's own bone (the
    review: one band per leg two-thirds down, as in 1-hero; the collar on the box sheared as the post turned)."""
    out = []
    z0, z1 = CAP_Z
    half = 0.5 * (z1 - z0)
    a = T.across(half, 0.003, high)
    for i, key in enumerate(F.LEGS):
        n_th = int(2 * math.pi * 0.072 / (0.0016 if high else 0.026))
        th = np.linspace(0, 2 * math.pi, n_th, endpoint=False)
        base = np.zeros((n_th, len(a), 3))
        for k, z in enumerate(0.5 * (z0 + z1) + a):
            c = F.leg_axis(key, float(z))
            base[:, k] = c[None] + F.lerp_tab(F.LEG_R, float(z)) * np.stack([np.cos(th), np.sin(th), np.zeros_like(th)], axis=1)
        nrm = np.repeat(np.stack([np.cos(th), np.sin(th), np.zeros_like(th)], axis=1)[:, None, :], len(a), axis=1)
        rel = T.hammer(base, 90 + i) if high else None
        rings = T.slab_rings(base, nrm, a, half, 0.003, 0.0055, rel, thin=not high)
        out.append(T.finish(T.band_piece(rings, True, T.slab_attrs(n_th, len(a), a, half, thin=not high), rel), pk=T.PK_CUFF, leg=float(i + 1)))
    return out


def build(high: bool) -> list:
    """The posts (each rigid on its thigh) and their thin top caps (gold, on the same bone), as two objects."""
    tag = 'hi' if high else 'lo'
    obs = [G.make_object(f'{tag}_legs', G.merge(posts(high))), G.make_object(f'{tag}_legcaps', G.merge(caps(high)))]
    if not high:
        for ob in obs:
            T.set_texel_k(ob)
    return obs
