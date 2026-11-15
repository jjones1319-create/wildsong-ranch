"""The shelled body plan (ART_2_PLAN §4, batch 5): rig template, sockets, springs and the clip generators for monsters
that carry a rigid shell on short legs: Moatshell (a tortoise; a castle keep for a shell) and Reefclaw (the crab option:
six walking legs, two claws, one of them big, and eyes on stalks).

A recipe selects it with `PLAN = 'shelled'` (tools/blender/monsters/breeds/RECIPE.md, "Shelled plan"). The same build
(build_ultra.py) drives it as every other plan: rig_specs, sockets, springs, chain_groups, heatless, make_clips,
STAR_CLIPS, MOVE_CLIPS, ROOT_DIRS and KO_ROLL (ko rolls it over at `ko_roll` degrees, onto its side or its back, and the
build measures and settles `body_width` so it lies on the ground, lifting any sinking frame with `ko_lift`).

Space: metres; the monster faces −Y, Z is up, +X is its left. Model it standing. From rig_p() (`P`):
  hip                  the shell's centre: the bone `hips` (parent `root`) carries the shell, never bends or squashes
  chest                the front opening, where the neck and the front legs come out: `chest` (parent `hips`) slides
                       back into the shell when it tucks (brace, hit, sleep, ko 'tuck')
  neck                 [p0 … pN] → neck.1..N from the opening to the head (none: the head sits on `chest`, a crab)
  head_c, head_r       the face's centre and size (the jaw, the mouth socket, the review framing)
  legs                 the left legs, front to back: two-bone legs (leg<i>.L, shin<i>.L, foot<i>.L), mirrored, planted
                       by IK
Options (RECIPE.md): size_k, shell_top, head_base, head_tip, jaw, legs, claws, big_claw, stalks, tail, chains, props,
tuck, strike_style, cast_style, ko_style, ko_roll, body_width, ko_lift and the per-clip knobs every plan has.
Rotations are world-aligned degrees relative to the parent at rest (lib.anim.ClipBuilder.rot): +x tips an upright bone
forward (and lifts a backward-pointing one, swings a hanging one back), +z turns toward the monster's left, +y tilts
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
from monsters.plans import kin as K
from monsters.plans.kin import Frame, mirror

PLAN = 'shelled'
SIDES = K.SIDES
KO_ROLL = 80.0              # the build's first guess of body_width rolls it this far; the settle corrects any ko_roll
STRIKE_STYLES = ('bash', 'bite', 'launch', 'claw', 'pinch')
CAST_STYLES = ('brace', 'raise')
KO_STYLES = ('roll', 'tuck')
SPRINGS = []                # Art 2.0 compatibility only; the Ultra build calls springs(P)
# chain kinds: a flag flutters, a tassel or a cloth hangs and sways, an antenna and a tail spring
KINDS = ('flag', 'tassel', 'cloth', 'antenna', 'tail')
HEATLESS_KINDS = ('flag', 'tassel', 'cloth')

SIDESTEP_DISTANCE = 1.4 * 100 / 150      # the same arena distance as every other plan
ROOT_DIRS = {'walk': (0, 0, 1), 'run': (0, 0, 1), 'dash': (0, 0, 1), 'step_fwd': (0, 0, 1), 'step_back': (0, 0, -1),
             'strafe_l': (1, 0, 0), 'strafe_r': (-1, 0, 0), 'sidestep_l': (1, 0, 0), 'sidestep_r': (-1, 0, 0)}
STAR_CLIPS = ['idle', 'idle_happy', 'idle_tired', 'idle_sad', 'idle_sick', 'sleep', 'eat', 'pet', 'look_around', 'hop',
              'celebrate', 'walk', 'run', 'sit_down', 'sit', 'dizzy', 'battle_idle', 'step_fwd', 'step_back', 'dash',
              'strike', 'cast', 'shove', 'hit', 'hit_heavy', 'ko', 'win']
MOVE_CLIPS = ['strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r']
# gaits: (frames, stride as a share of the leg's reach, the planted share of the cycle, foot lift as a share of the leg)
GAITS = {'walk': (30, 0.5, 0.7, 0.18), 'run': (20, 0.75, 0.55, 0.24), 'dash': (20, 0.95, 0.45, 0.28),
         'step_fwd': (24, 0.45, 0.65, 0.16), 'step_back': (24, 0.38, 0.65, 0.14), 'strafe': (24, 0.42, 0.65, 0.16)}


# --------------------------------------------------------------------------- options
def size_of(P: dict) -> float:
    return float(P.get('size_k', 1.0))


def _v(p) -> Vector:
    return Vector(p)


def crab(P: dict) -> bool:
    """The crab option: claws (and usually stalks, six legs, no neck)."""
    return bool(P.get('claws'))


def neck_points(P: dict) -> list[Vector]:
    return [_v(p) for p in (P.get('neck') or [])]


def neck_names(P: dict) -> list[str]:
    n = len(neck_points(P))
    return [f'neck.{i + 1}' for i in range(n - 1)] if n >= 2 else []


def head_base(P: dict) -> Vector:
    pts = neck_points(P)
    if len(pts) >= 2:
        return pts[-1]
    if P.get('head_base'):
        return _v(P['head_base'])
    return _v(P['head_c']) + Vector((0.0, 0.6 * float(P['head_r']), 0.0))


def head_tip(P: dict) -> Vector:
    if P.get('head_tip'):
        return _v(P['head_tip'])
    return _v(P['head_c']) + Vector((0.0, -0.9 * float(P['head_r']), 0.1 * float(P['head_r'])))


def jaw_points(P: dict) -> tuple[Vector, Vector]:
    if P.get('jaw'):
        return _v(P['jaw']['head']), _v(P['jaw']['tail'])
    hc, hr = _v(P['head_c']), float(P['head_r'])
    return hc + Vector((0, -0.3 * hr, -0.45 * hr)), hc + Vector((0, -0.9 * hr, -0.55 * hr))


def shell_top(P: dict) -> Vector:
    if P.get('shell_top'):
        return _v(P['shell_top'])
    return _v(P['hip']) + Vector((0.0, 0.0, 0.3 * size_of(P)))


def legs(P: dict) -> list[dict]:
    """Every leg, left then right: {'i', 'tag', 's', 'upper', 'lower', 'foot' (or None), 'hip', 'knee', 'ankle',
    'toe' (or None), 'parent'}. P['legs'] lists the left legs front to back as {'hip', 'knee', 'ankle', 'toe'?,
    'parent'?: 'hips'}; the right side mirrors them."""
    out = []
    for tag, s in SIDES:
        for i, lg in enumerate(P.get('legs') or [], start=1):
            toe = mirror(lg['toe'], s) if lg.get('toe') else None
            out.append({'i': i, 'tag': tag, 's': s, 'upper': f'leg{i}.{tag}', 'lower': f'shin{i}.{tag}',
                        'foot': f'foot{i}.{tag}' if toe is not None else None,
                        'hip': mirror(lg['hip'], s), 'knee': mirror(lg['knee'], s), 'ankle': mirror(lg['ankle'], s),
                        'toe': toe, 'parent': lg.get('parent', 'hips'), 'front': i == 1})
    return out


def claws(P: dict) -> dict[str, dict]:
    """The crab's claws per side: {'arm', 'forearm', 'claw', 'pincer' (bone names), 'shoulder', 'elbow', 'wrist', 'tip',
    'finger' (head, tail)}. P['claws'] is one dict (mirrored) or {'L': {...}, 'R': {...}} (a big and a small one)."""
    c = P.get('claws')
    if not c:
        return {}
    out = {}
    for tag, s in SIDES:
        d = c.get(tag) if ('L' in c or 'R' in c) else c
        if not d:
            continue
        mir = s if not ('L' in c or 'R' in c) else 1
        f = d.get('finger')
        out[tag] = {'arm': f'arm.{tag}', 'forearm': f'forearm.{tag}', 'claw': f'claw.{tag}', 'pincer': f'pincer.{tag}',
                    'shoulder': mirror(d['shoulder'], mir), 'elbow': mirror(d['elbow'], mir), 'wrist': mirror(d['wrist'], mir),
                    'tip': mirror(d['tip'], mir),
                    'finger': (mirror(f[0], mir), mirror(f[1], mir)) if f else None, 's': s}
        # the pincer opens about `open_axis` (model space; mirrored as a rotation), else lifting its tip
        ax = d.get('open_axis')
        if ax is not None:
            out[tag]['open_axis'] = Vector((ax[0], -ax[1], -ax[2])) if mir == -1 else Vector(ax)
        elif f:
            fd = out[tag]['finger'][1] - out[tag]['finger'][0]
            out[tag]['open_axis'] = fd.cross(Vector((0, 0, 1))) if Vector((fd.x, fd.y, 0)).length > 1e-6 else Vector((1, 0, 0))
        else:
            out[tag]['open_axis'] = Vector((1, 0, 0))
    return out


def big_claw(P: dict) -> str:
    """The side of the big claw (its strike swings it): P['big_claw'], else the longer claw."""
    cl = claws(P)
    if P.get('big_claw') in cl:
        return P['big_claw']
    if not cl:
        return 'R'
    return max(cl, key=lambda t: (cl[t]['tip'] - cl[t]['shoulder']).length + (0.001 if t == 'R' else 0.0))


def stalks(P: dict) -> dict[str, dict]:
    """Eye stalks per side: {'bones': [stalk<T>.1, stalk<T>.2], 'points': [base, mid, tip], 'visor': (head, tail) or
    None}. P['stalks'] = {'base', 'mid', 'tip', 'visor'?: (head, tail)} for the left; mirrored. The recipe hangs the
    blink bones on the tips: EYE_PARENTS = {'L': 'stalkL.2', 'R': 'stalkR.2'}."""
    st = P.get('stalks')
    if not st:
        return {}
    out = {}
    for tag, s in SIDES:
        pts = [mirror(st[k], s) for k in ('base', 'mid', 'tip')]
        v = st.get('visor')
        out[tag] = {'bones': [f'stalk{tag}.1', f'stalk{tag}.2'], 'points': pts, 's': s,
                    'visor': (mirror(v[0], s), mirror(v[1], s)) if v else None, 'visor_bone': f'visor.{tag}'}
    return out


def tail_points(P: dict) -> list[Vector]:
    return [_v(p) for p in (P.get('tail') or [])]


def tail_names(P: dict) -> list[str]:
    n = len(tail_points(P))
    return [f'tail.{i + 1}' for i in range(n - 1)] if n >= 2 else []


def chains(P: dict) -> list[dict]:
    """Extra chains: each {'name', 'kind', 'parent': 'hips', 'points', 'stiff' 0..1, 'heat', 'mirror', 'spring'};
    `mirror` True adds a right twin (<name>L / <name>R). A flag on a pole: parent it to the pole's prop bone."""
    out = []
    for m in P.get('chains') or []:
        kind = m.get('kind', 'tassel')
        if kind not in KINDS:
            raise ValueError(f"chain {m.get('name')}: kind {kind!r}, one of {', '.join(KINDS)}")
        nm0 = m.get('name', kind)
        twins = [(nm0 + 'L', 1), (nm0 + 'R', -1)] if m.get('mirror') else [(nm0, 1)]
        for nm, s in twins:
            pts = [mirror(p, s) for p in m['points']]
            if len(pts) < 2:
                raise ValueError(f'chain {nm}: needs at least 2 points')
            out.append({'name': nm, 'kind': kind, 'parent': m.get('parent', 'hips'), 'points': pts, 'side': s,
                        'stiff': float(m.get('stiff', 0.0)), 'heat': bool(m.get('heat', kind not in HEATLESS_KINDS)),
                        'spring': bool(m.get('spring', True)),
                        'tx': (pts[-1] - pts[0]).normalized().x if (pts[-1] - pts[0]).length > 1e-6 else 0.0,
                        'hangs': (pts[-1] - pts[0]).length > 1e-6 and (pts[-1] - pts[0]).normalized().z < -0.5,
                        'clear': max(0.0, min(p.z for p in pts) - 0.03 * size_of(P)),
                        'bones': [f'{nm}.{i + 1}' for i in range(len(pts) - 1)],
                        'length': sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))})
    return out


def _style(P: dict, key: str, allowed: tuple, default: str) -> str:
    st = P.get(key, default)
    if st not in allowed:
        raise ValueError(f"{key} {st!r}: one of {', '.join(allowed)}")
    return st


def strike_style(P: dict) -> str:
    return _style(P, 'strike_style', STRIKE_STYLES, 'claw' if crab(P) else 'bash')


def cast_style(P: dict) -> str:
    return _style(P, 'cast_style', CAST_STYLES, 'raise' if crab(P) else 'brace')


def ko_style(P: dict) -> str:
    return _style(P, 'ko_style', KO_STYLES, 'roll')


def springs(P: dict) -> list[dict]:
    """The tail, the eye stalks and every chain that springs (the runtime adds a damped lag to them)."""
    out = []
    if tail_names(P):
        out.append({'kind': 'tail', 'chain': tail_names(P)})
    for tag, st in stalks(P).items():
        out.append({'kind': 'stalk', 'chain': list(st['bones'])})
    for m in chains(P):
        if m['spring']:
            out.append({'kind': m['kind'], 'chain': m['bones']})
    return out


def chain_groups(P: dict) -> dict[str, str]:
    """Bone-name prefix → kind, for a recipe's CLIP_CALM: 'tail', 'neck', 'stalk' (stalkL, stalkR), each chain by
    its name or kind, 'claw' (arm, forearm, claw, pincer) and 'leg' (leg<i>, shin<i>, foot<i>)."""
    out = {'tail': 'tail', 'neck': 'neck'}
    for tag in stalks(P):
        out[f'stalk{tag}'] = 'stalk'
    for m in chains(P):
        out[m['name']] = m['kind']
    if claws(P):
        for p in ('arm', 'forearm', 'claw', 'pincer'):
            out[p] = 'claw'
    for i in range(1, len(P.get('legs') or []) + 1):
        for p in ('leg', 'shin', 'foot'):
            out[f'{p}{i}'] = 'leg'
    return out


def heatless(P: dict) -> set[str]:
    """Bones whose heat weights go to their parent, so the recipe's body_weight_regions skins them: flags, tassels and
    cloths (unless heat=True), the visors, the claws (unless P['claw_heat']) and, with P['rigid_legs'] (default on
    for a crab: a shell's jointed legs), the legs."""
    out = {m['name'] for m in chains(P) if not m['heat']}
    if stalks(P):
        out |= {'visor', 'stalkL', 'stalkR'}
    if claws(P) and not P.get('claw_heat'):
        out |= {'arm', 'forearm', 'claw', 'pincer'}
    if P.get('rigid_legs', crab(P)):
        for i in range(1, len(P.get('legs') or []) + 1):
            out |= {f'leg{i}', f'shin{i}', f'foot{i}'}
    return out


# --------------------------------------------------------------------------- rig
def rig_specs(P: dict) -> list[BoneSpec]:
    sk = size_of(P)
    hip, ch = _v(P['hip']), _v(P['chest'])
    fwd = ch - hip
    if fwd.length < 0.02 * sk:
        fwd = Vector((0.0, -0.1 * sk, 0.0))
    specs: list[BoneSpec] = [
        BoneSpec('root', (0, 0, 0), (0, -0.25 * sk, 0), radius=0.5 * sk),
        BoneSpec('hips', tuple(hip), tuple(hip + 0.8 * fwd), 'root', radius=0.4 * sk),
        BoneSpec('chest', tuple(ch), tuple(ch + fwd.normalized() * 0.08 * sk), 'hips', radius=0.25 * sk),
    ]
    npts, names = neck_points(P), neck_names(P)
    for i, nm in enumerate(names):
        specs.append(BoneSpec(nm, tuple(npts[i]), tuple(npts[i + 1]), 'chest' if i == 0 else names[i - 1], connect=i > 0,
                              radius=0.12 * sk))
    hr = float(P['head_r'])
    specs.append(BoneSpec('head', tuple(head_base(P)), tuple(head_tip(P)), names[-1] if names else 'chest', connect=bool(names),
                          radius=max(0.15 * sk, 1.2 * hr)))
    jh, jt = jaw_points(P)
    specs.append(BoneSpec('jaw', tuple(jh), tuple(jt), 'head', radius=0.5 * hr))
    for tag, st in stalks(P).items():
        b, p = st['bones'], st['points']
        specs.append(BoneSpec(b[0], tuple(p[0]), tuple(p[1]), 'head', radius=0.05 * sk))
        specs.append(BoneSpec(b[1], tuple(p[1]), tuple(p[2]), b[0], connect=True, radius=0.05 * sk))
        if st['visor']:
            specs.append(BoneSpec(st['visor_bone'], tuple(st['visor'][0]), tuple(st['visor'][1]), b[1], radius=0.04 * sk))
    for lg in legs(P):
        specs.append(BoneSpec(lg['upper'], tuple(lg['hip']), tuple(lg['knee']), lg['parent'], radius=0.08 * sk))
        specs.append(BoneSpec(lg['lower'], tuple(lg['knee']), tuple(lg['ankle']), lg['upper'], connect=True, radius=0.07 * sk))
        if lg['foot']:
            specs.append(BoneSpec(lg['foot'], tuple(lg['ankle']), tuple(lg['toe']), lg['lower'], connect=True, radius=0.06 * sk))
    for tag, c in claws(P).items():
        specs.append(BoneSpec(c['arm'], tuple(c['shoulder']), tuple(c['elbow']), 'chest', radius=0.08 * sk))
        specs.append(BoneSpec(c['forearm'], tuple(c['elbow']), tuple(c['wrist']), c['arm'], connect=True, radius=0.08 * sk))
        specs.append(BoneSpec(c['claw'], tuple(c['wrist']), tuple(c['tip']), c['forearm'], connect=True, radius=0.1 * sk))
        if c['finger']:
            specs.append(BoneSpec(c['pincer'], tuple(c['finger'][0]), tuple(c['finger'][1]), c['claw'], radius=0.06 * sk))
    tp, tn = tail_points(P), tail_names(P)
    for i, nm in enumerate(tn):
        specs.append(BoneSpec(nm, tuple(tp[i]), tuple(tp[i + 1]), 'hips' if i == 0 else tn[i - 1], connect=i > 0, radius=0.06 * sk))
    # props before chains, so a flag can fly from a pole prop (the build folds heatless bones into their parents in
    # reverse order: the flag into the pole, the pole into the shell)
    for pr in P.get('props', []) or []:
        specs.append(BoneSpec(f"prop.{pr['name']}", tuple(pr['head']), tuple(pr['tail']), pr.get('parent', 'hips'), radius=0.08 * sk))
    for m in chains(P):
        for i, nm in enumerate(m['bones']):
            specs.append(BoneSpec(nm, tuple(m['points'][i]), tuple(m['points'][i + 1]), m['parent'] if i == 0 else m['bones'][i - 1],
                                  connect=i > 0, radius=0.06 * sk))
    return specs


def sockets(P: dict) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """The game's seven (socket_head, _crown, _back, _mouth, _paw_L/_R, _tail), socket_shell at the shell's top (a
    turret's volley), socket_claw_L/_R at the claws' tips, socket_<chain> at each chain's tip, socket_<prop>."""
    sk = size_of(P)
    hc, hr = _v(P['head_c']), float(P['head_r'])
    hip, ch, top = _v(P['hip']), _v(P['chest']), shell_top(P)
    _jh, jt = jaw_points(P)
    st = stalks(P)
    crown = (sum((s['points'][-1] for s in st.values()), Vector()) / len(st) + Vector((0, 0, 0.06 * sk))) if st \
        else hc + Vector((0, 0, hr + 0.12 * sk))
    out = {
        'socket_head': ('head', tuple(hc + Vector((0, 0, hr)))),
        'socket_crown': ('head', tuple(crown)),
        'socket_back': ('hips', tuple(top)),
        'socket_shell': ('hips', tuple(top)),
        'socket_mouth': ('jaw', tuple(jt + Vector((0, -0.02 * sk, 0)))),
    }
    cl = claws(P)
    front = {lg['tag']: lg for lg in legs(P) if lg['front']}
    for tag, s in SIDES:
        if tag in cl:
            out[f'socket_claw_{tag}'] = (cl[tag]['claw'], tuple(cl[tag]['tip']))
            out[f'socket_paw_{tag}'] = out[f'socket_claw_{tag}']
        elif tag in front:
            lg = front[tag]
            out[f'socket_paw_{tag}'] = (lg['foot'] or lg['lower'], tuple(lg['toe'] if lg['toe'] is not None else lg['ankle']))
        else:
            out[f'socket_paw_{tag}'] = ('chest', (s * 0.6 * hr, ch.y - 0.05 * sk, ch.z))
    tp, tn = tail_points(P), tail_names(P)
    out['socket_tail'] = (tn[-1], tuple(tp[-1])) if tn else ('hips', tuple(2 * hip - ch))
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
    CRAB = crab(P)
    if style in ('claw', 'pinch') and not CRAB:
        raise ValueError(f'strike_style {style!r} needs claws (the crab option)')
    LEGS = [lg for lg in legs(P) if has(lg['upper']) and has(lg['lower'])]
    CL = {t: c for t, c in claws(P).items() if has(c['arm'])}
    BIG = big_claw(P) if CL else None
    SMALL = next((t for t in CL if t != BIG), None)
    ST = stalks(P)
    NECK = [n for n in neck_names(P) if has(n)]
    TAIL = [n for n in tail_names(P) if has(n)]
    CH = chains(P)
    JAW = bool(P.get('jaw_open', False))
    CLOSED = P.get('blink_closed')
    hip = _v(P['hip'])
    HZ = hip.z
    hr = float(P['head_r'])
    tuck_k = float(P.get('tuck', 0.35 if CRAB else 1.0))
    head_k = float(P.get('head_turn', 1.0 if NECK else 0.3))     # a face on the shell turns little; its stalks look
    ko_roll = float(P.get('ko_roll', KO_ROLL))
    lift_tab = P.get('ko_lift') or []
    strike_yaw = float(P.get('strike_yaw', 0.0))   # degrees toward its left at the drive (the 70-degree strike shot)

    def mm(v: float) -> float:
        """An absolute offset in Puddlepup's metres, at this breed's size."""
        return v * sk

    # ---- rest geometry the motions are measured in
    for lg in LEGS:
        lg['reach'] = rig.length(lg['upper']) + rig.length(lg['lower'])
        lg['rest_ankle'] = rig.tail[lg['lower']].copy()
        lg['rest_hip'] = rig.head[lg['upper']].copy()
        fallback = Vector((lg['s'] * 0.7, -0.3 if lg['front'] else 0.3, 0.6)).normalized()
        lg['hint'] = rig.bend_hint(lg['upper'], lg['lower'], fallback)
        # diagonal pairs with two legs a side, alternating tripods with three
        lg['phase'] = 0.5 * ((lg['i'] - 1 + (0 if lg['tag'] == 'L' else 1)) % 2)
    LEG = (sum(lg['reach'] for lg in LEGS) / len(LEGS)) if LEGS else mm(0.2)
    neck_len = sum(rig.length(n) for n in NECK)
    TAIL_PTS = tail_points(P)
    TAIL_LEN = sum((TAIL_PTS[i + 1] - TAIL_PTS[i]).length for i in range(len(TAIL_PTS) - 1))
    TD = float(P.get('tuck_depth', (0.75 * neck_len + 0.3 * hr) if NECK else mm(0.02)))

    def shell_room() -> float:
        """How far the shell can come down before its underside touches the ground: the recipe's `sink`, else measured
        on lo_body (the lowest vertex owned mostly by the shell or the front body), else half the hip height."""
        if P.get('sink') is not None:
            return float(P['sink'])
        body = bpy.data.objects.get('lo_body')
        if body is not None and body.type == 'MESH':
            gs = {body.vertex_groups[n].index for n in ('hips', 'chest') if n in body.vertex_groups}
            zs = [v.co.z for v in body.data.vertices if v.groups and max(v.groups, key=lambda g: g.weight).group in gs]
            if len(zs) > 20:
                return max(0.0, float(np.percentile(zs, 0.5)) - mm(0.005))
        return 0.5 * HZ

    ROOM = shell_room()

    SWINGING = set(TAIL) | {b for m in CH for b in m['bones']}

    def rides_shell(b: str | None) -> bool:
        while b:
            if b == 'chest' or b in SWINGING or b.startswith(('leg', 'shin', 'foot')):
                return False
            if b == 'hips':
                return True
            b = rig.parent.get(b)
        return False

    def shell_points() -> np.ndarray | None:
        """lo_body's vertices that move with the shell (relative to its centre, at most 3000): body() keeps them off
        the ground whatever it is asked to do."""
        ob = bpy.data.objects.get('lo_body')
        if ob is None or ob.type != 'MESH':
            return None
        names = {g.index: g.name for g in ob.vertex_groups}
        pts = [v.co[:] for v in ob.data.vertices
               if v.groups and rides_shell(names.get(max(v.groups, key=lambda g: g.weight).group))]
        if len(pts) < 20:
            return None
        a = np.array(pts) - np.array(hip[:])
        return a[:: max(1, len(a) // 3000)]

    SHELL_PTS = shell_points()
    C.log(f'shelled: shell room {ROOM:.3f} m, {0 if SHELL_PTS is None else len(SHELL_PTS)} shell points '
          f'(lowest {HZ + float(SHELL_PTS[:, 2].min()) if SHELL_PTS is not None else 0.0:.3f} m), {len(LEGS)} legs, tuck depth {TD:.3f} m')
    # a tail resting on the ground at rest must not lift every frame: the floor is the lower of 3 mm and the rest pose's
    CLEAR = min(mm(0.003), HZ + float(SHELL_PTS[:, 2].min())) if SHELL_PTS is not None else 0.0

    def reach_drop(shift: Vector, margin: float = 0.97) -> float:
        """How far the body must come down so every foot `shift` off its rest spot stays within reach."""
        need = 0.0
        for lg in LEGS:
            d = lg['rest_hip'] - (lg['rest_ankle'] + shift)
            r2 = (margin * lg['reach']) ** 2 - d.x * d.x - d.y * d.y
            need = max(need, d.z - math.sqrt(max(0.0, r2)))
        return min(max(0.0, need), 0.8 * ROOM)

    DIRS = {'walk': Vector((0, -1, 0)), 'run': Vector((0, -1, 0)), 'dash': Vector((0, -1, 0)), 'step_fwd': Vector((0, -1, 0)),
            'step_back': Vector((0, 1, 0))}
    stride_k = float(P.get('stride', 1.0))

    def stride_of(kind: str) -> float:
        return GAITS[kind][1] * LEG * stride_k

    def speed_of(kind: str) -> float:
        n, _sk, duty, _l = GAITS[kind]
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

    # ---- posing helpers (each adds to a Frame; each keys the same bones on every frame of a clip)
    def body(fr: Frame, dz: float = 0.0, dy: float = 0.0, dx: float = 0.0, pitch: float = 0.0, roll: float = 0.0,
             yaw: float = 0.0) -> None:
        """The shell moved and turned about its centre (+pitch dips the front, +roll tilts it toward its left), never
        lower than CLEAR above the ground (a tip back drops the rear rim: it rises by just enough)."""
        if SHELL_PTS is not None:
            Rz = np.array(K.m3((pitch, roll, yaw)))[2]
            low = HZ + dz + float((SHELL_PTS @ Rz).min())
            if low < CLEAR:
                dz += CLEAR - low
        fr.o('hips', dx, dy, dz)
        fr.drop = max(fr.drop, -dz)
        fr.shell = (dz, pitch, roll, yaw)

    def shell_z(fr: Frame, p: Vector) -> float:
        """The height of a rest point carried rigidly by the shell, in this frame's body pose (0 offsets if unset)."""
        dz, pitch, roll, yaw = getattr(fr, 'shell', (0.0, 0.0, 0.0, 0.0))
        return HZ + dz + (K.m3((pitch, roll, yaw)) @ (p - hip)).z

    def tip_need(fr: Frame, pts: list, margin: float) -> float:
        """How far a chain's lowest point (carried by the shell, unbent) would sink below `margin`."""
        return max(0.0, margin - min(shell_z(fr, p) for p in pts))
        fr.r('hips', pitch, roll, yaw)

    def look(fr: Frame, pitch: float = 0.0, yaw: float = 0.0, tilt: float = 0.0, reach: float = 0.0) -> None:
        """The head: pitch (+ down), yaw (+ toward its left), tilt, shared over the neck and the head; `reach` metres
        pushes the neck out of the shell (a negative tuck)."""
        if NECK:
            n = len(NECK)
            for nm in NECK:
                fr.r(nm, 0.6 * pitch / n, 0.5 * tilt / n, 0.6 * yaw / n)
            fr.r('head', 0.4 * pitch, 0.5 * tilt, 0.4 * yaw)
        else:
            fr.r('head', head_k * pitch, head_k * tilt, head_k * yaw)
        fr.o('chest', 0.0, -reach, 0.0)

    def tuck(fr: Frame, k: float, stalks_k: float | None = None) -> None:
        """Pull the head (the neck and the front body slide back into the shell, `tuck` × tuck_depth) and fold the eye
        stalks back onto the shell (by `stalks_k`, else k; the legs: plant(…, tuck_=k))."""
        sk_ = k if stalks_k is None else stalks_k
        kk = k * tuck_k
        fr.o('chest', 0.0, TD * kk, -0.12 * TD * kk)
        for nm in NECK:
            fr.r(nm, 14 * kk / len(NECK), 0, 0)
        fr.r('head', 10 * kk, 0, 0)
        for tag, st in ST.items():
            fr.r(st['bones'][0], -55 * sk_, 0, 0)
            fr.r(st['bones'][1], -25 * sk_, 0, 0)

    def plant(fr: Frame, lg: dict, d: Vector | None = None, tuck_: float = 0.0, pitch: float = 0.0) -> None:
        """A foot's IK goal `d` off its rest spot (root space, so the root carries it), drawn in under its hip by
        `tuck_` (0..1); the knee bends in its rest plane; the foot keeps flat (+pitch: toes down)."""
        a = lg['rest_ankle'] + (d if d is not None else Vector())
        if tuck_:
            h, ra = lg['rest_hip'], lg['rest_ankle']
            # under its hip and up into the shell, carried down with the shell when it sinks (sleep, the tuck ko)
            tucked = Vector((ra.x + 0.6 * (h.x - ra.x), ra.y + 0.5 * (h.y - ra.y), max(ra.z, ra.z + 0.55 * (h.z - ra.z) - fr.drop)))
            a = a.lerp(tucked + (d if d is not None else Vector()), min(1.0, tuck_))
        fr.ik[(lg['upper'], lg['lower'], lg['foot'])] = {'root_target': a, 'rest_hint': lg['hint'], 'hint_bone': lg['parent'],
                                                       'pitch': pitch if lg['foot'] else None}

    def feet(fr: Frame, tuck_: float = 0.0, out: float = 0.0, lift: float = 0.0, shift: Vector | None = None,
             spread: float = 0.0) -> None:
        """Every foot planted (wider by `out`, lifted `lift`, all moved by `shift`; `spread` moves the front feet
        forward and the back ones back)."""
        nmax = max([lg['i'] for lg in LEGS] or [1])
        for lg in LEGS:
            fb = -1.0 if lg['front'] else (1.0 if lg['i'] == nmax else 0.0)
            d = Vector((lg['s'] * out, fb * spread, lift)) + (shift if shift is not None else Vector())
            plant(fr, lg, d, tuck_)

    def fold_legs(fr: Frame, k: float, splay: float = 40.0, curl: float = 50.0, wave: float = 0.0, t: float = 0.0) -> None:
        """Legs by angle, off the ground (ko, a flip): swung out `splay` degrees and bent `curl`, kicking `wave`."""
        for lg in LEGS:
            s = lg['s']
            w = wave * A.wave(t, 3.0, 0.25 * lg['i'] + (0.5 if lg['tag'] == 'R' else 0.0))
            fr.r(lg['upper'], 0, -s * (splay * k + w), 0)       # −y swings a left leg's foot out (+x)
            fr.r(lg['lower'], 0, s * (curl * k + 0.5 * w), 0)    # and +y curls its shin in under the shell

    def stalk_pose(fr: Frame, t: float, droop: float = 0.0, sway: float = 0.0, rate: float = 1.0, spread: float = 0.0,
                   look_: float = 0.0, visor: float = 0.0, solo: str | None = None) -> None:
        """The eye stalks: droop (+ forward), sway (each its own phase), spread outward, look (+ toward its left;
        only `solo`'s when given), the visors lowered by `visor` degrees."""
        for tag, st in ST.items():
            s = st['s']
            b1, b2 = st['bones']
            w = sway * A.wave(t, rate, 0.0 if tag == 'L' else 0.35)
            lk = look_ if (solo is None or solo == tag) else 0.0
            fr.r(b1, droop + 0.3 * w, s * spread, lk + w)
            fr.r(b2, 0.5 * droop, 0.4 * s * spread, 0.5 * w)
            if st['visor'] and has(st['visor_bone']):
                fr.r(st['visor_bone'], visor, 0, 0)

    def claw(fr: Frame, tag: str | None, raise_: float = 0.0, out: float = 0.0, bend: float = 0.0, wrist: float = 0.0,
             open_: float = 0.0) -> None:
        """A claw by angle: raised (lifted about its own horizontal), swung out (+) or across (−), the elbow bent in
        (+), the wrist lifted, the pincer opened `open_` degrees."""
        c = CL.get(tag) if tag else None
        if not c:
            return
        s = c['s']
        d = c['wrist'] - c['shoulder']
        dh = Vector((d.x, d.y, 0.0))
        lift_ax = dh.cross(Vector((0, 0, 1))) if dh.length > 1e-6 else Vector((1, 0, 0))
        fr.r(c['arm'], 0, 0, 0)
        fr.turn(c['arm'], lift_ax, raise_)                   # lifted about its own horizontal, then
        fr.turn(c['arm'], (0, 0, 1), s * out)                # swung about the vertical
        fr.r(c['forearm'], 0, 0, -s * bend)
        cd = c['tip'] - c['wrist']
        ch = Vector((cd.x, cd.y, 0.0))
        fr.r(c['claw'], 0, 0, 0)
        fr.turn(c['claw'], ch.cross(Vector((0, 0, 1))) if ch.length > 1e-6 else Vector((1, 0, 0)), wrist)
        if c['finger'] and has(c['pincer']):
            fr.turn(c['pincer'], c['open_axis'], open_)
            fr.r(c['pincer'], 0, 0, 0)

    def claws_both(fr: Frame, **kw) -> None:
        for tag in CL:
            claw(fr, tag, **kw)

    def chain_pose(fr: Frame, t: float, sway: float = 0.0, rate: float = 1.0, trail: float = 0.0, flutter: float = 0.0,
                   wag: float = 0.0, lift: float = 0.0) -> None:
        """Every chain by its kind (a flag flutters about its pole, a tassel or a cloth sways and trails back, an
        antenna springs) and the tail (wags `wag`, lifts `lift`)."""
        for m in CH:
            n = len(m['bones'])
            k = 1.0 - m['stiff']
            for i, b in enumerate(m['bones']):
                lag = 0.08 * i
                share = (0.6 + 0.8 * i / max(1, n - 1)) / n
                if m['kind'] == 'flag':
                    # flutters about its pole; `trail` swings it toward the back (+y) by its sideways reach
                    fr.r(b, 4 * share * k * A.wave(t - lag, rate * 2, 0.25), 0, (flutter * A.wave(t - lag, rate * 2) + trail * m['tx']) * share * k)
                elif m['kind'] in ('tassel', 'cloth'):
                    x = trail * share * k
                    # a hanging one swings back just enough to keep its tip (its bone line 3.5 cm up, so its skin) off
                    # the ground as the shell comes down or tips back
                    need = tip_need(fr, m['points'], mm(0.035)) if (i == 0 and m['hangs'] and m['parent'] == 'hips') else 0.0
                    if need > 0 and m['length'] > 1e-4:
                        x += math.degrees(math.acos(max(-1.0, 1.0 - min(2.0, need / m['length']))))
                    fr.r(b, x, 0, sway * share * k * A.wave(t - lag, rate))
                elif m['kind'] == 'antenna':
                    fr.r(b, 0.5 * sway * share * k * A.wave(t - lag, rate, 0.25), 0, sway * share * k * A.wave(t - lag, rate))
                else:
                    up = tail_lift(fr, m['points'], m['length']) if (i == 0 and m['parent'] == 'hips') else 0.0
                    fr.r(b, lift * share * k + up, 0, 1.6 * wag * share * k * A.wave(t - lag, rate))
        n = len(TAIL)
        for i, b in enumerate(TAIL):
            share = (0.6 + 0.8 * i / max(1, n - 1)) / n
            up = tail_lift(fr, TAIL_PTS, TAIL_LEN) if i == 0 else 0.0
            fr.r(b, lift * share + up, 0, 1.6 * wag * share * A.wave(t - 0.08 * i, rate))

    def tail_lift(fr: Frame, pts: list, length: float) -> float:
        """Degrees to lift a tail at its root so its bone line stays 3 cm up (its skin clear) when the shell sinks or
        tips back."""
        need = tip_need(fr, pts, mm(0.03))
        return math.degrees(math.asin(min(1.0, need / length))) if need > 0 and length > 1e-4 else 0.0

    def jaw(fr: Frame, deg_: float) -> None:
        if JAW:
            fr.r('jaw', deg_, 0, 0)

    def ko_lift(t: float) -> float:
        return K.table_at(lift_tab, t)

    def guard(fr: Frame, w: float = 1.0, t: float = 0.0, clack: float = 0.0) -> None:
        """The claws up in front (the big one higher), the pincers ajar, clacking `clack` degrees."""
        for tag in CL:
            big = tag == BIG
            claw(fr, tag, raise_=(32 if big else 20) * w, out=-6 * w, bend=(18 if big else 26) * w, wrist=6 * w,
                 open_=(12 + clack * A.bounce(t, 2)) * w)

    def rest_claws(fr: Frame, t: float, lift: float = 0.0, open_: float = 0.0, rate: float = 1.0) -> None:
        """The claws held at rest, breathing a little (+lift raises them)."""
        for tag in CL:
            claw(fr, tag, raise_=lift + 3 * A.wave(t, rate, 0.1 if tag == 'L' else 0.4), open_=open_)

    # ================================================================= ranch life
    def p_idle(t: float) -> Frame:
        fr = Frame()
        glance = A.pulse(t, 0.55, 0.85)
        body(fr, dz=-mm(0.004) * (0.5 + 0.5 * A.wave(t, 2.0)), roll=1.5 * A.wave(t, 1.0), yaw=3 * glance)
        feet(fr)
        look(fr, pitch=2 * A.wave(t, 1.0), yaw=20 * glance, tilt=4 * glance)
        tuck(fr, 0.0)
        stalk_pose(fr, t, sway=6, look_=25 * glance)
        rest_claws(fr, t)
        chain_pose(fr, t, flutter=14, sway=4, wag=6)
        jaw(fr, 0)
        return fr

    def p_idle_happy(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 3)
        body(fr, dz=-mm(0.015) * b, roll=5 * A.wave(t, 2.0), yaw=4 * A.wave(t, 1.0, 0.25))
        feet(fr)
        look(fr, pitch=-10 + 4 * A.wave(t, 3.0), tilt=8 * A.wave(t, 2.0), reach=0.15 * TD)
        tuck(fr, 0.0)
        stalk_pose(fr, t, sway=14, rate=3.0, spread=8)
        for tag in CL:
            claw(fr, tag, raise_=28 + 10 * A.wave(t, 3.0, 0.0 if tag == 'L' else 0.5), out=8, open_=25 * A.bounce(t, 6))
        chain_pose(fr, t, flutter=24, rate=3.0, sway=10, wag=18)
        jaw(fr, 12)
        return fr

    def p_idle_tired(t: float) -> Frame:
        fr = Frame()
        yawn = A.pulse(t, 0.45, 0.72)
        body(fr, dz=-0.45 * ROOM, pitch=3 - 4 * yawn)
        feet(fr, out=mm(0.01))
        look(fr, pitch=20 - 34 * yawn, yaw=-4)
        tuck(fr, 0.15)
        stalk_pose(fr, t, droop=30 - 30 * yawn, sway=3)
        rest_claws(fr, t, lift=-14 + 10 * yawn)
        chain_pose(fr, t, flutter=6, sway=3, wag=3, lift=-8)
        jaw(fr, 28 * yawn)
        return fr

    def p_idle_sad(t: float) -> Frame:
        fr = Frame()
        body(fr, dz=-0.4 * ROOM, pitch=4, yaw=-4)
        feet(fr)
        look(fr, pitch=24, yaw=-10 + 4 * A.pulse(t, 0.5, 0.7))
        tuck(fr, 0.35)
        stalk_pose(fr, t, droop=40, sway=3, spread=-4)
        rest_claws(fr, t, lift=-18)
        chain_pose(fr, t, flutter=4, sway=2, wag=2, lift=-10)
        jaw(fr, 0)
        return fr

    def p_idle_sick(t: float) -> Frame:
        fr = Frame()
        w = A.wave(t, 1.0)
        shiver = A.wave(t, 9.0) * A.pulse(t, 0.25, 0.5)
        body(fr, dz=-0.3 * ROOM, roll=5 * w + 1.5 * shiver, pitch=3)
        feet(fr, out=mm(0.008))
        look(fr, pitch=16, yaw=8 * w, tilt=6 * w)
        tuck(fr, 0.25)
        stalk_pose(fr, t, droop=26, sway=8)
        rest_claws(fr, t, lift=-10)
        chain_pose(fr, t, flutter=5, sway=4, wag=3, lift=-6)
        jaw(fr, 4)
        return fr

    def p_sleep(t: float) -> Frame:
        fr = Frame()
        b = A.wave(t, 2.0)
        body(fr, dz=-ROOM + mm(0.003) * (0.5 + 0.5 * b), pitch=2)
        feet(fr, tuck_=1.0)
        look(fr, pitch=12)
        tuck(fr, 1.0)
        stalk_pose(fr, t, sway=1)
        for tag in CL:
            claw(fr, tag, raise_=-22, out=-12, bend=45, open_=0)
        chain_pose(fr, t, flutter=3, sway=1, wag=0, lift=-10)
        jaw(fr, 0)
        return fr

    def p_eat(t: float) -> Frame:
        fr = Frame()
        dip = A.step_ease(t, 0.0, 0.2) * (1 - A.step_ease(t, 0.85, 1.0))
        chew = dip * abs(math.sin(t * 2 * math.pi * 3))
        body(fr, dz=-0.15 * ROOM * dip, pitch=6 * dip)
        feet(fr)
        look(fr, pitch=34 * dip + 4 * chew, reach=0.35 * TD * dip)
        tuck(fr, 0.0)
        stalk_pose(fr, t, droop=18 * dip, sway=4)
        if SMALL:
            claw(fr, SMALL, raise_=34 * dip, out=-24 * dip, bend=50 * dip, wrist=10 * chew, open_=18 * chew)
            claw(fr, BIG, raise_=6, out=6)
        chain_pose(fr, t, flutter=10, sway=4, wag=8)
        jaw(fr, 18 * chew)
        return fr

    def p_pet(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, dz=-mm(0.01) * b, roll=6, pitch=-2)
        feet(fr)
        look(fr, pitch=-14 + 3 * A.wave(t, 2.0), tilt=14, yaw=6, reach=0.2 * TD)
        tuck(fr, 0.0)
        stalk_pose(fr, t, sway=10, rate=2.0, spread=-8, droop=-6)
        rest_claws(fr, t, lift=-6, open_=8, rate=2.0)
        chain_pose(fr, t, flutter=16, rate=2.0, sway=8, wag=20)
        jaw(fr, 8)
        return fr

    def p_look(t: float) -> Frame:
        fr = Frame()
        a = A.step_ease(t, 0.08, 0.22) * (1 - A.step_ease(t, 0.42, 0.56))
        b = A.step_ease(t, 0.5, 0.64) * (1 - A.step_ease(t, 0.84, 0.98))
        yaw = 40 * a - 40 * b
        body(fr, yaw=0.15 * yaw)
        feet(fr)
        look(fr, yaw=0.85 * yaw, tilt=0.1 * yaw, reach=0.1 * TD)
        tuck(fr, 0.0)
        # a crab's stalks look one at a time (the left first), then together
        stalk_pose(fr, t, sway=4, look_=50 * a, solo='L')
        stalk_pose(fr, t, look_=-50 * b, solo='R')
        rest_claws(fr, t)
        chain_pose(fr, t, flutter=12, sway=4, wag=6)
        jaw(fr, 0)
        return fr

    def p_hop(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.28, 0.82)
        crouch = A.pulse(t, 0.0, 0.28) + 0.8 * A.pulse(t, 0.8, 1.0)
        up = mm(0.12) * float(P.get('hop', 1.0)) * air
        body(fr, dz=up - 0.3 * ROOM * crouch, pitch=-6 * air + 4 * crouch)
        feet(fr, lift=0.8 * up, tuck_=0.35 * air)
        look(fr, pitch=-10 * air + 6 * crouch)
        tuck(fr, 0.2 * crouch)
        stalk_pose(fr, t, droop=-12 * air + 10 * crouch, sway=4)
        for tag in CL:
            claw(fr, tag, raise_=30 * air - 8 * crouch, out=14 * air, open_=20 * air)
        chain_pose(fr, t, flutter=14, sway=6, trail=-12 * air, wag=10, lift=10 * air)
        jaw(fr, 10 * air)
        return fr

    def p_celebrate(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.05, 0.35) + A.pulse(t, 0.4, 0.7)
        land = A.pulse(t, 0.33, 0.42) + A.pulse(t, 0.68, 0.77)
        up = mm(0.1) * float(P.get('hop', 1.0)) * air
        body(fr, dz=up - 0.25 * ROOM * land, roll=6 * A.wave(t, 2.0), yaw=12 * A.wave(t, 1.0))
        feet(fr, lift=0.8 * up, tuck_=0.3 * air)
        look(fr, pitch=-16, tilt=10 * A.wave(t, 2.0), reach=0.2 * TD)
        tuck(fr, 0.0)
        stalk_pose(fr, t, sway=18, rate=3.0, spread=10)
        for tag in CL:
            claw(fr, tag, raise_=55 + 10 * A.wave(t, 3.0), out=20, open_=30 * A.bounce(t, 6))
        chain_pose(fr, t, flutter=30, rate=3.0, sway=12, wag=24, lift=10)
        jaw(fr, 18)
        return fr

    # ================================================================= moving: legged gaits, planted by IK
    def gait(t: float, kind: str, dirv: Vector, waddle: float = 1.0, lean: float = 0.0, guard_w: float = 0.0,
             rate: float = 1.0) -> Frame:
        """One cycle: a planted foot slides back under the body as the root carries it (at speed_of(kind)), a swinging
        foot lifts and reaches ahead; diagonal pairs (two legs a side) or alternating tripods (three); the shell
        bobs twice a cycle and rocks toward the planted side; the head nods with the steps."""
        n, _s, duty, lift_k = GAITS[kind]
        stride = stride_of(kind)
        fr = Frame()
        bob = mm(0.006) * (0.5 - 0.5 * math.cos(4 * math.pi * t))
        body(fr, dz=-DROP[kind] - bob, pitch=lean, roll=3.0 * waddle * math.sin(2 * math.pi * t),
             yaw=2.0 * waddle * math.sin(2 * math.pi * t))
        for lg in LEGS:
            p = (t + lg['phase']) % 1.0
            if p < duty:
                u = p / duty
                d = dirv * (stride * (0.5 - u))
                plant(fr, lg, d)
            else:
                u = (p - duty) / (1 - duty)
                d = dirv * (stride * (-0.5 + C.ease_in_out(u))) + Vector((0, 0, lift_k * lg['reach'] * math.sin(math.pi * u)))
                plant(fr, lg, d, pitch=-10 * math.sin(math.pi * u))
        look(fr, pitch=3 * math.sin(4 * math.pi * t) - 0.5 * lean, yaw=-3 * waddle * math.sin(2 * math.pi * t))
        tuck(fr, 0.0)
        stalk_pose(fr, t, droop=-4 * dirv.y, sway=6, rate=2.0 * rate)
        if guard_w:
            guard(fr, guard_w, t)
        else:
            rest_claws(fr, t, lift=6, rate=2.0)
        trail = 10 + 20 * (stride / max(LEG, 1e-4))
        chain_pose(fr, t, flutter=18, rate=2.0 * rate, sway=6, trail=trail if dirv.y < 0 else -0.5 * trail, wag=10)
        jaw(fr, 0)
        return fr

    def gait_marks(kind: str) -> list:
        n = GAITS[kind][0]
        return [('step', 1), ('step', 1 + n // 2)]

    def p_strafe(t: float, side: int) -> Frame:
        fr = gait(t, 'strafe', Vector((side, 0, 0)), waddle=0.6, guard_w=1.0)
        fr.r('hips', 0, side * 3, 0)
        return fr

    def p_sidestep(t: float, side: int) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.15, 0.92)
        crouch = A.pulse(t, 0.0, 0.3) + 0.7 * A.pulse(t, 0.82, 1.0)
        up = mm(0.06) * air
        body(fr, dz=up - 0.2 * ROOM * crouch, roll=side * 14 * air)
        feet(fr, lift=0.8 * up, tuck_=0.4 * air)
        look(fr, yaw=side * 6 * air)
        tuck(fr, 0.2 * air)
        stalk_pose(fr, t, sway=4, spread=-side * 10 * air)
        guard(fr, 1.0, t)
        chain_pose(fr, t, flutter=14, sway=-side * 12 * air, trail=8 * air, wag=8)
        jaw(fr, 0)
        return fr

    # ================================================================= scenes
    def settle_pose(fr: Frame, t: float, k: float) -> None:
        """The shell lowered onto its belly (k: 0 standing → 1 down), the legs splaying out to the sides."""
        body(fr, dz=-0.9 * ROOM * k, pitch=2 * k)
        feet(fr, out=mm(0.03) * k, spread=mm(0.015) * k)

    def p_sit_down(t: float) -> Frame:
        fr = Frame()
        k = C.ease_in_out(t)
        settle_pose(fr, t, k)
        look(fr, pitch=-6 * k)
        tuck(fr, 0.0)
        stalk_pose(fr, t, sway=3)
        for tag in CL:
            claw(fr, tag, raise_=-14 * k, out=-8 * k, bend=20 * k)
        chain_pose(fr, t, flutter=10, sway=3, wag=4, lift=-8 * k)
        jaw(fr, 0)
        return fr

    def p_sit(t: float) -> Frame:
        fr = Frame()
        settle_pose(fr, t, 1.0)
        fr.o('hips', 0, 0, mm(0.002) * (0.5 + 0.5 * A.wave(t, 2.0)))
        g = A.pulse(t, 0.5, 0.75)
        look(fr, pitch=-6 + 2 * A.wave(t, 1.0), yaw=16 * g)
        tuck(fr, 0.0)
        stalk_pose(fr, t, sway=4, look_=20 * g)
        for tag in CL:
            claw(fr, tag, raise_=-14, out=-8, bend=20)
        chain_pose(fr, t, flutter=10, sway=3, wag=4, lift=-8)
        jaw(fr, 0)
        return fr

    def p_dizzy(t: float) -> Frame:
        fr = Frame()
        c, s_ = math.cos(t * 4 * math.pi), math.sin(t * 4 * math.pi)
        body(fr, dz=-0.15 * ROOM, roll=7 * s_, pitch=5 * c, yaw=6 * s_)
        feet(fr, out=mm(0.015))
        look(fr, pitch=10 * c, yaw=18 * s_, tilt=14 * s_)
        tuck(fr, 0.0)
        stalk_pose(fr, t, droop=10 * c, sway=20, rate=2.0, spread=12 * s_)
        for tag in CL:
            claw(fr, tag, raise_=10 + 12 * (s_ if tag == 'L' else c), out=10, open_=14)
        chain_pose(fr, t, flutter=20, rate=2.0, sway=14, wag=14)
        jaw(fr, 10)
        return fr

    # ================================================================= battle
    def p_battle_idle(t: float) -> Frame:
        fr = Frame()
        b = A.bounce(t, 2)
        body(fr, dz=-0.15 * ROOM - mm(0.006) * b, pitch=4, yaw=-4)
        feet(fr, out=mm(0.01))
        look(fr, pitch=6 - 2 * b, reach=0.2 * TD)
        tuck(fr, 0.0)
        stalk_pose(fr, t, sway=5, rate=2.0, spread=6, visor=6)
        guard(fr, 1.0, t, clack=10)
        chain_pose(fr, t, flutter=16, rate=2.0, sway=6, wag=10)
        jaw(fr, 0)
        return fr

    def p_hit(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.8)
        body(fr, dy=mm(0.05) * k, dz=-0.1 * ROOM * k, pitch=-10 * k, roll=-4 * k, yaw=-6 * k)
        feet(fr, shift=Vector((0, 0.4 * mm(0.05) * k, 0)))
        look(fr, pitch=-8 * k, yaw=-10 * k)
        tuck(fr, 0.55 * k)
        stalk_pose(fr, t, sway=10, spread=10 * k)
        for tag in CL:
            claw(fr, tag, raise_=22 * k, out=20 * k, open_=20 * k)
        chain_pose(fr, t, flutter=20, sway=10, trail=-20 * k, wag=8)
        jaw(fr, 10 * k)
        K.add_bones(P, 'hit_bones', fr, k)
        return fr

    def p_hit_heavy(t: float) -> Frame:
        fr = Frame()
        k = A.pulse(t, 0.0, 0.62)
        up = mm(0.06) * k
        body(fr, dy=mm(0.14) * k, dz=up, pitch=-24 * k, roll=-20 * k, yaw=-10 * k)
        feet(fr, shift=Vector((0, 0.7 * mm(0.14) * k, 0.7 * up)), out=mm(0.04) * k)
        look(fr, pitch=-12 * k, yaw=-14 * k)
        tuck(fr, 0.7 * k)
        stalk_pose(fr, t, sway=16, spread=16 * k)
        for tag in CL:
            claw(fr, tag, raise_=36 * k, out=30 * k, open_=30 * k)
        hang = float(P.get('hit_heavy_chain_hang', 0.0))
        chain_pose(fr, t, flutter=26, sway=16, trail=-34 * k * (1.0 - 0.5 * hang), wag=12)
        if hang:
            for m in CH:
                if m['kind'] in ('tassel', 'cloth'):
                    fr.r(m['bones'][0], 45 * k * hang, 0, 0)
        jaw(fr, 16 * k)
        K.add_bones(P, 'hit_heavy_bones', fr, k)
        return fr

    def droop_toward_ground(fr: Frame, root_deg, amount: float, stalks: bool = True) -> None:
        """Let the neck and head (or a crab's stalks) sag `amount` degrees toward the ground of a turned body."""
        down = K.m3(root_deg).transposed() @ Vector((0, 0, -1))
        names = NECK + ['head'] if NECK else []
        if names:
            dvec = (head_tip(P) - neck_points(P)[0]).normalized()
            ax = dvec.cross(down)
            if ax.length > 1e-4:
                for nm in names:
                    fr.turn(nm, ax, amount / len(names))
        for tag, st in (ST.items() if stalks else ()):
            p = st['points']
            ax = (p[2] - p[0]).normalized().cross(down)
            if ax.length > 1e-4:
                fr.turn(st['bones'][0], ax, 0.7 * amount)

    def p_ko(t: float) -> Frame:
        """It wobbles, then rolls over `ko_roll` degrees onto its right side or its back (or, 'tuck', pulls everything
        in and drops onto its belly), lying `body_width` up (the build settles it), the legs folding, eyes shut."""
        fr = Frame()
        wob = (1 - A.step_ease(t, 0.3, 0.5)) * A.step_ease(t, 0.0, 0.1)
        fall = A.step_ease(t, 0.35, 0.85)
        bw = float(P.get('body_width', (HZ - ROOM) if kstyle == 'tuck' else 0.6 * HZ))
        h = HZ * (1 - fall) + bw * fall + ko_lift(t)
        if kstyle == 'tuck':
            rd = (3 * fall, 6 * math.sin(t * 2 * math.pi * 2.5) * wob, 0.0)
            fr.r('root', *rd)
            fr.o('hips', *K.lay_offset(rd, hip, Vector((0, hip.y, h))))
            feet(fr, tuck_=fall, lift=h - HZ)            # the tucked feet come down with the shell (the settle is 1:1)
            tuck(fr, fall)
            look(fr, pitch=10 * fall)
            stalk_pose(fr, t, sway=0)
            for tag in CL:
                claw(fr, tag, raise_=-24 * fall, out=-12 * fall, bend=48 * fall)
        else:
            rd = (0.0, 8 * math.sin(t * 2 * math.pi * 2.5) * wob - ko_roll * fall, 0.0)
            fr.r('root', *rd)
            fr.o('hips', *K.lay_offset(rd, hip, Vector((0, hip.y, h))))
            # on its back the legs kick a little, then go still
            kick = 14 * A.pulse(t, 0.7, 1.0) if ko_roll > 120 else 0.0
            fold_legs(fr, fall, splay=28, curl=42, wave=kick, t=t)
            tuck(fr, 0.3 * fall, stalks_k=fall)
            look(fr, pitch=0)
            droop_toward_ground(fr, rd, 35 * fall, stalks=ko_roll <= 120)
            stalk_pose(fr, t, sway=0)
            for tag in CL:
                claw(fr, tag, raise_=-10 * fall, out=18 * fall, bend=12 * fall, open_=16 * fall)
        hang = float(P.get('ko_chain_hang', 0.0))
        chain_pose(fr, t, flutter=8 * (1 - fall), sway=2, wag=0, lift=-10 * fall)
        if hang and kstyle != 'tuck':
            for m in CH:
                if m['kind'] in ('tassel', 'cloth'):
                    fr.r(m['bones'][0], 0, ko_roll * fall * hang, 0)
        jaw(fr, 12 * fall)
        K.add_bones(P, 'ko_bones', fr, fall)
        K.scale_bones(P, 'ko_scale', fr, A.step_ease(t, 0.3, 0.75))
        return fr

    def p_win(t: float) -> Frame:
        fr = Frame()
        air = A.pulse(t, 0.04, 0.34)
        land = A.pulse(t, 0.32, 0.42)
        proud = A.step_ease(t, 0.3, 0.45) * (1 - A.step_ease(t, 0.86, 1.0))     # back to the start: win loops
        up = mm(0.1) * float(P.get('hop', 1.0)) * air
        body(fr, dz=up - 0.25 * ROOM * land, roll=7 * A.wave(t, 2.0) * proud, pitch=-3 * proud)
        feet(fr, lift=0.8 * up, tuck_=0.3 * air)
        look(fr, pitch=-18 * proud - 8 * air, tilt=8 * A.wave(t, 2.0) * proud, reach=0.25 * TD * proud)
        tuck(fr, 0.0)
        stalk_pose(fr, t, sway=16, rate=3.0, spread=12, droop=-8)
        for tag in CL:
            claw(fr, tag, raise_=62 + 8 * A.wave(t, 3.0), out=24, open_=30 * A.bounce(t, 6))
        chain_pose(fr, t, flutter=32, rate=3.0, sway=12, wag=24, lift=12)
        jaw(fr, 20 * proud)
        K.add_bones(P, 'win_bones', fr, max(air, A.pulse(t, 0.42, 0.86)))
        K.scale_bones(P, 'win_scale', fr, air)
        return fr

    # ---- strike: 24 frames, impact at 13 (t = 0.5) in every style
    def p_strike(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.42)
        go = A.pulse(t, 0.28, 0.72)
        if style == 'bash':
            # draws back low with the head in, then rams the shell's front at the target, the feet skidding along
            dy = mm(0.05) * ant - 0.55 * LEG * go
            body(fr, dy=dy, dz=-0.25 * ROOM * ant, pitch=-4 * ant + 10 * go, yaw=strike_yaw * go)
            feet(fr, shift=Vector((0, 0.5 * dy, 0)))
            look(fr, pitch=6 * go)
            tuck(fr, 0.5 * ant + 0.6 * go)
            stalk_pose(fr, t, sway=4, droop=-6 * ant)
            guard(fr, 1.0 - 0.5 * go, t)
            chain_pose(fr, t, flutter=20, trail=24 * go - 8 * ant, sway=4, wag=8)
            jaw(fr, 0)
        elif style == 'bite':
            # coils the neck back with the mouth opening wide, then shoots the head out and snaps shut on the impact
            body(fr, dy=mm(0.02) * ant - mm(0.04) * go, pitch=-3 * ant + 6 * go, yaw=strike_yaw * go)
            feet(fr)
            look(fr, pitch=-14 * ant + 12 * go, reach=-0.4 * TD * ant + (0.45 * TD + mm(0.04)) * go)
            tuck(fr, 0.0)
            stalk_pose(fr, t, sway=4, droop=-10 * ant + 10 * go)
            guard(fr, 1.0, t)
            chain_pose(fr, t, flutter=20, trail=16 * go, sway=4, wag=8)
            jaw(fr, 34 * A.pulse(t, 0.16, 0.5))
        elif style == 'launch':
            # braces wide and low, the head half in and the shell tipped back so its top aims up the line; the volley
            # leaves socket_shell on the impact and the recoil rocks the shell back
            brace = A.step_ease(t, 0.0, 0.3) * (1 - A.step_ease(t, 0.75, 1.0))
            rec = A.pulse(t, 0.48, 0.7)
            body(fr, dy=mm(0.04) * rec, dz=-0.5 * ROOM * brace, pitch=float(P.get('launch_pitch', -6.0)) * brace - 7 * rec,
                 yaw=strike_yaw * brace)
            feet(fr, out=mm(0.03) * brace)
            look(fr, pitch=8 * brace - 6 * rec)
            tuck(fr, 0.7 * brace)
            stalk_pose(fr, t, sway=6, droop=-10 * rec)
            guard(fr, brace, t)
            chain_pose(fr, t, flutter=18 + 20 * rec, trail=-30 * rec, sway=6, wag=6)
            jaw(fr, 0)
        elif style == 'claw':
            # the big claw rears up and out, then sweeps across in front at the target, the body turning into it
            sb = CL[BIG]['s']
            arc = A.pulse(t, 0.3, 0.85)
            body(fr, dy=-mm(0.03) * go, pitch=5 * go, roll=sb * 4 * ant - sb * 5 * arc,
                 yaw=sb * 14 * ant - sb * 18 * arc + strike_yaw * go)
            feet(fr)
            look(fr, yaw=-sb * 8 * ant)
            tuck(fr, 0.0)
            stalk_pose(fr, t, sway=4, spread=6 * ant, look_=-sb * 14 * ant + sb * 10 * go)
            claw(fr, BIG, raise_=75 * ant + 6 * go, out=45 * ant - 42 * arc, bend=30 * arc - 10 * ant, wrist=-10 * arc,
                 open_=35 * ant + 10 * A.pulse(t, 0.3, 0.48))
            if SMALL:
                claw(fr, SMALL, raise_=20, out=-6, bend=28, open_=10)
            chain_pose(fr, t, flutter=20, trail=12 * go, sway=8, wag=8)
            jaw(fr, 10 * go)
        else:      # 'pinch'
            # both claws spread wide with the pincers open, then lunge in together and snap shut on the impact
            dy = -0.3 * LEG * go
            body(fr, dy=dy, dz=-0.1 * ROOM * ant, pitch=-4 * ant + 6 * go, yaw=strike_yaw * go)
            feet(fr, shift=Vector((0, 0.3 * dy, 0)))
            look(fr, pitch=-6 * ant + 4 * go)
            tuck(fr, 0.0)
            stalk_pose(fr, t, sway=4, droop=-8 * ant + 8 * go, spread=8 * ant)
            snap = A.pulse(t, 0.22, 0.48)
            claws_both(fr, raise_=30 * ant + 10 * go, out=25 * ant - 20 * go, bend=-15 * go, open_=40 * ant + 25 * snap)
            chain_pose(fr, t, flutter=20, trail=14 * go, sway=4, wag=8)
            jaw(fr, 8 * go)
        K.add_bones(P, 'strike_bones', fr, go)
        K.add_bones(P, 'strike_windup_bones', fr, ant)
        return fr

    def p_cast(t: float) -> Frame:
        fr = Frame()
        up = A.step_ease(t, 0.0, 0.3) * (1 - A.step_ease(t, 0.72, 1.0))
        rel = A.pulse(t, 0.48, 0.72)
        if cstyle == 'brace':
            # braces like the launch strike; the shot leaves socket_shell at `release` and the recoil rocks it
            body(fr, dy=mm(0.04) * rel, dz=-0.5 * ROOM * up, pitch=float(P.get('launch_pitch', -6.0)) * up - 7 * rel)
            feet(fr, out=mm(0.03) * up)
            look(fr, pitch=8 * up - 6 * rel)
            tuck(fr, 0.7 * up)
            stalk_pose(fr, t, sway=6, droop=-10 * rel)
            guard(fr, up, t)
            chain_pose(fr, t, flutter=18 + 20 * rel, trail=-30 * rel, sway=6, wag=6)
            jaw(fr, 0)
        else:
            # rises proud with the claws (or the head) raised, then thrusts them at the target at `release`
            body(fr, dz=-0.1 * ROOM * up, pitch=-4 * up + 8 * rel)
            feet(fr)
            look(fr, pitch=-26 * up + 20 * rel, reach=0.3 * TD * up)
            tuck(fr, 0.0)
            stalk_pose(fr, t, sway=8, rate=2.0, droop=-12 * up + 12 * rel, spread=10 * up)
            claws_both(fr, raise_=75 * up - 40 * rel, out=20 * up - 25 * rel, bend=-10 * rel, open_=40 * up - 30 * rel)
            chain_pose(fr, t, flutter=26, rate=2.0, trail=20 * rel, sway=8, wag=10)
            jaw(fr, 20 * up)
        return fr

    def p_shove(t: float) -> Frame:
        fr = Frame()
        ant = A.pulse(t, 0.0, 0.32)
        go = A.pulse(t, 0.2, 0.55)
        dy = mm(0.04) * ant - 0.4 * LEG * go
        body(fr, dy=dy, pitch=-5 * ant + 8 * go, yaw=strike_yaw * go)
        feet(fr, shift=Vector((0, 0.5 * dy, 0)))
        look(fr, pitch=4 * go)
        tuck(fr, 0.4 * go)
        stalk_pose(fr, t, sway=4, droop=-6 * ant)
        claws_both(fr, raise_=15 * go, out=-10 * go, bend=-20 * go, open_=10 * ant)
        chain_pose(fr, t, flutter=16, trail=18 * go, sway=4, wag=6)
        jaw(fr, 0)
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
    clip('walk', 30, lambda t: gait(t, 'walk', DIRS['walk']), root_speed=speed_of('walk'), markers=gait_marks('walk'))
    clip('run', 20, lambda t: gait(t, 'run', DIRS['run'], waddle=1.4, lean=4), root_speed=speed_of('run'), markers=gait_marks('run'))
    clip('sit_down', 24, p_sit_down, loop=False, hold=True)
    clip('sit', 120, p_sit, step=2)
    clip('dizzy', 60, p_dizzy, faces=[(1, 'dizzy')])
    clip('battle_idle', 40, p_battle_idle)
    clip('step_fwd', 24, lambda t: gait(t, 'step_fwd', DIRS['step_fwd'], waddle=0.6, guard_w=1.0),
         root_speed=speed_of('step_fwd'), markers=gait_marks('step_fwd'))
    clip('step_back', 24, lambda t: gait(t, 'step_back', DIRS['step_back'], waddle=0.6, guard_w=1.0),
         root_speed=speed_of('step_back'), markers=gait_marks('step_back'))
    clip('dash', 20, lambda t: gait(t, 'dash', DIRS['dash'], waddle=1.6, lean=7, rate=1.5), root_speed=speed_of('dash'),
         markers=gait_marks('dash'))
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
