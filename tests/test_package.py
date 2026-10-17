"""Contracts specific to the self-contained skill package: CLI, workspace layout, recipe loading and paths."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SCRIPTS, SKILL, cli_env, posix_only, windows_only


def vfx(*args, cwd=None, env=None):
    """Run the CLI with the test interpreter; returns (exit code, parsed JSON stdout)."""
    run = subprocess.run([sys.executable, '-m', 'vfxkit', *args], capture_output=True, text=True, cwd=cwd, env=env or cli_env(), timeout=300)
    lines = run.stdout.strip().splitlines()
    assert len(lines) == 1, (run.stdout, run.stderr)  # exactly one JSON object on stdout
    return run.returncode, json.loads(lines[0])


def system_python():
    for candidate in ('/usr/bin/python3', '/usr/local/bin/python3', shutil.which('python3')):
        if candidate and Path(candidate).is_file() and Path(candidate).resolve() != Path(sys.executable).resolve():
            return candidate
    return None


@posix_only
def test_doctor_runs_through_the_wrapper_on_a_bare_system_python(tmp_path):
    python = system_python()
    if not python:
        pytest.skip('no system python3 separate from the test interpreter')
    # An empty toolchain home: the wrapper falls back to the system python3 and doctor needs only the standard library.
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'python3').symlink_to(python)
    env = {'PATH': f'{bin_dir}:/usr/bin:/bin', 'HOME': str(tmp_path / 'home'), 'EFFEKSEER_VFX_HOME': str(tmp_path / 'toolchain'),
           'VFX_PROJECT': str(tmp_path / 'game')}
    run = subprocess.run(['sh', str(SCRIPTS / 'vfx'), 'doctor'], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=120)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result['ok'] is True and set(result['modes']) == {'authoring', 'build', 'render'}
    assert result['project'] == str((tmp_path / 'game').resolve())
    assert not result['workspace']['initialized'] and result['workspace']['effects'] == 0
    assert result['toolchain']['home'] == str((tmp_path / 'toolchain').resolve())
    assert not result['toolchain']['effekseer_core'] and not result['modes']['build']
    assert result['next'], 'doctor must say what to do next on an empty machine'



@windows_only
def test_doctor_runs_through_vfx_cmd_on_a_bare_system_python(tmp_path):
    if not (shutil.which('py') or shutil.which('python')):
        pytest.skip('no system Python for vfx.cmd to fall back to')
    # An empty toolchain home: vfx.cmd falls back to the py launcher (or python) and doctor needs only the standard library.
    keep = ('SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATH', 'PATHEXT', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA', 'TEMP', 'TMP')
    env = {**{k: os.environ[k] for k in keep if k in os.environ},
           'EFFEKSEER_VFX_HOME': str(tmp_path / 'toolchain'), 'VFX_PROJECT': str(tmp_path / 'game')}
    run = subprocess.run([str(SCRIPTS / 'vfx.cmd'), 'doctor'], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=120)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result['ok'] is True and set(result['modes']) == {'authoring', 'build', 'render'}
    assert result['project'] == str((tmp_path / 'game').resolve())
    assert result['toolchain']['home'] == str((tmp_path / 'toolchain').resolve())
    assert not result['toolchain']['effekseer_core'] and not result['modes']['build']
    assert any('setup.ps1' in step for step in result['next']), result['next']


@windows_only
def test_setup_ps1_rejects_unknown_options_before_touching_anything(tmp_path):
    home = tmp_path / 'toolchain'
    run = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(SCRIPTS / 'setup.ps1'), '--bogus'],
                         capture_output=True, text=True, env={**os.environ, 'EFFEKSEER_VFX_HOME': str(home)}, timeout=120)
    assert run.returncode == 2 and '--authoring-only' in run.stderr, run.stderr
    assert not home.exists()


def test_launchers_keep_the_line_endings_their_shells_need():
    # A Windows clone with core.autocrlf would give the sh scripts CRLF (sh then fails on `set -eu\r`); .gitattributes
    # pins LF for them and CRLF for the batch launcher. Windows PowerShell reads a script without a BOM as ANSI: keep it ASCII.
    for name in ('vfx', 'setup.sh'):
        assert b'\r' not in (SCRIPTS / name).read_bytes(), name
    assert b'\r\n' in (SCRIPTS / 'vfx.cmd').read_bytes()
    assert (SCRIPTS / 'setup.ps1').read_bytes().isascii()


def test_doctor_reports_an_initialised_workspace(project):
    code, result = vfx('--project', str(project), 'doctor')
    assert code == 0 and result['modes']['authoring']
    assert result['workspace']['initialized'] and result['workspace']['effects'] == 16


def test_help_lists_commands_without_dependencies(tmp_path):
    run = subprocess.run([sys.executable, '-m', 'vfxkit', '--help'], capture_output=True, text=True, env=cli_env(), timeout=60)
    assert run.returncode == 0 and 'examples' in run.stdout and 'doctor' in run.stdout


def test_cli_init_examples_and_lint_in_a_fresh_project(tmp_path):
    game = tmp_path / 'game'
    code, result = vfx('--project', str(game), 'init', '--no-plugin', cwd=tmp_path)
    assert code == 0 and result['ok'] and result['workspace'] == str(game.resolve() / 'vfx')
    assert (game / 'vfx/textures/processed/T_Glow01.png').is_file()
    code, result = vfx('--project', str(game), 'lint', cwd=tmp_path)
    assert code == 1 and 'No recipes' in result['error']['message']
    code, result = vfx('--project', str(game), 'examples', 'add', 'ice', cwd=tmp_path)
    assert code == 0 and result['effects'] == ['VFX_Projectile_Ice', 'VFX_Ice_Spikes']
    assert 'vfx/src/VFX_Ice_Spikes.py' in result['copied'] and 'vfx/briefs/VFX_Ice_Spikes.json' in result['copied']
    code, result = vfx('--project', str(game), 'lint', '--ids', 'VFX_Ice_Spikes', cwd=tmp_path)
    assert code == 0 and result['ok'] and result['errors'] == {}
    code, result = vfx('--project', str(game), 'lint', '--ids', 'VFX_Nope', cwd=tmp_path)
    assert code == 1 and 'Unknown effect IDs' in result['error']['message']
    code, result = vfx('--project', str(game), 'brief-validate', 'VFX_Ice_Spikes', cwd=tmp_path)
    assert code == 0 and result['ok']
    code, result = vfx('--project', str(game), 'list', cwd=tmp_path)
    assert code == 0 and [e['id'] for e in result['effects']] == ['VFX_Ice_Spikes', 'VFX_Projectile_Ice']
    assert not any(e['built'] for e in result['effects'])
    # Nothing was written outside the chosen project.
    assert not (tmp_path / 'vfx').exists()


def test_examples_add_does_not_overwrite_without_force(tmp_path):
    game = tmp_path / 'game'
    code, first = vfx('--project', str(game), 'examples', 'add', 'fire')
    assert code == 0 and not first['skipped_existing']
    source = game / 'vfx/src/VFX_Projectile_Fire.py'
    brief = game / 'vfx/briefs/VFX_Projectile_Fire.json'
    source.write_text(source.read_text() + '\n# my edit\n')
    brief_text = brief.read_text()
    code, again = vfx('--project', str(game), 'examples', 'add', 'fire')
    assert code == 0 and 'vfx/src/VFX_Projectile_Fire.py' in again['skipped_existing']
    assert 'vfx/src/VFX_Projectile_Fire.py' not in again['copied']
    assert source.read_text().endswith('# my edit\n') and brief.read_text() == brief_text
    prompts = json.loads((game / 'vfx/texture_prompts.json').read_text())['prompts']
    assert len({p['id'] for p in prompts}) == len(prompts), 'adding twice must not duplicate texture prompts'
    code, forced = vfx('--project', str(game), 'examples', 'add', 'fire', '--force')
    assert code == 0 and 'vfx/src/VFX_Projectile_Fire.py' in forced['copied']
    assert source.read_bytes() == (SKILL / 'assets/examples/src/VFX_Projectile_Fire.py').read_bytes()


def test_examples_list_and_show_without_a_workspace(tmp_path):
    code, result = vfx('--project', str(tmp_path / 'none'), 'examples', cwd=tmp_path)
    assert code == 0 and [p['name'] for p in result['pairs']] == ['fire', 'ice', 'poison', 'dark']
    assert [s['name'] for s in result['singles']] == ['hit', 'slash', 'charge', 'shield', 'heal']
    code, result = vfx('--project', str(tmp_path / 'none'), 'examples', 'show', 'slash', cwd=tmp_path)
    assert code == 0 and result['id'] == 'VFX_Slash_Fire' and isinstance(result['lint'], str)  # no workspace: no texture lint
    code, result = vfx('--project', str(tmp_path / 'none'), 'examples', 'add', cwd=tmp_path)
    assert code == 1 and 'Name an example' in result['error']['message']
    assert not (tmp_path / 'none').exists()


def test_rubric_and_layer_schema_commands(project):
    code, rubric = vfx('--project', str(project), 'rubric')
    assert code == 0 and [c['id'] for c in rubric['criteria']] == ['read', 'timing', 'layering', 'shape_change', 'motion', 'placement', 'tail', 'identity', 'coherence']
    code, schema = vfx('--project', str(project), 'layer-schema')
    assert code == 0 and schema['ok'] and 'fade_out' in json.dumps(schema)


def test_effect_verify_reports_missing_evidence_and_fails(project, tmp_path):
    game = tmp_path / 'game'
    vfx('--project', str(game), 'examples', 'add', 'VFX_Ice_Spikes')
    code, result = vfx('--project', str(game), 'effect-verify', 'VFX_Ice_Spikes')
    assert code == 1 and result['ok'] and not result['verified']
    assert {'missing_build_receipt', 'missing_standard_capture'} <= set(result['issues'])
    code, result = vfx('--project', str(game), 'brief-validate', 'not-an-id')
    assert code == 1 and 'effect ID' in result['error']['message']


def test_library_load_rejects_id_file_mismatch_and_missing_recipe(tmp_path):
    from vfxkit.library import load
    mismatch = tmp_path / 'VFX_Foo.py'
    mismatch.write_text("from vfxkit.primitives import *\n\ndef recipe():\n return effect('Bar','Bar','hit','fire',.5,[flash('c',WHITE,1)])\n")
    with pytest.raises(ValueError, match="id is 'VFX_Foo', got 'VFX_Bar'"):
        load(mismatch)
    missing = tmp_path / 'VFX_None.py'
    missing.write_text('VALUE = 1\n')
    with pytest.raises(ValueError, match=r'define recipe\(\)'):
        load(missing)
    not_dict = tmp_path / 'VFX_List.py'
    not_dict.write_text('def recipe():\n return []\n')
    with pytest.raises(ValueError, match='must return effect'):
        load(not_dict)
    good = tmp_path / 'VFX_Foo2.py'
    good.write_text("from vfxkit.primitives import *\n\ndef recipe():\n return effect('Foo2','Foo','hit','fire',.5,[flash('c',WHITE,1)])\n")
    assert load(good)['id'] == 'VFX_Foo2'


def test_library_get_rejects_unknown_ids_and_reloads_helpers(tmp_path, monkeypatch):
    from vfxkit import library
    src = tmp_path / 'vfx/src'
    src.mkdir(parents=True)
    monkeypatch.setattr(library, 'SRC', src)
    with pytest.raises(ValueError, match='Unknown effect ID'):
        library.get('VFX_Missing')
    (src / '_shared.py').write_text('LIFE = 10\n')
    (src / 'VFX_Uses.py').write_text("from vfxkit.primitives import *\nimport _shared\n\n"
                                     "def recipe():\n return effect('Uses','Uses','hit','fire',.5,[flash('c',WHITE,1,life=_shared.LIFE)])\n")
    try:
        assert library.get('VFX_Uses')['layers'][0]['life'] == 10
        (src / '_shared.py').write_text('LIFE = 4\n')
        # A helper edit is picked up without restarting: sources and helpers load fresh on every call.
        assert library.get('VFX_Uses')['layers'][0]['life'] == 4
        assert [r['id'] for r in library.library()] == ['VFX_Uses']
    finally:
        if str(src) in sys.path:
            sys.path.remove(str(src))
        sys.modules.pop('_shared', None)


def test_workflow_relative_absolute_round_trip_for_project_skill_and_toolchain_paths():
    from vfxkit import workflow
    from vfxkit.paths import ROOT, SKILL as PKG_SKILL, HOME
    assert PKG_SKILL == SKILL
    cases = {ROOT / 'vfx/src/VFX_Fire_Explosion.py': 'vfx/src/VFX_Fire_Explosion.py',
             SKILL / 'assets/brief.schema.json': 'skill:assets/brief.schema.json',
             SKILL / 'scripts/vfxkit/lint.py': 'skill:scripts/vfxkit/lint.py',
             HOME / 'venv/bin/python': 'toolchain:venv/bin/python',
             HOME / 'effekseer/Effekseer1.80.7Win/Tool/bin/EffekseerCore.dll': 'toolchain:effekseer/Effekseer1.80.7Win/Tool/bin/EffekseerCore.dll'}
    for path, name in cases.items():
        assert workflow.relative(path) == name
        assert workflow.absolute(name) == Path(os.path.abspath(path))
        assert workflow.relative(workflow.absolute(name)) == name
    with pytest.raises(ValueError, match='outside the project'):
        workflow.relative(Path('/') / 'definitely-not-a-vfx-location' / 'x.png')
    # A snapshot keys files the same way, so receipts never carry absolute machine paths.
    snapshot = workflow.snapshot([SKILL / 'assets/brief.schema.json', ROOT / 'vfx/missing.png'])
    assert snapshot['skill:assets/brief.schema.json'] and snapshot['vfx/missing.png'] is None
    assert not workflow.unchanged(snapshot)
    assert workflow.unchanged({'skill:assets/brief.schema.json': snapshot['skill:assets/brief.schema.json']})


def test_paths_follow_vfx_project_and_toolchain_environment(tmp_path):
    code = ('import json,vfxkit.paths as p;print(json.dumps([str(p.ROOT),str(p.WORKSPACE),str(p.WORK),str(p.HOME),str(p.CORE_BIN)]))')
    env = cli_env(VFX_PROJECT=str(tmp_path / 'game'), EFFEKSEER_VFX_HOME=str(tmp_path / 'tools'))
    run = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, cwd=tmp_path, check=True)
    root, workspace, work, home, core = map(Path, json.loads(run.stdout))
    assert root == (tmp_path / 'game').resolve() and workspace == root / 'vfx' and work == root / 'vfx/work'
    assert home == (tmp_path / 'tools').resolve() and core == home / 'effekseer/Effekseer1.80.7Win/Tool/bin'
    env.pop('VFX_PROJECT')
    run = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=env, cwd=tmp_path, check=True)
    assert Path(json.loads(run.stdout)[0]) == tmp_path.resolve()  # default: the current directory


def test_effect_ids_are_validated_before_touching_files():
    from vfxkit import workflow
    assert workflow.effect_id('VFX_Fire_Explosion') == 'VFX_Fire_Explosion'
    for bad in ('../VFX_X', 'VFX_', 'Fire', 'VFX_a/b', None, 3):
        with pytest.raises(ValueError):
            workflow.effect_id(bad)


HIT_SPARK = '''from vfxkit.primitives import *
def recipe():
    hot = (255, 240, 200, 255)
    return effect('Hit_Spark', 'Spark Hit', 'hit', 'physical', .4, [
        flash('Contact flash', WHITE, 2.2, life=4, delay=1),
        glow('Bloom', (255, 170, 70, 170), 1.6, life=9, delay=1),
        radial_sparks('Sparks', 10, hot, color_end=(255, 120, 30, 255), distance=(.8, 1.7), life=(12, 16), delay=1, gravity=.0018),
        smoke('Dust', (185, 160, 135, 200), count=2, size=(.5, .7), life=(13, 14), delay=4),
    ], peak=.03, impact=.3, delivery=MELEE, design='One-line description of what the player sees.')
'''


def test_a_fresh_project_lints_a_recipe_that_uses_primitive_default_textures(tmp_path):
    # smoke() defaults to the painted T_SmokeSheet01: init must install the starter textures and their prompts.
    game = tmp_path / 'game'
    code, result = vfx('--project', str(game), 'init', '--no-plugin', cwd=tmp_path)
    assert code == 0 and result['ok']
    (game / 'vfx/src/VFX_Hit_Spark.py').write_text(HIT_SPARK)
    code, result = vfx('--project', str(game), 'lint', cwd=tmp_path)
    assert code == 0 and result['ok'] and result['errors'] == {}, result


def test_init_installs_starter_textures_without_overwriting_or_duplicating_prompts(tmp_path):
    from vfxkit.scaffold import initialize
    starters = sorted((SKILL / 'assets/examples/textures').glob('*.png'))
    assert {p.stem for p in starters} >= {'T_SmokeSheet01', 'T_WispTrail01', 'T_ExplosionSheet01'}
    processed = tmp_path / 'vfx/textures/processed'
    processed.mkdir(parents=True)
    (processed / 'T_SmokeSheet01.png').write_bytes(b'my own sheet')
    initialize(tmp_path, install_plugin=False)
    assert (processed / 'T_SmokeSheet01.png').read_bytes() == b'my own sheet'
    for path in starters:
        if path.stem != 'T_SmokeSheet01':
            assert (processed / path.name).read_bytes() == path.read_bytes(), path.name
    prompts_path = tmp_path / 'vfx/texture_prompts.json'
    prompts = json.loads(prompts_path.read_text())['prompts']
    assert {p.stem for p in starters} <= {p['id'] for p in prompts}
    custom = [{'id': 'T_Mine01', 'prompt': 'mine'}] + prompts
    prompts_path.write_text(json.dumps({'prompts': custom}))
    initialize(tmp_path, install_plugin=False)
    again = json.loads(prompts_path.read_text())['prompts']
    assert again == custom  # nothing added twice, project entries kept
