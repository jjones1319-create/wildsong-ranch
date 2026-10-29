/**
 * Art 2.0 (ART_2_PLAN §3.1): build one look end to end.
 *
 *   npm run art:monster -- <breed> [--quick] [--stages model,clips,export,review] [--sheets ...] [--clips ...]
 *
 * Runs headless Blender (tools/blender/monsters/build.py, logging to tools/blender/out/<look>/build.log), then
 * the optimiser (tools/art/optimize.ts) that writes public/models/monsters/<look>.glb and .json.
 */
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { optimizeLook } from './optimize.ts'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')

export function findBlender(): string {
  const candidates = [
    process.env.BLENDER,
    'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe',
    'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe',
    'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe',
  ].filter((p): p is string => !!p)
  for (const c of candidates) if (existsSync(c)) return c
  return 'blender'
}

const [breed, ...rest] = process.argv.slice(2)
if (!breed) {
  console.error('usage: npm run art:monster -- <breed> [--quick] [--stages model,clips,export,review] [--sheets a,b] [--clips a,b]')
  process.exit(1)
}
const stages = rest.includes('--stages') ? rest[rest.indexOf('--stages') + 1]! : 'model,clips,export'
const args = ['-b', '--factory-startup', '--python', join(ROOT, 'tools', 'blender', 'monsters', 'build.py'), '--', '--breed', breed, '--stages', stages]
if (rest.includes('--quick')) args.push('--quick')
for (const flag of ['--sheets', '--clips']) if (rest.includes(flag)) args.push(flag, rest[rest.indexOf(flag) + 1]!)
const blender = findBlender()
console.log(`${blender} ${args.join(' ')}`)
const r = spawnSync(blender, args, { stdio: 'inherit', cwd: ROOT })
if (r.status !== 0) {
  console.error(`Blender exited with ${r.status}; see tools/blender/out/${breed}/build.log`)
  process.exit(r.status ?? 1)
}
if (stages.split(',').includes('export')) {
  const report = await optimizeLook(breed)
  console.log(`${breed}: ${(report.bytes / 1024).toFixed(0)} KB · ${report.triangles} tris · ${report.joints} joints · animations ${(report.animationBytes / 1024).toFixed(0)} KB`)
  for (const p of report.problems) console.log(`  PROBLEM ${p}`)
  if (report.problems.length) process.exit(1)
}
