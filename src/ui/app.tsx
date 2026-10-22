import { UI_TEXT } from '../data/text/ui.ts'
import { AppToast } from './components/Toast.tsx'
import { UpdateToast } from './components/UpdateToast.tsx'
import { screen, type Screen } from './router.ts'
import { CreditsScreen } from './screens/Credits.tsx'
import { LabCreateScreen } from './screens/lab/LabCreate.tsx'
import { LabEditorScreen } from './screens/lab/LabEditor.tsx'
import { LabExportScreen } from './screens/lab/LabExport.tsx'
import { LabImportScreen } from './screens/lab/LabImport.tsx'
import { LabLibraryScreen } from './screens/lab/LabLibrary.tsx'
import { LabViewScreen } from './screens/lab/LabView.tsx'
import { PlaceholderScreen } from './screens/Placeholder.tsx'
import { SettingsScreen } from './screens/Settings.tsx'
import { TitleScreen } from './screens/Title.tsx'
import { ready } from './store/appStore.ts'

function Loading() {
  return (
    <main class="screen">
      <p class="loading">{UI_TEXT.loading}</p>
    </main>
  )
}

function LabScreen({ current }: { current: Screen }) {
  switch (current) {
    case 'labCreate':
      return <LabCreateScreen />
    case 'labView':
      return <LabViewScreen />
    case 'labEdit':
      return <LabEditorScreen />
    case 'labImport':
      return <LabImportScreen />
    case 'labExport':
      return <LabExportScreen />
    default:
      return <LabLibraryScreen />
  }
}

/** Picks the screen from app state (the router signal). Never path routing: GitHub Pages can't rewrite URLs. */
export function App() {
  const current = screen.value
  const booted = ready.value
  const needsStore = current.startsWith('lab') || current === 'settings'
  return (
    <>
      {current === 'title' && <TitleScreen />}
      {current === 'credits' && <CreditsScreen />}
      {(current === 'newGame' || current === 'continue') && <PlaceholderScreen screen={current} />}
      {needsStore && !booted && <Loading />}
      {needsStore && booted && (current === 'settings' ? <SettingsScreen /> : <LabScreen current={current} />)}
      <AppToast />
      {/* Always mounted so the service worker registers once; only shown on the title screen (later: the ranch). */}
      <UpdateToast visible={current === 'title'} />
    </>
  )
}
