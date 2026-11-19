/**
 * The 3D world (docs/WORLD_3D.md), W0: the pinned snapshot of what Wildsong takes from the owner's other game,
 * Gloamvault Open World — the town and land data, the town kit, the hero (the keeper's stand-in) and the townsfolk,
 * and the Blender scripts that build the kit.
 *
 *   npm run world:import -- [--from <gloamvault folder>] [--repin]     copy from Gloamvault (default ../Gloamvault Open World)
 *   npm run world:import -- --check                                     re-hash the snapshot against SOURCE.json
 *
 * The build and the tests never read the Gloamvault folder (GitHub's runners can't see it): everything they need is
 * here, in tools/world/gloamvault/ (data and models) and tools/blender/world/gvkit/ (the kit's Blender scripts, one
 * marked `# WS:` patch so their outputs land in tools/blender/out/world/gvkit/). SOURCE.json records the commit and
 * every file's sha256; tools/world/snapshot.test.ts holds the snapshot to it.
 */
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = join(HERE, '..', '..')
/** Where the data and models land. */
export const SNAPSHOT = join(HERE, 'gloamvault')
/** Where the kit's Blender scripts land. */
export const GVKIT = join(ROOT, 'tools', 'blender', 'world', 'gvkit')
/** The Gloamvault commit this snapshot is pinned to (0.14.1, Nov 7, 2026). */
export const PINNED_COMMIT = '588c001ff68f7aef6f3510dde796ee88736de5f1'

export interface SourceFile {
  /** Path relative to the repo root. */
  path: string
  /** Path inside the Gloamvault repo it came from. */
  from: string
  bytes: number
  sha256: string
  /** Set when the file is a filtered or patched copy, not byte-for-byte. */
  note?: string
}

export interface SourceRecord {
  about: string
  repo: string
  commit: string
  version: string
  imported: string
  files: SourceFile[]
}

/** Data and models: [snapshot path, Gloamvault path]. */
const DATA: [string, string][] = [
  ['land/vale.json', 'content/world/land/vale.json'],
  ['kit/kit_vale.glb', 'client/public/models/env/kit_vale.glb'],
  ['kit/vale.json', 'client/public/models/env/vale.json'],
  ['hero/hero_broad.glb', 'client/public/models/hero/hero_broad.glb'],
  ['hero/hero_slight.glb', 'client/public/models/hero/hero_slight.glb'],
  ['hero/hero_clips.glb', 'client/public/models/hero/hero_clips.glb'],
  ['hero/manifest.json', 'client/public/models/hero/manifest.json'],
  ['hero/clips.json', 'client/public/models/hero/clips.json'],
  ['people/humanoid.glb', 'client/public/models/monsters/humanoid.glb'],
]

/** The townsfolk entries of Gloamvault's monster manifest (the rest are its monsters and stay behind). */
const PEOPLE_MANIFEST: [string, string] = ['people/manifest.json', 'client/public/models/monsters/manifest.json']

/** The kit's Blender scripts: [gvkit path, Gloamvault path]. */
const SCRIPTS: [string, string][] = [
  ['env/build_kit_vale.py', 'tools/blender/env/build_kit_vale.py'],
  ['env/kit_lib.py', 'tools/blender/env/kit_lib.py'],
  ['env/vale_town_pieces.py', 'tools/blender/env/vale_town_pieces.py'],
  ['env/vale_land_pieces.py', 'tools/blender/env/vale_land_pieces.py'],
  ['env/vale_make_pieces.py', 'tools/blender/env/vale_make_pieces.py'],
  ['env/vale_agility_pieces.py', 'tools/blender/env/vale_agility_pieces.py'],
  ['lib/common.py', 'tools/blender/lib/common.py'],
  ['lib/toon.py', 'tools/blender/lib/toon.py'],
  ['lib/export.py', 'tools/blender/lib/export.py'],
  ['lib/render.py', 'tools/blender/lib/render.py'],
  ['palette.json', 'tools/blender/palette.json'],
  ['palettes/vale.json', 'tools/blender/palettes/vale.json'],
  ['palettes/shared.json', 'tools/blender/palettes/shared.json'],
  ['palettes/cellars.json', 'tools/blender/palettes/cellars.json'],
  ['palettes/crypts.json', 'tools/blender/palettes/crypts.json'],
  ['palettes/vault.json', 'tools/blender/palettes/vault.json'],
]

/** The one patch: gvkit's outputs go to tools/blender/out/world/gvkit/ (gitignored), never into the repo tree. */
const REPO_LINE = "REPO = os.path.dirname(os.path.dirname(TOOLS))     # the repo root"
const REPO_PATCH = "REPO = os.environ.get('GVKIT_ROOT') or os.path.join(os.path.dirname(os.path.dirname(TOOLS)), 'out', 'world', 'gvkit')  " +
  "# WS: Wildsong's copy writes into tools/blender/out/world/gvkit/ (gitignored); tools/world/import-gloamvault.ts"

export const sha256 = (buf: Buffer | string): string => createHash('sha256').update(buf).digest('hex')
const rel = (p: string) => relative(ROOT, p).replaceAll('\\', '/')

function write(path: string, data: Buffer | string): void {
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, data)
}

function record(path: string, from: string, note?: string): SourceFile {
  const buf = readFileSync(path)
  return { path: rel(path), from, bytes: buf.length, sha256: sha256(buf), ...(note ? { note } : {}) }
}

function importFrom(src: string, repin: boolean): void {
  if (!existsSync(join(src, 'content', 'world', 'land', 'vale.json'))) throw new Error(`no Gloamvault Open World at ${src} (pass --from <folder>)`)
  const head = execFileSync('git', ['-C', src, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  const dirty = execFileSync('git', ['-C', src, 'status', '--short'], { encoding: 'utf8' }).trim()
  if (head !== PINNED_COMMIT && !repin) throw new Error(`Gloamvault is at ${head}, the snapshot is pinned to ${PINNED_COMMIT}; pass --repin to move the pin (and update PINNED_COMMIT)`)
  if (dirty) console.warn(`warning: Gloamvault has uncommitted changes; the snapshot takes the files as they are on disk`)
  // The open world's version is the Unity app's (package.json holds the frozen web crawler's 0.8.0).
  const settings = readFileSync(join(src, 'unity', 'ProjectSettings', 'ProjectSettings.asset'), 'utf8')
  const version = /bundleVersion:\s*(\S+)/.exec(settings)?.[1] ?? 'unknown'

  const files: SourceFile[] = []
  for (const [to, from] of DATA) {
    const dest = join(SNAPSHOT, to)
    mkdirSync(dirname(dest), { recursive: true })
    copyFileSync(join(src, from), dest)
    files.push(record(dest, from))
  }

  const all = JSON.parse(readFileSync(join(src, PEOPLE_MANIFEST[1]), 'utf8')) as Record<string, unknown>
  const people = Object.fromEntries(Object.entries(all).filter(([id]) => id.startsWith('npc-')))
  const peoplePath = join(SNAPSHOT, PEOPLE_MANIFEST[0])
  write(peoplePath, JSON.stringify(people, null, 2) + '\n')
  files.push(record(peoplePath, PEOPLE_MANIFEST[1], `the ${Object.keys(people).length} npc-* entries only`))

  for (const [to, from] of SCRIPTS) {
    const dest = join(GVKIT, to)
    let text = readFileSync(join(src, from), 'utf8')
    let note: string | undefined
    if (to === 'lib/common.py') {
      if (!text.includes(REPO_LINE)) throw new Error(`gvkit: the REPO line in ${from} changed; update REPO_LINE`)
      text = text.replace(REPO_LINE, REPO_PATCH)
      note = 'patched (# WS:): REPO → tools/blender/out/world/gvkit/'
    }
    write(dest, text)
    files.push(record(dest, from, note))
  }

  const source: SourceRecord = {
    about: "Wildsong's pinned snapshot of Gloamvault Open World (the owner's own game): docs/WORLD_3D.md. Re-run npm run world:import to refresh.",
    repo: 'Gloamvault Open World',
    commit: head,
    version,
    imported: new Date().toISOString().slice(0, 10),
    files,
  }
  write(join(SNAPSHOT, 'SOURCE.json'), JSON.stringify(source, null, 2) + '\n')
  const bytes = files.reduce((n, f) => n + f.bytes, 0)
  console.log(`snapshot: ${files.length} files, ${(bytes / 1048576).toFixed(2)} MB, Gloamvault ${version} @ ${head.slice(0, 7)}`)
}

/** The files whose bytes differ from SOURCE.json (empty when the snapshot is intact). */
export function checkSnapshot(): string[] {
  const source = JSON.parse(readFileSync(join(SNAPSHOT, 'SOURCE.json'), 'utf8')) as SourceRecord
  const bad: string[] = []
  for (const f of source.files) {
    const p = join(ROOT, f.path)
    if (!existsSync(p)) { bad.push(`${f.path}: missing`); continue }
    if (sha256(readFileSync(p)) !== f.sha256) bad.push(`${f.path}: changed`)
  }
  return bad
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)
if (isMain) {
  const args = process.argv.slice(2)
  if (args.includes('--check')) {
    const bad = checkSnapshot()
    if (bad.length) { console.error(bad.join('\n')); process.exit(1) }
    console.log('snapshot intact')
  } else {
    const from = args.includes('--from') ? args[args.indexOf('--from') + 1]! : join(ROOT, '..', 'Gloamvault Open World')
    importFrom(resolve(from), args.includes('--repin'))
  }
}
