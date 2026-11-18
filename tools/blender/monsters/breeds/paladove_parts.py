"""Paladove's shared parts (Art 2.1 Ultra; chatgpt/monsters/26-paladove; CONTENT entry 24), for the young form
(paladove_ultra.py) and the grown form (paladove_grown_ultra.py):

  - the body as a union of ellipsoids (analytic: ray exits, normals, the inside test), with soft fluff clumps on it for a
    tufted outline (voxel-united into the body, as Plumdrake's fluff);
  - feathers as closed, leaf-wide lenses (each at least 40% of its width at 90% of its length, a rounded tip), and a
    wing as ONE closed slab: rows of feathers voxel-united along the folded arm, so it never spreads into loose pellets
    and never reads as a needle edge-on (round 9's lesson); the feather rows are real steps on both faces;
  - tubes for the legs and toes, talons, a torus for the halo, beaks, lens eyes and their material.
Deterministic. Metres; the monster faces -Y, Z is up, +X is its left. Colours come from CONTENT; where a picture shows
a colour the palette lacks (the blush, the mouth, the claws, the lashes), it is mixed from palette colours here.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib.surface import norm, smooth, v3
from monsters.breeds import hearthwing_parts as HP

WHITE, HI, GOLD, EYE = '#F7F4EE', '#FFFFFF', '#E3B448', '#4A6FA5'


def unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def mirror(p, s: int) -> np.ndarray:
    q = v3(p).astype(np.float64).copy()
    q[..., 0] *= 1.0 if s > 0 else -1.0
    return q


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def mixl(a: str, b: str, t: float) -> np.ndarray:
    return lin(C.mix_hex(a, b, t))


# ============================================================================= the body: a union of ellipsoids
def ell_q(p: np.ndarray, ells) -> np.ndarray:
    """Per point, the smallest normalised radius over the ellipsoids (< 1 inside the union)."""
    q = np.full(len(p), 9.0)
    for c, r in ells:
        q = np.minimum(q, np.sqrt((((p - v3(c)) / v3(r)) ** 2).sum(axis=1)))
    return q


def ray_exit(o, d, ells) -> float:
    """How far from `o` along unit `d` the ray leaves the union (the furthest exit among the ellipsoids it crosses)."""
    o, d = v3(o), unit(d)
    best = 0.0
    for c, r in ells:
        r = v3(r)
        oo, dd = (o - v3(c)) / r, d / r
        a, b, cc = float(dd @ dd), 2.0 * float(oo @ dd), float(oo @ oo) - 1.0
        disc = b * b - 4 * a * cc
        if disc <= 0:
            continue
        t2 = (-b + math.sqrt(disc)) / (2 * a)
        best = max(best, t2)
    return best


def ell_normal(p, ells) -> np.ndarray:
    """The outward normal of the union at points near its surface: the gradient of the ellipsoid each point is nearest
    to lying on (its normalised radius closest to 1, among the ones that don't contain it deeply)."""
    p = v3(p).reshape(-1, 3)
    best = np.full(len(p), 9.0)
    out = np.zeros_like(p)
    for c, r in ells:
        g = (p - v3(c)) / v3(r) ** 2
        q = np.sqrt((((p - v3(c)) / v3(r)) ** 2).sum(axis=1))
        score = np.abs(q - 1.0)
        take = score < best
        best = np.where(take, score, best)
        out[take] = g[take]
    return norm(out)


def surface_point(o, d, ells, out: float = 0.0) -> np.ndarray:
    o, d = v3(o), unit(d)
    t = ray_exit(o, d, ells)
    return o + d * (t + out)


# ============================================================================= feathers and fluff
def feather_frame(d, n) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(along, across, normal): `d` along the feather, `n` made perpendicular to it, across = n x d (so the loft's
    rings, X = across and Y = normal, face outward)."""
    d = unit(d)
    n = unit(v3(n) - d * float(v3(n) @ d))
    return d, np.cross(n, d), n


def feather(name: str, root, d, n, L: float, W: float, T: float, curl: float = 0.0, bury: float = 0.2, twist: float = 0.0,
            rings: int = 14, seg: int = 12, coll=None, tip: float = 0.42) -> bpy.types.Object:
    """A leaf-wide feather lens from `root` along `d` (lying on `n`), `L` long, `W` wide, `T` thick: full from the root,
    widest near `tip` of its length, then a rounded tip (about 0.73 of its width at 90% of its length); `curl` bends it
    toward +n (metres at the tip); `twist` turns its tip about its axis (degrees)."""
    d, a, nn = feather_frame(d, n)
    t = np.linspace(-bury, 1.0, rings)
    tt = np.clip(t, 0.0, 1.0)
    c = v3(root)[None] + d[None] * (L * t)[:, None] + nn[None] * (curl * tt ** 2)[:, None]
    tw = np.radians(twist) * tt
    X = a[None] * np.cos(tw)[:, None] + nn[None] * np.sin(tw)[:, None]
    Y = np.cross(np.broadcast_to(d, X.shape), X)
    wprof = np.sqrt(np.clip(1.0 - (np.abs(tt - tip) / max(1.0 - tip, 1e-3)) ** 4, 0.0, 1.0))
    wprof = np.where(tt < tip, np.maximum(wprof, 0.82), wprof)
    rx = 0.5 * W * wprof
    ry = 0.5 * T * (1.0 - 0.4 * tt) * np.sqrt(np.clip(1.0 - tt ** 6, 0.0, 1.0))
    return HP.loft(name, c[:-1], X[:-1], Y[:-1], np.maximum(rx[:-1], 3e-4), np.maximum(ry[:-1], 3e-4), seg, True, True, c[-1], coll)


def feather_local(p: np.ndarray, f: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A point's (a along 0..1, b across -1..1 of the local half-width, h along the normal) in a feather's frame."""
    d, ac, n = feather_frame(f['d'], f['n'])
    q = p - v3(f['root'])
    a = (q @ d) / f['L']
    tip = f.get('tip', 0.42)
    aa = np.clip(a, 0.0, 1.0)
    wprof = np.sqrt(np.clip(1.0 - (np.abs(aa - tip) / (1.0 - tip)) ** 4, 0.0, 1.0))
    wprof = np.where(aa < tip, np.maximum(wprof, 0.82), wprof)
    b = (q @ ac) / np.maximum(0.5 * f['W'] * wprof, 1e-4)
    return a, b, q @ n - f.get('curl', 0.0) * aa ** 2


def clump(name: str, spec: dict, rings: int = 10, seg: int = 9, coll=None) -> bpy.types.Object:
    """A soft lock of fluff: from `base` (buried `bury` of its length) along `dir`, its tip curling toward `bend`, wide
    along `side` and thin across; a full root rounding into a soft point (Plumdrake's fluff clumps)."""
    b = v3(spec['base'])
    d = unit(spec['dir'])
    L = float(spec['len'])
    side = unit(v3(spec['side']) - d * float(v3(spec['side']) @ d))
    bend = v3(spec.get('bend', (0.0, 0.0, -1.0)))
    bend = unit(bend - d * float(bend @ d))
    bury = float(spec.get('bury', 0.35))
    t = np.linspace(-bury, 1.0, rings)
    tt = np.clip(t, 0.0, 1.0)
    c = b[None] + d[None] * (L * t)[:, None] + bend[None] * (spec.get('curl', 0.3) * L * tt ** 2)[:, None]
    T, X, Y = HP.side_frames(c, side)
    prof = np.where(t < 0, 1.0, np.clip(1.0 - tt ** 1.8, 0.0, 1.0) ** 0.7)
    w, th = float(spec['w']), float(spec['th'])
    return HP.loft(name, c[:-1], X[:-1], Y[:-1], np.maximum(0.5 * w * prof[:-1], 3e-4),
                   np.maximum(0.5 * th * np.maximum(prof[:-1], 0) ** 0.75, 3e-4), seg, True, True, c[-1], coll)


def fib_dirs(n: int) -> np.ndarray:
    """n evenly spread unit directions (a Fibonacci sphere)."""
    i = np.arange(n) + 0.5
    z = 1.0 - 2.0 * i / n
    r = np.sqrt(1.0 - z * z)
    a = math.pi * (3.0 - math.sqrt(5.0)) * i
    return np.stack([r * np.cos(a), r * np.sin(a), z], axis=1)


def hash01(i, seed: int = 0) -> np.ndarray:
    x = np.sin(np.asarray(i, np.float64) * 12.9898 + seed * 78.233) * 43758.5453
    return x - np.floor(x)


# ============================================================================= wings: one closed slab of feather rows
def wing_arm(spec: dict, s: int = 1) -> np.ndarray:
    """The folded arm's polyline (shoulder, elbow, wrist, the first finger's tip) for side s."""
    pts = [spec['shoulder'], spec['elbow'], spec['wrist'], spec['fingers'][0]]
    return np.array([mirror(p, s) for p in pts])


def wing_feathers(spec: dict, rows: list[dict], normal_fn, s: int = 1) -> list[dict]:
    """The feathers of one folded wing: each row {'n', 'u': (u0, u1) along the arm (0 shoulder .. 1 tip),
    'phi': (deg at u0, deg at u1) from the arm's direction toward its trailing side, 'L': (L0, L1), 'W', 'T', 'lift' (m
    out from the arm's plane: higher rows lie on top), 'curl', 'level'}. `normal_fn(points)` gives the wing's outward
    normal along the arm (the body's, so the folded wing hugs it). Fingers past the first lay along the hand."""
    arm = wing_arm(spec, s)
    s_len = HP.arc_lengths(arm)
    out = []
    k = 0
    for ri, row in enumerate(rows):
        n_f = int(row['n'])
        for j in range(n_f):
            f = j / max(1, n_f - 1)
            u = row['u'][0] + (row['u'][1] - row['u'][0]) * f
            root = HP.curve_at(arm, u)[0]
            # the arm's direction there (the segment it lies on)
            seg_i = int(np.clip(np.searchsorted(s_len / s_len[-1], u, side='right') - 1, 0, len(arm) - 2))
            tdir = unit(arm[seg_i + 1] - arm[seg_i])
            nrm = unit(normal_fn(root[None])[0])
            nrm = unit(nrm - tdir * float(nrm @ tdir))
            # the trailing side: in the wing's plane, away from the leading edge (down for a folded wing)
            down = v3(row.get('down', (0.0, 0.0, -1.0)))
            down = down * (1.0 if s > 0 else 1.0)
            perp = unit(down - tdir * float(down @ tdir) - nrm * float(down @ nrm))
            phi = math.radians(row['phi'][0] + (row['phi'][1] - row['phi'][0]) * f)
            d = unit(tdir * math.cos(phi) + perp * math.sin(phi))
            L = row['L'][0] + (row['L'][1] - row['L'][0]) * f ** row.get('Lpow', 1.0)
            W = row['W'] if np.isscalar(row['W']) else row['W'][0] + (row['W'][1] - row['W'][0]) * f
            lift = float(row.get('lift', 0.0))
            out.append({'root': root + nrm * lift - d * 0.0, 'd': d, 'n': nrm, 'L': float(L), 'W': float(W),
                        'T': float(row['T']), 'curl': -float(row.get('curl', 0.0)) * float(L), 'level': ri, 'k': k,
                        'tip': row.get('tip', 0.42), 'twist': float(row.get('twist', 0.0)) * s})
            k += 1
    return out


def wing_slab(name: str, feathers: list[dict], spec: dict, s: int, voxel: float, arm_r: float, arm_flat: float = 0.6,
              smooth_iters: int = 2) -> bpy.types.Object:
    """One closed wing: every feather lens and the leading edge's arm (a flattened tube along the folded arm),
    voxel-united and smoothed."""
    objs = []
    for f in feathers:
        objs.append(feather(f'{name}_f{f["k"]}', f['root'], f['d'], f['n'], f['L'], f['W'], f['T'], curl=f['curl'], twist=f['twist'],
                            bury=min(0.2, 0.035 / f['L']),
                            tip=f['tip']))
    arm = HP.resample(HP.catmull(wing_arm(spec, s), 8), 24)
    nrm = np.array([f['n'] for f in feathers[:1]] * len(arm))
    r = arm_r * (1.0 - 0.45 * np.linspace(0, 1, len(arm)) ** 1.5)
    objs.append(HP.tube(f'{name}_arm', arm, r, nrm[0], seg=12, flat=arm_flat))
    return S.build_body(name, [], voxel, smooth_iters, extra=objs)


def wing_paint(co: np.ndarray, vn: np.ndarray, feathers: list[dict], plane_n: np.ndarray, base: np.ndarray,
               hi: np.ndarray, edge: np.ndarray, shaft: np.ndarray, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Per vertex of a wing slab: the feather on top there (the outer face shows the highest row, the inner face the
    lowest), and its paint: a soft white with a little per-feather jitter, brighter toward the tip, a fine warm edge
    along its outline, a faint shaft down the flight feathers. Both faces equally bright. Returns (rgb, edge mask)."""
    n = len(co)
    outer = (vn * plane_n).sum(axis=1) >= 0.0
    best = np.full(n, -1)
    score = np.full(n, -1e9)
    loc_a = np.zeros(n)
    loc_b = np.zeros(n)
    for f in feathers:
        a, b, _h = feather_local(co, f)
        inside = (a > -0.15) & (a < 1.02) & (np.abs(b) < 1.05)
        lvl = f['level'] * 10 + (f['k'] % 10) * 0.01
        sc = np.where(outer, lvl, -lvl) + np.where(inside, 1000.0, -1000.0 + -np.abs(b) * 10 - np.abs(a - 0.5) * 10)
        take = sc > score
        score = np.where(take, sc, score)
        best = np.where(take, f['k'], best)
        loc_a = np.where(take, a, loc_a)
        loc_b = np.where(take, b, loc_b)
    jit = (hash01(best, seed) - 0.5) * 0.05
    rgb = base[None] * (1.0 + jit)[:, None]
    tipk = smooth(0.35, 1.0, loc_a) * 0.55
    rgb = rgb * (1 - tipk[:, None]) + hi[None] * tipk[:, None]
    # the outline: the sides and the rounded tip (a soft 10-14% band)
    ed = np.maximum(smooth(0.8, 1.0, np.abs(loc_b)), smooth(0.9, 1.01, loc_a)) * (loc_a > 0.05)
    rgb = rgb * (1 - 0.8 * ed[:, None]) + edge[None] * (0.8 * ed[:, None])
    lv = np.array([f['level'] for f in feathers])[np.clip(best, 0, len(feathers) - 1)]
    sh = smooth(0.09, 0.03, np.abs(loc_b)) * smooth(0.05, 0.2, loc_a) * smooth(0.98, 0.8, loc_a) * (lv == 0)
    rgb = rgb * (1 - 0.5 * sh[:, None]) + shaft[None] * (0.5 * sh[:, None])
    return rgb, ed


# ============================================================================= tubes, toes, talons, the halo
def torus(name: str, centre, axis, R: float, r: float, nu: int, nv: int, ref=(1.0, 0.0, 0.0)) -> bpy.types.Object:
    """A closed ring: `R` from `centre` round `axis`, the tube `r` thick."""
    ax = unit(axis)
    e1 = unit(v3(ref) - ax * float(v3(ref) @ ax))
    e2 = np.cross(ax, e1)
    verts = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        radial = e1 * math.cos(a) + e2 * math.sin(a)
        cc = v3(centre) + radial * R
        for j in range(nv):
            b = 2 * math.pi * j / nv
            verts.append(cc + radial * (r * math.cos(b)) + ax * (r * math.sin(b)))
    faces = []
    for i in range(nu):
        for j in range(nv):
            i2, j2 = (i + 1) % nu, (j + 1) % nv
            faces.append((i * nv + j, i * nv + j2, i2 * nv + j2, i2 * nv + j))
    ob = HP.mesh_object(name, verts, faces)
    return ob


def scaled_tube(name: str, a, b, r0: float, r1: float, ref, rings: int, seg: int, ring_k: float = 0.0, n_scales: int = 0,
                flat: float = 1.0, tip=None) -> bpy.types.Object:
    """A tube from a to b (radius r0 -> r1); `n_scales` > 0 rings it with scutes (a bump of ring_k x radius each)."""
    t = np.linspace(0.0, 1.0, rings)
    pts = v3(a)[None] + (v3(b) - v3(a))[None] * t[:, None]
    r = r0 + (r1 - r0) * t
    if n_scales:
        r = r * (1.0 + ring_k * (0.5 + 0.5 * np.cos(2 * math.pi * n_scales * t)))
    return HP.tube(name, pts, r, ref, seg=seg, flat=flat, tip=tip)


def toe(name: str, base, direction, L: float, r: float, rings: int, seg: int, knuckles: int = 3, down=(0.0, 0.0, -1.0),
        arch: float = 0.0) -> bpy.types.Object:
    """A plump bird toe from `base` along `direction`: pads swelling under each knuckle, tapering to the claw's root,
    a little arch (`arch` x L up at the middle)."""
    d = unit(direction)
    t = np.linspace(0.0, 1.0, rings)
    c = v3(base)[None] + d[None] * (L * t)[:, None] + v3((0, 0, 1))[None] * (arch * L * np.sin(math.pi * t))[:, None]
    rr = r * (1.0 - 0.38 * t) * (1.0 + 0.12 * np.clip(np.sin(math.pi * knuckles * t), 0, None))
    rr[-1] *= 0.75
    return HP.tube(name, c, rr, v3(down), seg=seg, flat=0.85)


def talon(name: str, root, direction, L: float, r: float, rings: int = 8, seg: int = 10) -> bpy.types.Object:
    return HP.talon(name, root, direction, (0.0, 0.0, -1.0), L, r, curve=0.35, rings=rings, seg=seg, flat=0.8, blunt='cone', cap=0.3)


# ============================================================================= beaks
def beak(name: str, base, tip, width: float, height: float, hook: float, rings: int, seg: int, flat_bottom: float = 0.35,
         cap0: bool = True) -> bpy.types.Object:
    """A small rounded beak from `base` (inside the face) to `tip`: an elliptic section `width` wide and `height` tall
    at the base, tapering to a rounded point; `hook` bends the tip down (metres); the underside flattened."""
    b, tp = v3(base), v3(tip)
    d = unit(tp - b)
    L = float(np.linalg.norm(tp - b))
    t = np.linspace(0.0, 1.0, rings)
    c = b[None] + d[None] * (L * t)[:, None] + v3((0, 0, -1))[None] * (hook * t ** 2.2)[:, None]
    T, X, Y = HP.side_frames(c, (1.0, 0.0, 0.0))
    k = np.clip(1.0 - t ** 1.6, 0.0, 1.0) ** 0.85
    rx = 0.5 * width * np.maximum(k, 0.02)
    ry = 0.5 * height * np.maximum(k, 0.02)
    ob = HP.loft(name, c[:-1], X[:-1], Y[:-1], rx[:-1], ry[:-1], seg, cap0, True, c[-1])
    if flat_bottom > 0:
        co, _ = S.mesh_arrays(ob)
        # squash the underside toward the beak's centre line: a flatter cutting edge
        rel = co - b[None]
        along = rel @ d
        ctr = b[None] + along[:, None] * d[None] + v3((0, 0, -1))[None] * (hook * np.clip(along / L, 0, 1) ** 2.2)[:, None]
        dz = co[:, 2] - ctr[:, 2]
        co[:, 2] = np.where(dz < 0, ctr[:, 2] + dz * (1.0 - flat_bottom), co[:, 2])
        S.set_positions(ob, co)
    return ob


# ============================================================================= eyes
def eye_frame(c, look, s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(centre, x across toward the monster's left, y up, look)."""
    look = unit(look)
    xax = unit(np.cross(v3((0.0, 0.0, 1.0)), look))
    yax = unit(np.cross(look, xax))
    return v3(c), xax, yax, look


def build_lens(name: str, frame, r: float, depth: float, sink: float, s: int, high: bool) -> bpy.types.Object:
    """A glossy lens: a cap of a sphere, its base plane `sink` under the face along the look axis."""
    c, xax, yax, look = frame
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.3]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * r, v.co.y * r, v.co.z * r * depth))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    m = Matrix((tuple(xax), tuple(yax), tuple(look))).transposed().to_4x4()
    ob.matrix_world = Matrix.Translation(Vector(tuple(c - look * sink))) @ m
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / np.array([r, r, r * depth]))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def eye_material(name: str, rough_pass: bool, eye_hex: str, vis: float = 0.67, iris_shift: tuple[float, float] = (0.03, 0.07),
                 lid_hex: str = '#F1EBDF', pupil: float = 0.42, lid: float = 0.86, light: float = 0.0):
    """A big glossy blue eye (3-faces neutral, 4-details panel 2), drawn for the part of the lens that shows: only `vis`
    of its radius rises out of the face (round 2: the iris was drawn for the whole lens, so its pale outer ring showed as
    a white sticker rim and the blue as a narrow navy band). The iris fills the visible eye (CONTENT's blue with a paler
    ring, deep only at the pupil and the rim), a round pupil, two catchlights, the iris set a little high (the calm,
    upward gaze of 3-faces neutral), and the upper lid's down over the top with a dark lash line that lifts toward the
    outer corner."""
    from lib.nodes import new_mat
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.04, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x0, y0, _z = nb.sep(e)
    x = nb.math('DIVIDE', x0, vis)
    y = nb.math('DIVIDE', y0, vis)
    ix = nb.math('ADD', x, nb.math('MULTIPLY', side, iris_shift[0]))
    iy = nb.math('SUBTRACT', y, iris_shift[1])
    ri = nb.math('DIVIDE', nb.vmath('LENGTH', nb.comb(ix, iy, 0.0)), 0.97)
    deep = C.lin(C.shade_hex(eye_hex, 0.62 + 0.25 * light))
    mid = C.lin(C.mix_hex(eye_hex, '#FFFFFF', 0.08 + 0.12 * light))
    pale = C.lin(C.mix_hex(eye_hex, '#FFFFFF', 0.36 + 0.1 * light))
    limb = C.lin(C.shade_hex(eye_hex, 0.45))
    lash = C.shade_hex(eye_hex, 0.16)
    pr = pupil
    iris = nb.ramp(ri, [(0.0, C.lin('#05070C')), (pr * 0.96, C.lin('#05070C')), (pr + 0.04, deep), (pr + 0.16, mid),
                        (0.7, pale), (0.84, mid), (0.94, deep), (1.0, limb), (1.2, limb)])
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 40.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', nb.smooth(ri, pr + 0.05, 0.6), nb.smooth(ri, 0.95, 0.82)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.16), iris, nb.rgb(pale))
    low = nb.math('MULTIPLY', nb.smooth(iy, -0.05, -0.6), nb.math('MULTIPLY', nb.smooth(ri, 0.95, 0.6), nb.smooth(ri, pr, pr + 0.12)))
    c = nb.mix(nb.math('MULTIPLY', low, 0.35), iris, nb.rgb(C.lin(C.mix_hex(eye_hex, '#FFFFFF', 0.5))))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', ix, 0.26), nb.math('DIVIDE', nb.math('SUBTRACT', iy, 0.22), 1.1), 0.0)), 0.2, 0.16)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', ix, 0.24), nb.math('ADD', iy, 0.3), 0.0)), 0.08, 0.06)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    # the upper lid: the face's down over the top of the eye, a dark lash line along its edge lifting at the outer corner
    ey = nb.math('ADD', y, nb.math('MULTIPLY', nb.math('MULTIPLY', x, x), 0.12))
    c = nb.mix(nb.smooth(ey, lid, lid + 0.04), c, nb.rgb(C.lin(lid_hex)))
    ln = nb.math('MULTIPLY', nb.smooth(ey, lid - 0.1, lid - 0.06), nb.smooth(ey, lid + 0.06, lid + 0.02))
    c = nb.mix(ln, c, nb.rgb(C.lin(lash)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def feather_groove(co: np.ndarray, vn: np.ndarray, feathers: list[dict], plane_n) -> np.ndarray:
    """0..1 per vertex: the barbs of the feather on top there (fine grooves slanting out from the shaft toward the tip)."""
    plane_n = v3(plane_n)
    outer = (vn * plane_n[None]).sum(axis=1) >= 0.0
    score = np.full(len(co), -1e9)
    ga = np.zeros(len(co))
    gb = np.full(len(co), 9.0)
    for f in feathers:
        a, b, _h = feather_local(co, f)
        inside = (a > 0.0) & (a < 1.0) & (np.abs(b) < 1.0)
        lvl = f['level'] * 10 + (f['k'] % 10) * 0.01
        sc = np.where(outer, lvl, -lvl) + np.where(inside, 1000.0, -1000.0)
        take = sc > score
        score = np.where(take, sc, score)
        ga = np.where(take, a * f['L'], ga)
        gb = np.where(take & inside, np.abs(b) * 0.5 * f['W'], np.where(take, 9.0, gb))
    pitch = 0.006
    g = np.cos(2 * np.pi * (ga - 0.8 * gb) / pitch)
    return smooth(0.55, 0.95, g) * (gb < 8.0) * smooth(0.002, 0.006, gb)


def barb_relief(ob, feathers: list[dict], plane_n, depth: float) -> None:
    """Cut the barbs into a high wing or fan (baked into the normal map; round 1: the feathers read as satin)."""
    co, _ = S.mesh_arrays(ob)
    me = ob.data
    vn = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('normal', vn)
    vn = vn.reshape(-1, 3)
    g = feather_groove(co, vn, feathers, plane_n)
    S.set_positions(ob, co - vn * (depth * g)[:, None])


def drop_islands(ob, min_verts: int = 200) -> int:
    """Delete the loose pieces a voxel remesh leaves behind (a thin tuft tip breaking off into a floating chip, which
    bakes as a speck with a shadow): every connected part with fewer than min_verts vertices. Returns how many."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen = set()
    drop = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, part = [v], []
        seen.add(v.index)
        while stack:
            u = stack.pop()
            part.append(u)
            for e in u.link_edges:
                w = e.other_vert(u)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        if len(part) < min_verts:
            drop.append(part)
    if drop:
        bmesh.ops.delete(bm, geom=[v for part in drop for v in part], context='VERTS')
        bm.to_mesh(ob.data)
    bm.free()
    return len(drop)
