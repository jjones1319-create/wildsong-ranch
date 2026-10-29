import { readFileSync } from 'node:fs'
import preact from '@preact/preset-vite'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'

// The game lives at https://<user>.github.io/wildsong-ranch/ so every URL starts with this base.
// It must match the GitHub repo name and the manifest id/scope/start_url below.
const BASE = '/wildsong-ranch/'
const THEME = '#131a1e'

const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')) as {
  version: string
}

export default defineConfig({
  base: BASE,
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  plugins: [
    preact(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['favicon.ico', 'apple-touch-icon-180x180.png', 'logo.svg'],
      manifest: {
        id: BASE,
        scope: BASE,
        start_url: BASE,
        name: 'Wildsong Ranch',
        short_name: 'Wildsong',
        description: 'An original monster-raising game. Every monster is born from a song.',
        lang: 'en',
        display: 'standalone',
        orientation: 'portrait',
        background_color: THEME,
        theme_color: THEME,
        icons: [
          { src: 'pwa-64x64.png', sizes: '64x64', type: 'image/png' },
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // Sound 2.0 §5.4: the audio manifest and every sample are precached, so the game sounds right offline.
        globPatterns: ['**/*.{js,css,html,svg,png,webp,woff2,json,ogg}'],
        // Art 2.0 §3.7: models download on first use and are kept by the runtime cache below; the breed portraits
        // (public/portraits) stay precached as the offline fallback pictures.
        globIgnores: ['**/models/**'],
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
        navigateFallback: `${BASE}index.html`,
        cleanupOutdatedCaches: true,
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.includes('/models/') || url.pathname.includes('/baked/'),
            handler: 'CacheFirst',
            options: { cacheName: 'wildsong-art', expiration: { maxEntries: 120 }, cacheableResponse: { statuses: [0, 200] } },
          },
        ],
      },
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        // Sound 2.0 §2: the engine is its own chunk (≤ 45 KB gzipped, checked by check:build); each song is a
        // lazy chunk that loads with its place.
        manualChunks(id) {
          const n = id.replace(/\\/g, '/')
          // Art 2.0 §3.6: three and the 3D runtime form their own lazy chunk (art3d-*.js, ≤ 300 KB gzipped, checked by
          // check:build) through the dynamic import of src/art3d/art3d.ts; a manual rule here would pull shared app
          // modules into it and make the entry import it statically.
          if (n.includes('/src/audio/music/songs/') && !n.endsWith('/index.ts')) return `song-${n.split('/').pop()!.replace(/\.ts$/, '')}`
          if (n.includes('/src/audio/recipes/') || n.includes('/src/audio/music/stingers.ts') || n.includes('/src/audio/music/effects.ts')) return 'audio-recipes'
          // The checker and the motif detector only serve the Sound Lab and the tools, never the game at play.
          if (n.includes('/src/audio/music/checker.ts') || n.includes('/src/audio/music/motifs.ts')) return 'audio-checker'
          if (n.includes('/src/audio/engine/') || n.includes('/src/audio/music/') || n.includes('/src/audio/runtime.ts') || n.includes('/src/audio/levels.json')) return 'audio-engine'
          return undefined
        },
      },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    // The §26 sim tests play 40 whole lives per policy; give slower CI runners room.
    testTimeout: 60_000,
  },
})
