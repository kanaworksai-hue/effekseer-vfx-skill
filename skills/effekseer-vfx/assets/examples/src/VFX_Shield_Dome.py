"""VFX_Shield_Dome: Shield dome on the caster: raise, hold, then break into fragments.

Example from the effekseer-vfx skill. Copy it with `vfx examples add`, then edit, build and review it
like any other effect; its historical review does not carry over to your edits.
"""
from vfxkit.primitives import *


def recipe():
 blue=(90,170,255,255); pale=(215,240,255,255)
 pop=[[0,.2],[9,1.1],[16,.97],[24,1],[85,1],[100,1.08]]
 return effect('Shield_Dome','Shield Dome','status','arcane',1.8,[
  flash('Raise glint',WHITE,3.6,life=5,position=[0,.4,1.2]),
  # Clean fresnel force field (a colour texture or a held dissolve edge rendered as grey blotches in the plugin);
  # On expiry the full shell hands off to partial spherical geometry: the readable break-up (the shell's own cutoff once
  # never animated in Godot because it was an FCurve; it now compiles to an Easing, see engine conventions).
  mesh('Shell','Sphere',(50,120,255,170),life=84,radius=1,sides=48,rings=24,scale_start=[1.45]*3,scale_curve=pop,culling='Front',z_test=True,
   falloff=dict(begin=[60,120,255,90],end=[150,210,255,255],pow=.6,blend='Mul'),alpha_texture='T_NoiseTile02',alpha_scroll=[.002,.003],
   cutoff=dict(start=0,end=.98,easing='EaseInQuartic'),fade_in=2,fade_out=4),
  # Falloff: begin covers the part facing the camera and a higher pow shrinks it, so a thin rim needs pow < 1.
  mesh('Rim','Sphere',(150,200,255,200),life=84,radius=1,sides=48,rings=24,scale_start=[1.47]*3,scale_curve=pop,culling='Front',z_test=True,
   falloff=dict(begin=[0,0,0,0],end=[255,255,255,255],pow=.4,blend='Mul'),alpha_texture='T_NoiseTile02',
   cutoff=dict(start=0,end=.98,easing='EaseInQuartic'),fade_in=2,fade_out=4),
  # Energy streaks crawling over the surface: a streak mask flowing round the sphere (multiplied, no cutoff edge).
  mesh('Surface flow','Sphere',(110,190,255,170),life=80,radius=1,sides=48,rings=24,scale_start=[1.46]*3,scale_curve=pop,culling='Front',z_test=True,delay=4,
   alpha_texture='T_NoiseStreak01',alpha_scroll=[.012,.004],cutoff=dict(start=0,end=.98,easing='EaseInQuartic'),
   falloff=dict(begin=[0,0,0,0],end=[255,255,255,255],pow=.8,blend='Mul'),fade_in=8,fade_out=4,emissive=1.4),
  shock_ring('Equator pulse',pale,1.9,life=14,delay=3,ground=True,thickness=.18),
  shock_ring('Scan bands',blue,1.5,life=30,delay=14,ground=True,count=3,interval=22,travel=dict(start=[0,-1.1,0],end=[0,1.2,0],easing='Linear'),thickness=.08,size_curve=[[0,.65],[50,1],[100,.6]]),
  motes('Surface glints',18,pale,color_end=blue,life=(18,30),delay=8,interval=4,size=(.07,.14),spawn=dict(shape='Sphere',radius=[1.4,1.5]),travel=dict(end=[0,[.1,.3],0],easing='EaseOutQuadratic')),
  radial_sparks('Break shards',16,pale,color_end=blue,distance=(.4,1.2),life=(10,18),length=(.3,.6),width=.07,delay=88,spawn=dict(shape='Sphere',radius=[1.3,1.5])),
  *shell_fragments('Shell fragment',(90,165,255,230),1.47,delay=80,life=24),
 ],attach='body',peak=.15,impact=.3,light=(.6,.8,1),delivery=SELF,design='Fresnel shell pops with overshoot, scan bands sweep up; at expiry six partial spherical sheets separate and tumble outward, with fine shards between their gaps.')
