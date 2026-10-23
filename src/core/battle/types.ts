import type { Personality, Stats, TraitId } from '../../data/types.ts'
import type { Monster } from '../monster.ts'

/**
 * GAME_DESIGN §12: the battle's data model. Everything is integer fixed-point so a battle replays the same
 * on every phone: positions in centi-units (1/100 of an arena unit), percentages in tenths, multipliers in
 * thousandths. The engine owns and mutates one BattleState; the UI reads snapshots.
 */

export type Side = 0 | 1
export type Control = 'ai' | 'player'
/** Readable habits arrive with the rivals (M5); `none` for now. */
export type Habit = 'none'

export interface FighterSetup {
  monster: Monster
  control: Control
  personality: Personality
  habit?: Habit
}

export type PlayerAction =
  | { kind: 'fire'; tech: string }
  /** Hold a direction: +1 toward the opponent, −1 away, 0 stop. */
  | { kind: 'move'; dir: -1 | 0 | 1 }
  | { kind: 'dash' }
  | { kind: 'push' }
  /** Assist: walk to the technique's band and fire on arrival; null cancels. */
  | { kind: 'assist'; tech: string | null }
  | { kind: 'auto'; on: boolean }
  | { kind: 'forfeit' }

export interface BattleInput {
  tick: number
  side: Side
  action: PlayerAction
}

export type SpecialKind = 'lastStand' | 'valor' | 'rage' | 'bulwark' | 'clutch' | 'composure'

export interface ActiveSpecial {
  kind: SpecialKind
  /** Ticks left, or -1 for "until the end of the match" (Clutch). */
  ticksLeft: number
}

export interface TechniqueRef {
  id: string
  /** Mastery bonuses (§10.4): +2 hit at Lv2, +2 force at Lv3. */
  hitBonus: number
  forceBonus: number
}

export interface FighterState {
  side: Side
  name: string
  trait: TraitId
  control: Control
  personality: Personality
  habit: Habit
  /** Player side with Auto on: the AI drives. */
  auto: boolean
  techniques: TechniqueRef[]
  /** Raw stats; SPD′ and DEF′ (form-adjusted) are below. */
  stats: Stats
  spdForm: number
  defForm: number
  total: number
  maxHp: number
  gutsRate: number
  loyalty: number
  fame: number
  nature: number
  stress: number
  /** Tournament grade index (0 = E) for the rookie reserve. */
  gradeIndex: number

  /* dynamic */
  x: number
  hp: number
  guts: number
  gutsAcc: number
  busyTicks: number
  busyTech: string | null
  moveDir: -1 | 0 | 1
  dashTicks: number
  dashCooldown: number
  /** Lunge: dash until Close with no tick limit. */
  lunging: boolean
  pushTicks: number
  pushCooldown: number
  /** Ticks left sliding back from a push or knockback (the slide happens over push.ticks). */
  slideTicks: number
  slideDir: -1 | 1
  stunTicks: number
  dawdleTicks: number
  distractCooldown: number
  slowTicks: number
  special: ActiveSpecial | null
  usedSpecials: SpecialKind[]
  hitsTakenRow: number
  successRow: number
  stillTicks: number
  ramArmed: boolean
  dragonheartUsed: boolean
  blessedAcc: number
  /* AI */
  aiCooldown: number
  aiTargetBand: number
  aiNextThink: number
  assistTech: string | null
  /* requests for this tick (set by inputs or the AI, consumed by the engine) */
  wantFire: string | null
  wantDash: boolean
  wantPush: boolean
  /* counters */
  attacks: number
  hits: number
  damageDealt: number
  techUses: Record<string, number>
}

export type BattleEvent =
  | { t: number; kind: 'fire'; side: Side; tech: string; cost: number }
  | { t: number; kind: 'hit'; side: Side; target: Side; tech: string; damage: number; crit: boolean; wither: number; hitNo: number; of: number }
  | { t: number; kind: 'miss'; side: Side; target: Side; tech: string; hitNo: number; of: number }
  | { t: number; kind: 'heal'; side: Side; amount: number; why: 'tech' | 'drain' | 'blessed' | 'jackpot' }
  | { t: number; kind: 'reflect'; side: Side; target: Side; amount: number }
  | { t: number; kind: 'recoil'; side: Side; amount: number }
  | { t: number; kind: 'stun'; side: Side; ticks: number }
  | { t: number; kind: 'jackpot'; side: Side; result: 'double' | 'heal' | 'fizzle' }
  | { t: number; kind: 'dash'; side: Side }
  | { t: number; kind: 'push'; side: Side; target: Side; blocked: boolean }
  | { t: number; kind: 'distracted'; side: Side }
  | { t: number; kind: 'special'; side: Side; special: SpecialKind }
  | { t: number; kind: 'trait'; side: Side; trait: TraitId }
  | { t: number; kind: 'ko'; side: Side }
  | { t: number; kind: 'end'; outcome: BattleOutcome }

export interface BattleOutcome {
  how: 'ko' | 'time' | 'forfeit'
  /** null = draw. */
  winner: Side | null
  /** HP left as tenths of a percent, per side. */
  hpPct: [number, number]
  ticks: number
}

export interface BattleOptions {
  seed: number
  /** 1,800 for a 60-second match. */
  timerTicks: number
}

export interface BattleState {
  tick: number
  timerTicks: number
  seed: number
  fighters: [FighterState, FighterState]
  outcome: BattleOutcome | null
  log: BattleEvent[]
}

export interface BattleResult {
  outcome: BattleOutcome
  fighters: [FighterState, FighterState]
  log: BattleEvent[]
  seed: number
}
