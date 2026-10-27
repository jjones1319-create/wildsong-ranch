import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { checkSong } from './music/checker.ts'
import { MUSICAL_EFFECTS } from './music/effects.ts'
import { loadAllSongs } from './music/songs/index.ts'
import { STINGERS } from './music/stingers.ts'
import { passSeconds, type Song } from './music/song.ts'
import { DRILL_CUES } from './recipes/drills.ts'
import { INSTRUMENTS, type SampleRoots } from './recipes/instruments.ts'

/** The sample roots from the committed manifest (§5.3). */
export function manifestRoots(): SampleRoots {
  const m = JSON.parse(readFileSync('public/audio/manifest.json', 'utf8')) as { instruments: Record<string, { arts: Record<string, { root: number }[]> }> }
  const roots: SampleRoots = {}
  for (const [inst, def] of Object.entries(m.instruments)) {
    roots[inst] = {}
    for (const [art, list] of Object.entries(def.arts)) roots[inst]![art] = [...new Set(list.map((s) => s.root))]
  }
  return roots
}

const songs = await loadAllSongs()
const all: Song[] = [...Object.values(songs), ...Object.values(STINGERS), ...Object.values(DRILL_CUES).flatMap((c) => [c.song, ...Object.values(c.stingers)])]
const roots = manifestRoots()

describe('every piece passes the music checker (§6.7)', () => {
  for (const song of all) {
    it(`${song.id} has no errors`, () => {
      const issues = checkSong(song, { roots, others: all.filter((s) => s !== song) })
      expect(issues.filter((i) => i.level === 'error').map((i) => `rule ${i.rule}: ${i.message}`)).toEqual([])
    })
  }
})

describe('the S1 pieces (§15)', () => {
  it('Wildsong carries the motif, the lobby and the credits arrangements', () => {
    const w = songs.wildsong
    expect(w.motifQuote).toEqual({ part: 'lead', section: 'A' })
    expect(Object.keys(w.arrangements ?? {})).toEqual(['lobby', 'credits'])
    expect(w.arrangements!.credits!.heldEnding).toBe(true)
    // The credits arrangement runs 2–3 minutes.
    const credits = passSeconds(w, w.arrangements!.credits)
    expect(credits).toBeGreaterThanOrEqual(120)
    expect(credits).toBeLessThanOrEqual(200)
  })

  it('the four ranch songs breathe, quote the motif and carry the weather rules', () => {
    for (const id of ['ranch-spring', 'ranch-summer', 'ranch-autumn', 'ranch-winter'] as const) {
      const s = songs[id]
      expect(s.kind).toBe('ranch')
      expect(s.breath).toEqual([8, 20])
      expect(s.order).toContain('breath')
      expect(s.motifQuote).toBeTruthy()
      expect(s.weather?.cloudy?.gainDb).toBe(-1.5)
      expect(s.weather?.rain?.swap).toBeTruthy()
      expect(s.weather?.rain?.add).toContain('pad')
      expect(s.weather?.storm?.fragments).toContain('lead')
      expect(s.weather?.storm?.breath).toEqual([15, 30])
      const seconds = passSeconds(s)
      expect(seconds).toBeGreaterThanOrEqual(60)
      expect(seconds).toBeLessThanOrEqual(150)
    }
    expect(songs['ranch-winter'].weather?.snow?.add).toContain('sparkle')
  })

  it('Town has every stem of §7.3 and they all name real lines', () => {
    const t = songs.town
    expect(Object.keys(t.stems ?? {}).sort()).toEqual(['guild', 'journal', 'library', 'mail', 'market', 'oddJobs', 'shop', 'town', 'upgrades'])
    for (const ids of Object.values(t.stems!)) for (const id of ids) expect(t.lines.some((l) => l.id === id)).toBe(true)
    expect(t.stems!.guild).toContain('horn')
    expect(t.stems!.library).toContain('musicbox')
  })

  it('the cup has lobby, base, drive and tension layers, a lobby arrangement and at least 70 s of battle music', () => {
    const c = songs.cup
    const layers = new Set(c.lines.flatMap((l) => [...l.layers]))
    expect([...layers].sort()).toEqual(['base', 'drive', 'lobby', 'tension'])
    expect(c.arrangements?.lobby?.order).toEqual(['lobby'])
    const battleOrder = c.order.filter((n) => n !== 'lobby')
    const beats = battleOrder.reduce((s, n) => s + c.sections[n]!.beats, 0)
    expect((beats * 60) / c.bpm).toBeGreaterThanOrEqual(70)
    expect(c.kit).toBeTruthy()
    // The match-start hit is written in: a harp chord in the intro.
    expect(c.sections.intro!.events.hit![0]!.pitches.length).toBeGreaterThan(1)
  })

  it('stingers are 1.5–10 s and drill outcome stingers 1.2–2.5 s, all in C', () => {
    for (const s of Object.values(STINGERS)) {
      expect(s.tune.key.tonic).toBe(0)
      const sec = passSeconds(s)
      expect(sec).toBeGreaterThanOrEqual(1.5)
      expect(sec).toBeLessThanOrEqual(10)
    }
    for (const cue of Object.values(DRILL_CUES)) {
      for (const s of Object.values(cue.stingers)) {
        const sec = passSeconds(s)
        expect(sec).toBeGreaterThanOrEqual(1.2)
        expect(sec).toBeLessThanOrEqual(2.5)
      }
    }
  })

  it('musical effects are at most 1.5 s and use only real instruments', () => {
    for (const [id, def] of Object.entries(MUSICAL_EFFECTS)) {
      let end = 0
      for (const l of def.layers) {
        const start = l.delay ?? 0
        const len = l.kind === 'noise' || l.kind === 'tone' ? (l.a + (l.h ?? 0) + l.d) / 1000 : l.kind === 'sample' ? 0.5 : l.dur
        end = Math.max(end, start + len)
        if (l.kind === 'sample' || l.kind === 'note' || l.kind === 'chord') expect(INSTRUMENTS[l.inst], `${id} uses ${l.inst}`).toBeTruthy()
      }
      expect(end, `${id} lasts ${end.toFixed(2)} s`).toBeLessThanOrEqual(1.5)
    }
  })
})
