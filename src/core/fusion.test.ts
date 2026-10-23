import { describe, expect, it } from 'vitest'
import { STARTING_UNLOCKED } from '../data/breeds.ts'
import { techniquesOfBreed } from '../data/techniques.ts'
import { FUSION } from '../data/tuning.ts'
import { BREED_IDS, STAT_KEYS } from '../data/types.ts'
import { babyRanks, babyStatOffsets, catalystEffect, compatTier, compatibility, findRelative, fuse, fusionOutcomes, inheritedTechniques, makeBaby, rarityK } from './fusion.ts'
import { divRound } from './mathx.ts'
import { mixBreeds } from './monster.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

const ALL = [...BREED_IDS]

describe('Fusion odds (§15)', () => {
  it('weights mains 4/3/2/1 and subs 3/2/2/1 times lineage strength, and the shown list sums to 100', () => {
    const p1 = makeMonster({ main: 'puddlepup' })
    const p2 = makeMonster({ main: 'tumblefox' })
    // mains: puddlepup 4+2 = 6, tumblefox 3+1 = 4 · subs: tumblefox 3+2 = 5, puddlepup 2+1 = 3 · strengths 7 and 6
    // weights 210 / 126 / 120 / 72 of 528 → 39.8 / 23.9 / 22.7 / 13.6 → 40 / 24 / 23 / 13
    expect(fusionOutcomes(p1, p2, ALL)).toEqual([
      { main: 'puddlepup', sub: 'tumblefox', pct: 40 },
      { main: 'puddlepup', sub: 'puddlepup', pct: 24 },
      { main: 'tumblefox', sub: 'tumblefox', pct: 23 },
      { main: 'tumblefox', sub: 'puddlepup', pct: 13 },
    ])
  })

  it('the Lineage Seal doubles the first parent’s main weight', () => {
    const p1 = makeMonster({ main: 'puddlepup' })
    const p2 = makeMonster({ main: 'tumblefox' })
    const sealed = fusionOutcomes(p1, p2, ALL, true)
    expect(sealed.map((o) => o.pct).reduce((a, b) => a + b, 0)).toBe(100)
    expect(sealed.filter((o) => o.main === 'puddlepup').reduce((a, o) => a + o.pct, 0)).toBeGreaterThan(64)
  })

  it('removes locked mains, drops anything under 1 %, and shows at most six outcomes', () => {
    const p1 = makeMonster({ main: 'puddlepup' })
    const p2 = makeMonster({ main: 'tumblefox' })
    const noPup = fusionOutcomes(p1, p2, ALL.filter((b) => b !== 'puddlepup'))
    expect(noPup.every((o) => o.main === 'tumblefox')).toBe(true)
    expect(noPup.map((o) => o.pct)).toEqual([63, 37])
    // aurelwyrm (strength 9) with a lootlid (strength 2) sub: lootlid/lootlid weighs 4 of 664 (0.6 %) and is dropped.
    const rare = fusionOutcomes(makeMonster({ main: 'aurelwyrm' }), makeMonster({ main: 'aurelwyrm', sub: 'lootlid' }), ALL)
    expect(rare.find((o) => o.main === 'lootlid' && o.sub === 'lootlid')).toBeUndefined()
    expect(rare).toHaveLength(3)
    expect(rare.reduce((a, o) => a + o.pct, 0)).toBe(100)
    const many = fusionOutcomes(makeMonster({ main: 'puddlepup', sub: 'cobblemaw' }), makeMonster({ main: 'quillion', sub: 'bloatoad' }), ALL)
    expect(many.length).toBeLessThanOrEqual(FUSION.maxOutcomes)
    expect(many.reduce((a, o) => a + o.pct, 0)).toBe(100)
    expect(many.every((o) => o.pct >= FUSION.minPct)).toBe(true)
    for (let i = 1; i < many.length; i++) expect(many[i - 1]!.pct).toBeGreaterThanOrEqual(many[i]!.pct)
    // Only unlocked breeds ever appear as mains.
    for (let i = 0; i < 20; i++) {
      const a = makeMonster({ main: ALL[i % ALL.length]!, sub: ALL[(i * 7) % ALL.length]! })
      const b = makeMonster({ main: ALL[(i * 3) % ALL.length]!, sub: ALL[(i * 11) % ALL.length]! })
      const outs = fusionOutcomes(a, b, STARTING_UNLOCKED)
      expect(outs.every((o) => STARTING_UNLOCKED.includes(o.main))).toBe(true)
      if (outs.length) expect(outs.reduce((s, o) => s + o.pct, 0)).toBe(100)
    }
  })
})

describe('compatibility and the baby’s stats (§15)', () => {
  it('ranks the baby by grade (ties by base) and counts the stats where a parent agrees', () => {
    // Puddlepup: SKI B first, then the C stats by base (LIF 120, then POW/SPD/DEF at 70 in order), INT D last.
    expect(babyRanks('puddlepup', 'puddlepup')).toEqual({ SKI: 1, LIF: 2, POW: 3, SPD: 4, DEF: 5, INT: 6 })
    const perfect = makeMonster({ stats: { SKI: 600, LIF: 500, POW: 400, SPD: 300, DEF: 200, INT: 100 } })
    const reversed = makeMonster({ stats: { INT: 600, DEF: 500, SPD: 400, POW: 300, LIF: 200, SKI: 100 } })
    expect(compatibility(perfect, reversed, 'puddlepup', 'puddlepup')).toBe(6)
    expect(compatibility(reversed, reversed, 'puddlepup', 'puddlepup')).toBe(0)
    expect(compatTier(0)).toBe('low')
    expect(compatTier(2)).toBe('decent')
    expect(compatTier(4)).toBe('wonderful')
    expect(compatTier(6)).toBe('perfect')
  })

  it('K follows the rarity table', () => {
    expect([1, 2, 5, 7, 10, 15, 20, 30, 40, 50, 51, 100].map(rarityK)).toEqual([100, 100, 85, 85, 70, 70, 60, 60, 50, 50, 40, 40])
  })

  it('baby = base + round(offset · P · K) + catalyst, with offsets from the parents’ trained gains', () => {
    const base = mixBreeds('puddlepup', 'puddlepup').base
    const p1 = makeMonster({ stats: { POW: base.POW + 300 } })
    const p2 = makeMonster({ stats: { POW: base.POW + 150, INT: base.INT - 50 } })
    const m = compatibility(p1, p2, 'puddlepup', 'puddlepup')
    const off = babyStatOffsets(p1, p2, m, 40, catalystEffect(null))
    const pPct = FUSION.pBasePct + FUSION.pPerMatchPct * m
    expect(off.POW).toBe(divRound((2 * 300 + 150) * pPct * 50, 3 * 100 * 100))
    expect(off.INT).toBe(0) // never below zero
    const shard = babyStatOffsets(p1, p2, m, 40, catalystEffect('power-shard'))
    expect(shard.POW).toBe(off.POW + FUSION.shardStat)
    expect(catalystEffect('amber-charm')).toEqual({ stats: { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }, lifespan: 20, lineageSeal: false })
    expect(catalystEffect('lineage-seal').lineageSeal).toBe(true)
    expect(catalystEffect('sun-plum').lineageSeal).toBe(false)
  })
})

describe('inheritance (§15)', () => {
  const kitOf = (breed: 'puddlepup' | 'tumblefox') => techniquesOfBreed(breed).filter((t) => t.family !== 'Basic')

  it('same main as P1: two thirds of P1’s non-Basic techniques, with uses and levels', () => {
    const p1 = makeMonster({ id: 'p1' })
    const learned = kitOf('puddlepup').slice(0, 3)
    p1.techniques = [...p1.techniques, ...learned.map((t, i) => ({ id: t.id, uses: 20 + i, level: 2 as const }))]
    const p2 = makeMonster({ id: 'p2', main: 'tumblefox' })
    const r = makeBaby(p1, p2, { main: 'puddlepup', sub: 'tumblefox', pct: 40 }, catalystEffect(null), 'baby', createRng(1))
    const inherited = r.baby.techniques.filter((t) => learned.some((l) => l.id === t.id))
    expect(inherited).toHaveLength(2) // floor(3 · 2/3)
    expect(inherited[0]).toEqual({ id: learned[0]!.id, uses: 20, level: 2 })
    expect(r.baby.generation).toBe(2)
    expect(r.baby.parents).toEqual(['p1', 'p2'])
  })

  it('a different main: at most one technique per family from either parent, only from the baby’s kit', () => {
    const p1 = makeMonster({ id: 'p1' })
    const p2 = makeMonster({ id: 'p2', main: 'tumblefox' })
    const tf = kitOf('tumblefox')
    p2.techniques = [...p2.techniques, ...tf.map((t) => ({ id: t.id, uses: 5, level: 1 as const }))]
    const baby = makeBaby(p1, p2, { main: 'tumblefox', sub: 'puddlepup', pct: 13 }, catalystEffect(null), 'baby', createRng(2)).baby
    const got = inheritedTechniques({ ...baby, techniques: baby.techniques.filter((t) => !tf.some((x) => x.id === t.id)) }, p1, p2)
    const families = got.map((t) => tf.find((x) => x.id === t.id)!.family)
    expect(new Set(families).size).toBe(families.length)
    expect(got.length).toBeGreaterThan(0)
    expect(got.every((t) => tf.some((x) => x.id === t.id))).toBe(true)
  })

  it('blends nature and form 2:1 and takes grades, guts and lifespan from the baby’s breed', () => {
    const p1 = makeMonster({ id: 'p1', nature: 30 })
    p1.form = 30
    p1.gutsRate = 6
    const p2 = makeMonster({ id: 'p2', nature: -30 })
    p2.form = -30
    p2.generation = 4
    const r = makeBaby(p1, p2, { main: 'puddlepup', sub: 'puddlepup', pct: 24 }, catalystEffect('amber-charm'), 'baby', createRng(3))
    expect(r.baby.nature).toBe(10)
    expect(r.baby.form).toBe(10)
    expect(r.baby.generation).toBe(5)
    const mix = mixBreeds('puddlepup', 'puddlepup')
    expect(r.baby.grades).toEqual(mix.grades)
    expect(r.baby.gutsRate).toBe(mix.gutsRate)
    expect(r.baby.lifespanTotal).toBe(mix.lifespan + 20)
    expect(r.baby.ageWeeks).toBe(0)
  })
})

describe('fuse at Dr. Pell’s (§15)', () => {
  const setup = (withMonster: boolean) => {
    const state = createGameState({ monster: withMonster ? makeMonster({ id: 'active' }) : null })
    state.freezer = [makeMonster({ id: 'p1', stats: { POW: 400 } }), makeMonster({ id: 'p2', main: 'tumblefox' })]
    state.inventory = { 'power-shard': 1 }
    return state
  }

  it('charges the fee, uses the catalyst, makes Ancestors of the parents and places the baby', () => {
    const state = setup(false)
    const r = fuse(state, 'p1', 'p2', 'power-shard', 'baby', createRng(7))
    expect(r.refused).toBeNull()
    expect(r.placed).toBe('ranch')
    expect(r.state.money).toBe(state.money - FUSION.fee)
    expect(r.state.inventory['power-shard']).toBeUndefined()
    expect(r.state.monster?.id).toBe('baby')
    expect(r.state.freezer).toEqual([])
    expect(r.state.memorial.map((e) => e.cause)).toEqual(['fused', 'fused'])
    expect(r.state.memorial.map((e) => e.monster.id).sort()).toEqual(['p1', 'p2'])
    expect(r.result!.baby.parents).toEqual(['p1', 'p2'])
    expect(r.result!.baby.stats.POW).toBeGreaterThan(mixBreeds(r.result!.outcome.main, r.result!.outcome.sub).base.POW)
    expect(findRelative(r.state, 'p1')?.id).toBe('p1')
    expect(r.state.encyclopedia.breeds).toContain(r.result!.outcome.main)
    for (const k of STAT_KEYS) expect(r.result!.baby.stats[k]).toBeGreaterThan(0)
    // Deterministic for a seed.
    expect(fuse(state, 'p1', 'p2', 'power-shard', 'baby', createRng(7)).result!.baby).toEqual(r.result!.baby)
  })

  it('with a monster on the ranch the baby goes to the Freezer; refusals are explicit', () => {
    const state = setup(true)
    const r = fuse(state, 'p1', 'p2', null, 'baby', createRng(1))
    expect(r.placed).toBe('freezer')
    expect(r.state.freezer.map((m) => m.id)).toEqual(['baby'])
    expect(r.state.inventory['power-shard']).toBe(1)
    expect(fuse(state, 'p1', 'p1', null, 'b', createRng(1)).refused).toBe('sameMonster')
    expect(fuse(state, 'p1', 'nope', null, 'b', createRng(1)).refused).toBe('notFound')
    expect(fuse({ ...state, money: FUSION.fee - 1 }, 'p1', 'p2', null, 'b', createRng(1)).refused).toBe('money')
    expect(fuse(state, 'p1', 'p2', 'amber-charm', 'b', createRng(1)).refused).toBe('noCatalyst')
    const elders = setup(true)
    elders.elderGrove = elders.freezer
    elders.freezer = Array.from({ length: 20 }, (_, i) => makeMonster({ id: `f${i}` }))
    expect(fuse(elders, 'p1', 'p2', null, 'b', createRng(1)).refused).toBe('freezerFull')
    const locked = setup(false)
    locked.unlocked = []
    expect(fuse(locked, 'p1', 'p2', null, 'b', createRng(1)).refused).toBe('noOutcome')
  })
})
