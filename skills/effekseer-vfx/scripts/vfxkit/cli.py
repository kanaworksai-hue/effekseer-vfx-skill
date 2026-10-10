"""effekseer-vfx command line: one JSON object on stdout per command; progress and warnings go to stderr.

Exit codes: 0 ok, 1 failed check or error (the JSON says which), 2 setup required (toolchain or vfx init).
Images (strips, comparisons, key frames, texture previews) are returned as file paths: open them and look.
"""
import argparse
import json
import os
import sys
from pathlib import Path

COMMANDS = """
setup and workspace:   doctor, init, examples, procedural
authoring (no Core):   list, lint, layer-schema, texture-info, texture-audit, process-texture, brief-validate, effect-context
build (Core):          build, compile, export, discover, core
review (Godot):        review, overview, strip, frames, history, rubric, review-handoff, review-submit, effect-verify, preview, showcase, package
reference clips:       reference-import, reference-frames, reference-compare
"""


def parser():
    p = argparse.ArgumentParser(prog='vfx', description=__doc__ + COMMANDS, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--project', help='game project that holds (or will hold) the vfx/ workspace; default: VFX_PROJECT or the current directory')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='platform, toolchain and workspace status; which modes are available')
    a = sub.add_parser('init', help='create or refresh vfx/ (Lab, materials, math textures, Godot plugin)')
    a.add_argument('--update-templates', action='store_true', help='overwrite the Lab and materials with the skill version')
    a.add_argument('--no-plugin', action='store_true', help='skip downloading the Effekseer Godot plugin')
    a = sub.add_parser('examples', help='list, show or add the shipped example effects')
    a.add_argument('action', nargs='?', choices=['list', 'show', 'add'], default='list')
    a.add_argument('name', nargs='?', help='example name from `vfx examples list` (a pair such as fire, or a single kind such as hit), an effect ID, or all')
    a.add_argument('--force', action='store_true', help='overwrite existing files when adding')
    sub.add_parser('procedural', help='regenerate the math-primitive textures')
    sub.add_parser('list', help='effects in vfx/src with category, timing, design note and build state')
    a = sub.add_parser('lint', help='static recipe checks; build refuses to run while errors exist')
    a.add_argument('--ids', nargs='*'); a.add_argument('--timeline', action='store_true', help='include per-layer start/end frames')
    sub.add_parser('layer-schema', help='every layer field the compiler accepts')
    a = sub.add_parser('texture-info', help='measured coverage, bbox, border contact, orientation and bulge of processed textures')
    a.add_argument('names', nargs='*')
    a = sub.add_parser('texture-audit', help='role-aware texture or flipbook checks plus a preview image')
    a.add_argument('name'); a.add_argument('--role', default='shape'); a.add_argument('--grid', type=int, nargs=2)
    a.add_argument('--loop', action='store_true'); a.add_argument('--allow-empty', type=int, nargs='*')
    a = sub.add_parser('process-texture', help='crop, luminance alpha, padding and power-of-two resize of a generated image')
    a.add_argument('source'); a.add_argument('output'); a.add_argument('--size', type=int, default=256)
    a.add_argument('--color', action='store_true', help='keep colour (straight RGBA) instead of a white mask')
    a.add_argument('--grid', type=int, nargs=2, metavar=('COLS', 'ROWS'), help='flipbook sheet: keep the cell layout instead of cropping')
    for name, text in [('brief-validate', 'check vfx/briefs/<ID>.json against the recipe'), ('effect-context', 'brief, build state, latest evidence and recent rounds of one effect')]:
        a = sub.add_parser(name, help=text); a.add_argument('id')
    a = sub.add_parser('build', help='compile effects through EffekseerCore (runs lint first)')
    a.add_argument('--ids', nargs='*', help='only these; without --ids the whole library is rebuilt and stale outputs pruned')
    a = sub.add_parser('compile', help='compile one recipe JSON file')
    a.add_argument('recipe'); a.add_argument('--source'); a.add_argument('--runtime')
    a = sub.add_parser('export', help='re-export every built effect to .efk with its resources')
    a.add_argument('--output')
    sub.add_parser('discover', help='dump Core property paths, types and enums (for extending the compiler)')
    # Parsed by the vendored bridge itself (see main); listed here for --help.
    sub.add_parser('core', help='low-level Core document commands on an .efkefc: property-list, property-get, property-set, node-list, curve-list, ... (`vfx core --help`)')
    a = sub.add_parser('review', help='render filmstrips in the Godot Lab; returns strips, flags, changes and an evidence ID')
    a.add_argument('--ids', nargs='*'); a.add_argument('--step', type=int, default=4); a.add_argument('--bright', action='store_true')
    a.add_argument('--note', default='', help='what changed this round; stored in the iteration history')
    a.add_argument('--key-frames', type=int, nargs='*'); a.add_argument('--view', choices=['standard', 'close'], default='standard')
    a.add_argument('--profile', choices=['default', 'bare'], default='default'); a.add_argument('--output')
    a = sub.add_parser('overview', help='tile the latest standard captures into overview pages')
    a.add_argument('--ids', nargs='*', help='a scratch page of only these effects; it does not count for effect-verify')
    a = sub.add_parser('strip', help='path of the last strip (or BEFORE/AFTER comparison) plus its stored metrics')
    a.add_argument('id'); a.add_argument('--compare', action='store_true'); a.add_argument('--bright', action='store_true')
    a = sub.add_parser('frames', help='full-size frame paths of one capture, for detail review')
    a.add_argument('evidence_id'); a.add_argument('frames', type=int, nargs='+')
    a = sub.add_parser('history', help='recent review rounds of one effect, newest last')
    a.add_argument('id'); a.add_argument('--limit', type=int, default=10)
    sub.add_parser('rubric', help='the independent reviewer rubric')
    a = sub.add_parser('review-handoff', help='write the complete brief for an independent reviewer of the latest capture')
    a.add_argument('id')
    a = sub.add_parser('review-submit', help='bind an independent reviewer report to a capture')
    a.add_argument('evidence_id'); a.add_argument('report', help='path of the reviewer JSON report')
    a.add_argument('--reviewer', required=True)
    a.add_argument('--frames', type=int, nargs='+', help="frames the reviewer looked at (default: the report's observed_frames)")
    a = sub.add_parser('effect-verify', help='is the current build captured, independently reviewed and in the overview?')
    a.add_argument('id'); a.add_argument('--no-overview', action='store_true')
    a = sub.add_parser('preview', help='UI screenshots (baseline, peak, 50%%, 85%%)')
    a.add_argument('--ids', nargs='*'); a.add_argument('--bright', action='store_true'); a.add_argument('--output')
    a = sub.add_parser('showcase', help='open the Lab and auto-play the library'); a.add_argument('--movie', action='store_true')
    a = sub.add_parser('package', help='zip the Godot project with an inventory; never claims device tests'); a.add_argument('--preview-dir')
    a = sub.add_parser('reference-import', help='decode a local reference clip (at most 30 media seconds)')
    a.add_argument('source'); a.add_argument('--start', type=float, default=0); a.add_argument('--end', type=float)
    a.add_argument('--slow', type=float, default=1, help='slow-motion factor of the clip; 2 means half speed')
    a.add_argument('--roi', type=int, nargs=4); a.add_argument('--source-url', default=''); a.add_argument('--fps', type=int, default=12)
    a = sub.add_parser('reference-frames', help='labelled frames of one span of a stored reference')
    a.add_argument('reference_id'); a.add_argument('start', type=float); a.add_argument('end', type=float); a.add_argument('--count', type=int, default=12)
    a = sub.add_parser('reference-compare', help='pair reference times with captured Godot frames')
    a.add_argument('reference_id'); a.add_argument('evidence_id'); a.add_argument('--times', type=float, nargs='+', required=True)
    a.add_argument('--reference-times', type=float, nargs='+')
    return p


def recipes_for(ids):
    """(selected, context, unloaded): with --ids only the named sources must load; a full run needs every source."""
    from .library import library, partial
    if ids:
        return partial(ids)
    everything = library()
    if not everything:
        raise ValueError('No recipes in vfx/src; write one or run vfx examples add <pair>. Nothing was built or pruned.')
    return everything, everything, {}


def run(args):
    c = args.command
    if c == 'doctor':
        from .doctor import doctor
        return doctor()
    from .paths import ROOT, WORKSPACE
    if c == 'init':
        from .scaffold import initialize
        return initialize(install_plugin=not args.no_plugin, update_templates=args.update_templates)
    if c == 'examples':
        from . import examples
        if args.action == 'list':
            return examples.listing()
        if not args.name:
            raise ValueError('Name an example: vfx examples ' + args.action + ' <pair|ID|all>')
        if args.action == 'add':
            return examples.add(args.name, args.force)
        return examples.show_any(args.name)
    if c == 'procedural':
        from .textures import procedural
        return {'ok': True, 'generated': procedural()}
    if c == 'list':
        from .library import partial
        built = {e['id'] for e in json.loads((WORKSPACE / 'vfx_manifest.json').read_text())} if (WORKSPACE / 'vfx_manifest.json').is_file() else set()
        _, loaded, unloaded = partial()
        result = {'ok': True, 'effects': [{k: r.get(k) for k in ['id', 'category', 'element', 'duration', 'peak', 'impact', 'delivery', 'design']} | {'built': r['id'] in built} for r in loaded]}
        if unloaded:
            result['unloaded'] = unloaded
        return result
    if c == 'lint':
        from .lint import lint_library
        selected, everything, unloaded = recipes_for(args.ids)
        result = lint_library(selected, everything)
        if unloaded:
            result['unloaded'] = unloaded
        if not args.timeline:
            result.pop('reports')
        return result
    if c == 'layer-schema':
        from effekseer_ai.authoring import layer_schema
        return {'ok': True, **layer_schema()}
    if c == 'texture-info':
        from .textures import inspect, inspect_all
        if not args.names:
            return inspect_all()
        return {n: inspect(Path(n) if n.endswith('.png') else ROOT / f'vfx/textures/processed/{n}.png') for n in args.names}
    if c == 'texture-audit':
        from .texture_audit import audit
        return audit(args.name, args.role, args.grid, args.loop, args.allow_empty)
    if c == 'process-texture':
        from effekseer_ai.resources import process_texture
        return process_texture(args.source, args.output, args.size, mask=not args.color, grid=tuple(args.grid) if args.grid else None)
    if c in ('brief-validate', 'effect-context', 'effect-verify', 'review-submit'):
        from . import evidence, briefs
        if c == 'brief-validate':
            return briefs.validate(briefs.read(args.id), evidence.current_recipe(args.id))
        if c == 'effect-context':
            return evidence.context(args.id)
        if c == 'effect-verify':
            return evidence.verify(args.id, not args.no_overview)
        report = json.loads(Path(args.report).read_text())
        return evidence.submit(args.evidence_id, args.reviewer, report, args.frames or report.get('observed_frames'))
    if c == 'review-handoff':
        from .handoff import handoff
        return handoff(args.id)
    if c == 'build':
        from .build import build
        selected, _, unloaded = recipes_for(args.ids)
        # A full build prunes effects this skill built whose source left vfx/src; --ids rebuilds only the named ones.
        manifest = build(selected, prune=not args.ids)
        result = {'ok': True, 'effects': len(manifest), 'built': [r['id'] for r in selected]}
        if unloaded:
            result['unloaded'] = unloaded
        return result
    if c == 'compile':
        from effekseer_ai.authoring import compile_effect
        recipe = json.loads(Path(args.recipe).read_text())

        def resolve(layers):
            for layer in layers:
                for field in ['texture', 'alpha_texture', 'distortion_texture', 'blend_texture', 'model', 'material_profile']:
                    if layer.get(field):
                        layer[field] = str((ROOT / layer[field]).resolve())
                resolve(layer.get('children', []))
        resolve(recipe['layers'])
        rid = recipe.get('id', Path(args.recipe).stem)
        return compile_effect(recipe, Path(args.source or ROOT / f'vfx/effects/{rid}.efkefc'), Path(args.runtime or ROOT / f'vfx/exports/{rid}.efk'))
    if c == 'export':
        from shutil import copytree
        from effekseer_ai.session import EffectSession
        out = Path(args.output or WORKSPACE / 'exports').resolve()
        result = {'ok': True, 'exports': []}
        for entry in json.loads((WORKSPACE / 'vfx_manifest.json').read_text()):
            source = WORKSPACE / f'effects/{entry["id"]}.efkefc'
            target = out / (source.stem + '.efk')
            EffectSession.open(source).export(target)
            result['exports'].append(str(target))
        copytree(WORKSPACE / 'effects/resources', out / 'resources', dirs_exist_ok=True)
        return result
    if c == 'discover':
        from .discover import discover
        return discover()
    if c == 'review':
        from .review import capture
        return capture(args.ids, args.step, args.bright, output=args.output, note=args.note, key_frames=args.key_frames, view=args.view, profile=args.profile)
    if c == 'overview':
        from .review import overview
        return overview(args.ids)
    if c == 'strip':
        strips = WORKSPACE / 'previews/strips'
        name = args.id + ('_bright' if args.bright else '') + ('_compare' if args.compare else '')
        path = strips / f'{name}.png'
        if not path.is_file():
            raise FileNotFoundError(f'No strip named {path.name}; run vfx review --ids {args.id} first')
        stored = strips / ('metrics_bright.json' if args.bright else 'metrics.json')
        entry = json.loads(stored.read_text()).get(args.id, {}) if stored.is_file() else {}
        return {'ok': True, 'image': str(path), 'metrics': {k: v for k, v in entry.items() if k != 'timeline'}}
    if c == 'frames':
        from . import evidence, workflow
        record = evidence.read_capture(args.evidence_id)
        available = {int(Path(p).stem.rsplit('_f', 1)[1]): p for p in record['frames']}
        missing = [f for f in args.frames if f not in available]
        if missing:
            raise ValueError(f'Frames {missing} were not captured; available: {sorted(available)}')
        return {'ok': True, 'evidence_id': args.evidence_id, 'issues': evidence.capture_issues(record),
                'images': [str(workflow.absolute(available[f])) for f in args.frames]}
    if c == 'history':
        path = WORKSPACE / f'previews/strips/history/{args.id}.jsonl'
        lines = path.read_text().splitlines()[-args.limit:] if path.is_file() else []
        return {'ok': True, 'rounds': [json.loads(line) for line in lines]}
    if c == 'rubric':
        from .paths import ASSETS
        return {'ok': True, **json.loads((ASSETS / 'review_rubric.json').read_text())}
    if c == 'preview':
        from effekseer_ai.preview import preview_effects
        from .paths import godot
        report = preview_effects(str(WORKSPACE / 'godot'), args.output or str(WORKSPACE / 'previews'), args.ids, args.bright, godot=godot())
        return {key: report[key] for key in ['ok', 'output', 'count']}
    if c == 'showcase':
        import subprocess
        from .paths import godot
        movie = WORKSPACE / 'previews/vfx_showcase'
        cmd = [godot(), '--path', str(WORKSPACE / 'godot')]
        if args.movie:
            cmd += ['--write-movie', str(movie.with_suffix('.avi')), '--fixed-fps', '60']
        cmd += ['--', '--showcase'] + (['--movie'] if args.movie else [])
        subprocess.run(cmd, check=True)
        if args.movie:
            # Baseline profile, no B-frames, single thread: the MP4 plays on old phones and in every browser.
            subprocess.run(['ffmpeg', '-y', '-i', str(movie.with_suffix('.avi')), '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                            '-threads', '1', '-profile:v', 'baseline', '-level:v', '4.2', '-bf', '0', '-pix_fmt', 'yuv420p', '-an',
                            str(movie.with_suffix('.mp4'))], check=True)
        return {'ok': True, 'movie': str(movie.with_suffix('.mp4')) if args.movie else None}
    if c == 'package':
        from .finalize import finalize
        return finalize(args.preview_dir)
    from . import reference
    if c == 'reference-import':
        result = reference.import_clip(args.source, args.start, args.end, args.slow, args.roi, args.source_url, args.fps)
        return {k: v for k, v in result.items() if k not in ('frames', 'times')}
    if c == 'reference-frames':
        return reference.frames(args.reference_id, args.start, args.end, args.count)
    if c == 'reference-compare':
        return reference.compare(args.reference_id, args.evidence_id, args.times, args.reference_times)
    raise ValueError(f'Unknown command {c}')


# Commands that work before `vfx init`: they create the workspace, read only the skill, or take explicit file paths.
WITHOUT_WORKSPACE = {'doctor', 'init', 'examples', 'rubric', 'layer-schema', 'process-texture', 'core'}


def main(argv=None):
    raw = list(sys.argv[1:] if argv is None else argv)
    rest = raw[2:] if raw[:1] == ['--project'] else raw
    if rest[:1] == ['core']:
        # The vendored bridge's own command line (explicit file paths, its own JSON output and exit codes), passed through
        # untouched so its options such as --help are not taken by this parser.
        try:
            from effekseer_ai.cli import main as core_main
        except ModuleNotFoundError as error:
            from .paths import setup_command
            print(json.dumps({'ok': False, 'error': {'type': 'SetupRequired', 'message': f'{error}. Run {setup_command()}.'}}))
            return 2
        try:
            return core_main(rest[1:] or ['--help'])
        except SystemExit as done:  # argparse --help / usage errors
            return done.code if isinstance(done.code, int) else 1
    args = parser().parse_args(raw)
    if args.project:
        os.environ['VFX_PROJECT'] = str(Path(args.project).expanduser().resolve())
    from .paths import ROOT, initialized
    if args.command not in WITHOUT_WORKSPACE and not initialized():
        # Never create vfx/ as a side effect of a read: in the wrong folder that leaves a stray workspace behind.
        print(json.dumps({'ok': False, 'error': {'type': 'WorkspaceMissing', 'message':
            f'No effekseer-vfx workspace in {ROOT} (expected vfx/src and vfx/vfx_manifest.json). '
            'Run the command from the game project, pass --project <game project>, or run vfx init there first.'}}, ensure_ascii=False))
        return 2
    try:
        if args.command not in ('doctor', 'examples', 'rubric', 'layer-schema', 'process-texture'):
            from .workflow import project_lock
            with project_lock():
                result = run(args)
        else:
            result = run(args)
    except ModuleNotFoundError as error:
        from .paths import setup_command, full_mode_platform
        print(json.dumps({'ok': False, 'error': {'type': 'SetupRequired', 'message': f'{error}. Run {setup_command(authoring_only=not full_mode_platform())}.'}}))
        return 2
    except Exception as error:
        print(json.dumps({'ok': False, 'error': {'type': type(error).__name__, 'message': str(error)}}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, default=str))
    failed = isinstance(result, dict) and (result.get('ok') is False or (args.command == 'effect-verify' and not result.get('verified')))
    return 1 if failed else 0
