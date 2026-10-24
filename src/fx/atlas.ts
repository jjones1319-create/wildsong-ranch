/** The procedural texture atlas's frame indices (drawn in textures.ts). Pure constants so element styles need no Pixi. */
export const FRAME = {
  softDot: 0,
  spark: 1,
  droplet: 2,
  shard: 3,
  ring: 4,
  streak: 5,
  puff: 6,
  leaf: 7,
  petal: 8,
  note: 9,
  star: 10,
  rock: 11,
  coin: 12,
  bubble: 13,
  flake: 14,
  ember: 15,
} as const
export type FrameId = (typeof FRAME)[keyof typeof FRAME]
export const FRAME_COUNT = 16
/** Each frame is drawn in a cell this big (device pixels of the atlas). */
export const CELL = 64
export const ATLAS_COLS = 4
