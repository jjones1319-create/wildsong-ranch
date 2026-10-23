import { BREED_BY_ID } from '../../data/breeds.ts'
import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { BATTLE, BATTLE_TRAITS, HEARTSTONE } from '../../data/tuning.ts'
import { TOURNAMENT_GRADES, type Technique } from '../../data/types.ts'
import { clamp, divRound } from '../mathx.ts'
import { loyaltyOf, totalStats } from '../monster.ts'
import { createRng, type Rng } from '../rng.ts'
import { masteryBonuses } from '../songbook.ts'
import { variantFarHit, variantWitherPlus } from '../variants.ts'
import { decideAi } from './ai.ts'
import { bandOf, critTenths, damageBase, distractionPct, finishDamage, formAdjusted, hitTenths, hpPctTenths, nimbleBonus, walkPerTick } from './formulas.ts'
import { bulwarkPct, clutchPct, composurePct, lastStandPct, ragePct, specialMods, tickSpecial, tryTrigger, valorPct } from './specials.ts'
import {
  traitBlessed,
  traitChills,
  traitCritBonus,
  traitCritTakenMul,
  traitDealtMul,
  traitDragonheart,
  traitExtraHits,
  traitFameCapBonus,
  traitFreeDash,
  traitHealMul,
  traitHitBonus,
  traitImmovable,
  traitNimble,
  traitReflect,
  traitRegenMul,
  traitSpeedMul,
  traitTakenMul,
  traitWitherTakenMul,
} from './traits.ts'
import type { BattleEvent, BattleInput, BattleOptions, BattleOutcome, BattleResult, BattleState, FighterSetup, FighterState, Side } from './types.ts'

/**
 * GAME_DESIGN §12: the battle engine. A fixed-step simulation at 30 ticks per second, a pure function of
 * (monster A, monster B, seed, inputs). The engine owns one mutable state (immutability per tick would make
 * the Battle Lab's thousands of fights crawl); callers that need a snapshot clone `state.fighters`.
 *
 * A technique resolves on the tick it is fired, from the state at that moment; the attacker is then busy for
 * the technique's animation (no movement, no guts regeneration). The renderer shows the impact later.
 *
 * Tick order: inputs → timers → decisions (AI or Assist) → fires → dash, push, walking, slides → regen →
 * Clutch window → time-up check.
 */

export interface Battle {
  state: BattleState
  rng: Rng
}

const CENTI = 100
const GUTS_ACC = 1000

function setupFighter(side: Side, s: FighterSetup): FighterState {
  const m = s.monster
  const form = formAdjusted(m.stats, m.form)
  const techniques = m.techniques
    .filter((t) => TECHNIQUE_BY_ID[t.id] !== undefined)
    .map((t) => {
      const b = masteryBonuses(t)
      const tech = TECHNIQUE_BY_ID[t.id]!
      // §16 the Heirloom (+hit on the donor's family) and CONTENT §12 variant perks.
      const heirloom = m.heirloom === tech.family ? HEARTSTONE.heirloomHit : 0
      const far = tech.range === 4 ? variantFarHit(m) : 0
      return { id: t.id, hitBonus: b.hit + heirloom + far, forceBonus: b.force, witherBonus: variantWitherPlus(m, tech.family) }
    })
  return {
    side,
    name: m.name,
    trait: BREED_BY_ID[m.mainBreed].trait,
    control: s.control,
    personality: s.personality,
    habit: s.habit ?? 'none',
    auto: false,
    techniques,
    stats: { ...m.stats },
    spdForm: form.spd,
    defForm: form.def,
    total: totalStats(m.stats),
    maxHp: Math.max(1, m.stats.LIF),
    gutsRate: m.gutsRate,
    loyalty: loyaltyOf(m),
    fame: m.fame,
    nature: m.nature,
    stress: m.stress,
    gradeIndex: Math.max(0, TOURNAMENT_GRADES.indexOf(m.grade)),
    x: (side === 0 ? -BATTLE.arena.startX : BATTLE.arena.startX) * CENTI,
    hp: Math.max(1, m.stats.LIF),
    guts: BATTLE.guts.start,
    gutsAcc: 0,
    busyTicks: 0,
    busyTech: null,
    moveDir: 0,
    dashTicks: 0,
    dashCooldown: 0,
    lunging: false,
    pushTicks: 0,
    pushCooldown: 0,
    slideTicks: 0,
    slideDir: 1,
    stunTicks: 0,
    dawdleTicks: 0,
    distractCooldown: 0,
    slowTicks: 0,
    special: null,
    usedSpecials: [],
    hitsTakenRow: 0,
    successRow: 0,
    stillTicks: 0,
    ramArmed: false,
    dragonheartUsed: false,
    blessedAcc: 0,
    habitDone: false,
    aiCooldown: 0,
    aiTargetBand: 2,
    aiNextThink: 0,
    assistTech: null,
    wantFire: null,
    wantDash: false,
    wantPush: false,
    attacks: 0,
    hits: 0,
    damageDealt: 0,
    techUses: {},
  }
}

export function createBattle(a: FighterSetup, b: FighterSetup, opts: BattleOptions): Battle {
  return {
    state: { tick: 0, timerTicks: opts.timerTicks, seed: opts.seed, fighters: [setupFighter(0, a), setupFighter(1, b)], outcome: null, log: [] },
    rng: createRng(opts.seed),
  }
}

/** The gap between the two bodies, in whole units (§12.1). */
export function gapUnits(state: BattleState): number {
  const [a, b] = state.fighters
  return Math.floor(Math.abs(b.x - a.x) / CENTI) - 2 * BATTLE.arena.bodyRadius
}

export function currentBand(state: BattleState): number {
  return bandOf(gapUnits(state))
}

/** Busy, stunned, dawdling, shoving or being shoved: no actions this tick. */
export function canAct(f: FighterState): boolean {
  return f.busyTicks === 0 && f.stunTicks === 0 && f.dawdleTicks === 0 && f.pushTicks === 0 && f.slideTicks === 0
}

export function isOver(state: BattleState): boolean {
  return state.outcome !== null
}

export function effectiveCost(f: FighterState, tech: Technique): number {
  return divRound(tech.cost * specialMods(f.special).costPct, 100)
}

/** Could this fighter fire this technique right now (known, affordable, in range, free to act)? */
export function canFire(state: BattleState, f: FighterState, techId: string): boolean {
  const tech = TECHNIQUE_BY_ID[techId]
  if (!tech || !f.techniques.some((t) => t.id === techId)) return false
  if (!canAct(f)) return false
  if (f.guts < effectiveCost(f, tech)) return false
  return currentBand(state) === tech.range
}

/** Live hit chance (tenths of a percent) for the technique panel, without the random advantage of a distracted defender. */
export function previewHitTenths(state: BattleState, side: Side, techId: string): number {
  const f = state.fighters[side]
  const opp = state.fighters[1 - side as Side]
  const tech = TECHNIQUE_BY_ID[techId]
  const ref = f.techniques.find((t) => t.id === techId)
  if (!tech || !ref) return 0
  return hitTenths({
    techHit: tech.hit + ref.hitBonus,
    skiAtt: f.stats.SKI,
    spdDef: opp.spdForm + nimbleBonus(traitNimble(opp.trait)),
    gutsAtt: f.guts,
    gutsDef: opp.guts,
    bonus: traitHitBonus(f.trait, tech.range, opp.total > f.total),
    advantages: (opp.dawdleTicks > 0 ? 1 : 0) + (specialMods(opp.special).givesAdvantage ? 1 : 0),
    disadvantage: specialMods(opp.special).givesDisadvantage,
  })
}

/** Expected damage of a technique right now (no crit, no roll), for the AI and the panel. */
export function previewDamage(f: FighterState, opp: FighterState, tech: Technique, forceBonus: number): number {
  const base = damageBase({
    force: tech.force + forceBonus,
    a: f.stats[tech.type],
    defDef: opp.defForm,
    defSame: opp.stats[tech.type],
    gutsAtt: f.guts,
    rateAtt: f.gutsRate,
    gutsDef: opp.guts,
    rateDef: opp.gutsRate,
  })
  return finishDamage(base, [])
}

/* ---------- the tick ---------- */

function applyInput(state: BattleState, input: BattleInput, log: BattleEvent[]): void {
  const f = state.fighters[input.side]
  const a = input.action
  switch (a.kind) {
    case 'forfeit':
      endBattle(state, { how: 'forfeit', winner: (1 - input.side) as Side, hpPct: [hpPctTenths(state.fighters[0].hp, state.fighters[0].maxHp), hpPctTenths(state.fighters[1].hp, state.fighters[1].maxHp)], ticks: state.tick }, log)
      return
    case 'auto':
      f.auto = a.on
      if (a.on) {
        f.assistTech = null
        f.moveDir = 0
      }
      return
    default:
      break
  }
  if (f.control !== 'player' || f.auto) return
  switch (a.kind) {
    case 'fire':
      f.wantFire = a.tech
      f.assistTech = null
      break
    case 'move':
      f.moveDir = a.dir
      f.assistTech = null
      break
    case 'dash':
      f.wantDash = true
      break
    case 'push':
      f.wantPush = true
      break
    case 'assist':
      f.assistTech = a.tech
      if (a.tech === null) f.moveDir = 0
      break
  }
}

function tickTimers(f: FighterState, state: BattleState, log: BattleEvent[]): void {
  if (f.busyTicks > 0) f.busyTicks -= 1
  if (f.busyTicks === 0) f.busyTech = null
  if (f.dashCooldown > 0) f.dashCooldown -= 1
  if (f.pushCooldown > 0) f.pushCooldown -= 1
  if (f.distractCooldown > 0) f.distractCooldown -= 1
  if (f.slowTicks > 0) f.slowTicks -= 1
  if (f.stunTicks > 0) f.stunTicks -= 1
  if (f.dawdleTicks > 0) f.dawdleTicks -= 1
  if (f.aiCooldown > 0) f.aiCooldown -= 1
  tickSpecial(f)
  if (traitBlessed(f.trait) && f.hp > 0) {
    f.blessedAcc += 1
    if (f.blessedAcc >= BATTLE.blessedEveryTicks) {
      f.blessedAcc = 0
      const amount = Math.max(1, divRound(f.maxHp * BATTLE_TRAITS.blessedPct, 100))
      const before = f.hp
      f.hp = Math.min(f.maxHp, f.hp + amount)
      if (f.hp > before) log.push({ t: state.tick, kind: 'heal', side: f.side, amount: f.hp - before, why: 'blessed' })
    }
  }
}

/** Assist (§12.11): walk toward the technique's band and fire on arrival while guts last. */
function assistDecision(state: BattleState, f: FighterState): void {
  if (!f.assistTech) return
  const tech = TECHNIQUE_BY_ID[f.assistTech]
  if (!tech || f.guts < effectiveCost(f, tech)) {
    f.assistTech = null
    f.moveDir = 0
    return
  }
  const band = currentBand(state)
  if (band === tech.range) {
    f.wantFire = f.assistTech
    f.assistTech = null
    f.moveDir = 0
    return
  }
  f.moveDir = band > tech.range ? 1 : -1
}

function towardSign(f: FighterState, opp: FighterState): 1 | -1 {
  return opp.x >= f.x ? 1 : -1
}

/** Walking speed this tick in centi-units (traits, Chill and backing away included). */
export function speedPerTick(f: FighterState, backing: boolean): number {
  let v = walkPerTick(f.stats.SPD)
  v = divRound(v * traitSpeedMul(f.trait), 1000)
  if (f.slowTicks > 0) v = divRound(v * BATTLE_TRAITS.chillPct, 100)
  if (backing) v = divRound(v * BATTLE.walk.backPct, 100)
  return v
}

/** Moves `f` by `dx` centi-units, never through the wall or the opponent's body. */
function moveBy(f: FighterState, opp: FighterState, dx: number): void {
  const wall = (BATTLE.arena.halfWidth - BATTLE.arena.bodyRadius) * CENTI
  let nx = clamp(f.x + dx, -wall, wall)
  const minGap = 2 * BATTLE.arena.bodyRadius * CENTI
  if (opp.x >= f.x && nx > opp.x - minGap) nx = Math.max(f.x, opp.x - minGap)
  if (opp.x < f.x && nx < opp.x + minGap) nx = Math.min(f.x, opp.x + minGap)
  f.x = nx
}

function startDash(state: BattleState, f: FighterState, log: BattleEvent[]): void {
  const gap = gapUnits(state)
  if (f.dashCooldown > 0 || gap < BATTLE.dash.minGap) return
  const free = traitFreeDash(f.trait)
  if (!free && f.guts < BATTLE.dash.cost) return
  if (!free) f.guts -= BATTLE.dash.cost
  f.dashTicks = BATTLE.dash.maxTicks
  f.lunging = false
  f.dashCooldown = BATTLE.dash.cooldown
  if (traitFreeDash(f.trait)) f.ramArmed = true
  log.push({ t: state.tick, kind: 'dash', side: f.side })
}

function startPush(state: BattleState, f: FighterState, opp: FighterState, log: BattleEvent[]): void {
  if (f.pushCooldown > 0 || gapUnits(state) > BATTLE.push.maxGap) return
  f.pushTicks = BATTLE.push.ticks
  f.pushCooldown = BATTLE.push.cooldown
  const blocked = traitImmovable(opp.trait)
  if (!blocked) knockBack(opp, f)
  log.push({ t: state.tick, kind: 'push', side: f.side, target: opp.side, blocked })
}

function knockBack(target: FighterState, from: FighterState): void {
  target.slideTicks = BATTLE.push.ticks
  target.slideDir = target.x >= from.x ? 1 : -1
  target.assistTech = null
}

function movement(state: BattleState, f: FighterState, opp: FighterState): void {
  const before = f.x
  if (f.dashTicks > 0) {
    const bandBefore = currentBand(state)
    const v = divRound(speedPerTick(f, false) * BATTLE.dash.speedMul, 1)
    moveBy(f, opp, v * towardSign(f, opp))
    if (!f.lunging) f.dashTicks -= 1
    const bandAfter = currentBand(state)
    if (f.lunging ? bandAfter <= 1 : bandAfter < bandBefore) {
      f.dashTicks = 0
      f.lunging = false
    }
    if (gapUnits(state) <= 0) {
      f.dashTicks = 0
      f.lunging = false
    }
  } else if (f.moveDir !== 0 && canAct(f)) {
    const toward = f.moveDir === 1
    const v = speedPerTick(f, !toward)
    moveBy(f, opp, v * (toward ? towardSign(f, opp) : -towardSign(f, opp)))
  }
  if (f.x === before && f.dashTicks === 0) f.stillTicks += 1
  else f.stillTicks = 0
}

function slide(f: FighterState, opp: FighterState): void {
  if (f.slideTicks <= 0) return
  const perTick = divRound(BATTLE.push.distance * CENTI, BATTLE.push.ticks)
  const wall = (BATTLE.arena.halfWidth - BATTLE.arena.bodyRadius) * CENTI
  f.x = clamp(f.x + perTick * f.slideDir, -wall, wall)
  // Never slide into the opponent (a slide always goes away from them, but the wall can pin both).
  const minGap = 2 * BATTLE.arena.bodyRadius * CENTI
  if (Math.abs(f.x - opp.x) < minGap) f.x = opp.x + (f.slideDir > 0 ? minGap : -minGap)
  f.slideTicks -= 1
  f.stillTicks = 0
}

function regen(f: FighterState): void {
  if (f.busyTicks > 0 || f.stunTicks > 0 || f.hp <= 0) return
  let mul = traitRegenMul(f.trait, f.guts)
  mul = divRound(mul * specialMods(f.special).regenPct, 100)
  f.gutsAcc += mul
  const per = f.gutsRate * GUTS_ACC
  while (f.gutsAcc >= per) {
    f.gutsAcc -= per
    if (f.guts < BATTLE.guts.cap) f.guts += 1
  }
}

function endBattle(state: BattleState, outcome: BattleOutcome, log: BattleEvent[]): void {
  if (state.outcome) return
  state.outcome = outcome
  log.push({ t: state.tick, kind: 'end', outcome })
}

/** Applies damage to `target`, honouring Last Stand; returns true on a KO. */
function hurt(state: BattleState, target: FighterState, amount: number, rng: Rng, log: BattleEvent[]): boolean {
  if (amount <= 0 || target.hp <= 0) return false
  if (amount >= target.hp) {
    if (tryTrigger(target, 'lastStand', lastStandPct(target), rng, state.tick, log)) {
      target.hp = 1
      return false
    }
    target.hp = 0
    log.push({ t: state.tick, kind: 'ko', side: target.side })
    return true
  }
  target.hp -= amount
  return false
}

function heal(state: BattleState, f: FighterState, amount: number, why: 'tech' | 'drain' | 'jackpot', log: BattleEvent[]): void {
  if (amount <= 0 || f.hp <= 0) return
  const before = f.hp
  f.hp = Math.min(f.maxHp, f.hp + amount)
  if (f.hp > before) log.push({ t: state.tick, kind: 'heal', side: f.side, amount: f.hp - before, why })
}

function finishKo(state: BattleState, fallen: Side, log: BattleEvent[]): void {
  const [a, b] = state.fighters
  endBattle(state, { how: 'ko', winner: (1 - fallen) as Side, hpPct: [hpPctTenths(a.hp, a.maxHp), hpPctTenths(b.hp, b.maxHp)], ticks: state.tick }, log)
}

/** §12.5–§12.8 and §10.3: one technique, resolved now. */
function resolveFire(state: BattleState, f: FighterState, opp: FighterState, techId: string, rng: Rng, log: BattleEvent[]): void {
  const tech = TECHNIQUE_BY_ID[techId]
  const ref = f.techniques.find((t) => t.id === techId)
  if (!tech || !ref || !canAct(f)) return
  const cost = effectiveCost(f, tech)
  if (f.guts < cost || currentBand(state) !== tech.range) return

  // §12.6 distraction, rolled when an action starts, at most once every 90 ticks.
  if (f.distractCooldown === 0) {
    f.distractCooldown = BATTLE.distraction.rollCooldown
    if (rng.chance(distractionPct(f.loyalty))) {
      f.dawdleTicks = BATTLE.distraction.dawdleTicks
      f.moveDir = 0
      f.assistTech = null
      log.push({ t: state.tick, kind: 'distracted', side: f.side })
      return
    }
  }

  const gutsBefore = f.guts
  f.guts -= cost
  f.busyTicks = tech.anim
  f.busyTech = tech.id
  f.attacks += 1
  f.techUses[tech.id] = (f.techUses[tech.id] ?? 0) + 1
  log.push({ t: state.tick, kind: 'fire', side: f.side, tech: tech.id, cost })
  const ramArmed = f.ramArmed
  f.ramArmed = false

  const e = tech.effect
  if (e?.kind === 'heal') {
    heal(state, f, divRound(divRound(f.maxHp * e.pct, 100) * traitHealMul(f.trait), 1000), 'tech', log)
  }

  const underdog = opp.total > f.total
  const myMods = specialMods(f.special)
  const theirMods = specialMods(opp.special)
  const hits = tech.force > 0 ? (e?.kind === 'multi' ? e.hits + traitExtraHits(f.trait) : 1) : 0
  const hitChance = hitTenths({
    techHit: tech.hit + ref.hitBonus,
    skiAtt: f.stats.SKI,
    spdDef: opp.spdForm + nimbleBonus(traitNimble(opp.trait)),
    gutsAtt: gutsBefore,
    gutsDef: opp.guts,
    bonus: traitHitBonus(f.trait, tech.range, underdog),
    advantages: (opp.dawdleTicks > 0 ? 1 : 0) + (theirMods.givesAdvantage ? 1 : 0),
    disadvantage: theirMods.givesDisadvantage,
  })
  let critChance = critTenths({ sharp: tech.sharp, fame: f.fame, oppFame: opp.fame, nature: f.nature, stress: f.stress, fameCapBonus: traitFameCapBonus(f.trait), bonus: traitCritBonus(f.trait) })
  critChance = divRound(critChance * traitCritTakenMul(opp.trait), 1000) * myMods.critMul

  for (let i = 1; i <= hits; i++) {
    if (opp.hp <= 0 || state.outcome) break
    if (rng.nextInt(1, 1000) > hitChance) {
      log.push({ t: state.tick, kind: 'miss', side: f.side, target: opp.side, tech: tech.id, hitNo: i, of: hits })
      f.successRow = 0
      opp.successRow += 1
      opp.hitsTakenRow = 0
      if (e?.kind === 'recoil') {
        const self = Math.max(1, divRound(f.maxHp * e.pct, 100))
        log.push({ t: state.tick, kind: 'recoil', side: f.side, amount: self })
        if (hurt(state, f, self, rng, log)) {
          finishKo(state, f.side, log)
          return
        }
      }
      if (composurePct(opp) > 0) tryTrigger(opp, 'composure', composurePct(opp), rng, state.tick, log)
      continue
    }

    const crit = rng.nextInt(1, 1000) <= critChance
    const base = damageBase({
      force: tech.force + ref.forceBonus,
      a: f.stats[tech.type],
      defDef: opp.defForm,
      defSame: opp.stats[tech.type],
      gutsAtt: gutsBefore,
      rateAtt: f.gutsRate,
      gutsDef: opp.guts,
      rateDef: opp.gutsRate,
    })
    const mults: number[] = []
    if (crit) mults.push(BATTLE.damage.critMul * 10)
    mults.push(traitDealtMul(f.trait, { family: tech.family, hpPct: hpPctTenths(f.hp, f.maxHp), underdog, ramArmed }))
    mults.push(traitTakenMul(opp.trait, { techType: tech.type, still: opp.stillTicks >= BATTLE.statueTicks }))
    mults.push(myMods.dealtPct * 10, theirMods.takenPct * 10)
    let jackpot: 'double' | 'heal' | 'fizzle' | null = null
    if (e?.kind === 'jackpot') {
      jackpot = rng.pick(['double', 'heal', 'fizzle'] as const)
      log.push({ t: state.tick, kind: 'jackpot', side: f.side, result: jackpot })
      if (jackpot === 'double') mults.push(2000)
    }
    mults.push(BATTLE.damage.rnd.min * 10 + rng.nextInt(0, (BATTLE.damage.rnd.max - BATTLE.damage.rnd.min) * 10))
    const damage = jackpot === 'fizzle' ? 0 : finishDamage(base, mults)

    let wither = tech.wither + ref.witherBonus
    if (crit) wither = divRound(wither * BATTLE.damage.critMul, 100)
    wither = divRound(wither * myMods.witherDealtPct, 100)
    wither = divRound(wither * traitWitherTakenMul(opp.trait), 1000)
    const withered = Math.min(opp.guts, wither)
    opp.guts -= withered
    if (e?.kind === 'gutsSteal') f.guts = Math.min(BATTLE.guts.cap, f.guts + withered)

    f.hits += 1
    f.damageDealt += damage
    f.successRow += 1
    opp.successRow = 0
    opp.hitsTakenRow += 1
    log.push({ t: state.tick, kind: 'hit', side: f.side, target: opp.side, tech: tech.id, damage, crit, wither: withered, hitNo: i, of: hits })

    if (jackpot === 'heal') heal(state, f, divRound(f.maxHp * 20, 100), 'jackpot', log)
    if (e?.kind === 'drain' && damage > 0) heal(state, f, divRound(divRound(damage * e.pct, 100) * traitHealMul(f.trait), 1000), 'drain', log)
    if (e?.kind === 'stun' && !traitImmovable(opp.trait)) {
      opp.stunTicks = Math.max(opp.stunTicks, e.ticks)
      opp.assistTech = null
      log.push({ t: state.tick, kind: 'stun', side: opp.side, ticks: e.ticks })
    }
    if (e?.kind === 'push' && !traitImmovable(opp.trait)) {
      knockBack(opp, f)
      log.push({ t: state.tick, kind: 'push', side: f.side, target: opp.side, blocked: false })
    }
    if (traitChills(f.trait)) opp.slowTicks = BATTLE.chillTicks

    const hpBefore = opp.hp
    const ko = hurt(state, opp, damage, rng, log)
    if (traitDragonheart(opp.trait) && !opp.dragonheartUsed && opp.hp > 0 && opp.hp * 100 < opp.maxHp * BATTLE_TRAITS.dragonheart.hpPctBelow && hpBefore * 100 >= opp.maxHp * BATTLE_TRAITS.dragonheart.hpPctBelow) {
      opp.dragonheartUsed = true
      opp.guts = Math.min(BATTLE.guts.cap, opp.guts + BATTLE_TRAITS.dragonheart.guts)
      log.push({ t: state.tick, kind: 'trait', side: opp.side, trait: opp.trait })
    }
    if (ko) {
      finishKo(state, opp.side, log)
      return
    }

    const reflect = traitReflect(opp.trait)
    if (reflect && tech.type === 'INT' && damage > 0 && rng.chance(reflect.chancePct)) {
      const back = Math.max(1, divRound(damage * reflect.pct, 100))
      log.push({ t: state.tick, kind: 'reflect', side: opp.side, target: f.side, amount: back })
      if (hurt(state, f, back, rng, log)) {
        finishKo(state, f.side, log)
        return
      }
    }

    // §12.7 triggers after a hit lands.
    if (valorPct(opp) > 0) tryTrigger(opp, 'valor', valorPct(opp), rng, state.tick, log)
    if (ragePct(opp, withered) > 0) tryTrigger(opp, 'rage', ragePct(opp, withered), rng, state.tick, log)
    if (bulwarkPct(opp) > 0) tryTrigger(opp, 'bulwark', bulwarkPct(opp), rng, state.tick, log)
    if (composurePct(f) > 0) tryTrigger(f, 'composure', composurePct(f), rng, state.tick, log)
  }

  if (e?.kind === 'lunge' && !state.outcome && currentBand(state) > 1) {
    f.lunging = true
    f.dashTicks = 1
  }
}

/** Advances one tick. Returns the events of that tick (also appended to `state.log`). */
export function step(battle: Battle, inputs: readonly BattleInput[] = []): BattleEvent[] {
  const { state, rng } = battle
  if (state.outcome) return []
  state.tick += 1
  const log: BattleEvent[] = []
  const [a, b] = state.fighters

  for (const input of inputs) applyInput(state, input, log)
  if (state.outcome) {
    state.log.push(...log)
    return log
  }

  tickTimers(a, state, log)
  tickTimers(b, state, log)

  for (const f of state.fighters) {
    const opp = state.fighters[(1 - f.side) as Side]
    if (!canAct(f)) continue
    if (f.control === 'ai' || f.auto) decideAi(state, f, opp, rng)
    else assistDecision(state, f)
  }

  for (const f of state.fighters) {
    if (state.outcome) break
    const opp = state.fighters[(1 - f.side) as Side]
    const want = f.wantFire
    f.wantFire = null
    if (want && f.hp > 0) resolveFire(state, f, opp, want, rng, log)
  }

  if (!state.outcome) {
    for (const f of state.fighters) {
      const opp = state.fighters[(1 - f.side) as Side]
      if (canAct(f) && f.dashTicks === 0) {
        if (f.wantPush) startPush(state, f, opp, log)
        else if (f.wantDash) startDash(state, f, log)
      }
      f.wantDash = false
      f.wantPush = false
    }
    for (const f of state.fighters) {
      const opp = state.fighters[(1 - f.side) as Side]
      if (f.slideTicks > 0) slide(f, opp)
      else if (f.pushTicks > 0) f.pushTicks -= 1
      else movement(state, f, opp)
      // A busy monster that just finished its animation and owes a lunge: start it now.
      if (f.lunging && f.dashTicks === 0) f.lunging = false
    }
    regen(a)
    regen(b)

    if (state.tick === state.timerTicks - BATTLE.clutchWindowTicks) {
      for (const f of state.fighters) {
        const opp = state.fighters[(1 - f.side) as Side]
        const pct = clutchPct(f, opp)
        if (pct > 0) tryTrigger(f, 'clutch', pct, rng, state.tick, log)
      }
    }

    if (state.tick >= state.timerTicks) {
      const pa = hpPctTenths(a.hp, a.maxHp)
      const pb = hpPctTenths(b.hp, b.maxHp)
      endBattle(state, { how: 'time', winner: pa > pb ? 0 : pb > pa ? 1 : null, hpPct: [pa, pb], ticks: state.tick }, log)
    }
  }

  state.log.push(...log)
  return log
}

/** Runs a battle to its end with the given inputs (by tick). */
export function runBattle(a: FighterSetup, b: FighterSetup, opts: BattleOptions, inputs: readonly BattleInput[] = []): BattleResult {
  const battle = createBattle(a, b, opts)
  const byTick = new Map<number, BattleInput[]>()
  for (const i of inputs) byTick.set(i.tick, [...(byTick.get(i.tick) ?? []), i])
  let guard = 0
  while (!battle.state.outcome && guard++ < opts.timerTicks + 10) step(battle, byTick.get(battle.state.tick + 1) ?? [])
  if (!battle.state.outcome) {
    const [x, y] = battle.state.fighters
    endBattle(battle.state, { how: 'time', winner: null, hpPct: [hpPctTenths(x.hp, x.maxHp), hpPctTenths(y.hp, y.maxHp)], ticks: battle.state.tick }, battle.state.log)
  }
  return { outcome: battle.state.outcome!, fighters: battle.state.fighters, log: battle.state.log, seed: opts.seed }
}

/** Seconds per match → ticks. */
export function timerTicksFor(seconds: number): number {
  return seconds * BATTLE.ticksPerSecond
}
