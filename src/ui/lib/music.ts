import { effect } from '@preact/signals'
import { ranchTrackFor, type TrackId } from '../../audio/music.ts'
import { setMusic } from '../../audio/player.ts'
import { dateOf, seasonOf } from '../../core/calendar.ts'
import type { Screen } from '../router.ts'
import { screen } from '../router.ts'
import { view as battleView } from '../store/battleStore.ts'
import { game } from '../store/gameStore.ts'

/** Which loop belongs to a screen (§23): the ranch by season, Town, the Shrine, battle, the farewell. */
export function trackFor(current: Screen, week: number | null, battleRunning: boolean): TrackId {
  if (battleRunning || current === 'battle') return 'battle'
  if (current === 'farewell') return 'farewell'
  if (current === 'shrine') return 'shrine'
  switch (current) {
    case 'town':
    case 'shop':
    case 'library':
    case 'pell':
    case 'market':
    case 'guild':
    case 'mail':
    case 'journal':
    case 'oddJobs':
    case 'upgrades':
      return 'town'
    default:
      return ranchTrackFor(week === null ? 'Spring' : seasonOf(dateOf(week).month))
  }
}

/** Keeps the music in step with the screen. Call once from main. */
export function installMusic(): void {
  effect(() => {
    const running = battleView.value !== null && battleView.value.outcome === null
    setMusic(trackFor(screen.value, game.value?.week ?? null, running))
  })
}
