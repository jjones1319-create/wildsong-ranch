import { render } from 'preact'
import './ui/styles/base.css'
import { App } from './ui/app.tsx'
import { installRouter } from './ui/router.ts'

installRouter(window)
render(<App />, document.getElementById('app')!)
