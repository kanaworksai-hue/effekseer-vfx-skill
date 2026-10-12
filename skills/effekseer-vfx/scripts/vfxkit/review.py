"""Motion review: render a clean frame sequence in Godot and tile it into one filmstrip per effect.

Three stills cannot show timing. A strip shows anticipation, peak, follow-through and dissipation
at a glance, so an agent can judge and iterate on motion instead of on a single lucky frame.
"""
import json,subprocess,shutil,sys,re,threading,time
from pathlib import Path
from . import workflow, briefs, evidence
from .paths import ROOT, godot as godot_path
import numpy as np
from PIL import Image,ImageDraw
CROP=(160,60,1200,740)  # both dummies, the flight path and boss-sized areas in the 1280x800 combat view, UI hidden

# Flag thresholds, calibrated on a 20-effect library render (--step 3) checked tile by tile.
# - Energy alone undercounts alpha-blended dark smoke on the dark stage (Fire_Explosion read "dead" at f30
#   while smoke stayed visible to f54), so a frame also counts as active while 0.4% of the stage changes.
# - Pure white is also the colour of sustained hot bodies (Holy_Pillar's core beam, Ice_Spikes' spikes), so
#   the flash is only the contiguous run around the contact frame that stands above the white level the
#   effect holds before it (Magic_Charge's growing core read as a 28-frame flash at --step 4) and after it.
#   Sampled every 3-4 frames, a 5-frame contact plus its bloom spans up to 3 samples; the longest legitimate
#   run was Ice_Spikes' erupting white spikes at 12 frames, so the bar sits there.
# - A projectile's centroid and radius follow the flight path the game chose, not the element's own
#   motion, so the rise/inward checks skip category 'projectile' (Projectile_Dark read as "expanding").
# - Strips use the combat staging (dummies at both ends, farther camera, wider crop): effects cover ~0.77x the
#   area inside a 1.26x larger crop, so the absolute coverage bars were scaled by ~0.6 (0.4% -> 0.25%, cut off
#   2% -> 1.2%) and re-checked on a full-library render.
# - Only fire must rise: references/craft.md lets holy descend or rise, and ground seals that outlast
#   a pillar pull the centroid down at the end without anything sinking.
ACTIVE_FRACTION=.05   # a frame is "active" while its change energy is at least 5% of the peak frame's ...
VISIBLE_COVERAGE=.0025 # ... or at least 0.25% of the stage changes (the same bar as "barely visible")
CUT_OFF_COVERAGE=.012  # last frame still changes this much of the stage
DEAD_TAIL=.35         # flag when the inactive tail exceeds 35% of the duration (and 6 frames)
FLASH_SPAN=12         # contact flash should be gone within ~12 sampled frames
FLASH_SETTLE=30       # frames on each side of contact whose median white is the level the effect sustains
HOT_LUMA=.85          # white-hot pixel
RISING={'fire'}

def front_app():
 """(pid, bundle path) of the frontmost macOS app; (None, None) elsewhere."""
 if sys.platform!='darwin' or not shutil.which('lsappinfo'):return None,None
 asn=subprocess.run(['lsappinfo','front'],capture_output=True,text=True).stdout.strip()
 info=subprocess.run(['lsappinfo','info','-only','pid',asn],capture_output=True,text=True).stdout+subprocess.run(['lsappinfo','info','-only','bundlepath',asn],capture_output=True,text=True).stdout
 pid=re.search(r'pid = (\d+)',info); bundle=re.search(r'bundle path="([^"]+)"',info)
 return (int(pid.group(1)) if pid else None),(bundle.group(1) if bundle else None)

NO_WINDOW=('Godot started but rendered no frame within {seconds} s. Most likely it could not open its window: the review '
 'needs a real window on the logged-in desktop, which a sandboxed agent (for example Codex in its workspace sandbox) or '
 'a session without a desktop (SSH, CI) cannot open; check the Godot output below for another cause. Run this command '
 'outside the sandbox with the user\'s approval, or, if the agent cannot leave its sandbox, give the user the exact '
 'command to run in a terminal on their desktop. Godot output: {tail}')

def run_windowed(command,timeout,progress=None,startup=90):
 """Run a windowed Godot capture without taking the user's foreground: Godot activates itself on launch (and again
 when the Lab parks its window), so while it runs, focus is handed straight back to the app that was in front.

 `progress()` says whether the capture has produced anything yet; if it has not after `startup` seconds, Godot could
 not open its window, and the run stops with that explanation instead of waiting for the full timeout."""
 _,bundle=front_app()
 proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 def give_back():
  while proc.poll() is None:
   if front_app()[0]==proc.pid:subprocess.run(['open','-a',bundle],capture_output=True)
   time.sleep(.1)
 if bundle:threading.Thread(target=give_back,daemon=True).start()
 started=time.monotonic()
 while True:
  try:
   out,err=proc.communicate(timeout=2)  # retrying communicate after a timeout loses no output
   break
  except subprocess.TimeoutExpired:
   waited=time.monotonic()-started
   if progress and waited>startup and not progress():
    proc.kill(); out,err=proc.communicate()
    raise RuntimeError(NO_WINDOW.format(seconds=startup,tail=(out+err)[-1500:].strip() or '(none)'))
   if waited>timeout:
    proc.kill(); raise
 return subprocess.CompletedProcess(command,proc.returncode,out,err)

def sample_plan(entry,step=4,key_frames=None):
 if type(step) is not int or not 1<=step<=60:raise ValueError('step must be an integer 1..60')
 end=int(entry['duration']*60)
 if step>end:raise ValueError('step must not exceed the effect duration in frames')
 keys=briefs.keyframes(entry,briefs.read(entry['id']))+(key_frames or [])
 if any(type(f) is not int or not 1<=f<=end+12 for f in keys):raise ValueError('key frames must be integer frames within effect + 12')
 return sorted(set(range(step,end+1,step))|set(keys)|{end+6})

def frame_state(frames,rid,expected):
 shots={int(p.stem.rsplit('_f',1)[1]):p for p in frames.glob(rid+'_f*.png')}
 missing=sorted(({0}|set(expected))-set(shots))
 moving=False
 if 0 in shots:
  with Image.open(shots[0]) as image:base=np.asarray(image.convert('RGB'),dtype=np.int16)
  for f in expected:
   if f not in shots:continue
   with Image.open(shots[f]) as image:current=np.asarray(image.convert('RGB'),dtype=np.int16)
   if current.shape!=base.shape:missing.append(f);continue
   if np.abs(current-base).max()>24:moving=True
 status='missing_frames' if missing else 'complete' if moving else 'inconclusive'
 return {'status':status,'expected':expected,'actual':sorted(shots),'missing':missing,
         'activity_observed':moving,'note':'No pixel activity may mean an unplayed effect or a legitimately faint effect; inspect logs and frames.' if not moving else ''}

@workflow.locked
def capture(ids=None,step=4,bright=False,output=None,godot=None,timeout=900,note='',key_frames=None,view='standard',profile='default'):
 if view not in ('standard','close'):raise ValueError('view must be standard or close')
 if profile not in ('default','bare'):raise ValueError('profile must be default or bare')
 godot=godot or godot_path()
 project=ROOT/'vfx/godot'; out=Path(output or ROOT/'vfx/previews/strips').resolve()
 if view!='standard' or profile!='default':out=out/'variants'/f'{view}_{profile}'
 if not (project/'vfx_manifest.json').is_file():raise FileNotFoundError('vfx/godot is missing; run vfx init and vfx build first')
 entries={e['id']:e for e in json.loads((project/'vfx_manifest.json').read_text())}
 ids=ids or list(entries)
 unknown=sorted(set(ids)-set(entries))
 if unknown:raise ValueError(f'Unknown effect IDs: {unknown}')
 for rid in ids:workflow.effect_id(rid)
 plans={rid:sample_plan(entries[rid],step,key_frames) for rid in ids}
 for rid in ids:
  if evidence.read_build(rid):
   problems=evidence.build_issues(rid)
   if problems:raise RuntimeError(f'{rid}: build again before review: {problems}')
 sync=evidence.template_issues()
 if sync:raise RuntimeError('Sync the Lab before review: '+', '.join(sync))
 dependency_state={rid:evidence.dependencies(entries[rid]) for rid in ids}
 out.mkdir(parents=True,exist_ok=True); suffix='_bright' if bright else ''
 # Distinct run directories retain previous evidence and prevent partial review erasing sibling frames.
 import uuid
 run_id=uuid.uuid4().hex
 frames=out/'runs'/run_id/'frames';frames.mkdir(parents=True)
 plan_path=out/'runs'/run_id/'plan.json';workflow.save_json(plan_path,plans)
 metrics_path=out/('metrics_bright.json' if bright else 'metrics.json')
 previous=json.loads(metrics_path.read_text()) if metrics_path.is_file() else {}
 for rid in ids:
  if (out/f'{rid}{suffix}.png').is_file():shutil.copy2(out/f'{rid}{suffix}.png',out/f'{rid}{suffix}.prev.png')
 stage=evidence.stage_snapshot()
 imported=subprocess.run([godot,'--headless','--editor','--path',str(project),'--import'],capture_output=True,text=True,timeout=timeout)
 if imported.returncode or 'SCRIPT ERROR:' in imported.stdout+imported.stderr:raise RuntimeError(f'Godot import failed: {imported.stderr[-3000:]}')
 pending=list(ids);logs=[];states={}
 for attempt in range(3):
  for rid in pending:
   for shot in frames.glob(rid+'_f*.png'):shot.unlink()
  command=[godot,'--path',str(project),'--fixed-fps','60','--','--strip='+str(frames),f'--step={step}',
           '--ids='+','.join(pending),'--sample-plan='+str(plan_path),'--review-view='+view]
  if bright:command.append('--bright')
  if profile=='bare':command.append('--bare')
  run=run_windowed(command,timeout,progress=lambda:any(frames.glob('*.png')))
  logs.append(run.stdout+run.stderr); (frames.parent/'strip.log').write_text('\n'.join(logs))
  if run.returncode or 'SCRIPT ERROR:' in run.stdout+run.stderr:raise RuntimeError(f'Godot strip capture failed ({run.returncode}): {(run.stdout+run.stderr)[-3000:]}')
  for rid in pending:states[rid]=frame_state(frames,rid,plans[rid])
  pending=[rid for rid in pending if states[rid]['status']!='complete']
  if not pending:break
 if any(s['missing'] for s in states.values()):raise RuntimeError('Incomplete capture: '+json.dumps(states))
 if stage!=evidence.stage_snapshot():raise RuntimeError('Stage changed while capturing; discard this run')
 if dependency_state!={rid:evidence.dependencies(entries[rid]) for rid in ids}:raise RuntimeError('Staged dependencies changed while capturing; discard this run')
 sheets=[];compares=[];details={};proofs={};report={}
 legacy_frames=out/('frames_bright' if bright else 'frames');legacy_frames.mkdir(exist_ok=True)
 for rid in ids:
  shots=sorted(frames.glob(rid+'_f*.png'))[1:]
  target=out/f'{rid}{suffix}.png';sheets.append(str(sheet(rid,shots,target,entries[rid],key_frames=briefs.keyframes(entries[rid],briefs.read(rid)))))
  before=out/f'{rid}{suffix}.prev.png'
  if before.is_file():compares.append(str(compare_sheet(before,target,out/f'{rid}{suffix}_compare.png')))
  keys=sorted(set(briefs.keyframes(entries[rid],briefs.read(rid))+(key_frames or [])))
  detail_paths=[frames/f'{rid}_f{f:03d}.png' for f in keys if (frames/f'{rid}_f{f:03d}.png').is_file()]
  detail_target=out/'runs'/run_id/f'{rid}_keyframes.png'
  sheet(rid,detail_paths,detail_target,entries[rid],columns=3,width=600,key_frames=keys,max_tiles=len(keys))
  details[rid]={'sheet':str(detail_target),'frames':[str(p) for p in detail_paths]}
  # Metrics keep uniform sampling: irregular keyframes do not inherit old step-based thresholds.
  metric_frames=frames.parent/'metrics';metric_frames.mkdir(exist_ok=True)
  for p in frames.glob(rid+'_f*.png'):
   f=int(p.stem.rsplit('_f',1)[1])
   if f==0 or (f%step==0 and f<=int(entries[rid]['duration']*60)):shutil.copy2(p,metric_frames/p.name)
  report[rid]=metrics(rid,metric_frames,entries[rid],step)
  for p in legacy_frames.glob(rid+'_f*.png'):p.unlink()
  for p in frames.glob(rid+'_f*.png'):shutil.copy2(p,legacy_frames/p.name)
  # Immutable image copies, so a new review cannot mutate an older report's evidence.
  immutable=frames.parent/target.name;shutil.copy2(target,immutable)
  with Image.open(shots[0]) as image:resolution=list(image.size)
  states[rid]['log']={'path':workflow.relative(frames.parent/'strip.log'),'sha256':workflow.file_hash(frames.parent/'strip.log')}
  config={'view':view,'profile':profile,'bright':bright,'step':step,'key_frames':keys,'seed':entries[rid].get('seed',1729),
          'fps':60,'resolution':resolution,
          'engine_log':run.stdout.splitlines()[:4]}
  config['profile']=profile+('_bright' if bright else '')
  proof=evidence.write_capture(rid,[immutable,detail_target],list(frames.glob(rid+'_f*.png')),config,states[rid],stage,entries[rid],note)
  proofs[rid]=proof['evidence_id']
 metrics_path.write_text(dump_metrics(previous|report))
 changes={rid:diff(previous.get(rid),report[rid]) for rid in ids if rid in previous}
 history=[str(record(out,rid+suffix,report[rid],note,proofs[rid])) for rid in ids]
 return {'ok':not pending,'sheets':sheets,'compare':compares,'metrics':str(metrics_path),
         'flags':{rid:m['flags'] for rid,m in report.items() if m['flags']},'changes':{rid:c for rid,c in changes.items() if c},
         'history':history,'details':details,'evidence':proofs,'capture':states,'view':view,'profile':profile}

def metrics(rid,frames,entry,step=4):
 """Per-frame change energy, brightness layering and motion from viewport pixel differences.

 A reading aid for the strips, not a GPU or overdraw measurement. energy is the stage-wide mean change
 magnitude (0-1), so a large faint smoke and a small white flash are comparable; coverage is the share of
 changed pixels; white the share of changed pixels at pure white.
 """
 shots=sorted(frames.glob(rid+'_f*.png'))
 base=np.asarray(Image.open(shots[0]).convert('RGB').crop(CROP),dtype=np.int16); timeline=[]
 h,w=base.shape[:2]; yy,xx=np.mgrid[0:h,0:w]; scale=float(h)
 for shot in shots[1:]:
  image=np.asarray(Image.open(shot).convert('RGB').crop(CROP),dtype=np.int16)
  delta=np.abs(image-base).max(axis=2); changed=delta>18; weight=delta*changed; total=float(weight.sum())
  luma=(.2126*image[...,0]+.7152*image[...,1]+.0722*image[...,2])/255
  t={'frame':int(shot.stem.rsplit('_f',1)[1]),'coverage':round(float(changed.mean()),4),'white':round(float((np.all(image>250,axis=2)&changed).mean()),4),
   'energy':round(total/(255*h*w),5)}
  if changed.any():
   top=image.max(axis=2); saturation=(top-image.min(axis=2))/np.maximum(top,1); lit=luma[changed]
   t['layers']=[round(float((lit>HOT_LUMA).mean()),3),round(float(((saturation[changed]>.4)&(lit>=.2)&(lit<=HOT_LUMA)).mean()),3),round(float((lit<.2).mean()),3)]
   cx=float((weight*xx).sum()/total); cy=float((weight*yy).sum()/total)
   t['centre']=[round(cx/scale,3),round(1-cy/scale,3)]  # stage units of its height, y up
   t['radius']=round(float((weight*np.hypot(xx-cx,yy-cy)).sum()/total/scale),3)
  timeline.append(t)
 visible=[t['frame'] for t in timeline if t['coverage']>.0004]  # a handful of embers still counts as visible
 last=max(visible) if visible else 0; total=entry['duration']*60
 peak=max(timeline,key=lambda t:t['energy']); widest=max(timeline,key=lambda t:t['coverage'])
 active=[t for t in timeline if (peak['energy']>0 and t['energy']>=peak['energy']*ACTIVE_FRACTION) or t['coverage']>=VISIBLE_COVERAGE]
 last_active=active[-1]['frame'] if active else 0
 whitest=max(timeline,key=lambda t:t['white'])
 contact=whitest if whitest['white']>=.001 else peak
 flash_span=0
 if whitest['white']>=.001:
  # Contiguous samples around contact that stay above halfway between its white and the level the effect
  # holds on that side: a charge's growing core before the release and a beam after it are not the flash.
  whites=[t['white'] for t in timeline]; i=j=timeline.index(whitest); window=max(3,FLASH_SETTLE//step)
  def bar(side):return (float(np.median(side)) if side else 0.)*.5+whites[i]*.5
  before=bar(whites[max(0,i-window):i]); after=bar(whites[i+1:i+1+window])
  while i>0 and whites[i-1]>=before:i-=1
  while j<len(whites)-1 and whites[j+1]>=after:j+=1
  flash_span=timeline[j]['frame']-timeline[i]['frame']+step
 by_frame={t['frame']:t for t in timeline}
 def at(frame):return by_frame.get(frame,{})
 motion={}
 end=at(last_active)
 if 'centre' in contact and 'centre' in end and last_active>contact['frame']:
  motion['drift_up']=round(end['centre'][1]-contact['centre'][1],3); motion['spread']=round(end['radius']/max(contact['radius'],1e-3),2)
 first=active[0] if active else {}
 before_contact=[t for t in active if t['frame']<contact['frame'] and 'radius' in t]
 if first and len(before_contact)>=3 and contact['frame']-first['frame']>=12:
  motion['charge_spread']=round(before_contact[-1]['radius']/max(before_contact[0]['radius'],1e-3),2)
 flags=[]
 # Scaled effects (references/scale.md) last `stretch` times longer: frame tolerances stretch with them.
 stretch=float((entry.get('scale') or {}).get('time',1)); beam=(entry.get('delivery') or {}).get('kind')=='beam'
 if widest['coverage']<VISIBLE_COVERAGE:flags.append(f'barely visible: under {VISIBLE_COVERAGE:.2%} of the stage changes at its strongest frame')
 if total-last_active>max(6*stretch,total*DEAD_TAIL):flags.append(f'dead tail: under {ACTIVE_FRACTION:.0%} of peak energy and {VISIBLE_COVERAGE:.2%} of the stage after frame {last_active} of {round(total)}; shorten duration or keep the dissipation visible')
 if sum(t['white']>.1 for t in timeline)>2:flags.append('blown out: over 10% pure white for more than two sampled frames')
 if not entry.get('loop') and visible and timeline[-1]['coverage']>CUT_OFF_COVERAGE:flags.append('cut off: still clearly visible on the last frame')
 if entry.get('impact',0)>=.3:
  expected=entry.get('peak',0)*60
  # A beam's sustained white core outshines its ignition, so the contact of a beam is not its whitest frame.
  if not beam and abs(contact['frame']-expected)>max(6,2*step)*stretch:flags.append(f"off-peak contact: brightest at frame {contact['frame']} but manifest peak is frame {expected:.0f}; the Lab flash and camera kick land elsewhere")
  if flash_span>FLASH_SPAN*stretch:flags.append(f'lingering flash: near-peak white lasts {flash_span} frames; contact should be 2-5')
 layering=peak.get('layers')
 if layering and widest['coverage']>=VISIBLE_COVERAGE:
  if layering[0]<.005:flags.append('no white-hot core: almost no pixel above 85% brightness at the peak frame')
  if layering[1]<.03:flags.append('washed out: almost no saturated mid-tone body at the peak frame')
 travelling=entry.get('category')=='projectile'
 if not travelling and entry.get('element') in RISING and motion.get('drift_up',0)<-.04:flags.append(f"sinks: {entry['element']} mass moves down {-motion['drift_up']:.2f} stage heights after contact; it should rise")
 if not travelling and entry.get('element')=='dark' and motion.get('charge_spread',1)>1.1:flags.append(f"expands while charging: radius grows {motion['charge_spread']}x before the release; dark should draw inward")
 return {'peak_frame':peak['frame'],'peak_coverage':widest['coverage'],'peak_energy':peak['energy'],'contact_frame':contact['frame'],'flash_span':flash_span,
  'last_visible_frame':last,'last_active_frame':last_active,'duration_frames':round(total),'layering':layering,'motion':motion,'flags':flags,'timeline':timeline}

def dump_metrics(report):
 """Tracked baseline: one line per field and per timeline frame, so it stays small and diffs by frame."""
 line=lambda value:json.dumps(value,separators=(',',':'))
 effects=[]
 for rid,entry in report.items():
  fields=[f'  {json.dumps(k)}: {line(v)}' for k,v in entry.items() if k!='timeline']
  if 'timeline' in entry:fields.append('  "timeline": [\n'+',\n'.join('   '+line(t) for t in entry['timeline'])+'\n  ]')
  effects.append(f' {json.dumps(rid)}: {{\n'+',\n'.join(fields)+'\n }')
 return '{\n'+',\n'.join(effects)+'\n}\n'

def diff(old,new):
 """What this round changed, by flag kind (text before the colon) and key timings."""
 if not old:return {}
 kind=lambda flags:{f.split(':')[0] for f in flags}
 out={}
 added=sorted(kind(new['flags'])-kind(old.get('flags',[]))); resolved=sorted(kind(old.get('flags',[]))-kind(new['flags']))
 if added:out['flags_added']=added
 if resolved:out['flags_resolved']=resolved
 for key in ['peak_frame','contact_frame','last_active_frame','duration_frames']:
  if key in old and old[key]!=new[key]:out[key]=[old[key],new[key]]
 return out

def record(out,name,report,note='',evidence_id=None):
 """Append one line per review to history/<ID>.jsonl so later rounds (and agents) can see what was tried."""
 import datetime,hashlib
 recipe=ROOT/f"vfx/recipes/{name.removesuffix('_bright')}.json"
 def git(*args):
  try:return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,timeout=10).stdout.strip()
  except (OSError,subprocess.SubprocessError):return ''
 line={'evidence_id':evidence_id,'time':datetime.datetime.now().isoformat(timespec='seconds'),'note':note,'commit':git('rev-parse','--short','HEAD'),
  'uncommitted':bool(git('status','--porcelain','vfx/src','vfx/briefs')),
  'recipe_sha':hashlib.sha256(recipe.read_bytes()).hexdigest()[:12] if recipe.is_file() else None,
  **{k:report[k] for k in ['flags','peak_frame','contact_frame','last_active_frame','duration_frames','layering','motion']}}
 path=out/'history'/f'{name}.jsonl'; path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a') as f:f.write(json.dumps(line)+'\n')
 return path

def compare_sheet(before,after,target):
 """Previous strip above the new one, labelled, so one image shows whether the round helped."""
 a=Image.open(before).convert('RGB'); b=Image.open(after).convert('RGB'); width=max(a.width,b.width)
 canvas=Image.new('RGB',(width,a.height+b.height+48),(8,10,16)); draw=ImageDraw.Draw(canvas)
 draw.text((8,4),'BEFORE',fill=(255,140,120)); canvas.paste(a,(0,24))
 draw.text((8,a.height+28),'AFTER',fill=(140,255,160)); canvas.paste(b,(0,a.height+48))
 canvas.save(target); return target

def sheet(rid,shots,target,entry,columns=6,width=300,key_frames=None,max_tiles=18):
 # Long effects are thinned to at most 18 tiles so one image stays readable.
 if len(shots)>max_tiles:
  by_frame={int(p.stem.rsplit('_f',1)[1]):p for p in shots}
  picked={f for f in (key_frames or []) if f in by_frame}
  # Key moments are never dropped to meet a cosmetic tile cap.
  room=max(2,max_tiles-len(picked))
  picked.update(int(shots[round(i*(len(shots)-1)/(room-1))].stem.rsplit('_f',1)[1]) for i in range(room))
  shots=[by_frame[f] for f in sorted(picked)]
 scale=width/(CROP[2]-CROP[0]); height=round((CROP[3]-CROP[1])*scale)
 rows=(len(shots)+columns-1)//columns
 canvas=Image.new('RGB',(columns*width,rows*height+26),(8,10,16)); draw=ImageDraw.Draw(canvas)
 draw.text((8,6),f"{rid}   {entry['duration']:.2f}s   peak {entry.get('peak',0):.2f}s   frames @60fps",fill=(200,215,230))
 for i,shot in enumerate(shots):
  tile=Image.open(shot).convert('RGB').crop(CROP).resize((width,height),Image.Resampling.LANCZOS)
  x,y=(i%columns)*width,26+(i//columns)*height
  canvas.paste(tile,(x,y)); draw.text((x+6,y+4),'f'+shot.stem.rsplit('_f',1)[1].lstrip('0'),fill=(255,230,120))
 canvas.save(target)
 return target

@workflow.locked
def overview(ids=None,columns=6,width=300,per_page=10,output=None):
 """Library pages from the last capture: one row per effect, frames spread over its duration.

 Without `ids` this is the library baseline that effect-verify checks: effects that were never captured are left
 out and listed in `missing`. With `ids` it is a scratch page (overview_select_*.png) that never replaces the baseline.
 """
 out=Path(output or ROOT/'vfx/previews/strips').resolve(); frames=out/'frames'
 manifest=json.loads((ROOT/'vfx/vfx_manifest.json').read_text())
 unknown=sorted(set(ids or [])-{e['id'] for e in manifest})
 if unknown:raise ValueError(f'Not in the built manifest: {unknown}')
 entries=[e for e in manifest if not ids or e['id'] in ids]
 def captured(entry):
  proof=evidence.latest(entry['id'])
  return bool(proof and proof['frames']) or any(frames.glob(entry['id']+'_f*.png'))
 missing=[e['id'] for e in entries if not captured(e)]
 if ids and missing:raise RuntimeError(f"{missing}: no captured frames; run vfx review --ids {' '.join(missing)} first")
 entries=[e for e in entries if e['id'] not in missing]
 if not entries:raise RuntimeError('No effect has been captured yet; run vfx review first')
 prefix='overview_select_' if ids else 'overview_'
 scale=width/(CROP[2]-CROP[0]); height=round((CROP[3]-CROP[1])*scale); pages=[]
 for start in range(0,len(entries),per_page):
  rows=entries[start:start+per_page]
  canvas=Image.new('RGB',(columns*width,len(rows)*(height+20)),(8,10,16)); draw=ImageDraw.Draw(canvas)
  for r,entry in enumerate(rows):
   proof=evidence.latest(entry['id'])
   shots=sorted((ROOT/p for p in proof['frames'] if not p.endswith('_f000.png'))) if proof else sorted(frames.glob(entry['id']+'_f*.png'))[1:]
   if not shots:raise RuntimeError(f"{entry['id']}: no captured frames; run the strip capture first")
   # Skip the empty tail: sample the first 85% of the timeline, where the effect actually lives.
   picks=[shots[min(len(shots)-1,round(i*(len(shots)*.85-1)/(columns-1)))] for i in range(columns)]
   y=r*(height+20); draw.text((6,y+4),f"{entry['id']}  {entry['duration']:.2f}s",fill=(200,215,230))
   for i,shot in enumerate(picks):
    canvas.paste(Image.open(shot).convert('RGB').crop(CROP).resize((width,height),Image.Resampling.LANCZOS),(i*width,y+20))
    draw.text((i*width+6,y+24),'f'+shot.stem.rsplit('_f',1)[1].lstrip('0'),fill=(255,230,120))
  page=out/f'{prefix}{start//per_page+1}.png'; canvas.save(page); pages.append(str(page))
 if ids:
  return {'ok':True,'pages':pages,'note':'scratch page of the named effects only; run vfx overview without --ids for the baseline effect-verify checks'}
 # Pages left over from a larger library would otherwise look current.
 for stale in out.glob('overview_*.png'):
  if not stale.name.startswith('overview_select_') and str(stale) not in pages:stale.unlink()
 proofs={e['id']:evidence.latest(e['id']) for e in entries}
 workflow.save_json(evidence.store()/'overview.json',{'images':workflow.snapshot(map(Path,pages)),
  'evidence':{rid:r['evidence_id'] for rid,r in proofs.items() if r and not evidence.capture_issues(r)}})
 return {'ok':True,'pages':pages,'missing':missing}

