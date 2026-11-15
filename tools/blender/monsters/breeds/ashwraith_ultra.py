"""Ashwraith at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md, the
"Floater plan" section).

A floating, tattered ash-grey shroud with no visible body inside, eerie but cute (chatgpt/monsters/15-ashwraith/): a
soft hood that overhangs a dark void with two ember crescents, its tip flopping over into a fat frayed wisp; the
shroud's torn panels clutched closed at the chest by two small cream hands; one long cape from the hood down the back;
torn, holed hems; thin smoky wisps curling under them; embers in the dark folds and a warm light through the tears.

- The shape: ashwraith_form.py (measured on 2-turnaround.png), ashwraith_body.py (the voxel body: the hood with its
  brim, torn rim and the face egg; a slim dark core inside the cloth), ashwraith_drape.py (the cloth's shapes).
- Props: ashwraith_cloth.py (the cape and the four front panels, real holes cut through them), ashwraith_props.py
  (the hood's tip, the hands, Lantern-bearer's lantern), ashwraith_wisps.py (the wisps and the two front streamers),
  on ashwraith_mesh.py's builders.
- Colours and paint: ashwraith_paint.py; the per-pixel bake materials: ashwraith_shade.py.

Part counts (the card): no visible body; two ember eyes (no mouth: the jaw stays merged into the head); tiny hands
peeking out (little two-bone arms, floating mittens: no sleeves); the hood tip on a 3-bone `hood` chain; eight 3-bone
`wisp` chains round the hems; two 3-bone `ribbon` streamers from the hands' grip (the lash strike's whips).
Size: about 1.1 x Puddlepup (PROMPTS.md): HEIGHT_UNITS 165, the tip's top at about 1.10 m.
Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import math

import bpy
import numpy as np

from lib import surface as S
from lib import ultra as U
from lib.surface import smooth
from monsters.breeds import ashwraith_body as B
from monsters.breeds import ashwraith_cloth as CL
from monsters.breeds import ashwraith_drape as D
from monsters.breeds import ashwraith_form as F
from monsters.breeds import ashwraith_paint as WP
from monsters.breeds import ashwraith_props as PR
from monsters.breeds import ashwraith_shade as SH
from monsters.breeds import ashwraith_wisps as WS

ID = 'ashwraith'
LOOK = 'ashwraith-ultra'
PLAN = 'floater'
HEIGHT_UNITS = 165

PALETTE = dict(WP.BASE)
VARIANTS = {'lantern-bearer-ashwraith': {'body': '#2B2F3A', 'belly': '#4A5366', 'accent': '#5AB6FF', 'eye': '#CFF0FF',
                                         'props': ['lantern'], 'lantern': True}}

GLOW = {'strength': 1.6, 'tint': None, 'twinkle': 0.3}
ATLAS_STRIP = 0
BODY_TRIS = 40000
ATLAS_DENSITY = {'lo_eyes': 2.4}
AO_FLOOR = 0.25
AO_SOFTEN = 1.5
BODY_SHEEN = 0.0                    # the body's cloth matches the props' cloth (no sheen)
NORMAL_SCALE = 1.0                  # round 2: the folds and the torn edges at full strength
LITE_PROPS_TRIS = 6000
BLINK_CLOSED = (0.94, 0.03, 0.2)    # round 3: a thin line (it read as a soft blurred arch)
MOUTH_SOCKET = (0.0, -0.17, 0.64)

all_parts = B.all_parts
body_extras = B.body_extras
zones = B.zones
decimate_keep = B.decimate_keep
carve = B.carve
colours = WP.colours
body_material = SH.body_material
glow_material = SH.glow_material
prop_material = SH.prop_material
eye_material = SH.eye_material
make_marks = SH.make_marks


def texel_k(co: np.ndarray) -> np.ndarray:
    """lo_body's texel density per face: the hood's cloth 1.2, the dark face 0.9, the core (mostly hidden) 0.45."""
    zz = B.zones(co)
    k = np.where(zz['hood'], 1.2, 1.0)
    k = np.where(zz['face'], 2.2, k)                     # round 3: the embers on the face stepped in squares
    return np.where(zz['core'], 0.45, k)


# ----------------------------------------------------------------------------- the eyes
def build_eye(name: str, s: int, high: bool) -> bpy.types.Object:
    """Round 2: the patch is the crescent itself (a strip along its spine, CRES_MARGIN of halo either side), laid on
    the face egg along its radius, bulging EYE_DOME along the spine and tucked EYE_SINK under at its rim. No square of
    backing shows round it (the oval patch read as a darker disc)."""
    c, xa, ya, lk = F.eye_frame(s)
    nphi, nw = (120, 16) if high else (26, 6)
    phi = np.linspace(-F.CRES_PHI, F.CRES_PHI, nphi)
    spine = F.cres_spine(phi)
    half = F.cres_thick(phi) * 0.5
    nrm2 = np.stack([np.sin(phi), np.cos(phi)], axis=1)
    verts, uvw = [], []
    ws = np.linspace(-1.0, 1.0, nw + 1)
    for k in range(nphi):
        reach = half[k] + F.CRES_MARGIN
        for w in ws:
            q2 = spine[k] + nrm2[k] * (w * reach)
            verts.append(np.array((c + xa * float(q2[0]) + ya * float(q2[1]))[:]))
            off = abs(w) * reach
            uvw.append((phi[k] / F.CRES_PHI, (w * reach) / half[k], off - half[k]))
    P = np.array(verts)
    on = F.face_point(P)
    nrm = F.face_normal(on)
    w3 = np.array(uvw)
    bulge = np.clip(1.0 - np.abs(w3[:, 1]) * 0.5, 0.0, 1.0)
    h = F.EYE_DOME * bulge - F.EYE_SINK * smooth(0.0, F.CRES_MARGIN, w3[:, 2])
    co = on + nrm * h[:, None]
    m = nw + 1
    faces = [(k * m + j, k * m + j + 1, (k + 1) * m + j + 1, (k + 1) * m + j) for k in range(nphi - 1) for j in range(nw)]
    ob = S.sheet_object(name, co, faces, out=tuple(lk))
    S.add_attr(ob, 'eyeuv', w3)
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    if high:
        S.add_attr(ob, 'glow', eye_glow(w3))
    return ob


def eye_glow(w: np.ndarray) -> np.ndarray:
    """The crescent glows hottest along its spine, less at its edges, a little in the halo."""
    aw = np.abs(w[:, 1])
    core = 0.68 - 0.12 * smooth(0.3, 1.0, aw) + 0.12 * smooth(0.24, 0.08, aw)   # polish: an even ember fill, a thin hot line
    halo = 0.42 * smooth(F.CRES_MARGIN, 0.0, w[:, 2]) ** 1.6
    return np.where(aw <= 1.0, core, halo)


def blink_pivot(s: int):
    """At the crescent's middle height: a blink squashes it onto a thin line and sinks it into the face, where a faint
    arc along the spine is painted."""
    c, _xa, ya, lk = F.eye_frame(s)
    return c + ya * 0.002 - lk * (F.EYE_R * 0.5), ya, lk


# ----------------------------------------------------------------------------- paint
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return WP.body_paint(co, PALETTE)['paint']


def preview_prop_colour(name: str):
    col = WP.colours(PALETTE)
    return {'cape': col['shroud'], 'panels': col['shroud'], 'tip': col['shroud'], 'hands': col['hand'], 'wisps': col['smoke_root'],
            'lantern': col['iron']}.get(name, col['shroud'])


def build_props(high: bool, quick: bool) -> list:
    tag = 'hi' if high else 'lo'
    cloth = [CL.cape_object(f'{tag}_cape', high), CL.mid_object(f'{tag}_midcape', high), CL.panels_object(f'{tag}_panels', high)]
    return cloth + PR.objects(high, quick) + [WS.wisps_object(f'{tag}_wisps', high)]


def paint_sources(body_srcs, fins, props=()) -> None:
    for ob in body_srcs:
        co, _vn = S.mesh_arrays(ob)
        a = WP.body_paint(co, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'glow', a['glow'])
        S.add_attr(ob, 'inner', a['inner'])
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), WP.body_paint(co, var)['paint'])
    for ob in props:
        a = WP.prop_paint(ob, PALETTE)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'glow', a['glow'])
        for vid, var in VARIANTS.items():
            S.set_colour_attr(ob, U.variant_attr(vid, ID), WP.prop_paint(ob, var)['paint'])


# ----------------------------------------------------------------------------- the rig (plans/floater.py)
LANTERN = {'name': 'lantern', 'parent': 'forearm.L', 'head': tuple(PR.RING_C),
           'tail': (0.0, float(PR.LANTERN_C[1]), PR.LANTERN_Z['base'])}
HOOD_CALM = -1.0                    # the hood chain's calm factor (its rotations are turned round: it points up)


def _chain_names() -> list[tuple[str, float]]:
    """(chain name, angle round the body) of the eight wisp chains."""
    out = []
    for nm, t0 in D.WISPS:
        for tag, s in (('L', 1), ('R', -1)):
            out.append((f'{nm}{tag}', s * t0))
    return out


def _flare(deg: float, t0: float, t1: float) -> dict:
    """Each wisp chain's first bone swung outward (the hems flare like the sidesteps' cape)."""
    return {f'{nm}.1': [(t0, t1, (-deg * math.cos(th), -deg * math.sin(th), 0.0))] for nm, th in _chain_names()}


def _hood(x: float, y: float, z: float) -> tuple:
    return (x / HOOD_CALM, y / HOOD_CALM, z / HOOD_CALM)


def clip_bones() -> dict:
    """The per-clip extras (plans/floater.py `clip_bones`; rotations in degrees, offsets in metres x size_k)."""
    strike = _flare(6.0, 0.3, 0.85)
    for tag in ('L', 'R'):
        # round 3: the thick front lash wisps coil back in the wind-up, then whip forward and up past the hands in a
        # curl, and trail back (the plan's own lash swing adds about 70 degrees forward at the impact)
        strike[f'lash{tag}.1'] = [(0.0, 0.42, (40.0, 0.0, 0.0)), (0.28, 0.72, (-86.0, 0.0, 0.0))]
        strike[f'lash{tag}.2'] = [(0.0, 0.42, (40.0, 0.0, 0.0)), (0.28, 0.72, (-17.0, 0.0, 0.0))]
        strike[f'lash{tag}.3'] = [(0.0, 0.42, (34.0, 0.0, 0.0)), (0.28, 0.72, (-7.0, 0.0, 0.0))]
        strike[f'wispA{tag}.1'] = [(0.0, 0.42, (30.0, 0.0, 0.0))]
        strike[f'wispA{tag}.2'] = [(0.0, 0.42, (34.0, 0.0, 0.0))]
        strike[f'wispA{tag}.3'] = [(0.0, 0.42, (34.0, 0.0, 0.0))]
    # polish: in the wind-up both hands rise toward the hood's rim, out to its sides (clear of the eyes)
    strike['upperarm.L'] = [(0.0, 0.44, (-48.0, 0.0, 42.0))]
    strike['upperarm.R'] = [(0.0, 0.44, (-48.0, 0.0, -42.0))]
    # it leans back a little and turns toward its left as it lashes, so both eyes stay on the 70-degree camera
    strike['hover'] = [(0.26, 0.86, (-34.0, 0.0, 34.0))]      # rears back: the front hem and the lash fly up
    strike['hood.1'] = [(0.3, 0.85, _hood(30.0, 0.0, 0.0))]
    win = _flare(20.0, 0.06, 0.5)
    win['hover'] = [(0.04, 0.42, (0.0, 0.0, 0.0), (0.0, 0.0, 0.1))]          # a higher rise
    win['upperarm.L'] = [(0.04, 0.52, (-42.0, 0.0, 70.0))]                 # both hands up and out (round 3; y only rolls)
    win['upperarm.R'] = [(0.04, 0.52, (-42.0, 0.0, -70.0))]
    win['hood.1'] = [(0.04, 0.52, _hood(-10.0, 34.0, 0.0))]                # the tip perks up
    win['hood.2'] = [(0.04, 0.52, _hood(-25.0, 26.0, 0.0))]
    # ko: the tip curls in over the hood as it falls (round 2: it dragged behind like a tail); held to the end
    ko = {'hood.1': [(0.3, 1.7, _hood(-20.0, 55.0, 0.0))], 'hood.2': [(0.3, 1.7, _hood(-30.0, 30.0, 0.0))],
          'hood.3': [(0.3, 1.7, _hood(-30.0, 0.0, 0.0))]}
    # hit (polish: the hood hinged back alone like a bin lid): the plan's spine bend is cancelled, so the whole body
    # rocks back on its hover tilt, a little more of it
    hit = {'chest': [(0.0, 0.8, (3.6, 2.7, 6.3))], 'head': [(0.0, 0.8, (4.4, 3.3, 7.7))], 'hover': [(0.0, 0.8, (-8.0, 0.0, 0.0))]}
    # hit_heavy: the hands fold down and in to the chest (the plan lifts them about 22 degrees; they sat on top like
    # frog eyes)
    hh = {'upperarm.L': [(0.0, 0.6, (30.0, 0.0, -10.0))], 'upperarm.R': [(0.0, 0.6, (30.0, 0.0, 10.0))]}
    return {'strike': strike, 'win': win, 'ko': ko, 'hit': hit, 'hit_heavy': hh}


def rig_p() -> dict:
    chains = [{'name': 'hood', 'kind': 'hood', 'parent': 'head', 'points': F.HOOD_TIP}]
    for nm, t0 in D.WISPS:
        chains.append({'name': nm, 'kind': 'wisp', 'parent': 'hips', 'points': D.wisp_chain(t0, 1), 'mirror': True})
    chains.append({'name': 'lash', 'kind': 'ribbon', 'parent': 'hips', 'points': D.lash_chain(1), 'mirror': True})
    return {
        'hip': F.HIP, 'chest': F.CHEST, 'body_base': F.BASE,
        'head_c': F.HEAD_C, 'head_r': F.HEAD_R,
        'arms': {**F.ARM, 'parent': 'chest'},
        'chains': chains,
        'props': [LANTERN],
        'bob': 0.6, 'strike_style': 'lash', 'glide_lean': 1.2, 'arm_pitch': 1.0,
        # ko: the body (hood and core) lies 5 cm up, so the wider cloth lies on the ground rather than through it
        'ko_ground': 0.05, 'ko_chain_hang': 0.85, 'hit_heavy_chain_hang': 0.6,
        'clip_bones': clip_bones(),
    }


def _hem_weights(co: np.ndarray, z: np.ndarray | None = None, th: np.ndarray | None = None) -> dict:
    """Below the middle, the cloth (and what hangs from its hems) rides its two nearest wisp chains by its angle round
    the body: bone 1 from z 0.4 down to the hems, bone 2 at the lowest tatters; above, the squash chain."""
    z = co[:, 2] if z is None else z
    if th is None:
        _a, _b, yc = D.sh_abyc(z)
        th = F.theta_of(co, yc)
    names = _chain_names()
    angs = np.array([a for _n, a in names])
    d = np.abs(np.angle(np.exp(1j * (th[:, None] - angs[None, :]))))
    order = np.argsort(d, axis=1)[:, :2]
    da = np.take_along_axis(d, order, axis=1)
    wa = da[:, 1] / np.maximum(da.sum(1), 1e-9)
    s2 = smooth(0.2, 0.12, z) * 0.6
    s1 = smooth(0.42, 0.3, z) * (1.0 - s2)
    W: dict[str, np.ndarray] = {}
    for k, (nm, _a) in enumerate(names):
        share = np.where(order[:, 0] == k, wa, 0.0) + np.where(order[:, 1] == k, 1.0 - wa, 0.0)
        if share.any():
            W[f'{nm}.1'] = share * s1
            W[f'{nm}.2'] = share * s2
    rest = 1.0 - s1 - s2
    wl = smooth(0.5, 0.42, z)
    W['hips'] = rest * wl
    W['chest'] = rest * (1.0 - wl)
    return W


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The hood and the face on `head` (the eyes ride its blink bones), the core on `chest` and `hips` by height. No
    sleeves: the hands float clear of the cloth when raised."""
    z = co[:, 2]
    zz = B.zones(co)
    wh = np.where(zz['core'], 0.0, smooth(0.57, 0.65, z))
    wh = np.where(zz['face'] | (zz['open_k'] > 0.3), 1.0, wh)
    wl = smooth(0.5, 0.4, z) * (1 - wh)
    return [(np.ones(len(co), bool), {'head': wh, 'hips': wl, 'chest': 1.0 - wh - wl})]


def prop_weight_regions(co: np.ndarray, attr, names: list[str], mesh: str | None = None) -> list:
    part = np.rint(attr('part')).astype(int)
    pt = attr('pt').astype(np.float64)
    out = [(np.ones(len(co), bool), {'chest': np.ones(len(co))})]
    m = np.isin(part, (PR.CAPE, PR.PANEL))
    if m.any():
        W = _hem_weights(co[m])
        if (part[m] == PR.CAPE).any():
            # the cape's top rides the hood (it is tucked inside it)
            wh = np.where(part[m] == PR.CAPE, smooth(0.66, 0.74, co[m, 2]), 0.0)
            for b in list(W):
                W[b] = W[b] * (1.0 - wh)
            W['head'] = wh
        out.append((m, W))
    m = part == PR.TIP
    if m.any():
        out.append((m, U.chain_weights(co[m], F.HOOD_TIP, ['hood.1', 'hood.2', 'hood.3'], 'head', fade=(0.1, -0.02))))
    for tag, s in (('L', 1), ('R', -1)):
        m = (part == PR.HAND) & (np.sign(co[:, 0]) == s)
        if m.any():
            out.append(U.rigid(m, f'forearm.{tag}'))
    m = part == PR.WISP
    if m.any():
        rth = attr('rth').astype(np.float64)[m]
        rz = attr('rz').astype(np.float64)[m]
        W0 = _hem_weights(co[m], z=rz, th=rth)
        t = np.clip(pt[m], 0, 1)
        along = smooth(0.05, 0.35, t)
        s3 = smooth(0.3, 0.85, t)
        Wm: dict[str, np.ndarray] = {b: v * (1.0 - along) for b, v in W0.items()}
        names8 = _chain_names()
        angs = np.array([a for _n, a in names8])
        near = np.argmin(np.abs(np.angle(np.exp(1j * (rth[:, None] - angs[None, :])))), axis=1)
        for k, (nm, _a) in enumerate(names8):
            sel = near == k
            if sel.any():
                Wm[f'{nm}.2'] = Wm.get(f'{nm}.2', 0.0) + np.where(sel, along * (1.0 - s3), 0.0)
                Wm[f'{nm}.3'] = Wm.get(f'{nm}.3', 0.0) + np.where(sel, along * s3, 0.0)
        out.append((m, Wm))
    m = part == PR.LASH
    if m.any():
        ch = np.rint(attr('chain')).astype(int)
        for ci, tag, s in ((8, 'L', 1), (9, 'R', -1)):
            mm = m & (ch == ci)
            if mm.any():
                out.append((mm, U.chain_weights(co[mm], D.lash_chain(s), [f'lash{tag}.1', f'lash{tag}.2', f'lash{tag}.3'], 'hips')))
    m = np.isin(part, PR.LANTERN_PARTS)
    if m.any():
        # round 3: held in both hands (it hung from one): half on each forearm
        out.append((m, {'forearm.L': np.full(int(m.sum()), 0.5), 'forearm.R': np.full(int(m.sum()), 0.5)}))
    return out


# the hood's tip points up, so the plan's trailing swing (which swings a hanging chain back) would tip it forward:
# its rotations are turned round in every clip (HOOD_CALM); in ko clip_bones curls it in over the hood. The wisps whip
# fully in the strike (the wind-up lifts the hands to the rim: clip_bones); in the win clip_bones spreads them out.
CLIP_CALM = {'*': {'hood': HOOD_CALM}, 'strike': {'hood': HOOD_CALM, 'wisp': 1.0, 'arm': 0.8},
             'win': {'hood': HOOD_CALM, 'arm': 0.5}}

FACE_NOTE = ('No face but two ember eyes in the dark of the hood: each eye is a matte crescent patch (lo_eyes) laid on '
             'the dark face egg, a hot core along its spine fading to ember and a thin halo, glowing (the glow map); a '
             'soft ember halo is painted on the face round each. No mouth (the jaw is merged into the head). '
             'Expressions in clips\' `faces` are hints only. Blinking scales the blink bones (play `blink` over any clip): '
             'each crescent squashes onto a thin line and sinks into the face, where a faint arc is painted. The core\'s '
             'warm light, the embers, the cut edges and the cloth\'s underside by the hems glow too.')

REVIEW = {'centre': (0.0, 0.03, 0.56), 'size': 1.26, 'head': ((0.0, -0.1, 0.74), 0.64)}
