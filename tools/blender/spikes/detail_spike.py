"""Art 2.1 detail spike, round 2 (docs/ART_2_DETAIL.md §7): Puddlepup's head and one front paw at the Ultra targets.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/spikes/detail_spike.py -- [--stages build,bake,export,render] [--quick]

build   the high-detail source (a smooth 3.5 mm voxel body, carved muzzle, nose, eyes, ribbed fin ears and a coat of soft
        sculpted fur clumps) and the game mesh (the decimated body, fin sheets, eye domes, a coat of soft-tipped fur
        cards and the small crown tuft); saves spike.blend
bake    Cycles (GPU when there is one), selected → active: tangent normals, AO, base colour (each clump painted at its
        root, so markings follow the fur) and roughness / clearcoat, into
          - the body atlas (UV0): the head, paw and fins at the density a 2048² atlas gives a whole Puddlepup, with the
            strip at the bottom holding the tuft-lock tiles and the soft fur-card tiles (alpha in the base colour), and
          - the cinematic head set (UV1): the head, eyes and fins alone on their own 2048² atlas (Monster Card, cutscenes);
        the cards' and tuft's vertex colours are sampled from the baked colour at their roots
export  spike.glb (the game meshes only, two UV sets on the head and fins) plus the atlases as PNG
render  EEVEE stills (source = the sculpt with preview cards; game = the low mesh with its baked maps)

Everything lands in tools/blender/out/spike-detail/ (gitignored). Nothing here touches the shipped Puddlepup.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # tools/blender → `lib`

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from lib import common as C  # noqa: E402
from lib import mesh as M  # noqa: E402
from lib.mesh import Part  # noqa: E402
from lib.nodes import NB, new_image, new_mat  # noqa: E402
# A1 (ART_2_DETAIL §9): the generic surface and bake code now lives in lib/surface.py and lib/bake.py
from lib import bake as BK  # noqa: E402
from lib.bake import (BASE_AO, CARD_CELLS, CELLS, LOCK_CELLS, STRIP, bake, image_array, pack_atlas,  # noqa: E402,F401
                      sample_vertex_colours, save_png, set_material, strip_uvs, use_gpu)
from lib.surface import (add_attr, attr_array, base_attrs, build_body, card_template, coat_normals, decimate_to,  # noqa: E402,F401
                         elements_object, in_ellipsoid, instance, lock_frames, lock_template, low_strand_template, mesh_area,
                         mesh_arrays, norm, polyline_dist, scatter, scatter_layer, set_positions, smooth, v3)

OUT = C.OUT_ROOT / 'spike-detail'

# ----------------------------------------------------------------------------- palette (CONTENT §2.2 #1)
TEAL, CREAM, PINK, EYE = '#3FB6A8', '#F3E6C4', '#F28FA8', '#24323A'
# The card suggests #36A698 for dapples; the pictures show crisp, clearly darker spots, so derive a deeper teal.
DAPPLE = C.shade_hex(TEAL, 0.66, cool=0.03)
BROW = C.mix_hex(EYE, TEAL, 0.3)
NOSE = '#16171B'
MOUTH = '#4A2E35'

# ----------------------------------------------------------------------------- proportions (metres; faces −Y, Z up)
# Measured on 2-turnaround.png (1 m to the top of the head): a round head ~0.52 m wide over its fur, eyes ~0.1 m
# across a little below the middle of the head, the nose just below the eye line, a small cream muzzle; the ears start
# on the upper sides of the head and hang out and down to the chin (~0.95 m across their tips).
HEAD_C = Vector((0.0, -0.37, 0.77))
HEAD_R = (0.214, 0.182, 0.215)                   # round 4: a little narrower; round 5: shallower front to back
EYE_C = {s: Vector((0.125 * s, -0.522, 0.755)) for s in (1, -1)}
EYE_R = 0.061                                    # round 3: +10% (the pictures' eyes read bigger)
# round 5: the eye is a flatter lens set into the face: (dome height, how far its centre sits behind the surface) in
# eye radii, and how much wider the lens is so the visible eye keeps its size (round 4 stood 2.4 cm proud)
EYE_DEPTH = (0.44, 0.30)
EYE_SPREAD = 1.1
NOSE_C = Vector((0.0, -0.616, 0.708))
MUZZLE = ((0.0, -0.578, 0.666), (0.07, 0.056, 0.056))      # the plush, fur-free cream muzzle (centre, radii; round 4: smaller, set back)
EAR_ROOT = {s: Vector((0.146 * s, -0.37, 0.93)) for s in (1, -1)}
CHEEK = (0.11, -0.455, 0.68, 0.088)            # the cheek fluff (x, y, z, radius), mirrored
EAR_GAP = 0.028                                  # the ear hangs this far outside the head and cheeks (the fur between)
PAW = Vector((0.15, -0.19, 0.0))                 # the front-left paw's ground point
TOE_DX = (-0.076, 0.0, 0.076)


# ----------------------------------------------------------------------------- ears: a ribbed fan that hangs from the top of the head
def ear_frame(s: int):
    """Root, pink-face normal, in-plane down and outward axes for the left (s=1) or right (s=-1) ear."""
    R = EAR_ROOT[s]
    npk = Vector((0.42 * s, -0.9, 0.1)).normalized()             # the pink face looks mostly forward
    down = Vector((0, 0, -1))
    e2 = (down - npk * down.dot(npk)).normalized()
    e1 = Vector((s, 0, 0))
    e1 = (e1 - npk * e1.dot(npk) - e2 * e1.dot(e2)).normalized()
    return R, npk, e2, e1


N_RIBS = 6
EAR_THETA = (math.radians(40), math.radians(4))                  # outer edge (v=0) → inner edge (v=1), from straight down
EAR_LEN = (0.46, 0.5)


def ear_point(s: int, u: float, v: float, rib_relief: float = 0.0) -> Vector:
    """u 0..1 from the root to the scalloped far edge (already scaled by the scallop), v 0..1 outer → inner."""
    R, npk, e2, e1 = ear_frame(s)
    th = EAR_THETA[0] + (EAR_THETA[1] - EAR_THETA[0]) * v
    L = EAR_LEN[0] + (EAR_LEN[1] - EAR_LEN[0]) * v
    d = e2 * math.cos(th) + e1 * math.sin(th)
    p = R + d * (u * L)
    # the fan cups gently toward its pink face and droops (no pleats: they read as a crimped paper fan)
    p += npk * (0.045 * u * u)
    p += Vector((0, 0, -0.03 * u * u))
    p += npk * rib_relief
    # it hangs outside the head and cheeks, so the whole ear shows from its root on top (a flat fan ran inside the
    # head and only came out at mid-side)
    m = head_side_x(p.y, p.z) + EAR_GAP * float(smooth(0.0, 0.25, u))
    ax = abs(p.x)
    p.x = s * 0.5 * (ax + m + math.sqrt((ax - m) ** 2 + 0.02 ** 2))
    return p


def head_side_x(y: float, z: float) -> float:
    """How far out the head's dome and cheeks reach at depth y and height z."""
    q = 1.0 - ((y - HEAD_C.y) / HEAD_R[1]) ** 2 - ((z - HEAD_C.z) / HEAD_R[2]) ** 2
    x = HEAD_R[0] * math.sqrt(q) if q > 0 else 0.0
    cx, cy, cz, cr = CHEEK
    q = 1.0 - ((y - cy) / (cr * 0.95)) ** 2 - ((z - cz) / (cr * 0.9)) ** 2
    return max(x, cx + cr * math.sqrt(q)) if q > 0 else x


def scallop(v: float) -> float:
    """A gentle wave along the far edge: the rib tips reach a little further, soft hollows between (no points)."""
    return 1.0 - 0.026 * (0.5 - 0.5 * math.cos(2 * math.pi * N_RIBS * v))


def rib_mask(v: float, width: float = 0.11) -> float:
    k = (v * N_RIBS) % 1.0
    d = min(k, 1.0 - k)                                          # 0 on a rib
    return math.exp(-(d / width) ** 2)


def build_ear_sheet(name: str, s: int, nu: int, nv: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    uv_l = bm.loops.layers.uv.new('UVMap')
    rows = []
    params = []
    for j in range(nu + 1):
        u = j / nu
        row = []
        for i in range(nv + 1):
            v = i / nv
            uu = u * scallop(v)
            params.append((uu, v))
            relief = 0.0
            if high:
                relief = 0.0028 * rib_mask(v) * (1.0 - 0.5 * u) * smooth(0.04, 0.2, u)
                relief += 0.0004 * math.sin(u * 90.0) * (1.0 - rib_mask(v))
            row.append(bm.verts.new(ear_point(s, uu, v, relief)))
        rows.append(row)
    for j in range(nu):
        for i in range(nv):
            corners = [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]
            if s < 0:
                corners = [corners[0], corners[3], corners[2], corners[1]]
            f = bm.faces.new([rows[jj][ii] for jj, ii in corners])
            for lp, (jj, ii) in zip(f.loops, corners):
                lp[uv_l].uv = (ii / nv, jj / nu)
    bm.normal_update()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    uu = np.array([a for a, _ in params])
    vv = np.array([b for _, b in params])
    rib = np.array([rib_mask(x) for x in vv])
    add_attr(ob, 'fan', np.stack([uu, vv, rib], axis=1))
    return ob


def _orient(long_axis: Vector, width_axis: Vector) -> tuple[float, float, float]:
    d = long_axis.normalized()
    w = (width_axis - d * width_axis.dot(d)).normalized()
    n = w.cross(d).normalized()
    m = Matrix((w, d, n)).transposed()
    e = m.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


# ----------------------------------------------------------------------------- the smooth bodies
def head_parts() -> list[Part]:
    ps = [
        Part('head', 'sphere', loc=tuple(HEAD_C), radius=1.0, scale=HEAD_R),
        Part('forehead', 'sphere', loc=(0.0, -0.42, 0.85), radius=0.13, scale=(1.3, 0.85, 0.85)),
        Part('cheek', 'sphere', loc=CHEEK[:3], radius=CHEEK[3], scale=(1.0, 0.95, 0.9), mirror=True),
        Part('pad', 'sphere', loc=(0.029, -0.566, 0.666), radius=0.039, scale=(1.0, 0.95, 0.85), mirror=True),
        Part('bridge', 'sphere', loc=(0.0, -0.556, 0.716), radius=0.043, scale=(1.05, 1.2, 0.8)),
        Part('chin', 'sphere', loc=(0.0, -0.54, 0.626), radius=0.038, scale=(1.2, 0.95, 0.7)),
        Part('nose', 'sphere', loc=tuple(NOSE_C), radius=0.035, scale=(1.15, 0.72, 0.66)),
        Part('neck', 'capsule', loc=(0.0, -0.34, 0.66), to=(0.0, -0.3, 0.56), radius=0.13),
    ]
    for s in (1, -1):
        R, npk, e2, e1 = ear_frame(s)
        tag = 'L' if s > 0 else 'R'
        # a furry cap over the top of the ear, straddling the fin, merged into the head (it ends at the root: no bump)
        cap = ear_point(s, 0.3, 0.5)
        long = (cap - R).normalized()
        ps.append(Part(f'earcap{tag}', 'fin', loc=tuple(cap - long * 0.025), radius=0.11,
                       scale=(0.62, 1.0, 0.22), taper=0.3, rot=_orient(-long, e1)))
        # a narrower furry band down the outer edge toward the tip
        band = ear_point(s, 0.6, 0.04)
        longb = (band - R).normalized()
        ps.append(Part(f'earband{tag}', 'fin', loc=tuple(band), radius=0.17,
                       scale=(0.18, 1.0, 0.11), taper=0.55, rot=_orient(-longb, e1)))
        # the root sits inside the head's curve; round 2's (5 cm proud of the dome) read as teddy-bear ears
        ps.append(Part(f'earroot{tag}', 'sphere', loc=tuple(R + Vector((0.006 * s, 0.0, -0.05))), radius=0.056))
    return ps


CAP_SCALE = (1.05, 0.72, 0.9)
CAP_R = tuple(0.027 * k for k in CAP_SCALE)


def cap_centres() -> list[Vector]:
    return [Vector((PAW.x + dx * 1.05, PAW.y - 0.178 + abs(dx) * 0.3, 0.036)) for dx in TOE_DX]


def paw_parts() -> list[Part]:
    x, y = PAW.x, PAW.y
    ps = [
        Part('leg', 'capsule', loc=(x, y + 0.02, 0.36), to=(x, y - 0.005, 0.11), radius=0.076),
        Part('foot', 'sphere', loc=(x, y - 0.05, 0.056), radius=0.105, scale=(1.25, 1.12, 0.55)),
        Part('web', 'sphere', loc=(x, y - 0.125, 0.028), radius=0.06, scale=(1.7, 0.6, 0.3)),
        Part('pad', 'sphere', loc=(x, y - 0.04, 0.011), radius=0.05, scale=(1.2, 0.95, 0.3)),
    ]
    for k, dx in enumerate(TOE_DX):
        ps.append(Part(f'toe{k}', 'sphere', loc=(x + dx * 1.02, y - 0.128 + abs(dx) * 0.3, 0.043), radius=0.044,
                       scale=(0.95, 1.3, 0.9)))
        ps.append(Part(f'cap{k}', 'sphere', loc=tuple(cap_centres()[k]), radius=0.027, scale=CAP_SCALE))
    return ps


# ----------------------------------------------------------------------------- carving (high source only)


def mouth_curve() -> list[tuple[float, float]]:
    """The closed smile of 3-faces.png's neutral: a short philtrum from the nose, then a soft W curling up."""
    top, mid = NOSE_C.z - 0.026, NOSE_C.z - 0.046
    pts = [(0.0, top), (0.0, mid)]
    right = []
    for k in range(1, 13):
        t = k / 12
        x = 0.046 * t
        z = mid - 0.008 * math.sin(math.pi * min(1.0, t * 1.15)) + 0.007 * t ** 3
        right.append((x, z))
    return [(-x, z) for x, z in reversed(right)] + pts[1:] + right


def whisker_dots() -> list[tuple[float, float, float]]:
    out = []
    zc = NOSE_C.z
    for s in (1, -1):
        for z, xs in ((zc - 0.022, (0.038, 0.053, 0.067)), (zc - 0.036, (0.044, 0.06)), (zc - 0.05, (0.05,))):
            for x in xs:
                out.append((x * s, z, 0.0034))
    return out


def carve_head(ob: bpy.types.Object) -> None:
    co, vn = mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    front = smooth(-0.5, -0.57, y)
    md = polyline_dist(x, z, mouth_curve())
    groove = np.exp(-(md / 0.0022) ** 2) * front * (z < NOSE_C.z - 0.02)
    dots = np.zeros_like(x)
    for dx, dz, r in whisker_dots():
        dd = np.sqrt((x - dx) ** 2 + (z - dz) ** 2)
        dots = np.maximum(dots, np.exp(-(dd / r) ** 2))
    dots *= front
    nos = np.zeros_like(x)
    for s in (1, -1):
        dd = np.sqrt(((x - 0.014 * s) / 1.4) ** 2 + (z - (NOSE_C.z - 0.012)) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.0058) ** 2))
    nos *= smooth(NOSE_C.y + 0.018, NOSE_C.y + 0.008, y)
    # the muzzle stays plush and smooth: only the mouth line, the nostrils and a few shallow whisker pits
    disp = -0.0022 * groove - 0.005 * nos         # round 4: no whisker pits (they read as bumps and specks)
    set_positions(ob, co + vn * disp[:, None])
    base_attrs(ob, co, {'mouth': groove, 'dots': dots})


def carve_paw(ob: bpy.types.Object) -> None:
    co, vn = mesh_arrays(ob)
    lip = np.zeros(len(co))
    for c in cap_centres():
        d = np.linalg.norm((co - v3(c)) / v3(CAP_R), axis=1)
        lip = np.maximum(lip, np.exp(-((d - 1.0) / 0.07) ** 2))
    peb = np.sin(co[:, 0] * 700.0) * np.sin(co[:, 1] * 650.0) * (co[:, 2] < 0.03)
    set_positions(ob, co + vn * (-0.0014 * lip + 0.0002 * peb)[:, None])
    base_attrs(ob, co)


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    """A glossy dome. Its local frame: +Z looks out of the eye (a little forward of the head's surface normal)."""
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * 0.96 * EYE_SPREAD, v.co.y * EYE_R * 1.08 * EYE_SPREAD, v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    c = EYE_C[s]
    surf_n = Vector(((c.x - HEAD_C.x) / HEAD_R[0] ** 2, (c.y - HEAD_C.y) / HEAD_R[1] ** 2, (c.z - HEAD_C.z) / HEAD_R[2] ** 2)).normalized()
    look = (surf_n * 0.68 + Vector((0, -1, 0)) * 0.32).normalized()
    look = (look + Vector((0, 0, 0.05))).normalized()
    up = Vector((0, 0, 1))
    xax = up.cross(look).normalized()
    yax = look.cross(xax).normalized()
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    ob.matrix_world = Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m
    return ob


# ----------------------------------------------------------------------------- scattering


# ----------------------------------------------------------------------------- where the fur goes, and how it lies
def head_zones(p: np.ndarray, n: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ear = np.zeros(len(p), bool)
    ear_u = np.zeros(len(p))
    for s in (1, -1):
        R, npk, e2, e1 = ear_frame(s)
        rel = p - v3(R)
        mid = norm(v3(ear_point(s, 1.0, 0.5) - R))
        along = rel @ mid
        on = (np.sign(x) == s) & (along > 0.035) & (np.abs(x) > 0.16)
        ear |= on
        ear_u = np.where(on, along / EAR_LEN[1], ear_u)
    muzzle = in_ellipsoid(p, *MUZZLE) < 1.0
    nose = np.linalg.norm(p - v3(NOSE_C), axis=1) < 0.06
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = (y < -0.45) & (z > 0.6) & (z < 0.9) & (np.abs(x) < 0.19) & ~ear
    crown = (z > 0.9) & ~ear
    tuft = (np.abs(x) < 0.05) & (z > 0.97) & (y > -0.44) & (y < -0.34)
    cheek = (np.abs(x) > 0.12) & (z < 0.74) & (y < -0.36) & ~ear & ~muzzle
    throat = (z < 0.6) & ~ear & ~muzzle
    mirrored = p.copy()
    mirrored[:, 0] = np.abs(mirrored[:, 0])
    blush = in_ellipsoid(mirrored, (0.15, -0.5, 0.69), (0.06, 0.08, 0.05)) < 1.0
    return {'ear': ear, 'ear_u': ear_u, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face, 'crown': crown,
            'tuft': tuft, 'cheek': cheek, 'throat': throat, 'blush': blush, 'cut': z < 0.44}


def head_flow(p: np.ndarray, n: np.ndarray, zones) -> np.ndarray:
    g = norm(p - v3((NOSE_C.x, NOSE_C.y - 0.03, NOSE_C.z)))   # combed back from the nose
    wd = smooth(0.86, 0.62, p[:, 2])[:, None]
    g = norm(g * (1 - wd) + v3((0, 0, -1)) * wd * 1.3)
    for s in (1, -1):
        R = v3(EAR_ROOT[s])
        on = zones['ear'] & (np.sign(p[:, 0]) == s)
        g = np.where(on[:, None], norm(p - R + v3((0, 0, -0.05))), g)
    return norm(g - n * (g * n).sum(axis=1, keepdims=True))


def head_lock_params(p, n):
    """Lying clumps (baked): per point spacing, length, width, lift (radians); NaN spacing = none."""
    z = head_zones(p, n)
    k = len(p)
    # round 5: long narrow wet locks, about 3:1 (round 4's were about as wide as long and read as leaves)
    L = np.full(k, 0.068)
    W = np.full(k, 0.0115)
    lift = np.full(k, math.radians(2.0))
    L = np.where(z['face'], 0.044, L)
    W = np.where(z['face'], 0.008, W)
    L = np.where(z['crown'], 0.072, L)
    W = np.where(z['crown'], 0.012, W)
    L = np.where(z['cheek'], 0.076, L)
    W = np.where(z['cheek'], 0.013, W)
    L = np.where(z['blush'], 0.044, L)
    L = np.where(z['throat'], 0.085, L)
    W = np.where(z['throat'], 0.014, W)
    L = np.where(z['ear'], 0.076, L)
    W = np.where(z['ear'], 0.012, W)
    near_eye = smooth(EYE_R * 1.12, EYE_R * 1.8, z['eye_d'])
    L = L * (0.5 + 0.5 * near_eye)
    W = W * (0.62 + 0.38 * near_eye)
    skip = z['muzzle'] | z['nose'] | (z['eye_d'] < EYE_R * 1.1) | z['cut']
    sp = np.where(skip, np.nan, W * 0.55)
    return sp, L, W, lift, z


def head_card_params(p, n, layer: int):
    """Soft fur cards for the outline. Layer 0 covers the coat; layer 1 adds a second, longer fringe on the cheeks,
    the throat, the ear caps and the back of the head. None on the face front, the muzzle or around the eyes."""
    z = head_zones(p, n)
    k = len(p)
    back = p[:, 1] > -0.38
    if layer == 0:
        L = np.full(k, 0.07)
        W = np.full(k, 0.036)
        lift = np.full(k, math.radians(4))
        L = np.where(z['cheek'], 0.066, L)
        L = np.where(z['throat'], 0.058, L)
        L = np.where(z['ear'], 0.042, L)
        lift = np.where(z['ear'], math.radians(2), lift)
        sp = np.where(z['ear'], 0.034, 0.022)
        chin = (p[:, 2] < 0.64) & (p[:, 1] < -0.44)
        skip = z['face'] | z['muzzle'] | z['nose'] | (z['eye_d'] < 0.1) | z['cut'] | z['tuft'] | chin | z['blush']
    else:
        L = np.where(z['throat'], 0.08, 0.082)
        W = np.full(k, 0.04)
        lift = np.full(k, math.radians(10))
        sp = np.full(k, 0.045)
        chin = (p[:, 2] < 0.62) & (p[:, 1] < -0.46)
        fringe = (z['cheek'] | (back & (p[:, 2] < 0.9) & (p[:, 2] > 0.6))) & ~z['ear']
        skip = ~fringe | z['face'] | z['muzzle'] | (z['eye_d'] < 0.12) | z['cut'] | chin
    sp = np.where(skip, np.nan, sp)
    return sp, L, W, lift, z


def paw_lock_params(p, n):
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    L = np.where(zz > 0.13, 0.085, 0.04)
    W = np.where(zz > 0.13, 0.013, 0.01)
    lift = np.full(len(p), math.radians(3))
    toes = (zz < 0.095) & (y < PAW.y - 0.075)
    skip = toes | (zz < 0.04) | (zz > 0.37)
    return np.where(skip, np.nan, W * 0.55), L, W, lift, None


def paw_card_params(p, n, layer: int):
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    k = len(p)
    L = np.full(k, 0.08)
    W = np.full(k, 0.036)
    lift = np.full(k, math.radians(8 if layer == 0 else 13))
    sp = np.full(k, 0.026 if layer == 0 else 0.045)
    skip = (zz < 0.13) | (zz > 0.37)
    if layer == 1:
        # the second layer only on the back and outer side of the leg
        skip = skip | ((y < PAW.y) & (x < PAW.x + 0.03))
    return np.where(skip, np.nan, sp), L, W, lift, None


def paw_flow(p, n, zones=None) -> np.ndarray:
    g = np.tile(v3((0.0, -0.12, -1.0)), (len(p), 1))
    return norm(g - n * (g * n).sum(axis=1, keepdims=True))


# ----------------------------------------------------------------------------- shapes


def tuft_frames(surface: bpy.types.Object):
    """The small crown tuft of 2-turnaround.png: seven curved wet locks on top of the head, combed back and fanned."""
    bvh = BVHTree.FromObject(surface, bpy.context.evaluated_depsgraph_get())
    P, N, F, L, W, lift = [], [], [], [], [], []
    spots = [(0.0, -0.41, 0.0, 0.072, 34), (-0.022, -0.4, -26, 0.064, 29), (0.022, -0.4, 26, 0.064, 29),
             (-0.012, -0.43, -10, 0.058, 37), (0.013, -0.43, 12, 0.056, 37), (-0.04, -0.385, -44, 0.053, 22),
             (0.04, -0.383, 42, 0.053, 22)]
    for x, y, fan, ln, lf in spots:
        hit = bvh.ray_cast(Vector((x, y, 1.4)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        p = np.array(hit[0])
        n = np.array(hit[1])
        a = math.radians(fan)
        f = np.array([math.sin(a) + 0.4, math.cos(a) * 0.8, 0.3])
        f = f - n * (f @ n)
        P.append(p)
        N.append(n)
        F.append(f / np.linalg.norm(f))
        L.append(ln * 0.9)
        W.append(0.034)
        lift.append(math.radians(lf))
    P, N, F = np.array(P), np.array(N), np.array(F)
    return lock_frames(P, N, F, np.array(L), np.array(W), np.array(lift), np.random.default_rng(77), None, jitter_deg=4)


# ----------------------------------------------------------------------------- materials (paint, roughness, review)
def _attr_vec(nb: NB, name: str):
    return nb.attribute(name).outputs['Vector']


def _attr_fac(nb: NB, name: str):
    return nb.attribute(name).outputs['Fac']


def ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


DAPPLES = [  # (centre, radii): the round spot on the forehead, the scatter over the crown, the ear caps
    ((0.0, -0.545, 0.885), (0.03, 0.04, 0.03)),
    ((0.058, -0.53, 0.915), (0.022, 0.035, 0.02)), ((-0.06, -0.53, 0.912), (0.021, 0.035, 0.02)),
    ((0.03, -0.47, 0.965), (0.024, 0.03, 0.022)), ((-0.04, -0.455, 0.968), (0.025, 0.03, 0.022)),
    ((0.0, -0.37, 0.99), (0.03, 0.03, 0.022)), ((0.09, -0.4, 0.955), (0.022, 0.026, 0.022)), ((-0.095, -0.38, 0.95), (0.024, 0.028, 0.022)),
    ((0.05, -0.27, 0.965), (0.027, 0.03, 0.025)), ((-0.06, -0.25, 0.955), (0.026, 0.03, 0.025)),
    ((0.0, -0.2, 0.9), (0.03, 0.03, 0.028)),
    ((0.235, -0.36, 0.86), (0.024, 0.03, 0.024)), ((0.25, -0.39, 0.78), (0.028, 0.032, 0.028)),
    ((-0.235, -0.36, 0.86), (0.024, 0.03, 0.024)), ((-0.25, -0.39, 0.78), (0.028, 0.032, 0.028)),
    ((0.17, -0.27, 0.72), (0.026, 0.03, 0.026)), ((-0.17, -0.27, 0.72), (0.026, 0.03, 0.026)),
    # the stand-in body's back (performance check only)
    ((0.12, -0.05, 0.64), (0.04, 0.04, 0.04)), ((-0.1, 0.06, 0.65), (0.04, 0.045, 0.04)), ((0.06, 0.2, 0.62), (0.04, 0.04, 0.04)),
    ((-0.16, 0.25, 0.52), (0.035, 0.04, 0.035)), ((0.22, 0.12, 0.5), (0.035, 0.04, 0.035)), ((0.0, 0.62, 0.42), (0.04, 0.05, 0.03)),
]


def paint_body_material(name: str) -> bpy.types.Material:
    """Base colour as emission. Markings are evaluated at each clump's root (they follow the fur); the blush and the
    eye lid line at the true position (they stay soft and smooth)."""
    m, nb = new_mat(name)
    p = _attr_vec(nb, 'root')
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', _attr_fac(nb, 'kind'), 0.5)
    col = nb.rgb(C.lin(TEAL))
    # cream: the muzzle, a mask that rises to the nose bridge and around the lower halves of the eyes, the lower
    # cheeks, the chin and throat
    cream = nb.math('MAXIMUM', ell(nb, p, (0.0, -0.56, 0.64), (0.2, 0.17, 0.07), 0.12), ell(nb, p, MUZZLE[0], tuple(r * 1.12 for r in MUZZLE[1]), 0.08))
    cream = nb.math('MAXIMUM', cream, ell(nb, p, (0.0, -0.57, 0.725), (0.05, 0.1, 0.035), 0.15))
    cream = nb.math('MAXIMUM', cream, ell(nb, p, (0.0, -0.45, 0.53), (0.18, 0.2, 0.12), 0.1))
    cream = nb.math('MAXIMUM', cream, ell(nb, p, (0.0, -0.05, 0.27), (0.2, 0.42, 0.13), 0.12))
    cream = nb.math('MAXIMUM', cream, ell(nb, p, (0.0, -0.33, 0.46), (0.16, 0.1, 0.16), 0.12))
    for s in (1, -1):
        cream = nb.math('MAXIMUM', cream, ell(nb, p, (0.122 * s, -0.53, 0.698), (0.076, 0.07, 0.045), 0.22))
    # foot: a cream rim around the sole
    cream = nb.math('MAXIMUM', cream, nb.math('MULTIPLY', ell(nb, p, (PAW.x, PAW.y - 0.07, 0.0), (0.17, 0.2, 0.06), 0.12),
                                             nb.smooth(nb.sep(p)[2], 0.045, 0.02)))
    col = nb.mix(cream, col, nb.rgb(C.lin(CREAM)))
    dap = None
    for c, r in DAPPLES:
        e = ell(nb, pos, c, r, 0.16)
        dap = e if dap is None else nb.math('MAXIMUM', dap, e)
    dap = nb.math('MULTIPLY', dap, nb.math('SUBTRACT', 1.0, cream))
    col = nb.mix(dap, col, nb.rgb(C.lin(DAPPLE)))
    # brows: one soft dark dash per side well above the eye, by position (painted by root they broke into scribbles)
    brow = None
    for s in (1, -1):
        e = ell(nb, pos, (0.111 * s, -0.53, 0.858), (0.032, 0.05, 0.0115), 0.35)
        brow = e if brow is None else nb.math('MAXIMUM', brow, e)
    col = nb.mix(brow, col, nb.rgb(C.lin(BROW)))
    # the blush: a soft round spot between the eye and the muzzle, by position (no streaks along the clumps)
    blush = None
    for s in (1, -1):
        e = ell(nb, pos, (0.15 * s, -0.5, 0.69), (0.052, 0.06, 0.042), 0.6)
        blush = e if blush is None else nb.math('MAXIMUM', blush, e)
    col = nb.mix(nb.math('MULTIPLY', blush, 0.8), col, nb.rgb(C.lin('#F5919F')))
    # the upper lid line, on the body only
    rim = None
    for s in (1, -1):
        c = EYE_C[s]
        outer = ell(nb, pos, tuple(c + Vector((0, 0, 0.002))), (EYE_R * 1.13, EYE_R * 1.5, EYE_R * 1.2), 0.03)
        inner = ell(nb, pos, tuple(c + Vector((0, 0, -0.006))), (EYE_R * 1.04, EYE_R * 1.5, EYE_R * 1.08), 0.03)
        top = nb.smooth(nb.sep(pos)[2], c.z + EYE_R * 0.05, c.z + EYE_R * 0.45)
        e = nb.math('MULTIPLY', nb.math('MULTIPLY', outer, nb.math('SUBTRACT', 1.0, inner)), top)
        rim = e if rim is None else nb.math('MAXIMUM', rim, e)
    col = nb.mix(nb.math('MULTIPLY', rim, is_body), col, nb.rgb(C.lin('#2A2226')))
    # nose, mouth line, whisker dots
    col = nb.mix(ell(nb, pos, tuple(NOSE_C), (0.044, 0.036, 0.03), 0.06), col, nb.rgb(C.lin(NOSE)))
    # the mouth line on the muzzle only (a clump rooted at its corner took its colour: a brown speck)
    col = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', _attr_fac(nb, 'mouth'), 1.2, clamp=True), is_body), col, nb.rgb(C.lin(MOUTH)))
    # paw: toe caps and the central pad
    pad = ell(nb, p, (PAW.x, PAW.y - 0.04, 0.011), (0.06, 0.048, 0.02), 0.08)
    for c in cap_centres():
        pad = nb.math('MAXIMUM', pad, ell(nb, p, tuple(c), tuple(r + 0.0015 for r in CAP_R), 0.03))
    col = nb.mix(pad, col, nb.rgb(C.lin(PINK)))
    # clump shading: slightly darker roots, lighter tips, a little per-clump variation (body surface untouched)
    tpos = _attr_fac(nb, 'tpos')
    lrand = _attr_fac(nb, 'lrand')
    shade = nb.math('ADD', 0.8, nb.math('MULTIPLY', tpos, 0.28))
    shade = nb.math('ADD', shade, nb.math('MULTIPLY', nb.math('SUBTRACT', lrand, 0.5), 0.08))
    shade = nb.mix(is_body, shade, 1.0, dtype='FLOAT')
    col = nb.mix(1.0, col, nb.comb(shade, shade, shade), blend='MULTIPLY')
    em = nb.new('ShaderNodeEmission')
    nb.link(col, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def paint_rough_material(name: str) -> bpy.types.Material:
    """G = roughness, B = clearcoat (the wet sheen), R = 1 (AO is baked separately and packed in later).
    Damp fur, not wet plastic: rough with a light coat; the gloss lives on the nose, pads and eyes."""
    m, nb = new_mat(name)
    p = _attr_vec(nb, 'root')
    tpos = _attr_fac(nb, 'tpos')
    is_lock = nb.math('GREATER_THAN', _attr_fac(nb, 'kind'), 0.5)
    rough = nb.mix(is_lock, 0.62, nb.math('ADD', 0.4, nb.math('MULTIPLY', nb.math('ABSOLUTE', nb.math('SUBTRACT', tpos, 0.45)), 0.3)), dtype='FLOAT')
    coat = nb.mix(is_lock, 0.08, 0.16, dtype='FLOAT')
    muzzle = ell(nb, p, MUZZLE[0], tuple(r * 1.1 for r in MUZZLE[1]), 0.1)
    rough = nb.mix(muzzle, rough, 0.58, dtype='FLOAT')
    coat = nb.mix(muzzle, coat, 0.06, dtype='FLOAT')
    glossy = ell(nb, p, tuple(NOSE_C), (0.044, 0.036, 0.03), 0.06)
    pad = ell(nb, p, (PAW.x, PAW.y - 0.04, 0.011), (0.06, 0.048, 0.02), 0.08)
    for c in cap_centres():
        pad = nb.math('MAXIMUM', pad, ell(nb, p, tuple(c), tuple(r + 0.0015 for r in CAP_R), 0.03))
    glossy = nb.math('MAXIMUM', glossy, pad)
    rough = nb.mix(glossy, rough, 0.2, dtype='FLOAT')
    coat = nb.mix(glossy, coat, 0.9, dtype='FLOAT')
    em = nb.new('ShaderNodeEmission')
    nb.link(nb.comb(1.0, rough, coat), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def paint_eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """Iris, pupil, catchlights and a soft lid shadow, in the eye's own object space (+Z out of the eye)."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    o = nb.coords().outputs['Object']
    x, y, zc = nb.sep(o)
    rx = nb.math('DIVIDE', x, EYE_R * 0.96)
    ry = nb.math('DIVIDE', y, EYE_R * 1.08)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', rx, 0.8), nb.math('DIVIDE', ry, 0.9), 0.0))
    iris_c = nb.ramp(ri, [(0.0, C.lin('#0A1014')), (0.5, C.lin('#0A1014')), (0.56, C.lin('#1A383E')),
                          (0.8, C.lin('#2B5E62')), (0.9, C.lin('#3A7274')), (0.95, C.lin('#13202A')), (1.0, C.lin('#13202A'))])
    low = nb.math('MULTIPLY', nb.smooth(ry, -0.15, -0.65), nb.smooth(ri, 0.95, 0.6))
    col = nb.mix(nb.math('MULTIPLY', low, 0.55), iris_c, nb.rgb(C.lin('#5AA8A0')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.24), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.3), 1.2), 0.0)), 0.2, 0.17)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.27), nb.math('ADD', ry, 0.32), 0.0)), 0.075, 0.058)
    col = nb.mix(nb.math('MAXIMUM', big, small), col, nb.rgb((1.0, 1.0, 1.0)))
    lid = nb.math('MULTIPLY', nb.smooth(ry, 0.6, 0.98), 0.5)
    col = nb.mix(lid, col, nb.rgb(C.lin('#141012')))
    em = nb.new('ShaderNodeEmission')
    nb.link(col, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def paint_fin_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """The pink membrane: deeper along the ribs, paler and thinner toward the scalloped edge, teal at the root."""
    m, nb = new_mat(name)
    fan = _attr_vec(nb, 'fan')
    u, v, rib = nb.sep(fan)
    if rough_pass:
        rough = nb.mix(rib, 0.3, 0.24, dtype='FLOAT')
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, rough, 0.45), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    col = nb.mix(nb.math('MULTIPLY', rib, 0.45), nb.rgb(C.lin(PINK)), nb.rgb(C.lin(C.shade_hex(PINK, 0.86))))
    col = nb.mix(nb.math('MULTIPLY', nb.smooth(u, 0.6, 1.0), 0.6), col, nb.rgb(C.lin('#FFD9E2')))
    col = nb.mix(nb.smooth(u, 0.16, 0.05), col, nb.rgb(C.lin(C.mix_hex(TEAL, PINK, 0.3))))
    em = nb.new('ShaderNodeEmission')
    nb.link(col, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def preview_card_material(name: str) -> bpy.types.Material:
    """For quick source renders before a bake: the paint colour with a procedural soft clump alpha."""
    paint = paint_body_material(name + '_paint')
    m = paint.copy()
    m.name = name
    nt = m.node_tree
    nb = NB(nt)
    em = next(n for n in nt.nodes if n.type == 'EMISSION')
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    src = em.inputs['Color'].links[0].from_socket
    bsdf = nb.new('ShaderNodeBsdfPrincipled')
    nb.link(src, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.5
    bsdf.inputs['Sheen Weight'].default_value = 0.5
    tpos = _attr_fac(nb, 'tpos')
    across = _attr_fac(nb, 'across')
    clumps = nb.math('ABSOLUTE', nb.math('SINE', nb.math('MULTIPLY', nb.math('ADD', across, 1.0), 2.0 * math.pi)))
    reach = nb.math('ADD', 0.62, nb.math('MULTIPLY', clumps, 0.36))
    # a soft fade over the last quarter of each clump's reach
    alpha = nb.math('DIVIDE', nb.math('SUBTRACT', reach, tpos), 0.25, clamp=True)
    nb.link(alpha, bsdf.inputs['Alpha'])
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    nt.nodes.remove(em)
    m.surface_render_method = 'DITHERED'
    m.use_backface_culling = False
    return m


# ----------------------------------------------------------------------------- atlas layout


# ----------------------------------------------------------------------------- build stage
LYING = {'thickness': 0.085, 'bury': 0.04}


def stage_build(quick: bool) -> dict:
    C.clear_scene()
    voxel = 0.006 if quick else 0.0035
    hi_head = build_body('hi_head', head_parts(), voxel, 4)
    hi_paw = build_body('hi_paw', paw_parts(), voxel * 0.8, 4)
    carve_head(hi_head)
    carve_paw(hi_paw)
    hi_ears = [build_ear_sheet(f'hi_ear{"L" if s > 0 else "R"}', s, 90 if not quick else 40, 120 if not quick else 48, True) for s in (1, -1)]
    hi_eyes = [build_eye(f'hi_eye{"L" if s > 0 else "R"}', s, True) for s in (1, -1)]

    # the game mesh: the smooth bodies decimated to the Ultra budget (the carving lives in the normal map)
    lo_head = build_body('lo_head', head_parts(), 0.006, 4)
    lo_paw = build_body('lo_paw', paw_parts(), 0.005, 4)
    decimate_to(lo_head, 14000)
    decimate_to(lo_paw, 4000)
    lo_ears = [build_ear_sheet(f'lo_ear{"L" if s > 0 else "R"}', s, 16, 48, False) for s in (1, -1)]
    lo_eyes = [build_eye(f'lo_eye{"L" if s > 0 else "R"}', s, False) for s in (1, -1)]

    # fur: soft lying clumps (baked into the maps) on the source; soft cards and the tuft on the game mesh
    tpl_hi = lock_template(7, 11, 3, strand=0.22, closed=False)
    lie_head, _ = scatter_layer('hi_locks_head', hi_head, head_lock_params, head_flow, 11, tpl_hi, quick, LYING['thickness'], LYING['bury'], 1.0)
    lie_paw, _ = scatter_layer('hi_locks_paw', hi_paw, paw_lock_params, paw_flow, 21, tpl_hi, quick, LYING['thickness'], LYING['bury'], 1.0)
    tpl_card = card_template()
    cards = []
    for tag, surf, fn, flow, seed in (('head', hi_head, head_card_params, head_flow, 31), ('paw', hi_paw, paw_card_params, paw_flow, 41)):
        for layer in (0, 1):
            ob, _ = scatter_layer(f'lo_cards_{tag}_{layer}', surf, lambda p, n, fn=fn, layer=layer: fn(p, n, layer), flow, seed + layer,
                                  tpl_card, quick, 0.0, 0.02, 3.0, jitter_deg=8.0)
            cards.append(ob)
    tuft_fr = tuft_frames(hi_head)
    tpl_tuft_hi = lock_template(9, 14, 3, strand=0.18)
    hi_tuft = elements_object('hi_tuft', instance(tpl_tuft_hi, tuft_fr, 0.34, 0.08), tpl_tuft_hi, tuft_fr['P'], 2.0, np.random.default_rng(3))
    tpl_tuft_lo = low_strand_template()
    lo_tuft = elements_object('lo_tuft', instance(tpl_tuft_lo, tuft_fr, 0.34, 0.08), tpl_tuft_lo, tuft_fr['P'], 2.0, np.random.default_rng(3))
    add_attr(lo_tuft, 'rootn', np.repeat(tuft_fr['N'], len(tpl_tuft_lo[0]), axis=0))

    # join the card layers per part
    lo_cards = {}
    groups = {tag: [o for o in cards if o.name.startswith(f'lo_cards_{tag}_')] for tag in ('head', 'paw')}
    for tag, parts in groups.items():
        joined = M.join_meshes(parts, f'lo_cards_{tag}')
        for name in ('root', 'rootn', 'across', 'tpos', 'lrand', 'kind'):
            add_attr(joined, name, np.concatenate([attr_array(o, name) for o in parts]))
        for o in parts:
            bpy.data.objects.remove(o, do_unlink=True)
        lo_cards[tag] = joined

    # UVs: the body atlas (UV0) for the head with its eyes, the paw and the fins, the strip kept at the bottom; the
    # cinematic set (UVCine) for the head, eyes and fins alone
    lo_body = M.join_meshes([lo_head], 'lo_body')
    lo_eye = M.join_meshes(lo_eyes, 'lo_eyes')
    for o in [lo_head] + lo_eyes:
        bpy.data.objects.remove(o, do_unlink=True)
    fins = M.join_meshes(lo_ears, 'lo_fins')
    fan = np.concatenate([attr_array(o, 'fan') for o in lo_ears])
    for o in lo_ears:
        bpy.data.objects.remove(o, do_unlink=True)
    add_attr(fins, 'fan', fan)
    for o in (lo_body, lo_eye, lo_paw, fins):
        if 'UVMap' not in o.data.uv_layers:
            o.data.uv_layers.new(name='UVMap')
    pack_atlas([lo_body, lo_eye, lo_paw, fins], 'UVMap', STRIP)
    pack_atlas([lo_body, lo_eye, fins], 'UVCine', 0.0)
    strip_uvs(lo_cards['head'], CARD_CELLS)
    strip_uvs(lo_cards['paw'], CARD_CELLS)
    strip_uvs(lo_tuft, LOCK_CELLS)

    n_card = len(card_template()[0])
    stats = {
        'hi_tris': sum(M.tri_count(o) for o in [hi_head, hi_paw, lie_head, lie_paw, hi_tuft] + hi_ears + hi_eyes),
        'lying_clumps': (len(lie_head.data.vertices) + len(lie_paw.data.vertices)) // len(tpl_hi[0]),
        'tris': {'head_body': M.tri_count(lo_body), 'eyes': M.tri_count(lo_eye), 'paw': M.tri_count(lo_paw), 'fins': M.tri_count(fins),
                 'cards_head': M.tri_count(lo_cards['head']), 'cards_paw': M.tri_count(lo_cards['paw']), 'tuft': M.tri_count(lo_tuft)},
        'cards': {'head': len(lo_cards['head'].data.vertices) // n_card, 'paw': len(lo_cards['paw'].data.vertices) // n_card},
        'tuft_locks': len(tuft_fr['P']),
        'areas_m2': {'head': mesh_area(lo_body), 'paw': mesh_area(lo_paw), 'fins': mesh_area(fins)},
    }
    stats['tris']['total'] = sum(stats['tris'].values())
    C.log(json.dumps(stats))
    (OUT / 'stats_build.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'spike.blend'))
    return stats


# ----------------------------------------------------------------------------- bake stage


def atlas_px_for(areas: dict) -> int:
    """The body-atlas size that gives the spike the texel density a 2048² atlas gives a whole Puddlepup (about 3.7 m²
    of surface: head, body, four legs, tail and fins)."""
    spike = areas['head'] + areas['paw'] + areas['fins']
    return int(round(2048 * math.sqrt(spike / 3.7) / 32)) * 32


def bake_maps(prefix: str, size: int, plan, uv: str, with_strip: bool, hi_body, hi_eyes, hi_fins, samples) -> dict:
    """Bake one texture set for `plan` = [(low, sources, occluders)] with the spike's paint (lib/bake.py `bake_set`)."""
    def paint(pass_name: str) -> None:
        rough = pass_name == 'rough'
        set_material(hi_body, (paint_rough_material if rough else paint_body_material)(f'{prefix}_{pass_name}_body'))
        set_material(hi_eyes, paint_eye_material(f'{prefix}_{pass_name}_eye', rough))
        set_material(hi_fins, paint_fin_material(f'{prefix}_{pass_name}_fin', rough))
    return BK.bake_set(prefix, size, OUT, plan, uv, with_strip, paint, samples, base_ao=BASE_AO)


def stage_bake(quick: bool, cine_px: int) -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'spike.blend'))
    stats = json.loads((OUT / 'stats_build.json').read_text(encoding='utf-8'))
    px = atlas_px_for(stats['areas_m2'])
    dev = use_gpu()
    C.log(f'bake device {dev}, body atlas {px}², cinematic {cine_px}²')
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new('BakeWorld')
    sc.world.light_settings.distance = 0.05
    O = bpy.data.objects
    hi_head = [O['hi_head'], O['hi_locks_head'], O['hi_tuft']]
    hi_paw = [O['hi_paw'], O['hi_locks_paw']]
    hi_eyes = [O['hi_eyeL'], O['hi_eyeR']]
    hi_fins = [O['hi_earL'], O['hi_earR']]
    hi_body = hi_head + hi_paw
    lo_head, lo_eye, lo_paw, lo_fins = O['lo_body'], O['lo_eyes'], O['lo_paw'], O['lo_fins']
    s_n, s_ao, s_e = (2, 16, 2) if quick else (6, 48, 4)

    def maps(prefix: str, size: int, plan, uv: str, with_strip: bool) -> dict:
        return bake_maps(prefix, size, plan, uv, with_strip, hi_body, hi_eyes, hi_fins, (s_n, s_ao, s_e))

    body_plan = [(lo_head, hi_head, hi_head + hi_eyes + hi_fins), (lo_eye, hi_eyes, hi_eyes + hi_head), (lo_paw, hi_paw, hi_paw),
                 (lo_fins, hi_fins, hi_fins + hi_head)]
    body = maps('atlas', px, body_plan, 'UVMap', True)
    cine_plan = [(lo_head, hi_head, hi_head + hi_eyes + hi_fins), (lo_eye, hi_eyes, hi_eyes + hi_head), (lo_fins, hi_fins, hi_fins + hi_head)]
    maps('cine', cine_px, cine_plan, 'UVCine', False)

    base_px = image_array(body['base_rgba'])
    for name, surf in (('lo_cards_head', lo_head), ('lo_cards_paw', lo_paw), ('lo_tuft', lo_head)):
        sample_vertex_colours(O[name], surf, base_px)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'spike_baked.blend'))
    out = {'device': dev, 'px': px, 'cine_px': cine_px}
    (OUT / 'stats_bake.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    return out


# ----------------------------------------------------------------------------- export stage


def stage_export() -> dict:
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'spike_baked.blend'))
    O = bpy.data.objects
    head, eyes, paw, fins = O['lo_body'], O['lo_eyes'], O['lo_paw'], O['lo_fins']
    cards = [O['lo_cards_head'], O['lo_cards_paw']]
    tuft = O['lo_tuft']
    for c in cards:
        coat_normals(c, 0.15)
    coat_normals(tuft, 0.4)
    for name, obs in (('body', [head, paw]), ('eye', [eyes]), ('fin', [fins]), ('card', cards), ('lock', [tuft])):
        m, nb = new_mat(f'spike_{name}')
        nb.output(nb.new('ShaderNodeBsdfPrincipled').outputs[0])
        for ob in obs:
            ob.data.materials.clear()
            ob.data.materials.append(m)
    from lib import export as EX
    opts_before = dict(EX.EXPORT_OPTIONS)
    EX.EXPORT_OPTIONS.update(export_tangents=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False,
                             export_animations=False, export_skins=False, export_materials='EXPORT')
    objs = [head, eyes, paw, fins, tuft] + cards
    try:
        glb = EX.export_glb(OUT / 'spike.glb', objs)
    finally:
        EX.EXPORT_OPTIONS.clear()
        EX.EXPORT_OPTIONS.update(opts_before)
    stats = {o.name: M.tri_count(o) for o in objs}
    stats['glb_bytes'] = glb.stat().st_size
    (OUT / 'stats_export.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    C.log(json.dumps(stats))
    return stats


# ----------------------------------------------------------------------------- the performance stand-in (not the rebuild)
def torso_parts() -> list[Part]:
    """A grey-box Puddlepup body for the Performance check: P1's torso and tail proportions, joined to the spike's neck."""
    return [
        Part('body', 'sphere', loc=(0.0, 0.05, 0.42), radius=0.27, scale=(1.0, 1.38, 0.92)),
        Part('chest', 'sphere', loc=(0.0, -0.15, 0.45), radius=0.23, scale=(1.05, 1.0, 1.0)),
        Part('belly', 'sphere', loc=(0.0, 0.05, 0.35), radius=0.21, scale=(1.08, 1.25, 0.8)),
        Part('rump', 'sphere', loc=(0.0, 0.26, 0.4), radius=0.2, scale=(1.0, 1.0, 0.95)),
        Part('neckbase', 'capsule', loc=(0.0, -0.22, 0.5), to=(0.0, -0.3, 0.6), radius=0.15),
        Part('tailroot', 'capsule', loc=(0.0, 0.3, 0.4), to=(0.0, 0.48, 0.38), radius=0.07),
        Part('tail', 'paddle', loc=(0.0, 0.62, 0.37), radius=0.2, scale=(0.85, 1.0, 0.36), taper=0.5, rot=_orient(Vector((0, 1, -0.12)), Vector((1, 0, 0)))),
    ]


def torso_lock_params(p, n):
    k = len(p)
    under = p[:, 2] < 0.24
    L = np.where(under, 0.045, 0.07)
    W = np.where(under, 0.02, 0.026)
    lift = np.full(k, math.radians(2.5))
    skip = (p[:, 1] < -0.3) & (p[:, 2] > 0.55)              # under the head
    return np.where(skip, np.nan, W * 0.42), L, W, lift, None


def torso_card_params(p, n, layer: int):
    k = len(p)
    L = np.full(k, 0.07 if layer == 0 else 0.08)
    W = np.full(k, 0.05)
    lift = np.full(k, math.radians(9 if layer == 0 else 14))
    sp = np.full(k, 0.024 if layer == 0 else 0.042)
    skip = ((p[:, 1] < -0.3) & (p[:, 2] > 0.55)) | (p[:, 2] < 0.16)
    if layer == 1:
        skip = skip | ((p[:, 2] < 0.5) & (p[:, 2] > 0.25))   # the second layer on the back ridge and the belly fringe only
    return np.where(skip, np.nan, sp), L, W, lift, None


def torso_flow(p, n, zones=None) -> np.ndarray:
    side = np.clip(np.abs(n[:, 0]), 0, 1)[:, None]
    g = norm(v3((0.0, 1.0, 0.0)) * (1 - side) + v3((0.0, 0.4, -1.0)) * side)
    return norm(g - n * (g * n).sum(axis=1, keepdims=True))


def stage_standin(quick: bool) -> dict:
    """Build, bake and export the stand-in torso and tail into standin.glb with its own 2048² atlas (strip included)."""
    C.clear_scene()
    voxel = 0.006 if quick else 0.004
    hi = build_body('hi_torso', torso_parts(), voxel, 4)
    co, vn = mesh_arrays(hi)
    base_attrs(hi, co)
    lo = build_body('lo_torso', torso_parts(), 0.007, 4)
    decimate_to(lo, 14000)
    tpl_hi = lock_template(9, 9, 4, strand=0.2, closed=False)
    lie, _ = scatter_layer('hi_locks_torso', hi, torso_lock_params, torso_flow, 51, tpl_hi, quick, LYING['thickness'], LYING['bury'], 1.0)
    cards = []
    for layer in (0, 1):
        ob, _ = scatter_layer(f'lo_cards_torso_{layer}', hi, lambda p, n, layer=layer: torso_card_params(p, n, layer), torso_flow, 61 + layer,
                              card_template(), quick, 0.0, 0.02, 3.0, jitter_deg=14.0)
        cards.append(ob)
    joined = M.join_meshes(cards, 'lo_cards_torso')
    for name in ('root', 'rootn', 'across', 'tpos', 'lrand', 'kind'):
        add_attr(joined, name, np.concatenate([attr_array(o, name) for o in cards]))
    for o in cards:
        bpy.data.objects.remove(o, do_unlink=True)
    lo.data.uv_layers.new(name='UVMap')
    pack_atlas([lo], 'UVMap', STRIP)
    strip_uvs(joined, CARD_CELLS)
    dev = use_gpu()
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new('BakeWorld')
    sc.world.light_settings.distance = 0.05
    samples = (2, 16, 2) if quick else (4, 32, 4)
    imgs = bake_maps('standin', 2048, [(lo, [hi, lie], [hi, lie])], 'UVMap', True, [hi, lie], [], [], samples)
    sample_vertex_colours(joined, lo, image_array(imgs['base_rgba']))
    coat_normals(joined, 0.15)
    for name, obs in (('body', [lo]), ('card', [joined])):
        m, nb = new_mat(f'standin_{name}')
        nb.output(nb.new('ShaderNodeBsdfPrincipled').outputs[0])
        for ob in obs:
            ob.data.materials.clear()
            ob.data.materials.append(m)
    from lib import export as EX
    opts_before = dict(EX.EXPORT_OPTIONS)
    EX.EXPORT_OPTIONS.update(export_tangents=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False,
                             export_animations=False, export_skins=False, export_materials='EXPORT')
    try:
        glb = EX.export_glb(OUT / 'standin.glb', [lo, joined])
    finally:
        EX.EXPORT_OPTIONS.clear()
        EX.EXPORT_OPTIONS.update(opts_before)
    stats = {'device': dev, 'torso_tris': M.tri_count(lo), 'card_tris': M.tri_count(joined),
             'cards': len(joined.data.vertices) // len(card_template()[0]), 'glb_bytes': glb.stat().st_size}
    (OUT / 'stats_standin.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    C.log(json.dumps(stats))
    return stats


# ----------------------------------------------------------------------------- render stage (Blender stills for iteration)
def principled_from(paint: bpy.types.Material, name: str, sheen: float, coat: float, rough: float, translucent: float = 0.0):
    m = paint.copy()
    m.name = name
    nt = m.node_tree
    em = next(n for n in nt.nodes if n.type == 'EMISSION')
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    src = em.inputs['Color'].links[0].from_socket
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(src, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Sheen Weight'].default_value = sheen
    bsdf.inputs['Sheen Roughness'].default_value = 0.45
    bsdf.inputs['Coat Weight'].default_value = coat
    bsdf.inputs['Coat Roughness'].default_value = 0.12
    shader = bsdf.outputs[0]
    if translucent > 0:
        tr = nt.nodes.new('ShaderNodeBsdfTranslucent')
        nt.links.new(src, tr.inputs['Color'])
        mix = nt.nodes.new('ShaderNodeMixShader')
        mix.inputs[0].default_value = translucent
        nt.links.new(bsdf.outputs[0], mix.inputs[1])
        nt.links.new(tr.outputs[0], mix.inputs[2])
        shader = mix.outputs[0]
    nt.links.new(shader, out.inputs['Surface'])
    nt.nodes.remove(em)
    return m


def setup_review_scene(res=(900, 900)):
    """The pictures' studio: bright and soft, a big key from the upper left, a gentle fill, a warm rim, grey backdrop."""
    from lib import render as RN
    sc = RN.setup_eevee(res, 48, transparent=False)
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    w = sc.world
    wt = w.node_tree
    wt.nodes.clear()
    wb = NB(wt)
    lp = wb.new('ShaderNodeLightPath')
    lit = wb.new('ShaderNodeBackground')
    lit.inputs['Color'].default_value = (0.82, 0.84, 0.88, 1)
    lit.inputs['Strength'].default_value = 0.85
    cam_bg = wb.new('ShaderNodeBackground')
    cam_bg.inputs['Color'].default_value = (0.24, 0.245, 0.255, 1)
    cam_bg.inputs['Strength'].default_value = 1.0
    mx = wb.new('ShaderNodeMixShader')
    wb.link(lp.outputs['Is Camera Ray'], mx.inputs[0])
    wb.link(lit.outputs[0], mx.inputs[1])
    wb.link(cam_bg.outputs[0], mx.inputs[2])
    wo = wb.new('ShaderNodeOutputWorld')
    wb.link(mx.outputs[0], wo.inputs['Surface'])
    for name, (az, el), energy, color, angle in (('Key', (-45, 42), 3.0, (1.0, 0.97, 0.93), 28), ('Fill', (55, 12), 0.7, (0.9, 0.94, 1.0), 40),
                                                 ('Rim', (155, 28), 3.6, (1.0, 0.85, 0.66), 12)):
        ld = bpy.data.lights.new(name, 'SUN')
        ld.energy = energy
        ld.color = color
        ld.angle = math.radians(angle)
        lo = bpy.data.objects.new(name, ld)
        C.link_obj(lo)
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        lo.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    C.link_obj(cam)
    sc.camera = cam
    return sc, cam


VIEWS = {   # name: (target, azimuth, elevation, framing size m)
    'head_34': ((0.0, -0.42, 0.76), 26, 12, 0.98),
    'head_front': ((0.0, -0.42, 0.76), 0, 4, 0.98),
    'head_side': ((0.0, -0.42, 0.76), 90, 4, 0.98),
    'paw_34': ((PAW.x, PAW.y - 0.07, 0.1), 30, 16, 0.42),
}


def aim(cam, target, az, el, size):
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    dist = size * 2.4
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    cam.data.sensor_width = 36
    cam.data.lens = 36 * dist / size


def stage_render(which: str, views: list[str]) -> None:
    src = 'spike_baked.blend' if (which == 'game' and (OUT / 'spike_baked.blend').exists()) else 'spike.blend'
    bpy.ops.wm.open_mainfile(filepath=str(OUT / src))
    sc, cam = setup_review_scene()
    O = bpy.data.objects
    shown: list[bpy.types.Object] = []
    for o in O:
        if o.type == 'MESH':
            o.hide_render = True
    if which == 'source':
        body = principled_from(paint_body_material('pb'), 'rev_body', 0.5, 0.1, 0.5)
        eye = principled_from(paint_eye_material('pe'), 'rev_eye', 0.0, 1.0, 0.05)
        fin = principled_from(paint_fin_material('pf'), 'rev_fin', 0.0, 0.4, 0.3, translucent=0.35)
        card = preview_card_material('rev_card')
        tuft = principled_from(paint_body_material('pt'), 'rev_tuft', 0.4, 0.15, 0.45)
        for n, mat in (('hi_head', body), ('hi_paw', body), ('hi_locks_head', body), ('hi_locks_paw', body), ('hi_eyeL', eye),
                       ('hi_eyeR', eye), ('hi_earL', fin), ('hi_earR', fin), ('lo_cards_head', card), ('lo_cards_paw', card),
                       ('hi_tuft', tuft)):
            if n in O:
                shown.append(O[n])
                set_material([O[n]], mat)
    else:
        imgs = {k: bpy.data.images.load(str(OUT / f'atlas_{k}.png')) for k in ('base', 'normal', 'orm')}
        cine = {k: bpy.data.images.load(str(OUT / f'cine_{k}.png')) for k in ('base', 'normal', 'orm')}
        for d in (imgs, cine):
            for k in ('normal', 'orm'):
                d[k].colorspace_settings.name = 'Non-Color'
        for n in ('lo_body', 'lo_eyes', 'lo_paw', 'lo_fins', 'lo_cards_head', 'lo_cards_paw', 'lo_tuft'):
            o = O[n]
            shown.append(o)
            use_cine = n in ('lo_body', 'lo_eyes', 'lo_fins')
            src_imgs = cine if use_cine else imgs
            m, nb = new_mat(f'game_{n}')
            uvn = nb.new('ShaderNodeUVMap')
            uvn.uv_map = 'UVCine' if use_cine else 'UVMap'
            tb = nb.new('ShaderNodeTexImage', image=src_imgs['base'])
            tn = nb.new('ShaderNodeTexImage', image=src_imgs['normal'])
            to = nb.new('ShaderNodeTexImage', image=src_imgs['orm'])
            for t in (tb, tn, to):
                nb.link(uvn.outputs['UV'], t.inputs['Vector'])
            nm = nb.new('ShaderNodeNormalMap')
            nm.uv_map = uvn.uv_map
            nm.inputs['Strength'].default_value = 0.7
            nb.link(tn.outputs['Color'], nm.inputs['Color'])
            bsdf = nb.new('ShaderNodeBsdfPrincipled')
            base = tb.outputs['Color']
            if n.startswith('lo_cards') or n == 'lo_tuft':
                vc = nb.new('ShaderNodeVertexColor')
                vc.layer_name = 'Col'
                base = nb.mix(1.0, base, vc.outputs['Color'], blend='MULTIPLY')
            r, g, b = nb.sep_rgb(to.outputs['Color'])
            nb.link(nb.mix(r, nb.rgb((0, 0, 0)), base), bsdf.inputs['Base Color'])
            nb.link(g, bsdf.inputs['Roughness'])
            nb.link(b, bsdf.inputs['Coat Weight'])
            bsdf.inputs['Coat Roughness'].default_value = 0.12
            bsdf.inputs['Sheen Weight'].default_value = 0.0 if n == 'lo_fins' else 0.5
            nb.link(nm.outputs['Normal'], bsdf.inputs['Normal'])
            if n.startswith('lo_cards'):
                nb.link(tb.outputs['Alpha'], bsdf.inputs['Alpha'])
                m.surface_render_method = 'DITHERED'
            nb.output(bsdf.outputs[0])
            if n not in ('lo_body', 'lo_paw'):
                m.use_backface_culling = False
            set_material([o], m)
    for v in views:
        target, az, el, size = VIEWS[v]
        part = 'paw' if v.startswith('paw') else 'head'
        for o in shown:
            o.hide_render = ('paw' in o.name) != (part == 'paw')
        aim(cam, target, az, el, size)
        sc.render.filepath = str(OUT / 'renders' / f'{which}_{v}.png')
        bpy.ops.render.render(write_still=True)
        C.log(f'rendered {which}_{v}')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--stages', default='build,bake,export,render')
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--cine', type=int, default=2048, help='the cinematic head set size')
    ap.add_argument('--views', default='head_34,head_front,head_side,paw_34')
    ap.add_argument('--which', default='source,game')
    args = ap.parse_args(C.script_args())
    C.ensure_dir(OUT)
    C.open_log(OUT / 'spike.log')
    t0 = time.time()
    stages = args.stages.split(',')
    if 'build' in stages:
        stage_build(args.quick)
    if 'bake' in stages:
        stage_bake(args.quick, args.cine)
    if 'export' in stages:
        stage_export()
    if 'standin' in stages:
        stage_standin(args.quick)
    if 'render' in stages:
        for w in args.which.split(','):
            stage_render(w, args.views.split(','))
    C.log(f'spike done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
