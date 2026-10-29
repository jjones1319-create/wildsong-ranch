# Visual Upgrade Plan: monsters, attacks and cutaway scenes

Status: **decided** (Oct 24, 2026). The owner's decisions are in §0. Each milestone gets its own spec file and prompt (V1: `docs/VISUAL_V1_EFFECTS.md`).

## 0. Decisions (owner, Oct 24, 2026)

| Question | Decision |
|---|---|
| Style | Richer storybook vector. Keep the code-drawn, auto-recoloring monsters; add shading, rim light, textures and real animation. No painted sprite sets. |
| Attack intensity | A setting: **Cozy / Standard / Flashy** (shake, impact frames, bloom, flash strength). Default Standard. |
| Cutaway length | Up to **5 seconds**, cinematic, with camera moves; always skippable; must be genuinely good, not padded. |
| Outcome variants | **Four** per drill: Success / Great / Cheat / Fail. |
| Order | **V1 Effects engine → V3 Monster animation 2.0 → V2 Visible attacks → V4 Cinematic drills → V5 World polish.** |
| 3D pilot | **Skipped** for now. Make the 2D game as good as it can be first; revisit later if we want. |
| Painted backgrounds | **Yes.** The owner generates background layers in ChatGPT from prompts Claude writes (from V4 onward). Everything else stays code-drawn. |
| Monster concept reference | **Yes.** For V3, the owner generates 2–3 concept images per breed in ChatGPT from the prompts in `docs/CONCEPT_PROMPTS.md`, saved under `concept/<breed-id>/`. Claude Code uses them as a mood board while rebuilding each rig. They are reference only: never shipped, traced or imported, and kept out of the public repo. |

## 1. Where the game is today

- **Monsters** are "paper dolls" drawn in code (SVG): parametric parts on a body plan, flat fills plus one shading layer, CSS idle animation (breathe, bob, blink, wag), eight expressions, automatic recoloring for all 900 main/sub mixes (mixes were retired in Art P0, v1.12; every monster is one whole breed). They look consistent and charming, but they're stiff: one standing pose, no real body language, and in battle they just slide and flash.
- **Attacks** all look the same: a lunge, or a small dot that flies across, then a flash. Flame breath, ice lance and tidal wave are only words on the technique card.
- **Drill cutaways** are the monster standing beside a small prop picture (a 160×100 drawing) with the prop wiggling. The monster isn't *in* the scene: it doesn't sit under the waterfall, it stands next to a picture of one.

## 2. What the research says (short version)

Two independent research passes looked at every realistic route: better 2D, hand-painted or AI-generated sprites, skeletal animation tools (Rive, Spine), real-time 3D (three.js, Babylon), and AI 3D model generators (Meshy, Tripo, TRELLIS). Full details and sources are in §8.

**Both reached the same conclusion: don't rebuild the game in 3D; make the 2D game much richer, and run one small 3D experiment on the side.**

Why:
- The quality jump you want is mostly an **animation and effects** problem, not a renderer problem. A 3D version built without an artist usually ends up with 30 lumpy, inconsistent models that look worse than coherent 2D.
- Our current art has one enormous asset: every monster recolors automatically for 900 combinations and costs almost nothing to download. Hand-drawn or AI-generated sprite sheets lose that unless we build a palette-mask system, and they need hundreds of curated images per breed set.
- Visible attacks and cinematic scenes are achievable **now** with a GPU effects layer (particles, shaders, glow, distortion, screen shake) that Claude Code can write entirely in code and test by rendering screenshots.

## 3. Who can use which tools (honest limits)

| Tool | Who | What it's good for here | Limits |
|---|---|---|---|
| **Code-drawn art and effects** (SVG rigs, PixiJS/WebGL particles and shaders) | Claude Code | Everything in this plan's main path: monster rigs, attack effects, scene layers, water, fire, lightning | Claude can't *see* while drawing; it renders PNG frames and looks at them, then adjusts. Expect a draw → render → inspect loop |
| **Blender (headless, scripted)** | Claude Code, if Blender is installed on your PC | Baking fire/smoke/water flipbooks, rendering stylized props, and the optional 3D pilot (procedural models, Rigify rigs, sprite-sheet renders) | Claude writes and runs Blender Python scripts; it can't click around the Blender window. Blender 5.2 LTS or 4.5 LTS |
| **ChatGPT Images 2.5** | You | Backgrounds, sky/far/mid parallax layers, textures, concept art for new monsters, reference moods | Not reliable for 30 consistent monster sprite sets across poses and expressions; transparency can be flaky; risk of drifting toward famous characters. Great for scenery |
| **Rive** (free for individuals) | Claude Code via Rive's official editor connection, with the Rive app open on your PC | A professional 2D animation format with state machines, if we ever want artist-grade rigs | Needs the Rive desktop app installed and open while Claude works; bone/mesh rigging isn't fully automatable yet |
| **AI 3D generators** (Meshy $20/mo, Tripo ~$16/mo, TRELLIS 2 free/self-host) | You generate, Claude integrates | A 3D pilot: turn our own monster drawings into models | Auto-rigging is humanoid-only on Meshy; our roster is mostly quadrupeds, serpents and floaters. 20–60% of outputs need redoing; free tiers make assets public (CC BY) |
| **Spine** ($69–$379) | An animator | Industry-standard 2D skeletal animation | Only worth it if a human animator joins |

**Bottom line:** the main path (§4) needs **no new software and no subscriptions**. ChatGPT helps with backgrounds. Blender is optional and only for the 3D pilot or baked effects.

## 4. Recommended path: "2D-plus"

Five milestones, in this order. Each is one prompt and ends with a phone check.

### V1: Effects engine + arena staging (the foundation)
- Add a GPU effects layer (PixiJS 8, WebGL2 with automatic WebGPU) as a transparent canvas over the arena and the vignette scenes. The monsters stay as our SVG rigs; the layer draws particles, beams, water, fire, glows, distortion, shockwaves and screen shake on top.
- A small library of **effect primitives** written in code: cone emitter, trail, ring/shockwave, beam, projectile with arc, impact spark, debris burst, screen flash, hit-stop, camera shake, heat haze, chromatic flicker, water sheet, splash, mist, lightning bolt.
- An **element tag** on every technique (Fire, Water, Ice, Lightning, Wind, Earth, Light, Dark, Sound, Physical). Most names already imply it (Furnace Crush = Fire, Blizzard Lance = Ice, Tidebreaker Clamp = Water).
- A **Quality setting**: Ultra (S25 Ultra and up), High, Lite (fewer particles, no distortion). Auto-detect, user override.
- Phone check: a test arena where you tap buttons to fire each primitive.

### V2: Visible attacks (every technique)
- Every one of the 294 techniques gets an **attack recipe**: an anticipation pose, the effect(s), travel, impact, hit reaction, and sound. Recipes are built from the primitives by **family × element**, so a Fire Heavy at Close range becomes a charged flame crush, a Water Wither at Far becomes a drenching wave that saps guts, an Ice Hit becomes a fast icicle dart.
- Breed **Signature** techniques and Specials get bespoke, longer cinematics (1–2 s): Hearthfire Torrent is a sustained dragon-breath cone with embers and heat haze; Puddle Party is a geyser that rains back down.
- Hit reactions by body plan: squash on impact, knockback slide with dust, stagger, a brief white hit-flash, "crit" impact frame, KO flop with stars.
- Phone check: Versus with a brawler vs a caster; you can tell every technique apart by sight.

### V3: Monster animation 2.0
- **Concept reference first:** before redrawing a breed, Claude Code views that breed's concept images in `concept/<breed-id>/` (if present) to steer proportions, shading and personality. Prompts for the owner are in `docs/CONCEPT_PROMPTS.md`.
- Turn the paper dolls into proper **rigs**: a bone hierarchy per body plan with named joints (head, jaw, spine, limbs, tail, wings, ears, fins), so poses can be defined once per body plan and reused across breeds.
- A **pose library**: stand, sit, brace, crouch, lunge, cast (arms/head raised), bite, slam, hover, hit, dazed, faint, victory hop, sleep, eat, shiver, flex. Each with squash-and-stretch and secondary motion (ears, tails, wings lag behind the body).
- Better looks: soft top-left gradient on every part, rim light, contact shadow, eyes that track taps, per-breed textures (scales, fur strokes, stone grain) kept subtle so recoloring still works.
- Phone check: the Monster Card has a "poses" strip; the ranch idle shows mood through body language (tired = slumped, happy = bouncing).

### V4: Cinematic drill cutaways (your waterfall example)
Each of the 11 drills becomes a **real scene** with the monster inside it, 3–5 seconds, skippable, with Success / Great / Cheat / Fail variants.

**Waterfall Stand (DEF++ LIF+ INT−)**
- Scene: a mossy rock in a pool at the base of a waterfall; parallax layers (cliff, mist, pool, foreground ferns); the water is a shader sheet with foam and splash particles; mist drifts.
- Start: the monster climbs onto the rock and sits in its **brace** pose; the water pours over it; droplets bounce off; it shivers.
- **Success:** it endures, eyes squeezed shut, a small "grr" bubble; the water eases; it shakes itself dry. Banner.
- **Great:** it holds a proud pose under the full torrent; a glint; birds scatter. Banner with sparkles.
- **Fail:** the torrent knocks it off the rock; it tumbles into the pool with a big splash and surfaces dizzy with a lily pad on its head.
- **Cheat:** it sits beside the waterfall under a leaf umbrella, pretending; Wren notices.

Same treatment for the other ten (first-pass ideas):
- Hill Sprints: a winding hill path with parallax, panting, a finish ribbon; fail = trips and rolls down.
- Log Toss: heave, wobble, over the fence; fail = log rolls back over it.
- Puzzle Stones: a stone table; thinking bubbles; fail = stones topple.
- Target Toss: pinecones arc into the target; Great = bullseye with a "thunk".
- Dodge the Gourds: gourds swing on ropes; fail = bonk, stars.
- Acorn Shower: braced under a shaken oak; fail = buried in acorns.
- Plow Pull: furrows appear behind; fail = plow stuck, monster face-down in the mud.
- Moon Meditation: night sky, fireflies, a floating glow; fail = falls asleep and snores.
- Wind Chase: windmill gusts, leaves streaming; Great = catches the golden leaf.
- Quarry Haul: stone blocks up a ramp; fail = block slides back.

ChatGPT can supply the painted background layers for these (sky, cliffs, trees); Claude integrates them as parallax and keeps everything else in code.

### V5: World polish
- Ranch, town, shrine and arena backdrops as painted parallax layers with weather, time of day and seasons; the Shrine awakening becomes a short cinematic (the stone sings, light pours out, the monster forms).
- Tournament presentation: entrance walk-ons, a crowd silhouette layer, a winner's podium moment.
- Farewell and Signature scenes get the same cinematic treatment.

### Optional V6: the 3D pilot (time-boxed)
- Only if you still want to see what 3D looks like. Pick 3 breeds (one biped, one quadruped, one floater). Claude uses headless Blender to build or import models (procedural, or from our own monster drawings through Meshy/TRELLIS), rigs them with Rigify, animates idle/attack/hit/faint, and **renders them to sprite sheets** that drop into the 2D game, with a mask pass so recoloring still works.
- We compare them side by side with the SVG versions on your S25 Ultra and decide. Cost: Blender (free), optionally Meshy Pro ($20 for one month). Effort: roughly a week of sessions. Full 3D for all 30 breeds would be a 3–6 month project and is not recommended unless the pilot clearly wins.

## 5. Effort and order

| Milestone | Sessions (rough) | Depends on |
|---|---|---|
| V1 Effects engine | 3–5 | — |
| V2 Visible attacks | 6–10 | V1 |
| V3 Monster animation 2.0 | 6–10 | — (can run before or after V2) |
| V4 Cinematic drills | 6–10 (waterfall first as the pilot, then the rest) | V1, V3 |
| V5 World polish | 4–8 | V1 |
| V6 3D pilot (optional) | 6–10 | Blender installed |

A "session" is one Claude Code milestone run plus your phone check. All of V1–V5 are free.

## 6. Risks and how we handle them

- **Performance and heat:** the Quality setting, a cap on particles, rendering at no more than 2× pixel density, 30 fps when idle, pausing when the app is in the background. Targets: 60 fps on the S25 Ultra with two monsters and full effects.
- **Download size:** painted background layers add a few MB; we lazy-load scenes and keep the install under 10 MB. Our monsters stay tiny because they're code.
- **Originality:** effects and scenes are original by construction. For ChatGPT backgrounds, we avoid any prompt that names a franchise and we review results.
- **Claude can't see while it draws:** every visual milestone includes a render-to-PNG review step (contact sheets of every monster, pose and effect) before it ships, as M2 did.

## 7. Decisions to discuss

1. **Style target:** keep the storybook vector look but richer (recommended), or aim for a painted/textured look (more work, recoloring gets harder)?
2. **Attack intensity:** cozy-cartoon effects, or flashy anime-style with screen shake, impact frames and big bloom? (Can be a setting.)
3. **Cutaway length:** 3 seconds tight, or 5 seconds cinematic with a camera move? Always skippable either way.
4. **Variants:** four outcome versions per drill (Success / Great / Cheat / Fail) as proposed, or Success/Fail only to start?
5. **Order:** attacks first (V1→V2) or monster animation first (V3)? My suggestion: V1, then V3, then V2, then V4, because attacks look much better once monsters can pose.
6. **The 3D pilot:** do it after V2, or skip it?
7. **ChatGPT backgrounds:** are you happy to generate the painted layers yourself from prompts Claude writes, or should everything stay code-drawn?

## 8. Research notes (sources)

- **2D:** PixiJS 8.22 (WebGL2 + WebGPU auto) is the right effects layer; write our own emitter on its ParticleContainer (the old particle-emitter package isn't compatible with v8); pixi-filters for displacement, shockwave, bloom, RGB split. Rive 2.45 runtime, free for individuals, has an official editor connection Claude could drive. Spine is $69/$379 and needs an animator. DragonBones is abandoned. ChatGPT Images 2.5 (Sept 2026) is strong for backgrounds and single-character edits, weak for large consistent sprite sets; dedicated tools (Scenario $15–45/mo, Leonardo, Flux LoRAs) do better but still need heavy curation and a palette-mask system for recoloring. WebGPU has shipped on Android Chrome since v121.
- **3D:** three.js r186 is the fit for our stack (Babylon 9 runner-up); Godot/Unity web exports don't fit GitHub Pages or our codebase. Meshy's auto-rig is humanoid-only; Tripo's animal rigging unverified; Blender Rigify has animal rigs and Auto-Rig Pro ($50) handles quadrupeds/tails. AI 3D outputs from our own drawings keep originality; expect 20–60% rejects and topology problems. Full 3D estimated at 70–120 sessions vs 10–25 for 2D-plus.
- Sources: pixijs.com, rive.app docs and pricing, esotericsoftware.com/spine-purchase, openai.com (ChatGPT Images 2.5), scenario.com, developer.chrome.com (WebGPU), github.com/mrdoob/three.js/releases, blogs.windows.com (Babylon 9), docs.godotengine.org, meshy.ai/pricing and docs, developer.blender.org release notes, superhivemarket.com (Auto-Rig Pro), docs.github.com (Pages limits).
