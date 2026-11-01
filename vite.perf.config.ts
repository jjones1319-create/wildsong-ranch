import { defineConfig } from 'vite'

// The Art 2.1 Performance check (docs/ART_2_DETAIL.md §6) is its own small build, run after the game's: it writes
// dist/perf/index.html and dist/perf/assets/, never touches the game's chunks, and is not precached (the game's
// service worker leaves /perf/ alone, see vite.config.ts). It reads the test model from public/models/perf/ and the
// KTX2 transcoder from public/basis/, which the game's build already copied into dist/.
export default defineConfig(({ command }) => ({
  base: '/wildsong-ranch/',
  publicDir: command === 'build' ? false : 'public',
  server: { port: 5174 },
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    assetsDir: 'perf/assets',
    target: 'es2022',
    chunkSizeWarningLimit: 2048,
    rollupOptions: { input: { perf: 'perf/index.html' } },
  },
}))
