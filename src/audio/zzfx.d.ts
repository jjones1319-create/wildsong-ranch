/** Minimal types for the ZzFX sound engine (MIT, no bundled types). Imported lazily: the module creates an AudioContext when it loads. */
declare module 'zzfx' {
  export const ZZFX: {
    volume: number
    sampleRate: number
    audioContext: AudioContext
    play(...parameters: number[]): AudioBufferSourceNode
    playSamples(sampleChannels: number[][], volumeScale?: number, rate?: number, pan?: number, loop?: boolean): AudioBufferSourceNode & { gainNode?: GainNode }
    buildSamples(...parameters: number[]): number[]
    getNote(semitoneOffset?: number, rootNoteFrequency?: number): number
  }
  export function zzfx(...parameters: number[]): AudioBufferSourceNode
}
