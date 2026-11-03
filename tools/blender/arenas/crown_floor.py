"""The Crown Amphitheatre's sand floor and the duel ring's barrier.

Three floor meshes with planar bake UVs (they keep them; the bake does not repack them): the ring disc (r ≤ 9.5 m,
2048² over 19 m, about 108 px/m) and the two halves of the sand out to the podium (x < 0 and x ≥ 0, 2048 × 1536 over
41 × 30.7 m, 50 px/m). The ring: a marble curb at r = 6.0–6.35 m with bronze posts and a sagging crimson rope, open on
the A–B axis where the fighters walk in, taller posts with finials either side of each opening.
"""
from __future__ import annotations

import math
from pathlib import Path

import bpy
import numpy as np

from lib import common as C
from lib.nodes import new_mat
import kit as K
from crown_geo import A0, B0, MB, lathe
from crown_mats import attr, mul, obj_co
from crown_relief import relief
import crown_layout as L

RING_DISC = 9.5
APRON_UV = {'w': (-28.0, -20.5, 30.72, 41.0), 'e': (0.0, -20.5, 30.72, 41.0)}     # x0, y0, x span (v), y span (u)
OPEN_HALF = 1.25            # half the barrier's openings on the A–B axis


def relief_images(emblem) -> dict:
    """The relief maps as packed byte images: the ring (2048² over ±9.5 m) and the whole floor (4096 × 3072)."""
    out = {}
    for name, rect, (w, h) in (('ring', (-RING_DISC, RING_DISC, -RING_DISC, RING_DISC), (2048, 2048)),
                               ('floor', (-28.0, 28.0, -21.0, 21.0), (4096, 3072))):
        import hashlib
        src = (Path(__file__).parent / 'crown_relief.py').read_bytes() + repr((rect, w, h, L.SUN_DIR)).encode()
        cache = C.OUT_ROOT / 'arena-crown' / f'relief_{name}_{hashlib.md5(src).hexdigest()[:10]}.npy'
        if cache.exists():
            rgb = np.load(cache)
        else:
            with C.Timer(f'relief {name}'):
                rgb = relief(*rect, w, h, L.SUN_DIR, emblem)
            np.save(cache, rgb)
        img = bpy.data.images.new(f'relief_{name}', w, h, alpha=False, float_buffer=False)
        img.colorspace_settings.name = 'Non-Color'
        img.pixels.foreach_set(np.concatenate([rgb, np.ones((h, w, 1), np.float32)], -1).ravel())
        img.pack()
        out[name] = (img, rect)
    return out


def sand_mat(reliefs: dict) -> bpy.types.Material:
    """Warm arena sand: two CC0 photo sands, big soft tone patches, then the relief's light, the disturbed sand and
    the chalk; a damp darker band against the podium wall."""
    m, nb = new_mat('sand')
    co = obj_co(nb)
    x, y, _ = nb.sep(co)
    d1, _ = K.tex_nodes(nb, 'coast_sand_01', K.coords(nb, 'Object', 2.2), 'FLAT', normal=False)
    d2, _ = K.tex_nodes(nb, 'raked_dirt', K.coords(nb, 'Object', 2.8, 0.6), 'FLAT', normal=False)
    c1 = K.grade(nb, d1.outputs['Color'], 0.5, 0.95, 1.12, C.srgb('#E1C595'), 0.3, 0.0)
    c2 = K.grade(nb, d2.outputs['Color'], 0.5, 0.85, 1.25, C.srgb('#D7B686'), 0.35, 0.0)
    col = nb.mix(nb.smooth(nb.noise(co, 0.12, 3.0, 0.55), 0.4, 0.62), c1, c2)
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(nb.noise(co, 0.06, 2.0, 0.5), 0.5, 0.75), 0.4), col, C.lin('#C9A06A'))
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(nb.noise(co, 0.09, 2.0, 0.5), 0.55, 0.8), 0.3), col, C.lin('#EAD6AE'))
    r = nb.vmath('LENGTH', nb.comb(x, y, 0.0))
    samples = []
    for name in ('ring', 'floor'):
        img, (x0, x1, y0, y1) = reliefs[name]
        u = nb.math('DIVIDE', nb.math('SUBTRACT', x, x0), x1 - x0)
        v = nb.math('DIVIDE', nb.math('SUBTRACT', y, y0), y1 - y0)
        t = nb.new('ShaderNodeTexImage', image=img, interpolation='Linear')
        t.extension = 'EXTEND'
        nb.link(nb.comb(u, v, 0.0), t.inputs['Vector'])
        samples.append(t.outputs['Color'])
    rel = nb.mix(nb.smooth(r, RING_DISC - 0.6, RING_DISC - 0.2), samples[0], samples[1])
    lr, dist, chalk = nb.sep_rgb(rel)
    col = mul(nb, col, nb.math('MULTIPLY', lr, 2.0))
    col = nb.mix(nb.math('MULTIPLY', dist, 0.55), col, mul(nb, nb.mix(0.5, col, C.lin('#A97F52')), 0.85))
    col = nb.mix(chalk, col, C.lin('#F6F0E2'))
    # the damp band against the podium (elliptical distance to the wall under ~1.2 m) and sand drifts in its foot
    rho = nb.math('SQRT', nb.math('ADD', nb.math('POWER', nb.math('DIVIDE', x, A0), 2.0), nb.math('POWER', nb.math('DIVIDE', y, B0), 2.0)))
    wall = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, rho), B0)
    damp = nb.math('MULTIPLY', nb.smooth(wall, 1.4, 0.1), nb.smooth(nb.noise(co, 0.8, 3.0, 0.6), 0.25, 0.6))
    col = nb.mix(nb.math('MULTIPLY', damp, 0.45), col, mul(nb, col, 0.72))
    K.principled(nb, col, 0.95, K.bump_from(nb, K.lum(nb, d1.outputs['Color']), 0.15, 0.01), 0.2)
    return m


def ring_disc(mat: int, step_r: int = 14, segs: int = 112) -> MB:
    mb = MB()
    rings = list(np.linspace(0.0, RING_DISC, step_r + 1))
    verts = [(0.0, 0.0, 0.0)]
    for r in rings[1:]:
        verts += [(r * math.cos(2 * math.pi * s / segs), r * math.sin(2 * math.pi * s / segs), 0.0) for s in range(segs)]
    base = mb.verts(verts)
    S = 2 * RING_DISC

    def uv(i):
        x, y, _ = verts[i]
        return (x, y), ((x + RING_DISC) / S, (y + RING_DISC) / S)
    for s in range(segs):
        idx = [0, 1 + s, 1 + (s + 1) % segs]
        mb.face([base + i for i in idx], [uv(i)[0] for i in idx], [uv(i)[1] for i in idx], mat, {'lite': 1})
    for k in range(len(rings) - 2):
        for s in range(segs):
            a, b = 1 + k * segs + s, 1 + k * segs + (s + 1) % segs
            idx = [a, a + segs, b + segs, b]
            mb.face([base + i for i in idx], [uv(i)[0] for i in idx], [uv(i)[1] for i in idx], mat, {'lite': 1})
    return mb


def apron(side: str, mat: int, nr: int = 10, segs: int = 112) -> MB:
    """The sand from the ring disc out to the wall (and a little under it), one half."""
    mb = MB()
    x0, y0, xs, ys = APRON_UV[side]
    angs = np.linspace(math.pi / 2, 3 * math.pi / 2, segs // 2 + 1) if side == 'w' else np.linspace(-math.pi / 2, math.pi / 2, segs // 2 + 1)
    grid = []
    for a in angs:
        ca, sa = math.cos(a), math.sin(a)
        rw = 1.0 / math.sqrt((ca / (A0 + 0.5)) ** 2 + (sa / (B0 + 0.5)) ** 2)      # to just under the podium's foot
        grid.append([((RING_DISC + (rw - RING_DISC) * (k / nr) ** 1.1) * ca, (RING_DISC + (rw - RING_DISC) * (k / nr) ** 1.1) * sa, 0.0) for k in range(nr + 1)])
    for j in range(len(angs) - 1):
        for k in range(nr):
            q = [grid[j][k], grid[j][k + 1], grid[j + 1][k + 1], grid[j + 1][k]]      # out, then counter-clockwise: up
            b = mb.verts(q)
            mb.face(range(b, b + 4), [(p[0], p[1]) for p in q], [((p[1] - y0) / ys, (p[0] - x0) / xs) for p in q], mat, {'lite': 1})
    return mb


def barrier(mats: dict) -> MB:
    """The ring's marble curb, bronze posts and crimson rope (gaps on the A–B axis)."""
    mb = MB()
    R0, R1 = L.RING_R, L.RING_R + 0.35
    prof = [(R0, 0.0), (R0, 0.17), (R0 + 0.05, 0.24), (R1 - 0.05, 0.24), (R1, 0.17), (R1, 0.0)]
    gap = math.asin(OPEN_HALF / R0)
    for a0, a1 in ((gap, math.pi - gap), (math.pi + gap, 2 * math.pi - gap)):
        n = 40
        for i0 in range(0, n, 8):
            angs = [a0 + (a1 - a0) * k / n for k in range(i0, i0 + 9)]
            _circle_sweep(mb, prof, angs, mats['curb'])
        for a in (a0, a1):
            ca, sa = math.cos(a), math.sin(a)
            pts = [(r * ca, r * sa, z) for r, z in prof]
            mb.quad(pts if a == a1 else pts[::-1], [(r, z) for r, z in prof] if a == a1 else [(r, z) for r, z in prof][::-1], mats['curb'], {'lite': 1})
    posts = []
    for side in (0, 1):
        a0 = gap + side * math.pi
        a1 = math.pi - gap + side * math.pi
        n = 9
        for k in range(n + 1):
            a = a0 + (a1 - a0) * k / n
            tall = k in (0, n)
            x, y = (R0 + 0.175) * math.cos(a), (R0 + 0.175) * math.sin(a)
            h = 1.05 if tall else 0.62
            lathe(mb, [(0.06, 0.2), (0.05, h - 0.05), (0.075, h), (0.0, h + 0.1)], 6, (x, y, 0.0), mats['bronze'], {'lite': 1}, cap=False)
            if tall:
                lathe(mb, [(0.0, 0.0), (0.11, 0.07), (0.07, 0.2), (0.0, 0.27)], 6, (x, y, h + 0.05), mats['bronze'], {'lite': 1}, cap=False)
            posts.append((x, y, h - 0.1 if not tall else 0.55))
    from crown_top import _rope
    for i in range(len(posts) - 1):
        if (i + 1) % 10 == 0:
            continue
        p0, p1 = np.asarray(posts[i]), np.asarray(posts[i + 1])
        _rope(mb, p0, p1, 0.12, mats['rope'], 0.035)
    return mb


def _circle_sweep(mb: MB, prof, angs, mat: int) -> None:
    pts = [[(r * math.cos(a), r * math.sin(a), z) for a in angs] for r, z in prof]
    base = mb.verts([p for row in pts for p in row])
    n = len(angs)
    s = [0.0]
    for (r1, z1), (r2, z2) in zip(prof, prof[1:]):
        s.append(s[-1] + math.hypot(r2 - r1, z2 - z1))
    for i in range(len(prof) - 1):
        for j in range(n - 1):
            q = (base + i * n + j, base + (i + 1) * n + j, base + (i + 1) * n + j + 1, base + i * n + j + 1)
            u0, u1 = prof[i][0] * angs[j], prof[i][0] * angs[j + 1]
            uv = [(u0, s[i]), (u0, s[i + 1]), (u1, s[i + 1]), (u1, s[i])]
            mb.face(q, uv, uv, mat, {'lite': 1})
