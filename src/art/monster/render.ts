import { expressionCues } from '../../core/aging.ts'
import { cyrb53 } from '../../core/hash.ts'
import { sizePct, stageOf, type Monster } from '../../core/monster.ts'
import { BREED_BY_ID } from '../../data/breeds.ts'
import { STAGES } from '../../data/tuning.ts'
import type { BreedId } from '../../data/types.ts'
import { ACCENTS } from './accents.ts'
import { drawPlan, groundShadow, type Sockets } from './bodyPlans.ts'
import { buildDefs } from './defs.ts'
import { expressionFromCues, faceFor, type Expression } from './expressions.ts'
import { LOOKS, POLISH, type Look } from './looks.ts'
import { buildPalette } from './palettes.ts'
import { drawParticles } from './particles.ts'
import { cheeks, drawEyes, drawMouth, rainbow, sickTint, sparkles, sweatDrop, type PartPiece } from './parts.ts'
import { el, g } from './svg.ts'

/**
 * GAME_DESIGN §22: the paper-doll renderer. A pure function from a spec to an SVG string, so it
 * runs in tests, workers and the page alike. Layers, back to front: defs · ground shadow · back parts
 * (tails, wings, cloaks) · body · over parts (markings, plates) · face · front parts · particles · overlays.
 */

export type Form = 'young' | 'grown'

export interface RenderSpec {
  mainBreed: BreedId
  /** Whose palette the body wears (the sub by default, §14.3). */
  paletteBreed: BreedId
  /** Whose accent part is attached (the sub when not pure). */
  accentBreed: BreedId | null
  eyeColor: string
  /** Life stage 1–10: sets the size (§5.3), the "visibly old" look from stage 8, and the growth form. */
  stage: number
  expression: Expression
  sparkle: boolean
  mischief: boolean
  animate: boolean
  /** Signature particles (off for thumbnails and in lite mode). */
  particles: boolean
  /** Lite mode: no particles and no secondary motion (weaker phones). */
  lite: boolean
}

export interface RenderOptions {
  /** CSS pixel size of the square image (the viewBox is always 256). */
  size?: number
  /** Accessible label; the breed name by default. */
  label?: string
  /** Extra class names on the root svg. */
  class?: string
  /** Face left instead of right (the opponent in a battle). */
  mirror?: boolean
}

export interface SpecOverrides {
  expression?: Expression
  sparkle?: boolean
  mischief?: boolean
  animate?: boolean
  stage?: number
  particles?: boolean
  lite?: boolean
}

/** §22 growth forms: young for stages 1–4, grown from Prime, for the breeds that have a grown look. */
export function formForStage(breed: BreedId, stage: number): Form {
  return LOOKS[breed].grown && stage >= STAGES.prime[0]! ? 'grown' : 'young'
}

export function hasGrownForm(breed: BreedId): boolean {
  return LOOKS[breed].grown !== undefined
}

export function specFromMonster(m: Monster, o: SpecOverrides = {}): RenderSpec {
  const cues = expressionFromCues(expressionCues(m))
  const paletteBreed = BREED_BY_ID[m.appearance.paletteBreed] ? m.appearance.paletteBreed : m.subBreed
  const animate = o.animate ?? true
  return {
    mainBreed: m.mainBreed,
    paletteBreed,
    accentBreed: m.mainBreed === m.subBreed ? null : m.subBreed,
    eyeColor: BREED_BY_ID[m.mainBreed].art.palette.eye,
    stage: o.stage ?? stageOf(m),
    expression: o.expression ?? cues.expression,
    sparkle: o.sparkle ?? cues.sparkle,
    mischief: o.mischief ?? cues.mischief,
    animate,
    particles: (o.particles ?? true) && animate,
    lite: o.lite ?? false,
  }
}

/** A quick spec for a breed on its own (pickers, galleries). */
export function specForBreed(breed: BreedId, o: SpecOverrides & { sub?: BreedId } = {}): RenderSpec {
  const sub = o.sub ?? breed
  const animate = o.animate ?? true
  return {
    mainBreed: breed,
    paletteBreed: sub,
    accentBreed: sub === breed ? null : sub,
    eyeColor: BREED_BY_ID[breed].art.palette.eye,
    stage: o.stage ?? STAGES.prime[0]!,
    expression: o.expression ?? 'neutral',
    sparkle: o.sparkle ?? false,
    mischief: o.mischief ?? false,
    animate,
    particles: (o.particles ?? true) && animate,
    lite: o.lite ?? false,
  }
}

function collect(pieces: PartPiece[], key: keyof PartPiece): string {
  return pieces.map((p) => p[key] ?? '').join('')
}

export function renderMonsterSvg(spec: RenderSpec, o: RenderOptions = {}): string {
  const breed = BREED_BY_ID[spec.mainBreed]
  const base = LOOKS[spec.mainBreed]
  const look: Look = formForStage(spec.mainBreed, spec.stage) === 'grown' && base.grown ? base.grown : base
  const polish = POLISH[spec.mainBreed]
  const pal = buildPalette(BREED_BY_ID[spec.paletteBreed].art.palette, spec.eyeColor, { gradients: true, texture: polish.texture })
  const plan = drawPlan(breed.art.plan, pal, look.knobs)
  const s: Sockets = plan.sockets
  look.adjust?.(s)
  const happy = spec.expression === 'happy' || spec.sparkle
  const pieces = look.parts(s, pal, { happy })
  const accent: PartPiece = spec.accentBreed ? ACCENTS[spec.accentBreed](s, BREED_BY_ID[spec.accentBreed].art.palette.accent, pal) : {}
  const face = faceFor(spec.expression, look.face.mouth ?? 'smile', spec.mischief)
  const eyeMood = look.face.eyes === 'lidded' && face.eyes === 'open' ? 'droopy' : face.eyes
  const skin = pal.body

  const back = (accent.back ?? '') + collect(pieces, 'back') + plan.back
  const over = collect(pieces, 'over') + (accent.over ?? '')
  const mouth = face.mouth === null && look.mouthSvg ? look.mouthSvg(s, pal) : drawMouth(s, pal, face.mouth ?? look.face.mouth ?? 'smile', skin)
  const faceSvg = drawEyes(s, pal, eyeMood, look.face, skin) + mouth + (look.face.mouth === 'chew' ? '' : cheeks(s, pal.accent, 5))
  const front = collect(pieces, 'front') + (accent.front ?? '')
  const particles = spec.particles && !spec.lite && polish.particles ? drawParticles(polish.particles, s, cyrb53(spec.mainBreed + spec.paletteBreed)) : ''
  const overlays = (face.sick ? sickTint(s) : '') + (face.sweat ? sweatDrop(s, pal) : '') + (spec.sparkle ? sparkles(s) : '') + (look.happyExtra === 'rainbow' && spec.expression === 'happy' ? rainbow(s) : '')

  const k = sizePct(spec.stage) / 100
  const old = spec.stage >= STAGES.visiblyOld
  const figureClass = [plan.floats ? 'ws-mon__float' : 'ws-mon__bob', look.figureClass ?? ''].filter(Boolean).join(' ')
  const figure = g({ class: 'ws-mon__breathe' }, back + plan.body + over + faceSvg + front + particles + overlays)
  const scaled = g({ transform: `translate(128 232) scale(${k}) translate(-128 -232)` }, (plan.floats ? '' : groundShadow(pal, 128, Math.min(60, s.body.rx * 0.8))) + g({ class: figureClass }, figure))
  const mirrored = o.mirror ? g({ transform: 'translate(256 0) scale(-1 1)' }, scaled) : scaled
  const size = o.size ?? 256
  const classes = ['ws-mon', old ? 'ws-mon--old' : '', spec.lite ? 'ws-mon--lite' : '', o.class ?? ''].filter(Boolean).join(' ')
  return el(
    'svg',
    { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 256 256', width: size, height: size, class: classes, 'data-animate': spec.animate ? 'true' : 'false', role: 'img', 'aria-label': o.label ?? breed.name },
    buildDefs(pal, polish.texture) + mirrored,
  )
}

/** Monster → SVG in one call. */
export function renderMonster(m: Monster, o: SpecOverrides & RenderOptions = {}): string {
  return renderMonsterSvg(specFromMonster(m, o), { ...o, label: o.label ?? m.name })
}
