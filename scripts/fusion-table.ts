import { fusionSurprises, surpriseScores } from '../src/core/fusion.ts'
import { BREED_BY_ID, STARTING_UNLOCKED } from '../src/data/breeds.ts'
import { BREED_KINDS, FUSION_RECIPES, FUSION_RULES } from '../src/data/fusionRecipes.ts'
import { BREED_IDS, type BreedId } from '../src/data/types.ts'

/**
 * Prints Fusion 2's surprise table (GAME_DESIGN §15, CONTENT §2.3) so the kinds and recipes can be tuned by eye.
 *   node scripts/fusion-table.ts               → every pair of the 22 starting breeds and its two surprises
 *   node scripts/fusion-table.ts --all         → the same with all 30 breeds unlocked
 *   node scripts/fusion-table.ts --summary     → per-breed counts, idle rules, weak picks, recipes waiting on a lock
 *   node scripts/fusion-table.ts --pair a b    → one pair's full scored list
 */
const args = process.argv.slice(2)
const unlocked: readonly BreedId[] = args.includes('--all') ? BREED_IDS : STARTING_UNLOCKED
const name = (id: BreedId) => BREED_BY_ID[id].name
const kinds = (id: BreedId) => BREED_KINDS[id].join('·')

const pairAt = args.indexOf('--pair')
if (pairAt >= 0) {
  const a = args[pairAt + 1] as BreedId
  const b = args[pairAt + 2] as BreedId
  console.log(`${name(a)} (${kinds(a)}) + ${name(b)} (${kinds(b)})`)
  for (const s of surpriseScores(a, b, unlocked)) console.log(`  ${String(s.score).padStart(3)}  ${name(s.breed)} (${kinds(s.breed)})`)
  process.exit(0)
}

const pairs: [BreedId, BreedId][] = []
for (let i = 0; i < unlocked.length; i++) for (let j = i; j < unlocked.length; j++) pairs.push([unlocked[i]!, unlocked[j]!])

if (!args.includes('--summary')) {
  console.log('| First | Second | Surprise 20% | Surprise 10% | Top score |')
  console.log('|---|---|---|---|---|')
  for (const [a, b] of pairs) {
    const s = surpriseScores(a, b, unlocked)
    console.log(`| ${name(a)} | ${name(b)} | ${s[0] ? name(s[0].breed) : '—'} | ${s[1] ? name(s[1].breed) : '—'} | ${s[0]?.score ?? 0} |`)
  }
} else {
  const first: Record<string, number> = {}
  const second: Record<string, number> = {}
  for (const [a, b] of pairs) {
    const [s1, s2] = fusionSurprises(a, b, unlocked)
    if (s1) first[s1] = (first[s1] ?? 0) + 1
    if (s2) second[s2] = (second[s2] ?? 0) + 1
  }
  console.log(`${pairs.length} pairs, ${unlocked.length} breeds unlocked`)
  console.log('Breed            20%  10%  total')
  for (const id of unlocked) {
    const f = first[id] ?? 0
    const s = second[id] ?? 0
    console.log(`${name(id).padEnd(16)} ${String(f).padStart(3)}  ${String(s).padStart(3)}  ${String(f + s).padStart(5)}`)
  }
  const idle = FUSION_RULES.filter((r) => !pairs.some(([a, b]) => {
    const ka = BREED_KINDS[a]
    const kb = BREED_KINDS[b]
    const fires = (ka.includes(r.a) && kb.includes(r.b)) || (ka.includes(r.b) && kb.includes(r.a))
    return fires && unlocked.some((c) => c !== a && c !== b && BREED_KINDS[c].includes(r.makes))
  }))
  console.log('Rules that never pick anything:', idle.map((r) => `${r.a}+${r.b}→${r.makes}`).join(', ') || 'none')
  const weak = pairs.filter(([a, b]) => (surpriseScores(a, b, unlocked)[0]?.score ?? 0) <= 1)
  console.log(`Weak top picks (score ≤ 1): ${weak.length}`)
  for (const [a, b] of weak) console.log(`  ${name(a)} + ${name(b)} → ${fusionSurprises(a, b, unlocked).map(name).join(', ')}`)
  const waiting = FUSION_RECIPES.filter((r) => !unlocked.includes(r.makes))
  console.log('Recipes waiting on a locked breed:', waiting.map((r) => `${name(r.a)} + ${name(r.b)} → ${name(r.makes)}`).join('; ') || 'none')
}
