"""VFX_Projectile_Dark: Shadow orb projectile; paired with VFX_Dark_Vortex on arrival.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 violet=(170,90,255,255); magenta=(225,120,255,255); pale=(235,215,255,255)
 return effect('Projectile_Dark','Shadow Orb','projectile','dark',.9,[
  # Wake: the light decays along the path into a visible grey smoke line that slowly closes in on itself.
  sustain(smoke('Shadow wake',(118,106,130,185),size=(.5,.75),grow=.45,life=(14,18),speed=(0,.002),rise=0,radius=(0,.1),inherit=TRAIL),2),
  # Wake: broken strokes left behind on the path, cooling from magenta to grey, instead of one ruled line.
  sustain(wisps('Wake arcs',magenta,.5,count=1,width=.16,sweep=(0,140),life=18,flow=-.04,inherit=TRAIL,emissive=1.6,
   color_curve=ramp((0,(235,150,255,255)),(30,(170,90,230,230)),(65,(115,100,128,170)),(100,(80,72,90,0)))['color_curve']),2),
  sustain(glow('Violet halo',(140,60,255,65),1.35,life=9),3),
  # Broken wisp strokes at a new random tilt every emission: about four cross at once, never one clean disk.
  sustain(wisps('Wisp arcs',magenta,.65,count=1,width=.3,sweep=(0,160),life=10,flow=-.08,emissive=2.2),2),
  sustain(radial_sparks('Inward needles',1,pale,color_end=violet,life=(10,14),width=.06,length=(.35,.6),spawn=dict(shape='Sphere',radius=[.95,1.2]),
   travel=dict(end=[0,[-1.15,-.9],0],easing='EaseInCubic'),fade_in=2,fade_out=2,emissive=2.2),1),
  sustain(distortion_ring('Lens',.8,life=6,strength=1.4,fade_in=1,fade_out=3),3),
  # The orb's body is churning black smoke rather than a clean disc: its silhouette tears and boils every frame.
  sustain(sprite('Seed core','T_Smoke02',(6,1,16,245),life=7,size=.85,size_end=.5,blend='Blend',billboard='Billboard',cutoff=dict(start=0,end=.65,easing='Linear'),fade_in=0,fade_out=3),3),
  sustain(smoke('Churn core',(4,0,10,250),size=(.85,1.05),grow=.85,life=(7,9),speed=(0,0),rise=0,radius=(0,.07),fade_in=0,fade_out=4),1),
  # Grey-violet dust visibly dragged into the orb from all sides.
  sustain(motes('Drawn dust',1,(190,170,210,255),color_end=(120,60,200,255),size=(.06,.11),life=(12,16),spawn=dict(shape='Sphere',radius=[1.1,1.5]),
   travel=dict(end=[0,[-1.45,-1.05],0],easing='EaseInCubic'),turbulence=0,fade_in=3,fade_out=2),1),
  sustain(glow('Hot center',pale,.15,life=5,position=[-.09,.08,.1],emissive=1.8),2),  # off-centre glint, not a bullseye
  sustain(wisps('Hot wisps',pale,.52,count=1,width=.075,sweep=(0,130),life=8,flow=-.1,emissive=2.4),2),
  # Complementary accent: a short orange stroke that only ever sweeps the lower edge.
  sustain(wisps('Ember underside',(255,140,55,255),.8,count=1,width=.22,sweep=(140,225),life=8,tilt=((-20,20),(-20,20),(-15,15)),size=1,emissive=1.5),3),
  sustain(motes('Path glints',1,(255,210,255,255),color_end=violet,size=(.06,.12),life=(14,18),distance=(.05,.3),radius=(0,.2),turbulence=.003,texture='T_Star01',inherit=TRAIL),3),
 ],attach='projectile',peak=.05,flight=.6,delivery=dict(kind='projectile'),
 design='An alpha-black orb with a refraction lens and an off-centre glint inside broken magenta wisp strokes that cross at shifting tilts; needles and grey-violet dust are dragged in, an orange underside accent; it leaves broken strokes on the path that cool from magenta to grey over a grey smoke wake, and glints hang after it has passed.')
