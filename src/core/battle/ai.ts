import { TECHNIQUE_BY_ID } from '../../data/techniques.ts'
import { AI } from '../../data/tuning.ts'
import type { Technique } from '../../data/types.ts'
import { divRound } from '../mathx.ts'
import type { Rng } from '../rng.ts'
import { currentBand, effectiveCost, gapUnits, previewDamage, previewHitTenths, speedPerTick } from './engine.ts'
import { bandCentre, isqrt } from './formulas.ts'
import type { BattleState, FighterState } from './types.ts'

/**
 * GAME_DESIGN §12.10: the CPU brain (also Auto mode and the Battle Lab). It thinks every tick while it isn't
 * animating: a cooldown after each technique, a use-rate attack decision weighted by EV^1.5, a movement
 * target band re-picked every 15 ticks, pushes when touching and wanting distance, dashes when wanting to
 * close in. Everything integer; EV is in thousandths.
 */

interface Option {
  tech: Technique
  cost: number
  ev: number
}

/** EV = hit · (damage as % of the opponent's max HP + 0.35 · wither) + 0.05 · sharp, ×1000. */
function evOf(state: BattleState, f: FighterState, opp: FighterState, tech: Technique, forceBonus: number): number {
  const hit = previewHitTenths(state, f.side, tech.id)
  let term: number
  if (tech.force > 0) {
    const dmg = previewDamage(f, opp, tech, forceBonus)
    term = divRound(dmg * 100 * 1000, opp.maxHp) + AI.ev.witherWeight * 10 * tech.wither
  } else {
    const healPct = tech.effect?.kind === 'heal' ? tech.effect.pct : 0
    term = divRound(healPct * 1000 * (f.maxHp - f.hp), f.maxHp)
  }
  return divRound(hit * term, 1000) + AI.ev.sharpWeight * 10 * tech.sharp
}

function options(state: BattleState, f: FighterState, opp: FighterState, maxCost: number, band: number | null): Option[] {
  const out: Option[] = []
  for (const ref of f.techniques) {
    const tech = TECHNIQUE_BY_ID[ref.id]
    if (!tech) continue
    if (band !== null && tech.range !== band) continue
    const cost = effectiveCost(f, tech)
    if (cost > maxCost) continue
    out.push({ tech, cost, ev: evOf(state, f, opp, tech, ref.forceBonus) })
  }
  return out
}

/** The best score per band (1–4) among techniques the fighter could soon afford, with personality bias. */
function bandScores(state: BattleState, f: FighterState, opp: FighterState): number[] {
  const p = AI.personalities[f.personality]
  const scores = [0, 0, 0, 0, 0]
  for (const o of options(state, f, opp, f.guts + AI.affordSlack, null)) {
    let s = o.ev
    if (o.tech.range === 4) s = divRound(s * p.farBias, 100)
    if (o.tech.range === 1) s = divRound(s * p.closeBias, 100)
    if (s > scores[o.tech.range]!) scores[o.tech.range] = s
  }
  return scores
}

function cheapestBand(f: FighterState): number {
  let best: Technique | null = null
  for (const ref of f.techniques) {
    const tech = TECHNIQUE_BY_ID[ref.id]
    if (tech && (!best || tech.cost < best.cost)) best = tech
  }
  return best ? best.range : 2
}

/** Sets the fighter's requests for this tick (fire, dash, push, move direction). */
export function decideAi(state: BattleState, f: FighterState, opp: FighterState, rng: Rng): void {
  const p = AI.personalities[f.personality]
  const gap = gapUnits(state)
  const band = currentBand(state)

  // 1–2. Attack decision.
  const rookieHold = f.gradeIndex <= 1 && f.guts < AI.rookieReserve
  if (f.aiCooldown === 0 && !rookieHold && band <= 4) {
    const inRange = options(state, f, opp, f.guts, band)
    if (inRange.length > 0) {
      const rate = f.guts < AI.gutsSplit ? p.useLow : p.useHigh
      if (rng.chance(rate / 30)) {
        const pick = rng.weightedPick(inRange, (o) => {
          let w = Math.max(1, o.ev * Math.max(1, isqrt(o.ev)))
          if (o.cost >= AI.bigCost && f.guts >= AI.bigGuts) w = divRound(w * p.bigBias, 100)
          if (o.tech.family === 'Wither') w = divRound(w * p.witherBias, 100)
          return w
        })
        f.wantFire = pick.tech.id
        f.aiCooldown = rng.nextInt(AI.cooldown.min, AI.cooldown.max)
      }
    }
  }

  // 3. Movement: re-pick the target band every 15 ticks.
  if (state.tick >= f.aiNextThink) {
    f.aiNextThink = state.tick + AI.thinkEveryTicks
    const scores = bandScores(state, f, opp)
    let best = 0
    let second = 0
    for (let b = 1; b <= 4; b++) {
      if (scores[b]! > (scores[best] ?? -1)) {
        second = best
        best = b
      } else if (scores[b]! > (scores[second] ?? -1) && b !== best) second = b
    }
    if (best === 0) f.aiTargetBand = cheapestBand(f)
    else if (band <= 4 && scores[band]! > 0 && rng.chance(AI.stayPct)) f.aiTargetBand = band
    else if (second !== 0 && scores[second]! > 0 && rng.chance(AI.secondBestPct)) f.aiTargetBand = second
    else f.aiTargetBand = best
    // Kiting only works on a slower opponent: backing away (×0.85) from a chaser never gains ground, so a fighter
    // that can't outrun the other one fights at the best band it can actually reach instead of never attacking.
    if (f.aiTargetBand > band && speedPerTick(f, true) <= speedPerTick(opp, false)) {
      let reachable = 0
      for (let b = 1; b <= band && b <= 4; b++) if (scores[b]! > (scores[reachable] ?? 0)) reachable = b
      if (reachable > 0) f.aiTargetBand = reachable
    }
  }
  const centre = bandCentre(f.aiTargetBand)
  const dead = 20
  f.moveDir = gap > centre + dead ? 1 : gap < centre - dead ? -1 : 0

  // 4. Push when touching and wanting distance.
  if (gap <= 40 && f.aiTargetBand >= AI.pushFromBand && f.pushCooldown === 0) f.wantPush = true

  // 5. Dash in when the target is two or more bands closer.
  if (f.aiTargetBand <= band - AI.dash.bandsCloser && f.guts >= AI.dash.gutsMin && f.dashCooldown === 0 && rng.chance(AI.dash.pctPerTick)) f.wantDash = true
}
