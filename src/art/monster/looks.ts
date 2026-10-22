import type { BreedId } from '../../data/types.ts'
import { outlined, type PlanKnobs, type Sockets } from './bodyPlans.ts'
import type { Palette, TextureKind } from './palettes.ts'
import type { ParticleKind } from './particles.ts'
import {
  auroraMane,
  backRidges,
  batWings,
  beard,
  bracers,
  brows,
  dinoJaw,
  chestArmor,
  chestGlow,
  chestGrate,
  constellations,
  crystalKnuckles,
  dragonWings,
  fanCrest,
  featherShield,
  fourWings,
  frostFins,
  geodeCracks,
  haloRing,
  hooves,
  iceTusk,
  impTail,
  inkFreckles,
  leafTail,
  ledgeBrows,
  littleWings,
  nubHorns,
  petalEars,
  runeLines,
  scarf,
  scholarCap,
  spadeTail,
  spectacles,
  spiralHorns,
  squareGrin,
  starTail,
  stubbyHorns,
  sweptHorns,
  tealBack,
  tentacleItems,
  thickTail,
  tinyCrest,
  trunk,
} from './parts2.ts'
import {
  antennaNubs,
  antlers,
  backQuills,
  cheeks,
  coralClaw,
  crenellatedRim,
  crestPlumes,
  curledHorns,
  curledTail,
  emberTail,
  emberTufts,
  featherCrest,
  featheryAntennae,
  finEars,
  gearWings,
  pointedEars,
  ribbonCloak,
  ribbonFins,
  stonePlates,
  tadpoleTail,
  tasselTail,
  throatSac,
  trailingWisps,
  zigzagTail,
  type FaceOptions,
  type PartPiece,
} from './parts.ts'
import { circle, ellipse, g, line, path, polygon, rect } from './svg.ts'

/**
 * The 20 breed looks (CONTENT §2.2 art briefs): which body plan knobs to use, what face to draw,
 * and the signature features that snap to the plan's sockets. Fixed colours named in a brief
 * (a brick, a glow, a tongue) stay the same whatever palette the sub breed brings.
 */

export interface LookContext {
  /** True when the monster is drawn happy (buds open, crests glow). */
  happy: boolean
}

export interface Look {
  knobs: PlanKnobs
  face: FaceOptions
  /** Moves sockets before anything is drawn (a chest creature's mouth is its lid). */
  adjust?: (s: Sockets) => void
  parts: (s: Sockets, pal: Palette, ctx: LookContext) => PartPiece[]
  /** Extra overlay when the monster is happy. */
  happyExtra?: 'rainbow'
  /** A class on the whole figure (Zipwisp jitters). */
  figureClass?: string
  /** Custom mouth drawing instead of the standard styles. */
  mouthSvg?: (s: Sockets, pal: Palette) => string
  /** GAME_DESIGN §22 growth forms: the look from Prime onward. */
  grown?: Look
}

/** Per-breed polish (§22): a subtle texture pattern and a signature particle effect, or none. */
export const POLISH: Record<BreedId, { texture: TextureKind | null; particles: ParticleKind | null }> = {
  puddlepup: { texture: null, particles: 'bubble' },
  tumblefox: { texture: 'fur', particles: 'leaf' },
  cobblemaw: { texture: 'stone', particles: 'puff' },
  moatshell: { texture: 'stone', particles: 'puff' },
  wishlume: { texture: null, particles: 'mote' },
  quillion: { texture: 'fur', particles: null },
  cinderlynx: { texture: 'fur', particles: 'ember' },
  bloatoad: { texture: null, particles: 'bubble' },
  coilfang: { texture: 'scales', particles: null },
  nimbusheep: { texture: null, particles: 'rain' },
  galeheron: { texture: 'feathers', particles: 'feather' },
  nibblegrub: { texture: null, particles: null },
  velvesper: { texture: null, particles: 'mote' },
  ashwraith: { texture: null, particles: 'ash' },
  zipwisp: { texture: null, particles: 'spark' },
  mirrorkin: { texture: null, particles: 'glint' },
  gearhoot: { texture: null, particles: 'steam' },
  reefclaw: { texture: null, particles: 'bubble' },
  lootlid: { texture: null, particles: 'coin' },
  aurelwyrm: { texture: 'scales', particles: 'mote' },
  hearthwing: { texture: 'scales', particles: 'ember' },
  grumblestone: { texture: 'stone', particles: 'glint' },
  pluckrex: { texture: 'scales', particles: null },
  paladove: { texture: 'feathers', particles: 'mote' },
  starhowl: { texture: 'fur', particles: 'twinkle' },
  petalphant: { texture: null, particles: 'petal' },
  scrollopus: { texture: null, particles: 'bubble' },
  gloomgrin: { texture: 'stone', particles: 'puff' },
  rammerjack: { texture: 'fur', particles: null },
  frostlance: { texture: null, particles: 'flake' },
}

const stroke = (pal: Palette, width: number, color = pal.outline) => ({ fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })

export const LOOKS: Record<BreedId, Look> = {
  puddlepup: {
    knobs: {},
    face: { eyes: 'round', mouth: 'grin' },
    parts: (s, pal) => [
      finEars(s, pal.accent, pal.belly, pal),
      tadpoleTail(s, pal.body, pal),
      {
        over: g({}, [148, 168].flatMap((x) => [line(x - 5, 226, x - 5, 219, stroke(pal, 2)), line(x, 227, x, 219, stroke(pal, 2)), line(x + 5, 226, x + 5, 219, stroke(pal, 2))])),
      },
    ],
  },
  tumblefox: {
    knobs: { bodyRx: 50, bodyRy: 34, headR: 34, snout: true },
    face: { eyes: 'round', mouth: 'smile' },
    parts: (s, pal) => [
      curledTail(s, pal.body, pal.belly, pal),
      pointedEars(s, pal.body, pal.belly, pal),
      { over: ellipse(s.head.x, s.head.y - 6, s.head.r * 0.95, 11, { fill: pal.accent, opacity: 0.9 }) },
      { over: g({}, [96, 114, 148, 168].map((x) => rect(x - 9, 214, 18, 16, 7, { fill: pal.accent }))) },
      { over: circle(s.head.x + s.head.r * 0.9, s.head.y + s.head.r * 0.3, 4, { fill: pal.outline }) },
    ],
  },
  cobblemaw: {
    knobs: { bodyRx: 66, bodyRy: 46, headR: 42 },
    face: { eyes: 'beady', mouth: 'none', eyeScale: 0.8 },
    parts: (s, pal) => [
      stonePlates({ ...s, back: { x: 88, y: 134 } }, pal.belly, pal.accent, pal),
      { over: path(`M${s.eyeL.x - 14} ${s.eyeL.y - 12} L${s.eyeR.x + 14} ${s.eyeR.y - 12}`, stroke(pal, 6)) },
      {
        front: g({}, [
          rect(s.head.x - 26, s.head.y + 10, 56, 22, 10, { fill: pal.outline }),
          rect(s.head.x - 20, s.head.y + 12, 44, 8, 4, { fill: pal.shade }),
          polygon(
            [
              [s.head.x - 14, s.head.y + 30],
              [s.head.x - 8, s.head.y + 16],
              [s.head.x - 2, s.head.y + 30],
            ],
            { fill: '#fff', ...outlined(pal, { 'stroke-width': 2 }) },
          ),
          polygon(
            [
              [s.head.x + 10, s.head.y + 30],
              [s.head.x + 16, s.head.y + 16],
              [s.head.x + 22, s.head.y + 30],
            ],
            { fill: '#fff', ...outlined(pal, { 'stroke-width': 2 }) },
          ),
        ]),
      },
    ],
  },
  moatshell: {
    knobs: {},
    face: { eyes: 'lidded', mouth: 'smile' },
    parts: (s, pal) => [
      crenellatedRim({ ...s, back: { x: 128, y: 126 } }, pal.body, pal),
      {
        over: g({}, [
          rect(96, 150, 6, 18, 2, { fill: pal.outline }),
          rect(125, 142, 6, 18, 2, { fill: pal.outline }),
          rect(154, 150, 6, 18, 2, { fill: pal.outline }),
          line(84, 176, 172, 176, stroke(pal, 2.5, '#9A5B3C')),
          line(108, 176, 108, 190, stroke(pal, 2.5, '#9A5B3C')),
          line(148, 176, 148, 190, stroke(pal, 2.5, '#9A5B3C')),
          line(128, 114, 128, 74, stroke(pal, 5)),
          polygon(
            [
              [129, 74],
              [162, 84],
              [129, 96],
            ],
            { fill: pal.accent, ...outlined(pal) },
          ),
        ]),
      },
    ],
  },
  wishlume: {
    knobs: { lantern: true, bodyRx: 40, bodyRy: 50 },
    face: { eyes: 'painted', mouth: 'smile' },
    parts: (s, pal) => {
      const b = s.body
      return [
        {
          over: g({}, [
            circle(b.x, b.y + 8, 28, { fill: '#FFB85C', opacity: 0.3 }),
            circle(b.x, b.y + 8, 17, { fill: '#FFB85C', opacity: 0.9 }),
            path(`M${b.x} ${b.y + 18} C${b.x - 12} ${b.y + 4} ${b.x - 4} ${b.y - 6} ${b.x} ${b.y + 2} C${b.x + 4} ${b.y - 6} ${b.x + 12} ${b.y + 4} ${b.x} ${b.y + 18} Z`, { fill: '#fff3c4', opacity: 0.9 }),
            ...[-24, -8, 8, 24].map((dx) => line(b.x + dx, b.y - b.ry + 8, b.x + dx, b.y + b.ry - 8, { stroke: pal.accent, 'stroke-width': 3, opacity: 0.7, 'stroke-linecap': 'round' })),
            rect(b.x - 14, b.y - b.ry - 8, 28, 10, 3, { fill: pal.accent, ...outlined(pal) }),
          ]),
          front: g({}, [rect(b.x - b.rx - 14, b.y - 4, 22, 12, 6, { fill: pal.body, ...outlined(pal) }), rect(b.x + b.rx - 8, b.y - 4, 22, 12, 6, { fill: pal.body, ...outlined(pal) })]),
        },
        tasselTail(s, pal.accent, pal),
      ]
    },
  },
  quillion: {
    knobs: { bodyRx: 32, bodyRy: 40, headR: 30 },
    face: { eyes: 'round', mouth: 'smile' },
    parts: (s, pal) => {
      const f = s.front
      return [
        { back: path(`M${s.body.x - 20} ${s.body.y - 34} C${s.body.x - 60} ${s.body.y - 10} ${s.body.x - 56} ${s.body.y + 44} ${s.body.x - 30} ${s.body.y + 48} L${s.body.x + 6} ${s.body.y + 10} Z`, { fill: pal.accent, ...outlined(pal) }) },
        backQuills({ ...s, back: { x: s.head.x - 6, y: s.head.y - s.head.r + 8 } }, pal.shade, pal),
        backQuills({ ...s, back: { x: s.body.x - 28, y: s.body.y - 20 } }, pal.shade, pal),
        {
          front: g({}, [
            polygon(
              [
                [f.x - 14, f.y + 10],
                [f.x + 56, f.y - 14],
                [f.x - 8, f.y - 2],
              ],
              { fill: '#C9D3DD', ...outlined(pal) },
            ),
            circle(s.head.x + s.head.r * 0.9, s.head.y + 6, 4, { fill: pal.outline }),
          ]),
        },
      ]
    },
  },
  cinderlynx: {
    knobs: { bodyRx: 54, bodyRy: 32, headR: 32, snout: true },
    face: { eyes: 'round', mouth: 'smile' },
    parts: (s, pal) => [
      pointedEars(s, pal.body, pal.belly, pal),
      emberTufts(s, pal.accent, pal),
      emberTail(s, pal.body, pal.accent, pal),
      {
        over: g({}, [84, 100, 116, 132].map((x, i) => polygon(
          [
            [x, 136 - i * 2],
            [x + 6, 142 - i * 2],
            [x, 148 - i * 2],
            [x - 6, 142 - i * 2],
          ],
          { fill: pal.accent },
        ))),
        front: g({}, [path('M150 230 c-6 -6 -2 -12 -8 -16', { ...stroke(pal, 4, '#9a9a9a'), opacity: 0.6 }), path('M170 230 c6 -6 2 -12 8 -16', { ...stroke(pal, 4, '#9a9a9a'), opacity: 0.6 })]),
      },
    ],
  },
  bloatoad: {
    knobs: {},
    face: { eyes: 'lidded', mouth: 'smile', eyeScale: 1.1 },
    parts: (s, pal) => [
      throatSac(s, pal.belly, pal),
      { over: g({}, [[92, 120], [164, 116], [120, 110], [80, 150], [176, 148]].map(([x, y]) => circle(x!, y!, 5, { fill: pal.shade, opacity: 0.8 }))) },
      { over: g({}, [-16, 0, 16].map((dx) => circle(s.crown.x + dx, s.crown.y + 4 - (dx === 0 ? 4 : 0), 7, { fill: pal.body, ...outlined(pal) }))) },
    ],
  },
  coilfang: {
    knobs: {},
    face: { eyes: 'round', mouth: 'fangs' },
    parts: (s, pal) => [
      featherCrest(s, pal.accent, pal),
      {
        over: g({}, [[80, 172], [102, 160], [128, 176], [150, 200], [176, 198], [192, 164]].map(([x, y]) => polygon(
          [
            [x!, y! - 7],
            [x! + 6, y!],
            [x!, y! + 7],
            [x! - 6, y!],
          ],
          { fill: pal.outline, opacity: 0.45 },
        ))),
      },
    ],
  },
  nimbusheep: {
    knobs: { cloud: true, headR: 30 },
    face: { eyes: 'round', mouth: 'smile' },
    happyExtra: 'rainbow',
    parts: (s, pal) => [
      { over: circle(s.head.x, s.head.y, s.head.r * 0.85, { fill: pal.belly, ...outlined(pal) }) },
      curledHorns(s, '#F1E6CC', pal),
      { front: g({}, [[96, 212], [124, 218], [150, 212]].map(([x, y]) => path(`M${x} ${y} c-3 5 -3 8 0 10 c3 -2 3 -5 0 -10 Z`, { fill: '#8FB8F2', opacity: 0.75 }))) },
    ],
  },
  galeheron: {
    knobs: {},
    face: { eyes: 'round', mouth: 'beak' },
    parts: (s, pal) => [
      crestPlumes(s, pal.accent, pal),
      { over: g({}, [path('M94 152 c10 -8 22 -8 30 0', { ...stroke(pal, 3, pal.accent), opacity: 0.8 }), path('M98 164 c8 -6 18 -6 26 0', { ...stroke(pal, 3, pal.accent), opacity: 0.8 })]) },
    ],
  },
  nibblegrub: {
    knobs: {},
    face: { eyes: 'round', mouth: 'chew' },
    parts: (s, pal) => [antennaNubs(s, pal.accent, pal), { over: cheeks(s, '#F29C8F', 9) }],
  },
  velvesper: {
    knobs: { slim: true },
    face: { eyes: 'round', mouth: 'smile' },
    parts: (s, pal) => {
      const b = s.back
      const wing = (sx: number, sy: number, mirror: number) => {
        const d = `M${b.x} ${b.y + 10} C${b.x - 70 * sx} ${b.y - 90 * sy} ${b.x - 10 * sx} ${b.y - 120 * sy} ${b.x + 36 * sx} ${b.y - 50 * sy} C${b.x + 30 * sx} ${b.y - 20 * sy} ${b.x + 10 * sx} ${b.y - 4} ${b.x} ${b.y + 10} Z`
        const eyespot = { x: b.x - 14 * sx * mirror, y: b.y - 62 * sy }
        return g({}, [
          path(d, { fill: pal.body, ...outlined(pal) }),
          path(`M${b.x - 30 * sx} ${b.y - 70 * sy} a14 14 0 1 0 10 -16 a11 11 0 1 1 -10 16 Z`, { fill: pal.belly, opacity: 0.9 }),
          circle(eyespot.x, eyespot.y, 10, { fill: pal.accent, ...outlined(pal, { 'stroke-width': 2 }) }),
          circle(eyespot.x, eyespot.y, 5, { fill: '#F7E7B5' }),
        ])
      }
      return [{ back: g({}, [wing(1, 1, 1), wing(0.65, 0.55, 1)]) }, featheryAntennae(s, pal.accent, pal)]
    },
  },
  ashwraith: {
    knobs: { shroud: true },
    face: { eyes: 'ember', mouth: 'none', eyeScale: 1.2 },
    parts: (s, pal) => [
      trailingWisps({ ...s, tail: { x: s.body.x - 10, y: s.body.y + s.body.ry - 8 } }, pal.belly, pal),
      { front: g({}, [circle(s.body.x - s.body.rx + 6, s.body.y + 18, 8, { fill: pal.belly, ...outlined(pal) }), circle(s.body.x + s.body.rx - 6, s.body.y + 18, 8, { fill: pal.belly, ...outlined(pal) })]) },
    ],
  },
  zipwisp: {
    knobs: { small: true },
    face: { eyes: 'dot', mouth: 'smile', eyeScale: 1.2 },
    figureClass: 'ws-mon__jitter',
    parts: (s, pal) => {
      const b = s.body
      const spikes: [number, number][] = []
      for (let i = 0; i < 20; i++) {
        const a = (i * Math.PI) / 10
        const r = i % 2 === 0 ? b.rx + 10 : b.rx - 4
        spikes.push([b.x + Math.cos(a) * r, b.y + Math.sin(a) * r])
      }
      const wing = (dir: number) =>
        polygon(
          [
            [b.x + dir * (b.rx - 6), b.y - 6],
            [b.x + dir * (b.rx + 30), b.y - 30],
            [b.x + dir * (b.rx + 16), b.y - 4],
            [b.x + dir * (b.rx + 34), b.y + 12],
            [b.x + dir * (b.rx - 4), b.y + 10],
          ],
          { fill: pal.accent, ...outlined(pal) },
        )
      return [{ back: g({}, [wing(-1), wing(1), polygon(spikes, { fill: pal.body, ...outlined(pal) })]) }, zigzagTail(s, pal.accent, pal)]
    },
  },
  mirrorkin: {
    knobs: { hollow: true },
    face: { eyes: 'round', mouth: 'smile', rim: '#C9A04A' },
    parts: (s, pal) => {
      const b = s.body
      const frame = '#C9A04A'
      return [
        ribbonCloak(s, pal.accent, pal),
        {
          over: g({}, [
            rect(b.x - 8, b.y + b.ry - 10, 16, 44, 6, { fill: frame, ...outlined(pal) }),
            circle(b.x, b.y + b.ry + 36, 9, { fill: frame, ...outlined(pal) }),
            ellipse(b.x, b.y, b.rx, b.ry, { fill: frame, ...outlined(pal) }),
            ellipse(b.x, b.y, b.rx - 10, b.ry - 10, { fill: pal.belly, ...outlined(pal, { 'stroke-width': 2 }) }),
            ellipse(b.x - 14, b.y - 24, 8, 14, { fill: '#fff', opacity: 0.5 }),
            ...[0, 1, 2, 3].map((i) => circle(b.x + Math.cos((i * Math.PI) / 2 + Math.PI / 4) * (b.rx - 4), b.y + Math.sin((i * Math.PI) / 2 + Math.PI / 4) * (b.ry - 4), 5, { fill: pal.light, ...outlined(pal, { 'stroke-width': 1.5 }) })),
          ]),
          front: g({}, [circle(b.x - b.rx - 16, b.y + 20, 10, { fill: '#fff', ...outlined(pal) }), circle(b.x + b.rx + 16, b.y + 20, 10, { fill: '#fff', ...outlined(pal) })]),
        },
      ]
    },
  },
  gearhoot: {
    knobs: { roundHead: true },
    face: { eyes: 'round', mouth: 'none', rim: '#B86B3C' },
    parts: (s, pal) => [
      gearWings(s, pal.accent, pal),
      {
        back: g({}, [line(s.back.x + 4, s.back.y, s.back.x - 26, s.back.y, stroke(pal, 8)), line(s.back.x + 4, s.back.y, s.back.x - 26, s.back.y, stroke(pal, 4, '#B86B3C')), rect(s.back.x - 40, s.back.y - 12, 16, 24, 4, { fill: '#B86B3C', ...outlined(pal) })]),
        over: g({}, [
          polygon(
            [
              [s.earL.x - 6, s.earL.y + 12],
              [s.earL.x - 2, s.earL.y - 10],
              [s.earL.x + 12, s.earL.y + 8],
            ],
            { fill: pal.body, ...outlined(pal) },
          ),
          polygon(
            [
              [s.earR.x + 6, s.earR.y + 12],
              [s.earR.x + 2, s.earR.y - 10],
              [s.earR.x - 12, s.earR.y + 8],
            ],
            { fill: pal.body, ...outlined(pal) },
          ),
          line(s.body.x - 30, s.body.y - 26, s.body.x + 30, s.body.y - 26, { ...stroke(pal, 2), opacity: 0.4 }),
          polygon(
            [
              [s.mouth.x - 6, s.mouth.y - 4],
              [s.mouth.x + 6, s.mouth.y - 4],
              [s.mouth.x, s.mouth.y + 8],
            ],
            { fill: pal.accent, ...outlined(pal, { 'stroke-width': 2 }) },
          ),
        ]),
        front: circle(s.eyeR.x, s.eyeR.y, s.eyeR_ * 1.9, { fill: 'none', stroke: '#B86B3C', 'stroke-width': 4 }) + line(s.eyeR.x + s.eyeR_ * 1.9, s.eyeR.y, s.eyeR.x + s.eyeR_ * 1.9 + 10, s.eyeR.y + 14, { stroke: '#B86B3C', 'stroke-width': 3 }),
      },
    ],
  },
  reefclaw: {
    knobs: { crab: true, shellColor: '#B85B4E', skinFromBody: true },
    face: { eyes: 'round', mouth: 'flat', eyeScale: 0.9 },
    parts: (s, pal) => [
      coralClaw(s, pal.body, pal),
      {
        over: g({}, [
          line(s.eyeL.x, s.eyeL.y + 18, s.eyeL.x, s.eyeL.y, stroke(pal, 7)),
          line(s.eyeR.x, s.eyeR.y + 18, s.eyeR.x, s.eyeR.y, stroke(pal, 7)),
          line(s.eyeL.x, s.eyeL.y + 18, s.eyeL.x, s.eyeL.y, stroke(pal, 3, pal.body)),
          line(s.eyeR.x, s.eyeR.y + 18, s.eyeR.x, s.eyeR.y, stroke(pal, 3, pal.body)),
          ...[[92, 132], [106, 124], [120, 130]].map(([x, y]) => circle(x!, y!, 6, { fill: pal.accent, ...outlined(pal, { 'stroke-width': 2 }) })),
        ]),
        front: g({}, [line(s.eyeL.x - 12, s.eyeL.y - 12, s.eyeR.x + 12, s.eyeR.y - 12, stroke(pal, 5)), path(`M${s.body.x - 70} ${s.body.y + 10} l-18 -10 m18 10 l-16 10`, { ...stroke(pal, 12) }), path(`M${s.body.x - 70} ${s.body.y + 10} l-18 -10 m18 10 l-16 10`, { ...stroke(pal, 6, pal.body) })]),
      },
    ],
  },
  lootlid: {
    knobs: { noHead: true },
    face: { eyes: 'round', mouth: 'none' },
    adjust: (s) => {
      s.eyeL = { x: 112, y: 104 }
      s.eyeR = { x: 144, y: 104 }
      s.eyeR_ = 7
      s.mouth = { x: 128, y: 130 }
      s.head = { x: 128, y: 108, r: 40 }
      s.crown = { x: 128, y: 82 }
      s.cheekL = { x: 98, y: 114 }
      s.cheekR = { x: 158, y: 114 }
    },
    parts: (s, pal) => {
      const b = s.body
      const lid = `M${b.x - b.rx} ${b.y - b.ry + 2} L${b.x - b.rx + 6} ${b.y - b.ry - 36} Q${b.x} ${b.y - b.ry - 56} ${b.x + b.rx - 2} ${b.y - b.ry - 34} L${b.x + b.rx} ${b.y - b.ry + 2} Z`
      return [
        {
          over: g({}, [
            rect(b.x - b.rx, b.y - 10, b.rx * 2, 10, 2, { fill: pal.accent, ...outlined(pal, { 'stroke-width': 2 }) }),
            rect(b.x - b.rx, b.y + 22, b.rx * 2, 8, 2, { fill: pal.accent, ...outlined(pal, { 'stroke-width': 2 }) }),
            rect(b.x - b.rx + 4, b.y - b.ry - 2, b.rx * 2 - 8, 14, 4, { fill: pal.outline }),
            ...[-24, -8, 8, 24].map((dx) => circle(b.x + dx, b.y - b.ry + 4, 5, { fill: pal.accent, ...outlined(pal, { 'stroke-width': 1.5 }) })),
            path(lid, { fill: pal.body, ...outlined(pal) }),
            rect(b.x - b.rx + 6, b.y - b.ry - 50, b.rx * 2 - 12, 7, 2, { fill: pal.accent, opacity: 0.9 }),
            circle(b.x, b.y - b.ry - 8, 5, { fill: pal.outline }),
            rect(b.x - 2.5, b.y - b.ry - 8, 5, 8, 1, { fill: pal.outline }),
            ...[-18, 0, 18].map((dx) => circle(b.x + dx, b.y - b.ry + 6, 5, { fill: '#F2C94C', ...outlined(pal, { 'stroke-width': 1.5 }) })),
            path(`M${b.x - 10} ${b.y - b.ry + 10} C${b.x - 14} ${b.y - 6} ${b.x + 6} ${b.y - 2} ${b.x + 2} ${b.y + 14} C${b.x + 10} ${b.y + 6} ${b.x + 14} ${b.y - 8} ${b.x + 8} ${b.y - b.ry + 10} Z`, { fill: '#E86A7C', ...outlined(pal, { 'stroke-width': 2 }) }),
          ]),
        },
      ]
    },
  },
  aurelwyrm: {
    knobs: { lifted: true },
    face: { eyes: 'round', mouth: 'smile' },
    parts: (s, pal) => [
      ribbonFins(s, pal.accent, pal),
      ribbonFins({ ...s, back: { x: 150, y: 150 } }, pal.accent, pal),
      antlers(s, '#6B2D0F', pal),
      { front: g({}, [path(`M${s.mouth.x + 10} ${s.mouth.y - 2} c14 2 20 14 30 10`, stroke(pal, 2.5)), path(`M${s.mouth.x - 14} ${s.mouth.y + 2} c-14 2 -18 14 -28 10`, stroke(pal, 2.5))]) },
    ],
  },
  // Breeds 21–30 (docs/NEW_MONSTERS.md §3).
  hearthwing: {
    knobs: { bodyRx: 54, bodyRy: 40, headR: 36, snout: true },
    face: { eyes: 'round', mouth: 'smile' },
    parts: (s, pal) => [littleWings(s, pal.body, pal), nubHorns(s, '#B87333', pal), chestGlow(s, pal.accent), tadpoleTail(s, pal.body, pal)],
    grown: {
      knobs: { neck: true, bodyRx: 62, bodyRy: 44, headR: 30, snoutLong: true },
      face: { eyes: 'round', mouth: 'smile' },
      parts: (s, pal) => [dragonWings(s, pal.body, pal.accent, pal), sweptHorns(s, '#B87333', pal), chestGrate(s, pal.accent, pal), spadeTail(s, pal.body, pal.accent, pal)],
    },
  },
  grumblestone: {
    knobs: { hulk: true },
    face: { eyes: 'beady', mouth: 'frown', eyeScale: 0.9 },
    parts: (s, pal) => [geodeCracks(s, pal.accent, pal), ledgeBrows(s, pal.belly, pal), crystalKnuckles(pal.accent, pal)],
  },
  pluckrex: {
    knobs: { dino: true },
    face: { eyes: 'round', mouth: 'none' },
    mouthSvg: (s, pal) => dinoJaw(s, pal),
    parts: (s, pal, ctx) => [fanCrest(s, pal.accent, pal, ctx.happy, 1.15), backRidges(s, pal.accent, pal), thickTail(s, pal.body, pal)],
    grown: {
      knobs: { grownDino: true },
      face: { eyes: 'round', mouth: 'none' },
      mouthSvg: (s, pal) => dinoJaw(s, pal),
      parts: (s, pal, ctx) => [fanCrest(s, pal.accent, pal, ctx.happy, 1.6), backRidges(s, pal.accent, pal), thickTail(s, pal.body, pal), bracers(s, '#8E94A4', pal)],
    },
  },
  paladove: {
    knobs: { chick: true },
    face: { eyes: 'round', mouth: 'beak', eyeScale: 1.1 },
    parts: (s, pal) => [tinyCrest(s, pal.accent, pal), haloRing(s, pal.accent), { back: g({}, [ellipse(s.body.x - s.body.rx + 4, s.body.y - 6, 14, 22, { fill: pal.paint(pal.body), ...outlined(pal) }), ellipse(s.body.x + s.body.rx - 4, s.body.y - 6, 14, 22, { fill: pal.paint(pal.body), ...outlined(pal) })]) }],
    grown: {
      knobs: { stout: true },
      face: { eyes: 'round', mouth: 'beak' },
      parts: (s, pal) => [fourWings(s, pal.body, pal.accent, pal), haloRing(s, pal.accent), chestArmor(s, pal.accent, pal), featherShield(s, pal.accent, pal), crestPlumes(s, pal.accent, pal)],
    },
  },
  starhowl: {
    knobs: { bodyRx: 56, bodyRy: 34, headR: 32, snoutLong: true },
    face: { eyes: 'ember', mouth: 'smile', eyeScale: 0.95 },
    parts: (s, pal) => [auroraMane(s, pal.accent, '#F49AC1', pal), pointedEars(s, pal.body, pal.belly, pal), constellations(s, pal), starTail(s, pal.body, '#FFF2B0', pal)],
  },
  petalphant: {
    knobs: { bodyRx: 60, bodyRy: 44, headR: 38 },
    face: { eyes: 'round', mouth: 'none' },
    parts: (s, pal, ctx) => [petalEars(s, pal.accent, pal), trunk(s, pal.body, pal.accent, ctx.happy, pal), leafTail(s, '#7FAF5A', pal)],
  },
  scrollopus: {
    knobs: { tentacles: true },
    face: { eyes: 'round', mouth: 'smile' },
    parts: (s, pal) => [scholarCap(s, '#3A3A55', '#F2C94C', pal), spectacles(s, pal.accent, pal), tentacleItems(s, pal), inkFreckles(s, pal.accent)],
  },
  gloomgrin: {
    knobs: { squat: true },
    face: { eyes: 'round', mouth: 'none' },
    mouthSvg: (s, pal) => squareGrin(s, pal),
    parts: (s, pal) => [batWings(s, pal.body, pal), stubbyHorns(s, pal.belly, pal), runeLines(s, pal.accent), impTail(s, pal.body, pal)],
  },
  rammerjack: {
    knobs: { bodyRx: 58, bodyRy: 40, headR: 34, snoutLong: true },
    face: { eyes: 'round', mouth: 'flat' },
    parts: (s, pal) => [spiralHorns(s, pal.accent, '#C9A66B', pal), beard(s, pal.belly, pal), scarf(s, '#D1495B', pal), hooves([96, 114, 148, 168], pal.accent, pal), brows(s, pal)],
  },
  frostlance: {
    knobs: { horizontal: true },
    face: { eyes: 'round', mouth: 'smile', eyeScale: 0.9 },
    parts: (s, pal) => [frostFins(s, pal.belly, pal), tealBack(s, pal.accent), iceTusk(s, '#BDE8F5', pal)],
  },
}
