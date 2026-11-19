# The 3D world

*The spec for ART_2_PLAN roadmap step 2 (set Nov 18, 2026, at v1.27.0). W0 (groundwork) is done; its results are in §10. C1 is next. Each phase starts in plan mode, and its task list goes into `BUILD_PLAN.md` under "The 3D world".*

## 0. The owner's direction (Nov 18, 2026)

Wildsong Ranch becomes a **fully 3D game**. The order the owner gave:
1. **The city first.** You walk through Tunewick with your monsters and go to the stores. Tunewick is built from **Ashbrook**, the walled town in the owner's other game, *Gloamvault Open World*.
2. **Out the gates.** Walk up to a city exit, press A, and step out into the land around the town. From there you can walk to your ranch.
3. **The ranch, the same way.** A large, open ranch you roam freely, with farming land, a river to fish in, and "anything that makes the game better". If there's no free model of a whole ranch, build one.

The owner's answers:

| Question | Answer |
|---|---|
| Who walks? | **You, as a keeper.** Start with Gloamvault's hero as a stand-in. A character creator, where players make and edit their own keeper, comes later. |
| Upright or sideways? | **Both.** The owner may later switch the whole game to sideways, so build the 3D screens so that's easy. |
| Stores | **Walk up to the door and press A**, which opens today's store screen. Interiors come later. |
| Time | **The week stays the game's turn** (§6). |
| Weather | **It stays**, live in the world, with **more extreme weather later**. |

## 1. The sources

### Gloamvault Open World
- **Where it is:** `C:\Users\jjones1\Desktop\Claude\Gloamvault Open World` (a Unity 6.3 game), pinned at commit `588c001` (0.14.1, Nov 7, 2026; the working tree was clean).
- **It's the owner's own game.** Every town and land piece is built by script.
- **We copy a snapshot into this repo** and never read the sibling folder during a build: GitHub's builders can't see it.
- **The snapshot** (`npm run world:import`; `-- --check` re-hashes it):
  - The data and models are in `tools/world/gloamvault/`: `land/`, `kit/`, `hero/`, and `people/` (the `npc-*` townsfolk only). `SOURCE.json` records the commit and every file's sha256.
  - The kit's Blender scripts are in `tools/blender/world/gvkit/`. One `# WS:` patch in `lib/common.py` sends their outputs to `tools/blender/out/world/gvkit/`.
  - `tools/world/snapshot.test.ts` fails if a file drifts.
  - To take a newer Gloamvault, run `npm run world:import -- --repin` and update `PINNED_COMMIT`.

| What | Where (in Gloamvault) | Notes |
|---|---|---|
| Town and land layout | `content/world/land/vale.json` (456 KB), from `tools/content/gen-world-land.ts` | areas, hills, brook, pond, roads, buildings, props, woods, scatter rules, wildlife |
| Kit (buildings, props, trees, rocks, farm pieces) | `client/public/models/env/kit_vale.glb` + manifest `vale.json` | 189 pieces, 29,271 tris, vertex colour only, no textures. Built by `tools/blender/env/build_kit_vale.py`; needs `lib/{common,toon,export,render}.py` + `palette.json` |
| The ground | `unity/.../Runtime/World/Land.cs` (839 lines: heights about 300, surface about 370) + `LandData.cs` | Unity-only. Must be ported (see §4). |
| The hero (the keeper stand-in) | `client/public/models/hero/hero_broad.glb`, `hero_slight.glb` (1.36 MB each), `hero_clips.glb` (1.98 MB), `manifest.json`, `clips.json` | two body frames; face presets as shape keys; skin, hair and eye colour lists; hair and brow parts. Clips: Idle, Walk (1.07 m/s), Run (3.6 m/s), Interact, SitRest, Jump, Crawl, Climb… Built by `tools/blender/hero/` |
| Townsfolk outfits on the hero body | `tools/blender/monsters/build_humanoid.py` (`npc-*` variants) → `client/public/models/monsters/humanoid.glb` (6.6 MB, all variants) | includes **npc-farmer** (`v_farmer`, line 948), shopkeeper, smith, priest, innkeeper, banker, merchant, villagers, lamplighter |
| Animals | `client/public/models/monsters/manifest.json` | cow 2,570 tris, hen 1,120, rabbit 580, deer 2,258, bird 290, horse 2,930, goat 2,578 (ordinary animals) |
| Pictures | `unity/shots/town-*.png`, `vale-*.png` | |

- **Credits:** the hero bodies come from Blender Studio's **Human Base Meshes**, which are CC0. Log them in `CREDITS.md` when the keeper ships.
- **The base mesh file:** that bundle (48 MB) is not in the Gloamvault folder. It's at `C:\Users\jjones1\Desktop\Claude\Dungeon Crawler\art\ref\human-base-meshes\human_base_meshes_bundle.blend` (also in `ProjectAscend`). It's only needed to rebuild a body from scratch.

### Free CC0 kits for the ranch (researched Nov 18)
There is **no complete free ranch or farm map under CC0**. We'll assemble the ranch from Gloamvault's farm pieces, our own Blender pieces, and at most one or two CC0 kits. Mixing more than that looks patchy.

| Kit | Licence | What it adds | Notes |
|---|---|---|---|
| Quaternius **Ultimate Crops** | CC0 (https://quaternius.com/packs/ultimatecrops.html) | 102 crops, **5 growth stages** | flat colour, untextured. Fits our vertex-colour look. |
| Quaternius **Farm Buildings**, **Ultimate Nature**, **Stylized Nature MegaKit** | CC0 (https://quaternius.com/packs/farmbuildings.html) | barns, silo, fences, trees, rocks | |
| Quaternius **Animated Fish** and **Cute Fish** | CC0 (https://quaternius.com/packs/animatedfish.html, `.../cutefish.html`) | animated fish, rods, lures | |
| Kenney Nature / Survival / Food kits | CC0 (https://kenney.nl/support) | nature filler, food props | palette texture; bake it to vertex colour |
| KayKit Forest Nature, Medieval Hexagon | CC0 (https://kaylousberg.itch.io/kaykit-forest) | trees, mills, river pieces | gradient atlas |
| Poly Haven, ambientCG | CC0 | sky HDRIs (lighting reference) | realistic; use for light only |

- **Avoid:** Automata "Lowpoly Farm" (its licence field says CC BY), xra7en (CC BY), mcrafterzz ("use however you want" isn't CC0), Poly Pizza's Google items (CC BY) and Avramania Premium (royalty-free).
- **Avramania's free pack** is CC0, but the uploader is new. Prefer Quaternius.
- **Rules:** paid tiers need the owner's yes. Log every kit in `CREDITS.md`.

## 2. The keeper (stand-in now, creator later)

- **Now:** the hero body with the **npc-farmer** outfit, one fixed look, playing the hero's Idle, Walk, Run and Interact clips.
  - Load it in the city and the world only; it's never precached.
  - This first look adds nothing to the save.
- **Later (the creator):** players make and edit their keeper: body frame, face preset, skin, hair, eyes, outfit.
  - The manifest already lists these choices.
  - Like monsters (owner must-have), **the keeper can be edited at any time**, from the menu.
  - The look goes in the save (`SAVE_VERSION` bump, migration, test).
- **Names:** Gloamvault's NPC names and wares don't come across. Wildsong's keepers (Basil, Dr. Pell…) wear the townsfolk outfits.

## 3. The city: Tunewick, built from Ashbrook

- **The town:**
  - Walls x 400–560, z 528–722 (160 × 194 m).
  - Gates at N (480, 528), S (480, 722), W (400, 600) and E (560, 600).
  - The market is 30 × 44 m at (480, 600).
- **Coordinates:** metres, x east, z south. Kit fronts face +Z, and a yaw θ in degrees means `rotation.y = θ·π/180`.
- **The ground inside the walls is one flat level.** It's trodden earth with cobble patches, flagstone road strips, the market slab and four greens.
- **Contents:** 112 buildings and about 1,578 props: 82 different pieces, about 114,500 tris placed. In Unity on the phone it drew 168 draws and 162,600 tris at 120 fps.
- **Stores:**
  - Walk up to a door and the prompt reads "A · Basil's Shop". A opens today's screen over the city, so **no store rule changes**.
  - The keeper stands at the door.
  - Gloamvault has no interiors either.
- **Places on buildings** (proposal):

| Tunewick place | Building |
|---|---|
| Basil's Shop | general store (`vale_store`) |
| Guild Library | library (`vale_library`) |
| Market | the square's stalls and market hall |
| Dr. Pell's Lab | apothecary |
| Breeders' Guild + Upgrades | guildhall |
| Shrine of Echoes | the church for now. The design says "on the hill", so later it moves to a hill outside a gate. |
| Mailbox | by the inn (and a second one at the ranch gate) |
| Odd Jobs | notice board at the market cross |
| Journal, Calendar | the menu |
| Market Lane (Bond shopping trip) | the north–south street |

  Gloamvault's other shops (arms, bows, runes, larder) become houses for now. Its agility course inside the walls and its shop signs go (§10).
- **The gates:** A at a gate opens "Out to the Vale". It's the same prompt in reverse coming back in.
- **Look:**
  - Bake what doesn't move in Blender: the toon steps, AO, painted wear, the per-building paint and cloth swaps.
  - At runtime, keep a small material for the window glass and the lamp glow.
  - Gloamvault's old web client already decodes the vertex colour code in three.js (`client/src/scene/env/envMaterial.ts`).
  - The code is: R = slot ÷ 15; G = variation ×(1 + 0.36 (G − 0.5)); B = AO mix(0.45, 1, B); A = 1, 0.95 on trim, 0 on window panes.

## 4. The world around the town

- **The land:** 960 × 960 m. The Wildsong part is the farmland north of the walls:
  - **King's Road** runs from the north gate to the brook bridge at (480, 321).
  - The **brook** runs east to west about 200 m north of the town: 4.5 m wide, 1.1 m deep, with a ford with stepping stones at (330, 297).
  - The **mill pond** is at (588, 354), 31 × 22 m, with a jetty.
  - Woods all round; the Greyfell Hills to the east.
- **The ground: the height function is ported to TypeScript** (W0: `tools/world/land/`, `createLand(loadLand())`; tested in `land.test.ts`; the map is `npm run world:map`).
  - What it adds up: area discs, hills, an edge rise, the integer-hash fbm noise (amp 1.1, scale 46, 3 octaves, seed 7), the town plateau, plot flattening, and the water beds and banks.
  - It needs only plain math. Use `Math.imul`/`>>>0`, and `Math.fround` if we want Unity's exact heights.
  - Gloamvault has no test vectors, so make our own.
  - Roads don't flatten the ground; they're ribbons laid 6 cm above it.
- **Our land, not a copy:**
  - Fork the land tables into `tools/world/`. Remove Gloamvault's places: goblins, wasps, spiders, altars, essence rocks, the arena, the gallows, camps, caves, nests, the chapel, the toll ruin, the Keep, the secrets and the agility props.
  - Rename everything in Wildsong's words (Wildsong Vale; new road names in `CONTENT.md`).
  - Add Wildsong places as phases need them (the Guild arena by the river, the quarry for Quarry Haul, the shrine hill).
- **Baked at build time, not at runtime:**
  - Blender (or a Node builder) makes the terrain, water and scatter as 32 m chunk GLBs, merged and vertex-coloured, plus a far-land ring.
  - The sidecar holds a walk heightfield (int16 cm on a 2 m grid) and a walk map.
- **Life:**
  - grass tufts near the camera (instanced) and swaying trees;
  - birds, rabbits and deer (Gloamvault's ordinary animals), plus butterflies;
  - fog from 55 to 160 m, as in Gloamvault.
- **Quick travel:** a map with "Go to the ranch" and "Go to Tunewick", so a short session never has to walk.

## 5. The ranch

- **The site:** **x 390–640, z 250–500**, right outside the north gate up King's Road. It's the flattest place on the brook:
  - heights 1.7–4.8 m (mostly 2.1–3.4 m) and a slope of at most 9%;
  - 266 m of brook plus the mill pond;
  - the King's Road, a field track and the marsh path run through it.
  - It **absorbs Gloamvault's farm pieces already there:** old barn (420, 450), pasture (x 393–465, z 423–495), windmill (515, 366), watermill (553, 356), hen farm (516, 514), scarecrow field.
  - This matches the design: "a small, run-down homestead at the edge of town" with "the ranch's brook" (CONTENT §1).
  - At about 6 ha it's big and open, but a run from end to end takes about 70 s, so zones sit on one loop path.
- **Everything the ranch does today gets a place:**

| Today (screen or sheet) | On the 3D ranch |
|---|---|
| Star monster and ranch-mates (up to star + 6) | living in paddocks and the barn. Tap one to open its card (Edit, Bag, Songbook). |
| Empty pen "+" / buy a pen | an empty paddock with a sign |
| Train (Light / Heavy / Bond) | **each drill is a real spot**, as the design always said ("each drill is a real place around the vale"): Hill Sprints (hill behind the barn), Log Toss (log and fence), Puzzle Stones (stone table in the garden), Target Toss (painted target in the meadow), Dodge the Gourds (barn), Acorn Shower (big oak), Plow Pull (field), Moon Meditation (flat rock), Wind Chase (the windmill), **Waterfall Stand (a waterfall to build on the brook)**, Quarry Haul (the quarry). Walk your monster there and press A. The drill plays as today. |
| Bond games | in the yard: Fetch; hide-and-seek behind 4 real haystacks; the shopping trip walks to Market Lane |
| Rest / Next week | the keeper's house (bed = next week); the calendar on the wall |
| Journey, Expedition, Battle/cups | the ranch gate's signpost (Journey and Expedition) and the road to the Guild |
| Mailbox | at the ranch gate |
| Upgrades | they appear: Cozy Barn, Training Yard, Tide Pool (a pool on the brook), Lantern Garden (lanterns), Feed Shed, Farmhand (a helper on the ranch), Deep Freezer (a cold cellar), Campfire Circle |
| Keepsakes | placed as real props |
| Food (picked in week 1 of the month) | the Feed Shed. Home-grown crops can count toward it (see §6). |

- **New:** fields to farm, the brook and pond to fish, an orchard, forage spots that refill each week, wandering wildlife.
- **The look:** the farm pieces come from Gloamvault, crops from Quaternius Ultimate Crops, and the rest from our own Blender pieces. Upgrades and seasons change the ranch (snow, autumn leaves, live rain from the weekly weather roll).

## 6. Design questions to settle at the ranch phase (recommendations)

1. **Time. Decided (owner, Nov 18): the week stays the heartbeat.**
   - Walking, fishing and looking around are free; the week's one action happens at its place (a drill spot, the bed, the gate); crops grow by the week.
   - This keeps every balance target (GAME_DESIGN §26) and the 1.5–2-hour life.
   - Quick play stays: Repeat last week, the Planner and the old list screens.
   - **Weather stays too (owner, Nov 18).** The weekly weather roll shows live in the city, the world and the ranch: rain, snow, storms, wind and fog.
   - **More extreme weather comes later**, as its own phase.
2. **What farming gives.**
   - **Recommended:** crops grow in weeks and harvest into food that pays for the monthly feed (food today is price × mouths).
   - A few special crops give small treats.
   - New rules go into GAME_DESIGN and tuning, with a save bump.
3. **What fishing gives.**
   - **Recommended:** a short bite-and-reel game, skippable like every animation.
   - Catches: River Fish (a food today), coins from selling, rare catches as keepsakes, and a fish journal.
   - It's unlimited, with no hidden limits; balance comes through value, not caps.
4. **Petting and play anywhere** are cosmetic (a happy emote) unless tuned, so free petting can't break the stress balance.

## 7. Building blocks Wildsong already has

- **Monsters:** every monster has Walk and Run clips with a `rootSpeed` (all but the Nibblegrub cocoon), and Lite copies exist (≤ 12k tris).
- **Input and camera:** the Battle 3D thumb stick (`ui/screens/battle3d/ThumbStick.tsx`, `stickMath.ts`); the walk-on that matches clip speed to movement (`art3d/duel/duel3d.ts` 897–918); camera springs (`duel/framing.ts`).
- **Loading and sideways:** arena loading with Meshopt + KTX2 + a sidecar (`duel3d.ts` 163–224); sideways mode (`ui/screens/battle3d/sideways.ts`).
- **Missing:** free movement, a follow camera, collision, a walk heightfield, door and gate prompts, a keeper, and a saved place.

## 8. Rules and budgets

- **Budgets** (starting points, to be measured on the S25 and an iPhone):
  - Full: ≤ 150k tris, ≤ 100 draws in view.
  - Lite: ≤ 60k tris, ≤ 40 draws.
  - Followers use the **Lite** monster model in the world (the partner uses Ultra on the Ultra tier).
  - World files are never precached (the `models/**` rule).
  - The art3d chunk stays ≤ 300 KB gzipped, so the world code may need its own lazy chunk.
- **iOS Safari 16.4+ must run it.** Gloamvault only ever ran on Android through Unity.
- **Orientation (owner, Nov 18):** the city, world and ranch play **upright and sideways**, built so the whole game can go sideways later. Update CLAUDE.md's phone-first rule when the first phase ships.
- **Fallbacks:** the Town list, the Ranch screen and the hash routes stay for Classic monsters, slow phones and failed loads.
- **Saves:** v1 of the city needs no save change (you arrive at a gate). Saving your place, the keeper's look, plots or catches each bump `SAVE_VERSION` (16 today) with a migration and a test.
- **Credits:** log the Human Base Meshes (CC0) and every kit used in `CREDITS.md`.

## 9. Proposed phases (a stop and a phone checklist after each)

1. **W0 Groundwork (nothing to see). Done Nov 18, 2026 (§10).**
   - Import script `tools/world/import-gloamvault.ts`: the town, land tables, kit, hero and townsfolk, pinned to `588c001`.
   - The kit scripts are copied into `tools/blender/world/`.
   - The height function ported to TypeScript, with tests.
2. **C1 Walk Tunewick.**
   - The town built in Blender and shipped in Full and Lite.
   - The keeper (farmer stand-in), with the stick, a follow camera and collision.
   - Upright and sideways.
   - Town gets a "Walk the streets" button; the list stays.
3. **C2 Stores and company.**
   - Doors with A, our keepers at the doors, our signs.
   - Your partner monster follows you (up to 3).
   - Townsfolk.
4. **C3 Out the gates.**
   - The land between the town and the ranch: terrain, brook, pond, road, scatter, far land and life.
   - Gate prompts and quick travel.
5. **R1 The walkable ranch.**
   - The site laid out, with the herd living there.
   - Drill spots, the waterfall, the house and bed, the mailbox and signpost.
   - It becomes the 3D home; the old Ranch screen stays as the fallback.
   - This replaces the plan's old P10.
6. **R2 Farming** (design, core, save bump).
7. **R3 Fishing** (design, core, save bump).
8. **R4 The ranch grows.** Upgrades and keepsakes appear; bond games in the yard; forage; seasons and weather.
9. **K1 The keeper creator and editor** (save bump), whenever the owner wants it.
10. **Later:** more extreme weather (owner, Nov 18); interiors; more of the Vale (the Guild arena by the river, the quarry, the shrine hill, journey trails); possibly the whole game sideways.

`ART_2_PLAN.md` (roadmap step 2) and `BUILD_PLAN.md` ("The 3D world") follow this order since W0.

## 10. W0 results (Nov 18, 2026)

- **The snapshot:** 26 files, 14 MB. It's Gloamvault 0.14.1 at `588c001` (§1), kept honest by `tools/world/snapshot.test.ts`.
- **The ground port:**
  - Every one of Gloamvault's land assertions passes on our port (`tools/world/land/land.test.ts`).
  - The hash matches the C# bit for bit, and the noise and fbm match to 1e-5. The reference values came from the C# itself, compiled with PowerShell's `Add-Type`.
  - The town's plateau stands at **3.917 m**.
  - A golden table of 13 heights is frozen, covering the town, the road north, the brook, the pond, the ranch site, Greyfell, the edges and the south river.
  - From here on, the port is the reference.
- **The map** (`npm run world:map` → `art-review/world/map.png`, `map-north.png`): brook, pond, roads, walls, buildings, woods, hills, marsh pools, quarry and south river all sit where Gloamvault's own map has them. The ranch site box (§5) covers the farmland, brook and pond just up King's Road from the north gate.
- **The town check** (`npm run art:town` → `art-review/world/town-review.png`, `town-top.png`, `town-overview.png`):
  - What was placed: 113 buildings, 1,756 props and 10 stations (95 pieces, 175 colour variants), 729 road quads and the 330-cell market slab.
  - Built and rendered in about 17 s.
  - Set beside Gloamvault's three town screenshots from the same cameras, the positions, facing, roofs, stalls, awnings (orange and green), gates and walls all match.
  - **So the transform is settled:** game (x, y, z) goes to Blender (x, −z, y) with rotation z = yaw, no mirroring, and to three.js as `position (x, y, z)`, `rotation.y = yaw·π/180`.
  - Stations with no piece (the church's shrine, the workshop's rack) are spots inside other buildings, and are skipped as Unity skips them.
  - The hedgerow and oak by the north gate are newer than Gloamvault's Nov 5 shot.
- **The kit rebuilds on its own** (`npm run world:kit-check`): 189 pieces and 29,271 tris, identical to the snapshot, in 0.8 min.
- **Notes for C1:**
  - **Gloamvault-only pieces inside the walls** go when Tunewick is laid out: its agility course (balance beam, climbing net, crawl pipe, hop stones at z 684, two wall ladders) and the shop signs for its own shops (bow, flask, needle, loaf).
  - **The plain decode looks bluer and harder than Gloamvault** (the blue sky's ambient on the walls, no colour grading, no painted detail or wear). The toon ramp, wear and warm grading of §3 "Look" are C1's work.
  - The ground's cobble patches (stone where `noise(3.5, 41) > 0.3` inside the walls) read well from above.
