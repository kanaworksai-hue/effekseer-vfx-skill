# Command reference

`sh <skill>/scripts/vfx [--project DIR] <command> [options]` (on Windows: the same from Git Bash, or
`<skill>\scripts\vfx.cmd [--project DIR] <command> [options]` from cmd or PowerShell). Output: one JSON object on stdout; progress and lint
warnings during a build go to stderr. Exit codes: 0 ok, 1 failed check or error (`{"ok": false, "error": {...}}`),
2 setup required: the toolchain is missing (`SetupRequired`) or there is no workspace here (`WorkspaceMissing`).
Image results are file paths — open them.

Every command except `doctor`, `init`, `examples`, `rubric`, `layer-schema` and `process-texture` needs a workspace
made by `vfx init` (`vfx/src/` and `vfx/vfx_manifest.json`). Run from the game project or pass `--project`; a command
run in the wrong folder fails with `WorkspaceMissing` instead of creating a stray `vfx/`. The current directory is
kept off Python's import path, and `vfx/src` helpers resolve only as `_name` files, so project files never shadow
the standard library.

Environment: `VFX_PROJECT` (project, default current directory), `EFFEKSEER_VFX_HOME` (toolchain, default
`~/.cache/effekseer-vfx`, on Windows `%USERPROFILE%\.cache\effekseer-vfx`), `GODOT` (Godot 4 executable, default
`godot` or `godot4` on PATH, then `/Applications/Godot.app`; on Windows set it to the downloaded `Godot_v4.x_win64_console.exe`
unless Scoop or winget put `godot` on PATH).

Setup: `sh <skill>/scripts/setup.sh [--authoring-only]` on macOS and Linux;
`powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1 [--authoring-only]` on Windows (Git Bash's
`sh setup.sh` runs it). Both are safe to re-run, verify every download against a pinned SHA-256 and install nothing
outside `EFFEKSEER_VFX_HOME`.

| Command | Needs | What it does |
|---|---|---|
| `doctor` | — | platform, toolchain, workspace; `modes` and `next` steps |
| `init [--update-templates] [--no-plugin]` | Python | create/refresh `vfx/` (Lab, materials, math textures, starter painted textures); download the official Effekseer Godot plugin (checksum pinned) |
| `examples [list]` | — | shipped pairs, single effects and sets with historical scores, verdicts and weakest points |
| `examples show <name\|ID>` | Python | layer plan with absolute frames and roles (a pair or set shows every effect) |
| `examples add <name\|ID\|all> [--force]` | Python | copy example source, brief, painted textures and prompts into the project; names: `fire`, `ice`, `poison`, `dark`, `hit`, `slash`, `charge`, `shield`, `heal`, `kaiju` |
| `procedural` | Python | regenerate the math-primitive textures |
| `list` | Python | effects in `vfx/src` with category, timing, delivery, design and build state; sources that fail to load are listed in `unloaded` |
| `lint [--ids ...] [--timeline]` | Python | static rules (errors) and craft heuristics (warnings), see below |
| `layer-schema` | Python | every layer field the compiler accepts |
| `brief-validate <ID>` | Python | brief vs recipe, with the expanded absolute layer timeline |
| `effect-context <ID>` | Python | brief, build issues, latest evidence and the last 10 rounds |
| `texture-info [names...]` | Python | coverage, bbox, border contact, orientation, bulge, seam ratio |
| `texture-audit <name> [--role R] [--grid C R] [--loop] [--allow-empty i...]` | Python | role checks + preview image |
| `process-texture <src> <dst> [--size N] [--color] [--grid C R]` | Python | crop, alpha, padding, power-of-two resize |
| `build [--ids ...]` | Core | lint, compile, save/open read-back, manifest, build receipt; without `--ids` also prunes effects this skill built whose source left `vfx/src` (see below) |
| `compile <recipe.json> [--source] [--runtime]` | Core | compile one recipe JSON |
| `export [--output DIR]` | Core | re-export all built effects to `.efk` with `resources/` |
| `discover` | Core | dump Core property paths, types and enums to `vfx/work/property_schema.json` |
| `core <command> ...` | Core | the vendored bridge's low-level commands on explicit `.efkefc` files: `property-list`, `property-get`, `property-set`, `node-list`, `curve-list`, `curve-set`, `settings-list`, `settings-set`, ... (`vfx core --help`); see [engine conventions](engine-conventions.md#extending-the-compiler) |
| `review [--ids] [--step N] [--note] [--key-frames ...] [--view standard\|close] [--profile default\|bare] [--bright]` | Core + Godot | strips, key-frame sheet, flags, changes, evidence ID |
| `overview [--ids]` | review done | library overview pages of the latest standard captures (the baseline `effect-verify` checks); never-captured effects are skipped and listed in `missing`. With `--ids`, a scratch page `overview_select_*.png` that does not replace the baseline |
| `strip <ID> [--compare] [--bright]` | review done | strip path and stored metrics |
| `frames <evidence_id> <frame...>` | review done | full-size frame paths and freshness issues |
| `history <ID> [--limit N]` | — | review rounds, newest last |
| `rubric` | — | the independent review rubric |
| `review-handoff <ID>` | review done | write the independent reviewer's complete brief for the latest fresh capture (`prompt_file`), with `report_file` and the submit command |
| `review-submit <evidence_id> <report.json> --reviewer ID [--frames f...]` | review done | bind an independent report; frames default to its `observed_frames` |
| `effect-verify <ID> [--no-overview]` | — | exit 1 unless current build, capture, review and overview agree; `--no-overview` is a partial check that reports `passed_without_overview` and never `verified: true` |
| `preview [--ids] [--bright] [--output]` | Godot | UI screenshots at baseline, peak, 50 %, 85 % |
| `showcase [--movie]` | Godot (+ ffmpeg) | open the Lab auto-playing the library; `--movie` records it |
| `package [--preview-dir]` | Godot | zip the Godot project with a texture inventory; does not claim device tests |
| `reference-import`, `reference-frames`, `reference-compare` | ffmpeg | see [reference](reference.md) |

## `--ids` and broken sources

With `--ids`, `lint` and `build` only require the named sources to load; any other `vfx/src/VFX_*.py` that fails
(a half-written effect) is reported in `unloaded` and left out of the cross-effect checks, instead of blocking the
work. Without `--ids` every source must load.

## What a full build may delete

A full `vfx build` refuses to run when `vfx/src` has no recipes. Otherwise it removes only effects **this skill
built** whose `vfx/src/<ID>.py` is gone: manifest entries tagged `built_by: "effekseer-vfx"` with `source` equal to
their own `vfx/src/<ID>.py`, or, in a workspace built before that tag, an effect whose build receipt in
`vfx/work/builds/` still matches the `.efkefc` on disk. Malformed IDs are never owned, and every path is checked to
stay inside `vfx/` before anything is deleted. Effects in the manifest or in `vfx/effects/` that another tool or a
person made are kept; `vfx doctor` counts them as `unmanaged`.

A full build also prunes resource copies no recipe uses: only a file identical to a texture in
`vfx/textures/processed/` (and that PNG's own `.import`), never other files with the same prefix, and never a name an
unmanaged effect may use (its `.efkefc` names the file, or its file is missing). Core copies every texture and model
into `resources/` by base name, so a build stops with `Resource name conflict` when two different files share a name:
within the build, against an owned effect that uses it and is not rebuilt in the same call (rebuild them together),
or against an unmanaged effect that may use it (rename the file). A build refuses to run when any output folder
resolves outside `vfx/` (a symlink elsewhere). Each build receipt binds all of its resource copies, so a later build
that changes one makes the earlier capture stale.

## What lint checks

Errors (the build refuses while any exist):

- unknown or mistyped layer fields (with a suggestion), and invalid field values;
- `peak` outside the duration; an `infinite` layer without `flight` or without an `interval`;
- a layer alive past the duration (non-looping effects), counting births and the projectile release;
- particle budget above the category's limit: `hit` 60, `projectile` 100, `boss` 250, every other category 150;
- a texture that is neither a math primitive nor recorded in `vfx/texture_prompts.json`, or missing from
  `vfx/textures/processed/`;
- `size_curve`/`scale_curve` combined with a random size or scale range (the compiler cannot multiply them);
- UV distortion on a flipbook (it samples neighbouring cells and renders hard square edges);
- gravity above 0.01 (it is per frame squared).

Warnings (craft hints; the strip decides):

- `fade_in + fade_out` longer than the shortest life (the layer never reaches full opacity);
- an effect with `impact >= 0.3` but no contact: no `flash()` layer and no single white-hot additive layer that
  lives at most 10 frames;
- the contact starts more than 6 frames from the manifest `peak`, where the Lab kicks;
- a `flash()` that lives more than 6 frames (a contact should be 2–5);
- no layer changes shape: no dissolve cutoff, ring sweep, UV distortion or scroll, flipbook, or painted shape
  re-struck on later frames;
- no white-hot additive colour (luma ≥ 0.85 and every channel ≥ 180);
- two effects of one category but different elements that differ in fewer than 3 of shape, motion, rhythm,
  material and secondary (likely a recolour).

## Workspace layout

```
<project>/vfx/
  src/VFX_*.py            recipe sources (yours)              ┐
  briefs/VFX_*.json       design briefs                       │
  texture_prompts.json    prompts of painted textures         │ the effect library:
  textures/generated/     image-model originals (never edited)│ keep under version control
  textures/processed/     game textures (incl. procedural)    │
  recipes/*.json          compiled recipe snapshots           │
  effects/*.efkefc        Effekseer sources + resources/      │
  exports/*.efk           runtime exports + resources/        │
  vfx_manifest.json       ids, timing, delivery, design       │
  previews/strips/overview_*.png, metrics.json                ┘
  characters/             optional rigged stand-ins (player.glb, target.glb)
  godot/                  generated Godot Lab (ignored)
  work/                   receipts, locks, reference frames, audits, property schema (ignored)
```
