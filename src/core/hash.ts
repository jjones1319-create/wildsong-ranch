/**
 * Phrase normalization and the 53-bit string hash (cyrb53) that turn "any song title or phrase" into a seed.
 * GAME_DESIGN §14.1. Changing anything here changes every monster ever born from a phrase, so the tests pin
 * the exact outputs.
 */

/**
 * NFKC → lowercase → trim → collapse whitespace → keep only letters, digits and spaces (any script).
 * Punctuation can leave a double space behind, so the result is collapsed once more: "a - b" equals "a b".
 */
export function normalizePhrase(input: string): string {
  const basic = input.normalize('NFKC').toLowerCase().trim().replace(/\s+/g, ' ')
  const lettersOnly = basic.replace(/[^\p{L}\p{N} ]/gu, '')
  return lettersOnly.replace(/\s+/g, ' ').trim()
}

/** cyrb53: a fast, well-distributed 53-bit string hash (public domain, by bryc). */
export function cyrb53(str: string, seed = 0): number {
  let h1 = 0xdeadbeef ^ seed
  let h2 = 0x41c6ce57 ^ seed
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i)
    h1 = Math.imul(h1 ^ ch, 2654435761)
    h2 = Math.imul(h2 ^ ch, 1597334677)
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507)
  h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909)
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507)
  h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909)
  return 4294967296 * (2097151 & h2) + (h1 >>> 0)
}

export interface PhraseSeed {
  phrase: string
  artist: string
  h1: number
  h2: number
  /** The mulberry32 seed: the low 32 bits of h1 XOR h2. */
  seed: number
}

/** §14.1: h1 = hash(phrase, 1); h2 = hash(artist || phrase, 2); seed = h1 ^ h2. */
export function phraseSeed(phraseInput: string, artistInput = ''): PhraseSeed {
  const phrase = normalizePhrase(phraseInput)
  const artist = normalizePhrase(artistInput)
  const h1 = cyrb53(phrase, 1)
  const h2 = cyrb53(artist || phrase, 2)
  return { phrase, artist, h1, h2, seed: (h1 ^ h2) >>> 0 }
}
