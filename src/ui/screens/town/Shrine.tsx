import { useMemo, useState } from 'preact/hooks'
import type { AwakenResult } from '../../../core/creation.ts'
import { findStored } from '../../../core/legacy.ts'
import { monsterFromRoll, rollShrine } from '../../../core/shrine.ts'
import { offeringsInBag } from '../../../core/unlocks.ts'
import { variantNameOf } from '../../../core/variants.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { ITEM_BY_ID } from '../../../data/items.ts'
import { fill } from '../../../data/text/format.ts'
import { SHRINE_TEASERS } from '../../../data/text/shrine.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { SHRINE } from '../../../data/tuning.ts'
import { BREED_IDS } from '../../../data/types.ts'
import { Confirm, Field, Segmented, TopBar } from '../../components/Controls.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SceneBanner } from '../../components/SceneBanner.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { navigate, navigateFrom } from '../../router.ts'
import { playSfx } from '../../../audio/player.ts'
import { showToast } from '../../store/appStore.ts'
import { attendVigil, awaken, game, offerAtShrine, randomPhrase, recreate, wakeStone } from '../../store/gameStore.ts'
import { startEdit, startEditActive } from '../../store/labStore.ts'

type Section = 'sing' | 'stones' | 'encyclopedia' | 'offerings'

/** §14.1 the Shrine of Echoes in play: two fields, Randomize, the stone's hum or teaser, Sleeping Stones and the Encyclopedia. */
export function ShrineScreen() {
  const t = UI_TEXT.shrine
  const g = game.value
  const [section, setSection] = useState<Section>('sing')
  const [phrase, setPhrase] = useState('')
  const [artist, setArtist] = useState('')
  const [result, setResult] = useState<AwakenResult | null>(null)
  const [offering, setOffering] = useState<string | null>(null)
  const unlocked = g?.unlocked ?? []
  const roll = useMemo(() => (phrase.trim() ? rollShrine(phrase, artist, unlocked) : null), [phrase, artist, unlocked.length])
  if (!g) return null
  const offerings = offeringsInBag(g)
  const o = UI_TEXT.offerings
  const offeringsLabel = g.unlocks.vigilOpen || offerings.some((x) => !x.awake) ? `${o.title}•` : o.title

  const sing = () => {
    const r = awaken(phrase, artist)
    if (r) {
      setResult(r)
      playSfx('stoneHum')
    }
  }

  const editNewborn = (id: string) => {
    if (g.monster?.id === id) {
      startEditActive(g.monster, [])
    } else {
      const stored = findStored(g, id)
      if (!stored) return
      startEdit({ id, monster: stored.monster, source: 'freezer', history: [], createdAt: 0, updatedAt: 0 })
    }
    navigateFrom('shrine', 'labEdit')
  }

  const again = () => {
    setResult(null)
    setPhrase('')
    setArtist('')
  }

  const teaserFor = (breed: string) => SHRINE_TEASERS[breed] ?? SHRINE_TEASERS.default!

  return (
    <main class="screen">
      <TopBar title={t.title} right={<span class="calstrip__money">{gold(g.money)}</span>} />
      <SceneBanner scene="shrine" />
      <Segmented
        options={[
          { value: 'sing', label: t.tabSing },
          { value: 'stones', label: `${t.stonesShort} (${g.sleepingStones.length})` },
          { value: 'encyclopedia', label: t.encyclopedia },
          { value: 'offerings', label: offeringsLabel },
        ]}
        value={section}
        onChange={setSection}
        label={t.title}
      />

      {section === 'sing' && !result && (
        <>
          <SpeakerCard speaker={t.mara} tone="muted">
            <p>{t.intro}</p>
          </SpeakerCard>
          <Field label={t.phrase}>
            <input class="input" value={phrase} maxLength={200} autoCapitalize="words" onInput={(e) => setPhrase((e.currentTarget as HTMLInputElement).value)} />
          </Field>
          <Field label={t.artist}>
            <input class="input" value={artist} maxLength={200} onInput={(e) => setArtist((e.currentTarget as HTMLInputElement).value)} />
          </Field>
          {roll ? (
            roll.mainLocked ? (
              <section class="card">
                <p>{t.sleeping}</p>
                <p class="muted small">{teaserFor(roll.mainBreed)}</p>
              </section>
            ) : (
              <div class="preview">
                <MonsterPortrait monster={monsterFromRoll(roll, 'preview')} size={120} label={roll.variantName} />
                <div class="preview__info">
                  <span class="preview__name">{roll.variantName}</span>
                  <span class="muted small">{roll.secret ? t.secretHum : fill(t.hums, { variant: roll.variantName })}</span>
                </div>
              </div>
            )
          ) : (
            <p class="empty">{t.quiet}</p>
          )}
          <div class="spacer" />
          <div class="actionbar">
            <button type="button" class="btn btn--half" onClick={() => setPhrase(randomPhrase())}>
              🎲 {t.randomize}
            </button>
            <button type="button" class="btn btn--primary btn--half" disabled={!roll} onClick={sing}>
              {t.awaken} · {t.free}
            </button>
          </div>
        </>
      )}

      {section === 'sing' && result && (
        <>
          {result.kind === 'born' && (
            <>
              <h2 class="heading center">{fill(t.born, { name: result.monster.name })}</h2>
              <div class="farewell__art">
                <MonsterPortrait monster={result.monster} size={200} expression="happy" live clip="idle_happy" />
              </div>
              <p class="center muted">{variantNameOf(result.monster)}</p>
              <SpeakerCard speaker={t.mara} tone="muted">
                <p>{fill(result.placed === 'ranch' ? t.bornRanch : t.bornFreezer, { name: result.monster.name })}</p>
              </SpeakerCard>
              <div class="spacer" />
              <div class="actionbar actionbar--stack">
                {result.placed === 'ranch' && (
                  <button type="button" class="btn btn--primary" onClick={() => navigate('ranch')}>
                    {t.toRanch}
                  </button>
                )}
                <div class="actions__row">
                  <button type="button" class="btn btn--half" onClick={() => editNewborn(result.monster.id)}>
                    ✏️ {t.editFirst}
                  </button>
                  <button type="button" class="btn btn--half btn--ghost" onClick={again}>
                    {t.again}
                  </button>
                </div>
              </div>
            </>
          )}
          {result.kind === 'sleeping' && (
            <>
              <section class="card">
                <p class="speaker">{t.mara}</p>
                <p>{t.sleeping}</p>
                <p class="muted">{teaserFor(result.roll.mainBreed)}</p>
                <p class="muted small">{t.sleepingSaved}</p>
              </section>
              <div class="spacer" />
              <div class="actionbar">
                <button type="button" class="btn btn--primary" onClick={again}>
                  {t.again}
                </button>
              </div>
            </>
          )}
          {result.kind === 'refused' && (
            <>
              <section class="card">
                <p class="notice">{result.reason === 'freezerFull' ? t.freezerFull : UI_TEXT.pellLab.freezeBusy}</p>
              </section>
              <div class="spacer" />
              <div class="actionbar">
                <button type="button" class="btn btn--primary" onClick={() => setResult(null)}>
                  {UI_TEXT.back}
                </button>
              </div>
            </>
          )}
        </>
      )}

      {section === 'stones' && (
        <>
          {g.sleepingStones.length === 0 && <p class="empty">{t.stonesEmpty}</p>}
          <div class="list">
            {g.sleepingStones.map((s, i) => {
              const awake = g.unlocked.includes(s.breed)
              return (
                <div key={`${s.phrase}|${s.artist}`} class="stone">
                  <span class="stone__body">
                    <span class="stone__phrase">{fill(t.stoneRow, { phrase: s.phrase, artist: s.artist ? ` · ${s.artist}` : '' })}</span>
                    <span class="muted small">{awake ? BREED_BY_ID[s.breed].name : SHRINE_TEASERS[s.breed] ?? SHRINE_TEASERS.default}</span>
                  </span>
                  <button
                    type="button"
                    class={`btn btn--small ${awake ? 'btn--primary' : ''}`}
                    disabled={!awake}
                    onClick={() => {
                      const r = wakeStone(i)
                      if (!r || r.refused) showToast(r?.refused === 'freezerFull' ? t.freezerFull : UI_TEXT.pellLab.freezeBusy)
                      else showToast(fill(r.placed === 'ranch' ? t.bornRanch : t.bornFreezer, { name: r.monster!.name }))
                    }}
                  >
                    {awake ? t.wake : t.stillAsleep}
                  </button>
                </div>
              )
            })}
          </div>
        </>
      )}

      {section === 'encyclopedia' && (
        <>
          <section class="card">
            <p>{fill(t.seen, { breeds: g.encyclopedia.breeds.length, total: BREED_IDS.length, variants: g.encyclopedia.variants.length })}</p>
            <p class="row row--wrap small muted">
              {g.encyclopedia.breeds.map((b) => (
                <span key={b} class="pill">
                  {BREED_BY_ID[b].name}
                </span>
              ))}
            </p>
          </section>
          {g.encyclopedia.phrases.length === 0 && <p class="empty">{fill(t.phrasesEmpty, { price: gold(SHRINE.encyclopediaPrice) })}</p>}
          <div class="list">
            {g.encyclopedia.phrases.map((p, i) => (
              <div key={`${p.phrase}|${p.artist}`} class="stone">
                <MonsterPortrait monster={monsterFromRoll(rollShrine(p.phrase, p.artist, g.unlocked), 'enc')} size={56} animate={false} />
                <span class="stone__body">
                  <span class="stone__phrase">
                    {p.name} · {variantNameOf(p)}
                  </span>
                  <span class="muted small">{fill(t.stoneRow, { phrase: p.phrase, artist: p.artist ? ` · ${p.artist}` : '' })}</span>
                </span>
                <button
                  type="button"
                  class="btn btn--small"
                  disabled={g.money < SHRINE.encyclopediaPrice}
                  onClick={() => {
                    const r = recreate(i)
                    if (!r || r.refused) showToast(r?.refused === 'money' ? t.noMoney : r?.refused === 'freezerFull' ? t.freezerFull : UI_TEXT.pellLab.freezeBusy)
                    else showToast(fill(t.recreated, { name: r.monster!.name }))
                  }}
                >
                  {fill(t.recreate, { price: gold(SHRINE.encyclopediaPrice) })}
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {section === 'offerings' && (
        <>
          <SpeakerCard speaker={t.mara} tone="muted">
            <p>{o.intro}</p>
          </SpeakerCard>
          {g.unlocks.vigilOpen && (
            <section class="card">
              <p class="field__label">{UI_TEXT.mail.kinds.vigil}</p>
              <p class="muted small">{o.vigilHint}</p>
              <button
                type="button"
                class="btn btn--primary"
                style={{ marginTop: 8 }}
                onClick={() => {
                  if (attendVigil()) showToast(o.vigilDone)
                }}
              >
                🏮 {o.vigil}
              </button>
            </section>
          )}
          {offerings.length === 0 && !g.unlocks.vigilOpen && <p class="empty">{o.none}</p>}
          <div class="list">
            {offerings.map((x) => (
              <div key={x.itemId} class="stone">
                <span class="stone__body">
                  <span class="stone__phrase">{ITEM_BY_ID[x.itemId]?.name ?? x.itemId}</span>
                  <span class="muted small">{x.awake ? fill(o.already, { breed: BREED_BY_ID[x.breed].name }) : SHRINE_TEASERS[x.breed] ?? SHRINE_TEASERS.default}</span>
                </span>
                <button type="button" class="btn btn--small btn--primary" disabled={x.awake} onClick={() => setOffering(x.itemId)}>
                  {fill(o.offer, { item: ITEM_BY_ID[x.itemId]?.name ?? x.itemId })}
                </button>
              </div>
            ))}
          </div>
          <Confirm
            open={offering !== null}
            text={offering ? fill(o.ask, { item: ITEM_BY_ID[offering]?.name ?? offering, breed: BREED_BY_ID[offerings.find((x) => x.itemId === offering)?.breed ?? 'puddlepup'].name }) : ''}
            confirmLabel={offering ? fill(o.offer, { item: ITEM_BY_ID[offering]?.name ?? offering }) : ''}
            onConfirm={() => {
              const item = offering
              setOffering(null)
              if (!item) return
              const r = offerAtShrine(item)
              if (r.refused || !r.breed) showToast(r.refused === 'awake' ? fill(o.already, { breed: BREED_BY_ID[(r.breed ?? 'puddlepup') as keyof typeof BREED_BY_ID].name }) : o.none)
              else showToast(fill(WREN.offered, { item: ITEM_BY_ID[item]?.name ?? item, breed: BREED_BY_ID[r.breed as keyof typeof BREED_BY_ID].name }))
            }}
            onCancel={() => setOffering(null)}
          />
        </>
      )}
    </main>
  )
}
