# Wildsong Ranch: Content

Version 1.0. Every name, creature, character, place and item here is **original**, and these are the names to use. To rename anything, change it here first; then Claude updates `src/data/`. Rules and formulas live in `docs/GAME_DESIGN.md`.

> **Originality rule.** Do not add or substitute names, monster designs, characters, items or places from Monster Rancher / Monster Farm or any other franchise (Pokémon, Digimon, Dragon Quest, etc.). If a new design starts to look like a famous monster, change it until it doesn't.

---

## 1. World and characters

**Wildsong Vale** is a green valley ringed by mountains. Old legends say the land itself sings, and every monster is born when a song is sung to one of the Shrine's echo stones. The town of **Tunewick** sits at its heart: cobbled lanes, a market square, the Shrine of Echoes on the hill and the Breeders' Guild arena by the river. Your ranch is a small, run-down homestead at the edge of town, left to you by a relative who was once a great breeder. *Tone: cozy, warm, gently funny, a little bittersweet. Think storybook, not epic.*

| Character | Role | Personality / voice |
|---|---|---|
| **Wren** | Your ranch assistant. Gives weekly reports, hints and reactions | Upbeat, observant, a bit dramatic about good news; never nags twice in a row; uses the monster's name and pronoun |
| **Basil** | Shopkeeper (items, food, the Stat Sweets bakery counter, rumors) | Gossipy old merchant; "Don't tell anyone I told you…" |
| **Dr. Odessa Pell** | The Lab: Freezer, Fusion, Memorial, Monster Lab | Brisk, kind scientist who talks to monsters like colleagues |
| **Sister Mara** | Keeper of the Shrine of Echoes | Calm, poetic; hosts the Lantern Vigil |
| **Ines** | Breeders' Guild registrar (tournaments, ranks, Hall of Fame) and keeper of the Guild Library (Songsheets) | Formal, fair, secretly a huge fan |
| **Tomas** | Expedition guide | Big laugh, bad jokes, brave |
| **Master Oduya** | Mentor, Iron Quarry (POW / Heavy) | Few words, huge heart |
| **Coach Lark** | Mentor, Windrun Steppe (SPD / Sharp) | Whistle, stopwatch, endless energy |
| **Sage Ilsabet** | Mentor, Starfall Observatory (INT / Wither) | Dreamy astronomer, speaks in riddles |
| **Ranger Teo** | Mentor, Archer's Glade (SKI / Hit) | Patient, precise, dry humor |
| **Warden Brask** | Mentor, Glacier Bastion (DEF / Special) | Stern ice-fort keeper; respects grit |

Leagues for the every-4-years Summit: the **Vale League** (yours) and the **Coast League**.

---

## 2. Breeds (30)

`commonness` weights the Shrine's main-breed pick (unlocked and locked breeds alike). `strength` (1–10) weights Fusion outcomes. Stats are listed LIF / POW / INT / SKI / SPD / DEF. Grades use the same order.

| # | Breed | Niche | Start | Growth | Life (wks) | Guts | Lean | Base stats | Grades | Bonus drill | Strength | Common | Trait |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Puddlepup** | Balanced starter | Market (always) | Steady | 380 | 12 | Mixed | 120/70/60/80/70/70 | C C D B C C | Target Toss | 7 | 10 | Cheerful |
| 2 | **Tumblefox** | Quick trickster starter | Market (always) | Early | 360 | 11 | INT | 90/60/80/80/100/50 | D D C B B D | Dodge the Gourds | 6 | 10 | Nimble |
| 3 | **Cobblemaw** | Slow heavy bruiser | Shrine | Late | 420 | 15 | POW | 140/120/30/40/30/110 | B A E D E B | Log Toss | 8 | 8 | Heavy Hitter |
| 4 | **Moatshell** | Fortress wall | Shrine | Evergreen | 440 | 16 | POW | 130/70/50/50/30/150 | B C D D E A | Acorn Shower | 7 | 8 | Fortified |
| 5 | **Wishlume** | Frail INT caster | Shrine | Early | 320 | 10 | INT | 70/30/130/80/90/40 | E E A C B E | Puzzle Stones | 6 | 8 | Glow |
| 6 | **Quillion** | Fast skill duelist | Market (always) | Steady | 360 | 11 | POW | 90/90/50/120/100/60 | D C D A B D | Target Toss | 6 | 9 | En Garde |
| 7 | **Cinderlynx** | Power glass cannon | Market (autumn) | Steady | 340 | 13 | POW | 90/130/50/70/110/40 | D A D C B E | Plow Pull | 6 | 7 | Hot-Blooded |
| 8 | **Bloatoad** | HP sponge | Shrine | Late | 450 | 14 | POW | 190/100/50/50/40/60 | A B D D D E | Hill Sprints | 5 | 8 | Big Appetite |
| 9 | **Coilfang** | Short-lived prodigy | Market (spring) | Early | 300 | 11 | POW | 90/110/40/110/90/70 | C B E B C C | Wind Chase | 7 | 7 | Quick Study |
| 10 | **Nimbusheep** | Long-lived late bloomer | Market (winter) | Late | 480 | 13 | INT | 140/40/100/60/50/90 | B E B C D C | Moon Meditation | 5 | 7 | Fluffy |
| 11 | **Galeheron** | Fast INT striker | Market (summer) | Steady | 360 | 10 | INT | 80/50/100/100/120/40 | D D B B A E | Wind Chase | 6 | 7 | Tailwind |
| 12 | **Nibblegrub** | Metamorph tank | Shrine | Steady | 400 | 14 | POW | 160/90/50/50/30/90 | A C D D E C | Hill Sprints | 4 | 9 | Hungry Grub |
| 13 | **Velvesper** | Swift INT (metamorph form) | 🔒 Cocoon | Evergreen | 380 | 10 | INT | 80/40/140/100/130/40 | D E A B A E | Moon Meditation | 5 | 2 | Moth Dust |
| 14 | **Ashwraith** | Death-born guts engine | 🔒 Vigil | Early | 340 | 8 | INT | 60/30/150/120/120/50 | E E A B B D | Puzzle Stones | 4 | 2 | Ethereal |
| 15 | **Zipwisp** | Guts-engine harasser | 🔒 Storm Chase | Early | 340 | 8 | INT | 70/40/90/120/150/50 | D E C B A D | Dodge the Gourds | 3 | 2 | Live Wire |
| 16 | **Mirrorkin** | Trickster / guts drainer | 🔒 Masquerade | Steady | 360 | 11 | INT | 80/50/140/110/80/60 | D D A B C D | Puzzle Stones | 4 | 2 | Reflective |
| 17 | **Gearhoot** | Construct all-rounder | 🔒 Blueprint | Evergreen | 420 | 13 | INT | 90/70/120/110/60/120 | D D B B D B | Acorn Shower | 5 | 2 | Clockwork |
| 18 | **Reefclaw** | Long-prime armored knight | 🔒 Tide Pool | Evergreen | 400 | 14 | POW | 110/120/40/90/60/140 | C B E C D B | Waterfall Stand | 6 | 2 | Hard Shell |
| 19 | **Lootlid** | Challenge / joke breed | 🔒 Strange Chest | Steady | 300 | 15 | Mixed | 110/80/80/60/40/170 | C D D D E A | Acorn Shower | 2 | 1 | Gilded |
| 20 | **Aurelwyrm** | Elite dual-threat | 🔒 Four Crowns | Early | 280 | 18 | Both | 130/150/150/90/90/110 | B A A C C C | Plow Pull | 9 | 1 | Regal |
| 21 | **Hearthwing** | Late-blooming dragon powerhouse (grows up at Prime) | Shrine | Late | 400 | 16 | Both | 130/120/90/60/60/100 | B A C D D C | Plow Pull | 8 | 3 | Dragonheart |
| 22 | **Grumblestone** | Unmovable crystal tank | Shrine | Late | 460 | 18 | POW | 160/110/40/40/20/140 | B B E E E A | Waterfall Stand | 7 | 7 | Unshakable |
| 23 | **Pluckrex** | Brave rookie hero (grows up at Prime) | Market (always) | Early | 360 | 12 | POW | 110/100/50/90/80/80 | C B D C C C | Log Toss | 7 | 9 | Underdog |
| 24 | **Paladove** | Holy guardian healer (grows up at Prime) | Shrine | Evergreen | 420 | 13 | INT | 130/50/110/80/70/110 | B E B C D B | Moon Meditation | 6 | 6 | Blessed |
| 25 | **Starhowl** | Swift night hunter | Shrine | Steady | 360 | 10 | Mixed | 90/110/70/100/130/50 | D B C C A E | Wind Chase | 6 | 7 | Moonlit |
| 26 | **Petalphant** | Blooming support tank | Shrine | Late | 480 | 14 | INT | 180/80/90/50/40/80 | A C B D E C | Hill Sprints | 5 | 7 | Green Thumb |
| 27 | **Scrollopus** | Inky trickster scholar | Shrine | Steady | 380 | 11 | INT | 90/40/140/110/70/60 | D E A B C D | Puzzle Stones | 5 | 6 | Eight Arms |
| 28 | **Gloomgrin** | Stone-skinned counter-puncher | Shrine | Steady | 380 | 13 | POW | 100/110/60/100/50/120 | C B D B E B | Target Toss | 6 | 6 | Statue Pose |
| 29 | **Rammerjack** | Charging brawler | Shrine | Early | 340 | 13 | POW | 110/130/40/70/110/70 | C A E D B C | Plow Pull | 7 | 8 | Battering Ram |
| 30 | **Frostlance** | Icy precision lancer | Shrine | Evergreen | 400 | 12 | Mixed | 100/90/90/130/70/70 | C C C A D D | Target Toss | 6 | 6 | Chill |

### 2.1 Traits

| Trait | Effect |
|---|---|
| Cheerful | Stress from scolding −50% |
| Nimble | Counts as +50 SPD when being targeted |
| Heavy Hitter | Heavy-family techniques +15% damage |
| Fortified | All damage taken −20% |
| Glow | +6 hit with Far (range 4) techniques |
| En Garde | +8 hit with Near (range 2) techniques |
| Hot-Blooded | +15% damage while own HP ≤ 50% |
| Big Appetite | Monthly food effects ×1.5 (good and bad) |
| Quick Study | +10% Journey technique chance |
| Fluffy | Rest removes 8 more fatigue |
| Tailwind | Walk and dash speed +20% |
| Hungry Grub | Food form changes ×1.5; can cocoon (§11) |
| Moth Dust | Opponents' crit chance against it ×0.5 |
| Ethereal | Wither taken ×0.7 |
| Live Wire | Guts regen +25% while guts < 30 |
| Reflective | 15% chance to reflect 30% of INT damage taken |
| Clockwork | Drill fatigue −20% |
| Hard Shell | POW damage taken −15% |
| Gilded | Tournament prizes +15%; chore pay ×2 |
| Regal | +5 extra fame per tournament win; +5 to the fame-crit cap |
| Dragonheart | Once per battle, when its HP first drops below 50%, it gains 20 guts |
| Unshakable | Can't be pushed back or stunned; damage taken −10% |
| Underdog | +8 hit and +10% damage against opponents with a higher stat total |
| Blessed | Regenerates 1% of max HP every 5 seconds in battle |
| Moonlit | Crit chance +6% |
| Green Thumb | Heal and drain techniques restore 50% more |
| Eight Arms | Multi-hit techniques get one extra hit |
| Statue Pose | After standing still for 2 seconds, takes 30% less damage until it moves |
| Battering Ram | Dashing costs no guts, and the first technique after a dash deals +15% damage |
| Chill | Its hits slow the target's walking by 25% for 3 seconds |

### 2.2 Art briefs (procedural SVG; see GAME_DESIGN §22)

Each brief lists: body plan · signature features · palette (body / belly / accent / eye) · **accent part** (what this breed adds when it's the sub) · **sub adjective** (for variant names).

1. **Puddlepup**
   - Quadruped, stubby and round: a puppy-like amphibian with floppy fin-shaped ears, webbed paws, a wide happy grin and a tadpole-ish flat tail.
   - Palette: #3FB6A8 / #F3E6C4 / #F28FA8 / #24323A.
   - Accent: floppy fin-ears · adjective: "Puddle".
2. **Tumblefox**
   - Quadruped, small: a fox with an oversized curled tail bigger than its body, tall pointed ears, a dark mask band across the eyes and dark socks.
   - Palette: #D9733B / #F7F1E8 / #3B3240 / #2A1E22.
   - Accent: curled tail · adjective: "Tumble".
3. **Cobblemaw**
   - Quadruped, bulky and bear-like: cobblestone plates over shoulders and back with tufts of moss, a wide cave-like jaw with two short stubby tusks, small deep-set eyes.
   - Palette: #6E7486 / #8E94A4 / #7FAF5A / #F2B544.
   - Accent: stone shoulder plates · adjective: "Cobble".
4. **Moatshell**
   - Shelled tortoise: its shell is a tiny castle keep with crenellations, arrow slits and a pennant flag on top; stubby pillar legs, sleepy wise eyes.
   - Palette: #C9A66B / #E8D4A8 / #3AA6A1 (flag; brick details #9A5B3C) / #2B2B2B.
   - Accent: crenellated rim · adjective: "Bastion".
5. **Wishlume**
   - Floater: a paper sky-lantern creature. The warm flame "heart" glows through its paper body; two stubby paper arms, a dangling tassel tail, eyes painted on the paper.
   - Palette: #F6E3B4 / #FFF2D6 / #D94F4F (ribs and tassel; glow #FFB85C) / #3A2A2A.
   - Accent: tassel tail · adjective: "Lantern".
6. **Quillion**
   - Biped, small: a chestnut hedgehog fencer with a crest of back quills, one long silver tail-quill held like a blade, and a short crimson cape. Upright dueling stance.
   - Palette: #8C5A3C / #EED9C4 / #C0392B (quill #C9D3DD) / #1E1E1E.
   - Accent: back quills · adjective: "Quilled".
7. **Cinderlynx**
   - Quadruped, lean feline: ember-tipped ear tufts, a glowing ember pattern along the spine, smoke wisps curling from its paws, an ember tail-tip. No collar or mane.
   - Palette: #3A3236 / #5A4E52 / #FF7A2F / #FFD15C.
   - Accent: ember ear tufts · adjective: "Cinder".
8. **Bloatoad**
   - Squat blob-quadruped: a huge toad with an inflatable throat sac that balloons when happy, lazy half-lidded eyes, warty spots and little crown-like bumps on its head.
   - Palette: #7C9A3E / #F6C49B / #5E7A2E / #E9C46A.
   - Accent: throat sac · adjective: "Bog".
9. **Coilfang**
   - Serpent: a jade S-coil with a feathered golden crest, two neat fangs and a diamond scale pattern down its back.
   - Palette: #2FA37A / #DDF2D3 / #E8C14E / #1B3A2B.
   - Accent: feathered crest · adjective: "Jade".
10. **Nimbusheep**
    - Quadruped: a sheep whose wool is a soft raincloud that occasionally drizzles, with curled cream horns. A tiny rainbow appears over it when it's happy. No electricity.
    - Palette: #E9EEF6 / #8C97AD / rainbow (#F28F8F #F7D36B #8FD1A8 #8FB8F2) / #2E3440.
    - Accent: cloud-wool tufts · adjective: "Nimbus".
11. **Galeheron**
    - Avian, tall: a long-legged heron with a dagger beak, streaming crest plumes and wind-swirl markings on its wings.
    - Palette: #6FB7E9 / #F5F8FC / #2F5D8A / #F2C14E.
    - Accent: crest plumes · adjective: "Gale".
12. **Nibblegrub**
    - Insect: a chubby five-segment larva with tiny legs, big round cheeks always chewing, and stubby antenna nubs.
    - Palette: #F2D27A / #FFF0C2 / #D9A94F (cheeks #F29C8F) / #3B2F2F.
    - Accent: antenna nubs · adjective: "Grub".
13. **Velvesper**
    - Insect/avian moth: velvet dusk-colored wings with crescent-moon markings and two soft eyespots, feathery antennae.
    - Palette: #5B3F7A / #EDE3F5 / #F29E4C (eyespots #F7E7B5) / #1B1424.
    - Accent: feathery antennae · adjective: "Dusk".
14. **Ashwraith**
    - Floater: a tattered ash-grey shroud with no visible body, two ember eyes, wisps trailing like smoke, and tiny hands peeking out.
    - Palette: #A7A3A0 / #CFCAC6 / #FF6B3D / #FF6B3D.
    - Accent: trailing wisps · adjective: "Ashen".
15. **Zipwisp**
    - Floater, small: a fizzing ball of cyan static with two stubby spark-wings and a zigzag tail, always jittering. Keep the face simple and *not* like any existing electric mascot.
    - Palette: #6EF2FF / #FFFFFF / #FFE14D / #0E2A40.
    - Accent: zigzag tail · adjective: "Zappy".
16. **Mirrorkin**
    - Floater: a living vertical hand-mirror with an ornate gilded frame; the handle is its tail. Its face appears in the glass and changes expression. It wears a ribbon cloak and has two little floating gloved hands.
    - Palette: #CFD8E3 / #EEF3F8 / #6C5CE7 (frame #C9A04A) / #2B2B33.
    - Accent: ribbon cloak · adjective: "Mirror".
17. **Gearhoot**
    - Construct/avian: a clockwork owl of brass plates. One eye is a big monocle lens and one is normal; its wing feathers are little gears and a wind-up key turns on its back.
    - Palette: #C9A04A / #E9D7A6 / #5CC9C0 (copper #B86B3C) / #F7F3E3.
    - Accent: gear wings · adjective: "Brass".
18. **Reefclaw**
    - Shelled biped: a coral-pink crab knight with one oversized branching coral claw and one small claw, barnacle shoulder armor and visored eye-stalks.
    - Palette: #F07C6E / #FFD9CF / #BDE7E0 (shell #B85B4E) / #1F2A44.
    - Accent: coral claw · adjective: "Coral".
19. **Lootlid**
    - Construct: a treasure-chest creature on stubby legs. The lid is its mouth, with a long tongue and coins glinting inside, and a keyhole "nose".
    - Palette: #9C6B3F / #C99A6B / #F2C94C (tongue #E86A7C) / #2B1B10.
    - Accent: gold-trim lid · adjective: "Gilded".
20. **Aurelwyrm**
    - Serpent dragon: golden and serpentine, with long crimson ribbon fins, small branching antlers and whiskers. It floats without wings.
    - Palette: #F2C14E / #FFF4D6 / #D64545 / #6B2D0F.
    - Accent: ribbon fins · adjective: "Golden".
21. **Hearthwing**
    - **Quadruped dragon with two forms** (GAME_DESIGN §22, growth forms).
      - **Young** (stages 1–4): a round, stubby dragonet with tiny flappy wings, a short snout, nub horns and a faint glow in its chest.
      - **Grown** (stage 5+): a broad-winged dragon with a long neck and swept-back copper horns. The scales of its stocky chest part like a fireplace grate to show a molten glow. Ember-edged wing membranes and a spade-tipped tail.
    - Palette: #1F6F6A / #E9D8B4 / #FF8A3D (horns #B87333) / #FFD166.
    - Accent: little wings · adjective "Hearth".
22. **Grumblestone**
    - **Biped, hulking and hunched:** a boulder giant with a cracked granite shell. Violet crystals glow through the cracks like the inside of a geode.
    - Heavy stone-ledge eyebrows over small grumpy eyes, pillar arms with crystal knuckles, and short thick legs.
    - Palette: #7A7068 / #9C938A / #9B5DE5 / #F5E663.
    - Accent: crystal-studded shoulders · adjective "Geode".
23. **Pluckrex**
    - **Biped little dinosaur with two forms.**
      - **Young:** a big head, a wide toothy grin, stubby arms and a thick short tail. Its fan-shaped head crest glows sunflower-gold when it's fired up.
      - **Grown:** taller and sturdier, with a bigger crest, stone-plated forearm bracers and a tougher, scalier hide.
    - Palette: #4F6D8F slate blue / #F1E6CF / #F7C548 / #2B2D42.
    - Accent: fan crest · adjective "Plucky".
24. **Paladove**
    - **Avian (a stout dove) with two forms.** Not humanoid.
      - **Young:** a fluffy, round dove chick with a tiny feather crest and a little gold ring floating above its head.
      - **Grown:** a stately dove-knight in white-and-gold chest armor, with four broad wings, a glowing ring halo, and a round feather-emblem shield on one wing.
    - Palette: #F7F4EE / #FFFFFF / #E3B448 / #4A6FA5.
    - Accent: halo ring · adjective "Haloed".
25. **Starhowl**
    - **Quadruped wolf:** midnight-indigo fur speckled with tiny twinkling constellations, a flowing aurora mane (teal shading to rose), a star-cluster pattern across the brow, glowing pale eyes and a bushy star-tipped tail.
    - Palette: #2B2F6B / #4C5199 / #6EE7C8 (rose #F49AC1) / #E8F1FF.
    - Accent: aurora mane · adjective "Starry".
26. **Petalphant**
    - **Quadruped elephant calf:** round and sage-green, with huge blush-pink ears shaped like magnolia petals.
    - A flower bud at the tip of its trunk opens when it's happy. It has a leafy tail tuft and chubby legs.
    - Palette: #8FB996 / #DCEFD9 / #F4A7B9 / #3B3B3B.
    - Accent: petal ears · adjective "Blossom".
27. **Scrollopus**
    - **Blob octopus:** a plump violet octopus in round spectacles and a little tasseled scholar's cap.
    - Each tentacle curls around a scroll, a quill or a book. Ink-spot freckles.
    - Palette: #7D5BA6 / #CDB4E6 / #2E2A4F (cap #3A3A55, tassel #F2C94C) / #1E1E2E.
    - Accent: scholar's cap · adjective "Inky".
28. **Gloomgrin**
    - **Biped squat gargoyle imp:** charcoal-stone skin with faint violet rune lines, stubby horns, small bat wings and a curled tail.
    - A wide, cheeky grin of square teeth; amber eyes that glow at night. It crouches like a rooftop statue when idle.
    - Palette: #4B4F58 / #6B7079 / #8E7CC3 / #FFB347.
    - Accent: bat wings · adjective "Gloomy".
29. **Rammerjack**
    - **Quadruped mountain goat:** a stocky cream-and-chestnut goat with huge spiral horns banded with rope wraps, a shaggy beard, a red knitted scarf, sturdy hooves and determined eyebrows.
    - Palette: #EFE6D2 / #FFF8EA / #A0522D (scarf #D1495B) / #3A2E26.
    - Accent: spiral horns · adjective "Rammy".
30. **Frostlance**
    - **Floater narwhal:** pale blue-white, it swims through the air and leaves a trail of snowflakes.
    - A long spiral tusk of clear ice, frost-edged fins, and a deep-teal back with snowflake freckles.
    - Palette: #D8EEF7 / #F5FBFE / #1F7A8C (tusk #BDE8F5) / #1B263B.
    - Accent: ice tusk · adjective "Frosty".

---

## 3. Techniques (270 breed techniques + 24 universal)

These rows were generated from the family bands in GAME_DESIGN §10.2.
- **Range:** 1 Close · 2 Near · 3 Mid · 4 Far.
- **Anim** is in ticks (30 per second).
- **Multi-hit:** Force is per hit.
- **heal** techniques (force 0) always succeed.
- **Requirements** are `stats + loyalty ≥ value` (GAME_DESIGN §11).
- **Chains** need the base technique at Lv3.
- **"Sub-quirk"** marks the technique a breed passes on when it is the sub-breed.
- **Breed Songsheets** (GAME_DESIGN §10.5): every non-Basic technique below can also be learned from a sheet sold at the Guild Library once its breed is unlocked.
  - Prices: Hit 1,000G · Wither 1,500G · Sharp 1,500G · Heavy 2,500G · Special 4,000G · Chain 5,000G.
  - Rank gates: Wither and Sharp from breeder rank 2; Heavy, Special and Chain from rank 4.
  - Signature sheets are Crown prizes only.

#### Puddlepup

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Splash Nip | Basic | POW | 1 Close | 10 | 13 | +5 | 7 | 8 | 24 | — | Starter |
| Bubble Pop | Basic | INT | 3 Mid | 10 | 13 | +4 | 5 | 7 | 24 | — | Starter · sub-quirk |
| Frill Flick | Hit | POW | 2 Near | 20 | 14 | +17 | 9 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Belly Flop | Heavy | POW | 1 Close | 48 | 50 | -12 | 13 | 8 | 39 | — | Iron Quarry: POW ≥ 360 |
| Soggy Cloud | Wither | INT | 3 Mid | 29 | 12 | -2 | 42 | 8 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Slipstream Spin | Sharp | POW | 2 Near | 25 | 22 | -4 | 9 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Geyser Burst | Special | INT | 4 Far | 48 | 14 | -4 | 20 | 9 | 36 | 2 hits | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Cannonball Flop | Chain | POW | 1 Close | 54 | 70 | -4 | 16 | 11 | 42 | — | Iron Quarry: Belly Flop Lv3 + POW ≥ 520 |
| Puddle Party | Signature | INT | 3 Mid | 55 | 20 | +5 | 40 | 17 | 42 | heal 10% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Tumblefox

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Scamper Swipe | Basic | POW | 1 Close | 13 | 12 | +6 | 6 | 5 | 24 | — | Starter |
| Foxfire Flicker | Basic | INT | 3 Mid | 13 | 12 | +4 | 7 | 8 | 24 | — | Starter · sub-quirk |
| Tail Twirl | Hit | POW | 2 Near | 19 | 16 | +16 | 7 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Will-o'-Blaze | Heavy | INT | 2 Near | 44 | 57 | -9 | 13 | 11 | 39 | — | Iron Quarry: INT ≥ 360 |
| Trickster's Hush | Wither | INT | 3 Mid | 26 | 15 | +2 | 42 | 6 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Mirage Dart | Sharp | INT | 4 Far | 27 | 26 | -3 | 11 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Fluffstorm | Special | INT | 2 Near | 48 | 33 | +1 | 20 | 12 | 36 | stun 30 ticks | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Foxfire Volley | Chain | INT | 3 Mid | 21 | 20 | +7 | 8 | 11 | 27 | — | Archer's Glade: Foxfire Flicker Lv3 + INT ≥ 520 |
| Ninefold Feint | Signature | INT | 2 Near | 54 | 18 | +3 | 25 | 30 | 42 | 3 hits | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Cobblemaw

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gravel Swipe | Basic | POW | 1 Close | 10 | 10 | +3 | 6 | 6 | 24 | — | Starter · sub-quirk |
| Shoulder Check | Basic | POW | 2 Near | 10 | 10 | +3 | 6 | 8 | 24 | — | Starter |
| Crag Jab | Hit | POW | 1 Close | 16 | 14 | +14 | 8 | 9 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Landslide Maul | Heavy | POW | 1 Close | 47 | 64 | -12 | 13 | 11 | 39 | — | Iron Quarry: POW ≥ 360 |
| Moss Smother | Wither | POW | 2 Near | 27 | 16 | +3 | 44 | 4 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Fault Line Claw | Sharp | POW | 2 Near | 26 | 24 | +0 | 10 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Boulder Heave | Special | POW | 3 Mid | 46 | 46 | -1 | 16 | 9 | 36 | miss: self-dmg 8% max HP | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Mountainfall | Chain | POW | 1 Close | 53 | 84 | -9 | 16 | 14 | 42 | — | Iron Quarry: Landslide Maul Lv3 + POW ≥ 520 |
| Bedrock Roar | Signature | POW | 3 Mid | 55 | 30 | +2 | 50 | 16 | 42 | stun 45 ticks | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Moatshell

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Shell Bump | Basic | POW | 1 Close | 14 | 14 | +5 | 5 | 7 | 24 | — | Starter |
| Turret Toss | Basic | POW | 3 Mid | 14 | 11 | +3 | 5 | 4 | 24 | — | Starter · sub-quirk |
| Drawbridge Snap | Hit | POW | 2 Near | 17 | 14 | +16 | 8 | 6 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Keep Slam | Heavy | POW | 1 Close | 44 | 64 | -6 | 12 | 8 | 39 | — | Iron Quarry: POW ≥ 360 |
| Moat Mire | Wither | POW | 2 Near | 28 | 18 | +4 | 48 | 6 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Arrow Slit Shot | Sharp | POW | 3 Mid | 26 | 30 | +2 | 10 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Catapult Barrage | Special | POW | 4 Far | 48 | 13 | -2 | 19 | 10 | 36 | 3 hits | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Siege Volley | Chain | POW | 3 Mid | 22 | 21 | +6 | 6 | 7 | 27 | — | Archer's Glade: Turret Toss Lv3 + POW ≥ 520 |
| Hold the Line | Signature | POW | 1 Close | 54 | 0 | +5 | 30 | 16 | 42 | heal 20% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Wishlume

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Wishlight Flash | Basic | INT | 3 Mid | 11 | 13 | +3 | 5 | 4 | 24 | — | Starter · sub-quirk |
| Paper Flutter | Basic | INT | 2 Near | 13 | 13 | +3 | 7 | 8 | 24 | — | Starter |
| Glimmer Bolt | Hit | INT | 4 Far | 16 | 13 | +14 | 8 | 7 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Lantern Beam | Heavy | INT | 4 Far | 44 | 50 | -12 | 11 | 9 | 39 | — | Iron Quarry: INT ≥ 360 |
| Hypno Glow | Wither | INT | 3 Mid | 27 | 12 | -2 | 38 | 8 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Prism Needle | Sharp | INT | 3 Mid | 25 | 22 | -4 | 11 | 30 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Ember Siphon | Special | INT | 2 Near | 46 | 27 | -1 | 19 | 12 | 36 | drain 50% of dmg | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Starlight Lance | Chain | INT | 4 Far | 22 | 14 | +15 | 10 | 10 | 30 | — | Archer's Glade: Glimmer Bolt Lv3 + INT ≥ 520 |
| Festival of Lights | Signature | INT | 4 Far | 60 | 62 | +0 | 22 | 17 | 42 | — | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Quillion

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Quill Poke | Basic | POW | 1 Close | 11 | 14 | +5 | 6 | 6 | 24 | — | Starter |
| Lunge | Basic | POW | 2 Near | 14 | 11 | +7 | 7 | 5 | 24 | — | Starter · sub-quirk |
| Riposte | Hit | POW | 2 Near | 19 | 15 | +20 | 7 | 7 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Spine Burst | Heavy | POW | 1 Close | 44 | 50 | -12 | 11 | 8 | 39 | — | Iron Quarry: POW ≥ 360 |
| Bramble Bind | Wither | POW | 1 Close | 27 | 12 | -2 | 43 | 5 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Fleche | Sharp | POW | 2 Near | 26 | 22 | -4 | 10 | 34 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Quill Flurry | Special | POW | 3 Mid | 47 | 11 | +2 | 17 | 8 | 36 | 3 hits | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Grand Riposte | Chain | POW | 2 Near | 25 | 18 | +23 | 8 | 10 | 30 | — | Archer's Glade: Riposte Lv3 + POW ≥ 520 |
| Hundred-Quill Waltz | Signature | POW | 2 Near | 57 | 12 | +14 | 22 | 18 | 42 | 4 hits | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Cinderlynx

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ember Swipe | Basic | POW | 1 Close | 13 | 13 | +3 | 5 | 8 | 24 | — | Starter |
| Spark Pounce | Basic | POW | 2 Near | 13 | 11 | +4 | 7 | 5 | 24 | — | Starter · sub-quirk |
| Cinder Jab | Hit | POW | 1 Close | 17 | 19 | +14 | 8 | 10 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Inferno Maul | Heavy | POW | 1 Close | 45 | 50 | -12 | 11 | 9 | 39 | — | Iron Quarry: POW ≥ 360 |
| Smoke Veil | Wither | INT | 3 Mid | 25 | 12 | -2 | 44 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Blazing Rake | Sharp | POW | 2 Near | 29 | 22 | -4 | 11 | 31 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Wildfire Rush | Special | POW | 3 Mid | 47 | 36 | -1 | 20 | 11 | 36 | dash to Close after | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Flare Fang Flurry | Chain | POW | 1 Close | 21 | 21 | +6 | 6 | 11 | 27 | — | Archer's Glade: Ember Swipe Lv3 + POW ≥ 520 |
| Kindled Fury | Signature | POW | 2 Near | 55 | 60 | +6 | 26 | 14 | 42 | miss: self-dmg 10% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Bloatoad

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Belly Bounce | Basic | POW | 1 Close | 11 | 10 | +3 | 6 | 7 | 24 | — | Starter |
| Tongue Lash | Basic | POW | 2 Near | 10 | 10 | +3 | 6 | 6 | 24 | — | Starter · sub-quirk |
| Sticky Tongue | Hit | POW | 2 Near | 19 | 14 | +14 | 9 | 10 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Bog Slam | Heavy | POW | 1 Close | 44 | 53 | -8 | 13 | 11 | 39 | — | Iron Quarry: POW ≥ 360 |
| Croak Quake | Wither | POW | 3 Mid | 26 | 14 | +0 | 38 | 7 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Wart Spitball | Sharp | POW | 3 Mid | 25 | 26 | -3 | 10 | 31 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Gulp and Spit | Special | POW | 1 Close | 50 | 29 | +2 | 19 | 9 | 36 | drain 40% of dmg | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Swamp Sumo | Chain | POW | 1 Close | 50 | 70 | -5 | 16 | 14 | 42 | — | Iron Quarry: Bog Slam Lv3 + POW ≥ 520 |
| Balloon Belly | Signature | POW | 1 Close | 53 | 0 | +6 | 20 | 18 | 42 | heal 25% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Coilfang

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Coil Squeeze | Basic | POW | 1 Close | 10 | 10 | +3 | 6 | 8 | 24 | — | Starter |
| Fang Snap | Basic | POW | 2 Near | 10 | 10 | +3 | 5 | 7 | 24 | — | Starter · sub-quirk |
| Jade Strike | Hit | POW | 2 Near | 20 | 14 | +14 | 9 | 6 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Constrictor Crush | Heavy | POW | 1 Close | 44 | 50 | -12 | 12 | 10 | 39 | — | Iron Quarry: POW ≥ 360 |
| Venom Mist | Wither | INT | 3 Mid | 27 | 12 | -2 | 40 | 6 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Crest Cleave | Sharp | POW | 2 Near | 25 | 22 | -4 | 11 | 30 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Serpent Dance | Special | POW | 3 Mid | 48 | 16 | +1 | 28 | 12 | 36 | 2 hits | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Jade Viper Rush | Chain | POW | 2 Near | 26 | 20 | +21 | 11 | 9 | 30 | — | Archer's Glade: Jade Strike Lv3 + POW ≥ 520 |
| Emerald Coil | Signature | POW | 1 Close | 55 | 50 | +6 | 26 | 17 | 42 | stun 45 ticks | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Nimbusheep

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Woolly Bump | Basic | POW | 2 Near | 11 | 13 | +3 | 7 | 8 | 24 | — | Starter |
| Drizzle Puff | Basic | INT | 1 Close | 10 | 13 | +7 | 5 | 8 | 24 | — | Starter · sub-quirk |
| Hail Tuft | Hit | INT | 3 Mid | 19 | 15 | +17 | 8 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Downpour | Heavy | INT | 4 Far | 44 | 50 | -12 | 12 | 12 | 39 | — | Iron Quarry: INT ≥ 360 |
| Fog Fleece | Wither | INT | 2 Near | 26 | 12 | -2 | 45 | 8 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Rainbow Arc | Sharp | INT | 4 Far | 29 | 22 | -5 | 9 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Rain Shelter | Special | INT | 3 Mid | 48 | 0 | +2 | 17 | 9 | 36 | heal 20% max HP | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Rainstorm Flock | Chain | INT | 3 Mid | 18 | 20 | +10 | 6 | 11 | 27 | — | Archer's Glade: Drizzle Puff Lv3 + INT ≥ 520 |
| Cumulonimbus | Signature | INT | 4 Far | 60 | 64 | +0 | 23 | 15 | 42 | — | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Galeheron

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Beak Jab | Basic | POW | 2 Near | 11 | 14 | +8 | 5 | 5 | 24 | — | Starter |
| Gust Feather | Basic | INT | 1 Close | 13 | 14 | +8 | 7 | 5 | 24 | — | Starter · sub-quirk |
| Wind Spear | Hit | INT | 3 Mid | 18 | 19 | +20 | 9 | 6 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Tempest Dive | Heavy | INT | 4 Far | 44 | 64 | -6 | 12 | 12 | 39 | — | Iron Quarry: INT ≥ 360 |
| Downdraft | Wither | INT | 3 Mid | 28 | 18 | +4 | 41 | 8 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Lightning Stride | Sharp | POW | 2 Near | 25 | 30 | +2 | 10 | 31 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Squall Line | Special | INT | 4 Far | 48 | 13 | -1 | 16 | 12 | 36 | 3 hits | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Gale Lance | Chain | INT | 3 Mid | 24 | 24 | +21 | 11 | 9 | 30 | — | Archer's Glade: Wind Spear Lv3 + INT ≥ 520 |
| Eye of the Storm | Signature | INT | 3 Mid | 55 | 58 | +2 | 40 | 17 | 42 | stun 45 ticks | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Nibblegrub

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Nibble | Basic | POW | 1 Close | 14 | 12 | +5 | 5 | 5 | 24 | — | Starter |
| Wriggle Roll | Basic | POW | 2 Near | 11 | 13 | +6 | 5 | 4 | 24 | — | Starter · sub-quirk |
| Chomp | Hit | POW | 1 Close | 18 | 15 | +18 | 9 | 9 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Wobble Crush | Heavy | POW | 1 Close | 48 | 64 | -6 | 13 | 11 | 39 | — | Iron Quarry: POW ≥ 360 |
| Silk Spray | Wither | INT | 3 Mid | 29 | 18 | +4 | 39 | 8 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Mandible Snap | Sharp | POW | 2 Near | 26 | 30 | +2 | 11 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Cocoon Guard | Special | POW | 1 Close | 46 | 0 | -2 | 17 | 12 | 36 | heal 20% max HP | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Tumbleweed Roll | Chain | POW | 2 Near | 19 | 25 | +9 | 6 | 7 | 27 | — | Archer's Glade: Wriggle Roll Lv3 + POW ≥ 520 |
| Big Snack | Signature | POW | 1 Close | 53 | 56 | +6 | 21 | 16 | 42 | drain 60% of dmg | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Velvesper

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Dust Puff | Basic | INT | 3 Mid | 12 | 13 | +6 | 5 | 5 | 24 | — | Starter · sub-quirk |
| Wing Flutter | Basic | INT | 2 Near | 12 | 12 | +4 | 6 | 5 | 24 | — | Starter |
| Moonbeam Dart | Hit | INT | 4 Far | 20 | 15 | +13 | 9 | 10 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Dusk Nova | Heavy | INT | 4 Far | 48 | 50 | -12 | 12 | 12 | 39 | — | Iron Quarry: INT ≥ 360 |
| Drowsy Dust | Wither | INT | 3 Mid | 27 | 12 | -2 | 43 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Eyespot Glare | Sharp | INT | 3 Mid | 27 | 22 | -4 | 9 | 29 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Moonlit Waltz | Special | INT | 2 Near | 47 | 30 | +2 | 30 | 12 | 36 | heal 15% max HP | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Crescent Volley | Chain | INT | 4 Far | 26 | 17 | +14 | 11 | 13 | 30 | — | Archer's Glade: Moonbeam Dart Lv3 + INT ≥ 520 |
| Twilight Veil | Signature | INT | 3 Mid | 57 | 43 | +4 | 55 | 30 | 42 | — | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Ashwraith

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ember Touch | Basic | INT | 2 Near | 10 | 10 | +3 | 6 | 7 | 24 | — | Starter |
| Ash Flurry | Basic | INT | 3 Mid | 14 | 10 | +3 | 7 | 7 | 24 | — | Starter · sub-quirk |
| Wisp Lash | Hit | INT | 3 Mid | 19 | 14 | +14 | 7 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Pyre Bloom | Heavy | INT | 4 Far | 48 | 50 | -12 | 12 | 9 | 39 | — | Iron Quarry: INT ≥ 360 |
| Mournful Wail | Wither | INT | 2 Near | 27 | 12 | -2 | 44 | 8 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Ghostflame Dart | Sharp | INT | 4 Far | 29 | 22 | -5 | 11 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Soulsiphon | Special | INT | 3 Mid | 47 | 29 | 0 | 17 | 10 | 36 | drain 50% of dmg | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Phantom Lashes | Chain | INT | 3 Mid | 25 | 19 | +19 | 8 | 11 | 30 | — | Archer's Glade: Wisp Lash Lv3 + INT ≥ 520 |
| Last Ember | Signature | INT | 2 Near | 56 | 66 | +3 | 22 | 15 | 42 | miss: self-dmg 12% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Zipwisp

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Zip Bump | Basic | POW | 2 Near | 14 | 11 | +7 | 7 | 5 | 24 | — | Starter |
| Crackle | Basic | INT | 1 Close | 12 | 13 | +3 | 5 | 6 | 24 | — | Starter · sub-quirk |
| Arc Flick | Hit | INT | 3 Mid | 18 | 16 | +15 | 7 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Overcharge | Heavy | INT | 2 Near | 44 | 50 | -12 | 12 | 12 | 39 | — | Iron Quarry: INT ≥ 360 |
| Static Field | Wither | INT | 4 Far | 27 | 12 | -2 | 43 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Zigzag Bolt | Sharp | INT | 3 Mid | 25 | 22 | -4 | 10 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Chain Spark | Special | INT | 4 Far | 49 | 11 | -1 | 19 | 8 | 36 | 3 hits | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Crackle Storm | Chain | INT | 3 Mid | 20 | 20 | +6 | 6 | 9 | 27 | — | Archer's Glade: Crackle Lv3 + INT ≥ 520 |
| Ball Lightning Dance | Signature | INT | 2 Near | 54 | 13 | +6 | 36 | 17 | 42 | 4 hits | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Mirrorkin

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Glint | Basic | INT | 2 Near | 12 | 11 | +5 | 7 | 8 | 24 | — | Starter |
| Shard Toss | Basic | INT | 3 Mid | 13 | 11 | +4 | 5 | 7 | 24 | — | Starter · sub-quirk |
| Reflection Ray | Hit | INT | 3 Mid | 19 | 18 | +17 | 9 | 9 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Shatterburst | Heavy | INT | 4 Far | 45 | 60 | -11 | 13 | 10 | 39 | — | Iron Quarry: INT ≥ 360 |
| Mocking Image | Wither | INT | 2 Near | 25 | 16 | +3 | 48 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Prism Cut | Sharp | INT | 3 Mid | 27 | 27 | -1 | 10 | 30 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Steal the Spotlight | Special | INT | 2 Near | 49 | 16 | +0 | 34 | 12 | 36 | steal guts = wither | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Infinite Corridor | Chain | INT | 3 Mid | 25 | 23 | +20 | 11 | 12 | 30 | — | Archer's Glade: Reflection Ray Lv3 + INT ≥ 520 |
| Looking-Glass Swap | Signature | INT | 2 Near | 54 | 24 | +5 | 50 | 15 | 42 | steal guts = wither | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Gearhoot

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Talon Tick | Basic | POW | 2 Near | 11 | 14 | +8 | 7 | 8 | 24 | — | Starter |
| Lens Flash | Basic | INT | 1 Close | 11 | 14 | +8 | 6 | 8 | 24 | — | Starter · sub-quirk |
| Calibrated Shot | Hit | INT | 3 Mid | 17 | 19 | +20 | 8 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Overclock Cannon | Heavy | INT | 4 Far | 45 | 64 | -6 | 11 | 8 | 39 | — | Iron Quarry: INT ≥ 360 |
| Gear Grind | Wither | INT | 2 Near | 26 | 18 | +4 | 46 | 4 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Precision Bolt | Sharp | INT | 4 Far | 25 | 30 | +2 | 10 | 31 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Spring Repair | Special | INT | 3 Mid | 49 | 0 | +2 | 16 | 11 | 36 | heal 25% max HP | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Clockwork Barrage | Chain | INT | 3 Mid | 23 | 9 | +23 | 10 | 11 | 30 | 3 hits | Archer's Glade: Calibrated Shot Lv3 + INT ≥ 520 |
| Midnight Chime | Signature | INT | 3 Mid | 53 | 29 | +3 | 55 | 18 | 42 | stun 45 ticks | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Reefclaw

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Pincer Pinch | Basic | POW | 1 Close | 14 | 10 | +3 | 5 | 4 | 24 | — | Starter · sub-quirk |
| Shell Shove | Basic | POW | 2 Near | 11 | 10 | +3 | 5 | 7 | 24 | knockback | Starter |
| Coral Jab | Hit | POW | 2 Near | 16 | 14 | +14 | 7 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Tidebreaker Clamp | Heavy | POW | 1 Close | 47 | 62 | -9 | 12 | 11 | 39 | — | Iron Quarry: POW ≥ 360 |
| Barnacle Spray | Wither | POW | 3 Mid | 26 | 15 | +1 | 43 | 4 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Sideways Slash | Sharp | POW | 2 Near | 28 | 24 | -3 | 11 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Riptide Hold | Special | POW | 1 Close | 49 | 30 | +0 | 18 | 9 | 36 | stun 40 ticks | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Reef Lance | Chain | POW | 2 Near | 22 | 22 | +17 | 8 | 11 | 30 | — | Archer's Glade: Coral Jab Lv3 + POW ≥ 520 |
| Kingtide | Signature | POW | 2 Near | 53 | 58 | +2 | 27 | 15 | 42 | knockback | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Lootlid

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Lid Chomp | Basic | POW | 1 Close | 13 | 14 | +8 | 7 | 5 | 24 | — | Starter |
| Coin Toss | Basic | INT | 2 Near | 13 | 14 | +8 | 5 | 4 | 24 | — | Starter · sub-quirk |
| Tongue Grab | Hit | POW | 1 Close | 18 | 19 | +20 | 8 | 10 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Treasure Slam | Heavy | POW | 1 Close | 47 | 64 | -6 | 11 | 10 | 39 | — | Iron Quarry: POW ≥ 360 |
| Fool's Gold Glare | Wither | INT | 3 Mid | 26 | 14 | +1 | 38 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Hinge Snap | Sharp | POW | 2 Near | 28 | 30 | +2 | 10 | 30 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Jackpot! | Special | INT | 3 Mid | 48 | 35 | -2 | 16 | 11 | 36 | random: x2 dmg / heal 20% / fizzle | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Gold Rain | Chain | INT | 2 Near | 21 | 9 | +8 | 6 | 7 | 27 | 3 hits | Archer's Glade: Coin Toss Lv3 + INT ≥ 520 |
| Hoard Avalanche | Signature | POW | 2 Near | 56 | 72 | +3 | 23 | 16 | 42 | miss: self-dmg 12% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Aurelwyrm

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gilded Claw | Basic | POW | 1 Close | 10 | 14 | +8 | 7 | 6 | 24 | — | Starter |
| Sun Spark | Basic | INT | 3 Mid | 12 | 14 | +8 | 7 | 5 | 24 | — | Starter · sub-quirk |
| Ribbon Lash | Hit | POW | 2 Near | 17 | 19 | +20 | 7 | 9 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Sovereign Crush | Heavy | POW | 1 Close | 46 | 64 | -6 | 12 | 12 | 39 | — | Iron Quarry: POW ≥ 360 |
| Dragon's Glare | Wither | INT | 3 Mid | 29 | 14 | +3 | 39 | 4 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Crown Horn Thrust | Sharp | POW | 2 Near | 25 | 30 | +2 | 9 | 30 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Solar Flare Breath | Special | INT | 4 Far | 49 | 56 | -1 | 22 | 8 | 36 | — | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Sunfire Volley | Chain | INT | 3 Mid | 20 | 25 | +6 | 8 | 8 | 27 | — | Archer's Glade: Sun Spark Lv3 + INT ≥ 520 |
| Heaven's Ribbon | Signature | INT | 4 Far | 60 | 66 | +2 | 21 | 17 | 42 | — | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Hearthwing

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Talon Rake | Basic | POW | 1 Close | 11 | 14 | +4 | 7 | 7 | 24 | — | Starter |
| Cinder Cough | Basic | INT | 3 Mid | 11 | 11 | +7 | 5 | 5 | 24 | — | Starter · sub-quirk |
| Wingbeat Jab | Hit | POW | 2 Near | 19 | 15 | +15 | 8 | 6 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Furnace Crush | Heavy | POW | 1 Close | 45 | 53 | -11 | 11 | 9 | 39 | — | Iron Quarry: POW ≥ 360 |
| Smoulder Smoke | Wither | INT | 3 Mid | 27 | 14 | +2 | 37 | 6 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Horn Hook | Sharp | POW | 2 Near | 29 | 27 | -3 | 11 | 29 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Bellows Blaze | Special | INT | 4 Far | 48 | 11 | +0 | 17 | 8 | 36 | 3 hits | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Cinder Gust | Chain | INT | 3 Mid | 19 | 19 | +10 | 6 | 8 | 27 | — | Archer's Glade: Cinder Cough Lv3 + INT ≥ 520 |
| Hearthfire Torrent | Signature | INT | 4 Far | 60 | 64 | +0 | 25 | 15 | 42 | — | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Grumblestone

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Pebble Punch | Basic | POW | 1 Close | 10 | 10 | +3 | 6 | 5 | 24 | — | Starter |
| Grumble Shove | Basic | POW | 2 Near | 10 | 10 | +3 | 7 | 8 | 24 | knockback | Starter · sub-quirk |
| Knuckle Knock | Hit | POW | 1 Close | 17 | 14 | +14 | 7 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Geode Smash | Heavy | POW | 1 Close | 45 | 64 | -6 | 13 | 12 | 39 | — | Iron Quarry: POW ≥ 360 |
| Gravel Grind | Wither | POW | 2 Near | 28 | 18 | +4 | 46 | 8 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Crystal Jab | Sharp | POW | 2 Near | 27 | 30 | +2 | 10 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Rockfall Ruckus | Special | POW | 3 Mid | 49 | 13 | +2 | 18 | 12 | 36 | 3 hits | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Amethyst Avalanche | Chain | POW | 1 Close | 51 | 94 | -9 | 16 | 15 | 42 | — | Iron Quarry: Geode Smash Lv3 + POW ≥ 520 |
| Crystal Heart Quake | Signature | POW | 2 Near | 54 | 34 | +4 | 50 | 18 | 42 | stun 45 ticks | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Pluckrex

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Snap Bite | Basic | POW | 1 Close | 11 | 12 | +6 | 6 | 5 | 24 | — | Starter |
| Tail Thump | Basic | POW | 2 Near | 12 | 11 | +7 | 7 | 5 | 24 | — | Starter · sub-quirk |
| Plucky Jab | Hit | POW | 2 Near | 18 | 15 | +14 | 8 | 9 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Courage Crash | Heavy | POW | 1 Close | 44 | 52 | -11 | 11 | 8 | 39 | — | Iron Quarry: POW ≥ 360 |
| Crest Flare | Wither | INT | 3 Mid | 28 | 14 | +1 | 43 | 7 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Rising Claw | Sharp | POW | 2 Near | 25 | 24 | -1 | 10 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Stampede Rush | Special | POW | 3 Mid | 50 | 42 | +0 | 17 | 8 | 36 | dash to Close after | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Hero's Combo | Chain | POW | 2 Near | 24 | 20 | +17 | 10 | 12 | 30 | — | Archer's Glade: Plucky Jab Lv3 + POW ≥ 520 |
| Sunrise Roar | Signature | INT | 4 Far | 56 | 30 | +4 | 40 | 16 | 42 | stun 30 ticks | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Paladove

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Wing Buffet | Basic | POW | 2 Near | 14 | 12 | +3 | 6 | 8 | 24 | — | Starter |
| Halo Spark | Basic | INT | 1 Close | 11 | 12 | +5 | 7 | 8 | 24 | — | Starter · sub-quirk |
| Lightfeather Dart | Hit | INT | 3 Mid | 16 | 14 | +18 | 9 | 10 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Dawnbreak Beam | Heavy | INT | 4 Far | 47 | 50 | -12 | 13 | 9 | 39 | — | Iron Quarry: INT ≥ 360 |
| Lull of Peace | Wither | INT | 2 Near | 27 | 15 | +1 | 40 | 4 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Gleaming Quill | Sharp | INT | 4 Far | 27 | 23 | -2 | 10 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Mending Hymn | Special | INT | 3 Mid | 46 | 0 | -1 | 0 | 0 | 36 | heal 25% max HP | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Featherlight Volley | Chain | INT | 3 Mid | 22 | 7 | +21 | 11 | 13 | 30 | 3 hits | Archer's Glade: Lightfeather Dart Lv3 + INT ≥ 520 |
| Sanctuary Wings | Signature | INT | 2 Near | 53 | 0 | +3 | 40 | 14 | 42 | heal 15% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Starhowl

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Night Nip | Basic | POW | 1 Close | 11 | 10 | +3 | 7 | 5 | 24 | — | Starter |
| Twinkle Yip | Basic | INT | 3 Mid | 11 | 10 | +3 | 7 | 8 | 24 | — | Starter · sub-quirk |
| Moonleap Strike | Hit | POW | 2 Near | 16 | 14 | +14 | 8 | 7 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Eclipse Maul | Heavy | POW | 1 Close | 48 | 56 | -10 | 12 | 9 | 39 | — | Iron Quarry: POW ≥ 360 |
| Northwind Wail | Wither | INT | 3 Mid | 28 | 15 | +1 | 38 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Comet Fang | Sharp | POW | 2 Near | 28 | 29 | -1 | 10 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Falling Star Volley | Special | INT | 4 Far | 47 | 10 | -4 | 18 | 12 | 36 | 3 hits | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Supernova Fang | Chain | POW | 2 Near | 34 | 38 | +2 | 12 | 31 | 33 | — | Windrun Steppe: Comet Fang Lv3 + POW ≥ 520 |
| Constellation Hunt | Signature | INT | 3 Mid | 54 | 15 | +6 | 25 | 30 | 42 | 4 hits | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Petalphant

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Trunk Bop | Basic | POW | 2 Near | 14 | 14 | +8 | 6 | 8 | 24 | — | Starter |
| Seed Sneeze | Basic | INT | 1 Close | 11 | 14 | +8 | 7 | 6 | 24 | — | Starter · sub-quirk |
| Ear Flap Slap | Hit | POW | 2 Near | 17 | 19 | +20 | 8 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Stomp of Spring | Heavy | POW | 1 Close | 46 | 64 | -6 | 13 | 8 | 39 | — | Iron Quarry: POW ≥ 360 |
| Sleepy Blossom | Wither | INT | 3 Mid | 28 | 18 | +4 | 40 | 7 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Thorn Whirl | Sharp | INT | 2 Near | 26 | 30 | +2 | 11 | 31 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Rainwater Bath | Special | INT | 3 Mid | 49 | 0 | +1 | 0 | 0 | 36 | heal 25% max HP | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Seed Storm Sneeze | Chain | INT | 3 Mid | 19 | 21 | +10 | 8 | 9 | 27 | — | Archer's Glade: Seed Sneeze Lv3 + INT ≥ 520 |
| Full Bloom | Signature | INT | 1 Close | 56 | 58 | +6 | 26 | 18 | 42 | drain 60% of dmg | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Scrollopus

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tentacle Swat | Basic | POW | 2 Near | 13 | 14 | +8 | 7 | 5 | 24 | — | Starter |
| Ink Flick | Basic | INT | 1 Close | 12 | 14 | +8 | 5 | 5 | 24 | — | Starter · sub-quirk |
| Footnote Dart | Hit | INT | 3 Mid | 18 | 19 | +20 | 9 | 10 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Tome Tsunami | Heavy | INT | 4 Far | 48 | 64 | -6 | 13 | 8 | 39 | — | Iron Quarry: INT ≥ 360 |
| Ink Cloud | Wither | INT | 2 Near | 27 | 18 | +4 | 48 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Quill Scribble | Sharp | INT | 3 Mid | 29 | 30 | +2 | 9 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Eightfold Lecture | Special | INT | 4 Far | 47 | 9 | -2 | 19 | 11 | 36 | 4 hits | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Bibliography Barrage | Chain | INT | 3 Mid | 24 | 10 | +18 | 11 | 13 | 30 | 3 hits | Archer's Glade: Footnote Dart Lv3 + INT ≥ 520 |
| Inksteal Riddle | Signature | INT | 2 Near | 57 | 27 | +6 | 50 | 17 | 42 | steal guts = wither | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Gloomgrin

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Grin Bite | Basic | POW | 1 Close | 13 | 14 | +7 | 6 | 6 | 24 | — | Starter |
| Wing Slap | Basic | POW | 2 Near | 14 | 12 | +4 | 7 | 7 | 24 | — | Starter · sub-quirk |
| Sneaky Jab | Hit | POW | 1 Close | 17 | 16 | +16 | 9 | 10 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Rooftop Drop | Heavy | POW | 1 Close | 44 | 56 | -10 | 13 | 12 | 39 | — | Iron Quarry: POW ≥ 360 |
| Spooky Snicker | Wither | INT | 2 Near | 26 | 14 | +0 | 44 | 7 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Ledge Claw | Sharp | POW | 2 Near | 29 | 24 | -1 | 11 | 32 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Rain-Spout Spit | Special | POW | 3 Mid | 49 | 30 | +2 | 16 | 12 | 36 | stun 30 ticks | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Dusk Ambush | Chain | POW | 1 Close | 23 | 22 | +19 | 11 | 13 | 30 | — | Archer's Glade: Sneaky Jab Lv3 + POW ≥ 520 |
| Petrify Pounce | Signature | POW | 1 Close | 57 | 44 | +2 | 24 | 14 | 42 | stun 45 ticks | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Rammerjack

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Horn Bonk | Basic | POW | 1 Close | 11 | 10 | +3 | 7 | 8 | 24 | — | Starter |
| Hoof Stamp | Basic | POW | 2 Near | 11 | 10 | +3 | 7 | 8 | 24 | — | Starter · sub-quirk |
| Brow Bump | Hit | POW | 2 Near | 18 | 14 | +14 | 8 | 7 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Battering Charge | Heavy | POW | 1 Close | 44 | 50 | -12 | 13 | 10 | 39 | dash to Close after | Iron Quarry: POW ≥ 360 |
| Bleat Blast | Wither | POW | 3 Mid | 25 | 12 | -2 | 41 | 5 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Spiral Horn Hook | Sharp | POW | 2 Near | 27 | 22 | -4 | 10 | 30 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Avalanche Charge | Special | POW | 3 Mid | 47 | 36 | -2 | 19 | 10 | 36 | knockback | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Twin Horn Bash | Chain | POW | 1 Close | 19 | 19 | +10 | 8 | 11 | 27 | — | Archer's Glade: Horn Bonk Lv3 + POW ≥ 520 |
| Mountain Ram | Signature | POW | 2 Near | 53 | 64 | +4 | 23 | 18 | 42 | miss: self-dmg 10% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Frostlance

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tusk Poke | Basic | POW | 1 Close | 14 | 14 | +8 | 5 | 6 | 24 | — | Starter |
| Snowflake Puff | Basic | INT | 3 Mid | 12 | 14 | +8 | 7 | 5 | 24 | — | Starter · sub-quirk |
| Icicle Thrust | Hit | POW | 2 Near | 19 | 19 | +20 | 7 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Blizzard Lance | Heavy | INT | 4 Far | 46 | 64 | -6 | 13 | 10 | 39 | — | Iron Quarry: INT ≥ 360 |
| Frostbite Breeze | Wither | INT | 3 Mid | 27 | 18 | +4 | 42 | 7 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Glacier Pierce | Sharp | POW | 2 Near | 27 | 30 | +2 | 10 | 29 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Northern Lights | Special | INT | 4 Far | 48 | 0 | -2 | 30 | 0 | 36 | heal 15% max HP | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Crystal Lance Rush | Chain | POW | 2 Near | 25 | 25 | +20 | 8 | 11 | 30 | — | Archer's Glade: Icicle Thrust Lv3 + POW ≥ 520 |
| Polar Spiral | Signature | POW | 2 Near | 54 | 18 | +3 | 23 | 30 | 42 | 3 hits | Pure breed: auto at Prime (loyalty ≥ 60) |

### 3.1 Universal techniques (Songsheets; any monster can learn these)

24 music-themed techniques, one Songsheet each, sold at the Guild Library and given as prizes. A POW technique uses the monster's POW and an INT technique uses its INT.

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | Songsheet price · where |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Beat Bump | Basic | POW | 1 Close | 14 | 14 | +3 | 7 | 7 | 24 | — | 500G · Guild Library, from the start |
| Shuffle Step Kick | Basic | POW | 2 Near | 11 | 12 | +3 | 5 | 8 | 24 | — | 500G · Guild Library, from the start |
| Hum Pulse | Basic | INT | 3 Mid | 12 | 13 | +4 | 6 | 8 | 24 | — | 500G · Guild Library, from the start |
| Whistle Shot | Basic | INT | 4 Far | 13 | 11 | +4 | 7 | 7 | 24 | — | 500G · Guild Library, from the start |
| Staccato Jab | Hit | POW | 1 Close | 17 | 19 | +16 | 7 | 6 | 27 | — | 1,000G · Guild Library, from the start |
| Downbeat Strike | Hit | POW | 2 Near | 18 | 15 | +18 | 8 | 10 | 27 | — | 1,000G · Guild Library, from the start |
| Chime Bolt | Hit | INT | 3 Mid | 20 | 14 | +16 | 7 | 8 | 27 | — | 1,000G · Guild Library, from the start |
| Piccolo Dart | Hit | INT | 4 Far | 20 | 17 | +13 | 7 | 9 | 27 | — | 1,000G · Guild Library, from the start |
| Crescendo Slam | Heavy | POW | 1 Close | 47 | 56 | -9 | 13 | 11 | 39 | — | 2,500G · Guild Library, rank 4+ · or prizes/expeditions earlier |
| Timpani Crash | Heavy | POW | 2 Near | 45 | 61 | -7 | 12 | 9 | 39 | — | 2,500G · Guild Library, rank 4+ · or prizes/expeditions earlier |
| Grand Finale | Heavy | INT | 3 Mid | 48 | 52 | -10 | 11 | 10 | 39 | — | 2,500G · Guild Library, rank 4+ · or prizes/expeditions earlier |
| Fortissimo Blast | Heavy | INT | 4 Far | 44 | 53 | -13 | 11 | 10 | 39 | — | 2,500G · Guild Library, rank 4+ · or prizes/expeditions earlier |
| Drumroll Stomp | Wither | POW | 1 Close | 27 | 17 | +3 | 41 | 8 | 30 | — | 1,500G · Guild Library, breeder rank 2+ |
| Off-Key Wail | Wither | INT | 2 Near | 25 | 15 | -1 | 41 | 4 | 30 | — | 1,500G · Guild Library, breeder rank 2+ |
| Lullaby Haze | Wither | INT | 3 Mid | 27 | 15 | -1 | 44 | 5 | 30 | — | 1,500G · Guild Library, breeder rank 2+ |
| Hush Note | Wither | INT | 4 Far | 28 | 13 | -1 | 40 | 7 | 30 | — | 1,500G · Guild Library, breeder rank 2+ |
| Cymbal Clash | Sharp | POW | 1 Close | 27 | 28 | +1 | 9 | 30 | 30 | — | 1,500G · Guild Library, breeder rank 2+ |
| Pizzicato Pluck | Sharp | POW | 2 Near | 26 | 25 | +1 | 9 | 31 | 30 | — | 1,500G · Guild Library, breeder rank 2+ |
| Tremolo Ray | Sharp | INT | 3 Mid | 25 | 25 | +0 | 10 | 30 | 30 | — | 1,500G · Guild Library, breeder rank 2+ |
| High Note | Sharp | INT | 4 Far | 29 | 24 | -1 | 9 | 31 | 30 | — | 1,500G · Guild Library, breeder rank 2+ |
| Rondo Rush | Special | POW | 2 Near | 48 | 10 | -2 | 17 | 9 | 36 | 3 hits | 4,000G · Guild Library, rank 4+ · or prizes/expeditions earlier |
| Harmony Mend | Special | INT | 3 Mid | 49 | 0 | +0 | 0 | 0 | 36 | heal 20% max HP | 4,000G · Guild Library, rank 4+ · or prizes/expeditions earlier |
| Resonance Drain | Special | INT | 3 Mid | 47 | 31 | +0 | 19 | 11 | 36 | drain 40% of dmg | 4,000G · Guild Library, rank 4+ · or prizes/expeditions earlier |
| Feedback Loop | Special | INT | 4 Far | 49 | 16 | -2 | 36 | 9 | 36 | steal guts = wither | 4,000G · Guild Library, rank 4+ · or prizes/expeditions earlier |

---

## 4. Drills

| Kind | Drill | Effect | Vignette (2–3 s, skippable) |
|---|---|---|---|
| Light | **Hill Sprints** | LIF+ | Jogging up and down the grassy hill behind the barn |
| Light | **Log Toss** | POW+ | Heaving a log over a fence |
| Light | **Puzzle Stones** | INT+ | Sliding carved stones into the right holes |
| Light | **Target Toss** | SKI+ | Throwing pinecones at a painted target |
| Light | **Dodge the Gourds** | SPD+ | Dodging gourds that Wren swings on ropes |
| Light | **Acorn Shower** | DEF+ | Standing firm under a shaken oak tree |
| Heavy | **Plow Pull** | POW++ LIF+ SPD− | Dragging the old plow across the field |
| Heavy | **Moon Meditation** | INT++ SKI+ DEF− | Sitting under the moon on a flat rock, very still |
| Heavy | **Wind Chase** | SPD++ INT+ POW− | Chasing leaves in the windmill's gusts |
| Heavy | **Waterfall Stand** | DEF++ LIF+ INT− | Bracing under the little waterfall |
| Heavy | **Quarry Haul** (needs the Training Yard) | LIF++ DEF+ SKI− | Hauling stones from the old quarry |

---

## 5. Monthly food

| Food | Price | Neutral | Liked | Disliked |
|---|---|---|---|---|
| Turnips | 20G | S +4, Fe +2 | Sp +2 | S +12 |
| River Fish | 100G | S −3, form +2 | S −6, form +2 | S +2 |
| Honey Bread | 120G | S −4, form +3 | S −6, form +4, Sp +1 | S +2 |
| Berry Pudding | 150G | S −5, form −2 | S −8, form −3 | S +1 |
| Roast Haunch | 300G | S −6, form +6 | S −9, form +7 | Fe +2 |
| Hearty Stew | 450G | S −8, form +3, life +1 wk | S −11, form +3, life +1 wk | S −2, life +1 wk |
| Herbal Pellets | 500G | S −12 | S −15 | S −9 |

- At birth each monster gets one liked food and one disliked food (never the same one), rolled from its seed.
- Boredom: see GAME_DESIGN §8.

---

## 6. Items

There's **no limit** on how many items you use or buy (GAME_DESIGN §8). Life fruits are the one exception: each works once per monster.

| Item | Category | Price | Effect |
|---|---|---|---|
| Sun Plum | Recovery | 60G | Fatigue −10 |
| Warm Compress | Recovery | 200G | Fatigue −25 |
| Lavender Sachet | Recovery | 100G | Stress −10 |
| Calmleaf Tea | Recovery | 200G | Stress halved |
| Berry Tart | Mood | 150G | Spoil +8 |
| Thunder Rattle | Mood | 150G | Fear +8 |
| Kindness Charm | Mood | 120G | Nature +5 |
| Mischief Charm | Mood | 120G | Nature −5 |
| Honey Taffy | Form | 120G | Form +10 |
| Leanroot Tea | Form | 120G | Form −10 |
| Mighty Muffin · Clever Cookie · Steady Scone · Zippy Waffle · Sturdy Bun · Lively Pie | Stat Sweet | 400G | Permanently +5 POW · INT · SKI · SPD · DEF · LIF |
| Grand Muffin · Grand Cookie · Grand Scone · Grand Waffle · Grand Bun · Grand Pie | Stat Sweet | 1,500G (stocked once you have a grade C monster) | Permanently +15 to that stat |
| Wondercake | Stat Sweet | 2,500G (breeder rank 3+) | Permanently +5 to all six stats |
| Potential Pearl | Potential | 8,000G (rank 5+) | One stat's growth grade +1 step (max A) |
| Tempo Bell | Potential | 6,000G (rank 4+) | Guts rate −1 (regenerates faster), minimum 6 |
| Songsheets | Technique | 500–5,000G | Teach one technique; kept forever in the Songbook (GAME_DESIGN §10.5) |
| Ironroot Tonic | Tonic | 1,500G | 4 weeks: +3 POW on each successful drill that raises POW · **−6 weeks life** |
| Sagebrew | Tonic | 1,500G | Same for INT · −6 weeks |
| Hawkeye Drops | Tonic | 1,500G | Same for SKI · −6 weeks |
| Swiftmint | Tonic | 1,500G | Same for SPD · −6 weeks |
| Stoneskin Salve | Tonic | 1,500G | Same for DEF · −6 weeks |
| Heartroot Elixir | Tonic | 1,500G | Same for LIF · −6 weeks |
| Sunfruit | Life fruit | found only | +40 weeks lifespan (once per monster) |
| Moonfruit | Life fruit | found only | +20 weeks lifespan (once per monster) |
| Rubber Ball / Rope Tug / Music Box / Paper Kite / Squeaky Fish / Puzzle Cube | Toy | 300G | 5 uses. Favorite toy: S −12, Sp +4. Other toys: S −4 |
| Wind Chime → Silver Chime → Gold Chime | Charm · Comfort | 2k / 6k / 15k | Stress −2 / −4 / −6 in week 1 of each month (best one only) |
| Straw Bed → Feather Bed → Cloud Bed | Charm · Bedding | 2k / 6k / 15k | Rest removes +3 / +6 / +10 more fatigue (best one only) |
| Power / Mind / Skill / Swift / Guard / Life Shard | Catalyst | found / 3,000G | Fusion: +40 to that stat |
| Amber Charm | Catalyst | found | Fusion: baby lifespan +20 weeks |
| Lineage Seal | Catalyst | 5,000G (rank 5+) | Fusion: doubles the first parent's main-breed weight |
| Vigil Lantern · Stormglass · Shard Mask · Brass Blueprint · Wyrm Scale | Key item | event | Unlocks (§11) |
| Oduya's Charm · Lark's Charm · Ilsabet's Charm · Teo's Charm · Brask's Charm | Key item | mentor bond (every 8 Journeys at that site) | Lowers that mentor's technique requirements by 50, for good (GAME_DESIGN §11) |
| Old Coin · Silver Locket · Ruby Chip · Starstone | Sellable | sell 300 / 800 / 2,000 / 6,000G | Expedition loot |

---

## 7. Journeys (mentor sites)

| Site | Mentor | Stat (+LIF) | Family | Open | Gate |
|---|---|---|---|---|---|
| **Iron Quarry** | Master Oduya | POW | Heavy | All year | — |
| **Windrun Steppe** | Coach Lark | SPD | Sharp | Mar–Nov (closed in winter snows) | — |
| **Starfall Observatory** | Sage Ilsabet | INT | Wither | All year | — |
| **Archer's Glade** | Ranger Teo | SKI | Hit | All year | — |
| **Glacier Bastion** | Warden Brask | DEF | Special | Sep–May (closed in summer thaw) | Monster grade B+ |

**Trial opponents:** a wild monster of a breed native to the site:
- Iron Quarry: Cobblemaw or Reefclaw
- Windrun Steppe: Galeheron or Zipwisp
- Starfall Observatory: Wishlume or Velvesper
- Archer's Glade: Quillion or Tumblefox
- Glacier Bastion: Moatshell or Nimbusheep

Each wild breed is only used once it is unlocked; otherwise use the site's first breed.

---

## 8. Expeditions

| Site | Invitation (mail in week 1) | Requirements | Obstacle stats | Highlights |
|---|---|---|---|---|
| **Thornwood Ruins** | March and September | Grade E+, fame ≥ 20 | Brambles (POW 200), riddle doors (INT 200), snares (SKI 200) | **Strange Chest** (Lootlid, §11) · toys · Old Coins · Stat Sweets · Basic/Hit Songsheets · Moonfruit (rare) |
| **Sunken Library** | June | Grade C+, fame ≥ 40 | Sealed shelves (INT 300), flooded halls (stamina), collapsing floors (SPD 300). **Hidden archive: INT ≥ 350** | **Brass Blueprint** (hidden archive) · Silver Lockets · Mind Shard · Wither/Sharp Songsheets · Sunfruit (rare) |
| **Hollowmoon Caverns** | November | Grade C+, fame ≥ 45 | Boulders (POW 350), dark tunnels (INT reveals), crystal traps (SKI 350) | Ruby Chips · Power/Guard Shards · Amber Charm · Heavy Songsheets · Grand Sweets |
| **Skyreef Isles** | August | Grade B+, fame ≥ 60 | Gaps (SPD 450), gales (DEF 400), sky puzzles (INT 400) | Starstones · Swift/Skill Shards · Sunfruit · rare toys · Special Songsheets · Potential Pearl (rare) |

Guide: **Tomas** comes along and narrates.

---

## 9. Tournament calendar (48 weeks)

**Format abbreviations:**
- **RR4 / RR6:** round robin of 4 or 6.
- **Elim4 / Elim8:** elimination bracket of 4 or 8.
- **1v1:** a single match.
- **Inv.:** invitation only.

**Purses** are for 1st place; Officials pay little (GAME_DESIGN §13). **Bold** marks Officials, Crowns and the Legend Cup.

| Month | Week 1 | Week 2 | Week 3 | Week 4 |
|---|---|---|---|---|
| **Jan** (winter) | Frost Fair Cup · C · RR4 · 2,500 | Snowdrift Cup · E · Elim4 · 800 | Hearthfire Cup · B · RR4 · 4,000 | New Year Open · any grade (matched ±1) · Elim8 · 4,000 |
| **Feb** | Ice Lantern Cup · D · RR4 · 1,500 | **Crown of Dawn** · S Inv. · RR4 · 10,000 + Cocoa Cup · C · RR4 · 2,500 | Thaw Cup · E · RR4 · 1,000 | Twin Hearts Cup · A · Elim4 · 6,000 |
| **Mar** (spring) | Bud Cup · D · Elim4 · 1,500 | Meadow Cup · B · RR4 · 4,000 | Spring Masters · S · RR4 · 8,000 + Kite Day Cup · E · RR4 · 900 | **Spring Ascension** (Officials E–S · RR6) |
| **Apr** | Blossom Cup · C · RR4 · 3,000 | Rain Cup · E · RR4 · 1,000 | Pebble Cup · A · RR4 · 7,000 | **The Wildsong Legend** · Inv. · 1v1 · 15,000 + Daffodil Cup · D · RR4 · 2,000 |
| **May** | Iron Cup · B · POW techniques only · RR4 · 5,000 | **Crown of Tides** · S Inv. · RR4 · 10,000 + Clover Cup · D · RR4 · 2,000 | Songbird Cup · E · RR4 · 1,000 | May Fair Cup · C · Elim4 · 3,000 |
| **Jun** (summer) | Sunny Cup · A · RR4 · 7,000 | Sprout Cup (age < 48 wks; even years) or Elders' Cup (age ≥ 288 wks; odd years) · any grade · RR4 · 3,000 / 8,000 | Firefly Cup · D · RR4 · 2,000 + Summer Masters · S · RR4 · 8,000 | **Summer Ascension** (Officials) |
| **Jul** | Tidepool Cup · C · RR4 · 3,000 | Arcane Cup · B · INT techniques only · RR4 · 5,000 | Seashell Cup · E · RR4 · 1,200 | Summit Qualifier (every 4th year) · own grade · RR4 · 1,000 × grade index; other years Heatwave Cup · A · Elim4 · 7,000 |
| **Aug** | Lantern Festival Cup · D · Elim4 · 2,000 | **Crown of Embers** · S Inv. · RR4 · 10,000 + Sandcastle Cup · C · RR4 · 3,000 | Thunder Cup · B · RR4 · 5,000 | Vale–Coast Summit (every 4th year) · team relay; other years Stargazer Cup · E · RR4 · 1,200 |
| **Sep** (autumn) | Harvest Cup · A · RR4 · 8,000 | Apple Cup · C · RR4 · 3,000 | Scarecrow Cup · E · Elim4 · 1,000 + Autumn Masters · S · RR4 · 8,000 | **Autumn Ascension** (Officials) |
| **Oct** | Masquerade Cup · rumor Inv. (B+) · 1v1 vs the Masked Breeder · 6,000 + Shard Mask | Acorn Cup · D · RR4 · 2,000 | Bonfire Cup · B · Elim4 · 5,000 | Hero's Rally (nature ≥ +20) / Rogue's Rally (nature ≤ −20) · any grade · RR6 · 4,000 |
| **Nov** | Maple Cup · C · RR4 · 3,000 | **Crown of Frost** · S Inv. · RR4 · 10,000 + Mushroom Cup · E · RR4 · 1,000 | Copper Cup · A · RR4 · 8,000 | Hearth Cup · D · Elim4 · 2,000 |
| **Dec** | Starlight Cup · S · RR4 · 9,000 | Snowflake Cup · B · RR4 · 5,000 | Rival Showdown · 1v1 vs Corin Hale (your grade, C+) · 3,000 | **Winter Ascension** (Officials) |

**Invitations:**
- **Crowns:** an S-grade monster that has won an S Official is invited to every Crown. The invitation arrives by mail one month before.
- **Legend Cup:** invitation in March once a monster has won all four Crowns.
- **Summit years:** Year 4, 8, 12, …
- **Item prizes:** 1st place also wins items (Stat Sweets, Songsheets, Wondercakes, and Signature sheets at the Crowns); see GAME_DESIGN §13.
- **Vale–Coast Summit format:** 5 sequential 1v1s, one per grade D–S. You fill your monster's grade slot and NPC teammates fill the rest. Team win: 3,000G, plus 1,000G per win of your own.

---

## 10. Rival breeders

| Rival | AI personality | Signature monster | Readable habit | Appears in |
|---|---|---|---|---|
| **Corin Hale** (your rival) | Steady, then Aggressive from grade A | A Tumblefox line, an Aurelwyrm by the Crowns | Opens every match with its Far technique | Your grade's Officials, Rival Showdown, Crowns |
| Marigold Finch | Steady | Puddlepup | Banks guts to 70 before a Heavy | E–C cups |
| Brannock Steele | Brawler | Cobblemaw | Always walks straight into Close range | C–S cups |
| Wisteria Vane | Sniper | Wishlume | Backs away whenever you approach | D–A cups |
| Juno Quell | Trickster | Coilfang | Spams Wither techniques | C–A cups |
| Old Man Garrow | Cautious | Moatshell | Waits at 99 guts before attacking | B–S cups |
| Captain Saltmarsh | Aggressive | Reefclaw | Pushes whenever touching | B–S cups |
| Ember Rook | Aggressive | Cinderlynx | Dashes in when below half HP | C–S cups |
| The Masked Breeder | Trickster | Mirrorkin | Steals guts constantly | Masquerade Cup |

Rival monsters are generated by the NPC rules (GAME_DESIGN §13) at the cup's grade. Corin Hale scales with you: your monster's total × 1.05.

---

## 11. Unlock chains (8 locked breeds)

None of these can be permanently missed. Each starts with a rumor, and the Journal's Rumors page sharpens its hint as you make progress.

1. **Velvesper (metamorphosis).**
   - Rumor (Basil, after you've owned a Nibblegrub for about a year): "Grubs that eat sweet pudding and live happy lives sometimes spin silk…"
   - Condition: in June week 4, a Nibblegrub aged 144–240 weeks with loyalty ≥ 70, fatigue ≤ 20 and stress ≤ 15, that has had Berry Pudding as its monthly food at least 12 times.
   - Result: it spins a cocoon for 4 weeks (no actions; it still ages) and emerges as a Velvesper with the same sub-breed.
     - It keeps 80% of its trained gains.
     - Lifespan total +60 weeks.
     - Techniques are kept where Velvesper's kit has the same family; otherwise they become Velvesper's starters.
   - Unlocks Velvesper at the Shrine. Title: "Silk & Moonlight".
2. **Ashwraith (memorial).**
   - After any monster passes away or retires, mail the next week 1 brings Sister Mara's Lantern Vigil: a free action at the Shrine.
   - Attending gives the **Vigil Lantern**. Offer it at the Shrine to unlock Ashwraith.
3. **Zipwisp (storm chase).**
   - Rumor from Coach Lark: "Fast monsters chase the summer sparks."
   - Storm weather happens on about 20% of June–August weeks.
   - Condition: at the start of a storm week, the active monster has SPD ≥ 300, stress ≤ 25 and fatigue ≤ 30.
   - Event (uses the week): it chases a spark into the hills and returns with **Stormglass**. Offer it at the Shrine to unlock Zipwisp. Title: "Storm Chaser".
4. **Mirrorkin (masquerade).**
   - Once any monster reaches grade B, Basil whispers in September about "a masked breeder who only fights the strong."
   - The Masquerade Cup appears in October week 1 (grade B+ only).
   - Win: **Shard Mask**. Offer it at the Shrine to unlock Mirrorkin. If you lose, it returns every October. Title: "Unmasked".
5. **Gearhoot (blueprint).**
   - In the Sunken Library expedition, a hidden archive (revealed at INT ≥ 350) holds the **Brass Blueprint**.
   - Give it to Dr. Pell. From then on the Market sells Gearhoot (2,500G) and the Shrine can make it. Title: "Tinkerer".
6. **Reefclaw (tide pool).**
   - Buy the **Tide Pool** ranch upgrade.
   - The next June week 1, a Reefclaw moves in. It is free to adopt (it goes to the Freezer if your ranch is occupied) and is then available at the Shrine and as the Market's summer pick.
7. **Lootlid (strange chest).**
   - In Thornwood Ruins, the Strange Chest node has a 35% chance to be a Lootlid that wants to come home. It is guaranteed on your 3rd visit.
   - It goes to the Freezer and unlocks the breed. Title: "Treasure Hunter".
8. **Aurelwyrm (four crowns).**
   - Rumor from Ines: "Legend says a golden wyrm answers only to champions."
   - Win all four Crowns (any years, any monsters). The Guild presents the **Wyrm Scale**; offer it at the Shrine to unlock Aurelwyrm.

**Ranch upgrades** (offered by mail every May week 4):

| Upgrade | Price | Requires | Effect |
|---|---|---|---|
| Cozy Barn | 8,000G | Breeder rank 2 | Stress −2 every week |
| Training Yard | 10,000G | Rank 3 | +5 Great weight on drills; unlocks Quarry Haul |
| Tide Pool | 12,000G | Rank 4 | Unlocks Reefclaw; summer stress −1 per week |
| Lantern Garden | 6,000G | First Memorial entry | Visiting the Memorial (free action, once a month) gives stress −5; +5 Heartstone slots |

---

## 12. Secret phrases (special variants)

Store these as hashes of the normalized phrase. A secret variant gets a unique palette, a small bonus and its own Encyclopedia entry. If its breed is still locked, the phrase becomes a Sleeping Stone like any other.

| Phrase | Variant | Bonus |
|---|---|---|
| wildsong | Songheart Puddlepup (rainbow fins) | +15 all stats; likes every food |
| tunewick | Town Crier Tumblefox (little bell) | INT +20 |
| hello world | Glitch Tumblefox (pixel-glitch palette) | SPD +60, DEF −20 |
| happy birthday | Party Bloatoad (confetti spots) | Stress −10 on every birthday |
| thunderstorm | Stormcrown Nimbusheep (dark cloud wool) | INT +30 |
| teatime | Porcelain Moatshell (blue-and-white china shell) | DEF +30 |
| ember | Bonfire Cinderlynx (bright flames) | POW +25 |
| jade garden | Imperial Coilfang (gold scales) | Lifespan +20 weeks |
| pancakes | Syrup Nibblegrub (amber) | Loves Honey Bread |
| lighthouse | Beacon Wishlume (red-and-white stripes) | Far techniques +5 hit |
| fencing | Champion Quillion (gold cape) | SKI +30 |
| sunrise | Dawnwing Galeheron (peach and rose plumage) | SPD +25 |
| bedrock | Granite Cobblemaw (polished granite) | DEF +30 |
| midnight | Moonlit Velvesper (silver wings) | INT +25 |
| farewell | Lantern-bearer Ashwraith (blue flame) | Wither techniques +5 |
| static | Prism Zipwisp (rainbow sparks) | SKI +25 |
| reflection | Obsidian Mirrorkin (black glass) | INT +25 |
| clockwork | Silver Gearhoot (silver plates) | DEF +20, INT +10 |
| high tide | Abyss Reefclaw (deep-sea blue coral) | DEF +25 |
| treasure | Gilded Lootlid (solid gold) | Prizes +25% (stacks with Gilded) |
| golden hour | Sunsoul Aurelwyrm (white-gold) | All stats +10 |

---

## 13. Odd Jobs (weekly mini-game, free action)

**Turnip Sort:**
- Produce slides down a chute for 30 seconds. Swipe turnips into the left basket and rocks into the right.
- Scoring: +5G per correct item, −5G per wrong one, capped at 150G per week.
- Difficulty ramps up. One play per in-game week.
- **Big buttons, no fail state.**

---

## 14. Titles (achievements)

| Title | How |
|---|---|
| First Ribbon | Win any cup |
| Ascended | Win any Official |
| S-Class Breeder | Win an S Official |
| Crowned | Win a Crown |
| Four Crowns | Win all four Crowns |
| Legend of the Vale | Win the Wildsong Legend |
| Grand Breeder | Reach breeder rank 10 |
| Lineage Keeper | Raise a generation-5 monster |
| Encyclopedist | Own all 30 breeds |
| Collector | Discover 50 variants |
| Gentle Heart | A monster lives ≥ 95% of its nominal lifespan |
| Iron Bond | Win a Crown with loyalty 100 |
| Sleeper Awakened | Wake 10 Sleeping Stones |
| Songbook Scholar | Own all 24 universal Songsheets |
| Sweet Tooth | Feed 100 Stat Sweets |
| Storm Chaser · Silk & Moonlight · Unmasked · Tinkerer · Treasure Hunter | Unlock chains (§11) |

---

## 15. Wren's voice (samples; write the rest in the same tone)

| Moment | Line |
|---|---|
| Weekly, fresh | "{name} is bright-eyed and raring to go!" |
| Weekly, tired | "{name} looks a bit tired. Maybe go easy this week?" |
| Weekly, exhausted | "{name} can barely keep their eyes open. Please let them rest!" |
| Stressed | "{name} seems tense… something's bugging them." |
| Great drill | "Did you SEE that?! {name}, you're amazing!" |
| Cheat | "Hey! {name} only pretended to do that one…" |
| Request: play | "{name} keeps nudging the ball toward you. I think someone wants to play." |
| Prime | "{name} is in their prime! This is the time to push." |
| Past prime | "{name}'s growing older… they won't improve as fast from here." |
| 25% life left | "{name} is getting on in years. Let's make every week count." |
| 10 weeks left | "I don't think {name} has much time left. Let's make it a peaceful few weeks." |
| Breakdown | "{name} ran off! We found them at the creek… I think we pushed too hard." |
| Learned from a Songsheet | "{name} hummed the tune twice… and now knows {technique}!" |
| Ate a Stat Sweet | "Mmm! {name} looks stronger already." |
| Farewell | "Thank you for everything, {name}. We'll take good care of your Heartstone." |
