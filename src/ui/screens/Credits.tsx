import { UI_TEXT } from '../../data/text/ui.ts'
import { goBack } from '../router.ts'

export function CreditsScreen() {
  const c = UI_TEXT.credits
  return (
    <main class="screen">
      <h1 class="heading">{c.heading}</h1>
      <section class="card">
        <p>{c.madeBy}</p>
        <p>{c.original}</p>
        <p>{c.tools}</p>
        <p>{c.license}</p>
      </section>
      <section class="card card--muted">
        <p>{c.disclaimer}</p>
      </section>
      <p class="version version--center">
        {UI_TEXT.versionPrefix}
        {__APP_VERSION__}
      </p>
      <div class="spacer" />
      <button type="button" class="btn" onClick={goBack}>
        {UI_TEXT.back}
      </button>
    </main>
  )
}
