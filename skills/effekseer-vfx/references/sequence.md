# Sequences: combos, finishers and the staged workflow

A skill is rarely one effect. A combo fires several shots on the beats of an animation and ends on a finisher; the
player judges them together. Design, gate and review them together as a **sequence**. The workflow below follows how
senior real-time VFX artists build such a piece. It is independent of the look: a realistic explosion chain, a
painterly or a toon combo go through the same stages; the brief's `style` decides the materials and textures.

1. **Let the animation lead.** Start from the character's real clips and their event times, not from an idea of the
   effect. The sequence brief lists the moments the animation fires each effect.
2. **Block out first.** Basic shapes and solid colours only, to settle timing, size and readability. No painted
   textures until an independent blockout review says ship.
3. **Add detail, then cut.** Detail makes hits punchier, but an element that does not carry the theme (a meteor that
   comes out of nowhere at the end of a laser combo) is cut, not polished. Record what you cut and why.
4. **Steal from references on purpose.** For every reference write what you take from it (the speed lines inside a
   beam, a dark base where it meets the ground, the way smoke rolls over the impact, a colour). The reviewer checks
   each item.
5. **Paint over a key frame.** Turn a captured frame into a concept painting with an image-edit model and the steal
   list; the concept becomes the visual target the polish rounds are compared with.
6. **Textures and materials for the chosen style.** Realistic work keeps the existing painted and photographic
   flipbooks ([realism](realism.md), [textures](textures.md)). Only when the brief's `style` asks for a stylized,
   hard-edged look, use the greyscale masks and the hard-edge material in [stylized](stylized.md).
7. **Screen feedback last.** Camera shake, a flash or impact frame and a hit-stop on the finisher's contact, declared
   in the manifest (`screen`) so the game plays exactly what was reviewed.

## The sequence brief

`vfx/sequences/<SEQ_ID>.json` (IDs start with `SEQ_`):

```json
{
  "schema_version": 1,
  "sequence_id": "SEQ_Star_Combo",
  "stage": "blockout",
  "style": "stylized anime combat, hard-edged shapes",
  "theme": "Magenta star fire: thin lasers build to one huge laser from the sky.",
  "animation": "mage_atk1..4 fire a laser on each thrust; the burst calls the pillar 0.6 s in. Times measured in the game.",
  "steps": [
    {"t": 0.1, "effect": "VFX_Star_Laser", "beat": "atk1 thrust"},
    {"t": 3.13, "effect": "VFX_Sky_Pillar", "beat": "finisher"}
  ],
  "references": [
    {"source": "where it comes from", "steal": ["speed lines streaming inside the beam", "a dark base where the beam meets the ground"]}
  ],
  "concept": {"image": "vfx/concepts/SEQ_Star_Combo/concept.png", "frame": 210},
  "cut": [{"idea": "meteor finisher", "why": "came out of nowhere; the laser theme ends on a bigger laser"}],
  "acceptance": ["Each laser starts at the hand and ends on the target"]
}
```

- `style` (optional) is the look, as in the effect briefs: it steers the paintover prompt and which texture and
  material tools fit. Without it the paintover keeps the look of the captured frame.
- `steps[].t` is seconds from the start of the capture; take it from the game (log the frame each event fires on)
  rather than guessing. Each effect still has its own brief and recipe.
- `stage` is `blockout`, `detail` or `polish`. `vfx sequence-validate` enforces the gates:
  - **blockout**: every effect in the steps declares `effect(..., stage='blockout')`; lint then refuses painted
    textures and flipbooks in those recipes (math textures only) and drops texture-craft warnings.
  - **detail**: needs the blockout gate (`<SEQ_ID>.gate.json`, written when an independent blockout review says ship)
    and references with steal lists.
  - **polish**: also needs the concept image.

## Capturing and reviewing

```sh
vfx sequence-review SEQ_Star_Combo                       # the Lab performs every step at its time
vfx sequence-review SEQ_Star_Combo --frames <dir>        # frames the game captured (preferred)
vfx sequence-handoff SEQ_Star_Combo                      # reviewer brief for the latest capture
vfx sequence-submit <evidence_id> <report.json> --reviewer <id>
```

The Lab stages each step with its delivery (beams aim straight at the target in a sequence; projectiles fly;
targeted effects land on the target), but its dummies do not carry your character's animation, camera or lighting.
**Prefer frames from the game**: render the combo at a fixed 60 FPS (Godot's `--write-movie <dir>/frame.png
--fixed-fps 60`), keep every second frame, and name them `<SEQ_ID>_fNNN.png` with NNN counted from the capture start at
60 FPS (or pass `--fps`). Game frames catch what the Lab cannot: a bright daylight stage that washes additive colour
to white, effects hidden behind the character, a camera that frames the finisher badly.

The strip labels every tile with frame, time and the step that starts there; the steps sheet shows each step at its
start, +4, +10 and +20 frames. The rubric (`assets/sequence_rubric.json`) scores only the criteria of the capture's
stage: a blockout is judged on read, timing, scale, placement and **coherence**; detail adds layering, shape change,
motion, tail and the steal list; polish adds the concept and the screen feedback. One fix per round, as with single
effects.

## Paintover concept

```sh
vfx paintover SEQ_Star_Combo [--frame N]     # copies the frame, writes the image-edit prompt from theme + steal list
vfx concept-compare SEQ_Star_Combo           # concept beside the latest capture's frame
```

Give the copied frame and the prompt to an image-edit model (the frame as the reference image). Keep its untouched
output as `vfx/concepts/<SEQ_ID>/concept.png` and set `concept` in the brief. The concept is a target for palette,
shapes and value structure, not a pixel match: the engine still decides sizes and brightness.

## Screen feedback

`effect(..., screen=dict(shake=.7, flash_frames=2, flash='invert', hitstop=.08))` plays at the effect's `peak`:

| Key | Meaning | Starting point |
|---|---|---|
| `shake` | camera trauma 0..1 | 0.3 heavy hit, 0.6-0.8 finisher |
| `flash_frames` | frames of a full-screen flash, 0..6 | 1-3; more reads as a fade, not an impact |
| `flash` | `white` (a white veil) or `invert` (an impact frame: stage white, characters and effect ink) | `invert` suits stylized finishers; realistic work usually wants `white` or none |
| `hitstop` | seconds of near-frozen game time, 0..0.3 | 0.05-0.1 |

The Lab performs it (hit-stop only in interactive playback, so captures keep the 60 FPS clock). In the game, connect
`Vfx.screen_cue(id, screen, position)` to the camera, an impact-frame overlay and the game's hit-stop. An impact frame
on a bright stage needs a different threshold from the Lab's dark one: ink what is dark or in the effect's hue, white
the rest. Give only the finisher an impact frame; on every hit it stops meaning anything.
