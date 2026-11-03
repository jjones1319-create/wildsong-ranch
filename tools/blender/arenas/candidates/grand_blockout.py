"""Fallback candidate: our own grand amphitheatre, a quick blockout dressed with CC0 Poly Haven materials.

    py -I tools/blender/arenas/candidates/fetch_textures.py      (once)
    blender -b --factory-startup --python tools/blender/arenas/candidates/grand_blockout.py -- [--quick]

Oval stands in three tiers (~19,000 seats), a three-storey arcade with an attic, two gatehouses on the long axis,
a judges' box, banners and pennant masts. Writes art-review/arena-candidates/renders/grand_blockout_*.png + .json.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import grand_parts as G  # noqa: E402

TEX = C.CACHE / 'candidates' / 'textures'
N_SEG = 152            # sweep segments around the oval
N_BAYS = 76            # outer arcade bays
PODIUM_H = 4.2
# (rows, tread m, riser m, walkway after m, wall after m)
SECTIONS = [(14, 0.85, 0.42, 1.6, 1.3), (14, 0.85, 0.50, 1.5, 1.8), (10, 0.80, 0.55, 1.9, 0.0)]
STOREY_H = 9.0
ATTIC_H = 5.0
BANNER_COLS = [(0.30, 0.012, 0.018), (0.015, 0.04, 0.28), (0.60, 0.33, 0.03), (0.015, 0.16, 0.06)]
CROWD = [(0.32, 0.05, 0.04), (0.05, 0.10, 0.28), (0.55, 0.45, 0.28), (0.10, 0.22, 0.08), (0.45, 0.28, 0.08),
         (0.62, 0.60, 0.55), (0.18, 0.08, 0.22), (0.60, 0.30, 0.05), (0.07, 0.07, 0.08), (0.30, 0.30, 0.34)]


def materials() -> list[bpy.types.Material]:
    return [
        G.pbr('podium', TEX, 'castle_brick_07', 3.0, (0.95, 0.9, 0.85)),            # 0
        G.pbr('seats', TEX, 'large_sandstone_blocks_01', 2.5, (1.0, 0.95, 0.88)),   # 1
        G.pbr('facade', TEX, 'large_sandstone_blocks', 4.0, (1.0, 0.93, 0.82)),     # 2
        G.pbr('trim', TEX, 'large_sandstone_blocks_01', 1.5, (1.1, 1.08, 1.0), 0.1),  # 3
        C.flat_mat('shadow', (0.008, 0.007, 0.006), 0.95),                              # 4
        G.pbr('roof', TEX, 'clay_roof_tiles_02', 2.0),                               # 5
        C.flat_mat('wood', (0.25, 0.15, 0.08), 0.7),                                 # 6
        C.flat_mat('gold', (0.8, 0.6, 0.2), 0.35),                                   # 7
    ] + [G.pbr(f'cloth{i}', TEX, 'rough_linen', 1.2, c, 0.15) for i, c in enumerate(BANNER_COLS)]  # 8..11


def stands_profile() -> tuple[list, list, float, float]:
    """The bowl's cross-section from the arena wall outward, plus the seat rows for the crowd."""
    prof = [(0.0, 0.0, 0), (0.0, PODIUM_H + 1.0, 3), (0.4, PODIUM_H + 1.0, 3), (0.4, PODIUM_H, 1)]
    rows = []
    off, z = 2.2, PODIUM_H
    prof.append((off, z, 1))
    for n, tread, riser, walk, wall in SECTIONS:
        for _ in range(n):
            prof.append((off, z + riser, 1))
            z += riser
            rows.append((off, z, tread))
            off += tread
            prof.append((off, z, 1))
        off += walk
        prof.append((off, z, 0 if wall else 1))
        if wall:
            prof.append((off, z + wall, 3))
            z += wall
            prof.append((off + 0.3, z, 1))
            off += 0.3
    return prof, rows, off, z


def build(mats) -> dict:
    prof, rows, top_off, top_z = stands_profile()
    wall_off = top_off + 1.8                  # the outer wall's inner face
    depth = 2.4
    mb = G.MeshBuilder()
    G.sweep(mb, prof + [(top_off + 1.8, top_z, 1)], N_SEG)
    height = 3 * STOREY_H + ATTIC_H
    for s in range(3):                                         # outer arcade, three storeys
        G.bent_bays(mb, wall_off, depth, s * STOREY_H, STOREY_H, N_BAYS, 0.58, 0.62, 2, 2)
    G.sweep(mb, [(wall_off + depth, height, 2), (wall_off + depth, 3 * STOREY_H, 2)], N_SEG)
    G.sweep(mb, [(wall_off, top_z, 2), (wall_off, height, 2)], N_SEG)
    G.sweep(mb, [(wall_off - 0.2, height, 3), (wall_off + depth + 0.5, height, 3)], N_SEG)
    for s in range(1, 4):                                      # cornices
        z = s * STOREY_H
        G.sweep(mb, [(wall_off + depth, z + 0.3, 3), (wall_off + depth + 0.45, z + 0.15, 3),
                     (wall_off + depth + 0.45, z - 0.3, 3), (wall_off + depth, z - 0.5, 3)], N_SEG)
    amb = wall_off - 4.5                                       # ambulatory back wall, up to the seats above it
    amb_z = max(z for o, z, _ in prof if o <= amb) - 0.2
    G.sweep(mb, [(amb, amb_z, 4), (amb, 0.0, 4)], N_SEG)
    for j in range(N_BAYS):                                    # pilasters between the bays
        t = 2 * math.pi * (j + 0.5) / N_BAYS
        G.bent_box(mb, t, wall_off + depth, -0.45, 0.45, 0, 0.35, 0, 3 * STOREY_H, 3)
    for j in range(0, N_BAYS, 2):                              # pennant masts on the attic
        t = 2 * math.pi * (j + 0.5) / N_BAYS
        G.bent_box(mb, t, wall_off + depth - 0.3, -0.12, 0.12, -0.12, 0.12, height, height + 7, 6)
        G.pennant(mb, t, wall_off + depth - 0.3, height + 7, 3.2, 8 + (j // 2) % 4)
    for j in range(N_BAYS // 2):                               # podium banners
        t = 2 * math.pi * (j + 0.25) / (N_BAYS // 2)
        if min(abs(math.sin(t)), 1) < 0.2:
            continue
        G.banner(mb, t, 0.0, 1.5, PODIUM_H + 0.9, 3.4, 8 + j % 4)
    for j in range(16):                                        # great banners on the top gallery
        t = 2 * math.pi * (j + 0.5) / 16
        G.banner(mb, t, wall_off, 3.2, height - 0.6, 5.6, 8 + j % 4, 1.0)
    gates(mb)
    judges_box(mb)
    stands = mb.build('amphitheatre', mats)
    floor = sand_floor()
    ground()
    crowd = G.crowd(rows, 0.72, 7, CROWD)
    return {'rows': len(rows), 'outer_m': [round(2 * (G.A0 + wall_off + depth), 1), round(2 * (G.B0 + wall_off + depth), 1)],
            'height_m': height, 'arena_floor_m': [2 * G.A0, 2 * G.B0], 'crowd_people': len(crowd.data.vertices) // 16}


def gates(mb) -> None:
    for t in (0.0, math.pi):
        G.bent_arch(mb, t, -1.5, 8.0, 0.0, 15.0, 14.0, 6.4, 6.2, 2, 3)   # gatehouse with an arched opening
        G.bent_box(mb, t, -1.5, -7.5, 7.5, 0, 8.0, 14.0, 14.01, 2)        # roof slab
        G.bent_box(mb, t, -0.3, -3.3, 3.3, 0, 7.0, 0, 9.6, 4)             # dark tunnel behind it
        for k in range(9):                                                # raised portcullis bars
            x = -2.8 + k * 0.7
            G.bent_box(mb, t, -1.0, x - 0.06, x + 0.06, 0, 0.12, 6.4, 9.4, 6)
        G.bent_box(mb, t, -1.0, -3.0, 3.0, 0, 0.12, 6.3, 6.5, 6)
        G.bent_box(mb, t, -1.9, -7.9, 7.9, 0, 8.4, 14, 15.2, 3)  # cornice
        G.bent_box(mb, t, -1.7, -0.9, 0.9, -0.3, 0, 9.4, 13.2, 7)  # gold plaque
        for x in (-5.25, 5.25):
            G.banner(mb, t + x / G.speed(t, -1.5), -1.5, 2.6, 13.4, 9.0, 8 if t == 0 else 9, 1.0)
        for x in (-7.2, 7.2):                                  # flag poles on the gatehouse
            G.bent_box(mb, t, -1.0, x - 0.12, x + 0.12, 0, 0.24, 15.2, 22.0, 6)
            G.pennant(mb, t + x / G.speed(t, -1.0), -1.0, 22.0, 3.5, 10)


def judges_box(mb) -> None:
    t = math.pi / 2
    G.bent_box(mb, t, -2.5, -7, 7, 0, 3.0, 0, PODIUM_H + 0.4, 0)     # platform
    G.bent_box(mb, t, -2.6, -7.1, 7.1, -0.1, 3.1, PODIUM_H + 0.4, PODIUM_H + 1.3, 3)
    for x in (-6.4, -2.2, 2.2, 6.4):
        G.bent_box(mb, t, -2.5, x - 0.3, x + 0.3, 0.2, 0.8, PODIUM_H + 0.4, PODIUM_H + 6.2, 3)
    G.bent_box(mb, t, -2.8, -7.4, 7.4, -0.3, 4.0, PODIUM_H + 6.2, PODIUM_H + 6.9, 5)   # canopy
    G.banner(mb, t, -2.6, 13.0, PODIUM_H + 0.3, 2.6, 8, 0.0)


def sand_floor() -> bpy.types.Object:
    mb = G.MeshBuilder()
    n = N_SEG
    vs = [(0.0, 0.0, 0.0)] + [G.pt(2 * math.pi * j / n, 0.0, 0.0) for j in range(n)]
    mb.add(vs, [(0, 1 + j, 1 + (j + 1) % n) for j in range(n)], 0)
    return mb.build('sand_floor', [G.pbr('sand', TEX, 'coast_sand_01', 3.0, (1.05, 0.95, 0.82), 0.4)])


def ground() -> None:
    mb = G.MeshBuilder()
    mb.add([(-400, -400, -0.05), (400, -400, -0.05), (400, 400, -0.05), (-400, 400, -0.05)], [(0, 1, 2, 3)], 0)
    mb.build('ground', [G.pbr('plaza', TEX, 'coast_sand_01', 6.0, (0.62, 0.6, 0.5), 0.3)])


def main() -> None:
    quick = '--quick' in sys.argv
    C.reset()
    scene = bpy.context.scene
    eng = C.set_engine(scene, 16 if quick else 48)
    info = build(materials())
    C.world_and_sun(scene, 3.8)
    C.stand_ins(0.0)
    pct = 50 if quick else 100
    r = info['outer_m'][0] / 2
    over = C.camera('cam_overview', (-0.62 * r, -2.05 * r, 1.2 * r), (0, 0, 0.05 * r), 30)
    battle = C.camera('cam_battle', (0, -8.5, 1.6), (0, 36.0, 4.0), 22)
    gate = C.camera('cam_gate', (8.0, -3.5, 1.6), (-27.0, 0.0, 6.0), 22)
    out = C.OUT / 'grand_blockout'
    C.render(scene, over, 1600 * pct // 100, 1000 * pct // 100, Path(f'{out}_overview.png'))
    C.render(scene, battle, 1080 * pct // 100, 1920 * pct // 100, Path(f'{out}_battle.png'))
    C.render(scene, gate, 1080 * pct // 100, 1920 * pct // 100, Path(f'{out}_gate.png'))
    st = C.stats(skip=('spawnA', 'spawnB', 'ring12m', 'crowd_placeholder', 'ground'))
    st.update(info, engine=eng, name='grand_blockout')
    C.write_json(Path(f'{out}.json'), st)
    print('STATS', st, flush=True)


if __name__ == '__main__':
    main()
