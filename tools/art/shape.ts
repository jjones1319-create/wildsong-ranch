/**
 * Art 2.1: the fast shape preview of an Ultra recipe (about a minute; flat colours, no bake), headless Blender.
 *
 *   npm run art:shape -- <breed> [--out <dir>] [--voxel 0.0065] [--noeyes]
 *
 * A grown form is a look of its own: `npm run art:shape -- hearthwing-grown` previews breeds/hearthwing_grown_ultra.py.
 * Runs tools/blender/monsters/shape_preview.py for breeds/<breed>_ultra.py and writes art-review/<breed>-shape/sheet.png
 * (and one PNG per view); the log says the model's height against the size rule (HEIGHT_UNITS / 150 m).
 */
import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const [breed, ...rest] = process.argv.slice(2)
if (!breed || breed.startsWith('--')) {
  console.error('usage: node tools/art/shape.ts <breed> [--out <dir>] [--voxel 0.0065] [--noeyes]')
  process.exit(1)
}
const at = rest.indexOf('--out')
const out = at >= 0 ? rest[at + 1]! : join(ROOT, 'art-review', `${breed}-shape`)
mkdirSync(out, { recursive: true })
const pass = rest.filter((_a, i) => i !== at && i !== at + 1 || at < 0)
const blender = [process.env.BLENDER, 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'].find((c) => c && existsSync(c)) ?? 'blender'
// a grown form's recipe: hearthwing-grown → breeds/hearthwing_grown_ultra.py (RECIPE.md)
const args = ['-b', '--factory-startup', '--python', join(ROOT, 'tools', 'blender', 'monsters', 'shape_preview.py'), '--', '--breed', `${breed.replace(/-/g, '_')}_ultra`, '--out', out, ...pass]
console.log(`${blender} ${args.join(' ')}`)
const r = spawnSync(blender, args, { stdio: ['ignore', 'inherit', 'inherit'], cwd: ROOT })
if (r.status !== 0) process.exit(r.status ?? 1)
console.log(`shape preview: ${join(out, 'sheet.png')}`)
