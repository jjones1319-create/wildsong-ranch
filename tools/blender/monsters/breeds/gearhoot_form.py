"""Gearhoot's body (Art 2.1 Ultra; chatgpt/monsters/29-gearhoot): two rigid shells voxel-united into lo_body, a round
egg of a body (rigid on `hips`, with a riveted collar round its top) and a big round head (rigid on `head`) sitting in
the collar like a ball in a socket, so the owl's far head turn never tears the skin (the jaw lesson: separate shells, a
2-3 cm gap, each weighted rigid). The head's flat facial disc, its sockets and the brow mask are cut and carved here;
the plates, rivets and engravings are carved into the high source (gearhoot_carve.py).

Measured on 2-turnaround (front, side, back; 1.0 m to the ear tufts' tips, 1 px = 1.92 mm): the head 0.44 m wide and
0.45 m deep, its centre 0.72 m up, its face 0.26 m ahead of the body's centre line; the body 0.41 m wide, 0.46 m deep,
0.13-0.55 m up; the legs at x = +-0.11 m. Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import gearhoot_geo as G

# ----------------------------------------------------------------------------- the head (a ball in the collar)
HC = np.array([0.0, -0.035, 0.687])       # the head's centre and its pivot (the neck's top); rounds 1-2: 3.3 cm lower
HEAD_A = 0.222                             # half its width
HEAD_BF, HEAD_BF_LO = 0.31, 0.27           # its depth ahead of the centre (above / below the centre), cut by the face
HEAD_BB = 0.195                            # its depth behind the centre (round 1: shorter, a rounder head)
HEAD_UP, HEAD_LO = 0.2, 0.16               # its height above / below the centre (top 0.90, bottom 0.54)
HEAD_P = 2.2                               # the top's roundness (the profile's exponent above the centre)
HEAD_N = 2.5                               # the rings' squareness (round 1: a broader, flatter face)
Y_FACE = -0.257                            # the facial disc's plane
FACE_SOFT = 0.024                          # the rounding where the disc meets the head's sides

# ----------------------------------------------------------------------------- the body (an egg) and the collar
BC = np.array([0.0, -0.03, 0.31])         # the body's widest ring
BODY_A, BODY_BF, BODY_BB = 0.235, 0.25, 0.235
BODY_LO, BODY_UP = 0.18, 0.26              # bottom 0.13; the top is cut at the shoulder
BODY_P_UP = 3.6
BODY_P_LO = 2.6                            # a full, round bottom (2-turnaround front: +-0.25 m at 0.15 m)
Z_SHOULDER = 0.545
# round 1: a thin mid-brass rim (round, centred on the head's pivot); the opening is capped by the neck dome (a prop)
COLLAR = {'z': 0.548, 'a': 0.205, 'b': 0.205, 'bb': 0.205, 'tr': 0.014, 'tz': 0.013}

# ----------------------------------------------------------------------------- the eyes (s = +1 left: the monocle)
# round 1: both eyes forward on the facial disc, side by side (the normal eye read as round the side at 64 px)
# round 2: the eyes raised to ~58% down the head (they sat at 71% under a tall forehead), each lens flatter and sunk
# deeper into a socket (the normal eye bulged past the outline at three-quarter; the lens poked past the ring)
EYE = {1: {'x': 0.105, 'z': float(HC[2]) + 0.04, 'r': 0.06, 'depth': 0.3},     # the teal monocle lens (in the copper ring)
       -1: {'x': 0.105, 'z': float(HC[2]) + 0.04, 'r': 0.06, 'depth': 0.32}}   # the normal eye
EYE_SINK = 0.012                           # the lens's base behind the face
EYE_OUT = 0.03                             # each eye looks this much outward (x per unit forward)


def smax(a, b, k: float):
    return 0.5 * (a + b + np.sqrt((a - b) ** 2 + k * k))


def smin(a, b, k: float):
    return 0.5 * (a + b - np.sqrt((a - b) ** 2 + k * k))


def head_profile(z: float) -> tuple[float, float, float]:
    """(r, front depth, back depth) multipliers' base: the head's ring at height z is r * (A, BF, BB)."""
    u = (z - HC[2]) / (HEAD_UP if z >= HC[2] else HEAD_LO)
    u = min(1.0, abs(u))
    p = HEAD_P if z >= HC[2] else 2.0
    r = (1.0 - u ** p) ** (1.0 / p)
    if z >= HC[2]:
        # the forehead recedes above the eyes (2-turnaround side: the face's front 5.7 cm back at 0.86 m)
        return r, HEAD_BF * (1.0 - 0.25 * u * u), HEAD_BB
    # below the eyes the head rounds into a solid of revolution about its pivot, so it turns in the collar (a 20 degree
    # nod and the 95 degree owl turn stay clear of it); only the face bulges forward, above the chin
    f = (1.0 - u) ** 2.5
    return r, HEAD_A + (HEAD_BF - HEAD_A) * f, HEAD_A + (HEAD_BB - HEAD_A) * f


def head_n(z: float) -> float:
    """The rings' squareness: HEAD_N above the centre, round (2) toward the bottom."""
    if z >= HC[2]:
        return HEAD_N
    u = min(1.0, (HC[2] - z) / HEAD_LO)
    return 2.0 + (HEAD_N - 2.0) * (1.0 - u) ** 2


def ring(z: float, a: float, bf: float, bb: float, cy: float, n: float, nu: int) -> np.ndarray:
    cs = G.unit_ring(n, nu)
    c, s = cs
    x = a * c
    y = cy + np.where(s < 0, bf, bb) * s
    return np.stack([x, y, np.full(nu, z)], axis=1)


def face_cut(v: np.ndarray) -> np.ndarray:
    """The facial disc: everything ahead of the face plane pressed back onto it, rounded at the rim."""
    v = v.copy()
    v[:, 1] = smax(v[:, 1], np.full(len(v), Y_FACE), FACE_SOFT)
    return v


def head_piece(fine: bool) -> dict:
    nz, nu = (110, 160) if fine else (60, 96)
    rings = []
    zs = HC[2] + np.concatenate([-HEAD_LO * np.cos(np.linspace(0.04, math.pi / 2, nz // 2)),
                                  HEAD_UP * np.sin(np.linspace(0.0, math.pi / 2 - 0.04, nz // 2 + 1))[1:]])
    for z in zs:
        r, bf, bb = head_profile(float(z))
        rings.append(ring(float(z), HEAD_A * r, bf * r, bb * r, HC[1], head_n(float(z)), nu))
    pc = G.sweep(rings)
    pc['v'] = face_cut(pc['v'])
    return G.tag(pc, shell=1.0)


def body_profile(z: float) -> float:
    if z < BC[2]:
        u = min(1.0, (BC[2] - z) / BODY_LO)
        return max(0.0, 1.0 - u ** BODY_P_LO) ** (1.0 / BODY_P_LO)
    u = min(1.0, (z - BC[2]) / BODY_UP)
    return (1.0 - u ** BODY_P_UP) ** (1.0 / BODY_P_UP)


def body_piece(fine: bool) -> dict:
    nz, nu = (90, 160) if fine else (50, 96)
    zs = list(BC[2] - BODY_LO * np.cos(np.linspace(0.05, math.pi / 2, nz // 2)))
    zs += list(np.linspace(BC[2], Z_SHOULDER, nz // 2 + 1)[1:])
    rings = []
    for z in zs:
        r = body_profile(float(z))
        rings.append(ring(float(z), BODY_A * r, BODY_BF * r, BODY_BB * r, BC[1], 2.0, nu))
    r0 = body_profile(Z_SHOULDER)
    # the top: a shelf out under the collar's rim, then a seat sinking toward the middle (under the neck dome)
    for rr, zz in ((0.2, 0.543), (0.17, 0.541), (0.12, 0.53), (0.07, 0.514), (0.02, 0.504)):
        rings.append(ring(zz, rr, rr, rr, HC[1], 2.0, nu))
    return G.tag(G.sweep(rings), shell=0.0)


def collar_piece(fine: bool) -> dict:
    nu, nk = (160, 20) if fine else (96, 12)
    a = np.linspace(0, 2 * math.pi, nu, endpoint=False)
    k = np.linspace(0, 2 * math.pi, nk, endpoint=False)
    rings = []
    for t in a:
        cx, cy = math.cos(t), math.sin(t)
        b = COLLAR['b'] if cy < 0 else COLLAR['bb']
        centre = np.array([COLLAR['a'] * cx, HC[1] + b * cy, COLLAR['z']])
        rad = np.array([cx, cy, 0.0])
        rings.append(centre[None] + COLLAR['tr'] * np.cos(k)[:, None] * rad[None] + COLLAR['tz'] * np.sin(k)[:, None] * np.array([0, 0, 1.0])[None])
    return G.tag(G.sweep(rings, closed=True), shell=2.0)


def shells(fine: bool = True) -> dict:
    return {'head': head_piece(fine), 'body': body_piece(fine), 'collar': collar_piece(fine)}


def objects(fine: bool = True) -> list:
    return [G.make_object(f'gearhoot_{k}', pc, smooth=True) for k, pc in shells(fine).items()]


# ----------------------------------------------------------------------------- queries
def components(n: int, edges: np.ndarray) -> np.ndarray:
    """Connected components of a mesh (hook and compress): a label per vertex."""
    lab = np.arange(n)
    e0, e1 = edges[:, 0], edges[:, 1]
    while True:
        a, b = lab[e0], lab[e1]
        m = np.minimum(a, b)
        new = lab.copy()
        np.minimum.at(new, a, m)
        np.minimum.at(new, b, m)
        for _ in range(4):
            new = new[new]
        if np.array_equal(new, lab):
            return lab
        lab = new


def shells_of(ob) -> np.ndarray:
    """1 on the head shell's vertices, 0 on the body's (with the collar): the shells are apart, so the mesh's own
    connectivity splits them (the head is the piece holding the highest vertex)."""
    me = ob.data
    n = len(me.vertices)
    ed = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get('vertices', ed)
    co = np.empty(n * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    lab = components(n, ed.reshape(-1, 2))
    head = lab == lab[int(np.argmax(co[:, 2]))]
    # stray bits (none expected) go by position
    big = np.bincount(lab)
    stray = big[lab] < 0.02 * n
    return np.where(stray, head_mask(co), head).astype(bool)


def head_mask(co: np.ndarray) -> np.ndarray:
    """The head shell's vertices by position: above the head's round underside (less 1 cm). The rim and the seat
    stay below it."""
    r = np.hypot(co[:, 0], co[:, 1] - HC[1])
    zb = HC[2] - HEAD_LO * np.sqrt(np.clip(1.0 - (np.minimum(r, HEAD_A) / HEAD_A) ** 2, 0, 1))
    return co[:, 2] > zb - 0.01


# the neck dome (a prop on the hips, gearhoot_props.py): from under the rim up into the head, so no hole shows
# round 2: its foot inside the rim's opening (it crossed the rim: saw-toothed slivers), 0.8 cm lower with the rim
NECK_PROFILE = [(0.186, 0.535), (0.186, 0.556), (0.18, 0.574), (0.168, 0.59), (0.148, 0.605), (0.11, 0.62),
                (0.06, 0.628), (0.0, 0.63)]


def neck_piece(fine: bool) -> dict:
    nu = 128 if fine else 96
    rows = [(0.0, 0.522), (0.15, 0.527)] + [(r, z) for r, z in NECK_PROFILE]
    rings = []
    for r, z in rows:
        r = max(r, 0.002)
        rings.append(ring(z, r, r, r, HC[1], 2.0, nu))
    return G.sweep(rings)


def eye_frame(s: int):
    """(centre, x axis, y axis, look) of each eye on the face plane, looking ahead and a little outward."""
    e = EYE[s]
    c = np.array([s * e['x'], Y_FACE, e['z']])
    look = np.array([s * EYE_OUT, -1.0, 0.02])
    look /= np.linalg.norm(look)
    up = np.array([0.0, 0.0, 1.0])
    xax = np.cross(up, look)
    xax /= np.linalg.norm(xax)
    yax = np.cross(look, xax)
    return c, xax, yax, look
