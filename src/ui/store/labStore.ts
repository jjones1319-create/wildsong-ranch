import { computed, signal } from '@preact/signals'
import type { Expression } from '../../art/monster/expressions.ts'
import { finishEdit, pushHistory, techniquesOutsideKit, type EditHistoryEntry } from '../../core/lab.ts'
import { totalStats, type Monster } from '../../core/monster.ts'
import { allPresets, type PresetTier } from '../../core/presets.ts'
import { BREED_IDS, type BreedId } from '../../data/types.ts'
import type { LibraryEntry } from '../../save/schema.ts'
import { now } from '../lib/clock.ts'
import { newId } from '../lib/ids.ts'
import { findEntry, library, upsertEntry } from './appStore.ts'
import { replaceMonster } from './gameStore.ts'

/** Monster Lab screen state (§19): the Library view, what is selected, and the editor's draft. */

export type LabSource = 'library' | 'presets'
export type LabSort = 'date' | 'total' | 'age' | 'name'

export const labTab = signal<LabSource>('library')
export const labBreedFilter = signal<BreedId | 'all'>('all')
export const labSort = signal<LabSort>('date')
/** The monster View / Edit / Export act on. */
export const selected = signal<{ source: LabSource; id: string } | null>(null)

export interface Listed {
  id: string
  monster: Monster
  source: LabSource
  history: EditHistoryEntry[]
  createdAt: number
  updatedAt: number
  tier?: PresetTier
}

let presetCache: Listed[] | null = null

export function listPresets(): Listed[] {
  presetCache ??= allPresets().map((p) => ({ id: p.id, monster: p.monster, source: 'presets', history: [], createdAt: 0, updatedAt: 0, tier: p.tier }))
  return presetCache
}

function fromEntry(e: LibraryEntry): Listed {
  return { id: e.monster.id, monster: e.monster, source: 'library', history: e.history, createdAt: e.createdAt, updatedAt: e.updatedAt }
}

function sortBy(list: Listed[], sort: LabSort): Listed[] {
  const copy = [...list]
  switch (sort) {
    case 'date':
      return copy.sort((a, b) => b.updatedAt - a.updatedAt)
    case 'total':
      return copy.sort((a, b) => totalStats(b.monster.stats) - totalStats(a.monster.stats))
    case 'age':
      return copy.sort((a, b) => b.monster.ageWeeks - a.monster.ageWeeks)
    case 'name':
      return copy.sort((a, b) => a.monster.name.localeCompare(b.monster.name))
  }
}

/** What the Library screen shows right now. */
export const visible = computed<Listed[]>(() => {
  const base = labTab.value === 'library' ? library.value.entries.map(fromEntry) : listPresets()
  const filter = labBreedFilter.value
  const filtered = filter === 'all' ? base : base.filter((l) => l.monster.mainBreed === filter || l.monster.subBreed === filter)
  return labTab.value === 'presets' && labSort.value === 'date' ? filtered : sortBy(filtered, labSort.value)
})

export function findListed(sel: { source: LabSource; id: string } | null): Listed | null {
  if (!sel) return null
  if (sel.source === 'presets') return listPresets().find((l) => l.id === sel.id) ?? null
  const e = findEntry(sel.id)
  return e ? fromEntry(e) : null
}

export function selectedListed(): Listed | null {
  return findListed(selected.value)
}

/* ---------- the editor draft ---------- */

export interface EditorDraft {
  /** Where Save goes back to. A preset or a brand-new monster is saved as a new Library entry; `active` is the ranch's monster. */
  origin: 'library' | 'preset' | 'new' | 'active'
  original: Monster
  monster: Monster
  history: EditHistoryEntry[]
  createdAt: number
  keepAll: boolean
  allowAny: boolean
  preview: Expression | 'auto'
  openSection: string
}

export const draft = signal<EditorDraft | null>(null)

export function startEdit(listed: Listed): void {
  draft.value = {
    origin: listed.source === 'library' ? 'library' : 'preset',
    original: structuredClone(listed.monster),
    monster: structuredClone(listed.monster),
    history: listed.history,
    createdAt: listed.createdAt,
    keepAll: false,
    allowAny: false,
    preview: 'auto',
    openSection: 'stats',
  }
}

/** §19: editing the monster on the ranch. Save goes straight back to the game (gameStore.replaceMonster). */
export function startEditActive(monster: Monster, history: EditHistoryEntry[]): void {
  draft.value = {
    origin: 'active',
    original: structuredClone(monster),
    monster: structuredClone(monster),
    history,
    createdAt: 0,
    keepAll: false,
    allowAny: false,
    preview: 'auto',
    openSection: 'stats',
  }
}

export function startNew(monster: Monster): void {
  draft.value = {
    origin: 'new',
    original: structuredClone(monster),
    monster: structuredClone(monster),
    history: [],
    createdAt: 0,
    keepAll: false,
    allowAny: false,
    preview: 'auto',
    openSection: 'identity',
  }
}

/** Changes the draft in place (on a fresh clone) so every signal subscriber re-renders. */
export function patchDraft(fn: (d: EditorDraft) => void): void {
  const d = draft.value
  if (!d) return
  const next: EditorDraft = { ...d, monster: structuredClone(d.monster) }
  fn(next)
  draft.value = next
}

export function patchMonster(fn: (m: Monster) => void): void {
  patchDraft((d) => fn(d.monster))
}

export function draftBreedChanged(d: EditorDraft): boolean {
  return d.monster.mainBreed !== d.original.mainBreed || d.monster.subBreed !== d.original.subBreed
}

/** Techniques that Save will drop: only after a breed change, and only without Keep all. */
export function draftRemovals(d: EditorDraft): string[] {
  return draftBreedChanged(d) && !d.keepAll ? techniquesOutsideKit(d.monster) : []
}

export function draftDirty(d: EditorDraft): boolean {
  return JSON.stringify(d.monster) !== JSON.stringify(d.original)
}

/** Saves the draft to the Library (§19 Save / Save as copy). Returns the saved monster. */
export async function saveDraft(asCopy: boolean): Promise<Monster | null> {
  const d = draft.value
  if (!d) return null
  const when = now()
  const removals = draftRemovals(d)
  const cleaned = structuredClone(d.monster)
  cleaned.techniques = cleaned.techniques.filter((t) => !removals.includes(t.id))
  if (d.origin === 'active' && !asCopy) {
    replaceMonster(cleaned)
    draft.value = null
    return cleaned
  }
  let finished = finishEdit(d.original, cleaned)
  let entry: LibraryEntry
  if (asCopy || d.origin !== 'library') {
    finished = { ...finished, id: newId(), parents: [] }
    entry = { monster: finished, history: [], createdAt: when, updatedAt: when }
  } else {
    const existing = findEntry(d.original.id)
    const history = pushHistory(existing?.history ?? d.history, existing?.monster ?? d.original, when)
    entry = { monster: finished, history, createdAt: existing?.createdAt ?? when, updatedAt: when }
  }
  await upsertEntry(entry)
  selected.value = { source: 'library', id: entry.monster.id }
  labTab.value = 'library'
  draft.value = null
  return entry.monster
}

export function discardDraft(): void {
  draft.value = null
}

export const ALL_BREEDS: readonly BreedId[] = BREED_IDS
