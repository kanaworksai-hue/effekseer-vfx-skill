"""Unity pipeline: the same flipbooks, played by a small URP runtime instead of Effekseer.

  install  copy the com.vfx-skill.flipbook package into <UnityProject>/Packages/ and write the procedural textures it
           needs (flash, smoke, drops, flow noise, ground decal and the distance masks the mesh shells erode) into
           Assets/VfxSkill/Generated/Textures. Everything is drawn from math here: nothing painted ships with the skill.
  export   copy a processed sheet into Assets/VfxSkill/Flipbooks/ with a .flipbook.json sidecar (grid, cell size,
           source) so the import rules and the "Create element skill" window read its grid without guessing.

In Unity: VFX Skill -> 1. Setup shared materials -> 2. Create element skill from flipbooks -> 3. Build demo scene.
"""
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from .ownership import guard
from .paths import ASSETS

PACKAGE = ASSETS / 'unity/com.vfx-skill.flipbook'
TEXTURES = 'Assets/VfxSkill/Generated/Textures'
FLIPBOOKS = 'Assets/VfxSkill/Flipbooks'


def _project(path):
    root = Path(path).expanduser().resolve()
    if not (root / 'Assets').is_dir() or not (root / 'ProjectSettings').is_dir():
        raise ValueError(f'{root} is not a Unity project (expected Assets/ and ProjectSettings/)')
    return root


# ------------------------------------------------------------------ procedural textures
def _save(path, rgb, alpha, root):
    rgb = np.clip(np.broadcast_to(rgb, alpha.shape + (3,)) if np.ndim(rgb) < 3 else rgb, 0, 1)
    img = np.dstack([rgb, np.clip(alpha, 0, 1)])
    guard(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(path)
    return path.name


def _mask(path, m, root):
    """Greyscale distance mask in alpha (imported as linear data)."""
    return _save(path, np.ones(3), np.asarray(m, dtype=np.float64), root)


def _inner_gradient(binary, radius, power=0.7):
    """Binary shape -> interior gradient (an approximate distance field). A higher power keeps less area near 1, so
    the shell's white core is smaller and erosion thins the shape gradually instead of dropping it all at once."""
    b = np.asarray(Image.fromarray((binary * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(float(radius)))) / 255.0
    g = np.clip((b - 0.5) * 2, 0, 1) * binary
    return np.clip(g / max(g.max(), 1e-6), 0, 1) ** power


def _periodic(w, k, rng):
    x = np.linspace(0, 2 * np.pi, w, endpoint=False)
    n = sum(rng.uniform(0.3, 1) / f * np.sin(f * x + rng.uniform(0, 6.28)) for f in range(1, k + 1))
    return n / np.abs(n).max()


def _tile_noise(n, octaves, rng, base=4):
    """Tileable value noise in 0-1: random lattices sampled with wrap-around, smoothly interpolated."""
    out, amp, total = np.zeros((n, n)), 1.0, 0.0
    for o in range(octaves):
        cells = base * 2 ** o
        lat = rng.random((cells, cells))
        t = np.arange(n) * cells / n
        i0 = t.astype(int) % cells; i1 = (i0 + 1) % cells
        f = t - np.floor(t); f = f * f * (3 - 2 * f)
        a = lat[i0][:, i0] * (1 - f)[None, :] + lat[i0][:, i1] * f[None, :]
        b = lat[i1][:, i0] * (1 - f)[None, :] + lat[i1][:, i1] * f[None, :]
        out += amp * (a * (1 - f)[:, None] + b * f[:, None]); total += amp; amp *= 0.5
    return out / total


def _polar(n):
    yy, xx = np.mgrid[0:n, 0:n]
    dx, dy = (xx - n / 2 + 0.5) / (n / 2), (yy - n / 2 + 0.5) / (n / 2)
    return np.hypot(dx, dy), np.arctan2(dy, dx)


def _blob(n, rng, lobes=7, rough=0.12, base=0.62):
    """A soft-edged irregular puff: radius wobbles with angle, edge noise breaks the outline."""
    r, th = _polar(n)
    reach = base + sum(rng.uniform(0.02, 0.07) * np.sin(k * th + rng.uniform(0, 6.28)) for k in range(2, lobes))
    edge = (_tile_noise(n, 4, rng, 6) - 0.5) * rough
    return np.clip((reach + edge - r) / 0.06, 0, 1)


def _sheet(cells, cols):
    n = cells[0].shape[0]; rows = (len(cells) + cols - 1) // cols
    out = np.zeros((rows * n, cols * n) + cells[0].shape[2:])
    for i, c in enumerate(cells):
        out[(i // cols) * n:(i // cols + 1) * n, (i % cols) * n:(i % cols + 1) * n] = c
    return out


def textures(project, seed=7):
    """Write every texture the package's shared materials and mesh shells sample. Deterministic for a seed."""
    root = _project(project)
    out = root / TEXTURES
    rng = np.random.default_rng(seed)
    written = []

    r, th = _polar(256)                                          # contact flash: hot centre, fast falloff, 6 faint rays
    rays = 0.25 * np.abs(np.cos(th * 3)) ** 8 * np.clip(1 - r, 0, 1)
    written.append(_save(out / 'T_Flash.png', np.ones(3), np.clip(1 - r, 0, 1) ** 2.4 + rays, root))

    cells = []                                                   # smoke 2x2: neutral puffs, coloured by particle colour
    for _ in range(4):
        a = _blob(256, rng, rough=0.22, base=0.6)
        shade = 0.72 + 0.28 * np.clip(1 - _polar(256)[0] * 0.9, 0, 1) * _tile_noise(256, 3, rng, 3)
        cells.append(np.dstack([shade, shade, shade, a * (0.55 + 0.45 * _tile_noise(256, 4, rng, 4))]))
    s = _sheet(cells, 2); written.append(_save(out / 'T_Smoke_2x2.png', s[..., :3], s[..., 3], root))

    cells = []                                                   # drops 2x2: round beads, dark-edged, one highlight
    for i in range(4):
        n = 128; r2, _ = _polar(n)
        a = _blob(n, rng, lobes=4, rough=0.05, base=0.5 + 0.08 * (i % 2))
        yy, xx = np.mgrid[0:n, 0:n]
        hl = np.hypot(xx - n * 0.38, yy - n * 0.36) < n * 0.09
        v = np.where(hl, 1.0, 0.62 + 0.38 * np.clip(1 - r2 * 1.4, 0, 1))
        cells.append(np.dstack([v, v, v, a]))
    s = _sheet(cells, 2); written.append(_save(out / 'T_Drop_2x2.png', s[..., :3], s[..., 3], root))

    noise = np.dstack([_tile_noise(256, 5, rng, 4) for _ in range(3)])   # flow noise: RGB, tileable, linear
    written.append(_save(out / 'T_FlowNoise.png', noise, np.ones((256, 256)), root))

    a = _blob(256, rng, lobes=11, rough=0.35, base=0.66)         # ground decal: splat with broken edge and drops round it
    for _ in range(14):
        cx, cy, rad = rng.uniform(20, 236), rng.uniform(20, 236), rng.uniform(3, 9)
        yy, xx = np.mgrid[0:256, 0:256]
        a = np.maximum(a, (np.hypot(xx - cx, yy - cy) < rad).astype(float))
    written.append(_save(out / 'T_Decal.png', np.ones(3), a * (0.7 + 0.3 * _tile_noise(256, 4, rng, 5)), root))

    # Distance masks for StylizedShell (core / body / dark rim by threshold, eroded over life).
    W, H = 512, 256                                              # crown: U-tileable splash wall with spikes, holes, drops
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - yy / (H - 1); u = xx / W; spikes = 7
    heights = rng.uniform(0.62, 0.95, spikes)
    hi = heights[(u * spikes).astype(int) % spikes]
    spike = 0.36 + (hi - 0.36) * np.clip(1 - np.abs((u * spikes) % 1.0 - 0.5) * 2.2, 0, 1) ** 1.6
    crown = (v < spike + _periodic(W, 9, rng)[xx] * 0.03).astype(float)
    for _ in range(10):
        cx, cy, rad = rng.uniform(0, W), rng.uniform(0.42, 0.62) * H, rng.uniform(7, 14)
        crown[np.hypot(((xx - cx + W / 2) % W) - W / 2, (H - 1 - yy) - cy) < rad] = 0
    for _ in range(16):
        i = rng.integers(0, spikes)
        cx, cy, rad = (i + 0.5 + rng.normal(0, 0.06)) / spikes * W, (heights[i] + rng.uniform(0.04, 0.12)) * H, rng.uniform(5, 10)
        crown[np.hypot(((xx - cx + W / 2) % W) - W / 2, (H - 1 - yy) - cy) < rad] = 1
    written.append(_mask(out / 'T_MaskCrown.png', _inner_gradient(np.roll(crown, W // 2, 1), 12, 1.25), root))

    W, H = 1024, 128                                             # ribbon: long band, pointed ends, two cracks, ragged edge
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = xx / (W - 1), yy / (H - 1)
    width = np.sin(np.pi * u) ** 0.8 * (0.40 + 0.05 * np.sin(u * 23)) * (1 + 0.12 * _periodic(W, 24, rng)[xx] * u)
    wob = 0.05 * np.sin(u * 17 + 1.2) + 0.03 * np.sin(u * 41)
    band = (np.abs(v - 0.5 - wob * np.sin(np.pi * u)) < width).astype(float)
    for c, w0 in ((0.38, 0.018), (0.6, 0.012)):
        band[(np.abs(v - c - 0.03 * np.sin(u * 13 + c * 9)) < w0 * (0.4 + u)) & (u > 0.25)] = 0
    written.append(_mask(out / 'T_MaskRibbon.png', _inner_gradient(band, 10, 1.5), root))

    v = np.linspace(0, 1, 32)[:, None] * np.ones((1, 256))      # bolt strip: cross-section, ridge 1 -> edges 0
    written.append(_mask(out / 'T_MaskBoltStrip.png', np.clip(1 - np.abs(v - 0.5) * 2, 0, 1) ** 1.3, root))

    r, th = _polar(256); spikes = 9                              # contact star: uneven many-pointed burst
    amp = rng.uniform(0.55, 1.0, spikes)
    k = (th / (2 * np.pi) * spikes) % 1.0
    reach = 0.3 + (amp[((th + np.pi) / (2 * np.pi) * spikes).astype(int) % spikes] - 0.3) * np.clip(1 - np.abs(k - 0.5) * 2, 0, 1) ** 1.1
    written.append(_mask(out / 'T_MaskHitStar.png', _inner_gradient((r < reach * 0.95).astype(float), 12, 1.3), root))

    ring = ((r > 0.7 + 0.03 * np.sin(th * 7)) & (r < 0.86 + 0.03 * np.sin(th * 5 + 1))).astype(float)   # impact ring with a gap
    ring[(np.sin(th * 2 + 0.7) > 0.94) & (r > 0.6)] = 0
    written.append(_mask(out / 'T_MaskRing.png', _inner_gradient(ring, 6, 1.0), root))
    return {'folder': str(out), 'textures': written}


# ------------------------------------------------------------------ commands
def install(project, force=False):
    """Copy the package into Packages/ (Unity picks embedded packages up without editing the manifest) and write the
    procedural textures (always rewritten: they are generated). An existing package copy is replaced only with force, so
    local edits are never lost silently."""
    root = _project(project)
    dest = root / 'Packages' / PACKAGE.name
    guard(dest, root)
    if dest.exists() and not force:
        state = 'kept (pass --force to replace it with the skill\'s version)'
    else:
        # Unity identifies scripts, shaders and assets by the GUIDs in the .meta files it generated: keep them, or every
        # scene and material that uses the package loses its scripts ("Missing script") and shaders (pink).
        metas = {m.relative_to(dest): m.read_bytes() for m in dest.rglob('*.meta')} if dest.exists() else {}
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(PACKAGE, dest, ignore=shutil.ignore_patterns('*.meta', '.DS_Store'))
        for rel, data in metas.items():
            if (dest / rel).with_suffix('').exists():
                guard(dest / rel, root).write_bytes(data)
        state = 'updated (asset GUIDs kept)' if metas else 'installed'
    tex = textures(root)
    version = json.loads((PACKAGE / 'package.json').read_text())['version']
    return {'ok': True, 'package': str(dest), 'version': version, 'package_state': state, **tex,
            'next': ['Open the project in Unity (6000.0+, URP).', 'VFX Skill -> 1. Setup shared materials',
                     f'vfx unity-export <sheet.png> {root}  for each flipbook', 'VFX Skill -> 2. Create element skill from flipbooks',
                     'VFX Skill -> 3. Build demo scene, then Play']}


def export(sheet, project, grid=None, name=None):
    """Copy one processed sheet into the Unity project with its grid sidecar."""
    root = _project(project)
    src = Path(sheet).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    if grid is None:                                 # video-flipbook / video-grade record every sheet's grid
        from .video import PROMPTS
        entries = json.loads(PROMPTS.read_text(encoding='utf-8')).get('prompts', []) if PROMPTS.is_file() else []
        entry = next((e for e in entries if e.get('id') == src.stem), {})
        grid = entry.get('grid') or entry.get('params', {}).get('grid')
    if not grid:
        raise ValueError('pass --grid COLS ROWS (no grid found for this sheet)')
    cols, rows = int(grid[0]), int(grid[1])
    w, h = Image.open(src).size
    if w % cols or h % rows:
        raise ValueError(f'{src.name} is {w}x{h}: not divisible into a {cols}x{rows} grid')
    if name and (Path(name).name != name or name in ('.', '..')):
        raise ValueError(f'--name must be a plain file name, not {name!r}')
    dest = root / FLIPBOOKS / f'{name or src.stem}.png'
    guard(dest, root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    side = dest.with_suffix('.flipbook.json')
    guard(side, root)
    inset = bottom_inset(src, cols, rows)
    side.write_text(json.dumps({'grid': [cols, rows], 'cell': [w // cols, h // rows], 'frames': cols * rows, 'bottom_inset': inset, 'source': src.name}, indent=2) + '\n', encoding='utf-8')
    return {'ok': True, 'sheet': str(dest), 'sidecar': str(side), 'grid': [cols, rows], 'cell': [w // cols, h // rows], 'bottom_inset': inset}


def bottom_inset(sheet, cols, rows, alpha=0.25):
    """How far the drawn shape stays above each cell's bottom edge (fraction of the cell height, gutter included), taken
    low across the cells that have content. A column played from its base sinks by this much so its root touches the
    ground instead of floating with a strip of dry floor below it."""
    a = np.asarray(Image.open(sheet).convert('RGBA'))[..., 3] / 255.0
    h, w = a.shape[0] // rows, a.shape[1] // cols
    gaps = []
    for r in range(rows):
        for c in range(cols):
            filled = np.nonzero((a[r * h:(r + 1) * h, c * w:(c + 1) * w] > alpha).any(axis=1))[0]
            if len(filled):
                gaps.append((h - 1 - filled[-1]) / h)
    return round(float(np.percentile(gaps, 10)), 4) if gaps else 0.0
