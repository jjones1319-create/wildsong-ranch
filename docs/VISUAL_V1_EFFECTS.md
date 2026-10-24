# V1: Effects engine and arena staging

The first of five visual milestones (see `docs/VISUAL_UPGRADE_PLAN.md` §0 for the owner's decisions). V1 builds the foundation that V2–V5 draw with: a GPU effects layer, a library of effect primitives, element tags on every technique, the Quality and Intensity settings, and an Effects Lab to try everything on the phone.

**V1 does not change any rules.** The simulation (`src/core`) stays untouched and deterministic. Effects are presentation only and are driven by the events the battle engine already emits.

## 1. Goals

1. A transparent WebGL effects canvas that sits over the arena (and later over drill scenes), positioned in the same world coordinates as the monsters, including the arena camera from M10.
2. ~18 reusable **effect primitives** written in code (no asset files): particles, beams, projectiles, shockwaves, water, fire, lightning, screen effects.
3. An **element tag** on all 294 techniques, so the existing generic attack effects immediately take on their element's color and shape (fire is orange and flickers; ice is pale blue and shatters; water is teal and splashes).
4. **Quality** (Ultra / High / Lite, auto-detected) and **Intensity** (Cozy / Standard / Flashy) settings.
5. An **Effects Lab** screen to fire any primitive at any element, with an fps counter.
6. Performance: 60 fps on a Galaxy S25 Ultra with two monsters, the arena camera and a busy effect; graceful fallback on weaker phones.

## 2. Technology

- **PixiJS 8** (current 8.22.x; `pixi.js` from npm). WebGL2 renderer with automatic WebGPU where available. `backgroundAlpha: 0`, `antialias: false`, `resolution: min(devicePixelRatio, 2)` (Ultra) / 1.5 (High) / 1 (Lite), `autoDensity: true`.
- **Do not** use `@pixi/particle-emitter` (it isn't compatible with Pixi 8). Write our own emitter (~150 lines) on Pixi's `ParticleContainer`, with object pooling.
- `pixi-filters` (the Pixi 8 line) for: displacement (heat haze, water refraction), shockwave, bloom (advanced bloom or a cheap two-pass), RGB split, color matrix. Only when the Quality tier allows filters.
- A few short custom fragment shaders (GLSL, with Pixi's `Filter`/`Shader`): fire haze, water sheet, lightning glow. Keep each under ~60 lines.
- **Bundle:** load the whole `fx` module as a lazy chunk only on screens that use it (battle, Versus, Effects Lab, later drills). Budget: ≤ 150 KB gzipped for the chunk including Pixi. If Pixi's full build is larger, import only the needed sub-modules.
- **No new dependencies beyond `pixi.js` and `pixi-filters`** without asking.
- **Blender (optional, headless):** the owner has Blender installed. If a shader-only `sheet` (waterfall/wave) or `cone` (flame breath) doesn't look good enough on review, bake a short looping flipbook (Mantaflow fire/smoke or a fluid splash, 16–24 frames, WebP sprite sheet ≤ 1 MB) with a script in `tools/blender/` and use it as a particle/sheet texture. Prefer shaders first; bake only where it clearly wins.

## 3. Architecture

```
src/fx/
  FxLayer.ts        Pixi Application lifecycle; mounts a <canvas> over a host element; resize; pause/resume; destroy
  camera.ts         world↔screen mapping; subscribes to the arena camera (M10 ui/battle/camera.ts) so effects move with the view
  rng.ts            a separate seeded PRNG for *visual* randomness (never the core RNG)
  pool.ts           object pools for particles/sprites (no per-frame allocation)
  emitter.ts        the particle emitter (ParticleContainer): shape, rate/burst, lifetime, velocity, gravity, drag, scale/alpha/color curves, blend mode
  textures.ts       procedurally generated textures (soft dot, spark, droplet, shard, ring, streak, smoke puff) drawn once into a small atlas at startup
  elements.ts       per-element style: palette ramp, particle textures, blend mode, sound family, haze/refraction flags
  primitives/       one file per primitive (see §4); each is a pure factory: (layer, params) → handle {update, stop, dispose}
  quality.ts        tier detection + budgets; Intensity multipliers
  bus.ts            FxEvent types + subscribe; battle store publishes, fx layer consumes
  index.ts          lazy entry
src/ui/screens/lab/LabEffects.tsx   the Effects Lab (dev + owner testing)
```

- **Coordinates:** everything is placed in **arena world units** (the same 1,200-unit arena, x from −600 to 600, y = 0 at the ground). `camera.ts` converts to canvas pixels every frame using the current camera zoom/offset so effects stay glued to the monsters. Effects that are screen-space (flash, shake, impact frame, vignette) are flagged `screenSpace: true` and ignore the camera.
- **Monsters stay in the DOM** (SVG rigs). The Pixi canvas sits above the arena background and *below* the floating damage numbers and HUD. Z-order: background → monsters (DOM) → fx canvas (`pointer-events: none`) → HUD (DOM). Effects that must appear *behind* a monster (ground dust, a wave rising behind) use a second, lower Pixi canvas or a separate container with a mask; prefer one canvas above and accept that effects overlay the monsters for now. V3 may move monster rendering so layering gets simpler; design the layer API so that's possible.
- **Events:** `bus.ts` defines `FxEvent = { kind: 'fire'|'travel'|'hit'|'miss'|'crit'|'ko'|'special'|'push'|'dash'|'distract'|'wither'|'heal', side, techId?, element, from, to, strength }`. The battle store maps engine events to FxEvents (it already maps them to the current generic effects). V1 renders the *default recipe per element* for each event; V2 replaces it with per-technique recipes.
- **Timing:** effects advance on `requestAnimationFrame` with a clamped delta; they respect battle playback speed (×1/×2/×4) and pause with the battle. Skip = instantly dispose everything.
- **Lifecycle:** create the layer when a screen mounts, destroy on unmount; release GPU textures; handle `visibilitychange` (pause) and WebGL context loss (rebuild silently).

## 4. Effect primitives (all written in code, all parameterized by element)

| # | Primitive | What it is | Key params |
|---|---|---|---|
| 1 | `burst` | One-shot radial particle burst (sparks, shards, droplets, petals) | count, speed, spread, gravity, lifetime, texture, ramp |
| 2 | `cone` | Continuous directional emitter (flame breath, water jet, dust) | origin, direction, angle, rate, duration, speed, ramp, haze |
| 3 | `trail` | Ribbon/particle trail following a moving point | width, length, fade |
| 4 | `projectile` | A moving sprite along a straight or arced path with a trail, resolving to `impact` | shape (orb, lance, blade, boulder, feather, note), arc height, speed |
| 5 | `beam` | Instant line from A to B with core + glow + animated noise edge | width, duration, jitter |
| 6 | `ring` | Expanding ring/shockwave with fade; optional ground ellipse perspective | radius, thickness, duration, ground |
| 7 | `impact` | Hit spark: white core flash, radial spikes, debris burst, small ring | strength |
| 8 | `splash` | Water impact: crown of droplets + ripple rings + mist puff | size |
| 9 | `sheet` | Water sheet / waterfall / wave: shader-scrolled noise in a quad with foam band; can be shaped as a rising wave | width, height, speed, foam |
| 10 | `lightning` | Procedural bolt: midpoint-displaced polyline, three-pass glow, 2–3 frame flicker, branch chance | from, to, branches |
| 11 | `haze` | Displacement filter masked to a region (heat distortion, underwater wobble) | strength, region |
| 12 | `glow` | Soft additive aura around a point/monster (charging, specials) | radius, pulse |
| 13 | `debris` | Chunky physics particles with bounce (rocks, ice chunks, coins) | count, texture |
| 14 | `mist` | Slow large translucent puffs (fog, steam, smoke) | density, drift |
| 15 | `flash` | Screen-space full flash with alpha cap (≤ 0.3) and 3 Hz rate cap | color, alpha, ms |
| 16 | `shake` | Camera shake: decaying random offset applied to the arena world transform (DOM monsters and fx canvas together) | amplitude, ms |
| 17 | `hitstop` | Freeze both monsters' animation clocks and the fx layer for N ms (presentation only; the simulation keeps its own time) | ms |
| 18 | `impactFrame` | 1–2 frames of two-tone/inverted overlay on the arena (color-matrix filter) | palette |

Each primitive has a **default recipe per element** in `elements.ts` (e.g. `cone` with Fire = orange→yellow→smoke ramp, additive blend, haze on; with Water = teal droplets, normal blend, splash on end; with Ice = pale blue shards, slow fade, frost mist; with Lightning = beam + branches + flash; with Wind = white arcs + leaves; with Earth = brown debris + dust ring + heavier shake; with Nature = petals/leaves + green glow; with Light = white-gold motes + rays; with Dark = violet smoke + inward pull; with Sound = concentric rings + note sprites; with Physical = white sparks + dust).

## 5. Element tags on techniques (data change)

Add `element` to every technique in `src/data/techniques.ts` and a new **Element** column to the technique tables in `docs/CONTENT.md` §3 and `docs/NEW_MONSTERS.md` §4.

**Elements (11):** Fire, Water, Ice, Lightning, Wind, Earth, Nature, Light, Dark, Sound, Physical.

**How to assign (in this order):**
1. **Keyword rules on the technique name** (first match wins):
   - Fire: fire, flame, ember, cinder, blaze, furnace, pyre, inferno, kindled, smoulder, sun, solar, hearth, torrent (Hearthfire), bonfire, wildfire, flare (except Crest Flare → Light)
   - Water: water, splash, wave, tide, geyser, rain, drizzle, puddle, bubble, soggy, bog, swamp, pool, drench, riptide, kingtide, barnacle, moat, downpour, sea
   - Ice: ice, icicle, frost, snow, glacier, blizzard, polar, chill, hail, crystal lance
   - Lightning: bolt (Zipwisp/Nimbusheep only), spark (Zipwisp, Pluckrex-no), static, zap, crackle, arc, volt, lightning, overcharge, feedback
   - Wind: wind, gale, gust, squall, tempest, storm (non-electric), breeze, whirl, cyclone, tornado, downdraft, slipstream, stride (Lightning Stride → Wind)
   - Earth: stone, rock, boulder, gravel, quake, landslide, crag, geode, crystal (Grumblestone), pebble, bedrock, mountain, avalanche, cobble, knuckle knock, mountainfall, rockfall
   - Nature: petal, bloom, blossom, seed, thorn, leaf, bramble, moss, silk, vine, cocoon, sneeze (Seed Sneeze), lily
   - Light: light, glow, beam, prism, glimmer, star, halo, dawn, moon, lantern, gleam, flash, ray, reflection, mirror, glint, shard (Mirrorkin), lens, wish, festival, sunrise (Pluckrex's Sunrise Roar → Light), constellation, supernova, comet
   - Dark: shadow, dusk, gloom, ash, wraith, phantom, soul, ink, venom, poison, hush, wail, spooky, mournful, siphon, eclipse, night, twilight, drowsy, hypno, lullaby, sleepy, trickster, mocking, fool's gold, snicker
   - Sound: every **universal** technique (CONTENT §3.1) is Sound unless its name clearly says otherwise (Harmony Mend → Light, Resonance Drain → Dark); also roar, howl, yip, croak, bleat, chime, hum, whistle, drum, cymbal, note, song, wail (already Dark), crier
2. **Otherwise the breed default:** Puddlepup Water · Tumblefox Fire · Cobblemaw Earth · Moatshell Earth · Wishlume Light · Quillion Physical · Cinderlynx Fire · Bloatoad Water · Coilfang Dark · Nimbusheep Water · Galeheron Wind · Nibblegrub Nature · Velvesper Dark · Ashwraith Fire · Zipwisp Lightning · Mirrorkin Light · Gearhoot Light (INT) / Physical (POW) · Reefclaw Water · Lootlid Light (INT) / Physical (POW) · Aurelwyrm Fire (INT) / Physical (POW) · Hearthwing Fire · Grumblestone Earth · Pluckrex Physical · Paladove Light · Starhowl Light · Petalphant Nature · Scrollopus Dark · Gloomgrin Dark · Rammerjack Physical · Frostlance Ice.
3. **Plain melee names** (bite, jab, swipe, slam, punch, kick, bump, poke, thrust, claw, tackle, headbutt, bonk, stomp, shove) are **Physical** regardless of breed, unless rule 1 matched.

Claude generates the full table, prints it for the owner, and the owner can correct any row. A data test checks every technique has an element and that the table matches the data.

**Immediate visible payoff in V1:** the existing generic effects (lunge, shot, hit, crit, KO, special) are re-skinned per element using the default recipes. Attacks already look different by element before V2's per-technique recipes.

## 6. Quality and Intensity settings

**Quality** (Settings → Graphics → Quality: Auto / Ultra / High / Lite):

| | Ultra | High | Lite |
|---|---|---|---|
| Max live particles | 2,500 | 1,200 | 400 |
| Filters (haze, bloom, shockwave, RGB split) | all | bloom + shockwave only | none |
| Canvas resolution | min(DPR, 2) | min(DPR, 1.5) | 1 |
| Lightning passes | 3 | 2 | 1 |
| Target | S25 Ultra class | mid-range | low-end / battery saver |

- **Auto-detect:** start at Ultra; measure the average frame time over the first ~90 frames of the first battle; drop one tier if it exceeds 18 ms, two if it exceeds 28 ms. Also start at High if `navigator.deviceMemory < 4` or `hardwareConcurrency < 6`, and at Lite under the browser's data-saver / `prefers-reduced-data`. Remember the chosen tier.
- **Idle:** render at 30 fps when nothing is animating; pause entirely when the app is hidden.

**Intensity** (Settings → Graphics → Intensity: Cozy / Standard / Flashy):

| | Cozy | Standard | Flashy |
|---|---|---|---|
| Shake amplitude | 0 | 4 px | 8 px |
| Hit-stop | 0 | 60 ms | 120 ms |
| Impact frames | off | crits only | all heavy hits |
| Screen flash alpha | 0 | 0.2 | 0.3 (cap) |
| Bloom | off | low | high |
| Particle count multiplier | 0.6 | 1.0 | 1.4 (within the Quality cap) |

- **Reduced motion** forces Cozy and disables shake, flash and impact frames regardless of the setting.
- **Photosensitivity:** no more than 3 flashes per second anywhere; flash alpha never above 0.3.

## 7. Effects Lab (Monster Lab → Effects)

- A full-screen arena mock with two preset monsters (selectable) and the real arena camera.
- Rows of buttons: each primitive × each element, plus "Random attack", "Combo (fire → impact → shake)", and a "Stress test" that fires 20 effects at once.
- Live fps counter, particle count, current Quality/Intensity, with toggles to change them.
- A "Record 3 s" button that captures a frame sequence to PNGs in dev mode (Playwright uses the same screen for review).

## 8. Performance budget and verification

- 60 fps on a Galaxy S25 Ultra at Ultra with two monsters + camera + any single primitive; ≥ 45 fps during the stress test.
- Zero per-frame allocations in the steady state (pools); no GC spikes; GPU memory for textures < 16 MB.
- Battery/heat: idle 30 fps; pause when hidden.
- The `fx` chunk only loads on screens that need it; the title and ranch screens' load time is unchanged.

**Review step (mandatory, as in M2):** run Playwright against the Effects Lab on the Pixel 7 profile, capture a contact sheet of every primitive at every element (18 × 11), look at the images, and fix anything weak, muddy or unreadable before shipping. Attach the contact sheet to `docs/fx-review/`.

## 9. Tests

- Pure tests (Vitest, no WebGL): emitter math (positions, lifetimes, curves), pooling never grows after warm-up, element assignment rules (every technique has an element; universal techniques are Sound unless listed), quality tier selection from fake frame timings, intensity multipliers, 3 Hz flash cap, event mapping (each engine event produces the expected FxEvent).
- The simulation's existing determinism tests must still pass unchanged (fx must never touch core).
- Playwright (optional, `npm run e2e`): Effects Lab opens, fires a combo, no console errors, fps counter > 0; one screenshot per element.

## 10. Docs to update

- GAME_DESIGN §22 (effects layer, elements, Quality/Intensity), §24 (photosensitivity), §21 (Settings → Graphics; Effects Lab).
- CONTENT §3 / NEW_MONSTERS §4: Element column; a short "Elements" subsection describing each element's look.
- BUILD_PLAN: add V1–V5 as milestones (from `VISUAL_UPGRADE_PLAN.md`).
- PROGRESS.md entry; version bump (minor); CREDITS (PixiJS, pixi-filters licenses).

## 11. Try this on your phone

1. Monster Lab → Effects. Tap through the primitives: fire cone with heat haze, water sheet with splash, lightning with flash, shockwave, debris.
2. Switch Quality to Lite and back; switch Intensity Cozy → Flashy and fire the combo.
3. Run the stress test and read the fps counter.
4. Start a Versus battle: attacks now have element colors and shapes (fire orange and flickering, ice pale and shattering, water splashing).
5. Turn on reduced motion in Android settings and confirm shake/flash are gone.
