# Research notes: what we learned from the series, and why the design looks the way it does

**What this is:** background reading for the owner and for Claude. It is **not** a source of names or data. Everything we build is original (see `CLAUDE.md`).

**How it was compiled (Oct 2026):** six parallel research passes covered:
- raising mechanics
- battles and tournaments
- rosters, creation and legacy systems
- fan-documented formulas
- phone and web technology
- series reception and fan wishlists

They drew on official Koei Tecmo manuals, fan research archives (mainly LegendCup), Japanese guide sites, Wikipedia, critic reviews and Steam/App Store discussions. Reddit itself couldn't be reached directly. Mechanics are summarized here in our own words.

---

## 1. The series at a glance, and what we took from each

| Game (year, platform) | What it did that mattered | What we took |
|---|---|---|
| **Monster Rancher** (1997, PS1) | Monsters generated from *any* CD; six stats; drills that were paid jobs; month-long expert training to learn techniques; finite lifespans; fame boosting crits; combining; bankruptcy game over | Generation from your own input; chore pay; the stat set; finite life. **Dropped:** bankruptcy game over |
| **Monster Rancher 2** (1999, PS1). *Fan consensus: the best* | Light and heavy drills; 4-week technique trips with stat requirements; four-range battles with withering and sharpness; hidden fear/spoil, stress, fatigue, nature and form; monster requests; weekly item limit; Freezer; combining with item catalysts; E–S ladder plus a top-four series and a capstone cup; secret world events; importing first-game monsters | **The backbone of our design:** drill economy, Journeys, the care model, 4-range battle, the ladder, Fusion, the Freezer |
| **Monster Rancher 3** (2001, PS2) | Habitats instead of a ranch; regional evolution through food; an Encyclopedia to re-create monsters without the disc; a dead monster leaves a heart that boosts the next one; techniques level up with use | Encyclopedia re-creation; **Heartstones**; technique mastery levels. **Dropped:** no ranch / no combining (fans disliked losing them) |
| **Monster Rancher 4** (2003, PS2) | Up to five monsters at once; a scheduling planner; party dungeons; ranch-vs-ranch play; first story-driven entry | The **planner**; bond-flavored legacy; a post-game exploration idea. **Dropped:** big multi-monster ranches (fans call it micromanagement and ask for *two*, not five) |
| **Monster Rancher EVO** (2005/06, PS2). *Series low point* | Circus troupe; 3-on-3 battles; automatic training; no old-age death | Lessons only: don't automate the core loop, don't remove finite life, don't bury 1v1 battles under team chaos |
| **Monster Rancher Advance / Advance 2** (2001–02, GBA) | Monsters created by **typing words**, with longer words unlocking at higher ranks; retirement instead of death; retirees become coaches; offspring blending both parents | **Text-seeded Shrine**; the **Gentle mode** retirement option; Elders as mentors |
| **Monster Farm DS / Monster Rancher DS** (2007–10, DS) | Draw or speak to create monsters; stylus battles; drills as passive animations (reviewers: "babysitting") | Large, simple touch controls. Sketch-to-seed is a LATER idea. **Lesson:** don't make the player passive |
| **Phone ports + Monster Rancher 1 & 2 DX** (2019–21) | Song database replacing CDs; high-speed mode; autosave; Freezer expanded to 20; prime notices for every monster; total-stat display; multi-buy; bug fixes such as double lifespan charges; online battles against stored monsters | **All the modern QoL**; 20-slot Freezer; prime notice for every monster; share-code friend battles |
| **Ultra Kaiju Monster Rancher** (2022, Switch) | Keyword-pair generation; transparent technique chance tiers; mentor bonds lowering requirements; weekly autosave; well-documented AI (frame loop, personalities, cooldowns) | **Mentor bond**; chance tiers in the Mentor's Ledger; the **AI model** |
| **LINE: Monster Farm** (2023, JP mobile) | Phone-native raising; generation from your social circle; touch battles. Reviewers complained of input lag, overshooting movement and unfair-feeling hit chances | Lessons for **touch battle controls**: target-band walking, assist, live hit % |
| **Mamon King** (2025, indie homage) | A modern, well-received take on the formula: weekly turns, lifespans, inheritance between generations | Confirms there's still an audience; inheritance makes later generations easier |

**If you want the real thing on your phone:** *Monster Rancher 1 & 2 DX* (Koei Tecmo, 2021) is on the US iPhone App Store (about $29.99 for both; also on Switch and Steam). As of this research there was no Western Android release.

---

## 2. What fans loved, what hurt, and how our design responds

| Fans loved | Our design |
|---|---|
| Monsters born from *your* CDs, plus rumors about which disc made what | Phrase-seeded Shrine (song title + artist, or any words). It's deterministic, so friends can share phrases, and there are secret phrases |
| Bonding with one monster through care | A single active monster; praise/scold with a swipe-to-pet gesture; requests; expressions that show its mood |
| Finite lifespan giving every week weight | Kept, with readable life stages and warnings |
| Deep, interlocking systems (drills, trips, combining, freezer) | All kept, using best-of versions |
| Secret events and unlocks | 8 unlock chains with varied triggers |

| Pain point | Our fix |
|---|---|
| Hidden numbers that needed fan tools to see | Three transparency modes, including the exact-number "Breeder's Lens" |
| Sudden or early deaths | Warnings at 25% left, 48 weeks and 10 weeks; Gentle mode; Heartstones; no KO death outside Classic mode |
| Unlocks that required a monster's death or could be missed forever | Any natural death counts; every event recurs; the Journal's rumor hints sharpen over time |
| Swingy RNG that ruins sessions | Visible odds; partial results on Cheat; requirements shown up front; weekly autosave |
| Slow, unskippable animations and expeditions | Skip and speed everywhere; short tap-to-move expedition maps; a planner |
| Shrine results that are locked monsters (DX) | A "Sleeping Stone" teaser that is saved and wakes later; locked breeds are rare in the hash |
| Money game over | Guild Loan |
| Too much prize money (late series) | Officials pay little; promotion is the reward |
| A thin top-grade calendar | Extra S-grade cups in our calendar |
| *(Owner's addition, not from the series)* Wanting a Pokémon-style way to power up | **Unlimited item use**, **Songsheets** that teach techniques instantly (kept in a Songbook) and **Stat Sweets** that add stats. The series' one-item-per-week rule survives only as an option, on by default in Classic difficulty |
| A rookie "open" cup full of strong opponents | The New Year Open matches you to your grade ±1 |
| Clunky phone battle controls | Big thumb pads, a range ruler, glowing technique columns, live hit %, Assist, Auto |

---

## 3. Mechanic-by-mechanic: what the games did and what we chose

- **Time.**
  - The series standard is a 1-week turn, 4-week months and quarterly official cups.
  - Kept. Added free actions that don't use a turn (Ultra Kaiju style) and an optional planner (MR4 style).
- **Drills.**
  - MR1's drills were paid jobs; MR2 split them into six light drills (one per stat) and four heavy drills (two stats up, one down).
  - Neither had a heavy drill whose main stat is accuracy. That "accuracy tax" forces build choices, so we kept it.
  - We revived MR1's fifth heavy pattern as an unlockable.
- **Drill outcomes.**
  - Fan research shows success depends on life stage, fatigue, fear, stress, spoil, nature and stat difficulty (stars), but the exact decision chart was never published as text.
  - We wrote our own transparent weighted formula using the same inputs, and simulated it (§5).
- **Gains.**
  - The series multiplies an aptitude grade (E–A) by a life-stage curve, with light and heavy caps.
  - We fitted our own smooth formula to that shape instead of copying tables.
- **Growth.**
  - Four growth types and ten stages, with a "prime" window. Fans valued the prime notice; DX gave it to every monster.
  - Kept both, under our own breakpoints.
- **Care.**
  - Fatigue and stress (0–100); spoil and fear forming loyalty; training style bands; nature; form; requests; food likes and dislikes.
  - Kept, with labels shown weekly instead of stress being reported only monthly.
- **Lifespan.**
  - The documented model is a weekly loss plus extra loss from combined fatigue and stress; tournaments, trips and drugs cost weeks; fruit items add weeks.
  - Kept in structure with our own constants, softened after simulation, with breakdown events added.
- **Technique learning.**
  - MR1 used one check at the end of training. MR2 rolled on each successful week against stat thresholds, with loyalty counting as a wildcard. Ultra Kaiju showed chance tiers and added mentor bonds.
  - We use MR2's structure, Ultra Kaiju's transparency and MR3's mastery levels.
- **Battle.**
  - MR1 and MR2 used real-time 1-D duels with four ranges. Guts start at 50 and cap at 99, regenerate per breed rate, and pause during your own attack.
  - Hit chance comes from skill vs speed plus guts. Damage comes from attack stat vs defense times technique force, with crits at ×1.5 and flat withering.
  - Low loyalty causes "foolery".
  - Kept all of it under our own formula shapes and constants, with the AI modeled on the well-documented later-game approach.
- **Tournaments.**
  - E–S grades; official cups each quarter; a top-four series; a capstone cup with a Hall of Fame; cups restricted by nature or age; a team relay every 4 years.
  - Kept, all renamed and re-scheduled.
- **Creation and mixing.**
  - The main breed sets body and kit; the sub-breed sets colors and accents. Hand-made combo tables existed in the originals.
  - We use a formula-based 20×20 system: every pair is valid.
- **Combining.**
  - MR2 weighted outcome odds by "blood strength", inherited a share of trained stats scaled by stat-rank compatibility and outcome rarity, and used catalysts.
  - Kept the shape with our own weights and percentages. Our parents become Ancestors instead of vanishing.
- **Storage and death.**
  - The originals had a Freezer (10 slots, later 20), permanent death, funerals and altars, and a Hall of Fame. MR3 had hearts; the GBA games had retirement.
  - Kept the best of each.
- **Exploration.**
  - MR1 and MR2 had invitation-only mazes with stat obstacles where you could get lost. MR4 had dungeons.
  - Kept short, phone-friendly maps with stated requirements and guaranteed key routes.

---

## 4. Phone and web technology findings (checked Oct 2026)

- **Stack:** Vite 8, TypeScript 6 (the template default; TS 7 still lacks its API for tooling), Preact 10 + signals, vite-plugin-pwa 2, Vitest 5.
  - Game engines (Phaser 4, PixiJS 8) are overkill for menus plus a two-monster duel, and keep logic out of a testable core.
- **GitHub Pages:**
  - Free for public repos.
  - Deploy with GitHub Actions; Vite's official guide uses checkout v7, setup-node v7, configure-pages v6, upload-pages-artifact v5 and deploy-pages v5.
  - `base` must be `/<repo>/`. Use hash routing, because Pages can't rewrite paths.
  - All Pages sites on one account share an origin, so prefix storage keys.
- **Installing on iOS:**
  - Since iOS 26, sites added to the Home Screen open as web apps by default ("Open as Web App" switch).
  - There's no install prompt, so show our own help card.
  - Audio must start on a user gesture. There's no vibration API.
- **Saves:**
  - IndexedDB.
  - Safari can clear a website's storage after 7 days of browser use without visiting it. Home Screen web apps have their own counter and are effectively safe when played regularly.
  - A Safari tab and the installed app don't share storage, so export/import is how saves move.
  - `navigator.storage.persist()` is supported (iOS 15.2+).
  - Chromium's Web Share won't share `.json` files, so share as `.txt`.
- **Share codes:** `CompressionStream('deflate-raw')` + base64url. It works in all major browsers, needs no library, and one monster comes to a few hundred characters (fits in a QR code).
- **Determinism:**
  - Keep floating-point transcendental functions out of game rules.
  - Use a saveable 32-bit PRNG (mulberry32) and a synchronous string hash.

---

## 5. Balance simulations run before writing the spec

A Python prototype of our raising and battle formulas was run. About 60 simulated lives per breed and care policy; 150–300 AI battles per matchup at four power levels.

**Raising:**
- **Draft 1 had a problem.** Even good care lost about 45% of a monster's life to stress, and neglect killed monsters at about 15%.
- **Fixes:**
  - Drill stress was lowered (light +4, heavy +9).
  - Rest stress recovery was raised.
  - The strain threshold was set to 80, with steps of 45, capped at +3 weeks.
  - Tournaments now cost 1 week + strain.
  - Breakdown events were added.
- **Final results:**

| Care | Life lived | Typical stat total at death |
|---|---|---|
| Great | ≈ 85% | 2,500–3,200 |
| Good | ≈ 80% | 2,300–3,150 |
| OK | ≈ 70% | 2,050–2,900 |
| Neglect | ≈ 35% | 1,000–1,900 (3–6 breakdowns) |

- **Climb pace:** with good care, a strong late bloomer passes about 2,850 total (S-grade range) around year 6. An average breed tops out around grade A or S late in life. Legend-level opponents (about 3,500+) need Fusion lineages, which matches the series' "super baby" culture.

**Battle:**
- **Draft 1's AI was too passive.** It waited for big moves and attacked only 2–4 times a minute. Switching to a probabilistic use-rate AI gave 5–12 attacks.
- **Damage was flattened** so a hit costs a similar share of HP at every level: basics about 8–11%, heavies about 37–49% at equal stats.
- **Matchups:**
  - Mirror matches come out 50/50.
  - +10% total stats → about 70% wins; +30% → about 90%.
  - After narrowing guts rates to 8–18 and adding fortress traits, archetype matchups fall mostly between 35% and 65%.
  - Fast-regen casters stay the strongest archetype, and walls the weakest. Watch these in M9 balance tests.

---

## 6. Originality and IP guardrails (facts, not legal advice)

- **Ownership:** Monster Rancher / Monster Farm is owned by Koei Tecmo, and "Monster Rancher" is its trademark. The franchise is active (DX in 2021, Ultra Kaiju in 2022, LINE in 2023).
- **US copyright law:**
  - Copyright protects art, music, characters, text and code, but **not** game rules, systems or methods (17 U.S.C. §102(b); US Copyright Office factsheet FL-108).
  - Names and titles can't be copyrighted but can be trademarks.
  - Cloning a game's *look and feel* can infringe, even when copying its rules doesn't (*Tetris v. Xio*, 2012).
- **Enforcement:**
  - GitHub's public DMCA archive shows takedowns of fan games that bundled ripped assets from other franchises.
  - No Koei Tecmo notices were found there. That's not a promise; it's why we stay original.
- **What we do:**
  - An original title, monsters, characters, places, items, technique names, art, sound and text.
  - No extracted game data. Our numbers are our own tuning, not copied tables (fan archives also ask for permission before their data is reproduced).
  - A clear non-affiliation disclaimer.
  - Non-commercial.
  - Every external asset logged (CC0 only).

---

## 7. Key sources

**Fan research archives:**
- LegendCup.com, an archive of community research on the series. Raising methods: https://legendcup.com/raisingmethodsmr2.php · https://legendcup.com/raisingmethodsmr1.php
- Techniques and errantry research: https://legendcup.com/faqmr2techs.php · battle calculator https://legendcup.com/faqmr2battlecalc.php
- Combining research: https://legendcup.com/mr2researchcombining.php · walkthroughs https://www.legendcup.com/faqmr2walkthrough.php · https://legendcup.com/faqmr1walkthrough.php
- Calendars: https://legendcup.com/faqmr2calendar.php · https://legendcup.com/faqmr1calendar.php · unlocks https://legendcup.com/faqmr2unlock.php · https://legendcup.com/faqmr1unlock.php
- Later games: Ultra Kaiju AI processing https://legendcup.com/faq-ukmr-ai-processing.php · technique tiers https://www.legendcup.com/faq-ukmrtechs.php

**Official manuals and pages:**
- Monster Rancher 1 & 2 DX manuals (Koei Tecmo America): https://www.koeitecmoamerica.com/manual/mrdx/mr2/en/2200.html (and the 2300/2400/3300 pages) · https://www.koeitecmoamerica.com/manual/mrdx/mr1/en/2100.html
- Official DX page: https://www.koeitecmoamerica.com/mrdx · App Store bundle: https://apps.apple.com/app-bundle/id1597251985
- Japanese port change list (2020): https://www.gamecity.ne.jp/mf2/renew.html

**Encyclopedias and reviews:**
- Wikipedia series pages: https://en.wikipedia.org/wiki/Monster_Rancher (plus each game's page)
- Reviews of DX: Siliconera https://www.siliconera.com/review-monster-rancher-1-2-dx-is-the-best-way-to-play-two-classics/ · RPGamer https://rpgamer.com/review/monster-rancher-1-2-dx-review/ · TouchArcade https://toucharcade.com/2021/12/13/monster-rancher-1-2-dx-review-iphone-ipad-switch-steam · Nintendo Life https://www.nintendolife.com/reviews/switch-eshop/monster-rancher-1-and-2-dx
- Reviews of the PS2 and DS games: GameSpot MR3 https://gamespot.com/reviews/monster-rancher-3-review/1900-2814059/ · MR4 https://www.gamespot.com/reviews/monster-rancher-4-review/1900-6084921/ · DS http://www.gamespot.com/reviews/monster-rancher-ds-review/1900-6273577/
- Mamon King coverage: https://automaton-media.com/en/news/japanese-youtubers-160k-monster-rancher-inspired-passion-project-mamon-king-gets-switch-2-release-with-help-from-koei-tecmo/

**Fan discussion:**
- Steam discussions: https://steamcommunity.com/app/1716120/discussions/

**Law:**
- US law: 17 U.S.C. §102 https://www.law.cornell.edu/uscode/text/17/102 · Copyright Office FL-108 https://www.copyright.gov/fls/fl108.pdf
- GitHub's DMCA policy: https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy

**Phone and web technology:**
- Vite static deploy: https://vite.dev/guide/static-deploy
- GitHub Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- WebKit storage policy: https://webkit.org/blog/14403/updates-to-storage-policy/
- vite-plugin-pwa: https://vite-pwa-org.netlify.app/
- MDN Web Share: https://developer.mozilla.org/en-US/docs/Web/API/Web_Share_API
- Claude Code best practices: https://code.claude.com/docs/en/best-practices
