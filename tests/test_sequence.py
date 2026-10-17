"""Sequences (combos), the blockout gate, screen feedback and the stylized hard-edge pack."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from conftest import ASSETS, cli_env


def vfx(*args, cwd=None):
    run = subprocess.run([sys.executable, '-m', 'vfxkit', *args], capture_output=True, text=True, cwd=cwd, env=cli_env(), timeout=300)
    lines = run.stdout.strip().splitlines()
    assert len(lines) == 1, (run.stdout, run.stderr)
    return run.returncode, json.loads(lines[0])


SHOT = """from vfxkit.primitives import *
def recipe():
 return effect('{name}','{name}','hit','star',.4,[flash('Contact',WHITE,1.0,life=4,delay=1),
  sprite('Body','{texture}',(255,60,160,255),life=12,size=1,cutoff=DISSOLVE,alpha_texture='T_NoiseTile01')],
  peak=.03,impact=.3,delivery=MELEE{extra})
"""


def workspace(tmp_path, stage='blockout', texture='T_Glow01', screen=None):
    code, result = vfx('--project', str(tmp_path), 'init', '--no-plugin')
    assert code == 0, result
    extra = f", stage='{stage}'" + (f', screen={screen!r}' if screen is not None else '')
    for name in ('Shot_A', 'Finisher_A'):
        (tmp_path / f'vfx/src/VFX_{name}.py').write_text(SHOT.format(name=name, texture=texture, extra=extra))
    seq = {'schema_version': 1, 'sequence_id': 'SEQ_Test', 'stage': stage,
           'theme': 'Magenta star fire with hard edges throughout', 'animation': 'two beats',
           'steps': [{'t': 0.1, 'effect': 'VFX_Shot_A'}, {'t': 0.8, 'effect': 'VFX_Finisher_A'}],
           'references': [], 'concept': None, 'cut': [{'idea': 'meteor', 'why': 'off theme'}]}
    (tmp_path / 'vfx/sequences').mkdir()
    (tmp_path / 'vfx/sequences/SEQ_Test.json').write_text(json.dumps(seq))
    return tmp_path


def test_blockout_lint_holds_recipes_to_math_textures(tmp_path):
    root = workspace(tmp_path, texture='T_SmokeSheet01')
    code, result = vfx('--project', str(root), 'lint', '--ids', 'VFX_Shot_A')
    assert code == 1 and any('painted texture' in e for e in result['errors']['VFX_Shot_A'])
    root2 = workspace(tmp_path / 'b')
    code, result = vfx('--project', str(root2), 'lint', '--ids', 'VFX_Shot_A')
    assert code == 0 and not result['errors']


def test_screen_feedback_is_validated(tmp_path):
    root = workspace(tmp_path, screen={'shake': 2, 'flash_frames': 12, 'flash': 'rainbow', 'zoom': 1})
    code, result = vfx('--project', str(root), 'lint', '--ids', 'VFX_Shot_A')
    errors = ' '.join(result['errors']['VFX_Shot_A'])
    assert code == 1 and 'screen.shake' in errors and 'flash_frames' in errors and 'screen.flash' in errors and 'screen.zoom' in errors
    root2 = workspace(tmp_path / 'b', screen={'shake': .6, 'flash_frames': 2, 'flash': 'invert', 'hitstop': .08})
    code, result = vfx('--project', str(root2), 'lint', '--ids', 'VFX_Shot_A')
    assert code == 0


def test_detail_needs_the_blockout_gate_and_steal_lists(tmp_path):
    root = workspace(tmp_path, stage='detail')
    code, result = vfx('--project', str(root), 'sequence-validate', 'SEQ_Test')
    assert code == 1
    joined = ' '.join(result['errors'])
    assert 'blockout gate' in joined and 'steal list' in joined
    seq = json.loads((root / 'vfx/sequences/SEQ_Test.json').read_text())
    seq['references'] = [{'source': 'a board', 'steal': ['speed lines inside the beam']}]
    (root / 'vfx/sequences/SEQ_Test.json').write_text(json.dumps(seq))
    (root / 'vfx/sequences/SEQ_Test.gate.json').write_text(json.dumps({'verdict': 'ship'}))
    code, result = vfx('--project', str(root), 'sequence-validate', 'SEQ_Test')
    assert code == 0, result
    seq['stage'] = 'polish'
    (root / 'vfx/sequences/SEQ_Test.json').write_text(json.dumps(seq))
    code, result = vfx('--project', str(root), 'sequence-validate', 'SEQ_Test')
    assert code == 1 and any('concept' in e for e in result['errors'])


def test_a_blockout_sequence_needs_blockout_effects(tmp_path):
    root = workspace(tmp_path, stage='detail')
    seq = json.loads((root / 'vfx/sequences/SEQ_Test.json').read_text())
    seq['stage'] = 'blockout'
    (root / 'vfx/sequences/SEQ_Test.json').write_text(json.dumps(seq))
    code, result = vfx('--project', str(root), 'sequence-validate', 'SEQ_Test')
    assert code == 1 and any("stage='blockout'" in e for e in result['errors'])


def test_game_frames_become_evidence_and_a_blockout_ship_opens_the_gate(tmp_path):
    root = workspace(tmp_path)
    frames = tmp_path / 'game_frames'
    frames.mkdir()
    for f in range(0, 80, 4):
        Image.new('RGB', (320, 180), (20 + f, 30, 40)).save(frames / f'SEQ_Test_f{f:03d}.png')
    code, result = vfx('--project', str(root), 'sequence-review', 'SEQ_Test', '--frames', str(frames))
    assert code == 0 and result['source'] == 'game' and Path(result['strip']).is_file()
    code, handoff = vfx('--project', str(root), 'sequence-handoff', 'SEQ_Test')
    assert code == 0
    prompt = Path(handoff['prompt_file']).read_text(encoding='utf-8')
    assert 'blockout' in prompt and 'coherence' in prompt and 'layering' not in prompt.split('## Output')[1]
    report = {'id': 'SEQ_Test', 'stage': 'blockout', 'scores': {k: 2 for k in ('read', 'timing', 'scale', 'placement', 'coherence')},
              'worst': 'read', 'cut': '', 'fix': 'one change', 'verdict': 'ship', 'observed_frames': ['4', 8]}
    path = tmp_path / 'report.json'
    path.write_text(json.dumps(report))
    code, result = vfx('--project', str(root), 'sequence-submit', handoff['evidence_id'], str(path), '--reviewer', 'author')
    assert code == 1
    code, result = vfx('--project', str(root), 'sequence-submit', handoff['evidence_id'], str(path), '--reviewer', 'reviewer-1')
    assert code == 0 and result['verdict'] == 'ship' and (root / 'vfx/sequences/SEQ_Test.gate.json').is_file()
    code, paint = vfx('--project', str(root), 'paintover', 'SEQ_Test', '--frame', '40')
    assert code == 0 and Path(paint['source_image']).is_file() and 'Theme:' in paint['prompt']
    # No style in the brief: the concept keeps the screenshot's look instead of being forced into a toon style.
    assert 'hard-edged' not in paint['prompt'] and 'same visual style as the screenshot' in paint['prompt']
    seq = json.loads((root / 'vfx/sequences/SEQ_Test.json').read_text())
    seq['style'] = 'photoreal fire and smoke'
    (root / 'vfx/sequences/SEQ_Test.json').write_text(json.dumps(seq))
    code, paint = vfx('--project', str(root), 'paintover', 'SEQ_Test', '--frame', '40')
    assert code == 0 and 'photoreal fire and smoke' in paint['prompt']


def test_new_masks_tile_and_helix_wraps_a_strip():
    from vfxkit.textures import masks, helix
    m = masks(128)
    for name in ('T_SwirlNoise01', 'T_SpeedStreak01'):
        a = m[name]
        # Across the wrap the change is no bigger than between ordinary neighbours (texture-info's seam ratio).
        inner = (np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean()) / 2
        seam = (np.abs(a[:, 0] - a[:, -1]).mean() + np.abs(a[0] - a[-1]).mean()) / 2
        assert seam / inner < 1.6, (name, seam / inner)
    band = m['T_FlameBand01']
    assert band[-6].mean() > .5 and band[2].mean() < .2      # solid base at the bottom, tips at the top
    strip = Image.new('L', (256, 64), 0)
    strip.paste(255, (0, 24, 256, 40))
    out = helix(strip, size=64, turns=1, bands=2)
    assert out.shape == (64, 64) and .1 < out.mean() < .5
    assert abs(out[:, 0] - out[:, -1]).mean() < .3            # continues across the U seam


def test_stylized_primitives_compile_to_known_fields():
    from effekseer_ai.authoring import validate_layer
    from vfxkit import primitives as p
    layers = [p.spiral_ribbons('R', (200, 20, 110, 255), 1.5, 8, 40), p.spike_crown('S', p.INK, 1.2, 1.5, 40),
              p.speed_streaks('L', p.WHITE, 1.0, 10, 30), p.sparkle('Star', p.WHITE, .5, count=3, spread=1),
              *p.stylized_pair(p.sprite('Burst', 'T_Impact01', (255, 60, 160, 255), life=10, size=1.0), erode=(.2, .9))]
    for layer in layers:
        assert not validate_layer(layer), (layer['name'], validate_layer(layer))
    ink, bright = layers[-2:]
    assert ink['blend'] == 'Blend' and ink['size'] > bright['size'] and ink['cutoff'] == bright['cutoff']
    entry = p.effect('X', 'X', 'element', 'star', 1, [], screen=dict(shake=.5), stage='detail')
    assert entry['screen'] == {'shake': .5} and entry['stage'] == 'detail'


def test_lab_and_runtime_play_sequences_and_screen_feedback():
    lab = (ASSETS / 'godot-lab/scripts/VfxLab.gd').read_text(encoding='utf-8')
    api = (ASSETS / 'godot-lab/scripts/Vfx.gd').read_text(encoding='utf-8')
    handle = (ASSETS / 'godot-lab/scripts/VfxHandle.gd').read_text(encoding='utf-8')
    assert '--sequence=' in lab and 'stage_offset' in lab and 'func _screen(' in lab and 'hint_screen_texture' in lab
    assert 'signal screen_cue' in api and 'handle.cue(' in api
    assert 'signal screen_cue' in handle and 'func cue(' in handle
    rubric = json.loads((ASSETS / 'sequence_rubric.json').read_text(encoding='utf-8'))
    blockout = [c['id'] for c in rubric['criteria'] if 'blockout' in c['stages']]
    assert blockout == ['read', 'timing', 'scale', 'placement', 'coherence']
