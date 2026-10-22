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

- [ ] `core/rng.ts`: mulberry32 with saveable state; `core/hash.ts`: cyrb53-style 53-bit hash and phrase normalization.
- [ ] Data:
  - `data/breeds.ts`, `data/techniques.ts` (180 breed + 24 universal), `data/drills.ts`, `data/foods.ts`, `data/items.ts`, typed and generated from `CONTENT.md`.
  - A test that the data matches CONTENT: counts, ids, and every breed has techniques in at least 3 ranges.
- [ ] `core/monster.ts`: the model and derived values; creation from breed + sub + offsets; mixing rules (GAME_DESIGN §14.3).
- [ ] `core/calendar.ts`: weeks, months, seasons, weather, the week order of operations (GAME_DESIGN §3).
- [ ] `core/training.ts`: truancy, outcome weights, gains, praise/scold, rest, play, requests.
- [ ] `core/aging.ts`: life stages, strain, lifespan, illness, breakdowns, warnings.
- [ ] `core/food.ts` and `core/items.ts`: monthly food, boredom, **unlimited item use** (with the optional one-per-week rule), Stat Sweets (and per-stat "from sweets" tracking), Potential Pearl, Tempo Bell, charms, tonics (stacking rules), fruits (once each).
- [ ] `core/songbook.ts`: Songsheets, the Songbook (owned sheets are permanent), compatibility (universal / breed kit / sub quirk / Signature = pure only), learn, forget, relearn, and the 12-technique cap.
- [ ] `core/save/schema.ts`: valibot schema v1 and a `migrate()` skeleton.
- [ ] **Tests:**
  - Every reference table in GAME_DESIGN §5–§7 and §11.
  - Determinism (same seed → same life).
  - **Sim tests** for the raising targets in GAME_DESIGN §26.
- [ ] A dev-only script `npm run sim:life` that prints a full simulated life for a breed and care policy.

**Detailed plan (written 2026-10-22; building starts after the owner confirms M0 on their phone):** version `0.2.0`. Everything in `src/core/` is pure (injected RNG, integer math, no Date/DOM); every number lives in `src/data/tuning.ts`; relative imports keep their `.ts` extension so Node 24 can run core code directly.
- [ ] 1. `core/rng.ts`: mulberry32 with get/set state, `nextU32`, `nextInt(lo, hi)` inclusive, `nextFloat`, `pick`, `weightedPick`, `shuffle`, `chance(pct)`. Tests: fixed-seed sequence, determinism, save/restore resumes identically, inclusive ranges.
- [ ] 2. `core/hash.ts`: `normalizePhrase` (NFKC → lowercase → trim → collapse spaces → keep letters, digits and spaces of any script) and `cyrb53(str, seed)`. Tests: `"Hello,  World!"` → `"hello world"`, a snapshot of 10 hash values (the contract that keeps every phrase's monster stable), seeds 1 and 2 differ.
- [ ] 3. Data from CONTENT: `breeds.ts` (20), `traits.ts`, `techniques.ts` (180 breed + 24 universal, ids like `puddlepup.splash-nip`, structured `learn` requirements, `subQuirk` flag, parsed effects), `drills.ts` (11), `foods.ts` (7), `items.ts` (every row of CONTENT §6 with category, price, effect and gate). Data tests: counts and unique ids; each breed has 2 Basics, one each of the other families, exactly one sub-quirk (a Basic) and techniques in ≥ 3 ranges; band sanity for Basic/Hit/Heavy/Wither/Sharp rows (rows outside a band are reported to the owner, not changed).
- [ ] 4. `core/monster.ts`: types, `gradeFactor` (§5.2), derived values (loyalty, style + band, life stage, stage factor, strain, stars, total), `createMonster(main, sub, offsets, rng)` with the §14.3 mixing rules, `clampMonster`. Tests: grade factor, stage boundaries for all 4 growth types, the `sf` table, mixing examples including pure and tie-breaks.
- [ ] 5. `core/calendar.ts` (week index ↔ year/month/week, season, month start, seeded weather with Storm only in summer and Snow only in winter) and `core/week.ts` (`runWeek` in the strict §3 order, returning a phase log). Tests: the order, and that items never use a turn.
- [ ] 6. `core/training.ts`: stars, truancy, outcome weights with trait and Training Yard modifiers, normalization, `resolveDrill`, gains (light/heavy/secondary with Great/Cheat/Fail rules, lowered stat, breed bonus +1, tonic +3), chore pay, praise/scold/skip table (Cheerful halves scold stress), rest and play, request trigger/type/deny. Tests: the six §6.2 reference rows, the three §6.3 gain tables, the §6.5 rest/play table, request chances at 40/60/100.
- [ ] 7. `core/aging.ts`: `extraLifespanLoss` thresholds, illness and breakdown rolls with difficulty modifiers, weekly tick, warnings (25 % left, 48 weeks, 10 weeks), prime and past-prime notices, size stage, assistant labels, expression cues. Tests for every threshold and difficulty.
- [ ] 8. `core/food.ts` (neutral/liked/disliked, boredom halves positives from the 3rd month, Big Appetite ×1.5, Hungry Grub form ×1.5, Hearty Stew +1 week) and `core/items.ts` (unlimited quantities and use; only the optional one-per-week rule and once-per-monster fruits; Stat Sweets with per-stat "from sweets" tracking and the 999 cap; Potential Pearl max A; Tempo Bell min 6; tonics stack across stats and re-use resets them; toys with 5 uses; charms best-per-category). Tests cover every item class and prove there is no hidden limit (100 sweets in one call).
- [ ] 9. `core/songbook.ts`: `canLearn` (universal → anyone; breed sheet → main kit or sub quirk; Signature → pure only; a Chain from a sheet needs no Lv3), `learn` with the 12-cap "which one to forget" result, `forget`, `relearn`, ★ good fit; owned sheets are permanent. Tests for each rule.
- [ ] 10. `core/journey.ts` (M1 scope: weekly check, gains, technique roll; Trial, mentor bond and sale months wait for M5). Tests: the §11 reference table by exact enumeration of `rnd(0..29)`, plus the A/B and E/E variants.
- [ ] 11. `save/schema.ts` + `save/migrate.ts`: valibot v1 schema, `SAVE_VERSION = 1`, `migrate()` skeleton, `validateSave()` that clamps and never throws. Tests: round trip, garbage input gives a friendly error, out-of-range values are clamped.
- [ ] 12. `core/sim/lifeSim.ts`: whole-life simulator with the §26 care policies (Great / Good / OK / Neglect; money ignored) returning weeks lived, lifespan at birth, yearly stat totals, outcome counts and breakdowns.
- [ ] 13. Sim tests (§26, ≥ 40 seeds each): life lived per policy, Good-care totals for a Steady mostly-C breed and a Late A/B breed, Good-care outcome rates. Misses are fixed in `tuning.ts` only; a formula that looks wrong is reported and discussed first.
- [ ] 14. `scripts/sim-life.ts` + `npm run sim:life -- <breed> <policy>` (runs on Node 24 directly, no new dependency) printing a readable life.
- [ ] 15. `npm run verify`, update `docs/PROGRESS.md`, commit `M1: core simulation`, push, confirm the deploy, give the owner a plain-language summary of the sim results.

**Phone check:** nothing new on screen. The owner gets a short plain-language summary of the sim test results instead.

## M2: Saves and the Monster Lab (the editor)

**Goal:** create, load, edit, import and export monsters on the phone. This is also our main debug tool.

- [ ] `save/`:
  - IndexedDB (idb-keyval, `wildsong/` key prefix): 3 slots, rotating autosave, localStorage mirror, global Library.
  - `persist()` request; schema validation on every load.
- [ ] Share codes (`WS1-` + deflate-raw + base64url), file export (`.json` download; Web Share `.txt`), file import (`.json` and `.txt`), `#import=` links, QR codes.
- [ ] **Procedural monster art v1** (`art/monster/`):
  - All 9 body plans, the 20 breed briefs, palettes, sub accents, size stages and expressions.
  - Idle animation; respects reduced motion.
- [ ] **Monster Lab** UI: Library, Create, Editor (all sections in GAME_DESIGN §19, including Allow any technique, breed-change handling, and Edit history with Restore), Import, Export, and the optional edited badge.
- [ ] Presets: pure babies for every breed, plus trained presets at E / C / A / S power.
- [ ] Tests: share-code round trip, schema validation (bad input never crashes), clamping, migration test scaffold.

**Phone check:**
1. Make a monster from scratch and edit its stats.
2. Export it as a code, delete it, then paste the code back.
3. Download a file and re-import it.
4. Look at all 20 breeds in the presets.

## M3: The ranch loop

**Goal:** raise one monster from birth to old age.

- [ ] New Game flow: names, difficulty, first monster (Market gift or a basic Shrine with phrase generation).
- [ ] Ranch screen:
  - Monster on stage, calendar strip, Wren's report.
  - Action bar, item button (opens the Bag), and "Repeat last week".
- [ ] Train sheet: light and heavy drills, stars, odds by transparency mode.
- [ ] Drill result: vignette, banner, stat changes, praise/scold (swipe to pet, wag button).
- [ ] Rest, requests, monthly food prompt, Shop (multi-buy, Stat Sweets counter), charms.
- [ ] **Items and Songsheets in play:**
  - Bag screen (Use ×1 / ×5 / ×10 / Max), Guild Library (Songsheets), Songbook screen (★ good fit, learn, forget).
  - Monster Card buttons: **Use item · Learn technique · ✏️ Edit**.
  - **Edit before you start** after creating a monster.
- [ ] Monster Card: stats, grades, life bar, condition, techniques, personality.
- [ ] Settings: sound placeholders, text size, reduced motion, transparency mode, speed, export/import, persistence status.
- [ ] Aging: warnings, illness, breakdowns, death or retirement placeholder screen. The full farewell comes in M6.
- [ ] Onboarding: Wren guides the first month.
- [ ] Tests: UI-free integration test "a scripted player raises a monster for 3 in-game years without errors".

**Phone check:**
1. Raise a monster for a few in-game years; try resting, food, praise and scold.
2. Buy 10 Stat Sweets and feed them all at once.
3. Buy a Songsheet and teach it.
4. Edit your monster from its card, then keep playing.
5. Check that saves survive closing the app.

## M4: Battles

**Goal:** fun, fair, readable fights, played manually or automatically.

- [ ] `core/battle/`:
  - Engine (30 Hz fixed step, pure and deterministic), formulas (GAME_DESIGN §12.5), ranges, movement, dash, push, guts.
  - Distraction, specials, traits, effects, end conditions.
- [ ] `core/battle/ai.ts`: personalities, the use-rate model, band targeting, push and dash, rookie guts reserve.
- [ ] Battle screen (SVG/DOM):
  - Arena with the range ruler, HP and guts bars, technique columns, thumb pads, Assist.
  - Auto toggle, speed ×1/×2/×4, pause and forfeit, haptics, reduced motion.
  - Animations: lunge, projectiles, hit flash, crit, KO, victory.
- [ ] **Versus** mode and **Battle Lab** (Web Worker) inside the Monster Lab.
- [ ] Tests:
  - Formula reference tables.
  - Determinism and replay (same seed and inputs → same log).
  - 1,000-seed fuzz test (no NaN, no negative HP, no stuck states).
  - **Balance tests** (GAME_DESIGN §26). Tune `tuning.ts`, technique values or traits until they pass.
- [ ] Performance: steady 60 fps on a mid-range phone. No layout thrash; animate transforms only.

**Phone check:**
1. Fight a CPU monster manually and on Auto.
2. Try every range, dash, push, ×2 speed and Skip.
3. Run a 500-battle Battle Lab between two presets.

## M5: Tournaments, ranks and Journeys

- [ ] Calendar of cups (CONTENT §9), entry rules, formats, points and tiebreaks, prizes (purses **and item prizes**, GAME_DESIGN §13), KO withdrawal, after-effects, fame.
- [ ] NPC generator (GAME_DESIGN §13), rival breeders and habits (CONTENT §10); Corin Hale scales with your monster.
- [ ] Promotion, breeder ranks 1–10, Crowns, Legend Cup, credits at rank 10, Hall of Fame.
- [ ] Tournament entry screen, Results screen, Guild screen.
- [ ] **Journeys:**
  - Mentor's Ledger with requirements and chance tiers.
  - Weekly checks, gains, the one-technique roll, mastery levels, Chains, mentor bond, Trial battle, sale months.
- [ ] Signature-technique scene for pure breeds at Prime.
- [ ] Tests: tournament scheduling over 10 years, points and tiebreaks, Journey reference table, NPC stat bands per grade.

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
- [ ] Battle matrix for all 20 breeds at totals 1,000, 2,000 and 3,000; fix any matchup outside 30–70%.
- [ ] Optional Playwright smoke test (Pixel and iPhone emulation): new game → train → battle → save → reload. It needs Windows 11; skip it if unsupported.
- [ ] Bug bash from the owner's notes; final README (how to play, install, back up) and CREDITS.
- [ ] Tag `v1.0.0`.

**Phone check:** a full playtest session; export a backup.

## LATER (after v1.0)

Sketch Stone (draw-to-seed) · local 2-player Versus · optional coach mini-games for drills · a second trainee stall · online friend leagues (would need a backend) · cloud sync · localization.
