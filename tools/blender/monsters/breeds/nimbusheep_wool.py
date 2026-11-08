"""Nimbusheep's cloud wool (Art 2.1 Ultra; chatgpt/monsters/05-nimbusheep): a cumulus of clumps, each a puff of puffs
of puffs, voxel-united into the body as one mesh of instanced spheres (`puff_mesh`).

`layout()` places the clumps, deterministically: two shells for the body (the tall shoulders and chest in front, the
lower rump behind, 2-turnaround.png), the cap on the head with its fringe over the brow, the collar under the chin and
the little tail. No clump may reach into the face's window. Each clump is a core, a crown of sub-puffs and on every
sub-puff a few small bumps; the voxel remesh merges them into one soft cloud with creases between the puffs.

`field()` splats every puff's signed distance into an 8 mm grid once per process, keeping the nearest and second-nearest
clump and puff; `sample(points)` reads it back. The zones (wool or skin), the paint (bluish creases between the puffs,
the Stormcrown's gold rims) and the fur's flow (curls round each puff) all read it.

Metres; the monster faces −Y, Z is up, +X is its left. Nothing here knows the bake or the rig.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np

from lib import common as C
from lib import surface as S
from lib.surface import norm, smooth, v3

SEED = 51105
# round 3 (review): the head moves forward this much so the whole profile clears the chest ruff (2-turnaround side)
HEAD_DY = -0.05

# The body is two overlapping masses (outer envelopes measured on 2-turnaround.png): the tall front (shoulders and
# chest, up to z 0.86) and the lower rump (its back line falls to z 0.6 at the tail). Clump centres sit DEPTH inside.
FRONT = ((0.0, -0.16, 0.51), (0.385, 0.38, 0.37))
REAR = ((0.0, 0.1, 0.44), (0.39, 0.46, 0.36))
DEPTH = 0.088
# the cap on the head: a dome from the brow fringe (y −0.57) back to where it meets the body wool, its top at z 1.13
CAP = ((0.0, -0.33 + HEAD_DY, 0.9), (0.265, 0.24, 0.17))
CAP_DEPTH = 0.07
# no wool may reach into the face: an ellipse in x–z (the face's outline seen from the front) in front of y = −0.40
FACE_WIN = {'c': (0.0, 0.735), 'r': (0.205, 0.132), 'y': -0.40 + HEAD_DY}
# nor in front of the ears, which hang from under the horns in front of the body's wool (2-turnaround.png front, side)
EAR_WIN = {'c': (0.29, 0.655), 'r': (0.135, 0.085), 'y': -0.255 + HEAD_DY}
# the tail: a small puff on the rump (a sheep's tail, hidden in the wool; the tail bones wag it)
TAIL_C = (0.0, 0.47, 0.57)
TAIL_N = (0.0, 0.85, 0.2)

REGIONS = {'body': 0, 'cap': 1, 'fringe': 2, 'collar': 3, 'tail': 4}

_LAYOUT: dict = {}
_FIELD: dict = {}


# ----------------------------------------------------------------------------- the clumps
def _ell_normal(p: np.ndarray, c, r) -> np.ndarray:
    return norm((p - v3(c)) / v3(r) ** 2)


def _shell(c, r, depth: float, n: int, rng) -> tuple[np.ndarray, np.ndarray]:
    """Candidate clump centres on an envelope shrunk by `depth`, with the envelope's outward normals."""
    d = norm(rng.normal(size=(n, 3)))
    ri = v3(r) - depth
    p = v3(c) + d * ri
    return p, _ell_normal(p, c, ri)


def _in_face(p: np.ndarray, grow: float = 0.0) -> np.ndarray:
    fc, fr = FACE_WIN['c'], FACE_WIN['r']
    e = ((p[..., 0] - fc[0]) / (fr[0] + grow)) ** 2 + ((p[..., 2] - fc[1]) / (fr[1] + grow)) ** 2
    hit = (e < 1.0) & (p[..., 1] < FACE_WIN['y'])
    ec, er = EAR_WIN['c'], EAR_WIN['r']
    e = ((np.abs(p[..., 0]) - ec[0]) / er[0]) ** 2 + ((p[..., 2] - ec[1]) / er[1]) ** 2
    return hit | ((e < 1.0) & (p[..., 1] < EAR_WIN['y']))


_DIRS = norm(np.random.default_rng(7).normal(size=(160, 3)))


def _hits_face(c: np.ndarray, R: float) -> bool:
    """Would a clump of radius R at c (its puffs reach about 1.05 R) cover any of the face?"""
    return bool(_in_face(c[None] + _DIRS * R * 1.06).any())


def _settle(c: np.ndarray, n: np.ndarray, R: float, push=(0.0, 0.022, -0.004)) -> tuple[np.ndarray, float] | None:
    """Move a clump that covers the face along `push` (back for the body, up for the cap and its fringe, down for the
    collar), shrinking it a little, until it clears; None if it never does."""
    for _ in range(12):
        if not _hits_face(c, R):
            return c, R
        c = c + v3(push) + n * -0.003
        R *= 0.975
    return None


def _poisson(P, N, R, gap: float, kept: list, mirror: bool, rng, region: int, jitter: float = 0.012, push=(0.0, 0.022, -0.004)) -> None:
    """Greedy Poisson over candidates (P, N, R), against everything kept; with `mirror`, candidates on the left are
    mirrored to the right with their own jitter (the cloud is near-symmetric, as in the turnaround)."""
    order = rng.permutation(len(P))
    for i in order:
        p, nn, r = P[i], N[i], float(R[i])
        if mirror and p[0] < -0.004:
            continue
        cand = [(p, nn, r)]
        if mirror and p[0] > 0.045:
            j = rng.normal(0, jitter, 3)
            q = v3((-p[0] + j[0], p[1] + j[1], p[2] + j[2] * 0.6))
            cand.append((q, nn * v3((-1, 1, 1)), r * rng.uniform(0.92, 1.08)))
        ok = []
        for q, qn, qr in cand:
            s = _settle(q, qn, qr, push)
            if s is None:
                ok = []
                break
            ok.append((s[0], qn, s[1]))
        if not ok:
            continue
        clash = False
        for q, _qn, qr in ok:
            for k in kept:
                if np.linalg.norm(k[0] - q) < gap * (k[2] + qr):
                    clash = True
                    break
            if clash:
                break
        if clash:
            continue
        for q, qn, qr in ok:
            kept.append((q, norm(qn[None])[0], qr, region))


def _body_radius(p: np.ndarray, n: np.ndarray, rng) -> np.ndarray:
    """Clump radius: bigger on the back and shoulders, smaller underneath and on the chest under the chin."""
    up = smooth(0.0, 0.7, n[:, 2])
    down = smooth(-0.15, -0.75, n[:, 2])
    chest = smooth(-0.3, -0.5, p[:, 1]) * smooth(0.75, 0.55, p[:, 2])
    R = 0.1 + 0.014 * up - 0.03 * down - 0.014 * chest
    return R * rng.uniform(0.88, 1.12, len(p))


def _forehead_y(x: float, z: float) -> float:
    """The face's skin at (x, z) seen from the front: the head and brow ellipsoids of the recipe (moved by HEAD_DY)."""
    best = 0.0
    for k, ((cx, cy, cz), (rx, ry, rz)) in enumerate((((0.0, -0.36, 0.765), (0.19, 0.18, 0.185)), ((0.0, -0.425, 0.83), (0.15, 0.1, 0.08)))):
        q = 1.0 - ((x - cx) / rx) ** 2 - ((z - cz) / rz) ** 2
        if k == 0:
            q = max(q, 0.02)          # past the head's width: its side, so the end puffs sit on the temples, not in front
        if q > 0:
            best = min(best, cy + HEAD_DY - ry * math.sqrt(q))
    return best


def layout() -> dict:
    """The clumps (centre, radius, outward normal, region) and their puffs (centre, radius, level, clump), cached."""
    if _LAYOUT:
        return _LAYOUT
    rng = np.random.default_rng(SEED)
    kept: list = []
    # the tail first, then the cap and its fringe, the collar, then the body fills round them
    kept.append((v3(TAIL_C), norm(v3(TAIL_N)[None])[0], 0.064, REGIONS['tail']))
    P, N = _shell(*CAP, CAP_DEPTH, 6000, rng)
    top = (P[:, 2] > 0.86) | (P[:, 1] > -0.3)
    P, N = P[top], N[top]
    R = (0.07 + 0.008 * smooth(0.95, 1.05, P[:, 2])) * rng.uniform(0.88, 1.1, len(P))
    _poisson(P, N, R, 0.58, kept, True, rng, REGIONS['cap'], push=(0.0, 0.004, 0.012))
    # the crown: one bigger puff on top (the turnaround's tallest tuft)
    kept.append((v3((0.0, -0.36 + HEAD_DY, 0.985)), v3((0.0, -0.15, 1.0)) / np.linalg.norm((0.0, -0.15, 1.0)), 0.07, REGIONS['cap']))
    # the fringe over the brow: small puffs along the hairline, overhanging the forehead
    for k, t in enumerate(np.linspace(-1.0, 1.0, 9)):
        big = k % 2 == 0
        x = 0.2 * t
        z = (0.89 if big else 0.905) - 0.06 * t * t
        # round 3b: centred on the forehead's skin (no overhang, so no pocket under the fringe)
        y = _forehead_y(x, z) + 0.004
        c = v3((x, y, z))
        nn = norm(v3((x * 1.6, -1.0, 0.3))[None])[0]
        s = _settle(c, nn, (0.046 if big else 0.036) - 0.005 * t * t, (0.0, 0.0, 0.006))
        if s is not None:
            kept.append((s[0], nn, s[1], REGIONS['fringe']))
    # the collar: a ring of puffs under the chin and up the sides of the face, behind the ears
    for t in np.linspace(-1.0, 1.0, 7):
        a = t * math.radians(66)
        x = 0.24 * math.sin(a)
        y = -0.455 + 0.12 * (1 - math.cos(a))
        z = 0.5 + 0.04 * (1 - math.cos(a))
        c = v3((x, y, z))
        nn = norm(v3((math.sin(a), -math.cos(a) * 0.9, 0.25))[None])[0]
        s = _settle(c, nn, 0.072, (0.0, 0.006, -0.01))
        if s is not None:
            kept.append((s[0], nn, s[1], REGIONS['collar']))
    for env in (FRONT, REAR):
        P, N = _shell(*env, DEPTH, 9000, rng)
        # the other mass's inside is not a surface: drop candidates buried in it
        other = REAR if env is FRONT else FRONT
        inside = S.in_ellipsoid(P, other[0], tuple(r - DEPTH - 0.025 for r in other[1])) < 1.0
        P, N = P[~inside], N[~inside]
        # the belly between the legs is wool too, but keep the lowest puffs off the hooves
        low = P[:, 2] > 0.23
        P, N = P[low], N[low]
        R = _body_radius(P, N, rng)
        _poisson(P, N, R, 0.52, kept, True, rng, REGIONS['body'])
    C_ = np.array([k[0] for k in kept])
    N_ = np.array([k[1] for k in kept])
    R_ = np.array([k[2] for k in kept])
    G_ = np.array([k[3] for k in kept], np.int32)
    puffs = _puffs(C_, N_, R_, rng)
    _LAYOUT.update(c=C_, n=N_, R=R_, region=G_, **puffs)
    C.log(f'wool layout: {len(C_)} clumps, {len(puffs["pc"])} puffs')
    return _LAYOUT


def _basis(n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = v3((0, 0, 1)) if abs(n[2]) < 0.9 else v3((1, 0, 0))
    t1 = norm(np.cross(n, a)[None])[0]
    return t1, np.cross(n, t1)


def _puffs(Cc: np.ndarray, Nc: np.ndarray, Rc: np.ndarray, rng) -> dict:
    """Every clump: a core, a crown of 7–9 sub-puffs reaching about R, and 3–5 small bumps on each sub-puff."""
    pc, pr, lv, cl = [], [], [], []

    def add(c, r, level, k):
        pc.append(c)
        pr.append(r)
        lv.append(level)
        cl.append(k)

    for k, (c, n, R) in enumerate(zip(Cc, Nc, Rc)):
        add(c - n * 0.1 * R, 0.8 * R, 0, k)
        t1, t2 = _basis(n)
        ks = 12 if R > 0.085 else 9
        az0 = rng.uniform(0, 2 * math.pi)
        dirs = [norm((n + rng.normal(0, 0.12, 3))[None])[0]]
        for i in range(ks - 1):
            az = az0 + 2 * math.pi * i / (ks - 1) + rng.normal(0, 0.18)
            pol = math.radians(rng.uniform(30, 66) if i % 2 else rng.uniform(42, 72))
            d = n * math.cos(pol) + (t1 * math.cos(az) + t2 * math.sin(az)) * math.sin(pol)
            dirs.append(d)
        for d in dirs:
            # lobes: each sub-puff stands proud of the clump's ball, so a clump reads as a cauliflower, not a cotton ball
            rs = R * rng.uniform(0.36, 0.46)
            dist = R * rng.uniform(0.97, 1.06) - 0.82 * rs
            sc = c + d * dist
            add(sc, rs, 1, k)
            m = int(rng.integers(4, 6)) if rs > 0.03 else 3
            out = norm((d * 0.7 + n * 0.3)[None])[0]
            u1, u2 = _basis(out)
            a0 = rng.uniform(0, 2 * math.pi)
            for j in range(m):
                a = a0 + 2 * math.pi * j / m + rng.normal(0, 0.3)
                pol = math.radians(rng.uniform(25, 62))
                d2 = out * math.cos(pol) + (u1 * math.cos(a) + u2 * math.sin(a)) * math.sin(pol)
                r2 = rs * rng.uniform(0.4, 0.5)
                add(sc + d2 * (rs - 0.55 * r2), r2, 2, k)
    return {'pc': np.array(pc), 'pr': np.array(pr), 'plevel': np.array(lv, np.int32), 'pclump': np.array(cl, np.int32)}


# ----------------------------------------------------------------------------- the mesh joined into the body
def _ico(subdiv: int):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    v = np.array([x.co[:] for x in bm.verts])
    f = [tuple(x.index for x in face.verts) for face in bm.faces]
    bm.free()
    return v, f


def puff_mesh(name: str = 'wool_puffs') -> bpy.types.Object:
    """All the puffs as one mesh of closed icospheres (overlapping shells; the voxel remesh unites them)."""
    L = layout()
    objs = []
    for level, sub in ((0, 3), (1, 3), (2, 2)):
        on = L['plevel'] == level
        if not on.any():
            continue
        tv, tf = _ico(sub)
        verts = L['pc'][on][:, None, :] + L['pr'][on][:, None, None] * tv[None]
        me = S.mesh_from_template(f'{name}_{level}', verts, tf)
        ob = bpy.data.objects.new(me.name, me)
        C.link_obj(ob)
        objs.append(ob)
    from lib import mesh as M
    ob = M.join_meshes(objs, name)
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return ob


# ----------------------------------------------------------------------------- the field
GRID_LO = v3((-0.5, -0.74, -0.04))
GRID_HI = v3((0.5, 0.74, 1.24))
CELL = 0.008
FAR = 0.08
BAND = 0.045


def field() -> dict:
    """Per grid cell: d1 / d2 (the nearest and second-nearest clump's signed distance), cid (the nearest clump),
    p1 / p2 / pid (the same per puff). Built once per process (a few seconds)."""
    if _FIELD:
        return _FIELD
    L = layout()
    shape = tuple(int(math.ceil((GRID_HI[i] - GRID_LO[i]) / CELL)) + 1 for i in range(3))
    d1 = np.full(shape, FAR, np.float32)
    d2 = np.full(shape, FAR, np.float32)
    cid = np.full(shape, -1, np.int32)
    p1 = np.full(shape, FAR, np.float32)
    p2 = np.full(shape, FAR, np.float32)
    pid = np.full(shape, -1, np.int32)
    ax = [GRID_LO[i] + np.arange(shape[i], dtype=np.float32) * CELL for i in range(3)]
    with C.Timer('wool field'):
        for k in range(len(L['c'])):
            idx = np.nonzero(L['pclump'] == k)[0]
            pc, pr = L['pc'][idx], L['pr'][idx]
            lo = np.floor((np.min(pc - pr[:, None], axis=0) - BAND - GRID_LO) / CELL).astype(int)
            hi = np.ceil((np.max(pc + pr[:, None], axis=0) + BAND - GRID_LO) / CELL).astype(int) + 1
            lo = np.clip(lo, 0, np.array(shape) - 1)
            hi = np.clip(hi, 1, np.array(shape))
            sl = tuple(slice(lo[i], hi[i]) for i in range(3))
            X = ax[0][sl[0]][:, None, None]
            Y = ax[1][sl[1]][None, :, None]
            Z = ax[2][sl[2]][None, None, :]
            P1, P2, PID = p1[sl], p2[sl], pid[sl]
            dc = np.full(P1.shape, FAR, np.float32)
            for j, (c, r) in enumerate(zip(pc, pr)):
                d = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2) - np.float32(r)
                closer = d < P1
                P2 = np.where(closer, P1, np.minimum(P2, d))
                PID = np.where(closer, np.int32(idx[j]), PID)
                P1 = np.where(closer, d, P1)
                dc = np.minimum(dc, d)
            p1[sl], p2[sl], pid[sl] = P1, P2, PID
            D1, D2, CID = d1[sl], d2[sl], cid[sl]
            closer = dc < D1
            d2[sl] = np.where(closer, D1, np.minimum(D2, dc))
            cid[sl] = np.where(closer, np.int32(k), CID)
            d1[sl] = np.where(closer, dc, D1)
    _FIELD.update(d1=d1, d2=d2, cid=cid, p1=p1, p2=p2, pid=pid, shape=np.array(shape))
    return _FIELD


def _trilinear(g: np.ndarray, p: np.ndarray) -> np.ndarray:
    shape = np.array(g.shape)
    f = (p - GRID_LO) / CELL
    i0 = np.clip(np.floor(f).astype(int), 0, shape - 2)
    t = np.clip(f - i0, 0.0, 1.0)
    out = np.zeros(len(p))
    for dx in (0, 1):
        wx = t[:, 0] if dx else 1 - t[:, 0]
        for dy in (0, 1):
            wy = t[:, 1] if dy else 1 - t[:, 1]
            for dz in (0, 1):
                wz = t[:, 2] if dz else 1 - t[:, 2]
                out += wx * wy * wz * g[i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz]
    return out


def _nearest(g: np.ndarray, p: np.ndarray) -> np.ndarray:
    shape = np.array(g.shape)
    i = np.clip(np.round((p - GRID_LO) / CELL).astype(int), 0, shape - 1)
    return g[i[:, 0], i[:, 1], i[:, 2]]


def sample(p: np.ndarray, chunk: int = 400000) -> dict:
    """The field at points: d1, d2, p1, p2 (metres), cid, pid (−1 = far from all wool)."""
    F = field()
    out = {k: np.empty(len(p)) for k in ('d1', 'd2', 'p1', 'p2')}
    out['cid'] = np.empty(len(p), np.int32)
    out['pid'] = np.empty(len(p), np.int32)
    for a in range(0, len(p), chunk):
        q = p[a:a + chunk]
        for k in ('d1', 'd2', 'p1', 'p2'):
            out[k][a:a + chunk] = _trilinear(F[k], q)
        out['cid'][a:a + chunk] = _nearest(F['cid'], q)
        out['pid'][a:a + chunk] = _nearest(F['pid'], q)
    return out


# ----------------------------------------------------------------------------- Stormcrown's crown (a variant-only prop)
# "three taller cloud puffs on its head like a crown" (PROMPTS.md, variant-stormcrown-nimbusheep.png): three towers of
# stacked puffs rising from the cap, the middle one tallest; their feet sink into the cap's wool
CROWN_TOWERS = [
    # round 3 (review): three puffs rising out of the tuft on one wide base (no neck): the base is mostly sunk in the cap
    [((0.0, -0.36 + HEAD_DY, 1.03), 0.125)],
    [((0.0, -0.372 + HEAD_DY, 1.13), 0.088)],
    [((0.118, -0.355 + HEAD_DY, 1.1), 0.075)],
    [((-0.118, -0.355 + HEAD_DY, 1.1), 0.075)],
]
_CROWN: dict = {}


def crown_layout() -> dict:
    if not _CROWN:
        rng = np.random.default_rng(SEED + 7)
        cs, ns, rs = [], [], []
        for tower in CROWN_TOWERS:
            for c, r in tower:
                c = v3(c)
                n = norm(v3((c[0] * 3.0, -0.25, 0.9))[None])[0]
                cs.append(c)
                ns.append(n)
                rs.append(r)
        _CROWN.update(c=np.array(cs), n=np.array(ns), R=np.array(rs), **_puffs(np.array(cs), np.array(ns), np.array(rs), rng))
    return _CROWN


def build_crown(name: str, high: bool, quick: bool = False) -> bpy.types.Object:
    """The crown as one smooth closed mesh: its puffs voxel-united, a fine fibre ripple on the high copy (baked), the
    game copy decimated."""
    L = crown_layout()
    tv, tf = _ico(3)
    verts = L['pc'][:, None, :] + L['pr'][:, None, None] * tv[None]
    me = S.mesh_from_template(f'{name}_puffs', verts, tf)
    src = bpy.data.objects.new(me.name, me)
    C.link_obj(src)
    ob = S.build_body(name, [], 0.004 if (high and not quick) else 0.006, 3, extra=[src])
    co, vn = S.mesh_arrays(ob)
    if high:
        f = co * 260.0
        rip = (np.sin(f[:, 0] + 1.3 * np.sin(f[:, 1] * 0.7)) * np.sin(f[:, 1] + 1.1 * np.sin(f[:, 2] * 0.8))
               * np.sin(f[:, 2] + 0.9 * np.sin(f[:, 0] * 0.6)))
        S.set_positions(ob, co + vn * (0.0012 * rip)[:, None])
    else:
        S.decimate_to(ob, 2600, smooth_after=0.0)
    ob['prop'] = 'crown'
    return ob


def crown_paint(ob: bpy.types.Object, wool_hex: str, crease_hex: str, rim_hex: str | None) -> np.ndarray:
    """Linear RGB per vertex: the wool, its creases, and (Stormcrown) the gold glowing at the puffs' edges."""
    L = crown_layout()
    co, vn = S.mesh_arrays(ob)
    d = np.linalg.norm(co[:, None, :] - L['pc'][None], axis=2) - L['pr'][None]
    order = np.argsort(d, axis=1)
    i1, i2 = order[:, 0], order[:, 1]
    d1 = d[np.arange(len(co)), i1]
    d2 = d[np.arange(len(co)), i2]
    crease = smooth(0.012, 0.002, d2 - d1)
    lin = lambda h: v3(C.lin_rgb(h))  # noqa: E731
    rgb = lin(wool_hex)[None] * (1 - 0.75 * crease[:, None]) + lin(crease_hex)[None] * (0.75 * crease[:, None])
    if rim_hex:
        # gold along the edges of the small puffs (a fine glowing lace, as where sunlight breaks through), not rings
        # round each tower's puffs (round 1 read as stacked beads)
        # a thin rim tracing the edge of each sub-puff (round 3, as on the body)
        lv1 = np.nonzero(L['plevel'] == 1)[0]
        d1 = np.linalg.norm(co[:, None, :] - L['pc'][lv1][None], axis=2) - L['pr'][lv1][None]
        j = lv1[np.argmin(d1, axis=1)]
        own1 = (vn * norm(co - L['pc'][j])).sum(1)
        rim = smooth(0.72, 0.38, own1) * smooth(-0.2, 0.05, own1) * (1 - 0.5 * crease)
        g = np.clip(0.9 * rim, 0, 1)[:, None]
        rgb = rgb * (1 - g) + lin(rim_hex)[None] * g
    return rgb
