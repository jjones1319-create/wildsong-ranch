"""The floater body plan (ART_2_PLAN §4, batch 4): rig template, sockets, springs and the clip generators for monsters
that hover instead of standing: Wishlume, Ashwraith, Zipwisp, Mirrorkin, Frostlance.

A recipe selects it with `PLAN = 'floater'` (tools/blender/monsters/breeds/RECIPE.md, "Floater plan"). The same build
(build_ultra.py) drives it as the quadruped and the biped: rig_specs, sockets, springs, chain_groups, heatless,
make_clips, STAR_CLIPS, MOVE_CLIPS, ROOT_DIRS and KO_ROLL (ko drifts down and lies on its side at `body_width`, which
the build measures and settles, lifting any sinking frame with `ko_lift`).

Space: metres; the monster faces −Y, Z is up, +X is its left. The rest pose is modelled hovering. From rig_p() (`P`):
  hip                  the hover point: the body's centre, where it bobs, tilts, squashes and turns (the `hover` bone)
  chest                the top of the squash chain (a lantern's crown; the snout for a swimmer like Frostlance)
  body_base            its bottom (or a swimmer's rear) [the mirror of `chest` through `hip`]
  head_c, head_r       the face's centre and size (the eyes, the jaw, the review framing)
The squash chain is `hips` (base → ⅓), `chest` (⅓ → ⅔), `head` (⅔ → top), parented to `hover` (parented to `root`).
Options (RECIPE.md): size_k, jaw, arms (little two-bone arms), hands (floating hands), chains (tassels, wisps, tails,
a handle, a hood, ribbons, fins: each a spring chain with its own kind), props, bob, jitter, sway, sink,
strike_style, pulse_tilt, body_width, ko_lift.

Clips play the floater way (ART_2_PLAN §5): it hovers with a gentle bob instead of standing; walk and run are glides
(leaning in, the chains streaming back); sit settles low; sleep sinks almost to the ground and shuts its eyes (any
dimming of a glow is the runtime's); ko drifts down and lies on its side; a hit knocks it back through the air.
Rotations are world-aligned degrees relative to the parent at rest (lib.anim.ClipBuilder.rot): +x tips an upright body
forward (and lifts a backward-pointing chain, swings a hanging one back), +z turns toward the monster's left, +y tilts
toward its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector

from lib import anim as A
from lib import common as C
from lib.rig import BoneSpec

PLAN = 'floater'
SIDES = (('L', 1), ('R', -1))
KO_ROLL = 80.0              # degrees the body rolls onto its right side in ko (build_ultra measures body_width at it)
STRIKE_STYLES = ('pulse', 'ram', 'swipe', 'gust', 'spin', 'lash')
SPRINGS = []                # Art 2.0 compatibility only; the Ultra build calls springs(P)
# chain kinds: trailing ones hang and stream behind; the others swing (tail), flap (fin) or barely move (handle)
TRAILING = ('tassel', 'wisp', 'ribbon', 'hood', 'cape')
KINDS = TRAILING + ('tail', 'fin', 'handle')
HEATLESS_KINDS = ('tassel', 'wisp', 'ribbon', 'hood', 'cape', 'handle')

SIDESTEP_DISTANCE = 1.4 * 100 / 150      # the same arena distance as every other plan
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}
STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']
# glide speeds (model metres per second at Puddlepup's size; × size_k)
SPEED = {'walk': 0.25, 'run': 0.8, 'dash': 1.15, 'step_fwd': 0.25, 'step_back': 0.2, 'strafe': 0.25}


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def _v(p) -> Vector:
    return Vector(p)


def _mirror(p, s: int) -> Vector:
    v = Vector(p)
    return Vector((v.x * s, v.y, v.z))


def base_of(P: dict) -> Vector:
    if P.get('body_base'):
        return _v(P['body_base'])
    return 2 * _v(P['hip']) - _v(P['chest'])


def squash_points(P: dict) -> list[Vector]:
    b, t = base_of(P), _v(P['chest'])
    return [b, b.lerp(t, 1 / 3), b.lerp(t, 2 / 3), t]


def jaw_points(P: dict) -> tuple[Vector, Vector] | None:
    if not P.get('jaw'):
        return None
    return _v(P['jaw']['head']), _v(P['jaw']['tail'])


def chains(P: dict) -> list[dict]:
    """The spring chains: each {'name', 'kind', 'parent', 'points', 'stiff' 0..1, 'axis' 'z' or 'x', 'heat', 'mirror'};
    `mirror` True adds the right-side twin (name + '.R'-style: <name>R from <name>L, or <name>_R)."""
    out = []
    for m in P.get('chains') or []:
        kind = m.get('kind', 'tassel')
        if kind not in KINDS:
            raise ValueError(f"chain {m.get('name')}: kind {kind!r}, one of {', '.join(KINDS)}")
        twins = [(m.get('name', kind), 1)]
        if m.get('mirror'):
            nm = m.get('name', kind)
            twins = [(nm + 'L', 1), (nm + 'R', -1)]
        for nm, s in twins:
            pts = [_mirror(p, s) for p in m['points']]
            if len(pts) < 2:
                raise ValueError(f'chain {nm}: needs at least 2 points')
            out.append({'name': nm, 'kind': kind, 'parent': m.get('parent', 'hips'), 'points': pts, 'side': s,
                        'stiff': float(m.get('stiff', 0.8 if kind == 'handle' else 0.0)), 'axis': m.get('axis', 'z'),
                        'heat': bool(m.get('heat', kind not in HEATLESS_KINDS)),
                        'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)],
                        'length': sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))})
    return out


def strike_style(P: dict) -> str:
    st = P.get('strike_style', 'pulse')
    if st not in STRIKE_STYLES:
        raise ValueError(f"strike_style {st!r}: one of {', '.join(STRIKE_STYLES)}")
    return st


def springs(P: dict) -> list[dict]:
    """Every chain, by its kind (the runtime may drive the trailing ones with springs)."""
    return [{'kind': m['kind'], 'chain': m['bones']} for m in chains(P)]


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → kind, for a recipe's CLIP_CALM (each chain by its name or its kind; 'hand' for floating hands,
    'arm' for little arms)."""
    out = {m['name']: m['kind'] for m in chains(P)}
    if P.get('hands'):
        out['hand'] = 'hand'
    if P.get('arms'):
        out['upperarm'] = 'arm'
        out['forearm'] = 'arm'
    return out


def heatless(P: dict) -> set[str]:
    """Chains whose bones take no heat weights on the body (tassels, wisps, ribbons, a hood, a cape, a handle, unless
    the chain says heat=True); floating hands too (skin them with U.rigid)."""
    out = {m['name'] for m in chains(P) if not m['heat']}
    if P.get('hands'):
        out.add('hand')
    return out


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    hip = _v(P['hip'])
    sq = squash_points(P)
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk),
        BoneSpec('hover', tuple(hip), tuple(hip + Vector((0, 0, 0.1 * sk))), 'root', radius=0.3 * sk),
        BoneSpec('hips', tuple(sq[0]), tuple(sq[1]), 'hover', radius=0.3 * sk),
        BoneSpec('chest', tuple(sq[1]), tuple(sq[2]), 'hips', connect=True, radius=0.3 * sk),
        BoneSpec('head', tuple(sq[2]), tuple(sq[3]), 'chest', connect=True, radius=max(0.3 * sk, 1.2 * P['head_r'])),
    ]
    jp = jaw_points(P)
    specs.append(BoneSpec('jaw', tuple(jp[0]) if jp else tuple(_v(P['head_c']) + Vector((0, -0.6 * P['head_r'], -0.4 * P['head_r']))),
                          tuple(jp[1]) if jp else tuple(_v(P['head_c']) + Vector((0, -0.95 * P['head_r'], -0.55 * P['head_r']))),
                          'head', radius=0.5 * P['head_r']))
    if P.get('arms'):
        for tag, s in SIDES:
            a = {k: _mirror(v, s) for k, v in P['arms'].items()}
            par = P['arms'].get('parent', 'chest') if isinstance(P['arms'].get('parent'), str) else 'chest'
            specs.append(BoneSpec(f'upperarm.{tag}', tuple(a['shoulder']), tuple(a['elbow']), par, radius=0.06 * sk))
            specs.append(BoneSpec(f'forearm.{tag}', tuple(a['elbow']), tuple(a['hand']), f'upperarm.{tag}', connect=True, radius=0.06 * sk))
    if P.get('hands'):
        for tag, s in SIDES:
            h = P['hands']
            specs.append(BoneSpec(f'hand.{tag}', tuple(_mirror(h['centre'], s)), tuple(_mirror(h['tip'], s)), h.get('parent', 'chest'),
                                  radius=0.08 * sk))
    for m in chains(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.08 * sk))
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'head'), radius=0.08 * sk))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """The game's seven (socket_head, _crown, _back, _mouth, _paw_L/_R, _tail), socket_core at the hover point (a glowing
    heart's beam), socket_hand_L/_R with hands or arms, socket_<chain> at each chain's tip, socket_<prop>."""
    sk = size_of(P)
    hc, hr = _v(P['head_c']), float(P['head_r'])
    hip, top = _v(P['hip']), _v(P['chest'])
    jp = jaw_points(P)
    up_tip = top if top.z >= hip.z else hc + Vector((0, 0, hr))
    out = {
        'socket_head': ('head', tuple(up_tip)),
        'socket_crown': ('head', tuple(up_tip + Vector((0, 0, 0.12 * sk)))),
        'socket_back': ('chest', (0, hip.y + 0.2 * sk, hip.z + 0.05 * sk)),
        'socket_mouth': ('jaw' if jp else 'head', tuple((jp[1] if jp else hc + Vector((0, -hr, -0.3 * hr))) + Vector((0, -0.02 * sk, 0)))),
        'socket_core': ('hover', tuple(hip)),
    }
    if P.get('hands'):
        for tag, s in SIDES:
            out[f'socket_hand_{tag}'] = (f'hand.{tag}', tuple(_mirror(P['hands']['tip'], s)))
            out[f'socket_paw_{tag}'] = out[f'socket_hand_{tag}']
    elif P.get('arms'):
        for tag, s in SIDES:
            out[f'socket_hand_{tag}'] = (f'forearm.{tag}', tuple(_mirror(P['arms']['hand'], s)))
            out[f'socket_paw_{tag}'] = out[f'socket_hand_{tag}']
    else:
        # no hands: the body's sides at the hover height, a little forward (where a strike's effect starts)
        for tag, s in SIDES:
            out[f'socket_paw_{tag}'] = ('chest', (s * 0.6 * hr, hip.y - 0.6 * hr, hip.z))
    ch = chains(P)
    tail = next((m for m in ch if m['kind'] == 'tail'), None) or next((m for m in ch if m['kind'] in ('tassel', 'handle')), None)
    out['socket_tail'] = (tail['bones'][-1], tuple(tail['points'][-1])) if tail else ('hips', tuple(base_of(P)))
    for m in ch:
        out[f"socket_{m['name']}"] = (m['bones'][-1], tuple(m['points'][-1]))
    for pr in P.get('props', []) or []:
        out[f"socket_{pr['name']}"] = (f"prop.{pr['name']}", tuple(pr['tail']))
    return out


# --------------------------------------------------------------------------- clips
class Frame:
    """One frame's pose: rotations (degrees) and offsets (metres) added up per bone, and a scale per bone."""

    def __init__(self):
        self.rot: dict[str, list[float]] = {}
        self.loc: dict[str, list[float]] = {}
        self.scl: dict[str, tuple[float, float, float]] = {}
        self.drop = 0.0      # how far the body is below its rest hover this frame (hanging chains pool by it)

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


def make_clips(cb: A.ClipBuilder, P: dict, only: list[str] | None = None) -> list[A.ClipMeta]:
    sk = size_of(P)
    made: list[A.ClipMeta] = []
    bones = {b.name for b in cb.arm.data.bones}
    style = strike_style(P)
    CH = chains(P)
    HANDS = bool(P.get('hands'))
    ARMS = bool(P.get('arms'))
    JAW = bool(P.get('jaw_open', False)) and bool(P.get('jaw'))
    CLOSED = P.get('blink_closed')
    SHUT_EXP = tuple(math.log(v) / math.log(0.5) for v in (0.3, 0.62, 0.08))
    hip = _v(P['hip'])
    HZ = hip.z
    bob_k = float(P.get('bob', 1.0))
    jitter = float(P.get('jitter', 0.0))
    sway_k = float(P.get('sway', 1.0))
    tilt_k = float(P.get('pulse_tilt', 0.0))
    swimmer = (_v(P['chest']) - base_of(P)).normalized().z < 0.5      # the squash chain runs more forward than up

    def mm(v: float) -> float:
        return v * sk

    def sink_room() -> float:
        """How far the body can come down before its mass touches the ground (the recipe's `sink`, else measured on
        lo_body: the lowest vertex owned mostly by the squash chain, i.e. not by a tassel, a wisp or a handle)."""
        if P.get('sink') is not None:
            return float(P['sink'])
        body = bpy.data.objects.get('lo_body')
        if body is not None and body.type == 'MESH':
            gs = {body.vertex_groups[n].index for n in ('hover', 'hips', 'chest', 'head') if n in body.vertex_groups}
            zs = [v.co.z for v in body.data.vertices if v.groups and max(v.groups, key=lambda g: g.weight).group in gs]
            if len(zs) > 20:
                return max(0.0, float(np.percentile(zs, 0.5)))
        return max(0.0, float(base_of(P).z) - 0.02 * sk)

    SINK = sink_room()
    LOW = min([base_of(P).z] + [p.z for m in CH for p in m['points']])     # the lowest rest point of the rig
    # each chain: does it hang (points down), and how high is its tip off the ground at rest
    hangs = {m['name']: (m['points'][-1] - m['points'][0]).normalized().z < -0.5 for m in CH}
    clear = {m['name']: max(0.0, float(min(p.z for p in m['points'])) - mm(0.04)) for m in CH}

    def frames_of(n: int, step: int) -> list[int]:
        fs = list(range(1, n + 2, step))
        if fs[-1] != n + 1:
            fs.append(n + 1)
        return fs

    def key(f: int, fr: Frame) -> None:
        for b, v in fr.loc.items():
            if b in bones:
                cb.loc(b, f, *v)
        for b, v in fr.rot.items():
            if b in bones:
                cb.rot(b, f, *v)
        for b, v in fr.scl.items():
            if b in bones:
                cb.scale(b, f, *v)

    def eyes_shut(frames: int, k, step: int = 1) -> None:
        if not CLOSED:
            return
        for tag, _s in SIDES:
            pb = cb.arm.pose.bones.get(f'eye.{tag}')
            if pb is None:
                continue
            for f in frames_of(frames, step):
                kk = max(0.0, min(1.0, k((f - 1) / frames)))
                pb.scale = tuple(1.0 + (c - 1.0) * kk ** e for c, e in zip(CLOSED, SHUT_EXP))
                pb.keyframe_insert('scale', frame=f)

    def clip(name: str, n: int, pose, loop: bool = True, hold: bool = False, root_speed: float = 0.0, step: int = 1,
             markers=(), faces=(), shut=None) -> None:
        if only and name not in only:
            return
        cb.begin(name, n, loop=loop, hold=hold, root_speed=root_speed)
        for f in frames_of(n, step):
            key(f, pose((f - 1) / n))
        if shut is not None:
            eyes_shut(n, shut, step)
        for mk, f in markers:
            cb.marker(mk, f)
        for f, face in faces:
            cb.face(f, face)
        made.append(cb.end())

    # ---- posing helpers
    def hover(fr: Frame, t: float, dz: float = 0.0, dx: float = 0.0, dy: float = 0.0, pitch: float = 0.0, roll: float = 0.0,
              yaw: float = 0.0, bob: float = 1.0, rate: float = 1.0) -> None:
        """The body at the hover point: bobbing (bob × the breed's `bob`), moved, tipped forward (pitch), tilted and
        turned about its centre; a jittery breed shakes a little all the time."""
        b = mm(0.025) * bob * bob_k * A.wave(t, rate)
        jx = jy = jz = 0.0
        if jitter:
            jx = mm(0.006) * jitter * (math.sin(t * 2 * math.pi * 11) + 0.5 * math.sin(t * 2 * math.pi * 17))
            jz = mm(0.006) * jitter * math.sin(t * 2 * math.pi * 13 + 1.0)
            jy = 2.0 * jitter * math.sin(t * 2 * math.pi * 9)
        fr.o('hover', dx + jx, dy, dz + b + jz)
        fr.drop = max(fr.drop, -(dz + b + jz))
        fr.r('hover', pitch, roll + 1.5 * sway_k * A.wave(t, rate * 0.5, 0.2) * bob, yaw + jy)

    def squash(fr: Frame, k: float, axis: str = 'z') -> None:
        """Squash (k < 1) or stretch (k > 1) the whole body about its centre along `axis`, keeping its volume."""
        w = 1.0 / math.sqrt(max(0.2, k))
        if axis == 'z':
            fr.scl['hover'] = (w, w, k)
        else:      # along the travel (−Y): a glide's streak
            fr.scl['hover'] = (w, k, w)
        # a stretch about the centre takes the lowest point down with it: hanging chains pool by that too
        kz = k if axis == 'z' else w
        fr.drop = max(fr.drop, (kz - 1.0) * (HZ - LOW))

    def bend(fr: Frame, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        """The squash chain bends: a nod (+x forward), a tilt (+y left), a turn (+z left), shared over chest and head."""
        fr.r('chest', 0.45 * x, 0.45 * y, 0.45 * z)
        fr.r('head', 0.55 * x, 0.55 * y, 0.55 * z)

    def chain_pose(fr: Frame, t: float, trail: float = 0.0, sway: float = 0.0, rate: float = 1.0, lift: float = 0.0,
                   spread: float = 0.0, pool: float = 0.0, tail_wag: float = 0.0, flap: float = 0.0) -> None:
        """Every chain by its kind.
        Trailing (tassel, wisp, ribbon, hood, cape): `trail` degrees back (+x on a hanging or backward chain), swayed
        sideways with a lag down the chain, `spread` outward, `pool` metres of sinking to clear (the chain swings back
        just enough to keep its tip above the ground). Tails swing `tail_wag` (around their `axis`) and lift `lift`;
        fins flap `flap`; a handle barely moves (its `stiff`)."""
        for m in CH:
            n = len(m['bones'])
            k = 1.0 - m['stiff']
            kind = m['kind']
            for i, b in enumerate(m['bones']):
                lag = 0.07 * i
                share = (0.6 + 0.8 * i / max(1, n - 1)) / n
                if kind in TRAILING or kind == 'handle':
                    x = trail * share * k
                    # a hanging chain whose tip would go under the ground (the body sinking, bobbing or settling below
                    # its rest hover) swings back just enough to keep the tip on the ground
                    need = max(pool, fr.drop - clear[m['name']])
                    if i == 0 and need > 0 and m['length'] > 1e-4 and hangs[m['name']]:
                        x += math.degrees(math.acos(max(-1.0, 1.0 - min(2.0, need / m['length']))))
                    zz = sway * share * k * A.wave(t - lag, rate)
                    yy = m['side'] * spread * share * k * (-1)
                    fr.r(b, x, yy, zz)
                elif kind == 'tail':
                    w = tail_wag * share * k * A.wave(t - lag, rate) * 1.6
                    if m['axis'] == 'x':
                        fr.r(b, lift * share * k + w, 0, 0)
                    else:
                        fr.r(b, lift * share * k, 0, w)
                elif kind == 'fin':
                    fr.r(b, 0, -m['side'] * flap * (1.0 if i == 0 else 0.5) * k, 0)

    def hands(fr: Frame, t: float, lift: float = 0.0, fwd: float = 0.0, out: float = 0.0, curl: float = 0.0,
              drift: float = 1.0, sides=('L', 'R'), rate: float = 1.0) -> None:
        """Floating hands (or little arms): raised `lift` metres, `fwd` forward, `out` sideways, the fingers curled
        `curl` degrees; drifting on their own a little. Arms turn the same goals into shoulder and elbow angles."""
        for tag, s in SIDES:
            if tag not in sides:
                continue
            dz = lift + mm(0.012) * drift * A.wave(t, rate * 1.3, 0.2 if tag == 'L' else 0.6)
            if HANDS:
                fr.o(f'hand.{tag}', s * out, -fwd, dz)
                fr.r(f'hand.{tag}', curl, 0, -s * 0.5 * out / max(mm(0.1), 1e-4) * 10)
            if ARMS:
                # a little arm: raise (−y on the left lifts it out and up), reach forward (−x), bend the elbow
                fr.r(f'upperarm.{tag}', -fwd / max(mm(0.05), 1e-4) * 12, -s * (lift / max(mm(0.05), 1e-4) * 18 + out / max(mm(0.05), 1e-4) * 10), 0)
                fr.r(f'forearm.{tag}', -curl * 0.6, 0, 0)

    def jaw(fr: Frame, deg_: float) -> None:
        if JAW and deg_:
            fr.r('jaw', deg_, 0, 0)

    # ================================================================= ranch life
    def p_idle(t: float) -> Frame:
        fr = Frame()
        hover(fr, t, yaw=8 * A.pulse(t, 0.55, 0.8))
        bend(fr, 2 * A.wave(t, 1.0), 0, 6 * A.pulse(t, 0.55, 0.8))
        squash(fr, 1.0 + 0.02 * A.wave(t, 1.0, 0.25))
        hands(fr, t)
        chain_pose(fr, t, trail=3, sway=8, rate=1.0, tail_wag=8, flap=6 * A.wave(t, 2.0))
        return fr

    def p_idle_happy(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 3)
        hover(fr, t, dz=mm(0.05) * b, roll=6 * A.wave(t, 1.5), bob=0.5, rate=3.0)
        bend(fr, -4, 6 * A.wave(t, 1.5), 0)
        squash(fr, 1.0 + 0.07 * A.wave(t, 3.0, 0.25))
        hands(fr, t, lift=mm(0.06) + mm(0.03) * b, out=mm(0.03), rate=3.0)
        chain_pose(fr, t, trail=8 * b, sway=18, rate=3.0, tail_wag=20, flap=20 * A.wave(t, 6.0))
        jaw(fr, 14)
        return fr

    def p_idle_tired(t: float) -> Frame:
        fr = Frame()
        yawn = A.pulse(t, 0.45, 0.72)
        hover(fr, t, dz=-0.35 * SINK, pitch=12 - 14 * yawn, bob=0.6, rate=0.6)
        bend(fr, 8 - 16 * yawn, 0, 0)
        squash(fr, 0.96 + 0.08 * yawn)
        hands(fr, t, lift=-mm(0.03) + mm(0.05) * yawn, out=mm(0.05) * yawn, drift=0.4, rate=0.6)
        chain_pose(fr, t, trail=-2, sway=3, rate=0.6, tail_wag=3, pool=0.35 * SINK)
        jaw(fr, 24 * yawn)
        return fr

    def p_idle_sad(t: float) -> Frame:
        fr = Frame()
        hover(fr, t, dz=-0.4 * SINK, pitch=10, bob=0.5, rate=0.7)
        bend(fr, 12, 0, -6 + 3 * A.pulse(t, 0.5, 0.7))
        squash(fr, 0.95)
        hands(fr, t, lift=-mm(0.02), fwd=mm(0.04), out=-mm(0.03), drift=0.4, rate=0.7)
        chain_pose(fr, t, trail=-4, sway=3, rate=0.7, tail_wag=2, lift=-10, pool=0.4 * SINK)
        return fr

    def p_idle_sick(t: float) -> Frame:
        fr = Frame()
        w = A.wave(t, 0.8)
        hover(fr, t, dx=mm(0.04) * w, dz=-0.3 * SINK, roll=8 * w, pitch=6, bob=0.6, rate=0.8)
        bend(fr, 6, 3 * A.wave(t, 6.0) * A.pulse(t, 0.3, 0.45), 0)
        squash(fr, 1.0 + 0.03 * A.wave(t, 7.0) * A.pulse(t, 0.25, 0.5))
        hands(fr, t, fwd=mm(0.06), lift=-mm(0.02), out=-mm(0.05), sides=('L',), drift=0.3, rate=0.8)
        hands(fr, t, lift=-mm(0.03), sides=('R',), drift=0.3, rate=0.8)
        chain_pose(fr, t, trail=0, sway=5, rate=0.8, tail_wag=3, pool=0.3 * SINK)
        return fr

    def settle(fr: Frame, t: float, k: float, depth: float) -> None:
        """Sinks `depth` of the room under it (k: 0 hovering → 1 settled), the chains pooling clear of the ground."""
        hover(fr, t, dz=-depth * SINK * k, pitch=4 * k, bob=1.0 - 0.8 * k, rate=0.6)
        squash(fr, 1.0 - 0.06 * k)
        chain_pose(fr, t, trail=6 * k, sway=3, rate=0.6, tail_wag=3, lift=-15 * k)

    def p_sleep(t: float) -> Frame:
        fr = Frame()
        b = A.wave(t, 0.4)
        settle(fr, t, 1.0, 0.85)
        bend(fr, 14 + 3 * b, 6, 0)
        squash(fr, 0.93 + 0.03 * b)
        hands(fr, t, lift=-mm(0.04), fwd=mm(0.03), out=-mm(0.06), drift=0.2, rate=0.4)
        return fr

    def p_eat(t: float) -> Frame:
        fr = Frame()
        dip = A.step_ease(t, 0.0, 0.2) * (1 - A.step_ease(t, 0.85, 1.0))
        chew = dip * abs(math.sin(t * 2 * math.pi * 3))
        hover(fr, t, dz=-mm(0.03) * dip, pitch=12 * dip, bob=0.5)
        bend(fr, 6 * dip + 3 * chew, 0, 0)
        squash(fr, 1.0 - 0.04 * chew)
        hands(fr, t, lift=mm(0.05) * dip, fwd=mm(0.08) * dip, out=-mm(0.06) * dip, curl=30 * dip)
        chain_pose(fr, t, trail=2, sway=6, tail_wag=8)
        jaw(fr, 16 * chew)
        return fr

    def p_pet(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        hover(fr, t, dz=mm(0.015) * b, roll=10, bob=0.6, rate=2.0)
        bend(fr, -6, 12 + 2 * A.wave(t, 2.0), 4)
        squash(fr, 1.0 + 0.04 * b)
        hands(fr, t, lift=mm(0.03), fwd=mm(0.05), out=-mm(0.07), curl=20, rate=2.0)
        chain_pose(fr, t, trail=4, sway=16, rate=2.0, tail_wag=22, flap=14 * A.wave(t, 4.0))
        jaw(fr, 8)
        return fr

    def p_look(t: float) -> Frame:
        fr = Frame()
        yaw = 35 * A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56)) - 35 * A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        hover(fr, t, yaw=0.5 * yaw)
        bend(fr, 0, 0, 0.5 * yaw)
        hands(fr, t, out=mm(0.01))
        chain_pose(fr, t, trail=2, sway=6 - 0.2 * yaw, tail_wag=6)
        return fr

    def p_hop(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.28, 0.82)
        crouch = A.pulse(t, 0.0, 0.28) + 0.8 * A.pulse(t, 0.8, 1.0)
        hover(fr, t, dz=mm(0.15) * air - 0.25 * SINK * crouch, bob=0.0)
        squash(fr, 1.0 - 0.14 * crouch + 0.12 * A.pulse(t, 0.28, 0.6))
        bend(fr, 8 * crouch - 6 * air, 0, 0)
        hands(fr, t, lift=mm(0.08) * air - mm(0.03) * crouch, out=mm(0.04) * air)
        chain_pose(fr, t, trail=-20 * air + 14 * crouch, sway=6, tail_wag=10, flap=25 * air)
        return fr

    def p_celebrate(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        land = A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)
        hover(fr, t, dz=mm(0.12) * air - 0.2 * SINK * land, yaw=40 * A.step_ease(t, 0.08, 0.32) - 40 * A.step_ease(t, 0.43, 0.67), bob=0.0)
        squash(fr, 1.0 + 0.1 * air - 0.12 * land)
        hands(fr, t, lift=mm(0.12), out=mm(0.06), curl=-15, rate=3.0)
        chain_pose(fr, t, trail=-10 * air, sway=20, rate=2.0, tail_wag=26, flap=30 * A.wave(t, 6.0))
        jaw(fr, 18)
        return fr

    # ================================================================= moving: glides
    def glide(t: float, speed: float, lean: float, trail: float, rate: float = 2.0, back: bool = False, guard: bool = False) -> Frame:
        fr = Frame()
        sgn = -1 if back else 1
        hover(fr, t, pitch=sgn * lean, bob=0.6, rate=rate)
        bend(fr, -0.4 * sgn * lean, 0, 0)
        squash(fr, 1.0 + 0.04 * speed, axis='y')
        if guard:
            hands(fr, t, lift=mm(0.08), fwd=mm(0.06), out=-mm(0.02), curl=25, rate=rate)
        else:
            hands(fr, t, lift=-mm(0.02), fwd=-mm(0.05) * speed, rate=rate)
        chain_pose(fr, t, trail=sgn * trail, sway=6, rate=rate, tail_wag=10 + 6 * speed, flap=12 * speed * A.wave(t, rate * 2))
        return fr

    def glide_marks(n: int) -> list:
        return [('step', 1), ('step', 1 + n // 2)]

    # ================================================================= scenes
    def p_sit_down(t: float) -> Frame:
        fr = Frame()
        settle(fr, t, C.ease_in_out(t), 0.6)
        hands(fr, t, lift=-mm(0.03) * t, out=-mm(0.04) * t)
        return fr

    def p_sit(t: float) -> Frame:
        fr = Frame()
        settle(fr, t, 1.0, 0.6)
        bend(fr, 2 * A.wave(t, 1.0), 0, 8 * A.pulse(t, 0.5, 0.75))
        hands(fr, t, lift=-mm(0.03), out=-mm(0.04), drift=0.5)
        return fr

    def p_dizzy(t: float) -> Frame:
        fr = Frame()
        c, s_ = math.cos(t * 4 * math.pi), math.sin(t * 4 * math.pi)
        hover(fr, t, dx=mm(0.05) * s_, dy=mm(0.04) * c, roll=12 * s_, pitch=8 * c, bob=0.5)
        bend(fr, 6 * c, 8 * s_, 10 * s_)
        hands(fr, t, out=mm(0.05), lift=mm(0.02) * c)
        chain_pose(fr, t, trail=6 * c, sway=22, rate=2.0, tail_wag=14, spread=10)
        return fr

    # ================================================================= battle
    def p_battle_idle(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        hover(fr, t, dz=mm(0.02) * b, pitch=8, yaw=-6, bob=0.8, rate=2.0)
        bend(fr, -3, 0, 0)
        squash(fr, 1.0 + 0.04 * A.wave(t, 2.0, 0.25))
        hands(fr, t, lift=mm(0.08), fwd=mm(0.06), out=-mm(0.02), curl=25, rate=2.0)
        chain_pose(fr, t, trail=6, sway=10, rate=2.0, tail_wag=14, flap=10 * A.wave(t, 4.0))
        return fr

    def p_strafe(t: float, side: int) -> Frame:
        fr = Frame()
        hover(fr, t, roll=side * 12, pitch=5, bob=0.6, rate=2.0)
        bend(fr, 0, -side * 4, -side * 4)
        hands(fr, t, lift=mm(0.08), fwd=mm(0.06), out=-mm(0.02), curl=25, rate=2.0)
        chain_pose(fr, t, trail=6, sway=-side * 14, rate=2.0, tail_wag=8, flap=8)
        for m in CH:
            if m['kind'] in TRAILING:
                for b in m['bones']:
                    fr.r(b, 0, side * 12 / len(m['bones']), 0)
        return fr

    def p_sidestep(t: float, side: int) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.18, 0.92)
        crouch = A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        hover(fr, t, dz=mm(0.07) * air - 0.15 * SINK * crouch, roll=side * 22 * air, bob=0.0)
        squash(fr, 1.0 - 0.1 * crouch + 0.08 * air)
        hands(fr, t, out=mm(0.06) * air, lift=mm(0.04) * air)
        chain_pose(fr, t, trail=10 * air, sway=-side * 25 * air)
        for m in CH:
            if m['kind'] in TRAILING:
                for b in m['bones']:
                    fr.r(b, 0, side * 22 * air / len(m['bones']), 0)
        return fr

    def p_hit(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.8)
        hover(fr, t, dy=mm(0.12) * k, dz=mm(0.04) * k, pitch=-22 * k, yaw=-12 * k, bob=0.0)
        bend(fr, -8 * k, -6 * k, -14 * k)
        squash(fr, 1.0 - 0.1 * A.pulse(t, 0.0, 0.3))
        hands(fr, t, lift=mm(0.08) * k, fwd=-mm(0.04) * k, out=mm(0.05) * k, curl=-20 * k)
        chain_pose(fr, t, trail=-25 * k, sway=10, tail_wag=6, spread=15 * k)
        jaw(fr, 10 * k)
        return fr

    def p_hit_heavy(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.6)
        tumble = 360 * A.step_ease(t, 0.05, 0.6) if swimmer else 0.0
        hover(fr, t, dy=mm(0.3) * k, dz=mm(0.08) * k, pitch=-45 * k, yaw=-30 * k, roll=tumble, bob=0.0)
        bend(fr, -10 * k, -10 * k, -18 * k)
        squash(fr, 1.0 - 0.16 * A.pulse(t, 0.0, 0.25) + 0.06 * A.pulse(t, 0.25, 0.55))
        hands(fr, t, lift=mm(0.1) * k, fwd=-mm(0.06) * k, out=mm(0.08) * k, curl=-30 * k)
        chain_pose(fr, t, trail=-40 * k, sway=16, tail_wag=10, spread=25 * k)
        jaw(fr, 16 * k)
        return fr

    lift_tab = P.get('ko_lift') or []

    def ko_lift(t: float) -> float:
        if not lift_tab:
            return 0.0
        for (t0, d0), (t1, d1) in zip(lift_tab[:-1], lift_tab[1:]):
            if t0 <= t <= t1:
                return d0 + (d1 - d0) * (t - t0) / max(t1 - t0, 1e-9)
        return lift_tab[0][1] if t < lift_tab[0][0] else lift_tab[-1][1]

    def p_ko(t: float) -> Frame:
        """It wobbles, its glow (in the runtime) gutters, it drifts down and settles on its right side on the ground at
        body_width (the hover point that high), the chains lying out, the hands dropped beside it, eyes shut."""
        fr = Frame()
        wob = (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = A.step_ease(t, 0.35, 0.85)
        lie = float(P.get('body_width', 0.5 * HZ))
        fr.r('root', 0, 8 * math.sin(t * 2 * math.pi * 2.5) * wob - KO_ROLL * fall, 0)
        h = HZ * (1 - fall) + lie * fall + ko_lift(t)
        a = math.radians(KO_ROLL * fall)
        fr.o('hover', h * math.sin(a), 0.0, h * math.cos(a) - HZ)
        bend(fr, 10 * fall, 0, 0)
        squash(fr, 1.0 - 0.06 * fall)
        hands(fr, t, lift=-mm(0.04) * fall, out=-mm(0.03) * fall, drift=0.0)
        chain_pose(fr, t, trail=10 * fall, sway=2, tail_wag=0, lift=-10 * fall)
        return fr

    def p_win(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.04, 0.36)
        spin = 360 * A.step_ease(t, 0.42, 0.82)
        hover(fr, t, dz=mm(0.14) * air, yaw=spin, bob=0.3)
        squash(fr, 1.0 + 0.1 * air - 0.1 * A.pulse(t, 0.34, 0.44))
        hands(fr, t, lift=mm(0.14), out=mm(0.07), curl=-15, rate=3.0)
        chain_pose(fr, t, trail=-12 * air + 20 * A.pulse(t, 0.42, 0.82), sway=20, rate=2.0, tail_wag=26, flap=30 * A.wave(t, 6.0))
        jaw(fr, 18)
        return fr

    # ---- strike: 24 frames, impact at 13 (every style)
    def p_strike(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.42)
        go = A.pulse(t, 0.3, 0.75)
        if style == 'ram':
            # draws back and squashes, then darts at the target stretched out, the front (a tusk, a spark) leading
            hover(fr, t, dy=mm(0.08) * ant - mm(0.32) * go, dz=mm(0.02) * go, pitch=-8 * ant + (2 if swimmer else 6) * go, bob=0.0)
            squash(fr, 1.0 - 0.12 * ant + 0.2 * go, axis='y')
            bend(fr, -6 * ant + 2 * go, 0, 0)
            hands(fr, t, fwd=-mm(0.06) * go, lift=mm(0.02))
            chain_pose(fr, t, trail=-10 * ant + 40 * go, sway=4, tail_wag=6, lift=10 * go, flap=-25 * go)
            jaw(fr, 10 * go)
        elif style == 'swipe':
            # the left hand (or arm) rears up and back, then sweeps across in front of the face
            hover(fr, t, dy=-mm(0.06) * go, pitch=-4 * ant + 10 * go, yaw=12 * ant - 18 * go, bob=0.0)
            bend(fr, 0, 0, 6 * ant - 10 * go)
            if HANDS:
                sweep = A.step_ease(t, 0.34, 0.62)
                fr.o('hand.L', mm(0.04) - mm(0.24) * sweep, mm(0.04) * ant - mm(0.16) * go, mm(0.12) * ant - mm(0.08) * sweep)
                fr.r('hand.L', -30 * go, 0, -70 * sweep)
                hands(fr, t, lift=mm(0.05), fwd=mm(0.03), curl=20, sides=('R',))
            else:
                hands(fr, t, lift=mm(0.12) * ant + mm(0.04) * go, fwd=mm(0.14) * go, out=mm(0.06) * ant - mm(0.12) * go, curl=-20 * go)
            chain_pose(fr, t, trail=20 * go, sway=10, tail_wag=8)
            jaw(fr, 14 * go)
        elif style == 'gust':
            # draws in a breath (stretched up, leaning back), then blows: squashes forward, mouth wide
            hover(fr, t, dy=mm(0.03) * ant - mm(0.04) * go, pitch=-12 * ant + 6 * go, bob=0.0)
            squash(fr, 1.0 + 0.1 * ant - 0.14 * go)
            bend(fr, -8 * ant + 5 * go, 0, 0)
            hands(fr, t, lift=mm(0.06) * ant, fwd=mm(0.08) * go, out=mm(0.05) * ant)
            chain_pose(fr, t, trail=-14 * ant + 24 * go, sway=6, tail_wag=8, flap=-30 * ant + 30 * go)
            jaw(fr, 10 * ant + 28 * go)
        elif style == 'pulse':
            # gathers (squashed small, tipping back toward the light by pulse_tilt), then bursts: a quick swell and a
            # tip toward the target, as a beam leaves the core (socket_core)
            hover(fr, t, dy=-mm(0.03) * go, pitch=-6 * ant + 8 * go, roll=tilt_k * (ant - go), bob=0.0)
            swell = A.pulse(t, 0.45, 0.62)
            squash(fr, 1.0 - 0.08 * ant + 0.18 * swell)
            fr.scl['hover'] = tuple(v * (1.0 + 0.1 * swell) for v in fr.scl['hover'])
            bend(fr, -4 * ant + 6 * go, 0, 0)
            hands(fr, t, lift=mm(0.06) * ant + mm(0.03) * go, fwd=mm(0.1) * go, out=mm(0.05) * ant - mm(0.04) * go, curl=-25 * go)
            chain_pose(fr, t, trail=-8 * ant + 18 * swell, sway=6, tail_wag=8, spread=18 * swell, flap=20 * swell)
            jaw(fr, 18 * go)
        elif style == 'spin':
            # a spinning dart: one full turn while lunging forward (a ball-lightning dance, a polar spiral)
            spin = 360 * A.step_ease(t, 0.3, 0.7)
            hover(fr, t, dy=-mm(0.25) * go, dz=mm(0.03) * go, roll=spin if swimmer else 0.0, yaw=0.0 if swimmer else spin, bob=0.0)
            squash(fr, 1.0 - 0.1 * ant + 0.1 * go, axis='y')
            hands(fr, t, out=mm(0.08) * go, lift=mm(0.03))
            chain_pose(fr, t, trail=30 * go, sway=10, tail_wag=6, spread=25 * go)
        elif style == 'lash':
            # both hands raised high, then the wisps and tails whip forward over the body at the target
            hover(fr, t, dy=mm(0.04) * ant - mm(0.08) * go, pitch=-10 * ant + 14 * go, bob=0.0)
            squash(fr, 1.0 + 0.08 * ant - 0.06 * go)
            bend(fr, -6 * ant + 8 * go, 0, 0)
            hands(fr, t, lift=mm(0.14) * (ant + go), fwd=mm(0.06) * go, out=mm(0.03), curl=-30 * ant)
            chain_pose(fr, t, trail=-40 * ant - 70 * go, sway=8, tail_wag=6, lift=30 * go, spread=10 * ant)
            jaw(fr, 16 * go)
        return fr

    def p_cast(t: float) -> Frame:
        fr = Frame()
        up = A.step_ease(t, 0.0, 0.3) * (1 - A.step_ease(t, 0.7, 1.0))
        rel = A.pulse(t, 0.48, 0.72)
        hover(fr, t, dz=mm(0.06) * up, pitch=-6 * up + 10 * rel, bob=0.3, rate=2.0)
        squash(fr, 1.0 + 0.06 * up + 0.08 * rel)
        bend(fr, -6 * up + 8 * rel, 0, 0)
        hands(fr, t, lift=mm(0.14) * up, fwd=mm(0.12) * rel, out=mm(0.06) * up - mm(0.06) * rel, curl=-25 * up)
        chain_pose(fr, t, trail=-10 * up + 25 * rel, sway=12, rate=3.0, tail_wag=12, spread=20 * rel + 8 * up, flap=24 * rel)
        jaw(fr, 16 * up)
        return fr

    def p_shove(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.36)
        go = A.pulse(t, 0.28, 0.7)
        hover(fr, t, dy=mm(0.05) * ant - mm(0.16) * go, pitch=-6 * ant + 10 * go, bob=0.0)
        squash(fr, 1.0 - 0.08 * ant + 0.08 * go, axis='y')
        hands(fr, t, fwd=mm(0.14) * go - mm(0.03) * ant, lift=mm(0.04), out=-mm(0.03), curl=40 * go)
        chain_pose(fr, t, trail=-8 * ant + 22 * go, sway=4, tail_wag=6)
        return fr

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
    clip('walk', 30, lambda t: glide(t, 1.0, 8, 10, 2.0), root_speed=mm(SPEED['walk']), markers=glide_marks(30))
    clip('run', 20, lambda t: glide(t, 2.0, 16, 30, 2.0), root_speed=mm(SPEED['run']), markers=glide_marks(20))
    clip('sit_down', 24, p_sit_down, loop=False, hold=True)
    clip('sit', 120, p_sit, step=2)
    clip('dizzy', 60, p_dizzy, faces=[(1, 'dizzy')])
    clip('battle_idle', 40, p_battle_idle)
    clip('step_fwd', 24, lambda t: glide(t, 0.6, 6, 6, 2.0, guard=True), root_speed=mm(SPEED['step_fwd']), markers=glide_marks(24))
    clip('step_back', 24, lambda t: glide(t, 0.5, 6, 6, 2.0, back=True, guard=True), root_speed=mm(SPEED['step_back']), markers=glide_marks(24))
    clip('dash', 20, lambda t: glide(t, 3.0, 26, 45, 2.0), root_speed=mm(SPEED['dash']), markers=glide_marks(20))
    clip('strike', 24, p_strike, loop=False, markers=[('impact', 13)], faces=[(1, 'angry'), (20, 'neutral')])
    clip('cast', 36, p_cast, loop=False, markers=[('release', 20)], faces=[(1, 'strain'), (28, 'neutral')])
    clip('shove', 24, p_shove, loop=False, markers=[('impact', 10)])
    clip('hit', 15, p_hit, loop=False, faces=[(1, 'surprised'), (12, 'neutral')], shut=lambda t: 0.85 * A.pulse(t, 0.0, 0.7))
    clip('hit_heavy', 24, p_hit_heavy, loop=False, faces=[(1, 'strain'), (18, 'neutral')], shut=lambda t: 0.9 * A.pulse(t, 0.0, 0.75))
    clip('ko', 36, p_ko, loop=False, hold=True, faces=[(1, 'strain'), (20, 'dizzy')],
         shut=lambda t: max(0.8 * A.pulse(t, 0.0, 0.3), A.step_ease(t, 0.35, 0.6)))
    clip('win', 60, p_win, markers=[('land', 22)], faces=[(1, 'happy')])
    clip('strafe_l', 24, lambda t: p_strafe(t, 1), root_speed=mm(SPEED['strafe']), markers=[('step', 1), ('step', 13)])
    clip('strafe_r', 24, lambda t: p_strafe(t, -1), root_speed=mm(SPEED['strafe']), markers=[('step', 1), ('step', 13)])
    clip('sidestep_l', 8, lambda t: p_sidestep(t, 1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    clip('sidestep_r', 8, lambda t: p_sidestep(t, -1), loop=False, root_speed=SIDESTEP_DISTANCE / (8 / A.FPS), markers=[('land', 8)])
    return made
