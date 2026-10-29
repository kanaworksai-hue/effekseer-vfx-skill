"""Video-model flipbooks: a generated clip on black becomes a straight-alpha sheet the engines play frame by frame.

An image model paints one frame; a video model (image-to-video with a first and a last frame) also paints the motion:
a water column that rises, holds and collapses, fire that turns to smoke. Those continuous changes of shape are what
layered primitives cannot draw. This module turns such a clip into a sheet and gives every sheet the same look:

  timeline   labelled frames of the clip, to pick the span that carries the effect
  flipbook   decode at a fixed rate, luminance key on black, one shared crop for every frame (no jitter), a noisy
             round or rounded-box mask per cell (never a square edge), a fully transparent gutter round every cell,
             and a hard failure if any cell border still has alpha
  grade      re-colour by density with one value ramp per element (dark rim → body → light → hot core), erode the
             haze that keying leaves behind, fade the last cells to zero, optionally cool the tail to smoke
  first_frame  put a generated element image on pure black at the size and place the clip should start from

Originals stay in vfx/videos/ and vfx/textures/generated/; sheets go to vfx/textures/processed/; contact sheets and
the parameters of every run go to vfx/work/video/ so a sheet can be rebuilt exactly.
"""
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .ownership import guard
from .paths import ROOT, WORK

REPORTS = WORK / 'video'
PROMPTS = ROOT / 'vfx/video_prompts.json'   # every video-made texture, with the clip, its prompt and the exact parameters
FPS = 24  # every clip is decoded at one rate: generated clips often have variable frame rates


# ------------------------------------------------------------------ helpers
def _ffmpeg():
    exe = shutil.which('ffmpeg')
    if not exe:
        raise RuntimeError('ffmpeg was not found on PATH; install it (brew install ffmpeg, winget install ffmpeg)')
    return exe


def _decode(video, folder, fps=FPS):
    video = Path(video).resolve()
    if not video.is_file():
        raise FileNotFoundError(video)
    subprocess.run([_ffmpeg(), '-loglevel', 'error', '-i', str(video), '-vf', f'fps={fps}', str(Path(folder) / 'f_%04d.png')], check=True)
    files = sorted(Path(folder).glob('f_*.png'))
    if not files:
        raise ValueError(f'{video} decoded to no frames')
    return files


def _png(path):
    """Append .png unless it is already there: names may contain dots (T_Hit.v2, T_Burst_1.5)."""
    return path if path.suffix.lower() == '.png' else path.with_name(path.name + '.png')


def _in_project(path, default):
    """A relative path that starts with vfx/ is project-relative; a bare name lands in `default`."""
    path = Path(path)
    if path.is_absolute():
        return path
    return ROOT / path if path.parts[:1] == ('vfx',) else ROOT / default / path


def _resolve_output(output):
    """Bare names land in vfx/textures/processed/; every write must stay inside the project."""
    return guard(_png(_in_project(output, 'vfx/textures/processed')), ROOT)


def _resolve_sheet(source):
    """A sheet given as a path, a project path (vfx/...) or the bare name of a processed texture."""
    path = Path(source)
    for candidate in (path, _png(path), _png(_in_project(path, 'vfx/textures/processed'))):
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f'no sheet {source} (looked in vfx/textures/processed/ too)')


def _portable(path):
    """Project-relative when inside the project, else the file name only: the record is meant for version control and
    must not carry user names or home folders."""
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name


def _report_dir():
    REPORTS.mkdir(parents=True, exist_ok=True)
    return guard(REPORTS / 'x', ROOT).parent


def record(texture_id, entry):
    """Upsert one texture's provenance into vfx/video_prompts.json (lint accepts textures recorded here)."""
    data = json.loads(PROMPTS.read_text(encoding='utf-8')) if PROMPTS.is_file() else {'note': 'Textures made from generated video clips: '
            'the clip, the prompt that made it and the parameters that rebuild the sheet exactly.', 'prompts': []}
    data['prompts'] = [p for p in data['prompts'] if p.get('id') != texture_id] + [{'id': texture_id, **entry}]
    guard(PROMPTS, ROOT).parent.mkdir(parents=True, exist_ok=True)
    PROMPTS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def _prompt_text(prompt=None, prompt_file=None):
    if prompt_file:
        return Path(prompt_file).read_text(encoding='utf-8').strip()
    return prompt


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _key(path, floor, gain, dehaze):
    """Black → alpha. The median of a thin border ring is the frame's haze; it is subtracted before keying, and
    colour is un-premultiplied so thin glows keep their hue instead of turning grey."""
    img = np.asarray(Image.open(path).convert('RGB'), np.float32) / 255
    h, w = img.shape[:2]
    b = max(2, int(min(h, w) * .06))
    ring = np.concatenate([img[:b].reshape(-1, 3), img[-b:].reshape(-1, 3), img[:, :b].reshape(-1, 3), img[:, -b:].reshape(-1, 3)])
    haze = np.median(ring, axis=0) * dehaze
    img = np.clip((img - haze) / np.maximum(1 - haze, 1e-3), 0, 1)
    al = np.clip((img.max(-1) - floor) / (1 - floor) * gain, 0, 1) ** .9
    rgb = np.clip(img * gain / np.maximum(al, 1e-3)[..., None], 0, 1) * (al[..., None] > .002)
    return np.dstack([rgb, al])


def _sheet(img, path, width=1024, bg=(95, 120, 150)):
    """The sheet over a mid blue-grey: keyed edges, haze and dark rims are all visible against it."""
    back = Image.new('RGBA', img.size, bg + (255,))
    back.alpha_composite(img)
    back.convert('RGB').resize((width, round(width * img.height / img.width))).save(path, quality=88)


def _parse_frames(spec, total):
    a, b, s = (int(v) for v in spec.split(':'))
    if s < 1 or a < 0 or b >= total or a > b:
        raise ValueError(f'--frames {spec}: need start:end:step inside 0..{total - 1}')
    return list(range(a, b + 1, s))


# ------------------------------------------------------------------ timeline
def timeline(video, step=2, columns=10):
    """Every `step`-th frame (24 fps numbering, the same numbers `flipbook` takes) in a labelled grid."""
    tmp = Path(tempfile.mkdtemp())
    try:
        files = _decode(video, tmp)
        picks = list(range(0, len(files), max(1, step)))
        first = Image.open(files[0])
        tw = 160; th = round(tw * first.height / first.width)
        rows = math.ceil(len(picks) / columns)
        grid = Image.new('RGB', (tw * columns, th * rows))
        draw = ImageDraw.Draw(grid)
        for k, i in enumerate(picks):
            x, y = (k % columns) * tw, (k // columns) * th
            grid.paste(Image.open(files[i]).convert('RGB').resize((tw, th)), (x, y))
            draw.rectangle((x, y, x + 34, y + 14), fill=(0, 0, 0)); draw.text((x + 3, y + 1), str(i), fill=(255, 230, 0))
        out = _report_dir() / f'{Path(video).stem}_timeline.jpg'
        grid.save(out, quality=88)
        return {'ok': True, 'video': _portable(video), 'frames': len(files), 'fps': FPS, 'size': [first.width, first.height],
                'timeline': str(out), 'note': 'pick the span that carries the effect; skip opening white flashes and frames that fill the whole picture'}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ flipbook
def flipbook(video, output, cols=8, rows=8, cell=256, cell_h=0, start=-1, end=-1, frames=None, crop='auto', box=None,
             pad=1.04, radius=.38, feather=.12, mask_power=2.0, floor=.06, gain=1.3, gutter=6, dehaze=1.0, prompt=None, prompt_file=None):
    """Decode → key → shared crop → masked cells with transparent gutters → one sheet (cols × rows cells of cell × cell_h).

    `frames` 'a:b:s' picks exact 24 fps frames (len must equal cols*rows); otherwise `start`..`end` (auto: the span with
    visible content) is sampled evenly. `crop` 'auto' takes the union bounding box of every picked frame (padded by `pad`)
    at the cell's aspect; `box` 'cx,cy,half_width' (pixels) sets it by hand when stray sparks inflate the union.
    `mask_power` 2 is a round mask, 3-5 a rounded box for tall or wide shapes that touch the cell's top and bottom."""
    out = _resolve_output(output)
    cell_h = cell_h or cell
    n = cols * rows
    if min(cols, rows) < 1 or cell < 32 or cell_h < 32 or gutter < 2:
        raise ValueError('need cols, rows ≥ 1, cells ≥ 32 px and a gutter of at least 2 px')
    if cols * cell > 4096 or rows * cell_h > 4096:
        raise ValueError(f'sheet {cols * cell}×{rows * cell_h} exceeds 4096 px; use smaller cells or fewer frames')
    tmp = Path(tempfile.mkdtemp())
    try:
        files = _decode(video, tmp)
        if frames:
            pick = _parse_frames(frames, len(files))
            if len(pick) != n:
                raise ValueError(f'--frames gives {len(pick)} frames, the sheet has {n} cells')
            s, e = pick[0], pick[-1]
        else:
            cover = np.array([float((np.asarray(Image.open(f).convert('L'), np.float32) / 255 > floor + .04).mean()) for f in files])
            active = np.where(cover > max(cover.max() * .02, 1e-4))[0]
            if start >= len(files) or end >= len(files):
                raise ValueError(f'--start/--end beyond the clip: it has {len(files)} frames at {FPS} fps (0..{len(files) - 1})')
            s = start if start >= 0 else int(active[0]) if len(active) else 0
            e = end if end >= 0 else int(active[-1]) if len(active) else len(files) - 1
            if e <= s:
                raise ValueError(f'empty span {s}..{e}')
            pick = [round(s + i * (e - s) / max(n - 1, 1)) for i in range(n)]
        keyed = [_key(files[i], floor, gain, dehaze) for i in pick]
        H, W = keyed[0].shape[:2]
        asp = cell_h / cell
        if box:
            cx, cy, hw = (float(v) for v in str(box).split(','))
        elif crop == 'auto':
            union = np.zeros((H, W), bool)
            for fr in keyed:
                union |= fr[..., 3] > .03
            ys, xs = np.where(union)
            if not len(xs):
                raise ValueError('no visible pixels in the picked span; lower --floor or check the clip')
            cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
            hw = max((xs.max() - xs.min()) / 2, (ys.max() - ys.min()) / 2 / asp) * pad
            hw = min(hw, W / 2, H / 2 / asp)
            cy = float(np.clip(cy, hw * asp, H - hw * asp)); cx = float(np.clip(cx, hw, W - hw))
        else:
            hw = min(W / 2, H / 2 / asp); cx, cy = W / 2, H / 2
        hh = hw * asp
        crop_box = (int(cx - hw), int(cy - hh), int(cx + hw), int(cy + hh))
        inner_w, inner_h = cell - 2 * gutter, cell_h - 2 * gutter
        wob = .04
        limit = .5 - 1.5 / min(inner_w, inner_h)          # the mask (noise and feather included) stays inside the cell
        clamped = radius + wob + feather / 2 > limit
        if clamped:
            radius = limit - wob - feather / 2
        yy = np.linspace(0, 1, inner_h)[:, None] * np.ones((1, inner_w)); xx = np.ones((inner_h, 1)) * np.linspace(0, 1, inner_w)[None, :]
        r = (np.abs(xx - .5) ** mask_power + np.abs(yy - .5) ** mask_power) ** (1 / mask_power)
        th = np.arctan2(yy - .5, xx - .5)
        sheet = Image.new('RGBA', (cell * cols, cell_h * rows))
        for k, fr in enumerate(keyed):
            im = Image.fromarray((fr * 255 + .5).astype(np.uint8)).crop(crop_box).resize((inner_w, inner_h), Image.Resampling.LANCZOS)
            arr = np.asarray(im, np.float32).copy()
            ph = k * .07                                    # the edge noise drifts slowly, so the border never reads as a fixed shape
            w = wob * (.47 * np.sin(5 * th + 1.3 + ph) + .33 * np.sin(9 * th + 4.1 - ph * 1.7) + .2 * np.sin(17 * th + .6 + ph * 2.3))
            m = np.clip((radius + w - r) / feather + .5, 0, 1)
            arr[..., 3] *= m * m * (3 - 2 * m)
            sheet.paste(Image.fromarray(arr.astype(np.uint8)), ((k % cols) * cell + gutter, (k // cols) * cell_h + gutter))
        alpha = np.asarray(sheet)[..., 3]
        bad = [k for k in range(n) if max(alpha[(k // cols) * cell_h:(k // cols) * cell_h + 2, (k % cols) * cell:(k % cols + 1) * cell].max(),
                                         alpha[(k // cols + 1) * cell_h - 2:(k // cols + 1) * cell_h, (k % cols) * cell:(k % cols + 1) * cell].max(),
                                         alpha[(k // cols) * cell_h:(k // cols + 1) * cell_h, (k % cols) * cell:(k % cols) * cell + 2].max(),
                                         alpha[(k // cols) * cell_h:(k // cols + 1) * cell_h, (k % cols + 1) * cell - 2:(k % cols + 1) * cell].max()) > 0]
        if bad:
            raise ValueError(f'cell borders are not transparent in cells {bad[:8]}: raise --gutter or lower --radius')
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out)
        rep = _report_dir()
        contact = rep / f'{out.stem}_sheet.jpg'
        _sheet(sheet, contact)
        info = {'ok': True, 'video': _portable(video), 'output': str(out), 'grid': [cols, rows], 'cell': [cell, cell_h],
                'sheet_size': [cell * cols, cell_h * rows], 'frames_total': len(files), 'fps': FPS, 'span': [s, e], 'picked': pick,
                'duration_s': round((e - s + 1) / FPS, 3), 'crop_box': list(crop_box), 'gutter': gutter, 'radius': round(radius, 3),
                'radius_clamped': bool(clamped), 'mask_power': mask_power, 'contact_sheet': str(contact),
                'params': {'floor': floor, 'gain': gain, 'pad': pad, 'feather': feather, 'dehaze': dehaze, 'box': box, 'crop': crop}}
        (rep / f'{out.stem}.json').write_text(json.dumps(info, indent=1))
        text = _prompt_text(prompt, prompt_file)
        record(out.stem, {'kind': 'video flipbook', 'video': info['video'], 'prompt': text, 'grid': [cols, rows], 'cell': [cell, cell_h],
                          'frames': pick, 'crop_box': list(crop_box), 'params': info['params'] | {'mask_power': mask_power, 'radius': info['radius'], 'gutter': gutter},
                          'source': 'video generation model (image-to-video, first frame + black last frame); keyed with vfx video-flipbook'})
        if not text:
            info['warning'] = 'no --prompt/--prompt-file: record the video prompt so the clip can be made again'
        return info
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ grade
def _ramp(spec):
    stops = []
    for part in spec.split(';'):
        k, c = part.split(':')
        rgb = [float(v) for v in c.split(',')]
        if len(rgb) != 3:
            raise ValueError(f'ramp stop {part!r}: need position:r,g,b')
        stops.append((float(k), np.array(rgb)))
    return sorted(stops, key=lambda x: x[0])


def _eval(stops, d):
    ks = [k for k, _ in stops]
    return np.stack([np.interp(d, ks, [c[i] for _, c in stops]) for i in range(3)], -1)


def grade(source, output, cols=8, rows=8, ramp=None, erode=.22, erode_pow=1.5, tail_fade=6, highlight=0.0, ramp_fade=None,
          smoke=None, smoke_start=.4, keep_embers=False, late_gamma=1.0, late_alpha=1.0, alpha_gamma=1.0, late_blur=0.0, body_mask=0.0,
          open_px=0, open_until=1.0, cut_below=None, cut_from=0.0):
    """Re-colour a keyed sheet cell by cell (t = cell / last cell).

    - `erode`/`erode_pow`: the alpha threshold rises over time, so thin haze goes first and the structure last;
      `tail_fade` brings the last cells linearly to zero (no pop when the particle dies).
    - `ramp` 'pos:r,g,b;...' maps density (alpha × luminance) to the element's value ramp; close stops give hard
      cel steps. `highlight` keeps white only on fine detail (spray, glints). `ramp_fade` 't0,t1' blends back to the
      clip's own colours later in the sheet (a clip's grey smoke and embers usually read better than a re-colour).
    - `smoke`/`smoke_start` cool the tail towards one smoke colour; `keep_embers` leaves saturated orange-red pixels of
      the clip alone. Dark smoke turns transparent in a luminance key: `late_gamma` < 1 thickens only the late cells
      (a whole-sheet `alpha_gamma` grows a dark halo round bright fire); `late_alpha` multiplies late alpha.
    - `late_blur` softens late cells into one mass; `body_mask` removes strands thinner than its blur radius (dripping
      sparks under a fireball) while bodies keep round edges; `open_px` is a morphological opening for the early cells;
      `cut_below` fades everything below a cell height (0 top .. 1 bottom) from `cut_from` on."""
    src = _resolve_sheet(source)
    out = _resolve_output(output)
    if src == out.resolve():
        raise ValueError('output cannot overwrite the source sheet')
    im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float64) / 255
    H, W = im.shape[0] // rows, im.shape[1] // cols
    if H * rows != im.shape[0] or W * cols != im.shape[1]:
        raise ValueError(f'{im.shape[1]}×{im.shape[0]} does not divide into {cols}×{rows} cells')
    stops = _ramp(ramp) if ramp else None
    smoke_rgb = np.array([float(v) for v in smoke.split(',')]) if smoke else None
    fade = [float(v) for v in ramp_fade.split(',')] if ramp_fade else None
    total = cols * rows
    res = im.copy()
    yy = np.linspace(0, 1, H)[:, None] * np.ones((1, W))
    for k in range(total):
        t = k / max(total - 1, 1)
        y, x = (k // cols) * H, (k % cols) * W
        c = im[y:y + H, x:x + W]
        rgb, al = c[..., :3], c[..., 3]
        f = .02 + erode * t ** erode_pow if total > 1 else 0.0
        a2 = np.clip((al - f) / (1 - f), 0, 1)
        if body_mask > 0:
            bm = np.asarray(Image.fromarray((a2 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(float(body_mask)))).astype(np.float64) / 255
            peak = max(np.percentile(bm, 99.5), 1e-3)
            a2 = a2 * _smoothstep(.22 * peak, .42 * peak, bm)
        if open_px > 0 and t <= open_until:
            size = open_px * 2 + 1
            o = Image.fromarray((a2 * 255).astype(np.uint8))
            a2 = np.minimum(a2, np.asarray(o.filter(ImageFilter.MinFilter(size)).filter(ImageFilter.MaxFilter(size))).astype(np.float64) / 255)
        if alpha_gamma != 1.0:
            a2 = a2 ** alpha_gamma
        if late_gamma != 1.0:
            a2 = a2 ** (1 + (late_gamma - 1) * _smoothstep(smoke_start, .7, t))
        if late_alpha != 1.0:
            a2 = np.clip(a2 * (1 + (late_alpha - 1) * _smoothstep(smoke_start, .8, t)), 0, 1)
        if cut_below is not None and t >= cut_from:
            a2 = a2 * (1 - _smoothstep(cut_below - .04, cut_below + .06, yy))
        if tail_fade > 0 and total > 1 and k >= total - tail_fade:
            a2 = a2 * (total - 1 - k) / tail_fade
        lum = rgb @ np.array([.3, .55, .15])
        if stops is not None:
            body = _eval(stops, np.clip(a2 * (.5 + .5 * lum), 0, 1))
            if highlight > 0:
                blur = np.asarray(Image.fromarray((lum * a2 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(np.float64) / 255
                hp = np.clip((lum * a2 - blur) * highlight, 0, 1)[..., None]
                body = body * (1 - hp) + stops[-1][1] * hp
            if fade:
                w = _smoothstep(fade[0], fade[1], t)
                body = body * (1 - w) + rgb * w
            rgb = body
        if smoke_rgb is not None:
            s = _smoothstep(smoke_start, .85, t)
            l2 = rgb @ np.array([.3, .55, .15])
            sm = np.full(a2.shape, .85 * s)
            if keep_embers:
                o = c[..., :3]
                sm = sm * (1 - np.clip((o[..., 0] - o[..., 2] - .3) * 3, 0, 1))
            rgb = rgb * (1 - sm[..., None]) + smoke_rgb * (.7 + .5 * l2[..., None]) * sm[..., None]
        if late_blur > 0:
            rad = float(late_blur * _smoothstep(smoke_start + .1, .85, t))   # newer Pillow rejects a numpy scalar radius
            if rad > .3:
                pm = np.dstack([np.clip(rgb, 0, 1) * a2[..., None], a2])
                b = np.asarray(Image.fromarray((pm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))).astype(np.float64) / 255
                a2 = np.clip(b[..., 3] * 1.15, 0, 1)
                rgb = b[..., :3] / np.maximum(b[..., 3:4], 1e-3)
        res[y:y + H, x:x + W, :3] = np.clip(rgb, 0, 1)
        res[y:y + H, x:x + W, 3] = a2
    for k in range(rows * cols):   # blur and dilation can reach the gutter: keep every cell border transparent, like the flipbook
        y, x = (k // cols) * H, (k % cols) * W
        for sl in ((slice(y, y + 2), slice(x, x + W)), (slice(y + H - 2, y + H), slice(x, x + W)), (slice(y, y + H), slice(x, x + 2)), (slice(y, y + H), slice(x + W - 2, x + W))):
            res[sl + (3,)] = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    final = Image.fromarray((res * 255 + .5).astype(np.uint8))
    final.save(out)
    contact = _report_dir() / f'{out.stem}_sheet.jpg'
    _sheet(final, contact, bg=(150, 190, 120))
    params = {'source': _portable(src), 'grid': [cols, rows], 'ramp': ramp, 'erode': erode, 'erode_pow': erode_pow, 'tail_fade': tail_fade,
              'highlight': highlight, 'ramp_fade': ramp_fade, 'smoke': smoke, 'smoke_start': smoke_start, 'keep_embers': keep_embers,
              'late_gamma': late_gamma, 'late_alpha': late_alpha, 'alpha_gamma': alpha_gamma, 'late_blur': late_blur, 'body_mask': body_mask,
              'open_px': open_px, 'open_until': open_until, 'cut_below': cut_below, 'cut_from': cut_from}
    (_report_dir() / f'{out.stem}.grade.json').write_text(json.dumps(params, indent=1))
    record(out.stem, {'kind': 'graded video flipbook', 'from': src.stem, 'params': params, 'source': 'vfx video-grade of ' + src.stem})
    return {'ok': True, 'output': str(out), 'contact_sheet': str(contact), 'grid': [cols, rows], 'cell': [W, H],
            'note': 'check the contact sheet: bodies keep colour on a bright background, the last cells are clean'}


# ------------------------------------------------------------------ first frame
def first_frame(source, output, width=1024, height=1024, fill=.35, anchor='center', floor=.04):
    """Crop a generated element image on black and place it on a pure black canvas of the clip's size.

    `fill` is the longest side of the element as a fraction of the canvas's shorter side: small, so the motion has room
    and never leaves the frame. `anchor` 'bottom' puts it near the bottom edge (an eruption that rises)."""
    src = Path(source).resolve()
    out = guard(_png(_in_project(output, 'vfx/videos/frames')), ROOT)
    img = np.asarray(Image.open(src).convert('RGB')).astype(np.float64) / 255
    ys, xs = np.where(img.max(-1) > floor + .04)
    if not len(ys):
        raise ValueError('no visible content above the black floor')
    crop = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    crop = np.where(crop.max(-1, keepdims=True) > floor, crop, 0)
    h, w = crop.shape[:2]
    s = fill * min(width, height) / max(h, w)
    el = Image.fromarray((crop * 255).astype(np.uint8)).resize((max(1, round(w * s)), max(1, round(h * s))), Image.Resampling.LANCZOS)
    canvas = Image.new('RGB', (width, height))
    x = (width - el.width) // 2
    y = (height - el.height) // 2 if anchor == 'center' else height - el.height - round(height * .08)
    canvas.paste(el, (x, y))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    last = out.with_name(f'black_{width}x{height}.png')
    if not last.exists():
        Image.new('RGB', (width, height)).save(guard(last, ROOT))
    return {'ok': True, 'first_frame': str(out), 'last_frame': str(last), 'size': [width, height], 'element_size': [el.width, el.height],
            'note': 'use first_frame as the first frame and the black image as the last frame of an image-to-video generation'}
