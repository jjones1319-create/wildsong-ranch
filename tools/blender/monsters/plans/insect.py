"""The insect body plan (ART_2_PLAN §4, batch 7): rig template, sockets, springs and the clip generators for bugs:
Nibblegrub (a caterpillar: a head and four plump segments on six stubby legs; it crawls in humps and curls into a ball
to roll), Velvesper (a moth that hovers on two pairs of big velvet wings, its little legs dangling, feathery antennae)
and Nibblegrub's cocoon (`form: 'cocoon'`: a hanging silk cocoon with a reduced set of clips: see below).

A recipe selects it with `PLAN = 'insect'` (tools/blender/monsters/breeds/RECIPE.md, "Insect plan"). The same build
(build_ultra.py) drives it as every other plan: rig_specs, sockets, springs, chain_groups, heatless, make_clips,
STAR_CLIPS, MOVE_CLIPS, ROOT_DIRS and KO_ROLL (ko lies down at `body_width`, measured and settled by the build).

Space: metres; the monster faces −Y, Z is up, +X is its left. Model a crawler on the ground and a hoverer hovering, its
wings open. From rig_p() (`P`):
  form                 'crawl' (Nibblegrub), 'hover' (Velvesper) or 'cocoon'
  hip                  the body's pivot: `body` (parent `root`) carries everything; it bobs, leans, turns and falls
  front                [hip, F1 … Fk]: the segments ahead of it to the back of the head: `chest`, front.1..
  rear                 [hip, R1 … Rm]: the segments behind it to the tail's end: `hips`, rear.1..
  head_c, head_r       the face; `head` runs from the last front point to head_tip, the mouth is `jaw`
  chest                the build's ko measure reads it (required: a point on the first front segment)
  legs, moth_wings     the stubby legs (moved by angle) and a moth's wing pairs (not `wings`: see wings() below)
  head_reach           how far the head's skin reaches from head_c [head_r] (the ground guard; big cheeks reach further)
Rotations are world-aligned degrees relative to the parent at rest. No clip scales a bone (the ClipBuilder.scale
abs() trap on tilted bones).
"""
from __future__ import annotations

import math

from mathutils import Vector

from lib import anim as A
from lib import common as C
from lib.rig import BoneSpec
from monsters.plans import kin as K
from monsters.plans.kin import Frame, mirror

PLAN = 'insect'
SIDES = K.SIDES
KO_ROLL = 80.0
FORMS = ('crawl', 'hover', 'cocoon')
STRIKE_STYLES = ('roll', 'chomp', 'spray', 'dust', 'flutter', 'beam')
CAST_STYLES = ('spray', 'glow', 'dust')
KO_STYLES = ('back', 'roll', 'flat')
SPRINGS = []                # Art 2.0 compatibility only; the Ultra build calls springs(P)
# a crawler's belly lies on the floor beside the root bone, which would take its heat weights (and pin it there): the
# build gives them to `body` instead (build_ultra.py ROOT_HEAT_TO, opt-in)
ROOT_HEAT_TO = 'body'
KINDS = ('antenna', 'tassel', 'tail')

SIDESTEP_DISTANCE = 1.4 * 100 / 150
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}
STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']
# the cocoon's own reduced set (it never battles; RECIPE.md "Insect plan", the cocoon)
COCOON_CLIPS = ['idle', 'wriggle', 'split']
# crawl / glide speeds (model metres per second at Puddlepup's size; × size_k)
SPEED = {'walk': 0.22, 'run': 0.5, 'dash': 0.8, 'step_fwd': 0.2, 'step_back': 0.16, 'strafe': 0.2}


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def _v(p) -> Vector:
    return Vector(p)


def form_of(P: dict) -> str:
    f = P.get('form', 'crawl')
    if f not in FORMS:
        raise ValueError(f"form {f!r}: one of {', '.join(FORMS)}")
    return f


def front_points(P: dict) -> list[Vector]:
    pts = [_v(p) for p in (P.get('front') or [])]
    return pts if len(pts) >= 2 else [_v(P['hip']), _v(P['hip']) + Vector((0, -0.1 * size_of(P), 0))]


def rear_points(P: dict) -> list[Vector]:
    return [_v(p) for p in (P.get('rear') or [])]


def front_names(P: dict) -> list[str]:
    n = len(front_points(P)) - 1
    return ['chest'] + [f'front.{i}' for i in range(1, n)]


def rear_names(P: dict) -> list[str]:
    n = len(rear_points(P)) - 1
    return (['hips'] + [f'rear.{i}' for i in range(1, n)]) if n >= 1 else []


def head_tip(P: dict) -> Vector:
    if P.get('head_tip'):
        return _v(P['head_tip'])
    return _v(P['head_c']) + Vector((0.0, -0.9 * float(P['head_r']), 0.0))


def jaw_points(P: dict) -> tuple[Vector, Vector]:
    if P.get('jaw'):
        return _v(P['jaw']['head']), _v(P['jaw']['tail'])
    hc, hr = _v(P['head_c']), float(P['head_r'])
    return hc + Vector((0, -0.4 * hr, -0.4 * hr)), hc + Vector((0, -0.95 * hr, -0.5 * hr))


def legs(P: dict) -> list[dict]:
    """The stubby legs, left then right: P['legs'] lists the left ones front to back as {'hip', 'knee', 'foot',
    'parent'}; bones leg<i> (hip → knee) and shin<i> (knee → foot), moved by angle (tiny legs don't need planting)."""
    out = []
    for tag, s in SIDES:
        for i, lg in enumerate(P.get('legs') or [], start=1):
            out.append({'i': i, 'tag': tag, 's': s, 'upper': f'leg{i}.{tag}', 'lower': f'shin{i}.{tag}',
                        'hip': mirror(lg['hip'], s), 'knee': mirror(lg['knee'], s), 'foot': mirror(lg['foot'], s),
                        'parent': lg.get('parent', 'chest')})
    return out


def wings(P: dict) -> list[dict]:
    """Moth wings: P['moth_wings'] lists the left ones as {'name', 'points': [root, mid, tip], 'parent': 'chest', 'lag',
    'fold'}; mirrored to <name>L / <name>R, bones <name>L.1, .2. They beat about the body's long axis and fold back over
    the body. (Not P['wings']: the build and the shape preview read that one as the quadruped/biped wing dict and would
    ask for flying clips.)"""
    out = []
    for w in P.get('moth_wings') or []:
        for tag, s in SIDES:
            nm = f"{w.get('name', 'wing')}{tag}"
            pts = [mirror(p, s) for p in w['points']]
            out.append({'name': nm, 'base': w.get('name', 'wing'), 'tag': tag, 's': s, 'points': pts, 'parent': w.get('parent', 'chest'),
                        'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)], 'lag': float(w.get('lag', 0.0)),
                        'fold': float(w.get('fold', 70.0)),
                        # Nov 18 (Velvesper; opt-in, absent = as before): an upright hoverer's wings beat about its
                        # upright long axis, not the level one. `beat_axis` [(0, 1, 0)] is the axis the beat turns about
                        # (+ = the power stroke), `fold_axis` [(0, 0, 1)] the axis the fold (+) and the sweep (−) turn
                        # about, `fold_beat` [25] the beat added when folded; each world-aligned, X = 0 (mirrored by s)
                        'beat_axis': tuple(w.get('beat_axis', (0, 1, 0))), 'fold_axis': tuple(w.get('fold_axis', (0, 0, 1))),
                        'fold_beat': float(w.get('fold_beat', 25.0))})
    return out


def chains(P: dict) -> list[dict]:
    """Antennae (feathery or nubs) and other chains: {'name', 'kind', 'parent': 'head', 'points', 'stiff', 'heat',
    'mirror', 'spring'}."""
    out = []
    for m in P.get('chains') or []:
        kind = m.get('kind', 'antenna')
        if kind not in KINDS:
            raise ValueError(f"chain {m.get('name')}: kind {kind!r}, one of {', '.join(KINDS)}")
        nm0 = m.get('name', kind)
        twins = [(nm0 + 'L', 1), (nm0 + 'R', -1)] if m.get('mirror') else [(nm0, 1)]
        for nm, s in twins:
            pts = [mirror(p, s) for p in m['points']]
            out.append({'name': nm, 'kind': kind, 'parent': m.get('parent', 'head'), 'points': pts, 'side': s,
                        'stiff': float(m.get('stiff', 0.0)), 'heat': bool(m.get('heat', kind != 'antenna')),
                        'spring': bool(m.get('spring', True)), 'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)]})
    return out


def _style(P: dict, key: str, allowed: tuple, default: str) -> str:
    st = P.get(key, default)
    if st not in allowed:
        raise ValueError(f"{key} {st!r}: one of {', '.join(allowed)}")
    return st


def strike_style(P: dict) -> str:
    return _style(P, 'strike_style', STRIKE_STYLES, 'dust' if form_of(P) == 'hover' else 'roll')


def cast_style(P: dict) -> str:
    return _style(P, 'cast_style', CAST_STYLES, 'glow' if form_of(P) == 'hover' else 'spray')


def ko_style(P: dict) -> str:
    return _style(P, 'ko_style', KO_STYLES, 'flat' if form_of(P) == 'hover' else 'back')


def springs(P: dict) -> list[dict]:
    return [{'kind': m['kind'], 'chain': m['bones']} for m in chains(P) if m['spring']]


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → kind for CLIP_CALM: 'front', 'rear', each chain by name or kind, each wing (kind 'wing'),
    'leg' (leg<i>, shin<i>), 'shell' (the cocoon's halves)."""
    out = {'front': 'front', 'rear': 'rear', 'shell': 'shell'}
    for m in chains(P):
        out[m['name']] = m['kind']
    for w in wings(P):
        out[w['name']] = 'wing'
    for i in range(1, len(P.get('legs') or []) + 1):
        out[f'leg{i}'] = 'leg'
        out[f'shin{i}'] = 'leg'
    return out


def heatless(P: dict) -> set[str]:
    """The wings, the legs (tiny parts beside each other), the antennae (unless heat=True) and the cocoon's halves:
    the recipe skins them (U.segment_weights, U.chain_weights, U.rigid)."""
    out = {w['name'] for w in wings(P)} | {m['name'] for m in chains(P) if not m['heat']} | {'shell'}
    for i in range(1, len(P.get('legs') or []) + 1):
        out |= {f'leg{i}', f'shin{i}'}
    return out


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    hip = _v(P['hip'])
    hr = float(P['head_r'])
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk),
        BoneSpec('body', tuple(hip), tuple(hip + Vector((0, 0, 0.08 * sk))), 'root', radius=0.3 * sk),
    ]
    fp, fn = front_points(P), front_names(P)
    for i, nm in enumerate(fn):
        specs.append(BoneSpec(nm, tuple(fp[i]), tuple(fp[i + 1]), 'body' if i == 0 else fn[i - 1], connect=i > 0, radius=0.2 * sk))
    specs.append(BoneSpec('head', tuple(fp[-1]), tuple(head_tip(P)), fn[-1], connect=True, radius=max(0.15 * sk, 1.2 * hr)))
    jh, jt = jaw_points(P)
    specs.append(BoneSpec('jaw', tuple(jh), tuple(jt), 'head', radius=0.5 * hr))
    rp, rn = rear_points(P), rear_names(P)
    for i, nm in enumerate(rn):
        specs.append(BoneSpec(nm, tuple(rp[i]), tuple(rp[i + 1]), 'body' if i == 0 else rn[i - 1], connect=i > 0, radius=0.2 * sk))
    if not rn:
        # every look needs `hips` (the sidecar names it): a short one under the pivot
        specs.append(BoneSpec('hips', tuple(hip), tuple(hip + Vector((0, 0.06 * sk, 0))), 'body', radius=0.2 * sk))
    for lg in legs(P):
        specs.append(BoneSpec(lg['upper'], tuple(lg['hip']), tuple(lg['knee']), lg['parent'], radius=0.04 * sk))
        specs.append(BoneSpec(lg['lower'], tuple(lg['knee']), tuple(lg['foot']), lg['upper'], connect=True, radius=0.03 * sk))
    for w in wings(P):
        for i, nm in enumerate(w['bones']):
            specs.append(BoneSpec(nm, tuple(w['points'][i]), tuple(w['points'][i + 1]), w['parent'] if i == 0 else w['bones'][i - 1],
                                  connect=i > 0, radius=0.08 * sk))
    for sh in P.get('shell') or []:
        # the cocoon's halves, which open in `split`: {'name': 'L', 'head', 'tail', 'parent': 'hips'}
        specs.append(BoneSpec(f"shell.{sh['name']}", tuple(sh['head']), tuple(sh['tail']), sh.get('parent', 'hips'), radius=0.08 * sk))
        if sh.get('bulge'):
            # Nov 18 (Nibblegrub's cocoon; opt-in, absent = as before): a bulge bone under the half (its child, so it
            # opens with it), pushed out from inside in the wriggle while the seam stays shut
            bg = sh['bulge']
            specs.append(BoneSpec(f"shell.{sh['name']}.bulge", tuple(bg['head']), tuple(bg['tail']), f"shell.{sh['name']}",
                                  radius=0.05 * sk))
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'head'), radius=0.06 * sk))
    for m in chains(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.04 * sk))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """The game's seven (socket_paw_L / _R at the front legs' feet, or the first wing pair's tips on a hoverer, where a
    wing beat's dust starts), socket_core at the pivot, socket_<wing>, socket_<chain>, socket_<prop>."""
    sk = size_of(P)
    hc, hr = _v(P['head_c']), float(P['head_r'])
    hip = _v(P['hip'])
    _jh, jt = jaw_points(P)
    fp, rp, rn = front_points(P), rear_points(P), rear_names(P)
    out = {
        'socket_head': ('head', tuple(hc + Vector((0, 0, hr)))),
        'socket_crown': ('head', tuple(hc + Vector((0, 0, hr + 0.1 * sk)))),
        'socket_back': ('chest', tuple(fp[0].lerp(fp[1], 0.5) + Vector((0, 0, 0.12 * sk)))),
        'socket_mouth': ('jaw', tuple(jt)),
        'socket_core': ('body', tuple(hip)),
        'socket_tail': ((rn[-1], tuple(rp[-1])) if rn else ('hips', tuple(hip + Vector((0, 0.06 * sk, 0))))),
    }
    W = wings(P)
    front = {lg['tag']: lg for lg in legs(P) if lg['i'] == 1}
    for tag, s in SIDES:
        w = next((w for w in W if w['tag'] == tag), None)
        if form_of(P) == 'hover' and w:
            out[f'socket_paw_{tag}'] = (w['bones'][-1], tuple(w['points'][-1]))
        elif tag in front:
            out[f'socket_paw_{tag}'] = (front[tag]['lower'], tuple(front[tag]['foot']))
        else:
            out[f'socket_paw_{tag}'] = ('head', tuple(hc + Vector((s * 0.8 * hr, -0.3 * hr, -0.4 * hr))))
    for w in W:
        out[f"socket_{w['name']}"] = (w['bones'][-1], tuple(w['points'][-1]))
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
    FORM = form_of(P)
    HOVER = FORM == 'hover'
    style, cstyle, kstyle = strike_style(P), cast_style(P), ko_style(P)
    FRONT = [n for n in front_names(P) if has(n)]
    REAR = [n for n in rear_names(P) if has(n)]
    LEGS = [lg for lg in legs(P) if has(lg['upper'])]
    W = [w for w in wings(P) if has(w['bones'][0])]
    CH = chains(P)
    JAW = bool(P.get('jaw_open', False))
    CLOSED = P.get('blink_closed')
    hip = _v(P['hip'])
    HZ = hip.z
    ko_roll = float(P.get('ko_roll', {'back': 170.0, 'roll': KO_ROLL, 'flat': 0.0}[kstyle]))
    lift_tab = P.get('ko_lift') or []
    strike_yaw = float(P.get('strike_yaw', 0.0))
    hop_k = float(P.get('hop', 1.0))
    beat = float(P.get('beat', 3.0))           # a hoverer's wing beats a second
    flap_amp = float(P.get('flap', 30.0))      # degrees each side of its rest spread
    chew_k = float(P.get('chew', 1.0))         # Nibblegrub's cheeks are always chewing

    def mm(v: float) -> float:
        return v * sk

    # every joint the ground must not swallow, with the lowest it may go: a crawler's segments, head and feet keep
    # their rest heights where they lie (raised parts down to the body's radius); a hoverer only stays above ground
    rad = float(P.get('radius', 0.5 * HZ))
    JOINTS = [b for b in FRONT + REAR + ['head'] if has(b)] + [lg['lower'] for lg in LEGS]
    PROBES = [(b, rig.tail[b], min(rig.tail[b].z, rad) - mm(0.002) if not HOVER else mm(0.01)) for b in JOINTS if b != 'head']
    # head_tip is on the face's surface, and the head's ball must stay above ground too (a curl rolls it under):
    # `head_reach` (default head_r) is how far the head's skin reaches from head_c anywhere (big cheeks reach further)
    PROBES += [('head', rig.tail['head'], mm(0.01)), ('head', _v(P['head_c']), float(P.get('head_reach', P['head_r'])))]
    # and no antenna (or other chain) tip pokes into the ground
    PROBES += [(m['bones'][-1], _v(m['points'][-1]), 0.0) for m in chains(P) if has(m['bones'][-1])]
    # Nov 18 (Nibblegrub; opt-in, absent = as before): the recipe's own probes [(bone, (x, y, z), lowest z)], e.g. the
    # bottom of a big jowl or a broad foot's toe, which a pitch or a paddle would otherwise push into the ground
    PROBES += [(b, _v(p), float(fl)) for b, p, fl in (P.get('probes') or []) if has(b)]

    def ground(fr: Frame) -> None:
        """Lift the whole body (the pivot) by just enough that no joint goes below its floor (a curl, a lean, a rear)."""
        M = rig.fk(fr.rots(), fr.loc)
        need = max(fl - (M[b] @ p).z for b, p, fl in PROBES)
        if need > 0:
            fr.o('body', 0, 0, need)

    def clip(name: str, n: int, pose, loop: bool = True, hold: bool = False, root_speed: float = 0.0, step: int = 1,
             markers=(), faces=(), shut=None, guard: bool = True) -> None:
        if only and name not in only:
            return
        cb.begin(name, n, loop=loop, hold=hold, root_speed=root_speed)
        for f in K.frames_of(n, step):
            t = (f - 1) / n
            fr = pose(t)
            K.clip_bump(P, name, t, fr, sk)
            if guard and getattr(fr, 'guard', True):
                ground(fr)
            K.key_frame(cb, rig, f, fr)
        if shut is not None:
            K.eyes_shut(cb, CLOSED, n, shut, step)
        for mk, f in markers:
            cb.marker(mk, f)
        for f, face in faces:
            cb.face(f, face)
        made.append(cb.end())

    # ---- posing helpers (each keys the same bones on every frame of a clip)
    def body(fr: Frame, dz: float = 0.0, dy: float = 0.0, dx: float = 0.0, pitch: float = 0.0, roll: float = 0.0,
             yaw: float = 0.0, bob: float = 0.0, t: float = 0.0, rate: float = 1.0) -> None:
        """The pivot moved and turned (+pitch tips the front down); a hoverer bobs `bob` (× 2 cm)."""
        b = mm(0.02) * bob * A.wave(t, rate) if HOVER else 0.0
        fr.o('body', dx, dy, dz + b)
        fr.r('body', pitch, roll, yaw)

    def segs(fr: Frame, rise: float = 0.0, yaw: float = 0.0, tilt: float = 0.0, tail: float = 0.0, tail_yaw: float = 0.0,
             curl: float = 0.0, hump=None, look_pitch: float = 0.0, look_yaw: float = 0.0, look_tilt: float = 0.0) -> None:
        """The segment chain: the front rises `rise` degrees (spread along it), turns `yaw` and tilts; the rear lifts
        `tail` and swings `tail_yaw`; `curl` rolls both ends down and in (100: a ball); `hump` [per front and rear bone]
        adds a crawl's arch; the head looks (pitch + down)."""
        nf, nr = max(1, len(FRONT)), max(1, len(REAR))
        hf = hump[0] if hump else [0.0] * len(FRONT)
        hr_ = hump[1] if hump else [0.0] * len(REAR)
        for j, b in enumerate(FRONT):
            # a forward bone: −x lifts it; a curl (+x) rolls it down and under
            fr.r(b, -rise / nf + curl * 1.6 / nf - hf[j], tilt / nf, yaw / nf)
        for j, b in enumerate(REAR):
            # a backward bone: +x lifts it; a curl (−x) rolls it down and under
            fr.r(b, tail / nr - curl * 1.6 / nr + hr_[j], 0, tail_yaw / nr)
        fr.r('head', look_pitch + 0.4 * curl, look_tilt, look_yaw)

    def hump_wave(t: float, amp: float, cycles: float = 1.0, back: bool = False) -> tuple[list[float], list[float]]:
        """A crawl's arch running from the tail to the head (`back`: the other way): each segment lifts in turn."""
        bones = list(reversed(REAR)) + FRONT                  # tail end → head end
        n = max(1, len(bones))
        out = {}
        for j, b in enumerate(bones):
            ph = (j / n) * (-1 if back else 1)
            out[b] = amp * max(0.0, math.sin(2 * math.pi * (cycles * t - ph)))
        return [out[b] for b in FRONT], [out[b] for b in REAR]

    def legs_pose(fr: Frame, t: float, paddle: float = 0.0, rate: float = 2.0, tuck: float = 0.0, dangle: float = 0.0,
                  splay: float = 0.0) -> None:
        """The stubby legs: paddling `paddle` degrees in pairs (a walk), tucked up under the body, dangling (a hoverer's,
        swaying), splayed out (a ko)."""
        for lg in LEGS:
            ph = 0.5 * ((lg['i'] - 1 + (0 if lg['tag'] == 'L' else 1)) % 2)
            sw = paddle * math.sin(2 * math.pi * (rate * t + ph))
            lift = max(0.0, paddle * 0.8 * math.cos(2 * math.pi * (rate * t + ph)))
            dg = dangle * A.wave(t, rate, 0.15 * lg['i'])
            fr.r(lg['upper'], sw - tuck * 0.5 + dg, -lg['s'] * splay, 0)
            fr.r(lg['lower'], tuck + 0.6 * lift + 0.5 * dg, lg['s'] * 0.5 * splay, 0)

    def flutter(fr: Frame, t: float, rate: float | None = None, amp: float | None = None, bias: float = 0.0, fold: float = 0.0,
                sweep: float = 0.0, k: float = 1.0) -> None:
        """The moth wings: beating `rate` times a clip (`amp` degrees each side of `bias`, + = down), the hind pair a
        little behind; folded back over the body by `fold` (0..1) and swept forward by `sweep` degrees."""
        if not W:
            return
        r = rate if rate is not None else 1.0
        a = (amp if amp is not None else flap_amp) * k
        for w in W:
            s = w['s']
            ph = w['lag'] + (0.08 if w['base'] != W[0]['base'] else 0.0)
            f = bias + a * math.sin(2 * math.pi * (r * t - ph))
            for i, b in enumerate(w['bones']):
                fr.r(b, 0, 0, 0)
                if i == 0:
                    fr.turn(b, w['fold_axis'], s * (w['fold'] * fold - sweep))     # fold back about the vertical (+), sweep forward
                    fr.turn(b, w['beat_axis'], s * (f + w['fold_beat'] * fold))    # beat about the long axis (+ = down)
                else:
                    fr.turn(b, w['beat_axis'], s * 0.35 * a * math.sin(2 * math.pi * (r * t - ph - 0.12)))

    def chain_pose(fr: Frame, t: float, sway: float = 0.0, rate: float = 1.0, trail: float = 0.0, perk: float = 0.0) -> None:
        """Antennae spring and sway (`perk` lifts them, − droops), other chains sway and trail."""
        for m in CH:
            n = len(m['bones'])
            k = 1.0 - m['stiff']
            for i, b in enumerate(m['bones']):
                share = (0.6 + 0.8 * i / max(1, n - 1)) / n
                if m['kind'] == 'antenna':
                    fr.r(b, -perk * share * k + 0.5 * sway * share * k * A.wave(t - 0.1 * i, rate, 0.25), m['side'] * 0.3 * perk * share * k,
                         sway * share * k * A.wave(t - 0.1 * i, rate))
                else:
                    fr.r(b, trail * share * k, 0, sway * share * k * A.wave(t - 0.08 * i, rate))

    def jaw(fr: Frame, deg_: float) -> None:
        if JAW:
            fr.r('jaw', deg_, 0, 0)

    def chew(t: float, rate: float = 4.0) -> float:
        return 8.0 * chew_k * abs(math.sin(math.pi * rate * t))

    def ko_lift(t: float) -> float:
        return K.table_at(lift_tab, t)

    # the hover height a hoverer comes down from when it lands (sit, sleep): its lowest leg's foot to the ground
    LAND = (min((lg['foot'].z for lg in LEGS), default=HZ * 0.5) - mm(0.01)) if HOVER else 0.0

    def calm(fr: Frame, t: float, n: float, rise: float = 0.0, rate: float = 1.0, wings_k: float = 1.0, fold: float = 0.0,
             perk: float = 0.0, chew_on: bool = True) -> None:
        """What every calm clip shares: the legs (paddling a little, or dangling), the wings beating (a whole number
        of beats in the clip, `n` frames long), the antennae, the chewing."""
        legs_pose(fr, t, dangle=6.0 if HOVER and fold < 0.5 else 0.0, rate=rate, tuck=10.0 if HOVER and fold < 0.5 else 0.0)
        flutter(fr, t, rate=max(1, round(beat * n / A.FPS)) if fold < 0.5 else 1, k=wings_k * (1 - fold), fold=fold)
        chain_pose(fr, t, sway=8, rate=rate, perk=perk)
        jaw(fr, chew(t, 2 * round(2 * n / A.FPS)) if (chew_on and not HOVER) else 0.0)

    # ================================================================= ranch life
    def p_idle(t: float) -> Frame:
        fr = Frame()
        glance = A.pulse(t, 0.55, 0.85)
        body(fr, roll=1.5 * A.wave(t, 1.0), bob=1.0, t=t, rate=2.0)
        segs(fr, rise=(10 if not HOVER else 0) + 3 * A.wave(t, 2.0), yaw=8 * glance, look_yaw=16 * glance, look_tilt=5 * glance,
             tail=3 * (0.5 + 0.5 * A.wave(t, 1.0)), tail_yaw=4 * A.wave(t, 1.0))
        calm(fr, t, 120)
        return fr

    def p_idle_happy(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 3)
        body(fr, dz=mm(0.02) * b if HOVER else 0.0, roll=4 * A.wave(t, 2.0), bob=0.6, t=t, rate=3.0)
        segs(fr, rise=(24 if not HOVER else 6) + 8 * b, yaw=10 * A.wave(t, 2.0), tilt=6 * A.wave(t, 2.0), tail=8 * b, tail_yaw=10 * A.wave(t, 2.0),
             look_pitch=-8)
        calm(fr, t, 90, rate=3.0, perk=14)
        if not HOVER:
            jaw(fr, 14)                                     # a wide happy chew
        return fr

    def p_idle_tired(t: float) -> Frame:
        fr = Frame()
        yawn = A.pulse(t, 0.45, 0.72)
        body(fr, dz=-0.3 * LAND, pitch=4, bob=0.5, t=t)
        segs(fr, rise=-2 + 22 * yawn if not HOVER else 10 * yawn, look_pitch=14 - 26 * yawn)
        calm(fr, t, 150, wings_k=0.6, perk=-10, chew_on=False)
        jaw(fr, 30 * yawn)
        return fr

    def p_idle_sad(t: float) -> Frame:
        fr = Frame()
        body(fr, dz=-0.4 * LAND - mm(0.004) * (0.5 + 0.5 * A.wave(t, 1.0)), pitch=4 + 1.5 * A.wave(t, 1.0), bob=0.4, t=t)
        segs(fr, rise=-2 if not HOVER else -6, yaw=-8 + 4 * A.pulse(t, 0.5, 0.7), look_pitch=20, tail=2 * (0.5 + 0.5 * A.wave(t, 1.0)))
        calm(fr, t, 150, wings_k=0.4, perk=-18, chew_on=False)
        return fr

    def p_idle_sick(t: float) -> Frame:
        fr = Frame()
        w = A.wave(t, 1.0)
        shiver = A.wave(t, 9.0) * A.pulse(t, 0.25, 0.5)
        body(fr, dz=-0.25 * LAND, roll=5 * w + 1.5 * shiver, pitch=3, bob=0.5, t=t)
        segs(fr, rise=4 if not HOVER else 0, yaw=10 * w, tilt=6 * w, look_pitch=14, tail_yaw=-6 * w)
        calm(fr, t, 150, wings_k=0.6, perk=-8, chew_on=False)
        jaw(fr, 4)
        return fr

    def landed(fr: Frame, k: float) -> None:
        """A hoverer comes down to sit on the ground (k 0 → 1), its wings folding back over it."""
        body(fr, dz=-LAND * k, pitch=2 * k)

    def p_sleep(t: float) -> Frame:
        fr = Frame()
        b = A.wave(t, 1.0)
        if HOVER:
            landed(fr, 1.0)
            segs(fr, look_pitch=18, tail=-4)
        else:
            # curled into a loose crescent on the ground, the head tucked toward the tail
            body(fr, roll=0)
            segs(fr, yaw=50, tail_yaw=-50, look_pitch=10, look_yaw=20)
        fr.o('body', 0, 0, mm(0.008) * (0.5 + 0.5 * b))
        fr.r('body', 1.5 * b, 0, 0)                         # a slow breath (the body really moves)
        legs_pose(fr, t, tuck=20)
        flutter(fr, t, rate=1, amp=2, fold=1.0, k=0.0)
        chain_pose(fr, t, sway=1, perk=-20)
        jaw(fr, 0)
        return fr

    def p_eat(t: float) -> Frame:
        fr = Frame()
        dip = A.step_ease(t, 0.0, 0.2) * (1 - A.step_ease(t, 0.85, 1.0))
        munch = dip * abs(math.sin(t * 2 * math.pi * 3))
        body(fr, dz=-0.5 * LAND * dip, pitch=6 * dip, bob=0.4, t=t)
        segs(fr, rise=-6 * dip if not HOVER else 0, look_pitch=24 * dip)
        calm(fr, t, 60, wings_k=0.7, chew_on=False)
        jaw(fr, 18 * munch + 4)
        return fr

    def p_pet(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, roll=5, bob=0.6, t=t, rate=2.0)
        segs(fr, rise=(18 if not HOVER else 4) + 4 * b, tilt=14, look_tilt=14, look_pitch=-6, tail=6 * b, tail_yaw=8 * A.wave(t, 2.0))
        calm(fr, t, 75, rate=2.0, perk=10)
        return fr

    def p_look(t: float) -> Frame:
        fr = Frame()
        a = A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56))
        b = A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        yaw = 40 * a - 40 * b
        body(fr, yaw=0.3 * yaw, bob=1.0, t=t)
        segs(fr, rise=(12 if not HOVER else 0) + 6 * (a + b), yaw=0.5 * yaw, look_yaw=0.4 * yaw, tail_yaw=-0.2 * yaw)
        calm(fr, t, 90)
        return fr

    def hop_pose(fr: Frame, t: float, air: float, crouch: float, up: float, roll: float = 0.0, yaw: float = 0.0) -> None:
        body(fr, dz=up, pitch=-5 * air + 4 * crouch, roll=roll, yaw=yaw)
        segs(fr, rise=14 * air - 8 * crouch, tail=10 * air, curl=10 * crouch, look_pitch=-6 * air)
        legs_pose(fr, t, tuck=20 * air, dangle=0.0)
        flutter(fr, t, rate=2, amp=40, k=1.0)
        chain_pose(fr, t, sway=6, trail=-10 * air, perk=10 * air)

    def p_hop(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.28, 0.82)
        crouch = A.pulse(t, 0.0, 0.28) + 0.8 * A.pulse(t, 0.8, 1.0)
        hop_pose(fr, t, air, crouch, mm(0.12) * hop_k * air)
        jaw(fr, 10 * air)
        return fr

    def p_celebrate(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        land = A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)
        hop_pose(fr, t, air, land, mm(0.1) * hop_k * air, yaw=14 * A.wave(t, 1.0))
        jaw(fr, 16)
        return fr

    # ================================================================= moving
    # the crawl's travelling arch: a bump running along the body, each segment pitched to follow its slope (from the
    # bones' rest runs), so the body lies on the ground before and after it, as a caterpillar walks
    Y0 = rig.tail[REAR[-1]].y if REAR else hip.y
    Y1 = rig.tail[FRONT[-1]].y if FRONT else hip.y - mm(0.1)

    def u_of(p: Vector) -> float:
        return (Y0 - p.y) / max(Y0 - Y1, 1e-6)

    def arch(t: float, amp: float, cycles: int = 1, width: float = 0.5, back: bool = False):
        """A bump `amp` metres high, `width` (a share of the body) wide, running tail → head `cycles` times a clip
        (`back`: head → tail); it starts and ends off the body, so a loop has no seam. Returns (the pivot's lift, the
        front bones' extra lift, the rear bones'), degrees + = the bone's far end up."""
        c = ((cycles * t) % 1.0) * (1 + width) - width / 2
        if back:
            c = 1.0 - c

        def h(p: Vector) -> float:
            x = (u_of(p) - c) / width
            return amp * math.cos(math.pi * x) ** 2 if abs(x) < 0.5 else 0.0

        def chain(names: list[str]) -> list[float]:
            out, prev = [], 0.0
            for b in names:
                a_, e_ = rig.head[b], rig.tail[b]
                ang = math.degrees(math.atan2(h(e_) - h(a_), max(abs(e_.y - a_.y), 1e-6)))
                out.append(ang - prev)
                prev = ang
            return out

        return h(hip), chain(FRONT), chain(REAR)

    LEAN = {'walk': 8.0, 'run': 14.0, 'dash': 20.0, 'step_fwd': 8.0, 'step_back': -8.0, 'strafe': 0.0}
    ARCH = {'walk': 0.07, 'run': 0.09, 'dash': 0.11, 'step_fwd': 0.06, 'step_back': 0.06, 'strafe': 0.05}

    def speed_of(kind: str) -> float:
        return SPEED[kind] * sk

    def gait(t: float, kind: str, n: int, back: bool = False, side: int = 0, guard_w: float = 0.0) -> Frame:
        """A crawler humps along (the arch runs tail → head, `back` the other way; the legs paddle in pairs); a hoverer
        glides, leaning into it (`side`: sideways, banking), its wings beating a whole number of times a clip and its
        legs trailing."""
        fr = Frame()
        lean = LEAN[kind]
        if HOVER:
            body(fr, dx=0.0, pitch=lean, roll=side * 12.0 + 2.0 * A.wave(t, 1.0), yaw=-side * 6.0, bob=0.6, t=t, rate=2.0)
            segs(fr, rise=4 * guard_w, look_pitch=-0.6 * lean, tail=-0.3 * lean, tail_yaw=3 * A.wave(t, 1.0))
            legs_pose(fr, t, dangle=4.0, rate=2.0, tuck=10.0)
            for lg in LEGS:
                fr.r(lg['upper'], 1.2 * abs(lean) + 6, side * lg['s'] * 0.0, 0)          # the legs trail behind
            fast = 1.0 + 0.4 * (kind in ('run', 'dash'))
            flutter(fr, t, rate=max(1, round(beat * fast * n / A.FPS)), amp=flap_amp * fast, sweep=-0.3 * lean)
            chain_pose(fr, t, sway=4, rate=2.0, perk=-0.5 * abs(lean))
            jaw(fr, 0)
            return fr
        # Nov 18 (Nibblegrub; opt-in, absent = 1 as before): `arch` scales the crawl's travelling hump
        lift0, hf, hr_ = arch(t, mm(ARCH[kind]) * float(P.get('arch', 1.0)), back=back)
        body(fr, dz=lift0, roll=side * 5.0 + 2.0 * A.wave(t, 1.0), yaw=side * 8.0 + 2.0 * A.wave(t, 1.0))
        segs(fr, rise=8 + 8 * guard_w + 0.3 * lean, hump=(hf, hr_), look_pitch=-4 - 0.3 * lean, tail_yaw=-side * 6.0)
        legs_pose(fr, t, paddle=22.0 if kind != 'dash' else 30.0, rate=2.0)
        chain_pose(fr, t, sway=6, rate=2.0, perk=6 + 0.5 * lean)
        jaw(fr, chew(t, 4))
        return fr

    def gait_marks(n: int) -> list:
        return [('step', 1), ('step', 1 + n // 2)]

    def p_strafe(t: float, side: int) -> Frame:
        return gait(t, 'strafe', 24, side=side, guard_w=1.0)

    def p_sidestep(t: float, side: int) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.15, 0.92)
        crouch = A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        hop_pose(fr, t, air, crouch, mm(0.06) * air, roll=side * (20 if HOVER else 12) * air)
        jaw(fr, 0)
        return fr

    # ================================================================= scenes
    def sit_pose(fr: Frame, t: float, k: float, fan: float = 0.0) -> None:
        """A crawler rears up its front (the head looking ahead, the front legs dangling); a hoverer lands, its wings
        folding back over its body like a roof."""
        if HOVER:
            landed(fr, k)
            segs(fr, look_pitch=6 * k)
            legs_pose(fr, t, splay=10 * k, tuck=10 * (1 - k))
            flutter(fr, t, rate=1, fold=0.75 * k, k=(1 - k) + fan)        # `fan`: a slow open-and-close at rest
        else:
            body(fr)
            segs(fr, rise=46 * k, look_pitch=34 * k)
            legs_pose(fr, t, tuck=14 * k)

    def p_sit_down(t: float) -> Frame:
        fr = Frame()
        k = C.ease_in_out(t)
        sit_pose(fr, t, k)
        chain_pose(fr, t, sway=3, perk=-6 * k)
        jaw(fr, 0)
        return fr

    def p_sit(t: float) -> Frame:
        fr = Frame()
        sit_pose(fr, t, 1.0, fan=0.12)
        g = A.pulse(t, 0.5, 0.75)
        fr.o('body', 0, 0, mm(0.003) * (0.5 + 0.5 * A.wave(t, 2.0)))
        fr.r('body', 1.0 * A.wave(t, 1.0), 0, 0)
        fr.r('head', 3 * A.wave(t, 1.0), 4 * g, 20 * g)
        chain_pose(fr, t, sway=4, rate=2.0, perk=-6)
        jaw(fr, chew(t, 8) if not HOVER else 0.0)
        return fr

    def p_dizzy(t: float) -> Frame:
        fr = Frame()
        c, s_ = math.cos(t * 4 * math.pi), math.sin(t * 4 * math.pi)
        body(fr, dz=-0.3 * LAND, roll=8 * s_, pitch=4 * c, yaw=6 * s_, bob=0.5, t=t, rate=2.0)
        segs(fr, rise=(10 if not HOVER else 0) + 6 * c, yaw=18 * s_, tail_yaw=14 * s_, look_pitch=12 * c, look_yaw=20 * s_, look_tilt=16 * s_)
        legs_pose(fr, t, paddle=10, rate=2.0, dangle=8.0 if HOVER else 0.0)
        flutter(fr, t, rate=4, amp=flap_amp * 0.8, bias=6 * s_)
        chain_pose(fr, t, sway=18, rate=2.0, perk=-6)
        jaw(fr, 12)
        return fr

    # ================================================================= battle
    def p_battle_idle(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, dz=mm(0.012) * b if HOVER else 0.0, pitch=3, yaw=-4, bob=0.0)
        segs(fr, rise=(22 if not HOVER else 4) + 5 * b, look_pitch=-6, tail=4 * b)
        legs_pose(fr, t, paddle=8 if not HOVER else 0.0, rate=2.0, dangle=6.0 if HOVER else 0.0, tuck=10.0 if HOVER else 0.0)
        # a hoverer's wings beat strongly (they read from the 35-degree camera), a crawler's antennae perk
        flutter(fr, t, rate=max(1, round(beat * 40 / A.FPS)), amp=flap_amp * 1.15)
        chain_pose(fr, t, sway=8, rate=2.0, perk=12)
        jaw(fr, chew(t, 4))
        return fr

    def p_hit(t: float) -> Frame:
        k = A.pulse(t, 0.0, 0.8)
        fr = Frame()
        body(fr, dy=mm(0.05) * k, pitch=-12 * k if HOVER else -4 * k, roll=-4 * k, yaw=-8 * k)
        segs(fr, rise=14 * k, look_pitch=-20 * k, look_yaw=-12 * k, tail=8 * k)
        legs_pose(fr, t, splay=14 * k, dangle=4.0 if HOVER else 0.0)
        flutter(fr, t, rate=1, amp=8, bias=-24 * k, sweep=-10 * k)              # the wings fly up and back
        chain_pose(fr, t, sway=10, perk=-20 * k)
        jaw(fr, 18 * k)
        K.add_bones(P, 'hit_bones', fr, k)
        return fr

    def p_hit_heavy(t: float) -> Frame:
        k = A.pulse(t, 0.0, 0.62)
        fr = Frame()
        body(fr, dy=mm(0.14) * k, dz=mm(0.06) * k, pitch=(-32 if HOVER else -10) * k, roll=-12 * k, yaw=-10 * k)
        # both ends flung up (the body bent backward), the legs splayed
        segs(fr, rise=30 * k, tail=22 * k, look_pitch=-26 * k, look_yaw=-16 * k)
        legs_pose(fr, t, splay=24 * k, tuck=-10 * k)
        flutter(fr, t, rate=1, amp=10, bias=-34 * k, sweep=-16 * k)
        chain_pose(fr, t, sway=16, perk=-30 * k)
        jaw(fr, 22 * k)
        K.add_bones(P, 'hit_heavy_bones', fr, k)
        return fr

    def flat_wings() -> float:
        """The beat (degrees, + = down) that lays a 'flat' ko's first wings on the ground, their tips 1 cm up, once the
        body lies at body_width."""
        if not W:
            return 0.0
        w = next(w for w in W if w['s'] > 0)
        root, tip = w['points'][0], w['points'][-1]
        v = tip - root
        target = mm(0.01) - (root.z - (HZ - float(P.get('body_width', 0.5 * HZ))))
        lo, hi = -40.0, 60.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            z = -math.sin(math.radians(mid)) * v.x + math.cos(math.radians(mid)) * v.z
            lo, hi = (mid, hi) if z > target else (lo, mid)
        return 0.5 * (lo + hi)

    def p_ko(t: float) -> Frame:
        """It wobbles, then falls: onto its back, legs up ('back', a crawler's), onto its side ('roll'), or flat on its
        belly, wings spread on the ground ('flat', a hoverer's: it drifts down). The pivot lies `body_width` up (the
        build settles it); no ground guard here (the settle lifts the fall)."""
        fr = Frame()
        wob = (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = A.step_ease(t, 0.35, 0.85)
        w_ = 8 * math.sin(t * 2 * math.pi * 2.5) * wob
        rd = (0.5 * w_, w_, 0.0) if kstyle == 'flat' else (0.0, -ko_roll * fall + w_, 0.0)
        bw = float(P.get('body_width', 0.5 * HZ))
        h = HZ * (1 - fall) + bw * fall + ko_lift(t)
        fr.r('root', *rd)
        fr.o('body', *K.lay_offset(rd, hip, Vector((0, hip.y, h))))
        fr.r('body', 0, 0, 0)
        if kstyle == 'back':
            # a bug on its back: the ends curl up a little and the legs wiggle, then go still
            segs(fr, curl=22 * fall, look_pitch=-10 * fall)
            legs_pose(fr, t, paddle=26 * A.pulse(t, 0.55, 1.0), rate=3.0, splay=10 * fall)
            flutter(fr, t, rate=1, amp=0, fold=fall, k=0.0)
        elif kstyle == 'roll':
            segs(fr, curl=30 * fall, look_pitch=12 * fall)
            legs_pose(fr, t, tuck=20 * fall)
            flutter(fr, t, rate=1, amp=0, fold=fall, k=0.0)
        else:
            segs(fr, look_pitch=14 * fall, tail=-2 * fall)
            legs_pose(fr, t, splay=60 * fall, tuck=20 * fall)
            # Nov 18 (Velvesper; opt-in, absent = as before): `ko_wing_bias` (degrees) replaces the measured beat for
            # wings that don't beat about the level long axis (an upright hoverer lying back on its spread wings)
            kwb = P.get('ko_wing_bias')
            flutter(fr, t, rate=1, amp=flap_amp * (1 - fall), bias=(flat_wings() if kwb is None else float(kwb)) * fall)
        chain_pose(fr, t, sway=2 * (1 - fall), perk=-24 * fall)
        jaw(fr, 16 * fall)
        K.add_bones(P, 'ko_bones', fr, fall)
        K.scale_bones(P, 'ko_scale', fr, A.step_ease(t, 0.3, 0.75))
        return fr

    def p_win(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.04, 0.34)
        land = A.pulse(t, 0.32, 0.42)
        proud = A.step_ease(t, 0.3, 0.45) * (1 - A.step_ease(t, 0.86, 1.0))      # back to the start: win loops
        if HOVER:
            # up in a burst of beats, then a proud hover with the wings held high
            body(fr, dz=mm(0.14) * hop_k * air, pitch=-6 * air - 4 * proud, bob=0.5, t=t, rate=2.0)
            segs(fr, rise=8 * proud, look_pitch=-14 * proud, tail=6 * air)
            legs_pose(fr, t, dangle=6.0, rate=2.0, tuck=10.0 + 10 * air)
            flutter(fr, t, rate=6, amp=flap_amp * (1 + 0.3 * air), bias=-14 * proud)
            chain_pose(fr, t, sway=12, rate=2.0, perk=24 * max(air, proud))
        else:
            hop_pose(fr, t, air, land, mm(0.1) * hop_k * air)
            segs(fr, rise=30 * proud, look_pitch=-18 * proud)              # then rears up, proud
        jaw(fr, 18 * proud + 8 * air)
        K.add_bones(P, 'win_bones', fr, max(air, A.pulse(t, 0.42, 0.86)))
        K.scale_bones(P, 'win_scale', fr, air)
        return fr

    # ---- strike: 24 frames, impact at 13 (t = 0.5) in every style
    def p_strike(t: float) -> Frame:
        ant = A.pulse(t, 0.0, 0.42)
        go = A.pulse(t, 0.28, 0.72)
        fr = Frame()
        wing = dict(rate=max(1, round(beat * 24 / A.FPS)), amp=flap_amp * 0.8)
        perk = 30 * go - 8 * ant
        if style == 'roll':
            # curls into a ball and rolls into the target (Nibblegrub's tackle): the ball tips forward on the impact
            ball = A.step_ease(t, 0.04, 0.3) * (1 - A.step_ease(t, 0.72, 0.96))
            body(fr, dy=mm(0.03) * ant - mm(0.25) * go, pitch=-8 * ant + 70 * go, yaw=strike_yaw * go)
            # Nov 18 (Nibblegrub; opt-in, absent = 100 as before): `roll_curl`, how far the ball curls (a fat body folds
            # into itself at a full curl)
            segs(fr, curl=float(P.get('roll_curl', 100.0)) * ball)
            # Nov 18 (Nibblegrub; opt-in, absent = as before): `roll_bones` {bone: (x, y, z) degrees} added × the curl
            # (the ball's own shape: a lighter front curl, the head lifted to look out of it, a deeper rear curl)
            K.add_bones(P, 'roll_bones', fr, ball)
            legs_pose(fr, t, tuck=30 * ball)
            perk = -50 * ball                                    # the antennae laid back along the ball
            jaw(fr, 0)
        elif style == 'chomp':
            # rears back, mouth wide, then lunges down and snaps shut on the impact
            body(fr, dy=mm(0.04) * ant - mm(0.12) * go, pitch=-6 * ant + 10 * go, yaw=strike_yaw * go)
            segs(fr, rise=(26 if not HOVER else 10) * ant - 14 * go, look_pitch=-16 * ant + 18 * go, tail=6 * ant)
            legs_pose(fr, t, paddle=10 * ant, rate=2.0, dangle=4.0 if HOVER else 0.0)
            jaw(fr, 30 * A.pulse(t, 0.22, 0.52))
        elif style == 'spray':
            # rears, the head drawn back, then spits forward on the impact (from socket_mouth)
            body(fr, dy=mm(0.03) * ant - mm(0.04) * go, pitch=-4 * ant + 6 * go, yaw=strike_yaw * go)
            segs(fr, rise=30 * ant + 10 * go, look_pitch=-20 * ant + 22 * go)
            legs_pose(fr, t, tuck=10 * ant)
            jaw(fr, 26 * A.pulse(t, 0.4, 0.78))
        elif style == 'dust':
            # the wings rise high and back, then sweep down and forward in one great beat: the dust leaves the wing tips
            # (socket_paw) on the impact (Moth Dust)
            body(fr, dy=mm(0.03) * ant - mm(0.06) * go, dz=mm(0.03) * ant, pitch=-8 * ant + 12 * go, yaw=strike_yaw * go)
            segs(fr, look_pitch=-10 * ant + 10 * go, tail=6 * ant)
            legs_pose(fr, t, dangle=4.0, tuck=10.0)
            wing = dict(rate=1, amp=0.0, bias=-38 * ant + 42 * go, sweep=-22 * ant + 36 * go)
            jaw(fr, 0)
        elif style == 'flutter':
            # darts forward on a flurry of beats and bumps the target
            body(fr, dy=mm(0.03) * ant - mm(0.22) * go, pitch=-6 * ant + 20 * go, yaw=strike_yaw * go)
            segs(fr, look_pitch=-10 * go, tail=-8 * go)
            legs_pose(fr, t, dangle=4.0, tuck=10.0 + 10 * go)
            wing = dict(rate=4, amp=flap_amp * 1.2, sweep=-10 * go)
            jaw(fr, 10 * go)
        else:      # 'beam'
            # braces, the front lifting and the antennae flaring, the head thrust at the impact (from socket_mouth or
            # socket_head; the wings held wide)
            body(fr, dy=mm(0.03) * ant - mm(0.02) * go, pitch=-6 * ant + 4 * go, yaw=strike_yaw * go)
            segs(fr, rise=16 * ant + 8 * go, look_pitch=-8 * ant + 12 * go)
            legs_pose(fr, t, tuck=8 * ant, dangle=4.0 if HOVER else 0.0)
            wing = dict(rate=1, amp=6.0, bias=-18 * max(ant, go))
            jaw(fr, 22 * go)
        flutter(fr, t, **wing)
        chain_pose(fr, t, sway=6, perk=perk)
        K.add_bones(P, 'strike_bones', fr, go)
        K.add_bones(P, 'strike_windup_bones', fr, ant)
        return fr

    # ---- cast: 36 frames, release at 20
    def p_cast(t: float) -> Frame:
        up = A.step_ease(t, 0.0, 0.32) * (1 - A.step_ease(t, 0.72, 1.0))
        rel = A.pulse(t, 0.48, 0.72)
        fr = Frame()
        if cstyle == 'spray':
            # rears up high, the head drawn back, then thrusts forward at `release` (a spray from socket_mouth)
            body(fr, pitch=-4 * up + 6 * rel, dz=mm(0.02) * up if HOVER else 0.0)
            segs(fr, rise=(40 if not HOVER else 12) * up - 10 * rel, look_pitch=-20 * up + 30 * rel)
            legs_pose(fr, t, tuck=12 * up, dangle=4.0 if HOVER else 0.0)
            flutter(fr, t, rate=max(1, round(beat * 36 / A.FPS)), amp=flap_amp * 0.8)
            jaw(fr, 10 * up + 24 * rel)
        elif cstyle == 'glow':
            # rises with the wings spread wide and slow, the antennae raised; one great downbeat at `release` (the glow
            # leaves socket_core)
            body(fr, dz=mm(0.06) * up, pitch=-6 * up + 8 * rel, bob=0.3, t=t)
            segs(fr, rise=8 * up, look_pitch=-12 * up + 8 * rel, tail=-4 * up)
            legs_pose(fr, t, dangle=3.0 if HOVER else 0.0, tuck=(10.0 if HOVER else 0.0) + 10 * up)
            flutter(fr, t, rate=1, amp=flap_amp * (1 - up) * 0.5, bias=-26 * up + 50 * rel, sweep=-10 * up + 14 * rel)
            jaw(fr, 10 * rel)
        else:      # 'dust'
            # beats hard, faster and faster, sweeping forward at `release` (the dust leaves the wing tips)
            body(fr, dz=mm(0.03) * up, pitch=-6 * up + 10 * rel)
            segs(fr, rise=6 * up, look_pitch=-8 * up + 8 * rel)
            legs_pose(fr, t, dangle=4.0 if HOVER else 0.0, tuck=10.0 if HOVER else 0.0)
            flutter(fr, t, rate=5, amp=flap_amp * (1 + 0.3 * up), sweep=30 * rel)
            jaw(fr, 8 * rel)
        chain_pose(fr, t, sway=8, rate=2.0, perk=24 * up)
        return fr

    def p_shove(t: float) -> Frame:
        ant = A.pulse(t, 0.0, 0.32)
        go = A.pulse(t, 0.2, 0.55)
        fr = Frame()
        if HOVER:
            # a shoulder-check: banks into it with the wings flung up
            body(fr, dy=mm(0.03) * ant - mm(0.14) * go, roll=20 * go, pitch=-4 * ant + 8 * go, yaw=strike_yaw * go)
            segs(fr, look_pitch=-6 * ant + 6 * go)
            legs_pose(fr, t, dangle=4.0, tuck=10.0)
            flutter(fr, t, rate=2, amp=flap_amp * 0.6, bias=-22 * go)
        else:
            # a head-butt: the front low, the head down into it
            body(fr, dy=mm(0.03) * ant - mm(0.12) * go, pitch=-4 * ant + 8 * go, yaw=strike_yaw * go)
            segs(fr, rise=12 * ant - 10 * go, look_pitch=-8 * ant + 22 * go)
            legs_pose(fr, t, paddle=14 * go, rate=2.0)
        chain_pose(fr, t, sway=4, perk=-12 * go)
        jaw(fr, 0)
        return fr

    # ================================================================= the cocoon (form 'cocoon': COCOON_CLIPS only)
    # It hangs from its silk at the pivot (`hip`, at the top); the front chain runs down through it and `head` is its
    # lowest piece. It never battles, walks or sits; nothing here touches the ground.
    SHELL = [f"shell.{sh['name']}" for sh in (P.get('shell') or []) if has(f"shell.{sh['name']}")]
    # Nov 18 (opt-in): the halves' bulge bones {bone: degrees}: still in idle and split, pushed out in
    # the wriggle (the left on the first and third push, the right on the second)
    BULGE = {f"shell.{sh['name']}.bulge": float(sh['bulge'].get('deg', 8.0)) for sh in (P.get('shell') or [])
             if sh.get('bulge') and has(f"shell.{sh['name']}.bulge")}

    def shell_side(b: str) -> int:
        return 1 if rig.tail[b].x + rig.head[b].x >= 0 else -1

    def cocoon(fr: Frame, t: float, swing: float, twist: float, open_: float = 0.0, rate: float = 1.0) -> None:
        """A slow pendulum from the hang point, the silk turning a little, something stirring inside; `open_` (0..1)
        swings the shell halves out from their hinges."""
        fr.o('body', 0, 0, 0)
        fr.r('body', swing * A.wave(t, rate), 0.6 * swing * A.wave(t, rate, 0.25), twist * A.wave(t, rate, 0.1))
        for j, b in enumerate(FRONT):
            fr.r(b, 0.4 * swing * A.wave(t, rate, -0.08 * (j + 1)), 0, 0.5 * twist * A.wave(t, rate, 0.05 * j))
        fr.r('head', 0.3 * swing * A.wave(t, rate, -0.2), 0, 0)
        for b in SHELL:
            fr.r(b, 0, -shell_side(b) * 72 * open_, 0)
        for b in BULGE:
            fr.r(b, 0, 0, 0)
        for b in REAR:
            fr.r(b, 0, 0, 0)
        chain_pose(fr, t, sway=2, rate=rate)

    def c_idle(t: float) -> Frame:
        fr = Frame()
        cocoon(fr, t, swing=3.0, twist=4.0)
        return fr

    def c_wriggle(t: float) -> Frame:
        """Twitches from inside: three pushes, then still again (it loops)."""
        fr = Frame()
        tw = A.pulse(t, 0.08, 0.28) + A.pulse(t, 0.42, 0.58) + 0.7 * A.pulse(t, 0.7, 0.88)
        cocoon(fr, t, swing=2.0, twist=3.0)
        jolt = tw * math.sin(t * 2 * math.pi * 6)
        fr.r('body', 3 * jolt, 4 * jolt, 0)
        for j, b in enumerate(FRONT):
            fr.r(b, 2 * jolt, 0, 8 * tw * math.sin(t * 2 * math.pi * 6 + j))
        fr.r('head', 6 * jolt, 0, 6 * tw)
        for b in SHELL:
            fr.r(b, 0, -shell_side(b) * 4 * tw, 0)
        for b, deg in BULGE.items():
            push = (A.pulse(t, 0.08, 0.28) + 0.7 * A.pulse(t, 0.7, 0.88)) if shell_side(b) > 0 else A.pulse(t, 0.42, 0.58)
            fr.r(b, -deg * push * (0.75 + 0.25 * abs(math.sin(t * 2 * math.pi * 6))), 0, 0)
        return fr

    def c_split(t: float) -> Frame:
        """The shaking builds, then the shell halves burst open at `split` (the new monster appears in the game's
        light, not in this file) and hang open."""
        fr = Frame()
        shake = A.step_ease(t, 0.0, 0.5) * (1 - A.step_ease(t, 0.58, 0.7))
        op = A.step_ease(t, 0.56, 0.8)
        cocoon(fr, t, swing=2.0 * (1 - op), twist=3.0 * (1 - op), open_=op)
        j = shake * math.sin(t * 2 * math.pi * 9)
        fr.r('body', 4 * j + 6 * A.pulse(t, 0.56, 0.75), 3 * j, 0)
        fr.r('head', 5 * j, 0, 4 * j)
        return fr

    if FORM == 'cocoon':
        clip('idle', 120, c_idle, step=2, guard=False)
        clip('wriggle', 60, c_wriggle, guard=False)
        clip('split', 48, c_split, loop=False, hold=True, markers=[('split', 1 + int(round(0.6 * 48)))], guard=False)
        return made

    # ================================================================= the clip list (the same contract as every plan)
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
    clip('walk', 30, lambda t: gait(t, 'walk', 30), root_speed=speed_of('walk'), markers=gait_marks(30))
    clip('run', 20, lambda t: gait(t, 'run', 20), root_speed=speed_of('run'), markers=gait_marks(20))
    clip('sit_down', 24, p_sit_down, loop=False, hold=True)
    clip('sit', 120, p_sit, step=2)
    clip('dizzy', 60, p_dizzy, faces=[(1, 'dizzy')])
    clip('battle_idle', 40, p_battle_idle)
    clip('step_fwd', 24, lambda t: gait(t, 'step_fwd', 24, guard_w=1.0), root_speed=speed_of('step_fwd'), markers=gait_marks(24))
    clip('step_back', 24, lambda t: gait(t, 'step_back', 24, back=True, guard_w=1.0), root_speed=speed_of('step_back'),
         markers=gait_marks(24))
    clip('dash', 20, lambda t: gait(t, 'dash', 20), root_speed=speed_of('dash'), markers=gait_marks(20))
    clip('strike', 24, p_strike, loop=False, markers=[('impact', 13)], faces=[(1, 'angry'), (20, 'neutral')])
    clip('cast', 36, p_cast, loop=False, markers=[('release', 20)], faces=[(1, 'strain'), (28, 'neutral')])
    clip('shove', 24, p_shove, loop=False, markers=[('impact', 10)])
    clip('hit', 15, p_hit, loop=False, faces=[(1, 'surprised'), (12, 'neutral')], shut=lambda t: 0.85 * A.pulse(t, 0.0, 0.7))
    clip('hit_heavy', 24, p_hit_heavy, loop=False, faces=[(1, 'strain'), (18, 'neutral')], shut=lambda t: 0.9 * A.pulse(t, 0.0, 0.75))
    clip('ko', 36, p_ko, loop=False, hold=True, faces=[(1, 'strain'), (20, 'dizzy')],
         shut=lambda t: max(0.8 * A.pulse(t, 0.0, 0.3), A.step_ease(t, 0.35, 0.6)), guard=False)
    clip('win', 60, p_win, markers=[('land', 22)], faces=[(1, 'happy')])
    clip('strafe_l', 24, lambda t: p_strafe(t, 1), root_speed=speed_of('strafe'), markers=[('step', 1), ('step', 13)])
    clip('strafe_r', 24, lambda t: p_strafe(t, -1), root_speed=speed_of('strafe'), markers=[('step', 1), ('step', 13)])
    clip('sidestep_l', 8, lambda t: p_sidestep(t, 1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    clip('sidestep_r', 8, lambda t: p_sidestep(t, -1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    return made
