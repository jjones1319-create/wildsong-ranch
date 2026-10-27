import { useEffect, useRef, useState } from 'preact/hooks'
import { playSfx, unlockAudio } from '../../../audio/player.ts'
import { canPlayEchoStones, echoMelody, echoTempo, type EchoResult, type Stone } from '../../../core/echoStones.ts'
import type { Emote as EmoteKind } from '../../../core/emotes.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { ECHO_STONES } from '../../../data/tuning.ts'
import { Toggle, TopBar } from '../../components/Controls.tsx'
import { Emote } from '../../components/Emote.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { hapticTick } from '../../lib/haptics.ts'
import { settings, updateSettings } from '../../store/appStore.ts'
import { finishEchoStones, game, oddJobSeed } from '../../store/gameStore.ts'

const t = UI_TEXT.oddJobs
const NOTE_SFX = ['echo1', 'echo2', 'echo3', 'echo4'] as const
const STONES: Stone[] = [0, 1, 2, 3]

type Phase = 'intro' | 'listen' | 'input' | 'retry' | 'done'
type Mood = 'neutral' | 'hum' | 'pleased' | 'startled'

/** The four stones' shape symbols, drawn in code: circle, square, triangle, diamond. */
function Shape({ stone }: { stone: Stone }) {
  switch (stone) {
    case 0:
      return <circle cx="50" cy="50" r="20" />
    case 1:
      return <rect x="31" y="31" width="38" height="38" rx="5" />
    case 2:
      return <polygon points="50,28 72,70 28,70" />
    default:
      return <polygon points="50,26 74,50 50,74 26,50" />
  }
}

/**
 * CONTENT §13 Echo Stones: four glowing stones play a melody that grows by one note each round; tap it back.
 * The melody and the tempo are rules in core (seeded from the game's RNG); this component only runs the clock,
 * the glow, the notes and the monster beside the stones. The stones flash as well as sound, so it works with the
 * sound off; each has a shape as well as a colour, and a label for screen readers.
 */
export function EchoStones({ practice, onDone }: { practice: boolean; onDone: () => void }) {
  const g = game.value
  const [phase, setPhase] = useState<Phase>('intro')
  const [round, setRound] = useState(1)
  const [lit, setLit] = useState<Stone | null>(null)
  const [cleared, setCleared] = useState(0)
  const [retriesLeft, setRetriesLeft] = useState<number>(ECHO_STONES.retries)
  const [mood, setMood] = useState<Mood>('neutral')
  const [emote, setEmote] = useState<{ kind: EmoteKind; key: number } | null>(null)
  const [result, setResult] = useState<EchoResult | null>(null)
  const [won, setWon] = useState(false)
  const run = useRef<{ melody: Stone[]; round: number; index: number; retries: number; cleared: number; timers: ReturnType<typeof setTimeout>[]; stop: boolean } | null>(null)
  const relaxed = settings.value.oddJobsRelaxed

  useEffect(() => () => stopAll(), [])

  if (!g || !g.monster) return null
  const monster = g.monster
  const can = practice ? ({ ok: true } as const) : canPlayEchoStones(g)

  function stopAll(): void {
    const r = run.current
    if (!r) return
    r.stop = true
    for (const id of r.timers) clearTimeout(id)
    r.timers = []
  }

  function later(ms: number, fn: () => void): void {
    const r = run.current
    if (!r) return
    const id = setTimeout(() => {
      if (!run.current || run.current.stop) return
      fn()
    }, ms)
    r.timers.push(id)
  }

  function pop(kind: EmoteKind): void {
    setEmote({ kind, key: Date.now() })
  }

  /** Plays round `n` of the melody: lead-in, then each stone glows and sounds in turn, then it is the player's turn. */
  function listen(n: number): void {
    const r = run.current
    if (!r) return
    r.round = n
    r.index = 0
    setRound(n)
    setPhase('listen')
    setMood('hum')
    setLit(null)
    const { noteMs, gapMs } = echoTempo(n, relaxed)
    let at = ECHO_STONES.leadMs
    for (let i = 0; i < n; i++) {
      const s = r.melody[i]!
      later(at, () => {
        setLit(s)
        playSfx(NOTE_SFX[s])
      })
      later(at + noteMs, () => setLit(null))
      at += noteMs + gapMs
    }
    later(at, () => {
      setPhase('input')
      setMood('neutral')
    })
  }

  function start(): void {
    if (!can.ok) return
    void unlockAudio()
    stopAll()
    run.current = { melody: echoMelody(oddJobSeed()), round: 1, index: 0, retries: ECHO_STONES.retries, cleared: 0, timers: [], stop: false }
    setCleared(0)
    setRetriesLeft(ECHO_STONES.retries)
    setResult(null)
    setWon(false)
    setEmote(null)
    listen(1)
  }

  function finish(wonAll: boolean): void {
    const r = run.current
    if (!r) return
    stopAll()
    const res = finishEchoStones(r.cleared, practice)
    run.current = null
    setWon(wonAll)
    setResult(res)
    setPhase('done')
    setMood(wonAll ? 'pleased' : 'neutral')
  }

  function tap(s: Stone): void {
    const r = run.current
    if (!r || phase !== 'input') return
    hapticTick()
    playSfx(NOTE_SFX[s])
    setLit(s)
    later(ECHO_STONES.tapMs, () => setLit(null))
    if (s === r.melody[r.index]) {
      r.index += 1
      if (r.index < r.round) return
      // The round is echoed in full.
      r.cleared = r.round
      setCleared(r.cleared)
      setMood('pleased')
      pop('heart')
      playSfx('echoClear')
      if (r.round >= ECHO_STONES.maxRounds) {
        later(ECHO_STONES.leadMs, () => finish(true))
        return
      }
      setPhase('listen')
      later(ECHO_STONES.leadMs, () => listen(r.round + 1))
      return
    }
    // A slip.
    setMood('startled')
    pop('surprise')
    playSfx('echoWrong')
    if (r.retries > 0) {
      r.retries -= 1
      setRetriesLeft(r.retries)
      setPhase('retry')
      return
    }
    later(ECHO_STONES.leadMs, () => finish(false))
    setPhase('listen')
  }

  const moodLine = mood === 'hum' ? fill(t.humming, { name: monster.name }) : mood === 'pleased' ? fill(t.pleased, { name: monster.name }) : mood === 'startled' ? fill(t.startled, { name: monster.name }) : ''
  const statusLine = phase === 'listen' ? t.echoListen : phase === 'input' ? t.echoYourTurn : phase === 'retry' ? t.echoRetry : ''

  return (
    <main class="screen">
      <TopBar title={t.echoStones} />
      {phase === 'intro' && (
        <>
          <SpeakerCard speaker={UI_TEXT.basil} tone="muted">
            <p>{t.echoIntro}</p>
          </SpeakerCard>
          {practice && <p class="notice">{t.practiceOnly}</p>}
          {!can.ok && <p class="notice">{'reason' in can && can.reason === 'played' ? t.played : t.noMonster}</p>}
          <section class="card">
            <Toggle label={t.echoRelaxed} hint={t.echoRelaxedHint} checked={relaxed} onChange={(v) => void updateSettings({ oddJobsRelaxed: v })} />
            {g.echoStonesBest > 0 && <p class="muted small">{fill(t.bestRound, { n: g.echoStonesBest })}</p>}
          </section>
          <div class="spacer" />
          <div class="actionbar">
            <button type="button" class="btn btn--primary" disabled={!can.ok} onClick={start}>
              {t.echoStart}
            </button>
          </div>
        </>
      )}
      {(phase === 'listen' || phase === 'input' || phase === 'retry') && (
        <>
          <div class="chute__score">
            <span>{fill(t.echoRound, { n: round })}</span>
            <span>{practice ? t.practiceOnly : fill(t.result, { n: gold(Math.min(ECHO_STONES.cap, cleared * ECHO_STONES.payPerRound)) })}</span>
          </div>
          <div class="echo">
            <div class="echo__monster">
              <MonsterPortrait monster={monster} size={96} expression={mood === 'pleased' ? 'happy' : mood === 'startled' ? 'stressed' : undefined} />
              <Emote key={emote?.key ?? 0} kind={emote?.kind ?? null} name={monster.name} />
              {mood === 'hum' && (
                <span class="echo__hum" aria-hidden="true">
                  ♪
                </span>
              )}
            </div>
            <div class={`echo__grid ${phase === 'input' ? 'echo__grid--open' : ''}`} role="group" aria-label={t.echoStones}>
              {STONES.map((s) => (
                <button
                  key={s}
                  type="button"
                  class={`stone stone--${s} ${lit === s ? 'stone--lit' : ''}`}
                  aria-label={fill(t.stoneLabel, { name: t.stoneNames[s]!, note: t.stoneNotes[s]! })}
                  aria-pressed={lit === s}
                  disabled={phase !== 'input'}
                  onClick={() => tap(s)}
                >
                  <svg viewBox="0 0 100 100" aria-hidden="true">
                    <ellipse cx="50" cy="56" rx="42" ry="34" class="stone__body" />
                    <ellipse cx="38" cy="38" rx="14" ry="8" class="stone__sheen" />
                    <g class="stone__shape">
                      <Shape stone={s} />
                    </g>
                  </svg>
                </button>
              ))}
            </div>
          </div>
          <p class="echo__status" role="status" aria-live="polite">
            {statusLine} {moodLine}
          </p>
          {phase === 'retry' && (
            <div class="actionbar">
              <button type="button" class="btn btn--primary" onClick={() => listen(round)}>
                {t.echoListenAgain}
              </button>
            </div>
          )}
          {phase !== 'retry' && retriesLeft === 0 && <p class="muted small center">{t.echoMissed.split('.')[0]}</p>}
        </>
      )}
      {phase === 'done' && result && (
        <>
          <SpeakerCard speaker={UI_TEXT.basil}>
            <p>{won ? t.echoWon : fill(t.echoCleared, { n: cleared })}</p>
            <p class="heading">{practice ? t.practiceResult : fill(t.result, { n: gold(result.pay) })}</p>
            {result.stressRelief > 0 && <p>{fill(t.echoCalm, { name: monster.name, n: result.stressRelief })}</p>}
            {result.newBest && <p>{t.echoNewBest}</p>}
            {result.titles.map((title) => (
              <p key={title}>{fill(t.echoTitle, { title })}</p>
            ))}
          </SpeakerCard>
          <div class="spacer" />
          <div class="actionbar">
            {practice && (
              <button type="button" class="btn btn--half" onClick={() => setPhase('intro')}>
                {t.practice}
              </button>
            )}
            <button type="button" class={`btn btn--primary ${practice ? 'btn--half' : ''}`} onClick={onDone}>
              {t.done}
            </button>
          </div>
        </>
      )}
    </main>
  )
}
