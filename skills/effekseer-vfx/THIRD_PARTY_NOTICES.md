# Third-party notices

## Included in this repository

| Component | Where | License | Notes |
|---|---|---|---|
| effekseer-ai (laodeng000/effekseer-ai, commit `208922ef192220322c2a79e1243ed51ff7d2b7af`) | `skills/effekseer-vfx/scripts/effekseer_ai/` | MIT, see `scripts/effekseer_ai/LICENSE` | Vendored and extended: structured layer compiler, procedural models, texture processing, Godot preview. Its agent server entry point was removed; the skill uses a command line instead. |
| Example textures | `skills/effekseer-vfx/assets/examples/textures/` | this repository's MIT license | Made with an image generation model from the prompts in `assets/examples/texture_prompts.json`, then post-processed; originals are not included. |

## Downloaded on first use (not redistributed)

| Component | Downloaded by | License |
|---|---|---|
| Effekseer 1.80.7 for Windows (only its managed Core assemblies are loaded) — https://github.com/effekseer/Effekseer/releases/tag/1807 | `scripts/setup.sh` / `scripts/setup.ps1`, SHA-256 pinned | MIT (Effekseer Project); the archive's `LICENSE_TOOL` lists its bundled components |
| EffekseerForGodot4 1.80.5.1 — https://github.com/effekseer/EffekseerForGodot4/releases/tag/1.80.5.1 | `vfx init`, SHA-256 pinned | MIT; its LICENSE is copied into `vfx/godot/addons/effekseer/`. `init` changes one line of `plugin.gd` so the editor icon loads before the first import; the renderer is unchanged. |
| .NET 9 runtime (9.0.20) — official Microsoft archives `dotnet-runtime-9.0.20-osx-arm64.tar.gz` (macOS), `dotnet-runtime-9.0.20-win-x64.zip` / `-win-arm64.zip` (Windows) | `scripts/setup.sh` / `scripts/setup.ps1`, SHA-256 pinned | MIT |
| Python packages in `scripts/requirements.lock.txt` (numpy, Pillow, jsonschema, pythonnet, ...) | `scripts/setup.sh` / `scripts/setup.ps1`, pinned by version (not by hash) | their own permissive licenses |

Godot and ffmpeg are not downloaded; install them yourself under their licenses.

This project is not affiliated with or endorsed by the Effekseer project or the Godot Foundation.
