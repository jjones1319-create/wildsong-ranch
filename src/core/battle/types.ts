import type { AiTier, AutoStyle, Habit, Personality, PlanMode, Stats, TraitId } from '../../data/types.ts'
import type { Monster } from '../monster.ts'
import type { TechPath } from '../../data/paths.ts'

export type { TechPath }

export type { Habit }

/**
 * GAME_DESIGN §12: the battle's data model. Everything is integer fixed-point so a battle replays the same
 * on every phone: positions in centi-units (1/100 of an arena unit), percentages in tenths, multipliers in
 * thousandths. The engine owns and mutates one BattleState; the UI reads snapshots.
 */

export type Side = 0 | 1
export type Control = 'ai' | 'player'

/** Line: the classic battle on one line. Duel: Battle 3D's lock-on duel on a round ring (docs/BATTLE_3D.md). */
export type BattleMode = 'line' | 'duel'


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
  /** Hold a direction: +1 toward the opponent, −1 away, 0 stop. Duel: `side` strafes (+1 to the fighter's left, −1 right). */
  | { kind: 'move'; dir: -1 | 0 | 1; side?: -1 | 0 | 1 }
  /** Duel: a quick sidestep (+1 left, −1 right, as the fighter faces its opponent). */
  | { kind: 'sidestep'; dir: -1 | 1 }
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

/** Duel: a technique between its fire and its landing (the wind-up). */
export interface PendingFire {
  tech: string
  fireTick: number
  landTick: number
  path: TechPath
  /** Guts before paying, and the Battering Ram flag, as they were at the fire. */
  gutsBefore: number
  ramArmed: boolean
  /** The aim: the attacker's and the defender's centres at the fire. */
  ax: number
  ay: number
  dx: number
  dy: number
}

export interface FighterState {
  side: Side
  name: string
  /** The fighter's traits: its breed's own, then an inherited one (v1.11). */
  traits: readonly TraitId[]
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
  /** Duel only: the second floor coordinate (always 0 on the line). */
  y: number
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
  /* duel (docs/BATTLE_3D.md); unused on the line */
  /** Held strafe: +1 left, −1 right, 0 none. */
  strafeDir: -1 | 0 | 1
  sidestepTicks: number
  sidestepDir: -1 | 1
  sidestepCooldown: number
  /** Tick the last sidestep started. */
  sidestepStart: number
  wantSidestep: -1 | 0 | 1
  /** A knockback's slide direction in thousandths (the line uses slideDir). */
  slideVX: number
  slideVY: number
  pending: PendingFire | null
  /** AI: circling until this tick, and a sidestep it has decided on (when, and against which fire tick). */
  aiStrafeUntil: number
  aiSidestepAt: number
  aiSidestepFor: number
  /** AI 3.0 (docs/BATTLE_3D.md §4.1): battle sense 5–95, and how spoiled the monster is (0 no, 1 fond, 2 doting). */
  sense: number
  spoiled: 0 | 1 | 2
  /** §4.3: the opening it last decided about (the tick it began), and when it fires into it (NEVER: it won't). */
  aiOpeningSeen: number
  aiPunishAt: number
  /** §4.4 what it has seen: its straight-line fires, the opponent's sidesteps against them, ticks the opponent walked in, ticks watched, the opponent's fires per range [0, Close…Far]. */
  readLineFires: number
  readSidesteps: number
  readAdvance: number
  readTicks: number
  readBand: number[]
  /** §4.4–§4.5 what it makes of that (null outside the duel, so the line's AI is untouched). */
  duelBias: DuelBias | null
  /** §4.6–§4.7: feinting and slacking until these ticks. */
  aiFeintUntil: number
  aiLazyUntil: number
}

/** AI 3.0's adjustments to the range plan (×100; 100 = none): its sweeps, its knockbacks, and a range to stay out of. */
export interface DuelBias {
  sweepPct: number
  knockPct: number
  avoidBand: number
  avoidPct: number
}

export type BattleEvent =
  /** Duel: `lands` is the tick it lands (after the wind-up) and `path` its shape. */
  | { t: number; kind: 'fire'; side: Side; tech: string; cost: number; lands?: number; path?: TechPath }
  | { t: number; kind: 'hit'; side: Side; target: Side; tech: string; damage: number; crit: boolean; wither: number; hitNo: number; of: number }
  /** Duel: `dodged` when a sidestep carried the target out of a straight-line technique's path. */
  | { t: number; kind: 'miss'; side: Side; target: Side; tech: string; hitNo: number; of: number; dodged?: boolean }
  /** Duel: a sidestep started. */
  | { t: number; kind: 'sidestep'; side: Side; dir: -1 | 1 }
  /** Duel: knocked or shoved into the fence, and stunned there. */
  | { t: number; kind: 'fence'; side: Side; ticks: number }
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
  /** Line (default) or duel (Battle 3D). */
  mode?: BattleMode
}

export interface BattleState {
  mode: BattleMode
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
