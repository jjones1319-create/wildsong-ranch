import { describe, expect, it } from 'vitest'
import { createGameState } from '../core/state.ts'
import { makeMonster } from '../core/test-helpers.ts'
import { fileNameFor, importCodeFromHash, importUrlFor, monsterJsonText, monsterShareCode, parseImportText, qrSvgFor, readImport, shareTextFor } from './exportImport.ts'
import { makeSave } from './schema.ts'
import { encodeShareCode } from './shareCode.ts'

describe('export and import text (§19)', () => {
  it('still reads a share code made before v1.12, when the monster was a mix', async () => {
    const m = makeMonster({ main: 'tumblefox' })
    m.name = 'Cinder Tumblefox'
    const old = { ...JSON.parse(JSON.stringify(m)), subBreed: 'cinderlynx', flags: { pure: false, edited: false, sandbox: false }, appearance: { paletteBreed: 'cinderlynx', accentPart: 'ember ear tufts' } }
    const code = await encodeShareCode({ schemaVersion: 14, kind: 'monster', monster: old, history: [] })
    const r = await readImport(code)
    expect(r.ok && r.kind === 'monster' && r.file.monster).toEqual({ ...m, name: 'Tumblefox' })
  })

  it('reads the .json download back as a monster file with its history', async () => {
    const m = makeMonster({ id: 'orig' })
    const older = makeMonster({ id: 'orig' })
    older.name = 'Older'
    const text = monsterJsonText(m, [{ monster: older, savedAt: 5 }])
    const r = await readImport(text)
    expect(r.ok).toBe(true)
    if (r.ok && r.kind === 'monster') {
      expect(r.file.monster.id).toBe('orig')
      expect(r.file.history).toHaveLength(1)
      expect(r.file.history[0]!.monster.name).toBe('Older')
    } else {
      throw new Error('expected a monster')
    }
  })

  it('reads a share code, a share .txt, and an import link', async () => {
    const m = makeMonster({ main: 'galeheron' })
    const code = await monsterShareCode(m)
    for (const text of [code, shareTextFor(m, code), importUrlFor('https://x.github.io/wildsong-ranch/', code), `  ${code}\n`]) {
      const r = await readImport(text)
      expect(r.ok).toBe(true)
      if (r.ok && r.kind === 'monster') expect(r.file.monster.mainBreed).toBe('galeheron')
      else throw new Error('expected a monster')
    }
  })

  it('reads a full save and a bare monster object too', async () => {
    const save = makeSave(createGameState({ monster: makeMonster() }), 9)
    const r = await readImport(JSON.stringify(save))
    expect(r.ok && r.kind === 'save').toBe(true)
    const bare = await readImport(JSON.stringify(makeMonster()))
    expect(bare.ok && bare.kind === 'monster').toBe(true)
  })

  it('explains what is wrong instead of throwing', async () => {
    for (const text of ['', '   ', 'just some words', '{not json', '{"kind":"spaceship"}', '[1,2,3]']) {
      const r = await parseImportText(text)
      if (r.ok) {
        const v = await readImport(text)
        expect(v.ok).toBe(false)
      } else {
        expect(r.error.length).toBeGreaterThan(0)
      }
    }
  })

  it('pulls the code out of a hash', () => {
    expect(importCodeFromHash('#import=WS1-abc')).toBe('WS1-abc')
    expect(importCodeFromHash('#/import=WS1-abc&x=1')).toBe('WS1-abc')
    expect(importCodeFromHash('#import=WS1-a%2Db')).toBe('WS1-a-b')
    expect(importCodeFromHash('#lab')).toBeNull()
    expect(importCodeFromHash('#import=nothing')).toBeNull()
  })

  it('makes a QR code for a short link and gives up on an impossible one', async () => {
    const svg = await qrSvgFor('https://x.github.io/wildsong-ranch/#import=WS1-abc')
    expect(svg).toMatch(/^<svg/)
    expect(await qrSvgFor('x'.repeat(5000))).toBeNull()
  })

  it('builds safe file names', () => {
    const m = makeMonster()
    m.name = 'Señor Fluff/Ball!'
    expect(fileNameFor(m, 'json')).toBe('wildsong-senor-fluffball.json')
    m.name = '🐸'
    expect(fileNameFor(m, 'txt')).toBe('wildsong-puddlepup.txt')
  })
})
