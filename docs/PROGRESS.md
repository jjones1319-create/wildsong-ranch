# Progress log

One entry per milestone: what was done, what comes next, and known issues. Newest first.

## Art P1: Puddlepup pilot (2026-10-29) · v1.13.0

**Live:**
- **Puddlepup is a real 3D monster.** Blender builds it from numbers (`tools/blender/monsters/breeds/puddlepup.py`): a round, chunky puppy-amphibian with a big head, floppy fin ears with pink membranes and rib stripes, webbed paws with pink pads, a flat paddle tail, a cream belly and muzzle, darker-teal dapples on its back and a soft blush. Its face is anime-style: big glossy white eyes with a dark iris, a pupil and two highlights, drawn from a Blender-made face sheet, with blinks every few seconds and pupils that glance toward your taps.
- **Every face reads at a glance:** neutral, happy (arc eyes, blush, open grin), tired (heavy lids), stressed (raised brow, wobble), sad (outer lids down, frown), angry (inner lids down, teeth), sleepy (closed), sick (half lids, squiggle), strain (>< eyes, gritted teeth), dizzy (spirals) and surprised (wide eyes, round mouth).
- **27 moves** built in Blender for the quadruped rig: the ranch idles (plain, happy, tired, sad, sick), sleep, eat, pet, look around, hop, celebrate; walk and run (feet planted, no sliding); sit down, sit, dizzy; battle idle, step forward and back, dash, strike, cast, shove, hit, heavy hit, knockout and win. Ears and tail swing on springs after the body.
- **Where you see it:** live on the ranch (it looks around and hops now and then), the Monster Card, the Lab editor, the Shrine's result, Pell's Meet, the Farewell, the week summary, drill results, expeditions, Echo Stones and the Bond games; as a picture in every list and picker; and in battles (Versus, cups, the Effects Lab), where it steps, dashes, strikes, casts, shoves, flinches, topples and celebrates by the fight's flags. A Classic opponent stays its drawing.
- **Songheart Puddlepup** (the `wildsong` secret) has its own texture set: rainbow fin ribs on the ears and tail.
- **Monster Lab → Models:** any breed (the ones without a model show their Classic drawing and say so), variant, life stage, face and move; drag to turn it or let it turn on its own; an fps counter with triangle and draw counts.
- **Settings → Graphics → Monsters: 3D / Classic.** 3D is the default; the Classic drawings show without WebGL, while a model loads, with Reduce motion (as a still), and for every breed not rebuilt yet.

**Done**
- **Pipeline** (`tools/blender/lib/`, `monsters/plans/quadruped.py`, `monsters/breeds/puddlepup.py`, `monsters/build.py`): primitives merged by voxel remesh into one smooth body (8,200 tris), smart UVs, a 26-bone rig with automatic weights, sockets, a face sheet rendered from filled 2D curves (whites, lids, pupil masks, mouths), textures painted procedurally in object space and baked with Cycles (1024², plus the variant set), clips authored as keys in world-aligned axes and pushed to NLA tracks, glTF export with WebP textures, review sheets (turnaround, faces, textures, variant, clip strips). `tools/art/optimize.ts` dedups, prunes, resamples, quantises and meshopt-compresses into `public/models/monsters/puddlepup.glb` (583 KB; the budget is 700) and writes the sidecar `.json` (clip metadata, markers, face cues, sockets, springs, face cells, variants, budget report).
- **Runtime** (`src/art3d/`): one shared `WebGLRenderer` (`Stage3D`) that hosts mount and release, with eviction (newest wins), context-loss fallback, visibility pause, a 30 fps cap on Lite, and off-screen portrait rendering; the `Actor` (toon + outline + face materials, the mixer with cross-fades, markers and face cues, blink/glance/drift clocks, ear and tail springs, stage sizes, the old fade and sick tint); the arena camera (a long lens at a fixed distance, fov per frame) that reproduces the arena's pixel mapping exactly on the floor plane; the battle clip map; the arena layer. The chunk is lazy (`import('../art3d/art3d.ts')`, 176 KB gzipped; `check:build` enforces ≤ 300 KB and that the entry never imports it statically).
- **Game:** `MonsterPortrait` gained `live`, `clip`, `light`, `idleActs`; the cached pictures live in IndexedDB under `wildsong/portrait/…` (`src/save/portraitCache.ts`); the `monsters` setting (per-field fallback, no save bump); `#lab/models` with `window.__art3d` for the scripts; `npm run art:monster`, `art:optimize`, `art:review` (in-game sheets in `art-review/`, gitignored), `art:portraits` (precached base pictures in `public/portraits/`).
- **Tests:** `models`, `faceCells`, `springs`, `arenaCamera` (feet on the floor line across every phone size and zoom), `battleClips`, `manifest` (the shipped files against the budgets and the clip contract), `portraitCache`; e2e `models.spec.ts` (live on the ranch, card and Lab with one canvas; WebGL off; model missing; the setting; context lost and restored).
- **Docs:** CLAUDE.md, README, CREDITS, GAME_DESIGN §22, VISUAL_UPGRADE_PLAN §0, BUILD_PLAN (P1), CONCEPT_PROMPTS (the new style text), ART_2_PLAN §3.6 (chunk budget 300 KB), `.gitignore`, `.gitattributes`.

**What it should look like (for the phone check):** a soft teal pup with a big head and pink fin ears; the shading splits into a lit side and a cooler shadow side with a thin darker outline; the eyes are large and glossy and follow your taps; on the ranch it breathes, looks around and hops; in a battle its ears flap back on a dash and it flinches on a hit.

**Known issues**
- The arena's 3D fighter always paints over a Classic opponent at Close range (P11 rebuilds the arena with both in 3D).
- The textures are painted with soft noise edges; up close on a big phone the dapples look a little blurry. P3 can raise the base texture's detail if the owner wants.
- Headless Chrome renders the sheets through SwiftShader: the phone's GPU looks slightly cleaner.

**Next:** the owner's phone notes on Puddlepup, then P2 (Waterfall Stand with Puddlepup).

## Art P0: one breed per monster (2026-10-28) · v1.12.0

**Live:**
- **Every monster is one whole breed.** The main/sub mix is gone everywhere: the Shrine, the Market, Fusion, the Lab, the Library, share codes and the drawings. A breed now has one look, which is what lets Art 2.0 paint each breed individually in Blender.
- **The old "pure" bonuses go to everyone** (the owner's choice): every monster gets the +10% lifespan and can earn its Signature (loyalty 60 at Prime, the Glacier Bastion trial or the Crown's sheet, as before). The ✦ Pure badge is gone.
- **The Shrine still knows your phrases:** every phrase gives the same breed, personality and nature as before. A phrase that used to make a mix now makes that breed whole, with the breed's own stats, grades and lifespan.
- **Your monsters keep everything:** a mixed monster becomes its main breed with the same stats, grades, techniques, age and lifespan, and now wears that breed's colours. If it still had the name the game gave it ("Cinder Tumblefox"), it's now called "Tumblefox"; a name you chose stays.
- **Monster Lab:** Create and ✏️ Edit have one **Breed** picker; the Colours choice is gone.
- **Collector** needs 30 looks now (breeds or secret variants), down from 50, because there are only 51 in the whole game. Looks already collected still count.

**Done**
- **Core** (`core/monster.ts`): `breedBirth(breed)` replaces `mixBreeds(main, sub)`. The monster loses `subBreed`, `flags.pure` and `appearance`. `BIRTH.lifespanBonusPct` (10) applies to everyone; the blend weights are gone from `tuning.ts`.
- **Signature gates** lose their purity checks: Prime (`signatureAtPrime`), Glacier Bastion (`techniqueCandidates`), Songsheets (`canLearn`, no `signatureNotPure`), the Guild Library and bosses (`npcMonster`, no `sub` option).
- **Shrine** (`core/shrine.ts`): the sub step is gone. It drew from its own `h2` stream, so no other roll moved. Checked against the old code over 3,000 phrases (with all breeds and with only the starting ones unlocked): breed, offsets, likes, nature and name are identical, and the 106 phrases that already made one breed give byte-identical monsters.
- **Fusion, Lab, cocoon, Heartstones, titles:** one breed throughout. The cocoon makes a whole Velvesper (its base, grades and guts) instead of a Velvesper/Nibblegrub mix. Heartstones lose `donorSub`.
- **Data:** no accent parts or sub adjectives in `breeds.ts`, no sub-quirk tag in `techniques.ts`; the Signature rows read "Auto at Prime (loyalty ≥ 60)". CONTENT §2.2 and §3 changed with them.
- **Save v15** (`save/legacyMix.ts`, `schema.ts`, `migrate.ts`): the validator drops the old fields wherever a monster is stored (the ranch, edit history, cups, the Hall of Fame, the Freezer, the Elder Grove, the Memorial, monster files, the Library and bare imports, which never pass through `migrate()`), and renames an untouched mix name using a frozen table of the old adjectives. Heartstones and Encyclopedia phrases lose their sub. The migration step only bumps the version.
- **Classic drawings:** every monster wears its own breed's palette (secret variants keep theirs); `art/monster/accents.ts` is deleted.
- **Screens:** one Breed picker (Create, ✏️ Edit), no Colours control, no Pure badge, the Library's breed filter by breed, names via `variantNameOf`.
- **Tests:** 935 Vitest tests, up from 931.
  - **Birth:** every breed's newborn is its own base, grades and guts with 110% of its lifespan; the Puddlepup numbers are unchanged.
  - **Shrine:** the five pinned phrases keep their breeds (Wildsong and Hello are unchanged to the digit); the 1,000-phrase hash is re-pinned after the old/new comparison above.
  - **Saves:** a v14 save with mixed monsters in every place, Heartstones and phrases; old monster files, Libraries, bare monsters and an old share code; broken sub values never fail a load.
  - **Signatures** for every breed; a former mix keeps the other breed's Basic it knew but can't relearn it once forgotten.
  - **Balance:** the §26 sims pass unchanged, because every sim monster was already one breed with the +10%. The golden lives' hash was re-pinned only because the sim report lost its `sub` field; with it put back, the six lives hash to the old value exactly.
- **Docs:** GAME_DESIGN §4, §5.2, §7, §10, §12.8, §13, §14.1, §14.3 (rewritten as "One breed per monster"), §15, §19, §22; CONTENT §2.2, §3, §11 and the titles table; BUILD_PLAN's new Art 2.0 section; SOUND_UPGRADE §7.7 (the monster song's key comes from its breed); notes in NEW_MONSTERS and VISUAL_UPGRADE_PLAN; the P1–P9 prompts in `ART_2_PROMPTS.md` no longer mention accent parts or mixes.

**Decisions worth knowing**
- **Old mixes keep their numbers.** Nothing is recalculated, so a former mix may have stats, grades or a lifespan its breed wouldn't be born with today. The Lab's "Reset to breed default" brings the grades, guts and lifespan to the breed's.
- **A former mix's extra Basic** (its old sub-quirk) stays until it's forgotten; after that it can't be learned again.
- **Heartstones and Fusion** measure a former mix's trained gains against its breed's base now, not the old blended base.
- **Collector:** old mix looks stay in the Journal's count, so nobody loses progress.

- **Playwright** (two workers): 21 passed, 18 skipped. The one failure is `e2e/sound.spec.ts` on Pixel 7: the Sound Lab's song reads as stopped half a second after the Effects buttons are tapped. It fails the same way on the v1.11.0 commit (built and run separately), so it isn't from this change.

**Known issues**
- `e2e/sound.spec.ts` fails at the Sound Lab check (`lab.song` is null after the Effects taps) on v1.11.0 too; to look at in a sound step.

**Next:** Art P1, the Puddlepup pilot in 3D (Fable 5.1, high effort). It needs `three` and the glTF optimiser, which the owner approves by running P1.

## Grades to S: stat caps, inherited traits and grades, stat bars, the stats guide (2026-10-28) · v1.11.0

**Live:**
- **Grade S:** growth grades now go up to S. Every grade sets how high training can take that stat: E 1,000 · D 1,100 · C 1,200 · B 1,300 · A 1,400 · S 1,500, up from a flat 999.
- **Stat Sweets** always work, even past the cap.
- **The Monster Card's stat bars** (they used to look empty) fill toward each stat's cap in its own color. Sweets are a lighter segment on top, and a thin line marks the cap when sweets push past it.
- **The stats guide:** tap any stat, or "What do stats do?", to see what that stat does in a fight and elsewhere, which drills and Journeys grow it, and how grades, caps and sweets work. The same guide is the Journal's new **Stats** page.
- **Fusion babies** now inherit:
  - a second trait from a parent;
  - one better grade step wherever a parent's grade beats their breed's;
  - a head start of at most 10% of the parents' best trained stats.

**Done**
- **Grade S** (`GRADES`, `GRADE_FACTOR_100.S = 180`):
  - An S stat grows ×1.80, with its own higher drill ceilings (light 18, heavy 24, secondary 12) and Journey ceilings (14 and 10), so it beats A even at Prime.
  - **Where S comes from:** the Potential Pearl (now max S), the sub-breed's +1 step, Fusion inheritance and the Lab.
  - An S stat scores 6 in the Journey check.
- **Caps** (`STAT_CAP_BY_GRADE`; `addTrained` and `lowerStat` in `core/monster.ts`):
  - Drills, Journeys, cup podium growth and Heartstones raise **trained points** (stat − sweets) only up to the cap.
  - Nothing above a cap is ever taken away.
  - Sweets go past the cap. Only the save bound of 9,999 stops them, and then the sweet isn't eaten.
  - Opponents still generate with a 999 per-stat ceiling (`NPC.statMax`).
  - Walking speed counts SPD up to 1,500.
- **Two traits:**
  - **Data and helpers:** `Monster.inheritedTrait`, plus `traitsOf` and `hasTrait` for every raising check.
  - **Battle:** a fighter now carries a list of traits. Multipliers multiply, bonuses add, yes/no effects use "any", and Reflective takes the first.
  - **Checked:** a fixed-seed log of 30 battles was hashed before the change and still matches, so one-trait fights are bit-for-bit as before.
- **Fusion** (`core/fusion.ts`):
  - **The second trait:** the first parent's breed trait, then the second's, then the parents' own inherited traits; never the baby's own, and never Hungry Grub.
  - **Grades:** one step up wherever the better parent's grade beats the baby breed's, never past that parent.
  - **Head start:** `min(old formula, 10% of the better parent's trained points)`. Sweets never pass on.
  - **The "Meet" screen** names the inherited trait and the head start.
- **Heartstones and the cocoon:**
  - Heartstones pass on trained gains only, and the receiver's caps apply.
  - The cocoon keeps sweets whole and keeps any grade steps a Pearl or Fusion had earned. Until now it wiped Pearls.
- **The Lab:**
  - each stat's slider runs to 1,500 and its number box to 9,999, and each row shows its cap;
  - "Max all" fills to cap + sweets, and "Scale to total" stops at the caps;
  - there's an inherited-trait picker.
- **Card UI** (`MonsterSheet.tsx`, `StatsGuide.tsx`, `components.css`):
  - six 44 px stat rows you can tap, colors per stat on `:root`, and a gold S pill;
  - the empty bars are fixed (`.stats__fill` was an inline span with no `display`).
- **Schema v14:**
  - `inheritedTrait` (an unknown id becomes none) and grade S;
  - stats up to 9,999, the sweets record clamped to its stat, wider bounds for best total and stamina.
  - The migration only bumps the version, so saves, monster files and Libraries all upgrade.
- **Tests:** 931 Vitest tests, up from 914.
  - **Speed:** the battle trait helpers have a one-trait fast path, so battles run as fast as before (the 1,000-seed soak takes 37.6 s now vs 36.8 s before).
  - **Time limit:** that soak got the same 120 s limit as the AI soaks, because the full parallel run pushes it past 60 s.
  - **Golden records:** 30 battles and 6 lives, both hashed before the change. The sims' highest stat stays below 1,000, which proves the §26 targets didn't move.
  - **S grade and caps:** the S gain rows, caps and sweets, the drill drop, clamps, the newborn cap, Heartstones, the cocoon, the walk-speed limit, and safe-integer damage at 9,999.
  - **Traits:** two-trait helpers.
  - **Fusion:** the inheritance order, grades and the 10% limit.
  - **Saves:** the v13 → v14 migration, including a monster file.
  - **Playwright:** the new `e2e/card.spec.ts` at 360 px checks the filled bars, the S pill, sweets past the cap, the inherited trait, the guide from a stat tap and the Journal Stats page.
  - **Full Playwright run:** everything passes. Four older specs (bonds, cups, Turnip Sort, the Effects Lab) timed out mid-click while all four browsers ran at once on this busy PC; re-run with two workers, all 13 tests in those files passed.
- **Docs:** GAME_DESIGN §4, §5.1–§5.2, §6.3, §8, §11, §12.3, §12.8, §14.3, §15, §16 and §19; CONTENT §6 and §11; BUILD_PLAN.

**Decisions worth knowing**
- **The owner's choices:** caps 100 apart (S 1,500 to E 1,000); babies inherit both a second trait and better grades; the head start is at most 10% of the parents' best trained stats; the light bar segment is Stat Sweets.
- **S ceilings:** without its own drill and Journey ceilings S would do nothing at Prime, because A already hits the old ones.
- **Two traits stack fully.** Fortified + Unshakable take 0.8 × 0.7 = 0.56 of the damage. That's a deliberate legacy reward, and ✏️ Edit can change it.
- **Fusion feels flatter for strong parents:** the 10% limit almost always decides, so compatibility and rarity matter mostly for lightly trained parents.
- **Shrine mixes can now roll S.** A main A plus a sub whose best stat is the same gives S, so the same phrase can make a stronger monster than before. Monsters already born keep what they have.
- **Version mismatch:** a v14 save or share code can't be opened on a phone still running v1.10, so update both before moving saves.

**Known issues**
- Opponents still top out at 999 per stat, so a monster with several S stats past 1,000 will outclass most cups. That fits "power the player chose", but the late cups may want a look once real S monsters exist.
- The Elder double Memorial entry from v1.10 is still open.

**Next:** the owner's phone pass. Then the Blender monster work.

## Fusion 2: whole-breed babies and surprise recipes (2026-10-28) · v1.10.0

**Live:** a Fusion baby at Dr. Pell's is now always one whole breed, never a mix. The board shows four rows:
- the first parent's breed, 35%;
- the second parent's breed, 35%;
- two **surprises**, 20% and 10%. They show as "???" until you've bred that pair into that breed once. Then they show the breed's picture and name, and the first time, Dr. Pell says "A new recipe!".

Surprises make sense for the pair. Coilfang (a snake) + Galeheron (a bird) can make Hearthwing (a dragon). A fiery monster + a bird leans toward dragons too. Water + sky leans toward Frostlance (ice). Puddlepup + Nibblegrub can make Bloatoad. Some recipes lead to breeds you unlock later, like Wishlume + Nibblegrub → Velvesper, the moth drawn to the lantern. Those wait until that breed is awake.

**Done**
- **Recipes** (`data/fusionRecipes.ts`, CONTENT §2.3):
  - **Kinds:** every breed has one or two of 15 kinds (beast, bird, reptile, dragon, water, stone, plant, bug, spirit, construct, fire, sky, ice, night, knight).
  - **Rules:** 19 kind rules, such as "reptile + bird → dragon".
  - **Recipes:** 13 signature recipes.
  - **Scoring** (`FUSION.surprise`): a recipe +100, each rule that fires +6, sharing a kind with both parents +4, and +1 for each shared kind. Ties are broken by a hash, so pairs with the same kinds don't all get the same surprise.
- **`npm run fusion:table`** prints every pair's surprises:
  - `-- --all`: the same with every breed unlocked;
  - `-- --summary`: per-breed counts, idle rules and weak picks;
  - `-- --pair coilfang galeheron`: one pair's scores.

  I tuned the kinds with it. With the 22 starting breeds, every breed is a surprise for 7–39 of the 253 pairs. With all 30 unlocked, it's 11–43 of 465, and every rule picks something.
- **Odds** (`core/fusion.ts`, `FUSION.odds`):
  - **Normal:** 35 / 35 / 20 / 10. Same-breed parents: 70 / 20 / 10.
  - **Lineage Seal:** doubles the first parent's chance, giving 52 / 26 / 15 / 7 (78 / 15 / 7 for a same-breed pair).
  - **Locked breeds** drop out and the rest renormalize, so the list always adds up to 100.
  - **Subs are ignored:** a mixed parent counts as its main breed.
- **Inheritance fix:** universal techniques now count as part of every breed's kit, as GAME_DESIGN §10.5 always said. A surprise baby can inherit its parents' Songsheet techniques; before this fix, a different-breed baby got nothing outside its own kit.
- **Pell's Lab** (the Fusion tab):
  - parent rows say "Like the first parent" or "Like the second parent";
  - hidden surprises show a "？" tile, with Dr. Pell's hint when one is on the board;
  - "most likely" is hidden on a 35/35 tie;
  - the compatibility comment names the breed it means;
  - "New recipe!" on a first find, and a new Wren line for surprise babies;
  - the "not found", "no catalyst" and "no outcome" refusals have their own messages (they used to say "Finish the cup…").
- **Schema v13:** `fusionFinds` (keys `a+b>c`) with a migration and a test. Bad keys are dropped on load.
- **Tests:** 914 Vitest tests, up from 899.
  - **Odds:** every split above, plus the stat bonus K for each row.
  - **Surprises:**
    - Coilfang + Galeheron → Hearthwing;
    - swapping the parents changes nothing;
    - never a parent and never locked; a locked recipe waits until it is unlocked;
    - too few candidates.
  - **Spread and the pinned table:** the spread limits, and a hash that pins the whole table.
  - **Babies:** pure babies, universal-technique inheritance, and finds recorded once.
  - **Data:** the CONTENT §2.3 tables match the data.
  - **Saves:** the v12 → v13 migration with garbage dropped.
  - **Playwright:** the new `e2e/fusion.spec.ts` at 360 px:
    - the board shows 35/35/???/???, then a fuse;
    - a found recipe shows Hearthwing by name.
  - **`e2e/smoke.spec.ts` fix:** it now taps through every welcome tip. It had been stuck since v1.9.0 added the away-rule tip.
  - **Full Playwright run:** 21 passed, 17 skipped by design (one phone profile is enough for those specs). The Effects Lab spec timed out once while the PC was busy and passed on a re-run.
- **Docs:** GAME_DESIGN §14.3 and §15, CONTENT §2, §2.3 (new) and §6, and BUILD_PLAN.

**Decisions worth knowing**
- **The owner's choices:**
  - Fusion babies are whole breeds; mixes stay in the Shrine and ✏️ Edit for now.
  - New combo-only breeds (a bull-warrior and others) wait for the Blender work.
- **Same-breed pairs can surprise:** two Hearthwings are now 70% Hearthwing (78% with the Seal), not 100%. This follows the "parents + two surprises" rule; ✏️ Edit can always change a baby.
- **All Fusion babies are pure,** so they get pure's +10% lifespan, the classic colors and Signature access. That's a mild late-game buff, and no balance sim covers Fusion.
- **Surprises carry more stats:**
  - The stat bonus (K) follows a row's odds: 0.5 for a parent's breed, 0.6 and 0.7 for the surprises, 0.85 for a Seal's 7% surprise.
  - The ≤2% row can no longer happen.
- **Unlocking a breed can move a pair's surprises.** A recipe for a locked breed takes its slot once that breed wakes, so a found recipe can stop showing for that pair.
- **The surprise table is part of the save contract.** A test pins it, so a later change to kinds, rules or recipes is deliberate.
- **The breed `strength` number** is no longer used (it only fed the old Fusion odds). It stays in the data for later.

**Known issues**
- **Elder Memorial entry:** fusing an Elder from the Elder Grove gives it a second Memorial entry, because it already got one when it retired. This is an older bug and wasn't touched here.
- **A few weak pairs:** about 23 of the 253 starting pairs have no strong reason for their surprise, so the hash picks a loose fit (e.g. Galeheron + Grumblestone → Moatshell). `npm run fusion:table -- --summary` lists them, and they're easy to hand-tune with more recipes.
- **Test time-outs:** the full Vitest run timed out in the four life-sim tests while another project's dev server was busy on this PC. Alone they pass in 60 s, and the next full run was green.

**Next:** the owner's phone pass. Then the Blender monster work: one breed modeled first so the owner can judge it on the phone. That reverses VISUAL_UPGRADE_PLAN §0's "3D pilot skipped" and the CLAUDE.md "Not for now: 3D monsters" line, so those get updated together with it.

## The Bonds update (2026-10-28) · v1.9.0

**Live:** your monster now notices you. Open the game after a couple of hours and it comes to say hello (running up if it's loyal); pet it or give it a treat. Stay away a day and it's sad; two days and the ranch looks abandoned and it falls ill; four days and you find a note on the gate, and it has passed away (on Gentle it goes back to the wild). **Vacation mode** in Settings turns this off. The scenes are Blender-rendered scenery with your own monster drawn over it. There's a new weekly action, **Bond 💞** (fetch, hide-and-seek, or a shopping trip where your monster finds a keepsake to buy for the ranch), which boosts the next weeks' training ×1.75, ×1.5, ×1.25. Training has more levels: Fine +0, Good +2, Great +4, Superb +5 (loyalty 50+), Perfect +7 (loyalty 70+), and loyalty raises the odds of the top ones. Echo Stones pays 1G more each round after round 10.

**Done**
- **Echo Stones:** 15G a round through round 10, then 16G, 17G… (`ECHO_STONES.payRiseAfter`); 20 rounds pay 355G.
- **Training levels** (`core/outcomes.ts`, `core/training.ts`; numbers in `OUTCOME.levels`, `DRILL.levels`):
  - The §6.2 buckets stay, and loyalty now counts a little more toward Great (0.2 a point over 40, was 0.15).
  - Loyalty splits the great bucket into Perfect (from 70), Superb (from 50) and Great, and the success bucket into Good and Fine.
  - Bonuses go on after the gain caps, so a capped stat still gets them.
  - Chore pay: Great +50 %, Superb +75 %, Perfect +100 %.
  - The drill sounds and reactions follow the level's bucket.
  - The expert view shows the Superb and Perfect odds.
- **Bond weeks** (`core/bond.ts`, `screens/ranch/bond/`):
  - The Train sheet has a Bond tab.
  - **Fetch:** hold to wind up, let go in the green.
  - **Hide-and-seek:** four haystacks, a rustle, seeded from the game's RNG.
  - **Shopping trip:** a keepsake the ranch doesn't own yet; buy it, or "Not today".
  - The week calms the monster and builds its affection.
  - The bond boost lives on the monster (`status.bondPct`) and fades a quarter each week after.
- **Keepsakes** (`data/keepsakes.ts`, `art/keepsakes.ts`): ten original things, drawn in code beside the monster (four at a time) and listed on the Monster Card; −1 stress each per week, up to −4.
- **Arriving** (`core/arrival.ts`, `ArrivalScene.tsx`, `SceneClip.tsx`):
  - **Last visit:** the save's time; it's written on every change and when the app hides.
  - **When it's checked:** at launch, and on returning to the app. A return during a battle waits for the ranch.
  - **Consequences:** they apply before the scene plays.
  - **Arming the clock:** it arms on a save's first launch of this version (Wren's new `awayRule` tip explains it), for a new game, after an import, and when Vacation mode is turned off. Bad clock values in a save count as unarmed.
  - **Endings:** the new endings 'neglected' and 'wandered' go through the usual Farewell (Memorial "Left alone" / "Went back to the wild", Heartstone) and never count for Gentle Heart.
  - **Sandbox previews:** Settings → Sandbox → Preview arrival scenes plays each scene with nothing changed.
- **Blender scenes** (`tools/blender/ranch_scenes.py`, `tools/blender/encode.ts`, `public/baked/scenes/`):
  - **What they are:** four procedural clips rendered with EEVEE in Blender 5.2.2: the ranch at golden hour, under grey cloud, abandoned in the rain, and the note on the gate.
  - **Format:** each is 720×960, 7–8 s, H.264 under 0.9 MB, with a WebP still.
  - **How your monster is placed:** the camera is static, so the code places your monster in % of the frame.
  - **When the still shows:** with Reduce motion, offline (the clips aren't cached by the service worker; the stills are precached), or if a clip fails. Failing that, the ranch is drawn in code.
  - **Credits:** logged in CREDITS as our own renders. The 527 MB of scratch frames (`tools/blender/out/`) are gitignored.
- **Schema v12** with a migration and tests: `settings.vacation`, `away`, `keepsakes`, `status.bondPct`, the new endings and Memorial causes, and the new levels in the planner log.
- **Tests:** 899 Vitest tests, up from 878. New: the result levels and their reference table, the bonus after the caps, the bond boost on gains and its weekly fade, Bond effects, the seeded shop find and purchase, keepsake stress, every arrival stage at its exact boundary, vacation and arming, a clock that runs backwards, the consequences, the endings and Gentle Heart, greetings, pet and treat, the v11 → v12 migration with garbage clamped, and the new tip order. The §26 sims were updated for the levels. Playwright: the new `e2e/bonds.spec.ts` (the hello with pet and treat, a day away, two days away, the note and the neglect Farewell, Vacation mode, a Fetch week and a shopping trip that buys a keepsake) and `e2e/oddjobs.spec.ts` (Echo Stones now expects 183G for 12 rounds; the Meadow Dash lock check now records the lock as it happens): 9 passed at 360 px, no page errors.
- **Docs:** GAME_DESIGN §1 (principle 5's "nothing is permanently missable" replaced by principle 6, the owner's away rule), §3, §6.1–§6.4, new §6.9 and §6.10, and §26 (the A/B target and the outcome rates); CONTENT §4 (levels, Bond weeks, keepsakes) and §13; SOUND_UPGRADE (the stand-ins); BUILD_PLAN; CREDITS.

**Decisions worth knowing**
- **The owner's choices:**
  - Training levels Fine +0, Good +2, Great +4, Perfect +7, with Superb +5 added between.
  - Perfect only from loyalty 70.
  - Consequences for not opening the game, with Vacation mode to pause them.
  - Blender for the scenes.
- **Away consequences** (my decision, the owner asked for real ones):
  - **A day away:** stress +15, affection −10, respect −5, the bond boost gone.
  - **Two days:** stress +30, affection −20, respect −10, two weeks of lifespan, a week sick.
  - **Four days:** the life ends.
- **Balance:**
  - **Where the bonuses land:** going on above the caps is what makes Perfect feel good, but it lifts strong A/B monsters about 8 %. The §26 Late-bloomer target moved from 2,550 / 2,950 to 2,700 / 3,200 at years 5 / 6.
  - **Typical C-grade monsters** stay inside their original targets.
  - **Good-care rates:** Perfect about 5 %, Superb 5 %, Great 11 %, Good 12 %, Fine 47 %.
- **Bond weeks and the boost:** bonding every fourth week nets roughly +12 % growth, because the boost covers the three drill weeks after it. Bonding costs a little fatigue, so it doesn't replace rest.

**Known issues**
- The arrival scenes use stand-in sounds until S3 (the match-loss phrase for sad, the cup-exit fall for the note).
- The abandoned clip needed stronger compression to fit 1 MB, so its puddle ripples are soft.
- The away clock follows the save on this phone: a Safari tab and the installed Home Screen app keep separate saves and separate clocks.

**Next:** the owner's phone pass. Then S3 (the owner's S2 listening notes first).

## Odd Jobs 2: endless jobs and Meadow Dash (2026-10-27) · v1.8.0

**Live:** Basil's Odd Jobs have no pay limit any more, and every job keeps going for a skilled player.
- **Turnip Sort:** reaching 150G inside the 30 seconds starts overtime. The clock stops, weeds join (Compost, the middle bin or a swipe down), and each item comes a little faster. A missed item or the second mix-up ends the job.
- **Echo Stones:** the Moon stone (violet, crescent) wakes at round 11, the tempo then quickens only 1% every two rounds, and there's no last round.
- **Meadow Dash** (new): tap the Run pad and your monster races three rivals down the meadow. Win a heat to run a faster one; the run ends at the first heat you don't win. SPD adds up to 25% to each tap.

**Done**
- **Rules:**
  - `core/oddJobs.ts`: no cap; overtime with an endless seeded dealer (the first phase deals exactly as before, overtime has its own stream and starts with a weed) and a window that shrinks 12 ms an item to a 0.35 s floor. Overtime mix-ups are strikes, not pay, so the 150G stays banked. Turnip Sort keeps a best.
  - `core/echoStones.ts`: five stones; the melody is extendable and identical to before through round 10; the late tempo; no cap.
  - New `core/meadowDash.ts`: the race in fixed 1/50 s ticks with integer distances (hundredths of a millimetre, so rounding never stalls a runner).
    - Rivals ease to a pace that rises every heat, with paired wobbles. Rivals have no top speed and the player does, so every run ends.
    - A close finish goes to whoever crossed first within the tick, and a dead heat goes to the player.
    - Pay is 25G a heat. Numbers are in `ODD_JOBS`, `ECHO_STONES` and the new `DASH`.
- **Schema v11** (`turnipBest`, `dashWeek`, `dashBest`) with a migration and a test; bad values are clamped.
- **Screens:**
  - The board has three cards, each with its own pay line and best.
  - Turnip Sort: the clock moved into `useTurnipRun.ts`; adds the overtime banner (tap Ready to skip), three bins that fit at 360 px, swipe down, and mix-ups left.
  - Echo Stones: the Moon on its own row, rising in, and the "A fifth stone wakes" line.
  - Meadow Dash:
    - One animation-frame loop runs the countdown and the race, and the runners are drawn between ticks without re-rendering.
    - The Run pad is full width at the bottom. Two thumbs, keyboard and screen readers all work.
    - The heat buttons stay locked for 0.8 s after a heat, the race pauses when the phone switches away, and leaving mid-run still pays the heats won.
  - The stones and the Run pad no longer play the UI tap sound on top of their own.
- **Sound:**
  - `echo5`: the Moon's B4, below the other four, because the ocarina stops at the Star's C#6. No two stones share a note name.
  - `dashStep`: one soft grass footstep per tap, throttled to 70 ms.
  - `dashGo`: a frame drum with a glock note.
  - The countdown ticks on the woodblock; a heat won plays the music-box arpeggio, a heat lost the drooping kalimba.
  - Meadow Dash plays the Town fair stem over the meadow bed, a stand-in until S3.
  - `audio:check` passes on all three new effects (echo5 −28, dashGo −29, dashStep −42 LUFS momentary max).
- **Tests:** 878 Vitest tests, up from 859.
  - New: the Meadow Dash suite (calibration, top speed, rivals, ties, purity, the whole heat ladder, settling), overtime and the dealer, the Moon melody and late tempo, the v11 migration, the director's Dash row, and the five stone pitches.
  - A new Playwright spec, `e2e/oddjobs.spec.ts`, at 360 × 780. In-page bots play each game: Turnip Sort into overtime until an item slides off, Echo Stones to round 13 with the Moon, Meadow Dash winning heat 1 by tapping and losing heat 2. 3 passed, no page errors, no sideways scroll.
- **Docs:** CONTENT §13 (all three jobs; the stone notes corrected to what they actually play), GAME_DESIGN §3 and §9, SOUND_UPGRADE §10.4 and §11, BUILD_PLAN.

**Decisions worth knowing**
- **The owner's choices:** the Moon at the 150G mark (round 11); Turnip Sort's mix-ups count toward the two only after 150G; Meadow Dash is heats until you lose; SPD helps a little.
- **Meadow Dash heats won** (simulated, steady tapping):

  | Tapping | SPD 1 | SPD 999 |
  |---|---|---|
  | 5 taps a second | 3 | 5 |
  | 6 taps a second | 5 (125G) | 8 |
  | 8 taps a second | 9 | 12 |
  | 12 taps a second, two thumbs | 16 | 21 (525G) |

  Heat 1's lead rival takes 12.5 s; heat 10's takes 5.2 s.
- **Money:** a very good player can now earn roughly 1,000G a week from Odd Jobs (a Stat Sweet is 400G). The Relaxed option (one setting for Echo Stones and Meadow Dash) makes both easier at the same pay.

**Known issues**
- Listen for the footstep patter's level on the phone (`dashStep`); it was set by measurement only.
- The 🏁 on the board shows as a plain checkered square in desktop Chrome on Windows; phones draw the flag.

**Next:** the owner's phone pass. Then S3 (the owner's S2 listening notes first).

## Sound S2: a theme for every event (2026-10-27) · v1.7.0

**Live:** every event in the calendar now plays its own music. The regular cups keep the cup theme in their season's colours; the sixteen big events each have a new composition, with a lobby for the cup screens, a match that builds from base to drive to tension, a crowd of the right size, and their own stingers at the results.

**What to listen for (one line per piece; Sound Lab → Music → Event themes, or the event picker for any calendar event)**
- **New Year Open** (A Mixolydian, 126): a plucky strumstick dance doubled by the glock, horn calls answering each phrase, claps on two and four. A winter fair.
- **Ascensions** (B♭ major march, 112): violins with the horn an octave below, the Wildsong motif climbing through the B section, timpani on one and three; the lobby is organ and horn alone, like a procession. Each season's Ascension rings its own colour (harp in spring, glock in summer and winter, strumstick in autumn).
- **Crown of Dawn** (D Lydian, 116): violins rising phrase by phrase, horn calls from below, glock light at the phrase ends. A sunrise.
- **Crown of Tides** (G Dorian 6/8): the flute riding long-short swells, a cello answering, harp waves, an ocean-drum swell every four bars.
- **Crown of Embers** (A Phrygian dominant, 126): a low flute winding through the scale's step-and-a-half over strumstick strums, cello spiccato, darbuka and woodblock. Warm, glowing, dancing.
- **Crown of Frost** (B minor waltz, 108): vibes over a shivering low violin tremolo, a wine glass ringing every four bars, timpani and sleigh bells.
- **The Wildsong Legend** (D Lydian, 120): the title theme as the grandest battle, violins and horn in octaves; in the middle the ocarina plays alone over the harp, then the last climb home.
- **Masquerade** (C harmonic minor waltz, 126): a sly clarinet over harpsichord and pizzicato that opens on the masked chromatic turn; a muted drum and finger cymbals; the crowd only applauds politely.
- **Rival Showdown** (G Mixolydian, 124): the violins strut in on Corin's rising motif and the horn echoes it; a stop-time middle. Any match against Corin in any event plays this in that event's colours.
- **Vale–Coast Summit** (F major, 116): call and response, the Vale (ocarina with recorder) against the Coast (flute with horn), both together in the middle, claps on two and four; the crowd claps on two and four in the last ten seconds. The Qualifier is the same anthem with fewer layers.
- **Hero's Rally** (E major, 118): a bold tune, violins with the horn two octaves below, a bass-drum boom every four bars. **Rogue's Rally**: the same tune in E minor on a sneaking clarinet over pizzicato, claves on the off-beats.
- **Sprout Cup** (F major, 108): a bright kalimba tune that skips in after a rest, a music box answering. **Elders' Cup** (the same chords at 100): a tenor recorder remembering over harp and cellos.
- **Journey Trials** (E Dorian, 116, moved to each site's key): an earthy climbing tune; Iron Quarry on tenor recorder, Windrun Steppe on flute, Starfall Observatory on vibes with a wine glass, Archer's Glade on alto recorder with balafon, Glacier Bastion on violin tremolo with vibes.
- **Practice** (C major, 112, the Lab): a light marimba tune in skipping dotted rhythms, kalimba answers, no crowd.
- **Cups:** now also ring their season's colour (harp, glock or strumstick) at the phrase starts; the Lantern Festival and Starlight Cup ring hand chimes, the Arcane Cup vibes with wine glasses. Two cups of one season differ in lead, kit, key and tempo.
- **Results stingers:** second or third place is a modest rising recorder phrase; knocked out is a gentle two-note fall; each Crown has its own eight-second fanfare quoting its theme; the Legend's win is the Wildsong motif as a ten-second Hall of Fame anthem; a rank-up is a rising flute phrase; a title three kalimba notes with a glock above. They play one after another (result, rank, title), then the lobby returns.
- **Rival calling cards** (over the lobby when the round preview shows them): Corin climbs his motif on strumstick; Marigold a friendly flute turn; Brannock stomping cello spiccato; Wisteria falling vibes; Juno a sly clarinet wiggle; Garrow three slow recorder steps; Saltmarsh a ship's horn call; Ember Rook a quick kalimba run; the Masked Breeder the chromatic turn on harpsichord.
- **Crowds:** small cups murmur; Opens and the Rival Showdown are louder; Ascensions bigger again; Crowns bigger and wider; the Legend's crowd is huge; the Masquerade's hushed hall never cheers or gasps. In the last ten seconds the crowd claps on the beat (the Summit on two and four). Every match end gets applause.

**Done**
- **S1 gaps fixed:** the `events` sample pack now loads on the cup screens, battles and the Sound Lab and stays in use while wanted (before, cups played violins, cajon and cymbal swell on their fallback synths, and a loaded pack would have been released mid-cup after 60 s). A lead moved onto another instrument (an event's lead, a weather swap) now takes that instrument's articulation and folds into its range by octaves at play time; S1's note that it did was only true in the tests (the Iron Cup's cellos played above every cello sample). The results screen plays its stingers (S1 wrote `cupWin` and `promotion` but nothing played them). Journey Trials read their site from the Trial. A stinger that ends after the player has left the screen no longer brings the old music back over the new. A song could drop its first note or two: it starts 50 ms ahead, each note's callback runs 50 ms early, and humanising sometimes pulled the first note a few ms earlier still, past the scheduler's tolerance (the offline checks caught it as "2 late events"; it is the likely cause of S1's late notes at the Town switch and the match start). `audio:check` can rebuild by itself again on Node 24 for Windows (its `npm.cmd` call needed a shell).
- **Samples:** six new instruments, all in the `events` pack: Renaissance organ, wine glasses (tuned by water, so their rule allows 70 cents off the note name; the build now keeps a sample's true tuning when its octave is corrected), ocean drum, Flemish harpsichord, balafon (soft mallets) and clarinet (its top sample is mislabelled a semitone, so the rule stops below it). Core 3.34 MB / 370 s decoded, events 1.23 MB / 129 s, 4.57 MB in all.
- **Music:** 16 new themes (`src/audio/music/songs/`), 9 new stingers, 9 calling cards, two new kits (`tide`, `masque`), the cup's colour line. The checker now also asks for the Wildsong motif in `ascension` and `legend`, Corin's in `rival` and the masked turn in `masquerade`. Every piece passes it against every other.
- **Event table and director:** every row plays its own theme with concrete lead, kit, colour, key, tempo and arrangement (`THEME_DEFAULTS` holds each theme's own, checked against the songs); Trial rows per site; the Corin rule on the battle screen; requests carry the packs they need and the clap-along; no `TODO_S2` left. Stingers can play as a chain; the runtime's arrangement merges a named arrangement with the lobby form and writes only real changes.
- **Sound Lab:** the Event themes group, an event picker (any calendar event as its row plays), Journey-site chips, the calling cards, a clap-along switch beside the crowds.
- **Tools:** `audio:check` renders every theme's battle (with its event's crowd), lobby and tension, the Summit Qualifier, the new stingers, a stinger chain, the calling cards and every crowd size; `--only` takes a comma-separated list; `--jobs N` (default 2) renders several items at once.
- **Tests:** 859 Vitest tests (103 new: the event table against every song, the director's event rows, the Corin rule, Trial sites, clap-along and result stingers, the S2 songs, stingers and cards, crowd profiles, the beat grid, octave folding, and every screen's packs covering its instruments). The six CPU-heavy core simulation files time out in the parallel suite while another project runs on this PC and pass alone, as in S1. Playwright: 10 passed (the sound spec now also checks that the cup screens decode the events pack and that the Lab's event picker plays an Ascension on `ascension`).
- **Docs:** GAME_DESIGN §23 (events, results, crowds, the Lab); SOUND_UPGRADE §6.4 (the two kits), §7.4 (Trial transpositions), §7.6 (one stinger per Crown); CREDITS; BUILD_PLAN.

**Decisions worth knowing**
- **The horn's samples stop at middle C** (the library has nothing between C4 and D5), so horn-led pieces pair the horn in its warm range with violins or flute an octave or two up; the horn plays calls, countermelodies and octave doublings.
- **One stinger per Crown** instead of one shared `crownWon`; **Trial rows move up to ±5 semitones** to reach each site's tonic.
- **Plucked leads are peakier than S1's ocarina.** The violin, strumstick, kalimba and marimba themes reach −18 LUFS with a crest of 15–21 dB, so `audio:check` now reads true peak where §14.3 sets it: on the master for battle themes (what can clip, about 5.6 dB under the stems), and on the master for lobbies, tension layers and stingers, which the spec gives no peak of their own. Place songs still gate their own stem. Five quiet themes (Ascension, Dawn, Rival, Rally, Sprout) carry every line 3 dB higher so their calibration trims stay inside ±6 dB, and each lobby's gain is set from its measured offset to the battle.
- **Derived pieces:** `rally-rogue` is `rally` written in the minor (the same note letters under an E minor key signature) with its chords moved by degree; `elders` keeps `sprout`'s chords and form at 100; `legend` is derived from `wildsong`; each Crown stinger from its Crown.

**Stand-ins still waiting for S3** (`TODO_S3` in `director.ts`): the Shrine, Pell's Lab, the Monster Lab screens, Journeys and Expeditions, the Farewell, Turnip Sort, Echo Stones, the other ten drills; and the S3 stingers (birth, farewell, birthday, monster song, rest, play, journey depart and return), which use the nearest written stinger.

**Known issues**
- The calling-card and stinger levels are set by measurement like S1's; listen for a card that jumps out of the lobby.
- Late notes in the browser are logged by the e2e sound spec, not gated. With the first-note fix the counts were 0 after the ranch, 3 after Town and 12 after the match start in one run on this busy PC (another project's tests were running); a quieter run counted 3, 3 and 3. S1 measured 3, 9 and 4. Those come from the battle screen's main-thread work at mount; `AUDIO.lookaheadSec` is the lever if the phone drops notes there.
- The Ascension's and the Rally's violin tunes sit low and share their register with the viola pad on a few notes (the checker's warning, not an error).

**Next:** the owner's listening pass (the S2 phone check in SOUND_UPGRADE §15), then S3 (places, trainings and moments) from their Sound Lab notes.

## Sound S1: calm engine and first songs (2026-10-26) · v1.6.0

**Live:** the chiptune loops and the ZzFX effects are gone. The game now plays calm, acoustic music written for it (ocarina, recorders, harp, strings, soft mallets and hand drums) from CC0 instrument samples through our own Web Audio engine, with procedural ambience under it, soft natural effects, and a **Sound Lab** (Monster Lab → Sound, or Settings → Open Sound Lab) where every piece can be auditioned and rated. The spec is `docs/SOUND_UPGRADE.md`; this stage is its S1. Nothing in the rules changed; no save-schema bump (the new sound settings have fallbacks).

**What to listen for (one line per piece; the Sound Lab plays each one)**
- **Wildsong** (title, new game, credits): an ocarina states the six-note Wildsong motif over a slow harp arpeggio and a viola pad; the alto recorder takes the second half with a dreamy raised 4th; a glock sparkles at the turns. Should feel like home and a little wonder, at 72 BPM in D. The new-game screen hears only harp, pad and bass; the credits roll hears every section twice and ends held.
- **Ranch, spring** (6/8, G): a lilting ocarina tune over harp and cello pizzicato, a recorder answering in the gaps, a soft shaker; the motif opens the B section high up. Birds and a brook in the breaths between passes.
- **Ranch, summer** (4/4 with a light swing, C): a lazy marimba tune with a kalimba ticking under it, bongos and a shaker far back; the flute takes the brighter B section and quotes the motif. Warm and unhurried.
- **Ranch, autumn** (3/4, D): a slow waltz, ocarina over strummed strings with a cello answering between the phrases, a frame drum marking the downbeats. Wistful but warm.
- **Ranch, winter** (4/4, A minor, 66 BPM): sparse vibes with a glock shadow an octave up, a harp turning gently underneath, bowed vibes humming, sleigh bells only on the downbeats of B. Hushed.
- **Weather** on any ranch song: cloudy quietens the sparkle; rain drops the drums and the counter, swaps the lead to harp (vibes in spring) and adds a viola pad; a storm leaves pad, harp and fragments of the lead with longer breaths; snow adds a glock sparkle. The ambience follows (more wind, rain, distant thunder, a muffled snow).
- **Town** (3/4 folk waltz, F, 108): strummed strings and a recorder tune, bass on one and chords on two and three. Walk Shop → Market → Guild → Library → Mail → Workshop → Odd Jobs: the same tune, a different slice each time (kalimba and harp in the shop, claps at the market, horn and soft timpani at the guild, a music box in the library), and it never restarts.
- **Cup** (every regular cup; E Dorian, 120): the cup screens hear a half-time lobby; the match starts on a drum hit and a harp chord, strings pulse from bar three, the drums build, and when someone drops to 30% HP or ten seconds remain, string tremolo and a double-time drum come in. The lead and the drum kit change with the season (flute or recorder in spring, marimba or kalimba in summer, ocarina or cellos in autumn, vibes or violins in winter) and each cup has its own key and tempo nudge. Elimination cups are drier and 4 BPM faster.
- **Match stingers:** a win is a four-second recorder-and-horn fanfare; a loss three soft falling ocarina notes over a viola pad; a draw a recorder shrug. First place gets a six-second fanfare with timpani and a cymbal swell; "Ascended!" a proud horn climb. The area music comes back at its next section after each.
- **Musical effects** (in the key of whatever is playing): coins are a glock note and a handful of coins; a letter is wind chimes and a hand chime; using an item a harp-and-glock arpeggio; a Stat Sweet a kalimba lift; learning a technique an ocarina phrase over a harp chord; the planner stopping two harp notes; growing up a harp-and-horn phrase; the prime a warm chord bloom; a new week a bird and a harp chord; Wren's report two kalimba notes.
- **Buttons:** a soft wooden tick (marimba) on buttons, a kalimba tick on chips, a lower tick on back and close, two notes up or down on switches, a paper flick on tabs. The Button sounds setting turns them off.
- **Battle effects** follow each technique's element: fire whooshes and crackles, water burbles and splashes, ice shimmers and shatters softly, lightning cracks warmly without buzzing, earth rumbles and tumbles, nature rustles, light rings, dark thumps low, sound sings three notes in the song's key. Heavier hits are lower and longer; a crit adds a snap; a miss is a quick swish; a KO is a deep thump that cuts the music. At ×2 the travel sounds thin out; at ×4 only medium-and-heavier impacts and KOs remain. The crowd cheers heavy hits, "oohs" a miss, murmurs at a Special and applauds a KO.
- **Waterfall Stand** (the pilot drill): the waterfall roars (two decorrelated noise layers with spray and surges every second or so), a cello drone and a slow ocarina line play through it with harp, and the result lands exactly on its stinger: Great is a harp glissando and a high ocarina note through the roar; Success a warm cadence; Cheat a sly chromatic slide and a pizz plink; Fail a soft falling third left hanging; Slacked the whole bed sagging down a step, then a sleepy tenor-recorder yawn and soft breathing. The other ten drills share a soft generic cue in G until S3.
- **Ambience:** spring meadow (breeze, bird phrases, a far brook), summer field (bees), autumn wind with leaf rustles, winter yard with a far hearth crackle; the town's murmur (three band-passed noises with a syllable swell, no words), carts and footsteps and a far bell; the market's coins and crates; the shop's clock; the guild's far crowd; the library's page flips; the arena's wind and flags with a small crowd.
- **Listening on:** Phone speaker trims the low end and the harsh middle and narrows the stereo; Headphones keeps the full width. Mono audio sums everything.

**Done**
- **Samples** (`npm run audio:samples`, `tools/audio/`): sparse, blobless clones of VCSL and VSCO 2 CE at the pinned commits and the two Kenney zips (hashes in CREDITS), 395 samples chosen by per-instrument rules, every pitch measured (guided YIN; both libraries name notes an octave low, confirmed on 100% of harmonic samples), trimmed, level-matched, loop-baked (≥ 50 ms equal-power seams), encoded Opus 48 kHz mono with `ffmpeg-static`, re-decoded and measured. Packs computed from the usage graph: **core** 344 files, 3.40 MB, 376 s decoded; **events** 51 files, 0.45 MB (cup kits and stingers). `public/audio/manifest.json` records everything; a test checks files, ranges, loops, budgets, packs and credits.
- **Engine** (`src/audio/engine/`): the only place that touches Web Audio. Buses and master chain per spec §4.2 (effects join after the glue, so a hit never pulls the music down); listening presets and mono; a 400 ms look-ahead scheduler on a swappable driver (realtime, offline, fake); a sample bank with per-instrument readiness and release; sampler voices (nearest sample ±4 semitones, velocity to gain and lowpass, mono crossfades, scoops, grace notes); band-limited fallback voices; seeded reverbs in two slots; the ambience engine (seamless noise loops, LFO and random walks, Poisson spawners, crowds with reactions); the effect player (throttles, 16 + 4 voices, variation, panning, speed thinning). `window.__audio.state` is the read-only debug view.
- **Music system** (`src/audio/music/`): the ABC subset parser, chord symbols, 11 accompaniment generators, step-string percussion and kits, the song model (layers, stems, weather rules, breaths, arrangements), the performer (humanising, swing, phrase shaping, vibrato by length), the 14-rule checker, the motifs. `npm run audio:analyze` prints every piece's numbers and the checker's notes; all 24 S1 pieces pass with no errors.
- **Director** (`src/audio/director.ts`, pure; `ui/lib/audioDirector.ts` applies it): an explicit row for every Screen and every event, 250 ms debounce, crossfades (2.5 s between seasons), stems at the next bar, layers over one bar, weather at the next phrase, interrupting stingers, the pause lowpass, the KO cut.
- **UI:** Settings → Sound (ambience and button-sound switches, four volumes, Listening on, Mono, Test sound, Open Sound Lab); the Sound Lab (`#lab/sound`: Music, Ambience, Effects, Moments, Mix tabs, 👍/👎 and notes per item, Copy my sound notes); the drill result waits for the cue's `resultAt`; battle, Songbook, bag, shops, Shrine, Echo Stones and the game store call the new effects.
- **Quality tools:** `npm run audio:check` (offline renders of every piece through the real engine in headless Chrome; loudness, true peak, crest, clicks, dropouts, the effects' levels against the music, decoded samples vs the manifest; `--calibrate` writes `src/audio/levels.json`), `npm run audio:review` (listening files and an HTML report in `audio-review/`), `npm run check:build` (precache and chunk budgets, now in `verify`). `tools/audio/baseline-legacy.json` keeps the old loops' numbers (crest 6.5–8.9 dB, loops 3.6–16 s).
- **Tests:** 756 Vitest tests (87 new: the analysers, the ABC parser, generators, the song model, the scheduler, the voice pool, the checker over every piece, the event table, the director, effects, the manifest, the settings bump, the bans lint). Playwright `e2e/sound.spec.ts` (spec §14.5).
- **Docs:** GAME_DESIGN §23 rewritten and §24 extended; CLAUDE.md (no zzfx, an Audio section); CREDITS (VCSL, VSCO 2 CE, Kenney with commits, links and hashes); README; BUILD_PLAN; `docs/SOUND_UPGRADE.md` committed.

**Stand-ins until S2 and S3** (marked `TODO_S2` / `TODO_S3` in `director.ts`): every event theme but the regular cup (Opens, Ascensions, Crowns, the Legend, the Masquerade, the Rival Showdown, the Summit, the Rallies, Sprout and Elders, Journey Trials, the Lab) plays the cup in its season palette; the Shrine plays the Town library stem with no bed; Pell's Lab the Town workshop stem; the Monster Lab the Town shop stem; Journeys, Expeditions and the Farewell the ranch song of the season; Turnip Sort the Town fair stem; Echo Stones no music; the other ten drills the generic cue. The moments without their own stinger yet (second place, Crowns, births, farewells, birthdays, rest, play, journeys) use the nearest S1 one.

**Decisions worth knowing**
- **Levels are calibrated, not hand-set.** The engine carries a fixed music and ambience makeup (`AUDIO.musicMakeupDb`, `ambienceMakeupDb`) and a velocity range (`velocityRangeDb`), and `audio:check -- --calibrate` writes the remaining per-piece trims (within ±6 dB) to `src/audio/levels.json`.
- **Loudness targets are read on the stems** (the music stem for songs, layers and stingers; the ambience stem for beds), because the master sits about 5.6 dB lower: the volume sliders, the Phone speaker preset and the glue all come after the stems. The spec's battle target (−18 LUFS) is therefore the music stem too, with the master still gated on true peak; the drill cues' −22 LUFS is the master with the bed, and a cue's trim is the mean over its five outcomes. Two exceptions state the design rather than fight it: Slacked sits 1 LU under its siblings (the bed sags, that is the point), and the Waterfall Stand lands at −24, the level of its roar, because the music is written to stay under the water.
- **Coloured noise is baked into the loops in JS**, not made with an IIRFilterNode: Chrome takes about 400 ms to create one, which froze the page for 3–4 s on a Town bed switch and for half a second on every fire or earth hit (found by the e2e "Town within 2 s" check). The same filter coefficients run over the loop once at build time.
- **The cup lead folds by octaves** into whatever instrument the season gives it (a cello lead plays the tune an octave or two down), so one written tune serves every palette.
- **The engine chunk is 33 KB gzipped against a 45 KB budget** because the recipes (effects, beds, drills, events, stingers) live in a second chunk loaded with it and the checker and motif detector in a third that only the Sound Lab loads. Anything added to the engine later needs the same care.

**Next:** the owner's listening pass on the phone (the S1 checklist in SOUND_UPGRADE §15), then S2 (a theme for every event) from their Sound Lab notes.

**Known issues**
- The music is dark on purpose (0–1% of its energy above 2 kHz on the ranch songs); if it sounds dull on the phone, the first thing to try is the Headphones preset, the second a brighter velocity lowpass in `sampler.ts`.
- iOS Safari before 18.4 may stay on the fallback voices (it only partly decodes Ogg Opus); the owner plays on Android.
- Levels are set by measurement, not by ear: after the trims in `src/audio/levels.json` every song, layer, bed, cue and stinger sits within ±1 LU of its §14.3 target (the biggest trims: ranch-summer +4.3 dB, the promotion fanfare −5.2 dB, the arena-out bed +3.2 dB, the waterfall −3.6 dB). Whether the balance *feels* right on the phone is the owner's call; the Sound Lab's Mix tab is the place to say so.
- The §26 battle balance test (`src/core/battle/balance.test.ts`, from M9) takes about 3 minutes on its own and can run past its timeout when the whole suite shares a busy PC; it passes alone, and the Linux deploy runner finishes the whole suite in about 3½ minutes. If `npm test` reports it timing out, rerun that file alone.
- **Listen for dropped notes at the Town switch and the match start.** The scheduler looks 400 ms ahead; in a headless browser on a busy PC the e2e run counted 3 late notes at the Town switch, 9 at the match start (the effects layer starting up) and 4 when the Sound Lab loaded its chunks. A real phone with a GPU should stall far less; if a note goes missing there, the lookahead in `AUDIO.lookaheadSec` is the lever (longer lookahead, slower layer changes).
- `npm run e2e` starts eight browsers at once, and every spec now unlocks audio and decodes the sample pack; on a PC that is already busy the timing checks (Town within 2 s) and 10 s clicks time out. `npx playwright test --workers 2` is the reliable form there.
- `audio:check -- --calibrate` measures everything with the trims it starts from, so a cue whose master includes a bed (the drills) needs a second pass after the bed trims land, or a hand correction: the waterfall cue's trim was lifted from +1.6 to +4.1 dB after the waterfall bed took −3.6 dB.
- `audio:check` takes about 25 minutes for the full set (`-- --quick` renders one item per group in about 5); it needs the installed Chrome and a free port 4173.

## Calendar (2026-10-24) · v1.5.0

**Live:** a Calendar to plan training around. Tap the date bar on the ranch (or Calendar in Town, or "See calendar" on the cup entry screen):
- **Agenda:** the next 12 weeks.
- **Month:** four week rows.
- **Year:** 12 month tiles with icons for Officials, Crowns, Opens, invitationals, the Summit and Expeditions.

Every cup shows whether your monster can enter it, using the same rules as the entry screen. Star (★) a cup or a trip and Wren reminds you the week before and on the week; the Battle button gets a dot. Under the date, the ranch now shows what's next: "Next: Spring Ascension · in 3 wks".

**Done**
- **`core/calendarView.ts`** (pure). `calendarWeeks(state, fromWeek, count)` returns, for each week:
  - The cups with the year rules: Sprout in even years, Elders' in odd ones, and the Summit Qualifier and Summit replacing the Heatwave and Stargazer Cups in Summit years. Each has its purse at today's grade, rounds and item prize.
  - The expeditions open that month, with today's grade and fame check.
  - Dated notes: a Crown four weeks ahead for an S monster, the Legend in March once all four Crowns are won, the Market's seasonal stall each season, the May week 4 upgrade letter, and birthdays every 48 weeks of age.
  - What already occupies the week: the plan, a Journey or Expedition, injury, sickness, or time away.
  - Plan clashes with notable or starred events.

  Everything comes from `EVENTS`/`eventsAt`, `EXPEDITION_SITES`, `marketStock`, `isUpgradeOfferWeek` and tuning; no table is copied. Locked breeds, the cocoon, the Reefclaw, the storm spark, the Vigil and secret variants never appear until the save records them, and no weather is forecast. The module also provides `nextUp` (the date bar's line), `planClashes`, `togglePin`, `prunePins`, `pinnedItems` and `pinnedEventThisWeek`.
- **One set of entry rules:** `entryCheck(state, event, week)` in `core/tournament.ts` is now what `eventsForWeek` uses as well. For a later week it checks only what's knowable today, with the age projected and the temporary blocks skipped. `roundsOf(format)` and `itemPrizeKind(event, grade)` are new; the prize code itself now runs through `itemPrizeKind`, so the calendar can't drift from it.
- **★ reminders:** save **v10** adds `calendarPins` (keys `${weekIndex}:${id}`) with a migration (empty) and validation (bad keys dropped, deduplicated, capped at 200). Pins are pruned at each week's end; an expedition pin lasts its month. Wren mentions a starred cup the week before and on the week (`pinLines` in `core/report.ts`), and a starred trip the week before its month and while it's open. The Battle button gets a dot in a starred cup's week.
- **The screen** (`screens/ranch/Calendar.tsx`, route `#calendar`, Back returns to where it was opened):
  - Today's date, month and year arrows from January of this year to four years ahead, and a "Summit year" tag.
  - Agenda / Month / Year, with "Only events I can enter" (starred ones always show) and "Show expeditions".
  - Cards with the event-kind pill and icon, ★, the current week highlighted and past weeks greyed.
  - A detail sheet with the date, grade ("Your grade (D) · promotion" for an Official), format and rounds, purse, item prize, the entry answer with "Based on Pip's grade today (D)", ★, and Enter for this week's event (the entry screen opens with it picked).
  - The planner sheet warns "Your plan runs through the Summer Ascension".
- **Tests** (19 new, 605 in all): `core/calendarView.test.ts` covers:
  - Summit and normal years, even and odd years, and the next Summit always within four years.
  - Rounds and purses, invitation-only events, knowable-only checks for later weeks.
  - Entry answers equal to `eventsForWeek` for every event in four years of weeks under eleven monster setups.
  - No secrets or weather leaked, and a discovered Reefclaw joining the summer Market note.
  - Birthdays, the Market and upgrade notes, Crown and Legend notes, expeditions, busy weeks, plan clashes.
  - Pins: toggle, cleanup at week end, Wren's lines and the dot, the v9 → v10 migration, a save round-trip and garbage.
  - The "Next:" line.

  Playwright `e2e/calendar.spec.ts` at 412 × 915: date bar → calendar, Agenda → Month → Year, a month tile, a ★ that shows on the ranch line and as the Battle dot, then Enter from this week's event; no sideways scroll.
- **Docs:** GAME_DESIGN §3 (the Calendar screen) and §21 (the date bar's "Next:" line, the Calendar and Town rows).

**Decisions worth knowing**
- **The Crown and Legend notes are reminders, not letters.** CONTENT §9 says the Crown invitation arrives by mail a month before each Crown and the Legend's in March. The code has always used standing flags instead: the Crown invitation is set by winning the S Official (mailed once, then), and the Legend invitation the moment the fourth Crown is won. The calendar shows the notes on the CONTENT dates without claiming a letter arrives; no rule changed.
- **Plan-clash warnings and the "Next:" line only count notable events** (Officials, Crowns, Opens, the Legend, the Masquerade, the Rival Showdown, the Summit and its Qualifier) plus anything starred. Ordinary cups are skipped because almost every week holds one, which would make the warning permanent.
- **The calendar's filters and the browsed month are session-only.** The ★ reminders are saved.
- **The game has one (dark) theme.** The calendar uses only the shared colour tokens, so it follows any future light theme.

**Next:** the owner's phone pass, then V3 (monster animation 2.0).

**Known issues**
- A future week's answer uses today's grade, nature and techniques (the sheet says so). A promotion before then can change it.
- "Summit years only" isn't an answer the calendar gives. Summit events simply aren't listed in other years, and the Year view's header marks Summit years.

## Playable events + round-by-round cups (2026-10-24) · v1.4.0

**Live:** you can fight every match your monster is in, in every event, the Ascensions included. Before each of your matches the cup asks: **Fight**, **Auto** (watch, and one tap on Auto takes over or hands it back at any moment) or **Skip**. Cups are now played a round at a time: a round preview with every pairing, your match, the round's other results, then the standings after that round with ▲/▼ place changes. Below it, a tournament breakdown: Standings, Rounds, the Bracket for elimination cups, and Team and Legs at the Summit. Tap any finished match for how it ended, the HP left and the time, and watch an NPC match again.

**What was wrong (reproduced at 412 × 915 before the change)**
- The entry screen chose Auto or Manual once for the whole cup, defaulting to Auto. On Auto every match started with side A as a CPU fighter (`aControl: 'ai'`), and the battle screen only shows the Auto button for a player-controlled side, so the whole cup, Ascensions included, was watch-only. Manual worked (the pads and the Auto button were there in the Spring Ascension), so there was no second cause.
- The Journey Trial's Auto had the same problem (no takeover).
- `roundRobin()` gave every pairing its own round, with the player's pairings first: in an RR6 Official you fought all five matches back to back, and the other ten were only simulated after that, so the standings didn't move until the end.

**Done**
- **Always playable** (§12.11): the player's side is always `control: 'player'`, expert, with the saved Auto style. Auto is the engine's own `auto` flag, switched on by an input recorded at tick 1 (`autoStartInput`), so the Auto button is always there and replays stay exact. **Skip** runs the same setup with that same input (`skipPlayerMatch`), so it gives exactly the result an untouched Auto run on the same seed would. One function (`playerMatchSetup`) builds the player's match for Fight, Auto and Skip alike. The Journey Trial follows the same rule. The entry screen's choice is now the **default for this cup** (Fight / Auto). It starts on Fight, is remembered in settings (`cupMode`), and only decides which button is highlighted. `tournament.mode` keeps that meaning in the save (`manual` = Fight).
- **Real rounds** (`roundRobinSchedule`, the circle method): RR4 is 3 rounds of 2 matches, RR6 is 5 rounds of 3. Every pair meets once and everyone fights once per round. The opponents' seats come from the cup's seed (drawn after the opponents, so the opponents are unchanged). Corin, or else the strongest opponent, is your last-round opponent. Elimination and single matches are unchanged.
- **Round-by-round flow** (`currentRound`, `simulateRound`, `standings(t, upToRound)`, `placeChanges`): after your match only that round's other matches resolve. `simulatePending` now stops at your next match instead of playing every NPC match ahead. Walkovers (an opponent who withdrew after a KO) win your round without a fight. If you're knocked out, the rest plays a round at a time with "Skip to final standings".
- **The breakdown** (`TournamentPlay.tsx`): Standings (after the last finished round), Rounds (every round, results and "upcoming"), and the Bracket for elimination cups (`bracket()`, future slots as "Winner of A vs B"). The match-details sheet has a **Watch it again** button for NPC matches: `matchSetup` is the exact setup the cup simulated, and a test checks the replay ends the same. The Summit shows the Team score and the five Legs (`relayLegs`, replayed from the cup's seed; its win count equals the one stored at entry). Repeated wild names in one cup are told apart on screen with their breed.
- **Save v9** with a migration and tests. A cup match's result can carry its length in ticks, shown as the time in the details; older results show "—". Match rounds may now go up to 30, so a pre-v9 RR6 cup in progress (rounds 1–15) keeps its stored schedule and finishes through the same flow. Old saves with `mode: 'auto'` load as an Auto default.
- **Tests** (586 Vitest, 37 new): `core/cups.test.ts` covers the RR4 and RR6 schedules (every pair once, everyone once per round, the player in every round, the same seed gives the same schedule, the boss last). It also covers standings after round r, nothing simulated ahead of the current round, a KO'd player's remaining rounds, the bracket, the Summit legs, Auto taken over and handed back for every event kind and the Trial, Skip equal to an untouched Auto run, exact NPC replays, and v8 saves with an old-schedule cup and mode `auto` loading and finishing. `ui/store/battleStore.test.ts` checks that the battle screen's own Auto start ends exactly like Skip. Playwright `e2e/cups.spec.ts` at 412 × 915: an Ascension round by round (round 1 by hand, Auto taken over and handed back, Rounds tab, details, Skip, finish), an Elim4 bracket and the Summit legs, with no sideways scroll.
- **Docs:** GAME_DESIGN §11 (Trial), §12.11 (Fight / Auto / Skip), §13 (schedules, round-by-round play, the breakdown), §21 (the cup screen).

**Decisions worth knowing**
- **Seeds changed, as expected.** The new schedule moves matches to different places in the list, and each NPC match's seed comes from its place. The player's matches also use a fixed seed from the cup now (they used a fresh random one), so Skip and Auto agree. One seeded test (the round-robin tie-break) assumed the old order and now follows the schedule instead; no rule, reward, point, tie-break, tier or balance number changed.
- Walkovers are still recorded the moment a fighter is KO'd (that rule is unchanged); the standings "after round r" only count rounds up to r, so they don't show a walkover early.
- Versus "CPU vs CPU" stays an exhibition with both sides on the CPU; it isn't one of your matches.

**Next:** the owner's phone pass, then V3 (monster animation 2.0).

**Known issues**
- The round recap is screen state, not saved: if the app closes on a round's results, it reopens on the next round's preview (the Rounds tab still has every result).
- The opponent count is small enough that the breakdown recomputes each render; the Summit's legs are replayed once per visit (four short simulations).

## V1: Effects engine (2026-10-24) · v1.3.0

**Live:** battles have a real effects layer. A transparent WebGL canvas sits over the arena, follows the camera, and draws sparks, flames, droplets, rocks, petals, stars, smoke, beams, rings, bolts and waves in code. Every one of the 294 techniques now has an **element** (Fire, Water, Ice, Lightning, Wind, Earth, Nature, Light, Dark, Sound, Physical), so attacks already look different in Versus: a Fire hit bursts into embers and smoke, a Water hit splashes with ripple rings, an Earth hit throws rocks and shakes the ground, a Lightning hit forks a bolt and flashes, a Dark hit pulls violet smoke inward. Settings → Graphics has **Quality** (Auto / Ultra / High / Lite) and **Intensity** (Cozy / Standard / Flashy), and Monster Lab → **Effects** lets you fire every shape at every element with an fps counter and a stress test. Spec: `docs/VISUAL_V1_EFFECTS.md`; the plan for V1–V5: `docs/VISUAL_UPGRADE_PLAN.md`.

**Done**
- **Dependencies:** `pixi.js` 8.22 and `pixi-filters` 6.1. The WebGL renderer is imported directly (no WebGPU code), so the lazy `fx` chunk is 134 KB gzipped plus 11 KB of Pixi's browser bits, under the 150 KB budget. It loads only on the battle and Effects Lab screens; the title and ranch bundles are unchanged.
- **`src/fx/`:** `FxLayer` (renderer, world / shapes / screen containers, a clock that follows playback speed, pauses with the battle, freezes for hit-stop, sleeps when nothing is live and when the tab is hidden, survives context loss), `camera` (world ↔ screen, glued to the M10 arena camera), `rng` (visual randomness only; the core RNG is never touched), `pool` + `sim` (typed-array particles, swap-removal, no allocation after warm-up), `emitter` (two ParticleContainers, normal and additive, over a 16-frame atlas drawn with Canvas 2D at start-up), `elements` (every element's ramp, shapes, blend and flags), `quality` (tiers, Intensity, the 3 Hz / 0.3-alpha flash gate, the shake curve), `bus` (engine events → FxEvents), `recipes` (the default recipe per element per moment; melee hits land 117 ms into the lunge, ranged hits when the projectile arrives), `filters` (heat haze displacement, shockwave, bloom, RGB split, by tier).
- **The 18 primitives** (`src/fx/primitives/`): burst, cone, trail, projectile (shape by element: orb, lance, blade, boulder, drop, note, leaf, bolt), beam, ring (upright or a ground shockwave), impact, splash, sheet (a GLSL mesh shader: a rising wave with a curled crest, or a falling sheet), lightning (midpoint displacement with branches, three glow passes, flicker), haze, glow, debris (bounces on the floor), mist, flash, shake, hitstop, impactFrame. The four screen-space ones go through hooks the arena DOM implements: shake moves a stage wrapper that holds the monsters and the canvas together, hit-stop pauses the monsters' CSS animations, the impact frame is a two-frame difference-blend overlay (a canvas filter could not invert the DOM monsters).
- **Elements** (`src/data/elements.ts`, CONTENT §3 / NEW_MONSTERS §4 Element column, `docs/fx-review/element-table.md`): the §5 rules in order (keyword categories, whole-word or prefix matches so "Drain" is not "rain", named exceptions, breed-only keywords, plain melee names → Physical, breed defaults with the three INT / POW splits, universals → Sound). `ELEMENT_OVERRIDES` takes the owner's corrections; `scripts/element-table.ts` prints the table and `scripts/element-column.ts` rewrites the doc columns. Counts: Physical 62 · Light 47 · Dark 39 · Water 34 · Fire 31 · Earth 23 · Sound 18 · Wind 12 · Nature 11 · Lightning 9 · Ice 8.
- **Arena** (`ui/battle/Arena.tsx`): the arena is now one component shared by the battle screen and the Effects Lab. It owns the camera loop (which also feeds the fx layer), the fx canvas, a floats layer above the canvas, the impact overlay and the hit-stop class. The CSS shot, crit sparkle and arena shake are gone; the lunge, hit flash, knockback, KO flop and victory hop stay.
- **Settings → Graphics:** Quality Auto starts at Ultra (High under 4 GB / 6 cores, Lite under data saver), measures the first battle's first 90 frames and remembers the tier (`fxAutoTier`); choosing Auto again forgets it. Intensity Cozy / Standard / Flashy per the §6 table; Reduce motion (the toggle or the OS) forces Cozy. No save-version change: the three fields have fallbacks.
- **Effects Lab** (`#lab/effects`): two preset monsters (pickable), every primitive × element, Random attack (a made-up fire + hit through the real recipes), Combo (fire cone → impact → shake → hit-stop → impact frame), Stress test (20 effects at once), Clear, live fps / particles / tier / intensity, the Quality and Intensity controls, Record 3 s (dev builds), and `window.__fx` for scripts.
- **Review** (`docs/fx-review/*.png`, one sheet per element, 18 primitives × 2 moments): generated by `e2e/fx-review.spec.ts` on the Pixel 7 profile with a manual fx clock. Three rounds: the first found every texture-based primitive invisible (a plain `TextureSource` never uploads a canvas; `CanvasSource` does), the second found the manual clock clamped to one frame and the particles too small at phone scale (sizes up 40–60 %), the third fixed the oversized ring and the opaque mist (a per-particle alpha ceiling). `e2e/fx-lab.spec.ts` checks the Lab opens, fires a combo, reads an fps, and logs no errors.
- **Tests** (549, 54 new): `fx/sim`, `pool`, `quality` (tiers, Auto sample, Intensity, flash gate, shake), `bus`, `recipes`, `boltPath`, `camera`; `data/elements` (rules, exceptions, breed-only keywords, universals, melee, and the CONTENT / NEW_MONSTERS columns matching the data); the settings schema. The simulation's tests are untouched (`src/core` has no diff).
- **Docs:** GAME_DESIGN §21 (Settings → Graphics; the Effects Lab), §22 (the effects layer, elements, Quality / Intensity), §24 (the flash gate and reduced motion); CONTENT §3 (an Elements subsection and the column); NEW_MONSTERS §4; BUILD_PLAN (V1 ticked, V2–V5 outlined); CREDITS (PixiJS, pixi-filters).

**Decisions worth knowing**
- WebGL only, no WebGPU: it is what keeps the chunk inside the budget, and particles and filters at this scale gain nothing from WebGPU. `autoDetectRenderer` can come back later if the budget is raised.
- Filters (haze, shockwave, bloom, RGB split) only bend what the canvas draws. The monsters are DOM, so heat haze shows as shimmer on the flames and a translucent wobble, not on the fur. V3 may move the monsters into the canvas, which would lift that limit.
- Hits resolve in the same engine tick as the fire, so the recipes delay the impact (melee a little, ranged by travel time); the floating numbers still appear at once, as before.
- The default Lab monsters stand at ±210 so the camera is close to a real Near fight.

**Next:** the owner's phone pass (VISUAL_V1_EFFECTS §11) and any element corrections (`ELEMENT_OVERRIDES`). Then V3 (monster animation 2.0), then V2.

**Known issues**
- The Auto quality sample runs during the first battle, so that battle may start at Ultra on a phone that then settles on High.
- The water sheet is soft-edged; a Blender-baked flipbook stays an option if V2's wave techniques want crisper foam.
- The impact frame inverts the whole arena for two frames by design (Standard: crits only; Flashy: heavy hits too; off under Cozy and reduced motion).

## Odd Jobs: Echo Stones (2026-10-24) · v1.2.0

**Live:** Town → Odd Jobs is now Basil's board. It lists Turnip Sort and the new Echo Stones; each job pays once per in-game week on its own, and a free Practice button replays any job for fun with no pay. Echo Stones is a memory game: four glowing stones (Ember, Leaf, Tide, Star, each with a colour, a shape and a note) hum a tune that grows by one note a round and quickens every four rounds; you tap it back. One slip ends the game, with one second chance a game. Your monster sits beside the stones, hums along, is pleased when you get a round right and jumps when you slip.

**Done**
- **Schema v8** with a migration and tests: `echoStonesWeek` (the last paid week) and `echoStonesBest` (the best round, practice included). Settings gain `oddJobsRelaxed` (the Relaxed speed option, with a fallback, no version change).
- **Rules** (`core/echoStones.ts`, numbers in `ECHO_STONES`): a seeded melody (never three of a stone in a row), the tempo (−12 % every 4 rounds down to a floor; Relaxed ×1.5), 15G a round up to 150G, round 8 takes 5 stress off the monster (paid plays), the best round, and the title **Perfect Pitch** at round 15 (awarded at once, practice or paid). Turnip Sort keeps its own weekly stamp.
- **The board** (`screens/town/OddJobs.tsx`): job cards with status, best round, Play for pay and Practice; Turnip Sort moved to its own component with a practice mode (no pay).
- **Echo Stones screen** (`screens/town/EchoStones.tsx`): a 2 × 2 grid of big stones drawn in code (an ellipse with a sheen and a circle / square / triangle / diamond), a glow that flashes as the note sounds so it works with the sound off, four new bell notes through the existing ZzFX player (C4 E4 G4 C5), haptic ticks on Android through a shared `lib/haptics.ts`, screen-reader labels per stone and a live status line, the monster portrait with ♪ / ♥ / ?! reactions, the retry card, the result card (rounds, pay, calm, new best, title), and a Relaxed toggle remembered in Settings. Reduce motion stops the glow transitions through the global rule.
- **Tests** (10 new): seeded melodies, the tempo, pay and its cap, the weekly limit (independent of Turnip Sort), stress relief, practice paying nothing but keeping the best, the title once, the v7 → v8 migration with garbage clamped; the title table grows to 21.
- **Docs:** CONTENT §13 (the board, Echo Stones, Practice) and §14 (Perfect Pitch), GAME_DESIGN §9.

**Decisions worth knowing**
- Best scores and the Perfect Pitch title count in practice too (they are skill, not money); pay and the stress relief are weekly rewards.
- The melody is dealt from the game's RNG like Turnip Sort's chute, so a game is part of the save's story and a test can replay it.

**Next:** the owner's phone pass. Then the LATER list.

## M10: Smarter battles (2026-10-24) · v1.1.0

**Live:** battles are played by a new brain. Monsters plan a range, move to it with small footsies, back off, dash in with a reason, push when they are stuck together or cornered, use techniques from every range they own, save guts for big moves, punish an opponent that is out of guts, play safe when ahead late and go all in when behind. Your Auto mode is an Expert with a style (Balanced, Aggressive, Defensive), a little icon over each monster can show what it is thinking, and the arena camera keeps both monsters fully on screen, zooming in when they close and out when they spread, with fence posts at the walls. Spec: `docs/BATTLE_AI_V2.md`.

**Done**
- **AI 2.0** (`core/battle/ai.ts`, GAME_DESIGN §12.10): skill tiers (Rookie E–D, Skilled C–B, Expert A–S, every special-cup opponent, rivals from C, Trials from B, the player's Auto, Versus and the Lab) with reaction delays, sticky mistakes and a per-tier pause after a technique; a think loop that re-plans every 8–12 ticks and at once on events; the range plan (offense × aggression − threat × caution + variety − travel, threat at half weight, 15 % hysteresis, sweet spots away from the opponent's best band); the goal technique and the save-or-spend rules (fire the goal here, a worthwhile poke, anything at 90+ guts, against a broke opponent, when being punished or to break a stall; otherwise save); corner awareness, anti-stall, pushes with a reason, the step-in-to-shove, dashes with a reason, the clock and HP modifiers, the Heavy-ready, punish and special reads, trait reads (Statue Pose holds its ground, Unshakable ignores corners, Chill kites, Blessed and Green Thumb value heals, Battering Ram dashes freely), rival habits kept. Each side reads the other's last-tick direction and target, so neither sees the other's same-tick decisions. The plan is logged (`plan` events) so replays and tests cover decisions.
- **Auto styles** (§12.11): Balanced / Aggressive / Defensive in Settings and in the battle pause sheet; the style travels with the Auto input (`setAutoStyle`), so replays stay deterministic and it applies in cups and Trials too.
- **Show battle thinking:** 🛡 keeping distance · ⏳ saving guts · ⚡ pressing · ↔ pushing away · ❗ punish! · 🏳 playing safe · 🧱 cornered; a mode is held half a second; on by default in Breeder's Lens (`showThinking: null` follows the mode; no save-version change, the two settings have fallbacks).
- **Arena camera** (`ui/battle/camera.ts`, 11 pure tests): frames both monsters, zooms between "the whole arena fits" and a 45 %-of-width sprite cap, never shows past the walls, a critically damped spring (an ease with Reduce motion); the world layer is positioned through three CSS variables set once per frame; floats and the icon counter-scale; shots fly through the camera. `bodyRadius` 80 with a 200-unit sprite box so touching looks like touching (the start gap stays 300). Fixed a pre-existing centring bug: the art wrapper had zero width, so every sprite sat half a sprite to the right of its true position (part of the off-screen-at-the-wall complaint).
- **Balance** (`docs/BALANCE_REPORT.md`, now Expert vs Expert): Gilded gains 7 guts on every landed hit (Lootlid's mean sits inside 40–60 at every total); the four pure casters' Near basic moved to Close (an Unshakable brawler was a 0–8 % hard counter); 70 technique rows nudged inside the §10.2 bands (brawlers and walls up, ranged kits down: the new brain's kiting had shifted the meta); Statue Pose −50 %, Moth Dust ×0.65, Unshakable's CONTENT row fixed to −20 %; the five starters' Basics and Hits trimmed a point so the starters' KO average at 1,000 lands inside 15–35 (it is 33 %, 4.7 % at 3,000). Veteran toughness was not needed. The script now checks every pair 25–75, ≥ 95 % of pairs 30–70, Lootlid's mean 40–60 (every breed's mean is flagged in the table but only Lootlid's is a target), the starters' KO average, attacks, and prints AI health and its run time (about 13 minutes for 279,000 battles on 16 cores; the new brain costs about 3× the old one, 2 µs per monster per tick).
- **Tests** (495, 30 new): `ai2.test.ts` (no stall, pushes, the whole kit, movement, Expert beats Rookie, mirrors, punish windows, the clock, determinism with plan events, performance, tiers, attacks per tier, Gilded, the Auto input and styles, Statue Pose, the v1 brain stays inside the walls), `camera.test.ts`, the settings schema; `ai`, `habits`, `engine`, `balance`, `traits`, `unlocks` and the data tests updated (the Crown unlock test records the player's wins instead of relying on one seeded fight).
- **Headless check** at 390 × 844 and 360 × 780: Settings with the new controls, a Spar on Auto with the icons, the pause sheet with the style control, a monster pinned at the wall fully on screen, the result card; no page errors.

**Decisions worth knowing**
- **Head to head, AI 2.0 does not beat the v1 brain by the spec's 60 %.** Across the ten varied test pairs it wins 42–55 % (depending on the technique data of the moment); in mirrors the two are even. Greedy poking is close to optimal for damage in this guts economy (both brains run at about 8–12 guts on average), and the new brain's gains are positional: it wins with kiting kits (75–90 % as a caster against the old brain) and with brawlers against casters it can shove, and gives a little back with slow brawlers against kiters. The behaviours the owner asked for are all there and tested; the test is a regression floor (≥ 40 %) with the share logged. Banking guts for Heavies was tried (several variants) and never out-damaged poking, so pokes stay.
- The §26 KO band is measured on the five starters' mirrors over four NPC rolls each (one roll swung the average by 15 points); the script checks the same five.
- The casters' pushes are what make ranged kits strong under the new brain; giving pushes a reaction delay or restricting the step-in-to-shove made things worse (jitter, 0 pushes), so the rebalance went through technique values instead.
- Versus and the Battle Lab use Expert on both sides; cups and Trials follow the grade rules above.

**Next:** the owner's phone pass (BATTLE_AI_V2 §6). Then the LATER list.

**Where the matrix landed** (200 battles a cell, Expert vs Expert): 94.5 % / 99.3 % / 95.2 % of pairs inside 30–70 at 1,000 / 2,000 / 3,000 (the 1,000 tier misses the 95 % rule by two pairs); mirrors 45–55; +10 % and +30 % inside their bands; the starters' KO average 33 % at 1,000 and 7 % at 3,000; Lootlid's mean 46–59 %; attacks 4–12 everywhere (Coilfang sits exactly on 12 at 1,000). Eleven pairs remain outside the hard 25–75 band, most by a point or two of noise; the real outlier is Ashwraith at 3,000 (77–81 % against Lootlid, Grumblestone and Gloomgrin, 20 % for Cobblemaw against it).

**Known issues**
- The pairs above; Gloomgrin stays the weakest breed at 3,000 (slow, short reach, kited by casters) and Ashwraith the strongest.
- The plan icon can read "saving guts" for long stretches in even fights at 2,000+: both sides are banking for the same big technique.

## M9: Balance, QA and the v1.0 release (2026-10-23) · v1.0.0

**Live:** version 1.0. Every breed has been raised under all four care policies and fought against every other breed at three power levels, and the numbers were tuned until the matchups sit inside the design's bands almost everywhere (`docs/BALANCE_REPORT.md`). The special cups now scale to your monster, the casters fight properly at close range, the Shrine's tabs and the Journal's chips stop wrapping, lightning wanders, and a Playwright smoke test plays the game on a Pixel and an iPhone profile. The README explains how to play, install and back up.

**Done**
- **The balance script** (`scripts/balance.ts`, `scripts/balance-worker.ts`, `npm run sim:balance`): 4,800 lives (30 breeds × 4 policies × 40 seeds) and 279,000 battles (every breed pair, mirrors included, at totals 1,000 / 2,000 / 3,000, 200 seeds a cell, 8 NPC rolls a side, sides alternating) across worker threads in about two minutes; writes `docs/BALANCE_REPORT.md` with the raising table, a per-breed battle summary, the full matrices and the list of everything outside §26.
- **Raising:** every breed inside its band without any tuning: Great 84.8 %, Good 79.7 %, OK 65.6 %, Neglect 38.6 % of the nominal life (all breeds between 77.7 and 81.6 under Good care); Good-care outcome rates and the stat-total targets hold for every breed.
- **Battle, before tuning:** only 61 % of pairs sat inside 30–70 %. Two causes. The AI's kiting rule sent a caster to Close whenever it could not outrun its opponent, even one that was not chasing, so INT breeds spent whole matches poking with their weakest POW basic (Scrollopus 19 %, Paladove 24 %, Gearhoot 28 %); and attack counts tracked the breed's guts rate (4 a match at rate 18, 11 at rate 8), so the walls lost (Aurelwyrm 23 %) and the fast casters won (Ashwraith 77 %).
- **Battle tuning (numbers only; the formulas are untouched):** the AI treats only an opponent that is pressing forward, or that wants a closer band, as a chaser (§12.10 rule 6); every INT breed's INT basic now covers Close (Drizzle Puff, Gust Feather, Crackle, Lens Flash, Halo Spark, Seed Sneeze and Ink Flick moved to Close; Woolly Bump, Talon Tick and Trunk Bop to Near); breed guts rates narrowed from 8–18 to 10–14; the NPC stat weight base rose from 0.6 to 0.9; Fortified −30 %, Unshakable −20 %, Hard Shell −25 %, Live Wire +10 %, Green Thumb ×2; and 168 technique force and hit values nudged toward the top or bottom of their §10.2 bands by breed (walls and the weak casters up, the dominant breeds down). CONTENT §2, §2.1 and §3 and NEW_MONSTERS are updated to match.
- **Battle, after tuning:** 415 / 419 / 405 of 435 pairs inside 30–70 % at 1,000 / 2,000 / 3,000 (95 %, 96 %, 93 %); every breed's mean win share is between 38 and 63 %; mirrors 45–55 %; attacks 4–12 a match on average; the mirror KO average 15–35 % at 1,000.
- **Special cups** (`TOURNAMENT.specialScalePct`): the Masquerade Cup, the Crowns and the Legend Cup generate their opponents at your stat total (never below the grade's band); Corin follows you all the way at the Crowns and stays inside the band in the Officials. GAME_DESIGN §13 notes it; `specialCups.test.ts`.
- **Bug bash:** the Shrine's tabs never wrap (the segmented control scrolls sideways at large text sizes); the Journal's chips scroll in one row; three lightning bolts strike in turn with the flash.
- **Playwright** (`playwright.config.ts`, `e2e/smoke.spec.ts`, `npm run e2e`): new game → a week of training → a CPU battle at ×4 → the save survives a reload, on Pixel 7 and iPhone 14 profiles, in the installed Google Chrome (no browser download). Outside `verify`, so the deploy stays fast.
- **Tests** (465, 33 new): the special cups; every breed under Good and Neglect care (sampled); the battle sample is now a hard rule (≥ 80 % of sampled pairs inside 30–70 %, none outside 20–80 %) with `WILDSONG_FULL_SIM=1` for the whole matrix; the data, shrine, trait and habit tests follow the new numbers.
- **README** (how to play, install, back up and restore, the Lab, the developer commands), **CREDITS** (Playwright), version 1.0.0, tag `v1.0.0`.

**Decisions worth knowing**
- The matrices are a dev script, not a test: `npm test` would take twenty minutes with them. The report is the record; re-run it after any battle or breed change.
- Lootlid is the one breed left clearly below the band (30–42 % mean): it is the "challenge / joke breed" with a non-battle trait, and 25 of the 66 remaining misses involve it. Making it even keel would need a battle trait or a formula change, which is the owner's call.
- The mirror KO average at 3,000 is 18.8 % against a 3–15 % target: Heavy techniques at 37–49 % of HP make late-game cannon mirrors end early. Lowering it would mean touching the damage formula, so it is recorded rather than forced.
- Per-breed mirror KO rates range from 0 % (walls) to 90 % (glass cannons) by design; the report shows them but only checks the average.

**Next:** the owner's playtest. LATER items start after v1.0 (Sketch Stone, local Versus, coach mini-games, a trainee stall, leagues, cloud sync, localization).

**Known issues**
- See the balance notes above: Lootlid, a handful of caster-versus-wall pairs at 3,000 (the worst 20–30 % / 70–83 %), and the 3,000 KO average.
- The Playwright run needs Google Chrome installed on the machine and is skipped on CI.

## M8: Sound, juice and polish (2026-10-23) · v0.10.0

**Live:** the game has a voice and a pulse. Original music follows you around (the ranch by season, Town, the Shrine, battle, the farewell, a victory fanfare), every tap, drill and hit has a sound, and the ranch stage is a painted scene that changes with the season and the weather (drifting clouds, rain, snow, a storm with lightning). Each drill has its own vignette, monsters show emotes, battles have lunges, projectiles, hit flashes, knockback, crit sparkles, KO flops and victory hops. The title screen helps you install the game, the ranch reminds you to back up, Settings can check for updates, the battle pads flip for left-handed play, Reduce motion really stops everything, the heavy screens load lazily, and the planner runs up to eight weeks on its own.

**Done**
- **Schema v7** with a migration and tests: `planner` (queue, log, last stop). Settings (not in the save; validated with fallbacks) gain master, music and effects volumes, the left-handed layout, the install-card dismissal, the backup stamps and the backup baseline.
- **Audio** (`audio/sfx.ts`, `audio/music.ts`, `audio/player.ts`, `ui/lib/music.ts`): 21 ZzFX effects written for this game; nine original loops composed as step-sequencer patterns and rendered by a tiny pure synth (square, triangle, saw, sine, noise; attack, gate, release, soft clip), cached as audio buffers; audio unlocks on the first `pointerup`, ZzFX is imported then (it creates an AudioContext on load) and pointed at our context; iOS gets `audioSession.type = 'ambient'`; the context suspends in the background; music fades between tracks, ducks under effects, and the victory stinger returns to the previous loop. Hooks: every button (one delegated listener; `data-silent` opts out), drill stingers by outcome, battle `fire` / hit / crit / miss / KO / special / win / lose, coins at Basil's, the Market and the Guild Library, the stone hum at the Shrine, learning from a Songsheet, the grow-up and prime moments, a letter with the week, the planner's stop. Settings has three sliders and a Test sound button.
- **Backgrounds** (`art/backgrounds.ts`): layered SVG strings (sky gradient by season × weather, sun, clouds, far and near hills, the barn, the fence, a tree with spring blossom / summer and autumn foliage / bare winter branches, ground) with CSS-animated overlays: drifting clouds, rain, snow, a storm with one flash every 7 s (§24). Lite mode draws fewer drops and flakes. Town, the Shrine and the arena get lighter scenes (rooftops, standing stones, a ring). The ranch stage, the Town and Shrine banners and the battle arena use them.
- **Vignettes** (`art/props.ts`, `styles/polish.css`): a motion for each of the 11 drills (sprint, heave with the log flying over the fence, think while the stone slides home, throw with the pinecone hitting the target, dodge the swinging gourds, brace under the shaking oak, drag the plow, sit still under a breathing moon, chase blowing leaves, brace under the falling water, lift the quarry block). Transforms and opacity only (a test reads the stylesheet and checks), skippable as before, instant at speed "instant".
- **Emotes** (`core/emotes.ts`, `components/Emote.tsx`): ♥ for a devoted, fresh monster or after praise; ?! for a request or a pending event; 💢 for stress or after a scold; 💤 for tiredness or sickness. On the ranch stage and the drill result.
- **Battle effects**: a lunge for Close/Near techniques, a glowing shot for Mid/Far (flown with a CSS variable set from the arena's width), a hit flash and knockback on every hit, a five-star sparkle on crits, a KO flop that stays down, a victory hop on the result, and the arena backdrop. Fixed a keyframe name clash (`ws-float` in both battle.css and monster.css) that had the damage numbers bobbing instead of rising.
- **Install help** (`lib/platform.ts`, `components/InstallHelp.tsx`): a title card when the game is not running from its icon (hidden for two weeks after Later): the native Install prompt when Chrome offers one, otherwise iPhone or Android steps (detected from the user agent, iPadOS included); the same steps from Settings.
- **Backup reminders** (`save/backup.ts`, `components/BackupCard.tsx`, `lib/backup.ts`): every 7 real days or 8 in-game weeks since the last export (the day rule counts from the app's first run until the first backup); Later snoozes a week; Save a backup shares on phones and downloads elsewhere; exports from Settings stamp the time too, and Settings shows the last backup.
- **Updates** (`store/updateStore.ts`): the service worker is registered once in a store; the toast still only shows on the title and the quiet ranch; Settings has Check for updates (up to date / update found / offline) and Restart when one is waiting.
- **Left-handed layout**: the pads become ▶ · Push · ◀ and the Auto / speed / pause row flips (CSS direction, no logic change).
- **Accessibility**: the Reduce motion setting sets `data-reduce-motion` on `<html>`, and the same rules as the OS media query stop every animation and the particles; a visible focus outline everywhere; labels on the emotes, the install and backup cards (`role="status"`), the planner's remove buttons; no flash above 3 Hz (storm, hit flash, crit).
- **Performance**: `lib/lazy.tsx` loads Battle, Tournament, Lab, Expedition, Journal, Odd Jobs, Farewell and Credits Roll on first use; ZzFX loads on the first tap. The build is now 24 chunks; the largest is 171 kB (was one 589 kB file). Versus's picks moved to `store/versusStore.ts` so the ranch does not pull the Versus screen in.
- **The planner** (`core/planner.ts`, `screens/ranch/Planner.tsx`): queue up to 8 drills and rests, run them one a week (a short pause between, scaled by the speed setting, autosaved each week, Stop any time); keeps last month's food; no praise or scold; stops before a week on a request, a pending event, a trial, a cup in progress, a trip, a Journey, an absent monster or a new letter, and after a week on illness, a breakdown, a lifespan warning or past prime, a forced rest, the Signature, a grow-up, prime, fatigue ≥ 60 or stress ≥ 50; a drill that needs the Training Yard is dropped. The summary lists every week with its outcome, gains and pay, Wren says why it stopped, and Keep going resumes the rest of the queue.
- **Tests** (432, 35 new): the planner (cap, a clean run resumed after a letter, determinism, no reaction, the food default, each stop reason, forced rest, an unavailable drill, blockers); emotes; the sequencer (tokens, every track renders finite in-range samples, determinism, loop length) and the sound table; backgrounds (every season × weather, layer classes, determinism, lite); the vignette coverage and the transform/opacity rule; backup rules; platform detection; the music-to-screen map; schema v7 and tidying.
- **Headless check**: the title with the install card, the stormy and snowy ranch, a vignette, the praise emote, the planner sheet, a run that stopped for Tomas's letter and resumed, Settings at 130 %, a Versus battle in the left-handed layout with effects, the result, Town, the Shrine and the Journal at 360 px, with no page errors.

**Decisions worth knowing**
- Ordinary cups do not stop the planner (almost every week holds one at or near your grade); invitations and other letters do. Enter a cup between runs.
- The planner answers nothing: queued drills get no praise or scold, and a request pauses the run with the card waiting on the ranch.
- Settings keep their own fallbacks instead of a version: new fields arrive with defaults and never fail validation.
- The backup reminder's day rule counts from the app's first run on this phone until the first backup; the week rule starts with the first backup, so an old ranch is not nagged on the first launch after this update.
- The install card hides in the installed app and for 14 days after Later; Settings always has the steps.
- The music is written as note patterns and rendered in code, so there are no audio files in the repo and nothing to credit but ZzFX.

**Next (M9):** whole-life sims for every breed under the four care policies and the breed battle matrix with `docs/BALANCE_REPORT.md`; the owner's bug bash; the final README and CREDITS; `v1.0.0`.

**Known issues**
- Sound and music cannot be checked headlessly; the owner's phone is the first real listen. The volumes default to 80 / 55 / 100.
- The Shrine's "Stones (0)" tab wraps onto two lines at larger text sizes.
- The planner shows the weekly report in Wren's bubble as it runs, but drill results flash past without their vignette (by design: the summary has every week).
- The lightning bolt is drawn in one fixed spot on the ranch and the arena.

## M7: Exploration and unlocks (2026-10-23) · v0.9.0

**Live:** the valley opens up. Tomas's letters invite you to four expedition sites with tap-to-move node maps, stamina, obstacles, hidden spots, fog, treasure and a guaranteed route to each site's special stop. All eight locked breeds now have a way in: the cocoon, the Lantern Vigil, the storm chase, the Masquerade Cup, the Brass Blueprint, the Tide Pool, the Strange Chest and the four Crowns. Ranch upgrades are on offer every May, rumors arrive by mail and at Basil's, the Journal keeps the Encyclopedia, Sleeping Stones, Rumors, Records, Titles and the Hall of Fame, Basil buys expedition treasures, and Turnip Sort pays up to 150G a week.

**Done**
- **Schema v6** with a migration and tests: `expedition` (the trip in progress), `pendingEvent`, `unlocks` (rumors heard, the masked invitation, the Vigil, the cocoon, visits per site, the Reefclaw, the Wyrm Scale), `records`, `oddJobWeek`, `memorialVisitMonth`, `encyclopedia.combos`; new mail kinds and week actions. Loading rebuilds the map from the trip's seed and drops a trip whose stops don't fit it; nothing else is lost.
- **Expeditions** (`core/expedition.ts`, `data/expeditions.ts`, `screens/ranch/Expedition.tsx`): invitations in week 1 of each site's months (the trip can start any week of that month, as the week's action); a forward-only map of 12–16 stops rebuilt from (site, seed); stamina 50 + LIF/8, steps 5–12; obstacles at the site's thresholds with Detour (−10) or Turn back; search spots, hidden spots that only INT reveals, treasure, fog (lost = max(5 %, 30 % − INT/30): −10 stamina and a step back), the camp; Retreat keeps everything; 0 stamina limps home with everything. The "spine" from the trailhead to the event node holds only the stated obstacles, no fog, and costs at most the base stamina, so a monster that meets the letter always reaches the key item (tested over 200 maps per site). Loot: sellables, sweets, catalysts, toys, fruit and universal Songsheets of the listed families (a Grand Sweet when every one is owned). After the trip: fatigue +40, stress −10; weeks 2–4 pass as away weeks. Tomas narrates.
- **The eight chains** (`core/unlocks.ts`, `core/events.ts`): Velvesper (June week 4: a Nibblegrub aged 144–240 weeks, loyalty ≥ 70, fatigue ≤ 20, stress ≤ 15, 12 puddings → a 4-week cocoon; emerges with the same sub-breed, 80 % of its gains on the new base, the new breed's grades and trait, +60 weeks, techniques carried by family); Ashwraith (Sister Mara's letter the first week 1 after any farewell, the Vigil at the Shrine, the lantern offered); Zipwisp (a storm week, SPD ≥ 300, calm and rested: a yes/no card; yes uses the week and brings Stormglass); Mirrorkin (Basil's September whisper once any monster reached B opens the Masquerade Cup every October: a single match against the Masked Breeder's Mirrorkin; the Shard Mask); Gearhoot (the Sunken Library's archive at INT ≥ 350; the Blueprint handed to Dr. Pell; the Market sells Gearhoot for 2,500G); Reefclaw (the Tide Pool, then June week 1: it moves in, to the Freezer when the ranch is taken, and becomes the summer Market pick); Lootlid (Thornwood's chest: 35 %, certain on the third visit; the breed wakes even with no room); Aurelwyrm (the fourth Crown brings the Wyrm Scale once). Key items are offered on the Shrine's new Offerings tab.
- **Rumors and letters**: invitations, rumors (chest and archive with Tomas's letters, the cocoon from a year-old grub, storms in June, the masked card, the tide pool with Ines's May letter, the wyrm with a Crown invitation), the Vigil, the upgrades letter, the Reefclaw, the Wyrm Scale; Basil repeats the latest rumor; the Journal's Rumors page sharpens from "???" to heard, in progress and awake.
- **Ranch upgrades** (`core/upgrades.ts`, `screens/town/Upgrades.tsx`): Cozy Barn 8,000G (rank 2), Training Yard 10,000G (rank 3), Tide Pool 12,000G (rank 4), Lantern Garden 6,000G (a name on the Memorial); bought from the May letter or the Guild any time; the Lantern Garden's monthly visit at Dr. Pell's (stress −5) on top of its extra Heartstone slots.
- **The Journal** (`core/journal.ts`, `core/titles.ts`, `screens/town/Journal.tsx`): Encyclopedia (every breed owned / awake / asleep with its teaser, the 21 variants, looks collected), Sleeping Stones (wake from here too), Rumors, Records (best total, oldest, cups, expeditions, Journeys, stones, generation, sweets, sheets, drills), Titles (all 20 with how to earn them; Lineage Keeper, Encyclopedist, Collector, Gentle Heart, Sleeper Awakened, Songbook Scholar, Sweet Tooth and the five unlock titles are checked every week so none is missed), Hall of Fame. A new game's first monster now counts in the Encyclopedia; older saves catch up at the next week's end.
- **Odd Jobs** (`core/oddJobs.ts`, `screens/town/OddJobs.tsx`): Turnip Sort, 30 seconds, tap Basket / Rock pile or swipe, a shrinking window, missed items score nothing, +5/−5 capped at 150G, once per in-game week; the chute is dealt from a seed the game's RNG hands out.
- **Also**: Basil's Sell tab for expedition treasures; the Market's unlocked offers; the Masquerade opponent, prizes and `records.cupsWon`; the ranch's Expedition button and storm card; `expedition.css`.
- **Tests** (397 total, 50 new): map determinism, shape and reachability, the spine guarantee walked on 800 maps, stamina and step costs, obstacles with Detour and Turn back, hidden spots, the fog formula and reposition, exhaustion and Retreat, loot tables, the chest's odds and pity timer, the archive, the crystal heart and sky puzzle, invitations and a four-week trip through the controller; every chain from a scripted state plus re-triggers (a missed cocoon, a declined spark, a lost masquerade, a full Freezer for the Reefclaw, an ignored Vigil, a second Crown run); the week's mail and events; upgrades and the garden; Turnip Sort pay, cap, once a week and the ramp; titles; records; schema v6 and tidying; and an integration run (letter → the chest → the Lootlid → home → sell → a Sleeping Stone wakes) with a save round trip.
- **Headless check**: a phone-sized Chrome run through the ranch, the expedition sheet, a whole map to the camp, the summary, selling, an offering, the Blueprint, the Journal's pages, an upgrade, the Mailbox, the Market and a full Turnip Sort round, with no page errors.

**Decisions worth knowing**
- The expedition map is played in week 1 as the week's action and saved after every tap (it resumes mid-map); the loot, key items and after-effects apply the moment the trip ends; weeks 2–4 are away weeks. The trip can start any week of the invitation month.
- Fog moves the party to a random stop of the same or the previous layer, never forward; the spine never holds fog or hidden spots.
- The storm spark is a card you can decline; the cocoon just happens when every condition holds; an unanswered spark lapses at the end of the week.
- "50 variants" for Collector counts distinct looks owned (main/sub names, special variants included).
- A Lootlid with no room anywhere still wakes the breed; the Reefclaw with no room tries again next June.
- Titles computed from the save (not cup placings) are awarded at the end of every week, at the farewell and after an unlock, so they can never be missed.

**Next (M8):** sound and music, drill vignettes, seasonal backgrounds and weather overlays, the install-help card, backup reminders, the update flow, the left-handed layout, text sizes, the accessibility and performance passes (the bundle is over 500 kB now; lazy-load the heavy screens) and the planner queue.

**Known issues**
- The Journal's chips wrap onto three rows on a 360 px phone; fine to use, a little tall.
- Expedition stops are emoji glyphs with labels; M8's art pass can draw proper icons.
- The Masquerade Cup and the Crown opponents are generated at your grade's band, so a very strong monster wins them easily; M9's balance pass will look at the special cups.

## M6: Legacy (2026-10-23) · v0.8.0

**Live:** loss has meaning. A life ends in a farewell scene with an epitaph; the monster joins the Memorial wall and leaves a Heartstone; the ranch waits while you thaw, buy or sing up the next one. Dr. Pell's Lab holds the Freezer, the fusion table with its odds, the Memorial, the Heartstone shelf and (on Gentle) the Elder Grove. The Shrine of Echoes is open in Town with Sleeping Stones, the Encyclopedia and 21 secret phrases. The Market sells monsters after the first.

**Done**
- **Schema v5** with a migration and tests: `freezer`, `elderGrove`, `memorial`, `heartstones`, `encyclopedia`, `sleepingStones`, `unlocked`, `elderMentorMonth`; a Journey remembers its Elder mentor; monsters gain `heirloom`. Loading tidies the lists (duplicates, broken entries, the 20-slot and Heartstone caps, unknown variants) and always keeps the starters unlocked.
- **The farewell** (`core/legacy.ts`, `screens/Farewell.tsx`): the ranch at dusk, Wren's scene and two "remember when" moments, the best-moments card, a one-line epitaph (80 characters, editable later), Say goodbye → the Memorial (cause, epitaph, week) plus a Heartstone when the shelf has room; on Gentle the monster also walks to the Elder Grove. The ranch is then empty: the calendar waits, and the empty-ranch card offers the Freezer, the Market, the Shrine and the Lab.
- **The Freezer** (20 slots): freeze the active monster from Dr. Pell's (free, instant, not during a cup, Journey or Trial), Make active (the current one takes the freed slot), Move to the Lab Library, View / Edit / Export. Frozen monsters and Elders appear as a source in the Lab Library, Versus and the Battle Lab; the Library's cards gained Send to the Freezer and Make active (the current monster goes to the Freezer after a confirm). The editor has a `freezer` origin that saves back in place.
- **Fusion** (`core/fusion.ts`, §15 exactly): candidate mains 4/3/2/1 and subs 3/2/2/1 × lineage strength, locked mains removed, normalized with largest-remainder rounding so the board sums to 100, under-1 % outcomes dropped, at most six shown; the Lineage Seal doubles P1's main weight. Compatibility ranks the parents' stats and the baby breed's grades (ties by base stat), M = agreeing ranks, Dr. Pell's four comments. Baby stats = base + round(offset · P · K) + catalyst with P = 20 % + 9 %·M and K by rarity; grades, guts, lifespan and trait from the baby's breed; techniques by the two §15 cases (two thirds of P1's non-Basic ones with uses and levels when the main matches, otherwise one per family from the baby's kit); nature and form 2:1; generation max + 1; the 1,000G fee; shards, the Amber Charm and the Lineage Seal consumed. The parents become Ancestors on the Memorial; the baby takes the ranch when it is empty, else the Freezer. The Monster Card shows a Lineage card (generation, parents and grandparents by name, the Heirloom, the variant).
- **Heartstones**: created at the farewell from the donor's trained gains (stat − breed base) and most-used technique family; up to 10 (15 with the Lantern Garden); given to one monster under 48 weeks that has none: +15 % of the gains per stat capped at +60, plus the Heirloom (+3 hit on that family in the engine).
- **The Elder Grove** (Gentle): Elders fuse like frozen monsters, can be made active, and mentor once a month: a Journey at the site of the Elder's best stat gets +10 % technique chance (Wren says who came along).
- **The Shrine** (`core/creation.ts`, `screens/town/Shrine.tsx`): two fields, Randomize from a 50-word list (drawn from the game's RNG), the preview hum, Sing (free; to the ranch or the Freezer), a sleeping breed's teaser and the Sleeping Stones page (wakes for free once the breed unlocks), the Encyclopedia (breeds and variants owned; every Shrine birth can be sung back for 500G), Edit before you start.
- **Secret phrases** (`data/secrets.ts`, `core/variants.ts`, `art/monster/variants.ts`): the 21 CONTENT §12 phrases stored as salted cyrb53 hashes; a hit makes a pure monster of the variant's breed with its own palette (a render override), the stat or lifespan bonus, and the perk: likes every food, loves Honey Bread, birthday calm (−10 stress each birthday), Far +5 hit, Wither +5, prizes +25 % (stacks with the Gilded trait). Eight of them are sleeping until M7's unlocks and become Sleeping Stones like any other.
- **The Market** in Town: the four starters at 1,500G and the season's breed at 2,500G, to the ranch or the Freezer.
- **Tests** (347 total, 43 new): the Freezer rules, Heartstone gains and caps, the farewell on both modes, Elder mentoring, odds normalization and the Seal, locked and rare outcomes, compatibility and K, baby stats with catalysts, both inheritance cases, `fuse` with its refusals, the Shrine in play (births, the Freezer, Sleeping Stones, re-creation), the Market, each secret phrase, the variant hooks (food, birthday, hit, wither, prizes), the render override, schema v5 and tidying, and an integration test that lives out a monster, says goodbye, gives the Heartstone, sings twice and fuses, then validates the save round-trip. The 1,000-phrase Shrine snapshot pins the whole contract with one hash.

**Decisions worth knowing**
- Two of the five phrases pinned by the M2 Shrine snapshot ("wildsong", "hello world") are secret phrases; their rolls changed on purpose and the snapshot was updated. Everything else rolls exactly as before.
- Secret phrases are checked on the "Song or phrase" field after normalization; the artist field still shapes the offsets.
- A secret variant is a pure monster (so it keeps the +10 % lifespan and Signature access). Its name suggestion is still the first word of the phrase.
- Fusion percentages are whole numbers that always add up to 100 on the board, so the roll uses those shown numbers.
- The empty ranch does not advance the calendar; weeks only pass with a monster at home.
- "Move to the Lab Library" is how a Freezer slot is freed; nothing on the ranch is ever deleted.

**Next (M7):** Expeditions, the eight unlock chains (the Sleeping Stones and locked secret variants wake with them), weather events, ranch upgrades (the Lantern Garden's extra Heartstone slots are already honoured), rumors, the Journal pages and the Lantern Vigil mail.

**Known issues**
- The Lantern Vigil invitation after a natural death waits for M7's unlock chain, so the farewell does not yet send Sister Mara's mail.
- The family tree shows names only for relatives this ranch still knows (the Memorial, the Freezer, the Grove, the ranch); an imported monster's parents show as "Unknown".
- The farewell's Back button returns to the title; the ranch is reachable again through Continue.
- The Heartstone card lists "+0 stat points" for a donor that never trained; the Heirloom still applies.

## M5: Tournaments, ranks and Journeys (2026-10-23) · v0.7.0

**Live:** battles have stakes. The 48-week cup calendar, Officials and promotion, breeder ranks, the Crowns, the Legend Cup and the Hall of Fame, rival breeders with readable habits, and Journeys with the Mentor's Ledger, the Trial, mentor bonds and sale months. Pure breeds learn their Signature at Prime.

**Done**
- **Calendar and entry rules** (`data/calendar.ts`, `core/tournament.ts`): every CONTENT §9 event with its grade, format, purse and year rules (even/odd cups, Summit years), the §13 entry rules with reasons (grade, "too easy" below your grade, injured/sick/away, invitations, age/nature/technique-type rules), and the week's events on the ranch.
- **Cups**: participants generated by the seed (year, week, cup id) with `npcMonster`, rivals by grade (each eligible rival joins with a 50 % chance, at most two), Corin Hale in your Officials, the Rival Showdown and the Crowns at your total × 1.05 (Aggressive from grade A, an Aurelwyrm at the Crowns); round robins of 4 and 6, eliminations of 4 and 8, single matches and the Summit relay; points 4/3/2/0 with head-to-head, KO count and HP % tiebreaks; a KO'd fighter withdraws (walkovers); NPC-only matches run through the engine; the player's matches use the battle screen (Manual on the pads, or Auto with Skip). A cup lives in the save and resumes after the app closes.
- **Finishing a cup**: purse shares 100 / 40 / 20 % plus 50G × gradeIndex per win (Gentle ×1.25, Gilded +15 %), item prizes by tier (sweets, Grand sweets, universal Songsheets into the Songbook, Wondercake for an Official, the Signature sheet or a Potential Pearl for a Crown, a Tempo Bell and three Wondercakes for the Legend), fame (table, Regal +5, −1 without a podium), three random stat gains for a podium (±1 by battle like), the §13 after-effects, KO extras with the injury roll (and the Classic risk), records, mastery from the matches, promotion on your grade's Official, breeder rank (E–A Officials → 1–6, the S Official invites to the Crowns, the Crowns → 7–10), invitations by mail, the Hall of Fame on a Legend win, and the CONTENT §14 titles (First Ribbon, Ascended, S-Class Breeder, Crowned, Four Crowns, Legend of the Vale, Grand Breeder, Iron Bond). Rank 10 rolls "The Wildsong Rises" once.
- **Rival habits** (`core/battle/ai.ts`): opens Far, banks guts for a Heavy, walks straight into Close, backs away when approached, spams Wither, waits at 99 guts, pushes whenever touching (it steps in to touch first), dashes in below half HP, steals guts. Each is shown as a hint on the opponent card.
- **Journeys in play**: the Mentor's Ledger (sites, open months, gates, cost, each technique's requirement and your score, the tier or exact %, the four-week forecast, the bond count), the weekly beats as Wren's lines in the week summary, the Trial at the end (a wild monster of the site's breed at your grade or one up; fight, let the monster fight, or simulate; 600 × gradeIndex, a 10 % Moonfruit, injury rules on a KO), mentor bonds (a Mentor's Charm every 8 Journeys at a site, −50 on that site's requirements; five new key items), sale months (two a year rolled each January, mail in week 1, 1,000G Journeys), and the "make room" prompt when a technique is earned with a full list.
- **The Signature** (§10.4): learned at the end of the week a pure breed enters Prime with loyalty ≥ 60, or at Glacier Bastion with DEF + its type stat ≥ 700.
- **Town**: the Breeders' Guild (this month's cups, rank and how it climbs, Officials and Crowns won, invitations, titles, the Hall of Fame, the Library) and the Mailbox (sales, invitations, promotions, rank; unread count on the Town row).
- **Schema v4** with a migration and tests: tournament, trial, guild, Hall of Fame, mail, sale months, Journeys per site, titles.
- **Tests** (304 total, 26 new): the ten-year calendar, entry rules, cup building and determinism, Corin's scaling, round-robin and elimination flow with KO withdrawal and tiebreaks, finishing with every prize and effect, the rank ladder from E to the Legend, the habits, the Journey additions, the controller's cups, Trial, mail and Signature, and a three-year scripted raise that enters every eligible cup on Auto, takes two Journeys with Trials and gets promoted.

**Decisions worth knowing**
- Rank reading: the first Official win at each grade E–A raises rank 1 → 6; the S Official win invites to the Crowns; each Crown's first win raises rank 7 → 10 (the doc leaves one step ambiguous).
- The Masquerade Cup shows as "invitation only" until its rumor arrives with M7's unlock chains.
- The Summit relay: you fight your grade's slot; four NPC teammates are simulated; a team win needs three of five.
- The Journey Trial waits at the mentor's until the next week begins, then must be settled before anything else.
- Entering a cup is the week's action; Repeat last week never repeats a cup.

**Next (M6):** the Freezer, Fusion, the Memorial, Heartstones, the full Shrine (teasers, Sleeping Stones, the Encyclopedia, secret phrases) and the Market's seasonal stock.

**Known issues**
- The Journey's four beats are Wren's lines in the week summary rather than a separate four-beat screen; the full vignette treatment is M8 polish.
- Rival monsters use the §13 NPC generator at the cup's grade, so a rival's "signature monster" is a fresh one each cup (no persistent rival rosters yet).
- The Vale–Coast Summit's NPC teammates are not shown; only the team result is.

## M4: Battles (2026-10-22) · v0.6.0

**Live:** real-time 1-D duels. The Monster Lab has **Versus** (any two monsters, You vs CPU or CPU vs CPU) and the **Battle Lab** (hundreds of fights in the background with the numbers). The ranch's Battle button opens a friendly spar with the active monster.

**Done**
- **Engine** (`core/battle/engine.ts`): a 30-tick-per-second fixed-step simulation, a pure function of (monster A, monster B, seed, inputs). Integer fixed-point throughout: positions in centi-units, percentages in tenths, multipliers in thousandths, and an integer square root for the damage ratio, so a seed replays identically on every phone. Ranges and bands, walking (backing away ×0.85), dash (8 guts, ×3, 18 ticks, 60-tick cooldown), push (touching, 15-tick shove, 250 units, 90-tick cooldown), guts (start 50, cap 99, +1 every `gutsRate` ticks, paused during your own animation), distraction (§12.6, "?!"), KO, time-up by HP % and forfeit. A technique resolves on the tick it is fired; the attacker is then busy for its animation.
- **Formulas** (`core/battle/formulas.ts`): §12.5 hit (with advantage and disadvantage), damage, crit, wither, guts multipliers, form. Every reference row and hit example in §12.5 is reproduced exactly by tests.
- **Technique effects** (§10.3): multi-hit (each hit rolls), heal (always lands, Green Thumb +50 %), stun, drain, recoil on a miss, guts steal, knockback, lunge, jackpot. Mastery bonuses (Lv2 +2 hit, Lv3 +2 force).
- **Specials** (§12.7): Last Stand, Valor, Rage, Bulwark, Clutch, Composure, each once per battle, one timed special at a time, rolled every time the condition occurs.
- **All 30 traits** in `core/battle/traits.ts`, including the ten from NEW_MONSTERS §2 (Dragonheart's one-off guts, Unshakable's immunity, Underdog, Blessed's regen, Moonlit, Green Thumb, Eight Arms, Statue Pose, Battering Ram, Chill).
- **CPU AI** (`core/battle/ai.ts`, §12.10): cooldown, use rates by personality (the six personalities), choice weighted by EV^1.5 with the big-move bias, movement to the best band every 15 ticks, push when wanting distance, dash when wanting to close, the rookie guts reserve. One addition on top of the doc: a fighter that cannot outrun its opponent stops trying to kite and fights at the best band it can reach (without it, some kiters never attacked).
- **NPC generator** (`core/npc.ts`, §13): stats by growth-grade weights with ±8 % noise to an exact total, technique sets by grade, 1–2 universal techniques from grade B, loyalty and fame bands. Rivals, habits and cup seeding come with M5.
- **Battle screen** (§12.11): names, HP and guts bars (numbers in the Lens), timer, special badges; the arena with both monsters (B mirrored) moved with transforms only, a range ruler with the gap marker, floating damage, "Crit!", "Miss", "?!" and special names; four technique columns (Close · Near · Mid · Far) with cost and live hit %, the current column glowing, unaffordable cards dimmed; **Assist** (tap a card in another column to walk there and fire; a setting, on by default); ◀ ▶ hold pads, double-tap ▶ to dash, Push when touching; Auto, ×1 / ×2 / ×4, pause with Skip and Forfeit; the result card with Rematch and Done. Haptics on Android after the first tap; screen shake ≤ 4 px and none with Reduce motion.
- **Versus** and **Battle Lab** in the Lab (§19): pickers from the ranch, the Library and the Presets; personalities; 60 / 90 / 180 s. The Lab runs 100 / 500 / 1,000 battles in a Web Worker (sides alternating) with a progress bar, win / draw / KO %, length, attacks, hit rate, damage per hit, most-used techniques, and a CSV download.
- **Tests** (278 total, 45 new): formula reference tables, traits, specials, engine determinism and replay, a 1,000-seed fuzz (no NaN, no negative HP, ends by the timer; about 1 ms per battle), AI attack counts and personalities, stats, NPC bands, and the §26 balance cells.

**§26 battle results (NPC stats, alternating sides, Steady AIs)**

| Target | Doc says | Measured |
|---|---|---|
| Mirror match | 45–55 % | 51.5 / 48 (200 seeds) ✓ |
| +10 % total stats | 62–80 % | 68 % ✓ |
| +30 % total stats | 85–96 % | 92 % ✓ |
| KO rate, even fights (five starter mirrors) | 15–35 % at 1,000 · 3–15 % at 3,000 | 21 % · 9 % ✓ |
| Attacks per monster per match | 4–12 | 6.8 at 1,000 · 9.5 at 3,000 ✓ |
| Breed pairs at equal total (15 pairs × 3 totals) | 30–70 % | 29 of 45 cells inside (64 %) |

The pair sample is reported by the test and must keep at least 55 % of its cells inside the band; the full 30 × 30 matrix at three totals is M9's job, as the build plan says. The misses are the archetypes §27 warned about: fast-regen casters (Coilfang, Zipwisp, Starhowl) beat slow walls (Nimbusheep, Petalphant) by more than 70 %. One AI number was moved: the technique cooldown's top end from 75 to 84 ticks, so the fastest-regen breeds stay under 12 attacks a match.

**Decisions worth knowing**
- Versus and the spar are exhibition only: no fatigue, lifespan, record or mastery changes (tournaments in M5 do all of that).
- The engine mutates one state object (immutable ticks made the Battle Lab crawl); the UI reads snapshots.
- The ranch's Battle button is a spar at the Guild arena: the active monster is pre-picked as side A.

**Next (M5):** tournaments, ranks, rivals and their habits, NPC seeding by cup, Journeys with the Trial, after-battle effects, the Results and Guild screens.

**Known issues**
- Some fast-caster vs wall matchups sit outside 30–70 % at equal totals (M9 balances the full matrix).
- Rival habits are a `none` hook until M5. The left-handed layout and sound arrive with M8.
- The vignette-style attack animation is a squash; lunges, projectiles and KO flops are M8 polish.

## M3: The ranch loop (2026-10-22) · v0.5.0

**Live:** the game can be played. New Game → a monster → weeks of training, resting, feeding, shopping, items and Songsheets → old age and a farewell. Saves survive closing the app.

**Done**
- **The turn controller** (`core/game.ts`): the week's phase and the monster's pending request are part of the save (`weekPhase`, `pendingRequest`), so the app can be closed at any moment and reopened exactly where it was. Begin week → answer request → choose action → praise/scold → finish week; "Repeat last week" remembers the last drill or rest; an action menu says which buttons are on and why (sick: rest only; missing or at the clinic: wait a week). Free actions (items, sheets, edits) never use the turn. Food is now charged in week 1 (§9: the Guild Loan covers a shortfall at a 10% fee).
- **Economy, Market, Guild** (`core/economy.ts`, `core/market.ts`, `core/guild.ts`): buying with reasons (rank gate, grade C gate for Grand sweets, debt, money, quantity), max affordable, shop stock with gates; fixed-seed Market gifts (four starters plus the season's breed; same monster for everyone); Songsheets for sale with rank gates, ownership, ★ fit and learnability for the active monster.
- **Odds, Wren, onboarding** (`core/odds.ts`, `core/report.ts`, `core/onboarding.ts`): Guided words at the `TRANSPARENCY.oddsBands` edges and exact percentages for the Lens, with truancy taken off the top; every weekly line, drill line and event line Wren says (never the same line twice in one report); twelve one-time tips in the order a new player meets them, the first month guided.
- **Schema v3**: the game state gains the week phase, pending request, last action, the active monster's edit history, tips seen, counters and a sandbox flag, with a migration and tests. `AppSettings` gains transparency, text size, animation speed and sound placeholders (never-fail validation).
- **New Game**: names, difficulty cards in plain words, a Guild gift (five portraits) or the Shrine (a locked main breed makes the stone hum and no monster), "Meet {name}" with a name field, **Begin** and **Edit before you start**; replacing an existing ranch asks and offers an export first.
- **The ranch**: calendar strip (year, month, week, season, weather, purse, a ⚙ shortcut), the monster on a seasonal stage (tap → card), Wren's bubble, condition bars by transparency mode, the action bar (Train · Rest · Journey · Battle · Town, Bag, Repeat last week, Wait a week). Overlays: the monthly food prompt (♥ / ✗ / bored, effect preview, loan note), the request card, the Train sheet (stars, stat arrows, liked/disliked/bonus/tonic tags, odds by mode, Quarry Haul locked), the drill result (a prop vignette per drill in `art/props.ts`, banner, stat deltas, chore pay, stroke-to-praise or buttons), the end-of-week summary (aging events, fees, next weather, the **grow-up glow** at Prime for Hearthwing, Pluckrex and Paladove, breakdowns as a dramatic card), and the hand-off to the farewell.
- **Monster Card in play** (shared `MonsterSheet` with the Lab view): **Use item · Learn technique · ✏️ Edit**. The editor's `active` origin saves straight to the ranch (autosaved) and keeps the previous version in the monster's edit history; Back and Save return to the card.
- **Bag** (×1 / ×5 / ×10 / Max, the Pearl's stat picker, tonic and fruit warnings, charms shown as placed, one-per-week refusals), **Songbook** (known with Forget, learnable with ★ fit and Learn, "Make room" at 12, relearning), **Town** (Shop, Guild Library, Monster Lab; the rest "opens with a later update"), **Basil's Shop** (bakery counter first, categories as chips, effect text per item, gates with reasons, multi-buy with a running total, debt notice), **Guild Library** (universal and by-breed tabs, rank gates, Owned marks).
- **Settings**: transparency, animation speed, text size (a `--text-scale` on the root), reduce motion, edited badge, sound placeholders, Gentle ↔ Standard switch (Classic locked), one item per week, save backup (download .json, share .txt), import a save (paste or file, preview, replace), storage status, a Sandbox "Add 10,000G" tool that marks the ranch.
- **Farewell placeholder**: Wren's line (retire or pass), the old portrait, weeks lived, final total, care counters, Start a new ranch, Keep a copy in the Lab.
- **Tests**: 233 (31 new): controller phases, economy, Market, Guild, odds bands, Wren's report, onboarding order, schema v3 migration and round trip, router returns, and the **3-year scripted raise** through the controller (shopping, a batch of sweets, a Songsheet, toys, requests, one edit, a save round trip every year, deterministic for a seed).
- **Headless phone check**: the built app was driven through two sessions in headless Chrome at 390×844 (new game → food → drill → praise → weeks → shop → library → bag → card → songbook → edit → settings → reload; and a short-lived Pluckrex from birth to retirement) with no console errors. Screenshots were reviewed.

**Decisions worth knowing**
- The drill result screen is held in memory until the week ends: if the app dies mid-result, that week restarts from its beginning (deterministic, nothing double-applied). Everything else autosaves immediately (after the week begins, after every free action, at the end of the week, and when the app goes to the background).
- The food prompt and the welcome tip come first in a new game; every other ranch tip waits until the week has begun.
- With no tournaments until M5, chore pay is the only income, so a batch of ten regular sweets (4,000G) is out of reach of the 3,000G start. The Sandbox tool in Settings covers testing; the economy is M5's to balance.
- Journeys and Battles show on the action bar as "coming soon" buttons (a toast), so the layout is the final one.
- Manual save slots have no UI yet: Continue loads the newest autosave; a new ranch replaces it after a confirm with an export offer.

**Next (M4):** battles: the engine, formulas, AI, the battle screen, Versus and the Battle Lab.

**Known issues**
- Rank stays 1 until M5, so only Basic and Hit Songsheets, regular sweets, toys and care items can be bought; gated rows say why.
- The Shrine in New Game skips locked breeds with the "sleeping" line; Sleeping Stones and the Encyclopedia arrive with M6.
- The Lab's "Send to Freezer" and "Make Active" wait for M6; the Farewell is a placeholder until the Memorial exists.
- Odd Jobs, the Planner, ranch upgrades, mail and the install-help card are later milestones.

## M2.5: Ten new monsters (2026-10-22) · v0.4.0

Breeds 21–30 from `docs/NEW_MONSTERS.md`, added before the ranch loop at the owner's request, plus an art polish pass for all 30.

**Done**
- **Docs:** CONTENT §2 (30 breeds), §2.1 (10 traits), §2.2 (10 briefs with the two-form text) and §3 (10 technique tables; 270 + 24 = 294) now hold the ten exactly as written in NEW_MONSTERS. GAME_DESIGN: four Market starters (§14.2), 900 mixes (§14.3), "8 of the 30" (§18), "all 294" (§19), and the **growth forms** and **high-end polish** rules in §22. BUILD_PLAN: this M2.5 section, the ten trait effects on M4's list, 30 breeds in the M9 matrix.
- **Data:** ten breed ids, ten trait ids, ten breeds (Pluckrex always at the Market, the rest at the Shrine, none locked), `art.grown` briefs for Hearthwing, Pluckrex and Paladove, 90 technique rows transcribed by a script from the tables. Tests: 30 / 30 / 294, unique technique names, Pluckrex among the always-stocked starters, spot checks of the new rows. Every one of the 90 new rows sits inside its §10.2 band: the pinned outlier list did not grow.
- **Shrine snapshot regenerated on purpose:** the commonness weights changed (ten new breeds share the pick), so every phrase now gives a different monster than at v0.3.0. Nobody has a saved phrase yet, so nothing is lost.
- **Art, ten looks:** new plan variants (a necked quadruped, hulking and squat bipeds, young and grown dinosaurs, a chick and a stout dove, a tentacled blob, a horizontal swimmer), ten looks and ten accent parts (little wings, crystal shoulders, fan crest, halo, aurora mane, petal ears, scholar's cap, bat wings, spiral horns, ice tusk). **Growth forms:** Hearthwing, Pluckrex and Paladove switch from young to grown at Prime; the Lab preview and the presets follow the life stage; the form is never stored. Wren's "{name} has grown up!" line is in the text file for M3's ranch scene.
- **Polish for all 30:** top-left-lit gradients on every body part (ids carry a palette hash, so many monsters on one page never clash), rim highlights, a soft radial contact shadow, four subtle textures (scales, fur, stone, feathers) assigned per breed, secondary motion (ears, wings, manes, fins, tentacles, spinning gears, glowing crystals and embers), a hop with squash-and-stretch, eyes that glance toward where the player taps, and signature particles for 26 of the 30 breeds (embers, glints, motes, twinkles, petals, bubbles, dust puffs, snowflakes, rain, sparks, steam, leaves, ash, coin glints, feathers). Particles are off for static thumbnails, under reduced motion and in **lite mode**, which turns on automatically on phones with little memory or few cores, or when a one-off frame-rate sample is low (thresholds in `tuning.ts` `UI.perf`).
- **Visual QA:** PNG contact sheets of the ten new breeds, the three growth forms (young, grown, happy), all eight expressions for each new breed, 40 mixes (each new breed with three old subs, and ten old breeds with new subs) and the old 20 after the polish were reviewed. One design was changed on review: Pluckrex's first draft could read as a penguin (upright stance, slate-and-cream palette, small muzzle), so it got a real dinosaur jaw with teeth, back ridges and a bigger crest. Nothing resembles a character from another franchise.
- 30 pure babies + 120 trained presets; 900 mixes render cleanly in tests; 202 tests (8 new), bundle 265 KB (84 KB gzipped).

**Known issues**
- The ten new traits have descriptions and ids only; their battle effects are on M4's list.
- The "grow up" moment (glow, Wren's line) needs the ranch screen (M3).
- Lite mode is decided once per session; there is no manual switch yet beyond Reduce motion.
- Old-age desaturation, the idle animation and the particles only show in browsers, not in the PNG review tool.

## M2: Saves and the Monster Lab (2026-10-22) · v0.3.0

**Live:** the Monster Lab opens from the title screen. This is the first milestone the owner can use: make a monster, see it drawn, edit anything, and move it between phones.

**Done**
- **Saves on the phone** (`save/db.ts`): IndexedDB through idb-keyval in our own `wildsong-ranch` database, every key prefixed `wildsong/`; 3 manual slots; an autosave ring (the latest plus 3 backups, falling back to an older copy if the newest is corrupt); the global Library; Settings; a localStorage mirror of the latest save and of the Library, used when the database is empty or broken; `navigator.storage.persist()` after the first save. Nothing throws: a broken database reads as empty and a failed write returns false, and every read is validated.
- **Schema v2** (`SAVE_VERSION = 2`): saves gain `meta { savedAt, appVersion }` with a migration and a test; monster files (`kind: 'monster'`, with up to 10 edit-history entries), Library files (`kind: 'library'`) and Settings; `validateAny()` sorts any pasted object by its `kind` (a bare monster counts too); a file from a newer version gets a clear message. Friendly error strings live in `text/ui.ts`.
- **Share codes** `WS1-…` (deflate-raw + base64url through the browser's built-in `CompressionStream`, no library). Decoding tolerates lower-case, codes inside sentences and links, and line-wrapped email; a pinned code written at v0.3.0 guards compatibility forever. Import from JSON, codes, `.txt`, and `#import=` links; export as code, link, QR code (SVG), `.json` download and Web Share `.txt`.
- **Procedural monster art v1** (`art/monster/`): a pure SVG string renderer (runs in tests, later in workers); 9 body plans with sockets; 20 breed looks from CONTENT §2.2; 20 accent parts; the §14.3 palette rule (sub palette on the main body, the main's eyes stay); 8 expressions plus the sparkle and the mischievous grin from the §6.6 cues; size by life stage; a fade from stage 8; idle animation (breathe, bob, float, blink, wag, twinkle, jitter, chew) on transform and opacity only, off under reduced motion or `data-animate="false"`. Every breed, 15 mixes, every expression and every size were reviewed as PNG contact sheets before shipping.
- **Core**: `core/lab.ts` (scaleToTotal by grade factor with an exact total, breed base, max all, seeded randomize, the blank template, duplicate, breed change with Keep all, Allow any technique, the edited rule, edit history push and restore), `core/shrine.ts` (§14.1 steps 1–8 in order; a five-phrase snapshot is the "same phrase, same monster" contract), `core/presets.ts` (20 pure babies and 80 trained presets at E / C / A / S, generated, never stored).
- **Monster Lab UI**: Library (Library / Presets, breed filter, sort, cards with badges, an action sheet with View · Edit · Duplicate · Export · Delete), Create (breed tiles with portraits and the "Not discovered yet. Use anyway?" prompt, from a song with a live Shrine preview, or blank), Editor (every §19 section, a live portrait pinned at the top, the breed-change removal list with Keep all, Save · Save as copy · Cancel · Revert, Edit history with Restore), the Monster Card view, Import (paste, file, link, preview before accepting), Export, and a minimal Settings screen (edited badge, reduce motion, storage status).
- 194 tests (60 new), `npm run verify` green, bundle 216 KB (71 KB gzipped).

**Decisions worth knowing**
- The shared `.txt` holds one friendly line plus the code; the `.json` download holds the monster with its edit history; codes carry the monster alone so QR codes stay scannable.
- "Not discovered yet" means one of the 8 locked breeds, until the Journal exists (M7).
- Preset power: E 600 · C 1,200 · A 2,000 · S 2,800 total stat points at the first week of Prime (`tuning.ts` `PRESETS`). An S preset knows its whole 9-technique kit.
- Library and picker portraits are static; previews and the Monster Card animate, so a hundred cards stay smooth.
- Restore loads an old version into the editor's draft; Save keeps it and pushes the version it replaced into history, so a restore can be undone as well.
- Breed change in the editor only removes techniques on save, and only if the breeds actually changed and Keep all is off. Techniques added with Allow any are never stripped by themselves.

**Next (M3):** the ranch loop: New Game, the ranch screen, drills and results, rest, requests, food, the Shop, items and Songsheets in play, the Monster Card with ✏️ Edit, Settings, aging and warnings, onboarding.

**Known issues**
- The Lab's Versus and Battle Lab tabs wait for M4; the Freezer and Memorial sources, Send to Freezer and Make Active wait for M3 and M6.
- A whole save file cannot be loaded until the ranch exists (M3); Import offers its monster for the Library instead.
- A share code is about 900 characters for a baby monster: fine for a QR code, long to type by hand.
- Old-age desaturation and the idle animation only show in browsers, not in the PNG review tool.
- UI screens have no automated tests (they would need a DOM library); everything below them does.

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
