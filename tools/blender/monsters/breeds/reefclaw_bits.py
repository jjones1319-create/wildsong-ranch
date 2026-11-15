"""Reefclaw's small rigid parts (Art 2.1 Ultra), all props:
- the barnacle shoulder armour (4-details panel 6): two clusters of volcano barnacles of mixed sizes, ribbed plates, a
  crater with its plates inside, leaning out of the cluster (rigid on `hips`);
- the eye stalks (bending on their two bones), the cup at each stalk's top that holds the eyeball from behind, and the
  closed-lid ball inside each lens (rigid on the stalk's tip: the blink squashes the lens and shows it);
- the visors (4-details panels 1 and 2): little knightly cone hats with a rolled brim, a knob on top and a band of
  triangular windows (painted dark and inset), rigid on their visor bones.
"""
from __future__ import annotations

import math

import numpy as np

from lib.surface import smooth, v3
from monsters.breeds import reefclaw_form as F
from monsters.breeds import reefclaw_geo as G

# --------------------------------------------------------------------------- the eyes' frame (shared with the recipe)
EYE_R = 0.066                       # round 3 (review): bigger eyes


def eye_frame(s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(centre, across (+X-ish), up, out) of the eye on side s: it looks ahead, a little outward and down."""
    c = v3((0.13 * s, -0.115, 0.85))
    d = G.unit((0.26, -0.97, 0.0))       # round 3 (review): both gaze about 15 degrees toward the 3/4 camera's side
    u = G.unit(v3((0.0, 0.0, 1.0)) - d * d[2])
    x = np.cross(u, d)
    return c, x, u, d


def stalk_points(s: int) -> list[np.ndarray]:
    """The stalk's bone points: base (in the socket), mid, tip (in the cup behind the eye)."""
    c, _x, u, d = eye_frame(s)
    tip = c + (EYE_R + 0.008) * G.unit(-0.55 * d - 0.83 * u)
    base = v3((0.115 * s, -0.07, 0.665))
    return [base, base + 0.5 * (tip - base) + v3((0.002 * s, 0.004, 0.0)), tip]


def visor_frame(s: int) -> tuple[np.ndarray, np.ndarray]:
    """(brim centre, axis): the cone hat sits on the eye's top, tipped forward."""
    c, _x, u, d = eye_frame(s)
    ax = G.unit(u + 0.25 * d)               # round 3: a bell tipped about 14 degrees forward, on the eye's top quarter
    return c + u * 0.045 + d * 0.003, ax


def visor_bone(s: int) -> tuple[tuple, tuple]:
    c, _x, u, d = eye_frame(s)
    h = c + u * 0.06 - d * 0.04
    return tuple(map(float, h)), tuple(map(float, h + d * 0.08))


# --------------------------------------------------------------------------- barnacles
CLUSTER = (73.0, 28.0)          # phi, elevation on the carapace (mounded on each shoulder's top; mirrored)
# (d phi, d elevation, radius, lean out of the cluster, lift off the shell: some sit on the others) - round 2 (review):
# bigger and denser, mounded on top of the front of each shoulder
BARNACLES = [(0, 0, 0.05, 0.0, 0.0), (-11, 9, 0.042, 0.3, 0.0), (11, 9, 0.04, 0.3, 0.0), (13, -8, 0.044, 0.3, 0.0),
             (-12, -9, 0.04, 0.35, 0.0), (0, 17, 0.034, 0.45, 0.0), (-21, 1, 0.036, 0.4, 0.0), (22, 2, 0.034, 0.4, 0.0),
             (1, -17, 0.036, 0.45, 0.0), (-19, 16, 0.028, 0.5, 0.0), (19, 17, 0.029, 0.5, 0.0), (-3, 26, 0.024, 0.55, 0.0),
             (25, -15, 0.027, 0.5, 0.0), (-24, -15, 0.028, 0.5, 0.0), (30, 10, 0.024, 0.55, 0.0), (-30, 11, 0.025, 0.55, 0.0),
             (4, 6, 0.032, 0.25, 0.04), (-7, -3, 0.028, 0.3, 0.036), (8, -6, 0.024, 0.35, 0.034), (-4, 12, 0.022, 0.4, 0.03)]


def barnacle_specs(s: int) -> list[dict]:
    pc = F.ell_point(CLUSTER[0] * s, CLUSTER[1])
    out = []
    for j, (dp, de, r, lean, lift) in enumerate(BARNACLES):
        p = F.ell_point((CLUSTER[0] + dp) * s, CLUSTER[1] + de)
        n = F.ell_normal(p)
        p = p + n * lift
        away = p - pc
        away = away - n * float(away @ n)
        ax = G.unit(n + lean * (G.unit(away) if np.linalg.norm(away) > 1e-6 else 0.0))
        h = r * (1.25 + 0.25 * ((j * 0.618) % 1.0))
        out.append({'base': p - n * 0.004, 'axis': ax, 'r': r, 'h': h, 'phase': (j * 1.7 + (0.4 if s < 0 else 0.0)) % (2 * math.pi), 'seed': j})
    return out


def _barnacle(b: dict, high: bool):
    r, h = b['r'], b['h']
    prof = [(0.0, -0.014), (0.98 * r, -0.014), (r, 0.0), (0.96 * r, 0.25 * h), (0.86 * r, 0.55 * h), (0.72 * r, 0.82 * h),
            (0.62 * r, 0.95 * h), (0.55 * r, h), (0.46 * r, 0.97 * h), (0.41 * r, 0.86 * h), (0.36 * r, 0.74 * h),
            (0.26 * r, 0.77 * h), (0.11 * r, 0.83 * h), (0.0, 0.82 * h)]
    if not high:
        prof = [prof[i] for i in (0, 2, 4, 6, 7, 8, 10, 12, 13)]
    ph = b['phase']
    wall = {k for k, (_r, hh) in enumerate(prof) if 0.0 < hh <= 0.95 * h and _r > 0.6 * r}

    def rmod(th, k):
        if k not in wall:
            return np.ones_like(th)
        plates = 0.075 * np.cos(6 * th + ph)
        ribs = 0.028 * np.cos(30 * th + 2 * ph) if high else 0.0
        return 1.0 + plates + ribs

    def hmod(th, k):
        return 0.06 * h * np.cos(6 * th + ph) if prof[k][1] >= 0.95 * h else np.zeros_like(th)
    V, faces, tk = G.lathe(prof, 96 if high else 18, b['base'], b['axis'], rmod=rmod, hmod=hmod)
    faces = G.orient(V, faces)
    kk = tk[:, 1].astype(int)
    hh = np.array([prof[k][1] for k in kk]) / h
    rr = np.array([prof[k][0] for k in kk]) / r
    crater = ((hh < 0.99) & (rr < 0.5)).astype(float)
    rib = 0.5 + 0.5 * np.cos(30 * tk[:, 0] + 2 * ph) if high else np.zeros(len(V))
    plate_gap = np.clip(1.0 - (np.cos(6 * tk[:, 0] + ph) + 1.0) * 2.0, 0.0, 1.0)
    rim = (hh > 0.93).astype(float) * (1 - crater)
    return V, faces, {'crater': crater, 'rib': rib * (1 - crater), 'pgap': plate_gap * (1 - crater), 'brim': rim, 'bh': hh}


def barnacles(high: bool) -> list:
    out = []
    pre = 'hi' if high else 'lo'
    for s in (1, -1):
        Vs, Fs, A = [], [], {}
        for b in barnacle_specs(s):
            V, faces, at = _barnacle(b, high)
            off = sum(len(v) for v in Vs)
            Vs.append(V)
            Fs += [tuple(i + off for i in f) for f in faces]
            for k, v in at.items():
                A.setdefault(k, []).append(v)
        V = np.concatenate(Vs)
        ob = G.mesh(f"{pre}_barnacles{'L' if s > 0 else 'R'}", V, Fs)
        if high:
            G.tag(ob, 70, kind=2.0, **{k: np.concatenate(v) for k, v in A.items()})
        else:
            G.tag(ob, 70)
        out.append(ob)
    return out


# --------------------------------------------------------------------------- eye stalks, cups, lid balls
def stalk(s: int, high: bool):
    b, m, t = stalk_points(s)
    path = np.concatenate([np.linspace(b - (m - b) * 0.25, m, 6)[:-1], np.linspace(m, t, 6)])
    ts = np.linspace(0.0, 1.0, len(path))
    radii = 0.0175 + 0.0025 * np.exp(-(ts / 0.18) ** 2) + 0.0055 * smooth(0.7, 1.0, ts)
    radii[0] = radii[-1] = 0.0
    V, faces, tk = G.sweep(path, radii, 40 if high else 12)
    ob = G.mesh(f"{'hi' if high else 'lo'}_stalk{'L' if s > 0 else 'R'}", V, G.orient(V, faces))
    return ob, tk


def cup_and_lid(s: int, high: bool):
    """The cup that holds the eyeball from behind and below, and the closed-lid ball inside the lens."""
    c, _x, u, d = eye_frame(s)
    ro, ri = EYE_R + 0.012, EYE_R * 1.005
    n = 30 if high else 8
    al = np.radians(np.linspace(0.0, 70.0, n))
    prof = [(0.0, ro)] + [(ro * math.sin(a), ro * math.cos(a)) for a in al[1:]] + \
        [(ri * math.sin(a), ri * math.cos(a)) for a in al[::-1][:-1]] + [(0.0, ri)]
    back = G.unit(-0.92 * d - 0.38 * u)
    Vc, Fc, _ = G.lathe(prof, 96 if high else 22, c, back)
    rl = EYE_R * 0.98
    lp = [(rl * math.sin(a), -rl * math.cos(a)) for a in np.radians(np.linspace(0.0, 180.0, 91 if high else 9))]
    lp[0], lp[-1] = (0.0, -rl), (0.0, rl)
    Vl, Fl, _ = G.lathe(lp, 128 if high else 16, c, u)
    return (Vc, G.orient(Vc, Fc)), (Vl, G.orient(Vl, Fl))


def visor(s: int, high: bool):
    """Round 3 (review: bell or lampshade shapes, not party-hat cones; the hollow inside showed dark): a solid bell with
    a rounded crown, gently flaring sides and a rolled brim wider than the eye, its underside a shallow dish that rests on
    the eye's top quarter. A band of six triangular windows (alternating point up and point down; 4-details) is cut in.
    Returns (verts, faces, window depth 0..1: a bevel round each window, 1 at its floor)."""
    o, ax = visor_frame(s)
    RB, HV = 0.08, 0.09
    key_s = np.array([0.0, 0.06, 0.16, 0.34, 0.55, 0.74, 0.88, 1.0])
    key_r = np.array([0.0, 0.01, 0.019, 0.03, 0.04, 0.05, 0.063, RB - 0.004])
    key_h = np.array([HV, HV - 0.002, HV - 0.009, HV - 0.026, HV - 0.047, HV - 0.066, HV - 0.079, 0.006])
    n = 44 if high else 10
    ss = np.linspace(0.0, 1.0, n + 1)
    outer = [(0.0, HV)] + [(float(np.interp(t, key_s, key_r)), float(np.interp(t, key_s, key_h))) for t in ss[1:]]
    brim = [(RB, 0.003), (RB + 0.003, -0.003), (RB - 0.002, -0.009), (RB - 0.012, -0.008)]
    under = [(0.05, -0.005), (0.026, -0.003), (0.0, -0.002)]
    prof = outer + brim + under
    seg = 192 if high else 36
    V, faces, tk = G.lathe(prof, seg, o, ax, ref=eye_frame(s)[3])
    kk = tk[:, 1].astype(int)
    hrel = np.array([prof[k][1] for k in kk]) / HV
    rr = np.array([prof[k][0] for k in kk])
    is_out = np.array([1 <= k <= n for k in kk])
    sector = tk[:, 0] / (2 * math.pi) * 6.0
    u = sector % 1.0
    flip = (np.floor(sector) % 2).astype(bool)
    band = 0.4 * HV
    v = (hrel - 0.2) / 0.4
    v = np.where(flip, 1.0 - v, v)
    width = rr * 2 * math.pi / 6.0
    margin = np.minimum(np.minimum((0.4 * (1.0 - v) - np.abs(u - 0.5)) * width, v * band), (1.0 - v) * band)
    win = smooth(-0.0015, 0.004, margin) * is_out
    return V, faces, win


def arm_sockets(high: bool) -> list:
    """Polish (review: the arm ended against the belly/shell seam with no socket): a rigid shell collar round each arm's
    root, the arm turning inside it (rides `hips`)."""
    out = []
    for s in (1, -1):
        b = v3((F.SHOULDER[0] * s, F.SHOULDER[1], F.SHOULDER[2]))
        a = G.unit(v3((F.ARM_DIR[0] * s, F.ARM_DIR[1], F.ARM_DIR[2])))
        prof = [(0.052, -0.045), (0.07, -0.045), (0.08, -0.015), (0.078, 0.012), (0.068, 0.022), (0.058, 0.016), (0.054, -0.01)]
        prof = prof + [prof[0]]                                 # a closed ring
        V, faces, tk = G.lathe(prof, 64 if high else 20, b, a)
        ob = G.mesh(f"{'hi' if high else 'lo'}_socket{'L' if s > 0 else 'R'}", V, G.orient(V, faces))
        if high:
            rim = np.array([prof[int(k)][1] > 0.005 for k in tk[:, 1]], float)
            inner = np.array([prof[int(k)][0] < 0.06 for k in tk[:, 1]], float)
            G.tag(ob, 70, kind=6.0, rim=rim, inner=inner)
        else:
            G.tag(ob, 70)
        out.append(ob)
    return out


def eye_parts(high: bool) -> list:
    out = []
    pre = 'hi' if high else 'lo'
    for s in (1, -1):
        t = 'L' if s > 0 else 'R'
        st, tk = stalk(s, high)
        out.append(G.tag(st, 81 if s > 0 else 82, kind=3.0, along=tk[:, 1]) if high else G.tag(st, 81 if s > 0 else 82))
        (Vc, Fc), (Vl, Fl) = cup_and_lid(s, high)
        V = np.concatenate([Vc, Vl])
        faces = [tuple(f) for f in Fc] + [tuple(i + len(Vc) for i in f) for f in Fl]
        ob = G.mesh(f'{pre}_cup{t}', V, faces)
        if high:
            lid = np.concatenate([np.zeros(len(Vc)), np.ones(len(Vl))])
            G.tag(ob, 83 if s > 0 else 84, kind=4.0, lid=lid)
        else:
            G.tag(ob, 83 if s > 0 else 84)
        out.append(ob)
        V, faces, win = visor(s, high)
        ob = G.mesh(f'{pre}_visor{t}', V, G.orient(V, faces))
        G.displace(ob, -0.009 * win)                        # the windows cut in deep, with a bevel
        if high:
            G.tag(ob, 85 if s > 0 else 86, kind=5.0, win=win)
        else:
            G.tag(ob, 85 if s > 0 else 86)
        out.append(ob)
    return out
