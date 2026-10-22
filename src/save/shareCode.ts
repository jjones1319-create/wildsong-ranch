import { UI_TEXT } from '../data/text/ui.ts'

/**
 * GAME_DESIGN §19 share codes: `WS1-` + base64url(deflate-raw(JSON)).
 * No library: the browser's CompressionStream / DecompressionStream do the work
 * (iOS 16.4+, Android Chrome and Node 24 all have them). Decoding never throws.
 */

export const SHARE_PREFIX = 'WS1-'

export type DecodeResult = { ok: true; value: unknown } | { ok: false; error: string }

async function pump(bytes: Uint8Array, transform: CompressionStream | DecompressionStream): Promise<Uint8Array> {
  const stream = new Blob([bytes as BlobPart]).stream().pipeThrough(transform)
  return new Uint8Array(await new Response(stream).arrayBuffer())
}

export function deflateRaw(bytes: Uint8Array): Promise<Uint8Array> {
  return pump(bytes, new CompressionStream('deflate-raw'))
}

export function inflateRaw(bytes: Uint8Array): Promise<Uint8Array> {
  return pump(bytes, new DecompressionStream('deflate-raw'))
}

export function toBase64Url(bytes: Uint8Array): string {
  let binary = ''
  const chunk = 0x8000
  for (let i = 0; i < bytes.length; i += chunk) binary += String.fromCharCode(...bytes.subarray(i, i + chunk))
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/** Accepts base64url or plain base64, with or without padding. Returns null when it isn't base64 at all. */
export function fromBase64Url(text: string): Uint8Array | null {
  const clean = text.replace(/-/g, '+').replace(/_/g, '/').replace(/[^A-Za-z0-9+/]/g, '')
  const padded = clean + '='.repeat((4 - (clean.length % 4)) % 4)
  try {
    const binary = atob(padded)
    const out = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i)
    return out
  } catch {
    return null
  }
}

export async function encodeShareCode(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(JSON.stringify(value))
  return SHARE_PREFIX + toBase64Url(await deflateRaw(bytes))
}

const CODE_CHARS = 'A-Za-z0-9_\\-+/='
/** How many wrapped line pieces after the code we are willing to try to glue back on. */
const MAX_WRAPPED_PIECES = 64

/**
 * Possible codes in pasted text (a link, a chat message, a .txt file), best guess first:
 * the run of code characters right after `WS1-`, then that run extended one whitespace-separated
 * piece at a time (plain-text email wraps long lines). A deflate stream only decodes when it is
 * exactly complete, so the decoder can simply try these in order. Lower-cased prefixes are fine.
 */
export function shareCodeCandidates(text: string): string[] {
  const match = new RegExp(`ws1-([${CODE_CHARS}]+)((?:\\s+[${CODE_CHARS}]+)*)`, 'i').exec(text)
  if (!match) return []
  let code = `${SHARE_PREFIX}${match[1]}`
  const out = [code]
  const pieces = match[2]!.trim().split(/\s+/).filter(Boolean).slice(0, MAX_WRAPPED_PIECES)
  for (const piece of pieces) {
    code += piece
    out.push(code)
  }
  return out
}

/** The best-guess code in pasted text, or null. */
export function extractShareCode(text: string): string | null {
  return shareCodeCandidates(text)[0] ?? null
}

async function decodeOne(code: string): Promise<unknown> {
  const bytes = fromBase64Url(code.slice(SHARE_PREFIX.length))
  if (!bytes || bytes.length === 0) throw new Error('empty')
  const json = new TextDecoder().decode(await inflateRaw(bytes))
  return JSON.parse(json) as unknown
}

export async function decodeShareCode(text: string): Promise<DecodeResult> {
  const candidates = shareCodeCandidates(text)
  if (candidates.length === 0) return { ok: false, error: UI_TEXT.errors.notACode }
  for (const code of candidates) {
    try {
      return { ok: true, value: await decodeOne(code) }
    } catch {
      /* try the next guess */
    }
  }
  return { ok: false, error: UI_TEXT.errors.codeUnreadable }
}
