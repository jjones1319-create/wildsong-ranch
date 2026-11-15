"""Scrollopus's tentacle field (Art 2.1 Ultra): for any set of points on the body, which tentacle they lie on, how far
along it (arc length), its local frame (tangent, the sucker side) and radius, and how far from its skin. The carving,
the paint and the skin weights all read it, so they agree. Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

from monsters.breeds import scrollopus_form as F
from monsters.breeds import scrollopus_noise as N

smooth = N.smooth
# round 3: how far behind its root a tentacle's first segment reaches (unbounded, the flared roots' lines ran on
# through the body and claimed the far side's skin: the quill arm's tip)
BEHIND = 0.15


def _samples():
    T = F.tentacles()
    pts = np.concatenate([m['pts'] for m in T])
    tid = np.concatenate([np.full(len(m['pts']), i) for i, m in enumerate(T)])
    idx = np.concatenate([np.arange(len(m['pts'])) for m in T])
    return T, pts, tid, idx


def nearest(co: np.ndarray) -> dict:
    """Per point: the nearest tentacle centreline ('tid'), its arc length there ('s', may run below 0 behind the root),
    the arc fraction ('u'), the centreline point ('c'), tangent ('T'), sucker side ('U'), radius ('r'), the distance
    from the centreline ('d') and the angle's cosine toward the sucker side ('cu') and its sine ('su')."""
    T, pts, tid, idx = _samples()
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(Vector(p), i)
    kd.balance()
    n = len(co)
    near = np.empty(n, np.int64)
    for i in range(n):
        near[i] = kd.find(Vector(co[i]))[1]
    t_id = tid[near]
    k = idx[near]
    out = {'tid': t_id, 's': np.zeros(n), 'u': np.zeros(n), 'c': np.zeros((n, 3)), 'T': np.zeros((n, 3)),
           'U': np.zeros((n, 3)), 'r': np.zeros(n)}
    for i, m in enumerate(T):
        sel = np.nonzero(t_id == i)[0]
        if not len(sel):
            continue
        P, S, TT, UU, RR = m['pts'], m['s'], m['T'], m['U'], m['rad']
        kk = k[sel]
        q = co[sel]
        best_s = S[kk].copy()
        best_d = np.linalg.norm(q - P[kk], axis=1)
        for dk in (-1, 0):
            a = np.clip(kk + dk, 0, len(P) - 2)
            b = a + 1
            ab = P[b] - P[a]
            L2 = np.maximum((ab * ab).sum(axis=1), 1e-12)
            t = ((q - P[a]) * ab).sum(axis=1) / L2
            lo = np.where(a == 0, -BEHIND / np.sqrt(L2), 0.0)
            hi = 1.0                                # never past the tip (a curl's last segment points back in)
            t = np.clip(t, lo, hi)
            proj = P[a] + t[:, None] * ab
            d = np.linalg.norm(q - proj, axis=1)
            sv = S[a] + t * (S[b] - S[a])
            better = d < best_d - 1e-9
            best_d = np.where(better, d, best_d)
            best_s = np.where(better, sv, best_s)
        out['s'][sel] = best_s
        out['u'][sel] = best_s / m['L']
        sc = np.clip(best_s, 0.0, m['L'])
        for k3 in range(3):
            out['c'][sel, k3] = np.interp(sc, S, P[:, k3]) + np.minimum(best_s, 0.0) * TT[0, k3]
            out['T'][sel, k3] = np.interp(sc, S, TT[:, k3])
            out['U'][sel, k3] = np.interp(sc, S, UU[:, k3])
        out['r'][sel] = np.interp(sc, S, RR)
    out['T'] /= np.maximum(np.linalg.norm(out['T'], axis=1, keepdims=True), 1e-12)
    out['U'] = out['U'] - out['T'] * (out['U'] * out['T']).sum(axis=1, keepdims=True)
    out['U'] /= np.maximum(np.linalg.norm(out['U'], axis=1, keepdims=True), 1e-12)
    q = co - out['c']
    d = np.linalg.norm(q, axis=1)
    qn = q / np.maximum(d, 1e-9)[:, None]
    out['d'] = d
    out['cu'] = (qn * out['U']).sum(axis=1)
    out['su'] = (qn * np.cross(out['T'], out['U'])).sum(axis=1)
    return out


def tentacle_share(co: np.ndarray, fld: dict | None = None) -> np.ndarray:
    """0..1: how much a body point belongs to a tentacle (1 on its skin past the core, 0 on the head and the core)."""
    f = fld if fld is not None else nearest(co)
    on = smooth(f['r'] * 1.25 + 0.02, f['r'] * 1.05, f['d'])
    past = smooth(0.06, 0.13, f['s'])
    return on * past


def bone_u(m: dict, s: np.ndarray) -> np.ndarray:
    """A tentacle's arc length → its bone index space (0 at the root … 4 at the tip; the held part rigid at 3.5+)."""
    kn = m['knots']
    u = np.interp(s, kn, np.arange(len(kn), dtype=np.float64))
    u = np.where(s < 0.0, s / max(kn[1], 1e-6), u)
    return np.minimum(u, float(len(kn) - 1))


def chain_rows(m: dict, s: np.ndarray) -> dict[str, np.ndarray]:
    """Triangular blends centred on each bone (as lib.ultra.chain_weights), by the bone index space; the root fades to
    `hips` (the core it grows from)."""
    u = bone_u(m, s)
    n = len(m['knots']) - 1
    raw = [np.clip(1.0 - np.abs(u - (k + 0.5)), 0.0, 1.0) for k in range(n)]
    raw[0] = np.where(u < 0.5, 1.0, raw[0])
    raw[-1] = np.where(u > n - 0.5, 1.0, raw[-1])
    tot = np.maximum(sum(raw), 1e-9)
    par = smooth(0.42, -0.1, u)
    out = {'hips': par}
    for k in range(n):
        out[f"{m['name']}.{k + 1}"] = raw[k] / tot * (1.0 - par)
    return out


def body_weight_region(co: np.ndarray, names: list[str]):
    """One region over every vertex near a tentacle: each tentacle's chain blends by how near its skin the vertex lies
    (neighbours share the webbing between them smoothly); what is left goes to `hips`."""
    T = F.tentacles()
    n = len(co)
    share = np.zeros((n, len(T)))
    rows = []
    for i, m in enumerate(T):
        P, S, R = m['pts'], m['s'], m['rad']
        best_d = np.full(n, np.inf)
        best_s = np.zeros(n)
        for a in range(len(P) - 1):
            ab = P[a + 1] - P[a]
            L2 = max(float(ab @ ab), 1e-12)
            t = ((co - P[a]) @ ab) / L2
            t = np.clip(t, -BEHIND / np.sqrt(L2) if a == 0 else 0.0, 1.0)
            d = np.linalg.norm(co - (P[a] + t[:, None] * ab), axis=1)
            better = d < best_d
            best_d = np.where(better, d, best_d)
            best_s = np.where(better, S[a] + t * (S[a + 1] - S[a]), best_s)
        r = np.interp(np.clip(best_s, 0, m['L']), S, R)
        share[:, i] = best_d - r                   # the gap to this tentacle's skin (metres; < 0 inside it)
        rows.append(chain_rows(m, best_s))
        if i == 0:
            s_root = np.zeros((n, len(T)))
        s_root[:, i] = best_s
    # each vertex belongs to its nearest tentacle; where two fuse (the crotch between their roots) they share it over
    # about a centimetre of gap, so a tentacle lifting away never drags its neighbour's skin into a sheet
    gap = share
    gmin = gap.min(axis=1)
    soft = np.exp(-(gap - gmin[:, None]) / 0.0045)
    soft /= soft.sum(axis=1, keepdims=True)
    s_near = (soft * s_root).sum(axis=1)
    # near the core the skin fades onto `hips`; past the root a vertex is wholly its tentacle's, even inside a curl's
    # filled middle or a wrap's web (1-3 cm from any centreline)
    out_k = smooth(0.11, 0.2, s_near)
    near = np.maximum(smooth(0.026, 0.004, gmin), out_k * smooth(0.09, 0.05, gmin)) * smooth(0.0, 0.05, s_near)
    share = soft * near[:, None]
    # the head's own skin keeps its heat weights (what is left would go to `hips`, which never turns with the head)
    on_head = (F.mantle_sdf(co) < 0.006) & (co[:, 2] > F.ROOT_Z - 0.04)          # round 3: the head 5 cm lower
    share[on_head] = 0.0
    tot = share.sum(axis=1)
    mask = tot > 1e-4
    wd: dict[str, np.ndarray] = {'hips': np.zeros(n)}
    for i, m in enumerate(T):
        for b, w in rows[i].items():
            wd[b] = wd.get(b, np.zeros(n)) + share[:, i] * w
    wd['hips'] += 1.0 - share.sum(axis=1)
    return mask, {b: w[mask] for b, w in wd.items() if b in names}
