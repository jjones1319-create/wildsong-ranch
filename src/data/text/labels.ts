/** Player-facing words for the hidden-state labels (GAME_DESIGN §6.4, §6.6), stages, seasons, weather and outcomes. */

export const FATIGUE_LABELS = ['Bright-eyed', 'Fine', 'A bit tired', 'Tired', 'Exhausted', 'About to collapse'] as const
export const STRESS_LABELS = ['Carefree', 'Calm', 'A little tense', 'Stressed', 'Very stressed', 'At breaking point'] as const
export const LOYALTY_LABELS = ['Distant', 'Wary', 'Friendly', 'Devoted', 'Inseparable'] as const

export const STYLE_LABELS = {
  doting: 'Doting',
  fond: 'Fond',
  gentle: 'Gentle',
  even: 'Even',
  firm: 'Firm',
  strict: 'Strict',
  spartan: 'Spartan',
} as const

export const STAGE_NAMES = ['Hatchling', 'Youngling', 'Juvenile', 'Adolescent', 'Prime', 'Late Prime', 'Mature', 'Elder', 'Venerable', 'Twilight'] as const

/** The six stats (GAME_DESIGN §5.1): the code the docs use, plus a plain word. */
export const STAT_NAMES = { LIF: 'Life', POW: 'Power', INT: 'Intellect', SKI: 'Skill', SPD: 'Speed', DEF: 'Defense' } as const

export const GROWTH_WORDS = { Early: 'Early bloomer', Steady: 'Steady', Late: 'Late bloomer', Evergreen: 'Evergreen' } as const

export const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'] as const
export const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const

export const SEASON_NAMES = { Winter: 'Winter', Spring: 'Spring', Summer: 'Summer', Autumn: 'Autumn' } as const

/** Weather words and a plain glyph for the calendar strip (never colour alone, §24). */
export const WEATHER_LABELS = { Sunny: 'Sunny', Cloudy: 'Cloudy', Rain: 'Rain', Storm: 'Storm', Snow: 'Snow' } as const
export const WEATHER_GLYPHS = { Sunny: '☀', Cloudy: '☁', Rain: '☂', Storm: '⚡', Snow: '❄' } as const

export const OUTCOME_BANNERS = {
  Great: 'Great!',
  Success: 'Success',
  Cheat: 'Cheated…',
  Fail: 'Failed',
  Slacked: 'Slacked off',
} as const

/** Guided-mode odds words for the best outcome chance (Great + Success). */
export const ODDS_WORDS = { eager: 'Looks eager', likely: 'Likely', risky: 'Risky', veryRisky: 'Very risky' } as const

/** §7 difficulty modes, in plain words. */
export const DIFFICULTY_LABELS = {
  Gentle: { name: 'Gentle', blurb: 'No death: old monsters retire to the Elder Grove. Strain costs half, breakdowns are rare, prizes pay more.' },
  Standard: { name: 'Standard', blurb: 'The game as designed. Monsters pass away of old age; care decides how long they live.' },
  Classic: { name: 'Classic', blurb: 'Strain costs more, one item per week by default, and a knockout while exhausted can be fatal. Locked in once chosen.' },
} as const

export const TRANSPARENCY_LABELS = {
  classic: { name: 'Classic', blurb: "Wren's words, expressions and the life bar. No numbers, no odds." },
  guided: { name: 'Guided', blurb: 'Labelled bars for fatigue, stress, loyalty and life. Drill odds as words.' },
  lens: { name: "Breeder's Lens", blurb: 'Exact numbers everywhere: hidden stats, strain, weeks left, drill odds.' },
} as const

export const SPEED_LABELS = { normal: 'Normal', fast: 'Fast', instant: 'Instant' } as const

export const ITEM_CATEGORY_LABELS = {
  recovery: 'Recovery',
  mood: 'Mood',
  form: 'Form',
  sweet: 'Stat Sweets',
  potential: 'Potential',
  tonic: 'Tonics',
  fruit: 'Life fruit',
  toy: 'Toys',
  charm: 'Charms',
  catalyst: 'Fusion catalysts',
  key: 'Key items',
  sellable: 'Treasures',
} as const

export const FAMILY_LABELS = { Basic: 'Basic', Hit: 'Hit', Heavy: 'Heavy', Wither: 'Wither', Sharp: 'Sharp', Special: 'Special', Chain: 'Chain', Signature: 'Signature' } as const

export const RANGE_LABELS = { 1: 'Close', 2: 'Near', 3: 'Mid', 4: 'Far' } as const
