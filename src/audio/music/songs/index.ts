/**
 * SOUND_UPGRADE §4, §15: the songs, one lazy chunk each. The engine imports a song when its place is first
 * shown; the tests and the analyser import them all.
 */
import type { SongId } from '../../director.ts'
import type { Song } from '../song.ts'

export const SONG_LOADERS: Record<SongId, () => Promise<{ default: Song }>> = {
  wildsong: () => import('./wildsong.ts'),
  'ranch-spring': () => import('./ranch-spring.ts'),
  'ranch-summer': () => import('./ranch-summer.ts'),
  'ranch-autumn': () => import('./ranch-autumn.ts'),
  'ranch-winter': () => import('./ranch-winter.ts'),
  town: () => import('./town.ts'),
  cup: () => import('./cup.ts'),
}

const cache = new Map<SongId, Promise<Song>>()

export function loadSong(id: SongId): Promise<Song> {
  let p = cache.get(id)
  if (!p) {
    p = SONG_LOADERS[id]().then((m) => m.default)
    cache.set(id, p)
  }
  return p
}

/** Every song, for the tests, the analyser and the Sound Lab. */
export async function loadAllSongs(): Promise<Record<SongId, Song>> {
  const entries = await Promise.all((Object.keys(SONG_LOADERS) as SongId[]).map(async (id) => [id, await loadSong(id)] as const))
  return Object.fromEntries(entries) as Record<SongId, Song>
}
