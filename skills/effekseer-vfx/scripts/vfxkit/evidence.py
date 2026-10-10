"""Bind builds, real captures and independent reports to the state they describe.

These records attest to checks actually performed by the pipeline, not artistic quality
or reviewer independence. The host must arrange an independent reviewer.
"""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import uuid
from . import workflow
from .paths import ASSETS, SCRIPTS, CORE_BIN, WINDOWS

RUBRIC = ASSETS / 'review_rubric.json'
LAB = ASSETS / 'godot-lab'


def now():
    return datetime.now(timezone.utc).isoformat()


def store():
    return workflow.WORK


def current_recipe(rid):
    workflow.effect_id(rid)
    from . import library
    return library.get(rid)


def prepared(recipe):
    from .primitives import walk, TEXTURE_KEYS, is_path
    result = copy.deepcopy(recipe)
    for layer in walk(result['layers']):
        for key in TEXTURE_KEYS:
            if layer.get(key) and not is_path(layer[key]):
                layer[key] = str(workflow.ROOT / f'vfx/textures/processed/{layer[key]}.png')
        profile = {'Add': 'M_Additive', 'Blend': 'M_Alpha', 'Sub': 'M_Subtractive'}.get(layer.get('blend', 'Add'))
        if profile:
            layer['material_profile'] = str(workflow.ROOT / f'vfx/materials/{profile}.vfxmat.json')
    return result


def portable(value):
    if isinstance(value, dict):
        return {k: portable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [portable(v) for v in value]
    if isinstance(value, str) and value.startswith(str(workflow.ROOT) + '/'):
        return value[len(str(workflow.ROOT)) + 1:]
    return value


def inputs(recipe):
    from .primitives import walk
    result = prepared(recipe)
    paths = []
    for layer in walk(result['layers']):
        for key in ('texture', 'alpha_texture', 'distortion_texture', 'blend_texture', 'model', 'material_profile'):
            if layer.get(key):
                p = Path(layer[key])
                paths.append(p if p.is_absolute() else workflow.ROOT / p)
    paths += list((SCRIPTS / 'effekseer_ai').glob('*.py'))
    paths += [SCRIPTS / 'vfxkit' / n for n in ('primitives.py', 'build.py', 'lint.py')] + [SCRIPTS / 'vfx']
    paths += list(CORE_BIN.glob('Effekseer*.dll'))
    return {'recipe_sha256': workflow.digest(portable(result)), 'files': workflow.snapshot(paths)}


def outputs(rid):
    root = workflow.ROOT
    return [root / f'vfx/recipes/{rid}.json', root / f'vfx/effects/{rid}.efkefc', root / f'vfx/exports/{rid}.efk',
            root / f'vfx/godot/effects/{rid}.efkefc']


def write_build(recipe, compile_report):
    rid = workflow.effect_id(recipe['id'])
    if not compile_report.get('source') or compile_report.get('writes', 0) <= 0:
        raise ValueError('A successful Core save/open report is required')
    state = inputs(recipe)
    copies = []
    # Every imported texture and model, wherever it came from, is copied into the three resources/ folders by base
    # name; bind all of those copies, so another build that replaces a same-named resource makes this one stale.
    from .primitives import walk
    from .build import RESOURCE_KEYS
    for layer in walk(recipe['layers']):
        for key in RESOURCE_KEYS:
            if not layer.get(key):
                continue
            source = Path(layer[key]) if Path(layer[key]).is_absolute() else workflow.ROOT / layer[key]
            name = source.name
            for folder in ('effects', 'exports', 'godot/effects'):
                copied = workflow.ROOT / f'vfx/{folder}/resources/{name}'
                if workflow.file_hash(copied) != workflow.file_hash(source):
                    raise ValueError(f'Built resource copy differs from input: {folder}/resources/{name}')
                copies.append(copied)
    record = {'schema_version': 1, 'effect_id': rid, 'build_id': uuid.uuid4().hex,
              'time': now(), 'inputs': state, 'outputs': workflow.snapshot(outputs(rid) + copies),
              'readback': {'verified': True, 'writes': compile_report['writes']}}
    if not workflow.unchanged(record['outputs']):
        raise ValueError('Build outputs are missing')
    workflow.save_json(store() / f'builds/{rid}.json', record)
    return record


def read_build(rid):
    path = store() / f'builds/{workflow.effect_id(rid)}.json'
    return json.loads(path.read_text()) if path.is_file() else None


def build_issues(rid, recipe=None):
    receipt = read_build(rid)
    if not receipt:
        return ['missing_build_receipt']
    issues = []
    if receipt['inputs'] != inputs(recipe or current_recipe(rid)):
        issues.append('build_inputs_changed')
    if not workflow.unchanged(receipt['outputs']):
        issues.append('build_outputs_changed')
    if receipt.get('readback', {}).get('verified') is not True:
        issues.append('missing_core_readback')
    return issues


# What the Lab stage is made of. The Effekseer plugin's native library is libeffekseer (a macOS framework binary) or,
# on Windows, bin/windows/libeffekseer.<arch>.dll.
STAGE_SUFFIXES = ('.gd', '.gdshader', '.godot', '.tscn', '.gde', '.gdextension', '.dylib', '.glb', '.json', '.cfg') + (('.dll',) if WINDOWS else ())


def stage_snapshot():
    paths = []
    for folder in (LAB, workflow.ROOT / 'vfx/godot'):
        paths.extend(p for p in folder.rglob('*') if p.is_file()
                     and '.godot' not in p.relative_to(folder).parts
                     and (p.suffix in STAGE_SUFFIXES or p.name == 'libeffekseer')
                     and 'effects' not in p.relative_to(folder).parts
                     and p.name != 'vfx_manifest.json')
    paths += [SCRIPTS / 'vfxkit' / n for n in ('review.py', 'briefs.py', 'evidence.py')]
    return workflow.snapshot(paths)


def template_issues():
    issues = []
    for path in LAB.rglob('*'):
        if path.is_file() and path.suffix in ('.gd', '.gdshader', '.godot', '.tscn'):
            target = workflow.ROOT / 'vfx/godot' / path.relative_to(LAB)
            if workflow.file_hash(path) != workflow.file_hash(target):
                issues.append('templates_not_synced:' + path.relative_to(LAB).as_posix() + ' (run: vfx init --update-templates)')
    return issues


def read_capture(evidence_id):
    if not isinstance(evidence_id, str) or len(evidence_id) != 32 or any(c not in '0123456789abcdef' for c in evidence_id):
        raise ValueError('Invalid evidence ID')
    return json.loads((store() / f'captures/{evidence_id}.json').read_text())


def dependencies(entry):
    """A staged impact can show its incoming projectile and tail; bind that actual resource too."""
    dep = entry.get('delivery', {}).get('projectile')
    if not dep:
        return {}
    workflow.effect_id(dep)
    manifest = json.loads((workflow.ROOT/'vfx/godot/vfx_manifest.json').read_text())
    metadata = next((m for m in manifest if m['id'] == dep), None)
    from .primitives import walk, TEXTURE_KEYS
    recipe = json.loads((workflow.ROOT/f'vfx/recipes/{dep}.json').read_text())
    paths = [workflow.ROOT/f'vfx/godot/effects/{dep}.efkefc']
    paths += [workflow.ROOT/f'vfx/godot/effects/resources/{Path(l[k]).name}'
              for l in walk(recipe['layers']) for k in TEXTURE_KEYS if l.get(k)]
    return {dep: {'manifest': metadata, 'files': workflow.snapshot(paths)}}


def write_capture(rid, images, frames, configuration, capture_state, stage, manifest_entry, note=''):
    receipt = read_build(rid)
    ident = uuid.uuid4().hex
    from . import briefs
    record = {'schema_version': 1, 'evidence_id': ident, 'effect_id': rid, 'time': now(),
              'build_id': receipt['build_id'] if receipt else None, 'stage': stage,
              'brief_sha256': workflow.digest(briefs.read(rid)), 'manifest': manifest_entry,
              'configuration': configuration, 'capture': capture_state, 'note': note,
              'dependencies': dependencies(manifest_entry),
              'images': workflow.snapshot(images), 'frames': workflow.snapshot(frames)}
    workflow.save_json(store() / f'captures/{ident}.json', record)
    workflow.save_json(store() / f'latest/{rid}_{configuration["view"]}_{configuration["profile"]}.json', {'evidence_id': ident})
    return record


def capture_issues(record):
    rid = record['effect_id']
    problems = build_issues(rid)
    build = read_build(rid)
    if not build or record.get('build_id') != build['build_id']:
        problems.append('capture_build_changed')
    if record.get('stage') != stage_snapshot():
        problems.append('capture_stage_changed')
    problems += template_issues()
    from . import briefs
    if record.get('brief_sha256') != workflow.digest(briefs.read(rid)):
        problems.append('capture_brief_changed')
    manifest = json.loads((workflow.ROOT / 'vfx/godot/vfx_manifest.json').read_text())
    if record.get('manifest') != next((m for m in manifest if m['id'] == rid), None):
        problems.append('capture_manifest_changed')
    if record.get('dependencies', {}) != dependencies(record['manifest']):
        problems.append('capture_dependency_changed')
    if record.get('capture', {}).get('status') != 'complete':
        problems.append('capture_inconclusive')
    if not workflow.unchanged(record['images']) or not workflow.unchanged(record['frames']):
        problems.append('capture_files_changed')
    return problems


@workflow.locked
def submit(evidence_id, reviewer, report, observed_frames):
    record = read_capture(evidence_id)
    issues = capture_issues(record)
    if issues:
        raise ValueError('Cannot review stale or incomplete evidence: ' + ', '.join(issues))
    rubric = json.loads(RUBRIC.read_text())
    criteria = {c['id'] for c in rubric['criteria']}
    scores = report.get('scores', {})
    if set(scores) != criteria or any(type(v) is not int or not 0 <= v <= 3 for v in scores.values()):
        raise ValueError('Every rubric score must be an integer 0..3')
    if report.get('id') != record['effect_id'] or report.get('worst') not in criteria:
        raise ValueError('Report id or worst criterion is invalid')
    if scores[report['worst']] != min(scores.values()):
        raise ValueError('worst must name a lowest scoring criterion')
    verdict = 'ship' if min(scores.values()) >= 2 else 'iterate'
    if report.get('verdict') != verdict or not isinstance(report.get('fix'), str) or not report['fix'].strip():
        raise ValueError('Report needs one fix and a verdict consistent with scores')
    available = {int(Path(p).stem.rsplit('_f', 1)[1]) for p in record['frames'] if '_f' in Path(p).stem}
    if not observed_frames or any(type(f) is not int or f not in available for f in observed_frames):
        raise ValueError('observed_frames must name frames actually captured')
    if not isinstance(reviewer, str) or not reviewer.strip() or reviewer.lower() in ('author', 'self'):
        raise ValueError('A separately assigned reviewer identifier is required')
    review = {'evidence_id': evidence_id, 'reviewer': reviewer, 'time': now(), 'report': report,
              'observed_frames': observed_frames, 'rubric_sha256': workflow.file_hash(RUBRIC),
              'image_hashes': record['images'], 'independence': 'host_attested'}
    workflow.save_json(store() / f'reviews/{evidence_id}.json', review)
    return {'ok': True, 'verdict': verdict, 'evidence_id': evidence_id,
            'independence': 'host must ensure reviewer isolation; an identifier is not proof'}


def latest(rid, view='standard', profile='default'):
    path = store() / f'latest/{workflow.effect_id(rid)}_{view}_{profile}.json'
    return read_capture(json.loads(path.read_text())['evidence_id']) if path.is_file() else None


@workflow.locked
def verify(rid, require_overview=True):
    recipe = current_recipe(rid)
    from . import briefs
    brief_result = briefs.validate(briefs.read(rid), recipe)
    issues = [] if brief_result['ok'] else ['invalid_or_missing_brief']
    record = latest(rid)
    if not record:
        issues += build_issues(rid, recipe) + ['missing_standard_capture']
    else:
        issues += capture_issues(record)
        path = store() / f'reviews/{record["evidence_id"]}.json'
        review = json.loads(path.read_text()) if path.is_file() else None
        if not review:
            issues.append('missing_independent_review')
        elif review['rubric_sha256'] != workflow.file_hash(RUBRIC) or review['image_hashes'] != record['images']:
            issues.append('review_changed')
        elif review['report']['verdict'] != 'ship':
            issues.append('review_requires_iteration')
    if require_overview:
        path = store() / 'overview.json'
        overview = json.loads(path.read_text()) if path.is_file() else None
        if not overview or not record or overview.get('evidence', {}).get(rid) != record['evidence_id'] or not workflow.unchanged(overview.get('images', {})):
            issues.append('missing_or_stale_overview')
    # Skipping the overview is a partial check: it reports whether everything else passed but never `verified`,
    # which is the delivery condition.
    partial = {} if require_overview else {'partial': True, 'passed_without_overview': not issues}
    if not require_overview:
        issues.append('overview_not_checked')
    return {'ok': True, 'verified': not issues, **partial, 'effect_id': rid, 'issues': sorted(set(issues)),
            'evidence_id': record['evidence_id'] if record else None, 'brief': brief_result,
            'scope': 'visual authoring only; runtime behavior and device performance require separate tests'}


@workflow.locked
def context(rid):
    from . import briefs
    recipe = current_recipe(rid)
    record = latest(rid)
    history = workflow.ROOT / f'vfx/previews/strips/history/{rid}.jsonl'
    return {'ok': True, 'effect_id': rid, 'brief': briefs.read(rid), 'build_issues': build_issues(rid, recipe),
            'latest_evidence': record, 'rounds': [json.loads(s) for s in history.read_text().splitlines()[-10:]] if history.is_file() else []}
