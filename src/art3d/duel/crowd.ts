import { Color, DoubleSide, DynamicDrawUsage, Group, InstancedMesh, MeshMatcapMaterial } from 'three'
import type { BufferGeometry, CanvasTexture, Scene } from 'three'
import { cheerLevel, cheerSeconds, cheerStart, planCrowd, type Cheer, type CheerKind, type Occupant, type Seat } from './crowdPlan.ts'
import { BODY, buildPartGeometries, crowdMatcap, triangles, type PartName } from './crowdParts.ts'
import { armRot, m3, mul3, place, poseOf, rotYXZ, writeHidden, writeMatrix } from './crowdPose.ts'
import { createCutouts, type Cutouts } from './cutouts.ts'
import { ART } from '../../data/tuning.ts'

const T = ART.duel.crowd

/**
 * docs/BATTLE_3D.md §8: the Guild arena's living crowd. The arena's benches are baked empty and its guild.json lists
 * every seat; Fame decides how many are filled (crowdPlan.ts), each person is a handful of instanced parts (one draw
 * per part, a colour per person), and a few seats hold painted cut-outs of the breeds (cutouts.ts). Every frame each
 * person bobs, sways, turns their head to the action and, when the battle gives them something, cheers.
 */

export interface CrowdOptions {
  /** The player's monster's Fame, 0–100. */
  fame: number
  lite: boolean
  reduceMotion: boolean
  seed: number
}

export interface CrowdStats {
  spots: number
  people: number
  cutouts: number
  draws: number
  triangles: number
  textureBytes: number
  /** The crowd's CPU time per frame (ms, smoothed). */
  cpuMs: number
}

export interface Crowd {
  /** `now` = seconds of the duel's clock; `focus` = where the action is (the fighters' midpoint). */
  update(dt: number, now: number, focus: { x: number; z: number }): void
  cheer(kind: CheerKind): void
  stats(): CrowdStats
  dispose(): void
}

const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

/** The arena's seats, checked (a bad entry is skipped, never a crash). */
export function readSeats(info: { seats?: unknown } | null): Seat[] {
  const raw = Array.isArray(info?.seats) ? (info!.seats as unknown[]) : []
  return raw.flatMap((s): Seat[] => {
    const r = s as Partial<Seat>
    if (!r || !Array.isArray(r.p) || r.p.length !== 3 || !r.p.every(finite) || !finite(r.yaw)) return []
    const kind = r.kind === 'ground' || r.kind === 'stand' ? r.kind : 'seat'
    return [{ p: [r.p[0]!, r.p[1]!, r.p[2]!], yaw: r.yaw, row: finite(r.row) ? r.row : 0, section: typeof r.section === 'string' ? r.section : 'front', kind, lite: r.lite !== false }]
  })
}

let parts: ReturnType<typeof buildPartGeometries> | null = null
let matcap: CanvasTexture | null = null
const DOUBLE: PartName[] = ['hat', 'scarf', 'pennant']

export async function createCrowd(scene: Scene, info: { seats?: unknown } | null, o: CrowdOptions): Promise<Crowd | null> {
  const seats = readSeats(info)
  if (!seats.length) return null
  const plan = planCrowd(seats, o)
  const people = plan.filter((p) => p.what === 'person')
  parts ??= buildPartGeometries()
  matcap ??= crowdMatcap(T.light)
  const front = new MeshMatcapMaterial({ matcap, vertexColors: true })
  const double = new MeshMatcapMaterial({ matcap, vertexColors: true, side: DoubleSide })
  const group = new Group()
  group.name = 'crowd'
  // instance slots: every person has a head and two arms; the rest only who needs them (seated people also get a
  // standing body, used only for the ovation, after the always-standing ones)
  const standing = people.filter((p) => p.pose === 'stand')
  const sitting = people.filter((p) => p.pose === 'sit')
  const slot = new Map<Occupant, Partial<Record<PartName, number>>>()
  const counts: Record<PartName, number> = { bodySit: 0, bodyStand: 0, head: 0, arm: 0, hair: 0, hat: 0, scarf: 0, pennant: 0, foam: 0 }
  const take = (p: Occupant, part: PartName) => ((slot.get(p) ?? slot.set(p, {}).get(p)!)[part] = counts[part]++)
  for (const p of standing) take(p, 'bodyStand')
  for (const p of sitting) take(p, 'bodyStand')
  for (const p of sitting) take(p, 'bodySit')
  for (const p of people) {
    take(p, 'head')
    take(p, 'arm')
    counts.arm++
    if (p.headwear !== 'none') take(p, p.headwear)
    if (p.scarf >= 0) take(p, 'scarf')
    if (p.held) take(p, p.held)
  }
  const meshes = {} as Record<PartName, InstancedMesh>
  const c = new Color()
  for (const name of Object.keys(counts) as PartName[]) {
    const n = counts[name]
    const m = new InstancedMesh(parts[name] as BufferGeometry, DOUBLE.includes(name) ? double : front, Math.max(1, n))
    m.name = `crowd_${name}`
    m.count = name === 'bodyStand' ? standing.length : n
    m.instanceMatrix.setUsage(DynamicDrawUsage)
    m.frustumCulled = false
    m.matrixAutoUpdate = false
    m.visible = n > 0
    meshes[name] = m
    group.add(m)
  }
  const P = T.palette
  const colour = (name: PartName, i: number | undefined, hex: string) => {
    if (i !== undefined) meshes[name].setColorAt(i, c.set(hex))
  }
  for (const p of people) {
    const s = slot.get(p)!
    const shirt = P.clothes[p.shirt]!
    colour('bodyStand', s.bodyStand, shirt)
    colour('bodySit', s.bodySit, shirt)
    colour('head', s.head, P.skin[p.skin]!)
    meshes.arm.setColorAt(s.arm!, c.set(P.skin[p.skin]!))
    meshes.arm.setColorAt(s.arm! + 1, c)
    colour('hair', s.hair, P.hair[p.hair]!)
    colour('hat', s.hat, P.hats[p.hat]!)
    colour('scarf', s.scarf, P.accents[Math.max(0, p.scarf)]!)
    if (p.held) colour(p.held, s[p.held], P.accents[p.heldColour]!)
  }
  for (const m of Object.values(meshes)) if (m.instanceColor) m.instanceColor.needsUpdate = true
  const cutouts: Cutouts | null = await createCutouts(plan.filter((p) => p.what === 'cutout'), o.seed)
  if (cutouts) group.add(cutouts.mesh)
  scene.add(group)

  // live cheers, each with the moment it reaches every occupant (NaN: sitting it out), worked out once when it starts
  const cheers: { c: Cheer; starts: Float64Array }[] = []
  const indexOf = new Map(plan.map((p, i) => [p, i]))
  const personAt = people.map((p) => indexOf.get(p)!)
  let ovationNow = 0
  /** Excitement of occupant `i` of the plan now (the ovation's share is left in ovationNow). */
  const excite = (i: number, now: number): number => {
    let e = 0
    ovationNow = 0
    for (const { c, starts } of cheers) {
      const v = cheerLevel(c.kind, starts[i] ?? Number.NaN, now)
      if (v > e) e = v
      if (c.kind === 'ovation' && v > ovationNow) ovationNow = v
    }
    return e
  }
  let nextId = 0
  let focusAngle = 0
  let lastNow = 0
  let cpuMs = 0
  const headYaw = new Float32Array(people.length)
  const Rb = m3(), Rh = m3(), Ra = m3(), tmp = m3()
  const root = new Float64Array(3), at = new Float64Array(3)
  const arr = (name: PartName) => meshes[name].instanceMatrix.array as Float32Array
  const bodySit = arr('bodySit'), bodyStand = arr('bodyStand'), head = arr('head'), arm = arr('arm'), hair = arr('hair'), hat = arr('hat'), scarf = arr('scarf'), pennant = arr('pennant'), foam = arr('foam')
  const maxTurn = (T.look.maxDeg * Math.PI) / 180

  function update(dt: number, now: number, focus: { x: number; z: number }): void {
    const t0 = performance.now()
    lastNow = now
    focusAngle = Math.atan2(focus.x, focus.z)
    for (let i = cheers.length - 1; i >= 0; i--) if (now - cheers[i]!.c.at > cheerSeconds(cheers[i]!.c.kind) + 4) cheers.splice(i, 1)
    let anyStanding = false
    let anySitting = false
    for (let i = 0; i < people.length; i++) {
      const p = people[i]!
      const s = slot.get(p)!
      const e = excite(personAt[i]!, now)
      const pose = poseOf(p, now, e, ovationNow, o.reduceMotion, o.seed)
      const up = p.pose === 'stand' || pose.standing
      if (pose.standing) anyStanding = true
      else if (p.pose === 'sit') anySitting = true
      // the head turns toward the action, each at their own pace, as far as a neck goes
      let want = Math.atan2(focus.x - p.x, focus.z - p.z) - p.yaw
      want = Math.atan2(Math.sin(want), Math.cos(want))
      want = Math.max(-maxTurn, Math.min(maxTurn, want))
      headYaw[i]! += (want - headYaw[i]!) * Math.min(1, dt * T.look.rate * (0.6 + 0.8 * p.phase))
      const sc = p.height
      const w = p.width * sc
      const back = up ? 0 : 0.03
      root[0] = p.x - Math.sin(p.yaw) * back
      root[1] = p.y + pose.lift
      root[2] = p.z - Math.cos(p.yaw) * back
      rotYXZ(Rb, p.yaw, pose.lean, pose.roll)
      const lift = up ? (BODY.hipStand - 0.02) * sc : 0
      if (s.bodySit !== undefined) (up ? writeHidden(bodySit, s.bodySit) : writeMatrix(bodySit, s.bodySit, Rb, w, sc, w, root[0]!, root[1]!, root[2]!))
      if (up) writeMatrix(bodyStand, s.bodyStand!, Rb, w, sc, w, root[0]!, root[1]!, root[2]!)
      else writeHidden(bodyStand, s.bodyStand!)
      // the head (kids' heads are bigger for their size), its hair or hat
      const hk = p.kid ? 1.22 : 1
      place(at, Rb, root, 0, lift + BODY.headY * sc + BODY.headR * sc * (hk - 1) * 0.8, 0)
      mul3(Rh, Rb, rotYXZ(tmp, headYaw[i]!, pose.nod, 0))
      const hs = sc * hk
      writeMatrix(head, s.head!, Rh, hs, hs, hs, at[0]!, at[1]!, at[2]!)
      if (s.hair !== undefined) {
        const v = hs * (1 + 0.14 * ((p.phase * 7.3) % 1))
        writeMatrix(hair, s.hair, Rh, v, v, v, at[0]!, at[1]!, at[2]!)
      }
      if (s.hat !== undefined) writeMatrix(hat, s.hat, Rh, hs, hs, hs, at[0]!, at[1]!, at[2]!)
      if (s.scarf !== undefined) {
        place(at, Rb, root, 0, lift, 0)
        writeMatrix(scarf, s.scarf, Rb, w, sc, w, at[0]!, at[1]!, at[2]!)
      }
      // arms from the shoulders; a pennant or foam hand rides the right one
      for (const side of [1, -1]) {
        place(at, Rb, root, side * BODY.shoulderX * w, lift + BODY.shoulderY * sc, 0)
        mul3(Ra, Rb, armRot(tmp, side > 0 ? pose.leftRaise : pose.rightRaise, side > 0 ? pose.leftSpread : pose.rightSpread))
        writeMatrix(arm, s.arm! + (side > 0 ? 0 : 1), Ra, sc, sc, sc, at[0]!, at[1]!, at[2]!)
        if (side < 0 && p.held) writeMatrix(p.held === 'pennant' ? pennant : foam, s[p.held]!, Ra, sc, sc, sc, at[0]!, at[1]!, at[2]!)
      }
    }
    // the ovation's standing bodies are drawn only while someone stands, the seated ones while someone sits
    meshes.bodyStand.count = anyStanding ? counts.bodyStand : standing.length
    meshes.bodySit.count = anySitting ? counts.bodySit : 0
    for (const m of Object.values(meshes)) m.instanceMatrix.needsUpdate = true
    cutouts?.update(now, (p) => excite(indexOf.get(p) ?? -1, now), o.reduceMotion)
    cpuMs += (performance.now() - t0 - cpuMs) * 0.1
  }

  return {
    update,
    cheer(kind) {
      const c: Cheer = { kind, at: lastNow, from: focusAngle, id: nextId++ }
      cheers.push({ c, starts: Float64Array.from(plan, (p) => cheerStart(c, p, o.seed)) })
      if (cheers.length > T.maxCheers) cheers.shift()
    },
    stats() {
      let tris = cutouts?.triangles ?? 0
      let draws = cutouts ? 1 : 0
      for (const [name, m] of Object.entries(meshes) as [PartName, InstancedMesh][]) {
        if (!m.visible || m.count === 0) continue
        draws++
        tris += triangles(parts![name]) * m.count
      }
      const tex = (matcap?.image as HTMLCanvasElement | undefined)?.width ?? 0
      return { spots: o.lite ? seats.filter((s) => s.lite).length : seats.length, people: people.length, cutouts: cutouts?.count ?? 0, draws, triangles: tris, textureBytes: tex * tex * 4 + (cutouts?.bytes ?? 0), cpuMs }
    },
    dispose() {
      scene.remove(group)
      for (const m of Object.values(meshes)) m.dispose()
      front.dispose()
      double.dispose()
      cutouts?.dispose()
    },
  }
}
