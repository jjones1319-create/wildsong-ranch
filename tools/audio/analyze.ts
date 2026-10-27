/**
 * SOUND_UPGRADE §6.7: `npm run audio:analyze [-- <songId>…]` prints, for each song: key, tempo, meter,
 * length, range, step share, leaps, repetition, layers, and the checker's errors and warnings.
 * Runs on Node 24 directly; the sample roots come from public/audio/manifest.json.
 */
import { checkSong, type CheckIssue } from '../../src/audio/music/checker.ts'
import { SONG_LOADERS } from '../../src/audio/music/songs/index.ts'
import { STINGERS } from '../../src/audio/music/stingers.ts'
import { DRILL_CUES } from '../../src/audio/recipes/drills.ts'
import type { Song } from '../../src/audio/music/song.ts'
import { passSeconds } from '../../src/audio/music/song.ts'
import { INSTRUMENTS } from '../../src/audio/recipes/instruments.ts'
import { manifestRoots } from './manifest.ts'

function describe(song: Song): string {
  const lead = song.lines.find((l) => l.role === 'lead')
  let lo = Infinity
  let hi = -Infinity
  let moves = 0
  let steps = 0
  let leaps = 0
  if (lead) {
    for (const sec of Object.values(song.sections)) {
      const evs = sec.events[lead.id] ?? []
      evs.forEach((e, i) => {
        const p = Math.max(...e.pitches)
        lo = Math.min(lo, p)
        hi = Math.max(hi, p)
        const n = evs[i + 1]
        if (n) {
          const iv = Math.abs(Math.max(...n.pitches) - p)
          moves++
          if (iv <= 2) steps++
          if (iv > 7) leaps++
        }
      })
    }
  }
  const layers = [...new Set(song.lines.flatMap((l) => [...l.layers]))]
  const insts = [...new Set(song.lines.map((l) => `${l.inst}${INSTRUMENTS[l.inst].mono ? '*' : ''}`))]
  return [
    `${song.id} (${song.kind}): ${song.tune.key.text} · ${song.tune.tempoText} (${song.bpm} quarter BPM) · ${song.meter[0]}/${song.meter[1]} · ${passSeconds(song).toFixed(1)} s per pass`,
    `  sections ${Object.keys(song.sections).join(' ')} · order ${song.order.join(' ')} (loop from ${song.loopFrom})`,
    `  lead ${lead ? `${lead.inst} ${lo}–${hi}` : 'none'} · steps ${moves ? Math.round((steps / moves) * 100) : 0}% · leaps > 5th ${leaps} · layers ${layers.join(' ')}`,
    `  lines ${insts.join(', ')}`,
  ].join('\n')
}

function printIssues(issues: CheckIssue[]): void {
  for (const i of issues) console.log(`  ${i.level === 'error' ? '✗' : '⚠'} rule ${i.rule}: ${i.message}`)
  if (issues.length === 0) console.log('  ✓ no issues')
}

async function main(): Promise<void> {
  const roots = manifestRoots()
  const wanted = process.argv.slice(2)
  const songs: Song[] = []
  for (const [id, load] of Object.entries(SONG_LOADERS)) {
    if (wanted.length && !wanted.includes(id)) continue
    try {
      songs.push((await load()).default)
    } catch (e) {
      console.log(`${id}: cannot load (${(e as Error).message.split('\n')[0]})`)
    }
  }
  if (wanted.length === 0 || wanted.includes('stingers')) songs.push(...Object.values(STINGERS))
  if (wanted.length === 0 || wanted.includes('drills')) for (const cue of Object.values(DRILL_CUES)) songs.push(cue.song, ...Object.values(cue.stingers))
  let errors = 0
  for (const song of songs) {
    console.log(describe(song))
    const issues = checkSong(song, { roots, others: songs.filter((s) => s !== song) })
    printIssues(issues)
    errors += issues.filter((i) => i.level === 'error').length
  }
  console.log(`${songs.length} pieces, ${errors} errors`)
  if (errors) process.exit(1)
}

await main()
