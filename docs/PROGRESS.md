# Progress log

One entry per milestone: what was done, what comes next, and known issues. Newest first.

## M4: Battles (2026-10-22) · v0.6.0

**Live:** real-time 1-D duels. The Monster Lab has **Versus** (any two monsters, You vs CPU or CPU vs CPU) and the **Battle Lab** (hundreds of fights in the background with the numbers). The ranch's Battle button opens a friendly spar with the active monster.

**Done**
- **Engine** (`core/battle/engine.ts`): a 30-tick-per-second fixed-step simulation, a pure function of (monster A, monster B, seed, inputs). Integer fixed-point throughout: positions in centi-units, percentages in tenths, multipliers in thousandths, and an integer square root for the damage ratio, so a seed replays identically on every phone. Ranges and bands, walking (backing away ×0.85), dash (8 guts, ×3, 18 ticks, 60-tick cooldown), push (touching, 15-tick shove, 250 units, 90-tick cooldown), guts (start 50, cap 99, +1 every `gutsRate` ticks, paused during your own animation), distraction (§12.6, "?!"), KO, time-up by HP % and forfeit. A technique resolves on the tick it is fired; the attacker is then busy for its animation.
- **Formulas** (`core/battle/formulas.ts`): §12.5 hit (with advantage and disadvantage), damage, crit, wither, guts multipliers, form. Every reference row and hit example in §12.5 is reproduced exactly by tests.
- **Technique effects** (§10.3): multi-hit (each hit rolls), heal (always lands, Green Thumb +50 %), stun, drain, recoil on a miss, guts steal, knockback, lunge, jackpot. Mastery bonuses (Lv2 +2 hit, Lv3 +2 force).
- **Specials** (§12.7): Last Stand, Valor, Rage, Bulwark, Clutch, Composure, each once per battle, one timed special at a time, rolled every time the condition occurs.
- **All 30 traits** in `core/battle/traits.ts`, including the ten from NEW_MONSTERS §2 (Dragonheart's one-off guts, Unshakable's immunity, Underdog, Blessed's regen, Moonlit, Green Thumb, Eight Arms, Statue Pose, Battering Ram, Chill).
- **CPU AI** (`core/battle/ai.ts`, §12.10): cooldown, use rates by personality (the six personalities), choice weighted by EV^1.5 with the big-move bias, movement to the best band every 15 ticks, push when wanting distance, dash when wanting to close, the rookie guts reserve. One addition on top of the doc: a fighter that cannot outrun its opponent stops trying to kite and fights at the best band it can reach (without it, some kiters never attacked).
- **NPC generator** (`core/npc.ts`, §13): stats by growth-grade weights with ±8 % noise to an exact total, technique sets by grade, 1–2 universal techniques from grade B, loyalty and fame bands. Rivals, habits and cup seeding come with M5.
- **Battle screen** (§12.11): names, HP and guts bars (numbers in the Lens), timer, special badges; the arena with both monsters (B mirrored) moved with transforms only, a range ruler with the gap marker, floating damage, "Crit!", "Miss", "?!" and special names; four technique columns (Close · Near · Mid · Far) with cost and live hit %, the current column glowing, unaffordable cards dimmed; **Assist** (tap a card in another column to walk there and fire; a setting, on by default); ◀ ▶ hold pads, double-tap ▶ to dash, Push when touching; Auto, ×1 / ×2 / ×4, pause with Skip and Forfeit; the result card with Rematch and Done. Haptics on Android after the first tap; screen shake ≤ 4 px and none with Reduce motion.
- **Versus** and **Battle Lab** in the Lab (§19): pickers from the ranch, the Library and the Presets; personalities; 60 / 90 / 180 s. The Lab runs 100 / 500 / 1,000 battles in a Web Worker (sides alternating) with a progress bar, win / draw / KO %, length, attacks, hit rate, damage per hit, most-used techniques, and a CSV download.
- **Tests** (278 total, 45 new): formula reference tables, traits, specials, engine determinism and replay, a 1,000-seed fuzz (no NaN, no negative HP, ends by the timer; about 1 ms per battle), AI attack counts and personalities, stats, NPC bands, and the §26 balance cells.

**§26 battle results (NPC stats, alternating sides, Steady AIs)**

| Target | Doc says | Measured |
|---|---|---|
| Mirror match | 45–55 % | 51.5 / 48 (200 seeds) ✓ |
| +10 % total stats | 62–80 % | 68 % ✓ |
| +30 % total stats | 85–96 % | 92 % ✓ |
| KO rate, even fights (five starter mirrors) | 15–35 % at 1,000 · 3–15 % at 3,000 | 21 % · 9 % ✓ |
| Attacks per monster per match | 4–12 | 6.8 at 1,000 · 9.5 at 3,000 ✓ |
| Breed pairs at equal total (15 pairs × 3 totals) | 30–70 % | 29 of 45 cells inside (64 %) |

The pair sample is reported by the test and must keep at least 55 % of its cells inside the band; the full 30 × 30 matrix at three totals is M9's job, as the build plan says. The misses are the archetypes §27 warned about: fast-regen casters (Coilfang, Zipwisp, Starhowl) beat slow walls (Nimbusheep, Petalphant) by more than 70 %. One AI number was moved: the technique cooldown's top end from 75 to 84 ticks, so the fastest-regen breeds stay under 12 attacks a match.

**Decisions worth knowing**
- Versus and the spar are exhibition only: no fatigue, lifespan, record or mastery changes (tournaments in M5 do all of that).
- The engine mutates one state object (immutable ticks made the Battle Lab crawl); the UI reads snapshots.
- The ranch's Battle button is a spar at the Guild arena: the active monster is pre-picked as side A.

**Next (M5):** tournaments, ranks, rivals and their habits, NPC seeding by cup, Journeys with the Trial, after-battle effects, the Results and Guild screens.

**Known issues**
- Some fast-caster vs wall matchups sit outside 30–70 % at equal totals (M9 balances the full matrix).
- Rival habits are a `none` hook until M5. The left-handed layout and sound arrive with M8.
- The vignette-style attack animation is a squash; lunges, projectiles and KO flops are M8 polish.

## M3: The ranch loop (2026-10-22) · v0.5.0

**Live:** the game can be played. New Game → a monster → weeks of training, resting, feeding, shopping, items and Songsheets → old age and a farewell. Saves survive closing the app.

**Done**
- **The turn controller** (`core/game.ts`): the week's phase and the monster's pending request are part of the save (`weekPhase`, `pendingRequest`), so the app can be closed at any moment and reopened exactly where it was. Begin week → answer request → choose action → praise/scold → finish week; "Repeat last week" remembers the last drill or rest; an action menu says which buttons are on and why (sick: rest only; missing or at the clinic: wait a week). Free actions (items, sheets, edits) never use the turn. Food is now charged in week 1 (§9: the Guild Loan covers a shortfall at a 10% fee).
- **Economy, Market, Guild** (`core/economy.ts`, `core/market.ts`, `core/guild.ts`): buying with reasons (rank gate, grade C gate for Grand sweets, debt, money, quantity), max affordable, shop stock with gates; fixed-seed Market gifts (four starters plus the season's breed; same monster for everyone); Songsheets for sale with rank gates, ownership, ★ fit and learnability for the active monster.
- **Odds, Wren, onboarding** (`core/odds.ts`, `core/report.ts`, `core/onboarding.ts`): Guided words at the `TRANSPARENCY.oddsBands` edges and exact percentages for the Lens, with truancy taken off the top; every weekly line, drill line and event line Wren says (never the same line twice in one report); twelve one-time tips in the order a new player meets them, the first month guided.
- **Schema v3**: the game state gains the week phase, pending request, last action, the active monster's edit history, tips seen, counters and a sandbox flag, with a migration and tests. `AppSettings` gains transparency, text size, animation speed and sound placeholders (never-fail validation).
- **New Game**: names, difficulty cards in plain words, a Guild gift (five portraits) or the Shrine (a locked main breed makes the stone hum and no monster), "Meet {name}" with a name field, **Begin** and **Edit before you start**; replacing an existing ranch asks and offers an export first.
- **The ranch**: calendar strip (year, month, week, season, weather, purse, a ⚙ shortcut), the monster on a seasonal stage (tap → card), Wren's bubble, condition bars by transparency mode, the action bar (Train · Rest · Journey · Battle · Town, Bag, Repeat last week, Wait a week). Overlays: the monthly food prompt (♥ / ✗ / bored, effect preview, loan note), the request card, the Train sheet (stars, stat arrows, liked/disliked/bonus/tonic tags, odds by mode, Quarry Haul locked), the drill result (a prop vignette per drill in `art/props.ts`, banner, stat deltas, chore pay, stroke-to-praise or buttons), the end-of-week summary (aging events, fees, next weather, the **grow-up glow** at Prime for Hearthwing, Pluckrex and Paladove, breakdowns as a dramatic card), and the hand-off to the farewell.
- **Monster Card in play** (shared `MonsterSheet` with the Lab view): **Use item · Learn technique · ✏️ Edit**. The editor's `active` origin saves straight to the ranch (autosaved) and keeps the previous version in the monster's edit history; Back and Save return to the card.
- **Bag** (×1 / ×5 / ×10 / Max, the Pearl's stat picker, tonic and fruit warnings, charms shown as placed, one-per-week refusals), **Songbook** (known with Forget, learnable with ★ fit and Learn, "Make room" at 12, relearning), **Town** (Shop, Guild Library, Monster Lab; the rest "opens with a later update"), **Basil's Shop** (bakery counter first, categories as chips, effect text per item, gates with reasons, multi-buy with a running total, debt notice), **Guild Library** (universal and by-breed tabs, rank gates, Owned marks).
- **Settings**: transparency, animation speed, text size (a `--text-scale` on the root), reduce motion, edited badge, sound placeholders, Gentle ↔ Standard switch (Classic locked), one item per week, save backup (download .json, share .txt), import a save (paste or file, preview, replace), storage status, a Sandbox "Add 10,000G" tool that marks the ranch.
- **Farewell placeholder**: Wren's line (retire or pass), the old portrait, weeks lived, final total, care counters, Start a new ranch, Keep a copy in the Lab.
- **Tests**: 233 (31 new): controller phases, economy, Market, Guild, odds bands, Wren's report, onboarding order, schema v3 migration and round trip, router returns, and the **3-year scripted raise** through the controller (shopping, a batch of sweets, a Songsheet, toys, requests, one edit, a save round trip every year, deterministic for a seed).
- **Headless phone check**: the built app was driven through two sessions in headless Chrome at 390×844 (new game → food → drill → praise → weeks → shop → library → bag → card → songbook → edit → settings → reload; and a short-lived Pluckrex from birth to retirement) with no console errors. Screenshots were reviewed.

**Decisions worth knowing**
- The drill result screen is held in memory until the week ends: if the app dies mid-result, that week restarts from its beginning (deterministic, nothing double-applied). Everything else autosaves immediately (after the week begins, after every free action, at the end of the week, and when the app goes to the background).
- The food prompt and the welcome tip come first in a new game; every other ranch tip waits until the week has begun.
- With no tournaments until M5, chore pay is the only income, so a batch of ten regular sweets (4,000G) is out of reach of the 3,000G start. The Sandbox tool in Settings covers testing; the economy is M5's to balance.
- Journeys and Battles show on the action bar as "coming soon" buttons (a toast), so the layout is the final one.
- Manual save slots have no UI yet: Continue loads the newest autosave; a new ranch replaces it after a confirm with an export offer.

**Next (M4):** battles: the engine, formulas, AI, the battle screen, Versus and the Battle Lab.

**Known issues**
- Rank stays 1 until M5, so only Basic and Hit Songsheets, regular sweets, toys and care items can be bought; gated rows say why.
- The Shrine in New Game skips locked breeds with the "sleeping" line; Sleeping Stones and the Encyclopedia arrive with M6.
- The Lab's "Send to Freezer" and "Make Active" wait for M6; the Farewell is a placeholder until the Memorial exists.
- Odd Jobs, the Planner, ranch upgrades, mail and the install-help card are later milestones.

## M2.5: Ten new monsters (2026-10-22) · v0.4.0

Breeds 21–30 from `docs/NEW_MONSTERS.md`, added before the ranch loop at the owner's request, plus an art polish pass for all 30.

**Done**
- **Docs:** CONTENT §2 (30 breeds), §2.1 (10 traits), §2.2 (10 briefs with the two-form text) and §3 (10 technique tables; 270 + 24 = 294) now hold the ten exactly as written in NEW_MONSTERS. GAME_DESIGN: four Market starters (§14.2), 900 mixes (§14.3), "8 of the 30" (§18), "all 294" (§19), and the **growth forms** and **high-end polish** rules in §22. BUILD_PLAN: this M2.5 section, the ten trait effects on M4's list, 30 breeds in the M9 matrix.
- **Data:** ten breed ids, ten trait ids, ten breeds (Pluckrex always at the Market, the rest at the Shrine, none locked), `art.grown` briefs for Hearthwing, Pluckrex and Paladove, 90 technique rows transcribed by a script from the tables. Tests: 30 / 30 / 294, unique technique names, Pluckrex among the always-stocked starters, spot checks of the new rows. Every one of the 90 new rows sits inside its §10.2 band: the pinned outlier list did not grow.
- **Shrine snapshot regenerated on purpose:** the commonness weights changed (ten new breeds share the pick), so every phrase now gives a different monster than at v0.3.0. Nobody has a saved phrase yet, so nothing is lost.
- **Art, ten looks:** new plan variants (a necked quadruped, hulking and squat bipeds, young and grown dinosaurs, a chick and a stout dove, a tentacled blob, a horizontal swimmer), ten looks and ten accent parts (little wings, crystal shoulders, fan crest, halo, aurora mane, petal ears, scholar's cap, bat wings, spiral horns, ice tusk). **Growth forms:** Hearthwing, Pluckrex and Paladove switch from young to grown at Prime; the Lab preview and the presets follow the life stage; the form is never stored. Wren's "{name} has grown up!" line is in the text file for M3's ranch scene.
- **Polish for all 30:** top-left-lit gradients on every body part (ids carry a palette hash, so many monsters on one page never clash), rim highlights, a soft radial contact shadow, four subtle textures (scales, fur, stone, feathers) assigned per breed, secondary motion (ears, wings, manes, fins, tentacles, spinning gears, glowing crystals and embers), a hop with squash-and-stretch, eyes that glance toward where the player taps, and signature particles for 26 of the 30 breeds (embers, glints, motes, twinkles, petals, bubbles, dust puffs, snowflakes, rain, sparks, steam, leaves, ash, coin glints, feathers). Particles are off for static thumbnails, under reduced motion and in **lite mode**, which turns on automatically on phones with little memory or few cores, or when a one-off frame-rate sample is low (thresholds in `tuning.ts` `UI.perf`).
- **Visual QA:** PNG contact sheets of the ten new breeds, the three growth forms (young, grown, happy), all eight expressions for each new breed, 40 mixes (each new breed with three old subs, and ten old breeds with new subs) and the old 20 after the polish were reviewed. One design was changed on review: Pluckrex's first draft could read as a penguin (upright stance, slate-and-cream palette, small muzzle), so it got a real dinosaur jaw with teeth, back ridges and a bigger crest. Nothing resembles a character from another franchise.
- 30 pure babies + 120 trained presets; 900 mixes render cleanly in tests; 202 tests (8 new), bundle 265 KB (84 KB gzipped).

**Known issues**
- The ten new traits have descriptions and ids only; their battle effects are on M4's list.
- The "grow up" moment (glow, Wren's line) needs the ranch screen (M3).
- Lite mode is decided once per session; there is no manual switch yet beyond Reduce motion.
- Old-age desaturation, the idle animation and the particles only show in browsers, not in the PNG review tool.

## M2: Saves and the Monster Lab (2026-10-22) · v0.3.0

**Live:** the Monster Lab opens from the title screen. This is the first milestone the owner can use: make a monster, see it drawn, edit anything, and move it between phones.

**Done**
- **Saves on the phone** (`save/db.ts`): IndexedDB through idb-keyval in our own `wildsong-ranch` database, every key prefixed `wildsong/`; 3 manual slots; an autosave ring (the latest plus 3 backups, falling back to an older copy if the newest is corrupt); the global Library; Settings; a localStorage mirror of the latest save and of the Library, used when the database is empty or broken; `navigator.storage.persist()` after the first save. Nothing throws: a broken database reads as empty and a failed write returns false, and every read is validated.
- **Schema v2** (`SAVE_VERSION = 2`): saves gain `meta { savedAt, appVersion }` with a migration and a test; monster files (`kind: 'monster'`, with up to 10 edit-history entries), Library files (`kind: 'library'`) and Settings; `validateAny()` sorts any pasted object by its `kind` (a bare monster counts too); a file from a newer version gets a clear message. Friendly error strings live in `text/ui.ts`.
- **Share codes** `WS1-…` (deflate-raw + base64url through the browser's built-in `CompressionStream`, no library). Decoding tolerates lower-case, codes inside sentences and links, and line-wrapped email; a pinned code written at v0.3.0 guards compatibility forever. Import from JSON, codes, `.txt`, and `#import=` links; export as code, link, QR code (SVG), `.json` download and Web Share `.txt`.
- **Procedural monster art v1** (`art/monster/`): a pure SVG string renderer (runs in tests, later in workers); 9 body plans with sockets; 20 breed looks from CONTENT §2.2; 20 accent parts; the §14.3 palette rule (sub palette on the main body, the main's eyes stay); 8 expressions plus the sparkle and the mischievous grin from the §6.6 cues; size by life stage; a fade from stage 8; idle animation (breathe, bob, float, blink, wag, twinkle, jitter, chew) on transform and opacity only, off under reduced motion or `data-animate="false"`. Every breed, 15 mixes, every expression and every size were reviewed as PNG contact sheets before shipping.
- **Core**: `core/lab.ts` (scaleToTotal by grade factor with an exact total, breed base, max all, seeded randomize, the blank template, duplicate, breed change with Keep all, Allow any technique, the edited rule, edit history push and restore), `core/shrine.ts` (§14.1 steps 1–8 in order; a five-phrase snapshot is the "same phrase, same monster" contract), `core/presets.ts` (20 pure babies and 80 trained presets at E / C / A / S, generated, never stored).
- **Monster Lab UI**: Library (Library / Presets, breed filter, sort, cards with badges, an action sheet with View · Edit · Duplicate · Export · Delete), Create (breed tiles with portraits and the "Not discovered yet. Use anyway?" prompt, from a song with a live Shrine preview, or blank), Editor (every §19 section, a live portrait pinned at the top, the breed-change removal list with Keep all, Save · Save as copy · Cancel · Revert, Edit history with Restore), the Monster Card view, Import (paste, file, link, preview before accepting), Export, and a minimal Settings screen (edited badge, reduce motion, storage status).
- 194 tests (60 new), `npm run verify` green, bundle 216 KB (71 KB gzipped).

**Decisions worth knowing**
- The shared `.txt` holds one friendly line plus the code; the `.json` download holds the monster with its edit history; codes carry the monster alone so QR codes stay scannable.
- "Not discovered yet" means one of the 8 locked breeds, until the Journal exists (M7).
- Preset power: E 600 · C 1,200 · A 2,000 · S 2,800 total stat points at the first week of Prime (`tuning.ts` `PRESETS`). An S preset knows its whole 9-technique kit.
- Library and picker portraits are static; previews and the Monster Card animate, so a hundred cards stay smooth.
- Restore loads an old version into the editor's draft; Save keeps it and pushes the version it replaced into history, so a restore can be undone as well.
- Breed change in the editor only removes techniques on save, and only if the breeds actually changed and Keep all is off. Techniques added with Allow any are never stripped by themselves.

**Next (M3):** the ranch loop: New Game, the ranch screen, drills and results, rest, requests, food, the Shop, items and Songsheets in play, the Monster Card with ✏️ Edit, Settings, aging and warnings, onboarding.

**Known issues**
- The Lab's Versus and Battle Lab tabs wait for M4; the Freezer and Memorial sources, Send to Freezer and Make Active wait for M3 and M6.
- A whole save file cannot be loaded until the ranch exists (M3); Import offers its monster for the Library instead.
- A share code is about 900 characters for a baby monster: fine for a QR code, long to type by hand.
- Old-age desaturation and the idle animation only show in browsers, not in the PNG review tool.
- UI screens have no automated tests (they would need a DOM library); everything below them does.

## M1: Core simulation (2026-10-22) · v0.2.0

Nothing new on the phone; this milestone is the rules of raising, as pure TypeScript with tests.

**Done**
- `core/rng.ts` (mulberry32 with saveable state, seed scrambling so nearby seeds are unrelated), `core/hash.ts` (phrase normalization and cyrb53, with pinned values), `core/mathx.ts` (half-to-even integer rounding, which the design doc's reference tables use).
- Content data transcribed from `docs/CONTENT.md`: 20 breeds, 180 + 24 techniques (learn requirements and effects parsed from the CONTENT text), 11 drills, 7 foods, every item, 5 mentor sites, 20 traits. `src/data/data.test.ts` checks counts, ids, kits and value bands.
- `core/monster.ts` (model, derived values, §14.3 mixing, creation, clamping), `core/calendar.ts`, `core/training.ts` (drills, outcomes, gains, praise/scold, rest, play, requests), `core/aging.ts` (strain, illness, breakdowns, warnings, labels, expressions), `core/food.ts`, `core/items.ts` (unlimited use), `core/songbook.ts`, `core/journey.ts` (weekly check, gains, technique roll), `core/state.ts` + `core/week.ts` (the week in its strict order, items as free actions).
- `save/schema.ts` + `save/migrate.ts`: valibot schema v1, `SAVE_VERSION = 1`, clamping and friendly errors, never throws.
- `core/sim/lifeSim.ts` and `npm run sim:life -- <breed> <great|good|ok|neglect> [seed] [--weekly]`.
- 133 tests. Every reference table in GAME_DESIGN §5–§7 and §11 is reproduced exactly (grade factors, stage boundaries, the six outcome rows, the three gain tables, rest/play, strain ladder, the Journey table).

**§26 balance results (40 seeds, Puddlepup, no sweets/sheets/edits)**

| Target | Doc says | Measured (rules as written) |
|---|---|---|
| Stat total with Good care, years 1 / 3 / 5 | ≈ 700 / 1,450 / 2,350 | 669 / 1,409 / 2,419 ✓ |
| Late A/B monster, years 5 / 6 | ≈ 2,550 / 2,950 | 2,878 / 3,557 (a bit hot; our test monster is all A/B) |
| Outcome rates, Good care | G 17–23 · S 55–65 · C 7–12 · F 8–14 % | 20 / 60 / 10 / 10 ✓ |
| Life lived: Great / Good / OK / Neglect | 82–92 / 76–88 / 62–78 / 25–45 % | with the original ladder rule: **101 / 88 / 53 / 31 %** · with the smooth rule now in use: **86 / 81 / 66 / 38 %** ✓ |

**Design change (owner's decision, 2026-10-22):** the original §6.6 strain ladder (no loss below 80 strain, then 1–3 weeks) could not produce the doc's life-lived gradient: a player who praises after drills and rests at the stated thresholds never crossed 80 and lost nothing, while OK care sat just over it and lost half its life. The owner chose the smoother **strain debt** rule: every week adds `max(0, strain − 10)` to a running debt (compounding above 150 strain), and each 160 points of debt cost one week of life (Gentle builds debt half as fast with a cap of 1; Classic a quarter faster with a cap of 4). GAME_DESIGN §6.6 and §7 are updated; the ladder stays selectable in `tuning.ts` for comparison. All four life bands and every other §26 target now pass as real tests.

**Also for the owner:** 12 technique rows in CONTENT sit just outside the §10.2 value bands (listed in `src/data/data.test.ts`). They are kept as written; the test pins them so the list cannot grow unnoticed.

**Next (M2):** saves on the phone (IndexedDB slots, autosave, mirror), share codes and files, procedural monster art v1, and the Monster Lab editor.

**Known issues**
- The Journey Trial battle, mentor bond and sale months wait for M5; the Signature scene for M5; Nibblegrub's cocoon for M7.
- Relearning a forgotten technique restarts its mastery (uses reset to 0).

## M0: Project setup and live on the phone (2026-10-22) · v0.1.0

**Live:** https://jjones1319-create.github.io/wildsong-ranch/ (deployed by GitHub Actions on every push to `main`).

**Done**
- Vite 8 + TypeScript 6 + Preact 10 project (from the `preact-ts` template), with `@preact/signals`, `idb-keyval`, `valibot`, `zzfx`, `qrcode`, Vitest 5, `vite-plugin-pwa` 2 and the PWA assets generator.
- Scripts: `dev`, `build`, `preview`, `test`, `typecheck` (`tsc -b`), `verify`, `icons`.
- Installable PWA: manifest (`id`/`scope`/`start_url` = `/wildsong-ranch/`, standalone, portrait), `registerType: 'prompt'`, Workbox precache of js/css/html/svg/png/webp/woff2/json, original logo (`public/logo.svg`, a singing stone with a sprout) and generated icons.
- Phone-first base CSS: dark cozy palette, `100dvh`, safe-area padding, `touch-action: manipulation`, no overscroll, no text selection or long-press callouts, 48 px buttons, 520 px max width, reduced-motion support.
- Hash router (`src/ui/router.ts`, tested) and screens: Title (menu, Credits link, version), Placeholder (for New Game / Continue / Monster Lab / Settings), Credits (disclaimer).
- Update toast: "Update ready: Restart / Later" shown only on the title screen; "Ready to play offline" once; the app re-checks for updates when it returns to the foreground and hourly.
- Folder structure from CLAUDE.md with one-line placeholder modules; `src/data/tuning.ts` started.
- Git repo on `main`, MIT `LICENSE`, `CREDITS.md` with the disclaimer, `.gitattributes` (LF), GitHub Actions deploy workflow, GitHub Pages enabled (source: GitHub Actions).

**Known issues**
- The four menu buttons open "coming in M2/M3" placeholder screens by design.
- Commits for this repo use the GitHub no-reply address (repo-local git config) so the owner's work email is not published.
