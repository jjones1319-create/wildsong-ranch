import { afterEach, describe, expect, it, vi } from 'vitest'
import { goSideways, leaveSideways } from './sideways.ts'

/** docs/BATTLE_3D.md §5: turning the screen needs full screen first, even in the installed app (the owner's phone). */

function fakeBrowser(o: { lock?: 'ok' | 'refuse' | 'none'; standalone?: boolean }) {
  const calls: string[] = []
  let fullscreen: object | null = null
  const doc = {
    get fullscreenElement() {
      return fullscreen
    },
    documentElement: {
      requestFullscreen: vi.fn(async () => {
        calls.push('fullscreen')
        fullscreen = {}
      }),
    },
    exitFullscreen: vi.fn(async () => {
      calls.push('exit')
      fullscreen = null
    }),
  }
  const orientation =
    o.lock === 'none'
      ? {}
      : {
          lock: vi.fn(async () => {
            calls.push('lock')
            if (o.lock === 'refuse') throw new Error('NotSupportedError')
          }),
          unlock: vi.fn(() => calls.push('unlock')),
        }
  vi.stubGlobal('document', doc)
  vi.stubGlobal('screen', { orientation })
  vi.stubGlobal('matchMedia', (q: string) => ({ matches: q.includes('standalone') ? !!o.standalone : false }))
  return calls
}

describe('sideways battles', () => {
  afterEach(() => {
    leaveSideways()
    vi.unstubAllGlobals()
  })

  it('the installed app goes full screen before turning (it used to skip that, and Chrome refused)', async () => {
    const calls = fakeBrowser({ lock: 'ok', standalone: true })
    expect(await goSideways()).toBe(true)
    expect(calls).toEqual(['fullscreen', 'lock'])
    leaveSideways()
    expect(calls.slice(2)).toEqual(['unlock', 'exit'])
  })

  it('a browser that refuses to turn backs out of full screen and asks the player to turn the phone', async () => {
    const calls = fakeBrowser({ lock: 'refuse' })
    expect(await goSideways()).toBe(false)
    expect(calls).toEqual(['fullscreen', 'lock', 'unlock', 'exit'])
  })

  it('without the turning API (iPhone) it asks for nothing', async () => {
    const calls = fakeBrowser({ lock: 'none' })
    expect(await goSideways()).toBe(false)
    expect(calls).toEqual([])
  })
})
