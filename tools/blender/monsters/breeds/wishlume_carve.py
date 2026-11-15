"""Wishlume's carving (wishlume_ultra.py): the voxel union laid onto the exact lantern profile, the opening's inner
dome, and on the high source the paper's soft creases, the paddles' rolled rims and the smile's faint ink groove.

Both bodies take the profile and the dome (carve_low), so the silhouette and the opening match the bake's cage.
"""
from __future__ import annotations

import numpy as np

from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import wishlume_form as F

_CREASES: list = []


def shape_paper(co: np.ndarray) -> np.ndarray:
    """Every point of the paper onto the profile (bulging panels, dips at the ribs); the paddles keep their own shape
    past a short fillet; the bottom cap below the opening becomes the inside dome, seen through the ring."""
    ak = F.arm_k(co)
    snapped = F.globe_point(co)
    w = (1.0 - ak)[:, None]
    out = snapped * w + co * (1 - w)
    low = (out[:, 2] < F.Z_OPEN) & (ak < 0.5)
    if low.any():
        s = F.ellip_r(out[low]) / F.R_OPEN
        out[low, 2] = F.dish_z(s)
    return out


def creases() -> list[tuple[np.ndarray, np.ndarray, float]]:
    """Soft creases in the paper (4-details 2, 6; round 2: two or three per panel, deeper, so the head close-ups show
    them): (start, end, depth), none on the face, on the paddles' roots or at the opening; a fixed seed."""
    if _CREASES:
        return _CREASES
    rng = np.random.default_rng(14)
    for k in range(F.RIBS):
        mid = F.RIB_STEP * (k + 0.5)
        made, tries = 0, 0
        while made < 3 and tries < 60:
            tries += 1
            th = ((mid + rng.uniform(-11, 11)) + 180) % 360 - 180
            z = float(rng.uniform(F.Z_OPEN + 0.04, F.TOP_Z - 0.05))
            if abs(th) < 40 and 0.46 < z < 0.71:
                continue                                   # the face panel stays plain for the ink
            if abs(abs(th) - 90) < 28 and 0.36 < z < 0.6:
                continue                                   # the paddles' roots
            a = F.surface_dir(th, z)
            _n, t, _b = F.tangent_frame(a, float(rng.uniform(-75, 75)))
            L = float(rng.uniform(0.04, 0.09))
            b = F.surface_dir(*_theta_z(a + t * L))
            _CREASES.append((np.array(a[:]), np.array(b[:]), float(rng.uniform(0.0011, 0.0016))))
            made += 1
    return _CREASES


def _theta_z(p) -> tuple[float, float]:
    import math
    return math.degrees(math.atan2(p[0], -p[1])), float(p[2])


def crease_field(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(valley, shoulder) 0..1 of the creases at each point: a narrow fold with a soft raised edge beside it, fading at
    both ends; the depth share is scaled by each crease's depth."""
    val = np.zeros(len(co))
    sh = np.zeros(len(co))
    for a, b, dep in creases():
        ab = b - a
        L2 = float(ab @ ab)
        box = np.all(np.abs(co - (a + b) / 2) < np.abs(ab) / 2 + 0.008, axis=1)
        if not box.any():
            continue
        q = co[box]
        t = np.clip(((q - a) @ ab) / L2, 0, 1)
        d = np.linalg.norm(q - (a + t[:, None] * ab), axis=1)
        end = np.sin(np.pi * t) ** 0.5 * dep / 0.0016
        val[box] = np.maximum(val[box], np.exp(-(d / 0.0016) ** 2) * end)
        sh[box] = np.maximum(sh[box], np.exp(-((d - 0.0035) / 0.0018) ** 2) * end)
    return val, sh


def rim_band(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """0..1 on each paddle's rolled rim: where its skin turns edge-on to the broad face (the red cord round the
    paddle, 4-details 3), past the root's fillet."""
    out = np.zeros(len(co))
    ak = F.arm_k(co)
    for s in (1, -1):
        _al, fa, _up = F.arm_axes(s)
        on = (np.sign(co[:, 0]) == s) & (ak > 0.6)
        if not on.any():
            continue
        loc = F.arm_local(co[on], s)
        root = smooth(-0.125, -0.1, loc[:, 0])            # not where the paddle grows out of the globe
        d = np.abs(vn[on] @ v3(fa))
        out[on] = smooth(0.38, 0.24, d) * root
    return out


def smile_z(x: np.ndarray) -> np.ndarray:
    a = np.clip(np.abs(x) / F.MOUTH_W, 0, 1.2)
    return F.MOUTH_Z - F.MOUTH_SAG * (1 - a ** 2) + 0.0035 * smooth(0.8, 1.08, a)


def mouth_mask(co: np.ndarray) -> np.ndarray:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    a = np.abs(x) / F.MOUTH_W
    w = 0.0024 * (1 - 0.45 * np.clip(a, 0, 1) ** 2)
    return np.exp(-((z - smile_z(x)) / w) ** 2) * smooth(1.1, 0.98, a) * (y < -0.15)


def carve(ob) -> None:
    co, _vn = S.mesh_arrays(ob)
    co = shape_paper(co)
    S.set_positions(ob, co)
    co, vn = S.mesh_arrays(ob)
    cr, sh = crease_field(co)
    rim = rim_band(co, vn)
    mouth = mouth_mask(co)
    # a crease is a fold (round 2: 1.6 mm deep with a soft raised shoulder); the rim a rolled edge; the smile a faint dent
    disp = -0.0016 * cr + 0.0005 * sh + 0.0008 * rim - 0.0004 * mouth
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': mouth})
    S.add_attr(ob, 'crease', cr)
    S.add_attr(ob, 'armk', F.arm_k(co))


def carve_low(ob) -> None:
    co, _vn = S.mesh_arrays(ob)
    S.set_positions(ob, shape_paper(co))


def _check() -> str:
    """A quick sanity line for the shape preview's log."""
    p = np.array([[0.0, -0.3, F.C0[2]], [0.3, 0.0, F.C0[2]], [0.0, 0.0, 1.0], [0.0, 0.0, 0.0]])
    g = F.globe_point(p)
    return 'globe: front y %.3f, side x %.3f, top z %.3f, bottom z %.3f; eye L %s' % (
        g[0, 1], g[1, 0], g[2, 2], g[3, 2], tuple(round(v, 3) for v in F.EYE_C[1]))

