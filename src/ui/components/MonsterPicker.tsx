import { useState } from 'preact/hooks'
import { totalStats, type Monster } from '../../core/monster.ts'
import { variantNameOf } from '../../core/variants.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { Segmented, Sheet } from './Controls.tsx'
import { MonsterCard } from './MonsterCard.tsx'
import { MonsterPortrait } from './MonsterPortrait.tsx'
import { game } from '../store/gameStore.ts'
import { library } from '../store/appStore.ts'
import { listFreezer, listPresets, type Listed } from '../store/labStore.ts'

/** A monster chosen for Versus or the Battle Lab, with where it came from. */
export interface Picked {
  monster: Monster
  source: 'active' | 'library' | 'freezer' | 'presets'
}

type Source = Picked['source']

/** The "Choose…" row: a dashed slot that opens the picker sheet. */
export function PickSlot({ label, picked, onPick }: { label: string; picked: Picked | null; onPick: (p: Picked) => void }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" class={`pick ${picked ? 'pick--set' : ''}`} onClick={() => setOpen(true)}>
        {picked ? <MonsterPortrait monster={picked.monster} size={72} animate={false} /> : <span style={{ width: 72, textAlign: 'center', fontSize: '2em' }}>？</span>}
        <span class="pick__body">
          <span class="pick__label">{label}</span>
          <span class="pick__name">{picked ? picked.monster.name : UI_TEXT.versus.pick}</span>
          {picked && (
            <span class="muted small">
              {variantNameOf(picked.monster)} · {UI_TEXT.lab.total} {totalStats(picked.monster.stats)}
            </span>
          )}
        </span>
      </button>
      <PickerSheet
        open={open}
        onClose={() => setOpen(false)}
        onPick={(p) => {
          setOpen(false)
          onPick(p)
        }}
      />
    </>
  )
}

export function PickerSheet({ open, onClose, onPick }: { open: boolean; onClose: () => void; onPick: (p: Picked) => void }) {
  const t = UI_TEXT.versus
  const g = game.value
  const frozen = listFreezer()
  const [source, setSource] = useState<Source>(g?.monster ? 'active' : frozen.length ? 'freezer' : 'library')
  const rows: Listed[] =
    source === 'active'
      ? g?.monster
        ? [{ id: g.monster.id, monster: g.monster, source: 'library', history: [], createdAt: 0, updatedAt: 0 }]
        : []
      : source === 'library'
        ? library.value.entries.map((e) => ({ id: e.monster.id, monster: e.monster, source: 'library' as const, history: e.history, createdAt: e.createdAt, updatedAt: e.updatedAt }))
        : source === 'freezer'
          ? frozen
          : listPresets()
  const options: { value: Source; label: string }[] = [
    ...(g?.monster ? [{ value: 'active' as const, label: t.sources.active }] : []),
    ...(g && frozen.length ? [{ value: 'freezer' as const, label: UI_TEXT.versusSources.freezer }] : []),
    { value: 'library', label: t.sources.library },
    { value: 'presets', label: t.sources.presets },
  ]
  return (
    <Sheet open={open} title={t.pickTitle} onClose={onClose}>
      <Segmented options={options} value={source} onChange={setSource} label={t.pickTitle} />
      <div class="list" style={{ marginTop: 10 }}>
        {rows.length === 0 && <p class="empty">{t.noneHere}</p>}
        {rows.map((l) => (
          <MonsterCard key={l.id} listed={l} onTap={(x) => onPick({ monster: structuredClone(x.monster), source })} />
        ))}
      </div>
    </Sheet>
  )
}
