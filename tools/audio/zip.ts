/**
 * A minimal ZIP reader for the Kenney packs (stored and deflated entries), so the pipeline needs no unzip
 * tool. Reads the central directory, inflates on demand with node:zlib.
 */
import { inflateRawSync } from 'node:zlib'

export interface ZipEntry {
  name: string
  size: number
  read: () => Buffer
}

export function readZip(buf: Buffer): ZipEntry[] {
  // End of central directory record.
  let eocd = -1
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 70000); i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) {
      eocd = i
      break
    }
  }
  if (eocd < 0) throw new Error('not a zip file')
  const count = buf.readUInt16LE(eocd + 10)
  let pos = buf.readUInt32LE(eocd + 16)
  const out: ZipEntry[] = []
  for (let n = 0; n < count; n++) {
    if (buf.readUInt32LE(pos) !== 0x02014b50) throw new Error('bad central directory')
    const method = buf.readUInt16LE(pos + 10)
    const compressed = buf.readUInt32LE(pos + 20)
    const size = buf.readUInt32LE(pos + 24)
    const nameLen = buf.readUInt16LE(pos + 28)
    const extraLen = buf.readUInt16LE(pos + 30)
    const commentLen = buf.readUInt16LE(pos + 32)
    const localAt = buf.readUInt32LE(pos + 42)
    const name = buf.subarray(pos + 46, pos + 46 + nameLen).toString('utf8')
    out.push({
      name,
      size,
      read: () => {
        if (buf.readUInt32LE(localAt) !== 0x04034b50) throw new Error(`bad local header for ${name}`)
        const lName = buf.readUInt16LE(localAt + 26)
        const lExtra = buf.readUInt16LE(localAt + 28)
        const dataAt = localAt + 30 + lName + lExtra
        const data = buf.subarray(dataAt, dataAt + compressed)
        if (method === 0) return Buffer.from(data)
        if (method === 8) return inflateRawSync(data)
        throw new Error(`unsupported zip method ${method} for ${name}`)
      },
    })
    pos += 46 + nameLen + extraLen + commentLen
  }
  return out
}
