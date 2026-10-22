import { render } from 'preact'
import './ui/styles/base.css'
import './ui/styles/components.css'
import './art/monster/monster.css'
import { App } from './ui/app.tsx'
import { installRouter } from './ui/router.ts'
import { bootApp } from './ui/store/appStore.ts'
import { detectPerformance } from './ui/store/perf.ts'

installRouter(window)
void bootApp()
detectPerformance()
render(<App />, document.getElementById('app')!)
