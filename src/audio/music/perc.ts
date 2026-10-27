/**
 * SOUND_UPGRADE §6.4: percussion lines are step strings, one bar per segment (segments separated by `|` or
 * spaces): `X` accent, `x` normal, `o` ghost, `.` rest. `grid` is the steps per bar (16 for 4/4, 12 for 3/4
 * and 6/8). Battle songs write their lines by role and a kit maps roles to instruments. Pure.
 */
import { beatsPerBar } from './abc.ts'
import type { GenEvent } from './patterns.ts'

export const STEP_VEL: Record<string, number> = { X: 0.9, x: 0.6, o: 0.3 }

export function parseSteps(steps: string): string[] {
  const segments = steps
    .split(/[|\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  for (const seg of segments) if (!/^[Xxo.]+$/.test(seg)) throw new Error(`bad step string "${seg}": use X x o and .`)
  return segments
}

/** Default grid for a meter: 16 steps in 4/4 and 2/4 (8), 12 in 3/4, 6/8 and 9/8 (18), 24 in 12/8. */
export function defaultGrid(meter: readonly [number, number]): number {
  if (meter[1] === 8) return meter[0] * 2
  return meter[0] * 4
}

/** The hits of a step string over `bars` bars; segments cycle. Every segment must fit the grid. */
export function percEvents(steps: string, grid: number, bars: number, meter: readonly [number, number]): GenEvent[] {
  const segments = parseSteps(steps)
  const beats = beatsPerBar(meter)
  const stepBeats = beats / grid
  const out: GenEvent[] = []
  for (const seg of segments) if (seg.length !== grid) throw new Error(`step string "${seg}" has ${seg.length} steps, the grid is ${grid}`)
  for (let bar = 0; bar < bars; bar++) {
    const seg = segments[bar % segments.length]!
    for (let i = 0; i < seg.length; i++) {
      const ch = seg[i]!
      if (ch === '.') continue
      out.push({ bar, t: i * stepBeats, dur: stepBeats, pitches: [], vel: STEP_VEL[ch]! })
    }
  }
  return out
}
