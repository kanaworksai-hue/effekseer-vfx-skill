"""Local reference clips, explicit time mapping and honest approximate pixel analysis."""
from pathlib import Path
import json
import math
import shutil
import subprocess
import numpy as np
from PIL import Image, ImageDraw
from . import workflow
from . import evidence


def checked_id(ident):
    if not isinstance(ident, str) or len(ident) != 24 or any(c not in '0123456789abcdef' for c in ident):
        raise ValueError('Invalid reference ID')
    return ident


def read(ident):
    record = json.loads((evidence.store() / f'references/{checked_id(ident)}/manifest.json').read_text())
    if record.get('files') and not workflow.unchanged(record['files']):
        raise ValueError('Stored reference images changed; import the source again after removing this reference cache')
    return record


def effect_time(media_time, start, slow):
    if not all(math.isfinite(v) for v in (media_time, start, slow)) or slow < 1:
        raise ValueError('Times must be finite and slow must be >= 1')
    return (media_time-start)/slow


def analyse(paths, times):
    arrays = []
    for p in paths:
        with Image.open(p) as image:
            arrays.append(np.asarray(image.convert('RGB').resize((160, 100)), dtype=np.float32))
    frames = np.stack(arrays)
    base = np.median(frames[:min(3, len(frames))], axis=0)
    change = np.max(np.abs(frames-base), axis=-1)
    area = (change > 32).mean(axis=(1, 2))
    energy = change.mean(axis=(1, 2))/255
    camera = bool(np.mean(area > .6) > .4)
    peak = int(energy.argmax())
    active = np.flatnonzero(energy > max(float(energy.max())*.15, .002))
    return {'approximate': True, 'camera_or_full_screen_change': camera,
            'onset': times[int(active[0])] if len(active) and not camera else None,
            'peak': times[peak] if len(active) and not camera else None,
            'end': times[int(active[-1])] if len(active) and not camera else None,
            'largest_area_share': round(float(area.max()), 4) if not camera else None,
            'timeline': [{'time': t, 'coverage': round(float(a), 4), 'change': round(float(e), 4)} for t, a, e in zip(times, area, energy)],
            'limitations': ['compression, bloom and background mix values', 'camera/cuts/full-screen changes invalidate area timing',
                            'no world-size, emissive or particle-count inference']}


def tiles(paths, labels, target, columns=4, width=400):
    if not paths or len(paths) != len(labels):
        raise ValueError('Each selected image needs a label')
    canvas = Image.new('RGB', (columns*width, math.ceil(len(paths)/columns)*280), '#17202c')
    draw = ImageDraw.Draw(canvas)
    for i, (path, label) in enumerate(zip(paths, labels)):
        with Image.open(path) as source:
            image = source.convert('RGB')
        image.thumbnail((width, 252))
        x, y = i%columns*width, i//columns*280
        canvas.paste(image, (x+(width-image.width)//2, y+28+(252-image.height)//2))
        draw.text((x+8, y+8), label, fill='white')
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)
    return workflow.relative(target)


@workflow.locked
def import_clip(source, start=0., end=None, slow=1., roi=None, source_url='', fps=12):
    path = Path(source).resolve()
    if not path.is_file():
        raise FileNotFoundError(source)
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise RuntimeError('ffmpeg and ffprobe are required')
    if not math.isfinite(start) or not math.isfinite(slow) or not 1 <= slow <= 32 or not 1 <= fps <= 30:
        raise ValueError('Finite start, slow 1..32 and fps 1..30 are required')
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)],
                           capture_output=True, text=True, check=True, timeout=30)
    duration = float(json.loads(probe.stdout)['format']['duration'])
    end = duration if end is None else end
    if not math.isfinite(end) or not 0 <= start < end <= duration+.001 or end-start > 30:
        raise ValueError('Selection must be within the clip and at most 30 media seconds')
    if roi is not None and (len(roi) != 4 or any(type(v) is not int or v < 0 for v in roi) or roi[2] == 0 or roi[3] == 0):
        raise ValueError('ROI must be [x,y,width,height] in pixels')
    settings = {'source_sha256': workflow.file_hash(path), 'start': start, 'end': end, 'slow': slow, 'roi': roi, 'fps': fps}
    ident = workflow.digest(settings)[:24]
    folder = evidence.store() / f'references/{ident}'
    folder.mkdir(parents=True, exist_ok=True)
    if (folder/'manifest.json').is_file():
        return read(ident)
    filters = f'fps={fps}'
    if roi is not None:
        filters += f',crop={roi[2]}:{roi[3]}:{roi[0]}:{roi[1]}'
    # Keep a bounded image size and original aspect ratio; cropping is explicitly recorded.
    filters += ",scale=w='min(1280,iw)':h=-2"
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(start), '-i', str(path), '-t', str(end-start),
                    '-vf', filters, '-frames:v', '900', str(folder/'f%04d.png')],
                   capture_output=True, text=True, check=True, timeout=120)
    paths = sorted(folder.glob('f*.png'))
    if not paths:
        raise RuntimeError('No reference frames decoded')
    times = [i/fps/slow for i in range(len(paths))]
    selected = sorted({round(i*(len(paths)-1)/min(11, len(paths)-1)) for i in range(min(12, len(paths)))}) if len(paths) > 1 else [0]
    overview = tiles([paths[i] for i in selected], [f'R f{i}  effect {times[i]:.3f}s' for i in selected], folder/'overview.png')
    record = {'ok': True, 'reference_id': ident, **settings, 'source_url': source_url,
              'duration_effect': (end-start)/slow, 'frames': [workflow.relative(p) for p in paths],
              'times': times, 'overview': overview, 'analysis': analyse(paths, times),
              'files': workflow.snapshot([*paths, workflow.ROOT/overview])}
    workflow.save_json(folder/'manifest.json', record)
    return record


@workflow.locked
def frames(ident, start, end, count=12):
    if not 1 <= count <= 16 or not math.isfinite(start) or not math.isfinite(end) or not 0 <= start <= end:
        raise ValueError('Need an ordered nonnegative span and count 1..16')
    record = read(ident)
    candidates = [i for i, t in enumerate(record['times']) if start <= t <= end]
    if not candidates:
        raise ValueError('No stored frames in this span')
    indices = sorted({candidates[round(i*(len(candidates)-1)/max(1, min(count, len(candidates))-1))]
                      for i in range(min(count, len(candidates)))})
    target = evidence.store()/f'references/{ident}/span_{workflow.digest([start,end,count])[:12]}.png'
    result = tiles([workflow.ROOT/record['frames'][i] for i in indices],
                   [f'R f{i} effect {record["times"][i]:.3f}s' for i in indices], target)
    return {'ok': True, 'image': result, 'times': [record['times'][i] for i in indices]}


@workflow.locked
def compare(ident, evidence_id, times, reference_times=None):
    record = read(ident)
    capture = evidence.read_capture(evidence_id)
    problems = evidence.capture_issues(capture)
    if problems:
        raise ValueError('Capture is stale: '+', '.join(problems))
    if not 1 <= len(times) <= 8 or any(not math.isfinite(t) or t < 0 for t in times):
        raise ValueError('Need 1..8 nonnegative effect times')
    rt = times if reference_times is None else reference_times
    if len(rt) != len(times) or any(not math.isfinite(t) or not 0 <= t <= record['duration_effect'] for t in rt):
        raise ValueError('Reference times must match times and stay within the selection')
    rendered = {int(Path(p).stem.rsplit('_f', 1)[1]):p for p in capture['frames'] if '_f' in Path(p).stem}
    paths, labels, pairs = [], [], []
    for t, rtime in zip(times, rt):
        target_frame = max(1, round(t*60))
        if target_frame not in rendered:
            raise ValueError(f'Frame {target_frame} was not captured; review with key_frames including this frame')
        index = min(range(len(record['times'])), key=lambda i:abs(record['times'][i]-rtime))
        paths += [workflow.ROOT/record['frames'][index], workflow.ROOT/rendered[target_frame]]
        labels += [f'R {record["times"][index]:.3f}s', f'S f{target_frame} {target_frame/60:.3f}s']
        pairs.append({'requested': t, 'rendered_frame': target_frame, 'reference_time': record['times'][index]})
    target = evidence.store()/f'references/{ident}/compare_{evidence_id}_{workflow.digest([times,rt])[:8]}.png'
    return {'ok': True, 'image': tiles(paths, labels, target, columns=2, width=640), 'pairs': pairs,
            'note': 'Compare proportions and rhythm; views retain their own aspect ratio and recorded crop.'}
