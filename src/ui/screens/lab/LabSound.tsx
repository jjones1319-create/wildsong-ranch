import { useEffect, useRef, useState } from 'preact/hooks'
import { SONG_IDS, type SongId } from '../../../audio/director.ts'
import type { Engine } from '../../../audio/engine/index.ts'
import { DEFAULT_KEY } from '../../../audio/engine/sfx.ts'
import { checkSong, type CheckIssue } from '../../../audio/music/checker.ts'
import { CALLING_CARD_IDS, MUSICAL_EFFECT_IDS } from '../../../audio/music/effects.ts'
import { passSeconds, type Arrangement, type Song } from '../../../audio/music/song.ts'
import { STINGER_IDS, STINGERS } from '../../../audio/music/stingers.ts'
import { audioReady, getEngine, getRuntime, loadSongForLab, playSfx, unlockAudio } from '../../../audio/player.ts'
import { BED_IDS, bedLayers, CROWD_SIZES, type BedId, type CrowdReaction, type CrowdSize } from '../../../audio/recipes/ambience.ts'
import { DRILL_CUES } from '../../../audio/recipes/drills.ts'
import { EVENT_ARRANGEMENT_BY_ID, EVENT_ARRANGEMENTS, SEASON_PALETTES, THEME_IDS, TRIAL_ARRANGEMENTS, type EventArrangement, type ThemeId } from '../../../audio/recipes/events.ts'
import type { SongRequest } from '../../../audio/director.ts'
import { eventName } from '../../../core/tournament.ts'
import { battleSfx, UI_SFX_IDS, WORLD_SFX_IDS, type Strength } from '../../../audio/recipes/sfx.ts'
import { AUDIO } from '../../../data/tuning.ts'
import { DRILL_BY_ID } from '../../../data/drills.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { fill } from '../../../data/text/format.ts'
import { DRILL_IDS, ELEMENTS, JOURNEY_SITE_IDS, LISTENING_SETTINGS, SEASONS, WEATHERS, type DrillId, type Element, type JourneySiteId, type Season, type Weather } from '../../../data/types.ts'
import type { FxEventKind } from '../../../fx/bus.ts'
import type { DrillOutcome } from '../../../core/training.ts'
import { Chips, Segmented, Select, Toggle, TopBar } from '../../components/Controls.tsx'
import { settings, showToast, updateSettings } from '../../store/appStore.ts'
import { checkDecodedSamples, renderItem } from './soundRender.ts'

const t = UI_TEXT.soundLab
const NOTES_KEY = 'wildsong/soundNotes'
type Tab = 'music' | 'ambience' | 'effects' | 'moments' | 'mix'
type Notes = Record<string, { v: 1 | -1; note: string }>
const FX_KINDS: FxEventKind[] = ['fire', 'travel', 'hit', 'crit', 'miss', 'ko', 'special', 'push', 'dash', 'distract', 'wither', 'heal']
const OUTCOMES: DrillOutcome[] = ['Great', 'Success', 'Cheat', 'Fail', 'Slacked']
const REACTIONS: CrowdReaction[] = ['cheer', 'ooh', 'murmur', 'ko', 'applause', 'clap']

function readNotes(): Notes {
  try {
    return JSON.parse(localStorage.getItem(NOTES_KEY) ?? '{}') as Notes
  } catch {
    return {}
  }
}

function writeNotes(n: Notes): void {
  try {
    localStorage.setItem(NOTES_KEY, JSON.stringify(n))
  } catch {
    /* private mode */
  }
}

/** 👍 / 👎 and a short note, kept in this browser only. */
function NoteRow({ id, notes, onChange }: { id: string; notes: Notes; onChange: (n: Notes) => void }) {
  const cur = notes[id]
  const set = (v: 1 | -1) => onChange({ ...notes, [id]: { v, note: cur?.note ?? '' } })
  return (
    <div class="sndlab__notes">
      <button type="button" class={`btn btn--small sndlab__thumb ${cur?.v === 1 ? 'sndlab__thumb--on' : ''}`} data-silent aria-label={`${t.thumbsUp}: ${id}`} onClick={() => set(1)}>
        👍
      </button>
      <button type="button" class={`btn btn--small sndlab__thumb ${cur?.v === -1 ? 'sndlab__thumb--on' : ''}`} data-silent aria-label={`${t.thumbsDown}: ${id}`} onClick={() => set(-1)}>
        👎
      </button>
      <input class="sndlab__note" type="text" placeholder={t.notePlaceholder} value={cur?.note ?? ''} aria-label={`${t.notes}: ${id}`} onInput={(e) => onChange({ ...notes, [id]: { v: cur?.v ?? 1, note: (e.currentTarget as HTMLInputElement).value } })} />
    </div>
  )
}

export function LabSoundScreen() {
  const [tab, setTab] = useState<Tab>('music')
  const [ready, setReady] = useState(audioReady())
  const [notes, setNotes] = useState<Notes>(() => readNotes())
  const [debug, setDebug] = useState<ReturnType<Engine['debug']> | null>(null)
  const engine = getEngine()

  useEffect(() => {
    // Playwright and the render tool drive the Lab through window.__audio.
    const w = window as Window & { __audio?: Record<string, unknown> }
    // Assign onto the engine's view rather than spreading it: spreading would copy its `state` getter as a frozen value.
    w.__audio = Object.assign(w.__audio ?? {}, { render: renderItem, checkSamples: checkDecodedSamples, labReady: true })
    const timer = setInterval(() => {
      if (!ready && audioReady()) setReady(true)
      const e = getEngine()
      if (e) setDebug(e.debug())
    }, 250)
    return () => {
      clearInterval(timer)
      const e = getEngine()
      e?.music.stop(0.5)
      e?.ambience.setBed(null, 0.5)
      e?.ambience.setCrowd('none')
      if (w.__audio) w.__audio.labReady = false
    }
  }, [])

  const updateNotes = (n: Notes) => {
    setNotes(n)
    writeNotes(n)
  }

  const copyNotes = async () => {
    const lines = Object.entries(notes).map(([id, v]) => `${id} ${v.v === 1 ? '👍' : '👎'}${v.note ? ` "${v.note}"` : ''}`)
    if (lines.length === 0) {
      showToast(t.nothingToCopy)
      return
    }
    try {
      await navigator.clipboard.writeText(lines.join('\n'))
      showToast(t.copied)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = lines.join('\n')
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      ta.remove()
      showToast(t.copied)
    }
  }

  const tabs = (['music', 'ambience', 'effects', 'moments', 'mix'] as Tab[]).map((v) => ({ value: v, label: t.tabs[v] }))

  return (
    <main class="screen sndlab">
      <TopBar title={t.title} />
      <p class="muted small">{t.hint}</p>
      {!ready && (
        <section class="card">
          <p>{t.locked}</p>
          <button type="button" class="btn btn--primary" onClick={() => void unlockAudio().then(() => setReady(audioReady()))}>
            🔊 {t.play}
          </button>
        </section>
      )}
      <Segmented options={tabs} value={tab} onChange={setTab} label={t.title} />
      {engine && tab === 'music' && <MusicTab engine={engine} notes={notes} onNotes={updateNotes} debug={debug} />}
      {engine && tab === 'ambience' && <AmbienceTab engine={engine} notes={notes} onNotes={updateNotes} />}
      {engine && tab === 'effects' && <EffectsTab engine={engine} notes={notes} onNotes={updateNotes} />}
      {engine && tab === 'moments' && <MomentsTab engine={engine} notes={notes} onNotes={updateNotes} />}
      {engine && tab === 'mix' && <MixTab engine={engine} debug={debug} />}
      <section class="card">
        <button type="button" class="btn btn--primary" data-silent onClick={() => void copyNotes()}>
          📋 {t.copyNotes}
        </button>
      </section>
    </main>
  )
}

/* ---------- Music ---------- */

interface MusicItem {
  id: string
  label: string
  group: keyof typeof t.groups
  song?: SongId
  arrangement?: string
  stinger?: (typeof STINGER_IDS)[number]
  drill?: keyof typeof DRILL_CUES
  effect?: string
  /** An event row (the event picker, the Summit Qualifier, a Trial site): its lead, kit, colour, key and tempo. */
  row?: EventArrangement
}

const THEME_LABELS: Record<ThemeId, string> = {
  cup: 'Cup (every regular cup, season chips below)',
  open: 'New Year Open',
  ascension: 'Ascensions',
  'crown-dawn': 'Crown of Dawn',
  'crown-tides': 'Crown of Tides',
  'crown-embers': 'Crown of Embers',
  'crown-frost': 'Crown of Frost',
  legend: 'The Wildsong Legend',
  masquerade: 'Masquerade Cup',
  rival: 'Rival Showdown (and Corin)',
  summit: 'Vale–Coast Summit',
  rally: "Hero's Rally",
  'rally-rogue': "Rogue's Rally",
  sprout: 'Sprout Cup',
  elders: "Elders' Cup",
  trial: 'Journey Trial (site chips below)',
  practice: 'Practice (the Lab)',
}

/** The director's request for an event row, so the Lab plays it exactly as the game would. */
function requestFor(row: EventArrangement, layers: readonly string[]): SongRequest {
  return { id: row.theme, arrangement: row.arrangement, layers, stem: null, transpose: row.transpose, tempoNudge: row.tempoNudge, kit: row.kit, lead: row.lead, leadArt: row.leadArt, colour: row.colour, musicSend: row.musicSend, crossfadeSec: 0.5 }
}

function describeRow(row: EventArrangement, bpm: number): string {
  return fill(t.eventRow, { theme: row.theme, lead: row.lead, kit: row.kit, colour: row.colour, transpose: row.transpose > 0 ? `+${row.transpose}` : String(row.transpose), tempo: bpm + row.tempoNudge })
}

const MUSIC_ITEMS: MusicItem[] = [
  { id: 'wildsong', label: 'Wildsong (title)', group: 'places', song: 'wildsong' },
  { id: 'wildsong:lobby', label: 'Wildsong, lobby', group: 'places', song: 'wildsong', arrangement: 'lobby' },
  { id: 'wildsong:credits', label: 'Wildsong, credits', group: 'places', song: 'wildsong', arrangement: 'credits' },
  { id: 'ranch-spring', label: 'Ranch, spring', group: 'ranch', song: 'ranch-spring' },
  { id: 'ranch-summer', label: 'Ranch, summer', group: 'ranch', song: 'ranch-summer' },
  { id: 'ranch-autumn', label: 'Ranch, autumn', group: 'ranch', song: 'ranch-autumn' },
  { id: 'ranch-winter', label: 'Ranch, winter', group: 'ranch', song: 'ranch-winter' },
  { id: 'town', label: 'Town', group: 'town', song: 'town' },
  ...THEME_IDS.map((id): MusicItem => ({ id, label: THEME_LABELS[id], group: 'events', song: id })),
  { id: 'summit:qualifier', label: 'Summit Qualifier', group: 'events', song: 'summit', row: EVENT_ARRANGEMENT_BY_ID['summit-qualifier'] },
  { id: 'drill-waterfall', label: 'Waterfall Stand bed', group: 'drills', drill: 'waterfall-stand' },
  { id: 'drill-generic', label: 'Generic drill bed', group: 'drills', drill: 'generic' },
  ...STINGER_IDS.map((id): MusicItem => ({ id, label: id, group: 'stingers', stinger: id })),
  ...MUSICAL_EFFECT_IDS.map((id): MusicItem => ({ id, label: id, group: 'musical', effect: id })),
  ...CALLING_CARD_IDS.map((id): MusicItem => ({ id, label: id.replace('card-', ''), group: 'cards', effect: id })),
]

function MusicTab({ engine, notes, onNotes, debug }: { engine: Engine; notes: Notes; onNotes: (n: Notes) => void; debug: ReturnType<Engine['debug']> | null }) {
  const [current, setCurrent] = useState<MusicItem | null>(null)
  const [song, setSong] = useState<Song | null>(null)
  const [layers, setLayers] = useState<string>('main')
  const [stem, setStem] = useState<string>('town')
  const [weather, setWeather] = useState<Weather>('Sunny')
  const [season, setSeason] = useState<Season>('Spring')
  const [site, setSite] = useState<JourneySiteId>('iron-quarry')
  const [eventId, setEventId] = useState<string>(EVENT_ARRANGEMENTS[0]!.event)
  const [issues, setIssues] = useState<CheckIssue[]>([])
  const [loading, setLoading] = useState(false)
  const playing = debug?.song ?? null

  const play = async (item: MusicItem) => {
    setCurrent(item)
    if (item.stinger) {
      engine.music.interrupt(STINGERS[item.stinger], { transpose: 0, fadeInAfterSec: 1 })
      return
    }
    if (item.effect) {
      playSfx(item.effect as never)
      return
    }
    if (item.drill) {
      const recipe = DRILL_CUES[item.drill]
      engine.ambience.setBed(recipe.bed, 0.5)
      engine.music.play(recipe.song, { fadeInSec: 0.3, arrangement: { gainDb: recipe.musicGainDb } })
      setSong(recipe.song)
      setIssues(checkSong(recipe.song, { roots: engine.bank.roots() }))
      return
    }
    if (!item.song) return
    setLoading(true)
    const s = await loadSongForLab(item.song)
    setLoading(false)
    setSong(s)
    setIssues(checkSong(s, { roots: engine.bank.roots() }))
    startSong(s, item, layers, stem, weather, season, site)
  }

  /** The row a battle theme plays with: the item's own (the event picker), a Trial site's, or the cup in its season. */
  const rowFor = (s: Song, item: MusicItem, se: Season, si: JourneySiteId): EventArrangement | null => {
    if (item.row) return item.row
    if (s.id === 'trial') return TRIAL_ARRANGEMENTS[si]
    if (s.id === 'cup') {
      const p = SEASON_PALETTES[se]
      return { ...EVENT_ARRANGEMENTS.find((r) => r.theme === 'cup')!, palette: se, lead: p.leads[0], kit: p.kit, colour: p.colour, transpose: 0, tempoNudge: 0, musicSend: null }
    }
    return null
  }

  const startSong = (s: Song, item: MusicItem, ly: string, st: string, w: Weather, se: Season, si: JourneySiteId) => {
    const base: Arrangement | null = item.arrangement ? (s.arrangements?.[item.arrangement] ?? null) : null
    const battle = s.kind === 'battle'
    const layerSet = battle ? (ly === 'lobby' ? ['lobby'] : ly === 'base' ? ['base'] : ly === 'drive' ? ['base', 'drive'] : ['base', 'drive', 'tension']) : ['main']
    const row = battle ? rowFor(s, item, se, si) : null
    const runtime = getRuntime()
    // Battle themes play through the game's own request path (the runtime's arrangement), so the Lab sounds like the cup.
    const arrangement: Arrangement | null = battle && runtime ? runtime.arrangementFor(s, row ? requestFor(row, layerSet) : { id: s.id as SongId, arrangement: null, layers: layerSet, stem: null, transpose: 0, tempoNudge: 0, kit: null, lead: null, leadArt: null, colour: null, musicSend: null, crossfadeSec: 0.5 }) : base
    engine.music.play(s, { layers: layerSet, stem: s.stems ? st : null, weather: w, arrangement, transpose: row?.transpose ?? 0, fadeInSec: 0.3, fadeOutSec: 0.5, startIndex: battle && ly !== 'lobby' ? Math.max(0, s.order.indexOf('intro')) : 0 })
  }

  const info = song && debug && playing === song.id ? fill(t.info, { key: song.tune.key.text, tempo: song.tune.tempoText, meter: `${song.meter[0]}/${song.meter[1]}`, length: passSeconds(song).toFixed(0), section: debug.section }) : null
  const groups = [...new Set(MUSIC_ITEMS.map((i) => i.group))]
  const isBattle = song?.kind === 'battle'

  return (
    <>
      {current && song && (
        <section class="card">
          <p class="field__label">{current.label}</p>
          {loading && <p class="muted small">{t.loading}</p>}
          {info && <p class="sndlab__info small">{info}</p>}
          <div class="row">
            <button type="button" class="btn btn--small" data-silent onClick={() => void play(current)}>
              ▶ {t.play}
            </button>
            <button type="button" class="btn btn--small" data-silent onClick={() => engine.music.stop(0.5)}>
              ■ {t.stop}
            </button>
            <button type="button" class="btn btn--small" data-silent onClick={() => engine.music.nextSection()}>
              ⏭ {t.nextSection}
            </button>
          </div>
          {isBattle && (
            <>
              <p class="field__label small">{t.layers}</p>
              <Chips
                options={['lobby', 'base', 'drive', 'tension'].map((l) => ({ value: l, label: l }))}
                value={layers}
                onChange={(v) => {
                  setLayers(v)
                  if (playing === song.id && v !== 'lobby' && layers !== 'lobby') engine.music.setLayers(v === 'base' ? ['base'] : v === 'drive' ? ['base', 'drive'] : ['base', 'drive', 'tension'])
                  else startSong(song, current, v, stem, weather, season, site)
                }}
                label={t.layers}
              />
              {song.id === 'cup' && !current.row && (
                <>
                  <p class="field__label small">{t.season}</p>
                  <Chips
                    options={SEASONS.map((s) => ({ value: s, label: s }))}
                    value={season}
                    onChange={(v) => {
                      setSeason(v)
                      startSong(song, current, layers, stem, weather, v, site)
                    }}
                    label={t.season}
                  />
                </>
              )}
              {song.id === 'trial' && !current.row && (
                <>
                  <p class="field__label small">{t.site}</p>
                  <Chips
                    options={JOURNEY_SITE_IDS.map((x) => ({ value: x, label: x }))}
                    value={site}
                    onChange={(v) => {
                      setSite(v)
                      startSong(song, current, layers, stem, weather, season, v)
                    }}
                    label={t.site}
                  />
                </>
              )}
              {current.row && <p class="sndlab__info small">{describeRow(current.row, song.bpm)}</p>}
            </>
          )}
          {song.stems && (
            <>
              <p class="field__label small">{t.stems}</p>
              <Chips
                options={Object.keys(song.stems).map((s) => ({ value: s, label: s }))}
                value={stem}
                onChange={(v) => {
                  setStem(v)
                  if (playing === song.id) engine.music.setStem(v)
                  else startSong(song, current, layers, v, weather, season, site)
                }}
                label={t.stems}
              />
            </>
          )}
          {song.kind === 'ranch' && (
            <>
              <p class="field__label small">{t.weather}</p>
              <Chips
                options={WEATHERS.map((w) => ({ value: w, label: w }))}
                value={weather}
                onChange={(v) => {
                  setWeather(v)
                  engine.ambience.setWeather(v)
                  if (playing === song.id) engine.music.setWeather(v)
                  else startSong(song, current, layers, stem, v, season, site)
                }}
                label={t.weather}
              />
            </>
          )}
          <p class="field__label small">{t.warnings}</p>
          {issues.length === 0 ? (
            <p class="muted small">{t.noWarnings}</p>
          ) : (
            <ul class="sndlab__warn muted">
              {issues.map((i, k) => (
                <li key={k}>
                  {i.level === 'error' ? '✗' : '⚠'} {i.message}
                </li>
              ))}
            </ul>
          )}
          <NoteRow id={current.id} notes={notes} onChange={onNotes} />
        </section>
      )}
      {groups.map((g) => (
        <section class="card" key={g}>
          <p class="field__label">{t.groups[g]}</p>
          {MUSIC_ITEMS.filter((i) => i.group === g).map((item) => (
            <div class="sndlab__item" key={item.id}>
              <button type="button" class={`btn btn--small ${current?.id === item.id ? 'btn--on' : ''}`} data-silent onClick={() => void play(item)}>
                ▶
              </button>
              <span class="sndlab__item-name">{item.label}</span>
              <span class="muted small">{notes[item.id]?.v === 1 ? '👍' : notes[item.id]?.v === -1 ? '👎' : ''}</span>
            </div>
          ))}
        </section>
      ))}
      <section class="card">
        <p class="field__label">{t.eventPicker}</p>
        <Select
          label={t.eventPick}
          value={eventId}
          options={EVENT_ARRANGEMENTS.map((r) => ({ value: r.event, label: `${eventName(r.event)} (${r.theme})` }))}
          onChange={(v) => setEventId(v)}
        />
        <div class="row">
          <button
            type="button"
            class="btn btn--small"
            data-silent
            onClick={() => {
              const row = EVENT_ARRANGEMENT_BY_ID[eventId]!
              void play({ id: `event:${eventId}`, label: eventName(eventId), group: 'events', song: row.theme, row })
            }}
          >
            ▶ {t.play}
          </button>
        </div>
      </section>
    </>
  )
}

/* ---------- Ambience ---------- */

function AmbienceTab({ engine, notes, onNotes }: { engine: Engine; notes: Notes; onNotes: (n: Notes) => void }) {
  const [bed, setBed] = useState<BedId>('meadow')
  const [weather, setWeather] = useState<Weather>('Sunny')
  const [crowd, setCrowd] = useState<CrowdSize>('none')
  const [trims, setTrims] = useState<Record<string, number>>({})
  const start = (b: BedId, w: Weather, c: CrowdSize) => {
    engine.ambience.setWeather(w)
    engine.ambience.setBed(b, 1)
    engine.ambience.setCrowd(c)
  }
  return (
    <>
      <section class="card">
        <p class="field__label">{t.groups.beds}</p>
        <Chips
          options={BED_IDS.map((b) => ({ value: b, label: b }))}
          value={bed}
          onChange={(v) => {
            setBed(v)
            start(v, weather, crowd)
          }}
          label={t.groups.beds}
        />
        <p class="field__label small">{t.groups.weather}</p>
        <Chips
          options={WEATHERS.map((w) => ({ value: w, label: w }))}
          value={weather}
          onChange={(v) => {
            setWeather(v)
            start(bed, v, crowd)
          }}
          label={t.groups.weather}
        />
        <p class="field__label small">{t.crowdSize}</p>
        <Chips
          options={CROWD_SIZES.map((c) => ({ value: c, label: c }))}
          value={crowd}
          onChange={(v) => {
            setCrowd(v)
            start(bed, weather, v)
          }}
          label={t.crowdSize}
        />
        <div class="row">
          <button type="button" class="btn btn--small" data-silent onClick={() => start(bed, weather, crowd)}>
            ▶ {t.play}
          </button>
          <button type="button" class="btn btn--small" data-silent onClick={() => {
            engine.ambience.setBed(null, 1)
            engine.ambience.setCrowd('none')
          }}>
            ■ {t.stop}
          </button>
        </div>
        <NoteRow id={`bed:${bed}:${weather}`} notes={notes} onChange={onNotes} />
      </section>
      <section class="card">
        <p class="field__label">{t.layerSliders}</p>
        {bedLayers(bed).map((l) => {
          const key = `${bed}/${l.id}`
          const v = trims[key] ?? 0
          return (
            <label class="sndlab__slider" key={key}>
              <span class="small">{l.id}</span>
              <input
                class="range"
                type="range"
                min={-18}
                max={12}
                step={1}
                value={v}
                aria-label={l.id}
                onInput={(e) => {
                  const db = Number((e.currentTarget as HTMLInputElement).value)
                  setTrims({ ...trims, [key]: db })
                  engine.ambience.setLayerTrim(bed, l.id, db)
                }}
              />
              <span class="small muted">{v > 0 ? `+${v}` : v} dB</span>
            </label>
          )
        })}
      </section>
    </>
  )
}

/* ---------- Effects ---------- */

function EffectsTab({ engine, notes, onNotes }: { engine: Engine; notes: Notes; onNotes: (n: Notes) => void }) {
  const [element, setElement] = useState<Element>('Fire')
  const [moment, setMoment] = useState<FxEventKind>('hit')
  const [strength, setStrength] = useState<Strength>('medium')
  const [pan, setPan] = useState(0)
  const [clap, setClap] = useState(false)
  const [crowd, setCrowd] = useState<CrowdSize>('small')
  const fire = () => {
    const def = battleSfx(moment, element, strength, moment === 'crit')
    engine.sfx.play(`${moment}:${element}`, def, { pan, key: engine.music.key() ?? DEFAULT_KEY })
    if (moment === 'special') engine.graph.duck(AUDIO.duck.db, AUDIO.duck.sec)
  }
  return (
    <>
      <section class="card">
        <p class="field__label">{t.groups.ui}</p>
        <div class="sndlab__grid">
          {UI_SFX_IDS.map((id) => (
            <button type="button" class="btn" key={id} data-sound={id} onClick={() => undefined}>
              {id}
            </button>
          ))}
        </div>
        <NoteRow id="ui-sounds" notes={notes} onChange={onNotes} />
      </section>
      <section class="card">
        <p class="field__label">{t.groups.world}</p>
        <div class="sndlab__grid">
          {WORLD_SFX_IDS.map((id) => (
            <button type="button" class="btn" key={id} data-silent onClick={() => playSfx(id)}>
              {id}
            </button>
          ))}
        </div>
        <NoteRow id="world-sounds" notes={notes} onChange={onNotes} />
      </section>
      <section class="card">
        <p class="field__label">{t.groups.battleFx}</p>
        <p class="field__label small">{t.element}</p>
        <Chips options={ELEMENTS.map((e) => ({ value: e, label: e }))} value={element} onChange={setElement} label={t.element} />
        <p class="field__label small">{t.moment}</p>
        <Chips options={FX_KINDS.map((k) => ({ value: k, label: k }))} value={moment} onChange={setMoment} label={t.moment} />
        <p class="field__label small">{t.strength}</p>
        <Segmented options={(['light', 'medium', 'heavy'] as Strength[]).map((s) => ({ value: s, label: s }))} value={strength} onChange={setStrength} label={t.strength} />
        <label class="sndlab__slider">
          <span class="small">{t.pan}</span>
          <input class="range" type="range" min={-0.6} max={0.6} step={0.1} value={pan} aria-label={t.pan} onInput={(e) => setPan(Number((e.currentTarget as HTMLInputElement).value))} />
          <span class="small muted">{pan.toFixed(1)}</span>
        </label>
        <button type="button" class="btn btn--primary" data-silent onClick={fire}>
          💥 {t.fire}
        </button>
        <NoteRow id={`battle:${element}:${moment}:${strength}`} notes={notes} onChange={onNotes} />
      </section>
      <section class="card">
        <p class="field__label">{t.groups.crowds}</p>
        <Chips
          options={CROWD_SIZES.filter((c) => c !== 'none').map((c) => ({ value: c, label: c }))}
          value={crowd}
          onChange={(v) => {
            setCrowd(v)
            engine.ambience.setCrowd(v)
          }}
          label={t.crowdSize}
        />
        <div class="sndlab__grid">
          {REACTIONS.map((r) => (
            <button type="button" class="btn" key={r} data-silent onClick={() => {
              engine.ambience.setCrowd(crowd)
              engine.ambience.react(r)
            }}>
              {r}
            </button>
          ))}
        </div>
        <Toggle
          label={t.clapAlong}
          checked={clap}
          onChange={(v) => {
            setClap(v)
            engine.ambience.setCrowd(crowd)
            getRuntime()?.setClapAlong(engine, v)
          }}
        />
        <NoteRow id={`crowd:${crowd}`} notes={notes} onChange={onNotes} />
      </section>
    </>
  )
}

/* ---------- Moments ---------- */

function MomentsTab({ engine, notes, onNotes }: { engine: Engine; notes: Notes; onNotes: (n: Notes) => void }) {
  const [drill, setDrill] = useState<DrillId>('waterfall-stand')
  const [outcome, setOutcome] = useState<DrillOutcome>('Success')
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const run = () => {
    const rt = getRuntime()
    if (!rt) return
    if (timer.current) clearTimeout(timer.current)
    rt.startDrillCue(engine, drill, outcome, { vignetteMs: 2200 })
    timer.current = setTimeout(() => rt.endDrillCue(engine), 5500)
  }
  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current)
  }, [])
  return (
    <>
      <section class="card">
        <p class="field__label">{t.drillDemo}</p>
        <p class="field__label small">{t.drill}</p>
        <Chips options={DRILL_IDS.map((d) => ({ value: d, label: DRILL_BY_ID[d].name }))} value={drill} onChange={setDrill} label={t.drill} />
        <p class="field__label small">{t.outcome}</p>
        <Chips options={OUTCOMES.map((o) => ({ value: o, label: o }))} value={outcome} onChange={setOutcome} label={t.outcome} />
        <button type="button" class="btn btn--primary" data-silent onClick={run}>
          ▶ {t.runCue}
        </button>
        <NoteRow id={`drill:${drill}:${outcome}`} notes={notes} onChange={onNotes} />
      </section>
      <section class="card">
        <p class="field__label">{t.monsterSong}</p>
        <p class="muted small">{t.comingS3}</p>
      </section>
    </>
  )
}

/* ---------- Mix ---------- */

function MixTab({ engine, debug }: { engine: Engine; debug: ReturnType<Engine['debug']> | null }) {
  const s = settings.value
  const [demo, setDemo] = useState(false)
  const demoTag = useRef<string | null>(null)
  const battleDemo = async () => {
    const song = await loadSongForLab('cup')
    const now = engine.ctx.currentTime
    const key = engine.music.key() ?? DEFAULT_KEY
    engine.ambience.setBed('arena', 0.5)
    engine.ambience.setCrowd('small')
    engine.music.play(song, { layers: ['base'], weather: 'Sunny', fadeInSec: 0.05, startIndex: Math.max(0, song.order.indexOf('intro')) })
    const tag = `demo-${now}`
    demoTag.current = tag
    engine.scheduler.add(now + 4, () => engine.music.setLayers(['base', 'drive']), tag)
    const elements: Element[] = ['Physical', 'Fire', 'Water', 'Earth', 'Wind', 'Ice', 'Nature', 'Light', 'Dark', 'Lightning', 'Sound']
    let n = 0
    for (let dt = 2; dt < 57; dt += 1.2) {
      const element = elements[n % elements.length]!
      const kind: FxEventKind = n % 7 === 6 ? 'miss' : n % 5 === 4 ? 'crit' : 'hit'
      const strength: Strength = n % 3 === 0 ? 'light' : n % 3 === 1 ? 'medium' : 'heavy'
      engine.scheduler.add(now + dt - 0.4, (when) => engine.sfx.play(`fire:${element}`, battleSfx('fire', element, strength), { at: when, key, pan: -0.3 }), tag)
      engine.scheduler.add(now + dt, (when) => {
        engine.sfx.play(`${kind}:${element}`, battleSfx(kind, element, strength, kind === 'crit'), { at: when, key, pan: 0.3 })
        if (kind === 'crit' || strength === 'heavy') engine.ambience.react('cheer', when)
        if (kind === 'miss') engine.ambience.react('ooh', when)
      }, tag)
      n++
    }
    engine.scheduler.add(now + 20, (when) => {
      engine.sfx.play('special:Light', battleSfx('special', 'Light', 'heavy'), { at: when, key })
      engine.graph.duck(AUDIO.duck.db, AUDIO.duck.sec)
    }, tag)
    engine.scheduler.add(now + 45, () => engine.music.setLayers(['base', 'drive', 'tension']), tag)
    engine.scheduler.add(now + 58, (when) => {
      engine.sfx.play('ko:Physical', battleSfx('ko', 'Physical', 'heavy'), { at: when, key })
      engine.music.cut(0.15)
      engine.ambience.react('ko', when)
    }, tag)
    engine.scheduler.add(now + 59, () => {
      engine.music.interrupt(STINGERS.matchWin, { transpose: 4 })
      setDemo(false)
    }, tag)
    setDemo(true)
  }
  const stopDemo = () => {
    if (demoTag.current) engine.scheduler.cancel(demoTag.current)
    engine.music.stop(0.5)
    engine.ambience.setBed(null, 0.5)
    engine.ambience.setCrowd('none')
    setDemo(false)
  }
  const meters = debug?.meters ?? {}
  return (
    <>
      <section class="card">
        <p class="field__label">{t.meters}</p>
        <table class="sndlab__meters">
          <thead>
            <tr>
              <th>bus</th>
              <th>peak dB</th>
              <th>rms dB</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {Object.entries(meters).map(([name, m]) => (
              <tr key={name}>
                <td>{name}</td>
                <td>{Number.isFinite(m.peakDb) ? m.peakDb.toFixed(1) : '—'}</td>
                <td>{Number.isFinite(m.rmsDb) ? m.rmsDb.toFixed(1) : '—'}</td>
                <td style={{ width: '30%' }}>
                  <div class="sndlab__bar">
                    <i style={{ width: `${Math.max(0, Math.min(100, (m.rmsDb + 60) * (100 / 60)))}%` }} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {debug && (
          <p class="small muted sndlab__info">
            {t.voices}: music {debug.voices.music} · ambience {debug.voices.ambience} · effects {debug.voices.sfx} · {t.lateEvents}: {debug.lateEvents} · glue {debug.glueReductionDb} dB · filter {debug.musicFilterHz} Hz · duck {debug.duckDb} dB
          </p>
        )}
        {debug && (
          <p class="small muted">
            {t.packs}: {debug.packs.map((p) => `${p.pack} ${p.state} (${p.decodeMs} ms)`).join(' · ') || '—'}
          </p>
        )}
      </section>
      <section class="card">
        <p class="field__label small">{t.listening}</p>
        <Segmented options={LISTENING_SETTINGS.map((l) => ({ value: l, label: l === 'speaker' ? UI_TEXT.settings.listeningSpeaker : UI_TEXT.settings.listeningHeadphones }))} value={s.listening} onChange={(v) => void updateSettings({ listening: v })} label={t.listening} />
        <Toggle label={t.mono} checked={s.monoAudio} onChange={(v) => void updateSettings({ monoAudio: v })} />
        {demo ? (
          <button type="button" class="btn" data-silent onClick={stopDemo}>
            ■ {t.battleDemoRunning}
          </button>
        ) : (
          <button type="button" class="btn btn--primary" data-silent onClick={() => void battleDemo()}>
            ⚔ {t.battleDemo}
          </button>
        )}
      </section>
    </>
  )
}

export { SONG_IDS }
