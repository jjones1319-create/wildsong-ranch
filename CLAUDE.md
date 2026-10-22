# Wildsong Ranch: instructions for Claude

An **original**, phone-first monster-raising game: raise, train and battle monsters born from phrases. It's an installable web app (PWA) hosted on GitHub Pages at `https://<user>.github.io/wildsong-ranch/`. It is inspired by how the classic 1997–2003 raising sims *played*; everything else is ours.

**Read before working:** `docs/BUILD_PLAN.md` (the current milestone), `docs/GAME_DESIGN.md` (rules and formulas), `docs/CONTENT.md` (names and data). `docs/RESEARCH_NOTES.md` is background only.

## The owner
- Not a programmer. Explain in plain words, give exact click-by-click steps when you need them, and never ask them to edit code.
- They test on their phone after every milestone. End each milestone with a short "Try this on your phone" checklist.
- Ask before anything that costs money, publishes something new, deletes data, or changes a design rule.
- **The owner's must-haves:**
  - They can **edit any monster they own at any time** (Monster Card → ✏️ Edit).
  - A Pokémon-style item layer: **unlimited item use**, **Songsheets** that teach techniques, **Stat Sweets** that add stats.
  - Never add hidden limits to these.

## Golden rules (IMPORTANT)
1. **Originality.**
   - Never use names, characters, monster designs, art, sprites, music, sound effects, UI text, logos or data from Monster Rancher / Monster Farm (Koei Tecmo) or any other franchise (Pokémon, Digimon, Dragon Quest…).
   - No series terms such as "errantry", "Rancher" or the original breed and item names, and no other games' item terms either (e.g. "TM", "HM", "Rare Candy", vitamin names).
   - No ripped or extracted game data.
   - If a design or name starts to resemble something famous, change it.
   - Art and sound are generated in code or are CC0. Log every external asset in `CREDITS.md`.
   - Keep the disclaimer in Credits and the README: *"Unofficial fan-made game inspired by classic monster-raising sims. Not affiliated with or endorsed by Koei Tecmo. Monster Rancher is a trademark of KOEI TECMO GAMES CO., LTD."*
2. **Phone first.**
   - Portrait 360–430 px wide, tap targets ≥ 44 px, thumb-reachable controls, safe-area insets, `100dvh`.
   - No hover-only UI, and every animation is skippable.
   - Must work in iOS Safari (16.4+) and Android Chrome, including when installed to the Home Screen.
3. **Deterministic, pure core.**
   - `src/core/` has no DOM, no `Math.random`, no `Date.now`, and no `Math.sin`/`Math.exp` in rules.
   - Use the injected RNG (`core/rng.ts`, state saved in the save file).
   - `Math.pow` is allowed only as GAME_DESIGN §12.5 describes.
   - Prefer integer math.
4. **All tuning numbers live in `src/data/tuning.ts`.** No magic numbers in logic.
5. **Saves are sacred.**
   - Any schema change bumps `SAVE_VERSION` and adds a migration plus a test.
   - Validate and clamp everything that's loaded or imported, and never crash on bad data.
   - Storage keys are prefixed `wildsong/`.

## Tech stack (keep it; ask before adding dependencies)
- **Build and language:** Vite (current major) + TypeScript (the version the `preact-ts` template installs) + **Preact 10** + `@preact/signals`.
- **Battle rendering:** SVG/DOM with the Web Animations API (transforms and opacity only).
- **Libraries:** `idb-keyval` (saves), `valibot` (validation), `vite-plugin-pwa` (`registerType: 'prompt'`), `zzfx` (sound), `qrcode`.
- **Tests:** Vitest. Playwright only in M9, and only if the machine supports it.
- **Node:** 24 LTS or newer; npm ≥ 11, so the lockfile works on GitHub's Linux runners.

## Commands
- `npm run dev`: local dev at http://localhost:5173/wildsong-ranch/. Add `-- --host` to test on a phone over Wi-Fi; service workers and storage persistence won't work over plain LAN http.
- `npm test` (Vitest) · `npm run typecheck` · `npm run build` · `npm run preview`
- `npm run verify` = typecheck + test + build. **Run it before every commit.**
- `npm run sim:life -- <breed> <policy>`: prints a simulated life (dev tool, from M1).

## Architecture
```
src/
  core/      pure rules: rng, hash, calendar, monster, training, aging, food, items, journey,
             tournament, npc, fusion, shrine, expedition, events, battle/{engine,formulas,ai,specials}
  data/      tuning.ts (ALL numbers) · breeds · techniques · drills · foods · items · calendar ·
             journeys · expeditions · rivals · secrets (hashed) · text/ (all player-facing strings)
  save/      db (idb-keyval) · schema (valibot) · migrate · exportImport · shareCode
  art/       monster/ (bodyPlans, parts, palettes, expressions, render) · backgrounds · icons
  audio/     sfx · music
  ui/        app shell, screens/, components/ (Preact)
  workers/   battleLab.worker.ts
docs/        design docs + PROGRESS.md (+ BALANCE_REPORT.md in M9)
.github/workflows/deploy.yml
```
- UI reads state from signals and calls core functions; core never imports UI.
- Screens are chosen by app state and mirrored to the URL hash. **Never use path routing** (GitHub Pages can't serve it).
- Build asset URLs from `import.meta.env.BASE_URL`, never hard-coded `/`.

## Coding conventions
- TypeScript `strict`. Small, named, pure functions in core; one module per system.
- Content data mirrors `docs/CONTENT.md` exactly. If CONTENT changes, regenerate the data and run the data tests.
- Every formula gets a unit test, and the reference tables in GAME_DESIGN become test cases.
- Balance targets (GAME_DESIGN §26) are seeded sim tests. If they fail, tune `tuning.ts`, technique values or traits; **don't** change formulas without asking.
- Player-facing text lives in `src/data/text/`, in Wren's warm, simple voice.

## Workflow
1. **Start of a milestone:** use plan mode. Re-read its BUILD_PLAN section and the GAME_DESIGN/CONTENT sections it touches, and add a detailed task list under the milestone.
2. **Build** in small steps with tests. Use subagents for broad searches or reviews to keep context lean.
3. `npm run verify` until it's green, then update `docs/PROGRESS.md` (done / next / known issues).
4. **Commit** `M<n>: <summary>` and push `main`, which deploys via GitHub Actions. Check the deploy succeeded (`gh run list` or the Actions tab).
5. Give the owner the phone checklist and **stop**. Wait for their feedback before the next milestone.
6. **Design changes:** if something in the docs is unclear or seems wrong, propose the change, ask, then update the doc and the code together.

## Gotchas
- **Vite `base`:** must be `'/wildsong-ranch/'` and must match the repo name. The PWA manifest `id`, `scope` and `start_url` must match too.
- **Shared origin:** all GitHub Pages sites on an account share one origin, so always prefix storage keys.
- **iOS:**
  - No install prompt (show our own help card).
  - Audio must start on a user gesture (`pointerup`).
  - No `navigator.vibrate`.
  - A Safari tab and the installed Home Screen app have **separate storage**; use export/import to move saves.
- **Web Share** can't share `.json` files in Chromium. Share as `.txt`, download as `.json`, and accept both on import.
- **Windows:** keep `.gitattributes` with `eol=lf`, and use npm ≥ 11 when regenerating `package-lock.json`.
- **Updates:** never auto-reload mid-battle. Show the update toast only on the ranch screen.
- **When compacting context,** keep the current milestone, changed files, failing tests and open questions.
