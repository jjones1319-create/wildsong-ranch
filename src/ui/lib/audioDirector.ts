import { effect, signal } from '@preact/signals'
import { decide, type BattleOrigin, type Scene } from '../../audio/director.ts'
import { applyRequest, drillCueActive } from '../../audio/player.ts'
import { dateOf, seasonOf } from '../../core/calendar.ts'
import { nextPlayerMatch, opponentOf } from '../../core/tournament.ts'
import { AUDIO, BATTLE } from '../../data/tuning.ts'
import { screen } from '../router.ts'
import { paused as battlePaused, setup as battleSetup, speed as battleSpeed, view as battleView } from '../store/battleStore.ts'
import { game } from '../store/gameStore.ts'

/**
 * SOUND_UPGRADE §11: the director's controller. It reads the app's signals, builds the scene, lets the pure
 * `decide` turn it into a request, and hands the request to the player with a 250 ms debounce so fast
 * navigation never starts more than two songs. Sheets and overlays never reach here, so they never change
 * the music. The odd-job screen tells it which job is open.
 */

export const oddJobMode = signal<'turnip' | 'echo' | null>(null)

let timer: ReturnType<typeof setTimeout> | null = null
let lastKey = ''

function originOf(origin: string | undefined): BattleOrigin {
  if (origin === 'tournamentPlay') return 'cup'
  if (origin === 'ranch') return 'trial'
  if (origin === 'labBattleLab') return 'lab'
  return 'versus'
}

export function buildScene(): Scene {
  const g = game.value
  const week = g?.week ?? null
  const season = week === null ? 'Spring' : seasonOf(dateOf(week).month)
  const t = g?.tournament ?? null
  let opponentRivalId: string | null = null
  if (t) {
    const next = nextPlayerMatch(t)
    if (next) opponentRivalId = opponentOf(t, next.match).rivalId ?? null
  }
  const v = battleView.value
  const s = battleSetup.value
  const current = screen.value
  const battle: Scene['battle'] =
    v && s && current === 'battle'
      ? {
          phase: v.outcome ? 'result' : 'match',
          origin: originOf(s.origin),
          hp: [v.fighters[0].maxHp ? v.fighters[0].hp / v.fighters[0].maxHp : 1, v.fighters[1].maxHp ? v.fighters[1].hp / v.fighters[1].maxHp : 1],
          secondsLeft: Math.max(0, (v.timerTicks - v.tick) / BATTLE.ticksPerSecond),
          matchSeconds: v.timerTicks / BATTLE.ticksPerSecond,
          paused: battlePaused.value,
          speed: battleSpeed.value,
        }
      : null
  return {
    screen: current,
    season,
    weather: g?.weather ?? 'Sunny',
    eventId: t?.eventId ?? null,
    opponentRivalId,
    battle,
    drill: drillCueActive.value,
    journeySite: g?.journey?.site ?? null,
    expeditionSite: g?.expedition?.site ?? null,
    oddJob: current === 'oddJobs' ? oddJobMode.value : null,
  }
}

/** Keeps the sound in step with the app. Call once from main. */
export function installDirector(): void {
  effect(() => {
    const scene = buildScene()
    const request = decide(scene)
    // Battle layer changes must land fast (tension at the next bar); screen changes are debounced.
    const key = JSON.stringify(request)
    if (key === lastKey) return
    lastKey = key
    const urgent = scene.screen === 'battle' || scene.drill !== null
    if (timer) clearTimeout(timer)
    if (urgent) {
      timer = null
      applyRequest(request)
      return
    }
    timer = setTimeout(() => {
      timer = null
      applyRequest(request)
    }, AUDIO.navDebounceMs)
  })
}
