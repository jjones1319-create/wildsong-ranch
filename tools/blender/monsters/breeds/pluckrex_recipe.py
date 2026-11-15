"""Pluckrex's recipe functions (breeds/RECIPE.md), shared by both forms: `export(F, globals())` fills a form's module
(pluckrex_ultra.py, pluckrex_grown_ultra.py) with every hook the build calls, made from its Form."""
from __future__ import annotations

import math

import numpy as np

from lib import surface as S
from lib import ultra as U
from lib.surface import smooth, v3
from monsters.breeds import pluckrex_face as FC
from monsters.breeds import pluckrex_hide as HD
from monsters.breeds import pluckrex_paint as PA
from monsters.breeds import pluckrex_props as PR
from monsters.breeds import pluckrex_zones as Z
from monsters.breeds.pluckrex_form import mirror


def jaw_weight(F, p: np.ndarray, z: dict | None = None) -> np.ndarray:
    """0..1: the lower jaw's skin, below the grin's mid-line (crisp across the open mouth), fading behind the corners
    toward the hinge, down the throat and out on the cheeks."""
    k = F.k
    r, phi, _pu, _pl = F.mouth_coords(p)
    pu, pl, _rl, _ri = F.mouth_smooth(np.abs(p[:, 0]))
    mid = 0.5 * (pu + pl)
    hw = F.mouth_half_width()
    w = (smooth(mid - 3.0, mid + 3.0, phi) * smooth(F.HINGE[1] + 0.005 * k, F.HINGE[1] - 0.05 * k, p[:, 1])
         * smooth(F.HINGE[2] - 0.17 * k, F.HINGE[2] - 0.11 * k, p[:, 2]) * smooth(hw * 1.7, hw * 1.3, np.abs(p[:, 0])))
    head = (z['head'] if z is not None else Z.zones(F, p)['head'])
    return w * head


def export(F, g: dict, extra_props=None) -> None:
    G = F.G
    F.PALETTE = g['PALETTE']

    def all_parts():
        return F.all_parts()

    def zones(co, n=None):
        return Z.zones(F, co, n)

    def carve(ob):
        HD.carve(F, ob)

    def decimate_keep(co):
        z = Z.zones(F, co)
        throat = (co[:, 2] < F.HINGE[2]) & (co[:, 2] > F.HINGE[2] - 0.2 * F.k) & (co[:, 1] < F.HINGE[1] + 0.12 * F.k)
        return np.clip(z['face'] * 0.85 + z['muzzle'] * 1.0 + (z['eye_d'] < F.EYE_R * 1.7) * 1.0 + z['mouth_in'] * 1.0 + z['head'] * 0.35
                       + throat * 0.55
                       + z['toes'] * 0.6 + z['hand'] * 0.7, 0, 1)

    def texel_k(co):
        z = Z.zones(F, co)
        kk = np.ones(len(co))
        kk = np.where(z['cream'] > 0.5, 0.9, kk)
        kk = np.where(z['hand'] | z['foot'] | z['arm'], 1.15, kk)
        kk = np.where(z['tail'] & (z['tail_t'] > 0.55), 1.3, kk)            # polish: the tail's end (it smeared smooth)
        kk = np.where(z['head'], 1.4, kk)
        kk = np.where(z['face'] | (z['eye_d'] < F.EYE_R * 2.0), 1.7, kk)
        return kk

    def uv_smooth_mask(co):
        z = Z.zones(F, co)
        m = np.ones(len(co))
        m = np.where(z['head'], 0.0, m)      # round 3: the head unwrapped as it is (smoothing pinched a star on the skull)
        m = np.where(z['face'] | z['muzzle'] | z['mouth_in'] | (z['eye_d'] < F.EYE_R * 2.0), 0.0, m)
        m = np.where(z['hand'] | z['toes'], 0.4, m)
        return m

    def build_eye(name, s, high):
        return FC.build_eye(F, name, s, high)

    def eye_material(name, rough_pass=False, pal=None):
        return FC.eye_material(F, name, rough_pass, pal)

    def blink_pivot(s):
        return FC.blink_pivot(F, s)

    def body_material(name, attr, pal, marks):
        return FC.body_material(F, name, attr, pal, marks)

    def _body(ob, pal):
        co = S.attr_array(ob, 'root').astype(np.float64)
        n = S.attr_array(ob, 'rootn').astype(np.float64) if 'rootn' in ob.data.attributes else None
        z = Z.zones(F, co, n)
        peb = keel = None
        if 'peb_id' in ob.data.attributes and HD._PLATES.get('n') == len(co):
            pid = np.round(S.attr_array(ob, 'peb_id')).astype(np.int64)
            peb = (pid, S.attr_array(ob, 'peb_rim').astype(np.float64), S.attr_array(ob, 'peb_top').astype(np.float64),
                   HD._PLATES['plates']['cream'])
            if 'keel' in ob.data.attributes:
                keel = (S.attr_array(ob, 'keel') > 0.5, S.attr_array(ob, 'keel_ul').astype(np.float64),
                        S.attr_array(ob, 'keel_rho').astype(np.float64), S.attr_array(ob, 'keel_rib').astype(np.float64))
        return PA.body_paint(F, co, n, z, pal, peb, keel)

    def paint_sources(body_srcs, fins, props=()):
        for ob in body_srcs:
            a = _body(ob, g['PALETTE'])
            S.set_colour_attr(ob, 'paint', a['paint'])
            S.set_colour_attr(ob, 'rough', a['rough'])
            S.add_attr(ob, 'glow', np.zeros(len(ob.data.vertices)))
        for ob in props:
            rgb, rc, gl = PA.prop_paint(F, ob, g['PALETTE'])
            S.set_colour_attr(ob, 'paint', rgb)
            S.set_colour_attr(ob, 'rough', rc)
            S.add_attr(ob, 'glow', gl)

    def preview_colours(co, vn):
        z = Z.zones(F, co, vn)
        peb = None
        if HD._PLATES.get('n') == len(co):
            peb = (HD._PLATES['pid'], HD._PLATES['rim'], HD._PLATES['top'], HD._PLATES['plates']['cream'])
        rgb = PA.body_paint(F, co, vn, z, g['PALETTE'], peb, HD._PLATES.get('keel'))['paint']
        # the per-pixel face marks, roughly (the bake draws them crisp): the smile's crease and the brows
        col = PA.colours(g['PALETTE'])
        rgb = PA.blend(rgb, np.exp(-(PR.smile_dist(F, co) / (0.003 * F.k)) ** 2), col['smile'])
        bd = np.full(len(co), 9.0)
        for a, b, w in FC.brow_segments(F):
            a, b = v3(a), v3(b)
            t = np.clip(((co - a) @ (b - a)) / max(float((b - a) @ (b - a)), 1e-12), 0, 1)
            bd = np.minimum(bd, np.linalg.norm(co - (a + t[:, None] * (b - a)), axis=1) / w)
        return PA.blend(rgb, smooth(1.1, 0.8, bd), col['brow'])

    def build_props(high, quick):
        tag = 'hi' if high else 'lo'
        out = [PR.build_crest(f'{tag}_crest', F, high),
               PR.ringed(f'{tag}_spines', PR.spine_items(F, high)),
               PR.ringed(f'{tag}_teeth', PR.teeth_items(F, high)),
               PR.ringed(f'{tag}_claws', PR.claw_items(F, high))]
        if extra_props is not None:
            out += extra_props(F, high, quick)
        return [PR.complete_attrs(o) for o in out]

    def preview_prop_colour(name):
        col = PA.colours(g['PALETTE'])
        if 'teeth' in name:
            return col['tooth']
        if 'claw' in name:
            return col['claw']
        if 'bracer' in name:
            return col['stone']
        return col['accent']

    def body_weight_regions(co, names):
        z = Z.zones(F, co)
        regs = []
        tn = [f'tail.{i + 1}' for i in range(len(F.TAIL_PTS) - 1)]
        tail = z['tail'] & (z['tail_t'] > 0.03)
        if tail.any() and all(b in names for b in tn):
            regs.append((tail, U.chain_weights(co[tail], F.TAIL_PTS, tn, 'hips', fade=(0.06, -0.04))))
        jw = jaw_weight(F, co, z)
        jm = jw > 0.01
        if jm.any() and 'jaw' in names:
            regs.append((jm, {'jaw': jw[jm], 'head': 1.0 - jw[jm]}))
        A = G['arm']
        for s, tag in ((1, 'L'), (-1, 'R')):
            # round 2: the arm's skin along its own three bones (heat weights shared it with the chest, so the forearm's
            # texture smeared into streaks when the arms moved: clip_hit, hit_heavy, ko)
            m = (z['arm'] | z['hand']) & ~z['finger'] & (np.sign(co[:, 0]) == s)
            bones = [f'upperarm.{tag}', f'forearm.{tag}', f'hand.{tag}']
            if m.any() and all(b in names for b in bones):
                pts = [mirror(A[k], s) for k in ('shoulder', 'elbow', 'wrist', 'hand')]
                regs.append((m, U.chain_weights(co[m], pts, bones, 'chest', fade=(0.12, -0.03))))
            m = z['finger'] & (np.sign(co[:, 0]) == s)
            if m.any():
                regs.append(U.rigid(m, f'hand.{tag}'))
        return regs

    def _anchor_weights(co, anchor, names):
        import bpy
        from mathutils import Vector
        from mathutils.kdtree import KDTree
        body = bpy.data.objects.get('lo_body')
        if body is None or not body.vertex_groups:
            return {'chest': np.ones(len(co))}
        bn, W = S.body_weights(body)
        bco, _ = S.mesh_arrays(body)
        kd = KDTree(len(bco))
        for i, p in enumerate(bco):
            kd.insert(Vector(p), i)
        kd.balance()
        uniq, inv = np.unique(np.round(anchor, 5), axis=0, return_inverse=True)
        rows = np.zeros((len(uniq), len(bn)))
        for u, p in enumerate(uniq):
            near = kd.find_n(Vector(p), 6)
            rows[u] = np.mean([W[j] for _c, j, _d in near], axis=0)
        out = {}
        for j, nm in enumerate(bn):
            if nm in names and rows[:, j].max() > 1e-4:
                out[nm] = rows[inv.ravel(), j]
        return out

    def prop_weight_regions(co, attr, names):
        gp = np.round(attr('gpart')).astype(int)
        side = np.round(attr('side')).astype(int)
        regs = []
        m = (gp == PR.P_CREST) | (gp == PR.P_CROWN)
        if m.any():
            regs.append(U.rigid(m, 'prop.crest' if 'prop.crest' in names else 'head'))
        m = gp == PR.P_TOOTH_U
        if m.any():
            regs.append(U.rigid(m, 'head'))
        m = gp == PR.P_TOOTH_L
        if m.any():
            regs.append(U.rigid(m, 'jaw' if 'jaw' in names else 'head'))
        m = gp == PR.P_SPINE
        if m.any():
            regs.append((m, _anchor_weights(co[m], attr('anchor')[m], names)))
        for s, tag in ((1, 'L'), (-1, 'R')):
            m = (gp == PR.P_HCLAW) & (side == s)
            if m.any():
                regs.append(U.rigid(m, f'hand.{tag}'))
            m = (gp == PR.P_FCLAW) & (side == s)
            if m.any():
                regs.append(U.rigid(m, f'foot.{tag}'))
            m = (gp == PR.P_BRACER) & (side == s)
            if m.any():
                b = f'prop.bracer{tag}'
                regs.append(U.rigid(m, b if b in names else f'forearm.{tag}'))
        return regs

    def rig_p():
        R = G['rig']
        A, L = G['arm'], G['leg']
        v = v3(A['hand']) - v3(A['shoulder'])
        abd = math.degrees(math.atan2(v[0], max(1e-6, -v[2])))
        P = {'hip': R['hip'], 'chest': R['chest'], 'head_c': tuple(R['head_c']), 'head_r': R['head_r'],
             'legs': {'hip': L['hip'], 'knee': L['knee'], 'ankle': L['ankle'], 'toe': L['toe']},
             'arms': {'shoulder': A['shoulder'], 'elbow': A['elbow'], 'wrist': A['wrist'], 'hand': A['hand']},
             'arm_relax': abd * R.get('relax_k', 0.75),
             'tail_bones': len(F.TAIL_PTS) - 1, 'tail_points': F.TAIL_PTS,
             'jaw': {'head': tuple(F.HINGE), 'tail': R['chin']}, 'jaw_open': True,
             'props': [{'name': 'crest', 'parent': 'head', 'head': R['crest_bone'][0], 'tail': R['crest_bone'][1]}] + R.get('props', []),
             'strike_style': R['strike']}
        for key in ('neck_bones', 'neck_points', 'head_base', 'lean', 'stride', 'hit_body', 'ko_head', 'win', 'hand_clear', 'sit_height',
                    'headbutt', 'charge', 'walk_bob', 'ko_jaw', 'ko_arm'):
            if key in R:
                P[key] = R[key]
        return P

    def calm_group(bone):
        if bone == 'jaw':
            return 'jaw'
        pre = bone.split('.')[0]
        return pre if '.' in bone and pre in ('ear', 'tail') else None

    hw = F.mouth_half_width()
    lr = F.lip_r(0.0)
    M = F.mouth()
    j = np.nonzero(np.isfinite(M['pu'][0]))[0]
    mid = math.radians(0.5 * (M['pu'][0][j[-1]] + M['pl'][0][j[-1]])) if len(j) else 0.2
    g.update({
        'all_parts': all_parts, 'zones': zones, 'carve': carve, 'decimate_keep': decimate_keep, 'texel_k': texel_k,
        'uv_smooth_mask': uv_smooth_mask, 'build_eye': build_eye, 'eye_material': eye_material, 'blink_pivot': blink_pivot,
        'body_material': body_material, 'paint_sources': paint_sources, 'preview_colours': preview_colours,
        'build_props': build_props, 'preview_prop_colour': preview_prop_colour, 'body_weight_regions': body_weight_regions,
        'prop_weight_regions': prop_weight_regions, 'rig_p': rig_p, 'calm_group': calm_group, 'colours': PA.colours,
        'MOUTH_SOCKET': (0.0, float(F.HINGE[1] - lr * math.cos(mid)), float(F.HINGE[2] - lr * math.sin(mid))),
        'FORM': F, 'MOUTH_HALF_WIDTH': hw,
    })
