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
- **Libraries:** `idb-keyval` (saves), `valibot` (validation), `vite-plugin-pwa` (`registerType: 'prompt'`), `qrcode`, `pixi.js` + `pixi-filters` (the effects layer), `three` (the 3D monsters, in one lazy chunk; Art 2.0). Sound has **no runtime dependency**: our own engine on Web Audio (`src/audio/`). Dev only: `ffmpeg-static` (encodes the samples), `@gltf-transform/cli` (shrinks the models).
- **3D monsters (Art 2.0, `docs/ART_2_PLAN.md`):** Blender builds each breed's model, rig, clips and face sheet (`tools/blender/monsters/`); the game only displays them (`src/art3d/`, loaded with `import('../art3d/art3d.ts')` so the main chunk never imports three). Only `src/art3d/` imports `three`. The Classic SVG monsters stay as the fallback and as Settings → Graphics → Monsters: Classic.
- **Tests:** Vitest. Playwright only in M9, and only if the machine supports it.
- **Node:** 24 LTS or newer; npm ≥ 11, so the lockfile works on GitHub's Linux runners.

## Tools on the owner's PC
- **Blender is installed** (Windows). Use it **headless only**: `blender -b --python <script.py>` (find the exe under `C:\Program Files\Blender Foundation\Blender <ver>\blender.exe`; check `blender --version` first and pin scripts to that API). Never ask the owner to click around inside Blender.
- Good uses: baking fire / smoke / water flipbooks (Mantaflow) to sprite sheets when a shader isn't enough; rendering stylized props, rocks and scene pieces to PNG with alpha; mask passes for recoloring. Keep baked assets small (WebP/AVIF, ≤ 1 MB each, lazy-loaded) and log them in `CREDITS.md` as our own renders.
- **3D monsters are built here** (Art 2.0, from P1): `npm run art:monster -- <breed>` runs `tools/blender/monsters/build.py` headless (recipes in `breeds/`, rigs and clips in `plans/`, shared helpers in `tools/blender/lib/`), then `tools/art/optimize.ts` writes `public/models/monsters/<look>.glb` + `.json` within the §3.6 budgets. Always look at the Blender sheets in `tools/blender/out/<look>/review/` and the in-game sheets from `npm run art:review -- <look>` (in `art-review/`, gitignored) before calling a monster done; Claude can't see the phone, so the sheets and the owner's notes decide.
- Scripts live in `tools/blender/`; scene bakes go to `public/baked/`, models to `public/models/`. Always render a contact-sheet PNG and look at it before using a bake. Long Blender runs go in the background with a log file.

## Audio (Sound 2.0; spec `docs/SOUND_UPGRADE.md`)
- **Originality applies to music too:** every melody, chord progression and rhythm is written for this game. Never quote or paraphrase another work, and never name another game or its music in code or docs; describe a style only in musical words (instruments, modes, tempos). The reference games' names must not appear in any committed file (a Vitest lint checks).
- **Only `src/audio/engine/` touches Web Audio**, and only `engine/nodes.ts` creates oscillators, PeriodicWaves and compressors (no square or saw waves, no WaveShaper, no bit-crush; a lint test enforces it). `src/core` never imports audio. Audio randomness comes from `engine/rng.ts`, never the game RNG or `Math.random`.
- **Songs** are one TypeScript file each in `src/audio/music/songs/` (ABC notation for the notes, TypeScript for parts, generators, percussion, form, weather and stems). Run the checker after composing: `npm run audio:analyze` (prints every song's key, tempo, length, step share and the checker's errors). The checker rules are SOUND_UPGRADE §6.7.
- **Samples:** `npm run audio:samples` rebuilds `public/audio/` from the CC0 libraries pinned in `tools/audio/sources.ts` (sparse clones into `tools/audio/.cache/`, gitignored). It needs ffmpeg: one on PATH, or the `ffmpeg-static` devDependency. If npm blocked its install script, run `npm approve-scripts ffmpeg-static` and `npm rebuild ffmpeg-static`. Commit the processed `.ogg` files and the manifest, never the raw downloads. Packs are computed from `recipes/usage.ts`; the budgets are §2.
- **Checks:** `npm run audio:check` renders every piece offline through the real engine (Playwright + the installed Chrome) and gates the §14.3 targets; `-- --calibrate` writes `src/audio/levels.json`; `-- --quick` renders one item per group. `npm run audio:review` writes `audio-review/` (gitignored) with listening files and an HTML report for the owner. `npm run check:build` (part of `verify`) keeps the engine chunk ≤ 45 KB gzipped and the samples precached.
- **Claude can't hear.** Compose with the checker, verify with `audio:check`, and end every sound stage with the Sound Lab (`#lab/sound`) and PROGRESS lines saying what each piece should sound like; the owner's notes decide.

## Commands
- `npm run dev`: local dev at http://localhost:5173/wildsong-ranch/. Add `-- --host` to test on a phone over Wi-Fi; service workers and storage persistence won't work over plain LAN http.
- `npm test` (Vitest) · `npm run typecheck` · `npm run build` · `npm run preview`
- `npm run verify` = typecheck + test + build + `check:build` (the precache list and the audio chunk budgets). **Run it before every commit.**
- `npm run e2e`: the Playwright specs against the built app in the installed Chrome (kill any leftover preview on port 4173 first).
- `npm run sim:life -- <breed> <policy>`: prints a simulated life (dev tool, from M1).
- Sound (see the Audio section): `npm run audio:samples` · `npm run audio:analyze` · `npm run audio:check [-- --quick | --calibrate]` · `npm run audio:review`.
- Art 2.0: `npm run art:monster -- <breed> [--quick] [--stages model,clips,export,review]` (Blender build + optimise) · `npm run art:optimize -- <look>` · `npm run art:review -- <look> [--no-build]` (in-game sheets in `art-review/`) · `npm run art:portraits` (the precached breed pictures in `public/portraits/`).

## Architecture
```
src/
  core/      pure rules: rng, hash, calendar, monster, training, aging, food, items, journey,
             tournament, npc, fusion, shrine, expedition, events, battle/{engine,formulas,ai,specials}
  data/      tuning.ts (ALL numbers) · breeds · techniques · drills · foods · items · calendar ·
             journeys · expeditions · rivals · secrets (hashed) · text/ (all player-facing strings)
  save/      db (idb-keyval) · schema (valibot) · migrate · exportImport · shareCode
  art/       monster/ (bodyPlans, parts, palettes, expressions, render) · backgrounds · icons · models (which breeds have a 3D look)
  art3d/     the 3D monsters (Art 2.0): Stage3D (one renderer, hosts come and go) · actor · materials (cel shader,
             outline, face) · loader · faceCells · springs · arenaCamera · battleClips · arena3d; only this folder imports three
  audio/     player (the UI's API) · director (what plays where, pure) · runtime · engine/ (Web Audio: the only
             place that touches it) · music/ (ABC parser, generators, song model, checker, motifs, songs/)
             · recipes/ (instruments, kits, ambience, effects, drills, events, packs) · analysis/ (loudness…)
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
