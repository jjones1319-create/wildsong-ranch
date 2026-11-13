import { Texture } from 'three'
import { describe, expect, it } from 'vitest'
import { ART } from '../../data/tuning.ts'
import { filmMaterial } from '../perf/content.ts'
import { bodySheenOf } from './parts.ts'

/** A look's own body sheen (a recipe's BODY_SHEEN → the sidecar's `body.sheen`): a stone breed wants none. */
describe('the body sheen (sidecar body.sheen)', () => {
  const F = ART.ultra.film

  it('reads a usable sheen, and nothing else', () => {
    expect(bodySheenOf({ body: { sheen: 0 } })).toBe(0)
    expect(bodySheenOf({ body: { sheen: 0.2 } })).toBe(0.2)
    expect(bodySheenOf({ body: { sheen: 1 } })).toBe(1)
    for (const bad of [null, {}, { body: null }, { body: {} }, { body: { sheen: -0.1 } }, { body: { sheen: 1.5 } }, { body: { sheen: '0' } }, { body: { sheen: Number.NaN } }]) {
      expect(bodySheenOf(bad)).toBeNull()
    }
  })

  it('absent: the fur sheen, as before; 0: no sheen on the body; every other part unchanged', () => {
    const tex = { base: new Texture(), normal: null, orm: null }
    const sheenOf = (kind: Parameters<typeof filmMaterial>[0], bodySheen?: number | null) => filmMaterial(kind, tex, { bodySheen }).sheen
    // absent (or null, as bodySheenOf gives for a look without the entry): the film's default
    expect(sheenOf('body')).toBe(F.furSheen)
    expect(sheenOf('body', null)).toBe(F.furSheen)
    // a stone breed
    expect(sheenOf('body', 0)).toBe(0)
    expect(sheenOf('body', 0.2)).toBe(0.2)
    // the other parts take no notice of it
    for (const v of [undefined, 0, 0.2]) {
      expect(sheenOf('card', v)).toBe(F.cardSheen)
      expect(sheenOf('lock', v)).toBe(F.furSheen)
      expect(sheenOf('prop', v)).toBe(0)
      expect(sheenOf('fin', v)).toBe(0)
      expect(sheenOf('eye', v)).toBe(0)
    }
  })
})
