import { lookKey, type LookId } from '../art/models.ts'
import { ART, STAGES } from '../data/tuning.ts'
import { KEY_PREFIX, type KeyValueStore } from './db.ts'

/**
 * Art 2.0 (ART_2_PLAN §3.3): pictures of the 3D monsters for lists and pickers. The base look (prime size,
 * neutral face) ships as a precached WebP; every other (look, size band, face) is drawn on the phone the first
 * time it is needed and kept in IndexedDB under `wildsong/portrait/…`. Classic shows until a picture is ready.
 * Written against the store interface so the rules run on an in-memory store in tests.
 */

export type PortraitBand = 'small' | 'medium' | 'full' | 'old'

export interface PortraitReq {
  look: LookId
  variant: string | null
  stage: number
  face: string
}

export interface PortraitJob extends PortraitReq {
  band: PortraitBand
  /** The stage the band is drawn at. */
  drawStage: number
}

export type PortraitRenderer = (job: PortraitJob) => Promise<Blob | null>

export const PORTRAIT_PREFIX = `${KEY_PREFIX}portrait/`

/** Monsters are drawn at three sizes (STAGES.sizePct) and old ones fade, so pictures are shared per band. */
export function portraitBand(stage: number): PortraitBand {
  if (stage >= STAGES.visiblyOld) return 'old'
  if (stage <= STAGES.sizePct.smallUntil) return 'small'
  if (stage <= STAGES.sizePct.mediumUntil) return 'medium'
  return 'full'
}

export function bandStage(band: PortraitBand): number {
  switch (band) {
    case 'small':
      return 1
    case 'medium':
      return STAGES.sizePct.smallUntil + 1
    case 'old':
      return STAGES.visiblyOld
    default:
      return STAGES.prime[0]
  }
}

/** True when the precached base picture serves this request. */
export function isBasePortrait(req: PortraitReq): boolean {
  return portraitBand(req.stage) === 'full' && req.face === 'neutral'
}

export function portraitKey(req: PortraitReq): string {
  return `${PORTRAIT_PREFIX}v${ART.portrait.version}/${lookKey({ look: req.look, variant: req.variant })}/${portraitBand(req.stage)}/${req.face}`
}

interface Stored {
  at: number
  type: string
  blob: Blob
}

export class PortraitCache {
  private readonly store: KeyValueStore
  private readonly render: PortraitRenderer
  private readonly makeUrl: (b: Blob) => string
  private readonly mem = new Map<string, string>()
  private readonly pending = new Map<string, Promise<string | null>>()
  private queue: Promise<unknown> = Promise.resolve()
  private swept = false

  constructor(store: KeyValueStore, render: PortraitRenderer, makeUrl: (b: Blob) => string = (b) => URL.createObjectURL(b)) {
    this.store = store
    this.render = render
    this.makeUrl = makeUrl
  }

  /** A picture already in memory, or null. */
  peek(req: PortraitReq): string | null {
    return this.mem.get(portraitKey(req)) ?? null
  }

  /** Memory → IndexedDB → drawn (one at a time) → stored. Never throws. */
  get(req: PortraitReq): Promise<string | null> {
    const key = portraitKey(req)
    const hit = this.mem.get(key)
    if (hit) return Promise.resolve(hit)
    const inflight = this.pending.get(key)
    if (inflight) return inflight
    const p = this.lookup(key, req).finally(() => this.pending.delete(key))
    this.pending.set(key, p)
    return p
  }

  private async lookup(key: string, req: PortraitReq): Promise<string | null> {
    try {
      if (!this.swept) {
        this.swept = true
        await this.sweepOldVersions()
      }
      const stored = (await this.store.get(key)) as Stored | undefined
      if (stored && stored.blob) {
        const url = this.makeUrl(stored.blob)
        this.mem.set(key, url)
        return url
      }
    } catch {
      /* a broken store reads as empty */
    }
    const band = portraitBand(req.stage)
    const job: PortraitJob = { ...req, band, drawStage: bandStage(band) }
    const run = this.queue.then(() => this.render(job)).catch(() => null)
    this.queue = run
    const blob = await run
    if (!blob) return null
    const url = this.makeUrl(blob)
    this.mem.set(key, url)
    try {
      await this.store.set(key, { at: Date.now(), type: blob.type, blob } satisfies Stored)
      await this.trim()
    } catch {
      /* storage full or blocked: the picture still shows this session */
    }
    return url
  }

  /** Keep the newest `ART.portrait.cacheMaxEntries` pictures. */
  async trim(): Promise<number> {
    const keys = (await this.store.keys()).filter((k) => k.startsWith(PORTRAIT_PREFIX))
    if (keys.length <= ART.portrait.cacheMaxEntries) return 0
    const stamped: { key: string; at: number }[] = []
    for (const k of keys) {
      const v = (await this.store.get(k)) as Stored | undefined
      stamped.push({ key: k, at: v?.at ?? 0 })
    }
    stamped.sort((a, b) => a.at - b.at)
    const drop = stamped.slice(0, keys.length - ART.portrait.cacheMaxEntries)
    for (const d of drop) await this.store.del(d.key)
    return drop.length
  }

  /** Pictures from an older art version are stale: drop them once per session. */
  async sweepOldVersions(): Promise<number> {
    const current = `${PORTRAIT_PREFIX}v${ART.portrait.version}/`
    let n = 0
    try {
      for (const k of await this.store.keys()) {
        if (k.startsWith(PORTRAIT_PREFIX) && !k.startsWith(current)) {
          await this.store.del(k)
          n++
        }
      }
    } catch {
      /* ignore */
    }
    return n
  }
}
