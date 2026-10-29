# Concept reference prompts for ChatGPT (for Art 2.0: the Blender monsters)

**What this is for.** You generate 2–3 concept images per breed in ChatGPT. They are **reference only**: Claude Code looks at them while rebuilding each monster's rig, parts, proportions and shading in V3. They never ship in the game and never get traced or imported. They simply get your taste into the monsters.

**How to do it (per breed):**
1. Start a **new ChatGPT conversation** for each breed (so the creature stays consistent within it).
2. Paste the **Style Guide** below, then that breed's **Creature** paragraph, then the **Image 1** request. Generate.
3. In the same conversation, paste **Image 2**, generate; then **Image 3** (optional but valuable for battles), generate.
4. If an image looks like a famous character (a well-known cartoon fox, dragon, electric mouse…), reply "Make it more original; change the silhouette and markings" and regenerate.
5. Save each image into your project folder: `Monster Rancher/concept/<breed-id>/sheet.png`, `expressions.png`, `action.png` (breed ids are in the headings below). Claude Code will add `concept/` to `.gitignore` so these stay on your PC and out of the public repo.

Do the breeds in any order. Even 10 breeds done before V3 starts is a big help; Claude Code can work breed by breed as you add more.

---

## Style Guide (paste first in every conversation)

```
You are making original concept art for "Wildsong Ranch", a cozy monster-raising game whose monsters are cel-shaded 3D characters. Style: clean cel-shaded character art with a slight anime touch: soft two-tone shading, a warm rim light, outlines in a darker tint of each colour (not black), big glossy expressive eyes with white highlights, rounded chunky appealing shapes with a slightly big head, and a clear readable silhouette. Warm, friendly storybook feel. Not realistic, not pixel art. Plain white background, no text, no logos, no watermark. The creature must be an original design: do not base it on, or make it resemble, any character from Pokémon, Digimon, Monster Rancher, Dragon Quest, Yo-kai Watch or any other franchise, and avoid their signature silhouettes. Use exactly the hex colours I give. I will ask for several images of the same creature in this conversation: keep its design identical across all of them.
```

## Image requests (paste after the Creature paragraph, one at a time)

```
Image 1 (character sheet): one wide image showing this exact creature three times in a row, evenly spaced, standing in a relaxed neutral pose: front view, side view facing left, and back view. Same size, same colours, same proportions. White background.
```

```
Image 2 (expression sheet): one image with eight close-up heads of this exact creature in two rows of four, each labelled only by its pose (no text): neutral; happy; tired with droopy eyes; stressed with a sweat drop; angry; sleepy with closed eyes; sick with a slight green tint; sparkle-eyed and delighted. Same head design and colours in every cell.
```

```
Image 3 (action): one image with two poses of this exact creature side by side: on the left a dynamic battle pose mid-attack, [ATTACK]; on the right a hit reaction, knocked back with a squashed body, eyes shut, a few small impact stars. Side view, white background, no effects clutter beyond the attack itself.
```

Replace `[ATTACK]` with the breed's attack line given below.

---

## The 30 creatures

### 1. puddlepup · Puddlepup
**Creature:** A small, round, stubby quadruped: a puppy-like amphibian. Floppy fin-shaped ears, webbed paws, a wide happy grin, a flat tadpole-like tail. Cheerful and eager. Body #3FB6A8 teal, belly #F3E6C4 cream, accent (fins, tail edge) #F28FA8 pink, eyes #24323A.
**[ATTACK]:** leaping forward belly-first for a big splashy belly flop, water droplets flying.

### 2. tumblefox · Tumblefox
**Creature:** A small quick fox with an oversized curled tail bigger than its body, tall pointed ears, a dark mask band across the eyes and dark socks on all four paws. Clever and playful. Body #D9733B orange, belly and tail tip #F7F1E8 cream, mask and socks #3B3240 dark plum, eyes #2A1E22.
**[ATTACK]:** mid-pounce with a trail of small pale blue foxfire wisps around its tail.

### 3. cobblemaw · Cobblemaw
**Creature:** A bulky bear-like quadruped made of cobblestone plates over its shoulders and back with tufts of moss, a wide cave-like jaw with two short stubby tusks, small deep-set eyes. Slow, heavy, grumpy but gentle. Body #6E7486 grey-blue stone, belly #8E94A4 lighter stone, moss accents #7FAF5A green, eyes #F2B544 amber.
**[ATTACK]:** rearing up to slam both front paws down, cracking the ground, small rocks bouncing.

### 4. moatshell · Moatshell
**Creature:** A tortoise whose shell is a tiny stone castle keep with crenellations, arrow slits and a small pennant flag on top; stubby pillar legs; sleepy, wise eyes. Patient and immovable. Shell and skin #C9A66B sandstone, belly #E8D4A8, flag #3AA6A1 teal, brick details #9A5B3C, eyes #2B2B2B.
**[ATTACK]:** tucked low and braced as a flight of tiny pinecone "catapult" shots launches from the castle top.

### 5. wishlume · Wishlume
**Creature:** A floating paper sky-lantern creature. Its body is a soft glowing paper lantern with a warm flame heart visible through the paper, two stubby paper arms, a dangling tassel tail, and simple eyes painted on the paper. Gentle and dreamy. Paper #F6E3B4, inner glow #FFB85C, ribs and tassel #D94F4F red, eyes #3A2A2A.
**[ATTACK]:** glowing brightly and projecting a warm beam of light forward from its heart.

### 6. quillion · Quillion
**Creature:** A small upright hedgehog fencer: a crest of back quills, one long silver tail-quill held like a rapier, a short crimson cape, a proud dueling stance. Precise and dashing. Body #8C5A3C chestnut, belly #EED9C4 cream, cape #C0392B crimson, quill blade #C9D3DD silver, eyes #1E1E1E.
**[ATTACK]:** a fencing lunge, tail-quill extended straight forward like a sword, cape flaring.

### 7. cinderlynx · Cinderlynx
**Creature:** A lean feline with ember-tipped ear tufts, a glowing ember pattern along its spine, smoke wisps curling from its paws and an ember tail-tip. No mane, no collar. Fierce and fast. Fur #3A3236 charcoal, belly #5A4E52, embers #FF7A2F orange, eyes #FFD15C gold.
**[ATTACK]:** a raking claw swipe with a crescent of flame following the paw.

### 8. bloatoad · Bloatoad
**Creature:** A huge squat toad with an inflatable throat sac that balloons when happy, lazy half-lidded eyes, warty spots and a few little crown-like bumps on its head. Lazy and sturdy. Skin #7C9A3E olive, belly #F6C49B peach, warts #5E7A2E, eyes #E9C46A.
**[ATTACK]:** throat sac fully inflated, shooting its long tongue forward.

### 9. coilfang · Coilfang
**Creature:** A jade serpent coiled in an S-shape with a feathered golden crest on its head, two neat fangs and a diamond scale pattern down its back. Elegant and sharp. Scales #2FA37A jade, belly #DDF2D3 pale, crest #E8C14E gold, eyes #1B3A2B.
**[ATTACK]:** striking forward with open jaws, body uncoiling like a spring.

### 10. nimbusheep · Nimbusheep
**Creature:** A sheep whose wool is a soft raincloud that drizzles a little, with curled cream horns; a tiny rainbow appears over it when happy. No electricity, no lightning. Calm and sweet. Cloud wool #E9EEF6, face and legs #8C97AD grey-blue, rainbow accent (#F28F8F, #F7D36B, #8FD1A8, #8FB8F2), eyes #2E3440.
**[ATTACK]:** head lowered, a small downpour bursting from its wool toward the target.

### 11. galeheron · Galeheron
**Creature:** A tall long-legged heron with a dagger beak, streaming crest plumes and wind-swirl markings on its wings. Swift and graceful. Feathers #6FB7E9 sky blue, belly #F5F8FC white, swirl markings #2F5D8A deep blue, eyes and beak #F2C14E gold.
**[ATTACK]:** wings spread wide, beak thrust forward, a spiral of wind around it.

### 12. nibblegrub · Nibblegrub
**Creature:** A chubby five-segment larva with tiny legs, big round cheeks always chewing, stubby antenna nubs. Hungry and content. Body #F2D27A yellow, belly #FFF0C2, segment lines #D9A94F, cheeks #F29C8F pink, eyes #3B2F2F.
**[ATTACK]:** curled into a ball and rolling forward like a wheel.

### 13. velvesper · Velvesper
**Creature:** A velvet moth with dusk-coloured wings bearing crescent-moon markings and two soft eyespots, feathery antennae, a small fuzzy body. Mysterious and gentle. Wings #5B3F7A plum, body #EDE3F5 pale lavender, eyespots #F29E4C and #F7E7B5, eyes #1B1424.
**[ATTACK]:** wings flared, scattering a cloud of glittering dusk-coloured dust forward.

### 14. ashwraith · Ashwraith
**Creature:** A tattered ash-grey floating shroud with no visible body, two small ember-orange eyes, smoke-like wisps trailing below, and two tiny hands peeking out. Eerie but cute. Shroud #A7A3A0, lighter folds #CFCAC6, eyes and inner embers #FF6B3D.
**[ATTACK]:** both tiny hands raised, a ghostly flame lash curling forward.

### 15. zipwisp · Zipwisp
**Creature:** A small fizzing ball of cyan static with two stubby spark-shaped wings and a zigzag tail, always jittering; a simple face, nothing like any famous electric mascot. Hyper and giggly. Body #6EF2FF cyan, core #FFFFFF, sparks #FFE14D yellow, eyes #0E2A40.
**[ATTACK]:** darting forward with a crackling arc of lightning jumping ahead of it.

### 16. mirrorkin · Mirrorkin
**Creature:** A living ornate hand-mirror floating upright; its handle is its tail; its face appears inside the glass; a gilded frame, a ribbon cloak, and two little floating gloved hands. Sly and theatrical. Glass #CFD8E3, highlights #EEF3F8, frame #C9A04A gold, cloak #6C5CE7 violet, eyes #2B2B33.
**[ATTACK]:** tilting to catch light and firing a reflected beam from its glass.

### 17. gearhoot · Gearhoot
**Creature:** A clockwork owl of brass plates; one eye is a big monocle lens and the other is normal; wing feathers are little gears; a wind-up key turns on its back. Precise and polite. Brass #C9A04A, lighter plates #E9D7A6, copper details #B86B3C, lens glow #5CC9C0, eyes #F7F3E3.
**[ATTACK]:** wings open showing spinning gears, firing a tight bright bolt from its monocle lens.

### 18. reefclaw · Reefclaw
**Creature:** A coral-pink crab knight standing upright: one oversized branching coral claw and one small claw, barnacle shoulder armour, visored eye-stalks. Steadfast and brave. Shell #F07C6E coral, belly #FFD9CF, armour highlights #BDE7E0 pale aqua, shell shadows #B85B4E, eyes #1F2A44.
**[ATTACK]:** big coral claw swung in a wide arc with a spray of seawater.

### 19. lootlid · Lootlid
**Creature:** A wooden treasure chest on stubby legs; its lid is its mouth with a long tongue and glinting coins inside; a keyhole "nose". Greedy and goofy. Wood #9C6B3F, lighter wood #C99A6B, gold trim and coins #F2C94C, tongue #E86A7C, eyes #2B1B10.
**[ATTACK]:** lid flung wide, a shower of gold coins bursting out toward the target.

### 20. aurelwyrm · Aurelwyrm
**Creature:** A golden serpentine dragon that floats without wings; long crimson ribbon fins along its body, small branching antlers and whiskers. Regal and calm. Scales #F2C14E gold, belly #FFF4D6, ribbon fins #D64545 crimson, eyes #6B2D0F.
**[ATTACK]:** rearing up, mouth open, breathing a stream of golden sunfire.

### 21. hearthwing · Hearthwing (two forms)
**Creature:** A stocky dragon in two life stages. YOUNG: a round stubby dragonet with tiny flappy wings, a short snout, nub horns and a faint glow in its chest. GROWN: a broad-winged dragon with a long neck and swept-back copper horns; the scales of its chest part like a fireplace grate to show a molten glow; ember-edged wing membranes; a spade-tipped tail. Warm and loyal. Scales #1F6F6A deep teal, belly #E9D8B4 cream, embers and chest glow #FF8A3D, horns #B87333 copper, eyes #FFD166.
**Image 1 note:** show the GROWN form in the three views, and add the YOUNG form standing beside it at the right, smaller.
**[ATTACK]:** grown form, wings spread, breathing a wide cone of fire from its open jaws.

### 22. grumblestone · Grumblestone
**Creature:** A hulking hunched boulder giant on two short thick legs; cracked granite shell with violet crystals glowing through the cracks like a geode; heavy stone-ledge eyebrows over small grumpy eyes; pillar arms with crystal knuckles. Grumpy but dependable. Stone #7A7068, lighter stone #9C938A, crystals #9B5DE5 violet, eyes #F5E663.
**[ATTACK]:** both crystal fists raised overhead for a ground-cracking smash.

### 23. pluckrex · Pluckrex (two forms)
**Creature:** A brave little two-legged dinosaur in two life stages. YOUNG: a big head, a wide toothy grin, stubby arms, a thick short tail, and a fan-shaped head crest that glows gold. GROWN: taller and sturdier, a bigger crest, stone-plated forearm bracers, a tougher scalier hide. Plucky underdog energy. Hide #4F6D8F slate blue, belly #F1E6CF cream, crest and glow #F7C548 gold, eyes #2B2D42.
**Image 1 note:** show the GROWN form in the three views, with the YOUNG form standing beside it at the right, smaller.
**[ATTACK]:** grown form charging forward head-first, crest blazing gold.

### 24. paladove · Paladove (two forms)
**Creature:** A stout dove in two life stages (bird, not humanoid). YOUNG: a fluffy round dove chick with a tiny feather crest and a small gold ring floating above its head. GROWN: a stately dove-knight with white-and-gold chest armour, four broad wings, a glowing ring halo, and a round feather-emblem shield on one wing. Serene and protective. Feathers #F7F4EE, highlights #FFFFFF, gold armour and halo #E3B448, eyes #4A6FA5.
**Image 1 note:** show the GROWN form in the three views, with the YOUNG form beside it at the right, smaller.
**[ATTACK]:** grown form, four wings spread, halo blazing, releasing a beam of dawn light.

### 25. starhowl · Starhowl
**Creature:** A midnight-indigo wolf whose fur is speckled with tiny twinkling constellations; a flowing aurora mane shading from teal to rose; a star-cluster pattern across its brow; glowing pale eyes; a bushy star-tipped tail. Wild and noble. Fur #2B2F6B indigo, lighter fur #4C5199, aurora mane #6EE7C8 to #F49AC1, eyes #E8F1FF.
**[ATTACK]:** mid-leap with jaws open, a trail of falling-star sparkles behind it.

### 26. petalphant · Petalphant
**Creature:** A round sage-green elephant calf with huge blush-pink ears shaped like magnolia petals, a flower bud at the tip of its trunk that opens when happy, a leafy tail tuft and chubby legs. Gentle and nurturing. Skin #8FB996 sage, belly #DCEFD9, petal ears and bud #F4A7B9 pink, eyes #3B3B3B.
**[ATTACK]:** trunk raised, bud open, sneezing out a swirl of seeds and petals.

### 27. scrollopus · Scrollopus
**Creature:** A plump violet octopus wearing round spectacles and a small tasselled scholar's cap; each tentacle curls around a scroll, a quill or a book; ink-spot freckles. Bookish and sly. Skin #7D5BA6 violet, underside #CDB4E6, cap #3A3A55 with tassel #F2C94C, ink spots #2E2A4F, eyes #1E1E2E.
**[ATTACK]:** several tentacles raised, squirting a dark cloud of ink forward.

### 28. gloomgrin · Gloomgrin
**Creature:** A squat two-legged gargoyle imp with charcoal-stone skin, faint violet rune lines, stubby horns, small bat wings and a curled tail; a wide cheeky grin of square teeth; amber eyes. Crouches like a rooftop statue when idle. Mischievous. Stone #4B4F58, lighter stone #6B7079, runes #8E7CC3 violet, eyes #FFB347 amber.
**[ATTACK]:** dropping from above, claws out, wings tucked, grin wide.

### 29. rammerjack · Rammerjack
**Creature:** A stocky cream-and-chestnut mountain goat with huge spiral horns wrapped in rope bands, a shaggy beard, a red knitted scarf, sturdy hooves and determined eyebrows. Stubborn and brave. Fur #EFE6D2 cream, lighter fur #FFF8EA, horns and patches #A0522D chestnut, scarf #D1495B red, eyes #3A2E26.
**[ATTACK]:** head down in a full battering charge, scarf streaming behind.

### 30. frostlance · Frostlance
**Creature:** A pale blue-white narwhal that swims through the air leaving a trail of snowflakes; a long spiral tusk of clear ice; frost-edged fins; a deep-teal back with snowflake freckles. Cool and precise. Body #D8EEF7, underside #F5FBFE, back #1F7A8C teal, tusk #BDE8F5 icy, eyes #1B263B.
**[ATTACK]:** tusk pointed forward in a spiralling ice-lance thrust, frost crystals forming along it.

---

## Checklist before saving an image
- It's clearly **our** creature (matches the hex colours and the described features) and not recognisable as a franchise character.
- The three views in Image 1 are the same size and design.
- Nothing extra: no text, no logo, no busy background.
- Saved as `concept/<breed-id>/sheet.png`, `expressions.png`, `action.png`.
