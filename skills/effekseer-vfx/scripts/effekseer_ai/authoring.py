"""Reusable, discovered-property layer authoring. No GUI state is required."""
from pathlib import Path
import difflib, math, re
from .session import EffectSession
from .runtime import load_core

# Every key LayerBuilder reads. Anything else used to be ignored silently, so a misspelt 'fade_ot'
# compiled into a different effect without any error; validate_layer() now rejects it.
LAYER_FIELDS={
 'name','material_profile','material','count','life','interval','delay','blend','z_test','emissive','fade_in','fade_out',
 'renderer','color','color_curve','color_end','billboard','pivot','procedural_model','model','culling',
 'ring','ring_outer','ring_inner','track_size','texture','uv_scroll','distortion',
 'travel','position','velocity','acceleration','rotation','spin','scale_start','scale_end','scale_curve','size','size_end','size_curve','easing',
 'wrap','flipbook','alpha_texture','alpha_scroll','alpha_wrap','distortion_texture','distortion_scroll','distortion_intensity',
 'blend_texture','blend_scroll','blend_type','cutoff','edge','falloff','soft','collide','spawn','forces','inherit',
 'infinite','remove_with_parent','z_sort','priority','properties','curves','children','bind'}
NESTED_FIELDS={
 'ring':{'vertices','outer','inner','center_ratio','outer_color','center_color','inner_color','angle_start','angle_end','angle_easing','angle_fade'},
 'travel':{'start','end','easing'},
 'spawn':{'shape','rotate','radius','rot_x','rot_y','axis','division','order','angle_start','angle_end','angle_noise','start','end','noise'},
 'edge':{'color','threshold','scaling'},
 'falloff':{'begin','end','pow','blend'},
 'flipbook':{'x','y','frame_length','loop','start','lerp'},
 'inherit':{'location','rotation','scale','color'},
 'collide':{'height','bounce','friction','reduction','world'},
 'cutoff':{'start','end','easing'},
 'bind':{'position','scale'},
}
# Dynamic equations: a game input (@In0..@In3), numbers, arithmetic and Effekseer's built-in functions only.
EQUATION=re.compile(r'^[\s\w@.+\-*/(),]*$')
FORCE_FIELDS={'type','power','gravity','scale','octave','kind','control','min_range','max_range','position','rotation'}

def _number(v):return isinstance(v,(int,float)) and not isinstance(v,bool)
def _term(v):
 """A bind component: a number, an equation string, or [number, equation] meaning their product."""
 return _number(v) or isinstance(v,str) or (isinstance(v,(list,tuple)) and len(v)==2 and _number(v[0]) and isinstance(v[1],str))
def _code(v):
 if isinstance(v,(list,tuple)):return f'{float(v[0])!r} * ({v[1]})'
 return repr(float(v)) if _number(v) else v

def _unknown(keys,allowed,where):
 errors=[]
 for key in keys:
  if key in allowed:continue
  close=difflib.get_close_matches(key,allowed,1)
  errors.append(f"{where}: unknown field {key!r}"+(f"; did you mean {close[0]!r}?" if close else ''))
 return errors

def validate_layer(spec,where='',recursive=True):
 """List problems the compiler would otherwise swallow: unknown or misspelt keys at any nesting level."""
 here=f"{where}/{spec.get('name','?')}" if where else str(spec.get('name','?'))
 errors=[] if spec.get('name') else [f'{here}: layer needs a name']
 errors+=_unknown(spec,LAYER_FIELDS,here)
 for key,allowed in NESTED_FIELDS.items():
  if isinstance(spec.get(key),dict):errors+=_unknown(spec[key],allowed,f'{here}.{key}')
 if isinstance(spec.get('flipbook'),dict):
  for key in ('x','y','frame_length'):
   if key in spec['flipbook'] and (type(spec['flipbook'][key]) is not int or spec['flipbook'][key]<1):
    errors.append(f'{here}.flipbook.{key}: must be a positive integer (native Core Int field)')
 for key in ['outer','inner']:
  value=spec.get('ring',{}).get(key) if isinstance(spec.get('ring'),dict) else None
  if isinstance(value,dict):errors+=_unknown(value,{'start','end'},f'{here}.ring.{key}')
 for i,force in enumerate(spec.get('forces') or []):
  if 'type' not in force:errors.append(f'{here}.forces[{i}]: force needs a type')
  errors+=_unknown(force,FORCE_FIELDS,f'{here}.forces[{i}]')
 bind=spec.get('bind')
 if isinstance(bind,dict):
  for key,value in bind.items():
   if not isinstance(value,(list,tuple)) or len(value)!=3 or not all(_term(v) for v in value):
    errors.append(f'{here}.bind.{key}: needs three components, each a number, an equation string such as "@In0" or [number, "equation"] (their product)')
   elif not all(EQUATION.match(_code(v)) for v in value):
    errors.append(f'{here}.bind.{key}: equations may only use @In0..@In3, numbers, arithmetic and functions')
 if recursive:
  for child in spec.get('children') or []:errors+=validate_layer(child,here)
 return errors

CUTOFF_EASINGS={'Linear':lambda t:t,'EaseInQuadratic':lambda t:t**2,'EaseInCubic':lambda t:t**3,'EaseInQuartic':lambda t:t**4,
 'EaseOutQuadratic':lambda t:1-(1-t)**2,'EaseOutCubic':lambda t:1-(1-t)**3}

def cutoff_easing(curve):
 """{'start','end','easing'} equivalent of a cutoff curve [[percent_of_life, threshold], ...].

 Thresholds are written as an Easing because the Godot runtime keeps an FCurve threshold at its first key. Core
 clamps the values to 0..1, so the curve's shape goes into the easing type: start is the first key, end the curve
 extended to 100 %, and the easing type is the one that fits the keys best (a curve that holds and then erodes
 becomes an ease-in). Write the dict yourself for exact control.
 """
 keys=sorted((float(f),float(v)) for f,v in curve)
 if not keys:raise ValueError('cutoff curve needs at least one key')
 clamp=lambda v:round(min(1.0,max(0.0,v)),4)
 start=clamp(keys[0][1])
 if len(keys)==1:return {'start':start,'end':start,'easing':'Linear'}
 (f0,v0),(f1,v1)=keys[-2],keys[-1]
 end=clamp(v1+(v1-v0)/max(f1-f0,1e-6)*(100-f1))
 def at(t):
  for (a,va),(b,vb) in zip(keys,keys[1:]):
   if t<=b:return va+(vb-va)*(t-a)/max(b-a,1e-6) if t>=a else va
  return vb+(v1-v0)/max(f1-f0,1e-6)*(t-keys[-1][0])
 samples=[at(t) for t in range(0,101,5)]
 error=lambda f:sum((start+(end-start)*f(t/100)-v)**2 for t,v in zip(range(0,101,5),samples))
 return {'start':start,'end':end,'easing':min(CUTOFF_EASINGS,key=lambda name:error(CUTOFF_EASINGS[name]))}

def layer_schema():
 """Field names accepted by layer specs, for agents that want to check a recipe before compiling."""
 return {'layer':sorted(LAYER_FIELDS),**{k:sorted(v) for k,v in NESTED_FIELDS.items()},'forces':sorted(FORCE_FIELDS)}

class LayerBuilder:
 def __init__(self, session):
  self.session=session
  self.schema=None
  self.writes=[]
  self.equations={}   # equation code -> Core DynamicEquation, shared by every layer that binds the same code
  self.bindings=[]    # (vector property path, equation code) for the save/open check
 def set(self,node,field,value):
  if self.schema is None:
   self.schema={p.removeprefix(node+'/') for p in self.session.property_list(node,12)}
  if field not in self.schema:
   raise ValueError(f'Unknown Core property: {field}. Discover with property-list first.')
  p=f'{node}/{field}'
  before=self.session.property_get(p)
  self.session.property_set(p,value)
  self.writes.append({'property':p,'before':before,'after':self.session.property_get(p)})
 def scalar(self,n,p,v): self.set(n,p+'/Value',v)
 def rand(self,n,p,v):
  if isinstance(v,(tuple,list)):
   lo,hi=v
  else: lo=hi=v
  self.set(n,p+'/Max',hi); self.set(n,p+'/Min',lo)
 def vector(self,n,p,v,random=False):
  for axis,val in zip('XYZ',v):
   if random:self.rand(n,p+'/'+axis,val)
   else:self.scalar(n,p+'/'+axis,val)
 def color(self,n,p,rgba,random=False):
  for ch,val in zip('RGBA',rgba):
   if random:self.rand(n,p+'/'+ch,val)
   else:self.scalar(n,p+'/'+ch,val)
 def curve(self,n,p,keys):
  # p is a scalar FCurve object, already discovered as p/Keys.
  if p+'/Keys' not in self.schema: raise ValueError(f'Unknown FCurve {p}')
  self.session.curve_set_keys(n+'/'+p,[{'frame':int(f),'value':v,'interpolation':1} for f,v in keys])
  self.scalar(n,p+'/Sampling',1)
 def uv(self,n,base,texture,scroll=None,wrap=None):
  """Bind a texture slot and optionally scroll it; speeds are UV units per frame."""
  self.session.import_image(texture,n+'/'+base+'/Texture' if 'Advanced' in base else n+'/'+base)
  if wrap:self.scalar(n,(base if 'Advanced' in base else 'RendererCommonValues')+'/Wrap',wrap)
  if scroll:
   from PIL import Image
   size=Image.open(texture).size
   root=base if 'Advanced' in base else 'RendererCommonValues'
   self.scalar(n,root+'/UV','Scroll')
   for axis,dim,speed in zip('XY',size,scroll):
    self.rand(n,root+'/UVScroll/Size/'+axis,dim); self.rand(n,root+'/UVScroll/Speed/'+axis,speed*dim)
 def bind(self,n,bind):
  """Fixed position/scale that a dynamic equation recomputes every frame from the game's inputs (@In0..@In3):
  a beam's length or its end point follows Vfx.beam() while the particles are alive."""
  core=load_core()
  for key,group,vector in (('position','LocationValues','Fixed/Location'),('scale','ScalingValues','Fixed/Scale')):
   if key not in bind:continue
   code='\n'.join(f'@O.{axis} = {_code(value)}' for axis,value in zip('xyz',bind[key]))
   if code not in self.equations:
    core.Dynamic.Equations.New()
    equation=list(core.Dynamic.Equations.Values)[-1]
    equation.Name.SetValue(f'bind {len(self.equations)}'); equation.Code.SetValue(code)
    self.equations[code]=equation
   self.scalar(n,group+'/Type','Fixed')
   for axis,value in zip('XYZ',bind[key]):
    self.scalar(n,f'{group}/{vector}/{axis}',float(value) if _number(value) else 0.)
   self.scalar(n,f'{group}/{vector}/IsDynamicEquationEnabled',True)
   self.session._object_at_path(f'{n}/{group}/{vector}').DynamicEquation.SetValue(self.equations[code])
   self.bindings.append((f'{n}/{group}/{vector}',code))
 def advanced(self,n,spec):
  """Optional native features: dissolve, UV distortion, blend texture, fresnel, flipbook, spawn shapes, forces."""
  s=self.scalar; r=self.rand; A='AdvancedRendererCommonValuesValues/'
  if spec.get('wrap'):s(n,'RendererCommonValues/Wrap',spec['wrap'])
  if spec.get('flipbook'):
   from PIL import Image
   f=spec['flipbook']; w,h=Image.open(spec['texture']).size; P='RendererCommonValues/UVAnimation/AnimationParams/'
   s(n,'RendererCommonValues/UV','Animation')
   s(n,P+'Size/X',w//f['x']); s(n,P+'Size/Y',h//f['y']); s(n,P+'FrameCountX',f['x']); s(n,P+'FrameCountY',f['y'])
   s(n,P+'FrameLength/Value',f.get('frame_length',2)); s(n,P+'LoopType',f.get('loop','Once')); r(n,P+'StartSheet',f.get('start',0))
   s(n,'RendererCommonValues/UVAnimation/FlipbookInterpolationType','Lerp' if f.get('lerp',True) else 'None')
  if spec.get('alpha_texture'):
   s(n,A+'AlphaTextureParam/Enabled',True); self.uv(n,A+'AlphaTextureParam',spec['alpha_texture'],spec.get('alpha_scroll'),spec.get('alpha_wrap'))
  if spec.get('distortion_texture'):
   s(n,A+'UVDistortionTextureParam/Enabled',True); self.uv(n,A+'UVDistortionTextureParam',spec['distortion_texture'],spec.get('distortion_scroll'))
   s(n,A+'UVDistortionTextureParam/UVDistortionIntensity',spec.get('distortion_intensity',.05))
  if spec.get('blend_texture'):
   B=A+'BlendTextureParams/'
   s(n,B+'Enabled',True); self.uv(n,B+'BlendTextureParam',spec['blend_texture'],spec.get('blend_scroll'))
   s(n,B+'BlendTextureParam/BlendType',spec.get('blend_type','Mul'))
  cutoff=spec.get('cutoff')
  if cutoff is not None:
   # Dissolve: pixels whose (texture alpha x alpha texture) fall below the threshold disappear.
   C=A+'AlphaCutoffParam/'; s(n,C+'Enabled',True)
   if isinstance(cutoff,(int,float)):s(n,C+'Type','Fixed'); s(n,C+'Fixed/Threshold',cutoff)
   else:
    # The threshold is always written as an Easing over the particle's life: the Godot runtime
    # (EffekseerForGodot4 1.80.5.1) keeps an FCurve threshold at its first key, so a curve never erodes there.
    # Core clamps the thresholds to 0..1; a hold-then-erode shape comes from an ease-in curve, not a negative start.
    ease=cutoff if isinstance(cutoff,dict) else cutoff_easing(cutoff)
    s(n,C+'Type','Easing'); r(n,C+'Easing/Start',ease['start']); r(n,C+'Easing/End',ease['end'])
    s(n,C+'Easing/Type',ease.get('easing','Linear'))
   edge=spec.get('edge')
   if edge:
    self.color(n,C+'EdgeParam/EdgeColor',edge['color']); s(n,C+'EdgeParam/EdgeThreshold',edge.get('threshold',.1)); s(n,C+'EdgeParam/EdgeColorScaling',edge.get('scaling',2))
  falloff=spec.get('falloff')
  if falloff:
   F=A+'FalloffParam/'; s(n,F+'Enabled',True); s(n,F+'ColorBlendType',falloff.get('blend','Add')); s(n,F+'Pow',falloff.get('pow',2))
   self.color(n,F+'BeginColor',falloff['begin']); self.color(n,F+'EndColor',falloff['end'])
  if spec.get('soft'):
   # Soft particle: fade where the quad meets opaque geometry (depth buffer) instead of a hard intersection line.
   P=A+'SoftParticleParams/'; s(n,P+'Enabled',True); s(n,P+'Distance',spec['soft'])
  collide=spec.get('collide')
  if collide:
   # Ground plane collision: sparks and debris bounce and skid instead of sinking through the floor.
   C='CollisionsValues/'; s(n,C+'IsGroundCollisionEnabled',True); s(n,C+'Height',collide.get('height',0))
   s(n,C+'WorldCoordinateSyatem','World' if collide.get('world',True) else 'Local')
   r(n,C+'Bounce',collide.get('bounce',.4)); r(n,C+'Friction',collide.get('friction',.3)); r(n,C+'LifetimeReductionPerCollision',collide.get('reduction',.3))
  spawn=spec.get('spawn')
  if spawn:
   # With rotate=True particle velocity is expressed in the spawn direction: +Y points away from the centre.
   G='GenerationLocationValues/'; s(n,G+'Type',spawn['shape']); s(n,G+'EffectsRotation',spawn.get('rotate',True))
   if spawn['shape']=='Sphere':
    r(n,G+'Sphere/Radius',spawn.get('radius',0)); r(n,G+'Sphere/RotationX',spawn.get('rot_x',[-90,90])); r(n,G+'Sphere/RotationY',spawn.get('rot_y',[0,360]))
   elif spawn['shape']=='Circle':
    r(n,G+'Circle/Radius',spawn.get('radius',1)); s(n,G+'Circle/AxisDirection',spawn.get('axis','YAxis'))
    s(n,G+'Circle/Division',spawn.get('division',8)); s(n,G+'Circle/Type',spawn.get('order','Random'))
    r(n,G+'Circle/AngleStart',spawn.get('angle_start',0)); r(n,G+'Circle/AngleEnd',spawn.get('angle_end',360)); r(n,G+'Circle/AngleNoize',spawn.get('angle_noise',0))
   elif spawn['shape']=='Line':
    self.vector(n,G+'Line/PositionStart',spawn['start'],True); self.vector(n,G+'Line/PositionEnd',spawn['end'],True)
    s(n,G+'Line/Division',spawn.get('division',8)); s(n,G+'Line/Type',spawn.get('order','Random')); r(n,G+'Line/PositionNoize',spawn.get('noise',0))
  for slot,force in enumerate(spec.get('forces',[]),1):
   if slot>4:raise ValueError('Effekseer supports four local force fields per node')
   L=f'LocationAbsValues/LocalForceField{slot}/'; s(n,L+'Type',force['type']); s(n,L+'Power',force.get('power',1))
   if force['type']=='Gravity':self.vector(n,L+'Gravity/Gravity',force['gravity'])
   if force['type']=='Turbulence':
    s(n,L+'Turbulence/FieldScale',force.get('scale',4)); s(n,L+'Turbulence/Octave',force.get('octave',1)); s(n,L+'Turbulence/TurbulenceType',force.get('kind','Simple'))
   if force['type']=='Vortex':s(n,L+'Vortex/VortexType',force.get('kind','ConstantAngle'))
   if force['type']=='AttractiveForce':
    s(n,L+'AttractiveForce/Control',force.get('control',1)); s(n,L+'AttractiveForce/MinRange',force.get('min_range',0)); s(n,L+'AttractiveForce/MaxRange',force.get('max_range',0))
   if 'position' in force:self.vector(n,L+'Position',force['position'])
   if 'rotation' in force:self.vector(n,L+'Rotation',force['rotation'])
  inherit=spec.get('inherit')
  if inherit:
   # Children default to following the parent every frame; 'WhenCreating' leaves a trail of independent particles.
   for key,field in [('location','CommonValues/LocationEffectType'),('rotation','CommonValues/RotationEffectType'),('scale','CommonValues/ScaleEffectType'),('color','RendererCommonValues/ColorInheritType')]:
    if key in inherit:s(n,field,inherit[key])
  if spec.get('infinite'):s(n,'CommonValues/MaxGeneration/Infinite',True)
  if spec.get('remove_with_parent'):s(n,'CommonValues/Removal/WhenParentIsRemoved',True)
  if spec.get('z_sort'):s(n,'DepthValues/ZSort',spec['z_sort'])
  if spec.get('priority') is not None:s(n,'DepthValues/DrawingPriority',spec['priority'])
 def layer(self,spec,parent='node/root'):
  if spec.get('material_profile'):
   import json
   profile=json.loads(Path(spec['material_profile']).read_text())
   spec={**profile,**spec}
  errors=validate_layer(spec,recursive=False)
  if errors:raise ValueError('; '.join(errors))
  n=self.session.add_node(parent,spec['name'])
  s=self.scalar; r=self.rand; v=self.vector; c=self.color
  life=spec.get('life',24)
  s(n,'CommonValues/MaxGeneration/Value',spec.get('count',1))
  r(n,'CommonValues/Life',life)
  generation='CommonValues/Generation' if 'CommonValues/Generation/GenerationTime/Max' in self.schema else 'CommonValues'
  r(n,generation+'/GenerationTime',max(.00001,spec.get('interval',0)))
  r(n,generation+'/GenerationTimeOffset',spec.get('delay',0))
  s(n,'RendererCommonValues/AlphaBlend',spec.get('blend','Add'))
  s(n,'RendererCommonValues/ZTest',spec.get('z_test',False))
  s(n,'RendererCommonValues/ZWrite',False)
  s(n,'RendererCommonValues/EmissiveScaling',spec.get('emissive',1.0))
  s(n,'RendererCommonValues/FadeInType','Use' if spec.get('fade_in',1)>0 else 'None')
  s(n,'RendererCommonValues/FadeIn/Frame',spec.get('fade_in',1))
  s(n,'RendererCommonValues/FadeOutType','WithinLifetime')
  s(n,'RendererCommonValues/FadeOut/Frame',spec.get('fade_out',max(2,(min(life) if isinstance(life,(list,tuple)) else life)*.65)))
  renderer=spec.get('renderer','Sprite'); s(n,'DrawingValues/Type',renderer)
  color=spec.get('color',[255,255,255,255])
  if renderer in ['Sprite','Model']:
   if spec.get('color_curve'):
    s(n,'DrawingValues/ColorAll/Type','FCurve')
    for ch,val in zip('RGBA',color):
     keys=spec['color_curve'].get(ch,[[0,val],[100,val]])
     self.curve(n,'DrawingValues/ColorAll/FCurve/FCurve/'+ch,keys)
   elif spec.get('color_end'):
    s(n,'DrawingValues/ColorAll/Type','Easing')
    c(n,'DrawingValues/ColorAll/Easing/Start',color,True); c(n,'DrawingValues/ColorAll/Easing/End',spec['color_end'],True)
   else: c(n,'DrawingValues/ColorAll/Fixed',color)
  if renderer=='Sprite': s(n,'DrawingValues/Sprite/Billboard',spec.get('billboard','RotatedBillboard'))
  if renderer=='Sprite' and spec.get('pivot')=='bottom':
   # Quad spans y 0..1 instead of -0.5..0.5, so scaling grows it up from its base (spikes, bolts, pillars).
   s(n,'DrawingValues/Sprite/Position','Fixed')
   for corner,(x,y) in zip(['LL','LR','UL','UR'],[(-.5,0),(.5,0),(-.5,1),(.5,1)]):
    s(n,f'DrawingValues/Sprite/Position_Fixed_{corner}/X',x); s(n,f'DrawingValues/Sprite/Position_Fixed_{corner}/Y',y)
  if renderer=='Model':
   s(n,'DrawingValues/Model/Billboard',spec.get('billboard','Fixed'))
   s(n,'DrawingValues/Model/Culling',spec.get('culling','Double'))
   if spec.get('procedural_model'):
    from .models import assign_procedural_model
    assign_procedural_model(self.session,n,spec['procedural_model'])
   elif spec.get('model'):
    self.session.import_model(spec['model'],n+'/DrawingValues/Model/Model')
  if renderer=='Ring':
   ring=spec.get('ring',{})
   s(n,'DrawingValues/Ring/VertexCount',ring.get('vertices',64))
   s(n,'DrawingValues/Ring/Billboard',spec.get('billboard','Billboard'))
   # outer/inner are [radius,height]; {'start':..,'end':..} animates them over the particle life.
   for part,default in [('Outer',spec.get('ring_outer',[.5,0])),('Inner',spec.get('ring_inner',[.43,0]))]:
    value=ring.get(part.lower(),default)
    if isinstance(value,dict):
     s(n,f'DrawingValues/Ring/{part}',"Easing")
     for axis,a,b in zip('XY',value['start'],value['end']):
      r(n,f'DrawingValues/Ring/{part}_Easing/Start/{axis}',a); r(n,f'DrawingValues/Ring/{part}_Easing/End/{axis}',b)
    else:
     for axis,a in zip('XY',value):s(n,f'DrawingValues/Ring/{part}_Fixed/Location/{axis}',a)
   s(n,'DrawingValues/Ring/CenterRatio_Fixed',ring.get('center_ratio',.5))
   for part,key in [('OuterColor','outer_color'),('CenterColor','center_color'),('InnerColor','inner_color')]:
    c(n,f'DrawingValues/Ring/{part}_Fixed',ring.get(key,color if part=='CenterColor' else [*color[:3],0]))
   # A crescent whose start/end angles ease over life gives a swept arc (slash, sweep, opening seal).
   if 'angle_start' in ring or 'angle_end' in ring:
    s(n,'DrawingValues/Ring/RingShape/Type','Crescent')
    for part,key,default in [('StartingAngle','angle_start',0),('EndingAngle','angle_end',360)]:
     value=ring.get(key,default)
     if isinstance(value,(list,tuple)):
      s(n,f'DrawingValues/Ring/RingShape/Crescent/{part}','Easing')
      r(n,f'DrawingValues/Ring/RingShape/Crescent/{part}_Easing/Start',value[0]); r(n,f'DrawingValues/Ring/RingShape/Crescent/{part}_Easing/End',value[1])
      s(n,f'DrawingValues/Ring/RingShape/Crescent/{part}_Easing/Type',ring.get('angle_easing','EaseOutCubic'))
     else:s(n,f'DrawingValues/Ring/RingShape/Crescent/{part}_Fixed',value)
    fade=ring.get('angle_fade',[0,0])
    s(n,'DrawingValues/Ring/RingShape/Crescent/StartingFade',fade[0]); s(n,'DrawingValues/Ring/RingShape/Crescent/EndingFade',fade[1])
  if renderer=='Ribbon':
   s(n,'DrawingValues/Ribbon/ViewpointDependent',True)
   c(n,'DrawingValues/Ribbon/ColorAll_Fixed',color)
  if renderer=='Track':
   for part in ['TrailColorLeft','TrailColorLeftMiddle','TrailColorCenter','TrailColorCenterMiddle','TrailColorRight','TrailColorRightMiddle']:
    c(n,'DrawingValues/'+part+'/Fixed',color)
   for part,size in zip(['For','Middle','Back'],spec.get('track_size',[])):s(n,f'DrawingValues/Track/TrackSize{part}_Fixed',size)
  if spec.get('texture'):self.uv(n,'RendererCommonValues/ColorTexture',spec['texture'],spec.get('uv_scroll'))
  if spec.get('material'):
   s(n,'RendererCommonValues/Material',spec['material'])
  if spec.get('distortion') is not None:
   s(n,'RendererCommonValues/DistortionIntensity',spec['distortion'])
  self.advanced(n,spec)
  travel=spec.get('travel')
  if travel:
   # Eased displacement: with an ease-out type particles burst fast and then hang, which PVA cannot do
   # (Effekseer drag only damps force-field velocity, not PVA velocity).
   s(n,'LocationValues/Type','Easing')
   v(n,'LocationValues/Easing/Start',travel.get('start',spec.get('position',[0,0,0])),True); v(n,'LocationValues/Easing/End',travel['end'],True)
   s(n,'LocationValues/Easing/Type',travel.get('easing','EaseOutQuartic'))
  else:
   s(n,'LocationValues/Type','PVA')
   v(n,'LocationValues/PVA/Location',spec.get('position',[0,0,0]),True)
   v(n,'LocationValues/PVA/Velocity',spec.get('velocity',[0,0,0]),True)
   v(n,'LocationValues/PVA/Acceleration',spec.get('acceleration',[0,0,0]),True)
  s(n,'RotationValues/Type','PVA')
  v(n,'RotationValues/PVA/Rotation',spec.get('rotation',[0,0,0]),True)
  v(n,'RotationValues/PVA/Velocity',spec.get('spin',[0,0,0]),True)
  start=spec.get('scale_start',[1,1,1]); end=spec.get('scale_end',start)
  if isinstance(start,(int,float)):start=[start]*3
  if isinstance(end,(int,float)):end=[end]*3
  if 'size' in spec:
   # Uniform size keeps randomised particles undistorted; size_curve is absolute scale over 0-100% life.
   if spec.get('size_curve'):
    s(n,'ScalingValues/Type','SingleFCurve'); self.curve(n,'ScalingValues/SingleFCurve/S',[[f,x*spec['size']] for f,x in spec['size_curve']])
   else:
    s(n,'ScalingValues/Type','SingleEasing'); r(n,'ScalingValues/SingleEasing/Start',spec['size']); r(n,'ScalingValues/SingleEasing/End',spec.get('size_end',spec['size']))
    s(n,'ScalingValues/SingleEasing/Type',spec.get('easing','EaseOutCubic'))
  elif spec.get('scale_curve'):
   s(n,'ScalingValues/Type','FCurve')
   for axis,factor in zip('XYZ',start):
    self.curve(n,'ScalingValues/FCurve/FCurve/'+axis,[[f,x*factor] for f,x in spec['scale_curve']])
  else:
   s(n,'ScalingValues/Type','Easing')
   v(n,'ScalingValues/Easing/Start',start,True); v(n,'ScalingValues/Easing/End',end,True)
   s(n,'ScalingValues/Easing/Type',spec.get('easing','EaseOutCubic'))
  if spec.get('bind'):self.bind(n,spec['bind'])
  for field,value in spec.get('properties',{}).items(): self.set(n,field,value)
  for field,keys in spec.get('curves',{}).items(): self.curve(n,field,keys)
  for child in spec.get('children',[]):self.layer(child,n)
  return n

def compile_effect(recipe,source_path,runtime_path=None):
 """Build a fresh document from a JSON recipe; repeat calls replace only that output."""
 if not recipe.get('layers'):raise ValueError('Recipe needs at least one layer')
 errors=[e for layer in recipe['layers'] for e in validate_layer(layer)]
 if errors:raise ValueError('Invalid recipe layers: '+'; '.join(errors))
 source=Path(source_path).resolve()
 if source.suffix!='.efkefc':raise ValueError('Source must end in .efkefc')
 session=EffectSession.new()
 for node in reversed(session.node_list()):session.remove_node(node['path'])
 session.save(source)
 builder=LayerBuilder(session)
 for layer in recipe['layers']:builder.layer(layer)
 core=load_core(); core.EndFrame=int(recipe.get('duration',1)*60); core.IsLoop=bool(recipe.get('loop',False))
 core.Global.RandomSeed.SetValue(int(recipe.get('seed',1729)))
 # Default values of the game inputs (@In0..@In3) that bind equations read: what the Effekseer editor previews with and
 # what a new Godot handle starts from until Vfx.gd pushes the game's values.
 inputs=[float(v) for v in recipe.get('inputs') or []]
 if len(inputs)>4:raise ValueError('Effekseer has four game inputs (@In0..@In3)')
 for slot,value in enumerate(inputs):list(core.Dynamic.Inputs.Values)[slot].Input.SetValue(value)
 session.save()
 # Round-trip through the official reader before runtime export.
 session=EffectSession.open(source)
 # Reject silent writes to legacy/import-only fields that disappear on save.
 expected={write['property']:write['after'] for write in builder.writes}
 for path,value in expected.items():
  actual=session.property_get(path)
  equal=math.isclose(actual,value,rel_tol=1e-5,abs_tol=1e-6) if isinstance(value,(int,float)) and not isinstance(value,bool) else actual==value
  if not equal:raise RuntimeError(f'Property did not survive Core save/open: {path}: {value!r} -> {actual!r}')
 for path,code in builder.bindings:
  equation=session._object_at_path(path).DynamicEquation.Value
  if equation is None or equation.Code.Value!=code:raise RuntimeError(f'Dynamic equation did not survive Core save/open: {path}')
 saved=[float(i.Input.Value) for i in load_core().Dynamic.Inputs.Values][:len(inputs)]
 if not all(math.isclose(a,b,rel_tol=1e-5,abs_tol=1e-6) for a,b in zip(saved,inputs)):raise RuntimeError(f'Game input defaults did not survive Core save/open: {inputs} -> {saved}')
 if runtime_path:session.export(runtime_path)
 return {'source':str(source),'runtime':str(runtime_path) if runtime_path else None,'nodes':session.node_list(),'writes':len(builder.writes)}
