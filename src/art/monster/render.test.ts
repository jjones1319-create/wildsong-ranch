import { describe, expect, it } from 'vitest'
import { makeMonster } from '../../core/test-helpers.ts'
import { BREED_BY_ID } from '../../data/breeds.ts'
import { STAGES } from '../../data/tuning.ts'
import { BODY_PLANS, BREED_IDS, type BreedId } from '../../data/types.ts'
import { EXPRESSIONS, expressionFromCues, faceFor } from './expressions.ts'
import { POLISH } from './looks.ts'
import { buildPalette } from './palettes.ts'
import { formForStage, hasGrownForm, renderMonster, renderMonsterSvg, specForBreed, specFromMonster } from './render.ts'

const NEW = BREED_IDS.slice(20) as BreedId[]
const GROWING: BreedId[] = ['hearthwing', 'pluckrex', 'paladove']

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
  expect(tagBalance(svg, 'defs')).toBe(0)
}

describe('procedural monster art (§22)', () => {
  it('renders every breed cleanly at every life stage', () => {
    for (const breed of BREED_IDS) {
      for (let stage = 1; stage <= STAGES.count; stage++) {
        const svg = renderMonsterSvg(specForBreed(breed, { stage }))
        expectClean(svg)
        expect(svg.length).toBeGreaterThan(1500)
      }
    }
  })

  it('uses all nine body plans across the thirty breeds', () => {
    const plans = new Set(BREED_IDS.map((id) => BREED_BY_ID[id].art.plan))
    for (const plan of BODY_PLANS) expect(plans.has(plan)).toBe(true)
  })

  it("every breed wears its own palette and eyes, and no other breed's", () => {
    for (const breed of BREED_IDS) {
      const svg = renderMonsterSvg(specForBreed(breed))
      const pal = BREED_BY_ID[breed].art.palette
      expect(svg).toContain(pal.body)
      expect(svg).toContain(pal.eye)
    }
    expect(renderMonsterSvg(specForBreed('puddlepup'))).not.toContain(BREED_BY_ID.lootlid.art.palette.body)
  })

  it('a secret variant wears its own colours instead of its breed palette', () => {
    const m = makeMonster({ main: 'puddlepup' })
    const plain = renderMonsterSvg(specFromMonster(m, { animate: false }))
    m.variantId = 'songheart-puddlepup'
    const special = renderMonsterSvg(specFromMonster(m, { animate: false }))
    expect(special).not.toBe(plain)
    expect(special).toContain('#5FC7B0')
    expect(special).not.toContain(BREED_BY_ID.puddlepup.art.palette.body)
    m.variantId = 'not-a-variant'
    expect(renderMonsterSvg(specFromMonster(m, { animate: false }))).toBe(plain)
  })

  it('reads the palette and expression from a real monster', () => {
    const m = makeMonster({ main: 'coilfang' })
    const spec = specFromMonster(m)
    expect(spec.mainBreed).toBe('coilfang')
    expect(spec.eyeColor).toBe(BREED_BY_ID.coilfang.art.palette.eye)
    expect(renderMonsterSvg(spec)).toBe(renderMonsterSvg(specForBreed('coilfang', { stage: spec.stage })))
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

describe('breeds 21–30 and the growth forms (NEW_MONSTERS §3, §5)', () => {
  it('renders every new breed at every stage and expression', () => {
    for (const breed of NEW) {
      for (let stage = 1; stage <= STAGES.count; stage++) expectClean(renderMonsterSvg(specForBreed(breed, { stage })))
      for (const expression of EXPRESSIONS) expectClean(renderMonsterSvg(specForBreed(breed, { expression, sparkle: expression === 'happy' })))
    }
  })

  it('switches the three growing breeds to their grown look at Prime, and nobody else', () => {
    for (const breed of BREED_IDS) expect(hasGrownForm(breed)).toBe(GROWING.includes(breed))
    for (const breed of GROWING) {
      expect(formForStage(breed, STAGES.prime[0]! - 1)).toBe('young')
      expect(formForStage(breed, STAGES.prime[0]!)).toBe('grown')
      expect(formForStage(breed, STAGES.count)).toBe('grown')
      const strip = (svg: string) => svg.replace(/scale\([\d.]+\)/g, 'scale(S)')
      const young = strip(renderMonsterSvg(specForBreed(breed, { stage: 4 })))
      const grown = strip(renderMonsterSvg(specForBreed(breed, { stage: 5 })))
      expect(young).not.toBe(grown)
      expect(grown.length).toBeGreaterThan(young.length)
    }
    expect(formForStage('puddlepup', 10)).toBe('young')
    const m = makeMonster({ main: 'hearthwing' })
    m.lifespanTotal = 100
    m.ageWeeks = 50
    expect(formForStage(m.mainBreed, specFromMonster(m).stage)).toBe('young')
    m.ageWeeks = 60
    expect(formForStage(m.mainBreed, specFromMonster(m).stage)).toBe('grown')
  })

})

describe('high-end polish (NEW_MONSTERS §6)', () => {
  it('paints with gradients whose ids follow the palette', () => {
    const a = buildPalette(BREED_BY_ID.puddlepup.art.palette, undefined, { gradients: true })
    const b = buildPalette(BREED_BY_ID.coilfang.art.palette, undefined, { gradients: true })
    const flat = buildPalette(BREED_BY_ID.puddlepup.art.palette)
    expect(a.id).not.toBe(b.id)
    expect(a.id).toBe(buildPalette(BREED_BY_ID.puddlepup.art.palette, undefined, { gradients: true }).id)
    expect(a.paint(a.body)).toBe(`url(#${a.id}-b)`)
    expect(a.paint('#123456')).toBe('#123456')
    expect(flat.paint(flat.body)).toBe(flat.body)
    const svg = renderMonsterSvg(specForBreed('puddlepup'))
    expect(svg).toContain('<defs>')
    expect(svg).toContain(`id="${a.id}-b"`)
    expect(svg).toContain(`url(#${a.id}-b)`)
    expect(svg).toContain(`url(#${a.id}-s)`)
  })

  it('adds the texture pattern only for breeds that have one', () => {
    for (const breed of BREED_IDS) {
      const svg = renderMonsterSvg(specForBreed(breed))
      expect(svg.includes('<pattern')).toBe(POLISH[breed].texture !== null)
    }
  })

  it('draws signature particles, and drops them in lite mode or for a static picture', () => {
    for (const breed of BREED_IDS) {
      const svg = renderMonsterSvg(specForBreed(breed))
      expect(svg.includes('ws-mon__particles')).toBe(POLISH[breed].particles !== null)
    }
    expect(renderMonsterSvg(specForBreed('hearthwing', { lite: true }))).not.toContain('ws-mon__particles')
    expect(renderMonsterSvg(specForBreed('hearthwing', { lite: true }))).toContain('ws-mon--lite')
    expect(renderMonsterSvg(specForBreed('hearthwing', { animate: false }))).not.toContain('ws-mon__particles')
    expect(renderMonsterSvg(specForBreed('hearthwing', { particles: false }))).not.toContain('ws-mon__particles')
    const m = makeMonster({ main: 'frostlance' })
    expect(specFromMonster(m, { animate: false }).particles).toBe(false)
    expect(specFromMonster(m).particles).toBe(true)
  })

  it('gives the parts secondary motion classes and the eyes a glance group', () => {
    const svg = renderMonsterSvg(specForBreed('hearthwing'))
    expect(svg).toContain('ws-mon__wing')
    expect(svg).toContain('ws-mon__pupil')
    expect(svg).toContain('ws-mon__glow')
    expect(renderMonsterSvg(specForBreed('puddlepup'))).toContain('ws-mon__ear')
    expect(renderMonsterSvg(specForBreed('starhowl'))).toContain('ws-mon__mane')
    expect(renderMonsterSvg(specForBreed('scrollopus'))).toContain('ws-mon__tentacle')
    expect(renderMonsterSvg(specForBreed('frostlance'))).toContain('ws-mon__fin')
  })
})
