import * as v from 'valibot'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { fill } from '../data/text/format.ts'
import { UI_TEXT } from '../data/text/ui.ts'
import { AUDIO, BOND, FREEZER, FUSION, HEARTSTONE, LAB, PLANNER, RANGES, SONGBOOK, TEXT_SIZES } from '../data/tuning.ts'
import { EVENT_BY_ID } from '../data/calendar.ts'
import { STARTING_UNLOCKED } from '../data/breeds.ts'
import { SECRET_BY_ID } from '../data/secrets.ts'
import { AUTO_STYLES, BREED_IDS, DIFFICULTIES, DRILL_IDS, EXPEDITION_SITE_IDS, FAMILIES, FOOD_IDS, GRADES, GROWTH_TYPES, HABITS, JOURNEY_SITE_IDS, KEEPSAKE_IDS, MAIL_KINDS, PERSONALITIES, SPEEDS, STAT_KEYS, TOURNAMENT_GRADES, TOY_IDS, TRANSPARENCY_MODES, UNLOCK_CHAINS, WEATHERS, type AutoStyle, type Speed, type TransparencyMode, type UnlockChain, FX_INTENSITIES, FX_QUALITY_SETTINGS, FX_TIERS, type FxIntensity, type FxQualitySetting, type FxTier, LISTENING_SETTINGS, type ListeningSetting } from '../data/types.ts'
import { EXPEDITION } from '../data/tuning.ts'
import { clamp } from '../core/mathx.ts'
import { buildMap } from '../core/expedition.ts'
import { clampMonsterMut, type Monster } from '../core/monster.ts'
import type { ExpeditionLoot, GameState } from '../core/state.ts'
import { isRawSave, migrate, SAVE_VERSION } from './migrate.ts'

/**
 * GAME_DESIGN §20: every save is validated with valibot on load and import. Unknown fields are dropped,
 * numbers are clamped, missing pieces get safe defaults, and nothing here ever throws at the caller.
 * Only identity fields (ids, breeds) are strict: a save that gets those wrong is rejected with a friendly message.
 */

const int = (lo: number, hi: number, def: number) =>
  v.fallback(
    v.pipe(
      v.number(),
      v.transform((n) => clamp(Math.round(n), lo, hi)),
    ),
    def,
  )
const bool = (def: boolean) => v.fallback(v.boolean(), def)
const text = (def: string, max: number) =>
  v.fallback(
    v.pipe(
      v.string(),
      v.transform((s) => s.slice(0, max)),
    ),
    def,
  )
const oneOf = <const T extends readonly (string | number)[]>(options: T, def: T[number]) => v.fallback(v.picklist(options), def)

const stat = () => int(RANGES.stat.min, RANGES.stat.max, RANGES.stat.min)
const cond = () => int(RANGES.condition.min, RANGES.condition.max, 0)
const weeks = () => int(0, RANGES.lifespan.max, 0)

const StatsSchema = v.object({ LIF: stat(), POW: stat(), INT: stat(), SKI: stat(), SPD: stat(), DEF: stat() })
const SweetsSchema = v.object({
  LIF: int(0, RANGES.stat.max, 0),
  POW: int(0, RANGES.stat.max, 0),
  INT: int(0, RANGES.stat.max, 0),
  SKI: int(0, RANGES.stat.max, 0),
  SPD: int(0, RANGES.stat.max, 0),
  DEF: int(0, RANGES.stat.max, 0),
})
const GradesSchema = v.object({ LIF: oneOf(GRADES, 'C'), POW: oneOf(GRADES, 'C'), INT: oneOf(GRADES, 'C'), SKI: oneOf(GRADES, 'C'), SPD: oneOf(GRADES, 'C'), DEF: oneOf(GRADES, 'C') })

const TechniqueSlotSchema = v.object({ id: v.string(), uses: int(0, 1_000_000, 0), level: oneOf([1, 2, 3] as const, 1) })

const LikesSchema = v.fallback(
  v.object({
    food: oneOf(FOOD_IDS, 'honey-bread'),
    dislikedFood: oneOf(FOOD_IDS, 'turnips'),
    toy: oneOf(TOY_IDS, 'rubber-ball'),
    battle: oneOf([-1, 0, 1] as const, 0),
    drill: oneOf(DRILL_IDS, 'hill-sprints'),
    dislikedDrill: oneOf(DRILL_IDS, 'acorn-shower'),
  }),
  { food: 'honey-bread', dislikedFood: 'turnips', toy: 'rubber-ball', battle: 0, drill: 'hill-sprints', dislikedDrill: 'acorn-shower' },
)

const TonicsSchema = v.fallback(
  v.object({
    LIF: v.optional(int(0, 99, 0)),
    POW: v.optional(int(0, 99, 0)),
    INT: v.optional(int(0, 99, 0)),
    SKI: v.optional(int(0, 99, 0)),
    SPD: v.optional(int(0, 99, 0)),
    DEF: v.optional(int(0, 99, 0)),
  }),
  {},
)

const StatusSchema = v.fallback(
  v.object({
    injuredWeeks: weeks(),
    sickWeeks: weeks(),
    missingWeeks: weeks(),
    clinicWeeks: weeks(),
    cocoonWeeks: weeks(),
    strainDebt: int(0, 1_000_000, 0),
    tonics: TonicsSchema,
    usedSunfruit: bool(false),
    usedMoonfruit: bool(false),
    heartstoneReceived: bool(false),
    announcedPrime: bool(false),
    announcedPastPrime: bool(false),
    warnedQuarterLife: bool(false),
    warned48: bool(false),
    warned10: bool(false),
    bondPct: int(100, BOND.boostPct, 100),
  }),
  {
    injuredWeeks: 0,
    sickWeeks: 0,
    missingWeeks: 0,
    clinicWeeks: 0,
    cocoonWeeks: 0,
    strainDebt: 0,
    tonics: {},
    usedSunfruit: false,
    usedMoonfruit: false,
    heartstoneReceived: false,
    announcedPrime: false,
    announcedPastPrime: false,
    warnedQuarterLife: false,
    warned48: false,
    warned10: false,
    bondPct: 100,
  },
)

const DietSchema = v.fallback(
  v.object({ lastFood: v.nullable(oneOf(FOOD_IDS, 'turnips')), sameFoodStreak: int(0, 10_000, 0), puddingCount: int(0, 10_000, 0), monthsFed: int(0, 10_000, 0) }),
  { lastFood: null, sameFoodStreak: 0, puddingCount: 0, monthsFed: 0 },
)

const RecordsSchema = v.fallback(
  v.object({
    wins: int(0, 1_000_000, 0),
    losses: int(0, 1_000_000, 0),
    draws: int(0, 1_000_000, 0),
    kos: int(0, 1_000_000, 0),
    cupsWon: int(0, 1_000_000, 0),
    titles: v.fallback(v.array(v.string()), []),
    earnings: int(0, 1_000_000_000, 0),
    highestGrade: oneOf(TOURNAMENT_GRADES, 'E'),
    crownsWon: int(0, 1000, 0),
    fromSweets: v.fallback(SweetsSchema, { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }),
  }),
  { wins: 0, losses: 0, draws: 0, kos: 0, cupsWon: 0, titles: [], earnings: 0, highestGrade: 'E', crownsWon: 0, fromSweets: { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 } },
)

export const MonsterSchema = v.object({
  id: v.pipe(v.string(), v.minLength(1)),
  name: text('', RANGES.nameLength.max),
  mainBreed: v.picklist(BREED_IDS),
  subBreed: v.picklist(BREED_IDS),
  variantId: v.fallback(v.nullable(v.string()), null),
  generation: int(1, 1_000_000, 1),
  parents: v.fallback(v.union([v.tuple([v.string(), v.string()]), v.tuple([])]), []),
  seedPhrase: text('', 200),
  heirloom: v.fallback(v.nullable(v.picklist(FAMILIES)), null),
  stats: v.fallback(StatsSchema, { LIF: 1, POW: 1, INT: 1, SKI: 1, SPD: 1, DEF: 1 }),
  grades: v.fallback(GradesSchema, { LIF: 'C', POW: 'C', INT: 'C', SKI: 'C', SPD: 'C', DEF: 'C' }),
  growthType: oneOf(GROWTH_TYPES, 'Steady'),
  gutsRate: int(RANGES.gutsRate.min, RANGES.gutsRate.max, 12),
  lifespanTotal: int(RANGES.lifespan.min, RANGES.lifespan.max, 300),
  ageWeeks: weeks(),
  fatigue: cond(),
  stress: cond(),
  spoil: cond(),
  fear: cond(),
  nature: int(RANGES.nature.min, RANGES.nature.max, 0),
  form: int(RANGES.form.min, RANGES.form.max, 0),
  fame: int(RANGES.fame.min, RANGES.fame.max, 0),
  grade: oneOf(TOURNAMENT_GRADES, 'E'),
  techniques: v.fallback(v.array(v.fallback(v.nullable(TechniqueSlotSchema), null)), []),
  likes: LikesSchema,
  status: StatusSchema,
  diet: DietSchema,
  records: RecordsSchema,
  flags: v.fallback(v.object({ pure: bool(false), edited: bool(false), sandbox: bool(false) }), { pure: false, edited: false, sandbox: false }),
  appearance: v.fallback(v.object({ paletteBreed: v.picklist(BREED_IDS), accentPart: v.fallback(v.nullable(v.string()), null) }), { paletteBreed: 'puddlepup', accentPart: null }),
})

const JourneySchema = v.object({
  site: v.picklist(JOURNEY_SITE_IDS),
  weekNo: int(1, 5, 1),
  successes: int(0, 4, 0),
  learned: v.fallback(v.nullable(v.string()), null),
  pendingTechnique: v.fallback(v.nullable(v.string()), null),
  gains: v.fallback(SweetsSchema, { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }),
  elderMentor: bool(false),
})

const stamp = () => int(0, Number.MAX_SAFE_INTEGER, 0)
/** A real-world time in ms, or null; anything that isn't a positive, finite number becomes null. */
const maybeTime = () => v.fallback(v.nullable(v.pipe(v.number(), v.finite(), v.minValue(1), v.transform((n) => Math.round(n)))), null)

const HistoryEntrySchema = v.object({ monster: MonsterSchema, savedAt: stamp() })

/** A list whose broken entries are dropped instead of failing the whole file. */
const listOf = <S extends v.GenericSchema>(schema: S) => v.fallback(v.array(v.fallback(v.nullable(schema), null)), [])

const RequestSchema = v.fallback(
  v.nullable(v.object({ kind: v.picklist(['rest', 'play', 'treat'] as const), toy: v.fallback(v.nullable(v.picklist(TOY_IDS)), null) })),
  null,
)

const WeekActionSchema = v.fallback(
  v.nullable(
    v.variant('kind', [
      v.object({ kind: v.literal('drill'), drill: v.picklist(DRILL_IDS) }),
      v.object({ kind: v.literal('rest') }),
      v.object({ kind: v.literal('play') }),
      v.object({ kind: v.literal('journey'), site: v.picklist(JOURNEY_SITE_IDS) }),
      v.object({ kind: v.literal('expedition'), site: v.picklist(EXPEDITION_SITE_IDS) }),
      v.object({ kind: v.literal('event') }),
      v.object({ kind: v.literal('none') }),
    ]),
  ),
  null,
)

/* ---------- M8: the planner ---------- */

const PlannerStepSchema = v.variant('kind', [v.object({ kind: v.literal('drill'), drill: v.picklist(DRILL_IDS) }), v.object({ kind: v.literal('rest') })])

const PLANNER_STOPS = [
  'empty',
  'noMonster',
  'ended',
  'request',
  'event',
  'trial',
  'tournament',
  'expedition',
  'journey',
  'locked',
  'mail',
  'illness',
  'breakdown',
  'warning',
  'forcedRest',
  'signature',
  'grewUp',
  'prime',
  'fatigue',
  'stress',
  'invalid',
] as const

const PlannerLogSchema = v.object({
  week: int(0, 1_000_000, 0),
  step: PlannerStepSchema,
  outcome: v.fallback(v.nullable(v.picklist(['Perfect', 'Superb', 'Great', 'Good', 'Success', 'Cheat', 'Fail', 'Slacked'] as const)), null),
  gains: v.fallback(v.record(v.picklist(STAT_KEYS), int(-100_000, 100_000, 0)), {}),
  pay: int(0, 1_000_000_000, 0),
})

const PlannerSchema = v.fallback(
  v.object({
    queue: listOf(PlannerStepSchema),
    log: listOf(PlannerLogSchema),
    lastStop: v.fallback(v.nullable(v.picklist(PLANNER_STOPS)), null),
  }),
  { queue: [], log: [], lastStop: null },
)

/* ---------- M5: tournaments, Guild, mail ---------- */

const ParticipantSchema = v.object({
  name: text('', 32),
  monster: MonsterSchema,
  personality: oneOf(PERSONALITIES, 'Steady'),
  habit: oneOf(HABITS, 'none'),
  rivalId: v.fallback(v.nullable(v.string()), null),
  player: bool(false),
})

const MatchResultSchema = v.object({
  winner: v.fallback(v.nullable(v.picklist([0, 1] as const)), null),
  how: oneOf(['ko', 'time', 'forfeit', 'walkover'] as const, 'time'),
  hpPct: v.fallback(v.tuple([int(0, 1000, 0), int(0, 1000, 0)]), [0, 0]),
  /** v9: the match's length in ticks; absent on older results. */
  ticks: v.optional(v.fallback(v.pipe(v.number(), v.transform((n) => clamp(Math.round(n), 0, 100_000))), 0)),
})

const MatchSchema = v.object({
  round: int(1, 30, 1),
  a: int(0, 15, 0),
  b: int(0, 15, 0),
  result: v.fallback(v.nullable(MatchResultSchema), null),
})

const indexList = () => v.fallback(v.array(int(0, 15, 0)), [])

/** A cup in progress. Strict on identity (event id, participants); anything else falls back. */
const TournamentSchema = v.pipe(
  v.object({
    eventId: v.string(),
    week: int(0, 1_000_000, 0),
    seed: int(0, 4_294_967_295, 0),
    mode: oneOf(['auto', 'manual'] as const, 'auto'),
    participants: v.array(ParticipantSchema),
    matches: v.fallback(v.array(MatchSchema), []),
    koOut: indexList(),
    eliminated: indexList(),
    relayWins: int(0, 10, 0),
    done: bool(false),
    playerTechUses: v.optional(v.fallback(v.record(v.string(), int(0, 100_000, 0)), {})),
  }),
  v.check((t) => EVENT_BY_ID[t.eventId] !== undefined && t.participants.length >= 2, 'unknown tournament'),
)

const GuildSchema = v.fallback(
  v.object({
    officialsWon: v.fallback(v.array(v.picklist(TOURNAMENT_GRADES)), []),
    crownsWon: v.fallback(v.array(v.string()), []),
    legendWon: bool(false),
    crownInvite: bool(false),
    legendInvite: bool(false),
    creditsRolled: bool(false),
  }),
  { officialsWon: [], crownsWon: [], legendWon: false, crownInvite: false, legendInvite: false, creditsRolled: false },
)

const MailSchema = v.object({
  id: v.string(),
  week: int(0, 1_000_000, 0),
  kind: oneOf(MAIL_KINDS, 'info'),
  ref: text('', 64),
  read: bool(false),
})

const JourneysBySiteSchema = v.fallback(
  v.object({ 'iron-quarry': int(0, 100_000, 0), 'windrun-steppe': int(0, 100_000, 0), 'starfall-observatory': int(0, 100_000, 0), 'archers-glade': int(0, 100_000, 0), 'glacier-bastion': int(0, 100_000, 0) }),
  { 'iron-quarry': 0, 'windrun-steppe': 0, 'starfall-observatory': 0, 'archers-glade': 0, 'glacier-bastion': 0 },
)

/* ---------- M6: legacy ---------- */

const MemorialSchema = v.object({
  monster: MonsterSchema,
  cause: oneOf(['passed', 'retired', 'fused', 'neglected', 'wandered'] as const, 'passed'),
  epitaph: text('', 80),
  week: int(0, 1_000_000, 0),
})

const HeartstoneSchema = v.object({
  id: v.string(),
  donorId: text('', 64),
  donorName: text('', RANGES.nameLength.max),
  donorBreed: v.picklist(BREED_IDS),
  donorSub: v.fallback(v.picklist(BREED_IDS), 'puddlepup'),
  donorVariant: v.fallback(v.nullable(v.string()), null),
  gains: v.fallback(SweetsSchema, { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }),
  family: oneOf(FAMILIES, 'Basic'),
  week: int(0, 1_000_000, 0),
})

const EncyclopediaPhraseSchema = v.object({
  phrase: text('', 200),
  artist: text('', 200),
  name: text('', RANGES.nameLength.max),
  mainBreed: v.picklist(BREED_IDS),
  subBreed: v.picklist(BREED_IDS),
  variantId: v.fallback(v.nullable(v.string()), null),
})

const EncyclopediaSchema = v.fallback(
  v.object({
    breeds: v.fallback(v.array(v.picklist(BREED_IDS)), []),
    variants: v.fallback(v.array(v.string()), []),
    phrases: listOf(EncyclopediaPhraseSchema),
    combos: v.fallback(v.array(text('', 64)), []),
  }),
  { breeds: [], variants: [], phrases: [], combos: [] },
)

/* ---------- M7: expeditions, unlock chains, the Journal ---------- */

const nodeList = () => v.fallback(v.array(int(0, 63, 0)), [])

/** A trip in progress. Strict on the site; the node ids are checked against the rebuilt map in tidyGame. */
const ExpeditionSchema = v.object({
  site: v.picklist(EXPEDITION_SITE_IDS),
  seed: int(0, 4_294_967_295, 0),
  startWeek: int(0, 1_000_000, 0),
  weekNo: int(1, EXPEDITION.weeks + 1, 1),
  stamina: int(0, 1000, 0),
  staminaMax: int(1, 1000, 1),
  at: int(0, 63, 0),
  visited: nodeList(),
  searched: nodeList(),
  passed: nodeList(),
  blockedAt: v.fallback(v.nullable(int(0, 63, 0)), null),
  visit: int(1, 100_000, 1),
  loot: listOf(v.object({ id: v.string(), qty: int(1, 1000, 1) })),
  sheets: v.fallback(v.array(v.string()), []),
  keyFound: v.fallback(v.nullable(v.string()), null),
  lootlidPlaced: v.fallback(v.nullable(v.picklist(['ranch', 'freezer', 'none'] as const)), null),
  ended: v.fallback(v.nullable(v.picklist(['camp', 'retreat', 'exhausted'] as const)), null),
  log: v.fallback(v.array(text('', 400)), []),
})

const ExpeditionsBySiteSchema = v.fallback(
  v.object({ 'thornwood-ruins': int(0, 100_000, 0), 'sunken-library': int(0, 100_000, 0), 'hollowmoon-caverns': int(0, 100_000, 0), 'skyreef-isles': int(0, 100_000, 0) }),
  { 'thornwood-ruins': 0, 'sunken-library': 0, 'hollowmoon-caverns': 0, 'skyreef-isles': 0 },
)

const UnlocksSchema = v.fallback(
  v.object({
    rumorsHeard: listOf(v.picklist(UNLOCK_CHAINS)),
    masqueradeInvited: bool(false),
    vigilPending: bool(false),
    vigilOpen: bool(false),
    cocoonInto: v.fallback(v.nullable(v.picklist(BREED_IDS)), null),
    expeditionsBySite: ExpeditionsBySiteSchema,
    reefclawArrived: bool(false),
    wyrmScaleGiven: bool(false),
  }),
  { rumorsHeard: [], masqueradeInvited: false, vigilPending: false, vigilOpen: false, cocoonInto: null, expeditionsBySite: { 'thornwood-ruins': 0, 'sunken-library': 0, 'hollowmoon-caverns': 0, 'skyreef-isles': 0 }, reefclawArrived: false, wyrmScaleGiven: false },
)

const JournalRecordsSchema = v.fallback(
  v.object({
    bestTotal: int(0, 6000, 0),
    bestTotalName: text('', RANGES.nameLength.max),
    oldestWeeks: int(0, RANGES.lifespan.max, 0),
    oldestName: text('', RANGES.nameLength.max),
    cupsWon: int(0, 1_000_000, 0),
    expeditionsDone: int(0, 1_000_000, 0),
    stonesWoken: int(0, 1_000_000, 0),
    highestGeneration: int(1, 1_000_000, 1),
  }),
  { bestTotal: 0, bestTotalName: '', oldestWeeks: 0, oldestName: '', cupsWon: 0, expeditionsDone: 0, stonesWoken: 0, highestGeneration: 1 },
)

const SleepingStoneSchema = v.object({ phrase: text('', 200), artist: text('', 200), breed: v.picklist(BREED_IDS), week: int(0, 1_000_000, 0) })

const CountersSchema = v.fallback(
  v.object({ sweetsEaten: int(0, 1_000_000_000, 0), sheetsLearned: int(0, 1_000_000_000, 0), drillsDone: int(0, 1_000_000_000, 0), restsTaken: int(0, 1_000_000_000, 0) }),
  { sweetsEaten: 0, sheetsLearned: 0, drillsDone: 0, restsTaken: 0 },
)

export const GameStateSchema = v.object({
  week: int(0, 1_000_000, 0),
  money: int(-1_000_000_000, 1_000_000_000, 0),
  difficulty: oneOf(DIFFICULTIES, 'Standard'),
  settings: v.fallback(v.object({ onePerWeek: bool(false), vacation: bool(false) }), { onePerWeek: false, vacation: false }),
  monster: v.nullable(MonsterSchema),
  inventory: v.fallback(v.record(v.string(), int(0, 1_000_000_000, 0)), {}),
  songbook: v.fallback(v.array(v.string()), []),
  upgrades: v.fallback(v.object({ cozyBarn: bool(false), trainingYard: bool(false), tidePool: bool(false), lanternGarden: bool(false) }), {
    cozyBarn: false,
    trainingYard: false,
    tidePool: false,
    lanternGarden: false,
  }),
  foodChoice: oneOf(FOOD_IDS, 'turnips'),
  weather: oneOf(WEATHERS, 'Sunny'),
  itemsUsedThisWeek: int(0, 1_000_000, 0),
  journey: v.fallback(v.nullable(JourneySchema), null),
  ended: v.fallback(v.nullable(v.picklist(['passed', 'retired', 'neglected', 'wandered'] as const)), null),
  breeder: v.fallback(v.object({ name: text('Breeder', 24), ranchName: text('Wildsong Ranch', 24), rank: int(1, 10, 1) }), { name: 'Breeder', ranchName: 'Wildsong Ranch', rank: 1 }),
  weekPhase: oneOf(['start', 'action'] as const, 'start'),
  pendingRequest: RequestSchema,
  lastAction: WeekActionSchema,
  monsterHistory: listOf(HistoryEntrySchema),
  tipsSeen: v.fallback(v.array(v.string()), []),
  counters: CountersSchema,
  sandbox: bool(false),
  tournament: v.fallback(v.nullable(TournamentSchema), null),
  trial: v.fallback(v.nullable(v.object({ site: v.picklist(JOURNEY_SITE_IDS), pendingTechnique: v.fallback(v.nullable(v.string()), null) })), null),
  guild: GuildSchema,
  hallOfFame: v.fallback(v.array(v.fallback(v.nullable(v.object({ monster: MonsterSchema, week: int(0, 1_000_000, 0) })), null)), []),
  mail: v.fallback(v.array(v.fallback(v.nullable(MailSchema), null)), []),
  saleMonths: v.fallback(v.array(int(1, 12, 1)), []),
  journeysBySite: JourneysBySiteSchema,
  titles: v.fallback(v.array(v.string()), []),
  freezer: listOf(MonsterSchema),
  elderGrove: listOf(MonsterSchema),
  memorial: listOf(MemorialSchema),
  heartstones: listOf(HeartstoneSchema),
  encyclopedia: EncyclopediaSchema,
  sleepingStones: listOf(SleepingStoneSchema),
  unlocked: v.fallback(v.array(v.picklist(BREED_IDS)), [...STARTING_UNLOCKED]),
  elderMentorMonth: v.fallback(v.nullable(int(0, 1_000_000, 0)), null),
  expedition: v.fallback(v.nullable(ExpeditionSchema), null),
  pendingEvent: v.fallback(v.nullable(v.object({ kind: v.literal('stormChase') })), null),
  unlocks: UnlocksSchema,
  records: JournalRecordsSchema,
  oddJobWeek: v.fallback(v.nullable(int(0, 1_000_000, 0)), null),
  turnipBest: int(0, 100_000, 0),
  echoStonesWeek: v.fallback(v.nullable(int(0, 1_000_000, 0)), null),
  echoStonesBest: int(0, 10_000, 0),
  dashWeek: v.fallback(v.nullable(int(0, 1_000_000, 0)), null),
  dashBest: int(0, 10_000, 0),
  keepsakes: v.fallback(
    v.pipe(
      v.array(v.fallback(v.picklist(KEEPSAKE_IDS), KEEPSAKE_IDS[0])),
      v.transform((ids) => [...new Set(ids)]),
    ),
    [],
  ),
  // §6.10 a bad time is "not armed" (never 0, which would read as armed long ago and could punish an import).
  away: v.fallback(v.object({ armedAt: maybeTime(), lastGreetAt: maybeTime() }), { armedAt: null, lastGreetAt: null }),
  calendarPins: v.fallback(
    v.pipe(
      v.array(v.fallback(v.pipe(v.string(), v.regex(/^\d{1,6}:[a-z0-9-]{1,40}$/)), '')),
      v.transform((keys) => [...new Set(keys.filter((k) => k !== ''))].slice(0, 200)),
    ),
    [],
  ),
  memorialVisitMonth: v.fallback(v.nullable(int(0, 1_000_000, 0)), null),
  planner: PlannerSchema,
  // §15 found recipes `a+b>c`; tidyGame checks the breeds.
  fusionFinds: v.fallback(
    v.pipe(
      v.array(v.fallback(v.pipe(v.string(), v.regex(/^[a-z]{1,24}\+[a-z]{1,24}>[a-z]{1,24}$/)), '')),
      v.transform((keys) => [...new Set(keys.filter((k) => k !== ''))].slice(0, FUSION.findsCap)),
    ),
    [],
  ),
})

const MetaSchema = v.fallback(v.object({ savedAt: stamp(), appVersion: text('', 32) }), { savedAt: 0, appVersion: '' })

export const SaveSchema = v.object({
  schemaVersion: v.literal(SAVE_VERSION),
  kind: v.literal('save'),
  game: GameStateSchema,
  /** mulberry32 state. */
  rng: int(0, 4_294_967_295, 1),
  meta: MetaSchema,
})

/** A single exported monster (share code, .json, .txt). The edit history travels in files but not in codes. */
export const MonsterFileSchema = v.object({
  schemaVersion: v.literal(SAVE_VERSION),
  kind: v.literal('monster'),
  monster: MonsterSchema,
  history: listOf(HistoryEntrySchema),
})

const LibraryEntrySchema = v.object({
  monster: MonsterSchema,
  history: listOf(HistoryEntrySchema),
  createdAt: stamp(),
  updatedAt: stamp(),
})

/**
 * The global Library of Lab creations (§19, §20): shared by every save slot. The entry list itself is
 * strict (a library without a list is unreadable, so the mirror copy gets its turn); broken entries are dropped.
 */
export const LibrarySchema = v.object({
  schemaVersion: v.literal(SAVE_VERSION),
  kind: v.literal('library'),
  entries: v.array(v.fallback(v.nullable(LibraryEntrySchema), null)),
})

const SETTINGS_DEFAULTS = {
  showEditedBadge: false,
  reduceMotion: false,
  transparency: 'guided' as TransparencyMode,
  textSize: TEXT_SIZES[0],
  speed: 'normal' as Speed,
  sound: true,
  music: true,
  haptics: true,
  assist: true,
  autoStyle: 'balanced' as AutoStyle,
  showThinking: null as boolean | null,
  masterVolume: AUDIO.defaultVolume.master as number,
  musicVolume: AUDIO.defaultVolume.music as number,
  sfxVolume: AUDIO.defaultVolume.sfx as number,
  ambience: true,
  ambienceVolume: AUDIO.defaultVolume.ambience as number,
  buttonSounds: true,
  listening: 'speaker' as ListeningSetting,
  monoAudio: false,
  audioDefaultsV2: true,
  leftHanded: false,
  installHelpDismissedAt: 0,
  lastBackupAt: 0,
  lastBackupWeek: null as number | null,
  backupSnoozedAt: 0,
  backupBaselineAt: 0,
  oddJobsRelaxed: false,
  cupMode: 'manual' as 'manual' | 'auto',
  fxQuality: 'auto' as FxQualitySetting,
  fxIntensity: 'standard' as FxIntensity,
  fxAutoTier: null as FxTier | null,
}

/** App settings that live outside any save slot. Never fails validation: garbage becomes the defaults. */
export const SettingsSchema = v.fallback(
  v.object({
    showEditedBadge: bool(false),
    reduceMotion: bool(false),
    transparency: oneOf(TRANSPARENCY_MODES, 'guided'),
    textSize: oneOf(TEXT_SIZES, TEXT_SIZES[0]),
    speed: oneOf(SPEEDS, 'normal'),
    sound: bool(true),
    music: bool(true),
    haptics: bool(true),
    assist: bool(true),
    autoStyle: oneOf(AUTO_STYLES, 'balanced'),
    showThinking: v.fallback(v.nullable(v.boolean()), null),
    masterVolume: int(0, 100, AUDIO.defaultVolume.master),
    musicVolume: int(0, 100, AUDIO.defaultVolume.music),
    sfxVolume: int(0, 100, AUDIO.defaultVolume.sfx),
    ambience: bool(true),
    ambienceVolume: int(0, 100, AUDIO.defaultVolume.ambience),
    buttonSounds: bool(true),
    listening: oneOf(LISTENING_SETTINGS, 'speaker'),
    monoAudio: bool(false),
    // Sound 2.0 §12: a save from before it lacks this flag, so the one-time volume bump runs once.
    audioDefaultsV2: bool(false),
    leftHanded: bool(false),
    installHelpDismissedAt: stamp(),
    lastBackupAt: stamp(),
    lastBackupWeek: v.fallback(v.nullable(int(0, 1_000_000, 0)), null),
    backupSnoozedAt: stamp(),
    backupBaselineAt: stamp(),
    oddJobsRelaxed: bool(false),
    cupMode: oneOf(['manual', 'auto'] as const, 'manual'),
    fxQuality: oneOf(FX_QUALITY_SETTINGS, 'auto'),
    fxIntensity: oneOf(FX_INTENSITIES, 'standard'),
    fxAutoTier: v.fallback(v.nullable(v.picklist(FX_TIERS)), null),
  }),
  SETTINGS_DEFAULTS,
)

export interface SaveMeta {
  /** Real-world time (ms since the epoch) when it was written; 0 when unknown. */
  savedAt: number
  appVersion: string
}

export interface SaveFile {
  schemaVersion: typeof SAVE_VERSION
  kind: 'save'
  game: GameState
  rng: number
  meta: SaveMeta
}

export interface HistoryEntry {
  monster: Monster
  savedAt: number
}

export interface MonsterFile {
  schemaVersion: typeof SAVE_VERSION
  kind: 'monster'
  monster: Monster
  history: HistoryEntry[]
}

export interface LibraryEntry {
  monster: Monster
  /** Previous versions, oldest first, at most LAB.historyLimit. */
  history: HistoryEntry[]
  createdAt: number
  updatedAt: number
}

export interface Library {
  schemaVersion: typeof SAVE_VERSION
  kind: 'library'
  entries: LibraryEntry[]
}

export interface AppSettings {
  showEditedBadge: boolean
  reduceMotion: boolean
  /** §6.8. */
  transparency: TransparencyMode
  /** §24: 100, 115 or 130 percent. */
  textSize: number
  /** §21: the global animation speed. */
  speed: Speed
  /** §23 mutes. */
  sound: boolean
  music: boolean
  haptics: boolean
  /** §12.11 Assist: tapping a card in another column walks there and fires. */
  assist: boolean
  /** §12.11 how the player's monster fights on Auto (M10). */
  autoStyle: AutoStyle
  /** §12.11 the plan icons over the monsters; null = follow the transparency mode (on in Breeder's Lens). */
  showThinking: boolean | null
  /** §23 volumes, 0–100. */
  masterVolume: number
  musicVolume: number
  sfxVolume: number
  /** Sound 2.0 §12: ambience switch and volume, button sounds, the listening preset, mono, and the one-time defaults bump. */
  ambience: boolean
  ambienceVolume: number
  buttonSounds: boolean
  listening: ListeningSetting
  monoAudio: boolean
  audioDefaultsV2: boolean
  /** §24 the left-handed battle layout. */
  leftHanded: boolean
  /** §12.11 the default the cup entry screen offers for the player's matches: 'manual' = Fight, 'auto' = Auto (remembered). */
  cupMode: 'manual' | 'auto'
  /** V1 effects (VISUAL_V1_EFFECTS §6): Quality (auto picks a tier and remembers it in fxAutoTier) and Intensity. */
  fxQuality: FxQualitySetting
  fxIntensity: FxIntensity
  fxAutoTier: FxTier | null
  /** When "Later" was tapped on the install-help card (0 = never). */
  installHelpDismissedAt: number
  /** §20 backup reminders: the last export (real time and in-game week) and the last snooze. */
  lastBackupAt: number
  lastBackupWeek: number | null
  backupSnoozedAt: number
  /** When the app first ran on this phone: the day rule counts from here until the first backup. */
  backupBaselineAt: number
  /** CONTENT §13 Odd Jobs: the Relaxed option (Echo Stones' tempo, Meadow Dash's rivals). */
  oddJobsRelaxed: boolean
}

type Fail = { ok: false; error: string }
export type SaveValidation = { ok: true; save: SaveFile } | Fail
export type MonsterFileValidation = { ok: true; file: MonsterFile } | Fail
export type LibraryValidation = { ok: true; library: Library } | Fail
export type AnyValidation =
  | { ok: true; kind: 'save'; save: SaveFile }
  | { ok: true; kind: 'monster'; file: MonsterFile }
  | { ok: true; kind: 'library'; library: Library }
  | Fail

export function makeSave(game: GameState, rng: number, meta: Partial<SaveMeta> = {}): SaveFile {
  return { schemaVersion: SAVE_VERSION, kind: 'save', game, rng, meta: { savedAt: 0, appVersion: '', ...meta } }
}

export function makeMonsterFile(monster: Monster, history: HistoryEntry[] = []): MonsterFile {
  return { schemaVersion: SAVE_VERSION, kind: 'monster', monster, history }
}

export function emptyLibrary(): Library {
  return { schemaVersion: SAVE_VERSION, kind: 'library', entries: [] }
}

export function defaultSettings(): AppSettings {
  return { ...SETTINGS_DEFAULTS }
}

/** Drops unknown technique and sheet ids, caps the technique list and clamps the monster. */
function tidyMonster(m: Monster): Monster {
  m.techniques = (m.techniques as (Monster['techniques'][number] | null)[])
    .filter((t): t is Monster['techniques'][number] => t !== null && TECHNIQUE_BY_ID[t.id] !== undefined)
    .slice(0, SONGBOOK.maxTechniques)
  const seen = new Set<string>()
  m.techniques = m.techniques.filter((t) => (seen.has(t.id) ? false : (seen.add(t.id), true)))
  return clampMonsterMut(m)
}

function tidyHistory(list: (HistoryEntry | null)[]): HistoryEntry[] {
  return list
    .filter((h): h is HistoryEntry => h !== null)
    .map((h) => ({ monster: tidyMonster(h.monster), savedAt: h.savedAt }))
    .slice(-LAB.historyLimit)
}

/** A found recipe names three real breeds: a sorted pair and a result that is neither parent. */
function isFindKey(key: string): boolean {
  const [pair, result] = key.split('>') as [string, string]
  const [a, b] = pair.split('+') as [string, string]
  const known = (id: string) => (BREED_IDS as readonly string[]).includes(id)
  return known(a) && known(b) && known(result) && a <= b && result !== a && result !== b
}

function tidyGame(game: GameState): GameState {
  if (game.monster) game.monster = tidyMonster(game.monster)
  game.songbook = [...new Set(game.songbook.filter((id) => TECHNIQUE_BY_ID[id] !== undefined))].sort()
  for (const id of Object.keys(game.inventory)) if (game.inventory[id]! <= 0) delete game.inventory[id]
  game.monsterHistory = tidyHistory(game.monsterHistory as (HistoryEntry | null)[])
  game.tipsSeen = [...new Set(game.tipsSeen)]
  game.titles = [...new Set(game.titles)]
  game.hallOfFame = (game.hallOfFame as (GameState['hallOfFame'][number] | null)[]).filter((h): h is GameState['hallOfFame'][number] => h !== null).map((h) => ({ monster: tidyMonster(h.monster), week: h.week }))
  game.mail = (game.mail as (GameState['mail'][number] | null)[]).filter((m): m is GameState['mail'][number] => m !== null)
  game.saleMonths = [...new Set(game.saleMonths)]
  if (game.tournament) {
    game.tournament.participants = game.tournament.participants.map((p) => ({ ...p, monster: tidyMonster(p.monster) }))
    if (!game.tournament.participants[0]?.player) game.tournament = null
  }
  // M6 legacy lists: broken entries are already dropped; tidy the monsters, keep ids unique, honour the caps.
  const uniqueMonsters = (list: (Monster | null)[], seen: Set<string>): Monster[] =>
    list.filter((m): m is Monster => m !== null && !seen.has(m.id) && (seen.add(m.id), true)).map(tidyMonster)
  const ids = new Set<string>()
  if (game.monster) ids.add(game.monster.id)
  game.freezer = uniqueMonsters(game.freezer as (Monster | null)[], ids).slice(0, FREEZER.slots)
  game.elderGrove = uniqueMonsters(game.elderGrove as (Monster | null)[], ids)
  game.memorial = (game.memorial as (GameState['memorial'][number] | null)[]).filter((e): e is GameState['memorial'][number] => e !== null).map((e) => ({ ...e, monster: tidyMonster(e.monster) }))
  const stoneIds = new Set<string>()
  game.heartstones = (game.heartstones as (GameState['heartstones'][number] | null)[])
    .filter((h): h is GameState['heartstones'][number] => h !== null && !stoneIds.has(h.id) && (stoneIds.add(h.id), true))
    .slice(0, HEARTSTONE.maxWithLanternGarden)
  game.encyclopedia.breeds = [...new Set(game.encyclopedia.breeds)]
  game.encyclopedia.variants = [...new Set(game.encyclopedia.variants.filter((id) => SECRET_BY_ID[id] !== undefined))]
  game.encyclopedia.phrases = (game.encyclopedia.phrases as (GameState['encyclopedia']['phrases'][number] | null)[]).filter((p): p is GameState['encyclopedia']['phrases'][number] => p !== null)
  game.sleepingStones = (game.sleepingStones as (GameState['sleepingStones'][number] | null)[]).filter((p): p is GameState['sleepingStones'][number] => p !== null)
  game.unlocked = [...new Set([...STARTING_UNLOCKED, ...game.unlocked])]
  game.encyclopedia.combos = [...new Set(game.encyclopedia.combos)]
  game.fusionFinds = game.fusionFinds.filter(isFindKey)
  // M7: the expedition's node ids must fit the map its seed rebuilds; otherwise the trip is dropped (nothing else is lost).
  if (game.expedition) {
    const e = game.expedition
    const nodes = buildMap(e.site, e.seed).nodes.length
    const inMap = (i: number) => i >= 0 && i < nodes
    if (!inMap(e.at) || e.stamina > e.staminaMax) game.expedition = null
    else {
      e.visited = [...new Set(e.visited.filter(inMap))]
      e.searched = [...new Set(e.searched.filter(inMap))]
      e.passed = [...new Set(e.passed.filter(inMap))]
      if (e.blockedAt !== null && !inMap(e.blockedAt)) e.blockedAt = null
      e.loot = (e.loot as (ExpeditionLoot | null)[]).filter((l): l is ExpeditionLoot => l !== null)
      e.log = e.log.slice(-EXPEDITION.logLimit)
    }
  }
  game.unlocks.rumorsHeard = [...new Set((game.unlocks.rumorsHeard as (UnlockChain | null)[]).filter((c): c is UnlockChain => c !== null))]
  // M8: broken planner entries are already dropped; the queue keeps its cap.
  game.planner.queue = game.planner.queue.slice(0, PLANNER.maxWeeks)
  game.planner.log = game.planner.log.slice(-PLANNER.maxWeeks)
  if (!game.monster || game.ended) {
    game.tournament = null
    game.trial = null
    game.expedition = null
    game.pendingEvent = null
  }
  // A request or a phase only makes sense with a living monster.
  if (!game.monster || game.ended) {
    game.pendingRequest = null
    game.weekPhase = 'start'
  }
  return game
}

function describeIssue(issue: v.BaseIssue<unknown>): string {
  const path = issue.path?.map((p) => String(p.key)).join('.') ?? ''
  return path ? `${path}: ${issue.message}` : issue.message
}

/** Runs the migrations, and turns a too-new file into a clear message instead of a cryptic "invalid literal". */
function prepare(raw: unknown): { ok: true; value: unknown } | Fail {
  let migrated: unknown
  try {
    migrated = migrate(raw)
  } catch {
    return { ok: false, error: UI_TEXT.errors.saveUnreadable }
  }
  if (isRawSave(migrated) && typeof migrated.schemaVersion === 'number' && migrated.schemaVersion > SAVE_VERSION) {
    return { ok: false, error: UI_TEXT.errors.newerVersion }
  }
  return { ok: true, value: migrated }
}

/** Migrate, validate and tidy any raw save. Never throws. */
export function validateSave(raw: unknown): SaveValidation {
  const prepared = prepare(raw)
  if (!prepared.ok) return prepared
  const parsed = v.safeParse(SaveSchema, prepared.value)
  if (!parsed.success) {
    return { ok: false, error: fill(UI_TEXT.errors.saveInvalid, { detail: describeIssue(parsed.issues[0]) }) }
  }
  const output = parsed.output as unknown as SaveFile
  output.game = tidyGame(output.game)
  return { ok: true, save: output }
}

/** Validate a bare monster object. Never throws. */
export function validateMonster(raw: unknown): { ok: true; monster: Monster } | Fail {
  const parsed = v.safeParse(MonsterSchema, raw)
  if (!parsed.success) return { ok: false, error: fill(UI_TEXT.errors.monsterInvalid, { detail: describeIssue(parsed.issues[0]) }) }
  return { ok: true, monster: tidyMonster(parsed.output as unknown as Monster) }
}

function looksLikeBareMonster(raw: unknown): boolean {
  return isRawSave(raw) && raw.kind === undefined && typeof raw.mainBreed === 'string'
}

/** Validate a monster file (`kind: 'monster'`), or a bare monster object, for the Monster Lab. Never throws. */
export function validateMonsterFile(raw: unknown): MonsterFileValidation {
  if (looksLikeBareMonster(raw)) {
    const bare = validateMonster(raw)
    return bare.ok ? { ok: true, file: makeMonsterFile(bare.monster) } : bare
  }
  const prepared = prepare(raw)
  if (!prepared.ok) return prepared
  const parsed = v.safeParse(MonsterFileSchema, prepared.value)
  if (!parsed.success) return { ok: false, error: fill(UI_TEXT.errors.monsterInvalid, { detail: describeIssue(parsed.issues[0]) }) }
  const output = parsed.output as unknown as { monster: Monster; history: (HistoryEntry | null)[] }
  return { ok: true, file: makeMonsterFile(tidyMonster(output.monster), tidyHistory(output.history)) }
}

/** Validate the global Library. Broken entries are dropped; duplicate ids keep the first copy. Never throws. */
export function validateLibrary(raw: unknown): LibraryValidation {
  const prepared = prepare(raw)
  if (!prepared.ok) return prepared
  const parsed = v.safeParse(LibrarySchema, prepared.value)
  if (!parsed.success) return { ok: false, error: fill(UI_TEXT.errors.libraryInvalid, { detail: describeIssue(parsed.issues[0]) }) }
  const output = parsed.output as unknown as { entries: ({ monster: Monster; history: (HistoryEntry | null)[]; createdAt: number; updatedAt: number } | null)[] }
  const seen = new Set<string>()
  const entries: LibraryEntry[] = []
  for (const e of output.entries) {
    if (!e || seen.has(e.monster.id)) continue
    seen.add(e.monster.id)
    entries.push({ monster: tidyMonster(e.monster), history: tidyHistory(e.history), createdAt: e.createdAt, updatedAt: e.updatedAt })
  }
  return { ok: true, library: { schemaVersion: SAVE_VERSION, kind: 'library', entries } }
}

/** Settings never fail: anything unreadable becomes the defaults. */
export function validateSettings(raw: unknown): AppSettings {
  const parsed = v.safeParse(SettingsSchema, raw)
  return parsed.success ? applyAudioDefaultsV2(parsed.output as AppSettings) : defaultSettings()
}

/**
 * Sound 2.0 §12: existing players keep their own volumes, but the old defaults (music 55, effects 100) move to
 * the new ones (70, 75) once. Any other value was the player's choice and stays. Runs once per settings record.
 */
export function applyAudioDefaultsV2(s: AppSettings): AppSettings {
  if (s.audioDefaultsV2) return s
  return {
    ...s,
    musicVolume: s.musicVolume === AUDIO.legacyDefaults.music ? AUDIO.defaultVolume.music : s.musicVolume,
    sfxVolume: s.sfxVolume === AUDIO.legacyDefaults.sfx ? AUDIO.defaultVolume.sfx : s.sfxVolume,
    audioDefaultsV2: true,
  }
}

/** Sorts out any pasted or opened object by its `kind` (a bare monster counts as a monster). Never throws. */
export function validateAny(raw: unknown): AnyValidation {
  if (looksLikeBareMonster(raw)) {
    const r = validateMonsterFile(raw)
    return r.ok ? { ok: true, kind: 'monster', file: r.file } : r
  }
  if (!isRawSave(raw)) return { ok: false, error: UI_TEXT.errors.unknownKind }
  switch (raw.kind) {
    case 'save': {
      const r = validateSave(raw)
      return r.ok ? { ok: true, kind: 'save', save: r.save } : r
    }
    case 'monster': {
      const r = validateMonsterFile(raw)
      return r.ok ? { ok: true, kind: 'monster', file: r.file } : r
    }
    case 'library': {
      const r = validateLibrary(raw)
      return r.ok ? { ok: true, kind: 'library', library: r.library } : r
    }
    default:
      return { ok: false, error: UI_TEXT.errors.unknownKind }
  }
}

export { STAT_KEYS }
