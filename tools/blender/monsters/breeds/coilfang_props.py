"""Coilfang's props (Art 2.1 Ultra): the feathered crest (coilfang_crest.py), the forked tongue that flicks from the mouth
on the jaw's chain tongue.1..2, the two neat white fangs hanging from the upper lip's front (rigid on `head`), and the
mouth's pocket behind the lips (coilfang_mouth.py), all in lo_props (always worn).

Every prop object carries the same attributes (zero where they don't apply), so the joined mesh keeps them: the
crest's fu, fv, fside, fid, fbarb, fpart; the tongue's tg_u, tg_v, tg_top, tpart; the fangs' fang_u, fang; the pocket's
bag, bag_d, bag_floor, bag_a, bag_b, bag_t.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth, v3
from monsters.breeds import coilfang_crest as CR
from monsters.breeds import coilfang_form as F
from monsters.breeds import coilfang_mouth as MO

TONGUE = [(0.0, -0.75, 0.522), (0.0, -0.81, 0.524), (0.0, -0.87, 0.526)]
TONGUE_REACH = 0.15
FORK_AT = 0.64                       # the tines part here (share of the length)
# round 2-3: wide at the root, flattened front to back: a broad triangle from the front, ivory-white; hung from the upper
# lip's front, 7 mm inside its skin, clear in front of the lower jaw (coilfang_form's head)
def _fang_at(s: int) -> tuple:
    x = 0.046
    y_up = min(F._front_y(c, r, x, 0.556) for c, r in F.HEAD_SECTIONS)
    y = y_up + 0.009
    return (x * s, y, 0.562), (0.049 * s, y - 0.004, 0.497)


FANGS = {s: _fang_at(s) for s in (1, -1)}
FANG_R = 0.02
ATTRS = ('fbl', 'fL', 'fu', 'fv', 'fside', 'fid', 'fbarb', 'fpart', 'tg_u', 'tg_v', 'tg_top', 'tpart', 'fang_u', 'fang',
         'bag', 'bag_d', 'bag_floor', 'bag_a', 'bag_b', 'bag_t')


def _complete(ob) -> bpy.types.Object:
    n = len(ob.data.vertices)
    for k in ATTRS:
        if k not in ob.data.attributes:
            S.add_attr(ob, k, np.zeros(n))
    return ob


def loft(name: str, c: np.ndarray, X: np.ndarray, Y: np.ndarray, rx: np.ndarray, ry: np.ndarray, seg: int,
         tip: bool = True) -> tuple[np.ndarray, list]:
    """A closed tube of elliptic rings round the centres (X x Y along the line: the faces wind outward), a fan cap at the
    start and a fan to a point past the end (or a flat cap)."""
    n = len(c)
    a = np.linspace(0.0, 2 * math.pi, seg, endpoint=False)
    ring = c[:, None] + X[:, None] * (rx[:, None] * np.cos(a)[None])[..., None] + Y[:, None] * (ry[:, None] * np.sin(a)[None])[..., None]
    verts = list(ring.reshape(-1, 3))
    faces = []
    for i in range(n - 1):
        for j in range(seg):
            jn = (j + 1) % seg
            faces.append((i * seg + j, i * seg + jn, (i + 1) * seg + jn, (i + 1) * seg + j))
    c0 = len(verts)
    verts.append(c[0])
    for j in range(seg):
        faces.append((c0, (j + 1) % seg, j))
    c1 = len(verts)
    d = c[-1] - c[-2]
    verts.append(c[-1] + (d / max(np.linalg.norm(d), 1e-9) * 0.6 * max(rx[-1], ry[-1]) if tip else 0.0))
    for j in range(seg):
        faces.append((c1, (n - 1) * seg + j, (n - 1) * seg + (j + 1) % seg))
    return np.array(verts), faces


def _frames(c: np.ndarray, up) -> tuple[np.ndarray, np.ndarray]:
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    Y = np.broadcast_to(v3(up), c.shape) - T * (T @ v3(up))[:, None]
    Y /= np.linalg.norm(Y, axis=1, keepdims=True)
    X = np.cross(Y, T)
    return X, Y


def _mesh(name: str, verts: np.ndarray, faces: list) -> bpy.types.Object:
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.asarray(verts).tolist(), [], faces)
    me.update()
    me.validate(verbose=False)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    return ob


# ============================================================================= the forked tongue
def _polyline(pts: np.ndarray, u: np.ndarray) -> np.ndarray:
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    return np.stack([np.interp(u, cum, pts[:, k]) for k in range(3)], axis=1)


def tongue(high: bool) -> bpy.types.Object:
    """A slim, flattened tongue lying on the mouth's floor (hidden at rest), splitting into two pointed tines over its
    last third (4-details: 'a forked tongue'; the hero's open smile)."""
    pts = v3(TONGUE).reshape(-1, 3)
    L = float(np.linalg.norm(pts[-1] - pts[0]))
    nu, seg = (40, 16) if high else (9, 8)
    u = np.linspace(0.0, FORK_AT + 0.06, nu)
    c = _polyline(pts, u)
    X, Y = _frames(c, (0, 0, 1))
    w = 0.0062 - 0.0014 * smooth(0.0, FORK_AT, u)
    t = 0.0032 - 0.0006 * smooth(0.0, FORK_AT, u)
    verts, faces = loft('t', c, X, Y, w, t, seg, tip=False)
    parts = [(verts, faces, np.interp(np.linalg.norm(verts - pts[0], axis=1) / L, [0, 1], [0, 1]))]
    d = (pts[-1] - pts[0]) / L
    side = np.cross(d, np.array((0.0, 0.0, 1.0)))
    for s in (1, -1):
        ut = np.linspace(FORK_AT - 0.04, 1.0, 12 if high else 5)
        base = _polyline(pts, np.clip(ut, 0, 1))
        spread = (smooth(FORK_AT - 0.04, 1.0, ut) ** 0.8 * 0.022 * s)[:, None] * side[None]
        cc = base + spread + d[None] * (np.clip(ut - 1.0, 0, None) * L)[:, None]
        Xt, Yt = _frames(cc, (0, 0, 1))
        wt = 0.0026 * (1.0 - smooth(FORK_AT, 1.0, ut) ** 1.4) + 0.0004
        tt = 0.0018 * (1.0 - smooth(FORK_AT, 1.0, ut) ** 1.4) + 0.0003
        v2, f2 = loft('tine', cc, Xt, Yt, wt, tt, 8 if high else 6)
        parts.append((v2, f2, np.clip(np.interp(np.linalg.norm(v2 - pts[0], axis=1) / L, [0, 1], [0, 1]), 0, 1)))
    vs, fs, us, off = [], [], [], 0
    for v, f, uu in parts:
        vs.append(v)
        fs += [tuple(q + off for q in face) for face in f]
        us.append(uu)
        off += len(v)
    ob = _mesh(f'{"hi" if high else "lo"}_tongue', np.vstack(vs), fs)
    co, _ = S.mesh_arrays(ob)
    uu = np.clip(U_along(co), 0.0, 1.0)
    rel = co - _polyline(pts, uu)
    S.add_attr(ob, 'tg_u', uu)
    S.add_attr(ob, 'tg_v', np.clip(rel[:, 0] / 0.006, -1.0, 1.0))
    S.add_attr(ob, 'tg_top', smooth(-0.001, 0.002, rel[:, 2]))
    S.add_attr(ob, 'tpart', np.ones(len(co)))
    ob['prop'] = 'tongue'
    return _complete(ob)


def U_along(co: np.ndarray) -> np.ndarray:
    pts = v3(TONGUE).reshape(-1, 3)
    d = pts[-1] - pts[0]
    return ((co - pts[0]) @ d) / float(d @ d)


# ============================================================================= the fangs
def fangs(high: bool) -> list[bpy.types.Object]:
    """Two neat white fangs hanging from the upper lip's front, curving a touch back (3-faces, 4-details panel 1)."""
    out = []
    for s in (1, -1):
        a, b = (v3(p) for p in FANGS[s])
        u = np.linspace(0.0, 1.0, 16 if high else 6)
        c = a[None] + (b - a)[None] * u[:, None] + np.array((0.0, 0.006, 0.0))[None] * (np.sin(np.pi * u) * 0.0 + u ** 2)[:, None]
        X, Y = _frames(c, (0, -1, 0))
        r = FANG_R * (1.0 - u ** 1.05) + 0.0006
        v, f = loft('fang', c, X, Y, r, r * 0.5, 14 if high else 8)
        ob = _mesh(f'{"hi" if high else "lo"}_fang{"L" if s > 0 else "R"}', v, f)
        co, _ = S.mesh_arrays(ob)
        d = b - a
        S.add_attr(ob, 'fang_u', np.clip(((co - a) @ d) / float(d @ d), 0.0, 1.0))
        S.add_attr(ob, 'fang', np.ones(len(co)))
        ob['prop'] = 'fangs'
        out.append(_complete(ob))
    return out


# ============================================================================= all of them
def build(high: bool, quick: bool) -> list[bpy.types.Object]:
    out = [_complete(CR.build(high)), tongue(high)] + fangs(high)
    lo = bpy.data.objects.get('lo_body')
    if lo is not None:
        if 'jside' not in lo.data.attributes:
            # the game mesh is final here (after its decimation): cut its mouth, then grow the pocket from the cut
            MO.cut_mouth(lo)
        out.append(_complete(MO.pocket(high)))
    return out
