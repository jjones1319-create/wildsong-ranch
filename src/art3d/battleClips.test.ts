import { describe, expect, it } from 'vitest'
import { ART } from '../data/tuning.ts'
import { battleClipFor, IDLE_SIGNALS, locomotionRate, ranchActionFor, ranchIdleFor, type FighterSignals } from './battleClips.ts'
import { STAR_CLIPS } from './types.ts'

const DASH = 300
const sig = (o: Partial<FighterSignals>): FighterSignals => ({ ...IDLE_SIGNALS, ...o })

describe('battle flags → ★ clips (ART_2_PLAN §5, battles until P11)', () => {
  it('follows the priority order', () => {
    expect(battleClipFor(sig({ ko: true, win: true, hit: true }), DASH).clip).toBe('ko')
    expect(battleClipFor(sig({ win: true, hit: true }), DASH)).toMatchObject({ clip: 'win', face: 'happy' })
    expect(battleClipFor(sig({ hitHeavy: true, hit: true, lunge: true }), DASH)).toMatchObject({ clip: 'hit_heavy', face: 'strain', kind: 'hit' })
    expect(battleClipFor(sig({ hit: true, lunge: true }), DASH)).toMatchObject({ clip: 'hit', face: 'surprised' })
    expect(battleClipFor(sig({ stunned: true, busy: true }), DASH)).toMatchObject({ clip: 'dizzy', face: 'dizzy' })
    expect(battleClipFor(sig({ busy: true, lunge: true }), DASH)).toMatchObject({ clip: 'strike', face: 'angry', kind: 'action' })
    expect(battleClipFor(sig({ shove: true }), DASH).clip).toBe('shove')
    expect(battleClipFor(sig({ busy: true, ranged: true }), DASH).clip).toBe('cast')
    expect(battleClipFor(sig({ busy: true }), DASH).clip).toBe('strike')
  })

  it('moves: dash by flag or speed, steps by direction relative to facing, idle when standing', () => {
    expect(battleClipFor(sig({ dash: true }), DASH)).toMatchObject({ clip: 'dash', speedDriven: true })
    expect(battleClipFor(sig({ vx: -DASH * ART.arena.dashShare }), DASH).clip).toBe('dash')
    expect(battleClipFor(sig({ vx: 60, facing: 1 }), DASH).clip).toBe('step_fwd')
    expect(battleClipFor(sig({ vx: -60, facing: 1 }), DASH).clip).toBe('step_back')
    expect(battleClipFor(sig({ vx: -60, facing: -1 }), DASH).clip).toBe('step_fwd')
    expect(battleClipFor(sig({ vx: 2 }), DASH)).toMatchObject({ clip: 'battle_idle', kind: 'idle' })
    expect(battleClipFor(sig({ dawdling: true, vx: 60 }), DASH).clip).toBe('look_around')
  })

  it('the idle carries the screen face or tired when low', () => {
    expect(battleClipFor(sig({ lowHp: true, expression: 'happy' }), DASH).face).toBe('tired')
    expect(battleClipFor(sig({ expression: 'happy' }), DASH).face).toBe('happy')
    expect(battleClipFor(sig({}), DASH).face).toBeNull()
  })

  it('every clip it names is a ★ clip', () => {
    const cases: Partial<FighterSignals>[] = [{ ko: true }, { win: true }, { hitHeavy: true }, { hit: true }, { stunned: true }, { lunge: true }, { shove: true }, { busy: true, ranged: true }, { busy: true }, { dash: true }, { dawdling: true }, { vx: 50 }, { vx: -50 }, {}]
    for (const c of cases) expect(STAR_CLIPS).toContain(battleClipFor(sig(c), DASH).clip)
  })
})

describe('ranch idles and actions', () => {
  it('picks the mood idle from the expression and sleep over everything', () => {
    expect(ranchIdleFor('neutral', false, true)).toBe('sleep')
    expect(ranchIdleFor('sick', true, false)).toBe('idle_sick')
    expect(ranchIdleFor('tired', false, false)).toBe('idle_tired')
    expect(ranchIdleFor('sad', false, false)).toBe('idle_sad')
    expect(ranchIdleFor('neutral', true, false)).toBe('idle_happy')
    expect(ranchIdleFor('neutral', false, false)).toBe('idle')
  })

  it('actions follow the tuned weights and are ★ clips', () => {
    const seen = new Set<string>()
    for (let r = 0; r < 1; r += 0.01) seen.add(ranchActionFor(r))
    expect([...seen].sort()).toEqual(Object.keys(ART.anim.actWeights).sort())
    for (const c of seen) expect(STAR_CLIPS).toContain(c)
  })

  it('locomotion rate follows the real speed within the clamp', () => {
    expect(locomotionRate(40, 40)).toBe(1)
    expect(locomotionRate(400, 40)).toBe(ART.anim.rateMax)
    expect(locomotionRate(1, 40)).toBe(ART.anim.rateMin)
    expect(locomotionRate(50, 0)).toBe(1)
  })
})
