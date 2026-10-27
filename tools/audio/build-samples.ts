/**
 * SOUND_UPGRADE §5.3: `npm run audio:samples [-- --list | --skip-fetch | --force | --assemble]`
 *
 *  1. Fetches only the files the rules in `sources.ts` choose: blobless, sparse clones of VCSL and VSCO 2 CE
 *     at their pinned commits into tools/audio/.cache/, and the two Kenney zips (SHA-256 recorded).
 *  2. Measures every sample's real pitch (YIN), learns each library's octave convention from its harmonic
 *     instruments, and fails if a name disagrees with the measurement by more than 50 cents.
 *  3. Cleans: mono, leading silence trimmed to −50 dB keeping the attack, notes of one articulation
 *     level-matched (RMS of the first 300 ms), the instrument's peak set to −3 dBFS, length caps by class,
 *     every decay ending at −50 dB with a 30 ms fade.
 *  4. Bakes an equal-power crossfade loop (≥ 50 ms) into every sustain.
 *  5. Encodes Opus 48 kHz mono (64 kbps, 80 for drums, bells and glass) with ffmpeg; Vorbis q4 if libopus is missing.
 *  6. Decodes each encoded file again and stores its onset and loop points in seconds as measured there.
 *  7. Writes public/audio/<pack>/<instrument>/*.ogg and public/audio/manifest.json, packs computed from the
 *     usage graph (src/audio/recipes/packs.ts).
 *  8. Reports sizes and decoded seconds per pack and fails over budget (§2).
 *
 *  --list      only print which files the rules choose (after fetching the listings), then stop
 *  --skip-fetch  trust the cache
 *  --force     reprocess every sample even if its cached result exists
 *  --assemble  skip processing; rebuild the packs and the manifest from the cache
 */
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { basename, dirname, join } from 'node:path'
import { decodeWav, encodeWav } from '../../src/audio/analysis/wav.ts'
import { packOf, type PackId } from '../../src/audio/recipes/packs.ts'
import { registerUsage } from '../../src/audio/recipes/usage.ts'
import { decodeFile, encodeOgg, hasLibopus } from './opus.ts'
import { detectPitch, midiToHz } from './pitch.ts'
import { LIBRARIES, noteNameToMidi, parseSampleName, SOURCE_RULES, type Lib, type ParsedName, type SampleClass, type SourceRule } from './sources.ts'
import { readZip } from './zip.ts'

const args = new Set(process.argv.slice(2))
const LIST = args.has('--list')
const SKIP_FETCH = args.has('--skip-fetch')
const FORCE = args.has('--force')
const ASSEMBLE_ONLY = args.has('--assemble')

const CACHE = 'tools/audio/.cache'
const OUT = 'public/audio'
const OUT_RATE = 48000
const SILENCE_DB = -50
const PEAK_TARGET = Math.pow(10, -3 / 20)
const MAX_PER_ART = 14
const LOOP_XF_SEC = 0.08

const BUDGET = {
  totalBytes: 10 * 1024 * 1024,
  coreBytes: 4.5 * 1024 * 1024,
  seconds: { core: 450, events: 250, places: 300 } as Record<PackId, number>,
}

const CAP_SEC: Record<SampleClass, number> = { sustain: 1.6, pluck: 2.5, drum: 1.0, ringing: 3.5, foley: 1.2 }

/** A sample whose measured pitch disagrees with its name (§5.3 step 2). Collected, reported, and fatal unless --drop-mismatches. */
class MismatchError extends Error {}
const DROP_MISMATCHES = args.has('--drop-mismatches')
const mismatches: string[] = []
const LONG_PLUCK = new Set(['harp', 'vibes', 'tubular-bells', 'hand-chimes'])
const KBPS_80 = new Set<SampleClass>(['drum', 'ringing'])
const KBPS_80_INST = new Set(['tubular-bells', 'hand-chimes', 'glock', 'wine-glasses'])

interface Chosen {
  rule: SourceRule
  /** Path inside the library (git) or the zip entry name (Kenney). */
  path: string
  parsed: ParsedName
  nameMidi: number | null
  take: number
}

interface Processed {
  rule: SourceRule
  source: string
  take: number
  nameMidi: number | null
  root: number
  cents: number
  measuredMidi: number | null
  confidence: number | null
  /** Seconds, in the processed (source-rate) file. */
  onset: number
  loopStart: number | null
  loopEnd: number | null
  rms300: number
  peak: number
  seconds: number
  /** The unity-peak pre-gain applied to the source before anything else, dB. */
  preGainDb: number
  /** The total gain applied to the source (pre-gain, level match and peak normalisation), dB. */
  gainDb: number
  encoded: string
  wav: string
}

interface ManifestSample {
  file: string
  inst: string
  art: string
  dyn: string
  root: number
  cents: number
  take: number
  onset: number
  loopStart: number | null
  loopEnd: number | null
  trimDb: number
  seconds: number
  bytes: number
}

const log = (s: string) => console.log(s)

/* ---------- fetching ---------- */

function sh(cmd: string, argv: string[], cwd?: string): string {
  return execFileSync(cmd, argv, { cwd, encoding: 'utf8', maxBuffer: 1 << 28, stdio: ['pipe', 'pipe', 'inherit'] })
}

function ensureClone(lib: Lib): string {
  const meta = LIBRARIES[lib]
  const dir = join(CACHE, lib)
  if (!existsSync(join(dir, '.git'))) {
    mkdirSync(CACHE, { recursive: true })
    log(`cloning ${meta.name} (blobless, no checkout)…`)
    sh('git', ['clone', '--filter=blob:none', '--no-checkout', meta.url, dir])
  }
  const have = sh('git', ['cat-file', '-t', meta.pin], dir).trim() === 'commit'
  if (!have) sh('git', ['fetch', '--filter=blob:none', 'origin', meta.pin], dir)
  return dir
}

function gitListing(lib: Lib): string[] {
  const dir = ensureClone(lib)
  return sh('git', ['ls-tree', '-r', '--name-only', LIBRARIES[lib].pin], dir)
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
}

function sparseCheckout(lib: Lib, paths: string[]): void {
  const dir = ensureClone(lib)
  const missing = paths.filter((p) => !existsSync(join(dir, p)))
  if (missing.length === 0) return
  log(`fetching ${missing.length} files from ${LIBRARIES[lib].name}…`)
  execFileSync('git', ['sparse-checkout', 'set', '--no-cone', '--stdin'], { cwd: dir, input: paths.map((p) => `/${p}`).join('\n') + '\n', stdio: ['pipe', 'inherit', 'inherit'] })
  sh('git', ['checkout', '--detach', LIBRARIES[lib].pin], dir)
  for (const p of paths) if (!existsSync(join(dir, p))) throw new Error(`sparse checkout did not produce ${p}`)
}

async function ensureZip(lib: Lib): Promise<{ path: string; sha256: string }> {
  const meta = LIBRARIES[lib]
  const path = join(CACHE, 'kenney', `${lib}.zip`)
  if (!existsSync(path)) {
    mkdirSync(dirname(path), { recursive: true })
    log(`downloading ${meta.name}…`)
    const res = await fetch(meta.url)
    if (!res.ok) throw new Error(`download failed (${res.status}) for ${meta.url}; see SOUND_UPGRADE §5.1 for the fallback link`)
    writeFileSync(path, Buffer.from(await res.arrayBuffer()))
  }
  const sha256 = createHash('sha256').update(readFileSync(path)).digest('hex')
  return { path, sha256 }
}

/* ---------- choosing ---------- */

function pickBy(cands: Chosen[], field: 'dyn' | 'vel', order: readonly string[] | undefined): Chosen[] {
  if (!order) return cands
  for (const v of order) {
    const hit = cands.filter((c) => c.parsed[field] === v)
    if (hit.length) return hit
  }
  return cands
}

function byRr(a: Chosen, b: Chosen): number {
  return Number(a.parsed.rr ?? '1') - Number(b.parsed.rr ?? '1') || a.path.localeCompare(b.path)
}

function chooseFor(rule: SourceRule, listing: string[]): Chosen[] {
  const base = (p: string) => basename(p)
  const cands: Chosen[] = listing
    .filter((p) => (rule.dir ? p.startsWith(rule.dir) : true))
    .filter((p) => /\.(wav|ogg)$/i.test(p))
    .filter((p) => (rule.filter ? rule.filter.test(base(p)) : true))
    .filter((p) => !/legacy/i.test(p.slice(rule.dir.length)) || /legacy/i.test(rule.dir))
    .map((p) => {
      const parsed = parseSampleName(base(p))
      return { rule, path: p, parsed, nameMidi: parsed.note ? noteNameToMidi(parsed.note) : null, take: 0 }
    })
  if (cands.length === 0) return []
  if (rule.pitch === 'none' || rule.pitch === 'measure') {
    let pool = pickBy(pickBy(cands, 'dyn', rule.prefer?.dyn), 'vel', rule.prefer?.vel).sort(byRr)
    const takes = rule.takes ?? (rule.cls === 'foley' ? 4 : 2)
    if (pool.length < takes) pool = [...pool, ...cands.filter((c) => !pool.includes(c)).sort(byRr)]
    return pool.slice(0, takes).map((c, i) => ({ ...c, take: i }))
  }
  // Pitched: one main take per note (plus an alternate where the rule names one), then thin to the spacing.
  const byNote = new Map<number, Chosen[]>()
  for (const c of cands) {
    if (c.nameMidi === null) continue
    if (rule.range && (c.nameMidi < rule.range[0] || c.nameMidi > rule.range[1])) continue
    byNote.set(c.nameMidi, [...(byNote.get(c.nameMidi) ?? []), c])
  }
  const notes = [...byNote.keys()].sort((a, b) => a - b)
  if (notes.length === 0) return []
  const max = rule.max ?? MAX_PER_ART
  let spacing = 3
  let picked = thin(notes, spacing)
  while (picked.length > max && spacing < 12) {
    spacing++
    picked = thin(notes, spacing)
  }
  const out: Chosen[] = []
  for (const n of picked) {
    const group = byNote.get(n)!
    const mains = pickBy(pickBy(group, 'dyn', rule.prefer?.dyn), 'vel', rule.prefer?.vel).sort(byRr)
    const main = mains[0]!
    out.push({ ...main, take: 0 })
    if (rule.alt) {
      let alts = group.filter((c) => c !== main)
      if (rule.alt.dyn) alts = alts.filter((c) => rule.alt!.dyn!.includes(c.parsed.dyn ?? ''))
      if (rule.alt.vel) alts = alts.filter((c) => rule.alt!.vel!.includes(c.parsed.vel ?? ''))
      if (rule.alt.rr) alts = alts.filter((c) => rule.alt!.rr!.includes(c.parsed.rr ?? '') && c.parsed.dyn === main.parsed.dyn && c.parsed.vel === main.parsed.vel)
      const alt = alts.sort(byRr)[0]
      if (alt) out.push({ ...alt, take: 1 })
    }
  }
  return out
}

/** Every `spacing` semitones across the available notes, plus the nearest available note beyond each end. */
function thin(notes: number[], spacing: number): number[] {
  const out: number[] = []
  let last = -Infinity
  for (const n of notes) {
    if (n >= last + spacing) {
      out.push(n)
      last = n
    }
  }
  const lastNote = notes[notes.length - 1]!
  if (out[out.length - 1] !== lastNote) out.push(lastNote)
  return out
}

/* ---------- processing ---------- */


function rmsOf(x: Float32Array, from: number, to: number): number {
  let s = 0
  let n = 0
  for (let i = Math.max(0, from); i < Math.min(x.length, to); i++) {
    s += x[i]! * x[i]!
    n++
  }
  return n ? Math.sqrt(s / n) : 0
}

function peakOf(x: Float32Array): number {
  let p = 0
  for (let i = 0; i < x.length; i++) p = Math.max(p, Math.abs(x[i]!))
  return p
}

function loadSource(lib: Lib, path: string): { x: Float32Array; sr: number } {
  const full = LIBRARIES[lib].kind === 'git' ? join(CACHE, lib, path) : join(CACHE, 'kenney', lib, basename(path))
  if (/\.wav$/i.test(full)) {
    const w = decodeWav(new Uint8Array(readFileSync(full)))
    const n = w.channels[0]!.length
    const x = new Float32Array(n)
    for (const ch of w.channels) for (let i = 0; i < n; i++) x[i] = x[i]! + ch[i]! / w.channels.length
    return { x, sr: w.sampleRate }
  }
  const [x] = decodeFile(full, 44100, 1)
  return { x: x!, sr: 44100 }
}

/** Trims leading silence to the −50 dB point minus 5 ms, with a 2 ms fade-in. Returns the new signal and the onset index. */
function trimStart(x: Float32Array, sr: number): { x: Float32Array; onset: number } {
  const thr = Math.pow(10, SILENCE_DB / 20)
  let first = 0
  while (first < x.length && Math.abs(x[first]!) < thr) first++
  if (first >= x.length) throw new Error('silent sample')
  const start = Math.max(0, first - Math.round(0.005 * sr))
  const out = x.slice(start)
  const fade = Math.round(0.002 * sr)
  for (let i = 0; i < fade && i < out.length; i++) out[i] = out[i]! * (i / fade)
  return { x: out, onset: first - start }
}

/** Cuts the tail where the 10 ms RMS last exceeds −50 dB, caps the length, and fades the end. */
function trimEnd(x: Float32Array, sr: number, capSec: number): Float32Array {
  const thr = Math.pow(10, SILENCE_DB / 20)
  const block = Math.round(0.01 * sr)
  let end = x.length
  for (let b = Math.floor(x.length / block) - 1; b >= 0; b--) {
    if (rmsOf(x, b * block, (b + 1) * block) > thr) {
      end = Math.min(x.length, (b + 1) * block)
      break
    }
  }
  const cap = Math.round(capSec * sr)
  const capped = end > cap
  end = Math.min(end, cap)
  const out = x.slice(0, end)
  // A capped decay gets a long smooth fade so the cut is not heard; every file ends with the 30 ms fade.
  if (capped) {
    const long = Math.min(Math.round(0.4 * sr), Math.floor(out.length / 4))
    for (let i = 0; i < long; i++) {
      const t = i / long
      out[out.length - long + i] = out[out.length - long + i]! * (1 - t * t)
    }
  }
  const fade = Math.min(Math.round(0.03 * sr), out.length)
  for (let i = 0; i < fade; i++) out[out.length - fade + i] = out[out.length - fade + i]! * (1 - (i + 1) / fade)
  return out
}

/** Bakes an equal-power loop into a sustain: the file ends at loopEnd. */
function bakeLoop(x: Float32Array, sr: number, onset: number): { x: Float32Array; loopStart: number; loopEnd: number } {
  const xf = Math.round(LOOP_XF_SEC * sr)
  const avail = x.length - onset
  let loopStart = onset + Math.round(0.35 * sr)
  let targetLen = Math.round(0.7 * sr)
  if (avail < loopStart - onset + targetLen + xf) {
    loopStart = onset + Math.round(0.25 * sr)
    targetLen = Math.max(Math.round(0.3 * sr), x.length - loopStart - xf - Math.round(0.05 * sr))
  }
  if (loopStart + targetLen + xf > x.length) throw new Error(`sustain too short to loop (${(x.length / sr).toFixed(2)} s)`)
  // Pick the loop end in a ±40 ms window by the best correlation of the two crossfade regions.
  const search = Math.round(0.04 * sr)
  let best = loopStart + targetLen
  let bestScore = -Infinity
  for (let end = loopStart + targetLen - search; end <= Math.min(x.length, loopStart + targetLen + search); end++) {
    let dot = 0
    let ea = 0
    let eb = 0
    for (let i = 0; i < xf; i += 2) {
      const a = x[loopStart - xf + i]!
      const b = x[end - xf + i]!
      dot += a * b
      ea += a * a
      eb += b * b
    }
    const score = ea > 0 && eb > 0 ? dot / Math.sqrt(ea * eb) : -1
    if (score > bestScore) {
      bestScore = score
      best = end
    }
  }
  const loopEnd = best
  const out = x.slice(0, loopEnd)
  for (let i = 0; i < xf; i++) {
    const w = (i / xf) * (Math.PI / 2)
    out[loopEnd - xf + i] = Math.cos(w) * x[loopEnd - xf + i]! + Math.sin(w) * x[loopStart - xf + i]!
  }
  return { x: out, loopStart, loopEnd }
}

function processOne(c: Chosen, octaveShift: number | null): Omit<Processed, 'encoded' | 'wav' | 'gainDb'> & { x: Float32Array; sr: number } {
  const { rule } = c
  const src = loadSource(rule.lib, c.path)
  const sr = src.sr
  // Some library takes are recorded very quietly (a soft low marimba peaks near −50 dBFS): bring every source
  // to unity peak first so the −50 dB trims are relative to the sound, then level-match below.
  const srcPeak = peakOf(src.x)
  if (srcPeak <= 0) throw new Error('silent sample')
  const preGain = 1 / srcPeak
  for (let i = 0; i < src.x.length; i++) src.x[i] = src.x[i]! * preGain
  const t = trimStart(src.x, sr)
  let x = t.x
  const onset = t.onset
  let measuredMidi: number | null = null
  let cents = 0
  let confidence: number | null = null
  let root = 60
  if (rule.pitch !== 'none') {
    const steady = rule.cls === 'sustain' || rule.cls === 'ringing'
    // A named sample offers both octave conventions as candidates; the measurement still decides.
    const candidatesHz = rule.pitch === 'named' && c.nameMidi !== null ? [midiToHz(c.nameMidi + 12), midiToHz(c.nameMidi)] : undefined
    // Short notes are measured after their attack transient (which runs sharp), over more frames.
    const p = detectPitch(x, sr, { fromSec: onset / sr + (steady ? 0.3 : 0.06), minHz: rule.minHz ?? 60, frames: steady ? 5 : 6, candidatesHz })
    if (p) {
      measuredMidi = p.midi
      cents = p.cents
      confidence = p.confidence
    }
    if (rule.pitch === 'measure') {
      if (!p) throw new MismatchError(`no pitch found in ${c.path}`)
      root = p.midi
    } else if (rule.pitch === 'named') {
      if (!p) throw new MismatchError(`no pitch found in ${c.path}`)
      const named = c.nameMidi!
      // Distance from the name's pitch class, in cents, on the continuous measurement.
      const exact = p.midi + p.cents / 100
      let diff = (((exact - named) % 12) + 12) % 12
      if (diff > 6) diff -= 12
      if (Math.abs(diff) * 100 > 50) throw new MismatchError(`${c.path}: named ${named} (${c.parsed.note}) but sounds at MIDI ${p.midi} ${p.cents >= 0 ? '+' : ''}${p.cents} cents (${p.hz.toFixed(1)} Hz, confidence ${p.confidence.toFixed(2)})`)
      root = p.midi
    } else {
      // Inharmonic: the name's pitch class with the library's octave convention.
      root = c.nameMidi! + (octaveShift ?? 0)
      cents = 0
    }
  }
  let loopStart: number | null = null
  let loopEnd: number | null = null
  if (rule.cls === 'sustain') {
    const l = bakeLoop(x, sr, onset)
    x = l.x
    loopStart = l.loopStart
    loopEnd = l.loopEnd
  } else {
    const cap = rule.capSec ?? (rule.cls === 'pluck' && LONG_PLUCK.has(rule.inst) ? 3 : CAP_SEC[rule.cls])
    x = trimEnd(x, sr, cap)
  }
  return {
    rule,
    source: c.path,
    take: c.take,
    nameMidi: c.nameMidi,
    root,
    cents,
    measuredMidi,
    confidence,
    onset: onset / sr,
    loopStart: loopStart === null ? null : loopStart / sr,
    loopEnd: loopEnd === null ? null : loopEnd / sr,
    rms300: rmsOf(x, onset, onset + Math.round(0.3 * sr)),
    peak: peakOf(x),
    seconds: x.length / sr,
    preGainDb: 20 * Math.log10(preGain),
    x,
    sr,
  }
}

/* ---------- main ---------- */

async function main(): Promise<void> {
  mkdirSync(CACHE, { recursive: true })
  const opus = hasLibopus()
  if (!opus) log('WARNING: ffmpeg has no libopus; encoding Ogg Vorbis q4 instead (say so in PROGRESS.md)')

  // 1. listings and choices
  const listings = new Map<Lib, string[]>()
  const zipShas: Partial<Record<Lib, string>> = {}
  for (const lib of ['vcsl', 'vsco'] as const) if (!ASSEMBLE_ONLY) listings.set(lib, gitListing(lib))
  for (const lib of ['kenney-impact', 'kenney-rpg'] as const) {
    if (ASSEMBLE_ONLY) continue
    const z = await ensureZip(lib)
    zipShas[lib] = z.sha256
    const entries = readZip(readFileSync(z.path))
    listings.set(lib, entries.map((e) => e.name))
  }
  const chosen: Chosen[] = []
  if (!ASSEMBLE_ONLY) {
    for (const rule of SOURCE_RULES) {
      const picks = chooseFor(rule, listings.get(rule.lib) ?? [])
      if (picks.length === 0) {
        const near = (listings.get(rule.lib) ?? []).filter((p) => p.startsWith(rule.dir)).slice(0, 12)
        log(`!! ${rule.inst}/${rule.art}: nothing matched in ${rule.lib}:${rule.dir}\n   ${near.join('\n   ') || '(folder empty or missing)'}`)
      }
      chosen.push(...picks)
    }
    if (LIST) {
      for (const rule of SOURCE_RULES) {
        const mine = chosen.filter((c) => c.rule === rule)
        log(`${rule.inst}/${rule.art} (${mine.length}): ${mine.map((c) => basename(c.path) + (c.take ? '*' : '')).join(', ')}`)
      }
      log(`${chosen.length} files in all`)
      return
    }
    // 2. fetch the chosen files
    for (const lib of ['vcsl', 'vsco'] as const) {
      const paths = chosen.filter((c) => c.rule.lib === lib).map((c) => c.path)
      if (!SKIP_FETCH && paths.length) sparseCheckout(lib, [...new Set(paths)])
    }
    for (const lib of ['kenney-impact', 'kenney-rpg'] as const) {
      const wanted = new Set(chosen.filter((c) => c.rule.lib === lib).map((c) => c.path))
      if (wanted.size === 0) continue
      const dir = join(CACHE, 'kenney', lib)
      mkdirSync(dir, { recursive: true })
      const entries = readZip(readFileSync(join(CACHE, 'kenney', `${lib}.zip`)))
      for (const e of entries) {
        if (!wanted.has(e.name)) continue
        const target = join(dir, basename(e.name))
        if (!existsSync(target)) writeFileSync(target, e.read())
      }
    }
  }

  // 3. process (cached per source file)
  const processedDir = join(CACHE, 'processed')
  const encodedDir = join(CACHE, 'encoded')
  mkdirSync(processedDir, { recursive: true })
  mkdirSync(encodedDir, { recursive: true })
  const results: Processed[] = []
  if (!ASSEMBLE_ONLY) {
    // Pass 1: harmonic instruments teach each library's octave convention.
    const shiftVotes = new Map<Lib, number[]>()
    const pending: { c: Chosen; p: ReturnType<typeof processOne> }[] = []
    const cacheKey = (c: Chosen) => `${c.rule.inst}__${c.rule.art}__${c.take}__${basename(c.path).replace(/[^\w.#-]+/g, '_')}`
    const tryProcess = (c: Chosen, shift: number | null): ReturnType<typeof processOne> | null => {
      try {
        return processOne(c, shift)
      } catch (e) {
        if (e instanceof MismatchError) {
          mismatches.push(e.message)
          return null
        }
        throw new Error(`${c.rule.lib}:${c.path}: ${(e as Error).message}`)
      }
    }
    for (const c of chosen) {
      if (c.rule.pitch !== 'named') continue
      const p = tryProcess(c, null)
      if (!p) continue
      pending.push({ c, p })
      if (p.measuredMidi !== null && c.nameMidi !== null) shiftVotes.set(c.rule.lib, [...(shiftVotes.get(c.rule.lib) ?? []), p.measuredMidi - c.nameMidi])
    }
    const octaveShift = new Map<Lib, number>()
    for (const [lib, votes] of shiftVotes) {
      const counts = new Map<number, number>()
      for (const v of votes) counts.set(v, (counts.get(v) ?? 0) + 1)
      const [shift, n] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]!
      octaveShift.set(lib, shift)
      log(`${lib}: names sound ${shift >= 0 ? '+' : ''}${shift} semitones from their note names (${n}/${votes.length} agree)`)
      if (n / votes.length < 0.9) log(`   WARNING: ${votes.length - n} harmonic samples disagree with the convention; check the --list output`)
    }
    // A named sample whose pitch class agrees but whose measured octave does not follow the library's convention
    // was measured at a harmonic or a sub-octave: its root follows the convention, with the measured cents.
    for (const e of pending) {
      if (e.c.rule.pitch !== 'named' || e.c.nameMidi === null) continue
      const expected = e.c.nameMidi + (octaveShift.get(e.c.rule.lib) ?? 0)
      if (e.p.root !== expected) {
        log(`   octave: ${basename(e.c.path)} measured MIDI ${e.p.root}, convention says ${expected}; using ${expected}`)
        e.p.root = expected
      }
    }
    for (const c of chosen) {
      if (c.rule.pitch === 'named') continue
      const p = tryProcess(c, octaveShift.get(c.rule.lib) ?? 0)
      if (p) pending.push({ c, p })
    }
    if (mismatches.length) {
      log(`${mismatches.length} sample(s) disagree with their names:`)
      for (const m of mismatches) log(`  ${m}`)
      if (!DROP_MISMATCHES) {
        log('Fix the rule, or re-run with --drop-mismatches to leave them out (then say so in PROGRESS.md).')
        process.exit(1)
      }
    }
    // Pass 2: level-match per articulation, then peak per instrument.
    const gain = new Map<(typeof pending)[number], number>()
    const arts = new Map<string, (typeof pending)[number][]>()
    for (const e of pending) {
      const k = `${e.c.rule.inst}/${e.c.rule.art}`
      arts.set(k, [...(arts.get(k) ?? []), e])
    }
    for (const group of arts.values()) {
      const rms = group.map((e) => e.p.rms300).filter((r) => r > 0).sort((a, b) => a - b)
      const target = rms[Math.floor(rms.length / 2)] ?? 1
      for (const e of group) {
        const g = e.p.rms300 > 0 ? target / e.p.rms300 : 1
        gain.set(e, Math.max(0.25, Math.min(4, g)))
      }
    }
    const insts = new Map<string, (typeof pending)[number][]>()
    for (const e of pending) insts.set(e.c.rule.inst, [...(insts.get(e.c.rule.inst) ?? []), e])
    for (const group of insts.values()) {
      let peak = 0
      for (const e of group) peak = Math.max(peak, e.p.peak * gain.get(e)!)
      const norm = peak > 0 ? PEAK_TARGET / peak : 1
      for (const e of group) gain.set(e, gain.get(e)! * norm)
    }
    // Pass 3: write, encode, re-decode and measure.
    let n = 0
    for (const e of pending) {
      const key = cacheKey(e.c)
      const wav = join(processedDir, `${key}.wav`)
      const ogg = join(encodedDir, `${key}.ogg`)
      const meta = join(encodedDir, `${key}.json`)
      const g = gain.get(e)!
      const gainDb = 20 * Math.log10(g) + e.p.preGainDb
      if (!FORCE && existsSync(ogg) && existsSync(meta)) {
        const cached = JSON.parse(readFileSync(meta, 'utf8')) as Processed
        // Reuse only when the gain, the source and the processed length (caps, loop) all match.
        if (Math.abs(cached.gainDb - gainDb) < 0.05 && cached.source === e.c.path && Math.abs(cached.seconds - e.p.x.length / e.p.sr) < 0.05) {
          results.push(cached)
          continue
        }
      }
      const y = new Float32Array(e.p.x.length)
      for (let i = 0; i < y.length; i++) y[i] = Math.max(-1, Math.min(1, e.p.x[i]! * g))
      writeFileSync(wav, encodeWav([y], e.p.sr, 32))
      const kbps = KBPS_80.has(e.c.rule.cls) || KBPS_80_INST.has(e.c.rule.inst) ? 80 : 64
      encodeOgg(wav, ogg, kbps, opus)
      const [dec] = decodeFile(ogg, OUT_RATE, 1)
      const thr = Math.pow(10, SILENCE_DB / 20)
      let first = 0
      while (first < dec!.length && Math.abs(dec![first]!) < thr) first++
      const decodedOnset = first / OUT_RATE
      const shift = decodedOnset - e.p.onset
      const r: Processed = {
        rule: e.c.rule,
        source: e.c.path,
        take: e.c.take,
        nameMidi: e.c.nameMidi,
        root: e.p.root,
        cents: e.p.cents,
        measuredMidi: e.p.measuredMidi,
        confidence: e.p.confidence,
        onset: decodedOnset,
        loopStart: e.p.loopStart === null ? null : e.p.loopStart + shift,
        loopEnd: e.p.loopEnd === null ? null : e.p.loopEnd + shift,
        rms300: e.p.rms300,
        peak: e.p.peak * g,
        seconds: dec!.length / OUT_RATE,
        preGainDb: e.p.preGainDb,
        gainDb,
        encoded: ogg,
        wav,
      }
      writeFileSync(meta, JSON.stringify(r, (k, v) => (k === 'rule' ? { inst: e.c.rule.inst, art: e.c.rule.art, lib: e.c.rule.lib, cls: e.c.rule.cls, pitch: e.c.rule.pitch } : v), 2))
      results.push(r)
      n++
      if (n % 25 === 0) log(`  processed ${n} / ${pending.length}`)
    }
    log(`processed ${pending.length} samples (${n} new)`)
  } else {
    for (const f of execFileSync(process.platform === 'win32' ? 'cmd' : 'ls', process.platform === 'win32' ? ['/c', 'dir', '/b', encodedDir] : [encodedDir], { encoding: 'utf8' })
      .split(/\r?\n/)
      .filter((f) => f.endsWith('.json'))) {
      results.push(JSON.parse(readFileSync(join(encodedDir, f), 'utf8')) as Processed)
    }
  }

  // 4. assemble packs and the manifest
  registerUsage()
  rmSync(OUT, { recursive: true, force: true })
  const manifest = {
    version: 1,
    sampleRate: OUT_RATE,
    codec: opus ? 'opus' : 'vorbis',
    packs: {} as Record<string, { files: number; bytes: number; seconds: number }>,
    instruments: {} as Record<string, { pack: PackId; arts: Record<string, ManifestSample[]> }>,
    sources: Object.fromEntries(
      (Object.keys(LIBRARIES) as Lib[]).map((lib) => [lib, { name: LIBRARIES[lib].name, url: LIBRARIES[lib].url, license: LIBRARIES[lib].license, pin: LIBRARIES[lib].pin || null, sha256: zipShas[lib] ?? null }]),
    ),
  }
  for (const r of results) {
    const inst = r.rule.inst
    const pack = packOf(inst)
    const entry = (manifest.instruments[inst] ??= { pack, arts: {} })
    const list = (entry.arts[r.rule.art] ??= [])
    const fileName = r.rule.pitch === 'none' ? `${r.rule.art}_${r.take}.ogg` : `${r.rule.art}_${r.root}${r.take ? `_${r.take}` : ''}.ogg`
    const rel = `${pack}/${inst}/${fileName}`
    const target = join(OUT, rel)
    mkdirSync(dirname(target), { recursive: true })
    writeFileSync(target, readFileSync(r.encoded))
    const bytes = statSync(target).size
    list.push({
      file: rel,
      inst,
      art: r.rule.art,
      dyn: r.rule.prefer?.dyn?.[0] ?? r.rule.prefer?.vel?.[0] ?? 'main',
      root: r.root,
      cents: r.cents,
      take: r.take,
      onset: Math.round(r.onset * 1e5) / 1e5,
      loopStart: r.loopStart === null ? null : Math.round(r.loopStart * 1e5) / 1e5,
      loopEnd: r.loopEnd === null ? null : Math.min(Math.round(r.loopEnd * 1e5) / 1e5, Math.round(r.seconds * 1000) / 1000),
      trimDb: Math.round(r.gainDb * 100) / 100,
      seconds: Math.round(r.seconds * 1000) / 1000,
      bytes,
    })
    const p = (manifest.packs[pack] ??= { files: 0, bytes: 0, seconds: 0 })
    p.files++
    p.bytes += bytes
    p.seconds += r.seconds
  }
  for (const inst of Object.values(manifest.instruments)) for (const list of Object.values(inst.arts)) list.sort((a, b) => a.root - b.root || a.take - b.take)
  for (const p of Object.values(manifest.packs)) p.seconds = Math.round(p.seconds * 10) / 10
  writeFileSync(join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 1) + '\n')

  // 5. report and budgets
  let total = 0
  let over = false
  for (const [pack, p] of Object.entries(manifest.packs)) {
    total += p.bytes
    const limitSec = BUDGET.seconds[pack as PackId]
    const flag = p.seconds > limitSec || (pack === 'core' && p.bytes > BUDGET.coreBytes) ? '  OVER BUDGET' : ''
    if (flag) over = true
    log(`${pack.padEnd(7)} ${String(p.files).padStart(4)} files  ${(p.bytes / 1024 / 1024).toFixed(2)} MB  ${p.seconds.toFixed(1)} s decoded (limit ${limitSec} s)${flag}`)
  }
  log(`total ${(total / 1024 / 1024).toFixed(2)} MB of ${(BUDGET.totalBytes / 1024 / 1024).toFixed(1)} MB`)
  const perInst = Object.entries(manifest.instruments)
    .map(([id, e]) => ({ id, pack: e.pack, n: Object.values(e.arts).reduce((s, l) => s + l.length, 0), sec: Object.values(e.arts).reduce((s, l) => s + l.reduce((t, x) => t + x.seconds, 0), 0) }))
    .sort((a, b) => b.sec - a.sec)
  for (const i of perInst) log(`  ${i.id.padEnd(16)} ${i.pack.padEnd(7)} ${String(i.n).padStart(3)} samples ${i.sec.toFixed(1).padStart(6)} s`)
  if (total > BUDGET.totalBytes) over = true
  if (over) {
    log('Over budget. SOUND_UPGRADE §2 cut order: shorter sustains and decays, drop alternate takes, space accompaniment every 4 semitones, drop ocarina-hi / balafon / didgeridoo. Never the ocarina, harp, strings or drill Foley.')
    process.exit(1)
  }
}

await main()
