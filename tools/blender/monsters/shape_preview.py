"""Fast shape preview for any Ultra recipe (a minute, no bake): the coarse body with its extras, the membranes, the props
and the eyes in flat colours, rendered from the review angles into one contact sheet.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python tools/blender/monsters/shape_preview.py -- --breed <breed>_ultra --out <dir> [--voxel 0.0065] [--noeyes] [--res 420]

Flat colours: the recipe's `preview_colours(co, vn)` (n×3 linear RGB per body vertex) if it has one; else PALETTE['body'],
with PALETTE['belly'] where its zones() say 'belly' or 'bib', and the carved lash line dark. Membranes use
PALETTE['accent'], props a darker accent, the eyes PALETTE['eye']. Framing: the recipe's REVIEW, else the body's bounds.
Writes <out>/<view>.png and <out>/sheet.png, and logs the height against HEIGHT_UNITS / 150 m (the size rule).
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))        # tools/blender → `lib`, `monsters`

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from lib import common as C  # noqa: E402
from lib import mesh as M  # noqa: E402
from lib import render as RN  # noqa: E402
from lib import surface as S  # noqa: E402
from lib import ultra as U  # noqa: E402
from lib.nodes import new_mat  # noqa: E402
from monsters import build_ultra as BU  # noqa: E402


def lin(h: str) -> np.ndarray:
    return S.v3(C.lin_rgb(h))


def mat(name: str, colour=None, attr: str | None = None, rough: float = 0.6, double: bool = False) -> bpy.types.Material:
    m, nb = new_mat(name)
    b = nb.new('ShaderNodeBsdfPrincipled')
    if attr:
        nb.link(nb.attribute(attr).outputs['Color'], b.inputs['Base Color'])
    else:
        b.inputs['Base Color'].default_value = tuple(float(c) for c in colour) + (1.0,)
    b.inputs['Roughness'].default_value = rough
    nb.output(b.outputs[0])
    m.use_backface_culling = not double
    return m


def body_colours(recipe, ob: bpy.types.Object) -> np.ndarray:
    co, vn = S.mesh_arrays(ob)
    if hasattr(recipe, 'preview_colours'):
        return np.asarray(recipe.preview_colours(co, vn), np.float64)
    pal = recipe.PALETTE
    rgb = np.tile(lin(pal['body']), (len(co), 1))
    if hasattr(recipe, 'zones'):
        z = recipe.zones(co, vn)
        under = np.zeros(len(co), bool)
        for k in ('belly', 'bib'):
            if k in z:
                under |= np.asarray(z[k], bool)
        rgb = np.where(under[:, None], lin(pal['belly'])[None], rgb)
    if 'lash' in ob.data.attributes:
        lash = np.clip(S.attr_array(ob, 'lash'), 0, 1)[:, None]
        rgb = rgb * (1 - lash) + lin('#1A1214')[None] * lash
    return rgb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--breed', required=True, help='the recipe module, e.g. tumblefox_ultra')
    ap.add_argument('--out', required=True)
    ap.add_argument('--voxel', type=float, default=0.0065)
    ap.add_argument('--res', type=int, default=420)
    ap.add_argument('--noeyes', action='store_true')
    args = ap.parse_args(C.script_args())
    out = C.ensure_dir(Path(args.out))
    recipe = importlib.import_module(f'monsters.breeds.{args.breed}')
    BU.validate(recipe)
    C.clear_scene()
    extras = recipe.body_extras() if hasattr(recipe, 'body_extras') else []
    body = S.build_body('hi_body', recipe.all_parts(), args.voxel, 4, segments=40, extra=extras)
    if hasattr(recipe, 'carve'):
        recipe.carve(body)
    else:
        S.base_attrs(body, S.mesh_arrays(body)[0])
    S.set_colour_attr(body, 'Col', body_colours(recipe, body), active=True)
    body.data.materials.append(mat('body', attr='Col'))
    pal = recipe.PALETTE
    for f in (recipe.build_fins(False, True) if hasattr(recipe, 'build_fins') else []):
        f.data.materials.append(mat('fin', lin(pal['accent']), rough=0.4, double=True))
    owners = U.variant_prop_owners(recipe)
    prop_top = None
    for p in (recipe.build_props(False, True) if hasattr(recipe, 'build_props') else []):
        # the recipe's preview_prop_colour(name) -> hex or linear RGB (ivory tusks), else the accent darkened
        pc = recipe.preview_prop_colour(U.prop_name(p)) if hasattr(recipe, 'preview_prop_colour') else None
        pc = lin(pc) if isinstance(pc, str) else (S.v3(pc) if pc is not None else lin(pal['accent']) * 0.6)
        p.data.materials.append(mat('prop', pc, rough=0.35))
        if U.prop_owner(p, owners) is None:
            # always-worn props (horns) may set the top: reported beside the body's height
            bpy.context.view_layer.update()
            top = max((p.matrix_world @ v.co).z for v in p.data.vertices)
            prop_top = top if prop_top is None else max(prop_top, top)
    for s in (1, -1):
        e = recipe.build_eye(f'eye{s}', s, False)
        e.data.materials.append(mat('eye', lin(pal['eye']), rough=0.15))
        e.hide_render = args.noeyes
    mn, mx = M.bounds(body)
    want = recipe.HEIGHT_UNITS / U.UNITS_PER_METRE * 0.986
    C.log(f'{args.breed}: height {mx.z:.3f} m (the size rule says about {want:.3f} m for HEIGHT_UNITS {recipe.HEIGHT_UNITS}); '
          f'length {mx.y - mn.y:.3f} m, width {mx.x - mn.x:.3f} m, {M.tri_count(body)} tris')
    if prop_top is not None and prop_top > mx.z:
        C.log(f'{args.breed}: with its always-worn props {prop_top:.3f} m tall ({(prop_top / want - 1) * 100:+.0f}% against the size rule; '
              f'the game scales by the body, restHeight {mx.z:.3f} m)')
    P = dict(recipe.rig_p())
    rv = BU.review_frame(recipe, mn, mx, P)
    centre, size = rv['centre'], rv['size']
    head_t, head_s = rv['head']['target'], rv['head']['size']
    tail_t = (0.0, mx.y - 0.25 * (mx.y - mn.y), mx.z * 0.5)
    sc, cam = BU.review_scene((args.res, args.res))
    made = []
    views = [('front', 0, 6, centre, size), ('34', 35, 14, centre, size), ('side', 90, 4, centre, size), ('back', 180, 10, centre, size),
             ('head34', 26, 12, head_t, head_s), ('headside', 90, 4, head_t, head_s), ('headfront', 0, 4, head_t, head_s),
             ('tailback', 160, 20, tail_t, size * 0.7)]
    for name, az, el, tgt, sz in views:
        BU.aim(cam, tgt, az, el, sz)
        made.append((RN.render_png(out / f'{name}.png'), name))
    if P.get('wings'):
        # batch 2: the wings' spread pose (the recipe's `spread` points; the membranes only, the arms are props) in
        # place of the folded membranes, so the open pose can be checked without a build
        folded = [o for o in bpy.data.objects if o.type == 'MESH' and 'wing_side' in o.data.attributes]
        for o in folded:
            o.hide_render = True
        for s in (1, -1):
            v, f, _w = U.wing_membrane(P['wings'], s, 8, 12, spread=True)
            sh = S.sheet_object(f'spread{s}', v, f)
            sh.data.materials.append(mat('spread', lin(pal['accent']), rough=0.4, double=True))
        wide = (0.0, centre[1], max(centre[2], mx.z * 0.6))
        for name, az, el in (('wings_front', 0, 8), ('wings_34', 35, 16)):
            BU.aim(cam, wide, az, el, size * 1.5)
            made.append((RN.render_png(out / f'{name}.png'), name.replace('_', ' ') + ' (spread)'))
    RN.contact_sheet(made, 4, out / 'sheet.png', title=f'{recipe.ID} shape preview (flat colours; height {mx.z:.2f} m)')
    C.log(f'shape preview: {out / "sheet.png"}')


if __name__ == '__main__':
    main()
