import { useState } from 'preact/hooks'
import { duplicateMonster } from '../../../core/lab.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { RANGES } from '../../../data/tuning.ts'
import { BREED_IDS, type BreedId } from '../../../data/types.ts'
import { Chips, Confirm, Segmented, Sheet, TopBar } from '../../components/Controls.tsx'
import { MonsterCard } from '../../components/MonsterCard.tsx'
import { now } from '../../lib/clock.ts'
import { newId } from '../../lib/ids.ts'
import { navigate } from '../../router.ts'
import { library, removeEntry, showToast, upsertEntry } from '../../store/appStore.ts'
import { labBreedFilter, labSort, labTab, selected, startEdit, visible, type LabSort, type LabSource, type Listed } from '../../store/labStore.ts'

const BREED_OPTIONS: { value: BreedId | 'all'; label: string }[] = [{ value: 'all', label: UI_TEXT.lab.filterAll }, ...BREED_IDS.map((id) => ({ value: id, label: BREED_BY_ID[id].name }))]
const SORT_OPTIONS: { value: LabSort; label: string }[] = (['date', 'total', 'age', 'name'] as const).map((v) => ({ value: v, label: UI_TEXT.lab.sort[v] }))
const TAB_OPTIONS: { value: LabSource; label: string }[] = [
  { value: 'library', label: UI_TEXT.lab.tabs.library },
  { value: 'presets', label: UI_TEXT.lab.tabs.presets },
]

/** §19 Library: Library creations and Presets, filter, sort, and the action sheet for a card. */
export function LabLibraryScreen() {
  const t = UI_TEXT.lab
  const [sheetFor, setSheetFor] = useState<Listed | null>(null)
  const [deleting, setDeleting] = useState<Listed | null>(null)
  const items = visible.value
  const libraryEmpty = library.value.entries.length === 0

  const open = (l: Listed, target: 'labView' | 'labEdit' | 'labExport') => {
    selected.value = { source: l.source, id: l.id }
    if (target === 'labEdit') startEdit(l)
    setSheetFor(null)
    navigate(target)
  }

  const duplicate = async (l: Listed) => {
    const when = now()
    const copy = duplicateMonster(l.monster, newId())
    copy.name = `${l.monster.name}${t.copySuffix}`.slice(0, RANGES.nameLength.max)
    setSheetFor(null)
    await upsertEntry({ monster: copy, history: [], createdAt: when, updatedAt: when })
    labTab.value = 'library'
    showToast(fill(t.duplicated, { name: l.monster.name }))
  }

  const confirmDelete = async () => {
    const l = deleting
    setDeleting(null)
    if (!l) return
    await removeEntry(l.id)
    showToast(fill(t.deleted, { name: l.monster.name }))
  }

  return (
    <main class="screen">
      <TopBar
        title={t.title}
        right={
          <button type="button" class="btn btn--small" onClick={() => navigate('labImport')}>
            {t.import}
          </button>
        }
      />
      {libraryEmpty && labTab.value === 'library' && (
        <section class="card">
          <p class="speaker">{UI_TEXT.pell}</p>
          <p>{t.welcome}</p>
        </section>
      )}
      <div class="row">
        <button type="button" class="btn btn--half" onClick={() => navigate('labVersus')}>
          ⚔ {t.versus}
        </button>
        <button type="button" class="btn btn--half" onClick={() => navigate('labBattleLab')}>
          🧪 {t.battleLab}
        </button>
      </div>
      <Segmented options={TAB_OPTIONS} value={labTab.value} onChange={(v) => (labTab.value = v)} label={t.title} />
      <Chips options={BREED_OPTIONS} value={labBreedFilter.value} onChange={(v) => (labBreedFilter.value = v)} label={t.filterAll} />
      <Chips options={SORT_OPTIONS} value={labSort.value} onChange={(v) => (labSort.value = v)} />
      <div class="list">
        {items.map((l) => (
          <MonsterCard key={l.id} listed={l} onTap={setSheetFor} />
        ))}
      </div>
      {items.length === 0 && <p class="empty">{labTab.value === 'library' && labBreedFilter.value === 'all' ? t.empty : t.emptyFilter}</p>}
      <div class="spacer" />
      <div class="actionbar">
        <button type="button" class="btn btn--primary" onClick={() => navigate('labCreate')}>
          {t.create}
        </button>
      </div>

      <Sheet open={sheetFor !== null} title={sheetFor?.monster.name} onClose={() => setSheetFor(null)}>
        {sheetFor && (
          <div class="sheet__actions">
            <button type="button" class="btn btn--primary" onClick={() => open(sheetFor, 'labView')}>
              {t.actions.view}
            </button>
            <button type="button" class="btn" onClick={() => open(sheetFor, 'labEdit')}>
              {t.actions.edit}
            </button>
            <button type="button" class="btn" onClick={() => void duplicate(sheetFor)}>
              {t.actions.duplicate}
            </button>
            <button type="button" class="btn" onClick={() => open(sheetFor, 'labExport')}>
              {t.actions.export}
            </button>
            {sheetFor.source === 'library' && (
              <button
                type="button"
                class="btn btn--ghost"
                onClick={() => {
                  setDeleting(sheetFor)
                  setSheetFor(null)
                }}
              >
                {t.actions.delete}
              </button>
            )}
            <button type="button" class="btn btn--ghost" onClick={() => setSheetFor(null)}>
              {t.actions.cancel}
            </button>
          </div>
        )}
      </Sheet>
      <Confirm open={deleting !== null} text={fill(t.deleteAsk, { name: deleting?.monster.name ?? '' })} confirmLabel={t.actions.delete} danger onConfirm={() => void confirmDelete()} onCancel={() => setDeleting(null)} />
    </main>
  )
}
