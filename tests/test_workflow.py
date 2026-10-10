"""Workflow contracts: no stale evidence, dropped key moments or unlabelled reference clocks."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw

from conftest import ASSETS, SCRIPTS


def test_briefs_expand_child_births_and_validate_the_shipped_examples():
    from vfxkit import briefs
    from vfxkit.library import library
    rows = briefs.timeline([{'name': 'parent', 'delay': 3, 'count': 2, 'interval': 4, 'life': 10,
                             'children': [{'name': 'child', 'delay': 2, 'life': [4, 8]}]}])
    assert rows[1]['start_frame'] == 5 and rows[1]['last_birth_frame'] == 9 and rows[1]['end_frame'] == 17
    checked = 0
    for recipe in library():
        brief = briefs.read(recipe['id'])
        assert brief is not None, f'{recipe["id"]} ships without a brief'
        assert briefs.validate(brief, recipe)['ok']
        assert not briefs.validate(brief | {'anchor': 'wrong'}, recipe)['ok']
        bad = copy.deepcopy(brief)
        bad['beats'][0]['frame'] = .3
        assert not briefs.validate(bad, recipe)['ok']
        checked += 1
    assert checked == 13
    duplicate = briefs.timeline([{'name': 'same'}, {'name': 'same'}])
    assert duplicate[0]['path'] != duplicate[1]['path']
    assert not briefs.validate(None, library()[0])['ok']


def test_flipbook_integer_fields_are_rejected_before_native_compilation():
    from effekseer_ai.authoring import validate_layer
    assert any('positive integer' in e for e in validate_layer({'name': 'sheet', 'flipbook': {'x': 4, 'y': 4, 'frame_length': 4.5}}))
    assert not validate_layer({'name': 'sheet', 'flipbook': {'x': 4, 'y': 4, 'frame_length': 4}})


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point the workspace-relative modules at an empty project (ROOT) and its work/ store (WORK)."""
    from vfxkit import workflow
    monkeypatch.setattr(workflow, 'ROOT', tmp_path)
    monkeypatch.setattr(workflow, 'WORK', tmp_path / 'vfx/work')
    return tmp_path


@pytest.fixture
def lab(isolated, monkeypatch):
    from vfxkit import workflow, evidence
    root = isolated
    texture = root / 'vfx/textures/processed/T.png'
    texture.parent.mkdir(parents=True)
    Image.new('RGBA', (32, 32), 'white').save(texture)
    recipe = {'id': 'VFX_Test', 'duration': .5, 'peak': .1, 'category': 'hit', 'element': 'fire',
              'attach': 'body', 'delivery': {'kind': 'self'}, 'layers': [{'name': 'body', 'texture': str(texture), 'life': 20}]}
    for path in evidence.outputs(recipe['id']):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('compiled')
    for folder in ('effects', 'exports', 'godot/effects'):
        target = root / f'vfx/{folder}/resources/T.png'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(texture.read_bytes())
    material = root / 'vfx/materials/M_Additive.vfxmat.json'
    material.parent.mkdir(parents=True)
    material.write_text('{}')
    # The Lab template ships read-only inside the skill; a private copy stands in for it so a test can "update" it.
    template = root / 'skill-lab'
    shutil.copytree(ASSETS / 'godot-lab', template)
    monkeypatch.setattr(evidence, 'LAB', template)
    shutil.copytree(ASSETS / 'godot-lab', root / 'vfx/godot', dirs_exist_ok=True)
    (root / 'vfx/godot/vfx_manifest.json').write_text(json.dumps([recipe]))
    monkeypatch.setattr(evidence, 'current_recipe', lambda rid: copy.deepcopy(recipe))
    return root, recipe


def captured(lab):
    from vfxkit import evidence
    root, recipe = lab
    evidence.write_build(recipe, {'source': 'source.efkefc', 'writes': 12})
    paths = []
    for f in (0, 3, 6, 15, 30, 36):
        p = root / f'vfx/previews/strips/runs/one/frames/VFX_Test_f{f:03d}.png'
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.new('RGB', (64, 32), 'red' if f else 'black').save(p)
        paths.append(p)
    return evidence.write_capture(recipe['id'], [paths[1]], paths,
                                  {'view': 'standard', 'profile': 'default'}, {'status': 'complete'},
                                  evidence.stage_snapshot(), recipe)


def report():
    return {'id': 'VFX_Test', 'scores': {k: 2 for k in ('read', 'timing', 'layering', 'shape_change', 'motion', 'placement', 'tail', 'identity')},
            'worst': 'read', 'fix': 'Keep the main silhouette legible.', 'verdict': 'ship'}


def test_evidence_is_stored_in_the_workspace_work_folder(lab):
    from vfxkit import evidence
    root, _ = lab
    capture = captured(lab)
    assert evidence.store() == root / 'vfx/work'
    assert (root / f'vfx/work/captures/{capture["evidence_id"]}.json').is_file()
    assert (root / 'vfx/work/builds/VFX_Test.json').is_file()
    # Skill sources are bound with a skill: prefix, never as machine-specific absolute paths.
    build = evidence.read_build('VFX_Test')
    assert any(k.startswith('skill:scripts/vfxkit/') for k in build['inputs']['files'])
    assert not any(k.startswith('/') for k in [*build['inputs']['files'], *capture['images'], *capture['frames']])


def test_build_and_render_reject_changed_sources_assets_outputs_and_templates(lab):
    from vfxkit import evidence
    root, recipe = lab
    capture = captured(lab)
    assert not evidence.capture_issues(capture)
    recipe['layers'][0]['life'] = 21
    assert 'build_inputs_changed' in evidence.capture_issues(capture)
    recipe['layers'][0]['life'] = 20
    source = root / 'vfx/textures/processed/T.png'
    source.write_bytes(source.read_bytes() + b'changed')
    assert 'build_inputs_changed' in evidence.capture_issues(capture)
    source.write_bytes((root / 'vfx/effects/resources/T.png').read_bytes())
    evidence.outputs(recipe['id'])[1].write_text('tampered')
    assert 'build_outputs_changed' in evidence.capture_issues(capture)
    evidence.outputs(recipe['id'])[1].write_text('compiled')
    assert not evidence.capture_issues(capture)
    (root / 'skill-lab/project.godot').write_text('updated template')
    issues = evidence.capture_issues(capture)
    assert 'capture_stage_changed' in issues and any(i.startswith('templates_not_synced') for i in issues)


def test_independent_report_binds_images_scores_and_observed_frames(lab):
    from vfxkit import evidence
    capture = captured(lab)
    assert evidence.submit(capture['evidence_id'], 'reviewer-123', report(), [3, 15])['verdict'] == 'ship'
    with pytest.raises(ValueError, match='actually captured'):
        evidence.submit(capture['evidence_id'], 'reviewer-123', report(), [5])
    with pytest.raises(ValueError, match='reviewer'):
        evidence.submit(capture['evidence_id'], 'author', report(), [3])
    wrong = report()
    wrong['scores']['tail'] = 1
    with pytest.raises(ValueError):
        evidence.submit(capture['evidence_id'], 'reviewer-123', wrong, [3])
    p = lab[0] / next(iter(capture['images']))
    p.write_text('replaced image')
    with pytest.raises(ValueError, match='stale'):
        evidence.submit(capture['evidence_id'], 'reviewer-123', report(), [3])


def test_completion_requires_brief_review_and_overview_instead_of_no_flags(lab):
    from vfxkit import evidence, workflow
    root, recipe = lab
    capture = captured(lab)
    result = evidence.verify(recipe['id'], False)
    assert not result['verified'] and 'missing_independent_review' in result['issues'] and 'invalid_or_missing_brief' in result['issues']
    brief = {'schema_version': 1, 'effect_id': recipe['id'], 'role': 'hit', 'style': 'toon', 'dominant_shape': 'burst',
             'palette': {k: [200, 100, 50] for k in ('core', 'body', 'dark', 'matter')}, 'delivery': recipe['delivery'],
             'anchor': 'body', 'beats': [{'frame': 6, 'name': 'contact', 'expect': 'short flash'}],
             'layer_plan': [{'name': '0:body', 'role': 'body', 'primitive': 'sprite', 'exit': 'erode'}],
             'acceptance': ['readable'], 'avoid': ['flat']}
    workflow.save_json(root / 'vfx/briefs/VFX_Test.json', brief)
    assert 'capture_brief_changed' in evidence.capture_issues(capture)
    capture = captured(lab)
    evidence.submit(capture['evidence_id'], 'reviewer-123', report(), [3, 15])
    partial = evidence.verify(recipe['id'], False)
    assert partial['passed_without_overview'] and not partial['verified'] and partial['issues'] == ['overview_not_checked']
    assert 'missing_or_stale_overview' in evidence.verify(recipe['id'])['issues']
    overview = root / 'vfx/previews/strips/overview_1.png'
    overview.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (64, 32), 'red').save(overview)
    workflow.save_json(evidence.store() / 'overview.json', {'images': workflow.snapshot([overview]), 'evidence': {recipe['id']: capture['evidence_id']}})
    assert evidence.verify(recipe['id'])['verified']
    evidence.write_build(recipe, {'source': 'source', 'writes': 12})
    assert 'capture_build_changed' in evidence.verify(recipe['id'])['issues']


def test_frame_plan_keeps_contact_and_flags_static_or_missing_capture(tmp_path):
    from vfxkit.review import sample_plan, frame_state
    entry = {'id': 'VFX_Test', 'duration': 1.2, 'peak': .1}
    expected = sample_plan(entry, 4)
    assert set(range(4, 10)) <= set(expected) and 78 in expected
    for f in [0, *expected]:
        Image.new('RGB', (32, 32), 'black').save(tmp_path / f'VFX_Test_f{f:03d}.png')
    assert frame_state(tmp_path, 'VFX_Test', expected)['status'] == 'inconclusive'
    Image.new('RGB', (32, 32), 'white').save(tmp_path / 'VFX_Test_f006.png')
    assert frame_state(tmp_path, 'VFX_Test', expected)['status'] == 'complete'
    (tmp_path / 'VFX_Test_f005.png').unlink()
    assert frame_state(tmp_path, 'VFX_Test', expected)['missing'] == [5]
    with pytest.raises(ValueError):
        sample_plan(entry, 0)


def test_texture_checks_distinguish_intentional_blank_from_bad_grid(isolated):
    from vfxkit.texture_audit import audit
    p = isolated / 'vfx/textures/processed/T_Sheet.png'
    p.parent.mkdir(parents=True)
    im = Image.new('RGBA', (64, 64), (255, 255, 255, 0))
    ImageDraw.Draw(im).rectangle((8, 8, 20, 20), fill='white')
    im.save(p)
    result = audit('T_Sheet', 'flipbook', [2, 2], allow_empty=[1, 2, 3])
    assert result['ok'] and result['measurements']['empty_cells'] == [1, 2, 3]
    assert not any('Empty cells' in s for s in result['warnings'])
    assert (isolated / result['preview']).is_file() and result['preview'].startswith('vfx/work/')
    assert not audit('T_Sheet', 'flipbook', [3, 3])['ok']
    assert not audit('T_Sheet', 'uv_distortion')['ok']
    with pytest.raises(ValueError):
        audit('../T_Sheet')


def test_reference_clock_and_real_ffmpeg_import(isolated):
    from vfxkit import reference
    assert reference.effect_time(3.0, 1.0, 2.0) == 1.0
    with pytest.raises(ValueError):
        reference.effect_time(1., 0., 0.)
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('ffmpeg reference decoder unavailable')
    source = isolated / 'source.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=128x96:rate=12:duration=1', str(source)], check=True)
    record = reference.import_clip(source, end=1., slow=2., fps=12)
    assert record['duration_effect'] == .5 and len(record['frames']) == 12
    assert record['times'][1] == pytest.approx(1 / 24)
    span = reference.frames(record['reference_id'], 0, .2, 4)
    assert (isolated / span['image']).is_file() and len(span['times']) == 4


def test_reference_compare_requires_exact_fresh_render_frames(lab):
    from vfxkit import evidence, reference, workflow
    capture = captured(lab)
    ident = 'a' * 24
    source = evidence.store() / 'references' / ident / 'reference.png'
    source.parent.mkdir(parents=True)
    Image.new('RGB', (96, 64), 'orange').save(source)
    workflow.save_json(source.parent / 'manifest.json', {'reference_id': ident, 'duration_effect': .6,
                                                         'times': [0., .1, .5], 'frames': [workflow.relative(source)] * 3})
    result = reference.compare(ident, capture['evidence_id'], [.1, .5])
    assert (lab[0] / result['image']).is_file()
    assert result['pairs'][0]['rendered_frame'] == 6
    with pytest.raises(ValueError, match='was not captured'):
        reference.compare(ident, capture['evidence_id'], [.2])
    (lab[0] / 'vfx/godot/project.godot').write_text('changed')
    with pytest.raises(ValueError, match='stale'):
        reference.compare(ident, capture['evidence_id'], [.1])


def test_project_lock_serializes_two_independent_processes(tmp_path):
    common = ('import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);'
              'import vfxkit.workflow as workflow;workflow.WORK=Path(sys.argv[2]);')
    owner_code = common + '\nwith workflow.project_lock():\n print("held",flush=True)\n sys.stdin.readline()\n'
    contender_code = common + '\nwith workflow.project_lock():\n print("acquired",flush=True)\n'
    args = [str(SCRIPTS), str(tmp_path)]
    env = {'VFX_PROJECT': str(tmp_path), 'EFFEKSEER_VFX_HOME': str(tmp_path / 'toolchain'), 'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin',
           **{k: os.environ[k] for k in ('SYSTEMROOT',) if k in os.environ}}  # Windows needs SYSTEMROOT to start Python
    owner = subprocess.Popen([sys.executable, '-c', owner_code, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
    contender = None
    try:
        assert owner.stdout.readline().strip() == 'held'
        contender = subprocess.Popen([sys.executable, '-c', contender_code, *args], stdout=subprocess.PIPE, text=True, env=env)
        with pytest.raises(subprocess.TimeoutExpired):
            contender.communicate(timeout=.2)
        owner.stdin.write('release\n')
        owner.stdin.flush()
        assert owner.wait(timeout=5) == 0
        output, _ = contender.communicate(timeout=5)
        assert contender.returncode == 0 and output.strip() == 'acquired'
        assert (tmp_path / 'project.lock').is_file()
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.wait()
        if contender is not None and contender.poll() is None:
            contender.kill()
            contender.wait()


def test_project_lock_is_reentrant_within_a_process(isolated):
    from vfxkit import workflow

    @workflow.locked
    def inner():
        return 'ok'

    with workflow.project_lock():
        assert inner() == 'ok'
    assert (isolated / 'vfx/work/project.lock').is_file()


def test_review_handoff_gives_a_reviewer_everything_and_submits_its_report(lab):
    from vfxkit import evidence, handoff
    root, recipe = lab
    capture = captured(lab)
    result = handoff.handoff(recipe['id'])
    brief = Path(result['prompt_file']).read_text()
    assert result['evidence_id'] == capture['evidence_id'] and result['captured_frames'] == [0, 3, 6, 15, 30, 36]
    for image in capture['images']:
        assert str(root / image) in brief
    assert result['report_file'] in brief and 'review_rubric.json' in brief and 'vfx/src' in brief
    assert result['reviewer_skill'] and Path(result['reviewer_skill']).name == 'SKILL.md' and result['reviewer_skill'] in brief
    assert json.loads((root / 'vfx/work/handoff/review_rubric.json').read_text())['criteria']
    assert 'vfx review-submit ' + capture['evidence_id'] in result['next']
    # The reviewer writes the report where the brief says; the default frames come from it.
    Path(result['report_file']).write_text(json.dumps(report() | {'observed_frames': [3, 15]}))
    stored = json.loads(Path(result['report_file']).read_text())
    assert evidence.submit(capture['evidence_id'], 'reviewer-7', stored, stored['observed_frames'])['verdict'] == 'ship'


def test_review_handoff_refuses_a_missing_or_stale_capture(lab):
    from vfxkit import evidence, handoff
    root, recipe = lab
    with pytest.raises(ValueError, match='No standard capture'):
        handoff.handoff(recipe['id'])
    captured(lab)
    evidence.write_build(recipe, {'source': 'source', 'writes': 12})  # rebuilt after the capture
    with pytest.raises(ValueError, match='stale'):
        handoff.handoff(recipe['id'])
