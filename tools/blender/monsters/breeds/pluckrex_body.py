"""Pluckrex's Form: one form's numbers (young or grown) turned into rounded parts, frames and the open grin's geometry.
Zones (the paint and weight masks) are in pluckrex_zones.py. Metres; the monster faces -Y, Z is up, +X is its left."""
from __future__ import annotations

import math

import numpy as np
from mathutils import Matrix, Vector

from lib.mesh import Part
from lib.surface import v3
from monsters.breeds import pluckrex_form as PF
from monsters.breeds.pluckrex_form import _ell, mirror, rot_x, sd_parts, unit


class Form:
    """G keys: 'k' (detail size vs the young form), 'head' {cranium, face, brow, snout, bridge, nose, cheek, jaw,
    jawside, chin, throat (each (centre, radii)), hinge, jaw_open}, 'eye' {x, z, r, shape, depth, out}, 'neck' [(c, r)],
    'torso' [(name, c, r)], 'leg' {...}, 'arm' {...}, 'tail' {pts, rad}, 'cream', 'crest', 'spines', 'rig', ..."""

    def __init__(self, G: dict):
        self.G = G
        self.k = float(G.get('k', 1.0))
        H = G['head']
        self.H = H
        self.HEAD_C = v3(H['cranium'][0])
        self.HEAD_R = v3(H['cranium'][1])
        self.HINGE = v3(H['hinge'])
        self.JAW_OPEN = float(H['jaw_open'])
        E = G['eye']
        self.EYE_R = float(E['r'])
        self.EYE_SHAPE = tuple(E.get('shape', (1.0, 1.05)))
        self.EYE_DEPTH = tuple(E.get('depth', (0.5, 0.18)))
        self.EYE_C = {s: self._eye_centre(s) for s in (1, -1)}
        self.TAIL_PTS = [tuple(map(float, p)) for p in G['tail']['pts']]
        self.TAIL_RAD = [float(r) for r in G['tail']['rad']]
        self._mouth = None

    # ------------------------------------------------------------------ the head
    def jaw_part(self, name: str, e, mirror_: bool = False) -> Part:
        """A lower-jaw part given closed, turned open about the hinge."""
        c = rot_x(e[0], self.HINGE, self.JAW_OPEN)[0]
        r0 = float(e[2][0]) if len(e) > 2 else 0.0
        return _ell(name, (tuple(c), e[1]), mirror_, rot=(self.JAW_OPEN + r0, 0.0, 0.0))

    def head_parts(self) -> list[Part]:
        H = self.H
        ps = [_ell('cranium', H['cranium']), _ell('face', H['face'])] + ([_ell('brow', H['brow'], True)] if H.get('brow') else []) + [
              _ell('snout', H['snout']), _ell('bridge', H['bridge']), _ell('nose', H['nose'])]
        ps += [_ell('upperlip', H['upperlip'], True)] if H.get('upperlip') else []
        ps += [_ell('cheek', H['cheek'], True)] if H.get('cheek') else []
        ps += [self.jaw_part('jaw', H['jaw']), self.jaw_part('jawside', H['jawside'], True), self.jaw_part('chin', H['chin'])]
        ps += [self.jaw_part('tongue', H['tongue'])] if H.get('tongue') else []
        ps += [_ell('gullet', H['gullet'])] if H.get('gullet') else []
        if H.get('nape'):
            ps.append(_ell('nape', H['nape']))
        return ps

    def upper_parts(self) -> list[Part]:
        """The upper jaw (snout, nose, bridge): the palate is its underside."""
        H = self.H
        return [_ell('snout', H['snout']), _ell('bridge', H['bridge']), _ell('nose', H['nose'])] + (
            [_ell('upperlip', H['upperlip'], True)] if H.get('upperlip') else [])

    def lower_parts(self) -> list[Part]:
        H = self.H
        return [self.jaw_part('jaw', H['jaw']), self.jaw_part('jawside', H['jawside'], True), self.jaw_part('chin', H['chin'])] + (
            [self.jaw_part('tongue', H['tongue'])] if H.get('tongue') else [])

    def neck_parts(self) -> list[Part]:
        out = []
        for i, e in enumerate(self.G['neck']):
            out.append(_ell(f'neck{i}', e))
        out.append(_ell('throat', self.H['throat']))
        return out

    def torso_parts(self) -> list[Part]:
        return [_ell(n, (c, r)) for n, c, r in self.G['torso']]

    # ------------------------------------------------------------------ the eyes
    def _front_y(self, c, r, x: float, z: float) -> float:
        kk = 1.0 - (x / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
        return c[1] - r[1] * math.sqrt(kk) if kk > 0 else 9.0

    def _eye_centre(self, s: int) -> Vector:
        E = self.G['eye']
        x, z = float(E['x']), float(E['z'])
        # the front of the whole head (the union) at the eye: the lens sits on it, never sunk behind a cheek or brow
        ys = np.linspace(-0.8 * self.k, self.HEAD_C[1], 600)
        pts = np.stack([np.full(len(ys), x), ys, np.full(len(ys), z)], axis=1)
        hit = np.nonzero(sd_parts(pts, self.head_parts()) < 0)[0]
        y = float(ys[hit[0]]) if len(hit) else self._front_y(self.H['face'][0], self.H['face'][1], x, z)
        return Vector((x * s, y + float(E.get('sink', 0.004)) * self.k, z))

    def head_normal(self, c) -> Vector:
        c = Vector(c)
        h = Vector(self.H['face'][0])
        r = self.H['face'][1]
        return Vector(((c.x - h.x) / r[0] ** 2, (c.y - h.y) / r[1] ** 2, (c.z - h.z) / r[2] ** 2)).normalized()

    def eye_frame(self, s: int):
        """Centre, right, up and look axes: the eye looks forward and a little out, wrapping the face's curve."""
        c = self.EYE_C[s]
        out = float(self.G['eye'].get('out', 0.45))
        look = (self.head_normal(c) * out + Vector((0, -1, 0)) * (1.0 - out)).normalized()
        look = (look + Vector((0, 0, float(self.G['eye'].get('up', 0.03))))).normalized()
        xax = Vector((0, 0, 1)).cross(look).normalized()
        yax = look.cross(xax).normalized()
        return c, xax, yax, look

    def eye_matrix(self, s: int) -> Matrix:
        c, xax, yax, look = self.eye_frame(s)
        m = Matrix((xax, yax, look)).transposed().to_4x4()
        return Matrix.Translation(c - look * (self.EYE_R * self.EYE_DEPTH[1])) @ m

    # ------------------------------------------------------------------ limbs
    def hand_frame(self, s: int):
        """Wrist, the hand's direction, across (toward the front) and the palm's normal (toward the body's mid-line)."""
        A = self.G['arm']
        w = Vector(mirror(A['wrist'], s))
        h = (Vector(mirror(A['hand'], s)) - w).normalized()
        across = h.cross(Vector((0, 0, 1)))
        if across.y > 0:
            across = -across
        across.normalize()
        palm = across.cross(h).normalized()
        if palm.x * s > 0:
            palm = -palm
        return w, h, across, palm

    def fingers(self, s: int) -> list[tuple[Vector, Vector, float]]:
        """(base, tip, radius) of the three fingers, fanned and curled a little toward the palm."""
        A = self.G['arm']
        w, h, across, palm = self.hand_frame(s)
        base = w + h * A['palm_len']
        out = []
        for a, ln in zip(A['finger_ang'], A['finger_len']):
            r = math.radians(a)
            d = (h * math.cos(r) + across * math.sin(r)).normalized()
            d = (d + palm * A.get('curl', 0.35)).normalized()
            b = base + across * (A['palm_w'] * math.sin(r) / 0.5)
            out.append((b, b + d * ln, A['finger_r']))
        return out

    def toe_centres(self, s: int) -> list[Vector]:
        L = self.G['leg']
        fc = Vector(mirror(L['foot'][0], s))
        a = math.radians(L['yaw'] * s)
        ca, sa = math.cos(a), math.sin(a)
        out = []
        for dx in L['toe_dx']:
            lx, ly = dx * s, (L['toe_y'] - L['foot'][0][1]) + abs(dx) * L.get('toe_back', 0.35)
            out.append(Vector((fc.x + lx * ca - ly * sa, fc.y + lx * sa + ly * ca, L['toe_z'])))
        return out

    def toe_dir(self, s: int, dx: float) -> Vector:
        L = self.G['leg']
        a = math.radians(L['yaw'] * s)
        d = Vector((dx * L.get('splay', 0.9) * s, -1.0, 0.0))
        return Vector((d.x * math.cos(a) - d.y * math.sin(a), d.x * math.sin(a) + d.y * math.cos(a), 0.0)).normalized()

    def limb_parts(self) -> list[Part]:
        A, L = self.G['arm'], self.G['leg']
        ps: list[Part] = []
        for s, tag in ((1, ''), (-1, '.R')):
            m = lambda p, s=s: mirror(p, s)
            ps += [
                Part(f'upperarm{tag}', 'tube', loc=m(A['shoulder']), to=m(A['elbow']), radius=A['r'][0], r2=A['r'][1]),
                Part(f'elbow{tag}', 'sphere', loc=m(A['elbow']), radius=A['r'][1] * 1.02),
                Part(f'forearm{tag}', 'tube', loc=m(A['elbow']), to=m(A['wrist']), radius=A['r'][2], r2=A['r'][3]),
            ]
            w, h, across, palm = self.hand_frame(s)
            ps.append(Part(f'palm{tag}', 'sphere', loc=tuple(w + h * (A['palm_len'] * 0.55)), radius=1.0,
                           scale=tuple(A['palm_size']), rot=PF.basis_euler(palm, h)))
            for i, (b, t, r) in enumerate(self.fingers(s)):
                ps.append(Part(f'finger{i}{tag}', 'capsule', loc=tuple(b), to=tuple(t), radius=r))
            th = L['thigh']
            ps.append(Part(f'thigh{tag}', 'sphere', loc=m(th[0]), radius=1.0, scale=tuple(th[1]), rot=tuple(th[2]) if s > 0 else
                           (th[2][0], -th[2][1], -th[2][2])))
            ps += [
                Part(f'shin{tag}', 'tube', loc=m(L['knee']), to=m(L['ankle']), radius=L['shin_r'][0], r2=L['shin_r'][1]),
                Part(f'heel{tag}', 'sphere', loc=m(L['heel'][0]), radius=1.0, scale=tuple(L['heel'][1])),
                Part(f'foot{tag}', 'sphere', loc=m(L['foot'][0]), radius=1.0, scale=tuple(L['foot'][1]), rot=(0.0, 0.0, L['yaw'] * s)),
            ]
            for i, t in enumerate(self.toe_centres(s)):
                d = self.toe_dir(s, L['toe_dx'][i])
                yaw = math.degrees(math.atan2(-d.x, -d.y))
                ps.append(Part(f'toe{i}{tag}', 'sphere', loc=tuple(t), radius=1.0, scale=tuple(L['toe_r']), rot=(0.0, 0.0, -yaw)))
        return ps

    def tail_parts(self) -> list[Part]:
        P, R = self.TAIL_PTS, self.TAIL_RAD
        return [Part(f'tail{i}', 'tube', loc=P[i], to=P[i + 1], radius=R[i], r2=max(R[i + 1], 0.004)) for i in range(len(P) - 1)]

    def all_parts(self) -> list[Part]:
        return self.head_parts() + self.neck_parts() + self.torso_parts() + self.limb_parts() + self.tail_parts()

    def tail_param(self, p: np.ndarray):
        return PF.polyline_param(p, self.TAIL_PTS, self.TAIL_RAD)

    # ------------------------------------------------------------------ the open grin
    def mouth(self) -> dict:
        """The mouth cavity measured on the parts, per |x| sample: for each radius r from the hinge (in the y-z plane)
        the palate's angle (phi_u, degrees below the forward horizontal) and the floor's (phi_l); the lips' radius
        (r_lip) and the corners' (r_in)."""
        if self._mouth is not None:
            return self._mouth
        up, lo = self.upper_parts(), self.lower_parts()
        allh = self.head_parts()
        xs = np.linspace(0.0, 0.26 * self.k, 40)
        rs = np.linspace(0.01, 0.42, 120) * self.k
        ph = np.radians(np.linspace(-25.0, 70.0, 191))
        hy, hz = self.HINGE[1], self.HINGE[2]
        PU = np.full((len(xs), len(rs)), np.nan)
        PL = np.full((len(xs), len(rs)), np.nan)
        for i, x in enumerate(xs):
            R, A = np.meshgrid(rs, ph, indexing='ij')
            pts = np.stack([np.full(R.size, x), hy - R.ravel() * np.cos(A.ravel()), hz - R.ravel() * np.sin(A.ravel())], axis=1)
            iu = (sd_parts(pts, up) < 0).reshape(R.shape)
            il = (sd_parts(pts, lo) < 0).reshape(R.shape)
            ia = (sd_parts(pts, allh) < 0).reshape(R.shape)
            for j in range(len(rs)):
                ju = np.nonzero(iu[j])[0]
                jl = np.nonzero(il[j])[0]
                if not len(ju) or not len(jl):
                    continue
                a, b = ju.max(), jl.min()           # the palate's lowest solid angle, the floor's highest
                if b <= a + 1 or ia[j, a + 1:b].any():
                    continue                         # closed here (a corner or behind the cavity)
                PU[i, j], PL[i, j] = math.degrees(ph[a]), math.degrees(ph[b])
        self._mouth = {'xs': xs, 'rs': rs, 'pu': PU, 'pl': PL}
        return self._mouth

    def mouth_coords(self, p: np.ndarray):
        """(r, phi in degrees, palate angle, floor angle) per point, the angles NaN where the mouth is closed."""
        M = self.mouth()
        dy = p[:, 1] - self.HINGE[1]
        dz = p[:, 2] - self.HINGE[2]
        r = np.hypot(dy, dz)
        phi = np.degrees(np.arctan2(-dz, -dy))
        ix = np.clip(np.searchsorted(M['xs'], np.abs(p[:, 0])), 0, len(M['xs']) - 1)
        jr = np.clip(np.searchsorted(M['rs'], r), 0, len(M['rs']) - 1)
        return r, phi, M['pu'][ix, jr], M['pl'][ix, jr]

    def lip_r(self, x: float) -> float:
        """The lips' radius from the hinge at |x| (the cavity's front), or 0 where there is no opening."""
        M = self.mouth()
        i = int(np.clip(np.searchsorted(M['xs'], abs(x)), 0, len(M['xs']) - 1))
        ok = np.nonzero(np.isfinite(M['pu'][i]))[0]
        return float(M['rs'][ok.max()]) if len(ok) else 0.0

    def mouth_smooth(self, ax: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Per |x| (interpolated, smooth): the palate's and the floor's median angles, the lips' radius and the corners'
        (the innermost open radius); NaN-free (0 radius beyond the mouth's half width)."""
        M = self.mouth()
        if 'sm' not in M:
            pu, pl, rl, ri = [], [], [], []
            for i in range(len(M['xs'])):
                ok = np.isfinite(M['pu'][i])
                if ok.any():
                    pu.append(float(np.median(M['pu'][i][ok])))
                    pl.append(float(np.median(M['pl'][i][ok])))
                    rl.append(float(M['rs'][ok].max()))
                    ri.append(float(M['rs'][ok].min()))
                else:
                    pu.append(pu[-1] if pu else 0.0)
                    pl.append(pl[-1] if pl else 0.0)
                    rl.append(0.0)
                    ri.append(0.0)
            ker = np.array([0.25, 0.5, 0.25])
            sm = [np.convolve(np.pad(np.array(a), 1, mode='edge'), ker, mode='valid') for a in (pu, pl)]
            M['sm'] = (sm[0], sm[1], np.array(rl), np.array(ri))
        pu, pl, rl, ri = M['sm']
        return (np.interp(ax, M['xs'], pu), np.interp(ax, M['xs'], pl), np.interp(ax, M['xs'], rl), np.interp(ax, M['xs'], ri))

    def lip_rs(self, ax: np.ndarray) -> np.ndarray:
        """lip_r for many |x| at once (interpolated between the samples)."""
        M = self.mouth()
        if 'lip' not in M:
            M['lip'] = np.array([self.lip_r(x) for x in M['xs']])
        return np.interp(ax, M['xs'], M['lip'])

    def mouth_half_width(self) -> float:
        M = self.mouth()
        ok = [x for i, x in enumerate(M['xs']) if np.isfinite(M['pu'][i]).any()]
        return float(max(ok)) if ok else 0.0
