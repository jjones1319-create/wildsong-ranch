"""Mirrorkin's gilded ornaments and gems (mirrorkin_ultra.build_props): the crest (a fleur with a marquise gem), the
side clasps (a round gem in a bezel between curling scrolls), the bottom fleur and the collar where the handle joins,
the handle's gem and scroll setting and its finial, the gloves' bracelets (2-turnaround, 4-details 1, 4 and 3).

Scrolls are tubes along logarithmic spirals (a C-scroll: a wide sweep winding into a tight curl), slightly flattened,
with a fluted groove down their front on the high source; petals are flattened spindles with a raised vein. The gems are
faceted stones (mirrorkin_mesh.Kit.gem), each in a gold bezel. Part ids (attribute `part`) for the paint and weights.
"""
from __future__ import annotations

import math

import numpy as np

from monsters.breeds import mirrorkin_form as F
from monsters.breeds import mirrorkin_mesh as MM

# part ids
CREST, CLASP, FLEUR, COLLAR, HANDLE_SET, FINIAL, CUFF, BEZEL = 1, 2, 3, 4, 5, 6, 7, 8
GEM = 20                           # + 0 crest, 1 clasps, 2 fleur, 3 handle, 4 cuffs
GOLD_PARTS = (CREST, CLASP, FLEUR, COLLAR, HANDLE_SET, FINIAL, BEZEL)
ON_HANDLE = (HANDLE_SET, FINIAL)   # ride the handle chain

CREST_Y = -0.036                   # the crest's middle plane (in front of the frame's middle: it leans forward)
FLEUR_Y = -0.058


def spiral(c, r0: float, r1: float, th0: float, turns: float, side: int, n: int) -> np.ndarray:
    """A logarithmic spiral in the XZ plane round c (x, z): from radius r0 at angle th0 (degrees) winding `turns`
    turns toward `side` (+1 counter-clockwise seen from the front with +X to the right... i.e. increasing angle) to r1."""
    T = 2 * math.pi * turns
    k = math.log(r0 / r1) / T
    tau = np.linspace(0.0, T, n)
    r = r0 * np.exp(-k * tau)
    a = math.radians(th0) + side * tau
    return np.stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a)], axis=1)


def _xz(P2: np.ndarray, y) -> np.ndarray:
    y = np.broadcast_to(np.asarray(y, np.float64), (len(P2),))
    return np.stack([P2[:, 0], y, P2[:, 1]], axis=1)


def groove(depth: float, at: float = 0.5, w: float = 0.07):
    """A fluted channel down a tube's front face (pa = `at` faces -Y with the hint (0, 1, 0))."""
    def rel(pa, s):
        d = np.minimum(np.abs(pa - at), 1.0 - np.abs(pa - at))
        return -depth * np.exp(-(d / w) ** 2)
    return rel


def vein(height: float, at: float = 0.5, w: float = 0.05):
    def rel(pa, s):
        d = np.minimum(np.abs(pa - at), 1.0 - np.abs(pa - at))
        return height * np.exp(-(d / w) ** 2)
    return rel


def scroll(kit: MM.Kit, P: np.ndarray, r_a: float, r_b: float, part: int, high: bool, pr: float, aspect: float = 1.35,
           ball: float = 1.0) -> None:
    """A scroll tube along P: thick at the start, tapering into the curl. Review round 2: the end tapers on into a
    closed spiral (a ball on the curl read as a flat-cut end)."""
    if not high:
        P = MM.catmull(P, int(len(P) * 1.5))             # round 2: the game mesh's curls were kinked
    k = len(P)
    t = np.linspace(0.0, 1.0, k)
    r = r_a + (r_b - r_a) * t ** 0.8
    r = r * (1.0 - 0.45 * np.clip((t - 0.82) / 0.18, 0, 1) ** 1.5) * (1.0 + (ball - 1.0) * np.clip((t - 0.9) / 0.1, 0, 1) ** 2)
    kit.tube(P, r, 16 if high else 8, part, pr=pr, hint=(0.0, 1.0, 0.0), aspect=aspect,
             relief=groove(0.0011 * (r_a / 0.008)) if high else None, texel_k=1.1)


def spindle(kit: MM.Kit, a, b, width: float, part: int, high: bool, pr: float, aspect: float = 0.5, peak: float = 0.45,
            sharp: float = 0.8, hint=(1.0, 0.0, 0.0)) -> None:
    """A flattened, pointed petal from a to b (widest at `peak`), a raised vein down its front on the high source."""
    n = 26 if high else 18
    P = np.linspace(np.asarray(a, np.float64), np.asarray(b, np.float64), n)
    t = np.linspace(0.0, 1.0, n)
    prof = np.where(t < peak, np.sin(0.5 * math.pi * t / peak), np.cos(0.5 * math.pi * (t - peak) / (1 - peak))) ** sharp
    r = np.maximum(width * prof, 0.0015)
    # the tube's N runs along `hint` (the petal's width), B its depth (aspect); the front is at pa 0.75 or 0.25
    kit.tube(P, r, 14 if high else 11, part, pr=pr, hint=hint, aspect=aspect, relief=vein(0.0012, 0.75) if high else None,
             texel_k=1.1)


def leaf(kit: MM.Kit, pts, width: float, part: int, high: bool, pr: float, depth: float = 0.4, peak: float = 0.35) -> None:
    """An acanthus leaf along a curve (pts, in a plane facing -Y): widest a third of the way, a pointed curling tip,
    lobed edges and a vein down its front (review round 2: 2-3 leaves in each cluster, leaves round the gems)."""
    n = 30 if high else 16
    P = MM.catmull(np.asarray(pts, np.float64), n)
    t = np.linspace(0.0, 1.0, n)
    prof = np.where(t < peak, np.sin(0.5 * math.pi * np.clip(t / peak, 0, 1)) ** 0.7,
                    np.cos(0.5 * math.pi * np.clip((t - peak) / (1 - peak), 0, 1)) ** 0.9)
    r = np.maximum(width * depth * prof, 0.0012)
    L = float(MM.arclen(P)[-1])

    def rel(pa, ss):
        edge = np.abs(np.sin(2 * np.pi * pa)) ** 3
        lobes = (0.0018 if high else 0.0011) * np.sin(2 * np.pi * ss / max(L / 4.5, 1e-3)) * edge
        front = np.minimum(np.abs(pa - 0.5), 1.0 - np.abs(pa - 0.5))
        return lobes - (0.0009 * np.exp(-(front / 0.06) ** 2) if high else 0.0)
    # N runs along -Y/+Y (the depth: radius), B across the leaf in its plane (aspect = width / depth)
    kit.tube(P, r, 14 if high else 10, part, pr=pr, hint=(0.0, 1.0, 0.0), aspect=1.0 / depth, relief=rel, texel_k=1.1)


def loop(kit: MM.Kit, centre, nrm, up, ra: float, rb: float, thick: float, part: int, high: bool, pr: float,
         aspect: float = 0.8, marquise: bool = False, lift: float = 0.0) -> None:
    """A bezel ring round a gem (in the plane of nrm), radii ra across and rb along up; a marquise bezel is pointed.
    `thick` is its height along nrm, aspect its width / height, `lift` moves it toward the viewer: a raised collar as
    tall as the stone's crown shields the gold round it in the bake (review round 2: the gem's colour spilled)."""
    c, nrm, up = (np.asarray(v, np.float64) for v in (centre, nrm, up))
    nrm = nrm / np.linalg.norm(nrm)
    up = up - nrm * float(up @ nrm)
    up /= np.linalg.norm(up)
    ac = np.cross(up, nrm)
    n = 40 if high else 30
    t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    gu = ra * np.sin(t) * (np.abs(np.sin(t)) ** 0.35 if marquise else 1.0)       # the gem's own outline (round 1)
    gv = rb * np.cos(t)
    P = c[None] + nrm[None] * lift + gu[:, None] * ac + gv[:, None] * up
    kit.tube(P, thick, 8 if high else 7, part, pr=pr, hint=tuple(nrm), aspect=aspect, closed=True, texel_k=1.1)


def set_gem(kit: MM.Kit, gems: MM.Kit, gc, nrm, up, a: float, b: float, gid: int, high: bool, pr: float, cut: str = 'marquise',
            n: int = 16) -> None:
    """A gem sunk in a raised bezel collar: the collar stands as tall as the stone's crown."""
    gc, nrm = np.asarray(gc, np.float64), np.asarray(nrm, np.float64)
    nrm = nrm / np.linalg.norm(nrm)
    gems.gem(gc, nrm, up, a, b, gid, cut, pr=pr, n=n, crown=0.24)
    hc = 0.24 * min(a, b) * 1.6
    loop(kit, gc, nrm, up, a + 0.0028, b + 0.0028, 0.6 * hc + 0.0012, BEZEL, high, pr, aspect=0.55, marquise=cut == 'marquise',
         lift=0.4 * hc)


# ----------------------------------------------------------------------------- the crest
def crest(kit: MM.Kit, gems: MM.Kit, high: bool) -> None:
    """Stands on the frame's top, its middle plane a little in front of the frame's (2-turnaround side: it leans
    forward); the parts that hang over the frame's front (the low arms, the base band, the drop) lie on its face.
    Review round 2: about 1.4x wider and 1.2x taller, leaves wrapping the gem, the scrolls closing into spirals."""
    y, yf = CREST_Y, -0.062
    spindle(kit, (0.0, y - 0.004, 1.034), (0.0, y + 0.002, 1.19), 0.044, CREST, high, 0.11, aspect=0.55, peak=0.4)
    # the finial: a bead and a point
    kit.tube(np.array([(0.0, y + 0.002, 1.182), (0.0, y + 0.002, 1.191), (0.0, y + 0.002, 1.199), (0.0, y + 0.002, 1.21)]),
             np.array([0.007, 0.0098, 0.0068, 0.0018]), 10 if high else 7, CREST, pr=0.12, hint=(1.0, 0.0, 0.0), texel_k=1.1)
    # the drop hanging over the frame's lip (round 1: shorter, forward of the glass's dome)
    spindle(kit, (0.0, yf, 1.05), (0.0, yf - 0.008, 1.022), 0.0125, CREST, high, 0.13, aspect=0.6, peak=0.35)
    for s in (1, -1):
        # the fleur's arms: up and out from the base, curling outward and down into closed spirals
        P2 = spiral((0.092 * s, 1.118), 0.073, 0.0042, 215 if s > 0 else -35, 1.4, -s, 56 if high else 30)
        scroll(kit, _xz(P2, y - 0.004), 0.0152, 0.0058, CREST, high, 0.2 + 0.05 * s)
        # the low arms along the frame's top, curling up (on the frame's face)
        P2 = spiral((0.124 * s, 1.054), 0.044, 0.0038, 190 if s > 0 else -10, 1.25, s, 40 if high else 20)
        scroll(kit, _xz(P2, yf + 0.002), 0.0115, 0.0048, CREST, high, 0.3 + 0.05 * s)
        # two leaves cradling the gem from below
        leaf(kit, [(0.004 * s, yf + 0.004, 1.056), (0.03 * s, yf - 0.001, 1.08), (0.036 * s, yf - 0.003, 1.112), (0.026 * s, yf - 0.002, 1.142)],
             0.011, CREST, high, 0.14 + 0.02 * s)
    # the base: a band of carved leaves (round 1, 4-details 1)
    band = MM.catmull(np.array([(-0.056, yf + 0.003, 1.046), (0.0, yf, 1.043), (0.056, yf + 0.003, 1.046)]), 34 if high else 20)

    def leaves(pa, ss):
        lobe = np.abs(np.sin(np.pi * ss / 0.0135)) ** 0.7
        out = 0.0028 * lobe - 0.0012
        if high:
            front = np.minimum(np.abs(pa - 0.5), 1.0 - np.abs(pa - 0.5))
            out = out - 0.0007 * np.exp(-(front / 0.05) ** 2) * lobe
        return out
    kit.tube(band, 0.0092, 16 if high else 9, CREST, pr=0.15, hint=(0.0, 1.0, 0.0), aspect=1.4, relief=leaves, texel_k=1.1)
    set_gem(kit, gems, (0.0, y - 0.024, 1.11), (0.0, -1.0, 0.12), (0.0, 0.12, 1.0), 0.0245, 0.048, GEM + 0, high, 0.1)


# ----------------------------------------------------------------------------- the side clasps
SIDE_Y = -0.026      # review round 2: forward of the hood, which now tucks behind the frame's edge


def clasp_frame(s: int):
    """The side gem's centre and facing (s +1 the left side): on the frame's outer edge, turned out and forward, so it
    reads round from the front and from the side (2-turnaround), on a small boss."""
    x, z = F.oval_xz(0.0, F.BAND_SIDE)
    c = np.array([s * (float(x) - 0.003), -0.032, float(z)])
    nrm = np.array([0.6 * s, -0.8, 0.0])
    return c, nrm / np.linalg.norm(nrm)


def clasps(kit: MM.Kit, gems: MM.Kit, high: bool) -> None:
    """Review round 2: one leafy scroll cluster round each shoulder gem (about a quarter of the glass's height), not
    four separate hooks: a C-scroll above and one below, both rooted at the gem and curling outward into closed
    spirals, and three acanthus leaves fanning out behind the gem between them."""
    x0 = float(F.oval_xz(0.0, F.BAND_SIDE)[0])
    for s in (1, -1):
        for sz, th0 in ((1.0, -112.0), (-1.0, 112.0)):
            a0 = th0 if s > 0 else 180.0 - th0
            P2 = spiral((s * (x0 + 0.01), F.ZC + 0.04 * sz), 0.031, 0.0036, a0, 1.35, s * int(sz), 44 if high else 24)
            scroll(kit, _xz(P2, SIDE_Y), 0.0094, 0.0044, CLASP, high, 0.4 + 0.05 * s + 0.02 * sz)
        yl = SIDE_Y + 0.008
        for k, (dz1, dz2, ln) in enumerate(((0.012, 0.03, 0.06), (0.0, -0.006, 0.066), (-0.012, -0.034, 0.058))):
            pts = [(s * (x0 - 0.006), yl, F.ZC + 0.4 * dz1), (s * (x0 + 0.45 * ln), yl - 0.002, F.ZC + dz1 + 0.35 * dz2),
                   (s * (x0 + 0.85 * ln), yl - 0.003, F.ZC + dz2), (s * (x0 + ln), yl - 0.004, F.ZC + 1.25 * dz2 - 0.006)]
            leaf(kit, pts, 0.012, CLASP, high, 0.46 + 0.05 * s + 0.01 * k)
        c, nrm = clasp_frame(s)
        # the boss behind the stone, then the stone in its raised bezel
        kit.tube(np.array([c - nrm * 0.016, c - nrm * 0.008, c - nrm * 0.002]), np.array([0.016, 0.0185, 0.0185]),
                 16 if high else 10, CLASP, pr=0.42 + 0.05 * s, hint=(0.0, 0.0, 1.0), caps=(True, False), texel_k=1.0)
        set_gem(kit, gems, c - nrm * 0.002, nrm, (0.0, 0.0, 1.0), 0.0148, 0.0148, GEM + 1, high, 0.3 + 0.1 * s, cut='round', n=14)


# ----------------------------------------------------------------------------- the bottom fleur and the collar
def fleur(kit: MM.Kit, gems: MM.Kit, high: bool) -> None:
    """On the frame's bottom, in front of its face. Review round 2: about 1.4x wider, leaves wrapping the gem, the
    scrolls closing into spirals; the petal's tip stays below the glass's dome (it baked a dark pinch into it)."""
    y = FLEUR_Y
    spindle(kit, (0.0, y, 0.446), (0.0, y - 0.026, 0.538), 0.033, FLEUR, high, 0.6, aspect=0.5, peak=0.42)
    for s in (1, -1):
        # the side scrolls along the frame's bottom, curling up and in
        P2 = spiral((0.1 * s, 0.497), 0.056, 0.0042, 205 if s > 0 else -25, 1.35, -s, 48 if high else 26)
        scroll(kit, _xz(P2, y - 0.003), 0.0125, 0.0052, FLEUR, high, 0.62 + 0.05 * s)
        # two leaves cradling the gem from below
        leaf(kit, [(0.004 * s, y - 0.016, 0.452), (0.028 * s, y - 0.021, 0.468), (0.034 * s, y - 0.023, 0.494), (0.024 * s, y - 0.022, 0.522)],
             0.01, FLEUR, high, 0.64 + 0.02 * s)
    set_gem(kit, gems, (0.0, y - 0.018, 0.493), (0.0, -1.0, 0.18), (0.0, 0.18, 1.0), 0.022, 0.038, GEM + 2, high, 0.6)
    # the collar where the handle leaves the frame, and a leaf hanging down the neck
    for z, r in ((0.446, 0.0058), (0.425, 0.0048)):
        rx, ry = F.handle_rx(z)
        n = 36 if high else 20
        t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
        Pc = np.stack([(rx + 0.002) * np.cos(t), F.HANDLE_Y + (ry + 0.002) * np.sin(t), np.full(n, z)], axis=1)
        kit.tube(Pc, r, 8 if high else 6, COLLAR, pr=0.7, hint=(0.0, 0.0, 1.0), closed=True, aspect=1.0, texel_k=1.0)
    yf = F.handle_surface_y(0.41) - 0.003
    spindle(kit, (0.0, yf, 0.428), (0.0, F.handle_surface_y(0.37) - 0.002, 0.365), 0.011, COLLAR, high, 0.72, aspect=0.5, peak=0.3)


# ----------------------------------------------------------------------------- the handle's setting and the finial
def on_bulb(x, z, out: float = 0.0) -> np.ndarray:
    """A point on the handle's front surface at (x, z), `out` metres in front of it."""
    x, z = np.asarray(x, np.float64), np.asarray(z, np.float64)
    rx, ry = F.handle_rx(z)
    q = np.clip(x / np.maximum(rx, 1e-6), -0.999, 0.999)
    y = F.HANDLE_Y - ry * np.sqrt(1.0 - q * q)
    return np.stack([x, y - out, z], axis=-1)


def handle_set(kit: MM.Kit, gems: MM.Kit, high: bool) -> None:
    zc = 0.153
    gc = on_bulb(0.0, zc, 0.004)
    nrm = (0.0, -1.0, 0.05)
    set_gem(kit, gems, gc, nrm, (0.0, 0.0, 1.0), 0.0215, 0.036, GEM + 3, high, 0.8)
    for s in (1, -1):
        P2 = spiral((0.04 * s, zc + 0.03), 0.036, 0.0038, 250 if s > 0 else -70, 1.25, -s, 36 if high else 18)
        P = on_bulb(P2[:, 0], P2[:, 1], 0.004)
        scroll(kit, P, 0.0072, 0.004, HANDLE_SET, high, 0.82 + 0.05 * s)
        P2 = spiral((0.036 * s, zc - 0.045), 0.028, 0.0034, 110 if s > 0 else 70, 1.15, s, 30 if high else 16)
        P = on_bulb(P2[:, 0], P2[:, 1], 0.004)
        scroll(kit, P, 0.0064, 0.0036, HANDLE_SET, high, 0.85 + 0.05 * s)
    # leaves above and below the gem
    a, b = on_bulb(0.0, zc + 0.044, 0.004), on_bulb(0.0, zc + 0.1, 0.003)
    spindle(kit, a, b, 0.012, HANDLE_SET, high, 0.88, aspect=0.5, peak=0.3)
    # the finial: a collar and a point
    n = 30 if high else 18
    t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    rx, ry = F.handle_rx(0.07)
    P = np.stack([(rx + 0.001) * np.cos(t), F.HANDLE_Y + (ry + 0.001) * np.sin(t), np.full(n, 0.07)], axis=1)
    kit.tube(P, 0.0052, 8 if high else 6, FINIAL, pr=0.9, hint=(0.0, 0.0, 1.0), closed=True, texel_k=1.0)
    kit.tube(np.array([(0.0, F.HANDLE_Y, 0.064), (0.0, F.HANDLE_Y, 0.057), (0.0, F.HANDLE_Y, 0.05), (0.0, F.HANDLE_Y, F.HANDLE_TIP)]),
             np.array([0.015, 0.0125, 0.007, 0.0016]), 12 if high else 8, FINIAL, pr=0.92, hint=(1.0, 0.0, 0.0), texel_k=1.0)


# ----------------------------------------------------------------------------- the gloves' bracelets
def cuff_frame(s: int):
    g = F.glove_points(s)
    w, f, up = (np.array(g[k]) for k in ('wrist', 'along', 'up'))
    c = w + f * 0.004
    face = up * 0.55 + np.array((0.0, -1.0, 0.0)) * 0.8
    face = face - f * float(face @ f)
    face /= np.linalg.norm(face)
    return c, f, up, face


def cuffs(kit: MM.Kit, gems: MM.Kit, high: bool) -> None:
    g = F.GS
    for s in (1, -1):
        c, f, up, face = cuff_frame(s)
        n = 44 if high else 26
        t = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
        side = np.cross(f, up)
        R = 0.0318 * g                      # review round 1: snug on the wrist (it floated round it)
        P = c[None] + R * (np.cos(t)[:, None] * up[None] + np.sin(t)[:, None] * side[None])
        kit.tube(P, 0.0105 * g, 8 if high else 6, CUFF, pr=0.95 + 0.02 * s, hint=tuple(f), aspect=0.55, closed=True,
                 relief=(lambda pa, ss: 0.0008 * np.cos(4 * np.pi * pa) ** 8) if high else None, texel_k=1.0)
        gc = c + face * (R + 0.0062 * g)
        gems.gem(gc, face, f, 0.0092 * g, 0.0092 * g, GEM + 4, 'round', pr=0.96 + 0.02 * s, n=12)
        loop(kit, gc - face * 0.0015, face, f, 0.0104 * g, 0.0104 * g, 0.0028 * g, BEZEL, high, 0.96 + 0.02 * s)


def objects(high: bool, which: str = 'gold') -> list:
    """The ornaments (own unwrap; which='gold') or the gems (flat facets; which='gems'), as hi_ / lo_ objects. Review
    round 2: the gems are the build's membranes (mirrorkin_ultra.build_fins), baked on their own, because in the shared
    props bake the cage's rays from the gold round a stone hit the stone and its violet spilled onto the gold."""
    tag = 'hi' if high else 'lo'
    gold, gems = MM.Kit(), MM.Kit()
    crest(gold, gems, high)
    clasps(gold, gems, high)
    fleur(gold, gems, high)
    handle_set(gold, gems, high)
    cuffs(gold, gems, high)
    if which == 'gems':
        b = gems.object(f'{tag}_gems')
        b['prop'] = 'gems'
        return [b]
    a = gold.object(f'{tag}_gold')
    a['prop'] = 'gold'
    return [a]
