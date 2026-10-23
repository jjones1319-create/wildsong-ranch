import { useMemo } from 'preact/hooks'
import { sceneBackground, type SceneKind } from '../../art/backgrounds.ts'
import { dateOf, seasonOf } from '../../core/calendar.ts'
import { game } from '../store/gameStore.ts'
import { lite } from '../store/perf.ts'

/** §22: a short strip of scenery (Town rooftops, the Shrine's stones) that follows the ranch's season and weather. */
export function SceneBanner({ scene }: { scene: SceneKind }) {
  const g = game.value
  const season = g ? seasonOf(dateOf(g.week).month) : 'Spring'
  const weather = g?.weather ?? 'Sunny'
  const liteMode = lite.value
  const svg = useMemo(() => sceneBackground({ scene, season, weather, lite: liteMode, seed: 11 }), [scene, season, weather, liteMode])
  return <div class="scene" aria-hidden="true" dangerouslySetInnerHTML={{ __html: svg }} />
}
