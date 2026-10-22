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

export const OUTCOME_BANNERS = {
  Great: 'Great!',
  Success: 'Success',
  Cheat: 'Cheated…',
  Fail: 'Failed',
  Slacked: 'Slacked off',
} as const

/** Guided-mode odds words for the best outcome chance (Great + Success). */
export const ODDS_WORDS = { eager: 'Looks eager', likely: 'Likely', risky: 'Risky', veryRisky: 'Very risky' } as const
