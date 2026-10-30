# ChatGPT reference pictures for the monsters

These pictures are the blueprint for rebuilding the monsters in Blender. ChatGPT draws each monster in high detail from every angle: sculpted fur in clumps and strands, real scales, feathers, stone, wood and metal. Claude Code then builds the 3D model to match. The pictures are reference only. They never ship in the game, and they stay on this PC (they're kept out of GitHub).

**Start with 01 Puddlepup.** Its hero picture becomes the style anchor that every other monster matches.

## What's here

```text
chatgpt/
  README.md                ← start here
  PROJECT-INSTRUCTIONS.md  ← paste once into the ChatGPT project
  FIXES.md                 ← what to type when a picture comes out wrong
  CHECKLIST.md             ← tick off each picture
  FOR-CLAUDE-CODE.md       ← how Claude Code uses the pictures (you don't need to read it)
  style-anchor.png         ← you save this after Puddlepup's hero
  monsters/
    01-puddlepup/PROMPTS.md   ← that monster's prompts; save its pictures in the same folder
    02-tumblefox/PROMPTS.md
    …
    30-lootlid/PROMPTS.md
```

## One-time setup (about 10 minutes)

1. **Make a project.** In ChatGPT, click **New project** in the sidebar and name it `Wildsong Ranch – Monsters`. If it offers **project-only memory**, choose it. You can only pick it when you create the project, and it stops your other chats leaking into the designs.
2. **Add the instructions.** Open the project's **⋯** menu, choose **Instructions**, and paste everything inside the box in `PROJECT-INSTRUCTIONS.md`. First read the short note under the box. It lets you choose between the rich film-quality look (the default) and the flatter anime cel look.
3. **Use the best image setup.** Use the newest image model ChatGPT offers. In each chat, pick a **Thinking** model if your plan has one. It lays out multi-panel sheets (turnarounds, faces) much more reliably.
4. **Write down your two choices.** At the top of `CHECKLIST.md`, choose the look (film or anime cel; see the note under the box in `PROJECT-INSTRUCTIONS.md`), and whether Puddlepup has fur or smooth skin (see the "Fur or skin?" note at the top of its `PROMPTS.md`). Claude Code reads these later.
5. **Make the style anchor.** Do Puddlepup's step 1 (the hero) first. When you're happy with it, save it twice:
   - as `chatgpt/monsters/01-puddlepup/1-hero.png`;
   - as `chatgpt/style-anchor.png`.

   Every other monster's hero is made with this picture attached, so all 30 share one look and one level of detail. Attach it only where a step says to; don't add it to the project's files, or it can leak into other pictures.

## Making one monster (about 20–40 minutes)

1. **Start a new chat inside the project** for each monster, named like `07 Petalphant`. A fresh chat per monster stops designs bleeding into each other.
2. **Open that monster's `PROMPTS.md`.** Each step has a box. Above it, the step says what to **attach** first (drag the file into the message box). Copy the whole box, paste it and send.
3. **Step 1 is the hero**, with `style-anchor.png` attached. Regenerate or fix it until it passes the quality bar below. This is the design, and everything after copies it. Save it as `1-hero.png` in the monster's folder (see "Saving" below).
4. **Every step after that:** attach exactly the file(s) on that step's **Attach** line, paste, check, and save under the name shown. Attaching the approved picture again is the best cure for drift.
   - Usually the attachment is this monster's `1-hero.png`.
   - Grown-form steps use `grown-1-hero.png`, and the cocoon turnaround uses `cocoon-1-hero.png`.
   - The scale check needs two files that are both called `1-hero.png`: one from this monster's folder and one from `01-puddlepup`. Don't attach the same one twice.
5. **Something wrong?** Don't start over. `FIXES.md` has the exact words to type. For a small area, use ChatGPT's select or edit tool on that part of the picture.
6. **Tick it off** in `CHECKLIST.md`.

## The quality bar

Approve a picture only when all of these are true:

- **It matches the card.** Count the legs, toes, ears, wings, horns and tails, and check the markings are where the card says.
- **The colours are right.** The shading will vary, but the body must clearly be the body colour, and so on.
- **It's clearly more detailed than the game's Puddlepup today.** Zoom in: you should see fur clumps and strands (or scales, feathers, stone grain, wood grain…), not smooth plastic.
- **It reads at phone size.** Zoom out until it's as small as your thumbnail. The silhouette and the face should still be clear.
- **It's original.** If it reminds you of a famous character, fix it.
- **Sheets line up.**
  - In the turnaround, every view is the same height, on the same ground line, and shows the same creature. A top view is the exception: it sits beside the others, seen from above.
  - In the faces, the head is identical in every panel and only the face changes.
- **The background is plain grey.** The exceptions are the boulder-and-pool setting in pose panels 1–2 and the faint guide lines on turnarounds. There's no text except the small labels a box asks for.

## Saving

- Use ChatGPT's **download** button, so you get the full-size picture. Never use a screenshot.
- The download lands in your **Downloads** folder with a long name. Move it into the monster's folder, then rename it to exactly the name shown (`1-hero.png`, `2-turnaround.png`, …). Claude Code looks for these names.
- If your file names don't show ".png" at the end, Windows is hiding extensions. Type only `1-hero`, or you'll get `1-hero.png.png`.
- The pictures are kept out of GitHub on purpose (`chatgpt/.gitignore`), because about 190 big images would bloat the repo. **Back the folder up** yourself (OneDrive, Google Drive or a zip), since GitHub won't have them.

## Order

Follow the folder numbers. They match the Art 2.0 build batches: 01 Puddlepup, then P3 (02–05), P4 (06–09), P5 (10–13), P6 (14–18), P7 (19–22), P8 (23–26) and P9 (27–30).

Puddlepup goes first for two reasons: it sets the style anchor, and its poses show the Waterfall Stand (sitting on the rock and bracing under the water), the next scene Claude Code builds (P2).

## How many, and how long

- **The count:** 191 pictures in all, plus retries and up to 29 optional scale checks:
  - 30 monsters × 5;
  - 21 rare variants;
  - 3 grown forms;
  - the cocoon.
- **The limit:** ChatGPT caps how many images you can make in a few hours. On Plus it's roughly 40–50 every 3 hours, and it tells you when you can continue.
- **The pace:** plan on 2 to 4 monsters per sitting.

## Copying the boxes

- **On GitHub** (once the folder is committed), every box has a copy button.
- **In VS Code**, open a `PROMPTS.md` and press **Ctrl+Shift+V** for the preview, then select a box's text and copy it.

## When the pictures are done

Come back to the Claude chat and say so, and we'll move forward. Next come the scenes, plus the prompt that upgrades Claude Code's Art 2.0 plan to this level of detail.

If you'd rather get Claude Code started as soon as Puddlepup's pictures exist, paste this into the Claude extension in VS Code:

```text
Read chatgpt/FOR-CLAUDE-CODE.md, then look at every picture in chatgpt/monsters/01-puddlepup/ and at the current Puddlepup review sheets in art-review/.

1. Paths: update docs/ART_2_PLAN.md and ART_2_PROMPTS.md so every place that reads concept pictures from concept/<breed-id>/ reads them from chatgpt/monsters/<NN>-<breed-id>/ instead, with the file names and the "which source wins" rules in chatgpt/FOR-CLAUDE-CODE.md. Point ART_2_PLAN §2.4 and docs/CONCEPT_PROMPTS.md to chatgpt/PROJECT-INSTRUCTIONS.md as the style text now in use.
2. Detail: I want the monsters to reach the detail of these pictures (sculpted fur clumps and strands, scales, feathers, real materials), well above the P1 Puddlepup. Write docs/ART_2_DETAIL.md (Art 2.1): what the P1 pipeline can't reach, the techniques you propose (start from FOR-CLAUDE-CODE.md §3), the new ART_2_PLAN §3.6 budgets with numbers, and a test plan that proves 60 fps on the Galaxy S25 Ultra. Include a small spike: rebuild only Puddlepup's head and one front paw at the proposed detail, and render a review sheet beside chatgpt/monsters/01-puddlepup/1-hero.png so I can see it working.
3. Stop there and show me the plan, the spike sheet and the budget changes. Don't change budgets or rebuild any monster until I approve.
```
