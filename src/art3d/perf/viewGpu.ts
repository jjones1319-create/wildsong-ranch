import { MeshPhysicalNodeMaterial, NeutralToneMapping, PCFSoftShadowMap, PMREMGenerator, RenderPipeline, SRGBColorSpace, WebGPURenderer } from 'three/webgpu'
import type { Mesh, MeshPhysicalMaterial, Node, Object3D, PerspectiveCamera, Scene, Texture } from 'three/webgpu'
import { abs, color, diffuseColor, float, floor, fract, materialSheen, max, min, mix, mrt, normalView, output, pass, positionViewDirection, renderOutput, sin, smoothstep, texture, time, uniform, uv, vec2, vec3, vec4, vertexColor, dot, length, clamp } from 'three/tsl'
import { ao } from 'three/addons/tsl/display/GTAONode.js'
import { bloom } from 'three/addons/tsl/display/BloomNode.js'
import { dof } from 'three/addons/tsl/display/DepthOfFieldNode.js'
import { ART } from '../../data/tuning.ts'
import { FILM_TWINKLE, roomEnvironmentScene, type FilmGlow } from './content.ts'
import { levelFlags, setCoverage, type Level, type PerfView, type ViewOptions } from './view.ts'

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
  // the glow's twinkle amplitude (content.ts FILM_TWINKLE: 0 with Reduce motion), read each frame
  const twinkleU = uniform(FILM_TWINKLE.value)
  let scene: Scene | null = null
  let camera: PerspectiveCamera | null = null
  // the AO pre-pass's camera: the main one without the fur cards' layer (their alpha-tested quads, drawn without
  // coverage there, put stair-steps along the outline; content.ts / ultraAsset.ts put the cards on layer 1)
  let aoCamera: PerspectiveCamera | null = null
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
    setCoverage(scene, f.msaa)
    const scenePass = pass(scene, camera, { samples: f.msaa })
    owned.push(scenePass)
    const color = scenePass.getTextureNode('output')
    // TSL's generic node types don't follow a chain of effects; the graph is checked when the pipeline compiles
    // the film materials' ceiling (content.ts): a near-mirror's highlight can overflow the half-float target, and the
    // bloom would spread that infinite pixel over the frame
    let out = vec4(min(color.rgb, vec3(ART.ultra.film.hdrMax)), color.a) as unknown as Node<'vec4'>
    if (f.ao) {
      // GTAO can't read a multisampled depth buffer: a plain depth + normal pre-pass feeds it (as the WebGL GTAO pass does)
      aoCamera = camera.clone()
      aoCamera.layers.disable(1)
      const prePass = pass(scene, aoCamera, { samples: 0 })
      prePass.setMRT(mrt({ output: normalView }))
      const aoPass = ao(prePass.getTextureNode('depth'), prePass.getTextureNode(), aoCamera)
      owned.push(prePass, aoPass)
      aoPass.resolutionScale = f.aoHalf ? 0.5 : 1
      aoPass.radius.value = p.aoRadius
      aoPass.samples.value = 12
      // never darker than post.aoFloor: the monsters bake their own soft AO (deep creases went near-black)
      const occ = max(mix(float(1), aoPass.getTextureNode().r, float(p.aoIntensity)), float(p.aoFloor))
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

  /**
   * The film materials' shader rules (content.ts patches them into WebGL's shaders with onBeforeCompile, which WebGPU
   * ignores), rebuilt as node materials: the fur cards' edge fade, the glow (the ORM map's alpha, twinkling), and the
   * brightness cap on the lit surface (only glow blooms) under the half-float ceiling.
   */
  function prepare(root: Object3D): void {
    const G = ART.ultra.film.glow
    root.traverse((o) => {
      const m = o as Mesh
      const mat = m.material as MeshPhysicalMaterial | undefined
      if (!m.isMesh || !mat || (mat as { isNodeMaterial?: boolean }).isNodeMaterial) return
      const fade = mat.userData?.edgeFade as [number, number] | undefined
      const cap = mat.userData?.maxLum as number | undefined
      const glow = mat.userData?.glow as FilmGlow | undefined
      const coat = mat.userData?.coatMask as { gain: number; max: number } | undefined
      if ((!fade && cap === undefined && !glow && !coat) || !mat.map) return
      const n = new MeshPhysicalNodeMaterial()
      n.setValues({
        map: mat.map, normalMap: mat.normalMap, normalScale: mat.normalScale, aoMap: mat.aoMap, roughnessMap: mat.roughnessMap,
        roughness: mat.roughness, metalness: mat.metalness, clearcoat: mat.clearcoat, clearcoatRoughness: mat.clearcoatRoughness,
        sheen: mat.sheen, sheenColor: mat.sheenColor, sheenColorMap: mat.sheenColorMap, sheenRoughness: mat.sheenRoughness, envMapIntensity: mat.envMapIntensity,
        specularIntensity: mat.specularIntensity, emissive: mat.emissive, emissiveMap: mat.emissiveMap, emissiveIntensity: mat.emissiveIntensity,
        side: mat.side, vertexColors: mat.vertexColors, alphaTest: mat.alphaTest, alphaToCoverage: mat.alphaToCoverage,
      })
      if (mat.userData?.sheenByVertex && mat.sheen > 0) {
        // cards and the tuft: the sheen in the strand's own colour, the vertex colour over the strip tile (content.ts)
        n.sheenNode = materialSheen.mul(vertexColor().rgb) as unknown as Node<'vec3'>
      }
      if (coat && mat.roughnessMap) {
        // the clearcoat per texel: the ORM map's B channel (content.ts)
        n.clearcoatNode = clamp(texture(mat.roughnessMap).b.mul(coat.gain), 0, coat.max)
      }
      // the fur cards' opacity: the strand's alpha after the edge fade, plain (cut at alphaTest without MSAA) or as a
      // soft coverage ramp with MSAA (setCoverage swaps them: the built-in coverage would cut it hard at alphaTest)
      let opacityRaw: Node<'float'> | null = null
      let opacityRamp: Node<'float'> | null = null
      if (fade) {
        const edge = float(1).sub(abs(dot(normalView, positionViewDirection)))
        opacityRaw = texture(mat.map).a.mul(smoothstep(fade[0], fade[1], edge)) as unknown as Node<'float'>
        const ramp = (mat.userData?.coverageRamp as [number, number] | undefined) ?? [0, 1]
        opacityRamp = smoothstep(ramp[0], ramp[1], opacityRaw) as unknown as Node<'float'>
        n.opacityNode = opacityRaw
      }
      // TSL's generic node types don't follow these chains; the graph is checked when the material compiles
      let glowNode: Node<'vec3'> | null = null
      if (glow && mat.roughnessMap) {
        // the ORM map's alpha, on the base colour or the tint, twinkling slowly with a phase per texel cell
        const phase = fract(sin(dot(floor(uv().mul(G.cells)), vec2(12.9898, 78.233))).mul(43758.5453)).mul(6.2831853)
        const twinkle = float(1).add(twinkleU.mul(sin(time.mul(G.twinkleHz * 2 * Math.PI).add(phase))))
        const tint = glow.tint ? vec3(glow.tint[0], glow.tint[1], glow.tint[2]) : diffuseColor.rgb
        glowNode = tint.mul(texture(mat.roughnessMap).a).mul(glow.strength).mul(twinkle) as unknown as Node<'vec3'>
        // the material's own emissive (a fin's faint translucency) plus the glow
        const own = mat.emissiveMap ? texture(mat.emissiveMap).rgb.mul(color(mat.emissive).mul(mat.emissiveIntensity)) : color(mat.emissive).mul(mat.emissiveIntensity)
        n.emissiveNode = own.add(glowNode) as unknown as Node<'vec3'>
      }
      if (cap !== undefined) {
        // the lit surface capped below the bloom threshold (hue kept), the glow added back, all under the ceiling
        const g = glowNode ?? vec3(0)
        const lit = max(output.rgb.sub(g), vec3(0))
        const lum = dot(lit, vec3(0.2126, 0.7152, 0.0722))
        const capped = lit.mul(min(float(1), float(cap).div(max(lum, float(1e-4)))))
        n.outputNode = vec4(min(capped.add(g), vec3(ART.ultra.film.hdrMax)), output.a)
      }
      n.userData = { ...mat.userData, opacityRaw, opacityRamp, coverageOn: undefined }
      m.material = n
      mat.dispose()
    })
    setCoverage(root, levelFlags(level).msaa)
  }

  return {
    backend: 'webgpu',
    renderer,
    environment,
    async init(s, c) {
      scene = s
      camera = c
      prepare(s)
      build()
    },
    prepare,
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
      if (aoCamera && camera) aoCamera.copy(camera, false).layers.disable(1)
      twinkleU.value = FILM_TWINKLE.value
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
