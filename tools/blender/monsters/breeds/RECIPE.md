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
| `PLAN` | `'quadruped'` (`plans/quadruped.py`), `'biped'` (`plans/biped.py`: see *Biped plan* below) or `'floater'` (`plans/floater.py`: see *Floater plan*) |
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
  - `'slam'`: both fists rise overhead, then come down together to the ground in front, hips dropping, a beat held (Grumblestone). `slam` [the plan's own points] = `{'over': (x, y, z), 'ground': (x, y, z)}` places the left fist (mirrored) instead: `over` in the rest pose, carried by the chest; `ground` in model space. Grumblestone raises its fists high and wide overhead and lands them well in front of its big feet (the plan's ground point is 0.35 × the leg ahead, on its toes).
  - `'thrust'`: a fencing lunge with the tail's blade. The tail swings round under the left arm to point straight ahead while the left foot steps out and the cape flares (Quillion). `thrust_lift` [14°] raises the blade.
  - `'pounce'`: a leap from a deep crouch, the body stretched out, both claws reaching forward (Gloomgrin).
  - `'charge'`: head down and low, then a hard drive with the head leading and the arms tucked (Pluckrex grown).
  - `'gust'`: the wings rise and spread, then one great downbeat with both palms thrust out (Plumdrake). Without wings, the palms alone.
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
| Ashwraith | ≈ 37 (arms 4, a hood tip 3, about 8 wisps × 3) |
| Zipwisp | ≈ 16 (spark wings 2, a 3-bone bolt tail, a 2-bone tuft) |
| Mirrorkin | ≈ 22 (hands 2, a handle 1–2, two 3–4-bone cloak panels, a crest prop) |
| Frostlance | ≈ 17 (a 3-bone tail with its fluke, 2 fins, a tusk prop) |

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
Meshes: `lo_body` body, `lo_eyes` eye, `lo_fins` fin, `lo_cards` card, `lo_tuft` lock, `lo_props` prop, `lo_props_<short>` prop (a variant's own; only those built).
Per variant: bake pass and `atlas_<short>.png`, attribute `paint_<short>`, cards' colour `Col_<short>` → glTF `COLOR_1`, `COLOR_2`, … in `VARIANTS` order, holder mesh `__variant_<id>`, its own props `lo_props_<short>` (sidecar `variants[vid].meshes`), review sheet `variant_<short>.png`. The Lite copy (`<breed>.lite.glb`, ≤ 12k triangles in all): no cards, no tuft (unless `LITE_KEEP`); the membranes simplified to a quarter; props kept as they are up to 2.4k triangles in all, else simplified to fit; the body gets the rest. `npm run art:ultra -- <breed> --lite-only` rebuilds just it from the last ship.

## Commands
- Shape preview (a minute; flat colours): `blender -b --factory-startup --python tools/blender/monsters/shape_preview.py -- --breed <breed>_ultra --out <dir>`
- Full build and ship: `npm run art:ultra -- <breed> --blender --cpu` (add `--quick` for a fast look); review: `npm run art:ultra-review -- <breed>`; lineup: `npm run art:lineup -- <breed…>`. Shape preview through npm: `npm run art:shape -- <breed>`. Every command takes a grown form's look id too (`hearthwing-grown`).
- New clips without a new mesh: `npm run art:ultra -- <breed> --blender --stages clips,export` (the build, bake and rig stay; the textures re-encode to the same bytes).
