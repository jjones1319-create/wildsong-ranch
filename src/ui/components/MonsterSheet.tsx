import type { ComponentChildren } from 'preact'
import { fatigueLabel, loyaltyLabel, stressLabel } from '../../core/aging.ts'
import { findRelative } from '../../core/fusion.ts'
import { isPure, loyaltyOf, stageOf, strainOf, styleBandOf, styleOf, totalStats, traitOf, weeksLeft, type Monster } from '../../core/monster.ts'
import { secretOf, variantNameOf } from '../../core/variants.ts'
import { BREED_BY_ID } from '../../data/breeds.ts'
import { DRILL_BY_ID } from '../../data/drills.ts'
import { FOOD_BY_ID } from '../../data/foods.ts'
import { ITEM_BY_ID } from '../../data/items.ts'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { fill } from '../../data/text/format.ts'
import { FAMILY_LABELS, GROWTH_WORDS, RANGE_LABELS, STAGE_NAMES, STAT_NAMES, STYLE_LABELS } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { HEARTSTONE, RANGES } from '../../data/tuning.ts'
import { STAT_KEYS, type TransparencyMode } from '../../data/types.ts'
import { TRAIT_BY_ID } from '../../data/traits.ts'
import { LifeBar } from '../screens/lab/LabEditor.tsx'
import { settings } from '../store/appStore.ts'
import { game } from '../store/gameStore.ts'
import { Badge } from './Controls.tsx'
import { MonsterPortrait } from './MonsterPortrait.tsx'

/**
 * §21 Monster Card body, shared by the ranch (transparency-aware) and the Lab's view (always the Lens):
 * portrait, stats with grades and bars (plus "from sweets"), life bar, condition, techniques by range,
 * personality and records. The caller adds the buttons.
 */
export function MonsterSheet({ m, mode, editCount, children }: { m: Monster; mode: TransparencyMode; editCount?: number; children?: ComponentChildren }) {
  const t = UI_TEXT.lab.view
  const c = UI_TEXT.card
  const stage = stageOf(m)
  const trait = TRAIT_BY_ID[traitOf(m)]
  const exact = mode === 'lens'
  const sweetsTotal = STAT_KEYS.reduce((s, k) => s + m.records.fromSweets[k], 0)
  const byRange = [1, 2, 3, 4].map((r) => ({ r, slots: m.techniques.filter((s) => TECHNIQUE_BY_ID[s.id]?.range === r) }))
  return (
    <>
      <div class="preview">
        <MonsterPortrait monster={m} size={140} />
        <div class="preview__info">
          <span class="preview__name">{m.name}</span>
          <span class="muted small">{variantNameOf(m)}</span>
          <span class="row row--wrap small">
            {secretOf(m) && <Badge tone="preset">★ {UI_TEXT.lineage.variant}</Badge>}
            {isPure(m) && <Badge tone="pure">✦ {UI_TEXT.lab.badges.pure}</Badge>}
            {settings.value.showEditedBadge && m.flags.edited && <Badge tone="edited">🔧 {UI_TEXT.lab.badges.edited}</Badge>}
            <Badge>
              {UI_TEXT.lab.grade} {m.grade}
            </Badge>
          </span>
        </div>
      </div>

      {children}

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
        {sweetsTotal > 0 && <p class="muted small">{fill(c.sweetsTotal, { n: sweetsTotal })}</p>}
      </section>

      <section class="card">
        <p class="field__label">
          {STAGE_NAMES[stage - 1]}
          {exact ? ` · ${fill(t.lifeLeft, { n: weeksLeft(m) })}` : ''}
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
          {exact && (
            <>
              <dt>{t.lifespan}</dt>
              <dd>{fill(UI_TEXT.lab.weeks, { n: m.lifespanTotal })}</dd>
              <dt>{t.guts}</dt>
              <dd>{m.gutsRate}</dd>
            </>
          )}
        </dl>
      </section>

      <section class="card">
        <p class="field__label">{t.condition}</p>
        <dl class="kv">
          <dt>{UI_TEXT.lab.editor.fatigue}</dt>
          <dd>
            {fatigueLabel(m.fatigue)}
            {exact && <span class="muted small"> ({m.fatigue})</span>}
          </dd>
          <dt>{UI_TEXT.lab.editor.stress}</dt>
          <dd>
            {stressLabel(m.stress)}
            {exact && <span class="muted small"> ({m.stress})</span>}
          </dd>
          <dt>{UI_TEXT.lab.editor.loyalty}</dt>
          <dd>
            {loyaltyLabel(loyaltyOf(m))}
            {exact && <span class="muted small"> ({loyaltyOf(m)})</span>}
          </dd>
          <dt>{UI_TEXT.lab.editor.style}</dt>
          <dd>{STYLE_LABELS[styleBandOf(styleOf(m))]}</dd>
          {exact && (
            <>
              <dt>{c.strain}</dt>
              <dd>
                {strainOf(m)} <span class="muted small">({c.debt} {m.status.strainDebt})</span>
              </dd>
              <dt>{t.nature}</dt>
              <dd>{m.nature}</dd>
              <dt>{t.form}</dt>
              <dd>{m.form}</dd>
            </>
          )}
          <dt>{t.fame}</dt>
          <dd>{m.fame}</dd>
        </dl>
      </section>

      <section class="card">
        <p class="field__label">
          {t.techniques} · {m.techniques.length}
        </p>
        {m.techniques.length === 0 ? (
          <p class="muted">{t.none}</p>
        ) : (
          byRange.map(
            ({ r, slots }) =>
              slots.length > 0 && (
                <div key={r}>
                  <p class="muted small" style={{ margin: '6px 0 0' }}>
                    {RANGE_LABELS[r as 1 | 2 | 3 | 4]}
                  </p>
                  {slots.map((slot) => {
                    const tech = TECHNIQUE_BY_ID[slot.id]
                    return (
                      <div class="tech" key={slot.id}>
                        <span class="tech__name">
                          {tech?.name ?? slot.id}
                          <br />
                          <span class="tech__meta">{tech ? `${FAMILY_LABELS[tech.family]} · ${tech.type} · ${tech.cost} guts` : ''}</span>
                        </span>
                        <span class="pill">
                          {UI_TEXT.lab.editor.level}
                          {slot.level}
                        </span>
                      </div>
                    )
                  })}
                </div>
              ),
          )
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

      {(m.parents.length === 2 || m.generation > 1 || m.heirloom || secretOf(m)) && <LineageCard m={m} />}

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
          {editCount ? ` · ${fill(c.history, { n: editCount })}` : ''}
        </p>
      </section>
    </>
  )
}

/** §15 the family tree (parents and grandparents by name, when this ranch still knows them), the Heirloom and the variant. */
function LineageCard({ m }: { m: Monster }) {
  const t = UI_TEXT.lineage
  const g = game.value
  const secret = secretOf(m)
  const nameOf = (id: string) => (g ? findRelative(g, id) : null)
  const parents = m.parents.length === 2 ? m.parents.map((id) => nameOf(id)) : []
  const stone = g?.heartstones.find((h) => h.family === m.heirloom)
  return (
    <section class="card">
      <p class="field__label">{t.title}</p>
      <dl class="kv">
        <dt>{fill(t.generation, { n: m.generation })}</dt>
        <dd>{secret ? `${t.variant}: ${variantNameOf(m)} (${secret.look})` : ''}</dd>
        {parents.length === 2 && (
          <>
            <dt>{t.parents}</dt>
            <dd>
              {parents.map((p, i) => (
                <span key={i}>
                  {i > 0 ? ' × ' : ''}
                  {p ? `${p.name} (${variantNameOf(p)})` : t.unknown}
                </span>
              ))}
              {parents.some((p) => p && p.parents.length === 2) && (
                <span class="muted small">
                  <br />
                  {parents
                    .filter((p) => p && p.parents.length === 2)
                    .map((p) => p!.parents.map((id) => nameOf(id)?.name ?? t.unknown).join(' × '))
                    .join(' · ')}
                </span>
              )}
            </dd>
          </>
        )}
        {m.heirloom && (
          <>
            <dt>{UI_TEXT.pellLab.tabs.heartstones}</dt>
            <dd>{fill(t.heirloom, { hit: HEARTSTONE.heirloomHit, family: FAMILY_LABELS[m.heirloom], donor: stone?.donorName ?? t.unknown })}</dd>
          </>
        )}
      </dl>
    </section>
  )
}
