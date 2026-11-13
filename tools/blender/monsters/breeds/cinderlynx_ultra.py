"""Cinderlynx at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md).

A lean, long-legged wildcat (chatgpt/monsters/04-cinderlynx/): an elegant cat head with big gold eyes and a small smile,
tall lynx ears topped with ember tufts, a herringbone of glowing ember leaves from the forehead down the spine to the
tail, a bushy tail held up in a curve whose last third burns ember-orange and ends in a flame plume, big round paws with
glowing claw tips. Short sleek coat, longer on the cheeks, the neck ruff, the chest and the tail. No collar, no mane.
The smoke wisps from the paws are effects, not geometry (PROMPTS.md, Notes for Claude Code).

Size: 1.1 × Puddlepup's height (HEIGHT_UNITS 165): the ear tips stand at 1.10 m. Proportions from 2-turnaround.png at
1.73 mm per pixel; the tail's raised curve and the head's tilt from 1-hero.png (the hero wins; the turnaround asked
for a straight tail only as a modelling pose).

Colours: CONTENT §2.2 #7 (#3A3236 fur / #5A4E52 belly / #FF7A2F embers / #FFD15C eyes); Bonfire Cinderlynx:
src/art/monster/variants.ts (#5A1F14 / #A03A1E / #FFB300 / #FFF0A8), with bigger flames. The pictures paint the belly
far paler than #5A4E52; CONTENT wins, the belly fur only gets frosted tips. Parts CONTENT gives no colour (the inner ear,
the eye ring, the nose, the pads) take muted colours derived from the palette.

Metres; the monster faces −Y, Z is up, +X is its left.
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
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3
from monsters.breeds import cinderlynx_ears as E
from monsters.breeds import cinderlynx_flames as FL
from monsters.breeds import cinderlynx_mouth as MO

ID = 'cinderlynx'
LOOK = 'cinderlynx-ultra'
PLAN = 'quadruped'
HEIGHT_UNITS = 165

# 'frost' (the lock tips) and 'shadow' (the lock roots) are derived tints, not CONTENT colours. Round 2: the film look's
# warm lights turn a neutral dark grey olive (measured: the baked atlas averages sRGB 70/59/59, the film render 81/66/53,
# 12% of its fur pixels green-leaning), so the tips frost toward a violet grey and the roots shade toward blue-violet,
# which keeps the coat on #3A3236's plum side in the game
PALETTE = {'body': '#3A3236', 'belly': '#5A4E52', 'accent': '#FF7A2F', 'eye': '#FFD15C',
           'frost': '#A496AE', 'shadow': '#1C1830'}
# Bonfire: "bigger, brighter golden flames along its spine and tail" (variant-bonfire-cinderlynx.png)
VARIANTS = {'bonfire-cinderlynx': {'body': '#5A1F14', 'belly': '#A03A1E', 'accent': '#FFB300', 'eye': '#FFF0A8',
                                   'frost': '#B8705C', 'shadow': '#2A0C10', 'ember_size': 1.5, 'flame_start': 0.5,
                                   # Nov 12: a warm tan bib (round 3: pinkish grey) and golden flames that keep their
                                   # colour under the bloom (round 3: the pale-yellow core blew the tail out to white)
                                   'pale_cream': '#F2D2A0', 'pale_lift': 0.3, 'ember_core': '#FFC83A',   # Nov 13: the rust belly
                                   'ember_leaf': '#F0A000', 'ember_core_paint': '#FFC21E'}}
# Nov 12 ("hit #FF7A2F in game"): the leaves' paint and glow, measured through the film renderer (calib.py: the
# baked leaves recoloured, shipped and filmed): what lands on #FF7A2F with a #FFD15C core
# (measured: the leaves' texels at #F05008 / glow 0.22 and the cores at #FFB82A / 0.35 film as leaf centres #FFC475 to
# #FFC66C and orange bodies, against round 3's #FFBC87; the paint is about 7% brighter than those texels because the
# bake's AO share darkens it by about that much)
# Nov 13: the cores glow past the bloom threshold (a halo through the fur), the leaf bodies stay ember-orange
EMBER_FILM = {'leaf': '#FF5709', 'core': '#FFC52D', 'leaf_glow': 0.3, 'core_glow': 1.3}

NOSE_HEX = '#6A3934'
MOUTH_HEX = '#211719'
PAD_HEX = '#4B2C29'


PALE_CREAM = '#E6C9A8'      # the warm cream the belly colour is lifted toward (Nov 12: warmer, a step darker)


def colours(pal: dict) -> dict:
    """Every derived colour of a palette (the base or a variant)."""
    fur, belly, ember = pal['body'], pal['belly'], pal['accent']
    # Nov 12: a variant may lift its belly toward its own cream (Bonfire: a warm tan bib, not a pinkish grey)
    pale = C.mix_hex(belly, pal.get('pale_cream', PALE_CREAM), pal.get('pale_lift', 0.6))
    return {
        'fur': fur, 'belly': belly, 'ember': ember,
        # round 2 (the coordinator's decision): the pictures decide markings, so the chest, the muzzle, the lower
        # cheeks and the belly are a pale marking: the belly colour lifted toward a warm cream, in its own hue family
        # (base #5A4E52 → #BDB0A6; Bonfire #A03A1E → #D5A995). CONTENT's palette is unchanged.
        'pale': pale,
        'ember_hot': C.mix_hex(ember, '#FFE9A8', 0.5),       # the claw tips
        # round 3: the embers are the ember colour with a gold core (the reviewer: #FF7A2F with a #FFD15C core; round
        # 2's paler mix read as peach paint, not hot coals)
        'ember_core': pal.get('ember_core', pal['eye']),
        # Nov 12: what the leaves are painted so they land on the ember colour in game (the film's tone mapping
        # lifts and desaturates a bright orange; measured, see EMBER_FILM)
        'ember_leaf': pal.get('ember_leaf', EMBER_FILM['leaf']),
        'ember_core_paint': pal.get('ember_core_paint', EMBER_FILM['core']),
        'ember_deep': C.mix_hex(ember, '#B8320E', 0.35),     # the leaves' rims
        'brow': C.mix_hex(fur, '#0A0708', 0.78),             # round 2: dark brow strokes (1-hero, 4-details 2)
        'lash': '#0C0809',
        'eye_ring': C.mix_hex(belly, '#F0B898', 0.72),       # the pale ring round each eye (1-hero.png)
        'ear_skin': C.mix_hex('#E4968C', belly, 0.12),          # Nov 13: salmon pink (1-hero)
        # Nov 13: the muzzle and cheeks lifted toward the hero's cream (breaks the dark-mask read)
        'face_pale': C.mix_hex(belly, '#EEDCC4', 0.8),
        'ear_fur': C.mix_hex(pale, '#FFFFFF', 0.25),         # the pale fur filling the inner ear low down
        'frost': C.mix_hex(fur, pal.get('frost', '#A496AE'), 0.55),
        'shadow': C.mix_hex(fur, pal.get('shadow', '#1C1830'), 0.6),
        'whisker': C.mix_hex(pale, '#FFFFFF', 0.55),         # round 2: long fine pale whiskers (props)
        'tuft': C.mix_hex(ember, pal['eye'], 0.18),
    }


# ----------------------------------------------------------------------------- helpers: curves
def catmull(pts, n_per: int = 10) -> np.ndarray:
    """A Catmull-Rom curve through `pts` (k×3), `n_per` samples per span; passes through every key (key i at i·n_per)."""
    P = np.asarray(pts, np.float64)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n_per):
            t = k / n_per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return np.array(out)


def poly_nearest(p: np.ndarray, pts: np.ndarray):
    """Per point: the arc length (metres) of its nearest spot on the polyline, that spot, the unit tangent there and the
    distance. Runs past either end."""
    pts = np.asarray(pts, np.float64)
    seg = pts[1:] - pts[:-1]
    lens = np.linalg.norm(seg, axis=1)
    start = np.concatenate([[0.0], np.cumsum(lens)[:-1]])
    k = len(p)
    best = np.full(k, np.inf)
    s = np.zeros(k)
    c = np.zeros((k, 3))
    T = np.zeros((k, 3))
    for i in range(len(seg)):
        u = ((p - pts[i]) @ seg[i]) / max(float(lens[i]) ** 2, 1e-12)
        u = np.clip(u, -np.inf if i == 0 else 0.0, np.inf if i == len(seg) - 1 else 1.0)
        q = pts[i] + u[:, None] * seg[i]
        d = np.linalg.norm(p - q, axis=1)
        b = d < best
        best = np.where(b, d, best)
        s = np.where(b, start[i] + u * lens[i], s)
        c[b] = q[b]
        T[b] = seg[i] / max(float(lens[i]), 1e-12)
    return s, c, T, best


def poly_nearest_fast(p: np.ndarray, pts: np.ndarray, box: float = 0.25):
    """`poly_nearest` for many points: only points within `box` of the curve's bounds are solved (the rest get a huge
    distance), in chunks."""
    pts = np.asarray(pts, np.float64)
    k = len(p)
    s = np.zeros(k)
    c = np.zeros((k, 3))
    T = np.tile(v3((0.0, 1.0, 0.0)), (k, 1))
    d = np.full(k, 9.0)
    lo, hi = pts.min(0) - box, pts.max(0) + box
    idx = np.nonzero(np.all((p >= lo) & (p <= hi), axis=1))[0]
    if len(pts) <= 8:
        for a in range(0, len(idx), 200000):
            ii = idx[a:a + 200000]
            s[ii], c[ii], T[ii], d[ii] = poly_nearest(p[ii], pts)
        return s, c, T, d
    # a dense polyline: the nearest vertex first, then its two segments (millions of lock vertices in seconds)
    seg = pts[1:] - pts[:-1]
    lens = np.linalg.norm(seg, axis=1)
    start = np.concatenate([[0.0], np.cumsum(lens)[:-1]])
    n_seg = len(seg)
    P32 = pts.astype(np.float32)
    PP = (P32 * P32).sum(1)
    for a in range(0, len(idx), 100000):
        ii = idx[a:a + 100000]
        q = p[ii]
        q32 = q.astype(np.float32)
        j = np.argmin(PP[None, :] - 2.0 * (q32 @ P32.T), axis=1)
        best = np.full(len(ii), np.inf)
        for off in (-1, 0):
            si = np.clip(j + off, 0, n_seg - 1)
            A = pts[si]
            AB = seg[si]
            L2 = np.maximum(lens[si] ** 2, 1e-12)
            u = ((q - A) * AB).sum(1) / L2
            lo_u = np.where(si == 0, -np.inf, 0.0)
            hi_u = np.where(si == n_seg - 1, np.inf, 1.0)
            u = np.clip(u, lo_u, hi_u)
            cc = A + u[:, None] * AB
            dd = np.linalg.norm(q - cc, axis=1)
            b = dd < best
            best = np.where(b, dd, best)
            s[ii] = np.where(b, start[si] + u * lens[si], s[ii])
            c[ii] = np.where(b[:, None], cc, c[ii])
            T[ii] = np.where(b[:, None], AB / lens[si][:, None], T[ii])
        d[ii] = best
    return s, c, T, d


def arc_lengths(pts: np.ndarray) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])


# ----------------------------------------------------------------------------- the head
# The head (with its ears and neck) is modelled in head-local space at the turnaround's measurements, then scaled up
# about the neck and lowered, so it has the hero's bigger, cuter proportions at the same overall height (preview 7
# against 1-hero.png: the head read small; 2-turnaround.png front agrees: 0.42 m across the cheek fur). Functions that
# test positions against head landmarks take world points and convert them with `Hinv`.
HEAD_K = 1.14
HEAD_PIVOT = (0.0, -0.33, 0.70)
HEAD_OFS = (0.0, -0.004, -0.026)       # round 3: the head held higher on a rising neck (it hung at back height)


# Nov 13 (the review: the head points nose-up 15-20° in rest and walk): the whole head is pitched nose-down about
# PITCH_PIVOT before it is scaled and moved (H); directions modelled head-local turn with it (Hd)
HEAD_PITCH = 12.0
PITCH_PIVOT = (0.0, -0.31, 0.75)
_PC, _PS = math.cos(math.radians(HEAD_PITCH)), math.sin(math.radians(HEAD_PITCH))
_RX = np.array([[1.0, 0.0, 0.0], [0.0, _PC, -_PS], [0.0, _PS, _PC]])      # about +X: the front (-y) goes down


def Hd(d) -> np.ndarray:
    """A head-local direction in world space."""
    return np.asarray(d, np.float64) @ _RX.T


def H(p) -> np.ndarray:
    """Head-local → world (points: (3,) or (n, 3))."""
    q = (np.asarray(p, np.float64) - v3(PITCH_PIVOT)) @ _RX.T + v3(PITCH_PIVOT)
    return v3(HEAD_PIVOT) + (q - v3(HEAD_PIVOT)) * HEAD_K + v3(HEAD_OFS)


def Hinv(p) -> np.ndarray:
    """World → head-local."""
    q = v3(HEAD_PIVOT) + (np.asarray(p, np.float64) - v3(HEAD_PIVOT) - v3(HEAD_OFS)) / HEAD_K
    return (q - v3(PITCH_PIVOT)) @ _RX + v3(PITCH_PIVOT)


def Hv(p) -> Vector:
    return Vector(tuple(map(float, H(p))))


# round 3: the cranium about 15% smaller and flatter between the ears, so the face (cheeks and ruff) is the widest part
HEAD_C_L = (0.0, -0.334, 0.858)       # Nov 13: with HEAD_R_L's shorter y, the dome behind the ears drops
# round 3b: and flatter on top, between the ears (the reviewer: a shiny dome on the crown)
HEAD_R_L = (0.132, 0.145, 0.1)       # Nov 12: flatter still (the residual 'domed head' note)
EYE_R_L = 0.05
EYE_C_L = {s: (0.088 * s, -0.446, 0.85) for s in (1, -1)}      # Nov 13: sunk into the sockets (they bulged past the brow)
NOSE_C_L = (0.0, -0.556, 0.803)
MUZZLE_L = ((0.0, -0.528, 0.78), (0.068, 0.05, 0.045))
PAD_L = ((0.024, -0.536, 0.775), (0.025 * 1.15, 0.025 * 0.82, 0.025 * 0.86))     # the right-hand whisker pad (head-local)
WHISKER_DOTS = ((0.02, 0.784), (0.031, 0.779), (0.042, 0.773), (0.026, 0.771), (0.037, 0.766))   # (x, z) on a pad


def pad_front_y(dx: float, z: float | None = None) -> float:
    """The front of a whisker pad at head-local x = dx (and height z): the dots and the whisker roots sit on it."""
    (cx, cy, cz), (rx, ry, rz) = PAD_L
    zz = cz if z is None else z
    q = 1.0 - ((dx - cx) / rx) ** 2 - ((zz - cz) / rz) ** 2
    return cy - ry * math.sqrt(max(q, 0.04))
# world versions (the eyes, the nose and the shader work in world space)
HEAD_C = Hv(HEAD_C_L)
HEAD_R = tuple(r * HEAD_K for r in HEAD_R_L)
EYE_R = EYE_R_L * HEAD_K
EYE_SHAPE = (1.0, 0.95)                 # the lens' half axes across and up, in EYE_R (a round cat eye)
EYE_C = {s: Hv(c) for s, c in EYE_C_L.items()}
EYE_DEPTH = (0.44, 0.30)
NOSE_C = Hv(NOSE_C_L)
MUZZLE = (tuple(map(float, H(MUZZLE_L[0]))), tuple(r * HEAD_K for r in MUZZLE_L[1]))


def eye_frame(s: int):
    """Centre, right, up and look axes of an eye (+Z of its dome looks out; a cat's eyes look forward)."""
    c = EYE_C[s]
    surf_n = Vector(((c.x - HEAD_C.x) / HEAD_R[0] ** 2, (c.y - HEAD_C.y) / HEAD_R[1] ** 2, (c.z - HEAD_C.z) / HEAD_R[2] ** 2)).normalized()
    look = (surf_n * 0.55 + Vector((0, -1, 0)) * 0.45).normalized()
    look = (look + Vector((0, 0, 0.04))).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (EYE_R * EYE_DEPTH[1])) @ m


LID_LASH, LID_DROP, LID_W = 0.08, 0.16, 0.95


def blink_pivot(s: int):
    """The blink bone sits behind the lens at the closed lid's lash height (Puddlepup P1.2): a blink squashes the lens
    onto the lash line and sinks it, showing the closed lid sculpted under it."""
    c, _xax, yax, look = eye_frame(s)
    return c - yax * (EYE_R * (LID_LASH + 0.5 * LID_DROP)) - look * (EYE_R * 0.6), yax, look


BLINK_CLOSED = (0.74, 0.04, 0.2)
ATLAS_DENSITY = {'lo_eyes': 1.5}
BODY_TRIS = 50000

E_ROOT = {s: Hv(E.root(s)) for s in (1, -1)}
E_TIP = {s: Hv(E.tip(s)) for s in (1, -1)}


def ear_lookup(p: np.ndarray):
    """The ears' zone for world points: (on an ear, its u, on the cup's face, the lookup in head-local units)."""
    return E.zone(Hinv(p))


# ----------------------------------------------------------------------------- the tail: a raised, bushy curve
# 1-hero.png: back from the rump, then sweeping up behind the body, the tip curling a little forward
# round 2: rising behind in a curve as in 1-hero, the tip leaning to the monster's left so that from the front the flame
# shows beside the head, not as a crest behind it; the idle clips lift it further (CLIP_CALM)
# round 3 (1-hero): dipping from the rump, then curving up into a curl (the idles curl it further)
# Nov 12: leaning further to the side, so the rump's ember chain shows from straight behind
# Nov 13: sweeping back and up, lower at the tip (from the front its flame poked out beside the cheek)
TAIL_PTS = [(0.0, 0.345, 0.588), (0.03, 0.47, 0.558), (0.08, 0.6, 0.572), (0.13, 0.71, 0.615), (0.17, 0.8, 0.68), (0.2, 0.875, 0.755)]
TAIL_BONES = 5
TAIL_CURVE = catmull(TAIL_PTS, 12)
TAIL_S = arc_lengths(TAIL_CURVE)
TAIL_LEN = float(TAIL_S[-1])
# the tail's radius along it (0 root … 1 tip): slim at the root, bushier toward the ember end, rounded off at the tip
# round 2: bushier, about a leg thick at the base, fuller toward the end (the cards add the brush)
# Nov 12: thicker toward the plume (the hero's bushy flame brush)
TAIL_RAD = ((0.0, 0.068), (0.18, 0.066), (0.5, 0.078), (0.6, 0.078), (0.7, 0.052), (0.84, 0.032), (1.0, 0.014))
FLAME_START = 0.64          # where the tail starts to burn (share of its length): its last third


def tail_radius(t):
    t = np.asarray(t, float)
    return np.interp(t, [a for a, _ in TAIL_RAD], [b for _, b in TAIL_RAD])


def tail_param(p: np.ndarray):
    """(0..1 along the tail, distance to its centre line, the centre point, the unit tangent)."""
    s, c, T, d = poly_nearest_fast(p, TAIL_CURVE, 0.2)
    return s / TAIL_LEN, d, c, T


def tail_up(T: np.ndarray) -> np.ndarray:
    """The side of the tail that carries on from the back (the ember side): the tangent turned +90° in the YZ plane."""
    return norm(np.stack([np.zeros(len(T)), -T[:, 2], T[:, 1]], axis=1))


# ----------------------------------------------------------------------------- the legs
# the hind legs' (x, y) is the hip: with the plan's hocks option the leg bends forward to the knee, back to a raised hock, and
# the long rear foot runs down to the paw (round 2: the hind thigh no longer sits 10 cm in front of its bone)
LEGS = {'FL': (0.098, -0.258), 'FR': (-0.098, -0.258), 'BL': (0.09, 0.3), 'BR': (-0.09, 0.3)}
HIP_Z = {'F': 0.5, 'B': 0.52}
TOE_DX = (-0.043, -0.0145, 0.0145, 0.043)  # four toes a paw (1-hero.png, 4-details.png)


def leg_path(leg: str) -> list[tuple[float, float, float]]:
    """The leg's bone-line in the mesh: shoulder or hip, elbow or stifle, (hock), wrist or ankle, the paw."""
    x, y = LEGS[leg]
    s = 1 if x > 0 else -1
    # 2-turnaround.png side view: a long, stretched stance, the front toes level with the chest, the hind feet behind
    # the rump on long hocks
    if leg[0] == 'F':
        return [(0.088 * s, -0.255, 0.5), (0.094 * s, -0.212, 0.33), (0.098 * s, -0.252, 0.1), (0.098 * s, -0.283, 0.045)]
    return [(0.082 * s, 0.3, 0.52), (0.094 * s, 0.255, 0.31), (0.097 * s, 0.45, 0.2), (0.097 * s, 0.438, 0.085), (0.097 * s, 0.405, 0.045)]


def paw_centre(leg: str) -> Vector:
    return Vector(leg_path(leg)[-1])


def toe_centres(leg: str) -> list[Vector]:
    pc = paw_centre(leg)
    return [Vector((pc.x + dx, pc.y - 0.058 + abs(dx) * 0.45, 0.028)) for dx in TOE_DX]


def claw_marks(leg: str) -> list[tuple[Vector, tuple[float, float, float]]]:
    """The glowing claw tip under the front of each toe (1-hero.png: a little ember slit at every toe)."""
    return [(Vector((t.x, t.y - 0.022, 0.012)), (0.0075, 0.012, 0.011)) for t in toe_centres(leg)]


def pad_centre(leg: str) -> tuple[Vector, tuple[float, float, float]]:
    pc = paw_centre(leg)
    return Vector((pc.x, pc.y + 0.008, 0.004)), (0.034, 0.028, 0.012)


def leg_parts(leg: str) -> list[Part]:
    path = leg_path(leg)
    ps: list[Part] = []
    if leg[0] == 'F':
        ps += [Part(f'arm{leg}', 'tube', loc=path[0], to=path[1], radius=0.064, r2=0.056),
               Part(f'fore{leg}', 'tube', loc=path[1], to=path[2], radius=0.048, r2=0.038)]
    else:
        ps += [Part(f'thigh{leg}', 'tube', loc=path[0], to=path[1], radius=0.076, r2=0.056),
               Part(f'shin{leg}', 'tube', loc=path[1], to=path[2], radius=0.047, r2=0.036),
               Part(f'heel{leg}', 'sphere', loc=path[2], radius=0.038, scale=(0.95, 1.1, 1.0)),
               Part(f'meta{leg}', 'tube', loc=path[2], to=path[3], radius=0.036, r2=0.039)]
    pc = paw_centre(leg)
    ps.append(Part(f'paw{leg}', 'sphere', loc=tuple(pc), radius=0.056, scale=(1.12, 1.18, 0.84)))
    ps.append(Part(f'ankle{leg}', 'sphere', loc=(pc.x, pc.y + 0.022, 0.085), radius=0.043, scale=(1.0, 1.0, 1.0)))
    for i, t in enumerate(toe_centres(leg)):
        ps.append(Part(f'toe{leg}{i}', 'sphere', loc=tuple(t), radius=0.0255, scale=(0.92, 1.15, 1.06)))
    return ps


# ----------------------------------------------------------------------------- parts
def head_parts() -> list[Part]:
    """The head and neck, modelled in head-local space and moved into place by `H`."""
    out = []
    for p in head_parts_local():
        p.loc = tuple(map(float, H(p.loc)))
        if p.to is not None:
            p.to = tuple(map(float, H(p.to)))
        p.radius *= HEAD_K
        if p.r2 is not None:
            p.r2 *= HEAD_K
        p.rot = (p.rot[0] + HEAD_PITCH, p.rot[1], p.rot[2])
        out.append(p)
    return out


def head_parts_local() -> list[Part]:
    # a cat's head: a round skull, the big eyes set in a broad face, and (round 2, 4-details 1 and 2-turnaround side)
    # an elegant wedge: the muzzle sticks out about a third of the head's length, under a gently sloping bridge, with
    # neat rounded whisker pads and a small chin, on a visible neck (round 1's flat face, swollen pads and ball cheeks
    # read as a round-faced kitten); the lynx ruff at the jaw corners comes from the fur cards
    return [
        Part('cranium', 'sphere', loc=HEAD_C_L, radius=1.0, scale=HEAD_R_L),
        # Nov 13: a brow over the eyes and a stop down to the muzzle (the profile read seal-like)
        Part('forehead', 'sphere', loc=(0.0, -0.425, 0.896), radius=0.068, scale=(1.4, 0.85, 0.6)),
        # the face's breadth at eye level, so the big eyes sit in the face instead of bulging past the skull
        Part('mask', 'sphere', loc=(0.0, -0.39, 0.85), radius=1.0, scale=(0.155, 0.07, 0.062)),
        Part('face', 'sphere', loc=(0.0, -0.43, 0.792), radius=1.0, scale=(0.112, 0.078, 0.062)),
        Part('cheek', 'sphere', loc=(0.11, -0.37, 0.795), radius=1.0, scale=(0.066, 0.07, 0.06), mirror=True),
        Part('bridge', 'capsule', loc=(0.0, -0.47, 0.874), to=(0.0, -0.548, 0.81), radius=0.02),
        Part('snout', 'sphere', loc=(0.0, -0.508, 0.786), radius=1.0, scale=(0.058, 0.058, 0.046)),
        Part('pad', 'sphere', loc=(0.024, -0.536, 0.775), radius=0.025, scale=(1.15, 0.82, 0.86), mirror=True),
        Part('chin', 'sphere', loc=(0.0, -0.516, 0.74), radius=0.024, scale=(1.1, 1.0, 0.72)),    # Nov 13: a small chin
        Part('nose', 'sphere', loc=NOSE_C_L, radius=0.017, scale=(1.55, 1.0, 0.85)),
        Part('neck', 'capsule', loc=(0.0, -0.31, 0.78), to=(0.0, -0.255, 0.62), radius=0.092),
        Part('throat', 'capsule', loc=(0.0, -0.445, 0.73), to=(0.0, -0.36, 0.57), radius=0.052),
        Part('nape', 'sphere', loc=(0.0, -0.235, 0.79), radius=0.085, scale=(1.0, 1.0, 1.15)),
    ]


def torso_parts() -> list[Part]:
    ps = [
        Part('chest', 'sphere', loc=(0.0, -0.255, 0.522), radius=0.132, scale=(1.12, 1.0, 1.1)),
        Part('neckbase', 'capsule', loc=(0.0, -0.265, 0.58), to=(0.0, -0.3, 0.7), radius=0.105),
        Part('body', 'capsule', loc=(0.0, -0.17, 0.53), to=(0.0, 0.25, 0.537), radius=0.114),
        Part('belly', 'sphere', loc=(0.0, -0.07, 0.474), radius=0.1, scale=(1.08, 1.65, 0.78)),
        Part('rump', 'sphere', loc=(0.0, 0.268, 0.535), radius=0.11, scale=(1.02, 1.0, 0.95)),
        Part('shoulder', 'sphere', loc=(0.078, -0.235, 0.52), radius=0.075, scale=(0.85, 1.1, 1.45), mirror=True),
        Part('haunch', 'sphere', loc=(0.075, 0.272, 0.47), radius=0.09, scale=(0.85, 1.2, 1.35), mirror=True),
    ]
    # the tail: tapered tubes along the curve
    ts = np.linspace(0.0, 1.0, 19)
    for i in range(len(ts) - 1):
        a = TAIL_CURVE[int(round(ts[i] * (len(TAIL_CURVE) - 1)))]
        b = TAIL_CURVE[int(round(ts[i + 1] * (len(TAIL_CURVE) - 1)))]
        ra, rb = float(tail_radius(ts[i])), float(tail_radius(ts[i + 1]))
        if i == 0:
            a = a - (b - a) * 0.6
        ps.append(Part(f'tail{i}', 'tube', loc=tuple(a), to=tuple(b), radius=ra, r2=rb))
    for leg in LEGS:
        ps.extend(leg_parts(leg))
    return ps


def all_parts() -> list[Part]:
    return head_parts() + torso_parts()


def body_extras() -> list[bpy.types.Object]:
    """The two ear shells, voxel-united into the body (new objects on every call), moved into place with the head."""
    out = []
    for s in (1, -1):
        ob = E.shell(s)
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get('co', co)
        S.set_positions(ob, H(co.reshape(-1, 3).astype(np.float64)))
        out.append(ob)
    return out


# ----------------------------------------------------------------------------- whiskers (rigid props on the head)
# round 2 (1-hero, 3-faces, 4-details 1): long, fine, pale whiskers fanning out about a head-width. Few and not too
# thin, so they don't shimmer on the phone: four a side, 1.6 mm at the root
WHISKERS = (  # (pad x, pad z, fan angle up (deg), length) head-local, per side
    (0.022, 0.783, 12.0, 0.15), (0.031, 0.778, 2.0, 0.165), (0.04, 0.772, -9.0, 0.155), (0.028, 0.769, -20.0, 0.135))


def whisker_axis(s: int, i: int, n: int = 16) -> np.ndarray:
    """World points along whisker i on side s: from inside the pad, out and back, drooping a little toward its tip."""
    x, z, fan, ln = WHISKERS[i]
    root = v3((x * s, pad_front_y(x, z) + 0.006, z))
    a = math.radians(fan)
    d = norm(v3((s * math.cos(a), 0.32, math.sin(a)))[None])[0]
    u = np.linspace(-0.04, 1.0, n + 1)
    pts = root[None] + d[None] * (u * ln)[:, None]
    pts[:, 2] -= 0.022 * np.clip(u, 0, 1) ** 2                       # the droop
    pts[:, 1] += 0.012 * np.clip(u, 0, 1) ** 2                       # and a gentle sweep back
    return H(pts)


def whisker_mesh(name: str, high: bool) -> bpy.types.Object:
    sides, n = (7, 18) if high else (4, 8)
    bm = bmesh.new()
    axes = []
    for s in (1, -1):
        for i in range(len(WHISKERS)):
            pts = whisker_axis(s, i, n)
            axes.append(pts)
            rings = []
            for j, p in enumerate(pts):
                t = j / n
                r = (0.0016 - 0.0011 * t) * HEAD_K
                d = pts[min(j + 1, n)] - pts[max(j - 1, 0)]
                d /= np.linalg.norm(d)
                e1 = np.cross(d, v3((0.0, 0.0, 1.0)))
                e1 /= max(np.linalg.norm(e1), 1e-9)
                e2 = np.cross(d, e1)
                rings.append([bm.verts.new(tuple(p + (e1 * math.cos(2 * math.pi * k / sides) + e2 * math.sin(2 * math.pi * k / sides)) * r))
                              for k in range(sides)])
            for j in range(n):
                for k in range(sides):
                    bm.faces.new((rings[j][k], rings[j][(k + 1) % sides], rings[j + 1][(k + 1) % sides], rings[j + 1][k]))
            tip = bm.verts.new(tuple(pts[-1] + (pts[-1] - pts[-2]) * 0.6))
            for k in range(sides):
                bm.faces.new((rings[n][k], rings[n][(k + 1) % sides], tip))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob['prop'] = 'whiskers'
    allpts = np.vstack(axes)

    def inside(c):
        d = np.linalg.norm(c[:, None, :] - allpts[None, :, :], axis=2)
        return allpts[np.argmin(d, axis=1)]
    S.orient_away(ob, inside)
    S.add_attr(ob, 'whisker', np.ones(len(me.vertices)))
    S.add_attr(ob, 'flame_u', np.zeros(len(me.vertices)))
    S.add_attr(ob, 'flame_part', np.zeros(len(me.vertices)))
    S.add_attr(ob, 'mouth_part', np.zeros(len(me.vertices)))
    return ob


def flame_mesh(name: str, high: bool) -> bpy.types.Object:
    """Round 3: the ember flames on the ear tips and the tail's flame lick, as one prop (cinderlynx_flames)."""
    ears = {}
    for s in (1, -1):
        tp, a, xo, nf = E.tip_frame(s)
        ears[s] = (H(tp), Hd(a), Hd(xo), Hd(nf))
    # Nov 12: the plume's stations along the tail's last third (centre, tangent, up, radius)
    frames = []
    m = len(TAIL_CURVE) - 1
    for t in (0.62, 0.67, 0.72, 0.77, 0.82, 0.86, 0.9, 0.94, 0.97, 0.99):
        i = int(round(t * m))
        T = TAIL_CURVE[min(i + 2, m)] - TAIL_CURVE[max(i - 2, 0)]
        T = T / np.linalg.norm(T)
        up = norm(v3((0.0, -T[2], T[1]))[None])[0]
        frames.append((TAIL_CURVE[i], T, up, float(tail_radius(t))))
    ob = FL.build(name, high, ears, frames, HEAD_K)
    ob['prop'] = 'flames'
    S.add_attr(ob, 'whisker', np.zeros(len(ob.data.vertices)))
    S.add_attr(ob, 'mouth_part', np.zeros(len(ob.data.vertices)))
    return ob


# the Lite copy keeps the props whole: the flames (20 tongues, about 2.2k triangles) and the whiskers (544)
LITE_PROPS_TRIS = 5700     # Nov 13: 28 ear wisps + 40 tail strands ≈ 3.8k, the whiskers 0.5k and the mouth 1.2k


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    """hi_* / lo_*: the eight whiskers (rigid on the head), the ember flames (the ear tufts on ear.*.2, the tail's
    flame lick on the last tail bone) and the mouth (Nov 12: the inner skin, the throat and the fangs behind the cut lips,
    cinderlynx_mouth; made from the cut low body, so only once it exists): prop_weight_regions."""
    tag = 'hi' if high else 'lo'
    out = [whisker_mesh(f'{tag}_whiskers', high), flame_mesh(f'{tag}_flames', high)]
    lo = bpy.data.objects.get('lo_body')
    if lo is not None and lo.get('mouth_cut'):
        out.append(MO.mouth_mesh(f'{tag}_mouth', lo, Hinv, H, HEAD_K, inside=_inside_of(lo), target=MOUTH_TRIS))
    return out


def _inside_of(ob: bpy.types.Object):
    """points → bool: inside `ob`'s closed surface (by its nearest face's side)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()

    def inside(pts: np.ndarray) -> np.ndarray:
        out = []
        for p in pts:
            hit = bvh.find_nearest(Vector(tuple(map(float, p))))
            out.append(hit[0] is not None and (Vector(tuple(map(float, p))) - hit[0]).dot(hit[1]) < -0.002)
        return np.asarray(out, bool)
    return inside


def carve_low(ob: bpy.types.Object) -> None:
    """Nov 12: the mouth's cut along the lip line, on the low body before its decimation (cinderlynx_mouth)."""
    MO.cut(ob, Hinv, HEAD_K)
    ob['mouth_cut'] = 1


# the jaw opens (the swipe's snarl, the cast, the happy smiles). Its automatic heat weights are merged into the head
# first (they covered the whole muzzle, so the upper lip dropped with the jaw and the mouth stayed a slit);
# body_weight_regions then gives only the lower jaw to `jaw`, and rig_p's jaw_open keeps the smiles (Starhowl's way)
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')
MOUTH_TRIS = 1200           # the mouth prop's triangles (its inner skin decimated away from the lips)
MOUTH_SOCKET = tuple(map(float, H((0.0, -0.562, 0.7515))))    # at the lips (effects start there, not inside the snout)


def prop_weight_regions(co: np.ndarray, attr, names: list[str], mesh: str | None = None):
    """The whiskers rigid on the head; each ear's flame on its ear's tip bone; the tail's flame lick on the last tail
    bone."""
    part = attr('flame_part')
    whisk = attr('whisker') > 0.5
    mp = attr('mouth_part')
    out = [(whisk, {'head': np.ones(int(whisk.sum()))})]
    # the mouth: the palate, the throat and the fangs on the head; the floor and tongue with the lower jaw's own blend
    up = (mp > 0.5) & ~whisk
    out.append((up, {'head': np.ones(int(up.sum()))}))
    dn = (mp < -0.5) & ~whisk
    if dn.any():
        w = MO.jaw_weight(Hinv(co[dn]))
        out.append((dn, {'jaw': w, 'head': 1.0 - w}))
    whisk = whisk | up | dn
    for s, tag in ((1, 'L'), (-1, 'R')):
        m = (np.abs(part - s) < 0.1) & ~whisk
        out.append((m, {f'ear.{tag}.2': np.ones(int(m.sum()))}))
    m = (part > 1.5) & ~whisk
    if m.any():
        # the plume's tongues ride the tail's last bones (they root along its last third)
        out.append((m, U.chain_weights(co[m], rig_p()['tail_points'], tail_bone_names(), 'hips')))
    return out


# ----------------------------------------------------------------------------- carving (the high source only)
def mouth_polylines() -> list[list[tuple[float, float]]]:
    """(x, z) lines on the muzzle front, head-local: the short line down from the nose and the cat smile, two soft
    curves whose outer ends turn up (1-hero.png, 3-faces.png neutral)."""
    top = NOSE_C_L[2] - 0.012
    mid = NOSE_C_L[2] - 0.026
    lines = [[(0.0, top), (0.0, mid)]]
    for s in (1, -1):
        pts = []
        for k in range(0, 13):
            t = k / 12
            x = s * 0.034 * t
            z = mid - 0.0075 * math.sin(math.pi * min(1.0, t * 1.05)) + 0.006 * max(0.0, t - 0.7) / 0.3
            pts.append((x, z))
        lines.append(pts)
    return lines


EYE_SURROUND_MIX = 0.62     # the upper lid's tone: the coat toward the pale marking


def eye_surround(p: np.ndarray) -> np.ndarray:
    """0..1 round each eye: the light upper lid between the lens and the brow, and the lid under the lens (3-faces)."""
    out = np.zeros(len(p))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = p - v3(c)
        xe = (q @ v3(xax)) / (EYE_R * EYE_SHAPE[0])
        ye = (q @ v3(yax)) / (EYE_R * EYE_SHAPE[1])
        ze = q @ v3(look)
        r = np.sqrt(xe * xe + ye * ye)
        # widest above the eye (up to the brow), narrower at the sides and below (the pale face takes over there)
        reach = 1.22 + 0.2 * smooth(-0.2, 0.6, ye / np.maximum(r, 1e-6))
        # Nov 12 (the review: a mid-grey brow and eye area read as a tabby): only the closed lid under the lens is
        # light (the blink); round the open eye the coat stays charcoal
        # Nov 13: the closed lid is the coat (fur-coloured, under the dark lash line), only a touch lighter
        out = np.maximum(out, 0.3 * smooth(1.04, 0.96, r) * (ze > -0.035))
    return out


def closed_lid(co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Under each lens: the soft closed lid (a bulge) and its lash line, shown only while a blink sinks the lens."""
    bulge = np.zeros(len(co))
    lash = np.zeros(len(co))
    for s in (1, -1):
        c, xax, yax, look = eye_frame(s)
        q = co - v3(c)
        xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
        ax, ay = EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1]
        r2 = (xe / ax) ** 2 + (ye / ay) ** 2
        front = ze > -0.03
        bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
        xn = xe / (ax * LID_W)
        arc = -(LID_LASH + LID_DROP * (1.0 - np.clip(xn, -1, 1) ** 2)) * EYE_R
        th = 0.0034 + 0.003 * smooth(0.2, 1.0, xn * s)      # round 3b: a thicker lash curve (3-faces blink)
        on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
        lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
    return bulge, lash


def carve(ob: bpy.types.Object) -> None:
    co, vn = S.mesh_arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    hl = Hinv(co)                                     # the face's details are drawn in head-local space
    hx, hy, hz = hl[:, 0], hl[:, 1], hl[:, 2]
    front = smooth(-0.5, -0.53, hy)
    md = np.full(len(co), 9.0)
    for line in mouth_polylines():
        md = np.minimum(md, S.polyline_dist(hx, hz, line))
    groove = np.exp(-(md / 0.0018) ** 2) * front * (hz < NOSE_C_L[2] - 0.008) * (hz > 0.72)
    nos = np.zeros_like(x)
    for s in (1, -1):
        dd = np.sqrt(((hx - 0.0095 * s) / 1.5) ** 2 + (hz - (NOSE_C_L[2] - 0.006)) ** 2)
        nos = np.maximum(nos, np.exp(-(dd / 0.0042) ** 2))
    nos *= smooth(NOSE_C_L[1] + 0.014, NOSE_C_L[1] + 0.006, hy)
    # the toes: a soft cleft between neighbours
    cleft = np.zeros(len(co))
    for leg in LEGS:
        tc = toe_centres(leg)
        for a, b in zip(tc[:-1], tc[1:]):
            m = (a + b) * 0.5
            d = np.sqrt(((x - m.x) / 0.0035) ** 2 + ((y - (m.y - 0.012)) / 0.03) ** 2)
            cleft = np.maximum(cleft, np.exp(-d ** 2) * (z < 0.05) * (z > 0.004))
    bulge, lash = closed_lid(co)
    disp = -0.0018 * groove - 0.0035 * nos - 0.003 * cleft - 0.0012 * lash      # round 3: the closed lid is flush
    S.set_positions(ob, co + vn * disp[:, None])
    # Nov 12: the lips' line where the low body is cut (a thin dark rim at rest; the lips' edges when the mouth opens)
    lip = np.exp(-(MO.lip_f(hl) / 0.0024) ** 2) * MO.cut_region(hl)
    groove = np.maximum(groove, 0.0 * lip)        # Nov 13: no painted line at the cut (it read as a second mouth)
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
    sx, sy, sz = EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1], EYE_R * EYE_DEPTH[0]
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / v3((sx, sy, sz)))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


# ----------------------------------------------------------------------------- zones
def _ear(p: np.ndarray):
    return ear_lookup(p)


def ear_zone(p: np.ndarray):
    on, u, _inner, _L = ear_lookup(p)
    return on, u


def leg_masks(p: np.ndarray) -> dict[str, np.ndarray]:
    out = {}
    for leg in LEGS:
        path = np.array(leg_path(leg))
        if leg[0] == 'F':
            top = 0.42
            path = np.vstack([path[:1] + (path[1] - path[0]) * 0.3, path[1:]])
        else:
            top = 0.4
            path = np.vstack([path[1:2] + (path[0] - path[1]) * 0.35, path[1:]])
        _s, _c, _T, d = poly_nearest_fast(p, path, 0.12)
        out[leg] = (d < 0.085) & (p[:, 2] < top) & (p[:, 0] * np.sign(path[0, 0]) > 0.0)
    return out


_ZCACHE: list = []


def zones(p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """The coat's zones (cached for the big point sets the paint asks about several times)."""
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


def _zones(p: np.ndarray) -> dict[str, np.ndarray]:
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    hl = Hinv(p)                                       # the head's zones in head-local space
    hy, hz, hax = hl[:, 1], hl[:, 2], np.abs(hl[:, 0])
    ear, ear_u, ear_inner, ear_l = _ear(p)
    head = ((in_ellipsoid(hl, (0.0, -0.37, 0.845), (0.25, 0.23, 0.2)) < 1.0) & (hz > 0.69) & (hy < -0.22)) | ear
    muzzle = in_ellipsoid(p, *MUZZLE) < 1.0
    nose = np.linalg.norm(p - v3(NOSE_C), axis=1) < 0.026 * HEAD_K
    eye_d = np.minimum(np.linalg.norm(p - v3(EYE_C[1]), axis=1), np.linalg.norm(p - v3(EYE_C[-1]), axis=1))
    face = head & (hy < -0.42) & (hz > 0.71) & (hz < 0.93) & (hax < 0.13) & ~ear
    crown = head & (hz > 0.93) & ~ear
    cheek = head & (hax > 0.085) & (hz < 0.85) & (hy < -0.3) & ~ear & ~muzzle
    chin = head & (hz < 0.745) & (hy < -0.43)
    ruff = head & ~ear & ((hy > -0.36) | (hax > 0.13)) & (hz < 0.86) & ~face
    legs = leg_masks(p)
    leg = np.zeros(len(p), bool)
    for m in legs.values():
        leg |= m
    leg &= ~head
    paw = leg & (z < 0.1)
    toes = np.zeros(len(p), bool)
    for lg in LEGS:
        pc = paw_centre(lg)
        toes |= legs[lg] & (y < pc.y - 0.02) & (z < 0.07)
    sole = z < 0.012
    tt, td, _tc, tT = tail_param(p)
    tail = ~head & ~leg & (tt > 0.035) & (td < tail_radius(np.clip(tt, 0, 1)) + 0.05)
    torso = ~head & ~leg & ~tail
    # the pale front: the throat and the chest, narrowing between the front legs
    bib = (~head | chin) & ~tail & (y < -0.2) & (ax < 0.095 + 0.05 * smooth(0.45, 0.68, z)) & (z > 0.36) & (z < 0.76)
    bib &= ~(leg & (z < 0.42))
    zb = np.interp(y, [-0.38, -0.22, -0.05, 0.15, 0.3], [0.43, 0.42, 0.415, 0.43, 0.46])
    belly = torso & (z < zb)
    back = torso & (z > 0.58)
    return {'ear': ear, 'ear_u': ear_u, 'ear_v': ear_l['v'], 'ear_inner': ear_inner, 'ear_up': ear_l['up'], 'ear_d': ear_l['d'],
            'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face, 'crown': crown, 'cheek': cheek,
            'chin': chin, 'ruff': ruff, 'leg': leg, 'legs': legs, 'paw': paw, 'toes': toes, 'sole': sole, 'tail': tail,
            'tail_t': tt, 'tail_d': td, 'tail_T': tT, 'torso': torso, 'bib': bib, 'belly': belly, 'back': back}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    z = zones(co)
    hl = Hinv(co)
    # Nov 12: the cut lips keep every vertex; the muzzle round them a little less (the mouth's inner skin copies it)
    fl = np.abs(MO.lip_f(hl))
    lips = MO.cut_region(hl) * (smooth(0.004, 0.002, fl) * 1.0)
    near_mouth = MO.cut_region(hl) & (fl < 0.03)
    face = np.where(near_mouth, 0.55, z['face'] * 1.0 + z['muzzle'] * 1.0)
    return np.clip(face + (z['eye_d'] < 0.075) * 1.0 + z['toes'] * 0.75 + z['paw'] * 0.25
                   + (z['ear'] & (z['ear_u'] > 0.6)) * 0.6 + lips, 0, 1)


# ----------------------------------------------------------------------------- how the fur lies
def flow(p: np.ndarray, n: np.ndarray, z=None) -> np.ndarray:
    if z is None:
        z = zones(p, n)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    k = len(p)
    hl = Hinv(p)
    hy, hz = hl[:, 1], hl[:, 2]
    # the head: combed back from the nose; the cheeks sweep back, out and down into the ruff
    g = norm(p - v3((0.0, NOSE_C.y - 0.04, NOSE_C.z + 0.01)))
    wd = smooth(0.84, 0.74, hz)[:, None]
    # round 2: the cheek fur flares out sideways (2-turnaround.png front), it doesn't hang down like a beard
    # Nov 12: out, back and down (the review: radial needles; the reference's ruff sweeps down and back in tiers)
    cheek_dir = norm(np.stack([np.sign(x) * 0.65, np.full(k, 0.6), np.full(k, -0.7)], axis=1))
    g_head = norm(g * (1 - wd) + cheek_dir * wd * 1.2)
    face_up = norm(np.stack([hl[:, 0] * 3.0, np.full(k, 0.25), np.ones(k)], axis=1))
    wf = (smooth(-0.44, -0.48, hy) * smooth(0.85, 0.88, hz) * smooth(0.1, 0.05, np.abs(hl[:, 0])))[:, None]
    g_head = norm(g_head * (1 - wf) + face_up * wf)
    # the ears: up toward the tip
    g_head = np.where(z['ear'][:, None], z['ear_up'], g_head)
    # the ruff: back and down
    g_head = np.where(z['ruff'][:, None], norm(np.stack([np.sign(x) * 0.45, np.full(k, 0.7), np.full(k, -0.75)], axis=1)), g_head)
    side = np.clip(np.abs(n[:, 0]) * 1.2, 0, 1)[:, None]
    g_torso = norm(v3((0.0, 1.0, -0.08)) * (1 - side) + v3((0.0, 0.4, -1.0)) * side)
    g = np.where(z['torso'][:, None], g_torso, g_head)
    g = np.where(z['belly'][:, None], np.tile(v3((0.0, 0.5, -0.8)), (k, 1)), g)
    # the bib fans out across the chest (round 3)
    # Nov 12: one V bib, the fur pointing down and a little in toward the middle (round 3's fan split it in two lappets)
    g = np.where(z['bib'][:, None], norm(np.stack([-np.sign(x) * 0.22, np.full(k, -0.12), np.full(k, -1.0)], axis=1)), g)
    g = np.where(z['leg'][:, None], np.tile(v3((0.0, 0.08, -1.0)), (k, 1)), g)
    g_tail = z['tail_T']
    # toward the ember end the fur flares out a little, like flames
    out = norm(n - z['tail_T'] * (n * z['tail_T']).sum(1, keepdims=True))
    g_tail = norm(g_tail + out * (0.35 * smooth(0.6, 0.95, z['tail_t']))[:, None])
    g = np.where(z['tail'][:, None], g_tail, g)
    g = np.where((z['head'] & ~z['bib'])[:, None], g_head, g)
    return tangent(g, n)


def _rad(d) -> float:
    return math.radians(d)


def head_lock_params(p, n):
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.05)
    W = np.full(k, 0.0098)
    lift = np.full(k, _rad(2.0))
    L = np.where(z['face'], 0.032, L)
    W = np.where(z['face'], 0.0072, W)
    L = np.where(z['crown'], 0.044, L)
    L = np.where(z['crown'] & (np.abs(p[:, 0]) < 0.06), 0.034, L)      # round 2: short over the forehead flame (long locks broke it up)
    L = np.where(z['cheek'], 0.068, L)
    W = np.where(z['cheek'], 0.0115, W)
    L = np.where(z['ruff'], 0.07, L)
    W = np.where(z['ruff'], 0.012, W)
    L = np.where(z['chin'], 0.05, L)
    L = np.where(z['ear'], 0.036, L)
    W = np.where(z['ear'], 0.0078, W)
    # round 2: fine short fur on the muzzle too (it read as smooth plastic), kept off the nose and the smile line
    L = np.where(z['muzzle'], 0.017, L)
    W = np.where(z['muzzle'], 0.0052, W)
    lift = np.where(z['muzzle'], _rad(1.0), lift)
    near_eye = smooth(EYE_R * 1.15, EYE_R * 1.9, z['eye_d'])
    L = L * (0.45 + 0.55 * near_eye)
    W = W * (0.6 + 0.4 * near_eye)
    skin = ear_skin_mask(z) > 0.5                       # the inner ear's smooth skin: no locks there
    # round 3 (3-faces blink): short fur on the closed lid, under the lens (hidden while the eye is open), so a blink
    # shows a fur-toned lid flush with the face instead of a smooth dome
    # round 3b: round 3's lid locks were cancelled by the skip below (every point within 1.12 R of the eye), so the
    # blink still showed a smooth bare dome; now they grow under the lens, kept off the closed lid's lash line
    lid = (z['eye_d'] < EYE_R * 1.04) & z['head']
    L = np.where(lid, 0.013, L)
    W = np.where(lid, 0.0055, W)
    lift = np.where(lid, 0.0, lift)
    _bulge, lash = closed_lid(p)
    near_nose = np.linalg.norm(p - v3(NOSE_C), axis=1) < 0.03 * HEAD_K
    skip = (~z['head'] | z['bib'] | z['nose'] | near_nose | (z['muzzle'] & (mouth_dist(p) < 0.0055))
            | ((z['eye_d'] < EYE_R * 1.12) & ~lid) | (lid & (lash > 0.08)) | skin)
    return np.where(skip, np.nan, W * 0.55), L, W, lift, z


def mouth_dist(p: np.ndarray) -> np.ndarray:
    """Head-local distance in the muzzle's front plane to the mouth lines (the smile and the line under the nose)."""
    hl = Hinv(p)
    md = np.full(len(p), 9.0)
    for line in mouth_polylines():
        md = np.minimum(md, S.polyline_dist(hl[:, 0], hl[:, 2], line))
    return md


def body_lock_params(p, n):
    z = zones(p, n)
    k = len(p)
    L = np.full(k, 0.058)
    W = np.full(k, 0.0118)
    lift = np.full(k, _rad(2.0))
    L = np.where(z['bib'], 0.06, L)              # round 3: a short bib (round 2's hung off the chin like a beard)
    W = np.where(z['bib'], 0.0135, W)
    lift = np.where(z['bib'], _rad(6), lift)
    L = np.where(z['belly'], 0.07, L)
    upper = z['leg'] & (p[:, 2] > 0.2)
    L = np.where(z['leg'], np.where(upper, 0.05, 0.034), L)
    W = np.where(z['leg'], np.where(upper, 0.011, 0.0088), W)
    L = np.where(z['tail'], 0.064, L)
    W = np.where(z['tail'], 0.012, W)
    lift = np.where(z['tail'], _rad(5), lift)
    skip = (z['head'] & ~z['bib']) | z['toes'] | z['sole'] | (z['paw'] & (p[:, 2] < 0.035))
    return np.where(skip, np.nan, W * 0.6), L, W, lift, z


CARD_LAYERS = 3
CARD_SHADE = 0.82     # Nov 13: darker than the skin (the cards' edges read as pale fringes, frost, calico at 64 px)
# round 3b: crowded lock roots under the cheek ruff and the bib baked near black, so the cards that take their colour
# there read as dark slats (RECIPE.md: AO_FLOOR, AO_SOFTEN)
AO_FLOOR = 0.35
AO_SOFTEN = 1.5


def card_params(p, n, layer: int):
    """Soft fur cards for the outline. Layer 0: the sleek coat (short). Layer 1: the longer fur: the lynx ruff, the pale
    bib, spiky clumps at the elbows, the shoulders, the backs of the legs and the belly line, the tail. Layer 2: the bushy
    tail. Round 2: no cards over the ember leaves or the forehead crest and crown chain (cards take the colour under their
    root, and pale-gold cards standing up over the leaves read as a silver saddle and a crest of spikes)."""
    z = zones(p, n)
    k = len(p)
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    hl = Hinv(p)
    hy, hz, hax = hl[:, 1], hl[:, 2], np.abs(hl[:, 0])
    head = z['head']
    light = light_mask(p, z)
    em = ember_coords(p)
    on_leaf = (leaf_np(em['sigma'], em['tau'], 1.3) * em['env']) > 0.08
    crest = head & (hax < 0.06) & (hz > 0.86) & ~z['ear']
    if layer == 0:
        L = np.where(head, 0.048, 0.036)          # Nov 13: short and sleek on the body
        W = np.where(head, 0.028, 0.034)
        lift = np.full(k, _rad(4))
        L = np.where(z['cheek'], 0.058, L)
        L = np.where(z['leg'], 0.03, L)
        W = np.where(z['leg'], 0.03, W)
        L = np.where(z['tail'], 0.065, L)
        sp = np.where(head, 0.02, 0.021)
        sp = np.where(z['leg'], 0.02, sp)
        # no cards up the ears (dark notches past the rims; the lying locks cover the backs)
        skip = (z['face'] | z['muzzle'] | z['nose'] | (z['eye_d'] < 0.085) | (z['chin'] & (hy < -0.45)) | z['ear_inner']
                | (z['ear'] & (z['ear_u'] > 0.1)) | (z['leg'] & (zz < 0.09)) | z['sole'])
        # Nov 12: the cheek ruff in three tiers (this the shortest, inner one), soft clumps sweeping down and back
        ruff0 = head & ~z['ear'] & (hax > 0.085) & (hy > -0.44) & (hy < -0.24) & (hz > 0.69) & (hz < 0.9)
        L = np.where(ruff0, 0.055, L)
        W = np.where(ruff0, 0.032, W)
        lift = np.where(ruff0, _rad(12), lift)
        sp = np.where(ruff0, 0.016, sp)
        skip = skip & ~(ruff0 & ~(z['eye_d'] < 0.085))
    elif layer == 1:
        L = np.full(k, 0.07)
        W = np.full(k, 0.034)
        lift = np.full(k, _rad(10))
        sp = np.full(k, 0.032)
        # the lynx ruff (2-turnaround front, 3-faces neutral): spiky clumps flaring out sideways and down from below the
        # ears to the jaw corners, so the face is a wide diamond (round 1's long ruff hung as drapes off the jaw)
        ruff_c = head & ~z['ear'] & (hax > 0.08) & (hy > -0.44) & (hy < -0.24) & (hz > 0.69) & (hz < 0.9)
        neck = z['ruff'] & ~ruff_c & (hy > -0.33)
        # round 3: the bib starts under the jaw (not off the chin) and fans across the chest between the forelegs
        # Nov 12: on the chest only (under the jaw it hung as two lappets, a stole, and hid the open mouth)
        bib = z['bib'] & ~z['chin'] & (zz < 0.6)
        belly = z['belly'] & (zz < 0.45)
        clump = np.zeros(k, bool)
        for lg in LEGS:
            path = leg_path(lg)
            joint = v3(path[1])                                  # the elbow, or the knee
            clump |= np.linalg.norm(p - joint, axis=1) < 0.07
            if lg[0] == 'B':
                clump |= np.linalg.norm(p - v3(path[2]), axis=1) < 0.055     # the hock
        sx = np.sign(x)
        clump |= in_ellipsoid(np.stack([np.abs(x), y, zz], axis=1), (0.11, -0.22, 0.56), (0.05, 0.08, 0.09)) < 1.0   # shoulders
        leg_back = np.zeros(k, bool)
        for lg, (lx, ly) in LEGS.items():
            back_y = leg_path(lg)[2][1] if lg[0] == 'B' else ly
            leg_back |= z['legs'][lg] & (y > back_y - 0.03) & (zz > 0.12)
        tail = z['tail']
        # round 3: bigger, denser clumps so the cheeks are the widest part of the face (a diamond)
        L = np.where(ruff_c, 0.088, L)                 # Nov 12: the ruff's middle tier
        W = np.where(ruff_c, 0.034, W)
        lift = np.where(ruff_c, _rad(18), lift)
        sp = np.where(ruff_c, 0.016, sp)
        L = np.where(neck, 0.05, L)
        lift = np.where(neck, _rad(6), lift)
        sp = np.where(neck, 0.04, sp)
        # the bib: a short fluffy pale bib fanning across the chest between the forelegs
        L = np.where(bib, 0.058, L)
        W = np.where(bib, 0.042, W)
        lift = np.where(bib, _rad(10), lift)
        sp = np.where(bib, 0.022, sp)
        # small spiky clumps break the smooth tube outlines (1-hero, 4-details 6)
        spiky = clump | leg_back | belly
        L = np.where(spiky, 0.05, L)
        W = np.where(spiky, 0.028, W)
        lift = np.where(spiky, _rad(14), lift)
        sp = np.where(spiky, 0.028, sp)
        L = np.where(tail, 0.12, L)
        W = np.where(tail, 0.056, W)
        lift = np.where(tail, _rad(30), lift)
        sp = np.where(tail, 0.02, sp)
        fringe = ruff_c | neck | bib | spiky | tail
        skip = ~fringe | z['face'] | z['muzzle'] | (z['eye_d'] < 0.1) | (z['chin'] & (hy < -0.46)) | z['ear']
    else:
        # the bushy tail: long cards standing out, fuller toward the ember end (round 3: a foreleg thick at the base);
        # and a second layer of the lynx ruff's clumps
        tt = z['tail_t']
        ruff2 = head & ~z['ear'] & (hax > 0.09) & (hy > -0.42) & (hy < -0.26) & (hz > 0.7) & (hz < 0.88)
        L = np.where(ruff2, 0.112, 0.13 + 0.07 * smooth(0.25, 0.85, tt))     # Nov 12: the ruff's outer tier
        W = np.where(ruff2, 0.03, 0.06)
        lift = np.where(ruff2, _rad(24), _rad(32) + _rad(14) * smooth(0.5, 0.95, tt))
        sp = np.where(ruff2, 0.018, 0.019 - 0.004 * smooth(0.4, 0.9, tt))
        skip = ~(z['tail'] | ruff2) | (z['tail'] & (tt < 0.03))
    # none on the inner ear's skin, none where the pale marking meets the fur (a pale card over charcoal glittered),
    # none over the ember leaves or the crest
    # round 3: and none on the crown (their dark roots showed as rectangles)
    skip = (skip | (z['ear_inner'] & (z['ear_v'] > 0.25)) | ((light > 0.08) & (light < 0.92)) | (on_leaf & (z['tail_t'] < FLAME_START))
            | crest | (z['crown'] & ~z['ear'])
            # Nov 12: none in the tail's flame (the plume's tongues are the flame; the cards there were straws and
            # shards), none on the lower jaw or under it (they hid the open mouth)
            # Nov 13: the fur runs on a little into the flame (cards there take the flame's start: a gradient out of
            # the black fur, no hem), and the spine chain's band is left bare so the embers show through
            | (z['tail'] & (z['tail_t'] > FLAME_START + 0.08)) | (MO.jaw_weight(hl) > 0.02)
            | ((em['env'] > 0.15) & (np.abs(em['tau']) < 0.5) & ~(z['tail'] & (z['tail_t'] > FLAME_START)))
            | ((light > 0.5) & ~z['bib'])
            | (z['bib'] & (zz > 0.6) & ~(head & ~z['chin']))
            # round 3b: and no pale cards on the hind half (the inner thighs and the rump showed leftover pale cards)
            | ((light > 0.08) & (y > 0.1)))
    return np.where(skip, np.nan, sp), L, W, lift, z


# ----------------------------------------------------------------------------- the tuft: ember ear tufts and the tail's flame plume
# (round 3: no tuft locks: the ember ear tufts and the tail's flame lick are flame props, cinderlynx_flames; tuft locks
# can't glow, and their thin ribbons washed out to peach-white under the key and rim lights)


def tuft_colour(pal: dict) -> str:
    return colours(pal)['tuft']


def tuft_colours(pal: dict, tpos: np.ndarray, lrand: np.ndarray) -> np.ndarray:
    """Round 2: the flame strands run from a deep ember at the root through the ember colour to a hot yellow-orange at
    the tip (1-hero, 4-details 4), a little uneven per strand."""
    col = colours(pal)
    t = np.clip(np.asarray(tpos, np.float64), 0, 1)[:, None]
    lr = np.asarray(lrand, np.float64)[:, None]
    # round 3b: the tips end in the gold core (#FFD15C), not the pale hot mix (it read peach in the film)
    deep, ember, hot = lin(col['ember_deep']), lin(col['ember']), lin(col['ember_core'])
    # Nov 12: the ember colour at the root, gold at the tips (no pale core: it blew out to white under the bloom)
    hot = lin(col['ember_core_paint'])
    k1 = smooth(0.0, 0.15, t)
    k2 = smooth(0.35, 1.0, t) * 0.9
    rgb = deep[None] * (1 - k1) * 0.3 + ember[None] * (1 - (1 - k1) * 0.3)
    rgb = rgb * (1 - k2) + hot[None] * k2
    return rgb * (0.88 + 0.24 * lr)




TUFT_SHAPE = {'template': (9, 14, 3, 0.18), 'thickness': 0.3, 'bury': 0.05}


# ----------------------------------------------------------------------------- the ember pattern (spine coordinates)
# The ember leaves run in a herringbone chevron chain along one curve from the nape down the neck, along the back and up
# the tail (1-hero.png, 4-details 5, 2-turnaround.png back view): a centre chain of fat leaves on the midline, chevron
# arms fused to it angled back and out, smaller flanking leaves tapering down the sides; biggest over the shoulders and
# the tail base. Each source vertex stores its curve coordinates in cells (σ along, τ across) and the band's envelope;
# the bake shader draws the leaves per pixel from them (crisp), so the leaves glow through the locks.
# Round 2: no band over the head (where the curve bent round the back of the skull the leaves smeared into horizontal
# bars, a tabby look); the forehead crest and a chain of diamonds over the crown are explicit marks (`make_marks`).
N_HEAD_KEYS = 2     # SPINE_KEYS[:2] are head-local (the nape and the back of the neck, on the surface)
SPINE_KEYS = [  # (point, period of the pattern (m), half width of the band (m), depth allowed below the curve (m))
    # round 3: about 1.6× bigger (the reviewer: the leaves were a third of the reference's size; biggest about
    # eye-sized over the shoulders and the tail base)
    ((0.0, -0.152, 0.79), 0.07, 0.02, 0.05),
    ((0.0, -0.165, 0.7), 0.095, 0.05, 0.07),
    ((0.0, -0.14, 0.655), 0.15, 0.17, 0.11),         # the withers: the biggest
    ((0.0, 0.0, 0.648), 0.12, 0.15, 0.11),
    ((0.0, 0.15, 0.648), 0.11, 0.14, 0.11),
    ((0.0, 0.265, 0.64), 0.14, 0.16, 0.1),           # the tail base: big again
]
# the shoulder's line (down the front of the shoulder) and the hind leg's (down the back of the thigh to the hock),
# 2-turnaround.png side view; both sides
# Nov 13 (the review: a bar cluster on the shoulders and a one-sided ladder on the thigh): no limb lines; the one spine
# chain carries the embers
LIMB_KEYS: dict = {}
# (row, τ, phase, half length, half width, keep): round 2, a fused herringbone (round 1's two parallel rows of even
# ovals read as a dotted line): fat diamonds on the midline, the chevron arms' inner tips touching them
# round 3b: the flanking leaves smaller, angled back along the body (28°, not 48°) and staggered row to row, so the
# chain reads as one herringbone on the midline (round 3's centre, side and outer leaves lined up into bars across the
# back in the 3/4 view and the clips)
# Nov 12 (from straight behind the chain read as a dotted line): the midline diamonds touch, one continuous chain; the
# chevron arms sit between them with their inner tips on it, angled back 38° (a V from behind, short angled marks from
# the side, not bars); a sparse outer row lies nearly along the body (20°). The 7th value is the row's own tilt.
# Nov 13 (final round, the originality must): ONE chain of leaves, staggered two abreast along the spine, each leaf much
# longer along the spine than across and angled only a little outward, so the back camera sees chevrons, never bars
EMBER_ROWS = ((1, 0.2, 0.0, 0.42, 0.12, 1.0, 12.0), (-1, -0.2, 0.5, 0.42, 0.12, 1.0, 12.0))
# Nov 12 (from behind: horizontal arcs and dots, a famous fire kitten's stripes): one chain of nested, forward-pointing
# chevrons that touch: each midline diamond carries two arms from its middle, swept back 50° (a '^' from behind); no
# outer row
EMBER_TILT = math.radians(28)      # (the default tilt of a row without its own)


def _row_tilt(row_spec) -> float:
    row = row_spec[0]
    deg = row_spec[6] if len(row_spec) > 6 else math.degrees(EMBER_TILT)
    return math.radians(deg) * (1 if row > 0 else -1 if row < 0 else 0)
EMBER_JITTER = (0.65, 0.6)         # leaf size = (a + b · random) per leaf: uneven, like hot coals


def _spine_dense():
    tail_top = [tuple(v3(p) + v3((0.0, -T2, T1)) / max(1e-9, math.hypot(T1, T2)) * float(tail_radius(t)))
                for p, t, T1, T2 in _tail_key_frames()]
    # the keys on the head and the neck (the first N_HEAD_KEYS) grow with the head
    head = [(tuple(map(float, H(p))), per * HEAD_K, band * HEAD_K, dep * HEAD_K) for p, per, band, dep in SPINE_KEYS[:N_HEAD_KEYS]]
    keys = head + SPINE_KEYS[N_HEAD_KEYS:] + [(p, per, band, dep) for p, (per, band, dep) in zip(tail_top, _tail_band())]
    pts = [k[0] for k in keys]
    n_per = 8
    dense = catmull(pts, n_per)
    m = len(dense)
    kp = np.arange(len(keys)) * n_per
    per = np.interp(np.arange(m), kp, [k[1] for k in keys])
    band = np.interp(np.arange(m), kp, [k[2] for k in keys])
    dep = np.interp(np.arange(m), kp, [k[3] for k in keys])
    return dense, per, band, dep


def _tail_key_frames():
    """Points along the tail's centre (its 6 keys minus the root) with t and the tangent (y, z)."""
    out = []
    for p in TAIL_PTS[1:]:
        t, _d, _c, T = tail_param(v3(p)[None])
        out.append((p, float(t[0]), float(T[0, 1]), float(T[0, 2])))
    return out


def _tail_band():
    return [(0.11, 0.09, 0.07), (0.1, 0.09, 0.072), (0.095, 0.09, 0.074), (0.09, 0.09, 0.076), (0.08, 0.075, 0.06)]


_SPINE: dict = {}


def spine():
    if not _SPINE:
        dense, per, band, dep = _spine_dense()
        s = arc_lengths(dense)
        sigma = np.concatenate([[0.0], np.cumsum(np.diff(s) / (0.5 * (per[1:] + per[:-1])))])
        _SPINE.update(dense=dense, s=s, per=per, band=band, dep=dep, sigma=sigma)
        limbs = []
        for name, keys in LIMB_KEYS.items():
            for side in (1, -1):
                pts = [(x * side, y, z) for (x, y, z), _p in keys]
                d = catmull(pts, 6)
                ss = arc_lengths(d)
                kp = np.arange(len(keys)) * 6
                pr = np.interp(np.arange(len(d)), kp, [p for _k, p in keys])
                sg = np.concatenate([[0.0], np.cumsum(np.diff(ss) / (0.5 * (pr[1:] + pr[:-1])))])
                limbs.append({'name': name, 'side': side, 'dense': d, 's': ss, 'per': pr, 'sigma': sg + 0.37 * (1 + side)})
        _SPINE['limbs'] = limbs
    return _SPINE


def ember_coords(p: np.ndarray, pal: dict | None = None) -> dict[str, np.ndarray]:
    """Per point: σ (cells along the curve), τ (cells across), the band's envelope 0..1, and 'spark' (the wider
    envelope of the tiny ember sparks). From the spine and, below its band, the shoulder and hind leg lines."""
    sp = spine()
    k = len(p)
    s, c, T, d = poly_nearest_fast(p, sp['dense'], 0.2)
    i = np.clip(np.searchsorted(sp['s'], s) - 1, 0, len(sp['s']) - 2)
    f = np.clip((s - sp['s'][i]) / np.maximum(sp['s'][i + 1] - sp['s'][i], 1e-9), -2, 3)
    sigma = sp['sigma'][i] + f * (sp['sigma'][i + 1] - sp['sigma'][i])
    per = sp['per'][i] + np.clip(f, 0, 1) * (sp['per'][i + 1] - sp['per'][i])
    band = sp['band'][i] + np.clip(f, 0, 1) * (sp['band'][i + 1] - sp['band'][i])
    dep = sp['dep'][i] + np.clip(f, 0, 1) * (sp['dep'][i + 1] - sp['dep'][i])
    q = p - c
    Uv = norm(np.stack([np.zeros(k), -T[:, 2], T[:, 1]], axis=1))
    depth = (q * Uv).sum(1)
    # across: the chord from the curve (≈ the arc length round the back or the tail), signed by the side; q·X alone
    # squeezed the rows together on the flanks of the tail and stretched the leaves into bands
    t = np.sign(q[:, 0]) * np.sqrt(np.maximum((q * q).sum(1) - ((q * T).sum(1)) ** 2, 0.0))
    s_end = sp['s'][-1]
    near = d < 0.3                                      # points outside the search box get d = 9 (and s = 0)
    env = smooth(band + 0.012, band - 0.012, np.abs(t)) * smooth(-dep - 0.01, -dep + 0.015, depth) * near
    env *= smooth(0.008, 0.032, s) * smooth(s_end + 0.02, s_end - 0.08, s)     # the flame's lower tip fades in between the eyes
    tau = t / per
    spark = smooth(band * 1.9 + 0.02, band * 1.2, np.abs(t)) * smooth(-dep * 1.6 - 0.02, -dep, depth) * smooth(-0.01, 0.03, s) * near
    # the limb lines (outside the spine's band)
    for lb in sp['limbs']:
        ls, lc, lT, ld = poly_nearest_fast(p, lb['dense'], 0.12)
        out = v3((float(lb['side']), 0.0, 0.0))
        lq = p - lc
        B = norm(np.cross(lT, np.tile(out, (k, 1))))
        lt = (lq * B).sum(1)
        lt = np.sign(lt) * np.sqrt(np.maximum(lt * lt + np.minimum((lq * out).sum(1), 0.0) ** 2, 0.0))
        ldep = (lq * out).sum(1)
        li = np.clip(np.searchsorted(lb['s'], ls) - 1, 0, len(lb['s']) - 2)
        lf = np.clip((ls - lb['s'][li]) / np.maximum(lb['s'][li + 1] - lb['s'][li], 1e-9), -2, 3)
        lsig = lb['sigma'][li] + lf * (lb['sigma'][li + 1] - lb['sigma'][li])
        lper = lb['per'][li] + np.clip(lf, 0, 1) * (lb['per'][li + 1] - lb['per'][li])
        lend = lb['s'][-1]
        # only the centre row on a limb line: the envelope ends before the side rows
        lenv = (smooth(0.026, 0.014, np.abs(lt)) * smooth(-0.03, -0.012, ldep) * smooth(-0.01, 0.01, ls) * smooth(lend + 0.01, lend - 0.03, ls)
                * smooth(0.09, 0.06, ld))           # the limb line only near it (far points get s = 0 and d = 9)
        take = lenv > env
        sigma = np.where(take, lsig + 40.0, sigma)        # the limbs' σ live far from the spine's (their own leaves)
        tau = np.where(take, lt / lper, tau)
        env = np.where(take, lenv, env)
    return {'sigma': sigma, 'tau': tau, 'env': env, 'spark': spark}


def leaf_np(sig: np.ndarray, tau: np.ndarray, size: float = 1.0, seed: int = 0) -> np.ndarray:
    """The herringbone in numpy (the shape preview; the bake draws the same thing per pixel in `body_material`)."""
    out = np.zeros(len(sig))
    for spec in EMBER_ROWS:
        row, tr, ph, a, b, keep = spec[:6]
        u = sig - ph
        cell = np.floor(u)
        lx = u - cell - 0.5
        ly = tau - tr
        th = _row_tilt(spec)
        xr = lx * math.cos(th) + ly * math.sin(th)
        yr = -lx * math.sin(th) + ly * math.cos(th)
        h = np.sin(cell * 12.9898 + row * 78.233 + seed) * 43758.5453
        h = h - np.floor(h)
        sz = (EMBER_JITTER[0] + EMBER_JITTER[1] * h) * size
        aa, bb = a * sz, b * sz
        den = np.maximum(1.0 - (xr / aa) ** 2, 1e-3)
        m = np.abs(yr) / bb / den
        leaf = smooth(1.15, 0.85, m) * (np.abs(xr) < aa) * (h < keep + 0.001)
        out = np.maximum(out, leaf)
    return out


def flame_np(tt: np.ndarray, tail: np.ndarray, start: float = FLAME_START) -> np.ndarray:
    return smooth(start, start + 0.2, tt) * tail


# ----------------------------------------------------------------------------- paint (numpy, per source vertex)
def light_mask(p: np.ndarray, z: dict) -> np.ndarray:
    """0 the charcoal fur … 1 the pale marking, at the roots: the muzzle, the chin and the lower cheeks, the throat and
    chest, the belly, the tail's underside."""
    x, y, zz = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    hl = Hinv(p)
    hy, hz, hax = hl[:, 1], hl[:, 2], np.abs(hl[:, 0])
    face = np.maximum(ell_soft(p, MUZZLE[0], tuple(r * 1.25 for r in MUZZLE[1]), 0.15), ell_soft(hl, (0.0, -0.505, 0.745), (0.07, 0.06, 0.04), 0.2))
    # the lower face: below a line that runs under the eyes, from the top of the nose out to the cheeks
    under = smooth(0.012, -0.006, hz - (0.8 + 0.035 * smooth(0.0, 0.06, hax) - 0.03 * smooth(0.11, 0.17, hax)))
    # Nov 12: not out to the cheeks' edges (the ruff there takes the dark coat: pale ruff cards read as straw)
    face = np.maximum(face, under * z['head'] * (hy < -0.36) * ~z['ear'] * smooth(0.155, 0.12, hax))
    face = np.where(z['ear'], 0.0, face)
    # Nov 13: the throat's pale only at the front (it wrapped the neck like a collar), and the bib narrows to a point
    # between the forelegs
    throat = ell_soft(hl, (0.0, -0.42, 0.68), (0.06, 0.08, 0.09), 0.2) * smooth(-0.3, -0.36, hy)
    bib_w = 0.02 + 0.09 * smooth(0.38, 0.6, zz) - 0.05 * smooth(0.62, 0.72, zz)
    bib = smooth(bib_w + 0.012, bib_w - 0.012, ax) * smooth(-0.19, -0.24, y) * smooth(0.36, 0.4, zz) * smooth(0.78, 0.74, zz)
    bib *= ~z['tail']
    light = np.maximum(face, np.maximum(throat, bib) * (~z['head'] | z['chin'] | (hz < 0.74)))
    zb = np.interp(y, [-0.38, -0.22, -0.05, 0.15, 0.3], [0.45, 0.435, 0.425, 0.425, 0.44])
    # the belly's underside only (round 2: across the whole lower body it made pale bands round the tops of the legs)
    # round 3b: a little higher up the sides, so the pale belly line shows from the side and runs to the inner thighs
    light = np.maximum(light, z['torso'] * smooth(zb + 0.034, zb - 0.004, zz) * smooth(0.14, 0.1, ax))
    # round 3: the pale underside runs on to the inner thighs (2-turnaround side)
    for lg in ('BL', 'BR'):
        lx = abs(LEGS[lg][0])
        light = np.maximum(light, z['legs'][lg] * smooth(lx - 0.01, lx - 0.04, ax) * smooth(0.2, 0.3, zz) * smooth(0.5, 0.42, zz))
    # (round 2: no paler inner legs; with the pale marking they read as bands round the tops of the legs)
    # the tail's underside (the side away from the embers), up to where it starts to burn
    under_t = z['tail'] * smooth(-0.1, -0.6, _tail_side(p, z)) * smooth(FLAME_START, FLAME_START - 0.12, z['tail_t'])
    light = np.maximum(light, under_t * 0.0)    # round 3: none (from behind it read as a pale silver saddle)
    return np.clip(light, 0.0, 1.0)


def _tail_side(p: np.ndarray, z: dict) -> np.ndarray:
    """−1 … 1: where a tail point sits round the tail (1 = the ember side, −1 = the underside)."""
    t = np.clip(z['tail_t'], 0, 1)
    j = np.clip(np.round(t * (len(TAIL_CURVE) - 1)).astype(int), 0, len(TAIL_CURVE) - 1)
    c = TAIL_CURVE[j]
    up = tail_up(z['tail_T'])
    q = norm(p - c)
    return (q * up).sum(1)


def ear_skin_mask(z: dict) -> np.ndarray:
    """0..1: the inner ear's bare salmon skin, high up toward the outer edge of the cup (round 3, 1-hero)."""
    u, v = z['ear_u'], z['ear_v']
    cup = z['ear_inner'].astype(float)
    # Nov 13: salmon skin over most of the cup, cream tufts only low and at the rim
    return cup * smooth(0.14, 0.3, v) * smooth(0.97, 0.88, v) * smooth(0.12, 0.26, u) * smooth(0.9, 0.8, u)


def ear_paint(p: np.ndarray, z: dict) -> tuple[np.ndarray, np.ndarray]:
    """(the inner ear's smooth skin 0..1, its pale fur 0..1) on the cup's face."""
    v = z['ear_v']
    u = z['ear_u']
    cup = z['ear_inner'].astype(float)
    # 1-hero.png: pale fur fills the inner half of the cup low down, the salmon skin shows above and to the outside
    # round 3 (1-hero): pale cream fur fills most of the cup; the salmon skin shows only high up toward the outer edge
    skin = ear_skin_mask(z)
    fur = cup * smooth(0.0, 0.06, u) * smooth(0.92, 0.75, u) * (1.0 - skin)
    return skin, fur


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    """Flat colours for tools/blender/monsters/shape_preview.py: fur and belly, the inner ear, the ember leaves (per
    vertex, so coarser than the bake's) and the tail's flame end."""
    z = zones(co, vn)
    col = colours(PALETTE)
    light = light_mask(co, z)
    rgb = lin(col['fur'])[None] * (1 - light[:, None]) + lin(col['pale'])[None] * light[:, None]
    skin, efur = ear_paint(co, z)
    rgb = rgb * (1 - efur[:, None]) + lin(col['ear_fur'])[None] * efur[:, None]
    rgb = rgb * (1 - skin[:, None]) + lin(col['ear_skin'])[None] * skin[:, None]
    em = ember_coords(co)
    leaf = leaf_np(em['sigma'], em['tau']) * em['env']
    flame = flame_np(z['tail_t'], z['tail'])
    rgb = rgb * (1 - flame[:, None]) + lin(col['ember'])[None] * flame[:, None]
    return rgb * (1 - leaf[:, None]) + lin(col['ember_hot'])[None] * leaf[:, None]


def lin(h: str) -> np.ndarray:
    return v3(C.lin_rgb(h))


_LIGHT: dict[str, np.ndarray] = {}


def _light_of(ob, root: np.ndarray, pos: np.ndarray, kind: np.ndarray, tpos: np.ndarray) -> np.ndarray:
    """The light mask a source is painted with, by the roots; a lock that crosses a border blends toward the colour
    under its tip along its length (Puddlepup P1.2). Cached per source."""
    if ob.name not in _LIGHT:
        light = light_mask(root, zones(root))
        lock = kind > 0.5
        if lock.any():
            lp = light_mask(pos[lock], zones(pos[lock]))
            k = 0.6 * tpos[lock]
            light[lock] = light[lock] * (1 - k) + lp * k
        _LIGHT[ob.name] = light
    return _LIGHT[ob.name]


_EMBER: dict[str, dict] = {}


def _ember_of(ob, pos: np.ndarray) -> dict:
    if ob.name not in _EMBER:
        _EMBER[ob.name] = ember_coords(pos)
    return _EMBER[ob.name]


def paint_arrays(ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
    """Per vertex of a body source: 'paint' = the fur, or the pale marking where `light` says so (by root, linear), the
    inner ear's skin and pale fur, 'light', 'shade' (darker roots, lighter tips) and 'rough'."""
    col = colours(pal)
    root = S.attr_array(ob, 'root').astype(np.float64)
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', co)
    pos = co.reshape(-1, 3).astype(np.float64)
    kind = S.attr_array(ob, 'kind')
    tpos = S.attr_array(ob, 'tpos').astype(np.float64)
    lrand = S.attr_array(ob, 'lrand').astype(np.float64)
    light = _light_of(ob, root, pos, kind, tpos)
    # round 2: the pale marking (1-hero.png, 2-turnaround.png), the belly colour lifted toward cream (`colours`)
    rgb = lin(col['fur'])[None, :] * (1 - light[:, None]) + lin(col['pale'])[None, :] * light[:, None]
    # Nov 13: the muzzle and cheeks take the hero's lighter cream (the bib keeps the warmer, darker pale)
    hz_r = Hinv(root)[:, 2]
    face_k = light * (zones(root)['head'] & (hz_r > 0.72)).astype(float)
    rgb = rgb * (1 - face_k[:, None]) + lin(col['face_pale'])[None, :] * face_k[:, None]
    zr = zones(root)
    skin, efur = ear_paint(root, zr)
    rgb = rgb * (1 - efur[:, None]) + lin(col['ear_fur'])[None, :] * efur[:, None]
    rgb = rgb * (1 - skin[:, None]) + lin(col['ear_skin'])[None, :] * skin[:, None]
    # round 3b (3-faces neutral and blink): a light upper lid between the eye and the brow, and the closed lid under
    # the lens the same tone, so the blink shows a light lid over a dark lash curve (round 3's dark lids read as goggles)
    eye_k = eye_surround(root)
    rgb = rgb * (1 - eye_k[:, None]) + lin(C.mix_hex(col['fur'], col['pale'], EYE_SURROUND_MIX))[None, :] * eye_k[:, None]
    is_lock = kind > 0.5
    # round 1 (film look): a dark coat with the Puddlepup shading read as smooth plastic. 4-details.png: charcoal
    # strands with lighter, warmer tips. Darker roots, frosted tips, sleek but not glossy. Round 2: the tips frost to a
    # warm brown on the coat (it read grey-green in the film look) and to a lighter cream on the pale marking.
    tip = np.where(is_lock, np.clip(tpos, 0, 1) ** 1.4, 0.0)
    # the roots shade toward a blue-violet on the dark coat (not on the pale marking)
    root_k = np.where(is_lock, 0.42 * (1.0 - np.clip(tpos, 0, 1)) ** 1.5, 0.0) * (1.0 - light) * (1.0 - skin) * (1.0 - eye_k)
    rgb = rgb * (1 - root_k[:, None]) + lin(col['shadow'])[None, :] * root_k[:, None]
    frost = 0.3 * tip * (1.0 - skin) * (1.0 - efur)
    # Nov 12: the brow, crown and eye area keep the charcoal coat (their frosted tips read mid grey, a tabby)
    frost = frost * (1.0 - 0.7 * (zr['head'] & ~zr['muzzle'] & (light < 0.5)))
    frost_col = (lin(col['frost'])[None, :] * (1 - light[:, None])
                 + lin(C.mix_hex(col['pale'], '#FFF8EE', 0.45))[None, :] * light[:, None])
    rgb = rgb * (1 - frost[:, None]) + frost_col * frost[:, None]
    shade = 0.68 + 0.42 * np.clip(tpos, 0, 1) + 0.12 * (lrand - 0.5)
    shade = shade - 0.08 * light * (1.0 - np.clip(tpos, 0, 1))  # the pale fur's roots a touch shaded (strand depth)
    shade = np.where(is_lock, shade, 1.0)
    rough = np.where(is_lock, 0.6 + 0.2 * np.abs(tpos - 0.45), 0.7)
    coat = np.where(is_lock, 0.04, 0.03)
    rough = rough * (1 - skin) + 0.5 * skin
    coat = coat * (1 - skin) + 0.12 * skin
    glossy = ell_soft(pos, tuple(NOSE_C), tuple(r * HEAD_K for r in (0.024, 0.017, 0.014)), 0.08)
    for leg in LEGS:
        pc, pr = pad_centre(leg)
        glossy = np.maximum(glossy, ell_soft(pos, tuple(pc), pr, 0.1))
    rough = rough * (1 - glossy) + 0.28 * glossy
    # round 3b: a matte crown (its sheen read as a shiny dome)
    rough = np.where(zr['crown'] & ~zr['ear'], np.maximum(rough, 0.86), rough)
    # Nov 13: the forehead and the bridge matte too (a specular band read as a vinyl helmet)
    rough = np.where(zr['head'] & ~zr['ear'] & ~zr['nose'], np.maximum(rough, 0.9), rough)
    coat = np.where(zr['head'] & ~zr['nose'], np.minimum(coat, 0.01), coat)
    coat = coat * (1 - glossy) + 0.7 * glossy
    # round 2: the ear tips burn where the ember tufts grow (the tufts are tuft locks, which can't glow; the skin and
    # the lying locks under them can), and the high tuft locks baked at their roots glow too
    etip = zr['ear'] * smooth(0.8, 0.95, zr['ear_u'])
    rgb = rgb * (1 - etip[:, None]) + lin(col['ember'])[None, :] * etip[:, None]
    glow = np.maximum(etip, (np.abs(kind - S.KIND_TUFT) < 0.5).astype(float))
    return {'paint': rgb, 'light': light, 'shade': shade, 'rough': np.stack([np.ones(len(pos)), rough, coat], axis=1),
            'glow': glow}


def paint_sources(body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
    """Store the paint on every source: 'paint' (base), 'paint_<short>' (each variant), 'rough', 'light', 'shade', and
    the ember coordinates ('ember_s', 'ember_t', 'ember_env', 'spark') and the tail's 'flame' and 'tail_t'."""
    for ob in body_srcs:
        a = paint_arrays(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'light', a['light'])
        S.add_attr(ob, 'shade', a['shade'])
        S.add_attr(ob, 'glow', a['glow'])          # the shared glow pass's per-vertex value (the ear tips, the tuft roots)
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), paint_arrays(ob, var)['paint'])
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get('co', co)
        pos = co.reshape(-1, 3).astype(np.float64)
        em = _ember_of(ob, pos)
        S.add_attr(ob, 'ember_s', em['sigma'])
        S.add_attr(ob, 'ember_t', em['tau'])
        S.add_attr(ob, 'ember_env', em['env'])
        S.add_attr(ob, 'spark', em['spark'])
        z = zones(pos)
        S.add_attr(ob, 'tail_t', np.where(z['tail'], z['tail_t'], -1.0))
        side = np.where(z['tail'], _tail_side(pos, z), 0.0)
        S.add_attr(ob, 'tail_side', side)
        C.log(f'paint {ob.name}: {len(pos)} verts, ember band on {int((em["env"] > 0.01).sum())}')
    for ob in fins:
        n = len(ob.data.vertices)
        S.set_colour_attr(ob, 'paint', np.tile(lin(colours(PALETTE)['ear_skin']), (n, 1)))
        S.set_colour_attr(ob, 'rough', np.tile(v3((1.0, 0.5, 0.2)), (n, 1)))
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), np.tile(lin(colours(var)['ear_skin']), (n, 1)))
    for ob in props:
        n = len(ob.data.vertices)
        co = np.empty(n * 3, np.float32)
        ob.data.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3).astype(np.float64)
        fu = S.attr_array(ob, 'flame_u').astype(np.float64) if 'flame_u' in ob.data.attributes else np.zeros(n)
        is_flame = (S.attr_array(ob, 'flame_part') != 0) if 'flame_part' in ob.data.attributes else np.zeros(n, bool)
        mp = S.attr_array(ob, 'mouth_part').astype(np.float64) if 'mouth_part' in ob.data.attributes else np.zeros(n)
        root = smooth(0.06, 0.02, np.abs(Hinv(co)[:, 0]) - 0.03)[:, None]
        mouth_rgb = mouth_colours(co, mp)
        is_mouth = np.abs(mp) > 0.5
        for attr, pal in [('paint', PALETTE)] + [(U.variant_attr(vid, ID), var) for vid, var in VARIANTS.items()]:
            c = colours(pal)
            # the whiskers: pale, a little glossy, slightly darker at the root
            rgb = lin(c['whisker'])[None, :] * (1 - root * 0.6) + lin(c['pale'])[None, :] * (root * 0.6)
            # the flames: deep ember at the root, the ember colour, hot yellow-orange at the tips (tuft_colours)
            flame = tuft_colours(pal, fu, np.full(n, 0.5))
            rgb = np.where(is_flame[:, None], flame, rgb)
            rgb = np.where(is_mouth[:, None], mouth_rgb, rgb)
            S.set_colour_attr(ob, attr, rgb)
        rough = np.where(is_flame, 0.55, np.where(is_mouth, 0.5, 0.42))
        coat = np.where(is_flame, 0.0, np.where(is_mouth, 0.25, 0.35))
        S.set_colour_attr(ob, 'rough', np.stack([np.ones(n), rough, coat], axis=1))
        # the flames glow, hotter toward their tips; the whiskers don't
        S.add_attr(ob, 'glow', np.where(is_flame, 0.45 + 0.35 * np.clip(fu, 0, 1), 0.0))   # capped (no white core)


# the mouth's colours (the same on every variant): a dark rose palate and gums, a pink tongue down the middle of the
# floor, a deep throat and ivory fangs (3-faces happy)
# Nov 13: darker inside (it read as a pale pink tongue tip); a dark lip rim so the closed seam reads as a hairline
MOUTH_COLS = {'palate': '#3A1419', 'gum': '#4A1A22', 'tongue': '#B04A5A', 'throat': '#14060A', 'fang': '#F4EEE4', 'lip': '#1A1012'}


def mouth_colours(co: np.ndarray, mp: np.ndarray) -> np.ndarray:
    hl = Hinv(co)
    f = MO.lip_f(hl)
    rgb = np.tile(lin(MOUTH_COLS['palate']), (len(co), 1))
    tongue = smooth(0.026, 0.016, np.abs(hl[:, 0])) * smooth(-0.44, -0.47, hl[:, 1]) * smooth(-0.0015, -0.005, f)
    floor = np.where((mp < -0.5)[:, None], lin(MOUTH_COLS['gum'])[None] * (1 - tongue[:, None]) + lin(MOUTH_COLS['tongue'])[None] * tongue[:, None], rgb)
    rgb = np.where((mp < -0.5)[:, None], floor, rgb)
    rgb = np.where((np.abs(mp - 2) < 0.5)[:, None], lin(MOUTH_COLS['throat'])[None], rgb)
    rgb = np.where((np.abs(mp - 3) < 0.5)[:, None], lin(MOUTH_COLS['fang'])[None], rgb)
    # the lips' inner rims, dark where the inner skin meets the cut
    rim = smooth(0.008, 0.002, np.abs(f)) * (np.abs(mp) < 1.5)
    return rgb * (1 - rim[:, None]) + lin(MOUTH_COLS['lip'])[None] * rim[:, None]


# ----------------------------------------------------------------------------- marks: the explicit, crisp ones
def _snap(bvh, p, ax, a: float, b: float, kind: str) -> dict:
    """A leaf mark on the body's surface near world point `p`: centre, long axis (in the surface), normal, half sizes."""
    hit = bvh.find_nearest(Vector(tuple(map(float, p))))
    c = v3(hit[0]) if hit[0] is not None else v3(p)
    n = v3(hit[1]) if hit[0] is not None else v3((0.0, -1.0, 0.0))
    axv = v3(ax) - n * float(v3(ax) @ n)
    axv /= max(np.linalg.norm(axv), 1e-9)
    return {'c': list(map(float, c)), 'ax': list(map(float, axv)), 'n': list(map(float, n)), 'a': float(a), 'b': float(b), 'kind': kind}


def forehead_crest() -> list[tuple]:
    """Round 2 (3-faces neutral, 1-hero): one fused flame crest on the forehead, a central flame rising from between
    the eyes with three pairs of V chevrons opening upward, and a chain of diamonds on over the crown to the nape.
    Head-local (point, direction, half length, half width, kind)."""
    bot, top = v3((0.0, -0.474, 0.872)), v3((0.0, -0.412, 0.99))
    up = norm((top - bot)[None])[0]
    out = [(tuple((bot + top) * 0.5), tuple(up), 0.066, 0.0115, 'crest')]
    for f, a in ((0.2, 0.026), (0.42, 0.024), (0.64, 0.02)):
        base = bot + (top - bot) * f
        for s in (1, -1):
            d = up * math.cos(math.radians(44)) + v3((s, 0.0, 0.0)) * math.sin(math.radians(44))
            out.append((tuple(base + d * a * 0.9 + v3((0.005 * s, 0.0, 0.0))), tuple(d), a, 0.0068, 'crest'))
    # Nov 12: over the crown to the nape, the same chain as the back: touching diamonds, each with two arms swept back
    # (round 3's five separate diamonds read as a dotted line from behind)
    crown = [v3(q) for q in ((0.0, -0.395, 0.998), (0.0, -0.345, 1.004), (0.0, -0.293, 0.995), (0.0, -0.243, 0.974),
                             (0.0, -0.2, 0.94), (0.0, -0.168, 0.895))]
    for i, q in enumerate(crown):
        nxt = crown[min(i + 1, len(crown) - 1)] - crown[max(i - 1, 0)]
        back = norm(nxt[None])[0]
        sz = 1.0 - 0.15 * i / (len(crown) - 1)
        out.append((tuple(q), tuple(back), 0.027 * sz, 0.0095 * sz, 'crown'))
        for s in (1, -1):
            d = back * math.cos(math.radians(50)) + v3((s, 0.0, 0.0)) * math.sin(math.radians(50))
            out.append((tuple(q + back * 0.006 + d * 0.013 * sz), tuple(d), 0.015 * sz, 0.005 * sz, 'crown'))
    return out


def cheek_embers() -> list[tuple]:
    """Round 2 (3-faces neutral): 3–4 small embers fanning back from under each eye's outer corner. Head-local."""
    out = []
    pivot = v3((0.118, -0.436, 0.83))
    for i, ang in enumerate((-34.0, -14.0, 6.0, 26.0)):
        a = math.radians(ang)
        d = v3((0.62, 0.78, 0.0)) * math.cos(a) + v3((0.0, 0.0, 1.0)) * math.sin(a)
        out.append((tuple(pivot + d * (0.026 + 0.003 * i)), tuple(d), 0.019 - 0.0015 * abs(i - 1.5), 0.0058, 'cheek'))
    return out


def make_marks(hi_body: bpy.types.Object):
    """The explicit marks the bake draws per pixel, snapped onto the high body (JSON-able): the forehead crest and the
    crown chain, the cheek embers, a crescent claw slit on every toe."""
    bvh = BVHTree.FromObject(hi_body, bpy.context.evaluated_depsgraph_get())
    leaves = []
    for p, d, a, b, kind in forehead_crest():
        leaves.append(_snap(bvh, H(p), Hd(d), a * HEAD_K, b * HEAD_K, kind))
    for s in (1, -1):
        for p, d, a, b, kind in cheek_embers():
            leaves.append(_snap(bvh, H((p[0] * s, p[1], p[2])), Hd((d[0] * s, d[1], d[2])), a * HEAD_K, b * HEAD_K, kind))
    for leg in LEGS:
        for t in toe_centres(leg):
            # the claw slit: a thin glowing crescent down the front of the toe, into its tip (1-hero, 4-details 3)
            leaves.append(_snap(bvh, (t.x, t.y - 0.03, 0.018), (0.0, -0.35, 1.0), 0.016, 0.0052, 'claw'))
    return {'leaves': leaves}


# ----------------------------------------------------------------------------- paint (nodes: the crisp details, per pixel)
def _ell(nb: NB, p, c, r, soft=0.08):
    q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
    return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)


def _leaf_frame(nb: NB, p, c, ax, nrm, a, b, depth=0.02, soft=0.15, core: bool = False):
    """A leaf (pointed at both ends, round across) centred at c, its long axis `ax`, lying on a surface of normal
    `nrm`: 1 inside. With `core`, also its hot middle: (mask, core)."""
    axv = v3(ax) / np.linalg.norm(ax)
    nv = v3(nrm) - axv * float(v3(nrm) @ axv)
    nv /= np.linalg.norm(nv)
    bv = np.cross(nv, axv)
    q = nb.vmath('SUBTRACT', p, tuple(c))
    x = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', q, tuple(axv)), a)
    y = nb.math('ABSOLUTE', nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', q, tuple(bv)), b))
    zz = nb.math('ABSOLUTE', nb.vmath('DOT_PRODUCT', q, tuple(nv)))
    den = nb.math('MAXIMUM', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', x, x)), 0.001)
    m = nb.math('DIVIDE', y, den)
    near = nb.smooth(zz, depth, depth * 0.6)
    leaf = nb.math('MULTIPLY', nb.smooth(m, 1.0 + soft, 1.0 - soft), near)
    if not core:
        return leaf
    return leaf, nb.math('MULTIPLY', nb.smooth(m, 0.7, 0.35), near)


def _herringbone(nb: NB, size: float):
    """The ember leaves from the per-vertex curve coordinates: (mask, core) sockets, 0..1."""
    sig = nb.attribute('ember_s').outputs['Fac']
    tau = nb.attribute('ember_t').outputs['Fac']
    mask = None
    core = None
    for spec in EMBER_ROWS:
        row, tr, ph, a, b, keep = spec[:6]
        u = nb.math('SUBTRACT', sig, ph)
        cell = nb.math('FLOOR', u)
        lx = nb.math('SUBTRACT', nb.math('SUBTRACT', u, cell), 0.5)
        ly = nb.math('SUBTRACT', tau, tr)
        th = _row_tilt(spec)
        ct, st = math.cos(th), math.sin(th)
        xr = nb.math('ADD', nb.math('MULTIPLY', lx, ct), nb.math('MULTIPLY', ly, st))
        yr = nb.math('ADD', nb.math('MULTIPLY', lx, -st), nb.math('MULTIPLY', ly, ct))
        wn = nb.new('ShaderNodeTexWhiteNoise', noise_dimensions='2D')
        nb.link(nb.comb(cell, float(row) * 7.31 + 0.5, 0.0), wn.inputs['Vector'])
        h = wn.outputs['Value']
        sz = nb.math('MULTIPLY_ADD', h, EMBER_JITTER[1] * size, EMBER_JITTER[0] * size)
        aa = nb.math('MULTIPLY', sz, a)
        bb = nb.math('MULTIPLY', sz, b)
        xn = nb.math('DIVIDE', xr, aa)
        den = nb.math('MAXIMUM', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', xn, xn)), 0.001)
        m = nb.math('DIVIDE', nb.math('DIVIDE', nb.math('ABSOLUTE', yr), bb), den)
        inside = nb.math('LESS_THAN', nb.math('ABSOLUTE', xn), 1.0)
        keep_ok = nb.math('LESS_THAN', h, keep + 0.001)
        gate = nb.math('MULTIPLY', inside, keep_ok)
        leaf = nb.math('MULTIPLY', nb.smooth(m, 1.18, 0.82), gate)
        hot = nb.math('MULTIPLY', nb.smooth(m, 0.56, 0.24), gate)     # round 3b: a smaller gold core in an orange leaf
        mask = leaf if mask is None else nb.math('MAXIMUM', mask, leaf)
        core = hot if core is None else nb.math('MAXIMUM', core, hot)
    env = nb.attribute('ember_env').outputs['Fac']
    return nb.math('MULTIPLY', mask, env), nb.math('MULTIPLY', core, env)


def _ember_layers(nb: NB, pos, pal: dict, marks) -> dict:
    """The glowing parts as masks: the herringbone, the sparks, the tail's flame end, the cheek dashes, the claws."""
    size = float(pal.get('ember_size', 1.0))
    leaf, core = _herringbone(nb, size)
    # sparks: tiny dots scattered over the band and a little past it (round 2: finer and more of them)
    vor = nb.new('ShaderNodeTexVoronoi', feature='F1')
    vor.inputs['Scale'].default_value = 95.0
    vor.inputs['Randomness'].default_value = 1.0
    nb.link(pos, vor.inputs['Vector'])
    dot = nb.smooth(vor.outputs['Distance'], 0.07, 0.04)
    pick = nb.math('LESS_THAN', nb.sep_rgb(vor.outputs['Color'])[0], 0.32)
    spark = nb.math('MULTIPLY', nb.math('MULTIPLY', dot, pick), nb.attribute('spark').outputs['Fac'])
    # the tail's ember end: a noisy, flame-tongued front from charcoal to ember, hotter toward the tip
    tt = nb.attribute('tail_t').outputs['Fac']
    start = float(pal.get('flame_start', FLAME_START))
    nz = nb.noise(pos, 9.0, 2.0, 0.6)
    tw = nb.math('ADD', tt, nb.math('MULTIPLY', nb.math('SUBTRACT', nz, 0.5), 0.16))
    flame = nb.smooth(tw, start, start + 0.16)
    flame_hot = nb.smooth(tw, start + 0.2, 1.0)
    # the explicit leaves (make_marks): the forehead crest and the crown chain, the cheek embers (with hot cores), the
    # claw slits (hot)
    dashes = dcore = claws = None
    for d in (marks or {}).get('leaves', []):
        k = size ** 0.5 if d['kind'] != 'claw' else 1.0
        depth = 0.012 if d['kind'] == 'claw' else 0.025
        if d['kind'] == 'claw':
            e = _leaf_frame(nb, pos, d['c'], d['ax'], d['n'], d['a'], d['b'], depth, 0.25)
            claws = e if claws is None else nb.math('MAXIMUM', claws, e)
            continue
        e, ec = _leaf_frame(nb, pos, d['c'], d['ax'], d['n'], d['a'] * k, d['b'] * k, depth, 0.18, core=True)
        dashes = e if dashes is None else nb.math('MAXIMUM', dashes, e)
        dcore = ec if dcore is None else nb.math('MAXIMUM', dcore, ec)
    is_body = nb.math('LESS_THAN', nb.attribute('kind').outputs['Fac'], 1.5)
    return {'leaf': leaf, 'core': core, 'spark': nb.math('MULTIPLY', spark, is_body), 'flame': flame, 'flame_hot': flame_hot,
            'dashes': dashes, 'dcore': dcore, 'claws': claws}


def body_material(name: str, attr: str, pal: dict, marks, glow: bool = False) -> bpy.types.Material:
    """Emission = the painted attribute with the per-pixel details: each lock's shade, the brows, the eye rings, the
    nose, the mouth, the pads, the closed lids; then the embers on top (the herringbone, sparks, the cheek dashes, the
    tail's flame end, the claws). `glow=True` paints only the embers on black (the glow map)."""
    col = colours(pal)
    m, nb = new_mat(name)
    pos = nb.coords().outputs['Object']
    kind = nb.attribute('kind').outputs['Fac']
    is_body = nb.math('LESS_THAN', kind, 0.5)
    shade = nb.attribute('shade').outputs['Fac']
    if glow:
        c = nb.rgb((0.0, 0.0, 0.0))
    else:
        c = nb.attribute(attr).outputs['Color']
        c = nb.mix(1.0, c, nb.comb(shade, shade, shade), blend='MULTIPLY')
        brow = None
        for s in (1, -1):
            cc, xax, yax, look = eye_frame(s)
            # round 2: a thick dark brow stroke, rising toward the outer end (1-hero, 4-details 2)
            # round 3b: a stroke, not a band: higher, slimmer and arched up toward the outer end, with the light upper
            # lid between it and the eye (3-faces neutral); round 3's sat on the lens and made a dark socket band
            bc = cc + yax * (EYE_R * 1.64) + xax * (EYE_R * 0.12 * s)
            ax = (xax * 1.0 + yax * 0.28 * s).normalized()
            e = _leaf_frame(nb, pos, tuple(bc), tuple(ax), tuple(look), EYE_R * 1.08, EYE_R * 0.33, 0.04, 0.3)
            brow = e if brow is None else nb.math('MAXIMUM', brow, e)
            # and the upper lash line's outer flick, out and up past the lens onto the face
            fc = cc + xax * (EYE_R * 1.14 * s) + yax * (EYE_R * 0.34)
            fax = (xax * s * 0.86 + yax * 0.5).normalized()
            e = _leaf_frame(nb, pos, tuple(fc), tuple(fax), tuple(look), EYE_R * 0.6, EYE_R * 0.14, 0.035, 0.3)
            brow = nb.math('MAXIMUM', brow, nb.math('MULTIPLY', e, 1.2))
        c = nb.mix(nb.math('MINIMUM', brow, 1.0), c, nb.rgb(C.lin(col['brow'])))
        ring = None
        for s in (1, -1):
            cc, xax, yax, look = eye_frame(s)
            q = nb.vmath('SUBTRACT', pos, tuple(cc))
            xe = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', q, tuple(xax)), EYE_R * EYE_SHAPE[0] * 1.1)
            ye = nb.math('DIVIDE', nb.vmath('DOT_PRODUCT', q, tuple(yax)), EYE_R * EYE_SHAPE[1] * 1.08)
            ze = nb.vmath('DOT_PRODUCT', q, tuple(look))
            r = nb.vmath('LENGTH', nb.comb(xe, ye, 0.0))
            # round 2: a ring round the lens only, not a disc under it (the closed lids read as pale domes)
            e = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(r, 1.1, 0.92), nb.smooth(r, 0.84, 0.94)), nb.smooth(ze, -0.03, -0.015))
            ring = e if ring is None else nb.math('MAXIMUM', ring, e)
        # round 3: no ring round the eye (the reviewer: a socket ring, goggles in the blink); the brows and the lash flick
        # frame the eye instead
        c = nb.mix(nb.math('MULTIPLY', ring, nb.math('MULTIPLY', is_body, 0.0)), c, nb.rgb(C.lin(col['eye_ring'])))
        c = nb.mix(_ell(nb, pos, tuple(NOSE_C), tuple(r * HEAD_K for r in (0.025, 0.018, 0.015)), 0.1), c, nb.rgb(C.lin(NOSE_HEX)))
        mouth = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.3, clamp=True), is_body)
        c = nb.mix(mouth, c, nb.rgb(C.lin(MOUTH_HEX)))
        # whisker dots on the pads
        dots = None
        for s in (1, -1):
            for (dx, dz) in WHISKER_DOTS:
                e = _ell(nb, pos, tuple(map(float, H((dx * s, pad_front_y(dx), dz)))),
                         tuple(r * HEAD_K for r in (0.0024, 0.01, 0.0024)), 0.3)
                dots = e if dots is None else nb.math('MAXIMUM', dots, e)
        c = nb.mix(nb.math('MULTIPLY', dots, 0.7), c, nb.rgb(C.lin(C.mix_hex(col['pale'], '#2A2022', 0.72))))
        lid = nb.math('MULTIPLY', nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5), is_body)
        # round 2 (3-faces blink): the closed lid is fur-toned, flush with the face, under a dark lash curve
        # round 3b: the lid is painted by `paint_arrays` (the light upper-lid tone of `eye_surround`, on the skin and on
        # the lid's short fur alike); here only a soft blend toward it on the bare skin
        c = nb.mix(nb.math('MULTIPLY', lid, 0.5), c, nb.rgb(C.lin(C.mix_hex(col['fur'], col['pale'], EYE_SURROUND_MIX))))
        lash = nb.math('MULTIPLY', nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.6, clamp=True), is_body)
        c = nb.mix(lash, c, nb.rgb(C.lin(col['lash'])))
        pad = None
        for leg in LEGS:
            pc, pr = pad_centre(leg)
            e = _ell(nb, pos, tuple(pc), pr, 0.15)
            pad = e if pad is None else nb.math('MAXIMUM', pad, e)
            for t in toe_centres(leg):
                pad = nb.math('MAXIMUM', pad, _ell(nb, pos, (t.x, t.y + 0.002, 0.004), (0.014, 0.016, 0.01), 0.2))
        c = nb.mix(pad, c, nb.rgb(C.lin(PAD_HEX)))
    L = _ember_layers(nb, pos, pal, marks)
    ember = nb.rgb(C.lin(col['ember']))
    hot = nb.rgb(C.lin(col['ember_hot']))
    deep = nb.rgb(C.lin(col['ember_deep']))
    # the tail's flame end: deep ember at the front, hot toward the tip
    core_gold = nb.rgb(C.lin(col['ember_core']))
    # the tail's last third: charcoal → ember orange → the gold core toward the tip
    flame_col = nb.mix(L['flame_hot'], ember, nb.rgb(C.lin(col['ember_core_paint'])))
    flame_col = nb.mix(nb.math('SUBTRACT', 1.0, L['flame']), flame_col, deep)
    fl = nb.math('MULTIPLY', L['flame'], nb.math('GREATER_THAN', nb.attribute('tail_t').outputs['Fac'], 0.0))
    if not glow:
        # the fur in the flame keeps a little of its shade (a burning coat, not a flat sticker)
        fcol = nb.mix(1.0, flame_col, nb.comb(nb.math('ADD', 0.35, nb.math('MULTIPLY', shade, 0.65)),
                                              nb.math('ADD', 0.35, nb.math('MULTIPLY', shade, 0.65)),
                                              nb.math('ADD', 0.35, nb.math('MULTIPLY', shade, 0.65))), blend='MULTIPLY')
    else:
        fcol = flame_col
    c = nb.mix(fl, c, fcol)
    leaf_col = nb.mix(L['core'], nb.rgb(C.lin(col['ember_leaf'])), nb.rgb(C.lin(col['ember_core_paint'])))
    c = nb.mix(L['leaf'], c, leaf_col)
    c = nb.mix(L['spark'], c, hot)
    if L['dashes'] is not None:
        # Nov 12: the forehead mark and the cheek fans read yellow: mostly the ember colour, a small hot core
        mark_col = nb.mix(nb.math('MULTIPLY', L['dcore'], 0.55), nb.rgb(C.lin(col['ember_leaf'])), nb.rgb(C.lin(col['ember_core_paint'])))
        c = nb.mix(L['dashes'], c, mark_col)
    if L['claws'] is not None:
        c = nb.mix(L['claws'], c, hot)
    if glow:
        # the glow value 0..1 per pixel (the shared glow feature: the runtime's emissive = base × glow × strength):
        # the leaves (their hot cores fullest), the tail's flame end (hotter toward the tip), the sparks, the cheek
        # dashes and the claw tips
        # round 3b: the leaves glow less (the bloom washed their centres to pale apricot, #FFBC87 measured); the tail's
        # flame end and the claws keep their full glow
        g = nb.math('MAXIMUM', nb.math('MULTIPLY', L['leaf'], EMBER_FILM['leaf_glow']), nb.math('MULTIPLY', L['core'], EMBER_FILM['core_glow']))
        g = nb.math('MAXIMUM', g, nb.math('MULTIPLY', fl, nb.math('ADD', 0.35, nb.math('MULTIPLY', L['flame_hot'], 0.25))))
        g = nb.math('MAXIMUM', g, nb.math('MULTIPLY', L['spark'], 0.6))
        if L['dashes'] is not None:
            g = nb.math('MAXIMUM', g, nb.math('MAXIMUM', nb.math('MULTIPLY', L['dashes'], EMBER_FILM['leaf_glow']),
                                              nb.math('MULTIPLY', L['dcore'], EMBER_FILM['core_glow'])))
        if L['claws'] is not None:
            g = nb.math('MAXIMUM', g, L['claws'])
        g = nb.math('MAXIMUM', g, nb.attribute('glow').outputs['Fac'])     # the per-vertex glow (ear tips, tuft roots)
        c = nb.comb(g, g, g)
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def glow_material(name: str, marks) -> bpy.types.Material:
    """The glow pass (contract: GLOW, `glow_material(name, marks)`, baked into atlas_orm's alpha and shared by every
    variant): emission (g, g, g), g = 0..1 how much a pixel glows, black elsewhere. The leaves are drawn at the largest
    size and the tail burns from the earliest start of any palette (the Bonfire variant's bigger flames), so every
    variant's embers glow; around a base leaf the extra mask lands on charcoal, where base × glow adds next to nothing."""
    pals = [PALETTE] + list(VARIANTS.values())
    union = dict(PALETTE, ember_size=max(float(p.get('ember_size', 1.0)) for p in pals),
                 flame_start=min(float(p.get('flame_start', FLAME_START)) for p in pals))
    return body_material(name, 'paint', union, marks, glow=True)


# the shared glow pass is on (emissive = base × glow × strength; the sidecar's glow block)
GLOW = {'strength': 1.0, 'tint': None}


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None) -> bpy.types.Material:
    """A gold cat eye (CONTENT #FFD15C; each variant its own, e.g. Bonfire #FFF0A8): an amber ring round a tall oval
    pupil (round enough to read cute, as in 1-hero.png; a cat's in 4-details.png), the iris paler low down, a thin dark
    limbal ring, a black rim with a thick upper lash line winged at the outer corner, two crisp catchlights."""
    eye_hex = (pal or PALETTE)['eye']
    m, nb = new_mat(name)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.put(em.inputs['Color'], (1.0, 0.05, 1.0))
        nb.output(em.outputs[0])
        return m
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    x, y, _z = nb.sep(e)
    ri = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', x, 0.84), nb.math('DIVIDE', y, 0.86), 0.0))
    gold = C.lin(eye_hex)
    iris = nb.ramp(ri, [(0.0, C.lin('#C2561A')), (0.3, C.lin('#D8701E')), (0.46, C.lin('#F0A83A')), (0.62, gold),
                        (0.84, C.lin(C.mix_hex(eye_hex, '#B07818', 0.3))), (0.95, C.lin('#6A4416')),
                        (0.98, C.lin('#140E0C')), (1.5, C.lin('#140E0C'))])
    # radial fibres in the iris
    ang = nb.math('ARCTAN2', y, x)
    fib = nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 38.0)), 0.5)
    fib = nb.math('MULTIPLY', nb.math('ADD', fib, 0.5), nb.math('MULTIPLY', nb.smooth(ri, 0.3, 0.5), nb.smooth(ri, 0.9, 0.75)))
    iris = nb.mix(nb.math('MULTIPLY', fib, 0.18), iris, nb.rgb(C.lin('#FFE9A0')))
    low = nb.math('MULTIPLY', nb.smooth(y, -0.1, -0.7), nb.smooth(ri, 0.92, 0.5))
    iris = nb.mix(nb.math('MULTIPLY', low, 0.45), iris, nb.rgb(C.lin('#FFF0B8')))
    pupil_r = nb.vmath('LENGTH', nb.comb(nb.math('DIVIDE', x, 0.27), nb.math('DIVIDE', nb.math('SUBTRACT', y, 0.02), 0.6), 0.0))
    c = nb.mix(nb.smooth(pupil_r, 1.06, 0.94), iris, nb.rgb(C.lin('#070506')))
    hx = x
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', hx, 0.22), nb.math('DIVIDE', nb.math('SUBTRACT', y, 0.3), 1.15), 0.0)), 0.2, 0.165)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', hx, 0.24), nb.math('ADD', y, 0.3), 0.0)), 0.075, 0.056)
    c = nb.mix(nb.math('MAXIMUM', big, small), c, nb.rgb((1.0, 1.0, 1.0)))
    # the upper lash line: thick over the top, lower and thicker toward the outer corner, a wing (round 2: thicker;
    # the flick carries on onto the face in body_material)
    outer = nb.math('MULTIPLY', nb.smooth(nb.math('MULTIPLY', x, side), 0.15, 0.95), 0.2)
    lash = nb.smooth(nb.math('ADD', y, outer), 0.63, 0.71)
    c = nb.mix(lash, c, nb.rgb(C.lin('#100B0C')))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


# ----------------------------------------------------------------------------- the rig (plans/quadruped.py)
def rig_p() -> dict:
    ed = E_TIP[1] - E_ROOT[1]
    return {
        'hip': (0.0, 0.27, 0.53),
        'chest': (0.0, -0.21, 0.53),
        'head_c': tuple(HEAD_C),
        'head_r': 0.14 * HEAD_K,
        'ear_base': tuple(E_ROOT[1]),
        'ear_dir': tuple(ed.normalized()),
        'ear_len': ed.length,
        'tail_base': TAIL_PTS[0],
        'tail_dir': tuple(norm(v3(TAIL_PTS[1]) - v3(TAIL_PTS[0]))),
        'tail_len': TAIL_LEN,
        'tail_bones': TAIL_BONES,
        'tail_points': [tuple(map(float, TAIL_CURVE[int(round(k * (len(TAIL_CURVE) - 1) / TAIL_BONES))])) for k in range(TAIL_BONES + 1)],
        'legs': {leg: (lx, ly, HIP_Z[leg[0]]) for leg, (lx, ly) in LEGS.items()},
        'knee_back': 0.03,
        'ankle_z': 0.045,
        'foot_len': 0.1,
        'leg_radius': 0.07,
        'stride': 0.2,
        'hocks': hock_shares(),
        # round 3: the card's attack (5-poses 3): a raking forepaw swipe at head height (the shared plan's swipe style).
        # The jaw stays merged into the head: the model has a closed, painted smile and no mouth cavity, so opening the
        # jaw would only stretch the chin
        'strike_style': 'swipe',
        'swipe_lift': -20.0,        # Nov 12: the paw rakes low, so the forearm doesn't sit over the muzzle like a tube
        'jaw_open': True,           # the smiles and the win open the mouth too (the jaw is merged, then given back)
        # Nov 12: the jaw hinges behind the mouth's corners and runs to the chin; the lower jaw's skin rides it
        'jaw': {'head': tuple(map(float, H(MO.HINGE_L))), 'tail': tuple(map(float, H(MO.CHIN_L)))},
    }


def hock_shares() -> dict:
    """The plan's `hocks` from the mesh's hind leg (leg_path): knee, hock and paw as shares of the hip's height."""
    hip, knee, hock, _meta, paw = (v3(p) for p in leg_path('BL'))
    hz = hip[2]
    return {'knee': (float((knee[1] - hip[1]) / hz), float((knee[2] - hz) / hz)),
            'hock': (float((hock[1] - hip[1]) / hz), float((hock[2] - hz) / hz)),
            'paw': (float((paw[1] - hip[1]) / hz), -1.0)}


def tail_bone_names() -> list[str]:
    return [f'tail.{k + 1}' for k in range(TAIL_BONES)]


def ear_weights(p: np.ndarray, u: np.ndarray) -> dict[str, np.ndarray]:
    """Head → ear.1 → ear.2 up the ear (the tuft at the tip rides ear.2)."""
    w2 = smooth(0.45, 0.85, u)
    w1 = (1 - w2) * smooth(0.0, 0.3, u)
    return {'head': 1 - w1 - w2, '1': w1, '2': w2}


def body_weight_regions(co: np.ndarray, names: list[str]):
    out = []
    ear, ear_u = ear_zone(co)
    for s, tag in ((1, 'L'), (-1, 'R')):
        on = ear & (np.sign(co[:, 0]) == s)
        if on.any():
            w = ear_weights(co[on], ear_u[on])
            out.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    z = zones(co)
    zt = z['tail']
    if zt.any():
        pts = rig_p()['tail_points']
        out.append((zt, U.chain_weights(co[zt], pts, tail_bone_names(), 'hips')))
    # Nov 12: the lower jaw (below the cut lips, fading back to the hinge and down into the throat) rides the jaw
    w = MO.jaw_weight(Hinv(co))          # (the chin and the lower jaw lie below the 'head' zone)
    jm = w > 0.004
    if jm.any():
        out.append((jm, {'jaw': w[jm], 'head': 1.0 - w[jm]}))
    return out


CLIP_CALM = {
    '*': {'ear': 0.6, 'tail': 0.85},
    # round 2: the tail curls up in the idles like 1-hero (the plan lifts tail.1..N; this lifts them further)
    'battle_idle': {'ear': 0.6, 'tail': 1.1},     # Nov 13: the tail lower, so its tip stays off the cheek from the front
    'idle_happy': {'ear': 0.6, 'tail': 1.1},
    'idle': {'ear': 0.6, 'tail': 1.0},
    'ko': {'ear': 0.2, 'tail': 0.45},
    'hit_heavy': {'ear': 0.3, 'tail': 0.55},
    'win': {'ear': 0.4, 'tail': 0.6},
    'strike': {'ear': 0.35, 'tail': 0.6},
    'hit': {'ear': 0.4, 'tail': 0.7},
}

FACE_NOTE = ('The eyes are glossy gold lenses (lo_eyes) with the iris, the oval pupil, the catchlights and the upper lash '
             'line baked into the body atlas; the brows, the eye rings, the cheek ember dashes, the nose, the cat smile and '
             'the whisker dots are baked into the body. No face sheet and no morphs: expressions in clips\' `faces` are '
             'hints only. Blinking scales the blink bones (play `blink` over any clip): each lens squashes onto the closed '
             'lid\'s lash line and sinks into the head, showing the closed lid sculpted and painted under it. The embers '
             '(the spine herringbone, the tail end, the ear tufts, the cheek dashes, the claws) are painted in the atlas.'
             ' The mouth opens: the lips are cut along the crease under the whisker pads, the lower jaw rides the jaw bone, and '
             'a mouth prop (palate, tongue, throat and two small fangs, inside the lips) shows when it does.')

REVIEW = {
    'centre': (0.0, 0.17, 0.55),
    'size': 2.05,
    'head': (tuple(map(float, H((0.0, -0.37, 0.88)))), 0.74),
}
