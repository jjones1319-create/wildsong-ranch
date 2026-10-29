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
  Perfect: 'PERFECT!',
  Superb: 'Superb!',
  Great: 'Great!',
  Good: 'Good',
  Success: 'Fine',
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

/** §12.10 CPU personalities, in plain words. */
export const PERSONALITY_LABELS = {
  Steady: { name: 'Steady', blurb: 'Attacks at an even pace and saves up for big moves.' },
  Aggressive: { name: 'Aggressive', blurb: 'Attacks often, even when low on guts.' },
  Cautious: { name: 'Cautious', blurb: 'Waits for a full tank, then hits hard.' },
  Trickster: { name: 'Trickster', blurb: 'Loves Wither techniques that drain your guts.' },
  Sniper: { name: 'Sniper', blurb: 'Keeps its distance and fights from Far.' },
  Brawler: { name: 'Brawler', blurb: 'Walks straight in and fights up Close.' },
} as const

/** §12.11 (M10) the player's Auto styles. */
/** V1 effects: Settings → Graphics. */
export const FX_QUALITY_LABELS = {
  auto: { name: 'Auto', blurb: 'Picks the best your phone can draw smoothly, and remembers it.' },
  ultra: { name: 'Ultra', blurb: 'Every particle, every shimmer. For the newest phones.' },
  high: { name: 'High', blurb: 'Plenty of sparks, the glow kept, the heavy shimmer off.' },
  lite: { name: 'Lite', blurb: 'The essentials only. Easy on older phones and the battery.' },
} as const

export const FX_INTENSITY_LABELS = {
  cozy: { name: 'Cozy', blurb: 'Gentle. No shaking, no flashing, soft sparks.' },
  standard: { name: 'Standard', blurb: 'A little shake and a quick flash on the big hits.' },
  flashy: { name: 'Flashy', blurb: 'Big hits stop the world for a blink, shake the arena and flash.' },
} as const

/** Art 2.0: Settings → Graphics → Monsters. */
export const MONSTER_MODE_LABELS = {
  '3d': { name: '3D', blurb: 'The new living monsters, built in Blender. A breed that isn’t rebuilt yet still shows its Classic drawing.' },
  classic: { name: 'Classic', blurb: 'The hand-drawn look everywhere. Lightest on the battery.' },
} as const

export const ELEMENT_LABELS = {
  Fire: 'Fire',
  Water: 'Water',
  Ice: 'Ice',
  Lightning: 'Lightning',
  Wind: 'Wind',
  Earth: 'Earth',
  Nature: 'Nature',
  Light: 'Light',
  Dark: 'Dark',
  Sound: 'Sound',
  Physical: 'Physical',
} as const

export const AUTO_STYLE_LABELS = {
  balanced: { name: 'Balanced', blurb: 'Plays the odds: steps in when the trade is good, steps back when it is not.' },
  aggressive: { name: 'Aggressive', blurb: 'Closes in and spends guts on big hits.' },
  defensive: { name: 'Defensive', blurb: 'Keeps its distance and plays it safe.' },
} as const

export const BAND_LABELS = { 1: 'Close', 2: 'Near', 3: 'Mid', 4: 'Far', 5: 'Out of range' } as const

/** §13 formats (CONTENT §9). */
export const FORMAT_LABELS = { RR4: 'Round robin of 4', RR6: 'Round robin of 6', Elim4: 'Elimination of 4', Elim8: 'Elimination of 8', '1v1': 'Single match', Relay: 'Team relay' } as const

export const EVENT_KIND_LABELS = { cup: 'Cup', official: 'Official', crown: 'Crown', legend: 'Legend Cup', open: 'Open', summitQualifier: 'Qualifier', summit: 'Summit', rival: 'Rival match', masquerade: 'Invitational' } as const

/** §3 the calendar's icons: one per group of event kinds (the Year view's tiles use the groups). */
export const EVENT_KIND_ICONS = { cup: '🏆', official: '🎖', crown: '👑', legend: '💌', open: '🎪', summitQualifier: '⛰', summit: '⛰', rival: '💌', masquerade: '💌' } as const
export const EXPEDITION_ICON = '🧭'
export const CALENDAR_NOTE_ICONS = { crown: '👑', legend: '🌟', market: '🐾', upgrades: '🔨', birthday: '🎂' } as const

export const FAMILY_LABELS = { Basic: 'Basic', Hit: 'Hit', Heavy: 'Heavy', Wither: 'Wither', Sharp: 'Sharp', Special: 'Special', Chain: 'Chain', Signature: 'Signature' } as const

export const RANGE_LABELS = { 1: 'Close', 2: 'Near', 3: 'Mid', 4: 'Far' } as const
