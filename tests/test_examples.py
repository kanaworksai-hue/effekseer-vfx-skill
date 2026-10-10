"""Shipped example effects: complete, valid, self-consistent with their briefs and safe to add to a project."""
import copy
import json

import pytest

from conftest import ASSETS

EXAMPLES = ASSETS / 'examples'


def example_ids():
    return sorted(p.stem for p in (EXAMPLES / 'src').glob('VFX_*.py'))


def test_catalog_lists_every_shipped_example_as_pairs_and_singles():
    from vfxkit import examples
    catalog = examples.catalog()
    ids = examples.ids('all')
    assert sorted(ids) == example_ids() and len(ids) == len(set(ids)) == 13
    assert [p['name'] for p in catalog['pairs']] == ['fire', 'ice', 'poison', 'dark']
    assert [s['name'] for s in catalog['singles']] == ['hit', 'slash', 'charge', 'shield', 'heal']
    for pair in catalog['pairs']:
        assert examples.ids(pair['name']) == [pair['projectile'], pair['impact']]
        assert pair['teaches']
    for single in catalog['singles']:
        assert examples.ids(single['name']) == [single['effect']] and single['teaches']
    # Every example carries an independent review: all eight criteria scored, a verdict consistent with the scores,
    # and its weakest criterion with the reviewer's one fix.
    review = catalog['historical_review']
    assert set(catalog['historical_scores']) == set(review['verdicts']) == set(review['worst']) == set(ids)
    for rid, scores in catalog['historical_scores'].items():
        assert len(scores) == 8 and all(score in (0, 1, 2, 3) for score in scores.values())
        assert review['verdicts'][rid] == ('iterate' if min(scores.values()) < 2 else 'ship')
        assert scores[review['worst'][rid]['criterion']] == min(scores.values()) and review['worst'][rid]['fix']
    assert examples.ids('VFX_Ice_Spikes') == ['VFX_Ice_Spikes']
    with pytest.raises(ValueError, match='Unknown example'):
        examples.ids('invented')


def test_example_show_accepts_pair_and_single_names():
    from vfxkit import examples
    pair = examples.show_any('fire')
    assert [e['id'] for e in pair['effects']] == ['VFX_Projectile_Fire', 'VFX_Fire_Explosion']
    single = examples.show_any('slash')
    assert single['id'] == 'VFX_Slash_Fire' and single['historical_verdict'] in ('ship', 'iterate')


@pytest.mark.parametrize('rid', example_ids())
def test_each_example_source_loads_and_matches_its_brief(rid):
    from vfxkit import briefs
    from vfxkit.library import load
    recipe = load(EXAMPLES / f'src/{rid}.py')
    brief = json.loads((EXAMPLES / f'briefs/{rid}.json').read_text())
    assert recipe['id'] == brief['effect_id'] == rid
    assert recipe.get('delivery') == brief['delivery']
    assert recipe.get('attach') == brief['anchor']
    result = briefs.validate(brief, recipe)
    assert result['ok'], result['errors']
    assert not result['warnings'], result['warnings']  # every layer has a planned role


def test_lint_of_all_examples_has_no_errors():
    from effekseer_ai.authoring import validate_layer
    from vfxkit.lint import lint_library
    from vfxkit.library import library
    recipes = library()
    assert sorted(r['id'] for r in recipes) == example_ids()
    result = lint_library(recipes)
    assert result['ok'] and result['errors'] == {}, result['errors']
    assert not [e for r in recipes for layer in r['layers'] for e in validate_layer(layer)]


def test_example_show_gives_a_timeline_with_layer_roles_and_paired_projectiles():
    from vfxkit import examples
    ids = set(examples.ids('all'))
    for rid in ids:
        details = examples.show(rid)
        assert details['ok'] and details['id'] == rid and details['design']
        assert len(details['layer_plan']) >= 4
        assert all(row['role'] and row['path'] and row['end_frame'] >= row['start_frame'] for row in details['layer_plan'])
        assert details['source'].startswith('skill:assets/examples/src/')
        assert isinstance(details['lint'], dict) and details['lint']['errors'] == []
        projectile = (details['delivery'] or {}).get('projectile')
        if projectile:
            assert projectile in ids
    with pytest.raises(ValueError, match='Unknown example'):
        examples.show('VFX_Invented')


def test_loaded_examples_are_detached_copies():
    # Editing a loaded recipe never changes the next load (sources are re-executed on every call).
    from vfxkit.library import get
    first = get('VFX_Fire_Explosion')
    first['layers'][0]['name'] = 'edited copy'
    assert get('VFX_Fire_Explosion')['layers'][0]['name'] != 'edited copy'


def test_example_textures_are_installed_and_their_prompts_recorded(project):
    from vfxkit import examples
    prompts = {p['id'] for p in json.loads((project / 'vfx/texture_prompts.json').read_text())['prompts']}
    for rid in examples.ids('all'):
        for stem in examples.textures(rid):
            assert (project / f'vfx/textures/processed/{stem}.png').is_file(), (rid, stem)
            if (EXAMPLES / f'textures/{stem}.png').is_file():
                assert stem in prompts, (rid, stem)


def test_value_pair_preserves_geometry_and_rejects_unsynchronized_randomness():
    from vfxkit.primitives import sprite, ramp, contrast_pair
    source = sprite('Blade', 'T_IceShard01', (255, 120, 30, 255), life=16, delay=3, size=2., rotation=[0, 0, 30],
                    size_curve=[[0, .8], [100, 1.1]], color_curve=ramp((0, (255, 120, 30, 255)), (100, (180, 35, 10, 0)))['color_curve'])
    before = copy.deepcopy(source)
    dark, bright = contrast_pair(source)
    assert source == before and bright == source and dark['blend'] == 'Blend'
    for key in ('life', 'delay', 'size', 'rotation', 'size_curve', 'texture'):
        assert dark[key] == bright[key]
    assert dark['color_curve']['A'][-1][1] == 0
    assert dark['color_curve']['A'][0][1] == pytest.approx(210)
    for changes in ({'rotation': [0, 0, [0, 360]]}, {'size': [1, 2]}, {'life': [12, 16]},
                    {'spawn': {'shape': 'Sphere', 'radius': [0, 1]}}, {'count': 2},
                    {'flipbook': {'x': 4, 'y': 4, 'start': [0, 3]}},
                    {'properties': {'any/path': 1}}):
        with pytest.raises(ValueError):
            contrast_pair(source | changes)
