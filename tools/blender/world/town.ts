/**
 * Tunewick from Ashbrook (docs/WORLD_3D.md §3): the town from the Gloamvault snapshot, laid out, built in Blender and
 * reviewed. W0 runs the check; C1 adds the bake, export and ship stages to this same tool.
 *
 *   npm run art:town -- [--stages layout,build,review,sheet] [--quick] [--gv <Gloamvault folder>]
 *
 * layout   tools/world/town-layout.ts → tools/blender/out/world/town/{layout.json, ground.f32, ground.u8}
 * build    headless Blender (tools/blender/world/town.py): the kit decoded and placed, the ground, roads and slab
 * review   EEVEE stills from the layout's cameras → tools/blender/out/world/town/review/
 * sheet    art-review/world/town-review.png: each of Gloamvault's three town shots (right) beside ours from the same
 *          camera (left); and town-top.png, town-overview.png. Gloamvault's shots are read from its folder (review
 *          only; nothing in the build needs it) and the sheet shows ours alone when it isn't there.
 */
import { execFileSync, spawnSync } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { loadLand } from '../../world/land/data.ts'
import { createLand } from '../../world/land/land.ts'
import { buildTownLayout, readKitManifest } from '../../world/town-layout.ts'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..', '..')
const OUT = join(ROOT, 'tools', 'blender', 'out', 'world', 'town')
const REVIEW = join(ROOT, 'art-review', 'world')
const SNAP = join(ROOT, 'tools', 'world', 'gloamvault')
const FFMPEG: string = createRequire(import.meta.url)('ffmpeg-static')

const args = process.argv.slice(2)
const arg = (f: string) => (args.includes(f) ? args[args.indexOf(f) + 1] : undefined)
const stages = (arg('--stages') ?? 'layout,build,review,sheet').split(',')
const GV = arg('--gv') ?? join(ROOT, '..', 'Gloamvault Open World')

function findBlender(): string {
  const c = [process.env.BLENDER, 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'].filter((p): p is string => !!p)
  for (const p of c) if (existsSync(p)) return p
  return 'blender'
}

if (stages.includes('layout')) {
  const t0 = Date.now()
  const layout = buildTownLayout(createLand(loadLand()), readKitManifest(join(SNAP, 'kit', 'vale.json')), OUT)
  console.log(`layout: ${JSON.stringify(layout.counts)} in ${((Date.now() - t0) / 1000).toFixed(1)} s`)
}

const blenderStages = stages.filter(s => s === 'build' || s === 'review')
if (blenderStages.length) {
  const r = spawnSync(findBlender(), ['-b', '--factory-startup', '--python-exit-code', '1', '--python', join(HERE, 'town.py'), '--',
    '--layout', join(OUT, 'layout.json'), '--kit', join(SNAP, 'kit', 'kit_vale.glb'), '--out', OUT, '--stages', blenderStages.join(','),
    ...(args.includes('--quick') ? ['--quick'] : [])], { stdio: 'inherit', cwd: ROOT })
  if (r.status !== 0) { console.error(`Blender failed (exit ${r.status}); see tools/blender/out/world/town/town.log`); process.exit(1) }
}

if (stages.includes('sheet')) {
  mkdirSync(REVIEW, { recursive: true })
  const shots: [string, string][] = [['town-square', 'town-square.png'], ['town-gate', 'town-gate.png'], ['town-shops', 'town-shops.png']]
  const inputs: string[] = []
  const filters: string[] = []
  const rows: string[] = []
  shots.forEach(([name, gvShot], k) => {
    const ours = join(OUT, 'review', `${name}.png`)
    const theirs = join(GV, 'unity', 'shots', gvShot)
    const a = inputs.length / 2
    inputs.push('-i', ours)
    filters.push(`[${a}:v]scale=1170:540,setsar=1[o${k}]`)
    if (existsSync(theirs)) {
      const b = inputs.length / 2
      inputs.push('-i', theirs)
      filters.push(`[${b}:v]scale=1170:540,setsar=1[g${k}]`, `[o${k}][g${k}]hstack[r${k}]`)
    } else {
      filters.push(`[o${k}]pad=2340:540:0:0:gray[r${k}]`)
    }
    rows.push(`[r${k}]`)
  })
  filters.push(`${rows.join('')}vstack=inputs=${rows.length}`)
  const sheet = join(REVIEW, 'town-review.png')
  execFileSync(FFMPEG, ['-v', 'error', '-y', ...inputs, '-filter_complex', filters.join(';'), '-frames:v', '1', sheet])
  copyFileSync(join(OUT, 'review', 'top.png'), join(REVIEW, 'town-top.png'))
  copyFileSync(join(OUT, 'review', 'overview.png'), join(REVIEW, 'town-overview.png'))
  console.log(`${sheet}\n  left: Wildsong's Blender build from the snapshot · right: Gloamvault's own shot from the same camera`)
}
