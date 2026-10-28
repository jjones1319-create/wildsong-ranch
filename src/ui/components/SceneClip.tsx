import type { ComponentChildren } from 'preact'
import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import { ranchBackground } from '../../art/backgrounds.ts'
import type { Weather } from '../../data/types.ts'
import { BONDS_TEXT } from '../../data/text/bonds.ts'
import { reduceMotionNow } from '../store/fxStore.ts'

/** The Blender-rendered scenery clips (tools/blender/ranch_scenes.py → public/baked/scenes/). */
export type ClipName = 'welcome' | 'sad' | 'abandoned' | 'note'

/** Each clip's length (seconds): a stalled video still ends the scene this long after it started (plus a little). */
const CLIP_SECONDS: Record<ClipName, number> = { welcome: 7, sad: 8, abandoned: 8, note: 7 }
/** The weather the drawn fallback uses when neither the clip nor its still can load. */
const FALLBACK_WEATHER: Record<ClipName, Weather> = { welcome: 'Sunny', sad: 'Cloudy', abandoned: 'Rain', note: 'Cloudy' }

const src = (clip: ClipName, ext: 'mp4' | 'webp') => `${import.meta.env.BASE_URL}baked/scenes/${clip}.${ext}`

/**
 * §6.10 a scene: a pre-rendered scenery clip (muted, inline, so it plays on iOS and Android), with the monster and
 * anything else drawn in code on top (`children`, positioned in % of the frame). Tap to skip. With Reduce motion,
 * offline before the clip is cached, or if the video fails, the scene is its still picture; failing that, the
 * ranch drawn in code. `onEnd` fires when the clip ends, is skipped, or at once for a still.
 */
export function SceneClip({ clip, onEnd, children, label }: { clip: ClipName; onEnd: () => void; children?: ComponentChildren; label: string }) {
  const still = reduceMotionNow()
  const [mode, setMode] = useState<'video' | 'still' | 'drawn'>(still ? 'still' : 'video')
  const ended = useRef(false)
  const [done, setDone] = useState(still)
  const end = () => {
    if (ended.current) return
    ended.current = true
    setDone(true)
    onEnd()
  }

  useEffect(() => {
    if (still) {
      end()
      return
    }
    // A stalled or missing clip still ends the scene.
    const timer = setTimeout(end, (CLIP_SECONDS[clip] + 2) * 1000)
    return () => clearTimeout(timer)
  }, [clip])

  const drawn = useMemo(() => (mode === 'drawn' ? ranchBackground({ season: 'Summer', weather: FALLBACK_WEATHER[clip], lite: true, seed: 3 }) : ''), [mode, clip])

  return (
    <div class={`clip clip--${clip}`} role="img" aria-label={label} onClick={end}>
      {mode === 'video' && (
        <video
          class="clip__media"
          src={src(clip, 'mp4')}
          poster={src(clip, 'webp')}
          muted
          playsInline
          autoplay
          preload="auto"
          onEnded={end}
          onError={() => setMode('still')}
        />
      )}
      {mode === 'still' && <img class="clip__media" src={src(clip, 'webp')} alt="" onError={() => setMode('drawn')} />}
      {mode === 'drawn' && <div class="clip__media clip__media--drawn" dangerouslySetInnerHTML={{ __html: drawn }} />}
      <div class="clip__layer">{children}</div>
      {!done && mode === 'video' && <span class="clip__skip">{BONDS_TEXT.arrival.skip}</span>}
    </div>
  )
}
