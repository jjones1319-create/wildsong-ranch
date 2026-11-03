import { describe, expect, it } from 'vitest'
import { simulateRanch, type HerdReport, type HerdSimOptions } from './herdSim.ts'

/**
 * GAME_DESIGN §26 the herd targets (v1.21.0), 40 seeds each, without Stat Sweets, Songsheets or edits: a Good-care
 * star with a ranch-mate stays in its Good band; a ranch-mate on drill orders lives 62–80% of its life, and one that
 * rests ≥ 85%; an active farm reaches level 6–9 by year 5. The ranch-mates' own gold per month is reported.
 * Set HERD_SIM_FULL=1 for the extra report rows (Play orders, the farm without pens or achievements).
 */

const SEEDS = 40
const SLOW = 600_000
const cache = new Map<string, HerdReport[]>()
const runMany = (o: Omit<HerdSimOptions, 'seed'>): HerdReport[] => {
  const key = JSON.stringify(o)
  if (!cache.has(key)) cache.set(key, Array.from({ length: SEEDS }, (_, i) => simulateRanch({ ...o, seed: 1000 + i })))
  return cache.get(key)!
}
const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length)
const firstMates = (rs: HerdReport[]) => mean(rs.map((r) => r.mateLives[0]!))
const starLife = (rs: HerdReport[]) => mean(rs.map((r) => r.star.lifeLivedPct))
const yearTotal = (rs: HerdReport[], y: number) => mean(rs.flatMap((r) => (r.star.totalsByYear[y - 1] !== undefined ? [r.star.totalsByYear[y - 1]!] : [])))
const levelsAt = (rs: HerdReport[], y: number) => rs.map((r) => r.farmLevelByYear[y - 1]!)
const gold = (rs: HerdReport[]) => mean(rs.map((r) => r.netGoldPerMateMonth))
/** A mean percentage, or a dash when the run ended before any (a fixed five-year run). */
const pct = (xs: number[]) => (xs.length > 0 ? `${mean(xs).toFixed(1)}%` : '–')

const LIGHT = { mates: 'light' } as const
const HEAVY = { mates: 'heavy' } as const
const REST = { mates: 'rest' } as const
const ACTIVE = { mates: 'light', weeks: 240, buyPens: true, achievements: true } as const

const between = (value: number, lo: number, hi: number) => {
  expect(value).toBeGreaterThanOrEqual(lo)
  expect(value).toBeLessThanOrEqual(hi)
}

describe('the herd report (§26)', () => {
  it(
    'prints the numbers first',
    () => {
      const row = (label: string, rs: HerdReport[]) =>
        `${label.padEnd(22)} star ${pct(rs.map((r) => r.star.lifeLivedPct).filter((x) => x > 0))} · y1/y3/y5 ${[1, 3, 5].map((y) => yearTotal(rs, y).toFixed(0)).join(' / ')} · first mate ${pct(rs.flatMap((r) => r.mateLives.slice(0, 1)))} · ` +
        `farm y5 Lv ${mean(levelsAt(rs, 5)).toFixed(1)} · gold/mate/month ${gold(rs).toFixed(0)} · partner drills ${mean(rs.map((r) => r.partnerDrills)).toFixed(1)} · tiers ${mean(rs.map((r) => r.tiersReached)).toFixed(1)}`
      const lines = [row('light-drill mate', runMany(LIGHT)), row('heavy-drill mate', runMany(HEAVY)), row('resting mate', runMany(REST)), row('active farm (5 years)', runMany(ACTIVE))]
      if (process.env.HERD_SIM_FULL) {
        lines.push(row('playing mate', runMany({ mates: 'play' })))
        lines.push(row('farm: one pen only', runMany({ mates: 'light', weeks: 240 })))
        lines.push(row('farm: pens, no extras', runMany({ mates: 'light', weeks: 240, buyPens: true })))
      }
      console.info(`\n${lines.join('\n')}`)
      expect(lines.length).toBeGreaterThanOrEqual(4)
    },
    SLOW,
  )

  it('the same seed gives the same ranch', () => {
    expect(simulateRanch({ ...LIGHT, seed: 7, weeks: 60 })).toEqual(simulateRanch({ ...LIGHT, seed: 7, weeks: 60 }))
  })
})

describe('the herd targets (§26)', () => {
  it(
    'a Good-care star with a ranch-mate stays in its Good band (76–88% of its life; about 700 / 1,450 / 2,350)',
    () => {
      const rs = runMany(LIGHT)
      between(starLife(rs), 76, 88)
      between(yearTotal(rs, 1), 700 * 0.8, 700 * 1.2)
      between(yearTotal(rs, 3), 1450 * 0.8, 1450 * 1.2)
      between(yearTotal(rs, 5), 2350 * 0.8, 2350 * 1.2)
    },
    SLOW,
  )

  it('a ranch-mate on drill orders lives 62–80% of its life (a light or a heavy drill)', () => {
    between(firstMates(runMany(LIGHT)), 62, 80)
    between(firstMates(runMany(HEAVY)), 62, 80)
  }, SLOW)

  it('a resting ranch-mate lives at least 85% of its life', () => {
    expect(firstMates(runMany(REST))).toBeGreaterThanOrEqual(85)
  }, SLOW)

  it('an active farm (pens as they open, a typical year of cups and Journeys) reaches level 6–9 by year 5', () => {
    for (const level of levelsAt(runMany(ACTIVE), 5)) between(level, 6, 9)
  }, SLOW)

  it('ranch-mates on drill orders cost a little gold: their half pay never covers their food', () => {
    const g = gold(runMany(LIGHT))
    expect(g).toBeLessThan(0)
    expect(g).toBeGreaterThan(-300)
  }, SLOW)
})
