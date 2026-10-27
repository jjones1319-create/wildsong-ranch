import { playSfx } from '../../../audio/player.ts'
import { useEffect, useState } from 'preact/hooks'
import { forgotLine, learnedLine } from '../../../core/report.ts'
import { canLearn, goodFit, isFull, learnableFromSongbook } from '../../../core/songbook.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { TECHNIQUE_BY_ID } from '../../../data/techniques.ts'
import { fill } from '../../../data/text/format.ts'
import { FAMILY_LABELS, RANGE_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { SONGBOOK } from '../../../data/tuning.ts'
import type { Technique } from '../../../data/types.ts'
import { Sheet, TopBar } from '../../components/Controls.tsx'
import { navigate } from '../../router.ts'
import { showToast } from '../../store/appStore.ts'
import { forget, game, learn } from '../../store/gameStore.ts'

function techMeta(tech: Technique): string {
  return `${FAMILY_LABELS[tech.family]} · ${tech.type} · ${RANGE_LABELS[tech.range]} · ${tech.cost} guts`
}

/** §10.5 the Songbook: known techniques (Forget), what the monster can learn now (★ good fit, Learn), other owned sheets. */
export function SongbookScreen() {
  const g = game.value
  const t = UI_TEXT.songbook
  const [makingRoomFor, setMakingRoomFor] = useState<Technique | null>(null)
  useEffect(() => {
    if (!g || !g.monster) navigate('ranch')
  }, [g === null])
  if (!g || !g.monster) return null
  const m = g.monster
  const learnable = learnableFromSongbook(m, g.songbook)
  const known = m.techniques.map((s) => ({ slot: s, tech: TECHNIQUE_BY_ID[s.id] })).filter((x) => x.tech)
  const knownIds = new Set(m.techniques.map((s) => s.id))
  const others = g.songbook
    .map((id) => TECHNIQUE_BY_ID[id])
    .filter((x): x is Technique => x !== undefined && !learnable.includes(x) && !knownIds.has(x.id))
    .map((tech) => ({ tech, why: canLearn(m, tech.id) }))

  const doLearn = (tech: Technique, forgetId?: string) => {
    const status = learn(tech.id, forgetId)
    setMakingRoomFor(null)
    if (status === 'learned') {
      showToast(learnedLine(m, tech.id).text)
      playSfx('learnTechnique')
    }
    else if (status === 'full') setMakingRoomFor(tech)
  }

  const reasonText = (why: ReturnType<typeof canLearn>, tech: Technique) => {
    if (why.ok) return ''
    if (why.reason === 'known') return t.reasons.known
    if (why.reason === 'signatureNotPure') return fill(t.reasons.signatureNotPure, { breed: tech.breed === 'universal' ? '' : BREED_BY_ID[tech.breed].name })
    return fill(t.reasons.notInKit, { name: m.name })
  }

  return (
    <main class="screen">
      <TopBar title={t.title} />
      <section class="card">
        <p class="field__label">{fill(t.known, { n: m.techniques.length, max: SONGBOOK.maxTechniques })}</p>
        {known.length === 0 && <p class="muted">{UI_TEXT.lab.view.none}</p>}
        {known.map(({ slot, tech }) => (
          <div class="item" key={slot.id}>
            <span class="item__body">
              <span class="item__name">
                {tech!.name} <span class="pill">Lv{slot.level}</span>
              </span>
              <span class="item__meta">{techMeta(tech!)}</span>
            </span>
            <button
              type="button"
              class="btn btn--small"
              onClick={() => {
                forget(slot.id)
                showToast(forgotLine(m, slot.id).text)
              }}
            >
              {t.forget}
            </button>
          </div>
        ))}
      </section>

      <section class="card">
        <p class="field__label">{t.learnable}</p>
        {g.songbook.length === 0 && <p class="muted">{t.empty}</p>}
        {g.songbook.length > 0 && learnable.length === 0 && <p class="muted">{t.nothingNew}</p>}
        {learnable.map((tech) => (
          <div class="item" key={tech.id}>
            <span class="item__body">
              <span class="item__name">
                {tech.name} {goodFit(m, tech) && <span class="food__tag">{t.fit}</span>}
              </span>
              <span class="item__meta">{techMeta(tech)}</span>
            </span>
            <button type="button" class="btn btn--small btn--primary" onClick={() => (isFull(m) ? setMakingRoomFor(tech) : doLearn(tech))}>
              {t.learn}
            </button>
          </div>
        ))}
      </section>

      {others.length > 0 && (
        <section class="card">
          <p class="field__label">{t.others}</p>
          {others.map(({ tech, why }) => (
            <div class="item item--off" key={tech.id}>
              <span class="item__body">
                <span class="item__name">{tech.name}</span>
                <span class="item__meta">
                  {techMeta(tech)} · {reasonText(why, tech)}
                </span>
              </span>
            </div>
          ))}
        </section>
      )}

      <Sheet open={makingRoomFor !== null} title={t.makeRoom} onClose={() => setMakingRoomFor(null)}>
        {makingRoomFor && <p class="muted small">{fill(t.makeRoomHint, { name: m.name, max: SONGBOOK.maxTechniques, technique: makingRoomFor.name })}</p>}
        {known.map(({ slot, tech }) => (
          <div class="item" key={slot.id}>
            <span class="item__body">
              <span class="item__name">{tech!.name}</span>
              <span class="item__meta">{techMeta(tech!)}</span>
            </span>
            <button type="button" class="btn btn--small" onClick={() => makingRoomFor && doLearn(makingRoomFor, slot.id)}>
              {t.forget}
            </button>
          </div>
        ))}
        <div class="sheet__actions">
          <button type="button" class="btn" onClick={() => setMakingRoomFor(null)}>
            {UI_TEXT.lab.actions.cancel}
          </button>
        </div>
      </Sheet>
    </main>
  )
}
