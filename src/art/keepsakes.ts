import type { KeepsakeId } from '../data/types.ts'

/**
 * GAME_DESIGN §6.9 the keepsakes on the ranch, drawn in code: small flat props in the ranch's palette, each on a
 * 64 × 64 box standing on its bottom edge. Original shapes.
 */

const W = 64

function svg(body: string, label: string): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${W}" role="img" aria-label="${label}"><ellipse cx="32" cy="60" rx="22" ry="3.5" fill="#000" opacity=".18"/>${body}</svg>`
}

const ART: Record<KeepsakeId, string> = {
  'kick-ball': `<circle cx="32" cy="42" r="17" fill="#f3ead8" stroke="#3b2a22" stroke-width="2"/><path d="M32 30l7 5-3 8h-8l-3-8z" fill="#c55b4a"/><path d="M15 40l6-2 3 7-3 6M49 40l-6-2-3 7 3 6" fill="none" stroke="#c55b4a" stroke-width="3" stroke-linecap="round"/>`,
  pinwheel: `<rect x="30.5" y="30" width="3" height="28" rx="1.5" fill="#8a6440"/><path d="M32 30L32 12 44 24z" fill="#f2b544"/><path d="M32 30L50 30 38 42z" fill="#3f7fc4"/><path d="M32 30L32 48 20 36z" fill="#c55b4a"/><path d="M32 30L14 30 26 18z" fill="#7faf5a"/><circle cx="32" cy="30" r="2.5" fill="#f3ead8"/>`,
  'hay-hammock': `<rect x="8" y="20" width="4" height="38" rx="2" fill="#7a5132"/><rect x="52" y="20" width="4" height="38" rx="2" fill="#7a5132"/><path d="M11 26Q32 50 53 26" fill="none" stroke="#c9a66b" stroke-width="3"/><path d="M13 29Q32 52 51 29Q32 44 13 29z" fill="#e3c26a"/><path d="M20 35l3-4M28 40l2-5M36 40l-1-5M44 35l-3-4" stroke="#b8933f" stroke-width="1.5"/>`,
  'wind-chime': `<rect x="31" y="6" width="2" height="8" fill="#6b4a32"/><path d="M18 18h28l-4-5H22z" fill="#8a6440"/><g stroke="#6b4a32" stroke-width="1"><path d="M22 18v10M29 18v14M36 18v12M43 18v9"/></g><rect x="20.5" y="28" width="3" height="16" rx="1.5" fill="#cfd6db"/><rect x="27.5" y="32" width="3" height="18" rx="1.5" fill="#e8d9b5"/><rect x="34.5" y="30" width="3" height="15" rx="1.5" fill="#cfd6db"/><rect x="41.5" y="27" width="3" height="13" rx="1.5" fill="#e8d9b5"/><circle cx="32" cy="54" r="3" fill="#f2b544"/>`,
  'puzzle-board': `<rect x="10" y="34" width="44" height="22" rx="3" fill="#a87a4e" stroke="#6b4a32" stroke-width="2"/><circle cx="20" cy="42" r="3.5" fill="#c55b4a"/><circle cx="32" cy="42" r="3.5" fill="#3f7fc4"/><circle cx="44" cy="42" r="3.5" fill="#7faf5a"/><rect x="16" y="48" width="8" height="5" rx="1.5" fill="#f2b544"/><rect x="28" y="48" width="8" height="5" rx="1.5" fill="#8a63c9"/><rect x="40" y="48" width="8" height="5" rx="1.5" fill="#f3ead8"/>`,
  'splash-tub': `<path d="M8 36h48l-5 22H13z" fill="#9b6b42" stroke="#5e3f27" stroke-width="2"/><path d="M10 44h44M11.5 51h41" stroke="#5e3f27" stroke-width="1.5"/><ellipse cx="32" cy="36" rx="24" ry="5" fill="#5aa4d6" stroke="#5e3f27" stroke-width="2"/><path d="M22 35q3-2 6 0M36 37q3-2 6 0" stroke="#d8f0ff" stroke-width="1.5" fill="none"/>`,
  'star-plush': `<path d="M32 18l5.3 10.8 11.9 1.7-8.6 8.4 2 11.8L32 45.1l-10.6 5.6 2-11.8-8.6-8.4 11.9-1.7z" fill="#f2c94c" stroke="#b58a1f" stroke-width="2" stroke-linejoin="round" transform="translate(0 6)"/><circle cx="28" cy="40" r="1.6" fill="#3b2a22"/><circle cx="36" cy="40" r="1.6" fill="#3b2a22"/><path d="M29 44q3 2.5 6 0" stroke="#3b2a22" stroke-width="1.5" fill="none" stroke-linecap="round"/><circle cx="25" cy="43" r="1.8" fill="#f09a8a" opacity=".7"/><circle cx="39" cy="43" r="1.8" fill="#f09a8a" opacity=".7"/>`,
  'climbing-stump': `<path d="M16 58V30q0-4 4-4h24q4 0 4 4v28z" fill="#8a5a36" stroke="#5e3f27" stroke-width="2"/><ellipse cx="32" cy="28" rx="16" ry="5" fill="#c9a06b" stroke="#5e3f27" stroke-width="2"/><ellipse cx="32" cy="28" rx="9" ry="2.8" fill="none" stroke="#a37a4e" stroke-width="1.2"/><ellipse cx="32" cy="28" rx="4" ry="1.2" fill="none" stroke="#a37a4e" stroke-width="1"/><path d="M22 36v14M30 38v16M40 35v12" stroke="#6b4429" stroke-width="1.5"/><path d="M48 40q6-2 8 3" stroke="#7faf5a" stroke-width="3" fill="none" stroke-linecap="round"/>`,
  'kite-post': `<rect x="30.5" y="22" width="3" height="36" rx="1.5" fill="#7a5132"/><path d="M42 4l9 10-9 10-9-10z" fill="#c55b4a" stroke="#7a2f24" stroke-width="1.5"/><path d="M42 4v20M33 14h18" stroke="#7a2f24" stroke-width="1"/><path d="M42 24q-4 4-8 2t-2 4" fill="none" stroke="#3b2a22" stroke-width="1"/><path d="M42 24q2 5 6 6t2 6" fill="none" stroke="#f2b544" stroke-width="2"/>`,
  'story-blocks': `<rect x="12" y="42" width="16" height="16" rx="2" fill="#c55b4a" stroke="#7a2f24" stroke-width="1.5"/><rect x="30" y="42" width="16" height="16" rx="2" fill="#3f7fc4" stroke="#22466e" stroke-width="1.5"/><rect x="21" y="26" width="16" height="16" rx="2" fill="#f2b544" stroke="#9c6f1b" stroke-width="1.5"/><path d="M16 50h8M20 46v8" stroke="#f3ead8" stroke-width="2"/><circle cx="38" cy="50" r="3.5" fill="none" stroke="#f3ead8" stroke-width="2"/><path d="M29 30l4 8h-8z" fill="#f3ead8"/>`,
}

export function keepsakeSvg(id: KeepsakeId, label: string): string {
  return svg(ART[id], label)
}
