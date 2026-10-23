import { render } from 'preact'
import './ui/styles/base.css'
import './ui/styles/components.css'
import './ui/styles/ranch.css'
import './ui/styles/battle.css'
import './ui/styles/tournament.css'
import './art/monster/monster.css'
import { App } from './ui/app.tsx'
import { installRouter } from './ui/router.ts'
import { bootApp } from './ui/store/appStore.ts'
import { installAutosaveOnHide } from './ui/store/gameStore.ts'
import { detectPerformance } from './ui/store/perf.ts'

installRouter(window)
installAutosaveOnHide(document)
void bootApp()
detectPerformance()
render(<App />, document.getElementById('app')!)
