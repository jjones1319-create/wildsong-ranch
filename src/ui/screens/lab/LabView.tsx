import { useEffect } from 'preact/hooks'
import { fatigueLabel, loyaltyLabel, stressLabel } from '../../../core/aging.ts'
import { isPure, loyaltyOf, mixBreeds, stageOf, styleBandOf, styleOf, totalStats, traitOf, weeksLeft } from '../../../core/monster.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { DRILL_BY_ID } from '../../../data/drills.ts'
import { FOOD_BY_ID } from '../../../data/foods.ts'
import { ITEM_BY_ID } from '../../../data/items.ts'
import { TECHNIQUE_BY_ID } from '../../../data/techniques.ts'
import { fill } from '../../../data/text/format.ts'
import { GROWTH_WORDS, STAGE_NAMES, STAT_NAMES, STYLE_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { RANGES } from '../../../data/tuning.ts'
import { STAT_KEYS } from '../../../data/types.ts'
import { TRAIT_BY_ID } from '../../../data/traits.ts'
import { Badge, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { navigate } from '../../router.ts'
import { settings } from '../../store/appStore.ts'
import { selectedListed, startEdit } from '../../store/labStore.ts'
import { LifeBar } from './LabEditor.tsx'

/** §21 Monster Card (the Lab's read-only view): stats with grades and bars, life bar, condition, techniques, personality, records. */
export function LabViewScreen() {
  const t = UI_TEXT.lab.view
  const listed = selectedListed()
  useEffect(() => {
    if (!listed) navigate('lab')
  }, [listed])
  if (!listed) return null
  const m = listed.monster
  const stage = stageOf(m)
  const trait = TRAIT_BY_ID[traitOf(m)]
  return (
    <main class="screen">
      <TopBar title={t.title} />
      <div class="preview">
        <MonsterPortrait monster={m} size={140} />
        <div class="preview__info">
          <span class="preview__name">{m.name}</span>
          <span class="muted small">{mixBreeds(m.mainBreed, m.subBreed).variantName}</span>
          <span class="row row--wrap small">
            {isPure(m) && <Badge tone="pure">✦ {UI_TEXT.lab.badges.pure}</Badge>}
            {settings.value.showEditedBadge && m.flags.edited && <Badge tone="edited">🔧 {UI_TEXT.lab.badges.edited}</Badge>}
            <Badge>
              {UI_TEXT.lab.grade} {m.grade}
            </Badge>
          </span>
        </div>
      </div>

      <section class="card">
        <p class="field__label">
          {t.stats} · {UI_TEXT.lab.total} {totalStats(m.stats)}
        </p>
        <div class="stats">
          {STAT_KEYS.map((k) => (
            <>
              <span key={`${k}-l`}>
                {k} <span class="muted small">{STAT_NAMES[k]}</span> <span class="pill">{m.grades[k]}</span>
              </span>
              <span key={`${k}-b`} class="stats__bar">
                <span class="stats__fill" style={{ width: `${(m.stats[k] / RANGES.stat.max) * 100}%` }} />
              </span>
              <span key={`${k}-n`} class="stats__num">
                {m.stats[k]}
                {m.records.fromSweets[k] > 0 && <span class="muted small"> (+{m.records.fromSweets[k]})</span>}
              </span>
            </>
          ))}
        </div>
      </section>

      <section class="card">
        <p class="field__label">
          {STAGE_NAMES[stage - 1]} · {fill(t.lifeLeft, { n: weeksLeft(m) })}
        </p>
        <LifeBar m={m} />
        <dl class="kv" style={{ marginTop: 10 }}>
          <dt>{t.trait}</dt>
          <dd>
            {trait.name} <span class="muted small">{trait.description}</span>
          </dd>
          <dt>{t.growth}</dt>
          <dd>{GROWTH_WORDS[m.growthType]}</dd>
          <dt>{t.age}</dt>
          <dd>{fill(UI_TEXT.lab.weeks, { n: m.ageWeeks })}</dd>
          <dt>{t.lifespan}</dt>
          <dd>{fill(UI_TEXT.lab.weeks, { n: m.lifespanTotal })}</dd>
          <dt>{t.guts}</dt>
          <dd>{m.gutsRate}</dd>
        </dl>
      </section>

      <section class="card">
        <p class="field__label">{t.condition}</p>
        <dl class="kv">
          <dt>{UI_TEXT.lab.editor.fatigue}</dt>
          <dd>{fatigueLabel(m.fatigue)}</dd>
          <dt>{UI_TEXT.lab.editor.stress}</dt>
          <dd>{stressLabel(m.stress)}</dd>
          <dt>{UI_TEXT.lab.editor.loyalty}</dt>
          <dd>
            {loyaltyLabel(loyaltyOf(m))} <span class="muted small">({loyaltyOf(m)})</span>
          </dd>
          <dt>{UI_TEXT.lab.editor.style}</dt>
          <dd>{STYLE_LABELS[styleBandOf(styleOf(m))]}</dd>
          <dt>{t.fame}</dt>
          <dd>{m.fame}</dd>
        </dl>
      </section>

      <section class="card">
        <p class="field__label">{t.techniques}</p>
        {m.techniques.length === 0 ? (
          <p class="muted">{t.none}</p>
        ) : (
          m.techniques.map((slot) => {
            const tech = TECHNIQUE_BY_ID[slot.id]
            return (
              <div class="tech" key={slot.id}>
                <span class="tech__name">
                  {tech?.name ?? slot.id}
                  <br />
                  <span class="tech__meta">{tech ? `${tech.family} · ${tech.type} · R${tech.range}` : ''}</span>
                </span>
                <span class="pill">
                  {UI_TEXT.lab.editor.level}
                  {slot.level}
                </span>
              </div>
            )
          })
        )}
      </section>

      <section class="card">
        <p class="field__label">{t.personality}</p>
        <dl class="kv">
          <dt>{t.likes}</dt>
          <dd>
            {FOOD_BY_ID[m.likes.food].name} · {DRILL_BY_ID[m.likes.drill].name}
          </dd>
          <dt>{t.dislikes}</dt>
          <dd>
            {FOOD_BY_ID[m.likes.dislikedFood].name} · {DRILL_BY_ID[m.likes.dislikedDrill].name}
          </dd>
          <dt>{t.toy}</dt>
          <dd>{ITEM_BY_ID[m.likes.toy]?.name ?? m.likes.toy}</dd>
          <dt>{UI_TEXT.lab.editor.battle}</dt>
          <dd>{UI_TEXT.lab.editor.battleOptions[String(m.likes.battle) as '-1' | '0' | '1']}</dd>
        </dl>
      </section>

      <section class="card">
        <p class="field__label">{t.records}</p>
        <dl class="kv">
          <dt>{t.wins}</dt>
          <dd>{m.records.wins}</dd>
          <dt>{t.losses}</dt>
          <dd>{m.records.losses}</dd>
          <dt>{UI_TEXT.lab.editor.titles}</dt>
          <dd>{m.records.titles.length ? m.records.titles.join(', ') : t.none}</dd>
        </dl>
        <p class="muted small">
          {BREED_BY_ID[m.mainBreed].name} / {BREED_BY_ID[m.subBreed].name}
          {m.seedPhrase ? ` · “${m.seedPhrase}”` : ''}
        </p>
      </section>

      <div class="actionbar">
        <button
          type="button"
          class="btn btn--primary btn--half"
          onClick={() => {
            startEdit(listed)
            navigate('labEdit')
          }}
        >
          ✏️ {UI_TEXT.lab.actions.edit}
        </button>
        <button type="button" class="btn btn--half" onClick={() => navigate('labExport')}>
          {UI_TEXT.lab.actions.export}
        </button>
      </div>
    </main>
  )
}
