/** Player-facing strings for the app shell: title, menu, placeholders, credits, toasts. Wren's voice is warm and simple. */
export const UI_TEXT = {
  title: 'Wildsong Ranch',
  tagline: 'Every monster is born from a song.',
  wren: 'Wren',
  versionPrefix: 'v',
  back: 'Back',
  menu: {
    newGame: 'New Game',
    continue: 'Continue',
    lab: 'Monster Lab',
    settings: 'Settings',
    credits: 'Credits',
  },
  placeholder: {
    newGame: {
      heading: 'New Game',
      wren: 'The ranch gate is still getting its first coat of paint! New games open in milestone M3. For now, enjoy the view.',
    },
    continue: {
      heading: 'Continue',
      wren: "There's nothing to load yet. Saving arrives in milestone M2, and I'll keep every save safe after that.",
    },
    lab: {
      heading: 'Monster Lab',
      wren: 'Dr. Pell is still unpacking her instruments. The Monster Lab opens in milestone M2.',
    },
    settings: {
      heading: 'Settings',
      wren: 'Nothing to fiddle with yet. Settings arrive in milestone M3.',
    },
  },
  credits: {
    heading: 'Credits',
    madeBy: 'Wildsong Ranch is an original game, designed and built with Claude Code.',
    original: 'Every monster, character, name, picture, sound and line of text in this game is original.',
    tools: 'Built with Vite, TypeScript and Preact. Sound by ZzFX. Hosted on GitHub Pages.',
    license: 'The source code is released under the MIT License.',
    disclaimer:
      'Unofficial fan-made game inspired by classic monster-raising sims. Not affiliated with or endorsed by Koei Tecmo. Monster Rancher is a trademark of KOEI TECMO GAMES CO., LTD.',
  },
  toast: {
    updateReady: 'Update ready',
    restart: 'Restart',
    later: 'Later',
    offlineReady: 'Ready to play offline',
  },
} as const
