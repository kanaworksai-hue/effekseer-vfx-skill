"""Layer compiler, Core round trips, texture processing, recipe primitives and the workspace scaffold.

Tests marked requires_core skip cleanly where EffekseerCore is not installed (authoring-only toolchains)."""
import json
import math
from pathlib import Path

import pytest
from PIL import Image

from conftest import ASSETS, requires_core


@requires_core
def test_core_roundtrip_preserves_timing_curves_seed_and_model(tmp_path):
    from effekseer_ai.authoring import compile_effect
    from effekseer_ai.session import EffectSession
    tex = tmp_path / 'raw.png'
    Image.new('RGB', (128, 128), 'white').save(tex)
    source = tmp_path / 'test.efkefc'
    runtime = tmp_path / 'test.efk'
    compile_effect({'duration': 1.2, 'seed': 12345, 'layers': [
        {'name': 'curve', 'delay': 9, 'life': 25, 'interval': 3, 'count': 4, 'texture': str(tex), 'scale_start': 2,
         'scale_curve': [[0, 0], [15, 1], [70, .6], [100, 0]], 'color_curve': {'A': [[0, 0], [20, 255], [100, 0]]}},
        {'name': 'mesh', 'renderer': 'Model', 'life': 35, 'procedural_model': {'Name': 'Test Sphere', 'Shape/PrimitiveType': 'Sphere', 'Shape/Radius': .6}}]},
        source, runtime)
    assert source.read_bytes()[:4] == b'EFKE'
    assert runtime.read_bytes()[:4] == b'SKFE'
    s = EffectSession.open(source)
    n = 'node/root/0'
    assert s.property_get(n + '/CommonValues/Generation/GenerationTimeOffset/Center') == 9
    assert s.property_get(n + '/CommonValues/Generation/GenerationTime/Center') == 3
    assert s.property_get(n + '/RendererCommonValues/AlphaBlend/Value') == 'Add'
    assert len(s.curve_keys(n + '/ScalingValues/FCurve/FCurve/X')) == 4
    assert len(s.curve_keys(n + '/DrawingValues/ColorAll/FCurve/FCurve/A')) == 3
    from effekseer_ai.runtime import load_core
    assert load_core().Global.RandomSeed.Value == 12345
    assert load_core().ProceduralModel.ProceduralModels.Values.Count == 1
    assert s.property_get('node/root/1/DrawingValues/Model/ModelReference/Value') == 'ProceduralModel'


@requires_core
def test_discovery_excludes_import_only_legacy_fields_and_enums_are_validated(tmp_path):
    from effekseer_ai.session import EffectSession
    s = EffectSession.new()
    s.save(tmp_path / 'test.efkefc')
    p = 'node/root/0'
    paths = s.property_list(p)
    assert p + '/DrawingValues/Type/Value' in paths
    assert p + '/CommonValues/Generation/GenerationTimeOffset/Max' in paths
    assert p + '/CommonValues/GenerationTimeOffset/Max' not in paths
    with pytest.raises(ValueError, match='Import-only'):
        s.property_set(p + '/CommonValues/GenerationTimeOffset/Max', 7)
    with pytest.raises(Exception):
        s.property_set(p + '/DrawingValues/Type/Value', 123456)


@requires_core
def test_repeated_compile_is_idempotent_and_changes_do_not_accumulate(tmp_path):
    from effekseer_ai.authoring import compile_effect
    from effekseer_ai.session import EffectSession
    recipe = {'layers': [{'name': 'A', 'count': 6, 'life': 17}, {'name': 'B', 'renderer': 'Ring', 'life': 20}]}
    source = tmp_path / 'test.efkefc'
    runtime = tmp_path / 'test.efk'
    compile_effect(recipe, source, runtime)
    first = runtime.read_bytes()
    compile_effect(recipe, source, runtime)
    assert runtime.read_bytes() == first
    assert len(EffectSession.open(source).node_list()) == 2


@requires_core
def test_shell_fragment_surface_limits_survive_core_save_open(tmp_path):
    from effekseer_ai.authoring import compile_effect
    from effekseer_ai.session import EffectSession
    from vfxkit.primitives import shell_fragments
    pieces = shell_fragments('Fragment', (90, 165, 255, 230), 1.47)
    source = tmp_path / 'fragments.efkefc'
    compile_effect({'duration': 1.8, 'layers': pieces}, source, tmp_path / 'fragments.efk')
    session = EffectSession.open(source)
    nodes = session.node_list()
    assert len(nodes) == 6
    for node in nodes:
        model = session._node(node['path']).DrawingValues.Model.Reference.Value
        assert float(model.Mesh.AngleBeginEnd.X.Value) == pytest.approx(0)
        assert float(model.Mesh.AngleBeginEnd.Y.Value) == pytest.approx(40)
        assert float(model.Shape.DepthMin.Value) == pytest.approx(-.7)
        assert float(model.Shape.DepthMax.Value) == pytest.approx(.85)


@requires_core
def test_value_pair_fixed_geometry_and_alpha_curve_survive_core_roundtrip(tmp_path):
    from effekseer_ai.authoring import compile_effect
    from effekseer_ai.session import EffectSession
    from vfxkit.primitives import sprite, ramp, contrast_pair
    body = sprite('Matched shard', 'T_IceShard01', (255, 120, 30, 255), life=16, delay=3, size=2.0, rotation=[0, 0, 30],
                  color_curve=ramp((0, (255, 120, 30, 255)), (100, (180, 35, 10, 0)))['color_curve'])
    source = tmp_path / 'pair.efkefc'
    compile_effect({'duration': .5, 'layers': contrast_pair(body)}, source, tmp_path / 'pair.efk')
    session = EffectSession.open(source)
    nodes = session.node_list()
    assert len(nodes) == 2
    for node in nodes:
        n = node['path']
        assert session.property_get(n + '/CommonValues/Life/Max') == 16
        assert session.property_get(n + '/CommonValues/Generation/GenerationTimeOffset/Max') == 3
        assert session.property_get(n + '/RotationValues/PVA/Rotation/Z/Max') == 30
        keys = session.curve_keys(n + '/DrawingValues/ColorAll/FCurve/FCurve/A')
        assert keys[-1]['value'] == 0


@requires_core
def test_advanced_layer_features_survive_core_roundtrip(tmp_path):
    from effekseer_ai.authoring import compile_effect
    from effekseer_ai.session import EffectSession
    tex = tmp_path / 'mask.png'
    Image.new('RGBA', (64, 64), (255, 255, 255, 200)).save(tex)
    recipe = {'duration': 1, 'layers': [
        {'name': 'arc', 'renderer': 'Ring', 'billboard': 'Fixed', 'texture': str(tex), 'life': 12,
         'ring': {'outer': [1.5, 0], 'inner': {'start': [1, 0], 'end': [1.4, 0]}, 'angle_start': [0, 120], 'angle_end': [20, 200]},
         'alpha_texture': str(tex), 'cutoff': [[0, 0], [100, .8]], 'edge': {'color': [255, 120, 0, 255], 'threshold': .1, 'scaling': 3}},
        {'name': 'sparks', 'texture': str(tex), 'count': 12, 'life': [10, 20], 'billboard': 'DirectionalBillboard',
         'spawn': {'shape': 'Sphere', 'radius': [0, .2]}, 'travel': {'end': [0, [1, 2], 0]},
         'forces': [{'type': 'Gravity', 'gravity': [0, -.002, 0]}, {'type': 'Turbulence', 'power': .01}],
         'size': [.2, .4], 'size_end': 0, 'color_end': [255, 0, 0, 0], 'collide': {'bounce': [.3, .5]}},
        {'name': 'shell', 'renderer': 'Model', 'life': 30, 'procedural_model': {'Name': 'Shell', 'Shape/PrimitiveType': 'Sphere'},
         'distortion_texture': str(tex), 'distortion_scroll': [0, .02], 'falloff': {'begin': [0, 0, 0, 0], 'end': [255, 255, 255, 255], 'pow': 3, 'blend': 'Mul'}},
        {'name': 'spike', 'texture': str(tex), 'pivot': 'bottom', 'billboard': 'YAxisFixed', 'life': 20},
        {'name': 'haze', 'texture': str(tex), 'material': 'BackDistortion', 'distortion': .6, 'soft': .8, 'flipbook': {'x': 4, 'y': 4, 'frame_length': 3}}]}
    compile_effect(recipe, tmp_path / 'adv.efkefc', tmp_path / 'adv.efk')
    s = EffectSession.open(tmp_path / 'adv.efkefc')
    arc, sparks, shell, spike, haze = [f'node/root/{i}' for i in range(5)]
    assert s.property_get(arc + '/DrawingValues/Ring/RingShape/Type/Value') == 'Crescent'
    assert s.property_get(arc + '/DrawingValues/Ring/RingShape/Crescent/EndingAngle_Easing/End/Max') == 200
    assert s.property_get(arc + '/AdvancedRendererCommonValuesValues/AlphaCutoffParam/Type/Value') == 'FCurve'
    assert len(s.curve_keys(arc + '/AdvancedRendererCommonValuesValues/AlphaCutoffParam/FCurve/S')) == 2
    assert s.property_get(sparks + '/GenerationLocationValues/Type/Value') == 'Sphere'
    assert s.property_get(sparks + '/LocationValues/Type/Value') == 'Easing'
    assert s.property_get(sparks + '/LocationValues/Easing/End/Y/Max') == 2
    assert s.property_get(sparks + '/LocationAbsValues/LocalForceField2/Type/Value') == 'Turbulence'
    assert s.property_get(sparks + '/ScalingValues/Type/Value') == 'SingleEasing'
    assert s.property_get(sparks + '/CollisionsValues/IsGroundCollisionEnabled/Value') is True
    assert s.property_get(sparks + '/CollisionsValues/Bounce/Max') == .5
    assert s.property_get(shell + '/AdvancedRendererCommonValuesValues/UVDistortionTextureParam/Enabled/Value') is True
    assert s.property_get(shell + '/AdvancedRendererCommonValuesValues/FalloffParam/ColorBlendType/Value') == 'Mul'
    assert s.property_get(spike + '/DrawingValues/Sprite/Position_Fixed_LL/Y/Value') == 0
    assert s.property_get(haze + '/RendererCommonValues/Material/Value') == 'BackDistortion'
    assert s.property_get(haze + '/AdvancedRendererCommonValuesValues/SoftParticleParams/Enabled/Value') is True
    assert s.property_get(haze + '/RendererCommonValues/UVAnimation/AnimationParams/FrameCountX/Value') == 4
    with pytest.raises(ValueError, match='four local force fields'):
        compile_effect({'layers': [{'name': 'x', 'forces': [{'type': 'Gravity', 'gravity': [0, 0, 0]}] * 5}]}, tmp_path / 'bad.efkefc')


@requires_core
def test_curve_tangent_data_roundtrips_and_invalid_edit_preserves_keys(tmp_path):
    from effekseer_ai.session import EffectSession
    s = EffectSession.new()
    s.save(tmp_path / 'curve.efkefc')
    p = 'node/root/0/ScalingValues/SingleFCurve/S'
    s.curve_set_keys(p, [{'frame': 0, 'value': 0, 'right': [10, .2], 'interpolation': 0}, {'frame': 100, 'value': 1, 'left': [90, .8], 'interpolation': 0}])
    before = s.curve_keys(p)
    with pytest.raises(ValueError, match='unique integers'):
        s.curve_set_keys(p, [{'frame': 0, 'value': 1}, {'frame': 0, 'value': 2}])
    assert s.curve_keys(p) == before
    s.save()
    after = EffectSession.open(tmp_path / 'curve.efkefc').curve_keys(p)
    assert after[0]['right'][0] == 10
    assert math.isclose(after[0]['right'][1], .2, abs_tol=1e-5)
    assert after[1]['left'][0] == 90


def test_texture_processing_preserves_original_and_straight_alpha(tmp_path):
    from effekseer_ai.resources import process_texture
    raw = tmp_path / 'raw.png'
    im = Image.new('RGB', (256, 256), 'black')
    im.paste('white', (50, 60, 190, 170))
    im.save(raw)
    original = raw.read_bytes()
    output = tmp_path / 'processed.png'
    process_texture(str(raw), str(output), 128)
    assert raw.read_bytes() == original
    result = Image.open(output)
    assert result.size == (128, 128) and result.mode == 'RGBA'
    assert result.getpixel((0, 0)) == (255, 255, 255, 0)
    assert result.getpixel((64, 64)) == (255, 255, 255, 255)
    with pytest.raises(ValueError):
        process_texture(str(raw), str(raw), 128)


def test_flipbook_sheet_keeps_cells_in_place_and_feathers_their_borders(tmp_path):
    from effekseer_ai.resources import process_texture
    raw = tmp_path / 'sheet.png'
    im = Image.new('RGB', (512, 512), 'white')
    im.paste('black', (0, 0, 256, 256))
    im.save(raw)
    r = process_texture(str(raw), str(tmp_path / 'out.png'), 256, grid=(2, 2))
    result = Image.open(tmp_path / 'out.png')
    assert r['grid'] == [2, 2] and result.size == (256, 256)
    # No crop/re-centre: the empty top-left cell stays empty and the bottom-right cell stays solid in its middle.
    assert result.getpixel((64, 64))[3] == 0 and result.getpixel((192, 192))[3] == 255
    # Cell borders are feathered so neighbouring frames cannot bleed into each other.
    assert result.getpixel((128, 192))[3] == 0 and result.getpixel((255, 192))[3] == 0


def test_manifest_matches_assets_and_particle_lifetimes():
    from vfxkit.primitives import lifetime
    from vfxkit.paths import ROOT
    manifest = ROOT / 'vfx/vfx_manifest.json'
    if not manifest.is_file():
        pytest.skip('VFX outputs are local only; build them before asset integration tests')
    entries = json.loads(manifest.read_text())
    if not entries:
        pytest.skip('No built effect library (vfx build needs EffekseerCore)')
    assert len({e['id'] for e in entries}) == len(entries)
    for entry in entries:
        recipe = json.loads((ROOT / f'vfx/recipes/{entry["id"]}.json').read_text())
        for layer in recipe['layers']:
            life = lifetime(layer, release=entry.get('flight', 0) * 60)
            assert entry['loop'] or entry['duration'] * 60 >= life, (entry['id'], layer['name'], life)
        assert 0 <= entry['peak'] < entry['duration']
        assert (ROOT / f'vfx/effects/{entry["id"]}.efkefc').is_file()
        assert (ROOT / f'vfx/exports/{entry["id"]}.efk').is_file()


def test_library_recipes_are_valid_without_core_or_assets():
    from vfxkit.primitives import lifetime, budget, walk, TEXTURE_KEYS
    from vfxkit.library import library
    from vfxkit.textures import masks, EXTRA_PROCEDURAL
    from vfxkit.paths import ROOT
    available = set(masks(16)) | EXTRA_PROCEDURAL | {p['id'] for p in json.loads((ROOT / 'vfx/texture_prompts.json').read_text())['prompts']}
    recipes = library()
    ids = [r['id'] for r in recipes]
    assert len(set(ids)) == len(ids) == 13
    for recipe in recipes:
        layers = list(walk(recipe['layers']))
        assert recipe['design'] and len(layers) >= 4, recipe['id']
        assert max(lifetime(layer, release=recipe.get('flight', 0) * 60) for layer in recipe['layers']) <= recipe['duration'] * 60, recipe['id']
        assert sum(budget(layer) for layer in recipe['layers']) <= 250, recipe['id']
        for layer in layers:
            for key in TEXTURE_KEYS:
                # Every input is either a math primitive or has a recorded image prompt; nothing is undocumented.
                if layer.get(key):
                    assert Path(layer[key]).stem in available, (recipe['id'], layer[key])
                    resolved = Path(layer[key]) if '/' in layer[key] else ROOT / f'vfx/textures/processed/{layer[key]}.png'
                    assert resolved.is_file(), (recipe['id'], layer[key])


def test_every_effect_declares_how_a_game_delivers_it():
    # The Lab stages each exchange from `delivery`; projectile impacts must name a projectile that exists.
    from vfxkit.library import library
    recipes = library()
    by_id = {r['id']: r for r in recipes}
    kinds = {'self', 'melee', 'projectile', 'targeted', 'area'}
    for recipe in recipes:
        delivery = recipe.get('delivery') or {}
        assert delivery.get('kind') in kinds, recipe['id']
        if recipe['category'] == 'projectile':
            assert recipe.get('flight') and recipe['attach'] == 'projectile', recipe['id']
            assert any((r.get('delivery') or {}).get('projectile') == recipe['id'] for r in recipes), f"{recipe['id']} has no impact effect"
        elif delivery['kind'] == 'projectile':
            assert by_id[delivery['projectile']]['category'] == 'projectile', recipe['id']


def test_sustained_layers_live_until_release_and_budget_by_overlap():
    from vfxkit.primitives import lifetime, budget
    from vfxkit.lint import lint
    trail = {'name': 'trail', 'infinite': True, 'interval': 2, 'life': [10, 14], 'count': 1, 'delay': 3}
    assert lifetime(trail, release=30) == 30 + 14
    assert budget(trail) == 7
    recipe = {'id': 'VFX_T', 'category': 'projectile', 'element': 'fire', 'duration': .5, 'peak': .05, 'layers': [trail | {'texture': 'T_Glow01'}]}
    assert any('needs flight' in e for e in lint(recipe, (set(), {'T_Glow01'}))['errors'])
    recipe['flight'] = .5
    assert any('alive until frame' in e for e in lint(recipe, (set(), {'T_Glow01'}))['errors'])


def test_reference_primitives_break_shapes_and_decay_to_smoke():
    from vfxkit.primitives import wisps, decay, slice_line, spray, debris
    from vfxkit.lint import lint
    arcs = wisps('w', (200, 100, 255, 255), 1.2, count=4, life=(14, 22), tilt=((-90, 90), (0, 360), (0, 360)))
    # Each stroke takes its own tilt and size, and the erosion starts above zero so no arc is ever a clean ring.
    assert arcs['renderer'] == 'Ring' and isinstance(arcs['rotation'][0], list) and isinstance(arcs['size'], list)
    assert arcs['cutoff'][0][1] > 0 and arcs['ring']['angle_start'] != arcs['ring']['angle_end']
    smoke = decay(arcs | {'delay': 5, 'emissive': 2}, (110, 100, 120, 170), lag=6, stretch=2)
    assert smoke['blend'] == 'Blend' and smoke['delay'] == 11 and smoke['life'] == [28, 44] and 'emissive' not in smoke
    assert smoke['ring']['center_color'] == [110, 100, 120, 170] and smoke['alpha_scroll'][0] == arcs['alpha_scroll'][0] * .4
    line = slice_line('l', (255, 255, 255, 255), 10, width=.08)
    assert line['scale_end'][0] / line['scale_end'][1] > 40
    thrown = spray([[1, 3], [0, 2], [-1, 1]])
    assert thrown['spawn']['rotate'] is False and thrown['travel']['end'][0] == [1, 3]
    rocks = debris('d', 6, [[1, 3], [0, 2], [-1, 1]], floor=.02)
    assert rocks['blend'] == 'Blend' and rocks['collide']['height'] == .02
    # A random size with a size curve crashes the compiler, so lint stops it first.
    bad = {'id': 'VFX_T', 'category': 'element', 'element': 'fire', 'duration': 1, 'peak': .1,
           'layers': [{'name': 'g', 'texture': 'T_Glow01', 'size': [.5, 1], 'size_curve': [[0, 1], [100, 0]]}]}
    assert any('fixed size' in e for e in lint(bad, (set(), {'T_Glow01'}))['errors'])
    bad['layers'] = [{'name': 'f', 'texture': 'T_Glow01', 'flipbook': {'x': 4, 'y': 4}, 'distortion_texture': 'T_Glow01'}]
    assert any('neighbouring cells' in e for e in lint(bad, (set(), {'T_Glow01'}))['errors'])


def test_lifetime_and_budget_follow_children_and_random_life():
    from vfxkit.primitives import lifetime, budget
    layer = {'delay': 5, 'count': 4, 'interval': 2, 'life': [10, 20], 'children': [{'count': 3, 'life': 8, 'delay': 1}]}
    # The last parent is born at 11 and lives 20; its child starts 1 frame after the parent is created and lives 8.
    assert lifetime(layer) == 5 + 3 * 2 + 20
    assert lifetime({'life': 10, 'children': [{'delay': 6, 'life': 12}]}) == 18
    assert budget(layer) == 4 * (1 + 3)


def test_procedural_noise_is_tileable_and_distortion_maps_are_opaque(tmp_path):
    import numpy as np
    from vfxkit.textures import spectral, masks, procedural
    field = spectral(64, 1.7, seed=1)
    assert field.min() >= 0 and field.max() <= 1
    # Seamless: the wrap-around step is no larger than the steps inside the image.
    assert np.abs(field[:, 0] - field[:, -1]).mean() <= np.abs(np.diff(field, axis=1)).mean() * 1.5
    generated = masks(64)
    assert all(m.shape == (64, 64) for m in generated.values())
    assert generated['T_GradientV01'][-8].mean() > generated['T_GradientV01'][8].mean()
    names = procedural(32, root=tmp_path)
    for name in ('T_Distort01', 'T_Distort02'):
        with Image.open(tmp_path / f'vfx/textures/processed/{name}.png') as image:
            assert np.asarray(image.convert('RGBA'))[..., 3].min() == 255, name
    assert {p.stem for p in (tmp_path / 'vfx/textures/procedural').glob('*.png')} == set(names)


def test_scaffold_creates_workspace_and_preserves_existing_data(tmp_path):
    from vfxkit.scaffold import initialize
    from vfxkit.paths import ROOT
    result = initialize(tmp_path, install_plugin=False)
    assert result['ok'] and not result['plugin_installed']
    manifest = tmp_path / 'vfx/vfx_manifest.json'
    assert json.loads(manifest.read_text()) == []
    assert (tmp_path / 'vfx/godot/scripts/Vfx.gd').is_file()
    assert (tmp_path / 'vfx/materials/M_Additive.vfxmat.json').is_file()
    assert (tmp_path / 'vfx/.gitignore').is_file() and (tmp_path / 'vfx/src').is_dir() and (tmp_path / 'vfx/briefs').is_dir()
    # Math primitives land in the workspace being initialised, not in whichever project the process started in.
    assert (tmp_path / 'vfx/textures/processed/T_Glow01.png').is_file()
    assert tmp_path.resolve() != ROOT
    manifest.write_text('[{"id":"preserved"}]')
    script = tmp_path / 'vfx/godot/scripts/Vfx.gd'
    script.write_text('preserve custom source')
    initialize(tmp_path, install_plugin=False)
    assert json.loads(manifest.read_text())[0]['id'] == 'preserved'
    assert script.read_text() == 'preserve custom source'
    initialize(tmp_path, install_plugin=False, update_templates=True)
    assert script.read_bytes() == (ASSETS / 'godot-lab/scripts/Vfx.gd').read_bytes()


def test_scaffold_syncs_character_models(tmp_path):
    from vfxkit.scaffold import initialize
    models = tmp_path / 'vfx/characters'
    models.mkdir(parents=True)
    (models / 'player.glb').write_bytes(b'glTF v1')
    (models / 'player.materials.json').write_text('{"default": "cloth"}')
    initialize(tmp_path, install_plugin=False)
    copy = tmp_path / 'vfx/godot/characters/player.glb'
    assert copy.read_bytes() == b'glTF v1'
    assert (tmp_path / 'vfx/godot/characters/player.materials.json').is_file()
    # A re-exported model replaces the Godot copy even without --update-templates.
    (models / 'player.glb').write_bytes(b'glTF v2')
    initialize(tmp_path, install_plugin=False)
    assert copy.read_bytes() == b'glTF v2'
