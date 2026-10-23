# Wildsong Ranch: Build Plan

**How this plan works:**
- Work **one milestone at a time** and stop at the end of each so the owner can test on their phone.
- At the start of a milestone, use plan mode to break it into tasks. Add a "Detailed plan" sub-list under it here.
- Tick the checkboxes as you go, and log what was done in `docs/PROGRESS.md`.

**Definition of done (every milestone):**
1. `npm run verify` passes (typecheck + unit tests + build).
2. New rules have unit tests, and new formulas reproduce the reference tables in GAME_DESIGN.
3. The work is committed (`M<n>: <summary>`) and pushed to `main`, and the GitHub Pages deploy succeeded.
4. The version number is bumped (patch for fixes, minor for each milestone).
5. The owner gets a short **"Try this on your phone"** checklist (5–10 steps, plain words).

---

## M0: Project setup and live on the phone

**Goal:** an empty-but-real app the owner can open and install on their phone.

- [x] Check the computer: Node.js LTS (24 or newer), npm ≥ 11, Git, GitHub CLI (`gh`, optional but preferred).
  - If anything is missing, give the owner step-by-step install instructions (see `PHONE_AND_GITHUB_SETUP.md`) and wait.
- [x] Scaffold in this folder: `npm create vite@latest . -- --template preact-ts`.
  - Keep the template's Preact 10 and TypeScript versions; don't bump majors without asking.
  - Merge with the existing docs rather than overwriting them.
- [x] Add dev dependencies: Vitest, `vite-plugin-pwa`, `@vite-pwa/assets-generator`.
- [x] Add dependencies: `@preact/signals`, `idb-keyval`, `valibot`, `zzfx`, `qrcode`.
- [x] Add scripts: `dev`, `build`, `preview`, `test` (`vitest run`), `typecheck` (`tsc --noEmit`), `verify` (typecheck && test && build).
- [x] Create the folder structure from `CLAUDE.md` with placeholder modules and `src/data/tuning.ts`.
- [x] Set up the PWA:
  - Manifest: `id` and `scope` = `/<repo>/`, `display: standalone`, `orientation: portrait`.
  - `registerType: 'prompt'` with an "Update ready → Restart" toast.
  - Workbox `globPatterns` covering js, css, html, svg, png, webp, woff2 and json.
  - Generate icons from a simple original SVG logo (a singing stone with a little sprout).
- [x] Mobile base CSS:
  - Viewport `viewport-fit=cover`, `100dvh`, safe-area padding.
  - `touch-action: manipulation`, `overscroll-behavior: none`, no text selection or long-press callouts on game UI.
  - Dark theme base colors.
- [x] Title screen with the game name, "New Game / Continue / Monster Lab / Settings" (placeholders), the app version, and the non-affiliation disclaimer in Credits.
- [x] Hash-based screen state. No path routing; GitHub Pages can't rewrite URLs.
- [x] Git:
  - `git init`, a `.gitignore` (node_modules, dist), `.gitattributes` (`* text=auto eol=lf`).
  - `LICENSE` (MIT unless the owner chooses otherwise), `CREDITS.md`, and a short `README.md`.
- [x] Create a **public** GitHub repo `wildsong-ranch`.
  - Ask first: with `gh repo create`, or guide the owner through github.com.
  - Push `main`, and commit `package-lock.json` (npm ≥ 11).
- [x] Add `.github/workflows/deploy.yml`:
  - Checkout, setup-node (Node 24 or `lts/*`), `npm ci`, `npm test`, `npm run build`, configure-pages, upload-pages-artifact (`./dist`), deploy-pages.
  - Use the current major versions shown in Vite's static-deploy guide.
- [x] Turn Pages on (Settings → Pages → Source: GitHub Actions), or `gh api -X POST repos/OWNER/wildsong-ranch/pages -f build_type=workflow`.
- [x] Confirm the live URL `https://<user>.github.io/wildsong-ranch/` loads, then send the owner the link with install steps.

**Detailed plan (written 2026-10-22):**
- [x] 1. Scaffold from the `preact-ts` template (copied from a scratch scaffold, because `npm create vite .` would wipe this folder) and drop the template's demo assets. `package.json`: name `wildsong-ranch`, version `0.1.0`.
- [x] 2. Dependencies: `preact ^10.29`, `@preact/signals ^2.11`, `idb-keyval ^6.3`, `valibot ^1.5`, `zzfx ^1.4`, `qrcode ^1.5`. Dev: `typescript ~6.0` (the template's), `vite ^8`, `@preact/preset-vite`, `vitest ^5`, `vite-plugin-pwa ^2`, `@vite-pwa/assets-generator ^2`, `@types/node`, `@types/qrcode`.
- [x] 3. Scripts: `dev`, `build`, `preview`, `test` (vitest run), `typecheck` (`tsc -b`, because the template uses project references and `tsc --noEmit` alone would check nothing), `verify`, `icons`.
- [x] 4. `vite.config.ts`: `base '/wildsong-ranch/'`, `__APP_VERSION__` from package.json, Vitest block, VitePWA (`registerType: 'prompt'`, manifest id/scope/start_url `/wildsong-ranch/`, standalone, portrait, Workbox globs for js/css/html/svg/png/webp/woff2/json).
- [x] 5. Original logo `public/logo.svg` (a singing stone with a sprout) and generated icons (64/192/512, maskable 512, Apple 180, favicon.ico) committed to `public/`.
- [x] 6. `index.html`: `viewport-fit=cover`, theme-color, Apple web-app metas, icon links built from `%BASE_URL%`.
- [x] 7. `src/ui/styles/base.css`: dark cozy palette as CSS variables, `100dvh`, safe-area padding, `touch-action: manipulation`, `overscroll-behavior: none`, no text selection or long-press callouts, 48 px buttons, 520 px max width, reduced-motion support.
- [x] 8. `src/ui/router.ts`: hash ↔ screen (`title`, `credits`, `newGame`, `continue`, `lab`, `settings`), unknown hash → title; a `screen` signal mirrored to `location.hash`. Unit tests.
- [x] 9. Screens: Title (logo, name, tagline, four menu buttons, Credits link, version), Placeholder (says which milestone brings it, Back), Credits (disclaimer, MIT, tools). All strings in `src/data/text/ui.ts`.
- [x] 10. `UpdateToast`: "Update ready → Restart / Later" on the title screen only; "Ready to play offline" once; re-check for updates when the app returns to the foreground.
- [x] 11. Folder structure from CLAUDE.md with one-line placeholder modules and `src/data/tuning.ts`.
- [x] 12. Git: `git init -b main`, `.gitignore`, `.gitattributes` (`* text=auto eol=lf`), `LICENSE` (MIT), `CREDITS.md`, README live link, `docs/PROGRESS.md`. Commits use the GitHub no-reply email for this repo only (the global git email is a work address).
- [x] 13. `.github/workflows/deploy.yml`: checkout v7 → setup-node v7 (Node 24) → `npm ci` → typecheck → test → build → configure-pages v6 → upload-pages-artifact v5 → deploy-pages v5.
- [x] 14. `npm run verify` green, then commit `M0: …`, `gh repo create wildsong-ranch --public` (no push yet), enable Pages with `build_type=workflow`, push `main`, watch the run, `curl` the live page.
- [x] 15. Send the owner the link and Home Screen steps, then stop.

**Phone check:** open the link, add it to the Home Screen, open it from the icon (full screen, no browser bar), and see the version number.

## M1: Core simulation (pure TypeScript, no UI)

**Goal:** the rules of raising, fully tested.

- [x] `core/rng.ts`: mulberry32 with saveable state; `core/hash.ts`: cyrb53-style 53-bit hash and phrase normalization.
- [x] Data:
  - `data/breeds.ts`, `data/techniques.ts` (180 breed + 24 universal), `data/drills.ts`, `data/foods.ts`, `data/items.ts`, typed and generated from `CONTENT.md`.
  - A test that the data matches CONTENT: counts, ids, and every breed has techniques in at least 3 ranges.
- [x] `core/monster.ts`: the model and derived values; creation from breed + sub + offsets; mixing rules (GAME_DESIGN §14.3).
- [x] `core/calendar.ts`: weeks, months, seasons, weather, the week order of operations (GAME_DESIGN §3).
- [x] `core/training.ts`: truancy, outcome weights, gains, praise/scold, rest, play, requests.
- [x] `core/aging.ts`: life stages, strain, lifespan, illness, breakdowns, warnings.
- [x] `core/food.ts` and `core/items.ts`: monthly food, boredom, **unlimited item use** (with the optional one-per-week rule), Stat Sweets (and per-stat "from sweets" tracking), Potential Pearl, Tempo Bell, charms, tonics (stacking rules), fruits (once each).
- [x] `core/songbook.ts`: Songsheets, the Songbook (owned sheets are permanent), compatibility (universal / breed kit / sub quirk / Signature = pure only), learn, forget, relearn, and the 12-technique cap.
- [x] `core/save/schema.ts`: valibot schema v1 and a `migrate()` skeleton.
- [x] **Tests:**
  - Every reference table in GAME_DESIGN §5–§7 and §11.
  - Determinism (same seed → same life).
  - **Sim tests** for the raising targets in GAME_DESIGN §26.
- [x] A dev-only script `npm run sim:life` that prints a full simulated life for a breed and care policy.

**Detailed plan (written 2026-10-22; building starts after the owner confirms M0 on their phone):** version `0.2.0`. Everything in `src/core/` is pure (injected RNG, integer math, no Date/DOM); every number lives in `src/data/tuning.ts`; relative imports keep their `.ts` extension so Node 24 can run core code directly.
- [x] 1. `core/rng.ts`: mulberry32 with get/set state, `nextU32`, `nextInt(lo, hi)` inclusive, `nextFloat`, `pick`, `weightedPick`, `shuffle`, `chance(pct)`. Tests: fixed-seed sequence, determinism, save/restore resumes identically, inclusive ranges.
- [x] 2. `core/hash.ts`: `normalizePhrase` (NFKC → lowercase → trim → collapse spaces → keep letters, digits and spaces of any script) and `cyrb53(str, seed)`. Tests: `"Hello,  World!"` → `"hello world"`, a snapshot of 10 hash values (the contract that keeps every phrase's monster stable), seeds 1 and 2 differ.
- [x] 3. Data from CONTENT: `breeds.ts` (20), `traits.ts`, `techniques.ts` (180 breed + 24 universal, ids like `puddlepup.splash-nip`, structured `learn` requirements, `subQuirk` flag, parsed effects), `drills.ts` (11), `foods.ts` (7), `items.ts` (every row of CONTENT §6 with category, price, effect and gate). Data tests: counts and unique ids; each breed has 2 Basics, one each of the other families, exactly one sub-quirk (a Basic) and techniques in ≥ 3 ranges; band sanity for Basic/Hit/Heavy/Wither/Sharp rows (rows outside a band are reported to the owner, not changed).
- [x] 4. `core/monster.ts`: types, `gradeFactor` (§5.2), derived values (loyalty, style + band, life stage, stage factor, strain, stars, total), `createMonster(main, sub, offsets, rng)` with the §14.3 mixing rules, `clampMonster`. Tests: grade factor, stage boundaries for all 4 growth types, the `sf` table, mixing examples including pure and tie-breaks.
- [x] 5. `core/calendar.ts` (week index ↔ year/month/week, season, month start, seeded weather with Storm only in summer and Snow only in winter) and `core/week.ts` (`runWeek` in the strict §3 order, returning a phase log). Tests: the order, and that items never use a turn.
- [x] 6. `core/training.ts`: stars, truancy, outcome weights with trait and Training Yard modifiers, normalization, `resolveDrill`, gains (light/heavy/secondary with Great/Cheat/Fail rules, lowered stat, breed bonus +1, tonic +3), chore pay, praise/scold/skip table (Cheerful halves scold stress), rest and play, request trigger/type/deny. Tests: the six §6.2 reference rows, the three §6.3 gain tables, the §6.5 rest/play table, request chances at 40/60/100.
- [x] 7. `core/aging.ts`: `extraLifespanLoss` thresholds, illness and breakdown rolls with difficulty modifiers, weekly tick, warnings (25 % left, 48 weeks, 10 weeks), prime and past-prime notices, size stage, assistant labels, expression cues. Tests for every threshold and difficulty.
- [x] 8. `core/food.ts` (neutral/liked/disliked, boredom halves positives from the 3rd month, Big Appetite ×1.5, Hungry Grub form ×1.5, Hearty Stew +1 week) and `core/items.ts` (unlimited quantities and use; only the optional one-per-week rule and once-per-monster fruits; Stat Sweets with per-stat "from sweets" tracking and the 999 cap; Potential Pearl max A; Tempo Bell min 6; tonics stack across stats and re-use resets them; toys with 5 uses; charms best-per-category). Tests cover every item class and prove there is no hidden limit (100 sweets in one call).
- [x] 9. `core/songbook.ts`: `canLearn` (universal → anyone; breed sheet → main kit or sub quirk; Signature → pure only; a Chain from a sheet needs no Lv3), `learn` with the 12-cap "which one to forget" result, `forget`, `relearn`, ★ good fit; owned sheets are permanent. Tests for each rule.
- [x] 10. `core/journey.ts` (M1 scope: weekly check, gains, technique roll; Trial, mentor bond and sale months wait for M5). Tests: the §11 reference table by exact enumeration of `rnd(0..29)`, plus the A/B and E/E variants.
- [x] 11. `save/schema.ts` + `save/migrate.ts`: valibot v1 schema, `SAVE_VERSION = 1`, `migrate()` skeleton, `validateSave()` that clamps and never throws. Tests: round trip, garbage input gives a friendly error, out-of-range values are clamped.
- [x] 12. `core/sim/lifeSim.ts`: whole-life simulator with the §26 care policies (Great / Good / OK / Neglect; money ignored) returning weeks lived, lifespan at birth, yearly stat totals, outcome counts and breakdowns.
- [x] 13. Sim tests (§26, ≥ 40 seeds each): life lived per policy, Good-care totals for a Steady mostly-C breed and a Late A/B breed, Good-care outcome rates. Misses are fixed in `tuning.ts` only; a formula that looks wrong is reported and discussed first.
- [x] 14. `scripts/sim-life.ts` + `npm run sim:life -- <breed> <policy>` (runs on Node 24 directly, no new dependency) printing a readable life.
- [x] 15. `npm run verify`, update `docs/PROGRESS.md`, commit `M1: core simulation`, push, confirm the deploy, give the owner a plain-language summary of the sim results.

**Phone check:** nothing new on screen. The owner gets a short plain-language summary of the sim test results instead.

## M2: Saves and the Monster Lab (the editor)

**Goal:** create, load, edit, import and export monsters on the phone. This is also our main debug tool.

- [x] `save/`:
  - IndexedDB (idb-keyval, `wildsong/` key prefix): 3 slots, rotating autosave, localStorage mirror, global Library.
  - `persist()` request; schema validation on every load.
- [x] Share codes (`WS1-` + deflate-raw + base64url), file export (`.json` download; Web Share `.txt`), file import (`.json` and `.txt`), `#import=` links, QR codes.
- [x] **Procedural monster art v1** (`art/monster/`):
  - All 9 body plans, the 20 breed briefs, palettes, sub accents, size stages and expressions.
  - Idle animation; respects reduced motion.
- [x] **Monster Lab** UI: Library, Create, Editor (all sections in GAME_DESIGN §19, including Allow any technique, breed-change handling, and Edit history with Restore), Import, Export, and the optional edited badge.
- [x] Presets: pure babies for every breed, plus trained presets at E / C / A / S power.
- [x] Tests: share-code round trip, schema validation (bad input never crashes), clamping, migration test scaffold.

**Detailed plan (written 2026-10-22, after the owner confirmed M1):** version `0.3.0`. No new dependencies: share codes use the browser's built-in `CompressionStream`, art is pure SVG strings, and the UI is checked on the phone while everything below it has unit tests. Later-milestone parts of GAME_DESIGN §19 stay out: Versus and Battle Lab (M4), Freezer / Memorial / Make Active (M3, M6), variant overrides and secret phrases (M6), Sandbox tools (M3+).
- [x] 1. `tuning.ts`: `LAB` (edit-history limit 10, blank template, randomize spread), `PRESETS` (E/C/A/S totals 600 / 1,200 / 2,000 / 2,800 and technique counts), `SAVES` (3 slots, autosave with 3 backups).
- [x] 2. `save/schema.ts` + `save/migrate.ts`: `SAVE_VERSION = 2` (adds a `meta` block: saved time and app version) with a migration and a test; `MonsterFile` (`kind: 'monster'`), `Library` (`kind: 'library'`, entries with a 10-deep edit history), `Settings`, and `validateAny()` that sorts out any pasted object by its `kind`. Error strings live in `text/ui.ts`.
- [x] 3. `save/shareCode.ts`: `WS1-` + base64url(deflate-raw(JSON)); decoding tolerates whitespace, case and missing padding and never throws. Tests: round trip, a pinned code that must always decode, garbage.
- [x] 4. `save/exportImport.ts`: JSON text, code text, `parseImportText` (JSON, a code anywhere in the text, or an `#import=` link), import URLs, QR SVG via `qrcode` (null when too long). Tests for all forms.
- [x] 5. `save/db.ts`: a tiny `KeyValueStore` (idb-keyval with `wildsong/` keys, plus an in-memory store for tests); 3 slots; autosave ring (latest + 3 backups); Library; Settings; localStorage mirror with fallback. Every read validates and never throws; timestamps are passed in. Tests on the memory store.
- [x] 6. `core/lab.ts`: `scaleToTotal` (by grade factor, exact total, 1–999), breed base / max all / seeded randomize, blank template, duplicate, breed change (removes techniques outside kit ∪ sub quirk ∪ universal unless Keep all), allowed technique lists (with Allow any), the edited rule (anything but the name), edit history push / restore. Tests for each.
- [x] 7. `core/shrine.ts`: §14.1 steps 1–8 in order (secret phrases, teasers and Sleeping Stones wait for M6). A 5-phrase snapshot test is the "same phrase, same monster forever" contract.
- [x] 8. `core/presets.ts`: 20 pure babies and 80 trained presets (E/C/A/S at the start of Prime), deterministic. Tests: counts, totals, determinism.
- [x] 9. Art `art/monster/`: `render.ts` (pure SVG string, 256×256, life-stage size, stage-8 fade, animate flag), `bodyPlans.ts` (9 plans with sockets), `parts.ts` (20 breed feature sets + 20 accent parts), `palettes.ts` (§14.3 palette rule), `expressions.ts` (cues + preview override), `monster.css` (idle breathe / bob / blink / wag / hover on transform and opacity only; off under reduced motion). Tests: all 400 main/sub pairs render cleanly. Visual check: every breed rasterised to PNG with the already-installed `sharp`.
- [x] 10. Router: `#lab/create`, `#lab/view`, `#lab/edit`, `#lab/import`, `#lab/export`, Back returns to `#lab`; `#import=CODE` links open Import with the code and clear the hash. Tests.
- [x] 11. App store: loads Settings and the Library at start (IndexedDB, then the mirror), saves on every change, asks for storage persistence after the first save, toasts.
- [x] 12. Lab screens: Library (Library / Presets chips, breed filter, sort, cards with portraits and badges, action sheet: View · Edit · Duplicate · Export · Delete), Create (from a breed with portraits and the "Not discovered yet" prompt, from a phrase with a live preview, or blank), Editor (every §19 section, live portrait, Allow any technique, breed-change list with Keep all, Save · Save as copy · Cancel · Revert, Edit history with Restore), View, Import (paste, file, link, preview card), Export (code + Copy, QR, Download .json, Share .txt, Copy link).
- [x] 13. Minimal Settings: show the 🔧 edited badge (off by default), reduce motion, storage persistence status.
- [x] 14. CSS building blocks (top bar, chips, segmented tabs, bottom action bar, lists, bottom sheet, inputs, steppers, badges, toast), all tap targets ≥ 44 px; every string in `text/ui.ts`.
- [x] 15. `npm run verify`, `docs/PROGRESS.md`, commit `M2: saves, share codes, monster art and the Monster Lab`, push, confirm the deploy, phone checklist, stop.

**Phone check:**
1. Make a monster from scratch and edit its stats.
2. Export it as a code, delete it, then paste the code back.
3. Download a file and re-import it.
4. Look at all 20 breeds in the presets.

## M2.5: Ten new monsters (batch 2)

**Goal:** breeds 21–30 from `docs/NEW_MONSTERS.md`, with two-form growth for three of them and an art polish pass for all 30, before the ranch loop. Version `0.4.0`.

- [x] 1. Docs: CONTENT §2, §2.1, §2.2 and §3 gain the ten breeds (30 breeds, 270 + 24 = 294 techniques); GAME_DESIGN §14.2 (four starters), §14.3 (900 mixes), §18, §19 and the §22 growth-forms and polish rules; M4 gets the ten trait effects.
- [x] 2. Data: breed, trait and technique ids and rows; `art.grown` briefs; Pluckrex always at the Market. Tests updated for 30 / 294; the §10.2 pinned list unchanged; technique names unique; the Shrine snapshot regenerated on purpose.
- [x] 3. Art: new plan knobs (neck, hulk, squat, dino, chick, stout, tentacles, horizontal), ten looks, three grown forms, ten accent parts.
- [x] 4. Polish for all 30: gradients and rim light, contact shadow, textures, secondary motion, squash-and-stretch hop, eyes that follow taps, signature particles, automatic lite mode.
- [x] 5. PNG contact sheets of every new monster (young and grown, every expression, mixes) and of the old 20 after the polish, reviewed and fixed; nothing resembles another franchise.
- [x] 6. `npm run verify`, PROGRESS.md, commit `M2.5: ten new monsters`, push, confirm the deploy, phone checklist, stop.

**Phone check:**
1. Monster Lab → Presets: the ten new monsters are there.
2. Edit a Hearthwing, Pluckrex or Paladove and slide its age past Prime. It grows into its grown form.
3. Make a few mixes, e.g. Pluckrex with a Starhowl sub-breed, or Grumblestone with a Frostlance sub-breed.
4. Check that animations and particles look smooth, and that Settings → Reduce motion turns them off.

## M3: The ranch loop

**Goal:** raise one monster from birth to old age.

- [x] New Game flow: names, difficulty, first monster (Market gift or a basic Shrine with phrase generation).
- [x] Ranch screen:
  - Monster on stage, calendar strip, Wren's report.
  - Action bar, item button (opens the Bag), and "Repeat last week".
- [x] Train sheet: light and heavy drills, stars, odds by transparency mode.
- [x] Drill result: vignette, banner, stat changes, praise/scold (swipe to pet, wag button).
- [x] Rest, requests, monthly food prompt, Shop (multi-buy, Stat Sweets counter), charms.
- [x] **Items and Songsheets in play:**
  - Bag screen (Use ×1 / ×5 / ×10 / Max), Guild Library (Songsheets), Songbook screen (★ good fit, learn, forget).
  - Monster Card buttons: **Use item · Learn technique · ✏️ Edit**.
  - **Edit before you start** after creating a monster.
- [x] Monster Card: stats, grades, life bar, condition, techniques, personality.
- [x] Settings: sound placeholders, text size, reduced motion, transparency mode, speed, export/import, persistence status.
- [x] Aging: warnings, illness, breakdowns, death or retirement placeholder screen. The full farewell comes in M6.
- [x] Onboarding: Wren guides the first month.
- [x] Tests: UI-free integration test "a scripted player raises a monster for 3 in-game years without errors".

**Detailed plan (written 2026-10-22, after the owner confirmed M2.5):** version `0.5.0`. No new dependencies. The pure week loop from M1 (`core/week.ts`) is driven by a new turn controller (`core/game.ts`); the UI only reads signals and calls it. Later-milestone buttons (Journey, Battle, Market, Shrine, Freezer, Mailbox, Odd Jobs) are shown as "coming soon" where the screen expects them.
- [x] 1. `tuning.ts` (transparency odds bands, Market seeds, shop quantities, onboarding, vignette and speed timings, text sizes), `text/ui.ts` + `text/wren.ts` + `text/labels.ts` (every new string), `core/state.ts` (week phase, pending request, last action, the active monster's edit history, tips seen, counters).
- [x] 2. Schema v3 (`SAVE_VERSION = 3`): the new GameState fields with a migration and a test; `AppSettings` gains transparency, text size, speed and sound placeholders (never-fail validation).
- [x] 3. `core/game.ts`: begin week (phase bookkeeping, request stored in the save), answer request, choose action (stores "last week" for Repeat), react, finish week (then begins the next), wait a week while away, the action menu with reasons. `core/week.ts` charges the monthly food. Tests.
- [x] 4. `core/economy.ts` (buy with reasons, max affordable, shop stock with gates, the §9 loan fee), `core/market.ts` (fixed-seed gifts, seasonal pick), `core/guild.ts` (sheets for sale, buy a sheet), `core/odds.ts` (exact and Guided words), `core/report.ts` (Wren's weekly and event lines), `core/onboarding.ts` (the first-month tips). Tests for each.
- [x] 5. Integration test: a scripted player raises a monster for 3 in-game years through the controller (shopping, 10 sweets at once, a Songsheet, toys, requests, one edit), with a save round trip every year.
- [x] 6. `ui/store/gameStore.ts`: boot (latest autosave), new game, commit + autosave (end of week, every free action, on hide), the week flow signals, item use, shop, sheets, learn/forget, replace monster (from the editor), tips, export/import, difficulty switch. Router screens and `app.tsx` wiring; Title's Continue.
- [x] 7. New Game: names, difficulty, first monster (Market gift or Shrine with the locked-breed teaser), result card with Begin and **Edit before you start**; replace-confirm with an export offer.
- [x] 8. Ranch: calendar strip, monster stage (tap → card, swipe → pet), Wren's report and tip card, condition bars by transparency, action bar (Train · Rest · Journey · Battle · Town), Bag button, Repeat last week, locked weeks. Overlays: monthly food prompt, request card, Train sheet (odds by mode), drill result (prop vignette, banner, deltas, praise/scold/skip), week summary (aging events, breakdown card, grow-up glow).
- [x] 9. Monster Card in play (shared `MonsterSheet` with the Lab view; transparency-aware) with **Use item · Learn technique · ✏️ Edit**; the Lab editor's `active` origin saves straight to the ranch with edit history.
- [x] 10. Bag (×1 / ×5 / ×10 / Max, pearl stat picker, tonic and fruit confirmations, charms placed), Songbook (★ good fit, learn, forget, relearn, the forget-one prompt at 12).
- [x] 11. Town: Shop with Basil (food, care, the Stat Sweets bakery counter, charms, toys, tonics, potential; multi-buy; gates with reasons; debt notice), Guild Library with Ines (universal and breed sheets, rank gates, ★ fit, owned marks), Monster Lab link, coming-soon rows.
- [x] 12. Settings: sound placeholders, text size, reduce motion, transparency, speed, Gentle ↔ Standard, one item per week, edited badge, export/import a whole save, storage status.
- [x] 13. Farewell placeholder (Wren, the old portrait, age and records, start a new ranch, keep a Lab copy); the full scene comes in M6.
- [x] 14. `npm run verify`, PROGRESS.md, commit `M3: the ranch loop`, push, confirm the deploy, phone checklist, stop.

**Phone check:**
1. Raise a monster for a few in-game years; try resting, food, praise and scold.
2. Buy 10 Stat Sweets and feed them all at once.
3. Buy a Songsheet and teach it.
4. Edit your monster from its card, then keep playing.
5. Check that saves survive closing the app.

## M4: Battles

**Goal:** fun, fair, readable fights, played manually or automatically.

- [x] `core/battle/`:
  - Engine (30 Hz fixed step, pure and deterministic), formulas (GAME_DESIGN §12.5), ranges, movement, dash, push, guts.
  - Distraction, specials, traits, effects, end conditions.
- [x] `core/battle/ai.ts`: personalities, the use-rate model, band targeting, push and dash, rookie guts reserve.
- [x] Battle traits for breeds 21–30 (`docs/NEW_MONSTERS.md` §2): Dragonheart (once per battle, +20 guts when HP first drops below 50 %), Unshakable (no push-back or stun; damage taken −10 %), Underdog (+8 hit and +10 % damage against a higher stat total), Blessed (regenerates 1 % max HP every 5 s), Moonlit (crit +6 %), Green Thumb (heal and drain +50 %), Eight Arms (multi-hit techniques get one extra hit), Statue Pose (after 2 s still, −30 % damage taken until it moves), Battering Ram (dashing costs no guts; the first technique after a dash +15 %), Chill (hits slow walking 25 % for 3 s).
- [x] Battle screen (SVG/DOM):
  - Arena with the range ruler, HP and guts bars, technique columns, thumb pads, Assist.
  - Auto toggle, speed ×1/×2/×4, pause and forfeit, haptics, reduced motion.
  - Animations: lunge, projectiles, hit flash, crit, KO, victory.
- [x] **Versus** mode and **Battle Lab** (Web Worker) inside the Monster Lab.
- [x] Tests:
  - Formula reference tables.
  - Determinism and replay (same seed and inputs → same log).
  - 1,000-seed fuzz test (no NaN, no negative HP, no stuck states).
  - **Balance tests** (GAME_DESIGN §26). Tune `tuning.ts`, technique values or traits until they pass.
- [x] Performance: steady 60 fps on a mid-range phone. No layout thrash; animate transforms only.

**Detailed plan (written 2026-10-22, after the owner confirmed M3):** version `0.6.0`. No new dependencies. The engine is integer fixed-point (positions in centi-units, percentages in tenths, multipliers in thousandths, an integer square root for the damage ratio), so the same seed gives the same battle on every phone. Hits resolve on the tick a technique is fired; the attacker is then busy for the technique's animation. Tournaments, rivals, habits and after-battle effects stay in M5; Versus is exhibition only. The ranch's Battle button opens Versus with the active monster as side A (a spar).
- [x] 1. `tuning.ts`: `BATTLE` (§12.1–12.6 numbers), `SPECIALS` (§12.7), `AI` (§12.10 and the personality table), `BATTLE_TRAITS` (CONTENT §2.1 and NEW_MONSTERS §2), `NPC` (§13 bands). `core/battle/types.ts`.
- [x] 2. `core/battle/formulas.ts`: form, walk speed, bands, hit % with advantage and disadvantage, damage, crit, guts multipliers. Tests reproduce every §12.5 reference row and hit example.
- [x] 3. `core/battle/traits.ts` (all 30) and `core/battle/specials.ts` (six specials, once per battle, one active at a time except Last Stand). Tests.
- [x] 4. `core/battle/engine.ts`: create, step, run; inputs by tick; distraction; dash, push, stun, slow; technique effects (multi, heal, stun, drain, recoil, gutsSteal, push, lunge, jackpot); mastery bonuses; KO, time-up and forfeit. `core/battle/ai.ts`: cooldown, use rates, EV^1.5 choice, movement bands, push, dash, personalities, rookie reserve. `core/battle/stats.ts`: Battle Lab numbers and CSV. `core/npc.ts`: §13 stats and technique sets by grade or total. Tests: determinism, 1,000-seed fuzz, outcomes, AI attack counts, NPC bands, stats.
- [x] 5. `core/battle/balance.test.ts`: §26 battle targets (mirror, +10 %, +30 %, breed pairs at equal totals, KO rates, attacks per match) at 200 seeds per cell; tune AI or trait numbers in `tuning.ts` if a target misses.
- [x] 6. `ui/store/battleStore.ts` (setup, the frame loop at ×1/×2/×4 with interpolation, Skip, inputs, Auto, Assist, effects, result) and `ui/screens/battle/BattleScreen.tsx` (§12.11 layout: bars and timer, arena with mirrored monsters and the range ruler, floating numbers, four technique columns with live hit %, thumb pads, dash, Push, Auto, speed, pause and forfeit, the result card). `battle.css`. Haptics on Android; shake ≤ 4 px and none with reduced motion.
- [x] 7. Monster Lab: `LabVersus.tsx` (pick A and B from the ranch, the Library or the Presets; You vs CPU or CPU vs CPU; CPU personality; 60 / 90 / 180 s) and `LabBattleLab.tsx` (A, B, 100 / 500 / 1,000 battles, seed, progress bar, results table, CSV download) with `workers/battleLab.worker.ts`. Router, app wiring, Lab buttons, the ranch's Battle button, an Assist setting, text.
- [x] 8. `npm run verify`, a headless Chrome run of Versus and the Battle Lab, PROGRESS.md, commit `M4: battles`, push, confirm the deploy, phone checklist, stop.

**Phone check:**
1. Fight a CPU monster manually and on Auto.
2. Try every range, dash, push, ×2 speed and Skip.
3. Run a 500-battle Battle Lab between two presets.

## M5: Tournaments, ranks and Journeys

- [x] Calendar of cups (CONTENT §9), entry rules, formats, points and tiebreaks, prizes (purses **and item prizes**, GAME_DESIGN §13), KO withdrawal, after-effects, fame.
- [x] NPC generator (GAME_DESIGN §13), rival breeders and habits (CONTENT §10); Corin Hale scales with your monster.
- [x] Promotion, breeder ranks 1–10, Crowns, Legend Cup, credits at rank 10, Hall of Fame.
- [x] Tournament entry screen, Results screen, Guild screen.
- [x] **Journeys:**
  - Mentor's Ledger with requirements and chance tiers.
  - Weekly checks, gains, the one-technique roll, mastery levels, Chains, mentor bond, Trial battle, sale months.
- [x] Signature-technique scene for pure breeds at Prime.
- [x] Tests: tournament scheduling over 10 years, points and tiebreaks, Journey reference table, NPC stat bands per grade.

**Detailed plan (written 2026-10-23, after the owner confirmed M4):** version `0.7.0`. No new dependencies. A tournament lives in the save (`GameState.tournament`), so a cup resumes at its next match after the app closes; NPC-only matches run through the engine instantly, the player's matches use the battle screen (manual, or Auto with Skip). Rank reading: the first Official win at each grade E–A raises rank 1 → 6, the S Official win invites to the Crowns, the first win of each Crown raises rank 7 → 10. The Masquerade Cup waits for its rumor (M7).
- [x] 1. Data: `data/calendar.ts` (CONTENT §9, 48 weeks, double weeks, year rules), `data/rivals.ts` (CONTENT §10), Mentor's Charms in `data/items.ts`, `TOURNAMENT`, `RIVALS`, `JOURNEY` and `SIGNATURE` numbers in `tuning.ts`, the new text; schema v4 (`tournament`, `trial`, `guild`, `hallOfFame`, `mail`, `saleMonths`, `journeysBySite`, `titles`) with a migration and tests.
- [x] 2. `core/tournament.ts`: this week's events with eligibility reasons; a cup with its participants (NPCs by seed, rivals by grade, Corin scaled to your total), schedules for RR4 / RR6 / Elim4 / Elim8 / 1v1 / Relay, points and tiebreaks, KO withdrawal, simulated NPC matches, and the finish: placing, purse and per-win gold, item prizes, fame, stat growth, after-effects, KO injury (and the Classic risk), promotion, rank, Crown and Legend invitations, Hall of Fame, titles, mastery. Tests for each rule and a 10-year schedule.
- [x] 3. Rival habits in `core/battle/ai.ts` (opens Far, banks guts for a Heavy, walks straight into Close, backs away, spams Wither, waits at 99 guts, pushes whenever touching, dashes in below half HP, steals guts). Tests.
- [x] 4. Journeys in play: the Trial (auto, skippable; 600 × gradeIndex, a 10 % Moonfruit, injury rules on a KO), the mentor bond (a Mentor's Charm every 8 Journeys at a site, −50 on that site's requirements), sale months (two a year, mail in week 1, 1,000G), the Signature at Prime (pure, loyalty ≥ 60) or at Glacier Bastion (DEF + type stat ≥ 700). `core/game.ts`: enter a tournament, the trial state, mail, sale months each January. Tests, plus a 3-year scripted raise with cups and Journeys.
- [x] 5. UI: Tournament entry (events, eligibility, rules, purse, opponent cards, Auto / Manual), play (standings or bracket, next match, Watch / Fight), Results (placing, purse, items, fame, gains, condition, lifespan in the Lens, promotion, rank, titles, invitations); the battle store's finish hook and technique filter; Guild (month's events, rank, titles, Hall of Fame) and Mailbox in Town; the Mentor's Ledger, Journey beats and the Trial card on the ranch; the Signature moment in the week summary; the credits roll at rank 10; the calendar strip shows the week's events; Battle opens the entry screen on cup weeks.
- [x] 6. `npm run verify`, a headless Chrome run (a cup on Auto to the Results, a Journey with its Trial, the Guild), PROGRESS.md, commit `M5: tournaments, ranks and Journeys`, push, confirm the deploy, phone checklist, stop.

**Phone check:** take a monster from grade E to C or higher; do two Journeys and learn a technique; watch a rival's habit.

## M6: Legacy (Freezer, Fusion, Memorial, Heartstones)

- [ ] Freezer (20 slots), freeze and thaw, Freezer use in Lab, Versus and Battle Lab.
- [ ] Fusion: candidate odds, compatibility comment, inheritance math, catalysts, Ancestors, lineage tree.
- [ ] Farewell scene, epitaph, Memorial wall, Heartstones and Heirloom, Gentle-mode Elder Grove and mentoring.
- [ ] Full Shrine: two-field input, Randomize, teasers, Sleeping Stones, Encyclopedia re-creation (500G), secret phrases (hashed).
- [ ] Market seasonal stock.
- [ ] Tests: fusion odds normalization, inheritance math, Heartstone caps, Shrine determinism across 1,000 phrases (snapshot test), secret phrases.

**Phone check:** freeze two monsters and fuse them; check the odds screen; let a monster pass away (or retire) and use its Heartstone; find a secret phrase.

## M7: Exploration and unlocks

- [ ] Expeditions: invitations, node maps for the 4 sites, stamina, obstacles, search, fog, retreat, rewards (including Stat Sweets and Songsheets), guaranteed key routes.
- [ ] All 8 unlock chains (CONTENT §11), weather events, ranch upgrades (May offers), rumors (shop, mail, rivals).
- [ ] Journal: Encyclopedia, Sleeping Stones, Rumors, Records, Titles, Hall of Fame.
- [ ] Odd Jobs (Turnip Sort).
- [ ] Tests: every unlock chain triggers from a scripted state; nothing becomes impossible after failure (re-trigger tests).

**Phone check:** go on an expedition; trigger at least one unlock; open the Journal.

## M8: Sound, juice and polish

- [ ] ZzFX sound effects and original looping music (ranch by season, town, battle, victory, farewell, shrine); volume and mute; iOS audio unlock and ambient session.
- [ ] Drill vignettes for all 11 drills, emotes, seasonal backgrounds and weather overlays, battle effects polish.
- [ ] Install-help card (iOS and Android), backup reminders, the "Update ready" flow, the left-handed layout, text sizes.
- [ ] Accessibility pass (GAME_DESIGN §24) and a performance pass (bundle size, lazy-load heavy screens).
- [ ] Planner queue (up to 8 weeks) with auto-stop rules.

**Phone check:** play with sound on; install-help card; text size; reduced motion; queue 8 weeks.

## M9: Balance, QA and the v1.0 release

- [ ] Run whole-life sims for every breed under all 4 care policies; adjust tuning to meet GAME_DESIGN §26; record results in `docs/BALANCE_REPORT.md`.
- [ ] Battle matrix for all 30 breeds at totals 1,000, 2,000 and 3,000; fix any matchup outside 30–70%.
- [ ] Optional Playwright smoke test (Pixel and iPhone emulation): new game → train → battle → save → reload. It needs Windows 11; skip it if unsupported.
- [ ] Bug bash from the owner's notes; final README (how to play, install, back up) and CREDITS.
- [ ] Tag `v1.0.0`.

**Phone check:** a full playtest session; export a backup.

## LATER (after v1.0)

Sketch Stone (draw-to-seed) · local 2-player Versus · optional coach mini-games for drills · a second trainee stall · online friend leagues (would need a backend) · cloud sync · localization.
