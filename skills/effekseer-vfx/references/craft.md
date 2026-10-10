# VFX craft rules

The rules every recipe is built on. Read them before writing or changing an effect, together with
[layering](layering.md), [timing](timing.md) and [skeletons](skeletons.md). The craft starting points here may be
adjusted to the user's style; the measured engine behaviour in [engine-conventions](engine-conventions.md) may not.

Contents: 1. Why "sticker" effects fail · 2. Time structure · 3. Element differences · 4. Projectiles ·
5. Irregular, multi-role effects · 6. Budgets

## 1. Why "sticker" effects fail

A static billboard that is recoloured, scaled up and faded out reads as a sticker. Five things make an effect read
as an effect; missing any one of them visibly lowers quality:

1. **Time structure**: anticipation → contact flash → body → secondary motion → dissipation. Contact takes 2–5
   frames; dissipation takes most of the duration.
2. **Value layering**: a white-hot core, a saturated body and a darker rim or residue — not one flat colour.
3. **Shape change**: the body erodes (alpha cutoff dissolve), wobbles (UV distortion) or sweeps open; scale and
   opacity alone are not enough.
4. **Varied speed**: particles burst out, then hang and droop (eased travel), never at constant speed in a line.
5. **Screen feedback**: bloom, an environment flash and camera kick on impact. The Lab derives them from the
   manifest `impact`, `light` and `peak`; the effect must still work with them switched off (`--profile bare`).

## 2. Time structure

| Phase | Frames (60 FPS) | How |
|---|---|---|
| Anticipation | 2–14 | Shrinking small glow, ground warning ring, thin guide lines. Heavier hits anticipate longer |
| Contact | 2–5 | `flash` white star, 1.5–2× the body size, gone immediately |
| Body | 8–20 | Painted shape pops in with `POP`, then erodes with `DISSOLVE`; `shock_ring` expands |
| Secondary | 10–40 | `radial_sparks`, `motes`, debris, flame tongues, with gravity / rise / turbulence |
| Dissipation | 20–60 | Smoke, embers and ground-crack glow cooling down slowly |

Heals, shields and buffs drop the contact frame and use a slow fade-in, rising motion and slight overshoot instead.
Charges invert the structure: a long inward build, then one flash at release.

## 3. Element differences

A recolour is not a new element. Two elements of the same category must differ in at least three of
**shape, motion, rhythm, material and secondary** (`vfx lint` warns when they do not):

| Element | Shape | Motion | Rhythm | Secondary |
|---|---|---|---|---|
| Physical | jagged burst, speed lines | radial burst, then droop | shortest, 0.3–0.65 s | sparks, dust |
| Fire | billowing fireball, flame tongues | rises, UV distortion | medium, long tail | rising embers, dark smoke |
| Ice | prisms, shards | overshoot, hold still, then shatter | has a hold | shards under gravity, sinking cold mist |
| Lightning | jagged polyline | does not travel; frame-swapped or mirrored strikes | main strike, return stroke, after-flicker on different frames | ground cracks, crawling arcs |
| Dark | vortex, black core | draws inward | long draw-in plus one release | alpha-blended black body, inward motes |
| Holy | seal, pillar of light | falls or rises vertically | eases in, sustains | rising halos, twinkles |
| Poison | cloud, bubbles | slow drift, sinking fog | slowest, about 2 s | rising bubbles, spores |

## 4. Projectiles (category `projectile`)

A projectile has no contact frame. Its impact is a separate effect, triggered by the `arrived` signal of
`Vfx.launch`. The projectile recipe declares `flight` (seconds of the reference flight) and, for a lob, `arc`
(metres of lift at mid-flight). The impact points back with `delivery=dict(kind='projectile', projectile='VFX_...')`.

- **Head** layers follow the handle (default inheritance). **Trail** layers use `inherit=TRAIL` (position, rotation
  and scale `WhenCreating`) and stay where they were born, so the path draws itself. Both are emitted with
  `sustain(layer, interval)` (`infinite`); the game calls `stop_root()` on arrival, after which only the trail's
  dissipation remains. Lint computes lifetimes as if released at `flight`; the budget counts life/interval
  instances alive at once.
- Make elements differ in flight rhythm and secondary motion too: fire flickers, rises and turns to dark smoke;
  ice is fast and straight, sheds shards that fall and leaves sinking mist; dark is an alpha-black core that drags
  needles inward with a contracting wake; poison lobs on an arc, drips, bubbles and leaves hanging fumes.
- Review strips fly the projectile from the caster to the target and end on arrival. Its centroid and radius
  follow the flight path rather than the element's motion, so the `sinks` and `expands while charging` flags are
  not checked for projectiles.

## 5. Irregular, multi-role effects

Techniques that make ranged and impact effects read as professional work (the shipped example pairs use them):

1. **Broken arcs, not full rings.** Build the body from several incomplete strokes, each sweeping 60–200° with its
   own radius, tilt and width, crossing each other. Use `wisps` (painted wisp strands with a standing erosion), not
   a clean `shock_ring`, `shell` or round billboard as the main shape.
2. **Several roles, each with a job.** A complex ranged skill may combine arcs, a white-hot core, a dark core, two
   spark tiers, motes, dust, debris and ground marks. State what each role is for; do not treat a layer count as a
   pass mark. Light hits and simple skills need far fewer.
3. **Dark elements must be visible.** On a dark stage, grey smoke and debris need values of about 90–150; a colour
   like `(40,10,70)` might as well not be drawn.
4. **Small accents with a purpose**: an orange underside on dark, a prism fringe on ice, a dark core under poison.
   5–10 % of the area is only a first try; decide the main and accent roles in the brief first.
5. **Glow decays into smoke.** `decay()` gives an additive stroke an alpha-blended grey copy that starts a few
   frames later and lives 1.6–2.2× as long: the light goes out first and the shape lingers as smoke.
6. **One long thin line.** At release, a `slice_line` across half the screen, aspect ratio above 40:1, for 8–15 frames.
7. **Direction.** Debris, sparks and droplets spray along the line of the shot (+X) and slightly up (`spray`,
   `debris`), not as a symmetric sphere.
8. **Ground feedback.** Rolling dust, debris that lands and bounces, scorch marks, cracks, pools and seals pin the
   effect to the floor.
9. **Impact frame.** A near-black full-screen card and the white flash go on the **same frame** (the black card listed
   before the flash). Putting the black card earlier makes the dark "expands while charging" check read it as growth.

## 6. Budgets

Particle instances (`particle_budget`, parent × children): normal hit ≤ 60, projectile ≤ 100, element skill ≤ 150,
boss skill ≤ 250. At most three screen-sized additive layers alive at once. Textures 128–256 px; painted main shapes
and seals 512 px; 4×4 flipbook sheets 1024 px.
