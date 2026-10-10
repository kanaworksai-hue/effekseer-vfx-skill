"""Pixel observations grouped by texture role; stylistic warnings are not build failures."""
from pathlib import Path
import io
import math
import numpy as np
from PIL import Image, ImageDraw
from . import workflow

ROLES = ('shape', 'light', 'symbol', 'trail', 'flipbook', 'uv_distortion', 'screen_distortion')


def content(image):
    rgba = np.asarray(image.convert('RGBA'))
    return rgba[..., 3] / 255 if rgba[..., 3].min() < 255 else rgba[..., :3].mean(axis=2) / 255


def cell_report(image):
    a = content(image)
    mask = a > 8/255
    y, x = np.where(mask)
    weight = a.sum()
    return {'coverage': round(float(mask.mean()), 4),
            'bbox': [int(x.min()), int(y.min()), int(x.max())+1, int(y.max())+1] if len(x) else None,
            'centroid': [round(float((a*np.indices(a.shape)[1]).sum()/weight/image.width), 4),
                         round(float((a*np.indices(a.shape)[0]).sum()/weight/image.height), 4)] if weight else None,
            'touches_border': bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any()),
            'small_coverage': {str(n): round(float((content(image.resize((n, n), Image.Resampling.LANCZOS)) > .1).mean()), 4) for n in (64, 32)}}


@workflow.locked
def audit(name, role='shape', grid=None, loop=False, allow_empty=None):
    if role not in ROLES:
        raise ValueError(f'role must be one of {ROLES}')
    if not isinstance(name, str) or not name or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_' for c in name):
        raise ValueError('name must be a texture stem')
    path = workflow.ROOT / f'vfx/textures/processed/{name}.png'
    if not path.is_file():
        raise FileNotFoundError(f'vfx/textures/processed/{name}.png is missing')
    errors, warnings = [], []
    with Image.open(path) as original:
        image = original.convert('RGBA')
    result = {'name': name, 'role': role, 'size': list(image.size), 'sha256': workflow.file_hash(path)}
    if grid is not None or role == 'flipbook':
        grid = grid or [4, 4]
        if len(grid) != 2 or any(type(n) is not int or not 1 <= n <= 16 for n in grid):
            raise ValueError('grid must contain two integers 1..16')
        x, y = grid
        if image.width % x or image.height % y:
            errors.append('image dimensions are not divisible by grid')
        else:
            allow_empty = allow_empty or []
            if any(type(i) is not int or not 0 <= i < x*y for i in allow_empty):
                raise ValueError('allow_empty indices must be within the grid')
            cells = [image.crop((i % x * image.width//x, i//x * image.height//y,
                                 (i % x+1)*image.width//x, (i//x+1)*image.height//y)) for i in range(x*y)]
            reports = [cell_report(c) for c in cells]
            empty = [i for i, r in enumerate(reports) if r['coverage'] == 0]
            unexpected = sorted(set(empty)-set(allow_empty))
            if unexpected:
                warnings.append(f'Empty cells (may be intentional anticipation/exit): {unexpected}')
            clipped = [i for i, r in enumerate(reports) if r['touches_border']]
            if clipped:
                warnings.append(f'Cells touching a boundary: {clipped}')
            deltas = [round(float(np.abs(content(a)-content(b)).mean()), 4) for a, b in zip(cells, cells[1:])]
            held = [i+1 for i, d in enumerate(deltas) if d < .002]
            if held:
                warnings.append(f'Possible hold/repeated cells: {held}; confirm timing intent')
            if loop and float(np.abs(content(cells[0])-content(cells[-1])).mean()) > .15:
                warnings.append('Loop end differs substantially from start')
            result.update(grid=grid, cells=reports, empty_cells=empty, frame_change=deltas)
    else:
        result.update(cell_report(image))
        if result['touches_border'] and role not in ('trail', 'uv_distortion', 'screen_distortion'):
            warnings.append('Content touches image border; inspect clipping or intended crop')
        if role in ('shape', 'symbol') and result['coverage'] > 0 and result['small_coverage']['32'] < .005:
            warnings.append('Very little content survives at 32px; inspect game distance')
        if role == 'uv_distortion':
            rgba = np.asarray(image)
            if rgba[..., 3].min() != 255:
                errors.append('UV distortion requires opaque RG offsets')
            result['rg_mean'] = [round(float(rgba[..., i].mean()/255), 4) for i in (0, 1)]
    # A labelled preview at original scale plus checkerboard and small-size inspections.
    display = image.copy()
    if max(display.size) > 1024:
        display.thumbnail((1024, 1024))
    canvas = Image.new('RGB', (display.width+180, max(display.height, 432)+32), '#17202c')
    draw = ImageDraw.Draw(canvas)
    for y in range(32, canvas.height, 16):
        for x in range(display.width):
            if x % 16 == 0:
                draw.rectangle((x, y, x+15, y+15), fill='#4a5360' if ((x//16+y//16)%2) else '#303944')
    canvas.paste(display, (0, 32), display)
    draw.text((8, 8), name+'  '+role, fill='white')
    for i, n in enumerate((128, 64, 32)):
        small = image.resize((n, n), Image.Resampling.LANCZOS)
        canvas.paste(small, (display.width+12, 32+i*144), small)
        draw.text((display.width+12, 16+i*144), f'{n}px', fill='white')
    preview = workflow.WORK / f'textures/{name}_{role}.png'
    preview.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(preview)
    return {'ok': not errors, 'errors': errors, 'warnings': warnings, 'measurements': result,
            'preview': workflow.relative(preview), 'manual_checks': ['silhouette', 'distance', 'role/style fit', 'temporal intent']}
