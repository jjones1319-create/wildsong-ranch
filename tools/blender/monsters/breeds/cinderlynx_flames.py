"""Cinderlynx Ultra flame props (round 3): the ember tufts on the ear tips and the flame lick at the tail's tip.

Round 2's tufts were tuft locks: fine strands that can't glow, whose thin ribbons washed out to peach-white under the
key and rim lights. Each flame is now a rigid prop: a swept plume of a few tongues, every tongue a closed lens-shaped
tube (round at its root, widest a third of the way up, pointed at its tip) along a curve that sweeps up and curls,
with shallow strand ridges on the high mesh (they bake into the normal map) and the ember gradient painted root to
tip; it glows through the per-vertex `glow` attribute (props can glow; tuft locks can't). The recipe weights the ear
flames to `ear.L.2` / `ear.R.2` and the tail's to the last tail bone (prop_weight_regions).

Every object gets the attributes `flame_part` (1 left ear, −1 right ear, 2 tail) and `flame_u` (0 root … 1 tip).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib.surface import v3


def _norm(v: np.ndarray) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-9)


def width_profile(u: float) -> float:
    """0..1: a round root, the widest about a third of the way up, a long point to the tip."""
    return min(1.0, 2.3 * (u + 0.06) ** 0.5 * max(0.0, 1.0 - u) ** 0.9)


def tongue(bm: bmesh.types.BMesh, base, d0, side_ref, curl_dir, length: float, width: float, thick: float, curl: float,
           sway: float, sides: int, n: int, ridges: int, ridge_depth: float, part: float, attrs: dict) -> None:
    """One flame tongue: a tube of elliptic sections along p(u) = base + d0·L·u + curl_dir·curl·L·u² + side·sway·sin(πu),
    width across `side_ref` (the plume's fan), thickness across the fan; closed at the root and pointed at the tip."""
    base, d0, side_ref, curl_dir = v3(base), _norm(v3(d0)), v3(side_ref), _norm(v3(curl_dir))

    def centre(u: float) -> np.ndarray:
        return base + d0 * (length * u) + curl_dir * (curl * length * u * u) + side_ref * (sway * length * math.sin(math.pi * u))

    us = [k / n for k in range(n)] + [0.985]
    rings = []
    for u in us:
        p = centre(u)
        t = _norm(centre(min(u + 0.01, 1.0)) - centre(max(u - 0.01, 0.0)))
        e1 = _norm(side_ref - t * float(side_ref @ t))
        e2 = np.cross(t, e1)
        w = width * max(width_profile(u), 0.12 if u == 0 else 0.0)
        th = thick * max(width_profile(u), 0.12 if u == 0 else 0.0)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            r = 1.0 + ridge_depth * math.sin(a * ridges + u * 9.0) * (1.0 - u) if ridges else 1.0
            q = p + (e1 * (w * math.cos(a)) + e2 * (th * math.sin(a))) * r
            v = bm.verts.new(tuple(q))
            attrs['u'].append(u)
            attrs['part'].append(part)
            ring.append(v)
        rings.append(ring)
    for j in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[j][k], rings[j][(k + 1) % sides], rings[j + 1][(k + 1) % sides], rings[j + 1][k]))
    tip = bm.verts.new(tuple(centre(1.0)))
    attrs['u'].append(1.0)
    attrs['part'].append(part)
    for k in range(sides):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], tip))
    root = bm.verts.new(tuple(centre(0.0) - _norm(centre(0.02) - centre(0.0)) * thick * 0.4))
    attrs['u'].append(0.0)
    attrs['part'].append(part)
    for k in range(sides):
        bm.faces.new((rings[0][(k + 1) % sides], rings[0][k], root))


def build(name: str, high: bool, ear_frames: dict, tail_frame: tuple, head_k: float) -> bpy.types.Object:
    """The three flames as one object. `ear_frames[s]` = (tip point, long axis, outward across, normal out of the cup)
    in world space; `tail_frame` = (the tail tip's centre, its tangent, its 'up' (the back's side), its radius)."""
    sides, n = (14, 22) if high else (6, 6)
    ear_sides = 8 if high else 4           # the strands are thin: fewer sides on the low mesh
    tail_sides = ear_sides
    ridges, rd = (7, 0.07) if high else (0, 0.0)
    bm = bmesh.new()
    attrs = {'u': [], 'part': []}
    rng = np.random.default_rng(13)
    for s, (tp, a, xo, nf) in ear_frames.items():
        a, xo, nf = _norm(v3(a)), _norm(v3(xo)), _norm(v3(nf))
        # 1-hero / 3-faces: a flame plume about 40% of the ear's height, rising and leaning a little outward, its tongues
        # curling outward at their tips
        # Nov 13 (the review: stiff blade fans): soft wisps rising off the tip, swept a little back and out, thin and
        # many, each curling back at its end
        sweep = _norm(a * 0.94 - nf * 0.2 + xo * 0.16)
        side = _norm(xo - sweep * float(xo @ sweep))
        base = v3(tp) - a * 0.014 * head_k
        back = _norm(-nf - sweep * float(-nf @ sweep))
        for k in range(14):
            fr = (k + 0.5) / 14
            ang = (fr - 0.5) * 22.0 + rng.normal(0, 2.0)
            r = math.radians(ang)
            d = _norm(sweep * math.cos(r) + side * math.sin(r))
            ln = (0.07 + 0.05 * (1 - abs(fr - 0.45) * 1.8)) * (0.85 + 0.3 * rng.random())
            wd = 0.0065 + 0.002 * rng.random()
            off = side * (fr - 0.5) * 0.026 + back * rng.normal(0, 0.003)
            tongue(bm, base + off * head_k, d, side, back, ln * head_k, wd * head_k, wd * 0.6 * head_k,
                   0.25 + 0.15 * rng.random(), 0.06 * rng.normal(), ear_sides, n, ridges, rd, float(s), attrs)
    # Nov 13 (the review: an egg with blades, a crown or bud): a plume of many fine curved flame strands, all swept back
    # along the tail and curling up at their ends, rooted in the fur over the tail's last third (`tail_frame` = its
    # stations from the plume's start to the tip: centre, tangent, up, radius), longer toward the tip
    m = len(tail_frame)
    for k in range(40):
        fr = (k + 0.5) / 40
        si = min(m - 1, int(fr * m))
        c, T, up, rad = (v3(x) if i < 3 else x for i, x in enumerate(tail_frame[si]))
        T, up = _norm(T), _norm(up)
        side = _norm(np.cross(T, up))
        roll = rng.uniform(-2.0, 2.0) * (0.55 + 0.45 * fr)          # all round near the tip, mostly on top further in
        fan = _norm(up * math.cos(roll) + side * math.sin(roll))
        base = c + fan * rad * 0.6
        d = _norm(T + fan * 0.2 - up * 0.12)          # swept back along the tail, curling up only at the ends
        ln = (0.09 + 0.15 * fr) * (0.8 + 0.4 * rng.random())
        wd = 0.0085 + 0.004 * rng.random()
        tongue(bm, base, d, _norm(np.cross(d, fan)), up, ln, wd, wd * 0.55, 0.16 + 0.14 * rng.random(), 0.05 * rng.normal(),
               tail_sides, n, ridges, rd, 2.0, attrs)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)     # closed tubes: outward everywhere
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob['prop'] = 'flames'
    from lib import surface as S
    S.add_attr(ob, 'flame_u', np.asarray(attrs['u'], np.float64))
    S.add_attr(ob, 'flame_part', np.asarray(attrs['part'], np.float64))
    return ob
