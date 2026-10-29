import { signal } from '@preact/signals'
import { useState } from 'preact/hooks'
import { catalystEffect, compatTier, compatibility, fusionOutcomes, outcomeKnown, type FusionResult } from '../../../core/fusion.ts'
import { countOf } from '../../../core/items.ts'
import { duplicateMonster } from '../../../core/lab.ts'
import { canReceiveHeartstone, elderMentorUsedThisMonth, elderSite, freezerFull, fusionCandidates, heartstoneCap, heartstoneGrant, ranchBusy, findStored } from '../../../core/legacy.ts'
import { canVisitGarden } from '../../../core/upgrades.ts'
import { totalStats, type Monster } from '../../../core/monster.ts'
import { say } from '../../../core/report.ts'
import type { GameState, Heartstone, MemorialEntry } from '../../../core/state.ts'
import { variantNameOf } from '../../../core/variants.ts'
import { BREED_BY_ID } from '../../../data/breeds.ts'
import { ITEMS, ITEM_BY_ID } from '../../../data/items.ts'
import { TRAIT_BY_ID } from '../../../data/traits.ts'
import { JOURNEY_SITE_BY_ID } from '../../../data/journeys.ts'
import { fill } from '../../../data/text/format.ts'
import { FAMILY_LABELS, STAT_NAMES } from '../../../data/text/labels.ts'
import { UI_TEXT } from '../../../data/text/ui.ts'
import { WREN } from '../../../data/text/wren.ts'
import { FREEZER, FUSION, HEARTSTONE, JOURNEY, RANGES, UPGRADES } from '../../../data/tuning.ts'
import { STAT_KEYS, type BreedId } from '../../../data/types.ts'
import { Badge, Chips, Confirm, Field, Select, Sheet, TopBar } from '../../components/Controls.tsx'
import { MonsterCard } from '../../components/MonsterCard.tsx'
import { MonsterPortrait } from '../../components/MonsterPortrait.tsx'
import { SpeakerCard, gold } from '../../components/RanchBits.tsx'
import { now } from '../../lib/clock.ts'
import { newId } from '../../lib/ids.ts'
import { navigateFrom } from '../../router.ts'
import { showToast, upsertEntry } from '../../store/appStore.ts'
import { editMemorial, freezeActive, fuse, game, giveBlueprint, giveHeartstone, makeActive, releaseStored, visitGarden } from '../../store/gameStore.ts'
import { listFreezer, selected, startEdit, startEditActive, type Listed } from '../../store/labStore.ts'

type Tab = 'freezer' | 'fusion' | 'memorial' | 'heartstones' | 'elders'

/** The open tab survives a trip to the editor or the Monster Card. */
export const pellTab = signal<Tab>('freezer')

const t = UI_TEXT.pellLab

/** §15, §16, §7: Dr. Pell's Lab. Freezer · Fusion · Memorial · Heartstones · (Elder Grove). */
export function PellLabScreen() {
  const g = game.value
  if (!g) return null
  const elders = g.difficulty === 'Gentle' || g.elderGrove.length > 0
  const tabs: { value: Tab; label: string }[] = [
    { value: 'freezer', label: `${t.tabs.freezer} ${g.freezer.length}/${FREEZER.slots}` },
    { value: 'fusion', label: t.tabs.fusion },
    { value: 'memorial', label: `${t.tabs.memorial} ${g.memorial.length}` },
    { value: 'heartstones', label: `${t.tabs.heartstones} ${g.heartstones.length}` },
    ...(elders ? [{ value: 'elders' as const, label: `${t.tabs.elders} ${g.elderGrove.length}` }] : []),
  ]
  const tab = tabs.some((x) => x.value === pellTab.value) ? pellTab.value : 'freezer'
  return (
    <main class="screen">
      <TopBar title={t.title} right={<span class="calstrip__money">{gold(g.money)}</span>} />
      <div class="pell-tabs">
        <Chips options={tabs} value={tab} onChange={(v) => (pellTab.value = v)} label={t.title} />
      </div>
      {tab === 'freezer' && <FreezerTab g={g} />}
      {tab === 'fusion' && <FusionTab g={g} />}
      {tab === 'memorial' && <MemorialTab g={g} />}
      {tab === 'heartstones' && <HeartstonesTab g={g} />}
      {tab === 'elders' && <EldersTab g={g} />}
    </main>
  )
}

/* ---------- a stored monster's action sheet (Freezer and Elder Grove) ---------- */

function StoredSheet({ listed, onClose }: { listed: Listed | null; onClose: () => void }) {
  const g = game.value
  const [confirmActive, setConfirmActive] = useState(false)
  if (!listed || !g) return null
  const m = listed.monster
  const go = (target: 'labView' | 'labEdit' | 'labExport') => {
    selected.value = { source: 'freezer', id: m.id }
    if (target === 'labEdit') startEdit(listed)
    onClose()
    navigateFrom('pell', target)
  }
  const activate = () => {
    setConfirmActive(false)
    const refused = makeActive(m.id)
    onClose()
    if (refused === 'busy') showToast(t.freezeBusy)
    else if (refused === 'full') showToast(t.freezeFull)
    else if (!refused) showToast(fill(t.madeActive, { name: m.name }))
  }
  const toLibrary = async () => {
    const when = now()
    await upsertEntry({ monster: structuredClone(m), history: [], createdAt: when, updatedAt: when })
    releaseStored(m.id)
    onClose()
    showToast(fill(t.movedToLibrary, { name: m.name }))
  }
  return (
    <>
      <Sheet open={!confirmActive} title={m.name} onClose={onClose}>
        <div class="sheet__actions">
          <button type="button" class="btn btn--primary" onClick={() => setConfirmActive(true)}>
            {t.actions.makeActive}
          </button>
          <button type="button" class="btn" onClick={() => go('labView')}>
            {t.actions.view}
          </button>
          <button type="button" class="btn" onClick={() => go('labEdit')}>
            ✏️ {t.actions.edit}
          </button>
          <button type="button" class="btn" onClick={() => go('labExport')}>
            {t.actions.export}
          </button>
          <button type="button" class="btn btn--ghost" onClick={() => void toLibrary()}>
            {t.actions.toLibrary}
          </button>
          <button type="button" class="btn btn--ghost" onClick={onClose}>
            {t.actions.cancel}
          </button>
        </div>
      </Sheet>
      <Confirm
        open={confirmActive}
        text={g.monster ? fill(t.makeActiveAsk, { name: m.name, current: g.monster.name }) : fill(t.makeActiveAskEmpty, { name: m.name })}
        confirmLabel={t.actions.makeActive}
        onConfirm={activate}
        onCancel={() => setConfirmActive(false)}
      />
    </>
  )
}

/* ---------- Freezer ---------- */

function FreezerTab({ g }: { g: GameState }) {
  const [sheetFor, setSheetFor] = useState<Listed | null>(null)
  const [confirmFreeze, setConfirmFreeze] = useState(false)
  const [askBlueprint, setAskBlueprint] = useState(false)
  const rows = listFreezer().filter((l) => l.badge !== 'elder')
  const hasBlueprint = countOf(g.inventory, 'brass-blueprint') > 0 && !g.unlocked.includes('gearhoot')
  const handBlueprint = () => {
    setAskBlueprint(false)
    const refused = giveBlueprint()
    if (!refused) showToast(UI_TEXT.offerings.blueprintDone)
  }
  const busy = ranchBusy(g)
  const full = freezerFull(g)
  const freeze = () => {
    setConfirmFreeze(false)
    const name = g.monster?.name ?? ''
    const refused = freezeActive()
    if (!refused) showToast(fill(t.frozen, { name }))
    else if (refused === 'busy') showToast(t.freezeBusy)
    else if (refused === 'full') showToast(t.freezeFull)
  }
  return (
    <>
      <SpeakerCard speaker={UI_TEXT.pell} tone="muted">
        <p>{t.welcome}</p>
        <p class="muted small">{fill(t.slots, { n: g.freezer.length, max: FREEZER.slots })}</p>
      </SpeakerCard>
      {hasBlueprint && (
        <button type="button" class="btn btn--primary" onClick={() => setAskBlueprint(true)}>
          📐 {UI_TEXT.offerings.blueprint}
        </button>
      )}
      {g.monster && !g.ended && (
        <button type="button" class="btn" disabled={busy || full} onClick={() => setConfirmFreeze(true)}>
          ❄️ {fill(t.freezeActive, { name: g.monster.name })}
        </button>
      )}
      {g.monster && (busy || full) && <p class="muted small center">{busy ? t.freezeBusy : t.freezeFull}</p>}
      {rows.length === 0 && <p class="empty">{t.empty}</p>}
      <div class="list">
        {rows.map((l) => (
          <MonsterCard key={l.id} listed={l} onTap={setSheetFor} />
        ))}
      </div>
      <StoredSheet listed={sheetFor} onClose={() => setSheetFor(null)} />
      <Confirm open={confirmFreeze} text={g.monster ? say('freezeAsk', t.freezeAsk, g.monster).text : ''} confirmLabel={`❄️ ${t.tabs.freezer}`} onConfirm={freeze} onCancel={() => setConfirmFreeze(false)} />
      <Confirm open={askBlueprint} text={UI_TEXT.offerings.blueprintAsk} confirmLabel={UI_TEXT.offerings.blueprint} onConfirm={handBlueprint} onCancel={() => setAskBlueprint(false)} />
    </>
  )
}

/* ---------- Fusion ---------- */

function ParentSlot({ label, monster, onOpen }: { label: string; monster: Monster | null; onOpen: () => void }) {
  return (
    <button type="button" class={`pick ${monster ? 'pick--set' : ''}`} onClick={onOpen}>
      {monster ? <MonsterPortrait monster={monster} size={72} animate={false} /> : <span style={{ width: 72, textAlign: 'center', fontSize: '2em' }}>？</span>}
      <span class="pick__body">
        <span class="pick__label">{label}</span>
        <span class="pick__name">{monster ? monster.name : t.pickParent}</span>
        {monster && (
          <span class="muted small">
            {variantNameOf(monster)} · {UI_TEXT.lab.total} {totalStats(monster.stats)}
          </span>
        )}
      </span>
    </button>
  )
}

function FusionTab({ g }: { g: GameState }) {
  const cands = fusionCandidates(g)
  const [id1, setId1] = useState<string | null>(null)
  const [id2, setId2] = useState<string | null>(null)
  const [picking, setPicking] = useState<1 | 2 | null>(null)
  const [catalyst, setCatalyst] = useState<string>('none')
  const [confirm, setConfirm] = useState(false)
  const [born, setBorn] = useState<{ result: FusionResult; placed: 'ranch' | 'freezer' } | null>(null)
  const m1 = cands.find((c) => c.monster.id === id1)?.monster ?? null
  const m2 = cands.find((c) => c.monster.id === id2)?.monster ?? null
  const catalysts = ITEMS.filter((i) => i.category === 'catalyst' && (g.inventory[i.id] ?? 0) > 0)
  const catalystId = catalyst === 'none' || !catalysts.some((c) => c.id === catalyst) ? null : catalyst
  const seal = catalystEffect(catalystId).lineageSeal
  const outcomes = m1 && m2 ? fusionOutcomes(m1, m2, g.unlocked, seal) : []
  const top = outcomes[0]
  // A 35/35 tie has no single most likely breed.
  const topRow = top && outcomes[1]?.pct !== top.pct ? 0 : -1
  const compat = m1 && m2 && top ? compatibility(m1, m2, top.breed) : null
  const known = (o: (typeof outcomes)[number]) => outcomeKnown(o, g.fusionFinds)
  const nameOf = (o: (typeof outcomes)[number]) => (known(o) ? BREED_BY_ID[o.breed].name : t.hidden)
  const sealWasted = seal && m1 !== null && !g.unlocked.includes(m1.mainBreed)
  const toRanch = g.monster === null && !g.ended
  const whereText = toRanch ? t.whereRanch : t.whereFreezer

  const doFuse = () => {
    setConfirm(false)
    if (!id1 || !id2) return
    const r = fuse(id1, id2, catalystId)
    if (!r || r.refused) {
      showToast(r?.refused ? t.refused[r.refused] : t.freezeBusy)
      return
    }
    setBorn({ result: r.result!, placed: r.placed! })
    setId1(null)
    setId2(null)
    setCatalyst('none')
  }

  const editBaby = () => {
    if (!born) return
    const id = born.result.baby.id
    const current = game.value
    if (!current) return
    if (current.monster?.id === id) startEditActive(current.monster, [])
    else {
      const stored = findStored(current, id)
      if (!stored) return
      startEdit({ id, monster: stored.monster, source: 'freezer', history: [], createdAt: 0, updatedAt: 0 })
    }
    navigateFrom('pell', 'labEdit')
  }

  if (born) {
    const baby = born.result.baby
    const [pair] = (born.result.outcome.key ?? '').split('>')
    const [a, b] = (pair ?? '').split('+') as [BreedId, BreedId]
    const headStartTotal = STAT_KEYS.reduce((sum, k) => sum + born.result.headStart[k], 0)
    const inheritedName = baby.inheritedTrait ? TRAIT_BY_ID[baby.inheritedTrait].name : null
    return (
      <>
        <h2 class="heading center">{fill(t.born, { name: baby.name })}</h2>
        <div class="farewell__art">
          <MonsterPortrait monster={baby} size={200} expression="happy" />
        </div>
        <SpeakerCard speaker={UI_TEXT.pell}>
          <p>{fill(t.bornLine, { variant: variantNameOf(baby), gen: baby.generation })}</p>
          <p class="muted">
            {fill(t.compat, { m: born.result.compat })} · {t.comments[born.result.tier]}
          </p>
          {headStartTotal > 0 && <p class="muted small">{fill(t.headStart, { n: headStartTotal })}</p>}
          {inheritedName && <p class="muted small">{fill(t.inheritedTrait, { trait: inheritedName })}</p>}
          {born.result.newFind && <p class="notice">{fill(t.newRecipe, { a: BREED_BY_ID[a].name, b: BREED_BY_ID[b].name, breed: BREED_BY_ID[baby.mainBreed].name })}</p>}
          <p class="muted small">{fill(t.bornAt, { where: born.placed === 'ranch' ? t.bornRanch : t.bornFreezer })}</p>
        </SpeakerCard>
        <SpeakerCard speaker={UI_TEXT.wren} tone="muted">
          <p>{born.result.outcome.source === 'surprise' ? say('fusedSurprise', WREN.fusedSurprise, baby).text : say('fused', WREN.fused, baby).text}</p>
        </SpeakerCard>
        <div class="spacer" />
        <div class="actionbar">
          <button type="button" class="btn btn--primary btn--half" onClick={() => setBorn(null)}>
            {t.done}
          </button>
          <button type="button" class="btn btn--half" onClick={editBaby}>
            ✏️ {t.editFirst}
          </button>
        </div>
      </>
    )
  }

  return (
    <>
      <SpeakerCard speaker={UI_TEXT.pell} tone="muted">
        <p>{t.fusionIntro}</p>
      </SpeakerCard>
      {cands.length < 2 && <p class="notice">{t.needTwoFrozen}</p>}
      <div class="parents">
        <ParentSlot label={t.parentA} monster={m1} onOpen={() => setPicking(1)} />
        <ParentSlot label={t.parentB} monster={m2} onOpen={() => setPicking(2)} />
      </div>
      <Select
        label={t.catalyst}
        value={catalystId ?? 'none'}
        options={[{ value: 'none', label: t.noCatalyst }, ...catalysts.map((c) => ({ value: c.id, label: `${c.name} ×${g.inventory[c.id]}` }))]}
        onChange={setCatalyst}
        hint={fill(t.catalystHint, { shard: FUSION.shardStat, amber: ITEM_BY_ID['amber-charm']?.effect.kind === 'catalyst' ? ITEM_BY_ID['amber-charm'].effect.lifespan : 20 })}
      />
      {sealWasted && <p class="muted small">{t.sealWasted}</p>}
      {m1 && m2 && (
        <section class="card">
          <p class="field__label">{t.odds}</p>
          <div class="odds">
            {outcomes.map((o, i) => (
              <div key={o.breed} class={`odds__row ${i === topRow ? 'odds__row--top' : ''} ${o.source === 'surprise' ? 'odds__row--surprise' : ''}`}>
                {known(o) ? (
                  <MonsterPortrait breed={o.breed} size={52} animate={false} />
                ) : (
                  <span class="odds__mystery" aria-hidden="true">
                    ？
                  </span>
                )}
                <span class="odds__name">
                  <span>{nameOf(o)}</span>
                  <span class="muted small">
                    {known(o) ? t.source[o.source] : `${t.source.surprise} ${t.hiddenLine}`}
                    {i === topRow ? ` · ${t.mostLikely}` : ''}
                  </span>
                  <span class="odds__bar">
                    <span class="odds__fill" style={{ width: `${o.pct}%` }} />
                  </span>
                </span>
                <span class="odds__pct">{fill(t.pctRow, { pct: o.pct })}</span>
              </div>
            ))}
          </div>
          {compat !== null && top && (
            <p class="muted" style={{ marginTop: 8 }}>
              <span class="speaker">{UI_TEXT.pell}</span> {t.comments[compatTier(compat)]}{' '}
              <span class="small">
                ({fill(t.compat, { m: compat })} {fill(t.compatFor, { breed: nameOf(top) })})
              </span>
            </p>
          )}
          {outcomes.some((o) => !known(o)) && (
            <p class="muted small" style={{ marginTop: 4 }}>
              <span class="speaker">{UI_TEXT.pell}</span> {t.surpriseHint}
            </p>
          )}
        </section>
      )}
      <div class="spacer" />
      <div class="actionbar">
        <button type="button" class="btn btn--primary" disabled={!m1 || !m2 || outcomes.length === 0 || g.money < FUSION.fee} onClick={() => setConfirm(true)}>
          {fill(t.fee, { fee: gold(FUSION.fee) })}
        </button>
      </div>
      {m1 && m2 && g.money < FUSION.fee && <p class="muted small center">{t.refused.money}</p>}
      <Sheet open={picking !== null} title={t.pickTitle} onClose={() => setPicking(null)}>
        <div class="list">
          {cands
            .filter((c) => c.monster.id !== (picking === 1 ? id2 : id1))
            .map((c) => (
              <MonsterCard
                key={c.monster.id}
                listed={{ id: c.monster.id, monster: c.monster, source: 'freezer', history: [], createdAt: 0, updatedAt: 0, badge: c.where === 'elders' ? 'elder' : 'frozen' }}
                onTap={(l) => {
                  if (picking === 1) setId1(l.id)
                  else setId2(l.id)
                  setPicking(null)
                }}
              />
            ))}
          {cands.length === 0 && <p class="empty">{t.needTwoFrozen}</p>}
        </div>
      </Sheet>
      <Confirm open={confirm} text={m1 && m2 ? fill(t.fuseAsk, { a: m1.name, b: m2.name, where: whereText }) : ''} confirmLabel={fill(t.fee, { fee: gold(FUSION.fee) })} onConfirm={doFuse} onCancel={() => setConfirm(false)} />
    </>
  )
}

/* ---------- Memorial ---------- */

function MemorialTab({ g }: { g: GameState }) {
  const [open, setOpen] = useState<MemorialEntry | null>(null)
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState('')
  const [epitaph, setEpitaph] = useState('')
  const start = (e: MemorialEntry) => {
    setOpen(e)
    setEditing(false)
    setName(e.monster.name)
    setEpitaph(e.epitaph)
  }
  const save = () => {
    if (!open) return
    editMemorial(open.monster.id, name, epitaph)
    setOpen(null)
    showToast(UI_TEXT.lab.editor.saved.replace('{name}', name.trim() || open.monster.name))
  }
  const duplicate = async () => {
    if (!open) return
    const when = now()
    const copy = duplicateMonster(open.monster, newId())
    copy.name = `${open.monster.name}${UI_TEXT.lab.copySuffix}`.slice(0, RANGES.nameLength.max)
    await upsertEntry({ monster: copy, history: [], createdAt: when, updatedAt: when })
    setOpen(null)
    showToast(fill(t.duplicated, { name: open.monster.name }))
  }
  const view = () => {
    if (!open) return
    selected.value = { source: 'memorial', id: open.monster.id }
    setOpen(null)
    navigateFrom('pell', 'labView')
  }
  const garden = canVisitGarden(g)
  return (
    <>
      {g.upgrades.lanternGarden && (
        <section class="card card--muted">
          <p class="field__label">🏮 {UI_TEXT.upgrades.visit}</p>
          <p class="muted small">{UI_TEXT.upgrades.effects.lanternGarden}</p>
          <button
            type="button"
            class="btn btn--primary btn--small"
            disabled={!garden.ok}
            onClick={() => {
              const name = g.monster?.name ?? ''
              const refused = visitGarden()
              if (!refused) showToast(fill(UI_TEXT.upgrades.visitDone, { name, n: UPGRADES.lanternGardenVisitStress }))
            }}
          >
            {garden.ok ? UI_TEXT.upgrades.visit : garden.reason === 'visited' ? UI_TEXT.upgrades.visited : t.cantGive.none}
          </button>
        </section>
      )}
      {g.memorial.length === 0 && <p class="empty">{t.memorialEmpty}</p>}
      <div class="list">
        {g.memorial.map((e) => (
          <button key={e.monster.id} type="button" class="memorial" onClick={() => start(e)}>
            <MonsterPortrait monster={e.monster} size={72} animate={false} expression={e.cause === 'retired' ? 'happy' : 'sleepy'} />
            <span class="memorial__body">
              <span class="memorial__name">
                {e.monster.name} <Badge>{e.cause === 'fused' ? `🧬 ${t.cause.fused}` : `🕯️ ${t.cause[e.cause]}`}</Badge>
              </span>
              <span class="muted small">
                {variantNameOf(e.monster)} · {fill(t.livedShort, { n: e.monster.ageWeeks, total: e.monster.lifespanTotal })}
              </span>
              <span class="muted small">
                {UI_TEXT.lab.view.wins} {e.monster.records.wins} · {UI_TEXT.lab.view.losses} {e.monster.records.losses}
                {e.monster.records.titles.length ? ` · ${e.monster.records.titles.join(', ')}` : ''}
              </span>
              {e.epitaph && <span class="memorial__epitaph">“{e.epitaph}”</span>}
            </span>
          </button>
        ))}
      </div>
      <Sheet open={open !== null} title={open?.monster.name} onClose={() => setOpen(null)}>
        {open && !editing && (
          <div class="sheet__actions">
            <button type="button" class="btn btn--primary" onClick={() => setEditing(true)}>
              {t.editEntry}
            </button>
            <button type="button" class="btn" onClick={view}>
              {t.actions.view}
            </button>
            <button type="button" class="btn" onClick={() => void duplicate()}>
              {t.duplicate}
            </button>
            <button type="button" class="btn btn--ghost" onClick={() => setOpen(null)}>
              {t.actions.cancel}
            </button>
          </div>
        )}
        {open && editing && (
          <>
            <Field label={t.nameLabel}>
              <input class="input" value={name} maxLength={RANGES.nameLength.max} onInput={(e) => setName((e.currentTarget as HTMLInputElement).value)} />
            </Field>
            <Field label={t.epitaphLabel}>
              <input class="input" value={epitaph} maxLength={80} onInput={(e) => setEpitaph((e.currentTarget as HTMLInputElement).value)} />
            </Field>
            <div class="sheet__actions">
              <button type="button" class="btn btn--primary" onClick={save}>
                {t.save}
              </button>
              <button type="button" class="btn btn--ghost" onClick={() => setEditing(false)}>
                {t.actions.cancel}
              </button>
            </div>
          </>
        )}
      </Sheet>
    </>
  )
}

/* ---------- Heartstones ---------- */

function HeartstonesTab({ g }: { g: GameState }) {
  const [asking, setAsking] = useState<Heartstone | null>(null)
  const m = g.monster
  const can = m ? canReceiveHeartstone(m) : null
  const reason = !m ? t.cantGive.none : can && !can.ok ? (can.reason === 'age' ? fill(t.cantGive.age, { name: m.name, max: HEARTSTONE.maxAgeWeeks }) : fill(t.cantGive.has, { name: m.name })) : null
  const give = () => {
    const stone = asking
    setAsking(null)
    if (!stone || !m) return
    const refused = giveHeartstone(stone.id)
    if (!refused) showToast(say('heartstoneGiven', WREN.heartstoneGiven, m, { donor: stone.donorName }).text)
  }
  return (
    <>
      <p class="muted small center">{fill(t.stoneCount, { n: g.heartstones.length, max: heartstoneCap(g) })}</p>
      {g.heartstones.length === 0 && <p class="empty">{t.heartstonesEmpty}</p>}
      <div class="list">
        {g.heartstones.map((h) => {
          const grant = heartstoneGrant(h)
          const total = STAT_KEYS.reduce((s, k) => s + grant[k], 0)
          return (
            <div key={h.id} class="stone">
              <span style={{ fontSize: '2em' }} aria-hidden="true">
                💎
              </span>
              <span class="stone__body">
                <span class="stone__phrase">{fill(t.stoneFrom, { name: h.donorName, variant: variantNameOf({ mainBreed: h.donorBreed, variantId: h.donorVariant }) })}</span>
                <span class="muted small">{fill(t.stoneGives, { n: total, hit: HEARTSTONE.heirloomHit, family: FAMILY_LABELS[h.family] })}</span>
                <span class="muted small">{STAT_KEYS.filter((k) => grant[k] > 0).map((k) => `${STAT_NAMES[k]} +${grant[k]}`).join(' · ')}</span>
              </span>
              <button type="button" class="btn btn--small btn--primary" disabled={!m || reason !== null} onClick={() => setAsking(h)}>
                {m ? fill(t.giveTo, { name: m.name }) : t.actions.giveHeartstone}
              </button>
            </div>
          )
        })}
      </div>
      {reason && g.heartstones.length > 0 && <p class="muted small center">{reason}</p>}
      <Confirm open={asking !== null} text={asking && m ? fill(t.giveAsk, { donor: asking.donorName, name: m.name }) : ''} confirmLabel={m ? fill(t.giveTo, { name: m.name }) : ''} onConfirm={give} onCancel={() => setAsking(null)} />
    </>
  )
}

/* ---------- the Elder Grove ---------- */

function EldersTab({ g }: { g: GameState }) {
  const [sheetFor, setSheetFor] = useState<Listed | null>(null)
  const used = elderMentorUsedThisMonth(g)
  const rows = listFreezer().filter((l) => l.badge === 'elder')
  return (
    <>
      {rows.length === 0 && <p class="empty">{t.eldersEmpty}</p>}
      <div class="list">
        {rows.map((l) => {
          const site = JOURNEY_SITE_BY_ID[elderSite(l.monster)]
          return (
            <div key={l.id}>
              <MonsterCard listed={l} onTap={setSheetFor} />
              <p class="muted small" style={{ margin: '4px 8px 0' }}>
                {fill(t.mentors, { site: site.name, stat: STAT_NAMES[site.stat] })} · {used ? t.mentorUsed : fill(t.mentorReady, { pct: JOURNEY.technique.elderMentorPct })}
              </p>
            </div>
          )
        })}
      </div>
      <StoredSheet listed={sheetFor} onClose={() => setSheetFor(null)} />
    </>
  )
}
