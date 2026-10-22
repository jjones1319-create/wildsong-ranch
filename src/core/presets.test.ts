import { describe, expect, it } from 'vitest'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { PRESETS, SONGBOOK } from '../data/tuning.ts'
import { BREED_IDS } from '../data/types.ts'
import { stageOf, totalStats } from './monster.ts'
import { allPresets, firstWeekOfStage, isPresetId, makePreset, PRESET_TIERS } from './presets.ts'
import { canLearn } from './songbook.ts'

describe('presets (§19)', () => {
  const all = allPresets()

  it('has one of every tier for every breed, with unique stable ids', () => {
    expect(all).toHaveLength(BREED_IDS.length * PRESET_TIERS.length)
    expect(new Set(all.map((p) => p.id)).size).toBe(all.length)
    expect(all.every((p) => isPresetId(p.id) && p.monster.id === p.id)).toBe(true)
    expect(all.every((p) => p.monster.flags.pure && !p.monster.flags.edited)).toBe(true)
  })

  it('babies are newborn and trained presets hit their totals at the start of Prime', () => {
    for (const p of all) {
      if (p.tier === 'baby') {
        expect(p.monster.ageWeeks).toBe(0)
        expect(p.monster.grade).toBe('E')
        continue
      }
      const t = PRESETS.tiers[p.tier]
      expect(totalStats(p.monster.stats)).toBe(t.total)
      expect(stageOf(p.monster)).toBe(PRESETS.stage)
      expect(p.monster.grade).toBe(p.tier)
      expect(p.monster.fame).toBe(t.fame)
      expect(p.monster.records.wins).toBe(t.wins)
    }
  })

  it('trained presets know only techniques their breed could learn, under the cap, with matching mastery', () => {
    for (const p of all) {
      const ids = p.monster.techniques.map((x) => x.id)
      expect(ids.length).toBeLessThanOrEqual(SONGBOOK.maxTechniques)
      expect(new Set(ids).size).toBe(ids.length)
      const probe = structuredClone(p.monster)
      probe.techniques = []
      for (const slot of p.monster.techniques) {
        expect(TECHNIQUE_BY_ID[slot.id]).toBeDefined()
        expect(canLearn(probe, slot.id).ok).toBe(true)
        expect(slot.level).toBe(slot.uses >= SONGBOOK.lv3Uses ? 3 : slot.uses >= SONGBOOK.lv2Uses ? 2 : 1)
      }
      if (p.tier === 'S') expect(ids.some((id) => TECHNIQUE_BY_ID[id]!.family === 'Signature')).toBe(true)
      if (p.tier !== 'baby') expect(ids.length).toBe(Math.min(PRESETS.tiers[p.tier].techniques, SONGBOOK.maxTechniques))
    }
  })

  it('is deterministic', () => {
    expect(makePreset('zipwisp', 'A')).toEqual(makePreset('zipwisp', 'A'))
    expect(makePreset('zipwisp', 'A').likes).toEqual(allPresets().find((p) => p.id === 'preset.zipwisp.A')!.monster.likes)
  })

  it('firstWeekOfStage finds the first week of a stage', () => {
    const m = makePreset('puddlepup', 'baby')
    for (let stage = 1; stage <= 10; stage++) {
      const week = firstWeekOfStage(m, stage)
      expect(stageOf({ ...m, ageWeeks: week })).toBe(stage)
      if (week > 0) expect(stageOf({ ...m, ageWeeks: week - 1 })).toBe(stage - 1)
    }
  })
})
