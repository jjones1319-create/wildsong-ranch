# Credits

Wildsong Ranch is an original game, designed and built with Claude Code. The source code is released under the MIT License (see `LICENSE`).

## Disclaimer

Unofficial fan-made game inspired by classic monster-raising sims. Not affiliated with or endorsed by Koei Tecmo. Monster Rancher is a trademark of KOEI TECMO GAMES CO., LTD.

All monsters, characters, names, art, music, sound and text in this project are original.

## Tools and libraries

- Vite, TypeScript, Preact and @preact/signals (MIT)
- vite-plugin-pwa and Workbox (MIT)
- idb-keyval, valibot, qrcode (MIT)
- The music is composed for this game in ABC notation and played live by our own sequencer (`src/audio/`); every melody, chord progression and rhythm is original. The sound effects and the ambience are built from the CC0 samples below, filtered noise and plain sine and triangle tones.
- PixiJS 8 (MIT) draws the battle effects layer, and pixi-filters (MIT) supplies the shockwave, bloom and RGB-split filters; every particle texture is drawn in code at start-up (V1)
- Vitest (MIT) for the unit and simulation tests; Playwright (Apache-2.0) for the phone-emulation smoke test and the offline audio renders, driving the locally installed Google Chrome
- ffmpeg-static (GPL-licensed FFmpeg binaries, used only as a development tool on the author's PC to encode the samples below to Opus; nothing from it ships in the game)
- Hosted on GitHub Pages

## External assets

The logo (`public/logo.svg`) and every icon generated from it were drawn for this project. The instrument samples and Foley recordings under `public/audio/` come from the CC0 (public domain) libraries below. They were trimmed, level-matched, loop-baked and encoded to Opus by `tools/audio/build-samples.ts` (SOUND_UPGRADE §5.3); `public/audio/manifest.json` records every file's source library.

- **Versilian Community Sample Library (VCSL)** by Versilian Studios and contributors, CC0 1.0. `https://github.com/sgossner/VCSL` at commit `c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e`. Used: ocarina, baroque alto and tenor recorders, folk harp, strumstick, kalimba, marimba, glockenspiel, hand chimes, tubular bells, vibraphone (soft mallets and bowed), frame drum, shaker, tambourine, woodblock, claves, claps, finger cymbals, triangle, mark trees, sleigh bells, timpani, bass drum, darbuka, bongos, cajon, suspended cymbal.
- **Versilian Studios Chamber Orchestra 2 Community Edition (VSCO 2 CE)** by Versilian Studios and contributors, CC0 1.0. `https://github.com/sgossner/VSCO-2-CE` at commit `440300901dfe9275fd84e0b7763af1f8443ae62e`. Used: flute, F horn, violin, viola and cello sections, solo contrabass.
- **Kenney Impact Sounds** by Kenney (kenney.nl), CC0 1.0. `https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip`, SHA-256 `029d734af1582474edf3a694d1b0cebc97c1c152f2f39fa34d4c2bafc5de77f8`. Used: footsteps on grass, wood and stone; wood, soft, plank, mining and punch impacts.
- **Kenney RPG Audio** by Kenney (kenney.nl), CC0 1.0. `https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip`, SHA-256 `6dbeaf8544da958d8f2adcb4a4a4b76c1ade34a05f8ab9edccd327da7375f38b`. Used: cloth, creaks, coins, page flips.

Every external asset added later must be CC0 and listed here with its source and license.
