/**
 * The ffmpeg wrapper for the audio tools: decoding any source (WAV, Ogg Vorbis, Opus) to float PCM at a
 * chosen rate, and encoding Opus (or Vorbis when libopus is missing). `ffmpeg` on PATH wins; otherwise the
 * `ffmpeg-static` devDependency's binary (SOUND_UPGRADE §5.3 step 5).
 */
import { execFileSync, spawnSync } from 'node:child_process'
import { createRequire } from 'node:module'

function findFfmpeg(): string {
  if (process.env.FFMPEG) return process.env.FFMPEG
  const probe = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' })
  if (probe.status === 0) return 'ffmpeg'
  const require = createRequire(import.meta.url)
  const p = require('ffmpeg-static') as string | null
  if (!p) throw new Error('No ffmpeg: install one on PATH or run `npm approve-scripts ffmpeg-static && npm rebuild ffmpeg-static`.')
  return p
}

export const FFMPEG: string = findFfmpeg()

export function ffmpegEncoders(): string[] {
  const out = execFileSync(FFMPEG, ['-hide_banner', '-encoders'], { encoding: 'utf8' })
  return out
    .split('\n')
    .map((l) => /^\s*[A-Z.]{6}\s+(\S+)/.exec(l)?.[1] ?? '')
    .filter(Boolean)
}

export function hasLibopus(): boolean {
  return ffmpegEncoders().includes('libopus')
}

/** Decodes a file to float channels at `sampleRate`, folded to `channels` channels. */
export function decodeFile(path: string, sampleRate: number, channels: 1 | 2 = 1): Float32Array[] {
  const buf = execFileSync(FFMPEG, ['-v', 'error', '-i', path, '-f', 'f32le', '-acodec', 'pcm_f32le', '-ac', String(channels), '-ar', String(sampleRate), 'pipe:1'], { maxBuffer: 1 << 30 })
  const frames = Math.floor(buf.length / 4 / channels)
  const out = Array.from({ length: channels }, () => new Float32Array(frames))
  const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength)
  for (let f = 0; f < frames; f++) for (let c = 0; c < channels; c++) out[c]![f] = view.getFloat32((f * channels + c) * 4, true)
  return out
}

/** Encodes a WAV file to Opus in Ogg (48 kHz mono) or, without libopus, to Vorbis q4. Returns the codec used. */
export function encodeOgg(wavPath: string, outPath: string, kbps: number, opus: boolean): 'opus' | 'vorbis' {
  if (opus) {
    execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', wavPath, '-c:a', 'libopus', '-b:a', `${kbps}k`, '-vbr', 'on', '-application', 'audio', '-frame_duration', '20', '-ar', '48000', '-ac', '1', outPath])
    return 'opus'
  }
  execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', wavPath, '-c:a', 'libvorbis', '-q:a', '4', '-ar', '48000', '-ac', '1', outPath])
  return 'vorbis'
}

/** Encodes a review file: Opus 96 kbps stereo. */
export function encodeReview(wavPath: string, outPath: string, opus: boolean): void {
  if (opus) execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', wavPath, '-c:a', 'libopus', '-b:a', '96k', '-vbr', 'on', '-ar', '48000', outPath])
  else execFileSync(FFMPEG, ['-v', 'error', '-y', '-i', wavPath, '-c:a', 'libvorbis', '-q:a', '6', '-ar', '48000', outPath])
}
