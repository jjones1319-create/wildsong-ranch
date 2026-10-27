import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * SOUND_UPGRADE §14.1: `engine/nodes.ts` is the only file that creates oscillators, PeriodicWaves,
 * compressors and WaveShapers; nothing imports zzfx; no square or sawtooth wave is named anywhere in the
 * audio code; and the package has no zzfx dependency.
 */
function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.(ts|tsx)$/.test(name) && !name.endsWith('.test.ts')) out.push(p)
  }
  return out
}

const SRC = join(process.cwd(), 'src')
const NODES = join(SRC, 'audio', 'engine', 'nodes.ts').replace(/\\/g, '/')

describe('audio bans (§14.1)', () => {
  const files = walk(SRC)

  it('only nodes.ts creates oscillators, PeriodicWaves, compressors or WaveShapers', () => {
    const offenders: string[] = []
    for (const f of files) {
      if (f.replace(/\\/g, '/') === NODES) continue
      const text = readFileSync(f, 'utf8')
      for (const needle of ['createOscillator', 'new OscillatorNode', 'createPeriodicWave', 'new PeriodicWave', 'createDynamicsCompressor', 'new DynamicsCompressorNode', 'createWaveShaper', 'new WaveShaperNode']) {
        if (text.includes(needle)) offenders.push(`${f}: ${needle}`)
      }
    }
    expect(offenders).toEqual([])
  })

  it('no WaveShaper even in nodes.ts, and no square or sawtooth wave type is ever asked for', () => {
    const nodes = readFileSync(NODES, 'utf8')
    expect(nodes.includes('createWaveShaper')).toBe(false)
    const offenders: string[] = []
    for (const f of files) {
      const text = readFileSync(f, 'utf8')
      if (/type\s*=\s*['"](square|sawtooth)['"]/.test(text) || /['"](square|sawtooth)['"]\s*as\s+OscillatorType/.test(text)) offenders.push(f)
    }
    expect(offenders).toEqual([])
  })

  it('nothing imports zzfx and the package does not depend on it', () => {
    const offenders = files.filter((f) => /from\s+['"]zzfx['"]|import\(['"]zzfx['"]\)/.test(readFileSync(f, 'utf8')))
    expect(offenders).toEqual([])
    const pkg = JSON.parse(readFileSync(join(process.cwd(), 'package.json'), 'utf8')) as { dependencies?: Record<string, string>; devDependencies?: Record<string, string> }
    expect(pkg.dependencies?.zzfx).toBeUndefined()
    expect(pkg.devDependencies?.zzfx).toBeUndefined()
  })

  it('the reference game names never appear in the audio code or docs', () => {
    const banned = [/\bzelda\b/i, /ocarina of time/i]
    const offenders: string[] = []
    const docs = ['docs/SOUND_UPGRADE.md', 'docs/PROGRESS.md', 'docs/BUILD_PLAN.md', 'docs/GAME_DESIGN.md', 'CLAUDE.md', 'CREDITS.md', 'README.md'].map((d) => join(process.cwd(), d))
    for (const f of [...files, ...docs]) {
      let text = ''
      try {
        text = readFileSync(f, 'utf8')
      } catch {
        continue
      }
      for (const re of banned) if (re.test(text)) offenders.push(f)
    }
    expect(offenders).toEqual([])
  })
})
