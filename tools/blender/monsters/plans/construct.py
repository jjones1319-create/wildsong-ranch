"""The construct body plan (ART_2_PLAN §4, batch 5): rig template, sockets, springs and the clip generators for
machines and furniture that move as rigid parts: Lootlid (a treasure chest on four stubby legs whose lid is its mouth,
with a long tongue inside) now; Gearhoot (a clockwork owl: a head on a turning neck, gear-feather wings, a wind-up key)
later, through the 'neck' head mode, spinners and wing chains (basic hooks, not tuned yet).

A recipe selects it with `PLAN = 'construct'` (tools/blender/monsters/breeds/RECIPE.md, "Construct plan"). The same
build (build_ultra.py) drives it as every other plan: rig_specs, sockets, springs, chain_groups, heatless, make_clips,
STAR_CLIPS, MOVE_CLIPS, ROOT_DIRS and KO_ROLL (ko falls onto its side or its back at `body_width`, measured and settled
by the build, lifting any sinking frame with `ko_lift`).

Space: metres; the monster faces −Y, Z is up, +X is its left. Model it standing, the lid shut. From rig_p() (`P`):
  hip                  the body's centre: the bone `hips` (parent `root`) carries the body rigidly
  chest                the top of the body (the neck's base in the 'neck' head mode)
  head_c, head_r       the face's centre and size
  hinge, lid_front     (the 'lid' head mode) the lid's hinge at the back and its front edge: the bone `head` (parent
                       `hips`) turns about the hinge to open the mouth, carrying the eyes and everything on the lid
  legs                 the left legs, front to back (as the shelled plan's), planted by IK
Every part is rigid: the plan gives no part heat weights, so the recipe skins each with U.rigid / U.segment_weights and
the lid's seam is a hard split at the hinge (the jaw lesson: a soft blend would leak the lid over the box).
Rotations are world-aligned degrees relative to the parent at rest (lib.anim.ClipBuilder.rot).
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector

from lib import anim as A
from lib import common as C
from lib.rig import BoneSpec
from monsters.plans import kin as K
from monsters.plans.kin import Frame, mirror

PLAN = 'construct'
SIDES = K.SIDES
KO_ROLL = 80.0
STRIKE_STYLES = ('chomp', 'tongue', 'spit', 'slam', 'peck')
CAST_STYLES = ('spit', 'raise')
KO_STYLES = ('roll', 'back')
SPRINGS = []                # Art 2.0 compatibility only; the Ultra build calls springs(P)
KINDS = ('tassel', 'tail', 'antenna', 'tuft', 'wing')

SIDESTEP_DISTANCE = 1.4 * 100 / 150
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}
STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']
# gaits: (frames, stride as a share of the leg's reach, the planted share of the cycle, foot lift as a share of the leg)
GAITS = {'walk': (30, 0.55, 0.62, 0.22), 'run': (20, 0.8, 0.5, 0.3), 'dash': (20, 1.0, 0.42, 0.34),
         'step_fwd': (24, 0.5, 0.6, 0.2), 'step_back': (24, 0.42, 0.6, 0.18), 'strafe': (24, 0.45, 0.6, 0.2)}


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def _v(p) -> Vector:
    return Vector(p)


def head_mode(P: dict) -> str:
    m = P.get('head_mode', 'lid' if P.get('hinge') else 'neck')
    if m not in ('lid', 'neck'):
        raise ValueError(f"head_mode {m!r}: 'lid' or 'neck'")
    return m


def neck_points(P: dict) -> list[Vector]:
    return [_v(p) for p in (P.get('neck') or [])] if head_mode(P) == 'neck' else []


def neck_names(P: dict) -> list[str]:
    n = len(neck_points(P))
    return [f'neck.{i + 1}' for i in range(n - 1)] if n >= 2 else []


def head_points(P: dict) -> tuple[Vector, Vector]:
    """The head bone: the lid's hinge → its front edge ('lid'), else the neck's top (or head_base) → head_tip."""
    if head_mode(P) == 'lid':
        return _v(P['hinge']), _v(P['lid_front'])
    hc, hr = _v(P['head_c']), float(P['head_r'])
    pts = neck_points(P)
    base = pts[-1] if len(pts) >= 2 else (_v(P['head_base']) if P.get('head_base') else hc + Vector((0, 0.5 * hr, -0.5 * hr)))
    tip = _v(P['head_tip']) if P.get('head_tip') else hc + Vector((0, -0.9 * hr, 0.1 * hr))
    return base, tip


def jaw_points(P: dict) -> tuple[Vector, Vector] | None:
    """A jaw (a beak) in the 'neck' mode only; a lid is its own mouth."""
    if head_mode(P) == 'lid':
        return None
    if P.get('jaw'):
        return _v(P['jaw']['head']), _v(P['jaw']['tail'])
    hc, hr = _v(P['head_c']), float(P['head_r'])
    return hc + Vector((0, -0.3 * hr, -0.45 * hr)), hc + Vector((0, -0.9 * hr, -0.55 * hr))


def mouth_point(P: dict) -> Vector:
    """Where things leave the mouth: the box's front lip under the lid, else the jaw's tip."""
    if P.get('mouth'):
        return _v(P['mouth'])
    if head_mode(P) == 'lid':
        h, f = head_points(P)
        return Vector((0.0, f.y + 0.02 * size_of(P), f.z - 0.02 * size_of(P)))
    return jaw_points(P)[1]


def legs(P: dict) -> list[dict]:
    """As the shelled plan's: the left legs front to back {'hip', 'knee', 'ankle', 'toe'?, 'parent': 'hips'}, mirrored."""
    out = []
    for tag, s in SIDES:
        for i, lg in enumerate(P.get('legs') or [], start=1):
            toe = mirror(lg['toe'], s) if lg.get('toe') else None
            out.append({'i': i, 'tag': tag, 's': s, 'upper': f'leg{i}.{tag}', 'lower': f'shin{i}.{tag}',
                        'foot': f'foot{i}.{tag}' if toe is not None else None,
                        'hip': mirror(lg['hip'], s), 'knee': mirror(lg['knee'], s), 'ankle': mirror(lg['ankle'], s),
                        'toe': toe, 'parent': lg.get('parent', 'hips'), 'front': i == 1})
    return out


def tongue_of(P: dict) -> dict | None:
    """The tongue: {'points': [p0 … pN] (inside the box or the mouth), 'parent': 'hips' ('lid') or 'jaw', 'reach'}."""
    t = P.get('tongue')
    if not t:
        return None
    pts = [_v(p) for p in t['points']]
    if len(pts) < 2:
        raise ValueError('tongue: needs at least 2 points')
    return {'points': pts, 'parent': t.get('parent', 'hips' if head_mode(P) == 'lid' else 'jaw'),
            'bones': [f'tongue.{i + 1}' for i in range(len(pts) - 1)],
            'reach': float(t.get('reach', 0.45 * size_of(P))), 'dir': (pts[-1] - pts[0]).normalized()}


def spinners(P: dict) -> list[dict]:
    """Parts that turn about their own axis (a wind-up key, gears): {'name', 'head', 'tail' (the axis), 'parent':
    'hips', 'rate': turns a second} → bone spin.<name>."""
    out = []
    for sp in P.get('spinners') or []:
        out.append({'name': sp['name'], 'bone': f"spin.{sp['name']}", 'head': _v(sp['head']), 'tail': _v(sp['tail']),
                    'parent': sp.get('parent', 'hips'), 'rate': float(sp.get('rate', 0.5))})
    return out


def chains(P: dict) -> list[dict]:
    out = []
    for m in P.get('chains') or []:
        kind = m.get('kind', 'tassel')
        if kind not in KINDS:
            raise ValueError(f"chain {m.get('name')}: kind {kind!r}, one of {', '.join(KINDS)}")
        nm0 = m.get('name', kind)
        twins = [(nm0 + 'L', 1), (nm0 + 'R', -1)] if m.get('mirror') else [(nm0, 1)]
        for nm, s in twins:
            pts = [mirror(p, s) for p in m['points']]
            out.append({'name': nm, 'kind': kind, 'parent': m.get('parent', 'hips'), 'points': pts, 'side': s,
                        'stiff': float(m.get('stiff', 0.0)), 'spring': bool(m.get('spring', kind != 'wing')),
                        'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)]})
    return out


def _style(P: dict, key: str, allowed: tuple, default: str) -> str:
    st = P.get(key, default)
    if st not in allowed:
        raise ValueError(f"{key} {st!r}: one of {', '.join(allowed)}")
    return st


def strike_style(P: dict) -> str:
    return _style(P, 'strike_style', STRIKE_STYLES, 'chomp' if head_mode(P) == 'lid' else 'peck')


def cast_style(P: dict) -> str:
    return _style(P, 'cast_style', CAST_STYLES, 'spit' if head_mode(P) == 'lid' else 'raise')


def ko_style(P: dict) -> str:
    return _style(P, 'ko_style', KO_STYLES, 'roll')


def springs(P: dict) -> list[dict]:
    return [{'kind': m['kind'], 'chain': m['bones']} for m in chains(P) if m['spring']]


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → kind for CLIP_CALM: 'neck', 'tongue', 'spin', each chain by name or kind, 'leg'."""
    out = {'neck': 'neck', 'tongue': 'tongue', 'spin': 'spin'}
    for m in chains(P):
        out[m['name']] = m['kind']
    for i in range(1, len(P.get('legs') or []) + 1):
        for p in ('leg', 'shin', 'foot'):
            out[f'{p}{i}'] = 'leg'
    return out


def heatless(P: dict) -> set[str]:
    """Everything that moves on its own is skinned by the recipe (rigid parts; a lid's seam must be a hard split):
    the head (lid), the jaw, the legs, the tongue, the spinners and every chain (P['heat'] lists any to keep)."""
    keep = set(P.get('heat') or [])
    out = {'head', 'jaw', 'tongue', 'spin'} | {m['name'] for m in chains(P)}
    for i in range(1, len(P.get('legs') or []) + 1):
        out |= {f'leg{i}', f'shin{i}', f'foot{i}'}
    return out - keep


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    hip, top = _v(P['hip']), _v(P['chest'])
    hr = float(P['head_r'])
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk),
        BoneSpec('hips', tuple(hip), tuple(hip + Vector((0, -0.12 * sk, 0))), 'root', radius=0.4 * sk),
    ]
    npts, names = neck_points(P), neck_names(P)
    for i, nm in enumerate(names):
        specs.append(BoneSpec(nm, tuple(npts[i]), tuple(npts[i + 1]), 'hips' if i == 0 else names[i - 1], connect=i > 0,
                              radius=0.1 * sk))
    hb, ht = head_points(P)
    specs.append(BoneSpec('head', tuple(hb), tuple(ht), names[-1] if names else 'hips', connect=bool(names),
                          radius=max(0.15 * sk, 1.2 * hr)))
    jp = jaw_points(P)
    if jp:
        specs.append(BoneSpec('jaw', tuple(jp[0]), tuple(jp[1]), 'head', radius=0.5 * hr))
    tg = tongue_of(P)
    if tg:
        for i, nm in enumerate(tg['bones']):
            # unconnected, so each slides out along the tongue (the skin between stretches)
            specs.append(BoneSpec(nm, tuple(tg['points'][i]), tuple(tg['points'][i + 1]), tg['parent'] if i == 0 else tg['bones'][i - 1],
                                  radius=0.04 * sk))
    for lg in legs(P):
        specs.append(BoneSpec(lg['upper'], tuple(lg['hip']), tuple(lg['knee']), lg['parent'], radius=0.08 * sk))
        specs.append(BoneSpec(lg['lower'], tuple(lg['knee']), tuple(lg['ankle']), lg['upper'], connect=True, radius=0.07 * sk))
        if lg['foot']:
            specs.append(BoneSpec(lg['foot'], tuple(lg['ankle']), tuple(lg['toe']), lg['lower'], connect=True, radius=0.06 * sk))
    for sp in spinners(P):
        specs.append(BoneSpec(sp['bone'], tuple(sp['head']), tuple(sp['tail']), sp['parent'], radius=0.06 * sk))
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'hips'), radius=0.08 * sk))
    for m in chains(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.05 * sk))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """The game's seven, socket_core at the body's centre, socket_tongue at the tongue's tip, socket_<spinner>,
    socket_<chain>, socket_<prop>. socket_mouth sits at the box's front lip (a lid) or the jaw's tip."""
    sk = size_of(P)
    hc, hr = _v(P['head_c']), float(P['head_r'])
    hip, top = _v(P['hip']), _v(P['chest'])
    lid = head_mode(P) == 'lid'
    jp = jaw_points(P)
    head_top = Vector((hc.x, hc.y, max(top.z, hc.z + hr)))
    out = {
        'socket_head': ('head', tuple(head_top)),
        'socket_crown': ('head', tuple(head_top + Vector((0, 0, 0.1 * sk)))),
        'socket_back': ('hips', (hip.x, hip.y + 0.5 * abs(hip.y - hc.y) + 0.05 * sk, top.z)),
        'socket_mouth': ('hips' if lid else 'jaw', tuple(mouth_point(P))),
        'socket_core': ('hips', tuple(hip)),
    }
    tg = tongue_of(P)
    if tg:
        out['socket_tongue'] = (tg['bones'][-1], tuple(tg['points'][-1]))
    front = {lg['tag']: lg for lg in legs(P) if lg['front']}
    for tag, s in SIDES:
        if tag in front:
            lg = front[tag]
            out[f'socket_paw_{tag}'] = (lg['foot'] or lg['lower'], tuple(lg['toe'] if lg['toe'] is not None else lg['ankle']))
        else:
            out[f'socket_paw_{tag}'] = ('hips', (s * 0.8 * hr, hip.y - 0.8 * hr, hip.z))
    tail = next((m for m in chains(P) if m['kind'] == 'tail'), None)
    out['socket_tail'] = (tail['bones'][-1], tuple(tail['points'][-1])) if tail else ('hips', (hip.x, 2 * hip.y - hc.y, hip.z))
    for sp in spinners(P):
        out[f"socket_{sp['name']}"] = (sp['bone'], tuple(sp['tail']))
    for m in chains(P):
        out[f"socket_{m['name']}"] = (m['bones'][-1], tuple(m['points'][-1]))
    for pr in P.get('props', []) or []:
        out[f"socket_{pr['name']}"] = (f"prop.{pr['name']}", tuple(pr['tail']))
    return out


# --------------------------------------------------------------------------- clips
def make_clips(cb: A.ClipBuilder, P: dict, only: list[str] | None = None) -> list[A.ClipMeta]:
    rig = K.Rig(cb.arm)
    has = rig.has
    sk = size_of(P)
    made: list[A.ClipMeta] = []
    style, cstyle, kstyle = strike_style(P), cast_style(P), ko_style(P)
    LID = head_mode(P) == 'lid'
    LEGS = [lg for lg in legs(P) if has(lg['upper']) and has(lg['lower'])]
    NECK = [n for n in neck_names(P) if has(n)]
    TG = tongue_of(P) if has('tongue.1') else None
    if style == 'tongue' and not TG:
        raise ValueError("strike_style 'tongue' needs a tongue")
    SPIN = [sp for sp in spinners(P) if has(sp['bone'])]
    CH = chains(P)
    JAW = has('jaw') and bool(P.get('jaw_open', True))
    CLOSED = P.get('blink_closed')
    hip = _v(P['hip'])
    HZ = hip.z
    lid_max = float(P.get('lid_max', 70.0))
    ko_roll = float(P.get('ko_roll', KO_ROLL))
    ko_pitch = float(P.get('ko_pitch', 90.0))
    lift_tab = P.get('ko_lift') or []
    strike_yaw = float(P.get('strike_yaw', 0.0))
    hop_k = float(P.get('hop', 1.0))

    def mm(v: float) -> float:
        return v * sk

    for lg in LEGS:
        lg['reach'] = rig.length(lg['upper']) + rig.length(lg['lower'])
        lg['rest_ankle'] = rig.tail[lg['lower']].copy()
        lg['rest_hip'] = rig.head[lg['upper']].copy()
        fallback = Vector((lg['s'] * 0.7, -0.3 if lg['front'] else 0.3, 0.6)).normalized()
        lg['hint'] = rig.bend_hint(lg['upper'], lg['lower'], fallback)
        lg['phase'] = 0.5 * ((lg['i'] - 1 + (0 if lg['tag'] == 'L' else 1)) % 2)
    LEG = (sum(lg['reach'] for lg in LEGS) / len(LEGS)) if LEGS else mm(0.15)

    def rigid_points() -> np.ndarray | None:
        """lo_body's vertices that move with the body (hips and the props on it), relative to its centre: body() keeps
        them off the ground."""
        ob = bpy.data.objects.get('lo_body')
        if ob is None or ob.type != 'MESH':
            return None
        keep = {'hips'} | {f"prop.{pr['name']}" for pr in (P.get('props') or []) if pr.get('parent', 'hips') == 'hips'}
        names = {g.index: g.name for g in ob.vertex_groups}
        pts = [v.co[:] for v in ob.data.vertices if v.groups and names.get(max(v.groups, key=lambda g: g.weight).group) in keep]
        if len(pts) < 20:
            return None
        a = np.array(pts) - np.array(hip[:])
        return a[:: max(1, len(a) // 3000)]

    BODY = rigid_points()
    ROOM = float(P['sink']) if P.get('sink') is not None else (max(0.0, HZ + float(BODY[:, 2].min()) - mm(0.004)) if BODY is not None else 0.4 * HZ)
    FLOOR = min(mm(0.003), HZ + float(BODY[:, 2].min())) if BODY is not None else -1.0

    def leg_radius() -> float:
        """The legs' thickness at the top (lo_body's vertices owned by the upper leg bones, from their bone lines)."""
        ob = bpy.data.objects.get('lo_body')
        if ob is None or ob.type != 'MESH' or not LEGS:
            return mm(0.05)
        d = []
        for lg in LEGS:
            g = ob.vertex_groups.get(lg['upper'])
            if g is None:
                continue
            a, b = np.array(lg['rest_hip'][:]), np.array(rig.tail[lg['upper']][:])
            co = np.array([v.co[:] for v in ob.data.vertices if any(x.group == g.index and x.weight > 0.5 for x in v.groups)])
            if len(co) < 5:
                continue
            ab = b - a
            u = np.clip(((co - a) @ ab) / max(float(ab @ ab), 1e-9), 0, 1)
            d.append(float(np.percentile(np.linalg.norm(co - (a + u[:, None] * ab), axis=1), 90)))
        return max(d) if d else mm(0.05)

    LEG_R = leg_radius()
    # how far the body can sit down before the legs (their hips come down with it, the thighs sloping to the splayed
    # knees) reach the ground: a squat for stubby legs; `sit_drop` overrides
    SIT = float(P['sit_drop']) if P.get('sit_drop') is not None else         min(0.92 * ROOM, min((lg['rest_hip'].z for lg in LEGS), default=ROOM) - 2.0 * LEG_R - mm(0.008))
    C.log(f'construct: {"lid" if LID else "neck"} head, room under the body {ROOM:.3f} m (sits {SIT:.3f}), {len(LEGS)} legs, '
          f'tongue {bool(TG)}, {len(SPIN)} spinners')

    def reach_drop(shift: Vector, margin: float = 0.97) -> float:
        need = 0.0
        for lg in LEGS:
            d = lg['rest_hip'] - (lg['rest_ankle'] + shift)
            r2 = (margin * lg['reach']) ** 2 - d.x * d.x - d.y * d.y
            need = max(need, d.z - math.sqrt(max(0.0, r2)))
        return min(max(0.0, need), 0.8 * ROOM)

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
            # the spinners (a wind-up key, gears) turn a whole number of times in a loop, so it closes; still otherwise
            for sp in SPIN:
                turns = max(1, round(sp['rate'] * n / A.FPS)) if loop else 0
                fr.r(sp['bone'], 0, 0, 0)
                fr.turn(sp['bone'], sp['tail'] - sp['head'], 360.0 * turns * t)
            out = getattr(fr, 'tongue_out', 0.0)
            if LID and TG and out > 0 and 'head' in fr.rot:
                # the tongue only comes out under an open lid
                need = -40.0 * min(1.0, 3.0 * out)
                if fr.rot['head'][0] > need:
                    fr.rot['head'][0] = need
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
             yaw: float = 0.0) -> None:
        """The body moved and turned about its centre, never lower than 3 mm off the ground."""
        if BODY is not None:
            low = HZ + dz + float((BODY @ np.array(K.m3((pitch, roll, yaw)))[2]).min())
            if low < FLOOR:
                dz += FLOOR - low
        fr.o('hips', dx, dy, dz)
        fr.r('hips', pitch, roll, yaw)
        fr.drop = max(fr.drop, -dz)

    def mouth(fr: Frame, k: float) -> None:
        """Open the mouth by k (0 shut … 1 wide): the lid swings up `lid_max` degrees about its hinge, or the jaw drops."""
        k = max(0.0, k)                                  # never shut past closed (into the box)
        if LID:
            fr.r('head', -lid_max * k, 0, 0)
        elif JAW:
            fr.r('jaw', 30.0 * k, 0, 0)

    def look(fr: Frame, pitch: float = 0.0, yaw: float = 0.0, tilt: float = 0.0) -> None:
        """The head looks: on a neck it turns (an owl's turn reaches far), a lid can't, so the body turns a little."""
        if LID:
            fr.r('hips', 0.3 * pitch, 0.3 * tilt, 0.3 * yaw)
            return
        n = max(1, len(NECK))
        for nm in NECK:
            fr.r(nm, 0.5 * pitch / n, 0.4 * tilt / n, 0.5 * yaw / n)
        fr.r('head', 0.5 * pitch, 0.6 * tilt, 0.5 * yaw)

    def tongue(fr: Frame, out: float = 0.0, droop: float = 0.0, curl: float = 0.0, wag: float = 0.0) -> None:
        """The tongue slid `out` (0..1) of its reach, its root pitched `droop` down (over the box's lip), the tip curled
        up `curl`, wagged `wag` (as the blob plan's)."""
        if not TG:
            return
        n = len(TG['bones'])
        fr.tongue_out = max(0.0, out)
        step = TG['reach'] * max(0.0, out) / max(1, n - 1)
        # the droop bends the part that is out over the box's lip (a root pitched down would sink into the box)
        hang = droop * min(1.0, 2.0 * out)
        for i, b in enumerate(TG['bones']):
            fr.o(b, *(TG['dir'] * (step if i > 0 else 0.0)))
            if i == 0:
                fr.r(b, 0.1 * droop, 0, wag)
            else:
                fr.r(b, -curl * (1.0 if i == n - 1 else 0.4) + hang * 0.6 * i / max(1, n - 1), 0, 0.5 * wag)

    def plant(fr: Frame, lg: dict, d: Vector | None = None, pitch: float = 0.0) -> None:
        a = lg['rest_ankle'] + (d if d is not None else Vector())
        fr.ik[(lg['upper'], lg['lower'], lg['foot'])] = {'root_target': a, 'rest_hint': lg['hint'], 'hint_bone': lg['parent'],
                                                       'pitch': pitch if lg['foot'] else None}

    def feet(fr: Frame, out: float = 0.0, lift: float = 0.0, shift: Vector | None = None, tuck_: float = 0.0) -> None:
        """Every foot planted (wider by `out`, lifted, moved by `shift`, drawn in under the body by `tuck_`)."""
        for lg in LEGS:
            d = Vector((lg['s'] * out, 0.0, lift)) + (shift if shift is not None else Vector())
            if tuck_:
                h, ra = lg['rest_hip'], lg['rest_ankle']
                d += Vector((0.4 * (h.x - ra.x), 0.3 * (h.y - ra.y), max(0.0, 0.45 * (h.z - ra.z) - fr.drop))) * tuck_
            plant(fr, lg, d)

    def fold_legs(fr: Frame, k: float, splay: float = 35.0, curl: float = 30.0, wave: float = 0.0, t: float = 0.0) -> None:
        for lg in LEGS:
            s = lg['s']
            w = wave * A.wave(t, 3.0, 0.25 * lg['i'] + (0.5 if lg['tag'] == 'R' else 0.0))
            fr.r(lg['upper'], 0, -s * (splay * k + w), 0)
            fr.r(lg['lower'], 0, s * (curl * k + 0.5 * w), 0)

    def chain_pose(fr: Frame, t: float, sway: float = 0.0, rate: float = 1.0, trail: float = 0.0, wag: float = 0.0,
                   lift: float = 0.0, flap: float = 0.0) -> None:
        """Chains by kind: a tassel sways and trails, a tail wags and lifts, antennae and tufts spring, wings flap."""
        for m in CH:
            n = len(m['bones'])
            k = 1.0 - m['stiff']
            for i, b in enumerate(m['bones']):
                lag = 0.08 * i
                share = (0.6 + 0.8 * i / max(1, n - 1)) / n
                if m['kind'] == 'tassel':
                    fr.r(b, trail * share * k, 0, sway * share * k * A.wave(t - lag, rate))
                elif m['kind'] == 'wing':
                    fr.r(b, 0, -m['side'] * flap * (1.0 if i == 0 else 0.5) * k, 0)
                elif m['kind'] in ('antenna', 'tuft'):
                    fr.r(b, 0.5 * sway * share * k * A.wave(t - lag, rate, 0.25), 0, sway * share * k * A.wave(t - lag, rate))
                else:
                    fr.r(b, lift * share * k, 0, 1.6 * wag * share * k * A.wave(t - lag, rate))

    def ko_lift(t: float) -> float:
        return K.table_at(lift_tab, t)

    # ================================================================= ranch life
    def p_idle(t: float) -> Frame:
        fr = Frame()
        glance = A.pulse(t, 0.55, 0.85)
        body(fr, dz=-mm(0.005) * (0.5 + 0.5 * A.wave(t, 2.0)), roll=1.5 * A.wave(t, 1.0), yaw=4 * glance)
        feet(fr)
        look(fr, yaw=24 * glance, tilt=4 * glance)
        mouth(fr, 0.06 + 0.05 * (0.5 + 0.5 * A.wave(t, 2.0, 0.25)))     # the lid breathes a crack open
        tongue(fr)
        chain_pose(fr, t, sway=6, wag=6, flap=4 * A.wave(t, 2.0))
        return fr

    def p_idle_happy(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 3)
        body(fr, dz=-mm(0.02) * b, roll=5 * A.wave(t, 2.0), yaw=4 * A.wave(t, 1.0, 0.25))
        feet(fr)
        look(fr, pitch=-8, tilt=8 * A.wave(t, 2.0))
        mouth(fr, 0.35 + 0.08 * A.wave(t, 3.0))
        tongue(fr, out=0.35, droop=40, wag=18 * A.wave(t, 3.0))
        chain_pose(fr, t, sway=14, rate=3.0, wag=18, flap=16 * A.wave(t, 6.0))
        return fr

    def p_idle_tired(t: float) -> Frame:
        fr = Frame()
        yawn = A.pulse(t, 0.45, 0.72)
        body(fr, dz=-0.35 * ROOM, pitch=4 - 6 * yawn)
        feet(fr, out=mm(0.01))
        look(fr, pitch=10 - 20 * yawn)
        mouth(fr, 0.02 + 0.6 * yawn)
        tongue(fr, out=0.12 * yawn, droop=20 * yawn)
        chain_pose(fr, t, sway=3, wag=3, lift=-8)
        return fr

    def p_idle_sad(t: float) -> Frame:
        fr = Frame()
        body(fr, dz=-0.4 * ROOM, pitch=7, yaw=-5)
        feet(fr, out=mm(0.012))
        look(fr, pitch=16, yaw=-8 + 4 * A.pulse(t, 0.5, 0.7))
        mouth(fr, 0.0)
        tongue(fr)
        chain_pose(fr, t, sway=2, wag=2, lift=-10, flap=-6)
        return fr

    def p_idle_sick(t: float) -> Frame:
        fr = Frame()
        w = A.wave(t, 1.0)
        shiver = A.wave(t, 9.0) * A.pulse(t, 0.25, 0.5)
        body(fr, dz=-0.25 * ROOM, roll=5 * w + 1.5 * shiver, pitch=3)
        feet(fr, out=mm(0.008))
        look(fr, pitch=12, yaw=8 * w, tilt=6 * w)
        mouth(fr, 0.05 + 0.04 * abs(A.wave(t, 9.0)) * A.pulse(t, 0.25, 0.5))      # the lid rattles
        tongue(fr)
        chain_pose(fr, t, sway=5, wag=3, lift=-6)
        return fr

    def p_sleep(t: float) -> Frame:
        fr = Frame()
        b = A.wave(t, 1.0)
        body(fr, dz=-SIT, pitch=2)
        feet(fr, out=0.35 * LEG, lift=mm(0.022))
        look(fr, pitch=6)
        mouth(fr, 0.04 + 0.04 * (0.5 + 0.5 * b))          # a slow snore under the lid
        tongue(fr)
        chain_pose(fr, t, sway=1, wag=0, lift=-10, flap=-8)
        return fr

    def p_eat(t: float) -> Frame:
        fr = Frame()
        dip = A.step_ease(t, 0.0, 0.2) * (1 - A.step_ease(t, 0.85, 1.0))
        chew = dip * abs(math.sin(t * 2 * math.pi * 3))
        grab = A.pulse(t, 0.15, 0.4)
        body(fr, dz=-0.15 * ROOM * dip, pitch=8 * dip)
        feet(fr)
        look(fr, pitch=20 * dip)
        mouth(fr, 0.5 * chew + 0.5 * grab)
        tongue(fr, out=0.45 * grab, droop=50 * grab, curl=30 * A.pulse(t, 0.3, 0.42))
        chain_pose(fr, t, sway=4, wag=8)
        return fr

    def p_pet(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, dz=-mm(0.012) * b, roll=6, pitch=-3)
        feet(fr)
        look(fr, pitch=-10, tilt=12 + 3 * A.wave(t, 2.0), yaw=5)
        mouth(fr, 0.25)
        tongue(fr, out=0.25, droop=35, wag=12 * A.wave(t, 2.0))
        chain_pose(fr, t, sway=10, rate=2.0, wag=20, flap=10 * A.wave(t, 4.0))
        return fr

    def p_look(t: float) -> Frame:
        fr = Frame()
        a = A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56))
        b = A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        yaw = 40 * a - 40 * b
        body(fr, yaw=(0.35 if LID else 0.15) * yaw)
        feet(fr)
        look(fr, yaw=0.85 * yaw, tilt=0.1 * yaw)
        mouth(fr, 0.08)
        tongue(fr)
        chain_pose(fr, t, sway=6, wag=6)
        return fr

    def hop_pose(fr: Frame, t: float, air: float, crouch: float, up: float, roll: float = 0.0, yaw: float = 0.0) -> None:
        body(fr, dz=up - 0.3 * ROOM * crouch, pitch=-5 * air + 4 * crouch, roll=roll, yaw=yaw)
        feet(fr, lift=0.8 * up, tuck_=0.35 * air)
        look(fr, pitch=-8 * air + 5 * crouch)
        chain_pose(fr, t, sway=6, trail=-12 * air, wag=10, lift=10 * air, flap=25 * air)

    def p_hop(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.28, 0.82)
        crouch = A.pulse(t, 0.0, 0.28) + 0.8 * A.pulse(t, 0.8, 1.0)
        hop_pose(fr, t, air, crouch, mm(0.12) * hop_k * air)
        mouth(fr, 0.25 * air - 0.02 * crouch + 0.03)      # the lid flaps open in the air and claps shut on landing
        tongue(fr)
        return fr

    def p_celebrate(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        land = A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)
        hop_pose(fr, t, air, land, mm(0.1) * hop_k * air, yaw=14 * A.wave(t, 1.0))
        mouth(fr, 0.55)
        tongue(fr, out=0.4, droop=40, wag=22 * A.wave(t, 3.0))
        return fr

    # ================================================================= moving: legged gaits, planted by IK
    def gait(t: float, kind: str, dirv: Vector, waddle: float = 1.0, lean: float = 0.0, guard_w: float = 0.0,
             rate: float = 1.0, roll: float = 0.0) -> Frame:
        """Diagonal pairs (two legs a side) or tripods, each foot planted while the root carries the body; the body
        rocks and bobs, and a lid flaps a little at each step."""
        n, _s, duty, lift_k = GAITS[kind]
        stride = stride_of(kind)
        fr = Frame()
        bob = mm(0.008) * (0.5 - 0.5 * math.cos(4 * math.pi * t))
        body(fr, dz=-DROP[kind] - bob, pitch=lean, roll=roll + 3.5 * waddle * math.sin(2 * math.pi * t),
             yaw=2.0 * waddle * math.sin(2 * math.pi * t))
        for lg in LEGS:
            p = (t + lg['phase']) % 1.0
            if p < duty:
                plant(fr, lg, dirv * (stride * (0.5 - p / duty)))
            else:
                u = (p - duty) / (1 - duty)
                plant(fr, lg, dirv * (stride * (-0.5 + C.ease_in_out(u))) + Vector((0, 0, lift_k * lg['reach'] * math.sin(math.pi * u))),
                      pitch=-10 * math.sin(math.pi * u))
        look(fr, pitch=2 * math.sin(4 * math.pi * t), yaw=-2 * waddle * math.sin(2 * math.pi * t))
        mouth(fr, (0.04 + 0.06 * guard_w) + 0.05 * abs(math.sin(2 * math.pi * t)) * (1 + lean / 10))
        tongue(fr)
        chain_pose(fr, t, sway=6, rate=2.0 * rate, trail=(12 + 20 * stride / max(LEG, 1e-4)) * (1 if dirv.y < 0 else -0.5),
                   wag=10, flap=8 * math.sin(4 * math.pi * t))
        return fr

    def gait_marks(kind: str) -> list:
        n = GAITS[kind][0]
        return [('step', 1), ('step', 1 + n // 2)]

    def p_strafe(t: float, side: int) -> Frame:
        return gait(t, 'strafe', Vector((side, 0, 0)), waddle=0.6, guard_w=1.0, roll=side * 3)

    def p_sidestep(t: float, side: int) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.15, 0.92)
        crouch = A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        hop_pose(fr, t, air, crouch, mm(0.06) * air, roll=side * 12 * air)
        mouth(fr, 0.1)
        tongue(fr)
        return fr

    # ================================================================= scenes
    def settle_pose(fr: Frame, t: float, k: float) -> None:
        """Sat down: the body lowered onto its base (k 0 → 1), the legs splaying."""
        body(fr, dz=-SIT * k, pitch=2 * k)
        # the legs splay out sideways rather than fold up under it; the feet lift a little, as a folded leg's ankle skin
        # (blended onto the shin) swings down
        feet(fr, out=0.35 * LEG * k, lift=mm(0.022) * k)
        chain_pose(fr, t, sway=3, wag=4, lift=-8 * k, flap=-6 * k)

    def p_sit_down(t: float) -> Frame:
        fr = Frame()
        k = C.ease_in_out(t)
        settle_pose(fr, t, k)
        look(fr, pitch=-4 * k)
        mouth(fr, 0.1 + 0.15 * k)
        tongue(fr, out=0.2 * k, droop=40 * k)
        return fr

    def p_sit(t: float) -> Frame:
        fr = Frame()
        settle_pose(fr, t, 1.0)
        g = A.pulse(t, 0.5, 0.75)
        look(fr, pitch=-4 + 2 * A.wave(t, 1.0), yaw=16 * g)
        mouth(fr, 0.25 + 0.04 * A.wave(t, 2.0))
        tongue(fr, out=0.2, droop=40, wag=6 * A.wave(t, 1.0))
        return fr

    def p_dizzy(t: float) -> Frame:
        fr = Frame()
        c, s_ = math.cos(t * 4 * math.pi), math.sin(t * 4 * math.pi)
        body(fr, dz=-0.15 * ROOM, roll=7 * s_, pitch=5 * c, yaw=6 * s_)
        feet(fr, out=mm(0.015))
        look(fr, pitch=10 * c, yaw=18 * s_, tilt=14 * s_)
        mouth(fr, 0.2 + 0.15 * s_)
        tongue(fr, out=0.2, droop=30, wag=20 * s_)
        chain_pose(fr, t, sway=14, rate=2.0, wag=14, flap=14 * s_)
        return fr

    # ================================================================= battle
    def p_battle_idle(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, dz=-0.12 * ROOM - mm(0.008) * b, pitch=4, yaw=-4)
        feet(fr, out=mm(0.01))
        look(fr, pitch=4 - 2 * b)
        mouth(fr, 0.12 + 0.12 * A.bounce(t, 4))           # a goofy chomping chatter
        tongue(fr)
        chain_pose(fr, t, sway=6, rate=2.0, wag=10, flap=10 * A.wave(t, 4.0))
        return fr

    def p_hit(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.8)
        dy = mm(0.05) * k
        body(fr, dy=dy, pitch=-12 * k, roll=-4 * k, yaw=-6 * k)
        feet(fr, shift=Vector((0, 0.4 * dy, 0)))
        look(fr, pitch=-8 * k, yaw=-10 * k)
        mouth(fr, 0.55 * k)                                # the lid pops open, the tongue flung out (the hit picture)
        tongue(fr, out=0.3 * k, droop=10 * k, wag=-16 * k)
        chain_pose(fr, t, sway=10, trail=-20 * k, wag=8, flap=20 * k)
        K.add_bones(P, 'hit_bones', fr, k)
        return fr

    def p_hit_heavy(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.62)
        dy, up = mm(0.14) * k, mm(0.07) * k
        body(fr, dy=dy, dz=up, pitch=-30 * k, roll=-14 * k, yaw=-10 * k)
        feet(fr, shift=Vector((0, 0.7 * dy, 0.7 * up)), out=mm(0.04) * k)
        look(fr, pitch=-12 * k, yaw=-14 * k)
        mouth(fr, 0.8 * k)
        tongue(fr, out=0.45 * k, droop=-10 * k, curl=20 * k)
        hang = float(P.get('hit_heavy_chain_hang', 0.0))
        chain_pose(fr, t, sway=16, trail=-30 * k * (1.0 - 0.5 * hang), wag=12, flap=30 * k)
        if hang:
            for m in CH:
                if m['kind'] == 'tassel':
                    fr.r(m['bones'][0], 45 * k * hang, 0, 0)
        K.add_bones(P, 'hit_heavy_bones', fr, k)
        return fr

    def p_ko(t: float) -> Frame:
        """It wobbles, then falls onto its right side ('roll') or its back ('back'), lying `body_width` up (the build
        settles it): the legs splay in the air, the lid falls open with the tongue lolling out, eyes shut."""
        fr = Frame()
        wob = (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = A.step_ease(t, 0.35, 0.85)
        w_ = 7 * math.sin(t * 2 * math.pi * 2.5) * wob
        rd = (-ko_pitch * fall + w_, 0.0, 0.0) if kstyle == 'back' else (0.0, -ko_roll * fall + w_, 0.0)
        bw = float(P.get('body_width', 0.6 * HZ))
        h = HZ * (1 - fall) + bw * fall + ko_lift(t)
        fr.r('root', *rd)
        fr.o('hips', *K.lay_offset(rd, hip, Vector((0, hip.y, h))))
        fr.r('hips', 0, 0, 0)
        fold_legs(fr, fall, splay=30, curl=25, wave=10 * A.pulse(t, 0.72, 1.0) if kstyle == 'back' else 0.0, t=t)
        look(fr, pitch=10 * fall)
        mouth(fr, 0.45 * fall)
        tongue(fr, out=0.4 * fall, droop=30 * fall)
        hang = float(P.get('ko_chain_hang', 0.0))
        chain_pose(fr, t, sway=2, wag=0, lift=-10 * fall, flap=-20 * fall)
        if hang and kstyle == 'roll':
            for m in CH:
                if m['kind'] == 'tassel':
                    fr.r(m['bones'][0], 0, ko_roll * fall * hang, 0)
        K.add_bones(P, 'ko_bones', fr, fall)
        K.scale_bones(P, 'ko_scale', fr, A.step_ease(t, 0.3, 0.75))
        return fr

    def p_win(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.04, 0.34)
        land = A.pulse(t, 0.32, 0.42)
        proud = A.step_ease(t, 0.3, 0.45) * (1 - A.step_ease(t, 0.86, 1.0))       # back to the start: win loops
        hop_pose(fr, t, air, land, mm(0.12) * hop_k * air, roll=6 * A.wave(t, 2.0) * proud)
        mouth(fr, 0.3 * air + 0.6 * proud)
        tongue(fr, out=0.45 * proud, droop=35 * proud, wag=24 * A.wave(t, 3.0) * proud)
        K.add_bones(P, 'win_bones', fr, max(air, A.pulse(t, 0.42, 0.86)))
        K.scale_bones(P, 'win_scale', fr, air)
        return fr

    # ---- strike: 24 frames, impact at 13 (t = 0.5) in every style
    def p_strike(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.42)
        go = A.pulse(t, 0.28, 0.72)
        if style == 'chomp':
            # rears back with the mouth wide open, then lunges and slams it shut on the impact (Lid Chomp)
            dy = mm(0.04) * ant - 0.5 * LEG * go
            body(fr, dy=dy, pitch=-8 * ant + 9 * go, yaw=strike_yaw * go)
            feet(fr, shift=Vector((0, 0.5 * dy, 0)))
            look(fr, pitch=-6 * ant + 6 * go)
            mouth(fr, 0.95 * A.step_ease(t, 0.05, 0.3) * (1 - A.step_ease(t, 0.42, 0.5)))
            tongue(fr)
        elif style == 'tongue':
            # the mouth opens and the tongue lashes out at the target, fully out from 0.48 to 0.62, then snaps back
            out = A.step_ease(t, 0.3, 0.48) * (1 - A.step_ease(t, 0.62, 0.85))
            body(fr, dy=mm(0.02) * ant - mm(0.04) * go, pitch=-6 * ant + 6 * go, yaw=strike_yaw * go)
            feet(fr)
            look(fr, pitch=-6 * ant + 4 * go)
            mouth(fr, 0.6 * A.step_ease(t, 0.15, 0.3) * (1 - A.step_ease(t, 0.75, 0.95)))
            tongue(fr, out=out, droop=float(P.get('tongue_aim', 8.0)) * out, curl=25 * A.pulse(t, 0.5, 0.75))
        elif style == 'spit':
            # shut tight and reared back, then the mouth snaps wide open as it pitches forward: coins (or bolts) burst
            # from socket_mouth on the impact (the attack picture)
            body(fr, dy=mm(0.03) * ant - mm(0.05) * go, pitch=-10 * ant + 10 * go, yaw=strike_yaw * go)
            feet(fr)
            look(fr, pitch=-6 * ant + 6 * go)
            mouth(fr, 0.95 * A.step_ease(t, 0.4, 0.5) * (1 - A.step_ease(t, 0.75, 1.0)))
            tongue(fr, out=0.25 * go, droop=30 * go)
        elif style == 'slam':
            # a hop at the target, landing front first on the impact with the mouth clapping (Treasure Slam)
            air = A.pulse(t, 0.2, 0.5)
            slam = A.pulse(t, 0.44, 0.7)
            up = mm(0.12) * hop_k * air
            body(fr, dy=-0.5 * LEG * A.step_ease(t, 0.2, 0.5) * (1 - A.step_ease(t, 0.7, 1.0)), dz=up,
                 pitch=-6 * air + 14 * slam, yaw=strike_yaw * go)
            feet(fr, lift=0.8 * up, tuck_=0.3 * air, shift=Vector((0, -0.4 * LEG * A.step_ease(t, 0.2, 0.5) * (1 - A.step_ease(t, 0.7, 1.0)), 0)))
            look(fr, pitch=6 * slam)
            mouth(fr, 0.4 * air)
            tongue(fr)
        else:      # 'peck' (a head on a neck: Gearhoot)
            body(fr, dy=mm(0.02) * ant - mm(0.04) * go, pitch=-4 * ant + 8 * go, yaw=strike_yaw * go)
            feet(fr)
            look(fr, pitch=-20 * ant + 30 * go)
            mouth(fr, 0.6 * A.pulse(t, 0.2, 0.5))
            tongue(fr)
        chain_pose(fr, t, sway=6, trail=16 * go - 8 * ant, wag=8, flap=20 * ant - 10 * go)
        K.add_bones(P, 'strike_bones', fr, go)
        K.add_bones(P, 'strike_windup_bones', fr, ant)
        return fr

    def p_cast(t: float) -> Frame:
        fr = Frame()
        up = A.step_ease(t, 0.0, 0.32) * (1 - A.step_ease(t, 0.72, 1.0))
        rel = A.pulse(t, 0.48, 0.72)
        if cstyle == 'spit':
            # gathers shut and low, then the mouth bursts open at `release` (20) and the shower leaves socket_mouth
            body(fr, dz=-0.2 * ROOM * up, dy=mm(0.03) * rel, pitch=-6 * up + 12 * rel)
            feet(fr, out=mm(0.02) * up)
            look(fr, pitch=-6 * up + 8 * rel)
            mouth(fr, 0.95 * A.step_ease(t, 0.45, 0.53) * (1 - A.step_ease(t, 0.75, 1.0)))
            tongue(fr, out=0.3 * rel, droop=40 * rel)
        else:
            # rises tall on its legs, the mouth (or the beak) opening, then thrusts at the target at `release`
            body(fr, pitch=-6 * up + 8 * rel)
            feet(fr)
            look(fr, pitch=-14 * up + 12 * rel)
            mouth(fr, 0.5 * up)
            tongue(fr)
        chain_pose(fr, t, sway=8, rate=2.0, trail=20 * rel, wag=10, flap=30 * up)
        return fr

    def p_shove(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.32)
        go = A.pulse(t, 0.2, 0.55)
        dy = mm(0.04) * ant - 0.45 * LEG * go
        body(fr, dy=dy, pitch=-6 * ant + 8 * go, yaw=strike_yaw * go)
        feet(fr, shift=Vector((0, 0.5 * dy, 0)))
        look(fr, pitch=4 * go)
        mouth(fr, 0.05)
        tongue(fr)
        chain_pose(fr, t, sway=4, trail=18 * go, wag=6)
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
    clip('run', 20, lambda t: gait(t, 'run', FWD, waddle=1.4, lean=4), root_speed=speed_of('run'), markers=gait_marks('run'))
    clip('sit_down', 24, p_sit_down, loop=False, hold=True)
    clip('sit', 120, p_sit, step=2)
    clip('dizzy', 60, p_dizzy, faces=[(1, 'dizzy')])
    clip('battle_idle', 40, p_battle_idle)
    clip('step_fwd', 24, lambda t: gait(t, 'step_fwd', FWD, waddle=0.6, guard_w=1.0), root_speed=speed_of('step_fwd'),
         markers=gait_marks('step_fwd'))
    clip('step_back', 24, lambda t: gait(t, 'step_back', BACK, waddle=0.6, guard_w=1.0), root_speed=speed_of('step_back'),
         markers=gait_marks('step_back'))
    clip('dash', 20, lambda t: gait(t, 'dash', FWD, waddle=1.6, lean=7, rate=1.5), root_speed=speed_of('dash'), markers=gait_marks('dash'))
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
    return made

