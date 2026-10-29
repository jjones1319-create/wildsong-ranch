"""Clip authoring (Blender 5.2): one Action per clip, pushed to its own NLA track; metadata for the sidecar JSON.

Rotations are keyed in world-aligned axes relative to the parent's frame (X = pitch/nod, Y = roll, Z = yaw),
converted to each bone's local frame through its rest matrix, so clip generators read like animation notes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

from . import common as C
from . import rig as R

FPS = 30


@dataclass
class ClipMeta:
    name: str
    frames: int
    loop: bool = True
    hold: bool = False
    root_speed: float = 0.0          # metres per second the clip "means" to travel (runtime moves the root)
    markers: list[tuple[str, int]] = field(default_factory=list)
    faces: list[tuple[int, str]] = field(default_factory=list)
    action: object = None

    @property
    def seconds(self) -> float:
        return self.frames / FPS

    def to_json(self) -> dict:
        return {
            'loop': self.loop,
            'hold': self.hold,
            'seconds': round(self.seconds, 4),
            'rootSpeed': round(self.root_speed, 4),
            'markers': [{'name': n, 't': round(f / FPS, 4)} for n, f in self.markers],
            'faces': [{'t': round(f / FPS, 4), 'face': n} for f, n in self.faces],
        }


class ClipBuilder:
    """Author clips as keys on pose bones. Usage: begin(); rot()/loc()/scale(); marker(); end()."""

    def __init__(self, arm: bpy.types.Object, deform_bones: list[str]):
        self.arm = arm
        self.deform = deform_bones
        self.clips: list[ClipMeta] = []
        self.meta: ClipMeta | None = None
        self._rest: dict[str, Matrix] = {n: R.rest_matrix(arm, n) for n in [b.name for b in arm.data.bones]}
        self._rest_inv: dict[str, Matrix] = {n: m.inverted() for n, m in self._rest.items()}
        ad = arm.animation_data or arm.animation_data_create()
        self.ad = ad

    # --------------------------------------------------------------- lifecycle
    def begin(self, name: str, frames: int, loop: bool = True, hold: bool = False, root_speed: float = 0.0) -> ClipMeta:
        R.reset_pose(self.arm)
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        self.ad.action = act
        if hasattr(act, 'slots'):
            slot = act.slots.new(id_type='OBJECT', name=self.arm.name)
            self.ad.action_slot = slot
        self.meta = ClipMeta(name=name, frames=frames, loop=loop, hold=hold, root_speed=root_speed, action=act)
        # Only what a clip really moves is keyed: the exporter drops unchanged channels, and three's mixer puts a
        # bone back to its rest pose when no clip animates it, so the files stay small and nothing leaks.
        return self.meta

    def end(self) -> ClipMeta:
        assert self.meta is not None
        m = self.meta
        act = m.action
        if m.loop:
            # a seamless loop: copy frame-1 keys to the last frame for every keyed channel
            self._close_loop(act, 1, 1 + m.frames)
        act.use_frame_range = True
        act.frame_start = 1
        act.frame_end = 1 + m.frames
        # bezier with auto-clamped handles reads as natural ease; the exporter samples it anyway
        for fc in action_fcurves(act):
            for k in fc.keyframe_points:
                k.interpolation = 'BEZIER'
                k.handle_left_type = 'AUTO_CLAMPED'
                k.handle_right_type = 'AUTO_CLAMPED'
        # push to its own NLA track
        track = self.ad.nla_tracks.new()
        track.name = m.name
        strip = track.strips.new(m.name, 1, act)
        strip.name = m.name
        try:
            if hasattr(act, 'slots') and act.slots:
                strip.action_slot = act.slots[0]
        except Exception:  # noqa: BLE001
            pass
        self.ad.action = None
        R.reset_pose(self.arm)
        self.clips.append(m)
        self.meta = None
        C.log(f'clip {m.name}: {m.frames}f ({m.seconds:.2f}s){" loop" if m.loop else ""}{" hold" if m.hold else ""}'
              + (f' speed {m.root_speed:.2f}' if m.root_speed else '') + (f' markers {m.markers}' if m.markers else ''))
        return m

    def _close_loop(self, act, f0: int, f1: int) -> None:
        for fc in action_fcurves(act):
            v = fc.evaluate(f0)
            fc.keyframe_points.insert(f1, v, options={'REPLACE'})

    # --------------------------------------------------------------- keys
    def _pb(self, bone: str):
        return self.arm.pose.bones[bone]

    def rot(self, bone: str, frame: int, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        """Key a rotation given as world-aligned XYZ degrees (applied in the parent's frame)."""
        rw = Euler((math.radians(x), math.radians(y), math.radians(z)), 'XYZ').to_matrix()
        local = self._rest_inv[bone] @ rw @ self._rest[bone]
        pb = self._pb(bone)
        pb.rotation_quaternion = local.to_quaternion()
        pb.keyframe_insert('rotation_quaternion', frame=frame)

    def rotq(self, bone: str, frame: int, q: Quaternion) -> None:
        pb = self._pb(bone)
        pb.rotation_quaternion = q
        pb.keyframe_insert('rotation_quaternion', frame=frame)

    def loc(self, bone: str, frame: int, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        """Key a translation in world-aligned metres."""
        d = self._rest_inv[bone] @ Vector((x, y, z))
        pb = self._pb(bone)
        pb.location = d
        pb.keyframe_insert('location', frame=frame)

    def scale(self, bone: str, frame: int, x: float = 1.0, y: float = 1.0, z: float = 1.0) -> None:
        """Key a scale given in world-aligned axes (mapped through the bone's rest axes)."""
        inv = self._rest_inv[bone]
        ws = (x, y, z)
        ls = []
        for i in range(3):
            ls.append(sum(abs(inv[i][j]) * ws[j] for j in range(3)))
        pb = self._pb(bone)
        pb.scale = ls
        pb.keyframe_insert('scale', frame=frame)

    def marker(self, name: str, frame: int) -> None:
        assert self.meta is not None
        self.meta.markers.append((name, frame))

    def face(self, frame: int, name: str) -> None:
        assert self.meta is not None
        self.meta.faces.append((frame, name))

    # --------------------------------------------------------------- curves
    def curve_rot(self, bone: str, keys: list[tuple[int, tuple[float, float, float]]]) -> None:
        for f, (x, y, z) in keys:
            self.rot(bone, f, x, y, z)

    def curve_loc(self, bone: str, keys: list[tuple[int, tuple[float, float, float]]]) -> None:
        for f, (x, y, z) in keys:
            self.loc(bone, f, x, y, z)

    def curve_scale(self, bone: str, keys: list[tuple[int, tuple[float, float, float]]]) -> None:
        for f, (x, y, z) in keys:
            self.scale(bone, f, x, y, z)

    def sample(self, bone: str, frames: int, fn, kind: str = 'rot', step: int = 1) -> None:
        """Key `fn(t)` (t in 0..1 over the clip) every `step` frames; fn returns an (x, y, z) tuple."""
        f = 1
        while f <= 1 + frames:
            t = (f - 1) / frames
            v = fn(t)
            if kind == 'rot':
                self.rot(bone, f, *v)
            elif kind == 'loc':
                self.loc(bone, f, *v)
            else:
                self.scale(bone, f, *v)
            f += step
        if (1 + frames - 1) % step != 0:
            v = fn(1.0)
            if kind == 'rot':
                self.rot(bone, 1 + frames, *v)
            elif kind == 'loc':
                self.loc(bone, 1 + frames, *v)
            else:
                self.scale(bone, 1 + frames, *v)


def action_fcurves(act) -> list:
    """The F-curves of an action: Blender 5 keeps them in the slot's channel bag (4.x had `action.fcurves`)."""
    if hasattr(act, 'fcurves'):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for slot in act.slots:
                try:
                    bag = strip.channelbag(slot, ensure=False)
                except TypeError:
                    bag = strip.channelbag(slot)
                if bag is not None:
                    out.extend(bag.fcurves)
    return out


def set_clip(arm: bpy.types.Object, meta: ClipMeta) -> None:
    """Make a clip the active action (for review renders)."""
    ad = arm.animation_data
    for t in ad.nla_tracks:
        t.mute = True
    ad.action = meta.action
    if hasattr(meta.action, 'slots') and meta.action.slots:
        ad.action_slot = meta.action.slots[0]


def clear_clip(arm: bpy.types.Object) -> None:
    ad = arm.animation_data
    ad.action = None
    for t in ad.nla_tracks:
        t.mute = False
    R.reset_pose(arm)


# --------------------------------------------------------------------------- motion helpers
def bounce(t: float, n: int = 1) -> float:
    """|sin| bounce, n bounces over 0..1."""
    return abs(math.sin(t * math.pi * n))


def wave(t: float, n: float = 1.0, phase: float = 0.0) -> float:
    return math.sin((t * n + phase) * 2 * math.pi)


def pulse(t: float, start: float, end: float) -> float:
    """A smooth in-out bump between start and end (0 outside)."""
    if t <= start or t >= end:
        return 0.0
    u = (t - start) / (end - start)
    return math.sin(u * math.pi)


def step_ease(t: float, start: float, end: float) -> float:
    """0 before start, 1 after end, smooth in between."""
    if t <= start:
        return 0.0
    if t >= end:
        return 1.0
    return C.ease_in_out((t - start) / (end - start))


def leg_ik(hip: Vector, foot: Vector, l1: float, l2: float, forward: Vector) -> tuple[float, float]:
    """Two-bone IK in the sagittal plane: returns (thigh pitch, knee pitch) in degrees, bending the knee
    backward (like a dog's hind leg) when `forward` points the way the animal faces."""
    d = foot - hip
    L = max(1e-4, min(d.length, l1 + l2 - 1e-4))
    # angle of the hip→foot line from straight down, positive toward `forward`
    down = Vector((0, 0, -1))
    dn = d.normalized()
    ang = math.degrees(math.atan2(dn.dot(forward.normalized()), -dn.z))
    # law of cosines
    a = math.degrees(math.acos(max(-1.0, min(1.0, (l1 * l1 + L * L - l2 * l2) / (2 * l1 * L)))))
    b = math.degrees(math.acos(max(-1.0, min(1.0, (l1 * l1 + l2 * l2 - L * L) / (2 * l1 * l2)))))
    thigh = ang + a          # thigh swings forward of the line by `a`
    knee = -(180.0 - b)      # knee bends back
    return thigh, knee
