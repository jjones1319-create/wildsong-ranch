"""Art 2.1 Ultra: helpers for the recipe contract (tools/blender/monsters/breeds/RECIPE.md).

Recipes import this as `from lib import ultra as U`. Nothing here touches the scene, so the shape preview, the build and
the recipes can all use it.
"""
from __future__ import annotations

import numpy as np

from lib.surface import smooth, v3

# Puddlepup's size: HEIGHT_UNITS = 150 is a monster about 1 m tall (rest height 0.986 m). A recipe models its breed at
# HEIGHT_UNITS / UNITS_PER_METRE metres tall, so every breed is at true relative size in Blender and in the lineup.
UNITS_PER_METRE = 150.0

# Mesh name → material kind, in export order. lo_body and lo_eyes are required; the rest ship only when the recipe
# builds them (build_fins, card_params, tuft_frames, build_props).
MESH_KINDS = {'lo_body': 'body', 'lo_eyes': 'eye', 'lo_fins': 'fin', 'lo_cards': 'card', 'lo_tuft': 'lock', 'lo_props': 'prop'}
REQUIRED_MESHES = ('lo_body', 'lo_eyes')


def size_k(recipe) -> float:
    """The breed's size relative to Puddlepup (1.0 = 150 units): the plan scales its absolute offsets by it."""
    return float(getattr(recipe, 'HEIGHT_UNITS', UNITS_PER_METRE)) / UNITS_PER_METRE


def variant_short(vid: str, breed_id: str) -> str:
    """'songheart-puddlepup' → 'songheart', 'town-crier-tumblefox' → 'town-crier' (hyphens kept): the bake pass,
    atlas_<short>.png, the paint attribute, the card colours and the variant's own props mesh lo_props_<short>."""
    return vid[: -len(breed_id) - 1] if vid.endswith(f'-{breed_id}') else vid


def variant_attr(vid: str, breed_id: str) -> str:
    """The colour attribute a recipe's paint_sources writes on every source for a variant (the base is 'paint')."""
    return f'paint_{variant_short(vid, breed_id)}'


def variant_colour_attr(vid: str, breed_id: str) -> str:
    """The cards' and tuft's per-vertex colour for a variant (the base is 'Col')."""
    return f'Col_{variant_short(vid, breed_id)}'


def variant_props_mesh(vid: str, breed_id: str) -> str:
    """The game mesh holding the props only this variant wears (the runtime shows it only while the variant is on)."""
    return f'lo_props_{variant_short(vid, breed_id)}'


def prop_name(ob) -> str:
    """Which prop an object of build_props is: its custom property 'prop', else its name without the hi_ / lo_ prefix
    (and any .001 suffix). A prop listed in a variant's 'props' owns every object named <prop> or <prop>_<anything>."""
    if 'prop' in ob.keys():
        return str(ob['prop'])
    n = ob.name.split('.')[0]
    return n[3:] if n[:3] in ('hi_', 'lo_') else n


def variant_prop_owners(recipe) -> dict[str, str]:
    """prop name → the short name of the one variant that wears it (VARIANTS[vid]['props']); unlisted props are always worn."""
    out: dict[str, str] = {}
    for vid, pal in recipe.VARIANTS.items():
        for p in pal.get('props', []) or []:
            if p in out:
                raise SystemExit(f"prop {p!r} is listed under two variants; give each variant its own copy (e.g. '{p}_2')")
            out[p] = variant_short(vid, recipe.ID)
    return out


def prop_owner(ob, owners: dict[str, str]) -> str | None:
    """The short name of the variant that alone wears this prop object, or None when every variant wears it."""
    name = prop_name(ob)
    for p, short in owners.items():
        if name == p or name.startswith(p + '_'):
            return short
    return None


def polyline_param(p: np.ndarray, pts: np.ndarray) -> tuple[np.ndarray, float]:
    """For points `p` (n×3), the arc-length position 0..1 of their nearest spot on the polyline `pts` (k×3; may run
    past 0 or 1 beyond the ends) and the polyline's length."""
    pts = np.asarray(pts, np.float64)
    seg = pts[1:] - pts[:-1]
    lens = np.linalg.norm(seg, axis=1)
    total = float(lens.sum())
    start = np.concatenate([[0.0], np.cumsum(lens)[:-1]])
    best_d = np.full(len(p), np.inf)
    best_t = np.zeros(len(p))
    for i in range(len(seg)):
        L2 = max(float(lens[i]) ** 2, 1e-12)
        u = ((p - pts[i]) @ seg[i]) / L2
        lo = -np.inf if i == 0 else 0.0
        hi = np.inf if i == len(seg) - 1 else 1.0
        u = np.clip(u, lo, hi)
        q = pts[i] + u[:, None] * seg[i]
        d = np.linalg.norm(p - q, axis=1)
        better = d < best_d
        best_d = np.where(better, d, best_d)
        best_t = np.where(better, (start[i] + u * lens[i]) / max(total, 1e-9), best_t)
    return best_t, total


def chain_weights(p: np.ndarray, pts, bones: list[str], parent: str, fade: tuple[float, float] = (0.05, -0.08)) -> dict[str, np.ndarray]:
    """Weights for a chain of bones (a tail, a mane) by how far along the polyline `pts` (len(bones) + 1 points: the
    bones' heads and the last tail) a point lies: `parent` near the root, then each bone in turn (triangular blends
    centred on each bone). Puddlepup's tail_weights is this with 3 bones on a straight line."""
    t, _ = polyline_param(p, np.asarray(pts, np.float64))
    n = len(bones)
    w = {parent: smooth(fade[0], fade[1], t)}
    c = [(k + 0.5) / n for k in range(n)]
    raw = [np.clip(1.0 - np.abs(t - c[k]) * n, 0, 1) for k in range(n)]
    raw[0] = np.where(t < c[0], 1.0, raw[0])
    raw[-1] = np.where(t > c[-1], 1.0, raw[-1])
    tot = np.maximum(sum(raw), 1e-6)
    for k, b in enumerate(bones):
        w[b] = raw[k] / tot * (1 - w[parent])
    return w


def chain_points(base, direction, length: float, bones: int) -> list[tuple[float, float, float]]:
    """A straight chain's bones+1 points (what the plan builds when the recipe gives no explicit points)."""
    b = v3(base)
    d = v3(direction)
    d = d / max(np.linalg.norm(d), 1e-9)
    return [tuple(map(float, b + d * length * k / bones)) for k in range(bones + 1)]


def rigid(mask: np.ndarray, bone: str) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """A weight region that moves rigidly with one bone (horns, a rope, a scarf on the neck)."""
    return mask, {bone: np.ones(int(mask.sum()))}


# ============================================================================= batch 2: wings and hard plates
# Everything below is opt-in (RECIPE.md: "Quadruped plan options" and "Coats without fur"); no default uses it.

def _unit(a) -> np.ndarray:
    a = v3(a)
    return a / max(float(np.linalg.norm(a)), 1e-12)


def _seg_dist(p: np.ndarray, a, b) -> np.ndarray:
    a, b = v3(a), v3(b)
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def segment_weights(p: np.ndarray, segs, power: float = 6.0) -> dict[str, np.ndarray]:
    """Weights for rigid-looking parts on a chain (a wing's arm and finger tubes, a tusk on the jaw, a horn): every point
    follows the bone whose segment is nearest, blending smoothly where two meet (inverse distance to `power`; higher =
    crisper joints). `segs` is a list of (bone, head, tail); a bone may appear more than once (its weights add)."""
    p = v3(p).reshape(-1, 3)
    d = np.stack([_seg_dist(p, h, t) for _b, h, t in segs], axis=1)
    w = 1.0 / np.maximum(d, 1e-4) ** power
    w /= np.maximum(w.sum(axis=1, keepdims=True), 1e-30)
    out: dict[str, np.ndarray] = {}
    for j, (b, _h, _t) in enumerate(segs):
        out[b] = out.get(b, 0.0) + w[:, j]
    return out


# ----------------------------------------------------------------------------- wings (plans/quadruped.py `wings`)
def wing_tag(side: int) -> str:
    return 'L' if side > 0 else 'R'


def _mirror(p, side: int) -> np.ndarray:
    q = v3(p).astype(np.float64).copy()
    q[..., 0] *= 1.0 if side > 0 else -1.0
    return q


def wing_points(spec: dict, side: int = 1, spread: bool = False) -> dict:
    """One wing's joints (side +1 = the monster's left, +X; -1 mirrored): shoulder, elbow, wrist, fingers (one tip per
    finger bone), attach (where the trailing edge meets the body). The recipe gives the left wing folded (the rest pose)
    and `spread` = {'elbow', 'wrist', 'fingers'} for the open pose: those points give directions only, every bone keeps
    its rest length (so the spread pose never stretches a bone)."""
    s, e, w = v3(spec['shoulder']), v3(spec['elbow']), v3(spec['wrist'])
    tips = [v3(t) for t in spec['fingers']]
    if spec.get('attach') is not None:
        att = v3(spec['attach'])
    else:
        att = s + v3((0.0, 1.0, -0.35)) * float(np.linalg.norm(w - s)) * 0.8
    if spread:
        sp = spec['spread']
        if len(sp['fingers']) != len(tips):
            raise ValueError(f"wings: spread has {len(sp['fingers'])} fingers, the rest pose {len(tips)}")
        e2 = s + _unit(v3(sp['elbow']) - s) * float(np.linalg.norm(e - s))
        w2 = e2 + _unit(v3(sp['wrist']) - v3(sp['elbow'])) * float(np.linalg.norm(w - e))
        tips = [w2 + _unit(v3(t2) - v3(sp['wrist'])) * float(np.linalg.norm(t - w)) for t, t2 in zip(tips, sp['fingers'])]
        e, w = e2, w2
    return {'shoulder': _mirror(s, side), 'elbow': _mirror(e, side), 'wrist': _mirror(w, side),
            'fingers': [_mirror(t, side) for t in tips], 'attach': _mirror(att, side)}


def wing_bone_names(spec: dict, side: int) -> list[str]:
    """`<name>.L.1` shoulder -> elbow, `<name>.L.2` elbow -> wrist, `<name>.L.f1..fK` wrist -> each finger tip."""
    nm, t = spec.get('name', 'wing'), wing_tag(side)
    return [f'{nm}.{t}.1', f'{nm}.{t}.2'] + [f'{nm}.{t}.f{k + 1}' for k in range(len(spec['fingers']))]


def wing_bones(spec: dict, side: int, spread: bool = False) -> list[tuple]:
    """(bone, head, tail, parent) for one wing, at rest (folded) or spread."""
    q = wing_points(spec, side, spread)
    names = wing_bone_names(spec, side)
    out = [(names[0], q['shoulder'], q['elbow'], spec.get('parent', 'chest')), (names[1], q['elbow'], q['wrist'], names[0])]
    for k, tip in enumerate(q['fingers']):
        out.append((names[2 + k], q['wrist'], tip, names[1]))
    return out


def _arc(points: list, u: np.ndarray) -> np.ndarray:
    """Points at arc-length share u (0..1) along a polyline."""
    pts = np.stack([v3(p) for p in points])
    seg = np.linalg.norm(pts[1:] - pts[:-1], axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / max(float(seg.sum()), 1e-12)
    return np.stack([np.interp(u, cum, pts[:, i]) for i in range(3)], axis=1)


def _coons(C0, C1, D0, D1, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """A Coons patch from its four edges (callables of a 1-D array): C0(u) at v=0, C1(u) at v=1, D0(v) at u=0, D1(v) at u=1."""
    U_, V_ = u[:, None], v[:, None]
    z, o = np.zeros(1), np.ones(1)
    c00, c10, c01, c11 = C0(z)[0], C0(o)[0], C1(z)[0], C1(o)[0]
    return ((1 - V_) * C0(u) + V_ * C1(u) + (1 - U_) * D0(v) + U_ * D1(v)
            - ((1 - U_) * (1 - V_) * c00 + U_ * (1 - V_) * c10 + (1 - U_) * V_ * c01 + U_ * V_ * c11))


def _scalloped(a, b, toward, depth: float):
    """The trailing edge from a to b, curving in toward `toward` by depth x its length in the middle."""
    a, b = v3(a), v3(b)
    mid = (a + b) * 0.5
    inward = _unit(v3(toward) - mid) * float(np.linalg.norm(b - a)) * depth
    return lambda u: a[None] + u[:, None] * (b - a)[None] + np.sin(np.pi * u)[:, None] * inward[None]


def _line(a, b):
    a, b = v3(a), v3(b)
    return lambda t: a[None] + t[:, None] * (b - a)[None]


def wing_panels(spec: dict, side: int, spread: bool = False) -> list[dict]:
    """The membrane's panels, each a Coons patch {'C0', 'C1', 'D0', 'D1'} over (u across, v out): finger k -> finger k+1
    (fanning from the wrist), then the last finger -> the body (the arm edge wrist -> elbow -> shoulder at v = 0, the
    body line shoulder -> attach at u = 1). The trailing edges curve in by spec['scallop'] (0.12) of their length."""
    q = wing_points(spec, side, spread)
    w, e, s, att, tips = q['wrist'], q['elbow'], q['shoulder'], q['attach'], q['fingers']
    depth = float(spec.get('scallop', 0.12))
    out = []
    for k in range(len(tips) - 1):
        out.append({'C0': lambda t, w=w: np.tile(w, (len(t), 1)), 'C1': _scalloped(tips[k], tips[k + 1], w, depth),
                    'D0': _line(w, tips[k]), 'D1': _line(w, tips[k + 1])})
    centre = (w + e + s) / 3.0
    out.append({'C0': lambda t: _arc([w, e, s], t), 'C1': _scalloped(tips[-1], att, centre, depth),
                'D0': _line(w, tips[-1]), 'D1': _line(s, att)})
    return out


def wing_membrane(spec: dict, side: int, nu: int, nv: int, spread: bool = False):
    """The membrane of one wing as one welded sheet: (verts n x 3, faces, wing_uv n x 3 = (panel, u, v)). Each panel is
    an nu x nv grid; panels share their finger edges and the wrist. Build it folded (the rest pose: the skin is bound
    there); `spread=True` is for previews only."""
    panels = wing_panels(spec, side, spread)
    uu = np.linspace(0.0, 1.0, nu + 1)
    vv = np.linspace(0.0, 1.0, nv + 1)
    U_, V_ = np.meshgrid(uu, vv, indexing='ij')
    verts, uvs, faces = [], [], []
    index: dict[tuple, int] = {}
    for pi, pan in enumerate(panels):
        P = _coons(pan['C0'], pan['C1'], pan['D0'], pan['D1'], U_.ravel(), V_.ravel()).reshape(nu + 1, nv + 1, 3)
        ids = np.empty((nu + 1, nv + 1), np.int64)
        for j in range(nu + 1):
            for i in range(nv + 1):
                key = tuple(int(x) for x in np.round(P[j, i] / 1e-5))
                if key not in index:
                    index[key] = len(verts)
                    verts.append(P[j, i])
                    uvs.append((float(pi), uu[j], vv[i]))
                ids[j, i] = index[key]
        for j in range(nu):
            for i in range(nv):
                f = list(dict.fromkeys([int(ids[j, i]), int(ids[j + 1, i]), int(ids[j + 1, i + 1]), int(ids[j, i + 1])]))
                if len(f) >= 3:
                    faces.append(f)
    return np.array(verts), faces, np.array(uvs)


def wing_relief(wuv: np.ndarray, n_fingers: int, veins: int = 3) -> np.ndarray:
    """0..1 per membrane point: ridges along the finger bones and the arm edge, and fine veins fanning between them
    (the high source's relief, baked into the membrane's normal map; handy for the paint too)."""
    panel, u, v = wuv[:, 0], wuv[:, 1], wuv[:, 2]
    body = panel > n_fingers - 1.5
    ridge = np.exp(-(u / 0.035) ** 2) + np.where(body, np.exp(-(v / 0.04) ** 2), np.exp(-((1 - u) / 0.035) ** 2))
    fu = (u * veins) % 1.0
    vein = 0.35 * np.exp(-((fu - 0.5) / 0.05) ** 2) * smooth(0.12, 0.5, v) * (1 - smooth(0.85, 1.0, v))
    return np.clip(ridge + vein, 0, 1)


def wing_membrane_weights(wuv: np.ndarray, spec: dict, side: int, hub: float = 0.35) -> dict[str, np.ndarray]:
    """Skin weights for membrane points from their wing_uv (panel, u, v): between two fingers they blend across u from
    one finger bone to the next, and toward the wrist (bone 2) near the hub; the last panel blends from the last finger
    to the parent (the body line), its arm edge on bones 2 -> 1 -> parent. Each weight is a Coons blend of its edges'
    weights, so shared edges agree and the sheet follows the bones smoothly when the wing opens."""
    names = wing_bone_names(spec, side)
    b1, b2, fing = names[0], names[1], names[2:]
    par = spec.get('parent', 'chest')
    q = wing_points(spec, side)
    la = float(np.linalg.norm(q['elbow'] - q['wrist']))
    ue = la / max(la + float(np.linalg.norm(q['shoulder'] - q['elbow'])), 1e-9)
    panel = np.round(wuv[:, 0]).astype(int)
    u, v = wuv[:, 1].astype(np.float64), wuv[:, 2].astype(np.float64)
    bones = [par, b1, b2] + fing
    W = {b: np.zeros(len(u)) for b in bones}
    sv = smooth(0.0, hub, v)
    z1, o1 = np.zeros(1), np.ones(1)

    def val(d: dict, b: str, n: int) -> np.ndarray:
        x = d.get(b, 0.0)
        return np.broadcast_to(np.asarray(x, np.float64), (n,)) if np.ndim(x) else np.full(n, float(x))

    def add(mask, C0, C1, D0, D1):
        uu, vv, ss = u[mask], v[mask], sv[mask]
        n = len(uu)
        for b in bones:
            c0, c1 = val(C0(uu), b, n), val(C1(uu), b, n)
            d0, d1 = val(D0(vv, ss), b, n), val(D1(vv, ss), b, n)
            k00, k10 = float(val(C0(z1), b, 1)[0]), float(val(C0(o1), b, 1)[0])
            k01, k11 = float(val(C1(z1), b, 1)[0]), float(val(C1(o1), b, 1)[0])
            W[b][mask] = ((1 - vv) * c0 + vv * c1 + (1 - uu) * d0 + uu * d1
                          - ((1 - uu) * (1 - vv) * k00 + uu * (1 - vv) * k10 + (1 - uu) * vv * k01 + uu * vv * k11))

    K = len(fing)
    for k in range(K - 1):
        m = panel == k
        if m.any():
            add(m, lambda t: {b2: np.ones_like(t)}, lambda t, k=k: {fing[k]: 1 - t, fing[k + 1]: t},
                lambda t, s, k=k: {b2: 1 - s, fing[k]: s}, lambda t, s, k=k: {b2: 1 - s, fing[k + 1]: s})
    m = panel >= K - 1
    if m.any():
        def arm(t):
            t1 = smooth(ue - 0.08, ue + 0.08, t)
            t2 = smooth(0.8, 1.0, t)
            return {b2: 1 - t1, b1: t1 * (1 - t2), par: t2}
        add(m, arm, lambda t: {fing[-1]: 1 - t, par: t}, lambda t, s: {b2: 1 - s, fing[-1]: s}, lambda t, s: {par: np.ones_like(t)})
    for b in bones:
        W[b] = np.clip(W[b], 0, None)
    tot = np.maximum(sum(W.values()), 1e-9)
    return {b: w / tot for b, w in W.items()}


def wing_fin_regions(co: np.ndarray, attr, names: list[str], spec: dict) -> list:
    """Weight regions for a recipe's fin_weight_regions: every lo_fins point with wing_side +-1 (made by
    lib.surface.wing_membrane) is skinned by wing_membrane_weights. Other membranes (wing_side 0) are left to the caller."""
    side = attr('wing_side')
    wuv = attr('wing_uv')
    regs = []
    for s in (1, -1):
        on = np.abs(side - s) < 0.1
        if on.any():
            regs.append((on, wing_membrane_weights(wuv[on], spec, s)))
    return regs


def wing_limb_segments(spec: dict, side: int) -> list[tuple]:
    """(bone, head, tail) of one wing's bones at rest, for segment_weights (the arm and finger tubes, claws on them)."""
    return [(b, h, t) for b, h, t, _p in wing_bones(spec, side)]


# ----------------------------------------------------------------------------- hard plates (cobbles, scales)
def plate_layout(p: np.ndarray, n: np.ndarray, spacing, radius, height, seed: int, flow=None, aspect: float = 1.0,
                 wobble: float = 0.12, max_candidates: int = 60000) -> dict:
    """Place hard plates (cobblestones, scales, bark tiles) on a surface given as sample points `p` and normals `n` (the
    high body's vertices, or lib.surface.scatter's points): a Poisson set, no two centres closer than their spacing.
    `spacing`, `radius` and `height` are numbers or per-point arrays (spacing NaN = no plate there). `flow` (per-point
    unit tangents, e.g. the recipe's comb direction) orients each plate's long axis (`aspect` = long / across) and, for
    scales, which edge is raised; else a random tangent. `wobble` roughens every outline (chipped stones). Returns
    arrays: c (centre), n (normal), t (long axis), a (long radius), b (across), h (height), harm (outline harmonics).
    Deterministic for a seed and the same points: call it once and keep the result for the high and the low body."""
    rng = np.random.default_rng(seed)
    p, n = v3(p).reshape(-1, 3), v3(n).reshape(-1, 3)
    m = len(p)
    sp = np.broadcast_to(np.asarray(spacing, np.float64), (m,)).copy()
    rad = np.broadcast_to(np.asarray(radius, np.float64), (m,)).copy()
    hgt = np.broadcast_to(np.asarray(height, np.float64), (m,)).copy()
    ok = np.nonzero(np.isfinite(sp) & (sp > 0))[0]
    if len(ok) > max_candidates:
        ok = np.sort(rng.choice(ok, max_candidates, replace=False))
    order = ok[rng.permutation(len(ok))]
    cell = float(np.max(sp[ok])) if len(ok) else 1.0
    grid: dict[tuple, list[int]] = {}
    keep: list[int] = []
    for i in order:
        q = p[i]
        key = (int(q[0] // cell), int(q[1] // cell), int(q[2] // cell))
        clash = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        r = 0.5 * (sp[i] + sp[j])
                        d = p[j] - q
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
    k = len(keep)
    nn = n[keep] / np.maximum(np.linalg.norm(n[keep], axis=1, keepdims=True), 1e-9)
    g = v3(flow).reshape(-1, 3)[keep].copy() if flow is not None else rng.normal(0, 1, (k, 3))
    g = g - nn * (g * nn).sum(axis=1, keepdims=True)
    bad = np.linalg.norm(g, axis=1) < 1e-6
    if bad.any():
        alt = np.cross(nn[bad], np.array([0.0, 0.0, 1.0]))
        alt[np.linalg.norm(alt, axis=1) < 1e-6] = (1.0, 0.0, 0.0)
        g[bad] = alt
    t = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
    jit = 1.0 + 0.12 * np.clip(rng.normal(0, 1, k), -2, 2)
    a = rad[keep] * jit * np.sqrt(aspect)
    b = rad[keep] * jit / np.sqrt(aspect)
    h = hgt[keep] * (1.0 + 0.15 * np.clip(rng.normal(0, 1, k), -2, 2))
    amp = rng.uniform(0.3, 1.0, (k, 3)) * wobble * np.array([0.6, 0.35, 0.2])
    harm = np.stack([amp, rng.uniform(0, 2 * np.pi, (k, 3))], axis=2)
    return {'c': p[keep], 'n': nn, 't': t, 'a': a, 'b': b, 'h': h, 'harm': harm}


def plate_field(co: np.ndarray, vn: np.ndarray, plates: dict, shape: str = 'cobble', scale: float = 1.0,
                inset: float = 0.0, edge_soft: float = 0.0) -> dict[str, np.ndarray]:
    """The plates as a height field over a mesh's vertices: h (metres to push each vertex out along its normal; the
    highest plate wins where they overlap), mask (0..1 inside a plate), rim (0..1 at a plate's edge and between plates:
    crevices, moss, a scale's dark outline), top (0..1 toward a plate's crown, or a scale's raised free edge: wear,
    lichen, highlights), pid (the winning plate, -1 for none; plate_hash(pid) gives a per-plate random number).
    `shape`: 'cobble' = rounded stones with steep sides; 'scale' = shields raised toward their trailing edge (along the
    plate's t, i.e. the flow), so each one overlaps the next. `scale` multiplies the heights (e.g. 0.85 for the low
    body); `inset` sinks the ground between plates (the grooves) by that many metres. `edge_soft` 0..1 rounds the plates'
    walls (0: the steep stones as before; 1: a soft dome) where steep walls stretch a voxel body."""
    co, vn = v3(co).reshape(-1, 3), v3(vn).reshape(-1, 3)
    nv_ = len(co)
    best = np.full(nv_, -np.inf)
    pid = np.full(nv_, -1, np.int64)
    rho_w = np.full(nv_, 2.0)
    ul_w = np.zeros(nv_)
    k = len(plates['c'])
    if k == 0:
        z = np.zeros(nv_)
        return {'h': z - inset, 'mask': z, 'rim': z + 1.0, 'top': z, 'pid': pid}
    R = np.maximum(plates['a'], plates['b']) * (1.0 + np.abs(plates['harm'][:, :, 0]).sum(axis=1))
    cell = float(R.max())
    key = np.floor(co / cell).astype(np.int64) + (1 << 20)
    kk = (key[:, 0] * (1 << 21) + key[:, 1]) * (1 << 21) + key[:, 2]
    order = np.argsort(kk, kind='stable')
    sk = kk[order]
    offs = np.array([(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)], np.int64)
    for i in range(k):
        c = plates['c'][i]
        ck = np.floor(c / cell).astype(np.int64) + (1 << 20) + offs
        keys = (ck[:, 0] * (1 << 21) + ck[:, 1]) * (1 << 21) + ck[:, 2]
        lo = np.searchsorted(sk, keys, 'left')
        hi = np.searchsorted(sk, keys, 'right')
        parts = [order[a:b] for a, b in zip(lo, hi) if b > a]
        if not parts:
            continue
        idx = np.concatenate(parts)
        d = co[idx] - c
        nrm, t = plates['n'][i], plates['t'][i]
        bt = np.cross(nrm, t)
        s_, q_, r_ = d @ t, d @ bt, d @ nrm
        a, b = plates['a'][i], plates['b'][i]
        th = np.arctan2(q_ / b, s_ / a)
        hm = plates['harm'][i]
        mod = 1.0 + sum(hm[j, 0] * np.cos((j + 2) * th + hm[j, 1]) for j in range(hm.shape[0]))
        rho = np.sqrt((s_ / a) ** 2 + (q_ / b) ** 2) / mod
        near = (rho < 1.0) & (np.abs(r_) < 0.6 * max(a, b)) & ((vn[idx] @ nrm) > 0.25)
        if not near.any():
            continue
        idx, rho, ul = idx[near], rho[near], (s_ / a)[near]
        es = min(1.0, max(0.0, float(edge_soft)))
        if shape == 'scale':
            prof = np.clip(1.0 - rho ** 2, 0, 1) ** (0.5 + 0.5 * es) * (0.3 + 0.7 * np.clip((ul + 1.0) * 0.5, 0, 1))
        else:
            prof = np.clip(1.0 - rho ** 2.2, 0, 1) ** (0.4 + 0.6 * es)
        hh = plates['h'][i] * prof
        win = hh > best[idx]
        w_idx = idx[win]
        best[w_idx] = hh[win]
        pid[w_idx] = i
        rho_w[w_idx] = rho[win]
        ul_w[w_idx] = ul[win]
    inside = pid >= 0
    h = np.where(inside, best, 0.0) * scale - inset * (~inside)
    mask = np.where(inside, smooth(1.0, 0.9, rho_w), 0.0)
    rim = np.where(inside, smooth(0.72, 0.98, rho_w), 1.0)
    if shape == 'scale':
        top = np.where(inside, smooth(-0.2, 0.9, ul_w) * (1 - smooth(0.85, 1.0, rho_w)), 0.0)
    else:
        top = np.where(inside, 1.0 - smooth(0.0, 0.8, rho_w), 0.0)
    return {'h': h, 'mask': mask, 'rim': rim, 'top': top, 'pid': pid}


def plate_hash(pid: np.ndarray, seed: int = 0) -> np.ndarray:
    """0..1 per point, the same for every point of one plate (per-plate colour or roughness variation); 0.5 off plates."""
    x = (pid.astype(np.int64) * 2654435761 + seed * 40503) % 1000003
    return np.where(pid >= 0, (x % 9973) / 9972.0, 0.5)
