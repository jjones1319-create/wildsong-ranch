"""The quadruped body plan (ART_2_PLAN §4): rig template, sockets and the clip generators.

Proportions come from the breed recipe (`P`, metres; the monster faces −Y, Z is up). Rotations in the clip
generators are world-aligned degrees relative to the parent bone: +x nods forward/down (for a forward or
upward bone) and swings a leg backward; +z turns toward the monster's left; +y rolls.
"""
from __future__ import annotations

import math

from mathutils import Vector

from lib import anim as A
from lib import common as C
from lib.rig import BoneSpec

PLAN = 'quadruped'
LEGS = ['FL', 'FR', 'BL', 'BR']

SPRINGS = [
    {'kind': 'ear', 'chain': ['ear.L.1', 'ear.L.2']},
    {'kind': 'ear', 'chain': ['ear.R.1', 'ear.R.2']},
    {'kind': 'tail', 'chain': ['tail.1', 'tail.2', 'tail.3']},
]


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    hip = Vector(P['hip'])
    chest = Vector(P['chest'])
    hc = Vector(P['head_c'])
    hr = P['head_r']
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25, 0), radius=0.5),
        BoneSpec('hips', tuple(hip), tuple(hip + Vector((0, -0.12, 0.02))), 'root', radius=0.34),
        BoneSpec('spine', tuple(hip + Vector((0, -0.12, 0.02))), tuple(chest + Vector((0, 0.06, -0.01))), 'hips', connect=True, radius=0.34),
        BoneSpec('chest', tuple(chest + Vector((0, 0.06, -0.01))), tuple(chest + Vector((0, -0.12, 0.0))), 'spine', connect=True, radius=0.34),
        BoneSpec('neck', tuple(chest + Vector((0, -0.12, 0.0))), tuple(hc + Vector((0, 0.06, -hr * 0.55))), 'chest', connect=True, radius=0.25),
        BoneSpec('head', tuple(hc + Vector((0, 0.06, -hr * 0.55))), tuple(hc + Vector((0, 0.0, hr))), 'neck', connect=True, radius=hr * 1.35),
        BoneSpec('jaw', tuple(hc + Vector((0, -0.06, -hr * 0.35))), tuple(hc + Vector((0, -hr * 0.95, -hr * 0.6))), 'head', radius=0.12),
    ]
    # ears: two bones each, from the base along ear_dir
    eb = Vector(P['ear_base'])
    ed = Vector(P['ear_dir']).normalized()
    el = P['ear_len']
    for side, sx in (('L', 1), ('R', -1)):
        b = Vector((eb.x * sx, eb.y, eb.z))
        d = Vector((ed.x * sx, ed.y, ed.z))
        m = b + d * el * 0.5
        t = b + d * el
        specs.append(BoneSpec(f'ear.{side}.1', tuple(b), tuple(m), 'head', radius=0.11))
        specs.append(BoneSpec(f'ear.{side}.2', tuple(m), tuple(t), f'ear.{side}.1', connect=True, radius=0.11))
    # tail: three bones
    tb = Vector(P['tail_base'])
    td = Vector(P.get('tail_dir', (0, 1, -0.1))).normalized()
    tl = P['tail_len']
    pts = [tb + td * tl * k / 3 for k in range(4)]
    specs.append(BoneSpec('tail.1', tuple(pts[0]), tuple(pts[1]), 'hips', radius=0.1))
    specs.append(BoneSpec('tail.2', tuple(pts[1]), tuple(pts[2]), 'tail.1', connect=True, radius=0.11))
    specs.append(BoneSpec('tail.3', tuple(pts[2]), tuple(pts[3]), 'tail.2', connect=True, radius=0.12))
    # legs: thigh → shin → foot, with the knee a little back so the IK has slack
    for leg in LEGS:
        x, y, hz = P['legs'][leg]
        kb = P.get('knee_back', 0.03)
        ankle = P.get('ankle_z', 0.035)
        l1 = (hz - ankle) * 0.52
        knee = Vector((x, y - kb, hz - l1))      # knee a little forward, so the IK has slack to bend
        foot = Vector((x, y, ankle))
        toe = Vector((x, y - P.get('foot_len', 0.12), ankle * 0.6))
        parent = 'chest' if leg[0] == 'F' else 'hips'
        r = P.get('leg_radius', 0.11)
        specs.append(BoneSpec(f'thigh.{leg}', (x, y, hz), tuple(knee), parent, radius=r))
        specs.append(BoneSpec(f'shin.{leg}', tuple(knee), tuple(foot), f'thigh.{leg}', connect=True, radius=r))
        specs.append(BoneSpec(f'foot.{leg}', tuple(foot), tuple(toe), f'shin.{leg}', connect=True, radius=r * 1.2))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    hc = Vector(P['head_c'])
    hr = P['head_r']
    fl = P['legs']['FL']
    fr = P['legs']['FR']
    tb = Vector(P['tail_base'])
    td = Vector(P.get('tail_dir', (0, 1, -0.1))).normalized()
    return {
        'socket_head': ('head', (0, hc.y, hc.z + hr)),
        'socket_crown': ('head', (0, hc.y, hc.z + hr + 0.12)),
        'socket_back': ('spine', (0, P['hip'][1] - 0.1, P['hip'][2] + 0.3)),
        'socket_mouth': ('jaw', (0, hc.y - hr * 1.05, hc.z - hr * 0.55)),
        'socket_paw_L': ('foot.FL', (fl[0], fl[1] - 0.1, 0.03)),
        'socket_paw_R': ('foot.FR', (fr[0], fr[1] - 0.1, 0.03)),
        'socket_tail': ('tail.3', tuple(tb + td * P['tail_len'])),
    }


# --------------------------------------------------------------------------- leg helpers
class Legs:
    """Analytic two-bone IK for the four legs, in the body's frame (hip height may bob)."""

    def __init__(self, cb: A.ClipBuilder, P: dict):
        self.cb = cb
        self.P = P
        self.rest: dict[str, tuple[float, float]] = {}
        for leg in LEGS:
            x, y, hz = P['legs'][leg]
            l1, l2 = self.lengths(leg)
            self.rest[leg] = A.leg_ik(Vector((0, 0, hz)), Vector((0, 0, P.get('ankle_z', 0.035))), l1, l2, Vector((0, -1, 0)))

    def lengths(self, leg: str) -> tuple[float, float]:
        x, y, hz = self.P['legs'][leg]
        kb = self.P.get('knee_back', 0.03)
        ankle = self.P.get('ankle_z', 0.035)
        drop = (hz - ankle) * 0.52
        hip = Vector((0, 0, hz))
        knee = Vector((0, -kb, hz - drop))       # the knee sits a little forward (−Y), as the rig builds it
        foot = Vector((0, 0, ankle))
        return (knee - hip).length, (foot - knee).length

    def place(self, leg: str, frame: int, dy: float, dz: float, body_dz: float = 0.0, splay: float = 0.0, foot_extra: float = 0.0) -> None:
        """Put the foot at (dy back, dz up) from its rest spot while the body is `body_dz` higher."""
        x, y, hz = self.P['legs'][leg]
        l1, l2 = self.lengths(leg)
        ankle = self.P.get('ankle_z', 0.035)
        hip = Vector((0, 0, hz + body_dz))
        foot = Vector((0, dy, ankle + dz))
        th, kn = A.leg_ik(hip, foot, l1, l2, Vector((0, -1, 0)))
        rth, rkn = self.rest[leg]
        cb = self.cb
        cb.rot(f'thigh.{leg}', frame, x=-(th - rth), y=splay * (1 if leg.endswith('L') else -1))
        cb.rot(f'shin.{leg}', frame, x=-(kn - rkn))
        cb.rot(f'foot.{leg}', frame, x=(th - rth) + (kn - rkn) + foot_extra)

    def pose(self, leg: str, frame: int, thigh: float, shin: float, foot: float = 0.0, splay: float = 0.0) -> None:
        cb = self.cb
        cb.rot(f'thigh.{leg}', frame, x=thigh, y=splay * (1 if leg.endswith('L') else -1))
        cb.rot(f'shin.{leg}', frame, x=shin)
        cb.rot(f'foot.{leg}', frame, x=foot)


def gait(legs: Legs, frames: int, stride: float, lift: float, phases: dict[str, float], stance: float = 0.6,
         body_bob: float = 0.008, reverse: bool = False, bob_fn=None) -> list[int]:
    """Key an in-place walk/run cycle. Returns the frames of foot plants (for `step` markers)."""
    cb = legs.cb
    plants: list[int] = []
    for f in range(1, frames + 2):
        t = (f - 1) / frames
        bob = bob_fn(t) if bob_fn else body_bob * abs(math.sin(t * 2 * math.pi))
        for leg in LEGS:
            p = (t + phases[leg]) % 1.0
            if p < stance:
                u = p / stance
                dy = -stride / 2 + stride * u      # front (−Y) → back (+Y) while planted
                dz = 0.0
            else:
                u = (p - stance) / (1 - stance)
                dy = stride / 2 - stride * C.ease_in_out(u)
                dz = lift * math.sin(u * math.pi)
            if reverse:
                dy = -dy
            legs.place(leg, f, dy, dz, body_dz=bob)
    for leg in LEGS:
        # the foot plants where its phase wraps to 0
        plants.append(1 + int(round(((1.0 - phases[leg]) % 1.0) * frames)) % frames)
    return sorted(set(plants))


# --------------------------------------------------------------------------- clips
def make_clips(cb: A.ClipBuilder, P: dict, only: list[str] | None = None) -> list[A.ClipMeta]:
    legs = Legs(cb, P)
    hz = P['hip'][2]
    made: list[A.ClipMeta] = []

    def want(name: str) -> bool:
        return not only or name in only

    def breathe(frames: int, rate: float = 1.0, depth: float = 1.0, tail: float = 1.0, ear: float = 1.0) -> None:
        cb.sample('chest', frames, lambda t: (2.0 * depth * A.wave(t, rate), 0, 0), step=3)
        cb.sample('hips', frames, lambda t: (0, 0, 0.004 * depth * A.wave(t, rate)), kind='loc', step=3)
        cb.sample('head', frames, lambda t: (-1.4 * depth * A.wave(t, rate), 0, 0), step=3)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', frames, lambda t, sx=sx: (0, sx * 2.5 * ear * A.wave(t, rate, 0.25), 0), step=3)
        cb.sample('tail.1', frames, lambda t: (0, 0, 7 * tail * A.wave(t, rate * 1.5)), step=3)
        cb.sample('tail.2', frames, lambda t: (0, 0, 9 * tail * A.wave(t, rate * 1.5, -0.12)), step=3)
        cb.sample('tail.3', frames, lambda t: (0, 0, 11 * tail * A.wave(t, rate * 1.5, -0.24)), step=3)

    def ears(frames: int, droop: float, flutter: float = 0.0, rate: float = 1.0) -> None:
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', frames, lambda t, sx=sx: (0, sx * (droop + flutter * A.wave(t, rate, 0.25)), 0), step=3)
            cb.sample(f'ear.{s}.2', frames, lambda t, sx=sx: (0, sx * (droop * 0.6 + flutter * 0.6 * A.wave(t, rate, 0.1)), 0), step=3)

    def tail(frames: int, up: float, wag: float, rate: float = 1.0) -> None:
        cb.sample('tail.1', frames, lambda t: (up, 0, wag * A.wave(t, rate)), step=2)
        cb.sample('tail.2', frames, lambda t: (up * 0.5, 0, wag * 1.2 * A.wave(t, rate, -0.12)), step=2)
        cb.sample('tail.3', frames, lambda t: (up * 0.3, 0, wag * 1.4 * A.wave(t, rate, -0.24)), step=2)

    def stand(frames: int, splay: float = 0.0) -> None:
        for leg in LEGS:
            legs.pose(leg, 1, 0, 0, 0, splay)
            legs.pose(leg, 1 + frames, 0, 0, 0, splay)

    def squash(frames: int, fn) -> None:
        """fn(t) -> (vertical scale); the width compensates to keep volume."""
        def s(t):
            v = fn(t)
            w = 1.0 / math.sqrt(max(0.2, v))
            return (w, w, v)
        cb.sample('root', frames, s, kind='scale', step=1)

    # ---- ranch life
    if want('idle'):
        n = 120
        cb.begin('idle', n, loop=True)
        breathe(n, rate=1.0, depth=1.0)
        stand(n)
        cb.sample('head', n, lambda t: (-1.4 * A.wave(t, 1.0), 9 * A.pulse(t, 0.55, 0.8), 0), step=3)
        cb.sample('root', n, lambda t: (0.004 * A.wave(t, 0.5), 0, 0), kind='loc', step=4)
        made.append(cb.end())

    if want('idle_happy'):
        n = 90
        cb.begin('idle_happy', n, loop=True)
        cb.sample('hips', n, lambda t: (0, 0, 0.012 * A.bounce(t, 3)), kind='loc', step=2)
        squash(n, lambda t: 1.0 + 0.04 * A.wave(t, 3.0, 0.25))
        cb.sample('chest', n, lambda t: (2.5 * A.wave(t, 3.0), 0, 0), step=2)
        cb.sample('head', n, lambda t: (-3 * A.wave(t, 3.0), 8 * A.wave(t, 1.0), 0), step=2)
        ears(n, -6, 6, 3.0)
        tail(n, 18, 28, 3.0)
        stand(n)
        cb.face(1, 'happy')
        made.append(cb.end())

    if want('idle_tired'):
        n = 150
        cb.begin('idle_tired', n, loop=True)
        breathe(n, rate=0.6, depth=1.6, tail=0.3, ear=0.3)
        cb.sample('head', n, lambda t: (18 - 1.5 * A.wave(t, 0.6), 0, 0), step=3)
        cb.sample('neck', n, lambda t: (10, 0, 0), step=10)
        ears(n, 18, 2, 0.6)
        tail(n, -14, 4, 0.6)
        cb.sample('root', n, lambda t: (0, 1.6 * A.wave(t, 0.3), 0), step=4)
        stand(n)
        cb.face(1, 'tired')
        made.append(cb.end())

    if want('idle_sad'):
        n = 150
        cb.begin('idle_sad', n, loop=True)
        breathe(n, rate=0.7, depth=1.2, tail=0.2, ear=0.2)
        cb.sample('head', n, lambda t: (24, 0, -10 + 3 * A.pulse(t, 0.5, 0.7)), step=3)
        cb.sample('neck', n, lambda t: (8, 0, 0), step=10)
        cb.sample('hips', n, lambda t: (0, 0, -0.012 + 0.003 * A.wave(t, 0.7)), kind='loc', step=3)
        ears(n, 26, 1.5, 0.7)
        tail(n, -22, 3, 0.7)
        stand(n)
        cb.face(1, 'sad')
        made.append(cb.end())

    if want('idle_sick'):
        n = 150
        cb.begin('idle_sick', n, loop=True)
        breathe(n, rate=0.8, depth=1.3, tail=0.2, ear=0.2)
        cb.sample('root', n, lambda t: (0, 3.5 * A.wave(t, 0.8), 0), step=2)
        cb.sample('head', n, lambda t: (14, 2 * A.wave(t, 6.0) * A.pulse(t, 0.3, 0.45), 0), step=1)
        ears(n, 22, 2, 0.8)
        tail(n, -16, 2, 0.8)
        stand(n)
        cb.face(1, 'sick')
        made.append(cb.end())

    if want('sleep'):
        n = 150
        cb.begin('sleep', n, loop=True)
        cb.sample('hips', n, lambda t: (0, 0, -(hz - 0.1) + 0.003 * A.wave(t, 0.4)), kind='loc', step=4)
        cb.sample('chest', n, lambda t: (3 * A.wave(t, 0.4), 0, 0), step=4)
        cb.sample('neck', n, lambda t: (14, 0, 0), step=20)
        cb.sample('head', n, lambda t: (22, 0, 24), step=20)
        ears(n, 20, 1, 0.4)
        cb.sample('tail.1', n, lambda t: (-8, 0, 40), step=20)
        cb.sample('tail.2', n, lambda t: (0, 0, 40), step=20)
        cb.sample('tail.3', n, lambda t: (0, 0, 30), step=20)
        for leg in ('FL', 'FR'):
            legs.pose(leg, 1, -75, 125, -50)
            legs.pose(leg, 1 + n, -75, 125, -50)
        for leg in ('BL', 'BR'):
            legs.pose(leg, 1, 70, -125, 55)
            legs.pose(leg, 1 + n, 70, -125, 55)
        cb.face(1, 'sleepy')
        made.append(cb.end())

    if want('eat'):
        n = 60
        cb.begin('eat', n, loop=True)
        dip = lambda t: A.step_ease(t, 0.0, 0.25) * (1 - A.step_ease(t, 0.8, 1.0))
        cb.sample('neck', n, lambda t: (22 * dip(t), 0, 0), step=2)
        cb.sample('head', n, lambda t: (30 * dip(t), 0, 0), step=2)
        cb.sample('chest', n, lambda t: (6 * dip(t), 0, 0), step=2)
        cb.sample('hips', n, lambda t: (0, -0.02 * dip(t), -0.01 * dip(t)), kind='loc', step=2)
        cb.sample('jaw', n, lambda t: (14 * dip(t) * abs(math.sin(t * 2 * math.pi * 3)), 0, 0), step=1)
        ears(n, 6, 3, 3.0)
        tail(n, 6, 10, 1.0)
        stand(n)
        made.append(cb.end())

    if want('pet'):
        n = 75
        cb.begin('pet', n, loop=True)
        cb.sample('head', n, lambda t: (6, 14 + 2 * A.wave(t, 2.0), 4), step=2)
        cb.sample('neck', n, lambda t: (4, 4, 0), step=10)
        cb.sample('hips', n, lambda t: (0, 0, 0.008 * A.bounce(t, 2)), kind='loc', step=2)
        cb.sample('chest', n, lambda t: (0.8 * A.wave(t, 8.0), 0, 0), step=1)
        ears(n, 12, 3, 2.0)
        tail(n, 14, 22, 2.0)
        stand(n)
        cb.face(1, 'happy')
        made.append(cb.end())

    if want('look_around'):
        n = 90
        cb.begin('look_around', n, loop=True)
        yaw = lambda t: 35 * A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56)) - 35 * A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        cb.sample('head', n, lambda t: (0, 0, yaw(t)), step=1)
        cb.sample('neck', n, lambda t: (0, 0, yaw(t) * 0.25), step=1)
        cb.sample('chest', n, lambda t: (0, 0, yaw(t) * 0.12), step=1)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-yaw(t) * 0.15, sx * 2, 0), step=1)
        tail(n, 8, 6, 1.0)
        stand(n)
        made.append(cb.end())

    if want('hop'):
        n = 24
        cb.begin('hop', n, loop=False)
        air = lambda t: A.pulse(t, 0.28, 0.82)
        cb.sample('root', n, lambda t: (0, 0, 0.15 * air(t)), kind='loc', step=1)
        squash(n, lambda t: 1.0 - 0.14 * A.pulse(t, 0.0, 0.26) + 0.12 * A.pulse(t, 0.28, 0.6) - 0.16 * A.pulse(t, 0.8, 0.98))
        cb.sample('chest', n, lambda t: (-8 * air(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-6 * air(t) + 10 * A.pulse(t, 0.0, 0.26), 0, 0), step=1)
        ears(n, 4, 0)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-30 * air(t) + 25 * A.pulse(t, 0.8, 1.0), sx * 4, 0), step=1)
        cb.sample('tail.1', n, lambda t: (22 * air(t), 0, 0), step=1)
        cb.sample('tail.2', n, lambda t: (10 * air(t), 0, 0), step=1)
        for leg in LEGS:
            tuck = -28 if leg[0] == 'F' else 30
            cb.sample(f'thigh.{leg}', n, lambda t, tuck=tuck: (tuck * air(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t, tuck=tuck: (-tuck * 1.4 * air(t), 0, 0), step=1)
            cb.sample(f'foot.{leg}', n, lambda t, tuck=tuck: (tuck * 0.4 * air(t), 0, 0), step=1)
        cb.marker('land', 20)
        made.append(cb.end())

    if want('celebrate'):
        n = 60
        cb.begin('celebrate', n, loop=True)
        air = lambda t: A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        cb.sample('root', n, lambda t: (0, 0, 0.11 * air(t)), kind='loc', step=1)
        squash(n, lambda t: 1.0 + 0.1 * air(t) - 0.12 * (A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)))
        cb.sample('root', n, lambda t: (0, 9 * A.wave(t, 3.0) * A.step_ease(t, 0.75, 0.85) * (1 - A.step_ease(t, 0.95, 1.0)), 0), step=1)
        cb.sample('head', n, lambda t: (-8 * air(t), 10 * A.wave(t, 2.0), 0), step=1)
        ears(n, -8, 12, 3.0)
        tail(n, 22, 30, 4.0)
        for leg in LEGS:
            tuck = -22 if leg[0] == 'F' else 24
            cb.sample(f'thigh.{leg}', n, lambda t, tuck=tuck: (tuck * air(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t, tuck=tuck: (-tuck * 1.3 * air(t), 0, 0), step=1)
        cb.face(1, 'happy')
        cb.marker('land', 22)
        cb.marker('land', 43)
        made.append(cb.end())

    # ---- moving
    if want('walk'):
        n = 30
        stride = P.get('stride', 0.18)
        cb.begin('walk', n, loop=True, root_speed=stride / (0.6 * n / A.FPS))
        plants = gait(legs, n, stride, 0.05, {'FL': 0.0, 'BR': 0.25, 'FR': 0.5, 'BL': 0.75}, body_bob=0.008)
        cb.sample('chest', n, lambda t: (2.5 * A.wave(t, 2.0), 0, 2 * A.wave(t, 1.0)), step=2)
        cb.sample('hips', n, lambda t: (0, 0, 0), kind='loc', step=15)
        cb.sample('head', n, lambda t: (-2.5 * A.wave(t, 2.0, 0.5), 0, 0), step=2)
        ears(n, 2, 5, 2.0)
        tail(n, 6, 14, 1.0)
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    if want('run'):
        n = 20
        stride = P.get('stride', 0.18) * 1.6
        cb.begin('run', n, loop=True, root_speed=stride / (0.45 * n / A.FPS))
        plants = gait(legs, n, stride, 0.09, {'FL': 0.0, 'FR': 0.1, 'BL': 0.5, 'BR': 0.6}, stance=0.45,
                      bob_fn=lambda t: 0.03 * A.pulse(t, 0.55, 1.0))
        cb.sample('root', n, lambda t: (0, 0, 0.03 * A.pulse(t, 0.55, 1.0)), kind='loc', step=1)
        squash(n, lambda t: 1.0 + 0.08 * A.pulse(t, 0.55, 1.0) - 0.08 * A.pulse(t, 0.0, 0.3))
        cb.sample('chest', n, lambda t: (-9 * A.wave(t, 1.0, 0.25), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-4 + 5 * A.wave(t, 1.0, 0.5), 0, 0), step=1)
        ears(n, -16, 10, 1.0)
        tail(n, 4, 8, 1.0)
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    # ---- scenes
    def sit_pose(frame: int, k: float = 1.0) -> None:
        cb.rot('chest', frame, x=-18 * k)
        cb.rot('spine', frame, x=-8 * k)
        cb.rot('neck', frame, x=6 * k)
        cb.loc('hips', frame, 0, 0.03 * k, -(hz - 0.1) * k)
        for leg in ('BL', 'BR'):
            legs.pose(leg, frame, -82 * k, 128 * k, -46 * k, splay=6 * k)
        for leg in ('FL', 'FR'):
            legs.pose(leg, frame, 10 * k, -4 * k, -6 * k)
        cb.rot('tail.1', frame, x=-10 * k, z=25 * k)
        cb.rot('tail.2', frame, z=30 * k)

    if want('sit_down'):
        n = 24
        cb.begin('sit_down', n, loop=False, hold=True)
        for f in range(1, n + 2):
            sit_pose(f, C.ease_in_out((f - 1) / n))
        cb.sample('head', n, lambda t: (4 * A.pulse(t, 0.2, 0.9), 0, 0), step=2)
        made.append(cb.end())

    if want('sit'):
        n = 120
        cb.begin('sit', n, loop=True)
        sit_pose(1)
        sit_pose(1 + n)
        cb.sample('chest', n, lambda t: (-18 + 2 * A.wave(t, 1.0), 0, 0), step=3)
        cb.sample('head', n, lambda t: (-1.5 * A.wave(t, 1.0), 8 * A.pulse(t, 0.5, 0.75), 0), step=3)
        ears(n, 6, 2.5, 1.0)
        cb.sample('tail.3', n, lambda t: (0, 0, 12 * A.wave(t, 1.5)), step=2)
        cb.sample('tail.2', n, lambda t: (0, 0, 30 + 6 * A.wave(t, 1.5, -0.1)), step=2)
        made.append(cb.end())

    if want('dizzy'):
        n = 60
        cb.begin('dizzy', n, loop=True)
        cb.sample('head', n, lambda t: (12 * math.cos(t * 4 * math.pi), 0, 16 * math.sin(t * 4 * math.pi)), step=1)
        cb.sample('neck', n, lambda t: (4 * math.cos(t * 4 * math.pi), 0, 6 * math.sin(t * 4 * math.pi)), step=1)
        cb.sample('root', n, lambda t: (3 * math.sin(t * 4 * math.pi), 5 * math.cos(t * 4 * math.pi), 0), step=1)
        ears(n, 18, 4, 2.0)
        tail(n, -8, 6, 2.0)
        stand(n, splay=8)
        cb.face(1, 'dizzy')
        made.append(cb.end())

    # ---- battle
    if want('battle_idle'):
        n = 40
        cb.begin('battle_idle', n, loop=True)
        cb.sample('hips', n, lambda t: (0, 0, 0.012 * A.bounce(t, 2)), kind='loc', step=1)
        squash(n, lambda t: 1.0 + 0.03 * A.wave(t, 2.0, 0.25))
        cb.sample('chest', n, lambda t: (4 + 1.5 * A.wave(t, 2.0), 0, 0), step=2)
        cb.sample('head', n, lambda t: (-6 - 1.5 * A.wave(t, 2.0), 0, 0), step=2)
        ears(n, -10, 3, 2.0)
        tail(n, 22, 8, 2.0)
        stand(n, splay=9)
        made.append(cb.end())

    if want('step_fwd'):
        n = 24
        stride = P.get('stride', 0.18) * 0.8
        cb.begin('step_fwd', n, loop=True, root_speed=stride / (0.6 * n / A.FPS))
        plants = gait(legs, n, stride, 0.05, {'FL': 0.0, 'BR': 0.25, 'FR': 0.5, 'BL': 0.75}, body_bob=0.008)
        cb.sample('chest', n, lambda t: (5 + 2 * A.wave(t, 2.0), 0, 0), step=2)
        cb.sample('head', n, lambda t: (-6 - 2 * A.wave(t, 2.0, 0.5), 0, 0), step=2)
        ears(n, -8, 4, 2.0)
        tail(n, 20, 10, 2.0)
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    if want('step_back'):
        n = 24
        stride = P.get('stride', 0.18) * 0.65
        cb.begin('step_back', n, loop=True, root_speed=stride / (0.6 * n / A.FPS))
        plants = gait(legs, n, stride, 0.045, {'FL': 0.0, 'BR': 0.25, 'FR': 0.5, 'BL': 0.75}, body_bob=0.006, reverse=True)
        cb.sample('chest', n, lambda t: (-4 + 2 * A.wave(t, 2.0), 0, 0), step=2)
        cb.sample('head', n, lambda t: (-2 - 2 * A.wave(t, 2.0, 0.5), 0, 0), step=2)
        ears(n, 4, 4, 2.0)
        tail(n, 10, 8, 2.0)
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    if want('dash'):
        n = 20
        stride = P.get('stride', 0.18) * 2.0
        cb.begin('dash', n, loop=True, root_speed=stride / (0.4 * n / A.FPS))
        plants = gait(legs, n, stride, 0.1, {'FL': 0.0, 'FR': 0.08, 'BL': 0.5, 'BR': 0.58}, stance=0.4,
                      bob_fn=lambda t: 0.035 * A.pulse(t, 0.5, 1.0))
        cb.sample('root', n, lambda t: (0, 0, 0.035 * A.pulse(t, 0.5, 1.0)), kind='loc', step=1)
        cb.sample('root', n, lambda t: (1.0 / 1.1, 1.14, 0.9), kind='scale', step=20)
        cb.sample('chest', n, lambda t: (-10 * A.wave(t, 1.0, 0.25), 0, 0), step=1)
        cb.sample('neck', n, lambda t: (-10, 0, 0), step=10)
        cb.sample('head', n, lambda t: (-2 + 4 * A.wave(t, 1.0, 0.5), 0, 0), step=1)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-38, sx * 6, 0), step=10)
            cb.sample(f'ear.{s}.2', n, lambda t, sx=sx: (-20, sx * 4, 0), step=10)
        tail(n, -6, 6, 1.0)
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    if want('strike'):
        n = 24
        cb.begin('strike', n, loop=False)
        ant = lambda t: A.pulse(t, 0.0, 0.42)          # wind-up
        go = lambda t: A.pulse(t, 0.3, 0.75)            # lunge
        cb.sample('hips', n, lambda t: (0, 0.05 * ant(t) - 0.12 * go(t), 0.02 * go(t)), kind='loc', step=1)
        cb.sample('chest', n, lambda t: (-14 * ant(t) + 18 * go(t), 0, 0), step=1)
        cb.sample('neck', n, lambda t: (-8 * ant(t) + 10 * go(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-10 * ant(t) + 22 * go(t), 0, 0), step=1)
        cb.sample('jaw', n, lambda t: (28 * go(t), 0, 0), step=1)
        squash(n, lambda t: 1.0 - 0.08 * ant(t) + 0.08 * go(t))
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (18 * ant(t) - 30 * go(t), sx * 4, 0), step=1)
        cb.sample('tail.1', n, lambda t: (16 * ant(t) - 6 * go(t), 0, 0), step=1)
        for leg in ('FL', 'FR'):
            cb.sample(f'thigh.{leg}', n, lambda t: (-30 * go(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t: (18 * go(t), 0, 0), step=1)
        for leg in ('BL', 'BR'):
            cb.sample(f'thigh.{leg}', n, lambda t: (-14 * ant(t) + 10 * go(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t: (20 * ant(t) - 12 * go(t), 0, 0), step=1)
        cb.marker('impact', 13)
        cb.face(1, 'angry')
        cb.face(20, 'neutral')
        made.append(cb.end())

    if want('cast'):
        n = 36
        cb.begin('cast', n, loop=False)
        up = lambda t: A.step_ease(t, 0.0, 0.3) * (1 - A.step_ease(t, 0.7, 1.0))
        cb.sample('chest', n, lambda t: (-38 * up(t), 0, 0), step=1)
        cb.sample('spine', n, lambda t: (-10 * up(t), 0, 0), step=1)
        cb.sample('neck', n, lambda t: (12 * up(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (8 * up(t) + 2 * A.wave(t, 6.0) * A.pulse(t, 0.3, 0.7), 0, 0), step=1)
        cb.sample('hips', n, lambda t: (0, 0.03 * up(t), 0.01 * up(t)), kind='loc', step=1)
        for leg in ('FL', 'FR'):
            cb.sample(f'thigh.{leg}', n, lambda t: (-60 * up(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t: (-25 * up(t), 0, 0), step=1)
            cb.sample(f'foot.{leg}', n, lambda t: (40 * up(t), 0, 0), step=1)
        for leg in ('BL', 'BR'):
            cb.sample(f'thigh.{leg}', n, lambda t: (20 * up(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t: (-28 * up(t), 0, 0), step=1)
            cb.sample(f'foot.{leg}', n, lambda t: (8 * up(t), 0, 0), step=1)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-22 * up(t), sx * (4 + 6 * A.wave(t, 4.0) * up(t)), 0), step=1)
        tail(n, 14, 6, 1.0)
        cb.marker('release', 20)
        cb.face(1, 'strain')
        cb.face(28, 'neutral')
        made.append(cb.end())

    if want('shove'):
        n = 24
        cb.begin('shove', n, loop=False)
        ant = lambda t: A.pulse(t, 0.0, 0.36)
        go = lambda t: A.pulse(t, 0.28, 0.7)
        cb.sample('hips', n, lambda t: (0, 0.04 * ant(t) - 0.09 * go(t), 0), kind='loc', step=1)
        cb.sample('chest', n, lambda t: (-6 * ant(t) + 8 * go(t), 0, -14 * ant(t) + 16 * go(t)), step=1)
        cb.sample('head', n, lambda t: (6 * go(t), 0, 10 * go(t)), step=1)
        squash(n, lambda t: 1.0 - 0.06 * ant(t) + 0.05 * go(t))
        for leg in ('FL', 'FR'):
            cb.sample(f'thigh.{leg}', n, lambda t: (-22 * go(t), 0, 0), step=1)
        for leg in ('BL', 'BR'):
            cb.sample(f'thigh.{leg}', n, lambda t: (-12 * ant(t) + 14 * go(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t: (16 * ant(t) - 10 * go(t), 0, 0), step=1)
        ears(n, 0, 0)
        cb.marker('impact', 10)
        made.append(cb.end())

    if want('hit'):
        n = 15
        cb.begin('hit', n, loop=False)
        k = lambda t: A.pulse(t, 0.0, 0.8)
        cb.sample('hips', n, lambda t: (0, 0.05 * k(t), 0.01 * k(t)), kind='loc', step=1)
        cb.sample('chest', n, lambda t: (-10 * k(t), 0, 0), step=1)
        cb.sample('neck', n, lambda t: (-8 * k(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-16 * k(t), 0, 0), step=1)
        squash(n, lambda t: 1.0 - 0.06 * k(t))
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (28 * k(t), sx * 3, 0), step=1)
        cb.sample('tail.1', n, lambda t: (-10 * k(t), 0, 0), step=1)
        cb.face(1, 'surprised')
        cb.face(12, 'neutral')
        made.append(cb.end())

    if want('hit_heavy'):
        n = 24
        cb.begin('hit_heavy', n, loop=False)
        k = lambda t: A.pulse(t, 0.0, 0.55)
        rec = lambda t: A.step_ease(t, 0.5, 1.0)
        cb.sample('hips', n, lambda t: (0, 0.12 * k(t), 0.05 * k(t)), kind='loc', step=1)
        cb.sample('chest', n, lambda t: (-22 * k(t), 0, 0), step=1)
        cb.sample('neck', n, lambda t: (-12 * k(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-26 * k(t), 0, 0), step=1)
        cb.sample('root', n, lambda t: (0, 7 * math.sin(t * 2 * math.pi * 3) * (1 - rec(t)) * A.step_ease(t, 0.1, 0.3), 0), step=1)
        squash(n, lambda t: 1.0 - 0.12 * k(t))
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (36 * k(t), sx * 3, 0), step=1)
            cb.sample(f'ear.{s}.2', n, lambda t, sx=sx: (20 * k(t), 0, 0), step=1)
        cb.sample('tail.1', n, lambda t: (-18 * k(t), 0, 0), step=1)
        for leg in LEGS:
            cb.sample(f'thigh.{leg}', n, lambda t, s=(-1 if leg[0] == 'F' else 1): (s * 16 * k(t), 0, 0), step=1)
        stand(n, splay=10)
        cb.face(1, 'strain')
        cb.face(18, 'neutral')
        made.append(cb.end())

    if want('ko'):
        n = 36
        cb.begin('ko', n, loop=False, hold=True)
        wob = lambda t: (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = lambda t: A.step_ease(t, 0.4, 0.82)
        cb.sample('root', n, lambda t: (0, 10 * math.sin(t * 2 * math.pi * 2.5) * wob(t) + 78 * fall(t), 0), step=1)
        cb.sample('hips', n, lambda t: (0, 0, -(hz - 0.14) * fall(t)), kind='loc', step=1)
        cb.sample('head', n, lambda t: (14 * fall(t), 0, 18 * fall(t)), step=1)
        cb.sample('neck', n, lambda t: (6 * fall(t), 0, 0), step=1)
        for leg in LEGS:
            s = -1 if leg[0] == 'F' else 1
            cb.sample(f'thigh.{leg}', n, lambda t, s=s: (s * 30 * fall(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t, s=s: (-s * 20 * fall(t), 0, 0), step=1)
        ears(n, 24, 0)
        cb.sample('tail.1', n, lambda t: (-14 * fall(t), 0, 10 * fall(t)), step=1)
        cb.face(1, 'strain')
        cb.face(20, 'dizzy')
        made.append(cb.end())

    if want('win'):
        n = 60
        cb.begin('win', n, loop=True)
        air = lambda t: A.pulse(t, 0.04, 0.36)
        spin = lambda t: 360 * A.step_ease(t, 0.42, 0.82)
        cb.sample('root', n, lambda t: (0, 0, 0.14 * air(t)), kind='loc', step=1)
        cb.sample('root', n, lambda t: (0, 0, spin(t)), step=1)
        squash(n, lambda t: 1.0 + 0.1 * air(t) - 0.12 * A.pulse(t, 0.34, 0.44) + 0.04 * A.wave(t, 4.0) * A.step_ease(t, 0.84, 0.9))
        cb.sample('chest', n, lambda t: (-8 * air(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-10 * air(t), 10 * A.wave(t, 2.0) * A.step_ease(t, 0.84, 0.9), 0), step=1)
        ears(n, -8, 12, 3.0)
        tail(n, 26, 30, 4.0)
        for leg in LEGS:
            tuck = -24 if leg[0] == 'F' else 26
            cb.sample(f'thigh.{leg}', n, lambda t, tuck=tuck: (tuck * air(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t, tuck=tuck: (-tuck * 1.3 * air(t), 0, 0), step=1)
        cb.face(1, 'happy')
        cb.marker('land', 22)
        made.append(cb.end())

    return made


STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
