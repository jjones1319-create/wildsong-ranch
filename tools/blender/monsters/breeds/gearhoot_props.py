"""Gearhoot's rigid parts (Art 2.1 Ultra; chatgpt/monsters/29-gearhoot): every piece is a closed numpy mesh rigid on one
bone (the vertex attribute 'bn' indexes BONES), painted by its part kind 'pk' (gearhoot_paint.py):
  - the wings: overlapping leaf plates in three rigid sets (coverts and the shoulder plate, secondaries, primaries) on
    the wing chain, with gears on the coverts (the big and the middle one turn: spinners);
  - the wind-up key on its back (the shaft and the bow turn on spin.key; its copper housing stays on the hips);
  - the legs: a copper knee ball, an engraved brass boot, the foot's three front talons and one back talon;
  - on the head: the ear tufts (two bent brass blades a side), the hooked beak (its lower half on the jaw) and the
    monocle's copper ring with its hinge bracket and screw knob (on prop.monocle, which also carries the teal lens).
Measured on 2-turnaround and 4-details (1 px = 1.92 mm). Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import gearhoot_form as F
from monsters.breeds import gearhoot_geo as G

BONES = ['hips', 'head', 'jaw', 'prop.monocle', 'spin.key',
         'leg1.L', 'shin1.L', 'foot1.L', 'leg1.R', 'shin1.R', 'foot1.R',
         'wingL.1', 'wingL.2', 'wingL.3', 'wingR.1', 'wingR.2', 'wingR.3',
         'spin.gearL1', 'spin.gearL2', 'spin.gearR1', 'spin.gearR2']
BN = {b: i for i, b in enumerate(BONES)}

# part kinds (the paint)
PK_WING, PK_GEAR, PK_TUFT, PK_BEAK, PK_RING, PK_BRACKET, PK_KNOB = 1, 2, 3, 4, 5, 6, 7
PK_KEY, PK_KEYBASE, PK_KNEE, PK_BOOT, PK_CUFF, PK_TOE, PK_CLAW, PK_HUB = 8, 9, 10, 11, 12, 13, 14, 15
PK_NECK = 16

# ----------------------------------------------------------------------------- the rig points (left side)
LEG = {'hip': (0.104, -0.05, 0.215), 'knee': (0.112, -0.062, 0.15), 'ankle': (0.112, -0.06, 0.052), 'toe': (0.112, -0.175, 0.022)}
WING = [(0.19, -0.205, 0.52), (0.275, 0.0, 0.41), (0.27, 0.12, 0.31), (0.12, 0.29, 0.1)]
KEY_BASE = np.array([0.04, 0.175, 0.5])    # round 2: toward the left shoulder, so the bow clears the head at 3/4
KEY_DIR = np.array([0.12, 0.7, 0.7]) / np.linalg.norm([0.12, 0.7, 0.7])
KEY_LEN = 0.34                             # the housing to the bow's centre
GEARS = {  # name: (centre, radius, teeth, bone, spins)
    'gear1': ((0.25, -0.07, 0.455, 0.08), 0.062, 14, 'wing.1', True),       # (direction x, y, z, stand-off)
    'gear2': ((0.25, 0.07, 0.465, 0.074), 0.046, 11, 'wing.1', True),
    'gear3': ((0.25, 0.0, 0.35, 0.088), 0.031, 9, 'wing.2', False),
    'gear4': ((0.25, 0.065, 0.31, 0.09), 0.026, 8, 'wing.2', False),
}


def mirror_pt(p, s: int) -> np.ndarray:
    p = np.array(p, np.float64)
    return np.array([p[0] * s, p[1], p[2]])


def unit(v) -> np.ndarray:
    v = np.asarray(v, np.float64)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def frame(n, up=(0.0, 0.0, 1.0)) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = unit(n)
    up = np.asarray(up, np.float64)
    if abs(float(n @ unit(up))) > 0.95:
        up = np.array([0.0, 1.0, 0.0])
    e1 = unit(up - n * float(n @ up))
    return n, e1, np.cross(n, e1)


def mir(pc: dict, s: int) -> dict:
    """A piece mirrored to the side s (faces flipped back outward)."""
    if s > 0:
        return pc
    out = {'v': pc['v'] * np.array([-1.0, 1.0, 1.0]), 'f': pc['f'].copy(), 'a': {k: a.copy() for k, a in pc['a'].items()}}
    return G.outward(out)


def gear_axis(name: str, s: int) -> tuple[np.ndarray, np.ndarray]:
    c, r, _t, _b, _sp = GEARS[name]
    p, nrm = body_point(np.array(c[:3]), c[3])
    n = unit(nrm + np.array([0.0, 0.0, 0.25]))
    return mirror_pt(p, s), mirror_pt(n, s)


# ----------------------------------------------------------------------------- shapes
def leaf(root, tip, nrm, width: float, thick: float, bulge: float = 0.0, curl: float = 0.0, J: int = 10, M: int = 8,
         tipk: float = 0.12) -> dict:
    """A leaf plate: an elliptical outline (rounded root, a softly pointed tip), a lens-shaped section (a raised midrib),
    its midline bowed `bulge` along the normal and its tip curled `curl`. Attributes u (along), q (across, -1..1), h
    (0 at the edge, 1 on the midrib) and 'face' (+1 on the outer face)."""
    root, tip = np.asarray(root, np.float64), np.asarray(tip, np.float64)
    L = tip - root
    d = unit(L)
    n = unit(np.asarray(nrm, np.float64) - d * float(d @ nrm))
    side = np.cross(n, d)
    s = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, J + 1))
    mid = root[None] + s[:, None] * L[None] + ((bulge * np.sin(math.pi * s)) + curl * s * s)[:, None] * n[None]
    # a feather's outline: narrow at the root, broadest about 60% along, a rounded tip
    sm = 0.42
    e = np.where(s < sm, (sm - s) / sm, (s - sm) / (1.0 - sm))
    w = 0.5 * width * np.clip(1.0 - e ** 2, 0.0, 1.0) ** 0.42      # round 3: >= 40% wide at 90%, a rounded tip
    w = np.maximum(w, 0.003)
    a = np.linspace(0, 2 * math.pi, M, endpoint=False)
    rings, q, h, fc = [], [], [], []
    for j in range(J + 1):
        tk = 0.5 * thick * (0.35 + 0.65 * w[j] / (0.5 * width))
        rings.append(mid[j][None] + w[j] * np.cos(a)[:, None] * side[None] + tk * np.sin(a)[:, None] * n[None])
        q.append(np.cos(a))
        h.append(np.abs(np.sin(a)))
        fc.append(np.sign(np.sin(a) + 1e-9))
    pc = G.sweep(rings)
    nv = len(pc['v'])
    extra = nv - (J + 1) * M
    pc['a']['q'] = np.concatenate([np.concatenate(q), np.zeros(extra)])
    pc['a']['h'] = np.concatenate([np.concatenate(h), np.full(extra, 1.0)])
    pc['a']['face'] = np.concatenate([np.concatenate(fc), np.zeros(extra)])
    return pc


def gear(c, n, R: float, teeth: int, thick: float, high: bool, spokes: int = 5, hub: float = 0.28, tooth: float = 0.17) -> list[dict]:
    """A gear wheel: a toothed rim (square teeth), a hub and spokes. Attributes gr (0 at the hub … 1 at the teeth' tips)
    and tooth (1 on the teeth)."""
    n, e1, e2 = frame(n)
    c = np.asarray(c, np.float64)
    h = tooth * R
    Ri = R * 0.74
    th = []
    ro = []
    for j in range(teeth):
        base = 2 * math.pi * j / teeth
        for off, rr in ((-0.25, R), (-0.17, R + h), (0.17, R + h), (0.25, R)):
            th.append(base + off * 2 * math.pi / teeth)
            ro.append(rr)
    if high:
        # extra samples along the gaps between the teeth (a round root circle)
        th2, ro2 = [], []
        for i in range(len(th)):
            th2.append(th[i])
            ro2.append(ro[i])
            if i % 4 == 3:
                nxt = th[(i + 1) % len(th)] + (2 * math.pi if i + 1 == len(th) else 0.0)
                th2.append(0.5 * (th[i] + nxt))
                ro2.append(R)
        th, ro = th2, ro2
    t2 = 0.5 * thick
    rings = []
    for a, r in zip(th, ro):
        rad = math.cos(a) * e1 + math.sin(a) * e2
        rings.append(np.stack([c + Ri * rad - t2 * n, c + r * rad - t2 * n, c + r * rad + t2 * n, c + Ri * rad + t2 * n]))
    rim = G.sweep(rings, closed=True)
    k = np.round(rim['a']['k'] * 4).astype(int) % 4
    rim['a']['gr'] = np.where((k == 0) | (k == 3), 0.74, 1.0)
    rr = np.linalg.norm(rim['v'] - c[None], axis=1)
    rim['a']['tooth'] = (rr > R * 1.03).astype(np.float64)
    parts = [rim]
    nh = 16 if high else 10
    hub_pc = G.tube(np.array([c - 0.75 * thick * n, c + 0.75 * thick * n]), hub * R, nh, up_hint=e1)
    hub_pc['a']['gr'] = np.zeros(len(hub_pc['v']))
    hub_pc['a']['tooth'] = np.zeros(len(hub_pc['v']))
    G.tag(hub_pc, hubk=1.0)
    parts.append(hub_pc)
    for j in range(spokes):
        a = 2 * math.pi * (j + 0.5) / spokes
        rad = math.cos(a) * e1 + math.sin(a) * e2
        tan = np.cross(n, rad)
        sw = 0.07 * R
        cs = [np.array([-sw, -0.38 * thick]), np.array([sw, -0.38 * thick]), np.array([sw, 0.38 * thick]), np.array([-sw, 0.38 * thick])]
        rs = []
        for r in (hub * R * 0.8, Ri * 1.04):
            rs.append(np.stack([c + r * rad + p[0] * tan + p[1] * n for p in cs]))
        sp = G.sweep(rs)
        sp['a']['gr'] = np.full(len(sp['v']), 0.5)
        sp['a']['tooth'] = np.zeros(len(sp['v']))
        parts.append(sp)
    return parts


def torus(c, n, R: float, rr: float, rz: float, nu: int, nk: int, up=(0.0, 0.0, 1.0)) -> dict:
    """A ring about axis n: tube radius rr in its plane, rz along the axis."""
    n, e1, e2 = frame(n, up)
    c = np.asarray(c, np.float64)
    rings = []
    for t in np.linspace(0, 2 * math.pi, nu, endpoint=False):
        rad = math.cos(t) * e1 + math.sin(t) * e2
        k = np.linspace(0, 2 * math.pi, nk, endpoint=False)
        rings.append(c[None] + (R * rad)[None] + rr * np.cos(k)[:, None] * rad[None] + rz * np.sin(k)[:, None] * n[None])
    return G.sweep(rings, closed=True)


def washer(c, n, ri: float, ro: float, thick: float, nu: int, up=(0.0, 0.0, 1.0)) -> dict:
    """A flat ring plate (a washer) about axis n: inner radius ri, outer ro, `thick` thick."""
    n, e1, e2 = frame(n, up)
    c = np.asarray(c, np.float64)
    t2 = 0.5 * thick
    rings = []
    for t in np.linspace(0, 2 * math.pi, nu, endpoint=False):
        rad = math.cos(t) * e1 + math.sin(t) * e2
        rings.append(np.stack([c + ri * rad - t2 * n, c + ro * rad - t2 * n, c + ro * rad + t2 * n, c + ri * rad + t2 * n]))
    return G.sweep(rings, closed=True)


def tube_var(path, radii, nu: int, up=(0.0, 0.0, 1.0), squash: float = 1.0) -> dict:
    """A tube along a path with a radius per point (squash < 1 flattens it along the frames' binormal)."""
    path = np.asarray(path, np.float64)
    radii = np.broadcast_to(np.asarray(radii, np.float64), (len(path),))
    t, nn, b = G.frames(path, up)
    a = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    rings = [path[i] + radii[i] * (np.cos(a)[:, None] * nn[i] + squash * np.sin(a)[:, None] * b[i]) for i in range(len(path))]
    return G.sweep(rings)


def blade(path, widths, thick, nrm, nu: int) -> dict:
    """A flat bent blade (an ear tuft): an elliptical section `widths` wide across, `thick` along nrm, along a path."""
    path = np.asarray(path, np.float64)
    widths = np.asarray(widths, np.float64)
    thick = np.broadcast_to(np.asarray(thick, np.float64), (len(path),))
    nrm = unit(nrm)
    tng = np.gradient(path, axis=0)
    tng /= np.linalg.norm(tng, axis=1, keepdims=True)
    a = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    rings = []
    for i in range(len(path)):
        nn = unit(nrm - tng[i] * float(tng[i] @ nrm))
        side = np.cross(nn, tng[i])
        rings.append(path[i] + 0.5 * widths[i] * np.cos(a)[:, None] * side[None] + 0.5 * thick[i] * np.sin(a)[:, None] * nn[None])
    pc = G.sweep(rings)
    return pc


def smooth_path(pts, n: int) -> np.ndarray:
    """A Catmull-Rom curve through the points, n samples."""
    P = np.asarray(pts, np.float64)
    P = np.concatenate([P[:1] * 2 - P[1:2], P, P[-1:] * 2 - P[-2:-1]])
    out = []
    segs = len(P) - 3
    for i in range(n):
        u = i / (n - 1) * segs
        k = min(int(u), segs - 1)
        t = u - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return np.array(out)


# ----------------------------------------------------------------------------- the wings
def wing_plates() -> list[dict]:
    """The left wing's plates, folded on the body's side: (root, tip, width, layer offset, copper?, bone)."""
    out = []

    def fan(r0, r1, t0, t1, count, width, off0, doff, bone, cu, bulge=0.012):
        for i in range(count):
            f = i / max(1, count - 1)
            r = np.array(r0) + f * (np.array(r1) - np.array(r0))
            t = np.array(t0) + f * (np.array(t1) - np.array(t0))
            out.append({'root': r, 'tip': t, 'width': width, 'off': off0 + doff * i, 'cu': cu(i), 'bone': bone, 'bulge': bulge})
    # the primaries (wing.3): long plates sweeping back and down, their tips converging behind the body as its tail
    fan((0.25, -0.12, 0.37), (0.25, 0.18, 0.39), (0.25, -0.03, 0.12), (0.04, 0.34, 0.06), 6, 0.1, 0.03, -0.0025,
        'wing.3', lambda i: i % 2 == 1, 0.026)
    # the secondaries (wing.2): over the primaries' roots
    fan((0.25, -0.18, 0.455), (0.25, 0.16, 0.465), (0.25, -0.15, 0.215), (0.25, 0.22, 0.19), 6, 0.108, 0.05, -0.0018,
        'wing.2', lambda i: i % 2 == 0, 0.034)
    # the coverts (wing.1): a row of shorter plates under the shoulder plate and the gears
    fan((0.25, -0.19, 0.535), (0.25, 0.13, 0.54), (0.25, -0.18, 0.36), (0.25, 0.18, 0.365), 5, 0.11, 0.056, -0.0015,
        'wing.1', lambda i: i % 2 == 1, 0.006)
    # the shoulder plate: one broad rounded plate over the coverts' roots (copper, as 1-hero)
    out.append({'root': np.array([0.25, -0.2, 0.55]), 'tip': np.array([0.25, 0.02, 0.44]), 'width': 0.16, 'off': 0.064,
                'cu': True, 'bone': 'wing.1', 'bulge': 0.016})
    return out


def body_point(p: np.ndarray, off: float) -> tuple[np.ndarray, np.ndarray]:
    """A point pushed onto the body's side `off` outside it (along the horizontal ray from the body's axis), and that
    outward direction."""
    z = float(np.clip(p[2], 0.135, F.Z_SHOULDER))
    r = F.body_profile(z)
    dx, dy = p[0], p[1] - F.BC[1]
    th = math.atan2(dy / (F.BODY_BF if dy < 0 else F.BODY_BB), dx / F.BODY_A)
    a = F.BODY_A * r
    b = (F.BODY_BF if dy < 0 else F.BODY_BB) * r
    q = np.array([a * math.cos(th), F.BC[1] + b * math.sin(th), p[2]])
    nrm = unit(np.array([math.cos(th) / max(a, 1e-3), math.sin(th) / max(b, 1e-3), 0.0]))
    return q + nrm * off, nrm


def wing(high: bool) -> list[dict]:
    """The left wing (mirrored by the caller): its plates and its gears, each tagged with its bone."""
    J, M = (14, 12) if high else (10, 10)
    pieces = []
    for k, pl in enumerate(wing_plates()):
        r = pl['root']
        t = pl['tip']
        # the plate's midline follows the body's side: root and tip pushed out to their layer
        rr, nr = body_point(r, pl['off'])
        rt, nt = body_point(t, pl['off'] + 0.006) if t[2] > 0.14 else (t + np.array([0.0, 0.0, 0.0]), unit(np.array([t[0], 0.4, 0.0])))
        if t[2] <= 0.14:
            rt = np.array([t[0] + pl['off'], t[1], t[2]])
        nrm = unit(nr + nt)
        if pl['bone'] == 'wing.3':
            # round 3: at rest their plane followed the body's back curve, so the spread turned them edge-on (needles)
            nrm = unit(0.25 * nrm + 0.75 * np.array([1.0, 0.0, 0.0]))
        pc = leaf(rr, rt, nrm, pl['width'], 0.009, bulge=pl['bulge'], curl=0.0, J=J, M=M)      # round 2: flat, no hooks
        G.tag(pc, pk=PK_WING, cu=1.0 if pl['cu'] else 0.0, pid=float(k), wbone=float(int(pl['bone'][-1])))
        pc['bone'] = pl['bone']
        pieces.append(pc)
    for name, (c, R, teeth, bone, _sp) in GEARS.items():
        cc, n = gear_axis(name, 1)
        for g in gear(cc, n, R, teeth, 0.011 if R > 0.04 else 0.009, high, spokes=6 if R > 0.05 else 5):
            G.tag(g, pk=PK_GEAR if 'hubk' not in g['a'] else PK_HUB, gid=float(int(name[-1])))
            g['bone'] = f'spin.gear{{s}}{name[-1]}' if _sp else bone
            pieces.append(g)
    return pieces


def wings(high: bool) -> list[dict]:
    out = []
    for s, tag in ((1, 'L'), (-1, 'R')):
        for pc in wing(high):
            b = pc.pop('bone')
            b = b.replace('{s}', tag) if b.startswith('spin.') else f'wing{tag}.{b[-1]}'
            out.append(G.tag(mir(pc, s), bn=float(BN[b]), side=float(s)))
    return out


# ----------------------------------------------------------------------------- the key
def key(high: bool) -> list[dict]:
    """The wind-up key: a copper housing with a brass gear ring on the back (hips), the shaft, two collars and the
    two-looped bow (spin.key; the bow's plane holds the shaft and the body's X axis at rest, as 2-turnaround's back)."""
    nu = 20 if high else 12
    a = KEY_DIR
    base = KEY_BASE
    out = []
    hous = G.tube(np.array([base - 0.03 * a, base + 0.024 * a]), 0.058, 24 if high else 16, up_hint=(1, 0, 0))
    out.append(G.tag(hous, pk=PK_KEYBASE, bn=float(BN['hips'])))
    for g in gear(base + 0.03 * a, a, 0.046, 16, 0.014, high, spokes=0, tooth=0.2):
        out.append(G.tag(g, pk=PK_KEYBASE, gid=9.0, bn=float(BN['hips'])))
    shaft = G.tube(np.array([base + 0.01 * a, base + KEY_LEN * a]), 0.019, nu, up_hint=(1, 0, 0))
    out.append(G.tag(shaft, pk=PK_KEY, bn=float(BN['spin.key'])))
    for t0, t1, r in ((0.04, 0.095, 0.028), (KEY_LEN - 0.07, KEY_LEN - 0.03, 0.026)):
        col = G.tube(np.array([base + t0 * a, base + t1 * a]), r, nu, up_hint=(1, 0, 0))
        out.append(G.tag(col, pk=PK_KEYBASE, bn=float(BN['spin.key'])))
    bow_c = base + (KEY_LEN + 0.03) * a
    side = unit(np.array([1.0, 0.0, 0.0]) - a * a[0])         # the bow's long axis (its plane holds the shaft)
    bn = unit(np.cross(a, side))                                  # the bow's face normal (it faces back at rest)
    for s in (1, -1):
        # each lobe a flat washer (round 1: two fat rings read as a jug handle; 4-details panel 5: a flat plate)
        lc = bow_c + side * (0.06 * s)
        out.append(G.tag(washer(lc, bn, 0.018, 0.055, 0.011, 40 if high else 24, up=a), pk=PK_KEY, bn=float(BN['spin.key'])))
    web = G.uv_sphere(bow_c - 0.006 * a, (0.05, 0.034, 0.034), 16 if high else 10, 8 if high else 5)
    # flatten the web into the bow's plate
    d = web['v'] - bow_c[None]
    web['v'] = bow_c[None] + d - np.outer(d @ bn, bn) * 0.86
    out.append(G.tag(web, pk=PK_KEY, bn=float(BN['spin.key'])))
    return out


# ----------------------------------------------------------------------------- the legs
def leg(high: bool, s: int) -> list[dict]:
    tag = 'L' if s > 0 else 'R'
    kn, an = mirror_pt(LEG['knee'], s), mirror_pt(LEG['ankle'], s)
    nu = 20 if high else 12
    out = []
    knee = G.uv_sphere(kn, 0.035, 18 if high else 12, 10 if high else 6)
    out.append(G.tag(knee, pk=PK_KNEE, bn=float(BN[f'leg1.{tag}'])))
    path = np.array([kn + np.array([0, 0, 0.004]), kn * 0.5 + an * 0.5, an + np.array([0, 0, 0.004])])
    boot = tube_var(path, [0.056, 0.05, 0.052], nu)
    out.append(G.tag(boot, pk=PK_BOOT, bn=float(BN[f'shin1.{tag}'])))
    for z0, z1, r in ((kn[2] - 0.034, kn[2] - 0.008, 0.062), (an[2] - 0.008, an[2] + 0.03, 0.06)):
        cuff = G.tube(np.array([[an[0], an[1] + (kn[1] - an[1]) * 0.5, z0], [an[0], an[1] + (kn[1] - an[1]) * 0.5, z1]]), r, nu, up_hint=(0, 1, 0))
        out.append(G.tag(cuff, pk=PK_CUFF, bn=float(BN[f'shin1.{tag}'])))
    fb = float(BN[f'foot1.{tag}'])
    ank = G.uv_sphere(an, 0.032, 16 if high else 10, 8 if high else 5)
    out.append(G.tag(ank, pk=PK_KNEE, bn=fb))
    for ang, ln, back in ((-30.0, 1.0, False), (0.0, 1.12, False), (30.0, 1.0, False), (180.0, 0.6, True)):
        a = math.radians(ang * s)
        d = np.array([-math.sin(a) * (1 if not back else 1), -math.cos(a), 0.0])
        if back:
            d = np.array([0.0, 1.0, 0.0])
        p0 = an + np.array([0.0, 0.0, -0.012])
        p1 = p0 + d * 0.06 * ln + np.array([0, 0, -0.016])
        p2 = p1 + d * 0.042 * ln + np.array([0, 0, -0.003])
        seg1 = tube_var(np.array([p0, 0.5 * (p0 + p1), p1]), [0.024, 0.021, 0.02], nu)
        seg2 = tube_var(np.array([p1, 0.5 * (p1 + p2), p2]), [0.02, 0.019, 0.018], nu)
        out.append(G.tag(seg1, pk=PK_TOE, bn=fb))
        out.append(G.tag(seg2, pk=PK_TOE, bn=fb))
        out.append(G.tag(G.uv_sphere(p1, 0.023, 12 if high else 8, 6 if high else 4), pk=PK_KNEE, bn=fb))
        # the claw: a curved cone hooking down to the ground
        cl = [p2, p2 + d * 0.022 + np.array([0, 0, 0.002]), p2 + d * 0.042 + np.array([0, 0, -0.008]), p2 + d * 0.052 + np.array([0, 0, -0.019])]
        cl = smooth_path(cl, 9 if high else 6)
        cl[:, 2] = np.maximum(cl[:, 2], 0.0025)
        claw = tube_var(cl, np.linspace(0.0175, 0.0035, len(cl)) * (0.85 if back else 1.0), nu)
        out.append(G.tag(claw, pk=PK_CLAW, bn=fb))
    return out


def legs(high: bool) -> list[dict]:
    return leg(high, 1) + leg(high, -1)


# ----------------------------------------------------------------------------- the head's parts
TUFT_MAIN = [(0.11, -0.06, 0.812), (0.165, -0.062, 0.855), (0.218, -0.055, 0.893), (0.248, -0.04, 0.93), (0.236, -0.025, 0.958), (0.205, -0.012, 0.972)]
TUFT_MAIN_W = [0.125, 0.105, 0.085, 0.06, 0.032, 0.005]  # round 3: broad bent plates (1-hero), not horns
TUFT_SIDE = [(0.15, 0.0, 0.797), (0.215, 0.012, 0.827), (0.262, 0.024, 0.851), (0.285, 0.036, 0.872)]
TUFT_SIDE_W = [0.085, 0.066, 0.038, 0.004]


def tufts(high: bool) -> list[dict]:
    n = 24 if high else 12
    nu = 14 if high else 8
    out = []
    for s in (1, -1):
        for pts, ws, nrm in ((TUFT_MAIN, TUFT_MAIN_W, (0.3, -0.92, 0.2)), (TUFT_SIDE, TUFT_SIDE_W, (0.25, -0.75, 0.6))):
            p = smooth_path(pts, n)
            w = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(ws)), ws)
            th = np.interp(np.linspace(0, 1, n), [0, 0.7, 1], [0.012, 0.008, 0.003])
            pc = blade(p, w, th, nrm, nu)
            G.tag(pc, pk=PK_TUFT, bn=float(BN['head']))
            out.append(mir(pc, s))
    return out


# round 1: a short hooked beak tucked between the eyes (it read as a long drooping banana)
_EZ = F.EYE[1]['z']
BEAK_UP = [(0.0, -0.236, _EZ + 0.012), (0.0, -0.26, _EZ + 0.01), (0.0, -0.279, _EZ - 0.001), (0.0, -0.289, _EZ - 0.017),
           (0.0, -0.287, _EZ - 0.031), (0.0, -0.279, _EZ - 0.038)]
# round 3: the lower half tucked up inside the upper beak (it hung below it as a dark grey wedge); it shows when the
# jaw opens
BEAK_LO = [(0.0, -0.245, _EZ - 0.006), (0.0, -0.255, _EZ - 0.009), (0.0, -0.262, _EZ - 0.013)]
JAW = {'head': (0.0, -0.246, _EZ - 0.005), 'tail': (0.0, -0.262, _EZ - 0.013)}


def beak(high: bool) -> list[dict]:
    n = 20 if high else 14
    nu = 20 if high else 16
    up = smooth_path(BEAK_UP, n)
    w = np.interp(np.linspace(0, 1, n), [0, 0.3, 0.7, 1], [0.056, 0.046, 0.024, 0.004])
    hh = np.interp(np.linspace(0, 1, n), [0, 0.3, 0.7, 1], [0.044, 0.034, 0.018, 0.004])
    # round 3: a fixed side axis (the beak lies in the YZ plane); the up-hinted frames flipped where the hook turns back
    # (an inverted, dark tip under the beak)
    t = np.gradient(up, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    b = np.tile(np.array([1.0, 0.0, 0.0]), (n, 1))
    nn = np.cross(t, b)
    nn /= np.linalg.norm(nn, axis=1, keepdims=True)
    a = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    rings = []
    for i in range(n):
        # a rounded triangle: a ridge on top, a flat underside
        c, sn = np.cos(a), np.sin(a)
        ridge = 1.0 - 0.12 * np.abs(c) * (sn > 0) - 0.2 * (sn < 0) * sn * sn
        rings.append(up[i] + 0.5 * w[i] * c[:, None] * b[i][None] + 0.5 * hh[i] * (sn * ridge)[:, None] * nn[i][None])
    pu = G.sweep(rings)
    lo = smooth_path(BEAK_LO, n)
    w2 = np.interp(np.linspace(0, 1, n), [0, 0.5, 1], [0.024, 0.017, 0.005])
    h2 = np.interp(np.linspace(0, 1, n), [0, 0.5, 1], [0.011, 0.008, 0.004])
    t2, n2, b2 = G.frames(lo, (0.0, 0.0, 1.0))
    rings2 = [lo[i] + 0.5 * w2[i] * np.cos(a)[:, None] * b2[i][None] + 0.5 * h2[i] * np.sin(a)[:, None] * n2[i][None] for i in range(n)]
    pl = G.sweep(rings2)
    return [G.tag(pu, pk=PK_BEAK, bn=float(BN['head'])), G.tag(pl, pk=PK_BEAK, bn=float(BN['jaw']), lower=1.0)]


MONO_R, MONO_TR, MONO_TZ = 0.0725, 0.0125, 0.013


def monocle_frame():
    c, xax, yax, look = F.eye_frame(1)
    return c + look * 0.006, xax, yax, look


def monocle(high: bool) -> list[dict]:
    c, xax, yax, look = monocle_frame()
    nb = float(BN['prop.monocle'])
    ring_ = torus(c, look, MONO_R, MONO_TR, MONO_TZ, 56 if high else 28, 12 if high else 8, up=yax)
    out = [G.tag(ring_, pk=PK_RING, bn=nb)]
    # the hinge bracket on the outer side: a block, a hinge pin, the screw knob pointing out and back
    bc = c + xax * (MONO_R + 0.016)
    blk = G.uv_sphere(bc, (0.016, 0.013, 0.019), 12 if high else 8, 6 if high else 4)
    out.append(G.tag(blk, pk=PK_BRACKET, bn=nb))
    pin = G.tube(np.array([bc - yax * 0.024 + xax * 0.008, bc + yax * 0.024 + xax * 0.008]), 0.0075, 12 if high else 8, up_hint=xax)
    out.append(G.tag(pin, pk=PK_BRACKET, bn=nb))
    kd = unit(xax * 1.0 + look * -0.25)
    kb = G.tube(np.array([bc + xax * 0.012, bc + xax * 0.012 + kd * 0.028]), 0.012, 16 if high else 10, up_hint=yax)
    out.append(G.tag(kb, pk=PK_KNOB, bn=nb))
    return out


# ----------------------------------------------------------------------------- the props as Blender objects
def groups(high: bool) -> dict:
    neck = G.tag(F.neck_piece(high), pk=PK_NECK, bn=float(BN['hips']))
    return {'wings': wings(high), 'key': key(high) + [neck], 'legs': legs(high), 'head': tufts(high) + beak(high) + monocle(high)}


def build(high: bool, quick: bool) -> list:
    tag = 'hi' if high else 'lo'
    obs = []
    for k, pcs in groups(high).items():
        ob = G.make_object(f'{tag}_{k}', G.merge(pcs))
        obs.append(ob)
    return obs
