import { describe, expect, it } from 'vitest'
import { trialGateOpen } from './gates.ts'

const journey = (pendingTechnique: string | null) => ({ site: 'iron-quarry', weekNo: 2, successes: 0, learned: null, pendingTechnique, gains: { LIF: 0, POW: 0, INT: 0, SKI: 0, SPD: 0, DEF: 0 }, elderMentor: false })

describe('the ranch trial gate', () => {
  it('is closed with no journey, no trial and no outcome (the storm-spark soft-lock)', () => {
    expect(trialGateOpen({ trial: null, journey: null }, false)).toBe(false)
  })

  it('is closed on a journey with no technique waiting', () => {
    expect(trialGateOpen({ trial: null, journey: journey(null) as never }, false)).toBe(false)
  })

  it('opens for a technique waiting to be learned, a trial in progress, or an outcome to show', () => {
    expect(trialGateOpen({ trial: null, journey: journey('universal.beat-bump') as never }, false)).toBe(true)
    expect(trialGateOpen({ trial: { site: 'iron-quarry', pendingTechnique: null }, journey: null }, false)).toBe(true)
    expect(trialGateOpen({ trial: null, journey: null }, true)).toBe(true)
  })
})
