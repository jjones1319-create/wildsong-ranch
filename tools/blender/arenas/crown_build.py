"""The Crown Amphitheatre's build stage: every material, then every part into its atlas group's collection
(G_<group>; FAR_PANO holds what only the sky panorama sees). Saves crown_src.blend and stats_build.json.
"""
from __future__ import annotations

import json

import bpy
import numpy as np

from lib import common as C
import kit as K
import crown as CR
import crown_mats as S
import crown_mats2 as S2
import crown_mats3 as S3
from crown_geo import MB
import crown_bowl as BW
import crown_facade as FA
import crown_floor as FL
import crown_gates as GT
import crown_props as PR
import crown_banners as BN
import crown_top as TP
import crown_world as WD
import crown_dress as DR


class Mats:
    """Every material once, by name; `ix` maps a name to its slot (every object carries the whole list)."""

    def __init__(self) -> None:
        crowd = S2.crowd_paint
        emblem = S3.emblem_image()
        self.emblem = emblem
        m = {
            'trav': S.stone('trav', 'travertine', streak=0.8, grime=0.55, wear=0.3, foot=0.4, moss=0.3),
            'trav_dark': S.stone('trav_dark', 'travertine_dark', streak=0.3, grime=0.6, wear=0.2, foot=0.2, moss=0.2),
            'trav_trim': S.stone('trav_trim', 'travertine', streak=0.35, grime=0.45, wear=0.45, foot=0.0, val=1.06),
            'marble': S.stone('marble', 'marble', streak=0.3, grime=0.4, wear=0.3, foot=0.3, splash=0.6),
            'marble_trim': S.stone('marble_trim', 'marble', streak=0.25, grime=0.45, wear=0.45, foot=0.1, splash=0.3, val=0.96),
            'ashlar': S.stone('ashlar', 'ashlar', streak=0.35, grime=0.5, wear=0.3, foot=0.15),
            'seat1': S.stone('seat1', 'travertine', crowd=crowd, streak=0.2, grime=0.4, wear=0.35, foot=0.0, val=1.02),
            'seat2': S.stone('seat2', 'sandstone', crowd=crowd, streak=0.2, grime=0.4, wear=0.35, foot=0.0),
            'seat3': S.stone('seat3', 'sandstone', crowd=crowd, streak=0.2, grime=0.4, wear=0.35, foot=0.0, val=0.96),
            'stair': S.stone('stair', 'paving', streak=0.1, grime=0.4, wear=0.4, foot=0.0, val=1.04),
            'walk': S.stone('walk', 'paving', streak=0.1, grime=0.35, wear=0.3, foot=0.0, val=0.97),
            'dim': S.stone('dim', 'ashlar', streak=0.2, grime=0.5, wear=0.2, foot=0.2, val=0.82),
            'plaza': S.stone('plaza', 'plaza', streak=0.0, grime=0.35, wear=0.2, foot=0.0),
            'void': S.void(),
            'sand': None,
            'bronze': S.bronze('bronze'),
            'statue_marble': S.marble_obj('statue_marble'),
            'iron': S3.iron('iron'),
            'flame': S3.flame('flame'),
            'terracotta': S3.terracotta('terracotta'),
            'wood': S3.wood('wood'),
            'roof': S3.roof_tiles('roof'),
            'rope': S2.cloth('rope', '#9E2F2A'),
            'rigging': S2.cloth('rigging', '#B8A27A'),
            'banner_teal': S2.banner('banner_teal', '#1F7A72', '#F3E4C3', emblem),
            'banner_coral': S2.banner('banner_coral', '#C24F38', '#F3E4C3', emblem),
            'banner_plum': S2.banner('banner_plum', '#5E4287', '#F3E4C3', emblem),
            'awning_a': S2.stripes('awning_a', '#F1E6CC', '#1F7A72', 1.1, '#E7B24C'),
            'awning_b': S2.stripes('awning_b', '#F1E6CC', '#C24F38', 1.1, '#E7B24C'),
            'valance': S2.stripes('valance', '#E7B24C', '#5E4287', 0.4),
            'canopy': S2.stripes('canopy', '#5E4287', '#4B336F', 0.7, '#E7B24C'),
            'furled': S2.cloth('furled', '#E6D9BC'),
            'pennant_teal': S2.cloth('pennant_teal', '#1F7A72'),
            'pennant_coral': S2.cloth('pennant_coral', '#C24F38'),
            'pennant_gold': S2.cloth('pennant_gold', '#E7B24C'),
            'grass': S3.grass('grass'),
            'leaf': S3.foliage('leaf'),
            'bark': S3.bark('bark'),
            'plaster': S3.house('plaster'),
            'mountain': S3.mountain('mountain'),
            'emblem': S.emblem_bronze('emblem_bronze', emblem),
            'inset': S.inset('inset'),
            'door': S3.door('door'),
            'festoon': S2.stripes('festoon', '#5E4287', '#E7B24C', 0.5),
        }
        self.reliefs = FL.relief_images(np.asarray(_emblem_rows(emblem)))
        m['sand'] = FL.sand_mat(self.reliefs)
        self.all = list(m.values())
        self.ix = {k: i for i, k in enumerate(m)}

    def roles(self, **kw) -> dict:
        """Role name → slot, e.g. roles(wall='trav') → {'wall': ix['trav']}; lists stay lists."""
        return {k: ([self.ix[x] for x in v] if isinstance(v, list) else self.ix[v]) for k, v in kw.items()}


def _emblem_rows(img) -> np.ndarray:
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)[::-1, :, 0]          # rows top-down


def put(group: str, name: str, mb: MB, M: Mats, smooth: bool = False) -> bpy.types.Object | None:
    if not len(mb):
        return None
    coll = C.collection('FAR_PANO') if group == 'FAR_PANO' else C.collection('G_' + group)
    return mb.build(name, coll, M.all, smooth)


def stage_build(quick: bool) -> dict:
    C.clear_scene()
    CR.setup_scene(quick)
    rot = CR.setup_world()
    with C.Timer('materials'):
        M = Mats()
    R = M.roles
    with C.Timer('floor'):
        put('ring', 'ring_disc', FL.ring_disc(M.ix['sand']), M)
        for side in ('w', 'e'):
            put('apron_' + side, 'apron_' + side, FL.apron(side, M.ix['sand']), M)
        put('props', 'barrier', FL.barrier(R(curb='marble_trim', bronze='bronze', rope='rope')), M)
    with C.Timer('bowl'):
        put('podium', 'podium', BW.build_podium(1.2, R(base='marble_trim', face='marble', trim='marble_trim', walk='walk'), True), M)
        put('podium', 'podium_dress', DR.podium_dress(R(trim='marble_trim', inset='inset', door='door', emblem='emblem', bronze='bronze')), M)
        bowl = dict(front='marble', walk='walk', stair='stair', wall='ashlar', wood='wood')
        for ti, (seat, step, groups) in enumerate((('seat1', 1.2, ('low_n', 'low_s')), ('seat2', 1.6, ('mid', 'mid')), ('seat3', 2.2, ('top', 'top')))):
            n, s = BW.build_tier(ti, step, R(seat=seat, **bowl), 100 * ti, False)
            put(groups[0], f'tier{ti}_n', n, M)
            put(groups[1], f'tier{ti}_s', s, M)
            ln, ls = BW.build_tier(ti, 6.0, R(seat=seat, **bowl), 100 * ti, True, caps=False)
            put('lbowl_low' if ti == 0 else 'lbowl_high', f'lite_tier{ti}_n', ln, M)
            put('lbowl_low' if ti == 0 else 'lbowl_high', f'lite_tier{ti}_s', ls, M)
        put('mid', 'vomitoria', BW.vomitoria(R(void='void', wall='ashlar'), False), M)
    with C.Timer('top'):
        gr = R(column='marble_trim', trim='trav_trim', dim='dim', roof='roof')
        put('gallery', 'gallery', TP.gallery(gr, False), M)
        put('lbowl_high', 'lite_gallery', TP.gallery(gr, True, columns=False), M)
        put('facade', 'masts', TP.masts(R(trim='trav_trim', wood='wood')), M)
        put('velarium', 'velarium', TP.velarium(R(rope='rigging', furled='furled', awning=['awning_a', 'awning_b'], valance='valance',
                                                 pennant=['pennant_teal', 'pennant_coral', 'pennant_gold'])), M)
    with C.Timer('facade'):
        fr = R(wall='trav', rim='trav_dark', trim='trav_trim', void='void', dim='dim', floor='walk')
        put('facade', 'facade', FA.build_facade(fr), M)
        put('facade', 'ambulatory', FA.build_ambulatory(fr), M)
    with C.Timer('gates'):
        gm = R(face='marble', rim='trav_dark', trim='marble_trim', bronze='bronze', dim='dim', void='void', iron='iron',
               paving='stair', marble='marble_trim', canopy='canopy', valance='valance', inset='inset')
        for tag in ('A', 'B'):
            put('monuments', f'gatehouse_{tag}', GT.gatehouse(tag, gm), M)
        put('monuments', 'patrons_box', GT.patrons_box(gm), M)
        put('monuments', 'plinths', PR.plinths(R(trim='marble_trim', face='marble')), M)
        put('monuments', 'monument_dress', DR.monument_dress(R(emblem='emblem', bronze='bronze', festoon='festoon', trim='marble_trim', inset='inset')), M)
    with C.Timer('props'):
        put('props', 'urns', PR.urns(R(terracotta='terracotta')), M)
        put('props', 'braziers', PR.braziers(R(iron='iron', bronze='bronze', flame='flame')), M)
        put('props', 'banners', BN.build_banners({'banner': {c: M.ix['banner_' + c] for c in BN.COLOURS}}), M)
        smats = {'marble': M.all[M.ix['statue_marble']], 'bronze': M.all[M.ix['bronze']]}
        PR.build_statues(C.collection('G_statues'), smats)
        PR.build_statues(C.collection('G_lstatues'), smats, tris=750, lite=True)
    with C.Timer('world'):
        put('plaza', 'plaza', WD.plaza(R(plaza='plaza')), M)
        put('outskirts', 'plaza_dress', WD.plaza_dress(R(stone='trav_trim', wood='wood', awning=['awning_a', 'awning_b'])), M)
        put('land', 'land', WD.land(R(grass='grass')), M)
        put('outskirts', 'trees', WD.trees(R(bark='bark', leaf='leaf')), M)
        put('outskirts', 'town', WD.town(R(plaster='plaster', roof='roof')), M)
        put('FAR_PANO', 'mountains', WD.mountains(R(mountain='mountain')), M, smooth=True)
    CR.build_anchors()
    stats = {g: sum(K.tri_count(o) for o in C.collection('G_' + g).objects if o.type == 'MESH') for g in CR.GROUPS}
    stats['full'] = sum(v for g, v in stats.items() if g in CR.GROUPS and not CR.GROUPS[g][3])
    stats['hdri_rot'] = rot
    C.log('triangles by group: ' + json.dumps(stats))
    bpy.ops.wm.save_as_mainfile(filepath=str(CR.OUT / 'crown_src.blend'), compress=False)
    (CR.OUT / 'stats_build.json').write_text(json.dumps(stats, indent=1), encoding='utf-8')
    return stats
