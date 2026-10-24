import type { AiTier, AutoStyle, Habit, Personality, PlanMode, Stats, TraitId } from '../../data/types.ts'
import type { Monster } from '../monster.ts'

export type { Habit }

/**
 * GAME_DESIGN §12: the battle's data model. Everything is integer fixed-point so a battle replays the same
 * on every phone: positions in centi-units (1/100 of an arena unit), percentages in tenths, multipliers in
 * thousandths. The engine owns and mutates one BattleState; the UI reads snapshots.
 */

export type Side = 0 | 1
export type Control = 'ai' | 'player'

/** Which brain drives an AI side: AI 2.0 (the game) or the v1.0 brain (one comparison test only). */
export type Brain = 'v2' | 'v1'

export interface FighterSetup {
  monster: Monster
  control: Control
  personality: Personality
  habit?: Habit
  /** §12.10 skill tier; by default from the monster's grade (E–D rookie, C–B skilled, A–S expert). A player side is always expert. */
  tier?: AiTier
  /** §12.11 the Auto style (player side). */
  style?: AutoStyle
  brain?: Brain
}

export type PlayerAction =
  | { kind: 'fire'; tech: string }
  /** Hold a direction: +1 toward the opponent, −1 away, 0 stop. */
  | { kind: 'move'; dir: -1 | 0 | 1 }
  | { kind: 'dash' }
  | { kind: 'push' }
  /** Assist: walk to the technique's band and fire on arrival; null cancels. */
  | { kind: 'assist'; tech: string | null }
  | { kind: 'auto'; on: boolean; style?: AutoStyle }
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
  /** CONTENT §12 Lantern-bearer: +wither on Wither techniques. */
  witherBonus: number
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
  /** Habits: "opens Far" is satisfied after the first technique. */
  habitDone: boolean
  /* AI (§12.10) */
  tier: AiTier
  style: AutoStyle
  brain: Brain
  aiCooldown: number
  aiTargetBand: number
  aiNextThink: number
  /** The current plan: the gap it wants, the technique it is working toward, and what the icon shows. */
  aiSweet: number
  aiGoal: string | null
  aiMode: PlanMode | null
  /** The icon's mode is held until this tick. */
  aiModeUntil: number
  /** Earliest tick a decided technique fires (the reaction delay), and which one. */
  aiFireAt: number
  aiFireTech: string | null
  aiFootsie: number
  aiFootsieNext: number
  /** Tick each band and technique was last used (for variety). */
  aiBandUsed: number[]
  aiTechUsed: Record<string, number>
  aiKiteUntil: number
  aiBackWall: number
  /** A tier mistake keeps its band until this tick. */
  aiMistakeUntil: number
  /** Last tick this fighter walked toward its opponent (so an AI can tell a chasing player). */
  lastApproachTick: number
  /** Cached from the last plan: each technique's value, and whether the opponent out-damages me at Close. */
  aiValues: Record<string, number>
  aiWeakClose: boolean
  /** Event markers that force a re-plan. */
  aiLastHp: number
  aiLastOppAttacks: number
  aiAfford: number
  aiOppAfford: number
  aiLastTouching: boolean
  aiLastCornered: boolean
  aiLastHits: number
  /** The opponent reads these (last tick's values) instead of this tick's decisions. */
  prevMoveDir: -1 | 0 | 1
  prevTargetBand: number
  /** Consecutive ticks touching with neither side attacking. */
  touchStreak: number
  lastHitTakenTick: number
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
  /** M10 movement counters: sign changes of actual displacement, ticks spent touching, pushes started. */
  dirChanges: number
  lastDx: -1 | 0 | 1
  touchTicks: number
  pushes: number
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
  /** AI 2.0: the target band or the plan icon changed. */
  | { t: number; kind: 'plan'; side: Side; band: number; mode: PlanMode }
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
