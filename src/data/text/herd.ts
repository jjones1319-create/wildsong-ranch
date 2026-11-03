/**
 * Player-facing text for v16: the herd (ranch-mates on standing orders, GAME_DESIGN §6.11), the farm level and its
 * pens and perks (§9.1, CONTENT §11), setting a monster free, and the one-time homecoming (§6.10). Wren's warm,
 * simple voice; Ines is formal. {name} is the monster, {them}/{their}/{they} its pronoun ({They}/{Their} to start a
 * sentence), {old} the star it replaced, {n} a number.
 */
export const HERD_TEXT = {
  /** Wren's week-summary lines about a ranch-mate (notable news only; routine weeks show as badges). */
  wren: {
    illness: '{name} caught a sniffle out in the pen. {They} will rest until it passes.',
    ranOff: '{name} slipped out of the pen and ran off! I left the gate open and a bowl by the fence.',
    collapsed: '{name} keeled over during chores. Dr. Pell has {them} at the clinic for a little while.',
    cameBack: '{name} wandered back into the pen, muddy and very pleased to be home.',
    clinicBack: '{name} is back from the clinic and settling into the straw.',
    prime: '{name} is in {their} prime out in the pen. Look at {them} go!',
    signature: '{name} just learned {technique}, the family technique! The whole pen heard about it.',
    w48: '{name} has about a year left, I think. Let’s make it a gentle one.',
    w10: '{name} doesn’t have much time left. I’ll keep {their} corner of the pen warm.',
    passed: '{name} passed away quietly in the pen this week, with friends close by. {They} had a good life here.',
    retired: '{name} has moved to the Elder Grove. The pen feels bigger without {them}.',
    heartstone: '{name} left a Heartstone. Dr. Pell is keeping it safe.',
    heartstoneLost: 'There was no room on the shelf for {name}’s Heartstone.',
  },
  /** What each order is called on the herd strip and sheet. */
  orders: {
    drill: { icon: '🏋️', label: 'Train' },
    rest: { icon: '💤', label: 'Rest' },
    play: { icon: '🌼', label: 'Play' },
  },
  /** Last week's badge on a ranch-mate's tile. */
  last: {
    autoRest: {
      sick: 'Rested: unwell',
      injured: 'Rested: hurt',
      tired: 'Rested: tired',
      stressed: 'Rested: tense',
      noYard: 'Rested: no Training Yard',
    },
    away: { missing: 'Missing', clinic: 'At the clinic', cocoon: 'In a cocoon' },
    pay: '+{n}G',
    rest: 'Rested',
    play: 'Played',
    none: 'New in the pen',
    /** The sheet's longer line for a drill week: the drill and how it went. */
    drill: '{drill}: {outcome}',
  },
  /** What a ranch-mate is doing right now (it wins over last week's badge). */
  status: { sick: 'Unwell', injured: 'Hurt', missing: 'Missing', clinic: 'At the clinic', cocoon: 'In a cocoon' },
  /** The herd strip under the stage. */
  strip: {
    label: 'The herd',
    star: '{name}, the star. Open the Monster Card.',
    mate: '{name}. Order: {order}. {status}',
    emptyPen: 'An empty pen. Move a monster in.',
    /** "Pens 1/2 · Farm Lv 3". */
    count: 'Pens {used}/{max} · Farm Lv {n}',
    newPen: '+ pen',
    newPenLabel: 'Build another pen at Ranch Upgrades.',
    lockedPenLabel: 'The next pen opens at farm level {n}. See Ranch Upgrades.',
  },
  /** §6.11 friendships: monsters at home together grow closer. {a} and {b} are names. */
  friends: {
    tiers: ['Getting to know each other', 'Friends', 'Close friends', 'Best friends'],
    /** Wren's week-summary line when a pair reaches a tier (index 1–3). */
    reached: [
      '',
      '{a} and {b} are friends now! They keep finding reasons to sit together.',
      '{a} and {b} are close friends now! I caught them sharing a snack by the fence.',
      '{a} and {b} are best friends now! Where one goes, the other follows.',
    ],
    /** The herd sheet: the ranch-mate's friendship with the star. */
    withStar: 'With {name}',
    /** The Monster Card's section. */
    title: 'Friends',
    none: '{name} hasn’t made friends yet. Monsters who live at home together grow closer every week.',
    points: '{n} pts',
    /** The drill result, when the training partner joined in. */
    buddy: '{buddy} trained right alongside! {name} worked extra hard to keep up.',
    /** The Train sheet's tag on a drill a friend is ready to share. */
    partner: '🤝 {name} joins in',
  },
  /** A ranch-mate's sheet (tap its tile on the strip). */
  sheet: {
    age: '{n} weeks old · {stage}',
    lastWeek: 'Last week',
    order: 'Standing order',
    drill: 'Which drill',
    needsYard: '{drill} (needs the Training Yard)',
    orderSet: 'Got it. {name} will {order} from now on.',
    orderVerb: { drill: 'practise {drill}', rest: 'rest', play: 'play' },
    card: 'Monster Card',
    edit: '✏️ Edit',
    makeStar: '⭐ Make star',
    toFreezer: '❄️ To the Freezer',
    free: '🕊️ Set free',
  },
  /** The empty pen's "+" sheet. */
  pen: {
    title: 'An empty pen',
    intro: 'Who should move in? Time starts again for them once they’re out of the Freezer.',
    none: 'Nobody in the Freezer can move in. Sing to the stone at the Shrine, or find a friend at the Market.',
  },
  /** After the star's Farewell, or an empty ranch with ranch-mates. */
  next: {
    title: 'Who will you raise next?',
    wren: 'The pens are full of friends who’d love a turn on the ranch. Who should it be?',
    later: 'Later',
  },
  /** A ranch-mate's gentle goodbye card in the week summary. */
  goodbye: {
    passed: 'Goodbye, {name}',
    retired: 'Off to the Grove, {name}',
    memorial: 'Write an epitaph at the Memorial',
  },
  /** The Lab editor, for a ranch-mate. */
  edit: {
    saved: 'Saved. {name} is back in the pen.',
    note: 'This monster lives in a pen. Save writes straight to the pen and keeps the old version in Edit history.',
  },
  /** The Bag's and the Songbook's "who is this for?" row. */
  target: { label: 'For', star: '⭐ {name}' },
  /** Making a ranch-mate the star, and why it can't happen right now. */
  star: {
    done: '{name} is the star now. {old} is happy in the pen.',
    first: '{name} is the star now. The ranch is {their} stage.',
    ask: 'Make {name} the star? {old} moves into the pen and keeps a standing order.',
    askEmpty: 'Bring {name} onto the ranch as the star?',
    refused: {
      notFound: 'That monster isn’t in a pen.',
      ended: 'Say goodbye first. The swap can wait.',
      busy: 'Finish the cup, Journey, Trial or expedition first.',
      cocoon: 'Not while there’s a cocoon on the barn beam.',
    },
  },
  move: {
    toFreezer: '{name} is tucked into the Freezer. Time will wait.',
    toPen: '{name} is out of the Freezer and in a pen, stretching.',
    freezerFull: 'The Freezer is full.',
    pensFull: 'Every pen is taken.',
    toPenButton: '🏡 Move to a pen',
    /** Pell's Lab when the homecoming filled the Freezer past its slots. */
    freezerOver: 'The homecoming filled the Freezer past its slots. Nothing new fits until there’s room again.',
  },
  /** Setting a monster free (the star must be swapped first). */
  free: {
    title: 'Set {name} free?',
    body: '{name} will head off over the hills to a life of {their} own. {Their} name goes on the Memorial wall. There’s no Heartstone, and this can’t be undone.',
    keepCopy: 'Keep a copy in the Lab Library',
    confirm: 'Set free',
    done: '{name} trotted off over the hill, looked back once, and was gone. Go well, {name}.',
    star: 'Pick another star first, then {name} can go.',
    epitaph: '{name} went off over the hills, free and happy.',
  },
  /** The placement line for the Shrine, the Market and Fusion (the expedition's is in EXPEDITION_TEXT.lootlidWhere). */
  placed: {
    pen: '{name} moved into a pen.',
    /** Fusion's "the baby goes to {where}" and its "born at" line; the Market's "where" line. */
    where: 'a pen',
    bornPen: 'Settling into a pen',
    market: 'It will move into a pen beside the star.',
  },
  /** The planner stopped for ranch-mate news. */
  plannerStop: 'There’s news from the pens and the farm. I stopped so you can see.',
  /** The one-time homecoming card. */
  homecoming: {
    title: 'Welcome home!',
    wren: 'You won’t believe who just walked up the lane. Look who came home!',
    one: '{name} came home!',
    star: '{name} is back on the ranch.',
    pen: '{name} is settling into a pen.',
    freezer: '{name} is resting in the Freezer until there’s room.',
    button: 'Welcome home!',
  },
  /** Ines's letters (the mailbox). */
  mail: {
    kinds: { farm: 'The farm has grown', homecoming: 'Welcome home' },
    bodies: {
      farm: 'Ines: "The Guild has entered your farm at level {n}. New pens may now be built, and some comforts come with the rank. See the farm card at Ranch Upgrades."',
      homecoming: 'Ines: "The Guild is pleased to record a homecoming at your ranch (returned: {n}). The Memorial wall has been corrected accordingly. Welcome back."',
    },
  },
  /** The farm card (Ranch Upgrades) and its perks. */
  farm: {
    title: 'The farm',
    intro: 'The farm grows with every week and every success. Pens are bought; comforts come with the level.',
    level: 'Farm Lv {n}',
    xpLabel: 'XP',
    xp: '{xp} / {next} XP',
    max: 'Top level',
    pensBuilt: 'Pens built: {n} of {max}',
    nextPen: 'Next pen: {price}G at Lv {level}',
    allBuilt: 'Every pen is built.',
    buyPen: 'Build a pen ({price})',
    ask: 'Build pen {n} for {price}? One more ranch-mate will fit.',
    built: 'The new pen is built! There’s room for one more ranch-mate.',
    refused: { allBuilt: 'Every pen is built.', level: 'The farm needs to reach Lv {n} first.', money: 'Not enough gold yet.' },
    perksTitle: 'Comforts',
    locked: '🔒 Lv {n}',
    /** The week summary's little celebration, and Wren's line. */
    levelUp: 'Farm Lv {n}!',
    levelUpLine: 'The farm reached level {n}! Ines sent a letter from the Guild.',
    brings: 'New: {list}',
    newPen: 'a pen to build',
    perks: {
      feedShed: 'Ranch-mates eat at 60% of the price.',
      farmhand: 'A farmhand praises ranch-mates’ good drills.',
      deepFreezer: 'The Freezer holds 30.',
      campfire: 'Friendships grow faster around the fire.',
    },
  },
  /** The food prompt with ranch-mates to feed. */
  food: { feeds: 'Feeds {n} · {total}G' },
} as const
