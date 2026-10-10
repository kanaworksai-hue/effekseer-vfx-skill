"""VFX_Magic_Charge: Arcane charge on the caster: a long inward build, then one release.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 cyan=(120,220,255,255); pale=(235,250,255,255); blue=(60,120,255,255)
 return effect('Magic_Charge','Magic Charge','magic','arcane',1.5,[
  motes('Gathering motes',46,pale,color_end=cyan,life=(16,26),interval=1.2,size=(.09,.2),spawn=dict(shape='Sphere',radius=[1.6,2.6]),travel=dict(end=[0,[-2.6,-1.6],0],easing='EaseInQuadratic'),turbulence=.0005),
  radial_sparks('Gathering streaks',24,cyan,color_end=pale,life=(9,14),interval=2.4,length=(.5,.9),width=.07,spawn=dict(shape='Sphere',radius=[1.8,2.4]),travel=dict(end=[0,[-2.4,-1.8],0],easing='EaseInCubic')),
  # Two rune bands on different tilted planes orbit the core like a gyroscope and tighten as the charge builds.
  orbit_band('Orbit ring A',cyan,pale,(60,120,255,0),1.5,.22,64,tilt=(-62,0,28),flow=-.05,size=1,size_curve=[[0,1.3],[85,.55],[100,.2]],fade_in=12,fade_out=4,emissive=1.5),
  orbit_band('Orbit ring B',cyan,pale,(60,120,255,0),1.25,.18,60,tilt=(-10,62,0),flow=.07,delay=4,size=1,size_curve=[[0,1.3],[85,.5],[100,.2]],fade_in=12,fade_out=4,emissive=1.5),
  # Shells that implode onto the core: the gather reads as a volume collapsing, not a hoop shrinking on screen.
  shell('Converging shell',(120,220,255,170),2.0,life=20,delay=6,count=3,interval=18,scale_curve=[[0,1],[100,.1]],pow=.25,fade_in=6,fade_out=3),
  glow('Core',pale,1.7,life=64,size_curve=[[0,.1],[85,1],[100,1.25]],fade_in=6,fade_out=3,emissive=1.6),
  glow('Aura',(60,130,255,170),3.6,life=64,size_curve=[[0,.2],[85,1],[100,1.2]],fade_in=10,fade_out=3),
  flash('Charged flash',WHITE,5.6,life=6,delay=64,angle=20),
  glow('Charged bloom',(110,190,255,230),4.6,life=18,delay=64),
  shell('Charged shell',pale,2.6,life=12,delay=65),
  radial_sparks('Charged sparks',20,pale,color_end=blue,distance=(.9,2.4),life=(12,22),length=(.5,1.0),delay=64),
 ],attach='caster',peak=1.08,impact=.5,light=(.6,.8,1),delivery=SELF,design='Motes and streaks accelerate inward while two tilted rune bands orbit the core like a gyroscope and tighten onto it, then a single flash confirms the charge.')
