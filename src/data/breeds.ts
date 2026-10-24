import type { Breed, BreedId, Grade, Grades, StatKey, Stats } from './types.ts'

/** CONTENT §2 breeds. Stats and grades are listed LIF / POW / INT / SKI / SPD / DEF. */

const stats = (LIF: number, POW: number, INT: number, SKI: number, SPD: number, DEF: number): Stats => ({ LIF, POW, INT, SKI, SPD, DEF })
const grades = (LIF: Grade, POW: Grade, INT: Grade, SKI: Grade, SPD: Grade, DEF: Grade): Grades => ({ LIF, POW, INT, SKI, SPD, DEF })

export const BREEDS: readonly Breed[] = [
  {
    id: 'puddlepup', name: 'Puddlepup', niche: 'Balanced starter', availability: 'market', marketSeason: null, unlockChain: null,
    growth: 'Steady', lifespan: 380, gutsRate: 12, lean: 'Mixed', base: stats(120, 70, 60, 80, 70, 70), grades: grades('C', 'C', 'D', 'B', 'C', 'C'),
    bonusDrill: 'target-toss', strength: 7, commonness: 10, trait: 'cheerful',
    art: { plan: 'quadruped', brief: 'A stubby, round puppy-like amphibian with floppy fin-shaped ears, webbed paws, a wide happy grin and a tadpole-ish flat tail.', palette: { body: '#3FB6A8', belly: '#F3E6C4', accent: '#F28FA8', eye: '#24323A' }, accentPart: 'floppy fin-ears', adjective: 'Puddle' },
  },
  {
    id: 'tumblefox', name: 'Tumblefox', niche: 'Quick trickster starter', availability: 'market', marketSeason: null, unlockChain: null,
    growth: 'Early', lifespan: 360, gutsRate: 11, lean: 'INT', base: stats(90, 60, 80, 80, 100, 50), grades: grades('D', 'D', 'C', 'B', 'B', 'D'),
    bonusDrill: 'dodge-the-gourds', strength: 6, commonness: 10, trait: 'nimble',
    art: { plan: 'quadruped', brief: 'A small fox with an oversized curled tail bigger than its body, tall pointed ears, a dark mask band across the eyes and dark socks.', palette: { body: '#D9733B', belly: '#F7F1E8', accent: '#3B3240', eye: '#2A1E22' }, accentPart: 'curled tail', adjective: 'Tumble' },
  },
  {
    id: 'cobblemaw', name: 'Cobblemaw', niche: 'Slow heavy bruiser', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Late', lifespan: 420, gutsRate: 13, lean: 'POW', base: stats(140, 120, 30, 40, 30, 110), grades: grades('B', 'A', 'E', 'D', 'E', 'B'),
    bonusDrill: 'log-toss', strength: 8, commonness: 8, trait: 'heavy-hitter',
    art: { plan: 'quadruped', brief: 'A bulky bear-like beast with cobblestone plates over shoulders and back, tufts of moss, a wide cave-like jaw with two short stubby tusks and small deep-set eyes.', palette: { body: '#6E7486', belly: '#8E94A4', accent: '#7FAF5A', eye: '#F2B544' }, accentPart: 'stone shoulder plates', adjective: 'Cobble' },
  },
  {
    id: 'moatshell', name: 'Moatshell', niche: 'Fortress wall', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Evergreen', lifespan: 440, gutsRate: 14, lean: 'POW', base: stats(130, 70, 50, 50, 30, 150), grades: grades('B', 'C', 'D', 'D', 'E', 'A'),
    bonusDrill: 'acorn-shower', strength: 7, commonness: 8, trait: 'fortified',
    art: { plan: 'shelled', brief: 'A tortoise whose shell is a tiny castle keep with crenellations, arrow slits and a pennant flag on top; stubby pillar legs and sleepy wise eyes.', palette: { body: '#C9A66B', belly: '#E8D4A8', accent: '#3AA6A1', eye: '#2B2B2B' }, accentPart: 'crenellated rim', adjective: 'Bastion' },
  },
  {
    id: 'wishlume', name: 'Wishlume', niche: 'Frail INT caster', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Early', lifespan: 320, gutsRate: 11, lean: 'INT', base: stats(70, 30, 130, 80, 90, 40), grades: grades('E', 'E', 'A', 'C', 'B', 'E'),
    bonusDrill: 'puzzle-stones', strength: 6, commonness: 8, trait: 'glow',
    art: { plan: 'floater', brief: 'A paper sky-lantern creature whose warm flame heart glows through its paper body; two stubby paper arms, a dangling tassel tail and eyes painted on the paper.', palette: { body: '#F6E3B4', belly: '#FFF2D6', accent: '#D94F4F', eye: '#3A2A2A' }, accentPart: 'tassel tail', adjective: 'Lantern' },
  },
  {
    id: 'quillion', name: 'Quillion', niche: 'Fast skill duelist', availability: 'market', marketSeason: null, unlockChain: null,
    growth: 'Steady', lifespan: 360, gutsRate: 11, lean: 'POW', base: stats(90, 90, 50, 120, 100, 60), grades: grades('D', 'C', 'D', 'A', 'B', 'D'),
    bonusDrill: 'target-toss', strength: 6, commonness: 9, trait: 'en-garde',
    art: { plan: 'biped', brief: 'A small chestnut hedgehog fencer with a crest of back quills, one long silver tail-quill held like a blade and a short crimson cape, in an upright dueling stance.', palette: { body: '#8C5A3C', belly: '#EED9C4', accent: '#C0392B', eye: '#1E1E1E' }, accentPart: 'back quills', adjective: 'Quilled' },
  },
  {
    id: 'cinderlynx', name: 'Cinderlynx', niche: 'Power glass cannon', availability: 'market', marketSeason: 'Autumn', unlockChain: null,
    growth: 'Steady', lifespan: 340, gutsRate: 12, lean: 'POW', base: stats(90, 130, 50, 70, 110, 40), grades: grades('D', 'A', 'D', 'C', 'B', 'E'),
    bonusDrill: 'plow-pull', strength: 6, commonness: 7, trait: 'hot-blooded',
    art: { plan: 'quadruped', brief: 'A lean feline with ember-tipped ear tufts, a glowing ember pattern along the spine, smoke wisps curling from its paws and an ember tail-tip. No collar or mane.', palette: { body: '#3A3236', belly: '#5A4E52', accent: '#FF7A2F', eye: '#FFD15C' }, accentPart: 'ember ear tufts', adjective: 'Cinder' },
  },
  {
    id: 'bloatoad', name: 'Bloatoad', niche: 'HP sponge', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Late', lifespan: 450, gutsRate: 13, lean: 'POW', base: stats(190, 100, 50, 50, 40, 60), grades: grades('A', 'B', 'D', 'D', 'D', 'E'),
    bonusDrill: 'hill-sprints', strength: 5, commonness: 8, trait: 'big-appetite',
    art: { plan: 'blob', brief: 'A huge squat toad with an inflatable throat sac that balloons when happy, lazy half-lidded eyes, warty spots and little crown-like bumps on its head.', palette: { body: '#7C9A3E', belly: '#F6C49B', accent: '#5E7A2E', eye: '#E9C46A' }, accentPart: 'throat sac', adjective: 'Bog' },
  },
  {
    id: 'coilfang', name: 'Coilfang', niche: 'Short-lived prodigy', availability: 'market', marketSeason: 'Spring', unlockChain: null,
    growth: 'Early', lifespan: 300, gutsRate: 11, lean: 'POW', base: stats(90, 110, 40, 110, 90, 70), grades: grades('C', 'B', 'E', 'B', 'C', 'C'),
    bonusDrill: 'wind-chase', strength: 7, commonness: 7, trait: 'quick-study',
    art: { plan: 'serpent', brief: 'A jade S-coil serpent with a feathered golden crest, two neat fangs and a diamond scale pattern down its back.', palette: { body: '#2FA37A', belly: '#DDF2D3', accent: '#E8C14E', eye: '#1B3A2B' }, accentPart: 'feathered crest', adjective: 'Jade' },
  },
  {
    id: 'nimbusheep', name: 'Nimbusheep', niche: 'Long-lived late bloomer', availability: 'market', marketSeason: 'Winter', unlockChain: null,
    growth: 'Late', lifespan: 480, gutsRate: 12, lean: 'INT', base: stats(140, 40, 100, 60, 50, 90), grades: grades('B', 'E', 'B', 'C', 'D', 'C'),
    bonusDrill: 'moon-meditation', strength: 5, commonness: 7, trait: 'fluffy',
    art: { plan: 'quadruped', brief: 'A sheep whose wool is a soft raincloud that occasionally drizzles, with curled cream horns; a tiny rainbow appears over it when it is happy. No electricity.', palette: { body: '#E9EEF6', belly: '#8C97AD', accent: '#F28F8F', eye: '#2E3440' }, accentPart: 'cloud-wool tufts', adjective: 'Nimbus' },
  },
  {
    id: 'galeheron', name: 'Galeheron', niche: 'Fast INT striker', availability: 'market', marketSeason: 'Summer', unlockChain: null,
    growth: 'Steady', lifespan: 360, gutsRate: 11, lean: 'INT', base: stats(80, 50, 100, 100, 120, 40), grades: grades('D', 'D', 'B', 'B', 'A', 'E'),
    bonusDrill: 'wind-chase', strength: 6, commonness: 7, trait: 'tailwind',
    art: { plan: 'avian', brief: 'A tall long-legged heron with a dagger beak, streaming crest plumes and wind-swirl markings on its wings.', palette: { body: '#6FB7E9', belly: '#F5F8FC', accent: '#2F5D8A', eye: '#F2C14E' }, accentPart: 'crest plumes', adjective: 'Gale' },
  },
  {
    id: 'nibblegrub', name: 'Nibblegrub', niche: 'Metamorph tank', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Steady', lifespan: 400, gutsRate: 13, lean: 'POW', base: stats(160, 90, 50, 50, 30, 90), grades: grades('A', 'C', 'D', 'D', 'E', 'C'),
    bonusDrill: 'hill-sprints', strength: 4, commonness: 9, trait: 'hungry-grub',
    art: { plan: 'insect', brief: 'A chubby five-segment larva with tiny legs, big round cheeks always chewing and stubby antenna nubs.', palette: { body: '#F2D27A', belly: '#FFF0C2', accent: '#D9A94F', eye: '#3B2F2F' }, accentPart: 'antenna nubs', adjective: 'Grub' },
  },
  {
    id: 'velvesper', name: 'Velvesper', niche: 'Swift INT (metamorph form)', availability: 'locked', marketSeason: null, unlockChain: 'cocoon',
    growth: 'Evergreen', lifespan: 380, gutsRate: 11, lean: 'INT', base: stats(80, 40, 140, 100, 130, 40), grades: grades('D', 'E', 'A', 'B', 'A', 'E'),
    bonusDrill: 'moon-meditation', strength: 5, commonness: 2, trait: 'moth-dust',
    art: { plan: 'insect', brief: 'A moth with velvet dusk-colored wings bearing crescent-moon markings and two soft eyespots, and feathery antennae.', palette: { body: '#5B3F7A', belly: '#EDE3F5', accent: '#F29E4C', eye: '#1B1424' }, accentPart: 'feathery antennae', adjective: 'Dusk' },
  },
  {
    id: 'ashwraith', name: 'Ashwraith', niche: 'Death-born guts engine', availability: 'locked', marketSeason: null, unlockChain: 'vigil',
    growth: 'Early', lifespan: 340, gutsRate: 10, lean: 'INT', base: stats(60, 30, 150, 120, 120, 50), grades: grades('E', 'E', 'A', 'B', 'B', 'D'),
    bonusDrill: 'puzzle-stones', strength: 4, commonness: 2, trait: 'ethereal',
    art: { plan: 'floater', brief: 'A tattered ash-grey shroud with no visible body, two ember eyes, wisps trailing like smoke and tiny hands peeking out.', palette: { body: '#A7A3A0', belly: '#CFCAC6', accent: '#FF6B3D', eye: '#FF6B3D' }, accentPart: 'trailing wisps', adjective: 'Ashen' },
  },
  {
    id: 'zipwisp', name: 'Zipwisp', niche: 'Guts-engine harasser', availability: 'locked', marketSeason: null, unlockChain: 'storm-chase',
    growth: 'Early', lifespan: 340, gutsRate: 10, lean: 'INT', base: stats(70, 40, 90, 120, 150, 50), grades: grades('D', 'E', 'C', 'B', 'A', 'D'),
    bonusDrill: 'dodge-the-gourds', strength: 3, commonness: 2, trait: 'live-wire',
    art: { plan: 'floater', brief: 'A small fizzing ball of cyan static with two stubby spark-wings and a zigzag tail, always jittering, with a simple face unlike any existing electric mascot.', palette: { body: '#6EF2FF', belly: '#FFFFFF', accent: '#FFE14D', eye: '#0E2A40' }, accentPart: 'zigzag tail', adjective: 'Zappy' },
  },
  {
    id: 'mirrorkin', name: 'Mirrorkin', niche: 'Trickster / guts drainer', availability: 'locked', marketSeason: null, unlockChain: 'masquerade',
    growth: 'Steady', lifespan: 360, gutsRate: 11, lean: 'INT', base: stats(80, 50, 140, 110, 80, 60), grades: grades('D', 'D', 'A', 'B', 'C', 'D'),
    bonusDrill: 'puzzle-stones', strength: 4, commonness: 2, trait: 'reflective',
    art: { plan: 'floater', brief: 'A living vertical hand-mirror with an ornate gilded frame whose handle is its tail; its face appears in the glass, with a ribbon cloak and two little floating gloved hands.', palette: { body: '#CFD8E3', belly: '#EEF3F8', accent: '#6C5CE7', eye: '#2B2B33' }, accentPart: 'ribbon cloak', adjective: 'Mirror' },
  },
  {
    id: 'gearhoot', name: 'Gearhoot', niche: 'Construct all-rounder', availability: 'locked', marketSeason: null, unlockChain: 'blueprint',
    growth: 'Evergreen', lifespan: 420, gutsRate: 12, lean: 'INT', base: stats(90, 70, 120, 110, 60, 120), grades: grades('D', 'D', 'B', 'B', 'D', 'B'),
    bonusDrill: 'acorn-shower', strength: 5, commonness: 2, trait: 'clockwork',
    art: { plan: 'construct', brief: 'A clockwork owl of brass plates; one eye is a big monocle lens, its wing feathers are little gears and a wind-up key turns on its back.', palette: { body: '#C9A04A', belly: '#E9D7A6', accent: '#5CC9C0', eye: '#F7F3E3' }, accentPart: 'gear wings', adjective: 'Brass' },
  },
  {
    id: 'reefclaw', name: 'Reefclaw', niche: 'Long-prime armored knight', availability: 'locked', marketSeason: null, unlockChain: 'tide-pool',
    growth: 'Evergreen', lifespan: 400, gutsRate: 13, lean: 'POW', base: stats(110, 120, 40, 90, 60, 140), grades: grades('C', 'B', 'E', 'C', 'D', 'B'),
    bonusDrill: 'waterfall-stand', strength: 6, commonness: 2, trait: 'hard-shell',
    art: { plan: 'shelled', brief: 'A coral-pink crab knight with one oversized branching coral claw and one small claw, barnacle shoulder armor and visored eye-stalks.', palette: { body: '#F07C6E', belly: '#FFD9CF', accent: '#BDE7E0', eye: '#1F2A44' }, accentPart: 'coral claw', adjective: 'Coral' },
  },
  {
    id: 'lootlid', name: 'Lootlid', niche: 'Challenge / joke breed', availability: 'locked', marketSeason: null, unlockChain: 'strange-chest',
    growth: 'Steady', lifespan: 300, gutsRate: 13, lean: 'Mixed', base: stats(110, 80, 80, 60, 40, 170), grades: grades('C', 'D', 'D', 'D', 'E', 'A'),
    bonusDrill: 'acorn-shower', strength: 2, commonness: 1, trait: 'gilded',
    art: { plan: 'construct', brief: 'A treasure-chest creature on stubby legs; the lid is its mouth, with a long tongue and coins glinting inside, and a keyhole nose.', palette: { body: '#9C6B3F', belly: '#C99A6B', accent: '#F2C94C', eye: '#2B1B10' }, accentPart: 'gold-trim lid', adjective: 'Gilded' },
  },
  {
    id: 'aurelwyrm', name: 'Aurelwyrm', niche: 'Elite dual-threat', availability: 'locked', marketSeason: null, unlockChain: 'four-crowns',
    growth: 'Early', lifespan: 280, gutsRate: 14, lean: 'Both', base: stats(130, 150, 150, 90, 90, 110), grades: grades('B', 'A', 'A', 'C', 'C', 'C'),
    bonusDrill: 'plow-pull', strength: 9, commonness: 1, trait: 'regal',
    art: { plan: 'serpent', brief: 'A golden serpentine dragon with long crimson ribbon fins, small branching antlers and whiskers, floating without wings.', palette: { body: '#F2C14E', belly: '#FFF4D6', accent: '#D64545', eye: '#6B2D0F' }, accentPart: 'ribbon fins', adjective: 'Golden' },
  },
  // Breeds 21–30 (docs/NEW_MONSTERS.md, batch 2). None is locked.
  {
    id: 'hearthwing', name: 'Hearthwing', niche: 'Late-blooming dragon powerhouse (grows up at Prime)', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Late', lifespan: 400, gutsRate: 14, lean: 'Both', base: stats(130, 120, 90, 60, 60, 100), grades: grades('B', 'A', 'C', 'D', 'D', 'C'),
    bonusDrill: 'plow-pull', strength: 8, commonness: 3, trait: 'dragonheart',
    art: {
      plan: 'quadruped',
      brief: 'Young: a round, stubby dragonet with tiny flappy wings, a short snout, nub horns and a faint glow in its chest.',
      palette: { body: '#1F6F6A', belly: '#E9D8B4', accent: '#FF8A3D', eye: '#FFD166' },
      accentPart: 'little wings',
      adjective: 'Hearth',
      grown: { brief: 'A broad-winged dragon with a long neck and swept-back copper horns; the scales of its stocky chest part like a fireplace grate to show a molten glow, with ember-edged wing membranes and a spade-tipped tail.' },
    },
  },
  {
    id: 'grumblestone', name: 'Grumblestone', niche: 'Unmovable crystal tank', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Late', lifespan: 460, gutsRate: 14, lean: 'POW', base: stats(160, 110, 40, 40, 20, 140), grades: grades('B', 'B', 'E', 'E', 'E', 'A'),
    bonusDrill: 'waterfall-stand', strength: 7, commonness: 7, trait: 'unshakable',
    art: { plan: 'biped', brief: 'A hulking, hunched boulder giant with a cracked granite shell; violet crystals glow through the cracks like the inside of a geode, with heavy stone-ledge eyebrows over small grumpy eyes, pillar arms with crystal knuckles and short thick legs.', palette: { body: '#7A7068', belly: '#9C938A', accent: '#9B5DE5', eye: '#F5E663' }, accentPart: 'crystal-studded shoulders', adjective: 'Geode' },
  },
  {
    id: 'pluckrex', name: 'Pluckrex', niche: 'Brave rookie hero (grows up at Prime)', availability: 'market', marketSeason: null, unlockChain: null,
    growth: 'Early', lifespan: 360, gutsRate: 12, lean: 'POW', base: stats(110, 100, 50, 90, 80, 80), grades: grades('C', 'B', 'D', 'C', 'C', 'C'),
    bonusDrill: 'log-toss', strength: 7, commonness: 9, trait: 'underdog',
    art: {
      plan: 'biped',
      brief: 'Young: a little dinosaur with a big head, a wide toothy grin, stubby arms and a thick short tail; its fan-shaped head crest glows sunflower-gold when it is fired up.',
      palette: { body: '#4F6D8F', belly: '#F1E6CF', accent: '#F7C548', eye: '#2B2D42' },
      accentPart: 'fan crest',
      adjective: 'Plucky',
      grown: { brief: 'Taller and sturdier, with a bigger crest, stone-plated forearm bracers and a tougher, scalier hide.' },
    },
  },
  {
    id: 'paladove', name: 'Paladove', niche: 'Holy guardian healer (grows up at Prime)', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Evergreen', lifespan: 420, gutsRate: 12, lean: 'INT', base: stats(130, 50, 110, 80, 70, 110), grades: grades('B', 'E', 'B', 'C', 'D', 'B'),
    bonusDrill: 'moon-meditation', strength: 6, commonness: 6, trait: 'blessed',
    art: {
      plan: 'avian',
      brief: 'Young: a fluffy, round dove chick with a tiny feather crest and a little gold ring floating above its head. Not humanoid.',
      palette: { body: '#F7F4EE', belly: '#FFFFFF', accent: '#E3B448', eye: '#4A6FA5' },
      accentPart: 'halo ring',
      adjective: 'Haloed',
      grown: { brief: 'A stately dove-knight in white-and-gold chest armor, with four broad wings, a glowing ring halo, and a round feather-emblem shield on one wing.' },
    },
  },
  {
    id: 'starhowl', name: 'Starhowl', niche: 'Swift night hunter', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Steady', lifespan: 360, gutsRate: 11, lean: 'Mixed', base: stats(90, 110, 70, 100, 130, 50), grades: grades('D', 'B', 'C', 'C', 'A', 'E'),
    bonusDrill: 'wind-chase', strength: 6, commonness: 7, trait: 'moonlit',
    art: { plan: 'quadruped', brief: 'A wolf with midnight-indigo fur speckled with tiny twinkling constellations, a flowing aurora mane (teal shading to rose), a star-cluster pattern across the brow, glowing pale eyes and a bushy star-tipped tail.', palette: { body: '#2B2F6B', belly: '#4C5199', accent: '#6EE7C8', eye: '#E8F1FF' }, accentPart: 'aurora mane', adjective: 'Starry' },
  },
  {
    id: 'petalphant', name: 'Petalphant', niche: 'Blooming support tank', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Late', lifespan: 480, gutsRate: 13, lean: 'INT', base: stats(180, 80, 90, 50, 40, 80), grades: grades('A', 'C', 'B', 'D', 'E', 'C'),
    bonusDrill: 'hill-sprints', strength: 5, commonness: 7, trait: 'green-thumb',
    art: { plan: 'quadruped', brief: 'A round, sage-green elephant calf with huge blush-pink ears shaped like magnolia petals; a flower bud at the tip of its trunk opens when it is happy, with a leafy tail tuft and chubby legs.', palette: { body: '#8FB996', belly: '#DCEFD9', accent: '#F4A7B9', eye: '#3B3B3B' }, accentPart: 'petal ears', adjective: 'Blossom' },
  },
  {
    id: 'scrollopus', name: 'Scrollopus', niche: 'Inky trickster scholar', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Steady', lifespan: 380, gutsRate: 11, lean: 'INT', base: stats(90, 40, 140, 110, 70, 60), grades: grades('D', 'E', 'A', 'B', 'C', 'D'),
    bonusDrill: 'puzzle-stones', strength: 5, commonness: 6, trait: 'eight-arms',
    art: { plan: 'blob', brief: 'A plump violet octopus in round spectacles and a little tasseled scholar’s cap; each tentacle curls around a scroll, a quill or a book, with ink-spot freckles.', palette: { body: '#7D5BA6', belly: '#CDB4E6', accent: '#2E2A4F', eye: '#1E1E2E' }, accentPart: "scholar's cap", adjective: 'Inky' },
  },
  {
    id: 'gloomgrin', name: 'Gloomgrin', niche: 'Stone-skinned counter-puncher', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Steady', lifespan: 380, gutsRate: 12, lean: 'POW', base: stats(100, 110, 60, 100, 50, 120), grades: grades('C', 'B', 'D', 'B', 'E', 'B'),
    bonusDrill: 'target-toss', strength: 6, commonness: 6, trait: 'statue-pose',
    art: { plan: 'biped', brief: 'A squat gargoyle imp with charcoal-stone skin and faint violet rune lines, stubby horns, small bat wings and a curled tail; a wide cheeky grin of square teeth and amber eyes that glow at night. It crouches like a rooftop statue when idle.', palette: { body: '#4B4F58', belly: '#6B7079', accent: '#8E7CC3', eye: '#FFB347' }, accentPart: 'bat wings', adjective: 'Gloomy' },
  },
  {
    id: 'rammerjack', name: 'Rammerjack', niche: 'Charging brawler', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Early', lifespan: 340, gutsRate: 12, lean: 'POW', base: stats(110, 130, 40, 70, 110, 70), grades: grades('C', 'A', 'E', 'D', 'B', 'C'),
    bonusDrill: 'plow-pull', strength: 7, commonness: 8, trait: 'battering-ram',
    art: { plan: 'quadruped', brief: 'A stocky cream-and-chestnut mountain goat with huge spiral horns banded with rope wraps, a shaggy beard, a red knitted scarf, sturdy hooves and determined eyebrows.', palette: { body: '#EFE6D2', belly: '#FFF8EA', accent: '#A0522D', eye: '#3A2E26' }, accentPart: 'spiral horns', adjective: 'Rammy' },
  },
  {
    id: 'frostlance', name: 'Frostlance', niche: 'Icy precision lancer', availability: 'shrine', marketSeason: null, unlockChain: null,
    growth: 'Evergreen', lifespan: 400, gutsRate: 12, lean: 'Mixed', base: stats(100, 90, 90, 130, 70, 70), grades: grades('C', 'C', 'C', 'A', 'D', 'D'),
    bonusDrill: 'target-toss', strength: 6, commonness: 6, trait: 'chill',
    art: { plan: 'floater', brief: 'A pale blue-white narwhal that swims through the air and leaves a trail of snowflakes, with a long spiral tusk of clear ice, frost-edged fins, and a deep-teal back with snowflake freckles.', palette: { body: '#D8EEF7', belly: '#F5FBFE', accent: '#1F7A8C', eye: '#1B263B' }, accentPart: 'ice tusk', adjective: 'Frosty' },
  },
]

export const BREED_BY_ID = Object.fromEntries(BREEDS.map((b) => [b.id, b])) as Record<BreedId, Breed>

export function breedById(id: string): Breed | undefined {
  return (BREED_BY_ID as Record<string, Breed | undefined>)[id]
}

/** Breeds a brand-new game can create (Market starters and Shrine breeds). */
export const STARTING_UNLOCKED: readonly BreedId[] = BREEDS.filter((b) => b.availability !== 'locked').map((b) => b.id)

export function statOrderKey(stat: StatKey): number {
  return ['LIF', 'POW', 'INT', 'SKI', 'SPD', 'DEF'].indexOf(stat)
}
