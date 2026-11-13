"""The biped body plan (ART_2_PLAN §4, batch 3): rig template, sockets, springs and the clip generators for monsters
that stand on two legs: Quillion, Grumblestone, Gloomgrin, Plumdrake, Pluckrex (young and grown).

A recipe selects it with `PLAN = 'biped'` (tools/blender/monsters/breeds/RECIPE.md, "Biped plan"). The quadruped stays
the default plan and is untouched. The same build (build_ultra.py) drives both: rig_specs, sockets, springs,
chain_groups, heatless, make_clips, STAR_CLIPS, MOVE_CLIPS, ROOT_DIRS and KO_ROLL (ko lies on its side at
`body_width`, which the build measures and settles, then lifts any sinking frame with `ko_lift`).

Space: metres; the monster faces −Y, Z is up, +X is its left. Proportions come from the recipe's rig_p() (`P`):
  hip, chest           the pelvis centre and the top of the chest (the neck's base), on the mid-line
  head_c, head_r       the head's centre and radius
  legs                 the LEFT leg's joints {'hip', 'knee', 'ankle', 'toe'} (mirrored to the right)
  arms                 the LEFT arm's joints {'shoulder', 'elbow', 'wrist', 'hand'} (hand = the fingertips / knuckles)
Options (each off or Puddlepup-like by default; see RECIPE.md): size_k, neck_bones / neck_points / head_base, jaw, ears
(ear_base / ear_dir / ear_len), tail_bones / tail_points / tail_base / tail_dir / tail_len, tail_ground, tail_puff, wings
(the quadruped's wing dict), capes and manes (spring chains), props, hulk, squat, lean, stride, arm_relax, sit_height,
strike_style, body_width, ko_lift, and for a bulky breed hand_clear, hand_gap and slam {over, ground} (Grumblestone).

The clips are written as poses: each frame sets bone rotations (world-aligned degrees relative to the parent at rest,
as lib.anim.ClipBuilder.rot keys them: +x bends an upright bone forward, swings a hanging limb back and lifts a
backward bone; +z turns toward the monster's left; +y tilts an upright bone toward its left), the hips' offset, and
targets for the feet and hands, which a two-bone IK (no twist, bending in the rest pose's own plane) turns into the
limbs' rotations on the real rest bones. So the feet stay planted and the fists land where they aim whatever the
proportions (a hulk's long arms, a squat's bent legs, a long neck).
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

from lib import anim as A
from lib import common as C
from lib import ultra as U
from lib.rig import BoneSpec

PLAN = 'biped'
SIDES = (('L', 1), ('R', -1))
KO_ROLL = 80.0             # degrees the body rolls onto its right side in ko (build_ultra measures body_width at it)
STRIKE_STYLES = ('punch', 'swipe', 'headbutt', 'slam', 'thrust', 'pounce', 'charge', 'gust')
SPRINGS = []               # Art 2.0 compatibility only; the Ultra build calls springs(P)

# The sidestep's hop: the same arena distance as every quadruped (plans/quadruped.py): 1.4 arena metres at 150 units.
SIDESTEP_DISTANCE = 1.4 * 100 / 150
# Root motion directions in the glTF frame (Y up, the monster faces +Z, +X is its left).
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}
STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def _mirror(p, s: int) -> Vector:
    v = Vector(p)
    return Vector((v.x * s, v.y, v.z))


def limb(P: dict, key: str, s: int) -> dict[str, Vector]:
    """One side's joints of `legs` or `arms` (given for the left side, +X)."""
    return {k: _mirror(v, s) for k, v in P[key].items()}


def has_ears(P: dict) -> bool:
    return bool(P.get('ears', 'ear_base' in P))


def head_base(P: dict) -> Vector:
    """Where the head bone starts (the top of the neck): the recipe's head_base, else below the head's centre."""
    if P.get('head_base'):
        return Vector(P['head_base'])
    hc, hr = Vector(P['head_c']), P['head_r']
    return hc + Vector((0.0, 0.1 * hr, -0.6 * hr))


def neck_names(P: dict) -> list[str]:
    n = int(P.get('neck_bones', 1))
    return ['neck'] if n <= 1 else [f'neck.{i + 1}' for i in range(n)]


def neck_points(P: dict) -> list[Vector]:
    n = len(neck_names(P))
    if P.get('neck_points'):
        pts = [Vector(p) for p in P['neck_points']]
        if len(pts) != n + 1:
            raise ValueError(f'neck_points has {len(pts)} points; neck_bones = {n} needs {n + 1}')
        return pts
    a, b = Vector(P['chest']), head_base(P)
    return [a.lerp(b, k / n) for k in range(n + 1)]


def jaw_points(P: dict) -> tuple[Vector, Vector]:
    if P.get('jaw'):
        return Vector(P['jaw']['head']), Vector(P['jaw']['tail'])
    hc, hr = Vector(P['head_c']), P['head_r']
    return hc + Vector((0.0, -0.15 * hr, -0.3 * hr)), hc + Vector((0.0, -0.95 * hr, -0.55 * hr))


def tail_names(P: dict) -> list[str]:
    default = 3 if ('tail_base' in P or 'tail_points' in P) else 0
    return [f'tail.{i + 1}' for i in range(int(P.get('tail_bones', default)))]


def tail_points(P: dict) -> list[Vector]:
    n = len(tail_names(P))
    if P.get('tail_points'):
        pts = [Vector(p) for p in P['tail_points']]
        if len(pts) != n + 1:
            raise ValueError(f'tail_points has {len(pts)} points; tail_bones = {n} needs {n + 1}')
        return pts
    tb = Vector(P['tail_base'])
    td = Vector(P.get('tail_dir', (0, 1, -0.2))).normalized()
    return [tb + td * P['tail_len'] * k / n for k in range(n + 1)]


def puff_of(P: dict) -> tuple[Vector, Vector] | None:
    """The tail puff's bone (Plumdrake): `tail_puff` = {'length': m} continues the tail chain past its tip."""
    tp = P.get('tail_puff')
    if not tp or not tail_names(P):
        return None
    pts = tail_points(P)
    d = (pts[-1] - pts[-2]).normalized()
    return pts[-1], pts[-1] + d * float(tp.get('length', 0.1 * size_of(P)))


def chains(P: dict) -> list[dict]:
    """The spring chains: manes (a ruff, a beard) and capes (a cloak, a scarf's tails), each {'name', 'parent',
    'points'} as in the quadruped's manes; `kind` 'mane' or 'cape'."""
    out = []
    for key, kind in (('manes', 'mane'), ('capes', 'cape')):
        for m in P.get(key) or []:
            pts = [Vector(p) for p in m['points']]
            if len(pts) < 2:
                raise ValueError(f"{key} {m.get('name')}: needs at least 2 points")
            nm = m.get('name', kind)
            out.append({'name': nm, 'parent': m.get('parent', 'chest'), 'points': pts, 'kind': kind,
                        'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)], 'flare': float(m.get('flare', 1.0))})
    return out


def wings_of(P: dict) -> dict | None:
    return P.get('wings') or None


def strike_style(P: dict) -> str:
    st = P.get('strike_style', 'punch')
    if st not in STRIKE_STYLES:
        raise ValueError(f"strike_style {st!r}: one of {', '.join(STRIKE_STYLES)}")
    return st


def springs(P: dict) -> list[dict]:
    """The spring chains the runtime may drive: ears, tail (and its puff), manes, capes."""
    out = []
    if has_ears(P):
        out += [{'kind': 'ear', 'chain': ['ear.L.1', 'ear.L.2']}, {'kind': 'ear', 'chain': ['ear.R.1', 'ear.R.2']}]
    if tail_names(P):
        out.append({'kind': 'tail', 'chain': tail_names(P)})
    if puff_of(P):
        out.append({'kind': 'puff', 'chain': ['tail.puff']})
    for m in chains(P):
        out.append({'kind': m['kind'], 'chain': m['bones']})
    return out


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → chain kind for a recipe's CLIP_CALM: ear, tail (the puff too), each mane or cape by its own
    name (kind 'mane' / 'cape') and the wings ('wing')."""
    out = {'ear': 'ear', 'tail': 'tail', **{m['name']: m['kind'] for m in chains(P)}}
    if wings_of(P):
        out[wings_of(P).get('name', 'wing')] = 'wing'
    return out


def heatless(P: dict) -> set[str]:
    """Prefixes whose heat weights on the body go to their parent: the wings (folded against the back) and the capes
    (cloth: the body's skin must not follow them). Their parts are skinned by the recipe's fin / prop regions."""
    out = {m['name'] for m in chains(P) if m['kind'] == 'cape'}
    if wings_of(P):
        out.add(wings_of(P).get('name', 'wing'))
    return out


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    hip, chest = Vector(P['hip']), Vector(P['chest'])
    hc, hr = Vector(P['head_c']), P['head_r']
    s1, s2 = hip.lerp(chest, 0.3), hip.lerp(chest, 0.7)
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk),
        BoneSpec('hips', tuple(hip), tuple(s1), 'root', radius=0.3 * sk),
        BoneSpec('spine', tuple(s1), tuple(s2), 'hips', connect=True, radius=0.3 * sk),
        BoneSpec('chest', tuple(s2), tuple(chest), 'spine', connect=True, radius=0.3 * sk),
    ]
    npts, nn = neck_points(P), neck_names(P)
    for i, nm in enumerate(nn):
        specs.append(BoneSpec(nm, tuple(npts[i]), tuple(npts[i + 1]), 'chest' if i == 0 else nn[i - 1], connect=True, radius=0.2 * sk))
    specs.append(BoneSpec('head', tuple(npts[-1]), tuple(hc + Vector((0, 0, hr))), nn[-1], connect=True, radius=hr * 1.35))
    jh, jt = jaw_points(P)
    specs.append(BoneSpec('jaw', tuple(jh), tuple(jt), 'head', radius=0.6 * hr))
    if has_ears(P):
        eb, ed, el = Vector(P['ear_base']), Vector(P['ear_dir']).normalized(), P['ear_len']
        for tag, s in SIDES:
            b, d = _mirror(eb, s), Vector((ed.x * s, ed.y, ed.z))
            specs.append(BoneSpec(f'ear.{tag}.1', tuple(b), tuple(b + d * el * 0.5), 'head', radius=0.4 * hr))
            specs.append(BoneSpec(f'ear.{tag}.2', tuple(b + d * el * 0.5), tuple(b + d * el), f'ear.{tag}.1', connect=True, radius=0.4 * hr))
    for tag, s in SIDES:
        a = limb(P, 'arms', s)
        r = P.get('arm_radius', 0.08 * sk)
        specs.append(BoneSpec(f'upperarm.{tag}', tuple(a['shoulder']), tuple(a['elbow']), 'chest', radius=r))
        specs.append(BoneSpec(f'forearm.{tag}', tuple(a['elbow']), tuple(a['wrist']), f'upperarm.{tag}', connect=True, radius=r))
        specs.append(BoneSpec(f'hand.{tag}', tuple(a['wrist']), tuple(a['hand']), f'forearm.{tag}', connect=True, radius=r))
    for tag, s in SIDES:
        g = limb(P, 'legs', s)
        r = P.get('leg_radius', 0.1 * sk)
        specs.append(BoneSpec(f'thigh.{tag}', tuple(g['hip']), tuple(g['knee']), 'hips', radius=r))
        specs.append(BoneSpec(f'shin.{tag}', tuple(g['knee']), tuple(g['ankle']), f'thigh.{tag}', connect=True, radius=r))
        specs.append(BoneSpec(f'foot.{tag}', tuple(g['ankle']), tuple(g['toe']), f'shin.{tag}', connect=True, radius=r))
    tn = tail_names(P)
    if tn:
        pts = tail_points(P)
        for i, nm in enumerate(tn):
            specs.append(BoneSpec(nm, tuple(pts[i]), tuple(pts[i + 1]), 'hips' if i == 0 else tn[i - 1], connect=i > 0,
                                  radius=(0.1 + 0.02 * i / max(1, len(tn) - 1)) * sk))
        pf = puff_of(P)
        if pf:
            specs.append(BoneSpec('tail.puff', tuple(pf[0]), tuple(pf[1]), tn[-1], connect=True, radius=0.12 * sk))
    for m in chains(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.08 * sk))
    w = wings_of(P)
    if w:
        for s in (1, -1):
            for b, h, t, par in U.wing_bones(w, s):
                specs.append(BoneSpec(b, tuple(map(float, h)), tuple(map(float, t)), par, connect=par != w.get('parent', 'chest'), radius=0.08 * sk))
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'head'), radius=0.08 * sk))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """The game's seven (socket_head, _crown, _back, _mouth, _paw_L/_R at the hands, _tail) plus socket_hand_L/_R,
    socket_foot_L/_R, socket_wing_L/_R (with wings) and socket_<prop>."""
    sk = size_of(P)
    hc, hr = Vector(P['head_c']), P['head_r']
    chest = Vector(P['chest'])
    _jh, jt = jaw_points(P)
    out = {
        'socket_head': ('head', (0, hc.y, hc.z + hr)),
        'socket_crown': ('head', (0, hc.y, hc.z + hr + 0.12 * sk)),
        'socket_back': ('chest', (0, chest.y + 0.15 * sk, chest.z - 0.08 * sk)),
        'socket_mouth': ('jaw', (0, jt.y - 0.02 * sk, jt.z + 0.03 * sk)),
    }
    for tag, s in SIDES:
        a, g = limb(P, 'arms', s), limb(P, 'legs', s)
        out[f'socket_hand_{tag}'] = (f'hand.{tag}', tuple(a['hand']))
        out[f'socket_paw_{tag}'] = (f'hand.{tag}', tuple(a['hand']))
        out[f'socket_foot_{tag}'] = (f'foot.{tag}', tuple(g['toe']))
    tn = tail_names(P)
    out['socket_tail'] = (tn[-1], tuple(tail_points(P)[-1])) if tn else ('hips', (0, Vector(P['hip']).y + 0.15 * sk, P['hip'][2]))
    w = wings_of(P)
    if w:
        for s in (1, -1):
            q = U.wing_points(w, s)
            out[f'socket_wing_{U.wing_tag(s)}'] = (U.wing_bone_names(w, s)[1], tuple(map(float, q['wrist'])))
    for pr in P.get('props', []) or []:
        out[f"socket_{pr['name']}"] = (f"prop.{pr['name']}", tuple(pr['tail']))
    return out


# --------------------------------------------------------------------------- forward and inverse kinematics
I3 = Matrix.Identity(3)


def m3(e) -> Matrix:
    """(x, y, z) world-aligned degrees (as ClipBuilder.rot keys them) → a rotation matrix."""
    return Euler((math.radians(e[0]), math.radians(e[1]), math.radians(e[2])), 'XYZ').to_matrix()


def deg(m: Matrix) -> tuple[float, float, float]:
    e = m.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def _t(v: Vector) -> Matrix:
    return Matrix.Translation(v)


class Rig:
    """The armature's rest bones (armature space = model space) and a forward-kinematics evaluator that matches how
    ClipBuilder keys them: M_b = M_parent · T(head_b + offset_b) · R_b · T(−head_b), R_b world-aligned at rest."""

    def __init__(self, arm: bpy.types.Object):
        bones = arm.data.bones
        self.head = {b.name: Vector(b.head_local) for b in bones}
        self.tail = {b.name: Vector(b.tail_local) for b in bones}
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in bones}
        self.order: list[str] = []
        seen: set[str] = set()

        def visit(n: str) -> None:
            if n in seen:
                return
            p = self.parent[n]
            if p:
                visit(p)
            seen.add(n)
            self.order.append(n)
        for b in bones:
            visit(b.name)

    def has(self, b: str) -> bool:
        return b in self.head

    def length(self, b: str) -> float:
        return (self.tail[b] - self.head[b]).length

    def fk(self, rot: dict, loc: dict) -> dict[str, Matrix]:
        M: dict[str, Matrix] = {}
        ident = Matrix.Identity(4)
        for b in self.order:
            p = self.parent[b]
            h = self.head[b]
            r = rot.get(b)
            R = (r if isinstance(r, Matrix) else (m3(r) if r is not None else I3)).to_4x4()
            M[b] = (M[p] if p else ident) @ _t(h + Vector(loc.get(b, (0.0, 0.0, 0.0)))) @ R @ _t(-h)
        return M

    def bend_hint(self, a: str, b: str, fallback: Vector) -> Vector:
        """The rest pose's bend direction of the joint between a and b (perpendicular to the chain's line), else
        `fallback`: an IK aimed at the rest spots reproduces the rest pose."""
        h, k, e = self.head[a], self.head[b], self.tail[b]
        d = (e - h)
        if d.length < 1e-6:
            return fallback
        dn = d.normalized()
        perp = (k - h) - dn * (k - h).dot(dn)
        return perp.normalized() if perp.length > 0.02 * (k - h).length else fallback

    def two_bone(self, M: dict, a: str, b: str, c: str | None, target: Vector, hint: Vector, end_rot: Matrix | None = None,
                 w: float = 1.0) -> dict[str, Matrix]:
        """Rotations (world-aligned, relative to each parent) that put b's tip on `target` (or as near as the limb
        reaches), the middle joint bending toward `hint`; c (the foot or the hand) turned to the world rotation
        `end_rot` (None: it keeps its rest angle to b). w < 1 blends each rotation from the rest (slerp)."""
        Mp = M[self.parent[a]]
        Rp = Mp.to_3x3().normalized()
        A_ = Mp @ self.head[a]
        l1, l2 = self.length(a), self.length(b)
        d = target - A_
        dist = d.length
        L = max(abs(l1 - l2) + 1e-4, min(dist, l1 + l2 - 1e-4))
        dn = d.normalized() if dist > 1e-6 else (Rp @ (self.tail[b] - self.head[a])).normalized()
        hp = hint - dn * hint.dot(dn)
        if hp.length < 1e-6:
            hp = dn.orthogonal()
        hn = hp.normalized()
        ca = max(-1.0, min(1.0, (l1 * l1 + L * L - l2 * l2) / (2 * l1 * L)))
        K = A_ + dn * (l1 * ca) + hn * (l1 * math.sqrt(max(0.0, 1.0 - ca * ca)))
        E = A_ + dn * L
        ua = Rp @ (self.tail[a] - self.head[a])
        Ra_w = ua.rotation_difference(K - A_).to_matrix() @ Rp
        ub = Ra_w @ (self.tail[b] - self.head[b])
        Rb_w = ub.rotation_difference(E - K).to_matrix() @ Ra_w
        out = {a: Rp.transposed() @ Ra_w, b: Ra_w.transposed() @ Rb_w}
        if c is not None and end_rot is not None:
            out[c] = Rb_w.transposed() @ end_rot
        if w < 1.0:
            out = {k: Quaternion().slerp(m.to_quaternion(), max(0.0, w)).to_matrix() for k, m in out.items()}
        return out


class Frame:
    """One frame's pose: rotations (degrees, added up), offsets (metres, added up), and IK goals for the limbs."""

    def __init__(self):
        self.rot: dict[str, list[float]] = {}
        self.loc: dict[str, list[float]] = {}
        self.ik: dict[str, dict] = {}      # 'leg.L' / 'arm.R': {'target', 'hint', 'end', 'w'}
        self.mat: dict[str, Matrix] = {}   # whole rotations (the wings' slerps)

    def r(self, bone: str, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Frame:
        v = self.rot.setdefault(bone, [0.0, 0.0, 0.0])
        v[0] += x
        v[1] += y
        v[2] += z
        return self

    def o(self, bone: str, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Frame:
        v = self.loc.setdefault(bone, [0.0, 0.0, 0.0])
        v[0] += x
        v[1] += y
        v[2] += z
        return self


# --------------------------------------------------------------------------- clips
def _ramp(t: float, a: float, b: float) -> float:
    return A.step_ease(t, a, b)


def _lerp(a, b, k: float):
    return a + (b - a) * k


def make_clips(cb: A.ClipBuilder, P: dict, only: list[str] | None = None) -> list[A.ClipMeta]:
    rig = Rig(cb.arm)
    sk = size_of(P)
    made: list[A.ClipMeta] = []
    hulk = float(P.get('hulk', 0.0))
    squat = float(P.get('squat', 0.0))
    lean0 = float(P.get('lean', 0.0))
    style = strike_style(P)
    # 'thrust': degrees the tail's blade is raised as it points ahead (shared over the chain); or a list with one value
    # per tail bone (degrees each, applied as given): an upright blade on the last bone is pushed down to level (Quillion)
    thrust_lift = P.get('thrust_lift', 14.0)
    thrust_lift = [float(v) for v in thrust_lift] if isinstance(thrust_lift, (list, tuple)) else float(thrust_lift)
    thrust_swing = float(P.get('thrust_swing', -175.0))   # 'thrust': the tail's whole swing round the left side (degrees)
    has = rig.has
    TAIL = tail_names(P)
    PUFF = has('tail.puff')
    CHAINS = chains(P)
    NECK = neck_names(P)
    EARS = has_ears(P)
    JAW = bool(P.get('jaw_open', False))
    CLOSED = P.get('blink_closed')
    SHUT_EXP = tuple(math.log(v) / math.log(0.5) for v in (0.3, 0.62, 0.08))
    W_SPEC = wings_of(P)
    WQ = {s: wing_spread_quats(P, s) for s in (1, -1)} if W_SPEC else {}
    tail_ground = bool(P.get('tail_ground', False))

    # the rest geometry the motions are measured in
    hipL = rig.head['thigh.L']
    ank = {t: rig.head[f'foot.{t}'] for t, _ in SIDES}
    toe = {t: rig.tail[f'foot.{t}'] for t, _ in SIDES}
    foot_len = (toe['L'] - ank['L']).length
    LEG = rig.length('thigh.L') + rig.length('shin.L')
    d0 = (hipL - ank['L']).length               # the hip-to-ankle distance at rest
    HW = abs(hipL.x)                            # half the hips' width
    HZ = float(P['hip'][2])
    sh = {t: rig.head[f'upperarm.{t}'] for t, _ in SIDES}
    ARM = rig.length('upperarm.L') + rig.length('forearm.L')
    SW = abs(sh['L'].x)
    hc, hr = Vector(P['head_c']), float(P['head_r'])
    stride0 = float(P.get('stride', 0.55 * LEG * (1.0 - 0.18 * hulk)))
    knee_hint = {t: rig.bend_hint(f'thigh.{t}', f'shin.{t}', Vector((0.0, -1.0, 0.0))) for t, _ in SIDES}
    elbow_hint = {t: rig.bend_hint(f'upperarm.{t}', f'forearm.{t}', Vector((0.35 * s, 1.0, -0.4)).normalized()) for t, s in SIDES}
    # the arms' rest abduction (an A-pose's arms hang relaxed at arm_relax degrees out)
    relax = float(P.get('arm_relax', 10.0))
    abd = {}
    for t, s in SIDES:
        v = rig.head[f'hand.{t}'] - sh[t]
        abd[t] = math.degrees(math.atan2(v.x * s, max(1e-6, -v.z)))

    def mm(v: float) -> float:
        """An absolute offset in Puddlepup's metres, at this breed's size (size_k)."""
        return v * sk

    def drop_for(reach: float, slack: float = 0.96) -> float:
        """How far the hips must come down so a foot `reach` metres off its rest spot (along the ground) stays in reach."""
        return max(0.0, d0 - math.sqrt(max(1e-6, (slack * LEG) ** 2 - reach * reach)))

    def sit_height() -> float:
        """The hips' height when seated on the ground: the recipe's sit_height, else the thigh's thickness under its
        bone measured on lo_body (the seat is the back of the thighs), else 0.3 × the hip height."""
        if P.get('sit_height'):
            return float(P['sit_height'])
        body = bpy.data.objects.get('lo_body')
        if body is not None and body.type == 'MESH' and 'thigh.L' in body.vertex_groups and 'hips' in body.vertex_groups:
            gt = body.vertex_groups['thigh.L'].index
            # the seat: every vertex owned mostly by the pelvis, the spine or the tail's root (the buttocks, the belly,
            # the tail's thick base), which the seated hips must lift clear of the ground
            seat_groups = {body.vertex_groups[n].index for n in ('hips', 'spine', 'tail.1') if n in body.vertex_groups}
            thigh, pelvis = [], []
            for v in body.data.vertices:
                if not v.groups:
                    continue
                top = max(v.groups, key=lambda g: g.weight)
                for g in v.groups:
                    if g.group == gt and g.weight > 0.6:
                        thigh.append(v.co[:])
                if top.group in seat_groups and abs(v.co.x) < 1.3 * HW:
                    pelvis.append(v.co[:])
            if len(thigh) > 20:
                p = np.array(thigh)
                a, b = np.array(rig.head['thigh.L'][:]), np.array(rig.tail['thigh.L'][:])
                ab = b - a
                u = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
                seat = float(np.percentile(np.linalg.norm(p - (a + u[:, None] * ab), axis=1), 85)) * 1.05
                # the pelvis's own bottom (buttocks) below the hips' joint, when it reaches lower than the thighs
                if len(pelvis) > 20:
                    seat = max(seat, HZ - float(np.percentile(np.array(pelvis)[:, 2], 1)))
                return seat + 0.01 * LEG
        return 0.3 * HZ

    SIT_H = sit_height()

    def tail_clearance_lift(drop: float, margin: float) -> float:
        """Degrees to lift the whole tail (about its root) so it stays `margin` above the ground when the hips come
        down `drop` metres: from the rig's own tail points, searched in 2° steps up to 80°."""
        if not TAIL:
            return 0.0
        base = rig.head[TAIL[0]]
        pts = [rig.tail[b] for b in TAIL] + ([rig.tail['tail.puff']] if PUFF else [])
        for a in range(0, 82, 2):
            c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
            low = min((p - base).y * s_ + (p - base).z * c for p in pts)
            if base.z - drop + low >= margin:
                return float(a)
        return 80.0

    # tail() shares its lift over the chain (about 1.2x on the first bone): divide by the root's share
    sit_tail_lift = tail_clearance_lift(HZ - SIT_H, 0.06 * LEG) / (3.0 / max(3, len(TAIL)) * 1.2) if TAIL else 0.0

    # ---- keying
    def frame_rots(fr: Frame) -> dict:
        rot = {b: m3(v) for b, v in fr.rot.items()}
        for b, m in fr.mat.items():
            rot[b] = m @ rot.get(b, I3)
        return rot

    def key(f: int, fr: Frame) -> None:
        rot = frame_rots(fr)
        M = rig.fk(rot, fr.loc)
        solved: dict[str, Matrix] = {}
        for name in sorted(fr.ik, key=lambda n: 0 if n.startswith('leg') else 1):
            g = fr.ik[name]
            part, tag = name.split('.')
            if part == 'leg':
                chain = (f'thigh.{tag}', f'shin.{tag}', f'foot.{tag}')
            else:
                chain = (f'upperarm.{tag}', f'forearm.{tag}', f'hand.{tag}')
            res = rig.two_bone(M, *chain, g['target'], g['hint'], g.get('end'), g.get('w', 1.0))
            if part == 'arm' and g.get('hand') is not None and chain[2] not in res:
                res[chain[2]] = m3(g['hand'])
            solved.update(res)
            rot.update(res)
            M = rig.fk(rot, fr.loc)
        for b, v in fr.loc.items():
            if has(b):
                cb.loc(b, f, *v)
        for b in set(fr.rot) | set(fr.mat) | set(solved):
            if not has(b):
                continue
            if b in solved or b in fr.mat:
                cb.rot(b, f, *deg(rot[b]))
            else:
                cb.rot(b, f, *fr.rot[b])

    def clip(name: str, n: int, pose, loop: bool = True, hold: bool = False, root_speed: float = 0.0, step: int = 1,
             markers=(), faces=(), shut=None) -> None:
        if only and name not in only:
            return
        cb.begin(name, n, loop=loop, hold=hold, root_speed=root_speed)
        fs = list(range(1, n + 2, step))
        if fs[-1] != n + 1:
            fs.append(n + 1)
        for f in fs:
            key(f, pose((f - 1) / n))
        if shut is not None:
            eyes_shut(n, shut, step)
        for mk, f in markers:
            cb.marker(mk, f)
        for f, face in faces:
            cb.face(f, face)
        made.append(cb.end())

    def eyes_shut(frames: int, k, step: int = 1) -> None:
        """Squeeze the eyes toward the blink's closed pose by k(t) (the recipe's BLINK_CLOSED), as the quadruped does."""
        if not CLOSED:
            return
        fs = list(range(1, frames + 2, step))
        if fs[-1] != frames + 1:
            fs.append(frames + 1)
        for tag, _s in SIDES:
            pb = cb.arm.pose.bones.get(f'eye.{tag}')
            if pb is None:
                continue
            for f in fs:
                kk = max(0.0, min(1.0, k((f - 1) / frames)))
                pb.scale = tuple(1.0 + (c - 1.0) * kk ** e for c, e in zip(CLOSED, SHUT_EXP))
                pb.keyframe_insert('scale', frame=f)

    # ---- posing helpers (each adds to a Frame)
    def world_m(fr: Frame, bone: str) -> Matrix:
        """A bone's world matrix from the frame's FK rotations and offsets so far (no IK)."""
        return rig.fk(frame_rots(fr), fr.loc)[bone]

    def world_rot(fr: Frame, bone: str) -> Matrix:
        return world_m(fr, bone).to_3x3().normalized()

    def world_pos(fr: Frame, point: Vector, bone: str) -> Vector:
        return world_m(fr, bone) @ point

    def body(fr: Frame, crouch: float = 0.0, dx: float = 0.0, dy: float = 0.0, lean: float = 0.0, yaw: float = 0.0,
             roll: float = 0.0, gaze: float = 0.6) -> None:
        """The hips lowered by `crouch` metres and moved (dx, dy); the upper body leaning `lean` degrees forward over
        the hips, spine and chest, turned `yaw` (toward the left +) and rolled; the head takes back `gaze` of the lean
        so the eyes stay on the target."""
        lean += lean0 + 6.0 * hulk
        fr.o('hips', dx, dy, -crouch)
        fr.r('hips', 0.25 * lean, 0.4 * roll, 0.4 * yaw)
        fr.r('spine', 0.35 * lean, 0.3 * roll, 0.3 * yaw)
        fr.r('chest', 0.4 * lean, 0.3 * roll, 0.3 * yaw)
        for nm in NECK:
            fr.r(nm, -0.4 * gaze * (lean - lean0 - 6.0 * hulk) / len(NECK))
        fr.r('head', -0.6 * gaze * (lean - lean0 - 6.0 * hulk), -0.5 * roll, -0.6 * yaw * gaze)

    def plant(fr: Frame, tag: str, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0, pitch: float = 0.0, out: float = 0.0,
              yaw: float = 0.0, knee=None) -> None:
        """Put a foot's ankle (dx, dy, dz) from its rest spot (out = wider stance), the foot turned `pitch` degrees
        (+ = toes down, heel up) and `yaw`; the knee bends in its rest plane (or toward `knee`)."""
        # carried by the root: a jump's lift and win's spin take the feet along
        s = 1 if tag == 'L' else -1
        Mr = world_m(fr, 'root')
        tgt = Mr @ (ank[tag] + Vector((dx + s * out, dy, dz)))
        Rh = world_rot(fr, 'hips')
        hint = (Rh @ knee_hint[tag]) if knee is None else Vector(knee).normalized()
        end = Mr.to_3x3().normalized() @ Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Matrix.Rotation(math.radians(pitch), 3, 'X')
        fr.ik[f'leg.{tag}'] = {'target': tgt, 'hint': hint, 'end': end}

    def feet(fr: Frame, out: float = 0.0, stagger: float = 0.0, lift: float = 0.0) -> None:
        """Both feet planted at rest (wider by `out`, the left forward and the right back by `stagger`)."""
        out = out + 0.12 * hulk * HW
        plant(fr, 'L', dy=-stagger, dz=lift, out=out)
        plant(fr, 'R', dy=stagger, dz=lift, out=out)

    def toe_lift_pitch(h: float) -> float:
        """The foot's pitch (degrees) that keeps its toe on the ground when the ankle rises h."""
        return math.degrees(math.asin(max(-1.0, min(1.0, h / max(foot_len, 1e-4)))))

    def hang(fr: Frame, swing: dict | float = 0.0, bend: float = 15.0, out: float = 0.0, fwd: float = 0.0) -> None:
        """The arms hanging relaxed (an A-pose's arms come down to arm_relax degrees out), swung `swing` degrees back
        (+) per side, the elbows bent `bend`, raised `out` degrees sideways and `fwd` degrees forward."""
        for tag, s in SIDES:
            sw = swing.get(tag, 0.0) if isinstance(swing, dict) else swing
            down = (abd[tag] - relax) * (1.0 - 0.5 * hulk)
            fr.r(f'upperarm.{tag}', sw - fwd - 6.0 * hulk, s * (down - out), 0)
            fr.r(f'forearm.{tag}', -bend, 0, 0)

    def reach(fr: Frame, tag: str, point: Vector, w: float = 1.0, hint=None, hand=None) -> None:
        """A hand's IK goal: `point` in model space (the hand's knuckles/fingertips land there)."""
        point = clear_hand(fr, tag, point)
        Rc = world_rot(fr, 'chest')
        h = (Rc @ elbow_hint[tag]) if hint is None else Vector(hint).normalized()
        # the target is for the wrist (the forearm's tip): back off by the hand's length along the reach
        wrist = point - (point - world_pos(fr, sh[tag], 'chest')).normalized() * rig.length(f'hand.{tag}')
        fr.ik[f'arm.{tag}'] = {'target': wrist, 'hint': h, 'w': w, 'hand': hand}

    # options for a bulky breed (each off by default): `hand_gap` keeps each hand's goal at least that far (metres)
    # from the mid-line in the chest's frame, so two big fists never overlap; `hand_clear` lists ellipsoids in the rest
    # pose, each carried by its bone ({'bone', 'c', 'r', 'margin', 'push'}), that the knuckles and the wrist behind them
    # are pushed out of (radially, or along the bone-frame direction `push`), so fists in front of a deep belly or a
    # broad face stay in front of it (Grumblestone)
    CLEAR = list(P.get('hand_clear') or [])
    GAP = float(P.get('hand_gap', 0.0))

    def clear_hand(fr: Frame, tag: str, point: Vector) -> Vector:
        if not CLEAR and GAP <= 0.0:
            return point
        p = Vector(point)
        s = 1 if tag == 'L' else -1
        if GAP > 0.0:
            Mc = world_m(fr, 'chest')
            q = Mc.inverted() @ p
            if q.x * s < GAP:
                q.x = s * GAP
                p = Mc @ q
        hl = rig.length(f'hand.{tag}')
        for _ in range(3):
            moved = False
            for e in CLEAR:
                Mb = world_m(fr, e.get('bone', 'spine'))
                inv = Mb.inverted()
                c = Vector(e['c'])
                m = float(e.get('margin', 0.0))
                r = Vector(e['r']) + Vector((m, m, m))
                shp = world_pos(fr, sh[tag], 'chest')
                dv = (p - shp).normalized() if (p - shp).length > 1e-6 else Vector((0.0, -1.0, 0.0))
                for back in (0.0, hl):
                    q = inv @ (p - dv * back)
                    d = Vector(((q.x - c.x) / r.x, (q.y - c.y) / r.y, (q.z - c.z) / r.z))
                    if d.length < 1.0:
                        if e.get('push'):
                            # along the push direction to the surface: |(q + t u − c) / r| = 1, t ≥ 0
                            u = Vector(e['push']).normalized()
                            a_ = sum((u[i] / r[i]) ** 2 for i in range(3))
                            b_ = 2.0 * sum((q[i] - c[i]) * u[i] / r[i] ** 2 for i in range(3))
                            c_ = d.length_squared - 1.0
                            t_ = (-b_ + math.sqrt(max(0.0, b_ * b_ - 4.0 * a_ * c_))) / (2.0 * a_)
                            out = q + u * t_
                        else:
                            n = d.normalized() if d.length > 1e-6 else Vector((0.0, -1.0, 0.0))
                            out = c + Vector((n.x * r.x, n.y * r.y, n.z * r.z))
                        p = p + Mb.to_3x3().normalized() @ (out - q)
                        moved = True
            if not moved:
                break
        return p

    def body_point(fr: Frame, local: Vector, bone: str = 'chest') -> Vector:
        """A model-space point carried by a bone's current pose (e.g. in front of the chest)."""
        return world_pos(fr, local, bone)

    def guard(fr: Frame, w: float = 1.0, low: float = 0.0, wide: float = 0.0) -> None:
        """Fists up in front of the chest (a hulk's knuckles low and forward)."""
        lo = low + 0.6 * hulk
        for tag, s in SIDES:
            p = sh[tag] + Vector((-s * (0.35 - wide) * SW, -0.62 * ARM, (0.05 - 0.75 * lo) * ARM))
            reach(fr, tag, body_point(fr, p), w=w, hand=(-25, 0, 0))

    def breathe(fr: Frame, t: float, rate: float = 1.0, depth: float = 1.0) -> None:
        fr.r('chest', 2.0 * depth * A.wave(t, rate), 0, 0)
        fr.r('spine', 0.8 * depth * A.wave(t, rate), 0, 0)
        fr.r('head', -1.4 * depth * A.wave(t, rate), 0, 0)
        fr.o('hips', 0, 0, mm(0.003) * depth * A.wave(t, rate))
        for tag, s in SIDES:
            fr.r(f'upperarm.{tag}', 0, s * 1.2 * depth * A.wave(t, rate, 0.1), 0)

    def ears(fr: Frame, t: float, droop: float = 0.0, flutter: float = 0.0, rate: float = 1.0) -> None:
        if not EARS:
            return
        for tag, s in SIDES:
            fr.r(f'ear.{tag}.1', 0, s * (droop + flutter * A.wave(t, rate, 0.25)), 0)
            fr.r(f'ear.{tag}.2', 0, s * (0.6 * droop + 0.6 * flutter * A.wave(t, rate, 0.1)), 0)

    def tail(fr: Frame, t: float, up: float = 0.0, wag: float = 0.0, rate: float = 1.0, curl: float = 0.0) -> None:
        """The tail chain lifted `up` (+) and wagged `wag` degrees (shared over the bones with a lag to the tip);
        `curl` swings it round toward the left (+). A tail that lies on the ground (tail_ground) is never pushed down."""
        n = len(TAIL)
        if not n:
            return
        if tail_ground:
            up = max(0.0, up)
        for i, b in enumerate(TAIL):
            share = 3.0 / max(3, n)
            k = 0.7 + 0.6 * i / max(1, n - 1)
            fr.r(b, up * share * (1.2 - 0.4 * i / max(1, n - 1)), 0, share * (k * wag * A.wave(t - 0.05 * i, rate) + curl * k / 1.0))
        if PUFF:
            fr.r('tail.puff', 0, 0, 1.4 * wag * A.wave(t - 0.05 * n, rate))

    def capes(fr: Frame, t: float, trail: float = 0.0, sway: float = 0.0, rate: float = 1.0, lean: float = 0.0) -> None:
        """Every cape and mane: trailed back by `trail` degrees (shared down the chain, more toward the hem), swayed
        sideways, and turned back by `lean` (the chest's forward lean) so a cape keeps hanging when the body bends."""
        for m in CHAINS:
            n = len(m['bones'])
            k_kind = 1.0 if m['kind'] == 'cape' else 0.45
            for i, b in enumerate(m['bones']):
                lag = 0.06 * i
                x = (trail * m['flare'] * k_kind) / n * (0.7 + 0.6 * i / max(1, n - 1))
                if i == 0 and m['kind'] == 'cape':
                    x -= lean
                fr.r(b, x, 0, sway * k_kind / n * A.wave(t - lag, rate))

    def wings(fr: Frame, k: float, flap: float = 0.0) -> None:
        """Open both wings by k (0 folded, the rest pose; 1 the recipe's spread pose), beat them by `flap` degrees."""
        if not WQ:
            return
        for s, quats in WQ.items():
            for j, (bone, q) in enumerate(quats):
                qk = Quaternion().slerp(q, max(0.0, min(1.0, k)))
                if j == 0:
                    qk = Quaternion((0.0, 1.0, 0.0), math.radians(s * flap)) @ qk
                fr.mat[bone] = qk.to_matrix()

    def jaw(fr: Frame, deg_: float) -> None:
        if JAW and deg_:
            fr.r('jaw', deg_, 0, 0)

    def stand(t: float, crouch: float = 0.0, **kw) -> Frame:
        """A plain standing frame: the body, both feet planted (crouch metres lower: the knees bend)."""
        fr = Frame()
        body(fr, crouch=crouch, **kw)
        feet(fr)
        return fr

    hulk_drop = 0.05 * LEG * hulk
    squat_drop = squat * 0.42 * d0

    def rest_crouch(still: bool = True) -> float:
        """The standing crouch: a hulk's bent knees always, a squatter's deep crouch only when still."""
        return hulk_drop + (squat_drop if still else 0.25 * squat_drop)

    def squat_hands(fr: Frame, w: float = 1.0) -> None:
        """A squatter's hands resting on the ground in front of the feet (the rooftop statue)."""
        for tag, s in SIDES:
            p = Vector((s * 0.55 * SW, ank[tag].y - 0.5 * foot_len - 0.25 * LEG, 0.02 * LEG))
            reach(fr, tag, p, w=w, hand=(30, 0, 0))

    # ================================================================= ranch life
    def p_idle(t: float) -> Frame:
        fr = Frame()
        c = rest_crouch()
        body(fr, crouch=c, dx=0.06 * HW * A.wave(t, 1.0), lean=10 * squat, roll=1.2 * A.wave(t, 1.0),
             yaw=6 * A.pulse(t, 0.55, 0.8))
        feet(fr, out=0.12 * squat * HW)
        breathe(fr, t)
        fr.r('head', 0, 0, 10 * A.pulse(t, 0.55, 0.8))
        if squat >= 0.5:
            squat_hands(fr)
        else:
            hang(fr, swing=1.5 * A.wave(t, 1.0))
        ears(fr, t, 0, 3, 2.0)
        tail(fr, t, 4, 8, 1.0)
        capes(fr, t, 2 + 2 * A.wave(t, 1.0), 4, 1.0, lean=10 * squat)
        wings(fr, 0.04 + 0.03 * A.wave(t, 1.0))
        return fr

    def p_idle_happy(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 3)
        body(fr, crouch=rest_crouch() * 0.7 + 0.06 * LEG * (1 - b), roll=4 * A.wave(t, 1.5), lean=-4)
        feet(fr)
        fr.r('head', -6 * b, 8 * A.wave(t, 1.5), 0)
        hang(fr, swing={'L': -20 * A.wave(t, 3.0), 'R': 20 * A.wave(t, 3.0)}, bend=35, out=18 + 8 * b)
        ears(fr, t, -6, 6, 3.0)
        tail(fr, t, 18, 28, 3.0)
        capes(fr, t, 6 * b, 6, 3.0)
        wings(fr, 0.15 + 0.1 * b, 6 * A.wave(t, 3.0))
        jaw(fr, 14)
        return fr

    def p_idle_tired(t: float) -> Frame:
        fr = Frame()
        yawn = A.pulse(t, 0.45, 0.72)
        body(fr, crouch=rest_crouch() + 0.06 * LEG, lean=16 + 2 * A.wave(t, 0.6) - 14 * yawn, gaze=0.2,
             roll=2 * A.wave(t, 0.3))
        feet(fr)
        breathe(fr, t, 0.6, 1.6)
        fr.r('head', 14 - 22 * yawn, 0, 0)
        hang(fr, swing=-8, bend=8 + 50 * yawn, out=40 * yawn)
        ears(fr, t, 18, 2, 0.6)
        tail(fr, t, -14, 4, 0.6)
        capes(fr, t, 0, 2, 0.6, lean=16)
        wings(fr, 0.02)
        jaw(fr, 26 * yawn)
        return fr

    def p_idle_sad(t: float) -> Frame:
        fr = Frame()
        body(fr, crouch=rest_crouch() + 0.03 * LEG, lean=10, gaze=0.3, dx=0.04 * HW * A.wave(t, 0.7))
        feet(fr)
        breathe(fr, t, 0.7, 1.2)
        fr.r('head', 16, 0, -6 + 3 * A.pulse(t, 0.5, 0.7))
        for tag, s in SIDES:      # hands together in front of the belly
            p = Vector((s * 0.12 * SW, sh[tag].y - 0.45 * ARM, HZ + 0.15 * (sh[tag].z - HZ)))
            reach(fr, tag, body_point(fr, p, 'spine'))
        ears(fr, t, 26, 1.5, 0.7)
        tail(fr, t, -22, 3, 0.7)
        capes(fr, t, 0, 2, 0.7, lean=14)
        return fr

    def p_idle_sick(t: float) -> Frame:
        fr = Frame()
        sway = A.wave(t, 0.8)
        body(fr, crouch=rest_crouch() + 0.05 * LEG, lean=12, dx=0.12 * HW * sway, roll=4 * sway, gaze=0.3)
        feet(fr)
        breathe(fr, t, 0.8, 1.3)
        fr.r('head', 8, 2 * A.wave(t, 6.0) * A.pulse(t, 0.3, 0.45), 0)
        belly = Vector((0.1 * SW, Vector(P['hip']).y - 0.4 * (sh['L'].z - HZ), HZ + 0.35 * (sh['L'].z - HZ)))
        reach(fr, 'L', body_point(fr, belly, 'spine'))
        hang(fr, swing={'R': 4 * sway}, bend=10)
        fr.rot.pop('upperarm.L', None)
        fr.rot.pop('forearm.L', None)
        ears(fr, t, 22, 2, 0.8)
        tail(fr, t, -16, 2, 0.8)
        capes(fr, t, 0, 3, 0.8, lean=12)
        return fr

    def sit_frame(fr: Frame, k: float, t: float = 0.0) -> None:
        """Seated on the ground with the legs forward and the knees up a little, hands in the lap (k 0 stand → 1 sat)."""
        drop = (HZ - SIT_H) * k
        body(fr, crouch=drop, dy=0.12 * LEG * k, lean=-6 * k + 8 * squat * k)
        for tag, s in SIDES:
            seat = Vector((ank[tag].x * 1.25, hipL.y - 0.92 * math.sqrt(max(0.0, (0.94 * LEG) ** 2 - (SIT_H - ank[tag].z) ** 2)) + 0.12 * LEG,
                           ank[tag].z))
            tgt = ank[tag].lerp(seat, k)
            Rh = world_rot(fr, 'hips')
            hint = (Rh @ knee_hint[tag]).lerp(Vector((0.0, -0.4, 1.0)).normalized(), k)
            end = Matrix.Rotation(math.radians(-55 * k), 3, 'X')
            fr.ik[f'leg.{tag}'] = {'target': tgt, 'hint': hint, 'end': end}
        for tag, s in SIDES:
            lap = Vector((s * 0.35 * SW, hipL.y - 0.3 * LEG, HZ + 0.25 * (sh[tag].z - HZ)))
            reach(fr, tag, world_pos(fr, lap, 'hips'), w=k)
        # the tail swings round and lifts just enough to clear the ground; a cape trails out behind on the ground
        tail(fr, t, sit_tail_lift * k, 0, 1.0, curl=40 * k)
        capes(fr, t, 40 * k)

    def p_sleep(t: float) -> Frame:
        fr = Frame()
        sit_frame(fr, 1.0, t)
        b = A.wave(t, 0.4)
        fr.r('spine', 10, 0, 0).r('chest', 8 + 3 * b, 0, 0)
        for nm in NECK:
            fr.r(nm, 18 / len(NECK))
        fr.r('head', 16 + 3 * b, 14, 10)
        ears(fr, t, 20, 1, 0.4)
        capes(fr, t, 0, 1, 0.4, lean=18)
        return fr

    def p_eat(t: float) -> Frame:
        fr = Frame()
        dip = A.step_ease(t, 0.0, 0.2) * (1 - A.step_ease(t, 0.85, 1.0))
        body(fr, crouch=rest_crouch(), lean=4 * dip)
        feet(fr)
        fr.r('head', 10 * dip, 0, 0)
        mouth = hc + Vector((0.0, -1.25 * hr, -0.35 * hr))
        for tag, s in SIDES:
            reach(fr, tag, world_pos(fr, mouth + Vector((s * 0.35 * hr, 0, -0.2 * hr)), 'head'), w=dip)
        chew = dip * abs(math.sin(t * 2 * math.pi * 3))
        jaw(fr, 14 * chew)
        fr.r('head', 3 * chew, 0, 0)
        ears(fr, t, 6, 3, 3.0)
        tail(fr, t, 6, 10)
        return fr

    def p_pet(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, crouch=rest_crouch() + 0.02 * LEG * b, roll=3 * A.wave(t, 1.0))
        feet(fr)
        fr.r('head', -8, 16 + 2 * A.wave(t, 2.0), 4)      # leaning into the hand above
        for tag, s in SIDES:       # hands clasped at the chest
            p = Vector((s * 0.1 * SW, sh[tag].y - 0.5 * ARM, sh[tag].z - 0.15 * ARM))
            reach(fr, tag, body_point(fr, p))
        ears(fr, t, 12, 3, 2.0)
        tail(fr, t, 14, 22, 2.0)
        capes(fr, t, 2, 3, 2.0)
        jaw(fr, 8)
        return fr

    def p_look(t: float) -> Frame:
        fr = Frame()
        yaw = 35 * A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56)) - 35 * A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        body(fr, crouch=rest_crouch(), yaw=0.3 * yaw, lean=6 * squat)
        feet(fr, out=0.1 * squat * HW)
        fr.r('head', 0, 0, 0.8 * yaw)
        if squat >= 0.5:
            squat_hands(fr)
        else:
            hang(fr, swing={'L': 0.1 * yaw, 'R': -0.1 * yaw})
        ears(fr, t, 0, 2, 1.0)
        tail(fr, t, 8, 6)
        capes(fr, t, 0, 3)
        return fr

    def p_hop(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.28, 0.82)
        crouch = 0.14 * LEG * (A.pulse(t, 0.0, 0.28) + 0.8 * A.pulse(t, 0.8, 1.0))
        fr.o('root', 0, 0, mm(0.15) * air)
        body(fr, crouch=crouch + rest_crouch(False), lean=10 * A.pulse(t, 0.0, 0.3) - 6 * air)
        tuck = 0.18 * LEG * air
        plant(fr, 'L', dz=tuck, pitch=20 * air)
        plant(fr, 'R', dz=tuck, pitch=20 * air)
        hang(fr, swing=-70 * air + 20 * A.pulse(t, 0.0, 0.28), bend=30, out=25 * air)
        ears(fr, t, 0, 0)
        for tag, s in SIDES:
            if EARS:
                fr.r(f'ear.{tag}.1', -30 * air + 25 * A.pulse(t, 0.8, 1.0), s * 4, 0)
        tail(fr, t, 22 * air)
        capes(fr, t, 30 * air - 10 * A.pulse(t, 0.8, 1.0))
        wings(fr, 0.4 * air, 20 * A.wave(t, 2.0) * air)
        return fr

    def p_celebrate(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        land = A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)
        fr.o('root', 0, 0, mm(0.11) * air)
        body(fr, crouch=0.1 * LEG * land + rest_crouch(False), lean=-8 * air)
        for tag, _s in SIDES:
            plant(fr, tag, dz=0.1 * LEG * air, pitch=15 * air)
        pump = A.wave(t, 3.0)
        for tag, s in SIDES:       # both fists up in a V, pumping
            up = sh[tag] + Vector((s * 0.45 * ARM, -0.15 * ARM, (0.75 + 0.1 * pump) * ARM))
            reach(fr, tag, body_point(fr, up), hint=Vector((s, 0.4, -0.3)), hand=(-20, 0, 0))
        fr.r('head', -8 * air, 10 * A.wave(t, 2.0), 0)
        ears(fr, t, -8, 12, 3.0)
        tail(fr, t, 22, 30, 4.0)
        capes(fr, t, 20 * air, 8, 2.0)
        wings(fr, 0.6, 18 * A.wave(t, 3.0))
        jaw(fr, 16)
        return fr

    # ================================================================= moving
    def gait(t: float, stride: float, lift: float, stance: float, bob: float, sway: float, roll: float, yaw: float,
             arm: float, bend: float, lean: float, back: bool = False, guard_w: float = 0.0, flight: bool = False) -> Frame:
        """A two-legged cycle (the left foot plants at t = 0, the right at 0.5): planted feet slide back under the
        body (root motion carries it), swing feet lift and reach; the hips bob and shift over the planted foot, roll
        and turn with the swinging leg; the chest counter-turns; the arms swing against the legs."""
        fr = Frame()
        drop = drop_for(stride / 2 + 0.02 * LEG) + rest_crouch(False)
        mid = stance / 2
        if flight:   # running: the body sinks through stance and rises through the flight
            dz = -bob * max(0.0, math.cos(2 * math.pi * 2 * (t - mid)))
        else:        # walking: highest over the planted foot, lowest when both feet are down
            dz = -bob * (0.5 - 0.5 * math.cos(2 * math.pi * 2 * (t - mid)))
        sx = sway * math.cos(2 * math.pi * (t - mid))      # over the left foot at its mid-stance
        body(fr, crouch=drop - dz, dx=sx, lean=lean, roll=-roll * math.cos(2 * math.pi * (t - mid)),
             yaw=-yaw * math.cos(2 * math.pi * t) * (-1 if back else 1))
        fr.r('chest', 0, 0, 1.4 * yaw * math.cos(2 * math.pi * t) * (-1 if back else 1))
        fr.r('head', 0, 0, -0.6 * yaw * math.cos(2 * math.pi * t) * (-1 if back else 1))
        for tag, s in SIDES:
            p = (t + (0.0 if tag == 'L' else 0.5)) % 1.0
            if p < stance:
                u = p / stance
                dy = -stride / 2 + stride * u
                h = 0.25 * lift * A.step_ease(u, 0.75, 1.0) if not flight else 0.0
                pitch = toe_lift_pitch(h)
                dzf = h
            else:
                u = (p - stance) / (1 - stance)
                dy = stride / 2 - stride * C.ease_in_out(u)
                dzf = lift * math.sin(u * math.pi)
                pitch = 25 * math.sin(u * math.pi) * (1 - u) - 10 * A.pulse(u, 0.6, 1.0)
            if back:
                dy = -dy
            plant(fr, tag, dy=dy, dz=dzf, pitch=pitch, out=0.12 * hulk * HW)
        if guard_w:
            guard(fr, w=guard_w)
        else:
            hang(fr, swing={'L': arm * math.cos(2 * math.pi * t), 'R': -arm * math.cos(2 * math.pi * t)}, bend=bend,
                 out=8 * hulk)
        return fr

    def step_markers(n: int, stance_note: float = 0.0) -> list:
        return [('step', 1), ('step', 1 + int(round(0.5 * n)))]

    stride_w = stride0
    lift_w = 0.13 * LEG

    def p_walk(t: float) -> Frame:
        fr = gait(t, stride_w, lift_w, 0.6, 0.03 * LEG * (1 + 0.4 * hulk), 0.14 * HW * (1 + 1.2 * hulk), 3 + 4 * hulk,
                  6 + 3 * hulk, 22 * (1 - 0.3 * hulk), 18, 3)
        tail(fr, t, 6, 10, 1.0)
        ears(fr, t, 2, 5, 2.0)
        capes(fr, t, 6 + 4 * A.wave(t, 2.0), 5, 1.0)
        wings(fr, 0.03)
        return fr

    stride_r = 0.75 * LEG * (1.0 - 0.15 * hulk)

    def p_run(t: float) -> Frame:
        fr = gait(t, stride_r, 0.32 * LEG, 0.38, 0.06 * LEG, 0.08 * HW, 4, 8, 38, 80, 14, flight=True)
        tail(fr, t, 4, 8, 1.0)
        ears(fr, t, -16, 10, 1.0)
        capes(fr, t, 26 + 8 * A.wave(t, 1.0, -0.2), 4, 1.0)
        wings(fr, 0.08, 6 * A.wave(t, 2.0))
        return fr

    stride_d = 0.9 * LEG * (1.0 - 0.15 * hulk)

    def p_dash(t: float) -> Frame:
        fr = gait(t, stride_d, 0.36 * LEG, 0.32, 0.07 * LEG, 0.05 * HW, 3, 6, 50, 85, 24, flight=True)
        tail(fr, t, -6, 6, 1.0)
        ears(fr, t, -30, 4, 1.0)
        capes(fr, t, 40 + 6 * A.wave(t, 1.0, -0.2), 2, 1.0)
        wings(fr, 0.1)
        return fr

    stride_s = 0.35 * LEG

    def p_step(t: float, back: bool) -> Frame:
        fr = gait(t, stride_s * (0.8 if back else 1.0), 0.08 * LEG, 0.6, 0.015 * LEG, 0.08 * HW, 2, 4, 0, 0,
                  (2 if back else 8), back=back, guard_w=1.0)
        tail(fr, t, 18, 8, 2.0)
        ears(fr, t, -8 if not back else 4, 4, 2.0)
        capes(fr, t, (8 if not back else -4) + 3 * A.wave(t, 2.0), 3, 2.0)
        wings(fr, 0.12)
        return fr

    def p_strafe(t: float, side: int) -> Frame:
        """A sideways shuffle facing the opponent: each foot steps out to the side in turn and slides back."""
        fr = Frame()
        stance = 0.56
        stride = min(0.35 * LEG, 1.1 * HW)
        bob = 0.012 * LEG * abs(math.sin(t * 2 * math.pi * 2))
        body(fr, crouch=rest_crouch(False) + 0.05 * LEG + bob, roll=side * (3 + A.wave(t, 2.0)), lean=4)
        for tag, s in SIDES:
            p = (t + (0.0 if tag == 'L' else 0.5)) % 1.0
            if p < stance:
                u = p / stance
                dx = side * (stride / 2 - stride * u)
                dz = 0.0
            else:
                u = (p - stance) / (1 - stance)
                dx = side * (-stride / 2 + stride * C.ease_in_out(u))
                dz = 0.08 * LEG * math.sin(u * math.pi)
            plant(fr, tag, dx=dx, dz=dz, pitch=10 * dz / max(LEG, 1e-4), out=0.1 * HW)
        guard(fr)
        fr.r('head', 0, -side * 3, -side * 4)
        tail(fr, t, 14, -side * 12 + 6 * A.wave(t, 2.0))
        capes(fr, t, 6, -side * 12, 2.0)
        ears(fr, t, -4, 3, 2.0)
        wings(fr, 0.1)
        return fr

    def p_sidestep(t: float, side: int) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.18, 0.92)
        crouch = A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        fr.o('root', 0, 0, mm(0.07) * air)
        body(fr, crouch=rest_crouch(False) + 0.12 * LEG * crouch, roll=side * 10 * air, lean=6 * crouch)
        for tag, s in SIDES:
            lead = (tag == 'L') == (side > 0)
            plant(fr, tag, dx=side * 0.08 * LEG * air * (1.0 if lead else -0.3), dz=0.12 * LEG * air, pitch=15 * air)
        hang(fr, swing=-10 * air, bend=40, out=35 * air)
        fr.r('head', 0, -side * 10 * air, -side * 8 * air)
        tail(fr, t, 18 * air, -side * 20 * air)
        capes(fr, t, 14 * air, -side * 22 * air)
        ears(fr, t, -10 * air, 0)
        wings(fr, 0.3 * air)
        return fr

    # ================================================================= scenes
    def p_sit_down(t: float) -> Frame:
        fr = Frame()
        sit_frame(fr, C.ease_in_out(t), t)
        fr.r('head', 4 * A.pulse(t, 0.2, 0.9), 0, 0)
        return fr

    def p_sit(t: float) -> Frame:
        fr = Frame()
        sit_frame(fr, 1.0, t)
        breathe(fr, t)
        fr.r('head', -1.5 * A.wave(t, 1.0), 8 * A.pulse(t, 0.5, 0.75), 6 * A.pulse(t, 0.2, 0.4))
        ears(fr, t, 6, 2.5, 1.0)
        capes(fr, t, 0, 2, 1.0)
        return fr

    def p_dizzy(t: float) -> Frame:
        fr = Frame()
        c, s_ = math.cos(t * 4 * math.pi), math.sin(t * 4 * math.pi)
        body(fr, crouch=rest_crouch(False) + 0.04 * LEG, dx=0.12 * HW * s_, dy=0.08 * HW * c, roll=6 * s_, lean=4 * c)
        feet(fr, out=0.15 * HW)
        fr.r('head', 12 * c, 0, 16 * s_)
        for nm in NECK:
            fr.r(nm, 4 * c / len(NECK), 0, 6 * s_ / len(NECK))
        hang(fr, swing={'L': 15 * s_, 'R': -15 * c}, bend=25, out=20)
        ears(fr, t, 18, 4, 2.0)
        tail(fr, t, -8, 6, 2.0)
        capes(fr, t, 2, 6, 2.0)
        return fr

    # ================================================================= battle
    def p_battle_idle(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, crouch=rest_crouch() * 0.6 + 0.07 * LEG + 0.025 * LEG * (1 - b), lean=8 + 6 * squat, yaw=-8)
        plant(fr, 'L', dy=-0.12 * LEG, out=0.15 * HW)
        plant(fr, 'R', dy=0.12 * LEG, out=0.15 * HW)
        guard(fr, low=0.25 * squat)
        fr.r('head', -2 * A.wave(t, 2.0), 0, 0)
        ears(fr, t, -10, 3, 2.0)
        tail(fr, t, 18, 8, 2.0)
        capes(fr, t, 4 + 2 * A.wave(t, 2.0), 4, 2.0, lean=8)
        wings(fr, 0.18 + 0.05 * b)
        return fr

    def p_hit(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.8)
        body(fr, crouch=rest_crouch(False) + 0.04 * LEG * k, dy=0.08 * LEG * k, lean=-10 * k)
        feet(fr)
        fr.r('head', -6 * k, -14 * k, -30 * k)      # knocked aside, away from the review camera
        for tag, s in SIDES:      # forearms flinch up toward the face
            p = sh[tag] + Vector((-s * 0.2 * SW, -0.5 * ARM, 0.25 * ARM))
            reach(fr, tag, body_point(fr, p), w=k)
        ears(fr, t, -20 * k, 0)
        tail(fr, t, -10 * k)
        capes(fr, t, -12 * k)
        wings(fr, 0.45 * k)
        jaw(fr, 10 * k)
        return fr

    def p_hit_heavy(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.55)
        rec = A.step_ease(t, 0.5, 1.0)
        shake = 6 * math.sin(t * 2 * math.pi * 3) * (1 - rec) * A.step_ease(t, 0.1, 0.3)
        body(fr, crouch=rest_crouch(False) + 0.12 * LEG * k, dy=0.2 * LEG * k, lean=-22 * k, roll=shake)
        plant(fr, 'L', out=0.1 * HW * k)
        plant(fr, 'R', dy=0.22 * LEG * k, out=0.1 * HW * k, dz=0.04 * LEG * A.pulse(t, 0.05, 0.3))
        fr.r('head', -10 * k, -18 * k, -34 * k)
        hang(fr, swing=35 * k, bend=20, out=45 * k)
        ears(fr, t, 14 * k, 0)
        tail(fr, t, -18 * k)
        capes(fr, t, -25 * k)
        wings(fr, 0.7 * k)
        jaw(fr, 14 * k)
        return fr

    lift_tab = P.get('ko_lift') or []

    def ko_lift(t: float) -> float:
        """build_ultra's settle_ko: extra height (metres) per moment so no frame of the fall sinks into the ground."""
        if not lift_tab:
            return 0.0
        for (t0, d0_), (t1, d1) in zip(lift_tab[:-1], lift_tab[1:]):
            if t0 <= t <= t1:
                return d0_ + (d1 - d0_) * (t - t0) / max(t1 - t0, 1e-9)
        return lift_tab[0][1] if t < lift_tab[0][0] else lift_tab[-1][1]

    def p_ko(t: float) -> Frame:
        """It wobbles, buckles and topples onto its right side (the face and belly toward the review camera's side),
        then lies on the ground at body_width: the legs loosely bent, the arm underneath stretched above the head along
        the ground, the other draped over the body, the head rolled back so the face stays upright, eyes shut."""
        fr = Frame()
        wob = (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = A.step_ease(t, 0.4, 0.82)
        buckle = A.pulse(t, 0.25, 0.6)
        lie = float(P.get('body_width', 1.2 * HW + 0.1 * LEG))
        fr.r('root', 0, 10 * math.sin(t * 2 * math.pi * 2.5) * wob - KO_ROLL * fall, 0)
        h = HZ * (1 - fall) + lie * fall + ko_lift(t) - 0.15 * LEG * buckle * (1 - fall)
        a = math.radians(KO_ROLL * fall)
        fr.o('hips', h * math.sin(a), 0.0, h * math.cos(a) - HZ)
        fr.r('spine', 10 * fall, 0, 0).r('chest', 8 * fall, 0, 0)
        for nm in NECK:
            fr.r(nm, 6 * fall / len(NECK), 14 * fall / len(NECK), 0)
        fr.r('head', 8 * fall, 26 * fall, 0)
        fr.r('upperarm.R', -20 * fall, (160 - abd['R']) * fall, 0).r('forearm.R', -15 * fall, 0, 0)
        fr.r('upperarm.L', -55 * fall, (abd['L'] - relax + 15) * fall, 0).r('forearm.L', -30 * fall, 0, 0)
        # the feet: planted through the wobble and the buckle, then (as it topples) folded loosely in the hips' frame:
        # the top (left) knee drawn up more than the lower one
        gone = A.step_ease(t, 0.36, 0.7)
        Mh = world_m(fr, 'hips')
        Rh = Mh.to_3x3().normalized()
        for tag, s in SIDES:
            fold = 0.42 if tag == 'L' else 0.28
            tuck = Mh @ (ank[tag] + Vector((0.0, -fold * LEG, 0.55 * fold * LEG)))
            tgt = ank[tag].lerp(tuck, gone)
            hint = (Rh @ knee_hint[tag]).lerp(Rh @ Vector((0.0, -0.6, 0.8)), gone)
            end = Rh @ Matrix.Rotation(math.radians(-25 * gone), 3, 'X')
            fr.ik[f'leg.{tag}'] = {'target': tgt, 'hint': hint, 'end': Quaternion().slerp(end.to_quaternion(), gone).to_matrix()}
        ears(fr, t, 10 * fall, 0)
        tail(fr, t, -10 * fall, 0, 1.0, curl=20 * fall)
        capes(fr, t, 10 * fall)
        wings(fr, 0.2 * fall)
        return fr

    def p_win(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.04, 0.36)
        spin = 360 * A.step_ease(t, 0.42, 0.82)
        fr.o('root', 0, 0, mm(0.14) * air)
        fr.r('root', 0, 0, spin)
        land = A.pulse(t, 0.34, 0.44)
        body(fr, crouch=rest_crouch(False) + 0.1 * LEG * land, lean=-8 * air)
        for tag, _s in SIDES:
            plant(fr, tag, dz=0.12 * LEG * air, pitch=15 * air)
        up = A.step_ease(t, 0.0, 0.15)
        for tag, s in SIDES:
            v = sh[tag] + Vector((s * (0.35 if tag == 'L' else 0.5) * ARM, -0.1 * ARM, (0.85 if tag == 'L' else 0.5) * ARM))
            reach(fr, tag, body_point(fr, v), w=up, hint=Vector((s, 0.4, -0.3)), hand=(-20, 0, 0))
        fr.r('head', -10 * air, 10 * A.wave(t, 2.0) * A.step_ease(t, 0.84, 0.9), 0)
        ears(fr, t, -8, 12, 3.0)
        tail(fr, t, 26, 30, 4.0)
        capes(fr, t, 18 * air + 10, 10, 2.0)
        wings(fr, 0.8, 22 * A.wave(t, 3.0))
        jaw(fr, 18)
        return fr

    # ---- strike: 24 frames, impact at 13 (the same for every style)
    def p_strike(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.42)
        go = A.pulse(t, 0.3, 0.75)
        c0 = rest_crouch(False)
        if style == 'punch':
            # the left fist (the review camera's side) chambers at the ribs as the body coils (the left shoulder back: +z),
            # then it drives forward at head height as the left shoulder turns in (-z) and the right fist pulls back
            body(fr, crouch=c0 + 0.06 * LEG * (ant + go), dy=0.05 * LEG * ant - 0.12 * LEG * go, lean=-4 * ant + 12 * go,
                 yaw=22 * ant - 28 * go)
            plant(fr, 'L', dy=-0.18 * LEG * go, out=0.1 * HW)
            plant(fr, 'R', dy=0.1 * LEG, out=0.1 * HW, pitch=toe_lift_pitch(0.04 * LEG * go), dz=0.04 * LEG * go)
            cham = sh['L'] + Vector((0.05 * SW, 0.1 * ARM, -0.45 * ARM))
            out_ = sh['L'] + Vector((-0.25 * SW, -1.0 * ARM, 0.05 * ARM))
            k = _ramp(t, 0.32, 0.5)
            reach(fr, 'L', body_point(fr, cham.lerp(out_, k)), w=min(1.0, 2.5 * (ant + go)), hand=(-20, 0, 0))
            p = sh['R'] + Vector((0.3 * SW, -0.55 * ARM, 0.05 * ARM))
            reach(fr, 'R', body_point(fr, p), w=min(1.0, 2.0 * (ant + go)), hand=(-25, 0, 0))
        elif style == 'swipe':
            # the left claw rises high and back on the wind-up, then rakes down and across in front of the face
            body(fr, crouch=c0 + 0.08 * LEG * ant, dy=-0.1 * LEG * go, lean=-6 * ant + 14 * go, yaw=18 * ant - 26 * go)
            plant(fr, 'L', dy=-0.12 * LEG * go, out=0.1 * HW)
            plant(fr, 'R', dy=0.06 * LEG, out=0.1 * HW)
            hi = sh['L'] + Vector((0.4 * SW, 0.15 * ARM, 0.75 * ARM))
            a0 = sh['L'] + Vector((0.1 * SW, -0.8 * ARM, 0.45 * ARM))
            a1 = sh['L'] + Vector((-1.6 * SW, -0.7 * ARM, -0.35 * ARM))
            k = _ramp(t, 0.36, 0.66)
            tgt = hi.lerp(a0, _ramp(t, 0.28, 0.42)) if t < 0.42 else a0.lerp(a1, k)
            reach(fr, 'L', body_point(fr, tgt), w=min(1.0, 2.5 * (ant + go)), hint=Vector((1, 0.6, -0.4)), hand=(15, 0, 0))
            hang(fr, swing={'R': -15 * go}, bend=40, out=15 * go)
            fr.rot.pop('upperarm.L', None)
            fr.rot.pop('forearm.L', None)
            jaw(fr, 18 * go)
        elif style == 'headbutt':
            # leans back and crouches, then springs forward and up a little, the crown leading, the arms swept back
            air = A.pulse(t, 0.38, 0.7)
            fr.o('root', 0, 0, mm(0.08) * air)
            body(fr, crouch=c0 + 0.14 * LEG * ant, dy=0.08 * LEG * ant - 0.22 * LEG * go, lean=-18 * ant + 42 * go, gaze=0.2)
            for nm in NECK:
                fr.r(nm, (-10 * ant + 16 * go) / len(NECK))
            fr.r('head', -12 * ant + 22 * go, 0, 0)
            for tag, _s in SIDES:
                plant(fr, tag, dz=0.08 * LEG * air, dy=-0.1 * LEG * go * (1 if tag == 'L' else 0.3), pitch=20 * air)
            hang(fr, swing=25 * ant + 55 * go, bend=30, out=12 * go)
            jaw(fr, 22 * go)
        elif style == 'slam':
            # both fists rise overhead as the chest arches back, then come down together to the ground in front: the
            # hips drop, the body pitches over, a beat on the ground, then it straightens
            hold_ = A.step_ease(t, 0.42, 0.5) * (1 - A.step_ease(t, 0.72, 0.95))
            body(fr, crouch=c0 + 0.02 * LEG * ant + 0.2 * LEG * hold_, lean=-16 * ant + 34 * hold_, gaze=0.5)
            feet(fr, out=0.12 * HW)
            sl = P.get('slam') or {}        # a recipe's own overhead and ground points for the left fist (mirrored)
            for tag, s in SIDES:
                over = _mirror(sl['over'], s) if sl.get('over') else sh[tag] + Vector((-s * 0.3 * SW, 0.0, 0.85 * ARM))
                ground = _mirror(sl['ground'], s) if sl.get('ground') else Vector((s * 0.45 * SW, ank[tag].y - 0.35 * LEG - 0.25 * ARM, 0.05 * LEG))
                if t < 0.42:
                    tgt = body_point(fr, over)
                    w = _ramp(t, 0.02, 0.3)          # up and held overhead until the swing down
                else:
                    tgt = body_point(fr, over).lerp(ground, _ramp(t, 0.42, 0.52))
                    w = 1.0 - A.step_ease(t, 0.75, 1.0)
                reach(fr, tag, tgt, w=w, hint=Vector((s * 0.6, 0.6, -0.2)), hand=(-30, 0, 0))
            jaw(fr, 16 * go)
        elif style == 'thrust':
            # a fencing lunge with the tail's blade: side-on and low, the tail swings round under the left arm until
            # its tip points straight ahead at chest height, then the front (left) foot steps out and it drives in
            body(fr, crouch=c0 + 0.12 * LEG * (ant + 0.6 * go), dy=-0.22 * LEG * go, lean=-4 * ant + 14 * go, yaw=-30 * ant - 18 * go)
            plant(fr, 'L', dy=-0.32 * LEG * go, out=0.15 * HW)
            plant(fr, 'R', dy=0.08 * LEG, out=0.15 * HW, dz=0.03 * LEG * go, pitch=toe_lift_pitch(0.03 * LEG * go))
            swing = _ramp(t, 0.05, 0.4) * (1 - _ramp(t, 0.8, 1.0))
            n = len(TAIL)
            for i, b in enumerate(TAIL):
                lift = ((thrust_lift[i] if i < len(thrust_lift) else 0.0) * swing if isinstance(thrust_lift, list)
                        else thrust_lift * swing / max(1, n))
                fr.r(b, lift, 0, thrust_swing * swing / max(1, n) * (1.0 + 0.2 * (i - (n - 1) / 2) / max(1, n)))
            if PUFF:
                fr.r('tail.puff', 0, 0, 0)
            hang(fr, swing={'L': -10 * go, 'R': -60 * (ant + go)}, bend=50, out=25 * (ant + go))
            capes(fr, t, 34 * (ant + go), 10 * go, 1.0)
            jaw(fr, 8 * go)
        elif style == 'pounce':
            # a leap at the target from a deep crouch: the body stretches out flat, both claws reach forward overhead,
            # the legs trail back; it lands on the end
            air = A.pulse(t, 0.32, 0.86)
            fr.o('root', 0, 0, mm(0.16) * air)
            body(fr, crouch=c0 + 0.22 * LEG * ant + 0.1 * LEG * A.pulse(t, 0.8, 1.0), dy=-0.3 * LEG * air, lean=-6 * ant + 40 * air, gaze=0.8)
            for tag, s in SIDES:
                plant(fr, tag, dy=0.15 * LEG * air, dz=0.16 * LEG * air, pitch=35 * air)
                p = sh[tag] + Vector((-s * 0.1 * SW, -0.85 * ARM, 0.35 * ARM))
                reach(fr, tag, body_point(fr, p), w=min(1.0, 2.0 * air + 0.6 * ant), hand=(-35, 0, 0))
            wings(fr, 0.05)
            jaw(fr, 26 * air)
        elif style == 'charge':
            # head down and low, then a hard drive forward with the head leading, the arms tucked to the chest
            body(fr, crouch=c0 + 0.12 * LEG * ant + 0.08 * LEG * go, dy=0.06 * LEG * ant - 0.3 * LEG * go, lean=10 * ant + 30 * go, gaze=0.3)
            for nm in NECK:
                fr.r(nm, (14 * ant + 12 * go) / len(NECK))
            fr.r('head', 10 * ant + 10 * go, 0, 0)
            plant(fr, 'L', dy=-0.3 * LEG * go, out=0.1 * HW)
            plant(fr, 'R', dy=0.15 * LEG * go, dz=0.05 * LEG * go, pitch=toe_lift_pitch(0.05 * LEG * go), out=0.1 * HW)
            for tag, s in SIDES:
                p = sh[tag] + Vector((-s * 0.25 * SW, -0.35 * ARM, -0.25 * ARM))
                reach(fr, tag, body_point(fr, p), w=min(1.0, 2.5 * (ant + go)), hand=(-30, 0, 0))
            jaw(fr, 12 * go)
        elif style == 'gust':
            # the wings rise and spread high on the wind-up, then one great downbeat drives a gust forward with both
            # palms thrust out (without wings, the palms alone)
            body(fr, crouch=c0 + 0.05 * LEG * ant + 0.06 * LEG * go, lean=-14 * ant + 14 * go, gaze=0.6)
            feet(fr, out=0.1 * HW, stagger=0.06 * LEG)
            wings(fr, min(1.0, 1.8 * ant + go), -35 * ant + 45 * go)
            for tag, s in SIDES:
                up = sh[tag] + Vector((s * 0.3 * SW, 0.0, 0.6 * ARM))
                out_ = sh[tag] + Vector((-s * 0.2 * SW, -0.9 * ARM, 0.15 * ARM))
                tgt = up.lerp(out_, _ramp(t, 0.36, 0.52))
                reach(fr, tag, body_point(fr, tgt), w=min(1.0, 2.2 * (ant + go)), hand=(60, 0, 0))
            jaw(fr, 20 * go)
        if style != 'thrust':
            tail(fr, t, 16 * ant - 6 * go)
            capes(fr, t, 22 * go - 8 * ant)
        ears(fr, t, 8 * ant - 10 * go, 0)
        if style not in ('gust', 'pounce'):
            wings(fr, 0.35 * ant + 0.9 * go, -20 * ant + 30 * go)
        return fr

    def p_cast(t: float) -> Frame:
        """Both hands rise overhead, gathering (a shimmer), and push forward at the release; wings spread and beat."""
        fr = Frame()
        up = A.step_ease(t, 0.0, 0.3) * (1 - A.step_ease(t, 0.7, 1.0))
        rel = A.pulse(t, 0.48, 0.72)
        body(fr, crouch=rest_crouch(False) + 0.04 * LEG * up, lean=-12 * up + 16 * rel, gaze=0.6)
        feet(fr, out=0.08 * HW, stagger=0.05 * LEG)
        for tag, s in SIDES:
            hi = sh[tag] + Vector((-s * 0.25 * SW, -0.25 * ARM, 0.8 * ARM + 0.02 * ARM * A.wave(t, 6.0)))
            fwd = sh[tag] + Vector((-s * 0.3 * SW, -0.95 * ARM, 0.2 * ARM))
            tgt = hi.lerp(fwd, _ramp(t, 0.5, 0.6) * (1 - _ramp(t, 0.72, 0.85)))
            reach(fr, tag, body_point(fr, tgt), w=up, hint=Vector((s, 0.3, -0.5)), hand=(40 * rel, 0, 0))
        tail(fr, t, 14, 6)
        capes(fr, t, 10 * up + 25 * rel, 6 * up, 3.0)
        wings(fr, 0.9 * up, 6 * A.wave(t, 4.0) * up + 25 * rel)
        jaw(fr, 18 * up)
        return fr

    def p_shove(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.36)
        go = A.pulse(t, 0.28, 0.7)
        body(fr, crouch=rest_crouch(False) + 0.06 * LEG * (ant + go), dy=0.05 * LEG * ant - 0.14 * LEG * go, lean=-6 * ant + 16 * go)
        plant(fr, 'L', dy=-0.12 * LEG * go)
        plant(fr, 'R', dy=0.1 * LEG, dz=0.03 * LEG * go, pitch=toe_lift_pitch(0.03 * LEG * go))
        for tag, s in SIDES:
            pull = sh[tag] + Vector((-s * 0.1 * SW, -0.3 * ARM, -0.2 * ARM))
            push = sh[tag] + Vector((-s * 0.15 * SW, -0.95 * ARM, -0.05 * ARM))
            reach(fr, tag, body_point(fr, pull.lerp(push, _ramp(t, 0.28, 0.42))), w=min(1.0, 2.5 * (ant + go)), hand=(60, 0, 0))
        tail(fr, t, 10 * ant)
        capes(fr, t, 14 * go)
        return fr

    # ---- the list (same names, lengths, markers and faces as the quadruped)
    walk_speed = stride_w / (0.6 * 30 / A.FPS)
    clip('idle', 120, p_idle, step=2)
    clip('idle_happy', 90, p_idle_happy, step=2, faces=[(1, 'happy')])
    clip('idle_tired', 150, p_idle_tired, step=3, faces=[(1, 'tired')])
    clip('idle_sad', 150, p_idle_sad, step=3, faces=[(1, 'sad')])
    clip('idle_sick', 150, p_idle_sick, step=2, faces=[(1, 'sick')])
    clip('sleep', 150, p_sleep, step=3, faces=[(1, 'sleepy')], shut=lambda t: 1.0)
    clip('eat', 60, p_eat)
    clip('pet', 75, p_pet, faces=[(1, 'happy')])
    clip('look_around', 90, p_look)
    clip('hop', 24, p_hop, loop=False, markers=[('land', 20)])
    clip('celebrate', 60, p_celebrate, markers=[('land', 22), ('land', 43)], faces=[(1, 'happy')])
    clip('walk', 30, p_walk, root_speed=walk_speed, markers=step_markers(30))
    clip('run', 20, p_run, root_speed=stride_r / (0.38 * 20 / A.FPS), markers=step_markers(20))
    clip('sit_down', 24, p_sit_down, loop=False, hold=True)
    clip('sit', 120, p_sit, step=2)
    clip('dizzy', 60, p_dizzy, faces=[(1, 'dizzy')])
    clip('battle_idle', 40, p_battle_idle)
    clip('step_fwd', 24, lambda t: p_step(t, False), root_speed=stride_s / (0.6 * 24 / A.FPS), markers=step_markers(24))
    clip('step_back', 24, lambda t: p_step(t, True), root_speed=0.8 * stride_s / (0.6 * 24 / A.FPS), markers=step_markers(24))
    clip('dash', 20, p_dash, root_speed=stride_d / (0.32 * 20 / A.FPS), markers=step_markers(20))
    clip('strike', 24, p_strike, loop=False, markers=[('impact', 13)], faces=[(1, 'angry'), (20, 'neutral')])
    clip('cast', 36, p_cast, loop=False, markers=[('release', 20)], faces=[(1, 'strain'), (28, 'neutral')])
    clip('shove', 24, p_shove, loop=False, markers=[('impact', 10)])
    clip('hit', 15, p_hit, loop=False, faces=[(1, 'surprised'), (12, 'neutral')], shut=lambda t: 0.85 * A.pulse(t, 0.0, 0.7))
    clip('hit_heavy', 24, p_hit_heavy, loop=False, faces=[(1, 'strain'), (18, 'neutral')], shut=lambda t: 0.9 * A.pulse(t, 0.0, 0.75))
    clip('ko', 36, p_ko, loop=False, hold=True, faces=[(1, 'strain'), (20, 'dizzy')],
         shut=lambda t: max(0.8 * A.pulse(t, 0.0, 0.3), A.step_ease(t, 0.35, 0.6)))
    clip('win', 60, p_win, markers=[('land', 22)], faces=[(1, 'happy')])
    stance_s = 0.56
    strafe_speed = min(0.35 * LEG, 1.1 * HW) / (stance_s * 24 / A.FPS)
    clip('strafe_l', 24, lambda t: p_strafe(t, 1), root_speed=strafe_speed, markers=[('step', 1), ('step', 13)])
    clip('strafe_r', 24, lambda t: p_strafe(t, -1), root_speed=strafe_speed, markers=[('step', 1), ('step', 13)])
    clip('sidestep_l', 8, lambda t: p_sidestep(t, 1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    clip('sidestep_r', 8, lambda t: p_sidestep(t, -1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    return made


# --------------------------------------------------------------------------- wings (the quadruped's math, shared format)
def _frame(a: Vector, b: Vector) -> Matrix:
    x = a.normalized()
    z = x.cross(b)
    if z.length < 1e-8:
        z = x.orthogonal()
    z.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def wing_spread_quats(P: dict, side: int) -> list[tuple[str, Quaternion]]:
    """Each wing bone's rotation (relative to its parent, world-aligned at rest) from the folded rest pose to the
    recipe's spread pose: the same construction as plans/quadruped.py (exact at the end points; clips slerp)."""
    w = wings_of(P)
    rest, sp = U.wing_points(w, side), U.wing_points(w, side, spread=True)
    S, E, W = Vector(rest['shoulder']), Vector(rest['elbow']), Vector(rest['wrist'])
    E2, W2 = Vector(sp['elbow']), Vector(sp['wrist'])
    T = [Vector(t) for t in rest['fingers']]
    T2 = [Vector(t) for t in sp['fingers']]
    R1 = _frame(E2 - S, W2 - E2) @ _frame(E - S, W - E).transposed()
    m = sum((t - W for t in T), Vector()) / len(T)
    m2 = sum((t - W2 for t in T2), Vector()) / len(T2)
    R1i = R1.transposed()
    R2 = _frame(R1i @ (W2 - E2), R1i @ m2) @ _frame(W - E, m).transposed()
    R12i = (R1 @ R2).transposed()
    names = U.wing_bone_names(w, side)
    out = [(names[0], R1.to_quaternion()), (names[1], R2.to_quaternion())]
    for k, (t, t2) in enumerate(zip(T, T2)):
        out.append((names[2 + k], (t - W).rotation_difference(R12i @ (t2 - W2))))
    return out
