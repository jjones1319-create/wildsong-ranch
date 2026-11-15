"""Gloomgrin at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9; RECIPE.md, "Biped plan"): the recipe for
`tools/blender/monsters/build_ultra.py`.

A squat, two-legged gargoyle imp carved from charcoal stone; mischievous, cheeky and secretly loyal
(chatgpt/monsters/13-gloomgrin: the card decides the parts, 1-hero the shapes, 2-turnaround the measurements, CONTENT
§2.2 #28 the colours):
  - a big round head with wide jowls and a wide cheeky grin of square teeth (eight upper, seven lower, two lower fangs:
    props set in a carved gap), a small snout, heavy carved stone brows over big glowing amber eyes, stubby curved
    horns (props) and big bat ears out to the sides (in every picture, not on the card: modelled, lined in lilac);
  - round shoulders, long arms with big three-fingered hands and a thumb, short thick legs on big three-toed feet with
    a heel claw; dark stone claws (props);
  - small two-fingered bat wings folded half open behind the shoulders (stone arms and finger struts as props, thin
    stone-leather membranes), a crest of chunky stone spikes from the crown down the spine and the tail (in every
    picture), a curled tail ending in a faceted stone arrowhead (a prop);
  - the whole body cracked into chiselled charcoal plates of mixed sizes (bigger on the back, smaller on the head and
    limbs), lighter stone on the face and in chevron plates down the belly; faint violet runes etched over the body,
    the wings and the arrowhead, glowing softly (the glow map), and glowing eyes.
No fur, no cards, no tuft: the detail is carved, baked and painted.

Size: about 1 × Puddlepup standing (PROMPTS.md): HEIGHT_UNITS 150, about 0.97 m to the top of the skull, the crest
spikes and the horns a little higher. Palette: CONTENT §2.2 #28 (#4B4F58 charcoal stone / #6B7079 lighter stone /
#8E7CC3 runes violet / #FFB347 amber eyes); no secret variant. Every other colour (the claws, the teeth, the linings,
the cracks' weathered edges, the mouth) is derived from those four.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.nodes import new_mat
from lib.surface import smooth, v3
from monsters.breeds import gloomgrin_form as F
from monsters.breeds import gloomgrin_rings as RG
from monsters.breeds import gloomgrin_runes as RU
from monsters.breeds import gloomgrin_stone as K

ID = 'gloomgrin'
LOOK = 'gloomgrin-ultra'
PLAN = 'biped'
HEIGHT_UNITS = 150

PALETTE = {'body': '#4B4F58', 'belly': '#6B7079', 'accent': '#8E7CC3', 'eye': '#FFB347'}
VARIANTS: dict = {}

# no fur: no locks, cards or tuft, so the body atlas needs no strip (RECIPE.md "Coats without fur")
ATLAS_STRIP = 0
NORMAL_SCALE = 1.15              # the chiselled plates, chips and etched runes want about full strength
BODY_TRIS = 62000
VOXELS = {'hi': 0.0027, 'hi_quick': 0.0045, 'lo': 0.0045}     # a 1 m body with 2 cm ear slabs and 5 mm cracks
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_fins': 0.55, 'lo_props': 1.0}
UV_SMOOTH = 40                   # the plated body unwraps into fewer, larger islands (uv_smooth_mask keeps the face)
GLOW = {'strength': 2.3, 'tint': None}       # round 2: the runes and the eyes glow enough for the bloom (judged at 100 px)
BODY_SHEEN = 0                   # stone: no fur sheen (it reads as felt with a halo)
LITE_PROPS_TRIS = 3600           # the teeth, horns, claws and wing struts are the signature: keep them in Lite
MEMBRANE_AO_BODY = False         # the half-folded wings leave no baked shadow on the back (it stays when they spread)
AO_FLOOR = 0.3
AO_SOFTEN = 1.0
BLINK_CLOSED = (0.74, 0.04, 0.2)
FACE_NOTE = ('Baked face: heavy carved stone brows (no brow bone), big glowing amber lenses with round dark pupils '
             'that squash and sink to blink onto a carved lid line, a wide fixed grin of square teeth with two lower '
             'fangs (props in a carved gap; the jaw does not open). The runes and the eyes glow (ORM alpha).')

PUPIL_HEX = '#17141C'
LASH_HEX = '#1C1A20'

# the ears' rig bones (plans/biped.py ears): along each ear from the head's surface toward its tip
_root, _tip, _A, _B, _N = F.ear_frame(1)
EAR_BASE = tuple(map(float, _root + _A * 0.03))
EAR_DIR = tuple(map(float, _A))
EAR_LEN = 0.165

# the guard's and the pet's hands stay in front of the wide jowls and the round belly (plans/biped.py hand_clear)
HAND_CLEAR = [
    {'bone': 'head', 'c': (0.0, -0.13, 0.665), 'r': (0.215, 0.16, 0.12), 'margin': 0.085, 'push': (0.0, -1.0, 0.0)},
    # polish: the muzzle and the chin too (the cast's claws touched the lower jaw)
    {'bone': 'head', 'c': (0.0, -0.21, 0.63), 'r': (0.13, 0.1, 0.075), 'margin': 0.08, 'push': (0.0, -1.0, 0.0)},
    {'bone': 'spine', 'c': (0.0, -0.02, 0.36), 'r': (0.15, 0.135, 0.17), 'margin': 0.03, 'push': (0.0, -1.0, 0.0)},
]


def rig_p() -> dict:
    return {'hip': F.HIP, 'chest': F.CHEST_PT, 'head_c': F.RIG_HEAD_C, 'head_r': F.RIG_HEAD_R, 'head_base': F.HEAD_BASE,
            'legs': F.LEG, 'arms': F.ARM, 'arm_relax': 14.0, 'arm_radius': 0.06, 'leg_radius': 0.08,
            'ear_base': EAR_BASE, 'ear_dir': EAR_DIR, 'ear_len': EAR_LEN,
            'tail_bones': 6, 'tail_points': F.TAIL, 'wings': F.WINGS,
            # the rooftop statue (the card's habit, 1-hero): a deep crouch with the hands on the ground when still
            'squat': 0.9, 'squat_lean': 36.0, 'squat_hand_dy': 0.08, 'strike_style': 'pounce', 'hand_clear': HAND_CLEAR,
            # round 2: the pounce's claws spread wide and forward, clear of the jowls (5-poses attack: claws out)
            'pounce': {'hand': (0.4, -0.3, 0.78), 'gaze': 0.35, 'tuck': 0.07, 'wings': (1.0, 0.08)},
            # polish: the hits squash the torso, rock the body back about 15 degrees and lift the front foot
            'hit_body': {'squash': 0.25, 'lean': -15.0, 'step': 0.4, 'heavy': 1.5},
            # round 3: win's fists up in a V, as high as the short arms reach (the head is 40% of the height)
            'win': {'over': (0.4, -0.12, 1.0), 'hand': (-10.0, 0.0, 0.0)}}


# ============================================================================= the body
def all_parts():
    return F.all_parts()


def body_extras() -> list[bpy.types.Object]:
    """Voxel-united into the body: the two bat-ear slabs and the two carved brow blocks (the rig skins a proxy without
    them and copies its weights)."""
    out = [F.ear_slab(f'ear{s}', s) for s in (1, -1)]
    nb_ = F.NOSE_BLOCK
    out.append(K.rounded_block('nose', nb_['c'], nb_['half'], (12.0, 0.0, 0.0), m=0.62, seg=32, taper=nb_['taper']))
    for s in (1, -1):
        c, r = brow_place(s)
        out.append(K.rounded_block(f'brow{s}', c, F.BROW['half'], r, m=0.6, seg=32))
    return out


def brow_place(s: int):
    """One brow block's centre and rotation (the left one raised and tilted more: the cheeky look)."""
    b = F.BROW_SIDE[s]
    c = v3(F.BROW['c']) * v3((s, 1, 1)) + v3((0.0, 0.0, b['dz']))
    return c, (F.BROW['rot'][0], b['tilt'] * s, F.BROW['rot'][2] * s)


def brow_sdf(p: np.ndarray) -> np.ndarray:
    d = np.full(len(p), np.inf)
    for s in (1, -1):
        c, r = brow_place(s)
        d = np.minimum(d, K.box_sdf(p, tuple(c), F.BROW['half'], r))
    return d


# ============================================================================= the eyes (positions)
def _front_y(c, r, x: float, z: float) -> float:
    k = 1.0 - ((x - c[0]) / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
    return c[1] - r[1] * math.sqrt(k) if k > 0 else 9.0


def _eye_centre(s: int) -> Vector:
    x, z = F.EYE_X * s, F.EYE_Z
    y = min(_front_y(F.FACE[0], F.FACE[1], x, z), _front_y(F.CRANIUM[0], F.CRANIUM[1], x, z),
            _front_y(F.mirror(F.CHEEK[0], s), F.CHEEK[1], x, z))
    return Vector((x, y - 0.002, z))


EYE_C = {s: _eye_centre(s) for s in (1, -1)}
EYE_R = F.EYE_R
EYE_SHAPE = F.EYE_SHAPE
EYE_DEPTH = F.EYE_DEPTH


def eye_frame(s: int):
    c = EYE_C[s]
    look = Vector((0.36 * s, -1.0, 0.05)).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


LID_LASH, LID_DROP, LID_W = 0.04, 0.12, 0.94


def blink_pivot(s: int):
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


# ============================================================================= zones
_ZC: dict = {}


def _key(p: np.ndarray, n) -> tuple:
    step = max(1, len(p) // 211)
    return (len(p), round(float(p[::step].sum()), 6), n is None)


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict:
    k = _key(p, n)
    if k in _ZC:
        return _ZC[k]
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    hs = F.head_sdf(p)
    head = (hs < 0.03) & (z > 0.545)
    lf = F.light_face_sdf(p)
    face = lf < 0
    brow = brow_sdf(p) < 0.004
    ear, ear_side = F.ear_mask(p)
    if n is not None:
        ear_in = np.zeros(len(p), bool)
        ear_rim = np.zeros(len(p), bool)
        for s in (1, -1):
            _r, _t, _a, _b, N = F.ear_frame(s)
            eu, eacr, _off = F.ear_coords(p, s)
            ear_in |= ear & (ear_side == s) & ((n @ N) > 0.25) & (np.abs(eacr) < 0.72) & (eu < 0.86)   # round 2: a stone rim
            ear_rim |= ear & (ear_side == s) & ((np.abs(eacr) > 0.8) | (eu > 0.9))
    else:
        ear_in = np.zeros(len(p), bool)
        ear_rim = np.zeros(len(p), bool)
        for s in (1, -1):
            _u, _acr, off = F.ear_coords(p, s)
            ear_in |= ear & (ear_side == s) & (off > 0.0) & (np.abs(_acr) < 0.72) & (_u < 0.86)
            ear_rim |= ear & (ear_side == s) & ((np.abs(_acr) > 0.8) | (_u > 0.9))
    fing = F.finger_dist(p) < 0.004
    toes = F.toe_dist(p) < 0.004
    hand = np.zeros(len(p), bool)
    for s in (1, -1):
        hd, _t = F.seg_dist(p, F.mirror(F.ARM['wrist'], s), F.mirror(F.ARM['hand'], s))
        hand |= (hd < 0.075) & (np.sign(x) == s)
    arm = ((F.arm_dist(p) < 0.085) & (ax > 0.2) & ~head) | hand
    shoulder = np.zeros(len(p), bool)
    for s in (1, -1):
        shoulder |= np.linalg.norm(p - v3(F.mirror(F.SHOULDER[0], s)), axis=1) < F.SHOULDER[1] + 0.02
    tail_t, tail_d = F.tail_param(p)
    tail = (tail_d < 0.012) & (tail_t > 0.08)
    leg = (F.leg_dist(p) < 0.115) & (z < 0.32) & ~arm & ~tail
    foot = (z < 0.105) & (ax > 0.08) & (ax < 0.34) & (y < 0.15) & ~tail
    sole = F.sole_mask(p, n)
    belly = F.belly_sdf(p) < 0
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    th = F.mouth_theta(p)
    mz = F.mouth_z(th)
    mouth_area = (y < -0.12) & (np.abs(th) < 57) & (np.abs(z - mz) < 0.036) & head
    nose_d = np.linalg.norm(p - v3(F.NOSE[0]), axis=1) - 0.022
    out = {'head': head, 'face': face, 'face_sdf': lf, 'brow': brow, 'ear': ear, 'ear_in': ear_in, 'ear_side': ear_side, 'ear_rim': ear_rim,
           'fingers': fing, 'toes': toes | fing, 'toe': toes, 'hand': hand, 'paw': hand, 'arm': arm, 'shoulder': shoulder,
           'leg': leg, 'foot': foot, 'sole': sole, 'tail': tail, 'tail_t': tail_t, 'belly': belly, 'eye_d': eye_d,
           'theta': th, 'mouth_z': mz, 'mouth_area': mouth_area, 'muzzle': face & (z < 0.72), 'nose_d': nose_d}
    if len(_ZC) > 8:
        _ZC.clear()
    _ZC[k] = out
    return out


def texel_k(fc: np.ndarray) -> np.ndarray:
    """Round 3: the face (and the eyes' surroundings) at 1.5x the texel density, so the snout's top doesn't streak."""
    face = (F.head_sdf(fc) < 0.02) & (fc[:, 1] < -0.1) & (fc[:, 2] > 0.55)
    snout_top = face & (fc[:, 2] > 0.7) & (np.abs(fc[:, 0]) < 0.09) & (fc[:, 1] < -0.2)
    jaw_side = face & (fc[:, 2] < 0.66) & (np.abs(fc[:, 0]) > 0.07)
    tt, td = F.tail_param(fc)
    stalk = (td < 0.03) & (tt > 0.75)
    k = np.where(face, 1.5, 1.0)
    k = np.where(snout_top, 1.6, k)
    k = np.where(jaw_side, 1.4, k)
    return np.where(stalk, 1.2, k)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """Protect the face (the eyes and the grin's gap most), the brows, the ears' rims and the finger and toe pads from
    the decimation; the plates' edges keep themselves (the collapse keeps sharp creases)."""
    z = zones(co)
    k = (0.45 * z['face'] + 0.5 * (z['eye_d'] < 0.075) + 0.85 * z['mouth_area'] + 0.4 * z['brow'] + 0.3 * z['toes']
         + 0.2 * z['ear'])
    return np.clip(k, 0.0, 1.0)


def uv_smooth_mask(co: np.ndarray) -> np.ndarray:
    """The face, the ears, the fingers and the toes unwrap as they are (only the plated body is smoothed for it)."""
    z = zones(co)
    keep = z['head'] | z['ear'] | z['fingers'] | z['toe'] | (z['tail_t'] > 0.05) & (F.tail_param(co)[1] < 0.03)
    return np.where(keep, 0.0, 1.0)


# ============================================================================= the cracked plates
SEED = 1307
_PLATES: dict = {}


def plate_spacing(p: np.ndarray, n: np.ndarray, z: dict) -> np.ndarray:
    """Seed spacing per point (metres; NaN = no plates: the lighter face, the brows, the ear linings, the fingers and
    toes, the soles, the grin, the belly's chevrons, round the eyes): the biggest on the back, smaller on the head and
    the limbs, smallest on the hands, feet, ears and tail; sizes vary about 2.5x (a flagstone mosaic, not a grid)."""
    y, zz = p[:, 1], p[:, 2]
    sp = np.full(len(p), 0.08)
    sp = np.where(zz > 0.55, 0.068, sp)
    sp = np.where(z['head'], 0.06, sp)
    sp = np.where(z['head'] & (y < -0.07), 0.047, sp)
    sp = np.where(z['shoulder'], 0.066, sp)
    sp = np.where(z['arm'], 0.05, sp)
    sp = np.where(z['hand'], 0.034, sp)
    sp = np.where(z['leg'], 0.058, sp)
    sp = np.where(z['foot'], 0.036, sp)
    sp = np.where(z['tail'], 0.042 - 0.012 * z['tail_t'], sp)
    sp = np.where(z['ear'], 0.042, sp)
    sp = np.where(z['fingers'] | z['toe'], 0.026, sp)          # round 2: plates onto the fingers and toes
    sp = np.where(z['face'], 0.052, sp)                        # round 2: big low plates on the light face
    vary = 0.6 + 0.85 * K.value_noise(p, 1 / 0.14, 59)
    sp = sp * vary
    no = (z['brow'] | z['ear_in'] | z['ear_rim'] | z['sole'] | z['mouth_area'] | z['belly'] | (z['eye_d'] < 0.062) | (z['nose_d'] < 0.03))
    return np.where(no, np.nan, sp)


def seed_params(c: np.ndarray, n: np.ndarray) -> dict:
    """Per seed: proud height H, crack half width w, crack depth cd, flatness kf, bevel slope sb, the top's tilt g, its
    spacing sp."""
    z = zones(c, n)
    k = len(c)
    limb = z['arm'] | z['leg']
    small = z['hand'] | z['foot'] | z['tail'] | z['ear']
    digit = z['fingers'] | z['toe']
    face = z['face']
    H = np.where(limb, 0.0045, 0.0058)
    H = np.where(z['head'], 0.005, H)
    H = np.where(small, 0.0036, H)
    H = np.where(digit, 0.0026, H)
    H = np.where(face, 0.0022, H)
    H = np.where(z['ear'], 0.0018, H)
    w = np.where(limb | z['head'], 0.002, 0.0023)
    w = np.where(small, 0.0017, w)
    w = np.where(digit | face | z['ear'], 0.0013, w)
    cd = np.where(limb | z['head'], 0.0045, 0.0052)
    cd = np.where(small, 0.0036, cd)
    cd = np.where(digit | face | z['ear'], 0.0022, cd)
    kf = np.where(limb | small | z['head'], 0.95, 1.0)
    sb = np.full(k, 5.5)
    rnd = np.stack([K.hash1(np.arange(k), SEED + j) for j in range(6)], axis=1)
    H = H * (0.6 + 0.8 * rnd[:, 0])                         # some plates stand proud of their neighbours
    g = rnd[:, 1:4] - 0.5
    g = g - n * (g * n).sum(1, keepdims=True)
    g = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9) * np.where(limb | small, 0.07, 0.12)[:, None] * rnd[:, 4:5]
    sp = plate_spacing(c, n, z)
    return {'H': H, 'w': w, 'cd': cd, 'kf': kf, 'sb': sb, 'g': g, 'sp': np.where(np.isfinite(sp), sp, 0.05), 'face': face * 1.0}


def make_plates(co: np.ndarray, vn: np.ndarray) -> dict:
    """The seeds (cached: the high source's layout is reused for the low body): a Poisson set on the surface."""
    if 'plates' in _PLATES:
        return _PLATES['plates']
    z = zones(co, vn)
    sp = plate_spacing(co, vn, z)
    lay = U.plate_layout(co, vn, sp, 0.1, 0.02, SEED, wobble=0.0)
    c, n = lay['c'], lay['n']
    plates = {'c': c, 'n': n, **seed_params(c, n)}
    C.log(f'plates: {len(c)} seeds')
    _PLATES['plates'] = plates
    return plates


BELLY_ROW = 0.036             # round 3: smaller chevron tiles (a fishbone under-shell before)
BELLY_SPLIT = 0.056


def belly_field(co: np.ndarray) -> dict:
    """The lighter chest and belly: rows of chevron plates (V's pointing down, split at the mid-line; 2-turnaround
    front), bounded by the belly's outline."""
    x, zz = co[:, 0], co[:, 2]
    b = (zz - 0.5 * np.abs(x) - 0.06) / BELLY_ROW
    band = np.floor(b)
    fr = b - band
    d_band = np.minimum(fr, 1.0 - fr) * BELLY_ROW / math.sqrt(1.25)
    edge = np.maximum(-F.belly_sdf(co), 0.0)
    dw = np.minimum(np.minimum(np.minimum(d_band, np.abs(x)), np.abs(np.abs(x) - BELLY_SPLIT)), edge)
    pid = (100000 + band * 4 + (x > 0) * 2 + (np.abs(x) > BELLY_SPLIT)).astype(np.int64)
    hh = K.hash1(pid, SEED + 77)
    H = 0.0035 * (0.7 + 0.6 * hh)
    tilt = 0.06 * (K.hash1(pid, SEED + 78) - 0.5) * (fr - 0.5) * BELLY_ROW
    top = H + tilt
    edge_h = -0.003 + 2.0 * (dw - 0.0016)
    h = np.maximum(np.minimum(top, edge_h), -0.003)
    return {'h': h, 'dw': dw, 'pid': pid, 'w': np.full(len(co), 0.0016)}


def plain_distance(co: np.ndarray, z: dict) -> np.ndarray:
    """Metres to the nearest plain area (the light face, the brows, the fingers and toes, the belly, the grin, the eye
    sockets, the ear linings): plates end in a crack along each."""
    d = np.full(len(co), 1.0)                       # polish: no crack round the light face (it read as a mask)
    d = np.minimum(d, brow_sdf(co) - 0.004)
    d = np.minimum(d, z['nose_d'] - 0.03)
    d = np.minimum(d, F.belly_sdf(co))
    d = np.minimum(d, z['eye_d'] - 0.062)
    d = np.where(z['mouth_area'] | z['ear_in'] | (z['brow'] & ~z['face']), -1.0, d)
    return np.where(d < 0, 0.0, d)


def plate_field(co: np.ndarray, vn: np.ndarray, plates: dict, z: dict, scale: float = 1.0) -> dict:
    """The plates as heights along the normals: a flat, tilted, chiselled top on each plate, bevelled down to a narrow
    crack at the cell walls (the bisector to the 2nd nearest seed) and at the edge of every plain area; the belly's
    chevron plates inside its outline. Returns h, the wall distance dw, the crack's half width w, the plate id, its kind
    (0 charcoal, 1 the belly), the crack and gap masks and the top (0..1 toward the plate's middle)."""
    c, n = plates['c'], plates['n']
    # the light face's plates and the charcoal plates never share a cell (each side takes its own seeds)
    sf = plates['face'] > 0.5
    fz = z['face']
    idx = np.zeros((len(co), 3), np.int64)
    for want, m in ((True, fz), (False, ~fz)):
        cand = np.nonzero(sf == want)[0]
        if m.any() and len(cand) >= 3:
            ii, _d = K.nearest_seeds(co[m], vn[m], c[cand], n[cand], k=3)
            idx[m] = cand[ii]
    i1, i2 = idx[:, 0], idx[:, 1]
    dw = K.wall_distance(co, c[i1], c[i2])
    dw = np.minimum(dw, plain_distance(co, z))
    on = ~(z['brow'] | z['ear_in'] | z['ear_rim'] | z['sole'] | z['mouth_area'] | z['belly'] | (z['eye_d'] < 0.062) | (z['nose_d'] < 0.03))
    on &= ~(fz & ~sf[i1])
    q = co - c[i1]
    n1 = n[i1]
    H, w, cd, kf, sb, g, sp = (plates[k][i1] for k in ('H', 'w', 'cd', 'kf', 'sb', 'g', 'sp'))
    top = H + kf * np.minimum(np.maximum(0.0, -(q * n1).sum(1)), 0.006) + (q * g).sum(1)
    # chisel cuts: six planes per plate cut its shoulder into angular facets (round 2: chiselled, not pillowy)
    for j in range(6):
        phi = 2 * np.pi * j / 6 + 1.0 * K.hash1(i1, SEED + 20 + j)
        t1 = np.cross(n1, np.array([0.0, 0.0, 1.0]))
        bad = np.linalg.norm(t1, axis=1) < 1e-3
        t1[bad] = np.array([1.0, 0.0, 0.0])
        t1 = t1 / np.linalg.norm(t1, axis=1, keepdims=True)
        t2 = np.cross(n1, t1)
        dirv = t1 * np.cos(phi)[:, None] + t2 * np.sin(phi)[:, None]
        u = (q * dirv).sum(1) / (0.5 * sp)
        u0 = 0.32 + 0.38 * K.hash1(i1, SEED + 30 + j)
        gk = (0.5 + 0.6 * K.hash1(i1, SEED + 40 + j)) * np.where(fz | z['ear'], 0.3, 1.0)
        top = np.minimum(top, top - H * gk * np.maximum(0.0, u - u0) * 2.0)
    edge = -cd + sb * (dw - w)
    h = np.where(on, np.maximum(np.minimum(top, edge), -cd), 0.0)
    pid = np.where(on, i1, -1)
    kind = np.where(on, np.where(fz, 2.0, 0.0), -1.0)
    # the belly's chevrons
    bel = z['belly'] & ~z['sole']
    if bel.any():
        bf = belly_field(co)
        h = np.where(bel, bf['h'], h)
        dw = np.where(bel, bf['dw'], dw)
        w = np.where(bel, bf['w'], w)
        pid = np.where(bel, bf['pid'], pid)
        kind = np.where(bel, 1.0, kind)
    plated = kind >= 0
    crack = np.where(plated, smooth(w * 1.3, w * 0.5, dw), 0.0)
    gap = np.where(plated, smooth(w * 2.4, w * 1.0, dw), 0.0)
    topm = np.where(plated, smooth(0.0, 0.3, dw / np.maximum(sp if not bel.any() else np.where(bel, 0.05, sp), 1e-3)), 0.0)
    return {'h': h * scale, 'dw': dw, 'w': w, 'pid': pid, 'kind': kind, 'crack': crack, 'gap': gap, 'top': topm}


# ============================================================================= the face: grin, eyes, lids, nose
def mouth_field(co: np.ndarray, z: dict) -> dict:
    """The grin: a gap carved MOUTH_DEPTH deep between the lips (the teeth sit in it), a soft roll on each lip, and
    the creases curling up from its corners into the cheeks."""
    th, mz = z['theta'], z['mouth_z']
    gap = F.mouth_gap(th)
    zu = mz + F.MOUTH_UP * gap
    zl = mz - (1.0 - F.MOUTH_UP) * gap
    zz = co[:, 2]
    front = z['mouth_area'].astype(np.float64)
    inside = smooth(zl - 0.0015, zl + 0.003, zz) * smooth(zu + 0.0015, zu - 0.003, zz) * smooth(0.0008, 0.003, gap) * front
    lips = (np.exp(-((zz - (zu + 0.0052)) / 0.0048) ** 2) + 0.45 * np.exp(-((zz - (zl - 0.004)) / 0.0035) ** 2)) * front
    lips = lips * smooth(54.0, 44.0, np.abs(th)) * smooth(0.0, 0.003, gap)
    crease = np.zeros(len(co))
    zc = float(F.mouth_z(np.array([53.0]))[0])
    for s in (1, -1):
        # round 2: from the corner the smile line sweeps up toward the ear (1-hero)
        a = _arc_point(53.0 * s, 0.19, zc)
        b = a + v3((0.026 * s, 0.03, 0.026))
        d, t = F.seg_dist(co, a, b)
        crease = np.maximum(crease, np.exp(-(d / 0.0045) ** 2) * (1.0 - 0.65 * t))
    # the closed corners (the gap tapers to nothing): a dark line along the mouth line
    line = np.exp(-((zz - mz) / 0.0028) ** 2) * front * smooth(46.0, 50.0, np.abs(th)) * smooth(55.0, 52.0, np.abs(th))
    disp = 0.0026 * lips - 0.0028 * np.maximum(crease, line)
    return {'disp': disp, 'inside': inside, 'crease': np.maximum(crease * z['head'], line), 'zu': zu, 'zl': zl}


def mouth_push(co: np.ndarray, inside: np.ndarray) -> np.ndarray:
    """The grin's gap as a move: MOUTH_DEPTH straight in toward the grin's vertical axis (the teeth sit in it)."""
    rad = np.stack([co[:, 0], co[:, 1] - F.MOUTH_AXIS_Y, np.zeros(len(co))], axis=1)
    rad = rad / np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-9)
    return -rad * (F.MOUTH_DEPTH * inside)[:, None]


def cheek_lift(co: np.ndarray) -> np.ndarray:
    """Round 3 (cheeky): a soft bulge pushed up just above and outside each corner of the grin."""
    zc = float(F.mouth_z(np.array([50.0]))[0])
    out = np.zeros(len(co))
    for s in (1, -1):
        c = _arc_point(48.0 * s, 0.195, zc + 0.016)
        out = np.maximum(out, np.exp(-(np.linalg.norm(co - c, axis=1) / 0.022) ** 2))
    return 0.0055 * out


def nostrils(co: np.ndarray) -> np.ndarray:
    d = np.full(len(co), 9.0)
    for s in (1, -1):
        d = np.minimum(d, np.linalg.norm((co - v3((0.014 * s, -0.284, 0.7))) / v3((1.0, 0.7, 0.75)), axis=1))
    return smooth(0.0072, 0.0035, d)


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens, the closed lid (a soft bulge) and its lash line; hidden until a blink sinks the lens."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax_, ay_ = EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1]
        r2 = (xe / ax_) ** 2 + (ye / ay_) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax_ * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * EYE_R
        th = 0.0042 + 0.0018 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        seam = np.exp(-((ye - arc) / th) ** 2)
        fold = 0.55 * np.exp(-((ye - arc - 0.42 * EYE_R) / (0.7 * th)) ** 2)        # the squeezed lid's fold
        lash = np.maximum(lash, np.maximum(seam, fold) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def eye_socket(co: np.ndarray, vn: np.ndarray | None = None) -> np.ndarray:
    """Metres to move each vertex near an eye along its normal: inside the lens's outline the face becomes a dome just
    behind the lens (the closed lid: hidden while the eye is open, a smooth curved lid nearly flush with the face when
    a blink sinks the lens), easing out by 1.12 radii; the brows above are never moved."""
    out = np.zeros(len(co))
    off_brow = smooth(-0.004, 0.006, brow_sdf(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        r = np.sqrt((xe / (EYE_R * EYE_SHAPE[0])) ** 2 + (ye / (EYE_R * EYE_SHAPE[1])) ** 2)
        lens = (np.sqrt(np.clip(1.0 - r * r, 0.0, 1.0)) * EYE_DEPTH[0] - EYE_DEPTH[1]) * EYE_R - 0.0025
        blend = smooth(1.12, 0.98, r) * (ze > -0.04) * (ze < 0.03)
        delta = (lens - ze) * blend * off_brow
        if vn is not None:
            delta = delta / np.clip(vn @ v3(look), 0.6, 1.0)
        delta = np.clip(delta, -0.05, 0.004)
        out = np.where(blend > 0, delta, out)
    return out


def sole_grooves(co: np.ndarray) -> np.ndarray:
    q = co.copy()
    q[:, 2] = 0.0
    f1, f2, _ = K.voronoi(q, 0.035, 41)
    return smooth(0.004, 0.001, f2 - f1)


# ============================================================================= carving
_LAST: dict = {}


def carve(ob: bpy.types.Object) -> None:
    """The high source: the cracked plates (flat chiselled tops, chipped shoulders, narrow cracks), the belly's chevrons,
    the granite's coarse sparse pits and hairline cracks, the light face's pits, the etched runes, the grin's gap, its
    lips and corner creases, the nostrils, the eye sockets and the closed lids, the ear linings' veins, the soles."""
    co, vn = S.mesh_arrays(ob)
    z = zones(co, vn)
    plates = make_plates(co, vn)
    f = plate_field(co, vn, plates, z, 1.0)
    gran = (f['kind'] == 0) & (f['pid'] >= 0)
    light = np.clip(smooth(0.012, -0.012, z['face_sdf']) + (f['kind'] == 1) * 1.0, 0.0, 1.0)   # polish: a soft edge to the charcoal
    blocks = z['brow'] | z['toes']
    chips = K.facets(co, 0.017, 73) * smooth(0.028, 0.006, f['dw']) * gran * ~z['ear']
    flats = K.facets(co, 0.05, 77) * gran
    bchips = K.facets(co, 0.022, 78) * blocks
    pf1, _pf2, _ = K.voronoi(co, 0.011, 87)
    pits = smooth(0.0026, 0.001, pf1) * smooth(-0.15, 0.3, K.fbm(co, 1 / 0.05, 88, 2))            # coarse and sparse
    gr = K.grain(co)
    d_stone = (0.0005 * gr - 0.008 * chips - 0.0035 * flats - 0.0012 * pits) * (1.0 - light) - 0.004 * bchips
    lpits = (smooth(0.42, 0.62, K.fbm(co, 1 / 0.011, 89, 2)) * smooth(-0.1, 0.4, K.fbm(co, 1 / 0.05, 90, 2))
             + 0.6 * smooth(0.55, 0.7, K.fbm(co, 1 / 0.024, 91, 2))) * light
    lpits = np.clip(lpits, 0.0, 1.0)
    lchips = K.facets(co, 0.03, 92) * light
    d_light = (0.0009 * gr - 0.0016 * lpits - 0.0022 * lchips) * light
    hair = 0.3 * K.cracks(co, 0.09, 0.0011, 61, warp=0.03) * smooth(0.2, 0.5, K.fbm(co, 1 / 0.25, 62, 2)) * gran
    hair = hair * smooth(0.012, 0.03, f['dw']) * (1.0 - smooth(0.1, 0.06, z['eye_d']))
    veins = K.cracks(co, 0.028, 0.0011, 63, warp=0.012) * z['ear_in']
    line, halo = RU.rune_field(co, vn)
    mo = mouth_field(co, z)
    bulge, lash = closed_lid(co)
    nos = nostrils(co)
    sole_g = sole_grooves(co) * z['sole']
    disp = (f['h'] + d_stone + d_light - 0.0012 * hair - 0.0012 * veins - 0.0026 * line + mo['disp'] - 0.004 * nos
            - 0.0024 * lash + eye_socket(co, vn) + cheek_lift(co))
    disp = np.where(z['sole'], -0.005 * sole_g, disp)
    new = co + vn * disp[:, None] + mouth_push(co, mo['inside'])
    new[:, 2] = np.maximum(new[:, 2], 0.0)
    S.set_positions(ob, new)
    S.base_attrs(ob, co, {'mouth': mo['inside']})
    attrs = {'plate_id': f['pid'].astype(np.float64), 'plate_kind': f['kind'], 'crack': f['crack'], 'gap': f['gap'],
             'plate_top': f['top'], 'dw': f['dw'], 'chips': chips, 'bchips': bchips, 'hairline': hair, 'lash': lash,
             'lid': bulge, 'light': light, 'pits': pits * (1 - light), 'lpits': lpits, 'rune': line, 'halo': halo,
             'crease': mo['crease'], 'nostril': nos, 'ear_in': z['ear_in'] * 1.0, 'veins': veins, 'sole': z['sole'] * 1.0}
    for name, val in attrs.items():
        S.add_attr(ob, name, np.asarray(val, np.float64))
    _LAST.clear()
    _LAST.update({'n': len(co), 'co': new.copy(), 'vn': vn.copy(), 'base': co.copy(), **attrs, 'mouth': mo['inside']})
    C.log(f'carve: {len(plates["c"])} plates; {int((f["crack"] > 0.5).sum())} of {len(co)} vertices in a crack; '
          f'{int((line > 0.5).sum())} on a rune; height {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm')


def carve_low(ob: bpy.types.Object) -> None:
    """The low body takes the same plates (no fine detail), the grin's gap and the eye sockets, so the plates reach the
    silhouette, the teeth sit in the gap and the bake's cage finds everything."""
    co, vn = S.mesh_arrays(ob)
    z = zones(co, vn)
    plates = make_plates(co, vn)
    f = plate_field(co, vn, plates, z, 0.6)          # round 2: a calmer silhouette (jagged outlines)
    mo = mouth_field(co, z)
    disp = f['h'] + mo['disp'] + eye_socket(co, vn)
    disp = np.where(z['sole'], 0.0, disp)
    new = co + vn * disp[:, None] + mouth_push(co, mo['inside'])
    new[:, 2] = np.maximum(new[:, 2], 0.0)
    S.set_positions(ob, new)
    C.log(f'carve_low: height {float(disp.min()) * 1000:.1f}..{float(disp.max()) * 1000:.1f} mm')


# ============================================================================= eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * EYE_SHAPE[0], v.co.y * EYE_R * EYE_SHAPE[1], v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    uv = co / v3((EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1], EYE_R * EYE_DEPTH[0]))
    S.add_attr(ob, 'eyeuv', uv)
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    # the amber iris glows softly (the card: "amber eyes that glow"), the pupil and the rim don't
    r = np.sqrt(uv[:, 0] ** 2 + uv[:, 1] ** 2)
    S.add_attr(ob, 'glow', 0.45 * smooth(0.82, 0.74, r) * (0.2 + 0.8 * smooth(0.42, 0.52, r)))
    return ob


def eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """Big round amber eyes (4-details panel 2, 3-faces neutral): a deep amber ring round a golden iris, a big round
    dark pupil, a thin pale amber band and a dark rim, two crisp catchlights, and the stone lid just crossing the top
    (the cheeky look). The rough pass keeps the lid matte."""
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    inner = nb.smooth(nb.math('MULTIPLY', nb.math('MULTIPLY', rx, side), -1.0), 0.0, 0.9)
    edge = nb.math('ADD', nb.math('ADD', 0.5, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', rx, rx)), 0.08)),
                   nb.math('MULTIPLY', inner, -0.08))
    upper = nb.smooth(nb.math('SUBTRACT', ry, edge), -0.015, 0.015)
    low_edge = nb.math('ADD', -0.86, nb.math('MULTIPLY', nb.math('MULTIPLY', rx, rx), 0.12))
    lower = nb.smooth(nb.math('SUBTRACT', low_edge, ry), -0.02, 0.02)
    lid = nb.math('MAXIMUM', upper, lower)
    ix = nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.02))
    iy = nb.math('SUBTRACT', ry, 0.03)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', ix, 0.97), nb.math('DIVIDE', iy, 0.97), 0.0))
    if rough_pass:
        pupil = nb.smooth(ri, 0.5, 0.44)
        rim = nb.smooth(ri, 0.89, 0.95)
        rr = nb.math('ADD', nb.math('ADD', nb.math('ADD', 0.3, nb.math('MULTIPLY', pupil, 0.08)), nb.math('MULTIPLY', lid, 0.5)), nb.math('MULTIPLY', rim, 0.55))
        cc = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, lid), nb.math('SUBTRACT', 0.55, nb.math('MULTIPLY', pupil, 0.25)))
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, rr, cc), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    amb = PALETTE['eye']
    deep = C.mix_hex(amb, C.shade_hex(amb, 0.55), 0.6)
    gold = C.mix_hex(amb, '#FFFFFF', 0.06)
    pale = C.mix_hex(amb, '#FFFFFF', 0.55)
    # round 2: a big round pupil (about half the iris, 3-faces), a bright amber-gold iris
    iris = nb.ramp(ri, [(0.0, C.lin(PUPIL_HEX)), (0.38, C.lin(PUPIL_HEX)), (0.41, C.lin(C.shade_hex(deep, 0.8))),
                        (0.44, C.lin(amb)), (0.57, C.lin(amb)), (0.68, C.lin(gold)), (0.79, C.lin(amb)),
                        (0.85, C.lin(deep)), (0.89, C.lin(deep)), (0.93, C.lin(C.shade_hex(PALETTE['body'], 0.55))),
                        (1.0, C.lin(C.shade_hex(PALETTE['body'], 0.55)))])
    ang = nb.math('ARCTAN2', iy, ix)
    streak = nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 23.0)), 0.5)
    streak = nb.math('MULTIPLY', nb.math('ADD', streak, 0.5), nb.math('MULTIPLY', nb.smooth(ri, 0.45, 0.55), nb.smooth(ri, 0.84, 0.76)))
    c = nb.mix(nb.math('MULTIPLY', streak, 0.22), iris, nb.rgb(C.lin(C.mix_hex(amb, '#FFF4D8', 0.45))))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.24), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.24), 1.1), 0.0)), 0.17, 0.13)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.2), nb.math('ADD', ry, 0.24), 0.0)), 0.06, 0.045)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    sh = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ry, edge), -0.3, 0.0), 0.2)
    c = nb.mix(sh, c, nb.rgb(C.lin('#2A2420')), blend='MULTIPLY')
    c = nb.mix(upper, c, nb.rgb(C.lin(C.shade_hex(PALETTE['body'], 0.62))))
    c = nb.mix(lower, c, nb.rgb(C.lin(PALETTE['belly'])))
    lash = nb.math('MULTIPLY', nb.smooth(nb.math('SUBTRACT', ry, edge), -0.07, -0.01), nb.smooth(nb.math('SUBTRACT', ry, edge), 0.06, 0.01))
    c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ============================================================================= props
# kinds (the props' `gpart`)
P_CLAW, P_SPIKE, P_HORN, P_TOOTH, P_FANG, P_ARROW, P_WING, P_WCLAW = 1, 2, 3, 4, 5, 6, 7, 8


def _surf():
    if not _LAST:
        raise SystemExit('gloomgrin: build_props needs carve(hi_body) first (the props sit on the carved surface)')
    return _LAST['co'], _LAST['vn'], _LAST['base']


def claw_items(high: bool) -> list[dict]:
    """Dark stone claws (4-details 3): one on each finger and the thumb, curling toward the palm; one on each toe,
    curving down to the ground; a heel claw pointing back."""
    out = []
    sides = 8 if high else 6
    for s in (1, -1):
        _w, _h, _across, palm = F.hand_frame(s)
        for i, (b, t, _r0, r1) in enumerate(F.fingers(s)):
            d = F.unit(t - b)
            thumb = i == 3
            L = 0.044 if thumb else 0.06                    # round 2: as long as a finger's end
            base = t - d * 0.006
            path = RG.bezier(base, base + d * (0.6 * L), base + d * L + palm * (0.35 * L), 5 if high else 4)
            rr = r1 * 1.12
            radii = [rr, rr * 0.85, rr * 0.6, rr * 0.3, 0.0] if high else [rr, rr * 0.75, rr * 0.35, 0.0]
            out.append({'path': path, 'radii': radii, 'sides': sides, 'aspect': (1.0, 0.82), 'up': palm, 'jitter': 0.06,
                        'seed': 300 + i + 10 * (s > 0), 'kind': P_CLAW, 'anchor': t - d * 0.01, 'cap': True})
        for i, (b, t, _r0, r1) in enumerate(F.toes(s)):
            d = F.unit(t - b)
            base = t - d * 0.008
            tip = t + d * 0.064
            tip[2] = 0.004
            ctrl = t + d * 0.042
            ctrl[2] = t[2] + 0.006
            path = RG.bezier(base, ctrl, tip, 5 if high else 4)
            rr = r1 * 0.98
            radii = [rr, rr * 0.85, rr * 0.6, rr * 0.3, 0.0] if high else [rr, rr * 0.7, rr * 0.35, 0.0]
            out.append({'path': path, 'radii': radii, 'sides': sides, 'aspect': (0.85, 1.0), 'up': (0.0, 0.0, 1.0), 'jitter': 0.06,
                        'seed': 400 + i + 10 * (s > 0), 'kind': P_CLAW, 'anchor': t - d * 0.012, 'cap': True})
        hb = v3((F.HEEL[0][0] * s, F.HEEL[0][1] + 0.03, 0.04))
        path = RG.bezier(hb, hb + v3((0.004 * s, 0.032, -0.012)), hb + v3((0.006 * s, 0.048, -0.036)), 4)
        out.append({'path': path, 'radii': [0.016, 0.012, 0.006, 0.0], 'sides': sides, 'aspect': (0.85, 1.0),
                    'up': (0.0, 0.0, 1.0), 'jitter': 0.06, 'seed': 450 + (s > 0), 'kind': P_CLAW, 'anchor': hb, 'cap': True})
    return out


# the crest: (guide point on the mid-line or off it, height, back tilt) from the brow over the crown, down the nape and
# the spine to the rump (1-hero, 2-turnaround side and back)
CREST = [((0.0, -0.075, 0.96), 0.042, 0.1), ((0.0, -0.025, 0.966), 0.064, 0.25), ((0.0, 0.03, 0.956), 0.058, 0.4),
         ((0.0, 0.08, 0.93), 0.054, 0.55), ((0.0, 0.118, 0.88), 0.05, 0.7), ((0.0, 0.14, 0.81), 0.046, 0.85),
         ((0.04, -0.05, 0.952), 0.028, 0.2), ((-0.04, -0.05, 0.952), 0.028, 0.2), ((0.05, 0.005, 0.95), 0.026, 0.35),
         ((-0.05, 0.005, 0.95), 0.026, 0.35),
         ((0.0, 0.13, 0.7), 0.05, 0.8), ((0.0, 0.15, 0.63), 0.064, 0.75), ((0.0, 0.158, 0.56), 0.07, 0.7),
         ((0.0, 0.158, 0.49), 0.07, 0.7), ((0.0, 0.15, 0.42), 0.064, 0.7), ((0.0, 0.135, 0.355), 0.056, 0.75),
         ((0.0, 0.135, 0.29), 0.048, 0.85), ((0.0, 0.13, 0.235), 0.04, 0.95)]
# along the tail's top (t along it, height)
TAIL_SPIKES = [(0.12, 0.042), (0.26, 0.04), (0.4, 0.037), (0.54, 0.033), (0.68, 0.03), (0.8, 0.026)]


def _tail_at(t: float) -> tuple[np.ndarray, np.ndarray]:
    pts = np.array(F.TAIL, np.float64)
    seg = np.linalg.norm(pts[1:] - pts[:-1], axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    i = min(int(np.searchsorted(cum, t, side='right') - 1), len(seg) - 1)
    f = (t - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    p = pts[i] * (1 - f) + pts[i + 1] * f
    return p, F.unit(pts[i + 1] - pts[i])


def spike_items(high: bool) -> list[dict]:
    """Chunky faceted stone spikes: the crest over the crown and down the spine, and a row along the tail's outer
    curve; each seated on the carved surface, tilted back, its own axis (never a neighbour's)."""
    co, vn, base = _surf()
    out = []
    near_mid = np.abs(co[:, 0]) < 0.012
    for i, (g, h, tilt) in enumerate(CREST):
        m = near_mid if abs(g[0]) < 1e-6 else (np.abs(co[:, 0] - g[0]) < 0.012)
        idx = np.nonzero(m)[0]
        j = idx[int(np.argmin(((co[idx] - v3(g)) ** 2).sum(1)))]
        p, nrm = co[j], F.unit(vn[j])
        d = F.unit(nrm + v3((0.0, tilt, 0.0)) * 0.6)
        out.append(_spike(p, d, h, 600 + i, high))
    for i, (t, h) in enumerate(TAIL_SPIKES):
        c, T = _tail_at(t)
        # the outer side of the curl: away from the curl's centre, and up
        outward = F.unit(c - v3((0.13, 0.22, 0.2)))
        outward = F.unit(outward - T * float(outward @ T) + v3((0.0, 0.0, 0.25)))
        r = F.TAIL_R[min(int(t * (len(F.TAIL_R) - 1) + 0.5), len(F.TAIL_R) - 1)]
        j = int(np.argmin(((co - (c + outward * r)) ** 2).sum(1)))
        d = F.unit(outward - T * 0.45)
        out.append(_spike(co[j], d, h, 700 + i, high))
    return out


def _spike(p: np.ndarray, d: np.ndarray, h: float, seed: int, high: bool) -> dict:
    rng = np.random.default_rng(seed)
    r0 = 0.4 * h
    base = p - d * (0.4 * h)
    path = [base, p + d * (0.1 * h), p + d * (0.55 * h), p + d * h]
    radii = [r0 * 0.9, r0, r0 * 0.55, 0.0]
    return {'path': path, 'radii': radii, 'sides': 5 if seed % 2 else 4, 'aspect': (1.0, 0.72), 'up': (0.0, 1.0, 0.0),
            'roll': float(rng.uniform(-0.3, 0.3)), 'jitter': 0.1, 'seed': seed, 'kind': P_SPIKE, 'anchor': p, 'cap': True}


def horn_paths(s: int, n: int) -> list[np.ndarray]:
    """A stubby horn from the crown: out, up and a little back, its tip turning in (2-turnaround front and side)."""
    b = v3((0.13 * s, -0.068, 0.89))
    c = v3((0.215 * s, -0.075, 0.965))
    t = v3((0.158 * s, -0.035, 1.03))
    return RG.bezier(b, c, t, n)


def horn_items(high: bool, s: int) -> list[dict]:
    n = 72 if high else 12
    path = horn_paths(s, n)
    t = np.linspace(0.0, 1.0, n)
    r = 0.056 * (1 - t) ** 0.85 + 0.016 * t
    r[-1] = 0.0
    r[-2] *= 0.72
    if high:
        # ring plates: a groove every sixth of the length (2-turnaround, 4-details panel 1)
        g = np.exp(-(((t * 6.0) % 1.0 - 0.5) / 0.08) ** 2) * (t > 0.08) * (t < 0.92)
        r = r * (1.0 - 0.07 * g)
    return [{'path': path, 'radii': list(r), 'sides': 48 if high else 12, 'jitter': 0.0,
             'seed': 800 + (s > 0), 'kind': P_HORN, 'anchor': path[0], 'cap': True}]


def _face_radius(theta: float, zq: float) -> float:
    """The uncarved face's distance from the grin's axis at an angle and height."""
    base = _LAST.get('base')
    if base is not None:
        th = F.mouth_theta(base)
        m = (np.abs(th - theta) < 2.5) & (np.abs(base[:, 2] - zq) < 0.004) & (base[:, 1] < -0.1)
        if m.sum() >= 3:
            q = base[m]
            return float(np.percentile(np.sqrt(q[:, 0] ** 2 + (q[:, 1] - F.MOUTH_AXIS_Y) ** 2), 50))
    return 0.212


def _arc_point(theta: float, R: float, zq: float) -> np.ndarray:
    a = math.radians(theta)
    return v3((R * math.sin(a), F.MOUTH_AXIS_Y - R * math.cos(a), zq))


def teeth_items(high: bool) -> list[dict]:
    """The grin's teeth (round 2; 1-hero, 4-details panel 1): six big square cream teeth hanging from the upper lip,
    each a rounded block set well inside the lips (the front 6.5 mm behind them over the tooth's whole width, so no
    corner juts out in profile), the dark mouth showing below them."""
    out = []
    sides = 24 if high else 8
    step = F.TOOTH_STEP
    # round 3: each tooth at most 5 mm deeper than its neighbour toward the middle (the outer ones sank behind the
    # jowls' curve and left a dark gap like a missing tooth)
    r_prev = {1: None, -1: None}
    for c0 in sorted(F.UPPER_TEETH):
        for th in (c0, -c0):
            gap = float(F.mouth_gap(np.array([th]))[0])
            mz = float(F.mouth_z(np.array([th]))[0])
            zu = mz + F.MOUTH_UP * gap
            top, bot = zu + 0.006, mz + 0.002 - (0.002 if c0 < 6 else 0.0)
            zc = 0.5 * (top + bot)
            hh = 0.5 * (top - bot)
            zl = mz - (1 - F.MOUTH_UP) * gap
            R = min(_face_radius(th + dt, zq) for dt in (-0.42 * step, 0.0, 0.42 * step) for zq in (zu, zc, zl - 0.004))
            sd = 1 if th >= 0 else -1
            if r_prev[sd] is not None:
                R = max(R, r_prev[sd] - 0.005)
            r_prev[sd] = R
            half_w = 0.5 * (math.radians(step) * R - 0.0036)
            front = _arc_point(th, R - 0.0055, zc)
            back = _arc_point(th, R - F.MOUTH_DEPTH + 0.003, zc)
            d = F.unit(front - back)
            L = float(np.linalg.norm(front - back))
            ts, rk = ([0.0, 0.5, 0.8, 0.93, 1.0], [0.94, 1.0, 1.0, 0.95, 0.82]) if high else ([0.0, 1.0], [1.0, 1.0])
            path = [back + d * (L * t) for t in ts]
            out.append({'path': path, 'radii': rk, 'sides': sides, 'power': 0.3, 'roll': math.pi / sides,
                        'aspect': (hh * 1.04, half_w * 1.04), 'up': (0.0, 0.0, 1.0), 'seed': int(5000 + th * 3),
                        'kind': P_TOOTH, 'anchor': front, 'cap': True, 'cap_tip': True})
    return out


def fang_items(high: bool) -> list[dict]:
    """An upper fang at each end of the row, pointing down past the teeth to the lower lip (1-hero, 4-details 1)."""
    out = []
    for s in (1, -1):
        th = F.FANG_TH * s
        gap = float(F.mouth_gap(np.array([th]))[0])
        mz = float(F.mouth_z(np.array([th]))[0])
        zu, zl = mz + F.MOUTH_UP * gap, mz - (1 - F.MOUTH_UP) * gap
        R = min(_face_radius(th, zu), _face_radius(th, mz))
        b = _arc_point(th, R - 0.004, zu + 0.008)
        t = _arc_point(th - 1.5 * s, R - 0.0015, zl - 0.008)
        mid = 0.5 * (b + t) + F.unit(_arc_point(th, 1.0, 0.0) - _arc_point(th, 0.0, 0.0)) * 0.0015
        n = 7 if high else 4
        path = RG.bezier(b, mid, t, n)
        radii = list(np.linspace(0.015, 0.004, n))
        radii[-1] = 0.0
        out.append({'path': path, 'radii': radii, 'sides': 16 if high else 7, 'aspect': (1.0, 0.85), 'seed': 950 + (s > 0),
                    'kind': P_FANG, 'anchor': b, 'cap': True})
    return out


def arrow_frame():
    tip = v3(F.TAIL[-1])
    up = F.unit(F.ARROW['up'])
    face = F.unit(v3(F.ARROW['face']) - up * float(v3(F.ARROW['face']) @ up))
    wide = np.cross(up, face)
    return tip, up, face, wide


def arrow_items(high: bool) -> list[dict]:
    """The tail's arrowhead (4-details panel 5): a chunky stone diamond with softened facets (round 2: a gem cut, not
    a hard octahedron), its broad face to the three-quarter camera."""
    tip, up, face, wide = arrow_frame()
    L = F.ARROW['len']
    base = tip - up * 0.014
    ts = [0.0, 0.08, 0.22, 0.36, 0.44, 0.52, 0.7, 0.86, 0.96, 1.0]
    rk = [0.0, 0.32, 0.72, 0.95, 1.0, 0.96, 0.62, 0.3, 0.1, 0.0]
    path = [base + up * (L * t) for t in ts]
    return [{'path': path, 'radii': rk, 'sides': F.ARROW['sides'] * (2 if high else 1), 'power': 0.8,
             'aspect': (0.5 * F.ARROW['width'], 0.5 * F.ARROW['thick']), 'up': wide, 'roll': 0.0, 'jitter': 0.0,
             'seed': 990, 'kind': P_ARROW, 'anchor': tip}]


def arrow_rune(p: np.ndarray, vn: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The rune on the arrowhead's broad face (a diamond with a square spiral) and its halo."""
    tip, up, face, wide = arrow_frame()
    mid = tip - up * 0.014 + up * (F.ARROW['len'] * 0.44)
    runes = [{'c': tuple(mid + face * (0.5 * F.ARROW['thick'])), 'n': tuple(face), 'size': 0.036, 'glyph': 'spiral', 'up': tuple(up)},
             # round 2: the back face too (it was blank in the back view)
             {'c': tuple(mid - face * (0.5 * F.ARROW['thick'])), 'n': tuple(-face), 'size': 0.034, 'glyph': 'diamond', 'up': tuple(up)}]
    return RU.rune_field(p, vn, runes, half=0.0028)


def wing_items(high: bool, s: int) -> tuple[list[dict], list[dict]]:
    """One wing's stone arm (shoulder → elbow → wrist, a knuckle at the wrist) and finger struts (smooth tubes), and
    the little thumb claw on the wrist (faceted)."""
    q = U.wing_points(F.WINGS, s)
    sh, el, wr = q['shoulder'], q['elbow'], q['wrist']
    ra = F.WING_R['arm']
    k = 16 if high else 3
    a1 = [sh + (el - sh) * t for t in np.linspace(-0.1, 1.0, k + 1)]
    a2 = [el + (wr - el) * t for t in np.linspace(0.0, 1.0, k + 1)][1:]
    path = a1 + a2
    radii = list(np.linspace(ra[0], ra[1], k + 1)) + list(np.linspace(ra[1], ra[2], k + 1))[1:]
    sides = 28 if high else 9
    tubes = [{'path': path, 'radii': radii, 'sides': sides, 'seed': 1000 + (s > 0), 'kind': P_WING, 'wside': float(s),
              'anchor': sh, 'cap': True, 'cap_tip': True}]
    dwr = F.unit(wr - el)
    tubes.append({'path': [wr - dwr * 0.016, wr - dwr * 0.006, wr + dwr * 0.006, wr + dwr * 0.015],
                  'radii': [ra[2] * 0.95, ra[2] * 1.32, ra[2] * 1.32, ra[2] * 0.8], 'sides': sides, 'seed': 1010 + (s > 0),
                  'kind': P_WING, 'wside': float(s), 'anchor': wr, 'cap': True, 'cap_tip': True})
    rf = F.WING_R['finger']
    for j, tp in enumerate(q['fingers']):
        n = 22 if high else 4
        pts = [wr + (tp - wr) * t for t in np.linspace(0.0, 1.0, n)]
        rr = list(np.linspace(rf[0], rf[1], n))
        rr[-1] = 0.0
        tubes.append({'path': pts, 'radii': rr, 'sides': 18 if high else 7, 'seed': 1020 + j + 5 * (s > 0), 'kind': P_WING,
                      'wside': float(s), 'anchor': wr, 'cap': True})
    up = F.unit(v3((0.25 * s, -0.5, 0.85)))
    cb = wr + up * (ra[2] * 0.9)
    claw = [{'path': RG.bezier(cb, cb + up * 0.03, cb + up * 0.046 + v3((0.0, -0.016, -0.006)), 4),
             'radii': [0.0135, 0.01, 0.005, 0.0], 'sides': 7 if high else 5, 'aspect': (1.0, 0.8), 'jitter': 0.05,
             'seed': 1040 + (s > 0), 'kind': P_WCLAW, 'wside': float(s), 'anchor': wr, 'cap': True}]
    return tubes, claw


def stone_cells(co: np.ndarray, cell: float = 0.016, seed: int = 131) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(crack 0..1, a tone per cell 0..1, chips 0..1) of a small stone mosaic on a prop's surface (round 2: the horns,
    the wing struts and the arrowhead read as carved stone segments, not smooth plastic with painted rings)."""
    f1, f2, fid = K.voronoi(co, cell, seed)
    crack = smooth(0.0016, 0.0005, f2 - f1)
    tone = K.hash1(fid, seed + 1)
    chips = K.facets(co, cell * 0.7, seed + 2)
    return crack, tone, chips


def carve_stone(ob: bpy.types.Object, cell: float = 0.016) -> None:
    co, vn = S.mesh_arrays(ob)
    crack, tone, chips = stone_cells(co, cell)
    S.set_positions(ob, co + vn * (-0.0015 * crack - 0.001 * chips + 0.0008 * (tone - 0.5))[:, None])


def _set_attrs(ob: bpy.types.Object, kind: float, anchor, wside: float = 0.0) -> None:
    """After a subdivision: the per-object attributes again (constant), and the facet shade from the face normals."""
    n = len(ob.data.vertices)
    co, vn = S.mesh_arrays(ob)
    sh = np.sin(vn @ v3((12.9898, 78.233, 37.719)) * 43758.5453)
    sh = (sh - np.floor(sh)) * 2.0 - 1.0
    old = S.attr_array(ob, 'pt').astype(np.float64) if 'pt' in ob.data.attributes else np.zeros((n, 3))
    S.add_attr(ob, 'pt', np.stack([old[:, 0], sh, old[:, 2]], axis=1))
    S.add_attr(ob, 'gpart', np.full(n, float(kind)))
    S.add_attr(ob, 'anchor', np.tile(v3(anchor), (n, 1)))
    S.add_attr(ob, 'item', np.zeros(n))
    S.add_attr(ob, 'wside', np.full(n, float(wside)))


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    spikes = RG.ringed_object(f'{tag}_spikes', spike_items(high), flat=True, extra_attrs=('wside',))
    if high:
        RG.subdivide(spikes, 1 if quick else 6)
        carve_stone(spikes, 0.012)
    out = [RG.ringed_object(f'{tag}_claws', claw_items(high), flat=True, extra_attrs=('wside',)),
           spikes,
           RG.ringed_object(f'{tag}_teeth', teeth_items(high), flat=False, extra_attrs=('wside',)),
           RG.ringed_object(f'{tag}_fangs', fang_items(high), flat=False, extra_attrs=('wside',))]
    for s in (1, -1):
        horn = RG.ringed_object(f'{tag}_horn{"L" if s > 0 else "R"}', horn_items(high, s), flat=False, extra_attrs=('wside',))
        if not high:
            S.tube_uvs(horn, np.array(horn_paths(s, 12)))
        else:
            carve_stone(horn, 0.017)
        out.append(horn)
    # the high source smooth (its normal map softens the low one's facets); a smooth low arrowhead hung the packer
    arrow = RG.ringed_object(f'{tag}_arrow', arrow_items(high), flat=not high, extra_attrs=('wside',))
    if high:
        RG.subdivide(arrow, 1 if quick else 4)
        _set_attrs(arrow, P_ARROW, F.TAIL[-1])
        carve_stone(arrow, 0.022)
    out.append(arrow)
    for s in (1, -1):
        tubes, claw = wing_items(high, s)
        t = 'L' if s > 0 else 'R'
        for j, it in enumerate(tubes):
            ob = RG.ringed_object(f'{tag}_wbone{t}{j}', [it], flat=False, extra_attrs=('wside',))
            if not high and j != 1:
                S.tube_uvs(ob, np.array(it['path']))
            elif high:
                carve_stone(ob, 0.014)
            out.append(ob)
        out.append(RG.ringed_object(f'{tag}_wclaw{t}', claw, flat=True, extra_attrs=('wside',)))
    return out


def preview_prop_colour(name: str):
    col = colours(PALETTE)
    if 'teeth' in name or 'fang' in name:
        return col['tooth']
    if 'claw' in name:
        return col['claw']
    if 'horn' in name:
        return col['horn']
    return PALETTE['body']


def _anchor_weights(co: np.ndarray, anchor: np.ndarray, names: list[str]) -> dict[str, np.ndarray]:
    """Every vertex copies lo_body's weights at its anchor (the mean of the six nearest body vertices), so a claw moves
    with its finger and a spike with the skin it grows from. Without a skinned body (the preview): the chest."""
    from mathutils.kdtree import KDTree
    body = bpy.data.objects.get('lo_body')
    if body is None or not body.vertex_groups:
        return {'chest': np.ones(len(co))}
    bn, W = S.body_weights(body)
    bco, _ = S.mesh_arrays(body)
    kd = KDTree(len(bco))
    for i, p in enumerate(bco):
        kd.insert(Vector(p), i)
    kd.balance()
    uniq, inv = np.unique(np.round(anchor, 5), axis=0, return_inverse=True)
    rows = np.zeros((len(uniq), len(bn)))
    for u, p in enumerate(uniq):
        near = kd.find_n(Vector(p), 6)
        rows[u] = np.mean([W[j] for _c, j, _d in near], axis=0)
    out: dict[str, np.ndarray] = {}
    for j, nm in enumerate(bn):
        if nm in names and rows[:, j].max() > 1e-4:
            out[nm] = rows[inv.ravel(), j]
    return out


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    gp = np.round(attr('gpart')).astype(int)
    ws = attr('wside')
    regs = []
    m = (gp == P_CLAW) | (gp == P_SPIKE)
    if m.any():
        regs.append((m, _anchor_weights(co[m], attr('anchor')[m], names)))
    m = (gp == P_HORN) | (gp == P_TOOTH) | (gp == P_FANG)
    if m.any():
        regs.append(U.rigid(m, 'head'))
    m = gp == P_ARROW
    if m.any():
        regs.append(U.rigid(m, 'tail.6'))
    for s in (1, -1):
        m = ((gp == P_WING) | (gp == P_WCLAW)) & (np.abs(ws - s) < 0.1)
        if m.any():
            regs.append((m, U.segment_weights(co[m], U.wing_limb_segments(F.WINGS, s), power=6)))
    return regs


# ============================================================================= membranes: the wings
def build_fins(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    res = ((16, 28) if quick else (90, 150)) if high else (8, 14)        # round 3: fine enough for veins and runes
    return [S.wing_membrane(f'{tag}_wing{U.wing_tag(s)}', F.WINGS, s, high, quick, relief=0.0015, res=res) for s in (1, -1)]


def fin_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    return U.wing_fin_regions(co, attr, names, F.WINGS)


# ============================================================================= weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The head's skin (the face, the jowls, the brows, the cranium) moves with the head bone only; the fingers with
    their hand; each ear slab along its two bones; the tail along its six."""
    regs = []
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    hs = F.head_sdf(co)
    head = (hs < 0.006) & ((z > 0.6) | ((y < -0.12) & (z > 0.55)))
    head |= brow_sdf(co) < 0.006
    ear, ear_side = F.ear_mask(co)
    regs.append(U.rigid(head & ~ear, 'head'))
    for s, tag in ((1, 'L'), (-1, 'R')):
        fd = np.full(len(co), 9.0)
        for a, b, r0, r1 in F.fingers(s):
            dd, t = F.seg_dist(co, a, b)
            fd = np.minimum(fd, dd - (r0 + (r1 - r0) * t))
        m = (fd < 0.006) & (np.sign(x) == s)
        if m.any():
            regs.append(U.rigid(m, f'hand.{tag}'))
        m = ear & (ear_side == s)
        if m.any():
            root, tip, A, _B, _N = F.ear_frame(s)
            b0 = root + A * 0.03
            pts = [tuple(b0), tuple(b0 + A * EAR_LEN * 0.5), tuple(b0 + A * EAR_LEN)]
            regs.append((m, U.chain_weights(co[m], pts, [f'ear.{tag}.1', f'ear.{tag}.2'], 'head', fade=(0.08, -0.04))))
    tt, td = F.tail_param(co)
    m = (td < 0.02) & (tt > 0.04) & (y > 0.12)
    if m.any():
        tn = [f'tail.{i + 1}' for i in range(len(F.TAIL) - 1)]
        regs.append((m, U.chain_weights(co[m], F.TAIL, tn, 'hips', fade=(0.05, -0.05))))
    return regs


# ============================================================================= paint
def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


def colours(pal: dict) -> dict:
    """Every derived colour (CONTENT has four): made from the palette only."""
    body, light, rune, eye = pal['body'], pal['belly'], pal['accent'], pal['eye']
    lining = C.mix_hex(C.mix_hex(body, light, 0.55), rune, 0.42)      # round 2: a clearer violet tint
    return {
        'stone': body,
        'stone_dark': C.shade_hex(body, 0.62),
        'stone_warm': C.mix_hex(body, eye, 0.1),                    # the weathered grains
        'stone_top': C.mix_hex(body, light, 0.35),                  # fresh chipped stone
        'crack': C.shade_hex(body, 0.36),
        'crack_edge': C.mix_hex(C.shade_hex(body, 0.85), eye, 0.16),   # the cracks' weathered tan edges (4-details 6)
        'dust': C.mix_hex(C.mix_hex(C.shade_hex(body, 0.7), light, 0.2), eye, 0.2),   # round 3: warm brown dust in the grooves
        'light': light,
        'light_dark': C.shade_hex(light, 0.8),
        'rune': rune,
        'rune_deep': C.shade_hex(rune, 0.7),
        'lining': lining,                                           # the ears' linings and the wings' stone-leather
        'lining_vein': C.shade_hex(lining, 0.7),
        'membrane': C.mix_hex(C.mix_hex(body, light, 0.45), rune, 0.24),   # round 3: dusky violet-grey stone-leather
        'membrane_vein': C.shade_hex(C.mix_hex(body, rune, 0.12), 0.72),
        'mouth': C.mix_hex(C.shade_hex(body, 0.26), rune, 0.06),
        'tooth': C.mix_hex(C.mix_hex(light, '#FFFFFF', 0.55), eye, 0.14),
        'claw': C.shade_hex(body, 0.55),
        'horn': C.mix_hex(body, light, 0.55),
        'fleck_dark': C.shade_hex(body, 0.34),
        'fleck_pale': C.mix_hex(light, '#FFFFFF', 0.32),
        'sole': C.mix_hex(body, light, 0.45),
    }


def _body_paint(I: dict, pal: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(paint linear RGB, rough (1, roughness, coat), glow) per vertex of a body source."""
    col = colours(pal)
    k = len(I['co'])
    pid = I['pid'].astype(np.int64)
    ph = U.plate_hash(pid, 5)
    ph2 = U.plate_hash(pid, 9)
    mott = K.fbm(I['co'], 1 / 0.08, 81, 3)
    granite = lin(col['stone'])[None] * (1.1 + 0.26 * ph + 0.08 * mott)[:, None]
    warm = (smooth(0.55, 1.0, ph2) * 0.4)[:, None]
    granite = granite * (1 - warm) + lin(col['stone_warm'])[None] * (0.95 + 0.15 * ph[:, None]) * warm
    lt = I['light'][:, None]
    lk = np.where(I['kind'] > 0.5, np.where(I['kind'] > 1.5, 1.12, 1.5), 1.12)
    light = lin(col['light'])[None] * (lk + 0.14 * ph + 0.06 * mott)[:, None]
    light = light * (1.0 - 0.22 * I['lpits'][:, None])
    rgb = granite * (1 - lt) + light * lt
    rgb = rgb * (1.0 - 0.25 * I['pits'][:, None])
    # the plates' weathered tops a little paler (4-details 6)
    tk = (I['top'] * 0.22 * (1 - lt[:, 0]))[:, None]
    rgb = rgb * (1 - tk) + lin(col['stone_top'])[None] * 1.1 * tk
    # the plates' bevelled shoulders a little darker, the chipped corners paler (fresh broken stone)
    rim = (smooth(0.02, 0.006, I['dw']) * 0.12 * (1 - lt[:, 0]))[:, None]
    rgb = rgb * (1 - rim)
    ch = (np.clip(I['chips'] * 1.5, 0, 1) * 0.32 + np.clip(I['bchips'] * 1.5, 0, 1) * 0.2)[:, None]
    rgb = rgb * (1 - ch) + lin(col['stone_top'])[None] * ch
    # the cracks: weathered tan edges, a dark core
    gk = (I['gap'] * 0.65)[:, None]               # warm dust in the cracks
    rgb = rgb * (1 - gk) + lin(col['crack_edge'])[None] * gk
    ck = (I['crack'] * 0.8)[:, None]
    belly_crack = lin(col['light_dark'])[None] * 0.7
    crack_col = np.where((I['kind'] > 0.5)[:, None], belly_crack, lin(col['dust'])[None])
    rgb = rgb * (1 - ck) + crack_col * ck
    hl = (I['hairline'] * 0.5)[:, None]
    rgb = rgb * (1 - hl) + lin(col['stone_dark'])[None] * hl
    # the ear linings: lilac stone-leather with darker veins
    ein = I['ear_in'][:, None]
    lining = lin(col['lining'])[None] * (0.94 + 0.12 * mott[:, None]) * (1.0 - 0.35 * I['veins'][:, None])
    rgb = rgb * (1 - ein) + lining * ein
    # the soles: lighter pads
    so = I['sole'][:, None]
    rgb = rgb * (1 - so) + lin(col['sole'])[None] * (0.95 + 0.08 * mott[:, None]) * so
    # the grin's gap: a dark mouth; the creases and the closed corners darker; the nostrils
    mo = np.clip(I['mouth'] * 1.3, 0, 1)[:, None]
    rgb = rgb * (1 - mo) + lin(col['mouth'])[None] * mo
    cr = (np.clip(I['crease'], 0, 1) * 0.55)[:, None]
    rgb = rgb * (1 - cr) + lin(col['light_dark'])[None] * 0.45 * cr
    no = (I['nostril'] * 0.85)[:, None]
    rgb = rgb * (1 - no) + lin(col['mouth'])[None] * no
    lsh = (np.clip(I['lash'], 0.0, 1.0) * 1.0)[:, None]
    rgb = rgb * (1 - lsh) + lin(LASH_HEX)[None] * lsh
    # the runes: a faint violet line etched in, its glow tinting the stone round it a little
    ha = (I['halo'] * 0.18)[:, None]
    rgb = rgb * (1 - ha) + lin(col['rune_deep'])[None] * ha
    rn = (I['rune'] * 0.92)[:, None]
    rgb = rgb * (1 - rn) + lin(col['rune'])[None] * rn
    rough = np.stack([np.ones(k), 0.86 - 0.06 * I['light'] + 0.06 * I['crack'] - 0.1 * I['mouth'], np.full(k, 0.02)], axis=1)
    glow = np.clip(0.22 * I['rune'] + 0.34 * I['halo'], 0.0, 1.0)
    return rgb, rough, glow


def _inputs(ob: bpy.types.Object) -> dict:
    get = lambda nm, d=0.0: S.attr_array(ob, nm).astype(np.float64) if nm in ob.data.attributes else np.full(len(ob.data.vertices), d)  # noqa: E731
    co = S.attr_array(ob, 'root').astype(np.float64) if 'root' in ob.data.attributes else S.mesh_arrays(ob)[0]
    return {'co': co, 'pid': get('plate_id', -1.0), 'kind': get('plate_kind', -1.0), 'crack': get('crack'), 'gap': get('gap'),
            'dw': get('dw', 1.0), 'light': get('light'), 'chips': get('chips'), 'bchips': get('bchips'), 'hairline': get('hairline'),
            'pits': get('pits'), 'lpits': get('lpits'), 'mouth': get('mouth'), 'crease': get('crease'), 'nostril': get('nostril'),
            'lash': get('lash'), 'rune': get('rune'), 'halo': get('halo'), 'ear_in': get('ear_in'), 'veins': get('veins'),
            'sole': get('sole'), 'top': get('plate_top')}


def wing_rune_field(co: np.ndarray, vn: np.ndarray, wuv: np.ndarray, side: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two runes per wing laid as decals on the membrane's surface in 3-D (round 2: in the membrane's own (u, v) they
    stretched into a striped barcode): a diamond in the middle panel, a spiral in the inner one."""
    line = np.zeros(len(co))
    halo = np.zeros(len(co))
    nf = len(F.WINGS['fingers'])
    for sd in (1, -1):
        on = np.abs(side - sd) < 0.1
        if not on.any():
            continue
        runes = []
        for pan, u0, v0, size, g in ((nf - 2, 0.5, 0.6, 0.042, 'diamond'), (nf - 1, 0.42, 0.5, 0.045, 'chevron')):
            d = np.where(on & (np.abs(wuv[:, 0] - pan) < 0.5), (wuv[:, 1] - u0) ** 2 + (wuv[:, 2] - v0) ** 2, np.inf)
            i = int(np.argmin(d))
            if not np.isfinite(d[i]):
                continue
            runes.append({'c': tuple(co[i]), 'n': tuple(vn[i]), 'size': size, 'glyph': g, 'mirror': sd < 0, 'facing': -2.0})
        ln, hl = RU.rune_field(co, None, runes, half=0.0032)
        line = np.maximum(line, ln * on)
        halo = np.maximum(halo, hl * on)
    return line, halo


def _fin_paint(ob: bpy.types.Object) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The wings' thin stone-leather (4-details panel 4): lilac grey, a network of fine darker cracks, darker toward
    the struts and the scalloped edge, two small runes per wing."""
    col = colours(PALETTE)
    co, _vn = S.mesh_arrays(ob)
    _vn = _vn / np.maximum(np.linalg.norm(_vn, axis=1, keepdims=True), 1e-9)
    wuv = S.attr_array(ob, 'wing_uv').astype(np.float64)
    side = S.attr_array(ob, 'wing_side').astype(np.float64)
    nf = len(F.WINGS['fingers'])
    rel = U.wing_relief(wuv, nf)
    cr = K.cracks(co, 0.035, 0.0012, 64, warp=0.01)
    mott = K.fbm(co, 1 / 0.06, 65, 2)
    v = wuv[:, 2]
    u = wuv[:, 1]
    crackle = K.cracks(co, 0.022, 0.0016, 67, warp=0.008)
    near_bone = np.clip(np.exp(-(u / 0.07) ** 2) + np.exp(-((1 - u) / 0.07) ** 2) + np.exp(-(v / 0.06) ** 2), 0, 1)
    rgb = lin(col['membrane'])[None] * (0.9 + 0.12 * mott[:, None]) * (0.85 + 0.3 * smooth(0.1, 0.85, v))[:, None]
    dark = np.clip(0.4 * near_bone + 0.55 * crackle + 0.25 * cr + 0.3 * rel * 0.5, 0.0, 0.85)[:, None]
    rgb = rgb * (1 - dark) + lin(col['membrane_vein'])[None] * dark
    rim = (smooth(0.955, 0.985, v) * 0.75)[:, None]                  # a thin darker rim along the trailing edge
    rgb = rgb * (1 - rim) + lin(col['membrane_vein'])[None] * rim
    line, halo = wing_rune_field(co, _vn, wuv, side)
    rgb = rgb * (1 - (halo * 0.15)[:, None]) + lin(col['rune_deep'])[None] * (halo * 0.15)[:, None]
    rgb = rgb * (1 - (line * 0.9)[:, None]) + lin(col['rune'])[None] * (line * 0.9)[:, None]
    n = len(co)
    rough = np.stack([np.ones(n), np.full(n, 0.8), np.full(n, 0.02)], axis=1)
    return rgb, rough, np.clip(0.25 * line + 0.34 * halo, 0.0, 1.0)


def _prop_paint(ob: bpy.types.Object) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    col = colours(PALETTE)
    co, vn = S.mesh_arrays(ob)
    n = len(co)
    gp = np.round(S.attr_array(ob, 'gpart').astype(np.float64)).astype(int)
    pt = S.attr_array(ob, 'pt').astype(np.float64)
    t, fs = pt[:, 0], pt[:, 1]
    mott = K.fbm(co, 1 / 0.03, 66, 2)
    crk, tone, chp = stone_cells(co)
    cellk = (0.9 + 0.22 * tone + 0.15 * np.clip(chp * 1.5, 0, 1))[:, None]
    rgb = np.tile(lin(col['stone']), (n, 1))
    rough = np.tile(np.array([1.0, 0.8, 0.03]), (n, 1))
    glow = np.zeros(n)
    # claws: dark stone, a shade per facet, the tips a little paler (worn)
    m = (gp == P_CLAW) | (gp == P_WCLAW)
    c = lin(col['claw'])[None] * (1.0 + 0.16 * fs[:, None] + 0.05 * mott[:, None])
    c = c * (1.0 - 0.15 * smooth(0.6, 1.0, t))[:, None]
    rgb = np.where(m[:, None], c, rgb)
    rough = np.where(m[:, None], np.array([[1.0, 0.8, 0.0]]), rough)
    # spikes: the stone, a shade per facet, paler worn tips
    m = gp == P_SPIKE
    c = lin(col['stone'])[None] * cellk * (1.3 + 0.1 * fs[:, None] + 0.06 * mott[:, None])
    c = c * (1 - (crk * 0.6)[:, None]) + lin(col['dust'])[None] * (crk * 0.6)[:, None]
    tipk = (smooth(0.6, 1.0, t) * 0.3)[:, None]
    c = c * (1 - tipk) + lin(col['stone_top'])[None] * tipk
    rgb = np.where(m[:, None], c, rgb)
    rough = np.where(m[:, None], np.array([[1.0, 0.9, 0.0]]), rough)
    # horns: lighter stone in ring plates, the grooves dark
    m = gp == P_HORN
    g = np.exp(-(((t * 6.0) % 1.0 - 0.5) / 0.07) ** 2) * (t > 0.08) * (t < 0.92)
    c = lin(col['horn'])[None] * cellk * (0.95 + 0.1 * mott[:, None]) * (1.0 - 0.4 * g[:, None])
    c = c * (1 - (crk * 0.7)[:, None]) + lin(col['crack'])[None] * (crk * 0.7)[:, None]
    c = c * (1 - (smooth(0.75, 1.0, t) * 0.2)[:, None]) + lin(col['stone_top'])[None] * (smooth(0.75, 1.0, t) * 0.2)[:, None]
    rgb = np.where(m[:, None], c, rgb)
    rough = np.where(m[:, None], np.array([[1.0, 0.84, 0.02]]), rough)
    # teeth and fangs: pale stone, darker toward their roots in the gap
    m = (gp == P_TOOTH) | (gp == P_FANG)
    rootk = np.where(gp == P_TOOTH, smooth(0.45, 0.0, t), smooth(0.25, 0.0, t))
    c = lin(col['tooth'])[None] * (1.0 + 0.04 * mott[:, None]) * (1.0 - 0.35 * rootk[:, None])
    rgb = np.where(m[:, None], c, rgb)
    rough = np.where(m[:, None], np.array([[1.0, 0.88, 0.0]]), rough)
    # the arrowhead: faceted stone with its rune
    m = gp == P_ARROW
    if m.any():
        line, halo = arrow_rune(co, vn)
        c = lin(col['stone'])[None] * 1.1 * cellk * (0.95 + 0.06 * mott[:, None])
        c = c * (1 - (crk * 0.75)[:, None]) + lin(col['crack'])[None] * (crk * 0.75)[:, None]
        c = c * (1 - (halo * 0.18)[:, None]) + lin(col['rune_deep'])[None] * (halo * 0.18)[:, None]
        c = c * (1 - (line * 0.92)[:, None]) + lin(col['rune'])[None] * (line * 0.92)[:, None]
        rgb = np.where(m[:, None], c, rgb)
        glow = np.where(m, np.clip(0.25 * line + 0.34 * halo, 0, 1), glow)
    # the wing struts: stone, banded in ring plates
    m = gp == P_WING
    bands = np.exp(-(((t * 9.0) % 1.0 - 0.5) / 0.08) ** 2)
    c = lin(col['stone'])[None] * 1.1 * cellk * (0.98 + 0.08 * mott[:, None]) * (1.0 - 0.25 * bands[:, None])
    c = c * (1 - (crk * 0.7)[:, None]) + lin(col['crack'])[None] * (crk * 0.7)[:, None]
    rgb = np.where(m[:, None], c, rgb)
    return np.clip(rgb, 0.0, 1.0), rough, glow


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        rgb, rough, glow = _body_paint(_inputs(ob), PALETTE)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.add_attr(ob, 'glow', glow)
    for ob in fins:
        rgb, rough, glow = _fin_paint(ob)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.add_attr(ob, 'glow', glow)
    for ob in props:
        rgb, rough, glow = _prop_paint(ob)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rough)
        S.add_attr(ob, 'glow', glow)


def body_material(name: str, attr: str, pal: dict, marks):
    """The body's colour pass: the painted attribute plus the granite's dense flecks per pixel (dark, pale and warm
    grains of a millimetre or two; 4-details panel 6), fewer on the lighter stone, none in the cracks, the runes or the
    mouth."""
    m, nb = new_mat(name)
    base = nb.attribute(attr).outputs['Color']
    pos = nb.coords().outputs['Object']
    light = nb.attribute('light').outputs['Fac']
    crack = nb.attribute('crack').outputs['Fac']
    rune = nb.attribute('rune').outputs['Fac']
    mouth = nb.attribute('mouth').outputs['Fac']
    ear_in = nb.attribute('ear_in').outputs['Fac']
    col = colours(pal)
    keep = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.math('MAXIMUM', nb.math('MAXIMUM', crack, ear_in), nb.math('MAXIMUM', rune, mouth))),
                   nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', light, 0.85)))
    warp = nb.vmath('ADD', pos, nb.vmath('SCALE', nb.comb(nb.noise(pos, 60.0, 1.0, 0.5), nb.noise(nb.vmath('ADD', pos, nb.comb(1.7, 0.3, 2.9)), 60.0, 1.0, 0.5), 0.0), scale=0.003))
    dark = nb.math('MULTIPLY', nb.smooth(nb.voronoi(warp, 240.0, 'F1'), 0.26, 0.17), keep)
    c = nb.mix(nb.math('MULTIPLY', dark, 0.75), base, nb.rgb(C.lin(col['fleck_dark'])))
    warm = nb.math('MULTIPLY', nb.smooth(nb.voronoi(nb.vmath('ADD', warp, nb.comb(-5.3, 2.9, 4.1)), 150.0, 'F1'), 0.24, 0.16), keep)
    warm = nb.math('MULTIPLY', warm, nb.smooth(nb.noise(nb.vmath('ADD', pos, nb.comb(2.2, 5.1, 0.4)), 25.0, 1.0, 0.5), 0.45, 0.6))
    c = nb.mix(nb.math('MULTIPLY', warm, 0.6), c, nb.rgb(C.lin(col['crack_edge'])))
    pale = nb.math('MULTIPLY', nb.smooth(nb.voronoi(nb.vmath('ADD', warp, nb.comb(3.1, 7.7, 1.3)), 320.0, 'F1'), 0.2, 0.12), keep)
    c = nb.mix(nb.math('MULTIPLY', pale, 0.6), c, nb.rgb(C.lin(col['fleck_pale'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """The shape preview: the paint (plates, cracks, the light face and belly, the grin, the runes glowing)."""
    if _LAST and _LAST.get('n') == len(co):
        I = {k: _LAST[k] for k in ('crack', 'gap', 'dw', 'light', 'chips', 'bchips', 'hairline', 'pits', 'lpits', 'crease',
                                     'nostril', 'lash', 'rune', 'halo', 'ear_in', 'veins', 'sole', 'mouth')}
        I['top'] = _LAST['plate_top']
        I.update({'co': _LAST['base'], 'pid': _LAST['plate_id'], 'kind': _LAST['plate_kind']})
        rgb, _r, glow = _body_paint(I, PALETTE)
        g = glow[:, None]
        return rgb * (1 - g) + lin(PALETTE['accent'])[None] * 1.6 * g
    z = zones(co, vn)
    light = (z['face'] | z['belly'])[:, None]
    return np.where(light, lin(PALETTE['belly'])[None], lin(PALETTE['body'])[None])


# ============================================================================= clips
# the stone ears flick only a little; the half-folded wings stay folded at rest (an opening lifts them into a sail);
# the low curled tail keeps most of its swing
CLIP_CALM = {
    '*': {'ear': 0.6, 'tail': 0.8},
    'idle': {'ear': 0.6, 'tail': 0.8, 'wing': 0.4},
    'battle_idle': {'ear': 0.6, 'tail': 0.8, 'wing': 0.4},
    'look_around': {'ear': 0.6, 'tail': 0.8, 'wing': 0.4},
    # round 3: in ko the wings open to about half (2.5 x ko's slight opening): rolled onto its side, the lower wing then
    # lies out along the ground instead of pointing into it (folding them in pushed it down)
    'ko': {'ear': 0.3, 'tail': 0.6, 'wing': 2.5, 'head': 0.5},
    'hit_heavy': {'ear': 0.4, 'tail': 0.7, 'head': 0.45},
    # round 2: the knocked-aside head turns only half as far, so the squeezed lids stay in view (they hid under the brows)
    'hit': {'ear': 0.6, 'tail': 0.8, 'head': 0.35},
}


def calm_group(bone: str) -> str | None:
    """CLIP_CALM groups: the ears, the tail and the wings by their chains, and the head bone on its own."""
    if bone == 'head':
        return 'head'
    pre = bone.split('.')[0]
    return pre if '.' in bone and pre in ('ear', 'tail', 'wing') else None

REVIEW = {'centre': (0.0, 0.07, 0.5), 'size': 1.4, 'head': ((0.0, -0.12, 0.77), 0.64)}
