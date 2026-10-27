/**
 * A small RIFF/WAVE reader and writer for the audio tools and the render harness. Reads PCM 8/16/24/32-bit
 * integer and 32/64-bit float (plain and WAVE_FORMAT_EXTENSIBLE); writes 16-bit PCM or 32-bit float.
 * Pure: byte arrays in, byte arrays out.
 */

export interface WavData {
  sampleRate: number
  channels: Float32Array[]
}

export function decodeWav(bytes: Uint8Array): WavData {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const tag = (at: number) => String.fromCharCode(bytes[at]!, bytes[at + 1]!, bytes[at + 2]!, bytes[at + 3]!)
  if (tag(0) !== 'RIFF' || tag(8) !== 'WAVE') throw new Error('not a WAVE file')
  let pos = 12
  let format = 0
  let channelCount = 0
  let sampleRate = 0
  let bits = 0
  let dataAt = -1
  let dataLen = 0
  while (pos + 8 <= bytes.length) {
    const id = tag(pos)
    const size = view.getUint32(pos + 4, true)
    const body = pos + 8
    if (id === 'fmt ') {
      format = view.getUint16(body, true)
      channelCount = view.getUint16(body + 2, true)
      sampleRate = view.getUint32(body + 4, true)
      bits = view.getUint16(body + 14, true)
      if (format === 0xfffe && size >= 26) format = view.getUint16(body + 24, true)
    } else if (id === 'data') {
      dataAt = body
      dataLen = Math.min(size, bytes.length - body)
      break
    }
    pos = body + size + (size & 1)
  }
  if (dataAt < 0 || channelCount === 0 || sampleRate === 0) throw new Error('WAVE file without fmt or data')
  const bytesPer = bits / 8
  const frames = Math.floor(dataLen / (bytesPer * channelCount))
  const channels = Array.from({ length: channelCount }, () => new Float32Array(frames))
  const isFloat = format === 3
  for (let f = 0; f < frames; f++) {
    for (let c = 0; c < channelCount; c++) {
      const at = dataAt + (f * channelCount + c) * bytesPer
      let v: number
      if (isFloat) v = bits === 64 ? view.getFloat64(at, true) : view.getFloat32(at, true)
      else if (bits === 8) v = (bytes[at]! - 128) / 128
      else if (bits === 16) v = view.getInt16(at, true) / 32768
      else if (bits === 24) v = ((bytes[at]! | (bytes[at + 1]! << 8) | (bytes[at + 2]! << 16)) << 8) / 2147483648
      else if (bits === 32) v = view.getInt32(at, true) / 2147483648
      else throw new Error(`unsupported bit depth ${bits}`)
      channels[c]![f] = v
    }
  }
  return { sampleRate, channels }
}

export function encodeWav(channels: readonly Float32Array[], sampleRate: number, bits: 16 | 32 = 16): Uint8Array {
  const channelCount = channels.length
  const frames = channels[0]?.length ?? 0
  const bytesPer = bits / 8
  const dataLen = frames * channelCount * bytesPer
  const out = new Uint8Array(44 + dataLen)
  const view = new DataView(out.buffer)
  const put = (at: number, s: string) => {
    for (let i = 0; i < s.length; i++) out[at + i] = s.charCodeAt(i)
  }
  put(0, 'RIFF')
  view.setUint32(4, 36 + dataLen, true)
  put(8, 'WAVE')
  put(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, bits === 32 ? 3 : 1, true)
  view.setUint16(22, channelCount, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * channelCount * bytesPer, true)
  view.setUint16(32, channelCount * bytesPer, true)
  view.setUint16(34, bits, true)
  put(36, 'data')
  view.setUint32(40, dataLen, true)
  let at = 44
  for (let f = 0; f < frames; f++) {
    for (let c = 0; c < channelCount; c++) {
      const v = Math.max(-1, Math.min(1, channels[c]![f]!))
      if (bits === 32) view.setFloat32(at, v, true)
      else view.setInt16(at, Math.round(v * 32767), true)
      at += bytesPer
    }
  }
  return out
}
