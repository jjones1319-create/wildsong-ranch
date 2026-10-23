import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { DRILL_IDS } from '../data/types.ts'
import { propSvg } from './props.ts'

describe('drill vignettes (§22)', () => {
  it('every drill has a prop and its own motion in vignette CSS', () => {
    const css = readFileSync(new URL('../ui/styles/polish.css', import.meta.url), 'utf8')
    for (const id of DRILL_IDS) {
      const svg = propSvg(id)
      expect(svg.startsWith('<svg')).toBe(true)
      expect(css).toContain(`[data-vignette='${id}'] .vignette__mon`)
    }
    // Props with moving parts expose class hooks the CSS animates.
    expect(propSvg('log-toss')).toContain('ws-prop__log')
    expect(propSvg('dodge-the-gourds')).toContain('ws-prop__gourd--3')
    expect(propSvg('acorn-shower')).toContain('ws-prop__acorn--4')
  })

  it('keeps every animated property to transforms and opacity', () => {
    const css = readFileSync(new URL('../ui/styles/polish.css', import.meta.url), 'utf8')
    const keyframes = css.match(/@keyframes[^{]+\{([\s\S]*?)\n\}/g) ?? []
    expect(keyframes.length).toBeGreaterThan(20)
    for (const block of keyframes) {
      const props = [...block.matchAll(/^\s+([a-z-]+):/gm)].map((m) => m[1])
      for (const p of props) expect(['transform', 'opacity']).toContain(p)
    }
  })
})
