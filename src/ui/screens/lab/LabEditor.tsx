import { useEffect, useState } from 'preact/hooks'
import { EXPRESSIONS, type Expression } from '../../../art/monster/expressions.ts'
import { fatigueLabel, loyaltyLabel, stressLabel } from '../../../core/aging.ts'
import { addableTechniques, applyBreedChange, breedBaseStats, maxAllStats, randomizeStats, resetGrowthToBreed, scaleMaxTotal, scaleToTotal, techniquesOutsideKit } from '../../../core/lab.ts'
import { loyaltyOf, stageOf, statCap, styleBandOf, styleOf, totalStats, traitOf, type Monster } from '../../../core/monster.ts'
import { createRng } from '../../../core/rng.ts'
import { masteryLevel } from '../../../core/songbook.ts'
import { variantNameOf } from '../../../core/variants.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { DRILLS } from '../../../data/drills.ts'
import { FOODS } from '../../../data/foods.ts'
import { ITEM_BY_ID } from '../../../data/items.ts'
import { TECHNIQUE_BY_ID } from '../../../data/techniques.ts'
import { TRAITS } from '../../../data/traits.ts'
import { fill } from '../../../data/text/format.ts'
import { GROWTH_WORDS, STAGE_NAMES, STAT_NAMES, STYLE_LABELS } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { RANGES, SONGBOOK, STAGES, STAT_CAP_BY_GRADE } from '../../../data/tuning.ts'
import { BREED_IDS, GRADES, GROWTH_TYPES, STAT_KEYS, TOURNAMENT_GRADES, TOY_IDS, type BreedId, type Grade, type GrowthType, type StatKey, type Technique, type TournamentGrade } from '../../../data/types.ts'
import { Confirm, Field, Section, Select, Sheet, SliderRow, Stepper, Toggle, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { formatWhen } from '../../lib/clock.ts'
import { goBack, navigate } from '../../router.ts'
import { showToast } from '../../store/appStore.ts'
import { discardDraft, draft, draftDirty, draftRemovals, patchDraft, patchMonster, saveDraft, type EditorDraft } from '../../store/labStore.ts'
import { isDiscovered } from './LabCreate.tsx'

const t = UI_TEXT.lab.editor

const BREED_OPTIONS = BREED_IDS.map((id) => ({ value: id, label: `${BREED_BY_ID[id].name}${isDiscovered(id) ? '' : t.lockedSuffix}` }))
const GRADE_OPTIONS = GRADES.map((g) => ({ value: g, label: g }))
const GROWTH_OPTIONS = GROWTH_TYPES.map((g) => ({ value: g, label: GROWTH_WORDS[g] }))
const FOOD_OPTIONS = FOODS.map((f) => ({ value: f.id, label: f.name }))
const TOY_OPTIONS = TOY_IDS.map((id) => ({ value: id, label: ITEM_BY_ID[id]?.name ?? id }))
const DRILL_OPTIONS = DRILLS.map((d) => ({ value: d.id, label: d.name }))
const BATTLE_OPTIONS = (['-1', '0', '1'] as const).map((v) => ({ value: v, label: t.battleOptions[v] }))
const TGRADE_OPTIONS = TOURNAMENT_GRADES.map((g) => ({ value: g, label: g }))
const EXPR_OPTIONS: { value: Expression | 'auto'; label: string }[] = [{ value: 'auto', label: t.previewAuto }, ...EXPRESSIONS.map((e) => ({ value: e, label: t.expressions[e] }))]
const STAGE_OPTIONS: { value: string; label: string }[] = [{ value: 'auto', label: t.previewStageAuto }, ...STAGE_NAMES.map((name, i) => ({ value: String(i + 1), label: `${i + 1} ${name}` }))]

function statName(k: StatKey): string {
  return `${k} · ${STAT_NAMES[k]}`
}

/** The ten-segment life bar with the Prime window highlighted (§5.3). */
export function LifeBar({ m }: { m: Monster }) {
  const stage = stageOf(m)
  return (
    <div class="lifebar" aria-label={`${t.stage} ${stage} ${STAGE_NAMES[stage - 1]}`}>
      {STAGE_NAMES.map((_, i) => {
        const n = i + 1
        const cls = n === stage ? 'lifebar__seg--now' : n < stage ? 'lifebar__seg--lived' : STAGES.prime.includes(n) ? 'lifebar__seg--prime' : ''
        return <span key={n} class={`lifebar__seg ${cls}`} />
      })}
    </div>
  )
}

function BreedSelect({ label, value, onPick }: { label: string; value: BreedId; onPick: (id: BreedId) => void }) {
  const [asking, setAsking] = useState<BreedId | null>(null)
  return (
    <>
      <Select label={label} value={value} options={BREED_OPTIONS} onChange={(id) => (isDiscovered(id) || id === value ? onPick(id) : setAsking(id))} />
      <Confirm
        open={asking !== null}
        text={fill(UI_TEXT.lab.lockedAsk, { name: asking ? BREED_BY_ID[asking].name : '' })}
        confirmLabel={UI_TEXT.lab.useAnyway}
        cancelLabel={UI_TEXT.lab.keepSurprise}
        onConfirm={() => {
          if (asking) onPick(asking)
          setAsking(null)
        }}
        onCancel={() => setAsking(null)}
      />
    </>
  )
}

function TechniqueRows({ m }: { m: Monster }) {
  const outside = new Set(techniquesOutsideKit(m))
  if (m.techniques.length === 0) return <p class="muted">{t.none}</p>
  return (
    <div>
      {m.techniques.map((slot) => {
        const tech = TECHNIQUE_BY_ID[slot.id]
        return (
          <div class="tech" key={slot.id}>
            <span class="tech__name">
              <span>{tech?.name ?? slot.id}</span>
              <br />
              <span class="tech__meta">
                {tech ? `${tech.family} · ${tech.type} · R${tech.range}` : ''}
                {outside.has(slot.id) ? ' · ✎' : ''}
              </span>
            </span>
            <label class="tech__meta">
              {t.uses}
              <br />
              <input
                class="tech__num"
                type="number"
                inputMode="numeric"
                min={0}
                max={9999}
                value={slot.uses}
                onInput={(e) => {
                  const n = Math.max(0, Math.min(9999, Math.round(Number((e.currentTarget as HTMLInputElement).value) || 0)))
                  patchMonster((x) => {
                    const s = x.techniques.find((y) => y.id === slot.id)
                    if (s) {
                      s.uses = n
                      s.level = masteryLevel(n)
                    }
                  })
                }}
              />
            </label>
            <span class="pill">
              {t.level}
              {slot.level}
            </span>
            <button type="button" class="btn btn--small" onClick={() => patchMonster((x) => (x.techniques = x.techniques.filter((y) => y.id !== slot.id)))}>
              {t.remove}
            </button>
          </div>
        )
      })}
    </div>
  )
}

function AddTechniqueSheet({ d, open, onClose }: { d: EditorDraft; open: boolean; onClose: () => void }) {
  const m = d.monster
  const full = m.techniques.length >= SONGBOOK.maxTechniques
  const list = addableTechniques(m, d.allowAny)
  const groups: { key: keyof typeof t.groups; items: Technique[] }[] = [
    { key: 'kit', items: list.filter((x) => x.breed === m.mainBreed) },
    { key: 'universal', items: list.filter((x) => x.breed === 'universal') },
    { key: 'other', items: list.filter((x) => x.breed !== 'universal' && x.breed !== m.mainBreed) },
  ]
  const add = (id: string) => {
    patchMonster((x) => {
      if (x.techniques.length < SONGBOOK.maxTechniques && !x.techniques.some((y) => y.id === id)) x.techniques.push({ id, uses: 0, level: 1 })
    })
  }
  return (
    <Sheet open={open} title={t.addTitle} onClose={onClose}>
      <Toggle label={t.allowAny} hint={t.allowAnyHint} checked={d.allowAny} onChange={(v) => patchDraft((x) => (x.allowAny = v))} />
      {full && <p class="notice">{fill(t.full, { max: SONGBOOK.maxTechniques })}</p>}
      {groups.map(
        (grp) =>
          grp.items.length > 0 && (
            <div key={grp.key}>
              <p class="field__label">{t.groups[grp.key]}</p>
              {grp.items.map((x) => (
                <div class="tech" key={x.id}>
                  <span class="tech__name">
                    {x.name}
                    <br />
                    <span class="tech__meta">
                      {x.breed === 'universal' ? t.groups.universal : BREED_BY_ID[x.breed].name} · {x.family} · {x.type} · R{x.range}
                    </span>
                  </span>
                  <button type="button" class="btn btn--small btn--primary" disabled={full} onClick={() => add(x.id)}>
                    +
                  </button>
                </div>
              ))}
            </div>
          ),
      )}
      {list.length === 0 && <p class="muted">{t.noneToAdd}</p>}
      <div class="sheet__actions">
        <button type="button" class="btn" onClick={onClose}>
          {UI_TEXT.lab.actions.cancel}
        </button>
      </div>
    </Sheet>
  )
}

/** §19 Editor: every section, a live portrait, Save / Save as copy / Cancel, Revert, and the edit history. */
export function LabEditorScreen() {
  const d = draft.value
  const [confirmDiscard, setConfirmDiscard] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [scaleOpen, setScaleOpen] = useState(false)
  const [scaleValue, setScaleValue] = useState(0)
  const [previewStage, setPreviewStage] = useState('auto')

  useEffect(() => {
    if (!d) navigate('lab')
  }, [d])
  if (!d) return null

  const m = d.monster
  const total = totalStats(m.stats)
  const dirty = draftDirty(d)
  const removals = draftRemovals(d)
  const stage = stageOf(m)
  const open = d.openSection
  const toggle = (id: string) => patchDraft((x) => (x.openSection = x.openSection === id ? '' : id))

  const leave = () => {
    if (dirty) setConfirmDiscard(true)
    else {
      discardDraft()
      goBack()
    }
  }

  const save = async (asCopy: boolean) => {
    const name = m.name
    const active = d.origin === 'active' && !asCopy
    const saved = await saveDraft(asCopy)
    if (saved) {
      showToast(fill(active ? t.savedActive : asCopy ? t.savedCopy : t.saved, { name: saved.name || name }))
      if (active || (d.origin === 'freezer' && !asCopy)) goBack()
      else navigate('labView')
    }
  }

  const changeBreed = (breed: BreedId) => patchDraft((x) => (x.monster = applyBreedChange(x.monster, breed, true).monster))

  const restore = (index: number) => {
    const entry = d.history[index]
    if (!entry) return
    patchDraft((x) => {
      x.monster = structuredClone(entry.monster)
      x.monster.id = x.original.id
    })
    showToast(fill(t.restored, { when: formatWhen(entry.savedAt) }))
  }

  const previewExpression = d.preview === 'auto' ? undefined : d.preview
  const previewStageNum = previewStage === 'auto' ? undefined : Number(previewStage)

  return (
    <main class="screen">
      <TopBar
        title={d.origin === 'new' ? t.titleNew : d.origin === 'active' ? fill(t.titleActive, { name: d.original.name }) : t.title}
        onBack={leave}
        right={
          <button
            type="button"
            class="btn btn--small btn--ghost"
            disabled={!dirty}
            onClick={() => {
              patchDraft((x) => (x.monster = structuredClone(x.original)))
              showToast(t.reverted)
            }}
          >
            {t.revert}
          </button>
        }
      />
      <div class="preview">
        <MonsterPortrait monster={m} size={120} expression={previewExpression} stage={previewStageNum} live />
        <div class="preview__info">
          <span class="preview__name">{m.name || BREED_BY_ID[m.mainBreed].name}</span>
          <span class="muted small">
            {variantNameOf(m)} · {t.total} {total}
          </span>
          <span class="muted small">
            {STAGE_NAMES[stage - 1]} · {fatigueLabel(m.fatigue)} · {stressLabel(m.stress)}
          </span>
        </div>
      </div>

      <Section id="identity" title={t.sections.identity} open={open === 'identity'} onToggle={toggle} summary={m.name}>
        <Field label={t.name} hint={t.nameHint}>
          <input class="input" value={m.name} maxLength={RANGES.nameLength.max} onInput={(e) => patchMonster((x) => (x.name = (e.currentTarget as HTMLInputElement).value.slice(0, RANGES.nameLength.max)))} />
        </Field>
        <BreedSelect label={t.breed} value={m.mainBreed} onPick={changeBreed} />
        {removals.length > 0 && (
          <p class="notice">
            {t.willRemove} {removals.map((id) => TECHNIQUE_BY_ID[id]?.name ?? id).join(', ')}
          </p>
        )}
        {m.mainBreed !== d.original.mainBreed && <Toggle label={t.keepAll} checked={d.keepAll} onChange={(v) => patchDraft((x) => (x.keepAll = v))} />}
      </Section>

      <Section id="stats" title={t.sections.stats} open={open === 'stats'} onToggle={toggle} summary={`${t.total} ${total}`}>
        {STAT_KEYS.map((k) => (
          <SliderRow
            key={k}
            label={statName(k)}
            value={m.stats[k]}
            min={RANGES.stat.min}
            max={RANGES.stat.max}
            sliderMax={STAT_CAP_BY_GRADE.S}
            onChange={(v) => patchMonster((x) => (x.stats[k] = v))}
            extra={
              <span class="muted small">
                {m.grades[k]} · {fill(t.capOf, { n: statCap(m, k).toLocaleString('en-US') })}
                {m.records.fromSweets[k] > 0 ? ` · ${fill(t.fromSweets, { n: m.records.fromSweets[k] })}` : ''}
              </span>
            }
          />
        ))}
        <div class="btn-grid">
          <button type="button" class="btn" onClick={() => patchMonster((x) => (x.stats = breedBaseStats(x)))}>
            {t.statButtons.base}
          </button>
          <button type="button" class="btn" onClick={() => patchMonster((x) => (x.stats = maxAllStats(x)))}>
            {t.statButtons.max}
          </button>
          <button
            type="button"
            class="btn"
            onClick={() => {
              setScaleValue(total)
              setScaleOpen(true)
            }}
          >
            {t.statButtons.scale}
          </button>
          <button type="button" class="btn" onClick={() => patchMonster((x) => (x.stats = randomizeStats(x.stats, createRng(Math.floor(Math.random() * 0xffffffff)))))}>
            {t.statButtons.randomize}
          </button>
        </div>
      </Section>

      <Section id="growth" title={t.sections.growth} open={open === 'growth'} onToggle={toggle} summary={`${GROWTH_WORDS[m.growthType]} · ${STAGE_NAMES[stage - 1]}`}>
        <p class="field__label">{t.grades}</p>
        <div class="grid2">
          {STAT_KEYS.map((k) => (
            <Select key={k} label={k} value={m.grades[k]} options={GRADE_OPTIONS} onChange={(g: Grade) => patchMonster((x) => (x.grades[k] = g))} />
          ))}
        </div>
        <Select label={t.growthType} value={m.growthType} options={GROWTH_OPTIONS} onChange={(g: GrowthType) => patchMonster((x) => (x.growthType = g))} />
        <Select
          label={t.inheritedTrait}
          value={m.inheritedTrait ?? 'none'}
          options={[{ value: 'none', label: t.noInheritedTrait }, ...TRAITS.filter((tr) => tr.id !== traitOf(m)).map((tr) => ({ value: tr.id, label: tr.name }))]}
          onChange={(v: string) => patchMonster((x) => (x.inheritedTrait = v === 'none' ? null : (v as Monster['inheritedTrait'])))}
        />
        <Field label={t.gutsRate} hint={t.gutsHint}>
          <Stepper value={m.gutsRate} min={RANGES.gutsRate.min} max={RANGES.gutsRate.max} big={5} onChange={(v) => patchMonster((x) => (x.gutsRate = v))} label={t.gutsRate} />
        </Field>
        <Field label={t.lifespan}>
          <Stepper value={m.lifespanTotal} min={RANGES.lifespan.min} max={RANGES.lifespan.max} big={10} onChange={(v) => patchMonster((x) => (x.lifespanTotal = v))} label={t.lifespan} />
        </Field>
        <Field label={t.age}>
          <Stepper value={m.ageWeeks} min={0} max={RANGES.lifespan.max} big={10} onChange={(v) => patchMonster((x) => (x.ageWeeks = v))} label={t.age} />
        </Field>
        <Field label={`${t.stage}: ${stage} ${STAGE_NAMES[stage - 1]}`}>
          <LifeBar m={m} />
        </Field>
        <button type="button" class="btn" onClick={() => patchDraft((x) => (x.monster = resetGrowthToBreed(x.monster)))}>
          {t.resetGrowth}
        </button>
      </Section>

      <Section id="condition" title={t.sections.condition} open={open === 'condition'} onToggle={toggle} summary={`${t.loyalty} ${loyaltyOf(m)}`}>
        <SliderRow label={t.fatigue} value={m.fatigue} min={0} max={100} onChange={(v) => patchMonster((x) => (x.fatigue = v))} extra={<span class="muted small">{fatigueLabel(m.fatigue)}</span>} />
        <SliderRow label={t.stress} value={m.stress} min={0} max={100} onChange={(v) => patchMonster((x) => (x.stress = v))} extra={<span class="muted small">{stressLabel(m.stress)}</span>} />
        <SliderRow label={t.spoil} value={m.spoil} min={0} max={100} onChange={(v) => patchMonster((x) => (x.spoil = v))} />
        <SliderRow label={t.fear} value={m.fear} min={0} max={100} onChange={(v) => patchMonster((x) => (x.fear = v))} />
        <p class="muted small">
          {t.loyalty} {loyaltyOf(m)} ({loyaltyLabel(loyaltyOf(m))}) · {t.style} {styleOf(m)} ({STYLE_LABELS[styleBandOf(styleOf(m))]})
        </p>
        <SliderRow label={t.nature} value={m.nature} min={RANGES.nature.min} max={RANGES.nature.max} onChange={(v) => patchMonster((x) => (x.nature = v))} extra={<span class="muted small">{t.natureHint}</span>} />
        <SliderRow label={t.form} value={m.form} min={RANGES.form.min} max={RANGES.form.max} onChange={(v) => patchMonster((x) => (x.form = v))} extra={<span class="muted small">{t.formHint}</span>} />
        <SliderRow label={t.fame} value={m.fame} min={RANGES.fame.min} max={RANGES.fame.max} onChange={(v) => patchMonster((x) => (x.fame = v))} />
        <div class="grid2">
          <Field label={t.injured}>
            <Stepper value={m.status.injuredWeeks} min={0} max={52} big={4} onChange={(v) => patchMonster((x) => (x.status.injuredWeeks = v))} label={t.injured} />
          </Field>
          <Field label={t.sick}>
            <Stepper value={m.status.sickWeeks} min={0} max={52} big={4} onChange={(v) => patchMonster((x) => (x.status.sickWeeks = v))} label={t.sick} />
          </Field>
        </div>
      </Section>

      <Section id="personality" title={t.sections.personality} open={open === 'personality'} onToggle={toggle}>
        <Select label={t.likedFood} value={m.likes.food} options={FOOD_OPTIONS} onChange={(v) => patchMonster((x) => (x.likes.food = v))} />
        <Select label={t.dislikedFood} value={m.likes.dislikedFood} options={FOOD_OPTIONS} onChange={(v) => patchMonster((x) => (x.likes.dislikedFood = v))} />
        <Select label={t.toy} value={m.likes.toy} options={TOY_OPTIONS} onChange={(v) => patchMonster((x) => (x.likes.toy = v))} />
        <Select label={t.battle} value={String(m.likes.battle) as '-1' | '0' | '1'} options={BATTLE_OPTIONS} onChange={(v) => patchMonster((x) => (x.likes.battle = Number(v) as -1 | 0 | 1))} />
        <Select label={t.likedDrill} value={m.likes.drill} options={DRILL_OPTIONS} onChange={(v) => patchMonster((x) => (x.likes.drill = v))} />
        <Select label={t.dislikedDrill} value={m.likes.dislikedDrill} options={DRILL_OPTIONS} onChange={(v) => patchMonster((x) => (x.likes.dislikedDrill = v))} />
      </Section>

      <Section id="techniques" title={t.sections.techniques} open={open === 'techniques'} onToggle={toggle} summary={fill(t.learned, { n: m.techniques.length, max: SONGBOOK.maxTechniques })}>
        <TechniqueRows m={m} />
        <button type="button" class="btn" onClick={() => setAddOpen(true)}>
          {t.add}
        </button>
      </Section>

      <Section id="records" title={t.sections.records} open={open === 'records'} onToggle={toggle} summary={`${t.tournamentGrade} ${m.grade}`}>
        <Select label={t.tournamentGrade} value={m.grade} options={TGRADE_OPTIONS} onChange={(g: TournamentGrade) => patchMonster((x) => (x.grade = g))} />
        <Field label={t.wins}>
          <Stepper value={m.records.wins} min={0} max={99_999} onChange={(v) => patchMonster((x) => (x.records.wins = v))} label={t.wins} />
        </Field>
        <Field label={t.losses}>
          <Stepper value={m.records.losses} min={0} max={99_999} onChange={(v) => patchMonster((x) => (x.records.losses = v))} label={t.losses} />
        </Field>
        <Field label={t.draws}>
          <Stepper value={m.records.draws} min={0} max={99_999} onChange={(v) => patchMonster((x) => (x.records.draws = v))} label={t.draws} />
        </Field>
        <Field label={t.titles}>
          <input
            class="input"
            value={m.records.titles.join(', ')}
            onChange={(e) =>
              patchMonster(
                (x) =>
                  (x.records.titles = (e.currentTarget as HTMLInputElement).value
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean)),
              )
            }
          />
        </Field>
      </Section>

      <Section id="appearance" title={t.sections.appearance} open={open === 'appearance'} onToggle={toggle}>
        <Select label={t.previewExpression} value={d.preview} options={EXPR_OPTIONS} onChange={(v) => patchDraft((x) => (x.preview = v))} />
        <Select label={t.previewStage} value={previewStage} options={STAGE_OPTIONS} onChange={setPreviewStage} />
      </Section>

      <Section id="history" title={t.sections.history} open={open === 'history'} onToggle={toggle} summary={String(d.history.length)}>
        {d.history.length === 0 ? (
          <p class="muted">{t.noHistory}</p>
        ) : (
          <div class="history">
            {[...d.history].reverse().map((h, i) => {
              const index = d.history.length - 1 - i
              return (
                <div class="history__row" key={index}>
                  <MonsterPortrait monster={h.monster} size={48} animate={false} />
                  <span class="grow small">{fill(t.historyRow, { when: formatWhen(h.savedAt), total: totalStats(h.monster.stats) })}</span>
                  <button type="button" class="btn btn--small" onClick={() => restore(index)}>
                    {t.restore}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </Section>

      <p class="muted small center">{d.origin === 'active' ? t.activeNote : t.editedNote}</p>
      <div class="actionbar">
        <button type="button" class="btn btn--primary btn--half" onClick={() => void save(false)}>
          {t.save}
        </button>
        {(d.origin === 'library' || d.origin === 'active' || d.origin === 'freezer') && (
          <button type="button" class="btn btn--half" onClick={() => void save(true)}>
            {t.saveCopy}
          </button>
        )}
        <button type="button" class="btn btn--half btn--ghost" onClick={leave}>
          {t.cancel}
        </button>
      </div>

      <Confirm
        open={confirmDiscard}
        text={t.discardAsk}
        confirmLabel={t.discard}
        cancelLabel={t.keepEditing}
        danger
        onConfirm={() => {
          setConfirmDiscard(false)
          discardDraft()
          goBack()
        }}
        onCancel={() => setConfirmDiscard(false)}
      />
      <AddTechniqueSheet d={d} open={addOpen} onClose={() => setAddOpen(false)} />
      <Sheet open={scaleOpen} title={t.scaleTitle} onClose={() => setScaleOpen(false)}>
        <Field label={t.scaleTitle} hint={fill(t.scaleHint, { max: scaleMaxTotal(m.grades).toLocaleString('en-US') })}>
          <Stepper value={scaleValue} min={RANGES.stat.min * STAT_KEYS.length} max={scaleMaxTotal(m.grades)} big={100} onChange={setScaleValue} label={t.scaleTitle} />
        </Field>
        <div class="sheet__actions">
          <button
            type="button"
            class="btn btn--primary"
            onClick={() => {
              patchMonster((x) => (x.stats = scaleToTotal(x.grades, scaleValue)))
              setScaleOpen(false)
            }}
          >
            {t.apply}
          </button>
          <button type="button" class="btn" onClick={() => setScaleOpen(false)}>
            {UI_TEXT.lab.actions.cancel}
          </button>
        </div>
      </Sheet>
    </main>
  )
}
