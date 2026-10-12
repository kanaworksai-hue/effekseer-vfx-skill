"""World scale, game-driven bind equations, beams, charge chains and soft particles.

The Core round trips are marked requires_core; everything else is pure Python."""
import copy
import math

import pytest

from conftest import ASSETS, requires_core


def recipe_with(layers, **kw):
    from vfxkit.primitives import effect
    return effect('Scale_Test', 'Scale test', 'hit', 'physical', 1.0, layers, **kw)


# ---------------------------------------------------------------- scale

def test_scale_profiles_numbers_and_dicts():
    from vfxkit.scale import profile, PROFILES
    assert profile(None) is None
    kaiju = profile('kaiju')
    assert kaiju == dict(profile='kaiju', **PROFILES['kaiju']) and kaiju['world'] == 40 and kaiju['time'] == 2.5
    custom = profile(16)
    assert custom['world'] == 16 and custom['time'] == pytest.approx(2.0) and custom['budget'] >= 1
    assert profile({'world': 10, 'time': 1, 'budget': 2}) == dict(profile='custom', world=10.0, time=1.0, budget=2.0)
    for bad in ('huge', {'world': 0}, {'world': 4, 'speed': 2}, {'world': 4, 'time': -1}, {'world': 4, 'budget': .5}, True):
        with pytest.raises(ValueError):
            profile(bad)


def test_scale_converts_space_on_top_level_layers_and_time_everywhere():
    from vfxkit.scale import apply
    layer = {'name': 'Top', 'life': [10, 20], 'delay': 3, 'interval': 2, 'fade_in': 1, 'fade_out': 4, 'size': [.5, .8], 'size_end': [.2, .4],
             'position': [0, 1, 0], 'velocity': [0, .02, 0], 'acceleration': [0, -.001, 0], 'spin': [0, 0, 6], 'uv_scroll': [0, .01],
             'travel': {'end': [0, [1, 2], 0]}, 'spawn': {'shape': 'Sphere', 'radius': [0, .3]}, 'soft': .2,
             'forces': [{'type': 'Gravity', 'gravity': [0, -.002, 0]}, {'type': 'Turbulence', 'power': .01}],
             'collide': {'height': .02}, 'flipbook': {'x': 4, 'y': 4, 'frame_length': 3},
             'children': [{'name': 'Child', 'life': 8, 'size': .3, 'position': [0, .5, 0], 'velocity': [.01, 0, 0],
                           'forces': [{'type': 'Gravity', 'gravity': [0, -.002, 0]}], 'collide': {'height': .02}},
                          {'name': 'Free child', 'life': 8, 'size': .3, 'inherit': {'scale': 'NotBind'}}]}
    entry = {'id': 'VFX_T', 'duration': 1.0, 'peak': .1, 'hold': 2.0, 'arc': .5, 'layers': [layer]}
    before = copy.deepcopy(entry)
    out = apply(entry, {'world': 10, 'time': 2})
    assert entry == before, 'apply must not mutate its input'
    top, child, free = out['layers'][0], out['layers'][0]['children'][0], out['layers'][0]['children'][1]
    assert out['duration'] == 2 and out['peak'] == .2 and out['hold'] == 4 and out['arc'] == 5
    assert out['scale'] == dict(profile='custom', world=10.0, time=2.0, budget=pytest.approx(10 ** .3, rel=.01))
    # time
    assert top['life'] == [20, 40] and top['delay'] == 6 and top['interval'] == 4 and top['fade_out'] == 8
    assert top['flipbook']['frame_length'] == 6 and top['uv_scroll'] == [0, .005] and top['spin'] == [0, 0, 3]
    assert child['life'] == 16
    # space on the top-level layer: lengths x10, velocity x10/2, acceleration and gravity x10/4
    assert top['size'] == [5, 8] and top['size_end'] == [2, 4] and top['position'] == [0, 10, 0]
    assert top['travel']['end'] == [0, [10, 20], 0] and top['spawn']['radius'] == [0, 3]
    assert top['velocity'] == [0, pytest.approx(.1), 0] and top['acceleration'] == [0, pytest.approx(-.0025), 0]
    assert top['forces'][0]['gravity'][1] == pytest.approx(-.005) and top['forces'][1]['power'] == pytest.approx(.05)
    assert top['soft'] == pytest.approx(2) and top['collide']['height'] == pytest.approx(.2)
    # a child lives in its parent's (already scaled) frame: only time and world-coordinate fields change
    assert child['size'] == .3 and child['position'] == [0, .5, 0] and child['velocity'] == [pytest.approx(.005), 0, 0]
    assert child['forces'][0]['gravity'][1] == pytest.approx(-.0005) and child['collide']['height'] == pytest.approx(.2)
    # ...unless it does not bind its parent's scale
    assert free['size'] == pytest.approx(3)


def test_scale_gives_unsized_layers_a_node_scale_and_keeps_bind_equations_in_world_units():
    from vfxkit.scale import apply
    ring = {'name': 'Ring', 'renderer': 'Ring', 'life': 10}
    bound = {'name': 'Beam', 'life': 10, 'bind': {'scale': [[.5, '@In1'], '@In0', 1], 'position': [0, '@In0', .2]}}
    out = apply({'id': 'VFX_T', 'duration': 1, 'layers': [ring, bound]}, 'kaiju')
    assert out['layers'][0]['scale_start'] == [40, 40, 40]
    assert out['layers'][1]['bind'] == {'scale': [[20, '@In1'], '@In0', 40], 'position': [0, '@In0', 8]}
    assert 'scale_start' not in out['layers'][1]


def test_scaled_life_rounds_down_so_layers_stay_inside_the_stretched_duration():
    from vfxkit.primitives import effect, lifetime, glow
    recipe = effect('Fit', 'Fit', 'hit', 'physical', .5, [glow('Glow', (255, 255, 255, 255), 1, life=29, delay=1)], scale={'world': 3, 'time': 1.37})
    assert all(lifetime(layer) <= recipe['duration'] * 60 for layer in recipe['layers'])
    assert isinstance(recipe['layers'][0]['life'], int)


def test_scale_character_is_a_no_op_and_records_nothing():
    from vfxkit.primitives import glow
    plain = recipe_with([glow('Glow', (255, 255, 255, 255), 1)])
    assert recipe_with([glow('Glow', (255, 255, 255, 255), 1)], scale='character') == plain and 'scale' not in plain


def test_lint_scales_its_craft_limits_with_the_recipe():
    from vfxkit.lint import lint
    from vfxkit.primitives import radial_sparks, flash
    known = ({'T_Spark01', 'T_Flare01'}, set())
    sparks = radial_sparks('Sparks', 70, (255, 200, 120, 255), gravity=.009)
    # A 15-frame flash is too long for a character-scale contact...
    plain = lint(recipe_with([flash('Flash', (255, 255, 255, 255), 1, life=15, delay=6), copy.deepcopy(sparks)], impact=.5), known)
    assert any('particle budget' in e for e in plain['errors'])
    assert any('contact flash lives' in w for w in plain['warnings'])
    # ...but it is what a 6-frame Lab flash becomes at kaiju time (x2.5), and the budget triples.
    scaled = lint(recipe_with([flash('Flash', (255, 255, 255, 255), 1, life=6, delay=2), copy.deepcopy(sparks)], impact=.5, scale='kaiju'), known)
    assert scaled['budget'][1] == 180 and not any('particle budget' in e for e in scaled['errors'])
    assert not any('contact flash lives' in w for w in scaled['warnings'])
    # gravity limit: .009 * 40 / 2.5^2 = .0576 is still legal because the limit scales the same way
    assert not any('gravity' in e for e in scaled['errors'])


def test_shipped_kaiju_examples_are_scaled_and_record_their_profile():
    from vfxkit.library import load
    for rid in ('VFX_Kaiju_Atomic_Charge', 'VFX_Kaiju_Atomic_Beam', 'VFX_Kaiju_Explosion'):
        recipe = load(ASSETS / f'examples/src/{rid}.py')
        assert recipe['scale']['profile'] == 'kaiju' and recipe['scale']['world'] == 40


# ---------------------------------------------------------------- bind and inputs

def test_bind_components_and_equations_are_validated():
    from effekseer_ai.authoring import validate_layer, _code
    ok = {'name': 'B', 'bind': {'scale': [[.5, '@In1'], '@In0', 1], 'position': [0, '@In0 * 0.5', 0]}}
    assert validate_layer(ok) == []
    assert _code([.5, '@In1']) == '0.5 * (@In1)' and _code(2) == '2.0' and _code('@In0') == '@In0'
    for bad in ({'scale': [1, 2]}, {'scale': [1, True, 1]}, {'position': [0, '@In0; os.system(1)', 0]},
                {'position': [0, ['@In0', 1], 0]}, {'rotation': [0, 0, 0]}):
        assert validate_layer({'name': 'B', 'bind': bad}), bad


def test_lint_rejects_bind_conflicts_and_missing_input_defaults():
    from vfxkit.lint import lint
    known = ({'T_Glow01'}, set())
    from vfxkit.primitives import sprite
    def errors(layer, **kw):
        return lint(recipe_with([layer], **kw), known)['errors']
    assert any('bind.scale replaces' in e for e in errors(sprite('A', size=1, bind={'scale': [1, '@In0', 1]}), inputs=[1, 0, 0, 0]))
    assert any('bind.position fixes' in e for e in errors(sprite('A', travel={'end': [0, 1, 0]}, bind={'position': [0, '@In0', 0]}), inputs=[1, 0, 0, 0]))
    assert any('give the recipe inputs' in e for e in errors(sprite('A', bind={'position': [0, '@In2', 0]}), inputs=[1, 1]))
    assert any('four game inputs' in e for e in errors(sprite('A', bind={'position': [0, '@In5', 0]}), inputs=[1, 1, 1, 1]))
    assert not errors(sprite('A', bind={'position': [0, '@In1', 0]}), inputs=[1, 1, 0, 0])


@requires_core
def test_bind_equations_and_input_defaults_survive_core_save_open(tmp_path):
    from effekseer_ai.authoring import compile_effect
    from effekseer_ai.session import EffectSession
    from effekseer_ai.runtime import load_core
    source = tmp_path / 'bind.efkefc'
    compile_effect({'duration': 1, 'inputs': [7, 1, 0, 0], 'layers': [
        {'name': 'Strip', 'life': 12, 'bind': {'scale': [[.5, '@In1'], '@In0', 1]}},
        {'name': 'End', 'life': 12, 'bind': {'position': [0, '@In0', 0]}},
        {'name': 'Same', 'life': 12, 'bind': {'position': [0, '@In0', 0]}}]}, source, tmp_path / 'bind.efk')
    session = EffectSession.open(source)
    core = load_core()
    assert [float(i.Input.Value) for i in core.Dynamic.Inputs.Values][:2] == [7, 1]
    assert len(list(core.Dynamic.Equations.Values)) == 2, 'identical equations are shared'
    strip = session._object_at_path('node/root/0/ScalingValues/Fixed/Scale')
    end = session._object_at_path('node/root/1/LocationValues/Fixed/Location')
    assert session.property_get('node/root/0/ScalingValues/Type/Value') == 'Fixed'
    assert strip.IsDynamicEquationEnabled.Value and strip.DynamicEquation.Value.Code.Value == '@O.x = 0.5 * (@In1)\n@O.y = @In0\n@O.z = 1.0'
    assert end.DynamicEquation.Value.Code.Value == '@O.x = 0.0\n@O.y = @In0\n@O.z = 0.0'
    assert (tmp_path / 'bind.efk').read_bytes()[:4] == b'SKFE'


# ---------------------------------------------------------------- beam and charge

def test_beam_layers_are_held_axial_strips_bound_to_length_and_power():
    from vfxkit.primitives import beam, walk, held, BEAM_LENGTH, BEAM_POWER
    layers = beam('Ray', (255, 255, 255, 255), (60, 150, 255, 255), (25, 60, 220, 130), width=.5, interval=6, steam=(200, 200, 200, 120))
    names = [l['name'] for l in layers]
    assert names[:4] == ['Ray haze', 'Ray rim', 'Ray body', 'Ray core'] and names[-1] == 'Ray hit point'
    for strip in layers[:4]:
        assert strip['billboard'] == 'YAxisFixed' and strip['pivot'] == 'bottom'
        assert strip['bind']['scale'][1] == BEAM_LENGTH and strip['bind']['scale'][0][1] == BEAM_POWER
    for layer in layers:
        assert layer['infinite'] and layer['life'] == 2 * layer['interval'] and layer['interval'] == 6
    for point in (l for l in layers if ' end ' in l['name'] or l['name'].endswith('hit point')):
        assert point['bind']['position'] == [0, BEAM_LENGTH, 0]
    children = layers[-1]['children']
    assert [c['name'] for c in children] == ['Ray end sparks', 'Ray end steam']
    assert all(c['inherit']['location'] == 'WhenCreating' for c in children) and children[1]['soft'] > 0
    # held(): instance alphas fade in and out over one interval each, so two overlapping instances sum to a constant
    one = held({'name': 'X'}, 5)
    assert one['fade_in'] == one['fade_out'] == one['interval'] == 5 and one['life'] == 10
    assert not [l for l in beam('Plain', (255,) * 4, (0, 0, 255, 255), (0, 0, 255, 100), haze=0, sparks=0) if 'haze' in l['name'] or 'hit point' in l['name']]


def test_beam_recipe_lints_with_hold_and_needs_a_release():
    from vfxkit.lint import lint
    from vfxkit.primitives import beam, beam_inputs, flash, BEAM
    known = ({'T_Glow01', 'T_Flare01', 'T_BeamSection01', 'T_NoiseStreak02', 'T_DistortHaze01', 'T_Spark01', 'T_SmokeSheet01', 'T_NoiseTile01'}, set())
    layers = beam('Ray', (255,) * 4, (60, 150, 255, 255), (25, 60, 220, 130)) + [flash('Ignition', (255,) * 4, 1, delay=1)]
    good = recipe_with(copy.deepcopy(layers), delivery=BEAM, hold=1.0, inputs=beam_inputs(10), peak=.02, impact=.5)
    good['duration'] = 2.0
    report = lint(good, known)
    assert not [e for e in report['errors'] if 'missing' not in e], report['errors']
    unheld = recipe_with(copy.deepcopy(layers), delivery=BEAM, inputs=beam_inputs(10))
    assert any('needs flight' in e and 'or hold' in e for e in lint(unheld, known)['errors'])
    assert beam_inputs(12) == [12, 1.0, 0, 0]


def test_charge_chain_aims_each_arc_at_the_next_anchor_and_lights_in_order():
    from vfxkit.primitives import charge_chain
    anchors = [(0, 0, 0), (0, 1, 0), (1, 1, 1)]
    layers = charge_chain('Plates', anchors, (70, 150, 255, 255), (225, 245, 255, 255), step=4, until=40)
    nodes = [l for l in layers if l['name'].endswith(('node 1', 'node 2', 'node 3'))]
    assert [n['delay'] for n in nodes] == [0, 4, 8] and [n['position'] for n in nodes] == [list(a) for a in anchors]
    arcs = [l for l in layers if ' arc ' in l['name']]
    assert {a['name'][-2:] for a in arcs} == {'1a', '1b', '2a', '2b'}
    for arc in arcs:
        i = int(arc['name'].split(' arc ')[1][0]) - 1
        start, end = anchors[i], anchors[i + 1]
        length = math.dist(start, end)
        direction = [(b - a) / length for a, b in zip(start, end)]
        speed = math.sqrt(sum(v * v for v in arc['velocity']))
        assert arc['billboard'] == 'DirectionalBillboard' and arc['pivot'] == 'bottom' and arc['position'] == list(start)
        assert speed < 1e-3 and [v / speed for v in arc['velocity']] == pytest.approx(direction)
        assert abs(arc['scale_start'][1]) == pytest.approx(length)
    mirrored = {a['name'][-1]: a['scale_start'][0] for a in arcs if a['name'].startswith('Plates arc 1')}
    assert mirrored['a'] == -mirrored['b']
    with pytest.raises(ValueError):
        charge_chain('One', [(0, 0, 0)], (0, 0, 255, 255), (255,) * 4)


def test_lint_counts_repeatedly_emitted_painted_shapes_as_restruck():
    from vfxkit.lint import lint
    from vfxkit.primitives import charge_chain, flash
    known = ({'T_Glow01', 'T_Flare01'}, {'T_ArcStrand01'})
    layers = charge_chain('Plates', [(0, 0, 0), (0, 1, 0)], (70, 150, 255, 255), (225, 245, 255, 255), until=30)
    report = lint(recipe_with(layers + [flash('F', (255,) * 4, 1, delay=6)], impact=.3), known)
    assert not any('no layer changes shape' in w for w in report['warnings'])


# ---------------------------------------------------------------- soft particles

def test_soft_must_be_a_positive_distance_and_warns_when_it_swallows_the_card():
    from vfxkit.lint import lint
    from vfxkit.primitives import sprite
    known = ({'T_SoftCircle'}, set())
    def report(**kw):
        return lint(recipe_with([sprite('Card', 'T_SoftCircle', size=1.0, **kw)]), known)
    assert any('soft is the fade distance' in e for e in report(soft=0)['errors'])
    assert any('soft is the fade distance' in e for e in report(soft=True)['errors'])
    assert any('close to the particle size' in w for w in report(soft=.9)['warnings'])
    assert not report(soft=.3)['errors'] and not any('soft' in w for w in report(soft=.3)['warnings'])


# ---------------------------------------------------------------- review metrics and the Lab

def test_review_tolerances_stretch_with_scaled_time_and_skip_beam_contact(tmp_path):
    from PIL import Image
    from vfxkit.review import metrics
    size = (1280, 800)
    base = Image.new('RGB', size, (10, 12, 18))
    base.save(tmp_path / 'X_f000.png')
    for f in range(4, 61, 4):
        frame = base.copy()
        if f == 40:  # the whitest frame is far from the manifest peak
            frame.paste((255, 255, 255), (500, 300, 640, 420))
        else:
            frame.paste((40, 120, 255), (500, 300, 600, 400))
        frame.save(tmp_path / f'X_f{f:03d}.png')
    entry = {'id': 'X', 'duration': 1.0, 'peak': .05, 'impact': .6}
    flags = metrics('X', tmp_path, entry)['flags']
    assert any('off-peak contact' in f for f in flags)
    beam = metrics('X', tmp_path, entry | {'delivery': {'kind': 'beam'}})['flags']
    assert not any('off-peak contact' in f for f in beam)
    # 36 frames off at 2.5x time is inside the stretched tolerance (max(6, 8) * 2.5 = 20 frames? no: 36 > 20)
    stretched = metrics('X', tmp_path, entry | {'scale': {'time': 5.0}})['flags']
    assert not any('off-peak contact' in f for f in stretched)


def test_lab_scales_its_stage_and_stages_beams():
    lab = (ASSETS / 'godot-lab/scripts/VfxLab.gd').read_text()
    api = (ASSETS / 'godot-lab/scripts/Vfx.gd').read_text()
    handle = (ASSETS / 'godot-lab/scripts/VfxHandle.gd').read_text()
    test = (ASSETS / 'godot-lab/scripts/TestApi.gd').read_text()
    assert 'func _set_stage_scale' in lab and '"beam":' in lab and 'beam_handle.aim(' in lab and 'beam_handle.release()' in lab
    assert 'func beam(' in api and 'handle.inputs[i]' in api
    assert 'func aim(' in handle and 'func start_beam(' in handle and 'emitter.set_dynamic_input(i, inputs[i])' in handle
    assert 'manager.beam(' in test


def test_beam_cross_section_is_full_strength_along_its_length():
    from vfxkit.textures import masks
    section = masks(64)['T_BeamSection01']
    assert section[:, 32].std() == pytest.approx(0, abs=1e-9)          # constant along V
    assert section[10, 32] > .9 and section[10, 1] < .05                 # bright centre, gone at the edges
