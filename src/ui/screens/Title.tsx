import { dateOf } from '../../core/calendar.ts'
import { fill } from '../../data/text/format.ts'
import { MONTH_NAMES } from '../../data/text/labels.ts'
import { UI_TEXT } from '../../data/text/ui.ts'
import { InstallCard } from '../components/InstallHelp.tsx'
import { navigate } from '../router.ts'
import { ready } from '../store/appStore.ts'
import { arrival, game } from '../store/gameStore.ts'

const LOGO_URL = `${import.meta.env.BASE_URL}logo.svg`

export function TitleScreen() {
  const t = UI_TEXT
  const g = game.value
  const booted = ready.value
  const d = g ? dateOf(g.week) : null
  return (
    <main class="screen title">
      <header class="title__hero">
        <img class="title__logo" src={LOGO_URL} alt="" width="128" height="128" />
        <h1 class="title__name">{t.title}</h1>
        <p class="title__tagline">{t.tagline}</p>
      </header>
      <nav class="menu" aria-label="Main menu">
        <button type="button" class={`btn ${g ? 'btn--primary' : ''}`} disabled={!booted || !g} onClick={() => navigate(g?.ended && !arrival.value ? 'farewell' : 'ranch')}>
          {t.menu.continue}
          {g && d && (
            <>
              <br />
              <span class="small" style={{ fontWeight: 400 }}>
                {fill(t.menu.continueInfo, { breeder: g.breeder.name, ranch: g.breeder.ranchName, year: d.year, month: MONTH_NAMES[d.month - 1] })}
              </span>
            </>
          )}
        </button>
        {booted && !g && <p class="muted small center">{t.menu.continueNone}</p>}
        <button type="button" class={`btn ${g ? '' : 'btn--primary'}`} onClick={() => navigate('newGame')}>
          {t.menu.newGame}
        </button>
        <button type="button" class="btn" onClick={() => navigate('lab')}>
          {t.menu.lab}
        </button>
        <button type="button" class="btn" onClick={() => navigate('settings')}>
          {t.menu.settings}
        </button>
      </nav>
      {booted && <InstallCard />}
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
