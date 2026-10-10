# Value, colour and layer pairing

Plan three things a viewer can read in the standard camera: a short bright point, a body with a shape, and a dark
side or material that sets the body off. Every added layer must name the visible problem it fixes; a layer count is
not a quality measure.

## Palette roles first

| Role | What should be visible | First adjustment |
|---|---|---|
| core | a small hottest area or a thin hot edge, clear at contact | control size and duration before adding emissive |
| body | a saturated outline that names the element and the action | keep the form after the white flash leaves; cool its colour instead of removing it |
| dark | backing, concavity, cracks or real shadow | use Blend and check bright and dark backgrounds; black Add cannot do this job |
| matter | smoke, dust, shards, drops — weight | lower saturation, keep internal value and a visible exit |
| accent | a small second-colour cue | give it one place or phase, then check it does not steal the main colour |

The main colour can be single or a family of neighbours. A second colour needs a job (ice's prism fringe, poison's
dark core); never pick a colour per layer, and complementary colours are not mandatory. Smoke next to fire may pass
through a warm tone before turning grey, but do not repaint all the smoke saturated orange.

Read values in greyscale before hue. If core, body and background are all near white, adding orange particles will
not restore structure. Find which layer pushes the picture white first: the contact, a glow, the body, or several
overlapping Add layers.

## Three kinds of copies do different work

| Technique | Geometry and timing | Purpose | Typical mistake |
|---|---|---|---|
| Dark backing (`shadow()`) | its own shape, may be slightly larger, roughly the body's phase | sets bright colour off; readability on bright backgrounds | a black mass swallowing the body (reads as a black hole); invisible on a dark stage |
| Value pair (`contrast_pair()`) | identical outline, fixed angle, same motion and birth time | adds light-and-dark structure inside one shape | two random outlines drifting apart into two unrelated strokes |
| Smoke afterimage (`decay()`) | may be delayed, slower, longer, with different colour and blend | leaves matter after the light goes out | a dark blade arc hanging for a long time, reading as a dirty smear |

`decay()` is not a geometry-identical value pair.

A deterministic pair fixes `count=1`, life, size, rotation, position, spin, travel and flipbook start. Separate
particle nodes draw their own random values: equal ranges and one global seed do **not** give the same angle. When
many directions are needed, have an outer layer pick one fixed angle and use that fixed value for both nodes; never
give each layer its own `[0,360]`.

An exact pair keeps the same life and normalised curves. Lengthening the life also moves the real frame at which
50 % of life is reached, so scale and sweep drift apart. To let the dark layer exit later, recompute its curves
explicitly or make it an independent afterimage and stop calling it a matched outline.

Measured here: later layers draw in front, and Model ZWrite cannot provide this occlusion — use draw order. A Blend
dark copy drawn before an Add bright body is a starting point; a dark cut in front and a dark backing behind are
different designs, so decide from the render.

```python
from vfxkit.primitives import *

body = sprite('Matched burst', 'T_Explosion01', (255, 120, 30, 255),
    life=16, delay=3, size=2.0, rotation=[0, 0, 30],
    size_curve=[[0, .8], [30, 1], [100, 1.1]],
    color_curve=ramp((0, (255, 120, 30, 255)), (100, (180, 35, 10, 0)))['color_curve'],
    alpha_texture='T_NoiseTile01', cutoff=[[0, 0], [100, .8]],
    fade_in=0, fade_out=4, emissive=1.2)
layers = contrast_pair(body)   # [Blend dark underlay, the bright body]; splice into effect(..., [*layers, ...])
```

The two layers share geometry and clock and differ in colour and material. Alpha, blend and cutoff still change the
real edge, so check the render; pixel-exact overlap is not promised. 30° is a demonstration angle, not this
texture's orientation: run `vfx texture-info` and use the measured angle for the direction of action. The helper
handles one Sprite only; design Ring and Model pairs explicitly.

## Size and life starting points

Measure against the body's **visible width B** and **life L**, not the sprite card size: a texture holding one thin
line does not weigh the same as a filled card of the same size.

| Layer | Starting point | How to confirm |
|---|---|---|
| hot core | about 0.2–0.5 B wide, or one thin edge of the body | the core is findable at peak and the body is still findable afterwards |
| dark pair | same size and life as the body | if the size changes, decide again whether it is a cut or a backing |
| independent backing | slightly larger, about 1.1–1.4 B | no clean black circle forms outside the body |
| dim afterimage | about 1.1–1.2 L | after the bright layer dies, a short intentional layer remains |
| smoke afterimage | the longer life `decay()` gives | the exit keeps deforming; not a static dark arc |

These are tuning starts, not statistics and not lint rules. Slashes and sustained pillars may use long thin hot
edges; heals and shields need no attack-style white flash. Matching curves, negative space and the standard camera
matter more than the ratios.

## Fix order for white blobs and dark blobs

When the body fills with white: switch off glow, contact and duplicate Add layers one at a time to locate the cause;
then shorten the contact; then cut the body's long high-brightness stretch; add darks last. Do not change texture,
curves, smoke and camera shake at once — you will not know what worked.

When a dark layer reads as a separate black stroke: check angle and size alignment first, then birth time and life,
and only then grey value. Do not hide wrong geometry by lowering opacity. If it works on a bright background but not
on the default stage, give the material layer a suitable grey or a locally lit colour while keeping the dark and
matter roles distinct.

A finished round can name its improvement in one sentence with the frames you looked at, e.g. "after f12 the white
flash is gone and the orange-red fireball keeps its outline". See the [fire explosion case](cases.md#fire-explosion-a-contact-that-stays-white).
