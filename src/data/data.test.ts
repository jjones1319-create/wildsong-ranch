import { describe, expect, it } from 'vitest'
import { BREEDS, BREED_BY_ID } from './breeds.ts'
import { DRILLS, HEAVY_DRILLS, LIGHT_DRILLS } from './drills.ts'
import { FOODS } from './foods.ts'
import { ITEMS } from './items.ts'
import { JOURNEY_SITES } from './journeys.ts'
import { BREED_TECHNIQUES, TECHNIQUES, UNIVERSAL_TECHNIQUES, parseEffect, parseLearn, slugify, subQuirkOf, techniquesOfBreed } from './techniques.ts'
import { TRAITS } from './traits.ts'
import { BREED_IDS, FAMILIES, STAT_KEYS, type Family, type Technique } from './types.ts'

describe('breeds (CONTENT §2)', () => {
  it('has the 20 breeds with unique ids in table order', () => {
    expect(BREEDS).toHaveLength(20)
    expect(BREEDS.map((b) => b.id)).toEqual([...BREED_IDS])
    expect(new Set(BREEDS.map((b) => b.name)).size).toBe(20)
  })

  it('keeps every stat, grade, lifespan and guts rate inside its range', () => {
    for (const b of BREEDS) {
      for (const k of STAT_KEYS) {
        expect(b.base[k]).toBeGreaterThanOrEqual(1)
        expect(b.base[k]).toBeLessThanOrEqual(999)
      }
      expect(b.lifespan).toBeGreaterThanOrEqual(280)
      expect(b.lifespan).toBeLessThanOrEqual(480)
      expect(b.gutsRate).toBeGreaterThanOrEqual(8)
      expect(b.gutsRate).toBeLessThanOrEqual(18)
      expect(b.strength).toBeGreaterThanOrEqual(1)
      expect(b.strength).toBeLessThanOrEqual(10)
    }
  })

  it('locks exactly the 8 unlock-chain breeds', () => {
    const locked = BREEDS.filter((b) => b.availability === 'locked')
    expect(locked).toHaveLength(8)
    expect(new Set(locked.map((b) => b.unlockChain)).size).toBe(8)
    expect(BREEDS.filter((b) => b.availability === 'market' && b.marketSeason === null).map((b) => b.id)).toEqual(['puddlepup', 'tumblefox', 'quillion'])
  })

  it('spot-checks transcribed rows', () => {
    expect(BREED_BY_ID.cobblemaw.base).toEqual({ LIF: 140, POW: 120, INT: 30, SKI: 40, SPD: 30, DEF: 110 })
    expect(BREED_BY_ID.cobblemaw.grades).toEqual({ LIF: 'B', POW: 'A', INT: 'E', SKI: 'D', SPD: 'E', DEF: 'B' })
    expect(BREED_BY_ID.aurelwyrm.gutsRate).toBe(18)
    expect(BREED_BY_ID.nimbusheep.lifespan).toBe(480)
    expect(BREED_BY_ID.lootlid.trait).toBe('gilded')
  })
})

describe('traits, drills, foods, items, journeys', () => {
  it('has 20 traits, one per breed', () => {
    expect(TRAITS).toHaveLength(20)
    expect(new Set(BREEDS.map((b) => b.trait)).size).toBe(20)
  })

  it('has 6 light drills (one per stat) and 5 heavy drills', () => {
    expect(DRILLS).toHaveLength(11)
    expect(LIGHT_DRILLS.map((d) => d.main)).toEqual([...STAT_KEYS])
    expect(HEAVY_DRILLS).toHaveLength(5)
    expect(HEAVY_DRILLS.filter((d) => d.main === 'SKI')).toHaveLength(0)
    expect(HEAVY_DRILLS.filter((d) => d.needsTrainingYard).map((d) => d.id)).toEqual(['quarry-haul'])
  })

  it('has 7 foods and a sensible price ladder', () => {
    expect(FOODS).toHaveLength(7)
    expect(FOODS.map((f) => f.price)).toEqual([20, 100, 120, 150, 300, 450, 500])
  })

  it('has every item from CONTENT §6 with unique ids', () => {
    expect(new Set(ITEMS.map((i) => i.id)).size).toBe(ITEMS.length)
    const byCategory = (c: string) => ITEMS.filter((i) => i.category === c)
    expect(byCategory('sweet')).toHaveLength(13)
    expect(byCategory('tonic')).toHaveLength(6)
    expect(byCategory('toy')).toHaveLength(6)
    expect(byCategory('charm')).toHaveLength(6)
    expect(byCategory('fruit')).toHaveLength(2)
    expect(byCategory('key')).toHaveLength(5)
    expect(byCategory('sellable')).toHaveLength(4)
    expect(byCategory('catalyst')).toHaveLength(8)
  })

  it('has the 5 mentor sites with their stat and family', () => {
    expect(JOURNEY_SITES.map((s) => [s.stat, s.family])).toEqual([
      ['POW', 'Heavy'],
      ['SPD', 'Sharp'],
      ['INT', 'Wither'],
      ['SKI', 'Hit'],
      ['DEF', 'Special'],
    ])
  })
})

describe('techniques (CONTENT §3)', () => {
  it('has 180 breed techniques + 24 universal with unique ids', () => {
    expect(BREED_TECHNIQUES).toHaveLength(180)
    expect(UNIVERSAL_TECHNIQUES).toHaveLength(24)
    expect(new Set(TECHNIQUES.map((t) => t.id)).size).toBe(204)
  })

  it('gives every breed 2 Basics, one of each other family, one sub-quirk Basic and at least 3 ranges', () => {
    for (const breed of BREED_IDS) {
      const kit = techniquesOfBreed(breed)
      expect(kit).toHaveLength(9)
      const count = (f: Family) => kit.filter((t) => t.family === f).length
      expect(count('Basic')).toBe(2)
      for (const f of FAMILIES.filter((f) => f !== 'Basic')) expect(count(f)).toBe(1)
      const quirks = kit.filter((t) => t.subQuirk)
      expect(quirks).toHaveLength(1)
      expect(quirks[0]!.family).toBe('Basic')
      expect(subQuirkOf(breed).id).toBe(quirks[0]!.id)
      expect(new Set(kit.map((t) => t.range)).size).toBeGreaterThanOrEqual(3)
    }
  })

  it('parses learn requirements and chain bases into real technique ids', () => {
    const byId = new Map(TECHNIQUES.map((t) => [t.id, t]))
    for (const t of BREED_TECHNIQUES) {
      if (t.learn.kind === 'journey' && t.learn.chainOf) {
        expect(t.family).toBe('Chain')
        expect(byId.has(t.learn.chainOf)).toBe(true)
      }
      if (t.family === 'Chain') expect(t.learn.kind === 'journey' && t.learn.chainOf !== null).toBe(true)
      if (t.family === 'Signature') expect(t.learn.kind).toBe('signature')
      if (t.family === 'Basic') expect(t.learn.kind).toBe('starter')
      if (t.family === 'Special') expect(t.learn.kind === 'journey' && t.learn.gradeMin === 'B').toBe(true)
    }
    expect(parseLearn("Archer's Glade: Foxfire Flicker Lv3 + INT ≥ 520", 'tumblefox')).toEqual({
      kind: 'journey',
      site: 'archers-glade',
      stats: ['INT'],
      value: 520,
      chainOf: 'tumblefox.foxfire-flicker',
      gradeMin: null,
    })
    expect(parseLearn('Glacier Bastion: DEF+POW ≥ 820 · grade B+', 'cobblemaw')).toMatchObject({ stats: ['DEF', 'POW'], value: 820, gradeMin: 'B' })
    expect(parseEffect('3 hits')).toEqual({ kind: 'multi', hits: 3 })
    expect(parseEffect('miss: self-dmg 12% max HP')).toEqual({ kind: 'recoil', pct: 12 })
    expect(slugify("Will-o'-Blaze")).toBe('will-o-blaze')
    expect(slugify('Jackpot!')).toBe('jackpot')
  })

  it('prices Songsheets by family and never sells Signatures', () => {
    for (const t of TECHNIQUES) {
      if (t.family === 'Basic' && t.breed !== 'universal') expect(t.sheet).toBeNull()
      if (t.family === 'Signature') expect(t.sheet?.sold).toBe(false)
      if (t.breed === 'universal') expect(t.sheet?.sold).toBe(true)
    }
    const heavyUniversal = UNIVERSAL_TECHNIQUES.find((t) => t.name === 'Crescendo Slam')!
    expect(heavyUniversal.sheet).toEqual({ price: 2500, rankMin: 4, sold: true })
    const basicUniversal = UNIVERSAL_TECHNIQUES.find((t) => t.name === 'Beat Bump')!
    expect(basicUniversal.sheet).toEqual({ price: 500, rankMin: 1, sold: true })
  })

  it('stays inside the §10.2 value bands except for the known CONTENT exceptions', () => {
    // CONTENT wins for data; these rows sit just outside a band and are reported, not changed.
    const bands: Partial<Record<Family, { guts: [number, number]; force: [number, number]; hit: [number, number]; wither: [number, number]; sharp: [number, number]; anim: number }>> = {
      Basic: { guts: [10, 14], force: [10, 14], hit: [3, 8], wither: [5, 8], sharp: [5, 8], anim: 24 },
      Hit: { guts: [16, 20], force: [14, 19], hit: [14, 20], wither: [6, 10], sharp: [6, 10], anim: 27 },
      Heavy: { guts: [42, 50], force: [50, 64], hit: [-12, -6], wither: [10, 14], sharp: [8, 12], anim: 39 },
      Wither: { guts: [24, 30], force: [12, 18], hit: [-2, 4], wither: [36, 55], sharp: [4, 8], anim: 30 },
      Sharp: { guts: [24, 30], force: [22, 30], hit: [-4, 2], wither: [8, 12], sharp: [26, 34], anim: 30 },
    }
    const violations: string[] = []
    const check = (t: Technique, field: keyof typeof t, range: [number, number]) => {
      const v = t[field] as number
      if (v < range[0] || v > range[1]) violations.push(`${t.id} ${field}=${v} (band ${range[0]}..${range[1]})`)
    }
    for (const t of TECHNIQUES) {
      const band = bands[t.family]
      if (!band) continue
      check(t, 'cost', band.guts)
      check(t, 'force', band.force)
      check(t, 'hit', band.hit)
      check(t, 'wither', band.wither)
      check(t, 'sharp', band.sharp)
      if (t.anim !== band.anim) violations.push(`${t.id} anim=${t.anim}`)
    }
    expect(violations).toEqual([
      'moatshell.turret-toss sharp=4 (band 5..8)',
      'wishlume.wishlight-flash sharp=4 (band 5..8)',
      'wishlume.glimmer-bolt force=13 (band 14..19)',
      'nimbusheep.rainbow-arc hit=-5 (band -4..2)',
      'galeheron.tempest-dive hit=-13 (band -12..-6)',
      'nibblegrub.wriggle-roll sharp=4 (band 5..8)',
      'velvesper.moonbeam-dart hit=13 (band 14..20)',
      'ashwraith.ghostflame-dart hit=-5 (band -4..2)',
      'reefclaw.pincer-pinch sharp=4 (band 5..8)',
      'lootlid.coin-toss sharp=4 (band 5..8)',
      'universal.piccolo-dart hit=13 (band 14..20)',
      'universal.fortissimo-blast hit=-13 (band -12..-6)',
    ])
  })
})
