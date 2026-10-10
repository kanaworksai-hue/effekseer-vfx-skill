"""VFX_Hit_Heavy: Heavy melee hit: the blow lands on the target in place.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 hot=(255,236,170,255); orange=(255,140,40,255)
 return effect('Hit_Heavy','Heavy Hit','hit','physical',.5,[
  shadow('Dark backing',(30,14,8,150),3.6,life=14,delay=3),
  glow('Anticipation',(255,200,120,160),.5,life=3),
  flash('Contact flash',WHITE,4.2,life=5,delay=2,angle=18),
  sprite('Impact burst','T_Impact01',hot,color_end=orange,delay=2,life=10,size=2.6,size_curve=[[0,.45],[20,1],[100,1.12]],rotation=[0,0,[-30,30]],alpha_texture='T_NoiseTile01',cutoff=DISSOLVE,fade_in=0,fade_out=4,emissive=1.5),
  sprite('Speed lines','T_SpeedLines01',hot,delay=2,life=7,size=4.4,size_curve=[[0,.4],[40,1],[100,1.2]],rotation=[0,0,[0,360]],fade_in=0,fade_out=5),
  glow('Heat bloom',(255,120,30,200),3.4,life=14,delay=2),
  shell('Air bubble',(255,220,170,200),1.6,life=11,delay=3),
  tilted_ring('Air wave',(255,220,170,170),2.0,life=11,delay=3,thickness=.22,tilt=(0,58,0)),
  distortion_ring('Refraction wave',2.4,life=12,delay=2,strength=.8),
  *spark_burst('Sparks',20,hot,(255,70,10,255),distance=(1.0,2.6),life=(10,18),length=(.5,1.1),delay=2),
  motes('Embers',12,orange,color_end=(255,40,0,255),life=(22,27),distance=(.5,1.6),delay=3,rise=-.0006),
  smoke('Dust',(185,160,135,230),color_end=(150,125,105,140),count=5,size=(.7,1.1),life=(22,26),delay=4),
 ],peak=.05,impact=.9,delivery=MELEE,design='Two-frame anticipation, white flash, dissolving jagged burst, eased sparks that hang and droop, dust.')
