/**
 * Dev tool: simulate one whole life and print it.
 *   npm run sim:life -- <breed> <policy> [seed] [--weekly]
 *   breeds: puddlepup, tumblefox, cobblemaw, ...   policies: great, good, ok, neglect
 * Runs on Node 24 directly (TypeScript type stripping), no build step.
 */
import { BREED_IDS, type BreedId } from '../src/data/types.ts'
import { simulateLife, type PolicyName } from '../src/core/sim/lifeSim.ts'

const args = process.argv.slice(2)
const weekly = args.includes('--weekly')
const positional = args.filter((a) => !a.startsWith('--'))
const breed = (positional[0] ?? 'puddlepup').toLowerCase() as BreedId
const policyArg = (positional[1] ?? 'good').toLowerCase()
const seed = Number(positional[2] ?? 1)

const POLICY_NAMES: Record<string, PolicyName> = { great: 'Great', good: 'Good', ok: 'OK', neglect: 'Neglect' }
const policy = POLICY_NAMES[policyArg]

if (!BREED_IDS.includes(breed) || !policy || !Number.isFinite(seed)) {
  console.error(`Usage: npm run sim:life -- <breed> <great|good|ok|neglect> [seed] [--weekly]\nBreeds: ${BREED_IDS.join(', ')}`)
  process.exit(1)
}

const r = simulateLife({ breed, policy, seed, weekly })
const stats = (s: Record<string, number>) => `${s.LIF}/${s.POW}/${s.INT}/${s.SKI}/${s.SPD}/${s.DEF}`

console.log(`Wildsong Ranch life sim: ${r.breed} · policy ${r.policy} · seed ${r.seed}`)
console.log(`Born with a ${r.lifespanAtBirth}-week lifespan. Stats ${stats(r.birthStats)} (total ${Object.values(r.birthStats).reduce((a, b) => a + b, 0)}).`)
console.log('')
if (weekly) {
  for (const line of r.lines) console.log(line)
  console.log('')
}
for (const y of r.years) {
  const o = y.outcomes
  const pct = (n: number) => (y.drills ? Math.round((n * 100) / y.drills) : 0)
  console.log(
    `Year ${y.year}: total ${String(y.total).padStart(4)} (${stats(y.stats)}) · fatigue avg ${y.fatigueAvg} · stress avg ${y.stressAvg} · loyalty ${y.loyalty} · drills ${y.drills} (G ${pct(o.Great)}% S ${pct(o.Success)}% C ${pct(o.Cheat)}% F ${pct(o.Fail)}% slack ${pct(o.Slacked)}%) · rests ${y.rests} · breakdowns ${y.breakdowns}`,
  )
}
console.log('')
const how = r.endedBy === 'passed' ? 'Passed away' : r.endedBy === 'retired' ? 'Retired' : 'Stopped'
console.log(`${how} at age ${r.weeksLived} weeks (${r.lifeLivedPct}% of ${r.lifespanAtBirth}). Final stats ${stats(r.finalStats)} (total ${r.finalTotal}), loyalty ${r.finalLoyalty}.`)
const o = r.outcomes
console.log(`Drills ${r.drills}: Great ${o.Great}, Success ${o.Success}, Cheat ${o.Cheat}, Fail ${o.Fail}, Slacked ${o.Slacked}. Rests ${r.rests}, plays ${r.plays}, items ${r.itemsUsed}, requests accepted ${r.requestsAccepted} / denied ${r.requestsDenied}, breakdowns ${r.breakdowns}, illnesses ${r.illnesses}.`)
