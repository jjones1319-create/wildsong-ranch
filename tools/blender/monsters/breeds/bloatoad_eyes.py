"""Bloatoad's eyes (Art 2.1 Ultra): the lens material. Lazy golden eyes (1-hero, 3-faces neutral, 4-details panel 2): a
big gold iris filling the opening, finely streaked, a darker olive-brown ring at its edge and a warm inner ring, a round
dark pupil looking ahead (a little toward the nose, since the eyes face 31° outward), a soft shadow under the upper lid,
two catchlights. The lens's top, which the sculpted upper lid covers, is painted in the lid's dark olive, so a simplified
lid (the Lite copy) never shows a sliver of gold above it. The rough pass keeps the gold glossy.

The eye's own coordinates: `eyeuv` = (rx, ry, rz) in lens units (rx toward its outer corner on the left eye; × eye_side
on both), `eye_side` ±1.
"""
from __future__ import annotations

from lib import common as C
from lib.nodes import new_mat
from monsters.breeds import bloatoad_form as F


def eye_material(name: str, rough_pass: bool, pal: dict):
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    side = nb.attribute('eye_side').outputs['Fac']
    rx, ry, _z = nb.sep(e)
    rxs = nb.math('MULTIPLY', rx, side)
    # the upper lid's edge (bloatoad_form.lid_edge): a + b (1 - rx²) + c rx s
    a, b, cc = F.LID_EDGE
    edge = nb.math('ADD', nb.math('ADD', a, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, nb.math('MULTIPLY', rx, rx)), b)),
                   nb.math('MULTIPLY', rxs, cc))
    hidden = nb.smooth(nb.math('SUBTRACT', ry, edge), 0.02, 0.08)
    # the pupil looks ahead: a little toward the nose and down
    px = nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.1))
    py = nb.math('ADD', ry, 0.04)
    rp = nb.vmath('LENGTH', nb.comb(px, nb.math('MULTIPLY', py, 0.95), 0.0))
    ri = nb.vmath('LENGTH', nb.comb(rx, ry, 0.0))
    if rough_pass:
        rr = nb.math('ADD', 0.12, nb.math('MULTIPLY', hidden, 0.5))
        coat = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, hidden), 0.9)
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, rr, coat), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    eye = pal['eye']
    gold_d = C.shade_hex(C.mix_hex(eye, '#5E7A2E', 0.35), 0.7)
    gold_l = C.mix_hex(eye, '#FFFFFF', 0.18)
    pupil = C.shade_hex(C.mix_hex('#5E7A2E', '#000000', 0.6), 0.6)
    c = nb.ramp(ri, [(0.0, C.lin(gold_l)), (0.35, C.lin(eye)), (0.78, C.lin(eye)), (0.9, C.lin(C.mix_hex(eye, gold_d, 0.5))),
                     (0.97, C.lin(gold_d)), (1.02, C.lin(C.shade_hex(gold_d, 0.7))), (2.0, C.lin(C.shade_hex(gold_d, 0.7)))])
    # fine radial streaks in the gold
    ang = nb.math('ARCTAN2', py, px)
    streak = nb.math('MULTIPLY', nb.math('ADD', nb.math('MULTIPLY', nb.math('SINE', nb.math('MULTIPLY', ang, 31.0)), 0.5), 0.5),
                     nb.math('MULTIPLY', nb.smooth(rp, 0.44, 0.56), nb.smooth(ri, 0.95, 0.8)))
    c = nb.mix(nb.math('MULTIPLY', streak, 0.16), c, nb.rgb(C.lin(C.shade_hex(eye, 0.78))))
    # a warm ring round the pupil, then the pupil
    # round 2: a bigger pupil, about 45% of the iris across (4-details panel 2)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MULTIPLY', nb.smooth(rp, 0.38, 0.44), nb.smooth(rp, 0.6, 0.5)), 0.35), c,
               nb.rgb(C.lin(C.mix_hex(eye, '#C9772E', 0.45))))
    c = nb.mix(nb.smooth(rp, 0.43, 0.4), c, nb.rgb(C.lin(pupil)))
    # the upper lid's soft shadow across the gold just under its edge
    d = nb.math('SUBTRACT', ry, edge)
    sh = nb.math('MULTIPLY', nb.smooth(d, -0.3, 0.0), 0.32)
    c = nb.mix(sh, c, nb.rgb(C.lin('#2A2410')), blend='MULTIPLY')
    # two catchlights in the open part: a big one up toward the nose side, a small one low on the other
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', rx, nb.math('MULTIPLY', side, 0.26)), nb.math('ADD', ry, 0.08), 0.0)), 0.11, 0.075)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', rx, nb.math('MULTIPLY', side, 0.28)), nb.math('ADD', ry, 0.48), 0.0)), 0.05, 0.03)
    c = nb.mix(nb.math('MULTIPLY', nb.math('MAXIMUM', big, small), nb.math('SUBTRACT', 1.0, hidden)), c, nb.rgb((1.0, 1.0, 1.0)))
    # the covered top: the lid's dark olive (never gold above a simplified lid)
    c = nb.mix(hidden, c, nb.rgb(C.lin(C.shade_hex('#7C9A3E', 0.62))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
