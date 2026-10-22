import type { Trait, TraitId } from './types.ts'

/** CONTENT §2.1. The numbers behind each trait live in tuning.ts (raising) and the battle code (M4). */
export const TRAITS: readonly Trait[] = [
  { id: 'cheerful', name: 'Cheerful', description: 'Stress from scolding −50%' },
  { id: 'nimble', name: 'Nimble', description: 'Counts as +50 SPD when being targeted' },
  { id: 'heavy-hitter', name: 'Heavy Hitter', description: 'Heavy-family techniques +15% damage' },
  { id: 'fortified', name: 'Fortified', description: 'All damage taken −20%' },
  { id: 'glow', name: 'Glow', description: '+6 hit with Far (range 4) techniques' },
  { id: 'en-garde', name: 'En Garde', description: '+8 hit with Near (range 2) techniques' },
  { id: 'hot-blooded', name: 'Hot-Blooded', description: '+15% damage while own HP ≤ 50%' },
  { id: 'big-appetite', name: 'Big Appetite', description: 'Monthly food effects ×1.5 (good and bad)' },
  { id: 'quick-study', name: 'Quick Study', description: '+10% Journey technique chance' },
  { id: 'fluffy', name: 'Fluffy', description: 'Rest removes 8 more fatigue' },
  { id: 'tailwind', name: 'Tailwind', description: 'Walk and dash speed +20%' },
  { id: 'hungry-grub', name: 'Hungry Grub', description: 'Food form changes ×1.5; can cocoon' },
  { id: 'moth-dust', name: 'Moth Dust', description: "Opponents' crit chance against it ×0.5" },
  { id: 'ethereal', name: 'Ethereal', description: 'Wither taken ×0.7' },
  { id: 'live-wire', name: 'Live Wire', description: 'Guts regen +25% while guts < 30' },
  { id: 'reflective', name: 'Reflective', description: '15% chance to reflect 30% of INT damage taken' },
  { id: 'clockwork', name: 'Clockwork', description: 'Drill fatigue −20%' },
  { id: 'hard-shell', name: 'Hard Shell', description: 'POW damage taken −15%' },
  { id: 'gilded', name: 'Gilded', description: 'Tournament prizes +15%; chore pay ×2' },
  { id: 'regal', name: 'Regal', description: '+5 extra fame per tournament win; +5 to the fame-crit cap' },
]

export const TRAIT_BY_ID = Object.fromEntries(TRAITS.map((t) => [t.id, t])) as Record<TraitId, Trait>
