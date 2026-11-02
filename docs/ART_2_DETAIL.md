# Art 2.1: monsters at the detail of the reference pictures

**Status:** revision 2, Nov 1, 2026.
- **The owner's targets:** the owner raised them (§1–§6): an **Ultra** tier for Galaxy S25-class phones, designed for the phone when it's hot.
- **Tried in a working spike:** the spike and the Performance check (§7) try them out.
- **Not yet in the game:** no monster is rebuilt and ART_2_PLAN §3.6 is unchanged until the owner approves the spike's look and the phone's Performance check result.

Approval then changes:
- ART_2_PLAN §2.1 (shading and lines), §3.1 (the pipeline), §3.2 (the runtime), §3.6 (the budgets) and §6 (the review loop);
- ART_2_PROMPTS, which gets a P1.1 step (§10).

**Read with:**
- `docs/ART_2_PLAN.md` (Art 2.0, which this extends);
- `chatgpt/FOR-CLAUDE-CODE.md` (§3 was the brief for revision 1);
- the owner's choices in `chatgpt/CHECKLIST.md`: the **film** look, and **fur** for Puddlepup.

## 0. In short

- **The goal:** the detail of the owner's ChatGPT pictures (`chatgpt/monsters/<NN>-<breed-id>/`): sculpted damp fur, real scales, feathers, stone, wood, metal and cloth, glossy 3D eyes and soft film-like light, in the class of high-end phone games.
- **The method:**
  - Blender builds a very detailed **source** for each monster (the spike's head and paw: 1.4 million triangles of fur clumps, ribbed fins and carved details).
  - It **bakes** the detail into textures for a lighter **game model**.
  - Soft **fur cards** show only where the coat meets the outline, so the silhouette is furry without the coat looking like scales.
- **The Ultra tier, measured on the spike:**
  - about 60,000 triangles and 2,800 fur cards per monster;
  - a 2048² body atlas, plus a 2048² cinematic head set for the Monster Card and cutscenes;
  - soft key-light shadows, ambient occlusion, bloom, colour grading, 4× MSAA and depth of field in cutscenes, no outlines;
  - dynamic resolution and quality that hold 60 fps by lowering the render resolution first, then effects, never the monster's detail.
- **Download per monster on Ultra:** about **7 MB** with everything, the cinematic set included (§5.3); about 4 MB for what a battle needs.
- **Graphics memory:** a two-monster battle needs about **0.3 GB** of the 1 GB starting budget (§6), and less with KTX2.
- **The proof** is the **Performance check** the owner runs on the S25 Ultra (§7): https://jjones1319-create.github.io/wildsong-ranch/perf/. It tests WebGL against WebGPU, then soaks a battle for 10 minutes and reports fps, render resolution, memory and throttling at the start and at the end.

## 1. The baseline phone, and designing for it hot

**Galaxy S25 Ultra:**
- Snapdragon 8 Elite for Galaxy (Adreno 830 at 1.2 GHz), 12 GB RAM;
- 6.9-inch 3120 × 1440 screen at 120 Hz;
- 3DMark Wild Life Extreme about **5,900**, stability **56%**: once hot it runs at roughly half speed.

What that means for the design:
- **The hot phone is the target.** Everything on Ultra must hold 60 fps at about half the cold phone's speed.
- **The PC proxy:** that hot speed is about this PC's Intel Iris Xe laptop GPU.
  - Iris Xe scores roughly 3,000–3,500 in Wild Life Extreme; the cold S25 Ultra is about 1.7× that, the hot one about 0.95×.
  - So the GPU timings in §4.3, taken on the Iris Xe, are a fair first guess for the hot phone. The phone's own check (§7) decides.
- **Frame budget:** 16.7 ms. The 3D scene gets about 12 ms of it; the effects layer, the UI and the browser need the rest.
- **The screen:** the phone's CSS width is about 412 px at about 3.5 device pixels per CSS pixel. Rendering at the full 3.5× would cost about 3× the pixels of 2×. Dynamic resolution (§3.6) picks what the warm phone can sustain, between 1.25× and 3.0×.

## 2. Tiers

| Tier | For | Draws |
|---|---|---|
| **Ultra** (new) | S25-class phones (Auto picks it when the check passes or the GPU is known) | LOD0 up to 100,000 triangles (aim 60–80k) with up to 5,000 standing locks and 6,000 fur cards in up to 3 layers; the 2048² body atlas; the cinematic set in cutscenes and on the Monster Card; spring bones on tufts, ears, tails and manes; soft shadows, AO, bloom, grading, 4× MSAA, depth of field in cutscenes; dynamic resolution 1.25–3.0× |
| **High** | other good phones | LOD0 up to 40,000 triangles (cards ≤ 1,200, one layer); the 2048² body atlas; no cinematic set (the Card uses the body atlas); springs; key-light shadow, no AO, bloom off; MSAA 4×; resolution 1.0–2.0× |
| **Lite** | weak phones | LOD1 (≤ 12,000 triangles, no cards); 1024² textures; no springs, no post effects; 30 fps cap; resolution 1× |
| **Classic** | no WebGL, or by choice | the SVG drawings, unchanged |

## 3. The techniques

### 3.1 High-to-low baking (the core)
- **One recipe, two builds.** Each look is built twice from one recipe. It's still numbers, not hand sculpting.
- **The source** (never ships):
  - a smooth body at a 3.5 mm voxel;
  - carved details: the mouth line, nostrils, whisker pits, the lip around each toe cap;
  - a coat of **surface elements** from the breed's kit (§3.8), scattered by a variable-radius Poisson disk, combed by a flow field and bent onto the surface;
  - separate pieces with their own material: fins, eyes, nose, pads, horns, shells.
- **The game mesh:**
  - the body decimated to budget (the spike's head: 14,000 triangles);
  - fins as thin sheets with real wavy edges;
  - eye domes as their own object, with their own glossy material;
  - the cards and tufts (§3.2).
- **The bake** (Cycles, selected → active, OptiX on the PC's RTX A500) writes:
  - **the body atlas:** normal, AO, colour (markings painted by position so they stay crisp and round), roughness and the clearcoat mask, plus a strip at the bottom holding the tuft-lock and fur-card tiles (with alpha);
  - **the cinematic head set:** the head, eyes and fins alone on their own 2048² atlas (a second UV set).
  - 30% of the AO is multiplied into the colour, so crevices stay dark under direct light on any renderer.
- **Timings:** build 15 s; the two bakes, the export and the stand-in about 5.5 min.

### 3.2 The outline: fins of soft fur, and small tufts
- **Soft fur cards** (4 triangles each, alpha-tested with alpha-to-coverage under 4× MSAA):
  - each card's texture is two or three damp clumps that taper to soft tips, fade in at the root and stand apart down to it;
  - a card takes the shaded body colour at its root as a vertex colour, and the body's normal, so it lights as part of the coat;
  - cards cast no shadow (a card's shadow on the coat just under it reads as a hole).
- **Fins: cards show only at the outline.** A card fades out as it turns to face the camera (alpha × a smooth step of 1 − |N·V|, 0.25 → 0.65).
  - Seen face-on, the coat is the baked fur. Where the coat curves away at the silhouette, the cards stand up as soft fuzz.
  - This replaced cards that showed everywhere, which read as sequins or scales (§8.3).
- **Layers:** two on the spike (the coat, plus a longer fringe on the cheeks and the back); up to 3 on Ultra.
- **Tufts:** small sets of real curved locks (the spike's crown tuft: 7 locks, 154 triangles). Nothing spiky breaks the outline anywhere else.
- **Not used:** shell fur. It multiplies the pixel cost.

### 3.3 Textures and KTX2
- **Maps per set:** colour (sRGB, with alpha for the card tiles), normal (MikkTSpace tangents exported), and ORM (AO, roughness, clearcoat mask).
- **Sizes:**
  - body atlas 2048² (the spike: 1152², the density 2048² gives a whole Puddlepup);
  - cinematic head set 2048²;
  - face sheet 2048²;
  - Lite: half size.
- **KTX2 (toktx 4.4.2, installed on this PC):**

| One 2048² cinematic set (colour + normal + ORM) | Download | GPU memory, with mipmaps |
|---|---|---|
| WebP (decoded to RGBA8) | 2.02 MB | ≈ 67 MB |
| KTX2, ETC1S everywhere | 2.06 MB | ≈ 11 MB (ETC2 / ASTC) |
| KTX2, ETC1S colour + UASTC normals | 3.6 MB | ≈ 14 MB |
| KTX2, UASTC everywhere | 6.4–7.3 MB | ≈ 17 MB |

- **The verdict:** **KTX2 with ETC1S everywhere passes on this PC.**
  - It looks the same as WebP: the mixed version is 39 dB PSNR from WebP and visually identical; the all-ETC1S panel looks the same at sheet size.
  - It downloads about the same as WebP.
  - It uses about **84% less graphics memory**.
  - UASTC is out: it would blow the 8 MB download cap.
  - **Adopt it** if the phone's frames look right: the check runs on it, and `?tex=webp` runs the same scenes on WebP for comparison.
- **4096²: not proposed.**
  - On the Monster Card the head is about 900–1,100 device px wide and the 2048² head set already gives it about 1.5 texels per pixel.
  - In battle the whole body is about 600–750 px tall at the resolution the phone sustains, and the 2048² body atlas gives about 1 texel per pixel.
  - A 4096² set would cost 4× the memory and download for detail the screen can't show. Revisit only if the phone shows blur on the Card.

### 3.4 The film material
- **Standard physical materials only** (`MeshPhysicalMaterial`), so the WebGL and WebGPU renderers draw the same thing (§4.2 shows them side by side):
  - **damp fur:** rough, a light clearcoat (0.12) and sheen (0.55);
  - **fins:** a gentle self-glow from their own colour (fake translucency, paler toward the edge);
  - **eyes:** their own material: no sheen, a modest coat, weak reflections, so the iris stays deep slate with crisp catchlights.
- **The studio light of the pictures:**
  - a soft key from the upper left that casts the only shadow, a warm rim from behind, and a cool sky fill (shadows cooler, never grey);
  - a procedural environment for reflections;
  - Neutral tone mapping;
  - a grey backdrop.
- **No outlines** (the owner's choice).
- Every number lives in `tuning.ts` → `ART.ultra`.

### 3.5 Effects on Ultra
- Soft shadows from the key light (2048² PCF soft shadow map).
- Ambient occlusion: GTAO; in WebGPU it reads a plain depth and normal pre-pass, because it can't read a multisampled depth buffer.
- Bloom (subtle), colour grading in display space (saturation, contrast, warm highlights, a light vignette), 4× MSAA.
- Depth of field in cutscenes and on the Monster Card.

### 3.6 Dynamic resolution and quality (designed for the hot phone)
- **Starting point:** Ultra starts at 2.5×, capped at 60 fps.
- **Going down:** each second the controller counts frames that arrived late (more than 1.15 × 16.7 ms).
  - If more than 5% were late, it lowers the resolution by 0.1× at a time, down to **1.25×**.
  - Only then does it drop effects, one step at a time: AO at half resolution, bloom off, the shadow map 2048 → 1024, AO off, MSAA 4× → 2×, MSAA off.
- **Coming back:** after 5 calm seconds (and 6 s after any drop), it restores in reverse: effects first, then resolution in 0.05× steps, up to 3.0×.
- **Never touched:** the monster's triangles, cards, textures and springs.
- The levels and numbers are `ART.ultra.levels` and `ART.ultra.scaling`.

### 3.7 Faces, the cinematic set, springs
- **Eyes:** 3D glossy domes. The face sheet grows to **2048²** in the cinematic set (1024² in-game).
- **Morph targets:** up to **24** in the cinematic set (mouths, cheeks, brows, the open grin with tongue and teeth). In-game uses the first 8.
- **Spring bones:** fur tufts, ears, fins, tails and manes get light spring chains on top of the clips (Ultra and High). They extend Art 2.0's springs, which already run on ears and tails.

### 3.8 Surface kits
Unchanged from revision 1: wet fur, short velvet, long fluffy fur and manes, wool and down, scales, feathers, stone, plants, wood, metal, cloth, paper, glass, ice and crystal, skin, membranes, and glow, matched to every card's "Surfaces and materials" line.
- Fins of fur cards are the outline technique for every furry and fluffy kit.
- Feather and plume cards use the same edge fade.

## 4. Measured

### 4.1 The spike (head, both fins and one front paw; about 45% of a whole Puddlepup's surface)
| What | Measured |
|---|---|
| Source | 2.30 million triangles, 13,238 sculpted wet locks (top surfaces only; round 5) |
| Game triangles | head 14,000 · eyes 1,056 · fins 3,072 · paw 4,000 · head cards 2,272 (568 cards) · paw cards 504 (126 cards) · tuft 154 (7 locks) = **25,058** |
| Mesh `.glb` (meshopt, two UV sets on the head, tangents, colours) | 418 KB |
| Body atlas 1152² | WebP 778 KB · KTX2 ETC1S 754 KB |
| Cinematic head set 2048² | WebP 2.02 MB · KTX2 ETC1S 2.06 MB |

### 4.2 The performance stand-in
The spike's head, four copies of its paw and a grey-box torso and tail built with the same fur pipeline (its own 2048² atlas): **59,548 triangles and 2,806 fur cards**. This is the low end of the Ultra aim, not the rebuilt Puddlepup. Two of them fight in the check's battle.

### 4.3 GPU time on this PC (Intel Iris Xe ≈ the hot S25 Ultra, §1)
The check's own scenes on a 412 × 560 CSS-px canvas, all Ultra effects, measured with the GPU timer (the final round of the spike):

| Scene | Pixel ratio | GPU per frame |
|---|---|---|
| Battle, two stand-ins, WebGL | 2.0× | 17.4 ms |
| Battle, two stand-ins, WebGL | 2.5× | 27.3 ms |
| Battle, two stand-ins, **WebGPU** | 2.5× | **10.6 ms** |
| Monster Card close-up, cinematic + depth of field, WebGL | 2.5× | 36.9 ms |
| Meadow Dash, four stand-ins, WebGL | 2.5× | 26.5 ms |

How to read it:
- **WebGPU is about 2.6× faster than WebGL** here for the same picture. Most of the gap is the WebGL post chain: GTAO re-renders the scene for normals, and the composer copies half-float buffers.
- **On WebGL, a hot S25 Ultra would hold 60 fps** in battle at about 1.5–1.6× resolution. On WebGPU it could at about 2.5×.
- **The Monster Card needs dynamic resolution most:** a close-up fills the screen with fur.
- The phone's check decides; these numbers set the expectation.

## 5. Budgets (the owner's targets, Nov 1)
### 5.1 Per monster
| Item | Ultra | High | Lite |
|---|---|---|---|
| Triangles | LOD0 ≤ 100,000 (aim 60–80k) | ≤ 40,000 | ≤ 12,000 |
| Standing locks / tufts | ≤ 5,000 locks | ≤ 1,000 | none |
| Fur cards | ≤ 6,000 in ≤ 3 layers | ≤ 1,200, one layer | none |
| Body atlas | 2048² colour, normal, ORM | 2048² | 1024² |
| Cinematic set (Card, cutscenes only) | 2048² head set + 2048² face sheet + ≤ 24 morph targets | none | none |
| Face sheet in game | 1024² | 1024² | 512² |
| Spring bones | tufts, ears, fins, tails, manes | ears, tails | none |
| Deform bones | ≤ 64 (+ spring chains) | same | same |
| Download | **≤ 8 MB** with everything, loaded only when needed | ≤ 3.5 MB | ≤ 1.5 MB |
| Graphics memory | ≈ 15 MB in battle with KTX2 (≈ 70 MB on WebP); + 15 MB cinematic | ≈ 15 MB | ≈ 4 MB |

### 5.2 The game on Ultra
- **Graphics memory:** start at about **1 GB for the whole game**, then set the real ceiling from the check's memory test (§6).
- **Frame rate:** 60 fps after 10 minutes of battle, with dynamic resolution (§7.4). Meadow Dash and the Monster Card also hold 60.

### 5.3 Download totals (estimated from the spike)
| Part | Ultra, KTX2 ETC1S | Ultra, WebP |
|---|---|---|
| LOD0 mesh (~70k triangles) + LOD1 | ≈ 1.4 MB | ≈ 1.4 MB |
| Rig, clips, 24 morph targets | ≈ 0.5 MB | ≈ 0.5 MB |
| Body atlas 2048² | ≈ 2.4 MB | ≈ 2.5 MB |
| Cinematic head set 2048² | ≈ 2.1 MB | ≈ 2.0 MB |
| Cinematic face sheet 2048² | ≈ 0.5 MB | ≈ 0.4 MB |
| **One monster, everything** | **≈ 6.9 MB** | **≈ 6.8 MB** |
| What a battle loads (no cinematic set) | ≈ 4.3 MB | ≈ 4.4 MB |
| **All 35 looks, everything** (32 breeds + 3 grown forms) | **≈ 240 MB** | ≈ 240 MB |

- The cinematic set loads only when a cutscene or the Monster Card needs it.
- Every model is runtime-cached and never precached, so a player downloads only the monsters they meet.
- **Download all art** (P19) must show these totals and offer the in-game sets only (≈ 150 MB) or Lite only (≈ 40 MB).

## 6. Graphics memory
Estimated for a two-monster battle on Ultra at 2.5×, the battle canvas being 412 × 560 CSS px:

| Item | Size |
|---|---|
| Monster textures: 2 × body atlas | KTX2 ≈ 30 MB (WebP ≈ 135 MB) |
| Render targets: 4× MSAA half-float colour and depth, resolve, composer buffers, AO, bloom | ≈ 150 MB |
| Shadow map 2048² | 16 MB |
| Scene plates, effects and UI | ≈ 50 MB |
| **Total** | **≈ 0.25 GB with KTX2 (≈ 0.35 GB on WebP)** |

- The Monster Card adds the cinematic set (≈ 15 MB KTX2).
- The check reports its own estimate at the start and the end of the soak.
- Its opt-in **memory ceiling test** fills graphics memory with 2048² textures until the phone refuses, and records the last safe figure. That sets the real ceiling in place of the 1 GB starting budget.

## 7. The Performance check (built; on the phone)
### 7.1 Where
- **The page:** https://jjones1319-create.github.io/wildsong-ranch/perf/. It's a separate page from the game:
  - its own small build, `perf/` and `vite.perf.config.ts`, with its code in `src/art3d/perf/`;
  - the game's service worker leaves it alone and never downloads it.
- **What it draws:** the stand-in (§4.2) with the Ultra rendering.
- **Assets:** from `public/models/perf/` and three's KTX2 transcoder in `public/basis/` (both kept out of the game's precache).
- **Text formats:** add `?tex=webp` to run the same scenes on WebP.

### 7.2 What it runs (about 14 minutes)
1. **Renderer A/B:** the battle for 30 s on WebGL, then 30 s on WebGPU, uncapped, at the screen's own resolution (at least 2.0×). It keeps a frame from each so the owner can see they look the same, and continues with the faster one.
   - When both reach the screen's frame limit, the GPU time decides.
   - Android gives WebGL no GPU timer, so WebGPU wins a tie when its own GPU time leaves room.
   - `?renderer=webgl` or `?renderer=webgpu` in the address forces one.
2. **Monster Card close-up:** cinematic set and depth of field, 30 s, capped at 60, at 2.5×.
3. **Meadow Dash:** four stand-ins, 30 s.
4. **Speed probe, cold:** 5 s, uncapped at a fixed 2.0× with every effect.
5. **The battle soak:** **10 minutes** with dynamic resolution and quality, capped at 60 fps. The resolution never goes above the screen's own (2.625× on the owner's S25 Ultra at its default FHD+ setting).
6. **Speed probe, warm:** the same 5 s again. The ratio warm ÷ cold is the throttling factor.

The screen stays on (Wake Lock).

### 7.3 What it reports
- **The device:** the browser, the screen, and the renderers' GPU.
- **For the A/B, the close-up, Meadow Dash and both probes:**
  - fps, the 95th-percentile frame time and the share of late frames;
  - the GPU time where the browser exposes it;
  - **the CPU time:** the page's own work per frame. When it's high, the processor is the limit, not the graphics chip.
- **For the soak's first and last 30 s:**
  - fps;
  - **the render resolution** (pixels and pixel ratio);
  - the effect level it had to drop to;
  - GPU time;
  - **graphics memory** (estimated) and the JavaScript heap.
- **The controller:** how many times it changed the resolution or effects, and the range it used.
- **A timeline of the soak:** fps, resolution, effects, GPU and CPU time and late frames for every 30 s.
- **Throttling:** how much slower the same frame is at the end.
- **The scene:** triangles, cards and draw calls.
- **Copy results** puts the whole report on the clipboard for Claude Code. The last result is kept on the phone (`wildsong/perf/last`).

### 7.4 Pass
- **PASS** = the soak's last 30 s average ≥ 58 fps with < 2% late frames, with dynamic resolution.
- The report also shows the resolution the phone needed to hold that.
- 60 fps at only 1.25× and no effects would technically pass but tells us the look needs trimming. The report makes that visible.

### 7.5 The first phone run (Nov 2): the check was wrong, not the phone
**The S25 Ultra's run:**
- **Cold, every scene held 60 fps:** the battle at 2.0× on both renderers, the Card close-up, Meadow Dash and the probe. WebGPU's GPU time was 10.1 ms of the 16.7 ms frame.
- **The soak then reported 29 fps falling to 24, at 1.3–1.5× with every effect off.** That was a FAIL with 2.5× throttling.

**The check itself caused most of it:**
1. **Rebuilding on every change.**
   - Every resolution or effect change rebuilt WebGL's whole effect chain. The rebuild's own hitch looked like slowness, so the controller stepped down again, and it reached the bottom within about 20 s.
   - Every rebuild leaked its render targets.
   - WebGPU's level changes leaked their effect nodes too.
2. **Timing after the draw.** The soak timed frames after drawing them, so any frame with more drawing work than the last looked late.
3. **A tie went to WebGL.** Both renderers sat at the screen's 60 fps limit, so the A/B kept WebGL even though only WebGPU's GPU time was known (and it had room).
4. **Smaller faults:**
   - a cap that skipped a frame whenever the display's timing jittered early;
   - a step-up rule that needed a perfect second;
   - `preserveDrawingBuffer`, a full-screen copy every frame on phones;
   - a resolution ceiling above the screen's own.

**After the fixes (v1.13.3), this PC's quick run:**
- WebGPU holds 60 fps at 2.6× with every effect for the whole soak: GPU 10 ms, CPU 8–10 ms, two controller changes. It passes.
- WebGL needs 25 ms of GPU for the same frame.
- **Watch the CPU time on the phone:** about 8–10 ms per frame here. The stand-in draws each monster as about 15 pieces; a finished monster will be about 5.

The phone's re-run decides.

## 8. The spike, round 2
### 8.1 What changed after the owner's notes
- **Head:** rounder and narrower, from 2-turnaround.png. A higher forehead dome, a longer muzzle in profile, a shallower head.
- **Ears:** they start on the upper sides of the head and hang down past the cheeks, with a furry cap over the top 40% and a band down the outer edge. The fins' far edge is a gentle wave, not saw teeth.
- **Fur:**
  - baked clumps are softer and flatter, with clearer strands, tapering to soft points (no round petals, no hard blades);
  - fur cards as fins at the outline only (§3.2);
  - the tuft is 7 short curved locks (9 in round 2); nothing else spiky.
- **Muzzle:** smaller, smooth and plush cream, no fur clumps or pores. The blush is a soft spot painted by position.
- **Markings:** crisp round dapples by position (the round forehead spot of the pictures).
- **Eyes and paw:**
  - the eyes have their own dark glossy material;
  - the paw is broad, wider than the leg, with teal toes, pink caps only on the tips and a cream rim.
- **Lighting:** the pictures' bright soft studio at the hero's angle.

### 8.2 Review
`art-review/detail-spike/sheet.png`: the references beside every view, the cinematic and in-game sets, WebGPU against WebGL, KTX2 against WebP, the stand-in, the PC timings and the 64 / 100 / 200 px sizes. The fresh-eyes reviewer's verdict on this round is in §8.4.

### 8.3 Lessons
- **Card textures:** their clumps must stand apart down to the root. A card whose lower half is solid alpha reads as a flake.
- **Cards that face the camera read as sequins or scales.** Fade them by view angle (fins), so the coat is the bake and the cards are the outline.
- **Cards must not cast shadows.** Their shadow on the coat right under them reads as a hole.
- **Cards are front-side only.** A card's back face gets a flipped normal and renders nearly black at the outline.
- **Only the source may shadow the bake.**
  - With the game's own cards, tuft and low mesh visible to the AO rays, the baked fur surface sat in their shadow: the stand-in's AO came out almost black (median 0.03). The aoMap then drew black wedges wherever only fill light reaches (throat, chest).
  - The bake now hides everything but the sources and makes the low mesh invisible to rays.
  - Lying clumps are top surfaces only: closed undersides between overlapping clumps also bake dark.
- **A glossy dark part reflects the room.** With `scene.environment` set, three uses `scene.environmentIntensity` for every material without its own envMap, so a dark eye or nose turns grey. Cut its specular instead, or give it its own envMap.
- **A flat fan rooted on the head runs inside it.** Wrap the ear around the outside of the head, so it shows from its root.
- **Paint thin lines on the body only.** A clump rooted on a painted line takes the colour along its whole length and reads as a speck.
- **Eyes need their own material.** Fur sheen on an eye turns it milky grey.
- **GTAO in WebGPU** can't read a multisampled depth buffer. Give it a plain depth and normal pre-pass.
- **Markings that must stay round** (dapples, blush) are painted by position. Markings that should follow the fur are painted by root.
- **Editing the page while a capture runs** makes Vite reload it. Captures run only after edits.

### 8.4 The fresh-eyes verdict
**Round 2: detail and design "no"; 64 px "partly".**

What it liked:
- the sheen is right and the fur no longer looks glossy;
- the muzzle is smooth, with no stringy lines;
- the ears come off the top corners.

What it asked for, most important first:
1. **Ears:** one cupped flap with teal fur over the pink ribbed face, hanging closer to the cheek. The round bumps on top read as teddy-bear ears. Fins that glow read as neon.
2. **Head:** a smooth dome with no bumps, and a softer tuft.
3. **Eyes:** dark teal irises with big pupils. They read silver because the dark glossy eye reflected the bright studio room. The brows should be soft dark dashes, not scribbles.
4. **Light:** less washed out, cream not clipping, a visible warm rim.
5. **Muzzle and nose:** a smaller muzzle, a bigger black nose, a rosier blush.

### 8.5 Rounds 3 and 4
**Round 3** (the eyes, the brows, the face, the light):
- **The ear roots** sit inside the head's curve. Round 2's stood 5 cm proud of the dome.
- **Eyes:** 10% bigger, with a big dark pupil, a deep teal iris and a dark rim instead of a white ring.
  - Their reflections are cut with a weaker specular (`eyeSpecular`).
  - Why it was needed: three uses the scene's environment strength for any material without its own envMap, so the eye's `envMapIntensity` was being ignored.
- **Brows** are one soft dash per side, painted by position.
- **Nose and blush:** a bigger black nose and a rosier blush.
- **Muzzle and tuft:** a smaller muzzle and a tuft of 7 shorter locks.
- **Light:**
  - less fill and room light;
  - a sheen colour close to the fur's own;
  - bloom only above 1.2;
  - fins that barely glow.

**Round 3 verdict: detail and design "no"; 64 px "partly".**
- The eyes, nose and colours improved.
- The ears still splayed sideways like gills: a flat fan whose inner edge ran inside the head showed only from mid-side.
- The muzzle was still big.
- The tuft read as spikes.
- The coat read as a printed chevron pattern.

**Round 4** (the ears, the muzzle, the silhouette):
- **Ears:**
  - each ear wraps the outside of the head and cheeks from its root on top, hanging 3 cm out (the fur between);
  - the pink face looks mostly forward;
  - the pleats are gone (they read as a crimped paper fan);
  - the head's shadow no longer falls on the fins (it read as smudges).
- **Muzzle:**
  - smaller and set back, with a thinner mouth line;
  - no whisker pits;
  - the mouth colour stays on the muzzle (a clump rooted at its corner had taken it: a brown speck).
- **Head:**
  - 5% narrower, with smaller cheeks and neck;
  - the tuft is wider and swept to one side;
  - the dapples have soft edges.
- **Fur:**
  - clump tips are rounded rather than pointed;
  - the gaps between clumps are darker;
  - there's a glossier streak along each clump.
- **Light:**
  - a stronger warm rim from the side the camera sees;
  - more fill;
  - normals at 0.6.

**Round 4 verdict: detail and design "partly" (up from "no"); 64 px "partly".**
- **Better:** the palette, the big glossy eyes, the dapples and the drooping ears read as Puddlepup. The sheen level is right and the blush is soft.
- **Still short of the pictures:**
  - **Fur:** the baked clumps read as overlapping leaves. Pointed tips read as chevrons and rounded ones as scales: the coat needs a different technique, not more tuning (below).
  - **Ears:** the pink membranes are narrow strips under the flaps; in the pictures each is a fan about as tall as the head.
  - **Head:** a little bottom-heavy (jowls), too deep from the side, with a bulge at the back.
  - **Light:** still no visible warm rim; the fins look unlit.
  - **Muzzle:** a stray clump on its right side and a wobbly mouth line.

**Round 5** (the owner chose the realistic coat and asked for eyes that don't stick out):
- **Coat:** long narrow wet locks, about 3:1, instead of leaf-shaped clumps (about 1.2:1).
  - 13,238 locks from 2.3 million source triangles, baked in about 10 minutes.
  - The card tiles show three or four thin locks each.
- **Eyes:** a flatter lens set into the face, about 0.9 cm proud instead of 2.4 cm, at the same visible size, with the fur closer to its edge.
- **Ears and head:**
  - the membranes are as tall as the head and fan out wider;
  - the head is shallower front to back;
  - the cheek fluff is higher, with no jowls;
  - the cream reaches up the cheeks.
- **Light:** a second warm rim from the other back side, so the warm edge shows on both outlines.

**Round 5 verdict: detail and design "partly"; 64 px "partly"** (same as round 4).
- **Better:** the palette, the eye size, the spots and the droopy flaps; the soft blush.
- **The reviewers disagree:**
  - on the coat, round 4 saw leaves and round 5 sees fine streaks;
  - on the nose, round 2 wanted it bigger and round 5 wants it 40% smaller.
- **Round 6, what both rounds agree on:**
  - **Muzzle:** one smooth short cream muzzle, not three lobes. One soft smile line. No strands under the nose. The teal comes down in a V between the eyes.
  - **Eyes:** an upper lash line under a fur lid instead of the full black ring (it reads as goggles).
  - **Fins:** coral, not bubblegum pink, with darker shaded ribs, narrower at the root, hanging to the jaw angled slightly forward.
  - **Outline:** no stray cards at the ear roots and cheeks; a smaller teal tuft that doesn't blow out.
- **The owner's eye decides** whether round 6 runs before the pipeline work.

## 9. Plan after approval
- **A1, the pipeline:** generalise the spike into `lib/surface.py` and `lib/bake.py`, with LOD0 / LOD1, the cinematic set, the material sidecar, KTX2 ETC1S encoding and the new `optimize.ts` budgets.
- **A2, the runtime:**
  - the film material and the Ultra effects in `src/art3d/`, on whichever renderer the phone chose;
  - dynamic resolution and quality;
  - tiers and LODs, card fins, spring bones, eye domes, morph targets.
- **P1.1, Puddlepup at Art 2.1:**
  - rebuild it from the pictures with every clip, the cinematic set and Songheart Puddlepup;
  - run the review loop with the pictures;
  - the owner runs the Performance check with the real model.
  - CONTENT §2.2's art brief gets the damp fur coat and the nose.
- **Then** P2 (Waterfall Stand) and the P3–P9 batches, each breed with its surface kit.

## 10. What approval changes in the other docs
- **ART_2_PLAN:**
  - §2.1: film shading, no lines, 3D eyes and morphs;
  - §3.1 and §3.2: point here;
  - §3.6: the tables in §5;
  - §6: references on every sheet, and the two fresh-eyes questions;
  - §8: A1, A2 and P1.1 before P2.
- **ART_2_PROMPTS:** a P1.1 prompt; every batch prompt reads this file.
- **CLAUDE.md:**
  - the tools: toktx (installed), and `npm run perf:dev` for the check page;
  - the Ultra tier;
  - "only `src/art3d/` imports three" now includes `src/art3d/perf/`.
