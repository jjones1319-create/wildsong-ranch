import { useState } from 'preact/hooks'
import { duplicateMonster } from '../../../core/lab.ts'
import { freezerFull } from '../../../core/legacy.ts'
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
import { adoptMonster, game, makeActive, sendToFreezer } from '../../store/gameStore.ts'
import { labBreedFilter, labSort, labTab, selected, startEdit, visible, type LabSort, type LabSource, type Listed } from '../../store/labStore.ts'

const BREED_OPTIONS: { value: BreedId | 'all'; label: string }[] = [{ value: 'all', label: UI_TEXT.lab.filterAll }, ...BREED_IDS.map((id) => ({ value: id, label: BREED_BY_ID[id].name }))]
const SORT_OPTIONS: { value: LabSort; label: string }[] = (['date', 'total', 'age', 'name'] as const).map((v) => ({ value: v, label: UI_TEXT.lab.sort[v] }))

/** §19 Library: Library creations, the ranch's Freezer and Memorial, and Presets; filter, sort, and the action sheet for a card. */
export function LabLibraryScreen() {
  const t = UI_TEXT.lab
  const g = game.value
  const [sheetFor, setSheetFor] = useState<Listed | null>(null)
  const [deleting, setDeleting] = useState<Listed | null>(null)
  const [activating, setActivating] = useState<Listed | null>(null)
  const items = visible.value
  const libraryEmpty = library.value.entries.length === 0
  const tabs: { value: LabSource; label: string }[] = [
    { value: 'library', label: t.tabs.library },
    ...(g ? [{ value: 'freezer' as const, label: UI_TEXT.labSources.freezer }, { value: 'memorial' as const, label: UI_TEXT.labSources.memorial }] : []),
    { value: 'presets', label: t.tabs.presets },
  ]
  const tab = tabs.some((x) => x.value === labTab.value) ? labTab.value : 'library'

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

  const toFreezer = (l: Listed) => {
    setSheetFor(null)
    const refused = sendToFreezer({ ...structuredClone(l.monster), id: newId() })
    showToast(refused === 'full' ? UI_TEXT.pellLab.freezeFull : refused ? UI_TEXT.pellLab.freezeBusy : fill(UI_TEXT.pellLab.sentToFreezer, { name: l.monster.name }))
  }

  const confirmActivate = () => {
    const l = activating
    setActivating(null)
    if (!l) return
    const refused = l.source === 'freezer' ? makeActive(l.id) : adoptMonster({ ...structuredClone(l.monster), id: newId() })
    if (!refused) {
      showToast(fill(UI_TEXT.pellLab.madeActive, { name: l.monster.name }))
      navigate('ranch')
    } else showToast(refused === 'busy' ? UI_TEXT.pellLab.freezeBusy : refused === 'full' ? UI_TEXT.pellLab.freezeFull : UI_TEXT.pellLab.freezeBusy)
  }

  const confirmDelete = async () => {
    const l = deleting
    setDeleting(null)
    if (!l) return
    await removeEntry(l.id)
    showToast(fill(t.deleted, { name: l.monster.name }))
  }

  const canStore = g !== null && !g.ended
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
      {libraryEmpty && tab === 'library' && (
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
      <Segmented options={tabs} value={tab} onChange={(v) => (labTab.value = v)} label={t.title} />
      <Chips options={BREED_OPTIONS} value={labBreedFilter.value} onChange={(v) => (labBreedFilter.value = v)} label={t.filterAll} />
      <Chips options={SORT_OPTIONS} value={labSort.value} onChange={(v) => (labSort.value = v)} />
      <div class="list">
        {items.map((l) => (
          <MonsterCard key={l.id} listed={l} onTap={setSheetFor} />
        ))}
      </div>
      {items.length === 0 && <p class="empty">{tab === 'library' && labBreedFilter.value === 'all' ? t.empty : tab === 'freezer' ? UI_TEXT.pellLab.empty : tab === 'memorial' ? UI_TEXT.pellLab.memorialEmpty : t.emptyFilter}</p>}
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
            {sheetFor.source !== 'memorial' && (
              <button type="button" class="btn" onClick={() => open(sheetFor, 'labEdit')}>
                {t.actions.edit}
              </button>
            )}
            <button type="button" class="btn" onClick={() => void duplicate(sheetFor)}>
              {sheetFor.source === 'memorial' ? UI_TEXT.pellLab.duplicate : t.actions.duplicate}
            </button>
            <button type="button" class="btn" onClick={() => open(sheetFor, 'labExport')}>
              {t.actions.export}
            </button>
            {canStore && sheetFor.source !== 'memorial' && (
              <button
                type="button"
                class="btn"
                onClick={() => {
                  setActivating(sheetFor)
                  setSheetFor(null)
                }}
              >
                {UI_TEXT.labActions.makeActive}
              </button>
            )}
            {canStore && (sheetFor.source === 'library' || sheetFor.source === 'presets') && (
              <button type="button" class="btn" disabled={g !== null && freezerFull(g)} onClick={() => toFreezer(sheetFor)}>
                {UI_TEXT.labActions.sendToFreezer}
              </button>
            )}
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
      <Confirm
        open={activating !== null}
        text={activating ? (g?.monster ? fill(UI_TEXT.pellLab.makeActiveAsk, { name: activating.monster.name, current: g.monster.name }) : fill(UI_TEXT.pellLab.makeActiveAskEmpty, { name: activating.monster.name })) : ''}
        confirmLabel={UI_TEXT.labActions.makeActive}
        onConfirm={confirmActivate}
        onCancel={() => setActivating(null)}
      />
    </main>
  )
}
