import { describe, expect, it } from 'vitest'
import { FOOD_IDS } from '../data/types.ts'
import { HEARTSTONE, VARIANTS } from '../data/tuning.ts'
import { endOfWeekTick } from './aging.ts'
import { createBattle, previewHitTenths, timerTicksFor } from './battle/engine.ts'
import type { FighterSetup } from './battle/types.ts'
import { WEEKS_PER_YEAR } from './calendar.ts'
import { foodRelation } from './food.ts'
import { techniquesOfBreed } from '../data/techniques.ts'
import { createRng } from './rng.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'
import { prizeMultiplier } from './tournament.ts'
import { perkOf, secretForPhrase, variantNameOf, variantPrizePct } from './variants.ts'

const ai = (monster: FighterSetup['monster']): FighterSetup => ({ monster, control: 'ai', personality: 'Steady' })
const opts = { seed: 1, timerTicks: timerTicksFor(60) }

describe('variant perks (CONTENT §12)', () => {
  it('finds a secret by its normalized phrase and names the variant', () => {
    expect(secretForPhrase('wildsong')?.id).toBe('songheart-puddlepup')
    expect(secretForPhrase('nothing here')).toBeNull()
    const m = makeMonster()
    expect(variantNameOf(m)).toBe('Puddlepup')
    m.variantId = 'songheart-puddlepup'
    expect(variantNameOf(m)).toBe('Songheart Puddlepup')
    expect(perkOf(m)).toBe('likesEveryFood')
  })

  it('the Songheart likes every food', () => {
    const m = makeMonster()
    m.variantId = 'songheart-puddlepup'
    for (const food of FOOD_IDS) expect(foodRelation(m, food)).toBe('liked')
    m.variantId = null
    expect(foodRelation(m, 'turnips')).toBe('disliked')
  })

  it('the Party Bloatoad loses stress on its birthday, nobody else does', () => {
    const party = makeMonster({ main: 'bloatoad', stress: 50 })
    party.variantId = 'party-bloatoad'
    party.ageWeeks = WEEKS_PER_YEAR - 1
    const r = endOfWeekTick(party, 'Standard', createRng(1))
    expect(r.monster.stress).toBe(50 - VARIANTS.birthdayStressRelief)
    expect(r.events.some((e) => e.kind === 'birthday')).toBe(true)
    const plain = makeMonster({ main: 'bloatoad', stress: 50 })
    plain.ageWeeks = WEEKS_PER_YEAR - 1
    const r2 = endOfWeekTick(plain, 'Standard', createRng(1))
    expect(r2.events.some((e) => e.kind === 'birthday')).toBe(false)
    expect(r2.monster.stress).toBe(50)
  })

  it('the Heirloom adds +3 hit to the donor’s family; the Beacon adds +5 to Far techniques', () => {
    const plain = makeMonster()
    const heir = makeMonster()
    heir.heirloom = 'Basic'
    const a = createBattle(ai(plain), ai(makeMonster()), opts)
    const b = createBattle(ai(heir), ai(makeMonster()), opts)
    const tech = plain.techniques[0]!.id
    expect(previewHitTenths(b.state, 0, tech) - previewHitTenths(a.state, 0, tech)).toBe(HEARTSTONE.heirloomHit * 10)
    const wish = makeMonster({ main: 'wishlume' })
    const beacon = makeMonster({ main: 'wishlume' })
    beacon.variantId = 'beacon-wishlume'
    const farTech = techniquesOfBreed('wishlume').find((t) => t.range === 4)!
    wish.techniques.push({ id: farTech.id, uses: 0, level: 1 })
    beacon.techniques.push({ id: farTech.id, uses: 0, level: 1 })
    const far = { id: farTech.id }
    const c = createBattle(ai(wish), ai(makeMonster()), opts)
    const d = createBattle(ai(beacon), ai(makeMonster()), opts)
    expect(previewHitTenths(d.state, 0, far!.id) - previewHitTenths(c.state, 0, far!.id)).toBe(VARIANTS.farHit * 10)
  })

  it('the Lantern-bearer’s Wither techniques carry +5 wither into the fighter setup', () => {
    const ash = makeMonster({ main: 'ashwraith' })
    ash.variantId = 'lantern-bearer-ashwraith'
    const witherTech = techniquesOfBreed('ashwraith').find((t) => t.family === 'Wither')!
    ash.techniques.push({ id: witherTech.id, uses: 0, level: 1 })
    const b = createBattle(ai(ash), ai(makeMonster()), opts)
    const refs = b.state.fighters[0]!.techniques
    expect(refs.find((t) => t.id === witherTech.id)?.witherBonus).toBe(VARIANTS.witherPlus)
    expect(refs.find((t) => t.id === ash.techniques[0]!.id)?.witherBonus).toBe(0)
  })

  it('the Gilded Lootlid earns +25 % prize money, on top of the trait and the difficulty', () => {
    const loot = makeMonster({ main: 'lootlid' })
    const state = createGameState({ monster: loot })
    expect(prizeMultiplier(state, loot)).toBe(115) // the Gilded trait alone
    loot.variantId = 'gilded-lootlid'
    expect(variantPrizePct(loot)).toBe(125)
    expect(prizeMultiplier(state, loot)).toBe(144) // 115 × 1.25 rounded
    expect(prizeMultiplier({ ...state, difficulty: 'Gentle' }, loot)).toBe(180) // 125 × 1.15 = 144 (rounded) × 1.25 = 180
  })
})
