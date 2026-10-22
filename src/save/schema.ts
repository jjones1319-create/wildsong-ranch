import * as v from 'valibot'
import { TECHNIQUE_BY_ID } from '../data/techniques.ts'
import { RANGES, SONGBOOK } from '../data/tuning.ts'
import { BREED_IDS, DIFFICULTIES, DRILL_IDS, FOOD_IDS, GRADES, GROWTH_TYPES, JOURNEY_SITE_IDS, STAT_KEYS, TOURNAMENT_GRADES, TOY_IDS, WEATHERS } from '../data/types.ts'
import { clamp } from '../core/mathx.ts'
import { clampMonsterMut, type Monster } from '../core/monster.ts'
import type { GameState } from '../core/state.ts'
import { migrate, SAVE_VERSION } from './migrate.ts'

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
})

export const GameStateSchema = v.object({
  week: int(0, 1_000_000, 0),
  money: int(-1_000_000_000, 1_000_000_000, 0),
  difficulty: oneOf(DIFFICULTIES, 'Standard'),
  settings: v.fallback(v.object({ onePerWeek: bool(false) }), { onePerWeek: false }),
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
  ended: v.fallback(v.nullable(v.picklist(['passed', 'retired'] as const)), null),
  breeder: v.fallback(v.object({ name: text('Breeder', 24), ranchName: text('Wildsong Ranch', 24), rank: int(1, 10, 1) }), { name: 'Breeder', ranchName: 'Wildsong Ranch', rank: 1 }),
})

export const SaveSchema = v.object({
  schemaVersion: v.literal(SAVE_VERSION),
  kind: v.literal('save'),
  game: GameStateSchema,
  /** mulberry32 state. */
  rng: int(0, 4_294_967_295, 1),
})

export interface SaveFile {
  schemaVersion: typeof SAVE_VERSION
  kind: 'save'
  game: GameState
  rng: number
}

export type SaveValidation = { ok: true; save: SaveFile } | { ok: false; error: string }

export function makeSave(game: GameState, rng: number): SaveFile {
  return { schemaVersion: SAVE_VERSION, kind: 'save', game, rng }
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

function tidyGame(game: GameState): GameState {
  if (game.monster) game.monster = tidyMonster(game.monster)
  game.songbook = [...new Set(game.songbook.filter((id) => TECHNIQUE_BY_ID[id] !== undefined))].sort()
  for (const id of Object.keys(game.inventory)) if (game.inventory[id]! <= 0) delete game.inventory[id]
  return game
}

function describeIssue(issue: v.BaseIssue<unknown>): string {
  const path = issue.path?.map((p) => String(p.key)).join('.') ?? ''
  return path ? `${path}: ${issue.message}` : issue.message
}

/** Migrate, validate and tidy any raw save. Never throws. */
export function validateSave(raw: unknown): SaveValidation {
  let migrated: unknown
  try {
    migrated = migrate(raw)
  } catch {
    return { ok: false, error: 'This save could not be read.' }
  }
  const parsed = v.safeParse(SaveSchema, migrated)
  if (!parsed.success) {
    const first = parsed.issues[0]
    return { ok: false, error: `This save is not valid (${describeIssue(first)}).` }
  }
  const output = parsed.output as unknown as SaveFile
  output.game = tidyGame(output.game)
  return { ok: true, save: output }
}

/** Validate a single monster (Monster Lab import). Never throws. */
export function validateMonster(raw: unknown): { ok: true; monster: Monster } | { ok: false; error: string } {
  const parsed = v.safeParse(MonsterSchema, raw)
  if (!parsed.success) return { ok: false, error: `This monster is not valid (${describeIssue(parsed.issues[0])}).` }
  return { ok: true, monster: tidyMonster(parsed.output as unknown as Monster) }
}

export { STAT_KEYS }
