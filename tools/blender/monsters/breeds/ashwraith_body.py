"""Ashwraith's voxel body (ashwraith_ultra.py): two closed extras united by build_body (round 2 of the review).

- The hood: a closed, star-shaped surface round H0 (an icosphere's directions pushed out to ashwraith_form.hood_r):
  the outer cloth, the soft overhanging brim, the torn rolled rim, the inner wall falling back into the opening and
  the dark face egg filling it; a soft point rising toward the tip.
- The core: no body inside the shroud (the card), only a slim dark core with a rounded underside, seen through the
  cloth's tears and under its hems; it is painted dark, its lower half glowing warm with embers.
The cloth itself (cape, front panels, wisps) are props (ashwraith_cloth.py, ashwraith_wisps.py).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.mesh import Part
from lib.surface import smooth, v3
from monsters.breeds import ashwraith_form as F
from monsters.breeds import ashwraith_mesh as AM

ICO_LEVEL = 7


def _recalc(ob: bpy.types.Object) -> None:
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def hood_object(name: str = 'ash_hood') -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=ICO_LEVEL, radius=1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    d = co.reshape(-1, 3).astype(np.float64)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    r, _k = F.hood_r(d)
    me.vertices.foreach_set('co', (F.H0 + d * r[:, None]).astype(np.float32).ravel())
    me.update()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


def core_object(name: str = 'ash_core', n_th: int = 200) -> bpy.types.Object:
    th = np.linspace(-math.pi, math.pi, n_th, endpoint=False)
    rings = [F.core_point(th, np.full(n_th, z)) for z in np.linspace(0.72, 0.3, 50)]
    a, b, yc = F.core_abyc(0.3)
    low = F.core_point(th, np.full(n_th, 0.3))
    ctr = np.array([0.0, float(yc), 0.3])
    for t in np.linspace(0.08, 0.94, 18):
        s = math.cos(t * math.pi / 2)
        q = ctr + (low - ctr) * s
        q[:, 2] = 0.3 - (0.3 - F.CORE_BOTTOM) * math.sin(t * math.pi / 2)
        rings.append(q)
    _a, _b, ytop = F.core_abyc(0.72)
    return AM.closed_object(name, rings, (np.array([0.0, float(ytop), 0.72]), np.array([0.0, float(yc), F.CORE_BOTTOM])))


def body_extras() -> list[bpy.types.Object]:
    objs = [hood_object(), core_object()]
    for o in objs:
        _recalc(o)
    return objs


def all_parts() -> list[Part]:
    """Only a small filler hidden inside the core (the weight proxy is built from the parts)."""
    return [Part('core_fill', 'sphere', loc=(0.0, 0.02, 0.48), radius=0.12)]


def _seg_near(p: np.ndarray, pts, r: float) -> np.ndarray:
    d = np.full(len(p), np.inf)
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.array(a), np.array(b)
        ab = b - a
        u = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
        d = np.minimum(d, np.linalg.norm(p - (a + u[:, None] * ab), axis=1))
    return d


def zones(co: np.ndarray, n=None) -> dict:
    """Masks and shares per body point: face (the dark egg), open_k (the opening's share: 0 on the hood's outer cloth,
    1 on the face, between on the rim's inner side), hood (the hood's outer cloth), core (the dark core under the
    cloth), eye_d."""
    p = np.asarray(co, np.float64)
    z = p[:, 2]
    rel = p - F.H0
    dist = np.linalg.norm(rel, axis=1)
    d = rel / np.maximum(dist, 1e-9)[:, None]
    r, k = F.hood_r(d)
    rf = F.face_r(d)
    upper = z > 0.585
    face = (k > 0.6) & (dist < rf + 0.012) & upper
    open_k = np.clip(k, 0, 1) * smooth(0.57, 0.6, z)
    near_hood = dist > r - 0.012
    core = (F.core_outside(p) < 0.012) & ~near_hood & ~face
    core |= (z < 0.55) & ~(np.abs(dist - r) < 0.012)    # round 3: not the hood's back, which now hangs to z ~0.5
    hood = ~face & ~core & (open_k < 0.5)
    return {'face': face, 'open_k': open_k, 'hood': hood, 'core': core, 'eye_d': F.eye_dist(p), 'muzzle': np.zeros(len(p), bool)}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """The face round the eyes, the torn rim, the hood's point (it faceted) and its cloth; the hidden core least."""
    zz = zones(co)
    rim = smooth(0.15, 0.6, zz['open_k']) * (1 - zz['face'])
    peak = smooth(0.9, 0.98, co[:, 2])
    return np.clip(0.5 * zz['face'] + (zz['eye_d'] < 0.075) * 1.0 + 0.7 * rim + 0.6 * peak + 0.25 * zz['hood'], 0, 1)


# ----------------------------------------------------------------------------- the carving (high source)
def hood_creases(p: np.ndarray) -> np.ndarray:
    """Soft creases on the hood's dome, the cloth gathering up into its point, and folds falling from the brim."""
    root = v3(F.H0 + F.PEAK_DIR * 0.3)
    rel = p - root
    dist = np.linalg.norm(rel, axis=1)
    ang = np.arctan2(rel[:, 0], rel[:, 1] + 1e-9)
    radial = np.sin(6.0 * ang + 0.5 * np.sin(8.0 * dist)) * smooth(0.03, 0.1, dist) * smooth(0.4, 0.16, dist)
    return 0.004 * radial


def carve(ob) -> None:
    co, vn = S.mesh_arrays(ob)
    zz = zones(co)
    disp = hood_creases(co) * zz['hood'] * smooth(0.6, 0.7, co[:, 2])
    # (polish: no fine relief on the rim's lip; under the brim it baked into a dithered black fringe)
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, S.mesh_arrays(ob)[0])
