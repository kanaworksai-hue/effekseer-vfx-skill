"""Package current generated assets; never invent test/device verification results."""
from pathlib import Path
import hashlib, json, platform, shutil, subprocess, sys, zipfile
from PIL import Image
from .paths import ROOT, WORK, godot

def finalize(preview_dir=None):
 entries=json.loads((ROOT/'vfx/vfx_manifest.json').read_text())
 if not entries:raise ValueError('Build an effect manifest before packaging')
 previews=Path(preview_dir or ROOT/'vfx/previews')
 missing=[]
 for entry in entries:
  source=previews/(entry['id']+'.png')
  if not source.is_file():missing.append(entry['id']);continue
  destination=ROOT/'vfx/previews'/source.name
  if source.resolve()!=destination.resolve():shutil.copy2(source,destination)
  thumbnails=ROOT/'vfx/godot/previews';thumbnails.mkdir(exist_ok=True)
  image=Image.open(source).crop((400,175,1200,605));image.thumbnail((480,258),Image.Resampling.LANCZOS);image.save(thumbnails/source.name)
 def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
 inventory=[]
 for path in sorted((ROOT/'vfx/textures/processed').glob('*.png')):
  image=Image.open(path);raw=ROOT/'vfx/textures/generated'/path.name
  inventory.append({'name':path.stem,'size':image.size,'sha256':digest(path),'source_sha256':digest(raw) if raw.is_file() else None})
 docs=WORK;docs.mkdir(parents=True,exist_ok=True)
 (docs/'texture_inventory.json').write_text(json.dumps(inventory,indent=2))
 environment={'os':platform.platform(),'architecture':platform.machine(),'python':sys.version.split()[0],'godot':subprocess.check_output([godot(),'--version'],text=True).strip(),'project_path':'vfx/godot'}
 (docs/'environment.json').write_text(json.dumps(environment,indent=2))
 project=ROOT/'vfx/godot';package=ROOT/'vfx/exports/Vfx_Godot.zip';package.parent.mkdir(exist_ok=True)
 temporary=package.with_suffix('.zip.partial')
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,6) as archive:
  for path in sorted(project.rglob('*')):
   if not path.is_file() or '.godot' in path.parts or path.suffix=='.import' or path.name=='.DS_Store':continue
   archive.write(path,'Vfx_Godot/'+path.relative_to(project).as_posix())
 temporary.replace(package)
 summary={'effects':len(entries),'categories':len({e['category'] for e in entries}),'missing_previews':missing,'processed_textures':len(inventory),'package':str(package),'package_bytes':package.stat().st_size,'package_sha256':digest(package),'verification':'Run and record import/play/device tests separately; packaging does not establish those results.'}
 (docs/'delivery.json').write_text(json.dumps(summary,indent=2));return summary

