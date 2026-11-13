"""Build one monster at the Art 2.1 Ultra tier (docs/ART_2_DETAIL.md §3, §5, §9 P1.1), headless, for any breed.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/monsters/build_ultra.py -- --breed <breed>_ultra \
        [--stages build,bake,rig,clips,export,review] [--quick] [--cpu] [--atlas 2048] [--body-tris N] [--out DIR]

The recipe contract (what a `breeds/<breed>_ultra.py` must and may define) is tools/blender/monsters/breeds/RECIPE.md;
Puddlepup (`puddlepup_ultra.py`) is the worked example. Helpers: tools/blender/lib/ultra.py.

build   the high source (a 3.5 mm voxel body, carved details, lying locks, eyes, any membranes and props) and the game
        meshes (the decimated body, eye lenses, membrane sheets, props, soft fur cards in CARD_LAYERS layers, the
        tuft; each optional part only if the recipe makes it); numpy paint for every source (base, every variant,
        roughness) → build.blend
bake    Cycles selected → active: the body atlas (normal, AO, colour, ORM, the strip of tuft and card tiles) and one
        colour map per variant on the same UVs; the cards' and tuft's root colours (Col base, Col_<short> per variant)
        → baked.blend
rig     the plan's rig plus two blink bones; the body skinned (heat weights, then the recipe's weight regions: by
        default the ears and tail by position, so the fur and the membranes move together), the cards and the tuft
        copy the body's weights at their roots → rigged.blend
clips   the plan's clips (the 27 ★ clips and the Battle 3D moves) plus `blink`
export  <look>.glb (skinned lo_* meshes, the armature, sockets, NLA clips) and the raw sidecar <look>.json;
        `node tools/art/ultra.ts <breed>` encodes the textures and ships it (and the Lite copy)
review  EEVEE review sheets with the baked maps (one per variant) → <out>/review/

Everything lands in tools/blender/out/<look>/ (gitignored) unless --out says otherwise.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
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
from lib import marks as MK  # noqa: E402
from lib import mesh as M  # noqa: E402
from lib import render as RN  # noqa: E402
from lib import rig as R  # noqa: E402
from lib import surface as S  # noqa: E402
from lib import ultra as U  # noqa: E402
from lib.nodes import NB, new_image, new_mat  # noqa: E402

ALL_STAGES = ['build', 'bake', 'rig', 'clips', 'export', 'review']
TUFT_NVT = len(S.low_strand_template()[0])      # vertices per low tuft lock (19)
MESH_KINDS = U.MESH_KINDS
REQUIRED = ('ID', 'LOOK', 'PLAN', 'HEIGHT_UNITS', 'PALETTE', 'VARIANTS', 'all_parts', 'build_eye', 'eye_material', 'blink_pivot',
            'paint_sources', 'body_material', 'rig_p')
RESERVED_SHORTS = {'base', 'normal', 'orm', 'ao', 'rc', 'alpha', 'rough', 'eye', 'eye_rough'}
LOCK_LAYERS = [('head', 'head_lock_params', 11, (7, 11, 3, 0.22)), ('body', 'body_lock_params', 13, (5, 9, 3, 0.22))]
TUFT_DEFAULT = {'template': (9, 14, 3, 0.18), 'thickness': 0.34, 'bury': 0.08}
VOXELS_DEFAULT = {'hi': 0.0035, 'hi_quick': 0.006, 'lo': 0.0055}
# per-point attributes a joined membrane / props mesh keeps even when only some parts have them (zero on the others)
UNION_ATTRS = ('wing_uv', 'wing_side')
DEFAULT_FACE_NOTE = ('The eyes are glossy lenses (lo_eyes) with the iris, pupil and catchlights baked into the body atlas; the rest of '
                     'the face is baked into the body. No face sheet and no morphs: expressions in clips\' `faces` are hints only. '
                     'Blinking scales the blink bones (play `blink` over any clip): each lens squashes and sinks into the head, '
                     'showing the closed lid painted on the body under it.')


def load(breed: str):
    recipe = importlib.import_module(f'monsters.breeds.{breed}')
    validate(recipe)
    plan = importlib.import_module(f'monsters.plans.{recipe.PLAN}')
    return recipe, plan


def validate(recipe) -> None:
    """Fail early, in words, when a recipe breaks the contract (RECIPE.md)."""
    missing = [n for n in REQUIRED if not hasattr(recipe, n)]
    if missing:
        raise SystemExit(f'{recipe.__name__}: the recipe contract needs {", ".join(missing)} (tools/blender/monsters/breeds/RECIPE.md)')
    if hasattr(recipe, 'VARIANT_ID'):
        C.log(f'{recipe.__name__}: VARIANT_ID is ignored; every entry of VARIANTS is built')
    shorts = []
    for vid, pal in recipe.VARIANTS.items():
        sh = U.variant_short(vid, recipe.ID)
        if sh in RESERVED_SHORTS or not sh.replace('_', '').replace('-', '').isalnum():
            raise SystemExit(f'variant {vid!r}: its short name {sh!r} is reserved or not [a-z0-9_-]')
        lack = [k for k in ('body', 'belly', 'accent', 'eye') if k not in pal]
        if lack:
            raise SystemExit(f'variant {vid!r} has no {", ".join(lack)}')
        shorts.append(sh)
    if len(set(shorts)) != len(shorts):
        raise SystemExit(f'variant short names collide: {shorts}')
    for sh in getattr(recipe, 'VARIANT_CARDS_OFF', None) or ():
        if sh not in shorts:
            raise SystemExit(f'VARIANT_CARDS_OFF names {sh!r}, which is not one of the variants ({", ".join(shorts) or "none"})')
    for sh in variant_orm(recipe):
        if sh not in shorts:
            raise SystemExit(f'VARIANT_ORM names {sh!r}, which is not one of the variants ({", ".join(shorts) or "none"})')
        if sh + '_orm' in shorts:
            raise SystemExit(f'variant short {sh!r}: its ORM file atlas_{sh}_orm.png would be variant {sh}_orm\'s colour map')
    if U.variant_prop_owners(recipe) and not hasattr(recipe, 'build_props'):
        raise SystemExit(f'{recipe.__name__}: VARIANTS list props but there is no build_props(high, quick)')
    if (hasattr(recipe, 'card_params') or any(hasattr(recipe, fn) for _n, fn, *_ in LOCK_LAYERS)) and not hasattr(recipe, 'flow'):
        raise SystemExit(f'{recipe.__name__}: locks and cards need flow(p, n, z=None)')
    if hasattr(recipe, 'ATLAS_STRIP'):
        strip = float(recipe.ATLAS_STRIP)
        if strip not in (0.0, BK.STRIP):
            raise SystemExit(f'{recipe.__name__}: ATLAS_STRIP is 0 (no strip: a coat without cards or tuft) or {BK.STRIP} (the default)')
        has_cards = hasattr(recipe, 'card_params') and int(getattr(recipe, 'CARD_LAYERS', 2)) > 0
        if strip == 0.0 and (has_cards or hasattr(recipe, 'tuft_frames')):
            raise SystemExit(f'{recipe.__name__}: ATLAS_STRIP = 0 needs a coat without fur cards and tuft (the strip holds their tiles)')


def variant_orm(recipe) -> dict[str, dict]:
    """VARIANT_ORM: {variant short: options} for the variants that bake their own ORM map (roughness, clearcoat and
    glow mask) instead of sharing the breed's. Options: 'glow': {'strength', 'tint'} gives the variant its own glow
    (a glow pass from the sources' `glow_<short>` attribute and the recipe's glow_material(name, marks, pal)); without it
    the variant keeps the breed's glow, if any. The roughness and coat come from each source's `rough_<short>` colour
    attribute (written by paint_sources like 'rough'), or 'rough' where a source has none."""
    vo = getattr(recipe, 'VARIANT_ORM', None) or {}
    if not isinstance(vo, dict):
        raise SystemExit(f'{recipe.__name__}: VARIANT_ORM is a dict {{variant short: options}}')
    out = {}
    for sh, opts in vo.items():
        opts = dict(opts or {})
        bad = [k for k in opts if k != 'glow']
        if bad:
            raise SystemExit(f'VARIANT_ORM[{sh!r}]: unknown option(s) {", ".join(bad)} (only glow)')
        g = opts.get('glow')
        if g is not None and (not isinstance(g, dict) or float(g.get('strength', 0)) <= 0):
            raise SystemExit(f'VARIANT_ORM[{sh!r}][\'glow\'] is {{"strength": > 0, "tint": "#rrggbb" or None}}')
        out[sh] = opts
    return out


def atlas_strip(recipe) -> float:
    """The bottom share of the body atlas kept for the tuft and card tiles: BK.STRIP, or 0 for a recipe without them
    that sets ATLAS_STRIP = 0 (the islands get the whole square)."""
    return float(getattr(recipe, 'ATLAS_STRIP', BK.STRIP))


def variants(recipe) -> list[tuple[str, str, dict]]:
    """(id, short, paint) for every variant, in VARIANTS order (0..N)."""
    return [(vid, U.variant_short(vid, recipe.ID), pal) for vid, pal in recipe.VARIANTS.items()]


def rig_params(recipe) -> dict:
    """The plan's options: the recipe's rig_p() with the breed's size factor filled in."""
    P = dict(recipe.rig_p())
    P.setdefault('size_k', U.size_k(recipe))
    # the blink bones' shut scale (across, up, out): the hit, hit_heavy and ko clips squeeze the eyes shut with it
    P.setdefault('blink_closed', tuple(getattr(recipe, 'BLINK_CLOSED', (1.0, 0.08, 1.0))))
    # a weighted jaw (not merged into the head): the plan opens the mouth in idle_happy and win
    P.setdefault('jaw_open', 'jaw' not in tuple(getattr(recipe, 'MERGE_INTO_HEAD', ('jaw', 'eye.L', 'eye.R'))))
    return P


def socket_points(recipe, planned: dict) -> dict:
    """The plan's sockets with the recipe's overrides: SOCKET_POINTS {name: (x, y, z) or (bone, (x, y, z))} in model
    space (a new name adds a socket), and MOUTH_SOCKET = (x, y, z) as a shorthand for socket_mouth (breath and flame
    effects start at the lips, not inside the snout)."""
    out = dict(planned)
    over = dict(getattr(recipe, 'SOCKET_POINTS', {}) or {})
    if getattr(recipe, 'MOUTH_SOCKET', None) is not None:
        over.setdefault('socket_mouth', recipe.MOUTH_SOCKET)
    for name, v in over.items():
        if len(v) == 2 and isinstance(v[0], str):
            out[name] = (v[0], tuple(float(c) for c in v[1]))
        else:
            if name not in out:
                raise SystemExit(f'SOCKET_POINTS {name!r}: a new socket needs its bone: (bone, (x, y, z))')
            out[name] = (out[name][0], tuple(float(c) for c in v))
    return out


def skin_colour(lo_body, hi_body, paint, pass_name: str, size: int, ao: np.ndarray, samples: int) -> np.ndarray:
    """The bare skin's baked colour (hi_body alone: no lying locks over it), with the atlas's share of AO, for
    CARD_COLOUR_FROM = 'skin': what each card samples at its root instead of the atlas, where a lock of another colour
    may cover the root."""
    img = new_image(f'skin_{pass_name}', size, alpha=False, color=(0.0, 0.0, 0.0, 1.0), srgb=True)
    paint(pass_name)
    BK.bake('EMIT', lo_body, [hi_body], img, samples, clear=True)
    a = BK.image_array(img).copy()
    a[..., :3] *= (1.0 - BK.BASE_AO * (1.0 - ao[..., :1]))
    return a


def card_colours_from_paint(cards, hi_body, attr: str, shade: float) -> np.ndarray:
    """Each card's colour from the skin's own paint at its root (hi_body's colour attribute `attr`, the nearest vertex),
    not from the baked atlas, where a lying lock of another colour may cover the root (CARD_COLOUR_FROM = 'paint').
    Darkened by `shade` in sRGB like the atlas path; linear RGB per card vertex."""
    hco, _ = S.mesh_arrays(hi_body)
    paint = S.attr_array(hi_body, attr)[:, :3].astype(np.float64)
    kd = KDTree(len(hco))
    for i, p in enumerate(hco):
        kd.insert(Vector(p), i)
    kd.balance()
    roots = S.attr_array(cards, 'root')
    per = roots[::S.CARD_VERTS]
    idx = np.array([kd.find(Vector(r))[1] for r in per], dtype=np.int64)
    lin = paint[np.repeat(idx, S.CARD_VERTS)]
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, None), 1 / 2.4) - 0.055)
    srgb = np.clip(srgb * shade, 0, 1)
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def measured_body_width(P: dict, roll_deg: float) -> float | None:
    """How far the torso's side reaches off the spine line when the body lies on its side, rolled `roll_deg` (a little
    toward the belly): the spine's height in the ko clip (plans/quadruped.py `body_width`). Measured on lo_body at rest
    (the torso between the hips and the chest, above the lower legs); None without a lo_body."""
    body = bpy.data.objects.get('lo_body')
    if body is None or body.type != 'MESH':
        return None
    co, _ = S.mesh_arrays(body)
    sk = float(P.get('size_k', 1.0))
    hz = float(P['hip'][2])
    y0 = min(P['hip'][1], P['chest'][1]) - 0.1 * sk
    y1 = max(P['hip'][1], P['chest'][1]) + 0.1 * sk
    m = (co[:, 1] > y0) & (co[:, 1] < y1) & (co[:, 2] > 0.35 * hz)
    if not m.any():
        return None
    r = math.radians(roll_deg)
    return float((np.abs(co[m, 0]) * math.sin(r) + (hz - co[m, 2]) * math.cos(r)).max())


def posed_lowest(arm, m: A.ClipMeta | None = None, frame: int = 1) -> float | None:
    """The lowest point of lo_body (metres) at rest (m None) or at a clip's frame, evaluated like the game (from the
    rest pose; NLA tracks muted), then the armature is left at rest with its tracks on again."""
    body = bpy.data.objects.get('lo_body')
    ad = arm.animation_data
    if body is None or ad is None:
        return None
    for tr in ad.nla_tracks:
        tr.mute = True
    ad.action = m.action if m is not None else None
    if m is not None and hasattr(m.action, 'slots') and m.action.slots:
        ad.action_slot = m.action.slots[0]
    R.reset_pose(arm)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', co)
    ev.to_mesh_clear()
    ad.action = None
    for tr in ad.nla_tracks:
        tr.mute = False
    R.reset_pose(arm)
    bpy.context.scene.frame_set(1)
    return float(co[2::3].min())


def settle_ko(cb, plan, arm, P: dict, clips: list) -> list:
    """Lay ko on the ground: the last frame exactly (the body's lowest point there against the rest pose's, i.e. the
    feet: ko made again with body_width moved by the difference; the spine lies body_width above the ground), then no
    frame of the fall below it (P['ko_lift']: per moment, the height a frame sinks, added back; never pushed down)."""
    def remake(i: int) -> None:
        ad = arm.animation_data
        for tr in list(ad.nla_tracks):
            if tr.name == 'ko':
                ad.nla_tracks.remove(tr)
        bpy.data.actions.remove(clips[i].action)
        clips[i] = plan.make_clips(cb, P, ['ko'])[0]

    i = next((k for k, m in enumerate(clips) if m.name == 'ko'), None)
    rest = posed_lowest(arm)
    if i is None or 'body_width' not in P or rest is None:
        return clips
    tol = 0.003 * float(P.get('size_k', 1.0))
    for _ in range(2):
        ko = clips[i]
        err = posed_lowest(arm, ko, 1 + ko.frames) - rest
        C.log(f'clips: ko lies {err * 1000:+.0f} mm off the ground (body_width {P["body_width"]:.3f} m)')
        if abs(err) < tol:
            break
        P['body_width'] -= err
        remake(i)
    ko = clips[i]
    sink = [(f - 1) / ko.frames for f in range(1, ko.frames + 2, 2)]
    lows = [posed_lowest(arm, ko, 1 + int(round(t * ko.frames))) for t in sink]
    lift = [max(0.0, rest - lo) for lo in lows]
    if max(lift) > tol:
        # widen each dip a little so the lift eases in and out
        soft = [max(lift[max(0, k - 1):k + 2]) for k in range(len(lift))]
        P['ko_lift'] = [[round(t, 4), round(d, 4)] for t, d in zip(sink, soft)]
        remake(i)
        after = max(rest - posed_lowest(arm, clips[i], 1 + int(round(t * ko.frames))) for t in sink)
        C.log(f'clips: ko fall lifted up to {max(lift) * 1000:.0f} mm; the deepest frame now {after * 1000:+.0f} mm into the ground')
    return clips


def open_blend(out: Path, name: str) -> None:
    path = out / name
    if not path.exists():
        raise SystemExit(f'no {path}: run the earlier stages first')
    bpy.ops.wm.open_mainfile(filepath=str(path))


def check_finite(objs, when: str, weights: bool = False) -> None:
    """Stop in words if a mesh has NaN or infinite vertex positions, normals or (weights) skin weights: a recipe's
    negative base to a fractional power gave Hearthwing's frills NaN positions, seen only as a NaN area in the log;
    they would have broken the bake and shipped. Clean meshes pass untouched."""
    bad = []
    for o in objs:
        if o is None or o.type != 'MESH' or not len(o.data.vertices):
            continue
        me = o.data
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        me.vertices.foreach_get('co', co)
        nn = np.empty(n * 3, np.float32)
        me.vertices.foreach_get('normal', nn)
        k_co = int((~np.isfinite(co.reshape(-1, 3))).any(axis=1).sum())
        k_n = int((~np.isfinite(nn.reshape(-1, 3))).any(axis=1).sum())
        k_w = 0
        if weights and o.vertex_groups:
            k_w = sum(1 for v in me.vertices if any(not math.isfinite(g.weight) for g in v.groups))
        parts = [f'{k} {what}' for k, what in ((k_co, 'vertex positions'), (k_n, 'normals'), (k_w, 'vertices with skin weights')) if k]
        if parts:
            bad.append(f"{o.name}: {', '.join(parts)}")
    if bad:
        raise SystemExit(f"{when}: NaN or infinite numbers in {'; '.join(bad)}. Look at the recipe's shapes for that part (a negative "
                         'number to a fractional power, a division by zero, a zero-length direction) and build again.')


def save_blend(out: Path, name: str) -> None:
    bpy.ops.wm.save_as_mainfile(filepath=str(out / name), compress=False)
    C.log(f'saved {name}')


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return float(x)
    if isinstance(x, (np.integer, int)) and not isinstance(x, bool):
        return int(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x


def _tuples(x):
    if isinstance(x, list):
        return tuple(_tuples(v) for v in x)
    if isinstance(x, dict):
        return {k: _tuples(v) for k, v in x.items()}
    return x


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
    got = M.tri_count(ob)
    if got > target * 1.1:
        # the weighted collapse stalled: too much of the body is protected. A plain decimate from here (what this did
        # before) takes the rest out of the unprotected skin only and flattens it into big facets (Hearthwing grown: 60 cm
        # facets on the chest and belly). A small overshoot is kept as it is; a big one stops the build
        if got > target * DECIMATE_STALL_MAX:
            raise SystemExit(f'{ob.name}: the weighted decimation stopped at {got} triangles, far above the {target} asked for: the keep '
                             'mask (decimate_keep, or the face/toe zones) protects too much, so the collapse has too little left to '
                             'take, and a plain decimate would flatten the unprotected skin into big facets. Protect less (lower '
                             'decimate_keep weights or smaller zones), or raise BODY_TRIS.')
        C.log(f'WARNING weighted decimate stopped at {got} triangles (target {target}): kept as it is; the keep mask protects '
              'a lot (a plain decimate would flatten the unprotected skin)')
    sm = ob.modifiers.new('smooth', 'SMOOTH')
    sm.factor = 0.25
    sm.iterations = 1
    C.apply_modifiers(ob)
    ob.data.shade_smooth()


# the weighted decimation may stop this far over its target (kept as it is, with a warning); further over, the build stops
DECIMATE_STALL_MAX = 1.25
# lo_body's faces: the largest and the 99.9th percentile against the median (healthy builds reach about 1500 and 560;
# Hearthwing grown's flattened chest 9800 and 1485)
FACE_MAX_RATIO = 4000
FACE_P999_RATIO = 1000


def check_faces(ob: bpy.types.Object) -> None:
    """Stop in words when the low body has a few huge faces among small ones: skin flattened into facets."""
    me = ob.data
    area = np.empty(len(me.polygons), np.float32)
    me.polygons.foreach_get('area', area)
    med = float(np.median(area))
    mx, p999 = float(area.max()), float(np.percentile(area, 99.9))
    r_max, r_p = mx / max(med, 1e-12), p999 / max(med, 1e-12)
    C.log(f'{ob.name}: face areas median {med * 1e6:.1f} mm², 99.9th percentile {p999 * 1e6:.0f} mm² ({r_p:.0f}x), largest {mx * 1e6:.0f} mm² ({r_max:.0f}x)')
    if r_max > FACE_MAX_RATIO or r_p > FACE_P999_RATIO:
        c = me.polygons[int(area.argmax())].center
        raise SystemExit(f'{ob.name}: some faces are huge next to the rest (largest {mx * 1e4:.0f} cm², {r_max:.0f}x the median; '
                         f'99.9th percentile {r_p:.0f}x), at ({c.x:.2f}, {c.y:.2f}, {c.z:.2f}): the skin there was flattened into '
                         'facets (a decimation with too much protected elsewhere). Protect less or raise BODY_TRIS.')


# how much of the voxel body the decimated low body must keep: its box on every axis (below it the build stops) and its
# surface area (below it the build warns loudly)
DECIMATE_MIN_BOX = 0.9
DECIMATE_WARN_AREA = 0.8


def check_decimation(ob: bpy.types.Object, box0: np.ndarray, area0: float) -> None:
    """Stop in words when the decimated low body lost part of itself: a keep mask that protects too much leaves the
    collapse nothing to take but whole regions (Cobblemaw's build 1 kept only the head and neck, and nothing said so).
    Healthy builds keep their box and almost all their area; the log says how much."""
    co, _ = S.mesh_arrays(ob)
    box = co.max(axis=0) - co.min(axis=0)
    keep = box / np.maximum(box0, 1e-9)
    area = S.mesh_area(ob) / max(area0, 1e-12)
    C.log(f'{ob.name}: the decimation kept {", ".join(f"{a} {k * 100:.0f}%" for a, k in zip("xyz", keep))} of the box and {area * 100:.0f}% of the area')
    if keep.min() < DECIMATE_MIN_BOX:
        axis = 'xyz'[int(keep.argmin())]
        raise SystemExit(f'{ob.name}: the decimated body lost part of itself: its {axis} extent shrank to {keep.min() * 100:.0f}% of the voxel body'
                         f' ({box[int(keep.argmin())]:.3f} of {box0[int(keep.argmin())]:.3f} m). The keep mask (decimate_keep) '
                         'probably protects too much, so the collapse took whole regions; protect less, or raise BODY_TRIS.')
    if area < DECIMATE_WARN_AREA:
        C.log(f'WARNING {ob.name}: the decimated body kept only {area * 100:.0f}% of the surface area of the voxel body: look at the '
              'shape preview and the sheets; the keep mask (decimate_keep) may protect too much')


def keep_weights(recipe, co: np.ndarray) -> np.ndarray:
    """0..1 per low-body vertex: how much to protect it from decimation (recipe.decimate_keep, else from zones)."""
    if hasattr(recipe, 'decimate_keep'):
        return np.clip(np.asarray(recipe.decimate_keep(co), np.float64), 0, 1)
    keep = np.zeros(len(co))
    if not hasattr(recipe, 'zones'):
        return keep
    z = recipe.zones(co)
    for key, w in (('face', 1.0), ('muzzle', 1.0), ('eye_d', 1.0), ('toes', 0.75), ('paw', 0.25)):
        if key in z:
            keep = keep + ((z[key] < 0.1) if key == 'eye_d' else z[key]) * w
    return np.clip(keep, 0, 1)


def join_parts(parts: list[bpy.types.Object], name: str) -> bpy.types.Object | None:
    """Join a recipe's low parts (membranes, props) into one game mesh, keeping their common per-point attributes (and
    the UNION_ATTRS any part has, zero on the parts without them: a wing's membrane beside other membranes)."""
    if not parts:
        return None
    keep = None
    some: set[str] = set()
    for o in parts:
        have = {a.name for a in o.data.attributes if a.domain == 'POINT' and a.data_type in ('FLOAT', 'FLOAT_VECTOR')
                and not a.name.startswith('.') and a.name != 'position'}
        keep = have if keep is None else keep & have
        some |= have & set(UNION_ATTRS)
    ob = M.join_meshes(parts, name)
    for a in sorted(keep or ()):
        S.add_attr(ob, a, np.concatenate([S.attr_array(o, a) for o in parts]))
    for a in sorted(some - (keep or set())):
        ref = next(S.attr_array(o, a) for o in parts if a in o.data.attributes)
        S.add_attr(ob, a, np.concatenate([S.attr_array(o, a) if a in o.data.attributes else np.zeros((len(o.data.vertices),) + ref.shape[1:], np.float32)
                                          for o in parts]))
    for o in parts:
        bpy.data.objects.remove(o, do_unlink=True)
    return ob


# texels two faces may share before the build stops (2048 grid; slivers touching at a corner make a handful)
UV_OVERLAP_MAX = 32


# a baked colour map is "black" when its islands' median luminance is under this share of the body paint's own
BLACK_BAKE_SHARE = 0.3


def _lum(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def check_not_black(imgs: dict, hi_body, recipe, vs) -> None:
    """Stop in words when a baked colour map came out black: Cycles drops a material it can't compile ('out of SVM
    stack space, shader "paint_base" too big': too many per-pixel mark nodes) and the bake writes black, yet the build
    went on (Starhowl shipped black bodies three times). Each map's median over the islands is compared with the body
    paint's own (hi_body's colour attribute), so a dark coat still passes."""
    ao = BK.image_array(imgs['ao'])
    rows = int(round(ao.shape[0] * BK.STRIP))
    written = ao[rows:, :, 0] > 0.002
    if not written.any():
        return
    checks = [('base_rgba', 'paint', 'the colour map')] + [(f'{short}_rgba', U.variant_attr(vid, recipe.ID), f'variant {short}') for vid, short, _p in vs]
    for img, attr, label in checks:
        if img not in imgs:
            continue
        baked = float(np.median(_lum(BK.image_array(imgs[img])[rows:, :, :3])[written]))
        want = None
        if hi_body is not None and attr in hi_body.data.attributes:
            want = float(np.median(_lum(S.attr_array(hi_body, attr)[:, :3])))
        bad = baked < BLACK_BAKE_SHARE * want if want is not None and want > 0.002 else baked < 0.004
        C.log(f'bake check: {label} median luminance {baked:.3f}' + (f' (the paint {want:.3f})' if want is not None else ''))
        if bad:
            raise SystemExit(f'{label} baked black (median luminance {baked:.3f} over the islands' + (f', the paint {want:.3f}' if want is not None else '')
                             + '): Cycles most likely dropped the body material ("out of SVM stack space, shader paint_base too big" in '
                             'the log): too many per-pixel mark nodes. Use fewer marks, or merge them with lib.marks.union.')


def card_style(recipe):
    """The strip's card tiles: CARD_LAYER_STYLES (one style per card layer: 'fur', 'wool' or 'hair'; mixed styles share
    the six cells) or CARD_STYLE (one for all), default 'fur'."""
    st = getattr(recipe, 'CARD_LAYER_STYLES', None)
    if st:
        st = tuple(st)
        return st[0] if len(set(st)) == 1 else st
    return getattr(recipe, 'CARD_STYLE', 'fur')


def mark_own_uvs(parts: list[bpy.types.Object]) -> bool:
    """When any low part carries the custom property own_uv (its own unwrap in the UV layer 'UVMap'), give every part
    the FACE attribute own_uv (1 on those parts, 0 elsewhere) so the joined mesh knows which faces keep their UVs."""
    if not any(o.get('own_uv') for o in parts):
        return False
    for o in parts:
        me = o.data
        if o.get('own_uv') and 'UVMap' not in me.uv_layers:
            raise SystemExit(f"{o.name}: own_uv is set but there is no UV layer 'UVMap'")
        if 'own_uv' in me.attributes:
            me.attributes.remove(me.attributes['own_uv'])
        a = me.attributes.new('own_uv', 'FLOAT', 'FACE')
        a.data.foreach_set('value', np.full(len(me.polygons), 1.0 if o.get('own_uv') else 0.0, np.float32))
        if 'UVMap' not in me.uv_layers:
            me.uv_layers.new(name='UVMap')
    return True


# ----------------------------------------------------------------------------- build
def stage_build(recipe, out: Path, quick: bool, body_tris: int) -> dict:
    C.clear_scene()
    t0 = time.time()
    vox = {**VOXELS_DEFAULT, **getattr(recipe, 'VOXELS', {})}
    hi_vox = vox['hi_quick'] if quick else vox['hi']
    extras = getattr(recipe, 'body_extras', lambda: [])
    with C.Timer('high body'):
        hi_body = S.build_body('hi_body', recipe.all_parts(), hi_vox, 4, segments=48, extra=extras())
        if hasattr(recipe, 'carve'):
            recipe.carve(hi_body)
        else:
            S.base_attrs(hi_body, S.mesh_arrays(hi_body)[0])
    with C.Timer('low body'):
        lo_body = S.build_body('lo_body', recipe.all_parts(), vox['lo'], 4, segments=40, extra=extras())
        if hasattr(recipe, 'carve_low'):
            # big relief that must reach the silhouette (cobbles): the low body takes it before the decimation
            recipe.carve_low(lo_body)
        co, _ = S.mesh_arrays(lo_body)
        box0, area0 = co.max(axis=0) - co.min(axis=0), S.mesh_area(lo_body)
        decimate_keep(lo_body, body_tris, keep_weights(recipe, co))
        check_decimation(lo_body, box0, area0)
        check_faces(lo_body)
        if lo_body.data.validate(verbose=False):
            C.log('lo_body: validate() fixed invalid geometry')
        C.log(f'lo_body: {M.tri_count(lo_body)} tris')
    if hasattr(recipe, 'body_extras'):
        # heat weights can't be solved over thin extras (the ear slabs): the rig skins a proxy body without them and
        # copies its weights to lo_body by the nearest vertex (P1.2)
        with C.Timer('weight proxy'):
            proxy = S.build_body('lo_proxy', recipe.all_parts(), vox['lo'], 4, segments=40)
            S.decimate_to(proxy, 24000, smooth_after=0.0)
            proxy.data.validate(verbose=False)
            proxy.hide_render = True
    hi_eyes = [recipe.build_eye(f'hi_eye{"L" if s > 0 else "R"}', s, True) for s in (1, -1)]
    lo_eyes_parts = [recipe.build_eye(f'lo_eye{"L" if s > 0 else "R"}', s, False) for s in (1, -1)]
    fin_fn = getattr(recipe, 'build_fins', None)
    hi_fins = list(fin_fn(True, quick)) if fin_fn else []
    lo_fins_parts = list(fin_fn(False, quick)) if fin_fn else []
    prop_fn = getattr(recipe, 'build_props', None)
    hi_props = list(prop_fn(True, quick)) if prop_fn else []
    lo_props_parts = list(prop_fn(False, quick)) if prop_fn else []
    # the bake finds the membranes and the props by these attributes (any object names work)
    for o in hi_fins:
        S.add_attr(o, 'membrane', np.ones(len(o.data.vertices)))
    for o in hi_props:
        S.add_attr(o, 'prop_src', np.ones(len(o.data.vertices)))
    # props one variant alone wears (VARIANTS[vid]['props']): their own game mesh lo_props_<short>, and no occluders
    owners = U.variant_prop_owners(recipe)
    for name, short in owners.items():
        for tag, objs in (('hi', hi_props), ('lo', lo_props_parts)):
            if not any(U.prop_owner(o, {name: short}) for o in objs):
                raise SystemExit(f"variant {short!r} lists prop {name!r}, but build_props({tag == 'hi'}, ...) made no {tag}_{name}* object")
    variant_hi_props = {short: [o.name for o in hi_props if U.prop_owner(o, owners) == short] for short in dict.fromkeys(owners.values())}

    # the coat: lying locks (baked) on the source; soft cards and the tuft on the game mesh
    lies: list[bpy.types.Object] = []
    lock_counts: dict[str, int] = {}
    tpls = getattr(recipe, 'LOCK_TEMPLATES', {})
    with C.Timer('locks'):
        for name, fn_name, seed, tpl_d in LOCK_LAYERS:
            fn = getattr(recipe, fn_name, None)
            if fn is None:
                continue
            nu, nv, ridges, strand = tpls.get(name, tpl_d)
            tpl = S.lock_template(nu, nv, ridges, strand=strand, closed=False)
            ob, _ = S.scatter_layer(f'hi_locks_{name}', hi_body, fn, recipe.flow, seed, tpl, quick, 0.085, 0.04, S.KIND_LOCK)
            lies.append(ob)
            lock_counts[name] = S.element_count(ob, len(tpl[0]))
    lo_cards = None
    n_layers: list[int] = []
    card_layers = int(getattr(recipe, 'CARD_LAYERS', 2)) if hasattr(recipe, 'card_params') else 0
    if card_layers:
        with C.Timer('cards'):
            tpl_card = S.card_template()
            layers = []
            for layer in range(card_layers):
                ob, _ = S.scatter_layer(f'lo_cards_{layer}', hi_body, lambda p, n, layer=layer: recipe.card_params(p, n, layer), recipe.flow,
                                        31 + layer, tpl_card, quick, 0.0, 0.02, S.KIND_CARD, jitter_deg=9.0)
                S.add_attr(ob, 'layer', np.full(len(ob.data.vertices), float(layer)))
                layers.append(ob)
            n_layers = [S.element_count(o, S.CARD_VERTS) for o in layers]
            lo_cards = S.join_elements(layers, 'lo_cards', attrs=S.ELEMENT_ATTRS + ('layer',))
    hi_tuft = lo_tuft = None
    tuft_n = 0
    tuft_fn = getattr(recipe, 'tuft_frames', None)
    if tuft_fn:
        tuft_fr = tuft_fn(hi_body)
        tuft_n = len(tuft_fr['P'])
        if tuft_n:
            shape = {**TUFT_DEFAULT, **getattr(recipe, 'TUFT_SHAPE', {})}
            nu, nv, ridges, strand = shape['template']
            tpl_tuft_hi = S.lock_template(nu, nv, ridges, strand=strand)
            hi_tuft = S.elements_object('hi_tuft', S.instance(tpl_tuft_hi, tuft_fr, shape['thickness'], shape['bury']), tpl_tuft_hi, tuft_fr['P'],
                                        S.KIND_TUFT, np.random.default_rng(3), tuft_fr['N'])
            tpl_tuft_lo = S.low_strand_template()
            lo_tuft = S.elements_object('lo_tuft', S.instance(tpl_tuft_lo, tuft_fr, shape['thickness'], shape['bury']), tpl_tuft_lo, tuft_fr['P'],
                                        S.KIND_TUFT, np.random.default_rng(3), tuft_fr['N'])
    body_srcs = [hi_body] + lies + ([hi_tuft] if hi_tuft is not None else [])

    # paint every source (numpy): base, variants and roughness, as colour attributes the bake reads
    with C.Timer('paint'):
        marks_fn = getattr(recipe, 'make_marks', None) or getattr(recipe, 'make_dapples', None)
        marks = marks_fn(hi_body) if marks_fn else None
        (out / 'marks.json').write_text(json.dumps(_jsonable(marks)), encoding='utf-8')
        if hi_props:
            recipe.paint_sources(body_srcs, hi_fins, props=hi_props)
        else:
            recipe.paint_sources(body_srcs, hi_fins)
        want = ['paint', 'rough'] + [U.variant_attr(vid, recipe.ID) for vid, _s, _p in variants(recipe)]
        for o in body_srcs + hi_fins + hi_props:
            lack = [a for a in want if a not in o.data.attributes]
            if lack:
                raise SystemExit(f'paint_sources left {o.name} without {", ".join(lack)} (RECIPE.md: paint, rough, paint_<short>)')

    # the game meshes, joined per kind; the body atlas (UVMap) with the strip kept at the bottom
    lo_eyes = M.join_meshes(lo_eyes_parts, 'lo_eyes')
    for o in lo_eyes_parts:
        bpy.data.objects.remove(o, do_unlink=True)
    # recipe-supplied unwraps (a low part with the custom property own_uv = True and its UVs in 'UVMap': a horn or a rope
    # unrolled as one strip) survive the join as the face attribute own_uv and stay out of the smart projection
    own_any = mark_own_uvs(lo_fins_parts + lo_props_parts)
    lo_fins = join_parts(lo_fins_parts, 'lo_fins')
    # group the low props by wearer first: joining consumes the parts
    lo_owner = [(o, U.prop_owner(o, owners)) for o in lo_props_parts]
    lo_props = join_parts([o for o, w in lo_owner if w is None], 'lo_props')
    lo_vprops = {f'lo_props_{short}': join_parts([o for o, w in lo_owner if w == short], f'lo_props_{short}') for short in variant_hi_props}
    lows = [lo_body, lo_eyes] + [o for o in (lo_fins, lo_props, *lo_vprops.values()) if o is not None]
    with C.Timer('uv'):
        for o in lows:
            keep_uv = own_any and 'own_uv' in o.data.attributes and 'UVMap' in o.data.uv_layers
            for uvl in [u for u in o.data.uv_layers if not (keep_uv and u.name == 'UVMap')]:
                o.data.uv_layers.remove(uvl)
            if not keep_uv:
                o.data.uv_layers.new(name='UVMap')
        uv_smooth = int(getattr(recipe, 'UV_SMOOTH', 0) or 0)
        if uv_smooth > 0:
            # unwrap a heavily smoothed twin of lo_body (same topology: the vertices moved for the unwrap only), so a
            # lumpy coat unwraps into far fewer, larger islands; uv_smooth_mask(co) 0..1 keeps the face and ears as they are
            body_co, _ = S.mesh_arrays(lo_body)
            mask = recipe.uv_smooth_mask(body_co) if hasattr(recipe, 'uv_smooth_mask') else None
            S.set_positions(lo_body, S.laplacian_positions(lo_body, uv_smooth, 0.5, mask))
        if hasattr(recipe, 'texel_k'):
            # the recipe's per-face texel density on lo_body (texel_k(face centres) -> k; the head 1.6, the belly 0.7)
            fc = np.empty(len(lo_body.data.polygons) * 3, np.float32)
            lo_body.data.polygons.foreach_get('center', fc)
            k = np.asarray(recipe.texel_k(fc.reshape(-1, 3).astype(np.float64)), np.float64)
            if 'texel_k' in lo_body.data.attributes:
                lo_body.data.attributes.remove(lo_body.data.attributes['texel_k'])
            lo_body.data.attributes.new('texel_k', 'FLOAT', 'FACE').data.foreach_set('value', k.astype(np.float32))
        pack_opts = {'keep_faces': 'own_uv'} if own_any else {}
        if getattr(recipe, 'ATLAS_ANGLE', None):
            pack_opts['angle_deg'] = float(recipe.ATLAS_ANGLE)        # smart-project's angle limit (default 62°)
        BK.pack_atlas(lows, 'UVMap', atlas_strip(recipe), density=getattr(recipe, 'ATLAS_DENSITY', None), **pack_opts)
        if uv_smooth > 0:
            S.set_positions(lo_body, body_co)
            lo_body.data.shade_smooth()
            C.log(f'uv: lo_body unwrapped smoothed ({uv_smooth} steps{", masked" if mask is not None else ""})')
        # no two faces may share texels (both would bake into the same pixels): the packer repairs what it can; a few
        # texels (slivers touching) pass, more stop the build in words
        uv_overlaps = {}
        for o in lows:
            texels, faces = BK.uv_overlap_faces(o, 'UVMap')
            uv_overlaps[o.name] = texels
            if texels:
                C.log(f'uv: {o.name} has {texels} texels shared by two faces ({len(faces)} faces)')
            if texels > UV_OVERLAP_MAX:
                raise SystemExit(f'{o.name}: {texels} atlas texels are claimed by two faces at once ({len(faces)} faces), so both '
                                 'would bake into the same pixels, and the packer could not pull them apart. Look at the '
                                 'part\'s own unwrap (own_uv / tube_uvs: one tube per call, caps included) or its fold.')
        if lo_cards is not None:
            st = card_style(recipe)
            mixed = not isinstance(st, str) and len(set(st)) > 1
            BK.strip_uvs(lo_cards, BK.CARD_CELLS, by_layer=BK.layer_cells(st, card_layers) if mixed else None)
        if lo_tuft is not None:
            BK.strip_uvs(lo_tuft, BK.LOCK_CELLS)
    game = {'lo_body': lo_body, 'lo_eyes': lo_eyes, 'lo_fins': lo_fins, 'lo_cards': lo_cards, 'lo_tuft': lo_tuft, 'lo_props': lo_props, **lo_vprops}
    present = {n: k for n, k in MESH_KINDS.items() if game.get(n) is not None}
    present.update({n: 'prop' for n, o in lo_vprops.items() if o is not None})
    stats = {
        'quick': quick,
        'hi_tris': sum(M.tri_count(o) for o in body_srcs + hi_eyes + hi_fins + hi_props),
        'lying_locks': lock_counts,
        'tris': {n: M.tri_count(game[n]) for n in present},
        'cards': {'total': S.element_count(lo_cards, S.CARD_VERTS) if lo_cards is not None else 0, 'layers': n_layers},
        'tuft_locks': tuft_n,
        'uv_overlap_texels': uv_overlaps,
        'marks': len(marks) if hasattr(marks, '__len__') else 0,
        'areas_m2': {'body': S.mesh_area(lo_body), 'eyes': S.mesh_area(lo_eyes), **({'fins': S.mesh_area(lo_fins)} if lo_fins else {}),
                     **({'props': S.mesh_area(lo_props)} if lo_props else {})},
        'meshes': present,
        'sources': {'body': [o.name for o in body_srcs], 'eyes': [o.name for o in hi_eyes], 'fins': [o.name for o in hi_fins],
                    'props': [o.name for o in hi_props], 'variant_props': variant_hi_props},
        'seconds': round(time.time() - t0),
    }
    stats['tris']['total'] = sum(stats['tris'].values())
    if atlas_strip(recipe) != BK.STRIP:
        stats['atlas_strip'] = atlas_strip(recipe)
    C.log(json.dumps(stats))
    (out / 'stats_build.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    check_finite([o for o in bpy.data.objects if o.name.startswith(('hi_', 'lo_'))], 'build')
    save_blend(out, 'build.blend')
    return stats


# ----------------------------------------------------------------------------- bake
def tuft_hex(recipe, pal: dict) -> str:
    if hasattr(recipe, 'tuft_colour'):
        return recipe.tuft_colour(pal)
    if hasattr(recipe, 'colours'):
        return recipe.colours(pal)['tuft']
    return pal['body']


def stage_bake(recipe, out: Path, quick: bool, atlas_px: int, with_cpu: bool = False, cpu: bool = False) -> dict:
    open_blend(out, 'build.blend')
    O = bpy.data.objects
    dev = BK.use_cpu() if cpu else BK.use_gpu(with_cpu) + ('+CPU' if with_cpu else '')
    BK.bake_world(0.05)
    C.log(f'bake device {dev}, body atlas {atlas_px}²')
    built = json.loads((out / 'stats_build.json').read_text(encoding='utf-8'))
    src = built.get('sources') or {'body': ['hi_body', 'hi_locks_head', 'hi_locks_body', 'hi_tuft']}
    body_srcs = [O[n] for n in src['body'] if n in O]
    eyes = [O['hi_eyeL'], O['hi_eyeR']]
    fins = [o for o in O if o.type == 'MESH' and o.name.startswith('hi_') and 'membrane' in o.data.attributes]
    props = [o for o in O if o.type == 'MESH' and o.name.startswith('hi_') and 'prop_src' in o.data.attributes]
    vsrc = {short: [O[n] for n in names] for short, names in (src.get('variant_props') or {}).items()}
    vnames = {o.name for objs in vsrc.values() for o in objs}
    worn = [o for o in props if o.name not in vnames]          # always worn: they occlude the body
    lo_body, lo_eyes = O['lo_body'], O['lo_eyes']
    lo_fins, lo_props = O.get('lo_fins'), O.get('lo_props')
    vs = variants(recipe)
    mpath = out / 'marks.json'
    marks = _tuples(json.loads(mpath.read_text(encoding='utf-8'))) if mpath.exists() else None
    mats = {'base': recipe.body_material('paint_base', 'paint', recipe.PALETTE, marks)}
    for vid, short, pal in vs:
        mats[short] = recipe.body_material(f'paint_{short}', U.variant_attr(vid, recipe.ID), pal, marks)
    mats['rough'] = BK.emission_attr_material('paint_rough', 'rough')
    for kind, objs in (('fin', fins), ('prop', props)):
        if objs:
            mats[f'{kind}_base'] = BK.emission_attr_material(f'{kind}_base', 'paint')
            for vid, short, _pal in vs:
                mats[f'{kind}_{short}'] = BK.emission_attr_material(f'{kind}_{short}', U.variant_attr(vid, recipe.ID))
    if props and hasattr(recipe, 'prop_material'):
        # prop_material(name, attr, pal, marks): the props' colour per pixel, like body_material (Petalphant's petal ears),
        # instead of only their vertex paint
        mats['prop_base'] = recipe.prop_material('prop_base', 'paint', recipe.PALETTE, marks)
        for vid, short, pal in vs:
            mats[f'prop_{short}'] = recipe.prop_material(f'prop_{short}', U.variant_attr(vid, recipe.ID), pal, marks)
    mats['eye'] = recipe.eye_material('eye_paint')
    mats['eye_rough'] = recipe.eye_material('eye_rough', True)
    if len(inspect.signature(recipe.eye_material).parameters) >= 3:
        # eye_material(name, rough_pass, pal): each variant's eyes in its own colours (its palette's 'eye')
        mats['eye'] = recipe.eye_material('eye_paint', False, recipe.PALETTE)
        for vid, short, pal in vs:
            mats[f'eye_{short}'] = recipe.eye_material(f'eye_{short}', False, pal)

    def paint(pass_name: str) -> None:
        if pass_name == 'rough':
            BK.set_material(body_srcs + fins + props, mats['rough'])
            BK.set_material(eyes, mats['eye_rough'])
        else:
            BK.set_material(body_srcs, mats[pass_name])
            if fins:
                BK.set_material(fins, mats[f'fin_{pass_name}'])
            if props:
                BK.set_material(props, mats[f'prop_{pass_name}'])
            BK.set_material(eyes, mats.get(f'eye_{pass_name}', mats['eye']))

    samples = (2, 12, 2) if quick else (6, 24, 4)
    # P1.2: the eyes don't shadow the body: the skin under a lens is the closed lid a blink shows (it baked black)
    # variant-only props are never occluders (no collar of AO in the base or any variant's atlas)
    # MEMBRANE_AO_BODY = False: the membranes don't shade the body's AO (folded wings would leave a flank shadow that
    # stays when they spread); the default keeps them (Puddlepup's ear linings)
    body_occ = body_srcs + (fins if getattr(recipe, 'MEMBRANE_AO_BODY', True) else []) + worn
    plan = [(lo_body, body_srcs, body_occ), (lo_eyes, eyes, eyes + body_srcs)]
    if lo_fins is not None:
        plan.append((lo_fins, fins, fins))
    if lo_props is not None:
        plan.append((lo_props, worn, worn + body_srcs))
    for short, objs in vsrc.items():
        plan.append((O[f'lo_props_{short}'], objs, objs + body_srcs))
    t0 = time.time()
    with_strip = float(built.get('atlas_strip', BK.STRIP)) > 0
    style = card_style(recipe)
    ao_opts = {k: float(getattr(recipe, n)) for k, n in (('ao_floor', 'AO_FLOOR'), ('ao_soften', 'AO_SOFTEN')) if getattr(recipe, n, 0)}
    imgs = BK.bake_set('atlas', atlas_px, out, plan, 'UVMap', with_strip, paint, samples, extra_colours=tuple(s for _v, s, _p in vs),
                       **({'card_style': style} if style != 'fur' else {}), **ao_opts)
    base = BK.image_array(imgs['base_rgba'])
    check_not_black(imgs, O.get('hi_body'), recipe, vs)
    lo_cards, lo_tuft = O.get('lo_cards'), O.get('lo_tuft')
    shade = getattr(recipe, 'CARD_SHADE', 0.88)
    card_from = getattr(recipe, 'CARD_COLOUR_FROM', 'atlas')
    if lo_cards is not None and card_from == 'skin' and O.get('hi_body') is not None:
        # the bare skin under each card's root (one extra colour bake per variant): no lying lock of another colour
        ao_arr = BK.image_array(imgs['ao'])
        BK.sample_vertex_colours(lo_cards, lo_body, skin_colour(lo_body, O['hi_body'], paint, 'base', atlas_px, ao_arr, samples[2]), 'Col',
                                 active=True, scale=shade)
        for vid, short, _pal in vs:
            BK.sample_vertex_colours(lo_cards, lo_body, skin_colour(lo_body, O['hi_body'], paint, short, atlas_px, ao_arr, samples[2]),
                                     U.variant_colour_attr(vid, recipe.ID), active=False, scale=shade)
        C.log('cards: coloured from the bare skin at their roots (CARD_COLOUR_FROM = skin)')
    elif lo_cards is not None and card_from == 'paint' and O.get('hi_body') is not None:
        # the skin's own paint at each card's root (no lying lock of another colour in the way); the per-pixel marks
        # (body_material) are not in it
        S.set_colour_attr(lo_cards, 'Col', card_colours_from_paint(lo_cards, O['hi_body'], 'paint', shade), active=True)
        for vid, short, _pal in vs:
            S.set_colour_attr(lo_cards, U.variant_colour_attr(vid, recipe.ID), card_colours_from_paint(lo_cards, O['hi_body'], U.variant_attr(vid, recipe.ID), shade))
        C.log('cards: coloured from the paint at their roots (CARD_COLOUR_FROM = paint)')
    elif lo_cards is not None:
        # a touch darker than the skin under them: lit edge-on by the rims, cream cards glittered white (review 1)
        BK.sample_vertex_colours(lo_cards, lo_body, base, 'Col', active=True, scale=shade)
        for vid, short, _pal in vs:
            BK.sample_vertex_colours(lo_cards, lo_body, BK.image_array(imgs[f'{short}_rgba']), U.variant_colour_attr(vid, recipe.ID),
                                     active=False, scale=shade)
    if lo_tuft is not None and hasattr(recipe, 'tuft_colours'):
        # a per-vertex tuft colour (a root-to-tip gradient): tuft_colours(pal, tpos 0 root..1 tip, lrand) -> n x 3 linear RGB
        tp = S.attr_array(lo_tuft, 'tpos').astype(np.float64)
        lr = S.attr_array(lo_tuft, 'lrand').astype(np.float64)
        S.set_colour_attr(lo_tuft, 'Col', np.asarray(recipe.tuft_colours(recipe.PALETTE, tp, lr), np.float64), active=True)
        for vid, _short, pal in vs:
            S.set_colour_attr(lo_tuft, U.variant_colour_attr(vid, recipe.ID), np.asarray(recipe.tuft_colours(pal, tp, lr), np.float64))
    elif lo_tuft is not None:
        # round 6: the tuft is one flat colour and never blows out (a sampled crown colour with the lock's sheen read near white)
        n = len(lo_tuft.data.vertices)
        S.set_colour_attr(lo_tuft, 'Col', np.tile(S.v3(C.lin_rgb(tuft_hex(recipe, recipe.PALETTE))), (n, 1)), active=True)
        for vid, _short, pal in vs:
            S.set_colour_attr(lo_tuft, U.variant_colour_attr(vid, recipe.ID), np.tile(S.v3(C.lin_rgb(tuft_hex(recipe, pal))), (n, 1)))
    res = {'device': dev, 'atlas_px': atlas_px, 'variants': [s for _v, s, _p in vs], 'seconds': round(time.time() - t0)}
    # coverage: emission 1 on every source, the same bakes (cage, distance, UVs): 0 where every ray missed (deep crevices,
    # where the colour baked black and the roughness 0: a mirror in the game). tools/art/ultra-pad.ts treats those texels
    # as unwritten and fills them from their neighbours; a breed without misses ships byte-identical.
    with C.Timer('coverage'):
        cimg = new_image('atlas_coverage', atlas_px, alpha=False, color=(0.0, 0.0, 0.0, 1.0), srgb=False)
        one, nb1 = new_mat('coverage_one')
        em1 = nb1.new('ShaderNodeEmission')
        em1.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        nb1.output(em1.outputs[0])
        BK.set_material(body_srcs + eyes + fins + props, one)
        for k, (low, src, _occ) in enumerate(plan):
            BK.bake('EMIT', low, src, cimg, 1, clear=k == 0)
        BK.save_png(cimg, out / 'atlas_coverage.png')
        cov = BK.image_array(cimg)[..., 0]
        orm_now = BK.image_array(imgs['orm'])
        base_now = BK.image_array(imgs['base_rgba'])
        # a missed texel inside an island: a bake wrote AO there, but no source answered the rays
        missed = (cov < 0.5) & (orm_now[..., 0] > 0.004) & (base_now[..., :3].max(axis=-1) < 0.004)
        res['coverage'] = {'missedTexels': int(missed.sum())}
        C.log(f'coverage: {int(missed.sum())} island texels where every bake ray missed (ultra-pad fills them from their neighbours)')
    glow = getattr(recipe, 'GLOW', None)
    if glow is not None:
        # the glow pass: the sources' `glow` attribute (0 where a source has none) and the recipe's per-pixel marks
        # (glow_material) baked on the same UVs, written into the ORM's alpha (A = glow mask; the runtime's emissive is
        # base colour x mask x strength). Shared by every variant, like the normal and ORM maps.
        with C.Timer('glow'):
            gimg = new_image('atlas_glowpass', atlas_px, alpha=False, color=(0.0, 0.0, 0.0, 1.0), srgb=False)
            g_attr = MK.glow_material('glow_attr')
            g_body = recipe.glow_material('glow_body', marks) if hasattr(recipe, 'glow_material') else g_attr
            BK.set_material(body_srcs, g_body)
            BK.set_material(eyes + fins + props, g_attr)
            for k, (low, src, _occ) in enumerate(plan):
                BK.bake('EMIT', low, src, gimg, samples[2], clear=k == 0)
            orm = BK.image_array(imgs['orm']).copy()
            g = np.clip(BK.image_array(gimg)[..., 0], 0.0, 1.0)
            orm[..., 3] = g
            BK.save_png(BK.image_from_array('atlas_orm_glow', orm, srgb=False, alpha=True), out / 'atlas_orm.png')
        res['glow'] = {'strength': float(glow.get('strength', 1.0)), 'tint': glow.get('tint'), 'coverage': round(float((g > 0.05).mean()), 5)}
        C.log(f"glow: {res['glow']['coverage'] * 100:.2f}% of the atlas glows (ORM alpha)")
    vorm = variant_orm(recipe)
    if vorm:
        res['variant_orm'] = {}
        shared = BK.image_array(imgs['orm']).copy()
        rows = int(round(shared.shape[0] * BK.STRIP)) if with_strip else 0
        everything = body_srcs + fins + props
        for vid, short, pal in vs:
            if short not in vorm:
                continue
            opts = vorm[short]
            with C.Timer(f'orm {short}'):
                # the variant's roughness and coat (rough_<short>, else the shared 'rough'), on the same UVs
                ra = f'rough_{short}' if all(f'rough_{short}' in o.data.attributes for o in everything) else 'rough'
                rimg = new_image(f'atlas_rc_{short}', atlas_px, alpha=False, color=(0.0, 0.0, 0.0, 1.0), srgb=False)
                BK.set_material(everything, BK.emission_attr_material(f'paint_rough_{short}', ra))
                BK.set_material(eyes, mats['eye_rough'])
                for k, (low, src_objs, _occ) in enumerate(plan):
                    BK.bake('EMIT', low, src_objs, rimg, samples[2], clear=k == 0)
                rc = BK.image_array(rimg)
                orm_v = shared.copy()
                # the islands take the variant's roughness and coat; the AO and the strip's tiles stay the breed's
                orm_v[rows:, :, 1] = rc[rows:, :, 1]
                orm_v[rows:, :, 2] = rc[rows:, :, 2]
                vglow = opts.get('glow')
                if vglow is not None:
                    # the variant's own glow mask: glow_<short> on the sources (else none) and glow_material(name, marks, pal)
                    gattr = f'glow_{short}'
                    gv = new_image(f'atlas_glowpass_{short}', atlas_px, alpha=False, color=(0.0, 0.0, 0.0, 1.0), srgb=False)
                    g_attr_v = MK.glow_material(f'glow_attr_{short}', attr=gattr)
                    gm = getattr(recipe, 'glow_material', None)
                    g_body_v = gm(f'glow_body_{short}', marks, pal) if gm and len(inspect.signature(gm).parameters) >= 3 else g_attr_v
                    BK.set_material(body_srcs, g_body_v)
                    BK.set_material(eyes + fins + props, g_attr_v)
                    for k, (low, src_objs, _occ) in enumerate(plan):
                        BK.bake('EMIT', low, src_objs, gv, samples[2], clear=k == 0)
                    gvals = np.clip(BK.image_array(gv)[..., 0], 0.0, 1.0)
                    orm_v[..., 3] = gvals
                    spec = {'strength': float(vglow.get('strength', 1.0)), 'tint': vglow.get('tint'), 'coverage': round(float((gvals > 0.05).mean()), 5)}
                elif glow is not None:
                    orm_v[..., 3] = g                       # the breed's glow mask and spec, as on the usual look
                    spec = res['glow']
                else:
                    spec = None
                alpha = spec is not None
                BK.save_png(BK.image_from_array(f'atlas_{short}_orm', orm_v, srgb=False, alpha=alpha),
                            out / f'atlas_{short}_orm.png')
                res['variant_orm'][short] = {'glow': spec, 'rough': ra}
                C.log(f'orm {short}: its own roughness and coat ({ra})' + (f", glow {spec['coverage'] * 100:.2f}% of the atlas" if spec else ', no glow'))
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


def skin_body(body, proxy, arm, specs, retry=None, report: dict | None = None) -> tuple[list[str], np.ndarray]:
    """Heat weights for the body, as (group names, verts × groups). With a proxy (the body without its thin extras),
    the solve runs on the proxy and every body vertex copies its nearest proxy vertex. When heat leaves most bones
    empty (P1.2: the ear slabs; big bodies: Blender's solve fails quietly on a fine proxy, Cobblemaw needed a 9 mm
    voxel), `retry(mult)` builds coarser proxies to try in turn; distance weights only when every one fails. The log
    says loudly which weights were used, and `report` gets {'method', 'source'}."""
    src = proxy if proxy is not None else body
    deform = [s.name for s in specs if s.deform]

    def heat(ob) -> bool:
        if not R.skin_auto(ob, arm):
            return False
        _bn, W = S.body_weights(ob)
        filled = int((W.max(axis=0) > 0.01).sum())
        if filled < len(deform) // 2:
            C.log(f'WEIGHTS: heat on {ob.name} left {len(deform) - filled} of {len(deform)} bones without weight')
            return False
        return True
    ok = heat(src)
    if not ok and retry is not None:
        for mult in (1.6, 2.4):
            C.log(f'WEIGHTS: heat weights FAILED on {src.name}; trying a coarser proxy (voxel x {mult:g})')
            cand = retry(mult)
            if cand is None:
                break
            if heat(cand):
                proxy, src, ok = cand, cand, True
                break
            bpy.data.objects.remove(cand, do_unlink=True)
    if ok:
        C.log(f'WEIGHTS: heat weights, solved on {src.name} ({len(src.data.vertices)} verts)')
    else:
        C.log(f'WEIGHTS: DISTANCE WEIGHTS on {src.name}: heat failed on every proxy, so the skin bends more crudely '
              '(look for thin or intersecting parts, or set VOXELS["proxy"] coarser)')
        R.skin_distance(src, arm, specs)
    if report is not None:
        report.update({'method': 'heat' if ok else 'distance', 'source': src.name})
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


def default_body_regions(recipe, co: np.ndarray, names: list[str]) -> list:
    """Puddlepup's: the ear flaps follow head → ear.1 → ear.2 by the flap's u (like the membranes), and the tail zone
    follows the tail chain by how far along it lies. Each part only if the recipe has its functions."""
    regs = []
    if hasattr(recipe, 'ear_zone') and hasattr(recipe, 'ear_weights') and 'ear.L.1' in names:
        ear, ear_u = recipe.ear_zone(co)
        for s, tag in ((1, 'L'), (-1, 'R')):
            on = ear & (np.sign(co[:, 0]) == s)
            if on.any():
                w = recipe.ear_weights(co[on], ear_u[on])
                regs.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    if hasattr(recipe, 'tail_weights') and hasattr(recipe, 'zones'):
        zt = recipe.zones(co).get('tail')
        if zt is not None and zt.any():
            regs.append((zt, recipe.tail_weights(co[zt])))
    return regs


def default_fin_regions(recipe, co: np.ndarray, attr, names: list[str]) -> list:
    """Puddlepup's: fin_part ±1 = the left / right ear lining (head → ear.1 → ear.2 by fan u), 2 = the tail fluke."""
    try:
        part = attr('fin_part')
        fan = attr('fan')
    except KeyError as e:
        raise SystemExit(f'lo_fins has no {e}: give the membranes fin_part and fan, or define fin_weight_regions (RECIPE.md)') from e
    regs = []
    if hasattr(recipe, 'ear_weights') and 'ear.L.1' in names:
        for s, tag in ((1, 'L'), (-1, 'R')):
            on = np.abs(part - s) < 0.1
            w = recipe.ear_weights(co[on], fan[on, 0])
            regs.append((on, {'head': w['head'], f'ear.{tag}.1': w['1'], f'ear.{tag}.2': w['2']}))
    on = part > 1.5
    if on.any():
        regs.append((on, recipe.tail_weights(co[on])))
    return regs


def attr_reader(ob: bpy.types.Object):
    """attr(name) → the mesh's per-point attribute as an array; KeyError when it has none."""
    def attr(name: str) -> np.ndarray:
        if name not in ob.data.attributes:
            raise KeyError(name)
        return S.attr_array(ob, name)
    return attr


def apply_regions(W: np.ndarray, regions, names: list[str], what: str) -> None:
    """Each region (mask, {bone: weights over the masked rows}) first clears its rows, then sets its bones."""
    for mask, wd in regions:
        mask = np.asarray(mask, bool)
        W[mask] = 0.0
        for bone, w in wd.items():
            if bone not in names:
                raise SystemExit(f'{what}: weight region names bone {bone!r}, not in the rig ({", ".join(names)})')
            W[mask, names.index(bone)] = w


def review_frame(recipe, mn, mx, P: dict) -> dict:
    """The review framing: the recipe's REVIEW, else from the body's bounds and the head."""
    rv = getattr(recipe, 'REVIEW', None)
    if rv:
        return {'centre': [float(v) for v in rv['centre']], 'size': float(rv['size']),
                'head': {'target': [float(v) for v in rv['head'][0]], 'size': float(rv['head'][1])}}
    ext = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
    hc, hr = Vector(P['head_c']), P['head_r']
    return {'centre': [0.0, round((mn.y + mx.y) / 2, 4), round(mx.z * 0.5, 4)], 'size': round(ext * 1.28, 4),
            'head': {'target': [0.0, round(hc.y - hr * 0.25, 4), round(hc.z, 4)], 'size': round(hr * 4.6, 4)}}


def stage_rig(recipe, plan, out: Path) -> dict:
    open_blend(out, 'baked.blend')
    O = bpy.data.objects
    P = rig_params(recipe)
    specs = plan.rig_specs(P) + eye_bone_specs(recipe)
    arm = R.build_armature(f'{recipe.ID}_rig', specs)
    align_eye_bones(recipe, arm)
    names = [s.name for s in specs if s.deform]
    body = O['lo_body']
    vox = {**VOXELS_DEFAULT, **getattr(recipe, 'VOXELS', {})}

    def coarser_proxy(mult: float):
        # the heat solve's fallback: a coarser proxy body (scaled with the breed's size too); none without all_parts
        if not hasattr(recipe, 'all_parts'):
            return None
        v = float(vox.get('proxy', vox['lo'])) * max(1.0, float(P['size_k'])) * mult
        pr = S.build_body(f'lo_proxy_{mult:g}', recipe.all_parts(), v, 4, segments=40)
        S.decimate_to(pr, 24000, smooth_after=0.0)
        pr.data.validate(verbose=False)
        pr.hide_render = True
        C.log(f'WEIGHTS: proxy {pr.name} at a {v * 1000:.1f} mm voxel ({len(pr.data.vertices)} verts)')
        return pr
    weights_report: dict = {}
    with C.Timer('skin body'):
        bn, W = skin_body(body, O.get('lo_proxy'), arm, specs, retry=coarser_proxy, report=weights_report)
        W2 = np.zeros((W.shape[0], len(names)), np.float64)
        for j, nm in enumerate(bn):
            if nm in names:
                W2[:, names.index(nm)] = W[:, j]
        co, _ = S.mesh_arrays(body)
        hi = names.index('head')
        # no mouth to open and no lids on the body: the jaw and the blink bones never move the skin
        for nm in getattr(recipe, 'MERGE_INTO_HEAD', ('jaw', 'eye.L', 'eye.R')):
            if nm in names:
                j = names.index(nm)
                W2[:, hi] += W2[:, j]
                W2[:, j] = 0.0
        # mane chains and prop bones move only what the recipe's weight regions give them: their heat weights go to the
        # parent (tip first, down the chain), unless the recipe's KEEP_HEAT names the chain
        chains = {m['name'] for m in (P.get('manes') or [])} | {'prop'}
        # batch 2: the wings and a bud's petals likewise (plans/quadruped.py heatless)
        chains |= set(plan.heatless(P)) if hasattr(plan, 'heatless') else set()
        keep_heat = set(getattr(recipe, 'KEEP_HEAT', ()))
        for sp in reversed(specs):
            pre = sp.name.split('.')[0]
            if pre in chains and pre not in keep_heat and sp.name in names and sp.parent in names:
                j, pj = names.index(sp.name), names.index(sp.parent)
                W2[:, pj] += W2[:, j]
                W2[:, j] = 0.0
        regs = recipe.body_weight_regions(co, names) if hasattr(recipe, 'body_weight_regions') else default_body_regions(recipe, co, names)
        apply_regions(W2, regs, names, 'lo_body')
        set_group_weights(body, names, W2, arm)
        R.smooth_weights(body, iterations=2, factor=0.5)
    # the membranes and the props
    prop_meshes = ['lo_props'] + sorted(n for n in O.keys() if n.startswith('lo_props_'))
    for mesh_name, hook, default in [('lo_fins', 'fin_weight_regions', default_fin_regions)] + [(n, 'prop_weight_regions', None) for n in prop_meshes]:
        ob = O.get(mesh_name)
        if ob is None:
            continue
        mco, _ = S.mesh_arrays(ob)
        attr = attr_reader(ob)
        Wm = np.zeros((len(mco), len(names)))
        if hasattr(recipe, hook):
            fn = getattr(recipe, hook)
            # a hook may take the mesh's name as a 4th argument (lo_props, lo_props_<short>)
            regs = fn(mco, attr, names, mesh_name) if len(inspect.signature(fn).parameters) >= 4 else fn(mco, attr, names)
        elif default is not None:
            regs = default(recipe, mco, attr, names)
        else:
            regs = [(np.ones(len(mco), bool), {'head': np.ones(len(mco))})]     # props: rigid on the head
        apply_regions(Wm, regs, names, mesh_name)
        set_group_weights(ob, names, Wm, arm)
    # the eye lenses ride their blink bones
    eyes = O['lo_eyes']
    eco, _ = S.mesh_arrays(eyes)
    We = np.zeros((len(eco), len(names)))
    We[:, names.index('eye.L')] = eco[:, 0] > 0
    We[:, names.index('eye.R')] = eco[:, 0] <= 0
    set_group_weights(eyes, names, We, arm)
    # the cards and the tuft copy the skin under their roots
    if O.get('lo_cards') is not None:
        S.copy_weights_at_roots(O['lo_cards'], body, arm, S.CARD_VERTS)
        S.coat_normals(O['lo_cards'], 0.15, S.CARD_VERTS)
    if O.get('lo_tuft') is not None:
        S.copy_weights_at_roots(O['lo_tuft'], body, arm, TUFT_NVT)
        S.coat_normals(O['lo_tuft'], 0.4, TUFT_NVT)
    sockets = {}
    for name, (bone, pos) in socket_points(recipe, plan.sockets(P)).items():
        R.add_socket(arm, name, bone, Vector(pos))
        sockets[name] = bone
    mn, mx = M.bounds(body)
    meta = {'sockets': sockets, 'bounds': {'min': [round(v, 4) for v in mn], 'max': [round(v, 4) for v in mx]},
            'restHeight': round(mx.z, 4), 'deformBones': len(names), 'bones': len(specs), 'review': review_frame(recipe, mn, mx, P),
            'sizeK': P['size_k'], 'weights': weights_report}
    # horns and other always-worn props may set the top: always reported beside the body's height (restHeight, which
    # the game scales by, stays the body's); variant-only props (lo_props_<short>) are left out
    top = max(mx.z, M.bounds(O['lo_props'])[1].z) if O.get('lo_props') is not None else mx.z
    meta['restHeightWithProps'] = round(float(top), 4)
    if top > mx.z + 1e-4:
        C.log(f'rest height {mx.z:.3f} m (body), {top:.3f} m with the always-worn props')
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
    """A clip builder that scales a chain group's rotations per clip (a recipe's CLIP_CALM: ear, tail, each mane) and
    skips keys on bones the rig doesn't have (a breed without ears, or a shorter tail)."""

    def __init__(self, arm, deform, calm: dict, groups=None, group_of=None):
        super().__init__(arm, deform)
        self.calm = calm
        # bone-name prefix → chain kind (a mane named 'maneL' is of kind 'mane')
        self.groups = dict(groups) if isinstance(groups, dict) else {g: g for g in (groups or ('ear', 'tail'))}
        self.group_of = group_of
        self.bones = {b.name for b in arm.data.bones}
        self.skipped: set[str] = set()

    def _has(self, bone: str) -> bool:
        if bone in self.bones:
            return True
        if bone not in self.skipped:
            self.skipped.add(bone)
            C.log(f'clips: the rig has no {bone}; its keys are skipped')
        return False

    def _group(self, bone: str):
        """(group, kind) of a chain bone, or None: the recipe's calm_group(bone) if it has one."""
        if self.group_of is not None:
            g = self.group_of(bone)
            return (g, g) if g else None
        g = bone.split('.')[0]
        return (g, self.groups[g]) if '.' in bone and g in self.groups else None

    def _calm(self, group: str, kind: str) -> float:
        """CLIP_CALM[clip][group], else [clip][kind], else ['*'][group], else ['*'][kind], else 1."""
        for table in (self.calm.get(self.meta.name, {}), self.calm.get('*', {})):
            for key in (group, kind):
                if key in table:
                    return table[key]
        return 1.0

    def rot(self, bone: str, frame: int, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        if not self._has(bone):
            return
        gk = self._group(bone)
        k = 1.0
        if gk and self.meta is not None:
            k = self._calm(*gk)
        super().rot(bone, frame, x * k, y * k, z * k)

    def rotq(self, bone, frame, q) -> None:
        if self._has(bone):
            super().rotq(bone, frame, q)

    def loc(self, bone: str, frame: int, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        if self._has(bone):
            super().loc(bone, frame, x, y, z)

    def scale(self, bone: str, frame: int, x: float = 1.0, y: float = 1.0, z: float = 1.0) -> None:
        if self._has(bone):
            super().scale(bone, frame, x, y, z)


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
    P = rig_params(recipe)
    settle = False
    if 'body_width' not in P and hasattr(plan, 'KO_ROLL'):
        # the ko clip lays the body on its side at this height (the recipe's body_width wins): a first guess from the
        # torso, then settle_ko puts the posed body on the ground
        bw = measured_body_width(P, plan.KO_ROLL)
        if bw:
            P['body_width'] = bw
            settle = True
            C.log(f'clips: body_width {bw:.3f} m (measured on lo_body for ko)')
    deform = [b.name for b in arm.data.bones if b.use_deform]
    groups = plan.chain_groups(P) if hasattr(plan, 'chain_groups') else ('ear', 'tail')
    cb = CalmClips(arm, deform, getattr(recipe, 'CLIP_CALM', {}), groups, getattr(recipe, 'calm_group', None))
    with C.Timer('clips'):
        clips = plan.make_clips(cb, P, only)
        if settle:
            clips = settle_ko(cb, plan, arm, P, clips)
        if not only or 'blink' in only:
            clips.append(blink_clip(cb, arm, getattr(recipe, 'BLINK_CLOSED', (1.0, 0.08, 1.0))))
    want = plan.STAR_CLIPS + plan.MOVE_CLIPS + ['blink'] + (list(getattr(plan, 'FLY_CLIPS', [])) if P.get('wings') else [])
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
def present_meshes() -> dict[str, str]:
    """The game meshes this build has, in export order: MESH_KINDS, then each variant's own props (lo_props_<short>)."""
    O = bpy.data.objects
    out = {n: k for n, k in MESH_KINDS.items() if O.get(n) is not None}
    out.update({n: 'prop' for n in sorted(O.keys()) if n.startswith('lo_props_') and O[n].type == 'MESH'})
    return out


def _vglow(baked: dict, short: str) -> dict | None:
    """A variant ORM's glow for the sidecar ({strength, tint}), or None when that variant doesn't glow."""
    g = ((baked.get('variant_orm') or {}).get(short) or {}).get('glow')
    return {'strength': float(g['strength']), 'tint': g.get('tint')} if g else None


def stage_export(recipe, plan, out: Path) -> Path:
    open_blend(out, 'rigged.blend')
    O = bpy.data.objects
    arm = O[f'{recipe.ID}_rig']
    kinds = present_meshes()
    meshes = [O[n] for n in kinds]
    vs = variants(recipe)
    colour_sets = [('Col', '_COLOR_BASE')] + [(U.variant_colour_attr(vid, recipe.ID), '_COLOR_VARIANT' if i == 0 else f'_COLOR_VARIANT{i + 1}')
                                              for i, (vid, _s, _p) in enumerate(vs)]
    keep = {'position', 'sharp_face'} | {c for c, _ in colour_sets}
    for ob in meshes:
        m, nb = new_mat(f'{recipe.ID}_{kinds[ob.name]}')
        nb.output(nb.new('ShaderNodeBsdfPrincipled').outputs[0])
        ob.data.materials.clear()
        ob.data.materials.append(m)
        # only the UV map, the skin and (cards, tuft) the colour sets ship
        for a in [a.name for a in ob.data.attributes if not a.name.startswith('.') and a.name not in keep
                  and a.domain == 'POINT' and a.data_type in ('FLOAT', 'FLOAT_VECTOR')]:
            ob.data.attributes.remove(ob.data.attributes[a])
        if 'own_uv' in ob.data.attributes:
            ob.data.attributes.remove(ob.data.attributes['own_uv'])
        # Blender 5.2's exporter writes a white COLOR_0 for these meshes whatever the options, so the colours go out as
        # custom attributes and tools/art/ultra.ts promotes them: _COLOR_BASE → COLOR_0, _COLOR_VARIANT[n] → COLOR_1, COLOR_n
        me = ob.data
        for src, dst in colour_sets:
            if src in me.color_attributes:
                S.add_attr(ob, dst, S.attr_array(ob, src)[:, :3])
        for c in list(me.color_attributes):
            me.color_attributes.remove(c)
    sockets = [o for o in O if o.name.startswith('socket_')]
    check_finite(meshes, 'export', weights=True)
    # held poses survive the export (the exporter drops constant channels: a bud keyed open stayed shut in the game)
    held = EX.hold_constant_channels(arm, A.action_fcurves)
    if held:
        C.log(f"export: kept {sum(len(v) for v in held.values())} held channels in {len(held)} clips "
              f"({'; '.join(f'{k}: ' + ', '.join(v) for k, v in sorted(held.items()))})")
    opts_before = dict(EX.EXPORT_OPTIONS)
    EX.EXPORT_OPTIONS.update(export_tangents=True, export_vertex_color='NONE', export_all_vertex_colors=False,
                             export_attributes=True, export_materials='EXPORT')
    try:
        glb = EX.export_glb(out / f'{recipe.LOOK}.glb', [arm] + meshes + sockets)
    finally:
        EX.EXPORT_OPTIONS.clear()
        EX.EXPORT_OPTIONS.update(opts_before)
    EX.check_exported_channels(glb, arm, A.action_fcurves)
    rig = json.loads((out / 'stats_rig.json').read_text(encoding='utf-8'))
    clips = json.loads((out / 'clips.json').read_text(encoding='utf-8'))
    build = json.loads((out / 'stats_build.json').read_text(encoding='utf-8'))
    bpath = out / 'stats_bake.json'
    baked = json.loads(bpath.read_text(encoding='utf-8')) if bpath.exists() else {}
    P = rig_params(recipe)
    closed = getattr(recipe, 'BLINK_CLOSED', (1.0, 0.08, 1.0))
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
        'springs': plan.springs(P) if hasattr(plan, 'springs') else plan.SPRINGS,
        'meshes': kinds,
        'face': {
            'mode': 'baked',
            'note': getattr(recipe, 'FACE_NOTE', DEFAULT_FACE_NOTE),
            'eyeBones': ['eye.L', 'eye.R'],
            'blinkClip': 'blink',
            'blinkScale': {'axis': 'y', 'closed': closed[1], 'closedXYZ': list(closed)},
            'eyeColor': recipe.PALETTE['eye'],
        },
        # one colour map per variant (atlas_<short>.png → <breed>_<short>_base.*), the cards' and tuft's colours in COLOR_<i+1>
        'variants': {vid: {'textures': vid, 'colorAttribute': f'COLOR_{i + 1}', 'eyeColor': pal['eye'],
                           'palette': {k: pal[k] for k in ('body', 'belly', 'accent', 'eye')}, 'atlas': f'atlas_{short}.png',
                           # a variant with its own ORM (VARIANT_ORM): its file, and its glow (or null: it doesn't glow)
                           **({'orm': f'atlas_{short}_orm.png', 'glow': _vglow(baked, short)} if short in (baked.get('variant_orm') or {}) else {}),
                           # VARIANT_CARDS_OFF: the runtime hides the fur cards on this variant (bare polished stone)
                           **({'cards': False} if short in set(getattr(recipe, 'VARIANT_CARDS_OFF', None) or ()) else {}),
                           # the props only this variant wears: the runtime hides these meshes unless the variant is on
                           **({'meshes': [f'lo_props_{short}']} if f'lo_props_{short}' in kinds else {})}
                     for i, (vid, short, pal) in enumerate(vs)},
        'palette': recipe.PALETTE,
        # the atlas layout: the bottom `strip` share holds `cells` tiles (tuft locks, then fur cards with alpha)
        'atlas': {'strip': float(build.get('atlas_strip', BK.STRIP)), 'cells': BK.CELLS, 'lockCells': list(BK.LOCK_CELLS), 'cardCells': list(BK.CARD_CELLS)},
        # Blender coordinates (−Y forward, Z up): what the review tools frame
        'review': rig.get('review'),
        'clips': clips,
        'buildStats': {'cards': build['cards'], 'tuftLocks': build['tuft_locks'], 'lyingLocks': build['lying_locks'], 'sourceTriangles': build['hi_tris'],
                       **({'uvOverlapTexels': build['uv_overlap_texels']} if 'uv_overlap_texels' in build else {})},
    }
    if 'restHeightWithProps' in rig:
        side['restHeightWithProps'] = rig['restHeightWithProps']
    if getattr(recipe, 'CARD_EDGE_FADE', None) is not None:
        # the recipe's card edge fade (1 − |N·V| at which the cards fade in / are full): long mane cards may show more
        # face-on than the game's default (ART.ultra.film.cardEdgeFade)
        a, b = (float(v) for v in recipe.CARD_EDGE_FADE)
        side['cards'] = {'edgeFade': [a, b]}
    if getattr(recipe, 'NORMAL_SCALE', None) is not None:
        # the normal map's strength in the game's film material (default ART.ultra.film.normalScale, 0.6): scaled and
        # stone breeds show their baked relief at about 1.0-1.2
        side['normal'] = {'scale': float(recipe.NORMAL_SCALE)}
    if getattr(recipe, 'BODY_SHEEN', None) is not None:
        # the body's sheen in the game's film material (default ART.ultra.film.furSheen, 0.45): a stone breed wants 0 (the
        # fur sheen reads as felt with a soft halo on stone); validated like the runtime (parts.ts bodySheenOf)
        sheen = float(recipe.BODY_SHEEN)
        if not (0.0 <= sheen <= 1.0) or sheen != sheen:
            raise ValueError(f'BODY_SHEEN must be within 0..1, got {recipe.BODY_SHEEN!r}')
        side['body'] = {'sheen': sheen}
    if getattr(recipe, 'LITE_PROPS_TRIS', None):
        # the Lite copy's prop share (tools/art/ultra.ts; default 2.4k): signature props (Petalphant's ears and bud) survive
        side['litePropsTris'] = int(recipe.LITE_PROPS_TRIS)
    if getattr(recipe, 'LITE_KEEP', None):
        # parts the Lite copy keeps (tools/art/ultra.ts): e.g. ('tuft',) for a signature ear tuft
        side['liteKeep'] = [str(k) for k in recipe.LITE_KEEP]
    if getattr(recipe, 'GLOW', None) is not None:
        # the ORM's alpha is a glow mask: emissive = base colour x mask x strength (tint, when given, sets the hue)
        side['glow'] = {'strength': float(recipe.GLOW.get('strength', 1.0)), 'tint': recipe.GLOW.get('tint')}
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


def game_materials(out: Path, which: str = 'base', glow: float = 0.0) -> None:
    """The low meshes with their baked maps, as EEVEE sees them (cards: alpha from the strip tile × the edge fade is a
    runtime thing; here they dither). `which` is 'base' or a variant's short name. `glow` > 0: the ORM's alpha glows
    (base colour × mask × glow), as the runtime's emissive does."""
    O = bpy.data.objects
    imgs = {k: bpy.data.images.load(str(out / f'atlas_{k}.png')) for k in ('normal', 'orm')}
    imgs['base'] = bpy.data.images.load(str(out / f'atlas_{which}.png'))
    for k in ('normal', 'orm'):
        imgs[k].colorspace_settings.name = 'Non-Color'
    for n, kind in present_meshes().items():
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
            vc.layer_name = 'Col' if which == 'base' else f'Col_{which}'
            base = nb.mix(1.0, base, vc.outputs['Color'], blend='MULTIPLY')
        r, g, b = nb.sep_rgb(to.outputs['Color'])
        nb.link(nb.mix(nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, r), 0.5), base, nb.rgb((0, 0, 0)), dtype='RGBA'), bsdf.inputs['Base Color'])
        nb.link(g, bsdf.inputs['Roughness'])
        nb.link(b, bsdf.inputs['Coat Weight'])
        bsdf.inputs['Coat Roughness'].default_value = 0.12
        bsdf.inputs['Sheen Weight'].default_value = 0.0 if kind in ('fin', 'eye', 'prop') else 0.5
        bsdf.inputs['Sheen Roughness'].default_value = 0.45
        if kind != 'card':
            nb.link(nm.outputs['Normal'], bsdf.inputs['Normal'])
        if kind == 'eye':
            bsdf.inputs['Specular IOR Level'].default_value = 0.25
        if kind == 'fin':
            bsdf.inputs['Emission Strength'].default_value = 0.12
            nb.link(tb.outputs['Color'], bsdf.inputs['Emission Color'])
        if glow > 0 and kind not in ('card', 'lock'):
            nb.link(nb.mix(1.0, tb.outputs['Color'], nb.comb(to.outputs['Alpha'], to.outputs['Alpha'], to.outputs['Alpha']), blend='MULTIPLY'),
                    bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = 2.5 * glow
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
    kinds = present_meshes()
    for o in O:
        if o.type == 'MESH':
            o.hide_render = o.name not in kinds
    arm = O[f'{recipe.ID}_rig']
    clips = {m.name: m for m in clips_from_scene(out)}
    rig = json.loads((out / 'stats_rig.json').read_text(encoding='utf-8'))
    frame = rig.get('review') or review_frame(recipe, Vector(rig['bounds']['min']), Vector(rig['bounds']['max']), rig_params(recipe))
    centre, size = frame['centre'], frame['size']
    head_t, head_s = frame['head']['target'], frame['head']['size']
    made: list[tuple[Path, str]] = []

    def shot(name: str, az: float, el: float, target, sz: float) -> None:
        aim(cam, target, az, el, sz)
        p = RN.render_png(shots / f'{name}.png')
        made.append((p, name.replace('_', ' ')))

    def wear(short: str | None) -> None:
        for n in kinds:
            if n.startswith('lo_props_'):
                O[n].hide_render = n != f'lo_props_{short}'

    game_materials(out, 'base', glow=float((getattr(recipe, 'GLOW', None) or {}).get('strength', 1.0)) if getattr(recipe, 'GLOW', None) is not None else 0.0)
    wear(None)
    A.rest_pose(arm)            # every NLA track muted: the true rest pose, not frame 1 of the topmost track
    bpy.context.view_layer.update()
    for v, (az, el, tgt, _s) in VIEWS.items():
        if tgt == 'head':
            shot(v, az, el, head_t, head_s)
        else:
            shot(v, az, el, centre, size)
    turn = RN.contact_sheet(made[:4], 4, rv / 'turnaround.png', title=f'{recipe.LOOK} turnaround (game mesh, baked atlas)')
    faces = RN.contact_sheet(made[4:6], 2, rv / 'head.png', title=f'{recipe.LOOK} head')
    made.clear()
    # (clip, t[, label]): the strike's wind-up too (a slam's rear-up, a kick's spin, a swipe's draw)
    poses = [('strafe_l', 0.25), ('strafe_r', 0.25), ('sidestep_l', 0.5), ('sidestep_r', 0.5), ('strike', 0.3, 'strike_windup'), ('strike', 0.54), ('hit', 0.3),
             ('hit_heavy', 0.3), ('ko', 1.0), ('win', 0.2), ('battle_idle', 0.25), ('walk', 0.25), ('blink', 0.4)]
    Pr = rig_params(recipe)
    if Pr.get('wings') or Pr.get('trunk'):
        # batch 2: the wings wide open and the trunk raised, and the bud open
        poses += [('cast', 0.5), ('idle_happy', 0.3)]
    if Pr.get('wings') and 'fly' in clips:
        # Nov 12: the flight clips (framed wider: the working wings span about 2.5 x the standing height)
        poses += [('fly', 0.2, 'fly_downstroke'), ('fly', 0.6, 'fly_upstroke'), ('fly_takeoff', 0.25, 'fly_takeoff_crouch'),
                  ('fly_takeoff', 0.45, 'fly_takeoff_leap'), ('fly_cast', 0.5), ('fly_land', 0.3, 'fly_land_flare'),
                  ('fly_land', 0.66, 'fly_land_touch')]
    for name, t, *lab in poses:
        m = clips.get(name)
        if m is None:
            continue
        # from the rest pose, as the game's mixer plays a clip: bones the clip doesn't key must not keep the previous
        # clip's pose (Nov 7: win inherited ko's lowered hips, ko hit_heavy's reared chest)
        A.clear_clip(arm)
        A.set_clip(arm, m)
        f = 1 + int(round(t * m.frames))
        sc.frame_set(f)
        bpy.context.view_layer.update()
        if name == 'blink':
            shot(f'pose_{name}', 20, 8, head_t, head_s)
        elif name.startswith('fly'):
            shot(f'pose_{lab[0] if lab else name}', 35, 14, (centre[0], centre[1], centre[2] + 0.25 * size), size * 1.9)
        else:
            shot(f'pose_{lab[0] if lab else name}', 35, 14, centre, size)
    A.clear_clip(arm)
    sc.frame_set(1)
    pose_sheet = RN.contact_sheet(made, 4, rv / 'poses.png', title=f'{recipe.LOOK} key poses')
    sheets = [turn, faces, pose_sheet]
    for vid, short, _pal in variants(recipe):
        made.clear()
        game_materials(out, short, glow=float((getattr(recipe, 'GLOW', None) or {}).get('strength', 1.0)) if getattr(recipe, 'GLOW', None) is not None else 0.0)
        wear(short)
        shot(f'variant_{short}_three_quarter', 35, 14, centre, size)
        shot(f'variant_{short}_back', 160, 14, centre, size)
        sheets.append(RN.contact_sheet(made, 2, rv / f'variant_{short}.png', title=vid.replace('-', ' ')))
    return sheets


# ----------------------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--breed', default='puddlepup_ultra')
    ap.add_argument('--stages', default=','.join(ALL_STAGES))
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--atlas', type=int, default=2048)
    ap.add_argument('--body-tris', type=int, default=0, help="lo_body's triangles (default the recipe's BODY_TRIS, else 46000)")
    ap.add_argument('--clips', default='')
    ap.add_argument('--out', default='', help='output folder (default tools/blender/out/<look>/)')
    ap.add_argument('--with-cpu', action='store_true', help='bake on the GPU and the CPU together')
    ap.add_argument('--cpu', action='store_true', help='bake on the CPU only (another job saturates the GPU)')
    args = ap.parse_args(C.script_args())
    stages = [s for s in args.stages.split(',') if s]
    recipe, plan = load(args.breed)
    out = C.ensure_dir(Path(args.out) if args.out else C.OUT_ROOT / recipe.LOOK)
    C.open_log(out / 'build.log')
    C.log(f'build_ultra {recipe.LOOK} stages={stages} quick={args.quick} variants={[s for _v, s, _p in variants(recipe)]}')
    t0 = time.time()
    if 'build' in stages:
        stage_build(recipe, out, args.quick, args.body_tris or int(getattr(recipe, 'BODY_TRIS', 46000)))
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
