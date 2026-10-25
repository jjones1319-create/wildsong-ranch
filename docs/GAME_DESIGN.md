# Wildsong Ranch: Game Design

Version 1.0 · the rules of the game. Content (names, monsters, techniques, items, calendar) lives in `docs/CONTENT.md`. Build order lives in `docs/BUILD_PLAN.md`.

**How to read this:**
- **MUST** = required for v1. **SHOULD** = build it if at all possible. **LATER** = stretch goal; leave hooks for it.
- Every number here is a starting value. All of them live in one file, `src/data/tuning.ts`, so balance can be changed without touching logic.
- Formulas marked **(tested)** were balance-simulated before this doc was written (see §27). Write unit tests that reproduce the example tables.
- Where this doc and `CONTENT.md` disagree, this doc wins for rules and `CONTENT.md` wins for names and data.

---

## 1. Vision

**Pitch.** Every monster in Wildsong Vale is born from a song. Type any song title, name or phrase at the Shrine of Echoes and the singing stone wakes the monster that was listening for it. You raise it week by week: train it, feed it, praise it, worry about it, and take it from scrappy rookie cups to the Crowns of the Vale. Then you say goodbye, and its legacy carries into the next one.

**Inspiration.** The classic 1997–2003 monster-raising sims, especially the Monster Rancher series. We borrow how they **play** (systems and mechanics) and nothing else. Every name, character, monster design, sprite, sound, piece of text and logo is original (see `CLAUDE.md`).

### Five pillars (every feature must serve at least one)
1. **Born from your world.** Monsters come from things you type: deterministic, shareable, surprising.
2. **One life, fully lived.** A finite, readable lifespan. Every week is a trade-off between growth, rest and glory.
3. **Care is the gameplay.** Mood, fatigue, stress and loyalty drive results. You coach and the monster acts.
4. **Legacy over loss.** Death hurts but pays forward through the Freezer, Fusion, Heartstones, the Memorial and the Hall of Fame.
5. **Legible depth, respectful pacing.** Hidden systems show up through cues, with an optional exact view. Sessions fit on a phone. Nothing is permanently missable. No energy timers, ads or paywalls.

### Best-of-series decisions (summary; reasons in `RESEARCH_NOTES.md`)

| System | What we use | Why |
|---|---|---|
| Turn structure | 1 week per turn, 4-week months, quarterly Officials | The series standard; one decision per tap suits phones |
| Training | 6 light drills (one per stat) + 4 heavy (+1 unlockable), stars, Great/Success/Cheat/Fail | Light/heavy split is the most-loved drill economy in the series |
| Technique learning | 4-week mentor Journeys per technique family, requirements shown up front | Gives training a goal; fixes the series' opacity complaint |
| Growth | 4 growth types × 10 life stages, prime window, prime notice for every monster | Timing strategy plus transparency |
| Care | Fatigue, stress, spoil/fear loyalty, nature, form, requests, praise/scold | This is where the bond comes from |
| Battle | Real-time 1-D duel, 4 ranges, guts economy, 60 s, auto or manual | Watchable, tactical, light on input |
| Creation | Phrase-seeded Shrine (song title + artist, or any words), Market, Fusion | The series' signature "monsters from your stuff" |
| Legacy | 20-slot Freezer, Fusion with compatibility, Heartstones, Memorial, Hall of Fame | Makes loss meaningful instead of only sad |
| Items | **Unlimited item use.** Songsheets teach techniques instantly; Stat Sweets add stats directly | The owner's request: a collect-and-power-up item layer on top of the classic loop |
| Editing | The Monster Lab editor, one tap from any Monster Card | The owner's request: full control over your own monsters |
| Progression | Grades E→S, breeder rank 1–10, four Crowns, then the Legend Cup | Clear long-term goals |
| QoL | Skip and speed for everything, autosave, multi-buy, transparency settings, planner | Fixes the most common complaints about old and remastered entries |

---

## 2. Core loop

```
Shrine / Market ─► NEW MONSTER
        │
        ▼
 ┌──── WEEK (1 turn) ─────────────────────────────────────────────┐
 │ week 1 of month: choose monthly food · read mail               │
 │ monster may make a request (rest / play / treat)               │
 │ choose ONE: Light drill · Heavy drill · Rest · Journey (4 wks) │
 │             · Tournament (if held) · Expedition (if invited)   │
 │ optional: one item · free town visits                          │
 │ end of week: aging, condition checks, autosave                 │
 └────────────────────────────────────────────────────────────────┘
        │ repeat ~250–480 weeks
        ▼
 Prime → decline → farewell → Memorial + Heartstone
        │
        ▼
 Freezer & Fusion → stronger next generation → Crowns → Legend Cup → Hall of Fame
```

**Session targets (phone):**
- A normal week takes 1–3 taps and under 10 seconds with animations skipped.
- A tournament takes 3–6 minutes played manually, or 15 seconds on auto or skip.
- One in-game year takes about 15–20 minutes of real play.
- A full monster life takes about 1.5–2 hours.

---

## 3. Time and calendar (MUST)

- **Calendar.** 1 turn = 1 week. 4 weeks per month, 12 months (Jan–Dec), so 48 weeks per year. A new game starts in Year 1, January, week 1.
- **Seasons:** Winter (Dec–Feb), Spring (Mar–May), Summer (Jun–Aug), Autumn (Sep–Nov).
- **Weather.** Each week rolls one weather type, seeded: Sunny, Cloudy, Rain, Storm (summer only), Snow (winter only). Weather is cosmetic except where an event uses it (CONTENT §11).

**Order of operations for each week (strict; unit-test this order):**
1. **Start of week.**
   - In week 1: monthly food prompt (defaults to last month's choice), passive charm effects, ranch-upgrade offer (May week 4 only).
   - Deliver mail: event notices, invitations, rumors, sale notices.
2. **Request check** (§6.7).
3. **The player picks ONE action:** Light drill, Heavy drill, Rest, Journey (takes 4 weeks), Tournament (if one is held this week and the monster is eligible), or Expedition (if invited).
4. **Resolve the action.** Drills trigger the praise/scold prompt.
5. **Items.** Use **as many items as you like**, any time during the week (a free action). The optional **One item per week** rule (in Settings; on by default only in Classic difficulty) restores the old-school limit.
6. **End of week.** Aging tick (§7), illness and breakdown checks (§6.6), weather roll for next week, **autosave**.

**Free actions (never use a turn):** town visits (Shop, Market, Shrine, Lab, Guild), reading info, the Journal, using items (any number), learning techniques from Songsheets, editing in the Monster Lab, settings, saving and loading, and one Odd Job per week (§9).

**Planner** (SHOULD):
- Queue up to 8 weeks of actions (drills and rests). Queued drills get no praise or scold, and a month start keeps last month's food.
- Execution auto-stops on any request, warning, event, invitation or other mail, illness, breakdown, a forced rest, the Signature, a grow-up, prime, or fatigue ≥ 60 or stress ≥ 50. Ordinary cups never stop it (almost every week holds one; the ranch lists them).
- A "Repeat last week" button sits on the ranch screen.

**Calendar screen** (SHOULD; `core/calendarView.ts`, `screens/ranch/Calendar.tsx`):
- **What's on it,** built only from the existing data and the save, never from a copied table:
  - Every cup of CONTENT §9 with the year rules (Sprout in even years, Elders' in odd ones, the Summit Qualifier and the Summit in Summit years instead of the Heatwave and Stargazer Cups). Each shows its grade, format and rounds (a round robin of 4 has 3, of 6 has 5), the purse at the monster's grade today, and the 1st-place item prize.
  - The expeditions open each month, with their grade and fame asks.
  - Dated notes:
    - A Crown four weeks ahead, for an S monster: "you're invited", or "win the S Official to be invited". The invitation itself is the standing flag from the S Official, so this is a reminder, not a letter.
    - The Wildsong Legend, in March, once all four Crowns are won.
    - The Market's seasonal stall changing in March, June, September and December (a discovered Reefclaw joins the summer note).
    - Ines's upgrade letter in May week 4.
    - The monster's birthdays: it turns a year older on every 48th week of age.
  - **Busy weeks:** the planner's queued drills and rests, a Journey or Expedition in progress, and injury, sickness or time away.
- **Secrets stay secret.** Nothing from the unlock chains or the secret phrases (the cocoon, the Reefclaw, the storm spark, the Vigil, locked breeds, variants) appears before the save records it, and the weather is never forecast.
- **"Can I enter?"** uses the same rules as the cup entry screen (`entryCheck`). For a later week only what is knowable today applies:
  - Checked: the grade window, "too easy", the minimum grade, invitations, and the event's rule, with the age projected to that week and today's nature and techniques.
  - Skipped: the temporary blocks (a cup in progress, a Journey, injury, sickness, away).
  - The answer reads "Can enter", "Too easy (−2 fame, −2 loyalty)", or the reason ("Needs grade C", "Invitation only", "Age under 48 weeks"…), with "Based on {name}'s grade today (D)". An Official reads "Your grade (D) · promotion".
- **Plan clashes.** A planned week on a notable event the monster could enter (anything but an ordinary cup), or on a ★ one, gets a warning on the calendar and in the planner sheet: "Your plan runs through the Summer Ascension". Ordinary cups don't warn, because almost every week holds one.
- **★ reminders.** A ★ on any event or expedition occurrence is saved as `calendarPins` (`${weekIndex}:${id}`; an expedition is keyed by its month's first week). Save v10 added them, empty for older saves.
  - Wren mentions a starred cup the week before and on the week, and a starred trip the week before its month and while it's open.
  - The ranch's Battle button gets a dot in a starred cup's week.
  - A pin goes by itself at the end of the week its occurrence is over.
- **The screen:**
  - **Header:** today's date, arrows for month and year, from January of this year to four years ahead (the next Summit is always in view). A Summit year is marked, and earlier weeks are greyed.
  - **Views:** **Agenda** (default: the next 12 weeks, "This week" / "Next week" / "In 5 weeks"), **Month** (four week rows of cards) and **Year** (12 month tiles with icons for Officials, Crowns, Opens, invitationals, the Summit and Expeditions; a tile opens its month).
  - **Filters:** "Only events I can enter" (on; starred ones always show) and "Show expeditions" (on).
  - **Event details:** a sheet with the date, grade, format and rounds, purse, item prize, the entry answer, ★, and, in the event's own week, **Enter**, which opens the cup entry screen with it picked.
- **Ways in:**
  - Tap the ranch's date bar. Under the date it shows "Next: Spring Ascension · in 3 wks": the next notable event the monster can enter, or a sooner ★ item, shown with a ★.
  - The Calendar row in Town, next to the Guild.
  - "See calendar" on the cup entry screen.

---

## 4. The monster (data model, MUST)

| Field | Type / range | Notes |
|---|---|---|
| `id` | string | Unique; imported copies get a new id |
| `name` | 1–16 chars | Player-chosen; default = variant name |
| `mainBreed`, `subBreed` | breed id | Main = body, kit, trait. Sub = palette, accent, quirk technique |
| `variantId` | string or null | Secret-phrase special variants (CONTENT §12) |
| `generation` | int ≥ 1 | Fusion babies = max(parents) + 1 |
| `parents` | [id, id] or [] | Lineage |
| `seedPhrase` | string | Normalized phrase that created it (if any) |
| `stats` | `{LIF, POW, INT, SKI, SPD, DEF}` 1–999 | Visible |
| `grades` | `{…}` E–A each | Growth aptitude per stat |
| `growthType` | Early, Steady, Late, Evergreen | §5.3 |
| `gutsRate` | 6–20 (ticks per +1 guts) | Lower is faster |
| `lifespanTotal` | weeks | Shrinks with strain penalties, grows with fruits |
| `ageWeeks` | int | |
| `fatigue`, `stress` | 0–100 | Hidden or shown by transparency setting |
| `spoil`, `fear` | 0–100 | Loyalty = round((spoil + fear) / 2). Style = spoil − fear |
| `nature` | −100…100 | Good ↔ wicked |
| `form` | −100…100 | Gaunt ↔ round |
| `fame` | 0–100 | |
| `grade` | E, D, C, B, A, S | Tournament class |
| `techniques` | `[{id, uses, level}]` | Max 12 learned |
| `likes` | `{food, dislikedFood, toy, battle(−1/0/+1), drill, dislikedDrill}` | Rolled at birth |
| `status` | `{injuredWeeks, sickWeeks, tonic:{stat, weeksLeft}, usedSunfruit, usedMoonfruit, heartstoneReceived, cocoon…}` | |
| `diet` | `{lastFood, sameFoodStreak, puddingCount…}` | For boredom and events |
| `records` | wins, losses, draws, KOs, cups won, titles, earnings, highest grade, Crowns won, stat points gained from Stat Sweets (per stat) | Sweets are shown separately on the Monster Card |
| `flags` | `pure`, `edited`, `sandbox` | `edited` is set by Monster Lab |
| `appearance` | palette id, accent part, variant overrides | Derived from breeds, overridable in the Lab |

**Derived values (never stored):**
- `loyalty = round((spoil + fear) / 2)`
- `style = spoil − fear`
- `lifeStage` (1–10)
- `strain = fatigue + 2 × stress`
- `stars(stat)`
- `totalStats`

---

## 5. Stats and growth

### 5.1 What each stat does

| Stat | Battle meaning | Other uses |
|---|---|---|
| LIF | Max HP | Expedition stamina |
| POW | Damage of POW techniques; resistance to POW techniques | Expedition boulders |
| INT | Damage of INT techniques; resistance to INT techniques | Expedition search and lore; reduces getting lost |
| SKI | Accuracy | Expedition traps |
| SPD | Evasion; walk speed | Expedition gaps |
| DEF | Damage reduction against everything | Expedition winds and hazards |

### 5.2 Growth grades → grade factor `gf` (tested)

E 0.58 · D 0.79 · C 1.00 · B 1.32 · A 1.55

### 5.3 Growth types and life stages (tested)

`lifeStage` comes from `ageWeeks / lifespanTotal`. The stage ends at these cumulative percentages:

| Stage | 1 Hatchling | 2 Youngling | 3 Juvenile | 4 Adolescent | **5 Prime** | **6 Late Prime** | 7 Mature | 8 Elder | 9 Venerable | 10 Twilight |
|---|---|---|---|---|---|---|---|---|---|---|
| Early | 5 | 11 | 20 | 30 | 37 | 43 | 56 | 70 | 82 | 100 |
| Steady | 10 | 20 | 34 | 48 | 60 | 66 | 75 | 82 | 90 | 100 |
| Late | 14 | 28 | 42 | 56 | 68 | 78 | 85 | 90 | 95 | 100 |
| Evergreen | 5 | 11 | 20 | 30 | 45 | 55 | 66 | 77 | 87 | 100 |

**Stage factor `sf`** (drives gains and rest; tested):

| Stage | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `sf` | 0.45 | 0.60 | 0.75 | 0.88 | 1.00 | 0.96 | 0.85 | 0.72 | 0.55 | 0.35 |

**UI:**
- The life bar shows the 10 stage segments, with the Prime window (stages 5–6) highlighted.
- Wren announces Prime for **every** monster on entering stage 5 ("She's in her prime! Now's the time to push.").
- Wren also announces "past her prime" on entering stage 7.

**Size:**
- Stages 1–2 are drawn at 70% size, stages 3–4 at 85%, stages 5 and up at 100%.
- Stages 8 and up are slightly desaturated, with slower idle animations.

---

## 6. Training and care

### 6.1 Drills (MUST; names in CONTENT §4)

| Kind | Raises | Secondary | Lowers | Fatigue | Stress | Form |
|---|---|---|---|---|---|---|
| Light (×6, one per stat) | that stat | — | — | +10 | +4 | −1 |
| Heavy H1 | POW | LIF | SPD | +15 | +9 | −2 |
| Heavy H2 | INT | SKI | DEF | +15 | +9 | −2 |
| Heavy H3 | SPD | INT | POW | +15 | +9 | −2 |
| Heavy H4 | DEF | LIF | INT | +15 | +9 | −2 |
| Heavy H5 (needs the Training Yard upgrade) | LIF | DEF | SKI | +15 | +9 | −2 |

- There is deliberately no heavy drill with SKI as its main stat. Accuracy has to be bought with light drills, which forces real build choices.
- **Stars (difficulty):** 1★ if the main stat is under 300, 2★ for 300–599, 3★ for 600 and up.
- **Chore pay:** drills are jobs around the vale. A Success or Great pays 30G (light) or 50G (heavy). Great pays +50%.

### 6.2 Resolving a drill (MUST, tested)

Let `F` = fatigue, `S` = stress, `Sp` = spoil, `Fe` = fear, `N` = nature, `L` = loyalty, `stage` = life stage, and `stars` = stars of the drill's main stat.

**Step 1: truancy.**
- Only possible if `F ≥ 70`: `pTruant = (F − 69) × 2% × (1 − L / 150)`.
- On truancy: no gains, `F −5`, `S −2`, and the result is "Slacked off". The praise/scold prompt still appears.

**Step 2: outcome weights.**
```
great = 10 + max(0, L − 40)·0.15 + max(0, N)/10 − max(0, F − 40)·0.2 + (stage ∈ {5,6} ? 3 : 0) + (liked drill ? 6 : 0)
cheat = 8 + max(0, S − 20)·0.45·(N < 0 ? 1.5 : 1) + Sp·0.05 − max(0, L − 50)·0.1 + max(0, −N)/10 + (disliked drill ? 6 : 0)
fail  = 7 + 6·(stars − 1) + max(0, F − 30)·0.6 − Fe·0.06 + (stage ∈ {1,10} ? 4 : 0)
great ≥ 1, cheat ≥ 1, fail ≥ 2;  success = max(20, 100 − great − cheat − fail);  normalize all four to 100%.
```
The trait and Training Yard modifiers in CONTENT add to `great`. Apply them before normalizing.

**Reference outcomes** (Great / Success / Cheat / Fail %; unit-test these):

| State | G | S | C | F |
|---|---|---|---|---|
| Fresh baby, stage 1, 1★, F0 S0 Sp30 Fe30 N0 | 10 | 71 | 10 | 9 |
| Prime, happy and loyal, 2★, F20 S10 Sp60 Fe50 N+30 | 18 | 61 | 10 | 10 |
| Prime but tired, 2★, F60 S20 Sp50 Fe50 N0 | 10 | 51 | 10 | 28 |
| Prime, stressed and spoiled, 2★, F30 S60 Sp90 Fe20 N−30 | 15 | 31 | 42 | 12 |
| Old, 3★, F30 S20 Sp60 Fe60 N+10 | 14 | 61 | 10 | 15 |
| Neglected, stage 3, 1★, F75 S70 Sp20 Fe20 N−10 | 3 | 20 | 44 | 33 |

### 6.3 Gains (MUST, tested)

```
light  = clamp(round(10 · gf(stat) · sf) + rnd(−1..+1), 1, 15)
heavy  = clamp(round(16 · gf(main) · sf) + rnd(−1..+1), 3, 20)
second = clamp(round( 7 · gf(sec)  · sf) + rnd(−1..+1), 1, 10)
lowered stat: −rnd(2..3) on Success/Great, −rnd(1..4) on Cheat, nothing on Fail; never below 1
Great:  main +3 (still capped at 15 / 20), secondary +1 (cap 10), and the drill costs 3 less fatigue
Cheat:  main = max(1, floor(main / 2)), secondary = rnd(0..1), and the drill costs 5 less fatigue
Fail:   no gains
Breed bonus drill (CONTENT §2): +1 to the main gain on Success/Great
Active tonic for that stat: +3 to the main gain on Success/Great
```

**Light gain by grade and stage** (no noise; unit-test):

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| E | 3 | 3 | 4 | 5 | 6 | 6 | 5 | 4 | 3 | 2 |
| D | 4 | 5 | 6 | 7 | 8 | 8 | 7 | 6 | 4 | 3 |
| C | 4 | 6 | 8 | 9 | 10 | 10 | 8 | 7 | 6 | 4 |
| B | 6 | 8 | 10 | 12 | 13 | 13 | 11 | 10 | 7 | 5 |
| A | 7 | 9 | 12 | 14 | 15 | 15 | 13 | 11 | 9 | 5 |

**Heavy main gain:**

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| E | 4 | 6 | 7 | 8 | 9 | 9 | 8 | 7 | 5 | 3 |
| C | 7 | 10 | 12 | 14 | 16 | 15 | 14 | 12 | 9 | 6 |
| A | 11 | 15 | 19 | 20 | 20 | 20 | 20 | 18 | 14 | 9 |

**Heavy secondary gain:**

| | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| C | 3 | 4 | 5 | 6 | 7 | 7 | 6 | 5 | 4 | 2 |
| A | 5 | 7 | 8 | 10 | 10 | 10 | 9 | 8 | 6 | 4 |

### 6.4 Praise and scold (MUST)

After every drill (and after truancy) the player reacts with one of:
- **Praise:** swipe across the monster (petting), or tap the Praise button.
- **Scold:** tap the finger-wag button.
- **Skip.**

| Result | Praise | Scold | Skip |
|---|---|---|---|
| Great | Sp +4, S −5 | Fe +3, S +8, Sp −2 ("That's not fair!") | S +5 (wanted recognition) |
| Success | Sp +2, S −3 | Fe +3, S +6, Sp −1 | — |
| Cheat | Sp +5, N −2, S −3 (rewarding bad behavior) | Fe +4, N +1, S +4 (good nature) / +10 (bad nature) | Sp +2, N −1 |
| Fail | Sp +3, S −2 (encouragement) | Fe +3, S +2 (good) / +5 (bad) | — |
| Slacked off | Sp +4, N −2 | Fe +5, N +1, S +4 | Sp +2, N −1 |

- Traits can scale these (e.g., Cheerful halves the stress from scolding).
- **Fear helps drills**: it lowers `fail` (see §6.2).
- **Spoil hurts drills**: it raises `cheat`.
- **Both build loyalty**, and loyalty decides obedience in battle.

**Style bands** (Spoil − Fear; shown on the Monster Card): Doting ≥ 80 · Fond 50–79 · Gentle 20–49 · Even −19…19 · Firm −49…−20 · Strict −79…−50 · Spartan ≤ −80.

### 6.5 Rest and play (MUST, tested)

```
Rest: fatigue −round(30 + 20·sf), stress −round(6 + 8·sf), form +1
Play (only when the monster requests it): fatigue −round(14 + 10·sf), stress −round(10 + 12·sf)
```

| Stage | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Rest F/S | 39/10 | 42/11 | 45/12 | 48/13 | 50/14 | 49/14 | 47/13 | 44/12 | 41/10 | 37/9 |
| Play F/S | 18/15 | 20/17 | 22/19 | 23/21 | 24/22 | 24/22 | 22/20 | 21/19 | 20/17 | 18/14 |

### 6.6 Strain, illness and breakdowns (MUST, tested)

```
strain = fatigue + 2·stress
Strain debt (every week, at the end of the week):
  over  = max(0, strain − 10) · (100 + max(0, strain − 150)) / 100     (strain above 150 compounds)
  debt += over                                                         (Gentle ×0.5, Classic ×1.25)
  extraLifespanLoss = min(cap, floor(debt / 160)); debt −= 160 · extraLifespanLoss
  cap = 3 (Standard), 1 (Gentle), 4 (Classic)
  Examples: a calm week (strain 30) adds 20 debt, so a lazy ranch loses about 1 week in 8; a tired week
  (strain 90) adds 80, about 1 week in 2; a wrecked week (strain 250) adds 480, the full 3 weeks.
Illness: end of week with fatigue ≥ 90 → 10% chance: Sick for 2 weeks (only Rest allowed), −2 weeks lifespan.
Breakdown: end of week with strain ≥ 200 → 25% chance of one of:
  • Runs away: 2 weeks missing (they still age), 300G search fee, then fatigue = 30, stress = 30, spoil −5, fear −5
  • Collapses: 2 weeks at the clinic (they still age), 200G, −2 weeks lifespan, then fatigue = 30, stress = 30
```
Breakdowns are dramatic, teachable moments: Wren explains what happened and how to prevent it.

*History (M1, 2026-10-22):* the first draft used a step ladder (no loss below 80 strain; 80–124 → 1, 125–169 → 2, 170+ → 3). The M1 sims showed it made a cliff instead of a slope: a player who praised and rested on time never lost a week, while OK care lost half its life, so the §26 bands could not be met. The owner chose this smoother "strain debt" rule, which lands all four bands. The ladder stays selectable in `tuning.ts` (`STRAIN.mode = 'ladder'`) for comparison.

**Weekly assistant labels** (Guided and Classic modes show these words instead of numbers):

| | | | | | | |
|---|---|---|---|---|---|---|
| **Fatigue** | 0–14 Bright-eyed | 15–34 Fine | 35–54 A bit tired | 55–74 Tired | 75–89 Exhausted | 90–100 About to collapse |
| **Stress** | 0–9 Carefree | 10–24 Calm | 25–44 A little tense | 45–64 Stressed | 65–84 Very stressed | 85–100 At breaking point |
| **Loyalty** | 0–19 Distant | 20–39 Wary | 40–59 Friendly | 60–79 Devoted | 80–100 Inseparable | |

The monster's **expression** also reflects its state:

| State | Expression |
|---|---|
| fatigue ≥ 55 | droopy eyes |
| stress ≥ 45 | sweat drop |
| loyalty ≥ 80 | sparkle |
| sick | green tint |
| nature ≤ −60 | mischievous grin |

### 6.7 Requests (MUST)

- **Trigger:** at the start of the week, if `F ≥ 40` or `S ≥ 40`, with chance `8% + (max(F, S) − 40) × 0.8%`. That gives 40 → 8%, 60 → 24% and 100 → 56%.
- **Type:**
  - Rest if `F ≥ S`, Play if `S > F`.
  - About 1 in 10 requests is a Treat instead: the monster wants its favorite toy or liked food item. This only happens if you own one.
- **Accept:** Rest or Play uses the week. A Treat uses one item.
- **Deny:** stress +8 and spoil −2, then continue with the chosen action.

### 6.8 Transparency setting (MUST)

| Mode | What the player sees |
|---|---|
| **Classic** | Wren's words, expressions and the life bar only. No hidden numbers and no odds. |
| **Guided** (default) | Labeled bars for fatigue, stress, loyalty and life. Drill odds as words: "Looks eager", "Likely", "Risky", "Very risky". |
| **Breeder's Lens** | Exact numbers everywhere: hidden stats, strain, weeks left, exact drill odds, Journey chances, battle hit %. |

---

## 7. Lifespan, aging and the end of life (MUST)

**At birth:**
```
lifespanTotal = round(0.6 · main.lifespan + 0.4 · sub.lifespan)
                · (pure ? 1.10 : 1)
                + shrineOffset (−10…+30 weeks)
```

**Ongoing changes:**
- **Every week:** `ageWeeks +1`, and `lifespanTotal −= extraLifespanLoss` from the strain debt (§6.6). Journeys tick normally, once per week; never double-charge.
- **Tournament:** `lifespanTotal −= 1 + (KO'd ? 2 : 0)`, on top of that week's normal strain debt.
- **Fruits:** Sunfruit +40 weeks and Moonfruit +20 weeks, each **once per monster**. These rewind the life stage because the stage is `age / total`.
- **Tonics** cost 6 weeks each, shown clearly before use.
- **Hearty Stew** as the monthly food gives +1 week per month.

**Warnings:**
- Wren warns when 25% of life remains, again at 48 weeks left, and again at 10 weeks left.
- From stage 8 the monster visibly ages.

**Difficulty modes** (chosen at new game; Gentle ↔ Standard can be switched later, but Classic is locked in):

| | Gentle | Standard (default) | Classic |
|---|---|---|---|
| End of life | Retires to the Elder Grove (no death) | Passes away of old age | Passes away of old age |
| KO consequences | No injury | Injury chance: 5% + fatigue/2 % | Injury chance as Standard; KO with fatigue ≥ 80 → 15% chance of death |
| Strain penalty | Debt builds half as fast; max 1 week per week | As §6.6 (max 3) | Debt builds a quarter faster; max 4 |
| Breakdowns | 10% | 25% | 25% |
| Prize money | ×1.25 | ×1 | ×1 |
| Items | Unlimited | Unlimited | One item per week (can be switched off in Settings) |

**Farewell (Standard and Classic):**
1. A short, gentle scene: Wren, the ranch at dusk, the monster's best moments (titles, best win).
2. The player can write a one-line epitaph.
3. The monster moves to the **Memorial**.
4. It leaves a **Heartstone** (§16).
5. Mail from Sister Mara invites you to the Lantern Vigil (unlock event, CONTENT §11).

**Retirement (Gentle):** the same scene, but the monster moves to the **Elder Grove**. An Elder can be used in Fusion, and once per month it can mentor: the next Journey in its best stat's family gets +10% technique chance.

---

## 8. Food and items (MUST; tables in CONTENT §5–6)

**Monthly food:**
- Chosen in week 1 of each month.
- The effect depends on the monster's liked and disliked food.
- **Boredom:** the same food 3 or more months in a row halves its positive effects. Wren mentions it ("She's getting tired of turnips…").

**Items:**
- **No limit.** Use as many items as you want, whenever you want (a free action), and shop stock never runs out. There are only two exceptions:
  - **Life fruits** (Sunfruit, Moonfruit) still work once per monster each. Unlimited lifespan would remove aging, which is the heart of the game. The Monster Lab can still change lifespan freely.
  - The optional **One item per week** rule (Settings; on by default only in Classic difficulty).
- **Categories:** Recovery, Mood, Form, **Stat Sweets** (permanent stat boosts), **Songsheets** (teach techniques, §10.5), **Potential items** (growth grade and guts rate), Tonics (4-week drill boosts that cost lifespan), Life Fruits (found only), Toys (favorite-toy bonus), Charms (passive), Fusion catalysts, Key items, Sellables.
- **Stat Sweets** permanently add to one stat: regular +5, Grand +15, or a Wondercake for +5 to all six.
  - Stats still cap at 999. Sweets cost no fatigue, stress or lifespan, and there are no diminishing returns.
  - The Monster Card shows how much of each stat came from sweets (e.g. "+120 from sweets"), so trained and bought stats are both visible.
- **Potential items:** the Potential Pearl raises one stat's growth grade by one step (max A). The Tempo Bell makes guts regenerate faster (guts rate −1, minimum 6).
- **Tonics:** different tonics can run at the same time. Using the same tonic again resets its 4 weeks and costs lifespan again.
- **Use flow:** Bag → item → quantity (×1, ×5, ×10, Max) → confirm → a short, skippable eating or learning animation and the stat change.
- **Charms** are passive and placed on the ranch. Within one category (Comfort, Bedding) only the best owned charm applies, so they don't stack.
- **Shop:** multi-buy quantity picker; prices in CONTENT.

---

## 9. Economy (MUST)

- **Start:** 3,000G. The first monster is free: a Guild gift from the Market, or a Shrine creation.
- **Income:** tournament purses (§13), chore pay (§6.1), Journey trial bonuses, selling expedition loot, and Odd Jobs.
- **Odd Jobs** (SHOULD): Basil's board of short mini-games (Turnip Sort, Echo Stones), each paying once per in-game week as a free action, 0–150G by score; a free Practice mode replays any job without pay (CONTENT §13).
- **Expenses:** food, items (including Stat Sweets and Songsheets), Journeys (2,000G; 1,000G in sale months), Fusion fee (1,000G), Encyclopedia re-creation (500G), ranch upgrades, breakdown fees.
- **Money is the only limit on items**, so purses matter. Officials still pay little; regular cups and item prizes are where the rewards are.
- **No game over for money.** If money would go below 0 the Guild Loan covers it, up to 5,000G with a 10% fee. While in debt, 50% of every prize goes to repayment and only food and Recovery items can be bought.

---

## 10. Techniques (MUST; full list in CONTENT §3)

### 10.1 Attributes

`id, name, breed, family, type (POW|INT), range (1–4), cost (guts), force, hit, wither, sharp, anim (ticks), effect, effectValue, learn`.
- **Families:** Basic · Hit · Heavy · Wither · Sharp · Special · Chain · Signature.
- **Multi-hit techniques:** `force` is per hit, and each hit rolls separately.

### 10.2 Family value bands (keep new techniques inside these)

| Family | Guts | Force | Hit | Wither | Sharp | Anim | Role |
|---|---|---|---|---|---|---|---|
| Basic | 10–14 | 10–14 | +3…+8 | 5–8 | 5–8 | 24 | Cheap, reliable |
| Hit | 16–20 | 14–19 | +14…+20 | 6–10 | 6–10 | 27 | Accuracy |
| Heavy | 42–50 | 50–64 | −12…−6 | 10–14 | 8–12 | 39 | Big, risky |
| Wither | 24–30 | 12–18 | −2…+4 | 36–55 | 4–8 | 30 | Drains guts |
| Sharp | 24–30 | 22–30 | −4…+2 | 8–12 | 26–34 | 30 | Crits |
| Special | 40–55 | varies | varies | varies | varies | 36 | Effects |
| Chain | base +6 (+8 from Basic) | ×1.3 (×1.7 from Basic) | +3 | ×1.2 | +3 | +3 | Upgrade |
| Signature | 54–60 | strong | | | | 42 | Pure-breed showpiece |

### 10.3 Effects

- **drain X:** heal X% of the damage dealt.
- **heal X:** restore X% of max HP. Always succeeds (no hit roll) if the target is in range; force 0 deals no damage.
- **multi N:** N separate hits, each with its own hit and crit rolls.
- **stun T:** on hit, the target can't act, move or regenerate guts for T ticks.
- **gutsSteal:** gain the guts that were withered.
- **recoil X:** on a **miss**, take X% of your own max HP.
- **push:** knockback on hit (§12.3).
- **lunge:** after the attack, dash to Close range.
- **jackpot:** on hit, roll once:
  - 1/3: double damage
  - 1/3: heal 20%
  - 1/3: a funny fizzle with no damage

### 10.4 Learning

- **Starters:** each monster is born with its main breed's two Basic techniques, plus its sub-breed's **quirk** technique if that is different.
- **Journeys:** each successful week can teach one technique from that site's family (§11).
- **Songsheets:** read a Songsheet to learn its technique instantly (§10.5).
- **Mastery:**
  - Using a technique raises `uses`.
  - At 15 uses → Lv2 (+2 hit).
  - At 40 uses → Lv3 (+2 force), which unlocks its Chain upgrade at the matching Journey site.
- **Signature** (pure breeds only): learned automatically when the monster first enters Prime with loyalty ≥ 60, as a celebratory scene. If missed, it can be learned at Glacier Bastion with DEF + type stat ≥ 700.
- **Cap:** at most 12 learned techniques. Learning a 13th asks which one to forget. Forgotten techniques can be relearned any time from the Songbook (if you own the sheet) or on a Journey.
- **In battle:** all learned techniques are available, grouped by range.

### 10.5 Songsheets: learning techniques from items (MUST)

- **What they are:** a **Songsheet** is an item that teaches one technique. Reading it is instant and free (a free action): no stat requirement, no chance roll, no Journey.
- **The Songbook:**
  - A sheet you own goes into your **Songbook** for good; it isn't used up.
  - Any of your monsters that can learn it can learn it from the Songbook at any time, as often as you like.
  - The Journal shows Songbook completion.
- **Who can learn what:**
  - **Universal sheets** (24 music-themed techniques, CONTENT §3.1): **any** monster.
  - **Breed sheets:** one for every non-Basic technique in each breed's kit. A monster can learn one if the technique is in its main breed's kit or is its sub-breed's quirk.
  - **Signature sheets:** pure breeds of that breed only.
  - Chains taught by a sheet don't need the base technique at Lv3.
- **Where sheets come from:**
  - The **Guild Library** in Town sells the universal sheets and the breed sheets of every breed you've unlocked. Prices and rank gates are in CONTENT §3.
  - Tournament prizes (§13), expedition treasure and some events.
  - Signature sheets are never sold; they're Crown prizes.
- **Type matters:**
  - A POW technique uses POW and an INT technique uses INT. Teaching a big INT blast to a brawny bruiser is allowed; it just hits softer.
  - The Songbook marks a ★ "good fit" when the monster's matching stat is one of its top two.
- **Rules that still apply:**
  - The 12-technique cap. Forgetting is free and can be undone through the Songbook.
  - **Fusion:** universal techniques count as part of every breed's kit for inheritance.
- **Journeys still matter:** they also grow stats, build the mentor bond and earn Trial rewards, and they teach techniques for free if luck is on your side.

---

## 11. Journeys (MUST): four weeks with a mentor

- **Sites:** 5 sites (CONTENT §7). Each is tied to one stat and one technique family: Iron Quarry (POW, Heavy), Windrun Steppe (SPD, Sharp), Starfall Observatory (INT, Wither), Archer's Glade (SKI, Hit), Glacier Bastion (DEF, Special; grade B or higher).
- **Cost:** 2,000G, or 1,000G in sale months. Sale mail arrives in two random months each year.
- **The Mentor's Ledger** (the Journey picker) shows, for each site:
  - its techniques for your monster's breed;
  - each technique's requirement;
  - your current score;
  - the chance tier (Not ready, Possible, Likely, Very likely), or the exact % in Lens mode.
- **Each week (×4):** fatigue +18 and stress +7 (applied after the check), and the normal weekly aging tick.

**Weekly success check (tested):**
```
score = 3·gradeIndex(siteStat) + 2·gradeIndex(LIF) + 4·(stage − 1) + floor(fear/5) − floor(fatigue/5) + rnd(0..29)
gradeIndex: E=1 … A=5. Week thresholds: 10, 20, 30, 40.  score ≥ threshold → success.
```

**Reference success %** (site C, LIF C, fear 30, starting fatigue 10; unit-test):

| Stage | Wk 1 | Wk 2 | Wk 3 | Wk 4 |
|---|---|---|---|---|
| 1 | 100 | 87 | 40 | 0 |
| 3 | 100 | 100 | 67 | 23 |
| 5 | 100 | 100 | 93 | 50 |
| 8 | 100 | 100 | 100 | 90 |

The same setup with site grade A, LIF B at stage 5 gives 100/100/100/77. With site E, LIF E at stage 5 it gives 100/100/60/17.

**Each successful week:**
- site stat + `clamp(round(8 · gf · sf) + rnd(−1..1), 1, 12)`
- LIF + `clamp(round(5 · gf(LIF) · sf), 1, 8)`
- one technique roll

**Technique roll:**
1. Candidates are the site-family techniques of the monster's main breed (plus Chains whose base is at Lv3) that it hasn't learned, in table order.
2. Roll only for the **first** candidate whose requirement score is met.
3. `reqScore = sum of the listed stats + loyalty`.
4. Chance: 0% below the requirement; 30% at it; +10% per 50 points over; capped at 90%.
5. +10% if the breed trait is Quick Study.
6. +10% with an Elder mentor (Gentle mode).
7. **At most one technique per Journey.**

**Mentor bond:** every 8 Journeys at the same site, the mentor gives a Charm that lowers that site's requirements by 50 permanently.

**Trial (end of Journey):**
- A battle against a wild monster of your grade (+0 or +1 grade): **Fight**, **Auto** (take over at any time) or **Skip** (simulated exactly as an untouched Auto run would play it), like a cup match (§12.11).
- Win: 600 × gradeIndex G, plus a 10% chance of a rare drop.
- A KO uses normal injury rules.

---

## 12. Battle (MUST)

### 12.1 Arena and ranges

- **Arena:** a 1-D arena 1,200 units wide (x from −600 to +600). Each monster's body radius is 80 (M10: it was 50; the sprite box is drawn 200 units wide so visuals match the physics).
- **Gap:** `gap = |xB − xA| − 160`.
- **Start:** xA = −230, xB = +230, so the gap is 300 (Near).

| Band | 1 Close | 2 Near | 3 Mid | 4 Far | Out of range |
|---|---|---|---|---|---|
| Gap | 0–159 | 160–309 | 310–479 | 480–679 | ≥ 680 |

### 12.2 Timing

- **Engine:** a fixed-step simulation at **30 ticks per second**. A match lasts **60 seconds** (1,800 ticks).
- **Rendering:** interpolates between ticks.
- **Playback:** speed ×1, ×2 or ×4, plus Skip (instant simulation).
- **Determinism:** the engine is a pure function `(monsterA, monsterB, seed, inputs[]) → result`. Inputs are timestamped by tick, so battles can be replayed and tested.

### 12.3 Movement

- **Walk speed:** `70 + 50 · SPD/999` units per second. Backing away is ×0.85.
- **Dash:**
  - Costs 8 guts and is only allowed when the gap is 160 or more.
  - 3× speed toward the opponent for up to 18 ticks, or until the gap enters the next closer band.
  - 60-tick cooldown.
- **Push (knockback):**
  - Only when touching (gap ≤ 40).
  - A 15-tick shove; the opponent slides 250 units back (limited by the wall).
  - 90-tick cooldown, no guts cost.

### 12.4 Guts

- **Start and cap:** start at 50, cap at 99.
- **Regeneration:** +1 every `gutsRate` ticks. Breed rates run 10–14, which is 3 down to about 2.1 guts per second (M9 narrowed them from 8–18: the attack count was tracking the rate too closely).
- **During attacks:** regeneration **pauses during your own attack animation**.
- **Costs:** the cost is paid on use, even on a miss. Wither removes the opponent's guts on a hit.

### 12.5 Formulas (tested)

```
Hit% = 50 + tech.hit + (SKI_att − SPD′_def)/15 + (G_att − 50)/5 − (G_def − 50)/5   → clamp 5..95
  advantage (defender distracted / special): h = 100 − (100 − h)²/100 ; two: (100 − h)³/10⁴
  disadvantage (defender Composure):         h = h²/100
  G_att = attacker guts BEFORE paying the cost; G_def = defender's current guts

A  = attacker POW (POW tech) or INT (INT tech)
E  = (3·DEF′_def + defender's same-type stat) / 4
base  = force · (0.7 + A/180)
ratio = clamp(((A + 150)/(E + 150))^0.5, 0.45, 1.9)
k(R)  = 0.15 + 0.03·(R − 6)            (R = guts rate; slow-regen breeds gain more from banked guts)
gAtt  = 1 + (G_att − 50)/100 · k(R_att)
gDef  = 1 − (G_def − 50)/100 · k(R_def) · 0.5
damage = max(1, round(base · ratio · gAtt · gDef · crit · traits · specials · rnd(0.95..1.05)))

Crit% = sharp + min(10, fame/10)                                  (nature ≥ 0)
      = sharp + min(5, fame/20) + min(5, oppFame/20) + min(10, stress/10)   (nature < 0)
crit  = ×1.5 damage and ×1.5 wither
Wither = flat tech.wither (×1.5 on crit, specials below)

Form: f = form/100 → SPD′ = SPD·(1 − 0.2f), DEF′ = DEF·(1 + 0.2f)   (round = slower but sturdier)
HP = LIF. KO at 0.
```

`pow` is the one floating-point function allowed in rules. Implement it with `Math.pow` on values rounded to 4 decimals and round the result, or use a lookup table. Determinism tests must pass on Chrome and Safari.

**Reference numbers** (POW-type, 50 vs 50 guts, guts rate 12, no crit; force 12 / 18 / 55):

| Attacker A | Defender DEF / same / LIF | Damage | % of HP |
|---|---|---|---|
| 150 | 120 / 120 / 180 | 19 / 29 / 89 | 11 / 16 / 49 |
| 400 | 350 / 300 / 420 | 37 / 56 / 171 | 9 / 13 / 41 |
| 700 | 600 / 500 / 700 | 60 / 89 / 273 | 9 / 13 / 39 |
| 950 | 850 / 700 / 950 | 77 / 115 / 351 | 8 / 12 / 37 |
| 700 vs a glass cannon | 250 / 150 / 350 | 83 / 124 / 380 | 24 / 35 / 109 |
| 300 vs a fortress | 700 / 600 / 800 | 21 / 31 / 96 | 3 / 4 / 12 |

**Hit examples:**
- Tech +0, SKI 300 vs SPD 300 at 50/50 guts → 50%.
- Tech +16, SKI 600 vs SPD 300 → 86%.
- Tech −10, SKI 300 vs SPD 700, attacker at 90 guts and defender at 20 → 27%.

**Guts multiplier:**
- At 99 guts: ×1.07 (rate 6) to ×1.25 (rate 18).
- At 10 guts: ×0.94 to ×0.80.

### 12.6 Distraction (obedience)

Whenever the monster starts an action (AI decision or player tap), roll a distraction chance from its loyalty. Interpolate linearly between these points:

| Loyalty | 0 | 20 | 40 | 50 | 60 | 70 | 80 | 85+ |
|---|---|---|---|---|---|---|---|---|
| Chance | 45% | 30% | 17% | 12% | 8% | 4% | 2% | 1% |

- Roll at most once every 90 ticks.
- **When distracted:**
  - The monster dawdles for 60 ticks (chasing a butterfly, scratching, yawning): no actions and no movement, but guts still regenerate.
  - Incoming attacks get +1 advantage.
  - The player sees a "?!" bubble and a cute line.

### 12.7 Specials (each at most once per battle; only one active at a time, except Last Stand)

| Special | Trigger | Chance | Effect (8 s unless noted) |
|---|---|---|---|
| Last Stand | Takes lethal damage | min(35, guts/10 + loyalty/5 + DEF/100) % | Survive with 1 HP |
| Valor | Nature ≥ +20, HP ≤ 30% after a hit | min(50, nature/2) % | Damage dealt ×1.5 |
| Rage | Nature ≤ −20, just withered | min(50, wither/4 + \|nature\|/3) % | Wither dealt ×1.5, guts regen +40%, but enemies get +1 advantage against you |
| Bulwark | 3 hits taken in a row | (100 − guts)/3 % | Damage taken ×0.7, regen +40%, damage dealt ×0.6 |
| Clutch | Last 10 s and behind on HP% | (HP% gap)/2 % | Crit chance ×2 until the end |
| Composure | 4 hits or dodges in a row | (100 − guts)/3 % | Costs −30%, the opponent gets a disadvantage, but damage taken ×1.5 |

### 12.8 Breed traits

Each breed has one trait (CONTENT §2), applied as multipliers or bonuses. Traits are never inherited from the sub-breed. M10 gave Gilded a battle side: it gains 7 guts each time it lands a hit (`BATTLE_TRAITS.gildedGutsOnHit`), besides its prize and chore bonuses.

### 12.9 Ending a match

- **KO:** HP reaches 0.
- **Time up:** the higher **HP %** (truncated to 0.1%) wins; equal is a draw.
- **Forfeit:** from the pause menu, with confirmation. It counts as a loss.

### 12.10 CPU AI 2.0 (tested; also used by Auto mode and the Battle Lab)

M10 replaced the v1.0 brain (a per-tick use-rate roll in its own best band) with a planning brain. It stays
deterministic (the injected RNG only, integer math) and only changes *decisions*; what a monster can do is
still §12.1–§12.9. Every number lives in `tuning.ts` under `AI`.

**Skill tiers.** A fighter's tier sets its reaction delay (how long a decided technique or push waits), its
mistake chance (a random acceptable band instead of the best, kept for 2–4 s) and the pause after a technique:

| Tier | Who | Reaction | Mistakes | Pause after a technique | Reads |
|---|---|---|---|---|---|
| Rookie | NPCs at grades E–D | 18–30 ticks | 20 % | 45–90 ticks | Own offense only (no threat), holds 45 guts before attacking |
| Skilled | NPCs at grades C–B | 10–20 ticks | 8 % | 36–84 ticks | Everything but the special and trait reads |
| Expert | NPCs at A–S, every opponent in a Crown, the Masquerade and the Legend Cup, rivals from grade C, Journey Trials from grade B, **the player's Auto mode**, Versus and the Battle Lab | 6–12 ticks | 2 % | 33–78 ticks | Everything |

NPC personalities multiply on top (aggression / caution / Wither, Far and Close biases / the poke horizon / the
pause): Steady 1.0/1.0, Aggressive 1.3/0.7 (pause ×0.7), Cautious 0.8/1.4 (pause ×1.4), Trickster (Wither ×1.5),
Sniper (Far ×1.5, Close ×0.8), Brawler 1.2/0.8 (Close ×1.5, Far ×0.8). Rival habits (CONTENT §10) still apply:
walks Close, opens Far, backs away when approached, pushes whenever touching, waits at 99, banks 70 for a
Heavy, spams Wither, steals guts, dashes below half HP.

**Think loop.** A fighter re-plans every 8–12 ticks, and at once when it is hit, when the opponent fires, when
its own or the opponent's affordable techniques change (a cost was crossed), when it becomes cornered or
touching, and at 20 s and 10 s left. Between plans it executes the plan: walk to the sweet spot, push, dash, fire.
The opponent's direction and target band are read from the *previous* tick, so neither side sees the other's
same-tick decisions.

**The range plan.** For each band b = 1…4 that holds one of my techniques:

```
offense(b) = max over my techniques at b of  EV(t) × min(1, guts regenerated in 10 s ÷ cost(t))   (×1.2 when affordable now; Far/Close biases)
threat(b)  = the same from the opponent's side (its techniques, its guts, its stats against mine)
variety(b) = up to 30 % of offense(b) (at most 4,000) for a band unused in the last 10 s, decaying to 0 right after use
travel(b)  = ticks to reach b's sweet spot at my speed (capped at 5 s); +90 ticks when the opponent wants a closer band
             and is not slower than my backing speed (I cannot hold b); unreachable when b's near edge needs more room
             behind me than the wall allows and no push is coming
score(b)   = offense(b) × aggression − threat(b) × caution × 0.5 + variety(b) − travel(b) × 6
EV(t)      = hit% × (expected damage as % of the target's max HP + 0.35 × wither) + 0.05 × sharp
```

The threat term counts half so that a mirror still picks its own best band. The target changes only when a band
beats the current one by ≥ 15 % (at least 100 points). The **sweet spot** is the edge of the target band farthest
from the opponent's strongest band, 25 units inside it (the centre when they coincide; never inside touching
range). Rookies use caution 0.

**Attack choice.** The goal technique is the best-value technique at the target band that is affordable within
8 s of regen. Value is EV adjusted by: a Heavy whose hit chance is under 40 % counts ×0.6 unless guts ≥ 80;
+30 % in a punish window (the opponent cannot afford any technique, or is mid-animation, dawdling or stunned);
Wither +40 % against a slow guts rate (≥ 13) or an expensive best technique; a heal is worth the HP it restores
when HP ≤ 40 % and the threat here is low (×1.5 for Blessed and Green Thumb); +15 % for a technique unused for
10 s; the personality's Wither bias; the rival habits.

**Save or spend.** When the cooldown is over and something is affordable in range: fire the goal when it is
here and affordable; otherwise fire the best technique in range when its value is at least 60 % of the goal's,
or when the goal cannot be afforded within 6 s of regen anyway (the personality's and the Auto style's save
bias scale that horizon); always fire when sitting on 90 + guts, when the opponent is broke, when hit within the
last second, or to break a stall; otherwise save. A decided technique fires after the tier's reaction delay and
is re-checked then (band, cost, cooldown, the reserve rules). The old per-tick use-rate roll is gone; the
4–12 attacks target (§26) is kept by the pause after a technique.

**Movement.** Walk to the sweet spot ± a footsie wobble of 15–30 units every 1–3 s (Statue Pose never wobbles
and holds its ground whenever it has something to fire from here). Never walk backwards into the wall for more
than half a second. Cornered (less than 120 units behind me) and wanting distance → push when touching, otherwise
fight at the best band I can hold; a band whose near edge needs more room than I have is out of the plan.
Caught at Close with nothing to fire there, or cornered, a fighter steps in to touch and shoves.

**Push** when touching and the push is off cooldown, if the target band is ≥ 2, or the opponent out-damages me
at Close, or my back is within 120 units of the wall (Unshakable ignores the corner), never into an Unshakable
except to break a stall. **Anti-stall:** touching for over 1 s with neither side attacking → push (if allowed),
else step back, else fire a Close technique; over 2 s → push if available, otherwise back off.

**Dash** when the target band is closer, the gap allows it and the dash still leaves enough guts for a technique
at the target band, and one of: the opponent is in a punish window; I am behind with ≤ 15 s left; the goal is
≥ 2 bands closer; the opponent is kiting me (wants a farther band than I do); Battering Ram and the Aggressive
Auto style dash freely. The old per-tick dash roll is gone.

**Situation modifiers** (Skilled: the clock and HP only; Expert: all):

| Situation | Effect |
|---|---|
| Ahead on HP %, ≤ 20 s left | caution ×2 ("playing safe") |
| Behind, ≤ 15 s left | aggression ×1.5, caution ×0.5 |
| HP ≤ 30 % (and not behind late) | caution ×1.5 |
| The opponent can afford its best Heavy | caution ×1.3 at that Heavy's band |
| The opponent is in a punish window | caution ×0.3 |
| The opponent has Valor or Clutch active | caution ×1.5 |
| I have Valor or Clutch active | aggression ×1.3 |

Traits the brain reads: Statue Pose (above), Unshakable (ignores push and corner threats), Chill (farther bands
+800 for 3 s after landing a hit), Blessed and Green Thumb (heals ×1.5 in value), Battering Ram (dashes freely).

**The v1 brain** (`aiV1.ts`, `AI_V1` in tuning) is kept only so a test can compare the two; nothing in the game
uses it. Head to head they are about even: greedy poking is close to optimal for damage in this guts economy, and
AI 2.0's gains are positional (kiting kits win with it; brawlers win with it against casters they can shove).

**Acceptance (ai2.test.ts, seeded, ten varied pairs):** never touching for 2.5 s without a push, an attack or a
step back, touching under 25 % of the time; a push in ≥ 80 % of touching battles where a side's best band is
≥ 2; kits with ≥ 3 bands use ≥ 2 in ≥ 70 % of battles and 3 in ≥ 40 %; ≥ 4 direction changes per monster per
match; an Expert beats a Rookie ≥ 70 % at equal stats and is not worse than v1 across the pairs; Expert mirrors
45–55 %; a broke opponent is punished within 0.6 s in ≥ 75 % of windows; an Expert ahead in the last 20 s stays
out of the opponent's best band more than earlier; the same seed gives the same log (plan events included);
decisions cost well under 0.1 ms per monster per tick.

### 12.11 Touch controls and screen (MUST)

**Portrait, one-handed. Everything interactive sits in the bottom 45% of the screen.**
- **Top:** names, HP bars, guts bars (with the number in Lens mode), timer, and the active-special badge.
- **Middle (the arena):**
  - The two monsters in side view, drawn through the **arena camera** (M10): the camera centres on the two
    monsters' midpoint and zooms so both sprites, plus a margin, fill the arena width, clamped between "the whole
    arena fits" and a zoom where one sprite is at most 45 % of the width (and leaves room for the ruler); the view
    never shows past the walls. A critically damped spring smooths it (a gentle ease with Reduce motion). Sprites
    scale with the zoom; a sprite's box is 200 units wide against a 160-unit body (`bodyRadius` 80), so touching
    looks like touching and a monster pinned to a wall stays fully on screen. Fence posts mark the walls.
  - A range ruler under them: four tinted bands with a marker showing the current gap (not through the camera).
  - Floating damage numbers, "Crit!", "Miss" and "?!" bubbles.
  - **Thinking icons** (M10): a small icon over each monster shows its current plan when "Show battle thinking"
    is on (Settings; default on in Breeder's Lens, off otherwise): 🛡 keeping distance · ⏳ saving guts ·
    ⚡ pressing · ↔ pushing away · ❗ punish! · 🏳 playing safe · 🧱 cornered. A mode is held at least half a
    second so it reads as a thought.
- **Bottom (the technique panel):**
  - Four columns: Close, Near, Mid, Far. Each holds that range's technique cards, showing name, guts cost and live hit %; swipe vertically if there are more than 3.
  - The column matching the current range glows. Unaffordable cards are dimmed.
  - **Tap a glowing card to fire.**
  - **Assist** (setting, default on): tapping a card in another column walks toward that range and fires on arrival, as long as guts are still enough. Tap again to cancel.
- **Movement:** hold the ◀ or ▶ thumb pads to walk. Double-tap the forward pad to dash. A Push button appears only when touching.
- **Other buttons:** Auto toggle (always shown on your side: one tap hands the match to the brain, another takes it back), speed (×1, ×2, ×4), pause (forfeit and settings).
- **Auto styles** (M10): the player's Auto plays as an Expert with a style chosen in Settings or the pause
  sheet: **Balanced** (default), **Aggressive** (aggression ×1.4, caution ×0.6, Close ×1.4, shorter pauses,
  dashes freely, pokes sooner) or **Defensive** (aggression ×0.7, caution ×1.5, Far ×1.4, longer pauses, saves
  longer). The style travels with the Auto input, so replays stay deterministic.
- **Each of your matches: Fight, Auto, or Skip. Auto can be taken over at any time.** This holds in every event (cups,
  Opens, the Officials, the Crowns, the Legend, the Masquerade, the Rival Showdown, the Summit Qualifier, your Summit
  leg) and in the Journey Trial.
  - Your side is always under your control. Auto is the engine's own `auto` flag, switched on by an input recorded at
    the first tick, so a replay stays exact; on Auto your side plays as an Expert (§12.10) with your saved Auto style.
  - **Skip** simulates the match at once, giving exactly the result an untouched Auto run on the same seed would give.
    Each cup match has its own seed from the cup's seed and its place in the schedule.
  - The cup entry screen sets the **default for this cup** (Fight or Auto). It starts on Fight and remembers your last
    choice; it only decides which of the three buttons is highlighted. It is kept in the save as `tournament.mode`
    (`manual` = Fight).
- **Feedback:** haptic tick on hits on Android (`navigator.vibrate`; iOS has none). Screen shake ≤ 4 px, and none with reduced motion.

### 12.12 Balance targets (must pass in automated tests; see §26)

---

## 13. Tournaments and ranks (MUST; calendar in CONTENT §9)

**Grades:** E → D → C → B → A → S. Every new monster starts at E.

**Entry:**
- **Officials:** your own grade only.
- **Regular cups:**
  - your grade, or one grade above;
  - or any grade below, which costs −2 fame and −2 loyalty ("too easy");
  - plus any special restriction (nature, age, technique type).
- **A monster can't enter while** injured or sick, or during a Journey or Expedition.

**Formats:**
- **Officials:** round robin of 6 (5 matches).
- **Regular cups:** round robin of 4 (3 matches) or elimination of 4 (2 matches).
- **Opens:** elimination of 8, seeded so that you meet your own grade ±1.
- **Invitationals:** 1v1 or round robin of 4.

**Schedules:**
- **Round robins** are drawn by the circle method from the cup's seed: RR4 is 3 rounds of 2 matches, RR6 is 5 rounds of 3.
  - Every pair meets once, and everyone, you included, fights exactly once per round.
  - Corin is your last-round opponent; if he isn't in the cup, the opponent with the highest stat total is.
- **Elimination** cups keep their rounds: Elim4 has 2, Elim8 has 3. A 1v1 and the Summit leg are one match.
- A cup saved before v1.4 keeps its stored schedule (one round per pairing, your matches first) and finishes normally.

**Playing a cup, a round at a time:**
1. **Round preview** ("Round 2 of 5"): every pairing, yours highlighted, and Fight / Auto / Skip for your match.
2. **Your match.**
3. **The round's other matches resolve**, shown as "Round 2 results": the winner, KO / decision / time-out, and HP left.
4. **Updated standings** ("After round 2 of 5"): place changes since the last round (▲/▼), points, W-L-D and KOs, counting only the rounds played so far.
5. **The next round.**

- No match is ever simulated ahead of the current round.
- A **walkover** (your opponent withdrew after a KO) wins your round without a fight.
- **Knocked out yourself**, you can watch the remaining rounds one at a time, or "Skip to final standings".

**The tournament breakdown** (on the cup screen):
- Tabs: **Standings | Rounds | Bracket** (the Bracket for elimination cups).
  - **Rounds** lists every round: who fights whom, results for finished matches, "upcoming" for the rest.
  - **Bracket** draws the elimination tree; a future slot reads "Winner of A vs B".
- Tapping a finished match shows how it ended, the HP left and the time.
- An NPC-vs-NPC match can be **watched again**. The replay uses the same fighters, tiers and seed as the recorded match, with no inputs, so it ends the same way.
- **The Summit** shows **Team | Legs**:
  - **Team** is the Vale–Coast score.
  - **Legs** shows the five grade legs. Your leg is the real, fightable match; the four NPC legs show their results (replayed from the cup's seed, so they always match the score kept at entry).

**Points and placing:**
- Points: KO win 4 · win 3 · draw 2 · loss 0.
- Ties break by head-to-head, then KO count, then total HP% remaining.
- **A KO'd monster withdraws** from its remaining matches, which count as losses.

**Prizes:**
- Purse to 1st; 2nd gets 40%; 3rd gets 20%; +50G × gradeIndex per match won.
- Officials pay little; promotion is the reward.
- Gentle mode multiplies prizes ×1.25.
- **Item prizes** for 1st place, on top of the purse:

| Event | Item prize |
|---|---|
| E–D cups | 3 random Stat Sweets |
| C–B cups | A random Basic, Hit, Wither or Sharp universal Songsheet, or a Grand Sweet |
| A–S cups | 2 Grand Sweets, plus a 30% chance of a Heavy or Special universal Songsheet |
| Official win | A Wondercake |
| Crowns | The Signature Songsheet of your monster's breed, or a Potential Pearl if you already own it |
| Legend Cup | A Tempo Bell and 3 Wondercakes |

**Promotion and breeder rank:**
- Winning your grade's Official promotes the monster one grade. The **first** Official win at each grade E–S, by any monster, raises breeder rank 1 → 6.
- Winning the S Official also earns an invitation to the next **Crown**.
- **Crowns:** four S invitationals, one per season, round robin of 4. Each win invites you to the next one.
  - **Special cups scale with you (M9):** the Masquerade Cup, the Crowns and the Legend Cup generate their opponents at your monster's stat total (`TOURNAMENT.specialScalePct`, never below the grade's band), so they stay a fight for a monster far above its band. Corin follows you all the way at the Crowns; in the Officials he stays inside the grade's band.
  - The first win of each Crown raises breeder rank 7 → 10.
  - Rank 10 rolls the credits ("The Wildsong Rises"), then play continues.
- **Legend Cup:** invitation in March once a monster has won **all four Crowns**, over any number of years. A 1v1 in April week 4. A win puts that monster in the **Hall of Fame**.

**Fame:**
- Gains: win a regular cup +2 (E) … +6 (S); win an Official +5 (E) … +10 (S); win a Crown +10; win the Legend Cup +15.
- Losses: −1 per tournament without a podium.
- The cap is 100.
- Fame boosts crit chance and gates expeditions and rumors.

**After a tournament** (whole event):

| Placing | Fatigue | Stress | Lifespan |
|---|---|---|---|
| 1st | +25 | −35 | −(1 + strainExtra) |
| 2nd–3rd | +30 | −28 | −(1 + strainExtra) |
| 4th or lower | +38 | −18 | −(1 + strainExtra) |
| Was KO'd | +10 more | — | −2 more, plus injury roll (Standard: 5% + fatigue/2 %); injured = 2–4 weeks of Rest only, −2 weeks |

- **Stat growth:** finishing in the top 3 raises 3 random stats by a random amount by grade: E 1–5, D 2–6, C 2–8, B 3–9, A 4–11, S and above 5–13. +1 if the monster likes battle, −1 if it dislikes it.

**NPC opponents** (generated):

| | E | D | C | B | A | S | Crown | Legend |
|---|---|---|---|---|---|---|---|---|
| Total stats | 520–800 | 800–1,150 | 1,150–1,550 | 1,550–2,000 | 2,000–2,450 | 2,450–2,900 | 2,900–3,300 | 3,500–3,800 |
| Loyalty | 50–65 | 55–70 | 60–75 | 65–80 | 70–85 | 80–95 | 85–95 | 95 |
| Fame | 5–15 | 10–25 | 20–35 | 30–50 | 45–65 | 60–80 | 75–90 | 100 |

- **Stats** are distributed by breed growth grades with weight `0.9 + gf`, plus ±8% personal noise (M9 raised the base from 0.6 so generated walls and cannons are a little less extreme).
- **Techniques** by grade:
  - E: Basics only.
  - D: + Hit.
  - C: + one of Wither or Sharp.
  - B: + Heavy.
  - A: + the other of Wither/Sharp, plus a Chain at 50%.
  - S and above: all non-Signature techniques, plus Special.
  - Pure-breed bosses also get their Signature.
  - From grade B, NPCs also know 1–2 universal techniques that suit their stats.
- **Personality:** from CONTENT rivals; otherwise random.
- **Seeding:** deterministic from (year, week, cup id).

---

## 14. Monster creation

### 14.1 The Shrine of Echoes (MUST)

**Input:** two fields, "Song or phrase" (required) and "Artist or second word" (optional).

**Normalize:**
1. Unicode NFKC.
2. Lowercase.
3. Trim.
4. Collapse whitespace to one space.
5. Strip punctuation except letters and digits of any script.

So "Hello,  World!" equals "hello world".

**Hash:**
- Use a pure-TypeScript 53-bit string hash (cyrb53-style, implemented in `core/hash.ts` with tests). It must be synchronous and identical on every device.
- `h1 = hash(phrase, 1)`; `h2 = hash(artist || phrase, 2)`.
- Seed a `mulberry32` RNG from `h1 ^ h2`.

**Derive, in this order** (order is part of the contract; changing it changes every monster):
1. **Main breed:**
   - Weighted pick by breed `commonness` (CONTENT §2) among **all** breeds.
   - If the result is locked, the stone hums with a teaser such as "…a sleeping power, heavy as stone…" and **no monster is made**.
   - The phrase is saved to the Journal's **Sleeping Stones** list. When that breed unlocks, the stone wakes and can be tapped to create the monster for free.
2. **Sub breed:** from `h2`, weighted by commonness among unlocked breeds.
3. **Stat offsets:** −10…+20 per stat.
4. **Lifespan offset:** −10…+30 weeks.
5. **Guts rate:** ±1 (bounded 6–20).
6. **Personality:** liked food, disliked food, favorite toy, battle like, liked drill, disliked drill.
7. **Starting nature:** −30…+30.
8. **Name suggestion.**

**Secret phrases** (CONTENT §12) map to special variants. Store them as hashes so they aren't readable in the source.

**Other buttons and behavior:**
- **Randomize** generates a random phrase from a word list and shows it.
- **Encyclopedia:** any monster ever created can be re-created for 500G.
- **Cost:** creation is free. If a monster is already active, the new one goes to the Freezer, or the player releases one.

### 14.2 Market (MUST)

- Four starters are always available (Puddlepup, Tumblefox, Quillion and Pluckrex), plus one seasonal breed (CONTENT §2).
- The first monster is free; after that 1,500G, or 2,500G for the seasonal breed.
- Market monsters use fixed seeds (so they are the same for everyone) with zero offsets.

### 14.3 Main/sub mixing (MUST)

| Aspect | Rule |
|---|---|
| Body, kit, trait, growth type | Main breed |
| Base stats | round(0.75·main + 0.25·sub) + shrine offsets |
| Growth grades | Main's grades; then **+1 step** on the sub's best stat (cap A) and **−1 step** on the sub's worst stat (min E). Ties are broken in the order LIF, POW, INT, SKI, SPD, DEF |
| Guts rate | main + round((sub − main)/4), then the shrine offset |
| Lifespan | §7 (60/40 blend, pure +10%) |
| Palette | Sub's palette on the main body; the main's eyes and markings stay |
| Accent | One accent part from the sub (CONTENT §2 "accent"), e.g. its ears, tail or frills |
| Techniques | Main's kit + the sub's quirk technique |
| Pure (main = sub) | +10% lifespan, the classic palette, Signature technique access, "(Pure)" badge |
| Variant name | "{sub adjective} {Main name}", e.g. "Cinder Puddlepup"; pure → "Puddlepup" |

That gives 30 × 30 = 900 combinations, plus special variants.

---

## 15. Fusion at Dr. Pell's Lab (MUST)

- **Inputs:** two **frozen** monsters plus a 1,000G fee, and optionally one catalyst item.
- **Output:** the baby goes to the Freezer, or becomes active if the ranch is empty.
- **The parents become Ancestors.** They move to the Memorial with a "Fused" badge and are never deleted. The baby's Monster Card shows the family tree.

**Outcome odds:**
1. Candidate mains come from {P1.main, P2.main, P1.sub, P2.sub}, weighted 4 / 3 / 2 / 1 (duplicates add up).
2. Candidate subs are weighted P2.main 3, P1.sub 2, P2.sub 2, P1.main 1.
3. `weight(main, sub) = mainW · subW · lineageStrength(main)/5` (strength 1–10, CONTENT §2).
4. Remove locked mains. Normalize, drop anything under 1%, and show up to 6 outcomes with %.
5. **Lineage Seal** catalyst: doubles P1.main's main weight.

**Compatibility:**
- Rank each parent's stats by value (1–6).
- Rank the baby breed's stats by growth grade, with ties broken by base stat.
- `M` = the number of stats where the baby's rank equals **either** parent's rank (0–6).
- Dr. Pell's comment by M:
  - 0–1: "These two don't quite click."
  - 2–3: "A decent match."
  - 4–5: "A wonderful match!"
  - 6: "Perfect harmony!"

**Baby stats:**
```
offset_i  = max(0, (2·(P1_i − P1base_i) + (P2_i − P2base_i)) / 3)     (base = that parent's breed base at birth)
P         = 0.20 + 0.09·M                                            (20%…74%)
K (rarity of the chosen outcome) = ≤2% → 1.0 · ≤7% → 0.85 · ≤15% → 0.7 · ≤30% → 0.6 · ≤50% → 0.5 · >50% → 0.4
baby_i    = babyBase_i + round(offset_i · P · K) + catalyst_i       → clamp 999
```

**Inheritance:**
- Growth grades, guts rate, lifespan and trait always come from the baby's own breed (lineages raise starting stats, not growth).
- **Techniques:**
  - Same main breed as P1: inherit 2/3 of P1's learned non-Basic techniques (rounded down), with uses and levels.
  - Different main breed: up to one technique per family, taken from either parent's techniques that exist in the baby's breed kit.
- **Nature and form:** (2·P1 + P2)/3.
- **Generation:** max(parent generations) + 1.

**Catalysts** (CONTENT §6): stat shards (+40 to one stat), Amber Charm (+20 weeks lifespan), Lineage Seal.

---

## 16. Freezer, Memorial, Heartstones, Hall of Fame (MUST)

- **Freezer:** 20 slots. Freezing and thawing are free and instant; time stops for frozen monsters. Frozen monsters can be used in Fusion, Versus and the Battle Lab, and can be exported.
- **Memorial:** every monster that passed away, retired or fused. It shows:
  - portrait, name and variant;
  - lifespan lived vs. total;
  - records and titles;
  - cause (old age, fused, retired, or Classic-mode injury);
  - the epitaph.
  Name and epitaph can be edited in place. "Duplicate to edit" makes a fully editable copy in the Library; the Memorial record itself stays as it was.
- **Heartstone:**
  - Created when a monster passes away or retires. At most 10 are stored (15 with the Lantern Garden).
  - It can be given to one monster aged under 48 weeks that has not received one.
  - It grants +15% of the donor's trained gains (`stat − breedBase`) per stat, capped at +60 per stat.
  - It also grants the **Heirloom**: +3 hit for techniques of the donor's most-used family.
- **Hall of Fame:** Legend Cup winners, with portrait, lineage and date. Edited monsters show their badge.

---

## 17. Expeditions (MUST)

- **Invitations:** expeditions are invitation-only and arrive by mail in fixed months (CONTENT §8). The letter states the requirements openly (grade, fame).
- **Time:** an expedition takes 4 in-game weeks with normal aging. Afterwards: fatigue +40, stress −10.
- **The map:**
  - A tap-to-move node map of 12–16 nodes, with branching paths and a camp node to exit.
  - **Stamina** = 50 + LIF/8. Each step costs 5–12 stamina.
  - At 0 stamina the trip ends and the monster limps home. No loot is lost.
- **Node types:**

| Node | What happens |
|---|---|
| Path | Nothing |
| Obstacle | Boulder (POW), riddle door (INT), snare (SKI), chasm (SPD), gale (DEF). Passing it needs stat ≥ threshold; otherwise detour (+10 stamina) or skip the branch |
| Search spot | Visible spots always search. Hidden spots appear only if INT ≥ threshold |
| Fog | A "lost" check: `max(5%, 30% − INT/30)`. If lost: −10 stamina and a random reposition |
| Treasure | Loot |
| Event | Site-specific (e.g. the strange chest) |
| Camp | Exit |

- **Retreat:** possible at any time, keeping everything found.
- **Rewards:** gold loot to sell, toys, charms, catalysts, fruits (rare), key items for unlocks.
- **Odds are fair:** each site has a guaranteed key-item route for a monster that meets its stated thresholds, so unlocks don't depend on luck alone.

---

## 18. Unlocks, secrets and the Journal (MUST)

- **Locked breeds:** 8 of the 30 breeds start locked (CONTENT §11). Each unlock chain uses a different kind of trigger:
  - care-based metamorphosis
  - a memorial event after a natural death
  - a seasonal weather event with condition checks
  - a rumor followed by a secret invitational
  - an expedition key item
  - a ranch upgrade
  - an expedition rare encounter with a pity timer
  - championship glory
- **Rumors:** shop gossip, mail and rival chatter hint at each chain. The **Journal** keeps a Rumors page whose hints sharpen as you make progress.
- **Nothing is permanently missable.** Every event recurs yearly or can be retriggered, and no unlock requires sacrificing a favorite monster (any natural death or retirement counts).
- **Journal pages:**
  - **Encyclopedia:** breeds and variants seen or owned.
  - **Sleeping Stones.**
  - **Rumors.**
  - **Records:** best totals, cups won, oldest monster.
  - **Titles** (CONTENT §14).
  - **Hall of Fame.**

---

## 19. Monster Lab: load, create, edit (MUST; core feature the owner asked for)

**Where:** the title screen ("Monster Lab"), and Town → Lab → Monster Lab. Its tabs are Library, Create, Import, Versus and Battle Lab.

**Edit any monster you own, any time.**
- **Except:** mid-battle, on an expedition map, or while a Journey sequence is playing. The button is greyed out with a reason ("Finish the battle first").
- **One tap gets you there:**
  - Ranch → tap your monster → Monster Card → **✏️ Edit**.
  - Right after creating a monster (Shrine result, Market purchase, Fusion baby): **Edit before you start**.
  - Freezer → a monster → **Edit**, or Monster Lab → Library → any monster → **Edit**.
- **No strings attached:** editing is free, needs no special mode, and never locks you out of anything.
- Saving edits to your active monster updates the save slot immediately (autosave), and the ranch shows the change right away.

**Library (global, shared by all save slots):**
- **Sources:** Active monster, Freezer, Library (saved Lab creations), Memorial (read-only), and Presets.
  - Presets: every breed's pure baby, plus trained presets at E/C/A/S power, generated with `scaleToTotal`.
- Filter by breed, source and badge. Sort by total, age, name or date.
- **Card:** portrait, name, variant, total, grade, and badges (Edited 🔧, Frozen ❄️, Memorial 🕯️, Pure ✦).
- **Actions:** View · Edit · Duplicate · Export · Send to Freezer (if there's room) · Make Active (with a confirm that the current one goes to the Freezer) · Delete (Library only, with confirm) · Battle (Versus).

**Create:** start from a breed (main and sub pickers with portraits), from a phrase (Shrine preview), or from a blank template. The editor can use any breed or variant, even undiscovered ones; those ask "Not discovered yet. Use anyway?" so players who enjoy discovery aren't spoiled by accident.

**Editor sections** (live SVG preview pinned at the top; every change re-renders):
1. **Identity:** name, main, sub, variant (any; undiscovered ones ask for confirmation).
2. **Stats:**
   - Six sliders (1–999) with ±1 and ±10 steppers and a number field. The total is shown.
   - Buttons: Breed base · Max all · Scale to total… (distributes by growth grades) · Randomize (seeded).
3. **Growth:** grades E–A per stat, growth type, guts rate (6–20), lifespan total and age in weeks, with a life-stage preview bar. "Reset to breed default" is available.
4. **Condition:** fatigue, stress, spoil, fear (loyalty and style shown live), nature, form, fame, injured/sick weeks.
5. **Personality:** liked and disliked food, favorite toy, battle like, liked and disliked drill.
6. **Techniques:**
   - The learned list with uses and level.
   - Add from the breed kit, the sub's quirk and all universal techniques. An **Allow any technique** checkbox in the editor adds from all 294.
   - Set uses and level; remove.
7. **Records** (optional): grade, wins and losses, titles.
8. **Appearance:** palette (main, sub or variant), size stage preview.

- **Validation:** all values are clamped and validated with clear inline messages. Nothing invalid can be saved.
- **Edited flag:**
  - Saving any change other than the name sets `flags.edited = true`.
  - Showing a 🔧 badge is a Settings option, **off by default**.
  - **There are no gameplay restrictions on edited monsters**; it's the player's game.
- **Save:** Save (back to its source) · Save as copy (to the Library) · Cancel.
- **Breed change:** techniques that aren't in the new kit are listed and removed on save, unless **Keep all techniques** is ticked. Trait, body and kit follow the new main breed.
- **Undo:**
  - **Revert** discards unsaved changes.
  - Every save keeps the previous version in the monster's **Edit history** (last 10), and **Restore** brings any of them back.
- **Edits vs. items:** the editor is "creative mode" and ignores prices. Items (§8, §10.5) are the in-game way to power up. Both are always available.

**Import:**
- Paste a share code, pick a file (`.json` or `.txt`), or open a link with `#import=CODE`.
- A preview card appears before accepting. Validate, migrate older versions, and give the monster a new id.

**Export:**
- **Share code:** `WS1-` + base64url(deflate-raw(JSON)). Use `CompressionStream` / `DecompressionStream`; no library needed.
- **File:** `.json` download, or Web Share as `.txt`. Chromium doesn't share `.json` files.
- **QR code** (`qrcode` package) of `https://<user>.github.io/<repo>/#import=CODE`.
- Copy-to-clipboard button.

**Versus:**
- Pick any two monsters from any source.
- **Modes:** You vs CPU, CPU vs CPU (watch). Local 2-player on one phone is LATER.
- **Options:** timer 60, 90 or 180 s; speed.
- **Exhibition only:** no fatigue, lifespan or record changes.

**Battle Lab:**
- Pick A and B, a number of battles (100, 500 or 1,000) and a seed (random or fixed).
- **Shows:** win / draw / KO %, average length, average damage per hit, hit rates, most-used techniques.
- Runs in a **Web Worker** with a progress bar. Results can be exported as CSV.

**Sandbox tools** (Settings → Sandbox, off by default): set money, give items, unlock all breeds, jump the calendar. Using any of them marks the save slot `sandbox` (badge on the save card).

---

## 20. Saving (MUST)

- **Storage:** IndexedDB via `idb-keyval`. Every key is prefixed `wildsong/`, because all GitHub Pages sites under one account share an origin.
- **Slots:**
  - 3 manual slots.
  - A rotating autosave with 3 backups, saved at the end of every week, after every battle, and on `visibilitychange → hidden`.
  - The global Library (with each monster's edit history) and Journal unlock data.
  - Each save slot also holds the inventory (unlimited quantities) and the **Songbook**.
- **Fallback:** the latest save is also mirrored as JSON in `localStorage`, in case IndexedDB is corrupted.
- **Versioning:**
  - Each save stores `schemaVersion` and goes through `migrate()`.
  - Every schema change bumps the version and adds a migration with a test.
  - Everything is validated with **valibot** on load and import: unknown fields are dropped, values clamped, and **never crash**; show a friendly error instead.
- **Persistence:**
  - Call `navigator.storage.persist()` after the first save. Show the persisted status in Settings.
  - Show a backup reminder every 7 real days or 8 in-game weeks (dismissible, with "Export now").
- **Export/import a full save:** the same code, file and share paths as monsters, with `kind: "save"`.
- **Determinism:** the RNG state is saved. Reloading an autosave and replaying the week can give a different result only if the player chooses differently. We don't fight save-scumming; it's a single-player game.

---

## 21. Screens and UX (MUST)

**Layout:**
- Portrait, designed for 360–430 px wide, scaling to tablets with a centered max width of 520 px.
- Bottom navigation, thumb-reachable, tap targets ≥ 44 px.
- One primary action per screen.
- Every animation is skippable, and there's a global speed setting.

| Screen | Key contents |
|---|---|
| Title | Continue · New Game · Load · Monster Lab · Settings · Credits/Disclaimer · version |
| New Game | Breeder name, ranch name, difficulty, first monster (Market gift or Shrine) |
| Ranch (home) | Monster on stage with idle animation and expression cues · calendar strip (date, weather, upcoming events; tap it for the Calendar; a "Next: {event} · in N wks" line, ★ for a starred one) · Wren's weekly report bubble · action bar: Train · Rest · Journey · Battle · Town · item button · "Repeat last week" |
| Train sheet | Light and Heavy tabs. Drill cards show stat arrows, stars, odds (by transparency mode) and the bonus/liked tags |
| Drill result | Short vignette (skippable) · banner (Great!/Success/Cheated…/Failed/Slacked off) · stat deltas · praise/scold gesture |
| Monster Card | Portrait · stats with grade letters and bars (plus "from sweets") · life bar · condition (per transparency) · techniques (by range, mastery) · personality · records · lineage tree · buttons: **Use item** · **Learn technique** (Songbook) · **✏️ Edit** |
| Bag | Every item with its quantity, by category · Use ×1 / ×5 / ×10 / Max |
| Songbook | Every Songsheet you own, filtered to what the current monster can learn (★ good fit) · Learn · Forget and relearn |
| Calendar (§3) | Today's date and month/year arrows (up to four years ahead) · Agenda / Month / Year · "Only events I can enter" and "Show expeditions" · event and expedition details with the entry answer, ★ and Enter (this week) |
| Town | Calendar · Shop (food, care items, Stat Sweets bakery counter, charms) · Market · Shrine · Lab (Freezer, Fusion, Memorial, Heartstones, Monster Lab; the Monster Lab also holds Versus, the Battle Lab and the **Effects Lab** (V1)) · Guild (this month's events, rank, Hall of Fame, **Guild Library** of Songsheets) · Mailbox · Odd Jobs |
| Tournament entry | This week's events: eligible ones first, ineligible ones with the reason · rules · purse · opponent cards (breed, grade, personality tag) · the default for this cup (Fight / Auto) |
| Cup (§13) | Round preview with every pairing and Fight / Auto / Skip · round results · standings after each round with ▲/▼ · the breakdown: Standings / Rounds / Bracket (the Summit: Team / Legs) · match details (how it ended, HP left, time) · Watch an NPC match again |
| Battle | §12.11 |
| Results | Placings, purse, fame, stat gains, condition changes, lifespan cost (Lens) |
| Journey | Mentor's Ledger → a 4-beat progress screen (skippable) → result (gains, technique learned, Trial) |
| Expedition | Node map |
| Shrine | Two inputs · Awaken button · stone animation · result card (with **Edit before you start**) · Randomize · Encyclopedia · Sleeping Stones |
| Fusion | Two Freezer pickers · catalyst · outcome odds · compatibility comment · confirm |
| Journal | Encyclopedia, Sleeping Stones, Rumors, Records, Titles, Hall of Fame |
| Settings | Sound, music, haptics · master, music and effects volume · text size · reduced motion · **Graphics: effects Quality (Auto / Ultra / High / Lite) and Intensity (Cozy / Standard / Flashy)** (V1) · transparency mode · difficulty (Gentle ↔ Standard) · speed · Assist · left-handed battle layout · backup/export/import (with the last backup time) · storage persistence status · check for updates · install help · item rule (Unlimited / One per week) · edited badge on/off · Sandbox tools · credits and disclaimer |
| Install help | iPhone and Android steps (`PHONE_AND_GITHUB_SETUP.md` part C), shown when not running standalone |

**Onboarding:**
- The first in-game month is guided by Wren: first drill, praise/scold, rest, food, the Monster Card.
- After that, contextual one-time tips: first request, first Journey, first tournament, prime, first breakdown.
- Tips can be replayed from the Journal.

---

## 22. Art direction (MUST)

**Procedural SVG "paper-doll" monsters.** Each breed's art brief is in CONTENT §2.
- **Body plans:** blob, quadruped, biped, serpent, avian, floater, shelled, insect, construct.
- **Parts:** each plan defines **sockets** (head, back, tail, ears, limbs) where parts attach. Parts are parametric SVG paths.
- **Colors:** palettes are CSS variables: `--body`, `--belly`, `--accent`, `--eye`, `--outline`. The sub breed swaps the palette and adds one accent part.
- **Expressions:** neutral, happy, tired, stressed, sad, angry, sleepy, sick, plus a sparkle overlay. They map to the cues in §6.6.
- **Style:** cozy storybook.
  - Thick rounded outlines (3–4 px at 256 px size, `stroke-linejoin: round`).
  - Flat fills plus one soft shading layer.
  - Big readable eyes and a warm palette.
- **Must not resemble existing characters.** If a design starts to resemble a well-known monster, change it.
- **Animation** (CSS and the Web Animations API; transform and opacity only):
  - Idle: breathe, blink, bob, tail or fin wag.
  - Drill vignettes: a prop plus a motion (log, puzzle stones, target, gourds, acorns, plow, moon, wind, waterfall, quarry).
  - Battle: the monster itself lunges, flashes white and slides back on a hit, flops on a KO and hops on a win (CSS); everything that flies, bursts, splashes, shakes or flashes is the effects layer below (V1).
  - Emotes: ♥, ?!, 💢, 💤.
- **Battle effects layer (V1, `docs/VISUAL_V1_EFFECTS.md`):** a transparent WebGL canvas (PixiJS 8, WebGL only; the chunk loads lazily on the battle, Versus and Effects Lab screens) sits over the arena in the same world units as the monsters and follows the arena camera. It draws 18 code-written primitives (burst, cone, trail, projectile, beam, ring, impact, splash, water sheet, lightning, haze, glow, debris, mist, flash, shake, hit-stop, impact frame) from a procedural texture atlas; no asset files. Every technique has an **element** (Fire, Water, Ice, Lightning, Wind, Earth, Nature, Light, Dark, Sound, Physical; CONTENT §3 Element column, assigned by the rules in VISUAL_V1_EFFECTS §5) that gives the primitives their colours, shapes, blend mode and flags. The battle store turns engine events into effect events (presentation only; the simulation never reads them) and V1 draws a default recipe per element for each moment; V2 adds per-technique recipes. Monsters stay DOM SVG; the canvas sits above them and below the floating numbers, so haze and filters only bend what the canvas draws. The layer sleeps when nothing is live and pauses when the app is hidden.
- **Graphics settings (V1):** **Quality** Ultra (2,500 particles, every filter, up to 2× resolution, 3 lightning passes) / High (1,200, bloom and shockwave only, 1.5×, 2) / Lite (400, no filters, 1×, 1). Auto starts at Ultra (High under 4 GB or 6 cores, Lite under data saver), measures the first battle's first 90 frames, drops one tier above 18 ms and two above 28 ms, and remembers the result. **Intensity** Cozy (no shake, hit-stop, impact frames or flash, bloom off, ×0.6 particles) / Standard (4 px shake, 60 ms hit-stop, impact frames on crits, flash alpha 0.2, low bloom) / Flashy (8 px, 120 ms, impact frames on heavy hits, flash 0.3, high bloom, ×1.4 particles). Reduced motion (the toggle or the OS) forces Cozy.
- **Backgrounds:** layered SVG (ranch, town, shrine, lab, arena, journey sites, expedition tiles) with seasonal tints and weather overlays.
- **UI icons:** a small in-house SVG icon set.
- **External art:** none, unless CC0. Log every asset in `CREDITS.md`.

**Growth forms** (added with breeds 21–30, 2026-10-22; source: `docs/NEW_MONSTERS.md` §5):
- **Hearthwing**, **Pluckrex** and **Paladove** have two looks: **young** for life stages 1–4 and **grown** from stage 5 (Prime). Every other breed has one look.
- The switch happens the week the monster enters Prime, with a short, skippable "grow up" moment (a glow, then the new form) and a Wren line ("{name} has grown up!"). The ranch scene for it arrives with M3; the Lab preview and the presets already switch by stage.
- The breed's art data carries an optional `grown` look; anything it leaves out falls back to the base look.
- **Mixes:** the main breed's forms apply. The sub breed's palette and accent part are used on both forms.
- Size by life stage still applies (young 70–85 %, grown 100 %). The form is derived from the life stage and never stored in a save.

**High-end phone polish** (same date; the owner plays on a Galaxy S25 Ultra-class phone; source: `docs/NEW_MONSTERS.md` §6):
- The procedural SVG system and its palettes stay, so every main/sub mix (30 × 30 = 900) recolours automatically. No pre-rendered images or 3D.
- **Richer shading:** a soft top-left-lit gradient on every body part plus a rim highlight; a soft contact shadow; optional subtle textures per breed (scales, fur strokes, stone grain, feathers).
- **More life:** secondary motion (ears, tails, wings, manes and tentacles lag slightly behind the body), squash-and-stretch on hops, and eyes that glance toward where the player taps.
- **Signature particles** in a lightweight layer, off under reduced motion: Hearthwing embers · Grumblestone crystal glints · Paladove light motes · Starhowl twinkles · Petalphant drifting petals · Scrollopus ink bubbles · Gloomgrin dust puffs · Frostlance snowflakes · one fitting effect for each older breed where it suits (rain for Nimbusheep, sparks for Zipwisp, steam for Gearhoot…).
- **Performance budget:** a steady 60 fps on that class of phone with the ranch scene, two animated monsters and particles. Library and picker thumbnails stay static. On weaker phones, or when the frame rate drops, particles are reduced automatically.

## 23. Audio (SHOULD)

- **Sound effects:** **ZzFX** (MIT): UI tap, drill result stingers, hit, crit, miss, KO, level-up, coin, mail, stone hum.
- **Music:** short original looping chiptune tracks (ranch by season, town, battle, victory, farewell, shrine), written in code with ZzFXM or a tiny step sequencer.
- **Volume:** master, music and effects volume; mute.
- **Unlock:** audio starts on the first `pointerup`.
- **iOS:** set `navigator.audioSession.type = 'ambient'` where supported, so the player's own music keeps playing.

## 24. Accessibility and comfort (MUST)

- Text size (100%, 115%, 130%).
- Respect `prefers-reduced-motion`, with a manual toggle too.
- Never use color alone: icons and labels on every bar and band.
- No flashing faster than 3 Hz: the effects layer's flash gate allows at most 3 screen flashes in any rolling second, never brighter than alpha 0.3, and Cozy / reduced motion turns them off entirely (V1).
- Shake, hit-stop and impact frames are Intensity settings and are all off under reduced motion (V1).
- Haptics toggle.
- Left-handed battle layout (mirrors the pads).
- All text readable at 360 px width.
- Screen-reader labels on buttons where practical.

## 25. Difficulty

See §7. The difficulty is shown on the save card.

## 26. Balance targets: automated tests (MUST)

These come from the pre-build simulations (§27). Implement them as Vitest "sim tests" with fixed seeds. Raising and battle targets are measured **without** Stat Sweets, Songsheets or Monster Lab edits; those are deliberate power boosts the player chooses. Tune **numbers in `tuning.ts`, technique values or traits** to pass; change formulas only with the user's approval.

**Raising** (simulate whole lives with scripted care policies; run each over at least 40 seeds):

| Care policy | Life lived vs. nominal | Notes |
|---|---|---|
| Great (rest at fatigue ≥ 45, stress items at ≥ 30, liked food, accept requests) | 82–92% | |
| Good (rest ≥ 55, items ≥ 40) | 76–88% | |
| OK (rest ≥ 65, items ≥ 55, half the requests) | 62–78% | |
| Neglect (rest ≥ 80, no items, cheap disliked food, deny requests) | 25–45% | Several breakdowns per life |

**Stat totals with Good care:**
- A Steady breed with mostly C grades: about 700 at year 1, 1,450 at year 3, 2,350 at year 5.
- A Late bloomer with A/B grades: about 2,550 at year 5 and 2,950 at year 6.
- Good care should reach grade S (about 2,450–2,900) by years 5–7 for strong breeds, and grade A for average ones.

**Drill outcome rates over a Good-care life:** Great 17–23%, Success 55–65%, Cheat 7–12%, Fail 8–14%.

**Battle** (AI 2.0 Expert vs Expert since M10, with stats from the NPC generator, alternating sides, at least 200 seeds per cell):

| Target | Range |
|---|---|
| Mirror match | 45–55% |
| +10% total stats | 62–80% win |
| +30% total stats | 85–96% win |
| Any two breeds at equal total (1,000 / 2,000 / 3,000) | every pair 25–75%, and ≥ 95% of pairs 30–70% (M10); Lootlid's mean win share 40–60% (other breeds' means are reported, not targets) |
| KO rate, even fights (the five starters' mirrors, averaged) | 15–35% at total 1,000; 3–15% at 3,000 |
| Attacks per monster per match | 4–12 |
| Match length when no KO | 60 s, by definition |

**Determinism:**
- The same seed and inputs give an identical battle log on repeat runs.
- 1,000 random seeds produce no NaN, no negative HP and no stuck states.

## 27. Simulation notes (why these numbers)

A Python prototype of §6, §7 and §12 was run before writing this spec:
- **Raising:** about 60 lives per breed per policy.
- **Battle:** 150–300 AI battles per matchup at 4 power levels.

**Key findings:**
- **Stress drives lifespan loss.** The first draft lost about 45% of a life even with good care, so drill stress was cut to light +4 / heavy +9, rest stress recovery was raised, and the strain threshold set to 80 with a step of 45 and a cap of 3.
- **Neglect has to be bounded.** Without breakdown events, neglect killed monsters at about 20% of their life. Breakdowns (which reset fatigue and stress) bring it to about 35% and create story moments.
- **The first AI attacked too rarely.** It waited for big moves and made only 2–4 attacks a minute. A probabilistic use-rate AI, in the style of the later games, gives 5–12.
- **Damage scaling.** Damage was flattened (`0.7 + A/180`) so a hit costs a similar share of HP at every level: basics about 8–11%, heavies about 37–49% at equal stats.
- **Guts-rate range.** Narrowing guts rates to 8–18 and giving fortress breeds −20 to −25% damage taken brought archetype matchups into roughly 35–65%. Fast-regen casters remain the strongest archetype, and walls the weakest, so watch them in tests.

## 28. Out of scope for v1 (LATER, but keep hooks)

- Sketch Stone: draw a doodle to seed a monster.
- Local 2-player Versus on one phone.
- Online or asynchronous leagues; share codes cover friend battles for now.
- Cloud sync.
- A second "trainee" stall from rank B, for two active monsters.
- Optional coach touch mini-games for drills. Each would be ≤ 15 s, skippable, at most once or twice a month, and able to move the result up by at most one tier.
- Localization: keep all strings in `src/data/text/`.
