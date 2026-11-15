"""Mirrorkin at Art 2.1 Ultra: the recipe for `tools/blender/monsters/build_ultra.py` (contract: breeds/RECIPE.md, the
"Floater plan" section).

A living hand mirror floating upright, sly, theatrical and a little vain (chatgpt/monsters/17-mirrorkin/, CONTENT 16):
an oval convex glass in an ornate gilded frame with curling scrolls and violet gems; the handle hangs below as its tail;
its face is drawn softly in the glass; a violet silk ribbon cloak bunches over the frame's shoulders and falls from the
side clasps in two flared panels with a gold-trimmed hem; two little white gloves with gold bracelets float beside it.

- The shape: mirrorkin_form.py (measured on 2-turnaround.png; the mirror and the handle are exact closed solids voxel-
  united into the body, the gloves are rounded parts); the high source's engraving here (carve).
- The ornaments and the gems: mirrorkin_ornament.py; the cloak: mirrorkin_cloak.py (built with mirrorkin_mesh.py).
- Colours and paint: mirrorkin_paint.py; the per-pixel bake materials (the face, the engraving, the cloak's trim):
  mirrorkin_shade.py.

Part counts (the card): two floating gloved hands, one handle-tail, one cloak (two panels), no other limbs. The face is
baked (no face sheet, no morphs): one expression is painted, the turnaround's calm closed smile with the eyes open; the
clips' face hints are hints only. Size: about 1.2 x Puddlepup (PROMPTS.md): HEIGHT_UNITS 180; the crest's tip at 1.18
m, the handle's tip 4.4 cm off the ground. Metres; the monster faces -Y, Z is up, +X is its left.
"""
from __future__ import annotations

import numpy as np

from lib import surface as S
from lib import ultra as U
from lib.surface import smooth
from monsters.breeds import mirrorkin_cloak as CL
from monsters.breeds import mirrorkin_form as F
from monsters.breeds import mirrorkin_mesh as MM
from monsters.breeds import mirrorkin_ornament as OR
from monsters.breeds import mirrorkin_paint as MP
from monsters.breeds import mirrorkin_shade as SH

ID = 'mirrorkin'
LOOK = 'mirrorkin-ultra'
PLAN = 'floater'
HEIGHT_UNITS = 180

# CONTENT 16: glass / highlights / cloak (frame) / eyes; the glove white is the card's (a part CONTENT has no colour for)
PALETTE = {'body': '#CFD8E3', 'belly': '#EEF3F8', 'accent': '#6C5CE7', 'eye': '#2B2B33', 'frame': '#C9A04A', 'glove': '#F3F1EC'}
# src/art/monster/variants.ts: black glass, a silver-grey frame and cloak, the face glowing pale (its picture)
VARIANTS = {'obsidian-mirrorkin': {'body': '#141418', 'belly': '#2C2C34', 'accent': '#7A7A88', 'eye': '#E0E0EA',
                                   'frame': '#7A7A88', 'glove': '#F3F1EC', 'obsidian': True}}

# a faint glow lifts the glass's sheen and the gold's ridges out of the grey studio (polished metal read dark there);
# steady (twinkle 0: a large glowing area showed the runtime's per-cell twinkle as a square stipple)
GLOW = {'strength': 0.5, 'tint': None, 'twinkle': 0.0}
# Obsidian: the face in the black glass glows pale (its own glow mask: the lids, the brows, the mouth, the blush)
VARIANT_ORM = {'obsidian': {'glow': {'strength': 1.4, 'tint': None, 'twinkle': 0.0}}}

ATLAS_STRIP = 0                     # no fur cards, no tuft
BODY_TRIS = 38000
VOXELS = {'hi': 0.0022, 'hi_quick': 0.005, 'lo': 0.0045}
ATLAS_DENSITY = {'lo_eyes': 1.4, 'lo_fins': 1.3}
AO_FLOOR = 0.4
AO_SOFTEN = 1.2
BODY_SHEEN = 0.0                    # glass and metal: no fur sheen (it veils the gold)
NORMAL_SCALE = 1.0                  # the engraving at full strength
LITE_PROPS_TRIS = 5200              # the cloak and the ornaments are the look
BLINK_CLOSED = (0.78, 0.04, 0.2)
MERGE_INTO_HEAD = ('jaw', 'eye.L', 'eye.R')      # the mouth is painted; it never opens
# the beam of the pulse strike leaves the glass's middle (5-poses attack: a reflected beam from its glass)
SOCKET_POINTS = {'socket_core': ('head', (0.0, F.YG0 - F.DOME - 0.01, F.ZC)),
                 'socket_mouth': (0.0, -0.075, F.MOUTH_Z)}

all_parts = F.all_parts
zones = F.zones
decimate_keep = F.decimate_keep
body_material = SH.body_material
glow_material = SH.glow_material
prop_material = SH.prop_material
eye_material = SH.eye_material
colours = MP.colours


def body_extras() -> list:
    rings, a, b = F.mirror_rings(224)
    hr, ha, hb = F.handle_rings(72)
    return [MM.closed_object('mirror_solid', rings, (a, b)), MM.closed_object('handle_solid', hr, (ha, hb))]


def texel_k(co: np.ndarray) -> np.ndarray:
    """lo_body's texel density per face: the whole glass 1.5 (round 1: one density, so the glass stays one island; a
    denser face patch cut a seam round it that bled gold and lilac at small mips), the frame 1, the back 0.6, the
    gloves 0.9."""
    z = F.zones(co)
    k = np.ones(len(co))
    # polish: only the dome inside the steep band at the rim (within about 56 degrees of facing front, so it projects as
    # one island); the band goes with the frame (it pulled pieces out of the glass: a hairline seam, ochre specks)
    k = np.where((F.glass_rho(co[:, 0], co[:, 2]) < 0.96) & (co[:, 1] < -0.02), 1.5, k)
    k = np.where((co[:, 1] > 0.03) & ~z['glove'] & ~z['handle'], 0.6, k)
    k = np.where(z['glove'], 0.9, k)
    return k


# ----------------------------------------------------------------------------- carving (the high source)
def _nose(co: np.ndarray) -> np.ndarray:
    x, z = co[:, 0], co[:, 2]
    return np.exp(-((x / 0.011) ** 2 + ((z - F.NOSE[1]) / 0.0095) ** 2)) * F.glass_mask(co)


def engraving(co: np.ndarray) -> np.ndarray:
    """Relief (metres along the normal) on the gold: pearl beading on the inner bead, a twisted rope on the main bead,
    the back's raised oval border and its diamond (2-turnaround back), flutes down the handle's neck and two rings on
    the bulb."""
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    phi, d = F.ring_offset(x, z)
    q = d / F.band_k(phi)
    front = y < -0.02
    gl = F.glove_k(co) != 0
    hm = F.handle_mask(co)
    ring = ~gl & ~hm & ~F.glass_mask(co)
    disp = np.zeros(len(co))
    bead = ring & front & (q > 0.003) & (q < 0.012)
    disp += bead * 0.0006 * np.cos(phi * 200.0) ** 2
    rope = ring & front & (q > 0.018) & (q < 0.04)
    f = np.mod(phi * 120.0 / (2 * np.pi) + q / 0.011, 1.0)
    disp -= rope * 0.0011 * np.exp(-((f - 0.5) / 0.09) ** 2) * smooth(0.018, 0.021, q) * smooth(0.04, 0.037, q)
    back = ring & (y > 0.035)
    rb = F.glass_rho(x, z)
    # round 1: deeper relief on the flat back plate (2-turnaround back): the oval border, the diamond, its star and the
    # arabesques (C-scrolls opening toward the diamond, as painted in mirrorkin_shade.engraving)
    disp += back * 0.003 * np.exp(-((rb - 0.74) / 0.018) ** 2)
    dia = np.abs(x) / 0.07 + np.abs(z - F.ZC) / 0.13
    disp += back * 0.0028 * np.exp(-((dia - 1.0) / 0.045) ** 2)
    star = np.abs(x) / 0.025 + np.abs(z - F.ZC) / 0.05
    disp += back * 0.0045 * smooth(1.0, 0.35, star)
    for sgn in (1, -1):
        for cx, cz, r in ARABESQUES:
            dx, dz = x - cx * sgn, z - (F.ZC + cz)
            d = np.hypot(dx, dz)
            out = smooth(-0.35, 0.05, dx * sgn / np.maximum(d, 1e-4))
            disp += back * out * 0.0022 * (np.exp(-((d - r) / 0.0022) ** 2) + np.exp(-((d - 0.45 * r) / 0.002) ** 2))
    ang = np.arctan2(y - F.HANDLE_Y, x)
    neck = hm & (z > 0.25) & (z < 0.43)
    disp -= neck * 0.0006 * np.exp(-((np.mod(ang * 8 / (2 * np.pi), 1.0) - 0.5) / 0.1) ** 2)
    # round 1: an engraved vine winding down the shaft, front and back, with little leaves (4-details panel 4)
    for a0 in (-np.pi / 2, np.pi / 2):
        av = a0 + 0.55 * np.sin(2 * np.pi * (z - 0.25) / 0.06)
        da = np.angle(np.exp(1j * (ang - av)))
        disp += neck * 0.0028 * np.exp(-(da / 0.12) ** 2)
        leaf_a = av + 0.32 * np.sign(np.cos(2 * np.pi * (z - 0.25) / 0.06))
        dl = np.angle(np.exp(1j * (ang - leaf_a)))
        lz = np.mod((z - 0.25) / 0.03, 1.0) - 0.5
        disp += neck * 0.0032 * np.exp(-(dl / 0.2) ** 2 - (lz / 0.26) ** 2)
    rings_ = hm & ((np.abs(z - 0.236) < 0.004) | (np.abs(z - 0.092) < 0.003))
    disp += rings_ * 0.001
    return disp


# the back's arabesques: (x, z from the oval's centre, radius), mirrored
ARABESQUES = ((0.052, 0.148, 0.034), (0.1, 0.0, 0.042), (0.052, -0.148, 0.034))


def body_attrs(co: np.ndarray) -> dict:
    """Per-point attributes the per-pixel bake reads: the ring's angle and profile coordinate, the glass's radius, and
    the gloves' own frame (for the stitching)."""
    phi, d = F.ring_offset(co[:, 0], co[:, 2])
    out = {'rphi': phi, 'rq': d / F.band_k(phi), 'rrho': F.glass_rho(co[:, 0], co[:, 2])}
    gk = F.glove_k(co)
    ga, gu, gt = np.zeros(len(co)), np.zeros(len(co)), np.zeros(len(co))
    for s in (1, -1):
        on = gk == s
        if on.any():
            L = F.glove_local(co[on], s)
            ga[on], gu[on], gt[on] = L[:, 0], L[:, 1], L[:, 2]
    out.update({'gk': gk, 'ga': ga, 'gu': gu, 'gt': gt})
    return out


def snap_glass(co: np.ndarray) -> np.ndarray:
    """The glass onto its exact dome, blending out at the lip (review round 2: the voxel body's faint terraces baked into
    the normal map as banding and a woven hatch in tilted views)."""
    rho = F.glass_rho(co[:, 0], co[:, 2])
    w = smooth(1.0, 0.965, rho) * (co[:, 1] < -0.02) * (F.glove_k(co) == 0)
    out = co.copy()
    out[:, 1] = co[:, 1] + w * (F.glass_y(co[:, 0], co[:, 2]) - co[:, 1])
    return out


def carve(ob) -> None:
    co, _vn = S.mesh_arrays(ob)
    S.set_positions(ob, snap_glass(co))
    co, vn = S.mesh_arrays(ob)
    disp = 0.0042 * _nose(co) + engraving(co)
    S.set_positions(ob, co + vn * disp[:, None])
    S.base_attrs(ob, co)
    for k, v in body_attrs(co).items():
        S.add_attr(ob, k, v)


def carve_low(ob) -> None:
    co, _vn = S.mesh_arrays(ob)
    S.set_positions(ob, snap_glass(co))
    co, vn = S.mesh_arrays(ob)
    S.set_positions(ob, co + vn * (0.0042 * _nose(co))[:, None])


# ----------------------------------------------------------------------------- the eyes
def build_eye(name: str, s: int, high: bool):
    """The eye is an oval patch laid on the glass itself (the oval in the eye's tangent plane, each point carried onto
    the glass and lifted along its normal), bulging EYE_DOME at its centre and tucked EYE_SINK under the glass at its
    rim, so the whole oval shows and it sits flush in profile."""
    c, xa, ya, lk = F.eye_frame(s)
    rings, seg = (24, 72) if high else (8, 36)
    verts, uvw = [np.array(c[:])], [(0.0, 0.0, 1.0)]
    for i in range(1, rings + 1):
        r = i / rings
        for j in range(seg):
            a = 2 * np.pi * j / seg
            verts.append(np.array((c + xa * (F.EYE_A * r * np.cos(a)) + ya * (F.EYE_B * r * np.sin(a)))[:]))
            uvw.append((r * np.cos(a), r * np.sin(a), 1.0 - r * r))
    P = np.array(verts)
    gy = F.glass_y(P[:, 0], P[:, 2])
    on = np.stack([P[:, 0], gy, P[:, 2]], axis=1)
    nrm = F.glass_normal(P[:, 0], P[:, 2])
    w = np.array(uvw)
    h = F.EYE_DOME * np.sqrt(np.clip(w[:, 2], 0, 1)) - F.EYE_SINK * (1.0 - w[:, 2]) ** 6
    co = on + nrm * h[:, None]
    faces = [(0, 1 + j, 1 + (j + 1) % seg) for j in range(seg)]
    for i in range(rings - 1):
        b0, b1 = 1 + i * seg, 1 + (i + 1) * seg
        faces += [(b0 + j, b1 + j, b1 + (j + 1) % seg, b0 + (j + 1) % seg) for j in range(seg)]
    ob = S.sheet_object(name, co, faces, out=tuple(lk))
    S.add_attr(ob, 'eyeuv', w)
    S.add_attr(ob, 'eye_side', np.full(len(co), float(s)))
    return ob


def blink_pivot(s: int):
    """Behind the lens at the closed lid's height: a blink squashes the lens onto the painted lash line and sinks it
    under the glass."""
    c, _xa, ya, lk = F.eye_frame(s)
    return c - ya * (F.EYE_B * 0.14) - lk * (F.EYE_A * 0.6), ya, lk


# ----------------------------------------------------------------------------- paint
def preview_colours(co: np.ndarray, vn: np.ndarray) -> np.ndarray:
    return MP.body_paint(co, vn, PALETTE)['paint']


def preview_prop_colour(name: str):
    return MP.preview_colour(name, PALETTE)


def build_props(high: bool, quick: bool) -> list:
    return OR.objects(high) + CL.objects(high)


def build_fins(high: bool, quick: bool) -> list:
    """The gems, as membranes: baked on their own (in the shared props bake their violet spilled onto the gold round
    them); in the game they take the fin material: glossy, two-sided, a faint glow of their own colour."""
    return OR.objects(high, 'gems')


def fin_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    """The gems ride what they're set in: the handle's on the handle chain, the bracelets' on the hands, the rest on
    the head (the same rules as the props)."""
    return prop_weight_regions(co, attr, names)


def paint_sources(body_srcs, fins, props=()) -> None:
    props = list(props) + list(fins)              # the gems (membranes) paint like the props
    for ob in body_srcs:
        co, vn = S.mesh_arrays(ob)
        # review round 2: smoother (the voxel lip's noise made a ragged pale highlight band along it)
        cav = MP.cavity(ob, 0.0007, iters=10)
        a = MP.body_paint(co, vn, PALETTE, cav)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'glow', a['glow'])
        for vid, var in VARIANTS.items():
            v = MP.body_paint(co, vn, var, cav)
            S.set_colour_attr(ob, U.variant_attr(vid, ID), v['paint'])
            # Obsidian: no glow on the black glass itself (the face glows per pixel), a little on the silver's ridges
            S.add_attr(ob, f'glow_{U.variant_short(vid, ID)}', np.where(v['glass'], 0.0, v['glow'] * 0.6))
        if 'rphi' not in ob.data.attributes:
            for k, val in body_attrs(co).items():
                S.add_attr(ob, k, val)
    for ob in props:
        cav = MP.cavity(ob, 0.0016, iters=3)       # round 2: thin tubes saturated a finer scale (all highlight, cream)
        a = MP.prop_paint(ob, PALETTE, cav)
        S.set_colour_attr(ob, 'paint', a['paint'])
        S.set_colour_attr(ob, 'rough', a['rough'])
        S.add_attr(ob, 'glow', a['glow'])
        for vid, var in VARIANTS.items():
            v = MP.prop_paint(ob, var, cav)
            S.set_colour_attr(ob, U.variant_attr(vid, ID), v['paint'])
            S.add_attr(ob, f'glow_{U.variant_short(vid, ID)}', v['glow'] * 0.6)


# ----------------------------------------------------------------------------- the rig (plans/floater.py)
HANDLE_PTS = [(0.0, F.HANDLE_Y, 0.50), (0.0, F.HANDLE_Y, 0.30), (0.0, F.HANDLE_Y, 0.07)]
CREST = {'name': 'crest', 'parent': 'head', 'head': (0.0, OR.CREST_Y, 1.04), 'tail': (0.0, OR.CREST_Y, 1.18)}


def hands_spec() -> dict:
    g = F.glove_points(1)
    tip = g['fingers'][1][2]
    return {'centre': tuple(map(float, g['palm'])), 'tip': tuple(map(float, tip)), 'parent': 'chest'}


def rig_p() -> dict:
    return {
        'hip': (0.0, 0.0, 0.70), 'chest': (0.0, 0.0, 1.16),
        'head_c': (0.0, -0.08, 0.80), 'head_r': 0.22,
        'hands': hands_spec(),
        'chains': [{'name': 'handle', 'kind': 'handle', 'parent': 'head', 'points': HANDLE_PTS},
                   {'name': 'cloak', 'kind': 'ribbon', 'parent': 'head', 'points': CL.chain_points(1), 'mirror': True}],
        'props': [CREST],
        'bob': 0.6, 'strike_style': 'pulse', 'sink': 0.12,
        # the pulse tips the glass to catch the light first (5-poses attack), then turns toward its left at the burst
        # so the face shows in the in-game strike shot (70 degrees)
        # review round 2: at the burst the glass faces the opponent squarely and tilts back about 15 degrees (the plan's
        # bend adds 6 forward to the hover's -21), rolls only a little (a 14-degree roll and a turn read as a lunge from
        # the 70-degree camera), barely travels, holds about 2.5 frames round `impact` (strike_hold: an opt-in plan
        # knob), and the gloves open wide either side of the frame (clip_bones)
        # polish (review round 3): the wind-up tips back about 20 degrees, the glass turned up to the light, the
        # gloves drawn in to the frame; at impact the glass faces the target squarely with its top pitched forward
        # about 15 degrees (the plan's 8 + pulse_lean 1 + its bend 6), no roll, held
        'pulse_tilt': 0.0, 'pulse_yaw': 0.0, 'pulse_lean': 1.0, 'pulse_push': -0.02, 'strike_hold': 0.1,
        'strike_windup_bones': {'hover': (-14.0, 0.0, 0.0)},
        'clip_bones': clip_bones(),
        # ko: the mirror falls back and lies face up on the ground (a hand mirror can't lie on its edge), tipped toward
        # the three-quarter camera's side; the cloak droops to the ground
        'ko_bones': {'hover': (-75.0, 100.0, 0.0), **KO_DRAPES}, 'ko_ground': 0.008, 'ko_chain_hang': 0.6,
        # the heavy hit flings it back about 27 degrees instead of 45, so the face stays in view (it lay flat)
        'hit_heavy_bones': {'hover': (18.0, 0.0, 8.0)},
    }


# ko (review round 2: one drape stood out flat like a flag): the drapes' lower bones fold down toward the ground
KO_DRAPES = {f'cloak{t}.{i}': (0.0, 0.0, 0.0) for t in 'LR' for i in (2, 3)}
KO_DRAPES.update({'cloakL.2': (35.0, 0.0, 0.0), 'cloakL.3': (40.0, 0.0, 0.0), 'cloakR.2': (35.0, 0.0, 0.0), 'cloakR.3': (40.0, 0.0, 0.0),
                  'cloakL.1': (0.0, 50.0, 0.0), 'cloakR.1': (0.0, -50.0, 0.0)})     # each drape lies along its side


def clip_bones() -> dict:
    """Opt-in per-clip extras (plans/floater.py `clip_bones`; offsets in metres at Puddlepup's size, x size_k).
    - strike: the gloves spread open round the glass through the burst (the plan brings them forward and in).
    - win (round 1: it read like idle): a vain flourish at the top of the jump (leaning back, tilted toward its left,
      one glove raised high, the other touching the frame's side), the plan's spin, then a deep bow at the end."""
    sk = HEIGHT_UNITS / 150.0
    return {
        'strike': {'hand.L': [(0.3, 0.75, (0.0, 0.0, -25.0), (0.1 / sk, 0.085 / sk, 0.02 / sk)),
                              (0.0, 0.42, (0.0, 0.0, 20.0), (-0.19 / sk, 0.045 / sk, -0.017 / sk))],
                   'hand.R': [(0.3, 0.75, (0.0, 0.0, 25.0), (-0.1 / sk, 0.085 / sk, 0.02 / sk)),
                              (0.0, 0.42, (0.0, 0.0, -20.0), (0.19 / sk, 0.045 / sk, -0.017 / sk))]},
        # polish: the walk leans in about 10 degrees, the handle trailing back about 12-15 with a little swell (a bump
        # from -0.5 to 1.5 of the clip is 0.7 at both ends, so it loops)
        'walk': {'hover': [(-0.5, 1.5, (6.0, 0.0, 0.0))], 'handle.1': [(-0.45, 1.55, (15.0, 0.0, 0.0))]},
        # review round 2: a deep theatrical bow peaking at t 0.2 (the sampled frame): it tips well forward and turns
        # toward the camera, one glove pressed to the frame's side, the other swept wide and low; then the plan's spin
        # polish: and it ends on a flourish: tipped about 15 degrees toward the camera, one glove high, the other at
        # the frame's side
        'win': {'hover': [(0.0, 0.42, (34.0, 0.0, 16.0)), (0.8, 1.0, (0.0, 15.0, 10.0))],
                'hand.L': [(0.0, 0.42, (0.0, 0.0, -40.0), (0.1 / sk, 0.05 / sk, -0.2 / sk)), (0.8, 1.0, (0.0, 0.0, -30.0), (0.02 / sk, 0.0, 0.1 / sk))],
                'hand.R': [(0.0, 0.42, (0.0, 0.0, 40.0), (0.2 / sk, 0.03 / sk, 0.0)), (0.8, 1.0, (0.0, 0.0, 40.0), (0.2 / sk, 0.03 / sk, 0.0))]},
    }


def handle_weights(co: np.ndarray) -> dict:
    return U.chain_weights(co, HANDLE_PTS, ['handle.1', 'handle.2'], 'head', fade=(0.12, 0.02))


def panel_weights(co: np.ndarray, s: int) -> dict:
    tag = 'L' if s > 0 else 'R'
    return U.chain_weights(co, CL.chain_points(s), [f'cloak{tag}.1', f'cloak{tag}.2', f'cloak{tag}.3'], 'head', fade=(0.1, 0.0))


def body_weight_regions(co: np.ndarray, names: list[str]) -> list:
    """The mirror is one rigid piece on `head` (the lenses ride the head's blink bones; the squash comes from the hover
    bone); the handle bends a little from the frame down its chain; each glove is rigid on its hand bone."""
    regs = [(np.ones(len(co), bool), {'head': np.ones(len(co))})]
    hm = F.handle_mask(co)
    if hm.any():
        regs.append((hm, handle_weights(co[hm])))
    gk = F.glove_k(co)
    for s, tag in ((1, 'L'), (-1, 'R')):
        regs.append(U.rigid(gk == s, f'hand.{tag}'))
    return regs


def prop_weight_regions(co: np.ndarray, attr, names: list[str]) -> list:
    part = np.rint(attr('part')).astype(int)
    out = [(np.ones(len(co), bool), {'head': np.ones(len(co))})]
    on_h = np.isin(part, OR.ON_HANDLE + (OR.COLLAR, OR.GEM + 3)) | ((part == OR.BEZEL) & (co[:, 2] < 0.3))
    if on_h.any():
        out.append((on_h, handle_weights(co[on_h])))
    for s, tag in ((1, 'L'), (-1, 'R')):
        pm = (part == CL.PANEL) & (np.sign(co[:, 0]) == s)
        if pm.any():
            out.append((pm, panel_weights(co[pm], s)))
        cm = np.isin(part, (OR.CUFF, OR.GEM + 4, OR.BEZEL)) & F.glove_mask(co, s) & (np.sign(co[:, 0]) == s)
        out.append(U.rigid(cm, f'hand.{tag}'))
    return out


CLIP_CALM = {'*': {'handle': 1.0, 'cloak': 1.0, 'hand': 1.0}}

FACE_NOTE = ('The face is drawn in the glass: the eyes are shallow glossy lenses (lo_eyes) laid flush on the convex glass, '
             'with the dark violet iris, the pupil and two catchlights; the lavender lids, the flick lashes, the brows, '
             'the small nose, the calm closed smile and the blush are baked into the body atlas. One expression is painted '
             '(no face sheet, no morphs): the clips\' `faces` are hints only, and the mouth never opens. Blinking scales the '
             'blink bones (play `blink` over any clip): each lens squashes onto its painted lash line and sinks under the '
             'glass. socket_core sits on the glass\'s middle (the pulse strike\'s reflected beam). Obsidian\'s face glows '
             'pale in the black glass (its own glow mask).')

REVIEW = {'centre': (0.0, 0.03, 0.6), 'size': 1.55, 'head': ((0.0, -0.06, 0.8), 0.62)}
