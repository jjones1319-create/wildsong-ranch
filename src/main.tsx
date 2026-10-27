import { render } from 'preact'
import './ui/styles/base.css'
import './ui/styles/components.css'
import './ui/styles/ranch.css'
import './ui/styles/battle.css'
import './ui/styles/tournament.css'
import './ui/styles/legacy.css'
import './ui/styles/expedition.css'
import './ui/styles/polish.css'
import './ui/styles/sound.css'
import './art/monster/monster.css'
import { installAudio } from './audio/player.ts'
import { App } from './ui/app.tsx'
import { installDirector } from './ui/lib/audioDirector.ts'
import { installPromptCapture } from './ui/lib/platform.ts'
import { installTapSounds } from './ui/lib/tapSounds.ts'
import { installRouter } from './ui/router.ts'
import { bootApp } from './ui/store/appStore.ts'
import { installAutosaveOnHide } from './ui/store/gameStore.ts'
import { detectPerformance } from './ui/store/perf.ts'
import { installUpdates } from './ui/store/updateStore.ts'

installPromptCapture(window)
installRouter(window)
installAutosaveOnHide(document)
installAudio(document)
installTapSounds(document)
installDirector()
installUpdates(document)
void bootApp()
detectPerformance()
render(<App />, document.getElementById('app')!)
