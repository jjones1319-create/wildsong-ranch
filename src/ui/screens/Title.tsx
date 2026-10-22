import { UI_TEXT } from '../../data/text/ui.ts'
import { navigate } from '../router.ts'

const LOGO_URL = `${import.meta.env.BASE_URL}logo.svg`

export function TitleScreen() {
  const t = UI_TEXT
  return (
    <main class="screen title">
      <header class="title__hero">
        <img class="title__logo" src={LOGO_URL} alt="" width="128" height="128" />
        <h1 class="title__name">{t.title}</h1>
        <p class="title__tagline">{t.tagline}</p>
      </header>
      <nav class="menu" aria-label="Main menu">
        <button type="button" class="btn btn--primary" onClick={() => navigate('newGame')}>
          {t.menu.newGame}
        </button>
        <button type="button" class="btn" onClick={() => navigate('continue')}>
          {t.menu.continue}
        </button>
        <button type="button" class="btn" onClick={() => navigate('lab')}>
          {t.menu.lab}
        </button>
        <button type="button" class="btn" onClick={() => navigate('settings')}>
          {t.menu.settings}
        </button>
      </nav>
      <footer class="title__footer">
        <button type="button" class="link" onClick={() => navigate('credits')}>
          {t.menu.credits}
        </button>
        <span class="version">
          {t.versionPrefix}
          {__APP_VERSION__}
        </span>
      </footer>
    </main>
  )
}
