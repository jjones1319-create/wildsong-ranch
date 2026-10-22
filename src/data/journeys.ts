import type { JourneySite, JourneySiteId } from './types.ts'

const ALL_YEAR = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

/** CONTENT §7 mentor sites. */
export const JOURNEY_SITES: readonly JourneySite[] = [
  { id: 'iron-quarry', name: 'Iron Quarry', mentor: 'Master Oduya', stat: 'POW', family: 'Heavy', openMonths: ALL_YEAR, gradeMin: null, trialBreeds: ['cobblemaw', 'reefclaw'] },
  { id: 'windrun-steppe', name: 'Windrun Steppe', mentor: 'Coach Lark', stat: 'SPD', family: 'Sharp', openMonths: [3, 4, 5, 6, 7, 8, 9, 10, 11], gradeMin: null, trialBreeds: ['galeheron', 'zipwisp'] },
  { id: 'starfall-observatory', name: 'Starfall Observatory', mentor: 'Sage Ilsabet', stat: 'INT', family: 'Wither', openMonths: ALL_YEAR, gradeMin: null, trialBreeds: ['wishlume', 'velvesper'] },
  { id: 'archers-glade', name: "Archer's Glade", mentor: 'Ranger Teo', stat: 'SKI', family: 'Hit', openMonths: ALL_YEAR, gradeMin: null, trialBreeds: ['quillion', 'tumblefox'] },
  { id: 'glacier-bastion', name: 'Glacier Bastion', mentor: 'Warden Brask', stat: 'DEF', family: 'Special', openMonths: [9, 10, 11, 12, 1, 2, 3, 4, 5], gradeMin: 'B', trialBreeds: ['moatshell', 'nimbusheep'] },
]

export const JOURNEY_SITE_BY_ID = Object.fromEntries(JOURNEY_SITES.map((s) => [s.id, s])) as Record<JourneySiteId, JourneySite>
