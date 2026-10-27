/**
 * SOUND_UPGRADE §14.6: `npm run check:build` (part of `verify`, after `build`).
 *   - The service-worker precache list contains the audio manifest and every core-pack file.
 *   - The audio engine chunk is at most 45 KB gzipped.
 *   - All song chunks together are at most 120 KB gzipped.
 * Runs on Node 24 directly, reading dist/.
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const DIST = 'dist'
const ENGINE_LIMIT = 45 * 1024
const SONGS_LIMIT = 120 * 1024

function fail(msg: string): never {
  console.error(`check:build FAILED: ${msg}`)
  process.exit(1)
}

if (!existsSync(DIST)) fail('dist/ is missing; run npm run build first')

// 1. The precache list: vite-plugin-pwa writes it into sw.js (generateSW).
const sw = join(DIST, 'sw.js')
if (!existsSync(sw)) fail('dist/sw.js is missing')
const swText = readFileSync(sw, 'utf8')
const precached = new Set<string>()
for (const m of swText.matchAll(/["']?url["']?\s*:\s*"([^"]+)"/g)) precached.add(m[1]!)
if (precached.size === 0) fail('no precache entries found in sw.js')
const manifest = JSON.parse(readFileSync(join('public', 'audio', 'manifest.json'), 'utf8')) as { instruments: Record<string, { pack: string; arts: Record<string, { file: string }[]> }> }
const missing: string[] = []
if (!precached.has('audio/manifest.json')) missing.push('audio/manifest.json')
let coreFiles = 0
for (const inst of Object.values(manifest.instruments)) {
  if (inst.pack !== 'core') continue
  for (const list of Object.values(inst.arts)) for (const s of list) {
    coreFiles++
    if (!precached.has(`audio/${s.file}`)) missing.push(`audio/${s.file}`)
  }
}
if (missing.length) fail(`${missing.length} core audio files are not precached, e.g. ${missing.slice(0, 3).join(', ')}`)

// 2. Chunk budgets.
const assets = join(DIST, 'assets')
const files = readdirSync(assets).filter((f) => f.endsWith('.js'))
const gz = (f: string) => gzipSync(readFileSync(join(assets, f))).length
const engine = files.filter((f) => /^audio-engine-/.test(f))
const songs = files.filter((f) => /^song-/.test(f))
if (engine.length === 0) fail('no audio-engine chunk in dist/assets (check vite.config.ts manualChunks)')
const engineBytes = engine.reduce((s, f) => s + gz(f), 0)
const songBytes = songs.reduce((s, f) => s + gz(f), 0)
console.log(`precache: ${precached.size} entries, ${coreFiles} core audio files + manifest present`)
console.log(`audio-engine: ${(engineBytes / 1024).toFixed(1)} KB gzipped (limit ${ENGINE_LIMIT / 1024}) in ${engine.join(', ')}`)
console.log(`songs: ${(songBytes / 1024).toFixed(1)} KB gzipped in ${songs.length} chunks (limit ${SONGS_LIMIT / 1024})`)
for (const f of files) {
  const size = statSync(join(assets, f)).size
  if (size > 1.5 * 1024 * 1024) console.log(`note: ${f} is ${(size / 1024 / 1024).toFixed(1)} MB raw`)
}
if (engineBytes > ENGINE_LIMIT) fail(`the audio engine chunk is ${(engineBytes / 1024).toFixed(1)} KB gzipped, over ${ENGINE_LIMIT / 1024} KB`)
if (songBytes > SONGS_LIMIT) fail(`the song chunks are ${(songBytes / 1024).toFixed(1)} KB gzipped, over ${SONGS_LIMIT / 1024} KB`)
console.log('check:build OK')
