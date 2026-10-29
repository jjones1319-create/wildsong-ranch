import { describe, expect, it } from 'vitest'
import { addItems, bestCharm, charmValue, countOf, useItem, type Inventory } from './items.ts'
import { makeMonster } from './test-helpers.ts'

const bag = (entries: Record<string, number>): Inventory => ({ ...entries })

describe('items (§8): unlimited use', () => {
  it('feeds 100 Stat Sweets in one go and tracks the points that came from sweets', () => {
    const m = makeMonster()
    const r = useItem(m, bag({ 'mighty-muffin': 100 }), 'mighty-muffin', 100)
    expect(r.refused).toBeNull()
    expect(r.used).toBe(100)
    expect(r.monster.stats.POW).toBe(570)
    expect(r.monster.records.fromSweets.POW).toBe(500)
    expect(r.inventory['mighty-muffin']).toBeUndefined()
    expect(m.stats.POW).toBe(70) // input untouched
  })

  it('sweets go past the grade cap (v1.11); only the 9,999 bound stops them, and then they are not eaten', () => {
    const m = makeMonster({ stats: { INT: 1195 } }) // INT grade D: cap 1100, already above it
    const r = useItem(m, bag({ 'grand-cookie': 3 }), 'grand-cookie', 3)
    expect(r.monster.stats.INT).toBe(1240)
    expect(r.monster.records.fromSweets.INT).toBe(45)
    expect(r.used).toBe(3)
    const top = makeMonster({ stats: { INT: 9990 } })
    const t = useItem(top, bag({ 'grand-cookie': 3 }), 'grand-cookie', 3)
    expect(t.monster.stats.INT).toBe(9999)
    expect(t.monster.records.fromSweets.INT).toBe(9)
    expect(t.used).toBe(1)
    expect(t.inventory['grand-cookie']).toBe(2)
    expect(useItem(t.monster, t.inventory, 'grand-cookie', 1).refused).toBe('alreadyMaxed')
  })

  it('a Wondercake adds +5 to all six stats', () => {
    const r = useItem(makeMonster(), bag({ wondercake: 2 }), 'wondercake', 2)
    expect(r.monster.stats).toEqual({ LIF: 130, POW: 80, INT: 70, SKI: 90, SPD: 80, DEF: 80 })
  })

  it('uses only what is owned and refuses what is not', () => {
    const r = useItem(makeMonster({ fatigue: 80 }), bag({ 'sun-plum': 3 }), 'sun-plum', 10)
    expect(r.used).toBe(3)
    expect(r.monster.fatigue).toBe(50)
    expect(useItem(makeMonster(), bag({}), 'sun-plum', 1).refused).toBe('notOwned')
    expect(useItem(makeMonster(), bag({ nope: 1 }), 'nope', 1).refused).toBe('unknownItem')
  })

  it('applies recovery, mood and form items, with Calmleaf Tea halving stress', () => {
    const m = makeMonster({ fatigue: 50, stress: 50, spoil: 30, fear: 30, nature: 0 })
    expect(useItem(m, bag({ 'warm-compress': 1 }), 'warm-compress', 1).monster.fatigue).toBe(25)
    expect(useItem(m, bag({ 'lavender-sachet': 2 }), 'lavender-sachet', 2).monster.stress).toBe(30)
    expect(useItem(m, bag({ 'calmleaf-tea': 2 }), 'calmleaf-tea', 2).monster.stress).toBe(12)
    expect(useItem(m, bag({ 'berry-tart': 1 }), 'berry-tart', 1).monster.spoil).toBe(38)
    expect(useItem(m, bag({ 'thunder-rattle': 1 }), 'thunder-rattle', 1).monster.fear).toBe(38)
    expect(useItem(m, bag({ 'kindness-charm': 3 }), 'kindness-charm', 3).monster.nature).toBe(15)
    expect(useItem(m, bag({ 'leanroot-tea': 1 }), 'leanroot-tea', 1).monster.form).toBe(-10)
  })

  it('Potential Pearl steps a grade up to S and the Tempo Bell lowers the guts rate to 6', () => {
    const m = makeMonster() // INT grade D, guts 12
    const pearl = useItem(m, bag({ 'potential-pearl': 5 }), 'potential-pearl', 5, { stat: 'INT' })
    expect(pearl.monster.grades.INT).toBe('S')
    expect(pearl.used).toBe(4) // D → C → B → A → S
    expect(pearl.inventory['potential-pearl']).toBe(1)
    expect(useItem(pearl.monster, pearl.inventory, 'potential-pearl', 1, { stat: 'INT' }).refused).toBe('alreadyMaxed')
    expect(useItem(m, bag({ 'potential-pearl': 1 }), 'potential-pearl', 1).refused).toBe('needsStat')
    const bell = useItem(m, bag({ 'tempo-bell': 10 }), 'tempo-bell', 10)
    expect(bell.monster.gutsRate).toBe(6)
    expect(bell.used).toBe(6)
  })

  it('tonics run 4 weeks, stack across stats, and each use costs 6 weeks of life', () => {
    const m = makeMonster()
    const a = useItem(m, bag({ 'ironroot-tonic': 2, sagebrew: 1 }), 'ironroot-tonic', 2)
    expect(a.monster.status.tonics).toEqual({ POW: 4 })
    expect(a.monster.lifespanTotal).toBe(418 - 12)
    expect(a.lifespanChange).toBe(-12)
    const b = useItem(a.monster, a.inventory, 'sagebrew', 1)
    expect(b.monster.status.tonics).toEqual({ POW: 4, INT: 4 })
  })

  it('life fruits work exactly once per monster', () => {
    const m = makeMonster()
    const a = useItem(m, bag({ sunfruit: 3 }), 'sunfruit', 3)
    expect(a.used).toBe(1)
    expect(a.monster.lifespanTotal).toBe(458)
    expect(a.inventory.sunfruit).toBe(2)
    expect(useItem(a.monster, a.inventory, 'sunfruit', 1).refused).toBe('fruitAlreadyUsed')
    const b = useItem(a.monster, bag({ moonfruit: 1 }), 'moonfruit', 1)
    expect(b.monster.lifespanTotal).toBe(478)
  })

  it('toys come in 5 uses; the favorite toy helps more', () => {
    const inv = addItems({}, 'rubber-ball', 1)
    expect(countOf(inv, 'rubber-ball')).toBe(5)
    const m = makeMonster({ stress: 40, spoil: 30 })
    const fav = useItem(m, inv, 'rubber-ball', 1)
    expect(fav.monster).toMatchObject({ stress: 28, spoil: 34 })
    expect(fav.inventory['rubber-ball']).toBe(4)
    const other = useItem(m, addItems({}, 'music-box', 1), 'music-box', 2)
    expect(other.monster).toMatchObject({ stress: 32, spoil: 30 })
  })

  it('charms are passive and only the best per slot counts', () => {
    const inv = bag({ 'wind-chime': 1, 'gold-chime': 1, 'straw-bed': 1 })
    expect(useItem(makeMonster(), inv, 'gold-chime', 1).refused).toBe('passive')
    expect(bestCharm(inv, 'comfort')?.id).toBe('gold-chime')
    expect(charmValue(inv, 'comfort')).toBe(6)
    expect(charmValue(inv, 'bedding')).toBe(3)
    expect(charmValue({}, 'bedding')).toBe(0)
    expect(useItem(makeMonster(), bag({ 'old-coin': 1 }), 'old-coin', 1).refused).toBe('notUsable')
  })

  it('the optional one-per-week rule limits use to a single item, and only when switched on', () => {
    const m = makeMonster({ fatigue: 80 })
    const limited = useItem(m, bag({ 'sun-plum': 5 }), 'sun-plum', 5, { onePerWeek: true, usedThisWeek: 0 })
    expect(limited.used).toBe(1)
    expect(useItem(m, bag({ 'sun-plum': 5 }), 'sun-plum', 1, { onePerWeek: true, usedThisWeek: 1 }).refused).toBe('onePerWeek')
    expect(useItem(m, bag({ 'sun-plum': 5 }), 'sun-plum', 5, { onePerWeek: false, usedThisWeek: 7 }).used).toBe(5)
  })
})
