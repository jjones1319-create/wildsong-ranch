import { UI_TEXT } from '../../data/text/ui.ts'
import { goBack } from '../router.ts'

type PlaceholderKey = keyof typeof UI_TEXT.placeholder

/** Stands in for a screen that a later milestone builds. Wren explains what is coming. */
export function PlaceholderScreen({ screen }: { screen: PlaceholderKey }) {
  const text = UI_TEXT.placeholder[screen]
  return (
    <main class="screen">
      <h1 class="heading">{text.heading}</h1>
      <section class="card">
        <p class="speaker">{UI_TEXT.wren}</p>
        <p>{text.wren}</p>
      </section>
      <div class="spacer" />
      <button type="button" class="btn" onClick={goBack}>
        {UI_TEXT.back}
      </button>
    </main>
  )
}
