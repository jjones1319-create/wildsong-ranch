/** Small integer-math helpers shared by the core rules. No floats leak into stats. */

export function clamp(n: number, lo: number, hi: number): number {
  return n < lo ? lo : n > hi ? hi : n
}

/**
 * Integer division rounded half to even (banker's rounding), which is what the design doc's reference tables
 * use (they came from Python's round()). Example: divRound(45, 10) = 4, divRound(75, 10) = 8.
 */
export function divRound(n: number, d: number): number {
  if (d < 0) {
    n = -n
    d = -d
  }
  const q = Math.floor(n / d)
  const r = n - q * d
  const twice = 2 * r
  if (twice > d) return q + 1
  if (twice < d) return q
  return q % 2 === 0 ? q : q + 1
}

/** Round a (rarely needed) float half to even. */
export function roundHalfEven(x: number): number {
  const f = Math.floor(x)
  const diff = x - f
  if (diff > 0.5) return f + 1
  if (diff < 0.5) return f
  return f % 2 === 0 ? f : f + 1
}

export function sum(values: readonly number[]): number {
  let total = 0
  for (const v of values) total += v
  return total
}
