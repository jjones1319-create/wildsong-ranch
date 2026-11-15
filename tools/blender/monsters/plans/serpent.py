"""The serpent body plan (ART_2_PLAN §4, batch 5): rig template, sockets, springs and the clip generators for long,
legless monsters: Coilfang (a jade snake in a loose S-coil, its head raised) now; Aurelwyrm (a floating dragon-serpent
with ribbon fins, whiskers and antlers) later, through the `float` option and the ribbon and whisker chain kinds
(hooks, not tuned yet).

A recipe selects it with `PLAN = 'serpent'` (tools/blender/monsters/breeds/RECIPE.md, "Serpent plan"). The same build
(build_ultra.py) drives it as every other plan: rig_specs, sockets, springs, chain_groups, heatless, make_clips,
STAR_CLIPS, MOVE_CLIPS, ROOT_DIRS and KO_ROLL (ko lies flat at `body_width`, measured and settled by the build).

Space: metres; the monster faces −Y, Z is up, +X is its left. Model it resting in its S-coil, head raised. rig_p():
  spine                [Q0 … QN]: the body's centre line from the back of the head to the tail tip (12–16 bones)
  hip                  the anchor: the spine point nearest it is where the bone `hips` starts (pointing headward);
                       the forward chain spine.1.., neck.1..N runs to the head, tail.1.. runs back to the tip
  chest                a point on the neck's base (the build's ko measure reads it)
  radius               the body's half thickness (the ground clearance, the coil's spacing)
  head_c, head_r       the face; `head` runs from Q0 to head_tip, the jaw under it
How it moves: every spine bone keeps its length and gets a heading and an elevation along the body's arc length (the
rest pose's, plus the clip's bends, waves, rears and the coil); the chain is rebuilt from the anchor each frame, belly
down (no roll unless a clip twists it), never under the ground. Its spline is the polyline through the bones' joints.
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

PLAN = 'serpent'
SIDES = K.SIDES
KO_ROLL = 80.0
STRIKE_STYLES = ('lunge', 'squeeze', 'whip')
CAST_STYLES = ('hiss', 'rise')
KO_STYLES = ('belly', 'flat')
SPRINGS = []                # Art 2.0 compatibility only; the Ultra build calls springs(P)
KINDS = ('crest', 'whisker', 'ribbon', 'tail', 'tassel')
HEATLESS_KINDS = ('crest', 'whisker', 'ribbon', 'tassel')

SIDESTEP_DISTANCE = 1.4 * 100 / 150
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}
STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']
# slithers: (frames, the wave's length as a share of the body, its bend in degrees, the body's grip 0..1 (the share of
# the wave's travel the body moves; the rest slips))
SLITHER = {'walk': (30, 0.32, 24, 0.55), 'run': (20, 0.36, 30, 0.6), 'dash': (20, 0.42, 34, 0.65),
           'step_fwd': (24, 0.3, 18, 0.5), 'step_back': (24, 0.3, 16, 0.4), 'strafe': (24, 0.3, 14, 0.4)}


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def _v(p) -> Vector:
    return Vector(p)


def spine_points(P: dict) -> list[Vector]:
    pts = [_v(p) for p in P['spine']]
    if len(pts) < 6:
        raise ValueError('spine: needs at least 6 points (12-16 bones recommended)')
    return pts


def anchor_index(P: dict) -> int:
    """The spine point the `hips` bone starts from: the one nearest P['hip'] (never the head's or the tail's end)."""
    pts = spine_points(P)
    h = _v(P['hip'])
    m = min(range(len(pts)), key=lambda i: (pts[i] - h).length)
    return max(2, min(len(pts) - 3, m))


def chain_layout(P: dict) -> dict:
    """The spine's bones: 'fwd' [(name, head, tail)] from the anchor to the head (hips first), 'tail' [(name, head,
    tail)] from the anchor to the tip; the last `neck_bones` [4] forward bones are neck.1..n (neck.1 nearest the body)."""
    pts = spine_points(P)
    m = anchor_index(P)
    n_fwd = m                          # hips + m - 1 more forward bones
    n_neck = max(1, min(int(P.get('neck_bones', 4)), n_fwd - 1))
    fwd = [('hips', pts[m], pts[m - 1])]
    n_spine = n_fwd - 1 - n_neck
    for j, k in enumerate(range(m - 1, 0, -1)):
        nm = f'spine.{j + 1}' if j < n_spine else f'neck.{j - n_spine + 1}'
        fwd.append((nm, pts[k], pts[k - 1]))
    tail = [(f'tail.{j + 1}', pts[k], pts[k + 1]) for j, k in enumerate(range(m, len(pts) - 1))]
    return {'fwd': fwd, 'tail': tail, 'm': m, 'neck': [b[0] for b in fwd if b[0].startswith('neck.')]}


def head_tip(P: dict) -> Vector:
    if P.get('head_tip'):
        return _v(P['head_tip'])
    return _v(P['head_c']) + Vector((0.0, -0.9 * float(P['head_r']), 0.0))


def jaw_points(P: dict) -> tuple[Vector, Vector]:
    if P.get('jaw'):
        return _v(P['jaw']['head']), _v(P['jaw']['tail'])
    hc, hr = _v(P['head_c']), float(P['head_r'])
    return hc + Vector((0, -0.2 * hr, -0.4 * hr)), hc + Vector((0, -0.95 * hr, -0.45 * hr))


def tongue_of(P: dict) -> dict | None:
    """A forked tongue that flicks: {'points': [p0 … pN] in the mouth, 'parent': 'jaw', 'reach'} (as the blob's)."""
    t = P.get('tongue')
    if not t:
        return None
    pts = [_v(p) for p in t['points']]
    return {'points': pts, 'parent': t.get('parent', 'jaw'), 'bones': [f'tongue.{i + 1}' for i in range(len(pts) - 1)],
            'reach': float(t.get('reach', 0.12 * size_of(P))), 'dir': (pts[-1] - pts[0]).normalized()}


def chains(P: dict) -> list[dict]:
    """Chains: 'crest' (a fan of feathers that flares), 'whisker' (hangs and trails), 'ribbon' (a fin that trails and
    ripples), 'tail', 'tassel'; each {'name', 'kind', 'parent': 'head', 'points', 'stiff', 'heat', 'mirror', 'spring'}."""
    out = []
    for m in P.get('chains') or []:
        kind = m.get('kind', 'crest')
        if kind not in KINDS:
            raise ValueError(f"chain {m.get('name')}: kind {kind!r}, one of {', '.join(KINDS)}")
        nm0 = m.get('name', kind)
        twins = [(nm0 + 'L', 1), (nm0 + 'R', -1)] if m.get('mirror') else [(nm0, 1)]
        for nm, s in twins:
            pts = [mirror(p, s) for p in m['points']]
            out.append({'name': nm, 'kind': kind, 'parent': m.get('parent', 'head'), 'points': pts, 'side': s,
                        'stiff': float(m.get('stiff', 0.0)), 'heat': bool(m.get('heat', kind not in HEATLESS_KINDS)),
                        'spring': bool(m.get('spring', True)), 'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)]})
    return out


def _style(P: dict, key: str, allowed: tuple, default: str) -> str:
    st = P.get(key, default)
    if st not in allowed:
        raise ValueError(f"{key} {st!r}: one of {', '.join(allowed)}")
    return st


def strike_style(P: dict) -> str:
    return _style(P, 'strike_style', STRIKE_STYLES, 'lunge')


def cast_style(P: dict) -> str:
    return _style(P, 'cast_style', CAST_STYLES, 'hiss')


def ko_style(P: dict) -> str:
    return _style(P, 'ko_style', KO_STYLES, 'belly')


def springs(P: dict) -> list[dict]:
    """The tail's last `tail_springs` [2] bones (kind 'tail') and every chain that springs."""
    lay = chain_layout(P)
    n = int(P.get('tail_springs', 2))
    out = [{'kind': 'tail', 'chain': [b[0] for b in lay['tail'][-n:]]}] if n > 0 and lay['tail'] else []
    return out + [{'kind': m['kind'], 'chain': m['bones']} for m in chains(P) if m['spring']]


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → kind for CLIP_CALM: 'spine', 'neck', 'tail', 'tongue', each chain by name or kind."""
    out = {'spine': 'spine', 'neck': 'neck', 'tail': 'tail', 'tongue': 'tongue'}
    for m in chains(P):
        out[m['name']] = m['kind']
    return out


def heatless(P: dict) -> set[str]:
    """The tongue, and crests, whiskers, ribbons and tassels (unless heat=True): the recipe skins them."""
    return {'tongue'} | {m['name'] for m in chains(P) if not m['heat']}


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    lay = chain_layout(P)
    r = float(P.get('radius', 0.08 * sk))
    specs: list[BoneSpec] = [BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk)]
    prev = 'root'
    for i, (nm, h, t) in enumerate(lay['fwd']):
        specs.append(BoneSpec(nm, tuple(h), tuple(t), prev, connect=i > 0, radius=1.6 * r))
        prev = nm
    hr = float(P['head_r'])
    specs.append(BoneSpec('head', tuple(spine_points(P)[0]), tuple(head_tip(P)), prev, connect=True, radius=max(1.6 * r, 1.2 * hr)))
    jh, jt = jaw_points(P)
    specs.append(BoneSpec('jaw', tuple(jh), tuple(jt), 'head', radius=0.5 * hr))
    prev = 'hips'
    for i, (nm, h, t) in enumerate(lay['tail']):
        specs.append(BoneSpec(nm, tuple(h), tuple(t), prev, connect=i > 0, radius=1.6 * r))
        prev = nm
    tg = tongue_of(P)
    if tg:
        for i, nm in enumerate(tg['bones']):
            specs.append(BoneSpec(nm, tuple(tg['points'][i]), tuple(tg['points'][i + 1]), tg['parent'] if i == 0 else tg['bones'][i - 1],
                                  radius=0.03 * sk))
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'head'), radius=0.06 * sk))
    for m in chains(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.05 * sk))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """The game's seven (socket_paw_L / _R at the head's sides: where a strike's effect starts), socket_core at the
    anchor, socket_tongue, socket_<chain>, socket_<prop>; socket_tail at the tail's tip."""
    sk = size_of(P)
    hc, hr = _v(P['head_c']), float(P['head_r'])
    pts = spine_points(P)
    lay = chain_layout(P)
    r = float(P.get('radius', 0.08 * sk))
    _jh, jt = jaw_points(P)
    out = {
        'socket_head': ('head', tuple(hc + Vector((0, 0, hr)))),
        'socket_crown': ('head', tuple(hc + Vector((0, 0, hr + 0.1 * sk)))),
        'socket_back': ('hips', tuple(pts[lay['m']] + Vector((0, 0, r)))),
        'socket_mouth': ('jaw', tuple(jt + Vector((0, -0.015 * sk, 0)))),
        'socket_core': ('hips', tuple(pts[lay['m']])),
        'socket_tail': (lay['tail'][-1][0], tuple(pts[-1])),
    }
    for tag, s in SIDES:
        out[f'socket_paw_{tag}'] = ('head', tuple(hc + Vector((s * 0.7 * hr, -0.3 * hr, -0.2 * hr))))
    tg = tongue_of(P)
    if tg:
        out['socket_tongue'] = (tg['bones'][-1], tuple(tg['points'][-1]))
    for m in chains(P):
        out[f"socket_{m['name']}"] = (m['bones'][-1], tuple(m['points'][-1]))
    for pr in P.get('props', []) or []:
        out[f"socket_{pr['name']}"] = (f"prop.{pr['name']}", tuple(pr['tail']))
    return out


# --------------------------------------------------------------------------- the body's shape
class Shape:
    """One frame's body: per spine bone (head → tail order) a bend `dth` (degrees, + turns the headward direction
    toward the monster's left), a rise `dph` (degrees, + lifts the headward direction), a twist `tw` (degrees, + rolls
    it toward its left), a coil share, the anchor's offset and a yaw about it; the head's own extra turns."""

    def __init__(self, n: int):
        self.dth = np.zeros(n)
        self.dph = np.zeros(n)
        self.tw = np.zeros(n)
        self.coil = 0.0
        self.aim = 0.0               # how far the neck turns to face forward out of the coil
        self.anchor = Vector()
        self.yaw = 0.0
        self.head = [0.0, 0.0, 0.0]  # pitch (+ down), yaw (+ toward its left), tilt
        self.head_tw = 0.0
        self.head_level = None       # degrees: the head's elevation set outright (ko lays it on the ground)
        self.guard = True


def _rz(a: float):
    return K.axis_m((0, 0, 1), math.degrees(a))


def _pitch_axis(th: float) -> Vector:
    """The horizontal axis about which +angle raises a direction whose heading is th."""
    return Vector((math.sin(th), -math.cos(th), 0.0))


# --------------------------------------------------------------------------- clips
def make_clips(cb: A.ClipBuilder, P: dict, only: list[str] | None = None) -> list[A.ClipMeta]:
    rig = K.Rig(cb.arm)
    has = rig.has
    sk = size_of(P)
    made: list[A.ClipMeta] = []
    style, cstyle, kstyle = strike_style(P), cast_style(P), ko_style(P)
    lay = chain_layout(P)
    pts = spine_points(P)
    m = lay['m']
    RAD = float(P.get('radius', 0.08 * sk))
    FLOAT = float(P.get('float', 0.0))
    TG = tongue_of(P) if has('tongue.1') else None
    CH = chains(P)
    JAW = bool(P.get('jaw_open', False))
    CLOSED = P.get('blink_closed')
    hc, hr = _v(P['head_c']), float(P['head_r'])
    lift_tab = P.get('ko_lift') or []
    strike_yaw = float(P.get('strike_yaw', 0.0))
    HZ = float(_v(P['hip']).z)

    def mm(v: float) -> float:
        return v * sk

    # ---- the bones in head → tail order, with their rest headings and elevations (of the headward direction)
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + (pts[i] - pts[i - 1]).length)
    S_TOT, S_ANCHOR = cum[-1], cum[m]
    ORDER = []
    for j, (nm, h, t) in enumerate(lay['fwd']):
        k = m - j                                    # the bone runs Q_k → Q_k-1
        d = (t - h)
        ORDER.append({'name': nm, 'fwd': True, 'L': d.length, 's': 0.5 * (cum[k] + cum[k - 1]), 'hw': d.normalized(),
                      'start': h, 'end': t})
    for j, (nm, h, t) in enumerate(lay['tail']):
        k = m + j                                    # the bone runs Q_k → Q_k+1
        d = (t - h)
        ORDER.append({'name': nm, 'fwd': False, 'L': d.length, 's': 0.5 * (cum[k] + cum[k + 1]), 'hw': -d.normalized(),
                      'start': h, 'end': t})
    ORDER.sort(key=lambda b: b['s'])
    NB = len(ORDER)
    IDX = {b['name']: i for i, b in enumerate(ORDER)}
    th0 = [math.atan2(b['hw'].y, b['hw'].x) for b in ORDER]
    for i in range(1, NB):                           # unwrap along the body
        while th0[i] - th0[i - 1] > math.pi:
            th0[i] -= 2 * math.pi
        while th0[i] - th0[i - 1] < -math.pi:
            th0[i] += 2 * math.pi
    TH0 = np.array(th0)
    PH0 = np.array([math.asin(max(-1.0, min(1.0, b['hw'].z))) for b in ORDER])
    SMID = np.array([b['s'] for b in ORDER])
    NECK = [IDX[n] for n in lay['neck']]
    NECK_END = max(SMID[i] for i in NECK) + 0.5 * max(ORDER[i]['L'] for i in NECK) if NECK else 0.0
    # the lowest each bone's far end may go: its rest height where it lies on the ground, else the body's radius
    for b in ORDER:
        b['zmin'] = min(b['end'].z, RAD) - 0.001 if not FLOAT else -1e9
    head_rest = (head_tip(P) - pts[0])
    HEAD_L = head_rest.length
    HEAD_TH0 = math.atan2(head_rest.y, head_rest.x)
    HEAD_PH0 = math.asin(max(-1.0, min(1.0, head_rest.normalized().z)))
    head_follow = float(P.get('head_follow', 0.35))      # how much of the neck's rise the head takes (a snake keeps it level)
    HEAD_FLOOR = min(0.55 * hr, head_tip(P).z) - 0.001 if not FLOAT else -1e9

    # ---- the coil (sit, sleep): an Archimedean spiral through the anchor, the tail winding inward, the body outward
    cp = P.get('coil') or {}
    sigma = 1.0 if float(cp.get('turn', 1.0)) >= 0 else -1.0
    spacing = float(cp.get('spacing', 2.3 * RAD))
    r_in = float(cp.get('inner', 1.6 * RAD))
    bsp = spacing / (2 * math.pi)
    r_a = math.sqrt(r_in * r_in + 2 * bsp * max(0.0, S_TOT - S_ANCHOR)) + 0.2 * RAD
    i_anchor = IDX['hips']
    th_a = TH0[i_anchor]

    def coil_heading(u: float) -> float:
        if u >= 0:
            integ = (math.sqrt(r_a * r_a + 2 * bsp * u) - r_a) / bsp
        else:
            u_c = (r_in * r_in - r_a * r_a) / (2 * bsp)
            integ = ((math.sqrt(r_a * r_a + 2 * bsp * u) - r_a) / bsp) if u >= u_c else ((r_in - r_a) / bsp + (u - u_c) / r_in)
        return th_a + sigma * integ

    COIL_DTH = np.array([coil_heading(S_ANCHOR - SMID[i]) - TH0[i] for i in range(NB)])
    COIL_DPH = np.array([0.0 if i in NECK else -PH0[i] for i in range(NB)])
    # facing forward out of the coil: the neck's headings turn toward −Y (the representation nearest the coil's)
    FRONT = -0.5 * math.pi
    AIM_DTH = np.zeros(NB)
    for j, i in enumerate(sorted(NECK, key=lambda i: -SMID[i])):        # from the body toward the head
        tgt = FRONT - TH0[i]
        base = COIL_DTH[i]
        tgt += 2 * math.pi * round((base - tgt) / (2 * math.pi))
        AIM_DTH[i] = tgt - base
    nw = {i: (j + 1) / len(NECK) for j, i in enumerate(sorted(NECK, key=lambda i: -SMID[i]))}
    # the coil's centre (from the anchor, to the left of the headward direction for a left turn), so it can sit under
    # the root
    nrm = Vector((-math.sin(th_a), math.cos(th_a), 0.0)) * sigma
    COIL_CENTRE = pts[m] + nrm * r_a
    C.log(f'serpent: {NB} spine bones (anchor {m}, neck {len(NECK)}), body {S_TOT:.2f} m, coil radius {r_a:.2f} m')

    def ko_lift(t: float) -> float:
        return K.table_at(lift_tab, t)

    centre_coil = bool(cp.get('centre', True))
    PARENT = {b['name']: rig.parent[b['name']] for b in ORDER}
    last_neck = ORDER[0]['name']                       # the bone whose far end is the head's base

    def solve(sh: Shape) -> Frame:
        """Rebuild the spine from the anchor: each bone's heading and elevation (rest + bends + coil), its far end kept
        off the ground, belly down unless twisted; then the head on the last neck bone. Returns the keyed Frame."""
        fr = Frame()
        aim = np.array([sh.aim * nw.get(i, 0.0) * AIM_DTH[i] for i in range(NB)]) * sh.coil
        th = TH0 + np.radians(sh.dth + sh.yaw) + sh.coil * COIL_DTH + aim
        ph = np.clip(PH0 + np.radians(sh.dph) + sh.coil * COIL_DPH, -1.4, 1.4)
        anchor = Vector(sh.anchor)
        if centre_coil and sh.coil:
            anchor -= Vector((COIL_CENTRE.x, COIL_CENTRE.y, 0.0)) * sh.coil
        if FLOAT:
            anchor += Vector((0.0, 0.0, FLOAT))
        W: dict[str, object] = {'root': K.I3}
        ends: dict[str, Vector] = {}
        start0 = pts[m] + anchor
        for group in ([i for i in range(NB) if ORDER[i]['fwd']][::-1], [i for i in range(NB) if not ORDER[i]['fwd']]):
            p = start0.copy()
            for i in group:
                b = ORDER[i]
                sgn = 1.0 if b['fwd'] else -1.0
                own = Vector((math.cos(ph[i]) * math.cos(th[i]), math.cos(ph[i]) * math.sin(th[i]), math.sin(ph[i]))) * sgn
                if sh.guard and p.z + b['L'] * own.z < b['zmin']:
                    sz = max(-1.0, min(1.0, (b['zmin'] - p.z) / b['L']))
                    ph[i] = math.asin(sz) * sgn
                    own = Vector((math.cos(ph[i]) * math.cos(th[i]), math.cos(ph[i]) * math.sin(th[i]), math.sin(ph[i]))) * sgn
                th_own = th[i] if b['fwd'] else th[i] + math.pi
                d_ph = (ph[i] - PH0[i]) * sgn
                R = K.axis_m(own, sh.tw[i]) @ K.axis_m(_pitch_axis(th_own), math.degrees(d_ph)) @ _rz(th[i] - TH0[i])
                W[b['name']] = R
                p = p + own * b['L']
                ends[b['name']] = p
        # the head: it follows the neck's turn and some of its rise (a snake holds its head level), then looks
        i_l = IDX[last_neck]
        th_h = HEAD_TH0 + (th[i_l] - TH0[i_l]) + math.radians(sh.head[1])
        ph_h = HEAD_PH0 + head_follow * (ph[i_l] - PH0[i_l]) - math.radians(sh.head[0])
        if sh.head_level is not None:
            ph_h = math.radians(sh.head_level) - math.radians(sh.head[0])
        base = ends[last_neck]
        if sh.guard and base.z + HEAD_L * math.sin(ph_h) < HEAD_FLOOR:
            ph_h = math.asin(max(-1.0, min(1.0, (HEAD_FLOOR - base.z) / max(HEAD_L, 1e-4))))
        hdir = Vector((math.cos(ph_h) * math.cos(th_h), math.cos(ph_h) * math.sin(th_h), math.sin(ph_h)))
        W['head'] = K.axis_m(hdir, sh.head_tw + sh.head[2]) @ K.axis_m(_pitch_axis(th_h), math.degrees(ph_h - HEAD_PH0)) @ _rz(th_h - HEAD_TH0)
        for b in [o['name'] for o in ORDER] + ['head']:
            par = PARENT.get(b, last_neck) if b != 'head' else last_neck
            fr.mat[b] = W[par].transposed() @ W[b]
            fr.rot[b] = [0.0, 0.0, 0.0]
        fr.o('hips', *anchor)
        fr.ends = ends
        return fr

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

    # ---- shaping helpers (each adds to a Shape)
    NECK_ORDER = sorted(NECK, key=lambda i: -SMID[i])      # from the body toward the head
    BODY_IDX = [i for i in range(NB) if i not in NECK]

    def body_w(i: int) -> float:
        """0 on the neck, easing in over the body's first stretch, a little less toward the tail's tip."""
        s = SMID[i]
        if s <= NECK_END:
            return 0.0
        u = (s - NECK_END) / max(S_TOT - NECK_END, 1e-4)
        return A.step_ease(u, 0.0, 0.18) * (1.0 - 0.25 * u)

    def wave(sh: Shape, t: float, amp: float, lam: float, cycles: float = 1.0, back: bool = False, phase: float = 0.0) -> None:
        """A lateral wave down the body (`amp` degrees of bend, `lam` metres long) travelling toward the tail
        (`back`: toward the head) `cycles` times a clip: a slither, or breathing."""
        sgn = 1.0 if back else -1.0
        for i in BODY_IDX:
            sh.dth[i] += amp * body_w(i) * math.sin(2 * math.pi * (SMID[i] / max(lam, 1e-4) + sgn * cycles * t + phase))

    def neck(sh: Shape, rise: float = 0.0, s_curve: float = 0.0, yaw: float = 0.0, sway: float = 0.0, t: float = 0.0,
             rate: float = 1.0, bend: float = 0.0) -> None:
        """The neck: `rise` degrees more lift (most near the body), `s_curve` a cobra's S (up near the body, down near
        the head), `yaw` a turn shared along it (+ toward its left), `sway` side to side with a lag, `bend` a lateral C."""
        n = max(1, len(NECK_ORDER))
        for j, i in enumerate(NECK_ORDER):
            u = j / max(1, n - 1)
            sh.dph[i] += rise * (1.0 - 0.5 * u) / n * 2.0 + s_curve * (1.0 - 2.0 * u)
            sh.dth[i] += yaw / n + bend * (1.0 - u) / n * 2.0 + sway * math.sin(2 * math.pi * (rate * t - 0.08 * j)) / n
        # the body's first bones share a little of the rise, so the curve stays smooth
        first = [i for i in BODY_IDX if SMID[i] > NECK_END][:2]
        for k, i in enumerate(first):
            sh.dph[i] += rise * (0.25 if k == 0 else 0.1)

    def look(sh: Shape, pitch: float = 0.0, yaw: float = 0.0, tilt: float = 0.0) -> None:
        sh.head[0] += pitch
        sh.head[1] += yaw
        sh.head[2] += tilt

    TAIL_END = [i for i in range(NB) if not ORDER[i]['fwd']][-3:]

    def tail_tip(sh: Shape, t: float, rattle: float = 0.0, lift: float = 0.0, rate: float = 6.0) -> None:
        """The tail's last bones: shaken side to side (a rattle), lifted `lift` degrees (its tip up)."""
        for k, i in enumerate(TAIL_END):
            w = (k + 1) / len(TAIL_END)
            sh.dth[i] += rattle * w * math.sin(2 * math.pi * rate * t + k)
            sh.dph[i] -= lift * w

    def jaw(fr: Frame, deg_: float) -> None:
        if JAW:
            fr.r('jaw', deg_, 0, 0)

    def tongue(fr: Frame, out: float = 0.0, wag: float = 0.0) -> None:
        """The forked tongue slid `out` (0..1) of its reach (as the blob's), wagging."""
        if not TG:
            return
        n = len(TG['bones'])
        step = TG['reach'] * max(0.0, out) / max(1, n - 1)
        for i, b in enumerate(TG['bones']):
            fr.o(b, *(TG['dir'] * (step if i > 0 else 0.0)))
            fr.r(b, 0, 0, wag * (0.3 if i == 0 else 0.7))

    def flick(t: float, at: float, dur: float = 0.12) -> float:
        """A quick tongue flick (out and back twice) starting at `at`."""
        return A.pulse(t, at, at + dur * 0.5) + A.pulse(t, at + dur * 0.5, at + dur)

    def chain_pose(fr: Frame, t: float, flare: float = 0.0, sway: float = 0.0, rate: float = 1.0, trail: float = 0.0,
                   wag: float = 0.0) -> None:
        """Chains by kind: a crest flares (+ lifts its feathers) and sways, whiskers and tassels hang and trail,
        ribbons trail and ripple, a tail wags."""
        for mc in CH:
            n = len(mc['bones'])
            k = 1.0 - mc['stiff']
            for i, b in enumerate(mc['bones']):
                lag = 0.08 * i
                share = (0.6 + 0.8 * i / max(1, n - 1)) / n
                if mc['kind'] == 'crest':
                    fr.r(b, flare * share * k, mc['side'] * 0.3 * flare * share * k, sway * share * k * A.wave(t - lag, rate))
                elif mc['kind'] == 'ribbon':
                    fr.r(b, trail * share * k + sway * share * k * A.wave(t - lag, rate, 0.25), 0, 0.5 * sway * share * k * A.wave(t - lag, rate))
                elif mc['kind'] in ('whisker', 'tassel'):
                    fr.r(b, trail * share * k, 0, sway * share * k * A.wave(t - lag, rate))
                else:
                    fr.r(b, 0, 0, 1.6 * wag * share * k * A.wave(t - lag, rate))

    def finish(fr: Frame, t: float, jaw_deg: float = 0.0, tongue_out: float = 0.0, flare: float = 0.0, sway: float = 6.0,
               rate: float = 1.0, trail: float = 0.0, wag: float = 4.0) -> Frame:
        jaw(fr, jaw_deg)
        tongue(fr, tongue_out)
        chain_pose(fr, t, flare=flare, sway=sway, rate=rate, trail=trail, wag=wag)
        return fr

    def lift_body(sh: Shape, dz: float) -> None:
        sh.anchor += Vector((0.0, 0.0, dz))

    # ================================================================= ranch life
    def p_idle(t: float) -> Frame:
        sh = Shape(NB)
        glance = A.pulse(t, 0.55, 0.85)
        wave(sh, t, 4.0, 0.5 * S_TOT)
        neck(sh, rise=3 * A.wave(t, 2.0), sway=8, t=t, yaw=10 * glance)
        look(sh, yaw=14 * glance, tilt=4 * glance)
        tail_tip(sh, t, rattle=3, rate=2.0)
        return finish(solve(sh), t, tongue_out=flick(t, 0.3), sway=6)

    def p_idle_happy(t: float) -> Frame:
        sh = Shape(NB)
        b = A.bounce(t, 3)
        wave(sh, t, 8.0, 0.45 * S_TOT, cycles=2.0)
        neck(sh, rise=6 + 8 * b, sway=14, t=t, rate=2.0)
        look(sh, pitch=-6, tilt=8 * A.wave(t, 2.0))
        tail_tip(sh, t, rattle=12, lift=10, rate=6.0)
        return finish(solve(sh), t, jaw_deg=10, tongue_out=flick(t, 0.2) + flick(t, 0.65), flare=25, sway=14, rate=3.0)

    def p_idle_tired(t: float) -> Frame:
        sh = Shape(NB)
        yawn = A.pulse(t, 0.45, 0.72)
        wave(sh, t, 2.0, 0.5 * S_TOT)
        neck(sh, rise=-22 + 14 * yawn, sway=3, t=t)
        look(sh, pitch=8 - 22 * yawn)
        return finish(solve(sh), t, jaw_deg=38 * yawn, flare=-10, sway=3)

    def p_idle_sad(t: float) -> Frame:
        sh = Shape(NB)
        wave(sh, t, 2.0, 0.5 * S_TOT)
        neck(sh, rise=-30, yaw=-8 + 4 * A.pulse(t, 0.5, 0.7), sway=2, t=t)
        look(sh, pitch=12)
        return finish(solve(sh), t, flare=-18, sway=2)

    def p_idle_sick(t: float) -> Frame:
        sh = Shape(NB)
        w = A.wave(t, 1.0)
        shiver = A.wave(t, 9.0) * A.pulse(t, 0.25, 0.5)
        wave(sh, t, 4.0 + 3 * shiver, 0.4 * S_TOT)
        neck(sh, rise=-14, yaw=10 * w, sway=6, t=t)
        look(sh, pitch=8, tilt=8 * w)
        return finish(solve(sh), t, jaw_deg=6, flare=-10, sway=5)

    def p_sleep(t: float) -> Frame:
        sh = Shape(NB)
        sh.coil, sh.aim = 1.0, 0.5
        for i in NECK:                       # the neck comes down to lie along the coil, the head resting on it
            sh.dph[i] -= 0.85 * math.degrees(PH0[i])
        neck(sh, rise=2 * A.wave(t, 1.0))
        look(sh, pitch=8)
        return finish(solve(sh), t, flare=-15, sway=1)

    def p_eat(t: float) -> Frame:
        sh = Shape(NB)
        dip = A.step_ease(t, 0.0, 0.2) * (1 - A.step_ease(t, 0.85, 1.0))
        chew = dip * abs(math.sin(t * 2 * math.pi * 3))
        wave(sh, t, 3.0, 0.5 * S_TOT)
        neck(sh, rise=-32 * dip, sway=3, t=t)
        look(sh, pitch=24 * dip)
        return finish(solve(sh), t, jaw_deg=26 * chew, tongue_out=flick(t, 0.1), sway=4)

    def p_pet(t: float) -> Frame:
        sh = Shape(NB)
        b = A.bounce(t, 2)
        wave(sh, t, 4.0, 0.45 * S_TOT, cycles=2.0)
        neck(sh, rise=6 + 4 * b, sway=6, t=t, rate=2.0, yaw=8)
        look(sh, pitch=-8, tilt=16 + 3 * A.wave(t, 2.0), yaw=6)
        tail_tip(sh, t, rattle=8, lift=8, rate=4.0)
        return finish(solve(sh), t, jaw_deg=6, flare=15, sway=10, rate=2.0)

    def p_look(t: float) -> Frame:
        sh = Shape(NB)
        a = A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56))
        b = A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        yaw = 40 * a - 40 * b
        wave(sh, t, 3.0, 0.5 * S_TOT)
        neck(sh, yaw=0.6 * yaw, rise=4 * (a + b))
        look(sh, yaw=0.5 * yaw, tilt=0.1 * yaw)
        return finish(solve(sh), t, tongue_out=flick(t, 0.3) + flick(t, 0.72), sway=6)

    def hop_shape(sh: Shape, t: float, air: float, crouch: float, up: float) -> None:
        """A snake's hop: the body springs off the ground, the neck rearing as it rises and tucking as it lands."""
        lift_body(sh, up)
        neck(sh, rise=24 * air - 12 * crouch, s_curve=10 * crouch)
        wave(sh, t, 6.0 * crouch, 0.4 * S_TOT)
        tail_tip(sh, t, lift=20 * air)

    def p_hop(t: float) -> Frame:
        sh = Shape(NB)
        air = A.pulse(t, 0.28, 0.82)
        crouch = A.pulse(t, 0.0, 0.28) + 0.8 * A.pulse(t, 0.8, 1.0)
        hop_shape(sh, t, air, crouch, mm(0.09) * float(P.get('hop', 1.0)) * air)
        return finish(solve(sh), t, jaw_deg=10 * air, flare=20 * air, sway=6)

    def p_celebrate(t: float) -> Frame:
        sh = Shape(NB)
        air = A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        land = A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)
        hop_shape(sh, t, air, land, mm(0.08) * float(P.get('hop', 1.0)) * air)
        neck(sh, sway=20, t=t, rate=2.0)
        return finish(solve(sh), t, jaw_deg=16, tongue_out=flick(t, 0.45), flare=30, sway=16, rate=3.0)

    # ================================================================= moving: slithering
    def slither_speed(kind: str) -> float:
        n, lam, _amp, grip = SLITHER[kind]
        return lam * S_TOT / (n / A.FPS) * grip

    def p_slither(t: float, kind: str, back: bool = False, guard_w: float = 0.0) -> Frame:
        """A wave of bends runs down the body one wavelength a clip (toward the head going backwards); the body grips
        `grip` of it (the root speed), the neck held up and steady, the head on the target."""
        n, lam, amp, _grip = SLITHER[kind]
        sh = Shape(NB)
        wave(sh, t, amp, lam * S_TOT, back=back)
        neck(sh, rise=4 + 6 * guard_w, s_curve=6 * guard_w, sway=4, t=t, rate=2.0)
        look(sh, pitch=2 * math.sin(4 * math.pi * t))
        tail_tip(sh, t, rattle=4, rate=4.0)
        return finish(solve(sh), t, flare=10 * guard_w, sway=6, rate=2.0, trail=10)

    def slither_marks(kind: str) -> list:
        n = SLITHER[kind][0]
        return [('step', 1), ('step', 1 + n // 2)]

    def p_strafe(t: float, side: int) -> Frame:
        """Sidewinding, approximately: the slither's wave, the neck turned a little toward the travel."""
        n, lam, amp, _grip = SLITHER['strafe']
        sh = Shape(NB)
        wave(sh, t, amp, lam * S_TOT)
        neck(sh, rise=8, s_curve=6, yaw=side * 10, sway=4, t=t, rate=2.0)
        look(sh, yaw=-side * 8)
        return finish(solve(sh), t, flare=10, sway=6, rate=2.0)

    def p_sidestep(t: float, side: int) -> Frame:
        sh = Shape(NB)
        air = A.pulse(t, 0.15, 0.92)
        crouch = A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        hop_shape(sh, t, air, crouch, mm(0.05) * air)
        neck(sh, bend=-side * 20 * air)
        wave(sh, t, 10 * air, 0.6 * S_TOT, cycles=0.0, phase=0.25 * side)
        return finish(solve(sh), t, flare=10, sway=6)

    # ================================================================= scenes: the coil
    def p_sit_down(t: float) -> Frame:
        sh = Shape(NB)
        k = C.ease_in_out(t)
        sh.coil, sh.aim = k, k
        neck(sh, rise=8 * k)
        return finish(solve(sh), t, sway=3)

    def p_sit(t: float) -> Frame:
        sh = Shape(NB)
        sh.coil, sh.aim = 1.0, 1.0
        g = A.pulse(t, 0.5, 0.75)
        neck(sh, rise=8 + 2 * A.wave(t, 1.0), sway=5, t=t, yaw=12 * g)
        look(sh, yaw=10 * g)
        tail_tip(sh, t, rattle=3, rate=2.0)
        return finish(solve(sh), t, tongue_out=flick(t, 0.2), sway=4)

    def p_dizzy(t: float) -> Frame:
        sh = Shape(NB)
        c, s_ = math.cos(t * 4 * math.pi), math.sin(t * 4 * math.pi)
        wave(sh, t, 8.0, 0.4 * S_TOT, cycles=2.0)
        neck(sh, rise=8 * c, yaw=24 * s_)
        look(sh, pitch=10 * c, yaw=14 * s_, tilt=16 * s_)
        return finish(solve(sh), t, jaw_deg=12, tongue_out=0.3, flare=10, sway=14, rate=2.0)

    # ================================================================= battle
    def p_battle_idle(t: float) -> Frame:
        sh = Shape(NB)
        b = A.bounce(t, 2)
        wave(sh, t, 5.0, 0.45 * S_TOT)
        neck(sh, rise=16 + 4 * b, s_curve=12, sway=6, t=t, rate=2.0)
        look(sh, pitch=-4)
        tail_tip(sh, t, rattle=16, lift=12, rate=8.0)
        return finish(solve(sh), t, tongue_out=flick(t, 0.5), flare=20, sway=6, rate=2.0)

    def p_hit(t: float) -> Frame:
        sh = Shape(NB)
        k = A.pulse(t, 0.0, 0.8)
        sh.anchor = Vector((0.0, mm(0.04) * k, 0.0))
        wave(sh, t, 10 * k, 0.45 * S_TOT, cycles=0.0, phase=0.25)
        neck(sh, rise=16 * k, yaw=-20 * k, s_curve=8 * k)
        look(sh, pitch=-22 * k, tilt=-8 * k)
        tail_tip(sh, t, lift=10 * k)
        fr = finish(solve(sh), t, jaw_deg=16 * k, flare=-20 * k, sway=10)
        K.add_bones(P, 'hit_bones', fr, k)
        return fr

    def p_hit_heavy(t: float) -> Frame:
        sh = Shape(NB)
        k = A.pulse(t, 0.0, 0.62)
        sh.anchor = Vector((0.0, mm(0.12) * k, mm(0.04) * k))
        wave(sh, t, 18 * k, 0.4 * S_TOT, cycles=0.0, phase=0.25)
        neck(sh, rise=36 * k, yaw=-26 * k, s_curve=10 * k)
        look(sh, pitch=-30 * k, tilt=-12 * k)
        for i in range(NB):                  # the front rolls, showing its belly (the hit picture)
            sh.tw[i] = 55 * k * max(0.0, 1.0 - SMID[i] / max(0.6 * S_TOT, 1e-4))
        sh.head_tw = 25 * k
        tail_tip(sh, t, rattle=20 * k, lift=25 * k, rate=4.0)
        hang = float(P.get('hit_heavy_chain_hang', 0.0))
        fr = finish(solve(sh), t, jaw_deg=22 * k, flare=-25 * k, sway=14, trail=-25 * k * (1.0 - 0.5 * hang))
        K.add_bones(P, 'hit_heavy_bones', fr, k)
        return fr

    def p_ko(t: float) -> Frame:
        """It sways, then flops flat, the neck and head down on the ground, the body twisted belly-up (`ko_twist`
        [140°]; 'flat' doesn't twist) at body_width (the build settles it), the tongue lolling, eyes shut."""
        sh = Shape(NB)
        sh.guard = False                     # the lie is rigid in body_width, so the build's settle is exact
        wob = (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = A.step_ease(t, 0.35, 0.85)
        bw = float(P.get('body_width', RAD))
        h = HZ * (1 - fall) + bw * fall + ko_lift(t)
        sh.anchor = Vector((0.0, 0.0, h - HZ))
        neck(sh, yaw=14 * math.sin(t * 2 * math.pi * 2.5) * wob)
        for i in range(NB):                  # everything comes down level with the anchor
            sh.dph[i] -= math.degrees(PH0[i]) * fall
        wave(sh, t, 12 * fall, 0.5 * S_TOT, cycles=0.0, phase=0.25)
        if kstyle == 'belly':
            tw = float(P.get('ko_twist', 140.0))
            for i in range(NB):
                sh.tw[i] = tw * fall * min(1.0, 0.4 + SMID[i] / max(0.5 * S_TOT, 1e-4))
            sh.head_tw = 0.6 * tw * fall
        else:
            sh.head_tw = 70 * fall
        sh.head_level = -6.0 * fall + math.degrees(HEAD_PH0) * (1 - fall)
        fr = solve(sh)
        hang = float(P.get('ko_chain_hang', 0.0))
        finish(fr, t, jaw_deg=20 * fall, tongue_out=0.7 * fall, flare=-30 * fall, sway=2 * (1 - fall),
               trail=40 * fall * hang)
        K.add_bones(P, 'ko_bones', fr, fall)
        K.scale_bones(P, 'ko_scale', fr, A.step_ease(t, 0.3, 0.75))
        return fr

    def p_win(t: float) -> Frame:
        sh = Shape(NB)
        air = A.pulse(t, 0.04, 0.34)
        land = A.pulse(t, 0.32, 0.42)
        proud = A.step_ease(t, 0.3, 0.45) * (1 - A.step_ease(t, 0.86, 1.0))       # back to the start: win loops
        hop_shape(sh, t, air, land, mm(0.09) * float(P.get('hop', 1.0)) * air)
        neck(sh, rise=26 * proud, sway=26 * proud, t=t, rate=2.0)              # it rears up and dances
        look(sh, pitch=-10 * proud)
        tail_tip(sh, t, rattle=18 * proud, lift=15 * proud, rate=8.0)
        fr = finish(solve(sh), t, jaw_deg=16 * proud, tongue_out=flick(t, 0.5) + flick(t, 0.75), flare=35 * max(air, proud),
                    sway=16, rate=2.0)
        K.add_bones(P, 'win_bones', fr, max(air, A.pulse(t, 0.42, 0.86)))
        K.scale_bones(P, 'win_scale', fr, air)
        return fr

    # ---- strike: 24 frames, impact at 13 (t = 0.5) in every style
    TAIL_IDX = [i for i in range(NB) if not ORDER[i]['fwd']]

    def p_strike(t: float) -> Frame:
        sh = Shape(NB)
        ant = A.pulse(t, 0.0, 0.42)
        go = A.pulse(t, 0.28, 0.72)
        jaw_deg = 0.0
        if style == 'lunge':
            # coils the neck back into an S, then shoots the head out level at the target with the mouth wide, the body
            # sliding after it (Fang Snap; the attack picture)
            sh.anchor = Vector((0.0, mm(0.03) * ant - mm(0.12) * go, 0.0))
            neck(sh, rise=24 * ant - 20 * go, s_curve=20 * ant - 6 * go, yaw=strike_yaw * go)
            look(sh, pitch=-12 * ant + 6 * go)
            wave(sh, t, 12 * ant, 0.4 * S_TOT, cycles=0.0, phase=0.25)
            jaw_deg = 44 * A.pulse(t, 0.3, 0.7)
        elif style == 'squeeze':
            # the front of the body loops out and wraps round the target ahead, closing on the impact (Coil Squeeze)
            sh.anchor = Vector((0.0, -mm(0.06) * go, 0.0))
            neck(sh, bend=130 * go, rise=10 * ant - 8 * go, yaw=strike_yaw * go)
            front = [i for i in BODY_IDX if SMID[i] < NECK_END + 0.25 * S_TOT]
            for i in front:
                sh.dth[i] += 40 * go / max(1, len(front))
            look(sh, yaw=-40 * go, pitch=6 * go)
            jaw_deg = 12 * go
        else:      # 'whip'
            # the tail swings round from behind and lashes forward at the target, the body twisting into it
            for j, i in enumerate(TAIL_IDX):
                w = (j + 1) / len(TAIL_IDX)
                sh.dth[i] += (-40 * ant + 70 * go) * w * 2.0 / len(TAIL_IDX) * 3.0
            neck(sh, rise=8, yaw=10 * ant - 10 * go + strike_yaw * go)
            look(sh, yaw=-10 * go)
            jaw_deg = 10 * go
        fr = finish(solve(sh), t, jaw_deg=jaw_deg, flare=20 * ant + 10 * go, sway=6, trail=12 * go)
        K.add_bones(P, 'strike_bones', fr, go)
        K.add_bones(P, 'strike_windup_bones', fr, ant)
        return fr

    def p_cast(t: float) -> Frame:
        sh = Shape(NB)
        up = A.step_ease(t, 0.0, 0.32) * (1 - A.step_ease(t, 0.72, 1.0))
        rel = A.pulse(t, 0.48, 0.72)
        if cstyle == 'hiss':
            # rears up with the crest raised, then hisses at the target at `release` (a mist from socket_mouth)
            neck(sh, rise=30 * up - 10 * rel, s_curve=8 * up)
            look(sh, pitch=-16 * up + 18 * rel)
            jaw_deg = 34 * rel + 8 * up
        else:
            # rears up tall, the body's front lifting too, then sweeps down at the target at `release`
            neck(sh, rise=44 * up - 26 * rel)
            for i in [i for i in BODY_IDX if SMID[i] < NECK_END + 0.2 * S_TOT]:
                sh.dph[i] += 10 * up
            look(sh, pitch=-12 * up + 16 * rel)
            jaw_deg = 16 * rel
        wave(sh, t, 6 * up, 0.45 * S_TOT, cycles=0.0, phase=0.25)
        tail_tip(sh, t, rattle=14 * up, lift=10 * up, rate=8.0)
        return finish(solve(sh), t, jaw_deg=jaw_deg, tongue_out=flick(t, 0.2) + 0.5 * rel, flare=35 * up, sway=8, rate=2.0, trail=20 * rel)

    def p_shove(t: float) -> Frame:
        sh = Shape(NB)
        ant = A.pulse(t, 0.0, 0.32)
        go = A.pulse(t, 0.2, 0.55)
        sh.anchor = Vector((0.0, mm(0.03) * ant - mm(0.1) * go, 0.0))
        neck(sh, rise=10 * ant - 14 * go, yaw=strike_yaw * go)
        look(sh, pitch=-6 * ant + 8 * go)
        wave(sh, t, 8 * ant, 0.4 * S_TOT, cycles=0.0, phase=0.25)
        return finish(solve(sh), t, flare=10 * go, sway=4, trail=14 * go)

    # ---- the list (the same names, lengths, markers and faces as every plan)
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
    clip('walk', 30, lambda t: p_slither(t, 'walk'), root_speed=slither_speed('walk'), markers=slither_marks('walk'))
    clip('run', 20, lambda t: p_slither(t, 'run'), root_speed=slither_speed('run'), markers=slither_marks('run'))
    clip('sit_down', 24, p_sit_down, loop=False, hold=True)
    clip('sit', 120, p_sit, step=2)
    clip('dizzy', 60, p_dizzy, faces=[(1, 'dizzy')])
    clip('battle_idle', 40, p_battle_idle)
    clip('step_fwd', 24, lambda t: p_slither(t, 'step_fwd', guard_w=1.0), root_speed=slither_speed('step_fwd'),
         markers=slither_marks('step_fwd'))
    clip('step_back', 24, lambda t: p_slither(t, 'step_back', back=True, guard_w=1.0), root_speed=slither_speed('step_back'),
         markers=slither_marks('step_back'))
    clip('dash', 20, lambda t: p_slither(t, 'dash'), root_speed=slither_speed('dash'), markers=slither_marks('dash'))
    clip('strike', 24, p_strike, loop=False, markers=[('impact', 13)], faces=[(1, 'angry'), (20, 'neutral')])
    clip('cast', 36, p_cast, loop=False, markers=[('release', 20)], faces=[(1, 'strain'), (28, 'neutral')])
    clip('shove', 24, p_shove, loop=False, markers=[('impact', 10)])
    clip('hit', 15, p_hit, loop=False, faces=[(1, 'surprised'), (12, 'neutral')], shut=lambda t: 0.85 * A.pulse(t, 0.0, 0.7))
    clip('hit_heavy', 24, p_hit_heavy, loop=False, faces=[(1, 'strain'), (18, 'neutral')], shut=lambda t: 0.9 * A.pulse(t, 0.0, 0.75))
    clip('ko', 36, p_ko, loop=False, hold=True, faces=[(1, 'strain'), (20, 'dizzy')],
         shut=lambda t: max(0.8 * A.pulse(t, 0.0, 0.3), A.step_ease(t, 0.35, 0.6)))
    clip('win', 60, p_win, markers=[('land', 22)], faces=[(1, 'happy')])
    clip('strafe_l', 24, lambda t: p_strafe(t, 1), root_speed=slither_speed('strafe'), markers=[('step', 1), ('step', 13)])
    clip('strafe_r', 24, lambda t: p_strafe(t, -1), root_speed=slither_speed('strafe'), markers=[('step', 1), ('step', 13)])
    clip('sidestep_l', 8, lambda t: p_sidestep(t, 1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    clip('sidestep_r', 8, lambda t: p_sidestep(t, -1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    return made
