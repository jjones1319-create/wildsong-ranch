import { describe, expect, it } from 'vitest'
import { BREED_IDS, type BreedId } from '../../data/types.ts'
import type { Monster } from '../monster.ts'
import { npcMonster } from '../npc.ts'
import { runBattle, timerTicksFor } from './engine.ts'
import type { FighterSetup } from './types.ts'

/**
 * GAME_DESIGN §26 battle targets: AI vs AI, stats from the NPC generator, alternating sides, 200 seeds per cell.
 * Measured without sweets, sheets or edits. Tune `tuning.ts` AI or trait numbers to pass; the formulas stay.
 */

const SEEDS = 200
const ai = (monster: Monster): FighterSetup => ({ monster, control: 'ai', personality: 'Steady' })
const opts = (seed: number) => ({ seed, timerTicks: timerTicksFor(60) })

interface Cell {
  winA: number
  winB: number
  draw: number
  koA: number
  koB: number
  attacksA: number
  attacksB: number
}

/** A's results over `seeds` battles, sides alternating. Percentages of all battles. */
function cell(a: Monster, b: Monster, seeds = SEEDS): Cell {
  let winA = 0
  let winB = 0
  let draw = 0
  let koA = 0
  let koB = 0
  let attacksA = 0
  let attacksB = 0
  for (let seed = 0; seed < seeds; seed++) {
    const swapped = seed % 2 === 1
    const r = swapped ? runBattle(ai(b), ai(a), opts(seed)) : runBattle(ai(a), ai(b), opts(seed))
    const sideA = swapped ? 1 : 0
    if (r.outcome.winner === null) draw++
    else if (r.outcome.winner === sideA) {
      winA++
      if (r.outcome.how === 'ko') koA++
    } else {
      winB++
      if (r.outcome.how === 'ko') koB++
    }
    attacksA += r.fighters[sideA].attacks
    attacksB += r.fighters[1 - sideA]!.attacks
  }
  const pct = (n: number) => Math.round((n * 1000) / seeds) / 10
  return { winA: pct(winA), winB: pct(winB), draw: pct(draw), koA: pct(koA), koB: pct(koB), attacksA: Math.round((attacksA * 10) / seeds) / 10, attacksB: Math.round((attacksB * 10) / seeds) / 10 }
}

/** Win share among decided battles (draws are a tie, not a loss). */
const share = (c: Cell) => (c.winA + c.winB > 0 ? (c.winA * 100) / (c.winA + c.winB) : 50)

const between = (value: number, lo: number, hi: number, label: string) => {
  expect(value, label).toBeGreaterThanOrEqual(lo)
  expect(value, label).toBeLessThanOrEqual(hi)
}

const PAIRS: [BreedId, BreedId][] = [
  ['puddlepup', 'cobblemaw'],
  ['tumblefox', 'moatshell'],
  ['wishlume', 'quillion'],
  ['cinderlynx', 'bloatoad'],
  ['coilfang', 'nimbusheep'],
  ['galeheron', 'nibblegrub'],
  ['velvesper', 'ashwraith'],
  ['zipwisp', 'mirrorkin'],
  ['gearhoot', 'reefclaw'],
  ['lootlid', 'aurelwyrm'],
  ['hearthwing', 'grumblestone'],
  ['pluckrex', 'paladove'],
  ['starhowl', 'petalphant'],
  ['scrollopus', 'gloomgrin'],
  ['rammerjack', 'frostlance'],
]

describe('§26 battle balance (AI vs AI, NPC stats, alternating sides)', () => {
  it('mirror match: 45–55 %', () => {
    const m = npcMonster({ breed: 'puddlepup', total: 1500, seed: 1 })
    const c = cell(m, structuredClone(m))
    // eslint-disable-next-line no-console
    console.log('mirror', c)
    between(share(c), 45, 55, 'mirror win share')
  })

  it('+10 % total stats: 62–80 % · +30 %: 85–96 %', () => {
    const base = npcMonster({ breed: 'puddlepup', total: 1500, seed: 1 })
    const plus10 = npcMonster({ breed: 'puddlepup', total: 1650, seed: 1 })
    const plus30 = npcMonster({ breed: 'puddlepup', total: 1950, seed: 1 })
    const c10 = cell(plus10, base)
    const c30 = cell(plus30, base)
    // eslint-disable-next-line no-console
    console.log('+10%', c10, '+30%', c30)
    between(share(c10), 62, 80, '+10 % win share')
    between(share(c30), 85, 96, '+30 % win share')
  })

  it('KO rate in even fights (five starter mirrors): 15–35 % at total 1,000; 3–15 % at 3,000; 4–12 attacks', () => {
    const probes: BreedId[] = ['puddlepup', 'tumblefox', 'quillion', 'pluckrex', 'cobblemaw']
    const measure = (total: number) => {
      let ko = 0
      let attacks = 0
      for (const breed of probes) {
        const m = npcMonster({ breed, total, seed: 2 })
        const c = cell(m, structuredClone(m), 100)
        ko += c.koA + c.koB
        attacks += c.attacksA
      }
      return { ko: ko / probes.length, attacks: attacks / probes.length }
    }
    const low = measure(1000)
    const high = measure(3000)
    // eslint-disable-next-line no-console
    console.log('ko 1000', low, 'ko 3000', high)
    between(low.ko, 15, 35, 'KO rate at 1,000')
    between(high.ko, 3, 15, 'KO rate at 3,000')
    between(low.attacks, 4, 12, 'attacks per match at 1,000')
    between(high.attacks, 4, 12, 'attacks per match at 3,000')
  })

  /**
   * M9: the full 30 × 30 matrix at three totals (200 seeds a cell) is run by `npm run sim:balance` and recorded
   * in docs/BALANCE_REPORT.md (about 95 % of pairs inside 30–70 %; the rest are listed there). Here a fixed sample
   * of pairs guards the shape on every run: at least 80 % inside the band, none beyond 20–80 % (one NPC roll per
   * side and 100 seeds give a few points of noise), and every attack count in range. `WILDSONG_FULL_SIM=1` runs
   * every pair instead (slow).
   */
  it('breed pairs at equal total (1,000 / 2,000 / 3,000): ≥ 80 % inside 30–70 %, none outside 20–80 %, attacks 4–12', () => {
    const full = !!process.env.WILDSONG_FULL_SIM
    const pairs: [BreedId, BreedId][] = full ? BREED_IDS.flatMap((x, i) => BREED_IDS.slice(i + 1).map((y) => [x, y] as [BreedId, BreedId])) : PAIRS
    const rows: string[] = []
    const misses: string[] = []
    let inside = 0
    let cells = 0
    for (const total of [1000, 2000, 3000]) {
      for (const [x, y] of pairs) {
        const a = npcMonster({ breed: x, total, seed: 100 + total })
        const b = npcMonster({ breed: y, total, seed: 200 + total })
        const c = cell(a, b, full ? 200 : 100)
        const s = Math.round(share(c))
        cells += 1
        if (s >= 30 && s <= 70) inside += 1
        else misses.push(`${total} ${x} vs ${y}: ${s}%`)
        rows.push(`${total} ${x} vs ${y}: ${s}% (draws ${c.draw}%, attacks ${c.attacksA}/${c.attacksB})`)
        between(s, 20, 80, `${total} ${x} vs ${y} win share`)
        // The 4–12 target is an average over typical fights (checked above); single pairs get two attacks of slack.
        between(c.attacksA, 3, 14, `${x} attacks at ${total}`)
        between(c.attacksB, 3, 14, `${y} attacks at ${total}`)
      }
    }
    // eslint-disable-next-line no-console
    console.log(`${inside}/${cells} pairs inside 30–70 %\n${rows.join('\n')}\nOutside: ${misses.join('; ')}`)
    expect(inside / cells).toBeGreaterThanOrEqual(0.8)
  }, 1_800_000)
})
