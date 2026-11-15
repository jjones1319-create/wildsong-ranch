"""Bloatoad at the Art 2.1 Ultra tier (chatgpt/monsters/21-bloatoad; CONTENT entry 8): a huge squat toad with an
inflatable throat sac, lazy half-lidded eyes, warty spots and little crown-like bumps on its head, on the blob plan
(plans/blob.py; RECIPE.md "Blob plan").

    npm run art:shape -- bloatoad
    tools/blender/slot.sh npm run art:ultra -- bloatoad --blender --stages build,bake,rig,clips,export,review > tools/blender/out/bloatoad-build1.log 2>&1 &

Size: HEIGHT_UNITS 180 (the card: about 1.2 × Puddlepup's height, and very wide) → 1.20 m to the crown bump's top;
1.33 m across the hind feet and 1.28 m nose to rump (2-turnaround).

The parts:
  - the body (lo_body): the pear-shaped head-body with the face on its top front, the raised eye sockets with heavy
    upper lids over the lenses, the throat (the sac: bone `sac`, ballooning to 2×), four short legs on big webbed
    four-toed feet; moist toad skin with raised warts of every size, dark wart rosettes on the back, the crown bumps,
    folds on the throat and the belly and at the limbs (bloatoad_skin.py);
  - the tongue (lo_props): a pink prop inside the mouth on the jaw's three-bone chain (bloatoad_props.py);
  - the eyes: glossy golden lenses with round pupils, the upper lid of the body over their top 40% (half-lidded).
Colours (CONTENT): skin #7C9A3E, belly and throat #F6C49B, warts #5E7A2E, eyes #E9C46A.
Derived (CONTENT has none; from the palette, bloatoad_paint.py): the tongue's and the mouth's pinks (the belly peach
turned toward rose), the dark mouth and pupil, the lighter olive of the snout and the wart tops.
Party Bloatoad (secrets.ts "confetti spots", variants.ts): skin #8FB84A, belly and sac #FFD9A6, the wart rosettes and
spots turned confetti: mostly pink #FF5C8A, some yellow (the eye gold, brightened) and blue (the pink turned to blue
at the same strength); eyes #E9C46A.
"""
from __future__ import annotations

import numpy as np
from mathutils import Matrix, Vector

from lib import common as C
from lib import surface as S
from lib import ultra as U
from monsters.breeds import bloatoad_form as F

ID = 'bloatoad'
LOOK = 'bloatoad-ultra'
PLAN = 'blob'
HEIGHT_UNITS = 180
PALETTE = {'body': '#7C9A3E', 'belly': '#F6C49B', 'accent': '#5E7A2E', 'eye': '#E9C46A'}
VARIANTS = {'party-bloatoad': {'body': '#8FB84A', 'belly': '#FFD9A6', 'accent': '#FF5C8A', 'eye': '#E9C46A'}}
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')     # the lower lip is weighted to the jaw below (RECIPE.md, Blob plan)
BODY_TRIS = 70000                               # round 2: more for the sac's bubble, the mouth and the belly's side
VOXELS = {'hi': 0.0032}
ATLAS_STRIP = 0
NORMAL_SCALE = 1.2                              # round 2: the warts' and the rosettes' relief stronger
BODY_SHEEN = 0.0                                # wet skin: its gloss is the clearcoat (round 3: the sheen read milky on the head and back)
ATLAS_DENSITY = {'lo_eyes': 1.4}
AO_FLOOR = 0.4                                  # round 2: no stubbly dark creases (the inner thighs)
AO_SOFTEN = 3.0
FACE_NOTE = ('Baked face: a wide content smile curling up at the corners, two nostrils on the snout, big golden '
             'lenses with round pupils under heavy upper lids sculpted over their top 40% (lazy, half-lidded). '
             'Blinking scales the blink bones: each lens squashes down and sinks, showing the closed lid sculpted under it.')
BLINK_CLOSED = (0.92, 0.04, 0.15)

HIP, TOP, BASE = F.HIP, F.TOP, F.BASE
HEAD_C, HEAD_R = Vector(F.HEAD_C), F.HEAD_R
EYE_R, EYE_SHAPE, EYE_DEPTH = F.EYE_R, F.EYE_SHAPE, F.EYE_DEPTH


def rig_p() -> dict:
    return {'hip': HIP, 'chest': F.RIG_TOP, 'body_base': F.RIG_BASE, 'head_c': tuple(HEAD_C), 'head_r': HEAD_R,
            'head_split': F.HEAD_SPLIT, 'jaw': F.JAW, 'jaw_open': True, 'sac': F.SAC,
            'tongue': {'points': F.TONGUE, 'parent': 'jaw', 'reach': 0.78}, 'tongue_aim': 3.0, 'legs': F.LEGS,
            'strike_style': 'tongue', 'cast_style': 'inflate', 'ko_style': 'back', 'ko_pitch': 78.0, 'hop': 0.6, 'strike_yaw': 24.0,
            # win: the sac balloons as it jumps (the in-game win shot is airborne)
            'win_scale': {'sac': 2.4},
            # strike: the sac full as the tongue lashes (5-poses, attack; a blob.py knob, Nov 15)
            'strike_scale': {'sac': 2.2},
            # round 3: full through the wind-up too (a blob.py knob, as strike_scale with the wind-up)
            'strike_windup_scale': {'sac': 1.5},
            # round 2: the hops stretch less (the sidestep read as a bowling pin); a blob.py knob
            'hop_stretch': 0.35,
            # hit: a bigger knock back for the upper body (the in-game shot at t 0.3 read too close to idle)
            # round 3: the knock mostly in the head (the chest's bend dragged the shoulder's skin into teardrops)
            # polish: squashed wide and low on the impact (5-poses hit; the plan's front-to-back knock kept its volume
            # by growing 7% taller), the head thrown back less (blob.py knob hit_squash, Nov 15)
            'hit_squash': 0.13,
            'hit_bones': {'chest': (-3.0, 0.0, -3.0), 'head': (-4.0, 3.0, -5.0)},
            # hit_heavy leans back 12 degrees less (the belly ran through the planted front legs)
            # polish: and leans back, rises and stretches less (the belly still pushed through both arms' roots and the
            # shoulder's warts smeared into teardrops; blob.py knobs hit_heavy_pitch / _lift / _stretch)
            'hit_heavy_bones': {'body': (12.0, 0.0, 0.0)},
            'hit_heavy_pitch': 0.6, 'hit_heavy_lift': 0.3, 'hit_heavy_stretch': 0.0,
            # polish: the sidestep's mid-hop stretch, lean-back, roll and tuck halved (0.92 wide for 1 tall in the air,
            # 1.14 at rest; its tucked hind feet smeared the haunch's underside; blob.py knob sidestep_stretch)
            'sidestep_stretch': 0.5,
            # ko: the legs splay half as wide (their roots smeared across the peach)
            'ko_bones': {'leg1.L': (0, 20, 0), 'leg1.R': (0, -20, 0), 'leg2.L': (0, 20, 0), 'leg2.R': (0, -20, 0)},
            # hit_heavy: the tongue stays in (the plan lolls it out; its tip stood on the lips like a pink nose):
            # the same bump as the plan's knock (pulse 0..0.62), sliding each bone back by its step (0.78 m × 0.12 / 2)
            'clip_bones': {'hit_heavy': {'tongue.2': [(0.0, 0.62, (0, 0, 0), (0, 0.039, 0.0012))],
                                         'tongue.3': [(0.0, 0.62, (0, 0, 0), (0, 0.039, 0.0012))]},
                           # round 2: eat's two flicks leave through the open mouth, a little down (the plan droops the
                           # tongue 45 degrees on the opening jaw, which ran it out through the sac): the same bumps, lifted
                           'eat': {'tongue.1': [(0.2, 0.42, (-36, 0, 0)), (0.5, 0.72, (-36, 0, 0))]},
                           # ko: the face turned up toward the camera (it lay as an egg with feet)
                           'ko': {'chest': [(0.35, 1.65, (16, 0, 0))], 'head': [(0.35, 1.65, (22, 0, 0))],
                                  # the tongue stays in the mouth (the plan lolls it out, through the throat's skin)
                                  'tongue.2': [(0.3, 1.7, (0, 0, 0), (0, 0.0585, 0.0018))],
                                  'tongue.3': [(0.3, 1.7, (0, 0, 0), (0, 0.0585, 0.0018))]}},
            'ko_settle_meshes': ('lo_body', 'lo_props')}


# ----------------------------------------------------------------------------- the body
def all_parts():
    return F.all_parts()


def zones(co: np.ndarray, n=None) -> dict:
    from monsters.breeds import bloatoad_skin as SK
    return SK.zones(co)


def decimate_keep(co: np.ndarray) -> np.ndarray:
    from monsters.breeds import bloatoad_carve as CV
    z = zones(co)
    # round 1: the crown bumps too (decimated, they came out as faceted pyramids), and the lids a little more
    crown = F.smooth(0.03, 0.008, CV.crown_dist(co))
    # and the sac (it balloons to twice its size, so its facets would double)
    from monsters.breeds import bloatoad_skin as SK
    # every mask soft-edged: a hard step in the protection left long slivers along its edge (two by the right eye were
    # too thin for a tangent, which blanked the review's raw-material frame)
    muzzle = F.smooth(0.03, -0.01, F.ell_sdf(co, (0.0, -0.45, 0.87), (0.4, 0.22, 0.12)))
    keep = (0.9 * muzzle + 0.75 * F.smooth(0.165, 0.105, z['eye_d']) + 0.5 * z['toes'] + 0.25 * z['paw'] + 0.9 * crown
            + 0.5 * F.smooth(0.05, 0.3, SK.sac_weight(co)) + 0.6 * F.smooth(0.3, 0.8, SK.mouth_field(co)['band'])
            # round 2: the belly's side low down (it faceted into stair steps in turn_side)
            + 0.3 * F.smooth(0.32, 0.18, co[:, 2]) * F.smooth(0.0, 0.3, z['peach']))
    return np.clip(keep, 0, 1)


def texel_k(fc: np.ndarray) -> np.ndarray:
    """The face and the eyes' lids get the most texels, the warty back and legs the usual, the belly's underside less."""
    z = zones(fc)
    k = np.ones(len(fc))
    k = np.where(z['head'], 1.35, k)
    k = np.where(z['face'], 1.8, k)
    # round 2: the mouth's slit (its walls show when the jaw opens: more texels, no streaks from neighbours' colour)
    from monsters.breeds import bloatoad_skin as SK
    k = np.where(SK.mouth_field(fc)['band'] > 0.02, 2.6, k)
    k = np.where(z['under'], 0.55, k)
    return k


def calm_group(bone: str) -> str | None:
    if bone == 'jaw':
        return 'jaw'
    return 'tongue' if bone.startswith('tongue.') else None


# the jaw opens less than the plan's (a closed mesh's lips stretch); eat's tongue flicks out of the mouth, a little down,
# not 45 degrees down through the chin; dizzy's tongue only peeks
CLIP_CALM = {'*': {'jaw': 0.65}, 'strike': {'jaw': 0.8}, 'eat': {'jaw': 1.0}, 'dizzy': {'tongue': 0.5}, 'ko': {'tongue': 0.0}}


# ----------------------------------------------------------------------------- rig weights
def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    from monsters.breeds import bloatoad_skin as SK
    return SK.weight_regions(co, names)


def build_props(high: bool, quick: bool):
    from monsters.breeds import bloatoad_props as PR
    return PR.build(high, quick)


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """The tongue slides out along its three-bone chain from the jaw. The mouth's pocket (polish) moves exactly as the
    lips it grows from: each vertex takes the weights of its two lip vertices on lo_body (bag_a, bag_b, bag_t), the
    back wall's middle their mean, so its rim never parts from the lips."""
    bag = attr('bag') > 0.5
    tg = ~bag
    regs = [(tg, U.chain_weights(co[tg], F.TONGUE, ['tongue.1', 'tongue.2', 'tongue.3'], 'jaw', fade=(0.02, -0.05)))]
    if bag.any():
        import bpy
        lo = bpy.data.objects['lo_body']
        gn, W = S.body_weights(lo)
        ia = np.rint(attr('bag_a')[bag]).astype(np.int64)
        ib = np.rint(attr('bag_b')[bag]).astype(np.int64)
        t = attr('bag_t')[bag][:, None]
        if ia.max() >= len(W):
            raise SystemExit('bloatoad mouth pocket: its lip vertices are not lo_body\'s (bag_a past the body\'s vertices)')
        mid = ia < 0
        lips = np.unique(ia[~mid])
        Wb = W[np.maximum(ia, 0)] * (1.0 - t) + W[np.maximum(ib, 0)] * t
        Wb[mid] = W[lips].mean(axis=0)
        regs.append((bag, {g: Wb[:, k].astype(np.float64) for k, g in enumerate(gn) if g in names and Wb[:, k].any()}))
    return regs


def preview_prop_colour(name: str):
    from monsters.breeds import bloatoad_paint as PT
    return PT.colours(PALETTE)['tongue']


# ----------------------------------------------------------------------------- eyes
def eye_matrix(s: int) -> Matrix:
    c, xax, yax, look = F.eye_frame(s)
    m = Matrix((tuple(xax), tuple(yax), tuple(look))).transposed().to_4x4()
    return Matrix.Translation(Vector(tuple(c - look * (EYE_R * EYE_DEPTH[1])))) @ m


def build_eye(name: str, s: int, high: bool):
    import bmesh
    import bpy
    bm = bmesh.new()
    seg = 48 if high else 24
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
    back = [v for v in bm.verts if v.co.z < -0.3]
    bmesh.ops.delete(bm, geom=back, context='VERTS')
    for v in bm.verts:
        v.co = Vector((v.co.x * EYE_R * EYE_SHAPE[0], v.co.y * EYE_R * EYE_SHAPE[1], v.co.z * EYE_R * EYE_DEPTH[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    C.link_obj(ob)
    ob.matrix_world = eye_matrix(s)
    co = np.array([v.co[:] for v in me.vertices])
    S.add_attr(ob, 'eyeuv', co / np.array([EYE_R * EYE_SHAPE[0], EYE_R * EYE_SHAPE[1], EYE_R * EYE_DEPTH[0]]))
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def blink_pivot(s: int):
    """At the closed lid's lash line, low in the opening: the lens squeezes down onto it (the upper lid coming down)."""
    c, xax, yax, look = F.eye_frame(s)
    c0 = c - look * (EYE_R * EYE_DEPTH[1])
    p = c0 + yax * (EYE_R * EYE_SHAPE[1] * F.CLOSED_LASH) + look * (EYE_R * 0.15)
    return Vector(tuple(p)), Vector(tuple(yax)), Vector(tuple(look))


def eye_material(name: str, rough_pass: bool = False, pal: dict | None = None):
    from monsters.breeds import bloatoad_eyes as EY
    return EY.eye_material(name, rough_pass, pal or PALETTE)


# ----------------------------------------------------------------------------- the high source
def carve(hi_body) -> None:
    from monsters.breeds import bloatoad_carve as CV
    CV.carve(hi_body)


def carve_low(lo_body) -> None:
    from monsters.breeds import bloatoad_carve as CV
    CV.carve_low(lo_body)


# ----------------------------------------------------------------------------- paint
def paint_sources(body_srcs, fins, props=()) -> None:
    from monsters.breeds import bloatoad_paint as PT
    PT.paint_sources(body_srcs, fins, props)


def body_material(name: str, attr: str, pal: dict, marks):
    from monsters.breeds import bloatoad_paint as PT
    return PT.body_material(name, attr, pal, marks)


def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    from monsters.breeds import bloatoad_paint as PT
    return PT.preview_colours(co, vn)


REVIEW = {'centre': (0.0, -0.02, 0.58), 'size': 1.75, 'head': ((0.0, -0.46, 0.9), 0.75)}
