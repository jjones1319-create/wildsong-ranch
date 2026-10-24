# M10: Smarter battles (AI 2.0), the arena camera, and balance follow-ups

Owner-requested after v1.0. This file is the spec. **Built in M10 (2026-10-24):** the rules now live in GAME_DESIGN §12.10 (the AI) and §12.11 (Auto styles, camera, thinking icons); this file stays as the record. Where M10 landed differently from the spec: the "beats v1 ≥ 60 %" test became "not worse than v1" (head to head the brains are about even; see PROGRESS), veteran toughness was not needed, and the four pure casters got a Close basic so an Unshakable brawler is not a hard counter.

## What the owner sees today

- **Pressed together:** the two monsters walk into each other and stay pressed together, almost never pushing.
- **One range only:** they mostly use their Near/Close techniques. They don't move around, back off, or use the rest of their moves.
- **Auto has no strategy:** "play for me" just walks forward and attacks.
- **Off-screen:** near a wall, a monster is drawn partly off the screen.

## Why (from the current code)

1. **Band choice ignores the opponent.** `decideAi` picks its target band from its *own* best expected value only (`bandScores`). It stays in its current band 75% of the time, and it never weighs what the opponent can do at each range. Both monsters usually want the same close band, so they lean on each other.
2. **Push rarely fires.** It only triggers when touching **and** wanting band ≥ 3 (`AI.pushFromBand`). Two close-range fighters never push.
3. **Narrow technique choice.** Choice is weighted by EV^1.5, so one or two techniques at the current band crowd out everything else.
4. **No stall detection.** Nothing notices a stall (touching, neither attacking).
5. **Sprite scale mismatch.** The physics bodies are 50 units wide, but sprites are drawn at 118 px on an arena that maps 1,200 units to the screen width. A monster at the wall (x = ±550) is drawn half off-screen, and touching monsters overlap by most of a sprite.

## Goals

- **Purposeful movement:** monsters approach, back off, dash in, push away, stay out of the opponent's best range and reset the spacing.
- **The whole kit:** they use techniques from every range they have, not just one.
- **Push is a normal tool:** used when stuck together, when cornered, and to make room for longer-range techniques.
- **Real strategy:**
  - They play to their own strengths and avoid the opponent's.
  - They save guts for big moves and punish an opponent that's out of guts.
  - They play safe when ahead late and go all in when behind.
- **The right opponent:** rookies are simple; champions and **your Auto mode** are smart; rivals' readable habits still show.
- **Both monsters are always fully on screen.**

---

## 1. Arena camera (fixes the off-screen bug)

- Add a pure `ui/battle/camera.ts`. Given both x positions, the viewport size and the sprite sizes, it returns a zoom and an offset. The arena world layer (monsters, effects, floating numbers, walls) is drawn through that transform. The HUD and the range ruler are not.
- **Framing:**
  - Centre on the two monsters' midpoint.
  - Zoom so the span from the left monster's back edge to the right monster's back edge, plus a margin, fills the arena width.
  - Clamp the zoom between "the whole arena fits" and a maximum where one sprite is at most ~45% of the arena width.
  - Clamp the view so it never shows past the walls.
- **Smoothing:** a critically damped spring, with no jitter. With reduced motion, use gentle easing without overshoot.
- **Matching visuals to physics:**
  - Sprites scale with the zoom.
  - A sprite's visual half-width matches the physics body radius (plus a small allowance for fluffy parts), so touching looks like touching.
  - Tune `BATTLE.arena.bodyRadius` and the sprite world size together if needed. Keep the band distances (§12.1) unchanged.
- **Walls:** draw them at the arena edges (a fence, rocks or banners per arena) so "cornered" reads clearly.
- **Tests (pure, no DOM):**
  - For 10,000 random position pairs inside the walls and viewport widths of 320–1,024 px, both sprites stay entirely inside the arena rectangle.
  - The zoom stays within its bounds.
  - Small position changes produce small camera changes (continuity).
  - Push slides and dashes stay inside the walls; there's already an engine clamp, so add a fuzz assertion.

## 2. AI 2.0

Everything stays deterministic: the injected RNG only, integer or rounded math, and no `Math.random` or `Date.now`. It keeps GAME_DESIGN §12's rules for what a monster *can* do. Only the decisions change. Put every number in `tuning.ts` under `AI`.

### 2.1 Skill tiers

| Tier | Who | Reaction delay | Mistakes | Uses |
|---|---|---|---|---|
| Rookie | NPCs at grades E–D | 18–30 ticks | 20% (a random OK option instead of the best) | §2.3 without threat (own best band), anti-stall rules, simple guts use |
| Skilled | NPCs at grades C–B | 10–20 ticks | 8% | Everything except §2.6's special and trait reads |
| Expert | NPCs at A–S, Crowns, Masquerade, Legend, rivals from grade C, **the player's Auto mode**, Journey Trials at B+ | 6–12 ticks | 2% | Everything |

- **Auto styles:** the player's Auto has a style picked in the battle settings: **Balanced** (default) · **Aggressive** · **Defensive**. The style sets the aggression and caution multipliers in §2.3.
- **Personalities and habits:** NPC personalities (Steady, Aggressive, Cautious, Trickster, Sniper, Brawler) become multipliers on top of the tier. Rival **habits** (CONTENT §10) still apply on top, so rivals stay readable but now play well around their habit.

### 2.2 Think loop

- **Re-plan** every 8–12 ticks (random), and immediately on any of these events:
  - got hit
  - the opponent fired
  - its own or the opponent's guts crossed a technique cost
  - became cornered or touching
  - 20 s or 10 s left
- **Between plans,** execute the current plan: target band, sweet spot, and the goal technique.

### 2.3 The range plan (the core change)

For each band b = 1…4, score it:

```
offense(b)  = my best damage-per-second at b
            = max over my techniques at b of  EV(t) × min(1, regenPerSec / cost(t))   (+ a bonus if I can afford t right now)
threat(b)   = the same from the opponent's side (its techniques, its guts, its stats vs mine)
variety(b)  = bonus for bands whose techniques I haven't used in the last ~10 s (decays), so the whole kit gets used
travel(b)   = seconds to reach b at my speed; +∞ if it needs more room behind me than I have (cornered) and I can't push
score(b)    = offense(b) × aggression − threat(b) × caution + variety(b) − travel(b) × travelWeight
```

- **Choosing:** pick the best-scoring band. Switch targets only if the new band beats the current one by ≥ 15%. This hysteresis stops dithering.
- **Sweet spot:** the target is a **sweet spot** inside the band, not the band centre. It's the part of the band farthest from the opponent's strongest band, while still in mine; for example, the far edge of Near against a Close brawler.
- **Base multipliers** come from the tier, personality and Auto style; §2.6 adjusts them.

### 2.4 Movement and spacing rules

- **Footsies:** around the sweet spot, wobble ±15–30 units every 1–3 s, so idle spacing looks alive rather than frozen.
- **Anti-stall:** two monsters must not stand pressed together.
  - If touching (gap ≤ 40) for over 1 s with neither attacking, the AI must do one of these:
    - push, if push is off cooldown and its target band is ≥ 2, or it's the weaker Close fighter, or it's cornered;
    - step back;
    - fire a Close technique.
  - Hard rule: touching for over 2 s → push if available, otherwise back off.
- **Push more.** Push when touching and any of these is true:
  - the target band is ≥ 2;
  - the opponent's `threat(1)` exceeds my `offense(1)`;
  - my back is within 120 units of the wall.

  Push stays free with its 3 s cooldown. Expect several pushes per match when a brawler meets anything else.
- **Corner awareness:**
  - Backing away only works with room behind you.
  - Cornered and wanting distance → push when touching, otherwise fight at the best band you can hold.
  - Never walk backwards into a wall for more than 0.5 s.
- **Dash in** (it costs guts) when the target band is ≥ 1 band closer and one of these holds:
  - the opponent is in a punish window (§2.5);
  - I'm behind with ≤ 15 s left;
  - my goal technique is ≥ 2 bands closer.

  Battering Ram dashes more often.
- **Kiting:** a monster that wants distance from a faster chaser doesn't back off forever. It holds the best band it can keep, and uses push and its longer techniques when the chaser arrives.
- **Direction changes:** expect several per match. A monster should never just walk forward.

### 2.5 Attack choice and guts plan

**Goal technique:** the best-value affordable-soon technique at the target band. Its value is EV adjusted by:
- **Hit chance:** prefer Hit-family or Sharp techniques when my hit % for a Heavy is under 40%, unless guts ≥ 80.
- **Punish window:** the opponent's guts are below its cheapest technique cost, or it's mid-animation or distracted → +30%. Move in and fire.
- **Starve plan:** the opponent has a slow guts rate (≥ 13) or an expensive best technique → Wither +40%.
- **Heal:** when HP ≤ 40% and the opponent's current threat is low, a heal's value is the HP it restores.
- **Variety:** +15% for techniques not used in the last 10 s.

**Save or spend:**
- If I can afford the goal technique, fire it after the reaction delay.
- If I can't, save, unless a cheap option's value per guts is at least 2/3 of the goal's, or I'm being punished right now.
- **Never sit at 90+ guts:** spend.

**Pacing:** the old per-tick random "use rate" roll goes away. Keep the 1.0–2.5 s cooldown between techniques for balance, and keep attacks per match inside §26 (4–12).

### 2.6 Situation modifiers (Skilled: clock and HP only; Expert: all)

| Situation | Effect |
|---|---|
| Ahead on HP%, ≤ 20 s left | caution ×2: keep away, push, avoid trades |
| Behind, ≤ 15 s left | aggression ×1.5, caution ×0.5: dash in, fire the biggest techniques |
| HP ≤ 30% (and not behind late) | caution ×1.5 |
| Opponent has guts ≥ its best Heavy's cost | caution ×1.3 at bands that Heavy reaches |
| Opponent in a punish window | caution ×0.3 |
| Opponent has a damage-up special active | caution ×1.5 until it ends |
| I have Valor or Clutch active | aggression ×1.3 |

**Traits:**
- Statue Pose: stands still when the opponent approaches.
- Unshakable: ignores the opponent's push threat.
- Chill: kites after landing a hit.
- Blessed and Green Thumb: value heals more.

### 2.7 "Show battle thinking" (SHOULD)

- A small icon over each monster shows its current plan:

| Plan | Icon |
|---|---|
| Keeping distance | 🛡 |
| Saving guts | ⏳ |
| Pressing | ⚡ |
| Pushing away | ↔ |
| Punish! | ❗ |
| Playing safe | 🏳 |
| Cornered | 🧱 |

- **Toggle:** Settings → "Show battle thinking". It defaults to on in Breeder's Lens mode and off otherwise.
- It makes the strategy visible and is great for testing on the phone.

## 3. Balance follow-ups (the owner has approved these)

1. **Lootlid:**
   - Give Gilded a battle side: it keeps +15% prizes and ×2 chore pay, and it **gains 6 guts each time it lands a hit** (tunable).
   - Tune it until Lootlid's mean win share is 40–60% at totals 1,000, 2,000 and 3,000, while keeping its joke-breed flavor (Jackpot!).
2. **Late-game knockouts:**
   - **After** AI 2.0, re-measure. If the even-fight KO average at total 3,000 is still above 15%, add "veteran toughness": `maxHp = LIF + max(0, LIF − 500) × 0.25`, so 999 LIF gives 1,124 HP.
   - The owner approves this formula change. Update GAME_DESIGN §12.5, the reference tables and the tests.
3. **Caster vs. wall extremes:**
   - After AI 2.0, every pair must sit within 25–75%, and ≥ 95% of pairs within 30–70%, at each power level.
   - Tune technique values and traits to get there. No formula changes beyond #2.

## 4. Tuning and docs

- Re-run `npm run sim:balance`, with Expert vs Expert for the matrix and sides alternating. Retune until every GAME_DESIGN §26 battle target passes again:
  - mirror 45–55%
  - +10% total → 62–80%
  - +30% total → 85–96%
  - the pair bands in §3
  - attacks 4–12 per match
  - the KO bands
- Update GAME_DESIGN §12.10 (the AI) and §12.11 (Auto styles, camera, thinking icons), and the §26 battle targets if they change, plus BUILD_PLAN (add M10) and `docs/BALANCE_REPORT.md`.
- **Performance:** AI decisions ≤ 0.1 ms per monster per tick on a desktop. Record how long the balance script now takes.

## 5. Tests and acceptance (seeded; all fast tests run in `npm test`)

1. **No stall:**
   - Over 200 battles across 10 varied pairs, monsters are never touching for more than 2.5 s straight without a push, an attack or a step back.
   - Time spent touching averages under 25%.
2. **Push use:** in battles where the monsters touch and either one's best band is ≥ 2, at least one push happens in ≥ 80% of battles.
3. **Range variety:** a monster with techniques in ≥ 3 bands uses techniques from ≥ 2 bands in ≥ 70% of battles, and from 3 bands in ≥ 40%.
4. **Movement:** each monster changes walking direction ≥ 4 times per match on average.
5. **Smarts:**
   - Expert beats Rookie ≥ 70% at equal stats (10 pairs).
   - Expert beats the old v1 AI ≥ 60% (keep v1 behind a flag for this test only).
   - Expert mirrors land at 45–55%.
6. **Punish:** when the opponent can't afford any technique and the AI has an affordable in-range one, it fires within 0.6 s ≥ 75% of the time.
7. **Clock:** an Expert with an HP lead in the last 20 s spends more time outside the opponent's best band than it did earlier in that battle.
8. **Determinism:** the same seed and inputs give the same log. Update the pinned logs and replays deliberately.
9. **Camera:** the tests in §1.
10. **Balance:** §4 targets (via the balance script plus the fast sampled guard in `balance.test.ts`).

## 6. Try this on your phone

1. Watch 3 battles on Auto. Monsters should move around, back off, dash in, push when stuck together, and use techniques from different ranges.
2. Turn on Settings → "Show battle thinking" and watch the plan icons change.
3. Back a monster into a wall in Versus. Both monsters stay fully on screen and the camera zooms to fit.
4. In Versus, pit a brawler (Cobblemaw) against a caster (Wishlume). The caster keeps its distance and pushes when caught, and the brawler dashes in.
5. Try the three Auto styles: Balanced, Aggressive and Defensive.
