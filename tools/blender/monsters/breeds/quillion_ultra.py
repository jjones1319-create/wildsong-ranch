"""Quillion at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md, the
"Biped plan" section).

A small hedgehog fencer standing upright on two short, sturdy legs: precise, dashing and honourable
(chatgpt/monsters/10-quillion/). A big round head with a cream face, big glossy dark eyes, a small black nose and a neat
confident smile, small round ears; a crest of chunky chestnut quills with cream tips sweeping back from the forehead
over the head and down the back; a round cream belly; neat cream hands with three fingers and a thumb, small cream feet;
a short crimson wool cape fastened at the neck with a small round clasp; and the tail: one long polished silver quill
curved like a rapier, rising behind it from a ruff of quills. The hands are empty: the tail is the blade.

- The shape: quillion_form.py (measured on 2-turnaround.png; the hero wins where they disagree).
- The quills and the blade: quillion_quills.py (props: rigid clumps that ride the skin at their roots).
- The cape, the collar and the clasp: quillion_cape.py (props; the cape rides three spring chains).
- The coat: short soft lying fur (cream face, belly, hands and feet; chestnut limbs) and long quill-like locks on the
  spine-bed under the quills, all baked; soft fur cards break the limbs' and the cheeks' outlines.

Colours: CONTENT §2.2 #6 (#8C5A3C quills and fur / #EED9C4 face, belly, hands / #C0392B cape, quill #C9D3DD / #1E1E1E
eyes). Champion Quillion (src/art/monster/variants.ts; secrets.ts `champion-quillion`, "a gold cape"): #6B4A2E /
#F1E4D0 / #E8B923 / #1E1E1E, the blade staying silver, with a fine embroidered edge on the gold cape
(variant-champion-quillion.png). Parts the palette has no colour for are derived from it (`colours`): the inner ears
and the blush (cream toward the crimson), the brows, claws, pads and nose (the chestnut toward the eye colour), the
iris (the eye colour warmed toward the chestnut, as the pictures' brown eyes), the stitches (cream). The clasp is the
one exception the palette can't make: the pictures' brass, made from the breed's own Champion gold and its chestnut.

Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.kdtree import KDTree

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3
from monsters.breeds import quillion_cape as K
from monsters.breeds import quillion_form as F
from monsters.breeds import quillion_quills as Q

ID = 'quillion'
LOOK = 'quillion-ultra'
PLAN = 'biped'
HEIGHT_UNITS = 135

CHAMPION_GOLD = '#E8B923'
PALETTE_BASE_ACCENT = '#C0392B'     # the inner ears and blush are pink in every variant
PALETTE = {'body': '#8C5A3C', 'belly': '#EED9C4', 'accent': '#C0392B', 'eye': '#1E1E1E', 'quill': '#C9D3DD',
           'clasp': C.mix_hex(CHAMPION_GOLD, '#8C5A3C', 0.45)}
VARIANTS = {'champion-quillion': {'body': '#6B4A2E', 'belly': '#F1E4D0', 'accent': CHAMPION_GOLD, 'eye': '#1E1E1E',
                                  'quill': '#C9D3DD', 'clasp': C.mix_hex(CHAMPION_GOLD, '#6B4A2E', 0.62), 'embroidery': True}}


def colours(pal: dict) -> dict:
    """Every derived colour of a palette (the base or a variant)."""
    fur, cream, cape, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    return {
        'fur': fur, 'cream': cream, 'cape': cape, 'eye': eye, 'blade': pal['quill'], 'clasp': pal['clasp'],
        'fur_dark': C.shade_hex(fur, 0.62),                  # the quills' roots, the shaded fur (the chestnut, darker: warm)
        'fur_light': C.mix_hex(fur, cream, 0.22),            # the forehead's lighter fur
        'quill_tip': cream,
        'quill_mid': C.mix_hex(fur, cream, 0.38),
        'brow': C.shade_hex(fur, 0.52),
        'ear_in': C.mix_hex(cream, PALETTE_BASE_ACCENT, 0.38),     # polish: the base pink in every variant
        'blush': C.mix_hex(cream, PALETTE_BASE_ACCENT, 0.42),
        'nose': C.mix_hex(eye, fur, 0.12),
        'mouth': C.mix_hex(eye, fur, 0.2),
        'claw': C.mix_hex(fur, eye, 0.62),
        'pad': C.mix_hex(fur, eye, 0.5),
        'iris': C.mix_hex(eye, fur, 0.62),
        'iris_deep': C.mix_hex(eye, fur, 0.3),
        'stitch': C.shade_hex(cape, 0.68),                   # round 3: a darker tone-on-tone stitch
        'cape_dark': C.mix_hex(cape, eye, 0.28),
        'embroidery': C.mix_hex(cape, fur, 0.5),
    }


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


# ----------------------------------------------------------------------------- the body
def all_parts() -> list[Part]:
    return F.all_parts()


BODY_TRIS = 44000
ATLAS_DENSITY = {'lo_eyes': 1.4}


def texel_k(co: np.ndarray) -> np.ndarray:
    """lo_body's texel density per face (build 1's atlas left the face blurry): the face and the ears 1.6, the hands
    and feet 1.2, the spine-bed under the quills 0.55 (mostly hidden), the rest 1."""
    z = zones(co)
    k = np.ones(len(co))
    k = np.where(z['quill'] > 0.5, 0.55, k)
    k = np.where(z['hand'] | z['foot'], 1.2, k)
    k = np.where(z['head'] & (z['quill'] < 0.5), 1.6, k)
    return k
VOXELS = {'hi': 0.0032, 'hi_quick': 0.0055, 'lo': 0.005}


# ----------------------------------------------------------------------------- carving (the high source; the ear cups on both)
def smile_z(x: np.ndarray) -> np.ndarray:
    """The smile's height across the muzzle's front (x in metres): a gentle curve whose corners turn up."""
    a = np.clip(np.abs(x) / F.SMILE_W, 0, 1.4)
    return 0.5385 + 0.0055 * a ** 2 + 0.0075 * smooth(0.65, 1.05, a)


def mouth_mask(co: np.ndarray) -> np.ndarray:
    """0..1 on the mouth line: the smile across the muzzle's front and a short philtrum from the nose."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    front = smooth(-0.13, -0.155, y)
    on = np.abs(x) < F.SMILE_W * 1.06
    g = np.exp(-((z - smile_z(x)) / 0.0024) ** 2) * front * on
    phil = np.exp(-(x / 0.0016) ** 2) * (z < F.NOSE_C[2] - 0.009) * (z > 0.538) * smooth(-0.17, -0.19, y)
    return np.clip(np.maximum(g, phil), 0, 1)


LID_LASH, LID_DROP, LID_W = 0.06, 0.15, 0.95


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens: the soft closed lid and its lash line, shown only while a blink sinks the lens (Puddlepup P1.2)."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = F.eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax, ay = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1]
        r2 = (xe / ax) ** 2 + (ye / ay) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * F.EYE_R
        th = 0.003 + 0.0025 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 0.92) & (r2 < 1.1)     # round 3: kept under the lens (it showed as ticks at the corners)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(0.92, 0.78, np.abs(xn)))
    return bulge, lash


def ear_cup(co: np.ndarray) -> np.ndarray:
    """0..1 inside each ear's cup (its forward-facing side), for the hollow and the pink lining."""
    out = np.zeros(len(co))
    for s in (1, -1):
        c = v3(F.mirror(F.EAR_C, s))
        n = norm(v3(F.mirror(F.EAR_N, s))[None])[0]
        up = v3(F.mirror(F.EAR_UP, s))
        up = up - n * float(up @ n)
        up /= np.linalg.norm(up)
        sd = np.cross(up, n)
        q = co - c
        a, b, h = q @ sd, q @ up, q @ n
        r = np.sqrt((a / (F.EAR_SIZE[1] * 0.78)) ** 2 + ((b - 0.002) / (F.EAR_SIZE[2] * 0.8)) ** 2)
        out = np.maximum(out, smooth(1.0, 0.7, r) * smooth(-0.002, 0.004, h))
    return out


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    groove = mouth_mask(co)
    # the nostrils: two small dents under the nose's front
    nos = np.zeros(len(co))
    for s in (1, -1):
        dd = np.sqrt(((x - 0.0075 * s) / 1.4) ** 2 + (z - (F.NOSE_C[2] - 0.004)) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.0032) ** 2))
    nos *= smooth(F.NOSE_C[1] + 0.012, F.NOSE_C[1] + 0.004, y)
    # the fingers' and the toes' clefts
    cleft = np.zeros(len(co))
    for s in (1, -1):
        tc = F.toe_centres(s)
        for a, b in zip(tc[:-1], tc[1:]):
            m = (a + b) * 0.5
            d = np.sqrt(((x - m.x) / 0.0028) ** 2 + ((y - (m.y - 0.006)) / 0.02) ** 2)
            cleft = np.maximum(cleft, np.exp(-d ** 2) * (z < 0.035) * (z > 0.003))
    cup = ear_cup(co)
    bulge, lash = closed_lid(co)
    disp = -0.003 * groove - 0.003 * nos - 0.0025 * cleft - 0.0012 * lash - 0.0065 * cup
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)
    S.add_attr(ob, 'cup', cup)


def carve_low(ob: bpy.types.Object) -> None:
    """The ears' cups reach the silhouette: the low body takes the hollow too."""
    co, vn = S.mesh_arrays(ob)
    cup = ear_cup(co)
    S.set_positions(ob, co - vn * (0.006 * cup)[:, None])


# ----------------------------------------------------------------------------- the eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 32
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    sx, sy, sz = F.EYE_R * F.EYE_SHAPE[0], F.EYE_R * F.EYE_SHAPE[1], F.EYE_R * F.EYE_DEPTH[0]
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = F.eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((sx, sy, sz)))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def blink_pivot(s: int):
    """Behind the lens at the closed lid's lash height: a blink squashes the lens onto the lash line and sinks it."""
    c, _xax, yax, look = F.eye_frame(s)
    return c - yax * (F.EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (F.EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.74, 0.04, 0.2)


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """A big glossy dark eye (4-details 2): a warm off-white rim of sclera (more at the outer corner), a large iris that
    runs from a warm brown ring (the eye colour toward the chestnut) into the #1E1E1E pupil, a thin dark limbal ring,
    a thick dark upper lash line and two crisp catchlights."""
    col = colours(pal or PALETTE)
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    # the iris sits a little toward the nose and down, so the eyes look ahead
    ix = x
    iy = nb.math('ADD', y, 0.04)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 1.0), nb.math('DIVIDE', iy, 1.0), 0.0))
    sclera = C.lin(C.mix_hex('#F7F1EA', col['cream'], 0.5))
    iris = nb.ramp(ri, [(0.0, C.lin(col['eye'])), (0.5, C.lin(col['eye'])), (0.56, C.lin(col['iris_deep'])),
                        (0.78, C.lin(col['iris'])), (0.92, C.lin(C.mix_hex(col['iris'], col['eye'], 0.35))),
                        (0.97, C.lin(col['eye'])), (1.0, C.lin(col['eye'])), (1.06, sclera), (1.6, sclera)])
    # radial fibres in the iris ring
    ang = nb.math('ARCTAN2', iy, ix)
    fib = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 34.0)), 0.5), 0.5),
                  nb.math('MULTIPLY', nb.smooth(ri, 0.55, 0.65), nb.smooth(ri, 0.95, 0.85)))
    c = nb.mix(nb.math('MULTIPLY', fib, 0.18), iris, nb.rgb(C.lin(C.mix_hex(col['iris'], '#E0B890', 0.4))))
    # the sclera shades toward the lids
    shade = nb.math('MULTIPLY', nb.smooth(nb.vmath('LENGTH', nb.comb(x, y, 0.0)), 0.75, 1.0), nb.smooth(ri, 1.0, 1.1))
    c = nb.mix(nb.math('MULTIPLY', shade, 0.35), c, nb.rgb(C.lin('#B8A898')))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', x, nb.math('MULTIPLY', side, 0.22)), nb.math('DIVIDE', nb.math('SUBTRACT', y, 0.32), 1.1), 0.0)), 0.2, 0.16)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', x, nb.math('MULTIPLY', side, 0.2)), nb.math('ADD', y, 0.28), 0.0)), 0.12, 0.095)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', x, side), 0.1, 0.95), 0.16)
    lash = nb.smooth(nb.math('ADD', y, outer), 0.7, 0.8)
    c = nb.mix(lash, c, nb.rgb(C.lin(C.mix_hex(col['eye'], '#000000', 0.3))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- zones
def _head_mask(p: np.ndarray) -> np.ndarray:
    hc, hr = v3(F.HEAD_C), v3(F.HEAD_R)
    return (in_ellipsoid(p, tuple(hc + v3((0.0, -0.03, -0.02))), tuple(hr * v3((1.25, 1.35, 1.2)))) < 1.0) & (p[:, 2] > 0.485)


def _near_segment(p, a, b, r) -> np.ndarray:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / float(ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1) < r


def _zones(p: np.ndarray) -> dict:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    m = lambda q, s: F.mirror(q, s)
    quill = F.quill_zone(p)
    ear = F.ear_dist(p) < 0.05
    head = (_head_mask(p) | ear) & (quill < 0.5)
    muzzle = in_ellipsoid(p, *F.MUZZLE) < 1.25
    nose = in_ellipsoid(p, F.NOSE_C, tuple(r * 1.25 for r in F.NOSE_R)) < 1.0
    eye_d = np.minimum(np.linalg.norm(p - v3(F.EYE_C[1]), axis=1), np.linalg.norm(p - v3(F.EYE_C[-1]), axis=1))
    hand = np.zeros(len(p), bool)
    arm = np.zeros(len(p), bool)
    foot = np.zeros(len(p), bool)
    leg = np.zeros(len(p), bool)
    for s in (1, -1):
        w, h, _ac, _pl = F.hand_frame(s)
        hand |= (np.linalg.norm(p - v3(w + h * 0.025), axis=1) < 0.05) & ((p - v3(w)) @ v3(h) > -0.004)
        arm |= _near_segment(p, m(F.SHOULDER, s), m(F.WRIST, s), 0.055) & (x * s > 0.1)
        foot |= (z < 0.062) & (np.linalg.norm((p - v3(m(F.FOOT_C, s))) * v3((1.0, 0.7, 1.0)), axis=1) < 0.075)
        leg |= _near_segment(p, m(F.LEG_HIP, s), m(F.ANKLE, s), 0.07) & (z < 0.15) & (x * s > 0.02)
    arm &= ~hand
    leg &= ~foot
    toes = foot & (y < -0.07)
    sole = foot & (z < 0.01)
    tt, td = F.tail_param(p)
    tail = (tt > 0.08) & (td < 0.065) & ~head
    # the cream face: the lower face, the cheeks, round the eyes and up to the brows; the chestnut forehead comes down
    # in a soft point between the eyes (3-faces neutral, 2-turnaround front)
    cz = 0.69 - 0.075 * np.exp(-(x / 0.03) ** 2)
    face = head & ~ear & (y < -0.035 - 0.25 * np.clip(0.6 - z, 0, 1)) & (z < cz) & (ax < 0.15)
    face |= head & muzzle
    cheek = head & (ax > 0.06) & (z < 0.62) & (y < 0.0) & ~ear
    chin = head & (z < 0.53) & (y < -0.06)
    # the cream belly: the chest under the collar to the crotch (2-turnaround front and side)
    bel = ((x / (0.098 + 0.02 * smooth(0.42, 0.2, z))) ** 2 + ((z - 0.27) / 0.175) ** 2) < 1.0
    belly = bel & (y < -0.02 - 0.06 * smooth(0.2, 0.0, np.abs(z - 0.27))) & ~head & ~arm & ~hand & (quill < 0.5)
    torso = ~head & ~arm & ~hand & ~leg & ~foot & ~tail
    return {'quill': quill, 'ear': ear, 'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face,
            'cheek': cheek, 'chin': chin, 'hand': hand, 'arm': arm, 'foot': foot, 'leg': leg, 'toes': toes, 'sole': sole,
            'tail': tail, 'tail_t': tt, 'belly': belly, 'torso': torso, 'cup': ear_cup(p)}


_ZCACHE: list = []


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict:
    p = np.asarray(p, np.float64)
    if len(p) < 20000:
        return _zones(p)
    key = (p.shape, float(p[::max(1, len(p) // 251)].sum()), float(p[-1].sum()), float(p[len(p) // 2].sum()))
    for k, v in _ZCACHE:
        if k == key:
            return v
    z = _zones(p)
    _ZCACHE.append((key, z))
    del _ZCACHE[:-6]
    return z


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    return np.clip(z['face'] * 0.9 + z['muzzle'] * 1.0 + (z['eye_d'] < 0.06) * 1.0 + z['toes'] * 0.7 + z['hand'] * 0.7
                   + (z['ear'] * 0.8), 0, 1)


# ----------------------------------------------------------------------------- how the fur lies
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    k = len(p)
    x = p[:, 0]
    # the head: combed back from the nose; the cheeks sweep back, out and a little down
    g = norm(p - v3((0.0, F.NOSE_C[1] - 0.04, F.NOSE_C[2] + 0.01)))
    cheek_dir = norm(np.stack([np.sign(x) * 1.0, np.full(k, 0.35), np.full(k, -0.35)], axis=1))
    wc = (z['cheek'] * smooth(0.06, 0.1, np.abs(x)))[:, None]
    g_head = norm(g * (1 - wc) + cheek_dir * wc)
    # the body: down and a little back; the belly fans down; the limbs down their length
    side = np.clip(np.abs(n[:, 0]) * 1.2, 0, 1)[:, None]
    g_body = norm(v3((0.0, 0.35, -1.0)) * (1 - side) + v3((0.0, 0.25, -1.0)) * side)
    g = np.where(z['head'][:, None], g_head, g_body)
    g = np.where(z['belly'][:, None], np.tile(v3((0.0, 0.1, -1.0)), (k, 1)), g)
    lim = np.zeros((k, 3))
    for s in (1, -1):
        da = norm(v3(F.mirror(F.WRIST, s)) - v3(F.mirror(F.SHOULDER, s)))
        lim = np.where(((z['arm'] | z['hand']) & (np.sign(x) == s))[:, None], np.tile(da, (k, 1)), lim)
    g = np.where((z['arm'] | z['hand'])[:, None], lim, g)
    g = np.where((z['leg'] | z['foot'])[:, None], np.tile(v3((0.0, -0.1, -1.0)), (k, 1)), g)
    tax = norm(v3(F.TAIL_TUBE[1]) - v3(F.TAIL_TUBE[0]))
    g = np.where(z['tail'][:, None], np.tile(tax, (k, 1)), g)
    # the spine-bed: along the quills' sweep
    q = (z['quill'] > 0.5)[:, None]
    g = np.where(q, F.quill_flow(p, n), g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


def head_lock_params(p, n):
    """Short soft fur on the face (finest on the muzzle and round the eyes), fluffier on the cheeks, short velvet on
    the ears' backs; none on the nose, the mouth line, the inner ears or under the eye lenses."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.026)
    W = np.full(k, 0.0078)
    lift = np.full(k, _rad(3.0))
    L = np.where(z['cheek'], 0.04, L)
    W = np.where(z['cheek'], 0.0098, W)
    lift = np.where(z['cheek'], _rad(6.0), lift)
    L = np.where(z['muzzle'], 0.014, L)
    W = np.where(z['muzzle'], 0.0052, W)
    L = np.where(z['ear'], 0.016, L)
    W = np.where(z['ear'], 0.0055, W)
    near_eye = smooth(F.EYE_R * 1.1, F.EYE_R * 1.8, z['eye_d'])
    L = L * (0.5 + 0.5 * near_eye)
    W = W * (0.65 + 0.35 * near_eye)
    lid = (z['eye_d'] < F.EYE_R * 1.04) & z['head']
    L = np.where(lid, 0.012, L)
    W = np.where(lid, 0.005, W)
    lift = np.where(lid, 0.0, lift)
    _b, lash = closed_lid(p)
    skip = (~z['head'] | z['nose'] | (mouth_mask(p) > 0.15) | (z['cup'] > 0.3) | ((z['eye_d'] < F.EYE_R * 1.1) & ~lid)
            | (lid & (lash > 0.08)) | (z['quill'] > 0.5))
    return np.where(skip, np.nan, W * 0.55), L, W, lift, z


def body_lock_params(p, n):
    """The spine-bed under the quills: long quill-like locks (they fill the gaps between the quill props, cream-tipped);
    the cream belly's short soft fur; the chestnut limbs' shaggier fur; the hands' and feet's fine cream fur (none on
    the claws, the pads or the soles)."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.034)
    W = np.full(k, 0.0098)
    lift = np.full(k, _rad(5.0))
    q = z['quill'] > 0.5
    L = np.where(q, 0.072, L)
    W = np.where(q, 0.019, W)
    lift = np.where(q, _rad(9.0), lift)
    L = np.where(z['belly'], 0.03, L)
    W = np.where(z['belly'], 0.0092, W)
    L = np.where(z['arm'] | z['leg'], 0.032, L)
    lift = np.where(z['arm'] | z['leg'], _rad(4.0), lift)
    L = np.where(z['hand'] | z['foot'], 0.013, L)
    W = np.where(z['hand'] | z['foot'], 0.0052, W)
    L = np.where(z['tail'], 0.05, L)
    W = np.where(z['tail'], 0.014, W)
    sp = np.where(q, W * 0.62, W * 0.58)
    claws = _claw_mask(p) > 0.3
    skip = (z['head'] & ~q) | z['sole'] | claws | (z['toes'] & (p[:, 2] < 0.012)) | (collar_dist(p) < 0.045)
    return np.where(skip, np.nan, sp), L, W, lift, z


CARD_LAYERS = 0                # round 3: no fur cards (their edges glinted as pale specks; the Lite copy is clean without)
ATLAS_STRIP = 0
CARD_SHADE = 0.82
AO_FLOOR = 0.5
AO_SOFTEN = 2.5
CARD_COLOUR_FROM = 'paint'


def card_params(p, n, layer: int):
    """Soft fur cards for the outline. Layer 0: the chestnut limbs, the belly's edge and the tail tube (short, shaggy).
    Layer 1: the cream cheeks' fluff (1-hero, 3-faces: the face's widest part) and the chest under the collar. None on
    the spine-bed (the quill props make that outline), the face's middle, the hands, the feet or the inner ears."""
    z = zones(p, n)
    k = len(p)
    x = p[:, 0]
    if layer == 0:
        L = np.full(k, 0.036)
        W = np.full(k, 0.024)
        lift = np.full(k, _rad(10))
        sp = np.full(k, 0.02)
        on = z['arm'] | z['leg']
        skip = ~on | z['hand'] | z['foot'] | (z['quill'] > 0.2) | (cream_soft(p) > 0.02) | (collar_dist(p) < 0.06)
    else:
        L = np.full(k, 0.05)
        W = np.full(k, 0.026)
        lift = np.full(k, _rad(24))
        sp = np.full(k, 0.013)
        fluff = z['cheek'] & (np.abs(x) > 0.085) & (p[:, 1] > -0.1)
        skip = ~fluff | (z['eye_d'] < 0.06) | z['ear'] | (z['quill'] > 0.2)
    return np.where(skip, np.nan, sp), L, W, lift, z


# ----------------------------------------------------------------------------- props: the quills, the blade, the cape
def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    qo = Q.quills_object(f'{tag}_quills', high)
    Q.orient_out(qo)
    bo = Q.blade_object(f'{tag}_blade', high)
    Q.orient_out(bo)
    return [qo, bo, K.cape_object(f'{tag}_cape', high), K.collar_object(f'{tag}_collar', high), K.clasp_object(f'{tag}_clasp', high)]


LITE_PROPS_TRIS = 7000


def preview_prop_colour(name: str):
    col = colours(PALETTE)
    return {'quills': col['fur'], 'blade': col['blade'], 'cape': col['cape'], 'collar': col['cape'], 'clasp': col['clasp']}.get(name, col['fur'])


# ----------------------------------------------------------------------------- paint
def _claw_mask(p: np.ndarray) -> np.ndarray:
    out = np.zeros(len(p))
    for s in (1, -1):
        for b, t, r in F.finger_tips(s):
            d = (t - b).normalized()
            c = t + d * (r * 0.35)
            out = np.maximum(out, ell_soft(p, tuple(c), (r * 1.05, r * 1.05, r * 1.05), 0.25))
        for tc in F.toe_centres(s):
            out = np.maximum(out, ell_soft(p, (tc.x, tc.y - 0.012, 0.011), (0.0085, 0.009, 0.0085), 0.25))
    return out


def _pad_mask(p: np.ndarray) -> np.ndarray:
    out = np.zeros(len(p))
    for s in (1, -1):
        fc = v3(F.mirror(F.FOOT_C, s))
        out = np.maximum(out, ell_soft(p, (fc[0], fc[1] + 0.012, 0.002), (0.024, 0.032, 0.008), 0.15))
        for tc in F.toe_centres(s):
            out = np.maximum(out, ell_soft(p, (tc.x, tc.y + 0.003, 0.002), (0.008, 0.009, 0.006), 0.2))
    return out


def cream_soft(p: np.ndarray) -> np.ndarray:
    """0..1 how cream the coat is (round 2: soft, fur-feathered borders instead of round 1's hard boolean edges): the
    face, cheeks, muzzle and chin, the belly, the hands from the wrist and the feet from the ankle."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    head = (_head_mask(p) & (F.ear_dist(p) > 0.05)).astype(float) * (1.0 - smooth(0.4, 0.6, F.quill_zone(p)))
    cz = 0.69 - 0.075 * np.exp(-(x / 0.03) ** 2)
    yth = -0.035 - 0.25 * np.clip(0.6 - z, 0, 1)
    face = smooth(cz + 0.012, cz - 0.012, z) * smooth(yth + 0.018, yth - 0.018, y) * smooth(0.165, 0.135, ax)
    cheek = smooth(0.05, 0.075, ax) * smooth(0.635, 0.6, z) * smooth(0.015, -0.025, y)
    chin = smooth(0.545, 0.52, z) * smooth(-0.04, -0.07, y)
    c = np.maximum(np.maximum(face, cheek), chin) * head
    c = np.maximum(c, ell_soft(p, F.MUZZLE[0], tuple(r * 1.25 for r in F.MUZZLE[1]), 0.15) * head)
    e = (x / (0.098 + 0.02 * smooth(0.42, 0.2, z))) ** 2 + ((z - 0.27) / 0.175) ** 2
    thr = -0.02 - 0.06 * smooth(0.2, 0.0, np.abs(z - 0.27))
    belly = smooth(1.12, 0.88, e) * smooth(thr + 0.018, thr - 0.018, y) * (z < 0.47)
    c = np.maximum(c, belly * (1.0 - head))
    for s in (1, -1):
        w, h, _ac, _pl = F.hand_frame(s)
        along = (p - v3(w)) @ v3(h)
        near = np.linalg.norm(p - v3(w + h * 0.025), axis=1) < 0.06
        c = np.maximum(c, smooth(-0.014, 0.008, along) * near)
        fc = v3(F.mirror(F.FOOT_C, s))
        nearf = np.linalg.norm((p - fc) * v3((1.0, 0.75, 0.0)), axis=1) < 0.085
        c = np.maximum(c, smooth(0.075, 0.052, z) * nearf)
    return np.clip(c, 0.0, 1.0)


_COLLAR = None


def collar_dist(p: np.ndarray) -> np.ndarray:
    """Distance to the collar's centre line (no locks or cards poke through the collar)."""
    global _COLLAR
    if _COLLAR is None:
        _COLLAR = K.collar_ring(np.linspace(-math.pi, math.pi, 72, endpoint=False))
    d = np.full(len(p), 9.0)
    for i in range(0, len(p), 20000):
        q = p[i:i + 20000]
        d[i:i + 20000] = np.sqrt(((q[:, None, :] - _COLLAR[None]) ** 2).sum(-1)).min(1)
    return d


def body_paint(p: np.ndarray, pal: dict, kind=None, tpos=None, lrand=None, pos=None) -> dict:
    """Per point of a body source: 'paint' (linear RGB), 'shade', 'rough' (1, roughness, coat). `p` is each point's
    root on the skin (locks take the colour under their root; their tips lighten)."""
    col = colours(pal)
    k = len(p)
    z = zones(p)
    fur, cream = lin(col['fur']), lin(col['cream'])
    q = np.clip(z['quill'], 0, 1)[:, None]
    rgb = np.tile(fur, (k, 1))
    # the spine-bed: deeper chestnut
    rgb = rgb * (1 - q * 0.45) + lin(col['fur_dark'])[None] * (q * 0.45)
    creamk = cream_soft(p)
    if pos is not None and kind is not None:
        # a lock that crosses a border blends toward the colour under its tip along its length (Puddlepup P1.2)
        wk = np.where(kind > 0.5, 0.75 + 0.25 * np.clip(tpos, 0, 1), 0.0)
        creamk = creamk * (1 - wk) + cream_soft(pos) * wk
    # soft borders: the face's cream fades into the chestnut forehead; the hands' cream starts at the wrist
    rgb = rgb * (1 - creamk[:, None]) + cream[None] * creamk[:, None]
    # the forehead above the brows, a lighter chestnut
    fh = (z['head'] & ~z['face'] & ~z['ear'] & (p[:, 1] < -0.06)).astype(float) * 0.5
    rgb = rgb * (1 - fh[:, None]) + lin(col['fur_light'])[None] * fh[:, None]
    cup = np.clip(z['cup'] * 1.4, 0, 1)
    rgb = rgb * (1 - cup[:, None]) + lin(col['ear_in'])[None] * cup[:, None]
    claw = _claw_mask(p)
    rgb = rgb * (1 - claw[:, None]) + lin(col['claw'])[None] * claw[:, None]
    pad = _pad_mask(p)
    rgb = rgb * (1 - pad[:, None]) + lin(col['pad'])[None] * pad[:, None]
    nose = ell_soft(p, F.NOSE_C, tuple(r * 1.12 for r in F.NOSE_R), 0.12)
    rgb = rgb * (1 - nose[:, None]) + lin(col['nose'])[None] * nose[:, None]
    shade = np.ones(k)
    rough = np.full(k, 0.72)
    coat = np.full(k, 0.03)
    if kind is not None:
        lock = kind > 0.5
        t = np.clip(tpos, 0, 1)
        # locks: darker roots, lighter tips; on the spine-bed the tips turn cream like the quills'
        # build 1: strong root shade read as grey streaks on the cream face and belly: softer on the cream
        ck = creamk
        shade = np.where(lock, (0.84 + 0.16 * t + 0.08 * (lrand - 0.5)) * (1 - ck) + (0.94 + 0.08 * t + 0.04 * (lrand - 0.5)) * ck, 1.0)
        # the cream locks' roots warm toward a tan instead of greying (round 3: the muzzle's shade read grey-beige)
        warm = np.where(lock, (1 - t) * 0.22, 0.0) * ck
        rgb = rgb * (1 - warm[:, None]) + lin(col['fur_light'])[None] * warm[:, None]
        tip = np.where(lock, smooth(0.6, 0.95, t), 0.0) * q[:, 0] * 0.45
        rgb = rgb * (1 - tip[:, None]) + lin(col['quill_tip'])[None] * tip[:, None]
        rough = np.where(lock, 0.62 + 0.18 * np.abs(t - 0.45), rough)
    glossy = np.maximum(nose, claw * 0.8)
    # the nose, claws and pads a little glossy, never glassy (Nov 13: roughness at least 0.4, coat at most 0.3)
    rough = rough * (1 - glossy) + 0.42 * glossy
    coat = coat * (1 - glossy) + 0.28 * glossy
    rough = rough * (1 - cup) + 0.55 * cup
    return {'paint': rgb, 'shade': shade, 'rough': np.stack([np.ones(k), rough, coat], axis=1)}


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return body_paint(co, PALETTE)['paint']


def _quill_paint(qt: np.ndarray, qrand: np.ndarray, col: dict) -> np.ndarray:
    """A quill: a dark chestnut root, the chestnut body, a cream tip (its length varies per quill)."""
    t = np.clip(qt, 0, 1)
    start = 0.64 + 0.12 * (qrand - 0.5)
    rgb = lin(col['fur_dark'])[None] * (1 - smooth(0.0, 0.35, t))[:, None] + lin(col['fur'])[None] * smooth(0.0, 0.35, t)[:, None]
    mid = smooth(start - 0.12, start, t)
    rgb = rgb * (1 - mid[:, None] * 0.5) + lin(col['quill_mid'])[None] * (mid[:, None] * 0.5)
    tip = smooth(start, start + 0.14, t)
    rgb = rgb * (1 - tip[:, None]) + lin(col['quill_tip'])[None] * tip[:, None]
    return rgb * (0.9 + 0.2 * qrand)[:, None]


def prop_paint(ob: bpy.types.Object, pal: dict) -> np.ndarray:
    col = colours(pal)
    part = S.attr_array(ob, 'part')
    qt = S.attr_array(ob, 'qt').astype(np.float64)
    qrand = S.attr_array(ob, 'qrand').astype(np.float64)
    qside = S.attr_array(ob, 'qside').astype(np.float64)
    n = len(part)
    rgb = np.zeros((n, 3))
    quill = (np.abs(part - Q.PART_QUILL) < 0.5) | (np.abs(part - Q.PART_TAILQ) < 0.5)
    rgb[quill] = _quill_paint(qt[quill], qrand[quill], col)
    blade = np.abs(part - Q.PART_BLADE) < 0.5
    if blade.any():
        # polished silver: brighter along the middle, a touch darker toward the edges, warmer where it leaves the ruff
        # round 2 (4-details 4): polished silver: the base #C9D3DD, a bright highlight along both edges and one darker
        # reflection band down one face (never black chrome), warmer where it leaves the ruff
        qs = qside[blade]
        b = np.tile(lin(C.mix_hex(col['blade'], '#FFFFFF', 0.22)), (int(blade.sum()), 1))
        edge = smooth(0.62, 0.92, np.abs(qs))[:, None]
        b = b * (1 - edge * 0.75) + lin('#FFFFFF')[None] * (edge * 0.75)
        band = (smooth(-0.5, -0.32, qs) * smooth(0.0, -0.18, qs))[:, None]
        b = b * (1 - band * 0.4) + lin(C.shade_hex(col['blade'], 0.7))[None] * (band * 0.4)
        root = smooth(0.08, 0.01, qt[blade])[:, None]
        rgb[blade] = b * (1 - root * 0.5) + lin(col['fur'])[None] * (root * 0.5)
    cloth = (np.abs(part - Q.PART_CAPE) < 0.5) | (np.abs(part - Q.PART_COLLAR) < 0.5)
    rgb[cloth] = lin(C.mix_hex(col['cape'], col['cape_dark'], 0.3))
    clasp = np.abs(part - Q.PART_CLASP) < 0.5
    rgb[clasp] = lin(col['clasp'])
    return rgb


def prop_rough(ob: bpy.types.Object, satin: bool = False) -> np.ndarray:
    part = S.attr_array(ob, 'part')
    qt = S.attr_array(ob, 'qt').astype(np.float64)
    n = len(part)
    rough = np.full(n, 0.6)
    coat = np.full(n, 0.05)
    quill = (np.abs(part - Q.PART_QUILL) < 0.5) | (np.abs(part - Q.PART_TAILQ) < 0.5)
    # build 2: matte keratin (they read as plastic pencils)
    rough[quill] = 0.74 - 0.1 * qt[quill]
    coat[quill] = 0.03
    blade = np.abs(part - Q.PART_BLADE) < 0.5
    rough[blade] = 0.22
    coat[blade] = 0.6
    cloth = (np.abs(part - Q.PART_CAPE) < 0.5) | (np.abs(part - Q.PART_COLLAR) < 0.5)
    # wool: matte; Champion's gold cape a soft satin sheen (VARIANT_ORM)
    rough[cloth] = 0.55 if satin else 0.94
    coat[cloth] = 0.18 if satin else 0.0
    clasp = np.abs(part - Q.PART_CLASP) < 0.5
    rough[clasp] = 0.36
    coat[clasp] = 0.3
    return np.stack([np.ones(n), rough, coat], axis=1)


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        root = S.attr_array(ob, 'root').astype(np.float64)
        kind = S.attr_array(ob, 'kind')
        tpos = S.attr_array(ob, 'tpos').astype(np.float64)
        lrand = S.attr_array(ob, 'lrand').astype(np.float64)
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get('co', co)
        pos = co.reshape(-1, 3).astype(np.float64)
        a = body_paint(root, PALETTE, kind, tpos, lrand, pos)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'shade', a['shade'])
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), body_paint(root, var, kind, tpos, lrand, pos)['paint'])
    for ob in props:
        S.set_colour_attr(ob, 'paint', prop_paint(ob, PALETTE))
        S.set_colour_attr(ob, 'rough', prop_rough(ob))
        S.set_colour_attr(ob, 'rough_champion', prop_rough(ob, satin=True))
        # polish: the blade lifts itself a little out of the body's shadow (it read mid-grey in the game's grey studio)
        S.add_attr(ob, 'glow', np.where(np.abs(S.attr_array(ob, 'part') - Q.PART_BLADE) < 0.5, 1.0, 0.0))
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), prop_paint(ob, var))


# polish: the glow channel, used only by the blade (a faint self-light on the painted silver, far under the bloom
# threshold), so it reads light silver beside the body instead of mid-grey in its shadow
GLOW = {'strength': 0.4, 'tint': None}

# Champion's gold cape takes its own roughness and coat (a satin sheen; the props' `rough_champion`)
VARIANT_ORM = {'champion': {}}


def prop_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """The props per pixel: the cape's stitched hem (a dashed line of pale thread just above the rolled hem, 1-hero and
    4-details 5), and on Champion Quillion's gold cape an embroidered vine band above it (variant-champion-quillion)."""
    col = colours(pal)
    m, nb = new_mat(name)
    c = nb.attribute(attr).outputs['Color']
    part = nb.attribute('part').outputs['Fac']
    cape = nb.math('MULTIPLY', nb.math('GREATER_THAN', part, 3.5), nb.math('LESS_THAN', part, 4.5))
    v = nb.attribute('qt').outputs['Fac']
    u = nb.attribute('qside').outputs['Fac']
    if pal.get('embroidery'):
        mid = nb.math('ADD', 0.86, nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', u, 46.0)), 0.016))
        stem = nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, mid)), 0.0045, 0.002)
        # small leaves on alternate sides of the stem
        side = nb.math('SINE', nb.math('MULTIPLY', u, 92.0))
        lv = nb.math('ADD', mid, nb.math('MULTIPLY', side, 0.022))
        leaf = nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', nb.math('SUBTRACT', v, lv)), 0.009, 0.004),
                       nb.smooth(nb.math('ABSOLUTE', side), 0.55, 0.85))
        emb = nb.math('MULTIPLY', nb.math('MAXIMUM', stem, leaf), cape)
        c = nb.mix(emb, c, nb.rgb(C.lin(col['embroidery'])))
    # the quills: fine strands along each clump (build 2: smooth cones read as plastic), lighter and darker streaks
    # that fade toward the point, and a little shade along the clump's edges
    quill = nb.math('LESS_THAN', part, 2.5)
    qr = nb.attribute('qrand').outputs['Fac']
    ph = nb.math('ADD', nb.math('MULTIPLY', u, 19.0), nb.math('MULTIPLY', qr, 23.0))
    streak = nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', ph), 0.6), nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ph, 2.7)), 0.4))
    sk = nb.math('ADD', 1.0, nb.math('MULTIPLY', nb.math('MULTIPLY', streak, 0.3), nb.smooth(v, 0.98, 0.45)))
    sk = nb.math('MULTIPLY', sk, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', nb.smooth(nb.math('ABSOLUTE', u), 0.6, 1.0), 0.18)))
    sk = nb.math('ADD', nb.math('MULTIPLY', sk, quill), nb.math('SUBTRACT', 1.0, quill))
    c = nb.mix(1.0, c, nb.comb(sk, sk, sk), blend='MULTIPLY')
    band = nb.math('MULTIPLY', nb.smooth(v, 0.935, 0.944), nb.smooth(v, 0.962, 0.953))
    dash = nb.smooth(nb.math('SINE', nb.math('MULTIPLY', u, 260.0)), -0.1, 0.3)
    stitch = nb.math('MULTIPLY', nb.math('MULTIPLY', band, dash), cape)
    c = nb.mix(nb.math('MULTIPLY', stitch, 0.6), c, nb.rgb(C.lin(col['stitch'])))
    # the wool: a fine colour noise in the weave (round 2: it read as flat plastic)
    cloth = nb.math('MULTIPLY', nb.math('GREATER_THAN', part, 3.5), nb.math('LESS_THAN', part, 5.5))
    pos = nb.coords().outputs['Object']
    wn = nb.math('ADD', 0.8, nb.math('MULTIPLY', nb.noise(pos, 120.0, 4.0, 0.65), 0.3))
    wk = nb.math('ADD', nb.math('MULTIPLY', wn, cloth), nb.math('SUBTRACT', 1.0, cloth))
    c = nb.mix(1.0, c, nb.comb(wk, wk, wk), blend='MULTIPLY')
    # the clasp: a dark rim ring so it reads as a disc on the cloth (Champion's gold collar too)
    clasp = nb.math('GREATER_THAN', part, 5.5)
    rim = nb.math('MULTIPLY', nb.smooth(v, 0.84, 0.94), clasp)
    c = nb.mix(nb.math('MULTIPLY', rim, 0.6), c, nb.rgb(C.lin(C.shade_hex(col['clasp'], 0.45))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the paint × each lock's shade, with the face's details per pixel: the brows, the blush, the nose,
    the mouth line, the closed lids' lash lines."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    kind = nb.attribute('kind').outputs['Fac']
    is_body = nb.math('LESS_THAN', kind, 0.5)
    shade = nb.attribute('shade').outputs['Fac']
    c = nb.attribute(attr).outputs['Color']
    c = nb.mix(1.0, c, nb.comb(shade, shade, shade), blend='MULTIPLY')
    # the blush: soft pink under each eye (1-hero, 3-faces)
    blush = None
    for s in (1, -1):
        e = _ell(nb, pos, (0.105 * s, -0.098, 0.566), (0.03, 0.03, 0.02), 0.6)
        blush = e if blush is None else nb.math('MAXIMUM', blush, e)
    c = nb.mix(nb.math('MULTIPLY', blush, 0.55), c, nb.rgb(C.lin(col['blush'])))
    # the brows: thick dark arched strokes above the eyes, rising toward the outer end (2-turnaround front)
    brow = None
    for s in (1, -1):
        for k in range(5):
            t = k / 4
            bx = (0.066 + 0.056 * t) * s
            bz = F.BROW_Z + 0.008 * math.sin(math.pi * t) - 0.002 * t
            by = -0.135 + 0.045 * t ** 1.4
            e = _ell(nb, pos, (bx, by, bz), (0.014, 0.03, 0.0072 - 0.0018 * t), 0.25)
            brow = e if brow is None else nb.math('MAXIMUM', brow, e)
    c = nb.mix(nb.math('MULTIPLY', brow, 0.9), c, nb.rgb(C.lin(col['brow'])))
    c = nb.mix(_ell(nb, pos, F.NOSE_C, tuple(r * 1.1 for r in F.NOSE_R), 0.1), c, nb.rgb(C.lin(col['nose'])))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(mouth, c, nb.rgb(C.lin(col['mouth'])))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.6, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin(col['mouth'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the rig (plans/biped.py)
CAPE_COLUMNS = (('capeR', -0.62), ('capeC', 0.0), ('capeL', 0.62))
CAPES = [{'name': nm, 'parent': 'chest', 'points': K.chain_points(k)} for nm, k in CAPE_COLUMNS]
EAR_LEN = 0.085


def _blade_normal() -> Vector:
    p0, p1, p2 = (Vector(p) for p in F.BLADE_BEZ)
    n = (p1 - p0).cross(p2 - p0).normalized()
    return n if n.x >= 0 else -n


def _chain_pose(targets, face=None) -> list:
    """Tail-bone rotations (x, y, z degrees each, world-aligned relative to the parent at rest, as plans/biped.py keys
    them) that point each bone of the tail along its target world direction (the least turn from its rest direction)."""
    out = []
    w_prev = Matrix.Identity(3)
    for i, tg in enumerate(targets):
        d = Vector(F.TAIL_POINTS[i + 1]) - Vector(F.TAIL_POINTS[i])
        t = Vector(tg).normalized()
        w_i = d.normalized().rotation_difference(t).to_matrix()
        if face is not None and i == len(targets) - 1:
            # roll the blade about its own axis so its flat face looks toward `face` (either side of the face will do)
            n1 = w_i @ _blade_normal()
            nd = Vector(face) - t * Vector(face).dot(t)
            if nd.length > 1e-6:
                nd.normalize()
                if n1.dot(nd) < 0:
                    nd = -nd
                ang = math.atan2(n1.cross(nd).dot(t), n1.dot(nd))
                w_i = Matrix.Rotation(ang, 3, t) @ w_i
        e = (w_prev.transposed() @ w_i).to_euler('XYZ')
        out.append((math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)))
        w_prev = w_i
    return out


def _blade_pose(z12: float, x1: float, target) -> list:
    """Tail-bone rotations (x, y, z degrees each, world-aligned relative to the parent at rest, as plans/biped.py keys
    them) that swing the furry tail round by z12 per bone (lifted x1) and turn the blade toward `target`."""
    r1 = Euler((math.radians(x1), 0.0, math.radians(z12)), 'XYZ').to_matrix()
    r2 = Euler((0.0, 0.0, math.radians(z12)), 'XYZ').to_matrix()
    d_rest = (Vector(F.TAIL_POINTS[3]) - Vector(F.TAIL_POINTS[2])).normalized()
    rmin = d_rest.rotation_difference(Vector(target).normalized()).to_matrix()
    e = ((r1 @ r2).transposed() @ rmin).to_euler('XYZ')
    return [(x1, 0.0, z12), (0.0, 0.0, z12), (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))]


def fencer_poses() -> dict:
    """The fencer's tail poses (5-poses, CONTENT trait En Garde): the guard holds the blade forward and up over the left
    shoulder; the windup raises it high over the shoulder; the salute stands it upright beside the head. Each blade
    stays outside the quill halo (checked numerically against the rest geometry)."""
    # round 3 (the tail now leaves the rump under the cape): each pose names a direction per tail bone, checked
    # numerically against the rest geometry: the guard holds the blade forward and up over the left shoulder; the
    # windup raises it high over the shoulder; the salute stands it upright beside the head; the lunge brings the
    # blade's root round the outside of the left hip to chest height and the blade level, straight ahead
    front = (0.35, -0.94, 0.0)
    return {'guard': _chain_pose([(0.75, 0.25, 0.6), (0.55, -0.35, 0.75), (0.45, -0.75, 0.6)], front),
            'windup': _chain_pose([(0.6, 0.4, 0.7), (0.5, 0.05, 0.85), (0.4, 0.2, 1.0)], front),
            'salute': _chain_pose([(0.7, 0.2, 0.65), (0.6, -0.3, 0.75), (0.35, -0.3, 1.0)], front),
            # the lunge's blade shows its flat face to the side (the in-game strike camera is at 70°)
            'lunge': _chain_pose([(0.7, 0.15, 0.7), (0.6, -0.75, 0.3), (0.06, -1.0, 0.08)], (1.0, 0.0, 0.0))}


def rig_p() -> dict:
    eb = v3(F.EAR_C) - v3(F.EAR_UP) / np.linalg.norm(F.EAR_UP) * 0.042
    return {
        'hip': F.HIP, 'chest': F.CHEST, 'head_c': F.HEAD_C, 'head_r': 0.15,
        'legs': {'hip': F.LEG_HIP, 'knee': F.KNEE, 'ankle': F.ANKLE, 'toe': F.TOE},
        'arms': {'shoulder': F.SHOULDER, 'elbow': F.ELBOW, 'wrist': F.WRIST, 'hand': F.HAND},
        'arm_relax': 12.0,
        'ear_base': tuple(map(float, eb)), 'ear_dir': F.EAR_UP, 'ear_len': EAR_LEN,
        'tail_bones': 3, 'tail_points': F.TAIL_POINTS,
        'capes': CAPES,
        'jaw': {'head': F.JAW_HINGE, 'tail': F.JAW_TIP},
        # the fencing lunge (5-poses attack): the tail swings round the left hip and its upright blade is pushed down
        # toward level (per tail bone: the furry tail keeps its height, clear of the hip; the blade bone −62°), so
        # the blade drives ahead from beside the left hip, rising about 12° toward a target's chest; the blade leans
        # out at rest (the hero), so 160° of swing (not the plan's 175°) aims it straight
        'strike_style': 'thrust', 'thrust_lift': [15.0, 0.0, -50.0], 'thrust_swing': -170.0,
        # round 2: the fencer's battle clips (plans/biped.py `fencer`): en garde, the windup over the shoulder, the
        # lunge, the salute; a longer walking stride; the cape drapes in ko
        'fencer': fencer_poses(), 'stride': 0.2, 'cape_drape': 0.75,
    }


MERGE_INTO_HEAD = ('eye.L', 'eye.R')     # the jaw moves the lower jaw's skin (the smile opens)


def jaw_weights(co: np.ndarray) -> np.ndarray:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    lip = np.where(np.abs(x) < F.SMILE_W, smile_z(x), 0.548 + 0.004 * smooth(F.SMILE_W, 0.075, np.abs(x)))
    return (smooth(-0.095, -0.12, y) * smooth(lip + 0.0015, lip - 0.004, z) * (np.abs(x) < 0.075) * (z > 0.488)
            * _head_mask(co))


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    out = []
    z = zones(co)
    zt = z['tail'] | ((F.tail_param(co)[1] < 0.06) & (F.tail_param(co)[0] > 0.25))
    if zt.any():
        out.append((zt, U.chain_weights(co[zt], F.TAIL_POINTS[:3], ['tail.1', 'tail.2'], 'hips')))
    for tag, s in (('L', 1), ('R', -1)):
        P = rig_p()
        b = v3(F.mirror(P['ear_base'], s))
        d = v3(F.mirror(P['ear_dir'], s))
        d /= np.linalg.norm(d)
        on = (F.ear_dist(co) < 0.064) & (np.sign(co[:, 0]) == s)
        if on.any():
            pts = [tuple(b), tuple(b + d * EAR_LEN * 0.5), tuple(b + d * EAR_LEN)]
            out.append((on, U.chain_weights(co[on], pts, [f'ear.{tag}.1', f'ear.{tag}.2'], 'head', fade=(0.25, 0.05))))
    jw = jaw_weights(co)
    jm = jw > 0.01
    if jm.any() and 'jaw' in names:
        out.append((jm, {'jaw': jw[jm], 'head': 1.0 - jw[jm]}))
    return out


def _root_weights(roots: np.ndarray, names: list[str]) -> dict[str, np.ndarray]:
    """Each root's skin weights: lo_body's, at its nearest vertices (inverse-distance blend of the four nearest), so a
    quill rides the skin it grows from. Without a skinned lo_body (the shape preview) the head and the chest by height."""
    body = bpy.data.objects.get('lo_body')
    if body is None or not body.vertex_groups:
        hz = smooth(0.56, 0.62, roots[:, 2])
        return {'head': hz, 'chest': 1.0 - hz}
    bn, W = S.body_weights(body)
    bco = np.empty(len(body.data.vertices) * 3, np.float32)
    body.data.vertices.foreach_get('co', bco)
    bco = bco.reshape(-1, 3)
    kd = KDTree(len(bco))
    for i, p in enumerate(bco):
        kd.insert(Vector(p), i)
    kd.balance()
    uniq, inv = np.unique(np.round(roots, 6), axis=0, return_inverse=True)
    Wr = np.zeros((len(uniq), len(bn)))
    for i, r in enumerate(uniq):
        hits = kd.find_n(Vector(r), 4)
        ws = np.array([1.0 / max(d, 1e-4) for _c, _j, d in hits])
        ws /= ws.sum()
        for (_c, j, _d), w in zip(hits, ws):
            Wr[i] += w * W[j]
    Wr /= np.maximum(Wr.sum(1, keepdims=True), 1e-9)
    Wv = Wr[inv.ravel()]
    return {b: Wv[:, j] for j, b in enumerate(bn) if b in names and Wv[:, j].max() > 1e-4}


def cape_weights(co: np.ndarray, u: np.ndarray) -> dict[str, np.ndarray]:
    """The cape across its three chains (u: −1 its right edge, 0 the back, +1 its left), each column's chain weights
    blended by how near it is (the stand-in's fin_weight_regions)."""
    w: dict[str, np.ndarray] = {}
    ks = [k for _n, k in CAPE_COLUMNS]
    for c, (nm, kc) in zip(CAPES, CAPE_COLUMNS):
        i = ks.index(kc)
        if i == 0:
            bl = np.clip((ks[1] - u) / (ks[1] - ks[0]), 0, 1)
        elif i == len(ks) - 1:
            bl = np.clip((u - ks[-2]) / (ks[-1] - ks[-2]), 0, 1)
        else:
            bl = np.clip(1.0 - np.abs(u - kc) / (ks[1] - ks[0]), 0, 1)
        cw = U.chain_weights(co, c['points'], [f'{nm}.{j + 1}' for j in range(len(c['points']) - 1)], 'chest')
        for b, v in cw.items():
            w[b] = w.get(b, 0.0) + v * bl
    # round 2: over the shoulder tops the cloth rides the upper arm a little, so a raised arm lifts it
    for s, tag in ((1, 'L'), (-1, 'R')):
        near = smooth(0.15, 0.07, np.linalg.norm(co - v3(F.mirror(F.SHOULDER, s)), axis=1)) * 0.6
        if near.any():
            for b in list(w):
                w[b] = w[b] * (1 - near)
            w[f'upperarm.{tag}'] = w.get(f'upperarm.{tag}', 0.0) + near
    return w


def prop_weight_regions(co: np.ndarray, attr, names: list[str], mesh: str | None = None) -> list:
    part = attr('part')
    out = []
    quill = (np.abs(part - Q.PART_QUILL) < 0.5) | (np.abs(part - Q.PART_TAILQ) < 0.5)
    if quill.any():
        out.append((quill, _root_weights(attr('qroot')[quill].astype(np.float64), names)))
    blade = np.abs(part - Q.PART_BLADE) < 0.5
    if blade.any():
        out.append(U.rigid(blade, 'tail.3'))
    cape = np.abs(part - Q.PART_CAPE) < 0.5
    if cape.any():
        out.append((cape, cape_weights(co[cape], attr('qside')[cape].astype(np.float64))))
    rigid = (np.abs(part - Q.PART_COLLAR) < 0.5) | (np.abs(part - Q.PART_CLASP) < 0.5)
    if rigid.any():
        out.append(U.rigid(rigid, 'chest'))
    return out


# ----------------------------------------------------------------------------- clips
# The tail carries a rigid, upright blade: the plan's lifts (up to 26° per bone in win) tip it forward over the back into
# the quills, so the tail is calm (a sword's sway, not a wag), calmest in the clips that lift it most; the strike keeps
# its full swing; the low, drooping clips keep more (the blade leans back, away from the quills).
_TAIL_CALM = {'idle_happy': 0.15, 'pet': 0.2, 'hop': 0.12, 'celebrate': 0.12,
              'step_fwd': 0.15, 'step_back': 0.15, 'strafe_l': 0.18, 'strafe_r': 0.18, 'sidestep_l': 0.15,
              'sidestep_r': 0.15, 'cast': 0.2, 'shove': 0.3, 'idle_sad': 0.5, 'idle_tired': 0.5, 'idle_sick': 0.5,
              'ko': 0.6, 'sit_down': 1.0, 'sit': 1.0, 'sleep': 1.0}
CLIP_CALM = {
    '*': {'ear': 0.7, 'tail': 0.35},
    'strike': {'ear': 0.4, 'tail': 1.0, 'capeL': 1.7, 'capeC': 0.7, 'capeR': 0.9},
    'walk': {'ear': 0.7, 'tail': 0.35, 'cape': 1.6},
    'hit': {'ear': 0.7, 'tail': 0.5, 'cape': 1.5},
    'hit_heavy': {'ear': 0.7, 'tail': 0.5, 'cape': 1.5},
    'battle_idle': {'ear': 0.7, 'tail': 1.0},
    'win': {'ear': 0.7, 'tail': 1.0},
    **{clip: {'ear': 0.7, 'tail': k} for clip, k in _TAIL_CALM.items()},
}

FACE_NOTE = ('The eyes are glossy dark lenses (lo_eyes) with the brown iris, the pupil, the catchlights and the upper lash '
             'line baked into the body atlas; the brows, the blush, the nose and the smile are baked into the body. No face '
             'sheet and no morphs: expressions in clips\' `faces` are hints only. Blinking scales the blink bones (play '
             '`blink` over any clip): each lens squashes onto the closed lid\'s lash line and sinks into the head. The jaw '
             'moves the lower jaw\'s skin (the smile opens in the happy clips and the strike).')

REVIEW = {'centre': (0.0, 0.08, 0.45), 'size': 1.25, 'head': ((0.0, -0.06, 0.64), 0.52)}
