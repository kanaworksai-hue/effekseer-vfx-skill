"""Agent feedback loop: field validation, static lint, review metrics, iteration history and texture
measurement. None of these need EffekseerCore or Godot."""
import copy
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from conftest import ASSETS

DARK = (10, 12, 18)


def test_misspelt_and_nested_unknown_fields_are_rejected_with_suggestions(tmp_path):
    from effekseer_ai.authoring import validate_layer, compile_effect
    layer = {'name': 'Sparks', 'fade_ot': 4, 'ring': {'angle_ends': [0, 90], 'outer': {'start': [1, 0], 'ending': [2, 0]}},
             'travel': {'end': [0, 1, 0], 'ease': 'Linear'},
             'forces': [{'type': 'Gravity', 'gravty': [0, -.001, 0]}, {'power': 1}],
             'children': [{'name': 'Child', 'lifee': 10}, {'life': 3}]}
    errors = ' | '.join(validate_layer(layer))
    assert "'fade_ot'; did you mean 'fade_out'" in errors
    assert "Sparks.ring: unknown field 'angle_ends'; did you mean 'angle_end'" in errors
    assert "Sparks.ring.outer: unknown field 'ending'" in errors
    assert "Sparks.travel: unknown field 'ease'" in errors
    assert "forces[0]: unknown field 'gravty'" in errors and 'forces[1]: force needs a type' in errors
    assert "Sparks/Child: unknown field 'lifee'" in errors and 'layer needs a name' in errors
    # Validation runs before any Core call, so a bad recipe fails the same way with or without Core.
    with pytest.raises(ValueError, match='fade_ot'):
        compile_effect({'layers': [layer]}, tmp_path / 'bad.efkefc')


def test_library_recipes_use_only_known_fields():
    from effekseer_ai.authoring import validate_layer
    from vfxkit.library import library
    recipes = library()
    assert recipes
    assert [e for r in recipes for layer in r['layers'] for e in validate_layer(layer)] == []


def recipe(**changes):
    from vfxkit.primitives import effect, flash, radial_sparks, slash_arc
    layers = [flash('Contact', (255, 255, 255, 255), 3, life=4, delay=2), slash_arc('Arc', (255, 120, 40, 255), life=12, delay=2),
              radial_sparks('Sparks', 10, (255, 200, 120, 255), delay=2, gravity=.001)]
    base = effect('Test', 'Test', 'slash', 'fire', .4, layers, peak=.04, impact=.6)
    return base | changes


def test_lint_passes_the_library_and_reports_each_hard_rule():
    from vfxkit.lint import lint_library, lint
    from vfxkit.library import library
    assert lint_library(library())['ok']
    assert lint(recipe())['errors'] == []
    bad = recipe(category='hit')
    bad['layers'][2] |= {'count': 80, 'forces': [{'type': 'Gravity', 'gravity': [0, -.05, 0]}], 'life': (12, 40), 'fade_ot': 3}
    bad['layers'].append({'name': 'Fake', 'texture': 'vfx/textures/processed/T_Unrecorded.png'})
    errors = ' | '.join(lint(bad)['errors'])
    assert 'particle budget 83 exceeds 60' in errors
    assert 'gravity [0, -0.05, 0] is per frame squared' in errors
    assert 'alive until frame' in errors
    assert "unknown field 'fade_ot'" in errors
    assert 'T_Unrecorded is neither a math primitive nor recorded' in errors and 'T_Unrecorded.png is missing' in errors


def test_lint_accepts_a_cel_contact_and_a_restruck_painted_shape():
    # A short single white-hot additive layer counts as the contact even without flash().
    from vfxkit.lint import lint
    cel = recipe()
    cel['layers'][0] = {'name': 'Cel crescent', 'texture': 'vfx/textures/processed/T_WispTrail01.png', 'color': [240, 215, 255, 255], 'life': 8, 'delay': 2}
    assert not any('contact' in w for w in lint(cel)['warnings']), lint(cel)['warnings']
    # A painted shape (recorded in texture_prompts.json by `examples add`) re-struck on later frames changes shape.
    shard = {'texture': 'vfx/textures/processed/T_IceShard01.png', 'color': [245, 248, 255, 255], 'life': 5}
    strike = recipe()
    strike['layers'] = [strike['layers'][0], shard | {'name': 'Main shard', 'delay': 2}, shard | {'name': 'Restrike', 'delay': 8}]
    assert not any('changes shape' in w for w in lint(strike)['warnings'])


def test_lint_warns_about_craft_problems():
    from vfxkit.lint import lint, lint_library
    no_flash = recipe()
    no_flash['layers'] = no_flash['layers'][1:]
    assert any('without a contact flash' in w for w in lint(no_flash)['warnings'])
    late = recipe(peak=.3)
    assert any('manifest peak is frame 18' in w for w in lint(late)['warnings'])
    static = recipe()
    static['layers'][1] = {'name': 'Sticker', 'texture': 'vfx/textures/processed/T_Glow01.png', 'color': [120, 60, 255, 255], 'life': 12}
    static['layers'][0]['color'] = [120, 60, 255, 255]
    static['layers'][2]['color'] = [120, 60, 255, 255]
    static['layers'][2]['color_end'] = [60, 20, 200, 255]
    warnings = ' | '.join(lint(static)['warnings'])
    assert 'no layer changes shape' in warnings and 'no white-hot additive colour' in warnings
    # A copy that only swaps colours and element is a recolour, not a new element.
    original = recipe()
    recolour = copy.deepcopy(original) | {'id': 'VFX_Recolour', 'element': 'ice'}
    for layer in recolour['layers']:
        layer['color'] = [90, 180, 255, 255]
    result = lint_library([original, recolour])
    assert any('only in 0 of shape/motion/rhythm/material/secondary' in w for w in result['warnings']['VFX_Test'])


def frames(folder, rid, plan, size=(1280, 800)):
    """plan: {frame: [(box, colour), ...]} with boxes relative to the review crop."""
    from vfxkit.review import CROP
    for frame in range(0, max(plan) + 1, 3):
        image = Image.new('RGB', size, DARK)
        draw = ImageDraw.Draw(image)
        for (x0, y0, x1, y1), colour in plan.get(frame, []):
            draw.ellipse((CROP[0] + x0, CROP[1] + y0, CROP[0] + x1, CROP[1] + y1), fill=colour)
        image.save(folder / f'{rid}_f{frame:03d}.png')


def test_review_metrics_accept_a_well_formed_effect(tmp_path):
    from vfxkit.review import metrics
    plan = {0: []}
    for f in range(3, 31, 3):
        y = 400 - f * 6
        r = 60 if f > 3 else 30
        if f >= 24:
            plan[f] = [((375, y - 25, 425, y + 25), (255, 150, 60))]  # rising embers carry the dissipation to the end
            continue
        plan[f] = [((300, y - r, 500, y + r), (255, 110, 30))] + (
            [((370, y - 20, 430, y + 20), (255, 255, 255))] if f <= 6 else [((380, y - 12, 420, y + 12), (255, 240, 220))])
    frames(tmp_path, 'VFX_Good', plan)
    m = metrics('VFX_Good', tmp_path, {'duration': .5, 'peak': .05, 'impact': .8, 'element': 'fire'}, step=3)
    assert m['flags'] == [], m['flags']
    assert m['contact_frame'] == 3 and m['motion']['drift_up'] > 0 and m['layering'][0] > 0 and m['layering'][1] > .3


def test_review_metrics_flag_off_peak_flash_flat_colour_and_wrong_direction(tmp_path):
    from vfxkit.review import metrics
    late = {0: [], **{f: [((300, 300, 500, 500), (255, 120, 40))] for f in range(3, 31, 3)}, 12: [((300, 300, 500, 500), (255, 255, 255))]}
    frames(tmp_path, 'VFX_Late', late)
    m = metrics('VFX_Late', tmp_path, {'duration': .5, 'peak': .05, 'impact': .8}, step=3)
    assert m['contact_frame'] == 12 and any(f.startswith('off-peak contact') for f in m['flags'])
    flat = {0: [], **{f: [((300, 300, 500, 500), (70, 80, 95))] for f in range(3, 31, 3)}}
    frames(tmp_path, 'VFX_Flat', flat)
    flags = ' | '.join(metrics('VFX_Flat', tmp_path, {'duration': .5})['flags'])
    assert 'no white-hot core' in flags and 'washed out' in flags
    sinking = {0: [], **{f: [((300, 200 + f * 8, 500, 300 + f * 8), (255, 120, 40)), ((380, 230 + f * 8, 420, 270 + f * 8), (255, 255, 255))] for f in range(3, 31, 3)}}
    frames(tmp_path, 'VFX_Sink', sinking)
    assert any(f.startswith('sinks') for f in metrics('VFX_Sink', tmp_path, {'duration': .5, 'element': 'fire'})['flags'])
    spreading = {0: [], **{f: [((400 - f * 6, 350 - f * 6, 400 + f * 6, 350 + f * 6), (170, 80, 255))] for f in range(3, 40, 3)},
                 42: [((300, 250, 500, 450), (255, 255, 255))], 45: [((350, 300, 450, 400), (200, 120, 255))]}
    frames(tmp_path, 'VFX_Dark', spreading)
    assert any(f.startswith('expands while charging') for f in metrics('VFX_Dark', tmp_path, {'duration': .8, 'element': 'dark'})['flags'])


def test_short_effect_with_an_empty_second_half_is_a_dead_tail(tmp_path):
    # A short hit that is empty after its first third must flag even though a few ember pixels remain.
    from vfxkit.review import metrics
    plan = {0: [], 3: [((300, 300, 500, 500), (255, 200, 120))], 6: [((330, 330, 470, 470), (255, 160, 80))],
            9: [((390, 390, 410, 410), (255, 120, 40))], 18: []}
    frames(tmp_path, 'VFX_Short', plan)
    m = metrics('VFX_Short', tmp_path, {'duration': .3})
    assert m['last_visible_frame'] == 9 and m['last_active_frame'] == 6
    assert any(f.startswith('dead tail') for f in m['flags'])


def test_review_metrics_do_not_flag_known_false_positives(tmp_path):
    # Each case reproduces a false flag first seen on real frames.
    from vfxkit.review import metrics
    # A short contact flash followed by a long, steady white-hot body (a beam, erupting spikes) is not a lingering flash.
    beam = {0: [], 3: [((340, 290, 460, 410), (255, 255, 255))],
            **{f: [((300, 100, 500, 600), (255, 170, 60)), ((390, 200, 410, 500), (255, 255, 255))] for f in range(6, 31, 3)}}
    frames(tmp_path, 'VFX_Beam', beam)
    m = metrics('VFX_Beam', tmp_path, {'duration': .5, 'peak': .05, 'impact': .8, 'element': 'holy'}, step=3)
    assert m['flash_span'] == 3 and not any(f.startswith('lingering flash') for f in m['flags']), m['flags']
    # A white core that grows during a charge is not part of the release flash.
    charge = {0: [], **{f: [((400 - min(55, 3 * f), 350 - min(55, 3 * f), 400 + min(55, 3 * f), 350 + min(55, 3 * f)), (255, 255, 255))] for f in range(3, 28, 3)},
              30: [((330, 280, 470, 420), (255, 255, 255))], 33: [((390, 340, 410, 360), (120, 220, 255))]}
    frames(tmp_path, 'VFX_Charge', charge)
    m = metrics('VFX_Charge', tmp_path, {'duration': .6, 'peak': .5, 'impact': .5, 'element': 'arcane'}, step=3)
    assert m['contact_frame'] == 30 and m['flash_span'] == 3, m['flash_span']
    # Dark alpha-blended smoke after a bright blast has little change energy but is still visible.
    smoke = {0: [], 3: [((250, 200, 550, 500), (255, 255, 255))], **{f: [((350, 300, 450, 400), (45, 45, 55))] for f in range(6, 28, 3)}, 30: []}
    frames(tmp_path, 'VFX_Smoke', smoke)
    m = metrics('VFX_Smoke', tmp_path, {'duration': .5}, step=3)
    assert m['last_active_frame'] == 27 and not any(f.startswith('dead tail') for f in m['flags']), m['flags']
    # Holy may descend; only fire has to rise.
    falling = {0: [], **{f: [((300, 200 + f * 8, 500, 300 + f * 8), (255, 200, 90)), ((380, 230 + f * 8, 420, 270 + f * 8), (255, 255, 255))] for f in range(3, 31, 3)}}
    frames(tmp_path, 'VFX_Fall', falling)
    assert not any(f.startswith('sinks') for f in metrics('VFX_Fall', tmp_path, {'duration': .5, 'element': 'holy'})['flags'])


def test_review_metrics_flag_dead_tail_and_invisible_effects(tmp_path):
    from vfxkit.review import metrics, CROP
    size = (1280, 800)
    box = (CROP[0] + 100, CROP[1] + 100, CROP[0] + 500, CROP[1] + 500)
    for frame, lit in [(0, False), (3, True), (6, True), *((f, False) for f in range(9, 31, 3))]:
        image = Image.new('RGB', size, DARK)
        if lit:
            image.paste((255, 180, 60), box)
        image.save(tmp_path / f'VFX_A_f{frame:03d}.png')
        Image.new('RGB', size, DARK).save(tmp_path / f'VFX_B_f{frame:03d}.png')
    a = metrics('VFX_A', tmp_path, {'duration': .5})
    b = metrics('VFX_B', tmp_path, {'duration': .5})
    assert a['last_visible_frame'] == 6 and any('dead tail' in f for f in a['flags'])
    assert any('barely visible' in f for f in b['flags'])


def test_round_diff_history_and_comparison_sheet(tmp_path):
    from vfxkit.review import diff, record, compare_sheet
    old = {'flags': ['dead tail: after frame 6 of 18', 'no white-hot core: ...'], 'peak_frame': 3, 'contact_frame': 3, 'last_active_frame': 6, 'duration_frames': 18}
    new = {'flags': ['dead tail: after frame 9 of 18', 'washed out: ...'], 'peak_frame': 3, 'contact_frame': 3, 'last_active_frame': 9, 'duration_frames': 18}
    assert diff(old, new) == {'flags_added': ['washed out'], 'flags_resolved': ['no white-hot core'], 'last_active_frame': [6, 9]}
    assert diff(None, new) == {}
    report = new | {'layering': [.1, .5, .2], 'motion': {}}
    path = record(tmp_path, 'VFX_Test', report, 'shortened tail')
    record(tmp_path, 'VFX_Test', report, 'second round', 'e' * 32)
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [l['note'] for l in lines] == ['shortened tail', 'second round'] and lines[0]['last_active_frame'] == 9
    assert lines[1]['evidence_id'] == 'e' * 32
    Image.new('RGB', (300, 100), 'red').save(tmp_path / 'a.png')
    Image.new('RGB', (300, 120), 'blue').save(tmp_path / 'b.png')
    sheet = Image.open(compare_sheet(tmp_path / 'a.png', tmp_path / 'b.png', tmp_path / 'c.png'))
    assert sheet.size == (300, 268) and sheet.getpixel((10, 60)) == (255, 0, 0) and sheet.getpixel((10, 200)) == (0, 0, 255)


def test_metrics_baseline_is_compact_and_round_trips():
    from vfxkit.review import dump_metrics
    report = {'VFX_A': {'flags': ['dead tail: x'], 'motion': {'drift_up': .1},
                        'timeline': [{'frame': 4, 'coverage': .1, 'centre': [.5, .4]}, {'frame': 8, 'coverage': 0.}]}, 'VFX_B': {'flags': []}}
    text = dump_metrics(report)
    assert json.loads(text) == report
    # One line per timeline frame keeps the tracked file small and its diffs aligned to frames.
    assert '   {"frame":4,"coverage":0.1,"centre":[0.5,0.4]},' in text.splitlines()


def test_texture_measurement_finds_crescent_bulge_and_clipping(tmp_path):
    from vfxkit.textures import inspect
    image = Image.new('RGBA', (256, 256), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.arc((40, 40, 216, 216), 120, 240, fill=(255, 255, 255, 255), width=18)  # "(" bowing toward -x
    image.save(tmp_path / 'arc.png')
    info = inspect(tmp_path / 'arc.png')
    assert abs(info['bulge_deg'] - 180) < 10 and not info['touches_border'] and info['elongation'] > 1.5
    clipped = Image.new('RGBA', (64, 64), (255, 255, 255, 0))
    ImageDraw.Draw(clipped).rectangle((0, 20, 30, 40), fill=(255, 255, 255, 255))
    clipped.save(tmp_path / 'clip.png')
    assert inspect(tmp_path / 'clip.png')['touches_border']


def test_shipped_painted_textures_are_measurable_game_textures():
    # Replaces the original slash-angle check: every painted example texture is a processed RGBA game texture with
    # real content, and `examples add` installs it byte-identical into the project.
    from vfxkit.textures import inspect
    from vfxkit.paths import ROOT
    shipped = sorted((ASSETS / 'examples/textures').glob('*.png'))
    assert shipped
    prompts = {p['id'] for p in json.loads((ASSETS / 'examples/texture_prompts.json').read_text())['prompts']}
    for path in shipped:
        info = inspect(path)
        assert not info.get('empty') and info['coverage'] > 0, path.name
        assert all(n & (n - 1) == 0 and 128 <= n <= 1024 for n in info['size']), (path.name, info['size'])
        with Image.open(path) as image:
            assert image.mode == 'RGBA', path.name
        assert path.stem in prompts, f'{path.stem} has no recorded generation prompt'
        installed = ROOT / f'vfx/textures/processed/{path.name}'
        assert installed.read_bytes() == path.read_bytes(), path.name
