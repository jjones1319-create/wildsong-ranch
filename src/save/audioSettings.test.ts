import { describe, expect, it } from 'vitest'
import { AUDIO } from '../data/tuning.ts'
import { applyAudioDefaultsV2, defaultSettings, validateSettings } from './schema.ts'

describe('Sound 2.0 settings (§12)', () => {
  it('new installs get the new defaults with the bump already recorded', () => {
    const s = defaultSettings()
    expect(s.musicVolume).toBe(70)
    expect(s.sfxVolume).toBe(75)
    expect(s.masterVolume).toBe(80)
    expect(s.ambienceVolume).toBe(60)
    expect(s.ambience).toBe(true)
    expect(s.buttonSounds).toBe(true)
    expect(s.listening).toBe('speaker')
    expect(s.monoAudio).toBe(false)
    expect(s.audioDefaultsV2).toBe(true)
    expect(AUDIO.defaultVolume).toEqual({ master: 80, music: 70, sfx: 75, ambience: 60 })
  })

  it('an old settings record at the old defaults is bumped once', () => {
    const old = { ...defaultSettings(), musicVolume: 55, sfxVolume: 100, audioDefaultsV2: false }
    const bumped = applyAudioDefaultsV2(old)
    expect(bumped.musicVolume).toBe(70)
    expect(bumped.sfxVolume).toBe(75)
    expect(bumped.audioDefaultsV2).toBe(true)
    // A second run changes nothing.
    expect(applyAudioDefaultsV2(bumped)).toEqual(bumped)
  })

  it("a player's own values stay, and a record saved before Sound 2.0 loads with the new fields", () => {
    const chosen = { ...defaultSettings(), musicVolume: 40, sfxVolume: 100, audioDefaultsV2: false }
    const r = applyAudioDefaultsV2(chosen)
    expect(r.musicVolume).toBe(40)
    expect(r.sfxVolume).toBe(75)
    const legacy: Record<string, unknown> = { ...defaultSettings() }
    delete legacy.ambience
    delete legacy.ambienceVolume
    delete legacy.buttonSounds
    delete legacy.listening
    delete legacy.monoAudio
    delete legacy.audioDefaultsV2
    legacy.musicVolume = 55
    legacy.sfxVolume = 100
    const loaded = validateSettings(legacy)
    expect(loaded.ambience).toBe(true)
    expect(loaded.ambienceVolume).toBe(60)
    expect(loaded.buttonSounds).toBe(true)
    expect(loaded.listening).toBe('speaker')
    expect(loaded.monoAudio).toBe(false)
    expect(loaded.musicVolume).toBe(70)
    expect(loaded.sfxVolume).toBe(75)
    expect(loaded.audioDefaultsV2).toBe(true)
    expect(validateSettings({ ...defaultSettings(), listening: 'wat', ambienceVolume: 500 })).toMatchObject({ listening: 'speaker', ambienceVolume: 100 })
  })
})
