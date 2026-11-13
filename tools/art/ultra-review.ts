/**
 * Art 2.1 review sheet for one Ultra look (docs/ART_2_DETAIL.md §8, §9; ART_2_PLAN §6), for any breed.
 *
 *   node tools/art/ultra-review.ts <breed> [--no-shots]
 *
 * Renders public/models/monsters-ultra/<breed>.glb in the film look (the Performance check's renderer, src/art3d/perf/,
 * through tools/art/ultra-viewer/) in headless Chrome on this PC's GPU: the turnaround angles, the head, the clips' key
 * frames, every variant, the Lite copy, and 64 / 100 / 200 px; framed from the sidecar's height and centre. Lays them
 * beside the reference pictures (chatgpt/monsters/<nn>-<breed>/, crops given as fractions of each picture) and the
 * Blender sheets (tools/blender/out/<breed>-ultra/review/), with the measured budget, and saves
 * art-review/<breed>-ultra/sheet.png. A grown form (`<breed>-grown`, e.g. hearthwing-grown) uses its breed's folder
 * and the `grown-*.png` pictures (the grown turnaround's four views, wings spread last).
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import type { Browser, Page } from '@playwright/test'
import { BASE, framing, isGrown, launch, readSide, refDir, refPrefix, ROOT, savePng, startServer, stopServer, viewerPage, type UltraSide } from './ultra-serve.ts'

const args = process.argv.slice(2)
const breed = args.find((a) => !a.startsWith('--')) ?? 'puddlepup'
const OUT = join(ROOT, 'art-review', `${breed}-ultra`)
const SHOTS = join(OUT, 'shots')

interface ShotOpts {
  az?: number; el?: number; target?: [number, number, number]; frame?: number; size?: number; clip?: string; t?: number; variant?: string
  colorAttribute?: string; format?: string; dpr?: number; raw?: boolean; lite?: boolean; studio?: { focus: number[]; reach: number }
}

const slug = (vid: string) => vid.replace(/[^a-z0-9-]+/gi, '_')

function shotList(side: UltraSide): [string, ShotOpts][] {
  const F = framing(side)
  const B: ShotOpts = { target: F.body.target, frame: F.body.frame, studio: F.studio }
  const HEAD: ShotOpts = { target: F.head.target, frame: F.head.frame, studio: F.studio }
  const variantShots: [string, ShotOpts][] = Object.entries(side.variants).flatMap(([vid, v]) => [
    [`variant_${slug(vid)}_34`, { ...B, az: 35, el: 14, variant: vid, colorAttribute: v.colorAttribute }],
    [`variant_${slug(vid)}_back`, { ...B, az: 160, el: 14, variant: vid, colorAttribute: v.colorAttribute }],
  ] as [string, ShotOpts][])
  return [
    ['turn_front', { ...B, az: 0, el: 6 }],
    ['turn_34', { ...B, az: 35, el: 14 }],
    ['turn_side', { ...B, az: 90, el: 4 }],
    ['turn_back', { ...B, az: 180, el: 10 }],
    ['turn_34_other', { ...B, az: -35, el: 14 }],
    ['head_34', { ...HEAD, az: 26, el: 12 }],
    ['head_front', { ...HEAD, az: 0, el: 4 }],
    ['head_side', { ...HEAD, az: 90, el: 4 }],
    ['webp_34', { ...B, az: 35, el: 14, format: 'webp' }],
    ['raw_34', { ...B, az: 35, el: 14, raw: true }],
    ['lite_34', { ...B, az: 35, el: 14, lite: true }],
    ['lite_front', { ...B, az: 0, el: 6, lite: true }],
    ...variantShots,
    ['s64', { ...B, az: 35, el: 14, size: 64 }],
    ['s64_front', { ...B, az: 0, el: 6, size: 64 }],
    ['s100', { ...B, az: 35, el: 14, size: 100 }],
    ['s200', { ...B, az: 35, el: 14, size: 200 }],
    ['clip_battle_idle', { ...B, az: 35, el: 14, clip: 'battle_idle', t: 0.25, size: 500 }],
    ['clip_strafe_l', { ...B, az: 20, el: 14, clip: 'strafe_l', t: 0.25, size: 500 }],
    ['clip_strafe_r', { ...B, az: 20, el: 14, clip: 'strafe_r', t: 0.75, size: 500 }],
    ['clip_sidestep_l', { ...B, az: 0, el: 10, clip: 'sidestep_l', t: 0.5, size: 500 }],
    ['clip_sidestep_r', { ...B, az: 0, el: 10, clip: 'sidestep_r', t: 0.5, size: 500 }],
    // the wind-up too: a slam's rear-up, a kick's spin, a swipe's draw
    ['clip_strike_windup', { ...B, az: 35, el: 14, clip: 'strike', t: 0.3, size: 500 }],
    ['clip_strike', { ...B, az: 70, el: 10, clip: 'strike', t: 0.54, size: 500, frame: F.low.frame }],
    ['clip_hit', { ...B, az: 35, el: 14, clip: 'hit', t: 0.3, size: 500 }],
    ['clip_hit_heavy', { ...B, az: 35, el: 14, clip: 'hit_heavy', t: 0.3, size: 500 }],
    ['clip_ko', { ...B, az: 35, el: 20, clip: 'ko', t: 0.99, size: 500, frame: F.low.frame, target: F.low.target }],
    ['clip_win', { ...B, az: 35, el: 14, clip: 'win', t: 0.2, size: 500 }],
    ['clip_walk', { ...B, az: 90, el: 6, clip: 'walk', t: 0.3, size: 500 }],
    ['clip_blink', { ...HEAD, az: 20, el: 8, clip: 'blink', t: 0.45, size: 500 }],
    // batch 2: a rig with wings or a trunk also shows them open (cast) and the happy idle (a trunk's bud open)
    ...(hasWingsOrTrunk(side) ? [
      ['clip_cast', { ...B, az: 20, el: 14, clip: 'cast', t: 0.5, size: 500 }],
      ['clip_idle_happy', { ...B, az: 35, el: 14, clip: 'idle_happy', t: 0.3, size: 500 }],
    ] as [string, ShotOpts][] : []),
    // Nov 12: a rig with the flight clips (plans/quadruped.py FLY_CLIPS) shows them, framed for wings about 2.5 x the height
    ...(hasFlight(side) ? flightShots(side, F) : []),
  ]
}

/** The flight clips (fly, fly_takeoff, fly_cast, fly_land): plans/quadruped.py adds them only to a rig with wings. */
function hasFlight(side: UltraSide): boolean {
  return 'fly' in (side.clips ?? {})
}

function flightShots(side: UltraSide, F: ReturnType<typeof framing>): [string, ShotOpts][] {
  const h = side.restHeight
  const W: ShotOpts = { target: [0, F.body.target[1], Math.round(0.75 * h * 100) / 100], frame: Math.round(3.9 * h * 100) / 100, studio: F.studio, size: 500 }
  return [
    ['fly_front', { ...W, az: 0, el: 6, clip: 'fly', t: 0.2 }],
    ['fly_side', { ...W, az: 90, el: 6, clip: 'fly', t: 0.0 }],
    ['fly_top', { ...W, az: 35, el: 14, clip: 'fly', t: 0.0 }],
    ['clip_fly', { ...W, az: 35, el: 14, clip: 'fly', t: 0.2 }],
    ['clip_fly_up', { ...W, az: 35, el: 14, clip: 'fly', t: 0.65 }],
    ['clip_fly_takeoff', { ...W, az: 35, el: 14, clip: 'fly_takeoff', t: 0.25 }],
    ['clip_fly_takeoff_leap', { ...W, az: 35, el: 14, clip: 'fly_takeoff', t: 0.45 }],
    ['clip_fly_cast', { ...W, az: 35, el: 14, clip: 'fly_cast', t: 0.5 }],
    ['clip_fly_land', { ...W, az: 35, el: 14, clip: 'fly_land', t: 0.3 }],
    ['clip_fly_land_touch', { ...W, az: 35, el: 14, clip: 'fly_land', t: 0.66 }],
    // the tail tip close up (Nov 12: the spade's shape is an originality check)
    ['tail_tip', { target: [0, Math.round(((side.bounds.max as number[])[1] - 0.12 * h) * 100) / 100, Math.round(0.5 * h * 100) / 100], frame: Math.round(0.55 * h * 100) / 100, studio: F.studio, az: 120, el: 15, size: 500 }],
  ]
}

/** Wings (socket_wing_L) or a trunk (socket_trunk): plans/quadruped.py adds those sockets only with the option. */
function hasWingsOrTrunk(side: UltraSide): boolean {
  const sockets = (side.sockets ?? {}) as Record<string, unknown>
  return 'socket_wing_L' in sockets || 'socket_trunk' in sockets
}

/** The cast and happy-idle labels name only the parts this breed has (wings, a trunk, a bud: socket_bud). */
function partLabels(side: UltraSide): { cast: string; happy: string } {
  const sockets = (side.sockets ?? {}) as Record<string, unknown>
  const cast = [('socket_wing_L' in sockets) && 'wings open', ('socket_trunk' in sockets) && 'trunk raised'].filter(Boolean)
  return { cast: cast.length ? `cast (${cast.join(', ')})` : 'cast', happy: 'socket_bud' in sockets ? 'idle_happy (bud open)' : 'idle_happy' }
}

type ShotInfo = { ok: boolean; triangles?: number; cards?: number; error?: string; clips?: string[] }

async function shots(page: Page, list: [string, ShotOpts][]): Promise<Record<string, ShotInfo>> {
  mkdirSync(SHOTS, { recursive: true })
  const info: Record<string, ShotInfo> = {}
  for (const [file, o] of list) {
    try {
      const r = await page.evaluate((x) => (window as unknown as { __ultra: { shot(o: unknown): Promise<{ png: string; triangles: number; cards: number; clips: string[] }> } }).__ultra.shot(x), { look: breed, ...o })
      writeFileSync(join(SHOTS, `${file}.png`), savePng(r.png))
      info[file] = { ok: true, triangles: r.triangles, cards: r.cards, clips: file === 'turn_front' ? r.clips : undefined }
      console.log('shot', file, r.triangles, 'tris', r.cards, 'cards')
    } catch (e) {
      info[file] = { ok: false, error: (e as Error).message.split('\n')[0] }
      console.warn('shot failed', file, info[file]!.error)
    }
  }
  return info
}

// ---------------------------------------------------------------------------- the reference pictures
const REF_DIR = refDir(breed)
const REF_URL = REF_DIR ? `../../${relative(ROOT, REF_DIR).replace(/\\/g, '/')}/` : ''
/** Crops as fractions (x, y, w, h) of each picture, so pictures of any size line up (Puddlepup's P1 boxes). */
const CROP = {
  turnFront: [0.006, 0.186, 0.323, 0.595], turnSide: [0.308, 0.186, 0.443, 0.595], turnBack: [0.706, 0.186, 0.299, 0.595],
  whole: [0, 0, 1, 1], faceNeutral: [0, 0, 0.25, 0.299], detailHead: [0, 0, 0.332, 0.417], detailEye: [0.334, 0, 0.332, 0.417],
} as const satisfies Record<string, readonly [number, number, number, number]>
/** A grown form's turnaround (grown-2-turnaround.png, 2:1): front, side, back and the wings spread, left to right. */
const GROWN_TURN = {
  turnFront: [0.0, 0.2, 0.165, 0.58], turnSide: [0.16, 0.2, 0.335, 0.58], turnBack: [0.49, 0.2, 0.16, 0.58], turnWings: [0.64, 0.2, 0.36, 0.58],
} as const satisfies Record<string, readonly [number, number, number, number]>
type Crop = readonly [number, number, number, number]
const TURN: { turnFront: Crop; turnSide: Crop; turnBack: Crop; turnWings?: Crop } = isGrown(breed) ? GROWN_TURN : CROP
/** A reference picture's file name: `grown-` first for a grown form (refPrefix). */
const pic = (name: string) => `${refPrefix(breed)}${name}`

function pngSize(file: string): [number, number] {
  const b = readFileSync(join(REF_DIR!, file))
  return [b.readUInt32BE(16), b.readUInt32BE(20)]
}
function crop(file: string, f: readonly [number, number, number, number], D: number): string {
  const [nw, nh] = pngSize(file)
  const [x, y, w, h] = [f[0] * nw, f[1] * nh, f[2] * nw, f[3] * nh]
  const s = D / Math.max(w, h)
  return `background:#8a8b8f url('${REF_URL}${file}') no-repeat; background-size:${(nw * s).toFixed(1)}px ${(nh * s).toFixed(1)}px; background-position:${(-x * s + (D - w * s) / 2).toFixed(1)}px ${(-y * s + (D - h * s) / 2).toFixed(1)}px; width:${D}px; height:${D}px;`
}
const ref = (f: string, r: readonly [number, number, number, number], cap: string, D: number) =>
  REF_DIR && existsSync(join(REF_DIR, f)) ? `<figure class="ref"><div class="img" style="${crop(f, r, D)}"></div><figcaption>${cap}</figcaption></figure>` : ''
const img = (src: string, cap: string, D: number) => `<figure><img src="${src}" width="${D}" height="${D}"><figcaption>${cap}</figcaption></figure>`
const wide = (src: string, cap: string, W: number) => `<figure><img src="${src}" width="${W}"><figcaption>${cap}</figcaption></figure>`
const mb = (n: number) => `${(n / 1048576).toFixed(2)} MB`

interface Budget {
  triangles: number; trianglesByMesh: Record<string, number>; cards: number; cardLayers: number; joints: number; animations: number; animationBytes: number
  download: { glb: number; ktx2: { body: number; variants: number }; webp: { body: number; variants: number }; totalKtx2: number; totalWebp: number }
  problems: string[]
}
interface Lite { bytes: number; triangles: number; trianglesByMesh: Record<string, number>; atlasPx: number; build: string; problems: string[] }

function sheetHtml(side: UltraSide, info: Record<string, ShotInfo>, verdicts: string): string {
  const D = 280
  const b = side.budget as Budget
  const lite = side.lite as Lite | undefined
  const vids = Object.keys(side.variants)
  const ok = (f: string) => info[f]?.ok === true
  const shotOr = (f: string, cap: string, d = D) => (ok(f) ? img(`shots/${f}.png`, cap, d) : `<figure><div class="img" style="width:${d}px;height:${d}px"></div><figcaption>${cap}: ${info[f]?.error ?? 'missing'}</figcaption></figure>`)
  const blender = join(ROOT, 'tools', 'blender', 'out', `${breed}-ultra`, 'review')
  const bl = (f: string, cap: string) => (existsSync(join(blender, f)) ? wide(`../../tools/blender/out/${breed}-ultra/review/${f}`, cap, 760) : '')
  const blVariants = existsSync(blender) ? readdirSync(blender).filter((f) => /^variant.*\.png$/.test(f)) : []
  const clipRows = Object.entries(side.clips)
    .filter(([n]) => ['walk', 'battle_idle', 'step_fwd', 'step_back', 'strafe_l', 'strafe_r', 'sidestep_l', 'sidestep_r', 'strike', 'hit', 'hit_heavy', 'ko', 'win', 'blink'].includes(n))
    .map(([n, c]) => `<tr><td>${n}</td><td>${c.seconds.toFixed(3)} s</td><td>${c.rootSpeed ? `${c.rootSpeed} m/s ${c.rootDir ? `[${c.rootDir.join(', ')}]` : ''}` : ''}</td><td>${c.markers.map((m) => `${m.name} ${m.t}`).join(', ')}</td></tr>`)
    .join('')
  const variantRows = vids.map((vid) => `<div class="row">${ref(`variant-${vid}.png`, CROP.whole, `Reference: ${vid}`, D)}${shotOr(`variant_${slug(vid)}_34`, `${vid}, three-quarter`)}${shotOr(`variant_${slug(vid)}_back`, `${vid}, back`)}</div>`).join('')
  return `<!doctype html><html><head><meta charset="utf-8"><title>${breed} Ultra review</title><style>
body{margin:0;padding:18px 22px;background:#e4e6ea;font:14px/1.4 system-ui,Segoe UI,sans-serif;color:#1d2126;width:2440px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:18px 0 6px} p{margin:2px 0 8px;max-width:2300px}
.row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px} figure{margin:0;background:#fff;border-radius:8px;padding:6px;box-shadow:0 1px 2px #0002}
figure.ref{background:#f3ead8} figure img,.img{display:block;border-radius:4px;background:#8a8b8f} figcaption{font-size:12.5px;margin-top:5px;max-width:${D}px}
.small{display:flex;gap:14px;align-items:flex-end;background:#fff;border-radius:8px;padding:10px;box-shadow:0 1px 2px #0002}
table{border-collapse:collapse;background:#fff;border-radius:8px;box-shadow:0 1px 2px #0002} td,th{padding:4px 10px;border-bottom:1px solid #e4e6ea;text-align:left;font-size:13px} th{background:#f2f3f5}
.cols{display:flex;gap:20px;align-items:flex-start;flex-wrap:wrap} pre{white-space:pre-wrap;font-size:12.5px;background:#fff;padding:10px;border-radius:8px;max-width:1150px}
</style></head><body>
<h1>${breed}, Art 2.1 Ultra: the whole monster, rigged and animated</h1>
<p>three.js r186 on this PC's GPU, the Performance check's film renderer (Ultra effects: soft key-light shadow, GTAO, bloom, grading, 4× MSAA; no outlines), KTX2 textures (ETC1S colour and ORM, UASTC normals at 1024²). Beige frames are the reference pictures${REF_DIR ? ` (${relative(ROOT, REF_DIR).replace(/\\/g, '/')})` : ' (none found)'}. ${b.triangles.toLocaleString()} triangles · ${b.cards.toLocaleString()} fur cards in ${b.cardLayers} layers · ${b.joints} joints · ${b.animations} clips · rest height ${side.restHeight} m for ${side.heightUnits} units · build ${String(side.build)}.</p>
<h2>1 · Turnaround</h2>
<div class="row">
${ref(pic('2-turnaround.png'), TURN.turnFront, 'Reference: front', D)}${shotOr('turn_front', 'front')}
${ref(pic('2-turnaround.png'), TURN.turnSide, 'Reference: side', D)}${shotOr('turn_side', 'side')}
${ref(pic('2-turnaround.png'), TURN.turnBack, 'Reference: back', D)}${shotOr('turn_back', 'back')}
${shotOr('turn_34', 'three-quarter')}${ref(pic('1-hero.png'), CROP.whole, 'Reference: hero', D)}
</div>
<h2>2 · Head</h2>
<div class="row">
${ref(pic('3-faces.png'), CROP.faceNeutral, 'Reference: neutral', D)}${shotOr('head_front', 'front')}${shotOr('head_34', 'three-quarter')}${shotOr('head_side', 'side')}
${ref(pic('4-details.png'), CROP.detailHead, 'Reference: head detail', D)}${ref(pic('4-details.png'), CROP.detailEye, 'Reference: eye', D)}
</div>
<h2>3 · Clips (key frames)</h2>
<div class="row">
${shotOr('clip_battle_idle', 'battle_idle', 230)}${shotOr('clip_walk', 'walk', 230)}${shotOr('clip_strafe_l', 'strafe_l', 230)}${shotOr('clip_strafe_r', 'strafe_r', 230)}${shotOr('clip_sidestep_l', 'sidestep_l (mid-hop)', 230)}${shotOr('clip_sidestep_r', 'sidestep_r (mid-hop)', 230)}
${shotOr('clip_strike_windup', 'strike (wind-up)', 230)}${shotOr('clip_strike', 'strike (impact)', 230)}${shotOr('clip_hit', 'hit', 230)}${shotOr('clip_hit_heavy', 'hit_heavy', 230)}${shotOr('clip_ko', 'ko (end)', 230)}${shotOr('clip_win', 'win (airborne)', 230)}${shotOr('clip_blink', 'blink (closed)', 230)}
</div>
${hasWingsOrTrunk(side) ? `<div class="row">${shotOr('clip_cast', partLabels(side).cast, 230)}${shotOr('clip_idle_happy', partLabels(side).happy, 230)}${TURN.turnWings ? ref(pic('2-turnaround.png'), TURN.turnWings, 'Reference: wings spread', 230) : ''}</div>` : ''}
${hasFlight(side) ? `<div class="row">${shotOr('fly_front', 'fly: wings spread, front (mid-downstroke)', 230)}${shotOr('fly_side', 'fly: side (top of the stroke)', 230)}${shotOr('fly_top', 'fly: top of the upstroke', 230)}${shotOr('clip_fly', 'fly (mid-downstroke)', 230)}${shotOr('clip_fly_up', 'fly (upstroke)', 230)}</div>
<div class="row">${shotOr('clip_fly_takeoff', 'fly_takeoff (crouch, wings up)', 230)}${shotOr('clip_fly_takeoff_leap', 'fly_takeoff (leap)', 230)}${shotOr('clip_fly_cast', 'fly_cast (release)', 230)}${shotOr('clip_fly_land', 'fly_land (flare)', 230)}${shotOr('clip_fly_land_touch', 'fly_land (touch down)', 230)}${shotOr('tail_tip', 'the tail tip (spade)', 230)}</div>` : ''}
<h2>4 · Variants (${vids.length})</h2>
${variantRows || '<p>No variants.</p>'}
<h2>5 · Other side, formats and the Lite copy</h2>
<div class="row">${shotOr('turn_34_other', 'base, other side')}${shotOr('webp_34', 'WebP textures (the rest are KTX2)')}${shotOr('raw_34', 'the .glb materials as loaded (no card edge fade)')}${shotOr('lite_34', `Lite (${lite ? `${mb(lite.bytes)}, ${lite.triangles.toLocaleString()} triangles` : 'not shipped'})`)}${shotOr('lite_front', 'Lite, front')}</div>
<h2>6 · Phone sizes</h2>
<div class="cols"><div class="small">
${shotOr('s64', '64 px', 64)}${shotOr('s64_front', '64 px, front', 64)}${shotOr('s100', '100 px', 100)}${shotOr('s200', '200 px', 200)}
${ref(pic('1-hero.png'), CROP.whole, 'ref 64', 64)}${ref(pic('1-hero.png'), CROP.whole, 'ref 100', 100)}
</div>
<table><tr><th colspan="2">What ships (measured)</th></tr>
<tr><td>Triangles</td><td>${b.triangles.toLocaleString()} (${Object.entries(b.trianglesByMesh).map(([k, v]) => `${k} ${v.toLocaleString()}`).join(' · ')})</td></tr>
<tr><td>Fur cards</td><td>${b.cards.toLocaleString()} in ${b.cardLayers} layers</td></tr>
<tr><td>Joints</td><td>${b.joints}</td></tr>
<tr><td>Mesh + clips .glb (meshopt)</td><td>${mb(b.download.glb)} (animations ${mb(b.animationBytes)})</td></tr>
<tr><td>Body atlas (colour + normal + ORM)</td><td>KTX2 ${mb(b.download.ktx2.body)} · WebP ${mb(b.download.webp.body)}</td></tr>
<tr><td>Variant colour maps (${vids.length})</td><td>KTX2 ${mb(b.download.ktx2.variants)} · WebP ${mb(b.download.webp.variants)}</td></tr>
<tr><td><b>Download, everything</b></td><td><b>KTX2 ${mb(b.download.totalKtx2)} · WebP ${mb(b.download.totalWebp)}</b> (cap 8 MB)</td></tr>
<tr><td>Lite copy</td><td>${lite ? `${mb(lite.bytes)} (cap 1.5 MB) · ${lite.triangles.toLocaleString()} triangles (body ${(lite.trianglesByMesh.lo_body ?? 0).toLocaleString()}) · ${lite.atlasPx}² WebP · build ${lite.build}` : 'not shipped'}</td></tr>
<tr><td>Budget problems</td><td>${b.problems.length ? b.problems.join('; ') : 'none'}</td></tr>
</table>
<table><tr><th>clip</th><th>length</th><th>root speed (model m/s, glTF dir)</th><th>markers</th></tr>${clipRows}</table>
</div>
${verdicts ? `<h2>7 · Fresh-eyes verdicts</h2><pre>${verdicts}</pre>` : ''}
<h2>8 · Blender review sheets (EEVEE, the same baked maps)</h2>
<div class="row">${bl('turnaround.png', 'turnaround')}${bl('poses.png', 'key poses')}${blVariants.map((f) => bl(f, f.replace(/\.png$/, '').replace(/_/g, ' '))).join('')}${bl('head.png', 'head')}</div>
</body></html>`
}

async function main(): Promise<void> {
  mkdirSync(OUT, { recursive: true })
  const side = readSide(breed)
  const infoPath = join(OUT, 'shots.json')
  let info: Record<string, ShotInfo> = existsSync(infoPath) ? JSON.parse(readFileSync(infoPath, 'utf8')) : {}
  const verdictPath = join(OUT, 'verdicts.txt')
  const verdicts = existsSync(verdictPath) ? readFileSync(verdictPath, 'utf8').replace(/</g, '&lt;') : ''
  const server = await startServer()
  try {
    const b: Browser = await launch()
    try {
      if (!args.includes('--no-shots')) {
        info = await shots(await viewerPage(b), shotList(side))
        writeFileSync(infoPath, JSON.stringify(info, null, 1) + '\n')
      }
      writeFileSync(join(OUT, 'index.html'), sheetHtml(side, info, verdicts))
      const sheet = await b.newPage({ viewport: { width: 2484, height: 1400 }, deviceScaleFactor: 1 })
      await sheet.goto(`${BASE}art-review/${breed}-ultra/index.html`)
      await sheet.waitForLoadState('networkidle')
      await sheet.screenshot({ path: join(OUT, 'sheet.png'), fullPage: true })
      console.log('sheet', join(OUT, 'sheet.png'), readdirSync(SHOTS).length, 'shots')
    } finally {
      await b.close()
    }
  } finally {
    stopServer(server)
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
