# Wildsong Ranch

*Every monster is born from a song.*

Type any song title, name or phrase at the Shrine of Echoes and a singing stone wakes the monster that was listening for it. Raise it week by week: train it, feed it, praise it (or scold it), take it on Journeys and expeditions, and battle your way from rookie cups to the four Crowns of Wildsong Vale. When its long life ends, its Heartstone and its lineage carry on.

**Play:** https://jjones1319-create.github.io/wildsong-ranch/

Wildsong Ranch is a free, original, phone-first game. It runs in the browser, works offline once installed, and keeps your ranch on your own phone. Version 1.0.

## How to play

1. **New Game.** Pick a difficulty (Gentle is kind; Classic is the old-school challenge), accept the gift monster or sing one up at the Shrine, and name it.
2. **One week at a time.** Every week you choose one thing: a drill (light or heavy), a rest, a play, a Journey, a cup, an expedition or a trip to Town. On the first week of each month you also pick the month's food.
3. **Watch the bars.** Fatigue and stress climb with training. Rest before fatigue reaches the red, use care items for stress, and answer your monster's requests. Neglect leads to illness, breakdowns and a shorter life.
4. **Praise and scold.** After a drill you can praise or scold. Praise a good effort; scold cheating. Both shape nature and loyalty.
5. **Cups.** Town's Guild lists the week's cups. Win an Official to raise your grade, then chase the four Crowns and the Legend Cup. Battles are tap-to-fire with range bands; Auto mode fights for you with a style you choose (Balanced, Aggressive or Defensive), and "Show battle thinking" in Settings puts a little icon over each monster that says what it is planning.
6. **Town.** Basil's Shop (food, care items, Stat Sweets, toys), the Guild Library (Songsheets that teach techniques), Dr. Pell's Lab (the Freezer, fusion, the Memorial, Heartstones), the Shrine of Echoes (new monsters, Sleeping Stones, the Encyclopedia), the Journal and Odd Jobs.
7. **Journeys and expeditions.** Four-week trips with a mentor teach techniques; Tomas's letters invite you to explore the valley's sites for treasure and the rarer breeds.
8. **The planner.** Queue up to eight weeks of drills and rests and let them run; it stops when something needs you.
9. **Farewell.** When a life ends, the monster joins the Memorial and leaves a Heartstone. Fuse, thaw or sing up the next one and carry the lineage on.

**Power up any time.** Teach new attacks with **Songsheets** and boost stats with **Stat Sweets**; use as many as you like. The **Monster Lab** lets you create, load and edit any monster you own, including the one you're raising, share monsters by code or QR, and pit any two against each other in Versus or the Battle Lab.

## Install it on your phone

- **iPhone or iPad (Safari):** open the link, tap **Share** (the square with the arrow), then **Add to Home Screen**.
- **Android (Chrome):** open the link, tap the **⋮** menu, then **Install app** (or **Add to Home screen**).

The installed app runs full screen and offline. Note that the Safari tab and the installed app keep **separate saves**: move a ranch between them with a backup (below).

## Back up and restore

Your ranch lives only on your phone, so back it up now and then (the game reminds you).

- **Save a backup:** Settings → **Share save…** opens the share sheet on a phone (save the file to Files, Drive or Notes, or send it to yourself); **Download save (.json)** saves a file on a computer. The ranch's backup card does the same with one tap.
- **Restore:** Settings → **Import a save…** and pick the file (or paste its text). Backups are plain text (`.txt` or `.json`); both import.
- **Share a monster:** Monster Card → **Share…** gives a code and a QR that another player can import into their Lab.

## For developers

```
npm install
npm run dev          # http://localhost:5173/wildsong-ranch/  (add -- --host to test on a phone)
npm run verify       # typecheck + unit tests + build
npm run e2e          # Playwright smoke test on phone emulation (needs Google Chrome installed)
npm run sim:life -- puddlepup good     # print one simulated life
npm run sim:balance                    # the §26 balance matrices → docs/BALANCE_REPORT.md
```

Built with Vite, TypeScript, Preact and @preact/signals; procedural SVG art; ZzFX sound and music composed in code; an installable, offline-capable web app on GitHub Pages. The core rules are pure, deterministic TypeScript with a seeded RNG, and every tuning number lives in `src/data/tuning.ts`.

The project docs are in `docs/`: the game design, the content tables, the build plan, the balance report and the research notes. `CLAUDE.md` holds the standing instructions for the AI coding assistant that builds it.

## Disclaimer

Unofficial fan-made game inspired by classic monster-raising sims. Not affiliated with or endorsed by Koei Tecmo. Monster Rancher is a trademark of KOEI TECMO GAMES CO., LTD. All monsters, characters, names, art, music and text in this project are original.
