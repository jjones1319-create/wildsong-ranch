import { useEffect, useRef, useState } from 'preact/hooks'
import { playSfx, playStinger } from '../../../audio/player.ts'
import type { Monster } from '../../../core/monster.ts'
import { BONDS_TEXT } from '../../../data/text/bonds.ts'
import { fill } from '../../../data/text/format.ts'
import { ARRIVAL } from '../../../data/tuning.ts'
import { Emote } from '../../components/Emote.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { gold } from '../../components/RanchBits.tsx'
import { SceneClip, type ClipName } from '../../components/SceneClip.tsx'
import { hapticTick } from '../../lib/haptics.ts'
import { navigate } from '../../router.ts'
import { reduceMotionNow } from '../../store/fxStore.ts'
import { closeArrival, petArrival, treatArrival, type ArrivalView } from '../../store/gameStore.ts'

const t = BONDS_TEXT.arrival
const SIZE = 150

/** Where the monster stands in each clip (bottom centre, % of the frame) and how big, from and to. */
interface Pose {
  from: { x: number; y: number; s: number }
  to: { x: number; y: number; s: number }
  ms: number
}

const POSES: Record<string, Pose> = {
  happy: { from: { x: 50, y: 58, s: 0.42 }, to: { x: 50, y: 86, s: 1 }, ms: 2400 },
  curious: { from: { x: 50, y: 58, s: 0.42 }, to: { x: 50, y: 76, s: 0.75 }, ms: 3400 },
  aloof: { from: { x: 62, y: 62, s: 0.5 }, to: { x: 62, y: 62, s: 0.5 }, ms: 2000 },
  sad: { from: { x: 58, y: 68, s: 0.62 }, to: { x: 58, y: 68, s: 0.62 }, ms: 3000 },
  abandoned: { from: { x: 52, y: 74, s: 0.6 }, to: { x: 52, y: 74, s: 0.6 }, ms: 3000 },
}

const vars = (m: Monster, extra: Record<string, string | number> = {}) => ({ name: m.name, they: 'they', them: 'them', their: 'their', They: 'They', ...extra })

/** The monster drawn over the clip: walks (or runs, or doesn't) along its pose; transforms only, skippable with the clip. */
function ClipMonster({ m, pose, expression, dim }: { m: Monster; pose: Pose; expression: 'happy' | 'sad' | 'sick' | undefined; dim?: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current
    const parent = el?.parentElement
    if (!el || !parent || reduceMotionNow()) return
    const box = parent.getBoundingClientRect()
    const dx = ((pose.from.x - pose.to.x) / 100) * box.width
    const dy = ((pose.from.y - pose.to.y) / 100) * box.height
    const still = dx === 0 && dy === 0
    const frames = still
      ? [{ transform: `translate(-50%, -100%) scale(${pose.to.s})` }, { transform: `translate(-50%, -100%) scale(${pose.to.s * 1.02}, ${pose.to.s * 0.97})` }, { transform: `translate(-50%, -100%) scale(${pose.to.s})` }]
      : [
          { transform: `translate(calc(-50% + ${dx}px), calc(-100% + ${dy}px)) scale(${pose.from.s})` },
          { transform: `translate(calc(-50% + ${dx * 0.5}px), calc(-100% + ${dy * 0.5 - 10}px)) scale(${(pose.from.s + pose.to.s) / 2})`, offset: 0.5 },
          { transform: `translate(-50%, -100%) scale(${pose.to.s})` },
        ]
    const a = el.animate(frames, { duration: pose.ms, easing: 'ease-in-out', iterations: still ? Infinity : 1, fill: 'both' })
    return () => a.cancel()
  }, [])
  return (
    <div ref={ref} class={`clip__mon ${dim ? 'clip__mon--dim' : ''}`} style={{ left: `${pose.to.x}%`, top: `${pose.to.y}%`, transform: `translate(-50%, -100%) scale(${pose.to.s})` }}>
      <MonsterPortrait monster={m} size={SIZE} expression={expression} animate={false} />
    </div>
  )
}

/**
 * §6.10 the scene that greets the player: a hello (pet, treat), a day away (sad), two days (abandoned), or four
 * days (the note, then the Farewell). The consequences were applied before the scene started; the card shows them.
 */
export function ArrivalScene({ a, m }: { a: ArrivalView; m: Monster }) {
  const [phase, setPhase] = useState<'scene' | 'card' | 'note'>('scene')
  const [hearts, setHearts] = useState(0)
  const [noMoney, setNoMoney] = useState(false)
  const clip: ClipName = a.kind === 'greet' ? 'welcome' : a.kind === 'gone' ? 'note' : a.kind

  // Stand-ins until the S3 pieces: the sad scenes take the gentle match-loss phrase, the note the cup-exit fall.
  useEffect(() => {
    if (a.kind === 'sad' || a.kind === 'abandoned') playStinger('matchLoss')
    else if (a.kind === 'gone') playStinger('cupOut')
    else playSfx('jackpotDouble')
  }, [])

  const close = () => {
    closeArrival()
    if (a.kind === 'gone' && !a.preview) navigate('farewell')
  }

  const pet = () => {
    hapticTick(14)
    playSfx('jackpotHeal')
    setHearts((n) => n + 1)
    petArrival()
  }

  const pose = a.kind === 'greet' ? POSES[a.mood]! : a.kind === 'gone' ? null : POSES[a.kind]!
  const expression = a.kind === 'greet' ? (a.mood === 'aloof' ? undefined : 'happy') : a.kind === 'sad' ? 'sad' : a.kind === 'abandoned' ? 'sick' : undefined
  const heading = a.kind === 'greet' ? fill(a.mood === 'happy' ? t.greetHappy : a.mood === 'curious' ? t.greetCurious : t.greetAloof, vars(m)) : a.kind === 'sad' ? t.sadTitle : a.kind === 'abandoned' ? t.abandonedTitle : t.noteTitle

  return (
    <div class="overlay arrival" role="dialog" aria-label={heading}>
      <div class="overlay__inner">
        <SceneClip clip={clip} label={heading} onEnd={() => setPhase((p) => (p === 'scene' ? 'card' : p))}>
          {pose && <ClipMonster m={m} pose={pose} expression={expression} dim={a.kind === 'abandoned'} />}
          {a.kind === 'greet' && phase === 'card' && a.mood !== 'aloof' && (
            <button type="button" class="clip__pet" aria-label={fill(t.pet, vars(m))} data-silent onClick={(e) => (e.stopPropagation(), pet())}>
              <Emote key={hearts} kind={hearts > 0 ? 'heart' : null} name={m.name} />
            </button>
          )}
        </SceneClip>
        <h2 class="arrival__title">{heading}</h2>
        {a.preview && <p class="notice">{t.preview}</p>}

        {a.kind === 'greet' && phase === 'card' && (
          <>
            {a.petted && <p>{fill(t.petted, vars(m))}</p>}
            {a.treated && <p>{fill(t.treated, vars(m))}</p>}
            {noMoney && <p class="muted">{t.noMoney}</p>}
            <div class="row">
              <button type="button" class="btn btn--half" disabled={a.petted} data-silent onClick={pet}>
                🤚 {fill(t.pet, vars(m))}
              </button>
              <button
                type="button"
                class="btn btn--half"
                disabled={a.treated}
                onClick={() => {
                  if (treatArrival()) playSfx('itemGet')
                  else setNoMoney(true)
                }}
              >
                🍪 {fill(t.treat, { price: gold(ARRIVAL.treat.price) })}
              </button>
            </div>
            <div class="spacer" />
            <button type="button" class="btn btn--primary" onClick={close}>
              {t.toRanch}
            </button>
          </>
        )}

        {(a.kind === 'sad' || a.kind === 'abandoned') && phase === 'card' && (
          <>
            <p>{fill(a.kind === 'sad' ? t.sad : t.abandoned, vars(m))}</p>
            <section class="card">
              <p class="field__label">{t.changesTitle}</p>
              <ul class="arrival__changes">
                {(Object.keys(t.change) as (keyof typeof t.change)[])
                  .filter((k) => a.changes[k] !== 0)
                  .map((k) => (
                    <li key={k}>{fill(t.change[k], { n: k !== 'sickWeeks' && a.changes[k] > 0 ? `+${a.changes[k]}` : a.changes[k] })}</li>
                  ))}
              </ul>
            </section>
            <p class="arrival__plea">{fill(t.plea, vars(m))}</p>
            <div class="spacer" />
            <button type="button" class="btn btn--primary" onClick={close}>
              {t.continue}
            </button>
          </>
        )}

        {a.kind === 'gone' && phase === 'card' && (
          <>
            <div class="spacer" />
            <button type="button" class="btn btn--primary" onClick={() => setPhase('note')}>
              {t.openNote}
            </button>
          </>
        )}
        {a.kind === 'gone' && phase === 'note' && (
          <>
            <section class="card arrival__note">
              {fill(t.note, vars(m))
                .split('\n\n')
                .map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
            </section>
            <p class="arrival__gone">{fill(a.wandered ? t.wandered : t.gone, vars(m))}</p>
            <div class="spacer" />
            <button type="button" class="btn btn--primary" onClick={close}>
              {a.preview ? t.toRanch : t.goodbye}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
