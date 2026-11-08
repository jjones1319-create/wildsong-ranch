"""Rammerjack at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9; tools/blender/monsters/breeds/RECIPE.md).

A stocky mountain goat, 1.3 × Puddlepup's height (chatgpt/monsters/08-rammerjack/: the card decides the parts, the
pictures the shapes, CONTENT §2.2 the colours):
  - a long, shaggy cream coat (big wavy locks baked into the atlas, three layers of long fur cards for the outline),
    shorter on the face and the legs; chestnut on the brows, the cheeks and beard, the upper legs, a saddle patch on
    each flank and the tail; lighter cream on the face and the socks above the hooves;
  - huge spiral horns with growth rings, each wrapped in five bands of twisted rope (rigid props on `prop.horns`);
  - a red knitted scarf round the neck, knotted at the front-left with one hanging end and a fringe (the band moves
    with the neck and chest, the end on its own spring chain `scarf.*`);
  - a long chestnut beard on a spring chain (`beard.*`), small goat ears lined pink, big brown eyes under thick brows,
    a dark nose and a small smile; sturdy cloven hooves (plan option `hooves`).

Metres; the monster faces −Y, Z is up, +X is its left. Palette CONTENT §2.2 #29: #EFE6D2 / #FFF8EA / #A0522D
(scarf #D1495B) / #3A2E26. No secret variant (src/art/monster/variants.ts has none).
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3
from monsters.breeds import rammerjack_beard as BD
from monsters.breeds import rammerjack_props as RP

ID = 'rammerjack'
LOOK = 'rammerjack-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 195               # 1.3 × Puddlepup (PROMPTS.md: medium-large); modelled 1.3 m tall to the horns' top

PALETTE = {'body': '#EFE6D2', 'belly': '#FFF8EA', 'accent': '#A0522D', 'eye': '#3A2E26', 'scarf': '#D1495B'}
VARIANTS: dict = {}

# colours CONTENT has none for (the card's pictures suggest them; never sampled)
ROPE_HEX = '#C79A52'
HOOF_HEX = '#3D302A'
NOSE_HEX = '#4A2F29'
MOUTH_HEX = '#4E3029'
LINING_HEX = '#E9A9A2'
LASH_HEX = '#2A1C17'


def colours(pal: dict) -> dict:
    coat, light, nut = pal['body'], pal['belly'], pal['accent']
    scarf = pal.get('scarf', '#D1495B')
    return {
        'coat': coat, 'light': light, 'nut': nut, 'scarf': scarf,
        'nut_dark': C.shade_hex(nut, 0.72),
        'beard': C.mix_hex(nut, '#B0622F', 0.25),
        'brow': C.shade_hex(nut, 0.92),
        'horn': C.shade_hex(nut, 0.8),
        'horn_dark': C.mix_hex(C.shade_hex(nut, 0.52), '#2E1A10', 0.2),
        'horn_light': C.mix_hex(nut, '#C98A55', 0.25),
        'rope': ROPE_HEX, 'rope_dark': C.shade_hex(ROPE_HEX, 0.38),
        'scarf_dark': C.shade_hex(scarf, 0.5),
        'scarf_light': C.mix_hex(scarf, '#F07A86', 0.3),
        'hoof': HOOF_HEX,
        'lining': LINING_HEX,
        'tuft': C.shade_hex(C.mix_hex(coat, light, 0.25), 0.9),
    }


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def tuft_colour(pal: dict) -> str:
    return colours(pal)['tuft']


# ----------------------------------------------------------------------------- the head
HEAD_C = Vector((0.0, -0.44, 1.04))
HEAD_R = (0.174, 0.172, 0.186)
def _on_head(x: float, z: float, out: float) -> float:
    q = 1.0 - (x / HEAD_R[0]) ** 2 - ((z - HEAD_C.z) / HEAD_R[2]) ** 2
    return HEAD_C.y - HEAD_R[1] * math.sqrt(max(q, 0.0)) - out


EYE_C = {s: Vector((0.116 * s, _on_head(0.116, 1.0, 0.007), 1.0)) for s in (1, -1)}
EYE_R = 0.058
EYE_DEPTH = (0.42, 0.30)
EYE_SPREAD = 1.0
NOSE_C = Vector((0.0, -0.7, 0.948))
MUZZLE = ((0.0, -0.652, 0.918), (0.084, 0.07, 0.062))
CHIN_C = (0.0, -0.63, 0.868)
BROW = {s: [((0.078 * s, -0.587, 1.09), (0.046, 0.04, 0.025)), ((0.116 * s, -0.57, 1.103), (0.048, 0.042, 0.027)),
            ((0.154 * s, -0.54, 1.091), (0.044, 0.042, 0.024))] for s in (1, -1)}


def brow_soft(p: np.ndarray, soft: float, grow: float = 1.0) -> np.ndarray:
    out = np.zeros(len(p))
    for s in (1, -1):
        for c, r in BROW[s]:
            out = np.maximum(out, ell_soft(p, c, tuple(v * grow for v in r), soft))
    return out


def eye_frame(s: int):
    c = EYE_C[s]
    surf_n = Vector(((c.x - HEAD_C.x) / HEAD_R[0] ** 2, (c.y - HEAD_C.y) / HEAD_R[1] ** 2, (c.z - HEAD_C.z) / HEAD_R[2] ** 2)).normalized()
    # the pictures' eyes look out of the front of the face (big, anime): mostly forward, a little out
    look = (surf_n * 0.7 + Vector((0, -1, 0)) * 0.3).normalized()
    look = (look + Vector((0, 0, 0.03))).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


LID_LASH, LID_DROP, LID_W = 0.08, 0.16, 0.92


def blink_pivot(s: int):
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.74, 0.04, 0.2)
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_props': 0.85}


# ----------------------------------------------------------------------------- the body's layout
LEGS = {'FL': (0.19, -0.33), 'FR': (-0.19, -0.33), 'BL': (0.168, 0.35), 'BR': (-0.168, 0.35)}
SOCK_Z = (0.09, 0.178)          # the cream socks above the hooves
LEG_NUT_TOP = 0.37               # chestnut on the legs up to here (under the coat's fringe)
TAIL_BASE = Vector((0.0, 0.38, 0.685))
TAIL_POINTS = [(0.0, 0.38, 0.685), (0.0, 0.42, 0.738), (0.0, 0.455, 0.785)]
TAIL_DIR = (Vector(TAIL_POINTS[-1]) - Vector(TAIL_POINTS[0])).normalized()
TAIL_LEN = (Vector(TAIL_POINTS[-1]) - Vector(TAIL_POINTS[0])).length
BEARD_CHAINS = {name: pts for name, pts in BD.CHAINS.items()}


def head_parts() -> list[Part]:
    return [
        Part('head', 'sphere', loc=tuple(HEAD_C), radius=1.0, scale=HEAD_R),
        Part('crown', 'sphere', loc=(0.0, -0.42, 1.135), radius=1.0, scale=(0.15, 0.135, 0.094)),
        # the straight goat profile: a bridge from the brow down to the nose
        Part('bridge', 'capsule', loc=(0.0, -0.55, 1.06), to=(0.0, -0.634, 0.962), radius=0.062),
        Part('muzzle', 'sphere', loc=MUZZLE[0], radius=1.0, scale=MUZZLE[1]),
        Part('nose', 'sphere', loc=(NOSE_C.x, NOSE_C.y + 0.002, NOSE_C.z + 0.007), radius=1.0, scale=(0.046, 0.022, 0.021)),
        Part('nosetip', 'sphere', loc=(NOSE_C.x, NOSE_C.y - 0.002, NOSE_C.z - 0.012), radius=1.0, scale=(0.024, 0.019, 0.016)),
        Part('chin', 'sphere', loc=CHIN_C, radius=1.0, scale=(0.058, 0.047, 0.038)),
        Part('jaw', 'capsule', loc=(0.0, -0.58, 0.885), to=(0.0, -0.47, 0.875), radius=0.072),
        Part('neck', 'capsule', loc=(0.0, -0.43, 0.95), to=(0.0, -0.41, 0.79), radius=0.158),
        Part('nape', 'sphere', loc=(0.0, -0.33, 0.9), radius=1.0, scale=(0.19, 0.13, 0.11)),
    ] + brow_parts()


def brow_parts() -> list[Part]:
    """Round 2: thick raised brows, a sculpted mass of three thin ellipsoids per side arching over each eye (they
    carry chestnut locks and short cards), oriented to the head's surface."""
    out = []
    hc, hr = v3(HEAD_C), v3(HEAD_R)
    for i, (c, r) in enumerate(BROW[1]):
        c = v3(c)
        q = np.sqrt((((c - hc) / hr) ** 2).sum())
        cs = hc + (c - hc) / q
        nrm = (cs - hc) / hr ** 2
        nrm /= np.linalg.norm(nrm)
        ax = math.degrees(math.asin(float(nrm[2])))
        az = math.degrees(math.atan2(-float(nrm[0]), float(nrm[1])))
        out.append(Part(f'brow{i}', 'sphere', loc=tuple(cs + nrm * 0.003), radius=1.0, scale=(r[0] * 1.0, 0.016, r[2] * 0.95),
                        rot=(ax, 0.0, az), mirror=True))
    return out


def leg_parts(leg: str) -> list[Part]:
    x, y = LEGS[leg]
    front = leg[0] == 'F'
    top = 0.45 if front else 0.47
    return [
        Part(f'thigh{leg}', 'capsule', loc=(x, y + (0.0 if front else 0.02), top), to=(x, y, 0.21), radius=0.084 if front else 0.09),
        Part(f'shin{leg}', 'capsule', loc=(x, y, 0.22), to=(x, y - 0.004, 0.085), radius=0.063),
        Part(f'sock{leg}', 'sphere', loc=(x, y - 0.006, 0.122), radius=1.0, scale=(0.074, 0.078, 0.05)),
    ]


def torso_parts() -> list[Part]:
    ps = [
        Part('neckbase', 'capsule', loc=(0.0, -0.41, 0.79), to=(0.0, -0.36, 0.6), radius=0.19),
        Part('withers', 'sphere', loc=(0.0, -0.25, 0.63), radius=1.0, scale=(0.25, 0.2, 0.13)),
        Part('chest', 'sphere', loc=(0.0, -0.33, 0.515), radius=1.0, scale=(0.285, 0.245, 0.235)),
        Part('barrel', 'sphere', loc=(0.0, -0.04, 0.52), radius=1.0, scale=(0.3, 0.42, 0.222)),
        Part('rump', 'sphere', loc=(0.0, 0.21, 0.525), radius=1.0, scale=(0.276, 0.212, 0.218)),
        Part('belly', 'sphere', loc=(0.0, -0.06, 0.405), radius=1.0, scale=(0.265, 0.36, 0.14)),
        Part('shoulder', 'sphere', loc=(0.17, -0.34, 0.45), radius=1.0, scale=(0.105, 0.125, 0.155), mirror=True),
        Part('haunch', 'sphere', loc=(0.16, 0.27, 0.47), radius=1.0, scale=(0.115, 0.145, 0.175), mirror=True),
        Part('tailroot', 'tube', loc=TAIL_POINTS[0], to=TAIL_POINTS[1], radius=0.074, r2=0.068),
        Part('tail', 'tube', loc=TAIL_POINTS[1], to=TAIL_POINTS[2], radius=0.068, r2=0.05),
        Part('plume', 'sphere', loc=TAIL_POINTS[2], radius=1.0, scale=(0.064, 0.066, 0.068)),
    ]
    for leg in LEGS:
        ps.extend(leg_parts(leg))
    return ps


def all_parts() -> list[Part]:
    return head_parts() + torso_parts()


def body_extras() -> list[bpy.types.Object]:
    """The ear slabs and the hooves' toes (new objects on every call; the build consumes them)."""
    out = [RP.ear_slab(s) for s in (1, -1)]
    for leg, (x, y) in LEGS.items():
        out.extend(RP.hoof_toes(x, y - 0.012))
    out.extend(BD.clump_meshes(scarf_push))
    return out


def scarf_push(P: np.ndarray, r: np.ndarray) -> np.ndarray:
    """How far each beard point must move forward to clear the scarf's band (the scarf wraps under the beard)."""
    e1, e2, n = RP.scarf_axes()
    q = P - RP.SCARF_C
    h = q @ n
    inplane = q - np.outer(h, n)
    rho = np.linalg.norm(inplane, axis=1)
    beta = np.arctan2(inplane @ e2, inplane @ e1)
    outer = scarf_body_radius(beta) + RP.SCARF_T * 1.22 + 0.006
    near = np.abs(h) < RP.SCARF_W * 0.55 + 0.008 + r
    deficit = np.clip(outer + r + 0.005 - rho, 0.0, None) * near
    fwd = np.clip(-inplane[:, 1] / np.maximum(rho, 1e-6), 0.35, 1.0)
    return deficit / fwd


# ----------------------------------------------------------------------------- the analytic coat (props sit on it)
def _inside(p: np.ndarray, parts=None) -> np.ndarray:
    """Union of the body's spheres and capsules (no rotated parts): a point-in-body test for placing the scarf."""
    parts = parts if parts is not None else [q for q in all_parts() if q.kind in ('sphere', 'capsule', 'tube') and not any(r for r in q.rot)]
    ins = np.zeros(len(p), bool)
    for q in parts:
        for sx in ((1, -1) if q.mirror else (1,)):
            if q.kind == 'sphere':
                c = v3(q.loc) * v3((sx, 1, 1))
                r = v3(q.scale) * q.radius
                ins |= in_ellipsoid(p, c, r) < 1.0
            else:
                a = v3(q.loc) * v3((sx, 1, 1))
                b = v3(q.to) * v3((sx, 1, 1))
                ab = b - a
                t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
                r = q.radius + (((q.r2 if q.r2 is not None else q.radius) - q.radius) * t if q.kind == 'tube' else 0.0)
                ins |= np.linalg.norm(p - (a + t[:, None] * ab), axis=1) < r
    return ins


def _ray_out(origin, dirs, rmax=0.5, parts=None) -> np.ndarray:
    """Distance from `origin` to the body's surface along each direction (bisection on _inside)."""
    lo = np.zeros(len(dirs))
    hi = np.full(len(dirs), rmax)
    for _ in range(26):
        mid = 0.5 * (lo + hi)
        ins = _inside(origin + dirs * mid[:, None], parts)
        lo = np.where(ins, mid, lo)
        hi = np.where(ins, hi, mid)
    return 0.5 * (lo + hi)


def _neck_parts():
    return [q for q in all_parts() if q.name in ('neck', 'nape', 'neckbase', 'withers', 'chest', 'jaw', 'shoulder')]


def scarf_body_radius(beta: np.ndarray) -> np.ndarray:
    """The coat's distance from the scarf's centre round the band's plane (smoothed round the loop)."""
    e1, e2, _n = RP.scarf_axes()
    d = np.cos(beta)[:, None] * e1 + np.sin(beta)[:, None] * e2
    r = _ray_out(RP.SCARF_C, d, 0.45, _neck_parts())
    # smooth round the loop, then a little fur under the band
    k = np.exp(-0.5 * (np.arange(-12, 13) / 5.0) ** 2)
    k /= k.sum()
    rp = np.concatenate([r[-12:], r, r[:12]])
    return np.convolve(rp, k, mode='same')[12:-12] + 0.012


END_AZ = math.radians(30)       # the hanging end lies this far round from the front toward the left


def scarf_body_point(z: float):
    """The coat's surface on the chest's front-left diagonal at height z, and its outward normal."""
    c = v3((0.0, -0.33, z))
    d = v3((math.sin(END_AZ), -math.cos(END_AZ), 0.0))
    parts = [q for q in all_parts() if q.name in ('chest', 'neckbase', 'shoulder', 'withers', 'neck')]
    r = float(_ray_out(c, d[None, :], 0.5, parts)[0])
    p = c + d * r
    # the normal: a finite-difference gradient of the distance field along neighbouring rays
    eps = 0.01
    pu = c + v3((0, 0, eps)) + d * float(_ray_out(c + v3((0, 0, eps)), d[None, :], 0.5, parts)[0])
    rot = v3((math.sin(END_AZ + 0.08), -math.cos(END_AZ + 0.08), 0.0))
    ps = c + rot * float(_ray_out(c, rot[None, :], 0.5, parts)[0])
    nrm = np.cross(ps - p, pu - p)
    nrm /= max(np.linalg.norm(nrm), 1e-9)
    if nrm @ d < 0:
        nrm = -nrm
    return p + nrm * 0.03, nrm          # 3 cm of coat under it


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    """hi_* / lo_*: the two horns, their rope bands and the scarf (band, knot, end and fringe), joined per kind."""
    tag = 'hi' if high else 'lo'
    attrs = ('part', 'ridge', 'along', 'side', 'grain', 'strand', 'knit')
    out = []
    for s in (1, -1):
        sd = 'L' if s > 0 else 'R'
        horn = RP.horn_mesh(f'{tag}_horn{sd}', s, high, quick)
        ropes = RP.rope_mesh(f'{tag}_rope{sd}', s, high, quick)
        for o in [horn] + ropes:
            for a in attrs:
                if a not in o.data.attributes:
                    S.add_attr(o, a, np.zeros(len(o.data.vertices)))
        out.append(horn)
        out.append(RP.join(ropes, f'{tag}_rope{sd}', attrs))
    band = RP.scarf_band(f'{tag}_scarf', high, quick, scarf_body_radius)
    ends = RP.scarf_end(f'{tag}_scarfend', high, quick, scarf_body_point)
    for o in [band] + ends:
        for a in attrs:
            if a not in o.data.attributes:
                S.add_attr(o, a, np.zeros(len(o.data.vertices)))
    out.append(band)
    out.append(RP.join(ends, f'{tag}_scarfend', attrs))
    for o in out:
        o.data.validate(verbose=False)
    return out


# ----------------------------------------------------------------------------- zones
def leg_masks(p: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    out = {}
    for leg, (lx, ly) in LEGS.items():
        r = np.hypot(x - lx, (y - ly) * 0.9)
        top = 0.36 if leg[0] == 'F' else 0.38
        out[leg] = (r < 0.13) & (z < top)
    return out


def scarf_mask(p: np.ndarray, pad: float = 0.0, above: float = 0.0) -> np.ndarray:
    """Under the scarf's band (and the knot): no cards, short locks. `above` widens it toward the head (fur rooted
    there combs down over the band)."""
    e1, e2, n = RP.scarf_axes()
    q = p - RP.SCARF_C
    h = q @ n
    band = (h > -(RP.SCARF_W * 0.5 + 0.02 + pad)) & (h < RP.SCARF_W * 0.5 + 0.02 + pad + above)
    rr = np.linalg.norm(q - np.outer(h, n), axis=1)
    return band & (rr < 0.36)


def end_mask(p: np.ndarray, pad: float = 0.0) -> np.ndarray:
    """Behind the hanging end on the chest."""
    az = np.arctan2(p[:, 0], -(p[:, 1] + 0.33))
    return (np.abs(az - END_AZ) < 0.3 + pad * 3) & (p[:, 2] < 0.67) & (p[:, 2] > 0.655 - RP.END_LEN - 0.07) & (p[:, 1] < -0.4)


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    el = RP.ear_lookup(p)
    ear = el['on']
    head = ((in_ellipsoid(p, (0.0, -0.47, 1.0), (0.24, 0.3, 0.27)) < 1.0) & (z > 0.84)) | ear
    BD.build_clumps(scarf_push)
    bl = BD.lookup(p)
    beard_z = bl['on'] & (bl['u'] > 0.08)
    muzzle = in_ellipsoid(p, *MUZZLE) < 1.0
    nose = in_ellipsoid(p, tuple(NOSE_C), (0.05, 0.035, 0.035)) < 1.0
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = head & (y < -0.52) & (z > 0.88) & (z < 1.12) & (ax < 0.16) & ~ear
    crown = head & (z > 1.12) & ~ear
    cheek = head & (ax > 0.07) & (z < 0.97) & (y < -0.47) & ~ear & ~muzzle
    brow = brow_soft(p, 0.02, 1.25) > 0.5
    chin = head & (z < 0.905) & (y < -0.56)
    horn_root = np.zeros(len(p), bool)
    for s in (1, -1):
        hr = v3(RP.HORN_CTRL[0]) * v3((s, 1, 1))
        horn_root |= np.linalg.norm(p - (hr + v3((0.0, 0.0, 0.05))), axis=1) < 0.11
    legs = leg_masks(p)
    leg = np.zeros(len(p), bool)
    for m in legs.values():
        leg |= m
    leg &= ~head
    hoof = leg & (z < RP.HOOF_H + 0.006)
    sock = leg & (z >= RP.HOOF_H - 0.004) & (z < SOCK_Z[1])
    sole = z < 0.006
    tail = (~head) & (~leg) & (((p - v3(TAIL_BASE)) @ v3(TAIL_DIR)) > 0.0) & (y > 0.34) & (z > 0.55)
    torso = ~head & ~leg & ~tail & ~beard_z
    belly = torso & (z < np.interp(y, [-0.5, -0.3, 0.0, 0.3, 0.42], [0.42, 0.37, 0.35, 0.37, 0.44]))
    back = torso & (z > 0.62)
    chest = torso & (y < -0.3) & (z < 0.7)
    neck = torso & (z > 0.62) & (y < -0.2)
    scarf = scarf_mask(p) & ~head
    send = end_mask(p)
    return {'ear': ear, 'ear_u': el['u'], 'ear_v': el['v'], 'ear_lining': el['lining'], 'head': head, 'muzzle': muzzle,
            'nose': nose, 'eye_d': eye_d, 'face': face, 'crown': crown, 'cheek': cheek, 'brow': brow, 'chin': chin,
            'beard': beard_z, 'horn_root': horn_root, 'leg': leg, 'legs': legs, 'hoof': hoof, 'sock': sock, 'sole': sole,
            'toes': hoof, 'paw': leg & (z < SOCK_Z[1]), 'tail': tail, 'torso': torso, 'belly': belly, 'back': back,
            'chest': chest, 'neck': neck, 'scarf': scarf, 'scarf_end': send, 'beard_u': bl['u'], 'beard_th': bl['th'],
            'beard_dir': bl['dir'], 'beard_root': bl['on'] & (bl['u'] <= 0.08), 'mouth_d': mouth_dist(p)}


def mouth_dist(p: np.ndarray) -> np.ndarray:
    """Distance (in the front view) to the smile line, on the front of the muzzle; 1 elsewhere."""
    d = S.polyline_dist(p[:, 0], p[:, 2], mouth_curve())
    return np.where(p[:, 1] < -0.62, d, 1.0)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(z['face'] * 1.0 + z['muzzle'] * 1.0 + (z['eye_d'] < 0.1) * 1.0 + z['hoof'] * 0.85 + z['ear'] * 0.5, 0, 1)


BODY_TRIS = 46000
LITE_PROPS_TRIS = 4000          # the Lite copy keeps more of the horns, rope and scarf (default 2400)


# ----------------------------------------------------------------------------- how the fur lies
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    k = len(p)
    down = np.tile(v3((0, 0, -1)), (k, 1))
    # head: back from the nose over the crown, down the sides of the face
    g = norm(p - v3((0.0, -0.74, 0.93)))
    wd = smooth(1.02, 0.9, zz)[:, None] * smooth(0.04, 0.1, np.abs(x))[:, None]
    g_head = norm(g * (1 - wd) + down * wd * 1.2)
    # the crown's tuft stands up and back
    g_head = np.where(z['crown'][:, None], norm(v3((0, 0.5, 1.0)) + np.stack([x * 3, np.zeros(k), np.zeros(k)], 1)), g_head)
    # brows: combed out from the middle of the face
    g_head = np.where(z['brow'][:, None], norm(np.stack([np.sign(x), np.full(k, 0.15), np.full(k, 0.25)], 1)), g_head)
    # cheeks and the beard: down, gathering toward the beard's point
    g_beard = norm(np.stack([-x * 1.2, np.full(k, -0.08), np.full(k, -1.0)], 1))
    g_head = np.where((z['cheek'] | z['chin'])[:, None], norm(g_beard + v3((0, 0.3, 0))), g_head)
    # ears: out along the ear
    ear_d = np.stack([np.sign(x) * RP.EAR_DIR[0], np.full(k, RP.EAR_DIR[1]), np.full(k, RP.EAR_DIR[2])], 1)
    g_head = np.where(z['ear'][:, None], ear_d, g_head)
    # body: a parting along the spine, the long coat hangs down the sides and back toward the tail
    side = np.clip(np.abs(n[:, 0]) * 1.4, 0, 1)[:, None]
    part = np.stack([np.sign(x) * 0.7, np.full(k, 0.55), np.full(k, -0.25)], 1)
    g_torso = norm(part * (1 - side) + v3((0.0, 0.32, -1.0)) * side)
    # the neck and chest: down (the shaggy front)
    g_torso = np.where((z['chest'] | z['neck'])[:, None] & (n[:, 1] < -0.2)[:, None], norm(v3((0.0, -0.15, -1.0)) + np.stack([x * 0.8, np.zeros(k), np.zeros(k)], 1)), g_torso)
    g = np.where(z['torso'][:, None], g_torso, g_head)
    g = np.where(z['belly'][:, None], norm(v3((0.0, 0.2, -1.0)) + np.stack([x * 0.6, np.zeros(k), np.zeros(k)], 1)), g)
    g = np.where(z['leg'][:, None], norm(v3((0.0, 0.08, -1.0)) + np.stack([(x - np.sign(x) * 0.18) * 0.5, np.zeros(k), np.zeros(k)], 1)), g)
    g = np.where(z['beard'][:, None], norm(z['beard_dir'] * 1.0 + v3((0.0, 0.0, -0.25))), g)
    # the socks: soft fluff, out and down from the leg (round 1: icicle spikes)
    leg_axis = np.zeros((k, 3))
    for lg, (lx, ly) in LEGS.items():
        m = z['legs'][lg][:, None]
        leg_axis = np.where(m, np.stack([x - lx, y - ly, np.zeros(k)], 1), leg_axis)
    g = np.where(z['sock'][:, None], norm(norm(leg_axis) * 0.9 + down * 0.55), g)
    radial = norm(np.stack([x, y - TAIL_POINTS[-1][1] + 0.05, zz - TAIL_POINTS[-1][2] + 0.05], 1))
    g_tail = norm(np.tile(v3(TAIL_DIR), (k, 1)) * 0.7 + radial * 0.5)
    g = np.where(z['tail'][:, None], g_tail, g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


LOCK_TEMPLATES = {'head': (7, 11, 3, 0.22), 'body': (5, 11, 4, 0.26)}


def head_lock_params(p, n):
    """Short fur on the face, longer on the crown and cheeks; the brows thick and short; nothing on the muzzle's
    nose or round the eyes."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.06)
    W = np.full(k, 0.0115)
    lift = np.full(k, _rad(3.0))
    L = np.where(z['face'], 0.036, L)
    W = np.where(z['face'], 0.0085, W)
    L = np.where(z['muzzle'], 0.017, L)
    W = np.where(z['muzzle'], 0.0075, W)
    lift = np.where(z['muzzle'], _rad(0.5), lift)
    L = np.where(z['crown'], 0.07, L)
    W = np.where(z['crown'], 0.014, W)
    lift = np.where(z['crown'], _rad(5.0), lift)
    L = np.where(z['brow'], 0.032, L)
    W = np.where(z['brow'], 0.0105, W)
    lift = np.where(z['brow'], _rad(6.0), lift)
    L = np.where(z['cheek'], 0.08, L)
    W = np.where(z['cheek'], 0.013, W)
    L = np.where(z['chin'], 0.03, L)
    L = np.where(z['ear'], 0.03, L)
    W = np.where(z['ear'], 0.008, W)
    near_eye = smooth(EYE_R * 1.1, EYE_R * 1.75, z['eye_d'])
    L = L * (0.45 + 0.55 * near_eye)
    W = W * (0.6 + 0.4 * near_eye)
    nose_pad = in_ellipsoid(p, tuple(NOSE_C), (0.058, 0.04, 0.042)) < 1.0
    smile = (p[:, 1] < -0.655) & (p[:, 2] < NOSE_C.z - 0.012) & (p[:, 2] > NOSE_C.z - 0.09) & (np.abs(p[:, 0]) < 0.06)
    skip = ~z['head'] | z['beard'] | nose_pad | smile | (z['eye_d'] < EYE_R * 1.08) | z['ear_lining']
    L = _short_across(p, n, z, L, keep=z['brow'])
    spacing = np.where(z['muzzle'], W * 0.45, W * 0.55)
    return np.where(skip, np.nan, spacing), L, W, lift, z


def body_lock_params(p, n):
    """The long, wavy coat: big pointed locks on the body, long ones on the beard, medium on the legs."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.11)
    W = np.full(k, 0.022)
    lift = np.full(k, _rad(4.0))
    L = np.where(z['back'], 0.1, L)
    L = np.where(z['belly'], 0.12, L)
    L = np.where(z['beard'], 0.12, L)
    W = np.where(z['beard'], 0.016, W)
    lift = np.where(z['beard'], _rad(3.0), lift)
    upper = z['leg'] & (p[:, 2] > SOCK_Z[1])
    L = np.where(z['leg'], np.where(upper, 0.075, 0.05), L)
    W = np.where(z['leg'], np.where(upper, 0.016, 0.013), W)
    lift = np.where(z['sock'], _rad(12.0), lift)
    L = np.where(z['tail'], 0.08, L)
    W = np.where(z['tail'], 0.016, W)
    L = np.where(z['scarf'], 0.045, L)
    skip = (z['head'] & ~z['beard']) | z['hoof'] | z['sole']
    L = _short_across(p, n, z, L, keep=z['beard'] | (z['leg'] & (nut_mask(p, z) >= 0.5)))
    return np.where(skip, np.nan, W * 0.62), L, W, lift, z


def _short_across(p, n, z, L, keep):
    """Round 2: a lock whose tip would land on the other colour (a cream flank lock hanging over the saddle patch or
    the chestnut legs) is cut short, so the chestnut reads solid and its edge stays crisp; `keep` (leg fur over the
    socks, the beard) may hang over."""
    tip = p + flow(p, n, z) * L[:, None] * 0.85
    zt = zones(tip)
    # the beard hangs in front of the chest: a chest lock's tip near it is still over the cream chest (the face's
    # locks do see it: a cream chin or cheek lock over the beard is cut short)
    face = z['head'] | z['beard'] | z['beard_root']
    zt['beard'] = zt['beard'] & face
    zt['beard_root'] = zt['beard_root'] & face
    cream_over_nut = (nut_mask(p, z) < 0.5) & (nut_mask(tip, zt) > 0.55)
    return np.where(cream_over_nut & ~keep, L * 0.45, L)


CARD_LAYERS = 3
TUFT_SHAPE = {'template': (9, 16, 3, 0.2), 'thickness': 0.38, 'bury': 0.14}   # a fuller forelock
CARD_SHADE = 0.9
CARD_COLOUR_FROM = 'skin'
# 3b: the shared AO treatment: a light blur, then a floor (round 3: narrow slots between the beard's clumps and the
# forelock's crowded roots baked near black, dark specks in the beard and marks under the forelock)
AO_FLOOR = 0.35
AO_SOFTEN = 1.5


def card_params(p, n, layer: int):
    """Soft fur cards for the shaggy outline. Layer 0 covers the coat; layer 1 the long fringes (the chest, the belly,
    the backs of the legs, the cheeks, the socks); layer 2 the beard and the tail plume."""
    z = zones(p, n)
    k = len(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    head = z['head']
    # round 2: no chest cards behind the beard's front silhouette or just under the band (deep in the beard's and the
    # scarf's shadow they came out grey and poked out at the beard's edges)
    bw = 0.145 * np.clip((zz - 0.455) / 0.31, 0.0, 1.0) ** 0.8
    behind_beard = ~head & ~z['beard'] & (np.abs(x) < bw + 0.045) & (y < -0.45) & (zz > 0.42) & (zz < 0.8)
    ear_tip = (np.abs(x) > 0.2) & (zz > 0.84) & (y < -0.3)      # 3b: past the ear lookup's reach, still ear
    covered = ((scarf_mask(p, 0.05, 0.02) & ~head) | behind_beard | z['scarf_end'] | z['horn_root'] | z['ear_lining']
               | z['sole'] | z['hoof'] | ear_tip)
    # 3b: a beard card ends inside the beard (round 3: long cards at its point hung past it as dark spikes)
    beard_len = np.clip((zz - 0.475) * 0.85, 0.0, 1.0)
    if layer == 0:
        L = np.where(head, 0.04, 0.1)
        W = np.where(head, 0.032, 0.056)
        lift = np.where(head, _rad(3), _rad(7))
        L = np.where(z['crown'], 0.05, L)
        lift = np.where(z['crown'], _rad(4), lift)
        under = (~head) & (n[:, 2] < -0.15)
        L = np.where(under, 0.065, L)
        lift = np.where(under, _rad(3), lift)
        # 3b: no cards under the belly line at all (white icicle points along it)
        skip_under = (~head) & (n[:, 2] < -0.3) & ~z['leg']
        L = np.where(z['cheek'], 0.06, L)
        L = np.where(z['ear'], 0.032, L)
        W = np.where(z['ear'], 0.024, W)
        L = np.where(z['leg'], 0.07, L)
        W = np.where(z['leg'], 0.04, W)
        L = np.where(z['tail'], 0.08, L)
        L = np.where(z['beard'], np.minimum(0.11, beard_len), L)
        W = np.where(z['beard'], 0.04, W)
        sp = np.where(head, 0.025, 0.021)
        sp = np.where(z['leg'] | z['tail'], 0.02, sp)
        sp = np.where(z['beard'], 0.024, sp)
        skip = (z['face'] | z['muzzle'] | z['nose'] | (z['eye_d'] < 0.085) | z['brow'] | (z['chin'] & (y < -0.6))
                | (z['leg'] & (zz < SOCK_Z[1] + 0.01)) | covered | (n[:, 2] < -0.5) | skip_under | (z['beard'] & (L < 0.035)))
    elif layer == 1:
        L = np.full(k, 0.13)
        W = np.full(k, 0.06)
        lift = np.full(k, _rad(10))
        sp = np.full(k, 0.03)
        fr_chest = z['chest'] & (zz < 0.62)
        fr_belly = z['belly'] & (zz < 0.42) & (n[:, 2] > -0.2)
        fr_side = z['torso'] & (np.abs(n[:, 0]) > 0.55) & (zz < 0.56) & (zz > 0.3)
        fr_neck = z['neck'] & ~z['scarf'] & (zz > 0.7) & (n[:, 1] > 0.15)         # the nape only (round 1: whiskers by the ears)
        leg_back = np.zeros(k, bool)
        for lg, (lx, ly) in LEGS.items():
            leg_back |= z['legs'][lg] & ((y > ly) | (np.abs(x) > np.abs(lx) + 0.03)) & (zz > SOCK_Z[1])
        socks = z['sock'] & (zz > SOCK_Z[0] + 0.045)
        cheek = z['cheek'] & (y > -0.6)
        L = np.where(fr_belly, 0.1, L)
        lift = np.where(fr_belly, _rad(5), lift)
        L = np.where(leg_back, 0.09, L)
        W = np.where(leg_back, 0.045, W)
        L = np.where(socks, 0.026, L)
        W = np.where(socks, 0.07, W)
        lift = np.where(socks, _rad(10), lift)
        sp = np.where(socks, 0.016, sp)
        L = np.where(cheek, 0.06, L)
        W = np.where(cheek, 0.05, W)
        lift = np.where(cheek, _rad(14), lift)
        sp = np.where(cheek, 0.015, sp)
        fringe = fr_chest | fr_belly | fr_side | fr_neck | leg_back | socks | cheek
        skip = ~fringe | z['face'] | z['muzzle'] | (z['eye_d'] < 0.1) | z['beard'] | z['tail'] | covered
    else:
        L = np.full(k, 0.15)
        W = np.full(k, 0.046)
        lift = np.full(k, _rad(4))
        sp = np.full(k, 0.03)
        beard = z['beard']
        tail = z['tail']
        L = np.where(beard, np.minimum(0.095, beard_len), L)
        W = np.where(beard, 0.055, W)
        sp = np.where(beard, 0.022, sp)
        beard = beard & (beard_len >= 0.035)
        L = np.where(tail, 0.08, L)
        W = np.where(tail, 0.064, W)
        lift = np.where(tail, _rad(18), lift)
        sp = np.where(tail, 0.02, sp)
        brows = z['brow'] & z['head']
        L = np.where(brows, 0.032, L)
        W = np.where(brows, 0.036, W)
        lift = np.where(brows, _rad(20), lift)
        sp = np.where(brows, 0.009, sp)
        skip = ~(beard | tail | brows) | covered
    # no cards across the cream / chestnut border (a cream card over chestnut fur glitters at the edge)
    nut = nut_mask(p, z)
    skip = skip | ((nut > 0.08) & (nut < 0.92) & ~z['beard'])
    lower_face = head & (zz < 0.95) & (y < -0.5) & (nut < 0.5)
    skip = skip | lower_face | ((z['cheek'] | z['chin']) & (nut < 0.5) & (layer > 0))
    # 3b: the card's whole length (and a little more) must stay on its own colour (cream belly cards hung over the
    # chestnut legs as white flecks)
    tip = p + flow(p, n, z) * L[:, None] * 1.25
    skip = skip | ((np.abs(nut_mask(tip, zones(tip)) - nut) > 0.45) & ~z['beard'] & ~z['brow'])
    return np.where(skip, np.nan, sp), L, W, lift, z


# ----------------------------------------------------------------------------- the crown tuft
def tuft_frames(surface: bpy.types.Object):
    """A spiky cream forelock between the horn roots (1-hero.png, 2-turnaround.png front)."""
    bvh = BVHTree.FromObject(surface, bpy.context.evaluated_depsgraph_get())
    P, N, F, L, W, lift = [], [], [], [], [], []
    rng = np.random.default_rng(5)
    spots = []
    for row, (yy, n_, half, ln, lf) in enumerate(((-0.51, 3, 0.03, 0.075, 18), (-0.49, 4, 0.045, 0.09, 22), (-0.468, 5, 0.058, 0.1, 26),
                                                   (-0.445, 6, 0.065, 0.11, 30), (-0.42, 5, 0.06, 0.105, 32), (-0.395, 4, 0.05, 0.095, 34),
                                                   (-0.37, 3, 0.04, 0.085, 34))):
        for i in range(n_):
            xx = 0.0 if n_ == 1 else -half + 2 * half * i / (n_ - 1)
            spots.append((xx + rng.uniform(-0.006, 0.006), yy + rng.uniform(-0.006, 0.006), xx / half * 14 if half else 0.0, ln * 0.8, lf * 0.95))
    for x, y, fan, ln, lf in spots:
        hit = bvh.ray_cast(Vector((x, y, 1.6)), Vector((0, 0, -1)))
        if hit[0] is None:
            continue
        p = np.array(hit[0])
        nn = np.array(hit[1])
        a = math.radians(fan)
        f = np.array([math.sin(a) * 0.4, -0.92, 0.35])
        f = f - nn * (f @ nn)
        P.append(p)
        N.append(nn)
        F.append(f / np.linalg.norm(f))
        L.append(ln * rng.uniform(0.9, 1.1))
        W.append(0.04)
        lift.append(math.radians(lf))
    return S.lock_frames(np.array(P), np.array(N), np.array(F), np.array(L), np.array(W), np.array(lift), np.random.default_rng(77), None, jitter_deg=6)


# ----------------------------------------------------------------------------- the markings
def _noise3(p: np.ndarray, f: float, seed: int) -> np.ndarray:
    """A cheap smooth noise (sum of sines) in −1..1, deterministic."""
    rng = np.random.default_rng(seed)
    out = np.zeros(len(p))
    for _ in range(5):
        d = rng.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        out += np.sin((p @ d) * f * rng.uniform(0.7, 1.4) + rng.uniform(0, 6.3))
    return out / 5 * 1.6


SADDLE = {  # per side: blob centres and radii of the chestnut flank patch (turnaround side and back, hero)
    1: [((0.13, 0.11, 0.72), (0.085, 0.12, 0.07)), ((0.2, 0.15, 0.62), (0.1, 0.12, 0.1)), ((0.255, 0.17, 0.5), (0.08, 0.1, 0.1)),
        ((0.26, 0.12, 0.42), (0.06, 0.07, 0.06)), ((0.12, 0.28, 0.7), (0.07, 0.07, 0.06))],
    -1: [((-0.12, 0.03, 0.73), (0.09, 0.1, 0.07)), ((-0.2, 0.08, 0.62), (0.1, 0.12, 0.1)), ((-0.245, 0.13, 0.5), (0.08, 0.09, 0.09)),
         ((-0.12, 0.25, 0.68), (0.07, 0.07, 0.07))],
}
WITHERS = [((0.15, -0.15, 0.74), (0.09, 0.07, 0.06)), ((-0.13, -0.13, 0.75), (0.07, 0.06, 0.05))]


def nut_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """0 cream … 1 chestnut, at the roots (a lock is one colour)."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    nz = _noise3(p, 34.0, 3) * 0.16 + _noise3(p, 90.0, 4) * 0.07
    nut = np.zeros(len(p))
    # the brows
    nut = np.maximum(nut, brow_soft(p, 0.06))
    # the beard and the cheeks (mutton chops) beside the cream muzzle, down to the chin
    cheek_line = 0.945 + 0.015 * smooth(0.09, 0.15, ax) + 0.25 * np.clip(y + 0.55, 0.0, 0.15)
    chops = (y < -0.38) & (ax > 0.052 + 0.045 * smooth(0.95, 0.88, zz)) & (zz < cheek_line + nz * 0.08) & (zz > 0.78)
    chops &= ~z['ear']
    chops &= ~(in_ellipsoid(p, MUZZLE[0], tuple(r * 1.05 for r in MUZZLE[1])) < 1.0)
    nut = np.maximum(nut, chops * 1.0)
    nut = np.maximum(nut, z['beard'] * 1.0)
    nut = np.maximum(nut, z['beard_root'] * smooth(0.025, 0.05, ax + (0.875 - zz).clip(0, None)))
    # the legs: chestnut from under the coat to the socks
    for lg, (lx, ly) in LEGS.items():
        on = z['legs'][lg] & ~z['head']
        top = LEG_NUT_TOP + nz * 0.25
        nut = np.maximum(nut, on * smooth(SOCK_Z[1] - 0.004, SOCK_Z[1] + 0.012, zz + nz * 0.08) * smooth(top + 0.02, top - 0.02, zz))
    # the haunches' backs down to the hocks (back view)
    for s in (1, -1):
        hb = ell_soft(p, (0.16 * s, 0.37, 0.4), (0.1, 0.08, 0.12), 0.1) * (y > 0.3)
        nut = np.maximum(nut, smooth(0.35, 0.55, hb + nz))
    # the saddle patches, the withers
    for s, blobs in SADDLE.items():
        for c, r in blobs:
            q = ell_soft(p, c, r, 0.1)
            nut = np.maximum(nut, smooth(0.35, 0.55, q + nz))
    for c, r in WITHERS:
        nut = np.maximum(nut, smooth(0.35, 0.55, ell_soft(p, c, r, 0.1) + nz) * ~z['head'])
    # the tail: chestnut at the root and along its top, the plume's tip cream
    if 'tail' in z:
        along = (p - v3(TAIL_BASE)) @ v3(TAIL_DIR) / TAIL_LEN
        nut = np.maximum(nut, z['tail'] * smooth(0.75, 0.55, along + nz * 0.3))
    nut = np.maximum(nut, smooth(0.35, 0.55, ell_soft(p, (0.0, 0.33, 0.69), (0.08, 0.07, 0.07), 0.1) + nz))
    # never on the muzzle, the face's middle or the ears
    clear = in_ellipsoid(p, MUZZLE[0], tuple(r * 1.08 for r in MUZZLE[1])) < 1.0
    clear |= z['ear'] | z['crown']
    nut = np.where(clear & ~z['beard'], 0.0, nut)
    return np.clip(nut, 0.0, 1.0)


def light_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """0 coat cream … 1 the lighter cream: the face, the muzzle, the crown's tuft, the socks, the ears."""
    zz = p[:, 2]
    lt = np.maximum(ell_soft(p, (0.0, -0.58, 1.0), (0.15, 0.12, 0.12), 0.3), ell_soft(p, MUZZLE[0], tuple(r * 1.1 for r in MUZZLE[1]), 0.15))
    lt = np.maximum(lt, z['crown'] * 0.7)
    lt = np.maximum(lt, z['sock'] * smooth(SOCK_Z[1] + 0.01, SOCK_Z[1] - 0.02, zz))
    lt = np.maximum(lt, z['ear'] * 0.6)
    return np.clip(lt, 0, 1)


_MASKS: dict[str, tuple] = {}


def _masks_of(ob, root: np.ndarray, pos: np.ndarray, kind: np.ndarray, tpos: np.ndarray):
    if ob.name not in _MASKS:
        zr = zones(root)
        nut = nut_mask(root, zr)
        lt = light_mask(root, zr)
        lock = kind > 0.5
        if lock.any():
            # only the very tip of a lock crossing a border softens toward the colour under it. Round 2: the goat's long
            # locks hang over the next colour (chestnut leg fur over the cream socks, the saddle's fur over the flank,
            # the beard's tips past its clumps); a strong blend painted their tips pale and the cards sampled that
            zp = zones(pos[lock])
            cp = nut_mask(pos[lock], zp)
            kk = 0.15 * smooth(0.6, 1.0, tpos[lock])
            keep = (zr['beard'] | zr['beard_root'] | zr['brow'] | zr['leg'])[lock]
            kk = np.where(keep, 0.0, kk)
            nut[lock] = nut[lock] * (1 - kk) + cp * kk
        _MASKS[ob.name] = (nut, lt, zr)
    return _MASKS[ob.name]


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    col = colours(pal)
    root = S.attr_array(ob, 'root').astype(np.float64)
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    pos = co.reshape(-1, 3).astype(np.float64)
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    lrand = S.attr_array(ob, 'lrand').astype(np.float64)
    nut, lt, zr = _masks_of(ob, root, pos, kind, tpos)
    base = lin(col['coat'])[None, :] * (1 - lt[:, None]) + lin(col['light'])[None, :] * lt[:, None]
    nutc = np.tile(lin(col['nut'])[None, :], (len(pos), 1))
    nutc = np.where(zr['brow'][:, None], lin(col['brow'])[None, :], nutc)
    rgb = base * (1 - nut[:, None]) + nutc * nut[:, None]
    # the ear's lining: pink skin, a cream rim
    lining = zr['ear_lining'] * smooth(0.95, 0.7, np.abs(zr['ear_v'])) * smooth(0.04, 0.16, zr['ear_u']) * smooth(0.98, 0.85, zr['ear_u'])
    rgb = rgb * (1 - lining[:, None]) + lin(col['lining'])[None, :] * lining[:, None]
    # the hooves
    hoof = zr['hoof'] * smooth(RP.HOOF_H + 0.004, RP.HOOF_H - 0.006, pos[:, 2])
    rgb = rgb * (1 - hoof[:, None]) + lin(col['hoof'])[None, :] * hoof[:, None]
    # each lock: a darker root, lighter tip, a little variation
    shade = 0.84 + 0.2 * tpos + 0.1 * (lrand - 0.5)
    # the beard: lighter chestnut toward each lock's tip (round 3: matte, with highlights, not a streaky orange slab)
    shade = np.where(zr['beard'], 0.82 + 0.34 * tpos + 0.08 * (lrand - 0.5), shade)
    shade = np.where(kind < 0.5, 1.0, shade)
    is_lock = kind > 0.5
    warm = np.where(is_lock, 1.0 - tpos, 0.35)[:, None] * (1 - nut[:, None]) * (1 - hoof[:, None]) * (1 - lining[:, None])
    rgb = rgb * (1 - 0.1 * warm * v3((0.0, 0.25, 0.9))[None, :])
    rough = np.where(is_lock, 0.56 + 0.24 * np.abs(tpos - 0.45), 0.66)
    coat = np.where(is_lock, 0.12, 0.05)
    glossy = ell_soft(pos, tuple(NOSE_C), (0.046, 0.028, 0.032), 0.1)
    rough = rough * (1 - glossy) + 0.25 * glossy
    coat = coat * (1 - glossy) + 0.7 * glossy
    rough = rough * (1 - hoof) + 0.26 * hoof
    coat = coat * (1 - hoof) + 0.55 * hoof
    rough = rough * (1 - lining) + 0.55 * lining
    rough = np.where(zr['beard'] | zr['beard_root'], 0.8, rough)
    coat = np.where(zr['beard'] | zr['beard_root'], 0.0, coat)
    return {'paint': rgb, 'nut': nut, 'shade': shade, 'hoof': hoof, 'rough': np.stack([np.ones(len(pos)), rough, coat], axis=1)}


def prop_arrays(ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
    """The horns (chestnut, darker in the growth rings' grooves, lighter on the bands, a fine grain), the rope (golden,
    dark between the strands), the scarf (red, darker between the stitches) and its fringe."""
    col = colours(pal)
    part = S.attr_array(ob, 'part')
    ridge = S.attr_array(ob, 'ridge').astype(np.float64)
    along = S.attr_array(ob, 'along').astype(np.float64)
    grain = S.attr_array(ob, 'grain').astype(np.float64)
    strand = S.attr_array(ob, 'strand').astype(np.float64)
    knit = S.attr_array(ob, 'knit').astype(np.float64)
    n = len(part)
    co = np.empty(n * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    pos = co.reshape(-1, 3).astype(np.float64)
    rgb = np.zeros((n, 3))
    rough = np.full(n, 0.5)
    coat = np.zeros(n)
    horn = np.abs(part - RP.PART_HORN) < 0.1
    if horn.any():
        r = ridge[horn]
        g = np.clip(grain[horn], -1.5, 1.5)
        # the root darker where it meets the fur, the tip a touch darker and smoother
        # one keratin colour; only the narrow grooves darken and the very crests wear lighter (round 2 preview:
        # wide light and dark bands read as stripes)
        c = np.tile(lin(col['horn'])[None, :], (int(horn.sum()), 1))
        worn = smooth(0.93, 1.0, r) * 0.22
        c = c * (1 - worn[:, None]) + lin(col['horn_light'])[None, :] * worn[:, None]
        groove = smooth(0.08, 0.0, r) * 0.45
        c = c * (1 - groove[:, None]) + lin(col['horn_dark'])[None, :] * groove[:, None]
        # lengthwise grain: the same striations the high mesh carries, plus a slow mottle
        c = c * (1.0 + 0.16 * g + 0.05 * _noise3(pos[horn], 30.0, 10))[:, None]
        rgb[horn] = c
        rough[horn] = 0.9 - 0.08 * smooth(0.75, 1.0, r)
        coat[horn] = 0.0
    rope = np.abs(part - RP.PART_ROPE) < 0.1
    if rope.any():
        st = strand[rope]
        c = lin(col['rope_dark'])[None, :] * (1 - smooth(0.15, 0.7, st))[:, None] + lin(col['rope'])[None, :] * smooth(0.15, 0.7, st)[:, None]
        c = c * (1.0 + 0.08 * _noise3(pos[rope], 300.0, 12))[:, None]
        rgb[rope] = c
        rough[rope] = 0.92
        coat[rope] = 0.0
    sc = np.abs(part - RP.PART_SCARF) < 0.1
    fr = np.abs(part - RP.PART_FRINGE) < 0.1
    for m, kmix in ((sc, 1.0), (fr, 0.85)):
        if not m.any():
            continue
        kn = np.clip(knit[m], 0, 1)
        c = lin(col['scarf_dark'])[None, :] * (1 - smooth(0.12, 0.75, kn))[:, None] + lin(col['scarf'])[None, :] * smooth(0.12, 0.75, kn)[:, None]
        c = c * (1 - (smooth(0.75, 1.0, kn) * 0.25)[:, None]) + lin(col['scarf_light'])[None, :] * (smooth(0.75, 1.0, kn) * 0.25)[:, None]
        rgb[m] = c * kmix
        rough[m] = 0.82
        coat[m] = 0.0
    rc = np.stack([np.ones(n), rough, coat], axis=1)
    return rgb, rc


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'nut', a['nut'])
        S.add_attr(ob, 'shade', a['shade'])
        S.add_attr(ob, 'hoof', a['hoof'])
        for vid, vpal in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), paint_arrays(ob, vpal)['paint'])
    for ob in props:
        rgb, rc = prop_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        for vid, vpal in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), prop_arrays(ob, vpal)[0])


# ----------------------------------------------------------------------------- carving (the high source only)
def mouth_curve() -> list[tuple[float, float]]:
    """A small smile under the nose: a short centre line down from the nose, then a gentle curve up at both ends."""
    mid = NOSE_C.z - 0.054
    pts = []
    for k in range(-14, 15):
        t = k / 14
        x = 0.036 * t
        zc = mid + 0.012 * t * t + 0.006 * max(0.0, abs(t) - 0.7) / 0.3
        pts.append((x, zc))
    return pts


def closed_lid(co: np.ndarray):
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax, ay = EYE_R * 0.98 * EYE_SPREAD, EYE_R * 1.06 * EYE_SPREAD
        r2 = (xe / ax) ** 2 + (ye / ay) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * EYE_R
        th = 0.0022 + 0.0016 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    front = smooth(-0.62, -0.68, y)
    md = S.polyline_dist(x, z, mouth_curve())
    philtrum = np.exp(-((np.abs(x)) / 0.0022) ** 2) * (z < NOSE_C.z - 0.02) * (z > NOSE_C.z - 0.054)
    groove = np.maximum(np.exp(-(md / 0.0027) ** 2), philtrum) * front * (z < NOSE_C.z - 0.015) * (z > 0.85)
    nos = np.zeros_like(x)
    for s in (1, -1):
        dd = np.sqrt(((x - 0.017 * s) / 1.5) ** 2 + (z - (NOSE_C.z - 0.006)) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.006) ** 2))
    nos *= smooth(NOSE_C.y + 0.02, NOSE_C.y + 0.008, y)
    brow = brow_soft(co, 0.4)
    bulge, lash = closed_lid(co)
    # the hooves: a fine growth texture and a rim where the hoof meets the sock
    hoof = (z < RP.HOOF_H + 0.004) & (np.min([np.hypot(x - lx, y - ly) for lx, ly in LEGS.values()], axis=0) < 0.11)
    hz = np.sin(z * 900.0 + np.sin(x * 140.0) * 2) * hoof * smooth(0.0, 0.01, z)
    disp = -0.0022 * groove - 0.0045 * nos + 0.0055 * brow + 0.0032 * bulge - 0.0011 * lash + 0.00025 * hz
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    import bmesh
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * 0.98 * EYE_SPREAD, v.co.y * EYE_R * 1.06 * EYE_SPREAD, v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((EYE_R * 0.98, EYE_R * 1.06, EYE_R * EYE_DEPTH[0])))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """A big brown iris (CONTENT's eye colour at its rim, warmer toward the pupil), a large dark pupil, white showing
    at the corners, two catchlights toward the key light, and the dark upper lash line."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    eye_hex = PALETTE['eye']
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    rx, ry = x, y
    # the iris sits a touch toward the nose and low, like the pictures
    ix = nb.math('SUBTRACT', rx, nb.math('MULTIPLY', side, -0.04))
    iy = nb.math('ADD', ry, 0.03)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.74), nb.math('DIVIDE', iy, 0.8), 0.0))
    warm = C.mix_hex(eye_hex, PALETTE['accent'], 0.3)
    amber = C.mix_hex(warm, '#A86A3C', 0.22)
    iris = nb.ramp(ri, [(0.0, C.lin('#0D0907')), (0.44, C.lin('#0D0907')), (0.5, C.lin(C.shade_hex(eye_hex, 0.9))),
                        (0.62, C.lin(warm)), (0.8, C.lin(amber)), (0.93, C.lin(warm)), (0.985, C.lin(eye_hex)),
                        (1.0, C.lin(C.shade_hex(eye_hex, 0.6))), (1.04, C.lin('#F3EEE6')), (1.6, C.lin('#F3EEE6'))])
    # the sclera shades toward the lids
    shade = nb.math('MULTIPLY', nb.smooth(nb.vmath('LENGTH', nb.comb(rx, ry, 0.0)), 0.7, 1.0), 0.25)
    c = nb.mix(nb.math('MULTIPLY', shade, nb.smooth(ri, 1.0, 1.05)), iris, nb.rgb(C.lin('#C9BFB4')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.22), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.27), 1.15), 0.0)), 0.19, 0.16)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.25), nb.math('ADD', ry, 0.3), 0.0)), 0.07, 0.055)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', rx, side), 0.2, 0.9), 0.08)
    lash = nb.smooth(nb.math('ADD', ry, outer), 0.56, 0.66)
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the bake material (per pixel details)
def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the painted attribute × each lock's shade; then the crisp marks by position: the nose, the smile,
    the closed lids and their lash line, scuffs on the hooves."""
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 0.5)
    c = nb.attribute(attr).outputs['Color']
    shade = nb.attribute('shade').outputs['Fac']
    c = nb.mix(1.0, c, nb.comb(shade, shade, shade), blend='MULTIPLY')
    nose = nb.math('MAXIMUM', _ell(nb, pos, (NOSE_C.x, NOSE_C.y + 0.002, NOSE_C.z + 0.007), (0.05, 0.03, 0.025), 0.08),
                   _ell(nb, pos, (NOSE_C.x, NOSE_C.y - 0.002, NOSE_C.z - 0.012), (0.028, 0.026, 0.02), 0.08))
    c = nb.mix(nose, c, nb.rgb(C.lin(NOSE_HEX)))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 2.2, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(MOUTH_HEX)))
    lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
    c = nb.mix(nb.math('MULTIPLY', lid, 0.2), c, nb.rgb((0.0, 0.0, 0.0)))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    # hoof scuffs: lighter scratches and a darker sole edge
    hoof = nb.attribute('hoof').outputs['Fac']
    sc = nb.noise(pos, 38.0, 4.0, 0.62)
    scr = nb.smooth(sc, 0.58, 0.68)
    c = nb.mix(nb.math('MULTIPLY', hoof, nb.math('MULTIPLY', scr, 0.35)), c, nb.rgb(C.lin('#6A5A4E')))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the rig
SCARF_POINTS = None     # filled by rig_p (from the scarf's geometry)


def _scarf_chain() -> list[tuple[float, float, float]]:
    P, _N = RP.end_path(scarf_body_point)
    top = P[0] + v3((0.0, 0.0, 0.02))
    mid = P[len(P) // 2]
    bot = P[-1] + (P[-1] - P[-2]) / max(np.linalg.norm(P[-1] - P[-2]), 1e-9) * RP.FRINGE[1]
    return [tuple(map(float, top)), tuple(map(float, mid)), tuple(map(float, bot))]


def rig_p() -> dict:
    er = RP.EAR_ROOT
    return {
        'hip': (0.0, 0.24, 0.53),
        'chest': (0.0, -0.3, 0.56),
        'head_c': tuple(HEAD_C),
        'head_r': 0.155,
        'ear_base': tuple(map(float, er)),
        'ear_dir': tuple(map(float, RP.EAR_DIR)),
        'ear_len': RP.EAR_LEN,
        'tail_base': tuple(TAIL_BASE),
        'tail_dir': tuple(TAIL_DIR),
        'tail_len': TAIL_LEN,
        'tail_bones': 2,
        'tail_points': TAIL_POINTS,
        'legs': {leg: (lx, ly, 0.47 if leg[0] == 'F' else 0.49) for leg, (lx, ly) in LEGS.items()},
        'knee_back': 0.035,
        'leg_radius': 0.12,
        'stride': 0.2,
        'hooves': True,
        'strike_style': 'charge',             # head down below the withers, the horns lead (5-poses attack)
        # the beard and the scarf end keep hanging when the head jerks (counter) and never fan out (cap, degrees)
        'manes': [{'name': nm, 'parent': 'head', 'points': pts, 'counter': 1.0, 'cap': 12.0} for nm, pts in BEARD_CHAINS.items()]
                 + [{'name': 'scarf', 'parent': 'chest', 'points': _scarf_chain(), 'counter': 0.4, 'cap': 80.0}],
        'props': [{'name': 'horns', 'parent': 'head', 'head': (0.0, -0.42, 1.12), 'tail': (0.0, -0.36, 1.3)}],
    }


def ear_weights(p: np.ndarray, u: np.ndarray) -> dict[str, np.ndarray]:
    w2 = smooth(0.45, 0.9, u)
    w1 = (1 - w2) * smooth(0.0, 0.3, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def body_weight_regions(co: np.ndarray, names: list[str]):
    z = zones(co)
    regions = []
    for s, tag in ((1, 'L'), (-1, 'R')):
        on = z['ear'] & (np.sign(co[:, 0]) == s)
        if on.any():
            w = ear_weights(co[on], np.clip(z['ear_u'][on], 0, 1))
            regions.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    if z['tail'].any():
        regions.append((z['tail'], U.chain_weights(co[z['tail']], TAIL_POINTS, ['tail.1', 'tail.2'], 'hips')))
    bd = z['beard']
    if bd.any():
        # the beard's mass follows its chains (its root stays on the jaw and chin): the middle on `beard`, the chops
        # on `beardL` / `beardR`, blended by where each clump roots along the jaw
        blend = BD.chain_blend(z['beard_th'][bd])
        acc: dict[str, np.ndarray] = {}
        for nm, pts in BEARD_CHAINS.items():
            bones = [f'{nm}.{i + 1}' for i in range(len(pts) - 1)]
            w = U.chain_weights(co[bd], pts, bones, 'head', fade=(0.05, -0.05))
            for b, wv in w.items():
                acc[b] = acc.get(b, 0.0) + wv * blend[nm]
        regions.append((bd, acc))
    # the hooves ride their hoof bones rigidly (the proxy body has no hooves; its nearest skin is the sock's)
    for leg, m in z['legs'].items():
        hv = m & (co[:, 2] < RP.HOOF_H - 0.004)
        if hv.any() and f'foot.{leg}' in names:
            regions.append(U.rigid(hv, f'foot.{leg}'))
    return regions


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """Flat colours for the shared shape preview: coat, lighter coat, chestnut, the ear linings and the hooves."""
    col = colours(PALETTE)
    z = zones(co, vn)
    nut = nut_mask(co, z)
    lt = light_mask(co, z)
    rgb = lin(col['coat'])[None, :] * (1 - lt[:, None]) + lin(col['light'])[None, :] * lt[:, None]
    rgb = rgb * (1 - nut[:, None]) + lin(col['nut'])[None, :] * nut[:, None]
    lining = z['ear_lining'] * smooth(0.95, 0.7, np.abs(z['ear_v']))
    rgb = rgb * (1 - lining[:, None]) + lin(col['lining'])[None, :] * lining[:, None]
    hoof = z['hoof'] * smooth(RP.HOOF_H + 0.004, RP.HOOF_H - 0.006, co[:, 2])
    rgb = rgb * (1 - hoof[:, None]) + lin(col['hoof'])[None, :] * hoof[:, None]
    nose = in_ellipsoid(co, tuple(NOSE_C), (0.045, 0.03, 0.031)) < 1.0
    return np.where(nose[:, None], lin(NOSE_HEX)[None, :], rgb)


def prop_weight_regions(co: np.ndarray, attr, names: list[str]):
    part = attr('part')
    side = attr('side')
    horn = (np.abs(part - RP.PART_HORN) < 0.1) | (np.abs(part - RP.PART_ROPE) < 0.1)
    scarf = (np.abs(part - RP.PART_SCARF) < 0.1) | (np.abs(part - RP.PART_FRINGE) < 0.1)
    band = scarf & (np.abs(side) < 0.5)
    end = scarf & (np.abs(side) >= 0.5)
    regions = [U.rigid(horn, 'prop.horns')]
    if band.any():
        # the band follows the neck at the nape and the chest in front
        e1, e2, n = RP.scarf_axes()
        q = co[band] - RP.SCARF_C
        a = smooth(-0.08, 0.12, q @ e2)
        regions.append((band, {'neck': 0.12 + 0.28 * a, 'chest': 0.88 - 0.28 * a}))
    if end.any():
        regions.append((end, U.chain_weights(co[end], _scarf_chain(), ['scarf.1', 'scarf.2'], 'chest', fade=(0.06, -0.04))))
    return regions


CLIP_CALM = {   # round 1: the beard flew out sideways in hit and hit_heavy; it is long and heavy, so it mostly hangs
    '*': {'ear': 0.6, 'beard': 0.5, 'beardL': 0.5, 'beardR': 0.5, 'scarf': 0.8},
    'ko': {'ear': 0.2, 'beard': 0.25, 'beardL': 0.25, 'beardR': 0.25, 'scarf': 0.4, 'tail': 0.5},
    'hit': {'ear': 0.4, 'beard': 0.3, 'beardL': 0.3, 'beardR': 0.3, 'scarf': 0.6},
    'hit_heavy': {'ear': 0.3, 'beard': 0.25, 'beardL': 0.25, 'beardR': 0.25, 'scarf': 0.45},
    'win': {'ear': 0.4, 'beard': 0.4, 'beardL': 0.4, 'beardR': 0.4},
    'strike': {'ear': 0.3, 'beard': 0.4, 'beardL': 0.4, 'beardR': 0.4, 'scarf': 1.8},
    'sidestep_l': {'beard': 0.35, 'beardL': 0.35, 'beardR': 0.35, 'scarf': 0.6},
    'sidestep_r': {'beard': 0.35, 'beardL': 0.35, 'beardR': 0.35, 'scarf': 0.6},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the brown iris, pupil, catchlights and the upper lash line baked into '
             'the atlas; the thick chestnut brows, the nose and the small smile are baked into the body. No face sheet and no '
             'morphs: expressions in clips\' `faces` are hints only. Blinking scales the blink bones (play `blink` over any '
             'clip): each lens squashes onto the closed lid\'s lash line and sinks into the head, showing the closed lid.')

REVIEW = {
    'centre': (0.0, -0.06, 0.66),
    'size': 1.62,
    'head': ((0.0, -0.47, 1.0), 0.95),
}
