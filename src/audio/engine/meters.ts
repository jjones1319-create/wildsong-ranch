/**
 * SOUND_UPGRADE §4.8, §13: live meters for the debug view and the Sound Lab's Mix tab. One AnalyserNode per
 * bus reads the time-domain signal; `read()` returns the peak and a short-term RMS in dB for each.
 * Realtime contexts only (an offline render measures its buffers with the analysis modules instead).
 */

export interface MeterReading {
  peakDb: number
  rmsDb: number
}

export class Meters {
  private analysers = new Map<string, AnalyserNode>()
  private scratch: Float32Array<ArrayBuffer> | null = null
  private smoothed = new Map<string, number>()

  attach(ctx: BaseAudioContext, name: string, node: AudioNode): void {
    const a = ctx.createAnalyser()
    a.fftSize = 2048
    a.smoothingTimeConstant = 0
    node.connect(a)
    this.analysers.set(name, a)
  }

  names(): string[] {
    return [...this.analysers.keys()]
  }

  read(name: string): MeterReading {
    const a = this.analysers.get(name)
    if (!a) return { peakDb: -Infinity, rmsDb: -Infinity }
    if (!this.scratch || this.scratch.length !== a.fftSize) this.scratch = new Float32Array(new ArrayBuffer(a.fftSize * 4))
    a.getFloatTimeDomainData(this.scratch)
    let peak = 0
    let sum = 0
    for (let i = 0; i < this.scratch.length; i++) {
      const v = this.scratch[i]!
      peak = Math.max(peak, Math.abs(v))
      sum += v * v
    }
    const rms = Math.sqrt(sum / this.scratch.length)
    // A short-term feel: smooth the RMS over about half a second of reads.
    const prev = this.smoothed.get(name) ?? rms
    const s = prev + (rms - prev) * 0.25
    this.smoothed.set(name, s)
    return { peakDb: peak > 0 ? 20 * Math.log10(peak) : -Infinity, rmsDb: s > 0 ? 20 * Math.log10(s) : -Infinity }
  }

  readAll(): Record<string, MeterReading> {
    const out: Record<string, MeterReading> = {}
    for (const n of this.analysers.keys()) out[n] = this.read(n)
    return out
  }
}
