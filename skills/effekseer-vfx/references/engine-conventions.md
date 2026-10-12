# Verified engine conventions (Effekseer Core 1.80.7 + EffekseerForGodot4 1.80.5.1)

Each item below was confirmed in real renders. Use them as they are; do not re-guess axes, units or blend
behaviour. When you confirm a new convention, add it here with how it was measured.

Contents: angles and axes · forces and motion · meshes and fresnel · textures and flipbooks · inheritance and
lifetime · game inputs and dynamic equations · rendering, HDR and the Lab · anchors and placement · extending the
compiler

## Angles and axes

- **Ring angles**: 0° points up, 90° points left, increasing counter-clockwise. A swept arc is centred on the anchor
  by offsetting the ring centre against the middle of its sweep.
- **Sprite Z rotation** is counter-clockwise. Never eyeball a painted shape's orientation: `vfx texture-info <name>`
  reports coverage, bounding box, border contact, principal orientation and the bulge direction of a crescent in the
  same convention (+x is 0°, counter-clockwise). Use the measured angle in the recipe. Example: `T_Slash02` measures
  a 108° bulge and `slash_set()` uses `SLASH02_BULGE = 105`; re-measure and update the constant if you replace it.
- **`billboard='Billboard'` ignores Z rotation** (a sprite with `rotation=[0,0,90]` stays upright). Sprites that need
  a roll use the default `RotatedBillboard`.
- **Sphere emission with `rotate=True`**: the particle's local +Y points outward, so `travel.end=[0,d,0]` flies out
  and a negative value draws in.
- **Circle emission (default Y axis) with `rotate=True` is different**: Core builds `Translation(r,0,0)*RotationY(angle)`,
  so local **+X** points outward and +Y stays up. Smoke rolling out along the floor needs `travel.end=[[d0,d1],0,0]`;
  `[0,d,0]` turns it into a column rising straight up. With `rotate=False` the displacement is in world directions
  (use that for rising particles).
- **Sphere emission with `rotate=True` also rotates PVA `velocity`**: `velocity=[0, v, 0]` flies along each
  particle's random spawn direction, not up. A smoke column emitted that way drifted sideways and sank (the review's
  `sinks` flag); `spawn=dict(shape='Sphere', radius=[...], rotate=False)` keeps `velocity` in world directions.
- **Axial billboards**: `billboard='YAxisFixed'` with `pivot='bottom'` is a quad from the origin along local +Y that
  turns about that axis to face the camera — a beam that stays wide from any angle except straight down its axis.
  `DirectionalBillboard` aligns +Y with the particle's motion; with an imperceptible velocity (1e-4 units/frame,
  `charge_chain`) it aims a stationary sprite at any point without Euler angles (measured: arcs met every anchor of
  a 7-point chain on a curved spine).
- **`travel.end` is an absolute local position**, not an offset from `position`, and `rotate=True` emission rotates
  that local frame too. Put floor-rolling smoke under a `renderer='None'` pivot whose `position` is at floor height;
  for world-direction displacement use `spawn rotate=False` (`spray`).

## Forces and motion

- **Drag only damps velocity accumulated by force fields, not PVA velocity.** "Burst, then hang" must be `travel` with
  an EaseOut, not velocity + drag.
- **Gravity is in units per frame².** Falling sparks 0.001–0.002, rocks 0.004, rising smoke 0.0003–0.0006. One order
  of magnitude more and particles leave the screen (lint rejects above 0.01).
- **Floor collision `collide`**: world coordinate system; `height` is a world height (the Lab floor is 0.02). From an
  impact point 1.35 m up with gravity 0.0015 nothing reaches the floor within 20 frames, so bouncing only matters for
  explosions, boss slams and things that land.
- **Track + Circle `Order` emission does not make a spiral**: it advances one segment per frame, so at flight speed
  the pitch stretches into a flat zigzag. Use `wisps` strokes at random tilts around the head instead.

## Meshes and fresnel

- **Procedural cylinders and cones** span `DepthMin` to `DepthMax` along their axis; `mesh()` stands them on the
  origin. **Spheres** use a normalised depth of -1..1: size them with `scale_start`, never with Depth.
- **A Cone points down** (its base is at the +Y end). For a crystal pointing up use a `Cylinder` with `radius2≈0`
  (`crystal()` does). `Mesh/Divisions/X=6` makes a hexagonal prism. `ShapeNoise/WaveNoisePower` turns a sphere into
  a lumpy liquid glob. Large spheres need `rings ≥ 24` or the silhouette is faceted.
- **Procedural model V runs top to bottom.** A scrolling colour texture must tile (`T_NoiseStreak02`); keep gradients
  in a non-scrolling alpha texture (`T_GradientV01`) or a hard seam appears.
- **Falloff**: `begin` is the centre facing the camera, `end` is the edge, and a larger `pow` makes the `begin` area
  **smaller** (red/green test: at pow 8 almost the whole sphere shows `end`). A thin bright rim (fresnel, shock
  shell) uses `pow` 0.25–0.5. Draw spheres front faces only with `culling='Front'` (Effekseer naming: `Front` shows
  the front; `Double` lights the inner back faces as edge too and the sphere turns solid). Shields light the edge;
  pillars make the edge transparent.
- **Model layers with a colour texture or a standing cutoff + edge** render as grey blotches in the Godot plugin on
  shell spheres. Use a flat colour + fresnel and dissolve only at expiry; for a visible break-up use
  `shell_fragments` (real geometry) rather than a cutoff on the whole shell.
- **No camera-facing "vortex sticker"** for black holes, dark orbs or charges: put rings in tilted planes with
  `orbit_band` and stack them in draw order — far half ring → core (Blend black disc or bright core) → photon ring →
  near half ring — so the near half passes in front of the core. The plugin **ignores ZWrite between effect layers**
  (a depth-writing sphere plus depth-tested rings had no effect); occlusion comes only from list order. Spin a ring
  surface with `alpha_scroll` so streaks flow round it, not with Z spin.

## Textures and flipbooks

- **UV distortion textures must be opaque RG offset maps** (`T_Distort01/02`). A white-on-alpha mask used as a
  distortion map distorts nothing.
- **Alpha textures read the alpha channel**; every `T_Noise*` mask works directly for a `cutoff` dissolve.
- **Dissolve thresholds animate only as an Easing.** Measured in Godot renders (EffekseerForGodot4 1.80.5.1, Lab and a
  Mobile-renderer game): with `AlphaCutoffParam/Type = FCurve` (Percent or Time timeline) the threshold stays at its
  first key for the whole life, so the shape never erodes; with `Type = Easing` it animates, and the easing type
  (`Linear`, `EaseInQuadratic`, `EaseInCubic`, `EaseInQuartic`, `EaseInQuintic`, `EaseOut*`) shapes it. Core clamps
  the start and end thresholds to 0..1, so a hold-then-erode dissolve is an ease-in, not a negative start. The
  compiler always writes an Easing: `cutoff=dict(start=a, end=b, easing='EaseInQuadratic')` for exact control, or a
  curve `[[percent, value], ...]`, which it fits with the closest easing (`cutoff_easing`). Read-back alone does not
  show this; look at the strip.
- **Flipbook integers**: `flipbook.frame_length`, `x` and `y` are integer Core properties and must be positive integers
  (4.5 is rejected natively; the field validator catches it first). Lengthen playback with integer frame lengths
  and life together.
- **No UV distortion on a flipbook**: `distortion_intensity` is measured in whole-texture UV, so 0.12 on a 4×4 sheet
  shifts half a cell and samples the neighbouring frames — fire gets cut into hard-edged blocks. Lint rejects it;
  use a single-frame texture when you need distortion.
- **Flipbook sheets**: an image model can produce a whole 4×4 sequence (1024², 256² cells) with usable continuity.
  Process it with `vfx process-texture <original> <output> --size 1024 --grid 4 4`: cells keep their position (no
  crop, no re-centring, which would make the animation jitter) and each cell edge is feathered against bleeding.
  `frame_length` ≈ life / 16; one-shot with `loop='Once'`, looping fire with `Loop` and a random start frame.
- **One explosion sheet, two layers**: additive fire (ramp white → yellow → orange → dark red → out) plus a Blend dark
  smoke layer delayed by about 8 frames. The smoke must be **listed before** the fire (drawn behind it), otherwise it
  punches a black hole through the fireball.
- **Erosion edge colour** is added over the cooled red; a yellowish edge turns olive. Fire uses `(255,80,15)` with
  `scaling≈2`.
- **Wisp strand texture**: the painted strand band is cropped by rows at full width (so it tiles horizontally),
  resized to 512×256 with alpha = luminance. The default centred processing adds side margins and breaks the tiling.

## Inheritance and lifetime

- **Inheritance**: Core's default `LocationEffectType` is `Already` (follows the parent every frame). `WhenCreating`
  takes the parent transform only at birth, so particles stay put while the handle moves — projectile trails rely
  on it. `renderer='Track'` joins successive instances of one layer into a ribbon; with `WhenCreating` it is a
  continuous trail.
- **`EffekseerEmitter3D.stop_root()`** stops new emission; existing particles finish their own lives before
  `finished` fires.
- **Child timing**: a child's generation is timed from its parent instance's creation, not its death. A
  `renderer='None'` parent can spin its children, and children easing to the centre with `travel` make a spiral
  infall.
- **Random size cannot take a curve**: a random `size` / `scale_start` range combined with `size_curve` / `scale_curve`
  fails to compile (the compiler multiplies the curve by a fixed start scale; lint rejects it). Vary size with a
  second layer.

## Game inputs and dynamic equations

- **`bind` works at runtime in the Godot plugin.** A Fixed location or scale with a dynamic equation
  (`@O.y = @In0`) is recomputed every frame: a probe changed `@In0` from 3 to 9 to 5 on a playing handle and the
  beam's length and end flash followed within 2 frames; rotating the emitter re-aimed it. The compiler writes the
  equations into `Core.Dynamic.Equations` (identical code is shared) and checks them after save/open.
- **New handles start from the .efk input defaults** (the recipe's `inputs`): on the first simulated frame the kaiju
  beam's hit-point spray appeared at the default 160 m instead of the real end point. `Vfx.play()` / `Vfx.beam()`
  therefore push the handle's inputs right after creating it, and `CombatVfxHandle` pushes them again every frame. (An
  early probe saw zeros only because its .efk had no defaults saved.)
- **Held bodies**: a beam body is a `held()` cross-fade (an instance every interval, life 2×interval, fades of one
  interval each) rather than one long-lived instance, so `release()` (`stop_root()`) ends it on time: the kaiju beam
  narrowed and was gone within about 15 frames of its release in the strips, and `TestApi.gd` checks that a released
  beam frees itself.

## Rendering, HDR and the Lab

- **Screen distortion `material='BackDistortion'`** works in the Godot plugin (`hint_screen_texture`); `distortion` is
  the strength (0.4–1.2). It refracts only opaque objects (floor, dummies), not other effect layers. On a dark plain
  stage it shows only on the floor ring and dummy edges — zoom into frames to see it. The effect must still work
  with distortion off.
- **Lab stage and HDR bloom**: the default stage is a lit deep slate blue (background `1a2433`, floor `1d2733`,
  ambient 0.75, key 1.5, fill 1.0). In Forward+ the plugin's additive / emissive output lands in the HDR buffer.
  Measured with lit stand-in characters, dummy highlights peaked near 3.4× while effect cores exceeded 8×, so Glow
  ramps by `smoothstep(threshold, threshold + hdr_scale)` from 2.8 to fully on at 6.0, intensity 1.5, strength 1.1,
  additive before tonemapping, five blur levels 1.0/1.0/0.85/0.6/0.35, Filmic white 4 so cores burn white earlier,
  `glow_bloom=0`. These numbers were measured with lit, toon-shaded character stand-ins; the default Lab's capsule
  dummies have not been re-measured against them, so treat the threshold as a starting point and re-measure the dummy
  peak (linear tonemap, read back at exposure 1/8) after changing stage brightness, dummy lighting or the stand-ins
  before moving the threshold. `godot --path vfx/godot -- --no-glow` disables the post-process for comparison. The recipe primitive
  `glow()` is a texture layer, not this HDR post-process. Re-render the whole overview after stage changes.
- With strong bloom, effects whose contact is legitimately white-hot report `washed out` on their peak frame; that
  lasts 1–3 frames — judge from the strip and do not weaken the contact just to silence the flag.
- **Soft particles `soft` work in Forward+** (EffekseerForGodot4 1.80.5.1, Godot 4.7.2). The plugin's shader samples
  `hint_depth_texture` and fades the particle over `soft` world units in front of the opaque depth. Measured on
  depth-tested cards half sunk into the Lab floor: without `soft` the brightness dropped from 206 to 81 within one
  pixel at the floor line; with `soft=0.3` it ramped 198 → 188 → 169 → 124 → 81 over about 9 pixels; a card in the air
  kept exactly the same colour with and without `soft` (216, 198, 155). A `soft` close to the particle size fades the
  whole card (lint warns). Only opaque geometry is in the depth texture: a transparent water surface must write
  depth (or have an opaque depth pre-pass) for smoke to soften against it. The Compatibility renderer has no depth
  texture: there `soft` made sprites almost fully transparent in an earlier Lab — do not use it with Compatibility.
- **The stage flash at scale**: Godot omni lights fall off as 1/distance (attenuation 1), so the Lab multiplies the
  flash energy by the stage scale, not its square (with the square a kaiju hit washed out the whole stage).

## Anchors and placement

- Lab anchors: `body` is 0.95 m above the floor, `impact` 1.35 m, `ground` 0. Floor layers in a `body`-anchored
  effect sit at about `y = -0.93`, in an `impact`-anchored one at about `y = -1.3`; written lower, a depth-tested
  decal disappears under the floor.
- Melee shock rings across the line of the blow use `tilt=(0,58,0)`: perpendicular to a left-to-right attack, seen
  in perspective as a vertical ellipse.

## Extending the compiler

The recipe fields are a curated subset of Effekseer. When an effect needs an engine feature the compiler lacks:

1. Make a reference node with the feature (or open an effect that has it) and find the property paths:
   `vfx discover` dumps every path of a fresh node with its type and enum values to `vfx/work/property_schema.json`;
   `vfx core property-list <file.efkefc> node/root/0` lists the paths of a real node.
2. **Read before writing**: `vfx core property-get <file> <path>` for the current value, then
   `vfx core property-set <file> <path> <json>` and `property-get` again to see what Core actually stored. Curves go
   through `vfx core curve-list` / `curve-set`, renderer panels through `settings-list` / `settings-set`.
3. Use only properties the current Core saves; do not rely on legacy fields that are only read on import.
4. Add the feature as a layer field in `scripts/effekseer_ai/authoring.py` (it must appear in `vfx layer-schema`),
   with a test that compiles a layer, saves, re-opens and reads the value back. Never write raw property paths into a
   recipe.
5. Render it and add the convention to this file with how it was measured.

