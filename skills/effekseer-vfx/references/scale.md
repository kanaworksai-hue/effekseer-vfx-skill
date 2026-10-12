# World scale: giants, kaiju, warships

Contents: why scale is more than size · declaring a scale · what converts · writing a scaled recipe · the Lab at
scale · checks that scale with the recipe · using scaled effects in a game · how it was verified

## Why scale is more than size

Every primitive, default and craft number in this skill is tuned for a ~1.75 m character in a 1 unit = 1 m world:
sparks fall at 0.0015 units/frame², a contact lasts 2–5 frames, the Lab anchors sit at 0.95 and 1.35 m. A monster
70 m tall needs the same effects 40 times larger — and **slower**. A scaled-up explosion that keeps its
character-scale timing reads as a miniature on a table: debris falls 40 m in a second, smoke boils like steam from a
cup. Film model-makers shoot miniatures at high frame rates for the same reason (Froude similarity: time grows with
the square root of size).

Games and films do not go all the way: at sqrt(40) ≈ 6.3x a kaiju blast would last ten seconds and a breath weapon
would feel sluggish. The profiles below stretch time by about world^0.25, so a 40x effect lasts 2.5x longer.

## Declaring a scale

Write the recipe at the Lab's character scale and add `scale` to `effect()`:

```python
return effect('Kaiju_Explosion', 'Kaiju Explosion', 'explosion', 'fire', 2.3, [...], scale='kaiju')
```

| `scale` | world | time | budget | for |
|---|---|---|---|---|
| `'character'` (default) | 1 | 1 | 1 | people, creatures up to ~3 m |
| `'giant'` | 8 | 1.7 | 2 | 10–20 m giants, siege machines, mechs |
| `'kaiju'` | 40 | 2.5 | 3 | 50–100 m monsters, warships, city-scale hits |
| a number, e.g. `16` | 16 | 16^0.25 = 2.0 | 16^0.3 | your own size; time and budget follow the curve |
| `{'world': 40, 'time': 1.5, 'budget': 2}` | as given | as given | as given | an exact profile (a game that wants faster kaiju) |

`effect()` converts the recipe immediately and records the profile under `recipe['scale']`; the manifest carries
it, so the Lab and `Vfx.gd` know the effect's size. Brief `beats` and every frame you read in a review are frames of
the **built** (converted) timeline: a contact authored at frame 4 is at frame 10 in a kaiju strip.

## What converts

| Group | Fields | Conversion |
|---|---|---|
| time | `life`, `delay`, `interval`, `fade_in`, `fade_out`, `flipbook.frame_length`; effect `duration`, `peak`, `flight`, `hold` | × time (`life` and frame lengths round down to whole frames so nothing outlives the stretched duration) |
| rates | `uv_scroll`, `alpha_scroll`, `distortion_scroll`, `blend_scroll`, `spin` | ÷ time |
| node scale | `size`, `size_end`, `scale_start`, `scale_end` (a layer with none gets `scale_start=[world]*3`) | × world |
| position | `position`, `travel.start/end`, `spawn.radius/start/end/noise`, force `position` | × world |
| motion | `velocity`, turbulence/vortex `power` | × world ÷ time |
| acceleration | `acceleration`, gravity forces | × world ÷ time² |
| world coordinates | `collide.height`, `soft` | × world, on every level |
| `bind` | numbers and the constant of `[k, '@In1']` | × world; equation strings (`'@In0'`) are world values the game supplies and stay |
| effect | `arc` | × world |

Only **top-level layers** are scaled in space: children live in their parent's coordinate frame, which is already
scaled, so only their time and world-coordinate fields change. A child with `inherit={'scale': 'NotBind'}` lives in
world units again and is scaled like a top-level layer. Ring and procedural-mesh geometry sits inside the node scale
and needs nothing.

## Writing a scaled recipe

- Think and tune at character scale: the anchors, sizes and speeds you know from the other examples still apply.
  Read the strips of the converted effect, not of a 1x version.
- Kaiju effects are mostly **mass**: more smoke and dust volume, slower secondary motion, longer dissipation, fewer
  but bigger pieces. The budget multiplier is for density, not for more noise.
- Anything that must touch a surface (dust skirts, ground fire) needs world heights: write them relative to the Lab
  anchors as usual (`floor = -1.3` under an `impact` anchor) and the conversion scales them.
- Painted textures keep their resolution: a 1024² flipbook that covers 100 m of screen is soft. Prefer photographic
  sheets with large forms (see [realism](realism.md)) and stack two or three puffs instead of one giant card.

## The Lab at scale

The Lab reads the selected effect's `scale.world` and scales the whole stage about the world origin: platform,
floor, dummies (70 m capsules at kaiju scale), the camera position, near/far planes, shadow distance, the stage flash
(light energy grows with distance, Godot omni lights fall off as 1/distance) and the camera kick. The framing is
identical to a character-scale strip, so the review metrics — measured in stage heights — and the reviewer's eye
compare across scales. The subtitle shows `KAIJU x40`.

## Checks that scale with the recipe

| Check | Scaled by |
|---|---|
| lint particle budget | × budget |
| lint gravity limit (0.01 units/frame² at 1x) | × world ÷ time² |
| lint contact flash length, contact-layer life, peak tolerance | × time |
| review flash span, off-peak tolerance, dead-tail minimum | × time |

## Using scaled effects in a game

The `.efk` is built in world units: play it at scale 1 (`Vfx.play(id, position)`); do not scale the emitter again.
The manifest's `scale` entry is informational for the game (and the Lab). A beam's `@In0` length is a world
distance, so `Vfx.beam()` works the same at every scale.

## How it was verified

A copy of `VFX_Fire_Explosion` built with `scale={'world': 40, 'time': 1}` was rendered in the scaled Lab next to
the original: the frames matched within a mean of 4–6/255 per pixel (random sparks and bloom differ), so the space
conversion reproduces the effect exactly at 40x. The time stretch is a design choice, judged on the kaiju examples
(`vfx examples add kaiju`) by independent review.
