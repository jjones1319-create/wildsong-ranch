import { friendPoints, friendsOf, tierOf, type FriendTier } from '../../../core/friends.ts'
import type { GameState } from '../../../core/state.ts'
import { fill } from '../../../data/text/format.ts'
import { HERD_TEXT } from '../../../data/text/herd.ts'
import { settings } from '../../store/appStore.ts'

const t = HERD_TEXT.friends

/** Three hearts, filled by the tier (Friends ♥♡♡, Close ♥♥♡, Best ♥♥♥). */
export function hearts(tier: FriendTier): string {
  return '♥'.repeat(tier) + '♡'.repeat(3 - tier)
}

/** One friendship: hearts, the tier's name, and the points in Breeder's Lens. */
function FriendLine({ name, points }: { name: string; points: number }) {
  const tier = tierOf(points)
  const lens = settings.value.transparency === 'lens'
  return (
    <>
      <span>
        <b>{name}</b>
        <span class="muted small">
          {' · '}
          {t.tiers[tier]}
          {lens ? ` · ${fill(t.points, { n: points })}` : ''}
        </span>
      </span>
      <span class="friends__hearts" role="img" aria-label={t.tiers[tier]}>
        {hearts(tier)}
      </span>
    </>
  )
}

/** §6.11 the herd sheet: a ranch-mate's friendship with the star. */
export function StarFriendship({ g, id }: { g: GameState; id: string }) {
  if (!g.monster) return null
  return (
    <div class="herdsheet__friend friends__row">
      <FriendLine name={fill(t.withStar, { name: g.monster.name })} points={friendPoints(g, g.monster.id, id)} />
    </div>
  )
}

/** §6.11 the Monster Card's Friends section: this monster's friends, closest first. */
export function FriendsSection({ g, id, name }: { g: GameState; id: string; name: string }) {
  const list = friendsOf(g, id)
  // A one-monster ranch with no old friendships keeps its card as it was.
  if (list.length === 0 && g.ranchmates.length === 0) return null
  return (
    <section class="card" aria-label={t.title}>
      <p class="field__label">{t.title}</p>
      {list.length === 0 ? (
        <p class="muted small">{fill(t.none, { name })}</p>
      ) : (
        <ul class="friends">
          {list.map((f) => (
            <li key={f.id} class="friends__row">
              <FriendLine name={f.name} points={f.points} />
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
