/**
 * The Gloamvault snapshot (docs/WORLD_3D.md §1) is what SOURCE.json says it is: every file present with the recorded
 * sha256, pinned to one commit. Re-run `npm run world:import` (and `--repin`) to change it on purpose.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { checkSnapshot, PINNED_COMMIT, SNAPSHOT, type SourceRecord } from './import-gloamvault.ts'

describe('the Gloamvault snapshot', () => {
  it('matches SOURCE.json byte for byte', () => {
    expect(checkSnapshot()).toEqual([])
  })

  it('is pinned to one commit and holds the town, land, kit, hero and townsfolk', () => {
    const source = JSON.parse(readFileSync(join(SNAPSHOT, 'SOURCE.json'), 'utf8')) as SourceRecord
    expect(source.commit).toBe(PINNED_COMMIT)
    const paths = source.files.map(f => f.path)
    for (const p of ['land/vale.json', 'kit/kit_vale.glb', 'kit/vale.json', 'hero/hero_clips.glb', 'people/humanoid.glb', 'people/manifest.json']) {
      expect(paths).toContain(`tools/world/gloamvault/${p}`)
    }
    expect(paths).toContain('tools/blender/world/gvkit/env/build_kit_vale.py')
    const people = JSON.parse(readFileSync(join(SNAPSHOT, 'people', 'manifest.json'), 'utf8')) as Record<string, unknown>
    expect(Object.keys(people).every(id => id.startsWith('npc-'))).toBe(true)
    expect(people).toHaveProperty('npc-farmer')
  })
})
