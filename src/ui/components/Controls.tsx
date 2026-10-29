import type { ComponentChildren } from 'preact'
import { UI_TEXT } from '../../data/text/ui.ts'
import { goBack } from '../router.ts'

/** Small shared controls for the Lab and Settings: all tap targets are at least 44 px (CLAUDE.md phone-first). */

export function TopBar({ title, onBack, right }: { title: string; onBack?: () => void; right?: ComponentChildren }) {
  return (
    <header class="topbar">
      <button type="button" class="iconbtn" aria-label={UI_TEXT.back} onClick={onBack ?? goBack}>
        ‹
      </button>
      <h1 class="topbar__title">{title}</h1>
      <div class="topbar__right">{right}</div>
    </header>
  )
}

export interface Option<T extends string> {
  value: T
  label: string
}

export function Segmented<T extends string>({ options, value, onChange, label }: { options: Option<T>[]; value: T; onChange: (v: T) => void; label?: string }) {
  return (
    <div class="seg" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" role="tab" aria-selected={o.value === value} class={`seg__btn ${o.value === value ? 'seg__btn--on' : ''}`} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Chips<T extends string>({ options, value, onChange, label }: { options: Option<T>[]; value: T; onChange: (v: T) => void; label?: string }) {
  return (
    <div class="chips" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} class={`chip ${o.value === value ? 'chip--on' : ''}`} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ComponentChildren }) {
  return (
    <label class="field">
      <span class="field__label">{label}</span>
      {children}
      {hint && <span class="field__hint">{hint}</span>}
    </label>
  )
}

export function Select<T extends string>({ label, value, options, onChange, hint }: { label: string; value: T; options: Option<T>[]; onChange: (v: T) => void; hint?: string }) {
  return (
    <Field label={label} hint={hint}>
      <select class="select" value={value} onChange={(e) => onChange((e.currentTarget as HTMLSelectElement).value as T)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Field>
  )
}

export function Toggle({ label, checked, onChange, hint }: { label: string; checked: boolean; onChange: (v: boolean) => void; hint?: string }) {
  return (
    <label class="toggle">
      <span class="toggle__text">
        <span>{label}</span>
        {hint && <span class="field__hint">{hint}</span>}
      </span>
      <input type="checkbox" role="switch" checked={checked} onChange={(e) => onChange((e.currentTarget as HTMLInputElement).checked)} />
      <span class="toggle__track" aria-hidden="true" />
    </label>
  )
}

function clampInt(v: number, min: number, max: number): number {
  if (!Number.isFinite(v)) return min
  return Math.min(max, Math.max(min, Math.round(v)))
}

/** ±big / ±1 buttons around a number field. */
export function Stepper({ value, min, max, onChange, big = 10, label }: { value: number; min: number; max: number; onChange: (v: number) => void; big?: number; label?: string }) {
  const set = (v: number) => onChange(clampInt(v, min, max))
  return (
    <div class="stepper" role="group" aria-label={label}>
      <button type="button" class="stepper__btn" onClick={() => set(value - big)} aria-label={`−${big}`}>
        −{big}
      </button>
      <button type="button" class="stepper__btn" onClick={() => set(value - 1)} aria-label="−1">
        −
      </button>
      <input
        class="stepper__num"
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        value={value}
        onInput={(e) => {
          const n = Number((e.currentTarget as HTMLInputElement).value)
          if (Number.isFinite(n)) set(n)
        }}
        onBlur={(e) => {
          ;(e.currentTarget as HTMLInputElement).value = String(value)
        }}
      />
      <button type="button" class="stepper__btn" onClick={() => set(value + 1)} aria-label="+1">
        +
      </button>
      <button type="button" class="stepper__btn" onClick={() => set(value + big)} aria-label={`+${big}`}>
        +{big}
      </button>
    </div>
  )
}

/**
 * A labelled slider with a stepper under it (the six stats, the condition values). `sliderMax` lets the slider
 * cover the useful range while the stepper's number box still reaches `max` (stats: slider to 1,500, box to 9,999).
 */
export function SliderRow({ label, value, min, max, sliderMax, onChange, big = 10, extra }: { label: string; value: number; min: number; max: number; sliderMax?: number; onChange: (v: number) => void; big?: number; extra?: ComponentChildren }) {
  const top = Math.min(max, sliderMax ?? max)
  return (
    <div class="slider-row">
      <div class="slider-row__head">
        <span class="slider-row__label">{label}</span>
        {extra}
      </div>
      <input class="range" type="range" min={min} max={top} value={Math.min(value, top)} aria-label={label} onInput={(e) => onChange(clampInt(Number((e.currentTarget as HTMLInputElement).value), min, top))} />
      <Stepper value={value} min={min} max={max} onChange={onChange} big={big} label={label} />
    </div>
  )
}

/** A collapsible editor section. */
export function Section({ id, title, open, onToggle, children, summary }: { id: string; title: string; open: boolean; onToggle: (id: string) => void; children: ComponentChildren; summary?: string }) {
  return (
    <section class={`section ${open ? 'section--open' : ''}`}>
      <button type="button" class="section__head" aria-expanded={open} onClick={() => onToggle(id)}>
        <span class="section__title">{title}</span>
        {summary && <span class="section__summary">{summary}</span>}
        <span class="section__chev" aria-hidden="true">
          {open ? '▾' : '▸'}
        </span>
      </button>
      {open && <div class="section__body">{children}</div>}
    </section>
  )
}

/** A bottom sheet. Tapping the backdrop closes it. */
export function Sheet({ open, title, onClose, children }: { open: boolean; title?: string; onClose: () => void; children: ComponentChildren }) {
  if (!open) return null
  return (
    <div class="sheet-backdrop" onClick={onClose}>
      <div class="sheet" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        {title && <h2 class="sheet__title">{title}</h2>}
        {children}
      </div>
    </div>
  )
}

export function Confirm({ open, text, confirmLabel, cancelLabel, danger, onConfirm, onCancel }: { open: boolean; text: string; confirmLabel: string; cancelLabel?: string; danger?: boolean; onConfirm: () => void; onCancel: () => void }) {
  return (
    <Sheet open={open} onClose={onCancel}>
      <p class="sheet__text">{text}</p>
      <div class="sheet__actions">
        <button type="button" class={`btn ${danger ? 'btn--danger' : 'btn--primary'}`} onClick={onConfirm}>
          {confirmLabel}
        </button>
        <button type="button" class="btn" onClick={onCancel}>
          {cancelLabel ?? UI_TEXT.lab.actions.cancel}
        </button>
      </div>
    </Sheet>
  )
}

export function Badge({ children, tone }: { children: ComponentChildren; tone?: 'pure' | 'edited' | 'preset' | 'muted' }) {
  return <span class={`badge badge--${tone ?? 'muted'}`}>{children}</span>
}
