"""Composable layer primitives for effect recipes: `from vfxkit.primitives import *`.

Primitives return plain layer dicts for the effekseer_ai layer compiler. Units: life/delay in 60 FPS
frames, velocity in units per frame, angles in degrees, colours RGBA 0-255, curves in percent of life.
Textures are named by stem (`'T_Glow01'`) and resolved in the project's vfx/textures/processed/.
"""
from pathlib import Path
import math
from .paths import ROOT
T=ROOT/'vfx/textures/processed'
TEXTURE_KEYS=['texture','alpha_texture','distortion_texture','blend_texture']
WHITE=(255,255,255,255)

def tex(name):return str(T/f'{name}.png')
def is_path(value):
 """A texture already resolved to a file path (tex() returns native paths: backslashes on Windows), not a bare stem."""
 return '/' in value or '\\' in value
def fade(color,alpha=0):return [*color[:3],alpha]
def walk(layers):
 for layer in layers:
  yield layer
  yield from walk(layer.get('children',[]))

def sprite(name,texture='T_Glow01',color=WHITE,**kw):
 for key in TEXTURE_KEYS[1:]:
  if key in kw:kw[key]=tex(kw[key])
 return dict(name=name,texture=tex(texture),color=list(color),**kw)

def glow(name,color,size,life=10,delay=0,**kw):
 """Soft light bloom behind a shape: pops fast, then swells slightly while fading."""
 return sprite(name,'T_Glow01',color,life=life,delay=delay,size=size,size_curve=[[0,.25],[18,1],[100,1.25]],billboard='Billboard',fade_in=0,fade_out=life*.8) | kw

def shadow(name,color,size,life=12,delay=0,**kw):
 """Dark alpha backing behind an additive core: peaks a frame or two after the white flash (white -> dark -> fade),
 so the hot core keeps its value contrast even on a bright background."""
 return sprite(name,'T_SoftCircle',color,life=life,delay=delay,size=size,size_curve=[[0,.6],[20,1],[100,1.15]],billboard='Billboard',blend='Blend',
  fade_in=2,fade_out=life*.7) | kw

def flash(name,color,size,life=5,delay=0,angle=0,**kw):
 """One- to five-frame anamorphic star at the contact frame; sells the hit more than anything else."""
 return sprite(name,'T_Flare01',color,life=life,delay=delay,size=size,size_curve=[[0,.55],[25,1],[100,.15]],rotation=[0,0,angle],fade_in=0,fade_out=life*.6,emissive=1.6) | kw

def radial_sparks(name,count,color,color_end=None,distance=(.8,2.2),life=(12,22),width=.1,length=(.35,.7),delay=0,gravity=0,turbulence=0,hemisphere=False,radius=(0,.08),**kw):
 """Motion-aligned streaks thrown from a sphere; eased travel makes them burst fast, then hang and droop."""
 forces=[]
 if gravity:forces.append(dict(type='Gravity',gravity=[0,-gravity,0]))
 if turbulence:forces.append(dict(type='Turbulence',power=turbulence,scale=6))
 return sprite(name,'T_Spark01',color,color_end=list(color_end or color),count=count,life=list(life),delay=delay,billboard='DirectionalBillboard',
  spawn=dict(shape='Sphere',radius=list(radius),rot_x=[0,90] if hemisphere else [-90,90]),travel=dict(end=[0,list(distance),0],easing='EaseOutQuartic'),
  scale_start=[width,list(length),1],scale_end=[width*.3,length[0]*.2,1],easing='EaseInQuadratic',forces=forces,fade_in=0,fade_out=5,emissive=1.5) | kw

def spark_burst(name,count,hot,cool,distance=(1.0,2.6),life=(12,22),length=(.4,.9),delay=0,gravity=.0015,floor=None,**kw):
 """Three spark tiers instead of one uniform spray (AAA hits read as fast/medium/heavy at once):
 a few long thin streaks that are gone in 6-10 frames, the main body, and ~20% heavy sparks that are larger,
 fall harder and, given `floor` (world height), bounce and skid on the ground."""
 d0,d1=distance
 heavy=dict(collide=dict(height=floor,bounce=[.25,.45],friction=.4,reduction=.35)) if floor is not None else {}
 return [
  radial_sparks(name+' streaks',max(3,count//3),WHITE,color_end=hot,distance=(d0*1.3,d1*1.4),life=(6,10),length=(length[0]*1.5,length[1]*1.6),width=.05,delay=delay,fade_out=3,emissive=2.2,**kw),
  radial_sparks(name,count,hot,color_end=cool,distance=distance,life=life,length=length,delay=delay,gravity=gravity,**kw),
  radial_sparks(name+' heavy',max(2,count//5),hot,color_end=cool,distance=(d0*.7,d1*.9),life=(life[0]+6,life[1]+8),length=(length[0]*.6,length[1]*.7),width=.15,delay=delay,gravity=gravity*2.2,**heavy,**kw),
 ]

def motes(name,count,color,color_end=None,size=(.1,.22),life=(20,40),distance=(.3,1.2),delay=0,interval=0,rise=0,turbulence=.003,radius=(0,.3),hemisphere=False,**kw):
 """Small round glints that drift: embers, frost, magic dust. Uniform random size keeps them round."""
 forces=[dict(type='Turbulence',power=turbulence,scale=5)]
 if rise:forces.append(dict(type='Gravity',gravity=[0,rise,0]))
 return sprite(name,'T_Glow01',color,color_end=list(color_end or color),count=count,life=list(life),delay=delay,interval=interval,billboard='Billboard',
  spawn=dict(shape='Sphere',radius=list(radius),rot_x=[0,90] if hemisphere else [-90,90]),travel=dict(end=[0,list(distance),0],easing='EaseOutCubic'),
  size=list(size),size_end=0,easing='EaseInCubic',forces=forces,fade_in=1,fade_out=6,emissive=1.5) | kw

def shock_ring(name,color,radius,life=14,delay=0,thickness=.35,ground=False,**kw):
 """Expanding wave: the node scale eases out while the band thins from the inside."""
 return dict(name=name,renderer='Ring',color=list(color),life=life,delay=delay,billboard='Fixed' if ground else 'Billboard',rotation=[-90 if ground else 0,0,0],
  ring=dict(outer=[1,0],inner=dict(start=[1-thickness,0],end=[.97,0]),center_ratio=.8,outer_color=fade(color,color[3]//2),center_color=list(color),inner_color=fade(color)),
  size=radius,size_curve=[[0,.12],[35,.72],[100,1]],fade_in=0,fade_out=life*.7) | kw

def slash_arc(name,color,radius=1.5,width=.55,sweep=(-20,200),life=11,delay=0,tilt=(0,0,0),texture='T_Trail01',depth=0,flow=0,**kw):
 """Swept crescent: the head races round the arc, the tail follows, the band thins and dissolves.

 depth lifts the outer edge and drops the inner one so the band is a shallow cone with perspective thickness
 instead of a flat decal; flow slides the erosion noise along the arc so the dissolving tail streams after the head."""
 a0,a1=sweep
 extra=dict(alpha_scroll=[flow,0]) if flow else {}
 return dict(name=name,renderer='Ring',texture=tex(texture),color=list(color),life=life,delay=delay,billboard='Fixed',rotation=list(tilt),
  ring=dict(vertices=96,outer=[radius,depth],inner=dict(start=[radius-width,-depth*.6],end=[radius-width*.25,-depth*.15]),center_ratio=.6,
   outer_color=list(color),center_color=list(color),inner_color=list(color),angle_start=[a0,a0+(a1-a0)*.4],angle_end=[a0+(a1-a0)*.12,a1],angle_easing='EaseOutQuartic',angle_fade=[25,4]),
  alpha_texture=tex('T_NoiseStreak01'),cutoff=dict(start=0,end=.75,easing='EaseInQuadratic'),fade_in=0,fade_out=life*.5,wrap='Clamp',**extra) | kw

def wisps(name,color,radius,count=4,width=.3,sweep=(0,150),life=(14,22),delay=0,interval=0,tilt=((-90,90),(0,360),(0,360)),size=(.7,1.3),
  flow=-.05,broken=.1,texture='T_WispTrail01',**kw):
 """Broken energy strokes: `count` partial arcs, each at its own random tilt, radius and length, so several strands
 swirl and cross instead of one clean ring. The erosion starts above zero, so every arc is torn from its first frame."""
 a0,a1=sweep; peak=max(life) if isinstance(life,(list,tuple)) else life
 return dict(name=name,renderer='Ring',texture=tex(texture),color=list(color),count=count,interval=interval,life=list(life) if isinstance(life,(list,tuple)) else life,delay=delay,
  billboard='Fixed',rotation=[list(t) if isinstance(t,(list,tuple)) else t for t in tilt],size=list(size) if isinstance(size,(list,tuple)) else size,
  ring=dict(vertices=72,outer=[radius,0],inner=dict(start=[radius-width,0],end=[radius-width*.3,0]),center_ratio=.45,
   outer_color=fade(color,color[3]//3),center_color=list(color),inner_color=fade(color),angle_start=[a0,a0+(a1-a0)*.5],angle_end=[a0+(a1-a0)*.2,a1],angle_easing='EaseOutCubic',angle_fade=[20,6]),
  alpha_texture=tex('T_NoiseStreak01'),alpha_scroll=[flow,0],cutoff=dict(start=broken,end=.8,easing='EaseInQuadratic'),fade_in=1,fade_out=peak*.45,wrap='Clamp',emissive=2.0) | kw

def decay(layer,color,lag=6,stretch=2.2,name=None):
 """Emissive-to-smoke afterimage: the same stroke, alpha-blended grey, a few frames late and much longer lived, so the
 light goes out first and the shape lingers as smoke instead of the whole effect vanishing at once."""
 life=layer.get('life',20); life=[round(l*stretch) for l in life] if isinstance(life,(list,tuple)) else round(life*stretch)
 out={k:v for k,v in layer.items() if k not in('emissive','color_curve','color_end','edge')}
 if 'ring' in out:out['ring']=out['ring']|dict(outer_color=fade(color,color[3]//3),center_color=list(color),inner_color=fade(color))
 scroll=layer.get('alpha_scroll')
 return out|dict(name=name or layer['name']+' smoke',color=list(color),blend='Blend',delay=layer.get('delay',0)+lag,life=life,
  fade_in=3,fade_out=(max(life) if isinstance(life,list) else life)*.6,**({'alpha_scroll':[scroll[0]*.4,scroll[1]*.4]} if scroll else {}))

def slice_line(name,color,length,width=.06,angle=0,life=12,delay=0,**kw):
 """A very long, very thin accent line (aspect > 40:1) that shoots out to full length and thins away: the single
 most expensive-looking stroke in a release. `width` is the visible thickness (T_Streak01's core is 8% of the card)."""
 return sprite(name,'T_Streak01',color,life=life,delay=delay,rotation=[0,0,angle],scale_start=[length*.35,width/.08,1],scale_end=[length*1.15,width/.08*.15,1],
  easing='EaseOutQuartic',fade_in=0,fade_out=life*.7,emissive=2.4) | kw

def spray(end,radius=.1):
 """Directional burst: particles fly to a random point in the world-space box `end` ([[x0,x1],[y0,y1],[z0,z1]]) instead of
 a symmetric sphere, so debris and sparks follow the hit through the target. Use with travel easing on the layer."""
 return dict(spawn=dict(shape='Sphere',radius=[0,radius],rotate=False),travel=dict(end=[list(a) for a in end],easing='EaseOutCubic'))

def debris(name,count,end,color=(118,104,96,255),size=(.12,.3),life=(30,46),gravity=.004,floor=None,delay=0,**kw):
 """Dark tumbling rock chunks thrown along `end` (see spray): value contrast against the light, and they land."""
 hit=dict(collide=dict(height=floor,bounce=[.15,.35],friction=.6,reduction=.2)) if floor is not None else {}
 return sprite(name,'T_Shard01',color,color_end=[int(c*.6) for c in color[:3]]+[255],count=count,life=list(life),delay=delay,blend='Blend',
  rotation=[0,0,[-180,180]],spin=[0,0,[-12,12]],size=list(size),size_end=[size[0]*.8,size[1]*.8],forces=[dict(type='Gravity',gravity=[0,-gravity,0])],
  fade_in=0,fade_out=6,**spray(end),**hit) | kw

def orbit_band(name,color,inner_color,outer_color,radius,width,life,tilt=(-72,0,0),arc=(0,360),flow=-.03,delay=0,**kw):
 """A band lying in a tilted 3D plane (accretion disk, orbiting rune ring): an ellipse in perspective, with noise
 streaming round it. arc=(-90,90) is the far half (0 points up the tilted plane, away from the camera) and (90,270)
 the near half, so a core drawn between the two halves sits inside the band instead of on top of a sticker."""
 return dict(name=name,renderer='Ring',color=list(color),life=life,delay=delay,billboard='Fixed',rotation=list(tilt),
  ring=dict(vertices=96,outer=[radius,0],inner=[radius-width,0],center_ratio=.3,outer_color=list(outer_color),center_color=list(color),inner_color=list(inner_color),
   **({} if tuple(arc)==(0,360) else dict(angle_start=arc[0],angle_end=arc[1]))),
  alpha_texture=tex('T_NoiseStreak01'),alpha_scroll=[flow,0],fade_in=4,fade_out=life*.3) | kw

def smoke(name,color,count=5,size=(.5,.9),grow=1.9,life=(30,48),delay=0,interval=0,speed=(.005,.02),rise=.0004,radius=(0,.25),texture='T_SmokeSheet01',**kw):
 """Alpha-blended puffs that grow and slow down. The default painted flipbook billows, curls and tears itself
 apart over life (a single still puff only scales), so the noise dissolve is light; still textures erode harder."""
 sheet='Sheet' in texture  # every T_*Sheet* texture is a 4x4 flipbook; drawn whole it would show 16 puffs
 extra=dict(flipbook=dict(x=4,y=4,frame_length=max(1,round(max(life)/16)),loop='Once'),cutoff=dict(start=0,end=.3,easing='EaseInCubic')) if sheet else dict(cutoff=dict(start=0,end=.7,easing='EaseInQuadratic'))
 return sprite(name,texture,color,color_end=fade(color),count=count,life=list(life),delay=delay,interval=interval,blend='Blend',billboard='RotatedBillboard',
  spawn=dict(shape='Sphere',radius=list(radius)),velocity=[0,list(speed),0],rotation=[0,0,[-180,180]],spin=[0,0,[-.6,.6]],
  size=list(size),size_end=[size[0]*grow,size[1]*grow],easing='EaseOutCubic',forces=[dict(type='Gravity',gravity=[0,rise,0])],
  alpha_texture='T_NoiseTile01',fade_in=2,fade_out=10,**extra) | kw

def flame(name,color,color_end,size,life,count=1,**kw):
 """Fire tongues without a drawn flame: the painted turbulent explosion flipbook grows up from its base, cools
 white -> colour -> colour_end and is eaten away by noise with a hot rim. A sprite with a
 recognisable flame silhouette (the old T_FlameSheet01 / T_Flame02) reads as clip art and was dropped for that."""
 peak=max(life) if isinstance(life,(list,tuple)) else life
 cool=[(a+b)//2 for a,b in zip(color[:3],color_end[:3])]+[200]
 return sprite(name,'T_ExplosionSheet01',**ramp((0,(255,245,215,255)),(18,color),(55,cool),(100,list(color_end))),count=count,life=life,size=size,
  billboard='YAxisFixed',pivot='bottom',flipbook=dict(x=4,y=4,frame_length=max(1,round(peak/16)),loop='Once'),
  # No UV distortion: on a 4x4 sheet it is measured in whole-texture UV, so .12 shifts half a cell and samples the
  # neighbouring frames, cutting the fire into hard-edged blocks.
  alpha_texture='T_NoiseTile01',cutoff=dict(start=.04,end=.5,easing='EaseInQuintic'),edge=dict(color=[255,90,20,255],threshold=.06,scaling=2),
  fade_in=1,fade_out=8,emissive=1.5) | kw

def ramp(*stops):
 """Colour over life as a gradient: ramp((0,white),(30,orange),(100,red)) -> color_curve; percent of life, RGBA 0-255.

 A two-colour lerp reads as a tint; fire that cools white -> yellow -> orange -> red -> smoke needs 3+ stops."""
 return dict(color=list(stops[0][1]),color_curve={ch:[[p,c[i]] for p,c in stops] for i,ch in enumerate('RGBA')})

def billow(name,stops,size,life,count=1,frames=16,texture='T_ExplosionSheet01',grid=(4,4),**kw):
 """Painted flipbook billow played once over the particle's life: the shape itself rolls, opens and breaks up."""
 kw={'blend':'Add',**kw}
 return sprite(name,texture,**ramp(*stops),count=count,life=life,size=size,flipbook=dict(x=grid[0],y=grid[1],frame_length=max(1,round((max(life) if isinstance(life,(list,tuple)) else life)/frames)),loop='Once'),
  rotation=[0,0,[-180,180]],billboard='RotatedBillboard',fade_in=0,fade_out=4) | kw

def heat_haze(name,size,life=30,delay=0,strength=.6,**kw):
 """Screen-space refraction (BackDistortion): bends whatever is behind it, the cue that sells heat and force."""
 return sprite(name,'T_DistortHaze01',WHITE,material='BackDistortion',distortion=strength,life=life,delay=delay,size=size,size_curve=[[0,.5],[25,1],[100,1.2]],
  billboard='Billboard',uv_scroll=[0,.006],fade_in=3,fade_out=life*.6) | kw

def distortion_ring(name,radius,life=14,delay=0,strength=1.0,ground=False,**kw):
 """Refractive shockwave: an expanding ring that pushes the background outward instead of drawing a line."""
 return sprite(name,'T_DistortRing01',WHITE,material='BackDistortion',distortion=strength,life=life,delay=delay,size=radius*2,size_curve=[[0,.15],[40,.75],[100,1]],
  billboard='Fixed' if ground else 'Billboard',rotation=[-90 if ground else 0,0,0],fade_in=0,fade_out=life*.7) | kw

def decal(name,texture,color,size,life,delay=0,spin=0,**kw):
 """Flat ground-plane sprite (rune, crack, scorch); depth-tested so characters stand on top of it."""
 # Extra fields go through sprite() so texture names (alpha_texture, ...) resolve to files like every other layer.
 base=dict(billboard='Fixed',rotation=[-90,0,kw.pop('angle',0)],spin=[0,0,spin],position=[0,.05,0],z_test=True,
  fade_in=kw.pop('fade_in',4),fade_out=kw.pop('fade_out',life*.4))
 return sprite(name,texture,color,life=life,delay=delay,size=size,**(base|kw))

def standing(name,texture,color,size,life,delay=0,**kw):
 """Upright camera-facing sprite that grows from its base."""
 return sprite(name,texture,color,life=life,delay=delay,billboard='YAxisFixed',pivot='bottom',scale_start=[size[0],size[1],1],fade_in=kw.pop('fade_in',0),fade_out=kw.pop('fade_out',life*.4)) | kw

def mesh(name,shape,color,life,radius=1,depth=2,texture=None,sides=40,rings=12,model=None,**kw):
 """Procedural Sphere/Cone/Cylinder shell, usually textured with a scrolling gradient.

 sides=6 gives a hexagonal crystal; model={...} passes extra procedural-model fields (ShapeNoise/*, Radius2...)."""
 spec={'Name':name,'Shape/PrimitiveType':shape,'Shape/Radius':radius,'Mesh/Divisions/X':sides,'Mesh/Divisions/Y':rings}
 # Cylinders/cones span DepthMin..DepthMax along their axis; 0..depth makes them stand on their origin.
 if shape!='Sphere':spec.update({'Shape/Depth':depth,'Shape/DepthMin':0,'Shape/DepthMax':depth})
 if 'radius2' in kw:spec['Shape/Radius2']=kw.pop('radius2')
 spec.update(model or {})
 layer=dict(name=name,renderer='Model',procedural_model=spec,color=list(color),life=life,fade_in=kw.pop('fade_in',3),fade_out=kw.pop('fade_out',life_max(dict(life=life))*.5))
 if texture:layer['texture']=tex(texture)
 for key in TEXTURE_KEYS[1:]:
  if key in kw:kw[key]=tex(kw[key])
 return layer | kw

def crystal(name,color,height,radius,life,edge=WHITE,**kw):
 """Faceted ice/arcane crystal: a six-sided cone mesh with a cellular texture and bright fresnel edges, so it has
 real silhouettes from every angle instead of a painted spike that always faces the camera."""
 # A Cone opens toward +Y (tip at the base), so the crystal is a six-sided Cylinder tapering to a near point instead.
 return mesh(name,'Cylinder',color,life,radius=radius,radius2=radius*.04,depth=height,sides=6,rings=2,texture='T_NoiseTile02',uv_scroll=[.002,.004],culling='Double',
  falloff=dict(begin=[*color[:3],40],end=list(edge),pow=2.2,blend='Add'),**kw)

def shell(name,color,radius,life=14,delay=0,pow=.35,**kw):
 """3D shock bubble: a sphere whose fresnel rim is the only visible part, expanding with ease-out. Reads as a
 volume from any angle where a camera-facing ring reads as a flat hoop."""
 # Front faces only: with both sides drawn, the inner back faces also read as 'edge' and fill the bubble in.
 return mesh(name,'Sphere',color,life,radius=1,sides=48,rings=24,scale_start=[radius]*3,scale_curve=[[0,.15],[35,.75],[100,1]],culling='Front',delay=delay,
  falloff=dict(begin=[0,0,0,0],end=[255,255,255,255],pow=pow,blend='Mul'),alpha_texture='T_NoiseTile01',cutoff=dict(start=0,end=.75,easing='EaseInQuadratic'),
  fade_in=0,fade_out=life*.7) | kw   # the rim tears open as it expands instead of fading as one balloon

def shell_fragments(name,color,radius,delay=80,life=28):
 """Six partial spherical sheets separate at expiry; geometry supplies gaps without shader assumptions."""
 pieces=[]
 for i in range(6):
  angle=math.radians(i*60+20)
  pieces.append(mesh(f'{name} {i+1}','Sphere',color,life,radius=1,sides=12,rings=16,
   model={'Mesh/AngleBeginEnd/X':0.0,'Mesh/AngleBeginEnd/Y':40.0,'Shape/DepthMin':-.7,'Shape/DepthMax':.85},
   scale_start=[radius]*3,scale_end=[radius*1.06]*3,rotation=[0,i*60,0],delay=delay,
   travel=dict(end=[math.cos(angle)*.65,.2 if i%2 else -.2,math.sin(angle)*.65],easing='EaseOutCubic'),
   spin=[(-1 if i%2 else 1)*.8,(-1 if i%2 else 1)*1.2,0],culling='Double',z_test=True,
   falloff=dict(begin=[20,70,150,30],end=[225,245,255,255],pow=.35,blend='Mul'),
   color_curve=ramp((0,color),(18,(160,215,255,230)),(65,(70,120,215,200)),(100,(0,0,0,0)))['color_curve'],
   fade_in=1,fade_out=10,emissive=2.0))
 return pieces

def tilted_ring(name,color,radius,life=14,delay=0,tilt=(-70,0,0),thickness=.3,**kw):
 """Shockwave ring lying in a 3D plane (ground, or across the line of a hit): an ellipse in perspective."""
 return shock_ring(name,color,radius,life=life,delay=delay,thickness=thickness,billboard='Fixed',rotation=list(tilt)) | kw

def column(name,color,radius,height,life,delay=0,scroll=(.003,-.02),**kw):
 """Volumetric light shaft: streaks scroll up a cylinder, a static gradient fades the top, fresnel softens the sides."""
 return mesh(name,'Cylinder',color,life,radius=radius,depth=height,texture='T_NoiseStreak02',uv_scroll=list(scroll),delay=delay,culling='Double',
  alpha_texture='T_GradientV01',alpha_wrap='Clamp',falloff=dict(begin=[255,255,255,255],end=[255,255,255,0],pow=1.6,blend='Mul')) | kw

def effect(id,name,category,element,duration,layers,attach='impact',peak=.1,impact=0,light=(1,.85,.6),loop=False,design='',delivery=None,flight=None,arc=None,
  hold=None,inputs=None,scale=None):
 """impact (0..1) and light drive the lab's flash and camera kick at peak; they are stage hints, not Effekseer data.

 delivery tells a game (and the Lab) how the effect is performed: {'kind':'self'} on the caster, 'melee' on the
 target at the strike, 'projectile' (with the projectile effect id) on the target when the shot arrives,
 'targeted' called down on the target, 'area' centred on a caster that hits everything around it, 'beam' fired
 from the caster's mouth or weapon at a point the game keeps updating (see beam()).
 Projectiles declare flight (seconds of the reference flight) and optional arc (metres of lift at mid-flight);
 beams declare hold (seconds the reference beam fires). Their `infinite` layers emit until the game releases them.
 inputs are the default values of the game inputs @In0..@In3 that `bind` equations read (a beam's length and power).
 scale converts a recipe written at the Lab's character scale to a larger world: 'giant', 'kaiju', a number or
 {'world','time','budget'} (see vfxkit.scale and references/scale.md).
 """
 entry=dict(id='VFX_'+id,name=name,category=category,element=element,duration=duration,loop=loop,attach=attach,peak=peak,impact=impact,light=list(light),seed=1729,layers=layers,design=design)
 for key,value in [('delivery',delivery),('flight',flight),('arc',arc),('hold',hold),('inputs',list(inputs) if inputs is not None else None)]:
  if value is not None:entry[key]=value
 if scale is not None and scale!='character':
  from .scale import apply
  entry=apply(entry,scale)
 return entry

def life_max(layer):
 life=layer.get('life',24);return max(life) if isinstance(life,(list,tuple)) else life

def lifetime(layer,start=0,release=0):
 """Latest frame at which this layer or any child can still be alive.

 `infinite` layers emit until the projectile is released, `release` frames after the effect starts.
 """
 life=life_max(layer)
 born=start+(max(release,layer.get('delay',0)) if layer.get('infinite') else layer.get('delay',0)+(layer.get('count',1)-1)*layer.get('interval',0))
 # Effekseer times a child's generation from its parent instance's creation, not from its death.
 return max([born+life]+[lifetime(child,born) for child in layer.get('children',[])])

def budget(layer):
 # A sustained emitter holds about life/interval instances at once, whatever its nominal count.
 count=math.ceil(life_max(layer)/max(layer.get('interval',1),1e-6)) if layer.get('infinite') else layer.get('count',1)
 return count*(1+sum(budget(child) for child in layer.get('children',[])))

# ---------------------------------------------------------------- recipe helpers

POP=[[0,.4],[18,1],[100,1.1]]          # snap to size, then drift
# Hold solid, then erode through the alpha texture. Dissolve thresholds are Easings over the particle's life (an FCurve
# threshold does not animate in the Godot runtime, and Core clamps thresholds to 0..1): the ease-in keeps the shape
# nearly whole for the first third, then eats it away.
DISSOLVE=dict(start=0,end=.9,easing='EaseInQuadratic')
# How a game performs each effect (manifest `delivery`); the Lab stages the exchange from it.
SELF=dict(kind='self'); MELEE=dict(kind='melee'); TARGETED=dict(kind='targeted'); BEAM=dict(kind='beam')
# Trail layers keep the world position they were born at, so a moving projectile leaves them behind.
TRAIL=dict(location='WhenCreating',rotation='WhenCreating',scale='WhenCreating')

# Degrees T_Slash02's painted arc bows toward; `vfx texture-info T_Slash02` measures 108. Re-measure a replacement.
SLASH02_BULGE=105

def slash_set(colors,roll,sweep=(110,260),radius=1.5,offset=(0,0,.5),lean=-18,delay=1,life=14,texture='T_Trail01'):
 """Wide dim afterimage + saturated body + thin white-hot edge: one blade read at three widths.

 The ring faces the camera (leaned back by `lean`) and is rolled by `roll`; its centre is shifted so the
 middle of the swept arc passes through the anchor plus `offset`. Ring angles: 0 is up, 90 is left.
 """
 after,body,edge=colors
 mid=math.radians(sum(sweep)/2); r=math.radians(roll); x,y=-math.sin(mid),math.cos(mid)
 x,y=x*math.cos(r)-y*math.sin(r),x*math.sin(r)+y*math.cos(r)
 position=[offset[0]-radius*x,offset[1]-radius*y*math.cos(math.radians(lean)),offset[2]-radius*y*math.sin(math.radians(lean))]
 common=dict(tilt=(lean,0,roll),sweep=sweep,position=position)
 size=radius*2.3
 return [
  # The afterimage lags two frames and sits slightly inside the blade, so the cut reads as a fast motion smear.
  slash_arc('Afterimage',after,radius=radius*.94,width=radius*.8,life=life+3,delay=delay+2,texture=texture,depth=radius*.06,**common),
  slash_arc('Blade body',body,radius=radius,width=radius*.55,life=life,delay=delay,emissive=1.5,texture=texture,depth=radius*.1,flow=-.04,**common),
  slash_arc('Hot edge',edge,radius=radius*1.01,width=radius*.18,life=life-4,delay=delay,texture='T_Trail02',emissive=2.2,depth=radius*.1,**common),
  # The same sweep bends the background behind the blade.
  slash_arc('Refraction arc',WHITE,radius=radius*1.02,width=radius*.5,life=life,delay=delay,texture='T_DistortHaze01',material='BackDistortion',distortion=.7,cutoff=None,**common),
  # A hand-painted crescent held for a few frames gives the cel-animation "cut" that a swept ring alone lacks.
  # It lies in the blade's own plane (Fixed, same lean), so it tilts with the swing instead of facing the camera.
  sprite('Cel crescent','T_Slash02',edge,color_end=body,delay=delay+1,life=8,size=size,size_curve=[[0,.8],[20,1],[100,1.06]],billboard='Fixed',
   rotation=[lean,0,math.degrees(math.atan2(y,x))-SLASH02_BULGE],
   position=[offset[0]-x*size*.3,offset[1]-y*size*.3*math.cos(math.radians(lean)),offset[2]-y*size*.3*math.sin(math.radians(lean))+.1],
   alpha_texture='T_NoiseStreak01',cutoff=DISSOLVE,fade_in=0,fade_out=3,emissive=1.6),
 ]

def sustain(layer,interval):
 """Projectile emitter: one instance every `interval` frames until the game releases the handle on arrival."""
 return layer | dict(infinite=True,interval=interval,count=1)

def swing(layers,yaw,pitch=0):
 """Turn a blade's layers into a 3D swing plane: a pivot at the anchor yaws (and pitches) the whole set, so the arc is
 an ellipse cutting through space rather than a crescent painted on the screen. Children are timed from the pivot."""
 return [dict(name='Swing plane',renderer='None',life=max(lifetime(l) for l in layers),rotation=[pitch,yaw,0],children=list(layers))]

def contrast_pair(layer, dark_color=(32, 24, 20, 210)):
    """One fixed sprite plus a matching Blend underlay; rejects independently randomized geometry.

    This is a construction starting point, not a claim of independently reviewed quality.
    The renderer and background still decide whether an underlay or a front cut is useful.
    """
    from effekseer_ai.authoring import validate_layer
    import copy
    problems = validate_layer(layer)
    if problems:
        raise ValueError('; '.join(problems))
    if layer.get('renderer', 'Sprite') != 'Sprite':
        raise ValueError('contrast_pair demonstrates Sprite only; design Ring/Model pairing explicitly')
    if type(layer.get('count', 1)) is not int or layer.get('count', 1) != 1 or layer.get('infinite') or layer.get('children') or layer.get('spawn') or layer.get('forces'):
        raise ValueError('Use one deterministic particle without spawn/forces/children')
    if any(layer.get(k) for k in ('properties', 'curves', 'material_profile')):
        raise ValueError('Raw properties/curves or profiles can hide random geometry; use explicit layer fields')
    for field in ('life', 'size', 'size_end', 'delay', 'interval'):
        if field in layer and type(layer[field]) not in (int, float):
            raise ValueError(f'{field} must be fixed for a matched pair')
    for field in ('rotation', 'position', 'spin', 'velocity', 'acceleration', 'scale_start', 'scale_end'):
        if field in layer and any(type(v) not in (int, float) for v in layer[field]):
            raise ValueError(f'{field} must have fixed components')
    for field in ('start', 'end'):
        if field in layer.get('travel', {}) and any(type(v) not in (int, float) for v in layer['travel'][field]):
            raise ValueError('travel must have fixed components')
    if type(layer.get('flipbook', {}).get('start', 0)) is not int:
        raise ValueError('flipbook start must be fixed')
    if len(dark_color) != 4 or any(type(v) is not int or not 0 <= v <= 255 for v in dark_color):
        raise ValueError('dark_color must be integer RGBA 0..255')
    bright = copy.deepcopy(layer)
    dark = copy.deepcopy(layer)
    for key in ('emissive', 'color_curve', 'color_end', 'edge'):
        dark.pop(key, None)
    dark.update(name=layer['name']+' value underlay', blend='Blend', color=list(dark_color))
    if layer.get('color_curve'):
        alpha=layer['color_curve'].get('A', [[0,layer.get('color',[255]*4)[3]], [100,layer.get('color',[255]*4)[3]]])
        dark['color_curve']={ch:[[0,dark_color[i]],[100,dark_color[i]]] for i,ch in enumerate('RGB')}
        dark['color_curve']['A']=[[frame,value*dark_color[3]/255] for frame,value in alpha]
    return [dark, bright]

# ---------------------------------------------------------------- beams and charges

# Game inputs a beam reads (Vfx.beam() keeps them current): @In0 is the length to the end point in world units,
# @In1 the power 0..1 that widens the beam as it ignites and narrows it as it dies.
BEAM_LENGTH='@In0'; BEAM_POWER='@In1'

def beam_inputs(length,power=1.0):
 """Default inputs of a beam recipe (effect(..., inputs=beam_inputs(8))): what the editor and the Lab show
 before a game sets them."""
 return [length,power,0,0]

def held(layer,interval):
 """Sustained cross-fade: a new instance every `interval` frames, each fading in and out over `interval`, so two
 always overlap and their (linear) fades sum to a constant: a steady body with no pop and no loop seam. The game's
 release stops emission and the last instances fade out within 2 x interval frames."""
 return layer|dict(infinite=True,count=1,interval=interval,life=2*interval,fade_in=interval,fade_out=interval)

def _beam_strip(name,texture,color,width,interval,**kw):
 # Axial billboard along local +Y: the quad turns about the beam axis to face the camera; bind stretches it to the
 # end point every frame and scales its width with power.
 return held(sprite(name,texture,color,billboard='YAxisFixed',pivot='bottom',bind={'scale':[[width,BEAM_POWER],BEAM_LENGTH,1]},**kw),interval)

def beam(name,core,body,rim,width=.5,interval=6,flow=.05,origin=1.4,end=1.8,sparks=6,haze=.6,steam=None,steam_life=(50,70),scorch=None,scorch_life=40):
 """Sustained energy beam along local +Y from the effect's origin to a point @In0 away (Vfx.beam() aims the
 handle and updates the length every frame, so the game can sweep it). Built from the outside in:

 - haze: screen refraction around the beam (haze=0 drops it);
 - rim: wide coloured glow, body: saturated beam with noise streaks flowing outward, core: thin white-hot line.
   Every strip uses the T_BeamSection01 cross-section, so the beam keeps full strength to its very end;
 - origin and end flashes: glow + flare at the mouth and at the hit point, scaled by power;
 - end sparks (and optional steam, an RGBA colour) thrown back from the hit point every `interval` frames, and an
   optional scorch (RGBA): glowing marks that stay where the beam touched and cool from that colour through orange to
   dark red over `scorch_life` frames. They
   inherit the hit point only at birth, so a sweeping beam leaves a trail of them behind and they carry the effect's
   tail after the release (an independent review flagged an empty stage once the beam shut off).

 Pair it with effect(..., delivery=BEAM, hold=<seconds the Lab fires>, inputs=beam_inputs(<length>)) and a one-shot
 ignition (flash at frame 0-1) for the contact. Widths are Lab metres; scale='kaiju' converts them."""
 def point(label,texture,color,size,at,**kw):
  return held(sprite(label,texture,color,billboard='Billboard' if texture!='T_Flare01' else 'RotatedBillboard',
   bind={'position':[0,at,0],'scale':[[size,BEAM_POWER],[size,BEAM_POWER],1]},**kw),interval)
 layers=[]
 if haze:layers.append(_beam_strip(name+' haze','T_DistortHaze01',WHITE,width*3,interval,material='BackDistortion',distortion=haze,uv_scroll=[0,-.01]))
 layers+=[
  # Emissive steps keep the value layering of a hit: only the core burns past the bloom threshold; the body stays
  # saturated and the rim is a dim halo. With body/rim at 1.2+ the overlapping additive strips tonemap to white and
  # the beam loses its colour under the Lab's bloom (measured on the kaiju atomic beam).
  _beam_strip(name+' rim','T_BeamSection01',rim,width*2.6,interval,alpha_texture='T_NoiseStreak02',alpha_scroll=[0,-flow*.6],emissive=.7),
  # The body keeps most of its opacity (blend_texture modulates, not erodes): a noise alpha at full strength halves
  # it and the colour disappears between the white core and the background.
  _beam_strip(name+' body','T_BeamSection01',body,width,interval,blend_texture='T_NoiseStreak02',blend_scroll=[0,-flow],blend_type='Add',emissive=1.1),
  _beam_strip(name+' core','T_BeamSection01',core,width*.18,interval,emissive=1.8),
  point(name+' origin glow','T_Glow01',body,origin,0,emissive=1.0),
  point(name+' origin flare','T_Flare01',core,origin*.8,0,emissive=1.8),
  point(name+' end glow','T_Glow01',body,end,BEAM_LENGTH,emissive=1.0),
  point(name+' end flare','T_Flare01',core,end*.7,BEAM_LENGTH,emissive=2.0),
 ]
 children=[]
 if sparks:children.append(radial_sparks(name+' end sparks',sparks,core,color_end=body,distance=(end*.5,end*1.3),life=(10,16),delay=0,gravity=.0015,
  inherit=TRAIL,hemisphere=False))
 # The steam's flipbook plays slower than its life, so it never reaches the sheet's nearly empty last cells: it is
 # still a visible, thinning plume when its life ends (a review found the stage empty while the steam was "alive").
 if steam:children.append(smoke(name+' end steam',steam,count=1,size=(end*.5,end*.7),grow=2.4,life=steam_life,speed=(.01,.02),rise=.0006,inherit=TRAIL,
  soft=end*.2,color_end=fade(steam,steam[3]//2),flipbook=dict(x=4,y=4,frame_length=max(1,round(max(steam_life)/12)),loop='Once')))
 if scorch:children.append(sprite(name+' scorch','T_Glow01',**ramp((0,scorch),(30,(255,150,70,scorch[3])),(70,(150,50,20,scorch[3]*2//3)),(100,(60,20,10,0))),
  life=scorch_life,size=end*.8,size_curve=[[0,1],[100,.75]],billboard='Billboard',inherit=TRAIL,fade_in=0,fade_out=scorch_life*.5,emissive=1.3))
 if children:
  # The emitter of the spray: an invisible point riding the end of the beam.
  layers.append(dict(name=name+' hit point',renderer='None',infinite=True,count=1,interval=interval,life=2*interval,
   bind={'position':[0,BEAM_LENGTH,0]},children=children))
 return layers

def _aim(start,end):
 """Velocity that points a DirectionalBillboard sprite from start toward end without visibly moving it."""
 d=[b-a for a,b in zip(start,end)]; n=math.sqrt(sum(c*c for c in d)) or 1
 return [c/n*1e-4 for c in d],n

def charge_chain(name,anchors,color,hot,step=4,until=None,width=.35,glow=.6,texture='T_ArcStrand01',restrike=3,delay=0):
 """Electric arcs that light up along a chain of anchor points one after another (dorsal plates charging from the
 tail to the head, capacitor coils, a ley line): node i ignites at delay + i*step frames with a glow, then an arc
 jumps to node i+1 and keeps re-striking until `until` (default: a beat after the last node lights).

 anchors are local positions (Lab metres before scale). Each arc is a painted strand on an axial billboard aimed
 along its segment (DirectionalBillboard with an imperceptible velocity), re-struck every `restrike` frames
 alternately mirrored, so the bolt keeps changing shape instead of sliding. A charge is a self effect: the game plays
 it on the caster before the beam."""
 if len(anchors)<2:raise ValueError('charge_chain needs at least two anchors')
 last=delay+(len(anchors)-1)*step; until=until if until is not None else last+18
 layers=[]
 for i,at in enumerate(anchors):
  born=delay+i*step; span=max(4,until-born)
  layers.append(sprite(f'{name} node {i+1}','T_Glow01',color,delay=born,life=span,size=glow,size_curve=[[0,1.8],[12,1],[100,1.1]],
   billboard='Billboard',position=list(at),fade_in=0,fade_out=min(6,span*.3),emissive=2.0))
  # A small coloured pop, not a star flare (a T_Flare01 star on the first plate read as generic magic before any arc
  # showed) and not white: the release at the end of the chain must stay the brightest frame.
  layers.append(sprite(f'{name} node {i+1} spark','T_Glow01',color,delay=born,life=5,size=glow*1.1,size_curve=[[0,1.4],[100,.4]],billboard='Billboard',
   position=list(at),fade_in=0,fade_out=4,emissive=1.4))
  if i+1==len(anchors):continue
  # The arc jumps on the frame its plate lights, so the very first frames already read as electricity climbing.
  velocity,length=_aim(at,anchors[i+1]); start=born; strikes=max(1,(until-start)//restrike)
  for side,mirror in ((0,1),(1,-1)):
   if strikes-side<1:continue
   layers.append(sprite(f'{name} arc {i+1}{"ab"[side]}',texture,hot,color_end=color,count=(strikes-side+1)//2,interval=restrike*2,
    delay=start+side*restrike,life=restrike+1,billboard='DirectionalBillboard',pivot='bottom',position=list(at),velocity=velocity,
    scale_start=[width*mirror,length,1],fade_in=0,fade_out=1,emissive=2.6))
 return layers

__all__=[name for name in dir() if not name.startswith('_') and name not in ('Path','math','ROOT','T','is_path')]+['math']
