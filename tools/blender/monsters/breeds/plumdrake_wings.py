"""Plumdrake's big broad wings (Art 2.1 Ultra; chatgpt/monsters/32-plumdrake 2-turnaround back and wings views, 4-details
panel 4, 5-poses attack): dusky-blue membranes stretched between plum finger bones, a thick plum scaled arm along the
leading edge, and two rows of soft cloud-white feathers along the trailing edge.

- The rig's wing spec (plans/biped.py `wings`, lib/ultra.py): three fingers a wing. Folded (the rest pose every unkeyed
  clip shows) as in the back view: the wrist the high point behind the shoulder, the forearm down to the elbow by the
  spine, the fingers hanging down behind the back a little fanned, so the membrane shows and the feathers hang below.
  Spread (wings view, made broader: about 3.6 m across with the feathers, 2 x the height, so it looks able to fly):
  the arm raised out, the leading finger out to the tip, the others fanning down and a little back (the 70 degree
  in-game strike camera then still sees their faces).
- Membranes: lib/surface.wing_membrane (one sheet a wing, three panels), a gentle billow, branching veins on the high
  sheet for the normal map; weighted with U.wing_fin_regions.
- The arm, its knuckle and the finger bones: rigid tubes (props), weighted by construction (the arm bends at the
  elbow; each finger rigid on its bone).
- The feathers: props, each a soft rounded leaf with a quill down its middle, rooted just inside the trailing edge and
  pointing out of it; each rides the membrane's own weights at its root (wing_membrane_weights), so it follows the edge
  as the wing opens. Two rows: long flight feathers and shorter coverts over them on the upper side.

Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import surface as S
from lib import ultra as U
from lib.surface import smooth, v3
from monsters.breeds import hearthwing_parts as HP

# round 2: the rest pose is the hero's half-open wings (the turnaround's tight fold read as a thin dark strip, baked dark
# blotches where the folded panels covered each other, and vanished at 64 px)
# round 3: less swept back and the fingers fanned (the near wing hid behind the body in every three-quarter view, and
# the fingers bunched near the wrist)
_S = (0.16, 0.24, 1.08)
_E = (0.4, 0.3, 1.24)
_W = (0.72, 0.34, 1.46)


def _ahead(p, d, k):
    d = v3(d) / np.linalg.norm(d)
    return tuple(float(x) for x in v3(p) + d * k)


_E2 = _ahead(_S, (1.0, 0.05, 0.75), 0.3)
_W2 = _ahead(_E2, (1.0, 0.1, 0.55), 0.4)

WINGS = {
    'parent': 'chest', 'name': 'wing', 'scallop': 0.2,
    'shoulder': _S, 'elbow': _E, 'wrist': _W,
    'fingers': [(1.08, 0.46, 0.92), (0.86, 0.54, 0.62), (0.54, 0.5, 0.6)],
    'attach': (0.2, 0.38, 0.66),
    'spread': {'elbow': _E2, 'wrist': _W2,
               'fingers': [_ahead(_W2, (1.0, 0.25, -0.12), 0.5), _ahead(_W2, (0.82, 0.42, -0.45), 0.5),
                           _ahead(_W2, (0.32, 0.42, -0.85), 0.5)]},
}
NF = len(WINGS['fingers'])

P_ARM, P_KNUCKLE, P_FINGER, P_FEATHER = 10, 11, 12, 13
ARM_R = (0.066, 0.052, 0.044)           # the arm's radius at the shoulder, the elbow and the wrist
LEAD_R = (0.036, 0.013)                 # the leading finger (the leading edge out to the tip)
FINGER_R = (0.023, 0.009)
BILLOW = 0.035
FEATHER_TEXEL_K = 0.35


def membrane_out(s: int):
    return (0.6 * s, 1.0, 0.0)


def billow(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    wuv = S.attr_array(ob, 'wing_uv').astype(np.float64)
    u, v = wuv[:, 1], wuv[:, 2]
    b = BILLOW * np.sin(np.pi * np.clip(u, 0, 1)) * np.sin(np.pi * np.clip(v, 0, 1)) ** 0.7
    S.set_positions(ob, co + vn * b[:, None])


def veins(wuv: np.ndarray) -> np.ndarray:
    """Branching veins from the finger bones toward the trailing edge (4-details panel 4)."""
    return HP.branch_veins(wuv[:, 1], wuv[:, 2], wuv[:, 0], seed=32, n_main=4, width=0.028,
                           sides_of=lambda p: (0,) if p > NF - 1.5 else (0, 1))


def build_membranes(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for s in (1, -1):
        res = ((24, 40) if quick else (70, 120)) if high else (8, 16)
        ob = S.wing_membrane(f'{tag}_wing{U.wing_tag(s)}', WINGS, s, high, quick, relief=0.0016, res=res, out=membrane_out(s))
        billow(ob)
        if high:
            co, vn = S.mesh_arrays(ob)
            vv = veins(S.attr_array(ob, 'wing_uv').astype(np.float64))
            S.set_positions(ob, co + vn * (0.0011 * vv)[:, None])
        if 'UVMap' not in ob.data.uv_layers:
            ob.data.uv_layers.new(name='UVMap')
        out.append(ob)
    return out


# ----------------------------------------------------------------------------- props: the arm, the knuckle, the fingers
def _attrs(ob: bpy.types.Object, kind: int, side: int, t=None, g=None, fw=None) -> bpy.types.Object:
    n = len(ob.data.vertices)
    S.add_attr(ob, 'part', np.full(n, float(kind)))
    S.add_attr(ob, 'pside', np.full(n, float(side)))
    S.add_attr(ob, 'pt', np.zeros(n) if t is None else np.asarray(t, np.float64))
    S.add_attr(ob, 'pg', np.zeros(n) if g is None else np.asarray(g, np.float64))
    S.add_attr(ob, 'fwuv', np.zeros((n, 3)) if fw is None else np.asarray(fw, np.float64))
    if 'UVMap' not in ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    return ob


def elbow_share() -> float:
    a = float(np.linalg.norm(v3(_E) - v3(_S)))
    b = float(np.linalg.norm(v3(_W) - v3(_E)))
    return a / (a + b)


def build_bones(high: bool, quick: bool) -> list[bpy.types.Object]:
    """Each wing's arm (shoulder -> elbow -> wrist, a rounded root), a round knuckle over the wrist, and the three finger
    bones (the first thicker: the leading edge), each a rigid tube."""
    tag = 'hi' if high else 'lo'
    out = []
    for s in (1, -1):
        q = U.wing_points(WINGS, s)
        sh, el, wr = q['shoulder'], q['elbow'], q['wrist']
        n1 = 14 if high else 5
        a = np.linspace(0, 1, n1)[:, None]
        arm = np.concatenate([sh[None] * (1 - a) + el[None] * a, (el[None] * (1 - a) + wr[None] * a)[1:]])
        la, lb = float(np.linalg.norm(el - sh)), float(np.linalg.norm(wr - el))
        ta = np.concatenate([np.linspace(0, la, n1), (la + np.linspace(0, lb, n1))[1:]]) / (la + lb)
        e = la / (la + lb)
        ra = np.interp(ta, [0.0, e, 1.0], ARM_R) * (1.0 + 0.12 * np.exp(-((ta - e) / 0.06) ** 2))
        seg = (20 if not quick else 12) if high else 8
        d0 = HP.unit(el - sh)
        pre = np.array([0.95, 0.8, 0.55, 0.28])
        arm = np.concatenate([sh[None] - d0[None] * (ARM_R[0] * pre)[:, None], arm])
        ra = np.concatenate([ARM_R[0] * np.sqrt(1.0 - pre ** 2), ra])
        ta = np.concatenate([np.zeros(len(pre)), ta])
        ob = HP.tube(f'{tag}_warm{U.wing_tag(s)}', arm, ra, (0.0, 0.0, 1.0), seg=seg, tip=wr + HP.unit(wr - el) * ARM_R[2] * 0.3)
        out.append(_attrs(ob, P_ARM, s, np.concatenate([np.repeat(ta, seg), [0.0, 1.0]])))
        # the knuckle: a round cap over the wrist joint
        kr = ARM_R[2] * 1.05
        kd = HP.unit(wr - el)
        nk = 12 if high else 6
        u = np.linspace(-1.0, 1.0, nk)
        kp = wr[None] + kd[None] * (u * kr * 1.1)[:, None]
        krad = kr * np.sqrt(np.clip(1.0 - u ** 2, 0.0, 1.0)) + 1e-4
        ob = HP.tube(f'{tag}_wknuckle{U.wing_tag(s)}', kp[1:-1], krad[1:-1], (0.0, 0.0, 1.0), seg=seg, tip=kp[-1])
        out.append(_attrs(ob, P_KNUCKLE, s, np.ones(len(ob.data.vertices))))
        for k, tip in enumerate(q['fingers']):
            lead = k == 0
            nf = (16 if high else 6) if lead else (12 if high else 5)
            f = np.linspace(0, 1, nf)
            if not lead:
                # polish: the finger bones end where the blue membrane meets the feathers (they ran through the band)
                ln = float(np.linalg.norm(tip - wr))
                tip = wr + (tip - wr) * max(0.4, 1.0 - 0.27 / ln)
            pts = wr[None] * (1 - f[:, None]) + tip[None] * f[:, None]
            r0, r1 = LEAD_R if lead else FINGER_R
            d0 = HP.unit(tip - wr)
            pre = np.array([0.9, 0.6, 0.3])
            pts = np.concatenate([wr[None] - d0[None] * (r0 * pre)[:, None], pts])
            rf = np.concatenate([r0 * np.sqrt(1.0 - pre ** 2), r1 + (r0 - r1) * (1 - f) ** 1.2])
            f = np.concatenate([np.zeros(len(pre)), f])
            sg = ((14 if lead else 10) if not quick else 8) if high else (7 if lead else 5)
            ob = HP.tube(f'{tag}_wfin{U.wing_tag(s)}{k}', pts, rf, (0.0, 0.0, 1.0), seg=sg, tip=tip + d0 * r1 * 1.5)
            ft = np.concatenate([np.repeat(f, sg), [0.0, 1.0]])
            out.append(_attrs(ob, P_FINGER, s, ft, np.full(len(ft), float(k + 1))))
    return out


# ----------------------------------------------------------------------------- props: the feathers
def _panel_point(s: int, panel: int, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    pans = U.wing_panels(WINGS, s)
    p = pans[panel]
    return U._coons(p['C0'], p['C1'], p['D0'], p['D1'], np.atleast_1d(u), np.atleast_1d(v))


ROWS = [  # (v of the root, length per panel, width, count per panel, offset to the upper side, u jitter phase)
    {'v': 0.955, 'len': (0.28, 0.25, 0.22), 'w': 0.1, 'n': (12, 9, 13), 'lift': 0.0, 'phase': 0.0},
    {'v': 0.86, 'len': (0.17, 0.15, 0.13), 'w': 0.088, 'n': (9, 8, 10), 'lift': 0.012, 'phase': 0.5},
]


def feather_specs(s: int) -> list[dict]:
    """Every feather of one wing: root, direction (out of the trailing edge, in the membrane's plane), the membrane's
    upper normal, length, width, and its root's wing_uv (panel, u, v) for the weights."""
    rng = np.random.default_rng(3200 + (1 if s > 0 else 2))
    out = []
    up_ref = v3(membrane_out(s))
    for ri, row in enumerate(ROWS):
        for panel in range(NF):
            n = row['n'][panel]
            for i in range(n):
                u = (i + 0.5 + 0.5 * row['phase']) / (n + 0.5 * row['phase'] + 0.0)
                u = float(np.clip(u + rng.uniform(-0.02, 0.02), 0.02, 0.98))
                v = row['v']
                root = _panel_point(s, panel, u, v)[0]
                inner = _panel_point(s, panel, u, v - 0.2)[0]
                du = 0.01
                ta = _panel_point(s, panel, min(1.0, u + du), v)[0] - _panel_point(s, panel, max(0.0, u - du), v)[0]
                d = HP.unit(root - inner)
                t_edge = HP.unit(ta - d * float(ta @ d))
                nrm = HP.unit(np.cross(t_edge, d))
                if float(nrm @ up_ref) < 0:
                    nrm = -nrm
                L = row['len'][panel] * rng.uniform(0.9, 1.08)
                # near the body (the last panel's far end) the feathers shorten
                if panel == NF - 1:
                    L *= 1.0 - 0.35 * smooth(0.6, 1.0, u)
                out.append({'root': root + nrm * row['lift'], 'dir': d, 'edge': t_edge, 'nrm': nrm, 'len': L,
                            'w': row['w'] * rng.uniform(0.92, 1.08), 'wuv': (float(panel), u, v), 'row': ri,
                            'curl': rng.uniform(0.04, 0.09), 'sweep': rng.uniform(-0.08, 0.08)})
    return out


def feather_axis(f: dict, rings: int):
    t = np.linspace(-0.12, 1.0, rings)
    tt = np.clip(t, 0.0, 1.0)
    L = f['len']
    c = (v3(f['root'])[None] + v3(f['dir'])[None] * (L * t)[:, None] + v3(f['nrm'])[None] * (f['curl'] * L * tt ** 2)[:, None]
         + v3(f['edge'])[None] * (f['sweep'] * L * tt ** 2)[:, None])
    # a soft rounded leaf: narrow at the quill's root, full by 35%, a round tip
    tip = np.where(tt > 0.6, np.sqrt(np.clip(1.0 - ((tt - 0.6) / 0.42) ** 2, 0.0, 1.0)), 1.0)
    w = 0.5 * f['w'] * (0.4 + 0.6 * smooth(0.0, 0.35, tt)) * tip
    th = 0.5 * 0.012 * (1.0 - 0.55 * tt) * np.maximum(tip, 0.3)
    return c, w, th, t


def build_feathers(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    out = []
    for s in (1, -1):
        for i, f in enumerate(feather_specs(s)):
            rings = (16 if not quick else 9) if high else 7
            seg = (12 if not quick else 8) if high else 6
            c, w, th, t = feather_axis(f, rings)
            n_ = len(c)
            T = HP.tangents(c)
            X = np.tile(v3(f['edge']), (n_, 1))
            X = X - T * (X * T).sum(1, keepdims=True)
            X = X / np.linalg.norm(X, axis=1, keepdims=True)
            Y = np.cross(T, X)
            ob = HP.loft(f'{tag}_feather{U.wing_tag(s)}{i}', c[:-1], X[:-1], Y[:-1], np.maximum(w[:-1], 1e-4),
                         np.maximum(th[:-1], 1e-4), seg, True, True, c[-1], ring_attrs={'ft': np.clip(t[:-1], 0, 1)})
            co, _vn = S.mesh_arrays(ob)
            # across the vane: -1 .. 1 (the quill at 0), for the paint (loft's vertex order: rings, then the two caps)
            ring = np.concatenate([np.repeat(np.arange(n_ - 1), seg), [0, n_ - 2]])
            rel = co - c[:-1][ring]
            across = (rel * X[:-1][ring]).sum(1) / np.maximum(w[:-1][ring], 1e-4)
            nv = len(co)
            S.add_attr(ob, 'fq', np.clip(across, -1, 1))
            _attrs(ob, P_FEATHER, s, S.attr_array(ob, 'ft'), np.full(nv, float(f['row'])), np.tile(np.array(f['wuv']), (nv, 1)))
            S.orient_away(ob, lambda cc, c_=c: c_[np.argmin(((cc[:, None, :] - c_[None]) ** 2).sum(-1), axis=1)])
            if not high:
                # soft white feathers need few texels: a third of the density, so they don't take a quarter of the atlas
                ob.data.attributes.new('texel_k', 'FLOAT', 'FACE').data.foreach_set(
                    'value', np.full(len(ob.data.polygons), FEATHER_TEXEL_K, np.float32))
            out.append(ob)
    return out


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    # round 2: the feathers are no longer props (loose pellets with dark, mis-baked backs): plumdrake_feathers.py
    return build_bones(high, quick)


# ----------------------------------------------------------------------------- weights
HUB = 0.12          # round 3: the membrane's finger edges ride their finger bones from near the wrist (0.35 let them part)


def fin_regions(co: np.ndarray, attr, names: list[str]) -> list:
    side_, wuv = attr('wing_side'), attr('wing_uv')
    regs = []
    for s in (1, -1):
        on = np.abs(side_ - s) < 0.1
        if on.any():
            regs.append((on, U.wing_membrane_weights(wuv[on], WINGS, s, hub=HUB)))
    return regs


def prop_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """The wing props: the arm along its length (bending at the elbow), the knuckle on the forearm, each finger rigid on
    its bone, each feather with the membrane's weights at its root."""
    part = np.round(attr('part')).astype(int)
    side = np.round(attr('pside')).astype(int)
    t = attr('pt').astype(np.float64)
    g = np.round(attr('pg').astype(np.float64)).astype(int)
    regs = []
    e = elbow_share()
    for s in (1, -1):
        nm = U.wing_bone_names(WINGS, s)
        m = (part == P_ARM) & (side == s)
        if m.any():
            bend = smooth(e - 0.07, e + 0.07, t[m])
            regs.append((m, {nm[0]: 1.0 - bend, nm[1]: bend}))
        m = (part == P_KNUCKLE) & (side == s)
        if m.any():
            regs.append(U.rigid(m, nm[1]))
        for k in range(NF):
            m = (part == P_FINGER) & (side == s) & (g == k + 1)
            if m.any():
                regs.append(U.rigid(m, nm[2 + k]))
        m = (part == P_FEATHER) & (side == s)
        if m.any():
            wuv = attr('fwuv').astype(np.float64)[m]
            regs.append((m, U.wing_membrane_weights(wuv, WINGS, s)))
    return regs
