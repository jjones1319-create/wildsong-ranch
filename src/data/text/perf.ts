/** The Performance check page (perf/, docs/ART_2_DETAIL.md §6). Plain words: the owner reads it on the phone. */
export const PERF_TEXT = {
  title: 'Performance check',
  intro:
    'This runs the Art 2.1 Ultra test scenes on this phone and reports whether they hold 60 fps once the phone is warm. ' +
    'Keep the screen on and the phone unplugged, at a normal room temperature. Nothing in your saved game changes.',
  full: 'Run the full check (about 14 minutes)',
  quick: 'Quick run (about 2 minutes, to try it out)',
  memory: 'Memory ceiling test (the page may close itself)',
  memoryWarn:
    'This fills the graphics memory until the phone says no. The page can close or reload on its own; if it does, open it again and the last safe number is shown here.',
  copy: 'Copy results',
  copied: 'Copied. Paste them into Claude Code.',
  again: 'Run again',
  stages: {
    load: 'Loading the test monster…',
    ab: (name: string) => `Renderer test: ${name}`,
    card: 'Close-up: Monster Card with the cinematic textures and depth of field',
    dash: 'Meadow Dash: four runners',
    probe: (when: string) => `Speed probe (${when})`,
    soak: (min: number) => `Battle soak: ${min} minutes`,
    memory: 'Memory ceiling',
  },
  pass: 'PASS',
  fail: 'FAIL',
  notAvailable: 'not available on this browser',
  lastMemory: (mb: number) => `Last memory ceiling result: about ${mb} MB of graphics memory before the phone refused.`,
} as const
