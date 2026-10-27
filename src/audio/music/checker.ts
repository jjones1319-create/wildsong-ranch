/**
 * SOUND_UPGRADE §6.7: the music checker. The song's kind picks its tempo band and length bounds (§3.2) and
 * which rules apply. It runs over every song in Vitest and shows in the Sound Lab. Pure: it reads the
 * compiled song, the sample roots from the manifest and (for distinctness) the other songs.
 */
import { INSTRUMENTS, nearestRoot, playableRange, type InstrumentId, type SampleRoots } from '../recipes/instruments.ts'
import { strongBeats } from './abc.ts'
import { chordAt, isChordTone, type ChordAt } from './chords.ts'
import { containsMotif, CORIN_MOTIF, MASKED_MOTIF, WILDSONG_MOTIF } from './motifs.ts'
import { BREATH, passSeconds, type LineEvent, type Song, type SongKind } from './song.ts'

export interface CheckIssue {
  rule: number
  level: 'error' | 'warning'
  message: string
  line?: string
  section?: string
  bar?: number
}

export interface CheckContext {
  roots: SampleRoots
  /** The other songs, for rule 13. */
  others?: readonly Song[]
}

/** §3.2 tempo bands in quarter-note BPM, and loop-length bounds in seconds, by kind. */
export const TEMPO_BANDS: Partial<Record<SongKind, readonly [number, number]>> = {
  place: [50, 96],
  ranch: [66, 96],
  town: [96, 112],
  battle: [100, 132],
  drill: [56, 132],
  minigame: [120, 150],
}
export const LENGTH_BOUNDS: Partial<Record<SongKind, readonly [number, number]>> = {
  place: [60, 150],
  ranch: [60, 150],
  town: [60, 150],
  battle: [70, 600],
  stinger: [1.5, 10],
  effect: [0, 1.5],
}

const LEAD_LOW = 57 // A3
const LEAD_HIGH = 88 // E6
const C7 = 96
const A5 = 81
const P_VEL = 0.38
const MP_VEL = 0.5

function topPitch(e: LineEvent): number {
  return Math.max(...e.pitches)
}

export function checkSong(song: Song, ctx: CheckContext): CheckIssue[] {
  const issues: CheckIssue[] = []
  const err = (rule: number, message: string, extra: Partial<CheckIssue> = {}) => issues.push({ rule, level: 'error', message, ...extra })
  const warn = (rule: number, message: string, extra: Partial<CheckIssue> = {}) => issues.push({ rule, level: 'warning', message, ...extra })
  const beatsPerBarN = (song.meter[0] / song.meter[1]) * 4
  const secPerBeat = 60 / song.bpm
  const isBattle = song.kind === 'battle'
  const melodic = song.lines.filter((l) => l.role === 'lead' || l.role === 'counter')

  // 1. Structure.
  if (song.order.length === 0) err(1, 'the order is empty')
  if (song.loopFrom < 0 || song.loopFrom >= song.order.length) err(1, `loopFrom ${song.loopFrom} is outside the order`)

  // 2. Ranges and sample coverage.
  for (const line of song.lines) {
    const def = INSTRUMENTS[line.inst]
    const range = playableRange(ctx.roots, line.inst, line.art)
    const roots = ctx.roots[line.inst]?.[line.art] ?? []
    for (const [name, sec] of Object.entries(song.sections)) {
      for (const e of sec.events[line.id] ?? []) {
        for (const p of e.pitches) {
          if (def.melody === undefined) {
            // Unpitched percussion: nothing to check. Pitched percussion is rate-shifted up to ±9.
            if (line.pitchedPerc && roots.length && roots.every((r) => Math.abs(r - p) > 9)) err(2, `${line.id}: ${p} is more than 9 semitones from any ${line.inst} sample`, { line: line.id, section: name, bar: e.bar })
            continue
          }
          if (range === null) {
            err(2, `${line.id}: ${line.inst}/${line.art} has no samples in the manifest`, { line: line.id, section: name })
            break
          }
          if (p < range[0] || p > range[1]) err(2, `${line.id}: ${p} is outside ${line.inst}'s playable range ${range[0]}–${range[1]}`, { line: line.id, section: name, bar: e.bar })
          else if (!def.patch && nearestRoot(roots, p) === null) err(2, `${line.id}: ${p} is more than 4 semitones from any ${line.inst}/${line.art} sample`, { line: line.id, section: name, bar: e.bar })
          if ((line.role === 'lead' || line.role === 'counter') && (p < def.melody[0] || p > def.melody[1])) err(2, `${line.id}: ${p} is outside ${line.inst}'s melody range ${def.melody[0]}–${def.melody[1]}`, { line: line.id, section: name, bar: e.bar })
          if ((line.role === 'lead' || line.role === 'counter') && (p < LEAD_LOW || p > LEAD_HIGH)) err(10, `${line.id}: ${p} is outside the lead register A3–E6`, { line: line.id, section: name, bar: e.bar })
        }
      }
    }
  }

  // 3. Monophonic instruments never overlap.
  for (const line of song.lines) {
    if (!INSTRUMENTS[line.inst].mono) continue
    for (const [name, sec] of Object.entries(song.sections)) {
      const evs = (sec.events[line.id] ?? []).map((e) => ({ s: e.bar * beatsPerBarN + e.t, e: e.bar * beatsPerBarN + e.t + e.dur, bar: e.bar }))
      for (let i = 1; i < evs.length; i++) if (evs[i]!.s < evs[i - 1]!.e - 1e-6) err(3, `${line.id}: notes overlap in bar ${evs[i]!.bar + 1} (${line.inst} is monophonic)`, { line: line.id, section: name, bar: evs[i]!.bar })
      for (const e of sec.events[line.id] ?? []) if (e.pitches.length > 1) err(3, `${line.id}: a chord on a monophonic instrument`, { line: line.id, section: name, bar: e.bar })
    }
  }

  // 4. Wind leads breathe.
  for (const line of melodic) {
    if (INSTRUMENTS[line.inst].family !== 'wind') continue
    const limitBeats = Math.min(4 * beatsPerBarN, 8 / secPerBeat)
    for (const [name, sec] of Object.entries(song.sections)) {
      const evs = sec.events[line.id] ?? []
      let runStart: number | null = null
      let lastEnd = 0
      for (const e of evs) {
        const s = e.bar * beatsPerBarN + e.t
        if (runStart === null || s - lastEnd >= 0.5 - 1e-6) runStart = s
        lastEnd = s + e.dur
        if (lastEnd - runStart > limitBeats + 1e-6) {
          err(4, `${line.id}: no breath for ${((lastEnd - runStart) * secPerBeat).toFixed(1)} s ending in bar ${e.bar + 1}`, { line: line.id, section: name, bar: e.bar })
          runStart = lastEnd
        }
      }
    }
  }

  // 5. Melodic rules for lead and counter parts.
  if (song.kind !== 'drone') {
    for (const line of melodic) {
      let moves = 0
      let steps = 0
      let wideLeaps = 0
      let recovered = 0
      for (const [name, sec] of Object.entries(song.sections)) {
        const evs = sec.events[line.id] ?? []
        for (let i = 0; i < evs.length; i++) {
          const e = evs[i]!
          const p = topPitch(e)
          const next = evs[i + 1]
          if (next) {
            const q = topPitch(next)
            const iv = q - p
            moves++
            if (Math.abs(iv) <= 2) steps++
            if (Math.abs(iv) > 12) err(5, `${line.id}: a leap of ${Math.abs(iv)} semitones in bar ${next.bar + 1}`, { line: line.id, section: name, bar: next.bar })
            if (Math.abs(iv) > 7) {
              wideLeaps++
              const after = evs[i + 2]
              if (after) {
                const back = topPitch(after) - q
                if (Math.abs(back) <= 2 && Math.sign(back) === -Math.sign(iv)) recovered++
              } else recovered++
            }
          }
          // Phrase-final notes (followed by a rest, or the last of the section) are chord tones.
          const endsPhrase = !next || next.phraseStart === true
          if (endsPhrase && sec.chordTrack.length) {
            const c = chordAt(sec.chordTrack, e.bar, e.t)
            if (c && !isChordTone(c, p)) err(5, `${line.id}: phrase ends on ${p}, not a tone of ${c.text} (bar ${e.bar + 1})`, { line: line.id, section: name, bar: e.bar })
          }
        }
      }
      if (moves >= 8) {
        const share = steps / moves
        if (share < 0.55 || share > 0.85) err(5, `${line.id}: ${(share * 100).toFixed(0)}% of moves are steps (55–85% wanted)`, { line: line.id })
      }
      if (wideLeaps > 0 && recovered / wideLeaps < 0.8) err(5, `${line.id}: only ${recovered}/${wideLeaps} wide leaps turn back by step`, { line: line.id })
    }
  }

  // 6. Downbeats: chord tone or a suspension that resolves by step within the bar; no minor 2nd / major 7th against the bass.
  for (const line of melodic) {
    for (const [name, sec] of Object.entries(song.sections)) {
      if (sec.chordTrack.length === 0) continue
      const evs = sec.events[line.id] ?? []
      for (let b = 0; b < sec.bars; b++) {
        const sounding = evs.find((e) => e.bar === b && e.t === 0) ?? evs.find((e) => e.bar * beatsPerBarN + e.t < b * beatsPerBarN && e.bar * beatsPerBarN + e.t + e.dur > b * beatsPerBarN + 1e-6)
        if (!sounding) continue
        const c = chordAt(sec.chordTrack, b, 0)
        if (!c) continue
        const p = topPitch(sounding)
        if (!isChordTone(c, p)) {
          const idx = evs.indexOf(sounding)
          const next = evs[idx + 1]
          const resolves = next && next.bar === b && Math.abs(topPitch(next) - p) <= 2 && isChordTone(c, topPitch(next))
          if (!resolves) err(6, `${line.id}: downbeat ${p} of bar ${b + 1} is not a tone of ${c.text} and does not resolve by step`, { line: line.id, section: name, bar: b })
        }
        const againstBass = (((p - c.bass) % 12) + 12) % 12
        if (againstBass === 1 || againstBass === 11) warn(6, `${line.id}: ${p} is a ${againstBass === 1 ? 'minor 2nd' : 'major 7th'} against the bass of ${c.text} in bar ${b + 1}`, { line: line.id, section: name, bar: b })
      }
    }
  }

  // 7. The lead sits at least a 3rd above the highest accompaniment note on strong beats.
  const accompLines = song.lines.filter((l) => l.role === 'accomp')
  for (const line of melodic.filter((l) => l.role === 'lead')) {
    for (const [name, sec] of Object.entries(song.sections)) {
      const evs = sec.events[line.id] ?? []
      for (let b = 0; b < sec.bars; b++) {
        for (const sb of strongBeats(song.meter)) {
          const at = b * beatsPerBarN + sb
          const lead = evs.find((e) => e.bar * beatsPerBarN + e.t <= at + 1e-6 && e.bar * beatsPerBarN + e.t + e.dur > at + 1e-6)
          if (!lead) continue
          let top = -Infinity
          for (const a of accompLines) {
            for (const e of sec.events[a.id] ?? []) {
              const s = e.bar * beatsPerBarN + e.t
              if (s <= at + 1e-6 && s + e.dur > at + 1e-6 && e.pitches.length) top = Math.max(top, ...e.pitches)
            }
          }
          if (top !== -Infinity && topPitch(lead) < top + 3) {
            warn(7, `${line.id}: ${topPitch(lead)} sits under the accompaniment (${top}) on a strong beat of bar ${b + 1}`, { line: line.id, section: name, bar: b })
            break
          }
        }
      }
    }
  }

  // 8. Tempo band and loop length.
  const band = TEMPO_BANDS[song.kind]
  if (band && (song.bpm < band[0] || song.bpm > band[1])) err(8, `tempo ${song.bpm} is outside the ${song.kind} band ${band[0]}–${band[1]}`)
  const bounds = LENGTH_BOUNDS[song.kind]
  const seconds = passSeconds(song)
  if (bounds && (seconds < bounds[0] || seconds > bounds[1])) err(8, `one pass is ${seconds.toFixed(1)} s; a ${song.kind} wants ${bounds[0]}–${bounds[1]} s`)
  if (song.kind === 'drill') {
    const bars = song.order.filter((n) => n !== BREATH).reduce((s, n) => s + song.sections[n]!.bars, 0)
    if (bars < 2 || bars > 4) err(8, `a drill bed loops 2–4 bars, this one has ${bars}`)
  }

  // 9. Variety.
  if (song.kind === 'place' || song.kind === 'ranch' || song.kind === 'town' || song.kind === 'battle') {
    const lead = song.lines.find((l) => l.role === 'lead')
    if (lead) {
      const sigOf = (bars: number[][]) => bars.map((b) => b.join(',')).join('|')
      const names = Object.keys(song.sections)
      const sigs = names.map((n) => sigOf(song.sections[n]!.voiceBars[lead.id] ?? []))
      const distinct = new Set(sigs)
      if (distinct.size < 2) err(9, 'fewer than two contrasting sections')
      const allBars = names.flatMap((n) => song.sections[n]!.voiceBars[lead.id] ?? []).filter((b) => b.some((p) => p >= 0))
      const seen = new Set<string>()
      let identical = 0
      for (const b of allBars) {
        const k = b.join(',')
        if (seen.has(k)) identical++
        else seen.add(k)
      }
      if (allBars.length && identical / allBars.length > 0.35) err(9, `${((identical / allBars.length) * 100).toFixed(0)}% of lead bars repeat an earlier bar (35% allowed)`)
      let varied = false
      for (let i = 0; i < names.length && !varied; i++) {
        for (let j = 0; j < names.length; j++) {
          if (i === j) continue
          const a = song.sections[names[i]!]!.voiceBars[lead.id] ?? []
          const b = song.sections[names[j]!]!.voiceBars[lead.id] ?? []
          if (a.length === 0 || sigOf(a) === sigOf(b)) continue
          const shared = a.filter((bar, k) => b[k] && bar.join(',') === b[k]!.join(',')).length
          if (shared >= Math.ceil(a.length * 0.4)) {
            varied = true
            break
          }
        }
      }
      if (!varied) err(9, 'no varied repeat: no section shares at least 40% of its lead bars with another while differing')
    }
  }

  // 10. Register and density.
  for (const line of song.lines) {
    const def = INSTRUMENTS[line.inst]
    if (def.melody === undefined) continue
    for (const [name, sec] of Object.entries(song.sections)) {
      for (const e of sec.events[line.id] ?? []) {
        const p = topPitch(e)
        if (p > C7 && !(def.bright && e.vel <= P_VEL)) err(10, `${line.id}: ${p} is above C7 (only bright colours at p or softer may go there)`, { line: line.id, section: name, bar: e.bar })
        if (p > A5 && e.dur >= 1 && e.vel > MP_VEL + 1e-6) err(10, `${line.id}: a sustained ${p} above A5 at louder than mp`, { line: line.id, section: name, bar: e.bar })
      }
    }
  }
  {
    const limit = isBattle ? 6 : 4
    const melodicLine = (l: (typeof song.lines)[number]) => (l.role === 'lead' || l.role === 'counter' || l.role === 'accomp') && !(isBattle && l.layers.every((x) => x === 'lobby'))
    // Stems never sound together, so a song with stems is checked stem by stem.
    const groups: { name: string; lines: typeof song.lines }[] = song.stems ? Object.entries(song.stems).map(([name, ids]) => ({ name, lines: song.lines.filter((l) => ids.includes(l.id) && melodicLine(l)) })) : [{ name: '', lines: song.lines.filter(melodicLine) }]
    for (const group of groups) {
      for (const [name, sec] of Object.entries(song.sections)) {
        const steps = Math.round(sec.beats * 4)
        for (let s = 0; s < steps; s++) {
          const at = s / 4 + 1e-4
          let n = 0
          for (const l of group.lines) if ((sec.events[l.id] ?? []).some((e) => e.bar * beatsPerBarN + e.t <= at && e.bar * beatsPerBarN + e.t + e.dur > at)) n++
          if (n > limit) {
            err(10, `${n} melodic voices sound at once in bar ${Math.floor(at / beatsPerBarN) + 1}${group.name ? ` of stem ${group.name}` : ''} (${limit} allowed)`, { section: name, bar: Math.floor(at / beatsPerBarN) })
            break
          }
        }
      }
    }
  }

  // 11. Bright colours never carry more than 2 bars alone.
  for (const line of melodic) {
    if (!INSTRUMENTS[line.inst].bright) continue
    for (const [name, sec] of Object.entries(song.sections)) {
      const others = melodic.filter((l) => l !== line)
      let alone = 0
      for (let b = 0; b < sec.bars; b++) {
        const mine = (sec.events[line.id] ?? []).some((e) => e.bar === b)
        const theirs = others.some((o) => (sec.events[o.id] ?? []).some((e) => e.bar === b))
        alone = mine && !theirs ? alone + 1 : 0
        if (alone > 2) {
          warn(11, `${line.id}: a bright colour carries the line alone for more than 2 bars (bar ${b + 1})`, { line: line.id, section: name, bar: b })
          break
        }
      }
    }
  }

  // 12. The motifs where §3.6 requires them: the Wildsong motif in the title, the ranch songs, the Ascension
  // and the Legend; Corin's motif in the rival theme; the masked turn in the Masquerade.
  const needsMotif = song.kind === 'ranch' || song.id === 'wildsong' || song.id === 'ascension' || song.id === 'legend'
  if (needsMotif || song.motifQuote) {
    const q = song.motifQuote
    if (!q) err(12, 'this song must quote the Wildsong motif (motifQuote)')
    else {
      const sec = song.sections[q.section]
      const evs = sec?.events[q.part]
      if (!sec || !evs) err(12, `motifQuote names ${q.part}/${q.section}, which does not exist`)
      else if (!containsMotif(evs.map(topPitch), WILDSONG_MOTIF)) err(12, `the Wildsong motif is not in ${q.part}/${q.section}`)
    }
  }

  const needs: Partial<Record<string, 'corin' | 'masked'>> = { rival: 'corin', masquerade: 'masked' }
  const wanted = needs[song.id]
  if (wanted && !song.quotes?.some((q) => q.motif === wanted)) err(12, `this song must quote the ${wanted} motif (quotes)`)
  for (const q of song.quotes ?? []) {
    const evs = song.sections[q.section]?.events[q.part]
    const m = q.motif === 'corin' ? CORIN_MOTIF : MASKED_MOTIF
    if (!evs) err(12, `a ${q.motif} quote names ${q.part}/${q.section}, which does not exist`)
    else if (!containsMotif(evs.map(topPitch), m)) err(12, `the ${q.motif} motif is not in ${q.part}/${q.section}`)
  }

  // 13. Distinctness across songs.
  if (ctx.others?.length) {
    const mine = leadWindows(song)
    for (const other of ctx.others) {
      if (other.id === song.id || other.derivedFrom === song.id || song.derivedFrom === other.id) continue
      const theirs = leadWindows(other)
      for (const [sig, where] of mine) {
        if (theirs.has(sig)) {
          err(13, `${where} shares a 2-bar lead phrase with ${other.id} (${theirs.get(sig)})`)
          break
        }
      }
    }
  }

  // 14. Banned instruments: every id is in the table (defineSong already insists), and no banned words.
  for (const line of song.lines) {
    const id: string = line.inst
    if (!(id in INSTRUMENTS)) err(14, `${line.id}: ${id} is not an allowed instrument`)
  }
  return issues
}

/** Every 2-bar window of the lead's interval-and-rhythm signature, with where it sits. Motif windows are exempt. */
function leadWindows(song: Song): Map<string, string> {
  const out = new Map<string, string>()
  const lead = song.lines.find((l) => l.role === 'lead')
  if (!lead) return out
  for (const [name, sec] of Object.entries(song.sections)) {
    const evs = sec.events[lead.id] ?? []
    for (let b = 0; b + 1 < sec.bars; b++) {
      const win = evs.filter((e) => e.bar === b || e.bar === b + 1)
      if (win.length < 4) continue
      const pitches = win.map(topPitch)
      if (containsMotif(pitches, WILDSONG_MOTIF)) continue
      const sig = win.map((e, i) => `${i ? topPitch(e) - topPitch(win[i - 1]!) : 'x'}:${e.dur}`).join(' ')
      if (!out.has(sig)) out.set(sig, `${song.id}/${name} bars ${b + 1}–${b + 2}`)
    }
  }
  return out
}

export type { ChordAt, InstrumentId }
