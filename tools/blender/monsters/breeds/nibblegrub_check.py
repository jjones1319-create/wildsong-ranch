"""Nibblegrub's every-frame clip checker (a dev tool, not part of the build): poses the rigged game mesh on every frame
of every clip and reports, per clip, where it goes wrong:
  - ground: the lowest point of each part (feet, toe beads, head and cheeks, antenna balls, the trunk) below the floor;
  - buried: surface points that end up inside the body (each vertex pushed 4 mm out along its posed normal, then a
    parity ray test against the whole posed mesh): a leg through the belly, the head through a segment, a crease
    folding into itself;
  - stretch: the worst edge stretch and squash against the rest pose, per part (a cheek torn by the chew).
For the cocoon (--cocoon): the core's points outside the closed shell before the split, and the shells' and the core's
stretch.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b tools/blender/out/nibblegrub-ultra/rigged.blend \
        --python tools/blender/monsters/breeds/nibblegrub_check.py -- [--step 1] [--clips a,b] [--cocoon]
Writes check.json beside the .blend.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))        # tools/blender → lib, monsters

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from lib import anim as A  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
STEP = int(argv[argv.index('--step') + 1]) if '--step' in argv else 1
ONLY = argv[argv.index('--clips') + 1].split(',') if '--clips' in argv else None
COCOON = '--cocoon' in argv
WHERE = '--where' in argv                       # also print each part's worst edge (its stretch and rest position)
OUT = Path(bpy.data.filepath).parent


def clips_from_scene() -> list:
    data = json.loads((OUT / 'clips.json').read_text(encoding='utf-8'))
    out = []
    for name, d in data.items():
        act = bpy.data.actions.get(name)
        if act is not None:
            out.append(A.ClipMeta(name=name, frames=int(round(d['seconds'] * A.FPS)), loop=d['loop'], hold=d['hold'],
                                  root_speed=d['rootSpeed'], markers=[], faces=[], action=act))
    return out


def posed(obs) -> tuple[np.ndarray, np.ndarray, list]:
    """Every listed mesh evaluated (world space): (vertices, normals, [(start, polygons)])."""
    dg = bpy.context.evaluated_depsgraph_get()
    cos, nos, polys = [], [], []
    n0 = 0
    for ob in obs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        me.vertices.foreach_get('co', co)
        no = np.empty(n * 3, np.float32)
        me.vertex_normals.foreach_get('vector', no)
        M = np.array(ev.matrix_world)
        co = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
        no = no.reshape(-1, 3) @ M[:3, :3].T
        no /= np.maximum(np.linalg.norm(no, axis=1, keepdims=True), 1e-9)
        cos.append(co)
        nos.append(no)
        polys.append([[i + n0 for i in p.vertices] for p in me.polygons])
        ev.to_mesh_clear()
        n0 += n
    return np.concatenate(cos), np.concatenate(nos), polys


def inside(bvh: BVHTree, pts: np.ndarray) -> np.ndarray:
    """Parity of ray hits along +z and along +x (both odd = inside)."""
    res = np.zeros(len(pts), bool)
    for k, p in enumerate(pts):
        votes = 0
        for d in (Vector((0.0, 0.0, 1.0)), Vector((0.70710678, 0.0, 0.70710678))):
            o = Vector(p)
            hits = 0
            for _ in range(24):
                loc, _n, _i, _dist = bvh.ray_cast(o, d)
                if loc is None:
                    break
                hits += 1
                o = loc + d * 1e-4
            votes += hits % 2
        res[k] = votes == 2
    return res


def parts_of(co: np.ndarray) -> dict:
    """Rest-pose part masks for the report (Nibblegrub's form; the cocoon's are its meshes)."""
    from monsters.breeds import nibblegrub_form as F
    x, z = co[:, 0], co[:, 2]
    ds, db = F.antenna_dist(co)
    ant = ((ds < F.ANT_R[0] + 0.02) | (db < F.BALL_R + 0.01)) & (z > 0.66)
    legs = (F.leg_dist(co) < F.LEG_R[0] + 0.015) & (z < 0.13) & (np.abs(x) > 0.12) | (F.toe_dist(co) < F.TOE_R + 0.006)
    cheek = (F.cheek_q(co) < 1.15) & ~ant
    head = (F.head_zone(co) > 0.5) & ~ant & ~cheek & ~legs
    trunk = ~(ant | legs | cheek | head)
    return {'legs': legs, 'antenna': ant, 'cheek': cheek, 'head': head, 'trunk': trunk}


def edges_of(polys: list) -> np.ndarray:
    e = set()
    for group in polys:
        for p in group:
            for a, b in zip(p, p[1:] + p[:1]):
                e.add((min(a, b), max(a, b)))
    return np.array(sorted(e), np.int64)


def main() -> None:
    O = bpy.data.objects
    arm = next(o for o in O if o.type == 'ARMATURE')
    sc = bpy.context.scene
    if COCOON:
        meshes = [O[n] for n in ('lo_body', 'lo_props') if n in O]
    else:
        meshes = [O['lo_body']]
    for o in O:
        if o.type == 'MESH' and o not in meshes:
            o.hide_viewport = True
    A.rest_pose(arm)
    sc.frame_set(1)
    bpy.context.view_layer.update()
    co0, no0, polys = posed(meshes)
    if COCOON:
        nb = len(meshes[0].data.vertices)
        parts = {'core': np.arange(len(co0)) < nb, 'shell': np.arange(len(co0)) >= nb}
        shell_polys = polys[1] if len(polys) > 1 else []
    else:
        parts = parts_of(co0)
    E = edges_of(polys)
    L0 = np.linalg.norm(co0[E[:, 0]] - co0[E[:, 1]], axis=1)
    E, L0 = E[L0 > 0.004], L0[L0 > 0.004]           # sliver edges' ratios mean nothing
    rng = np.random.default_rng(5)
    sample = {k: rng.permutation(np.nonzero(m)[0])[:900 if k == 'trunk' else 500] for k, m in parts.items()}
    report = {}
    for m in clips_from_scene():
        if ONLY and m.name not in ONLY:
            continue
        A.clear_clip(arm)
        A.set_clip(arm, m)
        worst = {'ground': {}, 'buried': {}, 'stretch': {}, 'squash': {}}
        for f in range(1, m.frames + 1, STEP):
            sc.frame_set(f)
            bpy.context.view_layer.update()
            co, no, pl = posed(meshes)
            for k, msk in parts.items():
                zmin = float(co[msk, 2].min()) if msk.any() else 0.0
                if zmin < worst['ground'].get(k, (9.0, 0))[0]:
                    worst['ground'][k] = (zmin, f)
            L = np.linalg.norm(co[E[:, 0]] - co[E[:, 1]], axis=1)
            r = L / np.maximum(L0, 1e-9)
            for k, msk in parts.items():
                em = msk[E[:, 0]] & msk[E[:, 1]]
                if em.any():
                    hi, lo = float(np.percentile(r[em], 99.9)), float(np.percentile(r[em], 0.1))
                    if hi > worst['stretch'].get(k, (0.0, 0))[0]:
                        e = E[em][int(np.argmax(r[em]))]
                        where = tuple(round(float(v), 2) for v in 0.5 * (co0[e[0]] + co0[e[1]]))
                        worst['stretch'][k] = (hi, f, where, round(float(r[em].max()), 1))
                    if lo < worst['squash'].get(k, (9.0, 0))[0]:
                        worst['squash'][k] = (lo, f)
            if COCOON:
                # the core's points outside the shell's volume (only while it is shut: before the split opens it)
                if shell_polys and (m.name != 'split' or f <= int(0.56 * m.frames)):
                    # a core point is enclosed when a ray from it straight out from the egg's axis meets the shell
                    bvh = BVHTree.FromPolygons([tuple(v) for v in co], shell_polys)
                    idx = sample['core']
                    cen = co[parts['core']].mean(axis=0)
                    n_out = 0
                    for p in co[idx]:
                        d = p - cen
                        d[2] = 0.0
                        L = float(np.linalg.norm(d))
                        if L < 1e-3:
                            continue
                        loc, _n, _i, _dist = bvh.ray_cast(Vector(p), Vector(d / L))
                        n_out += loc is None
                    out_pts = None
                    if n_out > worst['buried'].get('core_out', (-1, 0))[0]:
                        worst['buried']['core_out'] = (n_out, f)
            else:
                bvh = BVHTree.FromPolygons([tuple(v) for v in co], pl[0])
                for k, idx in sample.items():
                    if not len(idx):
                        continue
                    b = int(inside(bvh, co[idx] + no[idx] * 0.004).sum())
                    if b > worst['buried'].get(k, (-1, 0))[0]:
                        worst['buried'][k] = (b, f)
        report[m.name] = worst
        g = ' '.join(f"{k} {v[0] * 1000:+.0f}mm@{v[1]}" for k, v in worst['ground'].items())
        b = ' '.join(f"{k} {v[0]}@{v[1]}" for k, v in worst['buried'].items() if v[0] > 0)
        st = ' '.join(f"{k} {v[0]:.2f}@{v[1]}" + (f" max {v[3]} at {v[2]}" if WHERE and len(v) > 2 else '') for k, v in worst['stretch'].items() if v[0] > 1.35)
        sq = ' '.join(f"{k} {v[0]:.2f}@{v[1]}" for k, v in worst['squash'].items() if v[0] < 0.6)
        print(f'CHECK {m.name:12s} {m.frames:4d}f | ground {g} | buried {b or "-"} | stretch {st or "-"} | squash {sq or "-"}', flush=True)
    A.clear_clip(arm)
    (OUT / 'check.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(f'CHECK written {OUT / "check.json"} (buried counts are out of {", ".join(f"{k} {len(v)}" for k, v in sample.items())})')


main()
