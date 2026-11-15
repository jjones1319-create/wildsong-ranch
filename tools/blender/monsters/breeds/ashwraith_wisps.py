"""Ashwraith's wisps (ashwraith_ultra.build_props; round 3 of the review): smoky ribbons hanging down and out from
under the hems, 3-4 cm wide at the root and tapering to a fine tip, in three lengths, curling smoothly outward and up
(2-turnaround, 4-details 4), fanning out from the hem, dark at the root lightening to pale smoke at the tip, with ember
specks (ashwraith_shade); and at the front hem two bunches of three thin lash curls, which the strike coils back and
whips forward.

Geometry ribbons (flattened tubes, never see-through cards), never tapering to zero (min 1.5 mm), with enough points
on the game mesh that every curl stays round (round 2's curls broke into square hooks); every point stays at least
LOWEST off the ground (a clear hover gap; the plan pools hanging chains whose tips would touch).
Attributes (ashwraith_mesh.ATTRS): part WISP or LASH, pt 0 root .. 1 tip, plus `rth` / `rz` (the wisp's root: its
angle round the body and its height, for the weights) and `chain` (8 / 9 on the left / right lash chain, else -1).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from monsters.breeds import ashwraith_drape as D
from monsters.breeds import ashwraith_mesh as AM

WISP, LASH = 5, 11
LOWEST = 0.07
UP = np.array([0.0, 0.0, 1.0])
LENGTHS = (0.07, 0.11, 0.15)


def _hook(p_end: np.ndarray, d_end: np.ndarray, bend: np.ndarray, r0: float, turns: float, n: int) -> np.ndarray:
    """A smooth curl leaving p_end along d_end and turning toward `bend`, tightening."""
    d = d_end / np.linalg.norm(d_end)
    b = bend - d * float(bend @ d)
    b /= np.linalg.norm(b)
    c = p_end + b * r0
    u = np.linspace(0.0, 1.0, n)
    phi = u * turns * 2 * np.pi
    R = r0 * (1.0 - 0.3 * u)          # polish: an open curl (a tight end read as a black hook nub)
    return c[None] + R[:, None] * (-np.cos(phi)[:, None] * b[None] + np.sin(phi)[:, None] * d[None])


def roots() -> list[tuple[np.ndarray, float]]:
    """(hem point, length) per wisp: round the cape's hem and along each front panel's hem (deterministic)."""
    rng = np.random.default_rng(1541)
    out = []
    for k, u in enumerate(np.linspace(-0.93, 0.93, 15) + rng.uniform(-0.03, 0.03, 15)):
        out.append((D.cape_point(np.array([u]), np.array([1.0]))[0], LENGTHS[(k * 2) % 3] * float(rng.uniform(0.9, 1.1))))
    for nm, us in (('innerL', (0.15, 0.7)), ('innerR', (0.15, 0.7)), ('outerL', (-0.3, 0.45)), ('outerR', (-0.3, 0.45))):
        for j, u in enumerate(us):
            out.append((D.panel_point(nm, np.array([u]), np.array([1.0]))[0], LENGTHS[(j + 1) % 3] * float(rng.uniform(0.9, 1.1))))
    return out


def _wisp(root: np.ndarray, o: np.ndarray, tang: np.ndarray, ln: float, r_hook: float, turns: float, fan: float) -> np.ndarray:
    """Out and down from under the hem, fanned `fan` radians out from straight down, then a smooth curl out and up
    (polish: the hem read as a narrow column; the references fan out to about 1.4x the hood's width)."""
    d1 = o * math.sin(fan) - UP * math.cos(fan)
    d2 = o * math.sin(fan + 0.35) - UP * math.cos(fan + 0.35)
    p1 = root + o * 0.01 + d1 * 0.4 * ln
    p2 = p1 + d2 * 0.42 * ln + tang * 0.08 * ln
    body = AM.catmull([root, p1, p2], 30)
    hook = _hook(body[-1], body[-1] - body[-2], o + UP * 0.9, r_hook, turns, 40)
    return AM.resample(np.vstack([body, hook[1:]]), 70)


def strand_paths() -> list[dict]:
    rng = np.random.default_rng(77)
    out = []
    for k, (hp, ln) in enumerate(roots()):
        a, b, yc = D.sh_abyc(hp[2])
        o = np.array([hp[0], hp[1] - yc, 0.0])
        o /= np.linalg.norm(o)
        tang = np.cross(UP, o) * (1 if k % 2 == 0 else -1)
        root = hp + UP * 0.022 - o * 0.014
        ln = min(ln, max(0.04, (hp[2] - LOWEST) / 0.62))
        w0 = float(rng.uniform(0.034, 0.046))
        rth = math.atan2(root[0], -(root[1] - yc))
        fan = math.radians(16.0 + 24.0 * float(np.clip((abs(rth) - 0.4) / 0.8, 0.0, 1.0)))    # the sides and back most
        P = _wisp(root, o, tang, ln, max(0.022, 0.6 * w0) * (ln / 0.11) ** 0.5, float(rng.uniform(0.55, 0.7)), fan)
        P[:, 2] = np.maximum(P[:, 2], LOWEST)
        out.append({'P': P, 'part': WISP, 'w': (w0, 0.003), 'o': o, 'chain': -1,
                    'rth': float(math.atan2(root[0], -(root[1] - yc))), 'rz': float(hp[2])})
    for s, ci in ((1, 8), (-1, 9)):
        pts = np.array(D.lash_chain(s))
        th = s * 9.0 * math.pi / 180.0
        o = np.array([math.sin(th), -math.cos(th), 0.0])
        tang = np.cross(UP, o) * s
        # polish: three thin curls fanning apart down their length (two broad ones read as stubby legs)
        for w0, off, scale in ((0.024, 0.0, 1.1), (0.019, 0.027, 0.9), (0.016, -0.025, 0.8)):
            base = pts + tang[None] * off * (1.0 + 1.6 * np.arange(len(pts))[:, None] / max(1, len(pts) - 1))
            body = AM.catmull([base[0], base[1], base[2]], 30)
            hook = _hook(body[-1], body[-1] - body[-2], o + UP * 1.0, 0.03 * scale, 0.85, 40)
            P = AM.resample(np.vstack([body, hook[1:]]), 70)
            P[:, 2] = np.maximum(P[:, 2], LOWEST)
            out.append({'P': P, 'part': LASH, 'w': (w0, 0.003), 'o': o, 'chain': ci, 'rth': th, 'rz': float(pts[0][2])})
    return out


def wisps_object(name: str, high: bool) -> bpy.types.Object:
    kit = AM.Kit()
    extra = {'rth': [], 'rz': [], 'chain': []}
    for k, r in enumerate(strand_paths()):
        n0 = kit.n
        P = r['P'] if high else AM.resample(r['P'], 30)
        n = len(P)
        s = np.linspace(0.0, 1.0, n)
        w = r['w'][0] + (r['w'][1] - r['w'][0]) * s ** 0.7
        T = P[1] - P[0]
        hint = np.cross(T / np.linalg.norm(T), r['o'])
        if np.linalg.norm(hint) < 1e-6:
            hint = UP

        def relief(a, ss, w0=r['w'][0], ph=0.41 * k):
            return w0 * (0.12 * np.sin(2 * np.pi * (ss / 0.04 + ph)) * np.cos(2 * np.pi * a) ** 2)
        kit.tube(P, w, 16 if high else 8, r['part'], pr=k / 40.0, hint=hint, aspect=0.45, relief=relief, caps=(True, True), texel_k=0.8)
        m = kit.n - n0
        extra['rth'].append(np.full(m, r['rth']))
        extra['rz'].append(np.full(m, r['rz']))
        extra['chain'].append(np.full(m, float(r['chain'])))
    ob = kit.object(name, extra={k: np.concatenate(v) for k, v in extra.items()})
    ob['prop'] = 'wisps'
    return ob
