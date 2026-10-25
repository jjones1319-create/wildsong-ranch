import { STARTING_UNLOCKED } from '../data/breeds.ts'

/**
 * Save migrations. Every schema change bumps SAVE_VERSION and adds one step here, with a test.
 * A migration takes the previous version's raw object and returns the next version's raw object.
 * The same version number covers every file kind (save, monster, library); a step that only
 * concerns one kind checks `raw.kind` and leaves the others alone.
 *
 * History:
 * - v1 (M1): first schema: `{ schemaVersion, kind: 'save', game, rng }`.
 * - v2 (M2): saves gain `meta: { savedAt, appVersion }`; monster files and libraries appear.
 * - v3 (M3): the game state gains the week phase, the pending request, the last action (Repeat last week),
 *   the active monster's edit history, the onboarding tips seen and a few counters.
 * - v4 (M5): tournaments, the Journey Trial, the Guild (Officials won, Crowns, invitations), the Hall of Fame,
 *   mail, sale months, Journeys per site and titles.
 * - v5 (M6): the Freezer, the Elder Grove, the Memorial, Heartstones, the Encyclopedia, Sleeping Stones, the
 *   unlocked breeds and the Elder mentor month; a Journey remembers its Elder mentor; monsters gain `heirloom`.
 * - v6 (M7): the expedition in progress, the pending event, unlock-chain progress, the Journal's records, the
 *   Odd Job week, the Lantern Garden visit month, and the Encyclopedia's collected looks.
 * - v7 (M8): the planner queue (`planner`: queue, log, last stop).
 * - v8 (Odd Jobs: Echo Stones): the Echo Stones week and best round (`echoStonesWeek`, `echoStonesBest`).
 * - v9 (Playable events + round-by-round cups): a cup match's result may carry its length (`ticks`), and match
 *   rounds go up to 30 so a pre-v9 round robin (one round per match, up to 15) keeps its stored schedule. Nothing
 *   to rewrite: older results simply have no length, and `tournament.mode` keeps its meaning (the cup's default).
 * - v10 (Calendar): the calendar's ★ reminders (`calendarPins`, keys `${week}:${id}`), empty for older saves.
 */
export const SAVE_VERSION = 10

type RawSave = Record<string, unknown>

type Migration = (raw: RawSave) => RawSave

/** Keyed by the version it upgrades FROM. Version 0 means "no version field" (pre-release saves). */
const MIGRATIONS: Record<number, Migration> = {
  0: (raw) => ({ ...raw, schemaVersion: 1 }),
  1: (raw) => {
    const next: RawSave = { ...raw, schemaVersion: 2 }
    if (raw.kind === 'save' && !isRawSave(raw.meta)) next.meta = { savedAt: 0, appVersion: '' }
    return next
  },
  2: (raw) => {
    const next: RawSave = { ...raw, schemaVersion: 3 }
    if (raw.kind === 'save' && isRawSave(raw.game)) {
      next.game = {
        weekPhase: 'start',
        pendingRequest: null,
        lastAction: null,
        monsterHistory: [],
        tipsSeen: [],
        counters: { sweetsEaten: 0, sheetsLearned: 0, drillsDone: 0, restsTaken: 0 },
        sandbox: false,
        ...raw.game,
      }
    }
    return next
  },
  3: (raw) => {
    const next: RawSave = { ...raw, schemaVersion: 4 }
    if (raw.kind === 'save' && isRawSave(raw.game)) {
      next.game = {
        tournament: null,
        trial: null,
        guild: { officialsWon: [], crownsWon: [], legendWon: false, crownInvite: false, legendInvite: false, creditsRolled: false },
        hallOfFame: [],
        mail: [],
        saleMonths: [],
        journeysBySite: { 'iron-quarry': 0, 'windrun-steppe': 0, 'starfall-observatory': 0, 'archers-glade': 0, 'glacier-bastion': 0 },
        titles: [],
        ...raw.game,
      }
    }
    return next
  },
  4: (raw) => {
    const next: RawSave = { ...raw, schemaVersion: 5 }
    if (raw.kind === 'save' && isRawSave(raw.game)) {
      next.game = {
        freezer: [],
        elderGrove: [],
        memorial: [],
        heartstones: [],
        encyclopedia: { breeds: [], variants: [], phrases: [] },
        sleepingStones: [],
        unlocked: [...STARTING_UNLOCKED],
        elderMentorMonth: null,
        ...raw.game,
      }
    }
    return next
  },
  5: (raw) => {
    const next: RawSave = { ...raw, schemaVersion: 6 }
    if (raw.kind === 'save' && isRawSave(raw.game)) {
      const game = raw.game
      const encyclopedia = isRawSave(game.encyclopedia) ? { combos: [], ...game.encyclopedia } : { breeds: [], variants: [], phrases: [], combos: [] }
      next.game = {
        expedition: null,
        pendingEvent: null,
        unlocks: {
          rumorsHeard: [],
          masqueradeInvited: false,
          vigilPending: false,
          vigilOpen: false,
          cocoonInto: null,
          expeditionsBySite: { 'thornwood-ruins': 0, 'sunken-library': 0, 'hollowmoon-caverns': 0, 'skyreef-isles': 0 },
          reefclawArrived: false,
          wyrmScaleGiven: false,
        },
        records: { bestTotal: 0, bestTotalName: '', oldestWeeks: 0, oldestName: '', cupsWon: 0, expeditionsDone: 0, stonesWoken: 0, highestGeneration: 1 },
        oddJobWeek: null,
        memorialVisitMonth: null,
        ...game,
        encyclopedia,
      }
    }
    return next
  },
  6: (raw) => {
    const next: RawSave = { ...raw, schemaVersion: 7 }
    if (raw.kind === 'save' && isRawSave(raw.game)) {
      next.game = { planner: { queue: [], log: [], lastStop: null }, ...raw.game }
    }
    return next
  },
  7: (raw) => {
    const next: RawSave = { ...raw, schemaVersion: 8 }
    if (raw.kind === 'save' && isRawSave(raw.game)) {
      next.game = { echoStonesWeek: null, echoStonesBest: 0, ...raw.game }
    }
    return next
  },
  8: (raw) => ({ ...raw, schemaVersion: 9 }),
  9: (raw) => {
    const next: RawSave = { ...raw, schemaVersion: 10 }
    if (raw.kind === 'save' && isRawSave(raw.game)) next.game = { calendarPins: [], ...raw.game }
    return next
  },
}

export function isRawSave(raw: unknown): raw is RawSave {
  return typeof raw === 'object' && raw !== null && !Array.isArray(raw)
}

/** Brings any older save up to SAVE_VERSION. Unknown input is returned untouched for the validator to reject. */
export function migrate(raw: unknown): unknown {
  if (!isRawSave(raw)) return raw
  let current: RawSave = { ...raw }
  let version = typeof current.schemaVersion === 'number' && Number.isFinite(current.schemaVersion) ? Math.floor(current.schemaVersion) : 0
  if (version > SAVE_VERSION) return current
  while (version < SAVE_VERSION) {
    const step = MIGRATIONS[version]
    if (!step) break
    current = step(current)
    version += 1
  }
  return current
}
