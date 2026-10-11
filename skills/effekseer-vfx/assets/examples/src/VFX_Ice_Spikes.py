"""VFX_Ice_Spikes: Ground ice eruption played where VFX_Projectile_Ice arrives.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 white=(240,252,255,255); cyan=(130,215,255,255); deep=(50,120,255,255)
 grow=[[0,0],[10,1.12],[18,.97],[26,1],[70,1],[88,.85],[100,.1]]
 # Faceted crystal meshes that punch up through the frost: real silhouettes from any angle, not painted cards.
 def spikes(tag,height,radius,delay,**kw):
  return crystal(tag,(125,210,255,245),height,radius,40,edge=(190,235,255,230),delay=delay,scale_start=[1,1,1],scale_curve=grow,
   alpha_texture='T_NoiseTile02',cutoff=dict(start=0,end=.95,easing='EaseInQuartic'),fade_in=0,fade_out=4,emissive=.85) | dict(falloff=dict(begin=[155,215,255,235],end=[205,240,255,245],pow=.35,blend='Mul'),culling='Front') | kw
 # Prism fringe on the cold wave: the same broken stroke in three hues, a few centimetres apart (ice's complementary accent).
 prism=[wisps(f'Cold wave {tag}',color,2.6,count=1,width=.25,sweep=(-30,230),life=14,delay=delay,tilt=(-90,0,0),size=1,position=[dx,.08,0],broken=.08,flow=-.06,texture='T_Trail02')
  for tag,color,dx,delay in [('R',(255,140,190,150),-.06,8),('G',(150,255,220,150),0,8),('B',(130,170,255,190),.06,9)]]
 return effect('Ice_Spikes','Ice Spikes','element','ice',1.35,[
  # Frost: a torn, uneven patch with bright cracks running through it, not a clean disc.
  decal('Frost creep','T_Smoke02',cyan,4.2,life=60,size_curve=[[0,.1],[12,.8],[30,1],[100,1.03]],color_end=fade(deep),cutoff=dict(start=.05,end=.5,easing='Linear'),fade_in=0,fade_out=30,angle=60),
  decal('Frost cracks','T_Crack01',(200,240,255,220),4.0,life=58,delay=3,size_curve=[[0,.3],[14,1],[100,1.02]],color_end=fade(deep),fade_in=0,fade_out=26,emissive=1.3,angle=25),
  decal('Frost glow','T_Glow01',(60,150,255,130),4.6,life=55,delay=2),
  # A tight core cluster leaning apart, a scatter of uneven crystals round it, and a ripple of crystals erupting in
  # sequence along the shot (+X), shrinking as they go.
  spikes('Core crystals',3.0,.42,6,count=3,interval=.5,rotation=[[-16,16],[0,360],[-16,16]],position=[[-.25,.25],0,[-.25,.25]]),
  # Scale curves need a fixed start scale, so size variety comes from two layers instead of a random scale.
  spikes('Outer crystals',1.9,.3,8,count=3,interval=.6,spawn=dict(shape='Circle',radius=[.6,1.3],division=3,order='Random',rotate=True,angle_noise=40),
   rotation=[[10,34],0,[-15,15]]),
  spikes('Outer shards',1.0,.2,9,count=5,interval=.8,spawn=dict(shape='Circle',radius=[.9,1.45],division=5,order='Random',rotate=True,angle_noise=40),
   rotation=[[22,48],0,[-18,18]]),
  spikes('Ripple crystals',1.1,.24,9,count=3,interval=3,spawn=dict(shape='Line',start=[.7,0,-.2],end=[1.6,0,.5],division=5,order='Random',rotate=False,noise=.4),
   rotation=[[-24,20],[0,360],[-50,-8]]),
  glow('Crystal glow',(80,170,255,80),2.4,life=40,delay=6,position=[0,1.2,0],size_curve=[[0,.3],[15,1],[100,.55]],color_curve=ramp((0,(80,170,255,80)),(25,(50,120,220,55)),(100,(25,65,150,0)))['color_curve'],fade_in=2,fade_out=16),
  # Contact: a sharp thin ice star tilted off-axis, distinct from the other elements' contacts.
  sprite('Eruption glint','T_Star01',WHITE,life=5,delay=8,size=3.4,size_curve=[[0,.5],[25,1],[100,.2]],rotation=[0,0,17],position=[0,1.3,.4],fade_in=0,fade_out=3,emissive=2.2),
  *prism,
  distortion_ring('Cold refraction',3.6,life=14,delay=8,strength=.8,ground=True,position=[0,.1,0]),
  # The hold is alive: thin halo rings climb the cluster and glints wink on the facets.
  *[shock_ring(f'Halo {i}',(210,240,255,200),r,life=20,delay=d,ground=True,thickness=.06,rotation=[-90+tilt,0,0],
     travel=dict(start=[0,.3,0],end=[0,h,0],easing='EaseOutCubic')) for i,(r,d,h,tilt) in enumerate([(1.1,14,2.4,8),(1.6,25,3.0,-6)])],
  sprite('Facet glints','T_Star01',WHITE,count=8,interval=5,delay=12,life=[8,12],size=.35,size_curve=[[0,.2],[30,1],[100,0]],rotation=[0,0,[0,90]],
   position=[[-.9,.9],[.6,2.6],[-.5,.5]],fade_in=0,fade_out=3,emissive=2.0),
  # Cold mist sinks and rolls outward along the floor.
  smoke('Frost mist',(165,212,255,160),count=8,size=(.8,1.2),grow=1.7,life=(30,40),delay=10,interval=4,spawn=dict(shape='Circle',radius=[.8,1.4],rotate=True,division=8),
   travel=dict(end=[[1.0,1.6],0,0],easing='EaseOutCubic'),rise=-.0002,position=[0,.25,0]),
  smoke('Kicked dust',(170,185,200,150),count=6,size=(.5,.8),grow=1.6,life=(26,36),delay=8,spawn=dict(shape='Circle',radius=[.6,1.0],rotate=True,division=6),
   travel=dict(end=[[.8,1.4],0,0],easing='EaseOutCubic'),rise=.0001,position=[0,.2,0]),
  debris('Frozen rubble',6,[[-.6,2.6],[.8,2.2],[-1.2,1.2]],color=(70,86,112,255),size=(.12,.24),life=(28,40),delay=8,floor=.02),
  motes('Ice dust',16,white,color_end=cyan,life=(26,50),distance=(.5,1.8),delay=8,hemisphere=True,size=(.07,.15),rise=.0002),
  # Pre-shatter tell: a two-frame glint over the cluster, then it breaks two frames later.
  flash('Crack glint',(220,245,255,255),3.2,life=3,delay=47,position=[0,1.5,.3],angle=30),
  crystal('Shatter shards',(80,170,255,170),1,.22,[16,28],edge=(180,230,255,200),count=5,delay=50,
   spawn=dict(shape='Sphere',radius=[.3,.9],rot_x=[5,90]),travel=dict(end=[0,[.8,2.0],0],easing='EaseOutCubic'),forces=[dict(type='Gravity',gravity=[0,-.002,0])],
   spin=[[-9,9],[-9,9],[-9,9]],scale_start=[[.4,.55],[.5,.8],[.4,.55]],scale_end=[.12,.2,.12],easing='EaseInCubic',fade_in=0,fade_out=5,emissive=1.0,
   collide=dict(height=.02,bounce=[.2,.35],friction=.5,reduction=.3)),
  sprite('Shard chips','T_IceShard01',(200,235,255,255),count=12,delay=50,life=[14,24],size=[.12,.24],rotation=[0,0,[-180,180]],spin=[0,0,[-12,12]],
   spawn=dict(shape='Sphere',radius=[.3,1.0],rot_x=[5,90]),travel=dict(end=[0,[1.0,2.4],0],easing='EaseOutCubic'),forces=[dict(type='Gravity',gravity=[0,-.003,0])],
   fade_in=0,fade_out=4,emissive=1.4),
 ],attach='ground',peak=.2,impact=.7,light=(.6,.85,1),delivery=dict(kind='projectile',projectile='VFX_Projectile_Ice'),
 design='Torn frost with bright cracks spreads on the ground; a leaning core cluster, an uneven scatter of crystals and a ripple of crystals erupting along the shot punch up with overshoot; a prism-fringed broken cold wave, rubble and dust; during the hold halo rings climb, glints wink and mist rolls out; a glint, then it cracks apart into large shards and chips.')
