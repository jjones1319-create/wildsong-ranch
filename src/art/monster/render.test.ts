import { describe, expect, it } from 'vitest'
import { makeMonster } from '../../core/test-helpers.ts'
import { BREED_BY_ID } from '../../data/breeds.ts'
import { STAGES } from '../../data/tuning.ts'
import { BODY_PLANS, BREED_IDS } from '../../data/types.ts'
import { EXPRESSIONS, expressionFromCues, faceFor } from './expressions.ts'
import { paletteFor } from './palettes.ts'
import { renderMonster, renderMonsterSvg, specForBreed, specFromMonster } from './render.ts'

function tagBalance(svg: string, tag: string): number {
  const opens = svg.match(new RegExp(`<${tag}[\\s>]`, 'g'))?.length ?? 0
  const closes = svg.match(new RegExp(`</${tag}>`, 'g'))?.length ?? 0
  return opens - closes
}

function expectClean(svg: string) {
  expect(svg.startsWith('<svg')).toBe(true)
  expect(svg.endsWith('</svg>')).toBe(true)
  expect(svg).not.toMatch(/NaN|undefined|\[object|Infinity/)
  expect(tagBalance(svg, 'svg')).toBe(0)
  expect(tagBalance(svg, 'g')).toBe(0)
}

describe('procedural monster art (§22)', () => {
  it('renders every main/sub pair cleanly (400 combinations)', () => {
    for (const main of BREED_IDS) {
      for (const sub of BREED_IDS) {
        const svg = renderMonsterSvg(specForBreed(main, { sub }))
        expectClean(svg)
        expect(svg.length).toBeGreaterThan(800)
      }
    }
  })

  it('uses all nine body plans across the twenty breeds', () => {
    const plans = new Set(BREED_IDS.map((id) => BREED_BY_ID[id].art.plan))
    for (const plan of BODY_PLANS) expect(plans.has(plan)).toBe(true)
  })

  it('wears the sub palette with the main eyes, and attaches the sub accent part', () => {
    const pure = renderMonsterSvg(specForBreed('puddlepup'))
    const mixed = renderMonsterSvg(specForBreed('puddlepup', { sub: 'lootlid' }))
    expect(mixed).not.toBe(pure)
    expect(mixed).toContain(BREED_BY_ID.lootlid.art.palette.body)
    expect(mixed).toContain(BREED_BY_ID.puddlepup.art.palette.eye)
    expect(mixed).not.toContain(BREED_BY_ID.puddlepup.art.palette.body)
    expect(mixed).toContain(BREED_BY_ID.lootlid.art.palette.accent)
    expect(mixed.length).toBeGreaterThan(pure.length)
  })

  it('reads the palette and expression from a real monster', () => {
    const m = makeMonster({ main: 'coilfang', sub: 'wishlume' })
    expect(paletteFor(m).body).toBe(BREED_BY_ID.wishlume.art.palette.body)
    expect(paletteFor(m).eye).toBe(BREED_BY_ID.coilfang.art.palette.eye)
    const spec = specFromMonster(m)
    expect(spec.accentBreed).toBe('wishlume')
    expect(spec.expression).toBe('neutral')
    m.fatigue = 90
    m.stress = 60
    expect(specFromMonster(m).expression).toBe('tired')
    m.fatigue = 0
    expect(specFromMonster(m).expression).toBe('stressed')
    m.status.sickWeeks = 1
    expect(specFromMonster(m).expression).toBe('sick')
    m.spoil = 100
    m.fear = 100
    expect(specFromMonster(m).sparkle).toBe(true)
    m.nature = -80
    expect(specFromMonster(m).mischief).toBe(true)
    expect(specFromMonster(m, { expression: 'happy', sparkle: false }).expression).toBe('happy')
    expectClean(renderMonster(m))
  })

  it('draws every expression, the sweat drop, the sick tint and the sparkle', () => {
    for (const expression of EXPRESSIONS) {
      for (const breed of ['puddlepup', 'galeheron', 'nibblegrub', 'ashwraith', 'lootlid'] as const) {
        const svg = renderMonsterSvg(specForBreed(breed, { expression }))
        expectClean(svg)
        expect(svg.includes('ws-mon__sweat')).toBe(expression === 'stressed')
      }
    }
    expect(renderMonsterSvg(specForBreed('puddlepup', { sparkle: true }))).toContain('ws-mon__sparkle')
    expect(renderMonsterSvg(specForBreed('puddlepup', { expression: 'sick' }))).toContain('#7faf5a')
    expect(renderMonsterSvg(specForBreed('nimbusheep', { expression: 'happy' }))).toContain('#8FB8F2')
    expect(renderMonsterSvg(specForBreed('puddlepup', { mischief: true }))).not.toBe(renderMonsterSvg(specForBreed('puddlepup')))
    expect(faceFor('tired', 'beak', false).mouth).toBeNull()
    expect(faceFor('tired', 'smile', false).mouth).toBe('flat')
    expect(faceFor('neutral', 'smile', true)).toMatchObject({ eyes: 'narrow', mouth: 'grin' })
    expect(expressionFromCues(['droopy', 'sweat', 'sparkle'])).toEqual({ expression: 'tired', sparkle: true, mischief: false })
    expect(expressionFromCues(['sick', 'grin'])).toEqual({ expression: 'sick', sparkle: false, mischief: true })
    expect(expressionFromCues([])).toEqual({ expression: 'neutral', sparkle: false, mischief: false })
  })

  it('sizes by life stage and marks old monsters', () => {
    const small = renderMonsterSvg(specForBreed('tumblefox', { stage: 1 }))
    const medium = renderMonsterSvg(specForBreed('tumblefox', { stage: 3 }))
    const full = renderMonsterSvg(specForBreed('tumblefox', { stage: 5 }))
    const old = renderMonsterSvg(specForBreed('tumblefox', { stage: STAGES.visiblyOld }))
    expect(small).toContain(`scale(${STAGES.sizePct.smallPct / 100})`)
    expect(medium).toContain(`scale(${STAGES.sizePct.mediumPct / 100})`)
    expect(full).toContain('scale(1)')
    expect(full).not.toContain('ws-mon--old')
    expect(old).toContain('ws-mon--old')
  })

  it('honours the animate flag, the size, the label and mirroring', () => {
    const on = renderMonsterSvg(specForBreed('zipwisp'), { size: 96, label: 'Zappy' })
    const off = renderMonsterSvg(specForBreed('zipwisp', { animate: false }))
    expect(on).toContain('data-animate="true"')
    expect(on).toContain('width="96"')
    expect(on).toContain('aria-label="Zappy"')
    expect(on).toContain('ws-mon__jitter')
    expect(off).toContain('data-animate="false"')
    expect(renderMonsterSvg(specForBreed('quillion'), { mirror: true })).toContain('scale(-1 1)')
    expect(renderMonsterSvg(specForBreed('wishlume'))).toContain('ws-mon__float')
    expect(renderMonsterSvg(specForBreed('puddlepup'))).toContain('ws-mon__bob')
  })
})
