"""Sequences: several effects performed one after another by a character's animation (a combo, a skill with a
finisher), designed, gated and reviewed as one piece. See references/sequence.md.

A sequence brief lives in vfx/sequences/<SEQ_ID>.json. It names the effects and the moments the animation fires
them, the one theme that ties them together, what each reference is there to be stolen for, the paintover concept
that is the visual target, and the ideas that were cut. The workflow is staged:

  blockout -> detail -> polish

A blockout uses basic shapes and solid colours only and is judged on timing, size and readability; the sequence may
only move on to detail once an independent blockout review says ship (the gate is recorded next to the brief).
Detail and polish need references with steal lists; polish needs the paintover concept.

Captures come from the Lab (the dummies perform every step at its time) or from the game itself (`--frames`: frames
the game captured with its own character, animation and camera), so the review sees the effects on the real moves.
"""
import json
import re
import shutil
import uuid
from pathlib import Path

from . import workflow
from .paths import ASSETS
from .ownership import guard

STAGES = ('blockout', 'detail', 'polish')
FIELDS = {'schema_version', 'sequence_id', 'stage', 'style', 'theme', 'animation', 'steps', 'references', 'concept', 'cut', 'acceptance', 'screen'}
RUBRIC = ASSETS / 'sequence_rubric.json'
MAX_TILES = 24


def sequence_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'SEQ_[A-Za-z0-9_]+', value):
        raise ValueError('Expected a sequence ID such as SEQ_Star_Combo')
    return value


def path(sid):
    return workflow.ROOT / f'vfx/sequences/{sequence_id(sid)}.json'


def gate_path(sid):
    return workflow.ROOT / f'vfx/sequences/{sequence_id(sid)}.gate.json'


def read(sid):
    p = path(sid)
    if not p.is_file():
        raise FileNotFoundError(f'No sequence brief {p.relative_to(workflow.ROOT).as_posix()}; write it first (references/sequence.md)')
    return json.loads(p.read_text(encoding='utf-8'))


def store():
    return workflow.WORK / 'sequences'


def rubric():
    return json.loads(RUBRIC.read_text(encoding='utf-8'))


def criteria(stage):
    return [c['id'] for c in rubric()['criteria'] if stage in c['stages']]


def recipe_hashes(seq):
    """The compiled recipe snapshot of every effect in the sequence: a capture is stale once any of them changes."""
    out = {}
    for step in seq.get('steps', []):
        rid = step.get('effect')
        if isinstance(rid, str):
            out[rid] = workflow.file_hash(workflow.ROOT / f'vfx/recipes/{rid}.json')
    return out


def validate(sid):
    """Structure, effects, stage gate, references and concept. Errors block review; warnings are craft hints."""
    seq = read(sid)
    errors, warnings = [], []
    errors += [f'Missing field: {k}' for k in ('schema_version', 'sequence_id', 'stage', 'theme', 'steps') if k not in seq]
    errors += [f'Unknown field: {k}' for k in sorted(set(seq) - FIELDS)]
    if seq.get('sequence_id') != sid:
        errors.append('sequence_id differs from the file name')
    stage = seq.get('stage')
    if stage not in STAGES:
        errors.append(f'stage must be one of {STAGES}')
    if not isinstance(seq.get('theme'), str) or len(seq.get('theme', '').split()) < 4:
        errors.append('theme needs one sentence: what every beat shares (palette, shape language, motion)')
    steps = seq.get('steps') or []
    if not steps:
        errors.append('steps must list at least one {t, effect}')
    times = []
    from . import library
    loaded, broken = {}, {}
    for i, step in enumerate(steps):
        rid = step.get('effect')
        t = step.get('t')
        if not isinstance(t, (int, float)) or t < 0:
            errors.append(f'steps[{i}].t must be seconds from the start of the sequence')
        else:
            times.append(t)
        try:
            workflow.effect_id(rid)
            loaded[rid] = loaded.get(rid) or library.get(rid)
        except Exception as error:  # a missing or broken source is the author's next fix, not a crash
            broken[rid] = str(error)
    if times != sorted(times):
        errors.append('steps must be ordered by t')
    errors += [f'{rid}: {message}' for rid, message in broken.items()]
    if stage == 'blockout':
        for rid, recipe in loaded.items():
            if recipe and recipe.get('stage') != 'blockout':
                errors.append(f"{rid}: a blockout sequence uses blockout effects; set effect(..., stage='blockout')")
    if stage in ('detail', 'polish'):
        gate = json.loads(gate_path(sid).read_text()) if gate_path(sid).is_file() else None
        if not gate or gate.get('verdict') != 'ship':
            errors.append('blockout gate: an independent blockout review of this sequence must say ship before detail work '
                          '(vfx sequence-review with stage blockout, then sequence-handoff / sequence-submit)')
        refs = seq.get('references') or []
        if not refs or any(not r.get('source') or not r.get('steal') for r in refs):
            errors.append('references: every reference needs a source and a steal list of what to take from it')
        for rid, recipe in loaded.items():
            if recipe and recipe.get('stage') == 'blockout':
                warnings.append(f'{rid} is still a blockout effect')
    if stage == 'polish':
        concept = seq.get('concept') or {}
        image = workflow.ROOT / concept.get('image', '') if concept.get('image') else None
        if not image or not image.is_file():
            errors.append('concept: polish needs the paintover concept image (vfx paintover, then an image-edit model) as its visual target')
    if not seq.get('cut'):
        warnings.append('cut is empty: record the ideas you dropped and why (an element that does not carry the theme is cut, not polished)')
    screen = seq.get('screen')
    if screen is not None and not isinstance(screen, dict):
        errors.append('screen must be an object')
    return {'ok': not errors, 'sequence_id': sid, 'stage': stage, 'errors': errors, 'warnings': warnings,
            'steps': [{'t': s.get('t'), 'effect': s.get('effect')} for s in steps],
            'length': length(seq, loaded)}


def length(seq, recipes=None):
    """Seconds until the last step's effect is over (beams count their hold), plus a short settle."""
    from . import library
    end = 0.0
    for step in seq.get('steps', []):
        recipe = (recipes or {}).get(step.get('effect'))
        if recipe is None:
            try:
                recipe = library.get(step.get('effect'))
            except Exception:
                continue
        end = max(end, float(step.get('t', 0)) + float(recipe.get('duration', 1)))
    return round(end + .2, 3)


def _frame_number(p):
    m = re.search(r'_f(\d+)$', Path(p).stem)
    return int(m.group(1)) if m else None


def strip(sid, seq, shots, target, columns=6, width=320, max_tiles=MAX_TILES, title=''):
    """Time-labelled tiles of the whole sequence; tiles where a step starts carry its effect name."""
    from PIL import Image, ImageDraw
    starts = {round(float(s['t']) * 60): s['effect'] for s in seq['steps']}
    if len(shots) > max_tiles:
        by = {_frame_number(p): p for p in shots}
        keep = set()
        frames = sorted(by)
        for f0 in starts:  # never drop the frame where a step begins, or the one 6 frames later (its contact)
            for want in (f0, f0 + 6):
                keep.add(min(frames, key=lambda f: abs(f - want)))
        room = max(2, max_tiles - len(keep))
        keep.update(frames[round(i * (len(frames) - 1) / (room - 1))] for i in range(room))
        shots = [by[f] for f in sorted(keep)]
    first = Image.open(shots[0]).convert('RGB')
    scale = width / first.width
    height = round(first.height * scale)
    rows = (len(shots) + columns - 1) // columns
    canvas = Image.new('RGB', (columns * width, rows * height + 26), (8, 10, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 6), title or f'{sid}  stage {seq.get("stage")}  frames @60fps', fill=(200, 215, 230))
    for i, shot in enumerate(shots):
        tile = Image.open(shot).convert('RGB').resize((width, height), Image.Resampling.LANCZOS)
        x, y = (i % columns) * width, 26 + (i // columns) * height
        canvas.paste(tile, (x, y))
        f = _frame_number(shot)
        label = f'f{f}  {f / 60:.2f}s'
        near = [rid for f0, rid in starts.items() if 0 <= f - f0 < 4]
        if near:
            label += '  > ' + near[0].removeprefix('VFX_')
        # Game frames can be bright: the label sits on a dark plate.
        draw.rectangle((x + 2, y + 2, x + 10 + 6 * len(label), y + 16), fill=(8, 10, 16))
        draw.text((x + 6, y + 4), label, fill=(255, 230, 120))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)
    return target


@workflow.locked
def capture(sid, frames_dir=None, fps=60, step=4, note='', godot=None, timeout=900):
    """Capture the sequence (Lab, or the game's own frames with frames_dir) and record it as sequence evidence."""
    checked = validate(sid)
    if not checked['ok']:
        raise ValueError('Sequence brief has errors: ' + '; '.join(checked['errors']))
    seq = read(sid)
    eid = uuid.uuid4().hex
    run = store() / 'runs' / eid
    frames = run / 'frames'
    frames.mkdir(parents=True)
    source = 'game' if frames_dir else 'lab'
    if frames_dir:
        shots = sorted(Path(frames_dir).glob('*.png'))
        if not shots:
            raise FileNotFoundError(f'No PNG frames in {frames_dir}')
        for i, shot in enumerate(shots):
            n = _frame_number(shot)
            f = n if n is not None else round(i * 60 / fps)
            shutil.copy2(shot, frames / f'{sid}_f{f:03d}.png')
    else:
        _lab_capture(sid, seq, checked['length'], frames, step, godot, timeout)
    shots = sorted((p for p in frames.glob(f'{sid}_f*.png') if _frame_number(p)), key=_frame_number)
    if len(shots) < 3:
        raise RuntimeError(f'Only {len(shots)} frames captured; check {run}')
    out = workflow.ROOT / 'vfx/previews/sequences'
    target = strip(sid, seq, shots, out / f'{sid}.png')
    shutil.copy2(target, run / target.name)
    keys = sheet_around_steps(sid, seq, shots, run / f'{sid}_steps.png')
    record = {'evidence_id': eid, 'sequence_id': sid, 'stage': seq['stage'], 'source': source, 'time': _now(), 'note': note,
              'sequence_sha256': workflow.file_hash(path(sid)), 'recipes': recipe_hashes(seq),
              'images': workflow.snapshot([run / target.name, keys]),
              'frames': [workflow.relative(p) for p in shots]}
    workflow.save_json(store() / f'{eid}.json', record)
    workflow.save_json(store() / f'latest_{sid}.json', {'evidence_id': eid})
    return {'ok': True, 'sequence_id': sid, 'evidence_id': eid, 'source': source, 'stage': seq['stage'], 'strip': str(target),
            'steps_sheet': str(keys), 'frames': len(shots), 'warnings': checked['warnings']}


def sheet_around_steps(sid, seq, shots, target):
    """For each step: the frames at its start, +4, +10 and +20 (contact, body, exit), one row per step."""
    from PIL import Image, ImageDraw
    by = {_frame_number(p): p for p in shots}
    frames = sorted(by)
    rows = []
    for s in seq['steps']:
        f0 = round(float(s['t']) * 60)
        rows.append((s['effect'], [min(frames, key=lambda f: abs(f - (f0 + d))) for d in (0, 4, 10, 20)]))
    first = Image.open(shots[0]).convert('RGB')
    width = 300
    height = round(first.height * width / first.width)
    canvas = Image.new('RGB', (4 * width, len(rows) * (height + 18)), (8, 10, 16))
    draw = ImageDraw.Draw(canvas)
    for r, (rid, picks) in enumerate(rows):
        y = r * (height + 18)
        draw.text((6, y + 2), rid, fill=(200, 215, 230))
        for c, f in enumerate(picks):
            canvas.paste(Image.open(by[f]).convert('RGB').resize((width, height), Image.Resampling.LANCZOS), (c * width, y + 18))
            draw.rectangle((c * width + 2, y + 20, c * width + 40, y + 34), fill=(8, 10, 16))
            draw.text((c * width + 6, y + 22), f'f{f}', fill=(255, 230, 120))
    canvas.save(target)
    return target


def _lab_capture(sid, seq, seconds, frames, step, godot, timeout):
    import subprocess
    from .paths import godot as godot_path
    from .review import run_windowed
    from . import evidence
    project = workflow.ROOT / 'vfx/godot'
    sync = evidence.template_issues()
    if sync:
        raise RuntimeError('Sync the Lab before review: ' + ', '.join(sync))
    plan = frames.parent / 'sequence.json'
    workflow.save_json(plan, {'id': sid, 'length': seconds, 'steps': [{'t': s['t'], 'id': s['effect']} for s in seq['steps']]})
    godot = godot or godot_path()
    imported = subprocess.run([godot, '--headless', '--editor', '--path', str(project), '--import'], capture_output=True, text=True, timeout=timeout)
    if imported.returncode:
        raise RuntimeError(f'Godot import failed: {imported.stderr[-2000:]}')
    command = [godot, '--path', str(project), '--fixed-fps', '60', '--', '--strip=' + str(frames), f'--step={step}', '--sequence=' + str(plan)]
    result = run_windowed(command, timeout, progress=lambda: any(frames.glob('*.png')))
    (frames.parent / 'strip.log').write_text(result.stdout + result.stderr)
    if result.returncode or 'SCRIPT ERROR:' in result.stdout + result.stderr:
        raise RuntimeError(f'Godot sequence capture failed: {(result.stdout + result.stderr)[-2000:]}')


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def latest(sid):
    p = store() / f'latest_{sequence_id(sid)}.json'
    if not p.is_file():
        return None
    return json.loads((store() / f"{json.loads(p.read_text())['evidence_id']}.json").read_text())


def issues(record):
    seq = read(record['sequence_id'])
    out = []
    if workflow.file_hash(path(record['sequence_id'])) != record['sequence_sha256']:
        out.append('sequence_brief_changed')
    if recipe_hashes(seq) != record['recipes']:
        out.append('effect_rebuilt')
    if not workflow.unchanged(record['images']):
        out.append('images_changed')
    return out


@workflow.locked
def handoff(sid):
    record = latest(sid)
    if not record:
        raise ValueError(f'No capture of {sid}; run vfx sequence-review {sid} first')
    stale = issues(record)
    if stale:
        raise ValueError(f'The latest capture of {sid} is stale ({", ".join(stale)}); capture it again')
    seq = read(sid)
    stage = record['stage']
    folder = workflow.WORK / 'handoff'
    folder.mkdir(parents=True, exist_ok=True)
    rub = guard(folder / 'sequence_rubric.json', workflow.ROOT / 'vfx')
    shutil.copy2(RUBRIC, rub)
    eid = record['evidence_id']
    report = folder / f'{eid}.report.json'
    frames = [_frame_number(p) for p in record['frames']]
    frame_dir = workflow.absolute(record['frames'][0]).parent
    names = criteria(stage)
    steals = [item for r in (seq.get('references') or []) for item in r.get('steal', [])] if stage != 'blockout' else []
    concept = (seq.get('concept') or {}).get('image')
    lines = [
        f'# Independent review of the sequence {sid} (stage: {stage})',
        '',
        'You are the reviewer, not the author. Judge only what the images show; do not open vfx/src, vfx/recipes or the',
        'author\'s notes. The theme and step list below are context, not evidence.',
        '',
        f'Rubric (authoritative; score only the criteria whose "stages" include "{stage}"): {rub}',
        '',
        '## Open these images',
        *[f'- {workflow.absolute(p)}' for p in record['images']],
        f'Full-size frames: {frame_dir}/{sid}_fNNN.png  (captured frames: {frames})',
        *([f'Visual target (paintover concept the author is aiming at): {workflow.ROOT / concept}'] if concept else []),
        '',
        '## Context',
        f'Source of the frames: {"the game itself (real character, animation and camera)" if record["source"] == "game" else "the VFX Lab (stand-in dummies)"}',
        f'Theme: {seq.get("theme")}',
        'Steps (seconds from the start; the effect fired at that moment): ' + json.dumps(seq['steps'], ensure_ascii=False),
        *(['Blockout stage: shapes and colours are placeholders on purpose. Judge only timing, rhythm, size, '
           'placement, readability and whether every beat belongs to one idea.'] if stage == 'blockout' else []),
        *(['Steal list (check each one: is it visibly present in the frames?): ' + json.dumps(steals, ensure_ascii=False)] if steals else []),
        '',
        '## Output',
        f'Write exactly one JSON object to {report}:',
        json.dumps({'id': sid, 'stage': stage, 'scores': {k: 0 for k in names},
                    **({'steals': [{'item': s, 'seen': False} for s in steals]} if steals else {}),
                    'worst': '<a lowest-scoring criterion>', 'cut': '<an element that does not belong to the theme, or "">',
                    'fix': '<one concrete change, naming frames>', 'verdict': 'ship or iterate',
                    'observed_frames': ['<frame numbers you looked at>']}, ensure_ascii=False),
        'Scores are 0-3 (0 missing or wrong, 1 present but weak, 2 clearly works, 3 reads instantly with its own identity).',
        'verdict is "iterate" if any score is below 2, otherwise "ship". Then reply with the scores, verdict and fix.',
    ]
    prompt = '\n'.join(lines) + '\n'
    brief = guard(folder / f'{eid}.md', workflow.ROOT / 'vfx')
    brief.write_text(prompt, encoding='utf-8')
    return {'ok': True, 'sequence_id': sid, 'evidence_id': eid, 'stage': stage, 'prompt_file': str(brief), 'report_file': str(report),
            'next': f'Give the prompt file to a separate agent that has not seen the recipes, then: vfx sequence-submit {eid} {report} --reviewer <id>'}


@workflow.locked
def submit(eid, report_path, reviewer):
    record = json.loads((store() / f'{eid}.json').read_text())
    stale = issues(record)
    if stale:
        raise ValueError('Cannot review stale evidence: ' + ', '.join(stale))
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    names = criteria(record['stage'])
    scores = report.get('scores', {})
    if set(scores) != set(names) or any(type(v) is not int or not 0 <= v <= 3 for v in scores.values()):
        raise ValueError(f'Scores must be integers 0..3 for exactly {names}')
    if report.get('id') != record['sequence_id'] or report.get('worst') not in names or scores[report['worst']] != min(scores.values()):
        raise ValueError('Report id or worst criterion is invalid')
    verdict = 'ship' if min(scores.values()) >= 2 else 'iterate'
    if report.get('verdict') != verdict or not str(report.get('fix', '')).strip():
        raise ValueError('Report needs one fix and a verdict consistent with its scores')
    captured = {_frame_number(p) for p in record['frames']}
    # Reviewers sometimes quote frame numbers as strings; the frames themselves are what is checked.
    observed = [int(f) if isinstance(f, str) and f.strip().isdigit() else f for f in report.get('observed_frames') or []]
    if not observed or any(type(f) is not int or f not in captured for f in observed):
        raise ValueError('observed_frames must name captured frames')
    if not reviewer or reviewer.lower() in ('author', 'self'):
        raise ValueError('A separately assigned reviewer identifier is required')
    review = {'evidence_id': eid, 'reviewer': reviewer, 'time': _now(), 'report': report, 'rubric_sha256': workflow.file_hash(RUBRIC),
              'image_hashes': record['images'], 'independence': 'host_attested'}
    workflow.save_json(store() / f'reviews/{eid}.json', review)
    gate = None
    if record['stage'] == 'blockout':
        gate = {'evidence_id': eid, 'verdict': verdict, 'reviewer': reviewer, 'time': review['time'], 'scores': scores}
        if verdict == 'ship':
            workflow.save_json(gate_path(record['sequence_id']), gate)
    return {'ok': True, 'sequence_id': record['sequence_id'], 'stage': record['stage'], 'verdict': verdict,
            'blockout_gate': ('open: detail work may start' if gate and verdict == 'ship' else 'closed' if gate else None)}


@workflow.locked
def paintover(sid, frame=None):
    """Pick a captured key frame and write the image-edit prompt that turns it into the concept painting."""
    record = latest(sid)
    if not record:
        raise ValueError(f'No capture of {sid}; run vfx sequence-review {sid} first')
    seq = read(sid)
    by = {_frame_number(p): workflow.absolute(p) for p in record['frames']}
    if frame is None:
        last = round(float(seq['steps'][-1]['t']) * 60) + 12
        frame = min(by, key=lambda f: abs(f - last))
    if frame not in by:
        raise ValueError(f'Frame {frame} was not captured; available: {sorted(by)}')
    folder = workflow.ROOT / f'vfx/concepts/{sid}'
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / f'paintover_source_f{frame:03d}.png'
    shutil.copy2(by[frame], source)
    steals = [f'- {item} (from {r.get("source")})' for r in (seq.get('references') or []) for item in r.get('steal', [])]
    # The look comes from the brief: a realistic sequence must not be repainted as a toon concept.
    style = seq.get('style') or 'the same visual style as the screenshot'
    prompt = '\n'.join([
        'Paint over this game screenshot as a VFX concept frame. Keep the camera, the characters, their poses, the',
        'ground and the composition exactly; repaint only the visual effect, as a game VFX concept in this style:',
        f'{style}. Keep clear value contrast (a hot core, a saturated body, darker accents or residue) and readable',
        'silhouettes.',
        f'Theme: {seq.get("theme")}',
        'Add the elements stolen from the references that belong in this moment of the sequence:',
        *(steals or ['- (no steal list yet: add references with steal lists to the sequence brief first)']),
        'No text, no labels, no UI, no watermark.',
    ]) + '\n'
    (folder / 'paintover_prompt.txt').write_text(prompt, encoding='utf-8')
    concept = folder / 'concept.png'
    return {'ok': True, 'sequence_id': sid, 'frame': frame, 'source_image': str(source), 'prompt_file': str(folder / 'paintover_prompt.txt'),
            'prompt': prompt, 'concept_image': str(concept),
            'next': ('Give the source image and the prompt to an image-edit model (the source as the reference image). Save its '
                     f'untouched output as {concept}, then set the sequence brief\'s concept to '
                     f'{{"image": "vfx/concepts/{sid}/concept.png", "frame": {frame}}} and compare later rounds with vfx concept-compare {sid}.')}


def concept_compare(sid):
    from PIL import Image, ImageDraw
    seq = read(sid)
    concept = seq.get('concept') or {}
    image = workflow.ROOT / concept.get('image', '')
    if not concept.get('image') or not image.is_file():
        raise FileNotFoundError('The sequence has no concept image yet (vfx paintover)')
    record = latest(sid)
    if not record:
        raise ValueError(f'No capture of {sid}')
    by = {_frame_number(p): workflow.absolute(p) for p in record['frames']}
    frame = min(by, key=lambda f: abs(f - int(concept.get('frame', 0))))
    a = Image.open(image).convert('RGB')
    b = Image.open(by[frame]).convert('RGB')
    h = 540
    a = a.resize((round(a.width * h / a.height), h))
    b = b.resize((round(b.width * h / b.height), h))
    canvas = Image.new('RGB', (a.width + b.width + 12, h + 28), (8, 10, 16))
    draw = ImageDraw.Draw(canvas)
    canvas.paste(a, (0, 28))
    canvas.paste(b, (a.width + 12, 28))
    draw.text((8, 6), 'CONCEPT (visual target)', fill=(255, 200, 140))
    draw.text((a.width + 20, 6), f'CURRENT f{frame} ({record["source"]}, evidence {record["evidence_id"][:8]})', fill=(140, 255, 160))
    target = workflow.ROOT / f'vfx/previews/sequences/{sid}_concept_compare.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)
    return {'ok': True, 'image': str(target), 'frame': frame}
