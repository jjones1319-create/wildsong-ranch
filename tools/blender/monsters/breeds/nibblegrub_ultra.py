"""Nibblegrub at the Art 2.1 Ultra tier (chatgpt/monsters/27-nibblegrub; CONTENT entry 12): a chubby five-segment larva
with tiny legs, big round cheeks always chewing, and stubby antenna nubs, on the insect plan (plans/insect.py;
RECIPE.md "Insect plan").

    npm run art:shape -- nibblegrub
    tools/blender/slot.sh npm run art:ultra -- nibblegrub --blender --stages build,bake,rig,clips,export,review > tools/blender/out/nibblegrub-build1.log 2>&1 &

Size: HEIGHT_UNITS 120 (the card: about 0.8 × Puddlepup's height, 1.5 × its length) → 0.80 m to the antenna balls'
tops, 1.14 m from the cheeks to the tail's end (2-turnaround).

The parts (all one body, lo_body; no props, no cards):
  - the head: a big round cranium over the jowl, big shiny pink cheeks sunk into the face up to the eyes, a small
    muzzle over a puffy 'w' lip and a little open mouth (a pocket cut into the head: dark inside, a pink tongue, two
    little teeth) that chews, brown brows, two antenna nubs (a short curved stalk, a round peach ball) on the crown;
  - the trunk: four plump segments pinched deep between them (a loft of thin discs, so the creases are soft valleys)
    with crisp gold bands in the creases, one smooth cream belly underneath, a round tail dome;
  - six stubby straight legs (three pairs, the card) under the front, each with three round peach toe beans;
  - the eyes: big glossy lenses (a warm brown iris round a large pupil, a white crescent, two catchlights) seated
    under a soft lid ring; under each lens the shut lid lies flat with its lash line.
The coat: velvet: a fine directional nap in the high source and a strong grazing sheen (no locks, no cards: RECIPE.md
"Coats without fur").
Colours: CONTENT's palette and the derived ones in nibblegrub_paint.py.
Syrup Nibblegrub: amber (nibblegrub_paint.py), glossy (VARIANT_ORM: its own roughness and coat).
"""
from __future__ import annotations

import numpy as np
from mathutils import Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import nibblegrub_form as F
from monsters.breeds.nibblegrub_form import smooth

ID = 'nibblegrub'
LOOK = 'nibblegrub-ultra'
PLAN = 'insect'
HEIGHT_UNITS = 120
PALETTE = {'body': '#F2D27A', 'belly': '#FFF0C2', 'accent': '#D9A94F', 'eye': '#3B2F2F', 'cheek': '#F29C8F'}
VARIANTS = {'syrup-nibblegrub': {'body': '#D9892E', 'belly': '#FFE2A8', 'accent': '#8C4A12', 'eye': '#3B2F2F'}}
VARIANT_ORM = {'syrup': {}}                     # glossy amber: its own roughness and coat
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')     # the recipe weights the jaw itself (body_weights)
BODY_TRIS = 66000
VOXELS = {'hi': 0.0019, 'lo': 0.0042}          # round 2: fine enough for the finer nap and the mouth's edges
ATLAS_STRIP = 0
ATLAS_MARGIN = 0.006                            # the pink cheeks' islands never bleed into the yellow at small mips
ATLAS_DENSITY = {'lo_eyes': 1.3}
NORMAL_SCALE = 0.4                              # round 3: the nap softer still (it read as clay stipple)
BODY_SHEEN = 1.0                                # round 3: velvet that lightens toward the silhouette (peach fuzz)
AO_FLOOR = 0.55                                 # the creases between the segments a soft warm shade, never black slits
AO_SOFTEN = 2.0
BLINK_CLOSED = (0.75, 0.05, 0.1)                # squashed onto the lash line and sunk under the flush skin (polish: narrower)
MOUTH_SOCKET = (0.0, -0.5, 0.38)
FACE_NOTE = ('Baked face: big glossy lenses under a soft lid ring (a warm brown iris round a large dark pupil, a white '
             'crescent at the outer bottom, two catchlights, a dark upper lash), soft brown brows, a puffy "w" lip over '
             'a little open mouth (a pocket in the head: tongue and two little teeth) that the jaw chews open and shut, '
             'big shiny pink cheeks that move with the jaw. Blinking squashes each lens onto its lash line and sinks it '
             'under the flat shut lid painted beneath it.')
# (CalmClips scales after the plan's ground guard: never calm a bone whose turn the guard's lift depends on)
_GAIT = {'leg': 0.6, 'jaw': 0.85}               # the paddle only (a calmer tuck would lower the feet under the guard's lift)
CLIP_CALM = {'*': {'jaw': 0.85, 'head': 0.55},
             'walk': _GAIT, 'run': _GAIT, 'dash': _GAIT, 'step_fwd': _GAIT, 'step_back': _GAIT, 'strafe_l': _GAIT, 'strafe_r': _GAIT,
             'sleep': {'front': 0.75, 'rear': 0.75},
             'sit': {'head': 0.35}, 'sit_down': {'head': 0.35}, 'dizzy': {'head': 0.35},
             'hit_heavy': {'head': 0.4},          # round 1: the head's lower edge slid over the first segment
             'idle_tired': {'jaw': 0.6}, 'cast': {'jaw': 0.6},
             'strike': {'head': 1.0}}

HEAD_C = Vector(F.HEAD_C)
PROBES = ([('front.2', (0.0, -0.3, 0.024), 0.0), ('front.2', (0.0, -0.4, 0.07), 0.0), ('front.2', (0.15, -0.3, 0.045), 0.0),
           ('front.2', (-0.15, -0.3, 0.045), 0.0), ('front.1', (0.0, -0.08, 0.008), -0.002), ('chest', (0.0, 0.1, 0.008), -0.002),
           ('hips', (0.0, 0.24, 0.008), -0.002), ('rear.1', (0.0, 0.37, 0.01), -0.002), ('rear.2', (0.0, 0.49, 0.03), 0.0)]
          # each foot's toe beans' bottoms (front) and its heel
          + [(f'shin{i + 1}.{tag}', (c[0], c[1] - 0.005, 0.0015), -0.003) for i in range(3) for tag, s in (('L', 1), ('R', -1))
             for c in F.toe_centres(s, i)]
          + [(f'shin{i + 1}.{tag}', (F._m(F.leg(i)['foot'], s)[0], F.leg(i)['foot'][1] + 0.045, 0.002), -0.003)
             for i in range(3) for tag, s in (('L', 1), ('R', -1))])


def rig_p() -> dict:
    return {'form': 'crawl', 'hip': F.HIP, 'chest': F.F1, 'front': F.FRONT, 'rear': F.REAR, 'head_c': F.HEAD_C,
            'head_r': F.HEAD_R, 'head_tip': F.HEAD_TIP, 'head_reach': F.HEAD_REACH, 'jaw': F.JAW, 'jaw_open': True,
            'legs': F.LEGS, 'radius': 0.25,
            'chains': [{'name': 'antenna', 'kind': 'antenna', 'parent': 'head', 'mirror': True, 'points': F.ANTENNA}],
            'strike_style': 'roll', 'cast_style': 'spray', 'ko_style': 'back',
            # round 2: a real hop in win and hop (the win read like battle_idle), the chew opens the mouth wide enough
            # to read at 100 px, and the crawl's hump nearly twice as tall (the walk read level) (plans/insect.py `arch`)
            'hop': 1.4, 'chew': 1.5, 'arch': 1.3,
            'clip_bones': {'win': {'jaw': [(0.02, 0.5, (22.0, 0.0, 0.0))]}},
            # round 2: the roll curls into a ball (90% of the plan's full curl, over three bones each side) and rolls
            # forward like a wheel, half a turn by the impact, so the face comes up at the front of the ball (5-poses
            # attack); the wind-up already rolls it forward; it turns toward the monster's left (the strike camera)
            # round 3: a ball held from the wind-up through the impact: the front curls a little under (95 degrees over
            # its three bones), the head lifts to look out of the front of the ball, the rear rolls right round under
            # it (195 degrees), the opening (the belly, the tucked legs) underneath; it lunges forward rocking onto its
            # front, then uncurls (round 2 rolled a half turn and sat up showing its legs)
            'roll_curl': 100.0,
            'roll_bones': {'chest': (-21.6, 0.0, 0.0), 'front.1': (-21.6, 0.0, 0.0), 'front.2': (-21.6, 0.0, 0.0),
                           'head': (-100.0, 0.0, 0.0), 'hips': (-12.0, 0.0, 0.0), 'rear.1': (-12.0, 0.0, 0.0), 'rear.2': (-12.0, 0.0, 0.0)},
            'strike_bones': {'body': (-62.0, 0.0, 0.0)}, 'strike_yaw': 20.0,
            # the ground guard also keeps the jowl's bottom, the belly and the toe beans up (a pitch or a paddle pushed
            # them 1-2 cm into the ground) (plans/insect.py `probes`)
            'probes': PROBES}


def calm_group(bone: str):
    if bone in ('jaw', 'head'):
        return bone
    if bone == 'chest':
        return 'front'
    if bone == 'hips':
        return 'rear'
    pre = bone.split('.')[0]
    if pre.startswith('antenna'):
        return 'antenna'
    if pre.startswith('leg') or pre.startswith('shin'):
        return 'leg'
    if pre in ('front', 'rear'):
        return pre
    return None


# ----------------------------------------------------------------------------- the body
def all_parts():
    return F.all_parts()


def _eye_rho(co: np.ndarray) -> np.ndarray:
    out = np.full(len(co), np.inf)
    for s in (1, -1):
        e = F.eye_local(co, s)
        r = np.hypot(e[:, 0], e[:, 1])
        out = np.minimum(out, np.where(np.abs(e[:, 2]) < 2.0, r, np.inf))
    return out


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    face = (y < -0.36) & (z > 0.28) & (z < 0.68) & (np.abs(x) < 0.3)
    return {'face': face, 'eye_d': _eye_rho(co) * F.EYE_R, 'belly': z < F.belly_border(co), 'toes': F.toe_dist(co) < 0.02}


def _mouth_zone(co: np.ndarray) -> np.ndarray:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    return smooth(0.07, 0.04, np.hypot(x, (z - F.MOUTH[2]) * 1.4)) * (y < -0.42)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    rho = _eye_rho(co)
    ds, db = F.antenna_dist(co)
    keep = (0.9 * smooth(1.5, 1.2, rho) + 0.95 * _mouth_zone(co) + 0.5 * smooth(0.026, 0.018, F.toe_dist(co))
            + 0.3 * smooth(F.BALL_R + 0.02, F.BALL_R, db))
    return np.clip(keep, 0, 1)


def texel_k(fc: np.ndarray) -> np.ndarray:
    """The face gets the most texels (the brows, the mouth, the lids), the belly's underside fewer."""
    x, y, z = fc[:, 0], fc[:, 1], fc[:, 2]
    k = np.ones(len(fc))
    k = np.where((y < -0.3) & (z > 0.3), 1.5, k)
    k = np.where(_eye_rho(fc) < 1.6, 1.9, k)
    k = np.where(_mouth_zone(fc) > 0.3, 2.4, k)
    return k


# (polish) the coat unwraps from relaxed positions (streaky, stretched texels on the flank-to-belly blend and the curled
# underside); the face keeps its own unwrap
UV_SMOOTH = 40


def uv_smooth_mask(co: np.ndarray) -> np.ndarray:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    face = smooth(-0.33, -0.4, y) * smooth(0.25, 0.32, z)
    return np.clip(1.0 - face - smooth(1.6, 1.2, _eye_rho(co)), 0.0, 1.0)


# ----------------------------------------------------------------------------- the high source and the game mesh
def seat_eyes(ob, gap: float = 0.0006) -> None:
    """(polish) Each lens follows the cranium's own curve (F.lens_w: 1.2-5.7 mm proud of it), so under its footprint the
    skin only has to lie `gap` under the head's surface: flush, no socket, no lid ring (round 3's ring read as a dome
    with a rim when shut, and the flat lens's edge caught a bright rim in profile). Never raised; blended out by 1.12
    radii (the cheek's top may meet the lower rim)."""
    co, _ = S.mesh_arrays(ob)
    out = co.copy()
    moved = 0
    for s in (1, -1):
        c, _xa, _ya, look = F.eye_frame(s)
        e = F.eye_local(co, s)
        rho = np.hypot(e[:, 0], e[:, 1])
        m = (rho < 1.12) & (np.abs(e[:, 2]) < 2.5) & (np.sign(co[:, 0]) == s)
        if not m.any():
            continue
        w = e[m, 2] * F.EYE_R
        target = F.head_w(e[m, 0], e[m, 1], s) - gap
        k = smooth(1.12, 1.0, rho[m])
        new = w + k * (np.minimum(w, target) - w)
        out[m] = co[m] + look[None] * (new - w)[:, None]
        moved += int(m.sum())
    S.set_positions(ob, out)
    C.log(f'{ob.name}: eyes seated flush ({moved} vertices)')


def cut_mouth(ob) -> None:
    """A little open mouth: a pocket pressed into the head under the lip's puffs (the opening F.mouth_edges, up to
    MOUTH_DEPTH deep), so the jaw's chew opens a real mouth (round 1: a closed mouth whose chew didn't read)."""
    co, _ = S.mesh_arrays(ob)
    ins = F.mouth_inside(co)
    m = ins > 0
    if not m.any():
        return
    d = F.MOUTH_DEPTH * np.sqrt(smooth(0.0, 0.7, ins[m]))
    co[m, 1] += d
    S.set_positions(ob, co)
    C.log(f'{ob.name}: mouth cut ({int(m.sum())} vertices)')


def carve(hi_body) -> None:
    from monsters.breeds import nibblegrub_paint as PT
    from monsters.breeds import paladove_parts as PP
    chips = PP.drop_islands(hi_body, 400)
    seat_eyes(hi_body)
    cut_mouth(hi_body)
    co, vn = S.mesh_arrays(hi_body)
    rho = _eye_rho(co)
    cheek = smooth(1.3, 1.05, F.cheek_q(co))
    toe = smooth(F.TOE_R + 0.006, F.TOE_R + 0.002, F.toe_dist(co))
    # the nap: fine directional fibres, none on the shiny cheeks, the beans, round the eyes or in the mouth, less on
    # the muzzle and the lip
    calm = np.maximum.reduce([cheek, toe, smooth(1.5, 1.15, rho), smooth(0.0, 0.2, F.mouth_inside(co)) + _mouth_zone(co) * 0.6])
    calm = np.maximum(calm, 0.5 * smooth(1.6, 1.0, F.ell_q(co, F.MUZZLE)))
    d = 0.0005 * PT.fuzz(co) * (1.0 - np.clip(calm, 0, 1))
    S.set_positions(hi_body, co + vn * d[:, None])
    co, _ = S.mesh_arrays(hi_body)
    S.base_attrs(hi_body, co)
    C.log(f'carve: {chips} loose chips dropped; nap on {int((calm < 0.5).sum())} of {len(co)} vertices')


def carve_low(lo_body) -> None:
    """The game mesh: no loose chips, and the same eye sockets and mouth (the lens must not stand proud; the mouth must
    open)."""
    from monsters.breeds import paladove_parts as PP
    PP.drop_islands(lo_body)
    seat_eyes(lo_body)
    cut_mouth(lo_body)


# ----------------------------------------------------------------------------- rig weights
BONES = ['rear.2', 'rear.1', 'hips', 'chest', 'front.1', 'front.2', 'head']


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """Every lo_body weight, analytic and smooth (one region over the whole body; the heat solve is not used): a plump
    tube bends best on soft blends along its centre line, and replacing only parts of the heat weights left steps at
    the regions' edges (the cheek's crease stretched 3-4x in sleep). See body_weights()."""
    W = body_weights(co)
    return [(np.ones(len(co), bool), {b: w for b, w in W.items() if np.any(w > 0)})]


def body_weights(co: np.ndarray) -> dict:
    """  - the trunk: along the centre line from the tail's end to the face (rear.2 … front.2), each joint blended over
         14 cm;
       - the head: the cranium, the cheeks, the muzzle, the lip and the face, fading out down the jowl (whose bottom,
         where the front legs stand, rides front.2);
       - the jaw: the lower lip and the pocket's floor, the chin, and the cheeks' lower halves (the chew);
       - the antenna nubs on their chains; the legs on their two bones, blended into the body at the hip."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    n = len(co)
    pts = np.array([F.R2, F.R1B, F.R1, F.HIP, F.F1, F.F1B, F.F2, F.HEAD_TIP], np.float64)
    t, total = U.polyline_param(co, pts)
    a = t * total
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    joints = np.cumsum(seg)[:-1]
    bw = 0.07
    W: dict = {}
    for k, b in enumerate(BONES):
        start = smooth(joints[k - 1] - bw, joints[k - 1] + bw, a) if k > 0 else np.ones(n)
        end = smooth(joints[k] - bw, joints[k] + bw, a) if k < len(joints) else np.zeros(n)
        W[b] = start * (1.0 - end)
    # the chain's own head weight belongs to the jowl's front.2; the head takes only the head lump's share
    W['front.2'] = W['front.2'] + W['head']
    ds, db = F.antenna_dist(co)
    # round 2: the cranium's back blends into the first segment (fully head only ahead of the head's pivot): its back
    # stretched 8-17x at the nape in the hump and the curl
    cran = smooth(1.3, 1.02, F.ell_q(co, F.HEAD)) * smooth(0.27, 0.46, z) * smooth(-0.02, -0.19, y)
    face = smooth(-0.36, -0.42, y) * smooth(0.25, 0.36, z)
    lips = np.minimum(F.ell_q(co, (F._m(F.LIP[0], 1), F.LIP[1])), F.ell_q(co, (F._m(F.LIP[0], -1), F.LIP[1])))
    hs = np.maximum.reduce([cran, smooth(1.5, 1.05, F.cheek_q(co)) * smooth(0.2, 0.3, z), smooth(1.6, 1.0, F.ell_q(co, F.MUZZLE)),
                            smooth(1.6, 1.0, lips), face, (np.minimum(ds, db) < 0.09).astype(float)])
    hs = np.clip(hs, 0.0, 1.0)
    for b in BONES[:-1]:
        W[b] = W[b] * (1.0 - hs)
    W['head'] = hs
    # the jaw: the mouth's lower half (its floor and the lower lip), the chin under it, the cheeks' lower halves
    top, bot = F.mouth_edges(x)
    mid = 0.5 * (top + bot)
    near_mouth = smooth(0.06, 0.035, np.abs(x)) * (y < -0.4)
    lower = smooth(mid + 0.002, mid - 0.004, z) * smooth(mid - 0.07, mid - 0.03, z) * near_mouth
    chin = smooth(0.11, 0.05, np.linalg.norm(co - np.array([0.0, -0.47, 0.33])[None], axis=1)) * smooth(mid + 0.002, mid - 0.01, z)
    ck = 0.42 * smooth(1.45, 1.0, F.cheek_q(co)) * smooth(0.44, 0.32, z)
    wj = np.maximum.reduce([0.92 * lower, 0.88 * chin, ck]) * (y < -0.27) * (z > 0.2)
    for b in list(W):
        W[b] = W[b] * (1.0 - wj)
    W['jaw'] = wj
    for tag, s in (('L', 1), ('R', -1)):
        # the antenna nubs: on their chains past where the stalk leaves the crown
        p3 = F.antenna_points(s)
        d = np.minimum(F.seg_dist(co, p3[0], p3[1])[0], F.seg_dist(co, p3[1], p3[2])[0])
        dbs = np.linalg.norm(co - F.v3(p3[2])[None], axis=1)
        m = ((d < F.ANT_R[0] + 0.03) | (dbs < F.BALL_R + 0.025)) & (z > 0.65) & (np.sign(x) == s)
        if m.any():
            cw = U.chain_weights(co[m], p3, [f'antenna{tag}.1', f'antenna{tag}.2'], 'head', fade=(0.4, 0.24))
            keep = cw['head']
            for b in list(W):
                W[b][m] = W[b][m] * keep
            for b, w in cw.items():
                if b != 'head':
                    W.setdefault(b, np.zeros(n))[m] = w
        # the legs: their two bones, blended into whatever the body has at the hip
        for i, lg in enumerate(F.LEGS, start=1):
            hip, knee, foot = (F._m(lg[k], s) for k in ('hip', 'knee', 'foot'))
            dl = np.minimum(F.seg_dist(co, hip, knee)[0], F.seg_dist(co, knee, foot)[0])
            near = (dl < F.LEG_R[0] + 0.03) | (np.linalg.norm(co - F.v3(foot)[None], axis=1) < 0.085)
            m = near & (np.sign(x) == s) & (z < hip[2] + 0.01) & (np.abs(x) > 0.11)
            if not m.any():
                continue
            w = U.segment_weights(co[m], [(f'leg{i}.{tag}', hip, knee), (f'shin{i}.{tag}', knee, foot)], power=8.0)
            # round 2: only the leg's own skin (to 1.5 cm past its surface) rides it (the belly between the legs
            # stretched 9-17x in the gaits)
            k = smooth(hip[2] + 0.005, hip[2] - 0.045, z[m]) * smooth(F.LEG_R[0] + 0.022, F.LEG_R[0] + 0.006, np.minimum(dl[m], 
                np.linalg.norm(co[m] - F.v3(foot)[None], axis=1) - 0.02))
            for b in list(W):
                W[b][m] = W[b][m] * (1.0 - k)
            for b, v in w.items():
                W.setdefault(b, np.zeros(n))[m] = v * k
    tot = sum(W.values())
    return {b: w / np.maximum(tot, 1e-9) for b, w in W.items()}


# ----------------------------------------------------------------------------- eyes
def build_eye(name: str, s: int, high: bool):
    """(polish) A lens laid on the cranium's own curve (round 3's flat cap read as a flat disc with a bright edge in
    profile): a polar grid over the eye's disc, each point the head's surface plus a low dome (F.lens_w), and a short
    skirt down under the skin at its edge. Attributes eyeuv (across, up in lens radii; the dome) and eye_side."""
    import bmesh
    import bpy
    c, xax, yax, look = F.eye_frame(s)
    nr, na = (28, 64) if high else (10, 28)
    base = c - look * F.EYE_SINK
    verts, uv3, faces = [], [], []
    rings = list(np.linspace(0.0, 1.0, nr + 1)[1:])
    verts.append(base + look * float(F.lens_w(0.0, 0.0, s)))
    uv3.append((0.0, 0.0, 1.0))
    for rho in rings:
        for k in range(na):
            a = 2 * np.pi * k / na
            u, v = rho * np.cos(a), rho * np.sin(a)
            verts.append(base + (u * xax + v * yax) * F.EYE_R + look * float(F.lens_w(u, v, s)))
            uv3.append((u, v, 1.0 - rho * rho))
    for k in range(na):                                  # the skirt, 5 mm down under the skin at the edge
        a = 2 * np.pi * k / na
        u, v = np.cos(a), np.sin(a)
        verts.append(base + (u * xax + v * yax) * F.EYE_R + look * (float(F.head_w(u, v, s)) - 0.005))
        uv3.append((u * 1.02, v * 1.02, 0.0))
    for k in range(na):
        faces.append((0, 1 + k, 1 + (k + 1) % na))
    for j in range(len(rings)):
        r0 = 1 + j * na
        for k in range(na):
            a0, a1 = r0 + k, r0 + (k + 1) % na
            faces.append((a0, a0 + na, a1 + na, a1))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in verts], [], faces)
    me.validate(verbose=False)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    if sum(f.normal.dot(tuple(look)) for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    S.add_attr(ob, 'eyeuv', np.array(uv3))
    S.add_attr(ob, 'eye_side', np.full(len(verts), float(s)))
    return ob


def blink_pivot(s: int):
    from monsters.breeds import nibblegrub_paint as PT
    c, _xax, yax, look = F.eye_frame(s)
    p = c - look * (F.EYE_SINK + 0.004) + yax * (F.EYE_R * PT.LASH_V)     # (polish) 4 mm deeper: the shut lens hides
    return Vector(tuple(p)), Vector(tuple(yax)), Vector(tuple(look))


def eye_material(name: str, rough_pass: bool = False):
    from monsters.breeds import nibblegrub_paint as PT
    return PT.eye_material(name, rough_pass, PALETTE)


# ----------------------------------------------------------------------------- paint
def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import nibblegrub_paint as PT
    PT.paint_sources(body_srcs, fins, props, PALETTE, VARIANTS, ID)


def body_material(name: str, attr: str, pal: dict, marks):
    from lib import bake as BK
    return BK.emission_attr_material(name, attr)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import nibblegrub_paint as PT
    return PT.preview_colours(co, vn, PALETTE)


# round 3: an idle frame mid-chew and battle_idle mid-chew (its shot at t 0.25 has the mouth shut) on the review sheets
REVIEW = {'centre': (0.0, 0.03, 0.4), 'size': 1.55, 'head': ((0.0, -0.38, 0.5), 0.72),
          'clips': [('idle', 0.22), ('battle_idle', 0.375), ('strike', 0.42)]}
