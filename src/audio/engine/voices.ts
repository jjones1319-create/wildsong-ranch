/**
 * SOUND_UPGRADE §2: voices at once (music 32, ambience 16, effects 16, UI 4). A pool counts the live voices
 * of one bus and, when full, steals one: voices in silent layers first, then the quietest, then the oldest.
 */
import type { Voice } from './sampler.ts'

export interface PooledVoice {
  voice: Voice
  startedAt: number
  /** Louder voices survive longer (0..1). */
  level: number
  silentLayer: boolean
  /** Which line or effect it belongs to, for the debug view. */
  owner: string
}

export class VoicePool {
  readonly limit: number
  readonly name: string
  private list: PooledVoice[] = []
  stolen = 0

  constructor(name: string, limit: number) {
    this.name = name
    this.limit = limit
  }

  /** Drops voices that ended on their own. */
  prune(now: number): void {
    this.list = this.list.filter((v) => !v.voice.stopped && v.voice.endsAt > now)
  }

  count(now: number): number {
    this.prune(now)
    return this.list.length
  }

  /** Makes room for one more voice if needed, stealing by the §4.4 order. Returns the number stolen. */
  makeRoom(now: number): number {
    this.prune(now)
    let stolen = 0
    while (this.list.length >= this.limit) {
      const victim =
        this.list.find((v) => v.silentLayer) ??
        [...this.list].sort((a, b) => a.level - b.level || a.startedAt - b.startedAt)[0]
      if (!victim) break
      victim.voice.stop(now, 0.02)
      this.list = this.list.filter((v) => v !== victim)
      stolen++
    }
    this.stolen += stolen
    return stolen
  }

  add(v: PooledVoice): void {
    this.list.push(v)
  }

  /** Marks the voices of an owner as silent-layer (or not), so they are stolen first. */
  setSilent(owner: string, silent: boolean): void {
    for (const v of this.list) if (v.owner === owner) v.silentLayer = silent
  }

  stopAll(now: number, release = 0.05): void {
    for (const v of this.list) v.voice.stop(now, release)
    this.list = []
  }

  stopOwner(owner: string, now: number, release = 0.05): void {
    for (const v of this.list) if (v.owner === owner) v.voice.stop(now, release)
    this.list = this.list.filter((v) => v.owner !== owner)
  }

  /** The live voices whose owner starts with `prefix` (a song's tag). */
  voicesOf(prefix: string): Voice[] {
    return this.list.filter((v) => v.owner.startsWith(prefix) && !v.voice.stopped).map((v) => v.voice)
  }

  owners(): Record<string, number> {
    const out: Record<string, number> = {}
    for (const v of this.list) out[v.owner] = (out[v.owner] ?? 0) + 1
    return out
  }
}
