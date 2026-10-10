"""Everything an independent reviewer needs for one capture, as a prompt the author passes on unchanged.

The author must not score its own effect. `vfx review-handoff <ID>` writes a self-contained brief (images, frame
numbers, manifest context, rubric, output format and where to save the report) so a separate agent can review it
whether or not that agent has the vfx-review skill loaded, then returns the command that submits its report.
"""
import json
import shutil
from pathlib import Path

from . import evidence, workflow
from .ownership import guard
from .paths import SKILL, ASSETS

MANIFEST_FIELDS = ('id', 'category', 'element', 'duration', 'peak', 'impact', 'delivery', 'design')


def reviewer_skill():
    """The vfx-review skill installed next to this one (both folders are installed side by side), if present."""
    path = SKILL.parent / 'vfx-review' / 'SKILL.md'
    return path if path.is_file() else None


@workflow.locked
def handoff(rid):
    rid = workflow.effect_id(rid)
    record = evidence.latest(rid)
    if not record:
        raise ValueError(f'No standard capture of {rid}; run vfx review --ids {rid} first')
    issues = evidence.capture_issues(record)
    if issues:
        raise ValueError(f'The latest capture of {rid} is stale ({", ".join(issues)}); run vfx review --ids {rid} again')
    eid = record['evidence_id']
    workspace = workflow.ROOT / 'vfx'  # read at call time, like evidence's store
    folder = workflow.WORK / 'handoff'
    folder.mkdir(parents=True, exist_ok=True)
    rubric = guard(folder / 'review_rubric.json', workspace)
    shutil.copy2(ASSETS / 'review_rubric.json', rubric)
    images = [str(workflow.absolute(p)) for p in record['images']]  # {path: sha256}: the strip and key-frame sheet
    frame_paths = list(record['frames'])
    frames = sorted(int(Path(p).stem.rsplit('_f', 1)[1]) for p in frame_paths if '_f' in Path(p).stem)
    frame_dir = str(workflow.absolute(frame_paths[0]).parent) if frame_paths else None
    metrics = workspace / 'previews/strips/metrics.json'
    flags = (json.loads(metrics.read_text()).get(rid, {}).get('flags') if metrics.is_file() else None) or []
    manifest = {k: record['manifest'].get(k) for k in MANIFEST_FIELDS if k in record['manifest']}
    report = folder / f'{eid}.report.json'
    skill = reviewer_skill()
    lines = [
        f'# Independent review of {rid}',
        '',
        'You are the reviewer, not the author: you did not make this effect. Judge only what the images show.',
        'Do not open or ask for the recipe, the brief or the author\'s notes (nothing under vfx/src, vfx/briefs or',
        'vfx/recipes); the design sentence below is context, not evidence.',
        '',
        (f'Follow the vfx-review skill: read {skill} first and apply it.' if skill else
         'Procedure: score every rubric criterion 0-3 from the images (0 missing or wrong, 1 present but weak, 2 clearly '
         'works, 3 reads instantly with its own identity), name the worst criterion and one concrete fix for it.'),
        f'The rubric (authoritative): {rubric}',
        '',
        '## Open these images with your image viewer',
        *[f'- {path}' for path in images],
        f'Full-size single frames, if you need detail: {frame_dir}/{rid}_fNNN.png' if frame_dir else '',
        f'Captured frame numbers (60 FPS from the effect\'s start; only these can be cited): {frames}',
        '',
        '## Context',
        f'Manifest entry: {json.dumps(manifest, ensure_ascii=False)}',
        f'Automatic flags (hints only; never score from them): {json.dumps(flags, ensure_ascii=False)}',
        'Stage: two stand-in dummies; the caster/player on the left, the target on the right. A projectile strip ends at '
        'arrival and does not show its impact. Heals, shields and buffs need no attack-style white flash; charges build '
        'inward before one release.',
        '',
        '## Output',
        f'Write exactly one JSON object to {report}:',
        '{"id": "%s", "scores": {"read": 0, "timing": 0, "layering": 0, "shape_change": 0, "motion": 0, '
        '"placement": 0, "tail": 0, "identity": 0}, "worst": "<a lowest-scoring criterion>", '
        '"fix": "<one concrete change for the worst criterion, naming frames>", "verdict": "ship or iterate", '
        '"observed_frames": [<frame numbers you actually looked at, from the list above>]}' % rid,
        'verdict is "iterate" if any score is below 2, otherwise "ship". Then reply with your scores, verdict and fix.',
    ]
    prompt = '\n'.join(lines) + '\n'
    brief = guard(folder / f'{eid}.md', workspace)
    brief.write_text(prompt, encoding='utf-8')
    return {'ok': True, 'effect_id': rid, 'evidence_id': eid, 'prompt_file': str(brief), 'report_file': str(report),
            'reviewer_skill': str(skill) if skill else None, 'captured_frames': frames,
            'next': ('Give the prompt file (or its text) to a separate agent that has not seen the recipe: a subagent, or '
                     'a new session the user opens if your host has none. Then run: vfx review-submit '
                     f'{eid} {report} --reviewer <that agent\'s identifier>'),
            'prompt': prompt}
