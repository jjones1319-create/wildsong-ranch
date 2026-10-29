"""Puddlepup (CONTENT §2.2 #1): a stubby, round puppy-like amphibian with floppy fin-shaped ears, webbed paws,
a wide happy grin and a tadpole-ish flat tail. Palette #3FB6A8 / #F3E6C4 / #F28FA8 / #24323A.

Everything here is a number. "Bigger ears" means changing one and rebuilding.
"""
from __future__ import annotations

import math

from mathutils import Matrix, Vector

from lib.face import FaceColors
from lib.mesh import Part
from lib.paint import Field

ID = 'puddlepup'
PLAN = 'quadruped'
HEIGHT_UNITS = 150          # arena units for the rest height (the runtime scales the model by this / rest height)

PALETTE = {'body': '#3FB6A8', 'belly': '#F3E6C4', 'accent': '#F28FA8', 'eye': '#24323A'}

# ---------------------------------------------------------------------------- proportions (metres; faces −Y)
P = {
    'hip': (0.0, 0.16, 0.40),
    'chest': (0.0, -0.16, 0.44),
    'head_c': (0.0, -0.36, 0.72),
    'head_r': 0.30,
    'ear_base': (0.27, -0.33, 0.80),
    'ear_dir': (0.62, 0.10, -0.77),
    'ear_len': 0.36,
    'tail_base': (0.0, 0.32, 0.40),
    'tail_dir': (0.0, 1.0, -0.12),
    'tail_len': 0.42,
    'legs': {'FL': (0.15, -0.17, 0.42), 'FR': (-0.15, -0.17, 0.42), 'BL': (0.15, 0.17, 0.40), 'BR': (-0.15, 0.17, 0.40)},
    'knee_back': 0.03,
    'ankle_z': 0.04,
    'foot_len': 0.12,
    'leg_radius': 0.11,
    'stride': 0.16,
}


def _orient(long_axis, width_axis) -> tuple[float, float, float]:
    """Euler degrees mapping a primitive's X (width), Y (long) and Z (thin) axes onto world directions."""
    d = Vector(long_axis).normalized()
    w = Vector(width_axis)
    w = (w - d * w.dot(d)).normalized()
    n = w.cross(d).normalized()
    m = Matrix((w, d, n)).transposed()  # columns = w, d, n
    e = m.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


_ear_dir = Vector(P['ear_dir']).normalized()
_ear_centre = Vector(P['ear_base']) + _ear_dir * (P['ear_len'] * 0.5)
_tail_dir = Vector(P['tail_dir']).normalized()
_tail_centre = Vector(P['tail_base']) + _tail_dir * (P['tail_len'] * 0.55)


def parts() -> list[Part]:
    L = P['legs']
    ps: list[Part] = [
        Part('head', 'sphere', loc=P['head_c'], radius=P['head_r'], scale=(1.0, 0.96, 0.95)),
        Part('cheek', 'sphere', loc=(0.21, -0.45, 0.63), radius=0.13, scale=(1.0, 1.0, 0.95), mirror=True),
        Part('muzzle', 'sphere', loc=(0.0, -0.56, 0.61), radius=0.16, scale=(1.3, 0.78, 0.66)),
        Part('brow', 'sphere', loc=(0.0, -0.46, 0.86), radius=0.14, scale=(1.6, 0.8, 0.6)),
        Part('body', 'sphere', loc=(0.0, 0.05, 0.42), radius=0.27, scale=(1.0, 1.38, 0.92)),
        Part('chest', 'sphere', loc=(0.0, -0.15, 0.45), radius=0.23, scale=(1.05, 1.0, 1.0)),
        Part('belly', 'sphere', loc=(0.0, 0.05, 0.35), radius=0.21, scale=(1.08, 1.25, 0.8)),
        Part('rump', 'sphere', loc=(0.0, 0.26, 0.40), radius=0.2, scale=(1.0, 1.0, 0.95)),
        # ears: a flattened teardrop hanging out and down from the head, plus a root that blends into the head
        Part('ear', 'fin', loc=tuple(_ear_centre), radius=P['ear_len'] / 2, scale=(0.8, 1.0, 0.28), taper=0.6,
             rot=_orient(_ear_dir, (0, 1, 0)), mirror=True),
        Part('ear_root', 'sphere', loc=(0.25, -0.33, 0.78), radius=0.1, scale=(1.0, 1.1, 1.0), mirror=True),
        # tail: a flat paddle with enough thickness to read from the side
        Part('tail', 'paddle', loc=tuple(_tail_centre), radius=P['tail_len'] / 2, scale=(0.85, 1.0, 0.42), taper=0.5,
             rot=_orient(_tail_dir, (1, 0, 0))),
        Part('tail_root', 'capsule', loc=(0.0, 0.24, 0.40), to=(0.0, 0.42, 0.385), radius=0.065),
    ]
    for leg, (x, y, hz) in L.items():
        ps.append(Part(f'leg_{leg}', 'capsule', loc=(x, y, hz), to=(x, y, 0.09), radius=0.078))
        ps.append(Part(f'paw_{leg}', 'sphere', loc=(x, y - 0.025, 0.06), radius=0.105, scale=(1.18, 1.35, 0.6)))
        for k, dx in enumerate((-0.07, 0.0, 0.07)):
            ps.append(Part(f'toe_{leg}_{k}', 'sphere', loc=(x + dx, y - 0.135, 0.05), radius=0.045, scale=(1.0, 1.1, 0.85)))
    return ps


MESH = {'voxel': 0.011, 'smooth_iters': 5, 'smooth_factor': 0.45, 'target_tris': 8200}


# ---------------------------------------------------------------------------- paint
def paint_fields(pal: dict[str, str], rainbow: bool = False) -> list[Field]:
    body, belly, accent = pal['body'], pal['belly'], pal['accent']
    darker = '#36A698' if not rainbow else '#52BBA8'
    pad = '#E58AA0'
    fields = [
        # cream belly, chest and muzzle: crisp patches that stay off the legs and the chin (the shader does the lighting)
        Field('ellipsoid', belly, centre=(0, 0.04, 0.32), radii=(0.15, 0.34, 0.14), soft=0.1, half=('z', '>', 0.25), edge=0.03),
        Field('ellipsoid', belly, centre=(0, -0.17, 0.38), radii=(0.15, 0.18, 0.14), soft=0.12),
        Field('ellipsoid', belly, centre=(0, -0.6, 0.615), radii=(0.21, 0.16, 0.085), soft=0.16),
        # paw pads: underneath only, a clean shape
        Field('ellipsoid', pad, centre=(0.15, -0.2, 0.0), radii=(0.09, 0.12, 0.04), soft=0.15, mirror=True, half=('z', '<', 0.03), edge=0.008),
        Field('ellipsoid', pad, centre=(0.15, 0.14, 0.0), radii=(0.09, 0.12, 0.04), soft=0.15, mirror=True, half=('z', '<', 0.03), edge=0.008),
        # blush
        Field('ellipsoid', accent, centre=(0.25, -0.52, 0.60), radii=(0.09, 0.075, 0.06), soft=0.55, strength=0.55, mirror=True),
        # pink inner ear membranes (toward the head) and fin ribs
        Field('ellipsoid', accent, centre=(_ear_centre.x - 0.03, _ear_centre.y, _ear_centre.z), radii=(0.07, 0.11, 0.17), soft=0.3, strength=0.9),
        Field('ellipsoid', accent, centre=(-_ear_centre.x + 0.03, _ear_centre.y, _ear_centre.z), radii=(0.07, 0.11, 0.17), soft=0.3, strength=0.9),
    ]
    if rainbow:
        colours = ['#FF6F6F', '#FFB36B', '#FFE96B', '#7BE495', '#6FB8FF', '#C28BFF']
        for k, c in enumerate(colours):
            off = _ear_dir * (k / len(colours) / 7.0)
            fields.append(Field('stripes', c, centre=tuple(_ear_centre + off), radii=(0.14, 0.14, 0.22), soft=0.3,
                                direction=tuple(_ear_dir), freq=7.0, width=0.14, strength=0.9, mirror=True))
            toff = _tail_dir * (k / len(colours) / 6.0)
            fields.append(Field('stripes', c, centre=tuple(_tail_centre + toff), radii=(0.2, 0.26, 0.1), soft=0.3,
                                direction=tuple(_tail_dir), freq=6.0, width=0.14, strength=0.75))
    # the usual look keeps plain pink fins (one colour, two tones from the shader) so the rainbow stays Songheart's
    return fields


PAINT = {'base': PALETTE['body'], 'fields': paint_fields(PALETTE), 'wobble': (3.0, 0.012)}

VARIANTS = {
    'songheart-puddlepup': {
        'palette': {'body': '#5FC7B0', 'belly': '#FFF4D6', 'accent': '#FF6FB5', 'eye': '#24323A'},
        'fields': paint_fields({'body': '#5FC7B0', 'belly': '#FFF4D6', 'accent': '#FF6FB5'}, rainbow=True),
    },
}

# ---------------------------------------------------------------------------- face
FACE = FaceColors(outline='#1E5F5A', skin='#38A79A', white='#FFF9F0', mouth='#2E2330', tongue='#F28FA8',
                  teeth='#FFF9F0', blush='#F28FA8', sweat='#9FDCF7')

# patches on the head: direction from the head centre, half-angles (radians); the aspect matches the sheet cells
FACE_PATCHES = {
    'eye.L': {'dir': (0.40, -0.82, 0.22), 'half_w': 0.37, 'half_h': 0.37 * 80 / 128, 'roll': -6.0},
    'eye.R': {'dir': (-0.40, -0.82, 0.22), 'half_w': 0.37, 'half_h': 0.37 * 80 / 128, 'roll': 6.0},
    'mouth': {'dir': (0.0, -0.86, -0.36), 'half_w': 0.58, 'half_h': 0.58 * 48 / 128, 'roll': 0.0},
}

# ---------------------------------------------------------------------------- review framing
REVIEW = {
    'centre': (0.0, -0.04, 0.50),
    'size': 1.45,
    'head_centre': (0.0, -0.42, 0.74),
    'head_size': 0.78,
    'texture_spots': [
        ('head', (0.0, -0.42, 0.74), 0.8, 0, 8),
        ('ear', (0.42, -0.30, 0.62), 0.55, 90, 0),
        ('back', (0.0, 0.05, 0.6), 1.0, 180, 60),
        ('belly', (0.0, 0.0, 0.3), 1.0, 0, -55),
        ('paw', (0.15, -0.2, 0.06), 0.36, 0, 25),
        ('tail', (0.0, 0.6, 0.37), 0.6, 135, 35),
        ('side', (0.0, -0.04, 0.5), 1.4, 90, 5),
        ('three_quarter', (0.0, -0.04, 0.5), 1.4, 40, 12),
    ],
}
