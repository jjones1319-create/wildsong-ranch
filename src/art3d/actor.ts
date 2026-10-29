import { AnimationClip, AnimationMixer, Bone, Color, Euler, Group, LoopOnce, LoopRepeat, Quaternion, ShaderMaterial, SkinnedMesh, Vector3, Vector4, type AnimationAction, type Matrix4 } from 'three'
import { MODEL_LOOKS } from '../art/models.ts'
import { variantPalette } from '../art/monster/variants.ts'
import { sizePct } from '../core/monster.ts'
import { ART, STAGES } from '../data/tuning.ts'
import { BlinkClock, DriftClock, glanceToward, layerCells, pupilScale, settle, type Glance, type Layer } from './faceCells.ts'
import { instantiate, type LookAsset, type LookInstance } from './loader.ts'
import { applyLight, makeFaceMaterial, makeOutlineMaterial, makeToonMaterial, outlineColorFor, type LightRig } from './materials.ts'
import { AccelTracker, ChainSpring, springParams } from './springs.ts'
import type { ClipName, FaceName } from './types.ts'

/**
 * One monster on a stage (ART_2_PLAN §3.2): the model instance with the toon and outline materials, the clip
 * player (cross-fades, markers, face cues), the face controller (expressions, blinks, glances) and the springs
 * on ears and tails. The stage owns the renderer and calls `update` once per frame.
 */

export interface ActorQuality {
  outline: boolean
  springs: boolean
  outlinePx: number
}

export interface PlayOptions {
  /** Cross-fade in ms (ART.anim.crossFadeMs by default). */
  fade?: number
  rate?: number
  restart?: boolean
  onFinish?: () => void
}

export interface ActorEvents {
  onMarker?: (clip: ClipName, marker: string) => void
}

export interface ActorInit {
  quality: ActorQuality
  variant: string | null
  stage: number
  face: FaceName
  rng: () => number
  events?: ActorEvents
}

const tmpQ = new Quaternion()
const tmpE = new Euler()
const tmpV = new Vector3()

/** Which way the pupils slide for a positive glance in patch space (set from the Lab if the patches run the other way). */
const GLANCE_U_SIGN = 1
const GLANCE_V_SIGN = -1

export class Actor {
  readonly root = new Group()
  readonly inst: LookInstance
  readonly asset: LookAsset
  readonly mixer: AnimationMixer
  readonly events: ActorEvents
  clipName: ClipName | null = null
  baseFace: FaceName = 'neutral'
  variant: string | null = null
  stage = 5
  /** Arena units per model metre at the current stage. */
  unitsPerMetre = 1

  private readonly clips = new Map<string, AnimationClip>()
  private action: AnimationAction | null = null
  private onFinish: (() => void) | null = null
  private prevT = 0
  private clipFace: FaceName | null = null
  private readonly toon: ShaderMaterial
  private outlineMat: ShaderMaterial | null = null
  private readonly faceMats = new Map<Layer, ShaderMaterial>()
  private readonly blink: BlinkClock
  private readonly drift: DriftClock
  private blinkPhase: 0 | 1 | 2 = 0
  private glance: Glance = { x: 0, y: 0, yaw: 0, pitch: 0 }
  private glanceHold = 0
  private readonly springs: { chain: ChainSpring; bones: Bone[]; driver: Bone; tracker: AccelTracker }[] = []
  private facesDirty = true
  private lastFace: FaceName | null = null
  private flash = 0

  constructor(asset: LookAsset, init: ActorInit) {
    this.asset = asset
    this.events = init.events ?? {}
    this.inst = instantiate(asset)
    this.root.add(this.inst.root)
    this.mixer = new AnimationMixer(this.inst.root)
    for (const c of asset.animations) this.clips.set(c.name, c)
    const baseMap = asset.textures.get('base')!
    this.toon = makeToonMaterial(baseMap)
    const body = this.inst.body
    body.material = this.toon
    body.frustumCulled = false
    body.castShadow = true
    if (init.quality.outline && init.quality.outlinePx > 0) {
      this.outlineMat = makeOutlineMaterial(asset.meta.palette.body ?? '#3fb6a8', init.quality.outlinePx)
      const o = new SkinnedMesh(body.geometry, this.outlineMat)
      o.bindMode = body.bindMode
      o.bind(body.skeleton, body.bindMatrix)
      o.frustumCulled = false
      o.name = 'outline'
      body.add(o)
    }
    const sheet = asset.faceSheet
    for (const [layer, mesh] of this.inst.faces) {
      const kind = layer.split('.')[0] as 'white' | 'pupil' | 'lid' | 'mouth'
      if (!sheet) {
        mesh.visible = false
        continue
      }
      const mat = makeFaceMaterial(sheet, kind, asset.meta.face.eyeColor)
      mesh.material = mat
      mesh.renderOrder = 2
      mesh.frustumCulled = false
      this.faceMats.set(layer as Layer, mat)
    }
    this.blink = new BlinkClock(init.rng)
    this.drift = new DriftClock(init.rng)
    if (init.quality.springs) {
      for (const s of asset.meta.springs) {
        const bones = s.chain.map((n) => this.inst.bones.get(n)).filter((b): b is Bone => !!b)
        const driver = bones[0]?.parent as Bone | undefined
        if (!bones.length || !driver || !(driver as Bone).isBone) continue
        this.springs.push({ chain: new ChainSpring(bones.length, springParams(s.kind)), bones, driver, tracker: new AccelTracker() })
      }
    }
    this.mixer.addEventListener('finished', (e) => {
      if ((e as { action: AnimationAction }).action === this.action) this.onFinish?.()
    })
    this.setVariant(init.variant)
    this.setStage(init.stage)
    this.setFace(init.face)
  }

  // ------------------------------------------------------------------ looks
  setVariant(id: string | null): void {
    const tex = (id && this.asset.textures.get(id)) || this.asset.textures.get('base')!
    this.variant = id && this.asset.textures.has(id) ? id : null
    this.toon.uniforms.map!.value = tex
    if (this.outlineMat) {
      const body = (this.variant && variantPalette(this.variant)?.body) || this.asset.meta.palette.body || '#3fb6a8'
      ;(this.outlineMat.uniforms.outlineColor!.value as Color).copy(outlineColorFor(body))
    }
    const eye = (this.variant && this.asset.meta.variants[this.variant]?.eyeColor) || this.asset.meta.face.eyeColor
    for (const [layer, m] of this.faceMats) {
      if (!layer.startsWith('pupil')) continue
      ;(m.uniforms.irisColor!.value as Color).set(eye)
      ;(m.uniforms.pupilColor!.value as Color).set(eye).multiplyScalar(0.45)
    }
  }

  setStage(stage: number): void {
    this.stage = stage
    const k = MODEL_LOOKS[this.asset.id as keyof typeof MODEL_LOOKS].unitsPerMetre * (sizePct(stage) / 100)
    this.unitsPerMetre = k
    this.root.scale.setScalar(k)
    this.toon.uniforms.oldMix!.value = stage >= STAGES.visiblyOld ? ART.toon.oldMix : 0
    // babies lean chibi (§2.1): the head bone grows a little, and the ears and face come with it
    const head = this.inst.bones.get(this.asset.meta.bones.head)
    if (head) {
      const hs = stage <= STAGES.sizePct.smallUntil ? ART.stage.headScale.small : stage <= STAGES.sizePct.mediumUntil ? ART.stage.headScale.medium : 1
      head.scale.setScalar(hs)
    }
  }

  setFace(face: FaceName): void {
    if (this.baseFace === face) return
    this.baseFace = face
    this.facesDirty = true
  }

  setSick(k: number): void {
    this.toon.uniforms.sickMix!.value = k * ART.toon.sickMix
  }

  setFlash(k: number): void {
    if (k === this.flash) return
    this.flash = k
    this.toon.uniforms.flash!.value = k
    for (const m of this.faceMats.values()) m.uniforms.flash!.value = k
  }

  setOpacity(k: number): void {
    this.toon.uniforms.opacity!.value = k
    this.toon.transparent = k < 1
    if (this.outlineMat) {
      this.outlineMat.uniforms.opacity!.value = k
      this.outlineMat.transparent = k < 1
    }
    for (const m of this.faceMats.values()) m.uniforms.opacity!.value = k
  }

  setResolution(w: number, h: number): void {
    if (this.outlineMat) (this.outlineMat.uniforms.resolution!.value as { set: (x: number, y: number) => void }).set(w, h)
  }

  applyLight(rig: LightRig, viewMatrix: Matrix4): void {
    applyLight(this.toon, rig, viewMatrix)
    for (const m of this.faceMats.values()) applyLight(m, rig, viewMatrix)
  }

  /** Where the monster stands (arena units) and which way it faces (yaw in degrees; 0 faces the camera). */
  place(x: number, z: number, yawDeg: number): void {
    this.root.position.set(x, 0, z)
    this.root.rotation.y = (yawDeg * Math.PI) / 180
  }

  /** The root bone's height above the ground in arena units (for the contact shadow). */
  rootHeight(): number {
    const hips = this.inst.bones.get(this.asset.meta.bones.hips)
    if (!hips) return 0
    hips.getWorldPosition(tmpV)
    const rest = (this.asset.meta.bounds.max[1] ?? 1) * 0.42 * this.unitsPerMetre
    return Math.max(0, tmpV.y - this.root.position.y - rest)
  }

  // ------------------------------------------------------------------ clips
  hasClip(name: string): boolean {
    return this.clips.has(name)
  }

  play(name: ClipName, o: PlayOptions = {}): boolean {
    const clip = this.clips.get(name)
    if (!clip) return false
    const meta = this.asset.meta.clips[name]
    if (this.clipName === name && this.action && !o.restart) {
      if (o.rate !== undefined) this.action.timeScale = o.rate
      if (o.onFinish) this.onFinish = o.onFinish
      return true
    }
    const next = this.mixer.clipAction(clip)
    const prev = this.action
    next.reset()
    next.enabled = true
    next.setLoop(meta?.loop === false ? LoopOnce : LoopRepeat, Infinity)
    next.clampWhenFinished = !!meta?.hold
    next.timeScale = o.rate ?? 1
    next.setEffectiveWeight(1)
    next.play()
    const fade = (o.fade ?? ART.anim.crossFadeMs) / 1000
    if (prev && prev !== next) {
      if (fade > 0) next.crossFadeFrom(prev, fade, false)
      else prev.stop()
    }
    this.action = next
    this.clipName = name
    this.clipFace = null
    this.prevT = 0
    this.onFinish = o.onFinish ?? null
    this.facesDirty = true
    return true
  }

  setRate(rate: number): void {
    if (this.action) this.action.timeScale = rate
  }

  /** Jump the current clip to a time (seconds); for stills and the Lab's scrubber. */
  seek(t: number): void {
    if (!this.action) return
    this.action.time = t
    this.mixer.update(0)
  }

  // ------------------------------------------------------------------ faces
  glanceToward(dx: number, dy: number, reach: number): void {
    this.glance = glanceToward(dx, dy, reach)
    this.glanceHold = ART.face.holdMs
  }

  private effectiveFace(): FaceName {
    return this.clipFace ?? this.baseFace
  }

  private pushFaceCells(): void {
    const face = this.effectiveFace()
    const cells = layerCells(this.asset.meta.face, { face, blink: this.blinkPhase })
    const ps = pupilScale(this.asset.meta.face, face)
    for (const [layer, m] of this.faceMats) {
      const c = cells[layer]
      const mesh = this.inst.faces.get(layer)
      if (!c) {
        if (mesh) mesh.visible = false
        continue
      }
      if (mesh) mesh.visible = true
      ;(m.uniforms.cell!.value as Vector4).set(c.u0, c.v0, c.w, c.h)
      m.uniforms.mirror!.value = c.mirror ? 1 : 0
      m.uniforms.pupilScale!.value = ps
    }
    this.lastFace = face
  }

  // ------------------------------------------------------------------ per frame
  update(dtMs: number, animate = true): void {
    const dt = dtMs / 1000
    if (animate) {
      this.mixer.update(dt)
      this.fireMarkers()
    }
    // blinks and glances
    const phase = animate ? this.blink.step(dtMs) : 0
    if (phase !== this.blinkPhase) {
      this.blinkPhase = phase
      this.facesDirty = true
    }
    if (this.facesDirty || this.lastFace !== this.effectiveFace()) {
      this.pushFaceCells()
      this.facesDirty = false
    }
    if (animate) {
      if (this.glanceHold > 0) this.glanceHold -= dtMs
      else {
        this.glance.x = settle(this.glance.x, dtMs)
        this.glance.y = settle(this.glance.y, dtMs)
        this.glance.yaw = settle(this.glance.yaw, dtMs)
        this.glance.pitch = settle(this.glance.pitch, dtMs)
      }
      const d = this.drift.step(dtMs)
      const px = (this.glance.x + d.x) * GLANCE_U_SIGN
      const py = (this.glance.y + d.y) * GLANCE_V_SIGN
      for (const [layer, m] of this.faceMats) {
        if (!layer.startsWith('pupil')) continue
        const mirror = (m.uniforms.mirror!.value as number) > 0.5
        ;(m.uniforms.pupilOffset!.value as { set: (x: number, y: number) => void }).set(mirror ? -px : px, py)
      }
      const head = this.inst.bones.get(this.asset.meta.bones.head)
      if (head && (this.glance.yaw !== 0 || this.glance.pitch !== 0)) {
        tmpE.set((this.glance.pitch * Math.PI) / 180, (this.glance.yaw * Math.PI) / 180, 0, 'XYZ')
        head.quaternion.multiply(tmpQ.setFromEuler(tmpE))
      }
      this.updateSprings(dt)
    }
  }

  private fireMarkers(): void {
    const a = this.action
    const name = this.clipName
    if (!a || !name) return
    const meta = this.asset.meta.clips[name]
    if (!meta) return
    const t = a.time
    const prev = this.prevT
    this.prevT = t
    const crossed = (mt: number) => (t >= prev ? mt > prev && mt <= t : mt > prev || mt <= t)
    for (const m of meta.markers) if (crossed(m.t)) this.events.onMarker?.(name, m.name)
    for (const f of meta.faces) {
      if (crossed(f.t)) {
        const face = f.face === 'neutral' ? null : (f.face as FaceName)
        if (face !== this.clipFace) {
          this.clipFace = face
          this.facesDirty = true
        }
      }
    }
  }

  private updateSprings(dt: number): void {
    if (!this.springs.length || dt <= 0) return
    const k = 1 / Math.max(1e-6, this.unitsPerMetre)
    for (const s of this.springs) {
      s.driver.updateWorldMatrix(true, false)
      s.driver.getWorldPosition(tmpV)
      const a = s.tracker.push([tmpV.x * k, tmpV.y * k, tmpV.z * k], dt)
      // project the parent's acceleration onto the first bone's swing axes (local Z → pitch, local X → yaw)
      const b0 = s.bones[0]!
      b0.updateWorldMatrix(true, false)
      const m = b0.matrixWorld
      const zx = m.elements[8]!, zy = m.elements[9]!, zz = m.elements[10]!
      const xx = m.elements[0]!, xy = m.elements[1]!, xz = m.elements[2]!
      const lz = Math.hypot(zx, zy, zz) || 1
      const lx = Math.hypot(xx, xy, xz) || 1
      const pushPitch = (a[0] * zx + a[1] * zy + a[2] * zz) / lz
      const pushYaw = -(a[0] * xx + a[1] * xy + a[2] * xz) / lx
      const states = s.chain.update(pushPitch, pushYaw, dt)
      for (let i = 0; i < s.bones.length; i++) {
        const st = states[i]!
        tmpE.set(st.x, 0, st.y, 'XYZ')
        s.bones[i]!.quaternion.multiply(tmpQ.setFromEuler(tmpE))
      }
    }
  }

  dispose(): void {
    this.mixer.stopAllAction()
    this.toon.dispose()
    this.outlineMat?.dispose()
    for (const m of this.faceMats.values()) {
      const t = m.uniforms.sheet?.value as { dispose?: () => void } | undefined
      if (m.uniforms.isPupil?.value === 1) t?.dispose?.()
      m.dispose()
    }
    this.root.removeFromParent()
  }
}
