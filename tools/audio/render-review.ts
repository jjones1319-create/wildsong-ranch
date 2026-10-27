/**
 * SOUND_UPGRADE §14.3–14.4: `npm run audio:check [-- --calibrate --quick --only <id>]` and `npm run audio:review`.
 *
 * Builds the app (unless --no-build), serves dist/ on port 4173, drives the installed Chrome headlessly with
 * Playwright to the Sound Lab, and asks `window.__audio.render(item, seed)` for every song, layer, bed,
 * drill cue, stinger and effect group at a fixed seed. The real engine renders offline in the page and
 * measures itself; only numbers come back (plus the master PCM for the review files).
 *
 * --check   gates every §14.3 target and exits 1 on a failure; --calibrate writes per-song, per-bed and
 *           per-effect trims to src/audio/levels.json (fails if any trim would exceed ±6 dB), then re-checks.
 * --review  writes audio-review/<id>.ogg (Opus 96 kbps) and audio-review/index.html with players, the
 *           numbers next to the legacy baseline, and the checker notes.
 */
import { chromium, type Page } from '@playwright/test'
import { execFileSync, spawn, type ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { encodeWav } from '../../src/audio/analysis/wav.ts'
import { checkSong } from '../../src/audio/music/checker.ts'
import { CALLING_CARD_IDS, MUSICAL_EFFECT_IDS } from '../../src/audio/music/effects.ts'
import { THEME_IDS, type ThemeId } from '../../src/audio/recipes/events.ts'
import { CROWD_SIZES, type CrowdSize } from '../../src/audio/recipes/ambience.ts'
import { SONG_LOADERS } from '../../src/audio/music/songs/index.ts'
import { STINGER_IDS, STINGERS } from '../../src/audio/music/stingers.ts'
import { passSeconds, type Song } from '../../src/audio/music/song.ts'
import { BED_IDS } from '../../src/audio/recipes/ambience.ts'
import { DRILL_CUES } from '../../src/audio/recipes/drills.ts'
import { UI_SFX_IDS, WORLD_SFX_IDS } from '../../src/audio/recipes/sfx.ts'
import type { RenderItem, RenderResult } from '../../src/audio/renderTypes.ts'
import { ELEMENTS } from '../../src/data/types.ts'
import { manifestRoots } from './manifest.ts'
import { encodeReview, hasLibopus } from './opus.ts'

const args = process.argv.slice(2)
const flag = (f: string) => args.includes(f)
const after = (f: string) => {
  const i = args.indexOf(f)
  return i >= 0 ? args[i + 1] : undefined
}
const CHECK = flag('--check') || !flag('--review')
const REVIEW = flag('--review')
const CALIBRATE = flag('--calibrate')
const QUICK = flag('--quick')
const ONLY = after('--only')
/** Items rendered at once, each in its own page (the renders are single-threaded; two use two cores). */
const JOBS = Math.max(1, Number(after('--jobs') ?? 2))
const NO_BUILD = flag('--no-build')
const BASE = 'http://localhost:4173/wildsong-ranch/'
const OUT = 'audio-review'
const LEVELS = 'src/audio/levels.json'

interface Levels {
  note: string
  songs: Record<string, number>
  beds: Record<string, number>
  effects: Record<string, number>
}

interface Spec {
  id: string
  item: RenderItem
  group: 'song' | 'battle' | 'lobby' | 'tension' | 'bed' | 'drill' | 'stinger' | 'musical' | 'ui' | 'battleFx' | 'seam'
  /** The calibration key (song id, bed id or effect id), if this item calibrates something. */
  key?: { kind: keyof Omit<Levels, 'note'>; id: string }
  /** LUFS target for the measured stem (integrated), with the stem it is measured on. */
  target?: { lufs: number; stem: 'music' | 'master' | 'ambience' | 'sfx' | 'ui' }
}

function specs(): Spec[] {
  const out: Spec[] = []
  for (const id of ['wildsong', 'ranch-spring', 'ranch-summer', 'ranch-autumn', 'ranch-winter', 'town'] as const) {
    out.push({ id, item: { kind: 'song', id, seconds: 45, layers: ['main'], weather: 'Sunny', stem: id === 'town' ? 'town' : null }, group: 'song', key: { kind: 'songs', id }, target: { lufs: -20, stem: 'music' } })
  }
  if (!QUICK) for (const stem of ['shop', 'market', 'guild', 'library', 'mail', 'upgrades', 'oddJobs']) out.push({ id: `town:${stem}`, item: { kind: 'song', id: 'town', seconds: 20, layers: ['main'], stem }, group: 'song' })
  // Every event theme: the scripted 60 s battle with its event's crowd, then the lobby and the tension layer alone.
  const THEME_CROWD: Partial<Record<ThemeId, CrowdSize>> = { open: 'medium', ascension: 'large', 'crown-dawn': 'large+', 'crown-tides': 'large+', 'crown-embers': 'large+', 'crown-frost': 'large+', legend: 'huge', masquerade: 'hushed', rival: 'medium', summit: 'chanting', trial: 'none', practice: 'none' }
  for (const id of THEME_IDS) {
    if (QUICK && id !== 'cup') continue
    out.push({ id, item: { kind: 'battleDemo', seconds: 60, song: id, crowd: THEME_CROWD[id] ?? 'small' }, group: 'battle', key: { kind: 'songs', id }, target: { lufs: -18, stem: 'music' } })
    out.push({ id: `${id}:lobby`, item: { kind: 'song', id, seconds: 30, layers: ['lobby'], arrangement: 'lobby' }, group: 'lobby', target: { lufs: -22, stem: 'music' } })
    out.push({ id: `${id}:tension`, item: { kind: 'song', id, seconds: 30, layers: ['base', 'drive', 'tension'] }, group: 'tension', target: { lufs: -18, stem: 'music' } })
  }
  if (!QUICK) out.push({ id: 'summit:qualifier', item: { kind: 'song', id: 'summit', seconds: 30, layers: ['base', 'drive'], arrangement: 'qualifier' }, group: 'tension', target: { lufs: -18, stem: 'music' } })
  for (const id of BED_IDS) {
    if (QUICK && id !== 'meadow' && id !== 'waterfall-near') continue
    out.push({ id: `bed:${id}`, item: { kind: 'bed', id, seconds: 20, weather: 'Sunny', crowd: id === 'arena' ? 'small' : undefined }, group: 'bed', key: { kind: 'beds', id }, target: { lufs: id === 'waterfall-near' ? -24 : -32, stem: 'ambience' } })
  }
  for (const cue of Object.values(DRILL_CUES)) {
    for (const outcome of ['Great', 'Success', 'Cheat', 'Fail', 'Slacked'] as const) {
      if (QUICK && outcome !== 'Success') continue
      out.push({ id: `drill:${cue.id}:${outcome}`, item: { kind: 'drill', drill: cue.id === 'generic' ? 'hill-sprints' : cue.id, outcome, seconds: 9 }, group: 'drill', key: { kind: 'songs', id: cue.song.id }, target: { lufs: (cue.id === 'waterfall-stand' ? -24 : -22) - (outcome === 'Slacked' ? 1 : 0), stem: 'master' } })
    }
  }
  for (const id of STINGER_IDS) {
    if (QUICK && id !== 'matchWin' && id !== 'crownWonDawn') continue
    out.push({ id: `stinger:${id}`, item: { kind: 'stinger', id, transpose: 2 }, group: 'stinger', key: { kind: 'songs', id }, target: { lufs: -20, stem: 'music' } })
  }
  // A results chain (§4.7): three stingers back to back, checked for clicks and gaps.
  if (!QUICK) out.push({ id: 'stinger:chain', item: { kind: 'stinger', id: 'cupWin', chain: ['cupWin', 'rankUp', 'titleEarned'], transpose: 2 }, group: 'stinger' })
  for (const id of [...MUSICAL_EFFECT_IDS, ...CALLING_CARD_IDS]) {
    if (QUICK && id !== 'coin' && id !== 'card-corin-hale') continue
    out.push({ id: `effect:${id}`, item: { kind: 'effect', id, seconds: 3 }, group: 'musical', key: { kind: 'effects', id } })
  }
  // Every crowd size over the arena bed (reported: clicks and peaks; §9.4 sets no loudness target).
  if (!QUICK) for (const size of CROWD_SIZES) if (size !== 'none') out.push({ id: `crowd:${size}`, item: { kind: 'bed', id: 'arena', seconds: 20, weather: 'Sunny', crowd: size }, group: 'bed' })
  for (const id of UI_SFX_IDS) {
    if (QUICK && id !== 'tap') continue
    out.push({ id: `ui:${id}`, item: { kind: 'effect', id, seconds: 1.5 }, group: 'ui', key: { kind: 'effects', id } })
  }
  for (const id of WORLD_SFX_IDS) {
    if (QUICK && id !== 'stoneHum') continue
    out.push({ id: `world:${id}`, item: { kind: 'effect', id, seconds: 3 }, group: 'musical', key: { kind: 'effects', id } })
  }
  for (const element of ELEMENTS) {
    if (QUICK && element !== 'Fire') continue
    for (const strength of ['light', 'medium', 'heavy'] as const) {
      if (QUICK && strength !== 'medium') continue
      out.push({ id: `battle:${element}:${strength}`, item: { kind: 'battleFx', kinds: ['fire', 'travel', 'hit', 'crit', 'miss', 'special', 'ko'], element, strength }, group: 'battleFx' })
    }
  }
  if (!QUICK) for (const element of ['Physical', 'Nature', 'Light'] as const) out.push({ id: `battle:${element}:kinds`, item: { kind: 'battleFx', kinds: ['push', 'dash', 'distract', 'wither', 'heal'], element, strength: 'medium' }, group: 'battleFx' })
  if (!ONLY) return out
  const wanted = ONLY.split(',').map((x) => x.trim()).filter(Boolean)
  return out.filter((s) => wanted.some((w) => s.id === w || s.id.startsWith(`${w}:`)))
}

/* ---------- gates (§14.3) ---------- */

interface Verdict {
  id: string
  ok: boolean
  notes: string[]
  measured: Record<string, number>
}

function gate(s: Spec, r: RenderResult, levels: Levels): Verdict {
  const notes: string[] = []
  const measured: Record<string, number> = {}
  let ok = true
  const fail = (msg: string) => {
    ok = false
    notes.push(`✗ ${msg}`)
  }
  const warn = (msg: string) => notes.push(`⚠ ${msg}`)
  const music = r.stems.music
  const master = r.stems.master
  if (s.target) {
    const stem = r.stems[s.target.stem]
    measured.lufs = stem.lufs
    measured.target = s.target.lufs
    const trim = s.key ? (levels[s.key.kind][s.key.id] ?? 0) : 0
    measured.trimDb = trim
    if (Math.abs(stem.lufs - s.target.lufs) > 1) fail(`${s.target.stem} ${stem.lufs} LUFS, target ${s.target.lufs} ±1`)
    // §14.3: place songs gate their own stem; battle themes gate the master (what can clip, about 5.6 dB under
    // the stems), and so do lobbies, tension layers and stingers, for which the spec sets no peak of their own.
    const peakOn = s.group === 'battle' || s.group === 'lobby' || s.group === 'tension' || s.group === 'stinger' ? master : stem
    if (peakOn.truePeakDb > -1) fail(`${peakOn === master ? 'master ' : ''}true peak ${peakOn.truePeakDb} dBTP (≤ −1)`)
    if (s.group === 'song' && stem.crestDb < 10) fail(`crest ${stem.crestDb} dB (≥ 10)`)
    measured.truePeakDb = stem.truePeakDb
    measured.crestDb = stem.crestDb
  }
  if (s.group === 'song' || s.group === 'battle' || s.group === 'lobby' || s.group === 'tension') {
    const limitMid = s.group === 'song' ? 10 : 14
    const limitHigh = s.group === 'song' ? 1.5 : 2.5
    measured.share2to6k = music.share2to6k
    measured.shareAbove8k = music.shareAbove8k
    if (music.share2to6k > limitMid) warn(`brightness: ${music.share2to6k}% in 2–6 kHz (warn above ${limitMid}%)`)
    if (music.shareAbove8k > limitHigh) warn(`brightness: ${music.shareAbove8k}% above 8 kHz (warn above ${limitHigh}%)`)
    if (music.dropouts > 0) fail(`${music.dropouts} dropout(s) in the music stem`)
  }
  for (const name of ['music', 'ambience', 'sfx', 'ui', 'master'] as const) {
    if (r.stems[name].clicks > 0) fail(`${r.stems[name].clicks} click(s) in the ${name} stem`)
  }
  if (s.group === 'battle') {
    // Relative targets against the music stem's short-term loudness in the 3 s before each event.
    const st = music.shortTerm
    const before = (t: number) => {
      const i = Math.max(0, Math.round(t * 10) - 1)
      const win = st.slice(Math.max(0, i - 30), i + 1).filter((v) => v > -100)
      return win.length ? win.reduce((a, b) => a + b, 0) / win.length : -120
    }
    const sfxM = r.stems.sfx.momentary
    let worstHit = -Infinity
    let worstCrit = -Infinity
    let worstKo = -Infinity
    for (const m of r.marks) {
      const i = Math.round(m.t * 10)
      const peakM = Math.max(...sfxM.slice(i, i + 6))
      const rel = peakM - before(m.t)
      if (m.what.startsWith('hit:')) worstHit = Math.max(worstHit, rel)
      else if (m.what.startsWith('crit:') || m.what === 'special') worstCrit = Math.max(worstCrit, rel)
      else if (m.what === 'ko') worstKo = Math.max(worstKo, rel)
    }
    measured.hitOverMusicLu = round(worstHit)
    measured.critOverMusicLu = round(worstCrit)
    measured.koOverMusicLu = round(worstKo)
    if (worstHit > 4) fail(`an ordinary hit sits ${round(worstHit)} LU over the music (≤ 4)`)
    if (worstCrit > 6) fail(`a crit or Special sits ${round(worstCrit)} LU over the music (≤ 6)`)
    if (worstKo > 9) fail(`the KO sits ${round(worstKo)} LU over the music (≤ 9)`)
    // No pumping: the music stem around an ordinary hit moves by at most 0.5 dB (effects join after the glue).
    let pump = 0
    for (const m of r.marks) {
      if (!m.what.startsWith('hit:')) continue
      const i = Math.round(m.t * 10)
      const a = music.momentary[Math.max(0, i - 2)] ?? -120
      const b = music.momentary[i + 1] ?? -120
      if (a > -100 && b > -100) pump = Math.max(pump, Math.abs(a - b))
    }
    measured.pumpDb = round(pump)
    if (pump > 0.5 + 1.5) warn(`the music moved ${round(pump)} dB around a hit (the music itself varies; the glue sees no effects)`)
    if (master.truePeakDb > -1) fail(`master true peak ${master.truePeakDb} dBTP`)
    measured.masterLufs = master.lufs
  }
  if (s.group === 'musical') {
    // A musical effect plays on the sfx bus; `pause` and a few others sit on the ui bus, so read the louder stem.
    const fxStem = r.stems.ui.momentaryMax > r.stems.sfx.momentaryMax ? r.stems.ui : r.stems.sfx
    measured.momentaryMax = fxStem.momentaryMax
    if (fxStem.momentaryMax > -20 + 3) fail(`short-term max ${fxStem.momentaryMax} LUFS (≤ music + 3 LU = −17)`)
    if (fxStem.truePeakDb > -3) fail(`true peak ${fxStem.truePeakDb} dBTP (≤ −3)`)
  }
  if (s.group === 'ui') {
    measured.momentaryMax = r.stems.ui.momentaryMax
    if (r.stems.ui.momentaryMax > -32) fail(`momentary ${r.stems.ui.momentaryMax} LUFS (≤ −32)`)
  }
  if (s.group === 'battleFx') {
    measured.truePeakDb = r.stems.sfx.truePeakDb
    measured.momentaryMax = r.stems.sfx.momentaryMax
    if (r.stems.sfx.truePeakDb > -3) fail(`true peak ${r.stems.sfx.truePeakDb} dBTP (≤ −3)`)
  }
  if (r.lateEvents > 0) fail(`${r.lateEvents} late event(s)`)
  measured.lateEvents = r.lateEvents
  return { id: s.id, ok, notes, measured }
}

function round(n: number): number {
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : -120
}

/* ---------- the run ---------- */

function killStalePreview(): void {
  if (process.platform !== 'win32') return
  try {
    const lines = execFileSync('netstat', ['-ano'], { encoding: 'utf8' }).split('\n').filter((l) => l.includes(':4173') && l.includes('LISTENING'))
    for (const l of lines) {
      const pid = l.trim().split(/\s+/).pop()
      if (pid && /^\d+$/.test(pid)) execFileSync('taskkill', ['/PID', pid, '/F', '/T'], { stdio: 'ignore' })
    }
  } catch {
    /* nothing listening */
  }
}

async function waitFor(url: string, ms: number): Promise<void> {
  const until = Date.now() + ms
  while (Date.now() < until) {
    try {
      const r = await fetch(url)
      if (r.ok) return
    } catch {
      /* not yet */
    }
    await new Promise((r) => setTimeout(r, 300))
  }
  throw new Error(`preview did not come up at ${url}`)
}

function pcmToWav(r: RenderResult, path: string): void {
  if (!r.pcm) return
  const bytes = Buffer.concat(r.pcm.chunks.map((c) => Buffer.from(c, 'base64')))
  const frames = bytes.length / 2 / r.pcm.channels
  const chans = Array.from({ length: r.pcm.channels }, () => new Float32Array(frames))
  for (let i = 0; i < frames; i++) for (let c = 0; c < r.pcm.channels; c++) chans[c]![i] = bytes.readInt16LE((i * r.pcm.channels + c) * 2) / 32768
  writeFileSync(path, encodeWav(chans, r.pcm.sampleRate, 16))
}

async function main(): Promise<void> {
  const list = specs()
  console.log(`${list.length} items${QUICK ? ' (quick)' : ''}${ONLY ? ` matching ${ONLY}` : ''}`)
  if (!NO_BUILD) {
    console.log('building…')
    execFileSync(process.platform === 'win32' ? 'npm.cmd' : 'npm', ['run', 'build'], { stdio: 'inherit', shell: process.platform === 'win32' })
  }
  killStalePreview()
  let preview: ChildProcess = spawn(process.platform === 'win32' ? 'npx.cmd' : 'npx', ['vite', 'preview', '--port', '4173', '--strictPort'], { stdio: 'ignore', shell: process.platform === 'win32' })
  try {
    try {
      await waitFor(BASE, 60_000)
    } catch {
      // A cold start, or the previous preview was still letting go of the port: once more.
      preview.kill()
      killStalePreview()
      preview = spawn(process.platform === 'win32' ? 'npx.cmd' : 'npx', ['vite', 'preview', '--port', '4173', '--strictPort'], { stdio: 'ignore', shell: process.platform === 'win32' })
      await waitFor(BASE, 60_000)
    }
    const browser = await chromium.launch({ channel: 'chrome', headless: true })
    const errors: string[] = []
    const pages: Page[] = []
    for (let j = 0; j < Math.min(JOBS, list.length); j++) {
      const page: Page = await browser.newPage({ viewport: { width: 412, height: 915 } })
      page.on('pageerror', (e) => errors.push(e.message))
      await page.goto(`${BASE}#lab/sound`)
      await page.waitForFunction(() => (window as unknown as { __audio?: { labReady?: boolean } }).__audio?.labReady === true, undefined, { timeout: 60_000 })
      pages.push(page)
    }
    if (JOBS > 1) console.log(`rendering ${pages.length} at a time`)
    const levels = JSON.parse(readFileSync(LEVELS, 'utf8')) as Levels
    mkdirSync(OUT, { recursive: true })
    const opus = hasLibopus()
    const results: Record<string, RenderResult> = {}
    const verdicts: Verdict[] = []
    const seedOf = (id: string) => {
      let h = 2166136261
      for (let i = 0; i < id.length; i++) h = Math.imul(h ^ id.charCodeAt(i), 16777619)
      return h >>> 0
    }
    const started = Date.now()
    let next = 0
    const worker = async (page: Page) => {
      while (next < list.length) {
        const s = list[next++]!
        const t0 = Date.now()
        const r = (await page.evaluate(([item, seed, pcm]) => (window as unknown as { __audio: { render: (i: unknown, s: number, o: { pcm: boolean }) => Promise<unknown> } }).__audio.render(item, seed, { pcm }), [s.item, seedOf(s.id), REVIEW] as const)) as RenderResult
        results[s.id] = { ...r, pcm: undefined }
        const v = gate(s, r, levels)
        verdicts.push(v)
        console.log(`${v.ok ? 'ok ' : 'FAIL'} ${s.id.padEnd(34)} ${Object.entries(v.measured).map(([k, n]) => `${k}=${n}`).join(' ')}  (${((Date.now() - t0) / 1000).toFixed(1)} s)`)
        for (const n of v.notes) console.log(`      ${n}`)
        if (REVIEW && r.pcm) {
          const wav = join(OUT, `${s.id.replace(/[^\w-]+/g, '_')}.wav`)
          pcmToWav(r, wav)
          encodeReview(wav, wav.replace(/\.wav$/, '.ogg'), opus)
        }
      }
    }
    await Promise.all(pages.map((p) => worker(p)))
    // Back in list order for the report.
    const order = new Map(list.map((s, i) => [s.id, i]))
    verdicts.sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0))
    if (CALIBRATE) {
      let bad = false
      // A key's trim is the mean correction over every item that carries it (a drill cue's five outcomes, the
      // battle theme's layers), so the outcomes must sit within ±1 LU of each other in the recipes themselves.
      const wanted = new Map<string, { key: NonNullable<Spec['key']>; deltas: number[] }>()
      for (const s of list) {
        if (!s.key || !s.target) continue
        const r = results[s.id]!
        const measured = r.stems[s.target.stem].lufs
        if (measured < -100) continue
        const k = `${s.key.kind}/${s.key.id}`
        const entry = wanted.get(k) ?? { key: s.key, deltas: [] }
        entry.deltas.push(s.target.lufs - measured)
        wanted.set(k, entry)
      }
      for (const { key, deltas } of wanted.values()) {
        const current = levels[key.kind][key.id] ?? 0
        const mean = deltas.reduce((a, b) => a + b, 0) / deltas.length
        const next = Math.round((current + mean) * 10) / 10
        if (Math.abs(next) > 6) {
          bad = true
          console.log(`calibrate: ${key.kind}/${key.id} would need ${next} dB; the mix itself is wrong`)
        }
        levels[key.kind][key.id] = next
      }
      if (bad) process.exit(1)
      writeFileSync(LEVELS, JSON.stringify(levels, null, 2) + '\n')
      console.log(`wrote ${LEVELS}; rebuild and run audio:check again to confirm`)
    }
    // Decoded samples vs the manifest.
    const decoded = (await pages[0]!.evaluate(() => (window as unknown as { __audio: { checkSamples: () => Promise<unknown> } }).__audio.checkSamples())) as { file: string; onsetMs: number; lengthMs: number; ok: boolean }[]
    const badDecodes = decoded.filter((d) => !d.ok)
    console.log(`decoded samples: ${decoded.length} checked, ${badDecodes.length} off (onset ±1 ms, length ±20 ms)`)
    for (const d of badDecodes.slice(0, 10)) console.log(`   ${d.file}: onset ${d.onsetMs} ms, length ${d.lengthMs} ms`)
    const failed = verdicts.filter((v) => !v.ok)
    const report = { at: new Date().toISOString(), quick: QUICK, items: verdicts, decoded: { checked: decoded.length, off: badDecodes }, pageErrors: errors, results }
    writeFileSync(join(OUT, 'report.json'), JSON.stringify(report, null, 1))
    if (REVIEW) writeIndex(list, verdicts, results)
    console.log(`${list.length} items, ${failed.length} failed, ${errors.length} page errors, ${((Date.now() - started) / 1000).toFixed(0)} s`)
    for (const e of errors.slice(0, 5)) console.log(`   page error: ${e}`)
    await browser.close()
    if (CHECK && !CALIBRATE && (failed.length > 0 || badDecodes.length > 0 || errors.length > 0)) process.exitCode = 1
  } finally {
    preview.kill()
    killStalePreview()
  }
}

async function writeIndex(list: Spec[], verdicts: Verdict[], results: Record<string, RenderResult>): Promise<void> {
  const baseline = existsSync('tools/audio/baseline-legacy.json') ? (JSON.parse(readFileSync('tools/audio/baseline-legacy.json', 'utf8')) as { tracks: Record<string, Record<string, number>> }) : null
  const roots = manifestRoots()
  const songs: Song[] = []
  for (const load of Object.values(SONG_LOADERS)) songs.push((await load()).default)
  songs.push(...Object.values(STINGERS))
  for (const cue of Object.values(DRILL_CUES)) songs.push(cue.song, ...Object.values(cue.stingers))
  const notesFor = (id: string) => {
    const song = songs.find((s) => s.id === id || s.id === id.split(':')[1])
    if (!song) return ''
    const issues = checkSong(song, { roots, others: songs.filter((s) => s !== song) })
    return `<p class="notes">${song.brief}<br>${passSeconds(song).toFixed(0)} s per pass · ${issues.length ? issues.map((i) => `${i.level === 'error' ? '✗' : '⚠'} ${i.message}`).join('<br>') : '✓ the checker has no notes'}</p>`
  }
  const rows = list
    .map((s) => {
      const v = verdicts.find((x) => x.id === s.id)!
      const r = results[s.id]!
      const file = `${s.id.replace(/[^\w-]+/g, '_')}.ogg`
      const legacy = baseline?.tracks[{ 'ranch-spring': 'ranchSpring', 'ranch-summer': 'ranchSummer', 'ranch-autumn': 'ranchAutumn', 'ranch-winter': 'ranchWinter', town: 'town', cup: 'battle' }[s.id] ?? '']
      return `<section class="${v.ok ? 'ok' : 'fail'}"><h3>${s.id} <small>${v.ok ? 'passes' : 'FAILS'}</small></h3><audio controls preload="none" src="${file}"></audio>
<table><tr><th></th><th>now</th><th>old loop</th></tr>
<tr><td>loudness</td><td>${r.stems.master.lufs} LUFS</td><td>${legacy?.lufs ?? '—'}</td></tr>
<tr><td>true peak</td><td>${r.stems.master.truePeakDb} dBTP</td><td>${legacy?.truePeakDbtp ?? '—'}</td></tr>
<tr><td>crest</td><td>${r.stems.master.crestDb} dB</td><td>${legacy?.crestDb ?? '—'}</td></tr>
<tr><td>2–6 kHz</td><td>${r.stems.master.share2to6k}%</td><td>${legacy?.share2to6k ?? '—'}</td></tr>
<tr><td>above 8 kHz</td><td>${r.stems.master.shareAbove8k}%</td><td>${legacy?.shareAbove8k ?? '—'}</td></tr></table>
${v.notes.length ? `<p>${v.notes.join('<br>')}</p>` : ''}${notesFor(s.id)}</section>`
    })
    .join('\n')
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Wildsong Ranch sound review</title>
<style>body{font:15px/1.4 system-ui,sans-serif;max-width:720px;margin:1rem auto;padding:0 1rem;background:#15191c;color:#e8e4d8}section{border:1px solid #334;border-radius:10px;padding:.6rem .9rem;margin:.7rem 0}section.fail{border-color:#b55}h3{margin:.2rem 0 .4rem}h3 small{font-weight:normal;color:#9a9}table{border-collapse:collapse;font-variant-numeric:tabular-nums}td,th{padding:.1rem .6rem .1rem 0;text-align:left;color:#cbc}audio{width:100%}.notes{color:#aab;font-size:.9em}</style></head>
<body><h1>Sound review</h1><p>Every piece as rendered by the real engine at the default volumes on the Phone speaker preset. The "old loop" column is the chiptune track it replaces (tools/audio/baseline-legacy.json). PROGRESS.md says what to listen for.</p>${rows}</body></html>`
  writeFileSync(join(OUT, 'index.html'), html)
  console.log(`wrote ${OUT}/index.html`)
}

await main()
