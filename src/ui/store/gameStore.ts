import { computed, signal } from '@preact/signals'
import type { AgingEvent } from '../../core/aging.ts'
import { buyItem, type BuyRefusal } from '../../core/economy.ts'
import {
  actionMenu,
  answerRequest,
  beginWeek,
  chooseAction,
  finishWeek,
  forgetFromCard,
  learnFromSongbook,
  needsFoodChoice,
  react,
  replaceActiveMonster,
  switchDifficulty,
  useItems as useItemsCore,
} from '../../core/game.ts'
import { buySheet, type SheetRefusal } from '../../core/guild.ts'
import { awaken as awakenCore, buyFromMarket as buyFromMarketCore, recreate as recreateCore, wakeStone as wakeStoneCore, type AwakenResult } from '../../core/creation.ts'
import { fuse as fuseCore, type FuseOutput } from '../../core/fusion.ts'
import {
  adopt as adoptCore,
  concludeLife as concludeLifeCore,
  editMemorial as editMemorialCore,
  freezeActive as freezeActiveCore,
  giveHeartstone as giveHeartstoneCore,
  makeActive as makeActiveCore,
  releaseStored as releaseStoredCore,
  replaceStored as replaceStoredCore,
  sendToFreezer as sendToFreezerCore,
  type AdoptRefusal,
  type ConcludeResult,
  type FreezeRefusal,
  type GiveRefusal,
  type SendRefusal,
  type ThawRefusal,
} from '../../core/legacy.ts'
import { randomPhrase as randomPhraseCore } from '../../core/shrine.ts'
import { answerEvent as answerEventCore } from '../../core/game.ts'
import { sellItem as sellItemCore, type SellRefusal } from '../../core/economy.ts'
import { detour as detourCore, moveTo as moveToCore, retreat as retreatCore, turnBack as turnBackCore, type MoveRefusal } from '../../core/expedition.ts'
import { applyOddJob as applyOddJobCore } from '../../core/oddJobs.ts'
import { attendVigil as attendVigilCore, giveBlueprint as giveBlueprintCore, offerAtShrine as offerAtShrineCore, type BlueprintRefusal, type OfferRefusal } from '../../core/unlocks.ts'
import { buyUpgrade as buyUpgradeCore, visitGarden as visitGardenCore, type GardenRefusal, type UpgradeRefusal } from '../../core/upgrades.ts'
import type { ExpeditionSiteId, UpgradeId } from '../../data/types.ts'
import { SHRINE_WORDS } from '../../data/text/shrine.ts'
import type { BreedId } from '../../data/types.ts'
import { newId } from '../lib/ids.ts'
import type { UseItemResult } from '../../core/items.ts'
import type { Monster } from '../../core/monster.ts'
import { markTipSeen, nextTip, type TipContext, type TipId } from '../../core/onboarding.ts'
import { drillLine, eventLines, growsUpAtPrime, type WrenLine } from '../../core/report.ts'
import { createRng, type Rng } from '../../core/rng.ts'
import type { LearnStatus } from '../../core/songbook.ts'
import { createGameState, type GameState, type NewGameOptions, type WeekAction } from '../../core/state.ts'
import type { DrillResult, Reaction } from '../../core/training.ts'
import type { WeekEvent } from '../../core/week.ts'
import type { Difficulty, FoodId, StatKey } from '../../data/types.ts'
import { loadLatestSave, persistAutosave, type LoadSource } from '../../save/db.ts'
import { makeSave, type SaveFile } from '../../save/schema.ts'
import { now } from '../lib/clock.ts'
import { askPersistence, kv, ls, onBoot, showToast } from './appStore.ts'
import { UI_TEXT } from '../../data/text/ui.ts'

/**
 * The ranch's state (M3). One game at a time: the newest autosave. Every change goes through `commit`,
 * which updates the signal and autosaves (database + mirror). The RNG lives here and its state is saved
 * with the game, so closing the app mid-week and reopening continues the very same sequence.
 */

export const game = signal<GameState | null>(null)
export const saveSource = signal<LoadSource>('none')

/** The in-progress drill result (held in memory until the week is finished and saved). */
export interface ResultFlow {
  kind: 'result'
  drill: DrillResult
  /** The monster before the drill, for the stat deltas. */
  before: Monster
  /** The state after the drill, not yet committed. */
  state: GameState
  events: WeekEvent[]
  line: WrenLine
  reaction: Reaction | null
}

export interface SummaryFlow {
  kind: 'summary'
  lines: WrenLine[]
  aging: AgingEvent[]
  fees: number
  grewUp: boolean
  ended: 'passed' | 'retired' | null
}

export type Flow = { kind: 'idle' } | { kind: 'train' } | ResultFlow | SummaryFlow

export const flow = signal<Flow>({ kind: 'idle' })

/** Lines from the start of the current week (food, charms), shown in Wren's bubble until the week ends. */
export const weekNews = signal<WrenLine[]>([])

let rng: Rng = createRng(0)

export function rngState(): number {
  return rng.getState()
}

/* ---------- loading and saving ---------- */

export async function bootGame(): Promise<void> {
  const r = await loadLatestSave(kv(), ls())
  saveSource.value = r.source
  if (r.save) loadSaveFile(r.save)
}

onBoot(bootGame)

export function loadSaveFile(save: SaveFile): void {
  rng = createRng(0)
  rng.setState(save.rng)
  game.value = save.game
  flow.value = { kind: 'idle' }
  weekNews.value = []
}

export function currentSave(): SaveFile | null {
  const g = game.value
  return g ? makeSave(g, rng.getState(), { savedAt: now(), appVersion: __APP_VERSION__ }) : null
}

async function persist(): Promise<void> {
  const save = currentSave()
  if (!save) return
  const ok = await persistAutosave(kv(), ls(), save)
  if (!ok) showToast(UI_TEXT.errors.saveFailed)
  void askPersistence()
}

/** Sets the new state and autosaves it. */
export function commit(next: GameState): void {
  game.value = next
  void persist()
}

/** §20: autosave when the app goes to the background. */
export function installAutosaveOnHide(doc: Document): void {
  doc.addEventListener('visibilitychange', () => {
    if (doc.visibilityState === 'hidden' && game.value) void persist()
  })
}

/* ---------- new game ---------- */

/** UI-side seed: core never calls Math.random. */
function freshSeed(): number {
  try {
    const a = new Uint32Array(1)
    crypto.getRandomValues(a)
    return a[0]!
  } catch {
    return Math.floor(Math.random() * 0xffffffff)
  }
}

export function startNewGame(opts: NewGameOptions): GameState {
  rng = createRng(freshSeed())
  const state = createGameState(opts)
  flow.value = { kind: 'idle' }
  weekNews.value = []
  commit(state)
  return state
}

export const hasGame = computed(() => game.value !== null)

/* ---------- the week ---------- */

/** Begins the week when it is waiting to begin and no food choice is pending. Call when the ranch shows. */
export function settle(): void {
  const g = game.value
  if (!g || g.ended || g.weekPhase !== 'start' || needsFoodChoice(g)) return
  const r = beginWeek(g, rng)
  weekNews.value = r.state.monster ? eventLines(r.events, r.state.monster) : []
  commit(r.state)
}

export function pickFood(food: FoodId): void {
  const g = game.value
  if (!g || !needsFoodChoice(g)) return
  const r = beginWeek(g, rng, food)
  weekNews.value = r.state.monster ? eventLines(r.events, r.state.monster) : []
  commit(r.state)
}

export function answer(accept: boolean): void {
  const g = game.value
  if (!g || !g.pendingRequest) return
  const r = answerRequest(g, accept)
  if (r.forcedAction) {
    takeAction(r.forcedAction, r.state, r.events)
    return
  }
  const m = r.state.monster
  if (m) weekNews.value = [...weekNews.value, ...eventLines(r.events, m)]
  commit(r.state)
}

/** The one action of the week. Drills open the result screen; everything else ends the week at once. */
export function takeAction(action: WeekAction, from: GameState | null = game.value, priorEvents: WeekEvent[] = []): void {
  const g = from
  if (!g || !g.monster) return
  const before = g.monster
  const r = chooseAction(g, action, rng)
  const events = [...priorEvents, ...r.events]
  if (r.drill) {
    flow.value = { kind: 'result', drill: r.drill, before, state: r.state, events, line: drillLine(r.state.monster ?? before, r.drill), reaction: null }
    return
  }
  finish(r.state, events)
}

export function reactTo(reaction: Reaction): void {
  const f = flow.value
  if (f.kind !== 'result' || f.reaction) return
  const state = react(f.state, f.drill.outcome, reaction)
  flow.value = { ...f, state, reaction }
}

/** Leaves the result screen (after a reaction, or skipping it) and ends the week. */
export function closeResult(): void {
  const f = flow.value
  if (f.kind !== 'result') return
  const state = f.reaction ? f.state : react(f.state, f.drill.outcome, 'skip')
  finish(state, [...f.events, { kind: 'reaction', reaction: f.reaction ?? 'skip' }])
}

function finish(state: GameState, events: WeekEvent[]): void {
  const r = finishWeek(state, rng)
  const all = [...events, ...r.events]
  const m = r.state.monster ?? state.monster
  const lines = m ? eventLines(all, m) : []
  const aging = all.flatMap((e) => (e.kind === 'aging' ? [e.event] : []))
  const fees = all.reduce((sum, e) => (e.kind === 'fees' ? sum + e.amount : sum), 0)
  const grewUp = m !== null && aging.some((e) => e.kind === 'prime') && growsUpAtPrime(m)
  weekNews.value = []
  commit(r.state)
  if (lines.length === 0 && fees === 0 && !r.state.ended) {
    flow.value = { kind: 'idle' }
    settle()
    return
  }
  flow.value = { kind: 'summary', lines, aging, fees, grewUp, ended: r.state.ended }
}

/** Closes the end-of-week summary and lets the next week begin. */
export function nextWeek(): void {
  flow.value = { kind: 'idle' }
  settle()
}

/** Ends the current week with no action of its own (a cup or Trial already was the action). */
export function endWeekNow(): void {
  const g = game.value
  if (!g || g.weekPhase !== 'action') return
  finish(g, [])
}

/** Runs something that needs the game's RNG (a Trial opponent, a cup's finish) and commits the result. */
export function withRng<T>(fn: (rng: Rng) => T): T {
  return fn(rng)
}

export function openTrain(): void {
  if (flow.value.kind === 'idle') flow.value = { kind: 'train' }
}

export function closeTrain(): void {
  if (flow.value.kind === 'train') flow.value = { kind: 'idle' }
}

export const menu = computed(() => (game.value ? actionMenu(game.value) : null))

/* ---------- free actions ---------- */

export function useItems(itemId: string, qty: number, stat?: StatKey): { used: number; result: UseItemResult | null } {
  const g = game.value
  if (!g) return { used: 0, result: null }
  const r = useItemsCore(g, itemId, qty, stat)
  if (r.used > 0) commit(r.state)
  return { used: r.used, result: r.result }
}

export function buy(itemId: string, qty: number): { cost: number; refused: BuyRefusal | null } {
  const g = game.value
  if (!g) return { cost: 0, refused: 'unknownItem' }
  const r = buyItem(g, itemId, qty)
  if (!r.refused) commit(r.state)
  return { cost: r.cost, refused: r.refused }
}

export function buySongsheet(techId: string): { cost: number; refused: SheetRefusal | null } {
  const g = game.value
  if (!g) return { cost: 0, refused: 'unknown' }
  const r = buySheet(g, techId)
  if (!r.refused) commit(r.state)
  return { cost: r.cost, refused: r.refused }
}

export function learn(techId: string, forgetId?: string): LearnStatus | 'notOwned' {
  const g = game.value
  if (!g) return 'unknownTechnique'
  const r = learnFromSongbook(g, techId, forgetId)
  if (r.status === 'learned') commit(r.state)
  return r.status
}

export function forget(techId: string): void {
  const g = game.value
  if (!g) return
  commit(forgetFromCard(g, techId))
}

/** The Lab editor saved the active monster. */
export function replaceMonster(edited: Monster): void {
  const g = game.value
  if (!g) return
  commit(replaceActiveMonster(g, edited, now()))
}

export function setDifficulty(to: Difficulty): boolean {
  const g = game.value
  if (!g) return false
  const next = switchDifficulty(g, to)
  if (next === g) return false
  commit(next)
  return true
}

export function setOnePerWeek(on: boolean): void {
  const g = game.value
  if (!g) return
  commit({ ...g, settings: { ...g.settings, onePerWeek: on } })
}

/** §19 Sandbox tools: marks the ranch. */
export function sandboxAddMoney(amount: number): void {
  const g = game.value
  if (!g) return
  commit({ ...g, money: g.money + amount, sandbox: true })
}

/* ---------- onboarding ---------- */

export function tipFor(ctx: TipContext): TipId | null {
  const g = game.value
  return g ? nextTip(g, ctx) : null
}

export function dismissTip(id: TipId): void {
  const g = game.value
  if (!g) return
  const next = markTipSeen(g, id)
  if (next !== g) commit(next)
}

/** For tests: a fresh in-memory game without storage. */
export function resetGameStoreForTests(): void {
  game.value = null
  flow.value = { kind: 'idle' }
  weekNews.value = []
  rng = createRng(0)
}

/* ---------- M6: the Freezer, the farewell, Heartstones, Fusion, the Shrine and the Market ---------- */

export function freezeActive(): FreezeRefusal | null {
  const g = game.value
  if (!g) return 'noMonster'
  const r = freezeActiveCore(g)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function makeActive(id: string): ThawRefusal | null {
  const g = game.value
  if (!g) return 'notFound'
  const r = makeActiveCore(g, id)
  if (!r.refused) {
    flow.value = { kind: 'idle' }
    weekNews.value = []
    commit(r.state)
  }
  return r.refused
}

/** The Lab's Make active for a monster that is not on this ranch yet (a Library creation or a preset). */
export function adoptMonster(m: Monster): AdoptRefusal | null {
  const g = game.value
  if (!g) return 'ended'
  const r = adoptCore(g, m)
  if (!r.refused) {
    flow.value = { kind: 'idle' }
    weekNews.value = []
    commit(r.state)
  }
  return r.refused
}

export function sendToFreezer(m: Monster): SendRefusal | null {
  const g = game.value
  if (!g) return 'full'
  const r = sendToFreezerCore(g, m)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function releaseStored(id: string): void {
  const g = game.value
  if (!g) return
  const next = releaseStoredCore(g, id)
  if (next !== g) commit(next)
}

/** The Lab editor saved a frozen monster. */
export function replaceStored(edited: Monster): void {
  const g = game.value
  if (!g) return
  const next = replaceStoredCore(g, edited)
  if (next !== g) commit(next)
}

export function concludeLife(epitaph: string): ConcludeResult | null {
  const g = game.value
  if (!g) return null
  const r = concludeLifeCore(g, epitaph)
  if (r) {
    flow.value = { kind: 'idle' }
    weekNews.value = []
    commit(r.state)
  }
  return r
}

export function giveHeartstone(stoneId: string, targetId?: string): GiveRefusal | null {
  const g = game.value
  if (!g) return 'noTarget'
  const r = giveHeartstoneCore(g, stoneId, targetId)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function editMemorial(id: string, name: string, epitaph: string): void {
  const g = game.value
  if (!g) return
  const next = editMemorialCore(g, id, name, epitaph)
  if (next !== g) commit(next)
}

export function fuse(id1: string, id2: string, catalystId: string | null): FuseOutput | null {
  const g = game.value
  if (!g) return null
  const r = fuseCore(g, id1, id2, catalystId, newId(), rng)
  if (!r.refused) {
    flow.value = { kind: 'idle' }
    weekNews.value = []
    commit(r.state)
  }
  return r
}

export function awaken(phrase: string, artist: string): AwakenResult | null {
  const g = game.value
  if (!g) return null
  const r = awakenCore(g, phrase, artist, newId())
  if (r.state !== g) {
    flow.value = { kind: 'idle' }
    weekNews.value = []
    commit(r.state)
  }
  return r
}

export function recreate(index: number): ReturnType<typeof recreateCore> | null {
  const g = game.value
  if (!g) return null
  const r = recreateCore(g, index, newId())
  if (!r.refused) {
    flow.value = { kind: 'idle' }
    commit(r.state)
  }
  return r
}

export function wakeStone(index: number): ReturnType<typeof wakeStoneCore> | null {
  const g = game.value
  if (!g) return null
  const r = wakeStoneCore(g, index, newId())
  if (!r.refused) {
    flow.value = { kind: 'idle' }
    commit(r.state)
  }
  return r
}

export function buyFromMarket(breed: BreedId): ReturnType<typeof buyFromMarketCore> | null {
  const g = game.value
  if (!g) return null
  const r = buyFromMarketCore(g, breed, newId())
  if (!r.refused) {
    flow.value = { kind: 'idle' }
    commit(r.state)
  }
  return r
}

/** Randomize at the Shrine: draws from the game's RNG so it is saved with everything else. */
export function randomPhrase(): string {
  const phrase = randomPhraseCore(rng, SHRINE_WORDS)
  void persist()
  return phrase
}

/* ---------- M7: expeditions, events, offerings, upgrades, Odd Jobs, selling ---------- */

/** Yes to the storm spark is the week's action; no just clears the card. */
export function answerEvent(accept: boolean): void {
  const g = game.value
  if (!g?.pendingEvent) return
  if (accept) takeAction({ kind: 'event' })
  else commit(answerEventCore(g, false, rng).state)
}

/** Sets off: the week's action, then the map screen. The week ends from the map's summary (`endWeekNow`). */
export function startExpeditionTrip(site: ExpeditionSiteId): boolean {
  const g = game.value
  if (!g?.monster) return false
  const r = chooseAction(g, { kind: 'expedition', site }, rng)
  if (!r.state.expedition) return false
  weekNews.value = [...weekNews.value, ...eventLines(r.events, r.state.monster ?? g.monster)]
  commit(r.state)
  return true
}

export function expeditionMove(nodeId: number): MoveRefusal | null {
  const g = game.value
  if (!g) return 'noTrip'
  const r = moveToCore(g, nodeId, rng)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function expeditionDetour(): void {
  const g = game.value
  if (!g) return
  const r = detourCore(g)
  if (!r.refused) commit(r.state)
}

export function expeditionTurnBack(): void {
  const g = game.value
  if (!g) return
  const r = turnBackCore(g)
  if (!r.refused) commit(r.state)
}

export function expeditionRetreat(): void {
  const g = game.value
  if (!g) return
  const r = retreatCore(g)
  if (!r.refused) commit(r.state)
}

export function offerAtShrine(itemId: string): { refused: OfferRefusal | null; breed: string | null } {
  const g = game.value
  if (!g) return { refused: 'notOwned', breed: null }
  const r = offerAtShrineCore(g, itemId)
  if (!r.refused) commit(r.state)
  return { refused: r.refused, breed: r.breed }
}

export function giveBlueprint(): BlueprintRefusal | null {
  const g = game.value
  if (!g) return 'notOwned'
  const r = giveBlueprintCore(g)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function attendVigil(): boolean {
  const g = game.value
  if (!g) return false
  const r = attendVigilCore(g)
  if (!r.refused) commit(r.state)
  return r.refused === null
}

export function buyUpgrade(id: UpgradeId): UpgradeRefusal | null {
  const g = game.value
  if (!g) return 'unknown'
  const r = buyUpgradeCore(g, id)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function visitGarden(): GardenRefusal | null {
  const g = game.value
  if (!g) return 'noMonster'
  const r = visitGardenCore(g)
  if (!r.refused) commit(r.state)
  return r.refused
}

export function sell(itemId: string, qty: number): { gold: number; refused: SellRefusal | null } {
  const g = game.value
  if (!g) return { gold: 0, refused: 'unknownItem' }
  const r = sellItemCore(g, itemId, qty)
  if (!r.refused) commit(r.state)
  return { gold: r.gold, refused: r.refused }
}

/** The Turnip Sort round's seed comes from the game's RNG, so the chute is part of the save's story. */
export function oddJobSeed(): number {
  const seed = rng.nextU32()
  void persist()
  return seed
}

export function finishOddJob(correct: number, wrong: number): number {
  const g = game.value
  if (!g) return 0
  const r = applyOddJobCore(g, correct, wrong)
  if (!r.refused) commit(r.state)
  return r.pay
}
