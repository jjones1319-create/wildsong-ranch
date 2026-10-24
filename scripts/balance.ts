/**
 * M9 balance matrices (GAME_DESIGN §26), run across worker threads and written to docs/BALANCE_REPORT.md.
 *   npm run sim:balance -- [--seeds 40] [--battles 200] [--only raise|battle] [--totals 1000,2000,3000] [--out docs/BALANCE_REPORT.md] [--json path]
 * Raising: every breed under the four care policies. Battle: every breed pair (mirrors included) at totals
 * 1,000 / 2,000 / 3,000, Expert vs Expert (M10), sides alternating. Runs on Node 24 directly (type stripping), no build step.
 */
import { availableParallelism } from 'node:os'
import { writeFileSync } from 'node:fs'
import { Worker } from 'node:worker_threads'
import { BREED_BY_ID } from '../src/data/breeds.ts'
import { BREED_IDS, type BreedId } from '../src/data/types.ts'
import type { PolicyName } from '../src/core/sim/lifeSim.ts'
import type { BattleCell, RaiseSlim, Task, TaskResult } from './balance-worker.ts'

const args = process.argv.slice(2)
const flag = (name: string, fallback: string) => {
  const i = args.indexOf(`--${name}`)
  return i >= 0 && args[i + 1] ? args[i + 1]! : fallback
}
const SEEDS = Number(flag('seeds', '40'))
const BATTLES = Number(flag('battles', '200'))
const ONLY = flag('only', 'both')
const OUT = flag('out', 'docs/BALANCE_REPORT.md')
const JSON_OUT = flag('json', '')
const VARIANTS = 8
const TOTALS = flag('totals', '1000,2000,3000').split(',').map(Number)
const POLICIES: PolicyName[] = ['Great', 'Good', 'OK', 'Neglect']

/** §26 bands. */
const LIFE_BAND: Record<PolicyName, [number, number]> = { Great: [82, 92], Good: [76, 88], OK: [62, 78], Neglect: [25, 45] }
const OUTCOME_BAND = { Great: [17, 23], Success: [55, 65], Cheat: [7, 12], Fail: [8, 14] } as const
const PAIR_BAND: [number, number] = [30, 70]
/** M10: no pair may sit outside this, and at least PAIR_INSIDE_PCT of pairs must be inside PAIR_BAND. */
const PAIR_HARD_BAND: [number, number] = [25, 75]
const PAIR_INSIDE_PCT = 95
/** M10: a breed's mean win share against the others is flagged in the table; the spec makes it a target for Lootlid only. */
const MEAN_BAND: [number, number] = [40, 60]
const MEAN_TARGETS: BreedId[] = ['lootlid']
const MIRROR_BAND: [number, number] = [45, 55]
/** §26 "even fights": the five starters' mirrors, like balance.test.ts (glass cannons KO each other by design). */
const KO_BAND: Record<number, [number, number]> = { 1000: [15, 35], 3000: [3, 15] }
const KO_PROBES: BreedId[] = ['puddlepup', 'tumblefox', 'quillion', 'pluckrex', 'cobblemaw']
const ATTACK_BAND: [number, number] = [4, 12]
const started = Date.now()

/* ---------- task list ---------- */

const tasks: Task[] = []
if (ONLY !== 'battle') {
  const chunk = 10
  for (const breed of BREED_IDS)
    for (const policy of POLICIES)
      for (let s = 0; s < SEEDS; s += chunk) tasks.push({ kind: 'raise', breed, policy, seeds: Array.from({ length: Math.min(chunk, SEEDS - s) }, (_, i) => 1000 + s + i) })
}
if (ONLY !== 'raise') {
  for (const total of TOTALS)
    for (let i = 0; i < BREED_IDS.length; i++)
      for (let j = i; j < BREED_IDS.length; j++) tasks.push({ kind: 'battle', a: BREED_IDS[i]!, b: BREED_IDS[j]!, total, seeds: BATTLES, variants: VARIANTS })
}

/* ---------- run across workers ---------- */

async function runAll(list: Task[]): Promise<TaskResult[]> {
  const n = Math.max(1, Math.min(availableParallelism() - 1, list.length))
  const results: TaskResult[] = []
  let next = 0
  let done = 0
  const started = Date.now()
  const tick = () => {
    if (done % 50 === 0 || done === list.length) process.stderr.write(`\r${done}/${list.length} tasks · ${Math.round((Date.now() - started) / 1000)}s   `)
  }
  await Promise.all(
    Array.from({ length: n }, () => {
      const w = new Worker(new URL('./balance-worker.ts', import.meta.url))
      return new Promise<void>((resolve, reject) => {
        const feed = () => {
          if (next >= list.length) {
            w.terminate().then(() => resolve(), reject)
            return
          }
          const id = next++
          w.postMessage({ id, task: list[id] })
        }
        w.on('message', (msg: { id: number; result: TaskResult }) => {
          results[msg.id] = msg.result
          done++
          tick()
          feed()
        })
        w.on('error', reject)
        feed()
      })
    }),
  )
  process.stderr.write('\n')
  return results
}

/* ---------- summaries ---------- */

interface RaiseSummary {
  breed: BreedId
  policy: PolicyName
  n: number
  lifeLivedPct: number
  breakdowns: number
  finalTotal: number
  totalsByYear: number[]
  outcomesPct: Record<string, number>
  retired: number
}

function summarizeRaise(breed: BreedId, policy: PolicyName, lives: RaiseSlim[]): RaiseSummary {
  const n = lives.length
  const avg = (f: (l: RaiseSlim) => number) => lives.reduce((s, l) => s + f(l), 0) / n
  const years: number[][] = []
  for (const l of lives) l.totalsByYear.forEach((t, i) => (years[i] ??= []).push(t))
  const drills = lives.reduce((s, l) => s + l.drills, 0)
  const outcomesPct: Record<string, number> = {}
  for (const k of ['Great', 'Success', 'Cheat', 'Fail', 'Slacked']) outcomesPct[k] = drills ? (lives.reduce((s, l) => s + (l.outcomes as Record<string, number>)[k]!, 0) * 100) / drills : 0
  return {
    breed,
    policy,
    n,
    lifeLivedPct: avg((l) => l.lifeLivedPct),
    breakdowns: avg((l) => l.breakdowns),
    finalTotal: avg((l) => l.finalTotal),
    totalsByYear: years.map((ys) => ys.reduce((a, b) => a + b, 0) / ys.length),
    outcomesPct,
    retired: lives.filter((l) => l.endedBy !== 'passed').length,
  }
}

const share = (c: BattleCell) => (c.winA + c.winB > 0 ? (c.winA * 100) / (c.winA + c.winB) : 50)
const pct = (n: number, of: number) => (of ? (n * 100) / of : 0)
const inBand = (v: number, [lo, hi]: readonly [number, number]) => v >= lo && v <= hi
const f1 = (v: number) => v.toFixed(1)
const f0 = (v: number) => String(Math.round(v))
const abbr = (id: BreedId) => BREED_BY_ID[id].name.slice(0, 3)

/* ---------- main ---------- */

const results = await runAll(tasks)

const raise = new Map<string, RaiseSummary>()
const raiseLives = new Map<string, RaiseSlim[]>()
const cells: BattleCell[] = []
for (const r of results) {
  if (r.kind === 'raise') {
    const key = `${r.breed}/${r.policy}`
    raiseLives.set(key, [...(raiseLives.get(key) ?? []), ...r.lives])
  } else cells.push(r.cell)
}
for (const [key, lives] of raiseLives) {
  const [breed, policy] = key.split('/') as [BreedId, PolicyName]
  raise.set(key, summarizeRaise(breed, policy, lives))
}

const lines: string[] = []
const misses: string[] = []
const today = new Date().toISOString().slice(0, 10)
lines.push('# Balance report', '', `Generated ${today} by \`npm run sim:balance\` (GAME_DESIGN §26). Raising: ${SEEDS} seeds per breed and policy, no Stat Sweets, Songsheets or edits. Battle: ${BATTLES} battles per cell, AI 2.0 Expert vs Expert (Steady), sides alternating, ${VARIANTS} NPC rolls per side, 60-second matches.`, '')

if (raise.size > 0) {
  lines.push('## Raising: life lived vs. nominal (%)', '', 'Targets: Great 82–92 · Good 76–88 · OK 62–78 · Neglect 25–45 (with several breakdowns). ✗ marks a cell outside its band.', '')
  lines.push('| Breed | Great | Good | OK | Neglect | Neglect breakdowns | Good total y1 / y3 / y5 | Good outcomes G / S / C / F % |', '|---|---|---|---|---|---|---|---|')
  for (const breed of BREED_IDS) {
    const row = POLICIES.map((p) => {
      const s = raise.get(`${breed}/${p}`)!
      const ok = inBand(s.lifeLivedPct, LIFE_BAND[p])
      if (!ok) misses.push(`Raising ${BREED_BY_ID[breed].name} ${p}: ${f1(s.lifeLivedPct)} % (band ${LIFE_BAND[p].join('–')})`)
      return `${f1(s.lifeLivedPct)}${ok ? '' : ' ✗'}`
    })
    const neg = raise.get(`${breed}/Neglect`)!
    const good = raise.get(`${breed}/Good`)!
    if (neg.breakdowns < 2) misses.push(`Raising ${BREED_BY_ID[breed].name} Neglect: ${f1(neg.breakdowns)} breakdowns per life (want ≥ 2)`)
    const o = good.outcomesPct
    const outcomeOk = inBand(o.Great!, OUTCOME_BAND.Great) && inBand(o.Success!, OUTCOME_BAND.Success) && inBand(o.Cheat!, OUTCOME_BAND.Cheat) && inBand(o.Fail!, OUTCOME_BAND.Fail)
    if (!outcomeOk) misses.push(`Raising ${BREED_BY_ID[breed].name} Good outcomes: G ${f1(o.Great!)} S ${f1(o.Success!)} C ${f1(o.Cheat!)} F ${f1(o.Fail!)}`)
    const y = (i: number) => (good.totalsByYear[i] !== undefined ? f0(good.totalsByYear[i]!) : '–')
    lines.push(`| ${BREED_BY_ID[breed].name} | ${row.join(' | ')} | ${f1(neg.breakdowns)} | ${y(0)} / ${y(2)} / ${y(4)} | ${f0(o.Great!)} / ${f0(o.Success!)} / ${f0(o.Cheat!)} / ${f0(o.Fail!)}${outcomeOk ? '' : ' ✗'} |`)
  }
  const avgOf = (p: PolicyName) => BREED_IDS.reduce((s, b) => s + raise.get(`${b}/${p}`)!.lifeLivedPct, 0) / BREED_IDS.length
  lines.push('', `All breeds: Great ${f1(avgOf('Great'))} · Good ${f1(avgOf('Good'))} · OK ${f1(avgOf('OK'))} · Neglect ${f1(avgOf('Neglect'))}.`, '')
}

if (cells.length > 0) {
  lines.push('## Battle: win share at equal totals (%)', '', `Row breed's share of decided battles against the column breed. Targets: every pair 25–75 and at least ${PAIR_INSIDE_PCT} % of pairs 30–70, Lootlid's mean 40–60 (other means are flagged, not targets), mirrors 45–55, attacks per monster per match 4–12, KO rate in the starters' mirrors ${KO_BAND[1000]!.join('–')} % at 1,000 and ${KO_BAND[3000]!.join('–')} % at 3,000. Breeds are the first three letters of their names.`, '')
  for (const total of TOTALS) {
    const at = cells.filter((c) => c.total === total)
    const get = (x: BreedId, y: BreedId) => {
      const c = at.find((k) => (k.a === x && k.b === y) || (k.a === y && k.b === x))!
      return c.a === x ? share(c) : 100 - share(c)
    }
    // Per-breed summary. The KO band is §26's "even fights" figure: the average over every breed's mirror
    // (glass cannons KO each other far more often than walls do, by design), so it is checked on the average.
    lines.push(`### Total ${total.toLocaleString('en-US')}`, '', '| Breed | Mean vs all | Worst | Best | Mirror | KO % (mirror) | Attacks |', '|---|---|---|---|---|---|---|')
    const koAvg = KO_PROBES.reduce((s, x) => {
      const m = at.find((k) => k.a === x && k.b === x)!
      return s + pct(m.koA + m.koB, m.seeds)
    }, 0) / KO_PROBES.length
    if (KO_BAND[total] && !inBand(koAvg, KO_BAND[total]!)) misses.push(`Battle ${total} starters' mirror KO rate ${f1(koAvg)} % (band ${KO_BAND[total]!.join('–')})`)
    const health = at.reduce((h, k) => ({ pushes: h.pushes + k.pushes, dir: h.dir + k.dirChanges, touch: h.touch + k.touchTicks, ticks: h.ticks + k.ticks, battles: h.battles + k.seeds }), { pushes: 0, dir: 0, touch: 0, ticks: 0, battles: 0 })
    for (const x of BREED_IDS) {
      const others = BREED_IDS.filter((y) => y !== x)
      const shares = others.map((y) => ({ y, s: get(x, y) }))
      const mean = shares.reduce((s, v) => s + v.s, 0) / shares.length
      const worst = shares.reduce((m, v) => (v.s < m.s ? v : m))
      const best = shares.reduce((m, v) => (v.s > m.s ? v : m))
      const mirror = at.find((k) => k.a === x && k.b === x)!
      const ko = pct(mirror.koA + mirror.koB, mirror.seeds)
      const attacks = at.filter((k) => k.a === x || k.b === x).reduce((s, k) => s + (k.a === x ? k.attacksA : k.attacksB) / k.seeds, 0) / at.filter((k) => k.a === x || k.b === x).length
      const mirrorShare = share(mirror)
      const flags: string[] = []
      if (!inBand(mirrorShare, MIRROR_BAND)) flags.push('mirror')
      if (!inBand(attacks, ATTACK_BAND)) flags.push('attacks')
      if (!inBand(mean, MEAN_BAND)) {
        flags.push('mean')
        if (MEAN_TARGETS.includes(x)) misses.push(`Battle ${total} ${BREED_BY_ID[x].name} mean win share ${f1(mean)} % (band 40–60)`)
      }
      if (!inBand(attacks, ATTACK_BAND)) misses.push(`Battle ${total} ${BREED_BY_ID[x].name} attacks ${f1(attacks)} per match (band 4–12)`)
      if (!inBand(mirrorShare, [40, 60])) misses.push(`Battle ${total} ${BREED_BY_ID[x].name} mirror ${f1(mirrorShare)} % (band 45–55; ±3.5 is noise at ${BATTLES} seeds)`)
      lines.push(`| ${BREED_BY_ID[x].name} | ${f1(mean)} | ${f0(worst.s)} vs ${abbr(worst.y)} | ${f0(best.s)} vs ${abbr(best.y)} | ${f1(mirrorShare)} | ${f1(ko)} | ${f1(attacks)}${flags.length ? ` ✗ ${flags.join(', ')}` : ''} |`)
    }
    // Pairs outside the bands: none may leave 25–75, and at least 95 % must sit inside 30–70.
    const out: string[] = []
    for (let i = 0; i < BREED_IDS.length; i++)
      for (let j = i + 1; j < BREED_IDS.length; j++) {
        const s = get(BREED_IDS[i]!, BREED_IDS[j]!)
        if (!inBand(s, PAIR_BAND)) {
          out.push(`${BREED_BY_ID[BREED_IDS[i]!].name} vs ${BREED_BY_ID[BREED_IDS[j]!].name}: ${f0(s)} %`)
          if (!inBand(s, PAIR_HARD_BAND)) misses.push(`Battle ${total} ${BREED_BY_ID[BREED_IDS[i]!].name} vs ${BREED_BY_ID[BREED_IDS[j]!].name}: ${f0(s)} % (hard band 25–75)`)
        }
      }
    const pairs = (BREED_IDS.length * (BREED_IDS.length - 1)) / 2
    const insidePct = ((pairs - out.length) * 100) / pairs
    if (insidePct < PAIR_INSIDE_PCT) misses.push(`Battle ${total} only ${f1(insidePct)} % of pairs inside 30–70 (want ≥ ${PAIR_INSIDE_PCT} %)`)
    lines.push('', `${pairs - out.length} of ${pairs} pairs (${f1(insidePct)} %) inside 30–70 %.${out.length ? ` Outside: ${out.join('; ')}.` : ''}`, '')
    lines.push(`AI health: ${f1(health.pushes / health.battles)} pushes per match, ${f1(health.dir / health.battles / 2)} direction changes per monster, touching ${f1(pct(health.touch, health.ticks))} % of the time.`, '')
    // The full matrix.
    lines.push('<details><summary>Full matrix</summary>', '', `| | ${BREED_IDS.map(abbr).join(' | ')} |`, `|---|${BREED_IDS.map(() => '---').join('|')}|`)
    for (const x of BREED_IDS) lines.push(`| **${abbr(x)}** | ${BREED_IDS.map((y) => f0(get(x, y))).join(' | ')} |`)
    lines.push('', '</details>', '')
  }
}

lines.push('## Outside the targets', '')
if (misses.length === 0) lines.push('Nothing. Every cell is inside its band.')
else for (const m of misses) lines.push(`- ${m}`)
lines.push('')

const seconds = Math.round((Date.now() - started) / 1000)
lines.push(`Run time: ${Math.floor(seconds / 60)} min ${seconds % 60} s on ${availableParallelism()} cores.`, '')
writeFileSync(OUT, lines.join('\n'))
if (JSON_OUT) writeFileSync(JSON_OUT, JSON.stringify({ raise: [...raise.values()], cells }, null, 1))
console.log(`Wrote ${OUT}: ${raise.size} raising cells, ${cells.length} battle cells, ${misses.length} outside the targets, ${seconds} s.`)
if (misses.length) console.log(misses.map((m) => `  - ${m}`).join('\n'))
