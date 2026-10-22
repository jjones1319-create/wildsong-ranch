import { useEffect, useRef, useState } from 'preact/hooks'
import { mixBreeds, totalStats, type Monster } from '../../../core/monster.ts'
import { fill } from '../../../data/text/format.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { UI } from '../../../data/tuning.ts'
import { readImport } from '../../../save/exportImport.ts'
import type { AnyValidation, HistoryEntry, LibraryEntry } from '../../../save/schema.ts'
import { TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { now } from '../../lib/clock.ts'
import { readFileText } from '../../lib/files.ts'
import { newId } from '../../lib/ids.ts'
import { navigate, pendingImport } from '../../router.ts'
import { addEntries, showToast } from '../../store/appStore.ts'
import { labTab, selected } from '../../store/labStore.ts'

interface Incoming {
  monster: Monster
  history: HistoryEntry[]
}

function incomingFrom(r: AnyValidation): Incoming[] {
  if (!r.ok) return []
  if (r.kind === 'monster') return [{ monster: r.file.monster, history: r.file.history }]
  if (r.kind === 'save') return r.save.game.monster ? [{ monster: r.save.game.monster, history: [] }] : []
  return r.library.entries.map((e) => ({ monster: e.monster, history: e.history }))
}

/** §19 Import: paste a code or file text, open a file, or arrive from an `#import=` link. Preview, then add with fresh ids. */
export function LabImportScreen() {
  const t = UI_TEXT.lab.import_
  const [text, setText] = useState('')
  const [fromLink, setFromLink] = useState(false)
  const [result, setResult] = useState<AnyValidation | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const code = pendingImport.value
    if (code) {
      pendingImport.value = null
      setFromLink(true)
      setText(code)
    }
  }, [])

  useEffect(() => {
    let alive = true
    const timer = setTimeout(() => {
      void readImport(text).then((r) => {
        if (alive) setResult(text.trim() ? r : null)
      })
    }, UI.importDebounceMs)
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [text])

  const pickFile = async (file: File | undefined) => {
    if (!file) return
    const content = await readFileText(file)
    if (content === null) showToast(UI_TEXT.errors.fileUnreadable)
    else setText(content)
  }

  const incoming = result ? incomingFrom(result) : []

  const accept = async () => {
    if (incoming.length === 0) return
    const when = now()
    const entries: LibraryEntry[] = incoming.map((i) => ({ monster: { ...i.monster, id: newId() }, history: i.history, createdAt: when, updatedAt: when }))
    await addEntries(entries)
    labTab.value = 'library'
    selected.value = { source: 'library', id: entries[0]!.monster.id }
    showToast(entries.length === 1 ? fill(t.added, { name: entries[0]!.monster.name }) : fill(t.addedMany, { n: entries.length }))
    navigate(entries.length === 1 ? 'labView' : 'lab')
  }

  const acceptLabel = result?.ok && result.kind === 'save' ? t.acceptSave : result?.ok && result.kind === 'library' ? fill(t.acceptLibrary, { n: incoming.length }) : t.accept

  return (
    <main class="screen">
      <TopBar title={t.title} />
      {fromLink && <p class="notice notice--ok">{t.fromLink}</p>}
      <label class="field">
        <span class="field__label">{t.paste}</span>
        <textarea class="textarea" value={text} rows={5} spellcheck={false} autoCapitalize="off" onInput={(e) => setText((e.currentTarget as HTMLTextAreaElement).value)} />
      </label>
      <button type="button" class="btn" onClick={() => fileRef.current?.click()}>
        {t.pickFile}
      </button>
      <input ref={fileRef} class="file-input" type="file" accept=".json,.txt,application/json,text/plain" onChange={(e) => void pickFile((e.currentTarget as HTMLInputElement).files?.[0])} />

      <section class="card">
        <p class="field__label">{t.preview}</p>
        {!result && <p class="muted">{UI_TEXT.errors.nothingToImport}</p>}
        {result && !result.ok && <p class="notice">{result.error}</p>}
        {result?.ok && result.kind === 'save' && <p class="muted small">{incoming.length ? t.saveNote : t.saveNoMonster}</p>}
        {result?.ok && result.kind === 'library' && <p class="muted small">{incoming.length ? t.libraryNote : t.emptyLibrary}</p>}
        {incoming.slice(0, 6).map((i, idx) => (
          <div class="row" key={idx} style={{ marginTop: 8 }}>
            <MonsterPortrait monster={i.monster} size={72} animate={false} />
            <div class="grow">
              <div>
                <strong>{i.monster.name}</strong>
              </div>
              <div class="muted small">
                {mixBreeds(i.monster.mainBreed, i.monster.subBreed).variantName} · {UI_TEXT.lab.total} {totalStats(i.monster.stats)} · {UI_TEXT.lab.grade} {i.monster.grade}
              </div>
            </div>
          </div>
        ))}
        {incoming.length > 6 && <p class="muted small">… +{incoming.length - 6}</p>}
      </section>

      <div class="spacer" />
      <div class="actionbar">
        <button type="button" class="btn btn--primary" disabled={incoming.length === 0} onClick={() => void accept()}>
          {acceptLabel}
        </button>
      </div>
    </main>
  )
}
