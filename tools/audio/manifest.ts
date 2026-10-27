/**
 * The committed sample manifest (public/audio/manifest.json) as the checker's sample roots, for the tools.
 * No side effects, so both analyze.ts and render-review.ts can import it.
 */
import { readFileSync } from 'node:fs'
import type { SampleRoots } from '../../src/audio/recipes/instruments.ts'

interface Manifest {
  instruments: Record<string, { arts: Record<string, { root: number }[]> }>
}

export function manifestRoots(path = 'public/audio/manifest.json'): SampleRoots {
  const m = JSON.parse(readFileSync(path, 'utf8')) as Manifest
  const roots: SampleRoots = {}
  for (const [inst, def] of Object.entries(m.instruments)) {
    roots[inst] = {}
    for (const [art, list] of Object.entries(def.arts)) roots[inst]![art] = [...new Set(list.map((s) => s.root))]
  }
  return roots
}
