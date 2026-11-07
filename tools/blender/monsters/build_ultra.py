"""Build one monster at the Art 2.1 Ultra tier (docs/ART_2_DETAIL.md §3, §5, §9 P1.1), headless.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/monsters/build_ultra.py -- --breed puddlepup_ultra \
        [--stages build,bake,rig,clips,export,review] [--quick] [--atlas 2048] [--views ...]

build   the high source (a 3.5 mm voxel body, carved details, sculpted lying locks, eyes, ribbed membranes) and the game
        meshes (the decimated body, eye lenses, membrane sheets, soft fur cards in two layers, the tuft); numpy paint
        for every source (base, variant, roughness) → build.blend
bake    Cycles selected → active: the 2048² body atlas (normal, AO, colour, ORM, the strip of tuft and card tiles) and
        the variant's colour map on the same UVs; the cards' and tuft's root colours (COLOR_0 base, COLOR_1 variant)
        → baked.blend
rig     the plan's rig plus two blink bones; the body skinned (heat weights, the ears and tail by position so the fur and
        the membranes move together), the cards and the tuft copy the body's weights at their roots → rigged.blend
clips   the plan's clips (the 27 ★ clips and the Battle 3D moves) plus `blink`
export  <look>.glb (skinned meshes lo_body, lo_eyes, lo_fins, lo_cards, lo_tuft, the armature, sockets, NLA clips) and
        the raw sidecar <look>.json; `node tools/art/ultra.ts <breed>` encodes the textures and ships it
review  EEVEE review sheets with the baked maps → tools/blender/out/<look>/review/

Everything lands in tools/blender/out/<look>/ (gitignored).
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # tools/blender → `lib`, `monsters`

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.kdtree import KDTree  # noqa: E402

from lib import anim as A  # noqa: E402
from lib import bake as BK  # noqa: E402
from lib import common as C  # noqa: E402
from lib import export as EX  # noqa: E402
from lib import mesh as M  # noqa: E402
from lib import render as RN  # noqa: E402
from lib import rig as R  # noqa: E402
from lib import surface as S  # noqa: E402
from lib.nodes import NB, new_mat  # noqa: E402

ALL_STAGES = ['build', 'bake', 'rig', 'clips', 'export', 'review']
TUFT_NVT = 19            # vertices per low tuft lock (surface.low_strand_template)


def load(breed: str):
    recipe = importlib.import_module(f'monsters.breeds.{breed}')
    plan = importlib.import_module(f'monsters.plans.{recipe.PLAN}')
    return recipe, plan


def open_blend(out: Path, name: str) -> None:
    path = out / name
    if not path.exists():
        raise SystemExit(f'no {path}: run the earlier stages first')
    bpy.ops.wm.open_mainfile(filepath=str(path))


def save_blend(out: Path, name: str) -> None:
    bpy.ops.wm.save_as_mainfile(filepath=str(out / name), compress=False)
    C.log(f'saved {name}')


def decimate_keep(ob: bpy.types.Object, target: int, keep: np.ndarray, factor: float = 6.0) -> None:
    """Collapse-decimate to `target` triangles, protecting vertices weighted by `keep` (the face, the toes)."""
    vg = ob.vertex_groups.new(name='keep')
    for w in (0.25, 0.5, 0.75, 1.0):
        idx = np.nonzero((keep > w - 0.25) & (keep <= w))[0]
        if len(idx):
            vg.add(idx.tolist(), w, 'REPLACE')
    dm = ob.modifiers.new('decimate', 'DECIMATE')
    dm.decimate_type = 'COLLAPSE'
    dm.ratio = min(1.0, target / max(1, M.tri_count(ob)))
    dm.use_collapse_triangulate = True
    # a vertex group's weight 1 means "free to collapse", 0 "protected": invert, so `keep` protects the face and toes
    dm.vertex_group = 'keep'
    dm.invert_vertex_group = True
    dm.vertex_group_factor = factor
    C.apply_modifiers(ob)
    ob.vertex_groups.clear()
    if M.tri_count(ob) > target * 1.1:
        C.log(f'weighted decimate stopped at {M.tri_count(ob)}: plain decimate to {target}')
        S.decimate_to(ob, target, smooth_after=0.0)
    sm = ob.modifiers.new('smooth', 'SMOOTH')
    sm.factor = 0.25
    sm.iterations = 1
    C.apply_modifiers(ob)
    ob.data.shade_smooth()


# ----------------------------------------------------------------------------- build
def stage_build(recipe, out: Path, quick: bool, body_tris: int) -> dict:
    C.clear_scene()
    t0 = time.time()
    hi_vox = 0.006 if quick else 0.0035
    extras = getattr(recipe, 'body_extras', lambda: [])
    with C.Timer('high body'):
        hi_body = S.build_body('hi_body', recipe.all_parts(), hi_vox, 4, segments=48, extra=extras())
        recipe.carve(hi_body)
    with C.Timer('low body'):
        lo_body = S.build_body('lo_body', recipe.all_parts(), 0.0055, 4, segments=40, extra=extras())
        co, _ = S.mesh_arrays(lo_body)
        z = recipe.zones(co)
        keep = np.clip(z['face'] * 1.0 + z['muzzle'] * 1.0 + (z['eye_d'] < 0.1) * 1.0 + z['toes'] * 0.75 + z['paw'] * 0.25, 0, 1)
        decimate_keep(lo_body, body_tris, keep)
        if lo_body.data.validate(verbose=False):
            C.log('lo_body: validate() fixed invalid geometry')
        C.log(f'lo_body: {M.tri_count(lo_body)} tris')
    if hasattr(recipe, 'body_extras'):
        # heat weights can't be solved over thin extras (the ear slabs): the rig skins a proxy body without them and
        # copies its weights to lo_body by the nearest vertex (P1.2)
        with C.Timer('weight proxy'):
            proxy = S.build_body('lo_proxy', recipe.all_parts(), 0.0055, 4, segments=40)
            S.decimate_to(proxy, 24000, smooth_after=0.0)
            proxy.data.validate(verbose=False)
            proxy.hide_render = True
    hi_eyes = [recipe.build_eye(f'hi_eye{"L" if s > 0 else "R"}', s, True) for s in (1, -1)]
    lo_eyes_parts = [recipe.build_eye(f'lo_eye{"L" if s > 0 else "R"}', s, False) for s in (1, -1)]
    hi_fins = recipe.build_fins(True, quick)
    lo_fins_parts = recipe.build_fins(False, quick)

    # the coat: lying locks (baked) on the source; soft cards and the tuft on the game mesh
    with C.Timer('locks'):
        tpl_head = S.lock_template(7, 11, 3, strand=0.22, closed=False)
        tpl_body = S.lock_template(5, 9, 3, strand=0.22, closed=False)
        lie_head, _ = S.scatter_layer('hi_locks_head', hi_body, recipe.head_lock_params, recipe.flow, 11, tpl_head, quick, 0.085, 0.04, S.KIND_LOCK)
        lie_body, _ = S.scatter_layer('hi_locks_body', hi_body, recipe.body_lock_params, recipe.flow, 13, tpl_body, quick, 0.085, 0.04, S.KIND_LOCK)
    with C.Timer('cards'):
        tpl_card = S.card_template()
        layers = []
        for layer in (0, 1):
            ob, _ = S.scatter_layer(f'lo_cards_{layer}', hi_body, lambda p, n, layer=layer: recipe.card_params(p, n, layer), recipe.flow,
                                    31 + layer, tpl_card, quick, 0.0, 0.02, S.KIND_CARD, jitter_deg=9.0)
            S.add_attr(ob, 'layer', np.full(len(ob.data.vertices), float(layer)))
            layers.append(ob)
        n_layers = [S.element_count(o, S.CARD_VERTS) for o in layers]
        lo_cards = S.join_elements(layers, 'lo_cards', attrs=S.ELEMENT_ATTRS + ('layer',))
    tuft_fr = recipe.tuft_frames(hi_body)
    tpl_tuft_hi = S.lock_template(9, 14, 3, strand=0.18)
    hi_tuft = S.elements_object('hi_tuft', S.instance(tpl_tuft_hi, tuft_fr, 0.34, 0.08), tpl_tuft_hi, tuft_fr['P'], S.KIND_TUFT,
                                np.random.default_rng(3), tuft_fr['N'])
    tpl_tuft_lo = S.low_strand_template()
    lo_tuft = S.elements_object('lo_tuft', S.instance(tpl_tuft_lo, tuft_fr, 0.34, 0.08), tpl_tuft_lo, tuft_fr['P'], S.KIND_TUFT,
                                np.random.default_rng(3), tuft_fr['N'])

    # paint every source (numpy): base, variant and roughness, as colour attributes the bake reads
    with C.Timer('paint'):
        dapples = recipe.make_dapples(hi_body)
        (out / 'dapples.json').write_text(json.dumps([[list(map(float, c)), list(map(float, r))] for c, r in dapples]), encoding='utf-8')
        recipe.paint_sources([hi_body, lie_head, lie_body, hi_tuft], hi_fins)

    # the game meshes, joined per kind; the body atlas (UVMap) with the strip kept at the bottom
    lo_eyes = M.join_meshes(lo_eyes_parts, 'lo_eyes')
    lo_fins = M.join_meshes(lo_fins_parts, 'lo_fins')
    for name in ('fan', 'fin_part'):
        S.add_attr(lo_fins, name, np.concatenate([S.attr_array(o, name) for o in lo_fins_parts]))
    for o in lo_eyes_parts + lo_fins_parts:
        bpy.data.objects.remove(o, do_unlink=True)
    with C.Timer('uv'):
        for o in (lo_body, lo_eyes, lo_fins):
            for uvl in list(o.data.uv_layers):
                o.data.uv_layers.remove(uvl)
            o.data.uv_layers.new(name='UVMap')
        BK.pack_atlas([lo_body, lo_eyes, lo_fins], 'UVMap', BK.STRIP, density=getattr(recipe, 'ATLAS_DENSITY', None))
        BK.strip_uvs(lo_cards, BK.CARD_CELLS)
        BK.strip_uvs(lo_tuft, BK.LOCK_CELLS)
    hi_srcs = [hi_body, lie_head, lie_body, hi_tuft]
    stats = {
        'quick': quick,
        'hi_tris': sum(M.tri_count(o) for o in hi_srcs + hi_eyes + hi_fins),
        'lying_locks': {'head': S.element_count(lie_head, len(tpl_head[0])), 'body': S.element_count(lie_body, len(tpl_body[0]))},
        'tris': {'lo_body': M.tri_count(lo_body), 'lo_eyes': M.tri_count(lo_eyes), 'lo_fins': M.tri_count(lo_fins),
                 'lo_cards': M.tri_count(lo_cards), 'lo_tuft': M.tri_count(lo_tuft)},
        'cards': {'total': S.element_count(lo_cards, S.CARD_VERTS), 'layers': n_layers},
        'tuft_locks': len(tuft_fr['P']),
        'dapples': len(dapples),
        'areas_m2': {'body': S.mesh_area(lo_body), 'fins': S.mesh_area(lo_fins), 'eyes': S.mesh_area(lo_eyes)},
        'seconds': round(time.time() - t0),
    }
    stats['tris']['total'] = sum(stats['tris'].values())
    C.log(json.dumps(stats))
    (out / 'stats_build.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    save_blend(out, 'build.blend')
    return stats


# ----------------------------------------------------------------------------- bake
def stage_bake(recipe, out: Path, quick: bool, atlas_px: int, with_cpu: bool = False, cpu: bool = False) -> dict:
    open_blend(out, 'build.blend')
    O = bpy.data.objects
    dev = BK.use_cpu() if cpu else BK.use_gpu(with_cpu) + ('+CPU' if with_cpu else '')
    BK.bake_world(0.05)
    C.log(f'bake device {dev}, body atlas {atlas_px}²')
    body_srcs = [O['hi_body'], O['hi_locks_head'], O['hi_locks_body'], O['hi_tuft']]
    eyes = [O['hi_eyeL'], O['hi_eyeR']]
    fins = [o for o in O if o.name.startswith('hi_ear') or o.name.startswith('hi_tailfan')]
    lo_body, lo_eyes, lo_fins = O['lo_body'], O['lo_eyes'], O['lo_fins']
    var = recipe.VARIANTS[recipe.VARIANT_ID]
    dapples = [tuple(map(tuple, d)) for d in json.loads((out / 'dapples.json').read_text(encoding='utf-8'))]
    mats = {
        'base': recipe.body_material('paint_base', 'paint', recipe.PALETTE, dapples),
        'songheart': recipe.body_material('paint_songheart', 'paint_v', var, dapples),
        'rough': BK.emission_attr_material('paint_rough', 'rough'),
        'fin_base': BK.emission_attr_material('fin_base', 'paint'),
        'fin_songheart': BK.emission_attr_material('fin_songheart', 'paint_v'),
        'eye': recipe.eye_material('eye_paint'),
        'eye_rough': recipe.eye_material('eye_rough', True),
    }

    def paint(pass_name: str) -> None:
        if pass_name == 'rough':
            BK.set_material(body_srcs + fins, mats['rough'])
            BK.set_material(eyes, mats['eye_rough'])
        else:
            BK.set_material(body_srcs, mats[pass_name])
            BK.set_material(fins, mats[f'fin_{pass_name}'])
            BK.set_material(eyes, mats['eye'])

    samples = (2, 12, 2) if quick else (6, 24, 4)
    # P1.2: the eyes don't shadow the body: the skin under a lens is the closed lid a blink shows (it baked black)
    plan = [(lo_body, body_srcs, body_srcs + fins), (lo_eyes, eyes, eyes + body_srcs), (lo_fins, fins, fins)]
    t0 = time.time()
    imgs = BK.bake_set('atlas', atlas_px, out, plan, 'UVMap', True, paint, samples, extra_colours=('songheart',))
    base = BK.image_array(imgs['base_rgba'])
    vari = BK.image_array(imgs['songheart_rgba'])
    lo_cards, lo_tuft = O['lo_cards'], O['lo_tuft']
    # a touch darker than the skin under them: lit edge-on by the rims, cream cards glittered white (review 1)
    BK.sample_vertex_colours(lo_cards, lo_body, base, 'Col', active=True, scale=0.88)
    BK.sample_vertex_colours(lo_cards, lo_body, vari, 'Col_songheart', active=False, scale=0.88)
    # round 6: the tuft stays teal and never blows out (a sampled crown colour with the lock's sheen read near white)
    n = len(lo_tuft.data.vertices)
    S.set_colour_attr(lo_tuft, 'Col', np.tile(recipe.lin(recipe.colours(recipe.PALETTE)['tuft']), (n, 1)), active=True)
    S.set_colour_attr(lo_tuft, 'Col_songheart', np.tile(recipe.lin(recipe.colours(var)['tuft']), (n, 1)))
    res = {'device': dev, 'atlas_px': atlas_px, 'seconds': round(time.time() - t0)}
    (out / 'stats_bake.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    save_blend(out, 'baked.blend')
    return res


# ----------------------------------------------------------------------------- rig
def eye_bone_specs(recipe) -> list[R.BoneSpec]:
    out = []
    for s, tag in ((1, 'L'), (-1, 'R')):
        pivot, up, *_ = recipe.blink_pivot(s)
        out.append(R.BoneSpec(f'eye.{tag}', tuple(pivot), tuple(pivot + up * 0.05), 'head', radius=0.05))
    return out


def align_eye_bones(recipe, arm) -> None:
    """Turn each blink bone about its own axis so its Z looks out of the face: the blink scales it across (X), up (Y)
    and out (Z)."""
    with bpy.context.temp_override(object=arm, active_object=arm, selected_objects=[arm], selected_editable_objects=[arm]):
        bpy.ops.object.mode_set(mode='EDIT')
        for s, tag in ((1, 'L'), (-1, 'R')):
            pv = recipe.blink_pivot(s)
            if len(pv) > 2:
                arm.data.edit_bones[f'eye.{tag}'].align_roll(pv[2])
        bpy.ops.object.mode_set(mode='OBJECT')


def set_group_weights(ob: bpy.types.Object, names: list[str], W: np.ndarray, arm) -> None:
    S.write_weights(ob, names, W, arm)


def skin_body(body, proxy, arm, specs) -> tuple[list[str], np.ndarray]:
    """Heat weights for the body, as (group names, verts × groups). With a proxy (the body without its thin extras),
    the solve runs on the proxy and every body vertex copies its nearest proxy vertex. Distance weights when heat
    leaves most bones empty (P1.2: the ear slabs made the solve fail for every bone)."""
    src = proxy if proxy is not None else body
    deform = [s.name for s in specs if s.deform]
    ok = R.skin_auto(src, arm)
    if ok:
        _bn, W = S.body_weights(src)
        ok = int((W.max(axis=0) > 0.01).sum()) >= len(deform) // 2
    if not ok:
        C.log(f'heat weights failed on {src.name}: distance weights')
        R.skin_distance(src, arm, specs)
    bn, W = S.body_weights(src)
    if proxy is None:
        return bn, W
    pco, _ = S.mesh_arrays(proxy)
    kd = KDTree(len(pco))
    for i, p in enumerate(pco):
        kd.insert(Vector(p), i)
    kd.balance()
    bco, _ = S.mesh_arrays(body)
    idx = np.array([kd.find(Vector(p))[1] for p in bco], dtype=np.int64)
    C.log(f'skin body: {len(bco)} verts copy the weights of the proxy ({len(pco)} verts)')
    return bn, W[idx]


def stage_rig(recipe, plan, out: Path) -> dict:
    open_blend(out, 'baked.blend')
    O = bpy.data.objects
    P = recipe.rig_p()
    specs = plan.rig_specs(P) + eye_bone_specs(recipe)
    arm = R.build_armature(f'{recipe.ID}_rig', specs)
    align_eye_bones(recipe, arm)
    names = [s.name for s in specs if s.deform]
    body = O['lo_body']
    with C.Timer('skin body'):
        bn, W = skin_body(body, O.get('lo_proxy'), arm, specs)
        W2 = np.zeros((W.shape[0], len(names)), np.float64)
        for j, nm in enumerate(bn):
            if nm in names:
                W2[:, names.index(nm)] = W[:, j]
        co, _ = S.mesh_arrays(body)
        hi = names.index('head')
        # no mouth to open and no lids on the body: the jaw and the blink bones never move the skin
        for nm in ('jaw', 'eye.L', 'eye.R'):
            j = names.index(nm)
            W2[:, hi] += W2[:, j]
            W2[:, j] = 0.0
        # the ears: the furry caps follow the same head → ear.1 → ear.2 blend as the membranes
        ear, ear_u = recipe.ear_zone(co)
        for s, tag in ((1, 'L'), (-1, 'R')):
            on = ear & (np.sign(co[:, 0]) == s)
            if on.any():
                w = recipe.ear_weights(co[on], ear_u[on])
                W2[on] = 0.0
                W2[on, hi] = w['head']
                W2[on, names.index(f'ear.{tag}.1')] = w['1']
                W2[on, names.index(f'ear.{tag}.2')] = w['2']
        # the tail: the paddle and the fluke follow the tail chain by how far along they are
        zt = recipe.zones(co)['tail']
        if zt.any():
            w = recipe.tail_weights(co[zt])
            W2[zt] = 0.0
            for nm, wv in w.items():
                W2[zt, names.index(nm)] = wv
        set_group_weights(body, names, W2, arm)
        R.smooth_weights(body, iterations=2, factor=0.5)
    # the membranes
    fins = O['lo_fins']
    fco, _ = S.mesh_arrays(fins)
    fan = S.attr_array(fins, 'fan')
    part = S.attr_array(fins, 'fin_part')
    Wf = np.zeros((len(fco), len(names)))
    for s, tag in ((1, 'L'), (-1, 'R')):
        on = np.abs(part - s) < 0.1
        w = recipe.ear_weights(fco[on], fan[on, 0])
        Wf[on, hi] = w['head']
        Wf[on, names.index(f'ear.{tag}.1')] = w['1']
        Wf[on, names.index(f'ear.{tag}.2')] = w['2']
    on = part > 1.5
    for nm, wv in recipe.tail_weights(fco[on]).items():
        Wf[on, names.index(nm)] = wv
    set_group_weights(fins, names, Wf, arm)
    # the eye lenses ride their blink bones
    eyes = O['lo_eyes']
    eco, _ = S.mesh_arrays(eyes)
    We = np.zeros((len(eco), len(names)))
    We[:, names.index('eye.L')] = eco[:, 0] > 0
    We[:, names.index('eye.R')] = eco[:, 0] <= 0
    set_group_weights(eyes, names, We, arm)
    # the cards and the tuft copy the skin under their roots
    S.copy_weights_at_roots(O['lo_cards'], body, arm, S.CARD_VERTS)
    S.copy_weights_at_roots(O['lo_tuft'], body, arm, TUFT_NVT)
    S.coat_normals(O['lo_cards'], 0.15, S.CARD_VERTS)
    S.coat_normals(O['lo_tuft'], 0.4, TUFT_NVT)
    sockets = {}
    for name, (bone, pos) in plan.sockets(P).items():
        R.add_socket(arm, name, bone, Vector(pos))
        sockets[name] = bone
    mn, mx = M.bounds(body)
    meta = {'sockets': sockets, 'bounds': {'min': [round(v, 4) for v in mn], 'max': [round(v, 4) for v in mx]},
            'restHeight': round(mx.z, 4), 'deformBones': len(names), 'bones': len(specs)}
    (out / 'stats_rig.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    save_blend(out, 'rigged.blend')
    return meta


# ----------------------------------------------------------------------------- clips
def blink_clip(cb: A.ClipBuilder, arm, closed=(1.0, 0.08, 1.0)) -> A.ClipMeta:
    """Both eyes close and open again: 7 frames. It keys only the blink bones, so the runtime can play it over any
    other clip. `closed` is the bones' (across, up, out) scale when shut; P1.2 squashes each lens down onto the closed
    lid's lash line first, then sinks it into the head, showing the lid."""
    n = 7
    cb.begin('blink', n, loop=False)
    half = tuple(1.0 + (c - 1.0) * k for c, k in zip(closed, (0.3, 0.62, 0.08)))
    for f, sc in ((1, (1.0, 1.0, 1.0)), (2, half), (3, closed), (5, closed), (6, half), (8, (1.0, 1.0, 1.0))):
        for tag in ('L', 'R'):
            pb = arm.pose.bones[f'eye.{tag}']
            pb.scale = sc
            pb.keyframe_insert('scale', frame=f)
    return cb.end()


class CalmClips(A.ClipBuilder):
    """A clip builder that scales the ear and tail bones' rotations per clip (a recipe's CLIP_CALM)."""

    def __init__(self, arm, deform, calm: dict):
        super().__init__(arm, deform)
        self.calm = calm

    def rot(self, bone: str, frame: int, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        group = 'ear' if bone.startswith('ear.') else 'tail' if bone.startswith('tail.') else None
        k = 1.0
        if group and self.meta is not None:
            k = self.calm.get(self.meta.name, {}).get(group, self.calm.get('*', {}).get(group, 1.0))
        super().rot(bone, frame, x * k, y * k, z * k)


def stage_clips(recipe, plan, out: Path, only: list[str] | None) -> list[A.ClipMeta]:
    open_blend(out, 'rigged.blend')
    arm = bpy.data.objects[f'{recipe.ID}_rig']
    bpy.context.scene.render.fps = A.FPS
    ad = arm.animation_data
    if ad is not None:
        for t in list(ad.nla_tracks):
            ad.nla_tracks.remove(t)
        ad.action = None
    for act in list(bpy.data.actions):
        bpy.data.actions.remove(act)
    deform = [b.name for b in arm.data.bones if b.use_deform]
    cb = CalmClips(arm, deform, getattr(recipe, 'CLIP_CALM', {}))
    with C.Timer('clips'):
        clips = plan.make_clips(cb, recipe.rig_p(), only)
        if not only or 'blink' in only:
            clips.append(blink_clip(cb, arm, getattr(recipe, 'BLINK_CLOSED', (1.0, 0.08, 1.0))))
    want = plan.STAR_CLIPS + plan.MOVE_CLIPS + ['blink']
    missing = [c for c in want if c not in [m.name for m in clips]]
    if missing and not only:
        C.log(f'WARNING missing clips: {missing}')
    meta = {m.name: clip_json(plan, m) for m in clips}
    (out / 'clips.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    save_blend(out, 'rigged.blend')
    return clips


def clip_json(plan, m: A.ClipMeta) -> dict:
    d = m.to_json()
    if m.name in plan.ROOT_DIRS and m.root_speed:
        d['rootDir'] = list(plan.ROOT_DIRS[m.name])
    if m.name.startswith('sidestep'):
        d['rootDistance'] = round(m.root_speed * m.seconds, 4)
    return d


def clips_from_scene(out: Path) -> list[A.ClipMeta]:
    data = json.loads((out / 'clips.json').read_text(encoding='utf-8'))
    clips = []
    for name, d in data.items():
        act = bpy.data.actions.get(name)
        if act is None:
            continue
        clips.append(A.ClipMeta(name=name, frames=int(round(d['seconds'] * A.FPS)), loop=d['loop'], hold=d['hold'], root_speed=d['rootSpeed'],
                                markers=[(x['name'], int(round(x['t'] * A.FPS))) for x in d['markers']],
                                faces=[(int(round(x['t'] * A.FPS)), x['face']) for x in d['faces']], action=act))
    return clips


# ----------------------------------------------------------------------------- export
MESH_KINDS = {'lo_body': 'body', 'lo_eyes': 'eye', 'lo_fins': 'fin', 'lo_cards': 'card', 'lo_tuft': 'lock'}


def stage_export(recipe, plan, out: Path) -> Path:
    open_blend(out, 'rigged.blend')
    O = bpy.data.objects
    arm = O[f'{recipe.ID}_rig']
    meshes = [O[n] for n in MESH_KINDS]
    for ob in meshes:
        m, nb = new_mat(f'{recipe.ID}_{MESH_KINDS[ob.name]}')
        nb.output(nb.new('ShaderNodeBsdfPrincipled').outputs[0])
        ob.data.materials.clear()
        ob.data.materials.append(m)
        # only the UV map, the skin and (cards, tuft) the two colour sets ship
        for a in [a.name for a in ob.data.attributes if not a.name.startswith('.') and a.name not in ('position', 'Col', 'Col_songheart', 'sharp_face')
                  and a.domain == 'POINT' and a.data_type in ('FLOAT', 'FLOAT_VECTOR')]:
            ob.data.attributes.remove(ob.data.attributes[a])
        # Blender 5.2's exporter writes a white COLOR_0 for these meshes whatever the options, so the colours go out as
        # custom attributes and tools/art/ultra.ts promotes them: _COLOR_BASE → COLOR_0, _COLOR_VARIANT → COLOR_1
        me = ob.data
        for src, dst in (('Col', '_COLOR_BASE'), ('Col_songheart', '_COLOR_VARIANT')):
            if src in me.color_attributes:
                S.add_attr(ob, dst, S.attr_array(ob, src)[:, :3])
        for c in list(me.color_attributes):
            me.color_attributes.remove(c)
    sockets = [o for o in O if o.name.startswith('socket_')]
    opts_before = dict(EX.EXPORT_OPTIONS)
    EX.EXPORT_OPTIONS.update(export_tangents=True, export_vertex_color='NONE', export_all_vertex_colors=False,
                             export_attributes=True, export_materials='EXPORT')
    try:
        glb = EX.export_glb(out / f'{recipe.LOOK}.glb', [arm] + meshes + sockets)
    finally:
        EX.EXPORT_OPTIONS.clear()
        EX.EXPORT_OPTIONS.update(opts_before)
    rig = json.loads((out / 'stats_rig.json').read_text(encoding='utf-8'))
    clips = json.loads((out / 'clips.json').read_text(encoding='utf-8'))
    build = json.loads((out / 'stats_build.json').read_text(encoding='utf-8'))
    var = recipe.VARIANTS[recipe.VARIANT_ID]
    side = {
        'look': recipe.ID,
        'tier': 'ultra',
        'plan': recipe.PLAN,
        'version': 2,
        'heightUnits': recipe.HEIGHT_UNITS,
        'restHeight': rig['restHeight'],
        'bounds': rig['bounds'],
        'bones': {'root': 'root', 'head': 'head', 'hips': 'hips', 'eyes': ['eye.L', 'eye.R']},
        'sockets': rig['sockets'],
        'springs': plan.SPRINGS,
        'meshes': MESH_KINDS,
        'face': {
            'mode': 'baked',
            'note': 'The eyes are glossy lenses (lo_eyes) with the iris, pupil, catchlights and the upper lash line baked into the '
                    'body atlas; the brows, blush, nose and the smile are baked into the body. No face sheet and no morphs: '
                    'expressions in clips\' `faces` are hints only. Blinking scales the blink bones (play `blink` over any clip): '
                    'each lens squashes onto the closed lid\'s lash line and sinks into the head, showing the closed lid '
                    '(sculpted and painted on the body under the lens).',
            'eyeBones': ['eye.L', 'eye.R'],
            'blinkClip': 'blink',
            'blinkScale': {'axis': 'y', 'closed': getattr(recipe, 'BLINK_CLOSED', (1.0, 0.08, 1.0))[1],
                           'closedXYZ': list(getattr(recipe, 'BLINK_CLOSED', (1.0, 0.08, 1.0)))},
            'eyeColor': recipe.PALETTE['eye'],
        },
        'variants': {recipe.VARIANT_ID: {'textures': recipe.VARIANT_ID, 'colorAttribute': 'COLOR_1', 'eyeColor': var['eye'],
                                         'palette': {k: var[k] for k in ('body', 'belly', 'accent', 'eye')}}},
        'palette': recipe.PALETTE,
        # the atlas layout: the bottom `strip` share holds `cells` tiles (tuft locks, then fur cards with alpha)
        'atlas': {'strip': BK.STRIP, 'cells': BK.CELLS, 'lockCells': list(BK.LOCK_CELLS), 'cardCells': list(BK.CARD_CELLS)},
        'clips': clips,
        'build': {'cards': build['cards'], 'tuftLocks': build['tuft_locks'], 'lyingLocks': build['lying_locks'], 'sourceTriangles': build['hi_tris']},
    }
    EX.write_sidecar(out / f'{recipe.LOOK}.json', side)
    return glb


# ----------------------------------------------------------------------------- review (Blender sheets)
def review_scene(res=(720, 720)):
    """The pictures' studio: a big soft key from the upper left, a gentle cool fill, a warm rim, grey backdrop."""
    sc = RN.setup_eevee(res, 32, transparent=False)
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    w = sc.world
    wt = w.node_tree
    wt.nodes.clear()
    wb = NB(wt)
    lp = wb.new('ShaderNodeLightPath')
    lit = wb.new('ShaderNodeBackground')
    lit.inputs['Color'].default_value = (0.82, 0.84, 0.88, 1)
    lit.inputs['Strength'].default_value = 0.85
    cam_bg = wb.new('ShaderNodeBackground')
    cam_bg.inputs['Color'].default_value = (0.24, 0.245, 0.255, 1)
    cam_bg.inputs['Strength'].default_value = 1.0
    mx = wb.new('ShaderNodeMixShader')
    wb.link(lp.outputs['Is Camera Ray'], mx.inputs[0])
    wb.link(lit.outputs[0], mx.inputs[1])
    wb.link(cam_bg.outputs[0], mx.inputs[2])
    wo = wb.new('ShaderNodeOutputWorld')
    wb.link(mx.outputs[0], wo.inputs['Surface'])
    for name, (az, el), energy, color, angle in (('Key', (-45, 42), 3.0, (1.0, 0.97, 0.93), 28), ('Fill', (55, 12), 0.7, (0.9, 0.94, 1.0), 40),
                                                 ('Rim', (155, 28), 3.6, (1.0, 0.85, 0.66), 12), ('Rim2', (-150, 24), 2.4, (1.0, 0.88, 0.7), 12)):
        ld = bpy.data.lights.new(name, 'SUN')
        ld.energy = energy
        ld.color = color
        ld.angle = math.radians(angle)
        lo = bpy.data.objects.new(name, ld)
        C.link_obj(lo)
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        lo.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    C.link_obj(cam)
    sc.camera = cam
    return sc, cam


def aim(cam, target, az, el, size):
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    dist = size * 2.4
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    cam.data.sensor_width = 36
    cam.data.lens = 36 * dist / size


def game_materials(out: Path, which: str = 'base') -> None:
    """The low meshes with their baked maps, as EEVEE sees them (cards: alpha from the strip tile × the edge fade is a
    runtime thing; here they dither)."""
    O = bpy.data.objects
    imgs = {k: bpy.data.images.load(str(out / f'atlas_{k}.png')) for k in ('normal', 'orm')}
    imgs['base'] = bpy.data.images.load(str(out / ('atlas_base.png' if which == 'base' else f'atlas_{which}.png')))
    for k in ('normal', 'orm'):
        imgs[k].colorspace_settings.name = 'Non-Color'
    for n, kind in MESH_KINDS.items():
        o = O[n]
        m, nb = new_mat(f'review_{n}_{which}')
        uvn = nb.new('ShaderNodeUVMap')
        uvn.uv_map = 'UVMap'
        tb = nb.new('ShaderNodeTexImage', image=imgs['base'])
        tn = nb.new('ShaderNodeTexImage', image=imgs['normal'])
        to = nb.new('ShaderNodeTexImage', image=imgs['orm'])
        for t in (tb, tn, to):
            nb.link(uvn.outputs['UV'], t.inputs['Vector'])
        nm = nb.new('ShaderNodeNormalMap')
        nm.uv_map = 'UVMap'
        nm.inputs['Strength'].default_value = 0.65
        nb.link(tn.outputs['Color'], nm.inputs['Color'])
        bsdf = nb.new('ShaderNodeBsdfPrincipled')
        base = tb.outputs['Color']
        if kind in ('card', 'lock'):
            vc = nb.new('ShaderNodeVertexColor')
            vc.layer_name = 'Col' if which == 'base' else 'Col_songheart'
            base = nb.mix(1.0, base, vc.outputs['Color'], blend='MULTIPLY')
        r, g, b = nb.sep_rgb(to.outputs['Color'])
        nb.link(nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, r), 0.5), base, nb.rgb((0, 0, 0)), dtype='RGBA'), bsdf.inputs['Base Color'])
        nb.link(g, bsdf.inputs['Roughness'])
        nb.link(b, bsdf.inputs['Coat Weight'])
        bsdf.inputs['Coat Roughness'].default_value = 0.12
        bsdf.inputs['Sheen Weight'].default_value = 0.0 if kind in ('fin', 'eye') else 0.5
        bsdf.inputs['Sheen Roughness'].default_value = 0.45
        if kind != 'card':
            nb.link(nm.outputs['Normal'], bsdf.inputs['Normal'])
        if kind == 'eye':
            bsdf.inputs['Specular IOR Level'].default_value = 0.25
        if kind == 'fin':
            bsdf.inputs['Emission Strength'].default_value = 0.12
            nb.link(tb.outputs['Color'], bsdf.inputs['Emission Color'])
        if kind == 'card':
            nb.link(tb.outputs['Alpha'], bsdf.inputs['Alpha'])
            m.surface_render_method = 'DITHERED'
        nb.output(bsdf.outputs[0])
        m.use_backface_culling = kind not in ('fin',)
        o.data.materials.clear()
        o.data.materials.append(m)


VIEWS = {   # name: (azimuth, elevation, target, size)
    'front': (0, 6, None, None), 'three_quarter': (35, 14, None, None), 'side': (90, 4, None, None), 'back': (180, 10, None, None),
    'head_34': (26, 12, 'head', None), 'head_front': (0, 4, 'head', None),
}


def stage_review(recipe, out: Path, quick: bool) -> list[Path]:
    open_blend(out, 'rigged.blend')
    rv = C.ensure_dir(out / 'review')
    shots = C.ensure_dir(rv / 'shots')
    sc, cam = review_scene((480, 480) if quick else (720, 720))
    O = bpy.data.objects
    for o in O:
        if o.type == 'MESH':
            o.hide_render = o.name not in MESH_KINDS
    arm = O[f'{recipe.ID}_rig']
    clips = {m.name: m for m in clips_from_scene(out)}
    centre, size = recipe.REVIEW['centre'], recipe.REVIEW['size']
    head_t, head_s = recipe.REVIEW['head']
    made: list[tuple[Path, str]] = []

    def shot(name: str, az: float, el: float, target, sz: float) -> None:
        aim(cam, target, az, el, sz)
        p = RN.render_png(shots / f'{name}.png')
        made.append((p, name.replace('_', ' ')))

    game_materials(out, 'base')
    A.clear_clip(arm)
    bpy.context.view_layer.update()
    for v, (az, el, tgt, _s) in VIEWS.items():
        if tgt == 'head':
            shot(v, az, el, head_t, head_s)
        else:
            shot(v, az, el, centre, size)
    turn = RN.contact_sheet(made[:4], 4, rv / 'turnaround.png', title=f'{recipe.LOOK} turnaround (game mesh, baked atlas)')
    faces = RN.contact_sheet(made[4:6], 2, rv / 'head.png', title=f'{recipe.LOOK} head')
    made.clear()
    poses = [('strafe_l', 0.25), ('strafe_r', 0.25), ('sidestep_l', 0.5), ('sidestep_r', 0.5), ('strike', 0.54), ('hit', 0.3),
             ('hit_heavy', 0.3), ('ko', 1.0), ('win', 0.2), ('battle_idle', 0.25), ('walk', 0.25), ('blink', 0.4)]
    for name, t in poses:
        m = clips.get(name)
        if m is None:
            continue
        A.set_clip(arm, m)
        f = 1 + int(round(t * m.frames))
        sc.frame_set(f)
        bpy.context.view_layer.update()
        if name == 'blink':
            shot(f'pose_{name}', 20, 8, head_t, head_s)
        else:
            shot(f'pose_{name}', 35, 14, centre, size)
    A.clear_clip(arm)
    sc.frame_set(1)
    pose_sheet = RN.contact_sheet(made, 4, rv / 'poses.png', title=f'{recipe.LOOK} key poses')
    made.clear()
    game_materials(out, 'songheart')
    shot('variant_three_quarter', 35, 14, centre, size)
    shot('variant_back', 160, 14, centre, size)
    var_sheet = RN.contact_sheet(made, 2, rv / 'variant.png', title='songheart puddlepup')
    return [turn, faces, pose_sheet, var_sheet]


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--breed', default='puddlepup_ultra')
    ap.add_argument('--stages', default=','.join(ALL_STAGES))
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--atlas', type=int, default=2048)
    ap.add_argument('--body-tris', type=int, default=46000)
    ap.add_argument('--clips', default='')
    ap.add_argument('--with-cpu', action='store_true', help='bake on the GPU and the CPU together')
    ap.add_argument('--cpu', action='store_true', help='bake on the CPU only (another job saturates the GPU)')
    args = ap.parse_args(C.script_args())
    stages = [s for s in args.stages.split(',') if s]
    recipe, plan = load(args.breed)
    out = C.ensure_dir(C.OUT_ROOT / recipe.LOOK)
    C.open_log(out / 'build.log')
    C.log(f'build_ultra {recipe.LOOK} stages={stages} quick={args.quick}')
    t0 = time.time()
    if 'build' in stages:
        stage_build(recipe, out, args.quick, args.body_tris)
    if 'bake' in stages:
        stage_bake(recipe, out, args.quick, args.atlas if not args.quick else min(args.atlas, 1024), args.with_cpu, args.cpu)
    if 'rig' in stages:
        stage_rig(recipe, plan, out)
    if 'clips' in stages:
        stage_clips(recipe, plan, out, [c for c in args.clips.split(',') if c] or None)
    if 'export' in stages:
        stage_export(recipe, plan, out)
    if 'review' in stages:
        stage_review(recipe, out, args.quick)
    C.log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
