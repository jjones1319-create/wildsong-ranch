import { useEffect, useRef, useState } from 'preact/hooks'
import { makePreset } from '../../../core/presets.ts'
import { ELEMENT_LABELS, FX_INTENSITY_LABELS, FX_QUALITY_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { FX } from '../../../data/tuning.ts'
import { ELEMENTS, FX_INTENSITIES, FX_QUALITY_SETTINGS, type Element } from '../../../data/types.ts'
import type { FxEvent } from '../../../fx/bus.ts'
import type { FxLayer } from '../../../fx/FxLayer.ts'
import { PRIMITIVE_NAMES, type PrimitiveCall, type PrimitiveName } from '../../../fx/primitives/types.ts'
import { comboRecipe, recipeFor } from '../../../fx/recipes.ts'
import { createFxRng } from '../../../fx/rng.ts'
import { Arena } from '../../battle/Arena.tsx'
import { Chips, Segmented, TopBar } from '../../components/Controls.tsx'
import { PickSlot, type Picked } from '../../components/MonsterPicker.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { settings } from '../../store/appStore.ts'
import { currentProfile, fxStats, fxUnavailable, setFxIntensity, setFxQuality } from '../../store/fxStore.ts'

const t = UI_TEXT.fxLab
const XA = -210
const XB = 210
const CHEST = -100

/** One primitive aimed from the left monster at the right one, so every shape has somewhere sensible to go. */
export function labCall(name: PrimitiveName, element: Element, strength = 0.9): PrimitiveCall {
  const from = { x: XA + 70, y: CHEST }
  const to = { x: XB, y: CHEST }
  switch (name) {
    case 'burst':
      return { name, params: { element, x: to.x, y: to.y, strength } }
    case 'cone':
      return { name, params: { element, x: from.x, y: from.y, dir: 0, durationMs: 700, strength, haze: true } }
    case 'trail':
      return { name, params: { element, x: from.x, y: from.y, to, durationMs: 420, strength, arc: 80 } }
    case 'projectile':
      return { name, params: { element, x: from.x, y: from.y, to, strength, onArrive: 'impact' } }
    case 'beam':
      return { name, params: { element, x: from.x, y: from.y, to, strength } }
    case 'ring':
      return { name, params: { element, x: to.x, y: to.y, strength } }
    case 'impact':
      return { name, params: { element, x: to.x - 30, y: to.y, strength, crit: true } }
    case 'splash':
      return { name, params: { element, x: to.x - 20, y: -40, strength } }
    case 'sheet':
      return { name, params: { element, x: 0, y: 0, rising: true, dir: 1, strength: 1 } }
    case 'lightning':
      return { name, params: { element, x: to.x - 90, y: -330, to, branches: true, strength } }
    case 'haze':
      return { name, params: { element, x: 0, y: -110, width: 300, height: 220, durationMs: 1200, strength } }
    case 'glow':
      return { name, params: { element, x: from.x - 70, y: from.y, pulse: true, durationMs: 1000, strength } }
    case 'debris':
      return { name, params: { element, x: to.x - 20, y: -40, strength } }
    case 'mist':
      return { name, params: { element, x: to.x, y: to.y, durationMs: 1400, strength } }
    case 'flash':
      return { name, params: { element } }
    case 'shake':
      return { name, params: { amplitudePx: currentProfile().shakePx || 0, element } }
    case 'hitstop':
      return { name, params: { ms: currentProfile().hitstopMs || 0 } }
    case 'impactFrame':
      return { name, params: { element } }
  }
}

/** A made-up attack: a fire then a hit (or crit) from the left monster, through the real battle recipes. */
export function randomAttack(element: Element, rng: ReturnType<typeof createFxRng>): PrimitiveCall[] {
  const ranged = rng.next() < 0.5
  const crit = rng.next() < 0.3
  const from = { x: XA, y: CHEST }
  const to = { x: XB, y: CHEST }
  const profile = currentProfile()
  const fire: FxEvent = { kind: 'fire', side: 0, element, from, to, strength: 0.7, ranged }
  const hit: FxEvent = { kind: crit ? 'crit' : 'hit', side: 1, element, from, to, strength: crit ? 0.9 : 0.6, crit }
  return [...recipeFor(fire, profile), ...recipeFor(hit, profile)]
}

interface LabWindow extends Window {
  __fx?: {
    fire: (name: PrimitiveName, element: Element, strength?: number) => void
    attack: (element: Element) => void
    combo: () => void
    stress: () => void
    clear: () => void
    step: (ms: number) => void
    stats: () => unknown
    ready: boolean
  }
}

/** VISUAL_V1_EFFECTS §7: the Effects Lab. Two preset monsters, the real arena camera, every primitive at every element. */
export function LabEffectsScreen() {
  const [a, setA] = useState<Picked>(() => ({ monster: makePreset('tumblefox', 'C'), source: 'presets' }))
  const [b, setB] = useState<Picked>(() => ({ monster: makePreset('puddlepup', 'C'), source: 'presets' }))
  const [element, setElement] = useState<Element>('Fire')
  const [frames, setFrames] = useState<string[]>([])
  const [recording, setRecording] = useState(false)
  const layerRef = useRef<FxLayer | null>(null)
  const rng = useRef(createFxRng(42))
  const stats = fxStats.value
  const s = settings.value
  const manual = typeof location !== 'undefined' && location.search.includes('fxmanual')

  const fire = (calls: PrimitiveCall[]) => layerRef.current?.fireAll(calls)
  const randomElement = () => rng.current.pick(ELEMENTS)
  const stress = () => {
    const calls: PrimitiveCall[] = []
    const shapes = PRIMITIVE_NAMES.filter((n) => n !== 'flash' && n !== 'shake' && n !== 'hitstop' && n !== 'impactFrame')
    for (let i = 0; i < FX.stressCount; i++) {
      const c = labCall(rng.current.pick(shapes), randomElement(), 1)
      // Spread the stress across the arena so it is not one pile.
      const params = c.params as { x?: number; to?: { x: number; y: number } }
      const dx = rng.current.range(-200, 200)
      if (typeof params.x === 'number') params.x += dx
      if (params.to) params.to = { x: params.to.x + dx * 0.5, y: params.to.y }
      calls.push(c)
    }
    fire(calls)
  }
  const combo = () => fire(comboRecipe(XA, 1, currentProfile()))

  // Playwright and the dev console drive the Lab through window.__fx.
  useEffect(() => {
    const w = window as LabWindow
    w.__fx = {
      fire: (name, el, strength) => fire([labCall(name, el, strength)]),
      attack: (el) => fire(randomAttack(el, rng.current)),
      combo,
      stress,
      clear: () => layerRef.current?.clear(),
      step: (ms) => layerRef.current?.step(ms),
      stats: () => layerRef.current?.stats() ?? null,
      ready: false,
    }
    return () => {
      delete w.__fx
    }
  }, [])

  const record = () => {
    const layer = layerRef.current
    if (!layer || recording) return
    setRecording(true)
    const shots: string[] = []
    const start = performance.now()
    let n = 0
    const tick = () => {
      if (performance.now() - start > 3000 || shots.length >= 24) {
        setFrames(shots)
        setRecording(false)
        return
      }
      if (n++ % 4 === 0) {
        try {
          shots.push(layer.canvas.toDataURL('image/png'))
        } catch {
          /* tainted or lost context: skip the frame */
        }
      }
      requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }

  return (
    <main class="screen fxlab">
      <TopBar title={t.title} />
      <SpeakerCard speaker={UI_TEXT.pell} tone="muted">
        <p>{fxUnavailable.value ? t.noWebgl : t.hint}</p>
      </SpeakerCard>
      <Arena
        fighters={[
          { monster: a.monster, x: XA },
          { monster: b.monster, x: XB },
        ]}
        season="Summer"
        weather="Sunny"
        manualClock={manual}
        onLayer={(layer) => {
          layerRef.current = layer
          const w = window as LabWindow
          if (w.__fx) w.__fx.ready = layer !== null
        }}
      />
      <p class="fxlab__stats muted small" aria-live="polite">
        {stats ? `${stats.fps} ${t.stats.fps} · ${stats.particles} ${t.stats.particles} · ${t.stats.quality} ${FX_QUALITY_LABELS[stats.tier].name} · ${t.stats.intensity} ${FX_INTENSITY_LABELS[stats.intensity].name}` : '…'}
      </p>
      <p class="field__label small">{t.element}</p>
      <Chips options={ELEMENTS.map((e) => ({ value: e, label: ELEMENT_LABELS[e] }))} value={element} onChange={setElement} label={t.element} />
      <p class="field__label small">{t.primitives}</p>
      <div class="fxlab__grid">
        {PRIMITIVE_NAMES.map((name) => (
          <button key={name} type="button" class="btn btn--small" data-fx={name} onClick={() => fire([labCall(name, element)])}>
            {t.primitiveNames[name]}
          </button>
        ))}
      </div>
      <p class="field__label small">{t.extras}</p>
      <div class="fxlab__grid">
        <button type="button" class="btn btn--small" onClick={() => fire(randomAttack(randomElement(), rng.current))}>
          {t.random}
        </button>
        <button type="button" class="btn btn--small" onClick={combo}>
          {t.combo}
        </button>
        <button type="button" class="btn btn--small" onClick={stress}>
          {t.stress}
        </button>
        <button type="button" class="btn btn--small" onClick={() => layerRef.current?.clear()}>
          {t.clear}
        </button>
        {import.meta.env.DEV && (
          <button type="button" class="btn btn--small" disabled={recording} onClick={record}>
            {recording ? t.recording : t.record}
          </button>
        )}
      </div>
      {frames.length > 0 && (
        <div class="fxlab__strip" aria-label={t.record}>
          {frames.map((src, i) => (
            <img key={i} src={src} alt="" />
          ))}
        </div>
      )}
      <p class="field__label small">{UI_TEXT.settings.fxQuality}</p>
      <Segmented options={FX_QUALITY_SETTINGS.map((q) => ({ value: q, label: FX_QUALITY_LABELS[q].name }))} value={s.fxQuality} onChange={setFxQuality} label={UI_TEXT.settings.fxQuality} />
      <p class="field__label small">{UI_TEXT.settings.fxIntensity}</p>
      <Segmented options={FX_INTENSITIES.map((i) => ({ value: i, label: FX_INTENSITY_LABELS[i].name }))} value={s.fxIntensity} onChange={setFxIntensity} label={UI_TEXT.settings.fxIntensity} />
      <div class="row">
        <PickSlot label={t.sideA} picked={a} onPick={setA} />
        <PickSlot label={t.sideB} picked={b} onPick={setB} />
      </div>
      <div class="spacer" />
    </main>
  )
}
