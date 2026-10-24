import { readFileSync, writeFileSync } from 'node:fs'
import { TECHNIQUES } from '../src/data/techniques.ts'

/**
 * V1: inserts (or refreshes) the Element column in the technique tables of docs/CONTENT.md §3 / §3.1 and
 * docs/NEW_MONSTERS.md §4, after the Type column. Breed tables sit under "#### Breedname" headings; the
 * universal table under "### 3.1". Run after changing ELEMENT_OVERRIDES: node scripts/element-column.ts
 */
const byBreedName = new Map<string, Map<string, string>>()
for (const t of TECHNIQUES) {
  const key = t.breed
  if (!byBreedName.has(key)) byBreedName.set(key, new Map())
  byBreedName.get(key)!.set(t.name, t.element)
}

function process(path: string): number {
  const lines = readFileSync(path, 'utf8').split('\n')
  let breed: string | null = null
  let inTable = false
  let hasElement = false
  let changed = 0
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]!
    const h4 = /^#### (\w+)/.exec(line)
    if (h4) breed = h4[1]!.toLowerCase()
    if (/^### 3\.1 /.test(line)) breed = 'universal'
    if (/^## /.test(line) && !/^## 3\./.test(line) && !/^## 4\./.test(line)) breed = null
    if (!line.startsWith('|')) {
      inTable = false
      continue
    }
    const cells = line.split('|').map((c) => c.trim())
    // cells[0] and cells[last] are empty (leading / trailing pipes)
    if (cells[1] === 'Technique' && cells[2] === 'Family' && cells[3] === 'Type') {
      inTable = true
      hasElement = cells[4] === 'Element'
      if (!hasElement) {
        cells.splice(4, 0, 'Element')
        lines[i] = cells.join(' | ').replace(/^ \| /, '| ').replace(/ \| $/, ' |')
        // The separator row follows.
        const sep = lines[i + 1]!.split('|')
        sep.splice(4, 0, '---')
        lines[i + 1] = sep.join('|')
        i += 1
        hasElement = true
      }
      continue
    }
    if (!inTable || !breed) continue
    if (cells[1] === '---' || cells[1] === '') continue
    const map = byBreedName.get(breed)
    if (!map) continue
    const element = map.get(cells[1]!)
    if (!element) {
      console.warn(`${path}: no technique "${cells[1]}" for ${breed}`)
      continue
    }
    const current = cells[4]
    const already = ['Fire', 'Water', 'Ice', 'Lightning', 'Wind', 'Earth', 'Nature', 'Light', 'Dark', 'Sound', 'Physical'].includes(current ?? '')
    if (already) {
      if (current !== element) {
        cells[4] = element
        changed += 1
      }
    } else {
      cells.splice(4, 0, element)
      changed += 1
    }
    lines[i] = cells.join(' | ').replace(/^ \| /, '| ').replace(/ \| $/, ' |')
  }
  writeFileSync(path, lines.join('\n'), 'utf8')
  return changed
}

console.log('CONTENT.md rows updated:', process('docs/CONTENT.md'))
console.log('NEW_MONSTERS.md rows updated:', process('docs/NEW_MONSTERS.md'))
