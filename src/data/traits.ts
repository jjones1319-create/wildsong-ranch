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
  { id: 'dragonheart', name: 'Dragonheart', description: 'Once per battle, when its HP first drops below 50%, it gains 20 guts' },
  { id: 'unshakable', name: 'Unshakable', description: "Can't be pushed back or stunned; damage taken −10%" },
  { id: 'underdog', name: 'Underdog', description: '+8 hit and +10% damage against opponents with a higher stat total' },
  { id: 'blessed', name: 'Blessed', description: 'Regenerates 1% of max HP every 5 seconds in battle' },
  { id: 'moonlit', name: 'Moonlit', description: 'Crit chance +6%' },
  { id: 'green-thumb', name: 'Green Thumb', description: 'Heal and drain techniques restore 50% more' },
  { id: 'eight-arms', name: 'Eight Arms', description: 'Multi-hit techniques get one extra hit' },
  { id: 'statue-pose', name: 'Statue Pose', description: 'After standing still for 2 seconds, takes 30% less damage until it moves' },
  { id: 'battering-ram', name: 'Battering Ram', description: 'Dashing costs no guts, and the first technique after a dash deals +15% damage' },
  { id: 'chill', name: 'Chill', description: "Its hits slow the target's walking by 25% for 3 seconds" },
]

export const TRAIT_BY_ID = Object.fromEntries(TRAITS.map((t) => [t.id, t])) as Record<TraitId, Trait>
