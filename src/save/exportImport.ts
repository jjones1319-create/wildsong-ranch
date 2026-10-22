import { toString as qrToString } from 'qrcode'
import type { Monster } from '../core/monster.ts'
import { fill } from '../data/text/format.ts'
import { UI_TEXT } from '../data/text/ui.ts'
import { makeMonsterFile, validateAny, type AnyValidation, type HistoryEntry } from './schema.ts'
import { decodeShareCode, extractShareCode } from './shareCode.ts'
import { encodeShareCode } from './shareCode.ts'

/**
 * GAME_DESIGN §19 import and export, without the DOM: text in, text out. The browser-side pieces
 * (downloads, Web Share, the file picker, the clipboard) live in `ui/lib/files.ts`.
 */

export const IMPORT_HASH_KEY = 'import'

/** The readable `.json` download: the monster plus its edit history. */
export function monsterJsonText(m: Monster, history: HistoryEntry[] = []): string {
  return JSON.stringify(makeMonsterFile(m, history), null, 2)
}

/** The share code carries the monster alone (history would make codes and QR codes huge). */
export function monsterShareCode(m: Monster): Promise<string> {
  return encodeShareCode(makeMonsterFile(m))
}

/** What goes into the shared `.txt` file: one friendly line, then the code on its own line. */
export function shareTextFor(m: Monster, code: string): string {
  return `${fill(UI_TEXT.export.shareIntro, { name: m.name })}\n${code}\n`
}

/** `#import=CODE` (also `#/import=CODE`, and with other `&` parameters after it). */
export function importCodeFromHash(hash: string): string | null {
  const body = hash.replace(/^#\/?/, '')
  const match = new RegExp(`(?:^|&)${IMPORT_HASH_KEY}=([^&]+)`).exec(body)
  if (!match) return null
  let value = match[1]!
  try {
    value = decodeURIComponent(value)
  } catch {
    /* keep it as written */
  }
  return extractShareCode(value)
}

export function importUrlFor(pageUrl: string, code: string): string {
  return `${pageUrl}#${IMPORT_HASH_KEY}=${code}`
}

export type ImportParse = { ok: true; value: unknown } | { ok: false; error: string }

/** Pasted text may be JSON, a share code (alone, in a sentence, or inside a link), or nothing useful. */
export async function parseImportText(text: string): Promise<ImportParse> {
  const trimmed = text.trim()
  if (!trimmed) return { ok: false, error: UI_TEXT.errors.nothingToImport }
  if (/^[[{]/.test(trimmed)) {
    try {
      return { ok: true, value: JSON.parse(trimmed) as unknown }
    } catch {
      /* fall through: maybe a code is hiding in there */
    }
  }
  const linkCode = trimmed.includes(`${IMPORT_HASH_KEY}=`) ? importCodeFromHash(trimmed.slice(trimmed.indexOf('#'))) : null
  if (linkCode) return decodeShareCode(linkCode)
  if (extractShareCode(trimmed)) return decodeShareCode(trimmed)
  return { ok: false, error: UI_TEXT.errors.unknownKind }
}

/** Text → validated save, monster or library. Never throws. */
export async function readImport(text: string): Promise<AnyValidation> {
  const parsed = await parseImportText(text)
  if (!parsed.ok) return parsed
  return validateAny(parsed.value)
}

/** An SVG QR code for an import link, or null when the code is too long for one. */
export async function qrSvgFor(url: string): Promise<string | null> {
  try {
    return await qrToString(url, { type: 'svg', errorCorrectionLevel: 'L', margin: 1 })
  } catch {
    return null
  }
}

/** `wildsong-<name>.<ext>` with anything odd stripped from the name. */
export function fileNameFor(m: Monster, ext: 'json' | 'txt'): string {
  const slug = m.name
    .normalize('NFKD')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .toLowerCase()
  return `wildsong-${slug || m.mainBreed}.${ext}`
}
