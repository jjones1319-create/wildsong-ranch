import { assignElement } from '../src/data/elements.ts'
import { TECHNIQUES } from '../src/data/techniques.ts'

/**
 * Prints the V1 element table (VISUAL_V1_EFFECTS §5) so the owner can correct rows.
 *   node scripts/element-table.ts            → markdown table
 *   node scripts/element-table.ts --summary  → counts per element and the rows worth a second look
 */
const summary = process.argv.includes('--summary')
const rows = TECHNIQUES.map((t) => {
  const v = assignElement({ name: t.name, breed: t.breed, type: t.type }, t.id)
  const flag = v.alsoMatched.length > 0 ? `? also ${v.alsoMatched.join('/')}` : ''
  return { t, v, flag }
})
if (!summary) {
  console.log('| # | Breed | Technique | Family | Type | Element | Rule | Note |')
  console.log('|---|---|---|---|---|---|---|---|')
  rows.forEach(({ t, v, flag }, i) => console.log(`| ${i + 1} | ${t.breed} | ${t.name} | ${t.family} | ${t.type} | **${v.element}** | ${v.rule} | ${flag} |`))
} else {
  const counts: Record<string, number> = {}
  for (const { v } of rows) counts[v.element] = (counts[v.element] ?? 0) + 1
  console.log(counts)
  console.log('Second look:')
  for (const { t, v, flag } of rows) if (flag) console.log(`  ${t.id}: ${v.element} (${v.rule}) ${flag}`)
}
