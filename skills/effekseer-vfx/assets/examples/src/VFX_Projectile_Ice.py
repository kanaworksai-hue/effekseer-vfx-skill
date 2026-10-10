"""VFX_Projectile_Ice: Ice lance projectile; paired with VFX_Ice_Spikes on arrival.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 white=(240,252,255,255); cyan=(130,215,255,255); deep=(60,130,255,255)
 lane=lambda tag,color,dy,size:sustain(sprite(tag,'T_Glow01',color,color_end=fade(deep),renderer='Track',track_size=size,life=12,inherit=TRAIL,position=[0,dy,0],fade_in=0,fade_out=4,emissive=.85),1)
 return effect('Projectile_Ice','Ice Lance','projectile','ice',.7,[
  sustain(smoke('Frost mist',(150,200,255,210),size=(.35,.7),grow=1.7,life=(16,19),color_curve=ramp((0,(170,215,255,210)),(50,(130,150,175,170)),(100,(100,110,125,0)))['color_curve'],speed=(0,.002),rise=-.0009,radius=(0,.06),inherit=TRAIL,delay=2),3),
  # Muzzle: three stacked shock rings left where the lance was loosed, across the line of flight.
  tilted_ring('Muzzle rings',(210,240,255,210),.5,life=12,tilt=(0,90,0),thickness=.1,count=3,interval=2,inherit=TRAIL),
  lane('Lance trail',cyan,0,[.18,.12,.02]),
  # Prism fringe: two faint coloured lanes either side of the white ribbon (ice's complementary accent).
  lane('Prism warm',(255,120,200,90),.045,[.12,.08,0]),
  lane('Prism gold',(255,230,120,90),-.045,[.12,.08,0]),
  # Frost rings frozen in the air along the path, one every few frames: cold, crisp punctuation.
  sustain(tilted_ring('Frost rings',(200,240,255,200),.45,life=10,tilt=(0,90,0),thickness=.08,inherit=TRAIL),5),
  sustain(crystal('Shed shards',(110,200,255,200),1,.22,[14,20],edge=(235,250,255,255),scale_start=[[.1,.3],[.15,.5],[.1,.3]],rotation=[[-180,180],[-180,180],[-180,180]],
   position=[[-.35,.35],[-.25,.2],[-.3,.3]],spin=[[-10,10],[-10,10],[-10,10]],velocity=[[-.02,.012],[-.014,.008],[-.014,.014]],forces=[dict(type='Gravity',gravity=[0,-.0035,0])],inherit=TRAIL,fade_in=0,fade_out=6,emissive=1.3),2),
  sustain(sprite('Ice chips','T_IceShard01',(210,240,255,255),life=[10,18],size=[.04,.18],rotation=[0,0,[-180,180]],spin=[0,0,[-14,14]],
   velocity=[[-.01,.004],[-.004,.006],[-.006,.006]],forces=[dict(type='Gravity',gravity=[0,-.005,0])],inherit=TRAIL,fade_in=0,fade_out=3,emissive=1.4),2),
  sustain(sprite('Navy chips','T_Shard01',(36,56,118,255),blend='Blend',life=[14,19],size=[.1,.22],position=[[-.3,.3],[-.2,.2],[-.25,.25]],rotation=[0,0,[-180,180]],spin=[0,0,[-12,12]],
   velocity=[[-.01,.004],[-.006,.004],[-.006,.006]],forces=[dict(type='Gravity',gravity=[0,-.004,0])],inherit=TRAIL,fade_in=0,fade_out=4),3),
  sustain(sprite('Twinkles','T_Star01',white,life=[8,12],size=[.15,.3],size_end=0,easing='EaseInCubic',position=[[-.12,.12],[-.12,.12],[-.12,.12]],rotation=[0,0,[0,90]],inherit=TRAIL,fade_in=1,fade_out=3),2),
  sustain(glow('Cold bloom',(80,170,255,45),.42,life=6),2),
  # Faceted navy backing follows the lance and exposes a narrow lower edge.
  sustain(crystal('Navy back',(40,85,185,230),1.7,.25,4,edge=(50,105,195,230),rotation=[0,0,-90],position=[-.93,-.055,0],blend='Blend',fade_in=0,fade_out=1) | dict(falloff=dict(begin=[45,70,150,230],end=[100,150,225,230],pow=.5,blend='Mul'),culling='Front'),2),
  # The lance is a faceted crystal lying along the flight line (+Y turned to +X), tip forward.
  sustain(crystal('Lance',(95,190,255,240),1.6,.22,4,edge=(190,235,255,220),rotation=[0,0,-90],position=[-.9,0,0],fade_in=0,fade_out=1,emissive=.9) | dict(falloff=dict(begin=[55,125,225,220],end=[190,235,255,230],pow=.5,blend='Mul'),culling='Front'),2),
  sustain(sprite('Tip star','T_Star01',WHITE,life=4,size=.28,rotation=[0,0,[0,90]],spin=[0,0,12],fade_in=0,fade_out=2,emissive=1.4),2),
 ],attach='projectile',peak=.05,flight=.35,delivery=dict(kind='projectile'),
 design='A fast, crisp crystal lance with a navy backing on a thin white ribbon fringed with faint prism colours; stacked rings at the muzzle and frost rings frozen along the path, shards and chips break off and fall, twinkles hang on the line, cold mist sinks behind it.')
