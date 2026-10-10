"""VFX_Slash_Fire: Fire sword slash played on the target (melee).

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 red=(255,70,15,200); orange=(255,150,40,255); white=(255,245,200,255)
 return effect('Slash_Fire','Fire Slash','slash','fire',.6,[
  *swing(slash_set((red,orange,white),roll=30,radius=1.6,life=16),yaw=-32),
  glow('Heat bloom',(255,110,20,170),3.6,life=16,delay=2),
  flame('Flame tongues',orange,(200,30,5,0),size=[1.3,2.0],size_end=[.5,.8],count=9,delay=3,interval=1,life=[18,24],
   position=[[-1.2,1.2],[-.7,.2],[-.7,.7]],velocity=[[-.008,.008],[.012,.03],0],z_test=True,fade_in=1,fade_out=12),  # tongues behind the body are hidden by it
  heat_haze('Heat haze',3.0,life=30,delay=4,strength=.4),
  radial_sparks('Sparks',16,white,color_end=(255,90,10,255),distance=(.8,2.2),life=(14,26),length=(.4,.8),delay=3,gravity=.0008),
  smoke('Cut smoke',(90,70,62,200),count=5,size=(.5,.8),grow=2.0,life=(18,20),delay=10,interval=1,radius=(.3,1.0),speed=(.01,.02),rise=.0005),
  motes('Rising embers',18,orange,color_end=(255,40,0,255),life=(22,30),distance=(.4,1.6),delay=4,rise=.0007,radius=(.3,1.2)),
  smoke('Heat haze',(110,80,65,130),count=4,size=(.6,.9),life=(16,22),delay=8,radius=(.3,1.0)),
 ],peak=.08,impact=.6,light=(1,.55,.2),delivery=MELEE,design='Red-orange-white swept blade, then distorted flame tongues peel upward off the arc with embers and thin smoke.')
