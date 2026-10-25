import { signal } from '@preact/signals'
import { playSfx, playStinger } from '../../audio/player.ts'
import { canFire, createBattle, currentBand, gapUnits, previewHitTenths, step, timerTicksFor, type Battle } from '../../core/battle/engine.ts'
import type { BattleEvent, BattleInput, BattleOutcome, FighterSetup, FighterState, PlayerAction, Side } from '../../core/battle/types.ts'
import type { Monster } from '../../core/monster.ts'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { fill } from '../../data/text/format.ts'
import { BAND_LABELS } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { BATTLE, BATTLE_FX } from '../../data/tuning.ts'
import { fxEventsFor, publishFx, type FighterPose } from '../../fx/bus.ts'
import type { AiTier, AutoStyle, Habit, Personality, PlanMode } from '../../data/types.ts'
import type { Screen } from '../router.ts'
import { settings, updateSettings } from './appStore.ts'

/**
 * Drives one battle for the screen (§12.11): a requestAnimationFrame loop steps the pure engine at
 * 30 × speed ticks per second, player taps become inputs for the next tick, and events become floating
 * numbers, flashes and a result card. Versus is exhibition only: nothing is written back to any monster.
 */

export interface BattleFinish {
  winner: 0 | 1 | null
  how: 'ko' | 'time' | 'forfeit'
  hpPct: [number, number]
  /** How long it lasted, in ticks. */
  ticks: number
  /** Side A's technique uses, for mastery. */
  techUses: Record<string, number>
}

export interface BattleSetup {
  a: Monster
  b: Monster
  /** Who drives side A; side B is always the CPU here. */
  aControl: 'player' | 'ai'
  personalityA: Personality
  personalityB: Personality
  habitB?: Habit
  /** §12.10 skill tiers (M10); the engine picks from the grade when missing. Side A on Auto also follows the Auto style setting. */
  tierA?: AiTier
  tierB?: AiTier
  timerSec: number
  /** Where Done goes. */
  origin: Screen
  /** Side B's display name when it isn't the monster's own (a rival breeder). */
  nameB?: string
  /** A cup or Trial match: the result goes here and the card's button reads "Continue". Rematch is hidden. */
  onFinished?: (r: BattleFinish) => void
  /**
   * The exact fighters to create (a cup's player match or a replay), so the battle on screen is the one the core
   * would simulate. Without it the fighters are built from the fields above (Versus).
   */
  setups?: { a: FighterSetup; b: FighterSetup }
  /** A fixed seed (a cup match); otherwise a fresh one. */
  seed?: number
  /** §12.11 Auto from the first tick, as a recorded input on side A (side A stays under the player's control). */
  autoStart?: boolean
  /** A replay of a recorded NPC match: no Rematch, and the card says so. */
  replay?: boolean
}

export interface FighterView {
  name: string
  hp: number
  maxHp: number
  guts: number
  /** Position in arena units (−550…550). */
  x: number
  busyTech: string | null
  special: string | null
  dawdling: boolean
  stunned: boolean
  attacks: number
  hits: number
  damage: number
  auto: boolean
  assistTech: string | null
  /** §12.11 the brain's current plan (the thinking icon); null for a player on the pads. */
  plan: PlanMode | null
  techniques: { id: string; name: string; range: 1 | 2 | 3 | 4; cost: number; hitPct: number; canFire: boolean; affordable: boolean }[]
}

export interface BattleView {
  tick: number
  timerTicks: number
  secondsLeft: number
  gap: number
  band: number
  touching: boolean
  fighters: [FighterView, FighterView]
  outcome: BattleOutcome | null
}

export interface FloatEffect {
  id: number
  side: Side
  text: string
  tone: 'damage' | 'crit' | 'miss' | 'heal' | 'note' | 'special'
}

/**
 * §22 battle effects on the monsters themselves: a lunge when a melee technique fires, a flash and knockback on a
 * hit. Everything else (projectiles, sparks, splashes, shake, hit-stop) is V1's effects layer, fed through fx/bus.
 */
export interface BattleFx {
  id: number
  side: Side
  kind: 'lunge' | 'hit'
}

export const fx = signal<BattleFx[]>([])

export const setup = signal<BattleSetup | null>(null)
export const view = signal<BattleView | null>(null)
export const speed = signal<1 | 2 | 4>(1)
export const paused = signal(false)
export const effects = signal<FloatEffect[]>([])
export const resultLine = signal<string>('')

let battle: Battle | null = null
let raf = 0
let lastTime = 0
let carry = 0
let pending: BattleInput[] = []
let effectId = 0
const inputs: BattleInput[] = []

function freshSeed(): number {
  try {
    const a = new Uint32Array(1)
    crypto.getRandomValues(a)
    return a[0]!
  } catch {
    return Math.floor(Math.random() * 0xffffffff)
  }
}

function techniqueViews(f: FighterState, battleState: Battle['state']): FighterView['techniques'] {
  return f.techniques.map((t) => {
    const tech = TECHNIQUE_BY_ID[t.id]!
    return {
      id: t.id,
      name: tech.name,
      range: tech.range,
      cost: tech.cost,
      hitPct: Math.round(previewHitTenths(battleState, f.side, t.id) / 10),
      canFire: canFire(battleState, f, t.id),
      affordable: f.guts >= tech.cost,
    }
  })
}

function snapshot(): BattleView | null {
  if (!battle) return null
  const s = battle.state
  const gap = gapUnits(s)
  const fighters = s.fighters.map((f) => ({
    name: f.name,
    hp: f.hp,
    maxHp: f.maxHp,
    guts: f.guts,
    x: Math.round(f.x / 100),
    busyTech: f.busyTech,
    special: f.special?.kind ?? null,
    dawdling: f.dawdleTicks > 0,
    stunned: f.stunTicks > 0,
    attacks: f.attacks,
    hits: f.hits,
    damage: f.damageDealt,
    auto: f.auto,
    assistTech: f.assistTech,
    plan: f.aiMode,
    techniques: techniqueViews(f, s),
  })) as [FighterView, FighterView]
  return {
    tick: s.tick,
    timerTicks: s.timerTicks,
    secondsLeft: Math.max(0, Math.ceil((s.timerTicks - s.tick) / BATTLE.ticksPerSecond)),
    gap,
    band: currentBand(s),
    touching: gap <= BATTLE.push.maxGap,
    fighters,
    outcome: s.outcome,
  }
}

function pushFx(f: Omit<BattleFx, 'id'>, ms: number): void {
  const e = { ...f, id: ++effectId }
  fx.value = [...fx.value.slice(-7), e]
  setTimeout(() => {
    fx.value = fx.value.filter((x) => x.id !== e.id)
  }, ms)
}

function pushEffect(side: Side, text: string, tone: FloatEffect['tone']): void {
  const e = { id: ++effectId, side, text, tone }
  effects.value = [...effects.value.slice(-11), e]
  setTimeout(() => {
    effects.value = effects.value.filter((x) => x.id !== e.id)
  }, 1100)
}

/** Browsers only allow vibration after a real tap; remember the first one so the console stays quiet before it. */
let userTapped = false
if (typeof document !== 'undefined') {
  document.addEventListener(
    'pointerdown',
    () => {
      userTapped = true
    },
    { once: true, passive: true },
  )
}

function vibrate(ms: number): void {
  try {
    if (userTapped && settings.value.haptics && typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') navigator.vibrate(ms)
  } catch {
    /* no haptics */
  }
}

function describe(events: readonly BattleEvent[]): void {
  const t = UI_TEXT.battle
  const s = battle?.state
  if (s) {
    // V1: every engine event becomes effects-layer events (pure mapping; the arena draws the element's recipe).
    const poses: [FighterPose, FighterPose] = [
      { x: s.fighters[0].x / 100, maxHp: s.fighters[0].maxHp },
      { x: s.fighters[1].x / 100, maxHp: s.fighters[1].maxHp },
    ]
    for (const e of events) publishFx(fxEventsFor(e, poses))
  }
  for (const e of events) {
    switch (e.kind) {
      case 'fire': {
        const tech = TECHNIQUE_BY_ID[e.tech]
        if (tech && tech.range <= 2) pushFx({ side: e.side, kind: 'lunge' }, BATTLE_FX.lungeMs)
        playSfx('fire')
        break
      }
      case 'hit':
        pushEffect(e.target, e.crit ? `${t.floats.crit} −${e.damage}` : `−${e.damage}`, e.crit ? 'crit' : 'damage')
        pushFx({ side: e.target, kind: 'hit' }, BATTLE_FX.knockbackMs)
        vibrate(e.crit ? 25 : 12)
        playSfx(e.crit ? 'crit' : 'hit')
        break
      case 'miss':
        pushEffect(e.target, t.floats.miss, 'miss')
        playSfx('miss')
        break
      case 'ko':
        playSfx('ko')
        break
      case 'heal':
        pushEffect(e.side, fill(t.floats.heal, { n: e.amount }), 'heal')
        break
      case 'distracted':
        pushEffect(e.side, t.floats.distracted, 'note')
        break
      case 'special':
        pushEffect(e.side, t.specials[e.special], 'special')
        playSfx('special')
        break
      case 'reflect':
        pushEffect(e.target, `${t.floats.reflect} −${e.amount}`, 'damage')
        break
      case 'recoil':
        pushEffect(e.side, `−${e.amount}`, 'damage')
        break
      case 'stun':
        pushEffect(e.side, t.floats.stun, 'note')
        break
      case 'push':
        pushEffect(e.target, e.blocked ? t.floats.blocked : t.floats.pushed, 'note')
        break
      case 'dash':
        pushEffect(e.side, t.floats.dash, 'note')
        break
      case 'jackpot':
        pushEffect(e.side, e.result === 'double' ? t.floats.jackpotDouble : e.result === 'heal' ? t.floats.jackpotHeal : t.floats.jackpotFizzle, 'special')
        break
      case 'trait':
        if (e.trait === 'dragonheart') pushEffect(e.side, t.traitMoments.dragonheart, 'special')
        break
      default:
        break
    }
  }
}

function finish(): void {
  stopLoop()
  const v = snapshot()
  view.value = v
  const s = setup.value
  if (!v?.outcome || !s) return
  const w = v.outcome.winner
  const name = w === null ? '' : v.fighters[w].name
  resultLine.value = w === null ? UI_TEXT.battle.result.draw : fill(UI_TEXT.battle.result.win, { name })
  // §23: the fanfare for the player's monster, a low note for a loss.
  if (w === 0) playStinger('victory')
  else if (w === 1) playSfx('lose')
}

function runTicks(n: number): void {
  if (!battle) return
  for (let i = 0; i < n && !battle.state.outcome; i++) {
    const tick = battle.state.tick + 1
    const now = pending.map((p) => ({ ...p, tick }))
    pending = []
    inputs.push(...now)
    describe(step(battle, now))
  }
  view.value = snapshot()
  if (battle.state.outcome) finish()
}

function frame(time: number): void {
  if (!battle || battle.state.outcome) return
  if (lastTime === 0) lastTime = time
  const dt = Math.min(100, time - lastTime)
  lastTime = time
  if (!paused.value) {
    carry += (dt / 1000) * BATTLE.ticksPerSecond * speed.value
    const n = Math.min(12, Math.floor(carry))
    carry -= n
    if (n > 0) runTicks(n)
  }
  if (battle && !battle.state.outcome) raf = requestAnimationFrame(frame)
}

function stopLoop(): void {
  if (raf) cancelAnimationFrame(raf)
  raf = 0
  lastTime = 0
  carry = 0
}

/** Starts (or restarts) the battle described by `s`. */
export function startBattle(s: BattleSetup, seed = s.seed ?? freshSeed()): void {
  stopLoop()
  setup.value = s
  battle = createBattle(
    s.setups?.a ?? { monster: s.a, control: s.aControl, personality: s.personalityA, tier: s.tierA, style: settings.value.autoStyle },
    s.setups?.b ?? { monster: s.b, control: 'ai', personality: s.personalityB, habit: s.habitB ?? 'none', tier: s.tierB },
    { seed, timerTicks: timerTicksFor(s.timerSec) },
  )
  if (s.nameB) battle.state.fighters[1].name = s.nameB
  pending = []
  inputs.length = 0
  // §12.11 Auto is the engine's own flag, switched on at tick 1 and recorded, so one tap on Auto takes over.
  if (s.autoStart && s.aControl === 'player') pending.push({ tick: 0, side: 0, action: { kind: 'auto', on: true, style: battle.state.fighters[0].style } })
  effects.value = []
  fx.value = []
  paused.value = false
  resultLine.value = ''
  view.value = snapshot()
  if (typeof requestAnimationFrame === 'function') raf = requestAnimationFrame(frame)
}

export function rematch(): void {
  const s = setup.value
  if (s) startBattle(s)
}

export function leaveBattle(): void {
  stopLoop()
  battle = null
  view.value = null
  effects.value = []
  fx.value = []
}

/** The finished battle's result for a cup or Trial (null while it is still running). */
export function finishedResult(): BattleFinish | null {
  if (!battle?.state.outcome) return null
  const o = battle.state.outcome
  return { winner: o.winner, how: o.how, hpPct: o.hpPct, ticks: o.ticks, techUses: { ...battle.state.fighters[0].techUses } }
}

/** Done on the result card: hand the result to whoever asked for the fight, or go back where we came from. */
export function finishAndLeave(navigateTo: (s: Screen) => void): void {
  const s = setup.value
  const r = finishedResult()
  leaveBattle()
  if (s?.onFinished && r) {
    s.onFinished(r)
    return
  }
  if (s) navigateTo(s.origin)
}

function act(action: PlayerAction, side: Side = 0): void {
  if (!battle || battle.state.outcome) return
  pending.push({ tick: 0, side, action })
}

export const fire = (tech: string) => act({ kind: 'fire', tech })
export const move = (dir: -1 | 0 | 1) => act({ kind: 'move', dir })
export const dash = () => act({ kind: 'dash' })
export const pushOpponent = () => act({ kind: 'push' })
export const assist = (tech: string | null) => act({ kind: 'assist', tech })
export const forfeit = () => {
  act({ kind: 'forfeit' })
  paused.value = false
  runTicks(1)
}

export function toggleAuto(): void {
  const v = view.value
  if (!v) return
  act({ kind: 'auto', on: !v.fighters[0].auto, style: settings.value.autoStyle })
  if (paused.value) runTicks(1)
}

/** §12.11 the Auto style: saved as a setting and, when side A is on Auto now, recorded as an input so replays stay exact. */
export function setAutoStyle(style: AutoStyle): void {
  void updateSettings({ autoStyle: style })
  const v = view.value
  if (!v || !v.fighters[0].auto) return
  act({ kind: 'auto', on: true, style })
  if (paused.value) runTicks(1)
}

/** Tap on a card: fire when it is usable now; otherwise, with Assist, walk there and fire on arrival. */
export function tapTechnique(id: string): void {
  const v = view.value
  if (!v) return
  const card = v.fighters[0].techniques.find((t) => t.id === id)
  if (!card) return
  if (card.canFire) {
    fire(id)
    return
  }
  if (!settings.value.assist || !card.affordable) return
  assist(v.fighters[0].assistTech === id ? null : id)
}

export function assistText(): string | null {
  const v = view.value
  const id = v?.fighters[0].assistTech
  if (!v || !id) return null
  const tech = TECHNIQUE_BY_ID[id]
  return tech ? fill(UI_TEXT.battle.assistOn, { band: BAND_LABELS[tech.range], tech: tech.name }) : null
}

export function setSpeed(s: 1 | 2 | 4): void {
  speed.value = s
}

export function setPaused(on: boolean): void {
  paused.value = on
  if (!on) lastTime = 0
}

/** Skip: simulate the rest instantly. */
export function skipToEnd(): void {
  if (!battle) return
  paused.value = false
  effects.value = []
  while (!battle.state.outcome) {
    const tick = battle.state.tick + 1
    const now = pending.map((p) => ({ ...p, tick }))
    pending = []
    step(battle, now)
  }
  finish()
}

/** The inputs recorded so far (a replay of this battle). */
export function recordedInputs(): BattleInput[] {
  return [...inputs]
}
