import { defineConfig } from '@vite-pwa/assets-generator/config'

// Generates the app icons in public/ from the original logo. Run: npm run icons
const background = '#1b262c'

export default defineConfig({
  headLinkOptions: { preset: '2023' },
  preset: {
    transparent: { sizes: [64, 192, 512], favicons: [[48, 'favicon.ico']] },
    maskable: { sizes: [512], padding: 0.2, resizeOptions: { background } },
    apple: { sizes: [180], padding: 0.1, resizeOptions: { background } },
  },
  images: ['public/logo.svg'],
})
