"""Velvesper's high source (Art 2.1 Ultra): velvety fuzz over the whole body as small, long, soft clumps (lib/ultra.py
plate_layout, 'scale' shields drawn out along the fur's comb: down the body and the ruff, out from the face over the
head and the cheeks, down each leg; 1-hero, 4-details panels 1 and 3), baked into the normal map and AO; a socket under
each eye lens so the voxel smoothing never laps over its edge.
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import velvesper_form as F
from monsters.breeds import velvesper_paint as PT
from monsters.breeds.velvesper_form import smooth


def flow(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """The fur's comb: down the body and the legs; on the head out from the face's middle (between the eyes) and back
    over the crown, then down the cheeks."""
    g = np.tile(np.array((0.0, 0.15, -1.0)), (len(co), 1))
    hc = np.array((0.0, -0.17, 0.84))
    head = (F.head_sd(co) < 0.03) & (co[:, 2] > 0.72)
    out = co - hc
    out[:, 2] -= 0.35 * np.linalg.norm(out, axis=1)                  # outward and a little down
    g = np.where(head[:, None], out, g)
    ld, li, _down = F.leg_dist(co)
    leg = (ld < 0.012) & (co[:, 2] < 0.47)
    for j, s in enumerate((1, -1)):
        for i in range(3):
            h, k, f = F.leg_chain(i, s)
            m = leg & (li == 3 * j + i)
            dirn = np.where((co[:, 2] > k[2])[:, None], (k - h)[None], (f - k)[None])
            g = np.where(m[:, None], dirn, g)
    return g


def eye_sockets(ob) -> None:
    """Sink the skin under each lens's footprint 1 mm below the analytic head the lenses sit on (the voxel smoothing
    fills the creases round a low lens, the skin then covers its edge and clips the iris into a wedge: Galeheron);
    blended out just past the lens's rim."""
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
        lo, hi = np.full(len(P), -0.06), np.full(len(P), 0.06)
        for _ in range(36):
            mid = 0.5 * (lo + hi)
            inside = F.head_sd(P + look[None] * mid[:, None]) < 0.0
            lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
        over = -0.5 * (lo + hi) + 0.001 + F.EYE_SINK
        w = smooth(1.4, 1.0, er[sel])
        out[sel] = P - look[None] * (np.maximum(over, 0.0) * w)[:, None]
    S.set_positions(ob, out)
    C.log(f'{ob.name}: eye sockets sunk under {int(m.sum())} vertices')


def drop_islands(ob, keep: int = 500) -> None:
    """Delete loose pieces the voxel remesh chipped off thin tuft tips (single triangles after the decimation, tiny
    cubes on the source: Paladove's torn flakes)."""
    import bmesh
    me = ob.data
    n = len(me.vertices)
    ed = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get('vertices', ed)
    ed = ed.reshape(-1, 2)
    lab = np.arange(n)
    while True:
        a, b = lab[ed[:, 0]], lab[ed[:, 1]]
        m = np.minimum(a, b)
        new = lab.copy()
        np.minimum.at(new, ed[:, 0], m)
        np.minimum.at(new, ed[:, 1], m)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    ids, counts = np.unique(lab, return_counts=True)
    small = set(ids[counts < keep].tolist())
    if not small:
        return
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in range(n) if lab[i] in small], context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    C.log(f'{ob.name}: dropped {len(small)} loose pieces ({int(counts[counts < keep].sum())} vertices)')


def carve(ob) -> None:
    drop_islands(ob)
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    e = PT.eye_local(co)
    er = np.hypot(e[:, 0], e[:, 1])
    near_eye = (er < 1.5) & (np.abs(e[:, 2]) < 1.6)
    nose = (np.abs(x) < 0.035) & (y < -0.15) & (z > 0.785) & (z < 0.835)
    head = (F.head_sd(co) < 0.03) & (z > 0.72)
    ld, _li, _down = F.leg_dist(co)
    leg = (ld < 0.012) & (z < 0.47)
    # (round 1) long soft clumps combed along the fur (the head, body and legs read as matte plaster with round
    # pebbles), then fine strands over them: a directional fuzz in the normal map
    spacing = np.where(head, 0.0105, np.where(leg, 0.008, 0.012))
    spacing = np.where(near_eye | nose, np.nan, spacing)
    height = np.where(head, 0.0022, np.where(leg, 0.0018, 0.0026))
    fl = flow(co, vn)
    plates = U.plate_layout(co, vn, spacing, spacing * 1.1, height, 29, flow=fl, aspect=3.6, wobble=0.18,
                            max_candidates=90000)
    S.apply_plates(ob, plates, shape='scale', prefix='plate', edge_soft=0.35)
    co, vn = S.mesh_arrays(ob)
    fsp = np.where(near_eye | nose, np.nan, np.where(head | leg, 0.0048, 0.0058))
    fine = U.plate_layout(co, vn, fsp, fsp * 1.15, np.where(head | leg, 0.0008, 0.001), 31, flow=flow(co, vn), aspect=4.5,
                          wobble=0.2, max_candidates=120000)
    S.apply_plates(ob, fine, shape='scale', prefix='fine', edge_soft=0.3)
    eye_sockets(ob)
    co, _ = S.mesh_arrays(ob)
    S.base_attrs(ob, co)
    C.log(f'{ob.name}: {len(plates["c"])} fur clumps, {len(fine["c"])} fine strands')
