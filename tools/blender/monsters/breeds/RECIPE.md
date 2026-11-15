# The Ultra recipe contract (Art 2.1)

`tools/blender/monsters/build_ultra.py --breed <breed>_ultra` imports `monsters.breeds.<breed>_ultra` and calls the
names below. Puddlepup (`puddlepup_ultra.py`) is the worked example of every one. Helpers for recipes:
`from lib import ultra as U` (`tools/blender/lib/ultra.py`).

Space: metres; the monster faces −Y, Z is up, +X is its left. **Size: model the breed `HEIGHT_UNITS / 150` metres
tall** (Puddlepup: 150 units, 0.986 m), so every breed stands at true relative size; the plan scales its own offsets
(hops, bobs, lifts) by the same factor.

## Required

| Name | What |
|---|---|
| `ID` | the breed id, e.g. `'tumblefox'` (bone rig `<ID>_rig`, files `<ID>.glb`) |
| `LOOK` | `f'{ID}-ultra'` (the out folder `tools/blender/out/<LOOK>/`) |
| `PLAN` | `'quadruped'` (`plans/quadruped.py`), `'biped'` (`plans/biped.py`: see *Biped plan* below), `'floater'` (`plans/floater.py`: see *Floater plan*), `'shelled'` (`plans/shelled.py`: see *Shelled plan*), `'blob'` (`plans/blob.py`: see *Blob plan*), `'construct'` (`plans/construct.py`: see *Construct plan*) or `'serpent'` (`plans/serpent.py`: see *Serpent plan*) |
| `HEIGHT_UNITS` | the breed's height in game units (CONTENT); sets the model's size (above) |
| `PALETTE` | `{'body', 'belly', 'accent', 'eye'}` hex colours (more keys allowed). The shape preview paints with it |
| `VARIANTS` | `{variant_id: paint}`, **0..N entries** (`{}` = no variant). Id `'<short>-<ID>'`, e.g. `'songheart-puddlepup'`, `'town-crier-tumblefox'`; `<short>` is the id minus `-<ID>`, hyphens kept (`town-crier`). `paint` has at least `body, belly, accent, eye`, and optionally `'props': ['bell', ...]` (props only this variant wears, below). There is no `VARIANT_ID` any more |
| `all_parts()` | the body's `lib.mesh.Part` list (voxel-united into `hi_body` and `lo_body`) |
| `build_eye(name, s, high)` | one eye lens object (`s` = +1 left, −1 right) |
| `eye_material(name, rough_pass=False)` | the eye's bake material (colour pass, or the roughness pass) |
| `blink_pivot(s)` | `(pivot, up, out)` Vectors for the blink bone `eye.L` / `eye.R` (`out` optional) |
| `paint_sources(body_srcs, fins, props=())` | write colour attributes on every source: `'paint'` (base), `'rough'` (1, roughness, clearcoat) and, for each variant, `U.variant_attr(vid, ID)` (= `'paint_<short>'`). `props` is passed only when `build_props` exists |
| `body_material(name, attr, pal, marks)` | the body sources' bake material: emission of attribute `attr` plus any per-pixel marks; `marks` is what `make_marks` returned (JSON round trip), or `None` |
| `rig_p()` | the plan's proportions and options (see *Quadruped plan options*) |

## Optional (default in brackets)

**Build**
- `carve(hi_body)`: sculpt the high source; must call `S.base_attrs(ob, co, {...})` [just `S.base_attrs`].
- `body_extras()`: closed meshes voxel-united into the body (Puddlepup's ear slabs) [none]. With extras, a proxy body without them is skinned and its weights copied.
- `zones(co, n=None)`: dict of masks. The build only reads `face`, `muzzle`, `eye_d`, `toes`, `paw` (protected from decimation) and `tail`, each only if present.
- `decimate_keep(co)`: 0..1 per `lo_body` vertex, 1 = protect from decimation [face + muzzle + eye_d<0.1 + 0.75·toes + 0.25·paw from `zones`, missing keys count 0].
- `BODY_TRIS` [46000] · `ATLAS_DENSITY` `{mesh: texel density factor}` [none].
- `flow(p, n, z=None)`: the fur's comb direction; needed by locks and cards.
- Lying locks, baked into the atlas: `head_lock_params(p, n)`, `body_lock_params(p, n)` (each optional; a layer is built only if its function exists). `LOCK_TEMPLATES` overrides `{'head': (7, 11, 3, 0.22), 'body': (5, 9, 3, 0.22)}` (nu, nv, ridges, strand).
- Fur cards: `card_params(p, n, layer)` and `CARD_LAYERS` [2; 0 = no `lo_cards`]. `CARD_SHADE` [0.88] darkens the colour they take from the skin.
- The tuft: `tuft_frames(hi_body)` [none = no `lo_tuft`]; its flat colour `tuft_colour(pal)` → hex [`colours(pal)['tuft']`]. `TUFT_SHAPE` overrides `{'template': (9, 14, 3, 0.18), 'thickness': 0.34, 'bury': 0.08}`.
- Membranes: `build_fins(high, quick)` → objects named `hi_*` / `lo_*` [none = no `lo_fins`]. The build stamps a `membrane` attribute on each, so the bake finds them by that (any names work). For the default fin weights give them `fin_part` (+1 left ear, −1 right ear, 2 tail) and `fan` (u along the membrane in `fan[:,0]`).
- Rigid props (horns, a rope, a scarf, as their own glossy meshes): `build_props(high, quick)` → `hi_<prop>*` / `lo_<prop>*` objects, baked into the same atlas (kind `prop`: the body's film material without sheen). Painted by `paint_sources(..., props=...)` (every prop, for the base and every variant). An object's prop name is its custom property `ob['prop']` if set, else its name without `hi_` / `lo_`; a listed prop `'bell'` owns `hi_bell`, `lo_bell`, `lo_bell_clapper`, ...
  - **Always worn** (not listed under any variant): joined as `lo_props`; they occlude the body in the bake (their AO is in every atlas).
  - **Variant-only** (`VARIANTS[vid]['props'] = ['bell', 'ribbon']`): joined as `lo_props_<short>` (e.g. `lo_props_town-crier`), same material and skinning; **not** body occluders (no AO collar in any atlas); listed in the sidecar as `variants[vid].meshes`. The runtime, the review viewer and the Blender sheets show it only with its variant. A prop belongs to one variant at most (give another variant its own copy, e.g. `bell_2`).
- Marks: `make_marks(hi_body)` → anything JSON-able (Puddlepup's dapples; `make_dapples` is read as an alias) [None].

**Rig weights** (each region is `(mask, {bone: weights over the masked rows})`; regions apply in order, each first clears its rows; `U.rigid(mask, bone)` and `U.chain_weights(p, points, bones, parent)` build them)
- `body_weight_regions(co, names)` → list of regions for `lo_body` [Puddlepup's: the ear flaps by `ear_zone(co)` + `ear_weights(p, u)` → `head` / `ear.<s>.1` / `ear.<s>.2`, then `zones(co)['tail']` by `tail_weights(p)`; each part only if those functions exist].
- `fin_weight_regions(co, attr, names)` (`attr(name)` reads a mesh attribute) [Puddlepup's: `fin_part` ±1 by `ear_weights(co, fan_u)`, `fin_part` 2 by `tail_weights`].
- `prop_weight_regions(co, attr, names[, mesh])` [everything rigid on `head`]; called once per props mesh (`lo_props`, each `lo_props_<short>`), with its name as the 4th argument if the hook takes one.
- `MERGE_INTO_HEAD` [`('jaw', 'eye.L', 'eye.R')`]: bones whose heat weights go to `head` (no skin moves with them).
- Mane chains and `prop.*` bones get **no heat weights** by default (theirs go to the parent, tip first), so they move only what your weight regions give them (a mane's fur via `U.chain_weights`, a prop via `U.rigid`); otherwise nearby neck skin follows the mane keys. `KEEP_HEAT = ('maneB', ...)` keeps the heat weights for the named chains.
- Cards and the tuft always copy the skin weights under their roots.

**Clips**
- `CLIP_CALM` `{clip or '*': {group: factor}}` scales a group's rotations per clip; groups `ear`, `tail`, and each mane's name.
- `calm_group(bone)` → group name or None [the bone name's first dot part when it is `ear`, `tail` or a mane name].
- `BLINK_CLOSED` [(1.0, 0.08, 1.0)]: the blink bones' scale when shut (across, up, out).

**Sidecar and review**
- `FACE_NOTE`: the sidecar's `face.note` for the runtime [a generic note: baked face, lenses, blink bones].
- `REVIEW = {'centre': (x, y, z), 'size': metres framed, 'head': ((x, y, z), size)}` [from the body's bounds]. It is also written to the sidecar (`review`) for `ultra-review.ts` and the lineup.
- `preview_colours(co, vn)` → n×3 linear RGB per body vertex, for the shape preview only [PALETTE body, belly where `zones` says `belly` / `bib`, the carved `lash` dark].

## Quadruped plan options (keys of `rig_p()`; every default is Puddlepup's)
Existing: `hip, chest, head_c, head_r, ear_base, ear_dir, ear_len, tail_base, tail_dir, tail_len, legs {FL,FR,BL,BR: (x, y, hip_z)}, knee_back, ankle_z, foot_len, leg_radius, stride`.
- `size_k` [`HEIGHT_UNITS / 150`, filled in by the build]: scales the clips' absolute offsets (hop height, body bobs, foot lifts, lunges, the sleep/sit/ko drop). Don't set it unless the model deliberately breaks the size rule.
- `tail_bones` [3]: bones in the tail chain `tail.1..N` (Tumblefox's spiral ≈ 5–6). Clips split the 3-bone motion over the chain so the total curl stays the same.
- `tail_points` [none]: `tail_bones + 1` points for a curved tail (a spiral); else a straight line `tail_base + tail_dir · tail_len`.
- `ears` [True]: False = no ear bones (their keys are skipped).
- `hooves` [False]: a short hoof bone standing on its tip (`foot_len` default 0.06·k, toe on the ground, `ankle_z` default 0.06·k), legs under the body (splay × 0.35) and a hoof flick in the swing.
- `manes` [[]]: spring chains, each `{'name': 'mane', 'parent': 'neck', 'points': [p0 … pN]}` → bones `mane.1..N` (parent `neck`, `chest` or `head`), a `springs` entry of kind `mane`, gentle keyed sway and trailing in the moving clips. Weight them with `U.chain_weights` in `body_weight_regions`.
- `props` [[]]: rigid attach bones, each `{'name': 'horns', 'parent': 'head', 'head': (x, y, z), 'tail': (x, y, z)}` → deform bone `prop.horns` (never keyed, so it moves rigidly with its parent) and a socket `socket_horns` at its tail. Skin a prop or a body region to it with `U.rigid`.

### Batch 2 options (each off by default; nothing changes for a recipe without them)
- `neck_bones` [1]: bones in the neck chain. 1 = Puddlepup's one bone `neck`; N > 1 = `neck.1..N` (Stripeneck ≈ 4–5, grown Hearthwing ≈ 3–4). The clips share the one-bone neck motion equally over the chain, so the total stays the same. With N > 1 there is no bone `neck`: parent manes and props on `neck.k` (the rig says so if you forget).
- `neck_points` [none]: `neck_bones + 1` points for a curved neck (an S rising steeply to the head). The first point should be the chest's tip, `chest + (0, −0.12·k, 0)` (else neck.1 is not joined to the chest); the head bone starts at the last point.
- `trunk` [none]: `{'points': [p0 … pN], 'parent': 'head', 'curl': 1.0, 'name': 'trunk', 'bud': {...}}` → a chain `trunk.1..N` (at least 2 bones; 4–5 for Petalphant), a `springs` entry of kind `trunk`, a `socket_trunk` at the tip and keyed curls: idle (a slow swing), idle_happy and win (raised), eat (curled in to the mouth), pet, walk, run, sleep, hit, hit_heavy, ko, dizzy, battle_idle, dash, the strafes and sidesteps, **strike** (winds back, then lashes out) and **cast** (raised high, trumpeting). `curl` scales every curl; CLIP_CALM group `trunk`. The trunk's bones keep their heat weights; for a clean bend give the trunk's skin `U.chain_weights(co[m], points, ['trunk.1', …], 'head')` in `body_weight_regions`.
  - `bud` (Petalphant's flower): `{'petals': 5, 'length': 0.05·k, 'closed': 14, 'open': 70, 'roll': 0, 'name': 'bud'}` → petal bones `bud.1..n` at the trunk's tip, each leaning `closed` degrees off the trunk's axis at rest (the bud shut) and turning `open` degrees outward in idle_happy, pet, celebrate, win (open) and hit (a quick surprised flick). Model the petals as props (`build_props`) and skin each with `U.segment_weights(co, [(bone, head, tail), …], power=8)` over `plans.quadruped.bud_petals(P)`. The petals get no heat weights (the trunk's skin never follows them). CLIP_CALM group `bud`.
- `wings` [none]: one dict for both wings, given for the **left** wing (+X; the right is mirrored) **folded**, as the reference's side views show it, which is the rest pose every unkeyed clip shows:
  `{'parent': 'chest', 'shoulder': (x, y, z), 'elbow': …, 'wrist': …, 'fingers': [tip, …], 'attach': (x, y, z), 'spread': {'elbow': …, 'wrist': …, 'fingers': [tip, …]}, 'scallop': 0.12, 'name': 'wing'}`
  → per side `wing.L.1` (shoulder → elbow), `wing.L.2` (elbow → wrist), `wing.L.f1..fK` (wrist → each finger tip), a socket `socket_wing_L` / `_R` at the wrist. `spread` is the open pose (directions only: every bone keeps its rest length); the plan works out each bone's rotation (exact at full spread) and the clips blend toward it: win (wide open, beating), cast (open, a shimmer), strike (mantled on the wind-up, a downbeat into the lunge), celebrate and hop (half open, flapping), idle_happy (a flutter), battle_idle, run, dash, dizzy, sidesteps, hit, hit_heavy and ko (a little). `attach` is where the trailing edge meets the body (the flank or hip). CLIP_CALM group `wing` scales a clip's wing keys (e.g. `{'win': {'wing': 0.7}}`).
  - Size: young Hearthwing's tiny wings ≈ 2 fingers, the grown form's big wings ≈ 3 fingers. Joints: 2 + fingers per side.
  - **Membranes**: `S.wing_membrane(name, spec, side, high, quick)` in `build_fins` builds one side's sheet (folded, faces outward, `wing_uv` = (panel, u, v) and `wing_side` ±1; the high one with ridges and veins for the normal map; panels: finger k → k+1, then the last finger → the body). Skin it in `fin_weight_regions` with `U.wing_fin_regions(co, attr, names, rig_p()['wings'])` (Coons-blended weights: exact on the bones, smooth between). `U.wing_relief(wuv, fingers)` gives the veins for the paint, `wuv[:, 2]` the distance out (an ember edge near 1). Other membranes beside the wings (ear frills) keep their own attributes: give the wing sheets the same names with zeros (e.g. `fin_part` 0) so the joined `lo_fins` keeps them; `wing_uv` / `wing_side` survive the join anyway (zero on the other sheets).
  - **Arm and finger bones** are props (tubes along `U.wing_limb_segments(spec, side)`), skinned with `U.segment_weights(co, U.wing_limb_segments(spec, side))` in `prop_weight_regions`; give each part an attribute (e.g. `part_id` ±1) so the hook can tell the sides apart.
  - The wing bones get **no heat weights** on the body (a folded wing lies against the flank and would drag its skin open).
  - The shape preview shows the folded wings and adds two views of the spread membranes.
- `body_width` [measured, then settled]: how high the spine lies when the monster is down on its side in ko. The clips stage measures a first guess on `lo_body`, then `settle_ko` poses the body at ko's last frame and corrects it until the lowest point sits where the feet stand at rest, and lifts any frame of the fall that would sink (`ko_lift`, made by the build; logged as `clips: ko lies … mm off the ground`). Set `body_width` only to override; a recipe's value is used as given (no settling). Without a body (Art 2.0) it falls back to 1.35 × the widest leg's x.
- `ko_head_lift` [0 degrees] (Nov 13): ko's neck curl is reduced by this much (the head's by 0.6×), so a long neck keeps the face out of the chest instead of folding it in (Stripeneck 30). Every other look is unchanged.
- `ko_leg_fold` [1.0]: how far ko folds the legs (0..1 of the shared fold). A coat hanging near the ground (Nimbusheep's wool, about 15 cm up) swallows fully tucked legs, so the hooves poke out of its side like beads; at about 0.4 they lie outside it, loose and bent. The ko settle (`body_width`, `ko_lift`) measures the posed body, so it follows.
- `hocks` [none]: True, or `{'knee': (dy, dz), 'hock': (dy, dz), 'paw': (dy, dz)}` as shares of the hip's height from each hind hip (−dy = forward; defaults knee (−0.16, −0.42), hock (0.14, −0.72), paw (0.08, −1.0), i.e. on the ground): a digitigrade hind leg (Cinderlynx, Starhowl): the thigh runs forward to the knee, the shin back to a raised hock, the foot bone is the long rear foot down to the paw. The walk, run, strafes and the crouch IK aim at the hock, so the paw stays planted (within a centimetre) and the hock reads as a clear angle. Front legs are unchanged.
- `strike_style` ['pounce']: same name, length and `impact` marker for every style.
  - `'pounce'`: the stretched leap: front paws reaching, hind legs pushing, the jaw open about 28° in a bite at `impact` (Puddlepup, Tumblefox, Starhowl).
  - `'charge'`: horned breeds (Rammerjack, Nimbusheep, Cobblemaw): rocks back, then drives forward low with the head below the withers so the horns lead, the front legs driving, the hind legs pushing, the chains streaming back, the jaw shut. At the drive the head also turns and rolls toward the monster's left (the three-quarter camera's side), so the near horn doesn't hide the eyes and brow. `rig_p()['charge_head_turn']` (0..1, default 1) scales that turn and roll; big ears that ride the head (Petalphant's petal ears) stand up like a sail at 1. `rig_p()['charge_windup']` (0..1, default 0, as before; Rammerjack v1.25) adds a readable wind-up: the weight rocks further back, the head comes up then tucks so the horns point ahead, and the near forehoof (FL) paws the ground. Nov 13 (Petalphant), opt-in, defaults unchanged: `rig_p()['charge_lunge']` (0..1, default 1) scales the drive (the hips' forward travel, the body's stretch, both legs' reach; 0.25 is a compact charge with all four feet planted), and `rig_p()['charge_dip']` (0..1, default 1) scales the neck's, head's and chest's dip (a dipping head swings big bent-back ears up over the back).
  - `'kick'`: Stripeneck's spinning double back-hoof kick: the body swings about 160° round on the spot (the root turns, its position never moves), pitches forward about 24° over the withers (the front legs stay upright under them, hooves planted) so the rump pops up, the hind legs fold under with the hocks bent, then both kick back and up from the raised rump at `impact` (with `hooves` the hooves flick) and the tail flicks up; nothing translates the hips away from the chest, so the body keeps its volume (Nov 7 fix: the legs used to shoot straight back at hip height and stretch the haunches). It turns back to face the opponent by the end; the face reads from the three-quarter camera at the start and the end. (Nov 13: a true double buck: the spin is 140° so both hind legs show, the front legs stand planted wide and staggered, both hind legs fold with bent hocks and snap straight back and up together at `impact`, and the neck and head yaw back over the shoulder toward the target.)
  - `'swipe'`: cats (Cinderlynx): low and coiled, the head leaning in and the mouth open; ONE forepaw (the left, the camera's side) draws out on the wind-up, then the arm straightens forward and up with the paw in line, claws leading, and rakes across the face through `impact` and down after it; the other three paws stay planted. The arm's angle is aimed from the rig's own leg at about cheek height (35–60° up, and never so high the paw can't clear the face; short legs reach the chin). `rig_p()['swipe_lift']` adds or takes away degrees. (Nov 7 fix: the paw used to fold back over the wrist and hide in the ruff, because the arm's x rotations add up down the chain.)
  - `'slam'`: Cobblemaw: rears up about 40° on the hind legs (the body pivots on the hind feet, which stay down), front paws raised and the face toward the three-quarter camera at the top, then on `impact` both front paws are driven down wide and forward, the chest drops (the body pitches about 8° onto them) and the whole body squashes, held a beat, then recovers. Every planted foot is solved in the body's frame, so the hind feet stay flat on the ground through the rear-up (they used to lift with it) and the front paws land exactly on the ground. All four feet are down by the end; root position unchanged (Nov 7 fix: the impact read as a plain level stand).
  - `'lunge'`: the default for a rig with `wings` (Hearthwing; any recipe may pick it). It draws back low, then drives forward with the head leading, the face level and the jaw open, one forepaw stepping out and the hind legs pushing (Nov 7: the pounce's long flat leap read as a belly-flop sprawl under open wings).
- `strike_trunk_raise` [0, the lash] (Nov 13, Petalphant): 0..1; any strike style: instead of winding back and lashing out, the trunk swings up and forward like the cast's and the bud opens at `impact` (scaled by the value). `hit_head` [1] (Nov 13): scales the hit's head and neck knock (Petalphant 0.45: its roll lifted the far petal ear above the crown).
- `jaw` [the head's own hinge]: `{'head': hinge, 'tail': chin tip}` (model space) puts the jaw bone at the mouth's corner for a long muzzle. A bite only shows if the jaw moves skin: leave `'jaw'` out of `MERGE_INTO_HEAD` and give the lower jaw's skin to `jaw` in `body_weight_regions` (Starhowl's muzzle is about 0.8× the cranium).
- Chain options, per mane (`manes[i]`) and on the `trunk` dict:
  - `counter` [0]: 0..1, how much of the clip's keyed head and neck rotation the chain's first bone takes back in hit, hit_heavy and ko, so a hanging beard, scarf or trunk keeps hanging when the head jerks instead of levering forward like a jaw (a chain on `head` or `jaw` counters the head and the neck, one on the neck counters the neck). 1 for a beard or a scarf.
  - `cap` [none]: the most degrees any one bone of the chain turns in any keyed clip (each axis): long manes stay calm (no locks standing up like quills in strike, no fanning in ko). 4–6 for a long many-bone mane.

Expected joints (deform bones, ≤ 64; the shipped budget counts these): Puddlepup 28; + (neck_bones − 1); + tail_bones − 3; + bones per mane; + 1 per prop; + trunk bones (+ petals); + 2 × (2 + fingers) for wings. Batch 2 estimates: **Stripeneck** ≈ 28 + 3 (neck 4) + 2 (tail 5) + 4 (brush mane chain, or 0 if baked) + 2 (ossicone props) ≈ 39; **Petalphant** ≈ 28 + 5 (trunk) + 5 (bud) ± tail ≈ 38; **Cobblemaw** ≈ 28 + 1 (tusks prop on `jaw` or `head`) ≈ 29; **Hearthwing young** ≈ 28 + 1 (tail 4) + 8 (wings, 2 fingers) + 2 (horns) ≈ 39; **Hearthwing grown** ≈ 28 + 3 (neck 4) + 3 (tail 6) + 10 (wings, 3 fingers) + 2 (horns) ≈ 46. The smoke test's rig (neck 3, trunk 4 + bud 5, wings 2 × 5) has 49.

### Shared clips (Nov 7 review)
Trunk and bud (Nov 8, Petalphant rounds 1–2): cast on a trunk rig keeps the body level and raises ONE foreleg (the other stays planted). The trunk swings up from the base (`trunk(..., raise_=True)`) and its outer half turns back down (`tip=`), so the tip points out at the target about 25° above level, at head height, with the bud fully open facing forward (`CAST_TRUNK_RAISE` 180, `CAST_TRUNK_TIP` 190, `CAST_TRUNK_REAR` 0 in the plan). Rigs without a trunk keep the old cast: a rear on both forelegs. In hit the bud stays closed (a small flick only).
Mouth (Nov 7): a recipe whose jaw is weighted (`jaw` not in `MERGE_INTO_HEAD`: Hearthwing, Starhowl) gets a happy open smile in idle_happy (about 16°) and win (16–22°); strike's 'pounce' and 'lunge' open it about 25° at impact. A merged jaw keeps every clip as it was.
Wings (Nov 7): wide open and raised at strike's impact (k reaches the recipe's `spread` pose, then a downbeat after), in cast (spread and raised with a shimmer) and through win (spread, beating, mostly raised); a startled flare in hit (half open) and flung open in hit_heavy (70%). The spread pose itself is the recipe's: widen `wings['spread']` for a wider span.

strike is a stretched pounce (crouch with the feet planted, then the body flies forward long and flat: front paws reaching, hind legs pushing out behind, the head leading with the face on the target), hit_heavy recoils the whole body back with the feet braced and the head ducking aside (never snapped up), ko topples onto the right side (belly, paws and face toward the monster's left: the review camera's three-quarter side), lies on the ground at `body_width` and curls up with every paw tucked, and win tucks the legs in the air. hit knocks the head about 30° aside, away from the three-quarter camera (toward the monster's right) and rolled with it, the muzzle level (Nov 8: turned toward the camera with the muzzle tipped up, Starhowl's read as a howl); hit_heavy shoves the whole body back and down with the head well aside; both squeeze the eyes shut at the peak (the blink bones toward the recipe's `BLINK_CLOSED`) and open them again; ko winces, then shuts them for good, lies with the legs folded loosely along the body as in sleep (no stiff pegs), and lays every mane chain down toward the ground (its `cap` and `counter` apply). The pounce's mane lift is smaller and hit_heavy's mane is half what it was. Names, lengths, markers and root speeds did not change. The Blender review's key poses now start each clip from the rest pose (as the game does); before, a clip inherited the previous one's unkeyed bones (win showed ko's lowered hips, ko hit_heavy's reared chest).

## Biped plan (`PLAN = 'biped'`, `plans/biped.py`; batch 3, Nov 12)
For monsters on two legs: Quillion, Grumblestone, Gloomgrin, Plumdrake, Pluckrex (young and grown). Everything else in this contract works the same: build, paint, membranes, props, weights, variants, glow, the Lite copy, `npm run art:shape`. Only `rig_p()` and the clips differ. The stand-in `breeds/_biped_test_ultra.py` switches every option on; it is not a breed and is never shipped or registered.

**`rig_p()`, required** (model space; limbs are given for the left side, +X, and mirrored):
- `hip` (0, y, z): the pelvis centre. `chest` (0, y, z): the top of the chest, where the neck starts. The plan splits hip → chest into `hips` 30%, `spine` 40%, `chest` 30%.
- `head_c`, `head_r`.
- `legs` = `{'hip', 'knee', 'ankle', 'toe'}`: bones `thigh.L` (parent `hips`), `shin.L`, `foot.L` (ankle → toe).
- `arms` = `{'shoulder', 'elbow', 'wrist', 'hand'}`, where `hand` is the fingertips or knuckles: bones `upperarm.L` (parent `chest`), `forearm.L`, `hand.L`.
- Model the rest pose with a small bend at the knees and elbows. The legs and arms are posed by a two-bone IK that bends in the rest pose's own plane, so IK aimed at the rest spots gives back the rest pose exactly.
- An A-pose is fine: `arm_relax` [10°] is how far out the arms hang when relaxed.

**Options** (each off by default):
- `size_k` (filled in by the build) scales the jumps: hop, celebrate, win, sidestep, and the headbutt and pounce lifts. The gait (stride, foot lift, bob, crouch) scales with the rig's own leg length.
- Neck: `neck_bones` [1], `neck_points`, `head_base` [0.6 × `head_r` below `head_c`], as the quadruped's neck chain. Pluckrex grown ≈ 2–3 bones. Grumblestone has no visible neck: put `head_base` in front of the chest, so `neck` is a short forward stub.
- `jaw` `{'head', 'tail'}` [the head's own hinge]. To let the mouth open, leave `'jaw'` out of `MERGE_INTO_HEAD` and give the lower jaw's skin to `jaw` in `body_weight_regions`. It then opens in idle_happy and win, chews in eat, yawns in idle_tired, and opens in the strikes, cast, hit and hit_heavy. The stand-in does this.
- Ears: `ear_base`, `ear_dir`, `ear_len` → `ear.{L,R}.{1,2}` (on whenever `ear_base` is given).
- Tail:
  - `tail_bones` [3 when a tail is given, else no tail], with `tail_points` or `tail_base` / `tail_dir` / `tail_len`. Clips share the motion over the chain.
  - `tail_ground` [False]: a tail that lies on the ground is never pushed down (Plumdrake).
  - `tail_puff` `{'length': m}` → a bone `tail.puff` past the tip (springs kind `puff`; it wags with a lag). Skin the puff to it (the stand-in's `body_weight_regions`).
  - When seated, the tail swings round and lifts just enough to clear the ground, worked out from the rig's own tail points.
- `wings`: the quadruped's wing dict, with `parent` default `chest` and the folded rest pose plus `spread` → `wing.L.1`, `.2`, `.f1..fK`, with `socket_wing_L` / `_R`. Gloomgrin's small wings ≈ 2 fingers; Plumdrake's big ones ≈ 3.
  - Membranes come from `S.wing_membrane` in `build_fins`, weighted with `U.wing_fin_regions`.
  - The wing bones get no heat weights.
  - The clips open them in idle_happy, hop, celebrate, cast, win and the `gust` strike; flare them in hit and hit_heavy; and keep them nearly folded otherwise.
- `capes` [[]]: chains like manes, each `{'name', 'parent': 'chest', 'points': [...], 'flare': 1.0}` → `<name>.1..N`, springs kind `cape`, no heat weights (the body's skin never follows them).
  - A cape sheet over several chains (left, centre, right) flares and parts well. Build it in `build_fins` (or as a prop), and blend each column's `U.chain_weights` across the sheet, as the stand-in's `fin_weight_regions` does.
  - The clips trail it back as the body moves (walk 6°, run 26°, dash 40°), flare it in strike (×`flare`), cast and win, keep it hanging when the body leans, and lay it out behind when seated.
- `manes` [[]]: as the quadruped's (Plumdrake's ruff), kind `mane`, at about half a cape's swing.
- `props` [[]]: as the quadruped's. Horns or a crest go on `head`; Pluckrex grown's bracers go on `forearm.L` / `forearm.R`.
- `hulk` [0..1] (Grumblestone):
  - knees always bent, a wider stance, the upper body leaning in;
  - arms hang forward and heavy (less swing), and the guard holds the fists low and forward;
  - the walk rolls (about twice the hip sway and roll) on a shorter stride.
- `squat` [0..1] (Gloomgrin):
  - the still clips (idle, look_around, battle_idle, pet, idle_happy) crouch deep (0.42 × squat × the leg's reach) with the body leaning over;
  - from 0.5 the hands rest on the ground in front of the feet in idle and look_around (the rooftop statue);
  - the moving clips crouch only a quarter as much.
  - `squat_lean` [10 × squat degrees] (Nov 13, opt-in): idle's forward lean in the statue crouch (look_around takes 0.6 of it), so short arms reach the ground (Gloomgrin 36). `squat_hand_dy` [0 m] (opt-in): the statue crouch's hands rest this much further forward (Gloomgrin 0.08: in front of the toes). Absent: as before.
- For a bulky body with big hands (Grumblestone), each off by default. The plan's hand goals in front of the body (the guard, idle_sad, idle_sick, pet, eat, sit's lap, hit, shove, cast, the strikes) are set from the shoulder and the arm's length, so on a deep belly or a broad face they land inside it:
  - `hand_clear` [[]]: ellipsoids `{'bone', 'c', 'r', 'margin', 'push'}` in the rest pose (model space), each carried by its bone as it is posed. Every hand goal is pushed out of each one to its surface grown by `margin` (radially from its centre, or along `push`, a direction in the bone's rest frame), and so is the wrist behind the goal, so the whole fist stays in front. Grumblestone: the belly on `spine` and the face on `head`, margins about the fist's half thickness, pushed straight forward (0, −1, 0) so the hulk's low guard stays low (a radial push lifted it beside the face).
  - `hand_gap` [0 m]: each hand's goal stays at least this far from the mid-line (in the chest's frame), so two big fists brought together (hands clasped, both to the mouth) touch instead of overlapping. Grumblestone 0.2.
- `lean` [0°]: an extra forward lean of the upper body in every clip (Pluckrex's carriage).
- `stride` [0.55 × leg length, less for a hulk]: the walk's step. Run, dash, the steps and the strafes scale with the leg length.
- `sit_height` [measured]: the hips' height when seated on the ground. It is measured on lo_body as the larger of the thigh's thickness and the pelvis's depth below its joint; without a body it is 0.3 × the hip height.
- `strike_style` ['punch']. Every style keeps the same name, 24 frames and `impact` at 13:
  - `'punch'`: the left fist chambers as the body coils, then drives straight out at shoulder height while the right fist guards.
  - `'swipe'`: the left claw rises high and back, then rakes down and across the face.
  - `'headbutt'`: leans back and crouches, then hops forward with the crown leading and the arms swept back (Pluckrex young).
    - `headbutt` [none] (Nov 14, Pluckrex; opt-in, absent = as before): `{'hop', 'rear', 'lean', 'reach', 'gaze', 'neck', 'head', 'lift', 'yaw', 'jaw'}`, each optional: the hop's height [0.08 × size_k m], the wind-up's lean back [18°] and the impact's lean in [42°], the hips' forward travel [0.22 × the leg], how much of the lean the head takes back [0.2], the neck's and the head's extra pitch at the impact [16°, 22°; negative lifts the face], the feet's tuck in the air [0.08 × the leg], a turn toward the monster's left [0°] (the in-game strike shot is taken from 70°), the jaw's opening [22°]; and for the wind-up, the crouch [0.14 × the leg] and the neck's, head's and jaw's turn [-10°, -12°, 0°; positive tucks the head down, a negative jaw closes a grin modelled open], and `arm_wind` [0°] more elbow bend (the arms tucked); `trail` [0 × the leg] the feet trailing back in the air (a long, flat hop).
  - `'slam'`: both fists rise overhead, then come down together to the ground in front, hips dropping, a beat held (Grumblestone). `slam` [the plan's own points] = `{'over': (x, y, z), 'ground': (x, y, z)}` places the left fist (mirrored) instead: `over` in the rest pose, carried by the chest; `ground` in model space. More keys, each optional: `lean` [34°] the body's lean at the impact, `gaze` [0.5] how much of it the head takes back (raise it so the face stays visible), `hand_up` / `hand_down` [(−30, 0, 0)] the fist's turn at the wrist overhead and on the ground (mirrored for the right), `yaw` [0°] a turn toward the monster's left through the wind-up and the impact (the in-game strike shot is taken from 70°, so Grumblestone turns its chest that way).
- `win` [the plan's pose] = `{'over': (x, y, z), 'hand': (x, y, z)}`: win's raised fists. `over` is the left fist's goal in the rest pose, carried by the chest, mirrored for the right so both go up (the plan raises the left high and the right to the side); `hand` is the turn at the wrist [(−20, 0, 0)]. Grumblestone raises both high and wide with the knuckle gems toward the camera. Grumblestone raises its fists high and wide overhead and lands them well in front of its big feet (the plan's ground point is 0.35 × the leg ahead, on its toes).
  - `'thrust'`: a fencing lunge with the tail's blade. The tail swings round under the left arm to point straight ahead while the left foot steps out and the cape flares (Quillion). `thrust_lift` [14°] raises the blade.
    - `thrust_lift` may also be a list, one value per tail bone, each applied as given (Quillion `[0, 0, -62]`): a blade that stands upright at rest is pushed down to level on its own bone while the furry tail keeps its height (one shared lift would leave it pointing up).
    - `thrust_swing` [−175°]: the tail's whole swing round the left side, shared over the chain as before. A blade that leans out at rest needs less (Quillion −160°) to point straight ahead.
- `fencer` [none] (Nov 13, Quillion): a tail-blade duellist's battle clips. A dict of tail poses, each a list of `(x, y, z)` degrees per tail bone (world-aligned, relative to the parent at rest, as the clips key them; Quillion's recipe solves them from a target direction per bone):
  - `'guard'`: battle_idle becomes en garde: side-on, the left foot forward and the right back and turned out, knees bent, the left hand forward in guard, the right hand on the hip, the blade in this pose (raised forward over the shoulder).
  - `'windup'` and `'lunge'` (the lunge defaults to the thrust pose from `thrust_lift` / `thrust_swing`): the thrust strike becomes a real lunge, fully stretched from just before `impact` to frame 18. The blade is drawn back to the windup as the body coils, then the front foot shoots out, the back leg straightens, the pelvis drops, the torso leans about 34°, the right arm swings up for balance and the blade drives into the lunge pose, with the cape flaring.
  - `'salute'`: win becomes a salute held from early on: chin up, the left hand flourished, the right hand on the hip, the blade in this pose, the cape flaring.
  - hit and hit_heavy squash and lean back with the arms flung out; hit_heavy is knocked off its feet.
  - Absent: every clip as before.
- `cape_drape` [0]: 0..1. In ko, each cape chain's first two bones turn back against the body's roll by this share, so the cape sags toward the ground instead of standing out like a board.
  - `'pounce'`: a leap from a deep crouch, the body stretched out, both claws reaching forward (Gloomgrin).
    - `pounce` [none] (Nov 13, opt-in): `{'hand': (x, y, z)}`, the left claw's goal in the rest pose, carried by the chest and mirrored for the right, so the claws spread wide and clear of a broad face (the default goal lands in front of Gloomgrin's jowls and the claws vanish in the 70° strike shot). More keys, each optional: `gaze` [0.8] how much of the leap's lean the head takes back (less pitches the head forward), `tuck` [0 m] extra lift of the feet in the air (the legs tuck up), `wings` [none] `(windup, air)` openings (else 0.05 throughout). Absent: as before (dry run: the stand-in, Quillion and Grumblestone key-identical).
  - `'charge'`: head down and low, then a hard drive with the head leading and the arms tucked (Pluckrex grown).
    - `charge` [none] (Nov 14, Pluckrex grown; opt-in, absent = as before): `{'lean', 'gaze', 'neck', 'head', 'reach', 'step', 'yaw', 'jaw'}`, each optional: the drive's lean [30°], how much of it the head takes back [0.3], the neck's and the head's extra pitch [12°, 10°; negative lifts the face], the hips' forward travel [0.3 × the leg], the front foot's step [0.3 × the leg], a turn toward the monster's left [0°], the jaw's opening [12°], `back` [0.15 × the leg] the rear foot's push back, `tail` [none] degrees the tail is lifted at the drive (negative keeps it level as the body tips), `hand` [none] the left hand's goal (x, y, z) in the rest pose, carried by the chest and mirrored (long arms tucked to the chest).
  - `'gust'`: the wings rise and spread, then one great downbeat with both palms thrust out (Plumdrake). Without wings, the palms alone.
    - `gust` [none] (Nov 13, Plumdrake; opt-in, absent = as before): `{'rear', 'toes', 'lean', 'yaw', 'gaze', 'raise', 'beat', 'sweep', 'push', 'jaw'}`, each optional. The wind-up rears back `rear` degrees [20] and up onto the toes (the heels rise `toes` × the leg's length [0]) as the wings rise `raise` degrees [35]. The impact leans in `lean` degrees [16], beats down `beat` degrees [45] and sweeps the spread wings forward `sweep` degrees [0] about the vertical (the tips ahead of the chest). The palms push out to `push` = (across × the shoulders' half width, forward and up × the arm's length) [(0.2, 0.9, 0.15)], the mouth opens `jaw` degrees [20], and the body turns `yaw` degrees toward the monster's left [0]. `wings(fr, k, flap, sweep)` gained the sweep (0 for every other caller).
- `hit_body` [none] (Nov 13, Plumdrake; opt-in): `{'squash', 'lean', 'step'}`. The hit's crouch is `squash` × the leg's length [0.04], its lean `lean` degrees [-10], and the right foot takes a half-step back of `step` × the leg's length [0] (the left a quarter of it). `'heavy'` [none] scales hit_heavy's crouch, lean and step back by that factor (a clearly bigger shove).
- `ko_wings` [none] (Nov 13, Plumdrake; opt-in): `{'flap', 'sweep'}` degrees the ko adds to both wings as it falls (a negative sweep lays them back along the body), so wings held open at rest lie down instead of the upper one standing up.
- `ko_arm` [none] (Nov 14, Pluckrex grown; opt-in): `{'upper': (x, y, z), 'fore': (x, y, z)}` degrees for the top (left) arm in ko, in place of the plan's draped arm (a long arm stood up like a periscope). `ko_jaw` [none] (opt-in): degrees the jaw turns as it falls (a grin modelled open goes slack or shut). `walk_bob` [1] (opt-in): scales the walk's body bob.
- `ko_head` [none] (Nov 14, Plumdrake; opt-in): (x, y, z) degrees the ko adds to the head as it falls, so the face isn't buried in the ground or a ruff.
- `body_width` and `ko_lift`: as the quadruped's. ko topples onto the right side, the arm underneath stretched above the head; the build measures and settles it.

**Clips:**
- **Contract:** the same 32 names, lengths, markers, faces and root-motion directions as the quadruped. Feet are planted by IK, so they don't slide (each moving clip's root speed is its stride over the stance time), and hands reach IK goals carried by the chest.
- **Ranch life:**
  - idle: breathing, a slow weight shift, a glance.
  - idle_happy: bouncing knees, arms swinging out, a smile.
  - idle_tired: slumped, then a yawn and stretch.
  - idle_sad: head down, hands together.
  - idle_sick: swaying, a hand on the belly.
  - sleep: seated, the head nodding on the chest, eyes shut.
  - eat: both hands to the mouth, chewing.
  - pet: leaning into a pat, hands clasped.
  - look_around.
  - hop: crouch, a tucked jump, a landing.
  - celebrate: two jumps with the fists up in a V.
- **Moving:**
  - walk: heel and toe-off, the hips shifting over the planted foot, rolling and turning, the chest counter-turning, the arms swinging against the legs.
  - run: a flight phase, a forward lean, elbows bent and pumping.
  - dash: lower and longer.
  - step_fwd and step_back: small guarded steps.
  - strafe_l and strafe_r: a sideways shuffle with the guard up.
  - sidestep_l and sidestep_r: a sideways hop.
- **Scenes:**
  - sit_down and sit: seated on the ground, legs forward, hands in the lap.
  - dizzy.
- **Battle:**
  - battle_idle: a staggered guard stance, bouncing.
  - strike: the styles above.
  - cast: hands rise overhead gathering, then push forward at `release`, with the wings spread.
  - shove: a two-palm push.
  - hit: head knocked aside, forearms flinching up.
  - hit_heavy: the body shoved back and down, arms flung, a step back.
  - ko: wobble, buckle, then topple onto the right side, with the legs folded and the eyes shut.
  - win: a jump with the arms up, then a spin.
- **Groups and sockets:**
  - CLIP_CALM groups: `ear`, `tail` (the puff too), each cape or mane by its name or kind (`cape`, `mane`), and `wing`.
  - Sockets: the game's seven, with `socket_paw_L` / `_R` at the hands, plus `socket_hand_L` / `_R`, `socket_foot_L` / `_R`, `socket_wing_L` / `_R` (with wings) and `socket_<prop>`.

**Joints:** the base rig has 25 deform bones: root, hips, spine, chest, neck, head, jaw, 4 ears, 6 arm bones, 6 leg bones and 2 blink bones. Add the tail (+1 for a puff), the neck beyond 1, each cape or mane chain's bones, 2 × (2 + fingers) for wings, and 1 per prop. The stand-in has 48. Estimates:

| Breed | Estimate |
|---|---|
| Quillion | ≈ 37 (tail 3, a 3 × 3 cape) |
| Grumblestone | ≈ 21–25 (no tail; ears optional) |
| Gloomgrin | ≈ 40 (tail 6, wings 2 × 4, horns) |
| Plumdrake | ≈ 47 (tail 6 + puff, wings 2 × 5, a ruff, horns) |
| Pluckrex young | ≈ 30 (tail 4, crest) |
| Pluckrex grown | ≈ 34 (neck 3, two bracers) |

**Reviewing a biped:** `npm run art:shape -- <breed>` and the full build work unchanged.

## Floater plan (`PLAN = 'floater'`, `plans/floater.py`; batch 4, Nov 12)
For monsters that hover instead of standing: Wishlume, Ashwraith, Zipwisp, Mirrorkin, Frostlance. Everything else in this contract works the same: build, paint, membranes, props, weights, variants, glow, Lite, `npm run art:shape`. The stand-in `breeds/_floater_test_ultra.py` switches every option on. It is not a breed and is never shipped or registered; `WS_FLOATER_ARMS=1` swaps its floating gloves for little arms.

**`rig_p()`, required** (model space; model the monster **hovering**, the rest pose being its idle height):
- `hip` (x, y, z): the hover point, the body's centre. The bone `hover` (parent `root`) bobs, glides, tilts, turns and squashes the whole body about it.
- `chest` (x, y, z): the top of the squash chain (a lantern's crown, a mirror's crest; a swimmer's snout).
- `body_base` [the mirror of `chest` through `hip`]: its bottom (or a swimmer's rear). The chain is `hips` (base → ⅓), `chest` (⅓ → ⅔), `head` (⅔ → top), so the face and the blink bones belong to `head`. A chain running more forward than up makes it a swimmer: it rolls rather than yaws in the spin strike, and tumbles in hit_heavy.
- `head_c`, `head_r`: the face (the jaw, the mouth socket, the review framing).

**Options** (each off by default):
- `size_k` (filled in) scales every offset: the bob, the lifts, the glide speeds.
- `jaw` `{'head', 'tail'}`: as in the other plans. Leave `'jaw'` out of `MERGE_INTO_HEAD` and weight the lower lip to it to open the mouth.
- `arms` `{'shoulder', 'elbow', 'hand', 'parent': 'chest'}`: little two-bone arms (`upperarm.L`, `forearm.L`), keyed by angle. Wishlume's paper paddles; Ashwraith's mittens peeking from the cloak.
- `hands` `{'centre', 'tip', 'parent': 'chest'}`: floating hands (`hand.L` / `.R` from the palm's centre to the fingertips), moved by offset and turned. They drift on their own and follow the body (Mirrorkin's gloves). No heat weights: skin each glove with `U.rigid`.
- `chains`: a list of `{'name', 'kind', 'parent': 'hips', 'points': [p0 … pN], 'stiff': 0..1, 'axis': 'z', 'heat', 'mirror'}` → bones `<name>.1..N`, a `springs` entry of that kind and a `socket_<name>` at the tip. `mirror: True` adds a right twin (`<name>L` / `<name>R`). Kinds:
  - **trailing** (`tassel`, `wisp`, `ribbon`, `hood`, `cape`): hang, sway with a lag down the chain, and stream back in the glides (walk 10°, run 30°, dash 45°). They whip in hits, flare in pulse and cast, and lie out in ko. A hanging one (tip below its root) swings back just enough to keep its tip on the ground whenever the body sinks, bobs or stretches below its rest hover. No heat weights unless `heat: True`.
  - `tail` (a zigzag tail; Frostlance's tail and fluke): swings round `axis`, `'z'` side to side or `'x'` up and down (a whale-like fluke), `stiff` damping it (Zipwisp's bolt ≈ 0.5). It keeps its heat weights.
  - `fin` (Frostlance's pectorals, Zipwisp's spark wings): flaps about the body's long axis.
  - `handle` (Mirrorkin's): barely moves (`stiff` 0.8).
- `props`: as in the other plans (a cap, a crest, a tusk on `head`; Ashwraith's variant lantern on `hand.L` or on a chain).
- `bob` [1.0] scales the hover bob (2.5 cm × size_k); `jitter` [0] adds a constant high-frequency shake (Zipwisp ≈ 1); `sway` [1.0] scales the idle side-to-side tilt.
- `sink` [measured]: how far the body can come down before its mass touches the ground (the lowest vertex owned by the squash chain). sit settles 0.6 of it; sleep and idle_tired / idle_sad sink 0.85 / 0.35 / 0.4.
- `strike_style` ['pulse']. Every style is 24 frames with `impact` at 13:
  - `'pulse'`: gathers small, then swells and tips at the target; the beam leaves `socket_core` (Wishlume, Mirrorkin).
  - `'ram'`: draws back, then darts in stretched, the front leading (Zipwisp; Frostlance's tusk thrust).
  - `'swipe'`: the left hand rears and sweeps across (floating hands or arms; Mirrorkin up close).
  - `'gust'`: breathes in stretched, then blows with the mouth wide (Frostlance's Snowflake Puff).
  - `'spin'`: one full turn while lunging (Zipwisp's dance, Frostlance's spiral).
  - `'lash'`: hands raised, then the wisps and tails whip forward over the body (Ashwraith).
- `pulse_tilt` [0°]: how far 'pulse' tips to catch the light first (Mirrorkin ≈ 15–20).
- `body_width`, `ko_lift`: as in the other plans. ko drifts down and settles on its right side, measured and settled by the build.
- Nov 14 (Wishlume), each opt-in (absent = as before; the stand-in's clips are key-identical):
  - `pulse_lean` [0°] more forward tip at the pulse's burst; `pulse_stretch` [1] scales its tall stretch (0.4: an even swell, not an egg); `pulse_yaw` [0°] turns it toward its left at the burst, so the face shows in the in-game strike shot (70°).
  - `pulse_push` [0 m] more forward travel at the burst (Wishlume 0.07 with `pulse_lean` −26: it leans back about 12° and pushes its lower front at the target). `glide_lean` [1] scales the glides' lean (walk, run, dash, the guarded steps).
  - `ko_ground` [the rest pose's lowest point] (read by build_ultra's ko settle): where the body's lowest point lies in ko. A floater whose lo_body hovers at rest (its tassel a prop) needs it (Wishlume 0.012), or ko lies in the air.
  - `ko_arm` [none] (x, y, z) degrees added to the little arm underneath (`upperarm.R`) as it falls, so the body doesn't lie propped on it (Wishlume (0, 120, 0): the paddle swings up beside the crown). `ko_chain_hang` [0] (0..1) turns hanging trailing chains back against the roll, so a tassel droops to the ground instead of standing out sideways. `hit_heavy_chain_hang` [0] (0..1) does the same against hit_heavy's tip and tilt and halves the chains' forward fling, so a tassel lags and droops instead of standing out along the body's axis (Wishlume 0.85).
  - `arms` may name its `parent` bone as documented (it used to crash the mirror); Wishlume's paddles ride `head`, as does its tassel chain (`'parent': 'head'`), because its paper is one rigid lantern on `head` (the lenses ride the head's blink bones).
- Nov 14 (Ashwraith), opt-in (absent = as before; the stand-in, with gloves and with arms, and Wishlume are key-identical): `arm_pitch` [0] (0..1) turns that share of the little arms' raise into a pitch up (−x) instead of the −y turn, which only rolls an arm that reaches forward out of a cloak. Put the shoulder above and behind the hand (Ashwraith: under the collar), so the pitch carries the hand up and forward in front of the body (1: the battle guard lifts the mittens about 9 cm, the lash strike about 13 cm).
  - `clip_bones` [none] `{clip: {bone: [(t0, t1, (x, y, z)[, (dx, dy, dz)])]}}`: adds each rotation (degrees) and offset (metres × size_k) to that clip's own pose in a smooth bump from t0 to t1 (0..1 of the clip; the bone is keyed 0 outside it). CLIP_CALM still scales chain bones. Ashwraith: the lash's coil and whip of its front streamers, the strike's turn toward the 70° camera, the win's higher rise and the cloth's flare.
- Nov 14 (Zipwisp), each opt-in (absent = as before; the stand-in, with the pulse and with the ram strike, and Wishlume are key-identical): `ko_bones`, `hit_bones`, `hit_heavy_bones`, `strike_bones` and `win_bones`, each `{bone: (x, y, z) degrees}`, added with ko's fall, the hit's and hit_heavy's knock, the strike's drive (any style) and win's jump and spin. A bone may be `hover` (Zipwisp: ko rolls only about 45 degrees, hit_heavy tips back about 23 instead of 45 and turns less away, the ram leans in 20). Zipwisp also uses them for the wings (folded up and drooped in ko, swept flat back in the dart, flared up in win) and the bolt tail (lifted in the knocks, trailing straight behind in the dart). `strike_windup_bones` (same form) is added with the strike's wind-up (Zipwisp tilts back and spreads its wings before the dart). `ko_scale` and `win_scale`, each `{bone: s}`, scale a bone toward s as ko falls or while win is in the air. Zipwisp's sparks ride a `prop.sparks` bone from the ball's centre: they fizzle to 0.02 in ko and burst to 1.3 in win. `ram_yaw` [0] turns the ram strike that many degrees toward the monster's left as it darts, so the face shows in the in-game strike shot (Zipwisp 30). A tuft that stands up on the crown is best a 2-bone `tail`-kind chain (a trailing kind would tip it forward in the glides); list the real tail first, as `socket_tail` takes the first tail-kind chain.
- Nov 14 (Frostlance), opt-in (absent = as before; key-identical for every other look): `ram_roll` [0] degrees of roll about the body's long axis while the ram strike darts, easing over `ram_roll_span` [(0.3, 0.52)] of the clip, so a full turn (360) is upright again by the impact (Frostlance's spiralling tusk thrust).
- Nov 14 (Mirrorkin), opt-in (absent = as before; the stand-in with gloves and with arms, Wishlume, Ashwraith and Zipwisp are key-identical): `strike_hold` [0] (0..1 of the clip) holds the strike's drive flat at its peak round `impact` for that long (any style), and the pulse's swell too, so a beam has a clear, still source (Mirrorkin 0.1: about 2.5 frames). `plans.floater.held_pulse(t, start, end, hold)` is the held bump.

**Clips:** the same 32 names, lengths, markers and faces as every plan, played the floater way.
- **Ranch life:**
  - idle: bobbing and swaying, a glance, the chains trailing with a lag.
  - idle_happy: bouncy, stretching and squashing.
  - idle_tired: sinks, droops and yawns.
  - idle_sad: low and tipped down.
  - idle_sick: wobbling and drifting.
  - sleep: sinks almost to the ground, squashed, eyes shut. Dimming a glow is the runtime's job (its face hint is `sleepy`).
  - eat: dips and chomps.
  - pet: leans into the pat.
  - look_around, hop (a float up), celebrate (two bounces and a twirl).
- **Moving:**
  - walk, run and dash are glides, leaning in with the chains streaming back.
  - step_fwd and step_back: guarded glides.
  - strafe_l and strafe_r: a sideways glide, banked.
  - sidestep_l and sidestep_r: a quick banked dart.
  - The root speeds are 0.25 / 0.8 / 1.15 / 0.25 / 0.2 / 0.25 m/s × size_k; the markers sit at the bob's troughs.
- **Scenes:** sit_down and sit settle low; dizzy circles and wobbles.
- **Battle:** battle_idle is a ready hover with the hands up. Then strike, cast (rises with the hands up, then bursts at `release`), shove (a body bump), hit (knocked back in the air), hit_heavy (flung back and tumbling), ko, and win (a jump and a twirl).
- **Groups and sockets:**
  - CLIP_CALM groups: each chain by its name or kind, `hand`, `arm`.
  - Sockets: the game's seven (`socket_paw_L` / `_R` at the hands or arms, else at the body's sides), plus `socket_core` (the hover point), `socket_hand_L` / `_R`, `socket_<chain>` and `socket_<prop>`.

**Joints:** the base rig has 8 (root, hover, hips, chest, head, jaw, 2 blink bones) + 4 for arms or 2 for hands + each chain's bones + props. The stand-in has 25. Estimates:

| Breed | Estimate |
|---|---|
| Wishlume | ≈ 17 (arms 4, a 3-bone tassel, a cap prop) |
| Ashwraith | 46 (arms 4, a hood tip 3, 8 wisp chains × 3, 2 lash streamers × 3, the lantern prop) |
| Zipwisp | ≈ 16 (spark wings 2, a 3-bone bolt tail, a 2-bone tuft) |
| Mirrorkin | ≈ 22 (hands 2, a handle 1–2, two 3–4-bone cloak panels, a crest prop) |
| Frostlance | ≈ 17 (a 3-bone tail with its fluke, 2 fins, a tusk prop) |

## Shelled plan (`PLAN = 'shelled'`, `plans/shelled.py`; batch 5, Nov 14)
For monsters that carry a rigid shell on short legs: Moatshell (a tortoise) and Reefclaw (the crab option). Everything else in this contract works the same. The stand-in `breeds/_shelled_test_ultra.py` switches every tortoise option on; `WS_SHELLED_CRAB=1` makes it the crab instead. It is not a breed and is never shipped or registered. The shelled and blob plans share their posing machinery in `plans/kin.py` (the biped's FK and two-bone IK, the per-clip knobs, the ko's lie-down); the biped keeps its own copy, so no existing look changes.

**`rig_p()`, required** (model it standing):
- `hip` (x, y, z): the shell's centre. The bone `hips` (parent `root`) carries the shell and never bends or squashes: give every shell vertex, and anything fixed on it, `U.rigid(…, 'hips')`.
- `chest` (x, y, z): the front opening, where the neck and the front legs come out. `chest` (parent `hips`) slides back into the shell when it tucks; let the neck's root skin and the soft front body blend onto it.
- `head_c`, `head_r`: the face.
- `legs`: the left legs, front to back, `[{'hip', 'knee', 'ankle', 'toe'?, 'parent': 'hips'}, …]`, mirrored to the right → `leg<i>.L` / `.R`, `shin<i>`, `foot<i>` (with a `toe`). Give the front legs `'parent': 'chest'`, so they tuck with it. Every gait plants the feet by IK, so no foot slides at the root speeds. The knees bend in their rest plane, so model them a little bent (outward for pillar legs, up for a crab's). Two legs a side walk in diagonal pairs; three walk in alternating tripods.

**Options** (each off by default):
- `neck` [none]: `[p0 … pN]` → `neck.1..N`, from the opening to the head. Without one, the head sits on `chest` (a crab's face on its shell) and turns `head_turn` [0.3] as far.
- `head_base`, `head_tip` [from `head_c`]: the head bone.
- `jaw` `{'head', 'tail'}`. Heat weights leak the jaw over the snout, so put `'jaw'` in `MERGE_INTO_HEAD`, set `'jaw_open': True` in `rig_p()`, and weight the lower lip to `jaw` with `U.rigid`.
- `shell_top` [`hip` + 0.3 m × size_k]: the shell's top, for `socket_back` and `socket_shell` (a turret's volley starts there).
- `claws` (the crab option): one dict, mirrored, or `{'L': {…}, 'R': {…}}` for a big and a small one. Keys: `{'shoulder', 'elbow', 'wrist', 'tip', 'finger': (head, tail), 'open_axis'?}`. Bones (parent `chest`):
  - `arm`, `forearm`, `claw` (the hand and its fixed finger);
  - `pincer` (the moving finger). It opens about `open_axis` (model space; by default it lifts its tip; `(1, 0, 0)` opens a lower finger downward).
  - `big_claw` [the longer one]: the side the 'claw' strike swings.
  - Claws get no heat weights (`claw_heat: True` keeps them): skin each segment with `U.segment_weights`.
- `stalks` `{'base', 'mid', 'tip', 'visor'?: (head, tail)}` (the left one; mirrored) → `stalkL.1`, `.2` and `visor.L` (and the right ones).
  - Set `EYE_PARENTS = {'L': 'stalkL.2', 'R': 'stalkR.2'}` in the recipe (a build option, below), so the blink bones ride the stalks.
  - The stalks fold back onto the shell when it tucks (brace, hit, sleep, ko), and lean, look and sway in every clip. Each is a `springs` entry of kind `stalk`.
  - No heat weights: skin them with `U.chain_weights` and the visors with `U.rigid`.
- `rigid_legs` [on with claws]: the legs get no heat weights. Skin them with `U.segment_weights`, since a shell's legs bend only at the joints.
- `tail` [none]: points → `tail.1..N` (springs kind `tail`). It lifts by itself when the shell sinks or tips back.
- `chains`: `[{'name', 'kind', 'parent': 'hips', 'points', 'stiff', 'heat', 'mirror', 'spring': True}]` → bones `<name>.1..N`, a `springs` entry and `socket_<name>`. The props are made before the chains, so a flag can fly from a pole prop (`'parent': 'prop.pole'`). Kinds:
  - `flag`: flutters about its pole; moving, it swings toward the back.
  - `tassel` and `cloth`: hang and sway, and trail back. One hanging from `hips` swings back just enough to stay off the ground when the shell sinks or tips.
  - `antenna`, `tail`.
  - No heat weights for flag, tassel or cloth unless `heat: True`.
- `props` [parent `hips`]: `prop.<name>` (a tower, a pole).
- `tuck` [1; 0.35 with claws]: how far the head and the front body pull in, × `tuck_depth` [0.75 × the neck's length + 0.3 × `head_r`]. The feet draw in under the shell too.
- `sink` [measured: the lowest vertex owned by `hips` or `chest`]: the room under the shell. Sit and sleep lower it onto its belly.
- `stride` [1] scales the gait strides (the root speeds follow).
- `hop` [1] scales the jump in hop, celebrate and win (a heavy breed 0.5–0.7).
- `strike_style` ['bash'; 'claw' with claws]. Every style is 24 frames with `impact` at 13:
  - `'bash'`: draws back low with the head in, then rams the shell's front at the target, its feet skidding (Shell Bump).
  - `'bite'`: coils the neck with the mouth opening wide, then shoots the head out and snaps shut on the impact (Drawbridge Snap).
  - `'launch'`: braces wide and low with the head half in and the shell tipped back `launch_pitch` [−6°]. The volley leaves `socket_shell` on the impact, and the recoil rocks the shell (Turret Toss).
  - `'claw'`: the big claw rears up and out, then sweeps across in front at the target, the body turning into it (Sideways Slash; Reefclaw's attack picture).
  - `'pinch'`: both claws spread with the pincers open, then lunge in together and snap shut on the impact (Pincer Pinch, Tidebreaker Clamp).
- `cast_style` ['brace'; 'raise' with claws]: `'brace'` is the launch over the cast's 36 frames (the shot at `release`, 20); `'raise'` lifts the claws (or the head) high, then thrusts them at the target at `release`.
- `strike_yaw` [0°]: turns the strike, shove and launch toward the monster's left as they drive, so the face shows in the in-game strike shot (about 70°; the battle and three-quarter camera is about 35°).
- `claw_keep_up` [0] (Nov 15, Reefclaw; opt-in, absent = as before): 0..1, the share of each claw's raise that its forearm takes back, so a claw that stands upright at rest lifts with the arm instead of tipping over the face (guard, strike, cast, win, celebrate, hit). Reefclaw 0.75.
- `shell_turn` [False] (Nov 15, Reefclaw; opt-in, absent = as before): `body()` really turns the shell by each clip's pitch, roll and yaw. Without it no clip turns the shell (the rotation sat after a `return`, so it never ran): hit and hit_heavy read as idle, the strike has no twist, idle doesn't rock. The floor clearance already assumed the turn. Reefclaw True; worth turning on for Moatshell too.
- `ko_style` ['roll']:
  - `'roll'` falls `ko_roll` [80°] onto the right side; about 160–175 lands it on its back, legs up, with the stalks folded flat so they don't prop it.
  - `'tuck'` pulls everything in and drops the shell onto its belly.
  - `body_width` and `ko_lift` work as in the other plans; the build's settle is exact for every style.
  - `ko_settle_meshes` [`('lo_body',)`] (Nov 15, Reefclaw; opt-in, read by build_ultra's settle, any plan): the game meshes the ko settle measures. A rig whose legs and claws are props needs `('lo_body', 'lo_props', 'lo_eyes')`: otherwise ko lies at the shell's rest height (hovering on its legs) and the roll drives the prop legs and claws through the floor; with it the fall pivots over them (Reefclaw lifts 7 cm mid-roll).
- The per-clip knobs, with the same meaning as the floater's: `clip_bones`, `ko_bones`, `ko_scale`, `hit_bones`, `hit_heavy_bones`, `strike_bones`, `strike_windup_bones`, `win_bones`, `win_scale`, `ko_chain_hang`, `hit_heavy_chain_hang`, and the build's `ko_ground`. IK-planted leg bones ignore rotations given to them; the knobs suit the shell, the neck, the claws, the stalks, the chains and the props.

**Build option** (Nov 14, opt-in; absent = as before): `EYE_PARENTS = {'L': bone, 'R': bone}` hangs the blink bones `eye.L` / `eye.R` on those bones instead of `head`.

**Clips:** the same 32 names, lengths, markers and faces as every plan.
- `body()` keeps every shell vertex at least 3 mm off the ground whatever a clip asks (a tip back raises the shell by just enough).
- **Ranch life:**
  - idle: breathing and rocking, with a glance; a crab's stalks glance on their own.
  - idle_happy: bobbing, the head up, the claws clacking.
  - idle_tired (a yawn), idle_sad (half tucked, the head low) and idle_sick (a wobble and a shiver).
  - sleep: the shell on its belly, everything tucked, the eyes shut.
  - eat: the head dips to the ground; a crab's small claw feeds the mouth.
  - pet, look_around (a crab's stalks look one at a time), hop, celebrate.
- **Moving:** walk, run, dash, step_fwd, step_back and strafe are IK gaits. The root speeds come from the strides: stride ÷ (planted share × cycle). Sidestep is a quick sideways hop.
- **Scenes:** sit_down and sit lower the shell onto its belly with the legs splaying; dizzy circles.
- **Battle:** battle_idle is a ready stance (a crab's claws up, clacking). Then strike, cast, shove (a shell bump), hit (knocked back, half tucked), hit_heavy (flipped up and back, the legs flailing), ko and win (a hop, then proud, the claws up).
- **Groups and sockets:**
  - CLIP_CALM groups: `tail`, `neck`, `stalk`, each chain by its name or kind, `claw` and `leg`.
  - Sockets: the game's seven (`socket_paw_L` / `_R` at the claws' tips with claws, else the front feet), plus `socket_shell`, `socket_claw_L` / `_R`, `socket_<chain>` and `socket_<prop>`.

**Joints:** the base rig has 7 (root, hips, chest, head, jaw, 2 blink bones). Add the neck's bones, 2–3 per leg, 4 per claw, 2–3 per stalk, the tail, the chains and the props. The stand-in has 30 as a tortoise and 38 as a crab. Estimates:

| Breed | Estimate |
|---|---|
| Moatshell | ≈ 28 (neck 2, 4 legs × 3, a 2-bone tail, the tower and pole props, a 3-bone flag) |
| Reefclaw | ≈ 33 (no neck; 6 legs × 2, 2 claws × 4, 2 stalks × 2 + 2 visors) |

**Per breed:**
- **Moatshell:**
  - Pillar legs with feet. `tuck` 1; `hop` ≈ 0.5.
  - strike `'bash'` (Shell Bump); cast `'brace'` (its tower fires Turret Toss, Siege Volley, Catapult Barrage and Arrow Slit Shot from `socket_shell`; `SOCKET_POINTS` can move it to the tower's top); `strike_yaw` ≈ 20.
  - ko `'roll'` at 85–90. On its back, the tower would prop it up, as the stand-in shows.
  - Size (decided Nov 14, as for Frostlance: FOR-CLAUDE-CODE §2, the size line sets the size and the pictures set the proportions): the height from the card (`HEIGHT_UNITS` 165, the flag included), the length from the pictures, about 1.2 m. The card's "1.5 × Puddlepup's length" (≈ 2.2 m) does not apply.
- **Reefclaw:**
  - `claws` per side, with `big_claw` `'R'` (its pictures put the big coral claw on its right). The coral branches are part of `claw.R`'s rigid mesh (watch the triangles).
  - Six legs with `rigid_legs`; `stalks` with visors and `EYE_PARENTS`. Barnacle pauldrons are rigid on `hips` (no bones).
  - strike `'claw'` (the attack picture's sweep) or `'pinch'`; cast `'raise'`; ko `'roll'` at 100–160.

## Blob plan (`PLAN = 'blob'`, `plans/blob.py`; batch 5, Nov 14)
For soft, squashy monsters that sit on the ground: Bloatoad (a toad on four short legs) and Scrollopus (an octopus). The stand-in `breeds/_blob_test_ultra.py` switches every toad option on; `WS_BLOB_OCTO=1` makes it the octopus instead. It is not a breed and is never shipped or registered.

**`rig_p()`, required** (model it sitting):
- `hip` (x, y, z): the body's centre. The bone `body` (parent `root`) carries everything: it leans, turns, hops and falls about this point, but never squashes. Legs and tentacles hang from it.
- `chest` (x, y, z): the top of the squash chain (the crown of the head-body).
- `body_base` [straight under `hip`, 2 cm up]: its bottom. The squash chain is `hips` (base → ⅓), `chest` (⅓ → `head_split` [⅔]) and `head` (`head_split` → top). It squashes and stretches about the bottom, so the bottom stays on the ground. The face and the blink bones belong to `head`: set `head_split` so the face sits above it (Bloatoad ≈ 0.6, Scrollopus 0.4).
- `head_c`, `head_r`: the face.

**Options** (each off by default):
- `jaw`: as the shelled plan's (`'jaw'` in `MERGE_INTO_HEAD`, `'jaw_open': True`, the lower lip on `jaw` by `U.rigid`).
- `sac` `{'head', 'tail', 'parent': 'head', 'max': 1.8}`: a throat sac (bone `sac`, from where it hangs to its far side). It scales up to `max` when it balloons: idle_happy, pet, win, cast 'inflate'; a slow bubble in sleep; a pulse in idle. Skin it with a smooth falloff, e.g. `{sac: w, head: 1 − w}`; it gets no heat weights. `socket_sac` sits at its far side.
- `tongue` `{'points': [p0 … pN] inside the mouth, 'parent': 'jaw', 'reach': 0.6 m × size_k}` → `tongue.1..N`, unconnected:
  - The bones after the first slide out along the tongue as it lashes, stretching the skin between them, and level out against the jaw's opening.
  - Model the tongue as a prop mesh (`build_props`) and skin it with `U.chain_weights` over the tongue's points in `prop_weight_regions` (parent `jaw`). Inside the body it would vanish into the voxel union.
  - `socket_tongue` sits at its tip, where a lash lands. `tongue_aim` [4°] tips the lash down.
- `legs`: as the shelled plan's (parent `body`), planted by IK. Walk and the steps crawl in diagonal pairs; run and dash hop with every foot together.
- `tentacles`: `[{'name', 'points', 'parent': 'body', 'role', 'mirror'}]` → `<name>.1..N` (mirror: `<name>L` / `<name>R`), CLIP_CALM kind `tentacle`, `socket_<name>` at each tip. They get no heat weights (`tentacle_heat: True` keeps them): neighbours would share weights, so skin each with `U.chain_weights`. Roles:
  - `'ground'`: curled on the ground and carrying it. They breathe (curling up a little, each in its own time) and lift just enough whenever the body's lean or drop would push them under. Without legs they shuffle: each lifts and reaches toward the travel in its turn round the body.
    - `ground_lift_exact` [False] (Nov 15, Scrollopus; opt-in): that lift turns the root by the angle that really raises each point lying on the ground (from its horizontal and vertical offset to the root). The default `asin(need / distance)` gives only about 40% of it when the root sits high above a steep descent, and the runs sank about 1 cm into the floor in idle_tired, idle_sad, pet, dizzy and win.
  - `'hold'`: raised, holding a prop (a scroll, a book: `props` with `'parent': '<name>.N'`). They gesture.
  - `'free'`: raised and empty, with springs (`'spring': True` on any tentacle adds one).
- `chains`: `tassel` (a cap's tassel on `prop.cap`), `frill`, `tail`, `antenna`, as the shelled plan's.
- `props` [parent `head`]: a cap, spectacles, or a held scroll or quill on a tentacle's tip bone. They are made after the tentacles and before the chains.
- `hop` [1], `stride` [1]: as the shelled plan's.
- `strike_style` ['tongue' with a tongue, else 'slap' with tentacles, else 'belly']. Every style is 24 frames with `impact` at 13:
  - `'tongue'`: rears back with the sac filling and the mouth opening, then the tongue lashes out, fully out from 0.48 to 0.62 of the clip, and snaps back (Tongue Lash; Bloatoad's attack picture).
  - `'belly'`: crouches wide, hops at the target and lands belly first on the impact, squashed flat (Belly Bounce, Bog Slam).
  - `'slap'`: the `slap_arm` tentacle rears up and out, then whips down across in front (Tentacle Swat).
  - `'ink'`: the `ink_arm` tentacle rises beside the head with the body drawing in, then points at the target. The ink leaves `socket_<ink_arm>` on the impact as the body puffs (Ink Flick; Scrollopus's attack picture).
  - `slap_arm` / `ink_arm` [the first free tentacle, else hold, else ground, on its left] name the tentacle. The ink arm should rest low or free, since it is raised about 80°.
  - `ink_lift` [80°], `ink_turn` [12°] (swung toward the front after the lift) and `ink_curl` [(-20, 50)] (the curl with the rise, and at the aim) (Nov 15, Scrollopus; opt-in, absent = as before). All 0 hands the arm to the recipe: Scrollopus poses its ink arm (rooted at its left-back) through `strike_windup_bones` / `strike_bones`, the keyed rotations solved from target joint points (`scrollopus_ultra.chain_euler`), which lifts it from beyond its fused root instead of tearing the skirt.
- `cast_style` ['raise' with tentacles, else 'inflate']: `'inflate'` swells with the sac at its fullest by `release` (20), then lets it all out at once (Croak Quake, Balloon Belly); `'raise'` rises tall with the tentacles and what they hold raised, then thrusts them at the target at `release` (a lecture).
- `strike_yaw` [0°]: as the shelled plan's.
- `strike_scale` [none] (Nov 15, Bloatoad; opt-in, absent = as before): `{bone: s}` scales each bone toward s with the strike's drive (any style), like `win_scale` with the jump. Bloatoad `{'sac': 2.2}`: the sac stays full as the tongue lashes (its attack picture; the 'tongue' style fills it only in the wind-up). `strike_windup_scale` (same form, Nov 15, opt-in) does the same with the wind-up (Bloatoad `{'sac': 1.5}`).
- `hop_stretch` [1] (Nov 15, Bloatoad; opt-in, absent = as before): scales the tall stretch in the air of every hop (hop, celebrate, win, the sidesteps). Bloatoad 0.35: a squat body stretched read as a bowling pin.
- `hit_squash` [0 = off] (Nov 15, Bloatoad; opt-in, absent = as before): the light hit squashes the body wide and low by this share (about z, peaking at 0.3 of the clip, a small rebound after) instead of the front-to-back knock, whose kept volume grew a squat body 7% taller. Bloatoad 0.13.
- `sidestep_stretch` [1] (Nov 15, Bloatoad; opt-in): scales the sidesteps' airborne stretch, lean-back, roll and foot tuck. Bloatoad 0.5.
- `hit_heavy_pitch`, `hit_heavy_lift`, `hit_heavy_stretch` [1 each] (Nov 15, Bloatoad; opt-in): scale the heavy hit's backward pitch, its rise and its rebound stretch. Bloatoad 0.6, 0.3, 0: the belly pushed through the planted arms' roots and the shoulder's warts smeared into teardrops.
- `ko_style` ['back']:
  - `'back'` falls `ko_pitch` [95°] onto its back: belly up, legs splayed and kicking, a tail folded along the back.
  - `'front'` falls onto its face; `'roll'` falls `ko_roll` [80°] onto its side.
  - Every tentacle is laid out level and away from the body, so none props it up. The sac goes flat and the tongue lolls.
  - `body_width` and `ko_lift`: as the other plans.
- The per-clip knobs: as the shelled plan's.

**Clips:** the same 32 names, lengths, markers and faces as every plan, played the squishy way: every clip breathes, squashes and stretches about the bottom.
- `body()` keeps the body's own vertices (the squash chain, the jaw, the sac and the roots of the chains on it) at least 3 mm off the ground.
- A tail lifts by itself as the body leans or sinks.
- **Ranch life:**
  - idle: breathing, the sac pulsing, the tentacles curling.
  - idle_happy: the sac balloons and goes down; bouncy.
  - idle_tired (a yawn, the tongue peeking out), idle_sad and idle_sick.
  - sleep: squashed low, a slow snoring bubble from the sac.
  - eat: the tongue flicks to the ground twice, or a holding tentacle feeds the mouth.
  - pet, look_around, hop, celebrate.
- **Moving:** gaits as above; sidestep is a quick banked hop.
- **Scenes:** sit_down and sit settle low and wide; dizzy circles with the tongue out.
- **Battle:** battle_idle is ready and bouncing with the holding tentacles up. Then strike, cast, shove (a body bump), hit (squashed front to back, the tentacles flung), hit_heavy (knocked onto its rump), ko and win (a hop, then the sac ballooning and the tentacles waving).
- **Groups and sockets:**
  - CLIP_CALM groups: each tentacle (kind `tentacle`), `tongue`, each chain by its name or kind, and `leg`.
  - Sockets: the game's seven (`socket_paw_L` / `_R` at the front feet, else the foremost tentacle tip on that side), plus `socket_core`, `socket_sac`, `socket_tongue`, `socket_<tentacle>`, `socket_<chain>` and `socket_<prop>`.

**Joints:** the base rig has 8 (root, body, hips, chest, head, jaw, 2 blink bones). Add the sac (1), the tongue's bones, 2–3 per leg, each tentacle's bones, the chains and the props. The stand-in has 26 as a toad and 38 as an octopus. Estimates:

| Breed | Estimate |
|---|---|
| Bloatoad | ≈ 24 (sac 1, a 3-bone tongue, 4 legs × 3) |
| Scrollopus | ≈ 39 (8 tentacles × 3, cap, spectacles, scroll, quill and book props, a 2-bone cap tassel); ≈ 47 with 4-bone tentacles for rounder curls |

**Per breed:**
- **Bloatoad:**
  - Four legs (the front short, the hind folded like a frog's), a `sac` with `max` ≈ 2 (its pictures balloon it bigger than the head), a 3-bone tongue prop.
  - strike `'tongue'` (Tongue Lash, the attack picture) or `'belly'` (Belly Bounce); cast `'inflate'` (Croak Quake, Balloon Belly); ko `'back'` (its hit picture).
  - `hop` ≈ 0.6; `head_split` ≈ 0.6. The crown bumps are part of the head's mesh.
  - Built (Nov 15): one weight region over the whole skin (`bloatoad_skin.weight_regions`: the squash chain in bands along BASE → TOP, each leg by its distance from its bones, the jaw, the sac), no heat weights. A throat region over heat weights couldn't match them at its edge, and hit_heavy tore the throat. The sac's weight peaks in the throat's middle (a flat core ballooned into a drawer's front, not a bubble). Round 3: the game mesh is cut along the slit's floor (`bloatoad_carve.cut_mouth`, before the decimation; each side stored as the lo_body attribute `jside`, which the weights read) and a matte mouth bag prop (an open cup, faces inward, roof on `head`, floor on `jaw`) sits behind the lips, so the lips part cleanly over a dark rose inside with the tongue on its bed. Round 2: the mouth is a real slit, a V 3.4 cm deep carved into the high source and the game mesh alike, its walls painted the mouth's dark inside and the jaw's weight split at its floor, so an opening jaw shows a dark mouth and only the deep floor stretches (a painted line on smooth skin stretched into streaks). The sac's weights put the throat on a sphere round the sac bone at full scale, `w = (SAC_R / d − 1) / (max − 1)`, so it balloons into a round bubble. The body's volumes meet in creases blended by Laplacian smoothing along them (pushing along the normals folded the skin over itself). The eyes are parts: an eyeball 3 mm inside the lens (the closed lid) and an egg for the heavy upper lid crossing the lens at the lash line.
  - Polish (Nov 15): the mouth is cut after the decimation, along the line itself (`bloatoad_carve.cut_mouth`, called from `bloatoad_props.build`: every edge crossing the line is split there or its near end moved onto it, so each lip ends in one smooth curve; cut before the decimation, the decimation's smoothing pass pulled the lips apart into a beaded zipper), and the slit is only a 4 mm crease painted one dark line (a 12 mm V let the bake's rays cross from lip to lip). The mouth's inside is a pocket grown from the cut's own edges (`bloatoad_props._bag`): ring 0 is the lip edge itself, deeper rings go in and up into the roof or down into the floor, a back wall closes it, and each vertex copies the weights of its two lip vertices (`prop_weight_regions` reads lo_body's groups), so no opening shows the background (a separate cup left grey wedges at the corners and a band in ko). The film keeps every body and prop texel at roughness ≥ 0.3, caps the coat at 0.5 and caps lit brightness, so a real highlight flattens on the bright peach: the sac and the tongue carry a painted soft wet sheen. Party confetti sits only on the chosen raised domes (no 1.8× discs, no small-wart dots: a few vertices across they painted as diamonds). No rosette reaches the peach (one across the arm-belly crease smeared into dark stubble). A trap for every plan: `lib/anim.py` `ClipBuilder.scale` maps a world-axis scale through the bone's rest axes by their absolute values, so a scale of 1 on a bone tilted 12° keys 1.19 on two axes; Bloatoad's squash chain leaned 12° and every clip stood it 19% taller and deeper than its rest (the sidestep's bowling pin). Its rig's chain now stands straight up (`RIG_BASE`, `RIG_TOP`; the weights keep the old axis) and the sac bone is level. Keep any bone a clip scales axis-aligned.
- **Scrollopus:**
  - Eight tentacles: 4 `ground` (mirrored), 3 `hold` (the scroll, the quill on its right, the book), and 1 `free` on its left as the `ink_arm` (the attack picture sprays from a raised tentacle beside the head on its left).
  - As built (Nov 15): five low tentacles (front-left, right, back-right, back, and the ink arm on its left-back, role `ground`), three holding; 4 bones each, 47 joints; ko `'roll'` 82° with the quill arm's tip turned (`ko_bones`) so the quill lies flat. Its skin weights blend each tentacle by the gap to its own skin (a softmax over the tentacles, `scrollopus_field.py`), so a lifted tentacle never drags its fused neighbour into a sheet.
  - Round 2 (review: a ball on a pinched neck): the head is one pear whose roots leave its flank (`ROOT_Z` 0.47) and slope out as a skirt; `head_split` 0.45 still keeps the face above the split. Strike, hit and win use the per-clip knobs only (`strike_bones`, `hit_bones`, `clip_bones`, `CLIP_CALM`).
  - Round 3 (review: a capsule on stilts): a rounder ball 5 cm lower (`head_split` 0.4), the roots under it (`ROOT_Z` 0.38) flaring straight out into thick arms that lie along the ground in S-curves and big leaning curls, a wide core filling the base. Two traps: a tentacle field that extends the first segment behind the root without a limit lets a flared root's line run through the body and claim the far side's skin (`scrollopus_field.BEHIND` caps it at 15 cm); and `CLIP_CALM` scales a recipe's own `clip_bones` too, so win's book and quill raise (on top of the plan's 40° gesture lift) are left uncalmed and only the scroll is calmed.
  - Polish (Nov 15): its colour map ships as UASTC instead of ETC1S (`tools/art/ultra.ts` `BASE_UASTC`, opt-in per look; the small dark ink dots stepped into ETC1S blocks); the cap's band follows the head to below the board's underside, then rises straight up into the board (a sloped shelf under the board caught the light and read as a gap); the book's cover and spine are turned toward the front, the arm round its spine; a hold arm's last joint stays at least 3 cm past its third (`scrollopus_form.hold_tentacle`).
  - Cap and spectacles are props on `head`; a cap tassel chain.
  - strike `'ink'` (Ink Flick) or `'slap'` (Tentacle Swat); cast `'raise'` (a lecture with the props aloft); ko `'front'` or `'back'`. `head_split` 0.4 (round 3).

## Construct plan (`PLAN = 'construct'`, `plans/construct.py`; batch 5, Nov 15)
For machines and furniture that move as rigid parts: Lootlid now; Gearhoot later, through the hooks below, which are not tuned yet. The stand-in `breeds/_construct_test_ultra.py` is a chest with every lid option on; `WS_CONSTRUCT_NECK=1` tries the Gearhoot hooks. It is not a breed and is never shipped or registered.

**`rig_p()`, required** (model it standing, the lid shut):
- `hip` (x, y, z): the body's centre. The bone `hips` (parent `root`) carries the body rigidly.
- `chest` (x, y, z): the body's top, the neck's base in the 'neck' head mode (the build's ko measure reads it).
- `head_c`, `head_r`: the face.
- `legs`: as the shelled plan's (`leg<i>` / `shin<i>` / `foot<i>`, parent `hips`), planted by IK. Two pairs walk in diagonal pairs; one pair alternates.

**The head** (`head_mode`: `'lid'` when `hinge` is given, else `'neck'`):
- `'lid'` (Lootlid): `hinge` (the lid's hinge, at the back) and `lid_front` (its front edge). The bone `head` (parent `hips`) runs between them and swings up `lid_max` [70°] about the hinge to open the mouth. The eyes and everything on the lid ride it; there is no jaw bone.
  - The jaw lesson, for a lid that is the jaw: no part gets heat weights. Model the lid and the box as **separate shells**, with a gap of 2–3 voxels (≈ 2.5 cm) along the seam, so the voxel union keeps them apart. Then weight the box with `U.rigid(…, 'hips')` and the lid with `U.rigid(…, 'head')`: the seam is a hard split at the hinge, and nothing of the lid stretches over the box when it opens.
  - `mouth` [the box's front lip]: `socket_mouth`, where coins (or bolts) leave.
- `'neck'` (a Gearhoot hook): `neck` points → `neck.1..N` from `chest`, `head` to `head_tip`, and a `jaw` (a beak) with `'jaw_open': True` (as the other plans'). `look()` turns the neck far, as an owl does.

**Options:**
- `tongue` `{'points': [p0 … pN] (inside the box), 'parent': 'hips', 'reach'}` → `tongue.1..N`, unconnected, as the blob plan's. The bones slide out along it, and the part that is out droops over the lip (`droop`). The lid is held at least 40° open whenever the tongue is out. Model it as a prop mesh skinned with `U.chain_weights` in `prop_weight_regions`. `socket_tongue` sits at its tip.
- `spinners` `[{'name', 'head', 'tail' (its axis), 'parent': 'hips', 'rate': turns a second}]` → `spin.<name>`: a wind-up key or gears that turn a whole number of times in every loop and rest in the one-shots. `socket_<name>`.
- `chains`: kinds `tassel`, `tail`, `antenna`, `tuft` and `wing` (a Gearhoot hook: gear-feather wings that flap about the body's long axis; no springs). `props` [parent `hips`] (a coin hoard inside the box).
- `sink` [measured: the body's lowest vertex owned by `hips`], `sit_drop` [measured: where the legs, coming down with the body, would meet the ground]: how far sit and sleep lower the body. Stubby legs give a squat with the feet splayed. `hop`, `stride` [1].
- `heat` [none]: a list of bones to keep heat weights for. Otherwise every moving part is skinned by the recipe: `head`, `jaw`, the legs, the tongue, the spinners and the chains.
- `strike_style` ['chomp' with a lid, else 'peck']. Every style is 24 frames with `impact` at 13:
  - `'chomp'`: rears back with the mouth wide open, then lunges and slams it shut on the impact (Lid Chomp).
  - `'tongue'`: the tongue lashes out, fully out from 0.48 to 0.62 of the clip (Tongue Grab). `tongue_aim` [8°] tips it down.
  - `'spit'`: shut tight and reared back, then the mouth snaps wide as it pitches forward; the coins burst from `socket_mouth` on the impact (Lootlid's attack picture).
  - `'slam'`: a hop at the target, landing front first on the impact (Treasure Slam).
  - `'peck'`: a Gearhoot hook (the head jabs on its neck).
- `cast_style` ['spit' with a lid, else 'raise']: `'spit'` gathers low and shut, then bursts open at `release` (a shower from `socket_mouth`: Coin Toss, Gold Rain); `'raise'` rises tall on its legs with the mouth opening, then thrusts.
- `strike_yaw`, `ko_style` ['roll' (`ko_roll` [80°]) or 'back' (`ko_pitch` [90°])], `body_width`, `ko_lift`, and the per-clip knobs: as the shelled plan's. In ko the lid falls open, the tongue lolls out and the legs splay.

**Clips:** the same 32 names, lengths, markers and faces as every plan.
- `body()` keeps the body (and the props on it) at least 3 mm off the ground.
- The lid breathes a crack open in idle, chatters in battle_idle, flaps at every step, pops open in a hit (the tongue flung out, as the hit picture), yawns in idle_tired, snores in sleep, and stays open with the tongue out in idle_happy, pet, sit, celebrate and win.
- **Groups and sockets:**
  - CLIP_CALM groups: `neck`, `tongue`, `spin`, each chain by its name or kind, and `leg`.
  - Sockets: the game's seven (`socket_paw_L` / `_R` at the front feet), plus `socket_core`, `socket_tongue`, `socket_<spinner>`, `socket_<chain>` and `socket_<prop>`.

**Joints:** the base rig has 5 (root, hips, head, 2 blink bones). Add 2–3 per leg, the tongue's bones, the spinners, the chains and the props; plus the neck and a jaw in the 'neck' mode. The stand-in has 24 as a chest and 18 as an owl. Estimates:

| Breed | Estimate |
|---|---|
| Lootlid | ≈ 21 (4 legs × 3, a 3-bone tongue, a coin-hoard prop) |
| Gearhoot (later) | ≈ 20–30 (neck 1–2, a beak, 2 legs × 3, 2 gear-wing chains × 2–3, the key spinner, the monocle prop) |

**Per breed:**
- **Lootlid:** `HEIGHT_UNITS` 135 (0.9 × Puddlepup's height).
  - The lid and the box are separate shells. The eyes and the keyhole plate are on the lid; the gold bands are split with them.
  - A 3-bone tongue prop lying on a coin-hoard prop inside. There are no teeth: the card says goofy, never menacing.
  - strike `'chomp'` (Lid Chomp) or `'tongue'`; cast `'spit'` (Coin Toss: the attack picture's burst of coins); ko `'roll'`.

## Serpent plan (`PLAN = 'serpent'`, `plans/serpent.py`; batch 5, Nov 15)
For long, legless monsters: Coilfang now; Aurelwyrm later, through the `float` option and the ribbon and whisker chains, which are not tuned yet. The stand-in `breeds/_serpent_test_ultra.py` is a snake with every option on; `WS_SERPENT_FLOAT=1` tries the Aurelwyrm hooks. It is not a breed and is never shipped or registered.

**`rig_p()`, required** (model it resting, head raised):
- `spine`: `[Q0 … QN]`, the body's centre line from the back of the head to the tail's tip. Use 12–16 bones of about equal length; the parts lying on the ground have their centre line at the body's radius.
- `hip` (x, y, z): the anchor. The spine point nearest it is where `hips` starts, pointing toward the head.
  - The forward chain `spine.1..`, `neck.1..N` runs to the head; the last `neck_bones` [4] are the neck (neck.1 nearest the body).
  - `tail.1..` runs from the anchor back to the tip.
  - Put the anchor on the ground at the body's first curve behind the neck.
- `chest`: a point on the neck's base (the build's ko measure reads it).
- `radius`: the body's half thickness (the ground clearance, the coil's spacing).
- `head_c`, `head_r`, `head_tip`: `head` runs from Q0 to `head_tip`, with a `jaw` (`'jaw'` in `MERGE_INTO_HEAD`, `'jaw_open': True`, the lower jaw by `U.rigid`).

**How it moves:**
- Every spine bone keeps its length and gets a heading and an elevation along the body's arc length: the rest pose's, plus the clip's bends, travelling waves, rears and the coil. The chain is rebuilt from the anchor each frame; the spline is the polyline through the joints.
- The body stays belly down unless a clip twists it (hit_heavy, ko). Each bone's far end never goes below its rest height where it lies, or below `radius` for the neck. The head holds itself level, taking `head_follow` [0.35] of the neck's rise.

**Options:**
- `coil` `{'turn': ±1, 'spacing': 2.3 × radius, 'inner': 1.6 × radius, 'centre': True}`: the coil-sit for sit_down, sit and sleep. It is an Archimedean spiral through the anchor: the tail winds inward and the body outward.
  - In sit, the neck rises out of the coil and turns to face forward.
  - In sleep, the neck lies along the coil and the head rests on it.
  - `centre` moves the coil under the root.
- `tongue` `{'points', 'parent': 'jaw', 'reach': 0.12 m × size_k}`: a forked tongue (a prop mesh, skinned with `U.chain_weights`) that flicks in idle, look_around, sit, battle_idle and win. `socket_tongue`.
- `chains` [parent `head`]. They get no heat weights unless `heat: True`. Kinds:
  - `crest`: a fan of feathers that flares in idle_happy, battle_idle, strike, cast and win, and lies flat when sad, tired or ko.
  - `whisker` and `tassel`: hang and trail.
  - `ribbon`: fins that trail and ripple (the Aurelwyrm hooks).
  - `tail`.
  - `tail_springs` [2]: the tail's last bones as a `springs` entry of kind `tail`.
- `float` [0 m]: a floating serpent (the Aurelwyrm hook) is lifted that high, with no ground guard.
- `strike_style` ['lunge']. Every style is 24 frames with `impact` at 13:
  - `'lunge'`: coils the neck back into an S, then shoots the head out level at the target with the mouth wide, the body sliding after it (Fang Snap; the attack picture).
  - `'squeeze'`: the body's front loops out and closes round the target ahead (Coil Squeeze).
  - `'whip'`: the tail swings round from behind and lashes forward.
- `cast_style` ['hiss']: `'hiss'` rears up with the crest raised, then hisses at `release` (Venom Mist, from `socket_mouth`); `'rise'` rears up tall, the body's front lifting too, then sweeps down.
- `strike_yaw`: as the shelled plan's (on the neck).
- `ko_style` ['belly']:
  - `'belly'` flops flat with the neck and head down on the ground, twisted belly-up by `ko_twist` [140°].
  - `'flat'` doesn't twist; the head lies on its side.
  - `body_width` and `ko_lift`: the anchor's height, settled exactly by the build.
- The per-clip knobs: as the shelled plan's (`clip_bones` rotations add a local bend on a spine bone).

**Clips:** the same 32 names, lengths, markers and faces as every plan.
- **Ranch life:**
  - idle: a slow breathing wave, the neck swaying, a glance and a tongue flick.
  - idle_happy: bobbing, the crest up, the tail tip rattling.
  - idle_tired (a yawn), idle_sad (the neck low, the crest flat) and idle_sick.
  - sleep and sit: the coil. eat: the head to the ground, gulping.
  - pet, look_around, hop (the body springs off the ground and the neck rears), celebrate.
- **Moving:**
  - walk, run, dash and the steps slither: one wavelength of bends runs down the body each clip, toward the head going backwards. The root speed is the wave's travel × `grip` (0.4–0.65; the rest slips).
  - strafe is an approximate sidewind; sidestep is a quick sideways spring.
- **Battle:** battle_idle is a cobra's raised S, swaying, with the tail tip rattling. Then strike, cast, shove (a neck bump), hit (the head thrown back), hit_heavy (the front flung up and rolled, the belly showing), ko and win (a rear and a dance).
- **Groups and sockets:**
  - CLIP_CALM groups: `spine`, `neck`, `tail`, `tongue`, and each chain by its name or kind.
  - Sockets: the game's seven (`socket_paw_L` / `_R` at the head's sides, where a strike's effect starts; `socket_tail` at the tail's tip), plus `socket_core` (the anchor), `socket_tongue`, `socket_<chain>` and `socket_<prop>`.

**Joints:** the spine (12–16) + head, jaw, root and 2 blink bones, + the tongue, the chains and the props. The stand-in has 23 (14 spine bones). Estimates:

| Breed | Estimate |
|---|---|
| Coilfang | ≈ 25–27 (16 spine bones, a 2-bone forked tongue, a 2–3-bone crest) |
| Aurelwyrm (later) | ≈ 35–45 (16 spine bones, ribbon-fin chains, 2 whiskers × 2–3, antler props) |

**Per breed:**
- **Coilfang:**
  - Size: `HEIGHT_UNITS` 150 (coiled, 1 × Puddlepup's height). Its pictures agree with the card's length, 3.5 × Puddlepup's (≈ 3.3 m snout to tail tip): the turnaround's path measures about 3.3 × its height.
  - A golden feather crest (a `crest` chain, or a few for a fan), two fangs in the head's mesh, a forked tongue prop.
  - strike `'lunge'` (Fang Snap) or `'squeeze'` (Coil Squeeze); cast `'hiss'` (Venom Mist); ko `'belly'`; `strike_yaw` ≈ 15.

## Coats without fur (skin, velvet, scales, stone)
A recipe without `head_lock_params`, `body_lock_params`, `card_params` (or with `CARD_LAYERS = 0`) and `tuft_frames` builds a body with no locks, no cards and no tuft: the detail comes from the high source's carving and plates baked into the normal map and AO, and from `paint_sources` (and `body_material`'s per-pixel marks). Every step handles it: the build makes no `lo_cards` / `lo_tuft` (the sidecar's `meshes` lists only what exists; `buildStats.cards` is 0), the bake, rig and export skip them, `tools/art/ultra.ts` ships without colour sets to promote, and the Lite copy has nothing to drop. `flow` is not needed. The game treats every mesh as optional.
- `ATLAS_STRIP = 0` (only without cards and tuft): the body atlas has no strip of card and tuft tiles; the islands get the whole square (≈ 14% more texels for the scales). The sidecar's `atlas.strip` says 0.
- The body kind keeps the film material's soft sheen (velvet and skin read well with it); stone and scales get their gloss from the `rough` paint (roughness and the clearcoat mask).
- **Hard plates** (cobbles, scales), from `lib.ultra` and `lib.surface`:
  - `plates = U.plate_layout(p, n, spacing, radius, height, seed, flow=None, aspect=1.0, wobble=0.12)`: a Poisson set of plates on sample points (the high body's vertices: `S.mesh_arrays(hi_body)`); per-point `spacing` (NaN = none there), `radius`, `height`; `flow` orients each plate's long axis and a scale's raised edge. Radius ≈ 0.8–1.0 × spacing covers the skin; less leaves skin between (moss grooves).
  - `S.apply_plates(ob, plates, shape, scale=1.0, inset=0.0, prefix='plate', edge_soft=0.0)` (`edge_soft` 0..1 rounds the plates' walls where steep stones stretch the voxel body) pushes the vertices out (shape `'cobble'`: rounded stones with steep sides; `'scale'`: shields raised toward their trailing edge, each overlapping the next) and stores `<prefix>` (inside a plate), `<prefix>_rim` (edges and grooves: moss, a scale's outline), `<prefix>_top` (crowns: wear, lichen) and `<prefix>_id` (`U.plate_hash(id)` = a random number per plate for colour or gloss) for `paint_sources`. Call it in `carve(hi_body)` after the rest of the carving; keep the `plates` (a module dict) for the low body. Two kinds on one body: call it twice with different prefixes.
  - `carve_low(lo_body)` [optional]: called on the low body after it is built and before it is decimated. For relief that must reach the silhouette (Cobblemaw's cobbles, 2–5 cm), apply the same plates there at about `scale=0.85, attrs=False`, so the low body bulges too and the bake's cage (2 cm out, 5 cm in) still finds the stones. Small relief (scales, 2–3 mm) belongs to the high source only.
  - Budget: nothing extra (the plates are the body's own triangles). Quick builds carve at 6 mm voxels, too coarse for scales; judge scales from a full build.
  - The alternative, rigid stones as `build_props` skinned with `U.segment_weights`, costs triangles and leaves gaps when the body bends; prefer displacement unless a stone must move on its own.
- Glow (Hearthwing's chest, the grown form's grate): the film material has no emission for the body kind; paint the glow bright and warm. A small membrane (`build_fins`, kind fin) glows a little with its own colour in the game, if a patch must glow.

### Coat, eyes and Lite (each optional)
- `eye_material(name, rough_pass=False, pal=None)`: a recipe whose eye_material takes this third parameter gets one eye colour pass per variant (the variant's palette, e.g. its `eye`), so a variant's eyes bake in their own colour; with two parameters every variant shares the base eyes.
- `tuft_colours(pal, tpos, lrand)` → n×3 linear RGB per tuft vertex (`tpos` 0 root … 1 tip, `lrand` 0..1 per lock): a root-to-tip gradient instead of the flat `tuft_colour(pal)`.
- `UV_SMOOTH = 80` (Laplacian steps) and optional `uv_smooth_mask(co)` → 0..1 per lo_body vertex: lo_body is unwrapped at heavily smoothed positions (same topology), then put back, so a lumpy coat (wool, shag, cobbles) unwraps into far fewer, larger islands (Nimbusheep: 1,746 islands → 376, coverage 0.20 → 0.56). Mask 0 on the face and ears keeps them as they are.
- `CARD_COLOUR_FROM` ['atlas']: where each fur card takes its colour. `'atlas'` samples the baked atlas at its root, where a lying lock of another colour may cover it (stray pale or grey cards at colour borders); `'skin'` samples a bake of the bare skin (hi_body alone, with the atlas's AO; one extra colour bake per variant): the fix for those border cards; `'paint'` takes the skin's vertex paint at the root (fast, but without the per-pixel marks and the AO, so cards read brighter).
- `CARD_STYLE = 'wool'`: the strip's six card tiles are curly, crimped ringlets in a fluffy clump instead of damp-fur locks (same layout, same alpha fade).
- `CARD_STYLE = 'hair'` (Nov 8): thin strands instead of fur lobes, for long cards (a mane, a long tail, a beard). Each tile has 8–14 strands 10–20 px wide (at 256 px) with alpha-0 gaps between them. Each strand tapers over its top 40–60% to a fine point, with a soft 2–3 px alpha falloff along its sides. The shading is in the tile: roots about 0.6×, lighter tips, a thin highlight line and a darker edge per strand, a little brightness jitter between strands. The normal rounds across each strand. The tiles are painted in numpy (`bake.hair_tile`), not baked from geometry. (The fur tiles' 2–3 broad, almost fully opaque, unshaded lobes read as cut-paper blades on Starhowl's mane.)
- `CARD_LAYER_STYLES = ('fur', 'hair', 'hair')`: one style per card layer (`card_params(p, n, layer)`), so a mane layer can be hair while the body stays fur. Mixed styles share the six cells: two styles get three cells each, three styles two each. Each card picks from its own layer's cells. Changing it re-maps the cards' UVs, so run the build stage again; a single `CARD_STYLE` keeps all six cells and needs only the bake. Puddlepup and every recipe without these settings keep their tiles byte for byte.
- `NORMAL_SCALE = 1.1` (Nov 8): written to the sidecar as `normal.scale`, the normal map's strength in the game's film material (default ART.ultra.film.normalScale, 0.6). Scaled and stone breeds (Hearthwing, Cobblemaw) use about 1.0–1.2 so their baked relief shows. The game-side runtime reads it.
- `BODY_SHEEN = 0` (Nov 13; 0..1, export checks it): written to the sidecar as `body.sheen`, the body's sheen in the game's film material instead of the fur's (default ART.ultra.film.furSheen, 0.45). A stone breed (Cobblemaw) uses 0: on stone the fur sheen reads as felt with a soft halo. Props never have sheen, and cards and the tuft keep theirs. Absent: the default, as before. Takes effect with `--stages export` and a ship; the game-side runtime, the review viewer and the ranch portraits read it.
- `CARD_EDGE_FADE = (0.15, 0.55)`: written to the sidecar as `cards.edgeFade` (1 − |N·V| where the cards start to fade in and where they are full; the game's default is ART.ultra.film.cardEdgeFade, [0.25, 0.65]). Lower values show long mane cards more face-on. The game-side runtime reads it.
- `MOUTH_SOCKET = (x, y, z)` (model space) moves `socket_mouth` to the lips, so breath and flame effects don't start inside the snout; `SOCKET_POINTS = {'socket_name': (x, y, z) or (bone, (x, y, z))}` moves any socket or adds one (a new one needs its bone).
- `MEMBRANE_AO_BODY = False` [True]: the membranes don't shade the body's AO bake (folded wings would leave a flank shadow that stays visible when they spread); the default keeps them (Puddlepup's ear linings).
- `LITE_PROPS_TRIS = 4500` [2400]: the Lite copy's share for props (lo_props and every lo_props_<short>; simplified to fit only above it, at most 60% of the 12k); the body takes what is left. For prop-heavy breeds whose signature props (Petalphant's ears and bud) would be crushed at 2.4k. Sidecar `litePropsTris`.
- `AO_FLOOR = 0.35` [0, off] and `AO_SOFTEN = 1.5` [0, off]: the baked AO (ORM red, and its `BASE_AO` share multiplied into the base colour) gets a Gaussian blur of that many texels (only among texels the bake wrote, so the empty space between islands never darkens an edge), then no written texel stays darker than the floor. For narrow slots that bake near black: between crossing clumps, at crowded lock roots, in deep wool seams (Rammerjack's beard specks, Starhowl's AO median 0.55). The strip's tiles are untouched. The bake log says `atlas: AO softened … floor … (N texels raised to it)`, and the AO percentiles after it show the result. Start with a floor of 0.3–0.4 and a softening of 1–2 texels; more flattens real creases.
- `LITE_KEEP = ('tuft',)`: the Lite copy keeps these parts (`'tuft'`, `'cards'`) instead of dropping them; they count inside its 12k triangles (the body takes what is left). Sidecar `liteKeep`.

## Glow (a channel of its own)
Parts that really glow and bloom (Starhowl's constellations and star tips, Cinderlynx's embers, Hearthwing's chest, later Pluckrex and Grumblestone):
- `GLOW = {'strength': 1.0, 'tint': None}` turns the glow pass on. Without it nothing changes (no pass, the ORM stays RGB, no sidecar entry).
  - `'twinkle'` [1] (Nov 14, opt-in; also in a `VARIANT_ORM` glow): the runtime's twinkle share, written to the sidecar's `glow.twinkle` (src/art3d/ultra/parts.ts glowOf, perf/content.ts and viewGpu.ts). The twinkle has a random phase per 4 × 4-texel cell, so a large glowing area (Wishlume's paper) showed it as a fine square stipple; 0 keeps the glow steady. Absent: as before.
- Paint a per-vertex `glow` (FLOAT point attribute, 0..1) on any source in `paint_sources` (body sources, membranes, props; a source without it glows 0), and/or give `glow_material(name, marks)` → the body sources' glow-pass material for crisp per-pixel shapes (`lib.marks.glow_material(name, marks_fn)` makes one from the `glow` attribute and your marks; `marks` is what `make_marks` returned). Membranes, props and the eyes use the attribute.
- The bake renders the glow on the atlas's UVs after the other maps and writes it into the **alpha of `atlas_orm.png`** (A = glow mask, R AO, G roughness, B clearcoat as before); shared by every variant. The sidecar gets `glow: {strength, tint}`; the runtime's emissive is base colour × mask × strength (`tint`, a hex, overrides the hue). `tools/art/ultra.ts` keeps the alpha through the padding and encodes the ORM as RGBA (KTX2 ETC1S, WebP yuva420p), in the Lite copy too. The Blender review sheets show it glowing.
- Fur cards and the tuft take their tiles from the shared strip, so they can't glow by the atlas; lying locks (baked into the body) can.

## A variant's own ORM (`VARIANT_ORM`, Nov 12)
By default every variant shares the breed's ORM map: its roughness, its clearcoat and, for a glowing breed, its glow mask. A variant that needs its own (Granite Cobblemaw's polished sheen, Stormcrown Nimbusheep's glowing gold) opts in:
```python
VARIANT_ORM = {
    'granite': {},                                                # its own roughness and coat
    'stormcrown': {'glow': {'strength': 1.4, 'tint': '#ffd36a'}},  # and its own glow
}
```
- **Keys** are variant shorts, as in `atlas_<short>.png`.
- **Roughness and coat:** in `paint_sources`, write a colour attribute `rough_<short>` on every source (body sources, membranes, props), laid out like `rough`: (1, roughness, coat). Any source without it uses `rough`, so a variant can change only its glow.
- **Glow, with `'glow'` set:** the variant gets its own glow pass.
  - Write a FLOAT point attribute `glow_<short>` (0..1) on any source; sources without it count as 0.
  - Per-pixel shapes come from `glow_material(name, marks, pal)`: give `glow_material` a third parameter and the bake calls it with the variant's palette for the body sources.
  - The variant can glow on a breed without `GLOW` (Stormcrown).
  - `'glow': None` is the same as leaving it out. To stop a glowing breed's variant from glowing, give it its own `'glow'` and no mask (no `glow_<short>`, no marks).
- **Glow, without `'glow'`:** the variant keeps the breed's glow mask and spec, if the breed has `GLOW`.
- **What the bake writes:** `atlas_<short>_orm.png`. Its AO and the strip's tiles are the breed's; its islands take the variant's roughness and coat; its alpha is the variant's glow mask (RGB when it doesn't glow). The log says `orm <short>: …`.
- **Sidecar:** `variants[vid].orm`, plus `variants[vid].glow` (`{strength, tint}` or null).
- **Ship:** `tools/art/ultra.ts` pads the map, encodes it as `<breed>_<short>_orm.{ktx2,webp}` (KTX2 ETC1S; WebP with the alpha floor) and hangs it on that variant's `__variant_<vid>` holder as its occlusion and metallicRoughness texture. The Lite copy carries it too, at 1024². The shipped sidecar says `orm: true`.
- **Runtime:** `src/art3d/ultra/ultraAsset.ts` swaps the holder's ORM in on every part but the eyes when that variant is shown, and glows by `variants[vid].glow` (`parts.ts` `variantHasOwnOrm`, `glowFor`). This runs in WebGL and WebGPU, and the review viewer does the same.
- **Unchanged:** a variant without an entry, and the usual look, keep the shared ORM exactly as before.
- **Cost:** one ETC1S 2048² map per opted-in variant, about 0.4–0.8 MB of KTX2. It counts in the 8 MB budget.
- **When it takes effect:** adding or changing `VARIANT_ORM` needs a run from the bake stage. Without `rough_<short>` or `glow_<short>`, that's only a re-bake; writing them in `paint_sources` needs the build stage.

## A variant without fur cards (`VARIANT_CARDS_OFF`, Nov 12)
`VARIANT_CARDS_OFF = {'granite'}` lists variant shorts whose look hides the fur cards (`lo_cards`). Granite Cobblemaw is bare polished stone, and the moss cards read as fibres on it whatever their colour.
- The build checks the names are variants.
- The export writes `variants[vid].cards: false` into the sidecar, and the ship passes it through.
- The runtime hides the cards on that variant only, after measuring, so it stands as tall as the other looks (`parts.ts` `variantCardsOff` / `partVisible`). WebGL and WebGPU share this, and the review viewer follows the same rule.
- The Lite copy has no cards anyway.
- The flag is written by the **export** stage. A built look needs `npm run art:ultra -- <breed> --blender --stages export` (about a minute of Blender, through slot.sh) and then its ship; nothing is re-baked.

## A props material (`prop_material`, Nov 12)
`prop_material(name, attr, pal, marks)` → the props' colour-pass material, like `body_material`. It is called with `'paint'` and the breed palette, then with each variant's `paint_<short>` attribute and palette. It paints props per pixel (Petalphant's petal ears: veins, a gradient) instead of only from their vertex paint. Without it the props use `emission_attr_material(attr)`, as before. The roughness and glow passes are unchanged (`rough`, `glow` attributes). It needs a run from the bake stage.

## Per-pixel marks (`lib/marks.py`)
- **The ceiling** (Nov 8): Cycles compiles the body material into a fixed-size SVM stack. Too many mark nodes and it logs `ERROR Shader graph: out of SVM stack space, shader "paint_base" too big`, then bakes that map BLACK and carries on. On Starhowl's real meshes 200 stars + 81 lines bake; 275 + 81 doesn't. That is lower than earlier tests suggested, so keep well under it, and merge masks with `marks.union` (a balanced MAXIMUM tree) rather than chaining them.
- **Guards**: the bake stage compares each baked colour map's median over the islands with the body paint's own, and stops in words below 30% (`bake check: … median luminance …` in the log; dark coats still pass). `npm run art:ultra -- <breed> --blender` watches Blender's log for the SVM error and stops. It also runs Blender with `--python-exit-code 1`, so any uncaught Python error fails the build (Blender's default exit code was 0: a failed build looked done, and the ship then used the old files). Direct `blender … build_ultra.py` runs should add `--python-exit-code 1` too.
Marks built from loose math nodes cost about ten nodes each (4,000 stars: 525 s to build). `lib.marks` makes each kind once as a node group (`WS_MarkDot`, `WS_MarkStar`, `WS_MarkLine`) and instances it per mark: one group node plus one MAXIMUM each (about 5 s for 4,000).
```python
from lib import marks as MK
pos = nb.coords().outputs['Object']
masks = [MK.dot(nb, pos, c, r) for c, r in spots]                       # ellipsoids: r a number or (x, y, z)
masks += [MK.star(nb, pos, c, n, t, 0.012, inner=0.45, points=5) for c, n, t in stars]   # on the surface: normal n, first point toward t
masks += [MK.line(nb, pos, a, b, 0.002) for a, b in links]             # a constellation's lines, stripes
mask = MK.union(nb, masks)                                              # 0..1 (a balanced MAXIMUM tree)
c = nb.mix(mask, c, nb.rgb(C.lin(star_hex)))                            # in body_material; or the glow material:
glow_material = lambda name, marks: MK.glow_material(name, lambda nb, pos: MK.union(nb, [...]))
```
Keep each mark's numbers plain (lists and floats) so `make_marks` can return them and the bake gets them back through `marks.json`.

## Props: UVs, normals, height
- **Own UVs**: smart-project cuts a curved tube (a horn, a rope) into many small islands. Give the low part its own unwrap in the UV layer `'UVMap'` and the custom property `ob['own_uv'] = True` (or call `S.tube_uvs(ob, axis_points)`: one strip, u around, v along, in metres, seam mended; it sets `own_uv`). The build keeps those faces' UVs (only scaled to the common texel density and packed with the rest: `bake.pack_atlas(..., keep_faces='own_uv')`). Works for membranes too.
- `tube_uvs` (Nov 7): positions along the tube follow the mesh (`S.tube_param`), so a rope coiled tighter than it is thick no longer takes the next turn's place. The angle comes from rotation-minimising frames, so it doesn't jump where a horn turns through vertical. Faces with a corner on the axis (a fan cap's centre, a tip's point: nearer it than `cap_ratio` 0.25 × the median radius) unroll flat as one disc per end beside the strip. One tube per call, the axis through the middle of the tube. A broad flat band (a scarf end 4× wider than thick) or a part that folds back on itself unrolls badly; the packer repairs what overlaps, but plain smart-project (no `own_uv`) may suit such a part better.
- **No shared texels** (Nov 7): two faces whose UVs cover the same texels bake into the same pixels. Tumblefox's belly lay over a front sock (a cream/plum checker); Puddlepup's cheeks lay under the ears; Rammerjack's ropes and caps overlapped by tens of thousands of texels.
  - After packing, `bake.pack_atlas` raster-checks every low mesh (`bake.uv_overlap_faces`, a 2048 grid). Faces that share texels are projected again on their own: smart-project at the pack's angle, then at a third of it, then each face flat on its own, with folded faces laid round a circle. They are scaled back to their object's texel density (the eyes and `ATLAS_DENSITY` keep their share) and packed with the rest. A pack without overlaps is left as it was.
  - The build then stops in words if any low mesh still has more than 32 shared texels (`UV_OVERLAP_MAX`). It logs `uv: <mesh> has N texels shared…` and writes the counts to `stats_build.json` (`uv_overlap_texels`) and the sidecar (`buildStats.uvOverlapTexels`).
  - `node tools/art/ultra-uv.ts <breed…> [--shipped]` counts the same on a raw export (or on the shipped .glb in `public/`). `tools/art/ultra.ts` warns at ship time (`WARNING uv overlap: …`). Fixing an old overlap needs a rebuild from the build stage.
  - Blender's `pack_islands` isn't repeatable run to run (two runs of the same code gave different layouts), so any build-stage rerun re-lays out the atlas. The look is unchanged, but every texture file changes.
- **Normals**: bmesh's `recalc_face_normals` can flip thin, curved or closed ribbons such as a scarf; an inverted prop bakes an inverted normal map and shades pale in the game. Orient props explicitly: `S.orient_away(ob, inside_fn)` turns every face away from `inside_fn(face centres)` (a tube's nearest axis point, a scarf's neck axis).
- **Shape preview colour**: props are tinted accent × 0.6; `preview_prop_colour(name)` → hex or linear RGB per prop (ivory tusks, copper horns).
- **Height**: the sidecar's `restHeight` (what the game scales by) is the body's; `restHeightWithProps` is always there too (the same value when no always-worn prop tops the body; variant-only props are left out), the build logs both when they differ, the shape preview prints the height with props against the size rule, and the lineup shows it.
- `texel_k(co)` → k per lo_body face (from the face centres; or a FACE float attribute `texel_k` on any low part): that face's texel density × k, e.g. the head 1.6, the belly 0.7 (missing or ≤ 0 = 1). The faces are grouped by k in 0.1 steps and each group is smart-projected on its own, so no island straddles two densities; an own-UV island takes its faces' mean k. Without it the pack is as before. The atlas is still one 2048² map, so raising one part's k shrinks the rest.
- `ATLAS_ANGLE = 75` [62]: smart-project's angle limit in degrees. A larger limit cuts fewer, larger islands (Hearthwing's scaled skin: hundreds of tiny islands, 34% of the atlas used); too large and islands fold over themselves (the packer then re-projects those faces, see No shared texels).
- `ATLAS_DENSITY = {'lo_fins': 0.3}` for a breed with hundreds of fin locks or big plain membranes: they take less of the atlas and the body more.

## Bake coverage and review parity
- **WebP copies keep the colour under transparent texels** (Nov 8): libwebp threw away the RGB wherever alpha was 0. A glow look's ORM has the glow mask in its alpha, which is 0 on about 97% of the atlas, so its WebP copy shipped with AO and roughness wrecked (Hearthwing grown: AO off by 53/255, a dark band across the throat on WebP phones). Every WebP with alpha (the colour maps, a glow look's ORM, the Lite) is now encoded with its alpha raised to at least 1/255 (`WEBP_ALPHA_FLOOR` in tools/art/ultra.ts). That keeps the colour and is invisible. The KTX2 maps were never affected.
- **Normal map encoding** (Nov 8): the shipped KTX2 normal map is UASTC (RDO 1.0, zstd 18) at 1024², not ETC1S at 2048². ETC1S's 4×4 blocks showed as square steps on smooth and scaled skin. The half-size UASTC map measures closer to the 2048² source (mean angular error Hearthwing 2.0° vs 3.1°, Puddlepup 3.4° vs 4.0°) for about 0.2 MB more per look. A full-size UASTC map would add 2–3 MB and push Tumblefox past 8 MB. The colour and ORM maps stay ETC1S; the WebP copies and the Lite stay as they were. The sidecar's textures note `ktx2Px: 1024` for the normal map.
- **Held poses survive the export** (Nov 7): the glTF exporter drops a bone channel that stays constant through a clip (in NLA_TRACKS mode every channel counts as baked), so a held pose came out at rest in the game: every look's `sleep`, the lowered neck in idle_tired and idle_sad, Petalphant's bud. The export stage now nudges each constant, non-rest channel invisibly on one middle frame (`export.hold_constant_channels`, logged as `export: kept N held channels…`). Bones a clip doesn't key stay unkeyed. It then checks the .glb against the actions and stops in words if a keyed, non-rest channel is missing (`export check: …`).
- **Review shots**: the turnaround and head shots show the true rest pose (`anim.rest_pose`: every NLA track muted). The poses sheet (and `art:ultra-review`) also shows strike's wind-up at 0.3 (`pose_strike_windup`). The in-game sheet names only the parts a breed has: cast (wings open / trunk raised) and idle_happy (bud open).
- **Decimation** (Nov 7): after the low body's decimation the build logs how much of the voxel body it kept (its box per axis, its surface area). It stops in words if any axis keeps less than 90% (a keep mask that protects too much lets the collapse take whole regions: Cobblemaw's build 1 kept only the head and neck). It warns loudly below 80% of the area.
- **A stalled decimation** (Nov 8): when the weighted collapse stops above its target (too much of the body protected), the build used to plain-decimate the rest out of the unprotected skin. That flattened Hearthwing grown's chest and belly into 60 cm facets. Now an overshoot up to 1.25× is kept as it is, with a loud `WARNING weighted decimate stopped…`; further over, the build stops in words (protect less, or raise BODY_TRIS). The ship's triangle budget still applies.
- **Face sizes** (Nov 8): the build logs lo_body's median, 99.9th-percentile and largest face area. It stops in words when the largest face is over 4000× the median or the 99.9th percentile over 1000× (healthy builds reach about 1500× and 560×; Hearthwing grown's flattened chest was 9800× and 1485×), naming where the largest face is.
- **Heat weights** (Nov 7): when Blender's heat solve fails (it fails quietly on big bodies), the rig stage retries on coarser proxy bodies: the voxel × 1.6, then × 2.4, scaled up with the breed's size; `VOXELS['proxy']` sets the base. Only when every proxy fails does it fall back to distance weights. The log says `WEIGHTS: heat weights, solved on …` or `WEIGHTS: DISTANCE WEIGHTS …`, and stats_rig.json has `weights` {method, source}. Healthy builds are unchanged: the first solve still runs on the usual proxy.
- **Finite numbers** (Nov 7): the build stage (every `hi_*` / `lo_*` mesh: positions, normals) and the export stage (the shipped meshes: positions, normals, skin weights) stop in words if any value is NaN or infinite, naming the object and the count (Hearthwing's frills got NaN positions from a negative number raised to a fractional power). `tools/art/ultra.ts` checks the Blender export and every .glb it writes (positions, node transforms) before writing it.
- Every bake also writes `atlas_coverage.png` (emission 1 on every source, the same cage and rays): 0 where every ray missed, e.g. the deepest crevices, where the colour baked black and the roughness 0 (a mirror in the game: green flecks at Nimbusheep's wool seams). `tools/art/ultra.ts` hands it to `ultra-pad`, which treats those island texels as unwritten and fills them from their neighbours (the strip's tiles are never touched). A breed without misses ships byte-identical. The bake log says `coverage: N island texels where every bake ray missed`.
- `art:ultra-review` and `art:lineup` dress each mesh with the game's own rules (src/art3d/ultra/parts.ts: partKind, partVisible, glowOf, softFinsOf; the film material's luminance caps and the ORM-alpha glow from src/art3d/perf), reading the sidecar beside the .glb, so the sheets show what the phone shows. Each run takes a free port, so two builders' reviews can run at once.

## Build slots
At most two full builds run at once (shape previews don't count). **Start every full build through the slot lock**, which waits for a free slot and frees it when the build ends, however it ends:
`tools/blender/slot.sh npm run art:ultra -- <breed> --blender [...] > <log> 2>&1 &`
(slots are directories in `tools/blender/out/.slots/`; a slot whose holder has died is reclaimed). This replaces the process count below, which races when two builders check at the same moment. The old check, for reference: `(Get-CimInstance Win32_Process -Filter "Name='blender.exe'" | Where-Object { $_.CommandLine -match 'build_ultra' }).Count`; the query sometimes returns nothing at all: **count an empty result as busy**, not as zero (wrap it as `@(...).Count`, and treat a failed or blank answer as 2).

## Grown forms
A grown form is its own look, built and shipped beside the young one:
- Recipe `breeds/<breed>_grown_ultra.py` with `ID = '<breed>-grown'` (e.g. `'hearthwing-grown'`), `LOOK = f'{ID}-ultra'`, its own `HEIGHT_UNITS` (CONTENT: grown Hearthwing about 2 × Puddlepup) and variants named `'<short>-<breed>-grown'`. Share code with the young form by importing it (`from monsters.breeds import hearthwing_ultra as Y`) or a common module (`hearthwing_parts.py`).
- Out folder `tools/blender/out/<breed>-grown-ultra/`; rig `<breed>-grown_rig`; ships to `public/models/monsters-ultra/<breed>-grown.{glb,json,lite.glb}` (+ its textures `<breed>-grown_*.ktx2/webp`).
- Commands take the look id: `npm run art:ultra -- hearthwing-grown --blender [--quick]`, `npm run art:shape -- hearthwing-grown`, `npm run art:ultra-review -- hearthwing-grown`, `npm run art:lineup -- hearthwing hearthwing-grown` (`<look>` → recipe module `<look with _ for ->_ultra`).
- References: the young form's folder (`chatgpt/monsters/09-hearthwing/`) and its `grown-*.png` pictures (`grown-1-hero`, `grown-2-turnaround` (four views: front, side, back, wings spread), `grown-3-faces`, `grown-4-details`); the review sheet picks them and crops the four-view turnaround.
- The game's registry (`src/art/ultraLooks.ts`) lists breeds only; a grown form needs its own entry there when the game uses it.

## Names that ship
Bones: `root, hips, spine, chest, neck, head, jaw, ear.{L,R}.{1,2}, tail.1..N, thigh/shin/foot.{FL,FR,BL,BR}, eye.{L,R}`, plus `mane.i` / `<name>.i` and `prop.<name>`; with the batch-2 options `neck.1..N` (instead of `neck`), `trunk.1..N`, `bud.1..n`, `wing.{L,R}.1`, `.2`, `.f1..fK`. Sockets also `socket_trunk`, `socket_wing_L` / `_R` with those options.
Biped bones (`plans/biped.py`): `root, hips, spine, chest, neck` (or `neck.1..N`), `head, jaw, ear.{L,R}.{1,2}, upperarm/forearm/hand.{L,R}, thigh/shin/foot.{L,R}, tail.1..N, tail.puff, eye.{L,R}`, plus each cape or mane chain `<name>.i`, `wing.{L,R}.1`, `.2`, `.f1..fK` and `prop.<name>`. Biped sockets add `socket_hand_L` / `_R` and `socket_foot_L` / `_R` (`socket_paw_L` / `_R` sit at the hands).
Floater bones (`plans/floater.py`): `root, hover, hips, chest, head, jaw, eye.{L,R}`, plus `upperarm/forearm.{L,R}` (arms) or `hand.{L,R}` (floating hands), each chain `<name>.i` and `prop.<name>`. Floater sockets add `socket_core`, `socket_hand_L` / `_R` and `socket_<chain>`.
Shelled bones (`plans/shelled.py`): `root, hips, chest, neck.1..N, head, jaw, eye.{L,R}`, plus `leg<i>/shin<i>/foot<i>.{L,R}`, `arm/forearm/claw/pincer.{L,R}` (claws), `stalk{L,R}.1..2` and `visor.{L,R}` (stalks), `tail.1..N`, each chain `<name>.i` and `prop.<name>`. Shelled sockets add `socket_shell`, `socket_claw_L` / `_R` and `socket_<chain>`.
Blob bones (`plans/blob.py`): `root, body, hips, chest, head, jaw, eye.{L,R}`, plus `sac`, `tongue.1..N`, `leg<i>/shin<i>/foot<i>.{L,R}`, each tentacle and chain `<name>.i` and `prop.<name>`. Blob sockets add `socket_core`, `socket_sac`, `socket_tongue`, `socket_<tentacle>` and `socket_<chain>`.
Construct bones (`plans/construct.py`): `root, hips, head` (the lid, or a head on `neck.1..N`), `eye.{L,R}`, plus `jaw` (the 'neck' mode), `tongue.1..N`, `leg<i>/shin<i>/foot<i>.{L,R}`, `spin.<name>`, each chain `<name>.i` and `prop.<name>`. Construct sockets add `socket_core`, `socket_tongue`, `socket_<spinner>` and `socket_<chain>`.
Serpent bones (`plans/serpent.py`): `root, hips, spine.1..K, neck.1..N, head, jaw, tail.1..M, eye.{L,R}`, plus `tongue.1..N`, each chain `<name>.i` and `prop.<name>`. Serpent sockets add `socket_core` (the anchor), `socket_tongue` and `socket_<chain>`.
Meshes: `lo_body` body, `lo_eyes` eye, `lo_fins` fin, `lo_cards` card, `lo_tuft` lock, `lo_props` prop, `lo_props_<short>` prop (a variant's own; only those built).
Per variant: bake pass and `atlas_<short>.png`, attribute `paint_<short>`, cards' colour `Col_<short>` → glTF `COLOR_1`, `COLOR_2`, … in `VARIANTS` order, holder mesh `__variant_<id>`, its own props `lo_props_<short>` (sidecar `variants[vid].meshes`), review sheet `variant_<short>.png`. The Lite copy (`<breed>.lite.glb`, ≤ 12k triangles in all): no cards, no tuft (unless `LITE_KEEP`); the membranes simplified to a quarter; props kept as they are up to 2.4k triangles in all, else simplified to fit; the body gets the rest. `npm run art:ultra -- <breed> --lite-only` rebuilds just it from the last ship.

## Commands
- Shape preview (a minute; flat colours): `blender -b --factory-startup --python tools/blender/monsters/shape_preview.py -- --breed <breed>_ultra --out <dir>`
- Full build and ship: `npm run art:ultra -- <breed> --blender --cpu` (add `--quick` for a fast look); review: `npm run art:ultra-review -- <breed>`; lineup: `npm run art:lineup -- <breed…>`. Shape preview through npm: `npm run art:shape -- <breed>`. Every command takes a grown form's look id too (`hearthwing-grown`).
- New clips without a new mesh: `npm run art:ultra -- <breed> --blender --stages clips,export` (the build, bake and rig stay; the textures re-encode to the same bytes).
