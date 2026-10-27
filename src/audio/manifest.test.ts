import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import type { Manifest } from './engine/samples.ts'
import { INSTRUMENT_IDS, INSTRUMENTS, playableRange, type SampleRoots } from './recipes/instruments.ts'
import { packFor, packsNeededBy } from './recipes/packs.ts'
import { buildUsage } from './recipes/usage.ts'
import { manifestRoots } from './songs.test.ts'

const ROOT = join(process.cwd(), 'public', 'audio')
const manifest = JSON.parse(readFileSync(join(ROOT, 'manifest.json'), 'utf8')) as Manifest

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else out.push(p)
  }
  return out
}

describe('the sample manifest (§5)', () => {
  it('lists every file in public/audio and every listed file exists', () => {
    const listed = new Set<string>()
    for (const inst of Object.values(manifest.instruments)) for (const list of Object.values(inst.arts)) for (const s of list) listed.add(s.file)
    for (const f of listed) expect(existsSync(join(ROOT, f)), f).toBe(true)
    const onDisk = walk(ROOT)
      .map((p) => p.slice(ROOT.length + 1).replace(/\\/g, '/'))
      .filter((p) => p !== 'manifest.json')
    expect(onDisk.filter((p) => !listed.has(p))).toEqual([])
    expect(manifest.codec).toBe('opus')
    expect(manifest.sampleRate).toBe(48000)
  })

  it('every sample has a root, cents, onset and loop points in seconds, and sustains loop', () => {
    for (const [instId, inst] of Object.entries(manifest.instruments)) {
      for (const [art, list] of Object.entries(inst.arts)) {
        for (const s of list) {
          expect(s.inst).toBe(instId)
          expect(s.art).toBe(art)
          expect(Number.isInteger(s.root)).toBe(true)
          expect(Math.abs(s.cents)).toBeLessThanOrEqual(50)
          expect(s.onset).toBeGreaterThanOrEqual(0)
          // Bowed and swelled samples cross −50 dB late; the attack is kept, never cut (§5.3 step 3).
          expect(s.onset, `${s.file} onset`).toBeLessThan(0.3)
          expect(s.seconds).toBeGreaterThan(0.05)
          if (s.loopStart !== null) {
            expect(s.loopEnd).not.toBeNull()
            expect(s.loopEnd! - s.loopStart).toBeGreaterThanOrEqual(0.05)
            expect(s.loopEnd!).toBeLessThanOrEqual(s.seconds + 0.002)
          }
        }
      }
    }
    for (const sus of [['ocarina', 'sus'], ['recorder-alto', 'vib'], ['violins', 'trem'], ['cellos', 'vib']] as const) {
      for (const s of manifest.instruments[sus[0]]!.arts[sus[1]]!) expect(s.loopStart, `${sus[0]}/${sus[1]} loops`).not.toBeNull()
    }
  })

  it('every instrument in the table has samples for every articulation it names, and melody ranges sit inside the playable ranges', () => {
    const roots: SampleRoots = manifestRoots()
    for (const id of INSTRUMENT_IDS) {
      const def = INSTRUMENTS[id]
      if (def.patch) continue
      expect(manifest.instruments[id], `${id} is in the manifest`).toBeTruthy()
      for (const art of def.arts) {
        expect(manifest.instruments[id]!.arts[art], `${id}/${art}`).toBeTruthy()
        if (def.melody) {
          const range = playableRange(roots, id, art)!
          expect(def.melody[0], `${id}/${art} low`).toBeGreaterThanOrEqual(range[0])
          expect(def.melody[1], `${id}/${art} high`).toBeLessThanOrEqual(range[1])
        }
      }
    }
  })

  it('keeps the §2 budgets', () => {
    let total = 0
    for (const [pack, p] of Object.entries(manifest.packs)) {
      total += p.bytes
      const limit = { core: 450, events: 250, places: 300 }[pack] ?? 300
      expect(p.seconds, `${pack} seconds`).toBeLessThanOrEqual(limit)
    }
    expect(manifest.packs.core!.bytes).toBeLessThanOrEqual(4.5 * 1024 * 1024)
    expect(total).toBeLessThanOrEqual(10 * 1024 * 1024)
  })

  it('packs follow the usage graph: every instrument a context uses is in a pack loaded there', () => {
    const usage = buildUsage()
    for (const [inst, contexts] of usage.byInstrument) {
      if (INSTRUMENTS[inst as keyof typeof INSTRUMENTS]?.patch) continue
      const entry = manifest.instruments[inst]
      expect(entry, `${inst} has samples`).toBeTruthy()
      expect(entry!.pack, `${inst} pack`).toBe(packFor(contexts))
      for (const c of contexts) expect(packsNeededBy(c), `${inst} in ${c}`).toContain(entry!.pack)
    }
  })

  it('credits every source', () => {
    const credits = readFileSync(join(process.cwd(), 'CREDITS.md'), 'utf8')
    for (const src of Object.values(manifest.sources)) {
      expect(credits).toContain(src.url)
      if (src.pin) expect(credits).toContain(src.pin)
      if (src.sha256) expect(credits).toContain(src.sha256)
    }
    expect(credits).not.toMatch(/zzfx/i)
  })
})
