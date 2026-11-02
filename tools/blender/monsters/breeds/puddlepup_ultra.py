"""Puddlepup at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9, P1.1): the recipe for `tools/blender/monsters/build_ultra.py`.

The approved spike head (tools/blender/spikes/detail_spike.py, round 5) with the round 6 fixes (ART_2_DETAIL §8.5):
  - one smooth, short cream muzzle and a single soft smile line; the teal comes down in a V between the eyes;
  - an upper lash line under a fur lid instead of a full dark ring round each eye;
  - coral ribbed fins, narrower at the root, hanging to the jaw and angled slightly forward;
  - no stray cards at the ear roots and cheeks; a smaller teal tuft;
  - the chest ruff and the belly cream, as in the pictures;
plus the body, the four legs and paws and the fluked tail from 2-turnaround.png, in the same fur pipeline.

Metres; the monster faces −Y, Z is up, +X is its left. Palette: CONTENT §2.2 #1 (#3FB6A8 / #F3E6C4 / #F28FA8 / #24323A);
Songheart Puddlepup: CONTENT §12 (#5FC7B0 / #FFF4D6 / #FF6FB5, rainbow fins).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from lib import common as C
from lib import surface as S
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3

ID = 'puddlepup'
LOOK = 'puddlepup-ultra'           # tools/blender/out/<LOOK>/
PLAN = 'quadruped'
HEIGHT_UNITS = 150

PALETTE = {'body': '#3FB6A8', 'belly': '#F3E6C4', 'accent': '#F28FA8', 'eye': '#24323A'}
VARIANTS = {'songheart-puddlepup': {'body': '#5FC7B0', 'belly': '#FFF4D6', 'accent': '#FF6FB5', 'eye': '#24323A', 'rainbow': True}}
VARIANT_ID = 'songheart-puddlepup'
RAINBOW = ['#FF6F6F', '#FFB36B', '#FFE96B', '#7BE495', '#6FB8FF', '#C28BFF']

NOSE_HEX = '#16171B'
MOUTH_HEX = '#4A2E35'


def colours(pal: dict) -> dict:
    """Every derived colour of a palette (the base or a variant)."""
    teal, cream, pink = pal['body'], pal['belly'], pal['accent']
    return {
        'teal': teal, 'cream': cream, 'pink': pink,
        # the pictures' dapples are crisp and clearly darker than the coat
        'dapple': C.mix_hex(C.shade_hex(teal, 0.62, cool=0.03), '#127F77', 0.45),
        'brow': C.mix_hex(pal['eye'], teal, 0.3),
        # round 6: coral fins, not bubblegum pink, with darker shaded ribs
        'coral': C.mix_hex(pink, '#FF8C69', 0.4),
        'blush': C.mix_hex('#F5919F', pink, 0.3),
        'tuft': C.shade_hex(teal, 0.86),
    }


# ----------------------------------------------------------------------------- the head (the approved spike, round 6)
HEAD_C = Vector((0.0, -0.37, 0.77))
HEAD_R = (0.214, 0.182, 0.215)
EYE_C = {s: Vector((0.125 * s, -0.522, 0.755)) for s in (1, -1)}
EYE_R = 0.061
EYE_DEPTH = (0.44, 0.30)
EYE_SPREAD = 1.1
NOSE_C = Vector((0.0, -0.598, 0.712))
# round 6: one smooth short muzzle (round 5's two pads and a chin read as three lobes)
MUZZLE = ((0.0, -0.554, 0.666), (0.096, 0.056, 0.064))
EAR_ROOT = {s: Vector((0.146 * s, -0.37, 0.93)) for s in (1, -1)}
CHEEK = (0.11, -0.455, 0.68, 0.088)
EAR_GAP = 0.028


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye (+Z of its dome looks out, a little forward of the head's normal)."""
    c = EYE_C[s]
    surf_n = Vector(((c.x - HEAD_C.x) / HEAD_R[0] ** 2, (c.y - HEAD_C.y) / HEAD_R[1] ** 2, (c.z - HEAD_C.z) / HEAD_R[2] ** 2)).normalized()
    look = (surf_n * 0.68 + Vector((0, -1, 0)) * 0.32).normalized()
    look = (look + Vector((0, 0, 0.05))).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


def blink_pivot(s: int) -> tuple[Vector, Vector]:
    """Where an eye's blink bone sits (the lash line, just under the fur lid) and the eye's up axis."""
    c, _xax, yax, look = eye_frame(s)
    return c + yax * (EYE_R * 0.8) + look * (EYE_R * 0.05), yax


# ----------------------------------------------------------------------------- ears (round 6: coral, narrow root, to the jaw)
N_RIBS = 6
EAR_THETA = (math.radians(38), math.radians(0))          # outer edge (v=0) → inner edge (v=1), from straight down
EAR_LEN = (0.37, 0.39)                                    # P1.1 review 1: about a head-height, just below the jaw


def ear_frame(s: int):
    R = EAR_ROOT[s]
    npk = Vector((0.62 * s, -0.78, 0.1)).normalized()
    down = Vector((0, 0, -1))
    e2 = (down - npk * down.dot(npk)).normalized()
    e1 = Vector((s, 0, 0))
    e1 = (e1 - npk * e1.dot(npk) - e2 * e1.dot(e2)).normalized()
    return R, npk, e2, e1


def head_side_x(y: float, z: float) -> float:
    q = 1.0 - ((y - HEAD_C.y) / HEAD_R[1]) ** 2 - ((z - HEAD_C.z) / HEAD_R[2]) ** 2
    x = HEAD_R[0] * math.sqrt(q) if q > 0 else 0.0
    cx, cy, cz, cr = CHEEK
    q = 1.0 - ((y - cy) / (cr * 0.95)) ** 2 - ((z - cz) / (cr * 0.9)) ** 2
    return max(x, cx + cr * math.sqrt(q)) if q > 0 else x


def ear_point(s: int, u: float, v: float, rib_relief: float = 0.0) -> Vector:
    """u 0..1 from the root to the scalloped far edge, v 0..1 outer → inner."""
    R, npk, e2, e1 = ear_frame(s)
    # round 6: narrower at the root, the fan opens over the first 60%
    mid = 0.5 * (EAR_THETA[0] + EAR_THETA[1])
    spread = 0.42 + 0.58 * C.smoothstep(0.0, 0.6, u)
    th = mid + (EAR_THETA[0] + (EAR_THETA[1] - EAR_THETA[0]) * v - mid) * spread
    L = EAR_LEN[0] + (EAR_LEN[1] - EAR_LEN[0]) * v
    d = e2 * math.cos(th) + e1 * math.sin(th)
    p = R + d * (u * L)
    p += npk * (0.04 * u * u)
    p += Vector((0, -0.05 * u * u, -0.025 * u * u))       # round 6: angled slightly forward
    p += npk * rib_relief
    m = head_side_x(p.y, p.z) + EAR_GAP * C.smoothstep(0.0, 0.25, u)
    ax = abs(p.x)
    p.x = s * 0.5 * (ax + m + math.sqrt((ax - m) ** 2 + 0.02 ** 2))
    return p


def scallop(v: float, ribs: int = N_RIBS, depth: float = 0.026) -> float:
    return 1.0 - depth * (0.5 - 0.5 * math.cos(2 * math.pi * ribs * v))


def rib_mask(v: float, ribs: int = N_RIBS, width: float = 0.11) -> float:
    k = (v * ribs) % 1.0
    d = min(k, 1.0 - k)
    return math.exp(-(d / width) ** 2)


# ----------------------------------------------------------------------------- the tail: a furry teal paddle with a coral fluke
TAIL_BASE = Vector((0.0, 0.31, 0.36))
TAIL_DIR = Vector((0.0, 1.0, 0.5)).normalized()
TAIL_UP = Vector((0.0, -TAIL_DIR.z, TAIL_DIR.y))         # up in the tail's own (sagittal) plane
TAIL_LEN = 0.5
PADDLE_C = TAIL_BASE + TAIL_DIR * 0.3
PADDLE_R = (0.056, 0.19, 0.115)                           # half thickness (x), half length (along the tail), half height
FAN_C = PADDLE_C - TAIL_DIR * 0.01
FAN_PHI = (math.radians(-100), math.radians(100))       # from straight back (along the tail), + = up
N_TAIL_RIBS = 11


def fan_radius(phi: float) -> float:
    return 0.25 + 0.06 * math.cos(phi)


def tail_fan_point(u: float, v: float, relief: float = 0.0) -> Vector:
    """u 0..1 from inside the paddle to the scalloped edge, v 0..1 bottom → top."""
    phi = FAN_PHI[0] + (FAN_PHI[1] - FAN_PHI[0]) * v
    r0, r1 = 0.06, fan_radius(phi)
    r = r0 + (r1 - r0) * u
    d = TAIL_DIR * math.cos(phi) + TAIL_UP * math.sin(phi)
    p = FAN_C + d * r
    # a soft cup and a slight sway so it isn't a flat disc
    p += Vector((0.012 * math.sin(v * math.pi) * u * u + relief, 0.0, 0.0))
    return p


def ear_fn(s: int):
    return lambda u, v, relief=0.0: ear_point(s, u, v, relief)


def build_fan_sheet(name: str, point_fn, nu: int, nv: int, ribs: int, high: bool, flip: bool, relief_axis: Vector | None,
                    edge_depth: float = 0.026) -> bpy.types.Object:
    """A ribbed membrane sheet over (u, v); `fan` attribute = (u, v, rib)."""
    bm = bmesh.new()
    uv_l = bm.loops.layers.uv.new('UVMap')
    rows, params = [], []
    for j in range(nu + 1):
        u = j / nu
        row = []
        for i in range(nv + 1):
            v = i / nv
            uu = u * scallop(v, ribs, edge_depth)
            params.append((uu, v))
            relief = 0.0
            if high:
                relief = 0.0028 * rib_mask(v, ribs) * (1.0 - 0.5 * u) * float(smooth(0.04, 0.2, u))
                relief += 0.0004 * math.sin(u * 90.0) * (1.0 - rib_mask(v, ribs))
            if relief_axis is None:
                p = point_fn(uu, v, relief)
            else:
                p = point_fn(uu, v) + relief_axis * relief
            row.append(bm.verts.new(p))
        rows.append(row)
    for j in range(nu):
        for i in range(nv):
            corners = [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]
            if flip:
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
    rib = np.array([rib_mask(x, ribs) for x in vv])
    S.add_attr(ob, 'fan', np.stack([uu, vv, rib], axis=1))
    return ob


def build_fins(high: bool, quick: bool) -> list[bpy.types.Object]:
    """Both ear membranes and the tail fluke. `fin_part` attribute: 1 left ear, -1 right ear, 2 tail."""
    out = []
    for s in (1, -1):
        nu, nv = ((90, 120) if not quick else (40, 48)) if high else (16, 48)
        ob = build_fan_sheet(f'{"hi" if high else "lo"}_ear{"L" if s > 0 else "R"}', ear_fn(s), nu, nv, N_RIBS, high, s < 0, None)
        S.add_attr(ob, 'fin_part', np.full(len(ob.data.vertices), float(s)))
        out.append(ob)
    nu, nv = ((80, 180) if not quick else (32, 72)) if high else (12, 66)
    ob = build_fan_sheet(f'{"hi" if high else "lo"}_tailfan', tail_fan_point, nu, nv, N_TAIL_RIBS, high, False, Vector((1, 0, 0)), 0.03)
    S.add_attr(ob, 'fin_part', np.full(len(ob.data.vertices), 2.0))
    out.append(ob)
    return out


# ----------------------------------------------------------------------------- body parts
def _orient(long_axis: Vector, width_axis: Vector) -> tuple[float, float, float]:
    d = long_axis.normalized()
    w = (width_axis - d * width_axis.dot(d)).normalized()
    n = w.cross(d).normalized()
    m = Matrix((w, d, n)).transposed()
    e = m.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def head_parts() -> list[Part]:
    ps = [
        Part('head', 'sphere', loc=tuple(HEAD_C), radius=1.0, scale=HEAD_R),
        Part('forehead', 'sphere', loc=(0.0, -0.42, 0.85), radius=0.13, scale=(1.3, 0.85, 0.85)),
        Part('cheek', 'sphere', loc=CHEEK[:3], radius=CHEEK[3], scale=(1.0, 0.95, 0.9), mirror=True),
        # round 6: one smooth short muzzle (no left and right pads), a soft chin tucked under it
        Part('muzzle', 'sphere', loc=MUZZLE[0], radius=1.0, scale=(0.092, 0.045, 0.056)),
        Part('chin', 'sphere', loc=(0.0, -0.54, 0.634), radius=0.036, scale=(1.35, 0.95, 0.62)),
        Part('nose', 'sphere', loc=tuple(NOSE_C), radius=0.042, scale=(1.3, 0.7, 0.68)),
        Part('neck', 'capsule', loc=(0.0, -0.34, 0.66), to=(0.0, -0.29, 0.52), radius=0.13),
    ]
    for s in (1, -1):
        R, npk, e2, e1 = ear_frame(s)
        tag = 'L' if s > 0 else 'R'
        cap = ear_point(s, 0.36, 0.5)
        long = (cap - R).normalized()
        ps.append(Part(f'earcap{tag}', 'fin', loc=tuple(cap - long * 0.025), radius=0.13,
                       scale=(0.62, 1.0, 0.2), taper=0.3, rot=_orient(-long, e1)))
        band = ear_point(s, 0.56, 0.1)
        longb = (band - R).normalized()
        ps.append(Part(f'earband{tag}', 'fin', loc=tuple(band), radius=0.19,
                       scale=(0.3, 1.0, 0.11), taper=0.5, rot=_orient(-longb, e1)))
        ps.append(Part(f'earroot{tag}', 'sphere', loc=tuple(R + Vector((0.006 * s, 0.0, -0.05))), radius=0.056))
        # P1.1 review 1: no lid ridge (it read as heavy, sad brows); the lash line is painted on the eye
    return ps


LEGS = {'FL': (0.17, -0.30), 'FR': (-0.17, -0.30), 'BL': (0.17, 0.21), 'BR': (-0.17, 0.21)}
PAW_K = 0.92
TOE_DX = (-0.076, 0.0, 0.076)
CAP_SCALE = (0.92, 0.85, 0.95)


def cap_centres(leg: str) -> list[Vector]:
    x, y = LEGS[leg]
    k = PAW_K
    return [Vector((x + dx * 1.05 * k, y + (-0.17 + abs(dx) * 0.3) * k, 0.04 * k)) for dx in TOE_DX]


def cap_radii() -> tuple[float, float, float]:
    return tuple(0.041 * PAW_K * s for s in CAP_SCALE)


def pad_centre(leg: str) -> tuple[Vector, tuple[float, float, float]]:
    x, y = LEGS[leg]
    k = PAW_K
    return Vector((x, y - 0.04 * k, 0.011 * k)), (0.06 * k, 0.048 * k, 0.02)


def paw_parts(leg: str) -> list[Part]:
    x, y = LEGS[leg]
    k = PAW_K
    top = 0.40 if leg[0] == 'F' else 0.34
    ps = [
        Part(f'leg{leg}', 'capsule', loc=(x, y + 0.02 * k, top), to=(x, y - 0.005 * k, 0.11), radius=0.072),
        Part(f'foot{leg}', 'sphere', loc=(x, y - 0.05 * k, 0.06 * k), radius=0.1 * k, scale=(1.06, 1.08, 0.8)),
        Part(f'web{leg}', 'sphere', loc=(x, y - 0.12 * k, 0.03 * k), radius=0.055 * k, scale=(1.35, 0.6, 0.38)),
        Part(f'pad{leg}', 'sphere', loc=(x, y - 0.04 * k, 0.011 * k), radius=0.05 * k, scale=(1.2, 0.95, 0.3)),
    ]
    for i, dx in enumerate(TOE_DX):
        ps.append(Part(f'toe{leg}{i}', 'sphere', loc=(x + dx * 1.02 * k, y + (-0.128 + abs(dx) * 0.3) * k, 0.043 * k), radius=0.044 * k,
                       scale=(0.95, 1.3, 0.9)))
        ps.append(Part(f'cap{leg}{i}', 'sphere', loc=tuple(cap_centres(leg)[i]), radius=0.041 * k, scale=CAP_SCALE))
    return ps


def torso_parts() -> list[Part]:
    ps = [
        Part('chest', 'sphere', loc=(0.0, -0.27, 0.4), radius=0.22, scale=(1.1, 1.05, 1.08)),
        Part('body', 'capsule', loc=(0.0, -0.16, 0.355), to=(0.0, 0.21, 0.345), radius=0.235),
        Part('belly', 'sphere', loc=(0.0, -0.02, 0.27), radius=0.19, scale=(1.12, 1.4, 0.78)),
        Part('neckbase', 'capsule', loc=(0.0, -0.27, 0.5), to=(0.0, -0.32, 0.6), radius=0.14),
        Part('shoulder', 'sphere', loc=(0.15, -0.28, 0.35), radius=0.11, scale=(0.9, 1.0, 1.1), mirror=True),
        Part('haunch', 'sphere', loc=(0.16, 0.19, 0.29), radius=0.135, scale=(0.85, 1.1, 1.1), mirror=True),
        Part('tailroot', 'tube', loc=tuple(TAIL_BASE - TAIL_DIR * 0.04), to=tuple(PADDLE_C - TAIL_DIR * 0.08), radius=0.085, r2=0.062),
        Part('tail', 'paddle', loc=tuple(PADDLE_C), radius=PADDLE_R[1], scale=(PADDLE_R[2] / PADDLE_R[1], 1.0, PADDLE_R[0] / PADDLE_R[1]),
             taper=0.5, rot=_orient(TAIL_DIR, Vector((0, 0, 1)))),
    ]
    for leg in LEGS:
        ps.extend(paw_parts(leg))
    return ps


def all_parts() -> list[Part]:
    return head_parts() + torso_parts()


# ----------------------------------------------------------------------------- carving (the high source only)
def mouth_curve() -> list[tuple[float, float]]:
    """Round 6: one soft smile line under the nose, its ends curling up (no philtrum, no second curve)."""
    mid = NOSE_C.z - 0.042
    pts = []
    for k in range(-14, 15):
        t = k / 14
        x = 0.043 * t
        z = mid + 0.011 * t * t + 0.006 * max(0.0, abs(t) - 0.75) / 0.25
        pts.append((x, z))
    return pts


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    front = smooth(-0.5, -0.57, y)
    md = S.polyline_dist(x, z, mouth_curve())
    groove = np.exp(-(md / 0.0022) ** 2) * front * (z < NOSE_C.z - 0.025) * (z > 0.6)
    nos = np.zeros_like(x)
    for s in (1, -1):
        dd = np.sqrt(((x - 0.014 * s) / 1.4) ** 2 + (z - (NOSE_C.z - 0.012)) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.0058) ** 2))
    nos *= smooth(NOSE_C.y + 0.018, NOSE_C.y + 0.008, y)
    lip = np.zeros(len(co))
    peb = np.zeros(len(co))
    cr = v3(cap_radii())
    for leg in LEGS:
        for c in cap_centres(leg):
            d = np.linalg.norm((co - v3(c)) / cr, axis=1)
            lip = np.maximum(lip, np.exp(-((d - 1.0) / 0.07) ** 2))
    near_paw = np.zeros(len(co), bool)
    for leg, (lx, ly) in LEGS.items():
        near_paw |= (np.hypot(x - lx, y - ly) < 0.16) & (z < 0.03)
    peb = np.sin(x * 700.0) * np.sin(y * 650.0) * near_paw
    disp = -0.0022 * groove - 0.005 * nos - 0.0014 * lip + 0.0002 * peb
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': groove})


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    # only the front half shows (the rest sits inside the head): drop the back cap to save triangles
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * 0.96 * EYE_SPREAD, v.co.y * EYE_R * 1.08 * EYE_SPREAD, v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    # the eye's own frame as attributes: the paint reads them after the transform is applied
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((EYE_R * 0.96, EYE_R * 1.08, EYE_R * EYE_DEPTH[0])))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def apply_transform(ob: bpy.types.Object) -> None:
    ob.data.transform(ob.matrix_world)
    ob.matrix_world = Matrix.Identity(4)


# ----------------------------------------------------------------------------- zones: where the coat goes and what it is
def ear_zone(p: np.ndarray):
    x = p[:, 0]
    ear = np.zeros(len(p), bool)
    ear_u = np.zeros(len(p))
    for s in (1, -1):
        R = v3(EAR_ROOT[s])
        rel = p - R
        mid = norm(v3(ear_point(s, 1.0, 0.5) - EAR_ROOT[s]))
        along = rel @ mid
        on = (np.sign(x) == s) & (along > 0.035) & (np.abs(x) > 0.16) & (p[:, 2] > 0.5) & (p[:, 1] < -0.2)
        ear |= on
        ear_u = np.where(on, along / EAR_LEN[1], ear_u)
    return ear, ear_u


def leg_masks(p: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    out = {}
    for leg, (lx, ly) in LEGS.items():
        top = 0.30 if leg[0] == 'F' else 0.22
        r = np.hypot(x - lx, (y - ly + 0.03) * 0.85)
        out[leg] = (r < 0.15) & (z < top + 0.02 * np.sign(x * lx))
    return out


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    if n is None:
        n = np.tile(v3((0, 0, 1)), (len(p), 1))
    ear, ear_u = ear_zone(p)
    head = ((in_ellipsoid(p, (0.0, -0.40, 0.79), (0.36, 0.27, 0.30)) < 1.0) & (z > 0.56)) | ear
    muzzle = in_ellipsoid(p, *MUZZLE) < 1.0
    nose = np.linalg.norm(p - v3(NOSE_C), axis=1) < 0.06
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = head & (y < -0.45) & (z > 0.6) & (z < 0.9) & (ax < 0.19) & ~ear
    crown = head & (z > 0.9) & ~ear
    tuft = (ax < 0.05) & (z > 0.97) & (y > -0.44) & (y < -0.34)
    cheek = head & (ax > 0.12) & (z < 0.74) & (y < -0.36) & ~ear & ~muzzle
    mirrored = p.copy()
    mirrored[:, 0] = ax
    blush = in_ellipsoid(mirrored, (0.15, -0.5, 0.69), (0.06, 0.08, 0.05)) < 1.0
    chin = head & (z < 0.64) & (y < -0.44)
    ear_root = np.minimum(np.linalg.norm(p - v3(EAR_ROOT[1]), axis=1), np.linalg.norm(p - v3(EAR_ROOT[-1]), axis=1)) < 0.095
    legs = leg_masks(p)
    leg = np.zeros(len(p), bool)
    for m in legs.values():
        leg |= m
    leg &= ~head
    paw = leg & (z < 0.12)
    toes = np.zeros(len(p), bool)
    for lg, (lx, ly) in LEGS.items():
        toes |= legs[lg] & (y < ly - 0.07 * PAW_K) & (z < 0.095)
    sole = z < 0.03
    tail = (~head) & (~leg) & ((((p - v3(TAIL_BASE)) @ v3(TAIL_DIR)) > 0.02) & (y > 0.36) & (z > 0.2))
    rel = p - v3(PADDLE_C)
    pr = np.sqrt(((rel @ v3(TAIL_DIR)) / PADDLE_R[1]) ** 2 + ((rel @ v3(TAIL_UP)) / PADDLE_R[2]) ** 2)
    paddle = tail & (pr < 1.15) & (np.abs(x) < 0.07)
    torso = ~head & ~leg & ~tail
    # the cream bib: from under the chin down the front of the chest to between the front legs
    bib = (~head | chin) & ~tail & (y < -0.24) & (ax < 0.115 + 0.05 * smooth(0.6, 0.3, z)) & (z > 0.1) & (z < 0.66)
    bib &= ~(leg & (z < 0.2))
    # the cream underside: the line falls from the chest's side to the belly and the flanks
    zb = np.interp(y, [-0.45, -0.28, -0.05, 0.2, 0.36], [0.46, 0.3, 0.245, 0.23, 0.26])
    belly = torso & (z < zb)
    back = torso & (z > 0.42)
    return {'ear': ear, 'ear_u': ear_u, 'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face,
            'crown': crown, 'tuft': tuft, 'cheek': cheek, 'blush': blush, 'chin': chin, 'ear_root': ear_root, 'leg': leg,
            'paw': paw, 'toes': toes, 'sole': sole, 'tail': tail, 'paddle': paddle, 'paddle_r': pr, 'torso': torso,
            'bib': bib, 'belly': belly, 'back': back, 'legs': legs}


# ----------------------------------------------------------------------------- how the fur lies
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    # head: combed back from the nose, turning down below the eyes (the spike)
    g = norm(p - v3((NOSE_C.x, NOSE_C.y - 0.03, NOSE_C.z)))
    wd = smooth(0.86, 0.62, zz)[:, None]
    g_head = norm(g * (1 - wd) + v3((0, 0, -1)) * wd * 1.3)
    # between the eyes the radial comb had its centre on the face (a starburst, review 1): comb up and a little out
    face_up = norm(np.stack([x * 4.0, np.full(len(p), 0.2), np.ones(len(p))], axis=1))
    wf = (smooth(-0.44, -0.5, y) * smooth(0.71, 0.75, zz) * smooth(0.13, 0.06, np.abs(x)))[:, None]
    g_head = norm(g_head * (1 - wf) + face_up * wf)
    for s in (1, -1):
        on = z['ear'] & (np.sign(x) == s)
        g_head = np.where(on[:, None], norm(p - v3(EAR_ROOT[s]) + v3((0, 0, -0.05))), g_head)
    # torso: back toward the tail along the top, down the sides
    side = np.clip(np.abs(n[:, 0]) * 1.2, 0, 1)[:, None]
    g_torso = norm(v3((0.0, 1.0, -0.1)) * (1 - side) + v3((0.0, 0.35, -1.0)) * side)
    g = np.where(z['torso'][:, None], g_torso, g_head)
    g = np.where(z['belly'][:, None], np.tile(v3((0.0, 0.45, -0.8)), (len(p), 1)), g)
    g = np.where(z['bib'][:, None], np.tile(v3((0.0, -0.22, -1.0)), (len(p), 1)), g)
    g = np.where(z['leg'][:, None], np.tile(v3((0.0, -0.1, -1.0)), (len(p), 1)), g)
    radial = norm(np.stack([np.zeros(len(p)), y - FAN_C.y, zz - FAN_C.z], axis=1))
    g_tail = norm(np.tile(v3(TAIL_DIR), (len(p), 1)) * 0.6 + radial * smooth(0.3, 0.8, z['paddle_r'])[:, None])
    g = np.where(z['tail'][:, None], g_tail, g)
    g = np.where((z['head'] & ~z['bib'])[:, None], g_head, g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


def head_lock_params(p, n):
    """The approved spike values on the head; NaN spacing elsewhere (the body layer covers it)."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.068)
    W = np.full(k, 0.0115)
    lift = np.full(k, _rad(2.0))
    L = np.where(z['face'], 0.044, L)
    W = np.where(z['face'], 0.008, W)
    L = np.where(z['crown'], 0.072, L)
    W = np.where(z['crown'], 0.012, W)
    L = np.where(z['cheek'], 0.076, L)
    W = np.where(z['cheek'], 0.013, W)
    front_cheek = z['cheek'] & (p[:, 1] < -0.46)
    L = np.where(front_cheek, 0.05, L)
    W = np.where(front_cheek, 0.0095, W)
    L = np.where(z['blush'], 0.044, L)
    L = np.where(z['chin'], 0.07, L)
    L = np.where(z['ear'], 0.076, L)
    W = np.where(z['ear'], 0.012, W)
    near_eye = smooth(EYE_R * 1.12, EYE_R * 1.8, z['eye_d'])
    L = L * (0.5 + 0.5 * near_eye)
    W = W * (0.62 + 0.38 * near_eye)
    skip = ~z['head'] | z['bib'] | z['muzzle'] | z['nose'] | (z['eye_d'] < EYE_R * 1.1)
    return np.where(skip, np.nan, W * 0.55), L, W, lift, z


def body_lock_params(p, n):
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.074)
    W = np.full(k, 0.0135)
    lift = np.full(k, _rad(2.5))
    L = np.where(z['bib'], 0.1, L)
    W = np.where(z['bib'], 0.016, W)
    lift = np.where(z['bib'], _rad(5), lift)
    L = np.where(z['bib'] & z['chin'], 0.06, L)
    L = np.where(z['belly'], 0.082, L)
    W = np.where(z['belly'], 0.015, W)
    upper = z['leg'] & (p[:, 2] > 0.13)
    L = np.where(z['leg'], np.where(upper, 0.07, 0.042), L)
    W = np.where(z['leg'], np.where(upper, 0.0125, 0.0105), W)
    L = np.where(z['tail'], 0.052, L)
    W = np.where(z['tail'], 0.011, W)
    L = np.where(z['paddle'], 0.04, L)
    W = np.where(z['paddle'], 0.0095, W)
    skip = (z['head'] & ~z['bib']) | z['toes'] | z['sole'] | (z['paw'] & (p[:, 2] < 0.04))
    return np.where(skip, np.nan, W * 0.6), L, W, lift, z


def card_params(p, n, layer: int):
    """Soft fur cards for the outline (they fade out face-on). Layer 0 covers the coat; layer 1 adds the longer
    fringes: the back of the head, the chest ruff, the belly, the back ridge, the backs of the legs."""
    z = zones(p, n)
    k = len(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    head = z['head']
    if layer == 0:
        L = np.where(head, 0.066, 0.07)
        W = np.where(head, 0.036, 0.046)
        lift = np.full(k, _rad(6))
        lift = np.where(head, _rad(4), lift)
        L = np.where(z['cheek'], 0.05, L)                 # round 6: no stray cards at the cheeks
        L = np.where(z['chin'], 0.058, L)
        L = np.where(z['ear'], 0.042, L)
        lift = np.where(z['ear'], _rad(2), lift)
        L = np.where(z['leg'], 0.06, L)
        W = np.where(z['leg'], 0.036, W)
        L = np.where(z['tail'], 0.05, L)
        W = np.where(z['tail'], 0.032, W)
        L = np.where(z['back'], 0.06, L)
        lift = np.where(z['back'], _rad(3), lift)
        sp = np.where(head, np.where(z['ear'], 0.034, 0.022), 0.025)
        sp = np.where(z['leg'] | z['tail'], 0.024, sp)
        skip = (z['face'] | z['muzzle'] | z['nose'] | (z['eye_d'] < 0.1) | z['tuft'] | (z['chin'] & (y < -0.5)) | z['blush']
                | z['ear_root'] | (z['cheek'] & (y < -0.47)) | (z['leg'] & (zz < 0.13)) | z['sole'])
    else:
        L = np.full(k, 0.082)
        W = np.full(k, 0.042)
        lift = np.full(k, _rad(10))
        sp = np.full(k, 0.045)
        back_head = head & (y > -0.38) & (zz < 0.9) & (zz > 0.6) & ~z['ear'] & ~z['cheek']
        ridge = z['torso'] & (zz > 0.5) & (np.abs(x) < 0.1)
        bib = z['bib'] & ~z['chin'] & (zz < 0.6)
        belly = z['belly'] & (zz < 0.22)
        leg_back = np.zeros(k, bool)
        for lg, (lx, ly) in LEGS.items():
            leg_back |= z['legs'][lg] & ((y > ly) | (np.abs(x) > np.abs(lx) + 0.03)) & (zz > 0.13)
        L = np.where(bib, 0.1, L)
        W = np.where(bib, 0.048, W)
        lift = np.where(bib, _rad(6), lift)
        lift = np.where(ridge, _rad(4), lift)
        L = np.where(belly, 0.088, L)
        L = np.where(leg_back, 0.07, L)
        fringe = back_head | ridge | bib | belly | leg_back
        skip = ~fringe | z['face'] | z['muzzle'] | (z['eye_d'] < 0.12) | (z['chin'] & (y < -0.48)) | z['ear_root'] | z['tail']
    return np.where(skip, np.nan, sp), L, W, lift, z


# ----------------------------------------------------------------------------- the tuft (round 6: smaller)
def tuft_frames(surface: bpy.types.Object):
    bvh = BVHTree.FromObject(surface, bpy.context.evaluated_depsgraph_get())
    P, N, F, L, W, lift = [], [], [], [], [], []
    spots = [(0.0, -0.41, 0.0, 0.056, 26), (-0.02, -0.4, -24, 0.048, 22), (0.021, -0.4, 24, 0.048, 22),
             (-0.034, -0.388, -40, 0.042, 16), (0.035, -0.386, 38, 0.042, 16)]
    for x, y, fan, ln, lf in spots:
        hit = bvh.ray_cast(Vector((x, y, 1.4)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        p = np.array(hit[0])
        nn = np.array(hit[1])
        a = math.radians(fan)
        f = np.array([math.sin(a) + 0.4, math.cos(a) * 0.8, 0.3])
        f = f - nn * (f @ nn)
        P.append(p)
        N.append(nn)
        F.append(f / np.linalg.norm(f))
        L.append(ln)
        W.append(0.028)
        lift.append(math.radians(lf))
    P, N, F = np.array(P), np.array(N), np.array(F)
    return S.lock_frames(P, N, F, np.array(L), np.array(W), np.array(lift), np.random.default_rng(77), None, jitter_deg=4)


# ----------------------------------------------------------------------------- paint (numpy, per source vertex)
DAPPLES_HEAD = [  # (centre, radii): the round spot on the forehead, the scatter over the crown, the ear caps (the spike's)
    ((0.0, -0.545, 0.885), (0.03, 0.04, 0.03)),
    ((0.058, -0.53, 0.915), (0.022, 0.035, 0.02)), ((-0.06, -0.53, 0.912), (0.021, 0.035, 0.02)),
    ((0.03, -0.47, 0.965), (0.024, 0.03, 0.022)), ((-0.04, -0.455, 0.968), (0.025, 0.03, 0.022)),
    ((0.0, -0.37, 0.99), (0.03, 0.03, 0.022)), ((0.09, -0.4, 0.955), (0.022, 0.026, 0.022)), ((-0.095, -0.38, 0.95), (0.024, 0.028, 0.022)),
    ((0.05, -0.27, 0.965), (0.027, 0.03, 0.025)), ((-0.06, -0.25, 0.955), (0.026, 0.03, 0.025)),
    ((0.0, -0.2, 0.9), (0.03, 0.03, 0.028)),
    ((0.235, -0.36, 0.86), (0.024, 0.03, 0.024)), ((0.25, -0.39, 0.78), (0.028, 0.032, 0.028)),
    ((-0.235, -0.36, 0.86), (0.024, 0.03, 0.024)), ((-0.25, -0.39, 0.78), (0.028, 0.032, 0.028)),
    ((0.17, -0.27, 0.72), (0.026, 0.03, 0.026)), ((-0.17, -0.27, 0.72), (0.026, 0.03, 0.026)),
]


def make_dapples(body: bpy.types.Object, seed: int = 404) -> list[tuple[tuple, tuple]]:
    """Round dark spots over the back, the sides, the haunches, the upper legs and the tail paddle (2-turnaround.png):
    a Poisson set on the body's left half, mirrored with a little jitter, plus a row down the spine."""
    co, vn = S.mesh_arrays(body)
    rng = np.random.default_rng(seed)
    z = zones(co, vn)
    cream = cream_mask(co, z)
    teal = (cream < 0.2) & ~z['head'] & ~z['paw'] & (co[:, 2] > 0.2)
    teal_body = teal & (z['torso'] | (z['leg'] & (co[:, 2] > 0.18)))
    out = list(DAPPLES_HEAD)
    picks: list[np.ndarray] = []

    def poisson(mask, spacing, rmin, rmax, count, flat_x: bool):
        idx = np.nonzero(mask)[0]
        if len(idx) == 0:
            return
        idx = rng.permutation(idx)[:20000]
        for i in idx:
            p = co[i]
            if picks and float(np.min(np.linalg.norm(np.array(picks) - p, axis=1))) < spacing:
                continue
            picks.append(p)
            r = rmin + (rmax - rmin) * rng.random()
            out.append((tuple(p), (r * 0.6 if flat_x else r, r * 1.05, r)))
            if p[0] > 0.035:
                j = rng.normal(0, 0.012, 3)
                q = v3((-p[0] + j[0], p[1] + j[1], p[2] + j[2] * 0.5))
                picks.append(q)
                r2 = r * (0.9 + 0.2 * rng.random())
                out.append((tuple(q), (r2 * 0.6 if flat_x else r2, r2 * 1.05, r2)))
            if len(picks) >= count:
                return

    # the spine row first (the back view's centre line), then the flanks and haunches, then the tail paddle
    spine = teal_body & (np.abs(co[:, 0]) < 0.02) & (co[:, 2] > 0.45)
    poisson(spine, 0.085, 0.024, 0.032, 8, False)
    poisson(teal_body & (co[:, 0] >= 0.0), 0.088, 0.024, 0.04, 80, False)
    n0 = len(picks)
    poisson(teal & z['tail'] & (co[:, 0] >= 0.0), 0.045, 0.012, 0.02, n0 + 30, True)
    C.log(f'dapples: {len(out)} ({len(DAPPLES_HEAD)} on the head)')
    return out


def cream_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """0 teal … 1 cream, evaluated at the roots (so locks are all of one colour and the markings follow the fur)."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    cream = np.maximum(ell_soft(p, (0.0, -0.56, 0.64), (0.2, 0.17, 0.07), 0.12), ell_soft(p, MUZZLE[0], tuple(r * 1.12 for r in MUZZLE[1]), 0.08))
    cream = np.maximum(cream, ell_soft(p, (0.0, -0.45, 0.53), (0.18, 0.2, 0.12), 0.1))
    for s in (1, -1):
        cream = np.maximum(cream, ell_soft(p, (0.13 * s, -0.5, 0.68), (0.1, 0.1, 0.065), 0.2))
    # round 6: the teal comes down in a V between the eyes to the top of the nose (round 5 had a cream bridge)
    tip = NOSE_C.z + 0.026
    under_eye = EYE_C[1].z - 0.014
    zv = np.where(ax < 0.075, tip + (ax / 0.075) * (under_eye - tip), under_eye + 0.004 * smooth(0.12, 0.17, ax))
    vfill = (y < -0.49) & (zz > 0.6) & (ax < 0.17)
    cream = np.maximum(cream, vfill * smooth(zv + 0.004, zv - 0.004, zz))
    cream = np.where(z['head'] & ~z['chin'] & (zz > zv + 0.004) & (ax < 0.17) & (y < -0.45), np.minimum(cream, 0.0), cream)
    # body: the chest ruff and the underside
    bib_w = 0.115 + 0.05 * smooth(0.6, 0.3, zz)
    bib = smooth(bib_w + 0.015, bib_w - 0.015, ax) * smooth(-0.22, -0.27, y) * smooth(0.08, 0.12, zz) * smooth(0.68, 0.64, zz)
    bib *= ~z['tail']
    cream = np.maximum(cream, bib * (~z['head'] | z['chin']))
    zb = np.interp(y, [-0.45, -0.28, -0.05, 0.2, 0.36], [0.48, 0.33, 0.27, 0.26, 0.27])
    cream = np.maximum(cream, z['torso'] * smooth(zb + 0.015, zb - 0.015, zz))
    for lg, (lx, ly) in LEGS.items():
        cream = np.maximum(cream, ell_soft(p, (lx, ly - 0.14 * PAW_K, 0.02), (0.11, 0.06, 0.04), 0.2))
    # the paws: a cream rim around the sole
    for lg, (lx, ly) in LEGS.items():
        rim = ell_soft(p, (lx, ly - 0.07 * PAW_K, 0.0), (0.16 * PAW_K, 0.19 * PAW_K, 0.06), 0.12) * smooth(0.045, 0.02, zz)
        cream = np.maximum(cream, rim)
    # the tail: a cream band round the paddle's edge, where the coral fluke begins
    along = (p - v3(PADDLE_C)) @ v3(TAIL_DIR)
    band = z['paddle'] * smooth(0.68, 0.84, z['paddle_r']) * smooth(-0.07, -0.02, along)
    cream = np.maximum(cream, band)
    return np.clip(cream, 0.0, 1.0)


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    """Per vertex of a body source (the smooth body, its locks or the tuft): 'paint' = teal or cream by root (linear RGB,
    unshaded), 'cream' = the cream mask, 'shade' = a darker root and lighter tip on each lock, 'rough' = (1, roughness,
    clearcoat mask). The dapples are added per pixel by the bake shader (`body_material`), so they stay round."""
    col = colours(pal)
    root = S.attr_array(ob, 'root').astype(np.float64)
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    pos = co.reshape(-1, 3).astype(np.float64)
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    lrand = S.attr_array(ob, 'lrand').astype(np.float64)
    z = zones(root)
    cream = cream_mask(root, z)
    rgb = lin(col['teal'])[None, :] * (1 - cream[:, None]) + lin(col['cream'])[None, :] * cream[:, None]
    shade = 0.72 + 0.3 * tpos + 0.1 * (lrand - 0.5)
    shade = np.where(kind < 0.5, 1.0, shade)
    is_lock = kind > 0.5
    rough = np.where(is_lock, 0.4 + 0.3 * np.abs(tpos - 0.45), 0.62)
    coat = np.where(is_lock, 0.16, 0.08)
    muz = ell_soft(root, MUZZLE[0], tuple(r * 1.1 for r in MUZZLE[1]), 0.1)
    rough = rough * (1 - muz) + 0.58 * muz
    coat = coat * (1 - muz) + 0.06 * muz
    glossy = ell_soft(pos, tuple(NOSE_C), (0.044, 0.036, 0.03), 0.06)
    for leg in LEGS:
        pc, pr = pad_centre(leg)
        glossy = np.maximum(glossy, ell_soft(pos, tuple(pc), pr, 0.08))
        for c in cap_centres(leg):
            glossy = np.maximum(glossy, ell_soft(pos, tuple(c), tuple(r + 0.0015 for r in cap_radii()), 0.03))
    rough = rough * (1 - glossy) + 0.2 * glossy
    coat = coat * (1 - glossy) + 0.9 * glossy
    return {'paint': rgb, 'cream': cream, 'shade': shade, 'rough': np.stack([np.ones(len(pos)), rough, coat], axis=1)}


def fin_arrays(ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    """The membranes: coral, darker along the ribs, paler toward the scalloped edge, teal (ears) or cream (tail) at the
    root. A rainbow palette runs its six colours across the fan (Songheart)."""
    col = colours(pal)
    fan = S.attr_array(ob, 'fan').astype(np.float64)
    part = S.attr_array(ob, 'fin_part')
    u, v, rib = fan[:, 0], fan[:, 1], fan[:, 2]
    if pal.get('rainbow'):
        stops = np.linspace(0, 1, len(RAINBOW))
        cols = np.stack([lin(h) for h in RAINBOW])
        vv = np.where(part > 1.5, v, np.where(part > 0, 1 - v, 1 - v))
        base = np.stack([np.interp(vv, stops, cols[:, i]) for i in range(3)], axis=1)
        base = base * 0.85 + lin(col['coral'])[None, :] * 0.15
    else:
        base = np.tile(lin(col['coral']), (len(u), 1))
    rib_dark = base * 0.5
    k = (rib * 0.8)[:, None]
    rgb = base * (1 - k) + rib_dark * k
    pale = (smooth(0.55, 1.0, u) * 0.45)[:, None]
    rgb = rgb * (1 - pale) + lin(C.mix_hex(col['coral'], '#FFD9C8', 0.45))[None, :] * pale
    root_col = np.where((part > 1.5)[:, None], lin(col['cream'])[None, :], lin(C.mix_hex(col['teal'], col['coral'], 0.3))[None, :])
    rw = np.where(part > 1.5, smooth(0.32, 0.1, u), smooth(0.16, 0.05, u))[:, None]
    rgb = rgb * (1 - rw) + root_col * rw
    rough = 0.3 * (1 - rib) + 0.24 * rib
    rc = np.stack([np.ones(len(u)), rough, np.full(len(u), 0.45)], axis=1)
    return rgb, rc


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object]) -> None:
    """Store the paint attributes on every source: 'paint' (base), 'paint_v' (Songheart), 'cream', 'shade', 'rough'."""
    var = VARIANTS[VARIANT_ID]
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'cream', a['cream'])
        S.add_attr(ob, 'shade', a['shade'])
        S.set_colour_attr(ob, 'paint_v', paint_arrays(ob, var)['paint'])
    for ob in fins:
        rgb, rc = fin_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        rgb_v, _ = fin_arrays(ob, var)
        S.set_colour_attr(ob, 'paint_v', rgb_v)


# ----------------------------------------------------------------------------- paint (nodes: the crisp details, per pixel)
def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def body_material(name: str, attr: str, pal: dict, dapples) -> bpy.types.Material:
    """Emission = the painted attribute, with the round marks evaluated per pixel by position: the dapples (on teal
    only), the brows, the blush, the nose, the smile line and the pink toe caps and pads; then each lock's shade."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 0.5)
    c = nb.attribute(attr).outputs['Color']
    dap = None
    for dc, dr in dapples:
        e = _ell(nb, pos, dc, dr, 0.14)
        dap = e if dap is None else nb.math('MAXIMUM', dap, e)
    if dap is not None:
        dap = nb.math('MULTIPLY', dap, nb.math('SUBTRACT', 1.0, nb.attribute('cream').outputs['Fac']))
        c = nb.mix(dap, c, nb.rgb(C.lin(col['dapple'])))
    shade = nb.attribute('shade').outputs['Fac']
    c = nb.mix(1.0, c, nb.comb(shade, shade, shade), blend='MULTIPLY')
    brow = None
    for s in (1, -1):
        e = _ell(nb, pos, (0.112 * s, -0.525, 0.884), (0.034, 0.05, 0.0105), 0.35)
        brow = e if brow is None else nb.math('MAXIMUM', brow, e)
    c = nb.mix(brow, c, nb.rgb(C.lin(col['brow'])))
    blush = None
    for s in (1, -1):
        e = _ell(nb, pos, (0.15 * s, -0.5, 0.69), (0.052, 0.06, 0.042), 0.6)
        blush = e if blush is None else nb.math('MAXIMUM', blush, e)
    c = nb.mix(nb.math('MULTIPLY', blush, 0.8), c, nb.rgb(C.lin(col['blush'])))
    c = nb.mix(_ell(nb, pos, tuple(NOSE_C), (0.044, 0.036, 0.03), 0.06), c, nb.rgb(C.lin(NOSE_HEX)))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.25, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(MOUTH_HEX)))
    pad = None
    for leg in LEGS:
        pc, pr = pad_centre(leg)
        e = _ell(nb, pos, tuple(pc), pr, 0.08)
        pad = e if pad is None else nb.math('MAXIMUM', pad, e)
        for cc in cap_centres(leg):
            pad = nb.math('MAXIMUM', pad, _ell(nb, pos, tuple(cc), tuple(r + 0.0015 for r in cap_radii()), 0.03))
    c = nb.mix(pad, c, nb.rgb(C.lin(col['pink'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """Round 6: a deep teal iris with a big pupil and crisp catchlights; the top is the dark upper lash line under the
    fur lid (thicker toward the outer corner); no dark ring round the bottom (it read as goggles)."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    rx = nb.math('DIVIDE', x, 1.0)
    ry = nb.math('DIVIDE', y, 1.0)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', rx, 0.8), nb.math('DIVIDE', ry, 0.9), 0.0))
    # P1.1 review 1: the pupil fills most of the iris; a thin dark liner round it, a white crescent low on the outer side
    iris_c = nb.ramp(ri, [(0.0, C.lin('#0A1014')), (0.6, C.lin('#0A1014')), (0.66, C.lin('#1A383E')),
                          (0.84, C.lin('#2B5E62')), (0.92, C.lin('#3A7274')), (0.97, C.lin('#2A5257')), (1.0, C.lin('#16191D')), (1.4, C.lin('#16191D'))])
    low = nb.math('MULTIPLY', nb.smooth(ry, -0.15, -0.65), nb.smooth(ri, 0.95, 0.6))
    c = nb.mix(nb.math('MULTIPLY', low, 0.55), iris_c, nb.rgb(C.lin('#5AA8A0')))
    crescent = nb.math('MULTIPLY', nb.smooth(ri, 1.06, 1.14), nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', rx, side), 0.1, 0.45), nb.smooth(ry, 0.25, -0.1)))
    c = nb.mix(crescent, c, nb.rgb(C.lin('#F2F0EA')))
    # the catchlights sit up and toward the key light, the same way in both eyes (one light)
    hx = rx
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', hx, 0.24), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.28), 1.2), 0.0)), 0.2, 0.17)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', hx, 0.27), nb.math('ADD', ry, 0.32), 0.0)), 0.075, 0.058)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    # the upper lash line: dark over the top, a little lower and thicker at the outer corner
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', rx, side), 0.2, 0.9), 0.1)
    lash = nb.smooth(nb.math('ADD', ry, outer), 0.6, 0.68)
    c = nb.mix(lash, c, nb.rgb(C.lin('#1A1214')))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the rig's proportions (plans/quadruped.py)
def rig_p() -> dict:
    ear_tip = ear_point(1, 1.0, 0.5)
    ed = ear_tip - EAR_ROOT[1]
    return {
        'hip': (0.0, 0.2, 0.36),
        'chest': (0.0, -0.24, 0.4),
        'head_c': tuple(HEAD_C),
        'head_r': 0.215,
        'ear_base': tuple(EAR_ROOT[1]),
        'ear_dir': tuple(ed.normalized()),
        'ear_len': ed.length,
        'tail_base': tuple(TAIL_BASE),
        'tail_dir': tuple(TAIL_DIR),
        'tail_len': TAIL_LEN,
        'legs': {leg: (lx, ly, 0.38 if leg[0] == 'F' else 0.34) for leg, (lx, ly) in LEGS.items()},
        'knee_back': 0.03,
        'ankle_z': 0.04,
        'foot_len': 0.12,
        'leg_radius': 0.1,
        'stride': 0.15,
    }


def ear_weights(p: np.ndarray, u: np.ndarray) -> dict[str, np.ndarray]:
    """Head → ear.1 → ear.2 along the ear (the fur cap and the membrane move together)."""
    w2 = smooth(0.35, 0.8, u)
    w1 = (1 - w2) * smooth(0.0, 0.18, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def tail_weights(p: np.ndarray) -> dict[str, np.ndarray]:
    """hips → tail.1 → tail.2 → tail.3 by how far along the tail a point lies (the paddle and the fluke move together)."""
    t = ((p - v3(TAIL_BASE)) @ v3(TAIL_DIR)) / TAIL_LEN
    w = {'hips': smooth(0.05, -0.08, t)}
    c = [1 / 6, 0.5, 5 / 6]
    raw = []
    for k in range(3):
        raw.append(np.clip(1.0 - np.abs(t - c[k]) * 3.0, 0, 1))
    raw[0] = np.where(t < c[0], 1.0, raw[0])
    raw[2] = np.where(t > c[2], 1.0, raw[2])
    tot = raw[0] + raw[1] + raw[2]
    for k in range(3):
        w[f'tail.{k + 1}'] = raw[k] / np.maximum(tot, 1e-6) * (1 - w['hips'])
    return w


# ----------------------------------------------------------------------------- review framing (Blender sheets)
REVIEW = {
    'centre': (0.0, 0.02, 0.5),
    'size': 1.75,
    'head': ((0.0, -0.42, 0.76), 0.98),
}
