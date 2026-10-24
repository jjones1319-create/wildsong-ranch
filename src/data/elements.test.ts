import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { assignElement, breedDefaultElement, elementOf, isMeleeName, keywordMatches } from './elements.ts'
import { BREED_TECHNIQUES, TECHNIQUES, TECHNIQUE_BY_ID, UNIVERSAL_TECHNIQUES } from './techniques.ts'
import { ELEMENTS, type Element } from './types.ts'

describe('technique elements (VISUAL_V1_EFFECTS §5)', () => {
  it('every one of the 294 techniques has an element', () => {
    expect(TECHNIQUES).toHaveLength(294)
    for (const t of TECHNIQUES) expect(ELEMENTS).toContain(t.element)
  })

  it('keyword rules fire in spec order, first category wins', () => {
    expect(elementOf({ name: 'Furnace Crush', breed: 'hearthwing', type: 'POW' })).toBe('Fire')
    expect(elementOf({ name: 'Blizzard Lance', breed: 'frostlance', type: 'INT' })).toBe('Ice')
    expect(elementOf({ name: 'Tidebreaker Clamp', breed: 'reefclaw', type: 'POW' })).toBe('Water')
    // Water before Lightning: Rainbow Arc is rain, not an arc.
    expect(elementOf({ name: 'Rainbow Arc', breed: 'nimbusheep', type: 'INT' })).toBe('Water')
    // Earth before Sound: Croak Quake shakes the ground.
    expect(elementOf({ name: 'Croak Quake', breed: 'bloatoad', type: 'POW' })).toBe('Earth')
    // Words match whole or as a prefix, never inside another word (Resonance Drain is not rain).
    expect(keywordMatches({ name: 'Resonance Drain', breed: 'universal', type: 'INT' })).toEqual([])
    expect(elementOf({ name: 'Rainstorm Flock', breed: 'nimbusheep', type: 'INT' })).toBe('Water')
  })

  it('breed-only keywords: bolt and spark are Lightning only for Zipwisp (and Nimbusheep), shard only for Mirrorkin, crystal only for Grumblestone', () => {
    expect(TECHNIQUE_BY_ID['zipwisp.zigzag-bolt']!.element).toBe('Lightning')
    expect(TECHNIQUE_BY_ID['wishlume.glimmer-bolt']!.element).toBe('Light')
    expect(TECHNIQUE_BY_ID['gearhoot.precision-bolt']!.element).toBe('Light')
    expect(TECHNIQUE_BY_ID['universal.chime-bolt']!.element).toBe('Sound')
    expect(TECHNIQUE_BY_ID['cinderlynx.spark-pounce']!.element).toBe('Fire')
    expect(TECHNIQUE_BY_ID['mirrorkin.shard-toss']!.element).toBe('Light')
    expect(TECHNIQUE_BY_ID['grumblestone.crystal-jab']!.element).toBe('Earth')
    expect(TECHNIQUE_BY_ID['frostlance.crystal-lance-rush']!.element).toBe('Ice')
  })

  it('the named exceptions hold', () => {
    expect(TECHNIQUE_BY_ID['pluckrex.crest-flare']!.element).toBe('Light')
    expect(TECHNIQUE_BY_ID['pluckrex.sunrise-roar']!.element).toBe('Light')
    expect(TECHNIQUE_BY_ID['galeheron.lightning-stride']!.element).toBe('Wind')
    expect(TECHNIQUE_BY_ID['universal.harmony-mend']!.element).toBe('Light')
    expect(TECHNIQUE_BY_ID['universal.resonance-drain']!.element).toBe('Dark')
  })

  it('universal techniques are Sound unless a keyword says otherwise', () => {
    for (const t of UNIVERSAL_TECHNIQUES) {
      const v = assignElement({ name: t.name, breed: 'universal', type: t.type }, t.id)
      if (v.rule === 'universal → Sound') expect(t.element).toBe('Sound')
      else expect(v.rule === 'named exception' || v.rule === 'override' || v.rule.startsWith('kw ')).toBe(true)
    }
    expect(UNIVERSAL_TECHNIQUES.filter((t) => t.element === 'Sound').length).toBeGreaterThanOrEqual(16)
    expect(TECHNIQUE_BY_ID['universal.beat-bump']!.element).toBe('Sound')
  })

  it('plain melee names are Physical regardless of breed; other names take the breed default (INT / POW split)', () => {
    expect(isMeleeName('Beak Jab')).toBe('jab')
    expect(isMeleeName('Puddle Party')).toBeNull()
    expect(TECHNIQUE_BY_ID['galeheron.beak-jab']!.element).toBe('Physical')
    expect(TECHNIQUE_BY_ID['nimbusheep.woolly-bump']!.element).toBe('Physical')
    expect(TECHNIQUE_BY_ID['puddlepup.frill-flick']!.element).toBe('Water')
    expect(TECHNIQUE_BY_ID['quillion.riposte']!.element).toBe('Physical')
    expect(breedDefaultElement('gearhoot', 'INT')).toBe('Light')
    expect(breedDefaultElement('gearhoot', 'POW')).toBe('Physical')
    expect(TECHNIQUE_BY_ID['gearhoot.calibrated-shot']!.element).toBe('Light')
    expect(TECHNIQUE_BY_ID['gearhoot.talon-tick']!.element).toBe('Physical')
    expect(TECHNIQUE_BY_ID['aurelwyrm.sovereign-crush']!.element).toBe('Physical')
    expect(TECHNIQUE_BY_ID['aurelwyrm.dragons-glare']!.element).toBe('Fire')
  })

  it('every element is used by someone, and Physical is the most common', () => {
    const counts = new Map<Element, number>()
    for (const t of TECHNIQUES) counts.set(t.element, (counts.get(t.element) ?? 0) + 1)
    for (const e of ELEMENTS) expect(counts.get(e) ?? 0).toBeGreaterThan(0)
    expect(counts.get('Physical')).toBeGreaterThan(40)
  })

  it('the Element column in CONTENT §3 / §3.1 and NEW_MONSTERS §4 matches the data', () => {
    const check = (path: string, breedsInFile: Set<string>) => {
      const lines = readFileSync(path, 'utf8').split('\n')
      let breed: string | null = null
      let header: string[] | null = null
      let rows = 0
      for (const line of lines) {
        const h4 = /^#### (\w+)/.exec(line)
        if (h4) breed = h4[1]!.toLowerCase()
        if (/^### 3\.1 /.test(line)) breed = 'universal'
        if (/^## /.test(line) && !/^## [34]\./.test(line)) breed = null
        if (!line.startsWith('|')) {
          header = null
          continue
        }
        const cells = line.split('|').map((c) => c.trim())
        if (cells[1] === 'Technique') {
          header = cells
          expect(header[4]).toBe('Element')
          continue
        }
        if (!header || !breed || cells[1] === '---') continue
        const tech = (breed === 'universal' ? UNIVERSAL_TECHNIQUES : BREED_TECHNIQUES.filter((t) => t.breed === breed)).find((t) => t.name === cells[1])
        expect(tech, `${path}: ${breed} / ${cells[1]}`).toBeDefined()
        expect(cells[4], `${path}: ${tech!.id}`).toBe(tech!.element)
        breedsInFile.add(breed)
        rows += 1
      }
      return rows
    }
    const content = new Set<string>()
    expect(check('docs/CONTENT.md', content)).toBe(294)
    expect(content.size).toBe(31)
    const extra = new Set<string>()
    expect(check('docs/NEW_MONSTERS.md', extra)).toBe(90)
    expect(extra.size).toBe(10)
  })
})
