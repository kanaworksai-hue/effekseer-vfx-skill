# Photographic explosions, fire and smoke

Use this when the brief asks for a realistic look (film, live-action reference, a photoreal game) instead of the
stylized default. The craft rules still apply — time structure, value layering, shape change — but the colours,
brightness and textures come from photographs.

## Colour and brightness from photographs

Daylight photographs and high-speed film of fuel and munitions explosions agree on these values (sRGB, before the
Lab's bloom). They are the palette of `VFX_Kaiju_Explosion`:

| Role | RGB | Notes |
|---|---|---|
| contact core | 255, 244, 214 | pale yellow-white, **not** pure white; one short spike, gone by ~8 Lab frames |
| fire body | 255, 168, 72 | orange; the body is the brightest part after the contact |
| cooling edge | 214, 84, 28 | deep red-orange where the fire meets soot |
| last glow | 120, 40, 18 → 60, 20, 10 | dull red pockets inside the smoke, then out |
| soot | 38, 32, 29 | warm near black, opaque: the fire burns in front of it |
| smoke column | 92, 84, 78 | brown-grey; lighter where the sun hits the top, darker underneath |
| dust skirt | 150, 136, 118 | the ground's colour, lighter than the smoke |
| steam | 205, 215, 225 | near white, thin, rises fast and disappears |

- **Avoid pink and magenta in fire.** Saturated red-pink (high R and B) reads as a game effect immediately.
- **The fire is not white for long.** In photographs the white-hot frame is one or two frames; after that the
  brightest pixels are yellow-orange. Under the Lab's bloom a ramp that stays near white for 10 % of a long life
  reads as a blown-out flash (an independent review flagged exactly that); start orange at about 5 %.
- **Smoke outlives fire by a lot** and moves slowly: in a real blast the fireball is gone in about a second and the
  column keeps climbing for many seconds. Keep its density (colour_end alpha above zero) and end the effect while it
  is still visibly thinning, not after it has vanished.
- **Smoke is lit from above.** Photographic smoke sheets have light tops and dark undersides; keep the roll small
  (±12°) so the light stays on top, and emit with `spawn rotate=False` so `velocity` is world-up.
- Emissive: additive fire 1.3–1.8 is enough; brighter values push the body past the bloom threshold and it turns
  white. The value structure (pale core, orange body, dark soot) is what sells it, not raw intensity.

## Textures

Painted stylized puffs look like cartoons next to a photoreal world. The skill ships three photographic flipbooks
(4×4, 1024², generated with an image model and processed; prompts in `assets/examples/texture_prompts.json`):

| Texture | Use | Blend |
|---|---|---|
| `T_FireballSheet01` | the fireball: alpha = luminance, so hot pockets glow and soot is transparent | Add, with a `ramp` |
| `T_FireballSootSheet01` | the same fireball's opaque body (shaded grey, full silhouette) | Blend, listed **before** the fire |
| `T_SmokeSheet02` | photographic rolling smoke column with lit tops | Blend, tinted by the smoke colour |

`smoke()` plays any `T_*Sheet*` texture as a 4×4 flipbook. For a column that must stay dense to the end, slow the
flipbook (`flipbook=dict(x=4, y=4, frame_length=8, loop='Once')`) so it stops before the sheet's last, nearly empty
cells.

## Smoke and fire meeting the ground

A sprite that cuts through the floor or a water surface leaves a hard horizontal line. Give ground smoke, dust and
steam a `soft` distance (world units, a third to a half of the puff size) — verified in Forward+, see
[engine conventions](engine-conventions.md#rendering-hdr-and-the-lab).

## Layer plan of a photographic explosion

Back to front: heat haze → smoke column (soft, slow flipbook) → soot body (Blend) → fireball (Add, photographic
ramp) → fire lobes thrown off it → contact flash and a short bloom → ground pivot with a soft dust skirt rolling out →
ground shock ring and refraction → spark tiers → dark debris that lands. `vfx examples show VFX_Kaiju_Explosion`
prints the timeline.
