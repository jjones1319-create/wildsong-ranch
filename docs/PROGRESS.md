# Progress log

One entry per milestone: what was done, what comes next, and known issues. Newest first.

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
