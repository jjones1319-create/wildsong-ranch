import { MeshPhysicalNodeMaterial, NeutralToneMapping, PCFSoftShadowMap, PMREMGenerator, RenderPipeline, SRGBColorSpace, WebGPURenderer } from 'three/webgpu'
import type { Mesh, MeshPhysicalMaterial, Node, PerspectiveCamera, Scene, Texture } from 'three/webgpu'
import { abs, float, mix, mrt, normalView, pass, positionViewDirection, renderOutput, smoothstep, texture, uniform, uv, vec3, vec4, dot, length, clamp } from 'three/tsl'
import { ao } from 'three/addons/tsl/display/GTAONode.js'
import { bloom } from 'three/addons/tsl/display/BloomNode.js'
import { dof } from 'three/addons/tsl/display/DepthOfFieldNode.js'
import { ART } from '../../data/tuning.ts'
import { roomEnvironmentScene } from './content.ts'
import { levelFlags, type Level, type PerfView, type ViewOptions } from './view.ts'

/**
 * Art 2.1 Performance check: the WebGPU renderer (three/webgpu, TSL post effects) with the same scene, lights,
 * materials and effects as the WebGL view, so the A/B on the phone compares like with like.
 */
export async function createWebGPUView(opts: ViewOptions): Promise<PerfView> {
  // MSAA lives in the scene pass; the canvas itself only receives the finished picture (no multisampled canvas)
  const renderer = new WebGPURenderer({ canvas: opts.canvas, antialias: false, powerPreference: 'high-performance', trackTimestamp: true })
  await renderer.init()
  renderer.outputColorSpace = SRGBColorSpace
  renderer.toneMapping = NeutralToneMapping
  renderer.toneMappingExposure = ART.ultra.studio.exposure
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = PCFSoftShadowMap
  renderer.setPixelRatio(opts.dpr)
  renderer.setSize(opts.width, opts.height, false)
  const pmrem = new PMREMGenerator(renderer)
  const environment = pmrem.fromScene(roomEnvironmentScene(), 0.04).texture as Texture
  pmrem.dispose()
  let pipeline: RenderPipeline | null = null
  let scene: Scene | null = null
  let camera: PerspectiveCamera | null = null
  let level: Level = 'all'
  let size = { w: opts.width, h: opts.height, dpr: opts.dpr }
  let cinematic = opts.cinematic
  const focusU = uniform(opts.focus)
  let lastGpu: number | null = null
  let resolving = false
  // the effect nodes of the current pipeline: disposed on a rebuild, or every level change would leak their targets
  let owned: { dispose(): void }[] = []

  function build(): void {
    if (!scene || !camera) return
    pipeline?.dispose()
    for (const n of owned) n.dispose()
    owned = []
    const f = levelFlags(level)
    const p = ART.ultra.post
    const scenePass = pass(scene, camera, { samples: f.msaa })
    owned.push(scenePass)
    const color = scenePass.getTextureNode('output')
    // TSL's generic node types don't follow a chain of effects; the graph is checked when the pipeline compiles
    let out = vec4(color) as unknown as Node<'vec4'>
    if (f.ao) {
      // GTAO can't read a multisampled depth buffer: a plain depth + normal pre-pass feeds it (as the WebGL GTAO pass does)
      const prePass = pass(scene, camera, { samples: 0 })
      prePass.setMRT(mrt({ output: normalView }))
      const aoPass = ao(prePass.getTextureNode('depth'), prePass.getTextureNode(), camera)
      owned.push(prePass, aoPass)
      aoPass.resolutionScale = f.aoHalf ? 0.5 : 1
      aoPass.radius.value = p.aoRadius
      aoPass.samples.value = 12
      const occ = mix(float(1), aoPass.getTextureNode().r, float(p.aoIntensity))
      out = vec4(color.rgb.mul(occ), color.a) as unknown as Node<'vec4'>
    }
    if (f.bloom) {
      const b = bloom(out, p.bloom.strength, p.bloom.radius, p.bloom.threshold)
      owned.push(b)
      out = out.add(b as unknown as Node<'vec4'>) as unknown as Node<'vec4'>
    }
    if (cinematic) {
      const d = dof(out, scenePass.getViewZNode(), focusU, float(0.25), float(1.2))
      owned.push(d as unknown as { dispose(): void })
      out = d as unknown as Node<'vec4'>
    }
    // tone map and encode first, then grade in display space (as the WebGL view's OutputPass + grade pass do)
    const g = p.grade
    const shown = renderOutput(out)
    const l = dot(shown.rgb, vec3(0.2126, 0.7152, 0.0722))
    let graded = mix(vec3(l), shown.rgb, float(g.saturation))
    graded = graded.sub(0.5).mul(g.contrast).add(0.5)
    graded = graded.add(vec3(g.warmth, g.warmth * 0.4, -g.warmth).mul(smoothstep(0.4, 1.0, l)))
    const d = length(uv().sub(0.5)).mul(1.4)
    graded = graded.mul(float(1).sub(float(g.vignette).mul(smoothstep(0.35, 0.85, d))))
    pipeline = new RenderPipeline(renderer)
    pipeline.outputColorTransform = false
    pipeline.outputNode = vec4(clamp(graded, 0, 1), 1)
    const key = scene.children.find((c) => (c as { isDirectionalLight?: boolean; castShadow?: boolean }).isDirectionalLight && (c as { castShadow: boolean }).castShadow) as
      | { shadow: { mapSize: { x: number; set(a: number, b: number): void }; map: { dispose(): void } | null } }
      | undefined
    if (key && key.shadow.mapSize.x !== f.shadowPx) {
      key.shadow.mapSize.set(f.shadowPx, f.shadowPx)
      key.shadow.map?.dispose()
      key.shadow.map = null
    }
  }

  return {
    backend: 'webgpu',
    renderer,
    environment,
    async init(s, c) {
      scene = s
      camera = c
      // the fur cards' edge fade (content.ts does it for WebGL with onBeforeCompile, which WebGPU ignores)
      s.traverse((o) => {
        const m = o as Mesh
        const mat = m.material as MeshPhysicalMaterial | undefined
        const fade = mat?.userData?.edgeFade as [number, number] | undefined
        if (!m.isMesh || !mat || !fade || !mat.map) return
        const n = new MeshPhysicalNodeMaterial()
        n.setValues({
          map: mat.map, normalMap: mat.normalMap, normalScale: mat.normalScale, aoMap: mat.aoMap, roughnessMap: mat.roughnessMap,
          roughness: mat.roughness, metalness: mat.metalness, clearcoat: mat.clearcoat, sheen: mat.sheen, sheenColor: mat.sheenColor,
          sheenRoughness: mat.sheenRoughness, envMapIntensity: mat.envMapIntensity, side: mat.side, vertexColors: mat.vertexColors,
          alphaTest: mat.alphaTest, alphaToCoverage: mat.alphaToCoverage,
        })
        const edge = float(1).sub(abs(dot(normalView, positionViewDirection)))
        n.opacityNode = texture(mat.map).a.mul(smoothstep(fade[0], fade[1], edge))
        m.material = n
      })
      build()
    },
    setSize(w, h, dpr) {
      size = { w, h, dpr }
      renderer.setPixelRatio(dpr)
      renderer.setSize(w, h, false)
    },
    setLevel(l) {
      if (l === level) return
      level = l
      build()
    },
    setCinematic(on, f) {
      focusU.value = f
      if (on !== cinematic) {
        cinematic = on
        build()
      }
    },
    render() {
      pipeline?.render()
      if (!resolving && renderer.hasFeature('timestamp-query')) {
        resolving = true
        renderer.resolveTimestampsAsync('render').then((ms) => {
          if (typeof ms === 'number' && ms > 0) lastGpu = ms
          resolving = false
        }, () => { resolving = false })
      }
    },
    gpuMs: () => lastGpu,
    targetBytes() {
      const f = levelFlags(level)
      const px = size.w * size.dpr * size.h * size.dpr
      const main = px * (8 * Math.max(1, f.msaa) + 8 + 8 * Math.max(1, f.msaa) + 4 * Math.max(1, f.msaa))
      const ao = f.ao ? px * (f.aoHalf ? 0.25 : 1) * 4 : 0
      const bl = f.bloom ? px * 8 * 0.66 : 0
      return Math.round(main + ao + bl + f.shadowPx * f.shadowPx * 4)
    },
    readPixels: () => (renderer.domElement as HTMLCanvasElement).toDataURL('image/png'),
    dispose() {
      pipeline?.dispose()
      for (const n of owned) n.dispose()
      environment.dispose()
      renderer.dispose()
    },
  }
}
