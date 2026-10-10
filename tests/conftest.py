"""Shared test setup for the effekseer-vfx skill.

vfxkit.paths computes the project ROOT when it is first imported, so this file points VFX_PROJECT at a fresh
temporary game project *before* anything imports vfxkit, initialises its vfx/ workspace without the Godot plugin
and adds the thirteen shipped example effects. Those examples are the library every library-wide test checks.

Tests that need an isolated workspace either monkeypatch the module-level ROOT/WORK attributes (as the original
pipeline tests did) or run the CLI in a subprocess with --project.
"""
import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.dont_write_bytecode = True  # never leave __pycache__ inside the (read-only at run time) skill folder

TESTS = Path(__file__).resolve().parent
PACKAGE = TESTS.parent
SKILL = PACKAGE / 'skills/effekseer-vfx'
SCRIPTS = SKILL / 'scripts'
ASSETS = SKILL / 'assets'

PROJECT = Path(tempfile.mkdtemp(prefix='vfx-skill-tests-')).resolve()
os.environ['VFX_PROJECT'] = str(PROJECT)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
atexit.register(shutil.rmtree, PROJECT, True)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vfxkit import paths  # noqa: E402  (must follow VFX_PROJECT)

assert paths.ROOT == PROJECT, 'vfxkit was imported before conftest set VFX_PROJECT'

# The vfx wrapper exports EFFEKSEER_AI_BIN_DIR from the toolchain; do the same when a full toolchain is installed.
if not os.environ.get('EFFEKSEER_AI_BIN_DIR') and (paths.CORE_BIN / 'EffekseerCore.dll').is_file():
    os.environ['EFFEKSEER_AI_BIN_DIR'] = str(paths.CORE_BIN)
    os.environ.setdefault('DOTNET_ROOT', str(paths.HOME / 'dotnet'))

from vfxkit import scaffold, examples  # noqa: E402

scaffold.initialize(install_plugin=False)
examples.add('all')



def _can_symlink():
    probe = Path(tempfile.mkdtemp(prefix='vfx-link-probe-'))
    try:
        (probe / 'link').symlink_to(probe / 'target')
        return True
    except OSError:  # Windows without Developer Mode or administrator rights
        return False
    finally:
        shutil.rmtree(probe, True)


requires_symlinks = pytest.mark.skipif(not _can_symlink(), reason='creating symlinks needs Developer Mode or administrator rights on Windows')
posix_only = pytest.mark.skipif(os.name == 'nt', reason='POSIX sh scripts; Windows uses vfx.cmd and setup.ps1')
windows_only = pytest.mark.skipif(os.name != 'nt', reason='Windows launchers')
CORE_READY = bool(os.environ.get('EFFEKSEER_AI_BIN_DIR') and (Path(os.environ['EFFEKSEER_AI_BIN_DIR']) / 'EffekseerCore.dll').is_file())
requires_core = pytest.mark.skipif(not CORE_READY, reason='Initialize the local EffekseerCore runtime first (sh scripts/setup.sh)')


def cli_env(**extra):
    """Environment for running `python -m vfxkit` in a subprocess with the scripts folder importable."""
    env = dict(os.environ)
    env['PYTHONPATH'] = str(SCRIPTS) + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env.update(extra)
    return env


@pytest.fixture
def project():
    """The shared temporary game project whose vfx/src holds the thirteen examples."""
    return PROJECT
