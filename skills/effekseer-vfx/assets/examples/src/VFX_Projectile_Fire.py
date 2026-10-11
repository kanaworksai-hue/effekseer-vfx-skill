"""VFX_Projectile_Fire: Fireball projectile; paired with VFX_Fire_Explosion on arrival.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 white=(255,250,220,255); yellow=(255,200,80,255); orange=(255,120,30,255); red=(200,40,10,255)
 return effect('Projectile_Fire','Fireball','projectile','fire',1.2,[
  # Trails only play the dense first ~10 frames of the smoke sheet; its torn last frames vanish against the dark stage.
  sustain(smoke('Smoke trail',(125,110,100,235),size=(.35,1.0),grow=2.4,life=(38,42),flipbook=dict(x=4,y=4,frame_length=4,loop='Once'),speed=(0,.002),rise=0,radius=(0,.1),
   travel=dict(end=[0,[.5,.9],0],easing='EaseOutCubic'),inherit=TRAIL,delay=3,color_curve=ramp((0,(125,110,100,235)),(60,(118,104,95,200)),(100,(65,60,56,0)))['color_curve']),3),
  # Fire peeling off the path: small turbulent billows that rise, cool and burn through with a hot rim.
  sustain(sprite('Flame trail','T_ExplosionSheet01',**ramp((0,(255,220,140,255)),(25,orange),(60,(200,55,15,200)),(100,(90,28,12,0))),life=[18,26],size=[.45,.95],size_end=[.15,.3],
   easing='EaseInQuadratic',rotation=[0,0,[-180,180]],flipbook=dict(x=4,y=4,frame_length=2,loop='Once',start=[3,7]),
   spawn=dict(shape='Sphere',radius=[0,.12],rotate=False),travel=dict(end=[0,[.45,.8],0],easing='EaseOutCubic'),inherit=TRAIL,
   alpha_texture='T_NoiseTile01',cutoff=dict(start=0,end=.8,easing='EaseInQuadratic'),edge=dict(color=[255,90,20,255],threshold=.06,scaling=2),fade_in=0,fade_out=6),1.5),
  # Broken flame strokes wrapping the ball at a new tilt every emission: it churns instead of reading as a disc.
  sustain(wisps('Flame wisps',(255,130,40,255),.6,count=1,width=.22,sweep=(0,150),life=8,flow=-.1,emissive=1.1),2),
  sustain(motes('Embers',1,orange,color_end=red,size=(.05,.11),life=(18,28),distance=(.1,.45),radius=(0,.15),rise=.0006,turbulence=.001,inherit=TRAIL,spawn=dict(shape='Sphere',radius=[0,.08],rotate=False),travel=dict(end=[[-.7,-.3],[.35,.65],[-.2,.2]],easing='EaseOutCubic')),2.5),
  # Flung sparks: a few long thin streaks thrown back and up off the head.
  sustain(radial_sparks('Flung sparks',1,white,color_end=orange,life=(7,10),length=(.4,.8),width=.05,inherit=TRAIL,emissive=2.2,
   **spray([[-1.4,-.5],[.1,.7],[-.4,.4]])),3),
  sustain(glow('Heat bloom',(255,90,20,65),.85,life=8),3),
  sustain(heat_haze('Heat wake',1.4,life=18,strength=.35,inherit=TRAIL,fade_in=2,fade_out=12),3),
  # Comet: a looping flame flipbook laid along the flight, tongues streaming back behind the boiling ball.
  # Comet tail: the same turbulent flipbook stretched back along the flight, so the head reads as a teardrop.
  sustain(sprite('Comet tail','T_ExplosionSheet01',(255,150,50,255),color_end=(255,80,20,255),life=6,scale_start=[[1.5,1.8],[.6,.75],1],rotation=[0,0,[-10,10]],position=[-.75,0,0],
   flipbook=dict(x=4,y=4,frame_length=1,loop='Once',start=[3,8]),alpha_texture='T_NoiseTile01',cutoff=dict(start=.05,end=.4,easing='Linear'),
   fade_in=1,fade_out=3,emissive=.85),2),
  # Each head sprite plays a few dense frames of the explosion sheet from a random start, so the ball boils.
  sustain(sprite('Fireball','T_ExplosionSheet01',(255,170,60,255),color_end=(255,90,20,255),life=[5,7],scale_start=[[1.15,1.35],[.75,.9],1],rotation=[0,0,[-25,25]],spin=[0,0,[-3,3]],
   flipbook=dict(x=4,y=4,frame_length=1,loop='Once',start=[2,6]),
   fade_in=0,fade_out=3,emissive=.8),1),
  # White-hot core stretched along the flight line: a streak, not a dot.
  sustain(sprite('Hot core','T_Glow01',white,life=6,scale_start=[.55,.17,1],billboard='Billboard',fade_in=0,fade_out=4,emissive=1.25),2),
 ],attach='projectile',peak=.05,flight=.45,delivery=dict(kind='projectile'),
 design='A boiling fireball with a stretched turbulent comet tail, a stretched white core and broken flame strokes churning round it; sparks are flung back, flame tongues peel off and rise, embers drift, and graded smoke lingers on the path.')
