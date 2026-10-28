import type { KeepsakeId } from './types.ts'

/** CONTENT §4.2 keepsakes: found on a Bond week's shopping trip, bought once, kept on the ranch for good. */
export interface Keepsake {
  id: KeepsakeId
  name: string
  price: number
  /** One line for the shop stall and the ranch card. */
  blurb: string
}

export const KEEPSAKES: readonly Keepsake[] = [
  { id: 'kick-ball', name: 'Kick Ball', price: 400, blurb: 'A big soft ball for kicking around the yard.' },
  { id: 'pinwheel', name: 'Pinwheel', price: 450, blurb: 'Spins and whirs in the slightest breeze.' },
  { id: 'star-plush', name: 'Star Plush', price: 500, blurb: 'A soft star to cuddle at night.' },
  { id: 'wind-chime', name: 'Wind Chime', price: 600, blurb: 'Shell and wood chimes that sing in the wind.' },
  { id: 'puzzle-board', name: 'Puzzle Board', price: 800, blurb: 'Wooden pegs and sliding blocks to fiddle with.' },
  { id: 'hay-hammock', name: 'Hay Hammock', price: 900, blurb: 'A swinging bed of sweet hay between two posts.' },
  { id: 'climbing-stump', name: 'Climbing Stump', price: 1000, blurb: 'A gnarled old stump, perfect for clambering.' },
  { id: 'splash-tub', name: 'Splash Tub', price: 1100, blurb: 'A wide wooden tub of cool water for paddling.' },
  { id: 'kite-post', name: 'Kite Post', price: 1300, blurb: 'A tall post with a bright kite tied to the top.' },
  { id: 'story-blocks', name: 'Story Blocks', price: 1500, blurb: 'Painted blocks that stack into little towers and towns.' },
]

export const KEEPSAKE_BY_ID = Object.fromEntries(KEEPSAKES.map((k) => [k.id, k])) as Record<KeepsakeId, Keepsake>
