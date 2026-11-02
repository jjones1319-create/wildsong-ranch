import type { BufferGeometry, Mesh, Object3D } from 'three'
import { ART } from '../../data/tuning.ts'
import { PERF_TEXT as T } from '../../data/text/perf.ts'
import { gpuBytes, loadAssets, type Assets, type TexFormat } from './content.ts'
import { buildScene, countCards, countTriangles, type PerfScene, type SceneKind } from './stage.ts'
import { createView, type Backend, type Level, type PerfView } from './view.ts'

/**
 * Art 2.1 Performance check (docs/ART_2_DETAIL.md §6.2), run by the owner on the phone:
 *   1. WebGL vs WebGPU on the battle scene (uncapped, fixed resolution) and a frame from each;
 *   2. the Monster Card close-up (cinematic textures, depth of field) and Meadow Dash (four runners);
 *   3. a battle soak held at 60 fps by dynamic resolution and quality, with speed probes before and after to show
 *      how much the phone slowed down as it warmed up; fps, resolution, quality and memory at the start and the end.
 */

const U = ART.ultra
const S = U.scaling

/** cpuMs: the page's own work per frame (scene update + issuing the draw), the median; high when the CPU is the limit. */
export interface Timing { seconds: number; frames: number; fps: number; p95Ms: number; missShare: number; gpuMs: number | null; cpuMs: number }
interface SecondLog { t: number; fps: number; dpr: number; level: Level; gpuMs: number | null; cpuMs: number; missShare: number }
export interface WindowSummary { fps: number; dpr: number; px: string; level: Level; gpuMs: number | null; memoryMb: number; jsHeapMb: number | null }

export interface CheckResult {
  when: string
  device: Record<string, string | number>
  format: TexFormat
  ab: Partial<Record<Backend, Timing & { frame?: string }>>
  abDpr: number
  chosen: Backend
  /** Why that renderer: faster, a tie at the screen's limit, the only one, or ?renderer= in the address. */
  chosenWhy: string
  card?: Timing
  dash?: Timing
  probeStart?: Timing
  probeEnd?: Timing
  soakStart?: WindowSummary
  soakEnd?: WindowSummary
  /** How often the controller changed the resolution or the effects, and the resolution range it used. */
  soakChanges?: { count: number; dprMin: number; dprMax: number }
  /** Every 30 s of the soak: fps, resolution, effects, GPU and CPU ms, late frames. */
  soakTimeline?: { t: number; fps: number; dpr: number; level: Level; gpuMs: number | null; cpuMs: number; missPct: number }[]
  soakMinutes: number
  throttle?: number
  pass?: boolean
  scene: { triangles: number; cards: number; drawCalls: number; textureMb: number }
}

function median(a: number[]): number {
  if (!a.length) return 0
  const s = [...a].sort((x, y) => x - y)
  return s[Math.floor(s.length / 2)]!
}

function pct(a: number[], p: number): number {
  if (!a.length) return 0
  const s = [...a].sort((x, y) => x - y)
  return s[Math.min(s.length - 1, Math.floor(s.length * p))]!
}

const raf = () => new Promise<number>((r) => requestAnimationFrame(r))

function geometryBytes(root: Object3D): number {
  let n = 0
  const seen = new Set<BufferGeometry>()
  root.traverse((o) => {
    const g = (o as Mesh).geometry
    if (!g || seen.has(g)) return
    seen.add(g)
    for (const a of Object.values(g.attributes)) n += (a.array as ArrayLike<number> & { byteLength: number }).byteLength
    if (g.index) n += (g.index.array as unknown as { byteLength: number }).byteLength
  })
  return n
}

function textureMb(assets: Assets): number {
  let n = 0
  for (const set of [assets.body, assets.cine, ...(assets.standin ? [assets.standin.tex] : [])]) for (const t of [set.base, set.normal, set.orm]) n += gpuBytes(t)
  return n / 2 ** 20
}

function memoryMb(view: PerfView, ps: PerfScene, assets: Assets): number {
  return textureMb(assets) + (view.targetBytes() + geometryBytes(ps.scene)) / 2 ** 20
}

function jsHeapMb(): number | null {
  const m = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory
  return m ? m.usedJSHeapSize / 2 ** 20 : null
}

/** Play a scene for `seconds`, uncapped or capped at 60 fps, and time every frame. */
export async function measure(view: PerfView, ps: PerfScene, seconds: number, cap: boolean, onFrame?: (t: number, at: number, cpuMs: number) => void): Promise<Timing> {
  const budget = 1000 / S.targetFps
  const t0 = performance.now()
  let last = t0
  const intervals: number[] = []
  const gpus: number[] = []
  const cpus: number[] = []
  for (;;) {
    const now = await raf()
    if (now - t0 > seconds * 1000) break
    // capped: skip only a display refresh that comes far too early (a 120 Hz screen's in-between frames), never a
    // 60 Hz refresh that is a little early, or every such jitter would cost a whole frame
    if (cap && now - last < budget * 0.75) continue
    const t = (now - t0) / 1000
    const c0 = performance.now()
    ps.update(t)
    view.render()
    const cpu = performance.now() - c0
    cpus.push(cpu)
    // `now` is when the display asked for the frame: timing after the draw would add the draw's own variation
    onFrame?.(t, now, cpu)
    if (intervals.length || now - last < 1000) intervals.push(now - last)
    last = now
    const g = view.gpuMs()
    if (g !== null) gpus.push(g)
  }
  const frames = intervals.length
  const total = intervals.reduce((a, b) => a + b, 0) || 1
  return {
    seconds,
    frames,
    fps: (frames * 1000) / total,
    p95Ms: pct(intervals, 0.95),
    missShare: intervals.filter((i) => i > budget * S.missFactor).length / Math.max(1, frames),
    gpuMs: gpus.length ? median(gpus) : null,
    cpuMs: median(cpus),
  }
}

/** The resolution range on this screen: never above the screen's own pixels (rendering past them costs and shows nothing). */
function dprRange(): { max: number; start: number } {
  const max = Math.max(S.dprMin, Math.min(S.dprMax, devicePixelRatio || S.dprMax))
  return { max, start: Math.min(S.dprStart, max) }
}

/**
 * Pick the renderer. When both reach the screen's frame limit the frame rate can't tell them apart, so the GPU time
 * decides; Android Chrome gives no GPU timer for WebGL, so WebGPU wins a tie when its own GPU time leaves room.
 */
function pickRenderer(a: Timing | undefined, g: Timing | undefined): { chosen: Backend; why: string } {
  if (!g) return { chosen: 'webgl', why: 'WebGPU is not available here' }
  if (!a) return { chosen: 'webgpu', why: 'WebGL is not available here' }
  const budget = 1000 / S.targetFps
  const atLimit = (x: Timing) => x.fps >= S.targetFps * 0.95 && x.missShare < 0.02
  if (atLimit(a) && atLimit(g)) {
    if (a.gpuMs !== null && g.gpuMs !== null) return a.gpuMs <= g.gpuMs ? { chosen: 'webgl', why: 'a tie at the screen limit; less GPU time' } : { chosen: 'webgpu', why: 'a tie at the screen limit; less GPU time' }
    if (g.gpuMs !== null && g.gpuMs < budget * 0.8) return { chosen: 'webgpu', why: 'a tie at the screen limit; WebGPU GPU time leaves room (WebGL has no GPU timer here)' }
    return { chosen: 'webgl', why: 'a tie at the screen limit' }
  }
  return g.fps > a.fps * 1.03 ? { chosen: 'webgpu', why: 'faster' } : { chosen: 'webgl', why: 'faster or equal' }
}

interface Ui { status(text: string): void; live(text: string): void; canvas(): HTMLCanvasElement }

async function stage(backend: Backend, kind: SceneKind, ui: Ui, format: TexFormat, dpr: number, cinematic = false) {
  const canvas = ui.canvas()
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  const view = await createView(backend, { canvas, width: w, height: h, dpr, cinematic, focus: 3 })
  if (!view) return null
  const assets = await loadAssets(view.renderer as never, format)
  const ps = buildScene(kind, assets, view, w / h, { cinematic })
  await view.init(ps.scene, ps.camera)
  view.setCinematic(cinematic, ps.focus)
  // warm up: compile shaders and upload textures before timing
  for (let i = 0; i < 20; i++) {
    ps.update(i / 60)
    view.render()
    await raf()
  }
  return { view, assets, ps }
}

function summarise(log: SecondLog[], fromS: number, toS: number, view: PerfView, ps: PerfScene, assets: Assets, w: number, h: number): WindowSummary {
  const win = log.filter((l) => l.t >= fromS && l.t <= toS)
  const dpr = median(win.map((l) => l.dpr))
  const lv = win.length ? win[win.length - 1]!.level : 'all'
  const g = win.map((l) => l.gpuMs).filter((x): x is number => x !== null)
  return {
    fps: win.reduce((a, l) => a + l.fps, 0) / Math.max(1, win.length),
    dpr,
    px: `${Math.round(w * dpr)}×${Math.round(h * dpr)}`,
    level: lv,
    gpuMs: g.length ? median(g) : null,
    memoryMb: Math.round(memoryMb(view, ps, assets)),
    jsHeapMb: jsHeapMb() === null ? null : Math.round(jsHeapMb()!),
  }
}

/** The battle soak with the dynamic resolution and quality controller (ART.ultra.scaling). */
async function soak(view: PerfView, ps: PerfScene, assets: Assets, minutes: number, ui: Ui): Promise<{ start: WindowSummary; end: WindowSummary; log: SecondLog[]; changes: NonNullable<CheckResult['soakChanges']> }> {
  const canvas = ui.canvas()
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  const budget = 1000 / S.targetFps
  const range = dprRange()
  let dpr: number = range.start
  let li = 0
  let changes = 0
  let dprLow = dpr
  let dprHigh = dpr
  // a change (resize, effects) costs a frame or two itself; those seconds aren't read as the phone being slow
  let graceUntil = 0
  const levels = U.levels
  view.setSize(w, h, dpr)
  view.setLevel(levels[li]!)
  const log: SecondLog[] = []
  let recent: number[] = []
  let lastDown = -1e9
  let calmSince = performance.now()
  let secondStart = performance.now()
  let secondFrames = 0
  let secondMiss = 0
  const total = minutes * 60
  const t0 = performance.now()
  let secondCpu: number[] = []
  await measure(view, ps, total, true, (_, now, cpu) => {
    const t = (now - t0) / 1000
    secondCpu.push(cpu)
    recent.push(now)
    recent = recent.filter((x) => now - x < 1000)
    secondFrames++
    if (recent.length > 1 && recent[recent.length - 1]! - recent[recent.length - 2]! > budget * S.missFactor) secondMiss++
    if (now - secondStart >= 1000) {
      const missShare = secondMiss / Math.max(1, secondFrames)
      log.push({ t, fps: (secondFrames * 1000) / (now - secondStart), dpr, level: levels[li]!, gpuMs: view.gpuMs(), cpuMs: median(secondCpu), missShare })
      secondCpu = []
      const decide = now >= graceUntil
      const changed = (): void => {
        changes++
        dprLow = Math.min(dprLow, dpr)
        dprHigh = Math.max(dprHigh, dpr)
        graceUntil = now + S.graceMs
      }
      ui.live(`${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')} · ${log[log.length - 1]!.fps.toFixed(0)} fps · ${Math.round(w * dpr)}×${Math.round(h * dpr)} px (${dpr.toFixed(2)}×) · ${levels[li]}`)
      if (!decide) {
        // the last change's own hitch is still in this second: wait for a clean one
      } else if (missShare > S.missShareDown) {
        if (dpr - S.dprStepDown >= S.dprMin - 1e-6) {
          dpr = Math.round((dpr - S.dprStepDown) * 100) / 100
          view.setSize(w, h, dpr)
          changed()
        } else if (li < levels.length - 1) {
          li++
          view.setLevel(levels[li]!)
          changed()
        }
        lastDown = now
        calmSince = now
      } else if (missShare <= S.calmMissShare && now - lastDown > S.holdAfterDownMs && now - calmSince > S.calmMsUp) {
        const g = view.gpuMs()
        if (g === null || g < budget * S.gpuShareUp) {
          // undo the last thing given up: effects first (they were dropped last), then resolution
          if (li > 0) {
            li--
            view.setLevel(levels[li]!)
            changed()
          } else if (dpr + S.dprStepUp <= range.max + 1e-6) {
            dpr = Math.round((dpr + S.dprStepUp) * 100) / 100
            view.setSize(w, h, dpr)
            changed()
          }
          calmSince = now
        }
      } else if (missShare > S.calmMissShare) {
        // not bad enough to step down, but not calm: the calm clock starts again
        calmSince = now
      }
      secondStart = now
      secondFrames = 0
      secondMiss = 0
    }
  })
  const win = Math.min(ART.ultra.check.windowSeconds, total / 3)
  return {
    start: summarise(log, 0, win, view, ps, assets, w, h),
    end: summarise(log, total - win, total, view, ps, assets, w, h),
    log,
    changes: { count: changes, dprMin: dprLow, dprMax: dprHigh },
  }
}

export async function runCheck(quick: boolean, ui: Ui): Promise<CheckResult> {
  const Q = quick ? { ...U.check, ...U.check.quick } : U.check
  const q = new URLSearchParams(location.search).get('tex')
  // the candidate that fits the download cap (ART_2_DETAIL §3.3); ?tex=webp runs the same scenes on WebP
  const format: TexFormat = q === 'webp' || q === 'ktx2' ? q : 'ktx2-etc1s'
  const nav = navigator as Navigator & { deviceMemory?: number; hardwareConcurrency?: number }
  const result: CheckResult = {
    when: new Date().toISOString(),
    device: { ua: navigator.userAgent, dpr: devicePixelRatio, screen: `${screen.width}×${screen.height}`, memoryGb: nav.deviceMemory ?? 0, cores: nav.hardwareConcurrency ?? 0 },
    format,
    ab: {},
    abDpr: Math.max(2, dprRange().max),
    chosen: 'webgl',
    chosenWhy: '',
    soakMinutes: Q.soakMinutes,
    scene: { triangles: 0, cards: 0, drawCalls: 0, textureMb: 0 },
  }
  const wake = await (navigator as Navigator & { wakeLock?: { request(t: 'screen'): Promise<{ release(): Promise<void> }> } }).wakeLock?.request('screen').catch(() => undefined)
  try {
    // 1. the renderer A/B at a fixed resolution, uncapped
    for (const b of ['webgl', 'webgpu'] as const) {
      ui.status(T.stages.ab(b === 'webgl' ? 'WebGL' : 'WebGPU'))
      const s = await stage(b, 'battle', ui, format, result.abDpr).catch((e) => {
        ui.live(String(e))
        return null
      })
      if (!s) continue
      const timing = await measure(s.view, s.ps, Q.abSeconds, false)
      result.ab[b] = { ...timing, frame: s.view.readPixels() }
      if (b === 'webgl') {
        result.scene = { triangles: countTriangles(s.ps.scene), cards: countCards(s.ps.scene), drawCalls: 0, textureMb: Math.round(textureMb(s.assets)) }
        const info = (s.view.renderer as { info?: { render?: { calls?: number } } }).info
        result.scene.drawCalls = info?.render?.calls ?? 0
      }
      s.view.dispose()
    }
    const pick = pickRenderer(result.ab.webgl, result.ab.webgpu)
    const forced = new URLSearchParams(location.search).get('renderer')
    if ((forced === 'webgl' || forced === 'webgpu') && result.ab[forced]) {
      result.chosen = forced
      result.chosenWhy = 'set in the address (?renderer=)'
    } else {
      result.chosen = pick.chosen
      result.chosenWhy = pick.why
    }
    // 2. the close-up and Meadow Dash
    ui.status(T.stages.card)
    const card = await stage(result.chosen, 'card', ui, format, U.scaling.dprStart, true)
    if (card) {
      result.card = await measure(card.view, card.ps, Q.sceneSeconds, true)
      card.view.dispose()
    }
    ui.status(T.stages.dash)
    const dash = await stage(result.chosen, 'dash', ui, format, U.scaling.dprStart)
    if (dash) {
      result.dash = await measure(dash.view, dash.ps, Q.sceneSeconds, true)
      dash.view.dispose()
    }
    // 3. the soak, with a fixed speed probe before and after
    const battle = await stage(result.chosen, 'battle', ui, format, 2)
    if (battle) {
      const { view, ps, assets } = battle
      ui.status(T.stages.probe('cold'))
      result.probeStart = await measure(view, ps, Q.probeSeconds, false)
      ui.status(T.stages.soak(Q.soakMinutes))
      const s = await soak(view, ps, assets, Q.soakMinutes, ui)
      result.soakStart = s.start
      result.soakEnd = s.end
      result.soakChanges = s.changes
      result.soakTimeline = timeline(s.log, Q.windowSeconds)
      ui.status(T.stages.probe('warm'))
      view.setSize(ui.canvas().clientWidth, ui.canvas().clientHeight, 2)
      view.setLevel('all')
      for (let i = 0; i < 10; i++) {
        view.render()
        await raf()
      }
      result.probeEnd = await measure(view, ps, Q.probeSeconds, false)
      const startMs = result.probeStart.gpuMs ?? 1000 / result.probeStart.fps
      const endMs = result.probeEnd.gpuMs ?? 1000 / result.probeEnd.fps
      result.throttle = endMs / Math.max(0.001, startMs)
      result.pass = s.end.fps >= Q.passFps && (s.log.slice(-Q.windowSeconds).reduce((x, l) => x + l.missShare, 0) / Math.max(1, Math.min(Q.windowSeconds, s.log.length))) <= Q.passMissShare
      view.dispose()
    }
  } finally {
    await wake?.release().catch(() => undefined)
  }
  try {
    localStorage.setItem('wildsong/perf/last', JSON.stringify({ ...result, ab: Object.fromEntries(Object.entries(result.ab).map(([k, v]) => [k, { ...v, frame: undefined }])) }))
  } catch {
    /* storage full or blocked: the on-screen report still has everything */
  }
  return result
}

/** The soak's seconds summed into windows of `w` seconds. */
function timeline(log: SecondLog[], w: number): NonNullable<CheckResult['soakTimeline']> {
  const out: NonNullable<CheckResult['soakTimeline']> = []
  for (let from = 0; from < (log[log.length - 1]?.t ?? 0); from += w) {
    const win = log.filter((l) => l.t >= from && l.t < from + w)
    if (!win.length) continue
    const avg = (k: (l: SecondLog) => number) => win.reduce((a, l) => a + k(l), 0) / win.length
    const g = win.map((l) => l.gpuMs).filter((x): x is number => x !== null)
    const last = win[win.length - 1]!
    out.push({ t: from + w, fps: avg((l) => l.fps), dpr: last.dpr, level: last.level, gpuMs: g.length ? median(g) : null, cpuMs: median(win.map((l) => l.cpuMs)), missPct: avg((l) => l.missShare) * 100 })
  }
  return out
}

/** The plain-text report the owner copies into Claude Code. */
export function reportText(r: CheckResult): string {
  const f = (x: number | null | undefined, d = 1) => (x == null ? 'n/a' : x.toFixed(d))
  const t = (x?: Timing) => (x ? `${f(x.fps, 0)} fps, 95th ${f(x.p95Ms)} ms, missed ${f(x.missShare * 100)}%, GPU ${f(x.gpuMs)} ms, CPU ${f(x.cpuMs)} ms` : 'not run')
  const w = (x?: WindowSummary) => (x ? `${f(x.fps, 0)} fps at ${x.px} (${f(x.dpr, 2)}×), effects ${x.level}, GPU ${f(x.gpuMs)} ms, graphics memory ~${x.memoryMb} MB, JS heap ${x.jsHeapMb ?? 'n/a'} MB` : 'not run')
  const lines = [
    `Wildsong Ranch Performance check (Art 2.1 Ultra), ${r.when}`,
    `Device: ${r.device.ua}`,
    `Screen ${r.device.screen} @${r.device.dpr}x, ${r.device.cores} cores, ${r.device.memoryGb || '?'} GB (browser-reported)`,
    `Textures: ${r.format.toUpperCase()} · scene: ${r.scene.triangles.toLocaleString()} triangles, ${r.scene.cards.toLocaleString()} fur cards, ${r.scene.drawCalls} draw calls, textures ~${r.scene.textureMb} MB on the GPU`,
    `Renderer A/B (battle, ${f(r.abDpr, 2)}×, uncapped): WebGL ${t(r.ab.webgl)} | WebGPU ${r.ab.webgpu ? t(r.ab.webgpu) : T.notAvailable} → using ${r.chosen} (${r.chosenWhy})`,
    `Monster Card close-up: ${t(r.card)}`,
    `Meadow Dash (4): ${t(r.dash)}`,
    `Speed probe cold: ${t(r.probeStart)}`,
    `Battle soak ${r.soakMinutes} min, start: ${w(r.soakStart)}`,
    `Battle soak ${r.soakMinutes} min, end:   ${w(r.soakEnd)}`,
    `Controller: ${r.soakChanges ? `${r.soakChanges.count} changes, resolution ${f(r.soakChanges.dprMin, 2)}–${f(r.soakChanges.dprMax, 2)}×` : 'n/a'}`,
    ...(r.soakTimeline ?? []).map((x) => `  ${String(Math.floor(x.t / 60)).padStart(2)}:${String(Math.floor(x.t % 60)).padStart(2, '0')}  ${f(x.fps, 0)} fps  ${f(x.dpr, 2)}×  ${x.level}  GPU ${f(x.gpuMs)}  CPU ${f(x.cpuMs)}  late ${f(x.missPct)}%`),
    `Speed probe warm: ${t(r.probeEnd)}`,
    `Throttling: the same frame took ${f(r.throttle, 2)}× as long at the end (1.00 = no slowdown)`,
    `Result: ${r.pass === undefined ? 'incomplete' : r.pass ? T.pass : T.fail} (pass = ≥ ${ART.ultra.check.passFps} fps with < ${ART.ultra.check.passMissShare * 100}% missed frames over the last ${ART.ultra.check.windowSeconds} s)`,
  ]
  return lines.join('\n')
}

// ----------------------------------------------------------------------------- memory ceiling (opt-in)
const MEM_KEY = 'wildsong/perf/memceiling'

export function lastMemoryCeiling(): number | null {
  const v = Number(localStorage.getItem(MEM_KEY))
  return Number.isFinite(v) && v > 0 ? v : null
}

/** Fill graphics memory with 2048² textures, drawing each once so it is really resident, until the GPU refuses. */
export async function memoryCeiling(canvas: HTMLCanvasElement, onStep: (mb: number) => void): Promise<number> {
  const gl = canvas.getContext('webgl2', { antialias: false, powerPreference: 'high-performance' })
  if (!gl) return 0
  let lost = false
  canvas.addEventListener('webglcontextlost', () => { lost = true })
  const vs = gl.createShader(gl.VERTEX_SHADER)!
  gl.shaderSource(vs, '#version 300 es\nin vec2 p; out vec2 uv; void main(){ uv = p * 0.5 + 0.5; gl_Position = vec4(p, 0, 1); }')
  gl.compileShader(vs)
  const fs = gl.createShader(gl.FRAGMENT_SHADER)!
  gl.shaderSource(fs, '#version 300 es\nprecision mediump float; uniform sampler2D t; in vec2 uv; out vec4 o; void main(){ o = texture(t, uv) + vec4(0.01); }')
  gl.compileShader(fs)
  const prog = gl.createProgram()!
  gl.attachShader(prog, vs)
  gl.attachShader(prog, fs)
  gl.linkProgram(prog)
  gl.useProgram(prog)
  const buf = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buf)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
  gl.enableVertexAttribArray(0)
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0)
  const size = 2048
  const perTexMb = (size * size * 4 * 1.333) / 2 ** 20
  const keep: WebGLTexture[] = []
  const pixels = new Uint8Array(size * size * 4)
  for (let i = 0; i < pixels.length; i += 97) pixels[i] = i & 255
  let mb = 0
  while (mb < ART.ultra.check.memoryCapMb) {
    const t = gl.createTexture()
    if (!t) break
    gl.bindTexture(gl.TEXTURE_2D, t)
    gl.texStorage2D(gl.TEXTURE_2D, 12, gl.RGBA8, size, size)
    gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, size, size, gl.RGBA, gl.UNSIGNED_BYTE, pixels)
    gl.generateMipmap(gl.TEXTURE_2D)
    gl.drawArrays(gl.TRIANGLES, 0, 3)
    const px = new Uint8Array(4)
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px)
    if (lost || gl.isContextLost() || gl.getError() === gl.OUT_OF_MEMORY) break
    keep.push(t)
    mb = Math.round(keep.length * perTexMb)
    try {
      localStorage.setItem(MEM_KEY, String(mb))
    } catch {
      /* ignore */
    }
    onStep(mb)
    await raf()
  }
  for (const t of keep) gl.deleteTexture(t)
  return mb
}
