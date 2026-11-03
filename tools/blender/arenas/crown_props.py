"""The Crown Amphitheatre's statues, urns and braziers.

Statues: our own Puddlepup (public/models/monsters/puddlepup.glb, the Art 2.0 look: smooth, no fur cards) posed
from its own clips and turned to stone: sitting guardians in weathered marble flanking each gate, a cheering pair in
old bronze flanking the Patrons' box, each on a moulded plinth. Urns: terracotta, on the podium's parapet and the
gatehouse cornices. Braziers: an iron tripod, a bronze bowl and a fire of three flame tongues (emission).
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Matrix

from lib import common as C
import kit as K
from crown_geo import MB, box, frame, lathe, perimeter, pt, t_at_arc
import crown_layout as L
from crown_gates import BOX_FRONT, FRONT_D

PUDDLEPUP = C.ROOT / 'public' / 'models' / 'monsters' / 'puddlepup.glb'
URN = [(0.0, 0.0), (0.17, 0.0), (0.19, 0.05), (0.11, 0.12), (0.15, 0.2), (0.29, 0.4), (0.27, 0.6), (0.15, 0.73),
       (0.19, 0.8), (0.23, 0.86), (0.2, 0.9)]


def statue_spots() -> list[dict]:
    """Where the statues stand (Blender frame): plinth centre, the yaw they face, pose, material, scale."""
    out = []
    for tag in ('A', 'B'):
        P = frame(L.GATE_T[tag])
        for sx in (-1, 1):
            x, y, _ = P(sx * 5.1, FRONT_D - 3.9, 0.0)
            cx, cy, _ = P(0.0, FRONT_D - 14.0, 0.0)
            out.append(dict(p=(x, y), face=math.atan2(cy - y, cx - x), pose='sit', frame=0.6, mat='marble', scale=2.05, mirror=sx > 0))
    P = frame(L.BOX_T)
    for sx in (-1, 1):
        x, y, _ = P(sx * 10.6, BOX_FRONT - 0.9, 0.0)
        out.append(dict(p=(x, y), face=math.atan2(-y, -x * 0.3), pose='sit', frame=0.5, mat='bronze', scale=1.95, mirror=sx > 0))
    return out


def _posed_mesh(staging, clip: str, frac: float) -> bpy.types.Mesh:
    """The Puddlepup body posed at `frac` of `clip`, as a plain mesh (rest height 1 m, feet at z = 0)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(PUDDLEPUP))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        staging.objects.link(o)
    arm = next(o for o in new if o.type == 'ARMATURE')
    body = next(o for o in new if o.type == 'MESH' and o.data.name.startswith('puddlepup') and o.find_armature() is not None)
    act = next(a for a in bpy.data.actions if a.name.split('_')[0] == clip or a.name == clip or a.name.startswith(clip + '_'))
    ad = arm.animation_data or arm.animation_data_create()
    for tr in ad.nla_tracks:
        tr.mute = True
    ad.action = act
    if hasattr(ad, 'action_slot') and len(act.slots):
        ad.action_slot = act.slots[0]
    f0, f1 = act.frame_range
    sc = bpy.context.scene
    sc.frame_set(int(round(f0 + (f1 - f0) * frac)))
    me = C.evaluated_mesh(body)
    me.transform(body.matrix_world)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return me


def build_statues(coll, mats: dict, tris: int = 2600, lite: bool = False) -> list[bpy.types.Object]:
    staging = C.collection('STATUE_staging')
    cache: dict = {}
    out = []
    for i, s in enumerate(statue_spots()):
        key = (s['pose'], s['frame'])
        if key not in cache:
            cache[key] = _posed_mesh(staging, s['pose'], s['frame'])
        me = cache[key].copy()
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        mn = co.min(0)
        x, y = s['p']
        top = 1.75
        # the model faces -Y in Blender (glTF +Z): turn it to face s['face']
        m = (Matrix.Translation((x, y, top)) @ Matrix.Rotation(s['face'] + math.pi / 2, 4, 'Z') @ Matrix.Scale(s['scale'], 4)
             @ (Matrix.Scale(-1, 4, (1, 0, 0)) if s['mirror'] else Matrix.Identity(4))
             @ Matrix.Translation((-(co[:, 0].min() + co[:, 0].max()) / 2, -(co[:, 1].min() + co[:, 1].max()) / 2, -mn[2])))
        me.transform(m)
        if s['mirror']:
            me.flip_normals()
        for layer in list(me.uv_layers):
            me.uv_layers.remove(layer)
        for a in [a.name for a in me.color_attributes]:
            me.color_attributes.remove(me.color_attributes[a])
        ob = bpy.data.objects.new(f'statue_{i}' + ('_lite' if lite else ''), me)
        coll.objects.link(ob)
        me.materials.clear()
        me.materials.append(mats[s['mat']])
        K.decimate_to(ob, tris)
        ob.data.polygons.foreach_set('use_smooth', np.ones(len(ob.data.polygons), bool))
        ob.data.uv_layers.new(name='UVMap')
        a = ob.data.attributes.new('lite', 'INT', 'FACE')
        a.data.foreach_set('value', np.full(len(ob.data.polygons), int(lite), np.int32))
        out.append(ob)
    bpy.data.collections.remove(staging)
    return out


def plinths(mats: dict) -> MB:
    mb = MB()
    for s in statue_spots():
        x, y = s['p']
        yaw = s['face']
        for (w, z0, z1, m) in ((1.95, 0.0, 0.32, 'trim'), (1.62, 0.32, 1.5, 'face'), (1.9, 1.5, 1.75, 'trim')):
            box(mb, (x, y, (z0 + z1) / 2), (w, w, z1 - z0), mats[m], {'lite': 1}, yaw=yaw, skip=('bottom',))
    return mb


def urn_spots() -> list[tuple[float, float, float]]:
    out = []
    P0 = perimeter(0.22)
    n = 22
    for k in range(n):
        t = float(t_at_arc(0.22, P0 * (k + 0.5) / n))
        if L.zone(t) is None and all(abs(L.arc_dist(t, ta)) > 2.0 for ta in L.aisle_ts(0)):
            x, y, _ = pt(t, 0.22, 0.0)
            out.append((x, y, L.PODIUM_H + L.PARAPET[2]))
    for tag in ('A', 'B'):
        P = frame(L.GATE_T[tag])
        for sx in (-1, 1):
            x, y, _ = P(sx * 6.9, FRONT_D + 0.1, 0.0)
            out.append((x, y, 13.4))
    return out


def urns(mats: dict) -> MB:
    mb = MB()
    for (x, y, z) in urn_spots():
        lathe(mb, URN, 8, (x, y, z), mats['terracotta'], {'lite': 0})
    return mb


def brazier_spots() -> list[tuple[float, float]]:
    out = []
    for tag in ('A', 'B'):
        P = frame(L.GATE_T[tag])
        for sx in (-1, 1):
            x, y, _ = P(sx * 4.4, FRONT_D - 6.9, 0.0)
            out.append((x, y))
    P = frame(L.BOX_T)
    for sx in (-1, 1):
        x, y, _ = P(sx * 8.7, BOX_FRONT - 0.9, 0.0)
        out.append((x, y))
    return out


def braziers(mats: dict) -> MB:
    mb = MB()
    for i, (x, y) in enumerate(brazier_spots()):
        h = 1.25
        for k in range(3):
            a = 2 * math.pi * k / 3 + i
            fx, fy = x + 0.42 * math.cos(a), y + 0.42 * math.sin(a)
            tx, ty = x + 0.16 * math.cos(a), y + 0.16 * math.sin(a)
            _leg(mb, (fx, fy, 0.0), (tx, ty, h), mats['iron'])
        lathe(mb, [(0.06, h - 0.06), (0.3, h + 0.02), (0.4, h + 0.22), (0.43, h + 0.3), (0.36, h + 0.28)], 9, (x, y, 0.0), mats['bronze'], {'lite': 1}, cap=True)
        for k, (dx, dy, s) in enumerate(((0.0, 0.0, 1.0), (0.15, 0.07, 0.62), (-0.12, -0.12, 0.7), (-0.08, 0.16, 0.5), (0.12, -0.15, 0.45))):
            fl = [(0.0, 0.0), (0.17 * s, 0.07 * s), (0.17 * s, 0.25 * s), (0.1 * s, 0.5 * s), (0.04 * s, 0.75 * s), (0.0, 0.95 * s)]
            lathe(mb, fl, 6, (x + dx, y + dy, h + 0.18), mats['flame'], {'lite': 1}, cap=False, squash=(1.0, 0.7))
    return mb


def _leg(mb: MB, p0, p1, mat: int, r: float = 0.035) -> None:
    p0, p1 = np.asarray(p0), np.asarray(p1)
    d = p1 - p0
    s = np.cross(d, [0, 0, 1.0])
    s = s / np.linalg.norm(s) * r
    u = np.cross(s, d)
    u = u / np.linalg.norm(u) * r
    ring = [s, u, -s, -u, s]
    Ln = float(np.linalg.norm(d))
    for k in range(4):
        mb.quad([p0 + ring[k + 1], p0 + ring[k], p1 + ring[k], p1 + ring[k + 1]], [(r, 0), (0, 0), (0, Ln), (r, Ln)], mat, {'lite': 1})
