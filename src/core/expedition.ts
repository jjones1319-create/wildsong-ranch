import { EXPEDITION_SITES, EXPEDITION_SITE_BY_ID } from '../data/expeditions.ts'
import { ITEM_BY_ID, grandSweetFor } from '../data/items.ts'
import { UNIVERSAL_TECHNIQUES } from '../data/techniques.ts'
import { EXPEDITION, UNLOCKS } from '../data/tuning.ts'
import { STAT_KEYS, TOURNAMENT_GRADES, type ExpeditionSite, type ExpeditionSiteId, type LootEntry, type NodeKind } from '../data/types.ts'
import { availability } from './aging.ts'
import { dateOf } from './calendar.ts'
import { placeNewMonster } from './creation.ts'
import { addItems, countOf } from './items.ts'
import { addCondition, createMonster, rollLikes, type Monster } from './monster.ts'
import { createRng, type Rng } from './rng.ts'
import { addSheet } from './songbook.ts'
import type { ExpeditionEnd, ExpeditionLoot, ExpeditionState, GameState } from './state.ts'

/**
 * GAME_DESIGN §17 expeditions. The map is a forward-only layered graph rebuilt from (site, seed): a trailhead,
 * four or five layers of two or three stops, and the camp. One route, the "spine", runs from the trailhead
 * through the site's event node to the camp; it only carries obstacles at the site's stated thresholds, never
 * fog, and its steps cost at most the base stamina together. That is the §17 promise: a monster that meets the
 * letter's thresholds can always reach the key item. Everything here is pure; live rolls use the injected RNG.
 */

export interface MapEdge {
  to: number
  cost: number
}

export interface MapNode {
  id: number
  /** 0 = the trailhead, layers + 1 = the camp. */
  layer: number
  /** Position inside the layer. */
  index: number
  kind: NodeKind
  /** For obstacles: an index into the site's obstacle list. */
  obstacle: number | null
  next: MapEdge[]
  spine: boolean
}

export interface ExpeditionMap {
  site: ExpeditionSiteId
  seed: number
  nodes: MapNode[]
  /** The middle layers (the trailhead and the camp are extra). */
  layers: number
  start: number
  camp: number
  event: number
  /** The guaranteed route, trailhead to event node. */
  spine: number[]
}

const NODE_KIND_LIST = ['path', 'obstacle', 'search', 'hidden', 'fog', 'treasure'] as const
const SPINE_KIND_LIST = ['path', 'obstacle', 'search', 'treasure'] as const

export function buildMap(siteId: ExpeditionSiteId, seed: number): ExpeditionMap {
  const site = EXPEDITION_SITE_BY_ID[siteId]
  const rng = createRng(seed)
  const cfg = EXPEDITION.map

  // 1. Layer sizes, nudged until the whole map has 12–16 stops.
  const layers = rng.nextInt(cfg.layers.min, cfg.layers.max)
  const sizes = Array.from({ length: layers }, () => rng.nextInt(cfg.perLayer.min, cfg.perLayer.max))
  const total = () => sizes.reduce((a, b) => a + b, 0) + 2
  while (total() < cfg.nodes.min) {
    const cands = sizes.map((_, i) => i).filter((i) => sizes[i]! < cfg.perLayer.max)
    sizes[rng.pick(cands)]! += 1
  }
  while (total() > cfg.nodes.max) {
    const cands = sizes.map((_, i) => i).filter((i) => sizes[i]! > cfg.perLayer.min)
    sizes[rng.pick(cands)]! -= 1
  }

  // 2. Nodes by layer.
  const nodes: MapNode[] = []
  const byLayer: number[][] = []
  const add = (layer: number, index: number, kind: NodeKind): number => {
    nodes.push({ id: nodes.length, layer, index, kind, obstacle: null, next: [], spine: false })
    return nodes.length - 1
  }
  const start = add(0, 0, 'start')
  byLayer.push([start])
  for (let l = 1; l <= layers; l++) {
    const ids: number[] = []
    for (let i = 0; i < sizes[l - 1]!; i++) ids.push(add(l, i, 'path'))
    byLayer.push(ids)
  }
  const camp = add(layers + 1, 0, 'camp')
  byLayer.push([camp])

  // 3. The spine: one stop per layer, ending at the event node just before the camp.
  const spine: number[] = [start]
  for (let l = 1; l <= layers; l++) spine.push(rng.pick(byLayer[l]!))
  const event = spine[layers]!
  for (const id of spine) nodes[id]!.spine = true
  nodes[event]!.kind = 'event'

  // 4. Edges: every stop reaches the next layer's spine stop (so the camp and the event are always reachable),
  //    plus a second link half the time; every stop gets at least one way in.
  const link = (from: number, to: number) => {
    if (nodes[from]!.next.some((e) => e.to === to)) return
    nodes[from]!.next.push({ to, cost: rng.nextInt(EXPEDITION.stepCost.min, EXPEDITION.stepCost.max) })
  }
  for (let l = 0; l <= layers; l++) {
    const here = byLayer[l]!
    const there = byLayer[l + 1]!
    const spineNext = spine[l + 1] ?? camp
    for (const id of here) {
      link(id, spineNext)
      if (there.length > 1 && rng.chance(cfg.extraEdgePct)) {
        const other = rng.pick(there.filter((t) => t !== spineNext))
        link(id, other)
      }
    }
    for (const t of there) {
      if (!here.some((h) => nodes[h]!.next.some((e) => e.to === t))) link(rng.pick(here), t)
    }
  }

  // 5. The spine's steps fit the base stamina: trim the dearest steps until they do.
  const spineEdges = spine.slice(0, -1).map((id, i) => nodes[id]!.next.find((e) => e.to === spine[i + 1])!)
  let budget = spineEdges.reduce((s, e) => s + e.cost, 0)
  while (budget > cfg.spineBudget) {
    const dearest = spineEdges.reduce((a, b) => (b.cost > a.cost ? b : a))
    if (dearest.cost <= EXPEDITION.stepCost.min) break
    dearest.cost -= 1
    budget -= 1
  }

  // 6. What each stop is. Spine stops never hold fog or hidden spots.
  const weights = EXPEDITION.nodeWeights
  const spineWeights = EXPEDITION.spineWeights
  for (let l = 1; l <= layers; l++) {
    for (const id of byLayer[l]!) {
      const n = nodes[id]!
      if (n.kind === 'event') continue
      n.kind = n.spine ? rng.weightedPick(SPINE_KIND_LIST, (k) => spineWeights[k]) : rng.weightedPick(NODE_KIND_LIST, (k) => weights[k])
      if (n.kind === 'obstacle') n.obstacle = rng.nextInt(0, site.obstacles.length - 1)
    }
  }
  return { site: siteId, seed, nodes, layers, start, camp, event, spine }
}

/* ---------- invitations and starting ---------- */

export function staminaFor(m: Pick<Monster, 'stats'>): number {
  return EXPEDITION.stamina.base + Math.floor(m.stats.LIF / EXPEDITION.stamina.lifDivisor)
}

/** The sites whose invitation month this is. */
export function sitesOpenAt(week: number): ExpeditionSite[] {
  const month = dateOf(week).month
  return EXPEDITION_SITES.filter((s) => s.months.includes(month))
}

export type ExpeditionBlock = 'noMonster' | 'ended' | 'busy' | 'away' | 'closed' | 'grade' | 'fame'

/** Whether a trip to this site could start this week (the week's action; the letter's thresholds). */
export function canStartExpedition(state: GameState, siteId: ExpeditionSiteId): { ok: true } | { ok: false; reason: ExpeditionBlock } {
  const m = state.monster
  const site = EXPEDITION_SITE_BY_ID[siteId]
  if (!m) return { ok: false, reason: 'noMonster' }
  if (state.ended) return { ok: false, reason: 'ended' }
  if (state.tournament || state.journey || state.trial || state.expedition) return { ok: false, reason: 'busy' }
  const a = availability(m)
  if (a.locked || a.restOnly) return { ok: false, reason: 'away' }
  if (!site.months.includes(dateOf(state.week).month)) return { ok: false, reason: 'closed' }
  if (TOURNAMENT_GRADES.indexOf(m.grade) < TOURNAMENT_GRADES.indexOf(site.gradeMin)) return { ok: false, reason: 'grade' }
  if (m.fame < site.fameMin) return { ok: false, reason: 'fame' }
  return { ok: true }
}

/** Starts the trip (the caller checked `canStartExpedition`). The seed comes from the game's RNG. */
export function startExpedition(input: GameState, siteId: ExpeditionSiteId, rng: Rng): GameState {
  const state = structuredClone(input)
  const m = state.monster!
  const visit = state.unlocks.expeditionsBySite[siteId] + 1
  state.unlocks.expeditionsBySite[siteId] = visit
  const seed = rng.nextU32()
  const map = buildMap(siteId, seed)
  const stamina = staminaFor(m)
  state.expedition = {
    site: siteId,
    seed,
    startWeek: state.week,
    weekNo: 1,
    stamina,
    staminaMax: stamina,
    at: map.start,
    visited: [map.start],
    searched: [],
    passed: [],
    blockedAt: null,
    visit,
    loot: [],
    sheets: [],
    keyFound: null,
    lootlidPlaced: null,
    ended: null,
    log: ['start'],
  }
  return state
}

export function expeditionMap(e: Pick<ExpeditionState, 'site' | 'seed'>): ExpeditionMap {
  return buildMap(e.site, e.seed)
}

/* ---------- walking the map ---------- */

/** What the player sees a stop as: hidden spots look like plain path until INT reveals them. */
export function visibleKind(node: MapNode, m: Pick<Monster, 'stats'>, site: ExpeditionSite): NodeKind {
  if (node.kind === 'hidden' && m.stats.INT < site.hiddenInt) return 'path'
  return node.kind
}

/** The stops the party can walk to now (none while blocked, exhausted or finished). */
export function movesFrom(state: GameState): MapEdge[] {
  const e = state.expedition
  if (!e || e.ended || e.blockedAt !== null || e.stamina <= 0) return []
  return expeditionMap(e).nodes[e.at]!.next
}

/** The lost chance in fog: max(floor, base − INT / 30) percent (§17). */
export function fogLostPct(m: Pick<Monster, 'stats'>): number {
  return Math.max(EXPEDITION.fog.floorPct, EXPEDITION.fog.basePct - Math.floor(m.stats.INT / EXPEDITION.fog.intDivisor))
}

function addLoot(list: ExpeditionLoot[], id: string, qty: number): void {
  const found = list.find((l) => l.id === id)
  if (found) found.qty += qty
  else list.push({ id, qty })
}

function lootName(id: string, qty: number): string {
  const name = ITEM_BY_ID[id]?.name ?? id
  return qty > 1 ? `${name} ×${qty}` : name
}

/** Draws one row of a loot table into the trip. Returns what to tell the player. */
function drawLoot(state: GameState, e: ExpeditionState, table: readonly LootEntry[], rng: Rng): string {
  const entry = rng.weightedPick(table, (row) => row.weight)
  if (entry.kind === 'item') {
    addLoot(e.loot, entry.id, entry.qty)
    return lootName(entry.id, entry.qty)
  }
  return drawSheet(state, e, entry.families, rng)
}

/** A universal Songsheet of one of the families the player does not own yet; a Grand Sweet when every one is owned. */
function drawSheet(state: GameState, e: ExpeditionState, families: readonly string[], rng: Rng): string {
  const pool = UNIVERSAL_TECHNIQUES.filter((t) => families.includes(t.family) && !state.songbook.includes(t.id) && !e.sheets.includes(t.id))
  if (pool.length === 0) {
    const sweet = grandSweetFor(rng.pick(STAT_KEYS))
    addLoot(e.loot, sweet.id, 1)
    return sweet.name
  }
  const tech = rng.pick(pool)
  e.sheets.push(tech.id)
  return `${tech.name} Songsheet`
}

function log(e: ExpeditionState, key: string, detail = ''): void {
  e.log.push(detail ? `${key}|${detail}` : key)
  if (e.log.length > EXPEDITION.logLimit) e.log.splice(0, e.log.length - EXPEDITION.logLimit)
}

function resolveEvent(state: GameState, e: ExpeditionState, site: ExpeditionSite, node: MapNode, rng: Rng): void {
  const m = state.monster!
  e.searched.push(node.id)
  switch (site.event) {
    case 'strange-chest': {
      const locked = !state.unlocked.includes('lootlid')
      if (locked && (e.visit >= EXPEDITION.chest.pityVisit || rng.chance(EXPEDITION.chest.lootlidPct))) {
        e.keyFound = 'lootlid'
        log(e, 'chestLootlid')
      } else log(e, 'chestLoot', drawLoot(state, e, site.eventLoot, rng))
      return
    }
    case 'archive': {
      const check = site.eventCheck
      const clever = check ? m.stats[check.stat] >= check.value : true
      if (clever && !state.unlocked.includes('gearhoot') && countOf(state.inventory, 'brass-blueprint') === 0) {
        e.keyFound = 'brass-blueprint'
        log(e, 'archive')
      } else log(e, 'archiveMiss', drawLoot(state, e, site.eventLoot, rng))
      return
    }
    case 'crystal-heart':
      log(e, 'crystal', drawLoot(state, e, site.eventLoot, rng))
      return
    case 'sky-puzzle': {
      const check = site.eventCheck
      if (check && m.stats[check.stat] >= check.value) {
        const pool = UNIVERSAL_TECHNIQUES.filter((t) => t.family === 'Special' && !state.songbook.includes(t.id) && !e.sheets.includes(t.id))
        if (pool.length === 0) {
          addLoot(e.loot, 'potential-pearl', 1)
          log(e, 'puzzle', lootName('potential-pearl', 1))
        } else {
          const tech = rng.pick(pool)
          e.sheets.push(tech.id)
          log(e, 'puzzle', `${tech.name} Songsheet`)
        }
      } else log(e, 'puzzleMiss', drawLoot(state, e, site.eventLoot, rng))
      return
    }
  }
}

function resolveNode(state: GameState, e: ExpeditionState, map: ExpeditionMap, node: MapNode, rng: Rng): void {
  const site = EXPEDITION_SITE_BY_ID[e.site]
  const m = state.monster!
  switch (node.kind) {
    case 'obstacle': {
      if (e.passed.includes(node.id)) return
      const ob = site.obstacles[node.obstacle ?? 0]!
      if (m.stats[ob.stat] >= ob.threshold) {
        e.passed.push(node.id)
        log(e, 'passed', ob.name)
      } else {
        e.blockedAt = node.id
        log(e, 'blocked', ob.name)
      }
      return
    }
    case 'search':
    case 'hidden':
    case 'treasure': {
      if (e.searched.includes(node.id)) return
      if (node.kind === 'hidden' && m.stats.INT < site.hiddenInt) return
      e.searched.push(node.id)
      const table = node.kind === 'search' ? site.search : site.treasure
      log(e, node.kind, drawLoot(state, e, table, rng))
      return
    }
    case 'fog': {
      if (rng.chance(fogLostPct(m))) {
        e.stamina = Math.max(0, e.stamina - EXPEDITION.fog.lostCost)
        const cands = map.nodes.filter((n) => n.id !== node.id && (n.layer === node.layer || n.layer === node.layer - 1) && n.kind !== 'camp').map((n) => n.id)
        if (cands.length > 0) {
          e.at = rng.pick(cands)
          e.visited.push(e.at)
        }
        log(e, 'lost')
      } else log(e, 'fogClear')
      return
    }
    case 'event':
      if (!e.searched.includes(node.id)) resolveEvent(state, e, site, node, rng)
      return
    case 'camp':
      conclude(state, 'camp')
      return
    default:
      return
  }
}

/** After any step: no stamina left means the party limps home with everything it found. */
function afterStep(state: GameState): void {
  const e = state.expedition!
  if (!e.ended && e.stamina <= 0) conclude(state, 'exhausted')
}

export type MoveRefusal = 'noTrip' | 'ended' | 'blocked' | 'notAdjacent' | 'noStamina'

/** Walks to a neighbouring stop, pays the step, and resolves what is there. */
export function moveTo(input: GameState, nodeId: number, rng: Rng): { state: GameState; refused: MoveRefusal | null } {
  const exp = input.expedition
  if (!exp || !input.monster) return { state: input, refused: 'noTrip' }
  if (exp.ended) return { state: input, refused: 'ended' }
  if (exp.blockedAt !== null) return { state: input, refused: 'blocked' }
  if (exp.stamina <= 0) return { state: input, refused: 'noStamina' }
  const map = expeditionMap(exp)
  const edge = map.nodes[exp.at]!.next.find((x) => x.to === nodeId)
  if (!edge) return { state: input, refused: 'notAdjacent' }
  const state = structuredClone(input)
  const e = state.expedition!
  e.stamina = Math.max(0, e.stamina - edge.cost)
  e.at = nodeId
  e.visited.push(nodeId)
  resolveNode(state, e, map, map.nodes[nodeId]!, rng)
  afterStep(state)
  return { state, refused: null }
}

/** Pushes through the obstacle in front for extra stamina (§17 detour). */
export function detour(input: GameState): { state: GameState; refused: 'noTrip' | 'notBlocked' | null } {
  const exp = input.expedition
  if (!exp || exp.ended) return { state: input, refused: 'noTrip' }
  if (exp.blockedAt === null) return { state: input, refused: 'notBlocked' }
  const state = structuredClone(input)
  const e = state.expedition!
  e.stamina = Math.max(0, e.stamina - EXPEDITION.detourCost)
  e.passed.push(e.blockedAt!)
  e.blockedAt = null
  log(e, 'detour')
  afterStep(state)
  return { state, refused: null }
}

/** Steps back to the previous stop to try another way (the step already paid is the price). */
export function turnBack(input: GameState): { state: GameState; refused: 'noTrip' | 'notBlocked' | null } {
  const exp = input.expedition
  if (!exp || exp.ended) return { state: input, refused: 'noTrip' }
  if (exp.blockedAt === null) return { state: input, refused: 'notBlocked' }
  const state = structuredClone(input)
  const e = state.expedition!
  const map = expeditionMap(e)
  e.visited.pop()
  e.at = e.visited[e.visited.length - 1] ?? map.start
  if (e.visited.length === 0) e.visited.push(e.at)
  e.blockedAt = null
  log(e, 'turnedBack')
  return { state, refused: null }
}

/** Heads home at any time, keeping everything found (§17). */
export function retreat(input: GameState): { state: GameState; refused: 'noTrip' | 'ended' | null } {
  const exp = input.expedition
  if (!exp) return { state: input, refused: 'noTrip' }
  if (exp.ended) return { state: input, refused: 'ended' }
  const state = structuredClone(input)
  conclude(state, 'retreat')
  return { state, refused: null }
}

/** The trip is over: loot and sheets come home, key items too, the Lootlid moves in, and the §17 after-effects apply. */
function conclude(state: GameState, how: ExpeditionEnd): void {
  const e = state.expedition!
  const m = state.monster!
  e.ended = how
  e.blockedAt = null
  log(e, how === 'camp' ? 'camp' : how === 'retreat' ? 'retreat' : 'exhausted')
  for (const l of e.loot) state.inventory = addItems(state.inventory, l.id, l.qty)
  for (const id of e.sheets) state.songbook = addSheet(state.songbook, id)
  if (e.keyFound === 'brass-blueprint') state.inventory = addItems(state.inventory, 'brass-blueprint', 1)
  if (e.keyFound === 'lootlid') {
    if (!state.unlocked.includes('lootlid')) state.unlocked.push('lootlid')
    const lootlid = createMonster({ id: `lootlid-${e.seed}`, mainBreed: 'lootlid', likes: rollLikes(createRng(UNLOCKS.lootlidSeed + e.seed)), name: 'Lootlid' })
    const placed = placeNewMonster(state, lootlid)
    if (placed.placed) {
      // placeNewMonster returns a fresh copy; carry its changes back into this state.
      state.freezer = placed.state.freezer
      state.monster = placed.state.monster
      state.encyclopedia = placed.state.encyclopedia
      e.lootlidPlaced = placed.placed
    } else e.lootlidPlaced = 'none'
  }
  const after = EXPEDITION.after
  const mm = state.monster!
  mm.fatigue = addCondition(mm.fatigue, after.fatigue)
  mm.stress = addCondition(mm.stress, after.stress)
  state.records.expeditionsDone += 1
  void m
}

/** Weeks away (2–4) tick through here from resolveAction; after the last one the trip is cleared. */
export function tickExpeditionWeek(input: GameState): { state: GameState; weekNo: number; home: boolean } {
  const state = structuredClone(input)
  const e = state.expedition!
  e.weekNo += 1
  const home = e.weekNo >= EXPEDITION.weeks
  if (home) state.expedition = null
  return { state, weekNo: e.weekNo, home }
}

export function isTripOver(e: ExpeditionState | null): boolean {
  return e !== null && e.ended !== null
}

/** The site's obstacle a stop holds, if any. */
export function obstacleOf(site: ExpeditionSite, node: MapNode): ExpeditionSite['obstacles'][number] | null {
  return node.kind === 'obstacle' && node.obstacle !== null ? (site.obstacles[node.obstacle] ?? null) : null
}

/** Every stop on the spine reachable with the base stamina and the stated thresholds (for tests and the Journal). */
export function spineCost(map: ExpeditionMap): number {
  let total = 0
  for (let i = 0; i + 1 < map.spine.length; i++) total += map.nodes[map.spine[i]!]!.next.find((e) => e.to === map.spine[i + 1])!.cost
  return total
}
