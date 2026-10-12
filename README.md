# effekseer-vfx-skill

English | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

Agent skills that let a coding agent (Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, OpenCode and other
[Agent Skills](https://agentskills.io) hosts) make real-time game VFX the way a VFX artist iterates, in code:

**design brief → textures → Python recipe → EffekseerCore build → real Godot filmstrip → look → fix one thing → repeat → independent review**

- **`effekseer-vfx`** — the authoring skill: craft rules, verified Effekseer/Godot engine conventions, about 30 composable
  layer primitives, a static linter, the official EffekseerCore compiler with save/open read-back, a Godot Lab that
  stages every effect as an exchange between two dummies, filmstrip capture with pixel flags, iteration history and
  tamper-evident evidence that ties a review to the exact build it saw.
- **`vfx-review`** — the reviewer skill: a separate agent scores the strip against a fixed rubric without seeing the
  recipe, because the author never grades its own work.
- **Examples** — sixteen finished effects with briefs and textures: four ranged pairs (fire, ice, poison, dark:
  projectile + impact), one each of hit, slash, charge, shield and heal, and a kaiju set (a charge that climbs the
  dorsal plates, a sweepable atomic beam, a photographic explosion), plus three diagnosed before/after cases.
- **Large and realistic effects** — `scale='kaiju'` builds a character-scale recipe 40x larger and 2.5x slower
  (sizes, speeds, gravity, budgets and the review camera all follow); `beam()` makes a held beam whose end point the
  game moves every frame (`Vfx.beam()` → `aim()` → `release()`); `charge_chain()` lights arcs along a chain of
  points; photographic fire, soot and smoke flipbooks; soft particles verified in Forward+.

## Requirements

| Mode | What you can do | Needs |
|---|---|---|
| authoring | write briefs and recipes, lint, process and measure textures | Python 3.11+ or [uv](https://docs.astral.sh/uv/) on macOS, Linux or Windows (macOS's built-in Python 3.9 is too old) |
| build | compile `.efkefc` / `.efk` through the official EffekseerCore | **macOS on Apple silicon** or **Windows x64**, network for the first setup (~250 MB into `~/.cache/effekseer-vfx`) |
| render | Godot filmstrip review, Lab, preview, packaging | the above + [Godot 4](https://godotengine.org) (Forward+) on `PATH` or in `GODOT`; `ffmpeg` for reference clips and recordings |

Build and render are verified on macOS ARM64 (Effekseer Core 1.80.7, EffekseerForGodot4 1.80.5.1, Godot 4.7, .NET 9)
and on Windows 11 x64 (the same versions, Godot 4.7.2). Windows ARM64 gets the matching .NET runtime from setup but is
not verified. Linux runs authoring mode; its build path is not verified.

On Windows every `sh <skill>/scripts/...` command below also works from Git Bash (what Claude Code uses); from cmd or
PowerShell use `<skill>\scripts\vfx.cmd` for `vfx` and
`powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1` for `setup.sh`.

## Install

The simplest way: give this repository's URL to your coding agent and ask it to install the skill. The steps it
follows are in [For agents: installing from this URL](#for-agents-installing-from-this-url). Or install it yourself:

**Claude Code** (type these in Claude Code)

```text
/plugin marketplace add kanaworksai-hue/effekseer-vfx-skill
/plugin install effekseer-vfx@effekseer-vfx
```

**Codex** (ask in a Codex chat; the skills land in `~/.codex/skills`, or `$CODEX_HOME/skills`, and are
used from the next turn or a new session)

```text
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/effekseer-vfx
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/vfx-review
```

**Other agents** (Cursor, Gemini CLI, Copilot, OpenCode, ...)

```sh
npx skills add kanaworksai-hue/effekseer-vfx-skill
```

Or copy `skills/effekseer-vfx` and `skills/vfx-review` into your agent's skills folder (`~/.claude/skills/`,
`.agents/skills/`, ...). Each skill folder
carries its own `LICENSE` (and `effekseer-vfx` its `THIRD_PARTY_NOTICES.md`), so a copied folder keeps them.

### For agents: installing from this URL

1. **Get the files.** If your host has a plugin or skill installer, prefer it (the commands above); a slash command
   such as `/plugin` must be typed by the user, so show it to them. Otherwise clone the repository and copy both skill
   folders into your skills folder, keeping their names: `git clone --depth 1 <this repository URL>`, then copy
   `skills/effekseer-vfx` and `skills/vfx-review` to `~/.claude/skills/` (Claude Code, all projects),
   `<project>/.claude/skills/` (Claude Code, one project), `~/.codex/skills/` (Codex; `$CODEX_HOME/skills` if set) or
   your host's skills folder (for example `.agents/skills/`).
   Do not copy anything else; the skills are self-contained and read-only at run time.
2. **Load them.** If the skills do not appear in your skill list yet, ask the user to start a new session.
3. **Check the machine.** From the user's game project run `sh <skill>/scripts/vfx doctor` (`<skill>` is the
   installed `effekseer-vfx` folder; on Windows outside Git Bash, `<skill>\scripts\vfx.cmd doctor`) and follow its
   `next` steps.
4. **Ask before downloading.** `sh <skill>/scripts/setup.sh` (Windows: `setup.ps1`, the exact command is in
   `doctor`'s `next`) installs the toolchain into `~/.cache/effekseer-vfx`
   (about 250 MB on macOS ARM64 and Windows x64; `--authoring-only` elsewhere), and the first `vfx init` downloads the official
   Effekseer Godot plugin (about 34 MB). Setup needs Python 3.11+ or uv: if `doctor` reports neither, ask the user to
   install one. Godot 4 is never installed for the user; ask them to install it (or to allow
   you to) and set `GODOT` if it is not on `PATH`.
5. **Run Godot outside the sandbox.** `vfx review`, `preview` and `showcase` open a Godot window on the user's
   desktop. A sandboxed agent (Codex in its workspace sandbox, for example) cannot open one: run those commands with
   the user's approval outside the sandbox; if your host cannot leave its sandbox, give the user the exact command to
   run in a terminal on their desktop. A review that renders no frame stops after about 90 s with "rendered no frame"
   (most likely the window could not open; check the Godot output it includes). `doctor`'s `render: true` only means
   Godot was found.
6. **Confirm it works.** Run `vfx doctor` again (`modes` should show what this machine supports), then follow
   [First steps](#first-steps). Report what works and what is missing; do not claim build or render works on a
   machine where `doctor` says it does not.

## First steps

Ask your agent, in your game project: *"Set up the effekseer-vfx skill here and show me the fire example."* It will run:

```sh
sh <skill>/scripts/vfx doctor            # what this machine can do, and what to install
sh <skill>/scripts/setup.sh              # macOS ARM64 / Windows x64; use --authoring-only elsewhere (asks you first)
sh <skill>/scripts/vfx init              # creates vfx/ with the Godot Lab, materials and math textures
sh <skill>/scripts/vfx examples add fire
sh <skill>/scripts/vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
sh <skill>/scripts/vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
sh <skill>/scripts/vfx showcase          # play the library in the Lab
```

Then ask for an effect: *"Make a lightning strike for a targeted spell, short and sharp, with a return stroke."* The
skill makes the agent write a brief, request painted textures from your image generation tool (or ask you for
them), write the recipe, build, review the strips over several rounds and hand the result to an independent reviewer
before it reports `effect-verify` as passed. Until that independent review is submitted and `vfx overview` has
been rerun, `effect-verify` says `verified: false` even when the effect renders correctly; an agent should report
"builds and renders" rather than "verified" at that point. The toolchain lives in `~/.cache/effekseer-vfx`; set
`EFFEKSEER_VFX_HOME` to put it elsewhere (see [the command reference](skills/effekseer-vfx/references/cli.md)).

## Image generation

Complex painted shapes (smoke, slash arcs, fire, cracks, ice, symbols) must come from an image generation model; the
skill never fakes them with code. If your agent has a built-in or connected image tool, it uses it with the prompts it
records in `vfx/texture_prompts.json`. Otherwise it tells you exactly which image to generate and where to save it.
Math shapes (glows, rings, noise, gradients, trails, distortion maps) are generated procedurally.

## Using the effects in a game

Effects end up as `.efk` runtime exports and `.efkefc` sources with a `vfx_manifest.json`. The generated Godot project
contains a small API:

```gdscript
var handle = Vfx.play("VFX_Fire_Explosion", position)
var shot = Vfx.launch("VFX_Projectile_Fire", from, to)
shot.arrived.connect(func(at): Vfx.play("VFX_Fire_Explosion", at))
```

Beams are aimed every frame; the game owns the end point (a ray cast, a target bone):

```gdscript
var ray = Vfx.beam("VFX_Kaiju_Atomic_Beam", mouth, target)
ray.aim(mouth, new_target)   # each frame: sweep, follow the head
ray.release()                # narrows and fades out, then frees itself
```

See [`skills/effekseer-vfx/references/godot.md`](skills/effekseer-vfx/references/godot.md) and, for giants and kaiju,
[`references/scale.md`](skills/effekseer-vfx/references/scale.md).

## Repository layout

```
skills/effekseer-vfx/      SKILL.md, references/ (craft, engine conventions, review...), scripts/ (vfx CLI and vfx.cmd,
                           setup.sh and setup.ps1, vfxkit, vendored effekseer_ai), assets/ (Godot Lab, materials, rubric,
                           brief schema, examples)
skills/vfx-review/         SKILL.md for the independent reviewer
docs/zh/, docs/ja/         Chinese and Japanese translations of the references
.claude-plugin/            Claude Code plugin and marketplace manifests
tests/                     pure-Python tests (no Core or Godot needed)
```

## Limitations

- Review metrics are pixel heuristics on the real viewport, not GPU or overdraw measurements.
- The review harness drives a windowed Godot on macOS and Windows; headless Linux capture is not supported yet. On
  Windows the Godot window keeps focus while it captures (macOS hands focus back to your app).
- On Windows, the symlink-safety tests need Developer Mode (or an administrator shell) and are skipped without it.
- Example scores are an independent review of the skill's own capsule-Lab renders (two of the sixteen were judged
  `iterate`); rebuild and review before relying on them.
- `soft` particles are verified in Forward+ (they fade against opaque depth only); the Compatibility renderer has no
  depth texture and cannot use them.

## Development

```sh
sh skills/effekseer-vfx/scripts/setup.sh --authoring-only
~/.cache/effekseer-vfx/venv/bin/python -m pip install pytest
~/.cache/effekseer-vfx/venv/bin/python -m pytest -q tests
```

On Windows (PowerShell; drop `--authoring-only` to also run the EffekseerCore build tests):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File skills\effekseer-vfx\scripts\setup.ps1 --authoring-only
~\.cache\effekseer-vfx\venv\Scripts\python.exe -m pip install pytest   # a venv made by uv: uv pip install --python <that python.exe> pytest
~\.cache\effekseer-vfx\venv\Scripts\python.exe -X utf8 -m pytest -q tests
```

Contributions that confirm a new engine convention should add it to
`skills/effekseer-vfx/references/engine-conventions.md` together with how it was measured.

## License

MIT, see [LICENSE](LICENSE). Third-party components and downloads: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Effekseer and Godot are trademarks of their respective owners; this project is not affiliated with them.

Made by KanaWorks_AI ([@KanaWorks_AI](https://x.com/KanaWorks_AI) on X).
