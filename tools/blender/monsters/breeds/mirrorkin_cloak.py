"""Mirrorkin's violet silk ribbon cloak (mirrorkin_ultra.build_props; 1-hero, 2-turnaround, 4-details 5):

- The mantle: the cloth bunched over the frame's shoulders, one thick scrunched roll that follows the frame's outer
  edge from the left clasp up over the top (behind the crest) to the right clasp, puffed out behind the frame (the side
  view's hood) and pinched into each clasp. Rigid on `head`.
- Two panels: from the gather behind each side gem the silk falls and flares like a half cone wrapped round the
  outside and the back, down to a wavy hem (lowest at its front tip, highest at the outer side). Each rides a 3-bone
  `ribbon` chain (cloakL / cloakR) down its axis. Thick sheets with their own unwrap; deep folds; the attributes ed
  (distance to the free edge) and es (arc length along it) carry the gold trim and the embroidered border.
Part ids: MANTLE, PANEL. Pure numpy.
"""
from __future__ import annotations

import math

import numpy as np

from lib.surface import smooth
from monsters.breeds import mirrorkin_form as F
from monsters.breeds import mirrorkin_mesh as MM

MANTLE, PANEL = 30, 31
D2R = math.pi / 180.0

# ----------------------------------------------------------------------------- the panels
GATHER = (0.255, 0.04, 0.776)          # the left panel's gather, behind the side gem (mirrored for the right)
HEM_C = (0.3, 0.125, 0.12)             # its axis's lower end (review round 2: closer and straighter under the knot)
R_TOP, R_HEM = 0.026, 0.13
A_FRONT, A_BACK = -58.0, 162.0          # the sheet wraps from out-front round the outside to back-in, its inner edge
                                        # tucked behind the frame (degrees)
# the hem's height round the panel (u 0 the front edge's foot .. 1 the back-inner edge): highest where the front edge
# meets the outer corner, lowest at the back (2-turnaround front, side, back)
# round 1: swallow-tailed: two pointed tails (one out at the side, the longer one at the back) between higher arcs
TAILS = ((0.3, 0.16, 0.1), (0.76, 0.17, 0.15))       # (u, half width, how far the point drops)
HEM_BASE = 0.235
PANEL_T = 0.0055


def axis_point(v, s: int) -> np.ndarray:
    v = np.asarray(v, np.float64)
    g, h = np.array(GATHER), np.array(HEM_C)
    p = g[None] + (h - g)[None] * v.reshape(-1, 1)
    p[:, 0] += 0.01 * np.sin(np.pi * np.clip(v.reshape(-1), 0, 1))
    p[:, 0] *= s
    return p.reshape(np.shape(v) + (3,))


def chain_points(s: int) -> list[tuple[float, float, float]]:
    return [tuple(map(float, axis_point(np.array([v]), s)[0])) for v in (0.0, 1 / 3, 2 / 3, 1.0)]


def tail_k_old(u) -> np.ndarray:
    """0..1: how near a tail's point (sharp)."""
    u = np.asarray(u, np.float64)
    out = np.zeros_like(u)
    for c, w, _d in TAILS:
        out = np.maximum(out, np.clip(1.0 - np.abs(u - c) / w, 0, 1) ** 1.3)
    return out  # (unused since review round 2)


def hem_z(u) -> np.ndarray:
    """Review round 2: one smooth S-curve round the panel (higher at the front edge's foot, lowest toward the back),
    not zig-zag tails."""
    u = np.asarray(u, np.float64)
    return 0.215 - 0.1 * smooth(0.1, 0.78, u) + 0.03 * np.sin(2 * np.pi * 1.25 * u + 0.4)


def tail_k(u) -> np.ndarray:
    """How far the hem rolls out (the lower, back part rolls most)."""
    return 0.5 + 0.5 * smooth(0.2, 0.8, np.asarray(u, np.float64))


def folds(u, v, high: bool) -> np.ndarray:
    """The silk's folds: a relative bulge growing down the panel (deep, soft), with fine ripples on the high source."""
    f = fold_shape(u, v) * 0.27 * v ** 0.8
    if high:
        # soft secondary folds only (round 2: fine regular ripples baked into stripes)
        f = f + 0.012 * v * np.sin(2 * np.pi * 7.7 * u + 3.0 * v + 0.4)
    return f


def fold_shape(u, v) -> np.ndarray:
    """The folds' pattern round the panel, -1 .. 1 (crests positive)."""
    # review round 2: rounder folds (broad crests, narrower hollows)
    w = 0.6 * np.sin(2 * np.pi * 3.2 * u + 0.5) + 0.4 * np.sin(2 * np.pi * 5.3 * u + 1.7 + 2.0 * v)
    return np.sign(w) * np.abs(w) ** np.where(w > 0, 0.7, 1.3)


def panel_grid(s: int, nu: int, nv: int, high: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    u = np.linspace(0.0, 1.0, nu + 1)
    v = np.linspace(0.0, 1.0, nv + 1)
    U, V = np.meshgrid(u, v)
    zt, zb = GATHER[2], HEM_C[2]
    # each column ends at its hem (a small extra wave along it)
    hz = hem_z(U) + 0.018 * np.sin(2 * np.pi * 3.3 * U + 0.8) * smooth(0.0, 0.1, U) * smooth(1.0, 0.9, U)
    vu = V * (zt - hz) / (zt - zb)
    A = axis_point(vu, s)
    r = R_TOP + (R_HEM - R_TOP) * np.clip(vu, 0, None) ** 0.75
    # the silk bells out toward the hem (2-turnaround: the hems flare wide and wave)
    r = r * (1.0 + folds(U, V, high)) * (1.0 + 0.06 * smooth(0.55, 1.0, V))
    # review round 2: the hem rolls outward and up in a curling S (not flat zig-zag tails)
    tk = tail_k(U)
    r = r * (1.0 + 0.12 * tk * smooth(0.84, 1.0, V))
    # the front edge flares forward and out as it falls (2-turnaround front: it sweeps out from the clasp to the outer
    # corner, the lining showing as its edge turns over); both free edges wave instead of falling straight
    al = (A_FRONT + (A_BACK - A_FRONT) * U - 22.0 * smooth(0.18, 0.0, U) * V
          + 6.0 * np.sin(2 * np.pi * 1.4 * V + 0.6) * V * smooth(0.22, 0.0, U)
          + 8.0 * np.sin(2 * np.pi * 1.1 * V + 1.9) * V * smooth(0.78, 1.0, U)) * D2R
    d = np.stack([np.cos(al) * s, np.sin(al), np.zeros_like(al)], axis=-1)
    G = A + r[..., None] * d
    G[..., 2] += 0.022 * tk * smooth(0.86, 1.0, V) ** 2
    return G, U, V


def panel_edges(G: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(ed, es) per grid point: the distance along the sheet to the nearest free edge (the front, the hem, the back)
    and the arc length along that edge."""
    su = np.concatenate([np.zeros((G.shape[0], 1)), np.cumsum(np.linalg.norm(np.diff(G, axis=1), axis=-1), axis=1)], axis=1)
    sv = np.concatenate([np.zeros((1, G.shape[1])), np.cumsum(np.linalg.norm(np.diff(G, axis=0), axis=-1), axis=0)], axis=0)
    d_front = su
    d_back = su[:, -1:] - su
    d_hem = sv[-1:, :] - sv
    ed = np.minimum(np.minimum(d_front, d_back), d_hem)
    es = np.where(d_hem <= np.minimum(d_front, d_back), su, sv)
    return ed, es


def panels(kit: MM.Kit, high: bool) -> None:
    nu, nv = (150, 110) if high else (30, 22)
    for s in (1, -1):
        G, U, V = panel_grid(s, nu, nv, high)
        ed, es = panel_edges(G)
        thick = PANEL_T + 0.003 * smooth(0.012, 0.0, ed)       # the rolled, gold-trimmed edge is a little thicker
        ax = axis_point(np.linspace(0, 1.1, 60), s)

        def inside(p, ax=ax):
            d = np.linalg.norm(p[:, None, :] - ax[None], axis=-1)
            return ax[np.argmin(d, axis=1)]
        fd = np.clip(fold_shape(U, V) * smooth(0.05, 0.35, V), -1, 1)
        kit.shell(G, thick, PANEL, pr=0.25 + 0.5 * (s > 0), inside=inside, texel_k=0.8, inner_k=0.5, wall_k=0.8,
                  extra={'ed': ed, 'es': es, 'fd': fd})


# ----------------------------------------------------------------------------- the mantle
PHI0, PHI1 = -6.0, 186.0
MANTLE_T = 0.006


def mantle_spec(phi_deg: np.ndarray) -> dict:
    """Along the frame's edge, by the angle from the nearer clasp (0) to the top (90): how far the drape reaches in
    over the back from the frame's outer edge (2-turnaround back: about a quarter of the back's width at the shoulders,
    just behind the crest at the top), how much it puffs out round the edge (the front view's shoulder puffs, the side
    view's hood) and how much of the cross-section is left where it gathers into each clasp."""
    psi = np.minimum(phi_deg - PHI0, PHI1 - phi_deg) + PHI0      # 0 at a clasp .. 96 at the top
    k_sh = np.exp(-((psi - 40.0) / 24.0) ** 2)
    k_top = smooth(55.0, 92.0, psi)
    gather = smooth(-6.0, 22.0, psi)
    # review round 2: the cloth sags lowest in the middle of the back (a gathered sag, not an arch along the frame)
    # (rising steadily toward the top: a dip between the shoulder and the top left gold 'ears' showing)
    reach = (0.04 + 0.12 * smooth(18.0, 90.0, psi)) * gather + 0.012
    puff = (0.02 + 0.028 * k_sh + 0.012 * k_top) * (0.35 + 0.65 * gather)
    return {'reach': reach, 'puff': puff, 'gather': gather}


def mantle_grid(nu: int, nv: int, high: bool) -> tuple[np.ndarray, np.ndarray]:
    """The drape's middle surface: u along the frame's edge (clasp to clasp over the top), v across it from its free
    edge on the back, out round the frame's outer edge, to its edge tucked behind the frame's front."""
    phi = np.linspace(PHI0, PHI1, nu + 1)
    sp = mantle_spec(phi)
    ph = phi * D2R
    x, z = F.oval_xz(ph, F.BAND_SIDE)
    edge = np.stack([x, np.zeros_like(x), z], axis=1)
    radial = np.stack([np.cos(ph), np.zeros_like(ph), np.sin(ph)], axis=1)
    # bunched folds along the edge: the puff swells and dips every ~7 cm (calmer toward the gathers)
    L = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(edge, axis=0), axis=1))])
    # round 2: a few broad, uneven folds (regular ribs and the high source's fine ripples read as a fluted shell)
    # round 3: soft, uneven folds (the smooth version read as a cushion)
    # round 4 (review round 1): calmer along the edge (it read lumpy); the folds now run across the drape (below)
    fold = (0.08 * np.sin(2 * np.pi * L / 0.15 + 0.6) * (0.55 + 0.45 * np.sin(2 * np.pi * L / 0.41 + 1.0))
            + 0.03 * np.sin(2 * np.pi * L / 0.083 + 1.9))
    # the back edge hangs in shallow swags between the folds
    # review round 2: the back edge sags in soft gathered scallops (it read as a sharp horseshoe)
    swag = 0.07 * np.sin(2 * np.pi * L / 0.2 + 2.2)
    G = np.zeros((nv + 1, nu + 1, 3))
    FD = np.zeros((nv + 1, nu + 1))
    w = np.linspace(0.0, 1.0, nv + 1)
    for i in range(nu + 1):
        g = sp['gather'][i]
        re, pf = sp['reach'][i] * (1.0 + swag[i] * g), sp['puff'][i] * (1.0 + fold[i] * g)
        # the cross-section in (out from the frame's edge, depth): back-inner edge, its bulge, round the edge, the tuck
        # review round 2: clear of the back plate's raised rim moulding (y 0.06), which poked through as gold 'ears'
        ctrl = np.array([(-re, 0.069), (-0.45 * re, 0.072 + 0.5 * pf), (0.35 * pf, 0.068 + 0.55 * pf),
                         (0.8 * pf + 0.006, 0.04 + 0.2 * pf), (0.45 * pf + 0.004, 0.018), (-0.004, 0.012)])
        # at a gather the whole section draws in toward the clasp's knot
        knot = np.array((0.012, 0.035))
        ctrl = knot + (ctrl - knot) * (0.3 + 0.7 * g)
        c = MM.catmull(np.column_stack([ctrl, np.zeros(len(ctrl))]), nv + 1)[:, :2]
        # round 1: three or four soft folds running along the drape (from behind the crest down to each knot), across
        # its width: the section is pushed out and in along its own normal (it read as a smooth roll, a bun)
        tng = np.gradient(c, axis=0)
        nrm2 = np.stack([tng[:, 1], -tng[:, 0]], axis=1)
        nrm2 /= np.maximum(np.linalg.norm(nrm2, axis=1, keepdims=True), 1e-9)
        if float((nrm2[:, 0] * (c[:, 0] - 0.0)).mean() + (nrm2[:, 1] * (c[:, 1] - 0.03)).mean()) < 0:
            nrm2 = -nrm2
        win = smooth(0.0, 0.18, w) * smooth(1.0, 0.7, w)
        sw = np.sin(2 * np.pi * 3.6 * w + 0.9 + 1.2 * np.sin(phi[i] * D2R * 2.0))
        wave = np.sign(sw) * np.abs(sw) ** 0.7
        # review round 2: deeper at the front (it read as a smooth inflated tube) and bunching toward the knots
        amp = 0.0085 + 0.006 * smooth(0.4, 0.75, w) + 0.004 * (1.0 - g)
        c = c + nrm2 * (amp * (0.5 + 0.5 * g) * win * wave)[:, None]
        FD[:, i] = wave * win
        G[:, i, :] = edge[i][None] + radial[i][None] * c[:, :1]
        G[:, i, 1] = c[:, 1]
    return G, FD


def mantle(kit: MM.Kit, high: bool) -> None:
    nu, nv = (300, 56) if high else (84, 22)
    G, FD = mantle_grid(nu, nv, high)
    su = np.concatenate([np.zeros((nv + 1, 1)), np.cumsum(np.linalg.norm(np.diff(G, axis=2 - 1), axis=-1), axis=1)], axis=1)
    sv = np.concatenate([np.zeros((1, nu + 1)), np.cumsum(np.linalg.norm(np.diff(G, axis=0), axis=-1), axis=0)], axis=0)
    ed = sv                                                    # the free edge is the back-inner one (v = 0)
    oc = np.array([0.0, 0.03, F.ZC])

    def inside(p):
        return np.repeat(oc[None], len(p), axis=0)
    kit.shell(G, MANTLE_T, MANTLE, pr=0.5, inside=inside, texel_k=0.75, inner_k=0.45, wall_k=0.6, extra={'ed': ed, 'es': su, 'fd': FD})
    # a knot of gathered silk behind each clasp, where the drape and the panel meet
    for s in (1, -1):
        g = np.array(GATHER) * np.array((s, 1, 1))
        P = np.array([g + np.array((-0.022 * s, -0.012, 0.012)), g + np.array((0.0, 0.0, 0.0)), g + np.array((0.016 * s, 0.01, -0.014))])
        n = 18 if high else 11
        tt = np.linspace(0.0, 1.0, n)
        rad = 0.022 + 0.014 * np.sin(np.pi * np.clip(tt * 1.15, 0, 1)) ** 0.7
        kit.tube(MM.catmull(P, n), rad, 18 if high else 12, MANTLE, pr=0.6 + 0.1 * s, hint=(0.0, 1.0, 0.0), aspect=1.15,
                 relief=lambda pa, ss: 0.0025 * np.sin(2 * np.pi * pa * 4.0 + 25.0 * ss), texel_k=0.75, ed=1.0)


def objects(high: bool) -> list:
    tag = 'hi' if high else 'lo'
    a, b = MM.Kit(), MM.Kit()
    mantle(a, high)
    panels(b, high)
    m = a.object(f'{tag}_mantle')
    m['prop'] = 'mantle'
    p = b.object(f'{tag}_panels')
    p['prop'] = 'panels'
    return [m, p]
