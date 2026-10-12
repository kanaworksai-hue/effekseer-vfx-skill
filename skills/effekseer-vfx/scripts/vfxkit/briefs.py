"""Design briefs (vfx/briefs/<ID>.json) live outside the strict Effekseer layer schema."""
import json
import math
from collections import Counter
from . import workflow
from .paths import ASSETS

FIELDS = {'schema_version', 'effect_id', 'role', 'style', 'dominant_shape', 'palette', 'delivery',
          'anchor', 'reference', 'beats', 'layer_plan', 'acceptance', 'avoid'}


def read(rid):
    path = workflow.ROOT / f'vfx/briefs/{workflow.effect_id(rid)}.json'
    return json.loads(path.read_text()) if path.is_file() else None


def timeline(layers, parent_start=0, parent_end=0, prefix='', release=0):
    """Absolute first/last births, including parent emission intervals and random life."""
    rows = []
    for index, layer in enumerate(layers):
        name = layer['name']
        start = parent_start + layer.get('delay', 0)
        end = parent_end + layer.get('delay', 0) + (layer.get('count', 1) - 1) * layer.get('interval', 0)
        if layer.get('infinite'):
            end = parent_end + max(release, layer.get('delay', 0))
        life = layer.get('life', 24)
        life = max(life) if isinstance(life, (list, tuple)) else life
        path = prefix + str(index) + ':' + name
        rows.append({'name': name, 'path': path, 'start_frame': start,
                     'last_birth_frame': end, 'end_frame': end + life,
                     'sustained': bool(layer.get('infinite'))})
        rows.extend(timeline(layer.get('children', []), start, end, path + '/', release))
    return rows


def validate(brief, recipe):
    errors, warnings = [], []
    if not isinstance(brief, dict):
        return {'ok': False, 'errors': ['Design brief is missing: write vfx/briefs/<ID>.json first (see references/design.md)'], 'warnings': []}
    from jsonschema import Draft202012Validator
    schema_path = ASSETS / 'brief.schema.json'
    if not schema_path.is_file():
        return {'ok': False, 'errors': ['Design brief schema is missing'], 'warnings': []}
    schema = json.loads(schema_path.read_text())
    schema_errors = list(Draft202012Validator(schema).iter_errors(brief))
    if schema_errors:
        return {'ok': False, 'errors': [f'{"/".join(map(str,e.absolute_path))}: {e.message}' for e in schema_errors], 'warnings': []}
    errors += [f'Missing field: {k}' for k in sorted(FIELDS - {'reference'} - set(brief))]
    errors += [f'Unknown field: {k}' for k in sorted(set(brief) - FIELDS)]
    if brief.get('schema_version') != 1:
        errors.append('schema_version must be 1')
    if brief.get('effect_id') != recipe['id']:
        errors.append('effect_id differs from recipe')
    if brief.get('delivery') != recipe.get('delivery'):
        errors.append('delivery differs from recipe')
    if brief.get('anchor') != recipe.get('attach'):
        errors.append('anchor differs from recipe')
    for key in ('role', 'style', 'dominant_shape'):
        if not isinstance(brief.get(key), str) or not brief[key].strip():
            errors.append(f'{key} needs a nonempty description')
    for key in ('acceptance', 'avoid'):
        value = brief.get(key)
        if not isinstance(value, list) or not value or any(not isinstance(v, str) or not v.strip() for v in value):
            errors.append(f'{key} needs observable descriptions')
    palette = brief.get('palette')
    if not isinstance(palette, dict) or not {'core', 'body', 'dark', 'matter'} <= set(palette):
        errors.append('palette needs core, body, dark and matter roles')
    elif any(not isinstance(c, list) or len(c) not in (3, 4) or
             any(type(v) is not int or not 0 <= v <= 255 for v in c) for c in palette.values()):
        errors.append('palette colors must be RGB or RGBA integer values 0..255')
    beats = brief.get('beats')
    if not isinstance(beats, list) or not beats:
        errors.append('beats needs at least one key moment')
    else:
        previous = -1
        for beat in beats:
            frame = beat.get('frame') if isinstance(beat, dict) else None
            if type(frame) is not int or not 0 <= frame <= math.ceil(recipe['duration'] * 60) + 12:
                errors.append('beat frame must be an absolute 60 FPS integer within effect + 12 frames')
            elif frame < previous:
                errors.append('beats must be ordered by frame')
            else:
                previous = frame
            if not isinstance(beat, dict) or not beat.get('name') or not beat.get('expect'):
                errors.append('each beat needs name and expect')
    rows = timeline(recipe['layers'], release=(recipe.get('flight') or recipe.get('hold') or 0)*60)
    duplicates = [n for n, c in Counter(r['path'] for r in rows).items() if c > 1]
    if duplicates:
        errors.append(f'Layer paths must be unique for brief association: {duplicates}')
    plans = brief.get('layer_plan')
    if not isinstance(plans, list) or not plans:
        errors.append('layer_plan needs at least one named layer')
    else:
        seen = set()
        for item in plans:
            if not isinstance(item, dict) or not {'name', 'role', 'primitive', 'exit'} <= set(item):
                errors.append('layer_plan entries need name, role, primitive and exit')
                continue
            if item['name'] in seen:
                errors.append(f'Duplicate layer_plan name: {item["name"]}')
            seen.add(item['name'])
            if item['name'] not in {r['path'] for r in rows}:
                errors.append(f'Unknown planned layer: {item["name"]}')
        unplanned = {r['path'] for r in rows} - seen
        if unplanned:
            warnings.append(f'Unplanned layers: {sorted(unplanned)}')
    reference = brief.get('reference')
    if reference is not None:
        if not isinstance(reference, dict) or not isinstance(reference.get('id'), str):
            errors.append('reference needs a reference id')
    return {'ok': not errors, 'errors': errors, 'warnings': warnings, 'timeline': rows}


def keyframes(recipe, brief=None):
    end = math.ceil(recipe['duration'] * 60)
    peak = round(recipe.get('peak', 0) * 60)
    frames = {1, max(1, round(end * .3)), max(1, round(end * .65)), end, end + 6}
    frames.update(range(max(1, peak - 2), peak + 4))
    if brief:
        frames.update(b['frame'] for b in brief.get('beats', []) if type(b.get('frame')) is int and b['frame'] > 0)
    return sorted(f for f in frames if 0 < f <= end + 12)
