"""Static recipe checks. Needs neither EffekseerCore nor Godot, so it also runs in cloud/Linux sessions.

Errors are hard rules that make a build wrong (unknown fields, budget, lifetime, units, undocumented
textures); `build` refuses to run while any exist. Warnings encode the references/craft.md heuristics:
they point at likely craft problems but the rendered strip decides.
"""
import json
from pathlib import Path
from effekseer_ai.authoring import validate_layer
from .primitives import walk, lifetime, budget, TEXTURE_KEYS
from .paths import ROOT

BUDGET={'hit':60,'boss':250,'projectile':100}  # references/craft.md, budgets; every other category is an element skill
DEFAULT_BUDGET=150
MAX_GRAVITY=.01               # per frame squared; sparks use .001-.002 and rocks .004
CONTACT_TEXTURE='T_Flare01'   # what flash() draws
CONTACT_MAX_LIFE=6            # contact frames are 2-5; the library uses up to 6
CONTACT_LAYER_LIFE=10         # a single white-hot additive layer this short also reads as the contact (slash_set's cel crescent)
HOT_LUMA=.85                  # same bar as review.py, so lint and review agree on what white-hot means
PEAK_TOLERANCE=6              # frames between the contact flash and manifest peak, where the Lab kicks
MIN_DIFFERENCES=3             # of shape, motion, rhythm, material, secondary (section 3)

def documented_textures():
 from .textures import masks,EXTRA_PROCEDURAL
 path=ROOT/'vfx/texture_prompts.json'
 prompts=json.loads(path.read_text())['prompts'] if path.is_file() else []
 return set(masks(8))|EXTRA_PROCEDURAL, {p['id'] for p in prompts}

def stem(value):return Path(value).stem if value else None

def hot(c):
 """White-hot: very bright and nearly unsaturated, so warm whites count and acid greens do not."""
 return (.2126*c[0]+.7152*c[1]+.0722*c[2])/255>=HOT_LUMA and min(c[:3])>=180 and (len(c)<4 or c[3]>0)

def colours(layer):
 found=[layer.get('color'),layer.get('color_end')]
 ring=layer.get('ring') if isinstance(layer.get('ring'),dict) else {}
 found+=[ring.get(k) for k in ['outer_color','center_color','inner_color']]
 return [c for c in found if isinstance(c,(list,tuple)) and len(c)>=3]

def moves(layer):
 """Coarse motion tags for the element-difference check."""
 tags=set(); travel=layer.get('travel') or {}; spawn=layer.get('spawn') or {}
 def high(v):return max(v) if isinstance(v,(list,tuple)) else v
 def low(v):return min(v) if isinstance(v,(list,tuple)) else v
 end=travel.get('end')
 if end:
  y=end[1]
  if spawn.get('shape') in ('Sphere','Circle') and spawn.get('rotate',True):tags.add('outward' if low(y)>=0 else 'inward')
  elif high(y)>0:tags.add('rise')
  elif low(y)<0:tags.add('fall')
 for force in layer.get('forces') or []:
  if force.get('type')=='Gravity':tags.add('rise' if force['gravity'][1]>0 else 'fall')
  if force.get('type') in ('Vortex','Turbulence'):tags.add(force['type'].lower())
 spin=layer.get('spin')
 if spin and max(abs(high(spin[2])),abs(low(spin[2])))>=3:tags.add('swirl')
 if isinstance(layer.get('ring'),dict) and 'angle_end' in layer['ring']:tags.add('sweep')
 if layer.get('scale_curve') and any(v>1.05 for _,v in layer['scale_curve'][1:-1]):tags.add('overshoot')
 return tags

def look(layer):
 """What a layer draws: renderer plus its texture or procedural mesh shape."""
 model=(layer.get('procedural_model') or {}).get('Shape/PrimitiveType')
 return (layer.get('renderer','Sprite'),model or stem(layer.get('texture')))

def features(recipe):
 layers=list(walk(recipe['layers']))
 duration=recipe['duration']; peak=recipe.get('peak',0)/max(duration,1e-6)
 # A projectile's trail (layers left behind in world space) is its secondary motion; its head is the shape.
 def many(l):return l.get('count',1)>1 or bool(l.get('inherit'))
 return {
  'shape':frozenset(look(l) for l in layers if not many(l) and stem(l.get('texture'))!=CONTACT_TEXTURE),
  'motion':frozenset(t for l in layers for t in moves(l))|({'lobbed'} if recipe.get('arc') else set()),
  'rhythm':(min(3,int(duration/.5)),0 if peak<.2 else 1 if peak<.5 else 2,round(recipe.get('flight',0)/.15)),
  'material':frozenset([l.get('blend','Add') for l in layers]+[k for l in layers for k in ('distortion_texture','falloff','edge','flipbook','procedural_model') if l.get(k)]),
  'secondary':frozenset(look(l) for l in layers if many(l)),
 }

def lint(recipe,known=None):
 errors=[];warnings=[]
 procedural,painted=known or documented_textures()
 layers=list(walk(recipe['layers'])); rid=recipe['id']; frames=recipe['duration']*60
 for layer in recipe['layers']:errors+=validate_layer(layer)
 if not 0<=recipe.get('peak',0)<recipe['duration']:errors.append(f"peak {recipe.get('peak')} s is outside the {recipe['duration']} s duration")
 release=recipe.get('flight',0)*60
 sustained=[l for l in layers if l.get('infinite')]
 if sustained and not recipe.get('flight'):errors.append(f"{sustained[0]['name']}: infinite layers emit until release, so the recipe needs flight (seconds of the reference flight)")
 for layer in sustained:
  if not layer.get('interval'):errors.append(f"{layer['name']}: infinite layer needs an interval > 0 or it spawns without limit")
 if not recipe.get('loop'):
  for layer in recipe['layers']:
   if lifetime(layer,release=release)>frames:errors.append(f"{layer['name']}: alive until frame {round(lifetime(layer,release=release))} but the effect ends at {round(frames)}; it would be cut off on recycle")
 limit=BUDGET.get(recipe.get('category'),DEFAULT_BUDGET); total=sum(budget(l) for l in recipe['layers'])
 if total>limit:errors.append(f"particle budget {total} exceeds {limit} for category {recipe.get('category')!r}")
 for layer in layers:
  for key in TEXTURE_KEYS:
   name=stem(layer.get(key))
   if name and name not in procedural|painted:errors.append(f"{layer['name']}.{key}: {name} is neither a math primitive nor recorded in vfx/texture_prompts.json")
   if name and not (ROOT/f'vfx/textures/processed/{name}.png').is_file():errors.append(f"{layer['name']}.{key}: vfx/textures/processed/{name}.png is missing")
  # The compiler multiplies a size/scale curve by a fixed start scale; a random size range with a curve crashes the build.
  random_scale=isinstance(layer.get('size'),(list,tuple)) or any(isinstance(v,(list,tuple)) for v in layer.get('scale_start') or [])
  if random_scale and (layer.get('size_curve') or layer.get('scale_curve')):
   errors.append(f"{layer['name']}: size_curve/scale_curve needs a fixed size/scale_start; vary size with a second layer instead of a random range")
  # UV distortion is measured in whole-texture UV; on a flipbook sheet it samples the neighbouring cells and the
  # sprite renders as hard-edged blocks (seen on the fire flipbooks).
  if layer.get('flipbook') and layer.get('distortion_texture'):
   errors.append(f"{layer['name']}: UV distortion on a flipbook samples neighbouring cells (hard square edges); drop distortion_texture or use a single-frame texture")
  for force in layer.get('forces') or []:
   if force.get('type')=='Gravity' and max(abs(g) for g in force.get('gravity',[0,0,0]))>MAX_GRAVITY:
    errors.append(f"{layer['name']}: gravity {force['gravity']} is per frame squared; above {MAX_GRAVITY} particles leave the screen")
  life=layer.get('life',24); shortest=min(life) if isinstance(life,(list,tuple)) else life
  if layer.get('fade_in',1)+layer.get('fade_out',0)>shortest*1.05:warnings.append(f"{layer['name']}: fade_in+fade_out exceed the shortest life {shortest}; it never reaches full opacity")
 # Craft heuristics (warnings).
 flashes=[l for l in layers if stem(l.get('texture'))==CONTACT_TEXTURE]
 def longest(l):life=l.get('life',24);return max(life) if isinstance(life,(list,tuple)) else life
 contacts=flashes+[l for l in layers if l not in flashes and l.get('count',1)==1 and l.get('blend','Add')=='Add' and longest(l)<=CONTACT_LAYER_LIFE and any(hot(c) for c in colours(l))]
 if recipe.get('impact',0)>=.3:
  if not contacts:warnings.append('impact effect without a contact flash: no flash() layer and no short single white-hot additive layer; the Lab kick at peak has no matching bright frame')
  else:
   peak=recipe.get('peak',0)*60; nearest=min(contacts,key=lambda l:abs(l.get('delay',0)-peak))
   if abs(nearest.get('delay',0)-peak)>PEAK_TOLERANCE:warnings.append(f"contact {nearest['name']!r} starts at frame {nearest.get('delay',0)} but manifest peak is frame {peak:.0f}; the Lab flash and camera kick land elsewhere")
  for l in flashes:
   life=l.get('life',5)
   if (max(life) if isinstance(life,(list,tuple)) else life)>CONTACT_MAX_LIFE:warnings.append(f"{l['name']}: contact flash lives {life} frames; contact should be 2-5")
 # Lightning changes shape by swapping frames: the same painted shape on several layers that start at different times.
 starts={}
 for l in layers:
  if l.get('count',1)==1 and stem(l.get('texture')):starts.setdefault(stem(l['texture']),set()).add(l.get('delay',0))
 swapped=any(len(s)>=2 for name,s in starts.items() if name in painted)
 if not swapped and not any(l.get('cutoff') is not None or l.get('distortion_texture') or l.get('uv_scroll') or l.get('alpha_scroll') or l.get('flipbook') or (isinstance(l.get('ring'),dict) and 'angle_end' in l['ring']) for l in layers):
  warnings.append('no layer changes shape (dissolve cutoff, ring sweep, UV distortion/scroll, flipbook or a painted shape re-struck on later frames); the body can only scale and fade')
 if not any(hot(c) for l in layers if l.get('blend','Add')=='Add' for c in colours(l)):
  warnings.append(f'no white-hot additive colour (luma >= {HOT_LUMA}, min channel >= 180); brightness layering needs a hot core above the saturated body')
 timeline=sorted(([l['name'],l.get('delay',0),round(lifetime(l,release=recipe.get("flight",0)*60))] for l in recipe['layers']),key=lambda t:t[1])
 return {'id':rid,'errors':errors,'warnings':warnings,'budget':[total,limit],'timeline':timeline}

def compare_elements(recipes):
 """Pairs in one category whose elements differ in fewer than MIN_DIFFERENCES feature groups: likely recolours."""
 out={}; feats={r['id']:features(r) for r in recipes}
 for i,a in enumerate(recipes):
  for b in recipes[i+1:]:
   if a.get('category')!=b.get('category') or a.get('element')==b.get('element'):continue
   same=[k for k in feats[a['id']] if feats[a['id']][k]==feats[b['id']][k]]
   if 5-len(same)<MIN_DIFFERENCES:
    for x,y in [(a,b),(b,a)]:out.setdefault(x['id'],[]).append(f"differs from {y['id']} ({y.get('element')}) only in {5-len(same)} of shape/motion/rhythm/material/secondary; same {', '.join(same)}")
 return out

def lint_library(recipes,context=None):
 """Lint `recipes`; element differences are judged against `context` (default: the recipes themselves)."""
 known=documented_textures(); reports=[lint(r,known) for r in recipes]
 pairs=compare_elements(context or recipes)
 for report in reports:report['warnings']+=pairs.get(report['id'],[])
 return {'ok':not any(r['errors'] for r in reports),
  'errors':{r['id']:r['errors'] for r in reports if r['errors']},
  'warnings':{r['id']:r['warnings'] for r in reports if r['warnings']},
  'reports':{r['id']:{k:r[k] for k in ('budget','timeline')} for r in reports}}

