import { signal } from '@preact/signals'
import { dateOf } from '../../../core/calendar.ts'
import { encyclopediaRows, journeysDone, titleRows, variantRows } from '../../../core/journal.ts'
import { chainCount, chainStage } from '../../../core/unlocks.ts'
import { BREED_BY_ID, BREEDS } from '../../../data/breeds.ts'
import { SECRETS } from '../../../data/secrets.ts'
import { fill } from '../../../data/text/format.ts'
import { MONTH_NAMES } from '../../../data/text/labels.ts'
import { SHRINE_TEASERS } from '../../../data/text/shrine.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { TITLES } from '../../../data/tuning.ts'
import { UNLOCK_CHAINS } from '../../../data/types.ts'
import { Badge, Chips, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { showToast } from '../../store/appStore.ts'
import { game, wakeStone } from '../../store/gameStore.ts'

type Page = 'encyclopedia' | 'stones' | 'rumors' | 'records' | 'titles' | 'hall'

/** The open page survives a trip elsewhere. */
export const journalPage = signal<Page>('encyclopedia')

const t = UI_TEXT.journal

/** §18 the Journal: Encyclopedia, Sleeping Stones, Rumors, Records, Titles, Hall of Fame. All free actions. */
export function JournalScreen() {
  const g = game.value
  if (!g) return null
  const pages: { value: Page; label: string }[] = [
    { value: 'encyclopedia', label: t.pages.encyclopedia },
    { value: 'stones', label: `${t.pages.stones} (${g.sleepingStones.length})` },
    { value: 'rumors', label: t.pages.rumors },
    { value: 'records', label: t.pages.records },
    { value: 'titles', label: `${t.pages.titles} ${g.titles.length}/${titleRows(g).length}` },
    { value: 'hall', label: t.pages.hall },
  ]
  const page = journalPage.value
  return (
    <main class="screen">
      <TopBar title={t.title} />
      <div class="journal-tabs">
        <Chips options={pages} value={page} onChange={(v) => (journalPage.value = v)} label={t.title} />
      </div>
      {page === 'encyclopedia' && <EncyclopediaPage />}
      {page === 'stones' && <StonesPage />}
      {page === 'rumors' && <RumorsPage />}
      {page === 'records' && <RecordsPage />}
      {page === 'titles' && <TitlesPage />}
      {page === 'hall' && <HallPage />}
    </main>
  )
}

function EncyclopediaPage() {
  const g = game.value!
  const rows = encyclopediaRows(g)
  const variants = variantRows(g)
  return (
    <>
      <section class="card">
        <p>{fill(t.breedsOwned, { n: g.encyclopedia.breeds.length, total: BREEDS.length })}</p>
        <p class="muted small">
          {fill(t.variantsOwned, { n: g.encyclopedia.variants.length, total: SECRETS.length })} · {fill(t.combos, { n: g.encyclopedia.combos.length, goal: TITLES.collectorVariants })}
        </p>
      </section>
      <section class="card">
        {rows.map(({ breed, status }) => (
          <div class={`jrow ${status === 'asleep' ? 'jrow--off' : ''}`} key={breed.id}>
            <MonsterPortrait breed={breed.id} size={52} animate={false} class={status === 'asleep' ? 'jrow__portrait--asleep' : ''} label={status === 'asleep' ? t.unknownVariant : breed.name} />
            <span class="jrow__body">
              <span class="jrow__name">{status === 'asleep' ? t.unknownVariant : breed.name}</span>
              <span class="muted small">{status === 'asleep' ? (SHRINE_TEASERS[breed.id] ?? SHRINE_TEASERS.default) : breed.niche}</span>
            </span>
            <Badge tone={status === 'owned' ? 'pure' : 'muted'}>{t.status[status]}</Badge>
          </div>
        ))}
      </section>
      <section class="card">
        <p class="field__label">{t.pages.encyclopedia} · {fill(t.variantsOwned, { n: g.encyclopedia.variants.length, total: SECRETS.length })}</p>
        <p class="muted small">{t.secretHint}</p>
        {variants.map(({ secret, owned }) => (
          <div class={`jrow ${owned ? '' : 'jrow--off'}`} key={secret.id}>
            <span class="jrow__body">
              <span class="jrow__name">{owned ? `${secret.adjective} ${BREED_BY_ID[secret.breed].name}` : t.unknownVariant}</span>
              <span class="muted small">{owned ? secret.look : BREED_BY_ID[secret.breed].name}</span>
            </span>
          </div>
        ))}
      </section>
    </>
  )
}

function StonesPage() {
  const g = game.value!
  const s = UI_TEXT.shrine
  return (
    <>
      <p class="muted small center">{t.stonesHint}</p>
      {g.sleepingStones.length === 0 && <p class="empty">{s.stonesEmpty}</p>}
      <div class="list">
        {g.sleepingStones.map((stone, i) => {
          const awake = g.unlocked.includes(stone.breed)
          return (
            <div key={`${stone.phrase}|${stone.artist}`} class="stone">
              <span class="stone__body">
                <span class="stone__phrase">{fill(s.stoneRow, { phrase: stone.phrase, artist: stone.artist ? ` · ${stone.artist}` : '' })}</span>
                <span class="muted small">{awake ? BREED_BY_ID[stone.breed].name : (SHRINE_TEASERS[stone.breed] ?? SHRINE_TEASERS.default)}</span>
              </span>
              <button
                type="button"
                class={`btn btn--small ${awake ? 'btn--primary' : ''}`}
                disabled={!awake}
                onClick={() => {
                  const r = wakeStone(i)
                  if (!r || r.refused) showToast(r?.refused === 'freezerFull' ? s.freezerFull : UI_TEXT.pellLab.freezeBusy)
                  else showToast(fill(r.placed === 'ranch' ? s.bornRanch : s.bornFreezer, { name: r.monster!.name }))
                }}
              >
                {awake ? s.wake : s.stillAsleep}
              </button>
            </div>
          )
        })}
      </div>
    </>
  )
}

function RumorsPage() {
  const g = game.value!
  return (
    <section class="card">
      {UNLOCK_CHAINS.map((chain) => {
        const stage = chainStage(g, chain)
        const r = UI_TEXT.rumors[chain]
        const n = chainCount(g, chain) ?? 0
        const text = stage === 0 ? t.rumorStages.unknown : stage === 1 ? r.heard : stage === 2 ? fill(r.progress, { n }) : r.done
        return (
          <div class={`jrow ${stage === 0 ? 'jrow--off' : ''}`} key={chain}>
            <span class="jrow__body">
              <span class="jrow__name">
                {stage === 0 ? t.unknownVariant : r.name} {stage === 3 && <Badge tone="pure">{t.rumorStages.done}</Badge>}
              </span>
              <span class="small">{text}</span>
            </span>
          </div>
        )
      })}
    </section>
  )
}

function RecordsPage() {
  const g = game.value!
  const r = g.records
  const rows: [string, string][] = [
    [t.records.bestTotal, r.bestTotal > 0 ? fill(t.records.by, { n: r.bestTotal, name: r.bestTotalName }) : t.records.none],
    [t.records.oldest, r.oldestWeeks > 0 ? fill(t.records.by, { n: fill(t.records.weeks, { n: r.oldestWeeks }), name: r.oldestName }) : t.records.none],
    [t.records.cupsWon, String(r.cupsWon)],
    [t.records.expeditions, String(r.expeditionsDone)],
    [t.records.journeys, String(journeysDone(g))],
    [t.records.stones, String(r.stonesWoken)],
    [t.records.generation, String(r.highestGeneration)],
    [t.records.sweets, String(g.counters.sweetsEaten)],
    [t.records.sheets, String(g.counters.sheetsLearned)],
    [t.records.drills, String(g.counters.drillsDone)],
  ]
  return (
    <section class="card">
      {rows.map(([label, value]) => (
        <div class="jrow" key={label}>
          <span class="jrow__body">
            <span class="muted small">{label}</span>
            <span class="jrow__name">{value}</span>
          </span>
        </div>
      ))}
    </section>
  )
}

function TitlesPage() {
  const g = game.value!
  const rows = titleRows(g)
  return (
    <section class="card">
      <p class="muted small">{fill(t.titlesCount, { n: g.titles.length, total: rows.length })}</p>
      {rows.map(({ id, earned }) => (
        <div class={`jrow ${earned ? '' : 'jrow--off'}`} key={id}>
          <span class="jrow__body">
            <span class="jrow__name">{id}</span>
            <span class="muted small">{UI_TEXT.titles[id]}</span>
          </span>
          <Badge tone={earned ? 'pure' : 'muted'}>{earned ? t.earned : t.notYet}</Badge>
        </div>
      ))}
    </section>
  )
}

function HallPage() {
  const g = game.value!
  return (
    <section class="card">
      {g.hallOfFame.length === 0 && <p class="muted">{t.hallEmpty}</p>}
      {g.hallOfFame.map((h, i) => (
        <div class="jrow" key={i}>
          <MonsterPortrait monster={h.monster} size={56} animate={false} />
          <span class="jrow__body">
            <span class="jrow__name">{h.monster.name}</span>
            <span class="muted small">
              {UI_TEXT.ranch.year.replace('{year}', String(dateOf(h.week).year))} · {MONTH_NAMES[dateOf(h.week).month - 1]} · {UI_TEXT.lineage.generation.replace('{n}', String(h.monster.generation))}
            </span>
          </span>
        </div>
      ))}
    </section>
  )
}
