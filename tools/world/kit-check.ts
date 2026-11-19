/**
 * The 3D world (docs/WORLD_3D.md §1), W0: the Vale kit's Blender scripts run on their own in this repo.
 *
 *   npm run world:kit-check [-- --no-build]
 *
 * Runs Wildsong's copy (tools/blender/world/gvkit/env/build_kit_vale.py, Blender 5.2 headless, no renders, no Unity
 * FBX), whose outputs land in tools/blender/out/world/gvkit/ (the `# WS:` patch in gvkit/lib/common.py), then compares
 * the manifest it writes with the snapshot's (tools/world/gloamvault/kit/vale.json): the same pieces with the same
 * triangle counts, so the town can gain our own pieces later without Gloamvault. A heavy build: run it through
 * tools/blender/slot.sh.
 */
import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')
const OUT = join(ROOT, 'tools', 'blender', 'out', 'world', 'gvkit')
const BUILT = join(OUT, 'client', 'public', 'models', 'env', 'vale.json')
const SNAP = join(HERE, 'gloamvault', 'kit', 'vale.json')
const SCRIPT = join(ROOT, 'tools', 'blender', 'world', 'gvkit', 'env', 'build_kit_vale.py')

function findBlender(): string {
  const c = [process.env.BLENDER, 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'].filter((p): p is string => !!p)
  for (const p of c) if (existsSync(p)) return p
  return 'blender'
}

type Manifest = { palette: string[]; pieces?: Record<string, { tris: number }> } & Record<string, unknown>

/** The manifest's pieces, whether they sit under `pieces` or at the top level beside `palette`. */
function pieces(m: Manifest): Record<string, number> {
  const src = (m.pieces ?? m) as Record<string, unknown>
  const out: Record<string, number> = {}
  for (const [id, v] of Object.entries(src)) if (v && typeof v === 'object' && 'tris' in v) out[id] = (v as { tris: number }).tris
  return out
}

if (!process.argv.includes('--no-build')) {
  mkdirSync(OUT, { recursive: true })
  const t0 = Date.now()
  const r = spawnSync(findBlender(), ['-b', '--factory-startup', '--python-exit-code', '1', '--python', SCRIPT, '--', '--no-renders', '--no-fbx'], {
    stdio: 'inherit', cwd: ROOT, env: { ...process.env, GVKIT_ROOT: OUT },
  })
  if (r.status !== 0) { console.error(`the kit build failed (exit ${r.status})`); process.exit(1) }
  console.log(`kit built in ${((Date.now() - t0) / 60000).toFixed(1)} min`)
}

const built = pieces(JSON.parse(readFileSync(BUILT, 'utf8')) as Manifest)
const snap = pieces(JSON.parse(readFileSync(SNAP, 'utf8')) as Manifest)
const diffs: string[] = []
for (const id of Object.keys(snap)) {
  if (!(id in built)) diffs.push(`missing ${id}`)
  else if (built[id] !== snap[id]) diffs.push(`${id}: ${built[id]} tris, the snapshot has ${snap[id]}`)
}
for (const id of Object.keys(built)) if (!(id in snap)) diffs.push(`extra ${id}`)
const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0)
console.log(`built ${Object.keys(built).length} pieces / ${sum(built)} tris; snapshot ${Object.keys(snap).length} / ${sum(snap)}`)
if (diffs.length) { console.error(diffs.join('\n')); process.exit(1) }
console.log('the kit rebuilds as the snapshot has it')
