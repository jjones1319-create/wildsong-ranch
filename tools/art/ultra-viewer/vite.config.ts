import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'

// The Ultra review viewer's dev server (tools/art/ultra-review.ts): the repo root under the game's base path, serving
// public/ (the models and the KTX2 transcoder). No hot reload: another agent editing src/ mid-capture must not reload
// the page (it did in the spike, ART_2_DETAIL §8.3).
const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..')

export default defineConfig({
  root: ROOT,
  base: '/wildsong-ranch/',
  publicDir: join(ROOT, 'public'),
  server: { port: 5181, strictPort: true, hmr: false, watch: { ignored: ['**/*'] } },
})
