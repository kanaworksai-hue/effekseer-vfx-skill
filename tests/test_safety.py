"""The skill never damages a project it was pointed at by mistake: no workspace side effects, no deleting effects it
did not build, no single broken source blocking the rest, and no project file shadowing a module."""
import json
import subprocess
import sys

import pytest

from conftest import SCRIPTS, SKILL, cli_env, requires_core
from test_package import vfx


def game(tmp_path, *examples):
    root = tmp_path / 'game'
    code, result = vfx('--project', str(root), 'init', '--no-plugin')
    assert code == 0, result
    for name in examples:
        code, result = vfx('--project', str(root), 'examples', 'add', name)
        assert code == 0, result
    return root


@pytest.mark.parametrize('command', [['list'], ['lint'], ['history', 'VFX_Heal'], ['overview'], ['build'], ['effect-verify', 'VFX_Heal']])
def test_commands_need_a_workspace_and_never_create_one(tmp_path, command):
    code, result = vfx(*command, cwd=tmp_path, env=cli_env(VFX_PROJECT=str(tmp_path)))
    assert code == 2 and result['error']['type'] == 'WorkspaceMissing'
    assert not (tmp_path / 'vfx').exists()


def test_a_vfx_folder_from_another_tool_is_not_a_workspace(tmp_path):
    (tmp_path / 'vfx/effects').mkdir(parents=True)
    (tmp_path / 'vfx/effects/VFX_Theirs.efkefc').write_bytes(b'not ours')
    (tmp_path / 'vfx/vfx_manifest.json').write_text(json.dumps([{'id': 'VFX_Theirs', 'duration': 1.0}]))
    code, result = vfx('--project', str(tmp_path), 'build')
    assert code == 2 and result['error']['type'] == 'WorkspaceMissing'
    code, result = vfx('--project', str(tmp_path), 'doctor')
    assert not result['workspace']['initialized'] and result['workspace']['unmanaged'] == 1
    assert any('not created by vfx init' in step for step in result['next'])
    assert (tmp_path / 'vfx/effects/VFX_Theirs.efkefc').read_bytes() == b'not ours'


def test_a_full_build_of_an_empty_library_refuses_before_touching_anything(tmp_path):
    root = game(tmp_path)
    (root / 'vfx/effects/VFX_Theirs.efkefc').write_bytes(b'not ours')
    code, result = vfx('--project', str(root), 'build')
    assert code == 1 and 'No recipes' in result['error']['message'] and 'Nothing was built or pruned' in result['error']['message']
    assert (root / 'vfx/effects/VFX_Theirs.efkefc').read_bytes() == b'not ours'


def test_a_broken_source_only_blocks_itself(tmp_path):
    root = game(tmp_path, 'hit', 'heal')
    (root / 'vfx/src/VFX_Broken.py').write_text('def recipe(:\n')
    code, result = vfx('--project', str(root), 'lint', '--ids', 'VFX_Heal')
    assert code == 0 and result['ok'] and 'SyntaxError' in result['unloaded']['VFX_Broken']
    code, result = vfx('--project', str(root), 'list')
    assert code == 0 and {e['id'] for e in result['effects']} == {'VFX_Hit_Heavy', 'VFX_Heal'} and 'VFX_Broken' in result['unloaded']
    code, result = vfx('--project', str(root), 'lint')  # a full lint (and a full build) needs every source
    assert code == 1 and result['error']['type'] == 'SyntaxError'
    code, result = vfx('--project', str(root), 'lint', '--ids', 'VFX_Broken')
    assert code == 1 and result['error']['type'] == 'SyntaxError'


def test_project_files_never_shadow_modules(tmp_path):
    root = game(tmp_path, 'heal')
    src = root / 'vfx/src'
    (src / '_palette.py').write_text('PALE = (225, 255, 235, 255)\n')
    (src / 'random.py').write_text('raise RuntimeError("vfx/src/random.py shadowed the standard library")\n')
    (root / 'json.py').write_text('raise RuntimeError("the project directory shadowed the standard library")\n')
    recipe = src / 'VFX_Heal.py'
    text = recipe.read_text().replace('from vfxkit.primitives import *\n', 'from vfxkit.primitives import *\nfrom _palette import PALE\nimport random\n', 1)
    recipe.write_text(text.replace('pale=(225,255,235,255)', 'pale=PALE', 1))
    # The wrapper keeps the current directory off sys.path (PYTHONSAFEPATH); helpers resolve only as vfx/src/_name.py.
    assert 'export PYTHONSAFEPATH=1' in (SCRIPTS / 'vfx').read_text()
    code, result = vfx('lint', '--ids', 'VFX_Heal', cwd=root, env=cli_env(VFX_PROJECT=str(root), PYTHONSAFEPATH='1'))
    assert code == 0 and result['ok'], result


def test_core_passthrough_needs_no_workspace(tmp_path):
    run = subprocess.run([sys.executable, '-m', 'vfxkit', 'core', '--help'], capture_output=True, text=True, cwd=tmp_path,
                         env=cli_env(VFX_PROJECT=str(tmp_path)), timeout=120)
    assert run.returncode == 0 and 'property-get' in run.stdout and 'property-set' in run.stdout
    assert not (tmp_path / 'vfx').exists()


def test_slash_set_bulge_matches_the_shipped_crescent(project):
    from vfxkit.primitives import SLASH02_BULGE
    from vfxkit.textures import inspect
    # slash_set rotates the painted crescent by the bulge angle it assumes; a repainted texture must match it.
    assert abs(inspect(project / 'vfx/textures/processed/T_Slash02.png')['bulge_deg'] - SLASH02_BULGE) < 10


@requires_core
def test_a_full_build_prunes_only_effects_it_built(tmp_path):
    root = game(tmp_path, 'hit', 'heal')
    code, result = vfx('--project', str(root), 'build')
    assert code == 0, result
    manifest = json.loads((root / 'vfx/vfx_manifest.json').read_text())
    assert all(e['source'] == f"vfx/src/{e['id']}.py" for e in manifest)
    # Another tool's effect: an entry without the marker, its file (which references T_Rune02, as .efkefc does, in
    # UTF-16) and a resource of its own.
    (root / 'vfx/effects/VFX_Theirs.efkefc').write_bytes(b'not ours ' + 'resources/T_Rune02.png'.encode('utf-16-le'))
    (root / 'vfx/effects/resources/T_Theirs.png').write_bytes(b'not ours')
    (root / 'vfx/vfx_manifest.json').write_text(json.dumps(manifest + [{'id': 'VFX_Theirs', 'duration': 1.0}]))
    (root / 'vfx/src/VFX_Heal.py').unlink()
    code, result = vfx('--project', str(root), 'build')
    assert code == 0, result
    ids = [e['id'] for e in json.loads((root / 'vfx/vfx_manifest.json').read_text())]
    assert ids == ['VFX_Hit_Heavy', 'VFX_Theirs']
    assert not (root / 'vfx/effects/VFX_Heal.efkefc').exists() and not (root / 'vfx/exports/VFX_Heal.efk').exists()
    assert (root / 'vfx/effects/VFX_Theirs.efkefc').read_bytes().startswith(b'not ours')
    assert (root / 'vfx/effects/resources/T_Theirs.png').read_bytes() == b'not ours'
    # The unmanaged effect may use T_Rune02, so that copy is kept even though no recipe uses it any more.
    assert (root / 'vfx/effects/resources/T_Rune02.png').is_file()
    code, result = vfx('--project', str(root), 'doctor')
    assert result['workspace']['built'] == 1 and result['workspace']['unmanaged'] == 1
    # Once nothing else may use it, the copy and its .import go; other files with that prefix stay.
    backup = root / 'vfx/effects/resources/T_Rune02.png.bak'
    backup.write_bytes(b'a backup of something else')
    (root / 'vfx/effects/VFX_Theirs.efkefc').unlink()
    (root / 'vfx/vfx_manifest.json').write_text(json.dumps([e for e in json.loads((root / 'vfx/vfx_manifest.json').read_text()) if e['id'] != 'VFX_Theirs']))
    code, result = vfx('--project', str(root), 'build')
    assert code == 0, result
    assert not (root / 'vfx/effects/resources/T_Rune02.png').exists()
    assert backup.read_bytes() == b'a backup of something else'
    assert (root / 'vfx/effects/resources/T_Theirs.png').read_bytes() == b'not ours'


@pytest.fixture
def owned_workspace(tmp_path, monkeypatch):
    from vfxkit import build
    monkeypatch.setattr(build, 'ROOT', tmp_path)
    monkeypatch.setattr(build, 'WORK', tmp_path / 'vfx/work')
    (tmp_path / 'vfx/effects').mkdir(parents=True)
    (tmp_path / 'vfx/work/builds').mkdir(parents=True)
    return tmp_path


def test_ownership_needs_the_marker_or_a_matching_receipt(owned_workspace):
    from vfxkit.build import owned, MARKER, digest
    root = owned_workspace
    assert owned({'id': 'VFX_A', 'built_by': MARKER, 'source': 'vfx/src/VFX_A.py'})
    assert not owned({'id': 'VFX_A', 'source': 'handmade/source.efkefc'})            # another tool's `source`
    assert not owned({'id': 'VFX_A', 'built_by': MARKER, 'source': 'vfx/src/VFX_B.py'})
    assert not owned({'id': '../../backup', 'built_by': MARKER, 'source': 'vfx/src/../../backup.py'})
    assert not owned({'id': None}) and not owned('VFX_A')
    # Pre-marker workspaces: a receipt counts only while it still describes the file on disk.
    effect = root / 'vfx/effects/VFX_Old.efkefc'
    effect.write_bytes(b'built by the skill')
    receipt = root / 'vfx/work/builds/VFX_Old.json'
    receipt.write_text(json.dumps({'outputs': {'vfx/effects/VFX_Old.efkefc': digest(effect)}}))
    assert owned({'id': 'VFX_Old'})
    effect.write_bytes(b'replaced by hand')
    assert not owned({'id': 'VFX_Old'})
    receipt.write_text('not json')
    assert not owned({'id': 'VFX_Old'})


def test_removal_refuses_paths_that_resolve_outside_the_workspace(owned_workspace, tmp_path_factory):
    from vfxkit.build import removable
    root = owned_workspace
    outside = tmp_path_factory.mktemp('outside')
    (outside / 'VFX_A.efk').write_bytes(b'keep')
    (root / 'vfx/exports').symlink_to(outside, target_is_directory=True)
    (root / 'vfx/effects/VFX_A.efkefc').write_bytes(b'ours')
    with pytest.raises(ValueError, match='outside'):
        removable('VFX_A')
    assert (outside / 'VFX_A.efk').read_bytes() == b'keep'


def test_same_named_resources_with_different_content_are_rejected(tmp_path):
    from vfxkit.build import resource_inputs
    a = tmp_path / 'a/T_Shared.png'; b = tmp_path / 'b/T_Shared.png'; c = tmp_path / 'c/T_Shared.png'
    for path, data in ((a, b'one'), (b, b'two'), (c, b'one')):
        path.parent.mkdir(parents=True); path.write_bytes(data)
    def recipe(*paths):
        return {'id': 'VFX_X', 'layers': [{'name': f'L{i}', 'texture': str(p)} for i, p in enumerate(paths)]}
    assert set(resource_inputs([recipe(a, c)])) == {'T_Shared.png'}      # identical copies are fine
    with pytest.raises(ValueError, match='Resource name conflict'):
        resource_inputs([recipe(a), {'id': 'VFX_Y', 'layers': [{'name': 'M', 'model': str(b)}]}])


def test_init_fills_missing_math_textures_without_replacing_edited_ones(tmp_path):
    root = game(tmp_path)
    processed = root / 'vfx/textures/processed'
    edited = processed / 'T_Glow01.png'
    edited.write_bytes(b'edited by the project')
    (processed / 'T_Dot01.png').unlink()
    code, result = vfx('--project', str(root), 'init', '--no-plugin')
    assert code == 0, result
    assert edited.read_bytes() == b'edited by the project' and (processed / 'T_Dot01.png').is_file()


def test_helpers_never_shadow_built_in_modules(tmp_path):
    root = game(tmp_path, 'heal')
    # `_lsprof` is a built-in extension that nothing has imported yet in a fresh CLI process.
    (root / 'vfx/src/_lsprof.py').write_text('raise RuntimeError("a project helper shadowed a built-in module")\n')
    recipe = root / 'vfx/src/VFX_Heal.py'
    recipe.write_text(recipe.read_text().replace('from vfxkit.primitives import *\n', 'from vfxkit.primitives import *\nimport _lsprof\n', 1))
    code, result = vfx('--project', str(root), 'lint', '--ids', 'VFX_Heal')
    assert code == 0 and result['ok'], result


def test_each_skill_folder_carries_its_license_texts():
    from conftest import PACKAGE
    root_license = (PACKAGE / 'LICENSE').read_bytes()
    assert (SKILL / 'LICENSE').read_bytes() == root_license
    assert (PACKAGE / 'skills/vfx-review/LICENSE').read_bytes() == root_license
    assert (SKILL / 'THIRD_PARTY_NOTICES.md').read_bytes() == (PACKAGE / 'THIRD_PARTY_NOTICES.md').read_bytes()


def test_setup_pins_every_archive_it_downloads():
    setup = (SCRIPTS / 'setup.sh').read_text()
    assert 'dotnet-install' not in setup  # an unpinned installer script would run unchecked code
    for name in ('CORE', 'DOTNET'):
        assert f'{name}_URL=' in setup and f'fetch "${name}_URL" "${name}_SHA256"' in setup


@requires_core
def test_a_build_never_replaces_a_resource_another_built_effect_uses(tmp_path):
    root = game(tmp_path, 'hit')
    code, result = vfx('--project', str(root), 'build')
    assert code == 0, result
    # A second effect brings a different file with the same base name as the hit's burst texture.
    other = root / 'vfx/textures/alt/T_Impact01.png'
    other.parent.mkdir(parents=True)
    other.write_bytes((root / 'vfx/textures/processed/T_Glow01.png').read_bytes())
    source = (root / 'vfx/src/VFX_Hit_Heavy.py').read_text().replace("'Hit_Heavy','Heavy Hit'", "'Hit_Alt','Alt Hit'")
    (root / 'vfx/src/VFX_Hit_Alt.py').write_text(source.replace("'T_Impact01'", repr(str(other.with_suffix('')))))
    before = (root / 'vfx/effects/resources/T_Impact01.png').read_bytes()
    code, result = vfx('--project', str(root), 'build', '--ids', 'VFX_Hit_Alt')
    assert code == 1 and 'Resource name conflict' in result['error']['message']
    assert (root / 'vfx/effects/resources/T_Impact01.png').read_bytes() == before


def test_output_folders_that_resolve_outside_the_workspace_are_refused(owned_workspace, tmp_path_factory):
    from vfxkit.build import check_output_dirs
    root = owned_workspace
    check_output_dirs()
    outside = tmp_path_factory.mktemp('outside')
    (root / 'vfx/effects/resources').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='outside'):
        check_output_dirs()


def conflict_setup(root, owner_entry=None, handmade=None):
    from vfxkit.ownership import MARKER
    resources = root / 'vfx/effects/resources'
    resources.mkdir(parents=True, exist_ok=True)
    (resources / 'T_Shared.png').write_bytes(b'current')
    new = root / 'new/T_Shared.png'
    new.parent.mkdir(parents=True, exist_ok=True)
    new.write_bytes(b'different')
    previous = []
    if owner_entry:
        (root / 'vfx/recipes').mkdir(parents=True, exist_ok=True)
        (root / 'vfx/recipes/VFX_B.json').write_text(json.dumps({'layers': [{'name': 'L', 'texture': 'vfx/effects/resources/T_Shared.png'}]}))
        previous.append({'id': 'VFX_B', 'built_by': MARKER, 'source': 'vfx/src/VFX_B.py'})
    if handmade is not None:
        (root / 'vfx/effects/VFX_Hand.efkefc').write_bytes(handmade)
    return {'T_Shared.png': new}, previous


def test_conflicts_protect_owned_effects_unless_they_are_rebuilt_or_removed(owned_workspace):
    from vfxkit.build import check_resource_conflicts
    inputs, previous = conflict_setup(owned_workspace, owner_entry=True)
    with pytest.raises(ValueError, match='VFX_B uses'):
        check_resource_conflicts(inputs, previous, {'VFX_A'}, set())
    check_resource_conflicts(inputs, previous, {'VFX_A', 'VFX_B'}, set())    # rebuilt together
    check_resource_conflicts(inputs, previous, {'VFX_A'}, {'VFX_B'})          # a full build is removing it


def test_conflicts_protect_hand_made_effects_without_a_recipe(owned_workspace):
    from vfxkit.build import check_resource_conflicts
    inputs, previous = conflict_setup(owned_workspace, handmade=b'x' + 'resources/T_Shared.png'.encode('utf-16-le'))
    with pytest.raises(ValueError, match='did not build'):
        check_resource_conflicts(inputs, previous, {'VFX_A'}, set())
    (owned_workspace / 'vfx/effects/VFX_Hand.efkefc').write_bytes(b'uses other textures only')
    check_resource_conflicts(inputs, previous, {'VFX_A'}, set())
    with pytest.raises(ValueError, match='unowned manifest entry'):  # an entry whose file is missing: unknown users
        check_resource_conflicts(inputs, [{'id': 'VFX_Gone', 'duration': 1}], {'VFX_A'}, set())


def test_doctor_uses_the_same_ownership_rules(tmp_path):
    root = game(tmp_path)
    (root / 'vfx/effects/VFX_Theirs.efkefc').write_bytes(b'not ours')
    (root / 'vfx/vfx_manifest.json').write_text(json.dumps([{'id': 'VFX_Theirs', 'source': 'handmade/theirs.efkefc'}]))
    (root / 'vfx/effects/VFX_Stray.efkefc').write_bytes(b'in no manifest')
    code, result = vfx('--project', str(root), 'doctor')
    assert result['workspace']['built'] == 0 and result['workspace']['unmanaged'] == 2


def test_setup_locks_with_the_kernel_not_a_lock_directory():
    setup = (SCRIPTS / 'setup.sh').read_text()
    assert 'exec flock' in setup and 'fcntl.flock' in setup
    assert 'mkdir "$LOCK"' not in setup and 'rm -rf "$LOCK"' not in setup


def test_missing_output_folders_under_an_outside_link_are_refused(owned_workspace, tmp_path_factory):
    from vfxkit.build import check_output_dirs
    root = owned_workspace
    outside = tmp_path_factory.mktemp('outside')
    (root / 'vfx/godot').symlink_to(outside, target_is_directory=True)  # vfx/godot/effects does not exist yet
    with pytest.raises(ValueError, match='outside'):
        check_output_dirs()


def test_file_links_that_lead_outside_are_never_written(owned_workspace, tmp_path_factory):
    from vfxkit.build import check_targets
    root = owned_workspace
    outside = tmp_path_factory.mktemp('outside') / 'precious.json'
    outside.write_text('keep')
    (root / 'vfx/recipes').mkdir()
    link = root / 'vfx/recipes/VFX_A.json'
    link.symlink_to(outside)
    with pytest.raises(ValueError, match='outside'):
        check_targets([link])
    check_targets([root / 'vfx/recipes/VFX_B.json'])  # not there yet: fine
    assert outside.read_text() == 'keep'


def test_resource_names_ignore_case(tmp_path):
    from vfxkit.build import resource_inputs
    from vfxkit.ownership import may_use
    effect = tmp_path / 'VFX_Hand.efkefc'
    effect.write_bytes(b'x' + 'resources/t_rune02.png'.encode('utf-16-le'))
    assert may_use(effect, 'T_Rune02.png') and not may_use(effect, 'T_Rune03.png')
    a = tmp_path / 'a/T_Glow.png'; b = tmp_path / 'b/t_glow.png'
    for path, data in ((a, b'one'), (b, b'two')):
        path.parent.mkdir(parents=True); path.write_bytes(data)
    with pytest.raises(ValueError, match='ignore case'):
        resource_inputs([{'id': 'VFX_X', 'layers': [{'name': 'A', 'texture': str(a)}, {'name': 'B', 'texture': str(b)}]}])


@requires_core
def test_a_build_mirrors_only_its_own_resources(tmp_path):
    root = game(tmp_path, 'hit', 'heal')
    code, result = vfx('--project', str(root), 'build')
    assert code == 0, result
    # Another effect's resource whose copies differ between folders (hand-made, say): an unrelated build leaves it.
    (root / 'vfx/effects/resources/T_Hand.png').write_bytes(b'effects copy')
    (root / 'vfx/exports/resources/T_Hand.png').write_bytes(b'exports copy')
    code, result = vfx('--project', str(root), 'build', '--ids', 'VFX_Heal')
    assert code == 0, result
    assert (root / 'vfx/exports/resources/T_Hand.png').read_bytes() == b'exports copy'
    assert not (root / 'vfx/godot/effects/resources/T_Hand.png').exists()
    rune = root / 'vfx/textures/processed/T_Rune02.png'
    for folder in ('effects/resources', 'exports/resources', 'godot/effects/resources'):
        assert (root / 'vfx' / folder / 'T_Rune02.png').read_bytes() == rune.read_bytes()


def test_references_match_non_ascii_names_in_any_case(tmp_path):
    from vfxkit.ownership import may_use
    effect = tmp_path / 'VFX_Hand.efkefc'
    for name in ('T_冰.png', 'T_Ä.png'):
        for prefix in (b'', b'\x00'):  # either UTF-16 alignment
            effect.write_bytes(prefix + ('resources/' + name).encode('utf-16-le'))
            assert may_use(effect, name) and may_use(effect, name.lower()) and may_use(effect, name.upper())
            assert not may_use(effect, 'T_Other.png')


def test_case_aliases_with_the_same_content_keep_every_spelling(tmp_path):
    from vfxkit.build import resource_inputs
    a = tmp_path / 'a/T_Glow.png'; b = tmp_path / 'b/t_glow.png'
    for path in (a, b):
        path.parent.mkdir(parents=True); path.write_bytes(b'same')
    found = resource_inputs([{'id': 'VFX_X', 'layers': [{'name': 'A', 'texture': str(a)}, {'name': 'B', 'texture': str(b)}]}])
    assert set(found) == {'T_Glow.png', 't_glow.png'}


@pytest.mark.parametrize('linked', ['godot/vfx_manifest.json', 'texture_prompts.json'])
def test_init_never_writes_through_a_link_that_leads_outside(tmp_path, tmp_path_factory, linked):
    root = game(tmp_path)
    outside = tmp_path_factory.mktemp('outside') / 'target.json'
    outside.write_text('[]\n' if linked.endswith('manifest.json') else '{"prompts": []}\n')
    before = outside.read_text()
    # A non-empty library makes init sync the Lab manifest; a missing starter prompt makes it rewrite the prompts.
    (root / 'vfx/vfx_manifest.json').write_text(json.dumps([{'id': 'VFX_Kept', 'duration': 1.0}]))
    (root / 'vfx' / linked).unlink()
    (root / 'vfx' / linked).symlink_to(outside)
    code, result = vfx('--project', str(root), 'init', '--no-plugin')
    assert code == 1 and 'outside' in result['error']['message']
    assert outside.read_text() == before


def test_resource_names_compare_in_unicode_normal_form(tmp_path):
    import unicodedata
    from vfxkit.ownership import may_use, same_name
    composed, decomposed = unicodedata.normalize('NFC', 'T_Ä.png'), unicodedata.normalize('NFD', 'T_Ä.png')
    assert composed != decomposed and same_name(composed, decomposed) and same_name(composed, decomposed.lower())
    effect = tmp_path / 'VFX_Hand.efkefc'
    effect.write_bytes(('resources/' + decomposed).encode('utf-16-le'))
    assert may_use(effect, composed)


def test_json_stores_never_write_through_a_pre_placed_temporary_link(tmp_path, tmp_path_factory, monkeypatch):
    import os
    from vfxkit import workflow
    monkeypatch.setattr(workflow, 'ROOT', tmp_path)
    (tmp_path / 'vfx/work').mkdir(parents=True)
    outside = tmp_path_factory.mktemp('outside') / 'precious'
    outside.write_text('keep')
    target = tmp_path / 'vfx/work/receipt.json'
    (tmp_path / f'vfx/work/receipt.json.{os.getpid()}.tmp').symlink_to(outside)  # the old predictable name
    workflow.save_json(target, {'ok': True})
    assert json.loads(target.read_text()) == {'ok': True} and outside.read_text() == 'keep'
    assert not [p for p in (tmp_path / 'vfx/work').iterdir() if p.name.endswith('.tmp') and not p.is_symlink()]


def test_setup_without_a_new_enough_python_stops_clearly_and_drops_a_stale_env(tmp_path):
    import os
    import shutil as sh
    for fixed in ('/opt/homebrew/bin/python3', '/usr/local/bin/python3'):
        if os.path.exists(fixed) and subprocess.run([fixed, '-c', 'import sys; sys.exit(sys.version_info < (3, 11))']).returncode == 0:
            pytest.skip(f'{fixed} is a usable Python, so setup would succeed here')
    # A PATH with the basic tools setup.sh needs but no uv, flock or python at all.
    tools = tmp_path / 'bin'
    tools.mkdir()
    for name in ('dirname', 'mkdir', 'mktemp', 'rm', 'uname', 'cat'):
        found = sh.which(name)
        if found:
            (tools / name).symlink_to(found)
    home = tmp_path / 'toolchain'
    stale = home / 'venv/bin'
    stale.mkdir(parents=True)
    (stale / 'python').write_text('#!/bin/sh\nexit 1\n')  # an old or broken environment from an earlier attempt
    (stale / 'python').chmod(0o755)
    run = subprocess.run(['/bin/sh', str(SCRIPTS / 'setup.sh'), '--authoring-only'], capture_output=True, text=True,
                         env={'PATH': str(tools), 'HOME': str(tmp_path), 'EFFEKSEER_VFX_HOME': str(home)}, timeout=120)
    assert run.returncode == 4, run.stderr
    assert 'Python 3.11 or newer is required' in run.stderr and 'Replacing' in run.stderr
    assert not (home / 'venv').exists()


def test_a_capture_that_never_draws_stops_early_with_the_reason(tmp_path):
    import time
    from vfxkit.review import run_windowed
    started = time.monotonic()
    # Stands in for a Godot that cannot open a window: it prints, then hangs without ever writing a frame.
    command = [sys.executable, '-c', 'import time; print("Connection invalid", flush=True); time.sleep(60)']
    with pytest.raises(RuntimeError, match='rendered no frame') as failure:
        run_windowed(command, timeout=60, progress=lambda: False, startup=2)
    assert time.monotonic() - started < 20 and 'Connection invalid' in str(failure.value)
    assert 'outside the sandbox' in str(failure.value)
    # A capture that writes frames runs to completion.
    done = run_windowed([sys.executable, '-c', 'print("ok")'], timeout=60, progress=lambda: True, startup=0)
    assert done.returncode == 0 and 'ok' in done.stdout
