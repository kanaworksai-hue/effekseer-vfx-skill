"""VFX_Fire_Explosion: Fire impact played where VFX_Projectile_Fire arrives.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 white=(255,250,225,255); yellow=(255,205,90,255); orange=(255,120,25,255); red=(200,40,10,255)
 GROUND=-.93   # floor below the body anchor (Lab: body sits 0.95 m up); the blast centres on the torso, not the head
 THROUGH=[[.4,3.2],[.4,2.6],[-1.3,1.3]]   # the shot travels +X: debris and sparks follow it through the target
 ground_arcs=[wisps('Ground lick A',(255,150,50,220),1.5,count=1,width=.5,sweep=(200,330),life=14,delay=7,tilt=(-90,0,0),size=1,position=[0,GROUND+.06,0],flow=-.05),
  wisps('Ground lick B',(255,190,90,200),2.1,count=1,width=.35,sweep=(20,150),life=18,delay=9,tilt=(-90,0,0),size=1,position=[0,GROUND+.06,0],flow=.05)]
 return effect('Fire_Explosion','Fire Explosion','element','fire',1.3,[
  decal('Scorch','T_Crack01',(36,24,18,180),3.4,life=48,delay=7,blend='Blend',position=[0,GROUND+.03,0],size_curve=[[0,.5],[8,1],[100,1.02]],fade_in=0,fade_out=26,angle=40),
  decal('Glowing cracks','T_Crack01',(255,100,25,255),3.4,life=34,delay=7,position=[0,GROUND+.04,0],size_curve=[[0,.5],[8,1],[100,1.02]],color_end=fade(red),fade_in=0,fade_out=24,emissive=1.6,angle=40),
  shadow('Dark backing',(40,18,10,150),5.0,life=22,delay=7),
  glow('Gather',(255,150,60,200),1.6,life=6,size_curve=[[0,1],[100,.15]],fade_in=2,fade_out=1),
  radial_sparks('Inward fuse',6,(255,170,75,255),color_end=(255,220,140,255),life=(7,7),width=.055,length=(.3,.5),
   spawn=dict(shape='Sphere',radius=[.7,1.0]),travel=dict(end=[0,[-1.0,-.7],0],easing='EaseInCubic'),fade_in=1,fade_out=2),
  flash('Detonation flash',white,6,life=3,delay=9),
  glow('Fire core',(255,205,90,200),3.0,life=5,delay=9,emissive=1.3),
  # The same billow, alpha-blended and dark, takes over as the fire burns out, so smoke grows out of the fireball.
  # Listed before the fire so the fire draws on top of it instead of being blotted out.
  billow('Smoke billow',[(0,(110,92,80,0)),(20,(140,125,112,240)),(60,(110,104,98,210)),(100,(75,75,80,0))],size=[2.0,3.8],life=[48,56],count=4,delay=14,interval=2,blend='Blend',
   flipbook=dict(x=4,y=4,frame_length=5,loop='Once'),spawn=dict(shape='Sphere',radius=[.2,.9]),velocity=[[.004,.01],[.018,.032],0],spin=[0,0,[-.4,.4]],fade_out=8,position=[.3,.1,0]),
  # Painted flipbook billows that cool as they roll, thrown off-centre along the shot so the ball is lopsided.
  billow('Fireball',[(0,(255,210,150,255)),(12,orange),(45,(235,65,10,240)),(75,(170,35,10,200)),(100,(60,10,5,0))],size=[1.6,3.4],life=[24,32],count=3,delay=6,interval=1,
   spawn=dict(shape='Sphere',radius=[.2,1.0]),position=[.35,0,0],velocity=[0,[.006,.02],0],spin=[0,0,[-.8,.8]],emissive=.85,
   alpha_texture='T_NoiseTile01',cutoff=dict(start=0,end=.8,easing='Linear'),alpha_scroll=[.018,-.01],edge=dict(color=[255,80,15,255],threshold=.05,scaling=2)),
  # A mushroom head that keeps climbing after the blast.
  billow('Mushroom',[(0,orange),(25,(235,80,20,240)),(70,(150,35,10,180)),(100,(50,15,8,0))],size=[1.6,2.2],life=[30,36],count=2,delay=12,interval=3,
   spawn=dict(shape='Sphere',radius=[0,.3],rotate=False),travel=dict(end=[[.3,.75],[1.6,2.1],[-.2,.2]],easing='EaseOutCubic'),emissive=.85,
   alpha_texture='T_NoiseTile01',cutoff=dict(start=0,end=.6,easing='EaseInQuadratic'),edge=dict(color=[255,80,15,255],threshold=.05,scaling=2)),
  *ground_arcs,*[decay(arc,(90,78,70,170),lag=5,stretch=2.0) for arc in ground_arcs],
  distortion_ring('Refraction wave',3.8,life=16,delay=6,strength=1.0),
  heat_haze('Heat haze',4.2,life=50,delay=8,strength=.5),
  flame('Ground licks',orange,fade(red),size=[.8,1.3],size_end=[.4,.6],count=5,delay=10,interval=2,life=[24,32],
   spawn=dict(shape='Circle',radius=[.6,1.5],division=5,order='Random',rotate=False),position=[0,GROUND,0],fade_in=1,fade_out=12),
  *spark_burst('Shrapnel sparks',20,white,(255,80,0,255),distance=(1.6,3.8),life=(18,36),length=(.5,1.2),delay=6,gravity=.0012,floor=.02),
  radial_sparks('Blow-through streaks',10,white,color_end=orange,life=(10,16),length=(.8,1.5),width=.07,delay=6,**spray([[2.2,4.6],[.2,2.0],[-1.2,1.2]])),
  debris('Char debris',8,THROUGH,color=(112,96,88,255),size=(.14,.3),life=(32,46),delay=6,floor=.02),
  smoke('Ground dust',(150,138,126,170),count=8,size=(.6,.9),grow=1.8,life=(22,28),delay=8,spawn=dict(shape='Circle',radius=[.8,1.3],rotate=True,division=8),
   travel=dict(end=[[1.2,2.0],0,0],easing='EaseOutCubic'),rise=.0001,position=[0,GROUND+.2,0]),
  motes('Rising embers',18,orange,color_end=(255,30,0,255),life=(30,48),distance=(.6,2.0),delay=9,rise=.0006,radius=(.2,.9)),
 ],attach='body',peak=.17,impact=1,light=(1,.6,.25),delivery=dict(kind='projectile',projectile='VFX_Projectile_Fire'),
 design='Inward gather, white detonation, a lopsided flipbook fireball thrown along the shot that rolls, cools white to red and burns open, a climbing mushroom head, two broken ground licks that go out as grey smoke, blow-through streaks, char debris that lands, a dust roll, glowing cracks over a dark scorch, ground flames, then the same billow as smoke.')
