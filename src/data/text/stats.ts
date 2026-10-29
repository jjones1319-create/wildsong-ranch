import type { StatKey } from '../types.ts'

/**
 * The stats guide (v1.11): what each stat does, in Wren's voice. Opened from the Monster Card ("What do stats
 * do?" or a tap on any stat) and as the Journal's Stats page. Rules: GAME_DESIGN §5, §8, §12 and §17.
 */
export const STATS_GUIDE = {
  title: 'What do stats do?',
  journalPage: 'Stats',
  intro: 'Six stats make a monster. Here’s what each one does, and how to grow it. Tap any stat on a Monster Card to come back here.',
  stats: {
    LIF: {
      does: 'Life is health. A monster has as much HP in a fight as it has Life, so more Life means it can take more hits.',
      also: 'On expeditions, Life is stamina: more steps before you have to head home.',
    },
    POW: {
      does: 'Power makes POW techniques hit harder, and helps shrug off POW techniques.',
      also: 'On expeditions, Power moves boulders and tears through brambles.',
    },
    INT: {
      does: 'Intellect makes INT techniques hit harder, and helps shrug off INT techniques.',
      also: 'On expeditions, Intellect solves riddle doors, finds hidden things and keeps you from getting lost.',
    },
    SKI: {
      does: 'Skill is aim. The more Skill, the more often techniques land.',
      also: 'On expeditions, Skill gets you past traps and snares.',
    },
    SPD: {
      does: 'Speed dodges attacks and walks faster around the arena, so it’s easier to pick your distance.',
      also: 'On expeditions, Speed jumps the gaps. In Meadow Dash, every tap goes a little further.',
    },
    DEF: {
      does: 'Defense softens every hit, POW or INT alike.',
      also: 'On expeditions, Defense braves the winds and hazards.',
    },
  } satisfies Record<StatKey, { does: string; also: string }>,
  labels: { does: 'In a fight', also: 'Elsewhere', grow: 'Grows with', growLittle: 'A little from', journeys: 'Journeys', everyJourney: 'Every Journey adds a little' },
  growTitle: 'Grades, caps and sweets',
  grades: 'Every stat has a growth grade: E, D, C, B, A, then S at the top. The better the grade, the more that stat grows from each drill and Journey.',
  caps: 'Each grade also sets how high training can take a stat: {caps}.',
  sweets: 'Stat Sweets always work, even past the cap. On the card they’re the lighter part of the bar.',
  pearl: 'A Potential Pearl raises one grade a step, and lifts that stat’s cap with it.',
  close: 'Got it',
} as const
