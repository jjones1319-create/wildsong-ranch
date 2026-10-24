# Ten new monsters (batch 2)

Breeds 21–30, added after M2 at the owner's request: a real winged dragon, a rock giant, a brave little dino hero, a holy winged guardian, and six more.

This file is the source for that change. Once the monsters are added, `docs/CONTENT.md` holds them like every other breed, and this file can stay as a record.

> **Originality rule** (same as `CLAUDE.md`): these are original creatures.
> - Do not make them resemble characters from Monster Rancher, Digimon, Pokémon or any other franchise.
> - If a drawing starts to look like a famous character, change it until it doesn't.
> - The names below were checked against the existing roster and technique list; keep them.

**Target device:** the owner plays on a **Samsung Galaxy S25 Ultra or newer** (Android, Chrome). Richer art and animation are welcome, but the game must still run on other modern phones (fewer effects if needed).

---

## 1. The ten

Same columns as CONTENT §2. Stats are listed LIF / POW / INT / SKI / SPD / DEF, and grades use the same order.

| # | Breed | Niche | Start | Growth | Life (wks) | Guts | Lean | Base stats | Grades | Bonus drill | Strength | Common | Trait |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 21 | **Hearthwing** | Late-blooming dragon powerhouse (grows up at Prime) | Shrine | Late | 400 | 14 | Both | 130/120/90/60/60/100 | B A C D D C | Plow Pull | 8 | 3 | Dragonheart |
| 22 | **Grumblestone** | Unmovable crystal tank | Shrine | Late | 460 | 14 | POW | 160/110/40/40/20/140 | B B E E E A | Waterfall Stand | 7 | 7 | Unshakable |
| 23 | **Pluckrex** | Brave rookie hero (grows up at Prime) | Market (always) | Early | 360 | 12 | POW | 110/100/50/90/80/80 | C B D C C C | Log Toss | 7 | 9 | Underdog |
| 24 | **Paladove** | Holy guardian healer (grows up at Prime) | Shrine | Evergreen | 420 | 12 | INT | 130/50/110/80/70/110 | B E B C D B | Moon Meditation | 6 | 6 | Blessed |
| 25 | **Starhowl** | Swift night hunter | Shrine | Steady | 360 | 11 | Mixed | 90/110/70/100/130/50 | D B C C A E | Wind Chase | 6 | 7 | Moonlit |
| 26 | **Petalphant** | Blooming support tank | Shrine | Late | 480 | 13 | INT | 180/80/90/50/40/80 | A C B D E C | Hill Sprints | 5 | 7 | Green Thumb |
| 27 | **Scrollopus** | Inky trickster scholar | Shrine | Steady | 380 | 11 | INT | 90/40/140/110/70/60 | D E A B C D | Puzzle Stones | 5 | 6 | Eight Arms |
| 28 | **Gloomgrin** | Stone-skinned counter-puncher | Shrine | Steady | 380 | 12 | POW | 100/110/60/100/50/120 | C B D B E B | Target Toss | 6 | 6 | Statue Pose |
| 29 | **Rammerjack** | Charging brawler | Shrine | Early | 340 | 12 | POW | 110/130/40/70/110/70 | C A E D B C | Plow Pull | 7 | 8 | Battering Ram |
| 30 | **Frostlance** | Icy precision lancer | Shrine | Evergreen | 400 | 12 | Mixed | 100/90/90/130/70/70 | C C C A D D | Target Toss | 6 | 6 | Chill |

**Notes:**
- All ten are available from the start: none is locked, so the owner can play with them right away.
- Pluckrex joins the always-stocked Market starters, making 4.
- **Hearthwing** is the strongest of the batch, balanced by a late peak, slow guts regeneration and its rarity at the Shrine (commonness 3).

---

## 2. New traits

These are battle traits. Add the data and descriptions now; the effects are implemented with the battle engine in **M4**. Add them to M4's checklist in `BUILD_PLAN.md`.

| Trait | Effect |
|---|---|
| Dragonheart | Once per battle, when its HP first drops below 50%, it gains 20 guts |
| Unshakable | Can't be pushed back or stunned; damage taken −20% |
| Underdog | +8 hit and +10% damage against opponents with a higher stat total |
| Blessed | Regenerates 1% of max HP every 5 seconds in battle |
| Moonlit | Crit chance +6% |
| Green Thumb | Heal and drain techniques restore twice as much |
| Eight Arms | Multi-hit techniques get one extra hit |
| Statue Pose | After standing still for 2 seconds, takes 50% less damage until it moves |
| Battering Ram | Dashing costs no guts, and the first technique after a dash deals +15% damage |
| Chill | Its hits slow the target's walking by 25% for 3 seconds |

---

## 3. Art briefs

Each brief gives the body plan · the look · palette (body / belly / accent / eye) · the **accent part** (what it adds as a sub-breed) · the **sub adjective**.

21. **Hearthwing**
    - **Quadruped dragon with two forms** (§5).
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

## 4. Techniques (90)

Same format and rules as CONTENT §3. The values were generated inside the GAME_DESIGN §10.2 family bands. Each new breed also gets breed Songsheets for its non-Basic techniques (CONTENT §3 prices).

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
| Pebble Punch | Basic | POW | 1 Close | 10 | 14 | +7 | 6 | 5 | 24 | — | Starter |
| Grumble Shove | Basic | POW | 2 Near | 10 | 12 | +7 | 7 | 8 | 24 | knockback | Starter · sub-quirk |
| Knuckle Knock | Hit | POW | 1 Close | 17 | 15 | +15 | 7 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Geode Smash | Heavy | POW | 1 Close | 45 | 64 | -12 | 13 | 12 | 39 | — | Iron Quarry: POW ≥ 360 |
| Gravel Grind | Wither | POW | 2 Near | 28 | 15 | +1 | 46 | 8 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Crystal Jab | Sharp | POW | 2 Near | 27 | 26 | +1 | 10 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Rockfall Ruckus | Special | POW | 3 Mid | 49 | 12 | +2 | 18 | 12 | 36 | 3 hits | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Amethyst Avalanche | Chain | POW | 1 Close | 51 | 84 | -9 | 16 | 15 | 42 | — | Iron Quarry: Geode Smash Lv3 + POW ≥ 520 |
| Crystal Heart Quake | Signature | POW | 2 Near | 54 | 30 | +4 | 50 | 18 | 42 | stun 45 ticks | Pure breed: auto at Prime (loyalty ≥ 60) |

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
| Halo Spark | Basic | INT | 3 Mid | 11 | 12 | +5 | 7 | 8 | 24 | — | Starter · sub-quirk |
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
| Night Nip | Basic | POW | 1 Close | 11 | 12 | +4 | 7 | 5 | 24 | — | Starter |
| Twinkle Yip | Basic | INT | 3 Mid | 11 | 11 | +7 | 7 | 8 | 24 | — | Starter · sub-quirk |
| Moonleap Strike | Hit | POW | 2 Near | 16 | 16 | +17 | 8 | 7 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Eclipse Maul | Heavy | POW | 1 Close | 48 | 56 | -10 | 12 | 9 | 39 | — | Iron Quarry: POW ≥ 360 |
| Northwind Wail | Wither | INT | 3 Mid | 28 | 15 | +1 | 38 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Comet Fang | Sharp | POW | 2 Near | 28 | 29 | -1 | 10 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Falling Star Volley | Special | INT | 4 Far | 47 | 10 | -4 | 18 | 12 | 36 | 3 hits | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Supernova Fang | Chain | POW | 2 Near | 34 | 38 | +2 | 12 | 31 | 33 | — | Windrun Steppe: Comet Fang Lv3 + POW ≥ 520 |
| Constellation Hunt | Signature | INT | 3 Mid | 54 | 15 | +6 | 25 | 30 | 42 | 4 hits | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Petalphant

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Trunk Bop | Basic | POW | 1 Close | 14 | 13 | +6 | 6 | 8 | 24 | — | Starter |
| Seed Sneeze | Basic | INT | 3 Mid | 11 | 11 | +7 | 7 | 6 | 24 | — | Starter · sub-quirk |
| Ear Flap Slap | Hit | POW | 2 Near | 17 | 18 | +16 | 8 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Stomp of Spring | Heavy | POW | 1 Close | 46 | 58 | -9 | 13 | 8 | 39 | — | Iron Quarry: POW ≥ 360 |
| Sleepy Blossom | Wither | INT | 3 Mid | 28 | 15 | +1 | 40 | 7 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Thorn Whirl | Sharp | INT | 2 Near | 26 | 24 | +1 | 11 | 31 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Rainwater Bath | Special | INT | 3 Mid | 49 | 0 | +1 | 0 | 0 | 36 | heal 25% max HP | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Seed Storm Sneeze | Chain | INT | 3 Mid | 19 | 19 | +10 | 8 | 9 | 27 | — | Archer's Glade: Seed Sneeze Lv3 + INT ≥ 520 |
| Full Bloom | Signature | INT | 1 Close | 56 | 52 | +6 | 26 | 18 | 42 | drain 60% of dmg | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Scrollopus

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tentacle Swat | Basic | POW | 2 Near | 13 | 11 | +7 | 7 | 5 | 24 | — | Starter |
| Ink Flick | Basic | INT | 3 Mid | 12 | 13 | +4 | 5 | 5 | 24 | — | Starter · sub-quirk |
| Footnote Dart | Hit | INT | 3 Mid | 18 | 18 | +15 | 9 | 10 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Tome Tsunami | Heavy | INT | 4 Far | 48 | 60 | -12 | 13 | 8 | 39 | — | Iron Quarry: INT ≥ 360 |
| Ink Cloud | Wither | INT | 2 Near | 27 | 16 | +2 | 48 | 5 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Quill Scribble | Sharp | INT | 3 Mid | 29 | 24 | -1 | 9 | 28 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Eightfold Lecture | Special | INT | 4 Far | 47 | 8 | -2 | 19 | 11 | 36 | 4 hits | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Bibliography Barrage | Chain | INT | 3 Mid | 24 | 9 | +18 | 11 | 13 | 30 | 3 hits | Archer's Glade: Footnote Dart Lv3 + INT ≥ 520 |
| Inksteal Riddle | Signature | INT | 2 Near | 57 | 24 | +6 | 50 | 17 | 42 | steal guts = wither | Pure breed: auto at Prime (loyalty ≥ 60) |

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
| Horn Bonk | Basic | POW | 1 Close | 11 | 12 | +7 | 7 | 8 | 24 | — | Starter |
| Hoof Stamp | Basic | POW | 2 Near | 11 | 11 | +4 | 7 | 8 | 24 | — | Starter · sub-quirk |
| Brow Bump | Hit | POW | 2 Near | 18 | 18 | +17 | 8 | 7 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Battering Charge | Heavy | POW | 1 Close | 44 | 59 | -7 | 13 | 10 | 39 | dash to Close after | Iron Quarry: POW ≥ 360 |
| Bleat Blast | Wither | POW | 3 Mid | 25 | 15 | +0 | 41 | 5 | 30 | — | Starfall Observatory: POW+INT ≥ 480 |
| Spiral Horn Hook | Sharp | POW | 2 Near | 27 | 27 | +0 | 10 | 30 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Avalanche Charge | Special | POW | 3 Mid | 47 | 40 | -2 | 19 | 10 | 36 | knockback | Glacier Bastion: DEF+POW ≥ 820 · grade B+ |
| Twin Horn Bash | Chain | POW | 1 Close | 19 | 21 | +10 | 8 | 11 | 27 | — | Archer's Glade: Horn Bonk Lv3 + POW ≥ 520 |
| Mountain Ram | Signature | POW | 2 Near | 53 | 64 | +4 | 23 | 18 | 42 | miss: self-dmg 10% max HP | Pure breed: auto at Prime (loyalty ≥ 60) |

#### Frostlance

| Technique | Family | Type | Range | Guts | Force | Hit | Wither | Sharp | Anim | Effect | How it's learned |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tusk Poke | Basic | POW | 1 Close | 14 | 12 | +4 | 5 | 6 | 24 | — | Starter |
| Snowflake Puff | Basic | INT | 3 Mid | 12 | 13 | +4 | 7 | 5 | 24 | — | Starter · sub-quirk |
| Icicle Thrust | Hit | POW | 2 Near | 19 | 17 | +17 | 7 | 8 | 27 | — | Archer's Glade: SKI ≥ 220 |
| Blizzard Lance | Heavy | INT | 4 Far | 46 | 50 | -12 | 13 | 10 | 39 | — | Iron Quarry: INT ≥ 360 |
| Frostbite Breeze | Wither | INT | 3 Mid | 27 | 14 | +3 | 42 | 7 | 30 | — | Starfall Observatory: INT ≥ 280 |
| Glacier Pierce | Sharp | POW | 2 Near | 27 | 26 | +0 | 10 | 29 | 30 | — | Windrun Steppe: SPD+SKI ≥ 520 |
| Northern Lights | Special | INT | 4 Far | 48 | 0 | -2 | 30 | 0 | 36 | heal 15% max HP | Glacier Bastion: DEF+INT ≥ 820 · grade B+ |
| Crystal Lance Rush | Chain | POW | 2 Near | 25 | 22 | +20 | 8 | 11 | 30 | — | Archer's Glade: Icicle Thrust Lv3 + POW ≥ 520 |
| Polar Spiral | Signature | POW | 2 Near | 54 | 16 | +3 | 23 | 30 | 42 | 3 hits | Pure breed: auto at Prime (loyalty ≥ 60) |

---

## 5. Growth forms (new art rule)

- **Hearthwing**, **Pluckrex** and **Paladove** have two looks: **young** for life stages 1–4, and **grown** from stage 5 (Prime) onward. The others have one look, as before.
- The switch happens the week the monster enters Prime, with a short, skippable "grow up" moment: a glow, then the new form, and a Wren line such as "{name} has grown up!".
- In data, add an optional `grown` look to the breed's art. It holds the same kind of fields as the base look, and anything it leaves out falls back to the base look.
- **Mixes:** the **main** breed's forms apply. The sub-breed's palette and accent part are used on both forms.
- Size by life stage still applies (young looks at 70–85%, grown at 100%).
- **Monster Lab:**
  - Moving a monster's age across Prime in the editor switches the preview.
  - The Presets show pure babies in young form, and the trained presets (which are at Prime) in grown form.
- Saves don't change: the form is derived from the life stage, never stored.

## 6. Art polish for high-end phones (applies to all 30 monsters)

- **Keep the procedural SVG system and its palettes** so every main/sub mix (now 30 × 30 = 900) still recolors automatically. Don't switch to Blender, pre-rendered images or 3D in this task.
- **Richer shading:**
  - A soft gradient on every body part (light from the top-left), plus a rim highlight.
  - A soft contact shadow under the monster.
  - Optional subtle texture patterns per breed: scales, fur strokes, stone grain, feathers.
- **More life:**
  - Secondary motion: ears, tails, wings, manes and tentacles lag slightly behind the body.
  - Squash-and-stretch on hops.
  - The eyes glance toward where the player taps.
- **Signature particles** in a lightweight layer, turned off under reduced motion:

| Monster | Particles |
|---|---|
| Hearthwing | Embers |
| Grumblestone | Crystal glints |
| Paladove | Light motes |
| Starhowl | Twinkles |
| Petalphant | Drifting petals |
| Scrollopus | Ink bubbles |
| Gloomgrin | Dust puffs |
| Frostlance | Snowflakes |
| Existing breeds | One fitting effect each where it suits (rain for Nimbusheep, sparks for Zipwisp, steam for Gearhoot, …) |

- **Performance budget:**
  - A steady 60 fps on a Galaxy S25 Ultra-class phone with the ranch scene, two animated monsters and particles.
  - Library and picker thumbnails stay static.
  - On weaker phones, or when the frame rate drops, reduce the particles automatically.

## 7. Implementation checklist

1. **Docs:**
   - Add breeds 21–30 to `docs/CONTENT.md`: the §2 table, the traits in §2.1, the art briefs in §2.2, and the technique tables in §3.
   - Update the counts everywhere they appear in CONTENT and GAME_DESIGN: **30 breeds**, **270 breed techniques + 24 universal = 294**, **900 mixes**.
   - Add the growth-forms rule (§5) to GAME_DESIGN §22.
2. **Data** (`src/data`):
   - Add the new breed ids, trait ids, breeds, traits, techniques (including their breed Songsheets), drills references, and art looks with the grown forms.
   - The CONTENT ↔ data sync tests must pass.
3. **Art** (`src/art/monster`):
   - New parts: big dragon wings, swept horns, chest-grate glow, geode cracks and crystals, fan crest, halo ring, four-wing armor, aurora mane, constellation speckles, petal ears and trunk bud, eight tentacles, spectacles and cap, bat wings, rune lines, spiral horns and scarf, ice tusk.
   - Then the §6 polish for all 30 breeds.
4. **Tests:**
   - Counts and ids updated.
   - Every new breed has techniques in at least 3 ranges.
   - New technique values sit inside the §10.2 bands (the existing pinned outlier list must not grow), and technique names are unique.
   - Render tests: every new breed at every size stage and expression, both forms where there are two, and a sample of mixes with every existing breed.
   - The **Shrine snapshot** test will change because the commonness weights changed. That's expected before launch; update it deliberately and note it in PROGRESS.md.
   - Presets: now **30 pure babies + 120 trained presets**.
5. **Market:** Pluckrex is always stocked.
6. **M4:** add the 10 new traits' battle effects to M4's checklist in `BUILD_PLAN.md`.
7. **Visual QA:**
   - Render PNG contact sheets with the existing review tool: each new monster young and grown, every expression, and 3 mixes each.
   - Look at them yourself.
   - Fix anything off-model or unappealing, and change any design that resembles a character from another franchise.
8. **Finish:** bump the version (minor), run `npm run verify`, update PROGRESS.md, commit `M2.5: ten new monsters`, push, and confirm the deploy.

## 8. Try this on your phone

1. Monster Lab → **Presets**: the ten new monsters are there.
2. Edit a Hearthwing, Pluckrex or Paladove and slide its age past Prime. It grows into its grown form.
3. Make a few mixes, e.g. Pluckrex with a Starhowl sub-breed, or Grumblestone with a Frostlance sub-breed.
4. Check that animations and particles look smooth, and that Settings → reduce motion turns them off.
