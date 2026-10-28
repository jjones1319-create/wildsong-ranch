import { useEffect, useRef, useState } from 'preact/hooks'
import { playSfx } from '../../../../audio/player.ts'
import { fetchCaught } from '../../../../core/bond.ts'
import type { Monster } from '../../../../core/monster.ts'
import { BONDS_TEXT } from '../../../../data/text/bonds.ts'
import { fill } from '../../../../data/text/format.ts'
import { BOND } from '../../../../data/tuning.ts'
import { MonsterPortrait } from '../../../components/MonsterPortrait.tsx'
import { hapticTick } from '../../../lib/haptics.ts'
import { reduceMotionNow } from '../../../store/fxStore.ts'

const t = BONDS_TEXT.bond.fetch
const F = BOND.fetch

/** The power bar: up and back down each cycle (a triangle wave), 0–100. */
function powerAt(ms: number): number {
  const phase = (ms % F.barCycleMs) / F.barCycleMs
  return Math.round((phase < 0.5 ? phase * 2 : 2 - phase * 2) * 100)
}

/**
 * §6.9 Fetch: hold to wind up, let go in the green; the monster races after the ball and trots back with it. Five
 * throws; a throw in the green is a catch. The bar is written straight to the element each frame.
 */
export function Fetch({ m, onDone }: { m: Monster; onDone: (score: number) => void }) {
  const [throwNo, setThrowNo] = useState(1)
  const [caught, setCaught] = useState(0)
  const [line, setLine] = useState<string>(t.hold)
  const [busy, setBusy] = useState(false)
  const [run, setRun] = useState<'idle' | 'out' | 'back'>('idle')
  const [ball, setBall] = useState<number | null>(null)
  const hold = useRef<{ start: number; raf: number } | null>(null)
  const fill_ = useRef<HTMLSpanElement>(null)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])
  const reduce = reduceMotionNow()

  useEffect(
    () => () => {
      for (const id of timers.current) clearTimeout(id)
      if (hold.current) cancelAnimationFrame(hold.current.raf)
    },
    [],
  )

  const later = (ms: number, fn: () => void) => timers.current.push(setTimeout(fn, reduce ? 0 : ms))

  function frame(): void {
    const h = hold.current
    if (!h) return
    if (fill_.current) fill_.current.style.transform = `scaleX(${powerAt(performance.now() - h.start) / 100})`
    h.raf = requestAnimationFrame(frame)
  }

  function press(): void {
    if (busy || hold.current || throwNo > F.throws) return
    hold.current = { start: performance.now(), raf: requestAnimationFrame(frame) }
  }

  function release(): void {
    const h = hold.current
    if (!h) return
    cancelAnimationFrame(h.raf)
    hold.current = null
    const power = powerAt(performance.now() - h.start)
    if (fill_.current) fill_.current.style.transform = `scaleX(${power / 100})`
    const ok = fetchCaught(power)
    hapticTick(12)
    playSfx('dashStep')
    setBusy(true)
    setBall(power)
    setRun('out')
    later(F.runMs, () => {
      setRun('back')
      setLine(fill(ok ? t.caught : power < F.zone.from ? t.short : t.missed, { name: m.name }))
      if (ok) {
        setCaught((n) => n + 1)
        playSfx('jackpotHeal')
      }
    })
    later(F.runMs + F.backMs, () => {
      setRun('idle')
      setBall(null)
      setBusy(false)
      const next = throwNo + 1
      if (next > F.throws) {
        onDone(caught + (ok ? 1 : 0))
        return
      }
      setThrowNo(next)
    })
  }

  return (
    <div class="bondgame">
      <p class="chute__score">
        <span>{fill(t.throwN, { n: Math.min(throwNo, F.throws), total: F.throws })}</span>
        <span>{fill(t.result, { n: caught, total: F.throws })}</span>
      </p>
      <div class="fetch">
        {ball !== null && <span class={`fetch__ball fetch__ball--${run}`} style={{ bottom: `${30 + ball * 0.55}%` }} aria-hidden="true" />}
        <div class={`fetch__mon fetch__mon--${run}`} style={run !== 'idle' && ball !== null ? { '--fetch-y': `${-ball * 2.2}px` } : undefined}>
          <MonsterPortrait monster={m} size={110} expression="happy" animate={false} />
        </div>
      </div>
      <div class="fetch__bar" aria-hidden="true">
        <span class="fetch__zone" style={{ left: `${F.zone.from}%`, width: `${F.zone.to - F.zone.from}%` }} />
        <span ref={fill_} class="fetch__fill" />
      </div>
      <p class="echo__status" role="status" aria-live="polite">
        {line}
      </p>
      <button
        type="button"
        class="btn btn--primary fetch__throw"
        disabled={busy}
        data-silent
        onPointerDown={(e) => {
          ;(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId)
          press()
        }}
        onPointerUp={release}
        onPointerCancel={release}
        onKeyDown={(e) => {
          if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) {
            e.preventDefault()
            press()
          }
        }}
        onKeyUp={(e) => {
          if (e.key === ' ' || e.key === 'Enter') {
            e.preventDefault()
            release()
          }
        }}
      >
        🎾 {t.holdButton}
      </button>
    </div>
  )
}
