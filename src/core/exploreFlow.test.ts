import { describe, expect, it } from 'vitest'
import { ITEM_BY_ID } from '../data/items.ts'
import { makeSave, validateSave } from '../save/schema.ts'
import { weekIndexOf } from './calendar.ts'
import { wakeStone } from './creation.ts'
import { sellableStock, sellItem } from './economy.ts'
import { expeditionMap, moveTo, retreat } from './expedition.ts'
import { actionMenu, beginWeek, chooseAction, finishWeek } from './game.ts'
import { marketMonster } from './market.ts'
import { createRng } from './rng.ts'
import { rollShrine } from './shrine.ts'
import { createGameState, type GameState } from './state.ts'

/** A phrase whose song wakes a Lootlid (the breed is rare, so this searches a little). */
function lootlidPhrase(unlocked: readonly string[]): string {
  for (let i = 0; i < 5000; i++) {
    const phrase = `treasure song ${i}`
    if (rollShrine(phrase, '', unlocked as never).mainBreed === 'lootlid') return phrase
  }
  throw new Error('no Lootlid phrase found')
}

/**
 * BUILD_PLAN M7: a scripted player gets Tomas's letter, walks Thornwood to the Strange Chest (the third visit,
 * so the Lootlid is certain), comes home over four weeks, sells the loot, and a Sleeping Stone for the new
 * breed wakes. The final save validates round-trip.
 */
describe('exploration end to end (M7)', () => {
  it('invitation → expedition → the Lootlid → home → sell → a Sleeping Stone wakes', () => {
    const rng = createRng(2027)
    let state: GameState = createGameState({ monster: marketMonster('quillion', 'q'), breederName: 'Tester', ranchName: 'Thorn Ranch' })
    state.money = 5000
    state.monster!.fame = 20
    for (const k of ['POW', 'INT', 'SKI'] as const) state.monster!.stats[k] = 250
    state.week = weekIndexOf({ year: 1, month: 3, week: 1 })
    state.unlocks.expeditionsBySite['thornwood-ruins'] = 2
    state.sleepingStones.push({ phrase: lootlidPhrase(state.unlocked), artist: '', breed: 'lootlid', week: 0 })

    // Week 1: the letter, then off we go.
    const begun = beginWeek(state, rng, 'honey-bread')
    state = begun.state
    expect(state.mail.some((m) => m.kind === 'expedition' && m.ref === 'thornwood-ruins')).toBe(true)
    expect(state.unlocks.rumorsHeard).toContain('strange-chest')
    state = chooseAction(state, { kind: 'expedition', site: 'thornwood-ruins' }, rng).state
    expect(state.expedition).not.toBeNull()
    expect(state.expedition!.visit).toBe(3)

    // Walk the guaranteed route to the chest, then on to the camp if the legs hold.
    const map = expeditionMap(state.expedition!)
    for (const id of [...map.spine.slice(1), map.camp]) {
      if (state.expedition!.ended) break
      const r = moveTo(state, id, rng)
      expect(r.refused).toBeNull()
      state = r.state
      expect(state.expedition!.blockedAt).toBeNull()
    }
    if (!state.expedition!.ended) state = retreat(state).state
    expect(state.expedition!.keyFound).toBe('lootlid')
    expect(state.expedition!.lootlidPlaced).toBe('freezer')
    expect(state.unlocked).toContain('lootlid')
    expect(state.freezer.map((m) => m.mainBreed)).toEqual(['lootlid'])
    expect(state.monster!.fatigue).toBe(40)
    const loot = state.expedition!.loot
    for (const l of loot) expect(ITEM_BY_ID[l.id]).toBeDefined()

    // The rest of the four weeks.
    state = finishWeek(state, rng).state
    expect(state.titles).toContain('Treasure Hunter')
    for (let week = 2; week <= 4; week++) {
      state = beginWeek(state, rng).state
      expect(actionMenu(state)).toMatchObject({ wait: true, reason: 'expedition' })
      state = chooseAction(state, { kind: 'none' }, rng).state
      state = finishWeek(state, rng).state
    }
    expect(state.expedition).toBeNull()
    expect(state.monster!.ageWeeks).toBe(4)
    expect(state.records.expeditionsDone).toBe(1)

    // Basil buys the treasures.
    const stock = sellableStock(state)
    const before = state.money
    let earned = 0
    for (const s of stock) {
      const sold = sellItem(state, s.item.id, s.owned)
      expect(sold.refused).toBeNull()
      state = sold.state
      earned += sold.gold
      expect(sold.gold).toBe(s.item.sell! * s.owned)
    }
    expect(state.money).toBe(before + earned)
    expect(sellableStock(state)).toEqual([])
    expect(sellItem(state, 'sun-plum', 1).refused).toMatch(/notSellable|notOwned/)

    // The Sleeping Stone for Lootlid wakes for free now.
    const woke = wakeStone(state, 0, 'stone-lootlid')
    expect(woke.refused).toBeNull()
    expect(woke.monster!.mainBreed).toBe('lootlid')
    expect(woke.placed).toBe('freezer')
    state = woke.state
    expect(state.sleepingStones).toEqual([])
    expect(state.records.stonesWoken).toBe(1)
    expect(state.encyclopedia.combos).toContain('Lootlid')

    // Everything survives a save round trip.
    const raw = JSON.parse(JSON.stringify(makeSave(state, rng.getState())))
    const v = validateSave(raw)
    expect(v.ok).toBe(true)
    if (v.ok) expect(v.save.game).toEqual(state)
  })
})
