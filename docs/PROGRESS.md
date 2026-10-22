# Progress log

One entry per milestone: what was done, what comes next, and known issues. Newest first.

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
