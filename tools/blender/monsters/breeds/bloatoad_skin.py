"""Bloatoad's skin (Art 2.1 Ultra): the zones, the rig's weight regions, and the high source's carving with the
attributes its paint reads (1-hero, 2-turnaround, 4-details):
  - the eyes: each lens half sunk in its raised socket, the heavy upper lid sculpted over its top 40% with a rounded
    rim at the lash line, a thin lower lid, and under the lens the closed lid a blink reveals;
  - the face: a wide smile curling up at the corners (upper and lower lips rolled), two nostrils on the snout;
  - warts of every size as raised domes (the big glossy ones, many small), and dark rosettes on the back, the head
    and the legs: raised patches of clustered nodules (4-details panel 6);
  - soft folds: rolls across the throat and the belly, creases at the wrists, the elbows and the limb roots;
  - fine pebbling on the olive skin, pores on the peach.
Metres; the monster faces −Y, Z is up, +X is its left.
"""
from __future__ import annotations

import numpy as np

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import bloatoad_form as F

smooth = F.smooth
v3 = F.v3
_LAST: dict = {}
_ROSETTES: dict = {}

# the mouth: a smile round a vertical axis at MOUTH_Y (theta 0 at the front, ± toward its corners)
MOUTH_Y = -0.3
MOUTH_TH = [0.0, 20.0, 36.0, 50.0, 60.0, 66.0, 71.0]
# round 2: the corners curl higher up into the cheeks (1-hero, 3-faces neutral: a lazy, content smile at rest)
MOUTH_Z = [0.826, 0.828, 0.834, 0.846, 0.863, 0.88, 0.904]
MOUTH_END = 71.5
# round 3: the game mesh is cut along the slit's floor and a mouth bag sits behind it, so the slit is only the lips' roll
# polish: a shallow crease (12 mm deep, the bake's rays crossed the narrow V from one lip to the other and laid a
# beaded zipper along the closed seam): the cut makes the opening, the paint the one dark line
MOUTH_DEPTH = 0.004                     # the slit's depth (metres)
MOUTH_HALF = 0.006                      # its half-width at the lips
NOSTRILS = [(0.068, -0.612, 0.922), (-0.068, -0.612, 0.922)]


# ----------------------------------------------------------------------------- zones
def mouth_theta(co: np.ndarray) -> np.ndarray:
    return np.degrees(np.arctan2(co[:, 0], -(co[:, 1] - MOUTH_Y)))


def mouth_z(th: np.ndarray) -> np.ndarray:
    return np.interp(np.abs(th), MOUTH_TH, MOUTH_Z)


def face_front(co: np.ndarray) -> np.ndarray:
    """The face's front shell (where the mouth, the lips and the nostrils are)."""
    return (F.ell_sdf(co, (0.0, -0.4, 0.85), (0.46, 0.3, 0.2)) < 0.03) & (co[:, 1] < -0.3)


def peach_mask(co: np.ndarray) -> np.ndarray:
    """0..1: the peach throat and belly (wide under the chin, narrowing down the belly between the arms), the whole
    underside, and the feet's webs (2-turnaround front and side)."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    th = mouth_theta(co)
    below = smooth(0.006, -0.004, z - mouth_z(th))
    # the bib's half-width falls from 0.37 m under the mouth to 0.22 m low on the belly
    hw = np.interp(z, [0.0, 0.15, 0.35, 0.5, 0.65, 0.78, 0.9], [0.24, 0.22, 0.23, 0.28, 0.35, 0.41, 0.42])
    # a soft, wavering edge (never a straight seam down the side)
    wob = 0.035 * np.sin(z * 23.0 + 1.3) + 0.02 * np.sin(z * 51.0 + 0.4)
    side = smooth(hw + wob + 0.07, hw + wob - 0.08, np.abs(x))
    front = smooth(-0.22, -0.34, y + 0.12 * (np.abs(x) / 0.4) ** 2 - 0.1 * smooth(0.5, 0.2, z))
    # the arms stay olive all the way down (2-turnaround front): the bib never reaches onto them
    bib = below * side * front * smooth(0.13, 0.17, F.arm_dist(co))
    # the underside: everything low, except up the legs and on the feet's tops
    ld = F.leg_dist(co)
    under = smooth(0.2, 0.12, z - 0.04 * smooth(0.2, 0.5, np.abs(x)))
    under = under * smooth(0.13, 0.17, ld) * (1.0 - F.foot_mask(co))
    web = web_mask(co)
    return np.clip(np.maximum(np.maximum(bib, under), web), 0.0, 1.0)


def web_mask(co: np.ndarray) -> np.ndarray:
    """0..1 on the webs between the toes (peach), not the toes' tops nor the pads."""
    tl = F.toe_line_dist(co)
    td = F.toe_dist(co)
    return F.foot_mask(co) * smooth(0.016, 0.024, tl) * smooth(0.0, 0.008, td) * smooth(0.04, 0.025, co[:, 2])


def eye_d(co: np.ndarray) -> np.ndarray:
    return np.minimum(np.linalg.norm(co - F.EYE_C[1], axis=1), np.linalg.norm(co - F.EYE_C[-1], axis=1))


def zones(co: np.ndarray) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    ed = eye_d(co)
    head = (F.ell_sdf(co, F.HEAD[0], F.HEAD[1]) < 0.03) & (z > 0.72)
    face = face_front(co) | (ed < 0.11)
    lid = (ed < 0.12) & (z > F.EYE_C[1][2] - 0.02)
    toes = smooth(0.012, -0.004, F.toe_dist(co))
    paw = F.foot_mask(co)
    peach = peach_mask(co)
    under = (z < 0.12) & (F.leg_dist(co) > 0.1) & (paw < 0.5)
    return {'face': face, 'muzzle': face_front(co) & (z > 0.8), 'eye_d': ed, 'toes': toes, 'paw': paw, 'belly': peach > 0.5,
            'peach': peach, 'head': head, 'lid': lid, 'under': under}


# ----------------------------------------------------------------------------- rig weights
def jaw_weight(co: np.ndarray) -> np.ndarray:
    """0..1: the lower lip and chin (below the mouth line, in its width): rigid on `jaw` for 5 cm, fading out 13 cm
    down the throat."""
    th = mouth_theta(co)
    dz = mouth_z(th) - co[:, 2]
    # (round 1: the lip's edge eases onto the jaw over 2 cm, not 6 mm: an opening jaw then stretches a band of skin a
    # few times over instead of a sliver fifteen times, which streaked)
    # round 2: the lips part at the mouth's slit (bloatoad_skin.mouth_field): the lower wall and the chin go with `jaw`, the
    # upper wall with the head, so an opening jaw opens the slit (a dark mouth) instead of stretching the skin
    w = smooth(-0.003, 0.003, dz) * smooth(0.1, 0.035, dz) * smooth(MOUTH_END + 1.0, MOUTH_END - 7.0, np.abs(th))
    return np.clip(w * face_front(co) * (co[:, 1] < -0.33), 0.0, 1.0)


def sac_weight(co: np.ndarray) -> np.ndarray:
    """0..1: the throat sac. Round 2: each point's weight puts it, at the sac's full scale, on a sphere of SAC_R round the
    sac bone's head (the bubble's centre, under the chin): w = (SAC_R / d − 1) / (max − 1). Uniform or peaked weights
    turned the flat throat into a flat-sided wedge; this makes a round, taut bubble bulging forward and sideways, easing
    into the body at its rim (w falls to 0 where d reaches SAC_R)."""
    h = v3(F.SAC['head'])
    d = np.linalg.norm(co - h, axis=1)
    w = np.clip((F.SAC_R / np.maximum(d, 1e-4) - 1.0) / (F.SAC['max'] - 1.0), 0.0, 1.0)
    return w * smooth(-0.32, -0.44, co[:, 1]) * smooth(0.2, 0.32, co[:, 2]) * smooth(0.44, 0.34, np.abs(co[:, 0]))


def sac_gloss(co: np.ndarray) -> np.ndarray:
    """0..1: the glossy sac at rest (the smooth dome under the chin, wetter than the belly)."""
    d = np.linalg.norm((co - v3((0.0, -0.56, 0.63))) / v3((0.36, 0.2, 0.22)), axis=1)
    return smooth(1.25, 0.8, d) * smooth(-0.36, -0.46, co[:, 1])


def trunk_t(co: np.ndarray) -> np.ndarray:
    """How far along the squash chain (BASE 0 → TOP 1) each point lies."""
    b, t = v3(F.BASE), v3(F.TOP)
    d = t - b
    return ((co - b) @ d) / float(d @ d)


LEG_R = {0: (0.115, 0.1, 0.075), 1: (0.17, 0.11, 0.075)}


def _jside(n: int):
    """The lo_body's `jside` attribute (set by bloatoad_carve.cut_mouth) when the rig stage asks for the game mesh's
    weights, else None."""
    try:
        import bpy
        ob = bpy.data.objects.get('lo_body')
        if ob is None or len(ob.data.vertices) != n or 'jside' not in ob.data.attributes:
            return None
        return S.attr_array(ob, 'jside').astype(np.float64)
    except Exception:
        return None       # the front and hind legs' radii: upper, lower, foot


def weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The whole skin, weighted here (no heat weights, which can't match a hand-made throat region at its edge and
    tore the throat in hit_heavy): the squash chain `hips`, `chest`, `head` in soft bands along it; the lower lip on
    `jaw`; the sac on `sac`; each leg by its distance from the leg's bones (the root of the thigh and of the arm stays
    with the body, so the skin creases there instead of stretching), split over its bones; each foot rigid on its foot
    bone, easing onto the shin at the ankle."""
    n = len(co)
    W = {b: np.zeros(n) for b in ('hips', 'chest', 'head', 'jaw', 'sac')}
    t = trunk_t(co)
    sp = F.HEAD_SPLIT
    hd = smooth(sp - 0.09, sp + 0.07, t)
    hp = smooth(1 / 3 + 0.1, 1 / 3 - 0.1, t)
    ch = np.clip(1.0 - hd - hp, 0.0, 1.0)
    # the legs
    legw = np.zeros(n)
    parts = []
    for i, lg in enumerate(F.LEGS, start=1):
        r_up, r_lo, r_ft = LEG_R[i - 1]
        foot = F.TOES_F if i == 1 else F.TOES_B
        for tag, s in (('L', 1), ('R', -1)):
            if f'leg{i}.{tag}' not in names:
                continue
            hip, knee, ank, toe = (v3(F._m(lg[k], s)) for k in ('hip', 'knee', 'ankle', 'toe'))
            d1, t1 = F.seg_dist(co, hip, knee)
            d2, _t2 = F.seg_dist(co, knee, ank)
            d3, _t3 = F.seg_dist(co, ank, toe)
            m1 = smooth(r_up + 0.05, r_up - 0.01, d1) * smooth(0.12, 0.5, t1)
            m2 = smooth(r_lo + 0.05, r_lo - 0.01, d2)
            palm = v3(F._m(foot['palm'], s))
            rr = np.linalg.norm((co - palm)[:, :2], axis=1)
            # round 2: the whole foot by its own parts: the palm, each toe's capsule and pad, and the webs in the fan (a
            # radius from the palm left the outer pads partly on the body, and they stretched into needles)
            tl = np.full(len(co), np.inf)
            pd = np.full(len(co), np.inf)
            for p0, pad in F.toe_lines(foot, s):
                tl = np.minimum(tl, F.seg_dist(co, p0, pad)[0])
                pd = np.minimum(pd, np.linalg.norm(co - pad, axis=1))
            fm = np.maximum.reduce([smooth(0.16, 0.12, rr) * smooth(0.1, 0.07, co[:, 2]),
                                    smooth(F.TOE_R[0] + 0.03, F.TOE_R[0] + 0.012, tl),
                                    smooth(F.PAD_R + 0.03, F.PAD_R + 0.012, pd),
                                    smooth(max(foot['len']) + 0.07, max(foot['len']) + 0.04, rr) * smooth(0.055, 0.04, co[:, 2])])
            m3 = np.maximum(smooth(r_ft + 0.04, r_ft - 0.01, d3), fm)
            m = np.clip(np.maximum(np.maximum(m1, m2), m3), 0.0, 1.0)
            sw = U.segment_weights(co, [('u', tuple(hip), tuple(knee)), ('l', tuple(knee), tuple(ank)), ('f', tuple(ank), tuple(toe))], power=6.0)
            # round 2: the whole foot (palm, toes, webs) rigid on the foot bone: the outer toes lie nearer the shin's line
            # than the foot's, so they half followed the shin and stretched into needles and cones in hit, strike and ko
            ff = smooth(0.0, 0.6, fm)
            wu, wl, wf = sw['u'] * (1.0 - ff), sw['l'] * (1.0 - ff), sw['f'] * (1.0 - ff) + ff
            tot = np.maximum(wu + wl + wf, 1e-6)
            parts.append((m, {f'leg{i}.{tag}': wu / tot, f'shin{i}.{tag}': wl / tot, f'foot{i}.{tag}': wf / tot}))
            legw = np.maximum(legw, m)
    # several legs never overlap much; normalise where they do
    tot_leg = sum(m for m, _ in parts) if parts else np.zeros(n)
    k = np.where(tot_leg > 1.0, 1.0 / np.maximum(tot_leg, 1e-6), 1.0)
    wj = jaw_weight(co)
    # round 3: the game mesh is cut along the mouth (bloatoad_carve.cut_mouth): each lip's side of the cut is stored as the
    # lo_body attribute `jside` (1 the jaw's, 0 the head's, −1 away from the cut), read here, so the lips part cleanly
    js = _jside(len(co))
    if js is not None:
        near = js >= 0.0
        wj = np.where(near, np.clip(js, 0.0, 1.0) * np.maximum(wj, smooth(-0.01, 0.0, mouth_z(mouth_theta(co)) - co[:, 2])), wj)
    wj = wj * (1.0 - legw)
    # the sac starts below the lower lip with no rim (it rose to full weight right under the jaw's rigid lip: a bucket)
    dzl = mouth_z(mouth_theta(co)) - co[:, 2]
    ws = sac_weight(co) * smooth(0.0, 0.05, dzl) * (1.0 - wj) * (1.0 - legw)
    rest = np.clip(1.0 - legw - wj - ws, 0.0, 1.0)
    W['jaw'] = wj
    W['sac'] = ws
    W['head'] = rest * hd
    W['chest'] = rest * ch
    W['hips'] = rest * hp
    for m, wd in parts:
        for b, w in wd.items():
            W[b] = W.get(b, np.zeros(n)) + m * k * w
    allm = np.ones(n, bool)
    return [(allm, {b: w for b, w in W.items() if b in names})]


# ----------------------------------------------------------------------------- the eyes and lids
def eye_field(co: np.ndarray, vn: np.ndarray | None = None) -> dict:
    """Metres to move each vertex near an eye along its normal (small: the eyeball and the lid are parts), and the
    masks the paint reads. Under the lens below the lid's edge the skin is kept 3 mm behind the lens (the closed lid a
    blink shows); just above the edge the lid's rim rolls forward (a thick fleshy lid, never a thin visor), with a soft
    fold above it; a thin lower lid rims the opening's bottom."""
    disp = np.zeros(len(co))
    lid = np.zeros(len(co))
    lash = np.zeros(len(co))
    closed = np.zeros(len(co))
    rim = np.zeros(len(co))
    socket = np.zeros(len(co))
    vec = np.zeros((len(co), 3))
    R = F.EYE_R
    for s in (1, -1):
        c, xax, yax, look = F.eye_frame(s)
        rx, ry, ze = F.eye_coords(co, s)
        r = np.sqrt(rx * rx + ry * ry)
        near = (r < 1.8) & (ze > -0.5 * R) & (ze < 1.5 * R)
        if not near.any():
            continue
        d = ry - F.lid_edge(rx, s)                          # + above the lid's edge
        lens = F.lens_ze(rx, ry)
        below = smooth(0.0, -0.03, d)
        roll = 0.0034 * np.exp(-((d - 0.06) / 0.06) ** 2) * smooth(1.18, 0.98, r)
        # round 3: two or three soft creases across the lid, parallel to its edge (4-details panel 2)
        fold = -0.0011 * (np.exp(-((d - 0.36) / 0.028) ** 2) + 0.8 * np.exp(-((d - 0.6) / 0.03) ** 2)
                          + 0.6 * np.exp(-((d - 0.86) / 0.035) ** 2)) * smooth(1.35, 1.0, r)
        lower = 0.006 * np.exp(-((r - 1.07) / 0.07) ** 2) * smooth(0.0, -0.08, d)         # round 3: a thick lower lid
        delta = (roll + fold + lower) * near
        if vn is not None:
            delta = delta / np.clip(vn @ look, 0.5, 1.0)
        # the lid's egg blends into the head and the brow (a soft fillet, never a cap's seam)
        yc, zc, ax, ay, az = F.LID
        c0 = c - look * (R * F.EYE_DEPTH[1])
        q = co - (c0 + yax * (R * yc) + look * (R * zc))
        s_lid = (np.sqrt((q @ xax / (R * ax)) ** 2 + (q @ yax / (R * ay)) ** 2 + (q @ look / (R * az)) ** 2) - 1.0) * (R * min(ax, ay, az))
        s_rest = np.minimum(F.ell_sdf(co, F.HEAD[0], F.HEAD[1]), F.ell_sdf(co, F.NAPE[0], F.NAPE[1]))
        kf = 0.085                                          # round 3: the lid melts into the brow (no seam)
        h = np.clip(kf - np.abs(s_lid - s_rest), 0.0, None) / kf
        delta = delta + 0.25 * kf * h * h * smooth(1.12, 1.3, r)
        # round the opening's bottom and outer side the face falls away behind the lens's rim (the eye bulges out
        # of the head, a thin lower lid round it), never in front of it
        # (moved straight back along the look, so the skin keeps its place round the lens and never shears)
        ze_max = 0.0035 * np.exp(-((r - 1.04) / 0.045) ** 2) + 0.22 * R * smooth(1.06, 1.75, r)
        pull = np.minimum(ze_max - ze, 0.0) * smooth(1.8, 1.45, r) * smooth(0.97, 1.02, r) * np.maximum(smooth(0.25, 0.05, d), smooth(0.002, 0.008, s_lid)) * near
        pull = np.maximum(pull, -0.05)
        vec = vec + look[None] * np.where(np.abs(pull) > np.abs(vec @ look), pull - (vec @ look), 0.0)[:, None]
        delta = np.clip(delta, -0.03, 0.015) * near
        disp = np.where(near & (np.abs(delta) > np.abs(disp)), delta, disp)
        lid = np.maximum(lid, smooth(-0.02, 0.05, d) * smooth(1.75, 1.35, r) * near)
        lash = np.maximum(lash, np.exp(-((d - 0.005) / 0.03) ** 2) * smooth(1.1, 0.97, r) * near)
        # the closed lid (under the lens) with its lash line low across it (where a blink squeezes the lens to)
        cl = below * smooth(1.02, 0.94, r) * near
        socket = np.maximum(socket, cl)
        cl_line = F.CLOSED_LASH + 0.1 * (1.0 - np.clip(rx, -1, 1) ** 2)
        closed = np.maximum(closed, np.exp(-((ry - cl_line) / 0.05) ** 2) * cl)
        rim = np.maximum(rim, below * np.exp(-((r - 1.07) / 0.09) ** 2) * near)
    return {'disp': disp, 'vec': vec, 'lid': lid, 'lash': lash, 'closed': closed, 'rim': rim, 'socket': socket}


# ----------------------------------------------------------------------------- the body's smooth blend
TRUNK = ('BELLY', 'BACK', 'RUMP', 'HEAD', 'NAPE', 'FRONT', 'SNOUT')


def crease_mask(co: np.ndarray) -> np.ndarray:
    """0..1 where two of the body's volumes meet in a crease (the two nearest are both near the surface)."""
    sd = [F.ell_sdf(co, *getattr(F, n)) for n in TRUNK]
    for side in (1, -1):
        c, r = F.HAUNCH
        sd.append(F.ell_sdf(co, (c[0] * side, c[1], c[2]), r))
    sd = np.sort(np.stack(sd, axis=1), axis=1)
    d1, d2 = sd[:, 0], sd[:, 1]
    return (smooth(0.1, 0.0, d2 - d1) * smooth(0.06, 0.0, np.abs(d1)) * smooth(0.08, 0.14, F.leg_dist(co))
            * smooth(0.13, 0.17, eye_d(co)))


def blend_creases(ob, iterations: int) -> None:
    """Round 2: the body's volumes melt into one surface: Laplacian smoothing only along their creases (the throat, the
    jowls and the belly met in two or three deep even grooves that read as stacked tyres; pushing along the normals
    instead folded the skin over itself). Run first, on the high source and the low body alike."""
    co, _vn = S.mesh_arrays(ob)
    me = ob.data
    ev = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', ev)
    ev = ev.reshape(-1, 2)
    n = len(co)
    deg = np.bincount(ev.ravel(), minlength=n).astype(np.float64)
    deg[deg == 0] = 1.0
    k = 0.8 * crease_mask(co)
    k = np.minimum(1.0, k * 1.0)[:, None]
    p = co.copy()
    for _ in range(int(iterations)):
        acc = np.stack([np.bincount(ev[:, 0], weights=p[ev[:, 1], j], minlength=n) + np.bincount(ev[:, 1], weights=p[ev[:, 0], j], minlength=n)
                        for j in range(3)], axis=1)
        p = p + k * (acc / deg[:, None] - p)
    S.set_positions(ob, p)
    C.log(f'{ob.name}: creases blended ({int((k[:, 0] > 0.05).sum())} vertices, {iterations} steps, moved up to '
          f'{float(np.linalg.norm(p - co, axis=1).max()) * 1000:.0f} mm)')


# ----------------------------------------------------------------------------- the mouth and the nostrils
def mouth_field(co: np.ndarray, vn: np.ndarray | None = None) -> dict:
    """The mouth: round 2, a real slit. The lips part along the smile's line into a narrow V MOUTH_DEPTH deep (both the
    high source and the game mesh carry it), whose walls are the mouth's dark inside: at rest it reads as a thin dark
    smile line; when the jaw opens (its weight splits exactly at the slit's floor) the walls part into a dark open mouth
    and only the slit's floor, deep inside and dark, stretches. The corners curl up into the cheeks with a soft fold
    round each (1-hero, 3-faces neutral); a soft roll on each lip, no shelf."""
    th = mouth_theta(co)
    dz = co[:, 2] - mouth_z(th)
    ff = face_front(co)
    span = smooth(MOUTH_END + 1.0, MOUTH_END - 4.0, np.abs(th)) * ff
    # the slit: deepest along the front, shallowing toward the corners
    deep = MOUTH_DEPTH * smooth(MOUTH_END - 1.0, MOUTH_END - 14.0, np.abs(th))
    prof = np.clip(1.0 - np.abs(dz) / MOUTH_HALF, 0.0, 1.0)
    slit = prof ** 1.6 * span
    groove = np.exp(-(dz / 0.0022) ** 2) * span
    upper = np.exp(-((dz - 0.011) / 0.009) ** 2) * span
    lower = np.exp(-((dz + 0.013) / 0.011) ** 2) * span
    # the corner's soft fold: a short crease curving up and out from each corner into the cheek
    cz = mouth_z(np.full(len(co), MOUTH_END)) + 0.004
    u = (np.abs(th) - (MOUTH_END - 3.0)) / 6.0
    fold = np.exp(-(((co[:, 2] - (cz + 0.04 * np.clip(u, 0, 1) ** 1.3)) / 0.006) ** 2)) * smooth(-0.15, 0.1, u) * smooth(1.6, 1.1, u) * ff
    corner = np.exp(-((np.abs(th) - MOUTH_END) / 2.2) ** 2 - (dz / 0.01) ** 2) * ff
    # round 3: the lips rolled soft (no shelf over the mouth), the corners tucked into a soft cheek fold
    disp = 0.0024 * upper + 0.0022 * lower - 0.004 * corner - 0.0032 * fold
    # the slit is cut straight in, level (never along the tilted normals: that moved its walls up and down across the
    # line, and the jaw's split zigzagged into teeth-like spikes when the mouth opened)
    nh = np.zeros((len(co), 3)) if vn is None else vn * np.array([1.0, 1.0, 0.0])
    nh = nh / np.maximum(np.linalg.norm(nh, axis=1, keepdims=True), 1e-6)
    vec = -(deep * slit)[:, None] * nh
    nos = np.zeros(len(co))
    for c in NOSTRILS:
        dd = np.linalg.norm((co - v3(c)) / v3((1.0, 1.0, 0.7)), axis=1)
        nos = np.maximum(nos, smooth(0.0085, 0.003, dd))
    disp = disp - 0.0045 * nos + 0.0015 * np.exp(-((np.minimum(*[np.linalg.norm(co - v3(c), axis=1) for c in NOSTRILS]) - 0.011) / 0.004) ** 2)
    return {'disp': disp, 'vec': vec, 'mouth': np.clip(groove + 0.6 * corner, 0, 1), 'band': slit, 'lip': np.clip(upper + lower, 0, 1),
            'nostril': nos, 'fold': fold, 'corner': corner, 'span': span, 'dz': dz}
