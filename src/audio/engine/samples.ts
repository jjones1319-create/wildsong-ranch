/**
 * SOUND_UPGRADE §5.4: the sample bank. Reads public/audio/manifest.json, decodes packs on demand with
 * `decodeAudioData` (a few files at a time), tracks per-articulation readiness so a screen can swap from the
 * fallback voices as soon as its instruments are in, releases a pack unused for 60 s (core stays), and
 * picks the nearest sample for a note with alternate takes rotating.
 */
import { nearestRoot, type InstrumentId, type SampleRoots } from '../recipes/instruments.ts'
import type { PackId } from '../recipes/packs.ts'

export interface ManifestSample {
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

export interface Manifest {
  version: number
  sampleRate: number
  codec: string
  packs: Record<string, { files: number; bytes: number; seconds: number }>
  instruments: Record<string, { pack: PackId; arts: Record<string, ManifestSample[]> }>
  sources: Record<string, { name: string; url: string; license: string; pin: string | null; sha256: string | null }>
}

export type PackState = 'idle' | 'loading' | 'ready' | 'failed'

export interface PickedSample {
  sample: ManifestSample
  buffer: AudioBuffer
  /** Playback rate for the wanted pitch. */
  rate: number
}

export const RELEASE_AFTER_SEC = 60
const CONCURRENCY = 6

export class SampleBank {
  readonly ctx: BaseAudioContext
  readonly baseUrl: string
  manifest: Manifest | null = null
  private buffers = new Map<string, AudioBuffer>()
  private packs = new Map<string, { state: PackState; decodeMs: number; lastUsed: number; promise: Promise<void> | null }>()
  private takeCounter = new Map<string, number>()
  private fetchFn: typeof fetch
  private manifestPromise: Promise<Manifest> | null = null
  /** Called when an articulation becomes ready (the transport swaps voices). */
  onReady: ((inst: string, art: string) => void) | null = null

  constructor(ctx: BaseAudioContext, baseUrl: string, fetchFn: typeof fetch = (...a) => fetch(...a)) {
    this.ctx = ctx
    this.baseUrl = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`
    this.fetchFn = fetchFn
  }

  loadManifest(): Promise<Manifest> {
    this.manifestPromise ??= this.fetchFn(`${this.baseUrl}audio/manifest.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`manifest ${r.status}`)
        return r.json() as Promise<Manifest>
      })
      .then((m) => {
        this.manifest = m
        return m
      })
    return this.manifestPromise
  }

  packState(pack: string): PackState {
    return this.packs.get(pack)?.state ?? 'idle'
  }

  decodeMs(pack: string): number {
    return this.packs.get(pack)?.decodeMs ?? 0
  }

  packOf(inst: string): PackId | null {
    return this.manifest?.instruments[inst]?.pack ?? null
  }

  /** Decodes every file of a pack; resolves when all are in (failures are logged once and skipped). */
  loadPack(pack: PackId, nowSec: number = this.ctx.currentTime): Promise<void> {
    const existing = this.packs.get(pack)
    if (existing?.promise && existing.state !== 'failed') {
      existing.lastUsed = nowSec
      return existing.promise
    }
    const entry = { state: 'loading' as PackState, decodeMs: 0, lastUsed: nowSec, promise: null as Promise<void> | null }
    this.packs.set(pack, entry)
    entry.promise = (async () => {
      const m = await this.loadManifest()
      const files: ManifestSample[] = []
      for (const inst of Object.values(m.instruments)) if (inst.pack === pack) for (const list of Object.values(inst.arts)) files.push(...list)
      const started = typeof performance !== 'undefined' ? performance.now() : Date.now()
      const pendingByArt = new Map<string, number>()
      for (const f of files) pendingByArt.set(`${f.inst}/${f.art}`, (pendingByArt.get(`${f.inst}/${f.art}`) ?? 0) + 1)
      let failed = 0
      let index = 0
      const worker = async () => {
        while (index < files.length) {
          const f = files[index++]!
          if (!this.buffers.has(f.file)) {
            try {
              const res = await this.fetchFn(`${this.baseUrl}audio/${f.file}`)
              if (!res.ok) throw new Error(String(res.status))
              const bytes = await res.arrayBuffer()
              const buffer = await this.ctx.decodeAudioData(bytes)
              this.buffers.set(f.file, buffer)
            } catch (e) {
              failed++
              if (failed === 1) console.warn(`audio: could not decode ${f.file} (${(e as Error).message}); the fallback voices stay on for it`)
            }
          }
          const key = `${f.inst}/${f.art}`
          const left = (pendingByArt.get(key) ?? 1) - 1
          pendingByArt.set(key, left)
          if (left === 0) this.onReady?.(f.inst, f.art)
        }
      }
      await Promise.all(Array.from({ length: Math.min(CONCURRENCY, files.length) }, worker))
      entry.decodeMs = Math.round((typeof performance !== 'undefined' ? performance.now() : Date.now()) - started)
      entry.state = failed === files.length && files.length > 0 ? 'failed' : 'ready'
    })()
    return entry.promise
  }

  /** Every sample of this articulation is decoded. */
  ready(inst: string, art: string): boolean {
    const list = this.manifest?.instruments[inst]?.arts[art]
    if (!list || list.length === 0) return false
    return list.every((s) => this.buffers.has(s.file))
  }

  hasInstrument(inst: string): boolean {
    return this.manifest?.instruments[inst] !== undefined
  }

  /** The roots per articulation, for ranges and the checker. */
  roots(): SampleRoots {
    const out: SampleRoots = {}
    if (!this.manifest) return out
    for (const [inst, def] of Object.entries(this.manifest.instruments)) {
      out[inst] = {}
      for (const [art, list] of Object.entries(def.arts)) out[inst]![art] = [...new Set(list.map((s) => s.root))]
    }
    return out
  }

  touch(pack: string, nowSec: number): void {
    const p = this.packs.get(pack)
    if (p) p.lastUsed = nowSec
  }

  /** Releases packs (never core) unused for 60 s. */
  sweep(nowSec: number): void {
    for (const [pack, p] of this.packs) {
      if (pack === 'core' || p.state !== 'ready') continue
      if (nowSec - p.lastUsed < RELEASE_AFTER_SEC) continue
      const m = this.manifest
      if (!m) continue
      for (const inst of Object.values(m.instruments)) if (inst.pack === pack) for (const list of Object.values(inst.arts)) for (const s of list) this.buffers.delete(s.file)
      this.packs.delete(pack)
    }
  }

  /** The nearest decoded sample for a pitched note (±4 semitones, preferring the one just below), takes rotating. */
  pick(inst: InstrumentId | string, art: string, midi: number): PickedSample | null {
    const list = this.manifest?.instruments[inst]?.arts[art]
    if (!list) return null
    const roots = [...new Set(list.map((s) => s.root))]
    const root = nearestRoot(roots, midi)
    if (root === null) return null
    const takes = list.filter((s) => s.root === root && this.buffers.has(s.file))
    if (takes.length === 0) return null
    const key = `${inst}/${art}/${root}`
    const n = this.takeCounter.get(key) ?? 0
    this.takeCounter.set(key, n + 1)
    const sample = takes[n % takes.length]!
    const rate = Math.pow(2, (midi - sample.root - sample.cents / 100) / 12)
    return { sample, buffer: this.buffers.get(sample.file)!, rate }
  }

  /** An unpitched hit (drums, Foley): takes rotate, never the same one twice in a row. */
  take(inst: string, art: string): PickedSample | null {
    const list = this.manifest?.instruments[inst]?.arts[art]
    if (!list) return null
    const takes = list.filter((s) => this.buffers.has(s.file))
    if (takes.length === 0) return null
    const key = `${inst}/${art}`
    const n = this.takeCounter.get(key) ?? 0
    this.takeCounter.set(key, n + 1)
    const sample = takes[n % takes.length]!
    return { sample, buffer: this.buffers.get(sample.file)!, rate: 1 }
  }

  /** For the debug view: packs with their states and decode times. */
  packReport(): { pack: string; state: PackState; decodeMs: number }[] {
    return [...this.packs.entries()].map(([pack, p]) => ({ pack, state: p.state, decodeMs: p.decodeMs }))
  }

  loadedBytes(): number {
    let n = 0
    for (const b of this.buffers.values()) n += b.length * b.numberOfChannels * 4
    return n
  }
}
