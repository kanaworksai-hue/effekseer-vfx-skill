"""Video-model flipbooks and the Unity pipeline, on a synthetic clip (a disc that grows and fades on black).

No video model, Effekseer Core or Unity is needed: ffmpeg encodes the clip, and the Unity commands write into a folder
that only has to look like a Unity project.
"""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from conftest import PROJECT, cli_env

requires_ffmpeg = pytest.mark.skipif(not shutil.which('ffmpeg'), reason='ffmpeg is not on PATH')


@pytest.fixture(scope='module')
def clip(tmp_path_factory):
    """48 frames at 24 fps: black, a warm disc grows to the middle of the clip, then shrinks and fades to black."""
    folder = tmp_path_factory.mktemp('clip')
    yy, xx = np.mgrid[0:256, 0:256]
    r = np.hypot(xx - 128, yy - 128)
    for i in range(48):
        t = i / 47
        size = 90 * np.sin(np.pi * t) ** 0.7
        a = np.clip((size - r) / 8, 0, 1) * (1 - max(0, t - 0.7) / 0.3)
        img = np.dstack([a * 255, a * 180, a * 60]).astype(np.uint8)
        Image.fromarray(img).save(folder / f'f_{i:03d}.png')
    video = folder / 'disc.mp4'
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', '24', '-i', str(folder / 'f_%03d.png'),
                    '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-crf', '12', str(video)], check=True)
    return video


@requires_ffmpeg
def test_flipbook_makes_a_gutter_sheet_and_records_the_prompt(clip):
    from vfxkit import video
    info = video.flipbook(clip, 'T_TestDisc_4x4', cols=4, rows=4, cell=64, gutter=6, prompt='a warm disc grows and fades on black')
    sheet = np.asarray(Image.open(info['output']).convert('RGBA'))
    assert sheet.shape[:2] == (256, 256)
    alpha = sheet[..., 3]
    for k in range(4):   # every cell border is fully transparent
        assert alpha[k * 64, :].max() == 0 and alpha[:, k * 64].max() == 0
    assert alpha.max() > 200   # and the cells hold the disc
    entry = next(p for p in json.loads((PROJECT / 'vfx/video_prompts.json').read_text())['prompts'] if p['id'] == 'T_TestDisc_4x4')
    assert entry['grid'] == [4, 4] and 'warm disc' in entry['prompt']


@requires_ffmpeg
def test_grade_fades_the_tail_and_lint_accepts_recorded_sheets(clip):
    from vfxkit import video, lint
    video.flipbook(clip, 'T_TestDisc_4x4', cols=4, rows=4, cell=64)
    src = PROJECT / 'vfx/textures/processed/T_TestDisc_4x4.png'
    info = video.grade(src, 'T_TestDisc_4x4_graded', cols=4, rows=4, ramp='0:.4,.05,.03;.5:.95,.35,.06;1:1,.95,.75', tail_fade=4)
    graded = np.asarray(Image.open(info['output']).convert('RGBA'))
    assert graded.shape == np.asarray(Image.open(src).convert('RGBA')).shape
    assert graded[192:, 192:, 3].max() == 0   # the last cell is faded to nothing
    _, documented = lint.documented_textures()
    assert {'T_TestDisc_4x4', 'T_TestDisc_4x4_graded'} <= documented


def test_first_frame_puts_the_element_on_black_and_writes_a_black_last_frame(tmp_path):
    from vfxkit import video
    src = tmp_path / 'element.png'
    img = np.zeros((300, 300, 3), np.uint8); img[100:200, 120:180] = (40, 150, 255)
    Image.fromarray(img).save(src)
    info = video.first_frame(src, 'test_first.png', width=512, height=512, fill=.4)
    first = np.asarray(Image.open(info['first_frame']).convert('RGB'))
    assert first.shape == (512, 512, 3) and first[0, 0].max() == 0 and first.max() > 100
    assert np.asarray(Image.open(info['last_frame'])).max() == 0


def test_video_body_plays_every_cell_once_or_stands_as_a_column():
    from vfxkit.primitives import video_body
    burst = video_body('Body', 'T_Burst_8x8', grid=(8, 8), size=3, frame_length=2, delay=7)
    assert burst['life'] == 128 and burst['delay'] == 7 and burst['blend'] == 'Blend'
    assert burst['flipbook']['x'] == 8 and burst['flipbook']['loop'] == 'Once' and burst['billboard'] == 'Billboard'
    column = video_body('Column', 'T_Column_8x7', grid=(8, 7), size=4, column=.56, loop=True)
    assert column['billboard'] == 'YAxisFixed' and column['flipbook']['loop'] == 'Loop'
    assert column['scale_start'][:2] == pytest.approx([4 * .56, 4])


def fake_unity(tmp_path):
    root = tmp_path / 'Game'
    (root / 'Assets').mkdir(parents=True); (root / 'ProjectSettings').mkdir()
    return root


def test_unity_install_copies_the_package_and_draws_its_textures(tmp_path):
    from vfxkit import unity
    root = fake_unity(tmp_path)
    info = unity.install(root)
    package = root / 'Packages/com.vfx-skill.flipbook'
    assert json.loads((package / 'package.json').read_text())['name'] == 'com.vfx-skill.flipbook'
    assert (package / 'Runtime/ElementSkill.cs').is_file() and (package / 'Editor/CreateElementSkill.cs').is_file()
    textures = root / 'Assets/VfxSkill/Generated/Textures'
    for name in ('T_Flash', 'T_Smoke_2x2', 'T_Drop_2x2', 'T_FlowNoise', 'T_Decal', 'T_MaskCrown', 'T_MaskRibbon',
                 'T_MaskBoltStrip', 'T_MaskHitStar', 'T_MaskRing'):
        assert np.asarray(Image.open(textures / f'{name}.png'))[..., 3].max() > 0, name
    assert info['package_state'] == 'installed'
    (package / 'Runtime/Local.cs').write_text('// a local edit')
    assert unity.install(root)['package_state'].startswith('kept') and (package / 'Runtime/Local.cs').exists()
    unity.install(root, force=True)
    assert not (package / 'Runtime/Local.cs').exists()
    with pytest.raises(ValueError, match='not a Unity project'):
        unity.install(tmp_path)


def test_unity_export_writes_the_grid_sidecar_and_stays_inside_the_project(tmp_path):
    from vfxkit import unity
    root = fake_unity(tmp_path)
    sheet = tmp_path / 'T_Column_4x2.png'
    a = np.zeros((200, 160), np.uint8)
    for c in range(4):
        for r in range(2):
            a[r * 100 + 10:r * 100 + 80, c * 40 + 8:c * 40 + 32] = 255   # 20 empty rows under each shape
    Image.fromarray(np.dstack([a, a, a, a])).save(sheet)
    info = unity.export(sheet, root, grid=(4, 2), name='Column')
    side = json.loads((root / 'Assets/VfxSkill/Flipbooks/Column.flipbook.json').read_text())
    assert side['grid'] == [4, 2] and side['cell'] == [40, 100] and info['bottom_inset'] == pytest.approx(.2)
    with pytest.raises(ValueError, match='grid'):
        unity.export(sheet, root, grid=(3, 2))
    with pytest.raises(ValueError, match='plain file name'):
        unity.export(sheet, root, grid=(4, 2), name='../../../../escaped')


def test_unity_commands_need_no_workspace(tmp_path):
    root = fake_unity(tmp_path)
    run = subprocess.run([__import__('sys').executable, '-m', 'vfxkit', 'unity-install', str(root)], capture_output=True, text=True,
                         cwd=tmp_path, env=cli_env(VFX_PROJECT=''), timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(run.stdout)['ok'] and not (tmp_path / 'vfx').exists()


@requires_ffmpeg
def test_paths_names_and_bounds_from_review(clip):
    from vfxkit import video
    # a project path and a bare name land in the same file; names with dots keep their dots
    a = video.flipbook(clip, 'vfx/textures/processed/T_Path.v2', cols=2, rows=2, cell=64)
    assert Path(a['output']) == PROJECT / 'vfx/textures/processed/T_Path.v2.png'
    g = video.grade('T_Path.v2', 'T_Path.v2_graded', cols=2, rows=2, late_blur=5, tail_fade=0)
    alpha = np.asarray(Image.open(g['output']).convert('RGBA'))[..., 3]
    assert alpha[:2].max() == 0 and alpha[:, 62:66].max() == 0   # blur never reaches the cell borders
    entry = next(p for p in json.loads((PROJECT / 'vfx/video_prompts.json').read_text(encoding='utf-8'))['prompts'] if p['id'] == 'T_Path.v2_graded')
    assert entry['params']['source'] == 'vfx/textures/processed/T_Path.v2.png'   # never an absolute local path
    with pytest.raises(ValueError, match='beyond the clip'):
        video.flipbook(clip, 'T_Bad', cols=2, rows=2, cell=64, end=500)


def test_unity_force_keeps_meta_guids(tmp_path):
    from vfxkit import unity
    root = fake_unity(tmp_path)
    unity.install(root)
    meta = root / 'Packages/com.vfx-skill.flipbook/Runtime/ElementSkill.cs.meta'
    meta.write_text('fileFormatVersion: 2\nguid: 0123456789abcdef0123456789abcdef\n')
    assert 'GUIDs kept' in unity.install(root, force=True)['package_state']
    assert '0123456789abcdef' in meta.read_text()
