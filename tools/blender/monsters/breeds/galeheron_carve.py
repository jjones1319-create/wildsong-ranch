"""Galeheron's high source (Art 2.1 Ultra): soft layered contour feathers over the whole body as overlapping scale
plates (lib/ultra.py plate_layout, 'scale': each raised toward its trailing edge, combed down the body, down the neck
and back over the crown: 4-details panel 6), the legs' scutes (ring grooves down the tarsus and the toes: panel 3) and
a soft lid rim round each eye; baked into the normal map and AO.
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import galeheron_form as F
from monsters.breeds import galeheron_paint as PT
from monsters.breeds.galeheron_form import smooth

_LAST: dict = {}


def flow(co: np.ndarray, head: np.ndarray, neck: np.ndarray) -> np.ndarray:
    g = np.tile(np.array((0.0, 0.35, -1.0)), (len(co), 1))
    pts = np.array(F.NECK)
    best = np.full(len(co), np.inf)
    nd = np.zeros((len(co), 3))
    for i in range(len(pts) - 1):
        d = F.sd_tube(co, pts[i], pts[i + 1], 0.0, 0.0)
        down = F.unit(pts[i] - pts[i + 1])
        m = d < best
        best = np.where(m, d, best)
        nd[m] = down
    g = np.where(neck[:, None], nd, g)
    g = np.where(head[:, None], np.array((0.0, 1.0, -0.12))[None], g)
    return g


def scutes(co: np.ndarray, leg: np.ndarray) -> np.ndarray:
    """1 on the grooves between the scutes: rings down the tarsus (1.05 cm apart) and the toes (0.75 cm)."""
    out = np.zeros(len(co))
    for s in (1, -1):
        a, t = np.array(F.mirror(F.LEG['ankle'], s)), np.array(F.mirror(F.LEG['toe'], s))
        segs = [(a + (t - a) * 0.06, t, 0.0105, F.TARSUS_R[0] + 0.006)]
        segs += [(b, tip, 0.0075, F.TOE_R[0] + 0.005) for b, tip, _k in F.toes(s)]
        for p0, p1, per, rad in segs:
            ab = p1 - p0
            L = float(np.linalg.norm(ab))
            t_ = (co - p0) @ ab / L
            d = F.sd_tube(co, p0, p1, 0.0, 0.0)
            m = leg & (d < rad) & (t_ > 0.004) & (t_ < L - 0.004)
            f = np.mod(t_ / per, 1.0)
            out = np.where(m, np.maximum(out, smooth(0.16, 0.0, np.minimum(f, 1.0 - f))), out)
    return out


def eye_sockets(ob) -> None:
    """(polish) Sink the skin under each lens's footprint 2 mm below the analytic head the lenses sit on (the voxel
    smoothing filled the creases round the eye, so from the front the skin covered the lens's inner side and the iris
    read as a wedge); blended out just past the lens's rim."""
    co, _vn = S.mesh_arrays(ob)
    e = PT.eye_local(co)
    er = np.hypot(e[:, 0], e[:, 1])
    m = (er < 1.25) & (np.abs(e[:, 2]) < 1.6)
    if not m.any():
        return
    idx = np.nonzero(m)[0]
    out = co.copy()
    for s in (1, -1):
        sel = idx[np.sign(co[idx, 0]) == s]
        if not len(sel):
            continue
        _c, _xa, _ya, look = (np.array(v) for v in F.eye_frame(s))
        P = co[sel]
        lo, hi = np.full(len(P), -0.05), np.full(len(P), 0.06)
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            inside = F.head_sd(P + look[None] * mid[:, None]) < 0.0
            lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
        # the skin's height above the analytic head along the look; push it down to 2 mm under it, blended out
        over = -0.5 * (lo + hi) + 0.002
        w = smooth(1.2, 1.02, er[sel])
        out[sel] = P - look[None] * (np.maximum(over, 0.0) * w)[:, None]
    S.set_positions(ob, out)
    C.log(f'{ob.name}: eye sockets sunk under {int(m.sum())} vertices')


def carve(ob) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    ld, _claw = PT.leg_dist(co)
    leg = (ld < 0.008) & (z < 0.6)
    head = (F.head_sd(co) < 0.012) & (z > 1.37)
    neck = (~head) & (z > 1.02) & (F.body_sd(co) < 0.02) & (y < 0.0)
    e = PT.eye_local(co)
    er = np.hypot(e[:, 0], e[:, 1])
    near_eye = (er < 1.75) & (np.abs(e[:, 2]) < 1.6)
    face = (y < -0.222) & (z < 1.47) & (np.abs(x) < 0.04)
    spacing = np.where(head, 0.0095, np.where(neck, 0.0125, 0.0205))
    spacing = np.where(leg | near_eye | face, np.nan, spacing)
    height = np.where(head, 0.0017, np.where(neck, 0.0018, 0.0026))      # (round 3) a feather texture on the crown
    plates = U.plate_layout(co, vn, spacing, spacing * 0.98, height, 41, flow=flow(co, head, neck), aspect=1.8, wobble=0.08)
    S.apply_plates(ob, plates, shape='scale', prefix='plate', edge_soft=0.35)
    co, vn = S.mesh_arrays(ob)
    sc = scutes(co, leg)
    # the lid rim: a soft ring just outside each lens
    rim = np.exp(-((er - 1.13) / 0.09) ** 2) * (np.abs(e[:, 2]) < 1.3)
    co = co - vn * (0.0008 * sc)[:, None] + vn * (0.0006 * rim)[:, None]
    S.set_positions(ob, co)
    eye_sockets(ob)
    co, _ = S.mesh_arrays(ob)
    S.add_attr(ob, 'scute', sc)
    S.base_attrs(ob, co)
    _LAST.update({'n': len(co)})
    C.log(f'{ob.name}: {int((sc > 0.5).sum())} scute-groove vertices, {int((rim > 0.5).sum())} on the lid rims')
