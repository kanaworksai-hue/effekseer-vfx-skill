"""VFX_Poison_Cloud: Poison splash and lingering cloud played where VFX_Projectile_Poison arrives.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 green=(120,220,60,255); dark=(40,90,25,200); acid=(210,255,90,255); hot=(240,255,205,255); bruise=(52,26,62,170)
 GROUND=-.93   # floor below the body anchor (Lab: body sits 0.95 m up)
 return effect('Poison_Cloud','Poison Cloud','status','poison',1.75,[
  # Ground: an uneven acid pool spreads under the target, rim glowing, and bubbles keep breaking out of it.
  # An irregular painted puff laid flat is a ragged puddle; a soft circle reads as a clean disc however it is eroded.
  decal('Acid pool','T_Smoke02',(55,120,28,210),4.6,life=101,delay=3,blend='Blend',position=[.1,GROUND+.02,0],size_curve=[[0,.2],[12,.85],[100,1.05]],
   cutoff=dict(start=.05,end=.5,easing='Linear'),fade_in=0,fade_out=34,angle=20),
  decal('Pool sheen','T_Smoke02',(160,255,70,120),3.6,life=80,delay=4,position=[.2,GROUND+.03,.1],size_curve=[[0,.2],[12,.85],[100,1.05]],
   cutoff=dict(start=.25,end=.8,easing='Linear'),fade_in=0,fade_out=30,emissive=1.3,angle=140),
  sprite('Acid glints','T_Star01',(245,255,220,255),count=10,interval=8,delay=6,life=[8,12],size=.3,size_curve=[[0,.2],[30,1],[100,0]],rotation=[0,0,[0,90]],
   position=[[-.9,1.5],[GROUND+.1,GROUND+.5],[-.8,.8]],fade_in=0,fade_out=3,emissive=2.0),
  # Splash: a white-hot acid flash and three broken strokes thrown at random tilts.
  # Contact is a ragged acid splat, not the shared four-point flare.
  sprite('Splash shadow','T_Explosion01',(65,22,78,240),life=10,delay=0,size=1.65,size_curve=[[0,1],[30,1.05],[100,1.15]],position=[0,-.12,0],rotation=[0,0,25],blend='Blend',cutoff=dict(start=0,end=.75,easing='Linear'),fade_in=0,fade_out=5),
  glow('Splash core',(245,255,225,255),.32,life=3,delay=1,fade_out=2,emissive=1.8),
  sprite('Splash flash','T_Explosion01',(215,255,130,255),life=3,delay=1,size=.9,size_curve=[[0,.5],[30,1],[100,1.15]],rotation=[0,0,25],fade_in=0,fade_out=2,emissive=2.0),
  wisps('Splash strokes',acid,1.0,count=3,width=.3,sweep=(0,120),life=10,delay=1,size=(.8,1.2),emissive=1.6),
  sprite('Burst puff','T_Explosion01',(105,190,45,255),color_end=dark,count=2,delay=1,life=[18,24],size=[.65,.9],size_end=[1.0,1.3],easing='EaseOutQuartic',blend='Blend',
   spawn=dict(shape='Sphere',radius=[.1,.3]),rotation=[0,0,[-180,180]],alpha_texture='T_NoiseTile01',cutoff=dict(start=0,end=.9,easing='EaseInQuadratic'),fade_in=0,fade_out=5),
  glow('Sick glow',(140,255,60,45),1.8,life=50,size_curve=[[0,.3],[10,1],[100,1.1]],fade_in=2,fade_out=30),
  # Value structure: a bruised purple underside first, then fumes that cool from acid yellow-green to murky green
  # to purple-grey, piled low and downwind (+X) instead of a round ball.
  smoke('Bruise smoke',(84,42,100,215),count=6,size=(.9,1.3),grow=1.5,life=(44,58),delay=5,interval=5,spawn=dict(shape='Sphere',radius=[.2,1.0],rot_x=[-80,0]),speed=(0,0),rise=-.0003,position=[.4,-.55,0]),
  smoke('Lingering fumes',(150,230,70,150),count=9,size=(.4,.9),grow=1.4,life=(42,54),delay=6,interval=4,spawn=dict(shape='Sphere',radius=[.3,1.3],rot_x=[-70,10]),speed=(0,0),rise=-.0005,position=[.5,-.35,0],
   color_curve=ramp((0,(185,245,95,190)),(25,(110,160,50,180)),(45,(100,92,110,170)),(100,(72,62,82,0)))['color_curve']),
  # Heavy fog rolls out along the floor from under the pool.
  dict(name='Ground pivot',renderer='None',life=105,position=[0,GROUND+.2,0],children=[
   smoke('Low fog',(80,105,70,210),count=8,size=(1.2,1.8),grow=1.6,life=(46,60),delay=4,interval=5,spawn=dict(shape='Circle',radius=[.5,1.0],rotate=True,division=8),
    travel=dict(end=[[1.5,2.4],0,0],easing='EaseOutCubic'),rise=0),
   sprite('Pool bubbles','T_Bubble01',acid,count=24,delay=8,interval=3,life=[14,22],size=[.06,.14],size_end=[.1,.2],spawn=dict(shape='Circle',radius=[.2,1.3],rotate=False),
    travel=dict(end=[[-.05,.05],[.15,.5],[-.05,.05]],easing='EaseOutCubic'),billboard='Billboard',fade_in=3,fade_out=2,emissive=1.4)]),
  # Droplets: heavy acid drops thrown through the target along the shot, which land and splat.
  sprite('Acid drops','T_Dot01',acid,color_end=green,count=14,delay=1,life=[22,32],size=[.07,.14],forces=[dict(type='Gravity',gravity=[0,-.004,0])],
   collide=dict(height=.02,bounce=[.05,.15],friction=.8,reduction=.5),fade_in=0,fade_out=4,emissive=1.4,**spray([[.3,2.4],[.4,1.8],[-1.0,1.0]])),
  radial_sparks('Acid spatter',8,acid,color_end=green,distance=(.6,1.4),life=(12,20),length=(.25,.5),width=.09,delay=1,gravity=.0022),
  motes('Spores',14,acid,color_end=green,life=(34,48),distance=(.3,1.0),delay=10,interval=3,size=(.06,.12),radius=(.3,1.1),turbulence=.004),
  motes('Purple spores',6,(185,110,255,255),color_end=(90,40,130,255),life=(30,44),distance=(.3,1.0),delay=16,interval=6,size=(.05,.1),radius=(.3,1.2),turbulence=.004),
 ],attach='body',peak=.05,impact=.2,light=(.6,1,.3),delivery=dict(kind='projectile',projectile='VFX_Projectile_Poison'),
 design='A white-hot acid splash with broken strokes and heavy drops thrown through the target that land; an uneven pool spreads underneath with a glowing rim and bubbles breaking out of it; fumes cool from acid green to murky purple-grey over a bruised underside, piled low and downwind, while heavy fog rolls out along the floor and spores drift.')
