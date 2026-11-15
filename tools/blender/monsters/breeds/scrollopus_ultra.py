"""Scrollopus at the Art 2.1 Ultra tier (chatgpt/monsters/22-scrollopus; CONTENT entry 27): a plump violet octopus
scholar in round gold spectacles and a felt cap with a gold tassel, on the blob plan (plans/blob.py; RECIPE.md "Blob
plan"). Its first real user, with Bloatoad.

    npm run art:shape -- scrollopus
    tools/blender/slot.sh npm run art:ultra -- scrollopus --blender --stages build,bake,rig,clips,export,review > tools/blender/out/scrollopus-build1.log 2>&1

Size: HEIGHT_UNITS 165 (the card: about 1.1 × Puddlepup's height) → 1.10 m to the top of the cap's board, the head's
crown at 0.98 m (round 3: the head lower on its arms). As for Moatshell's flag, the cap counts in the height.

The parts (the card wins on the count, FOR-CLAUDE-CODE section 2; the pictures on shapes and placement):
  - the body (lo_body): the round head-body with the face low on its front, the core under it, and all eight tentacles
    (scrollopus_form.py): five low on the ground with big spiral curls (front-left, right, back-right, back and the ink
    arm on its left-back), three holding the scroll (front-right), the quill (its right) and the book (its left);
    suckers in real cups on every underside and round the curls' outsides, soft folds, fine papillae
    (scrollopus_skin.py);
  - the props (lo_props): the felt cap with its board, button and braided cord, the tassel on a two-bone chain, the
    spectacles (scrollopus_cap.py); the scroll, the quill and the book on their tentacles' last bones
    (scrollopus_items.py);
  - the eyes: glossy lenses, big dark irises in white, the upper lid lowered a little (clever and a little mischievous).
Colours (CONTENT): skin #7D5BA6, underside #CDB4E6, ink spots #2E2A4F, cap #3A3A55, tassel #F2C94C, eyes #1E1E2E. The
spectacle rims take the tassel's gold (as the card says). Derived (CONTENT has none): see scrollopus_paint.py.
No secret variant (src/data/secrets.ts has none for Scrollopus).
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import scrollopus_cap as CP
from monsters.breeds import scrollopus_field as FL
from monsters.breeds import scrollopus_form as F
from monsters.breeds import scrollopus_geo as G
from monsters.breeds import scrollopus_items as IT

ID = 'scrollopus'
LOOK = 'scrollopus-ultra'
PLAN = 'blob'
HEIGHT_UNITS = 165
PALETTE = {'body': '#7D5BA6', 'belly': '#CDB4E6', 'accent': '#2E2A4F', 'eye': '#1E1E2E', 'cap': '#3A3A55', 'tassel': '#F2C94C'}
VARIANTS: dict = {}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')     # the smile is baked and never opens (no jaw weights)
BODY_TRIS = 66000                                # round 3: a bigger pile of arms, denser cups
ATLAS_STRIP = 0
ATLAS_DENSITY = {'lo_eyes': 1.4}
NORMAL_SCALE = 1.3                               # round 2: the cups, the papillae and the wet beads read as relief
BODY_SHEEN = 0.12                                # glossy wet skin: a little sheen, the gloss from the roughness and coat
LITE_PROPS_TRIS = 5200                           # the cap, the spectacles and the three held things are the look
AO_FLOOR = 0.42
AO_SOFTEN = 1.2
BLINK_CLOSED = (0.78, 0.04, 0.18)               # the shut lens stays inside the socket's dome
MOUTH_SOCKET = (0.0, -0.228, 0.5)
VOXELS = {'hi': 0.0027}                          # the suckers' rims and cups want a finer high source
FACE_NOTE = ('Baked face: big glossy eyes (white, a big dark iris with two catchlights) behind round gold spectacle rims '
             '(no glass), the upper lids lowered a little, the left brow raised, a small sly smile; ink-spot freckles. '
             'Blinking scales the blink bones: each lens squashes onto its lash line and sinks, showing the closed lid '
             'sculpted under it. The mouth never opens.')


def _t(p) -> tuple:
    return tuple(round(float(v), 4) for v in p)


# ----------------------------------------------------------------------------- the rig (plans/blob.py)
HIP = (0.0, 0.0, 0.4)
TOP = (0.0, 0.015, round(F.HEAD_TOP, 4))
BASE = (0.0, 0.0, 0.12)


def prop_specs() -> list[dict]:
    T = F.by_name()
    out = [{'name': 'cap', 'parent': 'head', 'head': _t(CP.board_frame()[0] - CP.board_frame()[3] * 0.06),
            'tail': _t(CP.board_frame()[0] + CP.board_frame()[3] * 0.04)},
           {'name': 'specs', 'parent': 'head', 'head': (0.0, -0.27, 0.605), 'tail': (0.0, -0.33, 0.605)}]
    for nm, arm in (('scroll', 'scrollarm'), ('quill', 'quillarm'), ('book', 'bookarm')):
        g, a = T[arm]['grip']
        out.append({'name': nm, 'parent': f'{arm}.4', 'head': _t(g), 'tail': _t(g + a * 0.1)})
    return out


def chain_euler(bone_pts, targets) -> list[tuple]:
    """The keyed rotations (world-aligned degrees relative to each parent at rest, as the plan keys them) that turn a
    chain at rest (its joints `bone_pts`) to point at the `targets` (one model-space point per joint after the root):
    each bone turns by the least rotation onto its target direction."""
    from monsters.plans import kin as K
    W = Matrix.Identity(3)
    out = []
    pts = [Vector(p) for p in bone_pts]
    tg = [Vector(bone_pts[0])] + [Vector(t) for t in targets]
    for i in range(len(pts) - 1):
        cur = W @ (pts[i + 1] - pts[i]).normalized()
        want = (tg[i + 1] - tg[i]).normalized()
        Wi = cur.rotation_difference(want).to_matrix() @ W
        out.append(tuple(round(v, 3) for v in K.deg(W.transposed() @ Wi)))
        W = Wi
    return out


# the Ink Flick (5-poses attack): the ink arm rises from its left-back, up behind the book, cocked back over its
# shoulder on the wind-up, then flicks forward over the book's top at eye height, its curled tip at the target
# round 2: the root on the pear's flank, so the arm rises from there (a smaller turn at the fused root)
# round 3: the head and the roots 5 cm lower
INK_WINDUP = [(0.26, 0.12, 0.5), (0.32, 0.13, 0.67), (0.31, 0.15, 0.71), (0.27, 0.23, 0.8)]
INK_IMPACT = [(0.27, 0.05, 0.49), (0.36, -0.01, 0.65), (0.36, -0.05, 0.685), (0.3, -0.18, 0.75)]
STRIKE_YAW = 12.0


def _unyaw(pts, deg: float) -> list:
    """Targets given as seen in the body's turned frame: turned back by the strike's yaw about the body's centre."""
    R = Matrix.Rotation(math.radians(-deg), 3, 'Z')
    c = Vector(HIP)
    return [tuple(c + R @ (Vector(p) - c)) for p in pts]


def turn_euler(axis, deg: float) -> tuple:
    from monsters.plans import kin as K
    return tuple(round(v, 3) for v in K.deg(Matrix.Rotation(math.radians(deg), 3, Vector(axis).normalized())))


def lax_of(m: dict, i: int = 0) -> Vector:
    a, b = Vector(m['bone_pts'][i]), Vector(m['bone_pts'][i + 1])
    d = b - a
    return Vector((d.y, -d.x, 0.0)).normalized()


def ink_knobs() -> tuple[dict, dict]:
    pts = F.by_name()['inkarm']['bone_pts']
    # the wind-up's peak comes as the body has turned about 0.85 of the strike's yaw, the impact all of it
    w = chain_euler(pts, _unyaw(INK_WINDUP, 0.85 * STRIKE_YAW))
    g = chain_euler(pts, _unyaw(INK_IMPACT, STRIKE_YAW))
    # the plan adds the wind-up's knob × its rise and the strike's × the drive (two bumps): the drive's rotation is
    # given as the change from the wind-up, so at the impact (the wind-up's bump spent) the arm is at INK_IMPACT
    return ({f'inkarm.{i + 1}': e for i, e in enumerate(w)}, {f'inkarm.{i + 1}': e for i, e in enumerate(g)})


# round 3 (review): win holds the book and the quill up high on either side of its head. The plan's gestures lift
# each holding arm 40 degrees from its root; on top of that each arm swings back from the face (about Z at its root)
# and its last bone turns back by the whole lift, so the book and the quill stay upright (leaning in, they hit the head)
# polish: the book a little lower and not swung back (it met the left temple)
WIN_SWING, WIN_LIFT = {'bookarm': 7.0, 'quillarm': 15.0}, {'bookarm': -14.0, 'quillarm': 6.0}
WIN_COUNTER = {'bookarm': 1.2, 'quillarm': 1.0}
PLAN_WIN_LIFT = 40.0


def turns_euler(*turns) -> tuple:
    from monsters.plans import kin as K
    M = Matrix.Identity(3)
    for axis, deg in turns:
        M = Matrix.Rotation(math.radians(deg), 3, Vector(axis).normalized()) @ M
    return tuple(round(v, 3) for v in K.deg(M))


def win_bones() -> dict:
    T = F.by_name()
    out = {}
    for arm, side in (('bookarm', 1.0), ('quillarm', -1.0)):
        lax = lax_of(T[arm])
        out[f'{arm}.1'] = [(-0.5, 1.5, turns_euler((lax, WIN_LIFT[arm]), ((0.0, 0.0, 1.0), side * WIN_SWING[arm])))]
        # polish: the book arm's last bone turns back only part of the lift (round the spine wrap, the whole of it
        # brought the book down to its rest height); the book leans a little in at the top, clear of the temple
        out[f'{arm}.4'] = [(-0.5, 1.5, turn_euler(lax, -(PLAN_WIN_LIFT + WIN_LIFT[arm]) * WIN_COUNTER[arm]))]
    # the scroll stays low and swings out to its right (the plan's lift put it in front of the face)
    out['scrollarm.1'] = [(-0.5, 1.5, turns_euler((lax_of(T['scrollarm']), -30.0), ((0.0, 0.0, 1.0), -20.0)))]
    return out


def rig_p() -> dict:
    tents = [{'name': m['name'], 'points': m['bone_pts'], 'role': m['role']} for m in F.tentacles()]
    wind, drive = ink_knobs()
    T = F.by_name()
    # the book comes down and out a little as the ink arm flicks over it (the arm reads beside the head)
    drive['bookarm.1'] = turn_euler(lax_of(T['bookarm']), -24.0)
    # round 2 (review: one arm only): the quill and the scroll rise with it and the head-body leans into the target
    # round 3 (review: 3-4 arms lift in the wind-up, the head pushes forward on the impact): the quill and the
    # front-left arm cock up with the ink arm, the scroll swings out to its right and stays low (the plan's gesture lift
    # put it in front of the face); the head-body drives forward into the flick
    wind.update({'chest': (-5.0, 0.0, -2.0), 'head': (-6.0, 0.0, -3.0),
                 'quillarm.1': turn_euler(lax_of(T['quillarm']), 35.0), 'scrollarm.1': turns_euler((lax_of(T['scrollarm']), -14.0), ((0.0, 0.0, 1.0), -20.0)),
                 'tentFL.1': turn_euler(lax_of(T['tentFL']), 16.0), 'tentFL.3': turn_euler(lax_of(T['tentFL'], 2), 30.0)})
    drive.update({'chest': (8.0, 0.0, 4.0), 'head': (14.0, 0.0, 6.0),
                  'quillarm.1': turn_euler(lax_of(T['quillarm']), 34.0), 'scrollarm.1': turns_euler((lax_of(T['scrollarm']), -10.0), ((0.0, 0.0, 1.0), -20.0)),
                  'tentFL.1': turn_euler(lax_of(T['tentFL']), 8.0)})
    # round 2 (review: hit read as idle): the head thrown back and aside, the spectacles knocked askew, every arm
    # flung outward and the curls whipped up
    # polish (review: the spectacles slid off the face, a temple through the book): the head rolls away from the
    # book, the spectacles a little askew with a rim on the face, the book flung down and out
    hit = {'head': (-9.0, -6.0, 0.0), 'chest': (-6.0, 0.0, 0.0), 'prop.specs': (0.0, 5.0, 0.0),
           'quillarm.1': turn_euler(lax_of(T['quillarm']), 32.0), 'scrollarm.1': turns_euler((lax_of(T['scrollarm']), -6.0), ((0.0, 0.0, 1.0), -15.0)),
           'bookarm.1': turns_euler((lax_of(T['bookarm']), -12.0), ((0.0, 0.0, 1.0), 15.0))}
    # round 3 (review: about half hit_heavy's fling): every ground arm lifts from its root and whips its curl up
    for g in F.GROUND:
        hit[f"{g['name']}.1"] = turn_euler(lax_of(T[g['name']]), 15.0)
        hit[f"{g['name']}.3"] = turn_euler(lax_of(T[g['name']], 2), 22.0)
    return {'hip': HIP, 'chest': TOP, 'body_base': BASE, 'head_split': 0.4, 'head_c': F.HEAD_C, 'head_r': F.HEAD_R,
            'jaw': {'head': (0.0, -0.19, 0.51), 'tail': (0.0, -0.245, 0.493)},
            'tentacles': tents, 'props': prop_specs(),
            'chains': [{'name': 'tassel', 'kind': 'tassel', 'parent': 'prop.cap', 'points': CP.tassel_points()}],
            'ink_arm': 'inkarm', 'strike_style': 'ink', 'cast_style': 'raise', 'ko_style': 'roll', 'ko_roll': 82.0,
            'hop': 0.8, 'strike_yaw': STRIKE_YAW,
            # plan options added for this breed (opt-in; RECIPE.md "Blob plan"): the ground tentacles' exact lift (its
            # roots are high above their ground runs), and the ink arm posed here instead of by the plan's lift
            'ground_lift_exact': True, 'ink_lift': 0.0, 'ink_turn': 0.0, 'ink_curl': (0.0, 0.0),
            'strike_windup_bones': wind, 'strike_bones': drive,
            # hit (5-poses): knocked back with the head thrown aside and the spectacles knocked askew
            'hit_bones': hit,
            'hit_heavy_bones': {'prop.specs': (0.0, -12.0, 0.0)}, 'hit_heavy_chain_hang': 0.6,
            # round 3 (review): win raises the book and the quill high (and the book out, clear of the cheek)
            'clip_bones': {'win': win_bones(),
                           'idle_happy': {'bookarm.1': [(-0.5, 1.5, turn_euler((0.0, 0.0, 1.0), 18.0))]},
                           'celebrate': {'bookarm.1': [(-0.5, 1.5, turn_euler((0.0, 0.0, 1.0), 18.0))]}},
            # ko rolls onto its right side, where the quill is: the quill arm's tip turns so the quill lies along the
            # ground behind it instead of propping the body up (the settle measures the props too); the tassel droops
            'ko_bones': {'quillarm.4': (70.0, 0.0, 0.0)}, 'ko_chain_hang': 0.9,
            'ko_settle_meshes': ('lo_body', 'lo_props')}


# ----------------------------------------------------------------------------- the body
all_parts = F.all_parts


def zones(co: np.ndarray, n=None) -> dict:
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    eye_d = np.minimum(np.linalg.norm(co - F.EYE_C[1], axis=1), np.linalg.norm(co - F.EYE_C[-1], axis=1))
    face = (y < -0.12) & (z > 0.415) & (z < 0.745) & (np.abs(x) < 0.25) & (F.mantle_sdf(co) < 0.01)
    muzzle = (np.linalg.norm((co - np.array([0.0, -0.222, 0.5])) / np.array([0.07, 0.05, 0.035]), axis=1) < 1.0)
    return {'face': face, 'muzzle': muzzle, 'eye_d': eye_d}


def decimate_keep(co: np.ndarray) -> np.ndarray:
    """The face, and a part of the curls (their outlines show the suckers' rims)."""
    z = zones(co)
    keep = 1.0 * z['face'] + 1.0 * z['muzzle'] + 1.0 * (z['eye_d'] < 0.085)
    f = FL.nearest(co)
    curl = (f['s'] / np.array([m['L'] for m in F.tentacles()])[f['tid']] > 0.62) & (f['d'] < f['r'] * 1.4)
    under = (f['cu'] > -0.25) & (f['d'] < f['r'] * 1.3) & (f['s'] > 0.17)
    keep = keep + 0.5 * curl + 0.2 * under            # round 2: the raised cups keep their outlines
    roots = (f['s'] < 0.3) & (f['d'] < f['r'] * 1.5)
    keep = np.maximum(keep, 0.45 * roots)               # round 3: the roots under the chin, without facets
    # build 2: the smooth head decimated into long slivers (thin streaks in the game's shading); it keeps more, except
    # the crown under the cap (round 3: with it protected too the collapse had nothing left to take but whole regions)
    keep = np.maximum(keep, 0.5 * head_zone(co) * (1.0 - hidden_crown(co)))
    return np.clip(keep, 0.0, 1.0)


def head_zone(co: np.ndarray) -> np.ndarray:
    return ((F.mantle_sdf(co) < 0.012) & (co[:, 2] > F.ROOT_Z - 0.01)).astype(float)


def texel_k(fc: np.ndarray) -> np.ndarray:
    """The head (the face, the spots, the brows) denser; the tentacles a little sparser; the crown under the cap,
    never seen, almost none (round 2: the spots by the cap's rim were pixel-stepped)."""
    from monsters.breeds import scrollopus_cap as CP
    k = np.where(head_zone(fc) > 0.5, 1.4, 0.9)
    # round 3: the forehead and the brows denser still (the spots above the brows stepped in the KTX2 blocks)
    k = np.where((head_zone(fc) > 0.5) & (fc[:, 1] < -0.06) & (fc[:, 2] > 0.62), 1.8, k)
    return np.where((hidden_crown(fc) > 0.5) & (head_zone(fc) > 0.5), 0.25, k)


def hidden_crown(co: np.ndarray) -> np.ndarray:
    """1 on the crown well under the cap's hem (as scrollopus_cap.skullcap lays it, by the azimuth; a safe margin)."""
    from monsters.breeds import scrollopus_cap as CP
    th = np.arctan2(co[:, 1] - F.MANTLE[0][1], co[:, 0] - F.MANTLE[0][0])
    hem = CP.SKULL_Z - CP.SKULL_TILT * np.cos(th) + 0.008 * np.sin(th)
    return (co[:, 2] > hem + 0.055).astype(float)


PROP_TEXEL = {'book': 1.7, 'scroll': 1.3, 'quill': 1.4, 'specs': 1.2, 'cap': 0.8, 'tassel': 0.9}


# polish: the plan's gesture lift calmed for the book where it reached the left temple
CLIP_CALM = {'win': {'bookarm': 0.5}, 'battle_idle': {'bookarm': 0.5}, 'cast': {'bookarm': 0.6}, 'idle_happy': {'bookarm': 0.7}, 'celebrate': {'bookarm': 0.7}, 'pet': {'bookarm': 0.8}}


# the ink leaves the curled tip of the ink arm (the plan's socket sits at its last bone's tail, the curl's outer side)
SOCKET_POINTS = {'socket_inkarm': ('inkarm.4', tuple(round(float(v), 4) for v in F.by_name()['inkarm']['pts'][-1]))}


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """Every tentacle by its own chain (no heat weights: neighbours would share them), blended smoothly across the
    webbing between their roots and into the core (`hips`); the head keeps its heat weights."""
    return [FL.body_weight_region(co, names)]


# ----------------------------------------------------------------------------- props
def _obj(name: str, pcs: list[dict], prop: str):
    pc = G.merge([G.orient_closed(p) for p in pcs])
    ob = G.make_object(name, pc)
    ob['prop'] = prop
    if name.startswith('lo_'):
        # round 2: the book's and the quill's per-pixel details want more texels, the cap's felt fewer
        G.set_face_attr(ob, 'texel_k', np.full(len(ob.data.polygons), PROP_TEXEL.get(prop, 1.0), np.float32))
    return ob


def _felt(ob) -> None:
    """The cap's felt (4-details panel 1): a fine fibrous nap in the high source (the normal map's relief)."""
    from monsters.breeds import scrollopus_noise as N
    co, vn = S.mesh_arrays(ob)
    pk = S.attr_array(ob, 'pk')
    felt = (pk > 0.5) & (pk < 2.5)
    d = 0.00045 * N.fbm(co, 1 / 0.0028, 131, 2) + 0.00025 * N.fbm(co, 1 / 0.0011, 132, 1)
    S.set_positions(ob, co + vn * (d * felt)[:, None])


def build_props(high: bool, quick: bool) -> list[bpy.types.Object]:
    tag = 'hi' if high else 'lo'
    cap = _obj(f'{tag}_cap', CP.cap(high), 'cap')
    if high:
        _felt(cap)
    return [cap, _obj(f'{tag}_tassel', CP.tassel(high), 'tassel'),
            _obj(f'{tag}_specs', CP.specs(high), 'specs'), _obj(f'{tag}_scroll', IT.scroll(high), 'scroll'),
            _obj(f'{tag}_quill', IT.quill(high), 'quill'), _obj(f'{tag}_book', IT.book(high), 'book')]


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    pk = np.rint(attr('pk')).astype(int)
    regs = [U.rigid(np.ones(len(co), bool), 'prop.cap')]
    regs.append(U.rigid((pk >= 10) & (pk < 20), 'prop.specs'))
    regs.append(U.rigid((pk >= 20) & (pk < 30), 'prop.scroll'))
    regs.append(U.rigid((pk >= 30) & (pk < 40), 'prop.quill'))
    regs.append(U.rigid((pk >= 40) & (pk < 50), 'prop.book'))
    hang = (pk >= 5) & (pk <= 7)
    if hang.any():
        regs.append((hang, U.chain_weights(co[hang], CP.tassel_points(), ['tassel.1', 'tassel.2'], 'prop.cap', fade=(0.02, -0.05))))
    return regs


def preview_prop_colour(name: str):
    from monsters.breeds import scrollopus_paint as PT
    return PT.preview_prop_colour(name)


# ----------------------------------------------------------------------------- eyes
def eye_frame(s: int):
    c = Vector(F.EYE_C[s])
    look = Vector(F.EYE_LOOK[s]).normalized()
    xax = Vector((0, 0, 1)).cross(look).normalized()
    yax = look.cross(xax).normalized()
    return c, xax, yax, look


def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = eye_frame(s)
    m = Matrix((xax, yax, look)).transposed().to_4x4()
    return Matrix.Translation(c - look * (F.EYE_R * F.EYE_DEPTH[1])) @ m


def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.35]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    R = F.EYE_R
    for v in bm.verts:
        v.co = Vector((v.co.x * R * F.EYE_SHAPE[0], v.co.y * R * F.EYE_SHAPE[1], v.co.z * R * F.EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / np.array([R * F.EYE_SHAPE[0], R * F.EYE_SHAPE[1], R * F.EYE_DEPTH[0]]))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


LID_EDGE = 0.46        # the upper lid's lash line, in the lens's units above its centre (lowered a little: sly)


def blink_pivot(s: int):
    c, _xax, yax, look = eye_frame(s)
    return c + yax * (F.EYE_R * F.EYE_SHAPE[1] * (LID_EDGE - 0.08)) - look * (F.EYE_R * 0.55), yax, look


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    from monsters.breeds import scrollopus_shade as SH
    return SH.eye_material(name, rough_pass, pal or PALETTE)


# ----------------------------------------------------------------------------- carving and paint
def carve(hi_body) -> None:
    from monsters.breeds import scrollopus_skin as SK
    SK.carve(hi_body)


def carve_low(lo_body) -> None:
    from monsters.breeds import scrollopus_skin as SK
    SK.carve_low(lo_body)


def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import scrollopus_paint as PT
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import scrollopus_shade as SH
    return SH.body_material(name, attr, pal, marks)


def prop_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import scrollopus_shade as SH
    return SH.prop_material(name, attr, pal, marks)


def make_marks(hi_body):
    from monsters.breeds import scrollopus_shade as SH
    return SH.make_marks(hi_body)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import scrollopus_paint as PT
    return PT.preview_colours(co, vn)


REVIEW = {'centre': (0.0, -0.03, 0.53), 'size': 1.55, 'head': ((0.0, -0.2, 0.63), 0.6)}
