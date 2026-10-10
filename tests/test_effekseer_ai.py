"""The vendored effekseer_ai bridge: portable CLI surface and an explicit, never-guessed Core location."""
from pathlib import Path

import pytest

from conftest import SCRIPTS


def test_cli_exposes_only_the_portable_effect_bridge_commands():
    from effekseer_ai.cli import build_parser
    parser = build_parser()
    command_parser = next(action for action in parser._actions if action.dest == 'command')
    commands = set(command_parser.choices)
    assert {'new', 'open', 'save', 'export', 'node-list', 'node-add', 'compile', 'texture-process'} <= commands
    assert not {'generate', 'model-convert', 'model-import', 'experience-record', 'experience-search', 'experience-brief'} & commands


def test_cli_rejects_removed_recipe_commands():
    from effekseer_ai.cli import build_parser
    with pytest.raises(SystemExit):
        build_parser().parse_args(['generate', 'black-hole', 'effect.efkefc'])


def test_vendored_package_has_no_protocol_server_and_keeps_its_license():
    folder = SCRIPTS / 'effekseer_ai'
    assert (folder / 'LICENSE').is_file() and 'MIT' in (folder / 'LICENSE').read_text()
    assert not list(folder.glob('*server*.py'))


def test_editor_bin_directory_requires_an_explicit_configuration(monkeypatch):
    """A public release must never probe a contributor's local disks."""
    monkeypatch.delenv('EFFEKSEER_AI_BIN_DIR', raising=False)
    from effekseer_ai.runtime import editor_bin_directory
    with pytest.raises(RuntimeError, match='EFFEKSEER_AI_BIN_DIR'):
        editor_bin_directory()


def test_editor_bin_directory_rejects_a_directory_without_core(tmp_path, monkeypatch):
    monkeypatch.setenv('EFFEKSEER_AI_BIN_DIR', str(tmp_path))
    from effekseer_ai.runtime import editor_bin_directory
    with pytest.raises(RuntimeError, match='EffekseerCore.dll'):
        editor_bin_directory()


def test_editor_bin_directory_uses_a_configured_core_directory(tmp_path, monkeypatch):
    core_directory = tmp_path / 'Tool' / 'bin'
    core_directory.mkdir(parents=True)
    (core_directory / 'EffekseerCore.dll').touch()
    monkeypatch.setenv('EFFEKSEER_AI_BIN_DIR', str(core_directory))
    from effekseer_ai.runtime import editor_bin_directory
    assert editor_bin_directory() == core_directory


def test_runtime_config_is_bundled():
    from effekseer_ai.runtime import runtime_config_path
    path = runtime_config_path()
    assert Path(path).is_file() and Path(path).is_relative_to(SCRIPTS / 'effekseer_ai')
