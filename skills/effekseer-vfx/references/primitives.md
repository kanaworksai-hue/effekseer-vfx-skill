# Recipe code and primitives

Contents: recipe files · `effect()` fields · primitives · helpers · layer fields · units

## Recipe files

One effect per file: `vfx/src/VFX_<Name>.py` defines `recipe()` returning `effect('<Name>', ...)`. The ID
`VFX_<Name>` must equal the file name. Files starting with `_` are shared helpers (`from _palette import *`).
Sources are reloaded on every command. `from vfxkit.primitives import *` brings in every primitive, the helpers
below, `WHITE`, `fade`, `ramp`, `walk` and `math`.

Every primitive returns a plain layer dict; override or add any field with `| dict(...)`. Textures are named by
stem (`'T_Glow01'`) and resolved in `vfx/textures/processed/`. Layers are drawn in list order: **later layers draw
on top** (the Godot plugin ignores ZWrite between effect layers).

## `effect()` fields

`effect(id, name, category, element, duration, layers, attach='impact', peak=.1, impact=0, light=(1,.85,.6), loop=False, design='', delivery=None, flight=None, arc=None, hold=None, inputs=None, scale=None)`

| Field | Meaning |
|---|---|
| `category` | `hit`, `slash`, `projectile`, `element`, `status`, `boss`, ... (sets the lint budget) |
| `element` | `physical`, `fire`, `ice`, `lightning`, `dark`, `holy`, `poison`, ... (element-difference and motion checks) |
| `duration`, `peak` | seconds; `peak` is the contact/release moment the Lab flash, kick and target reaction use |
| `attach` | anchor: `ground`, `body`, `impact`, `caster`, `caster_ground`, `projectile` |
| `impact`, `light` | 0–1 strength and RGB of the Lab's stage flash and camera kick (demo staging only) |
| `delivery` | how a game performs it: `SELF`, `MELEE`, `TARGETED`, `dict(kind='area')`, `dict(kind='projectile')` for the projectile itself, `dict(kind='projectile', projectile='VFX_X')` for its impact, `BEAM` or `dict(kind='beam', charge='VFX_X')` for a held beam (the Lab plays the charge first) |
| `flight`, `arc` | projectile only: reference flight seconds and lob height in metres |
| `hold` | beam only: seconds the Lab fires it before release; `infinite` layers emit until then |
| `inputs` | default values of the game inputs `@In0..@In3` that `bind` equations read; beams use `beam_inputs(length)` |
| `scale` | `'giant'`, `'kaiju'`, a number or `{'world','time','budget'}`: build a character-scale recipe for a larger world ([scale](scale.md)) |
| `design` | one sentence of what the player sees; shown in the Lab and given to reviewers |

## Primitives

**Think volume first, texture second.** Bodies, shock waves, crystals and pillars should be meshes or rings in a
tilted 3D plane rather than camera-facing cards. Keep camera-facing sprites for things that are screen-space by
nature: contact stars, glows, sparks and smoke puffs (stacked into volume).

| Primitive | Use | Key native feature |
|---|---|---|
| `flash` / `glow` | contact star, soft bloom under a shape | single-value F-curve scale |
| `shadow` | dark backing behind an additive core | Blend soft disc peaking 1–2 frames after the flash |
| `radial_sparks` | sparks, needles, rising streaks | sphere/circle emission + eased `travel` + DirectionalBillboard |
| `spark_burst` | hit/explosion sparks in three tiers | long fast streaks (6–10 frames), main body, ~20 % heavy sparks that bounce given `floor` |
| `motes` | embers, frost dust, magic motes, inward gathering | as above + turbulence force |
| `shock_ring` / `tilted_ring` | shock wave, rising halo, shrinking ring; ring in a 3D plane | Ring renderer with eased inner radius; melee tilt `(0,58,0)` crosses a left-to-right blow |
| `slash_arc` | blade arc | Crescent Ring with eased start/end angle sweep + dissolve |
| `wisps` | broken energy strokes, vortex strands, ground licks | Crescent Ring + `T_WispTrail01`, random tilt and size per emission, erosion starts above 0 so it is never a full ring |
| `orbit_band` | accretion disk, orbiting rune ring | Ring in a tilted plane, noise flowing round it; `arc=(-90,90)` far half, `(90,270)` near half |
| `smoke` | smoke, fog, dust, dark residue | painted smoke flipbook `T_SmokeSheet01` + light erosion; `texture='T_Smoke02'` for a single still puff — ice mist keeps the still puff so it differs from fire's rolling smoke |
| `billow` | fireball, the same billow as smoke | painted 4×4 flipbook `T_ExplosionSheet01` played once + `ramp` colour stops |
| `flame` | flame tongues, fire walls, ground fire | the explosion flipbook growing from its base, cooling white → colour → dark, eaten by noise with a hot rim (no clip-art flame silhouette) |
| `decal` | seals, cracks, scorch marks | ground-plane sprite, depth tested |
| `standing` | spikes, bolts, beams | YAxisFixed sprite pivoting at its base |
| `column` | light pillar, aura | procedural cylinder + scrolling streaks + static alpha gradient + fresnel |
| `mesh` | spheres, cones, cylinders | procedural model + falloff; `model={...}` for extra procedural fields |
| `crystal` | ice spikes, shards, lances | six-sided cylinder tapering to a point + cellular texture + fresnel edges |
| `shell` | shock bubble, implosion, release | front faces only, fresnel `pow<1` lights only the rim, eased expansion |
| `shell_fragments` | real geometric break-up of a shell | six partial sphere sheets (AngleBeginEnd) that separate and tumble |
| `heat_haze` / `distortion_ring` | heat shimmer, refractive shock wave | `BackDistortion` screen refraction |
| `slice_line` | long thin line at release | `T_Streak01` shooting from 35 % to full length while thinning; `width` is the visible thickness |
| `spray(end)` / `debris` | directional spray along the shot, dark tumbling chunks | non-rotating emission + world-direction `travel` box; Blend `T_Shard01` with gravity, can land |
| `decay(layer, color)` | glow → grey smoke afterimage | copy as Blend grey, `lag` frames later, life × `stretch`, no emissive, slower flow |
| `beam(name, core, body, rim, width=.5, ...)` | sustained beam the game aims and sweeps (breath weapon, laser, death ray) | axial billboards (`YAxisFixed`, pivot at the base) stretched to `@In0` and widened by `@In1` through `bind`; `T_BeamSection01` cross-section, noise streaming outward, mouth and end flashes, end sparks, optional `steam` and `scorch` left in world space ([godot](godot.md#beams)) |
| `charge_chain(name, anchors, color, hot, step=4, ...)` | arcs lighting a chain of points one after another (dorsal plates, coils, a ley line) | node glow + pop per anchor at `delay + i*step`; painted `T_ArcStrand01` arcs on a `DirectionalBillboard` aimed at the next anchor by an imperceptible velocity, re-struck mirrored every `restrike` frames until `until` |

## Helpers

| Helper | Meaning |
|---|---|
| `ramp((0,c0),(30,c1),(100,c2))` | colour over life as 3–5 stops → `color_curve` (a two-colour lerp reads as a tint) |
| `fade(color, alpha=0)` | same RGB, new alpha |
| `POP`, `DISSOLVE` | scale curve that snaps then drifts; cutoff easing that holds (ease-in) then erodes |
| `sustain(layer, interval)` | projectile emitter: one instance every `interval` frames until release |
| `held(layer, interval)` | sustained cross-fade: an instance every `interval` frames, each fading in and out over `interval`, so two always overlap and sum to a constant (a steady beam with no loop seam) |
| `beam_inputs(length, power=1)`, `BEAM_LENGTH`, `BEAM_POWER`, `BEAM` | the beam's default inputs, the `@In0`/`@In1` names its bind equations use, and its delivery |
| `TRAIL` | inherit position/rotation/scale only when created: the layer stays on the path |
| `slash_set(colors, roll, sweep=(110,260), radius=1.5, offset=(0,0,.5), lean=-18, delay=1, life=14)` | one blade at three widths: a wide dim afterimage two frames late, a saturated body, a thin white-hot edge (`slash_arc`), a refraction arc, and a painted cel crescent (`T_Slash02`, `billboard='Fixed'` in the blade's plane, rotated by the measured `SLASH02_BULGE`); `colors` = (afterimage, body, edge) |
| `swing(layers, yaw, pitch=0)` | wrap blade layers in a `renderer='None'` pivot so the arc cuts through 3D space; yaw about ±30–40° reads as an ellipse rather than a screen crescent |
| `contrast_pair(layer)` | one fixed sprite plus a geometry-identical Blend underlay (see [layering](layering.md)) |
| `lifetime(layer)`, `budget(layer)` | last frame a layer or its children can be alive; instance count |

## Layer fields

Beyond PVA, scale and colour the compiler supports: `collide` (floor bounce), `soft` (fade distance in world units
where the particle meets opaque geometry; verified in Forward+, see engine conventions), `bind` (position/scale
recomputed every frame from the game inputs, below),
`size` / `size_end` / `size_curve` (uniform scale), `color_end`, `color_curve`, `travel` (eased displacement), `spawn`
(sphere, circle, line emitters), `forces` (gravity, turbulence, vortex), `alpha_texture` + `cutoff` + `edge`
(dissolve with a hot rim), `distortion_texture`, `blend_texture`, `falloff` (fresnel), `flipbook`, `pivot`,
`ring{...}`, `inherit`, `track_size`, `material` (`BackDistortion`), `children`. `vfx layer-schema` lists every
accepted key; unknown keys fail with a spelling suggestion. Anything else must be added to the compiler with a
save/open read-back test, not written as raw property paths in a recipe (procedure: [engine conventions](engine-conventions.md#extending-the-compiler)).

### `bind`: values the game drives

`bind={'position': [x, y, z], 'scale': [x, y, z]}` replaces the layer's position or scale with a Fixed vector that
an Effekseer dynamic equation recomputes **every frame** from the game inputs `@In0..@In3` (`handle.set_input()` /
`Vfx.beam()` in Godot). Each component is a number, an equation string (`'@In0'`, `'@In0 * 0.5'`) or a product
`[k, '@In1']` whose constant `k` scales with the recipe's world scale while the input stays a world value. The
recipe must give `inputs=[...]` defaults for every input it reads. A bound scale cannot be combined with
`size`/`scale_*` fields and a bound position not with `travel`/`velocity`; children follow a bound parent.

## Units

Layer `life`, `delay`, `interval`: 60 FPS frames. Velocity and acceleration: units per frame; gravity: units per frame².
Angles: degrees. Colours: RGBA 0–255. Curves (`size_curve`, `color_curve`...): `[[percent_of_life, value], ...]`.
`cutoff` (dissolve threshold, 0..1): a number (fixed), `dict(start=a, end=b, easing='Linear')` (over the particle's life;
`EaseIn*` holds the shape first), or a curve, which the compiler fits to the closest easing — an FCurve threshold does
not animate in Godot (see [engine conventions](engine-conventions.md)).
Manifest `duration` and `peak`: seconds. Random ranges are `[min, max]`.
