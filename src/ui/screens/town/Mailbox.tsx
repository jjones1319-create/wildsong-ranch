import { readMail } from '../../../core/game.ts'
import { dateOf } from '../../../core/calendar.ts'
import { fill } from '../../../data/text/format.ts'
import { MONTH_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TopBar } from '../../components/Controls.tsx'
import { commit, game } from '../../store/gameStore.ts'

/** Town → Mailbox: sale notices, invitations and Guild news. Tapping a letter marks it read. */
export function MailboxScreen() {
  const g = game.value
  const t = UI_TEXT.mail
  if (!g) return null
  const body = (kind: keyof typeof t.bodies, ref: string) => {
    const month = Number(ref)
    return fill(t.bodies[kind], { month: Number.isFinite(month) && month >= 1 && month <= 12 ? MONTH_NAMES[month - 1]! : ref, g: ref, n: ref })
  }
  return (
    <main class="screen">
      <TopBar title={t.title} />
      {g.mail.length === 0 && <p class="empty">{t.empty}</p>}
      <div class="list">
        {g.mail.map((m) => (
          <button key={m.id} type="button" class={`townrow ${m.read ? 'townrow--off' : ''}`} onClick={() => commit(readMail(g, m.id))}>
            <span class="townrow__icon" aria-hidden="true">
              {m.read ? '✉' : '📩'}
            </span>
            <span class="townrow__body">
              <span class="townrow__name">{t.kinds[m.kind]}</span>
              <span class="townrow__hint">
                {UI_TEXT.ranch.year.replace('{year}', String(dateOf(m.week).year))} · {MONTH_NAMES[dateOf(m.week).month - 1]} · {body(m.kind, m.ref)}
              </span>
            </span>
          </button>
        ))}
      </div>
    </main>
  )
}
