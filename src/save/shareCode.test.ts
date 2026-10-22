import { describe, expect, it } from 'vitest'
import { makeMonster } from '../core/test-helpers.ts'
import { makeMonsterFile } from './schema.ts'
import { decodeShareCode, encodeShareCode, extractShareCode, fromBase64Url, SHARE_PREFIX, toBase64Url } from './shareCode.ts'

describe('share codes (§19)', () => {
  it('round-trips a monster file and starts with WS1-', async () => {
    const file = makeMonsterFile(makeMonster({ main: 'coilfang', sub: 'wishlume' }))
    const code = await encodeShareCode(file)
    expect(code.startsWith(SHARE_PREFIX)).toBe(true)
    expect(code).toMatch(/^WS1-[A-Za-z0-9_-]+$/)
    const back = await decodeShareCode(code)
    expect(back.ok).toBe(true)
    if (back.ok) expect(back.value).toEqual(JSON.parse(JSON.stringify(file)))
  })

  it('is shorter than the JSON it carries and fits in a QR code', async () => {
    const file = makeMonsterFile(makeMonster())
    const code = await encodeShareCode(file)
    expect(code.length).toBeLessThan(JSON.stringify(file).length)
    // Byte-mode QR capacity at the lowest error correction is 2,953 bytes; leave room for the link.
    expect(code.length).toBeLessThan(2500)
  })

  it('finds a code inside a sentence, a link, wrapped lines or lower-case text', async () => {
    const code = await encodeShareCode({ hello: 'world' })
    expect(extractShareCode(`Here is my monster: ${code} enjoy!`)).toBe(code)
    expect(extractShareCode(`https://example.github.io/wildsong-ranch/#import=${code}`)).toBe(code)
    const inSentence = await decodeShareCode(`Here is my monster: ${code} enjoy!`)
    expect(inSentence.ok && inSentence.value).toEqual({ hello: 'world' })
    const wrapped = `Code:\n${code.slice(0, 10)}\n${code.slice(10, 20)} \r\n ${code.slice(20)}\n\nSent from my phone`
    const unwrapped = await decodeShareCode(wrapped)
    expect(unwrapped.ok && unwrapped.value).toEqual({ hello: 'world' })
    const lower = `ws1-${code.slice(4)}`
    const back = await decodeShareCode(lower)
    expect(back.ok).toBe(true)
    if (back.ok) expect(back.value).toEqual({ hello: 'world' })
  })

  it('still decodes a code that was written at version 0.3.0 (the stable-code contract)', async () => {
    // Produced by encodeShareCode({ kind: 'probe', n: 7, list: [1, 2, 3] }) in Node 24. Deflate decoding is
    // standard, so this must decode on every engine. If this test ever fails, old codes have broken.
    const pinned = 'WS1-q1bKzsxLUbJSKijKT0pV0lHKU7Iy11HKySwuUbKKNtQx0jGOrQUA'
    const back = await decodeShareCode(pinned)
    expect(back.ok).toBe(true)
    if (back.ok) expect(back.value).toEqual({ kind: 'probe', n: 7, list: [1, 2, 3] })
  })

  it('never throws on garbage', async () => {
    for (const bad of ['', '   ', 'hello', 'WS1-', 'WS1-!!!', 'WS1-AAAA', 'WS2-abc', `${SHARE_PREFIX}${'A'.repeat(300)}`]) {
      const r = await decodeShareCode(bad)
      expect(r.ok).toBe(false)
      if (!r.ok) expect(r.error.length).toBeGreaterThan(0)
    }
  })

  it('base64url helpers handle padding and odd input', () => {
    for (const len of [0, 1, 2, 3, 4, 5, 100]) {
      const bytes = new Uint8Array(len).map((_, i) => (i * 37 + 11) % 256)
      const text = toBase64Url(bytes)
      expect(text).not.toMatch(/[+/=]/)
      expect(fromBase64Url(text)).toEqual(bytes)
      expect(fromBase64Url(text + '==')).toEqual(bytes)
    }
    expect(fromBase64Url('!!!')).toEqual(new Uint8Array(0))
  })
})
