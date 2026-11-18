"""Aurelwyrm's crimson ribbon fins (Art 2.1 Ultra): silky membranes (lo_fins: the game's fin material is two-sided and
glows a little with its own colour) that run along its back and sides and trail behind like silk (the card; 1-hero,
2-turnaround, 4-details panel 3, 5-poses).

Round 2 (the reviewer: about 40 short wide blades fanned every way, a red chrysanthemum hiding the gold body): far
fewer, long, narrow ribbons that run along the body and sweep back, overlapping, each ending in a long thin tip that
curls up and away; the gold S stays visible between the runs.
  - the dorsal run: five ribbons along the spine, each lying on the back for half its length (its root edge buried in
    the skin, so it follows every bend), then lifting off and curling (chains dorsal1..5);
  - the flank runs: two long ribbons on each lower side, hanging and trailing back (chains flankL1, flankL2, flankR1,
    flankR2);
  - the mane's flame locks: a ring round the back of the head behind the gold ruff, curling at their tips, and a few
    streaming back from the back of the neck (no chains: the head and the neck carry them);
  - the tail's fan: four long ribbons from the tail's tip, curling up and back (chain tailfin).

Each ribbon is a sheet lofted along a curving centre line: narrow at its root, widest early, then a long thin tip. The
high sheets carry fine vein lines along their length for the normal map; the paint (aurelwyrm_paint.py) lays the veins
and the lighter edge.

Attributes on every ribbon point: rib_u (0 root -> 1 tip), rib_v (-1..1 across), rib_id (0..1), rib_kind (0 head mane,
1 dorsal, 2 flank, 4 tail fan, 5 neck mane), rib_su (the place along the body whose spine weights it takes; < 0 = the
head), rib_chain (the chain's index in CHAINS, or -1), rib_side; fin_part and fan (zeros).
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import smooth
from monsters.breeds import aurelwyrm_form as F

TRAIL = 0.85               # a free ribbon point's distance back of its root that moves its place along the body
CHAIN_AT = (0.45, 0.72, 1.0)   # a hugging ribbon's chain points (shares of its length): it lifts off the body at 0.45


def _rot(v: np.ndarray, axis: np.ndarray, ang: float) -> np.ndarray:
    axis = F.unit(axis)
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * float(axis @ v) * (1 - math.cos(ang))


def _frame(s: np.ndarray):
    """(points, T, D, L, radius) at the body positions s (past the tail's tip: along its last direction)."""
    s = np.asarray(s, float)
    sc = np.clip(s, 0.0, F.S_TOT)
    p = F.point_at(sc)
    idx = np.clip(np.searchsorted(F.CUM, sc), 0, len(F.CUM) - 1)
    T, D, L = F.TAN[idx], F.DORSAL[idx], F.LEFT[idx]
    p = p + T * np.maximum(s - F.S_TOT, 0.0)[:, None]
    return p, T, D, L, F.radius(sc)


# ============================================================================= the layout
def _spec() -> list[dict]:
    rng = np.random.default_rng(61)
    out = []

    def free(kind, s_root, root, d, across, L, W, bend, side=0.0, swing=None, curl=0.0):
        out.append({'kind': kind, 'hug': False, 's': float(s_root), 'root': np.asarray(root, float), 'dir': F.unit(d),
                    'across': F.unit(across), 'L': float(L), 'W': float(W), 'bend': np.asarray(bend, float),
                    'side': float(side), 'twist': rng.choice([-1.0, 1.0]) * rng.uniform(0.55, 0.9), 'hook': rng.choice([-1.0, 1.0]) * rng.uniform(0.1, 0.22),
                    'swing': (rng.uniform(0.04, 0.08) if swing is None else swing) * rng.choice([-1.0, 1.0]),
                    'sc': rng.uniform(1.1, 1.6), 'wave': rng.uniform(0.006, 0.012), 'cyc': rng.uniform(1.2, 2.0),
                    'ph': rng.uniform(0, 2 * math.pi), 'curl': float(curl), 'chain': -1, 'seed': int(rng.integers(1 << 30))})

    def hug(kind, s_root, phi, L, W, rise, curl, lean, side, chain):
        out.append({'kind': kind, 'hug': True, 's': float(s_root), 'phi': float(phi), 'L': float(L), 'W': float(W),
                    'rise': float(rise), 'curl': float(curl), 'lean': float(lean), 'side': float(side),
                    'swing': rng.uniform(0.03, 0.05) * rng.choice([-1.0, 1.0]), 'twist': rng.choice([-1.0, 1.0]) * rng.uniform(0.35, 0.6),
                    'hook': rng.choice([-1.0, 1.0]) * rng.uniform(0.1, 0.2), 'wave': rng.uniform(0.004, 0.008),
                    'cyc': rng.uniform(1.5, 2.5), 'ph': rng.uniform(0, 2 * math.pi), 'chain': chain,
                    'seed': int(rng.integers(1 << 30))})

    # 0: the mane's flame locks round the back of the head (a halo behind the gold ruff), swept back, curling tips
    hc = np.array((0.0, -0.99, 1.25 + F.HDZ))
    for a in np.linspace(-150.0, 150.0, 17):
        ar = math.radians(a + rng.uniform(-4, 4))
        rad = np.array((math.sin(ar), 0.0, math.cos(ar)))
        root = hc + rad * np.array((0.1, 0.0, 0.105)) + np.array((0.0, rng.uniform(-0.02, 0.02), 0.0))
        side = smooth(20.0, 90.0, abs(a))
        d = rad * 0.5 + np.array((0.0, 1.15 + 0.2 * (1 - side), 0.0)) + np.array((0.0, 0.0, 0.1))     # (round 3) streaming back
        across = np.cross(np.array((0.0, 1.0, 0.0)), rad)
        L = (0.32 + 0.12 * side - 0.08 * smooth(110.0, 150.0, abs(a))) * (1.0 + 0.12 * rng.uniform(-1, 1))
        free(0, -0.04, root, d, across, L, L * 0.24, rad * 0.04 + np.array((0.0, 0.04, 0.0)), side=float(np.sign(a)) * side,
             swing=rng.uniform(0.05, 0.09), curl=0.1)
    # 5: a few streaming back from the back of the neck
    # (round 3: two, lying back down the neck: one stood straight up beside the head in the front views)
    for s_, ph in ((0.26, -0.45), (0.5, 0.45)):
        p, T, D, Lf, r = (q[0] for q in _frame(np.array([s_])))
        rad = D * math.cos(ph) + Lf * math.sin(ph)
        d = T * 0.95 + D * 0.2 + Lf * (0.12 * math.copysign(1, ph))
        tilt = D + Lf * (0.85 * math.copysign(1, ph))
        across = tilt - F.unit(d) * float(tilt @ F.unit(d))
        L = (0.5 - 0.06 * s_ / F.S_NECK) * (1.0 + 0.1 * rng.uniform(-1, 1))
        free(5, s_, p + rad * r * 0.85, d, across, L, L * 0.18, D * 0.03, side=math.copysign(1, ph), curl=0.12)
    # 1: the dorsal run: five long ribbons, each half its length on the spine, overlapping the next
    ch = 0
    for k, s_ in enumerate(np.linspace(F.S_NECK + 0.04, 0.74 * F.S_TOT, 5)):
        lean = (1 if k % 2 else -1) * math.radians(28 + rng.uniform(-4, 4))     # (polish: 16 left them edge-on at the hump)
        L = (1.05 - 0.15 * k / 4) * (1.0 + 0.05 * rng.uniform(-1, 1))
        hug(1, s_, 0.0, L, 0.085, 0.17, 0.2, lean, math.copysign(1, lean), ch)
        ch += 1
    # 2: the flank runs: two long ribbons on each lower side, hanging and trailing back
    for sd in (1, -1):
        for k, s_ in enumerate((F.S_NECK + 0.22, F.S_NECK + 1.15)):
            L = (1.15 - 0.1 * k) * (1.0 + 0.05 * rng.uniform(-1, 1))
            # rooted on the lower flank and leaning down: a hanging sail from the side (level, it was edge-on there)
            hug(2, s_ + rng.uniform(-0.04, 0.04), sd * 1.35, L, 0.08, 0.18, 0.18, -0.75 * sd, sd, ch)
            ch += 1
    # 4: the tail's fan (round 3: five upright blades read as a tulip): five long ribbons from the tail's last eighth,
    # within about 10 degrees of the tail's line, spread back and a little apart, each tilted 35 degrees off level so
    # none is edge-on, the tips curling up and back (1-hero)
    # (polish: the roots spread over the last 15% of the tail, deep inside it and narrow, so no hub knot shows; none
    # stands up)
    for i, ph in enumerate((0.3, 0.8, -0.6, 1.25, -1.2)):
        s_ = F.S_TOT * (0.85 + 0.03 * i)
        p, T, D, Lf, r = (q[0] for q in _frame(np.array([s_])))
        rad = D * math.cos(ph) + Lf * math.sin(ph)
        d = T * 0.98 + rad * 0.07 + Lf * (0.08 * math.sin(ph))
        tilt = math.radians(35.0) * (1 if i % 2 else -1)
        across = Lf * math.cos(tilt) + D * math.sin(tilt)
        L = (0.92 + 0.12 * (i % 2)) * (1.0 + 0.06 * rng.uniform(-1, 1))
        free(4, s_, p + rad * r * 0.25, d, across, L, L * 0.11, D * 0.04, side=float(np.sign(math.sin(ph))), curl=0.1)
    return out


SPEC = _spec()


def _hug_centre(f: dict, u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A hugging ribbon's centre line and its across direction: on the body's surface at angle phi (leaned), rising off
    it toward the tip, the last part curling up and away."""
    uu = np.clip(u, 0.0, 1.0)
    s = f['s'] + u * f['L']
    p, T, D, L, r = _frame(s)
    phi = f['phi']
    rad = D * math.cos(phi) + L * math.sin(phi)
    if f['lean']:
        c_, s_ = math.cos(f['lean']), math.sin(f['lean'])
        rad = rad * c_ + np.cross(T, rad) * s_
    rise = f['rise'] * uu ** 1.6
    side = np.cross(T, rad)
    # (polish) the tip curls sideways, square to the ribbon's width: curling it up into its own width (along rad)
    # collapsed the tips into needles and upright spikes
    hook = math.copysign(1.0, f['swing']) * f['curl'] * smooth(0.7, 1.0, uu) ** 2
    swing = side * (f['swing'] * f['L'] * np.sin(np.pi * 1.3 * uu) * uu + hook)[:, None]
    # a little lift toward the tail's direction at the tip too: the curl sweeps back as well as up
    c = p + rad * (r * 0.9 + rise)[:, None] + swing
    return c, rad


def _free_centre(f: dict, u: np.ndarray) -> np.ndarray:
    uu = np.clip(u, 0.0, None)
    swing = f['across'][None] * (f['swing'] * f['L'] * np.sin(np.pi * f['sc'] * uu) * smooth(0.0, 0.35, uu))[:, None]
    # (polish) the tip curls out of the sheet's plane (into its width it thinned to a needle)
    nrm = F.unit(np.cross(f['dir'], f['across']))
    curl = nrm[None] * (f['curl'] * f['L'] * smooth(0.7, 1.0, np.clip(uu, 0, 1)) ** 2)[:, None]
    return f['root'][None] + f['dir'][None] * (f['L'] * u)[:, None] + f['bend'][None] * (f['L'] * uu ** 2)[:, None] * 3.0 + swing + curl


def _width(u: np.ndarray) -> np.ndarray:
    """The outline (share of the half width): a narrow root, widest early, a long taper that keeps about a third of
    the width, then a rounded tip (round 3: they thinned to hair-like needles)."""
    u = np.clip(u, 0.0, 1.0)
    body = (0.5 + 0.5 * smooth(0.0, 0.18, u)) * (0.32 + 0.68 * np.clip(1.0 - smooth(0.35, 0.9, u), 0.0, 1.0) ** 0.85)
    return body * np.sqrt(np.clip(1.0 - smooth(0.86, 1.0, u) ** 2, 0.0, 1.0))


def chain_points(f: dict) -> list[tuple[float, float, float]]:
    u = np.array(CHAIN_AT)
    c, rad = _hug_centre(f, u)
    w = _width(u)
    c = c + rad * (0.85 * np.maximum(f['W'] * w, 0.003))[:, None]
    return [tuple(float(x) for x in q) for q in c]


def chain_parent(f: dict) -> str:
    """The spine bone under the ribbon where it lifts off (its chain hangs from it)."""
    s = f['s'] + CHAIN_AT[0] * f['L']
    k = int(np.clip(np.searchsorted(F.SPINE_S, s, side='right') - 1, 0, len(F.SPINE_S) - 2))
    names = [f'neck.{F.NECK_BONES - i}' for i in range(F.NECK_BONES)] + ['hips'] + [f'tail.{i + 1}' for i in range(F.TAIL_BONES)]
    return names[k]


def chains() -> list[dict]:
    """The rig's ribbon chains (2 bones each), in rib_chain order."""
    out = []
    for f in SPEC:
        if f['chain'] < 0:
            continue
        nm = f'dorsal{f["chain"] + 1}' if f['kind'] == 1 else f'flank{"L" if f["side"] > 0 else "R"}{1 + int(f["s"] > F.S_NECK + 0.6)}'
        out.append({'name': nm, 'kind': 'ribbon', 'parent': chain_parent(f), 'points': chain_points(f), 'index': f['chain']})
    return sorted(out, key=lambda m: m['index'])


def tailfin_points() -> list[np.ndarray]:
    p, T, D, Lf, r = (q[0] for q in _frame(np.array([F.S_TOT - 0.005])))
    return [p + T * (0.22 * k) for k in range(4)]


# ============================================================================= the sheets
def ribbon(f: dict, rid: int, high: bool, quick: bool) -> tuple[np.ndarray, list, dict]:
    long_ = f['kind'] in (1, 2)
    if high:
        nu, nv = ((50, 10) if quick else ((110, 22) if long_ else (80, 18)))
    else:
        nu, nv = (26, 3) if long_ else ((18, 4) if f['kind'] in (0, 5) else (22, 3))
    u = np.concatenate([[-0.04], np.linspace(0.0, 1.0, nu)])
    v = np.linspace(-1.0, 1.0, 2 * nv + 1)
    if f['hug']:
        c, across = _hug_centre(f, u)
    else:
        c = _free_centre(f, u)
        across = np.broadcast_to(f['across'], c.shape)
    T = np.gradient(c, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    X = across - T * (T * across).sum(axis=1, keepdims=True)
    X /= np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-9)
    N0 = np.cross(T, X)
    tw = f['twist'] * np.clip(u, 0.0, 1.0) ** 1.4
    X = X * np.cos(tw)[:, None] + N0 * np.sin(tw)[:, None]
    N = np.cross(T, X)
    # the outline: a narrow root, widest early, then a long taper to a thin tip hooked a little to one side
    uc = np.clip(u, 0.0, 1.0)
    w = _width(uc)
    halfw = np.maximum(f['W'] * w, 0.003)               # W is the half width
    if f['kind'] == 4:
        # (polish) the fan's roots start narrow inside the thin tail (full width at their root stuck out as a hub)
        halfw = halfw * (0.15 + 0.85 * smooth(-0.04, 0.3, uc))
    if f['hug']:
        # the inner edge just inside the skin, the ribbon standing out from it its whole width
        c = c + across * (0.85 * halfw)[:, None]
    shift = f['hook'] * f['W'] * smooth(0.5, 1.0, uc) ** 1.6
    U, V = np.meshgrid(u, v, indexing='ij')
    pos = c[:, None] + X[:, None] * (V * halfw[:, None] + shift[:, None])[..., None]
    amp = f['wave'] * smooth(0.0, 0.5, np.clip(U, 0, 1)) * (f['L'] / 0.5)
    rip = amp * np.sin(2 * math.pi * (f['cyc'] * U) + f['ph']) + 0.003 * np.sin(math.pi * V * 1.5 + f['ph']) * smooth(0.1, 0.6, np.clip(U, 0, 1))
    if high:
        # fine parallel veins along the length (the normal map's silk) and a slightly raised edge
        rng = np.random.default_rng(f['seed'])
        rip = rip + 0.00025 * np.sin(math.pi * 9.0 * V + rng.uniform(0, 6)) * smooth(0.02, 0.15, np.clip(U, 0, 1)) \
            + 0.0004 * smooth(0.85, 1.0, np.abs(V))
    pos = pos + N[:, None] * rip[..., None]
    verts = pos.reshape(-1, 3)
    m = len(v)
    faces = []
    for i in range(len(u) - 1):
        for j in range(m - 1):
            faces.append((i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j))
    n = len(verts)
    if f['hug']:
        su = np.repeat(f['s'] + np.clip(u, -0.04, 1.0) * f['L'], m)
    elif f['s'] < 0:
        su = np.full(n, -1.0)
    else:
        T0 = _frame(np.array([f['s']]))[1][0]
        su = f['s'] + TRAIL * np.maximum((verts - f['root'][None]) @ T0, 0.0)
    attrs = {'rib_u': np.clip(U.reshape(-1), 0.0, 1.0), 'rib_v': V.reshape(-1), 'rib_id': np.full(n, (rid * 0.618) % 1.0),
             'rib_kind': np.full(n, float(f['kind'])), 'rib_su': su, 'rib_chain': np.full(n, float(f['chain'])),
             'rib_side': np.full(n, f['side'])}
    return verts, faces, attrs


def build_fins(high: bool, quick: bool) -> list[bpy.types.Object]:
    vs, fs, at = [], [], {}
    off = 0
    for i, f in enumerate(SPEC):
        v, fc, a = ribbon(f, i, high, quick)
        vs.append(v)
        fs += [tuple(q + off for q in face) for face in fc]
        for k, val in a.items():
            at.setdefault(k, []).append(val)
        off += len(v)
    name = f'{"hi" if high else "lo"}_ribbons'
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.vstack(vs).tolist(), [], fs)
    me.update()
    me.validate(verbose=False)
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    for k, val in at.items():
        S.add_attr(ob, k, np.concatenate(val).astype(np.float64))
    n = len(ob.data.vertices)
    S.add_attr(ob, 'fan', np.zeros((n, 3)))
    S.add_attr(ob, 'fin_part', np.zeros(n))
    if 'UVMap' not in ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    if not high:
        # (round 3) the head's flame locks smeared in the atlas: twice the texel density on them
        kind = np.concatenate(at['rib_kind'])
        fk = np.array([kind[f[0]] for f in fs])
        a = me.attributes.new('texel_k', 'FLOAT', 'FACE')
        a.data.foreach_set('value', np.where(fk == 0, 2.0, 1.0).astype(np.float32))
    C.log(f'{name}: {len(fs)} faces in {len(SPEC)} ribbons')
    return [ob]
