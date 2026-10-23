import { describe, expect, it } from 'vitest'
import { platformOf } from './platform.ts'

describe('platform detection for the install card (§21)', () => {
  it('tells iPhones, iPads and Android phones apart', () => {
    expect(platformOf('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1')).toBe('ios')
    expect(platformOf('Mozilla/5.0 (iPad; CPU OS 16_4 like Mac OS X) AppleWebKit/605.1.15')).toBe('ios')
    expect(platformOf('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15', 5)).toBe('ios')
    expect(platformOf('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15', 0)).toBe('other')
    expect(platformOf('Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/124.0 Mobile Safari/537.36')).toBe('android')
    expect(platformOf('Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0')).toBe('other')
  })
})
