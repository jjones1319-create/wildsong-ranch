import { PERF_TEXT as T } from '../../data/text/perf.ts'
import { lastMemoryCeiling, measure, memoryCeiling, reportText, runCheck, type CheckResult, type Timing } from './check.ts'
import { loadAssets, type TexFormat } from './content.ts'
import { buildScene, countCards, countTriangles, VIEWS, type SceneKind } from './stage.ts'
import { createView, type Backend, type Level } from './view.ts'

/**
 * The Performance check page (perf/index.html). Two modes:
 *   default       the check the owner runs on the phone (check.ts);
 *   ?mode=shot    a capture API for tools/art/spike-detail.ts on the PC: window.__perf.shot({...}) → PNG data URL.
 */

const app = document.getElementById('app')!
const mode = new URLSearchParams(location.search).get('mode')

function el<K extends keyof HTMLElementTagNameMap>(tag: K, props: Partial<HTMLElementTagNameMap[K]> = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag)
  Object.assign(e, props)
  for (const k of kids) e.append(k)
  return e
}

// ----------------------------------------------------------------------------- the check UI
function checkUi(): void {
  const status = el('p', { className: 'status' })
  const live = el('p', { className: 'live' })
  const stageBox = el('div', { className: 'stage' })
  const report = el('div', { className: 'report' })
  const buttons = el('div', { className: 'buttons' })
  let canvas: HTMLCanvasElement | null = null
  const ui = {
    status: (t: string) => { status.textContent = t },
    live: (t: string) => { live.textContent = t },
    canvas: () => {
      // a fresh canvas per stage: a WebGL canvas can't later become a WebGPU one
      canvas?.remove()
      canvas = el('canvas')
      stageBox.append(canvas)
      return canvas
    },
  }
  const last = lastMemoryCeiling()
  app.append(
    el('h1', {}, T.title),
    el('p', {}, T.intro),
    buttons,
    status,
    live,
    stageBox,
    report,
    el('p', { className: 'muted' }, last ? T.lastMemory(last) : ''),
  )
  const run = async (quick: boolean) => {
    buttons.hidden = true
    report.replaceChildren()
    let result: CheckResult | null = null
    try {
      result = await runCheck(quick, ui)
    } catch (e) {
      ui.status(String(e))
    }
    canvas?.remove()
    buttons.hidden = false
    if (!result) return
    const text = reportText(result)
    const verdict = el('p', { className: result.pass ? 'pass' : 'fail' }, result.pass === undefined ? '…' : result.pass ? T.pass : T.fail)
    const pre = el('pre', {}, text)
    const copy = el('button', { type: 'button' }, T.copy)
    copy.onclick = async () => {
      await navigator.clipboard.writeText(text).catch(() => undefined)
      copy.textContent = T.copied
    }
    const frames = el('div', { className: 'frames' })
    for (const [k, v] of Object.entries(result.ab)) if (v?.frame) frames.append(el('figure', {}, el('img', { src: v.frame, alt: k }), el('figcaption', {}, k)))
    report.append(verdict, copy, pre, frames)
    ui.status('')
    ui.live('')
  }
  const full = el('button', { type: 'button' }, T.full)
  full.onclick = () => void run(false)
  const quick = el('button', { type: 'button', className: 'secondary' }, T.quick)
  quick.onclick = () => void run(true)
  const mem = el('button', { type: 'button', className: 'secondary' }, T.memory)
  mem.onclick = async () => {
    if (!confirm(T.memoryWarn)) return
    buttons.hidden = true
    ui.status(T.stages.memory)
    const mb = await memoryCeiling(ui.canvas(), (x) => ui.live(`${x} MB`))
    ui.live(T.lastMemory(mb))
    buttons.hidden = false
  }
  buttons.append(full, quick, mem)
}

// ----------------------------------------------------------------------------- the PC capture API
interface ShotOpts { view?: string; part?: 'head' | 'paw'; cinematic?: boolean; backend?: Backend; size?: number; level?: Level; format?: TexFormat; kind?: SceneKind; dpr?: number }

function shotApi(): void {
  const host = el('div')
  app.append(host)
  const api = {
    ready: true,
    async shot(o: ShotOpts): Promise<{ png: string; triangles: number; cards: number; gpuMs: number | null }> {
      const size = o.size ?? 900
      host.replaceChildren()
      const canvas = el('canvas')
      canvas.style.width = canvas.style.height = `${size}px`
      host.append(canvas)
      const view = await createView(o.backend ?? 'webgl', { canvas, width: size, height: size, dpr: o.dpr ?? 1, cinematic: o.cinematic === true, focus: 2.4 })
      if (!view) throw new Error('no such renderer here')
      const assets = await loadAssets(view.renderer as never, o.format ?? 'ktx2')
      const ps = buildScene(o.kind ?? 'shot', assets, view, 1, { shot: VIEWS[o.view ?? 'head_34'], part: o.part ?? 'head', cinematic: o.cinematic })
      await view.init(ps.scene, ps.camera)
      view.setCinematic(o.cinematic === true && o.kind !== undefined && o.kind !== 'shot', ps.focus)
      if (o.level) view.setLevel(o.level)
      for (let i = 0; i < 6; i++) {
        ps.update(0.4)
        view.render()
        await new Promise((r) => requestAnimationFrame(r))
      }
      const png = view.readPixels()
      const out = { png, triangles: countTriangles(ps.scene), cards: countCards(ps.scene), gpuMs: view.gpuMs() }
      view.dispose()
      return out
    },
    /** GPU time of one of the check's scenes on this machine, uncapped, on a phone-shaped canvas (CSS px × dpr). */
    async bench(o: ShotOpts & { width: number; height: number; seconds?: number }): Promise<Timing & { triangles: number; cards: number }> {
      host.replaceChildren()
      const canvas = el('canvas')
      canvas.style.width = `${o.width}px`
      canvas.style.height = `${o.height}px`
      host.append(canvas)
      const cinematic = o.kind === 'card'
      const view = await createView(o.backend ?? 'webgl', { canvas, width: o.width, height: o.height, dpr: o.dpr ?? 2, cinematic, focus: 2.4 })
      if (!view) throw new Error('no such renderer here')
      const assets = await loadAssets(view.renderer as never, o.format ?? 'ktx2')
      const ps = buildScene(o.kind ?? 'battle', assets, view, o.width / o.height, { cinematic })
      await view.init(ps.scene, ps.camera)
      view.setCinematic(cinematic, ps.focus)
      if (o.level) view.setLevel(o.level)
      for (let i = 0; i < 20; i++) {
        ps.update(i / 60)
        view.render()
        await new Promise((r) => requestAnimationFrame(r))
      }
      const t = await measure(view, ps, o.seconds ?? 6, false)
      const out = { ...t, triangles: countTriangles(ps.scene), cards: countCards(ps.scene) }
      view.dispose()
      return out
    },
  }
  ;(window as unknown as { __perf: typeof api }).__perf = api
}

if (mode === 'shot') shotApi()
else checkUi()
