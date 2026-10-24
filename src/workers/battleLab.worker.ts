import { runBattle, timerTicksFor } from '../core/battle/engine.ts'
import { addResult, emptyStats, summarize, type LabSummary } from '../core/battle/stats.ts'
import type { Monster } from '../core/monster.ts'
import { createRng } from '../core/rng.ts'
import { BATTLE } from '../data/tuning.ts'
import type { Personality } from '../data/types.ts'

/**
 * GAME_DESIGN §19 Battle Lab: runs N battles between two monsters in the background, sides alternating
 * every battle, and reports progress every few fights. Pure core only: no DOM in here.
 */

export interface LabRequest {
  type: 'run'
  a: Monster
  b: Monster
  battles: number
  seed: number
  personalityA: Personality
  personalityB: Personality
  timerSec: number
}

export type LabResponse = { type: 'progress'; done: number; total: number } | { type: 'done'; summary: LabSummary; seed: number }

const PROGRESS_EVERY = 25

/** The whole run, usable without a worker too (tests, browsers without module workers). */
export function runLab(req: LabRequest, onProgress?: (done: number, total: number) => void): LabSummary {
  const stats = emptyStats()
  const seeds = createRng(req.seed)
  for (let i = 0; i < req.battles; i++) {
    const seed = seeds.nextU32()
    const swapped = i % 2 === 1
    const opts = { seed, timerTicks: timerTicksFor(req.timerSec) }
    // §12.10: the Lab is a fair test, so both brains are expert.
    const r = swapped
      ? runBattle({ monster: req.b, control: 'ai', personality: req.personalityB, tier: 'expert' }, { monster: req.a, control: 'ai', personality: req.personalityA, tier: 'expert' }, opts)
      : runBattle({ monster: req.a, control: 'ai', personality: req.personalityA, tier: 'expert' }, { monster: req.b, control: 'ai', personality: req.personalityB, tier: 'expert' }, opts)
    addResult(stats, r, swapped)
    if (onProgress && ((i + 1) % PROGRESS_EVERY === 0 || i + 1 === req.battles)) onProgress(i + 1, req.battles)
  }
  return summarize(stats, BATTLE.ticksPerSecond)
}

// Only a real worker has WorkerGlobalScope; the page (fallback import) and Node (tests) just get `runLab`.
const g = globalThis as unknown as { WorkerGlobalScope?: unknown; onmessage?: ((e: MessageEvent<LabRequest>) => void) | null; postMessage?: (msg: LabResponse) => void }
if (typeof g.WorkerGlobalScope !== 'undefined' && typeof g.postMessage === 'function') {
  g.onmessage = (e) => {
    const req = e.data
    if (req.type !== 'run') return
    const summary = runLab(req, (done, total) => g.postMessage!({ type: 'progress', done, total }))
    g.postMessage!({ type: 'done', summary, seed: req.seed })
  }
}
