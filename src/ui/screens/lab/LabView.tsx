import { useEffect } from 'preact/hooks'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TopBar } from '../../components/Controls.tsx'
import { MonsterSheet } from '../../components/MonsterSheet.tsx'
import { navigate } from '../../router.ts'
import { selectedListed, startEdit } from '../../store/labStore.ts'

/** §21 Monster Card (the Lab's read-only view). The Lab is creative mode, so it always shows the Breeder's Lens. */
export function LabViewScreen() {
  const t = UI_TEXT.lab.view
  const listed = selectedListed()
  useEffect(() => {
    if (!listed) navigate('lab')
  }, [listed])
  if (!listed) return null
  return (
    <main class="screen">
      <TopBar title={t.title} />
      <MonsterSheet m={listed.monster} mode="lens" editCount={listed.history.length} />
      <div class="actionbar">
        {listed.source !== 'memorial' && (
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
        )}
        <button type="button" class="btn btn--half" onClick={() => navigate('labExport')}>
          {UI_TEXT.lab.actions.export}
        </button>
      </div>
    </main>
  )
}
