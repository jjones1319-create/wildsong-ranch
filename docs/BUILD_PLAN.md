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

- [x] Freezer (20 slots), freeze and thaw, Freezer use in Lab, Versus and Battle Lab.
- [x] Fusion: candidate odds, compatibility comment, inheritance math, catalysts, Ancestors, lineage tree.
- [x] Farewell scene, epitaph, Memorial wall, Heartstones and Heirloom, Gentle-mode Elder Grove and mentoring.
- [x] Full Shrine: two-field input, Randomize, teasers, Sleeping Stones, Encyclopedia re-creation (500G), secret phrases (hashed).
- [x] Market seasonal stock.
- [x] Tests: fusion odds normalization, inheritance math, Heartstone caps, Shrine determinism across 1,000 phrases (snapshot test), secret phrases.

**Detailed plan (written 2026-10-23, after the owner confirmed M5):** version `0.8.0`. No new dependencies. Legacy lives in the save (schema v5): `freezer` (20), `elderGrove` (Gentle retirees), `memorial` (snapshots with cause and epitaph), `heartstones` (10, 15 with the Lantern Garden), `encyclopedia`, `sleepingStones`, `unlocked`. The farewell is a flow that ends in `concludeLife`; an empty ranch offers the Freezer, the Market and the Shrine. Secret phrases are stored as cyrb53 hashes of the normalized phrase. Unlock chains, the Lantern Vigil mail, the Journal pages and the Lantern Garden purchase stay in M7.
- [x] 1. Data: `FUSION`, `HEARTSTONE`, `FREEZER`, `SHRINE`, `VARIANTS` and `ELDER` numbers in `tuning.ts`; `data/secrets.ts` (hash → variant, palette, bonus); the new text; `art/monster/variants.ts` palettes and the render override; schema v5 (`freezer`, `elderGrove`, `memorial`, `heartstones`, `encyclopedia`, `sleepingStones`, `unlocked`, `elderMentorMonth`; the monster's `heirloom`) with a migration and tests.
- [x] 2. `core/legacy.ts`: freeze, make active (swap), send to the Freezer, release, `concludeLife` (Memorial, Heartstone, Elder Grove), `heartstoneFrom`, `giveHeartstone`, caps, the Elder mentor. `core/fusion.ts`: outcome odds (4/3/2/1 and 3/2/2/1, × strength/5, locked mains removed, normalized, < 1 % dropped, ≤ 6; the Lineage Seal), compatibility M and Pell's comment, the baby (offsets × P × K, catalysts, grades/guts/lifespan/trait from the baby's breed, the two technique cases, nature and form (2·P1 + P2)/3, generation), parents to the Memorial. `core/shrine.ts`: secret variants, Sleeping Stones, Randomize, the Encyclopedia's 500G re-creation; `core/variants.ts`: birth bonuses and the rule hooks (every food liked, Honey Bread liked, birthday calm, Far +5 hit, Wither +5, prizes +25 %); `core/market.ts`: buying after the first monster. Hooks in the engine (Heirloom +3 hit), food, aging and the cup finish. Tests: odds normalization, inheritance math, Heartstone caps, a 1,000-phrase determinism snapshot, every secret phrase, the migration, and a life → farewell → Heartstone → Fusion integration test.
- [x] 3. UI: the Farewell scene (dusk, best moments, the epitaph, Say goodbye), the empty ranch card, Dr. Pell's Lab in Town (Freezer with Make Active / Edit / Release, Fusion with the odds and the comment, the Memorial wall with epitaph editing and Duplicate to edit, Heartstones with Give, the Elder Grove on Gentle, the family tree on a fused monster's card), the Shrine (two fields, Awaken, Randomize, the stone's teaser, Sleeping Stones, the Encyclopedia with re-creation), the Market (starters and the season's breed; to the ranch or the Freezer); the Freezer in the Lab's Library, Versus and the Battle Lab; Send to Freezer and Make Active in the Library; variant names and badges; `legacy.css`.
- [x] 4. `npm run verify`, a headless Chrome run (a farewell with an epitaph and a Heartstone, two monsters frozen and fused, a secret phrase), PROGRESS.md, commit `M6: legacy`, push, confirm the deploy, phone checklist, stop.

**Phone check:** freeze two monsters and fuse them; check the odds screen; let a monster pass away (or retire) and use its Heartstone; find a secret phrase.

## M7: Exploration and unlocks

- [x] Expeditions: invitations, node maps for the 4 sites, stamina, obstacles, search, fog, retreat, rewards (including Stat Sweets and Songsheets), guaranteed key routes.
- [x] All 8 unlock chains (CONTENT §11), weather events, ranch upgrades (May offers), rumors (shop, mail, rivals).
- [x] Journal: Encyclopedia, Sleeping Stones, Rumors, Records, Titles, Hall of Fame.
- [x] Odd Jobs (Turnip Sort).
- [x] Tests: every unlock chain triggers from a scripted state; nothing becomes impossible after failure (re-trigger tests).

**Detailed plan (written 2026-10-23, after the owner confirmed M6):** version `0.9.0`, schema v6, no new dependencies. An expedition is the week's action: the map is played at once on its own screen and saved after every tap (it resumes like a cup); the loot and the after-effects (fatigue +40, stress −10) apply when the trip ends, and weeks 2–4 pass as "away" weeks like a Journey's. The map is a forward-only layered node graph (12–16 nodes, start → camp) with a guaranteed "spine" route to the site's event node: only the stated obstacle thresholds, no fog, step costs that fit the base stamina. Weekly triggers (invitations, rumors, the Vigil letter, the May upgrades letter, storms, the cocoon, the Reefclaw) run from `beginWeek`; key items are offered at the Shrine (or handed to Dr. Pell) to wake a breed. Where the docs are silent: the storm chase is a yes/no card, the cocoon just happens, "50 variants" counts main/sub combinations, and a Lootlid with no room still unlocks the breed.
- [x] 1. Data and save: `EXPEDITION`, `UNLOCKS`, `UPGRADES`, `ODD_JOBS`, `TITLES` numbers in `tuning.ts`; `data/expeditions.ts` (the 4 sites, obstacles, loot tables, event nodes); `data/upgrades.ts`; new types (site ids, node kinds, mail kinds, week actions); the text (`text/expedition.ts`, `text/journal.ts`, additions to `ui.ts` and `wren.ts`); schema v6 (`expedition`, `pendingEvent`, `unlocks`, `records`, `oddJobWeek`, `memorialVisitMonth`, `encyclopedia.combos`) with a migration and tests.
- [x] 2. Core: `core/expedition.ts` (map builder with the spine, stamina, moves, obstacles and detours, hidden spots, fog, search and treasure, the Strange Chest with its pity timer, the hidden archive, retreat, exhaustion, the end of the trip); `core/unlocks.ts` (offerings, the Blueprint, the Vigil, the cocoon and metamorphosis, the storm chase, the Reefclaw, chain stages); `core/events.ts` (the weekly triggers and mail); `core/upgrades.ts`; `core/oddJobs.ts`; `core/titles.ts`; `core/journal.ts` (records, Encyclopedia rows); selling loot in `economy.ts`; Gearhoot and Reefclaw at the Market; the Masquerade Cup, the Shard Mask and the Wyrm Scale in `tournament.ts`; the Vigil hook in `legacy.ts`; the new actions and free actions in `week.ts` and `game.ts`. Tests: map guarantees over 200 seeds per site, every formula, all 8 chains from scripted states, re-trigger after every failure, titles, records, odd-job pay, upgrades, selling, the migration, and an integration run (invitation → expedition → sell → offer → a Sleeping Stone wakes).
- [x] 3. UI: the Expedition screen (SVG node map, stamina, Tomas, Retreat / Detour, the summary), the ranch's Expedition button and storm card, the Journal (Encyclopedia, Sleeping Stones, Rumors, Records, Titles, Hall of Fame), Odd Jobs (Turnip Sort), Ranch upgrades, Shrine offerings and the Vigil, the Blueprint and the Lantern Garden visit at Dr. Pell's, Basil's Sell tab and rumor line, the new letters, Market offers, Town and Guild links, `expedition.css`.
- [x] 4. `npm run verify`, a headless Chrome run (an expedition to the camp, selling loot, an offering, the Journal, a Turnip Sort round, an upgrade), PROGRESS.md, commit `M7: exploration and unlocks`, push, confirm the deploy, phone checklist, stop.

**Phone check:** go on an expedition; trigger at least one unlock; open the Journal.

## M8: Sound, juice and polish

- [x] ZzFX sound effects and original looping music (ranch by season, town, battle, victory, farewell, shrine); volume and mute; iOS audio unlock and ambient session.
- [x] Drill vignettes for all 11 drills, emotes, seasonal backgrounds and weather overlays, battle effects polish.
- [x] Install-help card (iOS and Android), backup reminders, the "Update ready" flow, the left-handed layout, text sizes.
- [x] Accessibility pass (GAME_DESIGN §24) and a performance pass (bundle size, lazy-load heavy screens).
- [x] Planner queue (up to 8 weeks) with auto-stop rules.

**Detailed plan (written 2026-10-23, after the owner confirmed M7):** version `0.10.0`, schema v7 (the planner queue), no new dependencies. Audio is ZzFX loaded lazily on the first tap plus a tiny step sequencer rendered in pure TypeScript (nine original loops); music follows the screen and the season. The planner runs through the same `beginWeek → chooseAction → finishWeek` controller one week at a time, keeps last month's food, says nothing after drills (so it never changes balance), and stops before a week on a request, a pending event, a trial, an eligible cup or new mail, and after a week on illness, a breakdown, a lifespan warning, a forced rest, the Signature, a grow-up, or fatigue ≥ 60 / stress ≥ 50. The left-handed layout mirrors the battle pads (forward under the left thumb) and the control cluster. Heavy screens load lazily so the first paint is lighter.
- [x] 1. Data and save: `AUDIO`, `PLANNER`, `BATTLE_FX`, `BACKGROUND`, `INSTALL` in `tuning.ts`; settings gain volumes, left-handed, install-help and backup stamps (fallbacks, no version); `GameState.planner` with schema v7, a migration and tests; `zzfx` types; the text (`install`, `backup`, `planner`, settings additions, emote labels, Wren's planner lines).
- [x] 2. Audio: `audio/sfx.ts` (the ZzFX table), `audio/music.ts` (tracks and the pure renderer, tested), `audio/player.ts` (unlock on `pointerup`, ambient session, volumes, ducking, pause when hidden), the screen → track hook, and the hooks for taps, drill stingers, battle events, coins, mail, the stone hum and learning; volume sliders and a test button in Settings.
- [x] 3. Juice: eleven drill vignettes (`vignette.css`, prop class hooks), emotes (`core/emotes.ts`, `Emote.tsx`), `art/backgrounds.ts` (ranch by season × weather with rain, snow, storm and cloud overlays; lighter scenes for Town, the Shrine and the arena), and battle effects (the keyframe clash fix, lunge, projectiles, hit flash, knockback, crit sparkle, KO flop, victory hop).
- [x] 4. Shell: the install-help card (iPhone and Android, the native prompt when offered), backup reminders (`save/backup.ts`, the ranch card, stamps on export), the update store with "Check for updates" in Settings, the left-handed layout, and a text-size audit at 130 % on 360 px.
- [x] 5. Accessibility and performance: the Reduce motion setting on `<html>` so CSS honours it, labels on icon-only buttons and bars, focus outlines, no flashing above 3 Hz; `lazyScreen()` for the Battle, Lab, Tournament, Expedition, Journal, Odd Jobs, Farewell and Credits screens and the audio module; the main chunk well under 500 kB.
- [x] 6. Planner: `core/planner.ts` (queue of up to 8, blockers, `runPlannedWeek`, the log), tests for the cap, every stop reason, the food default and a clean run; the Planner sheet, the running strip and the summary card.
- [x] 7. `npm run verify`, a headless Chrome run (install card, seasons and weather, a vignette, the planner, a battle with effects and the left-handed pads, Settings at 130 %, the backup card), PROGRESS.md, commit `M8: sound, juice and polish`, push, confirm the deploy, phone checklist, stop.

**Phone check:** play with sound on; install-help card; text size; reduced motion; queue 8 weeks.

## M9: Balance, QA and the v1.0 release

- [x] Run whole-life sims for every breed under all 4 care policies; adjust tuning to meet GAME_DESIGN §26; record results in `docs/BALANCE_REPORT.md`.
- [x] Battle matrix for all 30 breeds at totals 1,000, 2,000 and 3,000; fix any matchup outside 30–70%.
- [x] Optional Playwright smoke test (Pixel and iPhone emulation): new game → train → battle → save → reload. It needs Windows 11; skip it if unsupported.
- [x] Bug bash from the owner's notes; final README (how to play, install, back up) and CREDITS.
- [x] Tag `v1.0.0`.

**Detailed plan (written 2026-10-23, after the owner confirmed M8 and asked for the milestone to run through on its own):** version `1.0.0`, no schema change. The two matrices are far too slow for `npm test` (4,800 lives and 261,000 battles), so they run as a dev script across worker threads and write `docs/BALANCE_REPORT.md`; the test suite keeps the §26 sim tests plus new per-breed guards that run in seconds. The full matrix can still be run inside Vitest with `WILDSONG_FULL_SIM=1`. Playwright is supported on this machine (Windows 11) and drives the installed Chrome (no browser download), so it is a devDependency with its own `npm run e2e`, outside `verify` so the deploy stays fast.
- [x] 1. The balance script: `scripts/balance.ts` (`npm run sim:balance -- [--seeds N] [--battles N] [--only raise|battle]`) with `scripts/balance-worker.ts`: every breed under the four care policies over 40 seeds (life lived, breakdowns, totals by year, outcome rates), and the 30 × 30 battle matrix at totals 1,000 / 2,000 / 3,000 with 200 seeds per cell, sides alternating; flags every cell outside its §26 band and writes the tables and the misses to `docs/BALANCE_REPORT.md`.
- [x] 2. Tuning: read the report, then adjust `tuning.ts` (AI, traits, NPC weights) or technique values and breed traits until every breed's life bands and every matchup sit inside the targets, re-running the script after each change. Formulas stay as they are (GAME_DESIGN §26).
- [x] 3. Tests: per-breed raising guards in `lifeSim.test.ts` (every breed, Good care over 12 seeds: life lived inside a band around the Good target and a stat total that grows; Neglect shorter than Good); the battle sample in `balance.test.ts` becomes a hard rule (every sampled pair inside 30–70 %) and the full matrix runs under `WILDSONG_FULL_SIM=1`.
- [x] 4. Bug bash from the open known issues: the Masquerade Cup and the Crowns scale their opponents to the player's total like Corin does (`TOURNAMENT.specialScalePct`); the Shrine's tab labels no longer wrap at 130 %; the Journal's chips scroll in one row; the lightning bolt strikes in three places; a review pass over the UI for crashes on bad data.
- [x] 5. Playwright: `@playwright/test` (devDependency), `playwright.config.ts` with Pixel 7 and iPhone 14 profiles on the installed Chrome, `e2e/smoke.spec.ts`: new game → a week of training → a battle → the save survives a reload; `npm run e2e` builds and previews first. Skipped on CI.
- [x] 6. README (how to play, install, back up and restore, the Lab, the docs), CREDITS (Playwright), `CHANGELOG`-style notes in PROGRESS.md, version `1.0.0`.
- [x] 7. `npm run verify`, `npm run e2e`, PROGRESS.md, commit `M9: balance, QA and v1.0`, push, confirm the deploy, tag `v1.0.0` and push the tag, phone checklist, stop.

**Phone check:** a full playtest session; export a backup.

## M10: Smarter battles (AI 2.0, the arena camera, balance follow-ups)

Spec: `docs/BATTLE_AI_V2.md` (owner-requested after v1.0). Version `1.1.0`, no save-schema change (the two new settings have per-field fallbacks).

- [x] 1. Scaffolding: `AI_V1` keeps the v1 brain's numbers for `core/battle/aiV1.ts` (one comparison test); `AI` holds every AI 2.0 number; `AI_TIERS`, `AUTO_STYLES`, `PLAN_MODES`; `FighterSetup.tier / style / brain`; the `auto` input carries the style; `FighterState` gains the plan, the reaction-delay schedule, variety stamps, counters (direction changes, touching ticks, pushes) and last-tick snapshots of `moveDir` / `aiTargetBand` so neither side reads the other's same-tick decisions; `plan` log events; Gilded gains guts on a landed hit; `bodyRadius` 80 / `startX` 230 (the start gap stays 300).
- [x] 2. AI 2.0 (`core/battle/ai.ts`): tiers, the think loop with events, the range plan (offense × aggression − threat × caution + variety − travel), sweet spots, the goal technique and the save-or-spend rules, footsies, corner awareness, anti-stall, pushes, dashes with a reason, the situation modifiers, trait reads, rival habits, Auto styles, the plan icon with a hold.
- [x] 3. Tier plumbing: `tierFor(participant, event)` and `trialTier(grade)` in `core/tournament.ts`; cups, Trials (manual, auto and skip), Versus, the Battle Lab and the balance script pass tiers; the player's Auto is always expert with the chosen style; `setAutoStyle` queues the style as an input mid-battle.
- [x] 4. Arena camera (`ui/battle/camera.ts`, pure, 11 tests): framing, zoom bounds, wall clamp, a critically damped spring (an ease with Reduce motion); `BattleScreen` draws the world through CSS variables set once per animation frame; fence posts at the walls; floats counter-scale; shots fly through the camera.
- [x] 5. Thinking icons and settings: `showThinking` (null = follow Breeder's Lens) and `autoStyle` in `SettingsSchema`; the Play card and the battle pause sheet carry both controls; text in `data/text`.
- [x] 6. Balance: Expert vs Expert in the script and the sampled guard; the four pure casters' Near basic moved to Close (their only answer to an Unshakable brawler); brawler kits nudged up and ranged kits down inside the §10.2 bands (CONTENT §3 and `techniques.ts` together); Statue Pose 50 %, Moth Dust ×0.65, Gilded +7 guts; the script checks every pair 25–75, ≥ 95 % of pairs 30–70, Lootlid's mean 40–60 (other means are flagged in the table), the starters' KO average, and prints AI health and its run time. Veteran toughness was not needed (the 3,000 KO average sits inside 3–15 with AI 2.0).
- [x] 7. Tests (`ai2.test.ts`, `camera.test.ts`, updated `ai`, `habits`, `engine`, `balance` and `files` tests); `npm run verify`; PROGRESS, GAME_DESIGN §12.1 / §12.8 / §12.10 / §12.11 / §26, CONTENT §2.1 / §3, BALANCE_REPORT; commit `M10: smarter battles`, push, confirm the deploy, phone checklist, stop.

**Phone check:** BATTLE_AI_V2 §6.

## Visual upgrade (V1–V5)

Decided Oct 24, 2026 (`docs/VISUAL_UPGRADE_PLAN.md` §0): richer storybook vector, a Cozy / Standard / Flashy intensity setting, 5-second skippable cutaways with four outcome variants, order V1 → V3 → V2 → V4 → V5, no 3D pilot, painted backgrounds from ChatGPT from V4 on. Each milestone has its own spec file and its own phone check.

### V1: Effects engine and arena staging

Spec: `docs/VISUAL_V1_EFFECTS.md`. Version `1.3.0`, no save-schema change (the three Graphics settings have per-field fallbacks). The simulation is untouched.

- [x] 1. Dependencies: `pixi.js` 8.22 and `pixi-filters` 6.1 (the two the spec allows); the WebGL renderer is imported directly so the WebGPU code stays out of the chunk (fx chunk about 134 KB gzipped plus 11 KB for Pixi's browser bits, under the 150 KB budget).
- [x] 2. `FX` in `tuning.ts`: Quality budgets, the Intensity table, the Auto sample, the flash cap, every primitive's defaults.
- [x] 3. Elements: `Element` on every `Technique`; `data/elements.ts` with the §5 rules (keyword categories in order, named exceptions, breed-only keywords, plain melee → Physical, breed defaults with INT / POW splits, `ELEMENT_OVERRIDES` for the owner's corrections); `scripts/element-table.ts` prints the table; `scripts/element-column.ts` writes the Element column into CONTENT §3 / §3.1 and NEW_MONSTERS §4; a test checks the docs match the data.
- [x] 4. `src/fx/`: `FxLayer` (WebGL renderer, world / shapes / screen containers, the fx clock with playback speed, pause, hit-stop, idle sleep, hidden-tab pause, context loss), `camera` (world ↔ screen), `rng` (visual only), `pool`, `sim` (typed-array particles), `emitter` (two ParticleContainers over a Canvas-2D atlas), `textures` (16 procedural frames and a noise map), `elements` (the look per element), `quality` (tiers, Intensity, FlashGate, shake), `bus` (engine events → FxEvents), `recipes` (the default recipe per element per moment), `filters` (haze, shockwave, bloom, RGB split by tier).
- [x] 5. The 18 primitives in `src/fx/primitives/`, one file each (`screen.ts` holds the four screen-space ones), the water sheet as a custom GLSL mesh shader, lightning from pure midpoint displacement.
- [x] 6. `ui/battle/Arena.tsx`: the arena extracted from the battle screen (a stage wrapper that shakes, the world, the fx canvas, the floats layer, the impact-frame overlay, the hit-stop class, the camera loop feeding the layer); `battleStore` publishes FxEvents; the CSS shot, sparkle and shake are gone.
- [x] 7. Settings → Graphics: Quality (Auto / Ultra / High / Lite; Auto measures the first battle and remembers) and Intensity (Cozy / Standard / Flashy); reduced motion forces Cozy; `fxStore`.
- [x] 8. Monster Lab → Effects (`LabEffects.tsx`, `#lab/effects`): two preset monsters, every primitive × element, Random attack, Combo, Stress test, Clear, fps / particles / tier / intensity, the Quality and Intensity controls, Record 3 s in dev, `window.__fx` for Playwright.
- [x] 9. Review: `e2e/fx-review.spec.ts` writes one contact sheet per element to `docs/fx-review/` (manual fx clock, two moments per primitive); looked at and tuned before shipping. `e2e/fx-lab.spec.ts` is the optional smoke test.
- [x] 10. Tests: `fx/*.test.ts` (sim, pool, quality, flash gate, shake, bus, recipes, bolt geometry, camera), `data/elements.test.ts`, the settings schema; `npm run verify`; PROGRESS, GAME_DESIGN §21 / §22 / §24, CONTENT §3, NEW_MONSTERS §4, CREDITS; commit `V1: effects engine`, push, confirm the deploy, phone checklist (spec §11), stop.

**Phone check:** VISUAL_V1_EFFECTS §11.

### V3: Monster animation 2.0

Rigs per body plan with named joints, a pose library (stand, sit, brace, crouch, lunge, cast, bite, slam, hover, hit, dazed, faint, victory hop, sleep, eat, shiver, flex) with squash-and-stretch and secondary motion, richer shading (gradients, rim light, contact shadow, subtle textures), eyes that track taps, a poses strip on the Monster Card, mood through body language on the ranch. Spec to come (`docs/VISUAL_V3_RIGS.md`).

- [ ] Plan in plan mode at the start of the milestone.

### V2: Visible attacks

An attack recipe for every one of the 294 techniques (anticipation, effects, travel, impact, hit reaction, sound) built from the V1 primitives by family × element; bespoke 1–2 s cinematics for Signatures and Specials; hit reactions by body plan; KO flop with stars. Spec to come (`docs/VISUAL_V2_ATTACKS.md`).

- [ ] Plan in plan mode at the start of the milestone.

### V4: Cinematic drill cutaways

Each of the 11 drills as a real 3–5 s skippable scene with the monster inside it and Success / Great / Cheat / Fail variants; Waterfall Stand first as the pilot; painted parallax layers from ChatGPT (prompts written by Claude), everything else in code. Spec to come (`docs/VISUAL_V4_DRILLS.md`).

- [ ] Plan in plan mode at the start of the milestone.

### V5: World polish

Ranch, town, shrine and arena backdrops as painted parallax with weather, time of day and seasons; the Shrine awakening, tournament walk-ons, podium, Farewell and Signature moments as short cinematics. Spec to come (`docs/VISUAL_V5_WORLD.md`).

- [ ] Plan in plan mode at the start of the milestone.

## Sound 2.0 (S1–S3)

Decided Oct 25, 2026 (`docs/SOUND_UPGRADE.md` §0), done before V3: calm, warm, acoustic music (ocarina and recorder leads, harp, strings, soft hand drums, lots of space) played live in the browser from CC0 samples (VCSL, VSCO 2 CE, Kenney) by our own sequencer; a theme for every event; a soundscape for every drill; soft, natural effects; procedural ambience. ZzFX goes. `src/core` is untouched. The owner judges every stage on the phone through the Sound Lab, then sends listening notes before the next stage.

### S1: Calm engine and first songs

Spec: `docs/SOUND_UPGRADE.md` §15 S1. Version `1.6.0`, no save-schema change (the new sound settings have per-field fallbacks). Commit `Sound S1: calm engine and first songs`.

- [x] 1. **Baseline:** render the 9 old loops and the ZzFX effects with the shared analysers into `tools/audio/baseline-legacy.json` before anything is removed.
- [x] 2. **Samples:** `npm run audio:samples` (`tools/audio/build-samples.ts`): sparse, blobless clones of VCSL and VSCO 2 CE at the pinned commits, the two Kenney zips (SHA-256 recorded), per-instrument file rules, pitch detected per sample (YIN), cleaned, loop-baked, Opus via `ffmpeg-static`, re-decoded and measured, `public/audio/manifest.json`, packs computed from what S1 uses, budget check, CREDITS.
- [x] 3. **Engine** (§4): `engine/{context,nodes,driver,scheduler,samples,sampler,synth,reverb,ambience,sfx,meters}.ts`; buses and master chain, listening presets, mono, fallback voices, seeded reverbs, `window.__audio`. ZzFX removed from the package, the imports, CREDITS and CLAUDE.md.
- [x] 4. **Music system** (§6): the ABC subset, chord symbols, the 11 accompaniment generators, percussion lines and kits, the song model (layers, stems, weather, breaths, arrangements), the checker (14 rules), the motifs.
- [x] 5. **Director** (§11): a pure decision table with a row for every Screen and every event, stand-ins marked `TODO_S2` / `TODO_S3`, the controller (crossfades, quantised changes, stingers, debounce, pause filter).
- [x] 6. **Pieces:** Wildsong (title, lobby and credits arrangements); the four ranch songs with weather rules and breaths; Town with every stem; `cup` with lobby, base, drive and tension plus the four season palettes and kits.
- [x] 7. **Stingers and musical effects:** `matchWin`, `matchLoss`, `matchDraw`, `cupWin`, `promotion`; `coin`, `buy`, `mail`, `itemGet`, `sweet`, `learnTechnique`, `plannerStop`, `growUp`, `prime`, `weekStart`, `wrenReport`.
- [x] 8. **Beds:** `meadow`, `summer-field`, `autumn-wind`, `winter-yard`, `brook`, `waterfall-near`, `town`, `market`, `shop`, `guild`, `library`, `arena-out`, `arena`; crowds `small` and `large`; all weather overlays.
- [x] 9. **Effects:** the whole UI set; the whole battle set (every FxEvent kind by element and strength, the engine-only events, the last-5-s ticks); the Shrine's stone hum; the Echo Stones notes and flourish.
- [x] 10. **Drill cues:** the system (`drillCue.start/skip/end`, `resultAt`), Waterfall Stand in full as the pilot, a soft generic cue with generic outcome stingers for the other 10 drills.
- [x] 11. **The rest:** settings (§12) and Settings → Sound; the Sound Lab (§13, `#lab/sound`); `npm run audio:check` (+ `--calibrate` → `src/audio/levels.json`), `audio:review`, `audio:analyze`, `check:build` (in `verify`); the unit tests (§14.2) and `e2e/sound.spec.ts` (§14.5).
- [x] 12. **Docs:** GAME_DESIGN §23 rewritten and §24 extended; CLAUDE.md (libraries, an Audio section, `.gitignore` entries); CREDITS (VCSL, VSCO 2 CE, Kenney with commits, links and hashes); README; PROGRESS (one line per piece on what to listen for); this list ticked; `docs/SOUND_UPGRADE.md` committed.
- [x] 13. **Finish:** `npm run verify`, `npm run e2e` and `npm run audio:check` green; commit, push, confirm the deploy, the S1 phone checklist (spec §15), then stop for the owner's listening notes.

**Phone check:** SOUND_UPGRADE §15 "Phone check S1".

### S2: A theme for every event

The 16 event compositions, the per-event arrangement table for all 60 events, the S2 stingers and the rival calling cards, every crowd size, recomputed packs. Spec: `docs/SOUND_UPGRADE.md` §15 S2. Version `1.7.0`, no save-schema change. Commit `Sound S2: a theme for every event`.

Decided at the start of the stage (Oct 27, 2026, approved with the plan): the horn's samples stop at middle C, so horn-led pieces pair the horn in its warm range with violins or flute an octave up; two new kits, `tide` and `masque`; one 8 s stinger per Crown; Trial tonics up to ±5 semitones; the checker also asks for the Wildsong motif in `ascension` and `legend`, Corin's motif in `rival` and the masked motif in `masquerade`.

- [x] 1. **S1 gaps:** the `events` pack loads on the cup screens and stays in use while wanted; swapped leads fold into their instrument's range; the results screen plays its stinger; Trials read their site from the Trial.
- [x] 2. **Samples:** `organ`, `wine-glasses`, `ocean-drum`, `harpsichord`, `balafon`, `clarinet`; `npm run audio:samples`; packs recomputed (the new instruments land in `events`); budgets.
- [x] 3. **Event table and director:** every row plays its own theme; `THEME_DEFAULTS`; Ascensions take the season colour; the Summit Qualifier arrangement; Trial sites; the Corin rule; requests carry their packs and the clap-along; no `TODO_S2` left.
- [x] 4. **Pieces:** `open`, `ascension`, `crown-dawn`, `crown-tides`, `crown-embers`, `crown-frost`, `legend`, `masquerade`, `rival`, `summit` (+ `qualifier`), `rally`, `rally-rogue`, `sprout`, `elders`, `trial` (five sites), `practice`; the cup's colour line.
- [x] 5. **Stingers and cards:** `cupPlaced`, `cupOut`, the four Crown stingers, `legendWon`, `rankUp`, `titleEarned`; stinger chains; the nine rival calling cards; the results screen and the round preview wired.
- [x] 6. **Crowds:** a profile per size, `hushed` polite only, `chanting` on 2 and 4, clap-along on the music's beats in the last 10 s, applause at every match end.
- [x] 7. **Sound Lab and tools:** the Events group, the event picker, the cards; render items for every theme (battle, lobby, tension), the new stingers, cards and crowds; `--jobs`, `--only` lists.
- [x] 8. **Tests:** event table, director, songs, stingers, cards, crowds, folding, stinger chains, e2e (the `events` pack on the cup screen, an Ascension plays `ascension`).
- [x] 9. **Docs:** GAME_DESIGN §23; SOUND_UPGRADE §6.4, §7.4, §7.6; PROGRESS (one line per piece); CREDITS; this list ticked.
- [x] 10. **Finish:** calibrate; `npm run verify`, `npm run e2e`, `npm run audio:check` green; `audio:review`; commit, push, confirm the deploy, the S2 phone check, then stop for the owner's listening notes.

**Phone check:** SOUND_UPGRADE §15 S2 (an Ascension, the Masquerade, the Rival Showdown, every Crown in the Sound Lab, two regular cups from one season, "does any tune sound familiar?").

### S3: Places, trainings and moments

The Shrine, the Labs, Journey and Expedition pieces, Turnip Sort, the Echo Stones drone, Meadow Dash, the farewell loop; the S3 stingers; the other 10 drills in full; the remaining beds; monster songs. Spec: `docs/SOUND_UPGRADE.md` §15 S3.

- [ ] Plan in plan mode at the start of the stage, after the owner's S2 listening notes.

## Odd Jobs 2: endless jobs and Meadow Dash (v1.8.0)

The owner asked for no pay cap on Odd Jobs, endless play past the old 150G mark, and a third job that uses the monster. Their choices (2026-10-27): the fifth Echo stone joins at the 150G mark (round 11); Turnip Sort's mix-ups count toward the two that end it only after 150G; Meadow Dash is heats until you lose; SPD helps a little. Spec: CONTENT §13.

- [x] 1. Rules: `core/echoStones.ts` (five stones, an extendable melody, the slow late tempo, no cap), `core/oddJobs.ts` (no cap, overtime with weeds and a shrinking window, an endless seeded dealer, the best), new `core/meadowDash.ts` (the race in fixed ticks with integer distances, rivals, SPD bonus, crossing-time finishes, pay and the best); numbers in `ODD_JOBS`, `ECHO_STONES`, `DASH`.
- [x] 2. Save schema v11 (`turnipBest`, `dashWeek`, `dashBest`) with a migration and a test.
- [x] 3. Screens: the board (three cards with pay and best lines), Echo Stones (the Moon stone on its own row), Turnip Sort (`useTurnipRun`: the clock, the overtime intro, three bins, swipe down), Meadow Dash (one frame loop, the Run pad, pause on hide, the heat card).
- [x] 4. Sound: `echo5`, `dashStep`, `dashGo`; the director's Meadow Dash row (a stand-in until S3).
- [x] 5. Tests, docs (CONTENT §13, GAME_DESIGN §3 and §9, SOUND_UPGRADE §10.4 and §11), `npm run verify`, `audio:check` on the new effects, a headless run of all three jobs, PROGRESS, commit, deploy, phone checklist.

## The Bonds update (v1.9.0)

The owner asked (2026-10-28) for: Echo Stones pay that rises by 1G a round after round 10; consequences for not opening the game (a day: sad, two days: abandoned, four days: gone; Vacation mode turns it off) shown as Blender-made scenes; a welcome where the monster greets you and you can pet it or give it a treat; a weekly Bond action (fetch, hide-and-seek, a shopping trip that can buy a keepsake for the ranch) that boosts training ×1.75 then 0.25 less a week; and more training levels with loyalty deciding the best ones (Fine +0, Good +2, Great +4, Superb +5, Perfect +7; Perfect from loyalty 70). Spec: GAME_DESIGN §1, §6.2–§6.3, §6.9, §6.10; CONTENT §4, §13.

- [x] 1. Echo Stones rising pay.
- [x] 2. Training levels (`core/outcomes.ts`, `core/training.ts`, `OUTCOME.levels`, `DRILL.levels`), retuned so the §26 targets hold (the A/B target moved, see GAME_DESIGN §26).
- [x] 3. Bond weeks (`core/bond.ts`, `data/keepsakes.ts`, the Train sheet's Bond tab, `screens/ranch/bond/`), keepsakes on the ranch and the Monster Card.
- [x] 4. Arrival (`core/arrival.ts`, the store's clock and checks, `ArrivalScene.tsx`, `SceneClip.tsx`), Vacation mode, Sandbox previews, the `awayRule` tip, the neglect and wandered Farewells.
- [x] 5. Blender scenery clips (`tools/blender/`, `public/baked/scenes/`).
- [x] 6. Save schema v12 with its migration and test.
- [x] 7. Tests, docs, `npm run verify`, the e2e specs, PROGRESS, commit, deploy, phone checklist.

## Fusion 2: whole-breed babies and surprise recipes (v1.10.0)

The owner asked (2026-10-28) for Fusion to give one of four breeds, each with a %:
- the first parent's breed and the second parent's breed;
- two random-feeling **surprises** that make sense for the pair, like a snake and a bird making a dragon.

Their choices:
- Fusion babies are always one whole breed. Mixes stay in the Shrine and ✏️ Edit for now (retired everywhere in Art P0, v1.12).
- New combo-only breeds (a bull-warrior and others) wait for the Blender monster work, which comes next.

Spec: GAME_DESIGN §14.3 and §15; CONTENT §2, §2.3 and §6.

- [x] 1. Kinds, rules and signature recipes (`data/fusionRecipes.ts`, CONTENT §2.3), tuned with `npm run fusion:table` so every breed is reachable and none crowds the table.
- [x] 2. Core:
  - odds of 35 / 35 / 20 / 10;
  - the Seal, locked breeds dropping out and the found recipes (`core/fusion.ts`);
  - a pure baby;
  - universal techniques count as part of every kit for inheritance (§10.5).
- [x] 3. Save schema v13 (`fusionFinds`) with its migration and test.
- [x] 4. Pell's Lab (the Fusion tab):
  - hidden "???" rows and source labels;
  - no "most likely" on a tie; Dr. Pell's hint;
  - "New recipe!" on a first find;
  - the right refusal lines.
- [x] 5. Tests (odds, surprises, the pinned table, the spread, data mirror, schema v13), the e2e spec (`e2e/fusion.spec.ts`), docs, PROGRESS, commit, deploy, phone checklist.

## Grades to S: stat caps, inherited traits and grades, stat bars, the stats guide (v1.11.0)

The owner asked (2026-10-28) for:
- growth grades up to S, with each grade also capping its stat (S 1,500, then 100 less a step);
- Fusion babies that inherit a parent's trait and better grades, with a head start of at most 10% of the parents' best trained stats;
- Monster Card bars that fill toward each stat's cap in its own colour, with Stat Sweets as a lighter segment that may pass the cap;
- somewhere that explains what each stat does.

Spec: GAME_DESIGN §4, §5.1–§5.2, §6.3, §8, §11, §12.3, §12.8, §14.3, §15, §16 and §19; CONTENT §6 and §11.

- [x] 1. Golden records first: 30 fixed battles and 6 fixed lives, hashed on the commit before any change (`battle/golden.test.ts`, `sim/golden.test.ts`), plus a guard that no simulated stat reaches 1,000.
- [x] 2. Grade S and the caps:
  - `GRADES`, `GRADE_FACTOR_100.S`, `STAT_CAP_BY_GRADE`, the S gain ceilings;
  - `addTrained` and `lowerStat` for training, Journeys, cups, Heartstones and the cocoon;
  - sweets past the caps (refused only at 9,999);
  - the Pearl to S; NPCs at 999; the walk-speed limit.
- [x] 3. Two traits: `traitsOf` and `hasTrait`; the battle fighter's trait list with sum, multiply, any and first helpers.
- [x] 4. Fusion: `inheritedTraitFor`, `inheritedGrades`, `headStartFrom` (10% limit, trained points only), the born screen lines.
- [x] 5. Save schema v14 with its migration and test.
- [x] 6. UI:
  - the card's coloured stat rows (tap for the guide), the sweets segment and cap mark, the S pill, the inherited trait row;
  - `StatsGuide` (a sheet and the Journal's Stats page);
  - the editor's number box to 9,999, cap labels, "Max all" to the caps and the inherited-trait picker.
- [x] 7. Tests, docs, the e2e card spec, `npm run verify`, PROGRESS, commit, deploy, phone checklist.

## Art 2.0 (P0–P19)

Decided Oct 28, 2026. Spec: `docs/ART_2_PLAN.md`; the owner's prompts are in `ART_2_PROMPTS.md`. Blender makes every monster (a 3D model with its skeleton, animations and face sheet) and every scene; the game only displays them. One milestone per prompt, committed as `Art P<n>: <summary>` with a minor version bump.

**Mixes are retired.** Since P0 every monster is one whole breed. The earlier milestone lists above (M1, M2, M2.5, M5, M6) describe the main/sub mix system as it was built at the time; GAME_DESIGN §14.3 has the current rule.

### P0: One breed per monster (v1.12.0)

The owner retired the main/sub mix system (Oct 28) so that each breed can be designed and painted on its own. Their choices for the old "pure" bonuses: every monster gets the +10% lifespan and Signature access, and the Pure badge goes. Collector now needs 30 looks (was 50).

Spec: GAME_DESIGN §4, §5.2, §7, §10, §12.8, §13, §14.1, §14.3, §15, §19, §22; CONTENT §2.2, §3, §11 and the titles table; ART_2_PLAN §8 (P0).

- [x] 1. Core: `breedBirth(breed)` replaces `mixBreeds(main, sub)`; `subBreed`, `flags.pure` and `appearance` leave the monster; the Signature gates lose their purity checks (Prime, Glacier Bastion, Songsheets, the Guild Library, bosses); Fusion, the Lab, the cocoon (a whole Velvesper), Heartstones, titles and the sims use the one breed; `BIRTH.lifespanBonusPct` for everyone.
- [x] 2. Shrine: the sub step goes. It drew from its own `h2` stream, so every phrase keeps its breed, offsets, likes and nature (checked against the old code over 3,000 phrases; the 106 that were already one breed make byte-identical monsters).
- [x] 3. Data: no accent parts, sub adjectives or sub-quirk tags; "Auto at Prime (loyalty ≥ 60)" for the Signature rows (CONTENT §3 and `techniques.ts` together).
- [x] 4. Save v15: the validator drops the old fields everywhere a monster is stored (bare imports included) and renames an untouched mix name ("Cinder Tumblefox") to the breed's; Heartstones and Encyclopedia phrases lose their sub; tests for saves, files, Libraries, old share codes and garbage.
- [x] 5. Classic art: every monster wears its own breed's palette (secret variants keep theirs); `accents.ts` deleted.
- [x] 6. Screens: one Breed picker in Create and ✏️ Edit, no Colours choice, no Pure badge; names and Library filters by breed.
- [x] 7. Tests, docs, `npm run verify`, e2e, PROGRESS, commit, deploy, phone checklist.

### P1: Pilot monster, Puddlepup in 3D (v1.13.0)

Spec: ART_2_PLAN §2 (the look), §3.1 (pipeline), §3.2 (runtime), §3.3 (where monsters appear), §3.6 (budgets), §5 (the ★ clips), §6 (the review loop), §8 (P1). Done when the owner loves it on the phone; the owner's notes decide what P1 still changes before P2.

- [x] 1. Pipeline: `tools/blender/lib/` (node builder, mesh primitives and merge, rig and skinning, clip authoring, paint bakes, the face sheet, review renders, glTF export), the quadruped plan with the 27 ★ clips, Puddlepup's recipe with its painted textures and the Songheart texture set, `tools/blender/monsters/build.py`, `tools/art/optimize.ts` (glTF-Transform + meshopt, budget report), `npm run art:monster`.
- [x] 2. Runtime `src/art3d/`: Stage3D (one shared renderer, hosts come and go, context loss, portraits off-screen), the actor (cel shader with outline, face sheet cells with blinks and glances, springs on ears and tail, clips with markers and face cues, stage sizes, the old fade, the sick tint), the arena camera that keeps feet on the floor line (tested), the battle clip map (tested), lazy chunk ≤ 300 KB gzipped (check:build).
- [x] 3. In the game: Settings → Graphics → Monsters (3D / Classic), `MonsterPortrait`'s three modes (live, cached picture, Classic), Puddlepup live on the ranch, the Monster Card, the Lab editor, the Shrine, Pell's Meet, the Farewell, the week summary, drill results, expeditions, Echo Stones and the Bond games; pictures in lists (precached base portrait + on-phone cache in IndexedDB); the arena layer (Versus, cups, the Effects Lab) with a Classic opponent still SVG; Monster Lab → Models.
- [x] 4. Review loop: Blender sheets in `tools/blender/out/puddlepup/review/`, in-game sheets by `npm run art:review` in `art-review/puddlepup/`, fresh-eyes review (two passes: the first found the shading too soft, the outline hidden and the hop leaving the frame; all fixed), budgets (583 KB, 8,705 tris, 26 joints).
- [x] 5. Tests (`models`, `faceCells`, `springs`, `arenaCamera`, `battleClips`, `manifest`, `portraitCache`), e2e `models.spec.ts` (WebGL off, model 404, the setting, context loss, one canvas), docs, verify, commit, deploy, phone checklist.

## LATER (after v1.0)

Sketch Stone (draw-to-seed) · local 2-player Versus · optional coach mini-games for drills · a second trainee stall · online friend leagues (would need a backend) · cloud sync · localization.
