import { useEffect, useRef, useState } from 'preact/hooks'
import { playSfx } from '../../../../audio/player.ts'
import { hideSpots } from '../../../../core/bond.ts'
import type { Monster } from '../../../../core/monster.ts'
import { BONDS_TEXT } from '../../../../data/text/bonds.ts'
import { fill } from '../../../../data/text/format.ts'
import { BOND } from '../../../../data/tuning.ts'
import { MonsterPortrait } from '../../../components/MonsterPortrait.tsx'
import { hapticTick } from '../../../lib/haptics.ts'

const t = BONDS_TEXT.bond.hide
const H = BOND.hide

type Phase = 'hiding' | 'rustle' | 'pick' | 'reveal'

/**
 * §6.9 Hide-and-seek: the monster hides behind one of four haystacks (seeded from the game's RNG), one gives a quick
 * rustle, and you pick. Five rounds. With Reduce motion the rustle is a glow instead of a wiggle (the global rule).
 */
export function HideSeek({ m, seed, onDone }: { m: Monster; seed: number; onDone: (score: number) => void }) {
  const spots = useRef(hideSpots(seed))
  const [round, setRound] = useState(0)
  const [phase, setPhase] = useState<Phase>('hiding')
  const [found, setFound] = useState(0)
  const [line, setLine] = useState('')
  const [picked, setPicked] = useState<number | null>(null)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])
  const foundRef = useRef(0)

  const clear = () => {
    for (const id of timers.current) clearTimeout(id)
    timers.current = []
  }
  const later = (ms: number, fn: () => void) => timers.current.push(setTimeout(fn, ms))

  useEffect(() => clear, [])

  // Each round: hide, rustle, then a few seconds to pick.
  useEffect(() => {
    if (round >= H.rounds) return
    clear()
    setPicked(null)
    setPhase('hiding')
    setLine(fill(t.hiding, { name: m.name }))
    later(H.hideMs, () => {
      setPhase('rustle')
      playSfx('dashStep')
    })
    later(H.hideMs + H.rustleMs, () => {
      setPhase('pick')
      setLine(fill(t.pick, { name: m.name }))
    })
    later(H.hideMs + H.rustleMs + H.pickMs, () => reveal(null))
  }, [round])

  function reveal(choice: number | null): void {
    clear()
    const spot = spots.current[round]!
    setPicked(choice)
    setPhase('reveal')
    if (choice === spot) {
      foundRef.current += 1
      setFound(foundRef.current)
      setLine(fill(t.found, { them: 'them' }))
      playSfx('jackpotHeal')
      hapticTick(14)
    } else setLine(choice === null ? fill(t.slow, { name: m.name }) : fill(t.wrong, { name: m.name, n: spot + 1 }))
    later(1400, () => {
      if (round + 1 >= H.rounds) onDone(foundRef.current)
      else setRound(round + 1)
    })
  }

  const spot = spots.current[Math.min(round, H.rounds - 1)]!
  return (
    <div class="bondgame">
      <p class="chute__score">
        <span>{fill(t.roundN, { n: Math.min(round + 1, H.rounds), total: H.rounds })}</span>
        <span>{fill(t.result, { n: found, total: H.rounds })}</span>
      </p>
      <div class="hide">
        {Array.from({ length: H.spots }, (_, i) => (
          <button
            key={i}
            type="button"
            class={`hide__stack ${phase === 'rustle' && i === spot ? 'hide__stack--rustle' : ''} ${phase === 'reveal' && i === picked ? 'hide__stack--picked' : ''}`}
            aria-label={fill(t.stack, { n: i + 1 })}
            disabled={phase !== 'pick'}
            data-silent
            onClick={() => reveal(i)}
          >
            <svg viewBox="0 0 80 70" aria-hidden="true">
              <path d="M6 66 Q8 22 40 10 Q72 22 74 66z" fill="#e3c26a" stroke="#9c7a33" stroke-width="3" />
              <path d="M18 60 L24 30 M34 62 L38 24 M50 62 L48 26 M62 60 L58 32" stroke="#b8933f" stroke-width="2.5" />
            </svg>
            {phase === 'reveal' && i === spot && (
              <span class="hide__peek">
                <MonsterPortrait monster={m} size={64} expression="happy" animate={false} live clip="idle_happy" />
              </span>
            )}
          </button>
        ))}
      </div>
      <p class="echo__status" role="status" aria-live="polite">
        {line}
      </p>
    </div>
  )
}
