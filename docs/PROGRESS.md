# Progress log

One entry per milestone: what was done, what comes next, and known issues. Newest first.

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

**Next (M1):** the pure core simulation (RNG, hash, data from CONTENT, monster model, calendar, training, aging, food, items, songbook, journeys, save schema), the reference-table tests, the §26 sim tests and `npm run sim:life`. The detailed task list is in `docs/BUILD_PLAN.md`.

**Known issues**
- The four menu buttons open "coming in M2/M3" placeholder screens by design.
- Commits for this repo use the GitHub no-reply address (repo-local git config) so the owner's work email is not published.
