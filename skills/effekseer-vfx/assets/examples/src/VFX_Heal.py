"""VFX_Heal: Heal on the caster: no impact frame, a slow upward rise.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 green=(110,255,170,255); pale=(225,255,235,255); teal=(40,220,160,255)
 return effect('Heal','Heal','status','holy',1.7,[
  decal('Blessing seal','T_Rune02',green,3.4,life=88,spin=.6,size_curve=[[0,.2],[14,1.05],[24,1],[100,1.05]],color_end=teal,fade_in=4,fade_out=34,emissive=1.3),
  decal('Floor glow','T_Glow01',(60,230,140,150),4.4,life=88,fade_in=10,fade_out=30),
  column('Soft column',(90,255,170,200),.95,3.6,life=74,delay=8,scroll=(.003,-.012),fade_in=12,fade_out=28),
  shock_ring('Rising rings',green,1.25,life=40,delay=8,ground=True,count=3,interval=13,travel=dict(start=[0,.15,0],end=[0,2.5,0],easing='EaseOutCubic'),thickness=.1,size_curve=[[0,.5],[30,1],[100,.8]]),
  sprite('Plus signs','T_Cross01',pale,color_end=green,count=9,delay=10,interval=5,life=[30,40],size=[.22,.36],size_end=[.1,.16],
   spawn=dict(shape='Circle',radius=[.3,.9],rotate=False),position=[0,.3,0],travel=dict(start=[0,0,0],end=[0,[1.5,2.4],0],easing='EaseOutQuadratic'),billboard='Billboard',fade_in=5,fade_out=10,emissive=1.4),
  motes('Life motes',30,pale,color_end=green,life=(30,46),delay=6,interval=1.6,size=(.08,.18),spawn=dict(shape='Circle',radius=[.2,1.1],rotate=False),travel=dict(end=[0,[1.4,3.0],0],easing='EaseOutQuadratic')),
  sprite('Twinkles','T_Star01',pale,count=10,delay=14,interval=5,life=[12,18],size=[.3,.6],size_end=0,position=[[-.8,.8],[.4,2.4],[-.3,.6]],rotation=[0,0,[0,90]],fade_in=2,fade_out=5),
  glow('Body bloom',(120,255,180,150),3.2,life=40,delay=14,position=[0,1.1,0],size_curve=[[0,.5],[40,1],[100,1.1]],fade_in=12,fade_out=24),
 ],attach='ground',peak=.6,light=(.5,1,.7),delivery=SELF,design='No impact frame at all: slow seal, soft scrolling column, rings and plus signs drifting upward, a gentle bloom on the body.')
