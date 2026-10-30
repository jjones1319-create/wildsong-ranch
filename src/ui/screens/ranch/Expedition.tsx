import { useEffect, useMemo, useRef, useState } from 'preact/hooks'
import { expeditionMap, movesFrom, obstacleOf, visibleKind, type ExpeditionMap, type MapNode } from '../../../core/expedition.ts'
import type { ExpeditionState } from '../../../core/state.ts'
import { EXPEDITION_SITE_BY_ID } from '../../../data/expeditions.ts'
import { ITEM_BY_ID } from '../../../data/items.ts'
import { TECHNIQUE_BY_ID } from '../../../data/techniques.ts'
import { fill } from '../../../data/text/format.ts'
import { STAT_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { EXPEDITION } from '../../../data/tuning.ts'
import type { ExpeditionSite, NodeKind } from '../../../data/types.ts'
import { Confirm, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard } from '../../components/RanchBits.tsx'
import { navigate } from '../../router.ts'
import { endWeekNow, expeditionDetour, expeditionMove, expeditionRetreat, expeditionTurnBack, game } from '../../store/gameStore.ts'

const t = UI_TEXT.expedition

const COL = 92
const ROW = 84
const PAD_X = 46
const PAD_Y = 34

const GLYPHS: Record<NodeKind, string> = { start: '🚩', path: '·', obstacle: '⛰', search: '🔎', hidden: '🔍', fog: '🌫', treasure: '💰', event: '✨', camp: '⛺' }
const EVENT_GLYPHS = { 'strange-chest': '🧰', archive: '📚', 'crystal-heart': '💎', 'sky-puzzle': '🪁' } as const
const OBSTACLE_GLYPHS: Record<string, string> = { POW: '🪨', INT: '🧩', SKI: '🪤', SPD: '🌉', DEF: '🌬', LIF: '🌊' }

function nodeLabel(node: MapNode, kind: NodeKind, site: ExpeditionSite): string {
  if (kind === 'obstacle') return obstacleOf(site, node)?.name ?? t.screen.nodes.obstacle
  if (kind === 'event') return t.screen.nodes[site.event]
  return t.screen.nodes[kind]
}

function nodeGlyph(node: MapNode, kind: NodeKind, site: ExpeditionSite): string {
  if (kind === 'obstacle') return OBSTACLE_GLYPHS[obstacleOf(site, node)?.stat ?? ''] ?? GLYPHS.obstacle
  if (kind === 'event') return EVENT_GLYPHS[site.event]
  return GLYPHS[kind]
}

/** A log line → Tomas's sentence, with the item or obstacle filled in. */
function tomasLine(entry: string, name: string): string {
  const [key, detail = ''] = entry.split('|') as [keyof typeof t.tomas_lines, string?]
  const template = t.tomas_lines[key] ?? ''
  return fill(template, { name, item: detail, obstacle: detail })
}

function lootName(id: string, qty: number): string {
  const name = ITEM_BY_ID[id]?.name ?? id
  return qty > 1 ? `${name} ×${qty}` : name
}

function position(map: ExpeditionMap, node: MapNode): { x: number; y: number } {
  const size = map.nodes.filter((n) => n.layer === node.layer).length
  const maxRows = Math.max(...Array.from({ length: map.layers + 2 }, (_, l) => map.nodes.filter((n) => n.layer === l).length))
  const height = PAD_Y * 2 + (maxRows - 1) * ROW
  return { x: PAD_X + node.layer * COL, y: height / 2 + (node.index - (size - 1) / 2) * ROW }
}

/** §17 the node map: tap a lit stop to walk there; stamina, Tomas, the loot so far, Retreat and the summary. */
export function ExpeditionScreen() {
  const g = game.value
  const [askRetreat, setAskRetreat] = useState(false)
  const scroller = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!g || !g.monster || !g.expedition) navigate('ranch')
  }, [g === null, g?.expedition === null])
  const e = g?.expedition ?? null
  const map = useMemo(() => (e ? expeditionMap(e) : null), [e?.site, e?.seed])
  useEffect(() => {
    const box = scroller.current
    if (!box || !map || !e) return
    const here = position(map, map.nodes[e.at]!)
    box.scrollTo({ left: Math.max(0, here.x - box.clientWidth / 2), behavior: 'smooth' })
  }, [e?.at])
  if (!g || !g.monster || !e || !map) return null
  const m = g.monster
  const site = EXPEDITION_SITE_BY_ID[e.site]
  const moves = movesFrom(g)
  const reachable = new Set(moves.map((x) => x.to))
  const maxRows = Math.max(...Array.from({ length: map.layers + 2 }, (_, l) => map.nodes.filter((n) => n.layer === l).length))
  const width = PAD_X * 2 + (map.layers + 1) * COL
  const height = PAD_Y * 2 + (maxRows - 1) * ROW + 28
  const blocked = e.blockedAt !== null ? map.nodes[e.blockedAt]! : null
  const blockedOb = blocked ? obstacleOf(site, blocked) : null
  const lastLine = e.log[e.log.length - 1] ?? 'start'
  const foundCount = e.loot.length + e.sheets.length

  const walk = (id: number) => {
    if (!reachable.has(id)) return
    expeditionMove(id)
  }

  if (e.ended) {
    return (
      <main class="screen">
        <TopBar title={fill(t.screen.summaryTitle, { site: site.name })} onBack={() => navigate('ranch')} />
        <div class="farewell__art">
          <MonsterPortrait monster={m} size={160} expression={e.ended === 'exhausted' ? 'sleepy' : 'happy'} live clip={e.ended === 'exhausted' ? 'sleep' : 'idle_happy'} />
        </div>
        <SpeakerCard speaker={t.tomas} tone="muted">
          <p>{tomasLine(lastLine, m.name)}</p>
          <p class="muted small">{fill(t.screen.ended[e.ended], { name: m.name })}</p>
        </SpeakerCard>
        <section class="card">
          <p class="field__label">{t.screen.found}</p>
          {foundCount === 0 && !e.keyFound && <p class="muted">{t.screen.nothingYet}</p>}
          {e.loot.map((l) => (
            <p key={l.id}>{lootName(l.id, l.qty)}</p>
          ))}
          {e.sheets.length > 0 && (
            <p class="muted small">
              {t.screen.sheets}: {e.sheets.map((id) => TECHNIQUE_BY_ID[id]?.name ?? id).join(' · ')}
            </p>
          )}
          {e.keyFound === 'lootlid' && (
            <p class="notice notice--ok">
              {t.screen.lootlid} {t.screen.lootlidWhere[e.lootlidPlaced ?? 'none']}
            </p>
          )}
          {e.keyFound === 'brass-blueprint' && <p class="notice notice--ok">{t.screen.blueprint}</p>}
          <p class="muted small">{fill(t.screen.afterEffects, { fatigue: EXPEDITION.after.fatigue, stress: EXPEDITION.after.stress })}</p>
          {e.loot.some((l) => (ITEM_BY_ID[l.id]?.sell ?? null) !== null) && <p class="muted small">{t.screen.sellHint}</p>}
        </section>
        <div class="spacer" />
        <div class="actionbar">
          <button
            type="button"
            class="btn btn--primary"
            onClick={() => {
              endWeekNow()
              navigate('ranch')
            }}
          >
            {t.screen.done}
          </button>
        </div>
      </main>
    )
  }

  return (
    <main class="screen">
      <TopBar title={`${t.title} · ${site.name}`} onBack={() => navigate('ranch')} />
      <div class="bar bar--stamina">
        <span class="bar__label">{t.screen.stamina}</span>
        <span class="bar__track" role="img" aria-label={`${t.screen.stamina}: ${e.stamina} / ${e.staminaMax}`}>
          <span class="bar__fill" style={{ width: `${Math.min(100, (e.stamina / e.staminaMax) * 100)}%` }} />
        </span>
        <span class="bar__word">{fill(t.screen.staminaOf, { n: e.stamina, max: e.staminaMax })}</span>
      </div>

      <div class="expmap" ref={scroller}>
        <div class="expmap__inner" style={{ width, height }}>
          <svg class="expmap__lines" width={width} height={height} aria-hidden="true">
            {map.nodes.flatMap((n) =>
              n.next.map((edge) => {
                const a = position(map, n)
                const b = position(map, map.nodes[edge.to]!)
                const lit = n.id === e.at && reachable.has(edge.to)
                // The cost sits a little off the line, on the side away from the labels under the stops.
                const len = Math.hypot(b.x - a.x, b.y - a.y) || 1
                const ox = (-(b.y - a.y) / len) * 11
                const oy = ((b.x - a.x) / len) * 11
                return (
                  <g key={`${n.id}-${edge.to}`}>
                    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} class={`expmap__edge ${lit ? 'expmap__edge--lit' : ''}`} />
                    {lit && (
                      <text x={(a.x + b.x) / 2 + Math.abs(ox)} y={(a.y + b.y) / 2 - Math.abs(oy) - 4} class="expmap__cost" text-anchor="middle">
                        {fill(t.screen.cost, { n: edge.cost })}
                      </text>
                    )}
                  </g>
                )
              }),
            )}
          </svg>
          {map.nodes.map((n) => {
            const kind = visibleKind(n, m, site)
            const p = position(map, n)
            const here = n.id === e.at
            const lit = reachable.has(n.id)
            const done = e.searched.includes(n.id) || e.passed.includes(n.id) || (e.visited.includes(n.id) && !here)
            const label = nodeLabel(n, kind, site)
            return (
              <button
                key={n.id}
                type="button"
                class={`expnode ${here ? 'expnode--here' : ''} ${lit ? 'expnode--lit' : ''} ${done ? 'expnode--done' : ''}`}
                style={{ left: p.x, top: p.y }}
                disabled={!lit}
                aria-label={`${label}${here ? ` (${t.screen.legend.here})` : lit ? ` (${t.screen.legend.lit})` : ''}`}
                onClick={() => walk(n.id)}
              >
                <span class="expnode__glyph" aria-hidden="true">
                  {here ? '🐾' : nodeGlyph(n, kind, site)}
                </span>
                <span class="expnode__label">{label}</span>
              </button>
            )
          })}
        </div>
      </div>

      <SpeakerCard speaker={t.tomas} tone="muted">
        <p>{tomasLine(lastLine, m.name)}</p>
        {blocked && blockedOb ? (
          <p class="notice">{fill(t.screen.blockedHint, { obstacle: blockedOb.name, stat: STAT_NAMES[blockedOb.stat], n: blockedOb.threshold, name: m.name, have: m.stats[blockedOb.stat] })}</p>
        ) : (
          <p class="muted small">{t.screen.tapToMove}</p>
        )}
      </SpeakerCard>

      <section class="card">
        <p class="field__label">{t.screen.found}</p>
        {foundCount === 0 && !e.keyFound && <p class="muted small">{t.screen.nothingYet}</p>}
        <p class="small">
          {[...e.loot.map((l) => lootName(l.id, l.qty)), ...e.sheets.map((id) => `${TECHNIQUE_BY_ID[id]?.name ?? id} Songsheet`), ...(e.keyFound === 'lootlid' ? ['Lootlid'] : []), ...(e.keyFound === 'brass-blueprint' ? [ITEM_BY_ID['brass-blueprint']!.name] : [])].join(' · ')}
        </p>
      </section>

      <div class="spacer" />
      <div class="actionbar">
        {blocked ? (
          <>
            <button type="button" class="btn btn--primary btn--half" onClick={expeditionDetour}>
              {fill(t.screen.detour, { n: EXPEDITION.detourCost })}
            </button>
            <button type="button" class="btn btn--half" onClick={expeditionTurnBack}>
              {t.screen.turnBack}
            </button>
          </>
        ) : (
          <button type="button" class="btn btn--ghost" onClick={() => setAskRetreat(true)}>
            {t.screen.retreat}
          </button>
        )}
      </div>
      <Confirm
        open={askRetreat}
        text={t.screen.retreatAsk}
        confirmLabel={t.screen.retreat}
        onConfirm={() => {
          setAskRetreat(false)
          expeditionRetreat()
        }}
        onCancel={() => setAskRetreat(false)}
      />
    </main>
  )
}

/** For tests and the ranch: a short description of the trip in progress. */
export function tripStatus(e: ExpeditionState): string {
  return fill(t.weekLine, { week: e.weekNo, site: EXPEDITION_SITE_BY_ID[e.site].name })
}
