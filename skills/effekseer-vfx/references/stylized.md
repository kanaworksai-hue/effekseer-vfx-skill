# Stylized hard-edge VFX

**One style option, not a default.** Use this page only when the brief's `style` asks for a stylized, hard-edged
look. Realistic, painterly or soft-glow effects keep the existing primitives and textures ([realism](realism.md),
[textures](textures.md)); nothing here changes their defaults, and lint and review never require hard edges or ink
outlines.

The look of much current stylized game VFX: crisp toon shapes cut from hand-painted greyscale masks, a white-hot core
in a saturated body, ink-dark accents (spiky bases, outlines) and small four-point star glints. Soft additive glows
alone cannot reach it; neither can more bloom.

## Greyscale masks + a steep cutoff

A mask holds a shape as grey values; the material decides how it reads. A soft fade gives a smoky blob. A **steep,
fixed alpha cutoff** gives a crisp shape with the painted outline; **moving** the cutoff over life (EaseIn: hold, then
erode) breaks the shape apart from its thinnest parts first with a hard edge, which is what makes a ribbon or a spike
look hand-animated.

| Mask | Source | Use |
|---|---|---|
| `T_SwirlNoise01` | math (`vfx procedural`) | swirling breakup of smoke, energy fill, alpha erosion with curl |
| `T_FlameBand01` | math | band of flame tongues (U tiles): crowns and ground fire on a cylinder |
| `T_SpeedStreak01` | math | dashes of uneven length (tiles): scrolled along a beam they carry its speed |
| ribbon strip (e.g. `T_RibbonStrip01`) | image model | one long barbed ribbon; `vfx helix-texture` wraps it into `T_RibbonHelix01` |
| spike band (e.g. `T_SpikeCrown01`) | image model | jagged spikes rising from a solid base (U tiles) |
| spiky splat (e.g. `T_SpikeSplat01`) | image model | radial burst for hits, muzzles and ground decals |

The painted ones are not shipped: their prompts are templates in `assets/examples/texture_prompts.json` (white shape
on flat black, hard edges, no glow). Wrapped masks must tile in U: crossfade the ends, then threshold again so the
crossfade does not leave a grey smear.

## Primitives

| Helper | What it builds |
|---|---|
| `hard_edge(layer, threshold, outline, width, erode)` | steep cutoff + an edge band of `outline` colour inside the cut (visible on Blend layers) |
| `stylized_pair(layer, outline, grow, ...)` | Blend ink silhouette slightly larger + the bright shape, same clock and cutoff: an outline that always hugs the shape |
| `spiral_ribbons(name, color, radius, height, life, ...)` | double-sided cylinder with a helix mask scrolling round and along it, cut hard, ink edge |
| `spike_crown(name, color, radius, height, life, flare, rise, ...)` | flaring cylinder with a spike-band mask that shoots up in `rise` frames and erodes from the tips |
| `speed_streaks(name, color, radius, height, life, speed, ...)` | hard-cut dashes racing along a cylinder ("speed lives in the beam") |
| `sparkle(name, color, size, count, ...)` | four-point star glints that pop, hold and pinch out |

## Value and colour on real backgrounds

- **Additive colour washes to white on a bright stage.** A magenta additive beam that reads on the Lab's dark slate
  turns white over a daylit sky. Give the body an alpha-blended saturated colour and keep additive for the hot core
  and the glints; check a bright background (`--bright`) or, better, frames from the game.
- **Ink accents carry the shape**: a black spike crown or ink splat where a beam meets the ground, a dark rim behind a
  thin laser. They read on any background and make the bright parts look brighter.
- Keep the palette to one family plus white and ink. A second hue needs a job; a blue charge in a magenta combo is a
  coherence failure, not an accent.
