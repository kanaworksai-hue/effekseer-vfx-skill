"""Where the skill's own files live, where the toolchain is installed and which game project is being edited.

The skill folder is read-only at run time (agents may install it into a versioned cache). Everything an
effect produces lives in the project's `vfx/` workspace; downloaded tools live in EFFEKSEER_VFX_HOME.
"""
import os
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2]
SCRIPTS = SKILL / 'scripts'
ASSETS = SKILL / 'assets'
REFERENCES = SKILL / 'references'

# The game project that owns the vfx/ workspace: --project, then VFX_PROJECT, then the current directory.
ROOT = Path(os.environ.get('VFX_PROJECT') or Path.cwd()).expanduser().resolve()
WORKSPACE = ROOT / 'vfx'
# Local receipts, locks and scratch images; ignored by version control.
WORK = WORKSPACE / 'work'


def initialized():
    """`vfx init` has run here: a vfx/ folder that merely exists (another tool's output) does not count."""
    return (WORKSPACE / 'src').is_dir() and (WORKSPACE / 'vfx_manifest.json').is_file()

HOME = Path(os.environ.get('EFFEKSEER_VFX_HOME') or Path.home() / '.cache/effekseer-vfx').expanduser().resolve()
EFFEKSEER_VERSION = '1.80.7'
CORE_BIN = HOME / 'effekseer/Effekseer1.80.7Win/Tool/bin'
DOWNLOADS = HOME / 'downloads'


def godot():
    """Godot 4 executable: GODOT, then `godot` on PATH, then the standard macOS application bundle."""
    import shutil
    configured = os.environ.get('GODOT')
    if configured:
        return configured
    found = shutil.which('godot')
    if found:
        return found
    bundle = Path('/Applications/Godot.app/Contents/MacOS/Godot')
    return str(bundle) if bundle.is_file() else 'godot'
