import type { Emote as EmoteKind } from '../../core/emotes.ts'
import { fill } from '../../data/text/format.ts'
import { UI_TEXT } from '../../data/text/ui.ts'

const GLYPH: Record<EmoteKind, string> = { heart: '♥', surprise: '?!', anger: '💢', sleep: '💤' }

/** §22 emote bubble over a portrait: ♥, ?!, 💢, 💤. The parent positions it; `key` it to re-pop. */
export function Emote({ kind, name }: { kind: EmoteKind | null; name: string }) {
  if (!kind) return null
  return (
    <span class={`emote emote--${kind}`} role="img" aria-label={fill(UI_TEXT.emotes[kind], { name })}>
      {GLYPH[kind]}
    </span>
  )
}
