import { describe, expect, it } from 'vitest'
import { EXPEDITION_SITES, EXPEDITION_SITE_BY_ID } from '../data/expeditions.ts'
import { ITEM_BY_ID } from '../data/items.ts'
import { EXPEDITION } from '../data/tuning.ts'
import { EXPEDITION_SITE_IDS, STAT_KEYS, type ExpeditionSiteId, type Stats } from '../data/types.ts'
import { weekIndexOf } from './calendar.ts'
import { buildMap, canStartExpedition, detour, expeditionMap, fogLostPct, movesFrom, moveTo, retreat, spineCost, staminaFor, startExpedition, turnBack, type ExpeditionMap } from './expedition.ts'
import { actionMenu, beginWeek, chooseAction, finishWeek } from './game.ts'
import { createRng, type Rng } from './rng.ts'
import { createGameState, type GameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

const at = (year: number, month: number, week: number) => weekIndexOf({ year, month, week })
const SEEDS = 200

/** A monster that meets a site's stated thresholds exactly, and nothing more (LIF 1 unless an obstacle needs it). */
function thresholdStats(site: ExpeditionSiteId, extra: Partial<Stats> = {}): Partial<Stats> {
  const out: Partial<Stats> = { LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 1, DEF: 1 }
  for (const ob of EXPEDITION_SITE_BY_ID[site].obstacles) out[ob.stat] = Math.max(out[ob.stat] ?? 0, ob.threshold)
  return { ...out, ...extra }
}

function tripReady(site: ExpeditionSiteId, stats: Partial<Stats>, phase: 'start' | 'action' = 'action'): GameState {
  const data = EXPEDITION_SITE_BY_ID[site]
  const m = makeMonster({ stats })
  m.lifespanTotal = 400
  m.ageWeeks = 60
  m.grade = data.gradeMin
  m.fame = data.fameMin
  const g = createGameState({ monster: m })
  g.week = at(1, data.months[0]!, 1)
  g.weekPhase = phase
  return g
}

/** On the map of a chosen seed, standing at the trailhead. */
function onMap(site: ExpeditionSiteId, seed: number, stats: Partial<Stats>, visit = 1): GameState {
  const g = tripReady(site, stats)
  g.unlocks.expeditionsBySite[site] = visit - 1
  const s = startExpedition(g, site, createRng(9))
  const e = s.expedition!
  e.seed = seed
  e.at = buildMap(site, seed).start
  e.visited = [e.at]
  return s
}

function walkSpine(input: GameState, rng: Rng): GameState {
  const map = expeditionMap(input.expedition!)
  let s = input
  for (const id of map.spine.slice(1)) {
    const r = moveTo(s, id, rng)
    expect(r.refused).toBeNull()
    s = r.state
    expect(s.expedition!.blockedAt).toBeNull()
    if (s.expedition!.ended) break
  }
  return s
}

function reaches(map: ExpeditionMap, from: number, to: number): boolean {
  const seen = new Set<number>()
  const stack = [from]
  while (stack.length) {
    const id = stack.pop()!
    if (id === to) return true
    if (seen.has(id)) continue
    seen.add(id)
    for (const e of map.nodes[id]!.next) stack.push(e.to)
  }
  return false
}

/** An RNG whose chance rolls always succeed (fog gets you lost, the chest holds a Lootlid). */
function alwaysRng(): Rng {
  const real = createRng(1)
  return {
    getState: () => real.getState(),
    setState: (s) => real.setState(s),
    nextU32: () => real.nextU32(),
    nextFloat: () => real.nextFloat(),
    nextInt: (lo) => lo,
    chance: () => true,
    pick: (items) => items[0]!,
    weightedPick: (items) => items[0]!,
    shuffle: (items) => [...items],
  }
}

describe('the expedition map (§17)', () => {
  it('rebuilds the same map from a seed, with 12–16 stops that all reach the camp', () => {
    for (const site of EXPEDITION_SITE_IDS) {
      for (let seed = 1; seed <= SEEDS; seed++) {
        const map = buildMap(site, seed)
        expect(map).toEqual(buildMap(site, seed))
        expect(map.nodes.length).toBeGreaterThanOrEqual(EXPEDITION.map.nodes.min)
        expect(map.nodes.length).toBeLessThanOrEqual(EXPEDITION.map.nodes.max)
        expect(map.nodes[map.start]!.kind).toBe('start')
        expect(map.nodes[map.camp]!.kind).toBe('camp')
        expect(map.nodes[map.event]!.kind).toBe('event')
        expect(map.nodes[map.event]!.layer).toBe(map.layers)
        for (const n of map.nodes) {
          if (n.kind !== 'camp') expect(n.next.length, `site ${site} seed ${seed} node ${n.id}`).toBeGreaterThan(0)
          for (const e of n.next) {
            expect(map.nodes[e.to]!.layer).toBe(n.layer + 1)
            expect(e.cost).toBeGreaterThanOrEqual(EXPEDITION.stepCost.min)
            expect(e.cost).toBeLessThanOrEqual(EXPEDITION.stepCost.max)
          }
          expect(reaches(map, n.id, map.camp)).toBe(true)
        }
      }
    }
  })

  it('keeps the guaranteed route clean: stated thresholds only, no fog or hidden spots, within the base stamina', () => {
    for (const site of EXPEDITION_SITE_IDS) {
      for (let seed = 1; seed <= SEEDS; seed++) {
        const map = buildMap(site, seed)
        expect(map.spine[0]).toBe(map.start)
        expect(map.spine[map.spine.length - 1]).toBe(map.event)
        for (const id of map.spine) expect(['start', 'path', 'obstacle', 'search', 'treasure', 'event']).toContain(map.nodes[id]!.kind)
        expect(spineCost(map)).toBeLessThanOrEqual(EXPEDITION.map.spineBudget)
      }
    }
  })

  it('a monster that meets the letter exactly walks the route to the event node on every map', () => {
    for (const site of EXPEDITION_SITE_IDS) {
      for (let seed = 1; seed <= SEEDS; seed++) {
        const s = walkSpine(onMap(site, seed, thresholdStats(site)), createRng(seed))
        const e = s.expedition!
        expect(e.searched, `${site} seed ${seed}`).toContain(expeditionMap(e).event)
      }
    }
  })
})

describe('stamina, obstacles, hidden spots and fog (§17)', () => {
  it('stamina is 50 + LIF/8', () => {
    expect(staminaFor({ stats: { LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 1, DEF: 1 } })).toBe(50)
    expect(staminaFor({ stats: { LIF: 160, POW: 1, INT: 1, SKI: 1, SPD: 1, DEF: 1 } })).toBe(70)
    const s = onMap('thornwood-ruins', 3, { LIF: 400 })
    expect(s.expedition!.staminaMax).toBe(100)
  })

  it('a weak monster is blocked by an obstacle: Detour costs 10 and passes, Turn back returns to the last stop', () => {
    let found = false
    for (let seed = 1; seed <= SEEDS && !found; seed++) {
      const map = buildMap('thornwood-ruins', seed)
      const first = map.spine[1]!
      if (map.nodes[first]!.kind !== 'obstacle') continue
      found = true
      const weak = onMap('thornwood-ruins', seed, { LIF: 400 })
      const stepped = moveTo(weak, first, createRng(1))
      expect(stepped.refused).toBeNull()
      const e = stepped.state.expedition!
      expect(e.blockedAt).toBe(first)
      expect(movesFrom(stepped.state)).toEqual([])
      expect(e.log.at(-1)).toMatch(/^blocked\|/)
      const staminaBefore = e.stamina

      const around = detour(stepped.state)
      expect(around.refused).toBeNull()
      expect(around.state.expedition!.stamina).toBe(staminaBefore - EXPEDITION.detourCost)
      expect(around.state.expedition!.passed).toContain(first)
      expect(around.state.expedition!.blockedAt).toBeNull()
      expect(movesFrom(around.state).length).toBeGreaterThan(0)

      const back = turnBack(stepped.state)
      expect(back.refused).toBeNull()
      expect(back.state.expedition!.at).toBe(map.start)
      expect(back.state.expedition!.blockedAt).toBeNull()
      expect(detour(back.state).refused).toBe('notBlocked')
    }
    expect(found).toBe(true)
  })

  it('hidden spots only give loot to a monster with enough INT', () => {
    let found = false
    for (let seed = 1; seed <= SEEDS && !found; seed++) {
      const map = buildMap('thornwood-ruins', seed)
      const hidden = map.nodes.find((n) => n.layer === 1 && n.kind === 'hidden')
      if (!hidden) continue
      found = true
      const dim = moveTo(onMap('thornwood-ruins', seed, { INT: 100 }), hidden.id, createRng(1)).state.expedition!
      expect(dim.searched).not.toContain(hidden.id)
      expect(dim.loot).toEqual([])
      const bright = moveTo(onMap('thornwood-ruins', seed, { INT: 200 }), hidden.id, createRng(1)).state.expedition!
      expect(bright.searched).toContain(hidden.id)
      expect(bright.loot.length + bright.sheets.length).toBe(1)
    }
    expect(found).toBe(true)
  })

  it('fog: lost chance is max(5, 30 − INT/30); being lost costs 10 stamina and moves the party back', () => {
    expect(fogLostPct({ stats: { LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 1, DEF: 1 } })).toBe(30)
    expect(fogLostPct({ stats: { LIF: 1, POW: 1, INT: 300, SKI: 1, SPD: 1, DEF: 1 } })).toBe(20)
    expect(fogLostPct({ stats: { LIF: 1, POW: 1, INT: 999, SKI: 1, SPD: 1, DEF: 1 } })).toBe(5)
    let found = false
    for (let seed = 1; seed <= SEEDS && !found; seed++) {
      const map = buildMap('thornwood-ruins', seed)
      const fog = map.nodes.find((n) => n.layer === 2 && n.kind === 'fog' && map.nodes.some((p) => p.layer === 1 && p.next.some((e) => e.to === n.id)))
      if (!fog) continue
      const prev = map.nodes.find((p) => p.layer === 1 && p.next.some((e) => e.to === fog.id))!
      const edge = prev.next.find((e) => e.to === fog.id)!
      found = true
      const start = onMap('thornwood-ruins', seed, { LIF: 400 })
      const atPrev = moveTo(start, prev.id, createRng(1)).state
      const before = atPrev.expedition!.stamina
      const lost = moveTo(atPrev, fog.id, alwaysRng()).state.expedition!
      expect(lost.stamina).toBe(before - edge.cost - EXPEDITION.fog.lostCost)
      expect(lost.at).not.toBe(fog.id)
      expect([fog.layer, fog.layer - 1]).toContain(map.nodes[lost.at]!.layer)
      expect(lost.log.at(-1)).toBe('lost')
    }
    expect(found).toBe(true)
  })

  it('every step costs its stamina; at 0 the party limps home with everything found', () => {
    const s = onMap('thornwood-ruins', 7, thresholdStats('thornwood-ruins', { LIF: 1 }))
    const map = expeditionMap(s.expedition!)
    const first = map.spine[1]!
    const cost = map.nodes[map.start]!.next.find((e) => e.to === first)!.cost
    const stepped = moveTo(s, first, createRng(2)).state
    expect(stepped.expedition!.stamina).toBe(50 - cost)
    const tired = structuredClone(stepped)
    tired.expedition!.stamina = 1
    const next = map.nodes[first]!.next[0]!.to
    const home = moveTo(tired, next, createRng(2)).state
    expect(home.expedition!.ended).toBe('exhausted')
    expect(home.expedition!.stamina).toBe(0)
    expect(moveTo(home, next, createRng(2)).refused).toBe('ended')
    expect(home.monster!.fatigue).toBe(EXPEDITION.after.fatigue)
    expect(home.records.expeditionsDone).toBe(1)
  })

  it('Retreat keeps everything found and applies the after-effects; loot and sheets come home', () => {
    let s = onMap('thornwood-ruins', 11, thresholdStats('thornwood-ruins', { LIF: 400, INT: 999 }))
    s.monster!.stress = 30
    const rng = createRng(3)
    // Walk until something has been found.
    const map = expeditionMap(s.expedition!)
    for (const id of map.spine.slice(1)) {
      s = moveTo(s, id, rng).state
      if (s.expedition!.loot.length + s.expedition!.sheets.length > 0 || s.expedition!.ended) break
    }
    const e = s.expedition!
    const found = e.loot.length + e.sheets.length
    expect(found).toBeGreaterThan(0)
    expect(e.ended).toBeNull()
    const home = retreat(s)
    expect(home.refused).toBeNull()
    const h = home.state
    expect(h.expedition!.ended).toBe('retreat')
    for (const l of e.loot) expect(h.inventory[l.id]).toBeGreaterThanOrEqual(ITEM_BY_ID[l.id]!.category === 'toy' ? l.qty * 5 : l.qty)
    for (const id of e.sheets) expect(h.songbook).toContain(id)
    expect(h.monster!.fatigue).toBe(EXPEDITION.after.fatigue)
    expect(h.monster!.stress).toBe(30 + EXPEDITION.after.stress)
    expect(retreat(h).refused).toBe('ended')
  })

  it('loot tables only name real items and universal sheet families', () => {
    for (const site of EXPEDITION_SITES) {
      for (const table of [site.search, site.treasure, site.eventLoot]) {
        expect(table.length).toBeGreaterThan(0)
        for (const row of table) {
          expect(row.weight).toBeGreaterThan(0)
          if (row.kind === 'item') expect(ITEM_BY_ID[row.id], row.id).toBeDefined()
        }
      }
      for (const ob of site.obstacles) expect(STAT_KEYS).toContain(ob.stat)
    }
  })
})

describe('the special stops (CONTENT §8, §11)', () => {
  it('the Strange Chest holds a Lootlid about 35 % of the time, always on the third visit, never once Lootlid is awake', () => {
    let hits = 0
    for (let seed = 1; seed <= SEEDS; seed++) {
      const s = walkSpine(onMap('thornwood-ruins', seed, thresholdStats('thornwood-ruins', { LIF: 400 })), createRng(seed + 1000))
      if (s.expedition!.keyFound === 'lootlid') hits++
    }
    expect(hits / SEEDS).toBeGreaterThan(0.22)
    expect(hits / SEEDS).toBeLessThan(0.48)

    for (let seed = 1; seed <= 20; seed++) {
      const third = walkSpine(onMap('thornwood-ruins', seed, thresholdStats('thornwood-ruins', { LIF: 400 }), 3), createRng(seed))
      expect(third.expedition!.keyFound).toBe('lootlid')
      const home = retreat(third).state
      expect(home.unlocked).toContain('lootlid')
      expect(home.expedition!.lootlidPlaced).toBe('freezer')
      expect(home.freezer.map((m) => m.mainBreed)).toEqual(['lootlid'])
    }

    const awake = onMap('thornwood-ruins', 5, thresholdStats('thornwood-ruins', { LIF: 400 }), 3)
    awake.unlocked.push('lootlid')
    const again = walkSpine(awake, alwaysRng())
    expect(again.expedition!.keyFound).toBeNull()
    expect(again.expedition!.loot.length).toBeGreaterThan(0)
  })

  it('a Lootlid with nowhere to go still wakes the breed', () => {
    const s = onMap('thornwood-ruins', 8, thresholdStats('thornwood-ruins', { LIF: 400 }), 3)
    s.freezer = Array.from({ length: 20 }, (_, i) => makeMonster({ id: `f${i}` }))
    const home = retreat(walkSpine(s, createRng(1))).state
    expect(home.unlocked).toContain('lootlid')
    expect(home.expedition!.lootlidPlaced).toBe('none')
    expect(home.freezer).toHaveLength(20)
  })

  it('the Sunken Library archive gives the Brass Blueprint only at INT 350, and only once', () => {
    const clever = walkSpine(onMap('sunken-library', 4, thresholdStats('sunken-library', { INT: 350 })), createRng(4))
    expect(clever.expedition!.keyFound).toBe('brass-blueprint')
    const home = retreat(clever).state
    expect(home.inventory['brass-blueprint']).toBe(1)
    const dim = walkSpine(onMap('sunken-library', 4, thresholdStats('sunken-library', { INT: 340 })), createRng(4))
    expect(dim.expedition!.keyFound).toBeNull()
    expect(dim.expedition!.loot.length + dim.expedition!.sheets.length).toBeGreaterThan(0)
    const owner = onMap('sunken-library', 4, thresholdStats('sunken-library', { INT: 350 }))
    owner.inventory['brass-blueprint'] = 1
    expect(walkSpine(owner, createRng(4)).expedition!.keyFound).toBeNull()
  })

  it('the crystal heart gives an Amber Charm; the sky puzzle a Special sheet at INT 400, a Starstone otherwise', () => {
    const heart = walkSpine(onMap('hollowmoon-caverns', 2, thresholdStats('hollowmoon-caverns', { LIF: 400 })), createRng(2))
    expect(heart.expedition!.loot.some((l) => l.id === 'amber-charm')).toBe(true)
    const puzzle = walkSpine(onMap('skyreef-isles', 2, thresholdStats('skyreef-isles', { LIF: 400 })), createRng(2))
    expect(puzzle.expedition!.sheets.length).toBeGreaterThanOrEqual(1)
    expect(puzzle.expedition!.log.some((l) => l.startsWith('puzzle|'))).toBe(true)
    const stubborn = walkSpine(onMap('skyreef-isles', 2, thresholdStats('skyreef-isles', { LIF: 400, INT: 399, SPD: 450, DEF: 400 })), createRng(2))
    expect(stubborn.expedition!.log.some((l) => l.startsWith('puzzleMiss|'))).toBe(true)
  })
})

describe('invitations and the four weeks away (§17, §3)', () => {
  it('the trip needs the month, the grade, the fame and a free ranch', () => {
    const ok = tripReady('sunken-library', { LIF: 200 })
    expect(canStartExpedition(ok, 'sunken-library')).toEqual({ ok: true })
    expect(canStartExpedition(ok, 'thornwood-ruins')).toMatchObject({ ok: false, reason: 'closed' })
    const low = tripReady('sunken-library', {})
    low.monster!.grade = 'D'
    expect(canStartExpedition(low, 'sunken-library')).toMatchObject({ ok: false, reason: 'grade' })
    const unknown = tripReady('sunken-library', {})
    unknown.monster!.fame = 39
    expect(canStartExpedition(unknown, 'sunken-library')).toMatchObject({ ok: false, reason: 'fame' })
    const busy = tripReady('sunken-library', {})
    busy.journey = { site: 'iron-quarry', weekNo: 2, successes: 0, learned: null, pendingTechnique: null, elderMentor: false, gains: { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 } }
    expect(canStartExpedition(busy, 'sunken-library')).toMatchObject({ ok: false, reason: 'busy' })
    const sick = tripReady('sunken-library', {})
    sick.monster!.status.sickWeeks = 1
    expect(canStartExpedition(sick, 'sunken-library')).toMatchObject({ ok: false, reason: 'away' })
  })

  it('through the controller: the map is week 1, three away weeks follow, the monster ages four weeks', () => {
    const rng = createRng(77)
    let s = tripReady('thornwood-ruins', thresholdStats('thornwood-ruins', { LIF: 200 }), 'start')
    const age = s.monster!.ageWeeks
    const begun = beginWeek(s, rng)
    s = begun.state
    expect(begun.events.some((e) => e.kind === 'invitation' && e.site === 'thornwood-ruins')).toBe(true)
    expect(s.mail.some((m) => m.kind === 'expedition' && m.ref === 'thornwood-ruins')).toBe(true)
    expect(actionMenu(s).train).toBe(true)

    const started = chooseAction(s, { kind: 'expedition', site: 'thornwood-ruins' }, rng)
    s = started.state
    expect(started.events.some((e) => e.kind === 'expeditionStart')).toBe(true)
    expect(s.expedition).not.toBeNull()
    expect(s.unlocks.expeditionsBySite['thornwood-ruins']).toBe(1)
    expect(actionMenu(s)).toMatchObject({ train: false, wait: false, reason: 'expeditionMap' })
    // The week cannot end in the action phase without finishing the map: nothing else happens on a second action.
    expect(chooseAction(s, { kind: 'rest' }, rng).events.some((e) => e.kind === 'invalidAction' && e.reason === 'expeditionInProgress')).toBe(true)

    s = retreat(walkSpine(s, rng)).state
    expect(s.expedition!.ended).toBe('retreat')
    expect(actionMenu(s)).toMatchObject({ wait: true, reason: 'expedition' })
    s = finishWeek(s, rng).state

    for (let week = 2; week <= 4; week++) {
      s = beginWeek(s, rng).state
      expect(actionMenu(s)).toMatchObject({ wait: true, reason: 'expedition' })
      const r = chooseAction(s, { kind: 'none' }, rng)
      s = r.state
      if (week < 4) expect(r.events.some((e) => e.kind === 'expeditionWeek' && e.weekNo === week)).toBe(true)
      else expect(r.events.some((e) => e.kind === 'expeditionHome')).toBe(true)
      s = finishWeek(s, rng).state
    }
    expect(s.expedition).toBeNull()
    expect(s.monster!.ageWeeks).toBe(age + 4)
    expect(actionMenu(beginWeek(s, rng).state).train).toBe(true)
  })
})
