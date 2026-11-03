/**
 * The Crown Amphitheatre's runtime notes (written into crown.json) and its review shots and sheet: the three.js viewer
 * (art-review/arena-crown/viewer.html) in Chrome on this PC's GPU from every review camera, then sheet.png with the
 * Cycles renders beside them. Used by crown.ts.
 */
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type { ChildProcess } from 'node:child_process'
import { chromium } from '@playwright/test'

export interface Shipped { bytes: number; meshBytes: number; triangles: number; drawCalls: number; meshes: Record<string, number> }

export const RUNTIME = {
  shading: 'Every material is KHR_materials_unlit (three: MeshBasicMaterial) with its KTX2 atlas embedded (KHR_texture_basisu: the GLTFLoader needs a KTX2Loader). The light is baked in; light the fighters with a key along `sun.direction`.',
  hideForSideCamera: [] as string[],
  shadowCatcher: { node: 'shadow_catcher', radius: 14, y: 0.004, note: "an invisible disc over the sand (the ring and the walk-on from gate_*_start): give it a THREE.ShadowMaterial (opacity about 0.3) for the fighters' shadows" },
  sky: { radius: 600, centre: [0, 12, 0], note: "two half-domes (sky_front looks toward -Z: north, the Patrons' box; sky_back toward +Z), 600 m out so the fly-in's high start sees little parallax: keep the camera far plane at 1000 m (ART.duel.far)" },
  anisotropy: 'set map.anisotropy to 4-8 on the ground atlases (ring, apron_w, apron_e; plaza and land for the fly-in). duel3d.ts\'s /ring|apron|mid|far/ already catches ring and the aprons.',
  cameraRadius: 'cameras on the sand stay within cameraRadius (18.5 m) of the centre: the sand is an ellipse 54 x 40 m (the podium wall at 27 m on x, 20 m on y; the gate ramps and statues start beyond 20 m). The ring barrier stands at 6.0-6.35 m (curb 0.24 m, rope about 0.55 m, posts 0.62 m, the four gate posts 1.05 m): outside the ring keep the camera above about 1.2 m within 7.5 m of the centre.',
  lite: 'crown_lite.glb: the same layout with a coarser bowl (lbowl_low, lbowl_high: its own bake, painted crowd included), 750-triangle statues (lstatues), no urns, archivolts, keystones, half-columns or gallery columns, and the trees and market stalls painted into the Lite sky (the town stays: the fly-in starts above it); every Lite atlas is at most 1024 px.',
  ring: 'the duel ring: a marble curb (r 6.0-6.35 m) with bronze posts and a crimson rope, open 2.5 m wide on the A-B (x) axis where the fighters walk in: the fence a fighter is knocked into.',
  gates: 'gate_A/B = the openings in the ring barrier (x = -/+6.6 m); gate_A/B_start = 13 m out on the sand (a walk like the Guild\'s); tunnel_A/B = under each raised portcullis at the top of its ramp (x = -/+24.3, y = 0.55), for a longer walk-on (about 22 m) straight out of the gate.',
  flyIn: 'cam_fly_0 ... cam_fly_5: each node looks down its local -Z (three camera convention); `t` is seconds (6 s), `fovDeg` the vertical field of view, framed for a tall portrait phone; interpolate eye and target with a centripetal Catmull-Rom curve. It starts high above the town south-west of the arena, crosses the south rim (where the awnings are furled) well above the masts, dives over the south stands and ends low by spawn A looking at the ring. `flyInClearance` is the measured closest approach to any surface.',
  seats: "`seats`: the live crowd's spots only (the rest of the bowl is painted, see `crowd`). `p` = the seat top (glTF frame, metres), `yaw` = three's rotation.y with the person facing (sin yaw, 0, cos yaw), toward the ring centre; `row` = 0 (the front marble row) or 1 (the second; in the box its two benches); `section` = north / south (the long sides), west (gate A's end) / east (gate B's end), patrons (the Patrons' box); `kind` = seat; `lite` = kept in Lite (every other spot of each row).",
  crowd: "Fame fills `seats` (the front rows nearest the battle cameras); every other row is a painted crowd baked into the bowl's atlases (crowd.paintedRows), so the stands are never empty. The painted crowd leans teal toward gate A and coral toward gate B. Rows the live crowd leaves empty show bare marble.",
}

const SHOTS: { file: string; q: string }[] = [
  { file: 'three_battle', q: 'view=battle&w=540&h=960&dpr=2' },
  { file: 'three_lite_battle', q: 'view=battle&tier=lite&w=540&h=960&dpr=2' },
  { file: 'three_phone_battle', q: 'view=battle&w=412&h=892&dpr=2.625' },
  { file: 'three_battle_wide', q: 'view=battle_wide&w=960&h=540&dpr=2' },
  { file: 'three_lite_battle_wide', q: 'view=battle_wide&tier=lite&w=960&h=540&dpr=2' },
  { file: 'three_shoulder', q: 'view=shoulder&w=600&h=800' },
  { file: 'three_gate', q: 'view=gate&w=600&h=800' },
  { file: 'three_establish', q: 'view=establish&w=600&h=800' },
  { file: 'three_fly0', q: 'view=fly0&w=450&h=800' },
  { file: 'three_lite_fly0', q: 'view=fly0&tier=lite&w=450&h=800' },
]

async function waitFor(url: string, ms: number): Promise<boolean> {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) {
    try {
      if ((await fetch(url)).ok) return true
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 400))
  }
  return false
}

export async function runShots(ROOT: string, PUB: string, cp: { spawn: typeof import('node:child_process').spawn; execFileSync: typeof import('node:child_process').execFileSync }): Promise<void> {
  const REVIEW = join(ROOT, 'art-review', 'arena-crown')
  const PORT = 5176
  writeFileSync(join(REVIEW, 'viewer.html'), '<!doctype html><html><head><meta charset="utf-8"><title>Crown viewer</title><style>html,body{margin:0;background:#20242a}canvas{display:block}</style></head><body><script type="module" src="./viewer.js"></script></body></html>\n')
  const win = process.platform === 'win32'
  const server: ChildProcess = cp.spawn(win ? 'npx.cmd' : 'npx', ['vite', '--config', 'vite.perf.config.ts', '--port', String(PORT), '--strictPort'], { cwd: ROOT, stdio: 'ignore', shell: win })
  const info: Record<string, unknown> = {}
  try {
    if (!(await waitFor(`http://localhost:${PORT}/wildsong-ranch/art-review/arena-crown/viewer.html`, 120_000))) throw new Error('the dev server did not start')
    const b = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--enable-webgl', '--disable-gpu-sandbox'] })
    try {
      for (const s of SHOTS) {
        const page = await b.newPage({ viewport: { width: 1200, height: 2000 }, deviceScaleFactor: 1 })
        page.on('pageerror', (e) => console.error('page error:', e.message))
        await page.goto(`http://localhost:${PORT}/wildsong-ranch/art-review/arena-crown/viewer.html?${s.q}`)
        await page.waitForFunction(() => (window as unknown as { __arena?: { ready: boolean } }).__arena?.ready === true, null, { timeout: 240_000 })
        const r = await page.evaluate(() => (window as unknown as { __arena: { shot(): { png: string; calls: number; triangles: number; textures: number; ms: number } } }).__arena.shot())
        writeFileSync(join(REVIEW, `${s.file}.png`), Buffer.from(r.png.slice(r.png.indexOf(',') + 1), 'base64'))
        info[s.file] = { calls: r.calls, triangles: r.triangles, textures: r.textures, ms: Math.round(r.ms * 10) / 10 }
        console.log('shot', s.file, JSON.stringify(info[s.file]))
        await page.close()
      }
      writeFileSync(join(REVIEW, 'shots.json'), JSON.stringify(info, null, 1) + '\n')
      writeFileSync(join(REVIEW, 'index.html'), sheetHtml(REVIEW, PUB, info))
      const sheet = await b.newPage({ viewport: { width: 1840, height: 1200 }, deviceScaleFactor: 1 })
      await sheet.goto(`http://localhost:${PORT}/wildsong-ranch/art-review/arena-crown/index.html`)
      await sheet.waitForLoadState('networkidle')
      await sheet.screenshot({ path: join(REVIEW, 'sheet.png'), fullPage: true })
      console.log('sheet', join(REVIEW, 'sheet.png'))
    } finally {
      await b.close()
    }
  } finally {
    if (win && server.pid) {
      try {
        cp.execFileSync('taskkill', ['/PID', String(server.pid), '/F', '/T'], { stdio: 'ignore' })
      } catch {
        /* gone */
      }
    } else server.kill()
  }
}

interface Row { triangles: number; drawCalls: number; downloadBytes: number; meshBytes: number; webpEquivalentBytes: number }

function sheetHtml(REVIEW: string, PUB: string, info: Record<string, unknown>): string {
  const side = JSON.parse(readFileSync(join(PUB, 'crown.json'), 'utf8')) as {
    budget: { full: Row; lite: Row }; problems: string[]; sources: { id: string; authors: string[] }[]; cameraRadius: number
    crowd: { liveSeats: number; liveSeatsLite: number; paintedSpectators: number }; flyInClearance: { minMetres: number; nearest: string; minBeforeFaceOffMetres: number }
  }
  const mb = (n: number) => (n / 1048576).toFixed(2) + ' MB'
  const fig = (src: string, cap: string, w = 300, h = 400) => (existsSync(join(REVIEW, src)) ? `<figure><img src="${src}" width="${w}" height="${h}"><figcaption>${cap}</figcaption></figure>` : `<figure><div class="miss" style="width:${w}px;height:${h}px"></div><figcaption>${cap} (missing)</figcaption></figure>`)
  const si = (k: string) => {
    const s = info[k] as { calls?: number; triangles?: number } | undefined
    return s ? ` · ${s.calls} draws, ${(s.triangles ?? 0).toLocaleString()} tris drawn` : ''
  }
  const f = side.budget.full
  const l = side.budget.lite
  return `<!doctype html><html><head><meta charset="utf-8"><title>Crown Amphitheatre review</title><style>
body{margin:0;padding:16px 20px;background:#e4e6ea;font:14px/1.4 system-ui,Segoe UI,sans-serif;color:#1d2126;width:1800px}
h1{font-size:21px;margin:0 0 4px} h2{font-size:15px;margin:14px 0 6px} .row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-start}
figure{margin:0;background:#fff;border-radius:8px;padding:6px;box-shadow:0 1px 2px #0002} figure img{display:block;border-radius:4px;object-fit:cover}
figcaption{font-size:12px;margin-top:4px;max-width:300px} .miss{background:#bbb;border-radius:4px}
table{border-collapse:collapse;background:#fff;border-radius:8px;box-shadow:0 1px 2px #0002} td,th{padding:4px 10px;border-bottom:1px solid #e4e6ea;text-align:left;font-size:13px} th{background:#f2f3f5}
</style></head><body>
<h1>The Crown Amphitheatre: Cycles reference beside the game's three.js render</h1>
<p>Grey capsules = 1 m stand-ins at spawn A (−2.4 m) and spawn B (+2.4 m). The game draws the arena unlit with its light baked in (one texture, one draw per atlas); three.js uses Neutral tone mapping. Cameras on the sand stay within ${side.cameraRadius} m of the centre. Live crowd seats: ${side.crowd.liveSeats} (Lite ${side.crowd.liveSeatsLite}); painted spectators baked into the stands: about ${side.crowd.paintedSpectators.toLocaleString()}. Fly-in closest approach to any surface: ${side.flyInClearance.minBeforeFaceOffMetres} m until the final drop to the face-off (${side.flyInClearance.minMetres} m including it, ${side.flyInClearance.nearest}).</p>
<h2>1 · Side-on battle view (long lens from the camera radius, 1080 × 1920)</h2>
<div class="row">${fig('cycles_battle.png', 'Cycles, the source scene path traced', 270, 480)}${fig('three_battle.png', 'three.js, Full' + si('three_battle'), 270, 480)}${fig('three_lite_battle.png', 'three.js, Lite' + si('three_lite_battle'), 270, 480)}${fig('shipped_full_battle.png', 'Cycles, the shipped Full meshes drawn unlit', 270, 480)}${fig('three_phone_battle.png', 'three.js at phone size (412 × 892 CSS px, 2.625×)', 222, 480)}</div>
<h2>1b · Side-on, the phone held sideways (low at the side, long lens from inside the camera radius, 1920 × 1080)</h2>
<div class="row">${fig('cycles_battle_wide.png', 'Cycles', 576, 324)}${fig('three_battle_wide.png', 'three.js, Full' + si('three_battle_wide'), 576, 324)}${fig('three_lite_battle_wide.png', 'three.js, Lite' + si('three_lite_battle_wide'), 576, 324)}</div>
<h2>2 · Over spawn A's shoulder toward B · 3 · Gate B from the sand</h2>
<div class="row">${fig('cycles_shoulder.png', 'Cycles')}${fig('three_shoulder.png', 'three.js, Full' + si('three_shoulder'))}${fig('cycles_gate.png', 'Cycles')}${fig('three_gate.png', 'three.js, Full' + si('three_gate'))}</div>
<h2>4 · Establishing · 5 · Fly-in start (portrait)</h2>
<div class="row">${fig('cycles_establish.png', 'Cycles')}${fig('three_establish.png', 'three.js, Full' + si('three_establish'))}${fig('cycles_fly0.png', 'Cycles', 225, 400)}${fig('three_fly0.png', 'three.js, Full: cam_fly_0', 225, 400)}${fig('three_lite_fly0.png', 'three.js, Lite: cam_fly_0', 225, 400)}</div>
<h2>Budgets (measured)</h2>
<table><tr><th></th><th>Triangles</th><th>Draw calls (≤ 40)</th><th>Download (.glb, KTX2 inside)</th><th>of which mesh</th><th>Same with WebP textures</th></tr>
<tr><td>Full</td><td>${f.triangles.toLocaleString()} (≤ 150,000)</td><td>${f.drawCalls}</td><td>${mb(f.downloadBytes)} (≤ 12 MB)</td><td>${mb(f.meshBytes)}</td><td>${mb(f.webpEquivalentBytes)}</td></tr>
<tr><td>Lite</td><td>${l.triangles.toLocaleString()} (≤ 60,000)</td><td>${l.drawCalls}</td><td>${mb(l.downloadBytes)} (≤ 4 MB)</td><td>${mb(l.meshBytes)}</td><td>${mb(l.webpEquivalentBytes)}</td></tr></table>
<p>${side.problems.length ? 'Problems: ' + side.problems.join('; ') : 'Within every budget.'}</p>
<p style="color:#555">CC0 sources (Poly Haven): ${side.sources.map((s) => `${s.id} (${s.authors.join(', ')})`).join(' · ')}. Statues: our own Puddlepup model, posed and turned to marble and bronze.</p>
</body></html>`
}
