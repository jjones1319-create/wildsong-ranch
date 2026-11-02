# Battle 3D: the lock-on duel

**Status:** design and test build, Nov 2, 2026.
- **The owner asked for it.** Battles become a 2-D lock-on duel in a 3D arena.
- **The current battle stays the fallback** until the owner approves. It is the engine's **line** mode, and it replays bit for bit: the golden record holds.
- **The test build** is one finished-quality slice:
  - the Breeders' Guild arena;
  - Puddlepup (Art 2.1 Ultra) against Songheart Puddlepup;
  - an entrance cutscene and the cameras.

**Read with:**
- GAME_DESIGN §12 (the battle) and §12.10 (AI 2.0);
- ART_2_PLAN §7.3 (battles in 3D);
- ART_2_DETAIL (the Ultra look, the renderer, the budgets).

## 1. In short
- **The monsters always face each other.** Forward and back change the gap **exactly as today**. Left and right **strafe**, circling the opponent at the current distance.
- **Everything else stays:**
  - the four range bands, now measured as the straight-line gap;
  - guts, techniques, and the hit and damage formulas;
  - 60-second matches;
  - Fight, Auto (take over at any time) and Skip, at ×1, ×2 and ×4;
  - a deterministic fixed-step engine with tick-stamped inputs (`runBattle` with `mode: 'duel'`).
- **New:**
  - every technique **telegraphs during a wind-up**;
  - a quick **sidestep** timed in the wind-up makes a straight-line technique harder to land, and carries the defender out of its path if there is time;
  - **wide sweeps** can't be sidestepped;
  - the CPU and Auto circle and sidestep too, with timing set by their tier and SPD.
- **On the phone:**
  - a left-thumb stick for movement (a quick flick sideways is a sidestep);
  - the technique buttons on the right, as now;
  - one button switches between the **side-on** camera (best for reading distance; the default on Auto) and **behind your monster** (best for steering and sidestepping);
  - cinematic cuts for Specials, Signatures and KOs.

## 2. The ring and movement
- **The ring:** a disc of radius `arena.halfWidth` (600 units; 1 unit = 1 cm in the 3D arena, so the fence is at 6 m). Body centres stay within 520, the same wall as the line. Bodies have radius 80 and never overlap.
- **The gap:** the straight-line distance between the two centres, minus both radii. The bands are unchanged: Close 0–159, Near 160–309, Mid 310–479, Far 480–679.
- **Start:** the same positions, 230 units either side of the centre on one line, so the gap is 300 (Near).
- **Forward and back** run along the line between the fighters at the walking speed of §12.3 (backing away ×0.85), so they change the gap exactly as on the line. **Dash** and **push** are unchanged too.
- **Strafing** moves sideways at **80% of walking speed** (`BATTLE.duel.strafePct`). After each step the distance is set back to what it was, so a strafe circles the opponent and never changes the gap or the band.
- **Knockback and push** slide the target 250 units straight away from the attacker, stopped by the ring.
- **Corners:** "cornered" means the ring's edge is less than 120 units behind the fighter (§12.10's `cornerUnits`). Circling is the new way out: you can slip round to open ground instead of shoving.
- **Geometry** (`src/core/battle/geometry.ts`):
  - plain square roots and divisions, no trigonometry;
  - every position rounds back to whole centi-units, so a duel replays exactly on every phone;
  - in line mode every helper reduces to the original arithmetic.

## 3. Wind-ups, paths and the sidestep
**Wind-up.** In the duel, a technique is **fired** (cost paid, animation started, `fire` event with `lands` and `path`) and **lands** after its family's wind-up (`BATTLE.duel.windup`, ticks at 30 per second):

| Family | Basic | Hit | Sharp | Chain | Wither | Special | Heavy | Signature |
|---|---|---|---|---|---|---|---|---|
| Wind-up (ticks) | 6 | 7 | 8 | 8 | 9 | 10 | 12 | 12 |
| Seconds | 0.20 | 0.23 | 0.27 | 0.27 | 0.30 | 0.33 | 0.40 | 0.40 |

- The hit roll, damage and effects all happen at the landing, from the state at that moment.
- The animation still runs its full `anim`, counted from the fire, so the attacker's pacing is unchanged.
- On the line, both happen on the same tick, exactly as before.

**Paths** (`src/data/paths.ts`, `pathOf`). Each technique is a **straight line** or a **wide sweep**:
1. no force (a pure heal) or the Wither family (clouds, auras, roars) → sweep;
2. three or more hits (a barrage) → sweep;
3. a name word that names an area → sweep: spin, sweep, whirl, wave, quake, stomp, storm, tempest, blizzard, cyclone, tornado, avalanche, flood, tide, shower, rain, nova, burst, ring, gust, squall, gale, landslide, rockfall, downpour, tsunami, eruption, shockwave, roar, howl, chorus, crescendo, cascade, spiral, tremor, embrace;
4. everything else → straight line.

About a third of the 312 techniques are sweeps.

**The sidestep** (`BATTLE.duel.sidestep`):
- **The move:** 8 ticks (0.27 s), 180 units straight sideways.
- **The cost:** 4 guts, then a 45-tick (1.5 s) cooldown. Not while attacking, stunned, shoved or dashing.
- **Against a straight-line technique, if the sidestep starts during its wind-up:**
  - the hit roll gets the existing **disadvantage**, h = h²/100 (a 70% hit becomes 49%);
  - if the defender is more than **110 units** (a body radius and a little) from the technique's line when it lands, it **misses** (`miss` with `dodged`). The line runs from the attacker at the fire to where the defender stood then.
- **Against a sweep:** nothing.
- **What that means in play:** escaping completely needs about 5 ticks of sideways movement before the landing, so only the long wind-ups can be escaped. Heavies, Signatures and most Specials can be, with a quick reaction. Quick Basics and Hits can only be made harder to land. A sidestep **helps but never replaces stats**: the defender's SPD still sets the odds, and a sidestep costs guts and leaves a cooldown.

## 4. The CPU and Auto (`src/core/battle/duelAi.ts`)
The range plan of §12.10 (bands, techniques, dashes and pushes) is unchanged. On top of it:
- **Sidestepping:** against each incoming straight-line technique, the AI decides once.
  - It needs 4 guts plus 2 in reserve, and no cooldown.
  - Its chance by tier: Rookie 20%, Skilled 40%, Expert 60%.
  - It reacts after a reflex delay that SPD shortens (× (1 − SPD/2000)):

    | Tier | Reflex delay |
    |---|---|
    | Rookie | 8–14 ticks |
    | Skilled | 5–10 ticks |
    | Expert | 3–7 ticks |

  - Too late (after the landing) does nothing.
  - It sidesteps toward open ground.
- **Circling:**
  - between techniques, it circles for 1–2.5 s now and then (45% of its plans);
  - when the ring's edge is close behind it, it always circles toward open ground.
- **The player's Auto** is the same brain on the expert tier, with the chosen style. **Skip** gives exactly what an untouched Auto run would.
- **Every duel-only random draw happens in duel mode only.**

**Measured (24 matches per tier, 1,500–1,900 totals):**

| Tier | Straight-line techniques | Sidesteps | Full dodges |
|---|---|---|---|
| Expert | 431 | 124 (about 5 a match) | 3 |
| Skilled | 439 | 48 | 0 |
| Rookie | 153 | 1 | 0 |

## 5. Controls (phone)
- **Left thumb, movement:** a stick appears where the thumb lands.
  - Its direction is read against the camera: the part pointing at the opponent on screen walks forward or back, and the part across the screen strafes. So it works the same from any camera.
  - Release to stop.
  - **A quick flick sideways** (past 80% of its reach and released within 0.18 s) is a **sidestep** that way.
  - **A quick flick toward the opponent** is a **dash**.
- **Right side:** the four technique columns, exactly as now (cards glow when affordable and in range; Assist when that setting is on).
- **Push:** appears when touching, as now.
- **The top bar:** Auto, ×1/×2/×4, the camera button, pause.
- **Left-handed** mirrors the layout.

## 6. Cameras
- **Side-on** (the default on Auto and Skip-watching):
  - a three-quarter view from your monster's side of the line: turned 55° toward your monster and looking down 18°. On a tall phone, a square side view can't fit both monsters from inside the ring;
  - your monster on the left and a little nearer;
  - the distance is fitted every frame, so both monsters (whole, feet to ears) sit between the top bar and the technique panel;
  - it swings round smoothly as they circle (a critically damped spring, like today's arena camera).
- **Behind your monster:**
  - over its shoulder, looking down the line at the opponent;
  - best for steering and sidestepping.
- **Every camera stays inside the fence.** The Guild arena's crowd starts just past it.
  - When the side-on camera can't back up far enough, it widens its lens (up to 68°).
  - When the fight is by the wall on its side, it also rises until both fit.
  - All of these numbers are in `ART.duel` (`side`, `behind`, `confine`).
- **Cinematic cuts:**
  - for a **Special**, a **Signature** or a **KO**, a short cut (1.2–1.8 s) to a low three-quarter angle on the attacker, then back;
  - the battle keeps running: cuts never pause the simulation, and inputs still count.
- **One button** cycles side-on ⇄ behind. In the test build the cinematic cuts are a tuning switch (`ART.duel.cine.enabled`); a Settings toggle comes with the full release (it changes the save's settings, so it needs a save version).
- **Reduce motion:** gentle cuts (cross-fades, no swoops or shake), and the side-on camera turns slower.

## 7. What you see
- **Telegraph:** during the wind-up the attacker plays its wind-up pose.
  - A **straight-line technique** paints a soft lane on the floor toward the defender.
  - A **sweep** paints a wide arc or ring, which tells you not to bother sidestepping.
- **Sidestep:** the `sidestep_l` / `sidestep_r` clip; on a full dodge, a "Dodged!" float.
- **Impact:** at the landing tick (no more visual delays: the engine and the picture agree).
- Hits, KO and win use the monster's clips (`hit`, `hit_heavy`, `ko`, `win`). Effects are drawn in 3D: sparks and dust at the impact point.

## 8. The test build
- **Where:** Lab → **Battle 3D (test)** (`#lab/battle3d`).
  - Puddlepup (player) against Songheart Puddlepup (CPU), both Art 2.1 Ultra.
  - Fight, Auto, Skip, the speeds, both cameras and the cuts.
- **The entrance cutscene** (7.6 s):
  - the camera flies in over the river and Tunewick into the arena, along the arena's own camera path (`guild.json` → `flyIn`);
  - both monsters walk on from outside their gates to their start marks;
  - a face-off over your monster's shoulder;
  - then the fight starts. Tap to skip.
- **The arena:** the Breeders' Guild arena, built in Blender:
  - a packed-earth ring, rope-fence posts, banners, a crowd, the river and Tunewick behind;
  - our own layout dressed with CC0 Poly Haven models and materials (CREDITS);
  - baked lighting for the phone: every arena material is unlit with Cycles light in its texture; the monsters are lit by a key light along the arena's sun, and their shadows fall on an invisible shadow-catcher disc over the ring;
  - a Lite version (half the triangles, smaller textures, the town and distant trees painted into the sky);
  - built by `npm run art:arena` (`tools/blender/arenas/`; run `py -I tools/blender/arenas/fetch.py` once first to download the CC0 sources).
- **The renderer:** the Art 2.1 film look and its dynamic resolution (ART_2_DETAIL §3.5–§3.6).
  - WebGPU where the phone has it (it was 2.6× faster on the PC proxy), WebGL otherwise.
  - The target is **60 fps on the Galaxy S25 Ultra in Chrome**.
- **Lite** (Settings → Effects quality → Lite, or Auto choosing Lite): WebGL, the Lite arena, the Art 2.0 Puddlepup, the lowest effect level (no AO, bloom or MSAA), and at most 1.5× resolution.
- **The current battle is untouched** everywhere else (cups, Versus, trials).
- **What gets reported:** fps, render resolution, download size and memory, plus a screen recording from each camera. The stats line under the top bar shows fps, resolution, renderer and effect level live.

### 8.1 Measured (Nov 2, the PC proxy)
`npm run art:battle3d` on this PC: Intel Iris Xe, Chrome, WebGPU, a 412 × 892 phone screen at 2.625×. The owner's phone test gives the real numbers.

| | |
|---|---|
| Frame rate | the duel starts at 2.0× (`ART.duel.dprStart`); dynamic resolution steps down fast while most frames are late (`ART.duel.fastDrop`) and settles at 1.6–1.7× within about 4 s, then **60 fps with every effect on**. The entrance's first seconds stall here while the graphics warm up |
| GPU time per frame | 7–10 ms once settled |
| First download (Full) | **12.3 MB**: arena 7.4 MB, Puddlepup 4.1 MB (both fighters share it), code 0.7 MB gzipped (WebGPU renderer 192 KB, loaders 166 KB, the duel 46 KB, the texture decoder 262 KB); cached after the first visit |
| First download (Lite) | about 3.2 MB: arena 2.0 MB, the Art 2.0 Puddlepup 0.6 MB, code |
| Memory | graphics memory about 230 MB at 2.0×, 180–190 MB once settled (mostly the render buffers); JS heap about 105–120 MB |
| Arena | Full 127,923 triangles in 14 draws; Lite 58,562 in 10 |
| Puddlepup Ultra | 59,635 triangles, 2,061 fur cards, 28 joints |

## 9. Balance (re-run in duel mode)
Command: `npm run sim:balance -- --only battle --mode duel --out docs/BALANCE_DUEL.md` (200 AI-vs-AI battles per pair, 32 breeds).

| Pairs inside 30–70% | Total 1,000 | 2,000 | 3,000 |
|---|---|---|---|
| Classic (line) | 94.8% | 99.4% | 94.2% |
| Duel, first run | **97.0%** | 98.2% | 88.1% |
| Duel, after the two adjustments below (the committed report) | 96.4% | 98.2% | **90.3%** |

**What moved** (mean win share against every breed, at the 3,000 total):
- **Fast, skilful breeds gain:** they circle and sidestep well, because SPD shortens the reflex and evasion is already SPD.
  - Velvesper 61 → 67, now the strongest late, and the source of many of the 3,000 outliers
  - Galeheron 54 → 62
  - Tumblefox 51 → 58
  - Quillion 46 → 51
  - Plumdrake 39 → 45: its knockback gusts are sweeps, and its tankiness rides out the duel.
- **Slow heavy hitters lose:** their long, telegraphed Heavies are the easiest to sidestep.
  - Gloomgrin 40 → 34
  - Grumblestone 48 → 43
  - Lootlid 46 → 42
  - Hearthwing 41 → 37
  - Ashwraith 63 → 58, still the strongest.
- **On average** a breed's mean moves 3 points. At 1,000 the duel is *more* even than the line; at 3,000 less.

**Adjusted** (AI tuning only, no formulas):
1. Statue Pose fighters don't circle (unless cornered), because standing still is their trait.
2. SPD shortens the sidestep reflex less (`AI.duel.reactSpdDiv` 2,000 → 3,000).

Together they took the 3,000 total from 88.1% to 90.3%.

**Open, for after the owner has played it:**
- if the late game should be closer, shorten the Heavy and Signature wind-ups (12 → 10 ticks), or give slow breeds a longer reflex window;
- the wind-up table is the main lever.

## 10. Files
- **Core:**
  - `src/core/battle/geometry.ts` (the ring), `duelAi.ts`, and `engine.ts` (the `mode` option, the fire / land split, sidesteps, strafing);
  - `types.ts` (`BattleMode`, `PendingFire`, the `sidestep` action and event, `move.side`);
  - `src/data/paths.ts`;
  - `tuning.ts` (`BATTLE.duel`, `AI.duel`).
- **Tests:** `src/core/battle/duel.test.ts`; every line-mode test unchanged (the golden record holds).
- **Balance:** `scripts/balance.ts` `--mode duel`.
