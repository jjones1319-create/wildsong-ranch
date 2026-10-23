/**
 * The Shrine of Echoes' words (GAME_DESIGN §14.1): the Randomize word list, and the stone's teasers when a
 * song wakes a breed that is still sleeping. Teasers hint without naming the breed.
 */

export const SHRINE_WORDS: readonly string[] = [
  'river', 'lantern', 'thunder', 'meadow', 'ember', 'moon', 'harbor', 'willow', 'copper', 'frost',
  'violet', 'orchard', 'tide', 'cinder', 'echo', 'feather', 'marble', 'honey', 'storm', 'clover',
  'twilight', 'pebble', 'compass', 'ribbon', 'sparrow', 'velvet', 'quartz', 'bramble', 'saffron', 'drift',
  'hollow', 'kettle', 'mirror', 'nettle', 'ocean', 'paper', 'quiet', 'rumble', 'silver', 'tumble',
  'umber', 'wander', 'yonder', 'zephyr', 'amber', 'birch', 'candle', 'dawn', 'fable', 'garden',
]

/** Teasers by sleeping breed. Anything not listed falls back to `default`. */
export const SHRINE_TEASERS: Readonly<Record<string, string>> = {
  default: '…a sleeping power, waiting for a braver day…',
  velvesper: '…something soft that only the moon has seen…',
  ashwraith: '…a cold light that remembers a name…',
  zipwisp: '…a crackle in the air, too quick to catch…',
  mirrorkin: '…a shape that looks back when you look in…',
  gearhoot: '…a ticking in the dark, patient and slow…',
  reefclaw: '…a weight on the sea floor, dreaming of tides…',
  lootlid: '…a glint under a lid that will not lift…',
  aurelwyrm: '…a crown of gold, heavy as stone…',
}
