"""Shared posing machinery for the shelled and blob plans (plans/shelled.py, plans/blob.py): not a plan itself (no
recipe selects it). The forward and two-bone inverse kinematics are the biped plan's (plans/biped.py keeps its own copy,
so nothing here changes an existing look), with a Frame that also carries whole-rotation matrices, scales and IK goals,
the per-clip knobs every plan offers (RECIPE.md "Per-clip knobs") and the ko's lie-down offset for any roll or pitch.

Conventions (lib.anim.ClipBuilder): rotations are world-aligned degrees relative to the parent at rest (+x tips an
upright bone forward, +z turns toward the monster's left (+X), +y tilts toward its left); offsets are world-aligned
metres in the parent's frame; scales are world-aligned.
"""
from __future__ import annotations

import math

from mathutils import Euler, Matrix, Quaternion, Vector

from lib import anim as A

I3 = Matrix.Identity(3)
SIDES = (('L', 1), ('R', -1))
SHUT_EXP = tuple(math.log(v) / math.log(0.5) for v in (0.3, 0.62, 0.08))


def m3(e) -> Matrix:
    """(x, y, z) world-aligned degrees (as ClipBuilder.rot keys them) → a rotation matrix."""
    return Euler((math.radians(e[0]), math.radians(e[1]), math.radians(e[2])), 'XYZ').to_matrix()


def deg(m: Matrix) -> tuple[float, float, float]:
    e = m.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def axis_m(axis, degrees: float) -> Matrix:
    a = Vector(axis)
    if a.length < 1e-9 or not degrees:
        return I3.copy()
    return Matrix.Rotation(math.radians(degrees), 3, a.normalized())


def mirror(p, s: int) -> Vector:
    v = Vector(p)
    return Vector((v.x * s, v.y, v.z))


def frames_of(n: int, step: int) -> list[int]:
    fs = list(range(1, n + 2, step))
    if fs[-1] != n + 1:
        fs.append(n + 1)
    return fs


def table_at(tab, t: float) -> float:
    """Linear interpolation in [[t, value], …] (a settle's ko_lift); 0 for an empty table."""
    if not tab:
        return 0.0
    for (t0, d0), (t1, d1) in zip(tab[:-1], tab[1:]):
        if t0 <= t <= t1:
            return d0 + (d1 - d0) * (t - t0) / max(t1 - t0, 1e-9)
    return tab[0][1] if t < tab[0][0] else tab[-1][1]


class Rig:
    """The armature's rest bones (armature space = model space) and forward kinematics matching how ClipBuilder keys
    them: M_b = M_parent · T(head_b + offset_b) · R_b · T(−head_b), R_b world-aligned at rest (scales ignored)."""

    def __init__(self, arm):
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
            M[b] = (M[p] if p else ident) @ Matrix.Translation(h + Vector(loc.get(b, (0.0, 0.0, 0.0)))) @ R @ Matrix.Translation(-h)
        return M

    def bend_hint(self, a: str, b: str, fallback: Vector) -> Vector:
        """The rest pose's bend direction of the joint between a and b, else `fallback` (an IK aimed at the rest spots
        reproduces the rest pose)."""
        h, k, e = self.head[a], self.head[b], self.tail[b]
        d = e - h
        if d.length < 1e-6:
            return fallback
        dn = d.normalized()
        perp = (k - h) - dn * (k - h).dot(dn)
        return perp.normalized() if perp.length > 0.02 * (k - h).length else fallback

    def two_bone(self, M: dict, a: str, b: str, c: str | None, target: Vector, hint: Vector, end_rot: Matrix | None = None,
                 w: float = 1.0) -> dict[str, Matrix]:
        """Rotations (world-aligned, relative to each parent) putting b's tip on `target` (or as near as the limb
        reaches), the middle joint bending toward `hint`; c (a foot) turned to the world rotation `end_rot` (None: it
        keeps its rest angle to b). w < 1 blends each rotation from the rest."""
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
    """One frame's pose: Euler rotations (degrees) and offsets (metres) added up per bone, whole rotations composed
    after them (`turn`, about any axis), scales, IK goals {(upper, lower, end): {'target', 'hint', 'end', 'w'}}, and
    `drop` (how far the body is below its rest this frame)."""

    def __init__(self):
        self.rot: dict[str, list[float]] = {}
        self.loc: dict[str, list[float]] = {}
        self.mat: dict[str, Matrix] = {}
        self.scl: dict[str, tuple[float, float, float]] = {}
        self.ik: dict[tuple, dict] = {}
        self.drop = 0.0

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

    def turn(self, bone: str, axis, degrees: float) -> Frame:
        """A rotation of `degrees` about a world-aligned `axis`, composed after everything given so far."""
        if degrees:
            self.mat[bone] = axis_m(axis, degrees) @ self.mat.get(bone, I3)
        return self

    def s(self, bone: str, x: float, y: float | None = None, z: float | None = None) -> Frame:
        """Multiply the bone's scale (uniform with one value)."""
        y = x if y is None else y
        z = x if z is None else z
        a = self.scl.get(bone, (1.0, 1.0, 1.0))
        self.scl[bone] = (a[0] * x, a[1] * y, a[2] * z)
        return self

    def rots(self) -> dict:
        out = {b: m3(v) for b, v in self.rot.items()}
        for b, m in self.mat.items():
            out[b] = m @ out.get(b, I3)
        return out


def resolve_goals(rig: Rig, fr: Frame) -> dict[str, Matrix]:
    """The frame's IK goals given in the root's space ({'root_target', 'rest_hint', 'hint_bone', 'pitch'}: a planted
    foot that moves with the root, its knee bending in its rest plane carried by `hint_bone`) turned into model-space
    goals, from one forward pass of the frame's own rotations and offsets. Returns that pass's matrices."""
    M = rig.fk(fr.rots(), fr.loc)
    Mr = M['root']
    Rr = Mr.to_3x3().normalized()
    for g in fr.ik.values():
        if 'root_target' in g:
            g['target'] = Mr @ g['root_target']
            hb = g.get('hint_bone')
            g['hint'] = (M[hb].to_3x3().normalized() @ g['rest_hint']) if hb in M else Vector(g['rest_hint'])
            if g.get('pitch') is not None:
                g['end'] = Rr @ axis_m((1, 0, 0), g['pitch'])
    return M


def key_frame(cb, rig: Rig, f: int, fr: Frame) -> None:
    """Solve the frame's IK goals and key every bone. The chains must be independent (no IK chain inside another's
    parents: legs and arms of one body), so every goal is solved from one forward pass."""
    rot = fr.rots()
    solved: dict[str, Matrix] = {}
    if fr.ik:
        M = resolve_goals(rig, fr)
        for chain, g in fr.ik.items():
            a, b, c = chain
            if not (rig.has(a) and rig.has(b)):
                continue
            res = rig.two_bone(M, a, b, c if (c and rig.has(c)) else None, g['target'], g['hint'], g.get('end'), g.get('w', 1.0))
            solved.update(res)
            rot.update(res)
    for b, v in fr.loc.items():
        if rig.has(b):
            cb.loc(b, f, *v)
    for b in set(fr.rot) | set(fr.mat) | set(solved):
        if not rig.has(b):
            continue
        if b in solved or b in fr.mat:
            cb.rot(b, f, *deg(rot[b]))
        else:
            cb.rot(b, f, *fr.rot[b])
    for b, v in fr.scl.items():
        if rig.has(b):
            cb.scale(b, f, *v)


def eyes_shut(cb, closed, frames: int, k, step: int = 1) -> None:
    """Squeeze the blink bones toward the recipe's BLINK_CLOSED by k(t), as every plan does."""
    if not closed:
        return
    for tag, _s in SIDES:
        pb = cb.arm.pose.bones.get(f'eye.{tag}')
        if pb is None:
            continue
        for f in frames_of(frames, step):
            kk = max(0.0, min(1.0, k((f - 1) / frames)))
            pb.scale = tuple(1.0 + (c - 1.0) * kk ** e for c, e in zip(closed, SHUT_EXP))
            pb.keyframe_insert('scale', frame=f)


# --------------------------------------------------------------------------- the per-clip knobs (RECIPE.md)
def clip_bump(P: dict, name: str, t: float, fr: Frame, sk: float) -> None:
    """`clip_bones` {clip: {bone: [(t0, t1, (x, y, z)[, (dx, dy, dz)])]}}: rotations (degrees) and offsets (metres ×
    size_k) added to a clip's own pose in a smooth bump from t0 to t1."""
    extra = (P.get('clip_bones') or {}).get(name)
    if not extra:
        return
    for b, items in extra.items():
        for it in items:
            k = A.pulse(t, it[0], it[1])
            fr.r(b, *(v * k for v in it[2]))
            if len(it) > 3:
                fr.o(b, *(v * sk * k for v in it[3]))


def add_bones(P: dict, key: str, fr: Frame, k: float) -> None:
    """A knob {bone: (x, y, z) degrees} added × k (ko_bones × the fall, hit_bones × the knock, strike_bones × the
    drive, strike_windup_bones × the wind-up, win_bones × the jump)."""
    if not k:
        return
    for b, v in (P.get(key) or {}).items():
        fr.r(b, *(a * k for a in v))


def scale_bones(P: dict, key: str, fr: Frame, k: float) -> None:
    """A knob {bone: s}: each bone scaled toward s by k (ko_scale with the fall, win_scale with the jump)."""
    for b, sc in (P.get(key) or {}).items():
        v = 1.0 + (float(sc) - 1.0) * k
        fr.s(b, v)


def lay_offset(root_deg, head: Vector, final: Vector) -> Vector:
    """The offset (in the rotated root's frame) that puts a child of the root whose rest head is `head` at `final`
    (model space) while the root is turned by `root_deg` (x, y, z): the ko's lie-down for any roll or pitch."""
    R = m3(root_deg)
    return R.transposed() @ final - head
