import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import type { BattleResult, Side } from './types.ts'

/**
 * GAME_DESIGN §19 Battle Lab numbers: win / draw / KO %, average length, damage per hit, hit rates and the
 * most-used techniques, per side. `swapped` says the battle was fought with the monsters on exchanged sides
 * (alternating sides, §26), so the numbers are mapped back to "A" and "B".
 */

export interface SideStats {
  wins: number
  koWins: number
  attacks: number
  hits: number
  damage: number
  techUses: Record<string, number>
}

export interface LabStats {
  battles: number
  draws: number
  totalTicks: number
  sides: [SideStats, SideStats]
}

export interface LabSummary {
  battles: number
  winPct: [number, number]
  drawPct: number
  koPct: [number, number]
  avgSeconds: number
  attacksPerBattle: [number, number]
  hitRatePct: [number, number]
  damagePerHit: [number, number]
  topTechniques: [{ id: string; name: string; uses: number }[], { id: string; name: string; uses: number }[]]
}

export function emptyStats(): LabStats {
  return { battles: 0, draws: 0, totalTicks: 0, sides: [{ wins: 0, koWins: 0, attacks: 0, hits: 0, damage: 0, techUses: {} }, { wins: 0, koWins: 0, attacks: 0, hits: 0, damage: 0, techUses: {} }] }
}

/** Adds one result. With `swapped`, the result's side 0 is monster B. */
export function addResult(stats: LabStats, r: BattleResult, swapped: boolean): void {
  stats.battles += 1
  stats.totalTicks += r.outcome.ticks
  if (r.outcome.winner === null) stats.draws += 1
  for (const f of r.fighters) {
    const who = (swapped ? 1 - f.side : f.side) as Side
    const s = stats.sides[who]
    s.attacks += f.attacks
    s.hits += f.hits
    s.damage += f.damageDealt
    for (const [id, n] of Object.entries(f.techUses)) s.techUses[id] = (s.techUses[id] ?? 0) + n
    if (r.outcome.winner === f.side) {
      s.wins += 1
      if (r.outcome.how === 'ko') s.koWins += 1
    }
  }
}

const pct = (n: number, d: number) => (d > 0 ? Math.round((n * 1000) / d) / 10 : 0)

export function summarize(stats: LabStats, ticksPerSecond: number): LabSummary {
  const [a, b] = stats.sides
  const top = (s: SideStats) =>
    Object.entries(s.techUses)
      .sort((x, y) => y[1] - x[1])
      .slice(0, 3)
      .map(([id, uses]) => ({ id, name: TECHNIQUE_BY_ID[id]?.name ?? id, uses }))
  return {
    battles: stats.battles,
    winPct: [pct(a.wins, stats.battles), pct(b.wins, stats.battles)],
    drawPct: pct(stats.draws, stats.battles),
    koPct: [pct(a.koWins, stats.battles), pct(b.koWins, stats.battles)],
    avgSeconds: stats.battles ? Math.round((stats.totalTicks * 10) / stats.battles / ticksPerSecond) / 10 : 0,
    attacksPerBattle: [stats.battles ? Math.round((a.attacks * 10) / stats.battles) / 10 : 0, stats.battles ? Math.round((b.attacks * 10) / stats.battles) / 10 : 0],
    hitRatePct: [pct(a.hits, a.attacks), pct(b.hits, b.attacks)],
    damagePerHit: [a.hits ? Math.round(a.damage / a.hits) : 0, b.hits ? Math.round(b.damage / b.hits) : 0],
    topTechniques: [top(a), top(b)],
  }
}

/** A small CSV for sharing Battle Lab runs. */
export function toCsv(nameA: string, nameB: string, s: LabSummary): string {
  const lines = [
    'metric,A,B',
    `name,${csv(nameA)},${csv(nameB)}`,
    `battles,${s.battles},${s.battles}`,
    `win %,${s.winPct[0]},${s.winPct[1]}`,
    `draw %,${s.drawPct},${s.drawPct}`,
    `ko %,${s.koPct[0]},${s.koPct[1]}`,
    `avg seconds,${s.avgSeconds},${s.avgSeconds}`,
    `attacks per battle,${s.attacksPerBattle[0]},${s.attacksPerBattle[1]}`,
    `hit rate %,${s.hitRatePct[0]},${s.hitRatePct[1]}`,
    `damage per hit,${s.damagePerHit[0]},${s.damagePerHit[1]}`,
    `top techniques,${csv(s.topTechniques[0].map((t) => `${t.name} (${t.uses})`).join('; '))},${csv(s.topTechniques[1].map((t) => `${t.name} (${t.uses})`).join('; '))}`,
  ]
  return lines.join('\n') + '\n'
}

function csv(text: string): string {
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}
