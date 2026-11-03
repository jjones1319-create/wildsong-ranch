import { useMemo, useState } from 'preact/hooks'
import { makeStar as starCheck } from '../../../core/herd.ts'
import { stageOf } from '../../../core/monster.ts'
import type { MateOrder } from '../../../core/state.ts'
import { variantNameOf } from '../../../core/variants.ts'
import { wrenVars } from '../../../core/report.ts'
import { DRILLS } from '../../../data/drills.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { STAGE_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { Confirm, Segmented, Sheet } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { ConditionBars } from '../../components/RanchBits.tsx'
import { navigate, navigateFrom } from '../../router.ts'
import { settings, showToast } from '../../store/appStore.ts'
import { game } from '../../store/gameStore.ts'
import { cardId, makeStar, penToFreezer, setOrder } from '../../store/herdStore.ts'
import { startEditMate } from '../../store/labStore.ts'
import { FreeSheet } from './FreeSheet.tsx'
import { StarFriendship } from './FriendsBits.tsx'
import { defaultDrill, lastLine, mateStatus } from './herdBits.ts'

const t = HERD_TEXT.sheet

/** v16 a ranch-mate's sheet (tap its tile on the herd strip): how it is, last week, its standing order, and what to do with it. */
export function HerdSheet({ id, onClose }: { id: string | null; onClose: () => void }) {
  const g = game.value
  const [ask, setAsk] = useState<'star' | 'free' | null>(null)
  const mate = g && id ? (g.ranchmates.find((r) => r.monster.id === id) ?? null) : null
  // The same pure rule the move uses, so the button is disabled with the real reason.
  const refused = useMemo(() => (g && mate ? starCheck(g, mate.monster.id).refused : null), [g, mate?.monster.id])
  if (!g || !mate) return null
  const m = mate.monster
  const order = mate.order
  const status = mateStatus(m)
  const yard = g.upgrades.trainingYard

  const close = () => {
    setAsk(null)
    onClose()
  }
  const changeOrder = (next: MateOrder) => {
    if (setOrder(m.id, next)) return
    const verb = next.kind === 'drill' ? fill(t.orderVerb.drill, { drill: DRILLS.find((d) => d.id === next.drill)?.name ?? '' }) : t.orderVerb[next.kind]
    showToast(fill(t.orderSet, { name: m.name, order: verb }))
  }
  const pickKind = (kind: MateOrder['kind']) => {
    if (kind === order.kind) return
    changeOrder(kind === 'drill' ? { kind: 'drill', drill: defaultDrill(g, m) } : { kind })
  }
  const doStar = () => {
    const old = g.monster?.name ?? ''
    const why = makeStar(m.id)
    close()
    if (why) showToast(HERD_TEXT.star.refused[why])
    else showToast(fill(old ? HERD_TEXT.star.done : HERD_TEXT.star.first, wrenVars(m, { old })))
  }
  const toFreezer = () => {
    const why = penToFreezer(m.id)
    close()
    showToast(why === 'full' ? HERD_TEXT.move.freezerFull : why ? HERD_TEXT.star.refused.notFound : fill(HERD_TEXT.move.toFreezer, { name: m.name }))
  }

  return (
    <>
      <Sheet open={ask === null} title={m.name} onClose={close}>
        <div class="herdsheet__head">
          <MonsterPortrait monster={m} size={84} animate={false} />
          <div class="herdsheet__info">
            <span class="muted small">{variantNameOf(m)}</span>
            <span class="small">{fill(t.age, { n: m.ageWeeks, stage: STAGE_NAMES[stageOf(m) - 1] })}</span>
            {status && <span class={`herd__badge herd__badge--${status.tone}`}>{status.text}</span>}
          </div>
        </div>
        <ConditionBars m={m} mode={settings.value.transparency} />
        <p class="herdsheet__last">
          <span class="field__label">{t.lastWeek}</span> {lastLine(mate.last)}
        </p>
        <StarFriendship g={g} id={m.id} />
        <p class="field__label">{t.order}</p>
        <Segmented
          label={t.order}
          value={order.kind}
          onChange={pickKind}
          options={(['drill', 'rest', 'play'] as const).map((k) => ({ value: k, label: `${HERD_TEXT.orders[k].icon} ${HERD_TEXT.orders[k].label}` }))}
        />
        {order.kind === 'drill' && (
          <label class="field herdsheet__drill">
            <span class="field__label">{t.drill}</span>
            <select class="select" value={order.drill} onChange={(e) => changeOrder({ kind: 'drill', drill: (e.currentTarget as HTMLSelectElement).value as typeof order.drill })}>
              {(['light', 'heavy'] as const).map((kind) => (
                <optgroup key={kind} label={UI_TEXT.train.tabs[kind]}>
                  {DRILLS.filter((d) => d.kind === kind).map((d) => {
                    const locked = d.needsTrainingYard && !yard
                    return (
                      <option key={d.id} value={d.id} disabled={locked && d.id !== order.drill}>
                        {locked ? fill(t.needsYard, { drill: d.name }) : d.name}
                      </option>
                    )
                  })}
                </optgroup>
              ))}
            </select>
          </label>
        )}
        <div class="herdsheet__actions">
          <button
            type="button"
            class="btn"
            onClick={() => {
              cardId.value = m.id
              close()
              navigate('ranchCard')
            }}
          >
            {t.card}
          </button>
          <button
            type="button"
            class="btn"
            onClick={() => {
              startEditMate(m, mate.history)
              close()
              navigateFrom('ranch', 'labEdit')
            }}
          >
            {t.edit}
          </button>
          <button type="button" class="btn btn--primary herdsheet__wide" disabled={refused !== null} onClick={() => setAsk('star')}>
            {t.makeStar}
          </button>
          {refused && <p class="muted small herdsheet__wide">{HERD_TEXT.star.refused[refused]}</p>}
          <button type="button" class="btn" onClick={toFreezer}>
            {t.toFreezer}
          </button>
          <button type="button" class="btn btn--ghost" onClick={() => setAsk('free')}>
            {t.free}
          </button>
        </div>
      </Sheet>
      <Confirm
        open={ask === 'star'}
        text={g.monster ? fill(HERD_TEXT.star.ask, { name: m.name, old: g.monster.name }) : fill(HERD_TEXT.star.askEmpty, { name: m.name })}
        confirmLabel={t.makeStar}
        onConfirm={doStar}
        onCancel={() => setAsk(null)}
      />
      <FreeSheet monster={ask === 'free' ? m : null} onDone={close} onCancel={() => setAsk(null)} />
    </>
  )
}
