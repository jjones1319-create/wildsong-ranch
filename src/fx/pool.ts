/**
 * A fixed-capacity object pool: `make` runs at most `capacity` times, ever. After warm-up no frame allocates.
 * `take()` returns null when the pool is dry, so callers skip the particle instead of growing memory.
 */
export class Pool<T> {
  private readonly free: T[] = []
  private made = 0
  private readonly make: () => T
  readonly capacity: number
  constructor(make: () => T, capacity: number) {
    this.make = make
    this.capacity = capacity
  }

  /** How many objects exist (free or taken); never exceeds capacity. */
  get size(): number {
    return this.made
  }

  get available(): number {
    return this.free.length + (this.capacity - this.made)
  }

  take(): T | null {
    const t = this.free.pop()
    if (t !== undefined) return t
    if (this.made >= this.capacity) return null
    this.made += 1
    return this.make()
  }

  give(t: T): void {
    this.free.push(t)
  }

  /** Creates every object up front (at mount, not mid-battle). */
  warm(n = this.capacity): void {
    while (this.made < Math.min(n, this.capacity)) {
      this.made += 1
      this.free.push(this.make())
    }
  }
}
