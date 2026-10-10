"""What this machine can do right now. Standard library only, so it runs before setup."""
import importlib.util
import json
import platform
import shutil
import subprocess
from pathlib import Path
from .paths import ROOT, WORKSPACE, WORK, HOME, CORE_BIN, DOTNET, WINDOWS, godot, initialized, full_mode_platform, setup_command
from .ownership import owned, unmanaged


def version(command):
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def setup_python():
    """What setup.sh (setup.ps1 on Windows) would use for the toolchain: uv, else a Python 3.11+ (same search order)."""
    if shutil.which('uv'):
        return 'uv'
    check = ['-c', 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)']
    if WINDOWS:  # the py launcher picks an installed version; `python` may be the Microsoft Store stub
        candidates = [(['py', f'-3.{minor}'], 'py') for minor in (13, 12, 11)] + [([name], name) for name in ('python', 'python3')]
    else:
        candidates = [([name], name) for name in ('python3.13', 'python3.12', 'python3.11', '/opt/homebrew/bin/python3', '/usr/local/bin/python3', 'python3')]
    for prefix, name in candidates:
        found = shutil.which(name)
        if found:
            try:
                ok = subprocess.run([found, *prefix[1:], *check], capture_output=True, timeout=20).returncode == 0
            except (OSError, subprocess.SubprocessError):
                ok = False
            if ok:
                return ' '.join([found, *prefix[1:]])
    return None


def doctor():
    full = full_mode_platform()
    python_deps = {m: importlib.util.find_spec(m) is not None for m in ('numpy', 'PIL', 'jsonschema', 'clr_loader')}
    dotnet = DOTNET
    godot_cmd = godot()
    godot_version = version([godot_cmd, '--version']) if shutil.which(godot_cmd) or Path(godot_cmd).is_file() else None
    core = (CORE_BIN / 'EffekseerCore.dll').is_file()
    authoring = all(python_deps[m] for m in ('numpy', 'PIL', 'jsonschema'))
    build = authoring and python_deps['clr_loader'] and core and dotnet.is_file()
    render = build and bool(godot_version)
    manifest = WORKSPACE / 'vfx_manifest.json'
    entries = json.loads(manifest.read_text()) if manifest.is_file() else []
    workspace = {'path': str(WORKSPACE), 'initialized': initialized(),
                 'effects': len(list((WORKSPACE / 'src').glob('VFX_*.py'))) if (WORKSPACE / 'src').is_dir() else 0,
                 'built': sum(1 for e in entries if owned(e, ROOT, WORK)),
                 # Effects this skill did not build (unowned manifest entries and stray .efkefc files): left alone.
                 'unmanaged': len(unmanaged(ROOT, WORK, entries)) if WORKSPACE.is_dir() else 0}
    next_steps = []
    installer = setup_python() if not authoring else None
    if not authoring and not installer:
        python_hint = ('`winget install Python.Python.3.12`' if WINDOWS else '`brew install python@3.12`')
        next_steps.append('setup needs Python 3.11+ or uv, and neither was found' + ('' if WINDOWS else ' (macOS ships Python 3.9)') +
                          ': ask the user to install uv (https://docs.astral.sh/uv/getting-started/installation/) or ' + python_hint)
    if not authoring:
        next_steps.append(setup_command(authoring_only=not full))
    elif full and not build:
        next_steps.append(setup_command() + '  (downloads Effekseer Core and the .NET runtime)')
    if full and authoring and not godot_version:
        next_steps.append('install Godot 4.x (Forward+) and put it on PATH or set GODOT')
    if WORKSPACE.is_dir() and not workspace['initialized']:
        next_steps.append(f'{WORKSPACE} exists but was not created by vfx init: check this is the game project (or pass --project) '
                          'before running vfx init here; init only adds files, and builds never touch effects they did not build')
    if authoring and not workspace['initialized']:
        next_steps.append('vfx init' + ('' if render else ' --no-plugin'))
    return {'ok': True,
            'platform': {'system': platform.system(), 'machine': platform.machine(), 'python': platform.python_version(),
                         'full_mode_supported': full},
            'modes': {'authoring': authoring, 'build': build, 'render': render},
            'toolchain': {'home': str(HOME), 'python_packages': python_deps, 'setup_python': installer if not authoring else 'installed', 'effekseer_core': core, 'dotnet': dotnet.is_file(),
                          'godot': godot_version, 'ffmpeg': bool(shutil.which('ffmpeg'))},
            'project': str(ROOT), 'workspace': workspace,
            'note': 'authoring = write recipes, lint, textures and briefs; build = compile through EffekseerCore; render = Godot review strips. '
                    'Build and render are verified on macOS ARM64 and Windows x64 (Windows ARM64 is set up but unverified). render: true means Godot was found; review still needs a window '
                    'on the logged-in desktop, so a sandboxed agent must run review/preview/showcase outside its sandbox.',
            'next': next_steps}
