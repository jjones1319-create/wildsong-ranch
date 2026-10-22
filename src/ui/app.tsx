import { UpdateToast } from './components/UpdateToast.tsx'
import { screen } from './router.ts'
import { CreditsScreen } from './screens/Credits.tsx'
import { PlaceholderScreen } from './screens/Placeholder.tsx'
import { TitleScreen } from './screens/Title.tsx'

/** Picks the screen from app state (the router signal). Never path routing: GitHub Pages can't rewrite URLs. */
export function App() {
  const current = screen.value
  return (
    <>
      {current === 'title' && <TitleScreen />}
      {current === 'credits' && <CreditsScreen />}
      {(current === 'newGame' || current === 'continue' || current === 'lab' || current === 'settings') && (
        <PlaceholderScreen screen={current} />
      )}
      {/* Always mounted so the service worker registers once; only shown on the title screen (later: the ranch). */}
      <UpdateToast visible={current === 'title'} />
    </>
  )
}
