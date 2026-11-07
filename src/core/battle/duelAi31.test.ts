import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { AI } from '../../data/tuning.ts'
import type { AiTier, Personality } from '../../data/types.ts'
import { npcMonster } from '../npc.ts'
import { canFire, createBattle, currentBand, effectiveCost, previewHitTenths, step, timerTicksFor, type Battle } from './engine.ts'
import { NO_BAR, isOpen, shotScore, shotThreshold } from './duelShot.ts'
import type { BattleEvent, BattleInput, FighterSetup, FighterState } from './types.ts'

/** docs/BATTLE_3D.md §4.9 AI 3.1, human qualities (v1.22): intents, the shot score, the human reaction, set-ups. */

const H = AI.duel.human
const BREEDS = ['puddlepup', 'quillion', 'cobblemaw', 'galeheron', 'gloomgrin'] as const
const duel = (seed: number) => ({ seed, timerTicks: timerTicksFor(60), mode: 'duel' as const })
const cpu = (breed: (typeof BREEDS)[number], seed: number, tier: AiTier, personality: Personality = 'Steady'): FighterSetup => ({ monster: npcMonster({ breed, total: 1600, seed }), control: 'ai', personality, habit: 'none', tier })

/** A plain human: every 6 ticks it fires its strongest ready card, else walks in. */
function human(b: Battle, moving: { dir: number }): BattleInput[] {
  const st = b.state
  const me = st.fighters[0]
  if (st.tick % 6 !== 0) return []
  const ready = me.techniques.filter((t) => canFire(st, me, t.id)).sort((x, y) => (TECHNIQUE_BY_ID[y.id]?.force ?? 0) - (TECHNIQUE_BY_ID[x.id]?.force ?? 0))
  if (ready[0]) return [{ tick: st.tick + 1, side: 0, action: { kind: 'fire', tech: ready[0].id } }]
  const dir = currentBand(st) > 1 ? 1 : 0
  if (dir === moving.dir) return []
  moving.dir = dir
  return [{ tick: st.tick + 1, side: 0, action: { kind: 'move', dir: dir as 0 | 1 } }]
}

/** Has an affordable technique for the band it stands in. */
function inRange(b: Battle, f: FighterState): boolean {
  const band = currentBand(b.state)
  return f.techniques.some((t) => {
    const tech = TECHNIQUE_BY_ID[t.id]
    return tech !== undefined && tech.range === band && f.guts >= effectiveCost(f, tech)
  })
}

interface Watch {
  fires: number
  hitSum: number
  /** Ticks from entering range to each fire that wasn't into an opening. */
  delays: number[]
}

/** The CPU (side 1) against the plain human; `each` sees every tick before it is stepped. */
function vsHuman(setup: FighterSetup, seed: number, each?: (b: Battle, events: BattleEvent[]) => void): { b: Battle; w: Watch } {
  const me: FighterSetup = { monster: npcMonster({ breed: setup.monster.mainBreed, total: 1600, seed: seed + 1 }), control: 'player', personality: 'Steady' }
  const b = createBattle(me, setup, duel(seed))
  const w: Watch = { fires: 0, hitSum: 0, delays: [] }
  const moving = { dir: 0 }
  let since = -1
  while (!b.state.outcome) {
    const f = b.state.fighters[1]
    const opp = b.state.fighters[0]
    if (!inRange(b, f)) since = -1
    else if (since < 0) since = b.state.tick + 1
    const open = isOpen(opp)
    const hit: Record<string, number> = {}
    for (const t of f.techniques) hit[t.id] = previewHitTenths(b.state, 1, t.id)
    const events = step(b, human(b, moving))
    for (const e of events) {
      if (e.kind !== 'fire' || e.side !== 1) continue
      w.fires++
      w.hitSum += hit[e.tech] ?? 0
      if (!open && since >= 0) w.delays.push(e.t - since)
    }
    each?.(b, events)
  }
  return { b, w }
}

describe('AI 3.1 human qualities (docs/BATTLE_3D.md §4.9)', () => {
  it('never fires within the human reaction of entering range, unless punishing an opening', () => {
    const n = H.react.quick.min
    let checked = 0
    for (const tier of ['rookie', 'skilled', 'expert'] as const) {
      for (const [i, p] of (['Steady', 'Aggressive', 'Cautious', 'Trickster'] as const).entries()) {
        const { w } = vsHuman(cpu(BREEDS[i % BREEDS.length]!, 40 + i, tier, p), 600 + i)
        for (const d of w.delays) expect(d).toBeGreaterThanOrEqual(n)
        checked += w.delays.length
      }
    }
    expect(checked).toBeGreaterThan(60)
  })

  it('the bar falls to its floor as patience runs out, then lets any shot go; experts wait longer than rookies', () => {
    const f = { sense: 85 } as FighterState
    const r = { sense: 25 } as FighterState
    const t0 = shotThreshold(f, 0, 'steady')
    expect(shotThreshold(f, 20, 'steady')).toBeLessThan(t0)
    expect(shotThreshold(f, 20, 'steady')).toBeGreaterThanOrEqual(H.threshold.floor)
    expect(shotThreshold(f, 1_000, 'steady')).toBe(NO_BAR)
    expect(shotThreshold(r, 0, 'steady')).toBeLessThan(t0)
    const runsOut = (x: FighterState, style: 'steady' | 'rusher' | 'careful') => {
      let t = 0
      while (shotThreshold(x, t, style) !== NO_BAR) t++
      return t
    }
    expect(runsOut(f, 'steady')).toBeGreaterThan(runsOut(r, 'steady'))
    expect(runsOut(f, 'careful')).toBeGreaterThan(runsOut(f, 'rusher'))
    expect(shotThreshold(f, 0, 'rusher')).toBeLessThan(shotThreshold(f, 0, 'careful'))
  })

  it('an opponent that is open scores higher than a fresh one that can sidestep a straight line', () => {
    const b = createBattle(cpu('puddlepup', 1, 'expert'), cpu('puddlepup', 2, 'expert'), duel(1))
    const [f, opp] = b.state.fighters
    const line = f.techniques.map((t) => TECHNIQUE_BY_ID[t.id]!).find((t) => t.force > 0 && t.family !== 'Wither')!
    const fresh = shotScore(b.state, f, opp, line)
    opp.busyTicks = 10
    expect(shotScore(b.state, f, opp, line)).toBeGreaterThan(fresh + 10)
    // a rookie reads the moment far less
    opp.busyTicks = 0
    const rook = { ...f, sense: 25 }
    const rookFresh = shotScore(b.state, rook, opp, line)
    opp.busyTicks = 10
    expect(shotScore(b.state, rook, opp, line) - rookFresh).toBeLessThan(shotScore(b.state, f, opp, line) - fresh)
  })

  it('attacks per match stay within 4–12 for every tier', () => {
    for (const tier of ['rookie', 'skilled', 'expert'] as const) {
      let fires = 0
      const N = 10
      for (let s = 0; s < N; s++) fires += vsHuman(cpu(BREEDS[s % BREEDS.length]!, 70 + s, tier), 900 + s).w.fires
      expect(fires / N).toBeGreaterThanOrEqual(4)
      expect(fires / N).toBeLessThanOrEqual(12)
    }
  })

  it('holding a shot keeps the plan: no new pick, the cooldown only runs down, few shots are lost', () => {
    let taken = 0
    let dropped = 0
    let held = 0
    for (let s = 0; s < 8; s++) {
      const a = cpu(BREEDS[s % BREEDS.length]!, 20 + s, 'expert')
      const b = createBattle(a, cpu(BREEDS[(s + 2) % BREEDS.length]!, 30 + s, 'expert'), duel(100 + s))
      const f = b.state.fighters[0]
      while (!b.state.outcome) {
        const before = { intent: f.shot!.intent, taken: f.shot!.taken, cd: f.aiCooldown, goal: f.aiGoal }
        step(b)
        if (before.intent === null || f.shot!.intent !== before.intent || f.shot!.taken !== before.taken) continue
        held++
        expect(f.aiFireTech).toBeNull()
        expect(f.aiCooldown).toBeLessThanOrEqual(Math.max(before.cd - 1, 2))
      }
      taken += f.shot!.taken
      dropped += f.shot!.dropped
    }
    expect(held).toBeGreaterThan(100)
    expect(dropped * 100).toBeLessThanOrEqual(taken * 10)
  })

  it('a rookie takes the first shot it gets; an expert waits for one the opponent cannot dodge', () => {
    const b = createBattle(cpu('puddlepup', 1, 'expert'), cpu('puddlepup', 2, 'expert'), duel(1))
    const [f, opp] = b.state.fighters
    const line = f.techniques.map((t) => TECHNIQUE_BY_ID[t.id]!).find((t) => t.force > 0 && t.family !== 'Wither')!
    const rookie = { ...f, sense: AI.duel.sense.tier.rookie }
    // the opponent is fresh, with a sidestep ready
    expect(shotScore(b.state, rookie, opp, line)).toBeGreaterThanOrEqual(shotThreshold(rookie, 0, 'steady'))
    expect(shotScore(b.state, f, opp, line)).toBeLessThan(shotThreshold(f, 0, 'steady'))
    // it commits: recovering, it can't dodge
    opp.busyTicks = 10
    expect(shotScore(b.state, f, opp, line)).toBeGreaterThanOrEqual(shotThreshold(f, 0, 'steady'))
  })

  it('is deterministic with every style and a human on the other side', () => {
    for (const [i, p] of (['Aggressive', 'Cautious', 'Trickster'] as const).entries()) {
      const run = () => vsHuman(cpu(BREEDS[i]!, 60 + i, i === 0 ? 'rookie' : 'expert', p), 700 + i).b.state.log
      expect(run()).toEqual(run())
    }
  })
})
