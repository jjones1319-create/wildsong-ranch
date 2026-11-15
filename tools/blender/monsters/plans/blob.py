"""The blob body plan (ART_2_PLAN §4, batch 5): rig template, sockets, springs and the clip generators for soft,
squashy monsters that sit on the ground: Bloatoad (a squat toad on four short legs, a throat sac that balloons, a
lashing tongue) and Scrollopus (an octopus: eight tentacles, some curled on the ground, some holding a scroll, a quill
and a book).

A recipe selects it with `PLAN = 'blob'` (tools/blender/monsters/breeds/RECIPE.md, "Blob plan"). The same build
(build_ultra.py) drives it as every other plan: rig_specs, sockets, springs, chain_groups, heatless, make_clips,
STAR_CLIPS, MOVE_CLIPS, ROOT_DIRS and KO_ROLL (ko falls onto its back, its face or its side: the build measures and
settles `body_width`, the centre's height as it lies, lifting any sinking frame with `ko_lift`).

Space: metres; the monster faces −Y, Z is up, +X is its left. Model it sitting. From rig_p() (`P`):
  hip                  the body's centre: the bone `body` (parent `root`) carries everything; it leans, turns, hops
                       and falls about this point but never squashes
  chest                the top of the squash chain (the crown of the head-body)
  body_base            its bottom, on or near the ground [straight under `hip`, 2 cm up]: the squash chain `hips`
                       (base → ⅓), `chest` (⅓ → head_split), `head` (head_split → top) squashes and stretches about it,
                       so the bottom stays on the ground
  head_c, head_r       the face's centre and size (the jaw, the mouth socket, the review framing)
Options (RECIPE.md): size_k, head_split, jaw, sac, tongue, legs, tentacles, chains, props, strike_style, cast_style,
ko_style, ko_pitch, ko_roll, body_width, ko_lift, and the per-clip knobs every plan has.
Rotations are world-aligned degrees relative to the parent at rest (lib.anim.ClipBuilder.rot): +x tips an upright bone
forward (and lifts a backward-pointing one), +z turns toward the monster's left, +y tilts toward its left.
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

PLAN = 'blob'
SIDES = K.SIDES
KO_ROLL = 80.0              # the build's first guess of body_width; the settle corrects it for any ko style
STRIKE_STYLES = ('tongue', 'belly', 'slap', 'ink')
CAST_STYLES = ('inflate', 'raise')
KO_STYLES = ('back', 'front', 'roll')
TENTACLE_ROLES = ('ground', 'hold', 'free')
SPRINGS = []                # Art 2.0 compatibility only; the Ultra build calls springs(P)
KINDS = ('tassel', 'frill', 'tail', 'antenna')
HEATLESS_KINDS = ('tassel',)

SIDESTEP_DISTANCE = 1.4 * 100 / 150      # the same arena distance as every other plan
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}
STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']
# legged gaits: (frames, stride as a share of the leg's reach, the planted share of the cycle, foot lift as a share of
# the leg); run and dash hop (every foot together), the rest crawl in diagonal pairs
GAITS = {'walk': (30, 0.45, 0.7, 0.16), 'run': (20, 0.8, 0.5, 0.2), 'dash': (20, 1.0, 0.42, 0.24),
         'step_fwd': (24, 0.4, 0.65, 0.14), 'step_back': (24, 0.34, 0.65, 0.12), 'strafe': (24, 0.36, 0.65, 0.14)}
# without legs: a shuffle on the tentacles (model metres per second at Puddlepup's size; × size_k)
SHUFFLE = {'walk': 0.22, 'run': 0.6, 'dash': 0.9, 'step_fwd': 0.22, 'step_back': 0.18, 'strafe': 0.22}


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def _v(p) -> Vector:
    return Vector(p)


def base_of(P: dict) -> Vector:
    if P.get('body_base'):
        return _v(P['body_base'])
    h = _v(P['hip'])
    return Vector((h.x, h.y, 0.02 * size_of(P)))


def squash_points(P: dict) -> list[Vector]:
    b, t = base_of(P), _v(P['chest'])
    split = float(P.get('head_split', 2 / 3))
    return [b, b.lerp(t, min(1 / 3, 0.9 * split)), b.lerp(t, split), t]


def jaw_points(P: dict) -> tuple[Vector, Vector]:
    if P.get('jaw'):
        return _v(P['jaw']['head']), _v(P['jaw']['tail'])
    hc, hr = _v(P['head_c']), float(P['head_r'])
    return hc + Vector((0, -0.3 * hr, -0.45 * hr)), hc + Vector((0, -0.9 * hr, -0.55 * hr))


def sac_of(P: dict) -> dict | None:
    """The throat sac: {'head' (where it hangs from), 'tail' (its far side), 'parent': 'head', 'max': 1.8}."""
    s = P.get('sac')
    if not s:
        return None
    return {'head': _v(s['head']), 'tail': _v(s['tail']), 'parent': s.get('parent', 'head'), 'max': float(s.get('max', 1.8))}


def tongue_of(P: dict) -> dict | None:
    """The tongue: {'points': [p0 … pN] inside the mouth, 'parent': 'jaw', 'reach': metres it lashes out}."""
    t = P.get('tongue')
    if not t:
        return None
    pts = [_v(p) for p in t['points']]
    if len(pts) < 2:
        raise ValueError('tongue: needs at least 2 points')
    return {'points': pts, 'parent': t.get('parent', 'jaw'), 'bones': [f'tongue.{i + 1}' for i in range(len(pts) - 1)],
            'reach': float(t.get('reach', 0.6 * size_of(P))), 'dir': (pts[-1] - pts[0]).normalized()}


def legs(P: dict) -> list[dict]:
    """As the shelled plan's: P['legs'] lists the left legs front to back ({'hip', 'knee', 'ankle', 'toe'?,
    'parent'?: 'body'}); the right side mirrors them. Bones leg<i>, shin<i>, foot<i> (.L / .R)."""
    out = []
    for tag, s in SIDES:
        for i, lg in enumerate(P.get('legs') or [], start=1):
            toe = mirror(lg['toe'], s) if lg.get('toe') else None
            out.append({'i': i, 'tag': tag, 's': s, 'upper': f'leg{i}.{tag}', 'lower': f'shin{i}.{tag}',
                        'foot': f'foot{i}.{tag}' if toe is not None else None,
                        'hip': mirror(lg['hip'], s), 'knee': mirror(lg['knee'], s), 'ankle': mirror(lg['ankle'], s),
                        'toe': toe, 'parent': lg.get('parent', 'body'), 'front': i == 1})
    return out


def tentacles(P: dict) -> list[dict]:
    """Each tentacle: {'name', 'points', 'parent': 'body', 'role' ('ground': curled on the ground, carrying it;
    'hold': raised, holding a prop; 'free'), 'mirror'} → bones <name>.1..N (mirror: <name>L / <name>R)."""
    out = []
    for m in P.get('tentacles') or []:
        role = m.get('role', 'ground')
        if role not in TENTACLE_ROLES:
            raise ValueError(f"tentacle {m.get('name')}: role {role!r}, one of {', '.join(TENTACLE_ROLES)}")
        nm0 = m.get('name', 'tentacle')
        twins = [(nm0 + 'L', 1), (nm0 + 'R', -1)] if m.get('mirror') else [(nm0, 1)]
        for nm, s in twins:
            pts = [mirror(p, s) for p in m['points']]
            if len(pts) < 2:
                raise ValueError(f'tentacle {nm}: needs at least 2 points')
            d = pts[-1] - pts[0]
            dh = Vector((d.x, d.y, 0.0))
            out.append({'name': nm, 'role': role, 'parent': m.get('parent', 'body'), 'points': pts,
                        'side': 1 if pts[-1].x >= 0 else -1, 'spring': bool(m.get('spring', role == 'free')),
                        'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)],
                        'dirs': [(pts[i + 1] - pts[i]).normalized() for i in range(len(pts) - 1)],
                        'out': dh.normalized() if dh.length > 1e-6 else Vector((0, -1, 0)),
                        'length': sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))})
    return out


def chains(P: dict) -> list[dict]:
    """Other chains (a cap's tassel, a frill, a tail, feelers), as the shelled plan's."""
    out = []
    for m in P.get('chains') or []:
        kind = m.get('kind', 'tassel')
        if kind not in KINDS:
            raise ValueError(f"chain {m.get('name')}: kind {kind!r}, one of {', '.join(KINDS)}")
        nm0 = m.get('name', kind)
        twins = [(nm0 + 'L', 1), (nm0 + 'R', -1)] if m.get('mirror') else [(nm0, 1)]
        for nm, s in twins:
            pts = [mirror(p, s) for p in m['points']]
            out.append({'name': nm, 'kind': kind, 'parent': m.get('parent', 'head'), 'points': pts, 'side': s,
                        'stiff': float(m.get('stiff', 0.0)), 'heat': bool(m.get('heat', kind not in HEATLESS_KINDS)),
                        'spring': bool(m.get('spring', True)),
                        'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)]})
    return out


def _style(P: dict, key: str, allowed: tuple, default: str) -> str:
    st = P.get(key, default)
    if st not in allowed:
        raise ValueError(f"{key} {st!r}: one of {', '.join(allowed)}")
    return st


def strike_style(P: dict) -> str:
    return _style(P, 'strike_style', STRIKE_STYLES, 'tongue' if P.get('tongue') else ('slap' if P.get('tentacles') else 'belly'))


def cast_style(P: dict) -> str:
    return _style(P, 'cast_style', CAST_STYLES, 'raise' if P.get('tentacles') else 'inflate')


def ko_style(P: dict) -> str:
    return _style(P, 'ko_style', KO_STYLES, 'back')


def pick_arm(P: dict, key: str) -> str | None:
    """The tentacle a strike uses: P[key] (a tentacle's name), else the first 'free', else 'hold', else any, on its
    left (the in-game camera sees the monster's left side)."""
    T = tentacles(P)
    if not T:
        return None
    if P.get(key):
        if not any(m['name'] == P[key] for m in T):
            raise ValueError(f"{key} {P[key]!r}: no such tentacle ({', '.join(m['name'] for m in T)})")
        return P[key]
    for role in ('free', 'hold', 'ground'):
        c = [m for m in T if m['role'] == role]
        if c:
            return max(c, key=lambda m: (m['points'][-1].x, -m['points'][-1].y))['name']
    return T[0]['name']


def springs(P: dict) -> list[dict]:
    """Free tentacles and every chain that springs (the ground ones and the holding ones are animated whole)."""
    out = [{'kind': 'tentacle', 'chain': m['bones']} for m in tentacles(P) if m['spring']]
    out += [{'kind': m['kind'], 'chain': m['bones']} for m in chains(P) if m['spring']]
    return out


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → kind, for a recipe's CLIP_CALM: each tentacle (kind 'tentacle'), 'tongue', each chain by
    its name or kind, 'leg' (leg<i>, shin<i>, foot<i>)."""
    out = {m['name']: 'tentacle' for m in tentacles(P)}
    out['tongue'] = 'tongue'
    for m in chains(P):
        out[m['name']] = m['kind']
    for i in range(1, len(P.get('legs') or []) + 1):
        for p in ('leg', 'shin', 'foot'):
            out[f'{p}{i}'] = 'leg'
    return out


def heatless(P: dict) -> set[str]:
    """Bones the recipe's body_weight_regions skins (their heat goes to the parent): the tongue, the sac, every tentacle
    (unless P['tentacle_heat']: neighbours would share weights), tassels (unless heat=True)."""
    out = {'tongue', 'sac'}
    if not P.get('tentacle_heat'):
        out |= {m['name'] for m in tentacles(P)}
    out |= {m['name'] for m in chains(P) if not m['heat']}
    return out


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    hip = _v(P['hip'])
    sq = squash_points(P)
    hr = float(P['head_r'])
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk),
        BoneSpec('body', tuple(hip), tuple(hip + Vector((0, 0, 0.1 * sk))), 'root', radius=0.4 * sk),
        BoneSpec('hips', tuple(sq[0]), tuple(sq[1]), 'body', radius=0.35 * sk),
        BoneSpec('chest', tuple(sq[1]), tuple(sq[2]), 'hips', connect=True, radius=0.35 * sk),
        BoneSpec('head', tuple(sq[2]), tuple(sq[3]), 'chest', connect=True, radius=max(0.3 * sk, 1.2 * hr)),
    ]
    jh, jt = jaw_points(P)
    specs.append(BoneSpec('jaw', tuple(jh), tuple(jt), 'head', radius=0.5 * hr))
    sac = sac_of(P)
    if sac:
        specs.append(BoneSpec('sac', tuple(sac['head']), tuple(sac['tail']), sac['parent'], radius=0.12 * sk))
    tg = tongue_of(P)
    if tg:
        for i, nm in enumerate(tg['bones']):
            # unconnected, so each can slide out along the tongue (the skin between stretches)
            specs.append(BoneSpec(nm, tuple(tg['points'][i]), tuple(tg['points'][i + 1]), tg['parent'] if i == 0 else tg['bones'][i - 1],
                                  radius=0.04 * sk))
    for lg in legs(P):
        specs.append(BoneSpec(lg['upper'], tuple(lg['hip']), tuple(lg['knee']), lg['parent'], radius=0.08 * sk))
        specs.append(BoneSpec(lg['lower'], tuple(lg['knee']), tuple(lg['ankle']), lg['upper'], connect=True, radius=0.07 * sk))
        if lg['foot']:
            specs.append(BoneSpec(lg['foot'], tuple(lg['ankle']), tuple(lg['toe']), lg['lower'], connect=True, radius=0.06 * sk))
    for m in tentacles(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.06 * sk))
    # props after the tentacles (a scroll in a tentacle's grip), chains last (a tassel on a cap prop)
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'head'), radius=0.08 * sk))
    for m in chains(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.05 * sk))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """The game's seven, socket_core at the body's centre, socket_sac, socket_tongue (the tongue's tip, where a lash
    lands), socket_<tentacle> at each tip, socket_<chain>, socket_<prop>."""
    sk = size_of(P)
    hc, hr = _v(P['head_c']), float(P['head_r'])
    hip, top = _v(P['hip']), _v(P['chest'])
    _jh, jt = jaw_points(P)
    out = {
        'socket_head': ('head', tuple(top)),
        'socket_crown': ('head', tuple(top + Vector((0, 0, 0.1 * sk)))),
        'socket_back': ('chest', (hip.x, hip.y + 0.6 * (top.z - hip.z), top.z - 0.25 * (top.z - hip.z))),
        'socket_mouth': ('jaw', tuple(jt + Vector((0, -0.02 * sk, 0)))),
        'socket_core': ('body', tuple(hip)),
    }
    sac = sac_of(P)
    if sac:
        out['socket_sac'] = ('sac', tuple(sac['tail']))
    tg = tongue_of(P)
    if tg:
        out['socket_tongue'] = (tg['bones'][-1], tuple(tg['points'][-1]))
    front = {lg['tag']: lg for lg in legs(P) if lg['front']}
    T = tentacles(P)
    for tag, s in SIDES:
        if tag in front:
            lg = front[tag]
            out[f'socket_paw_{tag}'] = (lg['foot'] or lg['lower'], tuple(lg['toe'] if lg['toe'] is not None else lg['ankle']))
        else:
            side = [m for m in T if m['side'] == s] or T
            if side:
                m = min(side, key=lambda m: m['points'][-1].y)       # the foremost tip on that side
                out[f'socket_paw_{tag}'] = (m['bones'][-1], tuple(m['points'][-1]))
            else:
                out[f'socket_paw_{tag}'] = ('body', (s * 0.8 * hr, hip.y - 0.8 * hr, hip.z))
    tail = next((m for m in chains(P) if m['kind'] == 'tail'), None)
    out['socket_tail'] = (tail['bones'][-1], tuple(tail['points'][-1])) if tail else ('hips', (hip.x, hip.y + 0.9 * (top.z - hip.z), base_of(P).z + 0.1 * sk))
    for m in T:
        out[f"socket_{m['name']}"] = (m['bones'][-1], tuple(m['points'][-1]))
    for m in chains(P):
        out[f"socket_{m['name']}"] = (m['bones'][-1], tuple(m['points'][-1]))
    for pr in P.get('props', []) or []:
        out[f"socket_{pr['name']}"] = (f"prop.{pr['name']}", tuple(pr['tail']))
    return out


# --------------------------------------------------------------------------- clips
Z = Vector((0.0, 0.0, 1.0))


def make_clips(cb: A.ClipBuilder, P: dict, only: list[str] | None = None) -> list[A.ClipMeta]:
    rig = K.Rig(cb.arm)
    has = rig.has
    sk = size_of(P)
    made: list[A.ClipMeta] = []
    style, cstyle, kstyle = strike_style(P), cast_style(P), ko_style(P)
    LEGS = [lg for lg in legs(P) if has(lg['upper']) and has(lg['lower'])]
    T = [m for m in tentacles(P) if has(m['bones'][0])]
    TN = {m['name']: m for m in T}
    CH = chains(P)
    SAC = sac_of(P) if has('sac') else None
    TG = tongue_of(P) if has('tongue.1') else None
    if style == 'tongue' and not TG:
        raise ValueError("strike_style 'tongue' needs a tongue")
    if style in ('slap', 'ink') and not T:
        raise ValueError(f'strike_style {style!r} needs tentacles')
    SLAP = pick_arm(P, 'slap_arm') if T else None
    INK = pick_arm(P, 'ink_arm') if T else None
    JAW = bool(P.get('jaw_open', False))
    CLOSED = P.get('blink_closed')
    hip = _v(P['hip'])
    HZ = hip.z
    TOP = _v(P['chest'])
    ko_pitch = float(P.get('ko_pitch', 95.0))
    ko_roll = float(P.get('ko_roll', KO_ROLL))
    lift_tab = P.get('ko_lift') or []
    strike_yaw = float(P.get('strike_yaw', 0.0))   # degrees toward its left at the drive (the 70-degree strike shot)
    LIFT_EXACT = bool(P.get('ground_lift_exact', False))     # Nov 15 (Scrollopus), opt-in: ground_lift's exact turn
    hop_k = float(P.get('hop', 1.0))
    HOP_STRETCH = float(P.get('hop_stretch', 1.0))
    # Nov 15 (Bloatoad), opt-in: hit_squash > 0 squashes the light hit wide and low (about z) instead of the knock
    # front to back (whose kept volume stretched a squat body 7% taller); sidestep_stretch [1] scales the sidestep's
    # mid-hop stretch, its head-back bend and roll; hit_heavy_pitch / _lift / _stretch [1] scale the heavy hit's
    # backward pitch, its rise and its stretch (a squat body's belly pushed through the arms' roots)
    HIT_SQUASH = float(P.get('hit_squash', 0.0))
    SIDESTEP_K = float(P.get('sidestep_stretch', 1.0))
    HH_PITCH = float(P.get('hit_heavy_pitch', 1.0))
    HH_LIFT = float(P.get('hit_heavy_lift', 1.0))
    HH_STRETCH = float(P.get('hit_heavy_stretch', 1.0))

    def mm(v: float) -> float:
        return v * sk

    # ---- rest geometry
    for lg in LEGS:
        lg['reach'] = rig.length(lg['upper']) + rig.length(lg['lower'])
        lg['rest_ankle'] = rig.tail[lg['lower']].copy()
        lg['rest_hip'] = rig.head[lg['upper']].copy()
        fallback = Vector((lg['s'] * 0.7, 0.3 if lg['front'] else -0.3, 0.6)).normalized()
        lg['hint'] = rig.bend_hint(lg['upper'], lg['lower'], fallback)
        lg['phase'] = 0.5 * ((lg['i'] - 1 + (0 if lg['tag'] == 'L' else 1)) % 2)
    LEG = (sum(lg['reach'] for lg in LEGS) / len(LEGS)) if LEGS else mm(0.2)
    for m in T:
        m['rest_low'] = min(p.z for p in m['points'])
        # each tentacle's own phase round the body (the shuffle's wave, the idle's curl)
        m['phase'] = (math.atan2(m['out'].x, -m['out'].y) / (2 * math.pi)) % 1.0

    def mass_points() -> np.ndarray | None:
        """lo_body's vertices that move with the body itself (the squash chain, the jaw, the sac), relative to the
        centre: body() keeps them off the ground."""
        ob = bpy.data.objects.get('lo_body')
        if ob is None or ob.type != 'MESH':
            return None
        # the body, and the roots of the chains on it (a tail's root sinks with a lean back like the body does)
        keep = {'body', 'hips', 'chest', 'head', 'jaw', 'sac'} | {m['bones'][0] for m in CH if m['parent'] in ('body', 'hips', 'chest', 'head')}
        names = {g.index: g.name for g in ob.vertex_groups}
        pts = [v.co[:] for v in ob.data.vertices if v.groups and names.get(max(v.groups, key=lambda g: g.weight).group) in keep]
        if len(pts) < 20:
            return None
        a = np.array(pts) - np.array(hip[:])
        return a[:: max(1, len(a) // 3000)]

    MASS = mass_points()
    FLOOR = min(mm(0.003), HZ + float(MASS[:, 2].min())) if MASS is not None else -1.0
    C.log(f'blob: {0 if MASS is None else len(MASS)} body points (lowest {HZ + float(MASS[:, 2].min()) if MASS is not None else 0.0:.3f} m), '
          f'{len(LEGS)} legs, {len(T)} tentacles, sac {bool(SAC)}, tongue {bool(TG)}')

    def reach_drop(shift: Vector, margin: float = 0.97) -> float:
        need = 0.0
        for lg in LEGS:
            d = lg['rest_hip'] - (lg['rest_ankle'] + shift)
            r2 = (margin * lg['reach']) ** 2 - d.x * d.x - d.y * d.y
            need = max(need, d.z - math.sqrt(max(0.0, r2)))
        return min(max(0.0, need), 0.5 * HZ)

    stride_k = float(P.get('stride', 1.0))

    def stride_of(kind: str) -> float:
        return GAITS[kind][1] * LEG * stride_k

    def speed_of(kind: str) -> float:
        if not LEGS:
            return mm(SHUFFLE[kind])
        n, _s, duty, _l = GAITS[kind]
        return stride_of(kind) / (duty * n / A.FPS)

    DROP = {k: max(reach_drop(Vector((stride_of(k) / 2, 0, 0))), reach_drop(Vector((0, stride_of(k) / 2, 0))),
                   reach_drop(Vector((0, -stride_of(k) / 2, 0)))) if LEGS else 0.0 for k in GAITS}

    # ---- keying
    def clip(name: str, n: int, pose, loop: bool = True, hold: bool = False, root_speed: float = 0.0, step: int = 1,
             markers=(), faces=(), shut=None) -> None:
        if only and name not in only:
            return
        cb.begin(name, n, loop=loop, hold=hold, root_speed=root_speed)
        for f in K.frames_of(n, step):
            t = (f - 1) / n
            fr = pose(t)
            if TG and TG['parent'] == 'jaw' and 'jaw' in fr.rot and getattr(fr, 'tongue_out', 0.0) > 0:
                # a tongue on the jaw lashes level: its root takes back the jaw's opening as it slides out
                fr.r(TG['bones'][0], -fr.rot['jaw'][0] * min(1.0, 3.0 * fr.tongue_out), 0, 0)
            K.clip_bump(P, name, t, fr, sk)
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
             yaw: float = 0.0, guard: bool = True) -> None:
        """The whole monster moved and turned about its centre (+pitch tips it forward), its mass never under the
        ground (a lean lifts it by just enough)."""
        if guard and MASS is not None:
            low = HZ + dz + float((MASS @ np.array(K.m3((pitch, roll, yaw)))[2]).min())
            if low < FLOOR:
                dz += FLOOR - low
        fr.o('body', dx, dy, dz)
        fr.r('body', pitch, roll, yaw)
        fr.bpose = (dz, pitch, roll, yaw)

    def posed_z(fr: Frame, p: Vector) -> float:
        dz, pitch, roll, yaw = getattr(fr, 'bpose', (0.0, 0.0, 0.0, 0.0))
        return HZ + dz + (K.m3((pitch, roll, yaw)) @ (p - hip)).z

    def squash(fr: Frame, k: float, wide: float | None = None, axis: str = 'z') -> None:
        """Squash (k < 1) or stretch (k > 1) the body about its bottom, keeping its volume (or `wide` across); axis 'y'
        squashes it front to back (a knock, a shove)."""
        w = (1.0 / math.sqrt(max(0.2, k))) if wide is None else wide
        if axis == 'z':
            fr.s('hips', w, w, k)
        else:
            fr.s('hips', w, k, w)

    def bend(fr: Frame, pitch: float = 0.0, tilt: float = 0.0, yaw: float = 0.0) -> None:
        """The upper body bends: a nod (+ forward), a tilt (+ toward its left), a turn (+ toward its left)."""
        fr.r('chest', 0.4 * pitch, 0.4 * tilt, 0.4 * yaw)
        fr.r('head', 0.6 * pitch, 0.6 * tilt, 0.6 * yaw)

    def inflate(fr: Frame, k: float) -> None:
        """The throat sac blown up by k (0 rest … 1 its full `max`)."""
        if SAC:
            fr.s('sac', 1.0 + (SAC['max'] - 1.0) * max(0.0, k))

    def tongue(fr: Frame, out: float = 0.0, droop: float = 0.0, curl: float = 0.0, wag: float = 0.0) -> None:
        """The tongue slid `out` (0..1) of its reach (each bone beyond the first slides along it, the skin between
        stretching), its root pitched `droop` degrees down, its tip curled up `curl`, wagged `wag`."""
        if not TG:
            return
        n = len(TG['bones'])
        fr.tongue_out = max(0.0, out)
        step = TG['reach'] * max(0.0, out) / max(1, n - 1)
        for i, b in enumerate(TG['bones']):
            fr.o(b, *(TG['dir'] * (step if i > 0 else 0.0)))
            if i == 0:
                fr.r(b, droop, 0, wag)
            elif i == n - 1:
                fr.r(b, -curl, 0, 0.5 * wag)
            else:
                fr.r(b, -0.4 * curl, 0, 0.5 * wag)

    def jaw(fr: Frame, deg_: float) -> None:
        if JAW:
            fr.r('jaw', deg_, 0, 0)

    def ko_lift(t: float) -> float:
        return K.table_at(lift_tab, t)

    # ---- legs (as the shelled plan's: IK-planted in the root's space)
    def plant(fr: Frame, lg: dict, d: Vector | None = None, pitch: float = 0.0) -> None:
        a = lg['rest_ankle'] + (d if d is not None else Vector())
        fr.ik[(lg['upper'], lg['lower'], lg['foot'])] = {'root_target': a, 'rest_hint': lg['hint'], 'hint_bone': lg['parent'],
                                                       'pitch': pitch if lg['foot'] else None}

    def feet(fr: Frame, out: float = 0.0, lift: float = 0.0, shift: Vector | None = None, tuck_: float = 0.0) -> None:
        """Every foot planted (wider by `out`, lifted, moved by `shift`, drawn in toward its hip by `tuck_`)."""
        for lg in LEGS:
            d = Vector((lg['s'] * out, 0.0, lift)) + (shift if shift is not None else Vector())
            if tuck_:
                h, ra = lg['rest_hip'], lg['rest_ankle']
                d += Vector((0.5 * (h.x - ra.x), 0.4 * (h.y - ra.y), 0.4 * (h.z - ra.z))) * tuck_
            plant(fr, lg, d)

    def fold_legs(fr: Frame, k: float, splay: float = 40.0, curl: float = 40.0, wave: float = 0.0, t: float = 0.0) -> None:
        """Legs by angle, off the ground (ko): swung out `splay` and bent `curl`, kicking `wave`."""
        for lg in LEGS:
            s = lg['s']
            w = wave * A.wave(t, 3.0, 0.25 * lg['i'] + (0.5 if lg['tag'] == 'R' else 0.0))
            fr.r(lg['upper'], 0, -s * (splay * k + w), 0)
            fr.r(lg['lower'], 0, s * (curl * k + 0.5 * w), 0)

    # ---- tentacles
    def tent(fr: Frame, m: dict, t: float = 0.0, lift: float = 0.0, curl: float = 0.0, sway: float = 0.0, rate: float = 1.0,
             turn: float = 0.0, phase: float = 0.0) -> None:
        """One tentacle: `lift` raises it from its root (degrees, about its own horizontal), `curl` rolls it up from
        the root to the tip (shared along it, more at the tip; negative uncurls), `sway` swings it side to side with a
        lag down the chain, `turn` swings it toward its left (+)."""
        n = len(m['bones'])
        for i, b in enumerate(m['bones']):
            d = m['dirs'][i]
            dh = Vector((d.x, d.y, 0.0))
            lax = dh.cross(Z) if dh.length > 1e-3 else Vector((1.0, 0.0, 0.0))
            share = (0.6 + 0.8 * i / max(1, n - 1)) / n
            fr.r(b, 0, 0, 0)
            if i == 0:
                fr.turn(b, lax, lift)
                fr.turn(b, Z, turn)
            fr.turn(b, lax, curl * share)
            fr.turn(b, Z, sway * share * A.wave(t - 0.08 * i, rate, phase))

    def tents(fr: Frame, t: float, roles=TENTACLE_ROLES, lift: float = 0.0, curl: float = 0.0, sway: float = 0.0,
              rate: float = 1.0, wave_curl: float = 0.0, spread: float = 0.0, guard: bool = True, skip=()) -> None:
        """Every tentacle of these roles posed alike (each with its own phase for `sway` and `wave_curl`; `spread`
        swings them away from the front-back line); ground ones then lift just enough to clear the ground."""
        for m in T:
            if m['role'] not in roles or m['name'] in skip:
                continue
            sp = spread * (1 if m['out'].x >= 0 else -1) * min(1.0, abs(m['out'].x) * 2)
            c = curl + wave_curl * (0.5 + 0.5 * A.wave(t, rate, m['phase']))
            if m['role'] == 'ground':
                c = max(0.0, c)          # a tentacle lying on the ground only ever curls up off it
            tent(fr, m, t, lift=lift, curl=c, sway=sway, rate=rate, turn=sp, phase=m['phase'])
            if guard and m['role'] == 'ground':
                ground_lift(fr, m)

    def ground_lift(fr: Frame, m: dict) -> None:
        """A ground tentacle that the body's lean or drop would push under the ground rises from its root by just
        enough: each of its points lying on the ground at rest is kept at its rest height (+4 mm)."""
        r0 = m['points'][0]
        best = 0.0
        for p in m['points'][1:]:
            if p.z > m['rest_low'] + mm(0.04):
                continue
            need = p.z - posed_z(fr, p) + mm(0.004)
            d = (p - r0).length
            if need > 0 and d > 1e-4:
                if LIFT_EXACT:
                    # (Nov 15, Scrollopus; opt-in) the turn that really raises the point by `need`: a root high above
                    # its ground run (a steep descent) needs much more than asin(need / d)
                    q = p - r0
                    d0 = m['dirs'][0]
                    dh = Vector((d0.x, d0.y, 0.0))
                    dh = dh.normalized() if dh.length > 1e-3 else Vector((q.x, q.y, 0.0)).normalized()
                    A_, B_ = max(1e-4, q.x * dh.x + q.y * dh.y), max(0.0, -q.z)
                    R_ = math.hypot(A_, B_)
                    best = max(best, math.atan2(B_, A_) + math.asin(max(-1.0, min(1.0, (need - B_) / R_))))
                else:
                    best = max(best, math.asin(min(1.0, need / d)))
        if best > 0:
            d = m['dirs'][0]
            dh = Vector((d.x, d.y, 0.0))
            lax = dh.cross(Z) if dh.length > 1e-3 else Vector((1.0, 0.0, 0.0))
            fr.turn(m['bones'][0], lax, math.degrees(best))

    def chain_pose(fr: Frame, t: float, sway: float = 0.0, rate: float = 1.0, trail: float = 0.0, wag: float = 0.0,
                   lift: float = 0.0) -> None:
        """Other chains by kind: a tassel sways and trails (+x swings it back), a frill and feelers spring, a tail
        wags and lifts."""
        for m in CH:
            n = len(m['bones'])
            k = 1.0 - m['stiff']
            for i, b in enumerate(m['bones']):
                lag = 0.08 * i
                share = (0.6 + 0.8 * i / max(1, n - 1)) / n
                if m['kind'] == 'tassel':
                    fr.r(b, trail * share * k, 0, sway * share * k * A.wave(t - lag, rate))
                elif m['kind'] in ('frill', 'antenna'):
                    fr.r(b, 0.5 * sway * share * k * A.wave(t - lag, rate, 0.25), 0, sway * share * k * A.wave(t - lag, rate))
                else:
                    up = 0.0
                    if i == 0 and m['parent'] in ('body', 'hips', 'chest'):
                        # a tail lifts at its root just enough to keep its bone line 5 cm up as the body leans or sinks
                        need = mm(0.05) - min(posed_z(fr, p) for p in m['points'])
                        ln = sum((m['points'][j + 1] - m['points'][j]).length for j in range(len(m['points']) - 1))
                        if need > 0 and ln > 1e-4:
                            up = math.degrees(math.asin(min(1.0, need / ln)))
                    fr.r(b, lift * share * k + up, 0, 1.6 * wag * share * k * A.wave(t - lag, rate))

    def gestures(fr: Frame, t: float, lift: float = 0.0, sway: float = 4.0, rate: float = 1.0, curl: float = 0.0,
                 skip=()) -> None:
        """The holding tentacles (a scroll, a quill, a book) and the free ones: raised `lift`, gesturing a little."""
        tents(fr, t, roles=('hold', 'free'), lift=lift, sway=sway, rate=rate, curl=curl, skip=skip)

    def rest_pose(fr: Frame, t: float, rate: float = 1.0, curl_wave: float = 6.0, sway: float = 4.0) -> None:
        """The ground tentacles breathing (curling and uncurling a little, each in its own time) and the others
        gesturing: called by every calm pose after body()."""
        tents(fr, t, roles=('ground',), wave_curl=curl_wave, sway=0.5 * sway, rate=rate)
        gestures(fr, t, sway=sway, rate=rate)

    # ================================================================= ranch life
    def p_idle(t: float) -> Frame:
        fr = Frame()
        glance = A.pulse(t, 0.55, 0.85)
        body(fr, yaw=6 * glance)
        squash(fr, 1.0 + 0.02 * A.wave(t, 2.0))
        bend(fr, pitch=2 * A.wave(t, 1.0), yaw=14 * glance, tilt=4 * glance)
        inflate(fr, 0.12 * (0.5 + 0.5 * A.wave(t, 4.0)))
        tongue(fr)
        jaw(fr, 0)
        feet(fr)
        rest_pose(fr, t)
        chain_pose(fr, t, sway=6, wag=6)
        return fr

    def p_idle_happy(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 3)
        balloon = A.step_ease(t, 0.1, 0.3) * (1 - A.step_ease(t, 0.7, 0.92))     # the sac balloons and goes down
        body(fr, dz=mm(0.012) * b, roll=4 * A.wave(t, 2.0))
        squash(fr, 1.0 + 0.06 * A.wave(t, 3.0, 0.25))
        bend(fr, pitch=-8, tilt=8 * A.wave(t, 2.0))
        inflate(fr, balloon)
        tongue(fr)
        jaw(fr, 10 * (1 - balloon))
        feet(fr, lift=0.6 * mm(0.012) * b)
        tents(fr, t, roles=('ground',), wave_curl=14, sway=8, rate=3.0)
        gestures(fr, t, lift=12, sway=14, rate=3.0)
        chain_pose(fr, t, sway=14, rate=3.0, wag=18)
        return fr

    def p_idle_tired(t: float) -> Frame:
        fr = Frame()
        yawn = A.pulse(t, 0.45, 0.72)
        body(fr, pitch=6 - 10 * yawn)
        squash(fr, 0.93 + 0.06 * yawn)
        bend(fr, pitch=14 - 26 * yawn)
        inflate(fr, 0.05)
        tongue(fr, out=0.06 * yawn, droop=10 * yawn)
        jaw(fr, 30 * yawn)
        feet(fr, out=mm(0.01))
        tents(fr, t, roles=('ground',), wave_curl=3, sway=2)
        gestures(fr, t, lift=-10 + 8 * yawn, sway=2)
        chain_pose(fr, t, sway=3, wag=3, lift=-8)
        return fr

    def p_idle_sad(t: float) -> Frame:
        fr = Frame()
        body(fr, pitch=8, yaw=-6)
        squash(fr, 0.92)
        bend(fr, pitch=18, yaw=-8 + 4 * A.pulse(t, 0.5, 0.7))
        inflate(fr, 0.0)
        tongue(fr)
        jaw(fr, 0)
        feet(fr)
        tents(fr, t, roles=('ground',), wave_curl=2, sway=2)
        gestures(fr, t, lift=-14, sway=2, curl=8)
        chain_pose(fr, t, sway=2, wag=2, lift=-10)
        return fr

    def p_idle_sick(t: float) -> Frame:
        fr = Frame()
        w = A.wave(t, 1.0)
        shiver = A.wave(t, 9.0) * A.pulse(t, 0.25, 0.5)
        body(fr, roll=5 * w + 1.5 * shiver, pitch=4)
        squash(fr, 0.95 + 0.03 * A.wave(t, 7.0) * A.pulse(t, 0.25, 0.5))
        bend(fr, pitch=12, yaw=8 * w, tilt=6 * w)
        inflate(fr, 0.1 * A.pulse(t, 0.6, 0.8))
        tongue(fr)
        jaw(fr, 6)
        feet(fr, out=mm(0.008))
        tents(fr, t, roles=('ground',), wave_curl=4, sway=6)
        gestures(fr, t, lift=-8, sway=6)
        chain_pose(fr, t, sway=5, wag=3, lift=-6)
        return fr

    def p_sleep(t: float) -> Frame:
        fr = Frame()
        b = A.wave(t, 1.0)
        body(fr, pitch=4)
        squash(fr, 0.88 + 0.02 * b, wide=1.08)
        bend(fr, pitch=12, tilt=6)
        inflate(fr, 0.55 * (0.5 + 0.5 * b))          # a slow snoring bubble
        tongue(fr)
        jaw(fr, 0)
        feet(fr, out=mm(0.015))
        tents(fr, t, roles=('ground',), wave_curl=2, sway=1)
        gestures(fr, t, lift=-16, sway=1, curl=12)
        chain_pose(fr, t, sway=1, wag=0, lift=-10)
        return fr

    def p_eat(t: float) -> Frame:
        fr = Frame()
        dip = A.step_ease(t, 0.0, 0.2) * (1 - A.step_ease(t, 0.85, 1.0))
        chew = dip * abs(math.sin(t * 2 * math.pi * 3))
        flick = A.pulse(t, 0.2, 0.42) + A.pulse(t, 0.5, 0.72)     # the tongue flicks down to the ground twice
        body(fr, pitch=8 * dip)
        squash(fr, 1.0 - 0.04 * chew)
        bend(fr, pitch=14 * dip)
        inflate(fr, 0.15 * chew)
        tongue(fr, out=0.35 * flick, droop=45 * flick)
        jaw(fr, 18 * chew + 14 * flick)
        feet(fr)
        tents(fr, t, roles=('ground',), wave_curl=4, sway=3)
        # a holding tentacle brings the food to the mouth
        gestures(fr, t, lift=-10 * dip, sway=3, curl=30 * chew)
        chain_pose(fr, t, sway=4, wag=8)
        return fr

    def p_pet(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, roll=6, pitch=-3)
        squash(fr, 1.0 - 0.05 * b, wide=1.0 + 0.04 * b)
        bend(fr, pitch=-10, tilt=12 + 3 * A.wave(t, 2.0), yaw=5)
        inflate(fr, 0.4 + 0.2 * b)
        tongue(fr)
        jaw(fr, 8)
        feet(fr)
        tents(fr, t, roles=('ground',), wave_curl=12, sway=6, rate=2.0)
        gestures(fr, t, lift=6, sway=10, rate=2.0)
        chain_pose(fr, t, sway=10, rate=2.0, wag=20)
        return fr

    def p_look(t: float) -> Frame:
        fr = Frame()
        a = A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56))
        b = A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        yaw = 36 * a - 36 * b
        body(fr, yaw=0.35 * yaw)
        squash(fr, 1.0)
        bend(fr, yaw=0.65 * yaw, tilt=0.1 * yaw)
        inflate(fr, 0.08)
        tongue(fr)
        jaw(fr, 0)
        feet(fr)
        rest_pose(fr, t)
        chain_pose(fr, t, sway=6, wag=6)
        return fr

    def hop_pose(fr: Frame, t: float, air: float, crouch: float, up: float, roll: float = 0.0, yaw: float = 0.0,
                 stretch_k: float = 1.0) -> None:
        """A squash-and-stretch hop: crouched (squashed wide), then up (stretched tall), the feet and the tentacles
        leaving the ground with the body. stretch_k scales the airborne stretch, lean-back and tuck (the sidestep's)."""
        body(fr, dz=up, pitch=-4 * air * stretch_k + 3 * crouch, roll=roll, yaw=yaw)
        # Nov 15 (Bloatoad), opt-in: hop_stretch [1] scales the stretch in the air (a squat body read as a bowling pin)
        squash(fr, 1.0 - 0.16 * crouch + 0.14 * HOP_STRETCH * air * stretch_k)
        bend(fr, pitch=-8 * air * stretch_k + 6 * crouch)
        feet(fr, lift=0.85 * up, tuck_=0.3 * air * stretch_k)
        tents(fr, t, roles=('ground',), curl=10 * crouch + 20 * air, sway=4)
        gestures(fr, t, lift=20 * air - 6 * crouch, sway=6)
        chain_pose(fr, t, sway=6, trail=-12 * air, wag=10, lift=10 * air)

    def p_hop(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.28, 0.82)
        crouch = A.pulse(t, 0.0, 0.28) + 0.8 * A.pulse(t, 0.8, 1.0)
        hop_pose(fr, t, air, crouch, mm(0.13) * hop_k * air)
        inflate(fr, 0.2 * air)
        tongue(fr)
        jaw(fr, 10 * air)
        return fr

    def p_celebrate(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        land = A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)
        hop_pose(fr, t, air, land, mm(0.11) * hop_k * air, yaw=14 * A.wave(t, 1.0))
        inflate(fr, 0.7 * A.step_ease(t, 0.05, 0.2) * (1 - A.step_ease(t, 0.8, 0.95)))
        tongue(fr)
        jaw(fr, 16)
        return fr

    # ================================================================= moving
    def gait(t: float, kind: str, dirv: Vector, lean: float = 0.0, guard_w: float = 0.0, rate: float = 1.0,
             roll: float = 0.0) -> Frame:
        """Legs crawl in diagonal pairs (walk, the steps, strafe) or hop all together (run, dash), planted by IK;
        without legs it shuffles on its ground tentacles, each lifting and reaching in its turn round the body."""
        fr = Frame()
        n, _s, duty, lift_k = GAITS[kind]
        hop = kind in ('run', 'dash')
        if LEGS and hop:
            stride = stride_of(kind)
            p = t % 1.0
            if p < duty:
                u = p / duty
                d = dirv * (stride * (0.5 - u))
                lift_f, dz, sq = 0.0, -DROP[kind] - mm(0.03) * math.sin(math.pi * u), 1.0 - 0.12 * math.sin(math.pi * u)
            else:
                u = (p - duty) / (1 - duty)
                d = dirv * (stride * (-0.5 + C.ease_in_out(u)))
                lift_f = lift_k * LEG * math.sin(math.pi * u)
                dz, sq = mm(0.07) * hop_k * math.sin(math.pi * u) - DROP[kind], 1.0 + 0.1 * math.sin(math.pi * u)
            body(fr, dz=dz, pitch=lean, roll=roll)
            squash(fr, sq)
            for lg in LEGS:
                plant(fr, lg, d + Vector((0, 0, lift_f)))
            tents(fr, t, roles=('ground',), curl=10, sway=6, rate=2.0 * rate)
        elif LEGS:
            stride = stride_of(kind)
            body(fr, dz=-DROP[kind] - mm(0.006) * (0.5 - 0.5 * math.cos(4 * math.pi * t)), pitch=lean,
                 roll=roll + 3.0 * math.sin(2 * math.pi * t), yaw=2.0 * math.sin(2 * math.pi * t))
            squash(fr, 1.0 + 0.03 * math.cos(4 * math.pi * t))
            for lg in LEGS:
                p = (t + lg['phase']) % 1.0
                if p < duty:
                    plant(fr, lg, dirv * (stride * (0.5 - p / duty)))
                else:
                    u = (p - duty) / (1 - duty)
                    plant(fr, lg, dirv * (stride * (-0.5 + C.ease_in_out(u))) + Vector((0, 0, lift_k * lg['reach'] * math.sin(math.pi * u))),
                          pitch=-10 * math.sin(math.pi * u))
            tents(fr, t, roles=('ground',), wave_curl=6, sway=4, rate=2.0 * rate)
        else:
            body(fr, dz=mm(0.006) * (0.5 - 0.5 * math.cos(4 * math.pi * t)), pitch=lean, roll=roll + 4.0 * math.sin(2 * math.pi * t))
            squash(fr, 1.0 + 0.04 * math.cos(4 * math.pi * t))
            for m in T:
                if m['role'] != 'ground':
                    continue
                # each ground tentacle in its turn lifts, reaches toward the travel and plants
                step_ = max(0.0, math.sin(2 * math.pi * (2 * t + m['phase'])))
                ahead = m['out'].cross(Z).dot(dirv)       # which way about the vertical turns it toward the travel
                tent(fr, m, t, lift=16 * step_, curl=10 + 10 * step_, turn=-12 * step_ * (1 if ahead >= 0 else -1),
                     sway=0.0)
                ground_lift(fr, m)
        bend(fr, pitch=-0.4 * lean + 2 * math.sin(4 * math.pi * t), yaw=-2 * math.sin(2 * math.pi * t))
        inflate(fr, 0.1)
        tongue(fr)
        jaw(fr, 0)
        gestures(fr, t, lift=10 * guard_w + 4, sway=6, rate=2.0 * rate)
        chain_pose(fr, t, sway=6, rate=2.0 * rate, trail=(14 + 20 * (1 if hop else 0)) * (1 if dirv.y < 0 else -0.5), wag=10)
        return fr

    def gait_marks(kind: str) -> list:
        n = GAITS[kind][0]
        return [('step', 1), ('step', 1 + n // 2)]

    def p_strafe(t: float, side: int) -> Frame:
        return gait(t, 'strafe', Vector((side, 0, 0)), guard_w=1.0, roll=side * 4)

    def p_sidestep(t: float, side: int) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.15, 0.92)
        crouch = A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        hop_pose(fr, t, air, crouch, mm(0.07) * air, roll=side * 14 * air * SIDESTEP_K, stretch_k=SIDESTEP_K)
        inflate(fr, 0.1)
        tongue(fr)
        jaw(fr, 0)
        return fr

    # ================================================================= scenes
    def settle_pose(fr: Frame, t: float, k: float) -> None:
        """Settled low and wide (k: 0 up → 1 down), the legs splaying, the tentacles curling in."""
        body(fr, pitch=2 * k)
        squash(fr, 1.0 - 0.1 * k + 0.008 * A.wave(t, 2.0) * k)
        feet(fr, out=mm(0.025) * k)
        tents(fr, t, roles=('ground',), curl=8 * k, wave_curl=3, sway=2)
        gestures(fr, t, lift=-8 * k, sway=3, curl=6 * k)
        chain_pose(fr, t, sway=3, wag=4, lift=-8 * k)
        inflate(fr, 0.08)
        tongue(fr)
        jaw(fr, 0)

    def p_sit_down(t: float) -> Frame:
        fr = Frame()
        settle_pose(fr, t, C.ease_in_out(t))
        bend(fr, pitch=-4 * C.ease_in_out(t))
        return fr

    def p_sit(t: float) -> Frame:
        fr = Frame()
        settle_pose(fr, t, 1.0)
        g = A.pulse(t, 0.5, 0.75)
        bend(fr, pitch=-4 + 2 * A.wave(t, 1.0), yaw=14 * g)
        return fr

    def p_dizzy(t: float) -> Frame:
        fr = Frame()
        c, s_ = math.cos(t * 4 * math.pi), math.sin(t * 4 * math.pi)
        body(fr, roll=7 * s_, pitch=5 * c, yaw=6 * s_)
        squash(fr, 1.0 + 0.04 * s_)
        bend(fr, pitch=10 * c, tilt=14 * s_, yaw=12 * s_)
        inflate(fr, 0.1)
        tongue(fr, out=0.08, droop=20)
        jaw(fr, 12)
        feet(fr, out=mm(0.015))
        tents(fr, t, roles=('ground',), wave_curl=8, sway=12, rate=2.0)
        gestures(fr, t, sway=14, rate=2.0)
        chain_pose(fr, t, sway=14, rate=2.0, wag=14)
        return fr

    # ================================================================= battle
    def p_battle_idle(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, pitch=5, yaw=-4)
        squash(fr, 0.97 + 0.03 * A.wave(t, 2.0))
        bend(fr, pitch=-3)
        inflate(fr, 0.15 + 0.1 * b)
        tongue(fr)
        jaw(fr, 0)
        feet(fr, out=mm(0.01))
        tents(fr, t, roles=('ground',), curl=6, wave_curl=6, sway=4, rate=2.0)
        gestures(fr, t, lift=18, sway=6, rate=2.0)
        chain_pose(fr, t, sway=6, rate=2.0, wag=10)
        return fr

    def p_hit(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.8)
        dy = mm(0.05) * k
        body(fr, dy=dy, pitch=-10 * k, yaw=-8 * k)
        if HIT_SQUASH > 0.0:
            # squashed wide and low on the impact, a small rebound after
            squash(fr, 1.0 - HIT_SQUASH * A.pulse(t, 0.0, 0.6) + 0.3 * HIT_SQUASH * A.pulse(t, 0.6, 0.85))
        else:
            squash(fr, 1.0 - 0.14 * A.pulse(t, 0.0, 0.35) + 0.05 * A.pulse(t, 0.35, 0.7), axis='y')
        bend(fr, pitch=-8 * k, yaw=-6 * k)
        inflate(fr, 0.25 * A.pulse(t, 0.0, 0.5))
        tongue(fr)
        jaw(fr, 12 * k)
        feet(fr, shift=Vector((0, 0.4 * dy, 0)))
        tents(fr, t, roles=('ground',), curl=18 * k, sway=10)
        gestures(fr, t, lift=20 * k, sway=10, curl=-14 * k)
        chain_pose(fr, t, sway=10, trail=-20 * k, wag=8)
        K.add_bones(P, 'hit_bones', fr, k)
        return fr

    def p_hit_heavy(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.62)
        dy, up = mm(0.14) * k, mm(0.06) * k * HH_LIFT
        body(fr, dy=dy, dz=up, pitch=-32 * k * HH_PITCH, roll=-10 * k)
        squash(fr, 1.0 - 0.15 * A.pulse(t, 0.0, 0.25) + 0.08 * HH_STRETCH * A.pulse(t, 0.25, 0.55))
        bend(fr, pitch=-10 * k, yaw=-12 * k)
        inflate(fr, 0.3 * A.pulse(t, 0.0, 0.4))
        tongue(fr, out=0.12 * k, droop=10 * k)
        jaw(fr, 18 * k)
        feet(fr, shift=Vector((0, 0.7 * dy, 0.7 * up)), out=mm(0.04) * k)
        tents(fr, t, lift=30 * k, curl=20 * k, sway=14, guard=False)
        hang = float(P.get('hit_heavy_chain_hang', 0.0))
        chain_pose(fr, t, sway=14, trail=-30 * k * (1.0 - 0.5 * hang), wag=12)
        if hang:
            for m in CH:
                if m['kind'] == 'tassel':
                    fr.r(m['bones'][0], 45 * k * hang, 0, 0)
        K.add_bones(P, 'hit_heavy_bones', fr, k)
        return fr

    def splay_flat(fr: Frame, rd, k: float, t: float, droop: float = 0.3) -> None:
        """Every tentacle laid out along the ground of a fallen body (turned `rd`): its root swung (by k) to point
        level and away from the body, drooping a little, the chain uncurling, so none props the body up."""
        R = K.m3(rd)
        for m in T:
            d = m['dirs'][0]
            wd = R @ d
            hz = Vector((wd.x, wd.y, 0.0))
            if hz.length < 0.3:
                o = R @ m['out']
                hz = Vector((o.x, o.y, 0.0))
            if hz.length < 1e-4:
                hz = Vector((0.0, -1.0, 0.0))
            target = R.transposed() @ (hz.normalized() + Vector((0.0, 0.0, -droop))).normalized()
            ax = d.cross(target)
            n = len(m['bones'])
            for i, b in enumerate(m['bones']):
                fr.r(b, 0, 0, 0)
                if i == 0 and ax.length > 1e-5:
                    fr.turn(b, ax, math.degrees(d.angle(target)) * k)
                else:
                    di = m['dirs'][i]
                    dh = Vector((di.x, di.y, 0.0))
                    fr.turn(b, dh.cross(Z) if dh.length > 1e-3 else Vector((1.0, 0.0, 0.0)), -10.0 * k * (i / max(1, n - 1)))
                fr.turn(b, Z, 3.0 * (1 - k) * A.wave(t - 0.08 * i, 2.0, m['phase']))

    def p_ko(t: float) -> Frame:
        """It wobbles, then falls onto its back (or its face, or its side), lying `body_width` up (the build settles
        it): flattened a little, the legs splayed in the air, the tentacles splayed out, the sac gone flat, the tongue
        lolling, eyes shut."""
        fr = Frame()
        wob = (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = A.step_ease(t, 0.35, 0.85)
        w_ = 6 * math.sin(t * 2 * math.pi * 2.5) * wob
        if kstyle == 'back':
            rd = (-ko_pitch * fall + w_, 0.0, 0.0)
        elif kstyle == 'front':
            rd = (ko_pitch * fall + w_, 0.0, 0.0)
        else:
            rd = (0.0, -ko_roll * fall + w_, 0.0)
        bw = float(P.get('body_width', 0.6 * HZ))
        h = HZ * (1 - fall) + bw * fall + ko_lift(t)
        fr.r('root', *rd)
        fr.o('body', *K.lay_offset(rd, hip, Vector((0, hip.y, h))))
        fr.r('body', 0, 0, 0)
        squash(fr, 1.0 - 0.1 * fall, wide=1.0 + 0.06 * fall)
        bend(fr, pitch=(10 if kstyle != 'back' else -6) * fall)
        inflate(fr, 0.0)
        tongue(fr, out=0.18 * fall, droop=25 * fall)
        jaw(fr, 16 * fall)
        kick = 10 * A.pulse(t, 0.72, 1.0) if kstyle == 'back' else 0.0
        fold_legs(fr, fall, splay=40, curl=30, wave=kick, t=t)
        splay_flat(fr, rd, fall, t)
        hang = float(P.get('ko_chain_hang', 0.0))
        # on its back a tail would point at the ground and prop it up: it folds up along the back instead (the lie
        # stays a rigid function of body_width, so the build's settle is exact)
        chain_pose(fr, t, sway=2, wag=0, lift=-10.0 * fall)
        if kstyle == 'back':
            for m in CH:
                if m['kind'] == 'tail' and m['parent'] in ('body', 'hips', 'chest'):
                    fr.r(m['bones'][0], 90.0 * fall, 0, 0)
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
        gestures(fr, t, lift=40 * proud + 20 * air, sway=16, rate=3.0)
        inflate(fr, 0.9 * proud)
        tongue(fr)
        jaw(fr, 16 * proud + 8 * air)
        K.add_bones(P, 'win_bones', fr, max(air, A.pulse(t, 0.42, 0.86)))
        K.scale_bones(P, 'win_scale', fr, air)
        return fr

    # ---- strike: 24 frames, impact at 13 (t = 0.5) in every style
    def p_strike(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.42)
        go = A.pulse(t, 0.28, 0.72)
        skip = ()
        if style == 'tongue':
            # rears back with the sac filling and the mouth opening, then the tongue lashes out at the target (fully
            # out from 0.48 to 0.62, so the impact lands at its tip: socket_tongue) and snaps back
            out = A.step_ease(t, 0.3, 0.48) * (1 - A.step_ease(t, 0.62, 0.85))
            body(fr, dy=mm(0.02) * ant - mm(0.04) * go, pitch=-6 * ant + 7 * go, yaw=strike_yaw * go)
            squash(fr, 1.0 + 0.05 * ant - 0.05 * go)
            bend(fr, pitch=-10 * ant + 6 * go)
            inflate(fr, 0.5 * ant)
            tongue(fr, out=out, droop=float(P.get('tongue_aim', 4.0)) * out, curl=18 * A.pulse(t, 0.55, 0.8))
            jaw(fr, 34 * A.step_ease(t, 0.22, 0.36) * (1 - A.step_ease(t, 0.72, 0.9)))
            feet(fr)
        elif style == 'belly':
            # crouches wide, hops at the target and lands belly first on the impact (squashed flat), then bounces up
            air = A.pulse(t, 0.22, 0.5)
            slam = A.pulse(t, 0.44, 0.72)
            crouch = A.pulse(t, 0.0, 0.26)
            up = mm(0.12) * hop_k * air
            body(fr, dy=-mm(0.14) * A.step_ease(t, 0.22, 0.5) * (1 - A.step_ease(t, 0.7, 1.0)), dz=up,
                 pitch=-6 * air + 10 * slam, yaw=strike_yaw * go)
            squash(fr, 1.0 - 0.14 * crouch + 0.12 * air - 0.24 * slam)
            bend(fr, pitch=-8 * air + 8 * slam)
            inflate(fr, 0.3 * air)
            tongue(fr)
            jaw(fr, 12 * slam)
            feet(fr, lift=0.85 * up, out=mm(0.03) * slam)
        elif style == 'slap':
            # a tentacle rears up and out, then whips down across in front at the target, the body twisting into it
            m = TN[SLAP]
            s = 1 if m['side'] >= 0 else -1
            skip = (SLAP,)
            body(fr, dy=-mm(0.03) * go, pitch=4 * go, yaw=s * 10 * ant - s * 14 * go + strike_yaw * go)
            squash(fr, 1.0 + 0.04 * ant - 0.04 * go)
            bend(fr, tilt=-s * 6 * ant, yaw=-s * 6 * go)
            inflate(fr, 0.1)
            tongue(fr)
            jaw(fr, 10 * go)
            feet(fr)
            tent(fr, m, t, lift=70 * ant + 14 * go, curl=-25 * ant + 45 * go, turn=s * 25 * ant - s * 40 * go)
        else:      # 'ink'
            # a tentacle rises beside the head on its left with the body drawing in, then its tip points at the target
            # and the ink leaves socket_<that tentacle> on the impact, the body puffing with the recoil
            m = TN[INK]
            s = 1 if m['side'] >= 0 else -1
            skip = (INK,)
            up = A.step_ease(t, 0.0, 0.28) * (1 - A.step_ease(t, 0.75, 1.0))
            aim = A.pulse(t, 0.3, 0.7)
            puff = A.pulse(t, 0.45, 0.65)
            body(fr, dy=mm(0.03) * A.pulse(t, 0.48, 0.72), pitch=-4 * up + 3 * aim, yaw=strike_yaw * up)
            squash(fr, 1.0 - 0.08 * ant + 0.08 * puff, wide=1.0 + 0.05 * puff)
            bend(fr, pitch=-6 * up + 4 * aim, tilt=-s * 5 * up)
            inflate(fr, 0.2 * puff)
            tongue(fr)
            jaw(fr, 12 * aim)
            feet(fr)
            # Nov 15 (Scrollopus), opt-in: ink_lift [80], ink_turn [12] (degrees swung toward the front after the
            # lift) and ink_curl [(-20, 50)] (the curl with the rise and at the aim), for an arm rooted further back;
            # all 0 lets a recipe pose the arm itself through strike_windup_bones / strike_bones
            il, it_ = float(P.get('ink_lift', 80.0)), float(P.get('ink_turn', 12.0))
            ic0, ic1 = P.get('ink_curl', (-20.0, 50.0))
            tent(fr, m, t, lift=il * up, curl=ic0 * up + ic1 * aim, turn=-s * it_ * up)
        tents(fr, t, roles=('ground',), curl=6 + 10 * go, sway=4, skip=skip)
        gestures(fr, t, lift=12 + 10 * ant, sway=6, skip=skip)
        chain_pose(fr, t, sway=6, trail=16 * go - 8 * ant, wag=8)
        K.add_bones(P, 'strike_bones', fr, go)
        K.add_bones(P, 'strike_windup_bones', fr, ant)
        # Nov 15 (Bloatoad), opt-in: strike_scale {bone: s} scales a bone toward s with the drive (the sac full as the
        # tongue lashes, the attack picture); absent = as before
        K.scale_bones(P, 'strike_scale', fr, go)
        # (and strike_windup_scale with the wind-up: the sac full before the lash too)
        K.scale_bones(P, 'strike_windup_scale', fr, ant)
        return fr

    def p_cast(t: float) -> Frame:
        fr = Frame()
        up = A.step_ease(t, 0.0, 0.32) * (1 - A.step_ease(t, 0.72, 1.0))
        rel = A.pulse(t, 0.48, 0.72)
        if cstyle == 'inflate':
            # swells up with the sac at its fullest by `release`, then lets it all out at once (a croak, a quake)
            sac_k = A.step_ease(t, 0.0, 0.45) * (1 - A.step_ease(t, 0.53, 0.64))
            body(fr, dy=-mm(0.03) * rel, pitch=-5 * up + 8 * rel)
            squash(fr, 1.0 + 0.05 * up - 0.12 * rel, wide=1.0 + 0.08 * up + 0.08 * rel)
            bend(fr, pitch=-12 * up + 10 * rel)
            inflate(fr, sac_k)
            tongue(fr)
            jaw(fr, 32 * rel)
            feet(fr, out=mm(0.02) * up)
            tents(fr, t, roles=('ground',), curl=8, spread=14 * rel, sway=4)
            gestures(fr, t, lift=10 * up + 20 * rel, sway=8)
        else:
            # rises tall with the tentacles (and what they hold) raised, then thrusts them at the target at `release`
            body(fr, pitch=-4 * up + 8 * rel)
            squash(fr, 1.0 + 0.08 * up - 0.12 * rel)
            bend(fr, pitch=-10 * up + 8 * rel)
            inflate(fr, 0.4 * up)
            tongue(fr)
            jaw(fr, 18 * up)
            feet(fr)
            tents(fr, t, roles=('ground',), curl=6 + 8 * up, sway=6, rate=2.0)
            gestures(fr, t, lift=50 * up - 30 * rel, curl=-20 * up + 30 * rel, sway=8, rate=2.0)
        chain_pose(fr, t, sway=8, rate=2.0, trail=20 * rel, wag=10)
        return fr

    def p_shove(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.32)
        go = A.pulse(t, 0.2, 0.55)
        dy = mm(0.04) * ant - mm(0.14) * go
        body(fr, dy=dy, pitch=-5 * ant + 7 * go, yaw=strike_yaw * go)
        squash(fr, 1.0 - 0.1 * ant + 0.12 * go, axis='y')
        bend(fr, pitch=4 * go)
        inflate(fr, 0.15 * ant)
        tongue(fr)
        jaw(fr, 0)
        feet(fr, shift=Vector((0, 0.5 * dy, 0)))
        tents(fr, t, roles=('ground',), curl=8 * go, sway=4)
        gestures(fr, t, lift=14 * go, sway=4)
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
    clip('run', 20, lambda t: gait(t, 'run', FWD, lean=5), root_speed=speed_of('run'), markers=gait_marks('run'))
    clip('sit_down', 24, p_sit_down, loop=False, hold=True)
    clip('sit', 120, p_sit, step=2)
    clip('dizzy', 60, p_dizzy, faces=[(1, 'dizzy')])
    clip('battle_idle', 40, p_battle_idle)
    clip('step_fwd', 24, lambda t: gait(t, 'step_fwd', FWD, guard_w=1.0), root_speed=speed_of('step_fwd'), markers=gait_marks('step_fwd'))
    clip('step_back', 24, lambda t: gait(t, 'step_back', BACK, guard_w=1.0), root_speed=speed_of('step_back'), markers=gait_marks('step_back'))
    clip('dash', 20, lambda t: gait(t, 'dash', FWD, lean=8, rate=1.5), root_speed=speed_of('dash'), markers=gait_marks('dash'))
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
