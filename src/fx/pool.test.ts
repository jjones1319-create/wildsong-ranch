import { describe, expect, it } from 'vitest'
import { Pool } from './pool.ts'

describe('Pool (V1 effects: no allocation after warm-up)', () => {
  it('creates at most capacity objects and recycles them', () => {
    let made = 0
    const pool = new Pool(() => ({ id: ++made }), 3)
    const a = pool.take()!
    const b = pool.take()!
    const c = pool.take()!
    expect(pool.take()).toBeNull()
    expect(made).toBe(3)
    pool.give(b)
    expect(pool.take()).toBe(b)
    pool.give(a)
    pool.give(c)
    for (let i = 0; i < 100; i++) {
      const t = pool.take()!
      pool.give(t)
    }
    expect(made).toBe(3)
    expect(pool.size).toBe(3)
  })

  it('warm() builds everything up front and the pool never grows afterwards', () => {
    let made = 0
    const pool = new Pool(() => ({ id: ++made }), 50)
    pool.warm()
    expect(made).toBe(50)
    expect(pool.available).toBe(50)
    const taken = []
    for (let i = 0; i < 50; i++) taken.push(pool.take()!)
    expect(pool.available).toBe(0)
    expect(pool.take()).toBeNull()
    for (const t of taken) pool.give(t)
    for (let frame = 0; frame < 200; frame++) {
      const batch = []
      for (let i = 0; i < 37; i++) batch.push(pool.take()!)
      for (const t of batch) pool.give(t)
    }
    expect(made).toBe(50)
  })
})
