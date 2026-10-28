import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { BREEDS } from './breeds.ts'
import { BREED_KINDS, FUSION_RECIPES, FUSION_RULES } from './fusionRecipes.ts'
import { BREED_IDS, KINDS, type BreedId } from './types.ts'

const idOf = (name: string): BreedId => {
  const b = BREEDS.find((x) => x.name === name)
  if (!b) throw new Error(`unknown breed ${name}`)
  return b.id
}

/** The table rows (cells, trimmed) of CONTENT §2.3 whose header row starts with `first`. */
function tableRows(first: string): string[][] {
  const lines = readFileSync('docs/CONTENT.md', 'utf8').split('\n')
  const start = lines.findIndex((l) => l.startsWith('### 2.3 '))
  const end = lines.findIndex((l, i) => i > start && /^(##|---)/.test(l))
  const rows: string[][] = []
  let inTable = false
  for (const line of lines.slice(start, end)) {
    if (!line.startsWith('|')) {
      inTable = false
      continue
    }
    const cells = line.split('|').slice(1, -1).map((c) => c.trim())
    if (cells[0] === first) inTable = true
    else if (inTable && cells[0] !== '---') rows.push(cells)
  }
  return rows
}

describe('Fusion kinds and recipes (CONTENT §2.3)', () => {
  it('every breed has one or two known kinds, without repeats', () => {
    for (const id of BREED_IDS) {
      const kinds = BREED_KINDS[id]
      expect(kinds.length, id).toBeGreaterThanOrEqual(1)
      expect(kinds.length, id).toBeLessThanOrEqual(2)
      expect(new Set(kinds).size, id).toBe(kinds.length)
      for (const k of kinds) expect(KINDS).toContain(k)
    }
  })

  it('rules use known kinds and never repeat; recipes are sorted pairs of real breeds and never make a parent', () => {
    const ruleKeys = FUSION_RULES.map((r) => [r.a, r.b].sort().join('+') + '>' + r.makes)
    expect(new Set(ruleKeys).size).toBe(ruleKeys.length)
    for (const r of FUSION_RULES) for (const k of [r.a, r.b, r.makes]) expect(KINDS).toContain(k)
    const recipeKeys = FUSION_RECIPES.map((r) => `${r.a}+${r.b}>${r.makes}`)
    expect(new Set(recipeKeys).size).toBe(recipeKeys.length)
    for (const r of FUSION_RECIPES) {
      expect(r.a <= r.b, `${r.a}+${r.b}`).toBe(true)
      expect([r.a, r.b]).not.toContain(r.makes)
      for (const id of [r.a, r.b, r.makes]) expect(BREED_IDS).toContain(id)
    }
  })

  it('the code mirrors the three tables in CONTENT §2.3', () => {
    const kinds = tableRows('Breed').map(([name, list]) => [idOf(name!), list!.split('·').map((k) => k.trim())] as const)
    expect(Object.fromEntries(kinds)).toEqual(BREED_KINDS)
    expect(tableRows('One parent').map(([a, b, makes]) => ({ a, b, makes }))).toEqual(FUSION_RULES)
    const recipes = tableRows('Parents').map(([pair, makes]) => {
      const [a, b] = pair!.split('+').map((n) => idOf(n.trim()))
      return { a, b, makes: idOf(makes!) }
    })
    expect(recipes).toEqual(FUSION_RECIPES)
  })
})
