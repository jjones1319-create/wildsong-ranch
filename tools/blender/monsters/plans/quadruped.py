"""The quadruped body plan (ART_2_PLAN §4): rig template, sockets and the clip generators.

Proportions come from the breed recipe (`P`, metres; the monster faces −Y, Z is up). Rotations in the clip
generators are world-aligned degrees relative to the parent bone: +x nods forward/down (for a forward or
upward bone) and swings a leg backward; +z turns toward the monster's left; +y rolls.

Options in `P` (tools/blender/monsters/breeds/RECIPE.md; every default is Puddlepup's, whose output is unchanged):
  size_k      the breed's size relative to Puddlepup (HEIGHT_UNITS / 150; 1.0): scales every absolute offset the
              rig and the clips add (bone stubs, hop heights, body bobs, foot lifts, lunges, the sleep / sit / ko drop)
  tail_bones  bones in the tail chain tail.1..N (3); the clips spread the 3-bone motion over the chain
  tail_points tail_bones + 1 points for a curved tail (a spiral); else a straight tail_base + tail_dir · tail_len
  ears        False: no ear bones (their keys are skipped by the build's clip builder)
  hooves      a short hoof bone standing on its tip, legs under the body (less splay) and a hoof flick in the swing
  manes       spring chains [{'name', 'parent', 'points'}] → bones <name>.1..N, springs kind 'mane', keyed sway
  props       rigid attach bones [{'name', 'parent', 'head', 'tail'}] → bone prop.<name> (never keyed), socket_<name>
Batch 2 (each off by default; RECIPE.md has the details):
  neck_bones  bones in the neck chain (1 = the bone `neck`; N > 1 = neck.1..N); the clips spread the 1-bone motion over it
  neck_points neck_bones + 1 points for a curved neck (else a straight line from the chest to the head)
  trunk       {'points', 'parent', 'curl', 'bud'} → a chain trunk.1..N (springs kind 'trunk'), keyed curls; 'bud' adds
              petal bones bud.1..n at the tip that open in the happy, winning and surprised clips
  wings       {'parent', 'shoulder', 'elbow', 'wrist', 'fingers', 'attach', 'spread', ...} → per side wing.<S>.1, .2 and
              .f1..fK, folded at rest (the modelled pose), opened toward `spread` in win, cast, strike and the big moves
  body_width  half the body's width at the belly: the spine's height when the monster lies on its side in ko
              (default 1.35 x the widest leg's x)
The shared clips were reworked after the Nov 7 review (strike a stretched pounce, hit_heavy a braced recoil with the head
ducking aside, ko curled on its side facing the monster's left, win with the legs tucked); names, lengths, markers and
root speeds are unchanged.
"""
from __future__ import annotations

import math

from mathutils import Matrix, Quaternion, Vector

from lib import anim as A
from lib import common as C
from lib import ultra as U
from lib.rig import BoneSpec

PLAN = 'quadruped'
LEGS = ['FL', 'FR', 'BL', 'BR']

# Puddlepup's chains (Art 2.0's build.py reads this; the Ultra build calls springs(P))
SPRINGS = [
    {'kind': 'ear', 'chain': ['ear.L.1', 'ear.L.2']},
    {'kind': 'ear', 'chain': ['ear.R.1', 'ear.R.2']},
    {'kind': 'tail', 'chain': ['tail.1', 'tail.2', 'tail.3']},
]
HOOF_SPLAY = 0.35          # hooved legs stand under the body: their splay is this share of a paw's
KO_ROLL = 80.0             # degrees the body rolls onto its right side in ko (build_ultra measures body_width at it)
HOOF_FLICK = 35.0          # degrees the hoof curls back at the top of a swing


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def has_ears(P: dict) -> bool:
    return bool(P.get('ears', True))


def ankle_of(P: dict) -> float:
    return P.get('ankle_z', 0.06 * size_of(P) if P.get('hooves') else 0.035)


def hocked(P: dict, leg: str) -> dict | None:
    """A hind leg with a bent hock (digitigrade: the knee forward, the hock angled back and up off the ground, the long
    foot down to the paw), when `hocks` is set; the front legs and every leg without it: None. `hocks` = True or
    {'knee': (dy, dz), 'hock': (dy, dz), 'paw': (dy, dz)}, each as shares of the hip's height from the hip (−dy =
    forward, the paw's dz = −1 puts it on the ground). Returns the joints relative to (x, y, 0) of the leg."""
    h = P.get('hocks')
    if not h or leg[0] != 'B':
        return None
    h = {} if h is True else h
    _x, _y, hz = P['legs'][leg]
    out = {}
    for k, d in (('knee', (-0.16, -0.42)), ('hock', (0.14, -0.72)), ('paw', (0.08, -1.0))):
        dy, dz = h.get(k, d)
        out[k] = Vector((0.0, dy * hz, hz + dz * hz))
    return out


def foot_len_of(P: dict) -> float:
    return P.get('foot_len', 0.06 * size_of(P) if P.get('hooves') else 0.12)


def tail_names(P: dict) -> list[str]:
    return [f'tail.{i + 1}' for i in range(int(P.get('tail_bones', 3)))]


def tail_points(P: dict) -> list[Vector]:
    """The tail chain's bones + 1 points (heads, then the last tail)."""
    n = len(tail_names(P))
    if P.get('tail_points'):
        pts = [Vector(p) for p in P['tail_points']]
        if len(pts) != n + 1:
            raise ValueError(f'tail_points has {len(pts)} points; tail_bones = {n} needs {n + 1}')
        return pts
    tb = Vector(P['tail_base'])
    td = Vector(P.get('tail_dir', (0, 1, -0.1))).normalized()
    tl = P['tail_len']
    return [tb + td * tl * k / n for k in range(n + 1)]


def manes(P: dict) -> list[dict]:
    out = []
    for m in P.get('manes', []) or []:
        pts = [Vector(p) for p in m['points']]
        if len(pts) < 2:
            raise ValueError(f"mane {m.get('name')}: needs at least 2 points")
        out.append({'name': m.get('name', 'mane'), 'parent': m.get('parent', 'neck'), 'points': pts,
                    'bones': [f"{m.get('name', 'mane')}.{i + 1}" for i in range(len(pts) - 1)],
                    # batch 2 (opt-in): `counter` 0..1 = how much of the head's / neck's keyed rotation the chain's first
                    # bone takes back in hit, hit_heavy and ko (a hanging beard or scarf stays hanging when the head
                    # jerks); `cap` = the most degrees any one bone of the chain turns in a keyed clip (no quills)
                    'counter': float(m.get('counter', 0.0)), 'cap': m.get('cap')})
    return out


def neck_names(P: dict) -> list[str]:
    """The neck chain: ['neck'] (Puddlepup's one bone), or neck.1..N for neck_bones = N > 1."""
    n = int(P.get('neck_bones', 1))
    return ['neck'] if n <= 1 else [f'neck.{i + 1}' for i in range(n)]


def neck_points(P: dict) -> list[Vector]:
    """The neck chain's bones + 1 points: the recipe's neck_points, else a straight line from the chest's tip to the
    head's base (where Puddlepup's single neck bone runs)."""
    n = len(neck_names(P))
    if P.get('neck_points'):
        pts = [Vector(p) for p in P['neck_points']]
        if len(pts) != n + 1:
            raise ValueError(f'neck_points has {len(pts)} points; neck_bones = {n} needs {n + 1}')
        return pts
    sk = size_of(P)
    a = Vector(P['chest']) + Vector((0, -0.12 * sk, 0.0))
    b = Vector(P['head_c']) + Vector((0, 0.06 * sk, -P['head_r'] * 0.55))
    return [a + (b - a) * (k / n) for k in range(n + 1)]


def trunk_of(P: dict) -> dict | None:
    """The trunk option, filled in: points (Vectors), parent, bones trunk.1..N, curl (amplitude factor), bud (or None)."""
    t = P.get('trunk')
    if not t:
        return None
    pts = [Vector(p) for p in t['points']]
    if len(pts) < 3:
        raise ValueError('trunk: needs at least 3 points (2 bones)')
    name = t.get('name', 'trunk')
    return {'name': name, 'points': pts, 'parent': t.get('parent', 'head'), 'curl': float(t.get('curl', 1.0)),
            'bones': [f'{name}.{i + 1}' for i in range(len(pts) - 1)], 'bud': t.get('bud'),
            'counter': float(t.get('counter', 0.0)), 'cap': t.get('cap')}


def bud_petals(P: dict) -> list[tuple[str, Vector, Vector, Vector]]:
    """The bud's petal bones at the trunk's tip: (bone, head, tail, opening axis). Closed at rest (each petal leans
    `closed` degrees off the trunk's axis); opening turns it `open` degrees outward about its axis."""
    tr = trunk_of(P)
    if not tr or not tr['bud']:
        return []
    b = tr['bud']
    n = int(b.get('petals', 5))
    tip, prev = tr['points'][-1], tr['points'][-2]
    d = (tip - prev).normalized()
    ref = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 0, 1))
    e1 = d.cross(ref).normalized()
    e2 = d.cross(e1).normalized()
    c = math.radians(float(b.get('closed', 14.0)))
    L = float(b.get('length', 0.05 * size_of(P)))
    roll = math.radians(float(b.get('roll', 0.0)))
    out = []
    for i in range(n):
        ph = roll + 2 * math.pi * i / n
        r = e1 * math.cos(ph) + e2 * math.sin(ph)
        out.append((f"{b.get('name', 'bud')}.{i + 1}", tip.copy(), tip + (d * math.cos(c) + r * math.sin(c)) * L, d.cross(r).normalized()))
    return out


STRIKE_STYLES = ('pounce', 'charge', 'kick', 'swipe', 'slam', 'lunge')


def swipe_reach(P: dict, leg: str, curl: float = 15.0) -> tuple[float, float, float]:
    """The swipe's (thigh, shin, foot) x rotations for a front leg: the arm straight, `phi` degrees above level (aimed
    at cheek height from the crouched shoulder, 35–60°, and no higher than leaves the paw clear in front of the face), the
    paw in line with it and its tip curled `curl` degrees down. From the rig's own rest leg (bones: the hip, the knee
    knee_back forward, the ankle, the toe); x rotations add up down the chain."""
    _x, y, hz = P['legs'][leg]
    kb = P.get('knee_back', 0.03)
    ank = ankle_of(P)
    l1 = (hz - ank) * 0.52
    fl = foot_len_of(P)
    toe_z = 0.0 if P.get('hooves') else ank * 0.6
    a_t = math.degrees(math.atan2(kb, l1))
    a_s = math.degrees(math.atan2(-kb, hz - l1 - ank))
    a_f = math.degrees(math.atan2(fl, ank - toe_z))
    arm = math.hypot(kb, l1) + math.hypot(kb, hz - l1 - ank) + math.hypot(fl, ank - toe_z)
    hc, hr = P['head_c'], P['head_r']
    phi = math.degrees(math.asin(max(-1.0, min(1.0, (hc[2] - 0.3 * hr - 0.9 * hz) / arm))))
    clear = (y - (hc[1] - 1.8 * hr)) / arm           # the face's front (and its lean), ahead of the shoulder, as a share of the arm
    if clear < 1.0:
        phi = min(phi, math.degrees(math.acos(max(0.0, clear))))
    phi = max(35.0, min(60.0, phi + float(P.get('swipe_lift', 0.0))))     # rig_p()['swipe_lift']: degrees more (or less)
    return (a_t - 90.0 - phi, a_s - a_t, a_f - a_s + curl)


# cast on a trunk rig: the chest's rear (degrees; 0 keeps the other foreleg planted), the trunk's raise from the base and
# the tip's turn back to forward (Petalphant: the tip about 25 degrees above level, out in front at head height)
CAST_TRUNK_REAR = 0
CAST_TRUNK_RAISE = 180
CAST_TRUNK_TIP = 190


def strike_style(P: dict) -> str:
    """'pounce' (the stretched leap, front paws reaching, a bite), 'charge' (horned breeds: head low, horns first) or
    'kick' (Stripeneck: a spinning double back-hoof kick), 'swipe' (cats: one forepaw rakes at head height) or 'slam'
    (Cobblemaw: rears up on the hind legs, both front paws slam down) or 'lunge' (the body drives forward low with the head
    leading and the wings spread; the default for a rig with wings, where the pounce's long flat leap read as a
    belly-flop sprawl)."""
    st = P.get('strike_style', 'lunge' if P.get('wings') else 'pounce')
    if st not in STRIKE_STYLES:
        raise ValueError(f'strike_style {st!r}: one of {STRIKE_STYLES}')
    return st


def body_halfwidth(P: dict) -> float:
    """Half the body's width at the belly (metres): how high the spine lies off the ground when the monster is down on
    its side (ko). The recipe's `body_width`, else 1.35 x the widest leg's x (Puddlepup 0.23 m)."""
    return float(P.get('body_width', 1.35 * max(abs(P['legs'][leg][0]) for leg in LEGS)))


def wings_of(P: dict) -> dict | None:
    return P.get('wings') or None


def wing_specs(P: dict) -> list[tuple[str, Vector, Vector, str]]:
    """(bone, head, tail, parent) for both wings at rest (folded), left first."""
    w = wings_of(P)
    if not w:
        return []
    return [(b, Vector(h), Vector(t), par) for side in (1, -1) for b, h, t, par in U.wing_bones(w, side)]


def _frame(a: Vector, b: Vector) -> Matrix:
    """An orthonormal frame (columns) with x along a and z normal to the plane of a and b."""
    x = a.normalized()
    z = x.cross(b)
    if z.length < 1e-8:
        z = x.orthogonal()
    z.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def wing_spread_quats(P: dict, side: int) -> list[tuple[str, Quaternion]]:
    """Each wing bone's rotation (relative to its parent, world-aligned at rest, as ClipBuilder.rot keys them) that
    takes the folded wing to the spread pose: the arm by frames (its direction and the arm's plane), the hand by its
    direction and the fingers' fan, each finger by a swing. Exact at the end points; the clips blend with slerp."""
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


def springs(P: dict) -> list[dict]:
    """The spring chains the runtime may drive: the ears, the tail and every mane (and a trunk)."""
    out = []
    if has_ears(P):
        out += [{'kind': 'ear', 'chain': ['ear.L.1', 'ear.L.2']}, {'kind': 'ear', 'chain': ['ear.R.1', 'ear.R.2']}]
    if tail_names(P):
        out.append({'kind': 'tail', 'chain': tail_names(P)})
    for m in manes(P):
        out.append({'kind': 'mane', 'chain': m['bones']})
    tr = trunk_of(P)
    if tr:
        out.append({'kind': 'trunk', 'chain': tr['bones']})
    return out


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → chain kind, for a recipe's CLIP_CALM: ear, tail, and each mane by its own name (kind 'mane',
    so CLIP_CALM can scale one mane by name or every mane as 'mane'); a trunk ('trunk'), its bud ('bud') and the wings
    ('wing') when the rig has them."""
    out = {'ear': 'ear', 'tail': 'tail', **{m['name']: 'mane' for m in manes(P)}}
    tr = trunk_of(P)
    if tr:
        out[tr['name']] = 'trunk'
        if tr['bud']:
            out[tr['bud'].get('name', 'bud')] = 'bud'
    if wings_of(P):
        out[wings_of(P).get('name', 'wing')] = 'wing'
    return out


def heatless(P: dict) -> set[str]:
    """Bone-name prefixes whose heat weights on the body go to their parent (build_ultra stage_rig), like the manes and
    props: the wings (folded against the flank, their bones would drag its skin open) and the bud's petals (separate
    meshes on the trunk's tip). Their parts are skinned by the recipe's fin / prop weight regions."""
    out: set[str] = set()
    if wings_of(P):
        out.add(wings_of(P).get('name', 'wing'))
    tr = trunk_of(P)
    if tr and tr['bud']:
        out.add(tr['bud'].get('name', 'bud'))
    return out


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    hip = Vector(P['hip'])
    chest = Vector(P['chest'])
    hc = Vector(P['head_c'])
    hr = P['head_r']
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk),
        BoneSpec('hips', tuple(hip), tuple(hip + Vector((0, -0.12 * sk, 0.02 * sk))), 'root', radius=0.34 * sk),
        BoneSpec('spine', tuple(hip + Vector((0, -0.12 * sk, 0.02 * sk))), tuple(chest + Vector((0, 0.06 * sk, -0.01 * sk))), 'hips', connect=True, radius=0.34 * sk),
        BoneSpec('chest', tuple(chest + Vector((0, 0.06 * sk, -0.01 * sk))), tuple(chest + Vector((0, -0.12 * sk, 0.0))), 'spine', connect=True, radius=0.34 * sk),
    ]
    neck = neck_names(P)
    if neck == ['neck'] and not P.get('neck_points'):
        specs += [
            BoneSpec('neck', tuple(chest + Vector((0, -0.12 * sk, 0.0))), tuple(hc + Vector((0, 0.06 * sk, -hr * 0.55))), 'chest', connect=True, radius=0.25 * sk),
            BoneSpec('head', tuple(hc + Vector((0, 0.06 * sk, -hr * 0.55))), tuple(hc + Vector((0, 0.0, hr))), 'neck', connect=True, radius=hr * 1.35),
        ]
    else:
        # a neck chain (Stripeneck, grown Hearthwing): neck.1 from the chest's tip (joined when the points start there)
        npts = neck_points(P)
        joined = (npts[0] - (chest + Vector((0, -0.12 * sk, 0.0)))).length < 1e-4
        for i, nm in enumerate(neck):
            specs.append(BoneSpec(nm, tuple(npts[i]), tuple(npts[i + 1]), 'chest' if i == 0 else neck[i - 1], connect=i > 0 or joined, radius=0.25 * sk))
        specs.append(BoneSpec('head', tuple(npts[-1]), tuple(hc + Vector((0, 0.0, hr))), neck[-1], connect=True, radius=hr * 1.35))
    jw = P.get('jaw') or {}
    # `jaw` = {'head': hinge, 'tail': chin tip}: put the hinge at the mouth's corner for a long muzzle (Starhowl's)
    specs.append(BoneSpec('jaw', tuple(jw.get('head', hc + Vector((0, -0.06 * sk, -hr * 0.35)))), tuple(jw.get('tail', hc + Vector((0, -hr * 0.95, -hr * 0.6)))),
                          'head', radius=0.12 * sk))
    # ears: two bones each, from the base along ear_dir
    if has_ears(P):
        eb = Vector(P['ear_base'])
        ed = Vector(P['ear_dir']).normalized()
        el = P['ear_len']
        for side, sx in (('L', 1), ('R', -1)):
            b = Vector((eb.x * sx, eb.y, eb.z))
            d = Vector((ed.x * sx, ed.y, ed.z))
            m = b + d * el * 0.5
            t = b + d * el
            specs.append(BoneSpec(f'ear.{side}.1', tuple(b), tuple(m), 'head', radius=0.11 * sk))
            specs.append(BoneSpec(f'ear.{side}.2', tuple(m), tuple(t), f'ear.{side}.1', connect=True, radius=0.11 * sk))
    # tail: a chain of tail_bones (3) along a line or the recipe's points
    names = tail_names(P)
    if names:
        pts = tail_points(P)
        radii = [0.1, 0.11, 0.12] if len(names) == 3 else [0.1 + 0.02 * i / max(1, len(names) - 1) for i in range(len(names))]
        for i, nm in enumerate(names):
            specs.append(BoneSpec(nm, tuple(pts[i]), tuple(pts[i + 1]), 'hips' if i == 0 else names[i - 1], connect=i > 0, radius=radii[i] * sk))
    # legs: thigh → shin → foot, with the knee a little back so the IK has slack
    hooves = bool(P.get('hooves'))
    for leg in LEGS:
        x, y, hz = P['legs'][leg]
        kb = P.get('knee_back', 0.03)
        ankle = ankle_of(P)
        l1 = (hz - ankle) * 0.52
        knee = Vector((x, y - kb, hz - l1))      # knee a little forward, so the IK has slack to bend
        foot = Vector((x, y, ankle))
        # a paw's foot runs forward to the toes; a hoof stands on its tip, just ahead of the ankle
        toe = Vector((x, y - foot_len_of(P), 0.0 if hooves else ankle * 0.6))
        hk = hocked(P, leg)
        if hk:
            # a bent hock: the knee forward, the shin back to the raised hock, the foot (the long rear foot) down to the paw
            base = Vector((x, y, 0.0))
            knee, foot, toe = base + hk['knee'], base + hk['hock'], base + hk['paw']
        parent = 'chest' if leg[0] == 'F' else 'hips'
        r = P.get('leg_radius', 0.11)
        specs.append(BoneSpec(f'thigh.{leg}', (x, y, hz), tuple(knee), parent, radius=r))
        specs.append(BoneSpec(f'shin.{leg}', tuple(knee), tuple(foot), f'thigh.{leg}', connect=True, radius=r))
        specs.append(BoneSpec(f'foot.{leg}', tuple(foot), tuple(toe), f'shin.{leg}', connect=True, radius=r * 1.2))
    # manes: spring chains on the neck, the chest or the head
    for m in manes(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.08 * sk))
    # props: rigid attach bones (horns, a rope, a scarf): deform, never keyed, so they move with their parent
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'head'), radius=0.08 * sk))
    # batch 2: a trunk chain (and its bud's petals), the wings
    tr = trunk_of(P)
    if tr:
        for i, nm in enumerate(tr['bones']):
            specs.append(BoneSpec(nm, tuple(tr['points'][i]), tuple(tr['points'][i + 1]), tr['parent'] if i == 0 else tr['bones'][i - 1],
                                  connect=i > 0, radius=0.09 * sk))
        for nm, h, t, _axis in bud_petals(P):
            specs.append(BoneSpec(nm, tuple(h), tuple(t), tr['bones'][-1], radius=0.05 * sk))
    for nm, h, t, par in wing_specs(P):
        specs.append(BoneSpec(nm, tuple(h), tuple(t), par, connect=nm.endswith('.2'), radius=0.08 * sk))
    have = {s.name for s in specs}
    for s in specs:
        if s.parent and s.parent not in have:
            raise ValueError(f"bone {s.name}: its parent {s.parent!r} is not in the rig (with neck_bones > 1 the neck is "
                             f"{', '.join(neck)}; parent manes and props on one of those)")
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    sk = size_of(P)
    hc = Vector(P['head_c'])
    hr = P['head_r']
    fl = P['legs']['FL']
    fr = P['legs']['FR']
    names = tail_names(P)
    out = {
        'socket_head': ('head', (0, hc.y, hc.z + hr)),
        'socket_crown': ('head', (0, hc.y, hc.z + hr + 0.12 * sk)),
        'socket_back': ('spine', (0, P['hip'][1] - 0.1 * sk, P['hip'][2] + 0.3 * sk)),
        'socket_mouth': ('jaw', (0, hc.y - hr * 1.05, hc.z - hr * 0.55)),
        'socket_paw_L': ('foot.FL', (fl[0], fl[1] - 0.1 * sk, 0.03 * sk)),
        'socket_paw_R': ('foot.FR', (fr[0], fr[1] - 0.1 * sk, 0.03 * sk)),
        'socket_tail': (names[-1], tuple(tail_points(P)[-1])) if names else ('hips', tuple(P['tail_base'])),
    }
    for pr in P.get('props', []) or []:
        out[f"socket_{pr['name']}"] = (f"prop.{pr['name']}", tuple(pr['tail']))
    tr = trunk_of(P)
    if tr:
        out['socket_trunk'] = (tr['bones'][-1], tuple(tr['points'][-1]))
    if wings_of(P):
        for side in (1, -1):
            names = U.wing_bone_names(wings_of(P), side)
            out[f'socket_wing_{U.wing_tag(side)}'] = (names[1], tuple(U.wing_points(wings_of(P), side)['wrist']))
    return out


# --------------------------------------------------------------------------- leg helpers
class Legs:
    """Analytic two-bone IK for the four legs, in the body's frame (hip height may bob)."""

    def __init__(self, cb: A.ClipBuilder, P: dict):
        self.cb = cb
        self.P = P
        self.splay_k = HOOF_SPLAY if P.get('hooves') else 1.0
        self.rest: dict[str, tuple[float, float]] = {}
        for leg in LEGS:
            x, y, hz = P['legs'][leg]
            l1, l2 = self.lengths(leg)
            dy0, z0 = self.foot_rest(leg)
            self.rest[leg] = A.leg_ik(Vector((0, 0, hz)), Vector((0, dy0, z0)), l1, l2, Vector((0, -1, 0)))

    def foot_rest(self, leg: str) -> tuple[float, float]:
        """Where the IK's end (the ankle; a bent hock's hock) sits at rest: (y offset from the hip, height)."""
        hk = hocked(self.P, leg)
        return (hk['hock'].y, hk['hock'].z) if hk else (0, ankle_of(self.P))

    def lengths(self, leg: str) -> tuple[float, float]:
        hk = hocked(self.P, leg)
        if hk:
            hip = Vector((0, 0, self.P['legs'][leg][2]))
            return (hk['knee'] - hip).length, (hk['hock'] - hk['knee']).length
        x, y, hz = self.P['legs'][leg]
        kb = self.P.get('knee_back', 0.03)
        ankle = ankle_of(self.P)
        drop = (hz - ankle) * 0.52
        hip = Vector((0, 0, hz))
        knee = Vector((0, -kb, hz - drop))       # the knee sits a little forward (−Y), as the rig builds it
        foot = Vector((0, 0, ankle))
        return (knee - hip).length, (foot - knee).length

    def place(self, leg: str, frame: int, dy: float, dz: float, body_dz: float = 0.0, splay: float = 0.0, foot_extra: float = 0.0) -> None:
        """Put the foot at (dy back, dz up) from its rest spot while the body is `body_dz` higher."""
        x, y, hz = self.P['legs'][leg]
        l1, l2 = self.lengths(leg)
        dy0, ankle = self.foot_rest(leg)
        hip = Vector((0, 0, hz + body_dz))
        foot = Vector((0, dy0 + dy, ankle + dz))
        th, kn = A.leg_ik(hip, foot, l1, l2, Vector((0, -1, 0)))
        rth, rkn = self.rest[leg]
        cb = self.cb
        cb.rot(f'thigh.{leg}', frame, x=-(th - rth), y=splay * self.splay_k * (1 if leg.endswith('L') else -1))
        cb.rot(f'shin.{leg}', frame, x=-(kn - rkn))
        cb.rot(f'foot.{leg}', frame, x=(th - rth) + (kn - rkn) + foot_extra)

    def angles(self, leg: str, dy: float, dz: float, body_dz: float = 0.0) -> tuple[float, float, float]:
        """The (thigh, shin, foot) x rotations `place` would key: the foot `dy` back and `dz` up from its rest spot while
        the body is `body_dz` higher (a crouch with the feet planted: dy = minus the body's own shift)."""
        _x, _y, hz = self.P['legs'][leg]
        l1, l2 = self.lengths(leg)
        dy0, ankle = self.foot_rest(leg)
        th, kn = A.leg_ik(Vector((0, 0, hz + body_dz)), Vector((0, dy0 + dy, ankle + dz)), l1, l2, Vector((0, -1, 0)))
        rth, rkn = self.rest[leg]
        return -(th - rth), -(kn - rkn), (th - rth) + (kn - rkn)

    def pose(self, leg: str, frame: int, thigh: float, shin: float, foot: float = 0.0, splay: float = 0.0) -> None:
        cb = self.cb
        cb.rot(f'thigh.{leg}', frame, x=thigh, y=splay * self.splay_k * (1 if leg.endswith('L') else -1))
        cb.rot(f'shin.{leg}', frame, x=shin)
        cb.rot(f'foot.{leg}', frame, x=foot)


def gait(legs: Legs, frames: int, stride: float, lift: float, phases: dict[str, float], stance: float = 0.6,
         body_bob: float = 0.008, reverse: bool = False, bob_fn=None, foot_flick: float = 0.0) -> list[int]:
    """Key an in-place walk/run cycle. Returns the frames of foot plants (for `step` markers)."""
    cb = legs.cb
    plants: list[int] = []
    for f in range(1, frames + 2):
        t = (f - 1) / frames
        bob = bob_fn(t) if bob_fn else body_bob * abs(math.sin(t * 2 * math.pi))
        for leg in LEGS:
            p = (t + phases[leg]) % 1.0
            flick = 0.0
            if p < stance:
                u = p / stance
                dy = -stride / 2 + stride * u      # front (−Y) → back (+Y) while planted
                dz = 0.0
            else:
                u = (p - stance) / (1 - stance)
                dy = stride / 2 - stride * C.ease_in_out(u)
                dz = lift * math.sin(u * math.pi)
                flick = foot_flick * math.sin(u * math.pi)     # hooves: the hoof curls back in the swing
            if reverse:
                dy = -dy
            legs.place(leg, f, dy, dz, body_dz=bob, foot_extra=flick)
    for leg in LEGS:
        # the foot plants where its phase wraps to 0
        plants.append(1 + int(round(((1.0 - phases[leg]) % 1.0) * frames)) % frames)
    return sorted(set(plants))


# --------------------------------------------------------------------------- clips
def make_clips(cb: A.ClipBuilder, P: dict, only: list[str] | None = None) -> list[A.ClipMeta]:
    legs = Legs(cb, P)
    hz = P['hip'][2]
    sk = size_of(P)
    flick = HOOF_FLICK if P.get('hooves') else 0.0
    TAIL = tail_names(P)
    MANES = manes(P)
    CLOSED = P.get('blink_closed')
    # per axis, how far toward shut at a given closing: the blink clip's half pose is (0.3, 0.62, 0.08) of the way, so the
    # lens squashes onto the lash line before it sinks into the head
    SHUT_EXP = tuple(math.log(v) / math.log(0.5) for v in (0.3, 0.62, 0.08))
    made: list[A.ClipMeta] = []

    def mm(v: float) -> float:
        """An absolute offset in Puddlepup's metres, at this breed's size."""
        return v * sk

    def want(name: str) -> bool:
        return not only or name in only

    def tail_part(s: int) -> list[tuple[str, float, float]]:
        """The tail bones that play part `s` of the 3-bone motion (0 root, 1 middle, 2 tip), as (bone, share, lag):
        a longer chain splits each part over its bones (the total curl stays the same, the later bones lag a little)."""
        n = len(TAIL)
        if n >= 3:
            idx = [i for i in range(n) if min(2, i * 3 // n) == s]
        elif n == 2:
            idx = {0: [0], 1: [], 2: [1]}[s]
        else:
            idx = [0] if (n == 1 and s == 0) else []
        return [(TAIL[i], 1.0 / len(idx), 0.04 * j) for j, i in enumerate(idx)]

    def tsample(s: int, frames: int, fn, step: int = 1) -> None:
        for bone, share, lag in tail_part(s):
            g = fn if (share == 1.0 and lag == 0.0) else (lambda t, fn=fn, share=share, lag=lag: tuple(v * share for v in fn(t - lag)))
            cb.sample(bone, frames, g, step=step)

    def trot(s: int, frame: int, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        for bone, share, _lag in tail_part(s):
            cb.rot(bone, frame, x=x * share, y=y * share, z=z * share)

    def inherited(parent: str, against) -> list:
        """The keyed head / neck rotations (fns of t, whole-chain degrees) a chain hung on `parent` inherits."""
        if not against:
            return []
        keys = ('head', 'neck') if parent in ('head', 'jaw') else ('neck',) if (parent == 'neck' or parent in neck_names(P)) else ()
        return [against[k] for k in keys if k in against]

    def chain_fn(base, i: int, cap, inh: list, c: float):
        """A chain bone's key: `base(t)` (x, y, z), each axis capped to ±cap, the first bone taking back c × what it
        inherits from the head and neck (the counter option)."""
        def f(t):
            x, y, z = base(t)
            if cap is not None:
                x, y, z = (max(-cap, min(cap, v)) for v in (x, y, z))
            if i == 0 and inh:
                for g in inh:
                    gx, gy, gz = g(t)
                    x, y, z = x - c * gx, y - c * gy, z - c * gz
            return (x, y, z)
        return f

    def mane(frames: int, lift, sway, step: int = 2, against=None, only_counter: bool = False) -> None:
        """Key every mane chain: `lift(t)` streams it back and up (+x), `sway(t)` swings it sideways (+z), in degrees for
        the whole chain, shared over its bones with a lag toward the tip. Either may be a number. A mane's `cap` limits
        each bone's turn; its `counter` (with `against` = the clip's {'head': fn, 'neck': fn}) keeps it hanging when
        the head jerks. Without either the keys are exactly as before."""
        lf = lift if callable(lift) else (lambda t, v=lift: v)
        sw = sway if callable(sway) else (lambda t, v=sway: v)
        for mn in MANES:
            if only_counter and not mn['counter']:
                continue
            n = len(mn['bones'])
            inh = inherited(mn['parent'], against) if mn['counter'] else []
            for i, bone in enumerate(mn['bones']):
                if mn['cap'] is None and not (i == 0 and inh):
                    cb.sample(bone, frames, lambda t, lag=0.06 * i, n=n: (lf(t - lag) / n, 0, sw(t - lag) / n), step=step)
                    continue
                base = lambda t, lag=0.06 * i, n=n: (lf(t - lag) / n, 0.0, sw(t - lag) / n)
                cb.sample(bone, frames, chain_fn(base, i, mn['cap'], inh, mn['counter']), step=step)

    def mane_droop(frames: int, k, gravity, most: float = 70.0, step: int = 1, against=None) -> None:
        """Lay every mane chain down toward `gravity` (a direction in the body's rest frame) by k(t): each chain turns
        about (its own direction × gravity) by up to `most` degrees, shared over its bones; its cap and counter apply."""
        kf = k if callable(k) else (lambda t, v=k: v)
        g = Vector(gravity).normalized()
        for mn in MANES:
            d = (mn['points'][-1] - mn['points'][0]).normalized()
            axis = d.cross(g)
            if axis.length < 1e-6:
                continue
            axis.normalize()
            ang = min(math.degrees(d.angle(g)), most)
            n = len(mn['bones'])
            inh = inherited(mn['parent'], against) if mn['counter'] else []
            for i, bone in enumerate(mn['bones']):
                def base(t, lag=0.06 * i, n=n, axis=axis, ang=ang):
                    e = Quaternion(axis, math.radians(ang * max(0.0, min(1.0, kf(t - lag))) / n)).to_euler('XYZ')
                    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
                cb.sample(bone, frames, chain_fn(base, i, mn['cap'], inh, mn['counter']), step=step)

    # ---- batch 2 (each a no-op unless the rig has it): the neck chain, the trunk and its bud, the wings
    NECK = neck_names(P)
    TR = trunk_of(P)
    PETALS = bud_petals(P)
    WQ = {side: wing_spread_quats(P, side) for side in (1, -1)} if wings_of(P) else {}

    def nsample(frames: int, fn, step: int = 1) -> None:
        """Key the neck: Puddlepup's one bone as before; a chain shares the rotation equally (the total stays the same)."""
        if len(NECK) == 1:
            cb.sample(NECK[0], frames, fn, step=step)
            return
        n = len(NECK)
        for bone in NECK:
            cb.sample(bone, frames, lambda t, fn=fn, n=n: tuple(v / n for v in fn(t)), step=step)

    def nrot(frame: int, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        n = len(NECK)
        for bone in NECK:
            cb.rot(bone, frame, x=x / n, y=y / n, z=z / n)

    def trunk(frames: int, curl, sway=0.0, step: int = 2, against=None, raise_: bool = False, tip=0.0) -> None:
        """Key the trunk: `curl(t)` degrees for the whole chain (+ curls in toward the chest and mouth, − raises it out
        and up), `sway(t)` sideways (+ toward the left); shared more toward the tip, the tip lagging (a curl). With
        `raise_` the base takes the most instead, so the trunk swings up nearly straight and points forward and up
        rather than hooking back at the tip. `tip(t)` degrees more over the outer half of the chain (+ curls the tip
        in and down: after a raise it points the tip forward). Numbers allowed."""
        if not TR:
            return
        cf = curl if callable(curl) else (lambda t, v=curl: v)
        sf = sway if callable(sway) else (lambda t, v=sway: v)
        tf = tip if callable(tip) else (lambda t, v=tip: v)
        bones = TR['bones']
        outer = [i for i in range(len(bones)) if i >= len(bones) // 2]
        tot = len(bones) * (len(bones) + 1) / 2
        k = TR['curl']
        inh = inherited(TR['parent'], against) if TR['counter'] else []
        for i, bone in enumerate(bones):
            sh = ((len(bones) - i) if raise_ else (i + 1)) / tot * k
            ts = (k / len(outer)) if i in outer else 0.0
            base = (lambda t, sh=sh, lag=0.04 * i: (cf(t - lag) * sh, 0, sf(t - lag) * sh)) if not ts else                 (lambda t, sh=sh, ts=ts, lag=0.04 * i: (cf(t - lag) * sh + tf(t - lag) * ts, 0, sf(t - lag) * sh))
            cb.sample(bone, frames, chain_fn(base, i, TR['cap'], inh, TR['counter']) if (TR['cap'] is not None or inh) else base, step=step)

    def bud(frames: int, k, step: int = 2) -> None:
        """Open the bud's petals by k(t) (0 closed, the rest pose; 1 = `open` degrees). A number is allowed."""
        if not PETALS:
            return
        kf = k if callable(k) else (lambda t, v=k: v)
        ang = float(TR['bud'].get('open', 70.0))
        for nm, _h, _t, axis in PETALS:
            def f(t, axis=axis):
                e = Quaternion(axis, math.radians(ang * max(0.0, min(1.0, kf(t))))).to_euler('XYZ')
                return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
            cb.sample(nm, frames, f, step=step)

    def wings(frames: int, k, flap=0.0, step: int = 1) -> None:
        """Open both wings by k(t) (0 folded, the rest pose; 1 the recipe's spread pose) and beat them by flap(t) degrees
        about the body's long axis (+ = down). Numbers allowed."""
        if not WQ:
            return
        kf = k if callable(k) else (lambda t, v=k: v)
        ff = flap if callable(flap) else (lambda t, v=flap: v)
        for side, quats in WQ.items():
            for j, (bone, q) in enumerate(quats):
                def f(t, q=q, j=j, side=side):
                    qk = Quaternion().slerp(q, max(0.0, min(1.0, kf(t))))
                    if j == 0:
                        qk = Quaternion((0.0, 1.0, 0.0), math.radians(side * ff(t))) @ qk
                    e = qk.to_euler('XYZ')
                    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))
                cb.sample(bone, frames, f, step=step)

    def eyes_shut(frames: int, k, step: int = 1) -> None:
        """Squeeze the eyes toward the blink's closed pose by k(t) (0 open, 1 shut: the recipe's BLINK_CLOSED, keyed on
        the blink bones in their own axes, as the blink clip does). Only when the build passes blink_closed."""
        if not CLOSED:
            return
        kf = k if callable(k) else (lambda t, v=k: v)
        frames_k = list(range(1, frames + 2, step))
        if frames_k[-1] != frames + 1:
            frames_k.append(frames + 1)
        for tag in ('L', 'R'):
            pb = cb.arm.pose.bones.get(f'eye.{tag}')
            if pb is None:
                continue
            for f in frames_k:
                kk = max(0.0, min(1.0, kf((f - 1) / frames)))
                pb.scale = tuple(1.0 + (c - 1.0) * kk ** e for c, e in zip(CLOSED, SHUT_EXP))
                pb.keyframe_insert('scale', frame=f)

    def breathe(frames: int, rate: float = 1.0, depth: float = 1.0, tail: float = 1.0, ear: float = 1.0) -> None:
        cb.sample('chest', frames, lambda t: (2.0 * depth * A.wave(t, rate), 0, 0), step=3)
        cb.sample('hips', frames, lambda t: (0, 0, mm(0.004) * depth * A.wave(t, rate)), kind='loc', step=3)
        cb.sample('head', frames, lambda t: (-1.4 * depth * A.wave(t, rate), 0, 0), step=3)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', frames, lambda t, sx=sx: (0, sx * 2.5 * ear * A.wave(t, rate, 0.25), 0), step=3)
        tsample(0, frames, lambda t: (0, 0, 7 * tail * A.wave(t, rate * 1.5)), step=3)
        tsample(1, frames, lambda t: (0, 0, 9 * tail * A.wave(t, rate * 1.5, -0.12)), step=3)
        tsample(2, frames, lambda t: (0, 0, 11 * tail * A.wave(t, rate * 1.5, -0.24)), step=3)
        mane(frames, lambda t: 4.0 * depth * A.wave(t, rate), lambda t: 8.0 * ear * A.wave(t, rate, 0.2), step=3)

    def ears(frames: int, droop: float, flutter: float = 0.0, rate: float = 1.0) -> None:
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', frames, lambda t, sx=sx: (0, sx * (droop + flutter * A.wave(t, rate, 0.25)), 0), step=3)
            cb.sample(f'ear.{s}.2', frames, lambda t, sx=sx: (0, sx * (droop * 0.6 + flutter * 0.6 * A.wave(t, rate, 0.1)), 0), step=3)

    def tail(frames: int, up: float, wag: float, rate: float = 1.0) -> None:
        tsample(0, frames, lambda t: (up, 0, wag * A.wave(t, rate)), step=2)
        tsample(1, frames, lambda t: (up * 0.5, 0, wag * 1.2 * A.wave(t, rate, -0.12)), step=2)
        tsample(2, frames, lambda t: (up * 0.3, 0, wag * 1.4 * A.wave(t, rate, -0.24)), step=2)

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
        cb.sample('root', n, lambda t: (mm(0.004) * A.wave(t, 0.5), 0, 0), kind='loc', step=4)
        trunk(n, lambda t: 8 * A.wave(t, 2.0), lambda t: 12 * A.wave(t, 1.0, 0.25), step=3)
        wings(n, lambda t: 0.03 + 0.03 * A.wave(t, 1.0), step=3)
        made.append(cb.end())

    if want('idle_happy'):
        n = 90
        cb.begin('idle_happy', n, loop=True)
        cb.sample('hips', n, lambda t: (0, 0, mm(0.012) * A.bounce(t, 3)), kind='loc', step=2)
        squash(n, lambda t: 1.0 + 0.04 * A.wave(t, 3.0, 0.25))
        cb.sample('chest', n, lambda t: (2.5 * A.wave(t, 3.0), 0, 0), step=2)
        cb.sample('head', n, lambda t: (-3 * A.wave(t, 3.0), 8 * A.wave(t, 1.0), 0), step=2)
        ears(n, -6, 6, 3.0)
        tail(n, 18, 28, 3.0)
        stand(n)
        cb.face(1, 'happy')
        mane(n, lambda t: 6 * A.wave(t, 3.0), lambda t: 6 * A.wave(t, 1.0))
        trunk(n, lambda t: -25 + 10 * A.wave(t, 3.0), lambda t: 12 * A.wave(t, 1.0), step=2)
        bud(n, 1.0, step=30)
        wings(n, lambda t: 0.25 + 0.1 * A.wave(t, 3.0), lambda t: 10 * A.wave(t, 3.0), step=2)
        if P.get('jaw_open'):
            # a weighted jaw (the recipe doesn't merge it into the head): a happy open smile
            cb.sample('jaw', n, lambda t: (16 + 2 * A.wave(t, 3.0), 0, 0), step=2)

        made.append(cb.end())

    if want('idle_tired'):
        n = 150
        cb.begin('idle_tired', n, loop=True)
        breathe(n, rate=0.6, depth=1.6, tail=0.3, ear=0.3)
        cb.sample('head', n, lambda t: (18 - 1.5 * A.wave(t, 0.6), 0, 0), step=3)
        nsample(n, lambda t: (10, 0, 0), step=10)
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
        nsample(n, lambda t: (8, 0, 0), step=10)
        cb.sample('hips', n, lambda t: (0, 0, -mm(0.012) + mm(0.003) * A.wave(t, 0.7)), kind='loc', step=3)
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
        cb.sample('hips', n, lambda t: (0, 0, -(hz - mm(0.1)) + mm(0.003) * A.wave(t, 0.4)), kind='loc', step=4)
        cb.sample('chest', n, lambda t: (3 * A.wave(t, 0.4), 0, 0), step=4)
        nsample(n, lambda t: (14, 0, 0), step=20)
        cb.sample('head', n, lambda t: (22, 0, 24), step=20)
        ears(n, 20, 1, 0.4)
        tsample(0, n, lambda t: (-8, 0, 40), step=20)
        tsample(1, n, lambda t: (0, 0, 40), step=20)
        tsample(2, n, lambda t: (0, 0, 30), step=20)
        for leg in ('FL', 'FR'):
            legs.pose(leg, 1, -75, 125, -50)
            legs.pose(leg, 1 + n, -75, 125, -50)
        for leg in ('BL', 'BR'):
            legs.pose(leg, 1, 70, -125, 55)
            legs.pose(leg, 1 + n, 70, -125, 55)
        trunk(n, 25, step=20)
        cb.face(1, 'sleepy')
        made.append(cb.end())

    if want('eat'):
        n = 60
        cb.begin('eat', n, loop=True)
        dip = lambda t: A.step_ease(t, 0.0, 0.25) * (1 - A.step_ease(t, 0.8, 1.0))
        nsample(n, lambda t: (22 * dip(t), 0, 0), step=2)
        cb.sample('head', n, lambda t: (30 * dip(t), 0, 0), step=2)
        cb.sample('chest', n, lambda t: (6 * dip(t), 0, 0), step=2)
        cb.sample('hips', n, lambda t: (0, -mm(0.02) * dip(t), -mm(0.01) * dip(t)), kind='loc', step=2)
        cb.sample('jaw', n, lambda t: (14 * dip(t) * abs(math.sin(t * 2 * math.pi * 3)), 0, 0), step=1)
        ears(n, 6, 3, 3.0)
        tail(n, 6, 10, 1.0)
        stand(n)
        trunk(n, lambda t: 60 * dip(t))
        made.append(cb.end())

    if want('pet'):
        n = 75
        cb.begin('pet', n, loop=True)
        cb.sample('head', n, lambda t: (6, 14 + 2 * A.wave(t, 2.0), 4), step=2)
        nsample(n, lambda t: (4, 4, 0), step=10)
        cb.sample('hips', n, lambda t: (0, 0, mm(0.008) * A.bounce(t, 2)), kind='loc', step=2)
        cb.sample('chest', n, lambda t: (0.8 * A.wave(t, 8.0), 0, 0), step=1)
        ears(n, 12, 3, 2.0)
        tail(n, 14, 22, 2.0)
        stand(n)
        trunk(n, lambda t: -15 + 5 * A.wave(t, 2.0))
        bud(n, 0.8, step=25)
        cb.face(1, 'happy')
        made.append(cb.end())

    if want('look_around'):
        n = 90
        cb.begin('look_around', n, loop=True)
        yaw = lambda t: 35 * A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56)) - 35 * A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        cb.sample('head', n, lambda t: (0, 0, yaw(t)), step=1)
        nsample(n, lambda t: (0, 0, yaw(t) * 0.25), step=1)
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
        cb.sample('root', n, lambda t: (0, 0, mm(0.15) * air(t)), kind='loc', step=1)
        squash(n, lambda t: 1.0 - 0.14 * A.pulse(t, 0.0, 0.26) + 0.12 * A.pulse(t, 0.28, 0.6) - 0.16 * A.pulse(t, 0.8, 0.98))
        cb.sample('chest', n, lambda t: (-8 * air(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-6 * air(t) + 10 * A.pulse(t, 0.0, 0.26), 0, 0), step=1)
        ears(n, 4, 0)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-30 * air(t) + 25 * A.pulse(t, 0.8, 1.0), sx * 4, 0), step=1)
        tsample(0, n, lambda t: (22 * air(t), 0, 0), step=1)
        tsample(1, n, lambda t: (10 * air(t), 0, 0), step=1)
        mane(n, lambda t: -14 * air(t) + 16 * A.pulse(t, 0.8, 1.0), 0, step=1)
        for leg in LEGS:
            tuck = -28 if leg[0] == 'F' else 30
            cb.sample(f'thigh.{leg}', n, lambda t, tuck=tuck: (tuck * air(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t, tuck=tuck: (-tuck * 1.4 * air(t), 0, 0), step=1)
            cb.sample(f'foot.{leg}', n, lambda t, tuck=tuck: (tuck * 0.4 * air(t), 0, 0), step=1)
        trunk(n, lambda t: -30 * air(t) + 20 * A.pulse(t, 0.8, 1.0), step=1)
        wings(n, lambda t: 0.6 * air(t), lambda t: 25 * air(t) - 15 * A.pulse(t, 0.8, 1.0))
        cb.marker('land', 20)
        made.append(cb.end())

    if want('celebrate'):
        n = 60
        cb.begin('celebrate', n, loop=True)
        air = lambda t: A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        cb.sample('root', n, lambda t: (0, 0, mm(0.11) * air(t)), kind='loc', step=1)
        squash(n, lambda t: 1.0 + 0.1 * air(t) - 0.12 * (A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)))
        cb.sample('root', n, lambda t: (0, 9 * A.wave(t, 3.0) * A.step_ease(t, 0.75, 0.85) * (1 - A.step_ease(t, 0.95, 1.0)), 0), step=1)
        cb.sample('head', n, lambda t: (-8 * air(t), 10 * A.wave(t, 2.0), 0), step=1)
        ears(n, -8, 12, 3.0)
        tail(n, 22, 30, 4.0)
        mane(n, lambda t: 16 * air(t), lambda t: 6 * A.wave(t, 2.0), step=1)
        for leg in LEGS:
            tuck = -22 if leg[0] == 'F' else 24
            cb.sample(f'thigh.{leg}', n, lambda t, tuck=tuck: (tuck * air(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t, tuck=tuck: (-tuck * 1.3 * air(t), 0, 0), step=1)
        trunk(n, lambda t: -50 + 15 * A.wave(t, 3.0), lambda t: 10 * A.wave(t, 2.0), step=1)
        bud(n, 1.0, step=30)
        wings(n, lambda t: 0.55 + 0.45 * min(1.0, air(t)), lambda t: 30 * A.wave(t, 4.0))
        cb.face(1, 'happy')
        cb.marker('land', 22)
        cb.marker('land', 43)
        made.append(cb.end())

    # ---- moving
    if want('walk'):
        n = 30
        stride = P.get('stride', 0.18)
        cb.begin('walk', n, loop=True, root_speed=stride / (0.6 * n / A.FPS))
        plants = gait(legs, n, stride, mm(0.05), {'FL': 0.0, 'BR': 0.25, 'FR': 0.5, 'BL': 0.75}, body_bob=mm(0.008), foot_flick=flick)
        cb.sample('chest', n, lambda t: (2.5 * A.wave(t, 2.0), 0, 2 * A.wave(t, 1.0)), step=2)
        cb.sample('hips', n, lambda t: (0, 0, 0), kind='loc', step=15)
        cb.sample('head', n, lambda t: (-2.5 * A.wave(t, 2.0, 0.5), 0, 0), step=2)
        ears(n, 2, 5, 2.0)
        tail(n, 6, 14, 1.0)
        mane(n, lambda t: 6 + 4 * A.wave(t, 2.0), lambda t: 5 * A.wave(t, 1.0, -0.1))
        trunk(n, lambda t: 6 * A.wave(t, 2.0), lambda t: 10 * A.wave(t, 1.0, -0.1))
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    if want('run'):
        n = 20
        stride = P.get('stride', 0.18) * 1.6
        cb.begin('run', n, loop=True, root_speed=stride / (0.45 * n / A.FPS))
        plants = gait(legs, n, stride, mm(0.09), {'FL': 0.0, 'FR': 0.1, 'BL': 0.5, 'BR': 0.6}, stance=0.45,
                      bob_fn=lambda t: mm(0.03) * A.pulse(t, 0.55, 1.0), foot_flick=flick)
        cb.sample('root', n, lambda t: (0, 0, mm(0.03) * A.pulse(t, 0.55, 1.0)), kind='loc', step=1)
        squash(n, lambda t: 1.0 + 0.08 * A.pulse(t, 0.55, 1.0) - 0.08 * A.pulse(t, 0.0, 0.3))
        cb.sample('chest', n, lambda t: (-9 * A.wave(t, 1.0, 0.25), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-4 + 5 * A.wave(t, 1.0, 0.5), 0, 0), step=1)
        ears(n, -16, 10, 1.0)
        tail(n, 4, 8, 1.0)
        mane(n, lambda t: 22 + 8 * A.wave(t, 1.0, -0.2), lambda t: 4 * A.wave(t, 1.0))
        trunk(n, lambda t: 20 + 8 * A.wave(t, 1.0, -0.2), step=1)
        wings(n, 0.08, lambda t: 6 * A.wave(t, 1.0), step=2)
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    # ---- scenes
    def sit_pose(frame: int, k: float = 1.0) -> None:
        cb.rot('chest', frame, x=-18 * k)
        cb.rot('spine', frame, x=-8 * k)
        nrot(frame, x=6 * k)
        cb.loc('hips', frame, 0, mm(0.03) * k, -(hz - mm(0.1)) * k)
        for leg in ('BL', 'BR'):
            legs.pose(leg, frame, -82 * k, 128 * k, -46 * k, splay=6 * k)
        for leg in ('FL', 'FR'):
            legs.pose(leg, frame, 10 * k, -4 * k, -6 * k)
        trot(0, frame, x=-10 * k, z=25 * k)
        trot(1, frame, z=30 * k)

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
        tsample(2, n, lambda t: (0, 0, 12 * A.wave(t, 1.5)), step=2)
        tsample(1, n, lambda t: (0, 0, 30 + 6 * A.wave(t, 1.5, -0.1)), step=2)
        made.append(cb.end())

    if want('dizzy'):
        n = 60
        cb.begin('dizzy', n, loop=True)
        cb.sample('head', n, lambda t: (12 * math.cos(t * 4 * math.pi), 0, 16 * math.sin(t * 4 * math.pi)), step=1)
        nsample(n, lambda t: (4 * math.cos(t * 4 * math.pi), 0, 6 * math.sin(t * 4 * math.pi)), step=1)
        cb.sample('root', n, lambda t: (3 * math.sin(t * 4 * math.pi), 5 * math.cos(t * 4 * math.pi), 0), step=1)
        ears(n, 18, 4, 2.0)
        tail(n, -8, 6, 2.0)
        stand(n, splay=8)
        trunk(n, lambda t: 10 * math.cos(t * 4 * math.pi), lambda t: 14 * math.sin(t * 4 * math.pi), step=1)
        wings(n, lambda t: 0.2 + 0.08 * A.wave(t, 2.0), step=2)
        cb.face(1, 'dizzy')
        made.append(cb.end())

    # ---- battle
    if want('battle_idle'):
        n = 40
        cb.begin('battle_idle', n, loop=True)
        cb.sample('hips', n, lambda t: (0, 0, mm(0.012) * A.bounce(t, 2)), kind='loc', step=1)
        squash(n, lambda t: 1.0 + 0.03 * A.wave(t, 2.0, 0.25))
        cb.sample('chest', n, lambda t: (4 + 1.5 * A.wave(t, 2.0), 0, 0), step=2)
        cb.sample('head', n, lambda t: (-6 - 1.5 * A.wave(t, 2.0), 0, 0), step=2)
        ears(n, -10, 3, 2.0)
        tail(n, 22, 8, 2.0)
        mane(n, lambda t: 3 * A.wave(t, 2.0, -0.2), lambda t: 3 * A.wave(t, 1.0))
        stand(n, splay=9)
        trunk(n, lambda t: -10 + 6 * A.wave(t, 2.0), lambda t: 6 * A.wave(t, 1.0))
        wings(n, lambda t: 0.14 + 0.04 * A.wave(t, 2.0), step=2)
        made.append(cb.end())

    if want('step_fwd'):
        n = 24
        stride = P.get('stride', 0.18) * 0.8
        cb.begin('step_fwd', n, loop=True, root_speed=stride / (0.6 * n / A.FPS))
        plants = gait(legs, n, stride, mm(0.05), {'FL': 0.0, 'BR': 0.25, 'FR': 0.5, 'BL': 0.75}, body_bob=mm(0.008), foot_flick=flick)
        cb.sample('chest', n, lambda t: (5 + 2 * A.wave(t, 2.0), 0, 0), step=2)
        cb.sample('head', n, lambda t: (-6 - 2 * A.wave(t, 2.0, 0.5), 0, 0), step=2)
        ears(n, -8, 4, 2.0)
        tail(n, 20, 10, 2.0)
        mane(n, lambda t: 8 + 4 * A.wave(t, 2.0), lambda t: 4 * A.wave(t, 1.0))
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    if want('step_back'):
        n = 24
        stride = P.get('stride', 0.18) * 0.65
        cb.begin('step_back', n, loop=True, root_speed=stride / (0.6 * n / A.FPS))
        plants = gait(legs, n, stride, mm(0.045), {'FL': 0.0, 'BR': 0.25, 'FR': 0.5, 'BL': 0.75}, body_bob=mm(0.006), reverse=True, foot_flick=flick)
        cb.sample('chest', n, lambda t: (-4 + 2 * A.wave(t, 2.0), 0, 0), step=2)
        cb.sample('head', n, lambda t: (-2 - 2 * A.wave(t, 2.0, 0.5), 0, 0), step=2)
        ears(n, 4, 4, 2.0)
        tail(n, 10, 8, 2.0)
        mane(n, lambda t: -4 + 3 * A.wave(t, 2.0), lambda t: 4 * A.wave(t, 1.0))
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    if want('dash'):
        n = 20
        stride = P.get('stride', 0.18) * 2.0
        cb.begin('dash', n, loop=True, root_speed=stride / (0.4 * n / A.FPS))
        plants = gait(legs, n, stride, mm(0.1), {'FL': 0.0, 'FR': 0.08, 'BL': 0.5, 'BR': 0.58}, stance=0.4,
                      bob_fn=lambda t: mm(0.035) * A.pulse(t, 0.5, 1.0), foot_flick=flick)
        cb.sample('root', n, lambda t: (0, 0, mm(0.035) * A.pulse(t, 0.5, 1.0)), kind='loc', step=1)
        cb.sample('root', n, lambda t: (1.0 / 1.1, 1.14, 0.9), kind='scale', step=20)
        cb.sample('chest', n, lambda t: (-10 * A.wave(t, 1.0, 0.25), 0, 0), step=1)
        nsample(n, lambda t: (-10, 0, 0), step=10)
        cb.sample('head', n, lambda t: (-2 + 4 * A.wave(t, 1.0, 0.5), 0, 0), step=1)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-38, sx * 6, 0), step=10)
            cb.sample(f'ear.{s}.2', n, lambda t, sx=sx: (-20, sx * 4, 0), step=10)
        tail(n, -6, 6, 1.0)
        mane(n, lambda t: 30 + 6 * A.wave(t, 1.0, -0.2), 0)
        trunk(n, lambda t: 35 + 6 * A.wave(t, 1.0, -0.2), step=1)
        wings(n, 0.12, step=10)
        for f in plants:
            cb.marker('step', f)
        made.append(cb.end())

    if want('strike'):
        n = 24
        cb.begin('strike', n, loop=False)
        ant = lambda t: A.pulse(t, 0.0, 0.42)          # wind-up: a crouch, feet planted, the hind legs loading
        go = lambda t: A.pulse(t, 0.3, 0.75)            # the pounce, at its fullest on `impact`
        # review (Tumblefox round 1, Puddlepup P1.2): a stretched mid-pounce, not a planted head-dip. The body crouches
        # back, then flies forward and up, long and flat: front paws reaching, hind legs pushing out behind, the head
        # leading with the face toward the target (turned a little to the monster's left, the review camera's side)
        crouch_y = lambda t: mm(0.05) * ant(t)
        crouch_z = lambda t: -mm(0.05) * ant(t)
        body_up = lambda t: 0.0
        sweep: dict = {}
        extra: dict = {}
        ik: dict = {}          # leg -> t -> (dy, dz, body_dz) for legs.angles, instead of the shared crouch
        roll: dict = {}        # leg -> t -> the thigh's y rotation (+ rolls the leg toward the monster's right)
        if strike_style(P) == 'slam':
            # Cobblemaw's card: rears up on the hind legs (the body pivots on the hind feet, which stay put), front paws
            # raised, the face toward the three-quarter camera at the top; then both front paws slam down on `impact` and
            # the body thumps level, all four feet down again by the end. Root position unchanged.
            # review (Cobblemaw round 1): the impact read as a plain level stand with the head low. Now the front paws are
            # driven down wide and forward ON `impact`, the chest drops (the body pitches onto them) and the whole body
            # squashes, held a beat, then recovers
            rear = lambda t: A.step_ease(t, 0.04, 0.36) * (1 - A.step_ease(t, 0.4, 0.5))
            slam = lambda t: A.step_ease(t, 0.4, 0.5) * (1 - A.step_ease(t, 0.62, 0.92))
            dip = 8.0                                                  # degrees the chest pitches down onto the paws
            ang = lambda t: 40.0 * rear(t) - dip * slam(t)            # + rears up on the hind feet, − drops the chest
            yh = float(P['legs']['BL'][1])
            _fx, yf, hzf = (float(v) for v in P['legs']['FL'])

            def pivot(t):
                a = math.radians(ang(t))
                return (0.0, yh * (1.0 - math.cos(a)), yh * math.sin(a))
            cb.sample('root', n, lambda t: (-ang(t), 0, 0), step=1)
            cb.sample('root', n, pivot, kind='loc', step=1)
            squash(n, lambda t: 1.0 - 0.14 * slam(t))
            cb.sample('chest', n, lambda t: (-6 * rear(t) + 4 * slam(t), 0, 0), step=1)
            nsample(n, lambda t: (14 * rear(t) - 6 * slam(t), 0, 6 * rear(t)), step=1)
            cb.sample('head', n, lambda t: (14 * rear(t) - 6 * slam(t), 0, 10 * rear(t) + 6 * slam(t)), step=1)   # the face kept toward us
            cb.sample('jaw', n, lambda t: (18 * rear(t) + 14 * slam(t), 0, 0), step=1)
            for s, sx in (('L', 1), ('R', -1)):
                cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-14 * rear(t) + 14 * slam(t), sx * 3, 0), step=1)
            tsample(0, n, lambda t: (-10 * rear(t) + 16 * slam(t), 0, 0), step=1)
            mane(n, lambda t: -6 * rear(t) + 12 * slam(t), 0, step=1)
            reach = {'F': (0, 0, 0), 'B': (0, 0, 0)}
            # every planted foot is solved in the body's frame (the root's pitch about the hind hips, its offset and the
            # squash), so the hind feet stay down while it rears (they used to lift with the pitch) and the front paws
            # land ON impact `ahead` of their rest spot; the feet are kept flat against the pitch
            ahead = 0.16 * hzf

            def to_body(t, wy, wz):
                a = math.radians(ang(t))
                v = 1.0 - 0.14 * slam(t)
                w = 1.0 / math.sqrt(max(0.2, v))
                ty, tz = wy - yh * (1.0 - math.cos(a)), wz - yh * math.sin(a)
                return ((ty * math.cos(a) - tz * math.sin(a)) / w, (ty * math.sin(a) + tz * math.cos(a)) / v)

            def planted(leg, front):
                ly = float(P['legs'][leg][1])
                dy0, z0 = legs.foot_rest(leg)

                def f(t):
                    k = slam(t)
                    if front and k <= 0.0:
                        return (0.0, 0.0, 0.0)            # reared: the front paws are posed in the air (below)
                    py, pz = to_body(t, ly + dy0 - (ahead * k if front else 0.0), z0 - (0.02 * hzf * k if front else 0.0))
                    return (py - ly - dy0, pz - z0, 0.0)
                return f
            ik = {leg: planted(leg, leg[0] == 'F') for leg in LEGS}
            # the front paws raised while reared (no IK then), flat on the ground at the slam; the hind feet flat throughout
            fr = {0: lambda t: -45 * rear(t), 1: lambda t: 75 * rear(t), 2: lambda t: -25 * rear(t) - dip * slam(t)}
            hd = {0: lambda t: 0.0, 1: lambda t: 0.0, 2: lambda t: ang(t)}
            extra = {leg: (fr if leg[0] == 'F' else hd) for leg in LEGS}
            roll = {leg: (lambda t, sg=(-1.0 if leg.endswith('L') else 1.0): sg * 14.0 * slam(t)) for leg in LEGS if leg[0] == 'F'}
        elif strike_style(P) == 'swipe':
            # Cinderlynx's card: a raking swipe. Low and coiled, the head forward and the mouth open; ONE forepaw (the left,
            # the review camera's side) draws out to the side on the wind-up and rakes forward and across at head height
            # on `impact`, claws out; the other three paws stay planted
            body_up = lambda t: -mm(0.05) * go(t)
            cb.sample('hips', n, lambda t: (0, crouch_y(t) - mm(0.05) * go(t), crouch_z(t) + body_up(t)), kind='loc', step=1)
            cb.sample('chest', n, lambda t: (-4 * ant(t) - 4 * go(t), 0, 6 * go(t)), step=1)
            # the head leans into it (down a little and forward) and turns toward the paw's side; not as far forward as
            # the paw, which passes in front of the face
            nsample(n, lambda t: (-4 * ant(t) + 10 * go(t), 0, 4 * go(t)), step=1)
            cb.sample('head', n, lambda t: (-6 * ant(t) - 4 * go(t), 0, 10 * go(t)), step=1)
            cb.sample('jaw', n, lambda t: (26 * go(t), 0, 0), step=1)
            for s, sx in (('L', 1), ('R', -1)):
                cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (8 * ant(t) - 22 * go(t), sx * 3, 0), step=1)
            tsample(0, n, lambda t: (14 * ant(t) - 6 * go(t), 0, 12 * go(t)), step=1)
            tsample(1, n, lambda t: (6 * ant(t), 0, 14 * go(t)), step=1)
            mane(n, lambda t: -4 * ant(t) + 8 * go(t), 0, step=1)
            # review (Cinderlynx round 4): the paw folded back over the wrist and hid in the ruff under the chin (the arm's
            # x rotations add up down the chain, so a paw keyed like the arm turned right round and pointed back). Now the
            # arm straightens forward and up, aimed from this rig's own leg so the paw reaches about cheek height (35–60°
            # up; short legs reach the chin) and clears the face, and the paw carries on along it, claws leading
            reach = {'F': (0, 0, 0), 'B': (0, 0, 0), 'FL': swipe_reach(P, 'FL')}
            rake = lambda t: A.step_ease(t, 0.44, 0.74)        # at impact the paw is at the near cheek, raking across
            sweep = {'FL': lambda t: 25 * ant(t) - 34 * rake(t)}      # +z = out to the left side; raked across through impact
        elif strike_style(P) == 'kick':
            # Stripeneck's card: a spinning double back-hoof kick. The body swings round on the spot (the root turns; its
            # position never moves) and turns back to face the opponent by the end; the head looks back over the
            # shoulder, and the face reads from the three-quarter camera at the start and the end.
            # review (Stripeneck round 1): the hind legs shot straight back at hip height and dragged the haunches out
            # like rubber. Now the body pitches forward over the shoulders (the withers stay put, the front legs stay
            # upright under them, hooves planted) so the rump pops UP; the hind legs fold under on the way up, hocks bent,
            # then both kick back AND up at `impact` from the raised rump; the tail flicks up. The kick comes from the
            # body's pitch and the legs' rotation; nothing translates the hips away from the chest, so the body keeps
            # its volume
            turn = lambda t: A.step_ease(t, 0.04, 0.36) * (1 - A.step_ease(t, 0.66, 0.96))
            tilt = lambda t: 24.0 * A.pulse(t, 0.14, 0.86)            # degrees, nose down: the rump up
            tuck = lambda t: A.pulse(t, 0.12, 0.5)                    # the hind legs fold under on the way up
            crouch_y = crouch_z = body_up = lambda t: 0.0             # no hips translation at all
            _fx, fy, fz = (float(v) for v in P['legs']['FL'])

            def over_withers(t):
                # the root's offset that pitches the body about the front hips (the withers), turned with the spin
                a, th = math.radians(tilt(t)), math.radians(160 * turn(t))
                dy = fy - (fy * math.cos(a) - fz * math.sin(a))
                dz = fz - (fy * math.sin(a) + fz * math.cos(a))
                return (-dy * math.sin(th), dy * math.cos(th), dz)
            cb.sample('root', n, lambda t: (tilt(t), 0, 160 * turn(t)), step=1)
            cb.sample('root', n, over_withers, kind='loc', step=1)          # (no chest pitch: it would sink the front hooves)
            # the neck lifts against the pitch, so the head stays up and looks back over the shoulder
            nsample(n, lambda t: (-0.8 * tilt(t) - 6 * go(t), 0, 18 * turn(t)), step=1)
            cb.sample('head', n, lambda t: (-0.3 * tilt(t) - 4 * go(t), 0, 22 * turn(t)), step=1)
            for s, sx in (('L', 1), ('R', -1)):
                cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (8 * ant(t) - 20 * go(t), sx * 3, 0), step=1)
            tsample(0, n, lambda t: (34 * go(t), 0, -10 * turn(t)), step=1)          # the tail flicks up
            tsample(1, n, lambda t: (18 * go(t), 0, -10 * turn(t)), step=1)
            tsample(2, n, lambda t: (-12 * go(t), 0, -6 * turn(t)), step=1)
            mane(n, lambda t: 10 * go(t), lambda t: -8 * turn(t), step=1)
            reach = {'F': (0, 0, 0), 'B': (0, 0, 0)}
            # the front legs undo the pitch (upright, hooves flat and planted); the hind legs fold (thigh forward, hock
            # bent), then kick: the thigh back, the hock opening, the hoof flicking back and up
            fr = {0: lambda t: -tilt(t), 1: lambda t: 0.0, 2: lambda t: 0.0}     # (the thigh undoes it for the whole leg)
            hd = {0: lambda t: -22 * tuck(t) + 30 * go(t), 1: lambda t: 48 * tuck(t) + 4 * go(t), 2: lambda t: -24 * tuck(t) + 40 * go(t)}
            extra = {leg: (fr if leg[0] == 'F' else hd) for leg in LEGS}
        elif strike_style(P) == 'charge':
            # review (Rammerjack round 1): a horned breed charges. It rocks back on the wind-up (feet planted), then drives
            # forward low with the head dropped below the withers so the horns lead, the front legs driving and the hind
            # legs pushing; the chains (a scarf, a beard, a mane) stream back; the face turns a little to the monster's
            # left so it still reads from the three-quarter camera. No bite: the jaw stays shut.
            stretch = lambda t: 1.0 + 0.05 * go(t) - 0.03 * ant(t)
            cb.sample('hips', n, lambda t: (0, crouch_y(t) - mm(0.15) * go(t), crouch_z(t) - mm(0.02) * go(t)), kind='loc', step=1)
            cb.sample('root', n, lambda t: (1.0 / math.sqrt(stretch(t)), stretch(t), 1.0 / math.sqrt(stretch(t))), kind='scale', step=1)
            cb.sample('spine', n, lambda t: (2 * go(t), 0, 0), step=1)
            cb.sample('chest', n, lambda t: (-6 * ant(t) + 8 * go(t), 0, 0), step=1)
            nsample(n, lambda t: (-8 * ant(t) + 22 * go(t), 0, 0), step=1)        # the neck drops forward
            # head down, horns first; turned and rolled toward the monster's left (the three-quarter camera's side) so
            # the near horn doesn't hide the eyes and brow (review: Nimbusheep round 3, Rammerjack)
            # rig_p()['charge_head_turn'] (0..1, default 1) scales that turn and roll: big ears that ride the head
            # (Petalphant's petal ears) would otherwise stand up like a sail
            ht = float(P.get('charge_head_turn', 1.0))
            cb.sample('head', n, lambda t: (-6 * ant(t) + 20 * go(t), -14 * ht * go(t), 22 * ht * go(t)), step=1)
            for s, sx in (('L', 1), ('R', -1)):
                cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (8 * ant(t) - 18 * go(t), sx * 3, 0), step=1)
            tsample(0, n, lambda t: (14 * ant(t) - 8 * go(t), 0, 0), step=1)
            tsample(1, n, lambda t: (6 * ant(t) - 6 * go(t), 0, 0), step=1)
            mane(n, lambda t: -4 * ant(t) + 22 * go(t), 0, step=1)                 # the chains stream back
            reach = {'F': (-30, 22, 8), 'B': (36, 6, 30)}      # front legs driving, hind legs pushing out behind
        elif strike_style(P) == 'lunge':
            # winged quadrupeds (Hearthwing round 1: the pounce's long flat leap read as a belly-flop sprawl under open
            # wings): it draws back low, then drives forward with the head leading, the face level on the target and the
            # jaw open, one forepaw stepping out, the hind legs pushing, the wings spread wide and raised (see below)
            crouch_y = lambda t: mm(0.06) * ant(t) - mm(0.12) * go(t)       # back on the wind-up, then the body drives on
            crouch_z = lambda t: -mm(0.05) * ant(t) - mm(0.02) * go(t)
            cb.sample('hips', n, lambda t: (0, crouch_y(t), crouch_z(t)), kind='loc', step=1)
            cb.sample('spine', n, lambda t: (2 * ant(t) - 3 * go(t), 0, 0), step=1)
            cb.sample('chest', n, lambda t: (4 * ant(t) - 8 * go(t), 0, 0), step=1)          # the chest lifts into it
            nsample(n, lambda t: (-8 * ant(t) + 16 * go(t), 0, 4 * go(t)), step=1)           # drawn back, then reaching
            cb.sample('head', n, lambda t: (-4 * ant(t) - 12 * go(t), 0, 8 * go(t)), step=1)  # the face leads, level
            cb.sample('jaw', n, lambda t: (26 * go(t), 0, 0), step=1)
            for s, sx in (('L', 1), ('R', -1)):
                cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (8 * ant(t) - 22 * go(t), sx * 3, 0), step=1)
            tsample(0, n, lambda t: (14 * ant(t) + 8 * go(t), 0, 0), step=1)
            tsample(1, n, lambda t: (6 * ant(t) - 6 * go(t), 0, 0), step=1)
            mane(n, lambda t: -4 * ant(t) + 12 * go(t), 0, step=1)
            reach = {'F': (0, 0, 0), 'B': (18, -6, 8), 'FL': (-34, 12, 20)}   # one forepaw steps out; the hind legs drive
        else:
            cb.sample('hips', n, lambda t: (0, crouch_y(t) - mm(0.17) * go(t), crouch_z(t) + mm(0.06) * go(t)), kind='loc', step=1)
            cb.sample('root', n, lambda t: (1.0 / math.sqrt(1.0 + 0.09 * go(t) - 0.04 * ant(t)), 1.0 + 0.09 * go(t) - 0.04 * ant(t),
                                            1.0 / math.sqrt(1.0 + 0.09 * go(t) - 0.04 * ant(t))), kind='scale', step=1)
            cb.sample('spine', n, lambda t: (-4 * go(t), 0, 0), step=1)
            cb.sample('chest', n, lambda t: (-6 * go(t), 0, 0), step=1)
            nsample(n, lambda t: (-6 * ant(t) + 12 * go(t), 0, 0), step=1)       # the neck reaches forward (+x) at the impact
            cb.sample('head', n, lambda t: (-6 * ant(t) - 12 * go(t), 0, 8 * go(t)), step=1)   # the face stays level, on the target
            cb.sample('jaw', n, lambda t: (28 * go(t), 0, 0), step=1)             # a visible bite at the impact
            for s, sx in (('L', 1), ('R', -1)):
                cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (8 * ant(t) - 22 * go(t), sx * 3, 0), step=1)
            tsample(0, n, lambda t: (16 * ant(t) - 10 * go(t), 0, 0), step=1)
            tsample(1, n, lambda t: (6 * ant(t) - 8 * go(t), 0, 0), step=1)
            mane(n, lambda t: -4 * ant(t) + 10 * go(t), 0, step=1)                 # modest: locks never stand up like quills
            reach = {'F': (-68, -12, -22), 'B': (40, 8, 32)}      # the pounce: front legs forward, hind legs pushed out behind
        for leg in LEGS:
            r = reach.get(leg, reach[leg[0]])

            def leg_fn(t, leg=leg, r=r, j=0):
                c = legs.angles(leg, *ik[leg](t)) if leg in ik else legs.angles(leg, -crouch_y(t), 0.0, crouch_z(t) + body_up(t))
                sw = sweep[leg](t) if (j == 0 and leg in sweep) else 0.0
                ex = extra[leg][j](t) if leg in extra else 0.0
                ro = roll[leg](t) if (j == 0 and leg in roll) else 0.0
                return (c[j] + r[j] * go(t) + ex, ro, sw)
            for j, part in enumerate(('thigh', 'shin', 'foot')):
                cb.sample(f'{part}.{leg}', n, lambda t, f=leg_fn, j=j: f(t, j=j), step=1)
        # the trunk winds back in, then lashes out; the wings mantle on the wind-up and beat down into the lunge
        trunk(n, lambda t: 50 * ant(t) - 70 * go(t), step=1)
        # wide open and raised at the impact (k reaches the recipe's spread pose), a downbeat after it (Hearthwing round 1:
        # barely open, beating down onto the lunge)
        wings(n, lambda t: min(1.0, 0.7 * ant(t) + 1.1 * go(t)), lambda t: -15 * ant(t) - 14 * go(t) + 30 * A.pulse(t, 0.62, 0.98))
        cb.marker('impact', 13)
        cb.face(1, 'angry')
        cb.face(20, 'neutral')
        made.append(cb.end())

    if want('cast'):
        n = 36
        cb.begin('cast', n, loop=False)
        up = lambda t: A.step_ease(t, 0.0, 0.3) * (1 - A.step_ease(t, 0.7, 1.0))
        # a trunk rig (Petalphant round 2, 5-poses attack): ONE foreleg up and a smaller rear, the trunk high and
        # forward with its tip pointing out at the target and the bud fully open; the others rear on both forelegs
        trunked = bool(TR)
        rear = CAST_TRUNK_REAR if trunked else 38
        cb.sample('chest', n, lambda t: (-rear * up(t), 0, 0), step=1)
        cb.sample('spine', n, lambda t: (-(0 if trunked else 10) * up(t), 0, 0), step=1)
        nsample(n, lambda t: (12 * up(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (8 * up(t) + 2 * A.wave(t, 6.0) * A.pulse(t, 0.3, 0.7), 0, 0), step=1)
        cb.sample('hips', n, lambda t: (0, mm(0.03) * up(t), mm(0.01) * up(t)), kind='loc', step=1)
        for leg in (('FL',) if trunked else ('FL', 'FR')):
            cb.sample(f'thigh.{leg}', n, lambda t: (-60 * up(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t: (-25 * up(t), 0, 0), step=1)
            cb.sample(f'foot.{leg}', n, lambda t: (40 * up(t), 0, 0), step=1)
        hk = 0.35 if trunked else 1.0
        for leg in ('BL', 'BR'):
            cb.sample(f'thigh.{leg}', n, lambda t: (20 * hk * up(t), 0, 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t: (-28 * hk * up(t), 0, 0), step=1)
            cb.sample(f'foot.{leg}', n, lambda t: (8 * hk * up(t), 0, 0), step=1)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-22 * up(t), sx * (4 + 6 * A.wave(t, 4.0) * up(t)), 0), step=1)
        tail(n, 14, 6, 1.0)
        # the trunk rises and trumpets; the wings open wide with a shimmer
        # review (Petalphant round 1): the trunk curled back to the brow with the bud end-on; now it swings up from the
        # base, high and forward, and the bud opens fully toward the front
        trunk(n, lambda t: -CAST_TRUNK_RAISE * up(t) + 6 * A.wave(t, 6.0) * up(t), step=1, raise_=True, tip=lambda t: CAST_TRUNK_TIP * up(t))
        bud(n, up, step=1)
        wings(n, up, lambda t: -16 * up(t) + 10 * A.wave(t, 6.0) * up(t))     # spread and raised, shimmering
        cb.marker('release', 20)
        cb.face(1, 'strain')
        cb.face(28, 'neutral')
        made.append(cb.end())

    if want('shove'):
        n = 24
        cb.begin('shove', n, loop=False)
        ant = lambda t: A.pulse(t, 0.0, 0.36)
        go = lambda t: A.pulse(t, 0.28, 0.7)
        cb.sample('hips', n, lambda t: (0, mm(0.04) * ant(t) - mm(0.09) * go(t), 0), kind='loc', step=1)
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
        cb.sample('hips', n, lambda t: (0, mm(0.05) * k(t), mm(0.01) * k(t)), kind='loc', step=1)
        # review (Starhowl round 2): knocked back and to the side about 30 degrees, never the muzzle at the sky; the eyes
        # wince shut. Round 5: turned toward the camera's side with the muzzle tipped up it still read as a howl (the hips'
        # shove back and the chest lift add about 20 degrees of lift to the head). Now the head is knocked AWAY from the
        # three-quarter camera (toward the monster's right) and rolled with it, the muzzle level or a touch down
        cb.sample('chest', n, lambda t: (-4 * k(t), 0, 0), step=1)
        neck_fn = lambda t: (-2 * k(t), 0, -10 * k(t))
        head_fn = lambda t: (8 * k(t), -10 * k(t), -22 * k(t))
        nsample(n, neck_fn, step=1)
        cb.sample('head', n, head_fn, step=1)
        squash(n, lambda t: 1.0 - 0.06 * k(t))
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (28 * k(t), sx * 3, 0), step=1)
        tsample(0, n, lambda t: (-10 * k(t), 0, 0), step=1)
        mane(n, lambda t: -18 * k(t), 0, step=1, against={'head': head_fn, 'neck': neck_fn})
        trunk(n, lambda t: 30 * k(t), step=1, against={'head': head_fn, 'neck': neck_fn})
        bud(n, lambda t: 0.15 * A.pulse(t, 0.0, 0.6), step=1)        # a small flick; the bud stays closed (5-poses hit)
        wings(n, lambda t: 0.5 * k(t), lambda t: -10 * k(t))           # a startled flare
        eyes_shut(n, lambda t: 1.6 * A.pulse(t, 0.02, 0.75))          # a squeezed-shut wince at the peak, open again
        cb.face(1, 'surprised')
        cb.face(12, 'neutral')
        made.append(cb.end())

    if want('hit_heavy'):
        n = 24
        cb.begin('hit_heavy', n, loop=False)
        k = lambda t: A.pulse(t, 0.0, 0.55)
        rec = lambda t: A.step_ease(t, 0.5, 1.0)
        shake = lambda t: math.sin(t * 2 * math.pi * 3) * (1 - rec(t)) * A.step_ease(t, 0.1, 0.3)
        back_y = lambda t: mm(0.16) * k(t)
        drop = lambda t: -mm(0.07) * k(t)
        # review (Tumblefox round 1): the whole body is knocked back and hunches, the head ducking aside (to the
        # monster's left, the review camera's side) with the chin tucked; never snapped up (that stretched the chest
        # into a long "beard"). The feet stay planted, braced and a little splayed, as the body slides back and sinks
        cb.sample('hips', n, lambda t: (0, back_y(t), drop(t)), kind='loc', step=1)
        # review (Cinderlynx): it must read clearly: shoved back AND down, the body bending away, the head turned well aside
        cb.sample('root', n, lambda t: (0, 5 * shake(t), 0), step=1)
        cb.sample('spine', n, lambda t: (0, 0, 8 * k(t)), step=1)
        cb.sample('chest', n, lambda t: (0, 0, 10 * k(t)), step=1)
        neck_fn = lambda t: (6 * k(t), 0, 14 * k(t))
        head_fn = lambda t: (12 * k(t), 12 * k(t), 30 * k(t))
        nsample(n, neck_fn, step=1)
        cb.sample('head', n, head_fn, step=1)
        squash(n, lambda t: 1.0 - 0.1 * k(t))
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (14 * k(t), sx * 2, 0), step=1)
            cb.sample(f'ear.{s}.2', n, lambda t, sx=sx: (8 * k(t), 0, 0), step=1)
        tsample(0, n, lambda t: (-18 * k(t), 0, 0), step=1)
        mane(n, lambda t: -14 * k(t), lambda t: 8 * math.sin(t * 2 * math.pi * 3) * k(t), step=1, against={'head': head_fn, 'neck': neck_fn})
        for leg in LEGS:
            out = 10 * legs.splay_k * (1 if leg.endswith('L') else -1)
            for j, part in enumerate(('thigh', 'shin', 'foot')):
                # the paws slide a little with the shove (never a paw lifted off the ground: the legs stay within reach)
                cb.sample(f'{part}.{leg}', n, lambda t, leg=leg, j=j, o=(out if j == 0 else 0.0):
                          (legs.angles(leg, -0.6 * back_y(t), 0.0, drop(t))[j], o * k(t), 0), step=1)
        trunk(n, lambda t: 45 * k(t), lambda t: 12 * math.sin(t * 2 * math.pi * 3) * k(t), step=1, against={'head': head_fn, 'neck': neck_fn})
        wings(n, lambda t: 0.7 * k(t), lambda t: -14 * k(t))           # flung open by the blow
        eyes_shut(n, lambda t: 1.7 * A.pulse(t, 0.02, 0.72))          # screwed shut through the recoil, open again
        cb.face(1, 'strain')
        cb.face(18, 'neutral')
        made.append(cb.end())

    if want('ko'):
        n = 36
        cb.begin('ko', n, loop=False, hold=True)
        wob = lambda t: (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = lambda t: A.step_ease(t, 0.4, 0.82)
        curl = lambda t: A.step_ease(t, 0.38, 0.85)
        # review (Tumblefox round 1): no tipped toy with four straight legs and the face twisted up. It topples onto its
        # right side, so the belly, the tucked paws and the face turn to the monster's left (the review camera's side),
        # comes to rest lying on the ground, and curls up: the back rounds, the head tucks toward the chest with the
        # face toward us, the paws fold in and the tail curls round
        roll = KO_ROLL
        lie = body_halfwidth(P)
        cb.sample('root', n, lambda t: (0, 10 * math.sin(t * 2 * math.pi * 2.5) * wob(t) - roll * fall(t), 0), step=1)

        lift_tab = P.get('ko_lift') or []

        def lift(t: float) -> float:
            """build_ultra's settle_ko: extra height (metres) per moment so no frame of the fall sinks into the ground."""
            if not lift_tab:
                return 0.0
            for (t0, d0), (t1, d1) in zip(lift_tab[:-1], lift_tab[1:]):
                if t0 <= t <= t1:
                    return d0 + (d1 - d0) * (t - t0) / max(t1 - t0, 1e-9)
            return lift_tab[0][1] if t < lift_tab[0][0] else lift_tab[-1][1]

        def lying(t: float) -> tuple[float, float, float]:
            # the hips' offset in the rolled root's frame that sets the spine lie·fall + hz·(1 − fall) above the ground
            f = fall(t)
            h = hz * (1 - f) + lie * f + lift(t)
            a = math.radians(roll * f)
            return (h * math.sin(a), 0.0, h * math.cos(a) - hz)
        cb.sample('hips', n, lying, kind='loc', step=1)
        cb.sample('spine', n, lambda t: (12 * curl(t), 0, 0), step=1)
        cb.sample('chest', n, lambda t: (14 * curl(t), 0, 0), step=1)
        # the neck and head roll back against the fall (shared, so the neck never twists hard), keeping the face upright
        neck_fn = lambda t: (12 * curl(t), 24 * fall(t), 0)
        head_fn = lambda t: (16 * curl(t), 30 * fall(t), 0)
        nsample(n, neck_fn, step=1)
        cb.sample('head', n, head_fn, step=1)
        # review (Nimbusheep, Cinderlynx): no stiff pegs. The legs fold loosely along the body as in sleep: knees and hocks
        # flexed, the front paws tucked back under the chest, the hind paws forward under the belly, in line with the spine
        # rig_p()['ko_leg_fold'] (0..1, default 1) scales the fold: a long coat that hangs near the ground (Nimbusheep's
        # wool) swallows fully tucked legs, the hooves poking out of its side; at about 0.4 they lie outside it, loose and bent
        fold = float(P.get('ko_leg_fold', 1.0))
        tuck = {'F': (-70, 118, -45), 'B': (62, -112, 48)}
        for leg in LEGS:
            r = tuck[leg[0]]
            for j, part in enumerate(('thigh', 'shin', 'foot')):
                cb.sample(f'{part}.{leg}', n, lambda t, v=r[j] * fold: (v * curl(t), 0, 0), step=1)
        ears(n, 10, 0)
        tsample(0, n, lambda t: (-25 * curl(t), 0, 10 * curl(t)), step=1)
        tsample(1, n, lambda t: (-25 * curl(t), 0, 10 * curl(t)), step=1)
        tsample(2, n, lambda t: (-20 * curl(t), 0, 8 * curl(t)), step=1)
        trunk(n, lambda t: 20 * fall(t), lambda t: 15 * fall(t), step=1, against={'head': head_fn, 'neck': neck_fn})
        # review (Starhowl round 2): the mane chains lie down toward the ground (the body's right side, slightly toward the
        # belly) instead of standing up as a ridge
        mane_droop(n, fall, (-math.sin(math.radians(KO_ROLL)), 0.0, -math.cos(math.radians(KO_ROLL))), against={'head': head_fn, 'neck': neck_fn})
        wings(n, lambda t: 0.25 * fall(t), lambda t: 8 * fall(t))
        eyes_shut(n, lambda t: max(0.8 * A.pulse(t, 0.0, 0.3), A.step_ease(t, 0.35, 0.6)))   # wince, then shut and staying shut
        cb.face(1, 'strain')
        cb.face(20, 'dizzy')
        made.append(cb.end())

    if want('win'):
        n = 60
        cb.begin('win', n, loop=True)
        air = lambda t: A.pulse(t, 0.04, 0.36)
        spin = lambda t: 360 * A.step_ease(t, 0.42, 0.82)
        cb.sample('root', n, lambda t: (0, 0, mm(0.14) * air(t)), kind='loc', step=1)
        cb.sample('root', n, lambda t: (0, 0, spin(t)), step=1)
        squash(n, lambda t: 1.0 + 0.1 * air(t) - 0.12 * A.pulse(t, 0.34, 0.44) + 0.04 * A.wave(t, 4.0) * A.step_ease(t, 0.84, 0.9))
        cb.sample('chest', n, lambda t: (-8 * air(t), 0, 0), step=1)
        cb.sample('head', n, lambda t: (-10 * air(t), 10 * A.wave(t, 2.0) * A.step_ease(t, 0.84, 0.9), 0), step=1)
        ears(n, -8, 12, 3.0)
        tail(n, 26, 30, 4.0)
        mane(n, lambda t: 18 * air(t) - 10 * A.pulse(t, 0.34, 0.44), lambda t: -20 * A.pulse(t, 0.42, 0.82), step=1)
        # review (Tumblefox round 1): the legs dangled straight in the air. Now they tuck up under the body: the front
        # paws fold back under the chest, the hind paws fold forward under the belly
        tuck = {'F': (-50, 95, -30), 'B': (48, -95, 45)}
        for leg in LEGS:
            r = tuck[leg[0]]
            for j, part in enumerate(('thigh', 'shin', 'foot')):
                cb.sample(f'{part}.{leg}', n, lambda t, v=r[j]: (v * air(t), 0, 0), step=1)
        # wide open the whole loop, beating twice; the trunk trumpets; the bud open
        trunk(n, lambda t: -60 + 10 * A.wave(t, 2.0), lambda t: 10 * A.wave(t, 1.0), step=1)
        bud(n, 1.0, step=30)
        wings(n, 1.0, lambda t: -14 + 24 * A.wave(t, 2.0))        # spread the whole loop, beating twice, mostly raised
        if P.get('jaw_open'):
            cb.sample('jaw', n, lambda t: (16 + 6 * air(t), 0, 0), step=1)      # a happy open smile, wider in the air
        cb.face(1, 'happy')
        cb.marker('land', 22)
        made.append(cb.end())

    # ---- Battle 3D: moving sideways while facing the opponent (root motion runs along the monster's own ±X)
    def lateral(leg: str, frame: int, dx: float, dz: float, body_dz: float = 0.0) -> None:
        """Put a foot `dx` sideways (+ = the monster's left, +X) and `dz` up from its rest spot: the thigh rolls the leg
        out, the two-bone IK takes up the lift along the rolled leg, and the foot rolls back flat."""
        x, y, hz0 = P['legs'][leg]
        l1, l2 = legs.lengths(leg)
        dy0, ankle = legs.foot_rest(leg)
        h = hz0 + body_dz - ankle - dz
        roll = math.degrees(math.atan2(dx, max(mm(0.05), h)))
        reach = math.hypot(dx, h)
        th, kn = A.leg_ik(Vector((0, 0, reach)), Vector((0, dy0, 0)), l1, l2, Vector((0, -1, 0)))
        rth, rkn = legs.rest[leg]
        # a +y roll swings a downward bone's tip toward −X, so a foot going +X rolls by −y
        cb.rot(f'thigh.{leg}', frame, x=-(th - rth), y=-roll)
        cb.rot(f'shin.{leg}', frame, x=-(kn - rkn))
        cb.rot(f'foot.{leg}', frame, x=(th - rth) + (kn - rkn), y=roll)

    def strafe(name: str, side: int) -> None:
        n = 24
        stride = P.get('stride', 0.18) * 0.75
        stance = 0.56
        cb.begin(name, n, loop=True, root_speed=stride / (stance * n / A.FPS))
        phases = {'FL': 0.0, 'BR': 0.0, 'FR': 0.5, 'BL': 0.5}      # diagonal pairs: a sideways trot-shuffle
        plants: list[int] = []
        for f in range(1, n + 2):
            t = (f - 1) / n
            bob = mm(0.008) * abs(math.sin(t * 2 * math.pi * 2))
            for leg in LEGS:
                p = (t + phases[leg]) % 1.0
                if p < stance:
                    u = p / stance
                    dx = side * (stride / 2 - stride * u)       # planted: slides against the motion
                    dz = 0.0
                else:
                    u = (p - stance) / (1 - stance)
                    dx = side * (-stride / 2 + stride * C.ease_in_out(u))
                    dz = mm(0.045) * math.sin(u * math.pi)
                lateral(leg, f, dx, dz, body_dz=bob)
        for leg in LEGS:
            plants.append(1 + int(round(((1.0 - phases[leg]) % 1.0) * n)) % n)
        # lean into the step, head steady on the opponent, ears and tail trailing
        cb.sample('root', n, lambda t: (0, side * (3.0 + 1.0 * A.wave(t, 2.0)), 0), step=2)
        cb.sample('chest', n, lambda t: (3 + 1.5 * A.wave(t, 2.0), 0, side * 2.0), step=2)
        cb.sample('head', n, lambda t: (-5 - 1.5 * A.wave(t, 2.0, 0.5), -side * 3.0, -side * 4.0), step=2)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-6, sx * 3 - side * 6 + 3 * A.wave(t, 2.0, 0.2), 0), step=2)
        tsample(0, n, lambda t: (16, 0, -side * 10 + 6 * A.wave(t, 2.0)), step=2)
        tsample(1, n, lambda t: (8, 0, -side * 12 + 8 * A.wave(t, 2.0, -0.12)), step=2)
        tsample(2, n, lambda t: (4, 0, -side * 14 + 10 * A.wave(t, 2.0, -0.24)), step=2)
        mane(n, lambda t: 6 + 3 * A.wave(t, 2.0), lambda t: -side * 12 + 4 * A.wave(t, 2.0, -0.1))
        trunk(n, lambda t: 4 * A.wave(t, 2.0), lambda t: -side * 12 + 4 * A.wave(t, 2.0, -0.1))
        for f in sorted(set(plants)):
            cb.marker('step', f)
        made.append(cb.end())

    if want('strafe_l'):
        strafe('strafe_l', 1)
    if want('strafe_r'):
        strafe('strafe_r', -1)

    def sidestep(name: str, side: int) -> None:
        """A quick dodge hop to the side: 8 ticks (0.27 s). The runtime carries the root SIDESTEP_DISTANCE metres (model
        units) along ±X over the clip; the body crouches, springs, tucks its legs and lands on `land`."""
        n = 8
        cb.begin(name, n, loop=False, root_speed=SIDESTEP_DISTANCE / (n / A.FPS))
        air = lambda t: A.pulse(t, 0.18, 0.92)
        crouch = lambda t: A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        cb.sample('root', n, lambda t: (0, 0, mm(0.07) * air(t)), kind='loc', step=1)
        cb.sample('root', n, lambda t: (0, side * 14 * air(t), side * 6 * air(t)), step=1)
        squash(n, lambda t: 1.0 - 0.12 * crouch(t) + 0.08 * air(t))
        cb.sample('chest', n, lambda t: (-6 * air(t), 0, side * 4 * air(t)), step=1)
        cb.sample('head', n, lambda t: (-4 * air(t) + 6 * crouch(t), -side * 10 * air(t), -side * 8 * air(t)), step=1)
        for s, sx in (('L', 1), ('R', -1)):
            cb.sample(f'ear.{s}.1', n, lambda t, sx=sx: (-18 * air(t) + 12 * crouch(t), sx * 3 - side * 6 * air(t), 0), step=1)
            cb.sample(f'ear.{s}.2', n, lambda t, sx=sx: (-8 * air(t), -side * 3 * air(t), 0), step=1)
        tsample(0, n, lambda t: (18 * air(t), 0, -side * 20 * air(t)), step=1)
        tsample(1, n, lambda t: (8 * air(t), 0, -side * 16 * air(t)), step=1)
        mane(n, lambda t: 10 * air(t), lambda t: -side * 22 * air(t), step=1)
        for leg in LEGS:
            tuck = -24 if leg[0] == 'F' else 26
            out = side * 10 * (1 if (leg.endswith('L') == (side > 0)) else -0.4)
            cb.sample(f'thigh.{leg}', n, lambda t, tuck=tuck, out=out: (tuck * air(t), -out * air(t), 0), step=1)
            cb.sample(f'shin.{leg}', n, lambda t, tuck=tuck: (-tuck * 1.3 * air(t), 0, 0), step=1)
            cb.sample(f'foot.{leg}', n, lambda t, tuck=tuck, out=out: (tuck * 0.3 * air(t), out * air(t), 0), step=1)
        trunk(n, lambda t: -15 * air(t), lambda t: -side * 20 * air(t), step=1)
        wings(n, lambda t: 0.3 * air(t), step=1)
        cb.marker('land', n)
        made.append(cb.end())

    if want('sidestep_l'):
        sidestep('sidestep_l', 1)
    if want('sidestep_r'):
        sidestep('sidestep_r', -1)

    return made


# The sidestep's hop: 1.4 arena metres for a 1 m Puddlepup scaled to 150 arena units (100 units = 1 m), i.e.
# 140 / 150 model metres. The runtime moves the root (model units × heightUnits / restHeight = arena units).
# Not scaled by size_k on purpose: every breed is modelled HEIGHT_UNITS / 150 m tall, so a model metre is 150 arena
# units for all of them, and the hop covers the same arena distance (the game's sidestep is one distance for all).
SIDESTEP_DISTANCE = 1.4 * 100 / 150

# Root motion directions in the glTF frame (Y up, the monster faces +Z, +X is its left).
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}

STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
# Battle 3D (the arena's free movement): side-stepping while facing the opponent, and the dodge hop.
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']
