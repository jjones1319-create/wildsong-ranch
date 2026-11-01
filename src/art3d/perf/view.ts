import { HalfFloatType, NeutralToneMapping, PCFSoftShadowMap, PMREMGenerator, SRGBColorSpace, Vector2, WebGLRenderer, WebGLRenderTarget } from 'three'
import type { Camera, PerspectiveCamera, Scene, Texture } from 'three'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js'
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js'
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js'
import { ART } from '../../data/tuning.ts'
import { roomEnvironmentScene } from './content.ts'

/**
 * Art 2.1 Performance check: one interface over the two renderers, so the A/B test draws the same scene, lights,
 * materials and effects (shadows, AO, bloom, grading, depth of field, MSAA) with each.
 */

export type Backend = 'webgl' | 'webgpu'
export type Level = (typeof ART.ultra.levels)[number]

export interface ViewOptions { canvas: HTMLCanvasElement; width: number; height: number; dpr: number; cinematic: boolean; focus: number }

export interface PerfView {
  backend: Backend
  /** The renderer, for loaders (KTX2 picks its GPU format from it). */
  renderer: unknown
  /** A prefiltered environment for reflections, made by this renderer. */
  environment: Texture
  init(scene: Scene, camera: PerspectiveCamera): Promise<void>
  setSize(width: number, height: number, dpr: number): void
  setLevel(level: Level): void
  setCinematic(on: boolean, focus: number): void
  render(): void
  /** The last GPU time per frame in ms, when the browser exposes a GPU timer. */
  gpuMs(): number | null
  /** Bytes of the view's own render targets (colour, depth, MSAA, AO, bloom), estimated. */
  targetBytes(): number
  readPixels(): string
  dispose(): void
}

const GRADE_SHADER = {
  uniforms: {
    tDiffuse: { value: null as Texture | null },
    saturation: { value: ART.ultra.post.grade.saturation },
    contrast: { value: ART.ultra.post.grade.contrast },
    warmth: { value: ART.ultra.post.grade.warmth },
    vignette: { value: ART.ultra.post.grade.vignette },
  },
  vertexShader: /* glsl */ `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */ `
uniform sampler2D tDiffuse; uniform float saturation; uniform float contrast; uniform float warmth; uniform float vignette;
varying vec2 vUv;
void main() {
  vec4 c = texture2D(tDiffuse, vUv);
  float l = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
  vec3 g = mix(vec3(l), c.rgb, saturation);
  g = (g - 0.5) * contrast + 0.5;
  g += vec3(warmth, warmth * 0.4, -warmth) * smoothstep(0.4, 1.0, l);
  vec2 d = vUv - 0.5;
  g *= 1.0 - vignette * smoothstep(0.35, 0.85, length(d) * 1.4);
  gl_FragColor = vec4(clamp(g, 0.0, 1.0), c.a);
}`,
}

/** The levels a view applies, from 'all' down to 'no-msaa' (each includes the ones before it). */
export function levelFlags(level: Level) {
  const L = ART.ultra.levels
  const i = L.indexOf(level)
  return {
    aoHalf: i >= L.indexOf('ao-half'),
    bloom: i < L.indexOf('no-bloom'),
    shadowPx: i >= L.indexOf('shadow-1024') ? 1024 : ART.ultra.studio.shadowMapPx,
    ao: i < L.indexOf('no-ao'),
    msaa: i >= L.indexOf('no-msaa') ? 0 : i >= L.indexOf('msaa-2') ? 2 : ART.ultra.post.msaa,
  }
}

export function createWebGLView(opts: ViewOptions): PerfView {
  const renderer = new WebGLRenderer({ canvas: opts.canvas, antialias: false, powerPreference: 'high-performance', preserveDrawingBuffer: true, stencil: false })
  renderer.outputColorSpace = SRGBColorSpace
  renderer.toneMapping = NeutralToneMapping
  renderer.toneMappingExposure = ART.ultra.studio.exposure
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = PCFSoftShadowMap
  renderer.setPixelRatio(opts.dpr)
  renderer.setSize(opts.width, opts.height, false)
  const pmrem = new PMREMGenerator(renderer)
  const environment = pmrem.fromScene(roomEnvironmentScene(), 0.04).texture
  pmrem.dispose()
  const gl = renderer.getContext() as WebGL2RenderingContext
  const timer = gl.getExtension('EXT_disjoint_timer_query_webgl2') as { TIME_ELAPSED_EXT: number; GPU_DISJOINT_EXT: number } | null
  const pending: WebGLQuery[] = []
  let lastGpu: number | null = null
  let composer: EffectComposer | null = null
  let rt: WebGLRenderTarget | null = null
  let gtao: GTAOPass | null = null
  let bloom: UnrealBloomPass | null = null
  let bokeh: BokehPass | null = null
  let scene: Scene | null = null
  let camera: PerspectiveCamera | null = null
  let aoCamera: Camera | null = null
  let level: Level = 'all'
  let size = { w: opts.width, h: opts.height, dpr: opts.dpr }
  let cinematic = opts.cinematic
  let focus = opts.focus

  function build(): void {
    if (!scene || !camera) return
    composer?.dispose()
    rt?.dispose()
    const f = levelFlags(level)
    const w = Math.round(size.w * size.dpr)
    const h = Math.round(size.h * size.dpr)
    rt = new WebGLRenderTarget(w, h, { type: HalfFloatType, samples: f.msaa })
    composer = new EffectComposer(renderer, rt)
    composer.setPixelRatio(1)
    composer.setSize(w, h)
    composer.addPass(new RenderPass(scene, camera))
    gtao = null
    if (f.ao) {
      // fur cards are alpha-tested; the AO normal pass can't cut them out, so it draws without them (layer 1)
      aoCamera = camera.clone()
      aoCamera.layers.disable(1)
      const aw = f.aoHalf ? Math.round(w / 2) : w
      const ah = f.aoHalf ? Math.round(h / 2) : h
      gtao = new GTAOPass(scene, aoCamera, aw, ah)
      gtao.output = GTAOPass.OUTPUT.Default
      gtao.blendIntensity = ART.ultra.post.aoIntensity
      gtao.updateGtaoMaterial({ radius: ART.ultra.post.aoRadius, distanceExponent: 1, thickness: 1, scale: 1, samples: 12 })
      composer.addPass(gtao)
    }
    bloom = null
    if (f.bloom) {
      const b = ART.ultra.post.bloom
      bloom = new UnrealBloomPass(new Vector2(w, h), b.strength, b.radius, b.threshold)
      composer.addPass(bloom)
    }
    bokeh = new BokehPass(scene, camera, { focus, aperture: ART.ultra.post.dof.aperture, maxblur: ART.ultra.post.dof.maxBlur })
    bokeh.enabled = cinematic
    composer.addPass(bokeh)
    composer.addPass(new OutputPass())
    composer.addPass(new ShaderPass(GRADE_SHADER))
    const sh = scene.children.find((c) => (c as { isDirectionalLight?: boolean; castShadow?: boolean }).isDirectionalLight && (c as { castShadow: boolean }).castShadow) as
      | { shadow: { mapSize: Vector2; map: { dispose(): void } | null } }
      | undefined
    if (sh && sh.shadow.mapSize.x !== f.shadowPx) {
      sh.shadow.mapSize.set(f.shadowPx, f.shadowPx)
      sh.shadow.map?.dispose()
      sh.shadow.map = null
    }
  }

  function pollTimer(): void {
    if (!timer) return
    while (pending.length) {
      const q = pending[0]!
      if (!gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)) break
      pending.shift()
      if (!gl.getParameter(timer.GPU_DISJOINT_EXT)) lastGpu = gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6
      gl.deleteQuery(q)
    }
  }

  return {
    backend: 'webgl',
    renderer,
    environment,
    async init(s, c) {
      scene = s
      camera = c
      build()
    },
    setSize(w, h, dpr) {
      size = { w, h, dpr }
      renderer.setPixelRatio(dpr)
      renderer.setSize(w, h, false)
      build()
    },
    setLevel(l) {
      if (l === level) return
      level = l
      build()
    },
    setCinematic(on, f) {
      cinematic = on
      focus = f
      if (bokeh) {
        bokeh.enabled = on
        ;(bokeh.uniforms as Record<string, { value: number }>).focus!.value = f
      }
    },
    render() {
      if (!composer) return
      pollTimer()
      let q: WebGLQuery | null = null
      if (timer && pending.length < 4) {
        q = gl.createQuery()
        if (q) gl.beginQuery(timer.TIME_ELAPSED_EXT, q)
      }
      if (aoCamera && camera) aoCamera.copy(camera, false).layers.disable(1)
      composer.render()
      if (q && timer) {
        gl.endQuery(timer.TIME_ELAPSED_EXT)
        pending.push(q)
      }
    },
    gpuMs: () => lastGpu,
    targetBytes() {
      const f = levelFlags(level)
      const px = size.w * size.dpr * size.h * size.dpr
      // half-float colour (8 B) × MSAA samples + resolve, depth (4 B), two composer buffers, AO (normals + AO), bloom mips
      const main = px * (8 * Math.max(1, f.msaa) + 8 + 4 * Math.max(1, f.msaa))
      const comp = px * 8 * 2
      const ao = f.ao ? px * (f.aoHalf ? 0.25 : 1) * (8 + 4 + 4) : 0
      const bl = f.bloom ? px * 8 * 0.66 : 0
      const shadow = f.shadowPx * f.shadowPx * 4
      return Math.round(main + comp + ao + bl + shadow)
    },
    readPixels: () => renderer.domElement.toDataURL('image/png'),
    dispose() {
      composer?.dispose()
      rt?.dispose()
      environment.dispose()
      renderer.dispose()
    },
  }
}

/** The WebGPU view lives in its own lazy chunk (three/webgpu is large); undefined when the browser has no WebGPU. */
export async function createView(backend: Backend, opts: ViewOptions): Promise<PerfView | undefined> {
  if (backend === 'webgl') return createWebGLView(opts)
  if (!('gpu' in navigator)) return undefined
  const m = await import('./viewGpu.ts')
  return m.createWebGPUView(opts)
}
