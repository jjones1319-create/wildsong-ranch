/**
 * Ranch scenery clips: frames -> MP4 + WebP still, and contact sheets for review.
 *
 *   node tools/blender/encode.ts contact <scene> [--preview] [--zones]
 *       8 evenly spaced frames from tools/blender/out/<scene>[-preview]/ tiled 4x2 into
 *       tools/blender/out/contact-<scene>[-preview][-zones].png (--zones draws the overlay anchors).
 *   node tools/blender/encode.ts encode <scene|all>
 *       tools/blender/out/<scene>/f_%04d.png -> public/baked/scenes/<scene>.mp4 (H.264, yuv420p,
 *       +faststart, no audio, CRF searched so the file is <= 1 MB) and <scene>.webp (<= 150 KB).
 *
 * Uses the ffmpeg-static devDependency, or ffmpeg on PATH.
 */
import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(HERE, '..', '..')
const OUT = path.join(HERE, 'out')
const DEST = path.join(ROOT, 'public', 'baked', 'scenes')
const FPS = 24
const MAX_MP4 = 1_000_000
const AIM_MP4 = 900_000
const MIN_MP4 = 400_000
const MAX_WEBP = 150_000

/** Overlay anchors (fractions of the frame, y from the top) and the frame used for the still. */
type SceneCfg = {
  anchors: Array<[number, number]>
  zones: Array<[number, number, number, number]>
  still: number
  /** ffmpeg vignette angle (radians); 0 = none. Applied to the MP4 and the still alike. */
  vignette: number
}
const SCENES: Record<string, SceneCfg> = {
  welcome: { anchors: [[0.5, 0.58], [0.5, 0.84]], zones: [[0.415, 0.585, 0.5, 0.6], [0.3, 0.7, 0.6, 0.97]], still: 96, vignette: 0.42 },
  sad: { anchors: [[0.58, 0.68]], zones: [[0.45, 0.72, 0.5, 0.75]], still: 180, vignette: 0.55 },
  abandoned: { anchors: [[0.52, 0.74], [0.4, 0.765]], zones: [[0.37, 0.69, 0.6, 0.83], [0.32, 0.48, 0.7, 0.82]], still: 110, vignette: 0.6 },
  note: { anchors: [[0.55, 0.45]], zones: [], still: 90, vignette: 0.6 },
}

function look(scene: string): string[] {
  const v = SCENES[scene]?.vignette ?? 0
  return v > 0 ? ['-vf', `vignette=angle=${v}:mode=forward`] : []
}

function ffmpegBin(): string {
  const local = path.join(ROOT, 'node_modules', 'ffmpeg-static', process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg')
  return existsSync(local) ? local : 'ffmpeg'
}

function ff(args: string[]): string {
  const r = spawnSync(ffmpegBin(), ['-hide_banner', '-y', ...args], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
  if (r.status !== 0) {
    console.error(r.stderr)
    throw new Error(`ffmpeg failed: ${args.join(' ')}`)
  }
  return r.stderr
}

function frames(dir: string): string[] {
  if (!existsSync(dir)) throw new Error(`no frames in ${dir}`)
  return readdirSync(dir).filter((f) => /^f_\d{4}\.png$/.test(f)).sort()
}

function kb(n: number): string {
  return `${(n / 1024).toFixed(0)} KB`
}

function contact(scene: string, preview: boolean, zones: boolean): void {
  const dir = path.join(OUT, scene + (preview ? '-preview' : ''))
  const all = frames(dir)
  const pick = Array.from({ length: Math.min(8, all.length) }, (_, i) =>
    all[Math.round((i * (all.length - 1)) / Math.max(1, Math.min(8, all.length) - 1))])
  const inputs = pick.flatMap((f) => ['-i', path.join(dir, f)])
  const tw = 270
  const th = 360
  const cfg = SCENES[scene]
  const marks: string[] = []
  if (zones && cfg) {
    for (const [u0, u1, v0, v1] of cfg.zones) {
      marks.push(`drawbox=x=${Math.round(u0 * tw)}:y=${Math.round(v0 * th)}:w=${Math.round((u1 - u0) * tw)}:h=${Math.round((v1 - v0) * th)}:color=cyan@0.7:t=1`)
    }
    for (const [u, v] of cfg.anchors) {
      marks.push(`drawbox=x=${Math.round(u * tw) - 4}:y=${Math.round(v * th) - 4}:w=8:h=8:color=magenta@0.9:t=fill`)
    }
  }
  const per = pick.map((_, i) => `[${i}:v]scale=${tw}:${th}${marks.length ? ',' + marks.join(',') : ''}[t${i}]`)
  const n = pick.length
  const cols = Math.min(4, n)
  const layout = pick.map((_, i) => `${(i % cols) * tw}_${Math.floor(i / cols) * th}`).join('|')
  const filter = `${per.join(';')};${pick.map((_, i) => `[t${i}]`).join('')}xstack=inputs=${n}:layout=${layout}:fill=black[out]`
  const dest = path.join(OUT, `contact-${scene}${preview ? '-preview' : ''}${zones ? '-zones' : ''}.png`)
  ff([...inputs, '-filter_complex', filter, '-map', '[out]', '-frames:v', '1', dest])
  console.log(`contact sheet: ${dest} (frames ${pick.join(', ')})`)
}

function encode(scene: string): void {
  const dir = path.join(OUT, scene)
  const all = frames(dir)
  mkdirSync(DEST, { recursive: true })
  const mp4 = path.join(DEST, `${scene}.mp4`)
  const run = (crf: number): number => {
    ff(['-framerate', String(FPS), '-start_number', '1', '-i', path.join(dir, 'f_%04d.png'), ...look(scene),
      '-c:v', 'libx264', '-preset', 'veryslow', '-crf', String(crf), '-pix_fmt', 'yuv420p',
      '-profile:v', 'high', '-level:v', '4.0', '-g', '48', '-movflags', '+faststart', '-an', mp4])
    return statSync(mp4).size
  }
  // Find the lowest CRF (best quality) that stays under the aim; never exceed the hard cap.
  let crf = 22
  let size = run(crf)
  while (size > AIM_MP4 && crf < 40) {
    crf += 1
    size = run(crf)
  }
  while (size < MIN_MP4 && crf > 16) {
    const s2 = run(crf - 1)
    if (s2 > AIM_MP4) {
      size = run(crf)
      break
    }
    crf -= 1
    size = s2
  }
  if (size > MAX_MP4) throw new Error(`${scene}.mp4 is ${kb(size)} even at CRF ${crf}`)
  const info = spawnSync(ffmpegBin(), ['-hide_banner', '-i', mp4], { encoding: 'utf8' }).stderr
  const dur = /Duration: ([\d:.]+)/.exec(info)?.[1] ?? '?'
  console.log(`${scene}.mp4  ${kb(size)}  CRF ${crf}  ${all.length} frames = ${(all.length / FPS).toFixed(2)} s (container ${dur})`)

  const still = SCENES[scene]?.still ?? Math.ceil(all.length / 2)
  const src = path.join(dir, `f_${String(still).padStart(4, '0')}.png`)
  const webp = path.join(DEST, `${scene}.webp`)
  let q = 82
  let ws = 0
  for (;;) {
    ff(['-i', src, ...look(scene), '-c:v', 'libwebp', '-quality', String(q), '-compression_level', '6', '-preset', 'picture', webp])
    ws = statSync(webp).size
    if (ws <= MAX_WEBP || q <= 40) break
    q -= 6
  }
  console.log(`${scene}.webp ${kb(ws)}  quality ${q}  (frame ${still})`)
}

const [cmd, target, ...rest] = process.argv.slice(2)
const names = target === 'all' ? Object.keys(SCENES) : [target]
if (!cmd || !target || names.some((n) => !(n in SCENES))) {
  console.error('usage: node tools/blender/encode.ts contact|encode <welcome|sad|abandoned|note|all> [--preview] [--zones]')
  process.exit(1)
}
for (const n of names) {
  if (cmd === 'contact') contact(n, rest.includes('--preview'), rest.includes('--zones'))
  else if (cmd === 'encode') encode(n)
  else throw new Error(`unknown command ${cmd}`)
}
