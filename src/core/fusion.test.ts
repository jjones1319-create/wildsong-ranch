import { describe, expect, it } from 'vitest'
import { BREED_BY_ID, STARTING_UNLOCKED } from '../data/breeds.ts'
import { BREED_KINDS, FUSION_RULES } from '../data/fusionRecipes.ts'
import { techniquesOfBreed, UNIVERSAL_TECHNIQUES } from '../data/techniques.ts'
import { FUSION } from '../data/tuning.ts'
import { BREED_IDS, STAT_KEYS, type BreedId } from '../data/types.ts'
import { babyRanks, babyStatOffsets, catalystEffect, compatTier, compatibility, findKey, findRelative, fuse, fusionOutcomes, fusionSurprises, inheritedTechniques, makeBaby, pairKey, rarityK, type FusionOutcome } from './fusion.ts'
import { cyrb53 } from './hash.ts'
import { divRound } from './mathx.ts'
import { mixBreeds } from './monster.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

const ALL: readonly BreedId[] = [...BREED_IDS]
const outcome = (breed: BreedId, pct: number, source: FusionOutcome['source'] = 'p1'): FusionOutcome => ({ breed, pct, source, key: source === 'surprise' ? `x+y>${breed}` : null })

const pcts = (outs: { pct: number }[]) => outs.map((o) => o.pct)
const breeds = (outs: { breed: BreedId }[]) => outs.map((o) => o.breed)

describe('Fusion odds (§15)', () => {
  const pup = makeMonster({ main: 'puddlepup' })
  const fox = makeMonster({ main: 'tumblefox' })

  it('the first parent’s breed 35 %, the second’s 35 %, then two surprises at 20 % and 10 %', () => {
    const outs = fusionOutcomes(pup, fox, STARTING_UNLOCKED)
    expect(pcts(outs)).toEqual([35, 35, 20, 10])
    expect(outs.map((o) => o.source)).toEqual(['p1', 'p2', 'surprise', 'surprise'])
    expect(breeds(outs).slice(0, 2)).toEqual(['puddlepup', 'tumblefox'])
    expect(outs[2]!.key).toBe(`puddlepup+tumblefox>${outs[2]!.breed}`)
    expect(outs[0]!.key).toBeNull()
    // The subs never matter: a mixed parent counts as its main breed.
    expect(fusionOutcomes(makeMonster({ main: 'puddlepup', sub: 'cobblemaw' }), fox, STARTING_UNLOCKED)).toEqual(outs)
  })

  it('same-breed parents add up; the Lineage Seal doubles the first parent’s weight', () => {
    const twins = fusionOutcomes(pup, makeMonster({ main: 'puddlepup' }), STARTING_UNLOCKED)
    expect(pcts(twins)).toEqual([70, 20, 10])
    expect(twins[0]!.source).toBe('both')
    expect(pcts(fusionOutcomes(pup, fox, STARTING_UNLOCKED, true))).toEqual([52, 26, 15, 7])
    expect(pcts(fusionOutcomes(pup, makeMonster({ main: 'puddlepup' }), STARTING_UNLOCKED, true))).toEqual([78, 15, 7])
  })

  it('locked breeds drop out and the rest renormalize; nothing left means no outcome', () => {
    const noPup = fusionOutcomes(pup, fox, STARTING_UNLOCKED.filter((b) => b !== 'puddlepup'))
    expect(pcts(noPup)).toEqual([54, 31, 15])
    expect(breeds(noPup)).not.toContain('puddlepup')
    const neither = fusionOutcomes(pup, fox, STARTING_UNLOCKED.filter((b) => b !== 'puddlepup' && b !== 'tumblefox'))
    expect(pcts(neither)).toEqual([67, 33])
    expect(neither.every((o) => o.source === 'surprise')).toBe(true)
    expect(fusionOutcomes(pup, fox, ['puddlepup'])).toEqual([{ breed: 'puddlepup', pct: 100, source: 'p1', key: null }])
    expect(fusionOutcomes(pup, fox, [])).toEqual([])
  })

  it('every list sums to 100 and only ever offers unlocked breeds', () => {
    for (let i = 0; i < ALL.length; i++) {
      const a = makeMonster({ main: ALL[i]! })
      const b = makeMonster({ main: ALL[(i * 7 + 3) % ALL.length]! })
      for (const unlocked of [STARTING_UNLOCKED, ALL]) {
        const outs = fusionOutcomes(a, b, unlocked)
        expect(outs.reduce((s, o) => s + o.pct, 0)).toBe(100)
        expect(outs.every((o) => unlocked.includes(o.breed) && o.pct > 0)).toBe(true)
      }
    }
  })

  it('K follows each row’s odds: surprises carry more of the parents’ gains', () => {
    expect(pcts(fusionOutcomes(pup, fox, STARTING_UNLOCKED)).map(rarityK)).toEqual([50, 50, 60, 70])
    expect(pcts(fusionOutcomes(pup, fox, STARTING_UNLOCKED, true)).map(rarityK)).toEqual([40, 60, 70, 85])
  })
})

describe('Fusion surprises (CONTENT §2.3)', () => {
  it('a snake and a bird can make a dragon: Coilfang + Galeheron → Hearthwing at 20 %', () => {
    const outs = fusionOutcomes(makeMonster({ main: 'coilfang' }), makeMonster({ main: 'galeheron' }), STARTING_UNLOCKED)
    expect(outs[2]).toEqual({ breed: 'hearthwing', pct: 20, source: 'surprise', key: 'coilfang+galeheron>hearthwing' })
  })

  it('swapping the parents keeps the surprises; they are never a parent and never locked', () => {
    for (const unlocked of [STARTING_UNLOCKED, ALL]) {
      for (let i = 0; i < unlocked.length; i++) {
        for (let j = i; j < unlocked.length; j++) {
          const a = unlocked[i]!
          const b = unlocked[j]!
          const s = fusionSurprises(a, b, unlocked)
          expect(s).toEqual(fusionSurprises(b, a, unlocked))
          expect(s).toHaveLength(2)
          expect(new Set(s).size).toBe(2)
          expect(s.every((x) => x !== a && x !== b && unlocked.includes(x))).toBe(true)
        }
      }
    }
    expect(pairKey('galeheron', 'coilfang')).toBe('coilfang+galeheron')
    expect(findKey('galeheron', 'coilfang', 'hearthwing')).toBe('coilfang+galeheron>hearthwing')
  })

  it('a locked recipe result is skipped until it is unlocked, then takes a slot', () => {
    expect(fusionSurprises('coilfang', 'hearthwing', STARTING_UNLOCKED)[0]).toBe('pluckrex')
    expect(fusionSurprises('coilfang', 'hearthwing', STARTING_UNLOCKED)).not.toContain('aurelwyrm')
    expect(fusionSurprises('coilfang', 'hearthwing', ALL)).toContain('aurelwyrm')
    expect(fusionSurprises('coilfang', 'hearthwing', [...STARTING_UNLOCKED, 'aurelwyrm'])).toContain('aurelwyrm')
  })

  it('with too few candidates the empty surprise slots drop out', () => {
    expect(fusionSurprises('puddlepup', 'tumblefox', ['puddlepup', 'tumblefox', 'cobblemaw'])).toEqual(['cobblemaw'])
    expect(pcts(fusionOutcomes(makeMonster({ main: 'puddlepup' }), makeMonster({ main: 'tumblefox' }), ['puddlepup', 'tumblefox', 'cobblemaw']))).toEqual([39, 39, 22])
  })

  it('spreads the surprises: every breed shows up, none crowds the table, and every rule picks something', () => {
    const counts = (unlocked: readonly BreedId[]) => {
      const c = new Map<BreedId, number>(unlocked.map((b) => [b, 0]))
      for (let i = 0; i < unlocked.length; i++) for (let j = i; j < unlocked.length; j++) for (const s of fusionSurprises(unlocked[i]!, unlocked[j]!, unlocked)) c.set(s, c.get(s)! + 1)
      return [...c.values()]
    }
    const start = counts(STARTING_UNLOCKED)
    expect(Math.min(...start)).toBeGreaterThanOrEqual(5)
    expect(Math.max(...start)).toBeLessThanOrEqual(40)
    const all = counts(ALL)
    expect(Math.min(...all)).toBeGreaterThanOrEqual(8)
    expect(Math.max(...all)).toBeLessThanOrEqual(45)
    for (const r of FUSION_RULES) {
      const picks = ALL.some((a) =>
        ALL.some((b) => {
          const fires = (BREED_KINDS[a].includes(r.a) && BREED_KINDS[b].includes(r.b)) || (BREED_KINDS[a].includes(r.b) && BREED_KINDS[b].includes(r.a))
          return fires && fusionSurprises(a, b, ALL).some((s) => BREED_KINDS[s].includes(r.makes))
        }),
      )
      expect(picks, `${r.a}+${r.b}→${r.makes}`).toBe(true)
    }
  })

  it('the whole surprise table is pinned: changing kinds, rules or recipes is a deliberate act', () => {
    const table = (unlocked: readonly BreedId[]) => {
      const rows: string[] = []
      for (let i = 0; i < unlocked.length; i++) for (let j = i; j < unlocked.length; j++) rows.push(`${unlocked[i]}+${unlocked[j]}>${fusionSurprises(unlocked[i]!, unlocked[j]!, unlocked).join(',')}`)
      return rows.join(';')
    }
    expect([cyrb53(table(STARTING_UNLOCKED)), cyrb53(table(ALL))]).toEqual([4424695493812943, 2599830349750459])
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
    const r = makeBaby(p1, p2, outcome('puddlepup', 35), catalystEffect(null), 'baby', createRng(1))
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
    const baby = makeBaby(p1, p2, outcome('tumblefox', 35, 'p2'), catalystEffect(null), 'baby', createRng(2)).baby
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
    const r = makeBaby(p1, p2, outcome('puddlepup', 35), catalystEffect('amber-charm'), 'baby', createRng(3))
    expect(r.baby.nature).toBe(10)
    expect(r.baby.form).toBe(10)
    expect(r.baby.generation).toBe(5)
    const mix = mixBreeds('puddlepup', 'puddlepup')
    expect(r.baby.grades).toEqual(mix.grades)
    expect(r.baby.gutsRate).toBe(mix.gutsRate)
    expect(r.baby.lifespanTotal).toBe(mix.lifespan + 20)
    expect(r.baby.ageWeeks).toBe(0)
  })

  it('the baby is always one whole breed, with the pure lifespan bonus', () => {
    const r = makeBaby(makeMonster({ id: 'p1' }), makeMonster({ id: 'p2', main: 'tumblefox' }), outcome('hearthwing', 20, 'surprise'), catalystEffect(null), 'baby', createRng(4))
    expect([r.baby.mainBreed, r.baby.subBreed]).toEqual(['hearthwing', 'hearthwing'])
    expect(r.baby.name).toBe('Hearthwing')
    expect(r.baby.lifespanTotal).toBeGreaterThan(BREED_BY_ID.hearthwing.lifespan)
    expect(r.newFind).toBe(false)
  })

  it('a surprise baby inherits the parents’ universal techniques (§10.5: part of every kit)', () => {
    const universal = UNIVERSAL_TECHNIQUES.find((t) => t.family === 'Hit')!
    const p1 = makeMonster({ id: 'p1' })
    p1.techniques = [...p1.techniques, { id: universal.id, uses: 9, level: 2 }]
    const baby = makeBaby(p1, makeMonster({ id: 'p2', main: 'tumblefox' }), outcome('hearthwing', 20, 'surprise'), catalystEffect(null), 'baby', createRng(5)).baby
    expect(baby.techniques).toContainEqual({ id: universal.id, uses: 9, level: 2 })
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
    expect(r.result!.baby.stats.POW).toBeGreaterThan(mixBreeds(r.result!.outcome.breed, r.result!.outcome.breed).base.POW)
    expect(findRelative(r.state, 'p1')?.id).toBe('p1')
    expect(r.state.encyclopedia.breeds).toContain(r.result!.outcome.breed)
    expect(r.result!.baby.subBreed).toBe(r.result!.baby.mainBreed)
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

  it('records a surprise as a found recipe once, and never records the parents’ breeds', () => {
    const fused = Array.from({ length: 40 }, (_, seed) => fuse(setup(false), 'p1', 'p2', null, 'baby', createRng(seed)))
    const surprise = fused.find((r) => r.result!.outcome.source === 'surprise')!
    const parent = fused.find((r) => r.result!.outcome.source !== 'surprise')!
    expect(surprise.result!.newFind).toBe(true)
    expect(surprise.state.fusionFinds).toEqual([findKey('puddlepup', 'tumblefox', surprise.result!.baby.mainBreed)])
    expect(parent.result!.newFind).toBe(false)
    expect(parent.state.fusionFinds).toEqual([])
    // The same find again is not new and is not stored twice.
    const again = setup(false)
    again.fusionFinds = [...surprise.state.fusionFinds]
    const seed = fused.indexOf(surprise)
    const r = fuse(again, 'p1', 'p2', null, 'baby', createRng(seed))
    expect(r.result!.newFind).toBe(false)
    expect(r.state.fusionFinds).toEqual(again.fusionFinds)
  })
})
