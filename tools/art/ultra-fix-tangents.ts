/**
 * Repair the zero-length tangents in already-shipped Ultra files (tools/art/ultra-tangents.ts; Nov 15).
 *
 *   node tools/art/ultra-fix-tangents.ts [--dry] [--skip scrollopus,…] [look …]
 *
 * Reads every public/models/monsters-ultra/<look>.glb, .webp.glb and .lite.glb (or only the looks named), and for each
 * file with a short tangent: rebuilds those tangents, writes the file back and checks it (it reads again; every other
 * accessor, every image and the animations are unchanged; no short tangent is left). Textures are not re-encoded: their
 * bytes pass through. Then the look's sidecar gets the new `build` (sha of <look>.glb: the cache-busting tag the game
 * appends, which ultraLooks.test checks), `lite.build` and the byte counts of the files that changed. --dry only
 * reports. Prints one line per file and a summary of what changed.
 */
import { createHash } from 'node:crypto'
import { existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO, type Document } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer'
import { describeRepairs, repairTangents, shortTangents, TANGENT_MIN } from './ultra-tangents.ts'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const DIR = join(ROOT, 'public', 'models', 'monsters-ultra')
const sha10 = (b: Uint8Array): string => createHash('sha1').update(b).digest('hex').slice(0, 10)
const hash = (b: ArrayBufferView | null): string =>
  b ? createHash('sha1').update(new Uint8Array(b.buffer, b.byteOffset, b.byteLength)).digest('hex') : '-'

/** Every accessor's data (the tangents apart), every image and the animations' names, hashed in document order. */
function fingerprint(doc: Document): { other: string[]; tangents: Map<number, Float64Array>; images: string[]; anims: string[] } {
  const root = doc.getRoot()
  const tangentAccs = new Set(root.listMeshes().flatMap((m) => m.listPrimitives()).map((p) => p.getAttribute('TANGENT')).filter((a) => a))
  const other: string[] = []
  const tangents = new Map<number, Float64Array>()
  root.listAccessors().forEach((a, i) => {
    if (tangentAccs.has(a)) {
      const n = a.getCount()
      const out = new Float64Array(n * 4)
      const el: number[] = []
      for (let k = 0; k < n; k++) {
        a.getElement(k, el)
        for (let c = 0; c < 4; c++) out[k * 4 + c] = el[c] ?? 0
      }
      tangents.set(i, out)
    } else {
      other.push(`${a.getType()}:${a.getComponentType()}:${a.getCount()}:${a.getNormalized()}:${hash(a.getArray())}`)
    }
  })
  return { other, tangents, images: root.listTextures().map((t) => hash(t.getImage())), anims: root.listAnimations().map((a) => a.getName()) }
}

function lookOf(file: string): string {
  return file.replace(/\.lite\.glb$|\.webp\.glb$|\.glb$/, '')
}

async function main(): Promise<void> {
  const args = process.argv.slice(2)
  const dry = args.includes('--dry')
  const si = args.indexOf('--skip')
  const skip = new Set(si >= 0 ? (args[si + 1] ?? '').split(',').filter(Boolean) : [])
  const only = new Set(args.filter((a, i) => !a.startsWith('--') && !(si >= 0 && i === si + 1)))
  await MeshoptDecoder.ready
  await MeshoptEncoder.ready
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder, 'meshopt.encoder': MeshoptEncoder })
  const files = readdirSync(DIR).filter((f) => f.endsWith('.glb')).filter((f) => !skip.has(lookOf(f)) && (!only.size || only.has(lookOf(f)))).sort()
  const changed: Record<string, { file: string; bytes: Uint8Array; repairs: string }[]> = {}
  for (const f of files) {
    const path = join(DIR, f)
    const doc = await io.read(path)
    const short = shortTangents(doc)
    if (!Object.keys(short).length) {
      console.log(`${f}: clean`)
      continue
    }
    if (dry) {
      console.log(`${f}: short tangents ${describeRepairs(short)}`)
      continue
    }
    const before = fingerprint(doc)
    const repairs = repairTangents(doc)
    const bytes = await io.writeBinary(doc)
    // check what was written: it loads, nothing else moved, only the repaired tangents differ, none is short now
    const again = await io.readBinary(bytes)
    const after = fingerprint(again)
    const left = shortTangents(again)
    if (Object.keys(left).length) throw new Error(`${f}: still has short tangents after the repair (${describeRepairs(left)})`)
    if (before.other.length !== after.other.length || before.other.some((h, i) => h !== after.other[i])) throw new Error(`${f}: an accessor other than the tangents changed`)
    if (before.images.join() !== after.images.join()) throw new Error(`${f}: an image changed`)
    if (before.anims.join() !== after.anims.join()) throw new Error(`${f}: the animations changed`)
    let moved = 0
    for (const [i, t0] of before.tangents) {
      const t1 = after.tangents.get(i)
      if (!t1 || t1.length !== t0.length) throw new Error(`${f}: a tangent accessor changed shape`)
      for (let k = 0; k < t0.length / 4; k++) {
        if ([0, 1, 2, 3].some((c) => Math.abs(t0[4 * k + c]! - t1[4 * k + c]!) > 1e-3)) moved++
      }
    }
    const total = Object.values(repairs).reduce((a, b) => a + b, 0)
    if (moved !== total) throw new Error(`${f}: ${moved} tangents differ, but ${total} were repaired`)
    writeFileSync(path, bytes)
    console.log(`${f}: repaired ${describeRepairs(repairs)} (shorter than ${TANGENT_MIN}); ${bytes.byteLength} bytes`)
    ;(changed[lookOf(f)] ??= []).push({ file: f, bytes, repairs: describeRepairs(repairs) })
  }
  // the sidecars: the cache-busting tags and the byte counts of the files that changed
  for (const [look, list] of Object.entries(changed)) {
    const jsonPath = join(DIR, `${look}.json`)
    if (!existsSync(jsonPath)) {
      console.warn(`${look}: no sidecar to update`)
      continue
    }
    const text = readFileSync(jsonPath, 'utf8')
    const side = JSON.parse(text) as { build?: string; budget?: { download?: Record<string, number> }; lite?: { file?: string; build?: string; bytes?: number } }
    for (const { file, bytes } of list) {
      if (file === `${look}.glb`) {
        side.build = sha10(bytes)
        const d = side.budget?.download
        if (d) for (const k of ['glb', 'glbKtx2', 'totalKtx2']) if (k in d) d[k] = bytes.byteLength
      } else if (file === `${look}.webp.glb`) {
        const d = side.budget?.download
        if (d) for (const k of ['glbWebp', 'totalWebp']) if (k in d) d[k] = bytes.byteLength
      } else if (side.lite && (file === side.lite.file || file === `${look}.lite.glb`)) {
        side.lite.build = sha10(bytes)
        side.lite.bytes = bytes.byteLength
      }
    }
    writeFileSync(jsonPath, JSON.stringify(side, null, 1) + '\n')
    console.log(`${look}.json: build ${side.build}${side.lite ? `, lite.build ${side.lite.build}` : ''}`)
  }
  const n = Object.values(changed).flat().length
  console.log(dry ? 'dry run: nothing written' : `${n} file${n === 1 ? '' : 's'} repaired: ${Object.values(changed).flat().map((c) => `${c.file} (${c.repairs})`).join('; ') || 'none'}`)
}

main().catch((e) => {
  console.error(e instanceof Error ? e.message : e)
  process.exit(1)
})
