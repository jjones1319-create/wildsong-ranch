import { UI_TEXT } from '../data/text/ui.ts'
import { AppToast } from './components/Toast.tsx'
import { UpdateToast } from './components/UpdateToast.tsx'
import { screen, type Screen } from './router.ts'
import { lazyScreen } from './lib/lazy.tsx'
import { LabEditorScreen } from './screens/lab/LabEditor.tsx'
import { CreditsScreen } from './screens/Credits.tsx'
import { JourneyLedgerScreen } from './screens/ranch/JourneyLedger.tsx'
import { GuildScreen } from './screens/town/Guild.tsx'
import { MailboxScreen } from './screens/town/Mailbox.tsx'
import { NewGameScreen } from './screens/NewGame.tsx'
import { BagScreen } from './screens/ranch/Bag.tsx'
import { MonsterCardScreen } from './screens/ranch/MonsterCardScreen.tsx'
import { RanchScreen } from './screens/ranch/Ranch.tsx'
import { SongbookScreen } from './screens/ranch/Songbook.tsx'
import { SettingsScreen } from './screens/Settings.tsx'
import { TitleScreen } from './screens/Title.tsx'
import { GuildLibraryScreen } from './screens/town/GuildLibrary.tsx'
import { ShopScreen } from './screens/town/Shop.tsx'
import { TownScreen } from './screens/town/Town.tsx'
import { PellLabScreen } from './screens/town/PellLab.tsx'
import { ShrineScreen } from './screens/town/Shrine.tsx'
import { MarketScreen } from './screens/town/Market.tsx'
import { UpgradesScreen } from './screens/town/Upgrades.tsx'
import { ready } from './store/appStore.ts'
import { flow } from './store/gameStore.ts'

/* §22 performance: the heavy screens load on first use (see lib/lazy.tsx). */
const FarewellScreen = lazyScreen(() => import('./screens/Farewell.tsx'), 'FarewellScreen')
const CreditsRollScreen = lazyScreen(() => import('./screens/CreditsRoll.tsx'), 'CreditsRollScreen')
const BattleScreen = lazyScreen(() => import('./screens/battle/BattleScreen.tsx'), 'BattleScreen')
const TournamentEntryScreen = lazyScreen(() => import('./screens/tournament/TournamentEntry.tsx'), 'TournamentEntryScreen')
const TournamentPlayScreen = lazyScreen(() => import('./screens/tournament/TournamentPlay.tsx'), 'TournamentPlayScreen')
const TournamentResultsScreen = lazyScreen(() => import('./screens/tournament/TournamentResults.tsx'), 'TournamentResultsScreen')
const LabCreateScreen = lazyScreen(() => import('./screens/lab/LabCreate.tsx'), 'LabCreateScreen')
const LabBattleLabScreen = lazyScreen(() => import('./screens/lab/LabBattleLab.tsx'), 'LabBattleLabScreen')
const LabEffectsScreen = lazyScreen(() => import('./screens/lab/LabEffects.tsx'), 'LabEffectsScreen')
const LabSoundScreen = lazyScreen(() => import('./screens/lab/LabSound.tsx'), 'LabSoundScreen')
const LabModelsScreen = lazyScreen(() => import('./screens/lab/LabModels.tsx'), 'LabModelsScreen')
const LabExportScreen = lazyScreen(() => import('./screens/lab/LabExport.tsx'), 'LabExportScreen')
const LabVersusScreen = lazyScreen(() => import('./screens/lab/LabVersus.tsx'), 'LabVersusScreen')
const LabImportScreen = lazyScreen(() => import('./screens/lab/LabImport.tsx'), 'LabImportScreen')
const LabLibraryScreen = lazyScreen(() => import('./screens/lab/LabLibrary.tsx'), 'LabLibraryScreen')
const LabViewScreen = lazyScreen(() => import('./screens/lab/LabView.tsx'), 'LabViewScreen')
const ExpeditionScreen = lazyScreen(() => import('./screens/ranch/Expedition.tsx'), 'ExpeditionScreen')
const JournalScreen = lazyScreen(() => import('./screens/town/Journal.tsx'), 'JournalScreen')
const OddJobsScreen = lazyScreen(() => import('./screens/town/OddJobs.tsx'), 'OddJobsScreen')
const CalendarScreen = lazyScreen(() => import('./screens/ranch/Calendar.tsx'), 'CalendarScreen')

function Loading() {
  return (
    <main class="screen">
      <p class="loading">{UI_TEXT.loading}</p>
    </main>
  )
}

function Current({ current }: { current: Screen }) {
  switch (current) {
    case 'title':
      return <TitleScreen />
    case 'credits':
      return <CreditsScreen />
    case 'newGame':
      return <NewGameScreen />
    case 'ranch':
      return <RanchScreen />
    case 'ranchCard':
      return <MonsterCardScreen />
    case 'bag':
      return <BagScreen />
    case 'songbook':
      return <SongbookScreen />
    case 'town':
      return <TownScreen />
    case 'shop':
      return <ShopScreen />
    case 'library':
      return <GuildLibraryScreen />
    case 'pell':
      return <PellLabScreen />
    case 'shrine':
      return <ShrineScreen />
    case 'market':
      return <MarketScreen />
    case 'farewell':
      return <FarewellScreen />
    case 'settings':
      return <SettingsScreen />
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
    case 'labVersus':
      return <LabVersusScreen />
    case 'labBattleLab':
      return <LabBattleLabScreen />
    case 'labSound':
      return <LabSoundScreen />
    case 'labEffects':
      return <LabEffectsScreen />
    case 'labModels':
      return <LabModelsScreen />
    case 'battle':
      return <BattleScreen />
    case 'tournament':
      return <TournamentEntryScreen />
    case 'tournamentPlay':
      return <TournamentPlayScreen />
    case 'tournamentResults':
      return <TournamentResultsScreen />
    case 'guild':
      return <GuildScreen />
    case 'mail':
      return <MailboxScreen />
    case 'journey':
      return <JourneyLedgerScreen />
    case 'creditsRoll':
      return <CreditsRollScreen />
    case 'lab':
      return <LabLibraryScreen />
    case 'expedition':
      return <ExpeditionScreen />
    case 'journal':
      return <JournalScreen />
    case 'oddJobs':
      return <OddJobsScreen />
    case 'upgrades':
      return <UpgradesScreen />
    case 'calendar':
      return <CalendarScreen />
  }
}

/** Picks the screen from app state (the router signal). Never path routing: GitHub Pages can't rewrite URLs. */
export function App() {
  const current = screen.value
  const booted = ready.value
  const needsStore = current !== 'title' && current !== 'credits'
  // §20 updates: never mid-week-flow; only on the title and the quiet ranch.
  const quiet = current === 'title' || (current === 'ranch' && flow.value.kind === 'idle')
  return (
    <>
      {needsStore && !booted ? <Loading /> : <Current current={current} />}
      <AppToast />
      <UpdateToast visible={quiet} />
    </>
  )
}
