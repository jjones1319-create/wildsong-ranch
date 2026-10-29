# Art 2.0: how to run it, step by step

This file is for you. It walks you through the whole art overhaul one step at a time and has every prompt ready to copy. Everything runs in Claude Code inside VS Code, the way you've built the game so far. The details Claude needs are in `docs/ART_2_PLAN.md`; each prompt tells Claude to read it.

**What happens:**
1. Claude uses **Blender to create everything**: every monster as a real 3D model with its skeleton, every animation and every face, in a slight anime/cartoon style.
2. The game shows those Blender models live on your phone, so the monsters move smoothly and fit into every scene. Mixes are gone (P0): every monster is its own whole design, painted individually in Blender.
3. Then Claude builds the scenes in Blender too (the farm, the arena, every drill, every cutscene, and the splashes and fire) and puts your monster inside them: on the rock, under the waterfall, getting soaked.

**Two checkpoints before the batches:**
- Don't start **P2** until you love the **P1** monster on your phone.
- Don't start **P3** until the **P2** waterfall scene is right.

Those two steps set the look for everything after. Fixing the look later would mean redoing a lot of work.

---

## The steps and their settings

| Step | What it does | Model | Effort | Advisor |
|---|---|---|---|---|
| **P0** | Retire the mix system: one breed per monster (rules and saves, no art) | Opus 5.5 | high | off |
| **P1** | The pilot monster: Puddlepup in 3D | Fable 5.1 | high | off |
| **P2** | The pilot scene: Waterfall Stand | Fable 5.1 | high | off |
| **P3** | Four-legged monsters 1: Tumblefox, Cobblemaw, Cinderlynx, Nimbusheep | Opus 5.5 | high | fable |
| **P4** | Four-legged monsters 2: Starhowl, Petalphant, Rammerjack, Hearthwing | Opus 5.5 | high | fable |
| **P5** | Two-legged monsters: Quillion, Grumblestone, Pluckrex, Gloomgrin | Opus 5.5 | high | fable |
| **P6** | Floating monsters: Wishlume, Ashwraith, Zipwisp, Mirrorkin, Frostlance | Opus 5.5 | high | fable |
| **P7** | Shelled and squishy monsters: Moatshell, Reefclaw, Bloatoad, Scrollopus | Opus 5.5 | high | fable |
| **P8** | Snakes and birds: Coilfang, Aurelwyrm, Galeheron, Paladove | Opus 5.5 | high | fable |
| **P9** | Bugs and machines: Nibblegrub, Velvesper, Gearhoot, Lootlid | Opus 5.5 | high | fable |
| **P10** | The farm (and the arrival scenes, and the title screen) | Opus 5.5 | xhigh | fable |
| **P11** | Battles: the arena and every attack's body movement | Opus 5.5 | xhigh | fable |
| **P12** | Visible attacks: every technique gets its own effect | Opus 5.5 | high | fable |
| **P13** | Drill scenes 1: Acorn Shower, Log Toss, Target Toss | Opus 5.5 | high | fable |
| **P14** | Drill scenes 2: Hill Sprints, Dodge the Gourds, Wind Chase | Opus 5.5 | high | fable |
| **P15** | Drill scenes 3: Puzzle Stones, Moon Meditation, Plow Pull, Quarry Haul | Opus 5.5 | high | fable |
| **P16** | Life moments: Shrine, Fusion, growing up, Farewell | Opus 5.5 | high | fable |
| **P17** | Bond games and Odd Jobs | Opus 5.5 | high | fable |
| **P18** | Places: town, Journeys, Expeditions | Opus 5.5 | high | fable |
| **P19** | Final polish, offline download, version 2.0 | Opus 5.5 | high | off |

**How to set them in VS Code:**
- **Model and effort:**
  1. Click the model name at the bottom of the Claude Code prompt box (or type `/model` and press Enter).
  2. Pick the model, then set the **Effort** row.
  3. Leave **Ultracode** off.
- **Advisor:** type `/advisor fable` or `/advisor off` in the prompt box and press Enter.
- **They're remembered,** so you only change them where the table changes: at P0, P1, P3, P10, P12 and P19.
- **Check before you paste:** the model name at the bottom of the prompt box shows the model and effort, so glance at it before pasting any prompt.

**Why these settings:**
- **Fable** sets the look in P1 and P2. That's where its judgment matters most.
- **Opus with Fable as an advisor** repeats that look in the batches. Opus does the work and checks with Fable at the big decisions, which keeps your Fable allowance (up to half your weekly usage on Max) for when it counts.
- **P1 and P2 are long.** Expect a few hours each plus your feedback rounds. P1 and P2 may use a big part of a week's Fable allowance, and that's expected.

---

## Before you start (once)

1. **Update Claude Code in VS Code.** Fable 5.1, Opus 5.5 and the Effort setting need a recent version.
   1. Open Extensions (`Ctrl+Shift+X`), click **Claude Code**, and click **Update** if it offers one.
   2. Press `Ctrl+Shift+P`, type **Developer: Reload Window**, and press Enter.
   3. In the Claude Code prompt box, type `/status` and press Enter. The version should be **2.1.284 or newer**.
2. **Keep your PC awake during runs.** Some steps run for hours, and they pause if the PC sleeps. In Windows:
   1. Open Settings → System → Power & battery → Screen, sleep & hibernate timeouts.
   2. Set "When plugged in, put my device to sleep after" to **Never**. You can switch it back later.
3. **Optional: concept pictures.** If you want Claude to see what you have in mind before it models a monster, make 2–3 ChatGPT pictures of it:
   1. Use the prompts in `docs/CONCEPT_PROMPTS.md`, but **paste the new style text from `docs/ART_2_PLAN.md` §2.4 instead of the old Style Guide.** The old one says "not anime".
   2. Save the pictures as `Monster Rancher/concept/puddlepup/sheet.png`, `expressions.png` and `action.png`. To make the folders in VS Code, right-click in the Explorer and choose **New Folder**.
   3. Do the same for each batch's monsters before their step if you like.

   Claude works from the written descriptions without them, so this is optional.
4. **Want a different first monster?** P1 and P2 use Puddlepup. To pick another, replace the word `Puddlepup` (and `puddlepup`) in both prompts with its name. Four-legged ones are the easiest start: Tumblefox, Cobblemaw, Cinderlynx, Nimbusheep, Starhowl, Petalphant or Rammerjack.

---

## How to run each step

1. **Open a new Claude Code tab.** In VS Code, with the **Monster Rancher** folder open, press `Ctrl+Shift+Esc` (or press `Ctrl+Shift+P` and choose **Claude Code: Open in New Tab**). Give each step its own tab: if VS Code restarts, the tab comes back and Claude carries on.
2. **Check the settings** at the bottom of the prompt box against the table: the model, the effort, and the advisor where the table changes.
3. **Switch to Plan mode.** Click the mode indicator at the bottom of the prompt box and choose **Plan**.
4. **Paste the step's prompt** (below) and press Enter.
5. **Approve the plan.**
   - VS Code opens Claude's plan as a document. Read it, and add a comment right in it if something's off.
   - When it looks right, approve it in the chat. If it asks how to carry on, choose **Auto**, so Claude can work without stopping to ask about every file.
6. **Let it work.** It builds, renders, looks at its own pictures, tests, and sends the update to your phone. You can leave the PC while it works.
   - A **blue dot** on the tab's Claude icon means it's waiting for you: a question or a permission. An **orange dot** means it has finished.
   - When Claude mentions a picture (a review sheet or the lineup), click the file name in the chat to open it in VS Code.
7. **Check on your phone.** When Claude gives you the "Try this on your phone" checklist, open the game, wait for **Update ready**, tap **Restart**, and go through the list.
8. **Tell Claude what to fix, in the same tab.**
   - Be specific: "the ears are too small", "it looks stiff when it walks", "it's too dark under the waterfall", "I want the water to cover more of its back".
   - Screenshots help. Get the screenshot onto your PC, copy it (`Ctrl+C`) and paste it into the prompt box (`Ctrl+V`), or hold `Shift` while dragging the file into the box. Add your note and send.
   - Repeat until you're happy.
9. **Start the next step** in a new tab.

---

## The prompts

### P1 · The pilot monster

```
Art 2.0, P1: the pilot monster.

Read CLAUDE.md, then docs/ART_2_PLAN.md in full (the spec for this whole overhaul), the GAME_DESIGN and CONTENT sections it points to, and the latest docs/PROGRESS.md entries. If concept/puddlepup/ has pictures, look at them first. Start in plan mode and show me your plan before you build.

Goal: make ONE monster, Puddlepup, a high-quality 3D monster built in Blender, in the plan's "slight anime/cartoon" style, and put it in the game so I can judge it on my phone. Blender creates everything about it: the model, its skeleton, every animation and its face sheet. The game only displays it. Every other breed stays as it is for now.

I approve the two new tools the plan names: three (in the game) and the glTF optimizer (dev only).

Build, in this order:
1. The Blender pipeline (ART_2_PLAN §3.1): the shared helpers, the quadruped rig with the clips marked ★ in §5, Puddlepup's recipe with its painted textures, its face sheet with every expression, export and optimizing, and the review sheets.
2. The runtime that displays it (§3.2): three.js as a lazy chunk, the cel shader with outlines, the secret-variant texture swap, the face sheet switching for expressions, blinks and glances, spring wobble, life-stage sizes, the Quality tiers and the Classic fallback.
3. In the game (§3.3): Monster Lab → Models (any breed, variant, stage, face and clip; turn it; an fps counter), Settings → Graphics → Monsters: 3D / Classic, and Puddlepup in 3D on every screen: live on the ranch, the Monster Card, the Lab, Versus and battles, and as portrait images in lists.
4. The review loop (§6), until it meets the quality bar. Then tell me the file name of the final in-game sheet so I can open it in VS Code.
5. The docs listed under P1 in §8.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P1: Puddlepup pilot", push, confirm the deploy, then give me the phone checklist and stop. I'll tell you what to change before we go on.
```

**Before you move on, check on your phone:**
- From every angle in Monster Lab → Models, it's cute and clearly Puddlepup.
- It moves like a living creature: it bounces, and its ears and tail lag behind.
- The faces are easy to tell apart.
- Songheart Puddlepup (the secret variant) looks right, if P1 includes it.
- It's smooth on the ranch and in a Versus battle.
- It has the slight anime/cartoon look you want.

### P2 · The pilot scene: Waterfall Stand

```
Art 2.0, P2: the pilot scene, Waterfall Stand.

Read CLAUDE.md, docs/ART_2_PLAN.md (especially §2.2, §3.4, §3.5 and §7.1), docs/SOUND_UPGRADE.md §8, docs/VISUAL_UPGRADE_PLAN.md §4 (V4) and the latest docs/PROGRESS.md entry (what we settled in P1). Start in plan mode.

Goal: when Puddlepup does Waterfall Stand, it really sits on a mossy rock under a waterfall: the water pours onto its head and back and splashes around it, and it gets soaked. Same slight anime/cartoon style as the monster.

Build:
1. The scene pipeline, all made in Blender: a script for the set; plates in depth layers (with a loop for the falling water if it helps); scene.json with the camera, anchors and light; the live props (the rock top, the falling water, the pool around the rock); and the splash, droplet and mist effects baked as flipbooks. Then the scene player in the game, with crop camera moves, timelines, effect cues and sound markers.
2. Waterfall Stand with all five endings in §7.1 (Great, with an extra flourish for Superb and Perfect; Success; Cheat; Fail; Slacked), 3–5 seconds each, tap to skip.
3. The clips marked ◆ in §5 for the quadruped rig, the wet look, and the monster lit by the scene.
4. In the game: the drill result plays this scene for Waterfall Stand (the other drills keep today's vignette), the drill sound follows the scene's markers, Reduce motion shows a still, and Settings → Sandbox → Preview scenes plays any ending with any monster (breeds without a model show the Classic drawing).
5. The review loop (§6) for the scene: in-game sheets of each ending at its key moments, plus a fresh-eyes review. Then tell me the file names of the final sheets so I can open them in VS Code.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P2: Waterfall Stand", push, confirm the deploy, then give me the phone checklist and stop.
```

**Before you move on, check on your phone (Settings → Sandbox → Preview scenes, and a real Waterfall Stand week):**
- It truly sits on the rock under the falling water, and the water covers and splashes it.
- Every ending is fun and clear.
- It looks right in the waterfall's light.
- Each ending lasts 3–5 seconds, and tapping skips it.

### P3 · Four-legged monsters, part 1

```
Art 2.0, P3: four-legged monsters, part 1.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2, §3.1, §3.3, §4, §5, §6) and the latest docs/PROGRESS.md entries: what P1 and P2 settled is the reference for the look. Start in plan mode.

Build:
1. Finish the quadruped clip set: every clip in §5, for Puddlepup too.
2. Four breeds: Tumblefox, Cobblemaw, Cinderlynx, Nimbusheep. For each one: look at concept/<breed-id>/ first if it exists; build it in Blender from its CONTENT brief and colors, in the pilot's style; build its painted textures and every quadruped clip; and run the review loop (§6) until it meets the quality bar.
3. Each one is live in 3D everywhere (§3.3) and works in Waterfall Stand.
4. End with the lineup sheet and tell me its file name so I can open it in VS Code.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P3: quadrupeds 1", push, confirm the deploy, then give me the phone checklist (include Sandbox → Preview scenes with each new breed) and stop.
```

### P4 · Four-legged monsters, part 2

```
Art 2.0, P4: four-legged monsters, part 2.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2, §3.1, §3.3, §4, §5, §6) and the latest docs/PROGRESS.md entries: what P1 and P2 settled is the reference for the look. Start in plan mode.

Build:
1. Four breeds: Starhowl, Petalphant, Rammerjack, and Hearthwing in both forms (young and grown; the grown form needs the quadruped rig's long-neck and wing options, §4, and Petalphant needs the trunk). For each one: look at concept/<breed-id>/ first if it exists; build it in Blender from its CONTENT brief and colors, in the pilot's style; build its painted textures and every quadruped clip; and run the review loop (§6) until it meets the quality bar.
2. Each one is live in 3D everywhere (§3.3) and works in Waterfall Stand.
3. End with the lineup sheet and tell me its file name so I can open it in VS Code.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P4: quadrupeds 2", push, confirm the deploy, then give me the phone checklist (include Sandbox → Preview scenes with each new breed) and stop.
```

### P5 · Two-legged monsters

```
Art 2.0, P5: two-legged monsters.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2, §3.1, §3.3, §4, §5, §6) and the latest docs/PROGRESS.md entries: what P1 and P2 settled is the reference for the look. Start in plan mode.

Build:
1. A new body plan: the biped rig (§4) and every clip in §5 for it, proven on Quillion first. Its sit, brace and fall must work in Waterfall Stand.
2. Four breeds: Quillion, Grumblestone, Pluckrex in both forms (young and grown), Gloomgrin. For each one: look at concept/<breed-id>/ first if it exists; build it in Blender from its CONTENT brief and colors, in the pilot's style; build its painted textures and every biped clip; and run the review loop (§6) until it meets the quality bar.
3. Each one is live in 3D everywhere (§3.3) and works in Waterfall Stand.
4. End with the lineup sheet (every finished breed so far) and tell me its file name so I can open it in VS Code.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P5: bipeds", push, confirm the deploy, then give me the phone checklist (include Sandbox → Preview scenes with each new breed) and stop.
```

### P6 · Floating monsters

```
Art 2.0, P6: floating monsters.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2, §3.1, §3.3, §4, §5, §6) and the latest docs/PROGRESS.md entries: what P1 and P2 settled is the reference for the look. Start in plan mode.

Build:
1. A new body plan: the floater rig (§4) and every clip in §5 for it, in its own way (gliding instead of walking, hovering low instead of sitting, pressed down by the water instead of bracing).
2. Five breeds: Wishlume, Ashwraith, Zipwisp, Mirrorkin, Frostlance. For each one: look at concept/<breed-id>/ first if it exists; build it in Blender from its CONTENT brief and colors, in the pilot's style; build its painted textures and every floater clip; and run the review loop (§6) until it meets the quality bar.
3. Each one is live in 3D everywhere (§3.3) and works in Waterfall Stand.
4. End with the lineup sheet (every finished breed so far) and tell me its file name so I can open it in VS Code.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P6: floaters", push, confirm the deploy, then give me the phone checklist (include Sandbox → Preview scenes with each new breed) and stop.
```

### P7 · Shelled and squishy monsters

```
Art 2.0, P7: shelled monsters and blobs.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2, §3.1, §3.3, §4, §5, §6) and the latest docs/PROGRESS.md entries: what P1 and P2 settled is the reference for the look. Start in plan mode.

Build:
1. Two new body plans: the shelled rig (with the crab option) and the blob rig (with the throat sac and tentacles), §4, each with every clip in §5.
2. Four breeds: Moatshell, Reefclaw, Bloatoad, Scrollopus. For each one: look at concept/<breed-id>/ first if it exists; build it in Blender from its CONTENT brief and colors, in the pilot's style; build its painted textures and every clip for its plan; and run the review loop (§6) until it meets the quality bar.
3. Each one is live in 3D everywhere (§3.3) and works in Waterfall Stand.
4. End with the lineup sheet (every finished breed so far) and tell me its file name so I can open it in VS Code.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P7: shelled and blobs", push, confirm the deploy, then give me the phone checklist (include Sandbox → Preview scenes with each new breed) and stop.
```

### P8 · Snakes and birds

```
Art 2.0, P8: serpents and birds.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2, §3.1, §3.3, §4, §5, §6) and the latest docs/PROGRESS.md entries: what P1 and P2 settled is the reference for the look. Start in plan mode.

Build:
1. Two new body plans: the serpent rig and the avian rig (§4), each with every clip in §5.
2. Four breeds: Coilfang, Aurelwyrm, Galeheron, and Paladove in both forms (young and grown, the grown one with four wings). For each one: look at concept/<breed-id>/ first if it exists; build it in Blender from its CONTENT brief and colors, in the pilot's style; build its painted textures and every clip for its plan; and run the review loop (§6) until it meets the quality bar.
3. Each one is live in 3D everywhere (§3.3) and works in Waterfall Stand.
4. End with the lineup sheet (every finished breed so far) and tell me its file name so I can open it in VS Code.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P8: serpents and birds", push, confirm the deploy, then give me the phone checklist (include Sandbox → Preview scenes with each new breed) and stop.
```

### P9 · Bugs and machines

```
Art 2.0, P9: insects and constructs, the last monsters.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2, §3.1, §3.3, §4, §5, §6) and the latest docs/PROGRESS.md entries: what P1 and P2 settled is the reference for the look. Start in plan mode.

Build:
1. Two new body plans: the insect rig and the construct rig (§4), each with every clip in §5.
2. Four breeds: Nibblegrub, Velvesper, Gearhoot, Lootlid, plus the cocoon Nibblegrub turns into (a 3D model the life-moments step will animate). For each one: look at concept/<breed-id>/ first if it exists; build it in Blender from its CONTENT brief and colors, in the pilot's style; build its painted textures and every clip for its plan; and run the review loop (§6) until it meets the quality bar.
3. Each one is live in 3D everywhere (§3.3) and works in Waterfall Stand. Every breed now has a model, so check that no screen still shows a Classic drawing unless Classic is chosen in Settings.
4. End with the full lineup sheet of all 33 looks and tell me its file name so I can open it in VS Code.

Keep to the budgets (§3.6). Run npm run verify, commit "Art P9: insects and constructs", push, confirm the deploy, then give me the phone checklist (include Sandbox → Preview scenes with each new breed) and stop.
```

### P10 · The farm

```
Art 2.0, P10: the farm.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2.2, §3.4–§3.7 and §7.2), GAME_DESIGN §6.9–§6.10 and the latest docs/PROGRESS.md entries. Waterfall Stand (P2) is the reference for quality and for how a scene works. Start in plan mode.

Build the ranch in Blender at Waterfall Stand's quality and make it the home screen's stage:
1. The homestead (barn, fence, path, the big tree, fields, hills, mountains) in all four seasons and every weather, with live rain, snow, lightning and drifting leaves. The upgrades show once bought (Cozy Barn, Training Yard, Tide Pool, Lantern Garden). The keepsakes are 3D props, and the monster sometimes plays with them.
2. The ranch stage: the monster lives in it (it idles by mood, wanders a little, sleeps, eats, and reacts when tapped or petted), lit by the season and weather.
3. The four arrival scenes (hello, sad, abandoned, note), rebuilt on the new farm with the live monster; the hello really runs up the path. Retire the old clips.
4. The title screen: the farm at golden hour with a monster or two.
5. The review loop for every season and weather and for each arrival scene, with one monster from each body plan, plus a fresh-eyes review.

Keep to the budgets (§3.6), especially download size and 60 fps. Run npm run verify, commit "Art P10: the farm", push, confirm the deploy, then give me the phone checklist and stop.
```

### P11 · Battles

```
Art 2.0, P11: battles.

Read CLAUDE.md, docs/ART_2_PLAN.md (§3, §5 and §7.3), GAME_DESIGN §12 (especially §12.11), docs/VISUAL_V1_EFFECTS.md and the latest docs/PROGRESS.md entries. Start in plan mode.

Build:
1. The Breeders' Guild arena by the river, in Blender: the ring, the rope-fence walls, banners, a crowd, and the river and town behind, in every season and weather.
2. Both monsters in 3D in the arena camera, with the effects layer and the damage numbers lined up exactly at every zoom (with a test).
3. A motion for every technique (§7.3), assigned by rules like the elements were, with a CONTENT column and a test. Plus hits, knockback with dust, KOs, wins and entrances.
4. Tournament walk-ons and the podium. Versus, the Battle Lab and the Effects Lab use all of it.
5. The review loop: sheets of a brawler and a caster from every body plan mid-attack, and 60 fps on Flashy.

Run npm run verify, commit "Art P11: battles", push, confirm the deploy, then give me the phone checklist and stop.
```

### P12 · Visible attacks

```
Art 2.0, P12: visible attacks.

Read CLAUDE.md, docs/ART_2_PLAN.md §7.3, docs/VISUAL_UPGRADE_PLAN.md §4 (V2), docs/VISUAL_V1_EFFECTS.md, CONTENT §3 and the latest docs/PROGRESS.md entries. Start in plan mode.

Give every one of the 294 techniques its own look: an attack recipe built from its P11 motion and the effects layer (wind-up, effect, travel, impact, hit reaction and sound), by family and element. Make the big elemental effects (fire, water, ice, smoke, lightning) in Blender as baked flipbooks; V1's code pieces add the sparks and flashes. Each breed's Signature techniques and the Specials get bespoke 1–2 second cinematics. I should be able to tell every technique apart by sight: a flame breath, an ice lance, a tidal wave. Review with contact sheets per element and a fresh-eyes pass. Keep 60 fps on Flashy.

Run npm run verify, commit "Art P12: visible attacks", push, confirm the deploy, then give me the phone checklist and stop.
```

### P13 · Drill scenes 1

```
Art 2.0, P13: drill scenes 1: Acorn Shower, Log Toss, Target Toss.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2.2, §3.4, §3.5 and §7.1), docs/VISUAL_UPGRADE_PLAN.md §4 (the V4 ideas), docs/SOUND_UPGRADE.md §8 and the latest docs/PROGRESS.md entries. Waterfall Stand (P2) is the reference for quality and for how a scene works. Start in plan mode.

For each drill:
- a real place around the vale, built in Blender;
- all five endings (Great with its flourishes, Success, Cheat, Fail, Slacked), 3–5 seconds each;
- props the monster really holds, throws or gets hit by;
- it works for all nine body plans;
- sound markers, a Reduce motion still, and Sandbox previews.

Review: sheets of every ending with one monster from each body plan, plus a fresh-eyes pass.

Run npm run verify, commit "Art P13: drill scenes 1", push, confirm the deploy, then give me the phone checklist and stop.
```

### P14 · Drill scenes 2

```
Art 2.0, P14: drill scenes 2: Hill Sprints, Dodge the Gourds, Wind Chase.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2.2, §3.4, §3.5 and §7.1), docs/VISUAL_UPGRADE_PLAN.md §4 (the V4 ideas), docs/SOUND_UPGRADE.md §8 and the latest docs/PROGRESS.md entries. Waterfall Stand (P2) is the reference for quality and for how a scene works. Start in plan mode.

For each drill:
- a real place around the vale, built in Blender;
- all five endings (Great with its flourishes, Success, Cheat, Fail, Slacked), 3–5 seconds each;
- props the monster really holds, dodges or gets hit by;
- it works for all nine body plans;
- sound markers, a Reduce motion still, and Sandbox previews.

Review: sheets of every ending with one monster from each body plan, plus a fresh-eyes pass.

Run npm run verify, commit "Art P14: drill scenes 2", push, confirm the deploy, then give me the phone checklist and stop.
```

### P15 · Drill scenes 3

```
Art 2.0, P15: drill scenes 3: Puzzle Stones, Moon Meditation, Plow Pull, Quarry Haul.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2.2, §3.4, §3.5 and §7.1), docs/VISUAL_UPGRADE_PLAN.md §4 (the V4 ideas), docs/SOUND_UPGRADE.md §8 and the latest docs/PROGRESS.md entries. Waterfall Stand (P2) is the reference for quality and for how a scene works. Start in plan mode.

For each drill:
- a real place around the vale, built in Blender (Moon Meditation at night, Quarry Haul at the old quarry);
- all five endings (Great with its flourishes, Success, Cheat, Fail, Slacked), 3–5 seconds each;
- props the monster really moves, pulls or carries;
- it works for all nine body plans;
- sound markers, a Reduce motion still, and Sandbox previews.

Every drill now has its scene, so retire the old prop vignettes except as the fallback. Review: sheets of every ending with one monster from each body plan, plus a fresh-eyes pass.

Run npm run verify, commit "Art P15: drill scenes 3", push, confirm the deploy, then give me the phone checklist and stop.
```

### P16 · Life moments

```
Art 2.0, P16: life moments.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2.2, §3.3–§3.5 and §7.4), the GAME_DESIGN sections for each moment (§7, §14.1, §15, §16 and §22's growth forms) and the latest docs/PROGRESS.md entries. Start in plan mode.

Make each moment a real scene with the live monster, built in Blender to the same quality:
- New Game's first monster (the Market gift and the Shrine);
- the Shrine awakening (the stone sings, light pours out, the monster forms);
- a Market purchase, and Pell's Fusion "Meet";
- the grow-up moment for Hearthwing, Pluckrex and Paladove;
- Nibblegrub's cocoon becoming Velvesper;
- the Farewell (retired, passed away, gone back to the wild), the Memorial, the Heartstone and the Freezer.

Keep them skippable, keep the sound cues in step, and give each a Reduce motion still. Review with sheets and a fresh-eyes pass.

Run npm run verify, commit "Art P16: life moments", push, confirm the deploy, then give me the phone checklist and stop.
```

### P17 · Bond games and Odd Jobs

```
Art 2.0, P17: Bond games and Odd Jobs.

Read CLAUDE.md, docs/ART_2_PLAN.md (§3.3–§3.5 and §7.5), GAME_DESIGN §6.9, CONTENT §4.1 and §13, and the latest docs/PROGRESS.md entries. Start in plan mode.

Bring the live monster and Blender-built settings into:
- Fetch, Hide-and-seek, and the Shopping trip down Market Lane;
- Echo Stones (the monster sits beside the stones, hums along and reacts);
- Meadow Dash (four 3D runners, 60 fps);
- Turnip Sort's chute.

The games must play exactly as they do now: same rules, timing, tap targets and scores (the e2e specs must still pass). Review with sheets and a fresh-eyes pass.

Run npm run verify, commit "Art P17: bonds and odd jobs", push, confirm the deploy, then give me the phone checklist and stop.
```

### P18 · Places

```
Art 2.0, P18: places.

Read CLAUDE.md, docs/ART_2_PLAN.md (§2.2, §3.4, §3.5 and §7.6), CONTENT §1, §7 and §8, and the latest docs/PROGRESS.md entries. Start in plan mode.

Build in Blender, to the same quality:
- Tunewick and its screens (the Shop, Market, Guild, Mailbox, Odd Jobs board, Pell's Lab, the Shrine of Echoes);
- the five Journey mentor sites (the four-beat Journey screen, and each site's own arena for its Trial battle);
- the four Expedition maps, with the monster on them;
- the credits roll.

Seasons and weather wherever the screen has them. Review with sheets and a fresh-eyes pass.

Run npm run verify, commit "Art P18: places", push, confirm the deploy, then give me the phone checklist and stop.
```

### P19 · Final polish

```
Art 2.0, P19: final polish and version 2.0.

Read CLAUDE.md, docs/ART_2_PLAN.md (§3.6, §3.7, P19 in §8 and §9) and the latest docs/PROGRESS.md entries. Start in plan mode.

1. Performance and size audit: 60 fps on the S25 Ultra on every 3D screen, a mid-range phone profile at High and a weak one at Lite, memory released when screens close, and every budget in §3.6 met. Report the numbers.
2. Settings → Download all art (showing its size), so the whole game works offline from day one.
3. Reduce motion, screen-reader labels and the Classic fallback, checked on every screen that changed.
4. Remove what's dead (the old prop vignettes, the old Bonds clips, ranch_scenes.py), keeping Classic monsters as the fallback.
5. Rewrite GAME_DESIGN §21–§22 for the new art; update README, CREDITS and BUILD_PLAN.
6. The full Playwright suite plus a fresh-eyes review of a lineup of every monster and a sheet of every scene.

Run npm run verify, bump to 2.0.0, commit "Art P19: final polish, v2.0.0", push, confirm the deploy, then give me the phone checklist and stop.
```

---

## If something goes wrong

- **It hit a usage limit mid-run.** Wait for the reset (the message tells you when), then type `continue` in the same tab. Typing `/usage` shows your limits.
- **It hit the Fable limit (P1 or P2).** VS Code asks whether to keep going on usage credits or switch models. Choose to switch (unless you want to pay), set Opus 5.5 with Effort xhigh, and type `continue`. It picks up where it was.
- **A monster or scene still isn't right after two rounds of feedback.** In the same tab, switch the model to Fable 5.1 (click the model name), then send: "Take over this fix: <what's wrong>. Look at the review sheets first."
- **VS Code closed or restarted mid-run.** Reopen VS Code with the Monster Rancher folder. The step's tab comes back, and Claude carries on by itself if it was interrupted less than an hour ago. If it's sitting idle, type `continue`. Can't find the tab? Click **Session history** at the top of the Claude panel and open the conversation from there.
- **The update doesn't show on your phone.** Wait a few minutes, close the game fully and reopen it. If it still doesn't show, ask Claude: "Check the deploy."
- **Something broke in the game.** Tell Claude exactly what you did and what happened. It can undo a step.
- **A batch was too big to finish.** Claude stops cleanly and says what's left. In a new tab, paste the same prompt with "Continue: finish what's left of this step" at the top.
- **Claude asks you to run a command or open Blender.** Reply "Please do it yourself." You never need to type commands or open Blender; Claude runs it all in the background from VS Code.

## After the overhaul: new monsters

Each new breed (like the bull-warrior idea) is then one short prompt, in a new tab in Plan mode, with Opus 5.5, Effort high and the Fable advisor:

```
Add a new breed: <its name and a description of how it looks, acts and fights>. Write its CONTENT entry (stats, kit, palette) with me first, then build it in Blender on the closest body plan following docs/ART_2_PLAN.md, run the review loop, make it live everywhere, and give me the phone checklist.
```
