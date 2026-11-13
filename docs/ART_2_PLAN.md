# Art 2.0: Blender monsters and scenes

**Status:** written Oct 28, 2026. The owner approves it by running P0 and P1. This is the spec behind the prompts in `ART_2_PROMPTS.md` (repo root): one milestone each, P0 to P19. **Updated Nov 7, 2026:** the owner approved Puddlepup's Art 2.1 Ultra look (`docs/ART_2_DETAIL.md`), and the other monsters now come in batches of 5 (§6, §8) on the Ultra budgets (§3.6).

**One breed per monster:** the main/sub mix system is retired (owner, Oct 28). Every monster is its own whole breed with one fixed design, and breeding makes another whole breed. P0 removes mixing from the rules and saves. That frees every breed to be designed and painted individually in Blender for the highest quality, with no recolouring and no swapped parts.

**The owner's goal:** rehaul the entire animation, make every monster significantly higher quality, make the farm and battle scenes higher quality, and then every other scene. For example, Waterfall Stand should look like the monster really is sitting on a rock under a waterfall, in a slight anime/cartoon style. The same goes for every other scene in the game.

**Blender creates everything you see.** It makes:
- the monster models, their skeletons and every animation;
- their faces (every expression);
- the scenes and the props;
- the big water, splash, mist, fire and smoke effects.

The game (three.js) only displays what Blender made. Code still draws the UI, the Classic fallback monsters and V1's small effect sparks.

**How it runs:** P0 retires mixing (rules and saves, no art). P1 builds one pilot monster, rebuilt at Art 2.1's detail (`docs/ART_2_DETAIL.md`, P1.1–P1.2). Its look sets the look for everything after: the owner approved it on the phone on **Nov 7, 2026**, and the monster batches started then (§8). P2, the first real scene (Waterfall Stand), moved into roadmap step 2, the walkable 3D farm, so it no longer has to come first. The owner's roadmap after that: 3D event scenes, then the 3D duel as the real battle.

## 0. Decisions

| Question | Decision |
|---|---|
| What a monster is | A real 3D model built by Blender scripts from the breed's CONTENT brief and colours, exported as a small `.glb` and drawn live on the phone with our own cel shader (three.js). |
| One design per breed | Mixes are retired (P0), so each breed has one look (Hearthwing, Pluckrex and Paladove have a young and a grown one). Blender paints each breed's colours, markings and surface detail into its own textures; nothing is recoloured at runtime. The 21 secret-phrase variants (CONTENT §12) stay as special looks of their breed: an alternate texture set (and any small extra, like Town Crier Tumblefox's bell) on the same model. |
| Why live 3D and not pre-rendered frames | Drawn live, a model shows every face, grows with its life stage, follows taps, holds props, moves at 60 fps, takes each scene's light (warm at golden hour, soaked under the waterfall, moonlit at night) and works under any camera. Pre-rendered frames of 35 looks × ~50 animations would run to hundreds of MB and look the same in every scene. A breed's file is a few hundred KB. The same files can later walk into the owner's dungeon crawler, which already uses three.js. |
| Scenes | Built and lit in Blender and rendered as backdrop *plates*: two or three depth layers, plus a short loop wherever something moves. The camera, anchors and light are exported as JSON. Whatever the monster touches (the rock, the falling water, the log) is a live 3D prop, so the monster really sits on it, holds it or gets splashed by it. The monster is lit to match the plate. |
| Look | "Slight anime/cartoon" (§2). |
| Faces | Anime-style eyes and mouths made in Blender as a face sheet (every expression), shown on small patches of the 3D head. The game swaps cells of the sheet for expressions and blinks, and slides the pupils for glances. |
| Skeletons and motion | One rig template and one clip set per body plan (9 in all), shared by its breeds. The clip names are a contract (§5) that every scene can call. |
| The drawn (SVG) monsters | Stay, as the fallback (a model still loading, offline before its first download, and no WebGL where the portrait picture is missing) and as a setting: Settings → Graphics → Monsters: **3D / Classic**. A breed without a model shows Classic. |
| Pilot breed | **Puddlepup** (the owner may swap it). It's the balanced starter most players meet first; its quadruped body plan serves 9 breeds; its round shapes suit the style; and a water monster suits the Waterfall Stand pilot. |
| New dependencies (approved by running P1) | `three` (runtime, in a lazy chunk) and a dev-only glTF optimiser (`@gltf-transform/cli` with meshopt). Nothing else without asking. |
| Reference pictures | Every monster has the owner's ChatGPT reference set in `chatgpt/monsters/<NN>-<breed-id>/`: `PROMPTS.md` (its creature card and "Notes for Claude Code"), `1-hero.png` (the design lock), `2-turnaround.png`, `3-faces.png`, `4-details.png`, `5-poses.png`, and where they apply `variant-<variant-id>.png`, `grown-*.png`, `cocoon-*.png` and `6-scale.png`. Read `chatgpt/FOR-CLAUDE-CODE.md` and the owner's two choices at the top of `chatgpt/CHECKLIST.md`, then view every picture before modelling. Which source wins: the card on part counts and which parts exist (image models miscount; log any mismatch); the pictures on shapes, proportions, markings, placement, surface detail and materials (the hero over the others, the turnaround for measurements); CONTENT §2.2 and `src/art/monster/variants.ts` on exact colours (never sample hex from a picture). The pictures are gitignored reference only and never shipped. §2.4 points to the style text they were made with. |
| What this replaces | GAME_DESIGN §14.3 main/sub mixing (retired in P0); VISUAL_UPGRADE_PLAN §0 ("3D pilot skipped", "richer storybook vector", "ChatGPT painted backgrounds") and its V3, V4 and V5; CLAUDE.md's "Not for now: 3D monsters"; and the "no pre-rendered images or 3D" lines in GAME_DESIGN §22 and NEW_MONSTERS §6. V1's effects layer stays. V2 (visible attacks) becomes P12. |

## 1. What does not change

- **`src/core/`:** after P0 (which retires mixing in the rules), the rules, the battle simulation and determinism are untouched. P1–P19 are presentation only.
- **Saves:** after P0, a monster's look comes from its breed, its secret variant (if any) and its stage. The new Graphics setting uses a per-field fallback, as V1's did. If a schema change is ever needed, bump `SAVE_VERSION` and add a migration and a test.
- **The golden rules:**
  - originality;
  - phone first (iOS Safari 16.4+ and Android Chrome, installed or not);
  - every animation skippable;
  - Reduce motion shows still pictures;
  - numbers live in `tuning.ts` (a new `ART` block).
- **V1's effects layer (Pixi)** still sits on top of the 3D monsters. It plays the Blender-baked flipbooks and its own small sparks, beams and flashes.
- **Sound 2.0's drill cue contract** (SOUND_UPGRADE §8.1): scenes report their length and named markers (`impact`, `splash`, …) so the Foley lines up. There are five outcome stingers per drill (§8.3), which match the five scene endings (§3.4).

**Where it runs:** every prompt runs in Claude Code's VS Code extension on the owner's Windows PC, in the Monster Rancher folder.
- **The owner never runs commands.** Claude runs Blender (headless, by its full path; see CLAUDE.md), npm, Playwright and git itself.
- **Long renders run as background commands** that write a log Claude checks. Split them per breed, clip or plate so no single command hits a time limit.
- **Showing pictures:** to show the owner a picture, name its file in the chat; the owner clicks it and VS Code opens it.
- **Plans** open in VS Code as Markdown documents, and the owner may leave comments in them.

## 2. Art bible: "slight anime/cartoon"

### 2.1 Monsters
**Since Puddlepup's approval (Nov 7, 2026) the monsters use Art 2.1's film look** (`docs/ART_2_DETAIL.md` §3.4–§3.7): soft studio light with a cool fill and near-neutral rims, standard physical materials, fur, scales and plates baked from a detailed source, **no outlines**, and glossy 3D eye lenses with a baked face and blink bones (morph targets come with the cinematic set, not built yet). The shapes, colour and motion rules below still apply. The cel shading and outline rules are Art 2.0's: they describe the Art 2.0 models that normal play shows until the walkable-farm step.

- **Shapes:**
  - Soft, rounded and chunky, with clear silhouettes that read at 64 px.
  - Babies lean chibi (the head is about 45% of the height); grown forms and big breeds less so.
  - Sturdy limbs and no thin, fiddly parts.
- **Shading:**
  - Cel shading with two tones (lit and shadow) and a soft, slightly feathered terminator.
  - Shadows are the local colour shifted cooler and darker, never grey.
  - A warm rim light on the edge away from the key light.
  - A small sheen only on glossy materials (shell, scales, brass, ice).
- **Lines:**
  - An outline around the silhouette (inverted hull) in a darker tint of the local colour, not black.
  - About 2–3 CSS px at stage size; thinner on High; off on Lite.
- **Eyes and faces:**
  - Big, glossy, expressive eyes with one or two white highlights and a soft iris gradient; simple mouths; blush when happy.
  - Every face reads at 100 px: neutral, happy, tired, stressed, sad, angry, sleepy, sick, plus the scene faces strain (eyes squeezed shut), dizzy (spirals) and surprised. Sparkle and blink go on top.
- **Colour:** each breed's hex palette from CONTENT §2.2, saturated but soft. Avoid pure black and pure white.
- **Motion:**
  - Every clip has anticipation, follow-through and squash-and-stretch.
  - Ears, tails, fins, wings and capes lag behind the body (springs at runtime).
  - Feet plant without sliding.
  - Nothing is ever perfectly still: idles breathe, blink and glance.

### 2.2 Scenes
- **Painterly light:**
  - big soft clouds, and a warm sun with long soft shadows;
  - atmospheric depth (far layers lighter and bluer);
  - gentle bloom on highlights, and a light depth-of-field blur on the far layer.
- **Stylised nature:**
  - foliage as soft clumps with leaf cards, and grass in tufts;
  - rocks with chunky bevels and moss;
  - water as layered translucent teal with white foam ribbons, sparkles and mist.
- **Storybook coziness:** the vale, Tunewick and the ranch of CONTENT §1. Warm, gently funny, a little bittersweet; never epic or grim.
- **Readability:** the monster always reads first.
  - The plate behind it is lower in contrast.
  - It has a soft contact shadow.
  - It's lit by the scene's own light (§3.5).

### 2.3 Originality
- Everything is our own: procedural Blender geometry and materials. CC0 textures or HDRIs only if they clearly help, and each is logged in `CREDITS.md`.
- No design may resemble a famous character. The fresh-eyes review (§6) checks for it.
- Describe the style in plain words in code and docs; don't name other games, films or studios as references.

### 2.4 The style text for the ChatGPT reference pictures
The style text now in use is the project instructions in `chatgpt/PROJECT-INSTRUCTIONS.md`: every picture in `chatgpt/monsters/` was made with it, with `chatgpt/style-anchor.png` (Puddlepup's hero) attached to each hero. The owner chose its **film** look (not the anime cel variant described under its box) and a **fur** coat for Puddlepup (`chatgpt/CHECKLIST.md`). The older style text that used to sit here, and the Style Guide in `docs/CONCEPT_PROMPTS.md`, are retired. How the film look changes the shading and outline rules of §2.1 is in `docs/ART_2_DETAIL.md` (Art 2.1), approved with Puddlepup on Nov 7, 2026.

## 3. Architecture

### 3.1 The pipeline (the owner's PC, headless Blender 5.2)

Blender runs headless only (CLAUDE.md, "Tools on the owner's PC"): `blender -b --factory-startup --python <script> -- <args>`, with every script pinned to the installed version's API.

**Ultra monsters (Art 2.1, the pipeline every batch uses):** `tools/blender/monsters/build_ultra.py` builds a look from its recipe `breeds/<breed>_ultra.py` (a grown form: `<breed>_grown_ultra.py`, ID `<breed>-grown`), and `tools/art/ultra.ts` ships it to `public/models/monsters-ultra/` (the model, its Lite copy and the sidecar). The recipe contract is `tools/blender/monsters/breeds/RECIPE.md`; the techniques are ART_2_DETAIL §3 and §9. The tree below is Art 2.0's, which still makes the models normal play shows.

```
tools/blender/
  lib/                  shared helpers: node builder, toon materials, render setup, contact sheets (moved out of ranch_scenes.py)
  monsters/
    plans/<plan>.py     one body plan's rig template and clip generators (§4, §5)
    breeds/<id>.py      a breed recipe: shapes, proportions, parts, painted textures, sockets, forms, secret variant
    build.py            --breed <id> | --plan <plan> | --all  [--review]
  scenes/<scene>.py     one script per scene set: plates, loops, scene.json, props.glb
  out/                  scratch renders and review sheets (gitignored)
tools/art/              Node: optimise .glb, encode plates and loops (reusing encode.ts), portraits, art:review
public/models/monsters/<look>.glb    one per look (puddlepup, hearthwing-young, hearthwing-grown, …), textures inside
public/baked/scenes/<scene>/         plates (.webp), loops (.mp4), scene.json, props.glb
```

- **Recipes are data, not sculpts.**
  - A breed is built from rounded primitives (spheres, capsules, tapered tubes, tori), placed and sized by its recipe.
  - They're merged into one smooth body (voxel remesh, smoothing, then decimation to budget).
  - Hard parts (shells, horns, armour, capes, gears, the chest lid) are separate meshes on bones.
  - Feedback like "bigger ears" means changing a number and rebuilding.
- **Painted textures:**
  - Each breed's colours (its CONTENT palette), markings and surface detail (fur strokes, scales, stone grain, feathers, brass, paper) are painted procedurally in Blender.
  - They're baked into one small texture set per look: base colour, plus a glow map where the brief has glowing parts (embers, crystals, the lantern's heart).
  - Each breed can have details no other breed shares.
- **Faces:**
  - Blender draws each look's face sheet: every expression's eyes and mouth, plus a pupil layer and an eye-colour mask, rendered into one small texture embedded in the `.glb`.
  - Each eye and the mouth is its own small patch, conformed to the head and UV-mapped to the sheet.
- **Effects:** splashes, mist, droplets, foam, fire, smoke and ice are simulated or rendered in Blender (Mantaflow where it helps) and baked to small flipbook sprite sheets for the effects layer.
- **Sockets:** empties on bones (head, crown, back, mouth, hands or front paws, tail) where scene props attach: a log, pinecones, a leaf umbrella.
- **Secret variants:** a breed with a CONTENT §12 variant gets a second texture set (and any small extra part, such as Town Crier Tumblefox's bell) in the same `.glb`.
- **Forms:** Hearthwing, Pluckrex and Paladove get a young and a grown model.
- **Export:**
  - glTF binary, Y-up, deform bones only; every clip is its own action, sampled at 30 fps.
  - Then `@gltf-transform` quantises it and applies meshopt.
  - A test reads every `.glb` and checks its clip names against §5, its sockets, and its budget (§3.6).
- **Commands** (added to `package.json`):
  - `npm run art:monster -- <id> | --plan <plan> | --all`
  - `npm run art:scene -- <scene>`
  - `npm run art:review -- <id | scene>`
  - `npm run art:portraits`

### 3.2 The runtime (`src/art3d/`, one lazy chunk)
**Ultra monsters** draw on Art 2.1's film renderer (`src/art3d/perf/`, shared by `src/art3d/ultra/`, the Lab → 3D Gallery and Battle 3D): ART_2_DETAIL §3.4–§3.7 and §9.3. The registry of finished breeds is `src/art/ultraLooks.ts` (`ULTRA_LOOKS`). The list below is the Art 2.0 runtime, which normal play still uses.

- **Loader and cache:** `three` with `GLTFLoader` and the meshopt decoder. A model loads once, is cloned per use (`SkeletonUtils`), and is disposed when nothing uses it.
- **Toon material:** one shader for every monster. It does:
  - a two-tone cel ramp with a soft terminator, plus the rim light;
  - the breed's painted textures, with glow where its glow map says;
  - the sick tint and the "visibly old" fade from stage 8;
  - the wet look for water scenes, and the sparkle.

  Its light comes from the stage or the scene (§3.5).
- **Outline:** an inverted hull, skinned, in a darker tint of the colour beneath it.
- **Face controller:** switches cells of the Blender-made face sheet (expressions, blink, sparkle) and slides the pupils toward taps. The head turns a little toward the tap too.
- **Springs:** ears, tails, fins, wings, capes and tentacles get a light spring on top of the clip (off on Lite).
- **Also:** life-stage size, the secret-variant texture swap, and the signature particles from GAME_DESIGN §22 (embers, glints, petals…), now Blender-made sprites around the model.
- **`Stage3D`:** a transparent canvas that renders one or more monsters and props with a given camera and light.
  - Used by the ranch stage, the arena, the Lab and every scene.
  - One live 3D canvas per screen; the battle adds the effects canvas on top.
- **Animation player:**
  - plays contract clips by name, with cross-fades;
  - moves the root at the clip's speed so feet don't slide;
  - fires each clip's markers (footfalls, impacts) for sound and effects.
- **Quality:** follows Settings → Graphics → Quality (Auto works as today).
  - **Ultra:** up to 2× pixel ratio, MSAA, outlines, springs and a soft shadow.
  - **High:** 1.5×, outlines and springs.
  - **Lite:** 1×, no outline, no springs, a 30 fps cap.
- **Fallback:** Classic SVG when the setting says so and while a model loads (it cross-fades in); when WebGL fails, the portrait picture (or Classic if the picture is missing).

### 3.3 Where monsters appear
**Ultra monsters, for now:** each finished batch shows in **Lab → 3D Gallery** (`#lab/gallery3d`) and in **Battle 3D**, where any finished breed can fight on either side (BATTLE_3D §8.4); the owner chose this on Nov 7, 2026. The ranch, the Monster Card and the cups switch to them later, in the walkable-farm step (roadmap step 2); until then they show the Art 2.0 models and the Classic drawings as below.

`MonsterPortrait` is used on about 29 screens.
- **Live 3D** where the monster is the subject of the screen:
  - the ranch stage, the battle arena and the Monster Card;
  - the Lab (the editor preview and the Models viewer);
  - scenes, the Shrine result, Pell's "Meet" and the Farewell;
  - Meadow Dash (four runners), Echo Stones and the Bond games.
- **Portrait images** everywhere else: lists, pickers, small cards and the Journal.
  - **Every look and secret variant** is rendered at build time by the game's own renderer (`npm run art:portraits`: Playwright in the installed Chrome) and precached.
  - **Other life stages and faces** are rendered on the phone the first time they're needed and cached in IndexedDB (keys `wildsong/portrait/…`).
  - Classic shows until an image is ready.

### 3.4 Scenes
- **Layers, back to front:**
  1. the back plate (sky, distance);
  2. the mid plate (the set);
  3. the 3D canvas (live props, the monster, live water and foam);
  4. the front plate (overhanging leaves, ferns, bands of mist);
  5. the effects layer (Blender-baked splash, droplet and mist flipbooks, plus sparkles);
  6. the UI.

  Any layer may be a short loop where something moves (falling water behind, a turning windmill).
- **Plates:** rendered in Blender EEVEE at 1080×1440 (3:4 portrait, the clip card's shape), with alpha where needed, encoded to WebP. Loops follow the rules in `tools/blender/encode.ts`.
- **`scene.json`:**
  - the camera (lens, position, rotation, sensor) and the ground height;
  - named anchors (`rockTop`, `splashPoint`, `entrance`, …);
  - the key, fill and rim lights (direction and colour) and the shadow colour.

  The 3D camera *is* the Blender camera, so the monster stands exactly where the plate says.
- **Camera moves are crops:**
  - A pan or push-in moves a crop window over the plates and sets the same crop on the 3D camera (`PerspectiveCamera.setViewOffset`), so everything stays locked together.
  - Plates are rendered with enough margin for it.
- **Timelines are data:** one per ending, holding the crop keys, the monster's clips and faces, prop animations, effect cues and sound markers.
- **Drill endings (five):**
  - **Great** (Perfect, Superb and Great; Superb and Perfect add a growing flourish);
  - **Success** (Good and Success);
  - **Cheat**, **Fail** and **Slacked**.

  Each is 3–5 s and tap to skip. The speed setting scales them, and speed 0 skips straight to the result.
- **Body plans adapt the action:** a floater hovers low on the rock and is pressed down; a serpent coils; a bird grips and tucks its wings; a shelled monster pulls in. The clip contract (§5) carries this.
- **No motion:** with Reduce motion, offline before the scene has downloaded, or with no WebGL, the player shows the scene's final still with the monster posed in it (or the Classic doll over the still), then the result.
- **Previews:** Settings → Sandbox → Preview scenes plays any scene and ending with any breed or secret variant, and changes nothing (like today's arrival previews).

### 3.5 Lighting match
The monster's toon shader takes the key, fill and rim light from `scene.json`. On the ranch stage they come from the season and the weather. So a monster at golden hour is warm, under the waterfall it's cool and wet, and at night it's moonlit.

### 3.6 Budgets
The owner set these targets on Nov 1, 2026 (ART_2_DETAIL §2 and §5) and approved the look they buy with Puddlepup on Nov 7, 2026. Every look ships as two files in `public/models/monsters-ultra/`: the **Ultra** model `<look>.glb` and its **Lite** copy `<look>.lite.glb`, for phones set to Lite effects. Both are runtime-cached, never precached. `tools/art/ultra.ts` refuses to ship a look over budget (it exits with the reasons), and `src/art/ultraLooks.test.ts` checks every shipped one.

**Per monster:**

| Item | Ultra (`<look>.glb`) | Lite (`<look>.lite.glb`) |
|---|---|---|
| Triangles | ≤ 100,000 (aim 60–80k) | ≤ 12,000 in all: the membranes keep a quarter of theirs, props up to 2,400 (a recipe's `LITE_PROPS_TRIS` raises it, at most 60%), the body takes the rest |
| Fur | ≤ 5,000 standing locks; ≤ 6,000 fur cards in ≤ 3 layers | no cards and no tuft, unless the recipe's `LITE_KEEP` keeps them (they count in the 12k) |
| Body atlas | 2048² colour, normal and ORM, KTX2 ETC1S; a glow mask in the ORM's alpha where the breed glows | 1024² WebP at quality 78 / 84 / 76 (colour / normal / ORM), the normal map lightly blurred first (1.5 px) |
| Each secret variant | its own 2048² colour map on the same UVs (normal and ORM shared), plus any props only it wears | its own 1024² colour map |
| UVs | ≤ 32 texels shared between faces in any mesh (the build stops above it) | the same UVs |
| Skeleton and clips | ≤ 64 deform bones (+ spring chains); the ★ clips, Battle 3D's moves and the blink (§5) | the same skeleton and clips |
| Face | baked on the eye lenses and the body, with blink bones (ART_2_DETAIL §9.1) | the same |
| Cinematic set (Monster Card, cutscenes) | 2048² head set + 2048² face sheet + ≤ 24 morph targets (not built yet) | none |
| Size | built `HEIGHT_UNITS / 150` m tall, so every breed stands at its true size beside Puddlepup | the same |
| Download | **≤ 8 MB** (batch 1: 4.0–5.9 MB) | **≤ 1.5 MB** (batch 1: 1.0–1.4 MB) |
| Graphics memory | ≈ 15 MB in battle with KTX2 (+ 15 MB for the cinematic set) | ≈ 4 MB |

ART_2_DETAIL §5.1 also has a **High** column (≤ 40,000 triangles, ≤ 3.5 MB). No High copy is made yet: every setting but Lite draws the Ultra file.

**Art 2.0's monster budget** (the models normal play still shows, in `public/models/monsters/`): ≤ 700 KB per look, ≤ 12,000 triangles, ≤ 64 deform bones, WebP textures ≤ 1024² (glow ≤ 512², a variant's set ≤ 250 KB) and a face sheet ≤ 512². They retire when the ranch switches to Ultra.

**Everything else** (tests and `check:build` enforce these where they can):

| Item | Budget |
|---|---|
| One effect flipbook | ≤ 250 KB WebP |
| The art3d chunk (three, the loader, the decoder, our code) | ≤ 300 KB gzipped, lazy (a one-time download budget, not a performance one; raised from 200 with the owner on Oct 29, 2026, as P1 landed at ~230) |
| One plate | ≤ 300 KB WebP |
| One loop | ≤ 1 MB H.264 |
| A scene's `props.glb` | ≤ 300 KB |
| A whole scene | ≤ 1.5 MB |
| The install (precache) | grows by ≤ 2 MB over the whole of Art 2.0 (code, the fallback stills, the breed portraits) |
| Frame rate | 60 fps on a Galaxy S25 Ultra on the ranch (the monster plus keepsakes), in battle (two monsters, Flashy effects) and in Meadow Dash (four runners); on Ultra still 60 after 10 minutes of battle, with dynamic resolution (ART_2_DETAIL §3.6, §5.2); Lite holds 30 fps on a weak phone |
| Memory | about 1 GB of graphics memory for the whole game on Ultra, to start (ART_2_DETAIL §6); models and textures are disposed when a screen closes |

### 3.7 Offline and caching
- **Precache:** in `vite.config.ts`, `models/**` and `baked/scenes/**` leave the precache (`globIgnores`), except the fallback stills and the breed portraits.
- **Runtime cache:** a cache-first rule keeps every model, plate and loop once it has been downloaded, so the game keeps working offline afterwards.
  - A model's sidecar (`models/**/*.json`) is fetched network-first, and an Ultra `.glb` is asked for as `<look>.glb?v=<build>` (the sidecar's `build`, a short hash of the file), so a phone that cached an older model gets the re-shipped one.
- **Download all art:** P19 adds this to Settings (showing its size), for playing offline from day one.
- **Repo size:** commit art files only once they're final for that milestone, never scratch renders, to keep the repo's history small.

## 4. Body plans, rigs and batches

The Batch column is §8's batches (B1–B7). The quadrupeds are built on the Ultra plan `tools/blender/monsters/plans/quadruped.py`, whose options (RECIPE.md) cover the long necks, hooves, hocks, manes, trunks and wings below. The biped plan `plans/biped.py` exists (Nov 12): IK legs and arms, all 32 clips, eight strike styles. The floater plan `plans/floater.py` is under way (Nov 12): its rig and all 32 clips are written and tested on a stand-in, and no breed uses it yet. Each other plan is written when its first batch starts.

| Plan | Breeds (looks) | Rig notes | Batch |
|---|---|---|---|
| quadruped | Puddlepup · Tumblefox, Cinderlynx, Starhowl, Nimbusheep, Rammerjack · Stripeneck (31), Petalphant, Cobblemaw, Hearthwing (young, grown) | spine, neck, head, jaw, two-bone ears, four three-bone legs, a tail chain. Options: a long neck and wings (grown Hearthwing), a longer 4–5 bone neck and hooves (Stripeneck), a trunk chain (Petalphant) | P1 · B1 · B2 |
| biped (`plans/biped.py`, built) | Quillion, Grumblestone, Pluckrex (young, grown), Gloomgrin · Plumdrake (32) | hips, spine, neck, head, jaw, arms with hands, legs with feet. Options: a tail, small wings (Gloomgrin), big wings and a tail puff (Plumdrake), a cape chain (Quillion), hulking and squatting proportions | B3 |
| floater (`plans/floater.py`, under way) | Wishlume, Ashwraith, Zipwisp, Mirrorkin, Frostlance | a hover root, a short squash chain, optional little arms or floating hands, trailing chains (tassel, wisps, zigzag tail, handle), fins and a fluke (Frostlance) | B4 |
| shelled | Moatshell, Reefclaw | a rigid shell, head and neck, four stubby legs. Crab option: six legs, two claws (one big), eye stalks | B5 |
| blob | Bloatoad, Scrollopus | a squash chain for the body, a throat sac (Bloatoad), six to eight tentacle chains (Scrollopus) | B5 |
| serpent | Coilfang, Aurelwyrm | a 12–16-bone spine moved along a spline, head and jaw. For Aurelwyrm, which floats: ribbon-fin chains, whiskers, antlers | B6 |
| avian | Galeheron, Paladove (young, grown) | long legs, a neck chain, head, beak, two wings (four on grown Paladove), tail and crest plumes | B6 |
| insect | Nibblegrub (and its cocoon), Velvesper | a segment chain with tiny legs, antennae; moth wings (Velvesper) | B7 |
| construct | Gearhoot, Lootlid | Gearhoot: an owl body with gear-feather wings, a turning key and a monocle. Lootlid: a box body whose lid is the jaw, stubby legs, a tongue chain | B7 (Gearhoot), B5 (Lootlid) |

## 5. The clip contract

Every look has every clip below, under exactly these names.
- **Interpretation:** a body plan may play a clip its own way (a floater "walks" by gliding, a serpent "sits" by coiling) or alias it to another clip if that looks right. The name must still exist.
- **Metadata:** each clip carries
  - loop or one-shot (and the frame a one-shot holds on);
  - its duration;
  - the root speed, for clips that move;
  - markers (`step`, `impact`, `release`, `land`) for sound and effects.
- **Faces:** a clip can set a face at a marker.

★ = built in P1 for Puddlepup · ◆ = added in P2 (now with the walkable farm) · everything else comes with the batches and the scenes that need it. The Ultra looks also carry Battle 3D's moves (`strafe_l` / `strafe_r`, `sidestep_l` / `sidestep_r`) and `blink` (ART_2_DETAIL §9.1).

| Group | Clips |
|---|---|
| Ranch life | idle★, idle_happy★, idle_tired★, idle_sad★, idle_sick★, sleep★, eat★, pet★, look_around★, hop★, celebrate★, sulk |
| Moving | walk★, run★, jump, climb_on◆, sneak◆ |
| Scenes | sit_down★, sit★, brace_in◆, brace◆, shiver◆, shake_dry◆, proud_pose◆, slip_fall◆, surface_dizzy◆, dizzy★, get_up◆, doze◆, think, meditate, pull, push, carry, heave_throw, toss, dodge, duck, catch, bonk |
| Battle | battle_idle★, step_fwd★, step_back★, dash★, strike★, bite, slam, charge, tail_whip, cast★, breath, shoot, guard, shove★, hit★, hit_heavy★, ko★, win★, dawdle |

**Faces:** neutral, happy, tired, stressed, sad, angry, sleepy, sick, strain, dizzy and surprised, with sparkle and blink on top.

**Battles until P11:** map the arena's current fighter flags (lunge, busy, dawdling, stunned, hit, ko, win) and its moves (walking in and out, dashes, pushes) to the nearest ★ clips. P11 gives every technique its own motion.

## 6. The review loop (Claude can't see while it builds)

This is how every Ultra monster is made and checked, as run in batch 1 (Nov 7, 2026). Scenes and clips follow the same idea: sheets, fresh eyes, then the owner.

**For each breed:**
1. **The recipe.** A builder reads the breed's reference pictures and card in `chatgpt/monsters/<NN>-<breed-id>/` (the "which source wins" rules of §0 and `chatgpt/FOR-CLAUDE-CODE.md` §2) and writes `tools/blender/monsters/breeds/<breed>_ultra.py` by the contract in `breeds/RECIPE.md` (a grown form: `<breed>_grown_ultra.py`).
2. **Shape previews** (`npm run art:shape -- <breed>`, about a minute in flat colours, in `art-review/<breed>-shape/`): repeat until the shapes, proportions and height match the turnaround. No full build before that.
3. **The full build**, always through the build-slot lock, which lets at most two full builds run at once on this PC: `tools/blender/slot.sh npm run art:ultra -- <breed> --blender`, in the background with a log. It builds, bakes, rigs, makes the clips, exports and ships the Ultra model, its Lite copy and the sidecar. It stops, with the reason in words, when a budget (§3.6) is broken or two faces share texels.
4. **The sheets.** The Blender sheets in `tools/blender/out/<look>/review/` (turnaround, head, key poses of the clips, each variant) and the film sheet from `npm run art:ultra-review -- <breed>` in `art-review/<breed>-ultra/`: the game's own renderer and part rules, every view beside its reference picture, the clips' key frames, every variant, the Lite copy, and 64 / 100 / 200 px. The builder looks at every sheet; the film sheet is the one that counts.
5. **Fresh-eyes review.** A new agent each round, one that hasn't seen the work, judges the sheets against the reference pictures, the card, the CONTENT brief and palette, and §2. It answers the same two questions every time, each **yes, partly or no**:
   - **detail and design:** does it match the pictures?
   - **64 px:** does it read at a glance?

   It also checks deformation in the clips and that the design is not too close to a famous character. It lists what landed since the last round and the top fixes, most important first. Its verdict is added to `art-review/<breed>-ultra/verdicts.txt`.
6. **Rounds.** Fix the real problems and build again: **up to 3 review rounds**. After round 3 comes **one polish pass for defects only** (a geometry or texture fault, a tear when a joint bends; no taste changes), which the Claude session running the batch checks on the sheets itself, without a fourth reviewer. Taste items still open go to the owner as known issues in PROGRESS.

**For each batch:**
7. **Lineup:** `npm run art:lineup -- puddlepup <breed…>` puts every finished look side by side at true size, Puddlepup first (the approved yardstick), in `art-review/lineup/`, so the style doesn't drift.
8. **Budgets and tests:** `src/art/ultraLooks.test.ts` (the files, clips, variants and budgets of every look in the registry) and `npm run verify`.
9. **The owner decides.** The batch goes into the game (Lab → 3D Gallery and Battle 3D, §3.3). The owner hears which files to open (the film sheets and the lineup), PROGRESS says how each new breed should look and move, and the phone checklist names what to look at. Their notes are applied before the next batch ships.

**The quality bar.** A breed is done when:
- it's clearly its pictures from every angle, and charming at 64 px;
- it shows no faceting at phone size;
- its joints bend cleanly in every clip;
- its feet meet the ground, with a contact shadow, and it stands at its true height beside Puddlepup;
- its motion has anticipation, follow-through and lag, and its loops are seamless;
- its face reads at 100 px (Ultra faces are baked for now; expressions come later, ART_2_DETAIL §9.1);
- its painted textures and markings read clearly at phone size and match its brief, with no specks, glitter or dark seams (no shared or unbaked texels in the atlas);
- it's lit by its scene;
- it runs at 60 fps on the S25 Ultra, and its Lite copy still reads as the breed.

## 7. Scenes

### 7.1 Drill scenes (P2, P13–P15)
- **Ideas:** each drill's first-pass ideas are in VISUAL_UPGRADE_PLAN §4 (V4). Keep them, and add a **Slacked** ending to each (the monster wanders off to nap, eat or play).
- **Places:** each drill is a real place around the vale.
- **Body plans:** every drill works for all nine.
- **Replacing the vignettes:** each scene replaces that drill's prop vignette in `DrillResult`. The old vignette stays for drills not built yet, and as a fallback.

**Waterfall Stand (P2, the pilot scene; now part of roadmap step 2, the walkable farm).**
- **The set:** a mossy rock in a pool at the foot of a waterfall, with cliffs, ferns and mist.
- **The action:**
  - The monster climbs onto the rock and braces.
  - The water really pours onto its head and back, sheets off its sides and splashes around it.
  - It gets wet: darker, glossier, with drops beading.
- **Success:** it endures with its eyes squeezed shut; the flow eases; it shakes itself dry.
- **Great:** it holds a proud pose in the full torrent; a glint; birds scatter. Perfect adds a rainbow in the mist.
- **Fail:** the torrent knocks it off with a big splash, and it surfaces dizzy with a lily pad on its head.
- **Cheat:** it sits beside the falls under a leaf umbrella, pretending. Wren's line notices.
- **Slacked:** it dips a toe, decides against it, and naps in the sun on the bank.

### 7.2 The farm (P10)
- **The ranch home stage**, rebuilt at P2's quality: the run-down homestead of CONTENT §1 (barn, fence, path, the big tree, fields, hills, mountains).
  - Every season and weather (Sunny, Cloudy, Rain, Storm, Snow) as plate variants, with live rain, snow, lightning and drifting leaves.
  - The ranch upgrades show once bought (Cozy Barn, Training Yard, Tide Pool, Lantern Garden).
  - The keepsakes (CONTENT §4.2) are live 3D props the monster sometimes uses: it kicks the ball, naps in the hammock, paddles in the tub.
- **The four arrival scenes,** rebuilt on the new farm with the live monster: the hello really runs up the path; sad; abandoned in the rain; the note on the gate. They replace `ranch_scenes.py`'s clips.
- **The title screen:** the farm at golden hour with a monster or two.

### 7.3 Battles (P11) and visible attacks (P12)
- **The arena:** the Breeders' Guild arena by the river (CONTENT §1). A packed-earth ring with rope-fence posts at the walls, banners and a crowd silhouette layer, with the river and Tunewick behind. Seasons and weather.
- **The camera:**
  - The 3D monsters live in the arena camera (M10).
  - The world-unit mapping stays exact for the effects layer and the damage numbers; a test checks feet stay on the floor line at every zoom.
  - A long lens keeps depth distortion small.
- **Motions:** every technique gets one (strike, bite, slam, charge, tail_whip, cast, breath, shoot, guard, shove).
  - They're assigned by rules like V1's elements (family × range × breed, plus overrides).
  - A CONTENT column and a test keep data and doc in step.
- **Presentation:**
  - entrances, hit reactions by body plan, knockback slides with dust, KO flops and wins;
  - tournament walk-ons and the podium;
  - Versus, the Battle Lab view and the Effects Lab use all of it.
- **P12 (the old V2 plan):** a recipe for each of the 294 techniques, built from the new motions and the effects layer, plus bespoke 1–2 s cinematics for Signatures and Specials. The big elemental effects (fire, water, ice, smoke, lightning) are Blender-baked flipbooks; V1's code primitives add sparks and flashes.

### 7.4 Life moments (P16)
- **New monsters:**
  - New Game's first monster (the Market gift, or the Shrine);
  - the Shrine awakening: the stone sings, light pours out, the monster forms;
  - a Market purchase, and Pell's Fusion "Meet".
- **Growing up:** the grow-up moment (Hearthwing, Pluckrex, Paladove), and Nibblegrub's cocoon becoming Velvesper.
- **Endings:** the Farewell (retired, passed or wandered), the Memorial, the Heartstone and the Freezer.

### 7.5 Bonds and Odd Jobs (P17)
- **Bond games:** Fetch, Hide-and-seek, and the Shopping trip down Market Lane.
- **Odd Jobs:**
  - Echo Stones: the monster sits beside the stones, humming and reacting;
  - Meadow Dash: four 3D runners;
  - Turnip Sort's chute.

### 7.6 Places (P18)
- **Tunewick** and its screens: the Shop, Market, Guild, Mailbox, the Odd Jobs board, Pell's Lab and the Shrine of Echoes.
- **Journeys** at the five mentor sites (CONTENT §7): the four-beat screen, and each site's own Trial arena.
- **Expeditions** (CONTENT §8): the four node maps, with the monster on them.
- **The credits roll.**

## 8. Milestones

Each P is one milestone in the CLAUDE.md workflow:
1. plan mode first;
2. build in steps, with tests;
3. `npm run verify`;
4. PROGRESS;
5. commit `Art P<n>: <summary>` with a minor version bump, push, and check the deploy;
6. the phone checklist, then stop.

**The owner's roadmap (Nov 2026)** regroups what follows into four steps:
1. **Every monster in 3D:** the batches of 5 below (they replace P3–P9). Each batch is one milestone with a minor version bump (batch 1: v1.23.0).
2. **The walkable 3D farm:** P10, with P2's Waterfall Stand folded in. The ranch, the Monster Card and the cups switch to the Ultra monsters here.
3. **3D event scenes.**
4. **The 3D duel as the real battle.**

How P11–P19 fit steps 3 and 4 is settled when they start.

**P0 · One breed per monster** (rules and saves, no art). *Done when every monster is one whole breed everywhere.*
- **The rules:** no sub breed anywhere. No sub palette, accent part or quirk technique; no blended stats, grades, guts or lifespan. A monster's name is its breed's name (secret variants keep theirs).
- **The Shrine:** the sub step goes, but every random draw stays in the same order, so each phrase still makes the same breed, stats and personality.
- **The screens:** the Lab editor, the Market, the Encyclopedia, the Library, share codes and the Classic drawings no longer show or pick a sub.
- **Saves:**
  - Every mixed monster (active, Freezer, Library, Memorial) becomes its main breed and keeps its current stats, grades, techniques and lifespan.
  - Bump `SAVE_VERSION` with a migration and tests.
  - Old share codes and files still import.
- **The "pure" bonuses** (+10% lifespan, Signature access, the Pure badge): propose what happens now that every monster is one breed, check it against the §26 balance sims, and ask the owner before changing a rule.
- **Secret variants** (CONTENT §12) stay as special looks of their breed.
- **Docs:** GAME_DESIGN §14.1, §14.3, §19 and §22; CONTENT §2 (the accent column) and §12; BUILD_PLAN; PROGRESS.

**P1 · Pilot monster (Puddlepup).** *Done when the owner loves it on the phone.*
- The pipeline (§3.1), the runtime (§3.2), and the quadruped rig with the ★ clips.
- Puddlepup, with its painted textures and face sheet.
- The Models viewer: Monster Lab → Models, with any breed (Classic for those not built yet), stage, face and clip; turn it; an fps counter.
- Settings → Graphics → Monsters (3D / Classic).
- Puddlepup in 3D on every screen (§3.3).
- The review loop (§6).
- The docs: CLAUDE.md, VISUAL_UPGRADE_PLAN §0, a new Art 2.0 section in BUILD_PLAN, GAME_DESIGN §22, CREDITS, the style text in CONCEPT_PROMPTS (§2.4), and `.gitignore` entries for `concept/` and `art-review/`.

**P1.1–P1.2 · Puddlepup at Art 2.1** (ART_2_DETAIL §9; Nov 2–7, 2026). *Done: the owner approved the look on Nov 7, 2026. Puddlepup is now the reference for every batch.*
- A1, the Ultra pipeline (`lib/surface.py`, `lib/bake.py`, `build_ultra.py`, `tools/art/ultra.ts`); A2, the film runtime (`src/art3d/perf/`), first in Battle 3D.
- Puddlepup rebuilt from its pictures with every ★ clip, Battle 3D's moves and Songheart Puddlepup, through the §6 review loop.

**P2 · Pilot scene (Waterfall Stand with Puddlepup).** *Moved into roadmap step 2, the walkable 3D farm (owner, Nov 7, 2026), so the batches no longer wait for it. Done when the owner signs it off.*
- The scene pipeline (§3.4, §3.5).
- Waterfall Stand with all five endings (§7.1).
- The ◆ clips and the wet look.
- `DrillResult` plays the scene, and the sound markers drive the drill cue.
- Sandbox → Preview scenes. Breeds without a model appear in the scene as Classic.

**Every monster in 3D: batches of 5** (roadmap step 1; they replace P3–P9's batches of 4). The owner, Nov 7, 2026: *"Create them the same way you have been, make them in batches of 5 for upload. After each finishes have an independent reviewer come in and check it against the photos and make suggestions; after you make 5 put them on the game and I will let you know if they are up to the quality I would like."*

35 looks in all: the 31 breeds after Puddlepup, 3 grown forms and Nibblegrub's cocoon. For each:
- the Ultra build (§3.1) and the §6 review loop;
- the Ultra clip set (the ★ clips, Battle 3D's moves and the blink; §5);
- its secret variants, if it has any;
- its Lite copy;
- a line in `src/art/ultraLooks.ts`, so it appears in Lab → 3D Gallery and in Battle 3D (§3.3).

Each batch ends with a lineup sheet and the owner's verdict on the phone.

| Batch | Looks |
|---|---|
| **B1** (v1.23.0): four-legged fur and wool | Tumblefox, Cinderlynx, Starhowl, Nimbusheep, Rammerjack |
| **B2** | Stripeneck, Petalphant, Cobblemaw, Hearthwing (young and grown) |
| **B3** | Quillion, Grumblestone, Gloomgrin, Pluckrex (young and grown), Plumdrake |
| **B4** | Wishlume, Ashwraith, Zipwisp, Mirrorkin, Frostlance |
| **B5** | Moatshell, Reefclaw, Bloatoad, Scrollopus, Lootlid |
| **B6** | Coilfang, Aurelwyrm, Galeheron, Paladove (young and grown) |
| **B7** | Nibblegrub and its cocoon, Velvesper, Gearhoot |

**P10–P12 · The farm and battles** (§7.2, §7.3).
- **P10:** the farm (roadmap step 2, with Waterfall Stand from P2).
- **P11:** battles.
- **P12:** visible attacks.

**P13–P15 · Drill scenes** (§7.1).
- **P13:** Acorn Shower, Log Toss, Target Toss.
- **P14:** Hill Sprints, Dodge the Gourds, Wind Chase.
- **P15:** Puzzle Stones, Moon Meditation, Plow Pull, Quarry Haul.

**P16–P18 · Every other scene.**
- **P16:** life moments (§7.4).
- **P17:** Bonds and Odd Jobs (§7.5).
- **P18:** places (§7.6).

**P19 · Final polish.** It ends at v2.0.0.
- A performance and size audit on the S25 Ultra and a mid-range profile.
- Download all art.
- Reduce motion and screen-reader labels everywhere.
- Remove what's dead: the old prop vignettes, the old Bonds clips and `ranch_scenes.py`. Classic monsters stay as the fallback.
- Rewrite GAME_DESIGN §21–§22; update README and CREDITS.
- The full e2e suite.

**After Art 2.0:** a new breed (such as the combo-only bull-warrior BUILD_PLAN mentions) is one short prompt: a recipe on an existing body plan, then the review loop.

## 9. Risks
- **A breed still looks off after three review rounds:** the defect-only polish pass (§6), then the owner's call on what's left; or re-run the fix with Fable 5.1, put its reference pictures (`chatgpt/monsters/<NN>-<breed-id>/`) beside the film sheet again, or simplify the design.
- **Style drift across batches:** the lineup sheet in every batch, with Puddlepup (approved Nov 7, 2026) as the reference.
- **Frame rate or heat on weaker phones:** the Quality tiers. Lite drops outlines and springs and caps at 30 fps, and Classic is always there.
- **Download size and repo history:** the budgets (§3.6), runtime caching, and committing finals only.
- **WebGL lost or unavailable:** fall back without an error to the portrait picture (or Classic if the picture is missing), and restore when the context returns.
- **Long sessions:** a big batch may not fit one session. Finish what's done cleanly (verify, PROGRESS, commit), say what's left, and the next prompt continues it.
