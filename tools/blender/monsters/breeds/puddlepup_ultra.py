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
from monsters.breeds import puddlepup_ears as E

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
        # P1.2 review 1: deep teal, not grey-black smudges
        'dapple': C.mix_hex(C.shade_hex(teal, 0.7, cool=0.03), '#0E8C82', 0.6),
        'brow': C.mix_hex(pal['eye'], teal, 0.3),
        # round 6: coral fins, not bubblegum pink, with darker shaded ribs
        'coral': C.mix_hex(pink, '#FF8C69', 0.2),          # P1.2 review 1: pinker (0.4 read salmon-orange)
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
# P1.2: the nose sits back on the muzzle, with a short bridge behind it (P1.1's read as a ball on a stalk in profile)
NOSE_C = Vector((0.0, -0.598, 0.714))
# round 6: one smooth short muzzle (round 5's two pads and a chin read as three lobes); P1.2 a little fuller on top
MUZZLE = ((0.0, -0.556, 0.67), (0.098, 0.061, 0.068))
CHEEK = (0.11, -0.455, 0.68, 0.088)
E.configure(HEAD_C, HEAD_R, CHEEK)
EAR_ROOT = {s: E.root(s) for s in (1, -1)}


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


def blink_pivot(s: int) -> tuple[Vector, Vector, Vector]:
    """Where an eye's blink bone sits and its axes (up, and out of the face). P1.2: the pivot is behind the lens at the
    closed lid's lash height, so a blink squashes the lens down onto the lash line and sinks it into the head, showing
    the sculpted closed lid under it (closed_lid)."""
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.72, 0.04, 0.2)       # the blink bone's scale when closed: across, up (its axis), out of the face
# P1.2: texel density per game mesh in the atlas (the eyes' iris and catchlights crisper; the smooth membranes less)
ATLAS_DENSITY = {'lo_eyes': 1.35, 'lo_fins': 0.8}


# ----------------------------------------------------------------------------- ears (P1.2: one fur flap, lined; puddlepup_ears)
N_RIBS = 6


def scallop(v: float, ribs: int = N_RIBS, depth: float = 0.026) -> float:
    return 1.0 - depth * (0.5 - 0.5 * math.cos(2 * math.pi * ribs * v))


def rib_mask(v: float, ribs: int = N_RIBS, width: float = 0.075) -> float:
    k = (v * ribs) % 1.0
    d = min(k, 1.0 - k)
    return math.exp(-(d / width) ** 2)


# ----------------------------------------------------------------------------- the tail: a furry teal paddle with a coral fluke
TAIL_BASE = Vector((0.0, 0.31, 0.36))
TAIL_DIR = Vector((0.0, 1.0, 0.5)).normalized()
TAIL_UP = Vector((0.0, -TAIL_DIR.z, TAIL_DIR.y))         # up in the tail's own (sagittal) plane
# P1.2 review 1: a longer, thicker paddle with a round fan at its tip (P1.1's fan ran along the paddle's back like a sail)
TAIL_LEN = 0.6
PADDLE_C = TAIL_BASE + TAIL_DIR * 0.35
PADDLE_R = (0.062, 0.22, 0.12)                            # half thickness (x), half length (along the tail), half height
FAN_C = PADDLE_C + TAIL_DIR * 0.11
FAN_PHI = (math.radians(-82), math.radians(82))         # from straight back (along the tail), + = up
N_TAIL_RIBS = 11


def fan_radius(phi: float) -> float:
    return 0.2 + 0.05 * math.cos(phi)


FAN_THICK = 0.08          # P1.2: the fluke is a lens this thick in the middle by the paddle (P1.1's flat sheet read as a line)


def fan_half(u: float, v: float) -> float:
    return 0.5 * FAN_THICK * (1.0 - u) ** 0.9 * math.sin(math.pi * min(1.0, max(0.0, v))) ** 0.75


def tail_fan_point(u: float, v: float, face: int = 1, relief: float = 0.0) -> Vector:
    """u 0..1 from inside the paddle to the scalloped edge, v 0..1 bottom → top; `face` +1 / −1 is the fluke's left /
    right face. The fluke has volume, a lens that closes to an edge all round (a leaf from behind, as in the pictures),
    and its back rays curl gently up toward the edge."""
    phi = FAN_PHI[0] + (FAN_PHI[1] - FAN_PHI[0]) * v
    r0, r1 = 0.04, fan_radius(phi)
    r = r0 + (r1 - r0) * u
    d = TAIL_DIR * math.cos(phi) + TAIL_UP * math.sin(phi)
    p = FAN_C + d * r + TAIL_UP * (0.03 * u * u * max(0.0, math.cos(phi)))
    p += Vector((face * (fan_half(u, v) + relief), 0.0, 0.0))
    return p


def orient_sheet(ob: bpy.types.Object, out: Vector) -> None:
    """Flip a sheet's faces when its mean normal looks against `out` (its bake rays and AO need the outer side)."""
    me = ob.data
    n = np.empty(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get('normal', n)
    if float(n.reshape(-1, 3).mean(0) @ np.array(out[:], np.float32)) < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        me.update()


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
                relief = 0.0016 * rib_mask(v, ribs) * (1.0 - 0.5 * u) * float(smooth(0.04, 0.2, u))
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
    """The ear linings and the tail fluke's two faces. `fin_part` attribute: 1 left ear, -1 right ear, 2 tail. The
    linings' `fan` u is the flap's own u (so they share the fur flap's skin weights)."""
    out = []
    tag = 'hi' if high else 'lo'
    for s in (1, -1):
        nu, nv = ((90, 120) if not quick else (40, 48)) if high else (18, 40)
        ob = build_fan_sheet(f'{tag}_ear{"L" if s > 0 else "R"}', lambda u, v, relief=0.0, s=s: E.lining_point(s, u, v, relief),
                             nu, nv, N_RIBS, high, s < 0, None)
        fan = S.attr_array(ob, 'fan').astype(np.float64)
        fan[:, 0] = E.lining_u(fan[:, 0])
        S.add_attr(ob, 'fan', fan)
        orient_sheet(ob, Vector((-s, -0.4, 0.0)))
        S.add_attr(ob, 'fin_part', np.full(len(ob.data.vertices), float(s)))
        out.append(ob)
    for face in (1, -1):
        nu, nv = ((70, 160) if not quick else (28, 64)) if high else (12, 56)
        ob = build_fan_sheet(f'{tag}_tailfan{"L" if face > 0 else "R"}', lambda u, v, relief=0.0, face=face: tail_fan_point(u, v, face, relief),
                             nu, nv, N_TAIL_RIBS, high, False, None, 0.03)
        orient_sheet(ob, Vector((face, 0.0, 0.0)))
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
        Part('muzzle', 'sphere', loc=MUZZLE[0], radius=1.0, scale=(0.094, 0.05, 0.06)),
        # P1.2: a short bridge from the brow to the nose, so the nose sits on the muzzle (no stalk in profile)
        Part('bridge', 'sphere', loc=(0.0, -0.548, 0.727), radius=1.0, scale=(0.05, 0.047, 0.036)),
        Part('chin', 'sphere', loc=(0.0, -0.54, 0.634), radius=0.036, scale=(1.35, 0.95, 0.62)),
        Part('nose', 'sphere', loc=tuple(NOSE_C), radius=0.042, scale=(1.3, 0.68, 0.68)),
        Part('neck', 'capsule', loc=(0.0, -0.34, 0.66), to=(0.0, -0.29, 0.52), radius=0.13),
    ]
    # P1.1 review 1: no lid ridge (it read as heavy, sad brows); the lash line is painted on the eye.
    # P1.2: the ears are fur slabs (body_extras), not caps over separate fans
    return ps


def body_extras() -> list[bpy.types.Object]:
    """Meshes joined into the voxel body with the parts: the two ear flaps' fur slabs (new objects on every call)."""
    return [E.slab(s) for s in (1, -1)]


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


LID_LASH, LID_DROP, LID_W = 0.1, 0.16, 0.92      # the closed lid's lash line (review 1: 0.26 sat too low): ye = −(LASH + DROP·(1 − (xe/W)²))·EYE_R


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """P1.2 blink: under each lens, the soft round closed lid (a bulge) and its lash line, a down-curved arc a little
    below the eye's middle, thicker toward the outer corner. Hidden by the lens until a blink sinks it into the head
    (P1.1 squashed the lens, and the closed lids read as tape)."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax, ay = EYE_R * 0.96 * EYE_SPREAD, EYE_R * 1.08 * EYE_SPREAD
        r2 = (xe / ax) ** 2 + (ye / ay) ** 2
        front = ze > -0.035
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * EYE_R
        th = 0.0021 + 0.0017 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


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
    bulge, lash = closed_lid(co)
    disp = -0.0022 * groove - 0.005 * nos - 0.0014 * lip + 0.0002 * peb + 0.0035 * bulge - 0.0012 * lash
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)


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
    """(on an ear's fur flap, the flap's u there): the skin weights follow u, like the lining's."""
    on, u, _inner, _L = E.zone(p)
    return on, u


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
    ear, ear_u, ear_inner, ear_l = E.zone(p)
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
    ear_root = E.root_dist(p) < 0.06
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
    return {'ear': ear, 'ear_u': ear_u, 'ear_v': ear_l['v'], 'ear_inner': ear_inner, 'ear_down': ear_l['down'], 'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face,
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
    # P1.2: on the ear flaps the fur runs down the flap
    g_head = np.where(z['ear'][:, None], z['ear_down'], g_head)
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
        # P1.2: a shaggy fringe along each ear flap's edges and the bottom of its fur, so the flap reads as its own lobe
        ev = z['ear_v']
        ear_fringe = z['ear'] & ~z['ear_inner'] & (z['ear_u'] > 0.22) & (
            (z['ear_u'] > E.u_fur(np.clip(ev, 0, 1)) - 0.12) | (ev < 0.14) | (ev > 0.86))
        L = np.where(ear_fringe, 0.064, L)
        W = np.where(ear_fringe, 0.036, W)
        lift = np.where(ear_fringe, _rad(4), lift)
        sp = np.where(ear_fringe, 0.028, sp)
        fringe = back_head | ridge | bib | belly | leg_back | ear_fringe
        skip = ~fringe | z['face'] | z['muzzle'] | (z['eye_d'] < 0.12) | (z['chin'] & (y < -0.48)) | z['ear_root'] | z['tail']
    # P1.2: no cards on the lining side of an ear flap (they'd poke through the membrane), and none where cream meets
    # teal (a cream card over teal fur, or the reverse, glittered at the border)
    cream = cream_mask(p, z)
    skip = skip | z['ear_inner'] | ((cream > 0.06) & (cream < 0.94))
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
    ((0.0, -0.2, 0.9), (0.03, 0.03, 0.028)), ((0.012, -0.235, 0.925), (0.016, 0.018, 0.016)),
    ((0.17, -0.27, 0.72), (0.026, 0.03, 0.026)), ((-0.17, -0.27, 0.72), (0.026, 0.03, 0.026)),
]
EAR_SPOTS = [(0.3, 0.5, 0.025), (0.42, 0.8, 0.029), (0.52, 0.28, 0.019), (0.6, 0.62, 0.015)]   # (u, v, radius) on a flap


def make_dapples(body: bpy.types.Object, seed: int = 404) -> list[tuple[tuple, tuple]]:
    """Dark dapples over the back, the sides, the haunches, the upper legs, the tail paddle and the ear flaps
    (2-turnaround.png). P1.2: organic, not polka dots: mixed sizes (many small, a few big, the big ones on the back),
    uneven shapes, and some clustered with small satellites that merge into them; the bake's noise warp roughens every
    edge. A Poisson set on the left half, each mirrored with its own jitter and its own satellites."""
    co, vn = S.mesh_arrays(body)
    rng = np.random.default_rng(seed)
    z = zones(co, vn)
    cream = cream_mask(co, z)
    teal = (cream < 0.2) & ~z['head'] & ~z['paw'] & (co[:, 2] > 0.2)
    teal_body = teal & (z['torso'] | (z['leg'] & (co[:, 2] > 0.18)))
    out = list(DAPPLES_HEAD)
    for s in (1, -1):
        for u, v, r in EAR_SPOTS:
            P, _fu, _fv, n = E.frame(s, u, v)
            c = P[0] + n[0] * float(E.thickness(u, v))
            out.append((tuple(c), (r, r * 1.2, r)))
    picks: list[np.ndarray] = []

    def spot(p, nrm, r, flat_x: bool) -> None:
        a = rng.uniform(0.8, 1.25, 3)
        out.append((tuple(p), (r * a[0] * (0.6 if flat_x else 1.0), r * a[1] * 1.1, r * a[2])))
        if rng.random() < 0.4:                       # satellites that merge into it: kidney and blob shapes
            for _ in range(rng.integers(1, 3)):
                t = np.cross(nrm, rng.normal(0, 1, 3))
                t /= max(np.linalg.norm(t), 1e-9)
                rs = r * rng.uniform(0.35, 0.65)
                q = p + t * r * rng.uniform(0.7, 1.1)
                out.append((tuple(q), (rs * (0.6 if flat_x else 1.0), rs * 1.05, rs)))

    def poisson(mask, spacing, rmin, rmax, count, flat_x: bool):
        idx = np.nonzero(mask)[0]
        if len(idx) == 0:
            return
        idx = rng.permutation(idx)[:20000]
        for i in idx:
            p = co[i]
            # big ones on the back, smaller down the sides and the legs; most are small
            top = float(smooth(0.25, 0.55, p[2]))
            r = rmin + (rmax - rmin) * (rng.random() ** 1.7) * (0.55 + 0.45 * top)
            if picks and float(np.min(np.linalg.norm(np.array(picks) - p, axis=1))) < spacing * (0.55 + r / rmax):
                continue
            picks.append(p)
            spot(p, vn[i], r, flat_x)
            if p[0] > 0.035:
                j = rng.normal(0, 0.016, 3)
                q = v3((-p[0] + j[0], p[1] + j[1], p[2] + j[2] * 0.5))
                picks.append(q)
                spot(q, vn[i] * v3((-1, 1, 1)), r * rng.uniform(0.8, 1.2), flat_x)
            if len(picks) >= count:
                return

    # the spine first (the back view's centre line), then the flanks and haunches, then the tail paddle
    spine = teal_body & (np.abs(co[:, 0]) < 0.02) & (co[:, 2] > 0.45)
    poisson(spine, 0.07, 0.014, 0.042, 9, False)
    poisson(teal_body & (co[:, 0] >= 0.0), 0.075, 0.012, 0.058, 92, False)
    n0 = len(picks)
    poisson(teal & z['tail'] & (co[:, 0] >= 0.0), 0.04, 0.008, 0.022, n0 + 34, True)
    C.log(f'dapples: {len(out)} ellipsoids ({len(DAPPLES_HEAD)} on the head)')
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


_CREAM: dict[str, np.ndarray] = {}


def _cream_of(ob, root: np.ndarray, pos: np.ndarray, kind: np.ndarray, tpos: np.ndarray) -> np.ndarray:
    """The cream mask a source's vertices are painted with: by the root, so the markings follow the fur; P1.2: a lock
    that crosses the cream / teal border blends toward the colour under its tip along its length (review 1: hard cream
    shards and camouflage blotches at the border). Cached per source (base and variant paint the same mask)."""
    if ob.name not in _CREAM:
        cream = cream_mask(root, zones(root))
        lock = kind > 0.5
        if lock.any():
            cp = cream_mask(pos[lock], zones(pos[lock]))
            k = 0.6 * tpos[lock]
            cream[lock] = cream[lock] * (1 - k) + cp * k
        _CREAM[ob.name] = cream
    return _CREAM[ob.name]


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
    cream = _cream_of(ob, root, pos, kind, tpos)
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
    # P1.2 review 1: finer, softer ribs (strong dark ribs read as paper pleats) and a touch darker overall (the fluke
    # bloomed white-peach in ko, lit face-on by the key)
    base = base * 0.88
    rib_dark = base * 0.6
    k = (rib * 0.5)[:, None]
    rgb = base * (1 - k) + rib_dark * k
    # P1.2: a lighter coral at the edge, not near-white (the tip blew out white in ko), and rougher toward the edge so
    # the key light's highlight spreads instead of clipping
    pale = (smooth(0.6, 1.0, u) * 0.32)[:, None]
    rgb = rgb * (1 - pale) + lin(C.mix_hex(col['coral'], '#FFC2B0', 0.4))[None, :] * pale
    root_col = np.where((part > 1.5)[:, None], lin(col['cream'])[None, :], lin(C.mix_hex(col['teal'], col['coral'], 0.3))[None, :])
    rw = np.where(part > 1.5, smooth(0.32, 0.1, u), smooth(0.16, 0.05, u))[:, None]
    rgb = rgb * (1 - rw) + root_col * rw
    rough = (0.36 + 0.16 * smooth(0.45, 1.0, u)) * (1 - rib) + 0.28 * rib
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
    # P1.2: a noise warp roughens every dapple's edge (organic shapes, not polka dots)
    nz = nb.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 14.0
    nz.inputs['Detail'].default_value = 2.0
    nz.inputs['Roughness'].default_value = 0.55
    nb.link(pos, nz.inputs['Vector'])
    pw = nb.vmath('ADD', pos, nb.vmath('SCALE', nb.vmath('SUBTRACT', nz.outputs['Color'], (0.5, 0.5, 0.5)), scale=0.05))
    dap = None
    for dc, dr in dapples:
        e = _ell(nb, pw, dc, dr, 0.1)
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
    # P1.2: the closed lid (under the lens; it shows only while a blink sinks the lens) takes the fur's average tone, not
    # the smooth skin's brighter one (review 1: bright mint goggles), and its lash line
    lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
    c = nb.mix(nb.math('MULTIPLY', lid, 0.24), c, nb.rgb((0.0, 0.0, 0.0)))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin('#1A1214')))
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
    ed = E.tip(1) - EAR_ROOT[1]
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
    """Head → ear.1 → ear.2 along the flap's u (the fur flap and its lining move together). P1.2: the upper flap lies on
    the head and stays with it; the lower flap and the fan swing."""
    w2 = smooth(0.45, 0.88, u)
    w1 = (1 - w2) * smooth(0.08, 0.36, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


# P1.2: the ears and the tail swing less (the membranes flared like wings or sails in the big poses, ART_2_DETAIL §9.2);
# build_ultra scales these bones' rotations per clip ('*' = every clip without its own entry)
CLIP_CALM = {
    '*': {'ear': 0.7},
    'ko': {'ear': 0.1, 'tail': 0.45},
    'hit_heavy': {'ear': 0.2, 'tail': 0.55},
    'win': {'ear': 0.3, 'tail': 0.55},
    'hit': {'ear': 0.5},
    'strike': {'ear': 0.3},                  # review 1: the near ear swung across the muzzle
    'sidestep_l': {'ear': 0.5},
    'sidestep_r': {'ear': 0.5},
}


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
    'centre': (0.0, 0.07, 0.5),
    'size': 1.85,
    'head': ((0.0, -0.42, 0.76), 0.98),
}
