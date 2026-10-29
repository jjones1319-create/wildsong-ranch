# Art 2.0: Blender monsters and scenes

**Status:** written Oct 28, 2026. The owner approves it by running P0 and P1. This is the spec behind the prompts in `ART_2_PROMPTS.md` (repo root): one milestone each, P0 to P19.

**One breed per monster:** the main/sub mix system is retired (owner, Oct 28). Every monster is its own whole breed with one fixed design, and breeding makes another whole breed. P0 removes mixing from the rules and saves. That frees every breed to be designed and painted individually in Blender for the highest quality, with no recolouring and no swapped parts.

**The owner's goal:** rehaul the entire animation, make every monster significantly higher quality, make the farm and battle scenes higher quality, and then every other scene. For example, Waterfall Stand should look like the monster really is sitting on a rock under a waterfall, in a slight anime/cartoon style. The same goes for every other scene in the game.

**Blender creates everything you see.** It makes:
- the monster models, their skeletons and every animation;
- their faces (every expression);
- the scenes and the props;
- the big water, splash, mist, fire and smoke effects.

The game (three.js) only displays what Blender made. Code still draws the UI, the Classic fallback monsters and V1's small effect sparks.

**How it runs:** P0 retires mixing (rules and saves, no art). P1 builds one pilot monster. P2 puts it in the first real scene (Waterfall Stand). Nothing else starts until the owner has signed off both on the phone, because they set the look for everything after. Then come batches: the monsters by body plan, the farm, battles, the drill scenes, every other scene, and a final polish.

## 0. Decisions

| Question | Decision |
|---|---|
| What a monster is | A real 3D model built by Blender scripts from the breed's CONTENT brief and colours, exported as a small `.glb` and drawn live on the phone with our own cel shader (three.js). |
| One design per breed | Mixes are retired (P0), so each breed has one look (Hearthwing, Pluckrex and Paladove have a young and a grown one). Blender paints each breed's colours, markings and surface detail into its own textures; nothing is recoloured at runtime. The 21 secret-phrase variants (CONTENT §12) stay as special looks of their breed: an alternate texture set (and any small extra, like Town Crier Tumblefox's bell) on the same model. |
| Why live 3D and not pre-rendered frames | Drawn live, a model shows every face, grows with its life stage, follows taps, holds props, moves at 60 fps, takes each scene's light (warm at golden hour, soaked under the waterfall, moonlit at night) and works under any camera. Pre-rendered frames of 33 looks × ~50 animations would run to hundreds of MB and look the same in every scene. A breed's file is a few hundred KB. The same files can later walk into the owner's dungeon crawler, which already uses three.js. |
| Scenes | Built and lit in Blender and rendered as backdrop *plates*: two or three depth layers, plus a short loop wherever something moves. The camera, anchors and light are exported as JSON. Whatever the monster touches (the rock, the falling water, the log) is a live 3D prop, so the monster really sits on it, holds it or gets splashed by it. The monster is lit to match the plate. |
| Look | "Slight anime/cartoon" (§2). |
| Faces | Anime-style eyes and mouths made in Blender as a face sheet (every expression), shown on small patches of the 3D head. The game swaps cells of the sheet for expressions and blinks, and slides the pupils for glances. |
| Skeletons and motion | One rig template and one clip set per body plan (9 in all), shared by its breeds. The clip names are a contract (§5) that every scene can call. |
| The drawn (SVG) monsters | Stay, as the fallback (no WebGL, a model still loading, offline before its first download) and as a setting: Settings → Graphics → Monsters: **3D / Classic**. A breed without a model shows Classic. |
| Pilot breed | **Puddlepup** (the owner may swap it). It's the balanced starter most players meet first; its quadruped body plan serves 9 breeds; its round shapes suit the style; and a water monster suits the Waterfall Stand pilot. |
| New dependencies (approved by running P1) | `three` (runtime, in a lazy chunk) and a dev-only glTF optimiser (`@gltf-transform/cli` with meshopt). Nothing else without asking. |
| Concept art | Optional. If `concept/<breed-id>/` holds the owner's ChatGPT pictures, view them before modelling. They're reference only and never shipped. §2.4 has the new style text for those prompts. |
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

### 2.4 The new style text for ChatGPT concept pictures
P1 replaces the Style Guide in `docs/CONCEPT_PROMPTS.md` with this. The old one says "not anime". The owner can paste this one today:

```
You are making original concept art for "Wildsong Ranch", a cozy monster-raising game whose monsters are cel-shaded 3D characters. Style: clean cel-shaded character art with a slight anime touch: soft two-tone shading, a warm rim light, outlines in a darker tint of each colour (not black), big glossy expressive eyes with white highlights, rounded chunky appealing shapes with a slightly big head, and a clear readable silhouette. Warm, friendly storybook feel. Not realistic, not pixel art. Plain white background, no text, no logos, no watermark. The creature must be an original design: do not base it on, or make it resemble, any character from Pokémon, Digimon, Monster Rancher, Dragon Quest, Yo-kai Watch or any other franchise, and avoid their signature silhouettes. Use exactly the hex colours I give. I will ask for several images of the same creature in this conversation: keep its design identical across all of them.
```

## 3. Architecture

### 3.1 The pipeline (the owner's PC, headless Blender 5.2)

Blender runs headless only (CLAUDE.md, "Tools on the owner's PC"): `blender -b --factory-startup --python <script> -- <args>`, with every script pinned to the installed version's API.

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
- **Fallback:** Classic SVG when the setting says so, when WebGL fails, and while a model loads (it cross-fades in).

### 3.3 Where monsters appear
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
Tests and `check:build` enforce these where they can.

| Item | Budget |
|---|---|
| One look's `.glb` (mesh, rig, clips and textures, optimised) | ≤ 700 KB (aim for ~400 KB) |
| Textures | WebP inside the `.glb` (`EXT_texture_webp`), ≤ 1024×1024 base colour, ≤ 512×512 glow; a secret variant's set ≤ 250 KB |
| Triangles | ≤ 12,000 per look (aim for 6–9k) |
| Deform bones | ≤ 64 |
| Face sheet | made in Blender, inside the `.glb`, ≤ 512×512 |
| One effect flipbook | ≤ 250 KB WebP |
| The art3d chunk (three, the loader, the decoder, our code) | ≤ 300 KB gzipped, lazy (a one-time download budget, not a performance one; raised from 200 with the owner on Oct 29, 2026, as P1 landed at ~230) |
| One plate | ≤ 300 KB WebP |
| One loop | ≤ 1 MB H.264 |
| A scene's `props.glb` | ≤ 300 KB |
| A whole scene | ≤ 1.5 MB |
| The install (precache) | grows by ≤ 2 MB over the whole of Art 2.0 (code, the fallback stills, the breed portraits) |
| Frame rate | 60 fps on a Galaxy S25 Ultra on the ranch (the monster plus keepsakes), in battle (two monsters, Flashy effects) and in Meadow Dash (four runners); Lite holds 30 fps on a weak phone |
| Memory | models and textures are disposed when a screen closes |

### 3.7 Offline and caching
- **Precache:** in `vite.config.ts`, `models/**` and `baked/scenes/**` leave the precache (`globIgnores`), except the fallback stills and the breed portraits.
- **Runtime cache:** a cache-first rule keeps every model, plate and loop once it has been downloaded, so the game keeps working offline afterwards.
- **Download all art:** P19 adds this to Settings (showing its size), for playing offline from day one.
- **Repo size:** commit art files only once they're final for that milestone, never scratch renders, to keep the repo's history small.

## 4. Body plans, rigs and batches

| Plan | Breeds (looks) | Rig notes | Prompt |
|---|---|---|---|
| quadruped | Puddlepup · Tumblefox, Cobblemaw, Cinderlynx, Nimbusheep · Starhowl, Petalphant, Rammerjack, Hearthwing (young, grown) | spine, neck, head, jaw, two-bone ears, four three-bone legs, a tail chain. Options: a long neck and wings (grown Hearthwing), a trunk chain (Petalphant) | P1 · P3 · P4 |
| biped | Quillion, Grumblestone, Pluckrex (young, grown), Gloomgrin | hips, spine, neck, head, jaw, arms with hands, legs with feet. Options: a tail, small wings (Gloomgrin), a cape chain (Quillion), hulking and squatting proportions | P5 |
| floater | Wishlume, Ashwraith, Zipwisp, Mirrorkin, Frostlance | a hover root, a short squash chain, optional little arms or floating hands, trailing chains (tassel, wisps, zigzag tail, handle), fins and a fluke (Frostlance) | P6 |
| shelled | Moatshell, Reefclaw | a rigid shell, head and neck, four stubby legs. Crab option: six legs, two claws (one big), eye stalks | P7 |
| blob | Bloatoad, Scrollopus | a squash chain for the body, a throat sac (Bloatoad), six to eight tentacle chains (Scrollopus) | P7 |
| serpent | Coilfang, Aurelwyrm | a 12–16-bone spine moved along a spline, head and jaw. For Aurelwyrm, which floats: ribbon-fin chains, whiskers, antlers | P8 |
| avian | Galeheron, Paladove (young, grown) | long legs, a neck chain, head, beak, two wings (four on grown Paladove), tail and crest plumes | P8 |
| insect | Nibblegrub, Velvesper | a segment chain with tiny legs, antennae; moth wings (Velvesper) | P9 |
| construct | Gearhoot, Lootlid | Gearhoot: an owl body with gear-feather wings, a turning key and a monocle. Lootlid: a box body whose lid is the jaw, stubby legs, a tongue chain | P9 |

## 5. The clip contract

Every look has every clip below, under exactly these names.
- **Interpretation:** a body plan may play a clip its own way (a floater "walks" by gliding, a serpent "sits" by coiling) or alias it to another clip if that looks right. The name must still exist.
- **Metadata:** each clip carries
  - loop or one-shot (and the frame a one-shot holds on);
  - its duration;
  - the root speed, for clips that move;
  - markers (`step`, `impact`, `release`, `land`) for sound and effects.
- **Faces:** a clip can set a face at a marker.

★ = built in P1 for Puddlepup · ◆ = added in P2 · everything else comes in P3 (quadrupeds) and in each plan's batch.

| Group | Clips |
|---|---|
| Ranch life | idle★, idle_happy★, idle_tired★, idle_sad★, idle_sick★, sleep★, eat★, pet★, look_around★, hop★, celebrate★, sulk |
| Moving | walk★, run★, jump, climb_on◆, sneak◆ |
| Scenes | sit_down★, sit★, brace_in◆, brace◆, shiver◆, shake_dry◆, proud_pose◆, slip_fall◆, surface_dizzy◆, dizzy★, get_up◆, doze◆, think, meditate, pull, push, carry, heave_throw, toss, dodge, duck, catch, bonk |
| Battle | battle_idle★, step_fwd★, step_back★, dash★, strike★, bite, slam, charge, tail_whip, cast★, breath, shoot, guard, shove★, hit★, hit_heavy★, ko★, win★, dawdle |

**Faces:** neutral, happy, tired, stressed, sad, angry, sleepy, sick, strain, dizzy and surprised, with sparkle and blink on top.

**Battles until P11:** map the arena's current fighter flags (lunge, busy, dawdling, stunned, hit, ko, win) and its moves (walking in and out, dashes, pushes) to the nearest ★ clips. P11 gives every technique its own motion.

## 6. The review loop (Claude can't see while it builds)

A breed, scene or clip isn't done until it has been through all six steps.

1. **Blender sheets** in `tools/blender/out/`:
   - a turnaround (front, ¾ front, side, ¾ back, back);
   - the faces;
   - texture close-ups (head, body, markings, any glow);
   - its secret variant, if it has one;
   - an 8-frame strip of every clip.

   Look at every sheet. Fix shape, proportion, deformation (no collapsing joints, no parts passing through each other) and timing.
2. **In-game sheets** (`npm run art:review`): Playwright in the installed Chrome renders the Lab's Models viewer and the real screens at 412 px wide into `art-review/` (gitignored). They show the same angles and faces, the secret variant (if any), six key frames of the main clips, the ranch stage and a battle. The game's renderer decides the final look, so this is the sheet that counts.
3. **Fresh-eyes review:** a subagent that hasn't seen the work gets the in-game sheets, the breed's CONTENT brief and palette, §2 and any concept pictures. It lists what's off:
   - off-brief or off-style;
   - ugly deformation;
   - unreadable at 64 px;
   - too close to a famous character.

   Fix the real problems; don't chase taste nitpicks.
4. **Budgets and frame rate** (§3.6) are checked, and the art tests pass.
5. **Lineup:** every batch ends with a lineup sheet of every finished breed side by side, in the same light and scale, Puddlepup first, so the style doesn't drift.
6. **For the owner:**
   - Name the files of the final sheets (the in-game sheets and the lineup) in the chat, so they open in VS Code with a click.
   - PROGRESS says how each new breed should look and move.
   - The phone checklist names what to look at.

**The quality bar.** A breed is done when:
- it's clearly its brief from every angle, and charming at 64 px;
- it shows no faceting at phone size;
- its joints bend cleanly in every clip;
- its feet meet the ground, with a contact shadow;
- its motion has anticipation, follow-through and lag, and its loops are seamless;
- every face is distinct at 100 px;
- its painted textures and markings read clearly at phone size and match its brief;
- it's lit by its scene;
- it runs at 60 fps on the S25 Ultra.

## 7. Scenes

### 7.1 Drill scenes (P2, P13–P15)
- **Ideas:** each drill's first-pass ideas are in VISUAL_UPGRADE_PLAN §4 (V4). Keep them, and add a **Slacked** ending to each (the monster wanders off to nap, eat or play).
- **Places:** each drill is a real place around the vale.
- **Body plans:** every drill works for all nine.
- **Replacing the vignettes:** each scene replaces that drill's prop vignette in `DrillResult`. The old vignette stays for drills not built yet, and as a fallback.

**Waterfall Stand (P2, the pilot scene).**
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

**P2 · Pilot scene (Waterfall Stand with Puddlepup).** *Done when the owner signs it off. From then on, P1 and P2 are the reference for the look.*
- The scene pipeline (§3.4, §3.5).
- Waterfall Stand with all five endings (§7.1).
- The ◆ clips and the wet look.
- `DrillResult` plays the scene, and the sound markers drive the drill cue.
- Sandbox → Preview scenes. Breeds without a model appear in the scene as Classic.

**P3–P9 · Monsters by body plan** (§4). For each breed:
- the full §3.1 build and the §6 review loop;
- every §5 clip for its plan (P3 also finishes Puddlepup's, and adds Songheart Puddlepup);
- its secret variant, if it has one;
- live everywhere, and checked in Waterfall Stand.

Each batch ends with a lineup sheet.
- **P3, quadrupeds 1:** Tumblefox, Cobblemaw, Cinderlynx, Nimbusheep.
- **P4, quadrupeds 2:** Starhowl, Petalphant, Rammerjack, Hearthwing (young and grown).
- **P5, bipeds:** Quillion, Grumblestone, Pluckrex (young and grown), Gloomgrin.
- **P6, floaters:** Wishlume, Ashwraith, Zipwisp, Mirrorkin, Frostlance.
- **P7, shelled and blobs:** Moatshell, Reefclaw, Bloatoad, Scrollopus.
- **P8, serpents and birds:** Coilfang, Aurelwyrm, Galeheron, Paladove (young and grown).
- **P9, insects and constructs:** Nibblegrub, Velvesper, Gearhoot, Lootlid, and the cocoon.

**P10–P12 · The farm and battles** (§7.2, §7.3).
- **P10:** the farm.
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
- **A breed still looks off after two rounds of feedback:** re-run the fix with Fable 5.1, give it the concept pictures, or simplify the design.
- **Style drift across batches:** the lineup sheet in every batch, with P1 and P2 as the reference.
- **Frame rate or heat on weaker phones:** the Quality tiers. Lite drops outlines and springs and caps at 30 fps, and Classic is always there.
- **Download size and repo history:** the budgets (§3.6), runtime caching, and committing finals only.
- **WebGL lost or unavailable:** fall back to Classic without an error, and restore when the context returns.
- **Long sessions:** a big batch may not fit one session. Finish what's done cleanly (verify, PROGRESS, commit), say what's left, and the next prompt continues it.
