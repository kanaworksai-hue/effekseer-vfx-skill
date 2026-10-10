"""VFX_Projectile_Poison: Lobbed venom glob; paired with VFX_Poison_Cloud on arrival.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 green=(120,210,50,255); acid=(200,255,90,255); hot=(235,255,200,255)
 return effect('Projectile_Poison','Venom Glob','projectile','poison',1.2,[
  sustain(smoke('Fume trail',(130,200,70,195),size=(.35,.6),grow=2.0,life=(24,30),speed=(0,.002),rise=-.0003,radius=(0,.08),inherit=TRAIL,
   color_curve=ramp((0,(160,225,75,200)),(30,(105,135,60,190)),(60,(100,80,112,180)),(100,(80,68,90,0)))['color_curve']),2),
  # A thin acid thread draws the lob's arc clearly through the fumes.
  sustain(sprite('Acid thread','T_Glow01',acid,color_end=fade(green),renderer='Track',track_size=[.1,.06,0],life=10,inherit=TRAIL,fade_in=0,fade_out=4,emissive=1.4),1),
  sustain(sprite('Drips','T_Spark01',acid,color_end=green,billboard='DirectionalBillboard',life=[18,26],scale_start=[.07,.22,1],
   velocity=[[-.004,.004],0,[-.004,.004]],forces=[dict(type='Gravity',gravity=[0,-.003,0])],inherit=TRAIL,fade_in=0,fade_out=4,emissive=1.3),2),
  # Heavy drops that fall off the glob and land.
  sustain(sprite('Heavy drops','T_Dot01',acid,color_end=green,life=[24,30],size=[.07,.14],velocity=[[-.004,.004],0,[-.004,.004]],forces=[dict(type='Gravity',gravity=[0,-.004,0])],
   collide=dict(height=.02,bounce=[.05,.15],friction=.8,reduction=.5),inherit=TRAIL,fade_in=0,fade_out=4,emissive=1.3),3),
  sustain(sprite('Bubbles','T_Bubble01',acid,life=[14,20],size=[.06,.11],size_end=[.12,.18],easing='EaseInQuadratic',position=[[-.12,.12],[-.12,.12],[-.12,.12]],
   velocity=[0,[.002,.006],0],billboard='Billboard',inherit=TRAIL,fade_in=2,fade_out=2,emissive=1.2),4),
  sustain(motes('Spores',1,(195,120,255,255),color_end=(110,50,150,255),size=(.07,.12),life=(20,28),distance=(.1,.5),radius=(0,.2),turbulence=.004,inherit=TRAIL),3),
  sustain(glow('Acid glow',(140,255,60,130),1.1,life=8),3),
  # Purple dark core behind the goo: the complementary shadow that makes the green read as toxic, not lime.
  sustain(sprite('Dark core','T_SoftCircle',(60,20,70,170),blend='Blend',life=5,size=.5,billboard='Billboard',fade_in=0,fade_out=2),2),
  # One readable liquid volume: a colored, deformed mesh changes aspect ratio instead of stacking dark noisy shells.
  sustain(mesh('Glob','Sphere',(155,215,85,255),5,radius=1,sides=32,rings=16,texture=None,blend='Blend',culling='Front',
   model={'ShapeNoise/WaveNoisePower/X':.28,'ShapeNoise/WaveNoisePower/Y':.24,'ShapeNoise/WaveNoisePower/Z':.2,
    'ShapeNoise/WaveNoiseFrequency/X':2.4,'ShapeNoise/WaveNoiseFrequency/Y':2.4,'ShapeNoise/WaveNoiseFrequency/Z':2.4},
   scale_start=[.44,.23,.32],scale_end=[.28,.42,.31],easing='EaseOutCubic',rotation=[[-180,180],[-180,180],[-180,180]],spin=[[-9,9],[-9,9],[-9,9]],
   falloff=dict(begin=[105,75,125,255],end=[235,255,150,255],pow=.55,blend='Mul'),fade_in=0,fade_out=2),4),
  # Goo strands: short broken strokes flicking off the glob at random tilts.
  sustain(wisps('Goo strands',(190,255,90,230),.34,count=1,width=.12,sweep=(0,120),life=8,flow=-.1,emissive=1.6),3),
  sustain(glow('Hot center',hot,.22,life=5,emissive=1.5),2),
  # Wet specular highlight, up and to the left of centre: a white-hot point that sells a glossy liquid.
  sustain(sprite('Highlight','T_Dot01',WHITE,life=4,size=.09,position=[-.1,.12,.2],billboard='Billboard',fade_in=0,fade_out=2,emissive=2.0),2),
 ],attach='projectile',peak=.05,flight=.7,arc=1.3,delivery=dict(kind='projectile'),
 design='A small glossy goo glob lobbed on an arc: a wobbling body with a white wet highlight over a purple dark core, a thin acid thread drawing the arc, drips and heavy drops falling and landing, bubbles and purple spores, fumes that cool from green to murky purple-grey and sink.')
