"""Create or refresh the project's vfx/ workspace from the skill's Lab template and material profiles."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from .paths import ROOT, ASSETS, DOWNLOADS
from .ownership import guard
from . import filelock

PLUGIN_URL = 'https://github.com/effekseer/EffekseerForGodot4/releases/download/1.80.5.1/EffekseerForGodot4-180_5_1.zip'
PLUGIN_SHA256 = '1a4987f748156b4707659e9b96b9e28dad42614e2862dc63ec0da8408e089cb6'
FOLDERS = ['src', 'briefs', 'textures/generated', 'textures/procedural', 'textures/processed', 'materials', 'effects', 'exports',
           'previews', 'recipes', 'work', 'godot', 'characters']
GITIGNORE = '''# Local working files of the effekseer-vfx skill; the rest of vfx/ is the effect library.
/godot/
/work/
/previews/*
!/previews/strips/
/previews/strips/*
!/previews/strips/overview_*.png
/previews/strips/overview_select_*.png
!/previews/strips/metrics.json
'''


@contextmanager
def toolchain_lock():
    """Serialise downloads into the shared EFFEKSEER_VFX_HOME across projects and processes."""
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    with (DOWNLOADS / '.lock').open('a') as stream:
        filelock.acquire(stream)
        try:
            yield
        finally:
            filelock.release(stream)


def download(url, sha256, target):
    """A verified copy of `url` at `target`: downloaded to a private temporary file, checked, then moved in."""
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == sha256:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='.download.', dir=target.parent)
    os.close(handle)
    temporary = Path(name)
    try:
        urllib.request.urlretrieve(url, temporary)
        actual = hashlib.sha256(temporary.read_bytes()).hexdigest()
        if actual != sha256:
            raise ValueError(f'Checksum mismatch for {url}: {actual}')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def initialize(root=ROOT, install_plugin=True, update_templates=False):
    root = Path(root).resolve()
    vfx = root / 'vfx'

    def safe(path):  # every write below goes through this first: no link may lead it outside vfx/
        return guard(path, vfx)
    for folder in FOLDERS:
        safe(vfx / folder / 'x')
        (vfx / folder).mkdir(parents=True, exist_ok=True)
    if not (vfx / '.gitignore').exists():
        safe(vfx / '.gitignore').write_text(GITIGNORE)
    for template, target in [(ASSETS / 'godot-lab', vfx / 'godot'), (ASSETS / 'materials', vfx / 'materials')]:
        for src in template.rglob('*'):
            if not src.is_file():
                continue
            dst = target / src.relative_to(template)
            if dst.exists() and not update_templates:
                continue
            safe(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, safe(dst))
    for dst in [vfx / 'vfx_manifest.json', vfx / 'godot/vfx_manifest.json']:
        if not dst.exists():
            safe(dst).write_text('[]\n')
    if not (vfx / 'texture_prompts.json').exists():
        safe(vfx / 'texture_prompts.json').write_text(json.dumps({'prompts': []}, indent=2) + '\n')
    # Starter painted textures: the primitives' defaults (smoke, wisps, billow, flame) must work in a fresh project.
    # Never overwrite a project's own texture; record the matching prompts so lint knows where they came from.
    starters = ASSETS / 'examples/textures'
    installed = []
    for source in sorted(starters.glob('*.png')):
        dst = vfx / 'textures/processed' / source.name
        if not dst.exists():
            shutil.copy2(source, safe(dst))
        installed.append(source.stem)
    prompts_path = vfx / 'texture_prompts.json'
    prompts = json.loads(prompts_path.read_text())
    known = {p['id'] for p in prompts['prompts']}
    shipped = json.loads((ASSETS / 'examples/texture_prompts.json').read_text())['prompts']
    missing = [p for p in shipped if p['id'] in installed and p['id'] not in known]
    if missing:
        prompts['prompts'] += missing
        safe(prompts_path).write_text(json.dumps(prompts, ensure_ascii=False, indent=2) + '\n')
    # Math primitives are regenerated, never versioned by hand.
    from .textures import masks, EXTRA_PROCEDURAL, procedural
    names = set(masks(8)) | EXTRA_PROCEDURAL
    if any(not (vfx / f'textures/{folder}/{n}.png').is_file() for n in names for folder in ('processed', 'procedural')):
        procedural(root=root, missing_only=True)
    # An already built library (fresh clone): make the Lab playable without a Core rebuild.
    tracked = json.loads((vfx / 'vfx_manifest.json').read_text())
    demo = vfx / 'godot/vfx_manifest.json'
    if tracked and not json.loads(demo.read_text()):
        for entry in tracked:
            source = vfx / f"effects/{entry['id']}.efkefc"
            if source.is_file():
                (vfx / 'godot/effects').mkdir(exist_ok=True)
                shutil.copy2(source, safe(vfx / 'godot/effects' / source.name))
        for resource in sorted((vfx / 'effects/resources').glob('*')) if (vfx / 'effects/resources').is_dir() else []:
            if resource.is_file():
                safe(vfx / 'godot/effects/resources' / resource.name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(resource, vfx / 'godot/effects/resources' / resource.name)
        shutil.copy2(vfx / 'vfx_manifest.json', safe(demo))
    # Optional rigged stand-ins: vfx/characters/player.glb and target.glb replace the Lab's capsule dummies.
    for source in sorted([*(vfx / 'characters').glob('*.glb'), *(vfx / 'characters').glob('*.materials.json')]):
        dst = vfx / 'godot/characters' / source.name
        if not dst.is_file() or dst.read_bytes() != source.read_bytes():
            safe(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dst)
    addon = vfx / 'godot/addons/effekseer'
    if install_plugin and not (addon / 'plugin.cfg').is_file():
        with toolchain_lock():
            archive = download(PLUGIN_URL, PLUGIN_SHA256, DOWNLOADS / 'EffekseerForGodot4-180_5_1.zip')
        # Extract into a private folder (never a shared one another init could be rewriting), then copy the addon in.
        with tempfile.TemporaryDirectory(prefix='.plugin.', dir=vfx / 'work') as scratch:
            extracted = Path(scratch)
            with zipfile.ZipFile(archive) as z:
                for name in z.namelist():
                    if not (extracted / name).resolve().is_relative_to(extracted.resolve()):
                        raise ValueError('Unsafe plugin archive path')
                z.extractall(extracted)
            matches = list(extracted.glob('*/addons/effekseer/plugin.cfg'))
            if len(matches) != 1:
                raise ValueError('Expected one official Effekseer Godot addon')
            staged = vfx / 'work' / '.addon'
            shutil.rmtree(staged, ignore_errors=True)
            shutil.copytree(matches[0].parent, staged)
            license_file = matches[0].parents[2] / 'LICENSE'
            if license_file.is_file():
                shutil.copy2(license_file, staged / 'LICENSE')
            safe(addon / 'plugin.cfg')
            addon.parent.mkdir(parents=True, exist_ok=True)
            if addon.exists():  # an incomplete earlier install (no plugin.cfg); the addon folder is generated
                shutil.rmtree(addon)
            staged.replace(addon)
    if (addon / 'plugin.gd').is_file():
        # The editor plugin loads its icon through the import cache; read the PNG directly so a first import works.
        path = safe(addon / 'plugin.gd')
        text = path.read_text()
        text = text.replace('var icon = load(plugin_path + "/icon16.png") as Texture2D',
                            'var icon_image := Image.load_from_file(plugin_path + "/icon16.png")\n\tvar icon := ImageTexture.create_from_image(icon_image)')
        path.write_text(text)
    return {'ok': True, 'workspace': str(vfx), 'plugin_installed': (addon / 'plugin.cfg').is_file()}
