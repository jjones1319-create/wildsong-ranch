import { UI_TEXT } from '../../data/text/ui.ts'
import { navigate } from '../router.ts'

/** §13: rank 10 rolls the credits ("The Wildsong Rises"), then play continues. */
export function CreditsRollScreen() {
  const t = UI_TEXT.creditsRoll
  const c = UI_TEXT.credits
  return (
    <main class="screen">
      <div class="spacer" />
      <h1 class="heading center">{t.title}</h1>
      <section class="card">
        <p>{t.line1}</p>
        <p>{t.line2}</p>
        <p>{t.line3}</p>
      </section>
      <section class="card card--muted">
        <p>{c.madeBy}</p>
        <p>{c.original}</p>
        <p>{c.disclaimer}</p>
      </section>
      <p class="center">{t.thanks}</p>
      <div class="spacer" />
      <button type="button" class="btn btn--primary" onClick={() => navigate('ranch')}>
        {t.done}
      </button>
    </main>
  )
}
