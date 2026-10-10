"""Compile recipes through EffekseerCore into .efkefc sources, .efk runtime exports and the manifest."""
from pathlib import Path
import json, shutil, sys
from .workflow import locked
from .paths import ROOT, WORK
from .primitives import walk, tex, is_path, budget, TEXTURE_KEYS
from . import ownership
from .ownership import MARKER, valid_id, digest

RESOURCE_KEYS=TEXTURE_KEYS+['model']  # layer fields whose files Core copies into resources/ by base name
RESOURCE_DIRS=['effects/resources','exports/resources','godot/effects/resources']
# Every folder init or a build writes into or deletes from.
OUTPUT_DIRS=['src','briefs','work','materials','textures/procedural','textures/processed','previews','godot','effects','exports','recipes','godot/effects',*RESOURCE_DIRS]

def owned(entry):return ownership.owned(entry,ROOT,WORK)

def eid(entry):return entry.get('id') if isinstance(entry,dict) else None

def check_output_dirs():
 """Every folder init or a build writes into or deletes from must really be inside vfx/, also when it does not exist
 yet (its parent may be a symlink elsewhere)."""
 vfx=ROOT/'vfx'
 for folder in OUTPUT_DIRS:
  path=vfx/folder
  if not ownership.inside(path,vfx):raise ValueError(f'{path} resolves outside {vfx}; refusing to write or delete there')

def check_targets(paths):
 """No file a build is about to write may be a link that leads outside vfx/ (writes follow file symlinks)."""
 vfx=ROOT/'vfx'
 for path in paths:
  if (path.exists() or path.is_symlink()) and not ownership.inside(path,vfx):
   raise ValueError(f'{path} resolves outside {vfx}; refusing to overwrite it')

def removable(rid):
 """The outputs of one owned effect, refusing anything that resolves outside vfx/ (a symlinked folder, say)."""
 vfx=ROOT/'vfx'
 paths=[ROOT/f'vfx/effects/{rid}.efkefc',ROOT/f'vfx/exports/{rid}.efk',ROOT/f'vfx/recipes/{rid}.json',*(ROOT/'vfx/godot/effects').glob(f'{rid}.efkefc*')]
 safe=[]
 for path in paths:
  if not path.is_file():continue
  if not ownership.inside(path,vfx):raise ValueError(f'Refusing to delete {path}: it resolves outside {vfx}')
  safe.append(path)
 return safe

def resource_inputs(recipes):
 """{resource base name: source file} for every texture and model the recipes import.

 Core copies each into resources/ under its base name, so two different files with one name would silently replace
 each other inside every effect that uses it."""
 found={}
 for recipe in recipes:
  for layer in walk(recipe['layers']):
   for key in RESOURCE_KEYS:
    if layer.get(key):
     path=Path(layer[key]);name=path.name
     # Names that differ only in case are one file on a case-insensitive disk: their content must agree. Every
     # spelling is kept, because Core writes each under its own name and each must be mirrored and checked.
     for other in [n for n in found if ownership.same_name(n,name)]:
      if digest(found[other])!=digest(path):
       raise ValueError(f'Resource name conflict: {found[other]} and {path} are different files named {other} (names ignore case); rename one')
     found.setdefault(name,path)
 return found

def resource_names(rid):
 """Resource names a built effect uses, from its compiled recipe snapshot; None when that is unknown."""
 path=ROOT/f'vfx/recipes/{rid}.json'
 try:recipe=json.loads(path.read_text())
 except (OSError,ValueError):return None
 return {Path(layer[key]).name for layer in walk(recipe.get('layers',[])) for key in RESOURCE_KEYS if layer.get(key)}

def check_resource_conflicts(inputs,previous,rebuilding,removing):
 """Refuse to replace a resources/ file with different content while another effect may still use it: an owned effect
 that is neither rebuilt nor removed (per its recipe snapshot), or any effect this skill did not build."""
 unknown=ownership.unmanaged(ROOT,WORK,previous,ignore=rebuilding|removing)
 for name,source in inputs.items():
  if not any((ROOT/'vfx'/folder/name).is_file() and digest(ROOT/'vfx'/folder/name)!=digest(source) for folder in RESOURCE_DIRS):continue
  for entry in previous:
   rid=eid(entry)
   if not valid_id(rid) or rid in rebuilding or rid in removing or not owned(entry):continue
   names=resource_names(rid)
   if names is None or any(ownership.same_name(n,name) for n in names):
    raise ValueError(f'Resource name conflict: {source} would replace resources/{name}, which {rid} uses with different content; '
                     f'rebuild them together (vfx build --ids {" ".join(sorted(rebuilding|{rid}))}) or rename the file')
  users=[f for f in unknown if ownership.may_use(f,name)]
  if users:
   shown=', '.join(str(f.relative_to(ROOT)) if f else 'an unowned manifest entry' for f in users)
   raise ValueError(f'Resource name conflict: {source} would replace resources/{name}, which an effect this skill did not build may use ({shown}); rename the file')

@locked
def build(recipes,prune=False):
 import copy
 from effekseer_ai.authoring import compile_effect
 recipes=copy.deepcopy(recipes)
 from .scaffold import initialize
 check_output_dirs()  # before init writes the Lab into vfx/godot
 initialize()
 for recipe in recipes:
  for layer in walk(recipe['layers']):
   for key in TEXTURE_KEYS:
    if layer.get(key) and not is_path(layer[key]):layer[key]=tex(layer[key])
 missing=sorted({layer[key] for recipe in recipes for layer in walk(recipe['layers']) for key in TEXTURE_KEYS if layer.get(key) and not Path(layer[key]).is_file()})
 if missing:raise FileNotFoundError('Missing input textures; generate/process them first: '+', '.join(missing))
 check_output_dirs()
 manifest_path=ROOT/'vfx/vfx_manifest.json'
 previous=json.loads(manifest_path.read_text()) if manifest_path.is_file() else []
 rebuilding={r['id'] for r in recipes}
 # A full build (prune) drops effects this skill built whose source left vfx/src; decided before anything is written,
 # so those effects neither block the build nor survive it. Entries and files it did not build are never touched.
 removed=[eid(e) for e in previous if prune and eid(e) not in rebuilding and owned(e)]
 doomed=[path for rid in removed for path in removable(rid)]  # every path checked before anything is deleted
 # Writes follow file symlinks: refuse targets that lead outside vfx/ before anything is written.
 check_targets([ROOT/f'vfx/{folder}/{r["id"]}{ext}' for r in recipes for folder,ext in
                (('recipes','.json'),('effects','.efkefc'),('exports','.efk'),('godot/effects','.efkefc'))]
               +[manifest_path,ROOT/'vfx/godot/vfx_manifest.json'])
 # Same-named resources: within this build, and against what other effects already use from resources/.
 inputs=resource_inputs(recipes)
 check_targets([ROOT/'vfx'/folder/name for name in inputs for folder in RESOURCE_DIRS])
 check_resource_conflicts(inputs,previous,rebuilding,set(removed))
 # Static rules first: unknown fields, lifetimes past duration, budgets, units. Fails before any Core work.
 from .lint import lint_library
 checked=lint_library(recipes)
 if not checked['ok']:raise ValueError('Recipe lint failed: '+json.dumps(checked['errors'],ensure_ascii=False))
 if checked['warnings']:print(json.dumps({'lint_warnings':checked['warnings']},ensure_ascii=False),file=sys.stderr,flush=True)
 target=ROOT/'vfx/godot/effects'; target.mkdir(parents=True,exist_ok=True)
 built={}; compiled={}
 for recipe in recipes:
  for layer in walk(recipe['layers']):
   profile={'Add':'M_Additive','Blend':'M_Alpha','Sub':'M_Subtractive'}.get(layer.get('blend','Add'))
   if profile:layer['material_profile']=str(ROOT/f'vfx/materials/{profile}.vfxmat.json')
  rid=recipe['id']; source=ROOT/f'vfx/effects/{rid}.efkefc'; runtime=ROOT/f'vfx/exports/{rid}.efk'
  (ROOT/'vfx/recipes').mkdir(exist_ok=True)
  # Portable recipes: texture paths relative to workspace, normalized at load time.
  saved=json.loads(json.dumps(recipe).replace(str(ROOT)+'/',''))
  (ROOT/f'vfx/recipes/{rid}.json').write_text(json.dumps(saved,indent=2))
  report=compile_effect(recipe,source,runtime)
  compiled[rid]=report
  shutil.copy2(source,target/source.name)
  entry={k:v for k,v in recipe.items() if k!='layers'}
  # `built_by` + `source` mark the entry as built by this skill: only such entries are ever pruned.
  entry.update(built_by=MARKER,source=f'vfx/src/{rid}.py',file='res://effects/'+source.name,runtime='exports/'+runtime.name,preview='previews/'+rid+'.png',particle_budget=sum(budget(l) for l in recipe['layers']),layers=len(list(walk(recipe['layers']))))
  built[rid]=entry; print(json.dumps({k:v for k,v in report.items() if k!='nodes'}),file=sys.stderr,flush=True)
 # A partial build updates its entries in place; a full build also removes the effects planned above.
 built_ids=set(built)
 manifest=[built.pop(eid(e),e) for e in previous if eid(e) not in removed]+list(built.values())
 for path in doomed:path.unlink()
 # Resource copies no recipe references any more would otherwise ship with every export. Only exact copies of a
 # processed texture (and that PNG's own .import file), and never a name an effect this skill did not build may use.
 if prune:
  unknown=ownership.unmanaged(ROOT,WORK,manifest,ignore=built_ids)
  used={ownership.name_key(Path(layer[key]).name) for recipe in recipes for layer in walk(recipe['layers']) for key in RESOURCE_KEYS if layer.get(key)}
  candidates=[]
  for processed in sorted((ROOT/'vfx/textures/processed').glob('*.png')):
   name=processed.name
   if ownership.name_key(name) in used or any(ownership.may_use(f,name) for f in unknown):continue
   for folder in RESOURCE_DIRS:
    png=ROOT/'vfx'/folder/name; imported=ROOT/'vfx'/folder/(name+'.import')
    if png.is_file():
     if digest(png)!=digest(processed):continue  # same name, other content: not our copy
     candidates.append(png)
    # The PNG's own import file goes with it, or alone when the PNG itself is already gone.
    if imported.is_file() and (png in candidates or not png.exists()):candidates.append(imported)
  for path in candidates:
   if not ownership.inside(path,ROOT/'vfx'):raise ValueError(f'Refusing to delete {path}: it resolves outside vfx/')
  for path in candidates:path.unlink()
 # Mirror only the resources this build imported (checked above), never the whole folder: other effects' files stay.
 for name in inputs:
  for folder in ('exports/resources','godot/effects/resources'):
   (ROOT/'vfx'/folder).mkdir(parents=True,exist_ok=True)
   shutil.copy2(ROOT/'vfx/effects/resources'/name,ROOT/'vfx'/folder/name)
 for dst in [manifest_path,ROOT/'vfx/godot/vfx_manifest.json']:dst.write_text(json.dumps(manifest,indent=2))
 from .evidence import write_build
 for recipe in recipes:write_build(recipe,compiled[recipe['id']])
 return manifest
