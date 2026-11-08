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
    sides, n = (14, 22) if high else (6, 8)
    ear_sides = 10 if high else 5          # the ear strands are thin: fewer sides on the low mesh
    ridges, rd = (7, 0.07) if high else (0, 0.0)
    bm = bmesh.new()
    attrs = {'u': [], 'part': []}
    rng = np.random.default_rng(13)
    for s, (tp, a, xo, nf) in ear_frames.items():
        a, xo, nf = _norm(v3(a)), _norm(v3(xo)), _norm(v3(nf))
        # 1-hero / 3-faces: a flame plume about 40% of the ear's height, rising and leaning a little outward, its tongues
        # curling outward at their tips
        sweep = _norm(a * 0.88 + xo * 0.46)       # round 3b: swept further out
        side = _norm(xo - sweep * float(xo @ sweep))
        base = v3(tp) - a * 0.016 * head_k
        # five long narrow tongues, the middle one tallest, fanned only a little, their tips curling outward (preview 19:
        # four short fat ones fanned wide read as a flower)
        # round 3b: a plume of thin strands bunched at the root, in two staggered rows (front and back of the cup's
        # plane) so it has depth; round 3's seven wide flat tongues in one plane read as tulip petals in the film
        # round 3b: bunched (the fan halved) and all curling the same way, one swept plume instead of a fan of strands
        for ang, ln, wd, curl, off, dep in ((0.0, 0.12, 0.0115, 0.2, 0.0, 0.0), (-2.0, 0.112, 0.0105, 0.21, -0.003, 0.005),
                                            (3.0, 0.114, 0.0105, 0.24, 0.003, -0.005), (-5.0, 0.1, 0.01, 0.22, -0.005, -0.004),
                                            (6.0, 0.104, 0.01, 0.27, 0.005, 0.004), (-7.0, 0.086, 0.0095, 0.24, -0.007, 0.004),
                                            (8.0, 0.09, 0.0095, 0.3, 0.007, -0.004), (-10.0, 0.07, 0.009, 0.26, -0.009, -0.002),
                                            (11.0, 0.076, 0.009, 0.33, 0.009, 0.003), (-12.0, 0.054, 0.008, 0.28, -0.011, 0.0),
                                            (13.0, 0.058, 0.008, 0.36, 0.012, 0.0)):
            r = math.radians(ang)
            d = sweep * math.cos(r) + side * math.sin(r)
            tongue(bm, base + (side * off + nf * dep) * head_k, d, side, side, ln * head_k, wd * head_k,
                   wd * 0.7 * head_k, curl, 0.06 * rng.normal(), ear_sides, n, ridges, rd, float(s), attrs)
    # 4-details 4: the tail's tip ends in one swept flame lick, its tongues streaming on and curling forward over the
    # back (preview 19: five fat overlapping tongues read as a bulb)
    c, T, up, rad = (v3(x) if i < 3 else x for i, x in enumerate(tail_frame))
    T, up = _norm(T), _norm(up)
    side = _norm(np.cross(T, up))
    base = c - T * rad * 0.6
    for ang, roll, ln, wd, th, curl in ((0.0, 0.0, 0.19, 0.034, 0.014, 0.34), (-16.0, 0.0, 0.15, 0.028, 0.012, 0.4),
                                        (15.0, 0.0, 0.14, 0.028, 0.012, 0.26), (-30.0, 0.0, 0.1, 0.022, 0.01, 0.42),
                                        (6.0, 55.0, 0.125, 0.024, 0.011, 0.34), (6.0, -55.0, 0.12, 0.024, 0.011, 0.34)):
        r = math.radians(ang)
        fan = _norm(up * math.cos(math.radians(roll)) + side * math.sin(math.radians(roll)))
        d = T * math.cos(r) + fan * math.sin(r)
        tongue(bm, base + fan * rad * 0.3 * math.sin(r), d, _norm(np.cross(d, fan)) if roll else side, up, ln, wd, th, curl,
               0.04 * rng.normal(), sides, n, ridges, rd, 2.0, attrs)
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
