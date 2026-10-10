"""Render through the official Godot plugin and VfxLab capture harness."""
from pathlib import Path
import subprocess, json

def preview_effects(project_path: str, output_dir: str, ids: list[str] | None=None, bright: bool=False, godot: str='godot', timeout: int=300) -> dict:
 project=Path(project_path).resolve(); output=Path(output_dir).resolve()
 if not (project/'project.godot').is_file():raise ValueError(f'Godot project not found: {project}')
 if not (project/'scripts/VfxLab.gd').is_file():raise ValueError('Project needs the VfxLab capture harness')
 entries=json.loads((project/'vfx_manifest.json').read_text())
 if not entries:raise ValueError('No effects in the manifest; compile/build effects before previewing')
 known={entry['id'] for entry in entries}
 if ids and not set(ids)<=known:raise ValueError(f'Unknown preview IDs: {sorted(set(ids)-known)}')
 output.mkdir(parents=True,exist_ok=True)
 command=[godot,'--headless','--editor','--path',str(project),'--import']
 imported=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
 if imported.returncode or 'SCRIPT ERROR:' in imported.stderr or 'ERROR:' in imported.stderr:
  raise RuntimeError(f'Godot import failed: {imported.stderr[-4000:]}')
 command=[godot,'--path',str(project),'--fixed-fps','60','--','--capture='+str(output)]
 if ids:command.append('--ids='+','.join(ids))
 if bright:command.append('--bright')
 run=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
 captures=[]
 for line in run.stdout.splitlines():
  try:
   data=json.loads(line)
   if 'capture' in data:captures.append(data)
  except ValueError:pass
 (output/'capture.log').write_text(run.stdout+run.stderr)
 if run.returncode or 'SCRIPT ERROR:' in run.stderr or 'ERROR:' in run.stderr:
  raise RuntimeError(f'Godot preview failed ({run.returncode}): {run.stderr[-4000:]}')
 expected_ids=ids or [entry['id'] for entry in json.loads((project/'vfx_manifest.json').read_text())]
 expected={id+suffix for id in expected_ids for suffix in ['', '_baseline', '_phase1', '_phase2']}
 observed={capture['capture'] for capture in captures}
 missing=sorted(expected-observed)
 if missing:raise RuntimeError(f'Incomplete capture: {len(missing)} screenshots missing; process may have been closed before completion. First missing: {missing[:4]}')
 if not captures or any(c['error'] for c in captures):raise RuntimeError('Godot did not produce valid screenshots')
 return {'ok':True,'output':str(output),'captures':captures,'count':len(captures)}
