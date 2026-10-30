# The ChatGPT reference pictures: notes for Claude Code

The owner made these pictures in ChatGPT so the Art 2.0 monsters can be built at a much higher level of detail than the P1 Puddlepup pilot. They want sculpted fur in clumps and strands, real scales, feathers, stone, wood, metal and cloth, and they play on high-end phones (Galaxy S25 Ultra and newer). Read this file before building or rebuilding any monster. It replaces the optional `concept/<breed-id>/` folder of `docs/ART_2_PLAN.md` and `ART_2_PROMPTS.md`.

## 1. Where the pictures are

Each monster has a folder, `chatgpt/monsters/<NN>-<breed-id>/`, numbered in build-batch order:

| File | What it is | Use it for |
|---|---|---|
| `PROMPTS.md` | The prompts used. Its **creature card** is the written design, and **Notes for Claude Code** sits at the bottom | Parts list, materials, faces, size, attack |
| `1-hero.png` | The approved design, three-quarter view. **The design lock** | Overall look, shapes, markings, detail level |
| `2-turnaround.png` | Orthographic front, side and back views on one ground line (front, side and top for Coilfang and Aurelwyrm), plus a top, wings-spread or lid-open view for some plans. A top view sits beside the others, seen from above | Proportions and measurements; Blender reference planes |
| `3-faces.png` | 12 expressions in a 4 × 3 grid: neutral, happy, tired, stressed, sad, angry, sleepy, sick, strain, dizzy, surprised, blink | The face sheet (§2.1 and §5 of ART_2_PLAN) |
| `4-details.png` | Six close-ups plus colour swatches | Textures and materials, hands and feet, signature parts, **the detail target** |
| `5-poses.png` | Sit on the boulder, brace under the waterfall, attack, knocked back | Key poses for `sit`, `brace`, the attack clip and `hit`; the Waterfall Stand; P12 attack effects |
| `6-scale.png` | Optional: next to Puddlepup | Size, checked against the size line in `PROMPTS.md` |
| `variant-<variant-id>.png` | Front and back three-quarter views in the variant's paint | Variant colour placement and extras |
| `grown-1-hero.png` … `grown-5-poses.png`, `grown-6-compare.png` | The grown form's set (Hearthwing, Pluckrex, Paladove) | The grown look |
| `cocoon-1-hero.png`, `cocoon-2-turnaround.png` | In `27-nibblegrub/` | The cocoon model |

- The pictures are gitignored. They are reference only and never ship in the game, so don't copy them into `public/` or `src/`.
- If a picture is missing, build from the card and CONTENT, say so in the progress notes, and don't stop.
- `chatgpt/style-anchor.png` is Puddlepup's hero. It sets the shared look.
- **Read the owner's two choices at the top of `chatgpt/CHECKLIST.md` first.**
  - **Look: film or anime cel.** With the cel look, the pictures have two-tone shading and thin tinted outlines.
  - **Puddlepup: fur or skin.** With skin, Puddlepup has no fur, and its card's fur lines were overridden.

## 2. Which source wins

- **Part counts and which parts exist** (legs, toes, ears, wings, horns, tails, tentacles, segments): the card in `PROMPTS.md`. Image models miscount. If a picture disagrees with its card, follow the card and log it. The cards follow ART_2_PLAN §4 where CONTENT is older; for example, Reefclaw has six walking legs and two claws.
- **Shapes, proportions, markings, part placement, surface detail and materials:** the pictures. The hero wins when pictures disagree; the turnaround gives the measurements.
- **Exact colours:** the hex codes in `docs/CONTENT.md` §2.2 and `src/art/monster/variants.ts`. Generated pictures drift in colour, so use them to see where colours go and how materials shade, never to sample hex values. Extra hex codes in a card (dapples, horns and so on) are suggestions for parts CONTENT has no colour for.
- **Variants:** the variant picture shows where the four palette colours go and any extras. Parts it doesn't recolour keep the base breed's colours.
- **Body plan, rig, clip contract and the review loop:** `docs/ART_2_PLAN.md`. Budgets and the shader are changing too; see §3.
- **Design differences:** where a card deliberately changes CONTENT's art brief (for example, Puddlepup's damp fur coat if the owner chose fur), follow the card and pictures. Update the brief in CONTENT §2.2 to match and log it in `docs/PROGRESS.md`. Don't promote a picture's accident (an extra toe, a stray accessory) into the design.
- **Size:** the size line in `PROMPTS.md` is relative to Puddlepup, who is about 1 m tall in Blender (`unitsPerMetre` 150 in `src/art/models.ts`). `6-scale.png` confirms it.

## 3. The detail target, and what it means for the pipeline

The P1 pipeline can't reach these pictures. It uses rounded primitives, a voxel remesh, procedural paint at 1024², a flat two-tone cel ramp, and at most 12k triangles in ≤ 700 KB. Before the next monster batch:

1. Write `docs/ART_2_DETAIL.md` (Art 2.1) with numbers.
2. Prove it with a small spike: Puddlepup's head and one front paw, on a review sheet beside its `1-hero.png`.
3. Get the owner's OK before changing ART_2_PLAN's budgets or rebuilding any monster.

Measure, don't guess.

Options to evaluate:

- **High-to-low baking.** Build a high-detail version in Blender, headless:
  - sculpted fur clumps made with geometry nodes or displacement, or hair curves converted to mesh;
  - instanced scales, feathers, rivets and bricks.

  Then bake normal, AO and curvature/cavity maps onto the game mesh.
- **Silhouette fur.** Use alpha-tested fur cards or fins where the outline must look fluffy: tails, cheeks, manes, wool and down. Add a few short shells only where they clearly help. Watch overdraw on the phone.
- **Texture maps.** Use 2048² base colour, a normal map and a packed occlusion/roughness map, plus the glow map. Compress them: WebP is already in the pipeline, and KTX2/Basis is worth testing for GPU memory. Add a lower-resolution set for a Lite setting.
- **Shader.** Use a stylized lit material that uses the normal map. It must keep the anime eyes, clean colour shapes, cool-shifted shadows and the warm rim light. Two candidates:
  - a toon ramp with normal mapping and rim;
  - `MeshPhysicalMaterial`-style sheen for fur and velvet, clearcoat for shells, scales and brass, and fake translucency for fins, petals, paper and ice.

  With the film look, the pictures have no outlines, so decide whether the in-game outline stays: test thin and tinted, and none, against `1-hero.png`. With the cel look, keep the tinted outline.
- **Budgets for ART_2_PLAN §3.6.** Propose new numbers, as a starting point:
  - about 20–40k triangles for the close-up model, with a lighter LOD for the ranch crowd and Meadow Dash's four runners;
  - roughly 2–4 MB per `.glb` with compressed textures.

  Then prove 60 fps on the Galaxy S25 Ultra in battle (two monsters, Flashy effects) and in Meadow Dash. Keep the Classic SVG fallback and the Lite setting for weaker phones.
- **Face sheet.** The in-game face-sheet texture (ART_2_PLAN §2.1 and §3.6, now ≤ 512²) may need 1024² to hold the detailed eyes in `3-faces.png`. A face sheet's expressions follow its card's face notes, and some creatures show a mood with no mouth: Ashwraith's eyes, Lootlid's lid, the beaked birds.
- **Review loop.** Put the pictures beside the in-game renders on every art-review sheet. Ask the fresh-eyes reviewer two questions: "does the model reach the detail and design of the reference pictures?" and "does it still read at 64 px?".

## 4. Per monster

The bottom of each `PROMPTS.md` lists:

- the body plan;
- the size;
- the surfaces and materials;
- face notes;
- the signature detail to hit;
- the attack;
- build notes: hard parts, glow, springs and particles.
