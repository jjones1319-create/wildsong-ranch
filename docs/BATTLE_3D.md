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

## 4. The CPU and Auto: AI 3.0 (`src/core/battle/duelAi.ts`, `duelSense.ts`, `duelRead.ts`)
The range plan of §12.10 (bands, techniques, dashes and pushes) still decides where to stand and what to fire. AI 3.0 is the duel's own layer on top of it; the owner asked for "a mix of all of these" (Nov 2), plus: **an untrained or spoiled pet makes worse decisions**. Every rule below happens in duel mode only, so line battles replay bit for bit.

### 4.1 Battle sense
Every fighter brings a **battle sense** from 5 to 95. It sets how well it does everything below.
- **CPU fighters:** by tier: Rookie 25, Skilled 55, Expert 85.
- **Your monster (Auto and Skip):** from how it was raised:
  - 30 to start;
  - +1 for every battle it has fought (wins, losses and draws), up to +35;
  - loyalty (the average of Spoil and Fear): + (loyalty − 50) × 0.4, so −20 to +20;
  - spoiled (the raising style Spoil − Fear is *doting*: −15; *fond*: −6).
- Battle sense below 40 plans like a Rookie, below 70 like a Skilled fighter, and from 70 like an Expert.
- The screen shows it, with the reason ("seasoned", "loyal", "spoiled", "untrained").
- **In the test** (Lab → Battle 3D), the 🧠 chip raises the player's Puddlepup three ways (`ART.duel.testUpbringing`): Seasoned (30 battles, loyal: 70), Untrained (30) and Spoiled (doting: 19). Tapping it restarts the fight, so Auto can be compared.

### 4.2 Sidestepping, timed to the wind-up
- Against each incoming straight-line technique it decides once. Its chance is 10% + 0.6% per point of battle sense (25 → 25%, 85 → 61%). It needs 4 guts plus 2 in reserve, and no cooldown.
- **Its reflex** shrinks with battle sense, from 9–16 ticks at 0 to 2–5 ticks at 100, then × (1 − SPD/3,000). Too late (after the landing) does nothing.
- **From 50 battle sense** it doesn't bother sidestepping a technique already aimed off its line.
- **Below 35** it sometimes flinches: a nervous sidestep when nothing is coming, which wastes guts.
- It sidesteps toward open ground.

### 4.3 Punishing openings
- An **opening** is when the opponent can't sidestep or answer: recovering after its technique has landed or missed, stunned, distracted, or stopped by the fence (§4.5).
- Once per opening, with a chance of 0.9% per point of battle sense, it fires its best affordable technique for the current range after a delay that shrinks from 12 ticks to 2 with battle sense.
- With nothing ready there, it heads for the range of its best affordable technique and tries again while the opening lasts. A rusher, or any fighter from 70 battle sense, dashes in.
- **Patience** (from 50 battle sense): it doesn't trade blows with a technique it is about to sidestep. It dodges, then punishes.
- **Tried and dropped:** keeping a guts reserve for punishing. Holding shots resets the range plan's pacing, so the fighter attacked a third less often and lost more than it gained.
- **Measured:** given an opening it can use (free to act, a technique ready), an Expert punishes at least 1.5 times as often as a Rookie. Experts often spend their guts as fast as they get them, so against a player who attacks nonstop they punish about one opening in five; against a calmer player, more.

### 4.4 Reading habits
During the match it counts what the opponent does, and from about 3 seconds in it adjusts:
- **A sidestepper** (sidesteps at least 30% of its straight-line attacks, out of at least 3): its sweeps are worth up to 80% more.
- **A rusher** (walks in at least 40% of the time): its knockback techniques are worth up to 60% more, and it backs off and circles to make them chase.
- **One favourite range** (at least half of the opponent's techniques, out of at least 4): that range counts as up to twice as dangerous, so it stays out of it.
- How strongly it adjusts grows with battle sense; a Rookie barely notices.

### 4.5 Using the ring
- **The fence:** a fighter knocked or shoved into the fence stops there and is **stunned for 0.4 s** (`BATTLE.duel.fenceStunTicks`), an opening.
- **Herding:** when the opponent is within 3 m of the fence behind it, a fighter with at least 40 battle sense circles to get between the opponent and the middle, so the opponent's back faces the fence, and prefers knockback techniques (up to 60% more).
- **Escaping:** when its own back is near the fence, it always circles toward open ground.

### 4.6 Visible fighting styles
CPU personalities and the player's Auto styles fight in ways you can see:

| Style | Who | What it does |
|---|---|---|
| Rusher | Aggressive and Brawler; Auto Aggressive | circles half as often, dashes in to punish, taunts when you miss |
| Trickster | Trickster | feints: quick steps in and out at the edge of a range, switching the way it circles |
| Careful | Cautious and Sniper; Auto Defensive | circles 40% more, sidesteps 15 points more often, and saves guts for its Special or Signature once the opponent is under 35% HP |
| Steady | Steady; Auto Balanced | the plan as it is |

### 4.7 Spoiled monsters
A monster raised *doting* or *fond* (§4.1) also shows it:
- **showing off:** 25% (doting) or 12% (fond) of the time it fires its most forceful affordable technique instead of the best one;
- **slacking:** now and then (20% or 10% of its plans) it stops chasing for a second.

### 4.8 What stays the same
- The player's Auto is this same brain with the monster's own battle sense and the chosen style. **Skip** gives exactly what an untouched Auto run would.
- Every duel-only random draw happens in duel mode only, and the injected RNG is the only randomness.

**Measured before AI 3.0 (24 matches per tier, 1,500–1,900 totals):**

| Tier | Straight-line techniques | Sidesteps | Full dodges |
|---|---|---|---|
| Expert | 431 | 124 (about 5 a match) | 3 |
| Skilled | 439 | 48 | 0 |
| Rookie | 153 | 1 | 0 |

## 5. Controls (phone)
- **Sideways or upright** (the owner, Nov 2: "sideways, upright still works"):
  - A battle that starts upright asks once a session: **Play sideways** or **Stay upright**.
  - Sideways, where the browser can (Android: the installed app, or a tab in full screen), the game turns the screen itself and turns it back afterwards; elsewhere (iPhone) it asks you to turn the phone.
  - **Sideways layout:** the bars and buttons along the top, the cards as a 2×2 block down the right edge, the stick under the left thumb, Push just left of the cards. Left-handed mirrors it.
  - The rest of the game stays upright (the installed app's manifest).
- **Two thumbs at once:** the cards and Push act on the touch itself, and nothing on the panel starts a pinch or scroll, so a finger can stay on the stick while the other attacks (v1.16.1).
- **Left thumb, movement:** a stick appears where the thumb lands.
  - Its direction is read against the camera: the part pointing at the opponent on screen walks forward or back, and the part across the screen strafes. So it works the same from any camera.
  - Release to stop.
  - **A quick flick sideways** (past 80% of its reach and released within 0.18 s) is a **sidestep** that way.
  - **A quick flick toward the opponent** is a **dash**.
- **Right side:** the four technique columns, as now: cards glow when affordable and in range.
  - **Out of range, a tap does nothing** (the owner, Nov 2): you walk into range yourself. Battle 3D has no Assist walk.
  - A tap on an in-range card while your monster is still busy fires as soon as it can, within half a second (`INPUT.tapBufferMs`).
  - A chip above the cards shows the current range and distance ("Near · 2.6 m").
- **Push:** appears when touching, as now.
- **The top bar:** Auto, ×1/×2/×4, the camera button, pause.
- **Left-handed** mirrors the layout.

## 6. Cameras
- **Side-on** (the default on Auto and Skip-watching), framed for the screen's shape (`framing.ts`, `ART.duel.side`):
  - upright: a three-quarter view from your monster's side of the line, turned 55° toward your monster and looking down 18°. On a tall phone, a square side view can't fit both monsters from inside the ring;
  - sideways: nearly square side-on (14°, looking down 12°), with the fight kept left of the cards (right of them when left-handed);
  - between the two shapes it blends, so turning the phone swings the camera smoothly;
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
  - a packed-earth ring, rope-fence posts, banners, the stands (their crowd is drawn by the game, §8.2), the river and Tunewick behind;
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
| First download (Full) | **12.3 MB** in v1.15 (11.5 MB from v1.16, when the people left the arena's bake for the live crowd): arena 7.4 MB (6.6 MB), Puddlepup 4.1 MB (both fighters share it), code 0.7 MB gzipped (WebGPU renderer 192 KB, loaders 166 KB, the duel 46 KB, the texture decoder 262 KB); cached after the first visit |
| First download (Lite) | about 3.2 MB (2.9 MB from v1.16): arena 2.0 MB (1.7 MB), the Art 2.0 Puddlepup 0.6 MB, code |
| Memory | graphics memory about 230 MB at 2.0×, 180–190 MB once settled (mostly the render buffers); JS heap about 105–120 MB |
| Arena | Full 127,923 triangles in 14 draws; Lite 58,562 in 10 (from v1.16, without the baked people: 101,187 and 44,855) |
| Puddlepup Ultra | 59,635 triangles, 2,061 fur cards, 28 joints |

### 8.2 The crowd
The owner (Nov 2): "people cheering and movement with some detail and random monsters in there (more people based on your popularity)". For the monsters they chose painted wooden cut-outs of every breed's Classic drawing; each can become a real 3D monster later, when that breed's model is built.

- **Fame fills the stands.**
  - The arena's benches are baked empty. `guild.json` → `seats` lists every spot: 238 in Full (120 in Lite).
    - 172 bench seats;
    - 38 spots at the rail in front of the stands (always kids);
    - 28 standing spots by the gates and along the open front.
  - The share filled follows your monster's Fame: a quarter at Fame 0, every spot at 100, straight between (`ART.duel.crowd.fillPct`).
  - Seats fill in a fixed order from a seed: the long stand and the front rows first, plus a seeded random share. For one seed the same Fame always gives the same crowd, and more Fame only adds people (nobody moves or changes).
  - The seed is the battle's own (plus `ART.duel.crowd.seed`), so each battle seats a different crowd.
  - Empty benches show where nobody sits.
  - The test build's **"👥 Fame" chip** (in the top bar) cycles 10 → 40 → 70 → 100 and refills the stands. It starts at 60. The stats line shows the crowd's count and CPU time.
- **People** (`src/art3d/duel/crowd.ts`, `crowdParts.ts`): townsfolk built in code, low-poly and smooth-shaded.
  - One instanced draw per part, each with a colour per person: seated and standing bodies (trousers a darker shade of the top), heads with eyes, arms, hair, hats, scarves, pennants and foam hands.
  - 8 skin tones, 16 clothes colours; slim to stout and short to tall; kids are about 1 in 6 on the benches.
  - Their light is painted into a small matcap (a warm sun from above, a cool sky, a warm bounce) instead of the scene's lights. So they sit with the arena's baked light, cost no lights, and look the same on WebGL and WebGPU.
- **Movement** (`crowdPose.ts`, `crowdPlan.ts`):
  - a gentle bob and sway, each person at their own pace;
  - heads turn to follow the fighters (up to 70°);
  - now and then someone waves.
- **Cheers** start on the side nearest the action and ripple round the stands in about a second:
  - **small** on a hit (about a third join in);
  - **big** on a crit, a heavy hit, a knock into the fence, a Special or a Signature;
  - **huge** on a KO (everyone);
  - a **standing ovation** on the win (the benches stand up).
  - Arms go up, people bounce and lean in, and pennants and foam hands wave.
  - **Reduce motion:** arms still go up, but every other movement is at 35%, nobody hops, and nobody stands up.
- **Painted cut-outs** (`cutouts.ts`):
  - about 1 in 7 bench seats holds a plywood board of a random breed instead of a person: about 10% of the crowd (12.5% at Fame 10, 10% at Fame 100, averaged over seeds);
  - any of the 32 breeds; no breed repeats until all have shown, and with each battle's own seed every breed turns up within about three full-house battles;
  - boards stand only on the benches, never at the rail, where they would hide the people behind;
  - painted with the breed's Classic drawing, rasterised once at load into one atlas, with a plywood edge round the silhouette;
  - they bob and rock with the cheers;
  - **not built yet:** a breed with its own 3D model (`src/art/models.ts`) standing in its board's seat. The plan already gives every board's seat its breed.
- **Budgets** (the crowd's own; measured at Fame 100):

| | Full | Lite |
|---|---|---|
| People + boards (seed 7) | 213 + 25 | 108 + 12 |
| Triangles (≤ 40k / 20k) | 36,643; across 300 seeds 34,857–39,034 | 17,956; across 300 seeds 16,271–19,427 |
| Draw calls (≤ 10) | 10 (9 once everyone stands for the ovation) | 7 (no scarves, pennants or foam hands in Lite) |
| Textures (≤ 2 MB) | 1.9 MB: the boards' atlas (960 × 484, no mipmaps) and a 64 px matcap | the same |
| CPU per frame | 0.2–0.45 ms in the crowd viewer on the PC proxy; 0.4–0.9 ms measured inside the headless game, while the GPU there runs at a few fps | about half |

People and boards at each Fame (Full, seed 7): Fame 0: 52 + 8; Fame 10: 65 + 12; Fame 40: 113 + 18; Fame 60: 145 + 22; Fame 70: 159 + 25; Fame 100: 213 + 25. Lite: 26 + 4, 33 + 6, 55 + 11, 73 + 11, 82 + 11, 108 + 12.

Each person is about 170 triangles: a 7-sided torso with three-sided legs and feet (71), a head with eyes (50), two arms (18), hair (24) or a hat (40), and sometimes a scarf (18), a pennant (7) or a foam hand (24). A board is 12.

- **The arena without its baked people:** Full 101,187 triangles in 14 draws, 6.6 MB (was 127,923 and 7.4 MB); Lite 44,855 in 10, 1.7 MB (was 58,562 and 2.0 MB). The fly-in path is unchanged.
- **Review:** `node tools/art/crowd-review.ts` writes `art-review/arena-guild/crowd-sheet.png`. It shows the crowd viewer (`tools/art/crowd-viewer.html`: Fame, cheers, close-ups, Lite, Reduce motion) beside stills from the game.

## 9. Balance (re-run in duel mode)
Command: `npm run sim:balance -- --only battle --mode duel --out docs/BALANCE_DUEL.md` (200 AI-vs-AI battles per pair, 32 breeds).

| Pairs inside 30–70% | Total 1,000 | 2,000 | 3,000 |
|---|---|---|---|
| Classic (line) | 94.8% | 99.4% | 94.2% |
| Duel, first run | **97.0%** | 98.2% | 88.1% |
| Duel, after the two adjustments below | 96.4% | 98.2% | 90.3% |
| Duel with AI 3.0 (§4; the committed report) | 96.6% | 98.0% | **92.7%** |

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

**AI 3.0** (§4) made the late game a little more even: at 3,000 the breeds that had run away lost a little (Velvesper −4.4, Wishlume −4.4, Starhowl −3.9) and some slow ones gained (Cobblemaw +3.7, Scrollopus +3.6). Earlier totals barely moved. Attacks per monster per match stay at 6.3–12.2.

**Adjusted before AI 3.0** (AI tuning only, no formulas):
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
- **The picture:** `src/art3d/duel/duel3d.ts`; the crowd in `crowd.ts`, `crowdPlan.ts` (pure), `crowdPose.ts`, `crowdParts.ts` and `cutouts.ts` (`ART.duel.crowd`); the arena's seats from `tools/blender/arenas/guild.py` (`crowd_spots`).
- **Tests:** `src/core/battle/duel.test.ts`; every line-mode test unchanged (the golden record holds); `src/art3d/duel/crowdPlan.test.ts` (filling by Fame, the fixed seat order, the cut-outs, the cheers).
- **Balance:** `scripts/balance.ts` `--mode duel`.
