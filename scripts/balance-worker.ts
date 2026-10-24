/**
 * Worker for scripts/balance.ts: runs one raising task (a breed × policy over some seeds) or one battle cell
 * (two breeds at a total over some seeds) and posts the result back. Pure core code only.
 */
import { parentPort } from 'node:worker_threads'
import type { BreedId } from '../src/data/types.ts'
import { npcMonster } from '../src/core/npc.ts'
import { runBattle, timerTicksFor } from '../src/core/battle/engine.ts'
import type { FighterSetup } from '../src/core/battle/types.ts'
import type { Monster } from '../src/core/monster.ts'
import { simulateLife, type LifeReport, type PolicyName } from '../src/core/sim/lifeSim.ts'

export type RaiseTask = { kind: 'raise'; breed: BreedId; policy: PolicyName; seeds: number[] }
export type BattleTask = { kind: 'battle'; a: BreedId; b: BreedId; total: number; seeds: number; variants: number }
export type Task = RaiseTask | BattleTask

export interface RaiseSlim {
  lifeLivedPct: number
  finalTotal: number
  breakdowns: number
  endedBy: LifeReport['endedBy']
  outcomes: LifeReport['outcomes']
  drills: number
  totalsByYear: number[]
}

export interface BattleCell {
  a: BreedId
  b: BreedId
  total: number
  seeds: number
  winA: number
  winB: number
  draw: number
  koA: number
  koB: number
  attacksA: number
  attacksB: number
}

export type TaskResult = { kind: 'raise'; breed: BreedId; policy: PolicyName; lives: RaiseSlim[] } | { kind: 'battle'; cell: BattleCell }

const ai = (monster: Monster): FighterSetup => ({ monster, control: 'ai', personality: 'Steady' })

function runRaise(t: RaiseTask): TaskResult {
  const lives = t.seeds.map((seed) => {
    const r = simulateLife({ breed: t.breed, policy: t.policy, seed })
    return {
      lifeLivedPct: r.lifeLivedPct,
      finalTotal: r.finalTotal,
      breakdowns: r.breakdowns,
      endedBy: r.endedBy,
      outcomes: r.outcomes,
      drills: r.drills,
      totalsByYear: r.years.map((y) => y.total),
    }
  })
  return { kind: 'raise', breed: t.breed, policy: t.policy, lives }
}

/**
 * A's results over `seeds` battles, sides alternating. Each side draws from `variants` NPC rolls of its breed
 * (stat noise, loyalty, kit) so a cell measures the breed, not one lucky roll. A mirror uses identical twins.
 */
function runBattleCell(t: BattleTask): TaskResult {
  const mirror = t.a === t.b
  const as: Monster[] = []
  const bs: Monster[] = []
  for (let v = 0; v < t.variants; v++) {
    const a = npcMonster({ breed: t.a, total: t.total, seed: 1000 + t.total + v })
    as.push(a)
    bs.push(mirror ? structuredClone(a) : npcMonster({ breed: t.b, total: t.total, seed: 2000 + t.total + v }))
  }
  const ticks = timerTicksFor(60)
  let winA = 0
  let winB = 0
  let draw = 0
  let koA = 0
  let koB = 0
  let attacksA = 0
  let attacksB = 0
  for (let seed = 0; seed < t.seeds; seed++) {
    const a = as[seed % t.variants]!
    const b = bs[seed % t.variants]!
    const swapped = seed % 2 === 1
    const r = swapped ? runBattle(ai(b), ai(a), { seed, timerTicks: ticks }) : runBattle(ai(a), ai(b), { seed, timerTicks: ticks })
    const sideA = swapped ? 1 : 0
    if (r.outcome.winner === null) draw++
    else if (r.outcome.winner === sideA) {
      winA++
      if (r.outcome.how === 'ko') koA++
    } else {
      winB++
      if (r.outcome.how === 'ko') koB++
    }
    attacksA += r.fighters[sideA]!.attacks
    attacksB += r.fighters[1 - sideA]!.attacks
  }
  return { kind: 'battle', cell: { a: t.a, b: t.b, total: t.total, seeds: t.seeds, winA, winB, draw, koA, koB, attacksA, attacksB } }
}

export function runTask(t: Task): TaskResult {
  return t.kind === 'raise' ? runRaise(t) : runBattleCell(t)
}

if (parentPort) {
  const port = parentPort
  port.on('message', (msg: { id: number; task: Task }) => {
    port.postMessage({ id: msg.id, result: runTask(msg.task) })
  })
}
