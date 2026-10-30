import type { Emote as EmoteKind } from '../../core/emotes.ts'
import { fill } from '../../data/text/format.ts'
import { UI_TEXT } from '../../data/text/ui.ts'

const GLYPH: Record<EmoteKind, string> = { heart: '♥', surprise: '?!', anger: '💢', sleep: '💤' }

/**
 * §22 emote bubble over a portrait: ♥, ?!, 💢, 💤. The parent positions it; `key` it to re-pop.
 * With `onTap` the bubble is a tap target of its own (the ranch opens the waiting card from the ?! bubble)
 * and the tap does not reach whatever sits behind it.
 */
export function Emote({ kind, name, onTap }: { kind: EmoteKind | null; name: string; onTap?: () => void }) {
  if (!kind) return null
  const label = fill(UI_TEXT.emotes[kind], { name })
  if (onTap) {
    return (
      <span
        class={`emote emote--${kind} emote--tap`}
        role="button"
        tabIndex={0}
        aria-label={label}
        onClick={(e) => {
          e.stopPropagation()
          e.preventDefault()
          onTap()
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.stopPropagation()
            e.preventDefault()
            onTap()
          }
        }}
      >
        {GLYPH[kind]}
      </span>
    )
  }
  return (
    <span class={`emote emote--${kind}`} role="img" aria-label={label}>
      {GLYPH[kind]}
    </span>
  )
}
