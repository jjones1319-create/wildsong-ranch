import { elementOf } from './elements.ts'
import type { BreedId, Family, JourneySiteId, Songsheet, StatKey, TechEffect, TechLearn, TechRange, TechType, Technique, TournamentGrade } from './types.ts'

/**
 * CONTENT §3: 270 breed techniques (9 per breed) and 24 universal techniques.
 * Rows are transcribed verbatim from CONTENT.md, including the "How it's learned" text, which is parsed below.
 * Row: [name, family, type, range, guts, force, hit, wither, sharp, anim, effect, learn]
 */
type Row = readonly [string, Family, TechType, TechRange, number, number, number, number, number, number, string, string]

const BREED_ROWS: Record<BreedId, readonly Row[]> = {
  puddlepup: [
    ['Splash Nip', 'Basic', 'POW', 1, 10, 12, 7, 7, 8, 24, '—', 'Starter'],
    ['Bubble Pop', 'Basic', 'INT', 3, 10, 12, 6, 5, 7, 24, '—', 'Starter'],
    ['Frill Flick', 'Hit', 'POW', 2, 20, 14, 19, 9, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Belly Flop', 'Heavy', 'POW', 1, 48, 52, -10, 13, 8, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Soggy Cloud', 'Wither', 'INT', 3, 29, 12, -2, 42, 8, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Slipstream Spin', 'Sharp', 'POW', 2, 25, 22, -4, 9, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Geyser Burst', 'Special', 'INT', 4, 48, 14, -4, 20, 9, 36, '2 hits', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Cannonball Flop', 'Chain', 'POW', 1, 54, 70, -4, 16, 11, 42, '—', 'Iron Quarry: Belly Flop Lv3 + POW ≥ 520'],
    ['Puddle Party', 'Signature', 'INT', 3, 55, 20, 5, 40, 17, 42, 'heal 10% max HP', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  tumblefox: [
    ['Scamper Swipe', 'Basic', 'POW', 1, 13, 12, 7, 6, 5, 24, '—', 'Starter'],
    ['Foxfire Flicker', 'Basic', 'INT', 3, 13, 12, 7, 7, 8, 24, '—', 'Starter'],
    ['Tail Twirl', 'Hit', 'POW', 2, 19, 15, 17, 7, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ["Will-o'-Blaze", 'Heavy', 'INT', 2, 44, 59, -9, 13, 11, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ["Trickster's Hush", 'Wither', 'INT', 3, 26, 15, 2, 42, 6, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Mirage Dart', 'Sharp', 'INT', 4, 27, 26, -3, 11, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Fluffstorm', 'Special', 'INT', 2, 48, 33, 1, 20, 12, 36, 'stun 30 ticks', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Foxfire Volley', 'Chain', 'INT', 3, 21, 20, 7, 8, 11, 27, '—', "Archer's Glade: Foxfire Flicker Lv3 + INT ≥ 520"],
    ['Ninefold Feint', 'Signature', 'INT', 2, 54, 18, 3, 25, 30, 42, '3 hits', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  cobblemaw: [
    ['Gravel Swipe', 'Basic', 'POW', 1, 10, 11, 5, 6, 6, 24, '—', 'Starter'],
    ['Shoulder Check', 'Basic', 'POW', 2, 10, 11, 5, 6, 8, 24, '—', 'Starter'],
    ['Crag Jab', 'Hit', 'POW', 1, 16, 15, 18, 8, 9, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Landslide Maul', 'Heavy', 'POW', 1, 47, 64, -10, 13, 11, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Moss Smother', 'Wither', 'POW', 2, 27, 16, 3, 44, 4, 30, '—', 'Starfall Observatory: POW+INT ≥ 480'],
    ['Fault Line Claw', 'Sharp', 'POW', 2, 26, 24, 0, 10, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Boulder Heave', 'Special', 'POW', 3, 46, 46, -1, 16, 9, 36, 'miss: self-dmg 8% max HP', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Mountainfall', 'Chain', 'POW', 1, 53, 84, -9, 16, 14, 42, '—', 'Iron Quarry: Landslide Maul Lv3 + POW ≥ 520'],
    ['Bedrock Roar', 'Signature', 'POW', 3, 55, 30, 2, 50, 16, 42, 'stun 45 ticks', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  moatshell: [
    ['Shell Bump', 'Basic', 'POW', 1, 14, 13, 5, 5, 7, 24, '—', 'Starter'],
    ['Turret Toss', 'Basic', 'POW', 3, 14, 10, 3, 5, 4, 24, '—', 'Starter'],
    ['Drawbridge Snap', 'Hit', 'POW', 2, 17, 14, 16, 8, 6, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Keep Slam', 'Heavy', 'POW', 1, 44, 64, -6, 12, 8, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Moat Mire', 'Wither', 'POW', 2, 28, 18, 4, 48, 6, 30, '—', 'Starfall Observatory: POW+INT ≥ 480'],
    ['Arrow Slit Shot', 'Sharp', 'POW', 3, 26, 30, 2, 10, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Catapult Barrage', 'Special', 'POW', 4, 48, 13, -2, 19, 10, 36, '3 hits', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Siege Volley', 'Chain', 'POW', 3, 22, 21, 6, 6, 7, 27, '—', "Archer's Glade: Turret Toss Lv3 + POW ≥ 520"],
    ['Hold the Line', 'Signature', 'POW', 1, 54, 0, 5, 30, 16, 42, 'heal 20% max HP', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  wishlume: [
    ['Wishlight Flash', 'Basic', 'INT', 3, 11, 13, 3, 5, 4, 24, '—', 'Starter'],
    ['Paper Flutter', 'Basic', 'INT', 1, 13, 13, 3, 7, 8, 24, '—', 'Starter'],
    ['Glimmer Bolt', 'Hit', 'INT', 4, 16, 13, 14, 8, 7, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Lantern Beam', 'Heavy', 'INT', 4, 44, 50, -12, 11, 9, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Hypno Glow', 'Wither', 'INT', 3, 27, 12, -2, 38, 8, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Prism Needle', 'Sharp', 'INT', 3, 25, 22, -4, 11, 30, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Ember Siphon', 'Special', 'INT', 2, 46, 27, -1, 19, 12, 36, 'drain 50% of dmg', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Starlight Lance', 'Chain', 'INT', 4, 22, 14, 15, 10, 10, 30, '—', "Archer's Glade: Glimmer Bolt Lv3 + INT ≥ 520"],
    ['Festival of Lights', 'Signature', 'INT', 4, 60, 62, 0, 22, 17, 42, '—', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  quillion: [
    ['Quill Poke', 'Basic', 'POW', 1, 11, 12, 7, 6, 6, 24, '—', 'Starter'],
    ['Lunge', 'Basic', 'POW', 2, 14, 10, 8, 7, 5, 24, '—', 'Starter'],
    ['Riposte', 'Hit', 'POW', 2, 19, 14, 19, 7, 7, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Spine Burst', 'Heavy', 'POW', 1, 44, 52, -12, 11, 8, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Bramble Bind', 'Wither', 'POW', 1, 27, 12, -2, 43, 5, 30, '—', 'Starfall Observatory: POW+INT ≥ 480'],
    ['Fleche', 'Sharp', 'POW', 2, 26, 22, -4, 10, 34, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Quill Flurry', 'Special', 'POW', 3, 47, 11, 2, 17, 8, 36, '3 hits', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Grand Riposte', 'Chain', 'POW', 2, 25, 18, 23, 8, 10, 30, '—', "Archer's Glade: Riposte Lv3 + POW ≥ 520"],
    ['Hundred-Quill Waltz', 'Signature', 'POW', 2, 57, 12, 14, 22, 18, 42, '4 hits', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  cinderlynx: [
    ['Ember Swipe', 'Basic', 'POW', 1, 13, 14, 5, 5, 8, 24, '—', 'Starter'],
    ['Spark Pounce', 'Basic', 'POW', 2, 13, 13, 6, 7, 5, 24, '—', 'Starter'],
    ['Cinder Jab', 'Hit', 'POW', 1, 17, 19, 14, 8, 10, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Inferno Maul', 'Heavy', 'POW', 1, 45, 54, -12, 11, 9, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Smoke Veil', 'Wither', 'INT', 3, 25, 12, -2, 44, 5, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Blazing Rake', 'Sharp', 'POW', 2, 29, 22, -4, 11, 31, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Wildfire Rush', 'Special', 'POW', 3, 47, 36, -1, 20, 11, 36, 'dash to Close after', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Flare Fang Flurry', 'Chain', 'POW', 1, 21, 21, 6, 6, 11, 27, '—', "Archer's Glade: Ember Swipe Lv3 + POW ≥ 520"],
    ['Kindled Fury', 'Signature', 'POW', 2, 55, 60, 6, 26, 14, 42, 'miss: self-dmg 10% max HP', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  bloatoad: [
    ['Belly Bounce', 'Basic', 'POW', 1, 11, 10, 3, 6, 7, 24, '—', 'Starter'],
    ['Tongue Lash', 'Basic', 'POW', 2, 10, 11, 3, 6, 6, 24, '—', 'Starter'],
    ['Sticky Tongue', 'Hit', 'POW', 2, 19, 15, 15, 9, 10, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Bog Slam', 'Heavy', 'POW', 1, 44, 53, -8, 13, 11, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Croak Quake', 'Wither', 'POW', 3, 26, 14, 0, 38, 7, 30, '—', 'Starfall Observatory: POW+INT ≥ 480'],
    ['Wart Spitball', 'Sharp', 'POW', 3, 25, 26, -3, 10, 31, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Gulp and Spit', 'Special', 'POW', 1, 50, 29, 2, 19, 9, 36, 'drain 40% of dmg', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Swamp Sumo', 'Chain', 'POW', 1, 50, 70, -5, 16, 14, 42, '—', 'Iron Quarry: Bog Slam Lv3 + POW ≥ 520'],
    ['Balloon Belly', 'Signature', 'POW', 1, 53, 0, 6, 20, 18, 42, 'heal 25% max HP', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  coilfang: [
    ['Coil Squeeze', 'Basic', 'POW', 1, 10, 10, 3, 6, 8, 24, '—', 'Starter'],
    ['Fang Snap', 'Basic', 'POW', 2, 10, 10, 3, 5, 7, 24, '—', 'Starter'],
    ['Jade Strike', 'Hit', 'POW', 2, 20, 14, 14, 9, 6, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Constrictor Crush', 'Heavy', 'POW', 1, 44, 50, -12, 12, 10, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Venom Mist', 'Wither', 'INT', 3, 27, 12, -2, 40, 6, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Crest Cleave', 'Sharp', 'POW', 2, 25, 22, -4, 11, 30, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Serpent Dance', 'Special', 'POW', 3, 48, 16, 1, 28, 12, 36, '2 hits', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Jade Viper Rush', 'Chain', 'POW', 2, 26, 20, 21, 11, 9, 30, '—', "Archer's Glade: Jade Strike Lv3 + POW ≥ 520"],
    ['Emerald Coil', 'Signature', 'POW', 1, 55, 50, 6, 26, 17, 42, 'stun 45 ticks', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  nimbusheep: [
    ['Woolly Bump', 'Basic', 'POW', 2, 11, 12, 3, 7, 8, 24, '—', 'Starter'],
    ['Drizzle Puff', 'Basic', 'INT', 1, 10, 12, 7, 5, 8, 24, '—', 'Starter'],
    ['Hail Tuft', 'Hit', 'INT', 3, 19, 15, 17, 8, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Downpour', 'Heavy', 'INT', 4, 44, 50, -12, 12, 12, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Fog Fleece', 'Wither', 'INT', 2, 26, 12, -2, 45, 8, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Rainbow Arc', 'Sharp', 'INT', 4, 29, 22, -5, 9, 28, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Rain Shelter', 'Special', 'INT', 3, 48, 0, 2, 17, 9, 36, 'heal 20% max HP', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Rainstorm Flock', 'Chain', 'INT', 3, 18, 20, 10, 6, 11, 27, '—', "Archer's Glade: Drizzle Puff Lv3 + INT ≥ 520"],
    ['Cumulonimbus', 'Signature', 'INT', 4, 60, 64, 0, 23, 15, 42, '—', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  galeheron: [
    ['Beak Jab', 'Basic', 'POW', 2, 11, 12, 6, 5, 5, 24, '—', 'Starter'],
    ['Gust Feather', 'Basic', 'INT', 1, 13, 12, 6, 7, 5, 24, '—', 'Starter'],
    ['Wind Spear', 'Hit', 'INT', 3, 18, 17, 18, 9, 6, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Tempest Dive', 'Heavy', 'INT', 4, 44, 60, -6, 12, 12, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Downdraft', 'Wither', 'INT', 3, 28, 18, 4, 41, 8, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Lightning Stride', 'Sharp', 'POW', 2, 25, 30, 2, 10, 31, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Squall Line', 'Special', 'INT', 4, 48, 13, -1, 16, 12, 36, '3 hits', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Gale Lance', 'Chain', 'INT', 3, 24, 24, 21, 11, 9, 30, '—', "Archer's Glade: Wind Spear Lv3 + INT ≥ 520"],
    ['Eye of the Storm', 'Signature', 'INT', 3, 55, 58, 2, 40, 17, 42, 'stun 45 ticks', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  nibblegrub: [
    ['Nibble', 'Basic', 'POW', 1, 14, 13, 5, 5, 5, 24, '—', 'Starter'],
    ['Wriggle Roll', 'Basic', 'POW', 2, 11, 14, 6, 5, 4, 24, '—', 'Starter'],
    ['Chomp', 'Hit', 'POW', 1, 18, 16, 18, 9, 9, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Wobble Crush', 'Heavy', 'POW', 1, 48, 64, -6, 13, 11, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Silk Spray', 'Wither', 'INT', 3, 29, 18, 4, 39, 8, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Mandible Snap', 'Sharp', 'POW', 2, 26, 30, 2, 11, 28, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Cocoon Guard', 'Special', 'POW', 1, 46, 0, -2, 17, 12, 36, 'heal 20% max HP', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Tumbleweed Roll', 'Chain', 'POW', 2, 19, 25, 9, 6, 7, 27, '—', "Archer's Glade: Wriggle Roll Lv3 + POW ≥ 520"],
    ['Big Snack', 'Signature', 'POW', 1, 53, 56, 6, 21, 16, 42, 'drain 60% of dmg', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  velvesper: [
    ['Dust Puff', 'Basic', 'INT', 3, 12, 13, 6, 5, 5, 24, '—', 'Starter'],
    ['Wing Flutter', 'Basic', 'INT', 1, 12, 12, 4, 6, 5, 24, '—', 'Starter'],
    ['Moonbeam Dart', 'Hit', 'INT', 4, 20, 14, 13, 9, 10, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Dusk Nova', 'Heavy', 'INT', 4, 48, 50, -12, 12, 12, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Drowsy Dust', 'Wither', 'INT', 3, 27, 12, -2, 43, 5, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Eyespot Glare', 'Sharp', 'INT', 3, 27, 22, -4, 9, 29, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Moonlit Waltz', 'Special', 'INT', 2, 47, 30, 2, 30, 12, 36, 'heal 15% max HP', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Crescent Volley', 'Chain', 'INT', 4, 26, 17, 14, 11, 13, 30, '—', "Archer's Glade: Moonbeam Dart Lv3 + INT ≥ 520"],
    ['Twilight Veil', 'Signature', 'INT', 3, 57, 43, 4, 55, 30, 42, '—', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  ashwraith: [
    ['Ember Touch', 'Basic', 'INT', 1, 10, 11, 4, 6, 7, 24, '—', 'Starter'],
    ['Ash Flurry', 'Basic', 'INT', 3, 14, 11, 4, 7, 7, 24, '—', 'Starter'],
    ['Wisp Lash', 'Hit', 'INT', 3, 19, 14, 14, 7, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Pyre Bloom', 'Heavy', 'INT', 4, 48, 50, -12, 12, 9, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Mournful Wail', 'Wither', 'INT', 2, 27, 12, -2, 44, 8, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Ghostflame Dart', 'Sharp', 'INT', 4, 29, 22, -5, 11, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Soulsiphon', 'Special', 'INT', 3, 47, 27, 0, 17, 10, 36, 'drain 50% of dmg', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Phantom Lashes', 'Chain', 'INT', 3, 25, 19, 19, 8, 11, 30, '—', "Archer's Glade: Wisp Lash Lv3 + INT ≥ 520"],
    ['Last Ember', 'Signature', 'INT', 2, 56, 60, 3, 22, 15, 42, 'miss: self-dmg 12% max HP', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  zipwisp: [
    ['Zip Bump', 'Basic', 'POW', 2, 14, 11, 7, 7, 5, 24, '—', 'Starter'],
    ['Crackle', 'Basic', 'INT', 1, 12, 13, 3, 5, 6, 24, '—', 'Starter'],
    ['Arc Flick', 'Hit', 'INT', 3, 18, 15, 15, 7, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Overcharge', 'Heavy', 'INT', 2, 44, 50, -12, 12, 12, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Static Field', 'Wither', 'INT', 4, 27, 12, -2, 43, 5, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Zigzag Bolt', 'Sharp', 'INT', 3, 25, 22, -4, 10, 28, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Chain Spark', 'Special', 'INT', 4, 49, 11, -1, 19, 8, 36, '3 hits', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Crackle Storm', 'Chain', 'INT', 3, 20, 20, 6, 6, 9, 27, '—', "Archer's Glade: Crackle Lv3 + INT ≥ 520"],
    ['Ball Lightning Dance', 'Signature', 'INT', 2, 54, 13, 6, 36, 17, 42, '4 hits', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  mirrorkin: [
    ['Glint', 'Basic', 'INT', 1, 12, 11, 5, 7, 8, 24, '—', 'Starter'],
    ['Shard Toss', 'Basic', 'INT', 3, 13, 11, 4, 5, 7, 24, '—', 'Starter'],
    ['Reflection Ray', 'Hit', 'INT', 3, 19, 18, 17, 9, 9, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Shatterburst', 'Heavy', 'INT', 4, 45, 60, -11, 13, 10, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Mocking Image', 'Wither', 'INT', 2, 25, 16, 3, 48, 5, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Prism Cut', 'Sharp', 'INT', 3, 27, 27, -1, 10, 30, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Steal the Spotlight', 'Special', 'INT', 2, 49, 16, 0, 34, 12, 36, 'steal guts = wither', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Infinite Corridor', 'Chain', 'INT', 3, 25, 23, 20, 11, 12, 30, '—', "Archer's Glade: Reflection Ray Lv3 + INT ≥ 520"],
    ['Looking-Glass Swap', 'Signature', 'INT', 2, 54, 24, 5, 50, 15, 42, 'steal guts = wither', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  gearhoot: [
    ['Talon Tick', 'Basic', 'POW', 2, 11, 13, 7, 7, 8, 24, '—', 'Starter'],
    ['Lens Flash', 'Basic', 'INT', 1, 11, 13, 7, 6, 8, 24, '—', 'Starter'],
    ['Calibrated Shot', 'Hit', 'INT', 3, 17, 18, 20, 8, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Overclock Cannon', 'Heavy', 'INT', 4, 45, 64, -6, 11, 8, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Gear Grind', 'Wither', 'INT', 2, 26, 18, 4, 46, 4, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Precision Bolt', 'Sharp', 'INT', 4, 25, 30, 2, 10, 31, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Spring Repair', 'Special', 'INT', 3, 49, 0, 2, 16, 11, 36, 'heal 25% max HP', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Clockwork Barrage', 'Chain', 'INT', 3, 23, 9, 23, 10, 11, 30, '3 hits', "Archer's Glade: Calibrated Shot Lv3 + INT ≥ 520"],
    ['Midnight Chime', 'Signature', 'INT', 3, 53, 29, 3, 55, 18, 42, 'stun 45 ticks', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  reefclaw: [
    ['Pincer Pinch', 'Basic', 'POW', 1, 14, 10, 3, 5, 4, 24, '—', 'Starter'],
    ['Shell Shove', 'Basic', 'POW', 2, 11, 10, 3, 5, 7, 24, 'knockback', 'Starter'],
    ['Coral Jab', 'Hit', 'POW', 2, 16, 15, 15, 7, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Tidebreaker Clamp', 'Heavy', 'POW', 1, 47, 62, -9, 12, 11, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Barnacle Spray', 'Wither', 'POW', 3, 26, 15, 1, 43, 4, 30, '—', 'Starfall Observatory: POW+INT ≥ 480'],
    ['Sideways Slash', 'Sharp', 'POW', 2, 28, 24, -3, 11, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Riptide Hold', 'Special', 'POW', 1, 49, 30, 0, 18, 9, 36, 'stun 40 ticks', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Reef Lance', 'Chain', 'POW', 2, 22, 22, 17, 8, 11, 30, '—', "Archer's Glade: Coral Jab Lv3 + POW ≥ 520"],
    ['Kingtide', 'Signature', 'POW', 2, 53, 58, 2, 27, 15, 42, 'knockback', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  lootlid: [
    ['Lid Chomp', 'Basic', 'POW', 1, 13, 14, 8, 7, 5, 24, '—', 'Starter'],
    ['Coin Toss', 'Basic', 'INT', 2, 13, 14, 8, 5, 4, 24, '—', 'Starter'],
    ['Tongue Grab', 'Hit', 'POW', 1, 18, 19, 20, 8, 10, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Treasure Slam', 'Heavy', 'POW', 1, 47, 64, -6, 11, 10, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ["Fool's Gold Glare", 'Wither', 'INT', 3, 26, 14, 1, 38, 5, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Hinge Snap', 'Sharp', 'POW', 2, 28, 30, 2, 10, 30, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Jackpot!', 'Special', 'INT', 3, 48, 35, -2, 16, 11, 36, 'random: x2 dmg / heal 20% / fizzle', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Gold Rain', 'Chain', 'INT', 2, 21, 9, 8, 6, 7, 27, '3 hits', "Archer's Glade: Coin Toss Lv3 + INT ≥ 520"],
    ['Hoard Avalanche', 'Signature', 'POW', 2, 56, 72, 3, 23, 16, 42, 'miss: self-dmg 12% max HP', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  aurelwyrm: [
    ['Gilded Claw', 'Basic', 'POW', 1, 10, 11, 5, 7, 6, 24, '—', 'Starter'],
    ['Sun Spark', 'Basic', 'INT', 3, 12, 11, 5, 7, 5, 24, '—', 'Starter'],
    ['Ribbon Lash', 'Hit', 'POW', 2, 17, 19, 20, 7, 9, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Sovereign Crush', 'Heavy', 'POW', 1, 46, 64, -6, 12, 12, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ["Dragon's Glare", 'Wither', 'INT', 3, 29, 14, 3, 39, 4, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Crown Horn Thrust', 'Sharp', 'POW', 2, 25, 30, 2, 9, 30, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Solar Flare Breath', 'Special', 'INT', 4, 49, 56, -1, 22, 8, 36, '—', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Sunfire Volley', 'Chain', 'INT', 3, 20, 25, 6, 8, 8, 27, '—', "Archer's Glade: Sun Spark Lv3 + INT ≥ 520"],
    ["Heaven's Ribbon", 'Signature', 'INT', 4, 60, 66, 2, 21, 17, 42, '—', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  hearthwing: [
    ['Talon Rake', 'Basic', 'POW', 1, 11, 13, 4, 7, 7, 24, '—', 'Starter'],
    ['Cinder Cough', 'Basic', 'INT', 3, 11, 10, 7, 5, 5, 24, '—', 'Starter'],
    ['Wingbeat Jab', 'Hit', 'POW', 2, 19, 15, 15, 8, 6, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Furnace Crush', 'Heavy', 'POW', 1, 45, 53, -11, 11, 9, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Smoulder Smoke', 'Wither', 'INT', 3, 27, 14, 2, 37, 6, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Horn Hook', 'Sharp', 'POW', 2, 29, 27, -3, 11, 29, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Bellows Blaze', 'Special', 'INT', 4, 48, 11, 0, 17, 8, 36, '3 hits', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Cinder Gust', 'Chain', 'INT', 3, 19, 19, 10, 6, 8, 27, '—', "Archer's Glade: Cinder Cough Lv3 + INT ≥ 520"],
    ['Hearthfire Torrent', 'Signature', 'INT', 4, 60, 64, 0, 25, 15, 42, '—', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  grumblestone: [
    ['Pebble Punch', 'Basic', 'POW', 1, 10, 11, 4, 6, 5, 24, '—', 'Starter'],
    ['Grumble Shove', 'Basic', 'POW', 2, 10, 11, 4, 7, 8, 24, 'knockback', 'Starter'],
    ['Knuckle Knock', 'Hit', 'POW', 1, 17, 15, 15, 7, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Geode Smash', 'Heavy', 'POW', 1, 45, 64, -6, 13, 12, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Gravel Grind', 'Wither', 'POW', 2, 28, 18, 4, 46, 8, 30, '—', 'Starfall Observatory: POW+INT ≥ 480'],
    ['Crystal Jab', 'Sharp', 'POW', 2, 27, 30, 2, 10, 28, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Rockfall Ruckus', 'Special', 'POW', 3, 49, 13, 2, 18, 12, 36, '3 hits', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Amethyst Avalanche', 'Chain', 'POW', 1, 51, 94, -9, 16, 15, 42, '—', 'Iron Quarry: Geode Smash Lv3 + POW ≥ 520'],
    ['Crystal Heart Quake', 'Signature', 'POW', 2, 54, 34, 4, 50, 18, 42, 'stun 45 ticks', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  pluckrex: [
    ['Snap Bite', 'Basic', 'POW', 1, 11, 11, 6, 6, 5, 24, '—', 'Starter'],
    ['Tail Thump', 'Basic', 'POW', 2, 12, 10, 7, 7, 5, 24, '—', 'Starter'],
    ['Plucky Jab', 'Hit', 'POW', 2, 18, 15, 18, 8, 9, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Courage Crash', 'Heavy', 'POW', 1, 44, 54, -11, 11, 8, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Crest Flare', 'Wither', 'INT', 3, 28, 14, 1, 43, 7, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Rising Claw', 'Sharp', 'POW', 2, 25, 24, -1, 10, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Stampede Rush', 'Special', 'POW', 3, 50, 42, 0, 17, 8, 36, 'dash to Close after', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ["Hero's Combo", 'Chain', 'POW', 2, 24, 20, 17, 10, 12, 30, '—', "Archer's Glade: Plucky Jab Lv3 + POW ≥ 520"],
    ['Sunrise Roar', 'Signature', 'INT', 4, 56, 30, 4, 40, 16, 42, 'stun 30 ticks', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  paladove: [
    ['Wing Buffet', 'Basic', 'POW', 2, 14, 10, 3, 6, 8, 24, '—', 'Starter'],
    ['Halo Spark', 'Basic', 'INT', 1, 11, 10, 3, 7, 8, 24, '—', 'Starter'],
    ['Lightfeather Dart', 'Hit', 'INT', 3, 16, 14, 14, 9, 10, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Dawnbreak Beam', 'Heavy', 'INT', 4, 47, 50, -12, 13, 9, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Lull of Peace', 'Wither', 'INT', 2, 27, 15, 1, 40, 4, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Gleaming Quill', 'Sharp', 'INT', 4, 27, 23, -2, 10, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Mending Hymn', 'Special', 'INT', 3, 46, 0, -1, 0, 0, 36, 'heal 25% max HP', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Featherlight Volley', 'Chain', 'INT', 3, 22, 7, 21, 11, 13, 30, '3 hits', "Archer's Glade: Lightfeather Dart Lv3 + INT ≥ 520"],
    ['Sanctuary Wings', 'Signature', 'INT', 2, 53, 0, 3, 40, 14, 42, 'heal 15% max HP', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  starhowl: [
    ['Night Nip', 'Basic', 'POW', 1, 11, 10, 3, 7, 5, 24, '—', 'Starter'],
    ['Twinkle Yip', 'Basic', 'INT', 3, 11, 10, 3, 7, 8, 24, '—', 'Starter'],
    ['Moonleap Strike', 'Hit', 'POW', 2, 16, 14, 14, 8, 7, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Eclipse Maul', 'Heavy', 'POW', 1, 48, 56, -10, 12, 9, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Northwind Wail', 'Wither', 'INT', 3, 28, 15, 1, 38, 5, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Comet Fang', 'Sharp', 'POW', 2, 28, 29, -1, 10, 28, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Falling Star Volley', 'Special', 'INT', 4, 47, 10, -4, 18, 12, 36, '3 hits', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Supernova Fang', 'Chain', 'POW', 2, 34, 38, 2, 12, 31, 33, '—', 'Windrun Steppe: Comet Fang Lv3 + POW ≥ 520'],
    ['Constellation Hunt', 'Signature', 'INT', 3, 54, 15, 6, 25, 30, 42, '4 hits', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  petalphant: [
    ['Trunk Bop', 'Basic', 'POW', 2, 14, 12, 6, 6, 8, 24, '—', 'Starter'],
    ['Seed Sneeze', 'Basic', 'INT', 1, 11, 12, 6, 7, 6, 24, '—', 'Starter'],
    ['Ear Flap Slap', 'Hit', 'POW', 2, 17, 18, 19, 8, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Stomp of Spring', 'Heavy', 'POW', 1, 46, 64, -6, 13, 8, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Sleepy Blossom', 'Wither', 'INT', 3, 28, 18, 4, 40, 7, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Thorn Whirl', 'Sharp', 'INT', 2, 26, 30, 2, 11, 31, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Rainwater Bath', 'Special', 'INT', 3, 49, 0, 1, 0, 0, 36, 'heal 25% max HP', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Seed Storm Sneeze', 'Chain', 'INT', 3, 19, 21, 10, 8, 9, 27, '—', "Archer's Glade: Seed Sneeze Lv3 + INT ≥ 520"],
    ['Full Bloom', 'Signature', 'INT', 1, 56, 58, 6, 26, 18, 42, 'drain 60% of dmg', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  scrollopus: [
    ['Tentacle Swat', 'Basic', 'POW', 2, 13, 12, 6, 7, 5, 24, '—', 'Starter'],
    ['Ink Flick', 'Basic', 'INT', 1, 12, 12, 6, 5, 5, 24, '—', 'Starter'],
    ['Footnote Dart', 'Hit', 'INT', 3, 18, 17, 18, 9, 10, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Tome Tsunami', 'Heavy', 'INT', 4, 48, 60, -6, 13, 8, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Ink Cloud', 'Wither', 'INT', 2, 27, 18, 4, 48, 5, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Quill Scribble', 'Sharp', 'INT', 3, 29, 30, 2, 9, 28, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Eightfold Lecture', 'Special', 'INT', 4, 47, 9, -2, 19, 11, 36, '4 hits', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Bibliography Barrage', 'Chain', 'INT', 3, 24, 10, 18, 11, 13, 30, '3 hits', "Archer's Glade: Footnote Dart Lv3 + INT ≥ 520"],
    ['Inksteal Riddle', 'Signature', 'INT', 2, 57, 27, 6, 50, 17, 42, 'steal guts = wither', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  gloomgrin: [
    ['Grin Bite', 'Basic', 'POW', 1, 13, 14, 8, 6, 6, 24, '—', 'Starter'],
    ['Wing Slap', 'Basic', 'POW', 2, 14, 14, 8, 7, 7, 24, '—', 'Starter'],
    ['Sneaky Jab', 'Hit', 'POW', 1, 17, 19, 20, 9, 10, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Rooftop Drop', 'Heavy', 'POW', 1, 44, 64, -10, 13, 12, 39, '—', 'Iron Quarry: POW ≥ 360'],
    ['Spooky Snicker', 'Wither', 'INT', 2, 26, 18, 4, 44, 7, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Ledge Claw', 'Sharp', 'POW', 2, 29, 30, 2, 11, 32, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Rain-Spout Spit', 'Special', 'POW', 3, 49, 30, 2, 16, 12, 36, 'stun 30 ticks', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Dusk Ambush', 'Chain', 'POW', 1, 23, 22, 19, 11, 13, 30, '—', "Archer's Glade: Sneaky Jab Lv3 + POW ≥ 520"],
    ['Petrify Pounce', 'Signature', 'POW', 1, 57, 44, 2, 24, 14, 42, 'stun 45 ticks', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  rammerjack: [
    ['Horn Bonk', 'Basic', 'POW', 1, 11, 10, 3, 7, 8, 24, '—', 'Starter'],
    ['Hoof Stamp', 'Basic', 'POW', 2, 11, 10, 3, 7, 8, 24, '—', 'Starter'],
    ['Brow Bump', 'Hit', 'POW', 2, 18, 14, 14, 8, 7, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Battering Charge', 'Heavy', 'POW', 1, 44, 50, -12, 13, 10, 39, 'dash to Close after', 'Iron Quarry: POW ≥ 360'],
    ['Bleat Blast', 'Wither', 'POW', 3, 25, 12, -2, 41, 5, 30, '—', 'Starfall Observatory: POW+INT ≥ 480'],
    ['Spiral Horn Hook', 'Sharp', 'POW', 2, 27, 22, -4, 10, 30, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Avalanche Charge', 'Special', 'POW', 3, 47, 36, -2, 19, 10, 36, 'knockback', 'Glacier Bastion: DEF+POW ≥ 820 · grade B+'],
    ['Twin Horn Bash', 'Chain', 'POW', 1, 19, 19, 10, 8, 11, 27, '—', "Archer's Glade: Horn Bonk Lv3 + POW ≥ 520"],
    ['Mountain Ram', 'Signature', 'POW', 2, 53, 64, 4, 23, 18, 42, 'miss: self-dmg 10% max HP', 'Auto at Prime (loyalty ≥ 60)'],
  ],
  frostlance: [
    ['Tusk Poke', 'Basic', 'POW', 1, 14, 13, 8, 5, 6, 24, '—', 'Starter'],
    ['Snowflake Puff', 'Basic', 'INT', 3, 12, 13, 8, 7, 5, 24, '—', 'Starter'],
    ['Icicle Thrust', 'Hit', 'POW', 2, 19, 19, 20, 7, 8, 27, '—', "Archer's Glade: SKI ≥ 220"],
    ['Blizzard Lance', 'Heavy', 'INT', 4, 46, 64, -6, 13, 10, 39, '—', 'Iron Quarry: INT ≥ 360'],
    ['Frostbite Breeze', 'Wither', 'INT', 3, 27, 18, 4, 42, 7, 30, '—', 'Starfall Observatory: INT ≥ 280'],
    ['Glacier Pierce', 'Sharp', 'POW', 2, 27, 30, 2, 10, 29, 30, '—', 'Windrun Steppe: SPD+SKI ≥ 520'],
    ['Northern Lights', 'Special', 'INT', 4, 48, 0, -2, 30, 0, 36, 'heal 15% max HP', 'Glacier Bastion: DEF+INT ≥ 820 · grade B+'],
    ['Crystal Lance Rush', 'Chain', 'POW', 2, 25, 25, 20, 8, 11, 30, '—', "Archer's Glade: Icicle Thrust Lv3 + POW ≥ 520"],
    ['Polar Spiral', 'Signature', 'POW', 2, 54, 18, 3, 23, 30, 42, '3 hits', 'Auto at Prime (loyalty ≥ 60)'],
  ],
}

/** CONTENT §3.1: the learn column holds the Songsheet price and where it is sold. */
const UNIVERSAL_ROWS: readonly Row[] = [
  ['Beat Bump', 'Basic', 'POW', 1, 14, 14, 3, 7, 7, 24, '—', '500G · Guild Library, from the start'],
  ['Shuffle Step Kick', 'Basic', 'POW', 2, 11, 12, 3, 5, 8, 24, '—', '500G · Guild Library, from the start'],
  ['Hum Pulse', 'Basic', 'INT', 3, 12, 13, 4, 6, 8, 24, '—', '500G · Guild Library, from the start'],
  ['Whistle Shot', 'Basic', 'INT', 4, 13, 11, 4, 7, 7, 24, '—', '500G · Guild Library, from the start'],
  ['Staccato Jab', 'Hit', 'POW', 1, 17, 19, 16, 7, 6, 27, '—', '1,000G · Guild Library, from the start'],
  ['Downbeat Strike', 'Hit', 'POW', 2, 18, 15, 18, 8, 10, 27, '—', '1,000G · Guild Library, from the start'],
  ['Chime Bolt', 'Hit', 'INT', 3, 20, 14, 16, 7, 8, 27, '—', '1,000G · Guild Library, from the start'],
  ['Piccolo Dart', 'Hit', 'INT', 4, 20, 17, 13, 7, 9, 27, '—', '1,000G · Guild Library, from the start'],
  ['Crescendo Slam', 'Heavy', 'POW', 1, 47, 56, -9, 13, 11, 39, '—', '2,500G · Guild Library, rank 4+ · or prizes/expeditions earlier'],
  ['Timpani Crash', 'Heavy', 'POW', 2, 45, 61, -7, 12, 9, 39, '—', '2,500G · Guild Library, rank 4+ · or prizes/expeditions earlier'],
  ['Grand Finale', 'Heavy', 'INT', 3, 48, 52, -10, 11, 10, 39, '—', '2,500G · Guild Library, rank 4+ · or prizes/expeditions earlier'],
  ['Fortissimo Blast', 'Heavy', 'INT', 4, 44, 53, -13, 11, 10, 39, '—', '2,500G · Guild Library, rank 4+ · or prizes/expeditions earlier'],
  ['Drumroll Stomp', 'Wither', 'POW', 1, 27, 17, 3, 41, 8, 30, '—', '1,500G · Guild Library, breeder rank 2+'],
  ['Off-Key Wail', 'Wither', 'INT', 2, 25, 15, -1, 41, 4, 30, '—', '1,500G · Guild Library, breeder rank 2+'],
  ['Lullaby Haze', 'Wither', 'INT', 3, 27, 15, -1, 44, 5, 30, '—', '1,500G · Guild Library, breeder rank 2+'],
  ['Hush Note', 'Wither', 'INT', 4, 28, 13, -1, 40, 7, 30, '—', '1,500G · Guild Library, breeder rank 2+'],
  ['Cymbal Clash', 'Sharp', 'POW', 1, 27, 28, 1, 9, 30, 30, '—', '1,500G · Guild Library, breeder rank 2+'],
  ['Pizzicato Pluck', 'Sharp', 'POW', 2, 26, 25, 1, 9, 31, 30, '—', '1,500G · Guild Library, breeder rank 2+'],
  ['Tremolo Ray', 'Sharp', 'INT', 3, 25, 25, 0, 10, 30, 30, '—', '1,500G · Guild Library, breeder rank 2+'],
  ['High Note', 'Sharp', 'INT', 4, 29, 24, -1, 9, 31, 30, '—', '1,500G · Guild Library, breeder rank 2+'],
  ['Rondo Rush', 'Special', 'POW', 2, 48, 10, -2, 17, 9, 36, '3 hits', '4,000G · Guild Library, rank 4+ · or prizes/expeditions earlier'],
  ['Harmony Mend', 'Special', 'INT', 3, 49, 0, 0, 0, 0, 36, 'heal 20% max HP', '4,000G · Guild Library, rank 4+ · or prizes/expeditions earlier'],
  ['Resonance Drain', 'Special', 'INT', 3, 47, 31, 0, 19, 11, 36, 'drain 40% of dmg', '4,000G · Guild Library, rank 4+ · or prizes/expeditions earlier'],
  ['Feedback Loop', 'Special', 'INT', 4, 49, 16, -2, 36, 9, 36, 'steal guts = wither', '4,000G · Guild Library, rank 4+ · or prizes/expeditions earlier'],
]

/** CONTENT §3: breed Songsheet prices and breeder-rank gates by family. Basics have no sheet; Signatures are Crown prizes. */
const BREED_SHEETS: Partial<Record<Family, Songsheet>> = {
  Hit: { price: 1000, rankMin: 1, sold: true },
  Wither: { price: 1500, rankMin: 2, sold: true },
  Sharp: { price: 1500, rankMin: 2, sold: true },
  Heavy: { price: 2500, rankMin: 4, sold: true },
  Special: { price: 4000, rankMin: 4, sold: true },
  Chain: { price: 5000, rankMin: 4, sold: true },
  Signature: { price: 0, rankMin: 0, sold: false },
}

const SITE_BY_NAME: Record<string, JourneySiteId> = {
  'Iron Quarry': 'iron-quarry',
  'Windrun Steppe': 'windrun-steppe',
  'Starfall Observatory': 'starfall-observatory',
  "Archer's Glade": 'archers-glade',
  'Glacier Bastion': 'glacier-bastion',
}

/** "Will-o'-Blaze" → "will-o-blaze", "Trickster's Hush" → "tricksters-hush". */
export function slugify(name: string): string {
  return name
    .normalize('NFKD')
    .replace(/['’]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export function parseEffect(text: string): TechEffect | null {
  if (text === '—') return null
  let m: RegExpExecArray | null
  if ((m = /^(\d) hits$/.exec(text))) return { kind: 'multi', hits: Number(m[1]) }
  if ((m = /^heal (\d+)% max HP$/.exec(text))) return { kind: 'heal', pct: Number(m[1]) }
  if ((m = /^stun (\d+) ticks$/.exec(text))) return { kind: 'stun', ticks: Number(m[1]) }
  if ((m = /^drain (\d+)% of dmg$/.exec(text))) return { kind: 'drain', pct: Number(m[1]) }
  if ((m = /^miss: self-dmg (\d+)% max HP$/.exec(text))) return { kind: 'recoil', pct: Number(m[1]) }
  if (text === 'steal guts = wither') return { kind: 'gutsSteal' }
  if (text === 'knockback') return { kind: 'push' }
  if (text === 'dash to Close after') return { kind: 'lunge' }
  if (text === 'random: x2 dmg / heal 20% / fizzle') return { kind: 'jackpot' }
  throw new Error(`Unknown technique effect text: ${text}`)
}

const LEARN_RE = /^(Iron Quarry|Windrun Steppe|Starfall Observatory|Archer's Glade|Glacier Bastion): (?:(.+?) Lv3 \+ )?([A-Z]{3}(?:\+[A-Z]{3})*) ≥ (\d+)(?: · grade ([EDCBAS])\+)?$/

export function parseLearn(text: string, breed: BreedId): TechLearn {
  if (text.startsWith('Starter')) return { kind: 'starter' }
  if (text.startsWith('Auto at Prime')) return { kind: 'signature' }
  const m = LEARN_RE.exec(text)
  if (!m) throw new Error(`Unparsable learn text: ${text}`)
  return {
    kind: 'journey',
    site: SITE_BY_NAME[m[1]!]!,
    stats: m[3]!.split('+') as StatKey[],
    value: Number(m[4]),
    chainOf: m[2] ? `${breed}.${slugify(m[2])}` : null,
    gradeMin: (m[5] as TournamentGrade | undefined) ?? null,
  }
}

function parseUniversalSheet(text: string): Songsheet {
  const price = /^([\d,]+)G/.exec(text)
  const rank = /rank (\d)\+/.exec(text)
  if (!price) throw new Error(`Unparsable Songsheet text: ${text}`)
  return { price: Number(price[1]!.replace(/,/g, '')), rankMin: rank ? Number(rank[1]) : 1, sold: true }
}

function buildBreedTechnique(breed: BreedId, row: Row): Technique {
  const [name, family, type, range, cost, force, hit, wither, sharp, anim, effect, learn] = row
  const id = `${breed}.${slugify(name)}`
  return {
    id,
    name,
    breed,
    family,
    type,
    range,
    cost,
    force,
    hit,
    wither,
    sharp,
    anim,
    effect: parseEffect(effect),
    learn: parseLearn(learn, breed),
    element: elementOf({ name, breed, type }, id),
    sheet: BREED_SHEETS[family] ?? null,
  }
}

function buildUniversalTechnique(row: Row): Technique {
  const [name, family, type, range, cost, force, hit, wither, sharp, anim, effect, sheetText] = row
  const id = `universal.${slugify(name)}`
  return {
    id,
    name,
    breed: 'universal',
    family,
    type,
    range,
    cost,
    force,
    hit,
    wither,
    sharp,
    anim,
    effect: parseEffect(effect),
    learn: { kind: 'library' },
    element: elementOf({ name, breed: 'universal', type }, id),
    sheet: parseUniversalSheet(sheetText),
  }
}

export const BREED_TECHNIQUES: readonly Technique[] = (Object.keys(BREED_ROWS) as BreedId[]).flatMap((breed) =>
  BREED_ROWS[breed].map((row) => buildBreedTechnique(breed, row)),
)
export const UNIVERSAL_TECHNIQUES: readonly Technique[] = UNIVERSAL_ROWS.map(buildUniversalTechnique)
export const TECHNIQUES: readonly Technique[] = [...BREED_TECHNIQUES, ...UNIVERSAL_TECHNIQUES]
export const TECHNIQUE_BY_ID: Readonly<Record<string, Technique>> = Object.fromEntries(TECHNIQUES.map((t) => [t.id, t]))

export function techniqueById(id: string): Technique | undefined {
  return TECHNIQUE_BY_ID[id]
}

/** A breed's nine techniques in CONTENT table order. */
export function techniquesOfBreed(breed: BreedId): readonly Technique[] {
  return BREED_TECHNIQUES.filter((t) => t.breed === breed)
}

export function startersOf(breed: BreedId): readonly Technique[] {
  return techniquesOfBreed(breed).filter((t) => t.learn.kind === 'starter')
}

export function signatureOf(breed: BreedId): Technique {
  const sig = techniquesOfBreed(breed).find((t) => t.family === 'Signature')
  if (!sig) throw new Error(`Breed ${breed} has no Signature technique`)
  return sig
}
