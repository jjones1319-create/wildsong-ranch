import type { Drill, DrillId } from './types.ts'

/** CONTENT §4 and GAME_DESIGN §6.1. Six light drills (one per stat) and five heavy drills. */
export const DRILLS: readonly Drill[] = [
  { id: 'hill-sprints', name: 'Hill Sprints', kind: 'light', main: 'LIF', secondary: null, lowers: null, needsTrainingYard: false, vignette: 'Jogging up and down the grassy hill behind the barn' },
  { id: 'log-toss', name: 'Log Toss', kind: 'light', main: 'POW', secondary: null, lowers: null, needsTrainingYard: false, vignette: 'Heaving a log over a fence' },
  { id: 'puzzle-stones', name: 'Puzzle Stones', kind: 'light', main: 'INT', secondary: null, lowers: null, needsTrainingYard: false, vignette: 'Sliding carved stones into the right holes' },
  { id: 'target-toss', name: 'Target Toss', kind: 'light', main: 'SKI', secondary: null, lowers: null, needsTrainingYard: false, vignette: 'Throwing pinecones at a painted target' },
  { id: 'dodge-the-gourds', name: 'Dodge the Gourds', kind: 'light', main: 'SPD', secondary: null, lowers: null, needsTrainingYard: false, vignette: 'Dodging gourds that Wren swings on ropes' },
  { id: 'acorn-shower', name: 'Acorn Shower', kind: 'light', main: 'DEF', secondary: null, lowers: null, needsTrainingYard: false, vignette: 'Standing firm under a shaken oak tree' },
  { id: 'plow-pull', name: 'Plow Pull', kind: 'heavy', main: 'POW', secondary: 'LIF', lowers: 'SPD', needsTrainingYard: false, vignette: 'Dragging the old plow across the field' },
  { id: 'moon-meditation', name: 'Moon Meditation', kind: 'heavy', main: 'INT', secondary: 'SKI', lowers: 'DEF', needsTrainingYard: false, vignette: 'Sitting under the moon on a flat rock, very still' },
  { id: 'wind-chase', name: 'Wind Chase', kind: 'heavy', main: 'SPD', secondary: 'INT', lowers: 'POW', needsTrainingYard: false, vignette: "Chasing leaves in the windmill's gusts" },
  { id: 'waterfall-stand', name: 'Waterfall Stand', kind: 'heavy', main: 'DEF', secondary: 'LIF', lowers: 'INT', needsTrainingYard: false, vignette: 'Bracing under the little waterfall' },
  { id: 'quarry-haul', name: 'Quarry Haul', kind: 'heavy', main: 'LIF', secondary: 'DEF', lowers: 'SKI', needsTrainingYard: true, vignette: 'Hauling stones from the old quarry' },
]

export const DRILL_BY_ID = Object.fromEntries(DRILLS.map((d) => [d.id, d])) as Record<DrillId, Drill>
export const LIGHT_DRILLS = DRILLS.filter((d) => d.kind === 'light')
export const HEAVY_DRILLS = DRILLS.filter((d) => d.kind === 'heavy')
