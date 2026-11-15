"""Pluckrex's props: the ribbed fan crest (a sagittal fan of broad petals plus a halo of petals round the back of the
head: 2-turnaround front, side and back), the gold spines down the neck, back and tail, the grin's teeth, the dark
claws and (grown) the stone bracers (pluckrex_bracers.py). Every prop carries the same point attributes: `pt` (t along
0..1, q across -1..1, the facet shade), `gpart` (its kind), `anchor` (where its skin weights come from), `item`, `side`.
Metres; the monster faces -Y, Z is up, +X is its left."""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector

from lib import common as C
from lib import surface as S
from lib.surface import v3
from monsters.breeds import gloomgrin_rings as RG
from monsters.breeds.pluckrex_form import mirror, sd_parts, unit

P_CREST, P_SPINE, P_TOOTH_U, P_TOOTH_L, P_HCLAW, P_FCLAW, P_BRACER, P_CROWN = 1, 2, 3, 4, 5, 6, 7, 8
PROP_ATTRS = {'pt': 3, 'gpart': 1, 'anchor': 3, 'item': 1, 'side': 1}


def complete_attrs(ob: bpy.types.Object) -> bpy.types.Object:
    """Every prop carries the same point attributes (the build joins props keeping only the common ones)."""
    n = len(ob.data.vertices)
    for a, dim in PROP_ATTRS.items():
        if a not in ob.data.attributes:
            S.add_attr(ob, a, np.zeros(n) if dim == 1 else np.zeros((n, dim)))
    if 'UVMap' not in ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    return ob


# ============================================================================= the crest's petals
def _petal_rings(spec: dict, high: bool):
    """One petal: a broad, thin paddle from its root (inside the head) out to a round tip, with a raised rib down the
    middle of both faces. Returns (verts list, faces list, per-vertex (t, q, face))."""
    root, tip = v3(spec['root']), v3(spec['tip'])
    nrm = unit(spec['n'])
    d = unit(tip - root)
    e1 = unit(np.cross(nrm, d))
    e2 = unit(np.cross(d, e1))
    L = float(np.linalg.norm(tip - root))
    W, Th, rib, curl = spec['w'], spec['th'], spec.get('rib', 0.4), spec.get('curl', 0.0)
    rim = spec.get('rim', 0.0)
    nr = 26 if high else 12
    seg = 44 if high else 16
    ts = np.linspace(0.0, 0.985, nr)
    ts = 0.985 * (1.0 - (1.0 - ts / 0.985) ** 1.35)          # rings closer toward the round tip
    a = np.linspace(0.0, 2 * math.pi, seg, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    # round 2: a flatter, slab-like section (thick to its edges), so the raised rim bead and the rib both stand out
    ss = np.sign(sa) * np.abs(sa) ** 0.55
    verts, attrs = [], []
    for t in ts:
        if t <= 0.8:
            w = W * (0.42 + 0.58 * math.sin(0.5 * math.pi * min(1.0, t / 0.68)))
        else:
            w = W * math.sqrt(max(0.0, 1.0 - ((t - 0.8) / 0.2) ** 2))
        th = Th * (1.0 - 0.35 * t) * (w / W) ** 0.35
        c = root + d * (L * t) + e2 * (curl * L * t * t)
        bump = (1.0 + rib * np.exp(-(ca / 0.16) ** 2) * min(1.0, t / 0.3) * (w / W)
                + rim * np.exp(-((np.abs(ca) - 0.9) / 0.08) ** 2) * min(1.0, t / 0.25))
        for j in range(seg):
            q = ca[j]
            p = c + e1 * (w * 0.5 * q) + e2 * (th * 0.5 * ss[j] * bump[j])
            verts.append(p)
            attrs.append((t, q, 1.0 if sa[j] >= 0 else -1.0))
    faces = []
    for i in range(nr - 1):
        for j in range(seg):
            jn = (j + 1) % seg
            faces.append((i * seg + j, i * seg + jn, (i + 1) * seg + jn, (i + 1) * seg + j))
    c0 = len(verts)
    verts.append(root)
    attrs.append((0.0, 0.0, 0.0))
    for j in range(seg):
        faces.append((c0, (j + 1) % seg, j))
    c1 = len(verts)
    verts.append(root + d * L + e2 * (curl * L))
    attrs.append((1.0, 0.0, 0.0))
    last = (nr - 1) * seg
    for j in range(seg):
        faces.append((c1, last + j, last + (j + 1) % seg))
    return verts, faces, attrs, e1, e2


def petal_specs(F) -> list[dict]:
    """Each petal: root, tip, face normal n, width, thickness. The sagittal fan's petals stand in the mid-plane (broad
    from the side, a tall rib from the front); the halo's face forward round the back of the head (broad from the
    front and the back)."""
    Cr = F.G['crest']
    out = []
    fan = Cr['fan']
    piv = v3(fan['pivot'])
    for i, (ang, ln) in enumerate(zip(fan['angles'], fan['lens'])):
        a = math.radians(ang)
        d = v3((0.0, math.sin(a), math.cos(a)))
        dx = fan.get('stagger', 0.006) * F.k * (1 if i % 2 else -1)
        out.append({'root': piv + d * (ln * fan['root']) + v3((dx, 0, 0)), 'tip': piv + d * ln + v3((dx, 0, 0)),
                    'n': (1.0, 0.0, 0.0), 'w': fan['w'], 'th': fan['th'], 'rib': Cr.get('rib', 0.4), 'curl': fan.get('curl', 0.0),
                    'rim': Cr.get('rim', 0.0),
                    'kind': 'fan', 'i': i})
    halo = Cr['halo']
    piv = v3(halo['pivot'])
    tb = math.tan(math.radians(halo['back']))
    for i, (ang, ln) in enumerate(zip(halo['angles'], halo['lens'])):
        a = math.radians(ang)
        back = tb * (1.0 + halo.get('back_low', 0.0) * max(0.0, abs(ang) - 90.0) / 45.0)
        d = unit((math.sin(a), back, math.cos(a)))
        tg = v3((math.cos(a), 0.0, -math.sin(a)))
        n = unit(np.cross(d, tg))
        if n[1] > 0:
            n = -n
        out.append({'root': piv + d * (ln * halo['root']), 'tip': piv + d * ln, 'n': tuple(n), 'w': halo['w'], 'th': halo['th'],
                    'rib': Cr.get('rib', 0.4), 'curl': halo.get('curl', 0.0), 'kind': 'halo', 'i': i, 'rim': Cr.get('rim', 0.0)})
    return out


def build_crest(name: str, F, high: bool) -> bpy.types.Object:
    verts, faces, at, anch, items = [], [], [], [], []
    for ii, sp in enumerate(petal_specs(F)):
        v, f, a, _e1, _e2 = _petal_rings(sp, high)
        b = len(verts)
        verts += v
        faces += [tuple(i + b for i in fc) for fc in f]
        at += a
        anch += [tuple(sp['root'])] * len(v)
        items += [float(ii)] * len(v)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in verts], [], faces)
    me.update()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    n = len(verts)
    at = np.array(at)
    S.add_attr(ob, 'pt', at)
    S.add_attr(ob, 'gpart', np.full(n, float(P_CREST)))
    S.add_attr(ob, 'anchor', np.array(anch).reshape(n, 3))
    S.add_attr(ob, 'item', np.array(items))
    S.add_attr(ob, 'side', np.zeros(n))
    ob['prop'] = 'crest'
    return ob


# ============================================================================= the body's surface (ray marching)
def surface_point(F, origin, direction, parts=None, reach: float = 1.0, step: float = 0.0015):
    """The first point where a ray from `origin` (outside) enters the body's parts, and the outward normal there."""
    parts = parts if parts is not None else F.all_parts()
    o, d = v3(origin), unit(direction)
    s = np.arange(0.0, reach, step)
    pts = o[None] + d[None] * s[:, None]
    sd = sd_parts(pts, parts)
    hit = np.nonzero(sd < 0)[0]
    if not len(hit):
        return None, None
    p = pts[hit[0]]
    e = 0.002
    g = np.array([sd_parts((p + v3(dv))[None], parts)[0] - sd_parts((p - v3(dv))[None], parts)[0]
                  for dv in ((e, 0, 0), (0, e, 0), (0, 0, e))])
    return p, unit(g)


_SMILE: dict = {}


def smile_points(F) -> dict:
    """{side: [points]}: the smile's crease from each corner of the grin up and back into the cheek, on the skin."""
    if id(F) in _SMILE:
        return _SMILE[id(F)]
    M = F.mouth()
    ok = [i for i in range(len(M['xs'])) if np.isfinite(M['pu'][i]).any()]
    out = {1: [], -1: []}
    if ok and F.G.get('smile'):
        i = ok[-1]
        j = np.nonzero(np.isfinite(M['pu'][i]))[0]
        jr = j.max()
        r = M['rs'][jr]
        a = math.radians(0.5 * (M['pu'][i, jr] + M['pl'][i, jr]))
        corner = v3((M['xs'][i], F.HINGE[1] - r * math.cos(a), F.HINGE[2] - r * math.sin(a)))
        parts = F.head_parts()
        for s in (1, -1):
            for off in F.G['smile']:
                q = (corner + v3(off) * F.k) * v3((s, 1.0, 1.0))
                dout = unit(v3((0.7 * s, -0.7, 0.1)))
                hit, _n = surface_point(F, q + dout * 0.08 * F.k, -dout, parts, reach=0.25 * F.k, step=0.0008)
                out[s].append(hit if hit is not None else q)
    _SMILE[id(F)] = out
    return out


def smile_dist(F, p: np.ndarray) -> np.ndarray:
    """Distance (metres) from each point to the nearest smile crease."""
    d = np.full(len(p), 9.0)
    for s, pts in smile_points(F).items():
        for a, b in zip(pts[:-1], pts[1:]):
            ab = b - a
            t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
            d = np.minimum(d, np.linalg.norm(p - (a + t[:, None] * ab), axis=1))
    return d


# ============================================================================= the gold spines
def spine_items(F, high: bool) -> list[dict]:
    """Rounded gold spines in one row down the mid-line: the nape, the back and the tail's top (2-turnaround side and
    back), each seated on the skin, leaning back, longer along the spine than across."""
    Sp = F.G['spines']
    parts = F.all_parts()
    out = []
    for i, it in enumerate(Sp['items']):
        o, dirn = v3(it['from']), unit(it['dir'])
        p, nrm = surface_point(F, o - dirn * 0.0, dirn, parts, reach=0.6 * F.k + 0.4)
        if p is None:
            C.log(f'pluckrex: spine {i} missed the body from {tuple(o)}')
            continue
        nrm = unit(nrm * v3((0.0, 1.0, 1.0)) + v3((0.0, 0.0, 1e-6)))           # in the mid-plane
        h = it['h']
        back = unit(nrm + v3((0.0, it.get('tilt', 0.6), -0.15 * it.get('tilt', 0.6))))
        along = unit(np.cross(v3((1.0, 0.0, 0.0)), back))
        if along[1] < 0:
            along = -along
        r0 = h * it.get('base', 0.42)
        base = p - back * (0.35 * h)
        tip = p + back * h + along * (it.get('hook', 0.18) * h)
        mid = p + back * (0.55 * h)
        n_ = 7 if high else 5
        path = RG.bezier(base, mid, tip, n_)
        tt = np.linspace(0.0, 1.0, n_)
        prof = 1.0 - (np.clip(tt - 0.3, 0.0, None) / 0.7) ** 1.4
        radii = list(r0 * np.clip(prof, 0.0, 1.0) ** 0.8)
        radii[-2] = max(radii[-2], r0 * 0.12)
        radii[-1] = 0.0
        out.append({'path': path, 'radii': radii, 'sides': 18 if high else 8, 'aspect': (1.0, it.get('flat', 0.62)),
                    'up': tuple(along), 'seed': 500 + i, 'kind': P_SPINE, 'anchor': tuple(p), 'cap': True})
    return out


# ============================================================================= the teeth
def teeth_items(F, high: bool) -> list[dict]:
    """The grin's small, rounded teeth: a row hanging from the palate's rim and a few smaller ones standing on the jaw's
    (1-hero, 4-details panel 1), seated a little behind the lips."""
    T = F.G['teeth']
    M = F.mouth()
    k = F.k
    hw = F.mouth_half_width()
    out = []
    for row, kind in (('upper', P_TOOTH_U), ('lower', P_TOOTH_L)):
        n = T[row]['n']
        span = T[row]['span'] * hw
        xs = np.linspace(-span, span, n)
        for j, x in enumerate(xs):
            i = int(np.clip(np.searchsorted(M['xs'], abs(x)), 0, len(M['xs']) - 1))
            ok = np.nonzero(np.isfinite(M['pu'][i]))[0]
            if not len(ok):
                continue
            jr = ok[np.argmin(np.abs(M['rs'][ok] - (M['rs'][ok.max()] - T['inset'] * k)))]
            r = M['rs'][jr]
            ang = M['pu'][i, jr] if row == 'upper' else M['pl'][i, jr]
            a = math.radians(ang)
            root = v3((x, F.HINGE[1] - r * math.cos(a), F.HINGE[2] - r * math.sin(a)))
            ephi = v3((0.0, math.sin(a), -math.cos(a)))           # toward the floor
            d = ephi if row == 'upper' else -ephi
            d = unit(d + v3((0.0, -T['fwd'], 0.0)))
            gap = r * math.radians(M['pl'][i, jr] - M['pu'][i, jr])
            edge = 1.0 - 0.45 * (abs(x) / max(span, 1e-6)) ** 2
            L = min(T[row]['len'] * k * edge, 0.42 * gap)
            rr = T[row]['r'] * k * (0.8 + 0.2 * edge)
            # round 3: small rounded teeth set into the gums (half the tooth buried), never fangs or rivets
            base = root - d * (0.9 * L)
            path = [base + d * (1.9 * L * t) for t in (0.0, 0.4, 0.62, 0.78, 0.9, 0.97, 1.0)]
            radii = [rr, rr, rr * 0.96, rr * 0.82, rr * 0.6, rr * 0.33, 0.0]
            out.append({'path': path, 'radii': radii, 'sides': 12 if high else 6, 'aspect': (1.0, 0.78), 'up': (1.0, 0.0, 0.0),
                        'seed': 900 + j + (50 if row == 'lower' else 0), 'kind': kind, 'anchor': tuple(root), 'cap': True})
    return out


# ============================================================================= the claws
def claw_items(F, high: bool) -> list[dict]:
    """Dark, glossy claws: one on each finger curling toward the palm, one big one on each toe curving down to the
    ground (1-hero, 4-details panel 3)."""
    A, L = F.G['arm'], F.G['leg']
    out = []
    sides = 14 if high else 7
    for s in (1, -1):
        _w, _h, _ac, palm = F.hand_frame(s)
        for i, (b, t, r) in enumerate(F.fingers(s)):
            d = unit(v3(t - b))
            ln, cr = A['claw']
            base = v3(t) - d * (0.6 * r)
            # round 3: short, thick, blunt dark claws matching the feet's (long pale claws read as a held stick)
            path = RG.bezier(base, base + d * (0.6 * ln), base + d * ln + v3(palm) * (0.35 * ln), 6 if high else 4)
            radii = ([cr, cr * 0.97, cr * 0.85, cr * 0.62, cr * 0.32, 0.0] if high else [cr, cr * 0.8, cr * 0.4, 0.0])
            out.append({'path': path, 'radii': radii, 'sides': sides, 'aspect': (1.0, 0.8), 'up': tuple(palm),
                        'seed': 300 + i + 10 * (s > 0), 'kind': P_HCLAW, 'anchor': tuple(t), 'cap': True, 'side': float(s)})
        for i, tc in enumerate(F.toe_centres(s)):
            d = v3(F.toe_dir(s, L['toe_dx'][i]))
            ln, cr = L['claw']
            base = v3(tc) + d * (L['toe_r'][1] * 0.55) + v3((0.0, 0.0, 0.004 * F.k))
            tip = base + d * ln
            tip[2] = 0.003 * F.k
            ctrl = base + d * (0.65 * ln)
            ctrl[2] = base[2] + 0.004 * F.k
            path = RG.bezier(base, ctrl, tip, 8 if high else 5)
            # round 2: big, blunt, rounded claws (2-turnaround, 4-details panel 3), not needles
            radii = ([cr, cr, cr * 0.97, cr * 0.9, cr * 0.78, cr * 0.6, cr * 0.36, 0.0] if high else [cr, cr * 0.95, cr * 0.75, cr * 0.4, 0.0])
            out.append({'path': path, 'radii': radii, 'sides': sides, 'aspect': (1.0, 0.8), 'up': (0.0, 0.0, 1.0),
                        'seed': 400 + i + 10 * (s > 0), 'kind': P_FCLAW, 'anchor': tuple(tc), 'cap': True, 'side': float(s)})
    return out


def ringed(name: str, items: list[dict], flat: bool = False) -> bpy.types.Object:
    ob = RG.ringed_object(name, items, flat=flat, extra_attrs=('side',))
    if not flat:
        ob.data.shade_smooth()
    return ob
