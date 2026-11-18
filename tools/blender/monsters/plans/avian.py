"""The avian body plan (ART_2_PLAN §4, batch 6): rig template, sockets, springs and the clip generators for birds:
Galeheron (a long-legged, long-necked wind heron with streaming crest and tail plumes) and Paladove (young: a round
puffball dove; grown: a stately dove-knight with four wings, breastplate, shield and halo).

A recipe selects it with `PLAN = 'avian'` (tools/blender/monsters/breeds/RECIPE.md, "Avian plan"). The same build
(build_ultra.py) drives it as every other plan: rig_specs, sockets, springs, chain_groups, heatless, make_clips,
STAR_CLIPS, MOVE_CLIPS, FLY_CLIPS (a rig with wings: Hearthwing's precedent; the game flies any look whose file holds
all four), ROOT_DIRS and KO_ROLL (ko lies down at `body_width`, measured and settled by the build).

Space: metres; the monster faces −Y, Z is up, +X is its left. Model it standing, wings folded. From rig_p() (`P`):
  hip                  the pelvis: `hips` (parent `root`) runs from it to the middle of the body
  chest                the shoulders (where the neck and the wings start): `chest` (parent `hips`)
  neck                 [p0 … pN] → neck.1..N from the shoulders to the back of the head (Galeheron's S, Paladove's
                       one bone); `head` runs to head_tip, the beak's lower half is `jaw`
  head_c, head_r       the face
  legs                 the left leg {'hip', 'knee', 'ankle', 'toe', 'toe_tip'?}, mirrored: thigh (hidden in the body),
                       shin (the drumstick), tarsus (the long bare part, kept upright by the IK) and toe (kept flat)
  wings                the main pair: a wing spec (lib/ultra.py wing_points: shoulder, elbow, wrist, fingers, spread,
                       name, parent); `more_wings` [] adds pairs (grown Paladove's lower 'wingb', following the upper)
Rotations are world-aligned degrees relative to the parent at rest (lib.anim.ClipBuilder.rot). No clip scales a bone
(lib/anim.py ClipBuilder.scale maps a world scale through abs() of the rest axes, which is wrong on tilted bones).
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Quaternion, Vector

from lib import anim as A
from lib import common as C
from lib import ultra as U
from lib.rig import BoneSpec
from monsters.plans import kin as K
from monsters.plans.biped import wing_spread_quats as _biped_wing_quats
from monsters.plans.kin import Frame, mirror

PLAN = 'avian'
SIDES = K.SIDES
KO_ROLL = 80.0
STRIKE_STYLES = ('peck', 'buffet', 'gust', 'kick', 'beam')
CAST_STYLES = ('gust', 'beam', 'call')
KO_STYLES = ('roll', 'back')
SPRINGS = []                # Art 2.0 compatibility only; the Ultra build calls springs(P)
KINDS = ('plume', 'crest', 'tassel', 'tail')
HEATLESS_KINDS = ('plume', 'crest', 'tassel')

SIDESTEP_DISTANCE = 1.4 * 100 / 150
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}
STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']
FLY_CLIPS = ['fly_takeoff', 'fly', 'fly_cast', 'fly_land']
# gaits: (frames, stride as a share of the leg's reach, the planted share of the cycle, foot lift as a share of the leg)
GAITS = {'walk': (30, 0.55, 0.6, 0.16), 'run': (20, 0.85, 0.42, 0.22), 'dash': (20, 1.0, 0.36, 0.26),
         'step_fwd': (24, 0.45, 0.6, 0.14), 'step_back': (24, 0.38, 0.6, 0.12), 'strafe': (24, 0.4, 0.6, 0.14)}


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def _v(p) -> Vector:
    return Vector(p)


def neck_points(P: dict) -> list[Vector]:
    return [_v(p) for p in (P.get('neck') or [])]


def neck_names(P: dict) -> list[str]:
    n = len(neck_points(P))
    return [f'neck.{i + 1}' for i in range(n - 1)] if n >= 2 else []


def head_base(P: dict) -> Vector:
    pts = neck_points(P)
    if len(pts) >= 2:
        return pts[-1]
    return _v(P['head_c']) + Vector((0.0, 0.6 * float(P['head_r']), -0.3 * float(P['head_r'])))


def head_tip(P: dict) -> Vector:
    if P.get('head_tip'):
        return _v(P['head_tip'])
    return _v(P['head_c']) + Vector((0.0, -1.0 * float(P['head_r']), 0.0))


def jaw_points(P: dict) -> tuple[Vector, Vector]:
    """The beak's lower half, from its hinge to its tip."""
    if P.get('jaw'):
        return _v(P['jaw']['head']), _v(P['jaw']['tail'])
    hc, hr = _v(P['head_c']), float(P['head_r'])
    return hc + Vector((0, -0.6 * hr, -0.2 * hr)), hc + Vector((0, -1.6 * hr, -0.25 * hr))


def legs(P: dict) -> list[dict]:
    """The two legs: {'tag', 's', 'thigh', 'shin', 'tarsus', 'toe' (bone names; toe None without a toe_tip), 'hip',
    'knee', 'ankle', 'toe_base', 'toe_tip'}."""
    lg = P['legs']
    out = []
    for tag, s in SIDES:
        tip = mirror(lg['toe_tip'], s) if lg.get('toe_tip') else None
        out.append({'tag': tag, 's': s, 'thigh': f'thigh.{tag}', 'shin': f'shin.{tag}', 'tarsus': f'tarsus.{tag}',
                    'toe': f'toe.{tag}' if tip is not None else None, 'hip': mirror(lg['hip'], s), 'knee': mirror(lg['knee'], s),
                    'ankle': mirror(lg['ankle'], s), 'toe_base': mirror(lg['toe'], s), 'toe_tip': tip,
                    'parent': lg.get('parent', 'hips')})
    return out


def wing_specs(P: dict) -> list[dict]:
    """The main pair `wings` (one spec, as every plan and the shape preview read it) and any `more_wings` (a list:
    grown Paladove's lower pair, named apart, e.g. 'wingb')."""
    w = P.get('wings')
    main = [w] if isinstance(w, dict) else list(w or [])
    return main + list(P.get('more_wings') or [])


def chains(P: dict) -> list[dict]:
    """Plumes and crests: {'name', 'kind', 'parent', 'points', 'stiff', 'heat', 'mirror', 'spring'}; a tail fan is a
    few `plume` chains on `hips` (mirror: True for a pair), a crest a few on `head`."""
    out = []
    for m in P.get('chains') or []:
        kind = m.get('kind', 'plume')
        if kind not in KINDS:
            raise ValueError(f"chain {m.get('name')}: kind {kind!r}, one of {', '.join(KINDS)}")
        nm0 = m.get('name', kind)
        twins = [(nm0 + 'L', 1), (nm0 + 'R', -1)] if m.get('mirror') else [(nm0, 1)]
        for nm, s in twins:
            pts = [mirror(p, s) for p in m['points']]
            out.append({'name': nm, 'kind': kind, 'parent': m.get('parent', 'hips'), 'points': pts, 'side': s,
                        'stiff': float(m.get('stiff', 0.0)), 'heat': bool(m.get('heat', kind not in HEATLESS_KINDS)),
                        'spring': bool(m.get('spring', True)), 'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)],
                        'dir': (pts[-1] - pts[0]).normalized() if (pts[-1] - pts[0]).length > 1e-6 else Vector((0, 1, 0))})
    return out


def _style(P: dict, key: str, allowed: tuple, default: str) -> str:
    st = P.get(key, default)
    if st not in allowed:
        raise ValueError(f"{key} {st!r}: one of {', '.join(allowed)}")
    return st


def strike_style(P: dict) -> str:
    return _style(P, 'strike_style', STRIKE_STYLES, 'peck')


def cast_style(P: dict) -> str:
    return _style(P, 'cast_style', CAST_STYLES, 'gust')


def ko_style(P: dict) -> str:
    return _style(P, 'ko_style', KO_STYLES, 'roll')


def springs(P: dict) -> list[dict]:
    return [{'kind': m['kind'], 'chain': m['bones']} for m in chains(P) if m['spring']]


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → kind for CLIP_CALM: 'neck', each chain by name or kind, each wing by its name ('wing',
    'wingb': kind 'wing'), 'leg' (thigh, shin, tarsus, toe)."""
    out = {'neck': 'neck'}
    for m in chains(P):
        out[m['name']] = m['kind']
    for w in wing_specs(P):
        out[w.get('name', 'wing')] = 'wing'
    for p in ('thigh', 'shin', 'tarsus', 'toe'):
        out[p] = 'leg'
    return out


def heatless(P: dict) -> set[str]:
    """Plumes, crests and tassels (unless heat=True) and the wings (skin them with U.segment_weights / the membrane
    helpers): the recipe weights them."""
    out = {m['name'] for m in chains(P) if not m['heat']}
    out |= {w.get('name', 'wing') for w in wing_specs(P)}
    return out


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    hip, ch = _v(P['hip']), _v(P['chest'])
    mid = hip.lerp(ch, 0.5)
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk),
        BoneSpec('hips', tuple(hip), tuple(mid), 'root', radius=0.25 * sk),
        BoneSpec('chest', tuple(mid), tuple(ch), 'hips', connect=True, radius=0.25 * sk),
    ]
    npts, names = neck_points(P), neck_names(P)
    for i, nm in enumerate(names):
        specs.append(BoneSpec(nm, tuple(npts[i]), tuple(npts[i + 1]), 'chest' if i == 0 else names[i - 1], connect=i > 0,
                              radius=0.08 * sk))
    hr = float(P['head_r'])
    specs.append(BoneSpec('head', tuple(head_base(P)), tuple(head_tip(P)), names[-1] if names else 'chest', connect=bool(names),
                          radius=max(0.12 * sk, 1.2 * hr)))
    jh, jt = jaw_points(P)
    specs.append(BoneSpec('jaw', tuple(jh), tuple(jt), 'head', radius=0.5 * hr))
    for lg in legs(P):
        specs.append(BoneSpec(lg['thigh'], tuple(lg['hip']), tuple(lg['knee']), lg['parent'], radius=0.07 * sk))
        specs.append(BoneSpec(lg['shin'], tuple(lg['knee']), tuple(lg['ankle']), lg['thigh'], connect=True, radius=0.06 * sk))
        specs.append(BoneSpec(lg['tarsus'], tuple(lg['ankle']), tuple(lg['toe_base']), lg['shin'], connect=True, radius=0.04 * sk))
        if lg['toe']:
            specs.append(BoneSpec(lg['toe'], tuple(lg['toe_base']), tuple(lg['toe_tip']), lg['tarsus'], connect=True, radius=0.04 * sk))
    for w in wing_specs(P):
        for s in (1, -1):
            for b, h, t, par in U.wing_bones(w, s):
                specs.append(BoneSpec(b, tuple(map(float, h)), tuple(map(float, t)), par, radius=0.08 * sk))
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'head'), radius=0.06 * sk))
    for m in chains(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.05 * sk))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """The game's seven (socket_paw_L / _R at the first wing's wrists: a wing beat's effect starts there), socket_core
    at the breast (a beam), socket_foot_L / _R, socket_wing_<name>_L / _R, socket_<chain>, socket_<prop>."""
    sk = size_of(P)
    hc, hr = _v(P['head_c']), float(P['head_r'])
    hip, ch = _v(P['hip']), _v(P['chest'])
    _jh, jt = jaw_points(P)
    out = {
        'socket_head': ('head', tuple(hc + Vector((0, 0, hr)))),
        'socket_crown': ('head', tuple(hc + Vector((0, 0, hr + 0.1 * sk)))),
        'socket_back': ('chest', tuple(hip.lerp(ch, 0.5) + Vector((0, 0.05 * sk, 0.12 * sk)))),
        'socket_mouth': ('jaw', tuple(jt)),
        'socket_core': ('chest', tuple(ch + Vector((0, -0.08 * sk, -0.1 * sk)))),
    }
    ws = wing_specs(P)
    for lg in legs(P):
        out[f"socket_foot_{lg['tag']}"] = (lg['toe'] or lg['tarsus'], tuple(lg['toe_tip'] if lg['toe_tip'] is not None else lg['toe_base']))
    for i, w in enumerate(ws):
        for s in (1, -1):
            q = U.wing_points(w, s)
            nm = w.get('name', 'wing')
            out[f'socket_{nm}_{U.wing_tag(s)}'] = (U.wing_bone_names(w, s)[1], tuple(map(float, q['wrist'])))
            if i == 0:
                out[f'socket_paw_{U.wing_tag(s)}'] = out[f'socket_{nm}_{U.wing_tag(s)}']
                out[f'socket_wing_{U.wing_tag(s)}'] = out[f'socket_{nm}_{U.wing_tag(s)}']
    for tag, s in SIDES:
        out.setdefault(f'socket_paw_{tag}', out[f'socket_foot_{tag}'])
    tail = next((m for m in chains(P) if m['kind'] in ('plume', 'tail') and m['parent'] == 'hips'), None)
    out['socket_tail'] = (tail['bones'][-1], tuple(tail['points'][-1])) if tail else ('hips', tuple(2 * hip - ch))
    for m in chains(P):
        out[f"socket_{m['name']}"] = (m['bones'][-1], tuple(m['points'][-1]))
    for pr in P.get('props', []) or []:
        out[f"socket_{pr['name']}"] = (f"prop.{pr['name']}", tuple(pr['tail']))
    return out


def wing_quats(P: dict) -> dict[str, list[tuple[str, Quaternion]]]:
    """Each wing's rotations from folded to spread (the biped's construction, exact at the ends; clips slerp), by wing
    name and side tag."""
    out = {}
    for w in wing_specs(P):
        for s in (1, -1):
            out[f"{w.get('name', 'wing')}.{U.wing_tag(s)}"] = _biped_wing_quats({'wings': w}, s)
    return out


# --------------------------------------------------------------------------- clips
def make_clips(cb: A.ClipBuilder, P: dict, only: list[str] | None = None) -> list[A.ClipMeta]:
    rig = K.Rig(cb.arm)
    has = rig.has
    sk = size_of(P)
    made: list[A.ClipMeta] = []
    style, cstyle, kstyle = strike_style(P), cast_style(P), ko_style(P)
    LEGS = [lg for lg in legs(P) if has(lg['thigh'])]
    NECK = [n for n in neck_names(P) if has(n)]
    CH = chains(P)
    WQ = {k: v for k, v in wing_quats(P).items() if has(v[0][0])}
    # the lower pair (grown Paladove's) follows the upper one at `lower_k` of its opening and beat
    WLOW = {f"{w.get('name', 'wing')}": float(w.get('follow', 0.75 if i else 1.0)) for i, w in enumerate(wing_specs(P))}
    JAW = bool(P.get('jaw_open', False))
    CLOSED = P.get('blink_closed')
    hip = _v(P['hip'])
    HZ = hip.z
    ko_roll = float(P.get('ko_roll', KO_ROLL))
    ko_pitch = float(P.get('ko_pitch', 95.0))
    lift_tab = P.get('ko_lift') or []
    strike_yaw = float(P.get('strike_yaw', 0.0))
    hop_k = float(P.get('hop', 1.0))
    FLY = bool(P.get('fly', True)) and bool(WQ)

    def mm(v: float) -> float:
        return v * sk

    for lg in LEGS:
        lg['l1'] = rig.length(lg['thigh'])
        lg['l2'] = rig.length(lg['shin'])
        lg['reach'] = lg['l1'] + lg['l2']
        lg['rest_hip'] = rig.head[lg['thigh']].copy()
        lg['rest_ankle'] = rig.head[lg['tarsus']].copy()
        lg['rest_toe'] = rig.tail[lg['tarsus']].copy()
        # a bird's visible knee (its ankle, the heel) bends backward; the hidden knee forward: the rest pose's own plane
        lg['hint'] = rig.bend_hint(lg['thigh'], lg['shin'], Vector((lg['s'] * 0.2, -1.0, 0.0)).normalized())
    LEG = (sum(lg['reach'] + (lg['rest_ankle'] - lg['rest_toe']).length for lg in LEGS) / len(LEGS)) if LEGS else mm(0.3)

    def body_points() -> np.ndarray | None:
        ob = bpy.data.objects.get('lo_body')
        if ob is None or ob.type != 'MESH':
            return None
        keep = {'hips', 'chest'}
        names = {g.index: g.name for g in ob.vertex_groups}
        pts = [v.co[:] for v in ob.data.vertices if v.groups and names.get(max(v.groups, key=lambda g: g.weight).group) in keep]
        if len(pts) < 20:
            return None
        a = np.array(pts) - np.array(hip[:])
        return a[:: max(1, len(a) // 3000)]

    BODY = body_points()
    FLOOR = min(mm(0.003), HZ + float(BODY[:, 2].min())) if BODY is not None else -1.0
    ROOM = max(0.0, HZ + float(BODY[:, 2].min())) if BODY is not None else 0.5 * HZ
    C.log(f'avian: {len(LEGS)} legs (reach {LEG:.3f} m), neck {len(NECK)}, wings {sorted(WQ)}, room under the body {ROOM:.3f} m, '
          f'flight {FLY}')

    def reach_drop(shift: Vector, margin: float = 0.97) -> float:
        need = 0.0
        for lg in LEGS:
            d = lg['rest_hip'] - (lg['rest_ankle'] + shift)
            r2 = (margin * lg['reach']) ** 2 - d.x * d.x - d.y * d.y
            need = max(need, d.z - math.sqrt(max(0.0, r2)))
        return min(max(0.0, need), 0.6 * ROOM)

    stride_k = float(P.get('stride', 1.0))

    def stride_of(kind: str) -> float:
        return GAITS[kind][1] * LEG * stride_k

    def speed_of(kind: str) -> float:
        n, _s, duty, _l = GAITS[kind]
        return stride_of(kind) / (duty * n / A.FPS)

    DROP = {k: max(reach_drop(Vector((stride_of(k) / 2, 0, 0))), reach_drop(Vector((0, stride_of(k) / 2, 0))),
                   reach_drop(Vector((0, -stride_of(k) / 2, 0)))) for k in GAITS}

    # ---- keying
    def clip(name: str, n: int, pose, loop: bool = True, hold: bool = False, root_speed: float = 0.0, step: int = 1,
             markers=(), faces=(), shut=None) -> None:
        if only and name not in only:
            return
        cb.begin(name, n, loop=loop, hold=hold, root_speed=root_speed)
        for f in K.frames_of(n, step):
            t = (f - 1) / n
            fr = pose(t)
            K.clip_bump(P, name, t, fr, sk)
            K.key_frame(cb, rig, f, fr)
        if shut is not None:
            K.eyes_shut(cb, CLOSED, n, shut, step)
        for mk, f in markers:
            cb.marker(mk, f)
        for f, face in faces:
            cb.face(f, face)
        made.append(cb.end())

    # ---- posing helpers
    def body(fr: Frame, dz: float = 0.0, dy: float = 0.0, dx: float = 0.0, pitch: float = 0.0, roll: float = 0.0,
             yaw: float = 0.0, guard: bool = True) -> None:
        """The body about the pelvis (+pitch tips it forward), its belly never under the ground."""
        if guard and BODY is not None:
            low = HZ + dz + float((BODY @ np.array(K.m3((pitch, roll, yaw)))[2]).min())
            if low < FLOOR:
                dz += FLOOR - low
        fr.o('hips', dx, dy, dz)
        fr.r('hips', pitch, roll, yaw)
        fr.r('chest', 0, 0, 0)

    def breathe(fr: Frame, t: float, rate: float = 1.0, depth: float = 1.0) -> None:
        fr.r('chest', -1.5 * depth * A.wave(t, rate), 0, 0)

    def look(fr: Frame, pitch: float = 0.0, yaw: float = 0.0, tilt: float = 0.0, reach: float = 0.0, hold: float = 0.0) -> None:
        """The head: pitch (+ down), yaw (+ toward its left), tilt, shared along the neck; `reach` (degrees) leans the
        neck forward (+) or draws it back into an S (−); `hold` levels the head against the neck's lean (0..1)."""
        n = max(1, len(NECK))
        for j, nm in enumerate(NECK):
            u = j / max(1, n - 1)
            # an S: the base leans one way, the top the other
            fr.r(nm, 0.5 * pitch / n + reach * (1.0 - 1.6 * u) / n * 1.5, 0.5 * tilt / n, 0.6 * yaw / n)
        fr.r('head', 0.5 * pitch - hold * 0.6 * reach, 0.5 * tilt, 0.4 * yaw)

    def plant(fr: Frame, lg: dict, d: Vector | None = None, pitch: float = 0.0, toe_curl: float = 0.0) -> None:
        """A foot planted at `d` off its rest spot (root space); the tarsus tipped `pitch` degrees about the toes' base
        (+ the heel comes forward and up, − it folds back toward the ground, as in sitting); the toes stay flat
        (`toe_curl` bends them)."""
        toe = lg['rest_toe'] + (d if d is not None else Vector())
        tv = K.axis_m((1, 0, 0), pitch) @ (lg['rest_ankle'] - lg['rest_toe'])
        fr.ik[(lg['thigh'], lg['shin'], lg['tarsus'])] = {'root_target': toe + tv, 'rest_hint': lg['hint'], 'hint_bone': lg['parent'],
                                                       'pitch': pitch}
        if lg['toe']:
            fr.r(lg['toe'], -pitch + toe_curl, 0, 0)

    def feet(fr: Frame, out: float = 0.0, lift: float = 0.0, shift: Vector | None = None, pitch: float = 0.0,
             stagger: float = 0.0) -> None:
        for lg in LEGS:
            d = Vector((lg['s'] * out, -stagger if lg['tag'] == 'L' else stagger, lift)) + (shift if shift is not None else Vector())
            plant(fr, lg, d, pitch)

    def leg_fk(fr: Frame, k: float, thigh: float, shin: float, tarsus: float, toe: float = 0.0, splay: float = 0.0,
               kick: float = 0.0, t: float = 0.0) -> None:
        """The legs by angle, off the ground (flight, ko, a big knock): +x swings a hanging part back."""
        for lg in LEGS:
            w = kick * A.wave(t, 3.0, 0.0 if lg['tag'] == 'L' else 0.5)
            fr.r(lg['thigh'], (thigh + w) * k, -lg['s'] * splay * k, 0)
            fr.r(lg['shin'], shin * k, 0, 0)
            fr.r(lg['tarsus'], (tarsus - w) * k, 0, 0)
            if lg['toe']:
                fr.r(lg['toe'], toe * k, 0, 0)

    def wings(fr: Frame, k: float, flap: float = 0.0, sweep: float = 0.0, droop: float = 0.0, which=None) -> None:
        """Open the wings by k (0 folded, the rest pose; 1 the recipe's spread pose), beat them by `flap` degrees (+ =
        down), sweep them forward by `sweep` about the vertical, and droop the folded wing (+ its tip down). A lower
        pair follows at its `follow` share. Keyed on every frame of every clip (an untouched wing stays at rest)."""
        for key, quats in WQ.items():
            nm, tag = key.rsplit('.', 1)
            if which and nm not in which:
                continue
            s = 1 if tag == 'L' else -1
            f = WLOW.get(nm, 1.0)
            kk = max(0.0, min(1.0, k * f))
            for j, (bone, q) in enumerate(quats):
                qk = Quaternion().slerp(q, kk)
                if j == 0:
                    qk = Quaternion((0.0, 1.0, 0.0), math.radians(s * flap * f)) @ qk
                    if sweep:
                        qk = Quaternion((0.0, 0.0, 1.0), math.radians(-s * sweep * f)) @ qk
                    if droop:      # a folded wing lies back along the body: −x lowers its tip
                        qk = Quaternion((1.0, 0.0, 0.0), math.radians(-droop)) @ qk
                fr.mat[bone] = qk.to_matrix()
                fr.rot.setdefault(bone, [0.0, 0.0, 0.0])

    def chain_pose(fr: Frame, t: float, sway: float = 0.0, rate: float = 1.0, trail: float = 0.0, flare: float = 0.0,
                   lift: float = 0.0) -> None:
        """Plumes and crests: they sway with a lag down the chain, trail back as it moves (+x lifts a backward-pointing
        plume, so `trail` streams it), fan out by `flare` (a pair spreads apart and lifts) and droop by −lift."""
        for m in CH:
            n = len(m['bones'])
            k = 1.0 - m['stiff']
            for i, b in enumerate(m['bones']):
                lag = 0.08 * i
                share = (0.6 + 0.8 * i / max(1, n - 1)) / n
                fr.r(b, (trail + lift + 0.5 * flare) * share * k, m['side'] * 0.6 * flare * share * k * (1 if i == 0 else 0.3),
                     sway * share * k * A.wave(t - lag, rate))

    def jaw(fr: Frame, deg_: float) -> None:
        if JAW:
            fr.r('jaw', deg_, 0, 0)

    def ko_lift(t: float) -> float:
        return K.table_at(lift_tab, t)

    def saw(t: float, n: float = 2.0, hold: float = 0.7) -> float:
        """A bird's head-bob: 0 → 1 slowly (the head held still in the world as the body walks under it) over `hold`
        of each step, then a quick thrust back to 0. n steps a clip."""
        p = (t * n) % 1.0
        return p / hold if p < hold else 1.0 - C.ease_in_out((p - hold) / (1 - hold))

    # ================================================================= ranch life
    def stand(t: float, dz: float = 0.0, pitch: float = 0.0, roll: float = 0.0, yaw: float = 0.0, out: float = 0.0) -> Frame:
        fr = Frame()
        body(fr, dz=dz, pitch=pitch, roll=roll, yaw=yaw)
        feet(fr, out=out)
        return fr

    def p_idle(t: float) -> Frame:
        glance = A.pulse(t, 0.55, 0.85)
        ruffle = A.pulse(t, 0.12, 0.3)
        fr = stand(t, dz=-mm(0.004) * (0.5 + 0.5 * A.wave(t, 2.0)), pitch=1.5 * A.wave(t, 1.0), yaw=3 * glance)
        breathe(fr, t, 2.0)
        look(fr, pitch=2 * A.wave(t, 2.0), yaw=26 * glance, tilt=6 * glance, hold=0.5)
        wings(fr, 0.12 * ruffle, flap=-4 * ruffle)            # a little ruffle of the folded wings
        chain_pose(fr, t, sway=8, trail=2, flare=6 * ruffle)
        jaw(fr, 0)
        return fr

    def p_idle_happy(t: float) -> Frame:
        b = A.bounce(t, 3)
        fr = stand(t, dz=-mm(0.02) * b, roll=4 * A.wave(t, 2.0))
        breathe(fr, t, 3.0)
        look(fr, pitch=-10 + 4 * A.wave(t, 3.0), tilt=10 * A.wave(t, 2.0), reach=-6)
        wings(fr, 0.35 + 0.15 * A.wave(t, 3.0), flap=-14 * b)  # little happy flaps
        chain_pose(fr, t, sway=14, rate=3.0, flare=18)
        jaw(fr, 12)
        return fr

    def p_idle_tired(t: float) -> Frame:
        yawn = A.pulse(t, 0.45, 0.72)
        fr = stand(t, dz=-0.12 * LEG, pitch=6 - 8 * yawn)
        breathe(fr, t, 1.0, 0.6)
        look(fr, pitch=22 - 30 * yawn, reach=-4 * yawn)
        wings(fr, 0.1 * yawn, droop=12 - 8 * yawn)
        chain_pose(fr, t, sway=3, lift=-12)
        jaw(fr, 34 * yawn)
        return fr

    def p_idle_sad(t: float) -> Frame:
        fr = stand(t, dz=-0.1 * LEG - mm(0.006) * (0.5 + 0.5 * A.wave(t, 1.0)), pitch=8 + 1.5 * A.wave(t, 1.0, 0.2), yaw=-5)
        breathe(fr, t, 1.0, 0.8)
        look(fr, pitch=30, yaw=-10 + 4 * A.pulse(t, 0.5, 0.7), reach=8)
        wings(fr, 0.0, droop=16)
        chain_pose(fr, t, sway=2, lift=-18)
        jaw(fr, 0)
        return fr

    def p_idle_sick(t: float) -> Frame:
        w = A.wave(t, 1.0)
        shiver = A.wave(t, 9.0) * A.pulse(t, 0.25, 0.5)
        fr = stand(t, dz=-0.08 * LEG, roll=4 * w + 1.5 * shiver, pitch=4, out=mm(0.01))
        breathe(fr, t, 1.0, 0.6)
        look(fr, pitch=18, yaw=10 * w, tilt=8 * w)
        wings(fr, 0.05 + 0.1 * abs(shiver), droop=10, flap=-6 * shiver)
        chain_pose(fr, t, sway=5, lift=-10)
        jaw(fr, 4)
        return fr

    def leg_radius(bone: str) -> float:
        """A leg part's thickness: lo_body's vertices owned by it, from its bone line (90th percentile)."""
        ob = bpy.data.objects.get('lo_body')
        g = ob.vertex_groups.get(bone) if ob is not None and ob.type == 'MESH' else None
        if g is None:
            return mm(0.03)
        a, b = np.array(rig.head[bone][:]), np.array(rig.tail[bone][:])
        co = np.array([v.co[:] for v in ob.data.vertices if any(x.group == g.index and x.weight > 0.5 for x in v.groups)])
        if len(co) < 5:
            return mm(0.03)
        ab = b - a
        u = np.clip(((co - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
        return float(np.percentile(np.linalg.norm(co - (a + u[:, None] * ab), axis=1), 90))

    def roost_plan() -> tuple[float, float]:
        """How far the tarsi fold back (degrees) and the body comes down when it sits: the heel and the folded knee
        kept a shin's thickness off the ground (measured on lo_body), the belly at most onto the ground."""
        if not LEGS:
            return 0.0, 0.0
        lg = LEGS[0]
        r = max(leg_radius(lg['shin']), leg_radius(lg['tarsus'])) + mm(0.005)
        fold = float(P.get('sit_fold', 75.0))
        while fold > 0:
            heel = lg['rest_toe'] + K.axis_m((1, 0, 0), -fold) @ (lg['rest_ankle'] - lg['rest_toe'])
            if heel.z >= r:
                break
            fold -= 5.0
        heel = lg['rest_toe'] + K.axis_m((1, 0, 0), -fold) @ (lg['rest_ankle'] - lg['rest_toe'])
        l1, l2 = lg['l1'], lg['l2']
        drop = min(ROOM * 0.95, HZ)
        while drop > 0:
            h = lg['rest_hip'] - Vector((0, 0, drop))
            d = heel - h
            L = max(abs(l1 - l2) + 1e-4, min(d.length, l1 + l2 - 1e-4))
            dn = d.normalized()
            hp = lg['hint'] - dn * lg['hint'].dot(dn)
            hn = hp.normalized() if hp.length > 1e-6 else dn.orthogonal().normalized()
            ca = max(-1.0, min(1.0, (l1 * l1 + L * L - l2 * l2) / (2 * l1 * L)))
            knee = h + dn * (l1 * ca) + hn * (l1 * math.sqrt(max(0.0, 1.0 - ca * ca)))
            if knee.z >= r and d.length <= l1 + l2:
                break
            drop -= mm(0.01)
        return fold, max(0.0, drop)

    SIT_FOLD, SIT_DROP = roost_plan()
    C.log(f'avian: sits with the tarsi folded {SIT_FOLD:.0f} deg, the body {SIT_DROP:.3f} m down')

    def roost(fr: Frame, k: float, t: float = 0.0) -> None:
        """Sitting down on its legs: the tarsi fold back toward the ground, the body lowers onto them (roost_plan)."""
        body(fr, dz=-SIT_DROP * k, pitch=4 * k)
        feet(fr, pitch=-SIT_FOLD * k)

    def p_sleep(t: float) -> Frame:
        fr = Frame()
        roost(fr, 1.0, t)
        fr.o('hips', 0, 0, mm(0.008) * (0.5 + 0.5 * A.wave(t, 1.0)))       # slow, deep breaths
        breathe(fr, t, 1.0, 1.4)
        # the head turned back and tucked into the shoulder
        look(fr, pitch=40, yaw=float(P.get('sleep_turn', 110.0)), tilt=-20, reach=-10)
        wings(fr, 0.0, droop=4)
        chain_pose(fr, t, sway=1, lift=-10)
        jaw(fr, 0)
        return fr

    def p_eat(t: float) -> Frame:
        peck = A.pulse(t, 0.15, 0.4) + A.pulse(t, 0.5, 0.75)        # two pecks at the ground
        chew = abs(math.sin(t * 2 * math.pi * 4)) * A.step_ease(t, 0.75, 0.85) * (1 - A.step_ease(t, 0.95, 1.0))
        fr = stand(t, pitch=10 * peck + 4 * A.pulse(t, 0.0, 1.0))
        breathe(fr, t, 2.0)
        look(fr, pitch=60 * peck, reach=30 * peck)
        wings(fr, 0.1 * peck, flap=-6 * peck)
        chain_pose(fr, t, sway=4, trail=-6 * peck)
        jaw(fr, 16 * A.pulse(t, 0.25, 0.4) + 16 * A.pulse(t, 0.6, 0.75) + 8 * chew)
        return fr

    def p_pet(t: float) -> Frame:
        b = A.bounce(t, 2)
        fr = stand(t, dz=-mm(0.015) * b, roll=5, pitch=-2)
        breathe(fr, t, 2.0)
        look(fr, pitch=-8, tilt=18 + 3 * A.wave(t, 2.0), yaw=6, reach=-6)
        wings(fr, 0.2, flap=-6 * b)
        chain_pose(fr, t, sway=10, rate=2.0, flare=14)
        jaw(fr, 6)
        return fr

    def p_look(t: float) -> Frame:
        a = A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56))
        b = A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        yaw = 50 * a - 50 * b
        fr = stand(t, yaw=0.15 * yaw)
        breathe(fr, t, 2.0)
        look(fr, yaw=0.85 * yaw, tilt=0.15 * yaw, reach=-6 * (a + b), hold=1.0)
        wings(fr, 0.0)
        chain_pose(fr, t, sway=6 - 0.15 * yaw)
        jaw(fr, 0)
        return fr

    def hop_pose(fr: Frame, t: float, air: float, crouch: float, up: float, roll: float = 0.0, yaw: float = 0.0,
                 flap: float = 1.0) -> None:
        body(fr, dz=up - 0.18 * LEG * crouch, pitch=-6 * air + 6 * crouch, roll=roll, yaw=yaw)
        feet(fr, lift=0.85 * up, pitch=18 * air)
        look(fr, pitch=-8 * air + 6 * crouch, hold=0.6)
        wings(fr, (0.55 * air + 0.1 * crouch) * flap, flap=(-30 * A.pulse(t, 0.2, 0.5) + 30 * A.pulse(t, 0.5, 0.8)) * flap)
        chain_pose(fr, t, sway=6, trail=-10 * air, flare=10 * air)

    def p_hop(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.28, 0.82)
        crouch = A.pulse(t, 0.0, 0.28) + 0.8 * A.pulse(t, 0.8, 1.0)
        hop_pose(fr, t, air, crouch, mm(0.14) * hop_k * air)
        jaw(fr, 8 * air)
        return fr

    def p_celebrate(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        land = A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)
        hop_pose(fr, t, air, land, mm(0.12) * hop_k * air, yaw=14 * A.wave(t, 1.0))
        wings(fr, 0.85, flap=-30 * A.wave(t, 4.0))              # flapping with joy, over the hop's wings
        jaw(fr, 18)
        return fr

    # ================================================================= moving: a bird's walk, planted by IK
    def gait(t: float, kind: str, dirv: Vector, lean: float = 0.0, guard_w: float = 0.0, wing_k: float = 0.0,
             roll: float = 0.0) -> Frame:
        """Two legs, the left planting at t = 0, the right at 0.5: a planted foot slides back under the body (root
        motion carries it), the heel lifts at toe-off and the swinging foot folds its toes; the body bobs and rocks
        over the planted foot; the head holds still and thrusts forward each step (a bird's head-bob)."""
        n, _s, duty, lift_k = GAITS[kind]
        stride = stride_of(kind)
        fr = Frame()
        bob = mm(0.01) * (0.5 - 0.5 * math.cos(4 * math.pi * t))
        body(fr, dz=-DROP[kind] - bob, pitch=lean, roll=roll + 3.0 * math.cos(2 * math.pi * t), yaw=2.0 * math.sin(2 * math.pi * t))
        for lg in LEGS:
            p = (t + (0.0 if lg['tag'] == 'L' else 0.5)) % 1.0
            if p < duty:
                u = p / duty
                heel = 25 * A.step_ease(u, 0.7, 1.0)                    # the heel lifts at toe-off
                plant(fr, lg, dirv * (stride * (0.5 - u)), pitch=heel)
            else:
                u = (p - duty) / (1 - duty)
                d = dirv * (stride * (-0.5 + C.ease_in_out(u))) + Vector((0, 0, lift_k * LEG * math.sin(math.pi * u)))
                # the toes close only once the foot is well off the ground (a curl near it would dip them under)
                plant(fr, lg, d, pitch=25 * (1 - u) * math.sin(math.pi * u) + 10 * math.sin(math.pi * u), toe_curl=35 * A.pulse(u, 0.25, 0.8))
        head_bob = saw(t, 2.0) if dirv.y < 0 else 0.0
        look(fr, pitch=-0.5 * lean, reach=-8 * head_bob + 6 * (1 - head_bob) * (1 if dirv.y < 0 else 0), hold=0.8)
        wings(fr, wing_k + 0.25 * guard_w, flap=-8 * wing_k * math.sin(4 * math.pi * t))
        chain_pose(fr, t, sway=6, rate=2.0, trail=(8 + 20 * stride / max(LEG, 1e-4)) * (1 if dirv.y < 0 else -0.5))
        jaw(fr, 0)
        return fr

    def gait_marks(kind: str) -> list:
        n = GAITS[kind][0]
        return [('step', 1), ('step', 1 + n // 2)]

    def p_strafe(t: float, side: int) -> Frame:
        return gait(t, 'strafe', Vector((side, 0, 0)), guard_w=1.0, roll=side * 3)

    def p_sidestep(t: float, side: int) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.15, 0.92)
        crouch = A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        hop_pose(fr, t, air, crouch, mm(0.07) * air, roll=side * 12 * air)
        jaw(fr, 0)
        return fr

    # ================================================================= scenes
    def p_sit_down(t: float) -> Frame:
        fr = Frame()
        k = C.ease_in_out(t)
        roost(fr, k, t)
        look(fr, pitch=-4 * k, reach=-8 * k, hold=0.8)
        wings(fr, 0.0, droop=2 * k)
        chain_pose(fr, t, sway=3, lift=-6 * k)
        jaw(fr, 0)
        return fr

    def p_sit(t: float) -> Frame:
        fr = Frame()
        roost(fr, 1.0, t)
        g = A.pulse(t, 0.5, 0.75)
        fr.o('hips', 0, 0, mm(0.003) * (0.5 + 0.5 * A.wave(t, 2.0)))
        breathe(fr, t, 2.0)
        look(fr, pitch=-4 + 3 * A.wave(t, 1.0), yaw=22 * g, reach=-8, hold=0.8)
        wings(fr, 0.0, droop=2)
        chain_pose(fr, t, sway=4, lift=-6)
        jaw(fr, 0)
        return fr

    def p_dizzy(t: float) -> Frame:
        c, s_ = math.cos(t * 4 * math.pi), math.sin(t * 4 * math.pi)
        fr = stand(t, dz=-0.06 * LEG, roll=6 * s_, pitch=4 * c, yaw=5 * s_, out=mm(0.015))
        look(fr, pitch=12 * c, yaw=24 * s_, tilt=18 * s_)
        wings(fr, 0.3 + 0.15 * s_, flap=-10 * c, droop=6)
        chain_pose(fr, t, sway=16, rate=2.0)
        jaw(fr, 12)
        return fr

    # ================================================================= battle
    def p_battle_idle(t: float) -> Frame:
        b = A.bounce(t, 2)
        fr = stand(t, dz=-0.05 * LEG - mm(0.008) * b, pitch=5, yaw=-4, out=mm(0.015))
        breathe(fr, t, 2.0)
        look(fr, pitch=-2, reach=-10, hold=0.8)
        # the wings held a little open and away from the body, so the silhouette reads from the 35-degree camera
        wings(fr, float(P.get('guard_wings', 0.3)) + 0.06 * b, flap=-8 + 6 * A.wave(t, 2.0))
        chain_pose(fr, t, sway=8, rate=2.0, flare=10)
        jaw(fr, 0)
        return fr

    def p_hit(t: float) -> Frame:
        k = A.pulse(t, 0.0, 0.8)
        dy = mm(0.05) * k
        fr = Frame()
        body(fr, dy=dy, pitch=-14 * k, roll=-4 * k, yaw=-8 * k)
        feet(fr, shift=Vector((0, 0.4 * dy, 0)), pitch=10 * k)
        look(fr, pitch=-22 * k, yaw=-14 * k, reach=-12 * k)
        wings(fr, 0.55 * k, flap=-25 * k)                    # the wings fly open
        chain_pose(fr, t, sway=10, trail=-20 * k, flare=20 * k)
        jaw(fr, 18 * k)
        K.add_bones(P, 'hit_bones', fr, k)
        return fr

    def p_hit_heavy(t: float) -> Frame:
        k = A.pulse(t, 0.0, 0.62)
        dy, up = mm(0.16) * k, mm(0.1) * k
        fr = Frame()
        body(fr, dy=dy, dz=up, pitch=-32 * k, roll=-12 * k, yaw=-10 * k)
        leg_fk(fr, k, thigh=-30, shin=-30, tarsus=40, toe=30, splay=18)   # knocked off its feet, the legs flung up
        look(fr, pitch=-28 * k, yaw=-18 * k, reach=-14 * k)
        wings(fr, 0.8 * k, flap=-35 * k)
        hang = float(P.get('hit_heavy_chain_hang', 0.0))
        chain_pose(fr, t, sway=16, trail=-30 * k * (1.0 - 0.5 * hang), flare=25 * k)
        jaw(fr, 22 * k)
        K.add_bones(P, 'hit_heavy_bones', fr, k)
        return fr

    def droop_neck(fr: Frame, root_deg, amount: float) -> None:
        """The neck and head sag `amount` degrees toward the ground of a turned body."""
        down = K.m3(root_deg).transposed() @ Vector((0, 0, -1))
        names = NECK + ['head']
        base = neck_points(P)[0] if neck_points(P) else _v(P['chest'])
        ax = (head_tip(P) - base).normalized().cross(down)
        if ax.length > 1e-4:
            for nm in names:
                fr.turn(nm, ax, amount / len(names))

    def p_ko(t: float) -> Frame:
        """It wobbles, then falls onto its side ('roll') or its back ('back'), lying `body_width` up (the build settles
        it): the wings splayed limp, the legs folded, the neck down on the ground, eyes shut."""
        fr = Frame()
        wob = (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = A.step_ease(t, 0.35, 0.85)
        w_ = 8 * math.sin(t * 2 * math.pi * 2.5) * wob
        rd = (-ko_pitch * fall + w_, 0.0, 0.0) if kstyle == 'back' else (0.0, -ko_roll * fall + w_, 0.0)
        bw = float(P.get('body_width', 0.5 * HZ))
        h = HZ * (1 - fall) + bw * fall + ko_lift(t)
        fr.r('root', *rd)
        fr.o('hips', *K.lay_offset(rd, hip, Vector((0, hip.y, h))))
        fr.r('hips', 0, 0, 0)
        fr.r('chest', 0, 0, 0)
        kick = 12 * A.pulse(t, 0.72, 1.0) if kstyle == 'back' else 0.0
        leg_fk(fr, fall, thigh=-20, shin=50, tarsus=-60, toe=40, splay=12, kick=kick, t=t)
        look(fr)
        droop_neck(fr, rd, 50 * fall)
        wings(fr, 0.45 * fall, flap=20 * fall, droop=10 * fall)
        hang = float(P.get('ko_chain_hang', 0.0))
        chain_pose(fr, t, sway=2 * (1 - fall), lift=-12 * fall)
        if hang and kstyle == 'roll':
            for m in CH:
                fr.r(m['bones'][0], 0, ko_roll * fall * hang, 0)
        jaw(fr, 16 * fall)
        K.add_bones(P, 'ko_bones', fr, fall)
        K.scale_bones(P, 'ko_scale', fr, A.step_ease(t, 0.3, 0.75))
        return fr

    def p_win(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.04, 0.34)
        land = A.pulse(t, 0.32, 0.42)
        proud = A.step_ease(t, 0.3, 0.45) * (1 - A.step_ease(t, 0.86, 1.0))       # back to the start: win loops
        hop_pose(fr, t, air, land, mm(0.12) * hop_k * air)
        look(fr, pitch=-16 * proud, reach=-6 * proud)
        # the wings spread high in a victory beat (they read from every camera)
        wings(fr, 0.6 * air + proud, flap=-30 * proud - 12 * proud * A.wave(t, 4.0))
        chain_pose(fr, t, sway=12, rate=2.0, flare=30 * max(air, proud))
        jaw(fr, 18 * proud + 8 * air)
        K.add_bones(P, 'win_bones', fr, max(air, A.pulse(t, 0.42, 0.86)))
        K.scale_bones(P, 'win_scale', fr, air)
        return fr

    # ---- strike: 24 frames, impact at 13 (t = 0.5) in every style
    def p_strike(t: float) -> Frame:
        ant = A.pulse(t, 0.0, 0.42)
        go = A.pulse(t, 0.28, 0.72)
        fr = Frame()
        if style == 'peck':
            # the neck draws back into an S, then the beak darts forward and down at the target (Beak Jab)
            body(fr, dy=mm(0.03) * ant - mm(0.06) * go, pitch=-4 * ant + 12 * go, yaw=strike_yaw * go)
            feet(fr, stagger=mm(0.04))
            look(fr, pitch=-10 * ant + 20 * go, reach=-28 * ant + 30 * go, yaw=0.5 * strike_yaw * go)
            wings(fr, 0.25 + 0.2 * go, flap=-10 * go)
            jaw(fr, 20 * A.pulse(t, 0.2, 0.48))
        elif style == 'buffet':
            # the wings rear up and back, then sweep forward and strike together (Wing Buffet)
            body(fr, dy=-mm(0.04) * go, pitch=-6 * ant + 8 * go, yaw=strike_yaw * go)
            feet(fr, out=mm(0.02), stagger=mm(0.03))
            look(fr, pitch=-8 * ant + 6 * go, reach=-8, hold=0.8)
            # Nov 18 (Paladove; opt-in, absent = as before): `buffet` {'open', 'flap', 'sweep'} sets the strike's wings
            # at the impact (open share, downbeat and forward sweep in degrees), so they stay in view of the battle camera
            bf = P.get('buffet') or {}
            wings(fr, float(bf.get('open', 0.6)) + 0.4 * ant, flap=-45 * ant + float(bf.get('flap', 35.0)) * go,
                  sweep=-25 * ant + float(bf.get('sweep', 55.0)) * go)
            jaw(fr, 10 * go)
        elif style == 'gust':
            # wings spread wide, then a great downbeat sweeping forward with the beak open: the gust leaves on the
            # impact (Gust Feather; Galeheron's attack picture)
            body(fr, dy=mm(0.03) * ant - mm(0.03) * go, pitch=-8 * ant + 6 * go, yaw=strike_yaw * go)
            feet(fr, out=mm(0.04), stagger=mm(0.05))
            look(fr, pitch=-12 * ant + 4 * go, reach=-10 * ant + 6 * go)
            wings(fr, 0.75 + 0.25 * ant, flap=-40 * ant + 30 * go, sweep=30 * go)
            jaw(fr, 10 * ant + 32 * go)
        elif style == 'kick':
            # a hop with the wings flaring, the left foot kicking out at the target (Lightning Stride)
            air = A.pulse(t, 0.25, 0.68)
            body(fr, dz=mm(0.08) * air, dy=-mm(0.05) * go, pitch=-14 * go, yaw=strike_yaw * go)
            for lg in LEGS:
                if lg['tag'] == 'L':
                    plant(fr, lg, Vector((0, -0.55 * LEG * go, 0.35 * LEG * go + 0.8 * mm(0.08) * air)), pitch=-30 * go, toe_curl=-30 * go)
                else:
                    plant(fr, lg, Vector((0, 0, 0.8 * mm(0.08) * air)), pitch=20 * air)
            look(fr, pitch=-6 * go, reach=-10, hold=0.8)
            wings(fr, 0.4 + 0.5 * air, flap=-30 * air)
            jaw(fr, 12 * go)
        else:      # 'beam'
            # wings flung wide, the breast thrust at the target: the beam leaves socket_core on the impact (Dawnbreak
            # Beam; grown Paladove's attack picture)
            body(fr, dy=mm(0.02) * ant - mm(0.03) * go, pitch=-10 * ant - 4 * go, yaw=strike_yaw * go)
            feet(fr, out=mm(0.03), pitch=12 * go)
            look(fr, pitch=-14 * (ant + go), reach=-8)
            # Nov 18 (grown Paladove; opt-in, absent = as before): `beam` {'open', 'flap'} sets the wings at the impact
            # (open share, downbeat in degrees: - raises), e.g. spread wide and level rather than raised
            bm_ = P.get('beam') or {}
            wings(fr, 0.6 * ant + float(bm_.get('open', 1.0)) * go, flap=float(bm_.get('flap', -30.0)) * go)
            jaw(fr, 14 * go)
        chain_pose(fr, t, sway=6, trail=14 * go - 6 * ant, flare=16 * go)
        K.add_bones(P, 'strike_bones', fr, go)
        K.add_bones(P, 'strike_windup_bones', fr, ant)
        return fr

    def p_cast(t: float) -> Frame:
        up = A.step_ease(t, 0.0, 0.32) * (1 - A.step_ease(t, 0.72, 1.0))
        rel = A.pulse(t, 0.48, 0.72)
        fr = Frame()
        if cstyle == 'gust':
            # wings raised high, then a great beat at `release` (20) that sends the wind
            body(fr, pitch=-8 * up + 10 * rel)
            feet(fr, out=mm(0.03) * up, pitch=10 * up)
            look(fr, pitch=-12 * up + 10 * rel, reach=-8 * up)
            wings(fr, up, flap=-45 * up + 70 * rel, sweep=20 * rel)
            jaw(fr, 26 * rel)
        elif cstyle == 'beam':
            # rises on its toes with the wings wide, then the breast thrusts at `release` (a beam from socket_core)
            body(fr, dz=mm(0.02) * up, pitch=-8 * up + 6 * rel)
            feet(fr, pitch=22 * up)
            look(fr, pitch=-16 * up + 6 * rel, reach=-6 * up)
            wings(fr, up, flap=-25 * up + 10 * rel)
            jaw(fr, 12 * rel)
        else:      # 'call'
            body(fr, pitch=-6 * up + 4 * rel)
            feet(fr, pitch=8 * up)
            look(fr, pitch=-32 * up + 14 * rel, reach=-10 * up + 6 * rel)
            wings(fr, 0.5 * up, flap=-14 * up)
            jaw(fr, 10 * up + 30 * rel)
        chain_pose(fr, t, sway=8, rate=2.0, trail=20 * rel, flare=24 * up)
        return fr

    def p_shove(t: float) -> Frame:
        ant = A.pulse(t, 0.0, 0.32)
        go = A.pulse(t, 0.2, 0.55)
        dy = mm(0.04) * ant - 0.25 * LEG * go
        fr = Frame()
        body(fr, dy=dy, pitch=-6 * ant + 10 * go, yaw=strike_yaw * go)
        feet(fr, shift=Vector((0, 0.5 * dy, 0)), stagger=mm(0.04))
        look(fr, pitch=-4 * ant + 6 * go, reach=-12 * ant, hold=0.8)
        wings(fr, 0.35 * go, flap=-15 * go, sweep=20 * go)
        chain_pose(fr, t, sway=4, trail=14 * go)
        jaw(fr, 0)
        return fr

    # ================================================================= flight (a rig with wings: FLY_CLIPS)
    # Hearthwing's beat (plans/quadruped.py): 24 ticks, a downstroke (45%, the wing fully open, from high over the back
    # to below the body) and a recovery (55%, half folding on the way up). Every flying clip is in place: the root keeps
    # to the origin with a small bob, and the game raises and lowers the monster. Phase 0 = the top of the upstroke.
    FLY_UP, FLY_DOWN, FLY_FOLD = 35.0, 55.0, 0.35
    fly_pitch = float(P.get('fly_pitch', 22.0))          # the body tips forward into level flight

    def stroke(p: float) -> tuple[float, float]:
        p = p % 1.0
        if p < 0.45:
            return -FLY_UP + (FLY_UP + FLY_DOWN) * C.ease_in_out(p / 0.45), 1.0
        u = (p - 0.45) / 0.55
        return FLY_DOWN - (FLY_UP + FLY_DOWN) * C.ease_in_out(u), 1.0 - FLY_FOLD * math.sin(math.pi * u)

    def lift_of(p: float) -> float:
        return 0.5 - 0.5 * math.cos(2 * math.pi * ((p % 1.0) - 0.12))

    def fly_pose(fr: Frame, t: float, beats: float, ka: float = 1.0, rear: float = 0.0, beat: bool = True) -> None:
        """Airborne: the wings beating `beats` times a clip (unless `beat` is off), the body tipped into level flight
        (less by `rear`), the legs trailing back, the neck drawn into an S with the head level, the plumes streaming."""
        if beat:
            flap, kk = stroke(t * beats)
            wings(fr, kk, flap=flap)
        fr.o('root', 0, 0, mm(0.03) * (lift_of(t * beats) - 0.5) * ka)
        body(fr, pitch=(fly_pitch - rear) * ka - 3 * A.wave(t * beats, 1.0, 0.1) * ka, guard=False)
        leg_fk(fr, ka, thigh=45, shin=35, tarsus=55, toe=35)
        look(fr, pitch=-(fly_pitch - rear) * 0.8 * ka + 2 * A.wave(t * beats, 1.0, 0.3) * ka, reach=-14 * ka, hold=0.5)
        chain_pose(fr, t, sway=6, rate=max(1.0, round(beats)), trail=30 * ka, flare=8 * ka)

    def p_fly_takeoff(t: float) -> Frame:
        """A crouch with the wings swept up, a leap on the first downstroke (`leap`), the feet planted (IK) until they
        leave the ground at 0.4, then trailing back (by angle); it ends airborne at the top of the next upstroke (fly's
        first frame)."""
        fr = Frame()
        crouch = A.step_ease(t, 0.0, 0.25) * (1 - A.step_ease(t, 0.28, 0.4))
        air = A.step_ease(t, 0.4, 0.7)
        if t < 0.32:
            u = A.step_ease(t, 0.0, 0.32)
            flap, kk = -FLY_UP * u, u
        else:
            flap, kk = stroke((t - 0.32) / 0.68)
        wings(fr, kk, flap=flap)
        if t < 0.4:
            body(fr, dz=-0.15 * LEG * crouch, pitch=8 * crouch, guard=False)
            feet(fr, pitch=30 * A.pulse(t, 0.25, 0.4))
            look(fr, pitch=6 * crouch, reach=-8 * crouch, hold=0.6)
            chain_pose(fr, t, sway=4, trail=-6 * crouch)
        else:
            fly_pose(fr, (t - 0.32) / 0.68, 1.0, ka=air, beat=False)
        jaw(fr, 0)
        return fr

    def p_fly(t: float) -> Frame:
        fr = Frame()
        fly_pose(fr, t, 1.0)
        jaw(fr, 0)
        return fr

    def p_fly_cast(t: float) -> Frame:
        """Hovering (two beats, the body reared) while it casts: the beam or the gust leaves at `release`; level again
        at the end."""
        fr = Frame()
        hover = A.step_ease(t, 0.0, 0.22) * (1 - A.step_ease(t, 0.8, 1.0))
        thrust = A.step_ease(t, 0.3, 0.45) * (1 - A.step_ease(t, 0.72, 0.86))
        fly_pose(fr, t, 2.0, ka=1.0, rear=(fly_pitch + 20) * hover)
        look(fr, pitch=14 * thrust, reach=16 * thrust)
        jaw(fr, (32 if cstyle != 'beam' else 12) * thrust)
        return fr

    def p_fly_land(t: float) -> Frame:
        """A flare (the wings swept forward and up, braking; the body reared), legs reaching down (by angle), the feet
        planted (IK) from 0.45, touch down on `land`, then the wings fold into the idle stance."""
        fr = Frame()
        flare = A.step_ease(t, 0.0, 0.3) * (1 - A.step_ease(t, 0.55, 0.75))
        reach_down = A.step_ease(t, 0.05, 0.45)
        fold = A.step_ease(t, 0.6, 1.0)
        touch = A.pulse(t, 0.55, 0.85)
        air = 1 - A.step_ease(t, 0.3, 0.5)
        f0, _k0 = stroke(0.0)
        flap = f0 + (-20 - f0) * A.step_ease(t, 0.0, 0.3) if t < 0.3 else -20 * (1 - fold) + 6 * touch
        wings(fr, 1.0 - fold, flap=flap, sweep=25 * flare)
        fr.o('root', 0, 0, mm(0.03) * (lift_of(0.0) - 0.5) * air)
        if t < 0.45:
            body(fr, pitch=fly_pitch * (1 - reach_down) - 18 * flare, guard=False)
            leg_fk(fr, 1 - reach_down, thigh=45, shin=35, tarsus=55, toe=35)
        else:
            body(fr, dz=-0.12 * LEG * touch, pitch=-18 * flare, guard=False)
            feet(fr, pitch=-10 * touch)
        look(fr, pitch=-fly_pitch * 0.8 * (1 - reach_down) + 6 * touch, reach=-14 * (1 - fold), hold=0.6)
        chain_pose(fr, t, sway=6, trail=30 * air - 10 * touch, flare=20 * flare)
        jaw(fr, 0)
        return fr

    # ---- the list (the same names, lengths, markers and faces as every plan)
    FWD, BACK = Vector((0, -1, 0)), Vector((0, 1, 0))
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
    clip('walk', 30, lambda t: gait(t, 'walk', FWD), root_speed=speed_of('walk'), markers=gait_marks('walk'))
    clip('run', 20, lambda t: gait(t, 'run', FWD, lean=8, wing_k=0.35), root_speed=speed_of('run'), markers=gait_marks('run'))
    clip('sit_down', 24, p_sit_down, loop=False, hold=True)
    clip('sit', 120, p_sit, step=2)
    clip('dizzy', 60, p_dizzy, faces=[(1, 'dizzy')])
    clip('battle_idle', 40, p_battle_idle)
    clip('step_fwd', 24, lambda t: gait(t, 'step_fwd', FWD, guard_w=1.0), root_speed=speed_of('step_fwd'), markers=gait_marks('step_fwd'))
    clip('step_back', 24, lambda t: gait(t, 'step_back', BACK, guard_w=1.0), root_speed=speed_of('step_back'), markers=gait_marks('step_back'))
    clip('dash', 20, lambda t: gait(t, 'dash', FWD, lean=14, wing_k=0.6), root_speed=speed_of('dash'), markers=gait_marks('dash'))
    clip('strike', 24, p_strike, loop=False, markers=[('impact', 13)], faces=[(1, 'angry'), (20, 'neutral')])
    clip('cast', 36, p_cast, loop=False, markers=[('release', 20)], faces=[(1, 'strain'), (28, 'neutral')])
    clip('shove', 24, p_shove, loop=False, markers=[('impact', 10)])
    clip('hit', 15, p_hit, loop=False, faces=[(1, 'surprised'), (12, 'neutral')], shut=lambda t: 0.85 * A.pulse(t, 0.0, 0.7))
    clip('hit_heavy', 24, p_hit_heavy, loop=False, faces=[(1, 'strain'), (18, 'neutral')], shut=lambda t: 0.9 * A.pulse(t, 0.0, 0.75))
    clip('ko', 36, p_ko, loop=False, hold=True, faces=[(1, 'strain'), (20, 'dizzy')],
         shut=lambda t: max(0.8 * A.pulse(t, 0.0, 0.3), A.step_ease(t, 0.35, 0.6)))
    clip('win', 60, p_win, markers=[('land', 22)], faces=[(1, 'happy')])
    clip('strafe_l', 24, lambda t: p_strafe(t, 1), root_speed=speed_of('strafe'), markers=[('step', 1), ('step', 13)])
    clip('strafe_r', 24, lambda t: p_strafe(t, -1), root_speed=speed_of('strafe'), markers=[('step', 1), ('step', 13)])
    clip('sidestep_l', 8, lambda t: p_sidestep(t, 1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    clip('sidestep_r', 8, lambda t: p_sidestep(t, -1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    if FLY:
        clip('fly_takeoff', 24, p_fly_takeoff, loop=False, markers=[('leap', 1 + int(round(0.36 * 24)))], faces=[(1, 'neutral')])
        clip('fly', 24, p_fly, markers=[('beat', 1 + int(round(0.2 * 24)))], faces=[(1, 'neutral')])
        clip('fly_cast', 48, p_fly_cast, loop=False, markers=[('release', 1 + int(round(0.48 * 48)))],
             faces=[(1, 'angry'), (int(0.86 * 48), 'neutral')])
        clip('fly_land', 24, p_fly_land, loop=False, markers=[('land', 1 + int(round(0.7 * 24)))], faces=[(1, 'neutral')])
    return made
