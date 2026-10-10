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
WINDOWS = os.name == 'nt'
# The toolchain's Python and .NET host: Windows venvs keep executables in Scripts\ and add .exe.
VENV_PYTHON = HOME / ('venv/Scripts/python.exe' if WINDOWS else 'venv/bin/python')
DOTNET = HOME / ('dotnet/dotnet.exe' if WINDOWS else 'dotnet/dotnet')


def full_mode_platform():
    """Where build and render (EffekseerCore through .NET, the Effekseer Godot plugin) are supported:
    macOS on Apple silicon and Windows on x64 or ARM64."""
    import platform
    import sys
    machine = platform.machine().lower()
    if sys.platform == 'darwin':
        return machine == 'arm64'
    return WINDOWS and machine in ('amd64', 'x86_64', 'arm64')


def setup_command(authoring_only=False):
    """How to run setup on this system, as a command an agent can run from the project."""
    flag = ' --authoring-only' if authoring_only else ''
    if WINDOWS:
        return f'powershell -NoProfile -ExecutionPolicy Bypass -File "{SCRIPTS / "setup.ps1"}"{flag}'
    return f'sh {SCRIPTS}/setup.sh{flag}'


def godot():
    """Godot 4 executable: GODOT, then `godot` (or `godot4`) on PATH, then the standard macOS application bundle.
    Windows has no standard location (the official download is a loose .exe): use PATH (Scoop, winget) or GODOT."""
    import shutil
    configured = os.environ.get('GODOT')
    if configured:
        return configured
    for name in ('godot', 'godot4'):
        found = shutil.which(name)
        if found:
            return found
    bundle = Path('/Applications/Godot.app/Contents/MacOS/Godot')
    return str(bundle) if bundle.is_file() else 'godot'
