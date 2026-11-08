"""Hearthwing at Art 2.1 Ultra: everything the young and the grown recipe share, driven by a form's numbers.

hearthwing_ultra.py (young) and hearthwing_grown_ultra.py (grown) each build a `Form(G)` from their own geometry dict
and export its methods as the recipe contract's names (`export(form, globals())`; RECIPE.md). The two forms are the same
creature (chatgpt/monsters/09-hearthwing): a teal scaled dragon with a cream front, big gold eyes, a wide smile, copper
horns and claws, an orange frill behind each cheek (membranes on the ear bones, with spine props), wings (a teal arm,
orange-brown fingers, a veined orange membrane, a copper wrist claw), orange-tipped spikes from the crown to the tail,
an orange glowing spade on the tail, and a glow in the chest (young: a faint warm heart; grown: a fireplace grate).

Coat without fur (RECIPE.md "Coats without fur"): leaf scales laid like shingles (hearthwing_parts.shingle_field) on
the high body, baked into the normal map and AO; soft chevron bands down the cream chest; the glow in the ORM alpha.
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from lib.mesh import Part
from lib.nodes import NB, new_mat
from lib.surface import ell_soft, in_ellipsoid, norm, smooth, tangent, v3
from monsters.breeds import hearthwing_parts as HP

lin = HP.lin
LEG_INDEX = {'FL': 0, 'FR': 1, 'BL': 2, 'BR': 3}
NOSE_HEX = '#1A4D49'
MOUTH_HEX = '#3A2224'
LASH_HEX = '#16110F'
# prop kinds (attribute pkind): the build joins every prop into lo_props and prop_weight_regions skins them by kind
P_HORN, P_CLAW, P_ARM, P_FINGER, P_WCLAW, P_SPINE = 0, 1, 2, 3, 4, 5


def colours(pal: dict) -> dict:
    teal, cream, orange = pal['body'], pal['belly'], pal['accent']
    copper = pal.get('horn', '#B87333')
    return {
        'teal': teal, 'cream': cream, 'orange': orange, 'copper': copper,
        # darks stay deep teal (never grey or green-black): the scales' outlines and the shaded gaps
        'rim': C.mix_hex(C.shade_hex(teal, 0.5, cool=0.03), '#08474A', 0.4),
        'root': C.mix_hex(C.shade_hex(teal, 0.72, cool=0.02), '#0D5A5A', 0.3),
        'sheen': C.mix_hex(teal, '#4FB8AA', 0.3),
        'teal_lo': C.shade_hex(teal, 0.82, cool=0.01),
        'cream_base': C.mix_hex(cream, '#D2B07A', 0.34),
        'cream_rim': C.mix_hex(cream, '#A86E38', 0.62),
        'cream_hi': C.mix_hex(cream, '#FFF1D0', 0.3),
        'blush': C.mix_hex('#F2895E', cream, 0.2),
        'brow': '#173030',
        'spike_mid': C.mix_hex(teal, orange, 0.5),
        'spike_tip': C.mix_hex(orange, '#E8601A', 0.4),
        'glow_core': pal.get('eye', '#FFD166'),
        'glow_warm': C.mix_hex(orange, '#FF9A28', 0.2),
        'glow_seam': '#FFC24A',
        'membrane': orange,
        'membrane_lite': C.mix_hex(orange, '#FFA640', 0.45),
        'membrane_dark': C.mix_hex(orange, '#B03A0A', 0.55),
        'ember': '#FFC04A',
        'rib': C.mix_hex(orange, '#8E3510', 0.6),
        'finger': C.mix_hex(orange, '#94420F', 0.5),
        'copper': copper,
        'copper_base': C.mix_hex(copper, '#6A300E', 0.32),
        'copper_dark': C.mix_hex(copper, '#3E1C08', 0.55),
        'copper_lite': C.mix_hex(copper, '#E8A060', 0.4),
    }


class Form:
    """One form of Hearthwing from its geometry dict G (hearthwing_ultra.G_YOUNG, hearthwing_grown_ultra.G_GROWN)."""

    def __init__(self, G: dict, palette: dict):
        self.G = G
        self.pal = palette
        self.head_c = Vector(G['head_c'])
        self.head_r = tuple(G['head_r'])
        e = G['eye']
        self.eye_r = e['r']
        self.eye_shape = tuple(e['shape'])
        self.eye_depth = tuple(e['depth'])
        self.eye_c = {s: Vector((e['x'] * s, self.on_head(e['x'], e['z'], e['out']), e['z'])) for s in (1, -1)}
        self.nose_c = Vector(G['nose_c'])
        self.legs = G['legs']
        self.tail_curve = HP.catmull(G['tail']['pts'], 10)
        self._spikes: list = []
        self._plates: dict = {}
        self.wings = G['wings']

    # ------------------------------------------------------------------------- the head and the eyes
    def on_head(self, x: float, z: float, out: float = 0.0) -> float:
        """y of the skull's front surface at (x, z), pushed `out` metres forward."""
        hc, hr = self.head_c, self.head_r
        k = 1.0 - (x / hr[0]) ** 2 - ((z - hc.z) / hr[2]) ** 2
        return hc.y - hr[1] * math.sqrt(max(k, 0.0)) - out

    def eye_frame(self, s: int):
        c = self.eye_c[s]
        hc, hr = self.head_c, self.head_r
        surf_n = Vector(((c.x - hc.x) / hr[0] ** 2, (c.y - hc.y) / hr[1] ** 2, (c.z - hc.z) / hr[2] ** 2)).normalized()
        fwd = self.G['eye'].get('fwd', 0.45)
        look = (surf_n * (1 - fwd) + Vector((0, -1, 0)) * fwd).normalized()
        look = (look + Vector((0, 0, 0.03))).normalized()
        xax = Vector((0, 0, 1)).cross(look).normalized()
        yax = look.cross(xax).normalized()
        return c, xax, yax, look

    def eye_matrix(self, s: int) -> Matrix:
        c, xax, yax, look = self.eye_frame(s)
        m = Matrix((xax, yax, look)).transposed().to_4x4()
        return Matrix.Translation(c - look * (self.eye_r * self.eye_depth[1])) @ m

    def blink_pivot(self, s: int):
        lash, drop, _w = self.G['lid']
        c, _xax, yax, look = self.eye_frame(s)
        return c - yax * (self.eye_r * (lash + 0.5 * drop)) - look * (self.eye_r * 0.6), yax, look

    def build_eye(self, name: str, s: int, high: bool) -> bpy.types.Object:
        bm = bmesh.new()
        seg = 48 if high else 24
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
        back = [v for v in bm.verts if v.co.z < -0.35]
        bmesh.ops.delete(bm, geom=back, context='VERTS')
        sx, sy, sz = self.eye_r * self.eye_shape[0], self.eye_r * self.eye_shape[1], self.eye_r * self.eye_depth[0]
        for v in bm.verts:
            v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.shade_smooth()
        ob = bpy.data.objects.new(name, me)
        C.link_obj(ob)
        ob.matrix_world = self.eye_matrix(s)
        co = np.array([v.co[:] for v in me.vertices])
        S.add_attr(ob, 'eyeuv', co / v3((sx, sy, sz)))
        S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
        return ob

    def eye_material(self, name: str, rough_pass: bool = False) -> bpy.types.Material:
        e = self.G['eye']
        return HP.eye_material_nodes(name, rough_pass, self.pal['eye'], iris_r=e.get('iris', 0.8), pupil_r=e.get('pupil', 0.48),
                                     iris_shift=tuple(e.get('shift', (0.06, 0.04))))

    # ------------------------------------------------------------------------- legs and tail
    def toe_centres(self, leg: str) -> list[np.ndarray]:
        x, y = self.legs[leg]
        L = self.G['leg']
        k = L['paw_k'][leg[0]]
        t = L['toe']
        return [v3((x + dx * k, y - (t['dy'] - abs(dx) * t['dyk']) * k, t['z'] * k)) for dx in L['toe_dx']]

    def claw_root(self, leg: str, i: int) -> np.ndarray:
        L = self.G['leg']
        k = L['paw_k'][leg[0]]
        return self.toe_centres(leg)[i] + v3((L['toe_dx'][i] * 0.12, -L['toe']['r'] * 0.75 * k, -L['toe']['r'] * 0.1 * k))

    def tail_radius(self, t):
        rad = self.G['tail']['rad']
        return np.interp(np.asarray(t, float), np.linspace(0.0, 1.0, len(rad)), rad)

    def tail_param(self, p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        t, _ = U.polyline_param(p, self.tail_curve)
        q = HP.curve_at(self.tail_curve, np.clip(t, 0, 1))
        return t, np.linalg.norm(p - q, axis=1)

    def tail_points(self) -> list[tuple[float, float, float]]:
        sp = self.G['spade']
        pts = HP.resample(self.tail_curve, 200)
        full = np.concatenate([pts, [v3(sp['base']) * 0.4 + v3(sp['tip']) * 0.6]])
        return [tuple(map(float, q)) for q in HP.resample(full, self.G['tail']['bones'] + 1)]

    # ------------------------------------------------------------------------- body parts
    def leg_parts(self, leg: str) -> list[Part]:
        x, y = self.legs[leg]
        L = self.G['leg']
        f = leg[0]
        k = L['paw_k'][f]
        sx = 1 if x > 0 else -1
        ps = [
            Part(f'leg{leg}', 'capsule', loc=(x, y + L['lean'][f], L['top'][f]), to=(x, y - 0.5 * L['lean'][f], L['bottom'] * k), radius=L['r'][f]),
            Part(f'arm{leg}', 'sphere', loc=(x + L['arm_dx'] * sx, y + L.get('arm_dy', {}).get(f, 0.004), L['arm_z'][f]), radius=L['arm_r'][f],
                 scale=L['arm_scale']),
            Part(f'paw{leg}', 'sphere', loc=(x, y - L['paw_dy'] * k, L['paw_z'] * k), radius=L['paw_r'] * k, scale=L['paw_scale']),
            Part(f'heel{leg}', 'sphere', loc=(x, y + L['heel_dy'] * k, L['heel_z'] * k), radius=L['heel_r'] * k, scale=(1.0, 1.0, 0.85)),
        ]
        for i, c in enumerate(self.toe_centres(leg)):
            ps.append(Part(f'toe{leg}{i}', 'sphere', loc=tuple(c), radius=L['toe']['r'] * k, scale=tuple(L['toe'].get('scale', (0.95, 1.2, 0.9)))))
        return ps

    def tail_parts(self) -> list[Part]:
        pts = HP.resample(self.tail_curve, 11)
        r = self.tail_radius(np.linspace(0.0, 1.0, len(pts)))
        sq = self.G['tail'].get('tall', 1.0)
        out = []
        for i in range(len(pts) - 1):
            out.append(Part(f'tail{i}', 'tube', loc=tuple(map(float, pts[i])), to=tuple(map(float, pts[i + 1])), radius=float(r[i]), r2=float(r[i + 1])))
            if sq > 1.0 and i < 4:
                # the root is taller than wide (2-turnaround side): a second, lower tube under the first ones
                lo = pts[i] - v3((0, 0, r[i] * (sq - 1.0)))
                lo2 = pts[i + 1] - v3((0, 0, r[i + 1] * (sq - 1.0)))
                out.append(Part(f'tailb{i}', 'tube', loc=tuple(map(float, lo)), to=tuple(map(float, lo2)), radius=float(r[i] * 0.85), r2=float(r[i + 1] * 0.85)))
        return out

    def all_parts(self) -> list[Part]:
        ps = list(self.G['head_parts']) + list(self.G['torso_parts']) + self.tail_parts()
        for leg in self.legs:
            ps.extend(self.leg_parts(leg))
        return ps

    # ------------------------------------------------------------------------- spikes (body extras)
    def spikes(self) -> list[dict]:
        """Every blade on the body: the crest on the head, the dorsal row (nape, back, tail) and small spiky scales at the
        cheeks' back edges; seated on the parts' surface."""
        if self._spikes:
            return self._spikes
        G = self.G['spikes']
        parts = self.all_parts()
        out = []
        for y, L in G['dorsal']:
            z = HP.top_of(0.0, y, parts)
            out.append({'kind': 'dorsal', 'base': (0.0, y, z), 'up': G.get('dorsal_up', (0.0, 0.55, 1.0)), 'back': (0.0, 1.0, 0.0),
                        'length': L, 'width': L * G.get('dorsal_w', 0.95), 'thick': L * G.get('dorsal_thick', 0.3), 'bend': 0.34, 'bury': 0.45})
        for z0, L in G.get('neck', []):
            # down the back of a long neck: seated from behind, leaning back and down the neck
            hit = HP.surface_hit((0.0, 3.0, z0), (0.0, -1.0, 0.0), parts, reach=4.0)
            if hit is None:
                continue
            out.append({'kind': 'dorsal', 'base': tuple(hit), 'up': G.get('neck_up', (0.0, 1.0, 0.45)), 'back': G.get('neck_back', (0.0, 0.25, -1.0)),
                        'length': L, 'width': L * 0.9, 'thick': L * G.get('dorsal_thick', 0.3), 'bend': 0.3, 'bury': 0.45})
        tc = HP.resample(self.tail_curve, 60)
        T = HP.tangents(tc)
        for t, L in G['tail']:
            i = int(round(t * (len(tc) - 1)))
            up = HP.unit(np.cross(np.array([1.0, 0.0, 0.0]), T[i]))
            if up[2] < 0:
                up = -up
            r = float(self.tail_radius(t))
            base = tc[i] + up * r * 0.9
            out.append({'kind': 'tail', 'base': tuple(base), 'up': tuple(HP.unit(up + T[i] * 0.55)), 'back': tuple(T[i]), 'length': L,
                        'width': L * 0.95, 'thick': L * G.get('dorsal_thick', 0.3), 'bend': 0.32, 'bury': 0.45})
        for x, y, L, up in G['crest']:
            z = HP.top_of(x, y, parts)
            out.append({'kind': 'crest', 'base': (x, y, z), 'up': up, 'back': (0.0, 1.0, 0.0), 'length': L, 'width': L * G.get('crest_w', 0.95),
                        'thick': L * G.get('crest_thick', 0.42), 'bend': 0.3, 'bury': 0.5, 'centre': abs(x) < 1e-6})
        for s in (1, -1):
            for y, z, L, d in G.get('cheek', []):
                x = HP.side_of(y, z, parts)
                if x is None:
                    continue
                out.append({'kind': 'cheek', 'base': (s * x, y, z), 'up': (s * d[0], d[1], d[2]), 'back': (0.0, 1.0, -0.4), 'length': L,
                            'width': L * 0.8, 'thick': L * 0.35, 'bend': 0.35, 'bury': 0.5})
        out += self.ruff(parts)
        self._spikes.extend(out)
        return self._spikes

    def ruff(self, parts: list[Part]) -> list[dict]:
        """Round 2: lifted scale tips that break the outline (1-hero): flat leaf scales whose free tips stand off the
        skin, in rows: a ruff from behind the cheeks round to the frills and the nape, and on the backs of the shoulders,
        elbows, haunches and heels. Each row (G['spikes']['ruff']): (p0, p1, outward, pointing, count, length, width,
        lift degrees), left side, mirrored; every scale is seated by a ray onto the parts."""
        out = []
        rng = np.random.default_rng(17)
        for p0, p1, nrm, d, count, L, W, lift in self.G['spikes'].get('ruff', []):
            for s in (1, -1):
                m = v3((s, 1.0, 1.0))
                n0, d0 = HP.unit(v3(nrm) * m), HP.unit(v3(d) * m)
                for i in range(count):
                    f = (i + 0.5) / count
                    q = (v3(p0) * (1 - f) + v3(p1) * f) * m
                    hit = HP.surface_hit(q + n0 * 0.3, -n0, parts, reach=0.6)
                    if hit is None:
                        continue
                    a = math.radians(lift + rng.uniform(-6, 6))
                    up = HP.unit(d0 * math.cos(a) + n0 * math.sin(a))
                    across = HP.unit(np.cross(n0, d0))
                    j = 1.0 + 0.15 * rng.uniform(-1, 1)
                    out.append({'kind': 'ruff', 'base': tuple(hit - n0 * 0.002), 'up': tuple(up), 'back': tuple(across), 'length': L * j,
                                'width': W * j, 'thick': W * 0.34, 'bend': 0.0, 'bury': 0.35, 'lean': 0.0})
        return out

    def body_extras(self) -> list[bpy.types.Object]:
        sp = self.G['spade']
        objs = [HP.blade(f'spike{i}', b, rings=12, seg=12) for i, b in enumerate(self.spikes())]
        objs.append(HP.teardrop('spade', sp['base'], sp['tip'], (1.0, 0.0, 0.0), sp['width'], sp['thick'], sp['bulge'], sp['curl'],
                                taper=sp.get('taper', 1.6)))
        return objs

    def spade_field(self, p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(how much a point is on the spade 0..1, its position along it 0 base .. 1 tip)."""
        sp = self.G['spade']
        b, tp = v3(sp['base']), v3(sp['tip'])
        ax = HP.unit(tp - b)
        L = float(np.linalg.norm(tp - b))
        t = ((p - b) @ ax) / L
        r = np.linalg.norm((p - b) - np.outer(t * L, ax), axis=1)
        on = smooth(-0.1, 0.05, t) * (r < sp['width'] * 0.8) * (t < 1.15)
        return on, np.clip(t, 0, 1)

    # ------------------------------------------------------------------------- the ear frills
    def frills(self) -> list[dict]:
        """The frill layers behind each cheek: the main fan, and (round 2) the smaller one above it (1-hero)."""
        return [self.G['frill']] + ([self.G['frill2']] if self.G.get('frill2') else [])

    def frill_dir(self, V: np.ndarray, s: int, F: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
        F = F or self.G['frill']
        n = len(F['dirs'])
        k = np.clip(V * (n - 1), 0, n - 1 - 1e-9)
        i = np.floor(k).astype(int)
        f = (k - i)[:, None]
        D = np.array([HP.unit(d) for d in F['dirs']])
        D[:, 0] *= s
        d = norm(D[i] * (1 - f) + D[np.minimum(i + 1, n - 1)] * f)
        Ls = np.array(F['lens'])
        L = Ls[i] * (1 - f[:, 0]) + Ls[np.minimum(i + 1, n - 1)] * f[:, 0]
        return d, L

    def frill_edge(self, V: np.ndarray, F: dict | None = None) -> np.ndarray:
        """The membrane's reach (share of the spine's length): 1 at each spine, scalloped in between."""
        F = F or self.G['frill']
        m = len(F['dirs']) - 1
        f = (V * m) % 1.0
        return 1.0 - F['scallop'] * np.sin(np.pi * f) ** 0.8

    def frill_point(self, s: int, U_: np.ndarray, V: np.ndarray, reach=None, F: dict | None = None) -> np.ndarray:
        F = F or self.G['frill']
        rt, rb = v3(F['root_top']), v3(F['root_bot'])
        rt[0] *= s
        rb[0] *= s
        root = rt[None] * (1 - V[:, None]) + rb[None] * V[:, None]
        d, L = self.frill_dir(V, s, F)
        if reach is None:
            reach = U_ * self.frill_edge(V, F)
        p = root + d * (L * reach)[:, None]
        # cupped: the middle of the fan bows forward (a cupped ear, not a flat card) and the points curl back
        fwd = HP.unit(v3((0.25 * s, -1.0, 0.0)))
        rp = np.clip(reach, 0.0, None)          # a spine's buried root runs to reach < 0: no fractional powers of it
        p += fwd[None] * (F['cup'] * rp ** 1.5 * np.sin(np.pi * V) ** 0.8)[:, None]
        p += v3((0.0, 1.0, 0.0))[None] * (F['curl'] * rp ** 3)[:, None]
        return p

    def frill_rib(self, V: np.ndarray, width: float = 0.05, F: dict | None = None) -> np.ndarray:
        m = len((F or self.G['frill'])['dirs']) - 1
        f = (V * m) % 1.0
        d = np.minimum(f, 1.0 - f) / m
        return np.exp(-(d / width) ** 2)

    def build_frill(self, name: str, s: int, high: bool, quick: bool, F: dict | None = None) -> bpy.types.Object:
        F = F or self.G['frill']
        nu, nv = ((70, 140) if not quick else (24, 48)) if high else (10, 30)
        rel = F.get('relief', 0.0018)
        k = self.G['k']

        def pts(U_, V):
            p = self.frill_point(s, U_, V, F=F)
            if high:
                # raised ribs and a fine vein network (the normal map; 4-details panel 1)
                out = HP.unit((s * 0.7, -0.7, 0.0))
                vein = self.frill_veins(p, U_, V, F)
                p = p + out[None] * (rel * self.frill_rib(V, F=F) * smooth(0.05, 0.25, U_) * (1 - 0.5 * U_) + 0.0005 * k * vein)[:, None]
            return p

        def attrs(U_, V):
            n = len(U_)
            return {'fan': np.stack([U_ * self.frill_edge(V, F), V, self.frill_rib(V, F=F)], axis=1), 'fin_part': np.full(n, float(s)),
                    'wing_uv': np.zeros((n, 3)), 'wing_side': np.zeros(n),
                    **({'vein': self.frill_veins(self.frill_point(s, U_, V, F=F), U_, V, F)} if high else {})}

        return HP.fan_sheet(name, pts, nu, nv, out=(s * 0.7, -0.7, 0.1), attrs_fn=attrs)

    def frill_veins(self, p: np.ndarray, U_: np.ndarray, V: np.ndarray, F: dict) -> np.ndarray:
        """0..1 veins on a frill: branching from the spines out toward the scalloped edge (round 3), or the older cells."""
        if self.G['wing'].get('veins') != 'branch':
            return HP.cell_veins(p, 0.016 * self.G['k'], seed=9, width=0.1) * smooth(0.12, 0.3, U_)
        m = len(F['dirs']) - 1
        pid = np.minimum(np.floor(V * m), m - 1)
        return HP.branch_veins(V * m - pid, U_, pid, seed=9, n_main=3, width=0.045) * smooth(0.08, 0.2, U_)

    def wing_veins(self, co: np.ndarray, wuv: np.ndarray) -> np.ndarray:
        """0..1 veins on a wing: branching from the finger bones toward the trailing edge (round 3), or the older cells."""
        W = self.G['wing']
        if W.get('veins') != 'branch':
            return HP.cell_veins(co, W.get('vein_cell', 0.02) * self.G['k'], seed=5, width=0.1) * smooth(0.03, 0.12, wuv[:, 2])
        nf = len(self.wings['fingers'])
        return HP.branch_veins(wuv[:, 1], wuv[:, 2], wuv[:, 0], seed=5, n_main=W.get('vein_n', 4), width=W.get('vein_w', 0.03),
                               sides_of=lambda p: (0,) if p > nf - 1.5 else (0, 1))

    def build_frill_spines(self, high: bool, quick: bool) -> list[bpy.types.Object]:
        """The frills' spines as tapering rods out to the membrane's points (round 2: they stop at the scalloped edge, no
        needles past it), teal at the root, orange-brown to the tip; skinned like the membrane (head -> ear.1 -> ear.2)."""
        tag = 'hi' if high else 'lo'
        out = []
        for li, F in enumerate(self.frills()):
            n = len(F['dirs'])
            r0, r1 = F['spine_r']
            for s in (1, -1):
                for k in range(n):
                    V = np.full(1, k / (n - 1))
                    nr = 14 if high else 5
                    u = np.linspace(-0.05, F.get('spine_end', 0.99), nr)
                    pts = np.concatenate([self.frill_point(s, np.array([1.0]), V, reach=np.array([x]), F=F)[None, 0] for x in u])
                    t = np.linspace(0.0, 1.0, nr)
                    r = r0 * (1 - t) + r1 * t
                    seg = (10 if not quick else 8) if high else 5
                    ob = HP.tube(f'{tag}_fspine{li}{"L" if s > 0 else "R"}{k}', pts, r, (0.0, 0.0, 1.0), seg=seg,
                                 tip=pts[-1] + HP.unit(pts[-1] - pts[-2]) * r1 * 1.2)
                    tt = np.concatenate([np.repeat(np.clip(u, 0, 1), seg), [0.0, 1.0]])
                    out.append(self._prop_attrs(ob, P_SPINE, s, tt))
        return out

    # ------------------------------------------------------------------------- the wings
    def wing_billow(self, ob: bpy.types.Object) -> None:
        co, vn = S.mesh_arrays(ob)
        wuv = S.attr_array(ob, 'wing_uv').astype(np.float64)
        u, v = wuv[:, 1], wuv[:, 2]
        b = self.G['wing']['billow'] * np.sin(np.pi * np.clip(u, 0, 1)) * np.sin(np.pi * np.clip(v, 0, 1)) ** 0.7
        S.set_positions(ob, co + vn * b[:, None])

    def build_wings(self, high: bool, quick: bool) -> list[bpy.types.Object]:
        tag = 'hi' if high else 'lo'
        W = self.G['wing']
        out = []
        for s in (1, -1):
            res = (W['res_quick'] if quick else W['res_high']) if high else W['res_low']
            ob = S.wing_membrane(f'{tag}_wing{U.wing_tag(s)}', self.wings, s, high, quick, relief=W['relief'], res=tuple(res))
            self.wing_billow(ob)
            if high:
                # round 2: the fine vein network raised on the high sheet, so the normal map carries it (4-details panel 4)
                co, vn = S.mesh_arrays(ob)
                vein = self.wing_veins(co, S.attr_array(ob, 'wing_uv').astype(np.float64))
                S.set_positions(ob, co + vn * (W.get('vein_relief', 0.0006) * self.G['k'] * vein)[:, None])
            n = len(ob.data.vertices)
            S.add_attr(ob, 'fan', np.zeros((n, 3)))
            S.add_attr(ob, 'fin_part', np.zeros(n))
            if 'UVMap' not in ob.data.uv_layers:
                ob.data.uv_layers.new(name='UVMap')
            out.append(ob)
        return out

    def build_fins(self, high: bool, quick: bool) -> list[bpy.types.Object]:
        tag = 'hi' if high else 'lo'
        frills = [self.build_frill(f'{tag}_frill{li or ""}{"L" if s > 0 else "R"}', s, high, quick, F)
                  for li, F in enumerate(self.frills()) for s in (1, -1)]
        return frills + self.build_wings(high, quick)

    # ------------------------------------------------------------------------- props
    @staticmethod
    def _prop_attrs(ob: bpy.types.Object, kind: int, side: float, t=None, g=None) -> bpy.types.Object:
        n = len(ob.data.vertices)
        S.add_attr(ob, 'pkind', np.full(n, float(kind)))
        S.add_attr(ob, 'pside', np.full(n, float(side)))
        S.add_attr(ob, 'pt', np.zeros(n) if t is None else np.asarray(t, np.float64))
        S.add_attr(ob, 'pg', np.zeros(n) if g is None else np.asarray(g, np.float64))
        if 'UVMap' not in ob.data.uv_layers:
            ob.data.uv_layers.new(name='UVMap')
        return ob

    def build_horns(self, high: bool, quick: bool) -> list[bpy.types.Object]:
        tag = 'hi' if high else 'lo'
        H = self.G['horn']
        out = []
        for s in (1, -1):
            pts = np.array([(s * x, y, z) for x, y, z in H['path']])
            path = HP.catmull(pts, 16 if high else 6)
            seg = (32 if not quick else 20) if high else 12
            ob = HP.ringed_horn(f'{tag}_horn{"L" if s > 0 else "R"}', path, H['r0'], H['r_tip'], H['rings'], H['groove'], high, seg, (s * 1.0, 0.0, 0.0))
            h = S.attr_array(ob, 'horn')
            out.append(self._prop_attrs(ob, P_HORN, s, h[:, 0], h[:, 1]))
        return out

    def build_claws(self, high: bool, quick: bool) -> list[bpy.types.Object]:
        tag = 'hi' if high else 'lo'
        L = self.G['leg']
        length, radius, curve = L['claw']
        blunt = L.get('claw_blunt', False)
        out = []
        for leg in self.legs:
            k = L['paw_k'][leg[0]]
            for i, dx in enumerate(L['toe_dx']):
                r = self.claw_root(leg, i)
                outer = abs(dx) > 0.6 * max(abs(d) for d in L['toe_dx'])
                cone = blunt == 'cone'
                d = (dx / max(abs(d) for d in L['toe_dx']) * 0.35, -1.0, -0.42 if not blunt else (-0.5 if cone else -0.6))
                ob = HP.talon(f'{tag}_claw{leg}{i}', r, d, (0.0, -0.15, -1.0), length * k * (0.9 if outer else 1.0), radius * k,
                              curve=curve, rings=(14 if cone else (9 if not blunt else 11)) if high else 6,
                              seg=(18 if cone else 12) if high else 7, flat=0.85 if not blunt else (0.95 if cone else 0.92), blunt=blunt)
                out.append(self._prop_attrs(ob, P_CLAW, LEG_INDEX[leg], S.attr_array(ob, 'talon_t')))
        return out

    def build_wing_bones(self, high: bool, quick: bool) -> list[bpy.types.Object]:
        """Each wing's arm (shoulder -> elbow -> wrist, teal, banded with scale rows), its finger bones (orange-brown) and
        the copper claw at the wrist: rigid tubes on the wing bones (prop_weight_regions: segment weights)."""
        tag = 'hi' if high else 'lo'
        W = self.G['wing']
        ar = W['arm_r']
        f0, f1 = W['finger_r']
        out = []
        for s in (1, -1):
            q = U.wing_points(self.wings, s)
            sh, el, wr = q['shoulder'], q['elbow'], q['wrist']
            n1 = 14 if high else 5
            a = np.linspace(0, 1, n1)[:, None]
            arm = np.concatenate([sh[None] * (1 - a) + el[None] * a, (el[None] * (1 - a) + wr[None] * a)[1:]])
            ta = np.linspace(0, 1, len(arm))
            ra = np.interp(ta, [0.0, 0.5, 1.0], ar)
            wb = W.get('wrist_bulge', 0.12)
            ra = ra * (1.0 + 0.14 * np.exp(-((ta - 0.5) / 0.08) ** 2) + wb * np.exp(-((ta - 1.0) / 0.07) ** 2))
            seg = (20 if not quick else 12) if high else 8
            ob = HP.tube(f'{tag}_warm{U.wing_tag(s)}', arm, ra, (0.0, 0.0, 1.0), seg=seg,
                         tip=wr + HP.unit(wr - el) * ar[2] * W.get('wrist_cap', 0.9))
            out.append(self._prop_attrs(ob, P_ARM, s, np.concatenate([np.repeat(ta, seg), [0.0, 1.0]])))
            for k, tip in enumerate(q['fingers']):
                lead = k == 0 and bool(W.get('lead_r'))
                nf = (16 if high else 5) if lead else (12 if high else 4)
                f = np.linspace(0, 1, nf)
                pts = wr[None] * (1 - f[:, None]) + tip[None] * f[:, None]
                if lead:
                    # round 3: the wing's leading edge, wrist to tip, is the arm's thick teal scaled edge tapering out; its
                    # root a rounded dome inside the wrist (a flat end cap there read as a cut pipe in the folded pose)
                    l0, l1 = W['lead_r']
                    d0 = HP.unit(tip - wr)
                    pre = np.array([0.95, 0.8, 0.55, 0.28])
                    pts = np.concatenate([wr[None] - d0[None] * (l0 * pre)[:, None], pts])
                    rf = np.concatenate([l0 * np.sqrt(1.0 - pre ** 2), l1 + (l0 - l1) * (1 - f) ** 1.3])
                    f = np.concatenate([np.zeros(len(pre)), f])
                    sg = (18 if not quick else 10) if high else 7
                    end = tip + HP.unit(tip - wr) * l1 * 1.1
                else:
                    rf = (f0 * (1 - f) + f1 * f) * (1.0 + 0.3 * np.exp(-(f / 0.08) ** 2))
                    sg = (12 if not quick else 8) if high else 6
                    end = tip + HP.unit(tip - wr) * f1 * 2.5
                ob = HP.tube(f'{tag}_wfin{U.wing_tag(s)}{k}', pts, rf, (0.0, 0.0, 1.0), seg=sg, tip=end)
                ft = np.concatenate([np.repeat(f, sg), [0.0, 1.0]])
                out.append(self._prop_attrs(ob, P_ARM if lead else P_FINGER, s, ft, np.full(len(ft), float(k + 1))))
            cl, cr = W['wclaw']
            wd = W.get('wclaw_dir', (0.15, -0.75, 0.65))
            d = HP.unit(v3((wd[0] * s, wd[1], wd[2])))
            ob = HP.talon(f'{tag}_wclaw{U.wing_tag(s)}', wr + d * ar[2] * 0.6, d, (0.0, -0.6, -0.4), cl, cr, curve=0.4,
                          rings=9 if high else 5, seg=12 if high else 7)
            out.append(self._prop_attrs(ob, P_WCLAW, s, S.attr_array(ob, 'talon_t')))
        return out

    def build_props(self, high: bool, quick: bool) -> list[bpy.types.Object]:
        return (self.build_horns(high, quick) + self.build_claws(high, quick) + self.build_wing_bones(high, quick)
                + self.build_frill_spines(high, quick))

    # ------------------------------------------------------------------------- the face's carving
    def mouth_curve(self) -> list[tuple[float, float]]:
        """(x, z): a wide closed smile (2-turnaround front, 3-faces neutral), its ends curling up into the cheeks."""
        M = self.G['mouth']
        pts = []
        for k in range(-24, 25):
            t = k / 24
            x = M['half'] * t
            z = M['z'] + M['curve'] * t * t + M['curl'] * max(0.0, abs(t) - 0.78) / 0.22 - M['dip'] * math.exp(-(t / 0.12) ** 2)
            pts.append((x, z))
        return pts

    def mouth_front(self, co: np.ndarray) -> np.ndarray:
        xs, ys = self.G['mouth']['front']
        yf = np.interp(np.abs(co[:, 0]), xs, ys)
        return smooth(yf + 0.05 * self.G['k'], yf - 0.01 * self.G['k'], co[:, 1])

    def eye_rim(self, co: np.ndarray) -> np.ndarray:
        """0..1: a soft ring of skin round each lens's edge, fuller above (the lids wrapping the eye; round 3)."""
        er = self.eye_r
        out = np.zeros(len(co))
        for s in (1, -1):
            c, xax, yax, look = self.eye_frame(s)
            q = co - v3(c)
            xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
            r = np.sqrt((xe / (er * self.eye_shape[0])) ** 2 + (ye / (er * self.eye_shape[1])) ** 2)
            ring = np.exp(-((r - 1.04) / 0.14) ** 2) * (0.55 + 0.45 * smooth(-0.4, 0.5, ye / er)) * (ze > -0.9 * er)
            out = np.maximum(out, ring)
        return out

    def eye_lid_top(self, co: np.ndarray) -> np.ndarray:
        """0..1: a fold of skin over the top of each lens (an upper lid), so the eye isn't a fully ringed goggle."""
        er = self.eye_r
        out = np.zeros(len(co))
        for s in (1, -1):
            c, xax, yax, look = self.eye_frame(s)
            q = co - v3(c)
            xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
            r = np.sqrt((xe / (er * self.eye_shape[0])) ** 2 + (ye / (er * self.eye_shape[1])) ** 2)
            fold = np.exp(-((r - 0.97) / 0.13) ** 2) * smooth(0.2, 0.75, ye / er) * (ze > -0.9 * er)
            out = np.maximum(out, fold)
        return out

    def closed_lid(self, co: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        lash_k, drop, lw = self.G['lid']
        bulge = np.zeros(len(co))
        lash = np.zeros(len(co))
        er = self.eye_r
        for s in (1, -1):
            c, xax, yax, look = self.eye_frame(s)
            q = co - v3(c)
            xe, ye, ze = q @ v3(xax), q @ v3(yax), q @ v3(look)
            ax, ay = er * self.eye_shape[0], er * self.eye_shape[1]
            r2 = (xe / ax) ** 2 + (ye / ay) ** 2
            front = ze > -0.55 * er
            bulge = np.maximum(bulge, np.clip(1.0 - r2, 0.0, 1.0) ** 1.5 * front)
            xn = xe / (ax * lw)
            arc = -(lash_k + drop * (1.0 - np.clip(xn, -1, 1) ** 2)) * er
            th = (0.0024 + 0.0018 * smooth(0.2, 1.0, xn * s)) * self.G['k_face']
            on = front & (np.abs(xn) < 1.04) & (r2 < 1.4)
            lash = np.maximum(lash, np.exp(-((ye - arc) / th) ** 2) * on * smooth(1.04, 0.9, np.abs(xn)))
        return bulge, lash

    # ------------------------------------------------------------------------- zones
    def leg_masks(self, p: np.ndarray) -> dict[str, np.ndarray]:
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        out = {}
        for leg, (lx, ly) in self.legs.items():
            top = self.G['zone']['leg_top'][leg[0]]
            r = np.hypot(x - lx, (y - ly + 0.02 * self.G['k']) * 0.85)
            out[leg] = (r < self.G['zone']['leg_r']) & (z < top)
        return out

    def zones(self, p: np.ndarray, n: np.ndarray | None = None) -> dict[str, np.ndarray]:
        Z = self.G['zone']
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        ax = np.abs(x)
        head = (in_ellipsoid(p, *Z['head'][:2]) < 1.0) & (z > Z['head'][2])
        muzzle = in_ellipsoid(p, *Z['muzzle']) < 1.0
        nr = self.G['nose_r']
        nose = in_ellipsoid(p, tuple(self.nose_c), tuple(r * 1.5 for r in nr)) < 1.0
        eye_d = np.minimum(np.linalg.norm(p - v3(self.eye_c[1]), axis=1), np.linalg.norm(p - v3(self.eye_c[-1]), axis=1))
        fy, fz0, fz1, fx = Z['face']
        face = head & (y < fy) & (z > fz0) & (z < fz1) & (ax < fx)
        legs = self.leg_masks(p)
        leg = np.zeros(len(p), bool)
        for m in legs.values():
            leg |= m
        leg &= ~head
        k = self.G['k']
        paw = leg & (z < 0.12 * k)
        toes = np.zeros(len(p), bool)
        for lg, (lx, ly) in self.legs.items():
            toes |= legs[lg] & (y < ly - 0.06 * k) & (z < 0.09 * k)
        sole = z < 0.025 * k
        tt, td = self.tail_param(p)
        tail = (~leg) & (y > Z['tail_y']) & (tt > 0.03) & (td < Z['tail_r'])
        spade, _st = self.spade_field(p)
        tail |= spade > 0.5
        torso = ~head & ~leg & ~tail
        if 'neck' in Z:
            # the grown form's long neck: between the shoulders and the head (its own zone, part of the torso)
            neck = (in_ellipsoid(p, *Z['neck']) < 1.0) & ~head
        else:
            neck = np.zeros(len(p), bool)
        return {'head': head, 'muzzle': muzzle, 'nose': nose, 'eye_d': eye_d, 'face': face, 'leg': leg, 'paw': paw, 'toes': toes,
                'sole': sole, 'tail': tail, 'tail_t': tt, 'tail_d': td, 'spade': spade, 'torso': torso, 'legs': legs, 'neck': neck}

    def decimate_keep(self, co: np.ndarray) -> np.ndarray:
        z = self.zones(co)
        keep = z['face'] * 1.0 + z['muzzle'] + (z['eye_d'] < self.eye_r * 1.7) + 0.75 * z['toes'] + 0.25 * z['paw']
        on, t, _k = HP.blade_field(co, self.spikes(), pad=0.003)
        kb0, kb1 = self.G['scales'].get('keep_blade', (0.45, 0.55))
        keep = keep + on * (kb0 + kb1 * t) + self.G['spade'].get('keep', 0.5) * z['spade']
        return np.clip(keep, 0, 1)

    # ------------------------------------------------------------------------- the coat: where cream goes
    def cream_mask(self, p: np.ndarray, z: dict | None = None) -> np.ndarray:
        """0 teal .. 1 cream: the lower face (the teal comes down the snout to the nose), a cream patch round each eye,
        the throat, chest and belly, the tail's underside, the paws' rims."""
        if z is None:
            z = self.zones(p)
        Cg = self.G['cream']
        k = self.G['k']
        x, y, zz = p[:, 0], p[:, 1], p[:, 2]
        ax = np.abs(x)
        xs, zs = Cg['face_line']
        zline = np.interp(ax, xs, zs)
        fy0, fy1 = Cg['face_y']
        face = smooth(zline + 0.008 * k, zline - 0.008 * k, zz) * smooth(fy0, fy1, y)
        cream = face * z['head']
        er = self.eye_r
        px, pz, py, pdz = Cg['eye_patch']
        vt = None
        if 'v_teal' in Cg:
            # round 2: the teal forehead comes down in a V between the cream eye rings to the nose
            x0, slope, z0 = Cg['v_teal']
            vx = x0 + np.clip(zz - z0, 0, None) * slope
            vt = smooth(vx, vx + 0.012 * k, ax)
        for s in (1, -1):
            c = v3(self.eye_c[s])
            e = ell_soft(p, tuple(c + v3((0.004 * s * k, 0.0, pdz))), (er * px, py, er * pz), 0.12)
            if vt is not None:
                e = e * vt
            cream = np.maximum(cream, e * 0.94)
        zsb, wsb = Cg['bib']
        w = np.interp(zz, zsb, wsb)
        by0, by1 = Cg['bib_y']
        bz0, bz1 = Cg['bib_top']
        front = smooth(w + 0.012 * k, w - 0.012 * k, ax) * smooth(by0, by1, y) * smooth(bz0, bz1, zz)
        if 'bib_y_of_z' in Cg:
            # the grown form's long neck: the cream throat follows the neck's front up to the chin
            zq, yq = Cg['bib_y_of_z']
            yb = np.interp(zz, zq, yq)
            front = np.maximum(front, smooth(w + 0.012 * k, w - 0.012 * k, ax) * smooth(yb + 0.02 * k, yb - 0.01 * k, y)
                               * smooth(zq[0], zq[0] + 0.05 * k, zz) * smooth(bz0, bz1, zz))
        cream = np.maximum(cream, front * ~z['leg'])
        if 'throat' in Cg:
            # a long, slanted neck: cream on its front (by the angle round the neck's axis), up to the chin
            pts, fdir, cut = Cg['throat']
            pts = np.array(pts, np.float64)
            tq, _len = U.polyline_param(p, pts)
            q = HP.curve_at(pts, np.clip(tq, 0, 1))
            r = p - q
            rn = norm(r)
            f = rn @ HP.unit(fdir)
            on = smooth(-0.05, 0.05, tq) * smooth(1.08, 1.0, tq) * (np.linalg.norm(r, axis=1) < 0.35 * k)
            cream = np.maximum(cream, smooth(cut - 0.08, cut + 0.08, f) * on)
        ys, zb_ = Cg['belly']
        zb = np.interp(y, ys, zb_)
        cream = np.maximum(cream, (z['torso'] | z['neck']) * smooth(zb + 0.012 * k, zb - 0.012 * k, zz))
        tt, td = self.tail_param(p)
        q = HP.curve_at(self.tail_curve, np.clip(tt, 0, 1))
        below = smooth(0.05, -0.35, (zz - q[:, 2]) / np.maximum(td, 1e-4)) * z['tail'] * smooth(0.95, 0.85, tt)
        cream = np.maximum(cream, below)
        rr, rz = Cg['paw_rim']
        for lg, (lx, ly) in self.legs.items():
            rim = ell_soft(p, (lx, ly - 0.04 * k, 0.0), rr, 0.15) * smooth(rz, rz * 0.4, zz)
            cream = np.maximum(cream, rim)
        if Cg.get('crisp'):
            # round 3: narrow every soft edge round the 0.5 line, so no broad half-cream zone breaks into islands
            cream = smooth(0.5 - Cg['crisp'], 0.5 + Cg['crisp'], cream)
        return np.clip(cream, 0.0, 1.0)

    # ------------------------------------------------------------------------- the scales
    def scale_flow(self, p: np.ndarray, n: np.ndarray) -> np.ndarray:
        """Which way each scale points (its free edge): back from the nose over the head, toward the tail along the back,
        down the flanks, legs and neck, down the chest's bands, along the tail."""
        x, y, zz = p[:, 0], p[:, 1], p[:, 2]
        k = len(p)
        z_ = self.zones(p, n)
        g_head = norm(p - v3((0.0, self.nose_c.y - 0.05 * self.G['k'], self.nose_c.z + 0.03 * self.G['k'])))
        side = np.clip(np.abs(n[:, 0]) * 1.25, 0, 1)[:, None]
        g_torso = norm(v3((0.0, 1.0, -0.15))[None] * (1 - side) + v3((0.0, 0.45, -1.0))[None] * side)
        under = smooth(-0.2, -0.6, n[:, 2])[:, None]
        g_torso = norm(g_torso * (1 - under) + v3((0.0, 1.0, 0.0))[None] * under)
        front = smooth(-0.3, -0.6, n[:, 1])[:, None]
        g_torso = norm(g_torso * (1 - front) + v3((0.0, 0.0, -1.0))[None] * front)
        g_neck = norm(v3((0.0, 0.35, -1.0))[None] + 0.0 * p)
        T = HP.tangents(HP.resample(self.tail_curve, 60))
        i = np.clip((np.clip(z_['tail_t'], 0, 1) * 59).astype(int), 0, 59)
        g = np.where(z_['head'][:, None], g_head, g_torso)
        g = np.where(z_['neck'][:, None], g_neck, g)
        g = np.where(z_['leg'][:, None], np.tile(v3((0.0, -0.05, -1.0)), (k, 1)), g)
        g = np.where(z_['tail'][:, None], T[i], g)
        sp = self.G['spade']
        g = np.where((z_['spade'] > 0.5)[:, None], np.tile(HP.unit(v3(sp['tip']) - v3(sp['base'])), (k, 1)), g)
        return tangent(g, n)

    def scale_params(self, p: np.ndarray, n: np.ndarray):
        """Per point (spacing, NaN = none; radius; height) of the teal scales."""
        Sg = self.G['scales']
        z = self.zones(p, n)
        cream = self.cream_mask(p, z)
        sp = np.full(len(p), Sg['body'])
        sp = np.where(z['neck'], Sg.get('neck', Sg['body']), sp)
        if 'back' in Sg:
            # larger plates down the back (the grown form: grown-4-details panel 6)
            bsp, bx, bz = Sg['back']
            sp = np.where(z['torso'] & (np.abs(p[:, 0]) < bx) & (p[:, 2] > bz), bsp, sp)
        sp = np.where(z['head'], Sg['head'], sp)
        sp = np.where(z['muzzle'] | z['nose'], Sg['snout'], sp)
        sp = np.where(z['leg'], Sg['leg'], sp)
        sp = np.where(z['paw'], Sg['paw'], sp)
        sp = np.where(z['tail'], Sg['tail'][0] + (Sg['tail'][1] - Sg['tail'][0]) * np.clip(z['tail_t'], 0, 1), sp)
        sp = np.where(z['spade'] > 0.5, Sg['spade'], sp)
        h = np.where(z['head'] | z['leg'], Sg['h_head'], Sg['h_body'])
        h = np.where(z['muzzle'] | z['nose'], Sg['h_fine'], h)
        h = np.where(z['spade'] > 0.5, Sg.get('h_spade', Sg['h_fine']), h)
        on_sp, _t, _k = HP.blade_field(p, self.spikes(), pad=0.002)
        # round 2: the scales run on into the cream border (each takes the colour at its centre: a jagged scaly border)
        # and over the toes; not on the deep cream, the eyes, the soles or the nose pad
        skip = (cream > Sg.get('cream_skip', 0.45)) & ~(z['spade'] > 0.5)
        skip |= on_sp | (z['eye_d'] < self.eye_r * 1.25) | z['sole'] | (self.chevron_region(p) > 0.5)
        skip |= z['face'] & (cream > 0.45)
        skip |= in_ellipsoid(p, tuple(self.nose_c), tuple(r * 1.15 for r in self.G['nose_r'])) < 1.0
        return np.where(skip, np.nan, sp), sp * Sg['overlap'], h

    def band_params(self, p: np.ndarray, n: np.ndarray):
        """The cream throat and belly outside the chevrons: soft wide bands (4-details panel 5)."""
        Sg = self.G['scales']
        z = self.zones(p, n)
        cream = self.cream_mask(p, z)
        on = (cream > Sg.get('cream_skip', 0.45)) & ~z['paw'] & ~(z['spade'] > 0.5) & ~z['face']
        on &= ~(self.chevron_region(p) > 0.3)
        on &= ~(z['eye_d'] < self.eye_r * 1.6)
        on &= ~z['head']                    # round 2: the cream face stays smooth skin (the bands smeared the cheeks)
        sp = np.where(z['tail'], Sg['band'] * 0.75, Sg['band'])
        sp = np.where(z['leg'], Sg['band'] * 0.65, sp)
        return np.where(on, sp, np.nan), sp * 1.05, np.full(len(p), Sg['h_band'])

    def chevron_region(self, p: np.ndarray) -> np.ndarray:
        cv = self.G['chevron']
        return ell_soft(p, cv['centre'], cv['radii'], 0.05)

    def chevron_field(self, co: np.ndarray, vn: np.ndarray) -> dict[str, np.ndarray]:
        """The chest's leaf of chevrons (4-details panel 5; the grown form's fireplace grate, grown-4-details panel 5): a
        midrib down the chest's middle and V-shaped seams rising out from it, row under row, and the leaf's outline;
        between them leaf plates whose lower (free) edge stands out over the plate below. Returns region (0..1), seam
        (0..1, the grate's slots), frac (0 at a plate's lower edge .. 1 at its upper one), h (metres)."""
        cv = self.G['chevron']
        c0 = v3(cv['centre'])
        rx, ry, rz = cv['radii']
        region = ell_soft(co, cv['centre'], cv['radii'], cv.get('soft', 0.08)) * smooth(-0.05, -0.35, vn[:, 1])
        x, z = co[:, 0], co[:, 2]
        ax = np.abs(x)
        slope = math.tan(math.radians(cv['angle']))
        dz = 2 * rz / cv['rows']
        v = (z - (c0[2] - rz) - ax * slope) / dz
        frac = v - np.floor(v)
        dv = np.minimum(frac, 1 - frac) * dz * math.cos(math.atan(slope))
        q = np.sqrt((x / rx) ** 2 + ((z - c0[2]) / rz) ** 2)
        do = np.abs(1.0 - q) * min(rx, rz)
        w = cv['seam']
        seam = np.maximum(np.exp(-(dv / w) ** 2), np.exp(-(ax / (w * 0.9)) ** 2))
        if cv.get('outline', True):
            seam = np.maximum(seam, np.exp(-(do / w) ** 2) * smooth(0.7, 0.95, q))
        else:
            do = np.full(len(co), 9.0)     # young: no rim (it drew a shield); the scaly border comes from the scales
        d = np.minimum(np.minimum(dv, ax), do / 0.8)
        dome = smooth(0.0, w * 3.0, d) ** 0.7
        h = cv['h'] * dome * (0.4 + 0.6 * (1.0 - frac) ** 0.8)
        return {'region': region, 'seam': seam * region, 'frac': frac, 'h': h}

    def carve(self, ob: bpy.types.Object) -> None:
        k = self.G['k_face']
        co, vn = S.mesh_arrays(ob)
        x, y, z = co[:, 0], co[:, 1], co[:, 2]
        M = self.G['mouth']
        md = S.polyline_dist(x, z, self.mouth_curve())
        groove = np.exp(-(md / M['width']) ** 2) * self.mouth_front(co) * (z < self.nose_c.z - 0.03 * k) * (z > M['zmin'])
        if M.get('side'):
            # the grown form's long muzzle: the lip line runs back along each side of it to the mouth's corner
            sd = S.polyline_dist(y, z, M['side'])
            ys_ = [q[0] for q in M['side']]
            on_side = smooth(M['side_x'] * 0.6, M['side_x'], np.abs(x)) * (y > min(ys_) - 0.01) * (y < max(ys_) + 0.01)
            groove = np.maximum(groove, np.exp(-(sd / M['width']) ** 2) * on_side)
        Nn = self.G['nostril']
        nos = np.zeros(len(co))
        for s in (1, -1):
            dd = np.sqrt(((x - Nn['dx'] * s) / 1.6) ** 2 + (z - (self.nose_c.z + Nn['dz'])) ** 2)
            nos = np.maximum(nos, np.exp(-(dd / Nn['r']) ** 2))
        nos *= smooth(self.nose_c.y + 0.03 * k, self.nose_c.y + 0.01 * k, y)
        bulge, lash = self.closed_lid(co)
        disp = (-0.0024 * groove - 0.004 * nos + 0.0028 * bulge - 0.0012 * lash) * k
        if self.G['eye'].get('rim'):
            disp = disp + self.G['eye']['rim'] * self.eye_r * self.eye_rim(co)
        if self.G['eye'].get('lid_top'):
            disp = disp + self.G['eye']['lid_top'] * self.eye_r * self.eye_lid_top(co)
        # round 2: a cleft between neighbouring toes, so each paw reads as four distinct toe bulges
        kk = self.G['k']
        cleft = np.zeros(len(co))
        for leg in self.legs:
            tc = self.toe_centres(leg)
            for a, b in zip(tc[:-1], tc[1:]):
                m_ = (a + b) * 0.5
                d = np.sqrt(((x - m_[0]) / (0.0045 * kk)) ** 2 + ((y - (m_[1] - 0.012 * kk)) / (self.G['leg'].get('cleft_len', 0.04) * kk)) ** 2)
                cleft = np.maximum(cleft, np.exp(-d ** 2) * (z < self.G['leg'].get('cleft_z', 0.085) * kk) * (z > 0.004 * kk))
        disp = disp - self.G['leg'].get('cleft', 0.007) * kk * cleft
        SPg = self.G['spade']
        if SPg.get('midrib'):
            sp_on, sp_t = self.spade_field(co)
            b_, tp_ = v3(SPg['base']), v3(SPg['tip'])
            ax_ = HP.unit(tp_ - b_)
            side_ = HP.unit(np.cross(ax_, np.cross(v3((1.0, 0.0, 0.0)), ax_)))     # the leaf's width runs along X
            off = np.abs((co - b_) @ v3((1.0, 0.0, 0.0)))
            rib_ = np.exp(-(off / (SPg['midrib'][1] * kk)) ** 2) * smooth(0.05, 0.22, sp_t) * smooth(1.0, 0.8, sp_t) * (sp_on > 0.5)
            disp = disp + SPg['midrib'][0] * kk * rib_
        S.set_positions(ob, co + vn * disp[:, None])
        S.base_attrs(ob, co, {'mouth': groove})
        S.add_attr(ob, 'lash', lash)
        S.add_attr(ob, 'lid', bulge)
        Sg = self.G['scales']
        co2, vn2 = S.mesh_arrays(ob)
        flow = self.scale_flow(co, vn2)
        sp, rad, h = self.scale_params(co, vn2)
        plates = U.plate_layout(co2, vn2, sp, rad, h, seed=21, flow=flow, aspect=Sg['aspect'], wobble=0.08)
        f = HP.shingle_field(co2, vn2, plates, leaf=Sg.get('leaf', 0.22))
        # each scale takes the cream / teal colour at its centre (a scaly border, round 2)
        pc = self.cream_mask(plates['c']) if len(plates['c']) else np.zeros(0)
        if len(pc) and Sg.get('majority'):
            # round 3: no lone cream scales on the teal (or teal on the cream): a clean scaly sawtooth border
            pc = HP.plate_majority(plates['c'], pc > 0.5, k=8, flip=Sg['majority'])
        sp_b, rad_b, h_b = self.band_params(co, vn2)
        bands = U.plate_layout(co2, vn2, sp_b, rad_b, h_b, seed=22, flow=flow, aspect=0.5, wobble=0.05)
        nb = len(bands['c'])
        fb = HP.shingle_field(co2, vn2, bands, lift=0.3)
        hh = np.maximum(f['h'], fb['h'])
        # the grooves between plates sink a little
        gap = (f['pid'] < 0) & (fb['pid'] < 0)
        hh = hh - Sg.get('inset', 0.0004) * gap
        # the chest's leaf of chevrons replaces whatever plates lie in its region
        ch = self.chevron_field(co, vn2)
        hh = hh * (1 - ch['region']) + ch['h'] * ch['region']
        rib = HP.scale_midrib(co2, plates, f['pid'])
        hh = hh + Sg.get('rib_h', 0.0004) * rib * (f['h'] >= fb['h'])
        S.set_positions(ob, co2 + vn2 * hh[:, None])
        on_s = (f['pid'] >= 0) & (f['h'] >= fb['h'])
        on_b = (fb['pid'] >= 0) & ~on_s
        S.add_attr(ob, 'scale_id', np.where(on_s, f['pid'], -1).astype(np.float64))
        S.add_attr(ob, 'scale_ul', np.where(on_s, f['ul'], 0.0))
        S.add_attr(ob, 'scale_rho', np.where(on_s, f['rho'], 2.0))
        S.add_attr(ob, 'scale_cream', np.where(on_s, pc[np.clip(f['pid'], 0, None)] if len(pc) else 0.0, -1.0))
        S.add_attr(ob, 'band_id', np.where(on_b, fb['pid'], -1).astype(np.float64))
        S.add_attr(ob, 'band_ul', np.where(on_b, fb['ul'], 0.0))
        S.add_attr(ob, 'band_rho', np.where(on_b, fb['rho'], 2.0))
        S.add_attr(ob, 'chev', ch['region'])
        S.add_attr(ob, 'chev_seam', ch['seam'])
        S.add_attr(ob, 'chev_frac', ch['frac'])
        S.add_attr(ob, 'midrib', rib * on_s)
        C.log(f'{ob.name}: {len(plates["c"])} scales, {nb} bands, {int((ch["region"] > 0.5).sum())} chevron vertices; {int(on_s.sum())} + {int(on_b.sum())} of {len(co)} '
              f'vertices; relief up to {float(hh.max()) * 1000:.1f} mm')
        self._plates.clear()
        self._plates.update({'n': len(co), 'on_s': on_s, 'on_b': on_b, 'rho': np.where(on_s, f['rho'], np.where(on_b, fb['rho'], 2.0)),
                             'ul': np.where(on_s, f['ul'], fb['ul']), 'chev_seam': ch['seam']})

    # ------------------------------------------------------------------------- paint
    def glow_fields(self, root: np.ndarray, cream: np.ndarray, region: np.ndarray, seam: np.ndarray, frac: np.ndarray):
        """(glow mask 0..1, warm tint 0..1) of the chest: young, a soft warm heart; grown, the grate's molten seams and the
        light showing under each plate's lower edge."""
        gl = self.G['glow']
        heart = ell_soft(root, gl['centre'], gl['radii'], 0.9) * cream
        under = region * (1 - seam) * smooth(0.45, 0.0, frac)
        g = heart * gl['heart'] + seam * (0.35 + 0.65 * heart ** 0.5) * gl['seam'] + under * gl.get('under', 0.0)
        warm = np.clip(heart * gl['warm'] + seam * gl['seam_warm'] + under * gl.get('under', 0.0), 0, 1)
        return np.clip(g, 0, 1), warm

    def body_arrays(self, ob: bpy.types.Object, pal: dict) -> dict[str, np.ndarray]:
        col = colours(pal)
        root = S.attr_array(ob, 'root').astype(np.float64)
        n = len(root)
        z = self.zones(root)
        cream = self.cream_mask(root, z)

        def get(name, default=0.0):
            return S.attr_array(ob, name).astype(np.float64) if name in ob.data.attributes else np.full(n, default)

        pid = get('scale_id', -1).astype(np.int64)
        ul, rho = get('scale_ul'), get('scale_rho', 2.0)
        bpid = get('band_id', -1).astype(np.int64)
        bul, brho = get('band_ul'), get('band_rho', 2.0)
        region, cseam, cfrac = get('chev'), get('chev_seam'), get('chev_frac')
        mid = get('midrib')
        on = pid >= 0
        bon = bpid >= 0
        hsh = U.plate_hash(pid, 3)
        # the teal: each scale darker at its root (tucked under the one before), lighter toward its free edge, a fine dark
        # outline, a pale midrib; the gaps deep teal
        teal = np.tile(lin(col['teal']), (n, 1)) * (0.94 + 0.12 * hsh)[:, None]
        rootk = smooth(0.4, -0.95, ul) * on
        edge = smooth(0.8, 0.97, rho) * on
        teal = HP.blend(teal, rootk * 0.68, col['root'])
        teal = HP.blend(teal, smooth(-0.1, 0.75, ul) * (1 - edge) * on * 0.28, col['sheen'])
        teal = HP.blend(teal, mid * 0.22, col['sheen'])
        rim_k = (1.0 - 0.7 * smooth(0.15, 0.5, cream)) if self.G['cream'].get('border_soft') else 1.0
        teal = HP.blend(teal, np.where(on, edge * 0.85, 0.7) * rim_k, col['rim'])
        flecks = on & (U.plate_hash(pid, 11) > 0.955) & (root[:, 2] > self.G['fleck_z']) & (np.abs(root[:, 0]) < 0.12 * self.G['k']) & ~z['head']
        teal = HP.blend(teal, flecks * smooth(0.35, 0.85, ul) * (1 - edge) * 0.85, col['spike_tip'])
        # the cream: bands outlined in a warm tan, darker at their roots, paler in their middles
        bh = U.plate_hash(bpid, 5)
        cr = np.tile(lin(col['cream_base']), (n, 1)) * (0.95 + 0.08 * bh)[:, None]
        bedge = smooth(0.78, 0.97, brho) * bon
        cr = HP.blend(cr, smooth(0.3, -0.9, bul) * bon * 0.35, col['cream_rim'])
        cr = HP.blend(cr, np.where(bon, bedge * 0.7, 0.55), col['cream_rim'])
        cr = HP.blend(cr, smooth(-0.3, 0.6, bul) * (1 - bedge) * bon * 0.35, col['cream_hi'])
        # the chest's leaf of chevrons: plates paler at their free lower edge, shaded where they tuck under the row above,
        # outlined by the seams (young: a warm tan; grown: the molten grate, painted with the glow below)
        plate = HP.blend(np.tile(lin(col['cream_base']), (n, 1)), smooth(0.55, 0.05, cfrac) * 0.3, col['cream_hi'])
        plate = HP.blend(plate, smooth(0.5, 1.0, cfrac) * 0.35, col['cream_rim'])
        plate = HP.blend(plate, cseam / np.maximum(region, 1e-3) * 0.75, col['cream_rim'])
        tint = self.G['chevron'].get('plate_tint')
        if tint:
            # the grate's plates: a warm, darker cream-orange, so the molten seams stand out against them
            plate = HP.blend(plate, np.full(n, tint[1]), tint[0])
        cr = cr * (1 - region[:, None]) + plate * region[:, None]
        # round 2: a scale takes one colour, the cream / teal at its centre (a jagged scaly border, not a smooth shield);
        # cream scales get the same shading as teal ones, in tan
        pcream = get('scale_cream', -1.0)
        ce = np.where(on, smooth(0.42, 0.58, pcream), cream)
        if self.G['cream'].get('border_soft'):
            ce = np.where(on, 0.55 * smooth(0.42, 0.58, pcream) + 0.45 * smooth(0.3, 0.7, cream), cream)
        crs = np.tile(lin(col['cream_base']), (n, 1)) * (0.95 + 0.08 * hsh)[:, None]
        crs = HP.blend(crs, rootk * 0.5, col['cream_rim'])
        crs = HP.blend(crs, smooth(-0.1, 0.75, ul) * (1 - edge) * 0.3, col['cream_hi'])
        crs = HP.blend(crs, edge * 0.75, col['cream_rim'])
        cr = np.where(on[:, None], crs, cr)
        rgb = teal * (1 - ce[:, None]) + cr * ce[:, None]
        cream = ce
        # the spikes: teal at the root, orange toward the tip; the ruff's lifted scales stay teal, darker at the root
        sp = self.spikes()
        on_sp, t_sp, k_sp = HP.blade_field(root, sp, pad=0.003 * self.G['k'])
        idx = np.where(k_sp >= 0, k_sp, -1)
        starts = np.array([0.15 if b.get('centre') else (9.0 if b['kind'] == 'ruff' else self.G['spike_orange']) for b in sp] + [9.0])
        start = starts[idx]
        is_ruff = np.array([b['kind'] == 'ruff' for b in sp] + [False])[idx] & on_sp
        rgb = HP.blend(rgb, is_ruff * 1.0, col['teal'])
        rgb = HP.blend(rgb, is_ruff * smooth(0.45, 0.0, t_sp) * self.G['spikes'].get('ruff_dark', 0.6), col['root'])
        rgb = HP.blend(rgb, is_ruff * smooth(0.35, 1.0, t_sp) * 0.3, col['sheen'])
        rgb = HP.blend(rgb, smooth(start - 0.12, start + 0.15, t_sp) * on_sp, col['spike_mid'])
        rgb = HP.blend(rgb, smooth(start + 0.08, start + 0.45, t_sp) * on_sp, col['spike_tip'])
        # the spade (round 2): a plump bud glowing from within, a hot yellow-orange core through translucent orange, its
        # small scales outlined in deep orange, a few bright speckles
        SPg = self.G['spade']
        sp_on, sp_t = self.spade_field(root)
        sk = smooth(0.2, 0.75, sp_on)
        hot = smooth(0.6, 0.12, np.abs(sp_t - 0.42))
        if SPg.get('collar'):
            # a short teal scaled collar where the bud meets the tail (the bud a solid scaled thing, never a flame)
            sk = sk * smooth(SPg['collar'] - 0.035, SPg['collar'] + 0.035, sp_t)
        if SPg.get('saturated'):
            # round 3: a saturated #FF8A3D bud, its scales darker at the root and outlined deeper, a yellow core inside
            core = smooth(0.24, 0.04, np.abs(sp_t - 0.46))
            spade = HP.blend(np.tile(lin(col['orange']), (n, 1)), rootk * 0.5, col['membrane_dark'])
            spade = HP.blend(spade, edge * 0.75, col['rib'])
            spade = HP.blend(spade, smooth(-0.1, 0.75, ul) * (1 - edge) * 0.22, col['membrane_lite'])
            spade = HP.blend(spade, core ** 1.5 * (1 - edge) * 0.5, col['glow_core'])
            hot = core
        else:
            spade = HP.blend(np.tile(lin(col['spike_tip']), (n, 1)), hot * 0.55, col['glow_warm'])
            spade = HP.blend(spade, hot ** 2 * 0.6, col['glow_core'])
            spade = HP.blend(spade, rootk * 0.4, col['membrane_dark'])
            spade = HP.blend(spade, edge * 0.6, col['rib'])
        speck = np.zeros(n)
        cand = np.nonzero(sk > 0.6)[0]
        if len(cand):
            pick = cand[np.random.default_rng(7).choice(len(cand), min(12 if SPg.get('saturated') else 26, len(cand)), replace=False)]
            for c in root[pick]:
                d2 = ((root - c) ** 2).sum(axis=1)
                speck = np.maximum(speck, np.exp(-d2 / (0.0055 * self.G['k']) ** 2))
        spade = HP.blend(spade, speck * (0.75 if SPg.get('saturated') else 0.9), '#FFF0B0')
        rgb = rgb * (1 - sk[:, None]) + spade * sk[:, None]
        # the soles: cream with copper pads (a palm pad and one under each toe; 4-details panel 3)
        pads = np.zeros(n)
        k_ = self.G['k']
        L = self.G['leg']
        tips = np.zeros(n)
        hp = L.get('heart_pad')
        for lg, (lx, ly) in self.legs.items():
            kk = L['paw_k'][lg[0]] * k_
            if hp:
                # a heart: two lobes toward the toes, its point toward the heel
                hx, hy, hr = hp
                yl = ly - hy * kk
                heart = np.zeros(n)
                for sx_ in (1, -1):
                    heart = np.maximum(heart, ell_soft(root, (lx + sx_ * hx * kk, yl, 0.0), (hr * kk, hr * kk, 0.03 * kk), 0.12))
                depth = 2.3 * hr * kk
                dy = root[:, 1] - yl
                half = (hx + hr * 0.92) * kk * np.clip(1.0 - dy / depth, 0.0, 1.0) ** 0.9
                tri = smooth(-0.002 * kk, 0.002 * kk, half - np.abs(root[:, 0] - lx)) * (dy > 0) * (root[:, 2] < 0.03 * kk)
                pads = np.maximum(pads, np.maximum(heart, tri) * smooth(0.024 * k_, 0.012 * k_, root[:, 2]))
            else:
                pads = np.maximum(pads, ell_soft(root, (lx, ly - 0.012 * kk, 0.0), (0.05 * kk, 0.045 * kk, 0.022 * kk), 0.15)
                                  * smooth(0.024 * k_, 0.012 * k_, root[:, 2]))
            tr = L['toe']['r'] * L['paw_k'][lg[0]]       # the toes' own size (toe_centres: paw_k only)
            for i, c in enumerate(self.toe_centres(lg)):
                if hp:
                    # under each toe: a round pad on its underside
                    pads = np.maximum(pads, ell_soft(root, (c[0], c[1] + 0.1 * tr, c[2] - 0.95 * tr), (0.55 * tr, 0.6 * tr, 0.4 * tr), 0.2))
                    tips = np.maximum(tips, ell_soft(root, tuple(self.claw_root(lg, i) + v3((0.0, 0.1 * tr, 0.05 * tr))),
                                                     (0.62 * tr, 0.42 * tr, 0.58 * tr), 0.3))
                else:
                    pads = np.maximum(pads, ell_soft(root, (c[0], c[1] - 0.006 * kk, 0.0), (0.022 * kk, 0.024 * kk, 0.02 * kk), 0.2)
                                      * smooth(0.024 * k_, 0.012 * k_, root[:, 2]))
        rgb = HP.blend(rgb, tips * 0.9, col['cream_base'])
        rgb = HP.blend(rgb, pads, col[L.get('pad_colour', 'copper_base')])
        if self.G.get('lid_teal'):
            # the closed lid (sculpted under each lens) teal, under the dark lash line (the grown form's blink)
            rgb = HP.blend(rgb, smooth(0.02, 0.25, get('lid')), col['teal'])
        # the chest: a warm heart (young) or the grate's molten seams (grown)
        g, warm = self.glow_fields(root, cream, region, cseam, cfrac)
        rgb = HP.blend(rgb, warm * 0.8, col['glow_warm'])
        rgb = HP.blend(rgb, np.clip(warm - 0.45, 0, 1) * 1.4, col['glow_core'])
        seam_hex = self.G['glow'].get('seam_hex', col['glow_seam'])
        rgb = HP.blend(rgb, cseam * self.G['glow'].get('seam_paint', 0.0), seam_hex)
        if self.G['glow'].get('seam_core'):
            # hottest at the centre: the seams there run toward yellow
            rgb = HP.blend(rgb, cseam * ell_soft(root, self.G['glow']['centre'], tuple(r * 0.6 for r in self.G['glow']['radii']), 0.9) * 0.6,
                           col['glow_core'])
        nose = ell_soft(root, tuple(self.nose_c), tuple(r * 1.1 for r in self.G['nose_r']), 0.25)
        rgb = HP.blend(rgb, nose * 0.18, NOSE_HEX)
        # roughness and clear coat: a soft sheen on the scales, glossier on the spikes, the spade and the nose
        rough = np.where(on, 0.47 + 0.2 * edge + 0.1 * rootk, 0.6)
        rough = rough * (1 - cream) + (0.56 + 0.1 * bedge) * cream
        coat = np.where(on, 0.16 * (1 - edge) * (1 - rootk * 0.5) + 0.03, 0.04) * (1 - cream) + 0.05 * cream
        sk_rc = (0.42, 0.2) if SPg.get('saturated') else (0.34, 0.35)      # round 3: a satin bud, not a glassy one
        for m, r_, c_ in ((on_sp, 0.38, 0.28), (is_ruff * 1.0, 0.45, 0.14), (sk, *sk_rc), (nose, 0.52, 0.08), (pads, 0.3, 0.4)):
            rough = rough * (1 - m) + r_ * m
            coat = coat * (1 - m) + c_ * m
        glow = np.maximum(g, sk * ((0.03 + 0.34 * hot ** 2) if SPg.get('saturated') else (0.45 + 0.55 * hot)))
        glow = np.maximum(glow, sk * speck)
        return {'paint': rgb, 'rough': np.stack([np.ones(n), np.clip(rough, 0.05, 1), np.clip(coat, 0, 1)], axis=1), 'glow': np.clip(glow, 0, 1)}

    def fin_arrays(self, ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
        """Frills: orange, paler between the ribs, deeper at the ribs, a vein network, a deeper rim at the edge. Wings:
        orange, paler in each panel's middle (the light through them), ridges along the bones, a network of fine veins
        (4-details panel 4), a deeper trailing edge, and on the grown form an ember edge (grown-4-details panel 4)."""
        col = colours(pal)
        co, _vn = S.mesh_arrays(ob)
        n = len(co)
        k = self.G['k']
        side = S.attr_array(ob, 'wing_side').astype(np.float64)
        fan = S.attr_array(ob, 'fan').astype(np.float64)
        wuv = S.attr_array(ob, 'wing_uv').astype(np.float64)
        # round 2: a warmer, lighter membrane (translucent, lit through) under a clearly drawn vein network
        rgb = HP.blend(np.tile(lin(col['membrane']), (n, 1)), np.full(n, 0.22), col['membrane_lite'])
        Wg = self.G['wing']
        if np.abs(side).max() > 0.5:
            u, v = wuv[:, 1], wuv[:, 2]
            mid = np.sin(np.pi * np.clip(u, 0, 1)) * np.sin(np.pi * np.clip(v, 0, 1))
            rgb = HP.blend(rgb, mid * 0.35, col['membrane_lite'])
            rel = U.wing_relief(wuv, len(self.wings['fingers']))
            veins = self.wing_veins(co, wuv)
            rgb = HP.blend(rgb, (1 - mid) * 0.25, col['membrane_dark'])
            rgb = HP.blend(rgb, rel * 0.6, col['rib'])
            rgb = HP.blend(rgb, veins * 0.62, col['rib'])
            if self.G.get('ember'):
                e = smooth(0.84, 0.97, v)
                rgb = HP.blend(rgb, smooth(0.7, 0.86, v) * (1 - e) * 0.5, col['membrane_dark'])
                rgb = HP.blend(rgb, e * 0.85, col['ember'])
            else:
                rgb = HP.blend(rgb, smooth(0.86, 1.0, v) * 0.5, col['membrane_dark'])
            rough = 0.36 + 0.12 * smooth(0.6, 1.0, v) - 0.06 * rel
        else:
            u, v, rib = fan[:, 0], fan[:, 1], fan[:, 2]
            rgb = HP.blend(rgb, (1 - rib) * smooth(0.12, 0.5, u) * smooth(1.0, 0.7, u) * 0.3, col['membrane_lite'])
            if 'vein' in ob.data.attributes:
                veins = S.attr_array(ob, 'vein').astype(np.float64)
            else:
                veins = HP.cell_veins(co, 0.016 * k, seed=9, width=0.1) * smooth(0.12, 0.3, u)
            rgb = HP.blend(rgb, veins * 0.55, col['rib'])
            rgb = HP.blend(rgb, rib * (0.55 + 0.3 * smooth(0.2, 0.9, u)), col['rib'])
            tr_ = self.G['wing'].get('frill_teal', 0.3)
            rgb = HP.blend(rgb, smooth(tr_, 0.05, u) * 0.85, col['teal_lo'])
            edge = smooth(0.8, 1.0, u / np.maximum(self.frill_edge(v), 0.3))
            rgb = HP.blend(rgb, edge * 0.5, col['ember'] if self.G.get('ember') else col['membrane_dark'])
            rough = 0.38 + 0.12 * edge - 0.08 * rib
        rc = np.stack([np.ones(n), np.clip(rough + 0.06, 0.1, 1), np.full(n, 0.25)], axis=1)
        # a faint warmth through every membrane (the glow channel), stronger at the grown form's ember edge
        glow = np.full(n, Wg.get('glow', 0.0))
        if np.abs(side).max() > 0.5:
            glow = glow * (1 - 0.5 * rel) * (1 - 0.6 * veins)
            if self.G.get('ember'):
                glow = np.maximum(glow, smooth(0.86, 0.98, wuv[:, 2]) * Wg.get('ember_glow', 0.55))
        else:
            glow = glow * (1 - 0.6 * rib) * smooth(0.1, 0.35, u)
        return rgb, rc, glow

    def prop_arrays(self, ob: bpy.types.Object, pal: dict) -> tuple[np.ndarray, np.ndarray]:
        """Horns and claws copper (deeper in the horns' grooves and at the roots, polished paler toward the tips); the
        wings' arms teal, banded with scale rows; the finger bones orange-brown; the frill spines teal into orange."""
        col = colours(pal)
        n = len(ob.data.vertices)
        kind = int(round(float(S.attr_array(ob, 'pkind')[0])))
        t = S.attr_array(ob, 'pt').astype(np.float64)
        g = S.attr_array(ob, 'pg').astype(np.float64)
        if kind in (P_HORN, P_CLAW, P_WCLAW):
            rgb = np.tile(lin(col['copper_base']), (n, 1))
            rgb = HP.blend(rgb, g * 0.75, col['copper_dark'])
            rgb = HP.blend(rgb, smooth(0.3, 0.0, t) * 0.6, col['copper_dark'])
            rgb = HP.blend(rgb, smooth(0.5, 1.0, t) * 0.4, col['copper_lite'])
            rough = 0.34 + 0.16 * g
            coat = np.full(n, self.G['leg'].get('claw_coat', 0.35))
        elif kind == P_ARM:
            # round 2: a scaled teal leading edge (rows of small scales, each outlined), not a banded stick
            rgb = np.tile(lin(col['teal']), (n, 1))
            bands = 0.5 + 0.5 * np.cos(t * 2 * math.pi * self.G['wing']['arm_bands'])
            co, _vn = S.mesh_arrays(ob)
            cells = HP.cell_veins(co, 0.011 * self.G['k'], seed=13, width=0.12)
            rgb = HP.blend(rgb, bands ** 3 * 0.45, col['rim'])
            rgb = HP.blend(rgb, cells * 0.6, col['rim'])
            rgb = HP.blend(rgb, (1 - bands) ** 4 * (1 - cells) * 0.25, col['sheen'])
            rough = 0.48 + 0.15 * bands
            coat = np.full(n, 0.12)
        elif kind == P_SPINE:
            rgb = np.tile(lin(col['teal']), (n, 1))
            rgb = HP.blend(rgb, smooth(0.12, 0.45, t), col['rib'])
            rgb = HP.blend(rgb, smooth(0.6, 1.0, t) * 0.6, col['spike_tip'])
            rough = np.full(n, 0.42)
            coat = np.full(n, 0.25)
        else:
            rgb = np.tile(lin(col['finger']), (n, 1))
            rgb = HP.blend(rgb, smooth(0.25, 0.0, t) * 0.5, col['rib'])
            rough = np.full(n, 0.42)
            coat = np.full(n, 0.25)
        return rgb, np.stack([np.ones(n), np.clip(rough, 0.05, 1), coat], axis=1)

    def paint_sources(self, body_srcs: list[bpy.types.Object], fins: list[bpy.types.Object], props=()) -> None:
        for ob in body_srcs:
            a = self.body_arrays(ob, self.pal)
            S.set_colour_attr(ob, 'paint', a['paint'])
            S.set_colour_attr(ob, 'rough', a['rough'])
            S.add_attr(ob, 'glow', a['glow'])
        for ob in fins:
            rgb, rc, gl = self.fin_arrays(ob, self.pal)
            S.set_colour_attr(ob, 'paint', rgb)
            S.set_colour_attr(ob, 'rough', rc)
            S.add_attr(ob, 'glow', gl)
        for ob in props:
            rgb, rc = self.prop_arrays(ob, self.pal)
            S.set_colour_attr(ob, 'paint', rgb)
            S.set_colour_attr(ob, 'rough', rc)

    # ------------------------------------------------------------------------- paint (nodes: crisp face marks per pixel)
    @staticmethod
    def _ell(nb: NB, p, c, r, soft=0.08):
        q = nb.vmath('DIVIDE', nb.vmath('SUBTRACT', p, tuple(c)), tuple(r))
        return nb.smooth(nb.vmath('LENGTH', q), 1.0 + soft, 1.0 - soft)

    def brow_marks(self) -> list[tuple[tuple, tuple]]:
        """Each brow: a short thick dark arc above the eye (2-turnaround front), three overlapping ellipsoids."""
        out = []
        er = self.eye_r
        for s in (1, -1):
            c = self.eye_c[s]
            for dx, dz, r in self.G['brows']:
                x = c.x + dx * er * s
                z_ = c.z + dz * er
                out.append(((x, self.on_head(x, z_, -0.004 * self.G['k_face']), z_), tuple(q * er for q in r)))
        return out

    def body_material(self, name: str, attr: str, pal: dict, marks) -> bpy.types.Material:
        col = colours(pal)
        k = self.G['k_face']
        m, nb = new_mat(name)
        # the marks are drawn on the pre-carve surface ('root'): the scales' relief (up to ~1 cm) would break them up
        pos = nb.attribute('root').outputs['Vector']
        c = nb.attribute(attr).outputs['Color']
        brow = None
        if self.G.get('brow_arc'):
            # round 2: one continuous, thick, dark arched brow per eye (short line segments along the head's surface)
            from lib import marks as MK
            er = self.eye_r
            arc = self.G['brow_arc']
            segs = []
            for s in (1, -1):
                c0 = self.eye_c[s]
                pts = []
                for dx, dz, _t in arc:
                    x = c0.x + dx * er * s
                    zz_ = c0.z + dz * er
                    pts.append((x, self.on_head(x, zz_, -0.002 * self.G['k_face']), zz_))
                for (a, b), (ta, tb) in zip(zip(pts[:-1], pts[1:]), zip([q[2] for q in arc[:-1]], [q[2] for q in arc[1:]])):
                    segs.append(MK.line(nb, pos, a, b, 0.5 * (ta + tb) * er, soft=0.35))
            brow = MK.union(nb, segs)
        else:
            for bc, br in self.brow_marks():
                e = self._ell(nb, pos, bc, br, 0.35)
                brow = e if brow is None else nb.math('MAXIMUM', brow, e)
        c = nb.mix(brow, c, nb.rgb(C.lin(col['brow'])))
        bc, br = self.G['blush']
        blush = None
        for s in (1, -1):
            e = self._ell(nb, pos, (bc[0] * s, bc[1], bc[2]), br, 0.7)
            blush = e if blush is None else nb.math('MAXIMUM', blush, e)
        c = nb.mix(nb.math('MULTIPLY', blush, 0.5), c, nb.rgb(C.lin(col['blush'])))
        Nn = self.G['nostril']
        nos = None
        for s in (1, -1):
            e = self._ell(nb, pos, (Nn['dx'] * s, self.nose_c.y - 0.02 * k, self.nose_c.z + Nn['dz']), (Nn['r'] * 1.25, 0.03 * k, Nn['r'] * 0.7), 0.35)
            nos = e if nos is None else nb.math('MAXIMUM', nos, e)
        c = nb.mix(nos, c, nb.rgb(C.lin('#0E1E1D')))
        dots = None
        for s in (1, -1):
            for dx, dz in self.G['dots']:
                x = dx * s
                e = self._ell(nb, pos, (x, self.G['dots_y'] + abs(x) * 0.4, dz), (0.0026 * k, 0.05 * k, 0.0026 * k), 0.4)
                dots = e if dots is None else nb.math('MAXIMUM', dots, e)
        c = nb.mix(nb.math('MULTIPLY', dots, 0.35), c, nb.rgb(C.lin('#9C7A58')))
        mouth = nb.math('MULTIPLY', nb.attribute('mouth').outputs['Fac'], 1.3, clamp=True)
        c = nb.mix(mouth, c, nb.rgb(C.lin(MOUTH_HEX)))
        lid = nb.math('POWER', nb.attribute('lid').outputs['Fac'], 0.5)
        c = nb.mix(nb.math('MULTIPLY', lid, 0.18), c, nb.rgb((0.0, 0.0, 0.0)))
        lash = nb.math('MULTIPLY', nb.attribute('lash').outputs['Fac'], 1.3, clamp=True)
        c = nb.mix(lash, c, nb.rgb(C.lin(LASH_HEX)))
        em = nb.new('ShaderNodeEmission')
        nb.link(c, em.inputs['Color'])
        nb.output(em.outputs[0])
        return m

    # ------------------------------------------------------------------------- the rig
    def frill_axis(self) -> tuple[np.ndarray, np.ndarray, float]:
        F = self.G['frill']
        root = 0.5 * (v3(F['root_top']) + v3(F['root_bot']))
        tip = self.frill_point(1, np.array([1.0]), np.array([0.5]))[0]
        d = tip - root
        return root, HP.unit(d), float(np.linalg.norm(d))

    def rig_p(self) -> dict:
        R = self.G['rig']
        fr, fd, fl = self.frill_axis()
        tp = self.tail_points()
        out = {
            'hip': R['hip'], 'chest': R['chest'], 'head_c': tuple(self.head_c), 'head_r': R['head_r'],
            'ear_base': tuple(map(float, fr)), 'ear_dir': tuple(map(float, fd)), 'ear_len': fl,
            'tail_base': tp[0], 'tail_dir': tuple(map(float, HP.unit(v3(tp[1]) - v3(tp[0])))),
            'tail_len': float(HP.arc_lengths(np.array(tp))[-1]), 'tail_bones': self.G['tail']['bones'], 'tail_points': tp,
            'legs': {leg: (lx, ly, self.G['leg']['hip_z'][leg[0]]) for leg, (lx, ly) in self.legs.items()},
            'knee_back': R['knee_back'], 'ankle_z': R['ankle_z'], 'foot_len': R['foot_len'], 'leg_radius': R['leg_radius'],
            'stride': R['stride'], 'wings': self.wings,
            'props': [{'name': 'horns', 'parent': 'head', 'head': R['horn_bone'][0], 'tail': R['horn_bone'][1]}],
        }
        for key in ('neck_bones', 'neck_points', 'strike_style', 'jaw'):
            if key in R:
                out[key] = R[key]
        return out

    def jaw_weights(self, co: np.ndarray) -> np.ndarray:
        """Round 2: 0..1 per vertex, how much of the lower jaw's skin rides the jaw bone: below the smile line, from the
        mouth's corners forward to the chin, fading out down the throat (the strike's snap and the open smiles)."""
        M = self.G['mouth']
        k = self.G['k_face']
        mc = np.array(self.mouth_curve())
        x, y, z = co[:, 0], co[:, 1], co[:, 2]
        lip = np.interp(x, mc[:, 0], mc[:, 1], left=mc[0, 1], right=mc[-1, 1])
        if M.get('side'):
            # a long muzzle: the lip's height along its sides (by y), wherever the side line runs
            sy = np.array([q[0] for q in M['side']])
            sz = np.array([q[1] for q in M['side']])
            o = np.argsort(sy)
            lip_side = np.interp(y, sy[o], sz[o])
            lip = np.where(np.abs(x) > M['side_x'] * 0.6, lip_side, lip)
        J = self.G['jaw_skin']
        w = (smooth(lip + 0.002 * k, lip - 0.005 * k, z) * smooth(J['y0'], J['y1'], y) * smooth(lip - J['depth'], lip - 0.6 * J['depth'], z)
             * smooth(M['half'] * 1.15, M['half'] * 0.9, np.abs(x)))
        return w

    def jaw_region(self, co: np.ndarray, names: list[str]) -> list:
        if 'jaw' not in names or not self.G.get('jaw_skin'):
            return []
        w = self.jaw_weights(co)
        jm = w > 0.01
        return [(jm, {'jaw': w[jm], 'head': 1.0 - w[jm]})] if jm.any() else []

    @staticmethod
    def ear_weights(p: np.ndarray, u: np.ndarray) -> dict[str, np.ndarray]:
        """head -> ear.1 -> ear.2 along the frill's u: the root stays with the head, the fan's edge swings."""
        w2 = smooth(0.5, 0.95, u)
        w1 = (1 - w2) * smooth(0.12, 0.4, u)
        return {'head': 1 - w1 - w2, '1': w1, '2': w2}

    def body_weight_regions(self, co: np.ndarray, names: list[str]) -> list:
        z = self.zones(co)
        out = []
        m = (z['tail'] | (co[:, 1] > self.G['zone']['tail_y'] + 0.03 * self.G['k'])) & ~z['leg'] & (co[:, 2] > 0.12 * self.G['k'])
        if m.any():
            bones = [f'tail.{i + 1}' for i in range(self.G['tail']['bones'])]
            out.append((m, U.chain_weights(co[m], self.tail_points(), bones, 'hips', fade=(0.04, -0.1))))
        out += self.jaw_region(co, names)
        return out

    def fin_weight_regions(self, co: np.ndarray, attr, names: list[str]) -> list:
        hub = self.G['wing'].get('hub')
        if hub is None:
            regs = U.wing_fin_regions(co, attr, names, self.wings)
        else:
            side_, wuv = attr('wing_side'), attr('wing_uv')
            regs = []
            for s_ in (1, -1):
                on = np.abs(side_ - s_) < 0.1
                if on.any():
                    regs.append((on, U.wing_membrane_weights(wuv[on], self.wings, s_, hub=hub)))
        part = attr('fin_part')
        fan = attr('fan')
        for s, tag in ((1, 'L'), (-1, 'R')):
            on = np.abs(part - s) < 0.1
            if on.any():
                w = self.ear_weights(co[on], fan[on, 0])
                regs.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
        return regs

    def prop_weight_regions(self, co: np.ndarray, attr, names: list[str]) -> list:
        kind = np.round(attr('pkind')).astype(int)
        side = np.round(attr('pside')).astype(int)
        t = attr('pt').astype(np.float64)
        regs = []
        horn = kind == P_HORN
        if horn.any():
            regs.append(U.rigid(horn, 'prop.horns' if 'prop.horns' in names else 'head'))
        for leg, i in LEG_INDEX.items():
            m = (kind == P_CLAW) & (side == i)
            if m.any():
                regs.append(U.rigid(m, f'foot.{leg}'))
        for s, tag in ((1, 'L'), (-1, 'R')):
            m = (kind >= P_ARM) & (kind <= P_WCLAW) & (side == s)
            if m.any() and self.G['wing'].get('rigid_bones'):
                # round 3: by construction, not by distance (folded, the arm, forearm and fingers lie side by side, so
                # nearest-segment weights mixed them and the thick arm tore at the wrist when the wing opened): the arm
                # along its length, shoulder -> elbow -> wrist, bending softly at the elbow; each finger tube and the
                # leading edge rigid on their finger; the wrist claw on the forearm
                nm = U.wing_bone_names(self.wings, s)
                km, tm = kind[m], t[m]
                gm = np.round(attr('pg').astype(np.float64)[m]).astype(int)
                arm = (km == P_ARM) & (gm == 0)
                bend = smooth(0.42, 0.58, tm) * arm + (~arm)
                w = {nm[0]: np.where(arm, 1.0 - bend, 0.0), nm[1]: np.where(arm, bend, 0.0)}
                w[nm[1]] = np.where(km == P_WCLAW, 1.0, w[nm[1]])
                for k_ in range(len(self.wings['fingers'])):
                    w[nm[2 + k_]] = ((gm == k_ + 1) & (km != P_WCLAW)).astype(np.float64)
                regs.append((m, w))
            elif m.any():
                # round 2: a softer blend at the elbow (power 8 bent the arm like a stick in hit_heavy)
                regs.append((m, U.segment_weights(co[m], U.wing_limb_segments(self.wings, s), power=self.G['wing'].get('arm_power', 5))))
            m = (kind == P_SPINE) & (side == s)
            if m.any():
                w = self.ear_weights(co[m], t[m] * 0.95)
                regs.append((m, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
        return regs

    def uv_smooth_mask(self, co: np.ndarray) -> np.ndarray:
        """UV_SMOOTH's strength per lo_body vertex (round 3): the scaly body, legs, neck and tail smooth fully, so their
        lumps unwrap into far fewer, larger islands; the head partly; the face, the eyes' rims, the snout, the spikes'
        blades and the spade not at all (they unwrap well as they are, and their detail matters most)."""
        z = self.zones(co)
        m = np.ones(len(co))
        m = np.where(z['head'], 0.35, m)
        m = np.where(z['paw'], 0.5, m)
        m = np.where(z['face'] | z['muzzle'] | z['nose'] | (z['eye_d'] < self.eye_r * 1.8), 0.0, m)
        # the blades smooth too (nearly): left alone, each spike and lifted scale unwrapped into a few tiny islands, and
        # their margins left the grown form's atlas only 29% used (round 2's measure); squashed in the twin they join the
        # body's islands at a lower texel density, fine for their simple teal-to-orange paint
        # (the grown form's big dorsal plates squashed in the twin dragged the whole back's unwrap into smears: there the
        # blades keep the older rule, their bases smoothing and their tips not)
        on, t, _k = HP.blade_field(co, self.spikes(), pad=0.003 * self.G['k'])
        ub = self.G['scales'].get('uv_blade')
        if ub is None:
            m = m * (1.0 - on * smooth(0.05, 0.3, t))
        else:
            m = np.where(on > 0.5, np.maximum(m, ub), m)
        m = np.where(z['spade'] > 0.5, 0.25, m)
        return m

    # ------------------------------------------------------------------------- the shape preview
    def preview_colours(self, co: np.ndarray, vn: np.ndarray) -> np.ndarray:
        z = self.zones(co, vn)
        cream = self.cream_mask(co, z)
        col = colours(self.pal)
        rgb = lin(col['teal'])[None] * (1 - cream[:, None]) + lin(col['cream'])[None] * cream[:, None]
        P = self._plates
        if P.get('n') == len(co):
            rgb = HP.blend(rgb, P['on_s'] * smooth(0.8, 0.97, P['rho']) * 0.8 * (1 - cream), col['rim'])
            rgb = HP.blend(rgb, P['on_s'] * smooth(0.4, -0.95, P['ul']) * 0.5 * (1 - cream), col['root'])
            rgb = HP.blend(rgb, P['on_b'] * smooth(0.78, 0.97, P['rho']) * 0.55 * cream, col['cream_rim'])
        on_sp, t_sp, _k = HP.blade_field(co, self.spikes(), pad=0.003)
        rgb = HP.blend(rgb, smooth(0.3, 0.65, t_sp) * on_sp, col['spike_tip'])
        sp_on, _t = self.spade_field(co)
        rgb = HP.blend(rgb, smooth(0.2, 0.75, sp_on), col['orange'])
        gl = self.G['glow']
        rgb = HP.blend(rgb, ell_soft(co, gl['centre'], gl['radii'], 0.9) * cream * 0.6, col['glow_warm'])
        return rgb


CONTRACT = ('all_parts', 'body_extras', 'build_eye', 'eye_material', 'blink_pivot', 'carve', 'zones', 'decimate_keep', 'build_fins',
            'build_props', 'paint_sources', 'body_material', 'rig_p', 'body_weight_regions', 'fin_weight_regions',
            'prop_weight_regions', 'preview_colours', 'ear_weights')
EXTRAS = ('fin_arrays', 'prop_arrays', 'body_arrays', 'spikes', 'cream_mask', 'scale_flow', 'tail_points', 'eye_frame', 'on_head',
          'spade_field', 'frill_point', 'chevron_field', 'uv_smooth_mask')


def export(form: Form, ns: dict) -> None:
    """Put the form's contract functions into a recipe module's namespace (RECIPE.md's names)."""
    for name in CONTRACT + EXTRAS:
        ns[name] = getattr(form, name)
    ns['colours'] = colours
