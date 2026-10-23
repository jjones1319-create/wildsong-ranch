import { UI_TEXT } from '../data/text/ui.ts'
import { AppToast } from './components/Toast.tsx'
import { UpdateToast } from './components/UpdateToast.tsx'
import { screen, type Screen } from './router.ts'
import { CreditsScreen } from './screens/Credits.tsx'
import { FarewellScreen } from './screens/Farewell.tsx'
import { LabCreateScreen } from './screens/lab/LabCreate.tsx'
import { LabEditorScreen } from './screens/lab/LabEditor.tsx'
import { BattleScreen } from './screens/battle/BattleScreen.tsx'
import { CreditsRollScreen } from './screens/CreditsRoll.tsx'
import { JourneyLedgerScreen } from './screens/ranch/JourneyLedger.tsx'
import { TournamentEntryScreen } from './screens/tournament/TournamentEntry.tsx'
import { TournamentPlayScreen } from './screens/tournament/TournamentPlay.tsx'
import { TournamentResultsScreen } from './screens/tournament/TournamentResults.tsx'
import { GuildScreen } from './screens/town/Guild.tsx'
import { MailboxScreen } from './screens/town/Mailbox.tsx'
import { LabBattleLabScreen } from './screens/lab/LabBattleLab.tsx'
import { LabExportScreen } from './screens/lab/LabExport.tsx'
import { LabVersusScreen } from './screens/lab/LabVersus.tsx'
import { LabImportScreen } from './screens/lab/LabImport.tsx'
import { LabLibraryScreen } from './screens/lab/LabLibrary.tsx'
import { LabViewScreen } from './screens/lab/LabView.tsx'
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
import { ExpeditionScreen } from './screens/ranch/Expedition.tsx'
import { JournalScreen } from './screens/town/Journal.tsx'
import { OddJobsScreen } from './screens/town/OddJobs.tsx'
import { UpgradesScreen } from './screens/town/Upgrades.tsx'
import { ready } from './store/appStore.ts'
import { flow } from './store/gameStore.ts'

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
