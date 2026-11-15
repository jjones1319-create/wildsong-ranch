"""Reefclaw's bake materials (Art 2.1 Ultra): the body's and the props' colour passes (the painted attribute plus dense
per-pixel flecks on the shell: dark red-brown specks and paler grains, Voronoi only, no value-noise lattice), and the
eye lenses (4-details panel 2: a big glossy white eyeball, a deep navy iris with a lighter inner ring, a dark pupil and
two catchlights toward the key light).
"""
from __future__ import annotations

from lib import common as C
from lib.nodes import new_mat
from monsters.breeds import reefclaw_paint as P


def _flecks(nb, base, where, pal: dict, scale: float = 1.0):
    """Dense flecks over `where` (a 0..1 socket): dark specks of about 1.3 mm and pale grains."""
    col = P.colours(pal)
    pos = nb.coords().outputs['Object']
    warp = nb.vmath('ADD', pos, nb.vmath('SCALE', nb.comb(nb.noise(pos, 30.0, 1.0, 0.5), nb.noise(nb.vmath('ADD', pos, nb.comb(2.1, 0.7, 3.3)), 30.0, 1.0, 0.5), 0.0), scale=0.003))
    dark = nb.math('MULTIPLY', nb.smooth(nb.voronoi(warp, 140.0 * scale, 'F1'), 0.2, 0.11), where)
    c = nb.mix(nb.math('MULTIPLY', dark, 0.55), base, nb.rgb(C.lin(col['shadow'])))
    pale = nb.math('MULTIPLY', nb.smooth(nb.voronoi(nb.vmath('ADD', warp, nb.comb(4.4, -1.3, 2.2)), 230.0 * scale, 'F1'), 0.16, 0.09), where)
    return nb.mix(nb.math('MULTIPLY', pale, 0.4), c, nb.rgb(C.lin(col['pale'])))


def body_material(name: str, attr: str, pal: dict, marks):
    m, nb = new_mat(name)
    base = nb.attribute(attr).outputs['Color']
    shell = nb.attribute('shell').outputs['Fac']
    pit = nb.attribute('pit').outputs['Fac']
    sock = nb.attribute('socket').outputs['Fac']
    mouth = nb.attribute('mouth').outputs['Fac']
    where = nb.math('MULTIPLY', nb.math('MULTIPLY', shell, nb.math('SUBTRACT', 1.0, pit)),
                    nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, sock), nb.math('SUBTRACT', 1.0, mouth)))
    where = nb.math('ADD', where, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, shell), 0.25))
    em = nb.new('ShaderNodeEmission')
    nb.link(_flecks(nb, base, where, pal), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def prop_material(name: str, attr: str, pal: dict, marks):
    """The limbs, stalks, cups and visors get the shell's flecks (not the coral, the barnacles or the lid balls)."""
    m, nb = new_mat(name)
    base = nb.attribute(attr).outputs['Color']
    kind = nb.attribute('kind').outputs['Fac']
    coral = nb.attribute('coral').outputs['Fac']
    lid = nb.attribute('lid').outputs['Fac']
    win = nb.attribute('win').outputs['Fac']
    shellish = nb.math('MULTIPLY', nb.smooth(kind, 1.6, 1.4), nb.math('SUBTRACT', 1.0, coral))
    shellish = nb.math('MAXIMUM', shellish, nb.math('MULTIPLY', nb.smooth(kind, 2.6, 2.9), nb.math('SUBTRACT', 1.0, nb.math('MAXIMUM', lid, win))))
    em = nb.new('ShaderNodeEmission')
    nb.link(_flecks(nb, base, shellish, pal), em.inputs['Color'])
    nb.output(em.outputs[0])
    return m


def eye_material(name: str, rough_pass: bool, pal: dict):
    m, nb = new_mat(name)
    e = nb.attribute('eyeuv').outputs['Vector']
    x, y, z = nb.sep(e)
    if rough_pass:
        em = nb.new('ShaderNodeEmission')
        nb.link(nb.comb(1.0, 0.3, 0.7), em.inputs['Color'])
        nb.output(em.outputs[0])
        return m
    eye = pal['eye']
    front = nb.smooth(z, 0.05, 0.25)
    ri = nb.vmath('LENGTH', nb.comb(x, nb.math('ADD', y, 0.15), 0.0))
    ri = nb.math('ADD', ri, nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, front), 2.0))
    sclera = '#F2EEEA'
    pupil = C.mix_hex(eye, '#0A0E18', 0.85)
    inner = C.mix_hex(eye, '#7A9CD0', 0.42) if C.srgb(eye)[2] < 0.5 else C.mix_hex(eye, '#FFFFFF', 0.35)
    ring = C.shade_hex(eye, 0.55)
    iris = nb.ramp(ri, [(0.0, C.lin(pupil)), (0.29, C.lin(pupil)), (0.33, C.lin(C.mix_hex(eye, pupil, 0.4))),
                        (0.45, C.lin(inner)), (0.55, C.lin(eye)), (0.6, C.lin(ring)), (0.63, C.lin(C.shade_hex(sclera, 0.85, cool=0.02))),
                        (0.7, C.lin(sclera)), (1.0, C.lin(sclera))])
    # a soft cool shade on the eyeball's top (under the visor) and round its edge
    shade = nb.math('MULTIPLY', nb.math('ADD', nb.smooth(y, 0.45, 0.95), nb.math('MULTIPLY', nb.smooth(z, 0.2, -0.5), 0.6)), 0.3)
    c = nb.mix(shade, iris, nb.rgb(C.lin(C.shade_hex(sclera, 0.62, cool=0.04))))
    big = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('ADD', x, 0.17), nb.math('SUBTRACT', y, 0.06), 0.0)), 0.16, 0.125)
    small = nb.smooth(nb.vmath('LENGTH', nb.comb(nb.math('SUBTRACT', x, 0.18), nb.math('ADD', y, 0.38), 0.0)), 0.07, 0.05)
    hl = nb.math('MULTIPLY', nb.math('MAXIMUM', big, small), front)
    c = nb.mix(hl, c, nb.rgb(C.lin('#FBFAF8')))
    # round 2 (review: a pale sliver showed behind the visor): the eyeball's back, in the cup and under the visor, in the
    # shell's colour
    # round 3 (review: it read half white, half shell colour in profile): a clean white sphere whose back half shades
    # softly to a warm pale tone, and only the part deep in the cup takes the shell's colour
    c = nb.mix(nb.smooth(z, 0.0, -0.45), c, nb.rgb(C.lin(C.mix_hex(sclera, P.colours(pal)['peach_warm'], 0.35))))
    c = nb.mix(nb.smooth(z, -0.62, -0.8), c, nb.rgb(C.lin(C.mix_hex(pal['body'], P.colours(pal)['shadow'], 0.35))))
    em = nb.new('ShaderNodeEmission')
    nb.link(c, em.inputs['Color'])
    nb.output(em.outputs[0])
    return m
