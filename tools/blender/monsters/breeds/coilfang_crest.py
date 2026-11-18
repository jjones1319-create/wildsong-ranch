"""Coilfang's feathered golden crest (Art 2.1 Ultra): a dense mohawk tuft of narrow feathers rooted in a strip along the
top of the head's midline, from just above and between the eyes back to the nape, rising and sweeping up and back,
fanning out to the sides (1-hero, 2-turnaround front, side and top, 3-faces, 4-details panels 1 and 5).

Round 2 (the reviewer: broad torn-paper leaves fanned round the whole back of the head read as a halo and a crown):
  - each feather is narrow (about 4 to 1 long to wide), widest a little before its middle, tapering to a soft curved point
    that curls back, with no torn notches and no bare shaft at the tip;
  - a closed shell lofted along its curving shaft: a lens-shaped section, the raised shaft down its middle;
  - the barbs are painted per pixel (coilfang_paint.prop_material) from `fbl`: fine parallel lines about 30 degrees off
    the shaft. As geometry, 5 mm barbs aliased into a dot grid in the shipped 1024 px normal map.

Attributes on every crest point: fbl (the barb count across the vane), fL (the feather's length), fu (0 root -> 1 tip),
fv (-1..1 across the vane, 0 on the shaft), fside (-1 the monster's right .. +1 its left: which crest chain), fid (the
feather's number), fbarb 0, fpart 1.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import coilfang_form as F

# the root strip along the midline (y from the brow to the nape), its height on the skull, the feathers' lean back from
# vertical there, their length; at each station a centre feather and pairs splayed out to the sides
STATIONS = [
    # (y, z, lean back, length, splays: degrees out to each side, (+ the left, - the right))
    # round 3: no splay past 62 degrees (short feathers pointed down onto the skull); the back rows lie back and down
    # over the nape like a mane (2-turnaround top, the variant's back view), not a crown from behind
    (-0.712, 0.744, 16.0, 0.25, (-58.0, -38.0, -19.0, 0.0, 19.0, 38.0, 58.0)),
    (-0.69, 0.742, 26.0, 0.31, (-62.0, -42.0, -22.0, -7.0, 7.0, 22.0, 42.0, 62.0)),
    (-0.662, 0.728, 38.0, 0.33, (-55.0, -34.0, -14.0, 0.0, 14.0, 34.0, 55.0)),
    (-0.635, 0.715, 52.0, 0.33, (-48.0, -28.0, -9.0, 9.0, 28.0, 48.0)),
    (-0.608, 0.69, 68.0, 0.32, (-36.0, -17.0, 0.0, 17.0, 36.0)),
    (-0.582, 0.665, 84.0, 0.31, (-26.0, -9.0, 9.0, 26.0)),
    (-0.56, 0.635, 98.0, 0.28, (-18.0, 0.0, 18.0)),
]
ASPECT = 7.4            # length / the vane's half width (about 4 to 1 long to wide at the widest)
BURY = 0.06             # each shaft starts this share of its length under the skin
BARB = 0.0065           # the barbs' spacing along the shaft (metres)
SLANT = 0.0             # filled per feather: a barb reaches the edge this share of the length past its root (30 degrees)


def feathers() -> list[dict]:
    out = []
    rng = np.random.default_rng(23)
    for si, (y, z, lean, L0, splays) in enumerate(STATIONS):
        for sp in splays:
            k = abs(sp) / 60.0
            spr = math.radians(sp + rng.uniform(-5, 5))
            lr = math.radians(lean + 8.0 * k + rng.uniform(-4, 4))
            # up, leaning back, splayed out round the head's long axis
            d = F.unit(np.array((math.sin(spr) * math.cos(lr), math.sin(lr), math.cos(spr) * math.cos(lr))))
            root = np.array((0.055 * math.sin(spr), y + rng.uniform(-0.006, 0.006), z - 0.03 * k ** 1.5))
            # the vane faces the sides (a full plume from the side), turned toward the front the more it splays
            side = F.unit(np.cross(d, np.array((0.0, 1.0, 0.0))))
            fwd = F.unit(np.cross(side, d))
            roll = math.radians(25.0 * (1 if (len(out) % 2) else -1) + 40.0 * k * np.sign(sp) + rng.uniform(-12, 12))
            across = F.unit(fwd * math.cos(roll) + side * math.sin(roll))
            L = L0 * (1.0 - 0.14 * k ** 1.3) * (1.0 + 0.06 * rng.uniform(-1, 1))
            # each tip curls back and a little further out, like a soft plume
            bend = F.unit(np.array((0.0, 1.0, -0.15)) - d * d[1] + 0.4 * np.array((math.sin(spr), 0.0, 0.0))) * (0.26 + 0.06 * rng.uniform(-1, 1))
            # round 3: each feather curves along its length out of its own plane too, and twists a little toward its
            # tip, so no feather is ever seen edge-on as a straight stick
            nrm = F.unit(np.cross(d, across))
            sg = 1.0 if (len(out) % 2) else -1.0
            bend = bend + nrm * (0.11 * sg) + across * (0.05 * rng.uniform(-1, 1))
            out.append({'root': root, 'dir': d, 'across': across, 'L': L, 'W': L / ASPECT * (1.0 + 0.08 * rng.uniform(-1, 1)),
                        'bend': bend, 'twist': math.radians(sg * rng.uniform(18, 34)),
                        'side': float(np.clip(sp / 45.0, -1.0, 1.0)), 'row': si, 'seed': int(rng.integers(1 << 30))})
    return out


def _shaft(f: dict, u: np.ndarray) -> np.ndarray:
    uu = np.clip(u, 0.0, None)
    return f['root'][None] + f['dir'][None] * (f['L'] * u)[:, None] + f['bend'][None] * (f['L'] * uu ** 2)[:, None]


def _width(u: np.ndarray) -> np.ndarray:
    """The vane's half width (share of W) along the shaft: a narrow downy base, widest at 0.4, a soft curved point."""
    base = 0.36 + 0.64 * smooth(0.0, 0.28, u)
    tip = np.sqrt(np.clip(1.0 - smooth(0.52, 1.0, u) ** 2.2, 0.0, 1.0))
    return np.maximum(base * tip, 0.03)


def slant(f: dict) -> float:
    """How far (share of the length) a barb runs toward the tip from the shaft to the edge: 30 degrees off the shaft."""
    return f['W'] / math.tan(math.radians(30.0)) / f['L']


def barb_line(f: dict, U: np.ndarray, V: np.ndarray) -> np.ndarray:
    """Which barb a point of the vane is on (a continuous count: whole numbers on the barbs)."""
    return (U - slant(f) * np.abs(V)) * f['L'] / BARB


def feather_mesh(f: dict, fid: int, high: bool) -> tuple[np.ndarray, list, dict]:
    nu, nv = (130, 12) if high else (20, 2)
    u = np.concatenate([np.linspace(-BURY, 0.0, 3 if high else 2, endpoint=False), np.linspace(0.0, 0.97, nu)])
    v = np.linspace(-1.0, 1.0, 2 * nv + 1)
    c = _shaft(f, u)
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    X = f['across'][None] - T * (T @ f['across'])[:, None]
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    N0 = np.cross(T, X)
    # the twist toward the tip
    tw = f.get('twist', 0.0) * np.clip(u, 0.0, 1.0)
    X = X * np.cos(tw)[:, None] + N0 * np.sin(tw)[:, None]
    N = np.cross(T, X)
    U, V = np.meshgrid(u, v, indexing='ij')
    # a few soft notches split the vane's edge along the barbs (4-details panel 5)
    pull = np.zeros_like(U)
    rng = np.random.default_rng(f['seed'])
    for side in (1, -1):
        for at in np.sort(rng.uniform(0.38, 0.86, int(rng.integers(1, 3)))):
            line = U - slant(f) * np.abs(V)
            pull = np.maximum(pull, rng.uniform(0.08, 0.14) * np.exp(-((line - at) / 0.045) ** 2) * smooth(0.5, 0.98, np.abs(V)) * ((V * side) > 0))
    halfw = (f['W'] * _width(u))[:, None] * (1.0 - pull)
    # the section: a lens, the shaft a raised ridge down its middle, the vane cupped a little and curling at its edges
    t_vane = 0.0014 * (1.0 - 0.5 * smooth(0.5, 1.0, U))
    t_shaft = (0.0018 - 0.0012 * smooth(0.0, 1.0, U)) * np.exp(-(V * halfw / 0.004) ** 2)
    thick = t_vane * np.sqrt(np.clip(1.0 - V ** 2, 0.0, 1.0)) + t_shaft
    cup = 0.24 * f['W'] * (1.0 - np.sqrt(np.clip(1.0 - V ** 2, 0, 1))) * smooth(-0.05, 0.3, U)
    rings = []
    for i in range(len(u)):
        base = c[i][None] + X[i][None] * (V[i] * halfw[i])[:, None] - N[i][None] * cup[i][:, None]
        top = base + N[i][None] * thick[i][:, None]
        bot = base - N[i][None] * (thick[i] * 0.85)[:, None]
        rings.append(np.vstack([top, bot[-2:0:-1]]))
    m = len(rings[0])
    verts = np.vstack(rings)
    # (X, N, T) right-handed, each ring over the top from -X to +X and back underneath: these windings face out
    faces = []
    for i in range(len(rings) - 1):
        for j in range(m):
            j1 = (j + 1) % m
            faces.append((i * m + j, (i + 1) * m + j, (i + 1) * m + j1, i * m + j1))
    c0 = len(verts)
    verts = np.vstack([verts, c[0][None], _shaft(f, np.array([1.0]))])
    last = (len(rings) - 1) * m
    for j in range(m):
        faces.append((c0, j, (j + 1) % m))
        faces.append((c0 + 1, last + (j + 1) % m, last + j))
    vv = np.concatenate([v, v[-2:0:-1]])
    fu = np.concatenate([np.repeat(u, m), [u[0], 1.0]])
    fv = np.concatenate([np.tile(vv, len(u)), [0.0, 0.0]])
    n = len(verts)
    attrs = {'fbl': barb_line(f, fu, fv), 'fL': np.full(n, f['L']), 'fu': np.clip(fu, 0.0, 1.0), 'fv': fv,
             'fside': np.full(n, f['side']), 'fid': np.full(n, float(fid)), 'fbarb': np.zeros(n), 'fpart': np.ones(n)}
    return verts, faces, attrs


def build(high: bool) -> bpy.types.Object:
    """The whole crest as one object (`hi_crest` / `lo_crest`)."""
    vs, fs, at = [], [], {}
    off = 0
    fl = feathers()
    for i, f in enumerate(fl):
        v, fc, a = feather_mesh(f, i, high)
        vs.append(v)
        fs += [tuple(q + off for q in face) for face in fc]
        for k, val in a.items():
            at.setdefault(k, []).append(val)
        off += len(v)
    name = f'{"hi" if high else "lo"}_crest'
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.vstack(vs).tolist(), [], fs)
    me.update()
    me.validate(verbose=False)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    for k, val in at.items():
        S.add_attr(ob, k, np.concatenate(val).astype(np.float64))
    ob['prop'] = 'crest'
    C.log(f'{name}: {len(fs)} faces in {len(fl)} feathers')
    return ob


def crest_top() -> float:
    return float(max(_shaft(f, np.linspace(0, 1, 30))[:, 2].max() for f in feathers()))
