"""Reefclaw's shell carving (Art 2.1 Ultra): the carapace's lip over the belly, the spiked crown ring, round knobs,
scattered tubercles and pores (varied sizes: an even grid reads as bubble wrap), the plastron's plates, the smile and
the stalks' sockets. carve() works on the high source (the bake's normal map and the paint's masks); carve_low() puts
the relief that must reach the silhouette (the lip, the spikes, the knobs, the sockets) on the low body too.
"""
from __future__ import annotations

import numpy as np

from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import reefclaw_form as F

_LAST: dict = {}
ATTRS = ('shell', 'lip', 'under', 'spike', 'knob', 'tuber', 'peb', 'pit', 'groove', 'plate', 'mouth', 'socket', 'ridge')


def _spikes(co: np.ndarray, vn: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """Each spike a cone (0 at its base ring, 1 at its tip) along its own direction; returns the height in metres in
    column 0 and the cone share in column 1."""
    h_out, k_out = np.zeros(len(co)), np.zeros(len(co))
    for p, n, h, r in F.spike_specs():
        d = np.linalg.norm(co - p, axis=1)
        near = d < r
        if not near.any():
            continue
        k = np.clip(1.0 - d[near] / r, 0.0, 1.0) ** 1.25 * (vn[near] @ n > 0.2)
        hh = h * scale * k
        better = hh > h_out[near]
        idx = np.nonzero(near)[0][better]
        h_out[idx], k_out[idx] = hh[better], k[better]
    return np.stack([h_out, k_out], axis=1)


def _knobs(co: np.ndarray) -> np.ndarray:
    out = np.zeros(len(co))
    for phi, el, r, h in F.KNOBS:
        p = F.ell_point(phi, el)
        d = np.linalg.norm(co - p, axis=1)
        out = np.maximum(out, h * np.sqrt(np.clip(1.0 - (d / r) ** 2, 0.0, 1.0)) / 0.009)
    return out          # 0..1 at the biggest knob's crown; metres = 0.009 x this


def _sockets(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(displacement, the hole's darkness): a raised collar round each stalk and the hole it comes out of."""
    disp, hole = np.zeros(len(co)), np.zeros(len(co))
    for s in (1, -1):
        b, a = F.STALK_BASE[s], F.STALK_AXIS[s]
        v = co - b
        t = v @ a
        rho = np.linalg.norm(v - t[:, None] * a[None], axis=1)
        near = (t > -0.05) & (t < 0.04)
        disp += near * (0.006 * np.exp(-((rho - 0.031) / 0.007) ** 2) - 0.010 * smooth(0.027, 0.019, rho))
        hole = np.maximum(hole, near * smooth(0.028, 0.021, rho))
    return disp, hole


def _arm_sockets(co: np.ndarray) -> np.ndarray:
    """Round 3 (review: the arm went straight into the shell): a raised collar round each arm's root and a hollow in it."""
    disp = np.zeros(len(co))
    for s in (1, -1):
        b = v3((F.SHOULDER[0] * s, F.SHOULDER[1], F.SHOULDER[2]))
        a = v3((F.ARM_DIR[0] * s, F.ARM_DIR[1], F.ARM_DIR[2]))
        a = a / np.linalg.norm(a)
        v = co - b
        t = v @ a
        rho = np.linalg.norm(v - t[:, None] * a[None], axis=1)
        near = (t > -0.06) & (t < 0.07)
        disp += near * (0.007 * np.exp(-((rho - 0.072) / 0.011) ** 2) - 0.008 * smooth(0.064, 0.052, rho))
    return disp


def fields(co: np.ndarray, vn: np.ndarray, high: bool = True) -> dict:
    """Every carving field at the uncarved positions: 'disp' (metres along the normal) and the paint's masks."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    phi = F.phi_of(co)
    zr = F.rim_z(phi)
    e = F.ell_metric(co)
    on_cara = smooth(0.93, 0.975, e) * smooth(1.09, 1.04, e)
    shell = smooth(zr - 0.005, zr + 0.006, z)
    lip = np.exp(-((z - (zr + 0.012)) / 0.011) ** 2) * on_cara
    under = np.exp(-((z - (zr - 0.011)) / 0.008) ** 2) * on_cara
    sp = _spikes(co, vn, 1.0 if high else 0.9)
    kn = _knobs(co)
    sock, hole = _sockets(co)
    # polish: the arm sockets are collar props now (the carved hollow made a chrome-like streak at the belly's edge)
    disp = 0.016 * lip - 0.011 * under + sp[:, 0] + 0.009 * kn + sock
    out = {'shell': shell, 'lip': lip, 'under': under, 'spike': sp[:, 1], 'knob': kn, 'socket': hole,
           'tuber': np.zeros(len(co)), 'peb': np.zeros(len(co)), 'pit': np.zeros(len(co)), 'groove': np.zeros(len(co)), 'plate': np.zeros(len(co)),
           'mouth': np.zeros(len(co)), 'ridge': np.zeros(len(co))}
    if high:
        free = shell * (1.0 - smooth(0.0, 0.2, sp[:, 1])) * (1.0 - smooth(0.2, 0.6, kn)) * (1.0 - hole)
        # round 2 (review: a densely pebbled carapace, not a satin ball with painted dots): dense raised pebbles of
        # varied size all over, bigger tubercles among them; only the tubercles and a quarter of the pebbles pale-tipped
        # round 3 (review: still a satin cap): taller, denser pebbles and bigger tubercles, real bumps everywhere
        peb, ph = F.bumps(co, 0.0118, 41, (0.003, 0.0068), 0.88)
        big, bh = F.bumps(co + 0.37, 0.028, 43, (0.006, 0.011), 0.55)
        prad = 0.003 + 0.0038 * ((ph * 7.31) % 1.0)
        brad = 0.006 + 0.005 * ((bh * 7.31) % 1.0)
        tdisp = np.maximum(peb * 0.85 * prad, big * 0.8 * brad)
        out['tuber'] = np.maximum(big, peb * (ph < 0.25)) * free
        out['peb'] = peb * free
        pits, _ = F.bumps(co - 0.21, 0.016, 47, (0.0016, 0.003), 0.35)
        out['pit'] = pits * free * (1.0 - np.maximum(peb, big))
        disp += (tdisp - 0.0011 * out['pit']) * free
        # the plastron's plates: the nearest two seeds on the belly's front (x, z); a groove where they tie
        belly = (1.0 - shell) * (y < F.BELLY_C[1] + 0.07) * smooth(0.9, 0.96, F.ell_metric(co, F.BELLY_C, F.BELLY_R))
        sd = np.array(F.PLATE_SEEDS)
        d = np.sqrt((x[:, None] - sd[None, :, 0]) ** 2 + (z[:, None] - sd[None, :, 1]) ** 2)
        d.sort(axis=1)
        gap = d[:, 1] - d[:, 0]
        groove = np.exp(-(gap / 0.008) ** 2) * belly
        plate = smooth(0.0, 0.07, gap) * belly
        out['groove'], out['plate'] = groove, plate
        disp += -0.0038 * groove + 0.003 * plate
        # the smile: distance to its curve (the ends rounded)
        xm = np.clip(x, -F.MOUTH_W, F.MOUTH_W)
        dm = np.sqrt((x - xm) ** 2 + (z - F.mouth_z(xm)) ** 2) * (y < -0.1)
        dm = np.where(y < -0.1, dm, 1.0)
        out['mouth'] = smooth(0.0052, 0.0028, dm)
        disp += -0.0035 * np.exp(-(dm / 0.0042) ** 2)
        ridge = on_cara * smooth(0.04, 0.12, y) * smooth(zr + 0.02, zr + 0.08, z) * np.exp(-(x / 0.0075) ** 2)
        out['ridge'] = ridge
        disp += 0.005 * ridge
    out['disp'] = disp
    return out


def carve(ob) -> None:
    co, vn = S.mesh_arrays(ob)
    f = fields(co, vn, True)
    S.set_positions(ob, co + vn * f['disp'][:, None])
    S.base_attrs(ob, co)
    for k in ATTRS:
        S.add_attr(ob, k, f[k])
    _LAST.clear()
    _LAST.update({'n': len(co), **{k: f[k] for k in ATTRS}, 'co': co})


def carve_low(ob) -> None:
    co, vn = S.mesh_arrays(ob)
    f = fields(co, vn, False)
    S.set_positions(ob, co + vn * f['disp'][:, None])


def zones(co: np.ndarray, n=None) -> dict:
    phi = F.phi_of(co)
    zr = F.rim_z(phi)
    face = (co[:, 1] < -0.12) & (np.abs(co[:, 0]) < 0.13) & (co[:, 2] > 0.58) & (co[:, 2] < 0.72)
    return {'face': face, 'belly': co[:, 2] < zr}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """Protect the spikes' cones, the stalks' sockets and (a little) the lip from the collapse."""
    vn = np.zeros_like(co)
    vn[:, 2] = 1.0
    phi = F.phi_of(co)
    zr = F.rim_z(phi)
    keep = np.zeros(len(co))
    for p, n, h, r in F.spike_specs():
        d = np.linalg.norm(co - p, axis=1)
        keep = np.maximum(keep, smooth(r + h + 0.004, r * 0.5, d))
    for s in (1, -1):
        d = np.linalg.norm(co - F.STALK_BASE[s], axis=1)
        keep = np.maximum(keep, 0.8 * smooth(0.06, 0.035, d))
    keep = np.maximum(keep, 0.3 * np.exp(-((co[:, 2] - zr) / 0.02) ** 2))
    return keep


def preview_masks(co: np.ndarray) -> dict | None:
    """The last carve's masks when `co` is that body (the shape preview paints after carving)."""
    if _LAST and _LAST.get('n') == len(co):
        return {k: _LAST[k] for k in ATTRS}
    return None
