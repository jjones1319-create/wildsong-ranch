"""Grown Pluckrex's stone bracers (grown-1-hero, grown-4-details panel 3): a thick cuff of weathered grey stone round
each forearm's wrist half, cut into four slabs by deep grooves, a raised rim at each end, and a carved sun (a disc and
eight rays) on its outer face that glows gold like the crest. Props skinned rigidly to the forearm's prop bone. Each
vertex: `pt` = (t along the cuff 0..1, the angle round it 0..1, the sun mask 0..1). Metres; -Y is the front."""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import gloomgrin_stone as K
from monsters.breeds import pluckrex_props as PR
from monsters.breeds.pluckrex_form import mirror, unit


def frame(F, s: int):
    """(the cuff's start and end on the forearm's axis, its unit axis, the outward 'face' direction, the side axis)."""
    B = F.G['bracer']
    A = F.G['arm']
    e, w = v3(mirror(A['elbow'], s)), v3(mirror(A['wrist'], s))
    ax = unit(w - e)
    a = e + (w - e) * B['t'][0]
    b = e + (w - e) * B['t'][1]
    face = v3(B['face']) * v3((s, 1.0, 1.0))
    face = unit(face - ax * float(face @ ax))
    side = unit(np.cross(ax, face))
    return a, b, ax, face, side


def sun_mask(u: np.ndarray, q: np.ndarray, B: dict) -> np.ndarray:
    """0..1 on the carved sun: (u along, q across) in metres from the sun's centre on the cuff's face."""
    r = np.hypot(u, q)
    disc = smooth(B['sun_r'] * 1.05, B['sun_r'] * 0.92, r)
    ring = smooth(B['sun_r'] * 1.38, B['sun_r'] * 1.28, r) * smooth(B['sun_r'] * 1.12, B['sun_r'] * 1.2, r)
    ang = np.arctan2(q, u)
    ray_w = 0.5 * (1.0 + np.cos(8.0 * ang))
    rays = smooth(0.72, 0.92, ray_w) * smooth(B['sun_r'] * 1.25, B['sun_r'] * 1.4, r) * smooth(B['sun_r'] * 2.25, B['sun_r'] * 1.95, r)
    return np.clip(np.maximum(np.maximum(disc, rays), ring * 0.0), 0.0, 1.0)


def build_bracer(name: str, F, s: int, high: bool) -> bpy.types.Object:
    B = F.G['bracer']
    a, b, ax, face, side = frame(F, s)
    L = float(np.linalg.norm(b - a))
    A_r = (F.G['arm']['r'][2], F.G['arm']['r'][3])
    nt = 64 if high else 10
    na = 128 if high else 20
    ts = np.linspace(0.0, 1.0, nt)
    angs = np.linspace(0.0, 2 * math.pi, na, endpoint=False)
    verts, att = [], []
    for t in ts:
        rim = 1.0 + B['rim'] * (smooth(0.14, 0.04, t) + smooth(0.86, 0.96, t))
        # polish: the cuff's ends roll down into the forearm (end-on, a flat end face read as a hollow bore)
        edge = smooth(0.0, 0.09, t) * smooth(1.0, 0.91, t)
        tf = B['t'][0] + t * (B['t'][1] - B['t'][0])
        rf = A_r[0] + (A_r[1] - A_r[0]) * tf - 0.004 * F.k
        for th in angs:
            d = face * math.cos(th) + side * math.sin(th)
            g = 0.0
            if high:
                # four slabs: deep grooves between them (one each side of the sun)
                for k in range(4):
                    dth = math.atan2(math.sin(th - (math.pi / 4 + k * math.pi / 2)), math.cos(th - (math.pi / 4 + k * math.pi / 2)))
                    g = max(g, math.exp(-(dth / 0.09) ** 2))
                g = max(g, math.exp(-((t - 0.17) / 0.018) ** 2), math.exp(-((t - 0.83) / 0.018) ** 2)) if 0.1 < t < 0.9 else g
            r = (rf + B['th'] * rim * edge) * (1.0 - B['groove'] * g)
            verts.append(a + ax * (L * t) + d * r)
            att.append((t, th / (2 * math.pi), 0.0))
    faces = []
    for i in range(nt - 1):
        for j in range(na):
            jn = (j + 1) % na
            faces.append((i * na + j, i * na + jn, (i + 1) * na + jn, (i + 1) * na + j))
    for end, i0 in ((0, 0), (1, (nt - 1) * na)):
        c = len(verts)
        verts.append(a + ax * (L * end))
        att.append((float(end), 0.0, 0.0))
        for j in range(na):
            jn = (j + 1) % na
            faces.append((c, i0 + jn, i0 + j) if end == 0 else (c, i0 + j, i0 + jn))
    verts = np.array(verts)
    att = np.array(att)
    # the sun on the outer face, in the cuff's middle: carved a little in (the rays) and raised (the disc)
    mid = a + ax * (L * 0.5)
    rel = verts - mid
    u = rel @ ax
    out = rel @ face
    q = rel @ side
    sm = sun_mask(u, q, B) * (out > 0)
    att[:, 2] = sm
    if high:
        nrm = rel - ax[None] * u[:, None]
        nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        crack, _tone, chips = (lambda c: (smooth(0.0016, 0.0005, c[1] - c[0]), None, K.facets(verts, 0.012, 9)))(K.voronoi(verts, 0.022, 31))
        dz = -0.0025 * crack - 0.002 * chips - B['carve'] * sm * (smooth(B['sun_r'] * 0.9, B['sun_r'] * 1.2, np.hypot(u, q)))
        dz = dz + 0.0015 * sm * smooth(B['sun_r'] * 1.0, B['sun_r'] * 0.7, np.hypot(u, q))
        verts = verts + nrm * dz[:, None] * (np.abs(u) < L * 0.5 - 0.002)[:, None]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in verts], [], faces)
    me.update()
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    me.update()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    n = len(verts)
    S.add_attr(ob, 'pt', att)
    S.add_attr(ob, 'gpart', np.full(n, float(PR.P_BRACER)))
    S.add_attr(ob, 'anchor', np.tile(mid, (n, 1)))
    S.add_attr(ob, 'item', np.zeros(n))
    S.add_attr(ob, 'side', np.full(n, float(s)))
    ob['prop'] = 'bracers'
    return ob


def build(F, high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    return [build_bracer(f'{tag}_bracer{"L" if s > 0 else "R"}', F, s, high) for s in (1, -1)]


def prop_bones(F) -> list[dict]:
    out = []
    for s, t in ((1, 'L'), (-1, 'R')):
        a, b, ax, _f, _s = frame(F, s)
        out.append({'name': f'bracer{t}', 'parent': f'forearm.{t}', 'head': tuple(map(float, a)), 'tail': tuple(map(float, b))})
    return out


def paint(F, pt: np.ndarray, co: np.ndarray, col: dict, lin, blend):
    """(rgb, rough, coat, glow) for bracer vertices: weathered grey stone, slab by slab, dark grooves and cracks, worn
    light edges, the gold sun."""
    m = len(pt)
    t, ang, sm = pt[:, 0], pt[:, 1], pt[:, 2]
    slab = np.floor((ang * 4.0 - 0.5) % 4).astype(np.int64) + 4 * (t > 0.5)
    tone = K.hash1(slab, 41)
    rgb = np.tile(lin(col['stone']), (m, 1)) * (0.9 + 0.2 * tone)[:, None]
    f1, f2, fid = K.voronoi(co, 0.02, 31)
    crack = smooth(0.0018, 0.0005, f2 - f1)
    rgb = blend(rgb, crack * 0.55, col['stone_dark'])
    grain = K.fbm(co, 1 / 0.008, 17, 2)
    rgb = rgb * (1.0 + 0.08 * grain)[:, None]
    gr = np.zeros(m)
    for k in range(4):
        d = (ang * 4.0 - 0.5 - k) % 4.0
        d = np.minimum(d, 4.0 - d)
        gr = np.maximum(gr, smooth(0.08, 0.02, d))
    gr = np.maximum(gr, smooth(0.035, 0.012, np.abs(t - 0.17)) * (t > 0.1) + smooth(0.035, 0.012, np.abs(t - 0.83)) * (t < 0.9))
    rgb = blend(rgb, gr * 0.7, col['stone_dark'])
    rim = smooth(0.12, 0.04, t) + smooth(0.88, 0.96, t)
    rgb = blend(rgb, rim * 0.35, col['stone_hi'])
    rgb = blend(rgb, sm, col['accent'])
    rgb = blend(rgb, sm * 0.3, col['gold_rib'])
    rough = 0.82 - 0.1 * rim
    rough = rough * (1 - sm) + 0.38 * sm
    coat = 0.3 * sm
    glow = sm * F.G.get('glow', {}).get('sun', 0.75)
    return rgb, rough, coat, glow
