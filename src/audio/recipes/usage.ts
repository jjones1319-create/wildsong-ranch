/**
 * SOUND_UPGRADE §5.2: the usage graph that decides the packs. `buildUsage()` walks every song, stinger,
 * musical effect, drill cue, bed and effect recipe of this stage and records which context uses which
 * instrument; `packOf()` then puts an instrument in `core` when the ranch, the town, the UI, the drills,
 * the world effects or the battle effects use it, in `events` when only event themes and their stingers do,
 * and in `places` otherwise. Tools and tests import this; the runtime reads the result from the manifest.
 */
import { ELEMENTS } from '../../data/types.ts'
import { CALLING_CARDS, MUSICAL_EFFECTS } from '../music/effects.ts'
import type { Song } from '../music/song.ts'
import { STINGERS } from '../music/stingers.ts'
import ascension from '../music/songs/ascension.ts'
import crownDawn from '../music/songs/crown-dawn.ts'
import crownEmbers from '../music/songs/crown-embers.ts'
import crownFrost from '../music/songs/crown-frost.ts'
import crownTides from '../music/songs/crown-tides.ts'
import cup from '../music/songs/cup.ts'
import elders from '../music/songs/elders.ts'
import legend from '../music/songs/legend.ts'
import masquerade from '../music/songs/masquerade.ts'
import open from '../music/songs/open.ts'
import practice from '../music/songs/practice.ts'
import rally from '../music/songs/rally.ts'
import rallyRogue from '../music/songs/rally-rogue.ts'
import rival from '../music/songs/rival.ts'
import sprout from '../music/songs/sprout.ts'
import summit from '../music/songs/summit.ts'
import trial from '../music/songs/trial.ts'
import ranchAutumn from '../music/songs/ranch-autumn.ts'
import ranchSpring from '../music/songs/ranch-spring.ts'
import ranchSummer from '../music/songs/ranch-summer.ts'
import ranchWinter from '../music/songs/ranch-winter.ts'
import town from '../music/songs/town.ts'
import wildsong from '../music/songs/wildsong.ts'
import { BED_IDS, bedLayers, CROWDS, WEATHER_OVERLAYS, type BedLayer } from './ambience.ts'
import { DRILL_CUES } from './drills.ts'
import { EVENT_ARRANGEMENTS, SEASON_PALETTES, THEME_IDS, TRIAL_ARRANGEMENTS } from './events.ts'
import { INSTRUMENTS, type InstrumentId } from './instruments.ts'
import { KITS } from './kits.ts'
import { setUsage, type Usage, type UsageContext } from './packs.ts'
import { battleSfx, UI_SFX, WORLD_SFX, type SfxDef } from './sfx.ts'

const SONG_CONTEXT: Record<string, UsageContext> = {
  wildsong: 'place',
  'ranch-spring': 'ranch',
  'ranch-summer': 'ranch',
  'ranch-autumn': 'ranch',
  'ranch-winter': 'ranch',
  town: 'town',
  // Every event theme, the Trials and the Lab's practice included, plays on screens that load the events pack.
  ...Object.fromEntries(THEME_IDS.map((id) => [id, 'event' as const])),
}
const SONGS: Song[] = [wildsong, ranchSpring, ranchSummer, ranchAutumn, ranchWinter, town, cup, open, ascension, crownDawn, crownTides, crownEmbers, crownFrost, legend, masquerade, rival, summit, rally, rallyRogue, sprout, elders, trial, practice]

/** The instruments a patch expands to, plus itself. */
function expand(inst: InstrumentId): InstrumentId[] {
  const def = INSTRUMENTS[inst]
  return def.patch ? [inst, ...def.patch.layers.map((l) => l.inst)] : [inst]
}

function addSong(u: Usage, song: Song, ctx: UsageContext, add: (inst: InstrumentId, c: UsageContext) => void): void {
  for (const line of song.lines) add(line.inst, ctx)
  for (const rule of Object.values(song.weather ?? {})) for (const inst of Object.values(rule.swap ?? {})) if (inst) add(inst, ctx)
  for (const arr of Object.values(song.arrangements ?? {})) {
    for (const inst of Object.values(arr.swap ?? {})) if (inst) add(inst, ctx)
    if (arr.kit) for (const inst of Object.values(KITS[arr.kit])) if (inst) add(inst, ctx)
  }
  if (song.kit) for (const inst of Object.values(KITS[song.kit])) if (inst) add(inst, ctx)
  void u
}

function addSfx(def: SfxDef, ctx: UsageContext, add: (inst: InstrumentId, c: UsageContext) => void): void {
  for (const l of def.layers) if (l.kind === 'sample' || l.kind === 'note' || l.kind === 'chord') add(l.inst, ctx)
}

function addBed(layers: readonly BedLayer[], ctx: UsageContext, add: (inst: InstrumentId, c: UsageContext) => void): void {
  for (const l of layers) if (l.kind === 'spawn' && l.event.kind === 'sample') add(l.event.inst, ctx)
}

export function buildUsage(): Usage {
  const byInstrument = new Map<string, Set<UsageContext>>()
  const add = (inst: InstrumentId, c: UsageContext) => {
    for (const i of expand(inst)) {
      let s = byInstrument.get(i)
      if (!s) {
        s = new Set()
        byInstrument.set(i, s)
      }
      s.add(c)
    }
  }
  const u: Usage = { byInstrument }
  for (const song of SONGS) addSong(u, song, SONG_CONTEXT[song.id] ?? 'place', add)
  // The cup's season palettes and kits (every regular cup is an event).
  for (const p of Object.values(SEASON_PALETTES)) {
    for (const inst of p.leads) add(inst, 'event')
    add(p.colour, 'event')
    for (const inst of Object.values(KITS[p.kit])) if (inst) add(inst, 'event')
  }
  for (const inst of Object.values(KITS.knockout)) if (inst) add(inst, 'event')
  for (const inst of Object.values(KITS.wild)) if (inst) add(inst, 'event')
  // The event table's leads and colours (the Arcane Cup's wine glasses, the festivals' hand chimes, the Trial sites).
  for (const row of [...EVENT_ARRANGEMENTS, ...Object.values(TRIAL_ARRANGEMENTS)]) {
    add(row.lead, 'event')
    add(row.colour, 'event')
    for (const inst of Object.values(KITS[row.kit])) if (inst) add(inst, 'event')
  }
  for (const s of Object.values(STINGERS)) addSong(u, s, 'event', add)
  // The rival calling cards play over the cup lobby.
  for (const def of Object.values(CALLING_CARDS)) addSfx(def, 'event', add)
  for (const def of Object.values(MUSICAL_EFFECTS)) addSfx(def, 'world', add)
  for (const def of Object.values(UI_SFX)) addSfx(def, 'ui', add)
  for (const def of Object.values(WORLD_SFX)) addSfx(def, 'world', add)
  for (const element of ELEMENTS) {
    for (const kind of ['fire', 'travel', 'hit', 'crit', 'miss', 'ko', 'special', 'push', 'dash', 'distract', 'wither', 'heal'] as const) {
      for (const strength of ['light', 'medium', 'heavy'] as const) addSfx(battleSfx(kind, element, strength), 'battleFx', add)
    }
  }
  for (const cue of Object.values(DRILL_CUES)) {
    addSong(u, cue.song, 'drill', add)
    for (const s of Object.values(cue.stingers)) addSong(u, s, 'drill', add)
    for (const f of cue.foley) addSfx(f.sfx, 'drill', add)
    if (cue.breath) addSfx(cue.breath, 'drill', add)
  }
  for (const id of BED_IDS) addBed(bedLayers(id), id === 'arena' || id === 'arena-out' ? 'event' : 'world', add)
  for (const layers of Object.values(CROWDS)) addBed(layers, 'event', add)
  for (const o of Object.values(WEATHER_OVERLAYS)) if (o.add) addBed(o.add, 'world', add)
  return u
}

export function registerUsage(): Usage {
  const u = buildUsage()
  setUsage(u)
  return u
}

/** Which contexts use an instrument (empty when none). */
export function contextsOf(inst: InstrumentId): Set<UsageContext> {
  return buildUsage().byInstrument.get(inst) ?? new Set()
}
