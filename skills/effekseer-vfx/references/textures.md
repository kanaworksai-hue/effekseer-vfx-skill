# Texture roles, generation and acceptance

Choose the role, then write the prompt, then generate. **Complex painted shapes** — smoke, slash arcs, fire bodies,
cracks, ice, symbols — come from an **image generation model**. **Math shapes** — glows, rings, noise, gradients,
trail bands, RG distortion maps — are the procedural textures (`vfx procedural` regenerates them; names in
[primitives](primitives.md)). `vfx init` also installs a starter set of seven painted textures that the primitives
default to — `T_SmokeSheet01`, `T_ExplosionSheet01` (4×4 sheets), `T_WispTrail01`, `T_Smoke02`, `T_Explosion01`,
`T_Crack01`, `T_IceShard01` — with their prompts. `vfx examples add` installs four more with the examples that use
them (`T_Impact01`, `T_Slash02`, `T_Rune02`, `T_Vortex01`). The skill's `assets/examples/texture_prompts.json` also
holds prompt templates for common painted shapes it does not ship (slash crescent, flame tongues, lightning bolts,
rune circle, ice spikes, flame sheet...; their `source` says so): copy one into `vfx/texture_prompts.json`, adapt it,
generate and process. Never imitate a painted shape by drawing it with Python.

## Generating

- If your host offers an image generation tool, use it with the prompt you wrote. Save the untouched output to
  `vfx/textures/generated/<T_Name>.png`.
- If it does not, **do not substitute anything**: add the prompt to `vfx/texture_prompts.json`, tell the user which
  image to generate (name, size, prompt) and where to save it, and continue with the parts that do not need it.
- Record every prompt in `vfx/texture_prompts.json` as `{"id": "T_Name", "size": 256, "prompt": "..."}` (add
  `"grid": [4, 4]` for sheets and `"post"` for any non-default processing). Lint rejects painted textures without a
  recorded prompt.
- Process into the game texture, never overwriting the original:
  `vfx process-texture vfx/textures/generated/T_Name.png vfx/textures/processed/T_Name.png --size 256`
  (`--color` keeps colour as straight RGBA; `--grid 4 4 --size 1024` for flipbook sheets keeps cells in place).
- Measure: `vfx texture-info T_Name` for angles, bulge and clipping; `vfx texture-audit T_Name --role shape` (or
  `flipbook --grid 4 4`, `trail`, `symbol`, `light`, `uv_distortion`, `screen_distortion`) for borders, alpha,
  small-size survival and frame changes. Open the audit's `preview` image.

Sizes: ordinary particles 128–256, main shapes and seals 512; the verified 4×4 sequence is 1024².

## Prompt contents

State the visual role, outline and internal structure, required margin, background or transparency mode, the
exclusions (no environment, characters, text or UI) and the target size. For masks: white shape on pure black.
Sequences state the grid, the change from growth to break-up, a constant centre and scale, a margin in every cell;
loops state that first and last frames connect.

Solid shapes need a readable outline and varied thickness and may be asymmetric with negative space. Light needs a
smooth falloff from the core and may be symmetric. Seals and symbols may use exact geometry and dense ornament.
Smoke follows the target style — crisp outer edge, internal value or soft volume — but not every smoke should become
a cartoon cotton ball. Do not apply "break the rules" to optical stars or the seal itself.

| Type | Be specific about | Avoid |
|---|---|---|
| slash and claw marks | one main direction, thick root to thin tail, breaks and uneven thickness, space inside the arc | a uniform-width crescent icon; evenly spaced claw lines |
| bursts and solid flashes | a weighty core and a directional rim; the core either whole or clearly a ring | a random small hole in the middle that reads as an eye or a face |
| smoke and dust | a clear style, outline and internal value, lobes of different sizes, gradual break-up | identical cotton balls; a grey gradient with no outline |
| light and stars | a smooth hot core, straight falloff, symmetry chosen by role | forcing light into curved broken strokes and rescuing it with a huge glow |
| seals and symbols | clear density, structural hierarchy and fine symbol bands | a few giant letters that shrink into an empty ring |
| ground cracks | branching from the impact, thick roots to thin ends, local irregularity | an even grid or tiled cells that read as floor tiles |

A fillable request, e.g. for a smoke tail sequence:

> Purpose: grey smoke residue left after a fire projectile. A continuous 4×4 sequence, 1024². The mass starts dense,
> rolls upward and gradually breaks into uneven fragments. Constant centre and scale, a margin in every cell. Keep
> internal value; layered outer outline; avoid regular round puffs and uniform radial spread. No characters,
> environment, text or UI. An isolated asset to be tinted in the game.

This is a template, not the provenance of a generated asset: after generating, record the real prompt, original and
processing settings. Seals, slash arcs and fire bodies need their own role written, not just a different colour.
`assets/examples/texture_prompts.json` holds the prompts of the example textures.

## Acceptance

Hard errors: missing files, an invalid grid, dimensions not divisible by the grid. Empty first or last cells and held
frames may be intentional; empty middle cells, jumps and repeats are only hints — look at the image. A thin texture
that is beautiful at full size can vanish in the standard camera: check the 64 px and 32 px previews and the real
render.

Measured here: UV distortion on a flipbook samples neighbouring cells (lint forbids it); colour textures and alpha
textures use different channels; UV distortion needs an opaque RG map, while screen distortion may carry an alpha
extent. Fire keeps the verified explosion sequence with erosion rather than a clip-art flame sprite.

## Sequences must deform

Step through the cells: does the shape move from one key pose to another — opening, rolling, tearing, eroding?
Scaling the same outline while lowering opacity is not deformation. The change from dense to broken may be quick,
but the body must not be crumbs the moment it reaches visible size.

When one sequence serves several roles, choose different start cells and playback speeds and say why: a hot head may
play only the dense short segment; a smoke tail may change slowly with its colour cooling first.
`frame_length × cell count` is the playback time and life is the instance lifetime; when they differ, explain the
early exit, hold or cut.

Small previews are only a screen. If the texture disappears at 32 px, first widen the useful visible lines, remove
useless detail or change the real layer size; do not blindly raise a 512 original to 2048 — resolution does not
change screen share in the same camera.
