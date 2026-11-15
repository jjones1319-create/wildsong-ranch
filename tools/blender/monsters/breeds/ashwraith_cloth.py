"""Ashwraith's cloth pieces as props (ashwraith_ultra.build_props): the long cape and the four front panels
(ashwraith_drape.py), each a thick sheet with its torn hem and real holes cut through it (ashwraith_mesh.Kit.ragged),
with its own unwrap on the sheet's grid. Attributes: part (CAPE or PANEL), pt (0 at the top .. 1 at the hem), pa (0..1 across),
side (+1 outer, -1 inner, 0 the cut edges), pr (the piece: 0 the cape, 1..4 the panels).
"""
from __future__ import annotations

import numpy as np

from lib.surface import smooth
from monsters.breeds import ashwraith_drape as D
from monsters.breeds import ashwraith_mesh as AM


def axis_of(q: np.ndarray) -> np.ndarray:
    """The shroud's own axis at each point's height (the cloth's outside faces away from it)."""
    return np.stack([np.zeros(len(q)), D.sh_abyc(q[:, 2])[2], q[:, 2]], axis=1)

CAPE, PANEL = 1, 10
PANEL_ORDER = ('innerL', 'innerR', 'outerL', 'outerR')


def cape_object(name: str, high: bool) -> 'bpy.types.Object':
    nu, nv = (300, 130) if high else (72, 28)
    u = np.linspace(-1.0, 1.0, nu + 1)
    v = np.linspace(0.0, 1.0, nv + 1)
    UU, VV = np.meshgrid(u, v)
    G = D.cape_point(UU, VV)
    holes = [(D.cape_point(np.array([hu]), np.array([hv]))[0], r) for hu, hv, r in D.CAPE_HOLES]
    kit = AM.Kit()
    thick = D.CAPE_T * (1.0 + 0.3 * smooth(0.85, 1.0, VV))
    kit.ragged(G, thick, CAPE, holes=holes, pr=0.0, texel_k=0.85, inside=axis_of)
    ob = kit.object(name)
    ob['prop'] = 'cape'
    return ob


def mid_object(name: str, high: bool) -> 'bpy.types.Object':
    """Round 3: the middle cape layer at the back and sides."""
    nu, nv = (240, 80) if high else (56, 16)
    u = np.linspace(-1.0, 1.0, nu + 1)
    v = np.linspace(0.0, 1.0, nv + 1)
    UU, VV = np.meshgrid(u, v)
    G = D.mid_point(UU, VV)
    holes = [(D.mid_point(np.array([hu]), np.array([hv]))[0], r) for hu, hv, r in D.MID_HOLES]
    kit = AM.Kit()
    kit.ragged(G, D.CAPE_T, CAPE, holes=holes, pr=0.5, texel_k=0.85, inside=axis_of)
    ob = kit.object(name)
    ob['prop'] = 'midcape'
    return ob


def panels_object(name: str, high: bool) -> 'bpy.types.Object':
    kit = AM.Kit()
    for k, nm in enumerate(PANEL_ORDER):
        nu, nv = (84, 130) if high else (20, 26)
        u = np.linspace(-1.0, 1.0, nu + 1)
        # rows: denser round the gather, where the cloth bunches into the hand
        v = np.concatenate([np.linspace(0.0, D.PANEL_VG, int(nv * 0.3) + 1)[:-1], np.linspace(D.PANEL_VG, 1.0, nv - int(nv * 0.3) + 1)])
        UU, VV = np.meshgrid(u, v)
        G = D.panel_point(nm, UU, VV)
        holes = [(D.panel_point(nm, np.array([hu]), np.array([hv]))[0], r) for hu, hv, r in D.PANEL_HOLES.get(nm, [])]
        kit.ragged(G, D.PANEL_T, PANEL, holes=holes, pr=float(k + 1), texel_k=0.95, inside=axis_of)
    ob = kit.object(name)
    ob['prop'] = 'panels'
    return ob
