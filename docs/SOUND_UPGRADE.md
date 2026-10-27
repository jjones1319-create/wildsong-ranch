# Sound 2.0: calm acoustic music, a theme for every event, training soundscapes

The owner's request (2026-10-25), done before V3: *"Right now it is very harsh. I would also like the background music to be different for each event … something more calming. Then each of the trainings should be something to go with it, like waterfall for waterfall … I will leave those to your discretion."*

**Sound 2.0 changes no rules.** `src/core` stays untouched and deterministic. Audio only listens to game state; it never changes it, and its randomness comes from its own seeded generator, never the game's.

## 0. Decisions

| Topic | Decision |
|---|---|
| Style | Calm, warm and acoustic: a **storybook folk orchestra**. Ocarina and recorder leads, harp, plucked and bowed strings, soft mallets and hand drums, with plenty of space and reverb. The owner's reference is the gentle, ocarina-led music of classic 3D fantasy-adventure games. It is a mood reference only (§3.5). |
| Music per event | Every place and every event has its own music. The big events each get their own composition: the Officials (Ascensions), the four Crowns, the Legend, the Masquerade, the Rival Showdown, the Summit, the Rallies, Sprout/Elders and the Journey Trials. The regular cups share a cup theme, but each cup has its own arrangement (lead instrument, drum kit, key and tempo) inside its season's palette. |
| Trainings | Each of the 11 drills gets its own soundscape: the ambience of its place (the waterfall roars for Waterfall Stand), sounds for the action, a short music cue in its own mood, and five outcome stingers. |
| Effects | Redesigned to be soft and natural. Button taps are quiet and can be turned off. Battle sounds follow the V1 element of each technique. |
| How it's made | Live in the browser: real instrument **samples** (CC0) played by our own small sequencer, procedural ambience, and CC0 recorded sound effects. The engine loads at the first tap. No pre-rendered music files. No new runtime dependency; ZzFX is removed. |
| Who judges | The owner's ears, on the phone. Claude can't hear, so every stage ends with the Sound Lab (§13) and the review files (§14.4), then stops for listening notes. S1 composes the most-heard music first, so the direction is approved before the rest is written. |
| Stages | **S1** engine, mix, effects, ambience, Sound Lab and the first pieces, with the Waterfall pilot. **S2** a theme for every event. **S3** places, trainings and life moments. §15 lists exactly what each stage contains. |

## 1. What's wrong now (measured on the current code)

- **Music.** Nine loops are built from raw square, saw, triangle and sine waves, with a white-noise hi-hat.
  - They aren't band-limited and are rendered at **22,050 Hz mono**, so the square and saw leads alias (the "fizz").
  - There's no reverb, and a soft clipper squashes the result: crest factor only **6.5–8.9 dB**. Natural music sits around 12–20 dB.
  - The loops are **3.6–16 s long** (battle 6.4 s, town 7.7 s, ranch 8–12 s), so each repeats 4–9 times a minute.
- **One battle loop** (150 BPM, saw lead) plays in every battle in the game. **One town loop** covers ten screens.
- **Effects.**
  - Hit, crit and KO use ZzFX's "tan" waveform with bit-crush and noise, which is gritty by design.
  - Every button press plays an 880 Hz blip (660 Hz for chips).
  - Every effect, a tap included, dips the music by 4.4 dB for 0.3 s, so the music "pumps" all through a battle.
  - The defaults put effects at 100% and music at 55%.
- **Silence.** There is no ambience anywhere, and drills only get one generic stinger.

## 2. Goals, budgets, non-goals

**Goals**
- Pleasant on a phone speaker for an hour.
- Every context recognisably its own.
- Never harsh.
- Adaptive: battles build, and weather changes the ranch.
- Seamless changes between screens.
- Works offline.

**Budgets**

| What | Budget |
|---|---|
| Audio files in `public/audio` (Opus) | ≤ 10 MB in all; the core pack ≤ 4.5 MB |
| Decoded samples in memory | core ≤ 450 s of audio (about 86 MB at 48 kHz); events ≤ 250 s; places ≤ 300 s. Only core plus one other pack stay resident, and a pack unused for 60 s is released. |
| Engine JS | its own chunk, loaded by dynamic import at the first tap, ≤ 45 KB gzipped. Songs are lazy chunks that load with their place, ≤ 120 KB gzipped in all. Both are checked after the build (§14.6). |
| Voices at once | music 32 (voices in silent layers are stolen first) · ambience 16 · effects 16 · UI 4 |
| Start-up | No audio work before the first tap. The core pack decodes after unlock in under 1.5 s on the phone; the decode time per pack is shown in `window.__audio` and the Sound Lab. A screen never waits for audio: it uses the fallback voices (§4.5) until its samples are ready, then crossfades. |
| Battery | Nothing is scheduled while muted or while the app is hidden. |

**If a pack is over budget, cut in this order:**
1. Shorten sustains and decays.
2. Drop alternate takes.
3. Space accompaniment instruments' samples every 4 semitones instead of 3.
4. Drop `ocarina-hi`, `balafon` and `didgeridoo`.

Never cut the ocarina, the harp, the strings or the drill Foley.

**Not in Sound 2.0**
- Monster voices: they fit V3, with the rigs and poses.
- A sound for each technique: that's V2.
- Recorded nature ambience: it can be dropped in later as CC0 files (§9.1).
- Streaming music files.

## 3. Style bible

### 3.1 Palette (instrument ids from §5.2)

| Role | Instruments |
|---|---|
| Calm lead | `ocarina` (the signature voice: home, the Shrine, the main theme, farewells), `recorder-alto`, `recorder-tenor`, `flute` |
| Playful lead | `recorder-soprano`, `marimba`, `kalimba`, `xylophone`, `clarinet`, `bassoon` |
| Noble lead | `horn`, `cellos`, `violins` (ceremonies, Crowns, the Legend) |
| Harmony and texture | `harp`, `strumstick`, `vibes` (soft and bowed), `violas`, `organ` (one soft stop), `wine-glasses`, `psaltery`; `harpsichord` (the Masquerade only), `piano` (the Labs only), the `music-box` patch |
| Bright colours | `glock`, `hand-chimes`, `tubular-bells`, `wine-glasses`, `mark-trees`, `triangle`. They double or answer, and never carry a line longer than 2 bars on their own. |
| Bass | `cellos` and `contrabass` pizzicato, low `harp`, low `marimba`, `tuba` staccato (comic only), `timpani` (ceremonies and battles). Keep bass notes mostly at E2 or above so a phone speaker carries them through their harmonics. |
| Percussion | `frame-drum`, `darbuka`, `bongos`, `cajon`, `shaker`, `tambourine`, `woodblock`, `claves`, `claps`, `finger-cymbals`, `triangle`, `sleigh-bells` (winter), `mark-trees`, `bell-tree`, `timpani`, `bass-drum` (soft), `cymbal-swell` (mallet swells only), `ocean-drum` |
| **Never** | square, saw or pulse oscillators; bit-crush; distortion; drum machines; synth leads; electric guitar; trumpet; full-force cymbal crashes; anything that sounds like a phone notification |

### 3.2 Calm rules

- **Tempo bands** are in quarter notes per minute. In 6/8, 9/8 and 12/8, count a dotted quarter as 1.5 quarters (♩. = 60 counts as 90).
  - Shrine and meditation 50–66.
  - Ranch and places 66–96.
  - Town 96–112.
  - Battles 100–132, including every tempo variant and nudge (§7.4).
  - A lobby layer plays at its battle theme's tempo with a half-time feel: sparse, held notes.
  - Drill beds 56–132; each drill sets its own energy.
  - Turnip Sort 120–150 (it follows the game's speed ramp).
- **Density:** at most 4 melodic voices at once in places and 6 in battles. Parts with the role lead, counter or accomp count; a chord part counts as one voice. Leave rests. A wind lead never plays more than 4 bars (or 8 s) without a breath.
- **Register:**
  - Lead and counter parts stay between A3 and E6.
  - Nothing goes above C7 except bright colours at p or softer.
  - Sustained notes above A5 are mp or softer.
- **Dynamics:** p–mf in places, mf–f in battles. Crescendos take 2 bars or more, and accents stay gentle.
- **Space:**
  - Reverb on everything musical (§4.6).
  - On the ranch, a breath of 8–20 s of ambience only between passes of the music (15–30 s in a storm).
- **Lengths:**

  | Kind | Length |
  |---|---|
  | Place, ranch and town music | 60–150 s before it repeats, with at least two contrasting sections |
  | Battle themes | at least 70 s. A match is 60 s, so no match ever hears a repeat. |
  | Interrupting stingers | 1.5–10 s |
  | Musical effects | ≤ 1.5 s |
  | Drill outcome stingers | 1.2–2.5 s |
  | Drill beds | 2–4 bars, looping |

### 3.3 Energy map (1 = stillest, 5 = biggest)

| Level | Contexts |
|---|---|
| 1 | Shrine, Moon Meditation, Farewell, Journal, Library |
| 2 | Ranch, Monster Lab, Expeditions, cup lobbies |
| 2–3 | Journeys |
| 3 | Town, Pell's Lab |
| 3–4 | Turnip Sort |
| 4 | Cup battles, Ascensions, the Summit |
| 4–5 | Crowns |
| 5 | The Legend |

Level 5 is a warm full orchestra, never rock or EDM.

### 3.4 Musical language

**Modes as moods:**

| Mode | Mood |
|---|---|
| Ionian | home, warmth |
| Lydian | wonder, sunrise, magic (the raised 4th) |
| Mixolydian | rustic, cheerful, outdoors |
| Dorian | adventure, a little wistful, wind and water |
| Aeolian | melancholy, winter, night |
| Phrygian | mystery; rare (caves) |
| Phrygian dominant | the Crown of Embers only |
| Harmonic minor | the Masquerade only |
| Major / minor pentatonic | folk tunes, the stones, monster songs |

**Harmony**
- Slow harmonic rhythm: one chord per bar, or per two bars in calm pieces.
- Pedal points and drones.
- sus2, sus4 and add9 colours.
- Modal cadences (♭VII–I, IV–I, Dorian ii–I) and the occasional borrowed iv for nostalgia.
- Avoid the I–V–vi–IV pop loop, and don't make V7–I the only cadence.

**Meter and feel:** these are guidance, not rules.
- 3/4 waltz for villages.
- 6/8 for travel, wind and water.
- 4/4 for battles and work.
- 2/4 for comedy.

**Textures**
- Harp or kalimba ostinatos and pizzicato walking bass.
- Two winds in parallel 3rds or 6ths.
- Call and answer between the lead and a second instrument.
- Held string pads under a single melody.
- A hemiola at waltz cadences.

### 3.5 Originality (CLAUDE.md rule 1 applies to music too)

- Every melody, chord progression, bass line and rhythm is newly written for this game.
- Never quote or paraphrase anything from the reference games, from Monster Rancher or from any other game, film, show or song:
  - no famous openings;
  - no recognisable riffs;
  - no "item get", "secret found" or "puzzle solved" jingles from other games.
- Never name or describe a piece by another work in code or docs. Describe the style in musical words only: instruments, modes, tempos.
- Folk idioms (waltzes, jigs, drones, pentatonic tunes) are fine. Specific traditional tunes are not; keep it all original.
- If a phrase starts to sound like something known, change it. The owner's phone checks ask "does any tune sound like something you know?"

### 3.6 Motifs

- **The Wildsong motif.** An original phrase of 5–7 notes in D (Lydian colour), written once in `music/motifs.ts`.
  - The lore: the land itself sings, and this is its song.
  - Shape: singable, with one rising 4th or 5th; it touches the raised 4th once and ends on a held non-tonic note so it can lead anywhere.
  - Where it appears:
    - the title (in full);
    - one quote in each ranch song, usually in the B section;
    - the Shrine (the stones answer it);
    - the Ascension and the Legend (heroic);
    - the credits;
    - the last notes of a farewell.
  - A test checks it: the exact pitch-interval sequence, in any transposition, with free rhythm.
- **Corin's motif:** 3–4 notes with a cocky rising shape. It's in `rival` and in any match against him.
- **The Masked Breeder's motif:** a chromatic turn, for `masquerade` only.
- **Rival calling cards (S2):** each named rival in `data/rivals.ts` gets a musical effect (§4.7): a 3–4 note phrase on their own instrument, played over the lobby when the round preview shows them.
- **Monster songs:** every monster has its own (§7.7).

## 4. Engine

```
src/audio/
  player.ts            the public API the UI uses; imports the engine chunk at the first tap; keeps today's names working (§10.5)
  director.ts          what plays when: a pure decision function plus the controller that applies it (§11)
  engine/
    context.ts         AudioContext, unlock, buses, master chain, listening presets, mono, visibility
    nodes.ts           the only place that creates oscillators, PeriodicWaves, compressors and WaveShapers (with asserts, §14.1)
    driver.ts          realtime driver (timer + currentTime) and offline driver (suspend/resume), §4.4
    scheduler.ts       lookahead, one transport per song, quantised changes, late-event count
    samples.ts         manifest, packs, decode, cache, release · sampler.ts  sample voices · synth.ts  fallback voices
    reverb.ts          seeded impulse responses · ambience.ts  bed generator (§9) · sfx.ts  effect player (§10) · meters.ts
  music/
    abc.ts (§6.2) · chords.ts · patterns.ts (§6.3) · perc.ts (§6.4) · song.ts · checker.ts (§6.7)
    motifs.ts · monsterSong.ts · stingers.ts · songs/*.ts (one file per piece, lazy, via songs/index.ts)
  recipes/
    instruments.ts (ids, articulations, ranges, fallbacks) · kits.ts · ambience.ts · sfx.ts · drills.ts · events.ts (§7.4)
  analysis/
    loudness.ts (ITU-R BS.1770-4) · truepeak.ts · spectrum.ts · clicks.ts   (shared by tools and tests)
src/ui/screens/lab/LabSound.tsx   the Sound Lab (§13)
tools/audio/
  build-samples.ts (§5.3) · render-review.ts (§14.3–14.4) · baseline-legacy.json (the old tracks' numbers)
```

- Only `src/audio/engine` touches Web Audio.
- `src/core` never imports audio.
- The director's decision function is pure and fully table-tested.
- Audio randomness (humanising, ambience events, variations, breath lengths) uses its own mulberry32. It's seeded per session in play and fixed per item in renders. It never uses the game RNG or `Math.random`.

### 4.1 Context

- Keep today's unlock on the first `pointerup` / `keydown`. Create the context with `latencyHint: 'interactive'`.
- Keep `navigator.audioSession.type = 'ambient'` where it exists.
- Build the impulse responses and noise buffers at engine init, so an `OfflineAudioContext` gets them too.
- Suspend while hidden and resume on return, as today. Music continues where it was; it doesn't restart.

### 4.2 Buses and master chain

```
songs ─(part gains · layer gains · stem and weather gates)→ musicBus: HP 35 Hz · high shelf −1.5 dB @ 7 kHz · duck gain ─┐
beds  ─────────────────────────────────────────────────────→ ambienceBus ────────────────────────────────────────────┴→ mixBus: glue 1.5:1 @ −20 dB, knee 6 dB, 30 / 300 ms
sfx   → sfxBus: compressor 2:1 @ −16 dB, knee 6 dB, attack 3 ms, release 150 ms ────────────────────────────────────────────┐   (glue: music and ambience only)
ui    → uiBus ──────────────────────────────────────────────────────────────────────────────────────────────────────────┤
mixBus ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴→ listening preset EQ → limiter (−4 dB, 20:1, knee 0, 1 / 120 ms) → master gain → (mono) → out
reverbs: a music slot (hall in places, room in battles) fed by songs; a place slot (outdoor / room / cave / underwater, chosen by the scene) fed by beds and effects
```

- Effects and UI join **after** the glue, so a hit never pulls the music down (§1's pumping).
- `DynamicsCompressorNode` adds an automatic makeup gain, (1 / curve(1.0))^0.6 by the Web Audio spec, and its knee defaults to 30 dB.
  - `nodes.ts` always sets the knee.
  - It follows each compressor with a GainNode that cancels the makeup.
- **Gain staging.**
  - Volume sliders map to gain = (v / 100)²: 80 → −3.9 dB, 50 → −12 dB.
  - The master slider drives the master gain; the others drive their bus.
  - On normal material the glue should reduce no more than 2 dB. `audio:check` reports it.

### 4.3 Listening presets and mono

| Preset | EQ | Stereo width |
|---|---|---|
| **Phone speaker** (default) | high-pass 90 Hz (12 dB/oct) · peak −2.5 dB @ 3.2 kHz, Q 0.9 · high shelf −2 dB @ 8 kHz | 70% |
| **Headphones** | high-pass 30 Hz · peak −1 dB @ 3.2 kHz · high shelf −1 dB @ 9 kHz | 100% |

**Mono audio** sums the mix to mono after the limiter (an accessibility setting).

### 4.4 Drivers and scheduler

- **Drivers.** The scheduler never reads timers itself; a driver feeds it.
  - The **realtime driver** ticks every 25 ms and reads `currentTime`.
  - The **offline driver** suspends the `OfflineAudioContext` every 100 ms of render time, schedules, then resumes. That lets the real engine render faster than real time.
  - The unit tests drive a fake clock the same way.
- **Lookahead:** schedule every event due within the next 400 ms.
  - An event up to 5 ms late still plays. A later one is dropped and counted in `lateEvents`.
  - Test: 300 ms stalls give zero late events.
- **One transport per song** (tempo, meter, start time), so two songs with different tempos can crossfade.
- **Changes** quantise to `now`, `beat`, `bar` or `section`. Tempo changes (Turnip Sort) happen at bar lines.
- **Layers.**
  - Every part of the playing song is scheduled. Parts in silent layers play at zero gain, so a layer can fade in at any bar with its held notes already sounding.
  - Silent voices are stolen first.

### 4.5 Voices

- **Sampler voice.**
  - It plays the nearest sample of the right articulation within ±4 semitones, preferring the one just below.
  - Playback rate is `2^((midi − root − cents/100)/12)`.
  - Alternate takes rotate.
  - Velocity sets the gain (dB curve) and a per-voice lowpass, so soft notes are darker: about 1.8 kHz at pp up to 12 kHz at f.
- **Envelopes.**
  - Attack ≥ 3 ms; winds and strings take 20–80 ms.
  - Plucks ring to their natural decay and are damped 0.3–1.5 s after the note ends. Winds release in 60–150 ms, pads in 400–800 ms.
  - Every stop is a ramp. Never stop a source without a fade.
- **Monophonic instruments** (ocarina, recorders, flute, clarinet, oboe, bassoon, solo horn line): a new note replaces the old one with a 20 ms crossfade. Phrase starts scoop up 30 cents over 60 ms.
- **Vibrato:** instruments with a vibrato articulation use it for notes of a beat or longer and the plain sustain for shorter ones.
- **Humanising:** timing ±6 ms (drums ±3 ms) and velocity ±6%, from the audio RNG.
- **Fallback voices** (`synth.ts`) play while a pack loads, or if it fails (with one console warning). They are band-limited: sine, triangle, or a PeriodicWave with ≤ 8 harmonics.

  | Instruments | Fallback |
  |---|---|
  | winds: ocarina, recorders, flute, clarinet, oboe, bassoon, horn, tuba | **wind**: a sine with its 2nd harmonic at −30 dB, a breath-noise puff (band-pass 1.5 kHz) at onset, delayed 5 Hz vibrato of ±12 cents, darker for low instruments. A real ocarina is nearly a pure sine (the sample measures its 2nd harmonic at −54 dB), so this is close. |
  | bowed strings, organ, bowed vibes, psaltery | **pad**: 3 detuned triangles → lowpass 1.2 kHz, slow attack |
  | plucked: harp, strumstick, kalimba, pizzicato, harpsichord, piano, music box | **pluck**: Karplus-Strong, rendered once per pitch into cached buffers |
  | struck: marimba, xylophone, vibes, glock, chimes, bells, balafon | **mallet**: 3–4 modal partials with exponential decay |
  | percussion, Foley, wine glasses, ocean drum, didgeridoo | silent until loaded |

- **iOS Safari before 18.4** only partly decodes Ogg Opus, so there the game may stay on fallback voices. That's accepted: the owner plays on Android.

### 4.6 Reverbs

Impulse responses are generated at engine init with the audio RNG:
- decorrelated stereo noise × an exponential decay;
- 6–10 early reflections;
- a lowpass that darkens over the tail.

Set `normalize = false` and calibrate the wet gains.

| Preset | RT60 | Notes |
|---|---|---|
| hall | 2.6 s | 18 ms pre-delay |
| room | 0.9 s | |
| outdoor | 1.4 s | few early reflections |
| cave | 4.5 s | 40 ms pre-delay, darker |
| underwater | 1.8 s | lowpass 900 Hz |

- There are two slots (§4.2), so only two convolvers ever run.
- Changing a slot's preset fades its output out (300 ms), swaps the buffer and fades it back in.
- Songs set only their send level, `musicSend`; the song's kind picks hall or room.

### 4.7 Interrupting stingers, musical effects, ducking, pause

- **Interrupting stinger** (§7.6, 1.5–10 s):
  1. The area music fades out over 150 ms.
  2. The stinger plays on the music bus.
  3. **Straight after it**, the area music restarts at the start of the section after the one it interrupted, with a 1 s fade-in (1.5 s after a drill cue).
- **Musical effect** (≤ 1.5 s): plays on the effects bus, over the music, transposed into the playing song's key and mode. It ducks nothing and never restarts the music.
- **The only duck:** a Special dips the music 3 dB for 1 s (the duck gain in §4.2).
- **A KO** cuts the music as part of the KO sequence (§7.5).
- **Battle pause:** the music lowpasses to 700 Hz and drops 4 dB over 300 ms, and reverses on resume.
- Taps and ordinary hits never change the music.

### 4.8 Debug hook

In dev and e2e builds, `window.__audio` exposes a read-only view for Playwright and the Sound Lab:
- the scene, song, section, layers and stem;
- `musicFilterHz`, `duckDb` and `lateEvents`;
- voices per bus;
- bus peak and loudness;
- the packs loaded, with their decode times;
- the drill-cue timing error.

## 5. Samples

### 5.1 Sources (all CC0; credit them anyway in `CREDITS.md`)

| Library | Where | Pin |
|---|---|---|
| Versilian Community Sample Library (**VCSL**) | `https://github.com/sgossner/VCSL` | commit `c1ea7bcc3c7309650ab0da9d15c9cd1fbc4a4c7e` |
| Versilian Studios Chamber Orchestra 2 Community Edition (**VSCO 2 CE**) | `https://github.com/sgossner/VSCO-2-CE` | commit `440300901dfe9275fd84e0b7763af1f8443ae62e` |
| Kenney **Impact Sounds** (130 files) | `https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip` | record the zip's SHA-256 |
| Kenney **RPG Audio** (50 files) | `https://kenney.nl/media/pages/assets/rpg-audio/8e99002d76-1677590336/kenney_rpg-audio.zip` | record the zip's SHA-256 |

- Both Versilian libraries are WAV files; the ones checked are 44.1 kHz, 24-bit stereo. Download only the files you need (§5.3), never the whole repos, which run to several GB.
- If the Kenney URLs have moved, use the Download link on `https://kenney.nl/assets/impact-sounds` and `https://kenney.nl/assets/rpg-audio`.

### 5.2 Instruments (`recipes/instruments.ts`)

Folder paths are inside each library. Confirm the exact files by listing the repo (`git ls-tree`) at the pin.

| id | Source | Articulations (main dynamic) |
|---|---|---|
| `ocarina` | VCSL `Aerophones/Edge-blown Aerophones/Ocarina, Typical/Sustains/` | `sus` (Sus), `vib` (SusVib) |
| `ocarina-hi` | VCSL `…/Ocarina, Small` | `stac`: quiet ornaments only |
| `recorder-alto` | VCSL `…/Baroque Alto Recorder` | `sus` (Sustain), `vib` (SusVib), `stac` |
| `recorder-tenor` | VCSL `…/Baroque Tenor Recorder` | `sus`, `vib` |
| `recorder-soprano` | VCSL `…/Baroque Soprano Recorder` | `sus` (Sustain), `stac` (there's no vibrato set) |
| `flute` | VSCO `Woodwinds/Flute` | `vib` (susvib), `sus` (susNV), `stac` |
| `clarinet` · `oboe` · `bassoon` | VSCO `Woodwinds/Clarinet` · `Oboe` · `Bassoon` | `sus`, `stac` (confirm folder names) |
| `horn` | VSCO `Brass/F Horn` | `sus`, `stac` |
| `tuba` | VSCO `Brass/Tuba` | `stac` |
| `violins` | VSCO `Strings/Violin Section` | `vib` (susVib), `pizz`, `spic`, `trem` |
| `violas` | VSCO `Strings/Viola Section` | `vib` (susvib), `pizz` |
| `cellos` | VSCO `Strings/Cello Section` | `vib` (susvib), `pizz` (pizzT), `spic`, `trem` |
| `contrabass` | VSCO `Strings/Solo Contrabass` | `pizz`, `sus` (SusNV) |
| `harp` | VCSL `Chordophones/Composite Chordophones/Folk Harp` | `pluck`: v2 is the main take, v3 the level-matched alternate |
| `strumstick` | VCSL `…/Strumstick/Finger` | `pluck`: one velocity layer, the next as the alternate |
| `kalimba` | VCSL `Idiophones/Plucked Idiophones/Kalimba, Tanzania` | `pluck`: one take |
| `marimba` | VCSL `Idiophones/Struck Idiophones/Marimba` | `hit`: soft is the main take, med the level-matched alternate |
| `xylophone` · `glock` · `hand-chimes` · `tubular-bells` | VCSL `…/Xylophone` · `…/Glockenspiel` · `…/Hand Chimes` · `…/Tubular Bells 1` | `hit` |
| `vibes` | VCSL `…/Vibraphone` | `hit` (Soft Mallets), `bowed` |
| `wine-glasses` | VCSL `Idiophones/Friction Idiophones/Wine Glasses` | `slow`, `fast` |
| `psaltery` · `organ` | VCSL `Chordophones/Zithers/Psaltery, Bowed and Plucked` · `Aerophones/Edge-blown Aerophones/Renaissance Organ` | `bowed` · one soft stop |
| `harpsichord` · `piano` · `balafon` | VCSL `…/Harpsichord, Flemish` · `…/Upright Piano, Yamaha` · `…/Balafon` | `pluck` · `hit` · `hit` (the softest mallet there is) |
| `didgeridoo` · `ocean-drum` | VCSL `Aerophones/Lip Aerophones/Didgeridoo` · `Membranophones/Other Membranophones/Ocean Drum` | quiet drones · swells |
| Percussion | VCSL: `frame-drum`, `shaker` (Shaker, Small), `woodblock`, `claves`, `claps`, `tambourine` (Tambourine 1), `finger-cymbals`, `triangle` (Triangles), `mark-trees`, `bell-tree`, `sleigh-bells`, `timpani` (Timpani 1: hits and rolls), `bass-drum` (Bass Drum 1, soft hits), `darbuka`, `bongos`, `cajon`, `cymbal-swell` (Suspended Cymbal 1: mallet rolls and swells) | |
| `foley` | Kenney: e.g. `footstep_grass_*`, `footstep_snow_*`, `footstep_wood_*`, `footstep_concrete_*`, `impactWood_*`, `impactSoft_*`, `impactPlank_*`, `impactMining_*`, `impactPunch_*`, `creak*`, `cloth*`, `handleCoins*`, `bookFlip*` | |

- **`music-box`** is a patch, not a sample set: `kalimba` notes above C5 with the decay cut to 0.8 s, plus `glock` an octave up at −12 dB.
- **Ranges.** Every instrument has `range.playable` (its samples ±4 semitones) and `range.melody` (set by hand, inside playable). The checker, the generators, the event table's transpositions and the monster songs all use these.
- **Packs are computed, not hand-listed.** The pipeline builds a usage graph from the songs, beds, effect recipes and drill cues, and assigns each instrument to a pack:

  | Pack | What goes in it | When it loads |
  |---|---|---|
  | `core` | anything the ranch, the town (every stem), the UI, the drills, the world effects or the battle effects use | after unlock |
  | `events` | anything used only by event themes and their stingers | when a cup screen opens |
  | `places` | the rest | with its place |

  A test checks that every instrument a context uses is in a pack that's loaded there. The packs are rebuilt at every stage.

### 5.3 The pipeline: `npm run audio:samples` (`tools/audio/build-samples.ts`)

1. **Fetch only what's needed.**
   - For the two Versilian libraries: a blobless clone with a non-cone sparse checkout of the exact files, into `tools/audio/.cache/` (gitignored).
   - For Kenney: download the two zips.
   - Choose files by rule:
     - the main dynamic per articulation, as named in §5.2;
     - an alternate take only where §5.2 names one;
     - notes about every 3 semitones across the instrument's playable range, plus one beyond each end;
     - ≤ 14 samples per articulation.
2. **Detect each sample's real pitch. Don't trust file names.**
   - Run YIN or autocorrelation on the steady part.
   - VCSL names middle C "C3". Measured: `StdOcarina_SusVib_A4.wav` sounds at about 890 Hz, which is A5.
   - Store the measured MIDI note plus a cents offset.
   - Fail the build if the measured pitch class disagrees with the name by more than 50 cents.
   - For inharmonic instruments (glock, chimes, bells, kalimba), trust the name's pitch class, with the octave taken from the library's convention as measured on its harmonic instruments.
3. **Clean.**
   - Fold to mono.
   - Trim leading silence to −50 dB, keeping the attack.
   - Level-match all notes of one articulation (RMS of the first 300 ms), then set the instrument's peak to −3 dBFS.
   - Cap the lengths:

     | Class | Cap |
     |---|---|
     | Sustains | 1.2 s plus the loop region |
     | Plucks and struck | ≤ 2.5 s (low harp, vibes, tubular bells and chimes ≤ 4 s) |
     | Drums | ≤ 1.2 s |
     | Ringing or rolled percussion (`cymbal-swell`, timpani rolls, `ocean-drum`, `triangle`, `finger-cymbals`, `mark-trees`, `bell-tree`, `sleigh-bells`) | ≤ 6 s |

   - Every decay ends at −50 dB with a 30 ms fade.
4. **Loop sustains.** Always bake an equal-power crossfade loop of at least 50 ms into the file.
5. **Encode** Opus, 48 kHz, mono, in `.ogg`: 64 kbps, or 80 kbps for drums, bells and glass. Use `ffmpeg` if it's on PATH, otherwise the `ffmpeg-static` devDependency.
   - Check that `ffmpeg -encoders` lists `libopus`.
   - If it doesn't, use Ogg Vorbis at q4 and say so in PROGRESS.
6. **Measure on the decoded output.** Decode each encoded file again and store its onset and loop points **in seconds**, measured on that decoded audio. Opus pre-skip and resampling can't then shift them.
7. **Write** the files to `public/audio/<pack>/<instrument>/…` and `public/audio/manifest.json`. For each sample the manifest holds: file, instrument, articulation, dynamic, root MIDI, cents, take, onset, loopStart, loopEnd and trim gain.
8. **Report** the sizes and decoded seconds per pack, and fail over budget (§2).

Commit the processed files, which are small, and never the raw downloads.

### 5.4 Runtime and offline

- Packs decode with `decodeAudioData` and are cached in memory, then released per §2.
- `audio:check` decodes every file in Chrome and compares it with the manifest:
  - onset within ±1 ms;
  - length within one 20 ms Opus frame;
  - the loop points.
- PWA:
  - Add `ogg` to the Workbox `globPatterns`, and keep `json` there, so the manifest and all audio are precached and the game sounds right offline.
  - Raise `maximumFileSizeToCacheInBytes` if any file needs it.

## 6. Writing music

### 6.1 A song file

Each piece is one TypeScript file in `src/audio/music/songs/`.
- **The ABC headers are the only source** of tempo (`Q:`), meter (`M:`) and key (`K:`).
- **The TypeScript holds the rest:**
  - the kind;
  - the parts, accompaniment and percussion lines, each with an **id**, a **role** (`lead`, `counter`, `accomp`, `bass`, `perc`, `colour`) and its own **layers**;
  - the form;
  - the weather rules and stems.

A shape example, not a real piece:

```ts
export default defineSong({
  id: 'ranch-spring',
  kind: 'ranch',          // place | ranch | town | battle | drill | stinger | effect | drone | minigame (§6.7)
  brief: 'One sentence: the place, the mood, what the listener should feel.',
  energy: 2,
  musicSend: 0.25,
  swing: 0.5,             // 8th-note swing ratio, 0.5 (straight) to 0.62
  abc: `
X:1
M:6/8
L:1/8
Q:3/8=60
K:G mix
V:chords
[P:A] "G"z6 | "F/G"z6 | ...
V:lead
[P:A] d2B G2A | B3- B2z | ...
V:counter
[P:A] z6 | ...
`,
  parts: {
    lead:    { inst: 'ocarina', role: 'lead', layers: ['main'], gain: 0, pan: 0.05 },
    counter: { inst: 'recorder-alto', role: 'counter', layers: ['main'], gain: -4, pan: -0.2 },
  },
  accomp: {
    harp:    { inst: 'harp', role: 'accomp', pattern: 'harpArp', layers: ['main'], octave: 3, gain: -6 },
    pizz:    { inst: 'cellos', art: 'pizz', role: 'bass', pattern: 'pizzWalk', layers: ['main'], gain: -9 },
    pad:     { inst: 'violas', art: 'vib', role: 'accomp', pattern: 'padSustain', layers: ['weather'], gain: -14 },
    sparkle: { inst: 'glock', role: 'colour', pattern: 'flourish', layers: ['weather'], gain: -16 },
  },
  perc: {
    grid: 12,
    lines: {
      drum:   { inst: 'frame-drum', role: 'perc', layers: ['main'], steps: 'X.....x.....' },
      shaker: { inst: 'shaker', role: 'perc', layers: ['main'], steps: '..x..x..x..x' },
    },
  },
  order: ['intro', 'A', 'B', 'A2', 'breath', 'B2', 'A3'], loopFrom: 1,
  breath: [8, 20],
  weather: {
    cloudy: { gainDb: -1.5 },
    rain:   { mute: ['drum', 'shaker', 'counter'], add: ['pad'], swap: { lead: 'vibes' } },
    storm:  { mute: ['drum', 'shaker', 'counter', 'pizz'], add: ['pad'], fragments: ['lead'], breath: [15, 30] },
  },
  stems: {},
})
```

### 6.2 The ABC subset (`music/abc.ts`)

**Supported**
- **Headers:** `X: T: M: L: Q: K: V: P:`.
  - Meters: 2/4, 3/4, 4/4, 6/8, 9/8, 12/8, C.
  - Keys may carry modes (`K:D lyd`, `K:E dor`, `K:A min`).
  - Keys may carry explicit accidentals, as in ABC 2.1:
    - `K:A phr ^c` is A Phrygian dominant;
    - `K:C min =b` is C harmonic minor.
- **Notes:**
  - `C–B c–b` with `,` and `'` for octaves.
  - Accidentals `^ ^^ _ __ =`, which last to the end of the bar.
  - Durations: `A2 A/2 A/ A3/2`, and broken rhythm `A>B A<B`.
- **Other symbols:**
  - Rests `z` and `x`.
  - Ties `-`.
  - Chords `[CEG]`.
  - Triplets `(3abc`.
  - Grace notes `{g}`: a 35 ms ornament for winds.
- **Chord symbols** in quotes (`"Dm7"`, `"G/B"`). They belong in a `V:chords` voice of rests and feed the generators (§6.3).
- **Dynamics:** `!pp! !p! !mp! !mf! !f!` and `!crescendo(! … !crescendo)!` (also `diminuendo`).
- **Bars and structure:**
  - Bar lines `| || |] [|`.
  - Repeats `|: :| ::` and endings `[1 [2`.
  - Inline `[K:…] [M:…] [Q:…] [P:…]`. `[P:name]` marks a section.
- Comments `%`.

**Anything else throws** with its line and column.

**Checks:** every bar fills its meter (a pickup is allowed only in bar 1), and every voice has the same length in each section.

### 6.3 Accompaniment generators (`music/patterns.ts`)

Input: the chord track, meter, tempo, the instrument's range, a pattern name and parameters (octave, density, spread). Output: note events. The voicing:
- moves as little as possible from chord to chord;
- stays inside the instrument's range;
- puts the root (or the slash bass) at the bottom.

| Pattern | What it plays |
|---|---|
| `harpArp` | broken chords: 1-5-8-10 rising and falling in 4/4, in 3/4 and in 6/8; open or close spread |
| `waltz` | bass on 1, chord on 2 and 3 |
| `strum` | strumstick chords, down and up strokes, 15 ms between strings |
| `pizzWalk` | root-5-6-5 or root-3-5-6 with approach notes into the next chord |
| `kalimbaOstinato` | chord tones in syncopated 16ths (3+3+2) |
| `padSustain` | chords held one or two bars, voice-led, slow attack |
| `pulse` | 8th-note chord tones for battle drive (spiccato strings) |
| `tremolo` | string tremolo for tension |
| `bassRoot` | root on 1 (and 3), optional octave jumps |
| `drone` | tonic and fifth pedal |
| `flourish` | a quick rise to the top of the chord at section ends |

### 6.4 Percussion and kits (`music/perc.ts`, `recipes/kits.ts`)

- **Lines** are step strings, one bar per segment: `X` accent, `x` normal, `o` ghost, `.` rest.
  - `grid` is the steps per bar: 16 for 4/4, 12 for 3/4 or 6/8.
- **Battle songs** write their lines by role (`low`, `mid`, `high`, `shaker`, `accent`).
- **A kit** is a map from role to instrument, so an arrangement can swap the kit:

  | Kit | low | mid | high | shaker | accent |
  |---|---|---|---|---|---|
  | `meadow` | frame drum | none | none | shaker | tambourine |
  | `festival` | cajon | bongos | none | shaker | claps |
  | `harvest` | frame drum | darbuka | woodblock | none | tambourine |
  | `frost` | timpani | none | sleigh bells | none | finger cymbals |
  | `ceremony` | timpani | bass drum | triangle | none | cymbal swell |
  | `knockout` | cajon | darbuka | claves | none | claps |
  | `wild` | frame drum | darbuka | none | shaker | bass drum |

- **Pitched percussion** (timpani, tubular bells) takes `pitch: 'root' | 'fifth'` from the chord track.

### 6.5 Form, layers, stems, weather, variants

- **Sections** are labelled `[P:…]`.
  - `order` gives the play order, variations included, and `loopFrom` says where the loop restarts.
  - `breath` is a section with no music. Its length is drawn from `breath: [min, max]` with the audio RNG on every pass. Only ranch songs have one.
- **Layers by kind:**

  | Kind | Layers |
  |---|---|
  | `place`, `ranch`, `town` | `main`, plus `weather` parts that only weather rules switch on |
  | `battle` | `lobby`, `base`, `drive`, `tension` |
  | `drill`, `stinger`, `effect`, `drone`, `minigame` | `main` |

- **Which lines sound.** A part, accompaniment or percussion line sounds when all of these hold:
  - it's in the active stem, or no stem is active;
  - at least one of its layers is on;
  - weather hasn't muted it.
- **Stems** are named lists of line ids. The Town sub-screens use them (§7.3) so the music never restarts between shops.
- **Weather rules** (ranch songs) take effect at the next phrase. A rule may hold:
  - `mute`: line ids;
  - `add`: lines in the `weather` layer;
  - `swap`: a line's instrument, e.g. `{ lead: 'vibes' }`;
  - `fragments`: the line plays only bars 1–2 of every 4;
  - `gainDb`;
  - `breath`.
- **Variants** that change notes, such as Rogue's Rally (Aeolian) and the Elders' Cup, are separate files.
  - They share the original's chord track and set `derivedFrom`.
  - Variants that only change instruments or layers, like the Summit Qualifier, are arrangement data, not new files.

### 6.6 Performance

The engine performs the notes:
- humanising (§4.5);
- phrase shaping, rising to the phrase peak and easing at its end;
- vibrato chosen by note length;
- scoops at phrase starts;
- winds breathing at rests;
- harp chords rolled by 10–25 ms;
- alternate takes on plucks.

### 6.7 The music checker (`music/checker.ts`, run over every song in Vitest, shown in the Sound Lab)

The song's `kind` picks its tempo band and length bounds (§3.2) and which rules apply.

1. It parses, every bar is the right length, and the voices line up.
2. Every note is inside its instrument's `range.playable`, and lead and counter notes inside `range.melody`. Each note is within ±4 semitones of a sample of its articulation.
3. Monophonic instruments never overlap.
4. Wind leads breathe: never more than 4 bars or 8 s without a rest of at least an 8th.
5. **Lead and counter parts** (all kinds except `drone`):
   - 55–85% of moves are steps (≤ 2 semitones).
   - No leap is wider than an octave.
   - At least 80% of leaps wider than a 5th are followed by a step the other way.
   - Phrase-final notes are chord tones.
6. **Downbeats:** the lead is a chord tone, or a suspension that resolves by step within the bar. Flag minor 2nds and major 7ths against the bass.
7. The lead sits at least a 3rd above the highest accompaniment note on strong beats (a warning).
8. The tempo is inside the kind's band and the loop length inside its bounds.
9. **Variety** (`place`, `ranch`, `town` and `battle` only):
   - At least two contrasting sections.
   - Identical lead bars ≤ 35%.
   - At least one varied repeat (A′).
10. **Register and density:**
    - Nothing above C7 except bright colours at p or softer.
    - Sustained notes above A5 are mp or softer.
    - Melodic voices at once ≤ 4 in places and ≤ 6 in battles.
11. Bright colours never carry more than 2 bars alone (a warning).
12. **The Wildsong motif** is present where §3.6 requires it.
13. **Distinctness:** no two songs share a 2-bar lead sequence of intervals and rhythm. Motif quotes and `derivedFrom` pairs are exempt.
14. No banned instrument (§3.1) and no banned waveform (§14.1).

The checker also runs rules 2 and 3 on every row of the event table (§7.4), with its lead swap and transposition applied.

`npm run audio:analyze` prints, for each song: key, tempo, length, range, step %, leaps, repetition, layers and warnings.

### 6.8 How to compose each piece

1. Write the brief: place, mood, energy level and palette.
2. Write a chord chart in the mode, with the form and section lengths.
3. Write the melody to the chart. Build it from a 1–2 bar motif with question-and-answer phrases: 4 + 4 bars, then 8 more.
4. Add a countermelody that answers in the gaps.
5. Choose the accompaniment patterns and the percussion.
6. Run the checker and fix every error, plus any warnings that make sense.
7. Render the review file (§14.4), and write one line in PROGRESS.md on what the piece should sound like, so the owner can judge it.

## 7. The music map

### 7.1 Places

Ambience ids are from §9.2.

| Screen | Music | Ambience |
|---|---|---|
| `title` · `credits` | **Wildsong** (the main theme) | `meadow` (light) |
| `newGame` | Wildsong, lobby arrangement | `meadow` |
| `creditsRoll` | Wildsong, full credits arrangement (2–3 min, every section, a grand ending) | none |
| `ranch` · `ranchCard` · `bag` · `songbook` | the ranch song for the season (§7.2) | the season's ranch bed and the weather overlay |
| `town` · `mail` · `upgrades` · `oddJobs` (menu) | **Town**, with the stem for that screen (§7.3) | `town` |
| `shop` · `market` · `guild` | Town stems | `shop` · `market` · `guild` |
| `library` · `journal` | Town stems | `library` |
| `shrine` | **Shrine** | `shrine` |
| `pell` | **Pell's Lab** | `lab` |
| `lab` · `labCreate` · `labView` · `labEdit` · `labImport` · `labExport` · `labEffects` · `labVersus` (setup) | **Monster Lab** | `studio` |
| `labSound` | silent; it plays only what you audition | none |
| `journey` | **Journey**, in the site's arrangement | the site's bed |
| `expedition` | the site's **Expedition** piece | the site's bed |
| `farewell` | the farewell sequence (§7.6) | `dusk` |
| `tournament` (entry) | the `cup` lobby in this season's palette | `arena-out` |
| `tournamentPlay` · `tournamentResults` | the event's lobby layer | `arena`, with the event's crowd |
| `battle` | the battle for its origin (§7.5) | `arena` (none in Trials and the Lab) |
| Turnip Sort · Echo Stones | **Turnip Sort** · the **Echo Stones** drone | `barn` · `shrine` |
| `settings` · `calendar` | keep whatever is playing | |

Sheets and overlays never change the music: the food prompt, request card, Train sheet, planner, week summary, item sheets and the pause sheet (beyond its lowpass, §4.7).

### 7.2 The ranch: four seasons × weather

| Season | Key · meter · tempo | Palette | Ambience |
|---|---|---|---|
| Spring | G Mixolydian · 6/8 · ♩. = 60 | ocarina and alto recorder, harp, cello pizz, shaker | `meadow` with `brook` |
| Summer | C Lydian · 4/4 · 84, swing 0.56 | marimba and flute, kalimba ostinato, soft bongos | `summer-field` |
| Autumn | D Dorian · 3/4 · 88 | ocarina with a cello countermelody, strumstick, frame drum | `autumn-wind` |
| Winter | A Aeolian · 4/4 · 66, sparse | soft vibes doubled by glock, harp, bowed vibes, sleigh bells on downbeats in B | `winter-yard` |

The form is A, B, A′, a breath, then B′, A″, and so on.

| Weather | Music (a rule in each song, §6.5) | Ambience overlay (§9.3) |
|---|---|---|
| Sunny | the full arrangement | more birds |
| Cloudy | `gainDb: -1.5`; bright doubles muted | more wind |
| Rain | percussion and counter muted; the lead swaps to harp or vibes; a soft pad added | rain |
| Storm | only the pad, harp and lead `fragments`; breaths of 15–30 s | storm |
| Snow (winter) | a glock `sparkle` line added | muffled |

### 7.3 Town stems (one piece: F major, 3/4 folk waltz, 108)

| Screen | Stem |
|---|---|
| `town` | everything: strumstick and alto recorder lead, pizz, frame drum, light tambourine |
| `shop` | kalimba, harp, bass |
| `market` | everything, plus tambourine and claps |
| `guild` | proud: plus horn and soft timpani, no tambourine |
| `library` · `journal` | harp and `music-box` · `music-box` and harp |
| `mail` | pizz and kalimba |
| `upgrades` | the workshop: woodblock, strumstick, recorder |
| `oddJobs` | the fair: recorder, tambourine, pizz |

All stems share the key and tempo, and switch at the next bar.

### 7.4 Events

**Compositions** (S2, except `cup`, which is S1):

| id | Used for | Mood · key · meter · tempo | Palette |
|---|---|---|---|
| `cup` | every regular cup (round robin and elimination) | bright, sporting folk · E Dorian · 4/4 · 120 | season palette and kit (below) |
| `open` | the New Year Open | a winter festival · A Mixolydian · 4/4 · 126 | horn, strumstick, glock; kit `festival` |
| `ascension` | the four Ascensions (the promotion fights) | ceremonial, a proud march · B♭ Ionian · 4/4 · 112 | horn, strings, harp; kit `ceremony`; the lobby is a processional on organ and horn; tinted by season |
| `crown-dawn` | Crown of Dawn | sunrise, hopeful · D Lydian · 4/4 · 116 | rising violins, horn calls, harp, glock |
| `crown-tides` | Crown of Tides | a rolling sea · G Dorian · 6/8 · ♩. = 76 | harp waves, flute, cellos, ocean-drum swells, frame drum |
| `crown-embers` | Crown of Embers | warm fire · `K:A phr ^c` · 4/4 · 126 | strumstick strums, cello spiccato, low flute; kit `harvest` |
| `crown-frost` | Crown of Frost | crystalline · B Aeolian · 3/4 · 108 | wine glasses, vibes, violin tremolo, harp; kit `frost` |
| `legend` | The Wildsong Legend | the main theme as a grand battle · D Lydian · 4/4 · 120 | horn, strings, harp, an ocarina solo in the breakdown; kit `ceremony` |
| `masquerade` | the Masquerade Cup | a masked ball · `K:C min =b` · 3/4 · 126 | harpsichord, pizz, clarinet, finger cymbals, the masked motif |
| `rival` | the Rival Showdown, and any match against Corin Hale | confident, cheeky · G Mixolydian · 4/4 · 124 | horn, violin spiccato, strumstick, Corin's motif; kit `festival`. In another event it takes that event's lead and kit. |
| `summit` | the Vale–Coast Summit; the Summit Qualifier uses fewer layers | a festival team anthem, call and response · F Ionian · 4/4 · 116 | the Vale on ocarina and recorder, the Coast on flute and horn; claps on 2 and 4 |
| `rally` · `rally-rogue` | Hero's Rally · Rogue's Rally (`derivedFrom: 'rally'`) | E Ionian · E Aeolian, sly · 4/4 · 118 | horn lead · clarinet and pizz |
| `sprout` · `elders` | the Sprout Cup · the Elders' Cup (`derivedFrom: 'sprout'`) | F Ionian · 4/4 · 108 · 100, nostalgic | glock, kalimba, `music-box` · harp, cellos, tenor recorder |
| `trial` | Journey Trials | wild, earthy · E Dorian, transposed to the site's tonic · 4/4 · 116 | the site's lead (below); kit `wild` |
| `practice` | Monster Lab Versus and the Battle Lab | light, neutral · C Ionian · 4/4 · 112 | marimba, pizz, shaker |

**Journey sites** (used by `trial` in S2 and the Journey arrangements in S3):

| Site | Tonic | Lead |
|---|---|---|
| Iron Quarry | E | tenor recorder |
| Windrun Steppe | A | flute |
| Starfall Observatory | B | vibes doubled with wine glass |
| Archer's Glade | G | alto recorder and balafon |
| Glacier Bastion | D | violin tremolo and vibes |

**Season palettes** (for `cup`, and to tint `ascension`):

| Season | Leads | Kit | Colour |
|---|---|---|---|
| Spring | flute, alto recorder | `meadow` | harp |
| Summer | marimba, kalimba | `festival` | glock |
| Autumn | ocarina, cellos | `harvest` | strumstick |
| Winter | vibes, violins | `frost` | glock |

**The per-event arrangement table** (`recipes/events.ts`) has one row for every event in `data/calendar.ts`, 60 today. Each row holds:
- the theme;
- the palette and kit;
- the lead;
- the transposition (−3…+3 semitones);
- the tempo nudge (−6…+6, in quarter-note BPM);
- the crowd (§9.4);
- a note.

Rules for the rows:
- **Regular cups:**
  - Neighbouring cups never share both lead and kit.
  - Elimination cups use the `knockout` kit, a drier reverb send and +4 BPM.
- **Rule cups:**
  - `powOnly` (the Iron Cup) gets a heavier kit and cello drive.
  - `intOnly` (the Arcane Cup) gets a glassy colour: vibes doubled with wine glasses.
  - `hero` / `rogue` use `rally` / `rally-rogue`; `sprout` / `elders` use `sprout` / `elders`.
- **Named festivals** get a colour of their own. For example:
  - the Lantern Festival: glock and hand chimes;
  - Kite Day: flute and light tambourine;
  - Firefly, Snowflake and Starlight: Claude's choice.

A test checks every row:
- every event has a row;
- the theme, instruments and kit exist;
- the effective tempo (base + variant + nudge, in quarter-note BPM) is 100–132;
- checker rules 2–3 pass with the row's lead and transposition.

It's plain data the owner can edit.

### 7.5 Battles

1. **Lobby** (cup screens, round preview, standings, results after their stinger): the event theme's `lobby` layer. A rival's calling card plays over it when the preview shows them (S2).
2. **Match start:** the song restarts at its first battle section on the next beat.
   - On that downbeat it plays a frame-drum hit and a harp chord, written into the song.
   - `base` plays for bars 1–2, then `drive` from bar 3.
3. **Tension:** when either fighter is at or below 30% HP, or 10 s are left, the `tension` layer comes in at the next bar and stays.
4. **A Special** gets its element swell (§10.3), and the music dips 3 dB for 1 s.
5. **KO:** the music cuts over 150 ms. The KO sound plays, then the `matchWin` or `matchLoss` stinger, then the lobby restarts at its lobby section.
6. **Time up:** `matchWin`, `matchLoss` or `matchDraw`.
7. **Pause** lowpasses the music (§4.7). Speed ×2 and ×4 leave the music alone; effects thin out (§10.1). **Skip** plays no battle music, only the result stinger.
8. Journey Trials use `trial` at the site's tonic; the Lab uses `practice`.

### 7.6 Stingers and moments

**Interrupting stingers** (§4.7, 1.5–10 s). They're written in C and transposed to the area song's tonic, within instrument ranges.

| id | What | Stage |
|---|---|---|
| `matchWin` · `matchLoss` · `matchDraw` | the end of a match | S1 |
| `cupWin` (6 s) | first place | S1 |
| `promotion` (6 s) | "Ascended!", from `ascension` | S1 |
| `cupPlaced` (3 s) · `cupOut` (2 s, gentle) | second or third place · knocked out | S2 |
| `crownWon` (8 s) | from that Crown's theme | S2 |
| `legendWon` (10 s) | becomes the Hall of Fame anthem from Wildsong | S2 |
| `rankUp` (4 s) · `titleEarned` (2 s) | | S2 |
| `birth` (6 s) | at the Shrine: the monster's song on ocarina over harp and glock; the stones answer with the Wildsong motif | S3 |
| `farewell` | the monster's song slowly on solo ocarina with a long reverb, then the Wildsong motif on harp; the screen then loops a quiet farewell arrangement | S3 |
| `birthday` (3 s) · `monsterSong` (the Monster Card's ♪, 3 s) | the monster's song as a music box · as written | S3 |
| `rest` (4 s) · `play` (3 s) | a music-box lullaby in 3/4 · a playful kalimba phrase | S3 |
| `journeyDepart` · `journeyReturn` | a frame drum and a recorder phrase | S3 |

Until S2 and S3, moments without their own stinger use the nearest S1 one (§15).

**Musical effects** (§4.7, ≤ 1.5 s, over the music, in its key):

| id | Sound | Stage |
|---|---|---|
| `coin` · `buy` | a soft glock note plus Kenney coins | S1 |
| `mail` | mark trees and a hand chime | S1 |
| `itemGet` | a harp and glock arpeggio | S1 |
| `sweet` | a kalimba lift | S1 |
| `learnTechnique` | a Songsheet: a 4-note ocarina phrase over harp | S1 |
| `plannerStop` | two soft harp notes | S1 |
| `growUp` · `prime` | a rising harp and horn phrase · a warm chord bloom | S1 |
| `weekStart` | a bird and a soft harp chord | S1 |
| `wrenReport` | two kalimba notes | S1 |
| rival calling cards | §3.6 | S2 |
| `fusion` | a bowed-vibes swell and glass | S3 |
| `expeditionTreasure` · `expeditionEvent` | a chest creak and a glock arpeggio · a soft cue | S3 |

### 7.7 Monster songs (`music/monsterSong.ts`)

- **Made from:** the monster's `seedPhrase` plus its main and sub breed, hashed with `cyrb53` (the monster's `id` if the phrase is empty). The same monster always has the same song, and nothing is added to the save.
- **Mode, from the main breed's default element (V1):**

  | Element | Mode |
  |---|---|
  | Fire, Earth | Mixolydian |
  | Water | Dorian |
  | Ice, Dark | Aeolian |
  | Lightning, Wind, Light | Lydian |
  | Nature, Physical | Ionian |
  | Sound | major pentatonic |

  For the breeds with a split INT/POW default, use the INT one.
- **Key:** `cyrb53(subBreedId) mod 12`, placed so the song sits inside the ocarina's `range.melody`.
- **Shape:**
  - 6–8 notes over 2 bars of 3/4 or 4/4.
  - It starts on scale degree 1, 3 or 5 and ends on 1.
  - Mostly steps, with one leap of a 6th at most.
  - The rhythm comes from 8 cells.
  - It must pass checker rule 5.
- **Where it plays:** `birth`, `monsterSong`, `birthday`, `farewell`, and the Hall of Fame plaque.
- **Tests:** deterministic; 1,000 random phrases all valid, and at least 900 of them distinct.

## 8. Training soundscapes

### 8.1 Cue timing

**`drillCue.start(drillId, outcome, { vignetteMs })` returns `resultAt`**, the audio-clock time when the result should show. It then:
1. Fades out the area music over 0.4 s. The ranch bed fades out on the same curve the drill bed fades in on (0.3 s).
2. Plays the drill bed: its ambience, Foley on its timeline, and the music bed (2–4 bars, looping).
3. Plays the outcome stinger at `resultAt`.

**`DrillResult`** switches to its `result` phase at `resultAt`, within ±25 ms (logged in `window.__audio`). If audio is off or not unlocked, it uses its own timer, as today.

**Other calls and rules:**
- **`drillCue.skip()`:** the bed fades in 80 ms and the stinger plays at once; `DrillResult` switches at once.
- **`drillCue.end()`** (when the result closes): the drill bed fades over 1 s. The ranch bed returns, and the ranch music restarts at its next section with a 1.5 s fade-in.
- **Instant speed, or the planner running several weeks:** the stinger only, at −6 dB.
- **Timing:** today the vignette is 2.2 s × the speed factor. V4's 5 s cutaways will pass timeline markers (`impact`, `splash`, …), so build the Foley timeline around named markers with a default timing.

### 8.2 The eleven drills

| Drill | Place and ambience | Foley | Music bed | Notes |
|---|---|---|---|---|
| Hill Sprints (LIF) | `meadow`: the grassy hill behind the barn, breeze, far high birds | footsteps on grass (`footstep_grass`) in a jog that matches the tempo | G Ionian · 2/4 · 132: alto recorder over cello pizz and shaker | Great adds a harp run to the top |
| Log Toss (POW) | `farm` | cloth rustle, whoosh, heavy wood thud (`impactWood_heavy`), fence rattle (`impactPlank`) | D Mixolydian · 4/4 · 96 work-song stomp: frame drum on 1 and 3, cello spiccato, strumstick | |
| Puzzle Stones (INT) | `garden` | stone slide (filtered noise), a wooden clunk as each stone seats; each seated stone plays the next note of a rising kalimba arpeggio | F Lydian · 3/4 · 84: kalimba and marimba | `music-box` sparkle on Great |
| Target Toss (SKI) | `meadow` | throw whoosh, pinecone "tock" on the wooden target (woodblock and `impactWood_light`), misses rustle in the grass | C Ionian · 6/8 · ♩. = 72: violin pizz and soprano recorder | each hit pings a glock note in key |
| Dodge the Gourds (SPD) | `barn` | gourds swishing past left↔right (panned noise sweeps), quick scuffs (`footstep_wood`) | B♭ Ionian · 2/4 · 120: xylophone, bassoon staccato, woodblock | comic, light |
| Acorn Shower (DEF) | `oak` | acorns pattering (many tiny wood clicks, quiet) | E Dorian · 4/4 · 100: clarinet, bassoon and pizz on a steady "stand firm" ostinato | |
| Plow Pull (POW·LIF) | `farm` (wider) | the plow dragging (low filtered noise that swells with each step), heavy steps (`impactSoft_heavy`), harness creak | A Aeolian · 4/4 · 72: cellos and contrabass sustained, soft timpani on each step, a tenor-recorder work song | |
| Moon Meditation (INT·SKI) | `night`, plus a rare low recorder "owl" note | one slow breath swell | B Lydian · 4/4 · 56, almost free: wine glasses, bowed vibes, single harp notes | the calmest cue in the game |
| Wind Chase (SPD·INT) | `windmill` | leaves skittering | G Lydian · 6/8 · ♩. = 84: flute runs over harp, light tambourine | |
| **Waterfall Stand** (DEF·LIF), **the S1 pilot** | `waterfall-near` (§9.2), the star of the cue | a surge hitting the monster every 1.2 ± 0.2 s (a splash burst over the bed) | D Dorian · 4/4 · 80: cello drone, ocarina melody, harp, mixed under the roar (music −6 dB against the bed) | Great: a harp glissando and a high ocarina note ring out through the roar. Fail: the roar swells over a falling phrase |
| Quarry Haul (LIF·DEF) | `quarry` | stone scrape and drop thud | E Mixolydian · 4/4 · 76: tenor recorder, timpani, low strings, echoing | |

### 8.3 Outcome stingers (five per drill, in the cue's key and instruments, 1.2–2.5 s)

| Outcome | Stinger |
|---|---|
| Great | a rising phrase to the octave with a bright double (glock or harp glissando): joyful, not loud |
| Success | a warm modal cadence (IV–I or ♭VII–I), 2–3 notes on the lead |
| Cheat | a sly chromatic slide or trill on the lead, plus one pizz or woodblock plink |
| Fail | a soft falling 3rd or 4th that doesn't resolve, lower down: sympathetic, never a buzzer or a "wah-wah" |
| Slacked | every bed voice's playback rate ramps down 15% over 0.8 s (so the pitch sags too), then a sleepy two-note yawn on tenor recorder and soft breathing |

## 9. Ambience

### 9.1 Building blocks (`engine/ambience.ts`)

- **Noise:** only white-noise buffers are looped: 8 s each, seeded, with a crossfaded seam baked in.
  - Pink and brown noise are made from them at runtime with filters (IIRFilterNode or biquads).
  - Every instance starts at a random offset.
- **Shaping:** biquad filters, and slow movement from an LFO plus a seeded random walk updated every 250 ms (±dB, ±Hz).
- **Spawners** of one-shot events: a Poisson rate with random pan, pitch and level. The events can be samples (VCSL, Kenney) or synth: chirp, click, drip, crackle, creak, bubble.
- **Stereo:** two decorrelated sources per stereo bed.
- **Beds** are named sets of layers.
  - Beds crossfade over 2 s, except in a drill cue (§8.1).
  - Weather overlays add or remove layers.
- **Recorded beds later:** if a CC0 recording is dropped in at `public/audio/beds/<id>.ogg` (and logged in `CREDITS.md`), it replaces that bed's procedural layers. Nothing ships with one in Sound 2.0.

### 9.2 Recipes (`recipes/ambience.ts`)

The levels below are starting points, in dBFS, for each layer alone at default settings. Calibration (§14.3) sets each bed's overall level and keeps the balance between its layers.

| Bed | Layers | Used by |
|---|---|---|
| `meadow` | breeze (pink, band-pass 500 Hz Q 0.5, gusts ±4 dB at 0.1–0.3 Hz) · spring birds (FM chirps 2–4 kHz in phrases of 3–6 every 3–9 s, about −36 dB, wide pan, lowpass 6 kHz) · a far brook | spring ranch, title, Hill Sprints, Target Toss |
| `summer-field` | a softer warm breeze, sparse birds, far bees (an amplitude-modulated band-pass noise around 250 Hz, very quiet) | summer ranch |
| `autumn-wind` | gusty wind, leaf rustles (high-passed noise bursts that rise with the gusts) | autumn ranch |
| `winter-yard` | soft wind (lowpass 600 Hz), a far hearth crackle from the barn | winter ranch |
| `brook` | pink, band-pass 900 Hz Q 0.6 plus high-pass 200 Hz, a random swell at 0.8–2 Hz ±3 dB, bubble chirps (sine 500→1,400 Hz, 25 ms, 6–12 a second, about −40 dB) | the ranch's brook, Archer's Glade |
| `waterfall-near` | roar (pink, lowpass 2.2 kHz, high-pass 80 Hz) · rumble (brown, lowpass 250 Hz) · spray (white, band-pass 4.5 kHz Q 0.7, 20 dB under the roar, lowpass 8 kHz) · swells (random walk 0.3–0.6 Hz, ±3 dB) · splashes (noise bursts high-passed at 900 Hz, 60–150 ms, 2–4 a second) · left and right decorrelated | Waterfall Stand |
| `windmill` | band-pass noise sweeping 300–900 Hz, Q 1.2, gusts on a random walk · a whistle (band-pass Q 10 at 700–1,100 Hz, about −40 dB) · the sail's whoosh every 1.6 s with a pitched Kenney creak | Wind Chase |
| `night` | three detuned crickets (a 4.3 kHz sine pulsed at 30 Hz in 3-pulse chirps, about −44 dB, lowpass 6 kHz), a faint breeze | Moon Meditation, Starfall Observatory |
| `oak` | a heavy leaf rustle on each shake (band-pass bursts 2–6 kHz), a branch creak | Acorn Shower |
| `farm` | light wind, fence creaks, far birds | Log Toss, Plow Pull |
| `barn` | room tone, rope creaks | Dodge the Gourds, Turnip Sort |
| `garden` | soft wind, a rare mark-tree shimmer | Puzzle Stones |
| `quarry` | wind in stone (band-pass 250 Hz into the cave reverb), gravel trickles (noise bursts lowpassed at 1.5 kHz, 0.3–1 a second), a far pick (`impactMining`, about −30 dB) | Quarry Haul, Iron Quarry |
| `town` | murmur (three band-passed noises at 300 / 800 / 1,600 Hz with a syllable-rate swell of 3–6 Hz, about −38 dB; no words or voices) · a rare cart rumble · occasional footsteps (`footstep_concrete`) · a far tubular bell every 2–4 min · sparse birds | Town, Mail, Upgrades, Odd Jobs |
| `market` | `town` plus coin clinks and crate knocks | Market |
| `shop` | room tone, a quiet clock, a door chime on entering | Shop |
| `guild` | a big room with a far crowd from the arena next door | Guild |
| `library` | a quiet room and a page flip (`bookFlip`) every 10–25 s | Library, Journal |
| `shrine` | low room tone, a stone hum (sines at 110 / 165 / 220 Hz with 0.2 Hz beating, about −42 dB), rare hand chimes | Shrine, Echo Stones |
| `lab` | clock ticks, a bubbling flask, a soft 100 Hz machine hum (about −46 dB) | Pell's Lab |
| `studio` | a very quiet room | Monster Lab |
| `arena-out` · `arena` | a far crowd (lowpassed 1 kHz), wind, flags · the crowd sized by the event (§9.4) | cup entry · cup screens and battles |
| journey sites | Iron Quarry: `quarry` with hammer rings · Windrun Steppe: strong wind and grass rustle · Starfall Observatory: `night` with a rare glass shimmer · Archer's Glade: `meadow`, leaves and `brook` · Glacier Bastion: cold wind with a high whistle, ice creaks and soft crystalline ticks | Journey |
| expedition sites | Thornwood Ruins: wind through stones, creaks, far birds · Sunken Library: underwater (pink lowpassed at 450 Hz, bubbles, slow water movement, the `underwater` reverb) · Hollowmoon Caverns: drips (sine plinks 1,200→700 Hz, 15 ms) in the `cave` reverb, low wind · Skyreef Isles: sea swells (brown and pink over an 8–12 s cycle, lowpass sweeping 300→1,200 Hz), the ocean drum, gentle wind | Expedition |
| `dusk` | soft crickets, breeze, a far bell | Farewell |

### 9.3 Weather overlays (the ranch, the town and outdoor places)

| Weather | Overlay |
|---|---|
| Sunny | birds × 1.3 |
| Cloudy | wind +3 dB, birds × 0.6 |
| Rain | light rain (pink, high-pass 400 Hz, lowpass 8 kHz, about −34 dB), drips on wood (3–8 a second), no birds |
| Storm | heavy rain (about −30 dB), gusty wind, distant thunder every 25–60 s (a brown burst with a lowpass falling 200→60 Hz, 3–6 s decay; never close), no birds |
| Snow | soft wind; all ambience lowpassed at 3 kHz and 3 dB down ("muffled"); no birds |

### 9.4 Crowds

- **Sizes:** `none` · `small` (regular cups) · `medium` (Opens, the Rival Showdown) · `large` (Ascensions) · `large+` (Crowns) · `huge` (the Legend) · `hushed` (the Masquerade) · `chanting` (the Summit).
- **Reactions:**

  | Moment | Reaction |
  |---|---|
  | A heavy hit or a crit | a short cheer swell, 0.6 s |
  | A miss | an "ooh": the murmur swells, darker |
  | A Special | a rising murmur |
  | KO | a big cheer and applause, 2 s |
  | The last 10 s | clapping on the music's beat; a `chanting` crowd claps on 2 and 4 |
  | A win | applause |

- The Masquerade gets polite applause only.
- Every crowd sound is lowpassed at 4 kHz or below. No whistles and no voices.

## 10. Sound effects

### 10.1 Principles

- **Sources:** natural ones only: samples, Foley, filtered noise, sine and triangle. No square, saw or "tan" waveforms and no bit-crush.
- **Shape:** soft transients (attack ≥ 2 ms except deliberate impacts), and every sound fades out.
- **Levels:** §14.3.
- **Variety:**
  - Noise and Foley vary ±3% in pitch and ±1.5 dB in level, with alternate takes.
  - **Pitched effects** stay within ±10 cents and in key.
  - Never the identical sound twice in a row.
- **Throttles** (the minimum gap per id): UI 60 ms, hit 50 ms, miss 80 ms, crowd 350 ms. At most 16 effect voices; the quietest or oldest is stolen.
- **Pan:** from the FxEvent's `from` / `to` through the arena camera, −0.6 to +0.6.
- **Speed:** at ×2, drop travel layers and crowd reactions except KO. At ×4, play only impacts of medium strength or more, and KOs.

### 10.2 UI

| id | Sound | When |
|---|---|---|
| `tap` | a soft wooden tick (marimba at pp, lowpass 2.5 kHz) | buttons |
| `select` | a kalimba tick | chips, segmented controls |
| `back` | a lower wooden tick | back and close |
| `toggleOn` / `toggleOff` | two soft notes, up or down | switches |
| `deny` | a muted "thup" | a disabled control |
| `sheetOpen` / `sheetClose` | a soft cloth swish | sheets |
| `tab` | a paper flick | tabs |

`tapSounds.ts` keeps its one delegated listener and maps classes to ids. The **Button sounds** setting turns them all off.

### 10.3 Battle

**By element and moment:**

| Element | Cast | Travel | Impact |
|---|---|---|---|
| Physical | cloth swish and a foot scuff | an air whoosh (band-pass noise sweep 300→1,200 Hz) | a body thud (sine 90→55 Hz over 120 ms, plus `impactPunch` / `impactSoft`) |
| Fire | a soft ignition whoosh with crackles | a breathy roar (noise lowpassed 400–1,500 Hz, with flutter) | a muffled burst (brown, lowpass 900 Hz) and a crackle tail |
| Water | a bubbly burble | rushing water (pink, band-pass 800 Hz) | a splash (noise high-passed at 800 Hz, plus droplet chirps) |
| Ice | a quiet crystalline shimmer (high hand chimes) | a frosty air hiss (lowpass 4 kHz, quiet) | a soft shatter (a cluster of glock-like sines, fast decay, lowpass 6 kHz) and a crunch |
| Lightning | a quiet static fizz (lowpass 3 kHz) | none | a warm thunder-crack (a short noise burst, band-pass 1.2 kHz) with a low rumble tail; no zaps or buzzing |
| Wind | a gust swell | whooshes sweeping left→right | a gust thump (lowpass 300 Hz) and leaves |
| Earth | a low rumble (brown, lowpass 150 Hz) | a rock tumble (woodblock pitched down) | a stone thud and a gravel trickle |
| Nature | a leaf rustle and a vine creak | a swish | a soft thwack and a petal sparkle (high kalimba, quiet) |
| Light | a quiet harp glissando up | a shimmer swell | a hand-chime bell and a bright puff |
| Dark | a reversed swell | a low whoosh | a muffled thump with a low drone tail |
| Sound | 3 notes on ocarina or wine glass **in the playing song's key** | rings travel (vibes) | a chord bloom (harp and glass) |

**Strength,** by damage as a share of max HP:
- light (< 8%): shorter, higher, −3 dB;
- medium (8–18%);
- heavy (> 18%): 2 semitones lower, a longer tail, +2 dB, and a crowd cheer.

**FxEvent kinds** (the V1 bus: `fire travel hit miss crit ko special push dash distract wither heal`):

| Kind | Sound |
|---|---|
| `fire` | the element's cast |
| `travel` | the element's travel |
| `hit` | the element's impact, by strength |
| `crit` | the impact plus a snap (a whip-like noise transient, lowpass 5 kHz) and a heavier thud |
| `miss` | a quick soft swish |
| `ko` | a deep thump; the music cuts and the crowd reacts (§7.5) |
| `special` | the element's swell and a whoosh; the music dips 3 dB for 1 s |
| `push` | a body bump and a scrape |
| `dash` | a scurry of footsteps |
| `distract` | a two-note kalimba "huh?" |
| `wither` | a soft deflating sigh: filtered noise falling 1,200→300 Hz under a low, slightly detuned pad note |
| `heal` | rising harp and glass |

**Engine events that aren't FxEvents** (the battle store's event switch):

| Event | Sound |
|---|---|
| `stun` | wobbly, detuned harp notes |
| `reflect` | a bright, lowpassed ping |
| `recoil` | a thud |
| `jackpot` | double: a music-box arpeggio · heal: harp · fizzle: a drooping kalimba |
| `trait` (Dragonheart) | a low horn swell |
| the timer | a soft woodblock tick each second for the last 5 s |

### 10.4 The world

- **Drills:** the Foley in §8.
- **The Shrine:** the stone hum (a bowed-vibes and organ swell with chimes); `birth` is §7.6.
- **Echo Stones:**
  - Each of the four stones plays an ocarina plus hand-chime note in the Wildsong key, with four clearly different pitches.
  - A cleared sequence plays back as a harp phrase ending on the motif.
  - A wrong stone plays a soft low "thup".
  - The game's rules don't change.
- **Turnip Sort:**
  - A right answer plays a soft wooden "plop" into the basket, and a kalimba note that rises with the streak.
  - A wrong answer plays a muted thud.
  - The round ends with a small jingle.
  - The music's tempo follows the game's speed ramp.
- **Expeditions:** a chest creak, and soft pass and fail sounds for obstacles.

### 10.5 Compatibility

| Old `SfxId` | Becomes |
|---|---|
| `tap` · `select` | §10.2 |
| `fire` · `hit` · `crit` · `miss` · `ko` · `special` | §10.3. The battle store passes the FxEvent; with no element, it uses Physical. |
| `win` · `lose` | `matchWin` · `matchLoss` |
| `drillGreat` … `drillSlacked` | the drill cue's outcome stinger. `DrillResult` calls `drillCue`; the old ids play the generic cue's stingers. |
| `levelUp` | `learnTechnique` (Songbook) and `prime` (WeekSummary), by call site |
| `coin` · `mail` · `growUp` · `plannerStop` | the same ids (§7.6) |
| `stoneHum` | the Shrine's stone hum |
| `echo1`–`echo4` | the four stone notes |

- `setMusic` and `playStinger` stay as thin wrappers over the director.
- The tests that import the old `music.ts` are replaced by the new music tests.

## 11. The director (what plays when)

1. **The scene** is the screen plus its context:
   - the season and weather;
   - the cup event and opponent;
   - the battle phase, with HP % and time left;
   - the drill, odd job, site and any overlays.

   A pure function turns the scene into a request: song, layers, stem, bed and crowd.
2. **Every `Screen` and every event in `EVENTS` has an explicit mapping**, with no silent fall-through. A test walks all of them. Until S2 and S3, the missing pieces map to stand-ins marked `TODO_S2` / `TODO_S3` (§15).
3. **Same song, new layers or stem:** the change starts at the next bar and fades over one bar.
4. **New song:** a 1.5 s crossfade (2.5 s between ranch seasons). Songs in the same key and tempo can switch on the next beat. A match start restarts the battle song (§7.5).
5. **Stingers win.** After an interrupting stinger, the area music restarts at the start of the section after the one it interrupted (§4.7).
6. **Fast navigation:** a 250 ms debounce, and never more than two songs sounding at once.
7. Overlays don't change the music (§7.1).
8. **Off switches:** music off schedules nothing. Ambience and effects have their own switches.
9. A drill cue takes over from the area music (§8.1).
10. **The battle's theme** comes from its origin: the cup event and opponent, a Trial site, or the Lab. Matches against Corin use `rival` with the event's lead and kit.

## 12. Settings (per-field fallbacks, like V1's Graphics settings; no save-schema bump)

- **Kept:** `sound` (effects), `music`, `masterVolume`, `musicVolume`, `sfxVolume`.
- **New:**
  - `ambience` (on)
  - `ambienceVolume` (60)
  - `buttonSounds` (on)
  - `listening` (`'speaker'` | `'headphones'`, default `'speaker'`)
  - `monoAudio` (off)
- **New defaults:** master 80, music **70** (was 55), effects **75** (was 100), ambience 60.
  - A one-time bump for existing players: a `musicVolume` of exactly 55 becomes 70, and an `sfxVolume` of exactly 100 becomes 75. Any other value was the player's choice and stays.
  - Record `audioDefaultsV2: true` so the bump runs once.
  - Test the bump.
- **Settings → Sound:**
  - the switches and sliders;
  - "Listening on" (Phone speaker / Headphones);
  - "Mono audio";
  - "Test sound" (a short harp-and-ocarina phrase);
  - "Open Sound Lab".

## 13. The Sound Lab (Monster Lab → Sound, `#lab/sound`; also from Settings)

| Tab | What's on it |
|---|---|
| **Music** | Every song, grouped: Places, Ranch, Town stems, Events, Battles, Drills, Stingers, Musical effects. Play / Stop; chips for the song's layers and stems; weather chips for ranch songs; Next section; an info line (key, tempo, meter, length, section now playing); checker warnings |
| **Ambience** | Every bed and weather overlay, with sliders per layer (for this session only) |
| **Effects** | A grid of UI and world effects; a battle pad (element × moment × strength, crit, pan); crowd reactions by size |
| **Moments** | A drill-cue demo (drill, outcome, speed); your current monster's song plus "Random phrase"; birth, birthday and farewell demos. None of it touches the save. |
| **Mix** | Live meters (peak and short-term loudness per bus and master), voices in use, packs loaded with their decode times, late events, the Listening and Mono toggles, "Play the battle demo" (a scripted 60 s battle mix) |

- **Owner notes:** every item has 👍 / 👎 and a short note, kept in this browser only (wrapped in try/catch).
- **"Copy my sound notes"** puts a list like `ranch-spring 👎 "flute too high"` on the clipboard to paste to Claude Code.
- The layout is phone-first: it fits 412 px wide with 44 px tap targets.

## 14. Quality gates and tests

### 14.1 Bans

- `nodes.ts` is the only file that creates oscillators, PeriodicWaves, compressors and WaveShapers. It asserts at runtime:
  - no `square` or `sawtooth` type;
  - no PeriodicWave with more than 8 harmonics;
  - no WaveShaper curve (none is needed);
  - every compressor has an explicit knee and makeup cancellation.
- A Vitest lint fails on any direct creation call outside `nodes.ts`, and on any `zzfx` import.
- Every file in `public/audio` comes from the manifest, and every source is listed in `CREDITS.md`.

### 14.2 Unit tests

Vitest runs in Node, so it tests the pure modules. Anything that needs Web Audio is checked by `audio:check` and the e2e tests.

| Area | What the tests cover |
|---|---|
| ABC parser | every supported feature, explicit key accidentals, and the error cases |
| Generators | chord symbols and voicing, every pattern, percussion, kits, pitched percussion |
| Scheduler | on the fake-clock driver: 300 ms stalls give zero late events, changes land on bar lines, two transports crossfade |
| Director | every Screen, every event id, the Corin rule, weather, overlays, the stand-ins |
| Song model | the sounding rule (stem, layers, weather) and breath lengths |
| Songs | the checker (§6.7) over every song |
| Event table | complete and valid (§7.4) |
| Monster songs | §7.7 |
| Manifest | packs (§5.2), ranges and sample coverage, files present, budgets |
| Settings | the fallbacks and the old-default bump |
| Effects | the throttles and voice stealing |

### 14.3 Offline render checks (`npm run audio:check`)

**How it renders**
- Playwright drives the installed Chrome. The real engine runs on the offline driver (§4.4) in an `OfflineAudioContext` at 48 kHz, with the real samples, the Phone speaker preset and default volumes.
- Every rendered item has a **fixed seed**, so renders repeat exactly.
- An 8-channel render taps four stereo **stems** after their buses, before the master: music, ambience, effects and UI. A separate render records the master.
- **Measured layers:**

  | Kind | Measured as |
  |---|---|
  | Ranch, place and town songs | Sunny, the full stem |
  | Battle themes | base + drive for 60 s, then lobby and tension separately |
  | Beds | Sunny, no weather overlay |

**Targets**

| What | Target |
|---|---|
| Each ranch, place or town song (first 45 s) | −20 LUFS integrated · true peak ≤ −1 dBTP · crest factor ≥ 10 dB |
| Each battle theme, base + drive with the scripted battle effects (60 s; the music stem) | −18 LUFS · master true peak ≤ −1 dBTP |
| Battle lobby layer · tension layer | −22 LUFS · −18 LUFS |
| Each bed (20 s) | −32 LUFS (`waterfall-near` −24) |
| Each drill cue, all five outcomes (master, with its bed) | −22 LUFS; Slacked 1 LU lower (the sag is the point); the Waterfall Stand −24 (its roar is −24 by design and the music stays under it) |
| Each interrupting stinger | −20 LUFS integrated over its length |
| Each musical effect | short-term max ≤ music + 3 LU |
| Ordinary hits | short-term ≤ music + 4 LU |
| Crits and Specials | ≤ music + 6 LU |
| KO | ≤ music + 9 LU |
| Each UI effect | momentary (400 ms) ≤ −32 LUFS |
| Each battle effect alone | true peak ≤ −3 dBTP |
| No pumping | an ordinary hit moves the music stem by no more than 0.5 dB |
| Clicks | no sample-to-sample jump above 0.2, except within ±5 ms of an onset in the scheduler's event log |
| Loop seams | 400 ms loudness across a loop boundary within 1 dB of the same bars rendered straight through |
| Dropouts | no stretch below −60 dBFS for more than 300 ms, except where the score has a breath or rest |
| Decoded samples | onset within ±1 ms, length within one 20 ms frame, loop points as in the manifest |

- **"Music" in the relative targets** means the music stem's short-term loudness in the 3 s before the event, before any duck.
- **Calibration:** `npm run audio:check -- --calibrate` writes per-song, per-bed and per-effect trims to `src/audio/levels.json` (committed).
  - It fails if any trim would exceed ±6 dB; that means the mix itself is wrong.
  - After calibration, every loudness target is checked at ±1 LU.
- **Reported, not gated:**
  - Brightness. Warn above these shares of energy:

    | Music | 2–6 kHz | above 8 kHz |
    |---|---|---|
    | Place music | 10% | 1.5% |
    | Battle themes | 14% | 2.5% |

    Fix brightness with EQ or orchestration, not by deleting instruments. The old loops measure 0–10% in 2–6 kHz; their harshness came from aliasing and hard waveforms, which §14.1 bans outright. `tools/audio/baseline-legacy.json` keeps their numbers for the report.
  - The glue's gain reduction.

### 14.4 The review report (`npm run audio:review`; output in `audio-review/`, gitignored)

- One `.ogg` (Opus 96 kbps) per song, bed, drill cue and effect group.
- An `index.html` with players, the §14.3 numbers next to the legacy baseline, and the checker notes.
- The owner can open it on the PC. PROGRESS.md says what to listen for.

### 14.5 End-to-end (Playwright, 412 × 915)

- The first tap unlocks audio.
- The ranch plays the season's song (read from `window.__audio`).
- Town switches song within 2 s.
- A cup battle uses its event's theme.
- Pause sets `musicFilterHz` to 700.
- The Sound Lab plays a song and an effect without console errors.

### 14.6 Build checks (`npm run check:build`, added to `verify` after `build`)

- The service-worker precache list contains the manifest and every core-pack file.
- The engine chunk is ≤ 45 KB gzipped.
- All song chunks together are ≤ 120 KB gzipped.

## 15. Stages

Every id in §7.6, every piece and every bed belongs to exactly one stage. Anything not yet written uses a stand-in, marked `TODO_S2` / `TODO_S3` in the director's table and listed in PROGRESS.md:
- events use `cup` in their season palette;
- moments use `cupWin`, `promotion` or `matchLoss`;
- places use the Town stems or the ranch song;
- beds use the nearest written bed, or none.

### S1: Calm engine and first songs (v1.6.0, commit `Sound S1: calm engine and first songs`)

1. **Baseline:** render the 9 old loops and the ZzFX effects with the analyser into `tools/audio/baseline-legacy.json`, before anything is removed.
2. **Samples:** the pipeline (§5.3), with packs computed from what S1 uses. The Kenney Foley. Manifest, CREDITS, budget check.
3. **Engine** (§4), with drivers, `nodes.ts` and the master chain.
   - Remove ZzFX from the package, its imports, the CREDITS line and the CLAUDE.md library list.
4. **The music system** (§6), with the checker, kits and motifs.
5. **The director**, with the full mapping table and the stand-ins.
6. **Pieces:**
   - Wildsong: the title, the `newGame` lobby arrangement and the `creditsRoll` arrangement.
   - The four ranch songs, with weather rules and breaths.
   - Town with every stem.
   - `cup` with lobby, base, drive and tension, the four season palettes and kits.
7. **Stingers and musical effects:**
   - The interrupting stingers `matchWin`, `matchLoss`, `matchDraw`, `cupWin` and `promotion`.
   - The S1 musical effects (§7.6).
8. **Beds:** `meadow`, `summer-field`, `autumn-wind`, `winter-yard`, `brook`, `waterfall-near`, `town`, `market`, `shop`, `guild`, `library`, `arena-out` and `arena`, with crowds `small` and `large`, and all weather overlays.
9. **Effects:**
   - The whole UI set.
   - The whole battle set: every FxEvent kind and the engine-only events.
   - The Shrine's stone hum, and the Echo Stones notes and flourish.
10. **Drill cues:** the system, with **Waterfall Stand in full** as the pilot. The other 10 drills get a soft generic cue with generic outcome stingers.
11. **The rest:** settings (§12), the Sound Lab (§13), `audio:check`, `audio:review`, `check:build`, the tests and the e2e checks.
12. **Docs:**
    - GAME_DESIGN §23, rewritten: what plays where, the settings, the Sound Lab.
    - GAME_DESIGN §24: mono audio and button sounds.
    - CLAUDE.md: the library list without zzfx; an Audio section on the pipeline, `tools/audio`, ffmpeg and the audio checks; `.gitignore` entries for `tools/audio/.cache/` and `audio-review/`.
    - CREDITS: VCSL, VSCO 2 CE and Kenney, CC0, with commits, links and hashes.
    - PROGRESS and BUILD_PLAN.
13. **Finish:** `npm run verify`, `npm run e2e` and `npm run audio:check` all green. Commit, push, confirm the deploy, give the phone checklist, then **stop for the owner's listening notes**.

**Phone check S1:**
1. Open the app with the volume up: the title theme.
2. Stay on the ranch for 5 minutes. Is it calm? Do you hear the quiet breaths between passes?
3. In the Sound Lab, try the ranch weather chips and all four seasons.
4. Tap around. Are the button sounds soft? Try them off too.
5. Town: walk Shop → Market → Guild. The music should change smoothly without starting over.
6. Fight a cup match. Listen for the build-up when HP gets low and in the last 10 s.
7. Train Waterfall Stand.
8. Switch between Phone speaker and Headphones, with earbuds in.
9. Does any tune sound like something you know?
10. Play everything in the Sound Lab, give each a 👍 or 👎 with notes, tap "Copy my sound notes" and paste them to Claude.

### S2: A theme for every event (v1.7.0, commit `Sound S2: a theme for every event`)

- **Pieces:** `open`, `ascension`, `crown-dawn`, `crown-tides`, `crown-embers`, `crown-frost`, `legend`, `masquerade`, `rival` (with the Corin rule), `summit` (with the Qualifier arrangement), `rally`, `rally-rogue`, `sprout`, `elders`, `trial` (with the five site tonics and leads) and `practice`.
- **The per-event arrangement table** for all 60 events.
- **Stingers and effects:** `cupPlaced`, `cupOut`, `crownWon`, `legendWon` (with the Hall of Fame anthem), `rankUp`, `titleEarned`, and the rival calling cards.
- **Crowds:** every size, the Summit's on-beat claps, the Masquerade's hushed crowd.
- **Packs:** recompute them; `events` gets what's new.
- **Finish:** tests, `audio:check` and `audio:review`, docs, the commit, and the phone check: an Ascension, the Masquerade, the Rival Showdown, every Crown in the Sound Lab, two regular cups from the same season (they should sound different), and "does any tune sound familiar?". Then stop.

### S3: Places, trainings and moments (v1.8.0, commit `Sound S3: places, trainings and moments`)

- **Pieces:**
  - The Shrine, Pell's Lab and the Monster Lab.
  - Journey, with five site arrangements.
  - The four Expedition pieces (Thornwood Ruins, Sunken Library, Hollowmoon Caverns, Skyreef Isles).
  - Turnip Sort, whose tempo follows the ramp.
  - The Echo Stones drone.
  - The farewell loop.
- **Stingers and effects:**
  - `birth`, `farewell`, `birthday`, `monsterSong`, `rest`, `play`, `journeyDepart`, `journeyReturn`.
  - `fusion`, `expeditionTreasure`, `expeditionEvent`.
  - The Turnip Sort effects and the expedition obstacle sounds.
- **Trainings:** the other 10 drills in full (§8), each with five outcomes.
- **Beds:** `windmill`, `night`, `oak`, `farm`, `barn`, `garden`, `quarry`, `shrine`, `lab`, `studio`, the five journey-site beds, the four expedition-site beds, and `dusk`.
- **Monster songs**, everywhere §7.7 lists. Recompute the packs.
- **Finish:** tests, `audio:check` and `audio:review`, docs, the commit, and the phone check: train every drill once; visit the Shrine, Pell, the Lab, a Journey and an Expedition; play Turnip Sort and Echo Stones; play your monster's song on its card; and "does any tune sound familiar?". Then stop.

## 16. Not now, and later

- **Monster voices,** small breed-pitched chirps for praise, scolding and yawns, belong with V3's poses.
- **Per-technique sounds** belong with V2's attack recipes. Their timeline markers will drive §10.3's moments.
- **V4's cinematic drills** will pass timeline markers to §8.1's cues.
