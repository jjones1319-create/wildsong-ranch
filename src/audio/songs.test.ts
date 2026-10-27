import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { checkSong } from './music/checker.ts'
import { CALLING_CARDS, callingCardFor, MUSICAL_EFFECTS } from './music/effects.ts'
import { RIVALS } from '../data/rivals.ts'
import { THEME_IDS } from './recipes/events.ts'
import { loadAllSongs } from './music/songs/index.ts'
import { CROWN_STINGERS, STINGERS } from './music/stingers.ts'
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

  it('musical effects and the calling cards are at most 1.5 s and use only real instruments', () => {
    for (const [id, def] of [...Object.entries(MUSICAL_EFFECTS), ...Object.entries(CALLING_CARDS)]) {
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

describe('the S2 pieces (§15)', () => {
  it('every event theme has lobby, base, drive and tension, a lobby arrangement, at least 70 s of battle music and the match-start hit', () => {
    for (const id of THEME_IDS) {
      const s = songs[id]
      const layers = new Set(s.lines.flatMap((l) => [...l.layers]))
      expect([...layers].sort(), id).toEqual(['base', 'drive', 'lobby', 'tension'])
      expect(s.arrangements?.lobby?.order, id).toEqual(['lobby'])
      const battle = s.order.filter((n) => n !== 'lobby').reduce((t, n) => t + s.sections[n]!.beats, 0)
      expect((battle * 60) / s.bpm, id).toBeGreaterThanOrEqual(70)
      expect(s.order.slice(0, 2), id).toEqual(['lobby', 'intro'])
      expect(s.sections.intro!.events.hit![0]!.pitches.length, id).toBeGreaterThan(1)
      expect(s.lines.find((l) => l.id === 'lead')?.role, id).toBe('lead')
      expect(s.lines.some((l) => l.id === 'colour'), id).toBe(true)
      expect(s.kit, id).toBeTruthy()
    }
  })

  it('the motifs where §3.6 asks, and the derived pieces keep their originals’ form', () => {
    expect(songs.ascension.motifQuote).toBeTruthy()
    expect(songs.legend.motifQuote).toBeTruthy()
    expect(songs.legend.derivedFrom).toBe('wildsong')
    expect(songs.rival.quotes?.some((q) => q.motif === 'corin')).toBe(true)
    expect(songs.masquerade.quotes?.some((q) => q.motif === 'masked')).toBe(true)
    expect(songs['rally-rogue'].derivedFrom).toBe('rally')
    expect(songs.elders.derivedFrom).toBe('sprout')
    for (const [a, b] of [['rally-rogue', 'rally'], ['elders', 'sprout']] as const) {
      expect(Object.keys(songs[a].sections)).toEqual(Object.keys(songs[b].sections))
      for (const n of Object.keys(songs[b].sections)) expect(songs[a].sections[n]!.bars, `${a}/${n}`).toBe(songs[b].sections[n]!.bars)
    }
    expect(songs['crown-tides'].meter).toEqual([6, 8])
    expect(songs['crown-frost'].meter).toEqual([3, 4])
    expect(songs.masquerade.meter).toEqual([3, 4])
  })

  it('the Summit Qualifier drops the horn, the colour and the tension extras', () => {
    const q = songs.summit.arrangements!.qualifier!
    for (const id of ['horn', 'colour', 'trem', 'flourish', 'riser']) expect(q.lines).not.toContain(id)
    for (const id of q.lines!) expect(songs.summit.lines.some((l) => l.id === id), id).toBe(true)
  })

  it('the S2 stingers: each Crown’s quotes its Crown, the Legend’s anthem quotes the motif', () => {
    expect(Object.keys(CROWN_STINGERS).sort()).toEqual(['crown-of-dawn', 'crown-of-embers', 'crown-of-frost', 'crown-of-tides'])
    for (const [event, id] of Object.entries(CROWN_STINGERS)) expect(STINGERS[id].derivedFrom).toBe(event.replace('crown-of-', 'crown-'))
    expect(STINGERS.legendWon.motifQuote).toBeTruthy()
    expect(passSeconds(STINGERS.legendWon)).toBeLessThanOrEqual(10)
    expect(passSeconds(STINGERS.cupPlaced)).toBeCloseTo(3, 1)
    expect(passSeconds(STINGERS.cupOut)).toBeCloseTo(2, 1)
    expect(passSeconds(STINGERS.rankUp)).toBeCloseTo(4, 1)
    expect(passSeconds(STINGERS.titleEarned)).toBeCloseTo(2, 1)
    for (const id of ['crownWonDawn', 'crownWonTides', 'crownWonEmbers', 'crownWonFrost'] as const) {
      expect(passSeconds(STINGERS[id])).toBeGreaterThanOrEqual(7.5)
      expect(passSeconds(STINGERS[id])).toBeLessThanOrEqual(8.5)
    }
  })

  it('every named rival has a calling card', () => {
    for (const r of RIVALS) expect(callingCardFor(r.id), r.id).toBeTruthy()
    expect(callingCardFor('nobody')).toBeNull()
    expect(CALLING_CARDS['card-masked-breeder'].layers.some((l) => l.kind === 'note' && l.semis)).toBe(true)
  })
})
