/** docs/BATTLE_3D.md: the Battle 3D test screen (Lab → Battle 3D). */
export const BATTLE3D_TEXT = {
  title: 'Battle 3D (test)',
  labButton: 'Battle 3D (test)',
  loading: 'Building the arena…',
  noWebgl: "This phone can't draw the 3D arena. The classic battle still works everywhere else.",
  tapToSkip: 'Tap to skip',
  faceOff: 'Ready… Fight!',
  stickHint: 'Drag to move · flick sideways to sidestep · flick forward to dash',
  camera: { side: '🎥 Side', behind: '🎥 Behind' },
  cameraLabel: 'Switch camera',
  dodged: 'Dodged!',
  fence: 'Into the fence!',
  /** The speed button (×1 → ×2 → ×4). */
  speedLabel: (n: number) => `Speed ×${n}. Tap for the next speed.`,
  /** ⚙️ Setup: the test's choices in one sheet, so the buttons along the top fit one row on a phone. */
  setup: {
    chip: '⚙️ Setup',
    label: 'Fight setup: the breeds, the arena, the upbringing and the crowd',
    title: 'Fight setup',
    note: 'A new breed, arena or upbringing starts the fight again.',
    close: 'Back to the fight',
  },
  /** §8 the 🐾 chips: each side's breed, any finished 3D breed. */
  breed: {
    chip: (side: 0 | 1, name: string) => `🐾 ${side === 0 ? 'You' : 'Rival'}: ${name}`,
    label: (side: 0 | 1, name: string, more: boolean) =>
      `${side === 0 ? 'Your monster' : 'Your rival'} is a ${name}. ${more ? 'Tap for the next breed (the fight restarts).' : 'More breeds join here as they’re finished.'}`,
  },
  arena: {
    names: { guild: "the Breeders' Guild arena", crown: 'the Crown Amphitheatre' },
    short: { guild: 'Guild', crown: 'Crown' },
    chip: (name: string) => `🏟️ ${name}`,
    label: (name: string) => `Fighting in ${name}. Tap to try the other arena (the fight restarts).`,
  },
  sideways: {
    title: 'Better sideways',
    body: 'Turn your phone on its side: the stick under your left thumb, attacks under your right, and a wider view of the fight.',
    play: 'Play sideways',
    stay: 'Stay upright',
    turn: 'Turn your phone sideways',
  },
  push: 'Push',
  pushHint: 'Push: walk right up to them first',
  range: (band: string, metres: string) => `${band} · ${metres} m`,
  leave: 'Leave',
  rematch: 'Rematch',
  skip: 'Skip',
  reduceMotion: 'gentle camera',
  stats: (fps: number, dpr: number, backend: string, level: string) => `${fps.toFixed(0)} fps · ${dpr.toFixed(2)}× · ${backend} · ${level}`,
  stand: { arena: 'Stand-in arena (the Guild arena is being built)', monster: 'Stand-in Puddlepup (Art 2.0; the Ultra one is being built)' },
  /** The crowd chip: the stands fill with your monster's Fame. */
  crowdFame: (fame: number) => `👥 Fame ${fame}`,
  upbringing: {
    names: { seasoned: 'Seasoned', untrained: 'Untrained', spoiled: 'Spoiled' },
    chip: (name: string, sense: number) => `🧠 ${name} ${sense}`,
    label: (sense: number, why: string) => `Battle sense ${sense}${why ? `: ${why}` : ''}. It's how well your monster fights on Auto. Tap to try another upbringing (the fight restarts).`,
    why: { seasoned: 'seasoned', untrained: 'untrained', loyal: 'loyal', fickle: 'not very loyal', spoiled: 'spoiled' },
  },
  crowdFameLabel: (fame: number) => `Crowd for Fame ${fame}. Tap to try another Fame.`,
  crowdStats: (people: number, cutouts: number, ms: number) => ` · 👥 ${people} + ${cutouts} boards · ${ms.toFixed(2)} ms`,
} as const
