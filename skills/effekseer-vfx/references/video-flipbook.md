# Video flipbooks

An image model paints one frame. An image-to-video model also paints the **motion**: a water column that shoots up,
holds the target in the air and collapses as rain; a fireball that bursts and boils into grey smoke. Those are
continuous changes of shape and material that layered primitives cannot draw: a primitive can scale, fade, scroll and
erode a picture, but it cannot turn fire into smoke inside the same silhouette. A video flipbook can, because the model
drew every in-between.

The skill turns such a clip into a straight-alpha sheet, gives every sheet the same graded look, and plays it in either
engine. Nothing here depends on one video service: any image-to-video model that accepts a first and a last frame
works. The prompts and numbers below were verified with Seedance 2.5.

## Three ways to work — pick per effect, mix freely

| Mode | What makes the effect | Engine | Best for |
|---|---|---|---|
| **Procedural** (the original skill) | layered primitives in a Python recipe, painted textures | Effekseer → Godot | hits, slashes, auras, beams, shields; anything that must stay crisp, tiny or runtime-driven |
| **Video flipbook** | one generated clip as the body; the Unity runtime adds core, matter and ground | Unity (URP) | a single strong shape change: geysers, fire-to-smoke bursts, looping orbs, transformations |
| **Combined** | the clip is the body layer (`video_body`), primitives add contact flash, sparks, rings, cracks, decals, heat haze | Effekseer → Godot (or Unity with its own layers) | hero impacts: the clip gives the motion, primitives give the timing, the white-hot core and secondary motion |

Rules that stay true in every mode: time structure (anticipation → contact → body → secondary → dissipation), value
layering (hot core, saturated body, dark rim), and an independent review before calling an effect done. A clip is a
body, not a finished effect: it has no contact frame, no sparks that react to the target and no ground contact until
the engine adds them.

## Pipeline

```sh
vfx video-first-frame <element.png> vfx/textures/generated/<id>_first.png --fill .35 [--anchor bottom]
#   generate the clip (image-to-video, first + last frame) → save it as vfx/videos/<id>.mp4
vfx video-timeline vfx/videos/<id>.mp4                                   # labelled frames: pick the span
vfx video-flipbook vfx/videos/<id>.mp4 <ID> --grid 8 8 --cell 256 --start 24 --end 100 \
    --prompt-file <prompt.txt>                                            # key, crop, mask, gutter, record
vfx video-grade <ID> <ID>_graded --ramp "..."                          # one look per element
vfx texture-audit <ID>_graded --role flipbook --grid 8 8                  # border alpha, coverage, empty cells
```

`video-first-frame` puts the element image on pure black at the size and place the clip should start from and also
writes a pure black last frame. Bare sheet names live in `vfx/textures/processed/` (a path starting with `vfx/` is
project-relative). Every run records the clip, the prompt and the exact parameters in
`vfx/video_prompts.json` (lint accepts textures recorded there or in `texture_prompts.json`); contact sheets go to
`vfx/work/video/`. Originals stay in `vfx/videos/` and `vfx/textures/generated/`.

## Generating the clip

- **Image-to-video with first and last frame.** First frame = the element on black (`video-first-frame`). Last frame:
  pure black for a burst or a column (the effect must fully dissipate), the **same image as the first frame** for a
  loop (an orb that burns in place: the clip comes back to its start, so one period loops seamlessly).
- **Fixed camera, pure black background, nothing but the effect**: no character, ground, reflection, fog, text, music.
- **Keep it inside the frame**: say where the effect stays ("centred, the top never leaves the frame") — a clipped edge
  becomes a hard line in the sheet.
- **Say what it is NOT.** Models drift to clichés: an explosion becomes a mushroom cloud with a smoke column, a water
  burst becomes a white foam cloud. Name them: "not a mushroom cloud, no smoke column", "the water stays clear blue,
  never white foam".
- **Beats with whole-second timestamps**, one change per beat, and the end state of each beat.
- **Style from the first frame**: "keep the first frame's hand-painted cel style and palette: <core>, <inner>, <body>,
  <dark rim>, hard value steps, clean, not realistic".
- 4–5 s at 720p or 1080p is enough; 24 fps is the decode rate.

Template (write it in the language your model reads best):

```text
A stylized anime game skill effect: <what it is>. Pure black background, the camera is completely fixed, only the
effect is in frame — no character, ground or scenery. <Where it stays: centred, never crosses the frame edges>.
<Not: the cliché to avoid>.
0-1 s: <the first frame's element> <anticipation>, then <the burst / rise>.
1-2 s: <the body: how the shape changes, where secondary pieces go>.
2-4 s: <dissipation: how it breaks up / cools / falls>, until the frame is pure black again, matching the last frame.
Keep the first frame's hand-painted cel style and palette: <core>, <inner>, <body>, <dark rim>; hard value steps,
clean, not realistic. The background stays pure black; no ground, reflection or text. No music, no sound.
```

## Making the sheet

- **Pick the span** on the timeline. Skip an opening white flash or any frame that fills the screen (the body is small
  first; the engine grows it with `size_curve` / `_Grow`). Stop when the effect is gone.
- **Grid**: 8×8 for bursts; tall subjects use tall cells (`--grid 8 7 --cell 224 --cell-h 400` for a column).
  Loops: exactly one period (`--frames 40:79:1` for a 40-frame cycle).
- **Crop**: `auto` takes one shared box over every frame (no jitter). Stray sparks inflate it; then give `--box cx,cy,half`.
- **Mask**: round (`--mask-power 2`) for bursts and orbs, rounded box (`3`–`5`) for columns and wide splashes so the
  top and base are not shaved. Every cell gets a transparent gutter (`--gutter 6`); the command fails if any cell
  border still has alpha.
- **Grade**: `--ramp` maps density to 3–4 flat steps, dark rim → body → light → hot core. `--erode` removes the haze
  keying leaves; `--tail-fade` fades the last cells to zero; `--smoke r,g,b --smoke-start .3 --keep-embers` cools a fire
  tail to grey smoke and keeps its embers; `--ramp-fade t0,t1` blends back to the clip's own colours late in life.

Verified starting points:

| Effect | flipbook | grade |
|---|---|---|
| water column (rise, hold, collapse) | `--grid 8 7 --cell 224 --cell-h 400 --frames 0:110:2 --pad 1.03 --mask-power 3 --radius .47 --floor .1 --gain 1.25` | `--erode .18 --erode-pow 2 --tail-fade 8 --highlight 4` + a 4-step blue ramp |
| fireball loop | `--grid 8 5 --cell 256 --frames 40:79:1 --box ... --radius .46 --floor .05 --gain 1.15` | `--erode 0 --tail-fade 0 --highlight 1.5` + a 4-step fire ramp |
| fire burst → smoke | `--grid 8 8 --cell 256 --start 24 --end 100 --box ... --radius .47 --feather .1 --floor .1 --gain 1.15` | `--erode .2 --erode-pow 2 --late-gamma .5 --late-alpha 1.4 --smoke .42,.39,.38 --smoke-start .3 --keep-embers --tail-fade 10 --late-blur 1.5 --ramp-fade .35,.6` |

## Effekseer / Godot: `video_body`

```python
video_body('Fire body (video)', 'T_Burst_8x8_graded', grid=(8, 8), size=3.4, frame_length=2, delay=7)
video_body('Geyser', 'T_Geyser_8x7_graded', grid=(8, 7), size=4.0, column=224/400, root_inset=.09)   # Y-axis billboard from its base
```

One particle plays every cell once (`loop=True` for orbs). The sheet is alpha-blended and left white: a colour on it
would tint the clip's own values. `frame_length=2` plays a 24 fps clip about 1.25× faster than generated, which
tightens the model's timing. Combined mode: keep the recipe's flash, glow, sparks, rings, cracks and haze and replace
only the painted billows with `video_body`; the shipped fire explosion becomes a combined effect by swapping its three
billow layers for one `video_body` at `delay=7`.

## Unity (URP)

```sh
vfx unity-install <UnityProject>                    # package into Packages/, procedural textures into Assets/VfxSkill
vfx unity-export <sheet.png> <UnityProject>         # sheet + .flipbook.json (grid, cell, measured bottom inset)
```

In Unity 6 (URP): **VFX Skill → 1. Setup shared materials → 2. Create element skill from flipbooks → 3. Build demo
scene**, then Play (on-screen buttons cast each skill; keys 1–9 too when the legacy Input Manager is enabled). Agents can skip the window: write a spec and run Unity in
batch mode —

```json
{"name": "Water Column", "delivery": "Eruption",
 "theme": {"r": 0.25, "g": 0.6, "b": 1, "a": 1}, "dark": {"r": 0.03, "g": 0.14, "b": 0.4, "a": 1},
 "orb": "Assets/VfxSkill/Flipbooks/Water_Orb.png", "body": "Assets/VfxSkill/Flipbooks/Water_Column.png",
 "extra": "CrownSplash", "contact": "FoamRing", "trail": "Droplets", "linger": "Drip"}
```

```sh
Unity -batchmode -projectPath <UnityProject> -executeMethod VfxSkill.EditorTools.CreateElementSkill.FromCommandLine -vfxSpec /abs/path/spec.json -quit
```

Pass the spec as an absolute path (Unity resolves relative paths against the project). The command creates the
materials and profile, validates it (a missing material fails the run) and rebuilds the demo scene.

Each skill is one `ElementProfile` asset (Create → VfxSkill → Element Profile): materials, delivery
(`Projectile` flies, `Instant` connects like lightning, `Eruption` bursts from the ground under the target and lifts
it), trail, impact extra, contact accent, linger and hit feel. A new element is a new asset, not new code; only a new
kind of motion needs a new enum value and its case in `ElementSkill`. Call `ElementSkill.Play(target)` from the game;
targets implement `IElementHitReceiver` (`DemoTarget` is a reference reaction with knockback, squash, lift and flash).

Import rules (applied automatically to `Assets/VfxSkill/Flipbooks/` and any texture with a `.flipbook.json`): no
mipmaps (the gutter does not survive low mips), never rescaled to a power of two (8×7 sheets would shift every cell),
4096 on desktop, 2048 ASTC on mobile. The body material's `_Tiles` holds the grid; a looping orb uses `_Flip`
(cols, rows, fps). Hit-stop freezes particles: no hit-stop while a video body is on screen — a projectile burst uses
`hitStop = 0` and sells the hit with growth and shake; an eruption may stop briefly on the dive, before its column starts.
`vfx unity-install --force` replaces the package but keeps Unity's `.meta` files, so scenes and materials keep their
scripts and shaders.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| a hard line or square edge in a cell | the clip crossed the frame, or the crop is too tight | say "never leaves the frame" in the prompt; larger `--pad`; rounded-box mask |
| the sheet flickers or jitters | per-frame crop | the shared `auto` crop, or `--box` |
| the burst pops on at full size | the clip starts open | skip the opening frames; grow it in the engine (`size_curve`, `_Grow`) |
| a white blob for the first frames | an opening flash in the clip | start after it; the engine's flash layer gives the contact |
| a column floats above the ground | the sheet has empty rows under the root | the sidecar's `bottom_inset`: Unity sets `columnRootInset` from it; Effekseer: `video_body(..., root_inset=...)` |
| everything looks like the video, not like the game | no grade | one ramp per element, the same steps for every sheet of that element |
| "atomic bomb" explosions | the model's default | name it in the prompt: not a mushroom cloud, no smoke column |
| cells smear at a distance | mipmaps on a gutter sheet | the import rules turn them off; Effekseer: keep the sheet's own size |

Check the video model's terms for commercial use before shipping its output; clips and sheets you generate belong in
your project, not in this skill.
