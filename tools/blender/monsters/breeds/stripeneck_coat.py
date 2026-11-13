"""Stripeneck Ultra: the coat's pattern (numpy, per point; the shape preview and the build's paint share it).

From chatgpt/monsters/31-stripeneck/ (1-hero, 2-turnaround, 4-details panels 4 and 6):
  - giraffe at the front: golden tan with rounded chestnut patches, each outlined by a thin cream line (a Voronoi set
    of patches over the head, neck, chest, shoulders and front legs: big on the neck and shoulders, small on the face
    and toward the hooves; the corners rounded, every edge warped a little so they read as organic shapes);
  - zebra at the back: cream with bold charcoal stripes that curve round the body (arcs round a focus under the flank:
    opening toward the stifle on the haunches, long diagonals over the barrel, bands across the rump; horizontal rings
    down the back legs) and rings down the tail;
  - the blend: a soft wavy band round the middle of the body (further forward along the top of the back) where the
    patches stretch out along the stripes, the tan turns cream, and the stripes start thin and chestnut and grow bold
    and charcoal;
  - the mane's bands (one tuft per band, charcoal and cream alternating), the tufted ossicones, the tail's tuft.

Everything is evaluated at each point's own position (a lock takes the pattern where it lies), so the pattern stays
crisp over the short velvet locks. Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import numpy as np

from lib.surface import smooth, v3

# the stripes: rings round an axis through both hips, this far apart
# round 6: arcs round a point in the side view (x ignored) in the open gap under the flank, in front of the hind legs: the
# arcs open toward the stifle on the haunches, sweep as long diagonals over the barrel and run across the rump; the
# focus never touches the body (round 4's point by the stifle and round 5's hip axis left a bullseye on the thigh and
# the haunch). The back legs take plain horizontal rings below the haunch (stripe_phase's leg_w).
STRIPE_FOCUS = (0.42, 0.42)      # (y, z); round 2: further back and down, so the barrel's arcs straighten into long diagonals
STRIPE_Z = 0.85                  # heights count this much: the arcs stand a little taller than wide
STRIPE_PERIOD = 0.155            # review Nov 13: 5–6 bold bands on the barrel and rump (the 64 px read)
LEG_TOP = 0.66                   # where the legs' rings meet the arcs (on the leg's outside)
LEG_Y = 0.33
LEG_PERIOD = 0.14                # upgrade: bolder bands on the legs (round 3: 0.105)
TAIL_PERIOD = 0.072


def noise3(p: np.ndarray, f: float, seed: int, octaves: int = 5) -> np.ndarray:
    """A cheap smooth noise (a sum of sines along random directions) in about −1..1, deterministic."""
    rng = np.random.default_rng(seed)
    out = np.zeros(len(p))
    for _ in range(octaves):
        d = rng.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        out += np.sin((p @ d) * f * rng.uniform(0.7, 1.4) + rng.uniform(0, 6.3))
    return out / octaves * 1.6


def warp(p: np.ndarray, amp: float, f: float, seed: int) -> np.ndarray:
    """p moved by a smooth noise vector field (organic edges)."""
    return p + amp * np.stack([noise3(p, f, seed + k, 4) for k in range(3)], axis=1)


# ----------------------------------------------------------------------------- the giraffe patches (Voronoi)
class Seeds:
    """The patches' centres on the body's surface, each with its spacing (patch size) and a random number."""

    def __init__(self, c: np.ndarray, sp: np.ndarray, rnd: np.ndarray):
        self.c, self.sp, self.rnd = c, sp, rnd
        self.cell = float(np.max(sp)) * 1.05 if len(sp) else 1.0
        key = np.floor(c / self.cell).astype(np.int64)
        self.buckets: dict[tuple, list[int]] = {}
        for i, k in enumerate(map(tuple, key)):
            self.buckets.setdefault(k, []).append(i)


def make_seeds(co: np.ndarray, spacing_fn, seed: int = 31, max_candidates: int = 90000) -> Seeds:
    """A Poisson set over sample points `co` (the body's vertices): no two centres closer than their spacing;
    spacing_fn(points) → per point (NaN = no patch there)."""
    rng = np.random.default_rng(seed)
    sp = spacing_fn(co)
    ok = np.nonzero(np.isfinite(sp))[0]
    if len(ok) > max_candidates:
        ok = np.sort(rng.choice(ok, max_candidates, replace=False))
    order = ok[rng.permutation(len(ok))]
    cell = float(np.nanmax(sp[ok])) if len(ok) else 1.0
    grid: dict[tuple, list[int]] = {}
    keep: list[int] = []
    for i in order:
        q = co[i]
        key = (int(q[0] // cell), int(q[1] // cell), int(q[2] // cell))
        clash = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        r = 0.5 * (sp[i] + sp[j])
                        d = co[j] - q
                        if d @ d < r * r:
                            clash = True
                            break
                    if clash:
                        break
                if clash:
                    break
            if clash:
                break
        if not clash:
            grid.setdefault(key, []).append(int(i))
            keep.append(int(i))
    keep = np.array(keep, dtype=np.int64)
    return Seeds(co[keep].copy(), sp[keep].copy(), rng.random(len(keep)))


def voronoi(p: np.ndarray, seeds: Seeds) -> dict[str, np.ndarray]:
    """Per point: the nearest centre (index, distance F1) and the distance to the bisector with the second nearest
    (`edge`: 0 on a patch border, growing inward). Points with no centre within reach get F1 = inf."""
    n = len(p)
    i1 = np.full(n, -1, np.int64)
    f1 = np.full(n, np.inf)
    edge = np.full(n, np.inf)
    if len(seeds.c) < 2:
        return {'i': i1, 'f1': f1, 'edge': edge}
    cell = seeds.cell
    key = np.floor(p / cell).astype(np.int64)
    kk = (key[:, 0] + 4096) * (1 << 26) + (key[:, 1] + 4096) * (1 << 13) + (key[:, 2] + 4096)
    order = np.argsort(kk, kind='stable')
    sk = kk[order]
    starts = np.nonzero(np.concatenate([[True], sk[1:] != sk[:-1]]))[0]
    ends = np.concatenate([starts[1:], [len(sk)]])
    C = seeds.c
    for a, b in zip(starts, ends):
        idx = order[a:b]
        k0 = key[idx[0]]
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    cand.extend(seeds.buckets.get((int(k0[0] + dx), int(k0[1] + dy), int(k0[2] + dz)), ()))
        if len(cand) < 2:
            continue
        cand = np.array(cand, np.int64)
        q = p[idx]
        d2 = ((q[:, None, :] - C[cand][None, :, :]) ** 2).sum(axis=2)
        two = np.argpartition(d2, 1, axis=1)[:, :2]
        da = d2[np.arange(len(q)), two[:, 0]]
        db = d2[np.arange(len(q)), two[:, 1]]
        swap = db < da
        j1 = np.where(swap, two[:, 1], two[:, 0])
        j2 = np.where(swap, two[:, 0], two[:, 1])
        d1, d2b = np.minimum(da, db), np.maximum(da, db)
        s1, s2 = C[cand[j1]], C[cand[j2]]
        gap = np.maximum(np.linalg.norm(s2 - s1, axis=1), 1e-9)
        i1[idx] = cand[j1]
        f1[idx] = np.sqrt(d1)
        edge[idx] = (d2b - d1) / (2.0 * gap)
    return {'i': i1, 'f1': f1, 'edge': edge}


# ----------------------------------------------------------------------------- the zebra stripes
def arc_radius(p: np.ndarray) -> np.ndarray:
    """Distance from the stripes' focus in the side view."""
    return np.hypot(p[:, 1] - STRIPE_FOCUS[0], STRIPE_Z * (p[:, 2] - STRIPE_FOCUS[1]))


def stripe_phase(p: np.ndarray, leg_w: np.ndarray | None = None, chevron: np.ndarray | None = None) -> np.ndarray:
    """The stripes' phase (one stripe per unit), warped a little so the lines wave: arcs round the focus on the body;
    where leg_w > 0 (the back legs below the haunch) rings down the leg, continuing the arcs at the leg's outside, bent
    into a slight chevron by `chevron` (a phase offset per point: round 2, review: even rings read as tubes)."""
    q = warp(p, 0.018, 9.0, 70)
    ph = arc_radius(q) / STRIPE_PERIOD
    if leg_w is not None:
        top = float(arc_radius(v3([[0.0, LEG_Y, LEG_TOP]]))[0]) / STRIPE_PERIOD
        ph_leg = top + (LEG_TOP - q[:, 2]) / LEG_PERIOD
        if chevron is not None:
            ph_leg = ph_leg + chevron
        ph = ph * (1 - leg_w) + ph_leg * leg_w
    return ph


def duty_mask(phase: np.ndarray, duty: np.ndarray, soft: float = 0.035) -> np.ndarray:
    """1 on a stripe: `duty` of every period, centred on the period's middle, its edges `soft` of a period wide."""
    f = phase - np.floor(phase)
    d = np.abs(f - 0.5)
    half = 0.5 * duty
    return smooth(half + soft, half - soft, d) * (duty > 0.01)


# ----------------------------------------------------------------------------- the giraffe / zebra blend
def blend(p: np.ndarray) -> np.ndarray:
    """0 giraffe … 1 zebra on the torso: a soft, wavy band round the middle (further forward along the back)."""
    y, z = p[:, 1], p[:, 2]
    # round 3 (review): a wide, wavy band on the reference's diagonal (from behind the withers down and back to the flank)
    yb = -0.07 + 0.55 * (0.9 - z)
    yy = y + 0.05 * np.sin(z * 19.0 + 0.6) + 0.03 * noise3(p, 7.0, 11, 3)
    return smooth(yb - 0.18, yb + 0.22, yy)       # round 2: a wide band (round 1 read as one hard diagonal)


def stretch(p: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Where the patterns blend, the patches stretch out along the stripes: space is stretched across them (away from
    the stripes' focus in the side view), so a patch of the same size covers a thinner, longer piece of skin."""
    c = np.empty_like(p)
    c[:, 0] = p[:, 0]
    c[:, 1], c[:, 2] = STRIPE_FOCUS
    k = 1.0 + 1.6 * smooth(0.1, 0.8, b)[:, None]
    return c + (p - c) * k


def patch_masks(p: np.ndarray, seeds: Seeds, b: np.ndarray, rho_k: np.ndarray | None = None,
                seed_t: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """patch (1 inside a chestnut patch), outline (its soft cream rim, strongest at the patch's edge and fading out into
    the tan), and each patch's random number. Round 2 (review: a tight net of angular polygons read all chestnut): rounded,
    separate patches on visible tan ground, the gaps about a third of a patch; `rho_k` shrinks them (sparser) per point."""
    # round 3: no stretch here (it moved the points but not the patches' centres); the blend's lozenges are drawn along
    # the stripes instead (the recipe's coat_masks)
    q = warp(p, 0.0065, 15.0, 40)
    vo = voronoi(q, seeds)
    i = vo['i']
    has = i >= 0
    sp = np.where(has, seeds.sp[np.maximum(i, 0)], 0.1)
    rnd = np.where(has, seeds.rnd[np.maximum(i, 0)], 0.5)
    g = 0.13 * sp                        # from the cell's border to the patch's edge (half the gap between patches)
    o = np.maximum(0.085 * sp, 0.006)    # the soft cream rim round each patch
    rho = (0.53 + 0.06 * (rnd - 0.5)) * sp    # a disc round the centre: rounded patches, flattened only where neighbours crowd
    if rho_k is not None:
        rho = rho * rho_k
    f1 = vo['f1']
    if seed_t is not None:
        # round 3 (review): the last rows of patches stretch along the stripes into lozenges: each is measured from its
        # centre squeezed across the stripes' arcs (the side view's radial from the focus) and loosened along them
        st = np.where(has, seed_t[np.maximum(i, 0)], 0.0)
        d = q - seeds.c[np.maximum(i, 0)]
        ry, rz = q[:, 1] - STRIPE_FOCUS[0], (q[:, 2] - STRIPE_FOCUS[1]) * STRIPE_Z
        rn = np.maximum(np.hypot(ry, rz), 1e-6)
        ur, uz = ry / rn, rz / rn
        across = d[:, 1] * ur + d[:, 2] * uz
        along = d[:, 2] * ur - d[:, 1] * uz
        fa = np.sqrt(d[:, 0] ** 2 + (across * (1.0 + 1.5 * st)) ** 2 + (along / (1.0 + 0.5 * st)) ** 2)
        f1 = np.where(st > 0.0, fa, f1)
    dp = np.minimum(vo['edge'] - g * (1.0 - 0.5 * (seed_t[np.maximum(i, 0)] if seed_t is not None else 0.0)), rho - f1)
    dp = np.where(has, dp, -1.0)
    soft = 0.0018
    patch = smooth(-soft, soft, dp)
    outline = smooth(-o, -0.12 * o, dp) * (1 - patch)
    return {'patch': patch, 'outline': outline, 'rnd': rnd, 'has': has, 'i': i}


# ----------------------------------------------------------------------------- composing the colours
def lin_hex(h: str) -> np.ndarray:
    from lib import common as C
    return v3(C.lin_rgb(h))


def mix(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0, 1)[:, None]
    return a * (1 - t) + b * t
