"""Tumblefox at Art 2.1 Ultra (docs/ART_2_DETAIL.md §9; the recipe contract tools/blender/monsters/breeds/RECIPE.md).

A small, slim, springy fox on four light legs with a huge fluffy spiral tail (chatgpt/monsters/02-tumblefox; the card
decides the part counts: exactly one tail, four legs, two ears). From the pictures (the hero wins, 2-turnaround.png
gives the measurements, read at 0.9 m tall):
  - a big round head (chibi) with a narrow pointed muzzle, a small dark nose and a wide closed smile with two tiny
    fangs; big round glossy eyes with bright whites inside a dark plum mask band that runs across the eyes and over
    the bridge; dark plum brows; a spiky orange tuft on the crown; a cream cheek ruff flaring out at the sides;
  - tall pointed cupped ears (tumblefox_ears) with cream fluff inside and dark plum tips;
  - a slim body, a fluffy cream chest bib and a cream underside; thin legs in dark plum socks; round four-toed paws
    with tiny claws and mauve pads;
  - the tail (tumblefox_tail): a spiral as big as the body over the rump, orange with a cream tip and outer coil.
Fur: long and fluffy on the tail, the chest and the cheeks; medium on the back; short and velvety on the face, the
ears and the legs.

Metres; the monster faces −Y, Z is up, +X is its left. Size: 0.9 × Puddlepup (the card), HEIGHT_UNITS 135 → 0.9 m.
Palette: CONTENT §2.2 #2 (#D9733B / #F7F1E8 / #3B3240 / #2A1E22); variants: src/art/monster/variants.ts
(Town Crier: deeper red-orange, gold mask and socks, and a brass hand-bell on a red ribbon (a prop); Glitch: mint and
hot pink with blocky pixel patches on the tail, the ears and a flank, paint only).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from lib import common as C
from lib import mesh as M
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3
from monsters.breeds import tumblefox_ears as E
from monsters.breeds import tumblefox_tail as T

ID = 'tumblefox'
LOOK = 'tumblefox-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 135                  # 0.9 × Puddlepup (the card's size line): modelled 0.9 m tall

PALETTE = {'body': '#D9733B', 'belly': '#F7F1E8', 'accent': '#3B3240', 'eye': '#2A1E22'}
# variants.ts order (COLOR_1, COLOR_2). 'props': the rigid parts only this variant wears (lo_props_town-crier)
VARIANTS = {
    'town-crier-tumblefox': {'body': '#C8522B', 'belly': '#FFF7E8', 'accent': '#F2C14E', 'eye': '#2A1E22', 'props': ['bell', 'ribbon']},
    'glitch-tumblefox': {'body': '#2DE2A6', 'belly': '#F4F4F4', 'accent': '#FF3D81', 'eye': '#101014', 'glitch': True},
}
NOSE_HEX = '#1B1416'
RIBBON_HEX = '#C4302B'              # the card's "red ribbon" (CONTENT has no colour for it)
BRASS_HEX = VARIANTS['town-crier-tumblefox']['accent']


def marking_hex(h: str) -> str:
    """A dark accent (the plum mask and socks) painted more saturated and a little lighter, so after the baked AO, each
    lock's shading and the film grade it still reads as its CONTENT colour, red and blue above green (review 1 measured
    the rendered #3B3240 mask at #383B3C to #464D4C: neutral grey). Light accents (Town Crier's gold, Glitch's pink)
    are left as they are."""
    import colorsys
    r, g, b = C.srgb(h)
    hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
    if vv > 0.45:
        return h
    r, g, b = colorsys.hsv_to_rgb(hh, min(1.0, ss * 1.9), min(1.0, vv * 1.32))
    return '#%02x%02x%02x' % tuple(int(round(c * 255)) for c in (r, g, b))


def colours(pal: dict) -> dict:
    """Every derived colour of a palette (the base or a variant)."""
    fur, cream, eye = pal['body'], pal['belly'], pal['eye']
    acc = marking_hex(pal['accent'])
    return {
        'fur': fur, 'cream': cream, 'plum': acc,
        'ear_cream': C.mix_hex(cream, '#FFE2BC', 0.32),
        'lid': C.mix_hex(acc, '#A48AAE', 0.28),
        'brow': C.mix_hex(eye, acc, 0.4),
        'lash': C.mix_hex(eye, '#000000', 0.5),
        'pad': C.mix_hex(acc, '#D8A2B2', 0.42),
        'claw': C.mix_hex('#E8D8C6', acc, 0.18),     # review 2: small pale claws (4-details panel 3)
        'blush': C.mix_hex(fur, '#F0705E', 0.45),
        'tuft': C.shade_hex(fur, 0.94),
        'crown': C.mix_hex(fur, '#FFB27A', 0.22),
        'whisker': C.mix_hex(fur, '#4A2A22', 0.6),
        'mouth': C.mix_hex(eye, '#3A2028', 0.4),
        'glitch2': C.mix_hex(acc, cream, 0.38),
    }


def tuft_colour(pal: dict) -> str:
    return colours(pal)['tuft']


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


# ----------------------------------------------------------------------------- the head
HEAD_C = Vector((0.0, -0.218, 0.632))
HEAD_R = (0.172, 0.128, 0.145)
EYE_C = {s: Vector((0.081 * s, -0.329, 0.614)) for s in (1, -1)}
EYE_R = 0.036
EYE_AX = (1.08, 1.0)                # the lens: half width, half height (× EYE_R): wide round eyes
EYE_DEPTH = (0.58, 0.26)
NOSE_C = Vector((0.0, -0.452, 0.552))     # round 2: the muzzle ~30% longer (review 1)
MUZZLE = ((0.0, -0.392, 0.533), (0.032, 0.055, 0.02))
CHEEK = (0.0, -0.262, 0.556, (0.185, 0.1, 0.068))
E.configure(HEAD_C, HEAD_R)


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye (+Z of its dome looks out, a little forward of the head's normal)."""
    c = EYE_C[s]
    surf_n = Vector(((c.x - HEAD_C.x) / HEAD_R[0] ** 2, (c.y - HEAD_C.y) / HEAD_R[1] ** 2, (c.z - HEAD_C.z) / HEAD_R[2] ** 2)).normalized()
    look = (surf_n * 0.62 + Vector((0, -1, 0)) * 0.38).normalized()
    look = (look + Vector((0, 0, 0.04))).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


LID_LASH, LID_DROP, LID_W = 0.1, 0.16, 0.92      # the closed lid's lash line: ye = −(LASH + DROP·(1 − (xe/W)²))·EYE_R


def blink_pivot(s: int):
    """The blink bone sits behind the lens at the closed lid's lash height (Puddlepup P1.2): a blink squashes the lens
    onto the lash line and sinks it into the head, showing the closed lid sculpted under it."""
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.72, 0.04, 0.2)
ATLAS_DENSITY = {'lo_eyes': 1.6, 'lo_props': 1.2}
BODY_TRIS = 52000
CARD_LAYERS = 3
CARD_SHADE = 1.0                    # review 2: cream cards read grey; they take the skin's colour as it is


# ----------------------------------------------------------------------------- body parts
def _orient(long_axis: Vector, width_axis: Vector) -> tuple[float, float, float]:
    d = long_axis.normalized()
    w = (width_axis - d * width_axis.dot(d)).normalized()
    n = w.cross(d).normalized()
    m = Matrix((w, d, n)).transposed()
    e = m.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def head_parts() -> list[Part]:
    return [
        Part('head', 'sphere', loc=tuple(HEAD_C), radius=1.0, scale=HEAD_R),
        # the lower face widens into the cheek ruff (the head is onion-shaped from the front, widest at the cheeks)
        Part('cheeks', 'sphere', loc=CHEEK[:3], radius=1.0, scale=CHEEK[3]),
        # a narrow pointed muzzle: a wedge narrowing to the nose, and the lower jaw under it
        Part('snout', 'tube', loc=(0.0, -0.3, 0.588), to=(0.0, -0.436, 0.553), radius=0.052, r2=0.021),
        Part('muzzle', 'sphere', loc=MUZZLE[0], radius=1.0, scale=MUZZLE[1]),
        # round 1: fills the crease between the chin and the chest (a dark notch at the throat)
        Part('throat', 'sphere', loc=(0.0, -0.335, 0.49), radius=1.0, scale=(0.06, 0.05, 0.045)),
        Part('nose', 'sphere', loc=tuple(NOSE_C), radius=0.0195, scale=(1.3, 0.85, 0.85)),
        Part('neck', 'capsule', loc=(0.0, -0.215, 0.54), to=(0.0, -0.25, 0.43), radius=0.095),
    ] + cheek_tufts() + crown_spikes()


# round 2 (review 1): big cream cheek tufts flaring past the skull, so the face is heart-shaped and about 1.3x the
# skull's width (1-hero.png, 2-turnaround.png front). Each: (root, direction, length, thickness)
# review 2: the cards stuck straight out as a grey moustache, and a lobe pointing down read as a chin tuft. The ruff is
# now its own cream geometry (the bake lights it like the head), each lobe flat across the face like a feather and
# sweeping out and slightly up and back; only short cards at the lobes' ends
CHEEK_TUFTS = [((0.125, -0.27, 0.556), (1.0, 0.3, 0.22), 0.1, 0.044),
               ((0.128, -0.266, 0.546), (1.0, 0.36, -0.05), 0.108, 0.046),
               ((0.122, -0.258, 0.534), (0.92, 0.42, -0.32), 0.094, 0.042)]


def cheek_tufts() -> list[Part]:
    out = []
    for i, (root, d, ln, th) in enumerate(CHEEK_TUFTS):
        for s in (1, -1):
            r = Vector((root[0] * s, root[1], root[2]))
            dv = Vector((d[0] * s, d[1], d[2])).normalized()
            up = Vector((0.0, 0.0, 1.0))
            wide = (up - dv * up.dot(dv)).normalized()          # the lobe's width stands upright: flat across the face
            out.append(Part(f'cheektuft{i}{"L" if s > 0 else "R"}', 'fin', loc=tuple(r + dv * (ln * 0.5)), radius=ln * 0.5,
                            scale=(th / (ln * 0.5), 1.0, 0.5 * th / (ln * 0.5)), taper=0.86, rot=_orient(dv, wide)))
    return out


LEGS = {'FL': (0.105, -0.205), 'FR': (-0.105, -0.205), 'BL': (0.108, 0.185), 'BR': (-0.108, 0.185)}
TOE_DX = (-0.043, -0.0145, 0.0145, 0.043)
SOCK_TOP = {'F': 0.16, 'B': 0.168}
TOE_R = (0.0118, 0.0172, 0.0152)


def toe_centres(leg: str) -> list[Vector]:
    x, y = LEGS[leg]
    return [Vector((x + dx, y - 0.083 + abs(dx) * 0.3, 0.017)) for dx in TOE_DX]


def claw_centres(leg: str) -> list[Vector]:
    x, y = LEGS[leg]
    return [Vector((x + dx * 1.02, y - 0.1 + abs(dx) * 0.3, 0.011)) for dx in TOE_DX]


def pad_spots(leg: str) -> list[tuple[Vector, tuple[float, float, float]]]:
    x, y = LEGS[leg]
    out = [(Vector((x, y - 0.024, 0.004)), (0.03, 0.025, 0.012))]
    for dx in TOE_DX:
        out.append((Vector((x + dx * 0.95, y - 0.08 + abs(dx) * 0.3, 0.003)), (0.0095, 0.012, 0.01)))
    return out


def paw_parts(leg: str) -> list[Part]:
    x, y = LEGS[leg]
    ps = [Part(f'foot{leg}', 'sphere', loc=(x, y - 0.03, 0.03), radius=0.05, scale=(1.12, 1.05, 0.62))]
    if leg[0] == 'F':
        ps += [Part(f'leg{leg}', 'tube', loc=(x * 0.92, y + 0.006, 0.235), to=(x, y - 0.01, 0.06), radius=0.046, r2=0.049),
               Part(f'elbow{leg}', 'sphere', loc=(x * 0.88, y + 0.012, 0.21), radius=0.055, scale=(0.95, 1.0, 1.3))]
    else:
        ps += [Part(f'shank{leg}', 'capsule', loc=(x * 0.9, y - 0.012, 0.195), to=(x, y + 0.02, 0.12), radius=0.048),
               Part(f'hock{leg}', 'tube', loc=(x, y + 0.02, 0.125), to=(x, y - 0.012, 0.058), radius=0.045, r2=0.047)]
    for i, c in enumerate(toe_centres(leg)):
        ps.append(Part(f'toe{leg}{i}', 'sphere', loc=tuple(c), radius=1.0, scale=TOE_R))
    for i, c in enumerate(claw_centres(leg)):
        ps.append(Part(f'claw{leg}{i}', 'sphere', loc=tuple(c), radius=1.0, scale=(0.0042, 0.0075, 0.0045)))
    return ps


def torso_parts() -> list[Part]:
    ps = [
        Part('chest', 'sphere', loc=(0.0, -0.255, 0.335), radius=0.112, scale=(1.08, 1.0, 1.15)),
        Part('neckbase', 'capsule', loc=(0.0, -0.265, 0.39), to=(0.0, -0.255, 0.53), radius=0.094),
        Part('body', 'capsule', loc=(0.0, -0.19, 0.28), to=(0.0, 0.19, 0.275), radius=0.094),
        Part('belly', 'sphere', loc=(0.0, -0.04, 0.237), radius=0.085, scale=(1.0, 1.7, 0.8)),
        Part('shoulder', 'sphere', loc=(0.074, -0.22, 0.28), radius=0.074, scale=(0.9, 1.0, 1.15), mirror=True),
        # the deep chest under the bib, a puffed mass from the throat down between the front legs (review 1: a puffed
        # bib, not a hanging beard)
        Part('brisket', 'sphere', loc=(0.0, -0.285, 0.36), radius=1.0, scale=(0.108, 0.08, 0.165)),
        Part('haunch', 'sphere', loc=(0.068, 0.165, 0.265), radius=0.084, scale=(0.84, 1.1, 1.12), mirror=True),
        Part('rump', 'sphere', loc=(0.0, 0.215, 0.297), radius=0.088, scale=(1.0, 0.95, 0.95)),
    ]
    for leg in LEGS:
        ps.extend(paw_parts(leg))
    return ps


def all_parts() -> list[Part]:
    return head_parts() + torso_parts()


def body_extras() -> list[bpy.types.Object]:
    """Joined into the voxel body: the two ear slabs and the spiral tail's tubes (new objects on every call). With
    extras, the build skins a proxy without them (heat weights fail over thin slabs) and the ears and the tail take
    their own weights (body_weight_regions)."""
    coll = C.collection('SurfaceParts')
    objs = [E.slab(s) for s in (1, -1)]
    for p in T.parts() + E.fluff_parts():
        objs.extend(M.build_part(p, coll, segments=32))
    return objs


# ----------------------------------------------------------------------------- carving (the high source only)
def mouth_curve() -> list[tuple[float, float]]:
    """A short philtrum under the nose, then a wide closed smile whose ends curl up into the cheeks (1-hero.png)."""
    nz = NOSE_C.z
    mid = nz - 0.035
    pts = [(0.0, nz - 0.014), (0.0, mid)]
    smile = []
    for k in range(-16, 17):
        t = k / 16
        smile.append((0.074 * t, mid + 0.02 * t * t + 0.013 * max(0.0, abs(t) - 0.72) / 0.28))
    return pts, smile


def mouth_dist(p: np.ndarray) -> np.ndarray:
    """Distance (in x, z) to the smile and philtrum on the front of the muzzle; far away elsewhere."""
    phil, smile = mouth_curve()
    d = np.minimum(S.polyline_dist(p[:, 0], p[:, 2], phil), S.polyline_dist(p[:, 0], p[:, 2], smile))
    return np.where(p[:, 1] < -0.32, d, 9.0)


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens, the soft round closed lid (a bulge) and its lash line, hidden until a blink sinks the lens."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax, ay = EYE_R * EYE_AX[0] * 0.98, EYE_R * EYE_AX[1] * 1.05
        r2 = (xe / ax) ** 2 + (ye / ay) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * EYE_R
        th = 0.003 + 0.002 * smooth(0.2, 1.0, xn * s)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    front = smooth(-0.31, -0.34, y)
    phil, smile = mouth_curve()
    md = np.minimum(S.polyline_dist(x, z, phil), S.polyline_dist(x, z, smile))
    groove = np.exp(-(md / 0.0026) ** 2) * front * (z < NOSE_C.z - 0.01) * (z > 0.49)
    nos = np.zeros_like(x)
    for s in (1, -1):
        dd = np.sqrt(((x - 0.0085 * s) / 1.4) ** 2 + (z - (NOSE_C.z - 0.005)) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.0035) ** 2))
    nos *= smooth(NOSE_C.y + 0.012, NOSE_C.y + 0.004, y)
    # the toes part from each other and the foot: a crease round each toe
    lip = np.zeros(len(co))
    tr = v3(TOE_R)
    for leg in LEGS:
        for c in toe_centres(leg):
            d = np.linalg.norm((co - v3(c)) / tr, axis=1)
            lip = np.maximum(lip, np.exp(-((d - 1.0) / 0.08) ** 2) * (co[:, 2] < 0.05))
    bulge, lash = closed_lid(co)
    disp = -0.0022 * groove - 0.004 * nos - 0.0045 * lip + 0.003 * bulge - 0.0012 * lash
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co, {'mouth': groove})
    S.add_attr(ob, 'lash', lash)
    S.add_attr(ob, 'lid', bulge)


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    rx, ry, rz = EYE_R * EYE_AX[0], EYE_R * EYE_AX[1], EYE_R * EYE_DEPTH[0]
    for v in bm.verts:
        v.co = Vector((v.co.x * rx, v.co.y * ry, v.co.z * rz))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((rx, ry, rz)))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


# ----------------------------------------------------------------------------- zones: where the coat goes and what it is
def leg_masks(p: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    out = {}
    for leg, (lx, ly) in LEGS.items():
        top = 0.265 if leg[0] == 'F' else 0.235
        r = np.hypot(x - lx, (y - ly + 0.02) * 0.8)
        # the paws are wider and longer than the legs (round 2: the outer front toe fell outside, into the belly cream)
        reach = 0.075 + 0.04 * smooth(0.09, 0.03, z)
        out[leg] = (r < reach) & (z < top + 0.02 * np.sign(x * lx))
    return out


def head_phi(p: np.ndarray) -> np.ndarray:
    """Degrees round the head from the front (0) to the sides (90) and beyond."""
    return np.degrees(np.arctan2(np.abs(p[:, 0]), -(p[:, 1] - HEAD_C.y)))


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    ear, ear_u, ear_inner, eL = E.zone(p)
    tail_on, tL = T.zone(p)
    # the cheek tufts flare out and down past z 0.47
    low = (zz > 0.47) | ((zz > 0.44) & (ax > 0.1) & (y < -0.2))
    head = ((in_ellipsoid(p, (0.0, -0.29, 0.635), (0.29, 0.21, 0.2)) < 1.0) & low & ~tail_on) | ear
    # the cheek tufts' tips reach out and down past that ellipsoid
    head |= (ax > 0.1) & (zz > 0.42) & (zz < 0.6) & (y < -0.18) & (y > -0.36) & ~tail_on
    muzzle = in_ellipsoid(p, MUZZLE[0], tuple(r * 1.05 for r in MUZZLE[1])) < 1.0
    nose = np.linalg.norm(p - v3(NOSE_C), axis=1) < 0.03
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = head & (y < -0.33) & (zz > 0.5) & (zz < 0.72) & (ax < 0.13) & ~ear
    crown = head & (zz > 0.7) & ~ear
    cheek = head & (ax > 0.07) & (zz < 0.588) & (y < -0.18) & ~ear & ~muzzle
    chin = head & (zz < 0.52) & (y < -0.34)
    legs = leg_masks(p)
    leg = np.zeros(len(p), bool)
    for m in legs.values():
        leg |= m
    leg &= ~head
    paw = leg & (zz < 0.08)
    toes = np.zeros(len(p), bool)
    for lg, (lx, ly) in LEGS.items():
        toes |= legs[lg] & (y < ly - 0.05) & (zz < 0.05)
    sole = zz < 0.012
    tail = tail_on & ~head & ~leg
    torso = ~head & ~leg & ~tail
    bib_w = np.interp(zz, BIB_Z, BIB_W)
    bib = (~head | chin) & ~tail & ~leg & (y < -0.19) & (ax < bib_w) & (zz > 0.15) & (zz < 0.54)
    zb = np.interp(y, BELLY_Y, BELLY_Z) + 0.006
    belly = torso & (zz < zb)
    back = torso & (zz > 0.335)
    ruff = torso & (zz > 0.4) & (y < -0.12) & ~bib
    ear_tip = ear & (ear_u > E.U_TIP - 0.04)
    # the crown tuft: an upward-flicking rosette between the ears (3-faces neutral, 4-details panel 1)
    tuft = head & ~ear & (np.hypot(x / 1.3, y - TUFT_C[1]) < 0.05) & (zz > 0.72)
    return {'ear': ear, 'ear_u': ear_u, 'ear_v': eL['v'], 'ear_inner': ear_inner, 'ear_up': eL['up'], 'ear_tip': ear_tip,
            'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face, 'crown': crown, 'cheek': cheek,
            'chin': chin, 'leg': leg, 'paw': paw, 'toes': toes, 'sole': sole, 'tail': tail, 'tail_s': tL['s'],
            'tail_out': tL['out'], 'tail_T': tL['T'], 'tail_L': tL, 'torso': torso, 'bib': bib, 'belly': belly, 'back': back,
            'ruff': ruff, 'legs': legs, 'tuft': tuft}


# ----------------------------------------------------------------------------- markings (evaluated at the roots)
MASK_PHI = [0.0, 14.0, 36.0, 55.0, 72.0, 84.0, 93.0]
MASK_ZC = [0.614, 0.613, 0.615, 0.611, 0.611, 0.614, 0.616]
MASK_H = [0.018, 0.025, 0.043, 0.038, 0.029, 0.014, 0.0]
# round 2 (review 1): only a thin orange blush between the mask and the cream; the cream cheek tufts
CREAM_PHI = [0.0, 14.0, 36.0, 55.0, 72.0, 84.0, 93.0, 118.0, 140.0]
CREAM_Z = [0.598, 0.592, 0.565, 0.565, 0.573, 0.568, 0.563, 0.553, 0.53]
BIB_Z = [0.14, 0.2, 0.27, 0.36, 0.46, 0.56]
BIB_W = [0.04, 0.07, 0.1, 0.12, 0.115, 0.1]
BELLY_Y = [-0.3, -0.15, 0.0, 0.15, 0.27]
BELLY_Z = [0.28, 0.232, 0.212, 0.21, 0.232]


def mask_band(p: np.ndarray, z: dict) -> np.ndarray:
    """The bandit mask: a band across the eyes and over the bridge, curving round the sides of the head to a point
    behind the eyes (2-turnaround.png, 3-faces.png)."""
    phi = head_phi(p)
    zc = np.interp(phi, MASK_PHI, MASK_ZC)
    h = np.interp(phi, MASK_PHI, MASK_H)
    band = smooth(h + 0.003, h - 0.003, np.abs(p[:, 2] - zc)) * (h > 0.002)
    # it crosses the bridge between the eyes and stops there (round 2: on the longer muzzle it ran down the snout)
    band = band * smooth(-0.42, -0.405, p[:, 1])
    return band * (z['head'] & ~z['ear'] & (p[:, 1] < HEAD_C.y + 0.05))


def cream_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """0 orange … 1 cream: the muzzle, the lower face and the cheek ruff, the chin and the chest bib, the underside, the
    inside of the ears and the tail's tip and outer coil."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    phi = head_phi(p)
    zc = np.interp(phi, CREAM_PHI, CREAM_Z)
    face = smooth(zc + 0.004, zc - 0.004, zz) * smooth(142.0, 122.0, phi) * (z['head'] & ~z['ear'])
    cream = np.maximum(face, ell_soft(p, MUZZLE[0], tuple(r * 1.12 for r in MUZZLE[1]), 0.1) * (zz < 0.575))
    # the long muzzle is cream on its sides and underside, up to the mask on the bridge (review 1)
    cream = np.maximum(cream, (z['head'] & ~z['ear'] & (y < -0.355)) * smooth(0.605, 0.597, zz))
    cream = np.maximum(cream, z['chin'] * 1.0)
    bib_w = np.interp(zz, BIB_Z, BIB_W)
    bib = smooth(bib_w + 0.012, bib_w - 0.012, ax) * smooth(-0.17, -0.21, y) * smooth(0.11, 0.15, zz) * smooth(0.56, 0.52, zz)
    cream = np.maximum(cream, bib * ~z['tail'] * ~(z['head'] & ~z['chin']) * ~z['leg'])
    zb = np.interp(y, BELLY_Y, BELLY_Z)
    cream = np.maximum(cream, z['torso'] * smooth(zb + 0.012, zb - 0.012, zz))
    # the inside of the hind thighs
    for s in (1, -1):
        cream = np.maximum(cream, ell_soft(p, (0.045 * s, 0.11, 0.19), (0.025, 0.065, 0.05), 0.25) * z['torso'])
    # the ears: the fluff in the hollow, not the rims
    v = z['ear_v']
    inner = z['ear_inner'] * smooth(0.07, 0.14, v) * smooth(0.93, 0.86, v) * smooth(0.93, 0.86, z['ear_u'])
    cream = np.maximum(cream, inner)
    cream = np.where(z['tail'], T.cream(z['tail_L']), cream)
    return np.clip(cream, 0.0, 1.0)


def plum_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """0 … 1 dark plum (the palette's accent): the mask band, the socks and the ear tips."""
    zz = p[:, 2]
    plum = mask_band(p, z)
    x, y = p[:, 0], p[:, 1]
    for leg, (lx, ly) in LEGS.items():
        # review 1: a feathered top edge, not a hard ring
        a = np.arctan2(x - lx, y - ly)
        top = SOCK_TOP[leg[0]] + 0.01 * np.sin(7.0 * a) + 0.006 * np.sin(13.0 * a + 1.3)
        plum = np.maximum(plum, z['legs'][leg] * ~z['head'] * smooth(top + 0.005, top - 0.005, zz))
    u, v = z['ear_u'], z['ear_v']
    back = z['ear'] & ~z['ear_inner']
    # review 1: plum on each ear's top third and down its back (outer) edge (4-details panel 5, 2-turnaround back)
    edge = smooth(0.7, 0.8, v) * smooth(0.1, 0.22, u)
    rim = np.maximum(smooth(0.14, 0.08, v), smooth(0.86, 0.92, v)) * smooth(0.42, 0.5, u)
    tips = back * np.maximum(smooth(0.5, 0.56, u), edge) + z['ear_inner'] * np.maximum(rim, smooth(0.84, 0.9, u))
    return np.clip(np.maximum(plum, tips * z['ear']), 0.0, 1.0)


def glitch_density(p: np.ndarray, z: dict) -> np.ndarray:
    """Where Glitch Tumblefox's pixel patches go (variant-glitch-tumblefox.png): the tail along its orange / cream
    border and its outer coil, the upper ears, a patch on each flank above the hind leg."""
    tl = z['tail_L']
    border = np.exp(-((T.cream(tl) - 0.5) / 0.36) ** 2)
    d = z['tail'] * (0.08 + 0.36 * border) * smooth(0.12, 0.25, tl['s']) * smooth(-0.6, 0.1, tl['out'])
    d = np.maximum(d, z['ear'] * 0.46 * smooth(0.42, 0.7, z['ear_u']))
    for s in (1, -1):
        d = np.maximum(d, ell_soft(p, (0.1 * s, 0.1, 0.24), (0.055, 0.085, 0.07), 0.3) * 0.42 * z['torso'])
    # review 2: a checker on the ear tips, coded 0.95 (the shader draws a checker where the density is over 0.9)
    u = z['ear_u']
    d = np.where(z['ear'] & (u > 0.38) & (u < 0.62), 0.95, d)
    return np.clip(d, 0.0, 0.95)


# ----------------------------------------------------------------------------- how the fur lies
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    k = len(p)
    # head: combed back from the nose, turning down below the eyes; up and back over the crown
    g = norm(p - v3((NOSE_C.x, NOSE_C.y - 0.03, NOSE_C.z)))
    wd = smooth(0.66, 0.56, zz)[:, None]
    g_head = norm(g * (1 - wd) + v3((0, 0.2, -1)) * wd * 1.3)
    # between the eyes: up and a little out (no starburst at the bridge)
    face_up = norm(np.stack([x * 4.0, np.full(k, 0.25), np.ones(k)], axis=1))
    wf = (smooth(-0.32, -0.37, y) * smooth(0.6, 0.64, zz) * smooth(0.1, 0.04, np.abs(x)))[:, None]
    g_head = norm(g_head * (1 - wf) + face_up * wf)
    # the cheek ruff flares out sideways and down
    ruff = norm(np.stack([np.sign(x) * 1.0, np.full(k, 0.42), np.full(k, 0.08)], axis=1))
    g_head = np.where(z['cheek'][:, None], ruff, g_head)
    g_head = np.where(z['ear'][:, None], z['ear_up'], g_head)
    # torso: back toward the tail along the top, down the sides
    side = np.clip(np.abs(n[:, 0]) * 1.2, 0, 1)[:, None]
    g_torso = norm(v3((0.0, 1.0, -0.1)) * (1 - side) + v3((0.0, 0.35, -1.0)) * side)
    g = np.where(z['torso'][:, None], g_torso, g_head)
    g = np.where(z['ruff'][:, None], np.tile(v3((0.0, 0.5, -1.0)), (k, 1)), g)
    g = np.where(z['belly'][:, None], np.tile(v3((0.0, 0.45, -0.8)), (k, 1)), g)
    g = np.where(z['bib'][:, None], np.tile(v3((0.0, -0.15, -1.0)), (k, 1)), g)
    g = np.where(z['leg'][:, None], np.tile(v3((0.0, -0.05, -1.0)), (k, 1)), g)
    g = np.where(z['tail'][:, None], z['tail_T'], g)
    g = np.where((z['head'] & ~z['bib'])[:, None], g_head, g)
    fan = norm(np.stack([x - TUFT_C[0], (y - TUFT_C[1]) * 0.7 - 0.012, np.full(k, 0.05)], axis=1))
    g = np.where(z['tuft'][:, None], fan, g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


def head_lock_params(p, n):
    """Short velvety fur on the face and the ears, longer on the crown, long on the cheek ruff, fluffy in the ears."""
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.05)
    W = np.full(k, 0.0095)
    lift = np.full(k, _rad(2.0))
    L = np.where(z['face'], 0.03, L)
    W = np.where(z['face'], 0.0066, W)
    L = np.where(z['crown'], 0.056, L)
    # the crown spikes keep their shape: short locks combed up them (review 2: the tuft's cards rendered brown)
    L = np.where(z['tuft'], 0.026, L)
    W = np.where(z['tuft'], 0.0075, W)
    W = np.where(z['crown'], 0.0108, W)
    L = np.where(z['cheek'], 0.068, L)
    W = np.where(z['cheek'], 0.0135, W)
    lift = np.where(z['cheek'], _rad(6.0), lift)
    L = np.where(z['chin'], 0.05, L)
    ear_back = z['ear'] & ~z['ear_inner']
    L = np.where(ear_back, 0.032, L)
    W = np.where(ear_back, 0.0072, W)
    L = np.where(z['ear_inner'], 0.048, L)
    W = np.where(z['ear_inner'], 0.0105, W)
    lift = np.where(z['ear_inner'], _rad(3.0), lift)
    near_eye = smooth(EYE_R * 1.15, EYE_R * 1.9, z['eye_d'])
    L = L * (0.5 + 0.5 * near_eye)
    W = W * (0.62 + 0.38 * near_eye)
    skip = ~z['head'] | z['bib'] | z['muzzle'] | z['nose'] | (z['eye_d'] < EYE_R * 1.12) | (mouth_dist(p) < 0.009)
    return np.where(skip, np.nan, W * 0.55), L, W, lift, z


def body_lock_params(p, n):
    """Medium on the back and sides, long on the chest bib and the neck ruff, short in the socks, big clumps on the
    tail (its fur is the fluffiest)."""
    z = zones(p, n)
    k = len(p)
    zz = p[:, 2]
    L = np.full(k, 0.064)
    W = np.full(k, 0.012)
    lift = np.full(k, _rad(2.5))
    # review 1: a puffed bib, not a stringy hanging beard
    L = np.where(z['bib'], 0.074, L)
    W = np.where(z['bib'], 0.017, W)
    lift = np.where(z['bib'], _rad(11), lift)
    L = np.where(z['bib'] & z['chin'], 0.055, L)
    L = np.where(z['ruff'], 0.088, L)
    W = np.where(z['ruff'], 0.015, W)
    L = np.where(z['belly'], 0.072, L)
    W = np.where(z['belly'], 0.0135, W)
    sock = z['leg'] & (zz < 0.18)
    L = np.where(z['leg'], np.where(sock, 0.042, 0.044), L)
    W = np.where(z['leg'], np.where(sock, 0.0105, 0.0095), W)
    lift = np.where(sock, _rad(8), lift)
    L = np.where(z['toes'], 0.022, L)
    W = np.where(z['toes'], 0.0075, W)
    tl = z['tail_L']
    L = np.where(z['tail'], 0.11 - 0.025 * smooth(0.8, 1.0, tl['s']), L)
    W = np.where(z['tail'], 0.025, W)
    lift = np.where(z['tail'], _rad(7.0), lift)
    skip = (z['head'] & ~z['bib']) | z['sole'] | (z['paw'] & (zz < 0.012))
    return np.where(skip, np.nan, W * 0.6), L, W, lift, z


def card_params(p, n, layer: int):
    """Soft fur cards for the outline (they fade out face-on). Layer 0 covers the coat; layer 1 the longer fringes
    (the cheek ruff, the chest bib, the neck ruff, the back ridge, the belly, the backs of the legs and the fluff in
    the ears); layer 2 the tail's long fluff (the fluffiest part)."""
    z = zones(p, n)
    k = len(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    head = z['head']
    if layer == 0:
        L = np.where(head, 0.05, 0.06)
        W = np.where(head, 0.032, 0.04)
        lift = np.where(head, _rad(4), _rad(6))
        L = np.where(z['cheek'], 0.045, L)
        L = np.where(z['ear'], 0.032, L)
        W = np.where(z['ear'], 0.022, W)
        lift = np.where(z['ear'], _rad(2), lift)
        L = np.where(z['leg'], np.where(zz < 0.18, 0.032, 0.044), L)
        W = np.where(z['leg'], 0.028, W)
        L = np.where(z['tail'], 0.078, L)
        W = np.where(z['tail'], 0.042, W)
        lift = np.where(z['tail'], _rad(9), lift)
        sp = np.where(head, np.where(z['ear'], 0.022, 0.018), 0.019)
        sp = np.where(z['leg'], 0.017, sp)
        sp = np.where(z['tail'], 0.021, sp)
        skip = (z['face'] | z['muzzle'] | z['nose'] | (z['eye_d'] < 0.07) | (z['chin'] & (y < -0.37)) | z['ear_inner']
                | (z['leg'] & (zz < 0.04)) | z['sole'] | (z['tail'] & (z['tail_s'] < 0.06)))
    elif layer == 1:
        L = np.full(k, 0.08)
        W = np.full(k, 0.04)
        lift = np.full(k, _rad(10))
        sp = np.full(k, 0.027)
        cheek = z['cheek'] & (zz < 0.58)
        bib = z['bib'] & ~z['chin'] & (zz < 0.44)
        ruff = z['ruff']
        ridge = z['torso'] & (zz > 0.43) & (np.abs(x) < 0.07) & (y > -0.15)
        belly = z['belly'] & (zz < 0.25)
        leg_back = np.zeros(k, bool)
        for lg, (lx, ly) in LEGS.items():
            leg_back |= z['legs'][lg] & (y > ly) & (zz > 0.17)
        tuft = z['tuft']
        ear_fluff = z['ear_inner'] & (z['ear_u'] > 0.15) & (z['ear_u'] < 0.8) & (z['ear_v'] > 0.15) & (z['ear_v'] < 0.85)
        L = np.where(cheek, 0.058, L)
        W = np.where(cheek, 0.04, W)
        lift = np.where(cheek, _rad(4), lift)
        sp = np.where(cheek, 0.022, sp)
        L = np.where(bib, 0.06, L)
        W = np.where(bib, 0.05, W)
        lift = np.where(bib, _rad(9), lift)
        L = np.where(ruff, 0.095, L)
        L = np.where(belly, 0.075, L)
        L = np.where(leg_back, 0.05, L)
        W = np.where(leg_back, 0.03, W)
        L = np.where(ear_fluff, 0.08, L)
        W = np.where(ear_fluff, 0.03, W)
        lift = np.where(ear_fluff, _rad(28), lift)
        sp = np.where(ear_fluff, 0.014, sp)
        L = np.where(tuft, 0.07, L)
        W = np.where(tuft, 0.034, W)
        lift = np.where(tuft, _rad(34), lift)
        sp = np.where(tuft, 0.014, sp)
        fringe = cheek | bib | ruff | ridge | belly | leg_back | ear_fluff
        skip = ~fringe | z['face'] | z['muzzle'] | (z['eye_d'] < 0.09) | (z['chin'] & (y < -0.37)) | z['tail']
    else:
        # the tail's long fluff: longer on the outer coil, standing out from the brush
        tl = z['tail_L']
        L = 0.118 + 0.022 * smooth(-0.2, 0.8, tl['out']) - 0.03 * smooth(0.85, 1.0, tl['s'])
        W = np.full(k, 0.05)
        lift = np.full(k, _rad(13))
        sp = np.full(k, 0.022)
        skip = ~z['tail'] | (tl['s'] < 0.08)
    # no cards where cream meets orange or plum meets orange (a card of one colour over the other glitters)
    cream = cream_mask(p, z)
    plum = plum_mask(p, z)
    skip = skip | ((cream > 0.06) & (cream < 0.94)) | ((plum > 0.06) & (plum < 0.94))
    # round 1: none by the brows (they took the brow's colour: grey fur on the forehead), none in the orange strip under
    # the mask (orange cards splayed over the cream ruff, brown from the side); the cheek ruff's cards are cream only
    mirrored = p.copy()
    mirrored[:, 0] = np.abs(x)
    brows = in_ellipsoid(mirrored, (0.073, -0.33, 0.68), (0.045, 0.06, 0.028)) < 1.0
    under_mask = head & ~z['ear'] & (head_phi(p) < 110.0) & (zz < 0.62) & (zz > 0.5) & (cream < 0.94) & (plum < 0.5)
    in_mask = head & ~z['ear'] & (plum > 0.06)
    # review 2 prep: grey and brown cards at the cheek tufts' roots (the crease's AO) and orange cards from the side of
    # the head hanging down over the cream tufts
    tuft_root = np.zeros(k, bool)
    for root, _d, _ln, _th in CHEEK_TUFTS:
        tuft_root |= np.linalg.norm(mirrored - v3(root), axis=1) < 0.04
    over_tufts = head & ~z['ear'] & (head_phi(p) > 70.0) & (zz > 0.55) & (zz < 0.64) & (cream < 0.94)
    in_mask = in_mask | tuft_root | over_tufts
    # review 2: only short cards at the ends of the cheek lobes; none on the chin and throat (it read as a beard)
    lobe_base = np.zeros(k, bool)
    for root, _d, _ln, _th in CHEEK_TUFTS:
        lobe_base |= np.linalg.norm(mirrored - v3(root), axis=1) < 0.062
    chin_beard = ((z['chin'] | z['bib']) & (zz > 0.44)) | (head & (zz < 0.53) & (np.abs(x) < 0.07))
    # review 2: the tail's centre showed grey cards in its pocket: none on the inner faces of the disc
    tlc = z['tail_L']
    disc_face = z['tail'] & (((np.abs(n @ T.NX) > 0.5) & (tlc['theta'] > 450.0)) | (tlc['theta'] > 560.0))
    in_mask = in_mask | z['cheek'] | chin_beard | disc_face | (mouth_dist(p) < 0.02) | z['tuft']
    skip = skip | brows | under_mask | in_mask | (z['cheek'] & (cream < 0.94))
    return np.where(skip, np.nan, sp), L, W, lift, z


# ----------------------------------------------------------------------------- the crown tuft
# Round 2 (review 1: flat petals with dark blots, a daisy decal; then pale spikes): the tuft is fur like the rest of the
# coat: small spike lobes in the body (the locks bake onto them) and a rosette of lifted orange cards (card layer 1,
# zone 'tuft'). There is no separate lo_tuft.
TUFT_C = (0.0, -0.288)                  # its centre (x, y) on the crown, between the ears
# (x, y, fan°, elevation°, length, base radius): spikes flicking up and out from the crown
CROWN_SPIKES = [(0.0, -0.312, 0, 55, 0.062, 0.017), (-0.022, -0.304, -28, 60, 0.058, 0.016), (0.022, -0.304, 28, 60, 0.058, 0.016),
                (-0.038, -0.288, -60, 52, 0.05, 0.015), (0.038, -0.288, 60, 52, 0.05, 0.015), (0.0, -0.29, 0, 80, 0.068, 0.018),
                (-0.016, -0.272, -150, 66, 0.052, 0.015), (0.016, -0.272, 150, 66, 0.052, 0.015)]


def _skull_z(x: float, y: float) -> float:
    q = 1.0 - (x / HEAD_R[0]) ** 2 - ((y - HEAD_C.y) / HEAD_R[1]) ** 2
    return HEAD_C.z + HEAD_R[2] * math.sqrt(max(q, 0.0))


def crown_spikes() -> list[Part]:
    out = []
    for i, (x, y, fan, el, ln, r) in enumerate(CROWN_SPIKES):
        root = Vector((x, y, _skull_z(x, y) - 0.008))
        a, e = math.radians(fan), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))).normalized()
        side = Vector((0.0, 0.0, 1.0)).cross(d)
        if side.length < 1e-3:
            side = Vector((1.0, 0.0, 0.0))
        out.append(Part(f'crownspike{i}', 'fin', loc=tuple(root + d * (ln * 0.5)), radius=ln * 0.5,
                        scale=(r / (ln * 0.5), 1.0, r / (ln * 0.5)), taper=0.9, rot=_orient(d, side)))
    return out


# ----------------------------------------------------------------------------- paint (numpy, per source vertex)
_MASKS: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
_INNER: dict[str, np.ndarray] = {}
_TUFT: dict[str, np.ndarray] = {}


def _masks_of(ob, root: np.ndarray, pos: np.ndarray, kind: np.ndarray, tpos: np.ndarray):
    """The cream, plum and glitch masks a source is painted with, by the root (the markings follow the fur); a lock
    that crosses a border blends toward the colour under its tip along its length. Cached per source."""
    if ob.name not in _MASKS:
        zr = zones(root)
        cream = cream_mask(root, zr)
        plum = plum_mask(root, zr)
        glitch = glitch_density(root, zr)
        lock = kind > 0.5
        if lock.any():
            zp = zones(pos[lock])
            k = 0.6 * tpos[lock]
            cream[lock] = cream[lock] * (1 - k) + cream_mask(pos[lock], zp) * k
            # the mask keeps a clean edge (review 1): a plum lock blends less toward its tip
            plum[lock] = plum[lock] * (1 - 0.5 * k) + plum_mask(pos[lock], zp) * 0.5 * k
        _MASKS[ob.name] = (cream, plum, glitch)
    return _MASKS[ob.name]


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    """Per vertex of a body source: 'paint' = orange, cream or plum by root (linear RGB, unshaded), 'cream', 'shade' (a
    darker root and lighter tip on each lock), 'rough' = (1, roughness, clearcoat), 'glitch' (the patches' density)."""
    col = colours(pal)
    root = S.attr_array(ob, 'root').astype(np.float64)
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    pos = co.reshape(-1, 3).astype(np.float64)
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    lrand = S.attr_array(ob, 'lrand').astype(np.float64)
    cream, plum, glitch = _masks_of(ob, root, pos, kind, tpos)
    rgb = lin(col['fur'])[None, :] * (1 - cream[:, None]) + lin(col['cream'])[None, :] * cream[:, None]
    # the fluff inside the ears: its cream warmed a little so it survives the cup's shadow and the film grade's cool
    # shift (review 2 prep: it rendered grey-white, #918C84 to #B3AB9D in round 1)
    if ob.name not in _INNER:
        _INNER[ob.name] = zones(root)['ear_inner'].astype(float)
    warm = (_INNER[ob.name] * cream)[:, None]
    if ob.name not in _TUFT:
        _TUFT[ob.name] = zones(root)['tuft'].astype(float)
    crown = (_TUFT[ob.name] * (1 - cream))[:, None]
    rgb = rgb * (1 - crown) + lin(col['crown'])[None, :] * crown
    rgb = rgb * (1 - warm) + lin(col['ear_cream'])[None, :] * warm
    rgb = rgb * (1 - plum[:, None]) + lin(col['plum'])[None, :] * plum[:, None]
    shade = 0.72 + 0.3 * tpos + 0.07 * (lrand - 0.5)
    # the fluff inside the ears keeps light roots (it sits in the cup's shadow: dark roots read as a grey hole)
    if ob.name not in _INNER:
        _INNER[ob.name] = zones(root)['ear_inner'].astype(float)
    inner = _INNER[ob.name]
    shade = shade * (1 - inner) + (0.92 + 0.08 * tpos) * inner
    # review 2: the cream fur keeps lighter roots (the cards take the skin's colour: dark roots made grey cards)
    shade = shade * (1 - cream) + (0.84 + 0.16 * tpos) * cream
    # the crown spikes: light roots (review 3: they rendered rust brown, #9D582F)
    if ob.name not in _TUFT:
        _TUFT[ob.name] = zones(root)['tuft'].astype(float)
    tuftm = _TUFT[ob.name]
    shade = shade * (1 - tuftm) + (0.95 + 0.05 * tpos) * tuftm
    shade = np.where(kind < 0.5, 1.0, shade)
    is_lock = kind > 0.5
    rough = np.where(is_lock, 0.5 + 0.15 * np.abs(tpos - 0.45), 0.64)
    coat = np.where(is_lock, 0.14, 0.06)
    muz = ell_soft(root, MUZZLE[0], tuple(r * 1.1 for r in MUZZLE[1]), 0.1)
    rough = rough * (1 - muz) + 0.6 * muz
    coat = coat * (1 - muz) + 0.05 * muz
    glossy = ell_soft(pos, tuple(NOSE_C), (0.027, 0.022, 0.02), 0.06)
    pads = np.zeros(len(pos))
    claws = np.zeros(len(pos))
    for leg in LEGS:
        for c, r in pad_spots(leg):
            pads = np.maximum(pads, ell_soft(pos, tuple(c), r, 0.1))
        for c in claw_centres(leg):
            claws = np.maximum(claws, ell_soft(pos, tuple(c), (0.0055, 0.008, 0.0065), 0.1))
    plum_fur = plum * (1 - glossy)
    rough = rough * (1 - plum_fur) + 0.7 * plum_fur
    coat = coat * (1 - plum_fur) + 0.04 * plum_fur
    paw = smooth(0.07, 0.04, pos[:, 2]) * (kind < 0.5)
    rough = rough * (1 - paw) + 0.74 * paw
    coat = coat * (1 - paw) + 0.03 * paw
    rough = rough * (1 - glossy) + 0.2 * glossy
    coat = coat * (1 - glossy) + 0.75 * glossy
    rough = rough * (1 - pads) + 0.52 * pads
    coat = coat * (1 - pads) + 0.25 * pads
    rough = rough * (1 - claws) + 0.48 * claws
    coat = coat * (1 - claws) + 0.15 * claws
    return {'paint': rgb, 'cream': cream, 'shade': shade, 'glitch': glitch,
            'rough': np.stack([np.ones(len(pos)), rough, coat], axis=1)}


def prop_arrays(ob: bpy.types.Object) -> tuple[np.ndarray, np.ndarray]:
    """Town Crier's ribbon and brass bell: the same paint in every pass (only that variant wears them)."""
    part = S.attr_array(ob, 'part')
    brass = lin(BRASS_HEX)
    rgb = np.where((part < 0.5)[:, None], lin(RIBBON_HEX)[None], brass[None])
    rgb = np.where((part > 1.5)[:, None], (brass * 0.55)[None], rgb)
    rough = np.where(part < 0.5, 0.55, 0.22)
    coat = np.where(part < 0.5, 0.12, 0.85)
    return rgb, np.stack([np.ones(len(part)), rough, coat], axis=1)


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
    """Store the paint attributes on every source: 'paint' (base), 'paint_<short>' per variant, 'rough', 'cream',
    'shade' and 'glitch' (the body sources); the props' ribbon and brass."""
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'cream', a['cream'])
        S.add_attr(ob, 'shade', a['shade'])
        S.add_attr(ob, 'glitch', a['glitch'])
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), paint_arrays(ob, var)['paint'])
    for ob in props:
        rgb, rc = prop_arrays(ob)
        S.set_colour_attr(ob, 'paint', rgb)
        S.set_colour_attr(ob, 'rough', rc)
        for vid in VARIANTS:
            S.set_colour_attr(ob, U.variant_attr(vid, ID), rgb)


# ----------------------------------------------------------------------------- paint (nodes: the crisp details, per pixel)
def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def _arc(nb: NB, pos, xc: float, zc: float, half: float, bend: float, th: float, ymax: float):
    """A curved stroke on the face: z = zc + bend·(1 − ((x − xc)/half)²), `th` thick, tapered at both ends, only on
    surfaces in front of y = ymax."""
    x, y, z = nb.sep(pos)
    t = nb.math('DIVIDE', nb.math('SUBTRACT', x, xc), half)
    zl = nb.math('ADD', zc, nb.math('MULTIPLY', bend, nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', t, t))))
    taper = nb.smooth(nb.math('ABSOLUTE', t), 1.0, 0.45)
    w = nb.math('MULTIPLY', th, nb.math('ADD', 0.35, nb.math('MULTIPLY', 0.65, taper)))
    d = nb.math('DIVIDE', nb.math('ABSOLUTE', nb.math('SUBTRACT', z, zl)), w)
    line = nb.smooth(d, 1.0, 0.55)
    return nb.math('MULTIPLY', nb.math('MULTIPLY', line, nb.smooth(nb.math('ABSOLUTE', t), 1.05, 0.95)), nb.smooth(y, ymax, ymax - 0.01))


def _glitch(nb: NB, pos, density, cell: float):
    """Blocky square pixels: a random number per grid cell of `cell` metres, on where it's below `density`."""
    q = nb.vmath('FLOOR', nb.vmath('SCALE', pos, scale=1.0 / cell))
    wn = nb.new('ShaderNodeTexWhiteNoise')
    wn.noise_dimensions = '3D'
    nb.link(q, wn.inputs['Vector'])
    r = wn.outputs['Value']
    return nb.math('LESS_THAN', r, density), r


def body_material(name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
    """Emission = the painted attribute × each lock's shade, with the crisp marks evaluated per pixel: the brows, the
    blush, the nose, the smile and its two tiny fangs, the whisker dots, the closed lids and their lash lines, the
    pads and toe beans, the claws, and Glitch's pixel patches."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 0.5)
    c = nb.attribute(attr).outputs['Color']
    if pal.get('glitch'):
        dens = nb.attribute('glitch').outputs['Fac']
        # round 2 (review 1: scattered flecks): blocky squares in clusters, a coarse grid switching patches on
        dcode = dens
        dens = nb.math('MINIMUM', dens, 0.48)
        cluster, _rc = _glitch(nb, nb.vmath('ADD', pos, (0.031, 0.017, 0.043)), 0.7, 0.1)
        dens = nb.math('MULTIPLY', nb.math('MULTIPLY', dens, cluster), 2.0)
        big, r1 = _glitch(nb, pos, dens, 0.04)
        small, _r2 = _glitch(nb, nb.vmath('ADD', pos, (0.0041, 0.0067, 0.0023)), nb.math('MULTIPLY', dens, 0.35), 0.02)
        on = nb.math('MAXIMUM', big, small)
        qx, qy, qz = nb.sep(nb.vmath('FLOOR', nb.vmath('SCALE', pos, scale=1.0 / 0.013)))
        chk = nb.math('FLOORED_MODULO', nb.math('ADD', nb.math('ADD', qx, qy), qz), 2.0)
        on = nb.math('MAXIMUM', on, nb.math('MULTIPLY', nb.math('GREATER_THAN', dcode, 0.9), chk))
        light = nb.math('LESS_THAN', r1, nb.math('MULTIPLY', dens, 0.28))
        pc = nb.mix(light, nb.rgb(C.lin(col['plum'])), nb.rgb(C.lin(col['glitch2'])))
        c = nb.mix(on, c, pc)
    # each lock's root-to-tip shade, warm (a near-white cream shaded neutrally read grey, round 1)
    shade = nb.attribute('shade').outputs['Fac']
    # round 2: warm only on the cream (a warm multiply pushed the plum toward brown)
    crm = nb.attribute('cream').outputs['Fac']
    eg = nb.math('ADD', 1.0, nb.math('MULTIPLY', crm, 0.12))
    eb = nb.math('ADD', 1.0, nb.math('MULTIPLY', crm, 0.35))
    c = nb.mix(1.0, c, nb.comb(shade, nb.math('POWER', shade, eg), nb.math('POWER', shade, eb)), blend='MULTIPLY')
    brow = None
    for s in (1, -1):
        e = _arc(nb, pos, 0.073 * s, 0.68, 0.028, 0.008, 0.0058, -0.3)
        brow = e if brow is None else nb.math('MAXIMUM', brow, e)
    c = nb.mix(brow, c, nb.rgb(C.lin(col['brow'])))
    blush = None
    for s in (1, -1):
        e = _ell(nb, pos, (0.095 * s, -0.335, 0.566), (0.028, 0.045, 0.011), 0.6)
        blush = e if blush is None else nb.math('MAXIMUM', blush, e)
    c = nb.mix(nb.math('MULTIPLY', blush, 0.45), c, nb.rgb(C.lin(col['blush'])))
    c = nb.mix(_ell(nb, pos, tuple(NOSE_C), (0.0265, 0.021, 0.0185), 0.08), c, nb.rgb(C.lin(NOSE_HEX)))
    mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.3, clamp=True), is_body)
    mid = NOSE_C.z - 0.035
    smile = _arc(nb, pos, 0.0, mid + 0.026, 0.066, -0.026, 0.0032, -0.32)
    phil = _ell(nb, pos, (0.0, -0.45, NOSE_C.z - 0.026), (0.0016, 0.03, 0.0095), 0.3)
    hooks = None
    for s in (1, -1):        # the corners curl up (1-hero)
        for hx, hz, hr in ((0.062, 0.026, 0.0036), (0.0655, 0.0285, 0.0036), (0.068, 0.0315, 0.0034), (0.0700, 0.035, 0.0032), (0.0712, 0.0385, 0.003)):
            e = _ell(nb, pos, (hx * s, -0.36, mid + hz), (hr, 0.05, hr * 0.95), 0.25)
            hooks = e if hooks is None else nb.math('MAXIMUM', hooks, e)
    hooks = nb.math('MULTIPLY', hooks, nb.smooth(nb.sep(pos)[1], -0.31, -0.325))
    mouth = nb.math('MAXIMUM', mouth, nb.math('MULTIPLY', nb.math('MAXIMUM', nb.math('MAXIMUM', smile, phil), hooks), is_body))
    c = nb.mix(mouth, c, nb.rgb(C.lin(col['mouth'])))
    # two tiny fangs peeking under the smile, either side of the philtrum: white points with a thin dark edge (white on
    # the cream muzzle needs the edge to read)
    fang, rim = None, None
    _phil, smile = mouth_curve()
    ygate = nb.smooth(nb.sep(pos)[1], -0.38, -0.395)
    for s in (1, -1):
        fx = 0.017 * s
        fz = min(smile, key=lambda q: abs(q[0] - fx))[1] - 0.0046
        e = _ell(nb, pos, (fx, -0.445, fz), (0.0031, 0.03, 0.0046), 0.15)
        o = _ell(nb, pos, (fx, -0.445, fz + 0.0004), (0.0046, 0.03, 0.0062), 0.15)
        fang = e if fang is None else nb.math('MAXIMUM', fang, e)
        rim = o if rim is None else nb.math('MAXIMUM', rim, o)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', rim, ygate), is_body), c, nb.rgb(C.lin(col['mouth'])))
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', fang, ygate), is_body), c, nb.rgb(C.lin('#FBF7EF')))
    dots = None
    for s in (1, -1):
        for dx, dz in ((0.024, 0.541), (0.034, 0.534), (0.03, 0.548), (0.041, 0.543)):
            e = _ell(nb, pos, (dx * s, -0.425, dz), (0.0021, 0.04, 0.0021), 0.2)
            dots = e if dots is None else nb.math('MAXIMUM', dots, e)
    dots = nb.math('MULTIPLY', dots, nb.smooth(nb.sep(pos)[1], -0.37, -0.385))
    c = nb.mix(nb.math('MULTIPLY', dots, 0.8), c, nb.rgb(C.lin(col['whisker'])))
    # the closed lid (under the lens; it shows only while a blink sinks the lens): the mask's plum, a touch darker,
    # and its lash line
    lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
    # round 2 (review 1: grey bulges with no lid line): a lighter plum lid under a strong dark lash line
    c = nb.mix(nb.math('MULTIPLY', lid, 0.85), c, nb.rgb(C.lin(col['lid'])))
    lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True), is_body)
    c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
    pad = None
    for leg in LEGS:
        for pc, pr in pad_spots(leg):
            e = _ell(nb, pos, tuple(pc), pr, 0.1)
            pad = e if pad is None else nb.math('MAXIMUM', pad, e)
    c = nb.mix(pad, c, nb.rgb(C.lin(col['pad'])))
    claw = None
    for leg in LEGS:
        for cc in claw_centres(leg):
            e = _ell(nb, pos, tuple(cc), (0.0055, 0.008, 0.0065), 0.12)
            claw = e if claw is None else nb.math('MAXIMUM', claw, e)
    c = nb.mix(claw, c, nb.rgb(C.lin(col['claw'])))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def eye_material(name: str, rough_pass: bool = False) -> bpy.types.Material:
    """Big round eyes: bright whites round a large dark brown iris (#2A1E22) with a warm rim and a big pupil, crisp
    catchlights up toward the key light, the upper lash line along the top (4-details.png panel 2)."""
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    rr = nb.vmath('LENGTH', nb.comb(rx, ry, 0.0))
    # round 1: the iris filled the dome and the whites vanished in the game's renderer; the reference shows white round it
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', rx, 0.6), nb.math('DIVIDE', nb.math('ADD', ry, 0.03), 0.68), 0.0))
    iris = C.lin_rgb(PALETTE['eye'])
    warm = C.lin_rgb(C.mix_hex(PALETTE['eye'], '#8A4A26', 0.55))
    sclera = C.lin_rgb('#F5F1EA')
    c = nb.ramp(ri, [(0.0, C.lin('#070506')), (0.5, C.lin('#070506')), (0.56, iris), (0.78, C.lin(C.mix_hex(PALETTE['eye'], '#8A4A26', 0.3))),
                     (0.9, warm), (0.96, C.lin('#1A1214')), (1.0, C.lin('#1A1214')), (1.04, sclera), (1.6, sclera)])
    # the whites shade a little toward the rim of the lens (a ball, not a sticker)
    edge = nb.math('MULTIPLY', nb.smooth(rr, 0.78, 1.0), nb.math('GREATER_THAN', ri, 1.0))
    c = nb.mix(nb.math('MULTIPLY', edge, 0.35), c, nb.rgb(C.lin('#B9B0A8')))
    # the catchlights sit up and toward the key light, the same way in both eyes (one light)
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, 0.22), nb.math('DIVIDE', nb.math('SUBTRACT', ry, 0.3), 1.15), 0.0)), 0.19, 0.16)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, 0.24), nb.math('ADD', ry, 0.3), 0.0)), 0.07, 0.054)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    # the upper lash line: dark over the top, a little lower and thicker at the outer corner
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', rx, side), 0.2, 0.9), 0.12)
    lash = nb.smooth(nb.math('ADD', ry, outer), 0.7, 0.8)
    c = nb.mix(lash, c, nb.rgb(C.lin('#140D10')))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- Town Crier's ribbon and brass bell (props)
COLLAR_C = Vector((0.0, -0.27, 0.49))
COLLAR_N = Vector((0.0, -0.42, 1.0)).normalized()     # the ring tilts: lower at the front, under the chin
COLLAR_R = (0.104, 0.118)                              # across, front-back
BELL_TOP = Vector((0.0, -0.402, 0.448))


def _collar_frame():
    e1 = Vector((1.0, 0.0, 0.0))
    e2 = COLLAR_N.cross(e1).normalized()               # back and up
    return e1, e2


def _ring(name: str, seg: int) -> bpy.types.Object:
    e1, e2 = _collar_frame()
    w, t = 0.0105, 0.0035
    bm = bmesh.new()
    rows = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        rad = e1 * math.cos(a) * COLLAR_R[0] + e2 * math.sin(a) * COLLAR_R[1]
        out = rad.normalized()
        c = COLLAR_C + rad
        rows.append([bm.verts.new(c + out * dr + COLLAR_N * dn) for dr, dn in ((-t, -w), (t, -w), (t, w), (-t, w))])
    for i in range(seg):
        a, b = rows[i], rows[(i + 1) % seg]
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    S.add_attr(ob, 'part', np.zeros(len(me.vertices)))
    return ob


BELL_PROFILE = [(0.0, 0.0), (0.006, -0.0008), (0.0105, -0.004), (0.0132, -0.011), (0.0142, -0.019), (0.0158, -0.027),
                (0.0195, -0.034), (0.024, -0.039), (0.0262, -0.0415), (0.0258, -0.0432), (0.0232, -0.0428), (0.019, -0.0385),
                (0.0135, -0.031), (0.0105, -0.02), (0.0075, -0.011), (0.0, -0.009)]


def _bell(name: str, seg: int) -> bpy.types.Object:
    """A small hand-bell hanging from the ribbon: a flared brass cup, a loop on top and the clapper under the lip."""
    bm = bmesh.new()
    axis = Vector((0.0, -0.18, 1.0)).normalized()      # hangs a little away from the chest
    side = Vector((1.0, 0.0, 0.0))
    fwd = axis.cross(side).normalized()
    rows = []
    for r, z in BELL_PROFILE:
        row = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            row.append(bm.verts.new(BELL_TOP + axis * z + (side * math.cos(a) + fwd * math.sin(a)) * r))
        rows.append(row)
    for j in range(len(rows) - 1):
        for i in range(seg):
            a, b = rows[j], rows[j + 1]
            f = bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    n_brass = len(bm.verts)
    # the clapper and the loop
    clap = bmesh.ops.create_uvsphere(bm, u_segments=max(8, seg // 2), v_segments=max(6, seg // 4), radius=0.0062)
    for v in clap['verts']:
        v.co = v.co + BELL_TOP + axis * -0.04
    n_major, n_minor, R, r = max(10, seg // 3), 6, 0.0058, 0.0019
    ring = []
    for i in range(n_major):
        a = 2 * math.pi * i / n_major
        c = BELL_TOP + axis * (R * 0.8 + R * math.sin(a)) + side * (R * math.cos(a))
        radial = (axis * math.sin(a) + side * math.cos(a)).normalized()
        ring.append([bm.verts.new(c + (radial * math.cos(2 * math.pi * k / n_minor) + fwd * math.sin(2 * math.pi * k / n_minor)) * r)
                     for k in range(n_minor)])
    for i in range(n_major):
        a, b = ring[i], ring[(i + 1) % n_major]
        for k in range(n_minor):
            bm.faces.new((a[k], a[(k + 1) % n_minor], b[(k + 1) % n_minor], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    part = np.ones(len(me.vertices))
    part[n_brass:n_brass + len(clap['verts'])] = 2.0
    S.add_attr(ob, 'part', part)
    return ob


def _build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    seg = (64 if not quick else 40) if high else 22
    ring = _ring(f'{tag}_ribbon', 96 if high else 36)
    bell = _bell(f'{tag}_bell', seg)
    return [ring, bell]


# Variant-only props (RECIPE.md): Town Crier's bell and ribbon export as `lo_props_town-crier`, shown only for that
# variant, and don't shadow the body's bake
build_props = _build_props


# ----------------------------------------------------------------------------- the rig's proportions (plans/quadruped.py)
TAIL_BONES = 6


def rig_p() -> dict:
    ed = E.tip(1) - E.root(1)
    pts = T.points(TAIL_BONES + 1)
    td = Vector(pts[1]) - Vector(pts[0])
    return {
        'hip': (0.0, 0.17, 0.275),
        'chest': (0.0, -0.2, 0.31),
        'head_c': tuple(HEAD_C),
        'head_r': 0.14,
        'ear_base': tuple(E.root(1)),
        'ear_dir': tuple(ed.normalized()),
        'ear_len': ed.length,
        'tail_base': pts[0],
        'tail_dir': tuple(td.normalized()),
        'tail_len': T.LENGTH,
        'tail_bones': TAIL_BONES,
        'tail_points': pts,
        'legs': {leg: (lx, ly, 0.255 if leg[0] == 'F' else 0.235) for leg, (lx, ly) in LEGS.items()},
        'knee_back': 0.025,
        'ankle_z': 0.035,
        'foot_len': 0.085,
        'leg_radius': 0.08,
        'stride': 0.13,
    }


def ear_weights(u: np.ndarray) -> dict[str, np.ndarray]:
    """head → ear.1 → ear.2 along the ear (the root stays with the head)."""
    w2 = smooth(0.45, 0.85, u)
    w1 = (1 - w2) * smooth(0.05, 0.3, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def tail_weights(s: np.ndarray, names: list[str]) -> dict[str, np.ndarray]:
    """hips → tail.1 … tail.N by the arc position along the spiral (U.chain_weights' blend, but on the dense centre
    line: the coarse bone polyline can't tell the coils apart)."""
    bones = [f'tail.{k + 1}' for k in range(TAIL_BONES) if f'tail.{k + 1}' in names]
    n = len(bones)
    w = {'hips': smooth(0.12, -0.02, s)}
    c = [(k + 0.5) / n for k in range(n)]
    raw = [np.clip(1.0 - np.abs(s - c[k]) * n, 0, 1) for k in range(n)]
    raw[0] = np.where(s < c[0], 1.0, raw[0])
    raw[-1] = np.where(s > c[-1], 1.0, raw[-1])
    tot = np.maximum(sum(raw), 1e-6)
    for k, b in enumerate(bones):
        w[b] = raw[k] / tot * (1 - w['hips'])
    return w


def body_weight_regions(co: np.ndarray, names: list[str]):
    regions = []
    on, u, _inner, L = E.zone(co)
    for s, tag in ((1, 'L'), (-1, 'R')):
        m = on & (L['s'] == s)
        if m.any() and f'ear.{tag}.1' in names:
            w = ear_weights(u[m])
            regions.append((m, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    tl = T.lookup(co)
    m = (tl['d'] < T.reach(tl) + 0.008) & (tl['s'] > 0.01)
    if m.any():
        regions.append((m, tail_weights(tl['s'][m], names)))
    return regions


def prop_weight_regions(co: np.ndarray, attr, names: list[str], mesh=None):
    """The ribbon and the bell ride the neck."""
    return [U.rigid(np.ones(len(co), bool), 'neck')]


# Fox ears are stiff, and the tail is as big as the body: calm both in every clip, more in the big poses.
CLIP_CALM = {
    '*': {'ear': 0.75, 'tail': 0.6},
    'ko': {'ear': 0.3, 'tail': 0.35},
    'hit_heavy': {'ear': 0.4, 'tail': 0.4},
    'hit': {'ear': 0.6, 'tail': 0.5},
    'win': {'ear': 0.6, 'tail': 0.45},
    'celebrate': {'tail': 0.45},
    'idle_happy': {'tail': 0.5},
    'strike': {'ear': 0.5, 'tail': 0.5},
    'sidestep_l': {'ear': 0.5, 'tail': 0.45},
    'sidestep_r': {'ear': 0.5, 'tail': 0.45},
}

FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the bright whites, the dark brown iris, pupil, catchlights and the '
             'upper lash line baked into the body atlas; the plum mask band across the eyes, the brows, the nose, the wide '
             'smile with two tiny fangs and the whisker dots are baked into the body. No face sheet and no morphs: '
             'expressions in clips\' `faces` are hints only. Blinking scales the blink bones (play `blink` over any clip): '
             'each lens squashes onto the closed lid\'s lash line and sinks into the head, showing the closed lid (mask '
             'plum, sculpted and painted on the body under the lens).')

REVIEW = {
    'centre': (0.08, 0.04, 0.42),
    'size': 1.3,
    'head': ((0.0, -0.29, 0.66), 0.64),
}
