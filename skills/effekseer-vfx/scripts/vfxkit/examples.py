"""Shipped example effects: four ranged pairs (projectile + impact), five single effects and the kaiju set (world scale,
beam, charge chain, photographic explosion), with briefs and painted textures.

`add` copies an example into the project like any hand-written effect. Its historical review describes the
source renders, not your build: build and review it again before relying on it.
"""
import json
import shutil
from pathlib import Path
from . import workflow
from .paths import ASSETS, ROOT
from .ownership import guard

EXAMPLES = ASSETS / 'examples'


def catalog():
    return json.loads((EXAMPLES / 'catalog.json').read_text())


def ids(name):
    data = catalog()
    pairs = {p['name']: p for p in data['pairs']}
    singles = {s['name']: s for s in data.get('singles', [])}
    sets = {s['name']: s for s in data.get('sets', [])}
    if name == 'all':
        return ([i for p in pairs.values() for i in (p['projectile'], p['impact'])] + [s['effect'] for s in singles.values()]
                + [i for s in sets.values() for i in s['effects']])
    if name in pairs:
        return [pairs[name]['projectile'], pairs[name]['impact']]
    if name in singles:
        return [singles[name]['effect']]
    if name in sets:
        return list(sets[name]['effects'])
    if (EXAMPLES / f'src/{name}.py').is_file():
        return [name]
    raise ValueError(f'Unknown example {name!r}; choose all, a pair ({", ".join(pairs)}), a single ({", ".join(singles)}), '
                     f'a set ({", ".join(sets)}) or an effect ID')


def textures(rid):
    from .primitives import walk, TEXTURE_KEYS
    from .library import load
    recipe = load(EXAMPLES / f'src/{rid}.py')
    return sorted({Path(l[k]).stem for l in walk(recipe['layers']) for k in TEXTURE_KEYS if l.get(k)})


def listing():
    data = catalog()
    return {'ok': True, 'note': data['note'], 'pairs': data['pairs'], 'singles': data.get('singles', []), 'sets': data.get('sets', []),
            'historical_scores': data['historical_scores'], 'historical_review': data.get('historical_review'),
            'usage': 'vfx examples show <name|ID>; vfx examples add <name|ID|all>; then vfx lint, vfx build, vfx review'}


@workflow.locked
def add(name, force=False):
    from .scaffold import initialize
    initialize(install_plugin=False)
    chosen = ids(name)
    prompts_path = ROOT / 'vfx/texture_prompts.json'
    prompts = json.loads(prompts_path.read_text())
    shipped = {p['id']: p for p in json.loads((EXAMPLES / 'texture_prompts.json').read_text())['prompts']}
    copied, skipped, present = [], [], []
    for rid in chosen:
        pairs = [(EXAMPLES / f'src/{rid}.py', ROOT / f'vfx/src/{rid}.py'), (EXAMPLES / f'briefs/{rid}.json', ROOT / f'vfx/briefs/{rid}.json')]
        for stem in textures(rid):
            painted = EXAMPLES / f'textures/{stem}.png'
            if painted.is_file():
                pairs.append((painted, ROOT / f'vfx/textures/processed/{stem}.png'))
        for source, target in pairs:
            if target.is_file() and target.read_bytes() == source.read_bytes():
                present.append(workflow.relative(target))  # identical already: a starter texture from init, or shared by a pair
                continue
            if target.exists() and not force:
                skipped.append(workflow.relative(target))
                continue
            guard(target, ROOT / 'vfx').parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(workflow.relative(target))
        known = {p['id'] for p in prompts['prompts']}
        prompts['prompts'] += [shipped[s] for s in textures(rid) if s in shipped and s not in known]
    workflow.save_json(prompts_path, prompts)
    return {'ok': True, 'effects': chosen, 'copied': copied, 'already_present': sorted(set(present)), 'skipped_existing': skipped,
            'next': 'vfx lint --ids ' + ' '.join(chosen) + ' ; vfx build --ids ' + ' '.join(chosen)}


def show(rid):
    """Layer plan with absolute frames, so an example can be read as a timeline before it is adapted."""
    from .briefs import timeline
    from .primitives import walk, budget
    from .library import load
    from .lint import lint
    path = EXAMPLES / f'src/{rid}.py'
    if not path.is_file():
        raise ValueError(f'Unknown example effect {rid}')
    recipe = load(path)
    brief = json.loads((EXAMPLES / f'briefs/{rid}.json').read_text())
    roles = {item['name']: item['role'] for item in brief.get('layer_plan', [])}
    plan = []
    for row, layer in zip(timeline(recipe['layers'], release=(recipe.get('flight') or recipe.get('hold') or 0) * 60), walk(recipe['layers'])):
        plan.append({**row, 'role': roles.get(row['path'], 'supporting detail'), 'renderer': layer.get('renderer', 'Sprite'),
                     'texture': Path(layer['texture']).stem if layer.get('texture') else None})
    result = {'ok': True, 'id': rid, 'design': recipe.get('design'), 'delivery': recipe.get('delivery'),
              'source': workflow.relative(path), 'layer_plan': plan,
              'particle_budget': sum(budget(l) for l in recipe['layers']),
              'historical_scores': catalog()['historical_scores'].get(rid),
              'historical_verdict': (catalog().get('historical_review') or {}).get('verdicts', {}).get(rid),
              'known_weakest': (catalog().get('historical_review') or {}).get('worst', {}).get(rid)}
    from .paths import initialized
    note = 'run vfx examples add, then vfx lint, inside an initialized project to lint against its textures'
    if not initialized():
        result['lint'] = note
    else:
        try:
            result['lint'] = lint(recipe)
        except FileNotFoundError:
            result['lint'] = note
    return result


def show_any(name):
    """`show` for one effect, or for every effect of a named example (a pair shows projectile and impact)."""
    chosen = ids(name)
    if len(chosen) == 1:
        return show(chosen[0])
    return {'ok': True, 'example': name, 'effects': [show(rid) for rid in chosen]}
