import { AI, STYLE_BANDS } from '../../data/tuning.ts'
import type { AiTier } from '../../data/types.ts'
import { clamp, divRound } from '../mathx.ts'
import { loyaltyOf, styleOf, type Monster } from '../monster.ts'

/**
 * docs/BATTLE_3D.md §4.1 battle sense (5–95): how well a fighter reads a duel. CPU fighters take it from their tier;
 * the player's monster earns it by how it was raised: the battles it has fought, its loyalty, and not being spoiled.
 */

export interface Sense {
  sense: number
  /** 0 no, 1 fond, 2 doting (the raising style Spoil − Fear). */
  spoiled: 0 | 1 | 2
  /** The parts, for the screen's explanation. */
  battles: number
  fromBattles: number
  fromLoyalty: number
  fromSpoiling: number
}

const S = AI.duel.sense

export function spoiledLevel(m: Monster): 0 | 1 | 2 {
  const style = styleOf(m)
  return style >= STYLE_BANDS.doting ? 2 : style >= STYLE_BANDS.fond ? 1 : 0
}

export function senseOfMonster(m: Monster): Sense {
  const battles = m.records.wins + m.records.losses + m.records.draws
  const fromBattles = Math.min(S.battleCap, battles * S.perBattle)
  const fromLoyalty = divRound((loyaltyOf(m) - 50) * S.loyaltyPct, 100)
  const spoiled = spoiledLevel(m)
  const fromSpoiling = spoiled === 2 ? -S.spoiled.doting : spoiled === 1 ? -S.spoiled.fond : 0
  const sense = clamp(S.base + fromBattles + fromLoyalty + fromSpoiling, S.min, S.max)
  return { sense, spoiled, battles, fromBattles, fromLoyalty, fromSpoiling }
}

export function senseForTier(tier: AiTier): number {
  return S.tier[tier]
}

/** The range plan (§12.10) still works by tier: battle sense picks the tier it plans like. */
export function tierForSense(sense: number): AiTier {
  return sense >= S.expertFrom ? 'expert' : sense >= S.skilledFrom ? 'skilled' : 'rookie'
}

export type SenseReason = 'seasoned' | 'untrained' | 'loyal' | 'fickle' | 'spoiled'

/** Why it has the battle sense it has, for the screen (§4.1): the parts that count most. */
export function senseReasons(r: Sense): SenseReason[] {
  const W = S.why
  const out: SenseReason[] = []
  if (r.battles >= W.seasonedBattles) out.push('seasoned')
  else if (r.battles < W.untrainedBattles) out.push('untrained')
  if (r.fromLoyalty >= W.loyalFrom) out.push('loyal')
  else if (r.fromLoyalty <= -W.loyalFrom) out.push('fickle')
  if (r.spoiled > 0) out.push('spoiled')
  return out
}
