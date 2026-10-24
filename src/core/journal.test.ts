import { describe, expect, it } from 'vitest'
import { BREEDS } from '../data/breeds.ts'
import { SECRETS } from '../data/secrets.ts'
import { encyclopediaRows, journeysDone, titleRows, updateRecordsMut, variantRows } from './journal.ts'
import { totalStats } from './monster.ts'
import { createGameState } from './state.ts'
import { makeMonster } from './test-helpers.ts'

describe('the Journal (§18)', () => {
  it('records the best total, the oldest monster and the highest generation across the ranch', () => {
    const g = createGameState({ monster: makeMonster({ stats: { POW: 300 } }) })
    const elder = makeMonster({ id: 'old' })
    elder.name = 'Old'
    elder.ageWeeks = 390
    elder.generation = 3
    g.memorial.push({ monster: elder, cause: 'passed', epitaph: '', week: 1 })
    updateRecordsMut(g)
    expect(g.records.bestTotal).toBe(totalStats(g.monster!.stats))
    expect(g.records.bestTotalName).toBe(g.monster!.name)
    expect(g.records.oldestWeeks).toBe(390)
    expect(g.records.oldestName).toBe('Old')
    expect(g.records.highestGeneration).toBe(3)
    g.monster!.stats.POW = 100
    updateRecordsMut(g)
    expect(g.records.bestTotal).toBe(totalStats({ ...g.monster!.stats, POW: 300 }))
    g.journeysBySite['iron-quarry'] = 2
    g.journeysBySite['archers-glade'] = 1
    expect(journeysDone(g)).toBe(3)
  })

  it('shows every breed as owned, awake or asleep, every variant as owned or not, and every title', () => {
    const g = createGameState({ monster: makeMonster() })
    g.encyclopedia.breeds = ['puddlepup']
    g.encyclopedia.variants = ['songheart-puddlepup']
    g.unlocked.push('zipwisp')
    const rows = encyclopediaRows(g)
    expect(rows).toHaveLength(BREEDS.length)
    expect(rows.find((r) => r.breed.id === 'puddlepup')!.status).toBe('owned')
    expect(rows.find((r) => r.breed.id === 'tumblefox')!.status).toBe('awake')
    expect(rows.find((r) => r.breed.id === 'zipwisp')!.status).toBe('awake')
    expect(rows.find((r) => r.breed.id === 'aurelwyrm')!.status).toBe('asleep')
    const variants = variantRows(g)
    expect(variants).toHaveLength(SECRETS.length)
    expect(variants.filter((v) => v.owned).map((v) => v.secret.id)).toEqual(['songheart-puddlepup'])
    g.titles = ['First Ribbon']
    const titles = titleRows(g)
    expect(titles).toHaveLength(21)
    expect(titles.filter((t) => t.earned).map((t) => t.id)).toEqual(['First Ribbon'])
  })
})
