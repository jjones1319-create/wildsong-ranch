"""Plumdrake's feathered trailing edge (Art 2.1 Ultra, round 2; 4-details panel 4, 5-poses attack): a solid band of soft
cloud-white feathers along each wing's trailing edge, about 35-40% of the wing's depth, in three overlapping rows (long
flight feathers to a scalloped edge, coverts over their roots, small coverts over those), painted and lightly sculpted on
the membrane's outer part and on a band of membrane that carries on past the edge.

Round 1's feathers were separate props: they spread into a comb of loose pellets as the wing opened, and their stacked
backs baked dark (each bake ray hit the next feather). The band is one sheet with the membrane (a fin: two-sided, the
same weights at the edge as the membrane's), so it stays solid as the wing opens and nothing overlaps in the bake.

Coordinates: each point of a wing's fins has `fband` = (panel, u along the trailing edge, e metres from the edge: < 0 on
the membrane, > 0 on the band). Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import surface as S
from lib import ultra as U
from lib.surface import smooth, v3
from monsters.breeds import plumdrake_wings as WG

ROWS = [   # e from .. to (None: the band's scalloped edge), feathers per panel, offset, how high it lies (the top row last)
    {'e0': -0.07, 'e1': None, 'n': (7, 6, 9), 'phase': 0.0, 'level': 0},
    {'e0': -0.17, 'e1': 0.05, 'n': (8, 7, 10), 'phase': 0.5, 'level': 1},
    {'e0': -0.25, 'e1': -0.085, 'n': (10, 8, 12), 'phase': 0.25, 'level': 2},
]
BAND_LEN = (0.27, 0.24, 0.21)            # the flight feathers' reach past the edge, per panel (outer first)
WHITE_FROM = -0.25                       # the band's white starts this far in on the membrane


def band_len(panel: np.ndarray, u: np.ndarray) -> np.ndarray:
    """The band's length past the edge: a rounded tip per flight feather (the scalloped edge); shorter near the body."""
    panel = np.asarray(panel).astype(int)
    u = np.asarray(u, np.float64)
    L = np.array(BAND_LEN)[np.clip(panel, 0, 2)]
    L = np.where(panel == 2, L * (1.0 - 0.45 * smooth(0.55, 1.0, u)), L)
    # round 3: tapering to nothing at the wing's tip (feathers wrapped round the leading edge there)
    # polish: never quite zero (zero-area faces gave NaN normals: the raw .glb material rendered a blank frame)
    L = np.where(panel == 0, L * (0.1 + 0.9 * smooth(0.0, 0.2, u)), L)
    n = np.array(ROWS[0]['n'])[np.clip(panel, 0, 2)]
    f = (u * n) % 1.0
    # round 3: a round tip per flight feather (round 2's shallow scallop read as a saw-tooth hem)
    return L * (0.6 + 0.4 * np.sqrt(np.clip(np.sin(np.pi * f), 0.0, 1.0)))


def _panels(s: int):
    return U.wing_panels(WG.WINGS, s)


def edge_frame(s: int, panel: int, u: np.ndarray):
    """At the trailing edge (rest pose): the point, the outward direction in the membrane's plane, its upper normal."""
    p = _panels(s)[panel]
    u = np.clip(np.asarray(u, np.float64), 0.0, 1.0)
    c1 = U._coons(p['C0'], p['C1'], p['D0'], p['D1'], u, np.ones(len(u)))
    c8 = U._coons(p['C0'], p['C1'], p['D0'], p['D1'], u, np.full(len(u), 0.8))
    d = c1 - c8
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    du = 1e-3
    t = (U._coons(p['C0'], p['C1'], p['D0'], p['D1'], np.clip(u + du, 0, 1), np.ones(len(u)))
         - U._coons(p['C0'], p['C1'], p['D0'], p['D1'], np.clip(u - du, 0, 1), np.ones(len(u))))
    t -= d * (t * d).sum(1, keepdims=True)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    nrm = np.cross(t, d)
    ref = v3(WG.membrane_out(s))
    flip = (nrm @ ref) < 0
    nrm[flip] *= -1
    return c1, d, nrm


def membrane_e(s: int, wuv: np.ndarray) -> np.ndarray:
    """A membrane point's distance from the trailing edge (metres, negative), from its (panel, u, v) at rest."""
    out = np.zeros(len(wuv))
    pans = _panels(s)
    for k, p in enumerate(pans):
        m = np.round(wuv[:, 0]).astype(int) == k
        if not m.any():
            continue
        u = np.clip(wuv[m, 1], 0, 1)
        c0 = U._coons(p['C0'], p['C1'], p['D0'], p['D1'], u, np.zeros(len(u)))
        c1 = U._coons(p['C0'], p['C1'], p['D0'], p['D1'], u, np.ones(len(u)))
        out[m] = -(1.0 - np.clip(wuv[m, 2], 0, 1)) * np.linalg.norm(c1 - c0, axis=1)
    return out


def field(fb: np.ndarray) -> dict:
    """Per point (from fband): which feather row lies on top (-1 none), its across (-1..1) and along (0 root .. 1 tip)
    coordinates, and the white band's share (0 on the bare membrane)."""
    panel = np.round(fb[:, 0]).astype(int)
    u, e = fb[:, 1], fb[:, 2]
    n = len(fb)
    level = np.full(n, -1)
    q = np.zeros(n)
    sf = np.zeros(n)
    edge = band_len(panel, u)
    outl = []                                  # each row's distance outside its feathers' outline (normalised)
    for r in ROWS:
        cnt = np.array(r['n'])[np.clip(panel, 0, 2)]
        g = u * cnt + r['phase']
        qq = (g % 1.0) * 2.0 - 1.0
        e1 = edge if r['e1'] is None else np.full(n, r['e1'])
        ss = (e - r['e0']) / np.maximum(e1 - r['e0'], 1e-6)
        # a soft feather: full width from its root to 60%, then a rounded tip
        half = np.where(ss < 0.6, 1.0, np.sqrt(np.clip(1.0 - ((ss - 0.6) / 0.42) ** 2, 0.0, 1.0)))
        inside = (ss >= 0.0) & (ss <= 1.0) & (np.abs(qq) <= half * 1.02 + (r['e1'] is None))
        tipd = np.where(ss > 0.6, np.sqrt(qq ** 2 + ((ss - 0.6) / 0.42) ** 2) - 1.0, np.abs(qq) - 1.0)
        outl.append((r['level'], np.where(ss >= 0.0, tipd, 9.0)))
        level = np.where(inside, r['level'], level)
        q = np.where(inside, qq / np.maximum(half, 0.15), q)
        sf = np.where(inside, ss, sf)
    # round 3: crisp white where the feathers lie (round 2's soft gradient read as paint), and the shadow each row's
    # rounded tips cast on the row under them (distinct overlapping rows, 4-details panel 4)
    white = (level >= 0).astype(float) * smooth(WHITE_FROM - 0.004, WHITE_FROM + 0.006, e)
    shadow = np.zeros(n)
    for lv, d in outl:
        shadow = np.maximum(shadow, (level < lv) * (level >= 0) * np.exp(-(np.maximum(d, 0.0) / 0.14) ** 2) * (d > 0))
    return {'level': level, 'q': np.clip(q, -1.5, 1.5), 's': np.clip(sf, 0, 1), 'white': white, 'e': e, 'edge': edge,
            'shadow': shadow}


def relief(fb: np.ndarray) -> np.ndarray:
    """Metres along the normal on the high sheets: each row a little higher, each feather domed with a soft groove at
    its outline and its quill a fine ridge."""
    f = field(fb)
    on = f['level'] >= 0
    dome = np.sqrt(np.clip(1.0 - np.minimum(np.abs(f['q']), 1.0) ** 2, 0.0, 1.0))
    h = on * (0.0012 * f['level'] + 0.0016 * dome - 0.0008 * smooth(0.75, 1.0, np.abs(f['q'])))
    h += on * 0.0005 * np.exp(-(f['q'] / 0.08) ** 2) * smooth(0.95, 0.5, f['s'])
    return h * f['white']


def build_band(name: str, s: int, high: bool, quick: bool) -> bpy.types.Object:
    """One wing's band past the trailing edge, per panel a grid over (u, e from 0 to the scalloped edge)."""
    verts, faces, fb, wuv = [], [], [], []
    for panel in range(WG.NF):
        nf = ROWS[0]['n'][panel]
        nu = ((60 if quick else 24 * nf) if high else 6 * nf)
        nw = (14 if quick else 26) if high else 4
        uu = np.linspace(0.0, 1.0, nu + 1)
        c1, d, nrm = edge_frame(s, panel, uu)
        L = band_len(np.full(len(uu), panel), uu)
        base = len(verts)
        for j in range(nw + 1):
            w = j / nw
            e = w * L
            droop = 0.12 * e ** 2 / 0.27
            pts = c1 + d * e[:, None] - nrm * droop[:, None]
            for i in range(nu + 1):
                verts.append(pts[i])
                fb.append((float(panel), uu[i], float(e[i])))
                wuv.append((float(panel), uu[i], 1.0))
        for j in range(nw):
            for i in range(nu):
                a = base + j * (nu + 1) + i
                faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    fb = np.array(fb)
    ob = S.sheet_object(name, np.array(verts), faces, {'wing_uv': np.array(wuv), 'wing_side': np.full(len(verts), float(s)),
                                                      'fband': fb}, out=WG.membrane_out(s))
    if high:
        co, vn = S.mesh_arrays(ob)
        S.set_positions(ob, co + vn * relief(fb)[:, None])
    if 'UVMap' not in ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    return ob


def build_fins(high: bool, quick: bool) -> list[bpy.types.Object]:
    """The membranes (plumdrake_wings) with `fband` and, on the high ones, the feathers' relief on their outer part; then
    each wing's band."""
    tag = 'hi' if high else 'lo'
    out = []
    for ob in WG.build_membranes(high, quick):
        s = 1 if ob.name.endswith('L') else -1
        wuv = S.attr_array(ob, 'wing_uv').astype(np.float64)
        fb = np.stack([wuv[:, 0], wuv[:, 1], membrane_e(s, wuv)], axis=1)
        S.add_attr(ob, 'fband', fb)
        if high:
            co, vn = S.mesh_arrays(ob)
            S.set_positions(ob, co + vn * relief(fb)[:, None])
        out.append(ob)
    for s in (1, -1):
        out.append(build_band(f'{tag}_wingband{U.wing_tag(s)}', s, high, quick))
    return out
